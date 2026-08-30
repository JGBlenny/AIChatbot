"""unit：T4-B3 `bill.by_ref.v1` 顯式解析階段 ＋ B-G5（業主凍結 2026-08-30）。

```text
B-G5 NO HIDDEN FIRST-ROW SELECTION
     非數字 ref → contract lookup 回 [C1,C2] ⇒ **AMBIGUOUS**
     mutation `contracts[0]` 必紅
     ⚠️ 與 B-M1 不重複：B-M1 防 resolver 拿到 candidates 後自取第一筆；
        B-G5 防 **upstream adapter 在 resolver 看見 candidates 前就先取第一筆**
F-C6 responsibility path ⛔ 不呼叫 legacy get_bills(bill_ref=...)（其內部已 rows[0]）
```
"""
import pytest

from services import responsibility_bill_resolution as rbr
from services import responsibility_entity_resolution as rer

pytestmark = pytest.mark.unit


class FakeApi:
    """⚠️ 刻意**不提供** bill_ref 參數——若 resolver 誤呼叫 legacy 分支會 TypeError。"""

    def __init__(self, detail=None, contracts=None, bills=None):
        self._detail, self._contracts, self._bills = detail, contracts, bills
        self.calls = []

    async def get_bill_detail(self, role_id, bill_id):
        self.calls.append(("get_bill_detail", bill_id))
        return self._detail

    async def get_contracts(self, role_id, contract_ids=None, keyword=None, **kw):
        self.calls.append(("get_contracts", contract_ids, keyword))
        return self._contracts

    async def get_bills(self, role_id, contract_ids=None, **kw):
        if "bill_ref" in kw:
            raise AssertionError("⛔ responsibility path 呼叫了 legacy bill_ref 分支（F-C6）")
        self.calls.append(("get_bills", contract_ids))
        return self._bills


def ok(data):
    return {"success": True, "data": data}


async def _run(api, ref):
    return await rbr.resolve_bill_by_ref(api, "role-1", ref)


# ───────────────── 數字 ref ─────────────────
@pytest.mark.req("T4B3_NUM:1")
@pytest.mark.asyncio
async def test_numeric_ref_resolves_exact_bill():
    api = FakeApi(detail=ok({"id": 716317, "title": "8月房租"}))
    r = await _run(api, "716317")
    assert r["state"] == rer.STATE_RESOLVED and r["resolved_id"] == 716317
    assert r["stage"] == rbr.STAGE_BILL_DIRECT and r["uniqueness"] == "direct_bill_id"
    assert api.calls == [("get_bill_detail", 716317)], "⛔ 不應多打其他端點"


@pytest.mark.req("T4B3_NUM:2")
@pytest.mark.asyncio
async def test_numeric_ref_not_found():
    r = await _run(FakeApi(detail={"success": True, "data": None}), "999999")
    assert r["state"] == rer.STATE_NO_MATCH and r["stage"] == rbr.STAGE_BILL_DIRECT


@pytest.mark.req("T4B3_NUM:3")
@pytest.mark.asyncio
async def test_empty_ref_is_invalid_input():
    r = await _run(FakeApi(), "   ")
    assert r["state"] == rer.STATE_INVALID_INPUT


# ───────────────── B-G5：非數字 ref ─────────────────
@pytest.mark.req("T4B3_G5:1")
@pytest.mark.asyncio
async def test_b_g5_two_contracts_is_ambiguous_not_first():
    api = FakeApi(contracts=ok([{"id": 101, "title": "C1"}, {"id": 102, "title": "C2"}]))
    r = await _run(api, "台北")
    assert r["state"] == rer.STATE_AMBIGUOUS, "⛔ upstream 不得先偷偷取第一筆合約"
    assert r["stage"] == rbr.STAGE_CONTRACT_LOOKUP
    assert [c["id"] for c in r["candidates"]] == [101, 102]
    assert "resolved_id" not in r
    assert not any(c[0] == "get_bills" for c in api.calls), "AMBIGUOUS 後 ⛔ 不應繼續查帳單"


@pytest.mark.req("T4B3_G5:2")
@pytest.mark.asyncio
async def test_b_g5_mutation_taking_first_contract_makes_guard_red():
    """mutation：contracts[0]（＝legacy jgb_system_api.py:190 的行為）。"""
    api = FakeApi(contracts=ok([{"id": 101}, {"id": 102}]),
                  bills=ok([{"id": 9001, "title": "C1 的帳單"}]))

    async def mutated(a, role_id, ref):
        cs = rbr._rows(await a.get_contracts(role_id, keyword=ref))
        cid = cs[0].get("id")                       # ⛔ 隱藏的 first-row authority
        bs = rbr._rows(await a.get_bills(role_id, contract_ids=cid))
        return rbr._stage(rer.STATE_RESOLVED, rbr.STAGE_BILLS_OF_CONTRACT,
                          resolved_id=bs[0].get("id"), resolved_contract_id=cid)

    r = await mutated(api, "role-1", "台北")
    assert r["state"] == rer.STATE_RESOLVED and r["resolved_contract_id"] == 101, \
        "mutation 未讓 B-G5 變紅 ⇒ guard 是裝飾"


@pytest.mark.req("T4B3_G5:3")
@pytest.mark.asyncio
async def test_unique_contract_then_unique_bill_resolves():
    api = FakeApi(contracts=ok([{"id": 101, "title": "唯一合約"}]),
                  bills=ok([{"id": 9001, "title": "唯一帳單"}]))
    r = await _run(api, "民生東路")
    assert r["state"] == rer.STATE_RESOLVED and r["resolved_id"] == 9001
    assert r["resolved_contract_id"] == 101
    assert r["uniqueness"] == "unique_contract_then_unique_bill"


@pytest.mark.req("T4B3_G5:4")
@pytest.mark.asyncio
async def test_unique_contract_but_many_bills_is_ambiguous():
    api = FakeApi(contracts=ok([{"id": 101}]),
                  bills=ok([{"id": 9001}, {"id": 9002}]))
    r = await _run(api, "民生東路")
    assert r["state"] == rer.STATE_AMBIGUOUS and r["stage"] == rbr.STAGE_BILLS_OF_CONTRACT, \
        "⛔ 合約唯一 ⛔ 不代表帳單唯一"


@pytest.mark.req("T4B3_G5:5")
@pytest.mark.asyncio
async def test_no_contract_is_no_match():
    r = await _run(FakeApi(contracts=ok([])), "不存在的物件")
    assert r["state"] == rer.STATE_NO_MATCH and r["stage"] == rbr.STAGE_CONTRACT_LOOKUP


# ───────────────── F-C6 ─────────────────
@pytest.mark.req("T4B3_FC6:1")
@pytest.mark.asyncio
async def test_fc6_never_calls_legacy_bill_ref_branch():
    api = FakeApi(contracts=ok([{"id": 101}]), bills=ok([{"id": 9001}]))
    await _run(api, "民生東路")
    for call in api.calls:
        if call[0] == "get_bills":
            assert call[1] == 101, "get_bills 只能走 contract_ids 分支（F-C6）"


@pytest.mark.req("T4B3_FC6:2")
@pytest.mark.asyncio
async def test_ambiguous_cannot_enter_capability():
    api = FakeApi(contracts=ok([{"id": 101}, {"id": 102}]))
    r = await _run(api, "台北")
    with pytest.raises(rer.EntityResolutionError):
        rer.assert_executable(r)
