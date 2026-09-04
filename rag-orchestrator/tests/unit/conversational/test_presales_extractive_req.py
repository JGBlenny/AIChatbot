"""unit 層：D6 事實題抽取式作答（需求 2.10）。fact_class≠other 且有 grounding ⇒ 直接回 top-1 知識原文、⛔ 不經 LLM；
多項目問句且知識只涵蓋部分 ⇒ 接固定尾句＋handoff(partial_grounding)。推薦題／other／無知識路徑不變。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import conversational_config as cc
from services import usage_metering as um
from services.conversational_config import ConversationalConfig
from services.conversational_engine import ConversationalEngine
from services.presales_gate import HandoffReason, is_multi_item_question
from tests.support.brain_stub import stub_step

pytestmark = pytest.mark.unit
CFG = ConversationalConfig(key="presales", persona_role="prospect",
                           grounding_scope={"target_user": "prospect", "mode": "b2b"},
                           answer_rules=cc.PRESALES_ANSWER_RULES, handoff_message=cc.PRESALES_HANDOFF_MESSAGE)
KB_3357 = "系統支援物件批次匯入，由 JGB 協助提供批次匯入表格。注意事項：檔案格式須為 .xls（非 .xlsx）。"
KB_3611 = "可以的，新帳號享有免費試用一個月。"


def _engine(hits, llm_text="LLM 不該被呼叫"):
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
    return got


# ── 多項目偵測（封閉分隔詞）──────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:2.10")
@pytest.mark.parametrize("q,expect", [
    ("舊系統資料可以匯進來嗎？包含房東、租客、合約、歷史帳單", True),
    ("那物件跟合約呢？", True),
    ("房東和租客的資料能匯嗎", True),
    ("可以免費試用嗎", False),
    ("你好，請問可以線上簽約嗎", False),          # 逗號不算分隔詞（幾乎每句都有）
])
def test_multi_item_detection_is_a_closed_separator_set(q, expect):
    assert is_multi_item_question(q) is expect


# ── converge 路徑：事實題有知識 ⇒ 抽取，不叫 LLM ─────────────────────────────
@pytest.mark.req("presales-grounding-gate:2.10")
async def test_fact_with_grounding_returns_top1_verbatim_without_llm(snapshots):
    eng = _engine([{"answer": KB_3611, "similarity": 0.99, "score_source": "rerank"}, {"answer": "第二條", "similarity": 0.7}])
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "試用", "extracted_fields": {}, "fact_class": "feature"})
    r = await eng.handle("backtest_session_x1", "anon", 0, "可以免費試用嗎", CFG, start_if_absent=True)
    assert r["answer"] == KB_3611 and r.get("handoff") is None and r["converged"] is False
    eng.optimizer.synthesize_presales_answer.assert_not_called()
    pres = [s["presales"] for s in snapshots if s and "presales" in s]
    assert pres and pres[-1]["path"] == "extract" and pres[-1]["grounding_hits"] == 2


@pytest.mark.req("presales-grounding-gate:2.10")
async def test_multi_item_fact_gets_tail_and_partial_handoff(snapshots):
    eng = _engine([{"answer": KB_3357, "similarity": 0.8, "score_source": "rerank"}])
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "匯入", "extracted_fields": {}, "fact_class": "feature"})
    r = await eng.handle("backtest_session_x2", "anon", 0, "舊系統資料可以匯進來嗎？包含房東、租客、合約、歷史帳單", CFG, start_if_absent=True)
    assert r["answer"] == KB_3357 + "\n\n" + cc.PRESALES_PARTIAL_TAIL
    assert r["handoff"]["reason"] == "partial_grounding" and r["handoff"]["fact_class"] == "feature"
    assert "合約" not in r["answer"].replace("合約、", "") or "沒有資料" in r["answer"]   # 原文不含「合約可匯」
    eng.optimizer.synthesize_presales_answer.assert_not_called()


# ── inline（ask＋岔題即答）路徑：同樣抽取 ─────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:2.10")
async def test_inline_fact_with_grounding_is_extracted_not_brain_text(snapshots):
    eng = _engine([{"answer": KB_3357, "similarity": 0.8, "score_source": "rerank"}])
    stub_step(eng.optimizer, {"action": "ask", "next_question": "請問規模？", "inline_answer": "房東、租客、合約和帳單都可以匯入。",
                              "extracted_fields": {}, "fact_class": "feature"})
    r = await eng.handle("backtest_session_x3", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"].startswith(KB_3357) and "都可以匯入" not in r["answer"] and "請問規模" not in r["answer"]
    assert r["handoff"]["reason"] == "partial_grounding"


# ── 不受影響的路徑 ───────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:2.4")
async def test_recommend_still_goes_through_llm(snapshots):
    eng = _engine([{"answer": "方案", "similarity": 0.8}], llm_text="推薦文")
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "recommend", "converge_topic": "方案", "extracted_fields": {}, "fact_class": "other"})
    r = await eng.handle("backtest_session_x4", "anon", 0, "我適合哪種方案", CFG, start_if_absent=True)
    assert r["answer"] == "推薦文"; eng.optimizer.synthesize_presales_answer.assert_called_once()


@pytest.mark.req("presales-grounding-gate:2.10")
async def test_fact_class_other_answer_still_goes_through_llm(snapshots):
    eng = _engine([{"answer": "A", "similarity": 0.8}], llm_text="LLM 文")
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "x", "extracted_fields": {}, "fact_class": "other"})
    r = await eng.handle("backtest_session_x5", "anon", 0, "隨便聊", CFG, start_if_absent=True)
    assert r["answer"] == "LLM 文"


@pytest.mark.req("presales-grounding-gate:2.1")
async def test_fact_without_grounding_still_handoff(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "客戶", "extracted_fields": {}, "fact_class": "customer_reference"})
    r = await eng.handle("backtest_session_x6", "anon", 0, "有沒有600戶客戶", CFG, start_if_absent=True)
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and r["handoff"]["reason"] == "sensitive_no_grounding"


@pytest.mark.req("presales-grounding-gate:2.10")
def test_partial_grounding_is_a_valid_reason():
    assert HandoffReason("partial_grounding") is HandoffReason.partial_grounding
    assert "{" not in cc.PRESALES_PARTIAL_TAIL and "找真人" in cc.PRESALES_PARTIAL_TAIL and "沒有資料" in cc.PRESALES_PARTIAL_TAIL


@pytest.mark.req("presales-grounding-gate:2.10")
async def test_inline_with_grounding_is_extractive_even_when_fact_class_other(snapshots):
    """D6 上線首輪探針：brain 對「那物件跟合約呢？」回 fact_class=other＋inline「是的，物件和合約的資料也可以匯入」，
    有 1 筆知識 ⇒ 舊碼保留 brain 文字（假事實漏出）。inline 本身就是事實答 ⇒ 不看 fact_class 一律抽取。"""
    eng = _engine([{"answer": "物件可用 Excel 批次匯入", "similarity": 0.8}], llm_text="不該被呼叫")
    stub_step(eng.optimizer, {"action": "ask", "converge_kind": "answer", "converge_topic": "匯入", "extracted_fields": {},
                              "fact_class": "other", "inline_answer": "是的，物件和合約的資料也可以匯入。", "next_question": "請問您是哪一類管理者？"})
    r = await eng.handle("backtest_session_x7", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"].startswith("物件可用 Excel 批次匯入") and "合約的資料也可以匯入" not in r["answer"]
    assert r["handoff"]["reason"] == "partial_grounding"        # 「物件跟合約」含分隔詞「跟」⇒ 多項目尾句
    eng.optimizer.synthesize_presales_answer.assert_not_called()
