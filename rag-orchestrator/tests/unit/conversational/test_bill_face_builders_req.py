"""unit:帳務四 fact-builder（billing-conversational-facets 任務 3.1–3.4 / R2–R5, R7）。

決定性規則以 research.md 為準（file:line 皆盤）：
  金流：status 1/32/2/8/16/64；**超商通道停待對帳＝撥付逢 5/15/25 正常時程**；
        status=2 無繳費紀錄 → 引導核對；未知狀態 → 導客服附事實；attach/效期存在性驅動。
  異常：金額逐項引用存值（details）禁重算；可見性機械判（未發送/封存/失效）；
        封存屬合約域退租收尾 → 轉出提示。
  發票：invoice_status 0/1/2 ×「**number 空＝開立未完成**」判準；異常列七類常見原因；
        補開條件（已有有效發票/未付款拒絕）；不虛構號碼日期。
  滯納金：**兩機制**（付款後延遲金 vs 逾期排程開單）；合約欄位存在性驅動（G）；
        滯納金單引用結算存值與公式備註原樣。
"""
import pytest

from services.jgb.bills import (BILL_FACE_BUILDERS, build_payment_flow_facts,
                                build_bill_anomaly_facts, build_invoice_facts,
                                build_late_fee_facts)

pytestmark = pytest.mark.unit


def _bill(status=2, **over):
    b = {"id": 714100, "title": "2026-07 租金", "bit_status": status,   # 外部 API 現況：此欄裝 status 值
         "total": 20000, "date_expire": 20260705, "date_start": 20260701,
         "date_end": 20260731, "pay_at": None, "complete_at": None,
         "online_payment_action": None, "invoice_status": 0, "invoice_number": None}
    b.update(over)
    return b


# ════════ 3.1 build_payment_flow_facts ════════

@pytest.mark.req("billing-conversational-facets:2.2")
def test_flow_cvs_stuck_at_reconcile_gives_payout_schedule():
    out = build_payment_flow_facts(
        _bill(8, pay_at="2026-07-02 10:00:00", online_payment_action="cvs_barcode"), "繳了沒入帳")
    assert "已完成繳費" in out and "尚未入帳" in out
    assert "超商" in out and "5" in out and "15" in out and "25" in out   # 撥付時程
    assert "正常" in out                                                  # 不是異常，安撫
    assert "客服" not in out


@pytest.mark.req("billing-conversational-facets:2.2")
def test_flow_non_cvs_stuck_suggests_support_with_facts():
    out = build_payment_flow_facts(_bill(8, pay_at="2026-07-02 10:00:00"), "怎麼還沒入帳")
    assert "已完成繳費" in out
    assert "客服" in out and "714100" in out                              # 導客服附帳單編號事實


@pytest.mark.req("billing-conversational-facets:2.2")
def test_flow_ready_without_payment_guides_verification():
    out = build_payment_flow_facts(_bill(2), "租客說繳了")
    assert "查無" in out and "繳費" in out
    assert "帳號" in out or "上限" in out                                  # 引導核對
    assert "重發" in out                                                   # 收回重發取得新繳費資訊


@pytest.mark.req("billing-conversational-facets:2.2")
@pytest.mark.parametrize("status,marker", [(1, "尚未發送"), (32, "尚未發送"), (64, "已失效")])
def test_flow_not_sent_or_expired(status, marker):
    out = build_payment_flow_facts(_bill(status), "")
    assert marker in out
    if status in (1, 32):
        assert "看不到" in out                                             # 可見性連動


@pytest.mark.req("billing-conversational-facets:2.2")
def test_flow_completed():
    out = build_payment_flow_facts(
        _bill(16, pay_at="2026-07-02 10:00:00", complete_at="2026-07-02 12:00:00"), "")
    assert "已入帳" in out


@pytest.mark.req("billing-conversational-facets:2.3")
def test_flow_unknown_status_escalates_with_facts():
    out = build_payment_flow_facts(_bill(999), "")
    assert "客服" in out and "714100" in out                               # 不臆測，附事實


@pytest.mark.req("billing-conversational-facets:2.4")
def test_flow_attach_logs_and_va_expiry_existence_driven():
    base = build_payment_flow_facts(_bill(2), "")
    assert "金流事件" not in base and "效期" not in base                    # 缺 → 不虛構
    out = build_payment_flow_facts(
        _bill(2, payment_logs=[{"action": "取號", "created_at": "2026-07-01 09:00:00"},
                               {"action": "notify", "created_at": "2026-07-01 10:00:00"}],
              atm_info={"expire": "2026-12-28"}), "")
    assert "最後金流事件" in out and "notify" in out
    assert "效期" in out and "2026-12-28" in out


# ════════ 3.2 build_bill_anomaly_facts ════════

@pytest.mark.req("billing-conversational-facets:3.2")
def test_anomaly_lists_stored_details_verbatim():
    out = build_bill_anomaly_facts(
        _bill(2, details=[
            {"active": 1, "label": "租金", "total_price": 19000},
            {"active": 1, "item": {"name": "電費"}, "total_price": 1000},
            {"active": 0, "label": "作廢項", "total_price": 999},
        ]), "金額怎麼算的")
    assert "租金" in out and "19,000" in out
    assert "電費" in out and "1,000" in out
    assert "作廢項" not in out                                             # 非 active 不列
    assert "20,000" in out                                                 # 總額存值


@pytest.mark.req("billing-conversational-facets:3.1")
def test_anomaly_prorated_period_facts():
    out = build_bill_anomaly_facts(_bill(2, rate=0.35, days=11), "金額怪怪的")
    assert "比例" in out and "0.35" in out and "11" in out                  # 不足月比例存值


@pytest.mark.req("billing-conversational-facets:3.4")
def test_anomaly_visibility_not_sent():
    out = build_bill_anomaly_facts(_bill(1), "租客看不到帳單")
    assert "尚未發送" in out and "看不到" in out


@pytest.mark.req("billing-conversational-facets:3.3")
def test_anomaly_archived_routes_to_contract_domain():
    out = build_bill_anomaly_facts(_bill(2, is_archived=True), "帳單不見了")
    assert "封存" in out
    assert "退租收尾" in out                                               # 共用出口轉合約域


@pytest.mark.req("billing-conversational-facets:3.4")
def test_anomaly_ready_but_reported_invisible_gives_checks():
    out = build_bill_anomaly_facts(_bill(2), "租客說看不到")
    assert "已發送" in out
    assert "角色" in out or "租客身分" in out                               # 視角排查


# ════════ 3.3 build_invoice_facts ════════

@pytest.mark.req("billing-conversational-facets:4.1")
def test_invoice_not_issued_before_payment():
    out = build_invoice_facts(_bill(2, invoice_status=0), "發票什麼時候開")
    assert "尚未開立" in out
    assert "到帳" in out                                                    # 預設到帳後開立


@pytest.mark.req("billing-conversational-facets:4.1")
def test_invoice_paid_but_not_issued_lists_causes():
    out = build_invoice_facts(
        _bill(16, invoice_status=0, complete_at="2026-07-02 12:00:00"), "怎麼沒發票")
    assert "已到帳" in out and "未開立" in out
    assert "設定" in out                                                    # 指出設定位置


@pytest.mark.req("billing-conversational-facets:4.1")
def test_invoice_issued_with_number():
    out = build_invoice_facts(_bill(16, invoice_status=1, invoice_number="AB12345678"), "")
    assert "已開立" in out and "AB12345678" in out


@pytest.mark.req("billing-conversational-facets:4.1")
def test_invoice_status_one_but_number_empty_is_incomplete():
    out = build_invoice_facts(_bill(16, invoice_status=1, invoice_number=None), "")
    assert "未完成" in out or "失敗" in out                                 # number 空＝失敗判準
    assert "AB" not in out                                                  # 不虛構號碼


@pytest.mark.req("billing-conversational-facets:4.2")
def test_invoice_abnormal_lists_common_causes_and_supplement_rules():
    out = build_invoice_facts(_bill(16, invoice_status=2), "發票異常")
    assert "異常" in out
    assert "字軌" in out and "設定" in out                                  # 七類常見原因（節選）
    assert "補開" in out
    out2 = build_invoice_facts(_bill(2, invoice_status=0), "可以先開發票嗎")
    assert "尚未" in out2                                                   # 未付款情境事實


@pytest.mark.req("billing-conversational-facets:4.4")
def test_invoice_attach_records_existence_driven():
    base = build_invoice_facts(_bill(16, invoice_status=1, invoice_number="AB1"), "")
    assert "作廢" not in base
    out = build_invoice_facts(
        _bill(16, invoice_status=1, invoice_number="AB1",
              invoices=[{"status": 2, "number": "AB1", "invalid_at": "2026-07-01"}]), "")
    assert "作廢" in out and "2026-07-01" in out


# ════════ 3.4 build_late_fee_facts ════════

@pytest.mark.req("billing-conversational-facets:5.1")
def test_late_fee_contract_row_with_settings():
    out = build_late_fee_facts(
        {"id": 84981, "title": "基隆套房", "enable_late_fee": 1,
         "late_fee_percent": 5, "calc_late_fee_buffer_days": 3}, "滯納金怎麼算")
    assert "已啟用" in out and "5" in out and "3" in out                    # 費率/緩衝存值
    assert "付款後" in out and "逾期" in out                                # 兩機制都講
    assert "團隊" in out                                                    # 依團隊機制而定


@pytest.mark.req("billing-conversational-facets:5.1")
def test_late_fee_contract_row_disabled():
    out = build_late_fee_facts(
        {"id": 84981, "title": "基隆套房", "enable_late_fee": 0}, "會收滯納金嗎")
    assert "未啟用" in out


@pytest.mark.req("billing-conversational-facets:5.2")
def test_late_fee_bill_row_with_formula_note():
    out = build_late_fee_facts(
        _bill(2, type=4, title="2026-07 租金-延遲金帳單", total=300,
              date_expire_note={"s3": "租金 20000（遲繳 5 天−緩衝 3 天）X 5%"}), "為什麼收這麼多")
    assert "延遲金" in out and "300" in out                                 # 結算存值
    assert "遲繳 5 天" in out                                               # 公式備註原樣引用


@pytest.mark.req("billing-conversational-facets:5.3")
def test_late_fee_generic_bill_row_degrades_with_guidance():
    out = build_late_fee_facts(_bill(2), "這單會有滯納金嗎")
    assert "合約" in out and "設定" in out                                  # 欄位缺 → 引導查設定
    assert "客服" in out                                                    # 個案減免導客服


# ════════ 註冊表 ════════

@pytest.mark.req("billing-conversational-facets:7.1")
def test_bill_status_prefers_corrected_status_field():
    """jgb2 補正後：status 裝現行狀態、bit_status 回歸歷程位元遮罩 → 讀 status。

    真資料例（preview 2026-07-03）：709739 status=2、bit_status=35（1|2|32 歷程）。
    誤讀 35 會判「未知」導客服，正確是待繳費 → 查無繳費核對引導分支。
    """
    row = _bill(2)
    row["status"] = 2
    row["bit_status"] = 35
    out = build_payment_flow_facts(row, "租客說繳了")
    assert "查無" in out and "繳費" in out
    assert "未知" not in out


def test_bill_status_falls_back_to_bit_status_for_legacy_rows():
    """無 status 鍵的舊列（或 mock）→ 沿用 bit_status，行為不變。"""
    out = build_payment_flow_facts(_bill(2), "租客說繳了")   # _bill 只放 bit_status
    assert "查無" in out and "未知" not in out


def test_all_four_registered():
    assert BILL_FACE_BUILDERS.get("繳費金流排障") is build_payment_flow_facts
    assert BILL_FACE_BUILDERS.get("帳單異常") is build_bill_anomaly_facts
    assert BILL_FACE_BUILDERS.get("發票") is build_invoice_facts
    assert BILL_FACE_BUILDERS.get("滯納金") is build_late_fee_facts
    assert "帳單設定引導" not in BILL_FACE_BUILDERS       # 輕引導無 builder
