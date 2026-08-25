"""`/payment-logs` 替身逐條對照 `PaymentLogApiController`（inventory §8 第 5 項）。

這支端點是本輪最嚴重的一格：**回應信封與其他端點都不同**，而舊 mock 回的是
`{mapping, data, pagination}`——production 三個都沒有。消費端
`diagnose_payment_logs` 讀的正是 `data` ⇒ 線上永遠拿到空清單。
"""
import asyncio

import pytest

pytestmark = pytest.mark.unit

ROLE = "20151"
BILL = 900001


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


@pytest.mark.req("face-exit-before-grounding:1")
def test_envelope_matches_production(api):
    """production：`{success, bill_id, payments, payment_logs, summary}`（:110-119）。"""
    raw = api._mock_get_payment_logs(ROLE, None, BILL)
    assert set(raw) == {"success", "bill_id", "payments", "payment_logs", "summary"}
    assert "data" not in raw and "mapping" not in raw and "pagination" not in raw
    assert set(raw["summary"]) == {"payment_count", "payment_log_count",
                                   "has_successful_payment"}


@pytest.mark.req("face-exit-before-grounding:1")
def test_bill_id_is_required_like_production(api):
    """production 缺 bill_id 直接 400（:27-30）——舊 adapter 會送出那個注定失敗的請求。"""
    assert _run(api.get_payment_logs(role_id=ROLE))["success"] is False
    assert _run(api.get_payment_logs(role_id=ROLE, payment_id=9876))["success"] is False
    assert _run(api.get_payment_logs(role_id=ROLE, bill_id=BILL))["success"] is True


@pytest.mark.req("face-exit-before-grounding:1")
def test_adapter_normalizes_logs_into_data_for_the_consumer(api):
    """`data` 是 adapter 正規化出來的（值全部來自 payment_logs），不是 production 的鍵。"""
    r = _run(api.get_payment_logs(role_id=ROLE, bill_id=BILL))
    assert [x["id"] for x in r["data"]] == [50001]
    assert r["payments"] and r["summary"]["payment_count"] == 1
    assert r["bill_id"] == BILL


@pytest.mark.req("face-exit-before-grounding:1")
def test_log_rows_do_not_carry_response(api):
    """`response` 欄存在於 DB，但 controller 的列映射（:92-105）**不投影**。

    舊 mock 憑空給了它，而診斷引擎的原因碼分析正是讀它——
    這條測試確保沒有人再靠一個 production 不會回的欄位寫邏輯。
    """
    rows = _run(api.get_payment_logs(role_id=ROLE, bill_id=BILL))["data"]
    for row in rows:
        assert "response" not in row
        assert set(row) == {"source", "id", "payment_id", "role_id", "transaction_id",
                            "manufacturer", "action", "type", "amount", "note",
                            "created_at"}


@pytest.mark.req("face-exit-before-grounding:1")
def test_payments_rows_match_production_projection(api):
    """payments 列（:63-81）：含手動到帳；price／final_price 被 (float) 轉型。"""
    row = _run(api.get_payment_logs(role_id=ROLE, bill_id=BILL))["payments"][0]
    assert set(row) == {"source", "id", "no", "transaction_id", "user_id", "role_id",
                        "type", "status", "manufacturer", "payment_method", "price",
                        "final_price", "invoice_status", "invoice_number", "note",
                        "payment_completed_at", "created_at", "updated_at"}
    assert isinstance(row["price"], float) and isinstance(row["final_price"], float)


@pytest.mark.req("face-exit-before-grounding:1")
def test_has_successful_payment_uses_status_2(api):
    """`summary.has_successful_payment` = payments 中存在 status == 2（:116）。"""
    raw = api._mock_get_payment_logs(ROLE, None, BILL)
    assert raw["summary"]["has_successful_payment"] is False   # fixture 的 status=1（失敗）
