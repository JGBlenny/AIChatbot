"""
JGB 物件（Estate）領域檔

estate-conversational-facets 元件 2：物件現值決定性解碼。
- status 位元轉譯用程式不用 LLM（research 定案 #1：兩軸模型——合約軸 status
  1/2/4/8 × 刊登軸 is_open；本 API 硬過濾 is_open=1，查得到即隱含刊登中）。
- sentinel（wrapper 查無回 found:False）→「非刊登中」弱信號口徑，
  不得斷言已刪除（G-E1 天花板，見 estate-api-contract.md）。
- 個資紅線：facts 只出 title/display_address/serial_id——
  address/full_address/經緯度不出口。
- 面向字面只允許出現在本檔與資料列；face=None 恆等（零回歸慣例）。
"""

from typing import Any, Callable, Optional

# 合約軸 status 位元 → 中文（Estate.php:57-64；真碼查詢全以 == 比對當互斥枚舉用，
# 未知值原樣標注防組合值——validate-design Issue 3）
ESTATE_STATUS_ZH: dict[int, str] = {
    1: "未刊登（剛建立）",
    2: "刊登中",
    4: "洽談中（已綁合約、尚未完成簽署）",
    8: "租約中",
}


def estate_status_zh(status: Any) -> str:
    try:
        return ESTATE_STATUS_ZH.get(int(status), f"狀態值 {status}（系統未定義的狀態，請以後台顯示為準）")
    except (TypeError, ValueError):
        return "狀態不明"


def build_estate_status_facts(estate: dict, detail: Optional[dict] = None,
                              user_question: str = "") -> str:
    """物件現況診斷 facts（R4.2/R4.3）。

    sentinel 優先（引擎 0-row 短路對策——design Issue 1）；status 決定性轉譯；
    建約決策樹：刊登中＋contract_required_fields 欄位齊 → 可建約；缺欄列 label；
    非刊登中 → 建約前提為刊登中（EstateController.php:279-283 口徑）。
    """
    # ── sentinel：查無（打錯字與非刊登雙情境併述；不得斷言已刪除）──
    if estate.get("found") is False:
        kw = estate.get("keyword") or "該物件"
        return (f"在對外刊登清單中找不到「{kw}」。請先確認物件名稱是否正確；"
                "若名稱無誤，代表該物件目前非刊登中（可能尚未刊登或已下架）——"
                "刊登狀態可到後台物件總表確認。要讓物件可被查詢與建約，需先完成刊登。")

    title = estate.get("title") or f"物件 {estate.get('id', '?')}"
    lines = [f"物件「{title}」"]
    serial = estate.get("serial_id")
    if serial:
        lines[0] += f"（編號 {serial}）"
    display_addr = estate.get("display_address") or estate.get("full_display_address")
    if display_addr:
        lines[0] += f"，對外顯示地址：{display_addr}"
    lines[0] += "："

    status = estate.get("status")
    lines.append(f"目前狀態：{estate_status_zh(status)}（在對外刊登清單中，隱含刊登軸為刊登中）。")

    # ── 建約決策樹 ──
    is_published = False
    try:
        is_published = int(status) == 2
    except (TypeError, ValueError):
        pass
    # 建約前提句只講合約軸（status），不得說「非刊登中」——status=4/8 物件
    # 查得到＝對外刊登中（is_open=1），混軸會誤導（unit: status4_no_axis_confusion）
    zh = estate_status_zh(status)
    crf = (detail or {}).get("contract_required_fields") if detail else None
    if crf is not None:
        if crf.get("all_filled"):
            if is_published:
                lines.append("建約條件：必填欄位皆已齊備，此物件目前可建立合約。")
            else:
                lines.append(f"建約條件：必填欄位已齊備；惟依系統規則，建立新合約需物件狀態為"
                             f"「刊登中」——此物件目前為「{zh}」。")
        else:
            missing = [f.get("label") or f.get("field") or "?"
                       for f in (crf.get("fields") or []) if not f.get("is_filled")]
            if missing:
                lines.append("建約條件：尚缺必填欄位——" + "、".join(missing) +
                             "。補齊後即可建立合約" +
                             ("。" if is_published else f"（另需物件狀態為「刊登中」，目前為「{zh}」）。"))
    elif not is_published:
        lines.append(f"提醒：依系統規則，建立新合約需物件狀態為「刊登中」——此物件目前為「{zh}」。")

    rent = estate.get("rent")
    if rent is not None:
        lines.append(f"刊登租金：{rent} {estate.get('currency') or ''}（引用系統存值）。".replace("  ", " "))
    return "\n".join(lines)


# face → builder（面向名與 category_config 子分類一致）
EstateFaceBuilder = Callable[[dict, Optional[dict], str], str]
ESTATE_FACE_BUILDERS: dict[str, EstateFaceBuilder] = {
    "物件現況診斷": build_estate_status_facts,
}


def face_estate_response(rows: Any, user_question: str = "",
                         face: Optional[str] = None) -> Optional[str]:
    """face 分發入口（jgb_response_formatter 掛 jgb_estate_status endpoint）。

    face=None／未註冊 → None 恆等（呼叫端走原路，零回歸慣例）。
    rows[0] 為引擎鎖定列（sentinel 亦然）；detail 由引擎 secondary_call attach
    於列上（鍵名 'detail'，config result 形狀）。
    """
    if not face:
        return None
    builder = ESTATE_FACE_BUILDERS.get(face)
    if not builder:
        return None
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    detail_rows = row.get("detail")
    detail = None
    if isinstance(detail_rows, list) and detail_rows:
        detail = detail_rows[0]
    elif isinstance(detail_rows, dict):
        detail = detail_rows
    return builder(row, detail, user_question)
