"""其餘七支端點對照原始碼（inventory §8 第 9 項——原判 C 級，查證後**全部是 live**）。

dev DB 查證：這 8 個註冊鍵在 knowledge_base／form_schemas／vendor_sop_items 都有設定
（業主裁定本地≡線上），故不是死碼，逐一盤查。
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


# ── /invoice-logs：最嚴重的一支 ──────────────────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_invoice_logs_require_bill_or_invoice_id(api):
    """production：兩者皆缺 → 400（:23-25）。⚠️ 本端點**完全不看 role_id**。"""
    assert _run(api.get_invoice_logs(role_id=ROLE))["success"] is False
    assert _run(api.get_invoice_logs(role_id=ROLE, bill_id=12345))["success"] is True
    assert _run(api.get_invoice_logs(role_id=ROLE, invoice_id=5001))["success"] is True


@pytest.mark.req("face-exit-before-grounding:1")
def test_invoice_logs_return_parsed_not_raw(api):
    """production **不外露** request_data／response_data（含買受人 email、載具號碼），
    只回白名單化的 `response_parsed`（:77-79、:97-131）。舊 mock 回的是原始 response_data，
    而 services/jgb/invoices.py 三處都讀那個鍵 ⇒ 線上永遠取不到回應內容。"""
    row = _run(api.get_invoice_logs(role_id=ROLE, bill_id=12345))["data"][0]
    assert "response_data" not in row and "request_data" not in row
    assert set(row["response_parsed"]) == {"status", "message", "invoice_number",
                                           "random_number", "invoice_date"}


@pytest.mark.req("face-exit-before-grounding:1")
def test_invoice_logs_have_no_mapping_key(api):
    """production 的成功回應只有 data＋pagination（:60-70）；舊 mock 憑空給了 mapping。"""
    raw = api._mock_get_invoice_logs(ROLE, None, 12345)
    assert "mapping" not in raw


@pytest.mark.req("face-exit-before-grounding:1")
def test_invoice_logs_filters_and_order(api):
    r = _run(api.get_invoice_logs(role_id=ROLE, invoice_id=5002))
    assert [x["id"] for x in r["data"]] == [60002]
    both = _run(api.get_invoice_logs(role_id=ROLE, bill_id=12345, action="invalid"))
    assert both["data"] == []


@pytest.mark.req("face-exit-before-grounding:1")
def test_invoice_log_consumer_reads_parsed(api):
    """診斷引擎改讀 response_parsed（原本只讀 production 不回的 response_data）。"""
    from services.jgb.invoices import diagnose_invoice_logs
    logs = _run(api.get_invoice_logs(role_id=ROLE, bill_id=12345))["data"]
    text = diagnose_invoice_logs(logs, "發票開立了嗎")
    assert "AZ00000123" in text


@pytest.mark.req("face-exit-before-grounding:1")
def test_invoice_log_null_parsed_does_not_crash(api):
    """`parseResponseData` 對空回應回 **null**（:100-103）——消費端不得因此爆。"""
    from services.jgb.invoices import diagnose_invoice_logs
    logs = _run(api.get_invoice_logs(role_id=ROLE, bill_id=12333))["data"]
    assert logs[0]["response_parsed"] is None
    assert diagnose_invoice_logs(logs, "發票開立了嗎")


# ── /payments ───────────────────────────────────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_payments_filters_and_order(api):
    """production：bill_id 比對的是 **payments.paymentable_id**；orderBy id desc（:61-62、:80）。"""
    rows = _run(api.get_payments(role_id=ROLE, user_id="9001"))["data"]
    assert [r["id"] for r in rows] == sorted((r["id"] for r in rows), reverse=True)
    one = api._mock_get_payments(ROLE, "9001", None, rows[0]["bill_id"])
    assert all(r["bill_id"] == rows[0]["bill_id"] for r in one["data"])
    assert one["pagination"]["total"] == len(one["data"])


@pytest.mark.req("face-exit-before-grounding:1")
def test_payments_empty_filter_zeroes_pagination(api):
    empty = api._mock_get_payments(ROLE, "9001", None, 999999)
    assert empty["data"] == [] and empty["pagination"]["total_pages"] == 0


# ── /repairs ────────────────────────────────────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_repairs_filters(api):
    """`is_urgent` 對映 **emergency_status**（:64）——語義曾反轉，不可望文生義。"""
    all_rows = api._mock_get_repairs(ROLE)["data"]
    first = all_rows[0]
    by_status = api._mock_get_repairs(ROLE, status=first["status"])["data"]
    assert all(r["status"] == first["status"] for r in by_status)
    by_estate = api._mock_get_repairs(ROLE, estate_id=first["estate_id"])["data"]
    assert all(r["estate_id"] == first["estate_id"] for r in by_estate)
    assert api._mock_get_repairs(ROLE, estate_id=999999)["data"] == []


# ── /repairs/categories、/roles/{id}/subscription、/iot-manufacturers、
#    /tenants/{uid}/summary、/contracts/{id}/checkin-eligibility ──────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_repair_categories_shape_is_already_faithful(api):
    """`categories()`（:362-389）：{id, name, items:[{id, name, broken_reasons[]}]}。"""
    rows = _run(api.get_repair_categories())["data"]
    for cat in rows:
        assert set(cat) == {"id", "name", "items"}
        for item in cat["items"]:
            assert set(item) == {"id", "name", "broken_reasons"}
            assert isinstance(item["broken_reasons"], list)


@pytest.mark.req("face-exit-before-grounding:1")
def test_subscription_usage_formula_matches_production(api):
    """`limit = plan_estate_limit + coupon + extra`、`remain = max(0, limit - current)`（:35-40）。

    production **不投影** coupon／extra 兩欄，故替身的 limit 必須自洽（55 = 50 + 5）。
    """
    d = _run(api.get_subscription(role_id=ROLE))["data"]
    usage = d["estate_usage"]
    assert usage["limit"] >= d["plan_estate_limit"]
    assert usage["remain"] == max(0, usage["limit"] - usage["current_count"])


@pytest.mark.req("face-exit-before-grounding:1")
def test_iot_manufacturers_projection_excludes_password(api):
    """production 嚴格白名單 select，**不含 manufacturer_password**（:27-31）。"""
    rows = _run(api.get_iot_manufacturers(role_id=ROLE))["data"]
    for row in rows:
        assert set(row) == {"id", "role_id", "manufacturer",
                            "manufacturer_user_id", "is_active"}


@pytest.mark.req("face-exit-before-grounding:1")
def test_tenant_summary_sections(api):
    """`summary()`：tenant_info／contract_summary／bill_summary 三段。"""
    d = _run(api.get_tenant_summary(role_id=ROLE, user_id="9001"))["data"]
    assert {"tenant_info", "contract_summary", "bill_summary"} <= set(d)


@pytest.mark.req("face-exit-before-grounding:1")
def test_checkin_eligibility_shape(api):
    """`show()`：eligible／contract_status／first_bill_status／deposit_status／checkin_blockers。"""
    d = _run(api.get_contract_checkin_eligibility(
        role_id=ROLE, user_id="9001", contract_id=678))["data"]
    assert set(d) == {"contract_id", "eligible", "contract_status",
                      "first_bill_status", "deposit_status", "checkin_blockers"}
    assert set(d["deposit_status"]) == {"required_amount", "paid_amount", "is_fulfilled"}
