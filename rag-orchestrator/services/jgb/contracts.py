"""
JGB 合約狀態判斷引擎

根據 JGB 系統的合約業務邏輯，解讀 API 回傳的 bit_status / status，
判斷用戶詢問的操作（發送邀請/點交/點退/提前解約/續約）缺少什麼條件。

bit_status 是 bitmask（累加），每個階段會加上對應的 flag。
status 是當前階段（會被覆寫為最新階段的值）。

參考來源：JGB ContractController / ContractService / Contract Model
"""

from datetime import datetime, timedelta
from typing import Any


# ── 合約 bit_status 常數（bitmask）──────────────────────────
class ContractBit:
    READY = 1                      # 已建立
    INVITING = 2                   # 已發送簽約邀請
    INVITING_NEXT = 4              # 租客已簽名
    SIGNED = 8                     # 雙方簽名完成
    MOVE_IN = 16                   # 已發送點交
    MOVE_IN_DONE = 32              # 租客同意點交
    MOVE_OUT = 64                  # 已發送點退
    MOVE_OUT_DONE = 128            # 租客同意點退
    EARLY_TERMINATION = 256        # 提前解約中
    EARLY_TERMINATION_DONE = 512   # 提前解約確認
    HISTORY = 1024                 # 歷史合約
    HISTORY_DONE = 2048            # 歷史完成


# status 常數（當前階段，非 bitmask）
class ContractStatus:
    READY = 1
    INVITING = 2
    SIGNED = 3
    MOVE_IN = 4
    MOVE_IN_DONE = 5
    MOVE_OUT = 6
    MOVE_OUT_DONE = 7
    EARLY_TERMINATION = 8
    HISTORY = 9
    HISTORY_DONE = 10


# bit_status flag → 中文標籤
BIT_LABELS = {
    ContractBit.READY: "已建立",
    ContractBit.INVITING: "已發送簽約邀請",
    ContractBit.INVITING_NEXT: "租客已簽名",
    ContractBit.SIGNED: "雙方簽名完成",
    ContractBit.MOVE_IN: "已發送點交",
    ContractBit.MOVE_IN_DONE: "租客同意點交",
    ContractBit.MOVE_OUT: "已發送點退",
    ContractBit.MOVE_OUT_DONE: "租客同意點退",
    ContractBit.EARLY_TERMINATION: "提前解約中",
    ContractBit.EARLY_TERMINATION_DONE: "提前解約已確認",
    ContractBit.HISTORY: "歷史合約",
    ContractBit.HISTORY_DONE: "歷史完成",
}

# 社會住宅
SOCIAL_HOUSING = 2  # property_purpose_key


def has_bit(bit_status: int, flag: int) -> bool:
    """檢查 bit_status 是否包含指定 flag"""
    return (bit_status & flag) > 0


def decode_bit_status(bit_status: int) -> list[str]:
    """將 bit_status 拆解為中文標籤列表"""
    return [label for flag, label in BIT_LABELS.items() if has_bit(bit_status, flag)]


def is_renewing(contract: dict) -> bool:
    """判斷合約是否正在續約中（對應 JGB Contract::isRenewing()）"""
    father_id = contract.get("father_id")
    contract_id = contract.get("id")
    if not father_id or father_id == contract_id:
        return False
    # 完整判斷需要 renew_thinkcloud_pdf / old_contract_finish_sign_at / contract_finish_sign_at
    # 簡化：有 father_id 且 != id 就視為續約中
    return True


def get_current_stage(contract: dict) -> str:
    """根據 bit_status + status + is_history 判斷合約當前階段（人可讀）"""
    bit_status = contract.get("bit_status", 0)
    status = contract.get("status", 0)
    is_history = contract.get("is_history", 0)
    is_history_done = contract.get("is_history_done", 0)

    # 歷史狀態優先用 is_history / is_history_done 判斷
    if is_history_done:
        return "歷史完成（已歸檔）"
    if is_history:
        return "歷史合約（已到期）"

    if has_bit(bit_status, ContractBit.EARLY_TERMINATION_DONE):
        return "提前解約已確認"
    if has_bit(bit_status, ContractBit.EARLY_TERMINATION):
        return "提前解約中"
    if has_bit(bit_status, ContractBit.MOVE_OUT_DONE):
        return "點退完成"
    if has_bit(bit_status, ContractBit.MOVE_OUT):
        return "點退中（等待租客同意）"
    if has_bit(bit_status, ContractBit.MOVE_IN_DONE):
        return "已點交（執行中）"
    if has_bit(bit_status, ContractBit.MOVE_IN):
        return "點交中（等待租客同意）"
    if has_bit(bit_status, ContractBit.SIGNED):
        return "已簽約（待點交）"
    if has_bit(bit_status, ContractBit.INVITING_NEXT):
        return "租客已簽名（等待房東簽名）"
    if has_bit(bit_status, ContractBit.INVITING):
        return "已發送簽約邀請（等待租客簽名）"
    if has_bit(bit_status, ContractBit.READY):
        return "已建立（待發送）"
    return "未知狀態"


# ── 操作條件判斷 ────────────────────────────────────────────

def check_can_invite(contract: dict) -> dict:
    """
    判斷合約是否可以發送簽約邀請
    對應 JGB ContractController::invite() L14151-14308
    """
    bit_status = contract.get("bit_status", 0)
    status = contract.get("status", 0)
    blockers = []

    # 條件 1：合約啟用中
    if not contract.get("active", 1):
        blockers.append("合約已停用")

    # 條件 2：status < INVITING（尚未進入邀請階段）
    if isinstance(status, int) and status >= ContractStatus.INVITING:
        blockers.append("合約已發送過簽約邀請，無法重複發送")

    # 條件 3：isWriteDone（必填欄位已填完）— API 無法完整判斷，提示用戶
    # 這部分涉及多個欄位組合，由 JGB 系統驗證

    # 條件 4：租客聯絡方式至少有一種
    has_phone = bool(contract.get("to_user_phone"))
    has_email = bool(contract.get("to_user_email"))
    if not has_phone and not has_email:
        blockers.append("尚未設定租客聯絡方式（需至少填寫電話或 Email）")

    return {
        "can_do": len(blockers) == 0,
        "operation": "發送簽約邀請",
        "blockers": blockers,
    }


def check_can_move_in(contract: dict) -> dict:
    """
    判斷合約是否可以點交（發送點交）
    對應 JGB Contract::canMoveIn() L24045-24074
    """
    bit_status = contract.get("bit_status", 0)
    status = contract.get("status", 0)
    blockers = []

    # 條件 1：租客已綁定 JGB
    if not contract.get("to_user_connect"):
        blockers.append("租客尚未綁定 JGB 帳號")

    # 條件 2：雙方已簽名（bit_status 含 SIGNED）
    if not has_bit(bit_status, ContractBit.SIGNED):
        blockers.append("合約尚未完成雙方簽名")

    # 條件 3：不可已在點交/點退/歷史階段
    if has_bit(bit_status, ContractBit.MOVE_IN):
        blockers.append("合約已發送點交，目前等待租客確認中")
    if has_bit(bit_status, ContractBit.MOVE_IN_DONE):
        blockers.append("合約已完成點交")
    if has_bit(bit_status, ContractBit.MOVE_OUT):
        blockers.append("合約已在點退流程中")
    if has_bit(bit_status, ContractBit.MOVE_OUT_DONE):
        blockers.append("合約已完成點退")
    if has_bit(bit_status, ContractBit.HISTORY):
        blockers.append("合約已轉為歷史合約")

    # 條件 4：不可為提前解約狀態
    if isinstance(status, int) and status == ContractStatus.EARLY_TERMINATION:
        blockers.append("合約正在提前解約流程中")
    elif has_bit(bit_status, ContractBit.EARLY_TERMINATION):
        blockers.append("合約正在提前解約流程中")

    return {
        "can_do": len(blockers) == 0,
        "operation": "點交",
        "blockers": blockers,
    }


def check_can_move_out(contract: dict) -> dict:
    """
    判斷合約是否可以點退（發送點退）
    對應 JGB Contract::canMoveOut() L24081-24120
    """
    bit_status = contract.get("bit_status", 0)
    status = contract.get("status", 0)
    is_history = contract.get("is_history", 0)
    is_history_done = contract.get("is_history_done", 0)
    blockers = []

    # 條件 1：租客已綁定
    if not contract.get("to_user_connect"):
        blockers.append("租客尚未綁定 JGB 帳號")

    # 條件 2：status 必須在 SIGNED / MOVE_IN_DONE / HISTORY / HISTORY_DONE
    valid_statuses = {
        ContractStatus.SIGNED, ContractStatus.MOVE_IN_DONE,
        ContractStatus.HISTORY, ContractStatus.HISTORY_DONE,
    }
    if isinstance(status, int) and status not in valid_statuses:
        stage = get_current_stage(contract)
        blockers.append(f"合約目前狀態為「{stage}」，不在可點退的階段")

    # 條件 3：不可已完成點退
    if has_bit(bit_status, ContractBit.MOVE_OUT_DONE):
        blockers.append("合約已完成點退")

    # 條件 4：已到合約開始日
    date_start = contract.get("date_start")
    if date_start:
        start = _parse_date_int(date_start)
        if start and datetime.now() < start:
            blockers.append(f"合約尚未到開始日（{_format_date(start)}），目前無法點退")

    # 條件 5：合約到期前 30 天才可點退
    date_end = contract.get("date_end")
    if date_end:
        end = _parse_date_int(date_end)
        if end:
            earliest = end - timedelta(days=30)
            if datetime.now() < earliest:
                blockers.append(
                    f"合約到期日為 {_format_date(end)}，"
                    f"需到期前 30 天（{_format_date(earliest)}）起才可發送點退"
                )

    return {
        "can_do": len(blockers) == 0,
        "operation": "點退",
        "blockers": blockers,
    }


def check_can_early_termination(contract: dict) -> dict:
    """
    判斷合約是否可以提前解約
    對應 JGB Contract::canEarlyTermination() L24127-24161
    """
    bit_status = contract.get("bit_status", 0)
    status = contract.get("status", 0)
    blockers = []

    # 條件 1：status 必須在 SIGNED 或 MOVE_IN_DONE
    valid_statuses = {ContractStatus.SIGNED, ContractStatus.MOVE_IN_DONE}
    if isinstance(status, int) and status not in valid_statuses:
        stage = get_current_stage(contract)
        blockers.append(f"合約目前狀態為「{stage}」，僅在已簽約或已點交狀態才可申請提前解約")

    # 條件 2：不可已在提前解約流程
    if has_bit(bit_status, ContractBit.EARLY_TERMINATION) and not has_bit(bit_status, ContractBit.EARLY_TERMINATION_DONE):
        blockers.append("合約已在提前解約流程中")
    if has_bit(bit_status, ContractBit.EARLY_TERMINATION_DONE):
        blockers.append("合約已完成提前解約")

    # 條件 3：是否允許提前終止
    if not contract.get("allow_early_termination", False):
        blockers.append("此合約不允許提前終止（合約條款設定）")

    # 條件 4：不可在續約簽約進行中
    if is_renewing(contract):
        blockers.append("合約正在續約簽約流程中，無法同時提前解約")

    return {
        "can_do": len(blockers) == 0,
        "operation": "提前解約",
        "blockers": blockers,
    }


def check_can_renew(contract: dict) -> dict:
    """
    判斷合約是否可以續約
    對應 JGB Contract::canRenewContract() L24328-24348
    """
    bit_status = contract.get("bit_status", 0)
    blockers = []

    # 條件 1：租客已綁定
    if not contract.get("to_user_connect"):
        blockers.append("租客尚未綁定 JGB 帳號")

    # 條件 2：已簽約（bit_status 含 SIGNED）
    if not has_bit(bit_status, ContractBit.SIGNED):
        blockers.append("合約尚未完成簽約")

    # 條件 3：不可在點退流程
    if has_bit(bit_status, ContractBit.MOVE_OUT):
        blockers.append("合約已在點退流程中")
    if has_bit(bit_status, ContractBit.MOVE_OUT_DONE):
        blockers.append("合約已完成點退")

    # 條件 4：不可在點交中但未完成
    if has_bit(bit_status, ContractBit.MOVE_IN) and not has_bit(bit_status, ContractBit.MOVE_IN_DONE):
        blockers.append("合約正在點交中（等待租客確認），完成後才可續約")

    # 條件 5：不可在提前解約中但未完成
    if has_bit(bit_status, ContractBit.EARLY_TERMINATION) and not has_bit(bit_status, ContractBit.EARLY_TERMINATION_DONE):
        blockers.append("合約正在提前解約流程中")

    # 條件 6：不可已完成提前解約
    if has_bit(bit_status, ContractBit.EARLY_TERMINATION_DONE):
        blockers.append("合約已提前解約，無法續約")

    # 條件 7：合約尚未到期
    date_end = contract.get("date_end")
    if date_end:
        end = _parse_date_int(date_end)
        if end and datetime.now() > end:
            blockers.append(f"合約已於 {_format_date(end)} 到期")

    return {
        "can_do": len(blockers) == 0,
        "operation": "續約",
        "blockers": blockers,
    }


# ── 主要入口：回應格式化 ───────────────────────────────────

def format_contract_response(contracts: list | dict, user_question: str = "", keyword: str = "") -> str:
    """
    根據合約資料 + 用戶問題，產出客戶理解的自然語言回應。

    contracts: JGB API 回傳的 data（list 或 dict）
    user_question: 用戶的原始問題
    keyword: 用戶在表單中輸入的合約編號或物件名稱（用於過濾）
    """
    # 統一成 list
    if isinstance(contracts, dict):
        contracts = [contracts]

    if not contracts:
        return "查無合約資料，請確認合約編號或物件名稱是否正確。"

    # 用 keyword 過濾匹配的合約
    matched = _filter_by_keyword(contracts, keyword) if keyword else contracts

    if not matched:
        return f"查無符合「{keyword}」的合約，請確認合約編號或物件名稱是否正確。"

    # 只回應第一筆匹配的合約
    contract = matched[0]
    return _build_response(contract, user_question)


def _filter_by_keyword(contracts: list, keyword: str) -> list:
    """根據 keyword 過濾合約（比對 ID 或 title）"""
    keyword = keyword.strip()

    # 精確匹配 ID
    try:
        target_id = int(keyword)
        exact = [c for c in contracts if c.get("id") == target_id]
        if exact:
            return exact
    except ValueError:
        pass

    # 模糊匹配 title
    return [c for c in contracts if keyword in (c.get("title") or "")]


def _build_response(contract: dict, user_question: str) -> str:
    """根據合約狀態 + 用戶問題，產出自然語言回應"""
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    stage = get_current_stage(contract)
    date_start = _format_date_int(contract.get("date_start", ""))
    date_end = _format_date_int(contract.get("date_end", ""))
    rent = contract.get("rent")

    # 合約停用
    if not contract.get("active", 1):
        return f"合約「{title}」目前已停用，無法進行任何操作。如有疑問請聯繫管理師。"

    # 判斷用戶問的是什麼操作
    question = user_question.lower() if user_question else ""
    check = None
    operation = ""

    if any(k in question for k in ["邀請", "發送", "簽約邀請", "invite"]):
        check = check_can_invite(contract)
        operation = "invite"
    elif any(k in question for k in ["點交", "move_in", "入住"]):
        check = check_can_move_in(contract)
        operation = "move_in"
    elif any(k in question for k in ["點退", "move_out", "退租", "搬離"]):
        check = check_can_move_out(contract)
        operation = "move_out"
    elif any(k in question for k in ["提前", "解約", "終止", "early"]):
        check = check_can_early_termination(contract)
        operation = "early_termination"
    elif any(k in question for k in ["續約", "renew", "延長"]):
        check = check_can_renew(contract)
        operation = "renew"

    # 有特定操作 → 回答能不能做 + 原因
    if check:
        return _format_operation_response(contract, check, operation)

    # 沒有特定操作 → 回答合約現況
    return _format_status_response(contract)


def _format_operation_response(contract: dict, check: dict, operation: str) -> str:
    """格式化特定操作的回應（能不能做 + 原因 + 建議）"""
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    stage = get_current_stage(contract)
    date_start = _format_date_int(contract.get("date_start", ""))
    date_end = _format_date_int(contract.get("date_end", ""))

    header = f"您好，合約「{title}」目前為{stage}（合約期間 {date_start} ~ {date_end}）。\n"

    if check["can_do"]:
        return header + f"\n可以進行{check['operation']}，請在系統中操作。"

    # 不能做 → 說明原因
    reasons = "\n".join(f"• {b}" for b in check["blockers"])
    response = header + f"\n目前無法{check['operation']}，原因如下：\n{reasons}"

    return response


def _format_status_response(contract: dict) -> str:
    """格式化合約現況回應（沒有問特定操作時）"""
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    stage = get_current_stage(contract)
    date_start = _format_date_int(contract.get("date_start", ""))
    date_end = _format_date_int(contract.get("date_end", ""))
    rent = contract.get("rent")

    lines = [f"您好，以下是合約「{title}」的資訊：\n"]
    lines.append(f"• 目前狀態：{stage}")
    lines.append(f"• 合約期間：{date_start} ~ {date_end}")
    if rent:
        lines.append(f"• 月租金：NT$ {rent:,.0f}")

    # 簡要列出可用操作
    available = []
    for check_fn, label in [
        (check_can_move_in, "點交"),
        (check_can_move_out, "點退"),
        (check_can_early_termination, "提前解約"),
        (check_can_renew, "續約"),
    ]:
        result = check_fn(contract)
        if result["can_do"]:
            available.append(label)

    if available:
        lines.append(f"\n目前可進行的操作：{'、'.join(available)}")
    else:
        lines.append("\n目前沒有可進行的操作。")

    return "\n".join(lines)




# ── 工具函式 ────────────────────────────────────────────────

def _parse_date_int(date_val) -> datetime | None:
    """將 JGB 的日期整數（YYYYMMDD）轉為 datetime"""
    if isinstance(date_val, int):
        s = str(date_val)
        if len(s) == 8:
            return datetime(int(s[:4]), int(s[4:6]), int(s[6:]))
    if isinstance(date_val, str) and len(date_val) >= 10:
        try:
            return datetime.strptime(date_val[:10], "%Y-%m-%d")
        except ValueError:
            pass
    return None


def _format_date(dt: datetime) -> str:
    return dt.strftime("%Y/%m/%d")


def _format_date_int(date_val) -> str:
    dt = _parse_date_int(date_val)
    if dt:
        return _format_date(dt)
    return str(date_val)
