"""
JGB 訂閱方案診斷引擎

根據 subscription API 回傳的資料，判斷訂閱/物件問題的原因：
- E01：為什麼不能新增物件
- E02：物件為什麼突然全部下架
- S01：訂閱扣款失敗導致功能異常
"""

from typing import Any


def diagnose_subscription(data: dict, user_question: str = "") -> str:
    """
    訂閱方案診斷入口

    data: GET /roles/{role_id}/subscription 回傳的 data
    user_question: 用戶原始問題
    """
    if not data:
        return "查無訂閱方案資訊。"

    question = user_question.lower() if user_question else ""

    if any(k in question for k in ["不能新增", "無法新增", "新增物件", "物件上限"]):
        return _diagnose_cannot_add_estate(data)
    elif any(k in question for k in ["下架", "全部下架", "物件消失"]):
        return _diagnose_estates_delisted(data)
    elif any(k in question for k in ["扣款失敗", "訂閱失敗", "方案異常", "功能異常"]):
        return _diagnose_subscription_payment(data)

    return _format_subscription_status(data)


def _diagnose_cannot_add_estate(data: dict) -> str:
    """E01：為什麼不能新增物件"""
    is_subscribed = data.get("is_subscribed", 0)
    plan_type = data.get("plan_type", "")
    plan_name = data.get("plan_name", "")
    usage = data.get("estate_usage", {})
    current = usage.get("current_count", 0)
    limit = usage.get("limit", 0)
    remain = usage.get("remain", 0)
    blockers = []

    if not is_subscribed:
        blockers.append("目前沒有訂閱方案，需先訂閱 JGB 方案才能新增物件")

    if limit > 0 and remain <= 0:
        blockers.append(f"物件數量已達上限（目前 {current} 間 / 上限 {limit} 間）")

    if plan_type == "trial":
        blockers.append("目前為試用方案，物件數量有限。建議升級為基本或進階方案以增加額度")

    if not blockers:
        return f"目前方案「{plan_name}」物件額度：{current}/{limit}（剩餘 {remain} 間），看起來還有額度可以新增。如仍無法新增，請確認物件必填欄位是否已填完整。"

    reasons = "\n".join(f"• {b}" for b in blockers)
    header = f"目前方案：{plan_name}，物件使用量：{current}/{limit}\n"
    return f"{header}\n無法新增物件，原因：\n{reasons}"


def _diagnose_estates_delisted(data: dict) -> str:
    """E02：物件為什麼突然全部下架"""
    is_subscribed = data.get("is_subscribed", 0)
    plan_name = data.get("plan_name", "")
    plan_end = data.get("plan_end_ymd")

    lines = [f"目前訂閱狀態：{'有效' if is_subscribed else '無訂閱'}"]
    if plan_name:
        lines.append(f"方案：{plan_name}")
    if plan_end:
        lines.append(f"到期日：{_format_date_int(plan_end)}")

    if not is_subscribed:
        lines.append("\n⚠️ 訂閱方案已失效。物件全部下架通常是因為：")
        lines.append("• 方案到期後未續約")
        lines.append("• 訂閱扣款失敗導致方案中止")
        lines.append("\n建議重新訂閱方案，訂閱成功後物件會自動恢復上架。")
    else:
        lines.append("\n目前訂閱仍有效。如果物件下架，可能原因：")
        lines.append("• 訂閱扣款在上一個週期失敗，系統自動下架後又恢復")
        lines.append("• 超出物件上限（新增物件導致其他物件被暫時下架）")
        lines.append("\n如問題持續，請聯繫客服。")

    return "\n".join(lines)


def _diagnose_subscription_payment(data: dict) -> str:
    """S01：訂閱扣款失敗"""
    is_subscribed = data.get("is_subscribed", 0)
    plan_name = data.get("plan_name", "")
    plan_price = data.get("plan_price", 0)
    plan_cycle = data.get("plan_cycle", "")

    lines = []
    if is_subscribed:
        lines.append(f"目前訂閱方案「{plan_name}」仍有效。")
    else:
        lines.append("⚠️ 目前沒有有效的訂閱方案。")

    if plan_price:
        lines.append(f"方案費用：NT$ {plan_price:,.0f}/{plan_cycle}")

    lines.append("\n訂閱扣款失敗常見原因：")
    lines.append("• 信用卡已過期或額度不足")
    lines.append("• 信用卡授權已失效，需重新綁定")
    lines.append("• 銀行端拒絕定期定額交易")
    lines.append("\n建議至「收款設置」頁面確認並更新付款方式。")

    return "\n".join(lines)


def _format_subscription_status(data: dict) -> str:
    """格式化訂閱方案現況"""
    plan_name = data.get("plan_name", "無")
    is_subscribed = data.get("is_subscribed", 0)
    usage = data.get("estate_usage", {})
    current = usage.get("current_count", 0)
    limit = usage.get("limit", 0)
    remain = usage.get("remain", 0)
    plan_end = data.get("plan_end_ymd")

    lines = ["訂閱方案資訊：\n"]
    lines.append(f"• 狀態：{'有效' if is_subscribed else '無訂閱'}")
    lines.append(f"• 方案：{plan_name}")
    if plan_end:
        lines.append(f"• 到期日：{_format_date_int(plan_end)}")
    lines.append(f"• 物件使用量：{current}/{limit}（剩餘 {remain} 間）")

    return "\n".join(lines)


def _format_date_int(date_val) -> str:
    if isinstance(date_val, int):
        s = str(date_val)
        if len(s) == 8:
            return f"{s[:4]}/{s[4:6]}/{s[6:]}"
    return str(date_val) if date_val else "未設定"
