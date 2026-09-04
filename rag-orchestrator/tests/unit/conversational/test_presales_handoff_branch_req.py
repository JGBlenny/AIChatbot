"""unit 層：引擎分流——事實題空 grounding 走 handoff、不進 optimizer（design.md 元件 3）。
需求 2.1、2.2、2.3、2.4、2.6、4.2、5.4、7.1、7.2、7.3。

⛔ 這是整個 spec 的核心：占位字串不得再讓 LLM 在無知識時生成事實。
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
                           answer_rules=cc.PRESALES_ANSWER_RULES, cta_rules=cc.PRESALES_CTA_RULES,
                           handoff_message=cc.PRESALES_HANDOFF_MESSAGE)
Q = "你們現在服務的案場裡，有沒有600戶以上、商辦加店面混合的客戶"


def _engine(hits, *, dialog=None, last_topic=None, llm_text="知識裡說可以。"):
    eng = ConversationalEngine(db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
                               get_system_context=AsyncMock(return_value="md"), rules_loader=AsyncMock(return_value="規則"))
    eng.retriever.retrieve = AsyncMock(return_value=hits)
    state = {"collected_fields": {"identity": "個人房東"}, "asked_count": 0, "dialog": dialog or []}
    if last_topic is not None:
        state["last_converge_topic"] = last_topic
    eng.get_state = AsyncMock(return_value=state)
    eng._save = AsyncMock()
    eng.optimizer.synthesize_presales_answer = MagicMock(return_value=llm_text)
    return eng


def _brain(eng, kind="answer", fact_class="customer_reference", topic="客戶"):
    stub_step(eng.optimizer, {"action": "converge", "converge_kind": kind, "converge_topic": topic,
                              "extracted_fields": {}, "fact_class": fact_class})


@pytest.fixture
def snapshots(monkeypatch):
    got = []
    monkeypatch.setattr(um, "set_decision", lambda snapshot=None, facet_event=None: got.append(snapshot))
    return got


# ── answer ∧ 空 grounding ⇒ handoff、不進 optimizer（R2.1／2.2／2.6）─────────────
@pytest.mark.req("presales-grounding-gate:2.1")
async def test_answer_with_empty_grounding_returns_fixed_sentence_without_llm(snapshots):
    eng = _engine([]); _brain(eng)
    r = await eng.handle("backtest_session_h1", "anon", 0, Q, CFG, start_if_absent=True)
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and r["conversational"] is True and r["converged"] is False
    assert r["handoff"] == {"reason": "sensitive_no_grounding", "fact_class": "customer_reference",
                            "channel": "line_official", "message": cc.PRESALES_HANDOFF_MESSAGE}
    eng.optimizer.synthesize_presales_answer.assert_not_called()


@pytest.mark.req("presales-grounding-gate:2.2")
async def test_non_sensitive_class_uses_no_grounding_reason_same_sentence(snapshots):
    eng = _engine([]); _brain(eng, fact_class="feature")
    r = await eng.handle("backtest_session_h2", "anon", 0, "可以自動開發票嗎", CFG, start_if_absent=True)
    assert r["handoff"]["reason"] == "no_grounding" and r["answer"] == cc.PRESALES_HANDOFF_MESSAGE


@pytest.mark.req("presales-grounding-gate:2.6")
async def test_handoff_is_deterministic_across_sessions(snapshots):
    outs = []
    for i in range(3):
        eng = _engine([]); _brain(eng)
        outs.append(await eng.handle(f"backtest_session_d{i}", "anon", 0, Q, CFG, start_if_absent=True))
    assert len({o["answer"] for o in outs}) == 1 and len({str(o["handoff"]) for o in outs}) == 1


# ── answer ∧ 有 grounding ⇒ 現行合成（temp 由 cta_mode=suppress 守）＋後置掃描（R2.3／4.2）──
@pytest.mark.req("presales-grounding-gate:2.3")
async def test_answer_with_hits_synthesizes_with_suppress_and_no_handoff(snapshots):
    # D6 後：fact_class≠other 且有知識 ⇒ 抽取式（見 test_presales_extractive_req）；LLM 事實路徑只剩 fact_class=other
    eng = _engine([{"answer": "電子發票可自動開立", "similarity": 0.9, "score_source": "rerank"}]); _brain(eng, fact_class="other", topic="發票")
    r = await eng.handle("backtest_session_h3", "anon", 0, "可以自動開發票嗎", CFG, start_if_absent=True)
    kw = eng.optimizer.synthesize_presales_answer.call_args
    assert kw.args[4] == "suppress" and "prev_turn" in kw.kwargs
    assert r["answer"] == "知識裡說可以。" and r.get("handoff") is None


@pytest.mark.req("presales-grounding-gate:4.2")
async def test_llm_text_mentioning_staff_gets_handoff_signal(snapshots):
    eng = _engine([{"answer": "A", "similarity": 0.9}], llm_text="細節建議洽專人確認。"); _brain(eng, fact_class="other")   # D6 後 LLM 事實路徑＝other
    r = await eng.handle("backtest_session_h4", "anon", 0, "問題", CFG, start_if_absent=True)
    assert r["handoff"]["reason"] == "llm_mentioned_handoff" and r["handoff"]["fact_class"] == "other"
    assert r["answer"] == "細節建議洽專人確認。"                      # ⛔ 只加訊號、不改文字
    assert r["handoff"]["message"] == cc.PRESALES_HANDOFF_ENTRY_HINT   # 入口提示，⛔ 不是「沒有可靠資料」句（實打抓到的矛盾）
    assert "沒有可靠資料" not in r["handoff"]["message"]


# ── recommend ∧ 空 grounding ⇒ 系統脈絡推薦，禁事實斷言（R2.4，D3）─────────────
@pytest.mark.req("presales-grounding-gate:2.4")
async def test_recommend_with_empty_grounding_still_synthesizes_with_fact_ban(snapshots):
    eng = _engine([]); _brain(eng, kind="recommend", fact_class="other", topic="方案")
    r = await eng.handle("backtest_session_h5", "anon", 0, "我適合哪種方案", CFG, start_if_absent=True)
    eng.optimizer.synthesize_presales_answer.assert_called_once()
    grounding_arg, _ctx, system_md, _q, cta = eng.optimizer.synthesize_presales_answer.call_args.args[:5]
    from services.conversational_engine import EMPTY_GROUNDING_MARK
    assert grounding_arg == EMPTY_GROUNDING_MARK and "⛔" not in grounding_arg      # 知識槽只放中性標記，⛔ 不塞指令（verifier A3）
    assert "依系統脈絡" not in grounding_arg                                       # 舊「導 demo/專人」占位不得回來
    assert "不得含客戶名單" in system_md and cta == "force"                         # 禁事實斷言由 answer_rules 供給
    assert r.get("handoff") is None and r["converged"] is True


# ── 同題重問 ⇒ 決定性重播 handoff、不呼叫 brain（e2e 第二輪 F2：重問時 brain 改問痛點或改判 other）──
@pytest.mark.req("presales-grounding-gate:2.8")
async def test_repeated_question_replays_handoff_without_brain(snapshots):
    eng = _engine([]); _brain(eng)
    r1 = await eng.handle("backtest_session_rp", "anon", 0, Q, CFG, start_if_absent=True)
    # 第二輪：把「已存」狀態餵回（含 handoff_log），brain 改成會問痛點
    saved = eng._save.await_args.args[1]
    eng.get_state = AsyncMock(return_value=saved)
    stub_step(eng.optimizer, {"action": "ask", "next_question": "請問您主要的管理痛點是什麼呢？", "extracted_fields": {}, "fact_class": "other"})
    r2 = await eng.handle("backtest_session_rp", "anon", 0, Q, CFG, start_if_absent=False)
    assert r2["answer"] == r1["answer"] == cc.PRESALES_HANDOFF_MESSAGE
    assert r2["handoff"] == r1["handoff"]                              # reason／fact_class 逐字相同
    eng.optimizer.conversational_step_result.assert_not_called()       # 重播不問 brain


@pytest.mark.req("presales-grounding-gate:2.8")
async def test_different_question_after_handoff_still_consults_brain(snapshots):
    eng = _engine([]); _brain(eng)
    await eng.handle("backtest_session_rq", "anon", 0, Q, CFG, start_if_absent=True)
    saved = eng._save.await_args.args[1]; eng.get_state = AsyncMock(return_value=saved)
    stub_step(eng.optimizer, {"action": "ask", "next_question": "請問您管理幾戶？", "extracted_fields": {}, "fact_class": "other"})
    r2 = await eng.handle("backtest_session_rq", "anon", 0, "我是個人房東", CFG, start_if_absent=False)
    eng.optimizer.conversational_step_result.assert_called_once()
    assert r2["answer"] == "請問您管理幾戶？"


# ── 事實題被 brain 判 recommend ⇒ 以 answer 處理（e2e 回測：匯入題走推薦路徑逃過閘門）────
@pytest.mark.req("presales-grounding-gate:2.1")
async def test_recommend_with_fact_class_is_treated_as_answer_and_gated(snapshots):
    eng = _engine([]); _brain(eng, kind="recommend", fact_class="feature", topic="匯入")
    r = await eng.handle("backtest_session_r1", "anon", 0, "舊系統資料可以匯進來嗎？含房東租客合約帳單", CFG, start_if_absent=True)
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and r["handoff"]["reason"] == "no_grounding"
    eng.optimizer.synthesize_presales_answer.assert_not_called()


@pytest.mark.req("presales-grounding-gate:2.4")
async def test_recommend_with_fact_class_other_stays_recommend(snapshots):
    eng = _engine([]); _brain(eng, kind="recommend", fact_class="other", topic="方案")
    r = await eng.handle("backtest_session_r2", "anon", 0, "我適合哪種方案", CFG, start_if_absent=True)
    eng.optimizer.synthesize_presales_answer.assert_called_once()
    assert eng.optimizer.synthesize_presales_answer.call_args.args[4] == "force" and r["converged"] is True


# ── ask 分支也要掃三詞（verifier F-1）；固定句不入對話史（A4）───────────────────
@pytest.mark.req("presales-grounding-gate:4.2")
async def test_ask_branch_with_staff_wording_carries_handoff_non_stream(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, {"action": "ask", "next_question": "這部分要由專人為您說明，請問您管理幾戶呢？",
                              "extracted_fields": {}, "fact_class": "other"})
    r = await eng.handle("backtest_session_a1", "anon", 0, "我想了解", CFG, start_if_absent=True)
    assert "專人" in r["answer"] and r["handoff"]["reason"] == "llm_mentioned_handoff"
    assert r["handoff"]["message"] == cc.PRESALES_HANDOFF_ENTRY_HINT


@pytest.mark.req("presales-grounding-gate:4.2")
async def test_ask_branch_scans_even_when_caller_passes_no_config(snapshots, monkeypatch):
    """續會話（第 2 輪起）呼叫端 config=None，由 state.config_key 還原——F-1 第二次實打抓到的漏掃。"""
    import services.conversational_engine as ce
    monkeypatch.setattr(ce, "get_config", AsyncMock(return_value=CFG))
    eng = _engine([])
    eng.get_state = AsyncMock(return_value={"config_key": "presales", "collected_fields": {}, "asked_count": 0, "dialog": []})
    stub_step(eng.optimizer, {"action": "ask", "next_question": "這部分要由專人為您說明，請問您管理幾戶呢？",
                              "extracted_fields": {}, "fact_class": "other"})
    r = await eng.handle("backtest_session_a4", "anon", 0, "那物件跟合約呢？", None, start_if_absent=False)
    # R2.11 後：使用者在問＋反問句前綴子句含轉人詞、沒知識 ⇒ 固定句＋no_grounding（config 仍須由 state.config_key 還原才組得出固定句）
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and r["handoff"]["reason"] == "no_grounding"


@pytest.mark.req("presales-grounding-gate:2.7")
async def test_inline_answer_without_grounding_is_replaced_by_fixed_sentence(snapshots):
    """岔題即答（ask＋inline_answer）也要過閘門：空 grounding ⇒ inline 換固定句、帶 handoff、next_question 照接。"""
    eng = _engine([])
    stub_step(eng.optimizer, {"action": "ask", "next_question": "請問您是個人房東還是二房東呢？",
                              "inline_answer": "物件和合約的資料也可以匯入。", "extracted_fields": {}, "fact_class": "feature"})
    r = await eng.handle("backtest_session_i1", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    # e2e 回測後改判：閘門觸發＝直接回 handoff 決策——固定句**逐字**、⛔ 不接 next_question（假事實曾從問句溜出、且破 R2.6）
    assert r["answer"] == cc.PRESALES_HANDOFF_MESSAGE and "也可以匯入" not in r["answer"]
    assert "請問您是個人房東" not in r["answer"]
    assert r["handoff"]["reason"] == "no_grounding" and r["handoff"]["fact_class"] == "feature"
    saved = eng._save.await_args.args[1]
    from services.conversational_engine import HANDOFF_DIALOG_MARK
    assert saved["dialog"][-1]["a"] == HANDOFF_DIALOG_MARK
    eng.optimizer.synthesize_presales_answer.assert_not_called()
    pres=[s["presales"] for s in snapshots if s and "presales" in s]
    assert pres and pres[-1]["path"] == "inline"


@pytest.mark.req("presales-grounding-gate:2.7")
async def test_inline_answer_with_grounding_is_kept(snapshots, monkeypatch):
    eng = _engine([{"answer": "物件可用 Excel 批次匯入", "similarity": 0.9, "score_source": "rerank"}])
    stub_step(eng.optimizer, {"action": "ask", "next_question": "請問規模？", "inline_answer": "物件可以批次匯入。",
                              "extracted_fields": {}, "fact_class": "feature"})
    monkeypatch.setenv("PRESALES_EXTRACTIVE", "1")
    r = await eng.handle("backtest_session_i2", "anon", 0, "物件呢？", CFG, start_if_absent=True)
    # D6 開：有知識的事實 inline ⇒ 抽取 top-1 知識原文（⛔ 不是 brain 的 inline 文字）；單項目問句無尾句、無 handoff
    assert r["answer"] == "物件可用 Excel 批次匯入" and r.get("handoff") is None


@pytest.mark.req("presales-grounding-gate:4.2")
async def test_ask_branch_without_staff_wording_has_no_handoff(snapshots):
    eng = _engine([])
    stub_step(eng.optimizer, {"action": "ask", "next_question": "請問您管理幾戶呢？", "extracted_fields": {}, "fact_class": "other"})
    r = await eng.handle("backtest_session_a2", "anon", 0, "我想了解", CFG, start_if_absent=True)
    assert "handoff" not in r or r["handoff"] is None


@pytest.mark.req("presales-grounding-gate:2.6")
async def test_handoff_turn_writes_marker_not_sentence_into_dialog(snapshots):
    from services.conversational_engine import HANDOFF_DIALOG_MARK
    eng = _engine([]); _brain(eng)
    await eng.handle("backtest_session_a3", "anon", 0, Q, CFG, start_if_absent=True)
    saved = eng._save.await_args.args[1]
    assert saved["dialog"][-1]["a"] == HANDOFF_DIALOG_MARK and cc.PRESALES_HANDOFF_MESSAGE not in saved["dialog"][-1]["a"]


# ── prev_turn 守門（R5.4）───────────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:5.4")
async def test_prev_turn_used_only_when_converge_topic_unchanged(snapshots):
    dialog = [{"u": "舊系統的資料能匯進來嗎？", "a": "可以批次匯入"}]
    eng = _engine([], dialog=dialog, last_topic="匯入"); _brain(eng, fact_class="feature", topic="匯入")
    await eng.handle("backtest_session_p1", "anon", 0, "那物件跟合約呢？", CFG, start_if_absent=True)
    assert "舊系統的資料能匯進來嗎" in eng.retriever.retrieve.await_args.kwargs["query"]
    eng2 = _engine([], dialog=dialog, last_topic="匯入"); _brain(eng2, fact_class="pricing", topic="價格")
    await eng2.handle("backtest_session_p2", "anon", 0, "那多少錢", CFG, start_if_absent=True)
    assert "舊系統" not in eng2.retriever.retrieve.await_args.kwargs["query"]      # 岔題不被拖走


@pytest.mark.req("presales-grounding-gate:5.4")
async def test_finalize_records_last_converge_topic(snapshots):
    eng = _engine([{"answer": "A", "similarity": 0.9}]); _brain(eng, fact_class="feature", topic="發票")
    await eng.handle("backtest_session_t1", "anon", 0, "可以自動開發票嗎", CFG, start_if_absent=True)
    saved = eng._save.await_args.args[1]
    assert saved.get("last_converge_topic") == "發票"


# ── 串流：handoff 整句一次（R2.1）────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:2.1")
async def test_stream_answer_yields_fixed_sentence_once_for_handoff(snapshots):
    eng = _engine([]); _brain(eng)
    d = await eng.prepare("backtest_session_s1", "anon", 0, Q, CFG, start_if_absent=True)
    assert d["kind"] == "handoff" and d["handoff"]["reason"] == "sensitive_no_grounding"
    chunks = [c async for c in eng.stream_answer(d)]
    assert chunks == [cc.PRESALES_HANDOFF_MESSAGE]
    eng.optimizer.synthesize_presales_answer_stream = MagicMock()
    eng.optimizer.synthesize_presales_answer_stream.assert_not_called()


# ── 計量與日誌（R7.1／7.2／7.3）─────────────────────────────────────────────────
@pytest.mark.req("presales-grounding-gate:7.1")
async def test_decision_snapshot_has_presales_namespace(snapshots):
    eng = _engine([]); _brain(eng)
    await eng.handle("backtest_session_m1", "anon", 0, Q, CFG, start_if_absent=True)
    pres = [s["presales"] for s in snapshots if s and "presales" in s]
    assert pres and pres[-1]["handoff"] == "sensitive_no_grounding" and pres[-1]["fact_class"] == "customer_reference"
    assert pres[-1]["grounding_hits"] == 0 and pres[-1]["path"] == "brain" and "threshold" in pres[-1]


@pytest.mark.req("presales-grounding-gate:7.3")
async def test_logs_do_not_leak_grounding_text(snapshots, capsys):
    eng = _engine([{"answer": "機密知識全文XYZ", "similarity": 0.9}]); _brain(eng, fact_class="feature")
    await eng.handle("backtest_session_l1", "anon", 0, "問題", CFG, start_if_absent=True)
    out = capsys.readouterr().out
    assert "[presales-gate]" in out and "hits=1" in out and "fact_class=feature" in out
    assert "機密知識全文XYZ" not in out
