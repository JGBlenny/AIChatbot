"""unit 層：`_converge_grounding` 走 `retrieve()`＋門檻、回結構化結果（design.md 元件 2）。需求 1.1、1.4、1.5、5.1。

⛔ 空 grounding 不再塞占位字串（那是 P0-1 的病灶）；門檻值必須來自 presales_gate 唯一讀值點；retrieve 例外＝空（fail-closed）。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import presales_gate as pg
from services.conversational_config import ConversationalConfig
from services.conversational_engine import ConversationalEngine, ConvergeGrounding

pytestmark = pytest.mark.unit
CFG = ConversationalConfig(key="presales", persona_role="prospect",
                           grounding_scope={"target_user": "prospect", "mode": "b2b"})
STATE = {"collected_fields": {"identity": "個人房東"}, "dialog": [{"u": "舊系統的資料能匯進來嗎？", "a": "可以批次匯入"}]}


def _engine(hits):
    eng = ConversationalEngine(db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
                               get_system_context=AsyncMock(return_value="md"), rules_loader=AsyncMock(return_value="規則"))
    eng.retriever.retrieve = AsyncMock(return_value=hits)
    eng.retriever._vector_search = AsyncMock(side_effect=AssertionError("⛔ 不得再走 _vector_search（門檻參數是死的）"))
    return eng


# ── 門檻與呼叫形狀（R1.1）─────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:1.1")
async def test_vector_path_uses_retrieve_with_presales_threshold(monkeypatch):
    monkeypatch.setenv("PRESALES_GROUNDING_THRESHOLD", "0.61")
    eng = _engine([{"answer": "A1", "similarity": 0.9, "score_source": "rerank"}])
    cg = await eng._converge_grounding(STATE, "匯入", "那物件跟合約呢？", CFG, "answer")
    kw = eng.retriever.retrieve.await_args.kwargs
    assert kw["similarity_threshold"] == pytest.approx(0.61) == pg.presales_threshold()
    assert kw["target_user"] == "prospect" and kw["mode"] == "b2b" and kw["top_k"] == 3
    assert isinstance(cg, ConvergeGrounding) and cg.threshold == pytest.approx(0.61)


@pytest.mark.req("presales-grounding-gate:1.1")
async def test_hits_are_joined_and_counted():
    eng = _engine([{"answer": "A1", "similarity": 0.9, "score_source": "rerank"},
                   {"answer": "A2", "similarity": 0.7, "score_source": "rerank"},
                   {"answer": "", "similarity": 0.6}])                     # 空 answer 不算
    cg = await eng._converge_grounding(STATE, None, "問題", CFG, "answer")
    assert cg.hits == 2 and cg.empty is False and cg.text == "A1\n\nA2" and cg.score_source == "rerank"
    assert cg.cta_mode == "suppress" and cg.ctx is None


# ── 空 grounding（R1.4）────────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:1.4")
@pytest.mark.parametrize("kind", ["answer", "recommend"])
async def test_zero_hits_is_empty_without_placeholder(kind):
    eng = _engine([])
    cg = await eng._converge_grounding(STATE, None, "有沒有 600 戶客戶", CFG, kind)
    assert cg.empty is True and cg.text == "" and cg.hits == 0
    assert "依系統脈絡" not in cg.text                                     # ⛔ 舊占位字串不得回來


@pytest.mark.req("presales-grounding-gate:1.5")
async def test_retrieve_exception_is_fail_closed():
    eng = _engine([])
    eng.retriever.retrieve = AsyncMock(side_effect=RuntimeError("retriever down"))
    cg = await eng._converge_grounding(STATE, None, "問題", CFG, "answer")
    assert cg.empty is True and cg.text == "" and cg.hits == 0 and cg.error == "RuntimeError"


# ── 上一輪問句併入（R5.1）─────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:5.1")
async def test_prev_user_message_is_merged_into_query_for_answer_kind():
    eng = _engine([])
    await eng._converge_grounding(STATE, "匯入", "那物件跟合約呢？", CFG, "answer",
                                  prev_user_message="舊系統的資料能匯進來嗎？")
    q = eng.retriever.retrieve.await_args.kwargs["query"]
    assert "舊系統的資料能匯進來嗎" in q and "那物件跟合約呢" in q and q.index("舊系統") < q.index("那物件")


@pytest.mark.req("presales-grounding-gate:5.1")
async def test_prev_user_message_ignored_for_recommend_and_when_none():
    eng = _engine([])
    await eng._converge_grounding(STATE, "方案", "適合我嗎", CFG, "recommend", prev_user_message="上一句")
    assert "上一句" not in eng.retriever.retrieve.await_args.kwargs["query"]
    await eng._converge_grounding(STATE, "匯入", "那物件跟合約呢？", CFG, "answer", prev_user_message=None)
    assert eng.retriever.retrieve.await_args.kwargs["query"].startswith("那物件跟合約呢")


# ── 追問時本輪問句自身也要過門檻（e2e 回測 N-1：併入上一輪撈到相鄰知識 ⇒ 假放行）─────────────
@pytest.mark.req("presales-grounding-gate:5.1")
async def test_merged_query_hit_but_own_question_miss_is_empty():
    eng = _engine([])
    async def _retrieve(query, **kw):
        return [{"answer": "個人房東方案", "similarity": 0.7}] if "舊系統" in query else []   # 併入上一輪才撈到
    eng.retriever.retrieve = AsyncMock(side_effect=_retrieve)
    cg = await eng._converge_grounding(STATE, "匯入", "那物件跟合約呢？", CFG, "answer", prev_user_message="舊系統的資料能匯進來嗎？")
    assert cg.empty is True and cg.hits == 0 and eng.retriever.retrieve.await_count == 2


@pytest.mark.req("presales-grounding-gate:5.1")
async def test_merged_query_hit_and_own_question_hit_is_kept():
    eng = _engine([])
    eng.retriever.retrieve = AsyncMock(return_value=[{"answer": "物件批次匯入", "similarity": 0.8, "score_source": "rerank"}])
    cg = await eng._converge_grounding(STATE, "匯入", "那物件呢？", CFG, "answer", prev_user_message="舊系統的資料能匯進來嗎？")
    assert cg.empty is False and cg.hits == 1 and eng.retriever.retrieve.await_count == 2


@pytest.mark.req("presales-grounding-gate:5.1")
async def test_no_prev_message_does_not_double_retrieve():
    eng = _engine([{"answer": "A", "similarity": 0.8}])
    await eng._converge_grounding(STATE, None, "問題", CFG, "answer")
    assert eng.retriever.retrieve.await_count == 1


# ── prepare 暴露 grounding_empty；answer∧空 ⇒ kind=handoff（3.2 分流，取代 3.1 的過渡占位）──
@pytest.mark.req("presales-grounding-gate:1.4")
async def test_prepare_exposes_grounding_empty_flag(monkeypatch):
    from tests.support.brain_stub import stub_step
    eng = _engine([])
    eng.get_state = AsyncMock(return_value=dict(STATE, asked_count=0))
    eng._save = AsyncMock()
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": "answer", "converge_topic": "客戶",
                              "extracted_fields": {}, "fact_class": "customer_reference"})
    d = await eng.prepare("backtest_session_x", "anon", 0, "有沒有 600 戶客戶", CFG, start_if_absent=True)
    assert d and d["kind"] == "handoff" and d["grounding_empty"] is True and d["grounding_hits"] == 0
    assert "依系統脈絡" not in (d.get("grounding") or "")            # ⛔ 舊占位字串不得回來
