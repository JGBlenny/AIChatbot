"""`/invoices` 替身逐條對照 `InvoiceApiController`（inventory §8 第 5 項）。

`App\\Invoice` **無 $casts、無 accessor**，所有欄位都是原始欄位值；唯一由控制器加工的是
`tax_rate`（`$invoice->tax_rate ? (float) : null` → **0 變 null**，:125）。
故本檔的重點在**過濾與排序**：舊 mock 把 bill_id／status 兩個參數整個忽略、且固定升冪。
"""
import asyncio

import pytest

pytestmark = pytest.mark.unit

ROLE = "20151"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


@pytest.mark.req("face-exit-before-grounding:1")
def test_orders_by_id_desc(api):
    """production：`orderBy('invoices.id','desc')`（:71）。舊 mock 固定回 5001 在前。"""
    rows = _run(api.get_invoices(role_id=ROLE, bill_id=None, user_id="9001"))["data"]
    assert [r["id"] for r in rows] == sorted((r["id"] for r in rows), reverse=True)
    assert rows[0]["id"] == 5002


@pytest.mark.req("face-exit-before-grounding:1")
def test_bill_id_filter_bites(api):
    r = _run(api.get_invoices(role_id=ROLE, bill_id=12345))
    assert [x["id"] for x in r["data"]] == [5001]
    assert r["pagination"]["total"] == 1


@pytest.mark.req("face-exit-before-grounding:1")
def test_status_filter_bites(api):
    r = _run(api.get_invoices(role_id=ROLE, user_id="9001", status=2))
    assert [x["id"] for x in r["data"]] == [5002]


@pytest.mark.req("face-exit-before-grounding:1")
def test_pagination_tracks_the_filtered_set(api):
    """舊 mock 的 pagination 是寫死的 total=2／total_pages=1，不隨過濾改變。"""
    empty = _run(api.get_invoices(role_id=ROLE, bill_id=999999))
    assert empty["data"] == []
    assert empty["pagination"]["total"] == 0 and empty["pagination"]["total_pages"] == 0
    assert empty["pagination"]["has_more"] is False


@pytest.mark.req("face-exit-before-grounding:1")
def test_mapping_values_match_invoice_constants(api):
    """`App\\Invoice`:9-23——status 0-4／category B2B・B2C／tax_type 1・2・3・**9**。"""
    m = _run(api.get_invoices(role_id=ROLE, user_id="9001"))["mapping"]
    assert m["status"] == {"0": "未開立", "1": "已開立", "2": "作廢",
                           "3": "折讓", "4": "作廢折讓"}
    assert set(m["category"]) == {"B2B", "B2C"}
    assert m["tax_type"]["9"] == "混合"          # 不是 4，容易抄錯


@pytest.mark.req("face-exit-before-grounding:1")
def test_projection_matches_format_invoice(api):
    """`formatInvoice()` 逐鍵 26 欄（:107-135）。"""
    row = _run(api.get_invoices(role_id=ROLE, user_id="9001"))["data"][0]
    assert set(row) == {
        "id", "bill_id", "payment_id", "manufacturer", "number", "random_num",
        "status", "upload_status", "category", "buyer_name", "buyer_ubn",
        "buyer_address", "buyer_email", "carrier_type", "carrier_number",
        "love_code", "print_flag", "tax_type", "tax_rate", "tax_amt", "amt",
        "total_amt", "item_data", "bar_code", "url",
        "added_at", "invalid_at", "allowanced_at",
    }


@pytest.mark.req("face-exit-before-grounding:1")
def test_gap_i1_user_id_is_not_filtered_yet(api):
    """**GAP-I1（已登記缺口，非已證行為）**：`user_id` 目前不過濾。

    production 是 `whereExists(contracts.id = bills.contract_id
    AND contracts.to_user_id = ? AND contracts.active = 1)`——跨三張表。
    替身的發票掛在 bill 12345／12340，帳單 fixture 是 900001-3、合約 fixture 是 678／600，
    **三個 fixture 宇宙不連通**（與 GAP-B1 同源）。讀到這條綠燈**不得**推論
    「發票的租客過濾已驗」。
    """
    a = _run(api.get_invoices(role_id=ROLE, user_id="9001"))["data"]
    b = _run(api.get_invoices(role_id=ROLE, user_id="9002"))["data"]
    assert [r["id"] for r in a] == [r["id"] for r in b]
