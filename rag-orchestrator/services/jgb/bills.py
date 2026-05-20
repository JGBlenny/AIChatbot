"""
JGB 帳單診斷引擎

根據帳單詳情 API 回傳的資料，判斷帳單問題的原因：
- B01：帳單發不出去（明細項目未填完整）
- B02：帳單取消不了
- B03：為什麼被收逾期費
- B04：手動到帳失敗
- P04：虛擬帳號過期
"""

from datetime import datetime
from typing import Any


def diagnose_bill(bill: dict, user_question: str = "") -> str:
    """
    帳單診斷入口

    bill: GET /bills/{bill_id} 回傳的 data
    user_question: 用戶原始問題
    """
    if not bill:
        return "查無此帳單資料，請確認帳單編號是否正確。"

    question = user_question.lower() if user_question else ""
    bill_id = bill.get("id", "?")
    title = bill.get("title", f"帳單 {bill_id}")
    bit_status = bill.get("bit_status", 0)

    # 判斷用戶問的是什麼問題
    if any(k in question for k in ["發不出", "無法發送", "發送失敗", "送不出"]):
        return _diagnose_cannot_send(bill)
    elif any(k in question for k in ["取消", "作廢", "cancel"]):
        return _diagnose_cannot_cancel(bill)
    elif any(k in question for k in ["逾期", "延遲金", "滯納金", "late fee"]):
        return _diagnose_late_fee(bill)
    elif any(k in question for k in ["到帳", "收款", "標記已收", "手動"]):
        return _diagnose_manual_complete(bill)
    elif any(k in question for k in ["虛擬帳號", "帳號過期", "ATM", "轉帳失敗"]):
        return _diagnose_atm_expired(bill)

    # 沒有特定問題 → 回傳帳單現況
    return _format_bill_status(bill)


def _diagnose_cannot_send(bill: dict) -> str:
    """B01：帳單為什麼發不出去"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = bill.get("bit_status", 0)
    details = bill.get("details", [])
    blockers = []

    # 條件 1：帳單必須在草稿狀態，否則直接回覆
    if bit_status != 1:
        status_label = _get_status_label(bit_status)
        return f"帳單「{title}」目前狀態為「{status_label}」，已經不在待發送階段，不需要再發送。"

    # 條件 2：帳單明細不能為空
    if not details:
        blockers.append("帳單沒有任何收費項目，請先新增費用明細")

    # 條件 3：檢查明細項目是否完整
    UNIT_TYPE_NAMES = {1: "度數類費用", 2: "日數類費用", 3: "月數類費用"}
    for idx, detail in enumerate(details, 1):
        if not detail.get("active"):
            continue
        # 費用名稱：label > item.name > unit_type 推斷
        item = detail.get("item", {}) or {}
        raw_label = detail.get("label") or item.get("name")
        label = raw_label or UNIT_TYPE_NAMES.get(detail.get("unit_type"), f"第 {idx} 項費用")
        unit_type = detail.get("unit_type")
        unit_price = detail.get("unit_price")
        measurement_before = detail.get("measurement_before")
        measurement_after = detail.get("measurement_after")

        # 費用名稱為空（label=null）：系統可能要求填寫
        if not raw_label:
            blockers.append(f"{label}（第 {idx} 項）尚未設定費用名稱")

        # 度數類（電費、水費等）需要上期/本期度數
        if unit_type == 1:  # 度
            if measurement_after is None or measurement_after == 0:
                blockers.append(f"「{label}」本期度數尚未填寫")
            elif measurement_before is not None and measurement_after < measurement_before:
                blockers.append(f"「{label}」本期度數（{measurement_after}）小於上期度數（{measurement_before}）")
        # 金額不能為 0
        if unit_price is not None and unit_price <= 0 and unit_type != 1:
            blockers.append(f"「{label}」金額為 0，請確認是否正確")

    if not blockers:
        return f"帳單「{title}」看起來沒有明顯問題。如果仍然無法發送，可能是系統端驗證未通過，建議重新整理頁面後再試。"

    reasons = "\n".join(f"• {b}" for b in blockers)
    return f"帳單「{title}」無法發送，可能原因：\n{reasons}"


def _diagnose_cannot_cancel(bill: dict) -> str:
    """B02：帳單為什麼取消不了"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = bill.get("bit_status", 0)
    bill_type = bill.get("type", 1)
    blockers = []

    # 條件 1：只有草稿狀態可取消
    if bit_status != 1:
        status_label = _get_status_label(bit_status)
        blockers.append(f"帳單目前狀態為「{status_label}」，只有「待發送」狀態的帳單才能取消")

    # 條件 2：點退帳單不可取消
    if bill_type == 2:
        blockers.append("此為點退帳單，系統自動產生的帳單無法直接取消")

    if not blockers:
        return f"帳單「{title}」目前為待發送狀態，應該可以取消。如仍無法操作，請重新整理頁面後再試。"

    reasons = "\n".join(f"• {b}" for b in blockers)
    return f"帳單「{title}」無法取消，原因：\n{reasons}"


def _diagnose_late_fee(bill: dict) -> str:
    """B03：為什麼被收逾期費"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    date_expire = bill.get("date_expire")
    complete_at = bill.get("complete_at")
    pay_at = bill.get("pay_at")

    lines = [f"關於帳單「{title}」的逾期費：\n"]

    if date_expire:
        expire_str = _format_date_int(date_expire)
        lines.append(f"• 繳費期限：{expire_str}")

    if pay_at:
        lines.append(f"• 繳費時間：{pay_at}")
    elif complete_at:
        lines.append(f"• 到帳時間：{complete_at}")

    if date_expire and (pay_at or complete_at):
        lines.append("\n逾期費會在超過繳費期限後自動計算。具體計算方式取決於合約中的逾期費設定（緩衝天數、百分比）。")
        lines.append("如需確認逾期費計算細節，請查看合約的「逾期費設定」。")
    else:
        lines.append("\n此帳單尚未繳費。若超過繳費期限仍未付款，系統會依合約設定計算逾期費。")

    return "\n".join(lines)


def _diagnose_manual_complete(bill: dict) -> str:
    """B04：手動到帳失敗"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = bill.get("bit_status", 0)
    complete_at = bill.get("complete_at")
    blockers = []

    # 已到帳
    if bit_status == 16:
        return f"帳單「{title}」已標記為已到帳（完成時間：{complete_at or '未知'}），無需再次操作。"

    # 必須在待繳費或待對帳狀態
    if bit_status not in (2, 8):
        status_label = _get_status_label(bit_status)
        blockers.append(f"帳單目前狀態為「{status_label}」，只有「待繳費」或「待對帳」狀態才能手動標記到帳")

    if not blockers:
        return f"帳單「{title}」狀態正確，應該可以手動標記到帳。如果操作時出現錯誤，可能是系統暫時忙碌，請稍後再試。"

    reasons = "\n".join(f"• {b}" for b in blockers)
    return f"帳單「{title}」無法手動到帳，原因：\n{reasons}"


def _diagnose_atm_expired(bill: dict) -> str:
    """P04：虛擬帳號過期"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    pay_info = bill.get("pay_info") or {}

    # 判斷繳費方式：優先看 pay_info.action，fallback 看 online_payment_action
    action = pay_info.get("action") or bill.get("online_payment_action") or ""
    atm_info = pay_info.get("atm_info") or {}
    expire_ymd = pay_info.get("expire_ymd", "")

    if action != "atm":
        display_action = action or "未設定"
        if not action:
            return f"帳單「{title}」尚未產生繳費方式，可能租客尚未操作付款。"
        return f"帳單「{title}」的繳費方式不是虛擬帳號（ATM），目前為「{display_action}」。"

    if not atm_info:
        return f"帳單「{title}」已設定為 ATM 轉帳，但虛擬帳號尚未產生。租客需先在繳費頁面操作取號。"

    lines = [f"帳單「{title}」的虛擬帳號資訊：\n"]
    lines.append(f"• 銀行：{atm_info.get('bank_name', '?')}（代碼 {atm_info.get('bank_code', '?')}）")
    lines.append(f"• 虛擬帳號：{atm_info.get('atm', '?')}")
    lines.append(f"• 有效期限：{atm_info.get('expire', expire_ymd)}")

    expire = atm_info.get("expire") or expire_ymd
    if expire:
        try:
            expire_date = datetime.strptime(expire[:10], "%Y-%m-%d")
            if datetime.now() > expire_date:
                lines.append("\n⚠️ 此虛擬帳號已過期，轉帳將不會入帳。請在系統中重新產生新的繳費方式。")
            else:
                lines.append(f"\n帳號尚未過期，請在 {expire[:10]} 前完成轉帳。")
        except ValueError:
            lines.append(f"\n有效期限：{expire}")

    return "\n".join(lines)


def _format_bill_status(bill: dict) -> str:
    """格式化帳單現況"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = bill.get("bit_status", 0)
    status_label = _get_status_label(bit_status)
    total = bill.get("total", 0)
    date_expire = bill.get("date_expire")

    lines = [f"帳單「{title}」資訊：\n"]
    lines.append(f"• 狀態：{status_label}")
    lines.append(f"• 金額：NT$ {total:,.0f}")
    if date_expire:
        lines.append(f"• 繳費期限：{_format_date_int(date_expire)}")

    details = bill.get("details", [])
    UNIT_TYPE_NAMES = {1: "度數類費用", 2: "日數類費用", 3: "月數類費用"}
    if details:
        lines.append("\n收費明細：")
        for idx, d in enumerate(details, 1):
            if not d.get("active"):
                continue
            item = d.get("item", {}) or {}
            label = d.get("label") or item.get("name") or UNIT_TYPE_NAMES.get(d.get("unit_type"), f"第 {idx} 項")
            price = d.get("total_price", 0)
            lines.append(f"  - {label}：NT$ {price:,.0f}")

    return "\n".join(lines)


# ── 工具函式 ──

STATUS_LABELS = {
    1: "待發送", 2: "待繳費", 8: "待對帳",
    16: "已繳費", 32: "排定發送", 64: "已失效",
}

def _get_status_label(bit_status: int) -> str:
    return STATUS_LABELS.get(bit_status, f"未知（{bit_status}）")

def _format_date_int(date_val) -> str:
    if isinstance(date_val, int):
        s = str(date_val)
        if len(s) == 8:
            return f"{s[:4]}/{s[4:6]}/{s[6:]}"
    return str(date_val) if date_val else "未設定"
