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
    "estate_title": "物件",
    "estate_name": "物件",
    "total": "金額",
    "amount": "金額",
    "price": "金額",
    "final_price": "實付金額",
    "total_amt": "發票金額",
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
    "type": "類型",
    "category": "類別",
    "manufacturer": "金流商",
    "payment_method": "付款方式",
    "note": "備註",
    "name": "姓名",
    "email": "Email",
    "phone": "電話",
    "is_registered": "已註冊",
    "is_email_verified": "Email 已驗證",
    "category_name": "類別",
    "item_name": "項目",
    "emergency_status": "急迫性",
    "manufacturer_name": "維修廠商",
    "manufacturer_phone": "廠商電話",
    "broken_reason": "損壞原因",
    "broken_note": "補充說明",
    "estate_full_address": "地址",
    "estate_room_number": "房號",
    "user_name": "管理者",
    "to_user_name": "租客",
    "agent_name": "經辦人",
    "user_note": "管理者備註",
    "to_user_note": "租客備註",
    "user_phone": "管理者電話",
    "user_email": "管理者信箱",
    "to_user_phone": "租客電話",
    "to_user_email": "租客信箱",
    "ready_at": "發送時間",
    "apply_at": "申請時間",
    "assign_at": "派工時間",
    "complete_at": "完成時間",
    "finish_at": "結單時間",
    "lessee_name": "姓名",
    "lessee_email": "Email",
    "lessee_registered_phone": "電話",
    "lessee_primary_contact": "主要聯絡方式",
    "is_lessee_user_registered": "已註冊",
    "plan_name": "方案名稱",
    "plan_type": "方案類型",
    "eligible": "可點交",
    "contract_status": "合約狀態",
    "first_bill_status": "首期帳單",
    "deposit_status": "押金狀態",
    "checkin_blockers": "未通過項目",
    "required_amount": "應繳金額",
    "paid_amount": "已繳金額",
    "is_fulfilled": "已繳足",
    "is_signed": "已簽署",
    "is_paid": "已繳費",
    "label": "狀態",
    "city": "城市",
    "district": "區域",
    "address": "地址",
    "deposit_amount": "押金",
    "allow_early_termination": "可提前終止",
    "early_termination_days": "提前終止天數",
    "enable_late_fee": "滯納金",
    "calc_late_fee_buffer_days": "滯納金寬限天數",
    "late_fee_percent": "滯納金比例(%)",
    "early_termination_penalty_type": "違約金類型",
    "early_termination_penalty": "違約金倍數",
    "early_termination_penalty_amount": "違約金金額",
    "payment_completed_at": "付款完成時間",
    "no": "交易編號",
    "transaction_id": "金流交易號",
}

# 跳過不顯示的欄位
SKIP_KEYS = {
    "success", "pagination", "mapping", "updated_at",
    "estate_id", "contract_id", "bill_id", "currency",
    "is_auto_generate_invoice", "payment_id",
    "role_id", "user_id", "to_user_id", "agent_user_id",
    "role_id_comment", "team_id", "team_id_comment", "team_name_comment",
    "category_id", "item_id", "creditor_role_id",
    "orig_currency", "final_currency", "orig_price",
    "discount_cash", "discount_price", "payment_times",
    "upload_status", "random_num", "print_flag",
    "buyer_ubn", "buyer_address", "carrier_type", "carrier_number",
    "love_code", "bar_code", "item_data",
    "online_payment_method", "online_payment_action",
    "date_expire_note", "cycle", "days", "rate", "sub_title",
    "broken_photos", "archive_at",
    "lessee_role_id", "lessor_role_id", "lessee_user_id",
    "lessee_registered_phone_country", "lessee_nationality", "lessee_birthday",
    "data", "items", "ymd", "payment_completed_ymd",
    "user_phone", "user_email", "to_user_phone", "to_user_email",
    "manufacturer_phone",
    "final_total", "is_auto_pay", "is_paid_on_time",
    "orig_price", "discount_cash", "discount_price",
    "no", "transaction_id", "category",
    "random_num", "upload_status", "print_flag",
    "buyer_name", "buyer_email", "buyer_ubn", "buyer_address",
    "carrier_type", "carrier_number", "love_code",
    "bar_code", "url", "item_data",
    "tax_rate", "tax_amt", "amt",
    "added_at", "allowanced_at",
}

# 金額類欄位
MONEY_KEYS = {
    "total", "amount", "rent", "price", "final_price",
    "deposit_amount", "required_amount", "paid_amount",
    "total_amt", "amt", "tax_amt",
    "early_termination_penalty_amount", "final_total",
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


def format_jgb_response(api_result: dict, endpoint: str = "", user_question: str = "", form_data: dict = None, face: str | None = None) -> str:
    """
    格式化 JGB API 回應（進入點）

    endpoint: API endpoint 名稱（如 jgb_contracts），用於決定走哪個判斷引擎
    user_question: 用戶原始問題，用於判斷要檢查什麼操作
    form_data: 表單收集的資料（含用戶輸入的關鍵字）
    face: 當輪對話面向（僅透傳給領域模組選 fact 集，此層不解讀）
    """
    mapping = api_result.get("mapping", {})
    data = api_result.get("data", [])

    # 修繕建單 endpoint → 專屬格式化
    if endpoint == "jgb_create_repair":
        return _format_create_repair(api_result)

    # 合約相關 endpoint → 走合約判斷引擎（含 face 分流至 contracts/accounts builder）
    if endpoint in ("jgb_contracts", "jgb_contract_checkin"):
        return _format_contracts(data, user_question, form_data=form_data, face=face)

    # 電表 endpoint（iot 電表排障面向）：face 命中 → iot builder；未命中/None → 原路（零回歸）。
    if endpoint == "jgb_meters":
        from services.jgb.iot import face_meter_response
        faced = face_meter_response(data, user_question, face)
        if faced is not None:
            return faced

    # 團隊成員 endpoint（account 團隊權限面向）：face 命中 → accounts builder；
    # 主列為 T1 成員（含 permissions/bill_visibility secondary attach），零回歸（無此 face 不進此檔）。
    if endpoint == "jgb_team_members":
        from services.jgb.accounts import ACCOUNT_FACE_BUILDERS
        builder = ACCOUNT_FACE_BUILDERS.get(face) if face else None
        if builder:
            rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
            if rows:
                return builder(rows[0], user_question)

    # 租客摘要 → 專屬格式化
    if endpoint == "jgb_tenant_summary":
        return _format_tenant_summary(data if isinstance(data, dict) else {})

    # 帳務面向分流（billing-conversational-facets）：face 命中 BILL_FACE_BUILDERS 才接手，
    # 否則往下走原路（jgb_bills 通用格式化、其餘各自 diagnose 引擎）——零回歸。
    if face and endpoint in ("jgb_bills", "jgb_bill_detail",
                             "jgb_payment_logs", "jgb_invoice_logs"):
        from services.jgb.bills import face_bill_response
        faced = face_bill_response(endpoint, data, user_question, face)
        if faced is not None:
            return faced

    # v1.1 診斷用 endpoint → 各自的診斷引擎
    if endpoint == "jgb_bill_detail":
        from services.jgb.bills import diagnose_bill
        return diagnose_bill(data if isinstance(data, dict) else {}, user_question)

    if endpoint == "jgb_payment_logs":
        from services.jgb.payments import diagnose_payment_logs
        return diagnose_payment_logs(data if isinstance(data, list) else [], user_question)

    if endpoint == "jgb_invoice_logs":
        from services.jgb.invoices import diagnose_invoice_logs
        return diagnose_invoice_logs(data if isinstance(data, list) else [], user_question)

    if endpoint == "jgb_subscription":
        from services.jgb.subscription import diagnose_subscription
        return diagnose_subscription(data if isinstance(data, dict) else {}, user_question)

    if endpoint == "jgb_iot_manufacturers":
        from services.jgb.iot import diagnose_iot
        return diagnose_iot(data if isinstance(data, list) else [], user_question)

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


def _format_create_repair(api_result: dict) -> str:
    """格式化修繕建單回應"""
    if not api_result.get("success", False):
        error = api_result.get("error", {})
        if isinstance(error, dict):
            msg = error.get("message", "建單失敗，請稍後再試。")
        else:
            msg = str(error) if error else "建單失敗，請稍後再試。"
        return f"❌ **修繕單建立失敗**\n\n{msg}"

    data = api_result.get("data", {})
    repair_id = data.get("id", "—")
    broken_reason = data.get("broken_reason", "")
    broken_note = data.get("broken_note", "")
    emergency = "緊急" if data.get("emergency_status") == 1 else "非緊急"

    lines = [
        f"✅ **修繕單 #{repair_id} 已建立**",
        "",
        f"　損壞原因：{broken_reason}",
    ]
    if broken_note:
        lines.append(f"　補充說明：{broken_note}")
    lines.append(f"　急迫性：{emergency}")
    lines.append("")
    lines.append("我們會儘快安排維修，如有進度會通知您。")

    return "\n".join(lines)


def _format_contracts(data: Any, user_question: str, form_data: dict = None, face: str | None = None) -> str:
    """合約資料走判斷引擎"""
    from services.jgb.contracts import format_contract_response

    keyword = ""
    if form_data:
        keyword = form_data.get("contract_keyword", "") or form_data.get("keyword", "")

    return format_contract_response(data, user_question=user_question, keyword=keyword, face=face)


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
    if key in mapping:
        m = mapping[key]
        # mapping 可能是 dict {"1": "..."} 或 list ["...", "..."]（用 index 當 key）
        if isinstance(m, dict) and str_val in m:
            return m[str_val]
        if isinstance(m, list) and isinstance(value, int) and 0 <= value < len(m):
            return m[value]

    # bit_status 特殊處理：欄位名是 bit_status，mapping key 可能是 bit_status 或 status
    if key == "bit_status":
        for mk in ("bit_status", "status"):
            if mk in mapping and str_val in mapping[mk]:
                return mapping[mk][str_val]

    # emergency_status 對照
    if key == "emergency_status" and "emergency_status" in mapping and str_val in mapping["emergency_status"]:
        return mapping["emergency_status"][str_val]

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


def _format_tenant_summary(data: dict) -> str:
    """格式化租客摘要"""
    if not data:
        return "查無此租客資料，請確認租客 ID 或姓名是否正確。"

    tenant = data.get("tenant_info", {})
    contract = data.get("contract_summary", {})
    bill = data.get("bill_summary", {})
    repair = data.get("repair_summary", {})

    lines = []

    # 租客資訊
    name = tenant.get("lessee_name", "未知")
    email = tenant.get("lessee_email", "")
    phone = tenant.get("lessee_registered_phone", "")
    registered = "已註冊" if tenant.get("is_lessee_user_registered") else "未註冊"
    active = "啟用" if tenant.get("active") else "停用"

    lines.append(f"**租客：{name}**")
    if email:
        lines.append(f"　Email：{email}")
    if phone:
        lines.append(f"　電話：{phone}")
    lines.append(f"　帳號狀態：{registered}（{active}）")

    # 合約摘要
    total = contract.get("registered_contract_count", 0) + contract.get("exempt_register_contract_count", 0)
    signed = contract.get("registered_contract_signed_count", 0) + contract.get("exempt_register_contract_signed_count", 0)
    history = contract.get("registered_contract_history_count", 0) + contract.get("exempt_register_contract_history_count", 0)
    inviting = contract.get("registered_contract_inviting_count", 0)

    lines.append(f"\n**合約：**共 {total} 份")
    parts = []
    if signed:
        parts.append(f"執行中 {signed}")
    if history:
        parts.append(f"歷史 {history}")
    if inviting:
        parts.append(f"簽約中 {inviting}")
    if parts:
        lines.append(f"　{' / '.join(parts)}")

    # 帳單摘要
    bill_total = bill.get("income_bill_count", 0)
    ready = bill.get("income_bill_ready_count", 0)
    overdue = bill.get("income_bill_ready_overdue_count", 0)
    complete = bill.get("income_bill_complete_count", 0)
    on_time = bill.get("income_bill_complete_on_time_count", 0)
    late = bill.get("income_bill_complete_late_count", 0)
    ratio = bill.get("income_bill_paid_on_time_ratio", 0)

    lines.append(f"\n**帳單：**共 {bill_total} 筆")
    if ready:
        overdue_note = f"，其中逾期 {overdue} 筆" if overdue else ""
        lines.append(f"　待繳 {ready} 筆{overdue_note}")
    if complete:
        lines.append(f"　已繳 {complete} 筆（準時 {on_time} / 逾期繳 {late}，準時率 {ratio}%）")

    # 修繕摘要
    repair_total = repair.get("repair_count", 0)
    apply_count = repair.get("repair_apply_count", 0)
    assign_count = repair.get("repair_assign_count", 0)
    complete_count = repair.get("repair_complete_count", 0)
    finish_count = repair.get("repair_finish_count", 0)

    lines.append(f"\n**修繕：**共 {repair_total} 筆")
    r_parts = []
    if apply_count:
        r_parts.append(f"申請中 {apply_count}")
    if assign_count:
        r_parts.append(f"安排中 {assign_count}")
    if complete_count:
        r_parts.append(f"已完成 {complete_count}")
    if finish_count:
        r_parts.append(f"已結單 {finish_count}")
    if r_parts:
        lines.append(f"　{' / '.join(r_parts)}")

    return "\n".join(lines)
