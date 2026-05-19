"""
JGB 發票日誌診斷引擎

根據 invoice-logs API 回傳的日誌，判斷發票問題的原因：
- I01：發票為什麼沒有開出來
- I02：發票為什麼作廢不了
"""

from typing import Any


def diagnose_invoice_logs(logs: list, user_question: str = "") -> str:
    """
    發票日誌診斷入口

    logs: GET /invoice-logs 回傳的 data（list）
    user_question: 用戶原始問題
    """
    if not logs:
        return "查無此帳單的發票日誌。可能是尚未嘗試開立發票，或帳單編號不正確。"

    question = user_question.lower() if user_question else ""

    if any(k in question for k in ["沒開", "沒有開", "開不出", "未開立", "開立失敗"]):
        return _diagnose_issue_failure(logs)
    elif any(k in question for k in ["作廢", "不能作廢", "作廢失敗"]):
        return _diagnose_invalid_failure(logs)

    return _format_invoice_logs(logs)


def _diagnose_issue_failure(logs: list) -> str:
    """I01：發票為什麼沒有開出來"""
    issue_keywords = ["開立", "issue", "觸發開立"]
    issue_logs = [l for l in logs if any(k in str(l.get("action", "")) for k in issue_keywords)]

    if not issue_logs:
        return "查無發票開立紀錄。可能的原因：\n• 帳單尚未到帳（需繳費完成後才會觸發開立）\n• 合約未設定自動開立發票\n• 發票廠商設定尚未完成"

    lines = ["發票開立紀錄：\n"]

    has_success = False
    for log in issue_logs:
        created = log.get("created_at", "?")
        response = log.get("response_data", {})
        note = log.get("note", "")
        http_code = log.get("http_code")
        rtn_code = response.get("RtnCode", "")
        rtn_msg = response.get("RtnMsg", "")
        inv_number = response.get("InvoiceNumber", "")

        lines.append(f"• {created[:16]}")
        if inv_number:
            lines.append(f"  發票號碼：{inv_number}")
            has_success = True
        if rtn_code:
            lines.append(f"  回應碼：{rtn_code}")
        if rtn_msg:
            lines.append(f"  說明：{rtn_msg}")
        if note:
            lines.append(f"  備註：{note}")
        if http_code and http_code != 200:
            lines.append(f"  HTTP 狀態：{http_code}")

    if has_success:
        lines.append("\n✅ 發票已成功開立。如果帳單上仍顯示「未開立」，可能是同步延遲。")
    else:
        lines.append("\n⚠️ 發票開立嘗試未成功。常見原因：")
        lines.append("• 發票廠商 API 回傳錯誤（如重複開立）")
        lines.append("• 買受人資訊不完整")
        lines.append("• 發票廠商系統暫時異常")

    return "\n".join(lines)


def _diagnose_invalid_failure(logs: list) -> str:
    """I02：發票為什麼作廢不了"""
    invalid_keywords = ["作廢", "invalid"]
    invalid_logs = [l for l in logs if any(k in str(l.get("action", "")) for k in invalid_keywords) and "折讓" not in str(l.get("action", ""))]

    if not invalid_logs:
        return "查無發票作廢紀錄。如需作廢發票，請在系統中操作。若按鈕無法點擊，可能是發票狀態不允許作廢（如已折讓）。"

    lines = ["發票作廢紀錄：\n"]

    for log in invalid_logs:
        created = log.get("created_at", "?")
        response = log.get("response_data", {})
        note = log.get("note", "")
        rtn_code = response.get("RtnCode", "")
        rtn_msg = response.get("RtnMsg", "")

        lines.append(f"• {created[:16]}")
        if rtn_code:
            lines.append(f"  回應碼：{rtn_code}")
        if rtn_msg:
            lines.append(f"  說明：{rtn_msg}")
        if note:
            lines.append(f"  備註：{note}")

    lines.append("\n常見發票無法作廢的原因：")
    lines.append("• 發票已超過當月或規定的作廢時限")
    lines.append("• 發票已進行折讓，需先取消折讓")
    lines.append("• 發票廠商端處理中或系統異常")

    return "\n".join(lines)


def _format_invoice_logs(logs: list) -> str:
    """格式化發票日誌列表"""
    ACTION_LABELS = {"issue": "開立", "invalid": "作廢", "allowance": "折讓", "search": "查詢"}

    lines = [f"查詢到 {len(logs)} 筆發票日誌：\n"]

    for log in logs:
        action = ACTION_LABELS.get(log.get("action", ""), log.get("action", "?"))
        created = log.get("created_at", "?")
        response = log.get("response_data", {})
        rtn_msg = response.get("RtnMsg", "")
        inv_number = response.get("InvoiceNumber", "")

        summary = f"• {created[:16]} | {action}"
        if inv_number:
            summary += f" | {inv_number}"
        if rtn_msg:
            summary += f" | {rtn_msg}"
        lines.append(summary)

    return "\n".join(lines)
