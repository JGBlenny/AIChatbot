"""unit 層：R2.13（主題 pilot 2026-09-04，反問未答 15/46）。brain 回 `ask`、未填 inline、但自己標了 `fact_class≠other`
（＝使用者這句是事實題，只是句形是陳述：「舊約要輸入系統」「我有現成的合約想放進系統」），且知識非空 ⇒ 走有據作答，
⛔ 不反問身分。知識空 ⇒ 維持原 ask（不升格固定句：陳述句可能真的是在描述情境）。fact_class=other ⇒ 不動。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import conversational_config as cc
from services import usage_metering as um
from services.conversational_config import ConversationalConfig
from services.conversational_engine import ConversationalEngine
from tests.support.brain_stub import stub_step

pytestmark = pytest.mark.unit
CFG = ConversationalConfig(key="presales", persona_role="prospect",
                           grounding_scope={"target_user": "prospect", "mode": "b2b"},
                           answer_rules=cc.PRESALES_ANSWER_RULES, handoff_message=cc.PRESALES_HANDOFF_MESSAGE)
KB = "紙本簽約：把既有的紙本合約上傳留存，與制式合約效力相同。"
ASK_Q = "請問您是個人房東、二房東、包租代管業還是物管呢？"


def _engine(hits, llm_text="合成文"):
    eng = ConversationalEngine(db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
                               get_system_context=AsyncMock(return_value="md"), rules_loader=AsyncMock(return_value="規則"))
    eng.retriever.retrieve = AsyncMock(return_value=hits)
    eng.get_state = AsyncMock(return_value={"collected_fields": {}, "asked_count": 0, "dialog": []})
    eng._save = AsyncMock()
    eng.optimizer.synthesize_presales_answer = MagicMock(return_value=llm_text)
    return eng


@pytest.fixture
def snapshots(monkeypatch):
    got = []
    monkeypatch.setattr(um, "set_decision", lambda snapshot=None, facet_event=None: got.append(snapshot))
    monkeypatch.delenv("PRESALES_EXTRACTIVE", raising=False)
    return got


def _ask(fact_class):
    return {"action": "ask", "converge_kind": "recommend", "converge_topic": "合約", "extracted_fields": {},
            "fact_class": fact_class, "next_question": ASK_Q}


@pytest.mark.req("presales-grounding-gate:2.13")
async def test_declarative_fact_with_grounding_is_answered_not_asked_back(snapshots):
    eng = _engine([{"answer": KB, "similarity": 0.8}])
    stub_step(eng.optimizer, _ask("feature"))
    r = await eng.handle("backtest_session_af1", "anon", 0, "舊約要輸入系統", CFG, start_if_absent=True)
    assert r["answer"] == "合成文" and ASK_Q not in r["answer"]
    assert KB in eng.optimizer.synthesize_presales_answer.call_args.args[0]
    assert snapshots[-1]["presales"]["path"] == "ask_fact" and snapshots[-1]["presales"]["fact_class"] == "feature"


@pytest.mark.req("presales-grounding-gate:2.13")
async def test_declarative_fact_without_grounding_keeps_ask(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, _ask("feature"))
    r = await eng.handle("backtest_session_af2", "anon", 0, "舊約要輸入系統", CFG, start_if_absent=True)
    assert r["answer"] == ASK_Q and r.get("handoff") is None      # 陳述句無知識 ⇒ 不升格固定句，照 brain 反問
    eng.optimizer.synthesize_presales_answer.assert_not_called()


@pytest.mark.req("presales-grounding-gate:2.13")
async def test_fact_class_other_declarative_untouched(snapshots):
    eng = _engine([{"answer": KB, "similarity": 0.8}])
    stub_step(eng.optimizer, _ask("other"))
    r = await eng.handle("backtest_session_af3", "anon", 0, "我們公司管180間", CFG, start_if_absent=True)
    assert r["answer"] == ASK_Q
    eng.retriever.retrieve.assert_not_called()


@pytest.mark.req("presales-grounding-gate:2.13")
async def test_question_shaped_fact_with_grounding_answers_before_r211(snapshots):
    """有問句標記＋fact_class≠other＋有知識 ⇒ 直接有據作答（不必等 R2.11 去拆反問句）。"""
    eng = _engine([{"answer": KB, "similarity": 0.8}])
    stub_step(eng.optimizer, _ask("feature"))
    r = await eng.handle("backtest_session_af4", "anon", 0, "我有現成的合約想放進系統可以嗎？", CFG, start_if_absent=True)
    assert r["answer"] == "合成文"


@pytest.mark.req("presales-grounding-gate:2.13")
async def test_non_prospect_untouched(snapshots):
    cfg = ConversationalConfig(key="pm", persona_role="property_manager", grounding_scope={"target_user": "property_manager", "mode": "b2b"})
    eng = _engine([{"answer": KB, "similarity": 0.8}])
    stub_step(eng.optimizer, _ask("feature"))
    r = await eng.handle("backtest_session_af5", "anon", 0, "舊約要輸入系統", cfg, start_if_absent=True)
    assert r["answer"] == ASK_Q
    eng.retriever.retrieve.assert_not_called()
