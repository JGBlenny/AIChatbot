"""TDD：C4a 斷言量尺本身（spec conversational-routing-execution 任務 5.1，R3.1／R4.2）。

⚠️ **本組驗的是量尺，不是被測系統**——先證明尺會咬，5.3／5.4 的綠燈才有意義。

三條結構性禁令都以「拋例外」實現，不是只寫在註解裡：
1. 對最終回答文字下斷言 → 拒絕（腳本化 brain 的輸出是測試自己寫的）；
2. `required_grounding_facts` 為空 → 拒絕（未驗充分性）；
3. 未知 `closure_scope` → 拒絕（避免部分閉環被報成 full closure）。
"""
import pytest

from tests.support.chain_closure import (
    AnswerTextAssertionError,
    ChainClosureAssertion,
    ChainClosureScopeError,
    SufficiencyNotAssertedError,
    assert_chain_closure,
    extract_fact_keys,
)

pytestmark = pytest.mark.unit

GROUNDING = (
    "900001｜2026年8月租金\n"
    "【帳單狀態】待繳費\n"
    "【發送判定】已發送，不可再次發送\n"
    "【取消判定】可收回\n"
    "【手動到帳判定】尚未到帳"
)


def _spec(**kw):
    base = dict(
        case="bill_diagnosis/為什麼發不出去",
        grounding_must_contain=["900001"],
        required_grounding_facts=["發送判定"],
    )
    base.update(kw)
    return ChainClosureAssertion(**base)


# ── 事實鍵抽取 ────────────────────────────────────────────────────────────
def test_extract_fact_keys_reads_bracket_markers():
    assert extract_fact_keys(GROUNDING) == {
        "帳單狀態", "發送判定", "取消判定", "手動到帳判定"
    }


def test_extract_fact_keys_on_empty_grounding():
    assert extract_fact_keys("") == set()


# ── 通過路徑 ─────────────────────────────────────────────────────────────
def test_passes_when_both_dimensions_satisfied():
    result = assert_chain_closure(GROUNDING, _spec())
    assert result["case"].startswith("bill_diagnosis/")
    assert result["closure_scope"] == "numeric_bill_ref"
    assert "發送判定" in result["facts_present"]


def test_result_carries_not_covered_into_report():
    """部分閉環的限制必須原樣進報告——5.5 才不會把它寫成 full closure。"""
    spec = _spec(not_covered=["bill_ref 非數字分支（get_contracts 未遷移）"])
    result = assert_chain_closure(GROUNDING, spec)
    assert result["not_covered"] == ["bill_ref 非數字分支（get_contracts 未遷移）"]


# ── 兩維度各自會咬（互不替代）─────────────────────────────────────────────
def test_delivery_failure_is_caught():
    """送達性：該筆的實際值字面沒進底稿。"""
    with pytest.raises(AssertionError) as ei:
        assert_chain_closure(GROUNDING, _spec(grounding_must_contain=["900003"]))
    assert "送達性缺字面" in str(ei.value)


def test_sufficiency_failure_is_caught_even_when_delivery_passes():
    """⚠️ 核心：字面送到了、但缺回答該問題所必需的事實鍵，仍須紅。

    這一條防的是「查到了就算閉環」——送達性不能替代充分性。
    """
    with pytest.raises(AssertionError) as ei:
        assert_chain_closure(GROUNDING, _spec(required_grounding_facts=["逾期費判定"]))
    msg = str(ei.value)
    assert "充分性缺事實鍵" in msg
    assert "送達性缺字面：[]" in msg          # 送達性其實是過的


# ── 三條結構性禁令 ───────────────────────────────────────────────────────
def test_rejects_assertion_against_final_answer_object():
    """禁令 1：傳入疑似最終回應物件 → 拒絕。"""
    with pytest.raises(AnswerTextAssertionError) as ei:
        assert_chain_closure({"answer": "您這張帳單已發送，無法再次發送"}, _spec())
    assert "answer" in str(ei.value)


@pytest.mark.parametrize("key", ["message", "content", "reply", "text"])
def test_rejects_other_answer_like_shapes(key):
    with pytest.raises(AnswerTextAssertionError):
        assert_chain_closure({key: "任何最終文字"}, _spec())


def test_rejects_non_string_grounding():
    with pytest.raises(AnswerTextAssertionError):
        assert_chain_closure(["900001"], _spec())


def test_rejects_empty_required_facts():
    """禁令 2：未驗充分性即不構成 C4a 通過的證據（任務 5.2 的紀律，機制強制）。"""
    with pytest.raises(SufficiencyNotAssertedError) as ei:
        _spec(required_grounding_facts=[])
    assert "required_grounding_facts" in str(ei.value)


def test_rejects_unknown_closure_scope():
    """禁令 3：scope 必須是已宣告的其中之一。"""
    with pytest.raises(ChainClosureScopeError):
        _spec(closure_scope="full_adapter")


def test_numeric_bill_ref_is_the_only_declared_scope():
    """⚠️ 目前只承認部分閉環——非數字分支因 `get_contracts` 未遷移而不在 claim 內。"""
    from tests.support.chain_closure import CLOSURE_SCOPES

    assert CLOSURE_SCOPES == frozenset({"numeric_bill_ref"})
