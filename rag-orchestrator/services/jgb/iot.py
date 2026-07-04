"""
JGB IoT 診斷引擎

根據 iot-manufacturers API 回傳的資料，判斷 IoT 問題的原因：
- IOT02：IoT 廠商帳號綁定失敗

電表面向 fact-builder（iot-conversational-facets 元件 4）：
- build_meter_facts：未給電四分支決定性判因（research.md 主題 1/2 定案語義）。
  面向字面只允許出現在本檔與資料列；度數/餘額/單價一律引用存值不重算；
  斷電/復電措辭歸電表端（廠商行為）；不代執行遠端控制（只指路）。
"""

from typing import Any, Callable

MeterFaceBuilder = Callable[[dict, str], str]   # (meter_row, user_question) -> facts 文字

_MANUFACTURER_ZH = {"DAE": "台科電", "Miezo": "鳴周", "SkyWatch": "SkyWatch"}


def _meter_head(meter: dict) -> list:
    """共同開頭 facts：名稱/物件/廠牌/現值（度數為 JGB 側最後同步值，引用存值）。"""
    name = meter.get("name") or f"電表 {meter.get('id', '?')}"
    estate = meter.get("estate_name") or ""
    vendor = _MANUFACTURER_ZH.get(meter.get("manufacturer") or "", meter.get("manufacturer") or "")
    lines = [f"電表「{name}」" + (f"（物件：{estate}）" if estate else "") +
             (f"，廠牌 {vendor}" if vendor else "") + "："]
    reading = meter.get("current_reading")
    if reading is not None:
        lines.append(f"目前度數 {reading} 度（JGB 側最後同步值）。")
    return lines


def build_meter_facts(meter: dict, user_question: str = "") -> str:
    """電表排障（R2.2–2.5；research.md 主題 1/2）。

    決定性四分支：離線優先（截至 synced_at 快照措辭；離線不引用 is_poweron 下供電結論
    ——J-I1 防護）→ 儲值耗盡（電表端自動斷/復電）→ 供電關閉（無斷電原因紀錄不臆測）
    → 供電正常轉硬體。每小時同步一次為機制事實；度數/餘額引用存值。
    """
    lines = _meter_head(meter)
    manufacturer = meter.get("manufacturer") or ""
    vendor = _MANUFACTURER_ZH.get(manufacturer, manufacturer or "廠商")

    # ── 分支①：離線優先（其他欄位皆為最後同步快照，不下供電結論）──
    if not meter.get("is_online"):
        synced = meter.get("synced_at")
        if synced:
            lines.append(f"電表目前離線——以下皆為截至 {synced} 的最後同步狀態，"
                         "非即時值（系統每小時同步一次）。")
        else:
            lines.append("電表目前離線（此電表無最後同步時間可參考）。")
        if manufacturer == "DAE":
            lines.append("常見原因：台科電雲端帳號的密碼變更或未開通 API 服務——"
                         "會使該帳號下所有電表整批停止同步。請到「IoT 裝置」頁"
                         "重新驗證廠商帳號密碼；另請確認設備電源與網路正常後等下一次同步。")
        else:
            lines.append("請確認設備電源與網路正常（可嘗試重啟設備），等下一次同步再確認。")
        lines.append(f"若仍持續離線，請聯繫{vendor}處理，並提供電表名稱與所在物件資訊。")
        return "\n".join(lines)

    # ── 分支②：儲值耗盡（電表端自動斷電；儲值入帳後電表端自動復電）──
    balance = meter.get("balance")
    available = meter.get("available_meter")
    exhausted = (balance is not None and float(balance) <= 0) or \
                (available is not None and float(available) <= 0)
    if not meter.get("is_poweron"):
        if meter.get("enable_topup") and exhausted:
            lines.append(f"儲值餘額 {balance} 元、可用 {available} 度（系統存值）——"
                         "儲值模式下餘額耗盡時電表端會自動斷電。")
            lines.append("處理方式：請租客完成儲值（前台儲值會產生儲值帳單），"
                         "款項入帳後電表端會自動復電，不需另外操作。")
            return "\n".join(lines)
        # 供電關閉（非儲值耗盡）：無斷電原因紀錄，不臆測誰關的
        lines.append("供電目前為關閉狀態。系統沒有斷電原因的紀錄，無法判斷是誰或何時關閉。")
        if meter.get("enable_topup") and balance is not None:
            lines.append(f"（儲值餘額 {balance} 元、可用 {available} 度，餘額充足——可排除儲值因素。）")
        lines.append("處理路徑：可於「IoT 裝置」頁切換該電表的供電模式（強制供電／斷電／儲值模式）。")
        return "\n".join(lines)

    # ── 分支④：供電正常 → 轉硬體/確認問對表 ──
    lines.append("供電狀態正常、設備在線。若租客仍反映沒電：可能是室內迴路、跳電或"
                 f"電表硬體問題——請聯繫{vendor}協助檢測；也請確認反映的是否為這顆電表。")
    if meter.get("enable_topup") and balance is not None:
        lines.append(f"儲值餘額 {balance} 元、可用 {available} 度（系統存值）。")
    return "\n".join(lines)


# ── 電表面向 fact-builder 註冊表 ────────────────────────────────────────────
#
# face 命中 → builder 接手；未命中/None → 原路（diagnose_iot／通用格式化，零回歸）。

METER_FACE_BUILDERS: dict[str, MeterFaceBuilder] = {
    "電表排障": build_meter_facts,
}


def face_meter_response(data, user_question: str, face: str):
    """jgb_meters 的 face 分發入口：face 命中才接手（回 None → formatter 走原路）。"""
    builder = METER_FACE_BUILDERS.get(face) if face else None
    if builder is None:
        return None
    rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
    if not rows:
        return None
    return builder(rows[0], user_question)


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
