"""TDD：C4b 斷言量尺本身（spec conversational-routing-execution 任務 6.1，R3.2）。

⚠️ **本組驗的是量尺，不是被測系統**——先證明尺會咬，6.2／6.3 的綠燈才有意義。
⚠️ 本檔**零 OpenAI 成本**：所有「回答」都是本檔自己寫的字串，用來測尺的判定，
   不是拿來證明 brain——證明 brain 是 6.2 的事，且必須用真 LLM。

四條結構性禁令都以拋例外實現：
1. `answer_must_contain` 為空 → 拒絕（未驗「有沒有用 grounding」）；
2. 待驗字面出現在使用者輸入 → 拒絕（測試自己餵進去的不算引用）；
3. 字面過長或含句讀 → 拒絕（鎖措辭必產生假紅）；
4. `generic_fallback_markers` 為空 → 拒絕（未驗「是否退回泛用答案」）。
"""
import pytest

from tests.support.brain_grounding import (
    AnswerTextRequiredError,
    BrainGroundingAssertion,
    FallbackNotAssertedError,
    GroundingUseNotAssertedError,
    LiteralFedByTestError,
    ProvenanceNotDeclaredError,
    WordingLockError,
    assert_brain_uses_grounding,
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
    assert out["quoted_literals"]["7,500"] in ("7,500", "7500")
    assert out["fixture_bill_id"] == 900003


@pytest.mark.req("conversational-routing-execution:3.2")
def test_report_carries_actual_quoted_literal():
    """6.3 要求逐面向列出**實際引用字面**——摘要必須帶得出來，不能只回過/不過。"""
    out = assert_brain_uses_grounding("金額 7500 元", _spec())
    assert out["quoted_literals"] == {"7,500": "7500"}
    assert out["literal_provenance"]["7,500"].endswith("900003.total")


# ── 尺會咬：三種紅各自可辨 ──────────────────────────────────────────────────
@pytest.mark.req("conversational-routing-execution:3.2")
def test_bites_when_value_absent():
    """完全沒引用該筆的值 → 紅（這正是 C4b 要抓的主症狀）。"""
    with pytest.raises(AssertionError, match="未引用該筆實際值"):
        assert_brain_uses_grounding("這張帳單目前待對帳，等撥付日即會入帳。", _spec())


@pytest.mark.req("conversational-routing-execution:3.2")
def test_bites_when_quoting_another_record():
    """引用到別筆 fixture 的值 → 紅，即使該筆的值也在。"""
    with pytest.raises(AssertionError, match="引用到別筆"):
        assert_brain_uses_grounding("金額 7,500，另一張是 18,000。", _spec())


@pytest.mark.req("conversational-routing-execution:3.2")
def test_bites_on_generic_fallback_marker():
    """退回泛用答案的標記 → 紅（第二維度，與第一維度正交）。"""
    with pytest.raises(AssertionError, match="退回泛用答案"):
        assert_brain_uses_grounding("金額 7,500。一般來說帳單問題請洽客服。", _spec())


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
def test_refuses_literal_without_provenance():
    with pytest.raises(ProvenanceNotDeclaredError):
        _spec(answer_must_contain=(("7,500",),), literal_provenance={})


@pytest.mark.req("conversational-routing-execution:3.2")
@pytest.mark.parametrize("bad", [
    {"grounding": "900003｜金額 7,500"},          # 誤傳 grounding 物件
    {"answer": "金額 7,500"},                     # 誤傳回應物件
    12345,
])
def test_refuses_non_answer_text(bad):
    """C4a 的鏡像禁令：C4b 只吃回答文字；誤傳 grounding 會讓兩層證據混為一談。"""
    with pytest.raises(AnswerTextRequiredError):
        assert_brain_uses_grounding(bad, _spec())


@pytest.mark.req("conversational-routing-execution:3.2")
def test_foil_literals_merge_with_declared_ones():
    """別筆字面可由呼叫端補（如自 fixture 表算出的 foil），與宣告的合併判定。"""
    with pytest.raises(AssertionError, match="引用到別筆"):
        assert_brain_uses_grounding("金額 7,500，期間 2026/08/01 起。", _spec(),
                                    foil_literals=("2026/08/01",))
