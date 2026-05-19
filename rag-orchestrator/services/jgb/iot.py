"""
JGB IoT 診斷引擎

根據 iot-manufacturers API 回傳的資料，判斷 IoT 問題的原因：
- IOT02：IoT 廠商帳號綁定失敗
"""

from typing import Any


def diagnose_iot(data: list, user_question: str = "") -> str:
    """
    IoT 診斷入口

    data: GET /iot-manufacturers 回傳的 data（list）
    user_question: 用戶原始問題
    """
    if not data:
        return "目前沒有綁定任何 IoT 廠商。若要使用 IoT 功能（門鎖、電表等），請先至「IoT 裝置」頁面綁定廠商帳號。"

    question = user_question.lower() if user_question else ""

    if any(k in question for k in ["綁定失敗", "綁不上", "無法綁定", "連不上"]):
        return _diagnose_binding_failure(data)

    return _format_iot_status(data)


def _diagnose_binding_failure(data: list) -> str:
    """IOT02：IoT 廠商帳號綁定失敗"""
    lines = ["目前已綁定的 IoT 廠商：\n"]

    has_inactive = False
    for item in data:
        manufacturer = item.get("manufacturer", "?")
        user_id = item.get("manufacturer_user_id", "?")
        is_active = item.get("is_active", 0)
        status = "✅ 啟用" if is_active else "❌ 停用"

        lines.append(f"• {manufacturer}（帳號：{user_id}）— {status}")
        if not is_active:
            has_inactive = True

    if has_inactive:
        lines.append("\n⚠️ 有廠商帳號處於停用狀態。可能原因：")
        lines.append("• 廠商端帳號密碼已變更")
        lines.append("• 廠商端帳號已停用")
        lines.append("\n建議至「IoT 裝置」頁面重新輸入廠商帳號密碼。")
    else:
        lines.append("\n所有 IoT 廠商帳號狀態正常。如果仍有綁定問題：")
        lines.append("• 確認廠商端帳號密碼是否正確")
        lines.append("• 確認該廠商是否支援您的裝置型號")
        lines.append("• 聯繫 IoT 廠商確認帳號狀態")

    return "\n".join(lines)


def _format_iot_status(data: list) -> str:
    """格式化 IoT 綁定狀態"""
    lines = [f"目前綁定 {len(data)} 個 IoT 廠商：\n"]

    for item in data:
        manufacturer = item.get("manufacturer", "?")
        user_id = item.get("manufacturer_user_id", "?")
        is_active = item.get("is_active", 0)
        status = "啟用" if is_active else "停用"

        lines.append(f"• {manufacturer}（帳號：{user_id}）— {status}")

    return "\n".join(lines)
