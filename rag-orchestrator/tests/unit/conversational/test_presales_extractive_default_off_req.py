"""unit 層：PRESALES_EXTRACTIVE 預設關（業主 2026-09-04 二次裁決：不要 D6，補完知識再考慮）。
關時：事實題有知識 ⇒ LLM 依知識合成（converge 合成路，cta suppress）；inline／ask 反問句閘門抓到有知識 ⇒ 同樣合成、⛔ 不用 brain 文字；
沒知識 ⇒ 固定句不變；開關只認 1/true/on/yes。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import conversational_config as cc
from services import usage_metering as um
from services.conversational_config import ConversationalConfig
from services.conversational_engine import ConversationalEngine
from services.presales_gate import extractive_enabled
from tests.support.brain_stub import stub_step

pytestmark = pytest.mark.unit
CFG = ConversationalConfig(key="presales", persona_role="prospect",
                           grounding_scope={"target_user": "prospect", "mode": "b2b"},
                           answer_rules=cc.PRESALES_ANSWER_RULES, handoff_message=cc.PRESALES_HANDOFF_MESSAGE)
KB = "系統支援物件批次匯入，由 JGB 協助提供批次匯入表格。"


def _engine(hits, llm_text="合成文"):
    eng = ConversationalEngine(db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
                               get_system_context=AsyncMock(return_value="md"), rules_loader=AsyncMock(return_value="規則"))
    eng.retriever.retrieve = AsyncMock(return_value=hits)
    eng.get_state = AsyncMock(return_value={"collected_fields": {}, "asked_count": 0, "dialog": []})
    eng._save = AsyncMock()
    eng.optimizer.synthesize_presales_answer = MagicMock(return_value=llm_text)
    return eng


@pytest.fixture(autouse=True)
def _flag_unset(monkeypatch):
    monkeypatch.delenv("PRESALES_EXTRACTIVE", raising=False)


@pytest.fixture
def snapshots(monkeypatch):
    got = []
    monkeypatch.setattr(um, "set_decision", lambda snapshot=None, facet_event=None: got.append(snapshot))
    return got


@pytest.mark.req("presales-grounding-gate:2.10")
@pytest.mark.parametrize("val,expect", [(None, False), ("", False), ("0", False), ("off", False), ("1", True), ("true", True), ("ON", True), ("yes", True)])
def test_flag_parsing_default_off(monkeypatch, val, expect):
    if val is None:
        monkeypatch.delenv("PRESALES_EXTRACTIVE", raising=False)
    else:
        monkeypatch.setenv("PRESALES_EXTRACTIVE", val)
    assert extractive_enabled() is expect


@pytest.mark.req("presales-grounding-gate:2.10")
async def test_converge_fact_with_grounding_goes_to_llm_synth(snapshots):
    eng = _engine([{"answer": KB, "similarity": 0.8}])
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "匯入", "extracted_fields": {}, "fact_class": "feature"})
    r = await eng.handle("backtest_session_off1", "anon", 0, "物件可以匯入嗎", CFG, start_if_absent=True)
    assert r["answer"] == "合成文"
    kw = eng.optimizer.synthesize_presales_answer.call_args
    assert KB in kw.args[0] and kw.args[4] == "suppress"          # grounding 是知識原文、事實型 cta suppress


@pytest.mark.req("presales-grounding-gate:2.10")
async def test_inline_with_grounding_goes_to_llm_synth_not_brain_text(snapshots):
    eng = _engine([{"answer": KB, "similarity": 0.8}])
    stub_step(eng.optimizer, {"action": "ask", "converge_kind": "answer", "converge_topic": "匯入", "extracted_fields": {}, "fact_class": "other",
                              "inline_answer": "是的，物件和合約的資料也可以匯入。", "next_question": "請問您是哪一類管理者？"})
    r = await eng.handle("backtest_session_off2", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"] == "合成文" and "合約的資料也可以匯入" not in r["answer"]
    assert KB in eng.optimizer.synthesize_presales_answer.call_args.args[0]
    assert snapshots[-1]["presales"]["path"] == "inline" and snapshots[-1]["presales"]["grounding_hits"] == 1


@pytest.mark.req("presales-grounding-gate:2.11")
async def test_ask_declarative_with_grounding_goes_to_llm_synth(snapshots):
    eng = _engine([{"answer": KB, "similarity": 0.8}])
    # R2.13 後 fact_class≠other 會先走 ask_fact；本測試守的是 R2.11 反問句結構閘門 ⇒ 用 fact_class=other 讓它走到 R2.11
    stub_step(eng.optimizer, {"action": "ask", "converge_kind": "answer", "converge_topic": "匯入", "extracted_fields": {}, "fact_class": "other",
                              "next_question": "我們的系統支援租客批次匯入，包括房東、租客、合約和歷史帳單。請問您還有其他想了解的功能嗎？"})
    r = await eng.handle("backtest_session_off3", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"] == "合成文" and "歷史帳單" not in r["answer"]
    assert snapshots[-1]["presales"]["path"] == "ask"


@pytest.mark.req("presales-grounding-gate:2.1")
async def test_no_grounding_still_fixed_sentence(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "客戶", "extracted_fields": {}, "fact_class": "customer_reference"})
    r = await eng.handle("backtest_session_off4", "anon", 0, "有沒有600戶客戶", CFG, start_if_absent=True)
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and r["handoff"]["reason"] == "sensitive_no_grounding"
    eng.optimizer.synthesize_presales_answer.assert_not_called()


@pytest.mark.req("presales-grounding-gate:4.2")
async def test_llm_synth_mentioning_staff_still_gets_handoff(snapshots):
    eng = _engine([{"answer": KB, "similarity": 0.8}], llm_text="細節可由專人說明。")
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "匯入", "extracted_fields": {}, "fact_class": "feature"})
    r = await eng.handle("backtest_session_off5", "anon", 0, "物件可以匯入嗎", CFG, start_if_absent=True)
    assert r["handoff"]["reason"] == "llm_mentioned_handoff" and r["handoff"]["message"] == cc.PRESALES_HANDOFF_ENTRY_HINT
