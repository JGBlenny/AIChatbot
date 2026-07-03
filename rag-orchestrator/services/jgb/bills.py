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
from typing import Any, Callable, Optional


# ── 帳務面向 fact-builder 註冊表（billing-conversational-facets 元件 2）────────
#
# face（當輪對話面向）命中 → 該面向決定性 fact-builder 接手；未命中/None →
# 原路（jgb_bills 通用格式化、bill_detail/payment_logs/invoice_logs 各自 diagnose 引擎）。
# 面向字面只允許出現在本檔與資料列；金額一律引用系統存值，builder 不重算。

BillFaceBuilder = Callable[[dict, str], str]   # (bill_row, user_question) -> facts 文字

# ── 面向 fact-builders（決定性規則見 billing spec research.md §一–§四）──────
#
# 註：jgb2 已補正 bills API 欄位（2026-07-03）：`status` 裝現行狀態、`bit_status` 為歷程位元遮罩；
# 一律經 `_bill_status()` 讀值（status 優先；無 status 鍵的舊列/mock fallback bit_status）。

def _bill_status(bill: dict) -> int:
    v = bill.get("status")
    return v if isinstance(v, int) else (bill.get("bit_status") or 0)


def _bill_head(bill: dict) -> list:
    """共同開頭 facts：名稱/編號/狀態/金額（系統存值）/期限。"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    lines = [f"帳單「{title}」（編號 {bill.get('id', '?')}）狀態：{_get_status_label(_bill_status(bill))}。"]
    total = bill.get("total")
    if total is not None:
        lines.append(f"帳單金額 NT$ {total:,.0f}（系統存值）。")
    if bill.get("date_expire"):
        lines.append(f"繳費期限：{_format_date_int(bill.get('date_expire'))}。")
    return lines


def build_payment_flow_facts(bill: dict, user_question: str = "") -> str:
    """繳費金流排障（R2.2–2.4；research §一）。

    status 決定金流階段；超商通道停待對帳＝撥付逢 5/15/25 正常時程；
    status=2 查無繳費 → 引導核對；未知 → 導客服附事實；attach/效期存在性驅動。
    """
    status = _bill_status(bill)
    lines = _bill_head(bill)

    if status == 16:
        lines.append(f"款項已入帳（到帳時間 {bill.get('complete_at')}），金流流程已完成。")
    elif status == 8:
        lines.append(f"租客已完成繳費（繳費時間 {bill.get('pay_at')}），款項尚未入帳（待對帳）。")
        action = str(bill.get("online_payment_action") or "")
        if "cvs" in action or "超商" in action:
            lines.append("繳費通道為超商代收：超商撥付入帳為每月 5、15、25 日（遇假日順延），"
                         "目前停在待對帳屬正常時程，等撥付日即會入帳，無需處理。")
        else:
            lines.append("此通道通常於金流通知後即入帳；若已多日未入帳，請聯繫客服核查"
                         f"（可提供：帳單編號 {bill.get('id')}、繳費時間 {bill.get('pay_at')}）。")
    elif status == 2:
        lines.append("帳單已發送、目前系統查無繳費成功紀錄。")
        lines.append("引導核對：請租客確認繳款帳號是否正確、轉帳金額是否超過單筆上限，並保留交易明細；"
                     "若繳費資訊有疑慮，可將帳單收回重發，重發會產生新的繳費資訊。")
    elif status in (1, 32):
        lines.append(f"帳單尚未發送（{_get_status_label(status)}）——租客此時看不到帳單、也還無法繳費；"
                     "發送後才會產生繳費資訊。")
    elif status == 64:
        lines.append("此帳單已失效，無法繳費；如需收款請重新產生帳單。")
    else:
        lines.append(f"無法辨識此帳單的金流狀態，請聯繫客服核查（帳單編號 {bill.get('id')}、"
                     f"狀態值 {status}、繳費時間 {bill.get('pay_at')}）。")

    # attach：payment_logs（secondary_call 附掛；缺 → 不虛構）
    logs = bill.get("payment_logs")
    if isinstance(logs, list) and logs:
        last = logs[-1]
        lines.append(f"最後金流事件：{last.get('action')}（{last.get('created_at')}）。")

    # 繳費資訊效期（G 欄位，存在才輸出）
    expire = (bill.get("atm_info") or {}).get("expire") or (bill.get("pay_info") or {}).get("expire_ymd")
    if expire:
        lines.append(f"繳費帳號效期至 {expire}；若已逾效期，將帳單收回重發即可取得新繳費資訊。")

    return "\n".join(lines)


def build_bill_anomaly_facts(bill: dict, user_question: str = "") -> str:
    """帳單異常診斷（R3.1–3.4；research §二）。

    金額逐項引用存值（details）禁重算；不足月比例存值；可見性機械判
    （未發送/封存/失效）；封存屬合約域退租收尾 → 轉出提示。
    """
    status = _bill_status(bill)
    lines = _bill_head(bill)

    if bill.get("date_start") and bill.get("date_end"):
        period = f"{_format_date_int(bill.get('date_start'))} ~ {_format_date_int(bill.get('date_end'))}"
        lines.append(f"計費期間：{period}。")
    if bill.get("rate") not in (None, "", 1, 1.0):
        days = f"、實際計費 {bill.get('days')} 天" if bill.get("days") else ""
        lines.append(f"本期為不足月比例計費（比例 {bill.get('rate')}{days}），金額按比例計算後存值。")

    details = bill.get("details") or []
    active_items = [d for d in details if d.get("active")]
    if active_items:
        lines.append("收費明細（系統存值逐項）：")
        for d in active_items:
            label = d.get("label") or (d.get("item") or {}).get("name") or "項目"
            lines.append(f"  - {label}：NT$ {d.get('total_price', 0):,.0f}")

    # 可見性機械判（租客看不到帳單）
    if bill.get("is_archived"):
        lines.append("此帳單已封存：不會出現在任何正常帳單列表，催繳也已停止。"
                     "帳單封存屬合約退租收尾範疇，如需處理封存/點退帳單，建議轉由合約領域（退租收尾）接手。")
    elif status in (1, 32):
        lines.append("此帳單尚未發送——租客端看不到是正常的；發送後租客才會在帳務列表看到。")
    elif status == 64:
        lines.append("此帳單已失效，不會顯示於待繳列表。")
    elif status == 2:
        lines.append("此帳單已發送，租客端應可見；若租客仍反映看不到，請確認租客是否以租客身分登入"
                     "（左上角角色切換）並於帳務管理頁查看。")

    return "\n".join(lines)


def build_invoice_facts(bill: dict, user_question: str = "") -> str:
    """發票（R4.1–4.4；research §三）。

    invoice_status 0/1/2 ×「number 空＝開立未完成」判準；異常列常見原因；
    補開/作廢條件事實；attach invoices 存在性驅動；不虛構號碼日期。
    """
    status = _bill_status(bill)
    inv_status = bill.get("invoice_status")
    number = bill.get("invoice_number")
    lines = _bill_head(bill)

    if inv_status == 1 and number:
        lines.append(f"發票已開立，號碼 {number}。")
    elif inv_status == 1 and not number:
        lines.append("發票狀態顯示已開立但查無發票號碼——開立未完成（可能開立失敗），"
                     "請至後台發票稽核確認或進行補開。")
    elif inv_status == 2:
        lines.append("發票狀態為「異常」。常見原因：加值中心字軌不足、發票設定缺失（金鑰/買受人資料）、"
                     "資料錯誤、API 錯誤——可於後台發票稽核查看失敗原因並補開，或聯繫客服協助。")
    else:  # 0 未開立
        if bill.get("complete_at"):
            lines.append(f"款項已到帳（{bill.get('complete_at')}）但發票尚未開立。"
                         "請確認此帳單/合約的自動開立發票設定是否啟用；已啟用仍未開立可於後台補開。")
        else:
            lines.append("發票尚未開立：款項尚未入帳，系統預設於到帳後才開立發票"
                         "（團隊若設定提前開立模式，時點依團隊設定）。")

    # attach：invoices 紀錄（secondary_call 附掛；缺 → 不虛構）
    invoices = bill.get("invoices")
    if isinstance(invoices, list) and invoices:
        latest = invoices[-1]
        inv_map = {0: "未開立", 1: "已開立", 2: "已作廢", 3: "折讓", 4: "作廢折讓"}
        state = inv_map.get(latest.get("status"), str(latest.get("status")))
        extra = f"（作廢時間 {latest.get('invalid_at')}）" if latest.get("invalid_at") else ""
        lines.append(f"發票紀錄：最新一筆狀態為「{state}」{extra}。")

    lines.append("補開規則：帳單已有有效發票時不可重複補開；款項尚未付款的帳單不可開立發票。")
    return "\n".join(lines)


def build_late_fee_facts(row: dict, user_question: str = "") -> str:
    """滯納金（R5.1–5.3；research §四）。

    兩機制分流事實（付款後延遲金 vs 逾期排程開單）；合約欄位存在性驅動（G）；
    滯納金單引用結算存值與公式備註原樣；個案減免導客服。
    """
    lines = []

    # 合約列（含滯納金設定欄位，G：preview 三欄）
    if "enable_late_fee" in row:
        title = row.get("title", f"合約 {row.get('id', '?')}")
        if row.get("enable_late_fee"):
            lines.append(f"合約「{title}」的滯納金設定：已啟用，"
                         f"費率 {row.get('late_fee_percent', '—')}%、"
                         f"緩衝 {row.get('calc_late_fee_buffer_days', '—')} 天。")
            lines.append("實際結算依團隊採用的機制而定，系統有兩種："
                         "一、付款後結算的延遲金（租金 ×（實際付款日 − 繳費期限 − 緩衝天數）× 費率，"
                         "到帳當下開立獨立延遲金帳單）；"
                         "二、對逾期未付款帳單的排程開單（依團隊為階梯費率或固定金額，到期日規則各異）。"
                         "以系統實際產生的滯納金帳單為準。")
        else:
            lines.append(f"合約「{title}」的滯納金設定：未啟用——此合約逾期不會自動產生滯納金帳單。")
        return "\n".join(lines)

    # 滯納金/延遲金帳單列（type=4 罰款或標題含滯納/延遲金）
    title = str(row.get("title") or "")
    if row.get("type") == 4 or "延遲金" in title or "滯納" in title:
        lines = _bill_head(row)
        note = (row.get("date_expire_note") or {}).get("s3") if isinstance(row.get("date_expire_note"), dict) else None
        note = note or ((row.get("late_fee_info") or {}).get("note") if isinstance(row.get("late_fee_info"), dict) else None)
        if note:
            lines.append(f"系統結算備註（原樣）：{note}")
        lines.append("此金額為系統依合約設定結算之存值；每張逾期帳單各自結算、不累加，"
                     "滯納金帳單本身逾期不會再產生滯納金。")
        return "\n".join(lines)

    # 一般帳單列（無合約設定欄位可判 → 降級引導）
    lines = _bill_head(row)
    lines.append("是否產生滯納金取決於該合約的滯納金設定與團隊採用的結算機制"
                 "（本查詢未含合約設定資料）——請查看合約的滯納金設定，或以系統實際產生的滯納金帳單為準；"
                 "個案減免或調整請聯繫客服處理。")
    return "\n".join(lines)


BILL_FACE_BUILDERS: dict[str, BillFaceBuilder] = {
    "繳費金流排障": build_payment_flow_facts,
    "帳單異常": build_bill_anomaly_facts,
    "發票": build_invoice_facts,
    "滯納金": build_late_fee_facts,
    # "帳單設定引導" 為輕引導（select='category'），無 builder
}


def face_bill_response(endpoint: str, data: Any, user_question: str = "",
                       face: Optional[str] = None) -> Optional[str]:
    """帳務面向分流入口：face 命中註冊表且有資料列才接手，否則回 None（呼叫端走原路）。

    list 正規化為第一列（引擎收斂本為單筆；secondary_call 附掛資料在主列鍵上）。
    """
    builder = BILL_FACE_BUILDERS.get(face) if face else None
    if builder is None:
        return None
    if isinstance(data, dict):
        row = data
    elif isinstance(data, list) and data:
        row = data[0]
    else:
        return None   # 無列可 ground → 原路（查無訊息等既有行為）
    return builder(row, user_question)


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
    bit_status = _bill_status(bill)

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
    bit_status = _bill_status(bill)
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
    bit_status = _bill_status(bill)
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
    bit_status = _bill_status(bill)
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
    bit_status = _bill_status(bill)
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
