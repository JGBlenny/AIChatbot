"""TDD：C4b 斷言量尺本身（spec conversational-routing-execution 任務 6.1，R3.2）。

**對象為 v2**（`c4b-ruler-v2-amendment.md`）。v1 曾凍結但未執行，於首次付費量測前被
audit 反證；本檔鎖住 v2 的三項修訂：

```text
A  標題不再是正向要求        → identity 屬 C4a OB-3，C4b 不重驗
B  方向性字面不得阻斷        → 拿不出別筆 fixture 出處者，結構上進不了阻斷集
C  過與不過都留下回答原文    → 否則 ruler_false_red 與 wrong_direction 分不開
```

⚠️ **本組驗的是量尺，不是被測系統**——先證明尺會咬、且**只咬該咬的**，
6.2／6.3 的綠燈才有意義。
⚠️ 本檔**零 OpenAI 成本**：所有「回答」都是本檔自己寫的字串。
"""
import pytest

from tests.support.brain_grounding import (
    AnswerTextRequiredError,
    BrainGroundingAssertion,
    BrainGroundingFailure,
    ContradictoryFlagError,
    FallbackNotAssertedError,
    FoilProvenanceNotDeclaredError,
    GroundingUseNotAssertedError,
    LiteralFedByTestError,
    ProvenanceNotDeclaredError,
    WordingLockError,
    assert_brain_uses_grounding,
    evaluate_brain_grounding,
)

pytestmark = pytest.mark.unit

TURNS = ("幫我查點退帳單金額", "900003")


def _spec(**kw):
    base = dict(
        case="c4b-diag-01",
        execution_face="bill_diagnosis",
        fixture_bill_id=900003,
        user_turns=TURNS,
        answer_must_contain=(("7,500", "7500"),),
        answer_must_not_contain=("18,000", "1,200"),
        generic_fallback_markers=("請洽客服", "一般來說"),
        literal_provenance={"7,500": "fixtures 900003.total"},
        foil_provenance={"18,000": "fixtures 900001.total", "1,200": "fixtures 900002.total"},
    )
    base.update(kw)
    return BrainGroundingAssertion(**base)


# ── 尺會給過：措辭不同但值對 ────────────────────────────────────────────────
@pytest.mark.req("conversational-routing-execution:3.2")
@pytest.mark.parametrize("answer", [
    "這張點退帳單的金額是 NT$ 7,500，目前待對帳。",
    "帳單金額為 7500 元喔，還在等金流對帳。",
    "金額：7,500（系統存值）",
])
def test_passes_regardless_of_wording(answer):
    """不鎖措辭：同一個值的不同寫法都要過，否則真 LLM 必假紅。"""
    out = assert_brain_uses_grounding(answer, _spec())
    assert out["passed"] is True
    assert out["matched_spans"][0]["literal"] in ("7,500", "7500")


@pytest.mark.req("conversational-routing-execution:3.2")
def test_answer_that_only_answers_the_question_passes():
    """**A 項回歸**：只回答被問到的值、未複述帳單標題 → 必須過。

    v1 曾要求回答出現標題（如「2026年9月點退結算」），那是在 C4b 這一層重驗
    identity（已由 C4a OB-3 機器斷言），且會誤殺完全正確的回答。
    """
    out = assert_brain_uses_grounding("金額是 7,500 元。", _spec())
    assert out["passed"] is True


# ── C：過與不過都留下原文與命中片段 ─────────────────────────────────────────
@pytest.mark.req("conversational-routing-execution:3.2")
def test_record_keeps_raw_answer_verbatim_on_pass():
    answer = "金額 7500 元　（含空白與全形符號，原文不得被正規化）"
    out = assert_brain_uses_grounding(answer, _spec())
    assert out["raw_answer"] == answer


@pytest.mark.req("conversational-routing-execution:3.2")
def test_record_keeps_raw_answer_and_spans_on_fail():
    """紅燈也要留原文——否則 6.3 無法把 ruler_false_red 與真失敗分開。"""
    answer = "這張帳單金額 7,500，另一張是 18,000。"
    with pytest.raises(BrainGroundingFailure) as ei:
        assert_brain_uses_grounding(answer, _spec())
    rec = ei.value.record
    assert rec["raw_answer"] == answer
    assert rec["violated_dimensions"] == ["wrong_instance"]
    assert rec["wrong_instance_hits"][0]["literal"] == "18,000"


@pytest.mark.req("conversational-routing-execution:3.2")
def test_matched_span_context_preserves_negation():
    """命中片段附前後文窗：「不是」必須留得下來，單一 token 不足以裁決。"""
    spec = _spec(case="c4b-anom-02", fixture_bill_id=900003,
                 user_turns=("這張帳單現在的狀態是什麼", "900003"),
                 answer_must_contain=(("待對帳",),),
                 answer_must_not_contain=(),
                 foil_provenance={},
                 adjudication_flags=("待繳費",),
                 literal_provenance={"待對帳": "fixtures 900003.status→STATUS_LABELS"})
    out = evaluate_brain_grounding("目前是待對帳，不是待繳費。", spec)
    assert out["passed"] is True
    assert "不是" in out["adjudication_hits"][0]["context"]


# ── B：方向性字面只記錄、不判紅 ─────────────────────────────────────────────
@pytest.mark.req("conversational-routing-execution:3.2")
def test_adjudication_flag_is_recorded_but_never_blocks():
    """**B 項回歸**：方向性表述片段命中 → 仍然通過，只把該次交 6.3 判讀。"""
    spec = _spec(case="c4b-diag-02", fixture_bill_id=900001,
                 user_turns=("這張帳單現在還能不能收回", "900001"),
                 answer_must_contain=(("待繳費",),),
                 answer_must_not_contain=("待對帳",),
                 foil_provenance={"待對帳": "fixtures 900003.status→STATUS_LABELS"},
                 adjudication_flags=("無法收回", "不能收回"),
                 literal_provenance={"待繳費": "fixtures 900001.status→STATUS_LABELS"})
    out = assert_brain_uses_grounding(
        "已失效的帳單無法收回，但這張還在待繳費，可以收回。", spec)
    assert out["passed"] is True
    assert [h["literal"] for h in out["adjudication_hits"]] == ["無法收回"]


@pytest.mark.req("conversational-routing-execution:3.2")
def test_blocking_foil_without_other_fixture_provenance_is_refused():
    """**B 項的機制落點**：拿不出別筆出處的字面，結構上進不了阻斷集。"""
    with pytest.raises(FoilProvenanceNotDeclaredError, match="無法收回"):
        _spec(answer_must_not_contain=("無法收回",), foil_provenance={})


@pytest.mark.req("conversational-routing-execution:3.2")
def test_literal_cannot_be_both_blocking_and_adjudication():
    with pytest.raises(ContradictoryFlagError):
        _spec(adjudication_flags=("18,000",))


# ── 尺仍會咬：三種真紅各自可辨 ──────────────────────────────────────────────
@pytest.mark.req("conversational-routing-execution:3.2")
def test_bites_when_value_absent():
    with pytest.raises(BrainGroundingFailure) as ei:
        assert_brain_uses_grounding("這張帳單目前待對帳，等撥付日即會入帳。", _spec())
    assert ei.value.record["violated_dimensions"] == ["value_not_used"]


@pytest.mark.req("conversational-routing-execution:3.2")
def test_bites_on_generic_fallback_marker():
    with pytest.raises(BrainGroundingFailure) as ei:
        assert_brain_uses_grounding("金額 7,500。一般來說帳單問題請洽客服。", _spec())
    assert ei.value.record["violated_dimensions"] == ["generic_fallback"]


# ── 結構性禁令 ──────────────────────────────────────────────────────────────
@pytest.mark.req("conversational-routing-execution:3.2")
def test_refuses_empty_must_contain():
    with pytest.raises(GroundingUseNotAssertedError):
        _spec(answer_must_contain=())


@pytest.mark.req("conversational-routing-execution:3.2")
def test_refuses_empty_fallback_markers():
    with pytest.raises(FallbackNotAssertedError):
        _spec(generic_fallback_markers=())


@pytest.mark.req("conversational-routing-execution:3.2")
def test_refuses_literal_fed_by_the_test_itself():
    """帳單編號由使用者輸入提供 → 回答裡出現它不是引用證據，尺必須拒收。"""
    with pytest.raises(LiteralFedByTestError, match="900003"):
        _spec(answer_must_contain=(("900003",),),
              literal_provenance={"900003": "fixtures 900003.id"})


@pytest.mark.req("conversational-routing-execution:3.2")
@pytest.mark.parametrize("literal", [
    "這張帳單的金額是 NT$ 7,500 元整",   # 過長
    "金額為 7,500，待對帳",              # 含句讀
])
def test_refuses_wording_lock(literal):
    with pytest.raises(WordingLockError):
        _spec(answer_must_contain=((literal,),), literal_provenance={literal: "x"})


@pytest.mark.req("conversational-routing-execution:3.2")
def test_wording_lock_guard_also_applies_to_blocking_foils():
    """阻斷型反向同樣不得是句子——否則 B 項會從反向那一側破功。"""
    with pytest.raises(WordingLockError):
        _spec(answer_must_not_contain=("這張帳單已失效，無法收回",),
              foil_provenance={"這張帳單已失效，無法收回": "x"})


@pytest.mark.req("conversational-routing-execution:3.2")
def test_refuses_literal_without_provenance():
    with pytest.raises(ProvenanceNotDeclaredError):
        _spec(answer_must_contain=(("7,500",),), literal_provenance={})


@pytest.mark.req("conversational-routing-execution:3.2")
@pytest.mark.parametrize("bad", [
    {"grounding": "900003｜金額 7,500"},
    {"answer": "金額 7,500"},
    12345,
])
def test_refuses_non_answer_text(bad):
    with pytest.raises(AnswerTextRequiredError):
        assert_brain_uses_grounding(bad, _spec())


@pytest.mark.req("conversational-routing-execution:3.2")
def test_foil_literals_merge_with_declared_ones():
    """別筆字面可由呼叫端自 fixture 表算出補入，與宣告的合併判定。"""
    with pytest.raises(BrainGroundingFailure) as ei:
        assert_brain_uses_grounding("金額 7,500，期間 2026/08/01 起。", _spec(),
                                    foil_literals=("2026/08/01",))
    assert ei.value.record["wrong_instance_hits"][0]["literal"] == "2026/08/01"
