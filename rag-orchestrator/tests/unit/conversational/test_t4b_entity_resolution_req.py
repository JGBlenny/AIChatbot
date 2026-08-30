"""unit：T4-B1 responsibility-only entity resolution guards（業主凍結 2026-08-30）。

```text
B-C1 0→NO_MATCH／1→RESOLVED／>1 無唯一性證明→AMBIGUOUS
     ⛔ MUST NOT choose first／highest DB order／earliest returned
例外  已 review 的 deterministic selection contract（select_point_refund 為正例）
B-M1 AMBIGUOUS → candidates[0]     → guard RED
B-M2 resolver missing → fallback first row → RED
```
⚠️ R-29（bill.by_ref.v1）與 R-05（contract.current_entity.v1）為第一組正反控制。
"""
import pytest

from services import responsibility_entity_resolution as rer
from services.responsibility_entity_resolution import EntityResolutionError, resolve

pytestmark = pytest.mark.unit

BILL = "bill.by_ref.v1"
CONTRACT = "contract.current_entity.v1"


def _rows(*ids):
    return [{"id": i, "title": f"帳單 {i}"} for i in ids]


# ───────────────── R-29 正控制：bill.by_ref ─────────────────
@pytest.mark.req("T4B_C1:1")
def test_r29_unique_bill_ref_resolves():
    r = resolve(BILL, {"bill_ref": "716317"}, _rows(716317))
    assert r["state"] == rer.STATE_RESOLVED
    assert r["resolved_id"] == 716317 and r["uniqueness"] == "single_returned_entity"


@pytest.mark.req("T4B_C1:2")
def test_r29_no_rows_is_no_match():
    r = resolve(BILL, {"bill_ref": "999999"}, [])
    assert r["state"] == rer.STATE_NO_MATCH and "_not_executable" in r


@pytest.mark.req("T4B_C1:3")
def test_r29_missing_field_is_invalid_input():
    r = resolve(BILL, {}, _rows(1))
    assert r["state"] == rer.STATE_INVALID_INPUT and r["missing_fields"] == ["bill_ref"]


# ───────────────── R-05 反控制：多筆合約 ⛔ 不得取第一筆 ─────────────────
@pytest.mark.req("T4B_C1:4")
def test_r05_multiple_contracts_is_ambiguous_not_first():
    r = resolve(CONTRACT, {"contract_ref": "台北"}, _rows(101, 102, 103))
    assert r["state"] == rer.STATE_AMBIGUOUS, "⛔ 多筆時不得默默取第一筆（F-C3）"
    assert [c["id"] for c in r["candidates"]] == [101, 102, 103]
    assert "resolved_id" not in r


@pytest.mark.req("T4B_C1:5")
def test_ambiguous_cannot_enter_capability():
    r = resolve(CONTRACT, {"contract_ref": "台北"}, _rows(101, 102))
    with pytest.raises(EntityResolutionError, match="不得進 direct capability"):
        rer.assert_executable(r)


# ───────────────── 唯一例外：reviewed selection contract ─────────────────
@pytest.mark.req("T4B_C1:6")
def test_reviewed_selection_contract_may_uniquify():
    """正例：select_point_refund 形狀的 (state, selected, candidates)。"""
    from services.jgb import point_refund_selection as pr
    rows = [{"id": 1, "type": 1, "title": "月租"}, {"id": 2, "type": 2, "title": "點退"}]
    r = resolve("point_refund.bill_by_contract.v1", {"contract_ref": "C-1"}, rows,
                selection_contract=pr.select_point_refund)
    assert r["state"] == rer.STATE_RESOLVED
    assert r["resolved_id"] == 2, "必須選 type=2，⛔ 不是第一筆"
    assert r["uniqueness"] == "reviewed_selection_contract"


@pytest.mark.req("T4B_C1:7")
def test_selection_contract_two_candidates_is_ambiguous():
    from services.jgb import point_refund_selection as pr
    rows = [{"id": 2, "type": 2, "title": "點退A"}, {"id": 3, "type": 2, "title": "點退B"}]
    r = resolve("point_refund.bill_by_contract.v1", {"contract_ref": "C-1"}, rows,
                selection_contract=pr.select_point_refund)
    assert r["state"] == rer.STATE_AMBIGUOUS, "多筆 type=2 ⛔ 不得任選"


@pytest.mark.req("T4B_C1:8")
def test_selection_contract_absent_falls_to_ambiguous_not_first():
    """⚠️ 有 policy 但**沒帶** selection contract ⇒ 仍是 AMBIGUOUS，⛔ 不得取第一筆。"""
    r = resolve("point_refund.bill_by_contract.v1", {"contract_ref": "C-1"}, _rows(1, 2))
    assert r["state"] == rer.STATE_AMBIGUOUS


# ───────────────── tagged alternatives（R-28 的 input contract）─────────────────
@pytest.mark.req("T4B_C1:9")
def test_late_fee_tagged_alternatives():
    spec = rer.INPUT_CONTRACTS["late_fee.bill_or_contract.v1"]
    assert spec["_accepts"] == ["resolved_contract", "resolved_late_fee_bill"]
    bad = resolve("late_fee.bill_or_contract.v1", {"something_else": 1}, _rows(1))
    assert bad["state"] == rer.STATE_INVALID_INPUT
    ok = resolve("late_fee.bill_or_contract.v1", {"resolved_late_fee_bill": 9}, _rows(9))
    assert ok["state"] == rer.STATE_RESOLVED


# ───────────────── resolver identity ⛔ 不是 callable ─────────────────
@pytest.mark.req("T4B_C1:10")
def test_resolver_id_is_opaque_not_callable():
    for cid, spec in rer.INPUT_CONTRACTS.items():
        rid = spec["resolver_id"]
        assert isinstance(rid, str) and "::" not in rid and ".py" not in rid, cid
        assert not callable(rid)


# ───────────────── mutations ─────────────────
@pytest.mark.req("T4B_M1:1")
def test_b_m1_ambiguous_taking_first_makes_guard_red():
    """B-M1：AMBIGUOUS → candidates[0]。"""
    r = resolve(CONTRACT, {"contract_ref": "台北"}, _rows(101, 102, 103))
    mutated = {**r, "state": rer.STATE_RESOLVED, "resolved_id": r["candidates"][0]["id"]}
    assert rer.assert_executable(mutated)["resolved_id"] == 101, "B-M1 未讓 guard 變紅 ⇒ guard 是裝飾"


@pytest.mark.req("T4B_M2:1")
def test_b_m2_missing_resolver_must_not_fallback_to_first_row():
    """B-M2：resolver 未註冊時 ⛔ 不得 fallback 取第一筆。"""
    with pytest.raises(EntityResolutionError, match="不得因為缺 resolver 就 fallback 取第一筆"):
        resolve("nonexistent.contract.v1", {"x": 1}, _rows(1, 2, 3))
