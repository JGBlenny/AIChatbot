"""unit 層：押金二選一規則（design.md 元件 6／deposit_rule）。需求 6.1–6.6、10.3。

⛔ 鐵則：`deposit`（月數）與 `deposit_amount`（金額）不得同時非空，且任一 ⛔ 不得由另一方乘／除得出。
本檔含**突變控制**：把「deposit_amount ÷ rent 回填 deposit」注入後，不變式測試必須轉紅。
"""
import pytest

from services.ocr_mapping.deposit_rule import DepositDecision, assert_deposit_exclusive, decide_deposit
from services.ocr_mapping.models import FieldSource

pytestmark = pytest.mark.unit


# ── R6.1 金額原文 ─────────────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:6.1")
def test_amount_text_sets_type_1_and_amount_only():
    d = decide_deposit("押金新台幣貳萬柒仟陸佰元整", page=2, confidence=0.8)
    assert (d.deposit_type.value, d.deposit_type.jgb_value) == (1, 1)
    assert d.deposit_amount.value == 27600 and d.deposit_amount.source is FieldSource.ocr
    assert d.deposit.value is None and d.deposit.source is FieldSource.absent
    assert d.needs_confirmation is False
    assert_deposit_exclusive(d)


# ── R6.2 月數原文 ─────────────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:6.2")
@pytest.mark.parametrize("text,months", [("押金貳個月", 2), ("押金二個月租金", 2), ("押金為兩個月", 2), ("押金 3 個月", 3)])
def test_months_text_sets_type_0_and_months_only(text, months):
    d = decide_deposit(text, page=1, confidence=0.7)
    assert d.deposit_type.value == 0 and d.deposit.value == months
    assert d.deposit_amount.source is FieldSource.absent
    assert_deposit_exclusive(d)


# ── R6.3 兩者並存 → 金額為準、月數進 raw、列 needs_confirmation ────────────────
@pytest.mark.req("documind-ocr-mapping:6.3")
def test_both_present_prefers_amount_and_flags_confirmation():
    d = decide_deposit("押金貳個月，計新台幣貳萬柒仟陸佰元整", page=1, confidence=0.7)
    assert d.deposit_type.value == 1 and d.deposit_amount.value == 27600
    assert d.deposit.value is None and "貳個月" in (d.deposit_type.raw or "")
    assert d.needs_confirmation is True
    assert_deposit_exclusive(d)


# ── R6.4 判不出 → 三欄 absent、deposit_type 待確認 ───────────────────────────
@pytest.mark.req("documind-ocr-mapping:6.4")
@pytest.mark.parametrize("text", [None, "", "押金另議", "押金依雙方約定", "租金每月壹萬元整"])
def test_unparseable_deposit_is_all_absent_and_flagged(text):
    d = decide_deposit(text, page=1, confidence=0.5)
    assert all(f.source is FieldSource.absent for f in (d.deposit_type, d.deposit, d.deposit_amount))
    assert d.needs_confirmation is True


# ── R6.6 三欄各自帶 source ────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:6.6")
def test_each_of_three_fields_carries_its_own_source_and_page():
    d = decide_deposit("押金新台幣貳萬柒仟陸佰元整", page=2, confidence=0.8)
    assert d.deposit_type.page == 2 and d.deposit_amount.page == 2
    assert {d.deposit_type.source, d.deposit_amount.source} == {FieldSource.ocr}
    assert d.deposit.source is FieldSource.absent and d.deposit.page is None


# ── R6.5 ⛔ 不推算——不變式＋突變控制（需求 10.3）──────────────────────────────
def _mutant_decide_deposit(text: str, rent: int, *, page: int, confidence: float) -> DepositDecision:
    """注入版本：把 deposit_amount ÷ rent 回填 deposit——這正是業主曾寫過又拿掉的推算。"""
    d = decide_deposit(text, page=page, confidence=confidence)
    if d.deposit_amount.value and d.deposit.value is None:
        derived = d.deposit.model_copy(update={"value": d.deposit_amount.value // rent, "jgb_value": d.deposit_amount.value // rent,
                                               "source": FieldSource.derived, "page": page})
        return d._replace(deposit=derived)
    return d


@pytest.mark.req("documind-ocr-mapping:6.5")
def test_invariant_rejects_derived_months_from_amount():
    with pytest.raises(AssertionError):
        assert_deposit_exclusive(_mutant_decide_deposit("押金新台幣貳萬柒仟陸佰元整", 13800, page=1, confidence=0.8))


@pytest.mark.req("documind-ocr-mapping:6.5")
def test_invariant_rejects_derived_amount_from_months():
    d = decide_deposit("押金貳個月", page=1, confidence=0.7)
    mutated = d._replace(deposit_amount=d.deposit_amount.model_copy(update={"value": 2 * 13800, "source": FieldSource.derived}))
    with pytest.raises(AssertionError):
        assert_deposit_exclusive(mutated)


@pytest.mark.req("documind-ocr-mapping:10.3")
def test_mutation_control_actually_bites_positive_control():
    # 正對照：未注入的正常結果必須通過不變式——證明尺不是永遠紅
    assert_deposit_exclusive(decide_deposit("押金新台幣貳萬柒仟陸佰元整", page=1, confidence=0.8))
