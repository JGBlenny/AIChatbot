"""unit 層：R2.11 ask 分支閘門（e2e 第三輪 A1）。brain 用 ask、不填 inline_answer、把答案塞進 next_question ⇒
結構判定後走同一把閘門：有知識抽取原文、沒知識固定句；非問句／純反問不受影響。附 E1：抽取原文含「專人」⇒ handoff 非 null。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import conversational_config as cc
from services import usage_metering as um
from services.conversational_config import ConversationalConfig
from services.conversational_engine import ConversationalEngine
from services.presales_gate import ask_is_answering, looks_like_question, split_declaratives, ASK_DECLARATIVE_MIN_CHARS, analyze_ask, strip_declarative_clauses
from tests.support.brain_stub import stub_step

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _extractive_on(monkeypatch):
    """本檔驗 D6 抽取式行為 ⇒ 明確開旗標（預設關，見 test_presales_extractive_default_off_req）。"""
    monkeypatch.setenv("PRESALES_EXTRACTIVE", "1")
CFG = ConversationalConfig(key="presales", persona_role="prospect",
                           grounding_scope={"target_user": "prospect", "mode": "b2b"},
                           answer_rules=cc.PRESALES_ANSWER_RULES, handoff_message=cc.PRESALES_HANDOFF_MESSAGE)
KB_3357 = "系統支援物件批次匯入，由 JGB 協助提供批次匯入表格。"
KB_3611 = "可以的，新帳號享有免費試用一個月。想看實際操作可預約 demo 由專人帶您看。"
FABRICATED_Q = "我們的系統支援租客批次匯入，您可以將舊系統的資料匯進來，包括房東、租客、合約和歷史帳單。請問您還有其他想了解的功能嗎？"


def _engine(hits):
    eng = ConversationalEngine(db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
                               get_system_context=AsyncMock(return_value="md"), rules_loader=AsyncMock(return_value="規則"))
    eng.retriever.retrieve = AsyncMock(return_value=hits)
    eng.get_state = AsyncMock(return_value={"collected_fields": {}, "asked_count": 0, "dialog": []})
    eng._save = AsyncMock()
    eng.optimizer.synthesize_presales_answer = MagicMock(return_value="LLM 不該被呼叫")
    return eng


@pytest.fixture
def snapshots(monkeypatch):
    got = []
    monkeypatch.setattr(um, "set_decision", lambda snapshot=None, facet_event=None: got.append(snapshot))
    return got


def _ask(q, fact_class="other"):
    return {"action": "ask", "converge_kind": "answer", "converge_topic": "匯入", "extracted_fields": {},
            "fact_class": fact_class, "next_question": q}


# ── 結構判定 ────────────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:2.11")
@pytest.mark.parametrize("u,expect", [
    ("現在用的舊系統資料可以匯進來嗎？包含房東、租客、合約、歷史帳單", True), ("那物件跟合約呢？", True),
    ("所以合約也能匯？", True), ("可不可以線上簽約", True), ("有沒有600戶以上的客戶", True),
    ("我們公司管180間", False), ("個人房東", False), ("收租對帳很亂", False),
])
def test_looks_like_question_closed_markers(u, expect):
    assert looks_like_question(u) is expect


@pytest.mark.req("presales-grounding-gate:2.11")
def test_split_declaratives_separates_statement_from_question():
    decl, ques = split_declaratives(FABRICATED_Q)
    assert decl.startswith("我們的系統支援租客批次匯入") and "合約和歷史帳單" in decl
    assert ques == "請問您還有其他想了解的功能嗎？"
    assert split_declaratives("請問您管理幾間？") == ("", "請問您管理幾間？")
    assert split_declaratives("了解。請問主要痛點是什麼？")[0] == "了解。" and len("了解。") < ASK_DECLARATIVE_MIN_CHARS


@pytest.mark.req("presales-grounding-gate:2.11")
def test_ask_is_answering_only_when_user_asked_and_brain_stated():
    assert ask_is_answering("所以合約也能匯？", FABRICATED_Q) is True
    assert ask_is_answering("所以合約也能匯？", "請問您目前用什麼系統？") is False          # 純反問
    assert ask_is_answering("我們公司管180間", "180 間的規模收租對帳不輕鬆。請問主要痛點是什麼？") is False   # 使用者沒在問
    assert ask_is_answering("那物件跟合約呢？", "了解。請問您想先看哪個功能？") is False        # 招呼語 < 門檻


# ── 引擎行為 ────────────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:2.11")
async def test_ask_with_stated_answer_and_grounding_becomes_extractive(snapshots):
    eng = _engine([{"answer": KB_3357, "similarity": 0.7}])
    stub_step(eng.optimizer, _ask(FABRICATED_Q))
    r = await eng.handle("backtest_session_ag1", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"].startswith(KB_3357) and "歷史帳單" not in r["answer"] and "還有其他想了解" not in r["answer"]
    assert r["handoff"]["reason"] == "partial_grounding"
    eng.optimizer.synthesize_presales_answer.assert_not_called()
    assert snapshots[-1]["presales"]["path"] == "extract"


@pytest.mark.req("presales-grounding-gate:2.11")
async def test_ask_with_stated_answer_and_no_grounding_becomes_handoff(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, _ask("是的，合約也能批次匯入，這樣可以讓您更方便地管理所有資料。請問您還有其他想了解的功能嗎？"))
    r = await eng.handle("backtest_session_ag2", "anon", 0, "所以合約也能匯？", CFG, start_if_absent=True)
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and r["handoff"]["reason"] == "no_grounding"
    assert snapshots[-1]["presales"]["path"] == "ask"


@pytest.mark.req("presales-grounding-gate:2.11")
async def test_pure_counter_question_passes_untouched(snapshots):
    eng = _engine([{"answer": KB_3357, "similarity": 0.7}])
    stub_step(eng.optimizer, _ask("請問您目前用什麼系統管理？"))
    r = await eng.handle("backtest_session_ag3", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"] == "請問您目前用什麼系統管理？" and r.get("handoff") is None
    eng.retriever.retrieve.assert_not_called()


@pytest.mark.req("presales-grounding-gate:2.11")
async def test_non_question_user_turn_keeps_brain_preamble(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, _ask("180 間的規模，收租對帳應該不輕鬆。請問目前最花時間的是哪一塊？"))
    r = await eng.handle("backtest_session_ag4", "anon", 0, "我們公司管180間", CFG, start_if_absent=True)
    assert r["answer"].startswith("180 間的規模") and r.get("handoff") is None
    eng.retriever.retrieve.assert_not_called()


@pytest.mark.req("presales-grounding-gate:4.2")
async def test_extractive_kb_text_mentioning_staff_gets_handoff(snapshots):
    """E1：知識原文自帶「專人」（3611）⇒ 抽取式回覆的 handoff 也要非 null（入口提示句），文字不改。"""
    eng = _engine([{"answer": KB_3611, "similarity": 0.9}])
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "試用", "extracted_fields": {}, "fact_class": "feature"})
    r = await eng.handle("backtest_session_ag5", "anon", 0, "可以免費試用嗎", CFG, start_if_absent=True)
    assert r["answer"] == KB_3611
    assert r["handoff"]["reason"] == "llm_mentioned_handoff" and r["handoff"]["message"] == cc.PRESALES_HANDOFF_ENTRY_HINT


# ── 子句層（D6 上線探針：斷言與反問同一句）──────────────────────────────────
CLAUSE_Q = "物件和合約的資料也可以匯入，您還有其他想了解的功能或需求嗎？"


@pytest.mark.req("presales-grounding-gate:2.11")
def test_strip_declarative_clauses_removes_leading_assertion():
    decl, q_only = strip_declarative_clauses(CLAUSE_Q)
    assert decl == "物件和合約的資料也可以匯入" and q_only == "您還有其他想了解的功能或需求嗎？"
    assert strip_declarative_clauses("請問您管理幾間，主要在哪個城市？") == ("", "請問您管理幾間，主要在哪個城市？")   # 前綴子句含問句標記「幾」⇒ 不是作答
    assert strip_declarative_clauses("了解，請問主要痛點？") == ("", "了解，請問主要痛點？")                         # 招呼 < 門檻


@pytest.mark.req("presales-grounding-gate:2.11")
def test_analyze_ask_distinguishes_sentence_and_clause():
    assert analyze_ask("那物件跟合約呢？", FABRICATED_Q)[0] == "sentence"
    assert analyze_ask("那物件跟合約呢？", CLAUSE_Q) == ("clause", "您還有其他想了解的功能或需求嗎？", "物件和合約的資料也可以匯入")
    assert analyze_ask("那物件跟合約呢？", "請問您目前用什麼系統？") is None
    assert analyze_ask("我們公司管180間", CLAUSE_Q) is None


@pytest.mark.req("presales-grounding-gate:2.11")
async def test_clause_assertion_with_grounding_becomes_extractive(snapshots):
    eng = _engine([{"answer": KB_3357, "similarity": 0.7}])
    stub_step(eng.optimizer, _ask(CLAUSE_Q))
    r = await eng.handle("backtest_session_ag6", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"].startswith(KB_3357) and "也可以匯入" not in r["answer"]


@pytest.mark.req("presales-grounding-gate:2.11")
async def test_clause_assertion_without_grounding_is_stripped_not_blocked(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, _ask(CLAUSE_Q))
    r = await eng.handle("backtest_session_ag7", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"] == "您還有其他想了解的功能或需求嗎？" and r.get("handoff") is None
    assert snapshots[-1]["presales"]["path"] == "ask" and snapshots[-1]["presales"]["grounding_hits"] == 0


@pytest.mark.req("presales-grounding-gate:2.11")
async def test_clause_that_is_a_handoff_cue_becomes_fixed_sentence(snapshots):
    """剝掉的子句含轉人詞 ⇒ 不是事實斷言而是轉人線索；沒知識時走固定句＋handoff（不能剝掉就丟）。"""
    eng = _engine([])
    stub_step(eng.optimizer, _ask("這部分要由專人為您說明，請問您管理幾戶呢？"))
    r = await eng.handle("backtest_session_ag8", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and r["handoff"]["reason"] == "no_grounding"
