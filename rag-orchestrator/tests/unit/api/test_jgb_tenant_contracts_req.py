"""get_tenant_contracts：走**真端點** `GET /contracts/status-overview`（帶 `user_id`）。

原判定「jgb2 尚未提供租客視角租約端點」（J 清單 G1）於 2026-08-25 盤查**改判作廢**：
production `ContractApiController@index:63-65` 就是 `where('to_user_id', (int) user_id)`。
先前的 `NotImplementedError` 讓本方法在真實模式必然拋例外，而 `repair_prefill` 會吞例外
→ production 物件預填靜默失效、mock 測試卻全綠。本檔驗的就是那個洞被補起來。

驗證契約：
- 雙證（role_id + user_id）缺一 → 降級（success: False）
- 打的是 `/api/external/v1/contracts/status-overview`，且 `user_id` 有帶上（非方法級 mock）
- `user_id` 過濾會咬：9001 → 只有 678；9002 只有歷史合約 → 0 筆；未知租客 → 0 筆
- 投影對映逐鍵；`room` **不輸出**（formatContract 無此欄，不得假造）
- 內部欄位 `to_user_id` 不得出現在任何回應
"""
import asyncio

import pytest

pytestmark = pytest.mark.unit


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def api():
    import os
    os.environ["USE_MOCK_JGB_API"] = "true"
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


# ---------------------------------------------------------------------------
# 雙證缺一 → 降級（行為保持）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.1")
@pytest.mark.parametrize("role_id,user_id", [
    (None, "9001"), ("R001", None), ("", "9001"), ("R001", ""),
])
def test_identity_required(api, role_id, user_id):
    assert _run(api.get_tenant_contracts(role_id=role_id, user_id=user_id))["success"] is False


# ---------------------------------------------------------------------------
# 真的走 transport 的合約端點（證明不再是方法級 mock，也證明真實模式不再拋例外）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.2")
def test_hits_contracts_endpoint_with_user_id(api):
    seen = {}
    inner = api._mock_transport

    class _Spy:
        async def send(self, method, path, *, params=None, data=None):
            seen.update({"method": method, "path": path, "params": params or {}})
            return await inner.send(method, path, params=params, data=data)

    api._mock_transport = _Spy()
    _run(api.get_tenant_contracts(role_id="R001", user_id="9001"))

    assert seen["method"] == "GET"
    assert seen["path"] == "/api/external/v1/contracts/status-overview"
    assert seen["params"]["user_id"] == "9001" and seen["params"]["role_id"] == "R001"


# ---------------------------------------------------------------------------
# user_id 過濾會咬（fixture 兩列分屬不同租客）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.2")
def test_user_id_converges_to_that_tenant(api):
    result = _run(api.get_tenant_contracts(role_id="R001", user_id="9001"))
    assert result["success"] is True
    assert [r["contract_id"] for r in result["data"]] == [678]


@pytest.mark.req("conversational-repair:2.2")
def test_history_only_tenant_gets_zero(api):
    """9002 名下只有 600（is_history=1）——adapter 濾掉歷史合約，故 0 筆。

    ⚠️ production index **不濾** is_history；這條界線在 adapter，不是 API。
    """
    result = _run(api.get_tenant_contracts(role_id="R001", user_id="9002"))
    assert result["success"] is True and result["data"] == []


@pytest.mark.req("conversational-repair:2.2")
def test_unknown_tenant_gets_zero(api):
    result = _run(api.get_tenant_contracts(role_id="R001", user_id="9999"))
    assert result["success"] is True and result["data"] == []


# ---------------------------------------------------------------------------
# 投影對映
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.2")
def test_projection_maps_formatcontract_keys(api):
    row = _run(api.get_tenant_contracts(role_id="R001", user_id="9001"))["data"][0]
    assert row == {
        "contract_id": 678,
        "estate_id": 456,
        "estate_title": "信義區套房A",
        "display_address": "台北市信義區信義路五段7號",
    }


@pytest.mark.req("conversational-repair:2.2")
def test_room_is_not_fabricated(api):
    """`formatContract` 沒有房號欄位——不得拿別的欄位湊 `room`。

    `repair_prefill._estate_display` 以 `if row.get(k)` 逐段組字串，缺鍵不會炸。
    """
    row = _run(api.get_tenant_contracts(role_id="R001", user_id="9001"))["data"][0]
    assert "room" not in row


@pytest.mark.req("conversational-repair:2.2")
def test_internal_column_never_leaks(api):
    """`to_user_id` 是內部欄位（production select 但 formatContract 不投影）。"""
    raw = _run(api._request("/api/external/v1/contracts/status-overview",
                            {"role_id": "R001"}))
    assert raw["success"] is True and raw["data"]
    for row in raw["data"]:
        assert "to_user_id" not in row
