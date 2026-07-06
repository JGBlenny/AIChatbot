"""unit:帳單識別 adapter（billing-conversational-facets 任務 2.1 / R2.1, R7.3）。

背景（research §六-1）：bills 列表無編號直查、無名稱搜尋——「給帳單編號」與「給物件名稱」
單靠一個端點的 search_params 蓋不住。解法：`get_bills` 擴充 `bill_ref` 識別語意參數
（adapter 屬 JGB 領域檔職責，引擎零改、後端當裁判慣例不變）：
  純數字 → get_bill_detail 直查（單筆包成列）；查無 → 當合約識別（contract_id 直查）；
  非數字 → get_contracts(keyword) 解析 → 取第一筆合約 → bills?contract_id 回列候選。
（2026-07-05 修正：上游參數為 contract_id 單數，誤送複數被無視致整 role 帳單全回；
 另加 client 端防衛過濾——列上帶 contract_id 才啟動。）
降級：解析失敗/例外 → 回空列（success=True, data=[]）不拋——引擎走 0 筆追問路，不炸忙線。
既有呼叫（無 bill_ref）零回歸。
"""
import pytest
from unittest.mock import AsyncMock

from services.jgb_system_api import JGBSystemAPI

pytestmark = pytest.mark.unit

_BILL = {"id": 714100, "title": "2026-07 租金", "total": 20000}


def _api():
    api = JGBSystemAPI()
    api.use_mock = False
    api.get_bill_detail = AsyncMock(return_value={"success": False})
    api.get_contracts = AsyncMock(return_value={"success": True, "data": []})
    api._request = AsyncMock(return_value={"success": True, "data": []})
    return api


# ── 路徑一：純數字 → bill_detail 直查命中 → 單筆包成列，不打 bills 列表 ──
@pytest.mark.req("billing-conversational-facets:2.1")
async def test_numeric_bill_ref_direct_hit():
    api = _api()
    api.get_bill_detail = AsyncMock(return_value={"success": True, "data": _BILL})
    r = await api.get_bills(role_id="20151", bill_ref="714100")
    assert r["success"] is True and r["data"] == [_BILL]
    api.get_bill_detail.assert_awaited_once_with("20151", 714100)
    api.get_contracts.assert_not_awaited()
    api._request.assert_not_awaited()


# ── 路徑二：純數字 bill_detail 查無 → 當合約 id 解析 → bills?contract_ids ──
@pytest.mark.req("billing-conversational-facets:2.1")
async def test_numeric_miss_falls_back_to_contract_id():
    api = _api()
    api.get_contracts = AsyncMock(return_value={"success": True, "data": [{"id": 84908}]})
    api._request = AsyncMock(return_value={"success": True, "data": [_BILL, {"id": 2}]})
    r = await api.get_bills(role_id="20151", bill_ref="84908")
    assert [b["id"] for b in r["data"]] == [714100, 2]
    kwargs = api.get_contracts.await_args.kwargs
    assert kwargs.get("contract_ids") == "84908"          # 數字先當合約 id 解析
    assert api._request.await_args.args[1]["contract_id"] == 84908


# ── 路徑三：非數字 → 合約 keyword 解析 → 取第一筆 → bills 列候選 ──
@pytest.mark.req("billing-conversational-facets:2.1")
async def test_text_bill_ref_resolves_contract_by_keyword():
    api = _api()
    api.get_contracts = AsyncMock(return_value={"success": True,
                                                "data": [{"id": 84981}, {"id": 84972}]})
    api._request = AsyncMock(return_value={"success": True, "data": [_BILL]})
    r = await api.get_bills(role_id="20151", bill_ref="基隆溫馨一人宅套房")
    assert r["data"] == [_BILL]
    assert api.get_contracts.await_args.kwargs.get("keyword") == "基隆溫馨一人宅套房"
    assert api.get_bill_detail.await_count == 0            # 非數字不試 bill_detail
    assert api._request.await_args.args[1]["contract_id"] == 84981   # 取第一筆


# ── 降級：合約解析空/例外 → 空列不拋（引擎 0 筆追問路，不炸忙線）──
@pytest.mark.req("billing-conversational-facets:7.3")
async def test_resolution_failure_returns_empty_not_raise():
    api = _api()                                           # contracts 回空
    r = await api.get_bills(role_id="20151", bill_ref="查無此物件xyz")
    assert r["success"] is True and r["data"] == []

    api2 = _api()
    api2.get_contracts = AsyncMock(side_effect=TimeoutError("upstream"))
    r2 = await api2.get_bills(role_id="20151", bill_ref="基隆")
    assert r2["success"] is True and r2["data"] == []


# ── 身分：role_id＋bill_ref 即可（b2b per-bill 授權，同 contract_ids 形態）──
@pytest.mark.req("billing-conversational-facets:2.1")
async def test_identity_allows_role_id_plus_bill_ref():
    api = _api()
    api.get_bill_detail = AsyncMock(return_value={"success": True, "data": _BILL})
    r = await api.get_bills(role_id="20151", bill_ref="714100")   # 無 user_id
    assert r["success"] is True


# ── 零回歸：無 bill_ref → 原路（直打 bills 列表，不碰 detail/contracts）──
@pytest.mark.req("billing-conversational-facets:2.1")
async def test_without_bill_ref_unchanged():
    api = _api()
    api._request = AsyncMock(return_value={"success": True, "data": [_BILL]})
    r = await api.get_bills(role_id="20151", contract_ids="84908")
    assert r["data"] == [_BILL]
    api.get_bill_detail.assert_not_awaited()
    api.get_contracts.assert_not_awaited()
    assert api._request.await_args.args[1]["contract_id"] == "84908"


# ── get_invoices b2b per-bill 授權（secondary_call 用；比照 get_bills 形態）──
@pytest.mark.req("billing-conversational-facets:7.5")
async def test_get_invoices_allows_role_id_plus_bill_id():
    api = _api()
    api._request = AsyncMock(return_value={"success": True, "data": [{"id": 1, "status": 1}]})
    r = await api.get_invoices(role_id="20151", bill_id=714100)     # 無 user_id
    assert r["success"] is True
    assert api._request.await_args.args[1]["bill_id"] == 714100

    api2 = _api()
    r2 = await api2.get_invoices(role_id="20151")                    # 無 user_id 也無 bill_id → 仍降級
    assert r2["success"] is False
