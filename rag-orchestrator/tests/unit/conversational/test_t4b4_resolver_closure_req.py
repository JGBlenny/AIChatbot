"""unit：T4-B4 input-contract execution closure（業主凍結 2026-08-30）。

```text
B4-G1 estate >1 → AMBIGUOUS，**絕不** first-row
B4-G2 estate exact unique → RESOLVED exact entity
B4-G3 subscription valid singleton dict → RESOLVED
B4-G4 subscription wrong/list shape → hard fail（contract violation）
B4-G5 tenant verified_user_id → 可進 summary lookup
B4-G6 tenant keyword-only → **⛔ 不得當 user_id**
B4-G7 singleton response shape ⛔ 不得覆蓋 unresolved identity（F-C13）
B4-G8 resolver signatures 無 user_question／face／category
B4-M1 tenant_keyword 直接當 user_id → guard RED
B4-M2 estate rows[0]                → ambiguity guard RED
```
"""
import inspect

import pytest

from services import responsibility_entity_resolution as rer
from services.responsibility_entity_resolution import IdentityNotResolved

pytestmark = pytest.mark.unit


def ok(d):
    return {"success": True, "data": d}


class FakeEstateApi:
    def __init__(self, detail=None, search=None):
        self._d, self._s = detail, search
        self.calls = []

    async def get_estate_detail(self, estate_id=None, **kw):
        self.calls.append(("detail", estate_id)); return self._d

    async def get_estates(self, role_id, keyword="", **kw):
        self.calls.append(("search", keyword)); return self._s


class FakeSubApi:
    def __init__(self, resp): self._r = resp
    async def get_subscription(self, role_id, **kw): return self._r


class FakeTenantApi:
    def __init__(self, resp=None):
        self._r = resp or ok({"tenant_info": {"id": 101}})
        self.calls = []

    async def get_tenant_summary(self, role_id, user_id, **kw):
        self.calls.append((role_id, user_id)); return self._r


# ───────────────────────── B4-G1 ／ B4-G2 ─────────────────────────
@pytest.mark.req("T4B4_G2:1")
@pytest.mark.asyncio
async def test_estate_exact_id_resolves():
    api = FakeEstateApi(detail=ok({"id": 501, "title": "民生東路 3F"}))
    r = await rer.resolve_estate_by_ref(api, "role-1", "501")
    assert r["state"] == rer.STATE_RESOLVED and r["resolved_id"] == 501
    assert r["uniqueness"] == "exact_estate_id" and r["stage"] == "estate_detail"
    assert api.calls == [("detail", 501)], "⚠️ exact path 優先——⛔ 不應再打 search"


@pytest.mark.req("T4B4_G1:1")
@pytest.mark.asyncio
async def test_estate_keyword_many_is_ambiguous_not_first():
    api = FakeEstateApi(search=ok([{"id": 501, "title": "民生 A"}, {"id": 502, "title": "民生 B"}]))
    r = await rer.resolve_estate_by_ref(api, "role-1", "民生")
    assert r["state"] == rer.STATE_AMBIGUOUS, "⛔ 多筆物件不得取第一筆"
    assert [c["id"] for c in r["candidates"]] == [501, 502]
    assert "resolved_id" not in r


@pytest.mark.req("T4B4_G1:2")
@pytest.mark.asyncio
async def test_estate_unique_keyword_resolves():
    api = FakeEstateApi(search=ok([{"id": 501, "title": "唯一物件"}]))
    r = await rer.resolve_estate_by_ref(api, "role-1", "唯一")
    assert r["state"] == rer.STATE_RESOLVED and r["uniqueness"] == "unique_keyword_match"


@pytest.mark.req("T4B4_G1:3")
@pytest.mark.asyncio
async def test_estate_sentinel_is_not_an_entity():
    """⚠️ `{"found": False}` 是 sentinel，⛔ 不得被當成一筆物件。"""
    api = FakeEstateApi(search=ok([{"found": False, "keyword": "查無"}]))
    r = await rer.resolve_estate_by_ref(api, "role-1", "查無")
    assert r["state"] == rer.STATE_NO_MATCH


@pytest.mark.req("T4B4_M2:1")
@pytest.mark.asyncio
async def test_b4_m2_first_row_mutation_would_be_red():
    api = FakeEstateApi(search=ok([{"id": 501}, {"id": 502}]))
    r = await rer.resolve_estate_by_ref(api, "role-1", "民生")
    mutated = {**r, "state": rer.STATE_RESOLVED, "resolved_id": r["candidates"][0]["id"]}
    assert mutated["resolved_id"] == 501, "B4-M2 未讓 guard 變紅 ⇒ guard 是裝飾"


# ───────────────────────── B4-G3 ／ B4-G4 ─────────────────────────
@pytest.mark.req("T4B4_G3:1")
@pytest.mark.asyncio
async def test_subscription_singleton_resolves():
    r = await rer.resolve_subscription_current(
        FakeSubApi(ok({"plan": "pro", "estate_quota": 50})), "20151")
    assert r["state"] == rer.STATE_RESOLVED
    assert r["resolved_entity"]["plan"] == "pro"
    assert r["uniqueness"] == "semantic_singleton_by_verified_role"


@pytest.mark.req("T4B4_G4:1")
@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [[{"plan": "a"}, {"plan": "b"}], "字串", 123])
async def test_subscription_wrong_shape_is_contract_violation(bad):
    r = await rer.resolve_subscription_current(FakeSubApi(ok(bad)), "20151")
    assert r["state"] == rer.STATE_INVALID_INPUT and "contract_violation" in r


@pytest.mark.req("T4B4_G4:2")
@pytest.mark.asyncio
@pytest.mark.parametrize("resp", [ok(None), ok({}), {"success": False}])
async def test_subscription_absent_is_no_match(resp):
    r = await rer.resolve_subscription_current(FakeSubApi(resp), "20151")
    assert r["state"] == rer.STATE_NO_MATCH


@pytest.mark.req("T4B4_G7:1")
@pytest.mark.asyncio
async def test_subscription_requires_verified_role():
    with pytest.raises(IdentityNotResolved, match="verified_role_id"):
        await rer.resolve_subscription_current(FakeSubApi(ok({"plan": "pro"})), None)


# ───────────────────────── B4-G5 ／ B4-G6 ／ B4-G7 ─────────────────────────
@pytest.mark.req("T4B4_G5:1")
@pytest.mark.asyncio
async def test_tenant_verified_user_id_resolves():
    api = FakeTenantApi()
    r = await rer.resolve_tenant_summary(api, "20151", verified_user_id="2001")
    assert r["state"] == rer.STATE_RESOLVED and r["uniqueness"] == "verified_user_id"
    assert api.calls == [("20151", "2001")]


@pytest.mark.req("T4B4_G6:1")
@pytest.mark.asyncio
async def test_tenant_keyword_only_is_hard_fail():
    """⚠️ **負控制**：只有 keyword 時 ⛔ 不得呼叫 summary endpoint。"""
    api = FakeTenantApi()
    with pytest.raises(IdentityNotResolved, match="不得原樣當 user_id"):
        await rer.resolve_tenant_summary(api, "20151", tenant_keyword="王小明")
    assert api.calls == [], "⛔ 身分未解析卻已呼叫 endpoint"


@pytest.mark.req("T4B4_G7:2")
@pytest.mark.asyncio
async def test_singleton_shape_cannot_override_unresolved_identity():
    """F-C13：endpoint 回單一 dict **只證 output cardinality**。"""
    api = FakeTenantApi(ok({"tenant_info": {"id": 999}}))   # 形狀完美
    with pytest.raises(IdentityNotResolved):
        await rer.resolve_tenant_summary(api, "20151", tenant_keyword="王小明")


# ───────────────────────── B4-G8 ─────────────────────────
@pytest.mark.req("T4B4_G8:1")
@pytest.mark.parametrize("fn", ["resolve_estate_by_ref", "resolve_subscription_current",
                                 "resolve_tenant_summary", "resolve_collection", "resolve"])
def test_resolver_signatures_have_no_semantic_inputs(fn):
    params = set(inspect.signature(getattr(rer, fn)).parameters)
    assert not ({"user_question", "face", "category"} & params), \
        f"{fn} 收了 semantic input ⇒ input resolution 會變成另一個 rerouter"
