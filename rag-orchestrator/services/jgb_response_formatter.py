"""
JGB API 回應格式化

將 JGB API 的 { success, mapping, data, pagination } 回應
格式化為用戶易讀的文字。使用 mapping 翻譯狀態碼。
"""

from typing import Any

# 欄位中文對照
FIELD_LABELS = {
    "id": "編號",
    "title": "標題",
    "estate_name": "物件",
    "total": "金額",
    "amount": "金額",
    "rent": "月租金",
    "date_expire": "繳費期限",
    "date_start": "起始日",
    "date_end": "結束日",
    "pay_at": "繳費時間",
    "complete_at": "完成時間",
    "completed_at": "完成時間",
    "paid_at": "付款時間",
    "created_at": "建立時間",
    "bit_status": "狀態",
    "status": "狀態",
    "invoice_status": "發票狀態",
    "invoice_number": "發票號碼",
    "number": "發票號碼",
    "category": "類別",
    "manufacturer": "金流商",
    "payment_method": "付款方式",
    "name": "姓名",
    "email": "Email",
    "phone": "電話",
    "is_registered": "已註冊",
    "is_email_verified": "Email 已驗證",
    "category_name": "類別",
    "item_name": "項目",
    "is_emergency": "緊急",
    "assigned_vendor": "維修廠商",
    "scheduled_date": "預約日期",
    "cost": "費用",
    "eligible": "可點交",
    "contract_status": "合約狀態",
    "first_bill_paid": "首期帳單已繳",
    "deposit_required": "應繳押金",
    "deposit_paid": "已繳押金",
    "blockers": "未通過項目",
    "city": "城市",
    "district": "區域",
    "address": "地址",
    "deposit_amount": "押金",
    "allow_early_termination": "可提前終止",
    "early_termination_days": "提前終止天數",
    "active_count": "進行中",
    "history_count": "歷史",
    "unpaid_count": "待繳",
    "total_count": "總計",
    "on_time_ratio": "準時率",
    "in_progress_count": "進行中",
}

# 跳過不顯示的欄位
SKIP_KEYS = {
    "success", "pagination", "mapping", "updated_at",
    "estate_id", "contract_id", "bill_id", "currency",
    "is_auto_generate_invoice",
}

# 金額類欄位
MONEY_KEYS = {
    "total", "amount", "rent", "cost",
    "deposit_amount", "deposit_required", "deposit_paid",
}

# 日期整數欄位（YYYYMMDD）
DATE_INT_KEYS = {"date_expire", "date_start", "date_end"}

# 巢狀 dict 的區段標題
SECTION_LABELS = {
    "tenant_info": "租客資訊",
    "contract_summary": "合約摘要",
    "bill_summary": "帳單摘要",
    "repair_summary": "修繕摘要",
}


def format_jgb_response(api_result: dict, endpoint: str = "", user_question: str = "", form_data: dict = None) -> str:
    """
    格式化 JGB API 回應（進入點）

    endpoint: API endpoint 名稱（如 jgb_contracts），用於決定走哪個判斷引擎
    user_question: 用戶原始問題，用於判斷要檢查什麼操作
    form_data: 表單收集的資料（含用戶輸入的關鍵字）
    """
    mapping = api_result.get("mapping", {})
    data = api_result.get("data", [])

    # 合約相關 endpoint → 走合約判斷引擎
    if endpoint in ("jgb_contracts", "jgb_contract_checkin"):
        return _format_contracts(data, user_question, form_data=form_data)

    # 其他 endpoint → 通用格式化
    if isinstance(data, dict):
        return _format_single(data, mapping)

    if not data:
        return "查無資料。"

    lines = [f"查詢到 {len(data)} 筆資料：\n"]
    for i, item in enumerate(data, 1):
        lines.append(f"**【第 {i} 筆】**")
        lines.append(_format_single(item, mapping))
        if i < len(data):
            lines.append("---")
    return "\n".join(lines)


def _format_contracts(data: Any, user_question: str, form_data: dict = None) -> str:
    """合約資料走判斷引擎"""
    from services.jgb.contracts import format_contract_response

    keyword = ""
    if form_data:
        keyword = form_data.get("contract_keyword", "") or form_data.get("keyword", "")

    return format_contract_response(data, user_question=user_question, keyword=keyword)


def _format_single(item: dict, mapping: dict) -> str:
    """格式化單筆資料"""
    lines: list[str] = []

    for key, value in item.items():
        if key in SKIP_KEYS or value is None:
            continue

        label = FIELD_LABELS.get(key, key)

        # 巢狀 dict → 遞迴
        if isinstance(value, dict):
            section_title = SECTION_LABELS.get(key, label)
            lines.append(f"\n**{section_title}：**")
            lines.append(_format_single(value, mapping))
            continue

        # mapping 翻譯狀態碼
        value = _translate(key, value, mapping)

        # 格式化
        value = _format_value(key, value)

        lines.append(f"　{label}：{value}")

    return "\n".join(lines)


def _translate(key: str, value: Any, mapping: dict) -> Any:
    """用 mapping 翻譯狀態碼"""
    str_val = str(value)

    # 直接 key 對照（如 status, payment_method）
    if key in mapping and str_val in mapping[key]:
        return mapping[key][str_val]

    # bit_status 特殊處理
    if key == "bit_status" and "bit_status" in mapping and str_val in mapping["bit_status"]:
        return mapping["bit_status"][str_val]

    return value


def _format_value(key: str, value: Any) -> str:
    """格式化欄位值"""
    if isinstance(value, bool):
        return "是" if value else "否"

    if key in MONEY_KEYS and isinstance(value, (int, float)):
        return f"NT$ {value:,.0f}"

    if key in DATE_INT_KEYS and isinstance(value, int):
        s = str(value)
        if len(s) == 8:
            return f"{s[:4]}/{s[4:6]}/{s[6:]}"

    if key == "on_time_ratio":
        return f"{value}%"

    if isinstance(value, list):
        return "、".join(str(v) for v in value) if value else "無"

    return str(value)
