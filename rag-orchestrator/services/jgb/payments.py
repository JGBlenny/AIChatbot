"""
JGB 付款日誌診斷引擎

根據 payment-logs API 回傳的金流日誌，判斷付款問題的原因：
- P01：已付款但帳單狀態沒有更新
- P02：信用卡付款失敗
- P03：信用卡自動扣款失敗
"""

from typing import Any


def diagnose_payment_logs(logs: list, user_question: str = "") -> str:
    """
    付款日誌診斷入口

    logs: GET /payment-logs 回傳的 data（list）
    user_question: 用戶原始問題
    """
    if not logs:
        return "查無此帳單的付款紀錄。可能是尚未嘗試付款，或帳單編號不正確。"

    question = user_question.lower() if user_question else ""

    if any(k in question for k in ["沒到帳", "沒更新", "付了款", "已付款"]):
        return _diagnose_payment_not_reflected(logs)
    elif any(k in question for k in ["信用卡失敗", "信用卡錯誤", "刷卡失敗"]):
        return _diagnose_credit_card_failure(logs)
    elif any(k in question for k in ["自動扣款", "自動付款", "auto"]):
        return _diagnose_auto_pay_failure(logs)

    # 預設：列出所有日誌
    return _format_payment_logs(logs)


def _diagnose_payment_not_reflected(logs: list) -> str:
    """P01：已付款但帳單狀態沒有更新"""
    lines = ["以下是此帳單的付款交易紀錄：\n"]

    has_success = False
    has_failure = False

    for log in logs:
        status_text = _get_log_status(log)
        action = log.get("action", "?")
        amount = log.get("amount", "?")
        created = log.get("created_at", "?")
        response = log.get("response", {})

        lines.append(f"• {created[:16]} | {action} | NT$ {amount} | {status_text}")

        if response:
            msg = response.get("Message") or response.get("RtnMsg", "")
            code = response.get("Status") or response.get("RtnCode", "")
            if msg:
                lines.append(f"  回應：[{code}] {msg}")

        if "成功" in status_text or code in ("SUCCESS", "1", 1):
            has_success = True
        else:
            has_failure = True

    if has_success:
        lines.append("\n✅ 有付款成功的紀錄。如果帳單狀態仍未更新，可能是金流回呼延遲，通常 1-2 小時內會自動同步。若超過 24 小時仍未更新，請聯繫客服。")
    elif has_failure:
        lines.append("\n⚠️ 所有付款嘗試都未成功。請確認付款方式是否正確，或嘗試其他繳費方式。")

    return "\n".join(lines)


def _diagnose_credit_card_failure(logs: list) -> str:
    """P02：信用卡付款失敗"""
    cc_keywords = ["信用卡", "credit_card", "授權", "綁卡"]
    cc_logs = [l for l in logs if any(k in str(l.get("action", "")) for k in cc_keywords)]

    if not cc_logs:
        return "查無信用卡付款紀錄，可能是透過其他方式繳費。"

    lines = ["信用卡付款紀錄：\n"]

    for log in cc_logs:
        created = log.get("created_at", "?")
        response = log.get("response", {})
        note = log.get("note", "")
        code = response.get("Status") or response.get("RtnCode", "")
        msg = response.get("Message") or response.get("RtnMsg", "")

        lines.append(f"• {created[:16]}")
        if code:
            lines.append(f"  錯誤碼：{code}")
        if msg:
            lines.append(f"  說明：{msg}")
        if note:
            lines.append(f"  備註：{note}")

    lines.append("\n常見信用卡失敗原因：")
    lines.append("• 卡片餘額不足或額度已滿")
    lines.append("• 卡片已過期")
    lines.append("• 銀行端拒絕交易（安全驗證未通過）")
    lines.append("• 卡號或安全碼輸入錯誤")
    lines.append("\n建議確認卡片狀態後重試，或改用其他繳費方式（ATM/超商）。")

    return "\n".join(lines)


def _diagnose_auto_pay_failure(logs: list) -> str:
    """P03：自動扣款失敗"""
    lines = ["自動扣款相關紀錄：\n"]

    for log in logs:
        created = log.get("created_at", "?")
        action = log.get("action", "?")
        response = log.get("response", {})
        note = log.get("note", "")
        code = response.get("Status") or response.get("RtnCode", "")
        msg = response.get("Message") or response.get("RtnMsg", "")

        lines.append(f"• {created[:16]} | {action}")
        if code:
            lines.append(f"  錯誤碼：{code}")
        if msg:
            lines.append(f"  說明：{msg}")

    lines.append("\n自動扣款失敗可能原因：")
    lines.append("• 信用卡授權已過期，需要租客重新綁定卡片")
    lines.append("• 信用卡額度不足")
    lines.append("• 合約中的自動扣款設定已關閉")
    lines.append("\n建議請租客至繳費頁面手動付款，並確認是否需要重新設定自動扣款。")

    return "\n".join(lines)


def _format_payment_logs(logs: list) -> str:
    """格式化付款日誌列表"""
    lines = [f"查詢到 {len(logs)} 筆付款交易紀錄：\n"]

    for log in logs:
        action = log.get("action", "?")
        amount = log.get("amount", "?")
        created = log.get("created_at", "?")
        status_text = _get_log_status(log)
        response = log.get("response", {})

        lines.append(f"• {created[:16]} | {action} | NT$ {amount} | {status_text}")
        msg = response.get("Message") or response.get("RtnMsg", "")
        if msg:
            lines.append(f"  說明：{msg}")

    return "\n".join(lines)


def _get_log_status(log: dict) -> str:
    """從 response 判斷這筆日誌的狀態"""
    response = log.get("response") or {}
    note = log.get("note", "") or ""

    if isinstance(response, dict):
        code = response.get("Status") or response.get("RtnCode", "")
        msg = response.get("Message") or response.get("RtnMsg", "")
    else:
        code = ""
        msg = str(response)[:30] if response else ""

    if str(code) in ("SUCCESS", "1"):
        return "成功"
    if msg:
        return msg[:30]
    if note:
        return note[:30]
    return "—"
