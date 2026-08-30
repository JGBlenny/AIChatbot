"""unit：三種 cardinality_mode ＋ F-C11 COLLECTION IS THE ENTITY（業主凍結 2026-08-30）。

```text
T4-B-C1 SELECT_ONE   0→NO_MATCH／1→RESOLVED／>1→AMBIGUOUS（僅此模式適用）
T4-B-C2 SINGLETON    absent→NO_MATCH／single→RESOLVED／multiple competing→AMBIGUOUS
T4-B-C3 COLLECTION   0→依 empty_collection_policy／>=1→RESOLVED（**collection 即 entity**）
                     ⛔ member count 永不觸發 AMBIGUOUS、⛔ 禁止取第一筆
F-C11   若 contract 定義整個 collection 為 input，count>1 是**正常資料形狀**
```
⚠️ 對稱 bug 防護：`0 rows` ⛔ 不得被自動當成「entity 不存在」——
   NO_MATCH 保留給**上游 required entity／scope 找不到**。
"""
import pytest

from services import responsibility_entity_resolution as rer
from services.responsibility_entity_resolution import EntityResolutionError

pytestmark = pytest.mark.unit

COLL = "payment_logs.by_bill.v1"


def _logs(n, scope=716317):
    return [{"id": i, "resolved_bill_id": scope} for i in range(1, n + 1)]


# ───────────────── cardinality_mode 是 contract 的一部分 ─────────────────
@pytest.mark.req("T4B_CARD:1")
def test_every_contract_declares_cardinality_mode():
    """⚠️ ⛔ 不是 runtime 猜的——每個 contract 都必須明示。"""
    for cid, spec in rer.INPUT_CONTRACTS.items():
        assert spec.get("cardinality_mode") in rer.VALID_CARDINALITY, cid


@pytest.mark.req("T4B_CARD:2")
def test_owner_ruled_shapes():
    want = {"payment_logs.by_bill.v1": rer.CARD_COLLECTION,
            "invoice_logs.by_bill.v1": rer.CARD_COLLECTION,
            "iot.manufacturers.v1": rer.CARD_COLLECTION,
            "subscription.current.v1": rer.CARD_SINGLETON,
            "tenant.summary.v1": rer.CARD_SINGLETON,
            "estate.by_ref.v1": rer.CARD_SELECT_ONE}
    for cid, mode in want.items():
        assert rer.INPUT_CONTRACTS[cid]["cardinality_mode"] == mode, cid


# ───────────────── F-C11：count>1 ⛔ 不是 ambiguity ─────────────────
@pytest.mark.req("T4B_C3:1")
def test_collection_many_members_is_resolved_not_ambiguous(monkeypatch):
    monkeypatch.setitem(rer.INPUT_CONTRACTS[COLL], "empty_collection_policy",
                        rer.EMPTY_RESOLVED_EMPTY)
    r = rer.resolve_collection(COLL, _logs(7), scope_value=716317)
    assert r["state"] == rer.STATE_RESOLVED, "collection 的 >1 被誤判成 AMBIGUOUS"
    assert r["member_count"] == 7 and len(r["resolved_entity"]) == 7
    assert r["uniqueness"] == "collection_is_the_entity"


@pytest.mark.req("T4B_C3:2")
def test_collection_never_takes_first_member(monkeypatch):
    monkeypatch.setitem(rer.INPUT_CONTRACTS[COLL], "empty_collection_policy",
                        rer.EMPTY_RESOLVED_EMPTY)
    r = rer.resolve_collection(COLL, _logs(3), scope_value=716317)
    assert isinstance(r["resolved_entity"], list), "⛔ 不得取單筆"
    assert "resolved_id" not in r


# ───────────────── empty_collection_policy 兩態 ─────────────────
@pytest.mark.req("T4B_C3:3")
def test_empty_resolved_empty_is_still_executable(monkeypatch):
    monkeypatch.setitem(rer.INPUT_CONTRACTS[COLL], "empty_collection_policy",
                        rer.EMPTY_RESOLVED_EMPTY)
    r = rer.resolve_collection(COLL, [], scope_value=716317)
    assert r["state"] == rer.STATE_RESOLVED_EMPTY
    assert r["state"] in rer.EXECUTABLE_STATES, "RESOLVED_EMPTY 邏輯上仍是 RESOLVED"
    assert r["resolved_entity"] == [] and r["member_count"] == 0


@pytest.mark.req("T4B_C3:4")
def test_empty_no_match_policy(monkeypatch):
    monkeypatch.setitem(rer.INPUT_CONTRACTS[COLL], "empty_collection_policy",
                        rer.EMPTY_NO_MATCH)
    r = rer.resolve_collection(COLL, [], scope_value=716317)
    assert r["state"] == rer.STATE_NO_MATCH and r["state"] not in rer.EXECUTABLE_STATES


@pytest.mark.req("T4B_C3:5")
def test_undecided_policy_hard_fails(monkeypatch):
    """⚠️ **大聲失敗**：⛔ 不得預設成 NO_MATCH——那是「0 rows 被錯當不存在」的對稱 bug。

    ⚠️ 三個 collection contract 已於 2026-08-30 裁定 RESOLVED_EMPTY，
    故此處**注入**未裁定狀態來驗守門仍在（⛔ 不依賴「剛好還沒裁」的暫時狀態，
    否則這條 guard 會在裁定後靜默失效）。
    """
    monkeypatch.setitem(rer.INPUT_CONTRACTS[COLL], "empty_collection_policy", None)
    with pytest.raises(EntityResolutionError, match="尚未裁定"):
        rer.resolve_collection(COLL, [], scope_value=716317)


# ───────────────── collection scope identity ─────────────────
@pytest.mark.req("T4B_C3:6")
def test_collection_scope_violation(monkeypatch):
    monkeypatch.setitem(rer.INPUT_CONTRACTS[COLL], "empty_collection_policy",
                        rer.EMPTY_RESOLVED_EMPTY)
    mixed = _logs(2, scope=716317) + _logs(1, scope=999999)
    with pytest.raises(EntityResolutionError, match="INPUT_CONTRACT_VIOLATION"):
        rer.resolve_collection(COLL, mixed, scope_value=716317)


@pytest.mark.req("T4B_C3:7")
def test_select_one_contract_cannot_use_collection_resolver():
    with pytest.raises(EntityResolutionError, match="不得以 collection 方式解析"):
        rer.resolve_collection("bill.by_ref.v1", _logs(2), scope_value=1)


# ───────────────── SELECT_ONE 仍維持原語義（正對照）─────────────────
@pytest.mark.req("T4B_C1:11")
def test_select_one_still_ambiguous_on_many():
    """⚠️ 正對照：T4-B-C1 的 >1→AMBIGUOUS **只**適用 SELECT_ONE，且仍然有效。"""
    r = rer.resolve("contract.current_entity.v1", {"contract_ref": "台北"},
                    [{"id": 1}, {"id": 2}])
    assert r["state"] == rer.STATE_AMBIGUOUS
