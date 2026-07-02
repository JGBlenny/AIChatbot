"""
JGB 合約狀態判斷引擎

根據 JGB 系統的合約業務邏輯，解讀 API 回傳的 bit_status / status，
判斷用戶詢問的操作（發送邀請/點交/點退/提前解約/續約）缺少什麼條件。

bit_status 是 bitmask（累加），每個階段會加上對應的 flag。
status 是當前階段（會被覆寫為最新階段的值）。

參考來源：JGB ContractController / ContractService / Contract Model
"""

from datetime import datetime, timedelta
from typing import Any, Callable, TypedDict


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


# status 常數（jgb2 的 status 值與 bit_status 常數相同）
class ContractStatus:
    READY = 1
    INVITING = 2
    INVITING_NEXT = 4
    SIGNED = 8
    MOVE_IN = 16
    MOVE_IN_DONE = 32
    MOVE_OUT = 64
    MOVE_OUT_DONE = 128
    EARLY_TERMINATION = 256
    EARLY_TERMINATION_DONE = 512
    HISTORY = 1024
    HISTORY_DONE = 2048


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

    # 條件 1：必須已簽約或已點交（用 bit_status 判斷，比 status 欄位更可靠）
    is_signed = has_bit(bit_status, ContractBit.SIGNED)
    is_moved_in_done = has_bit(bit_status, ContractBit.MOVE_IN_DONE)
    if not is_signed and not is_moved_in_done:
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


# ── 面向 fact-builders（contract-conversational-facets 元件 2）──────────────
#
# 每個 builder 為純函式：(contract_row, user_question) -> 決定性 facts 文字。
# 分流結論全由 status/bit_status/欄位機械算出，LLM 只把 facts 講成人話（R7.1）；
# G1–G4 擴充欄位採存在性驅動：欄位缺 → 略過該分支不虛構（R10.3）。

def build_change_exit_facts(contract: dict, user_question: str = "") -> str:
    """合約異動三出口（R2.2, R2.6；research.md §二 ground truth）。

    status==1 → 可直接編輯；status∈{2,4} → 取消退回待發送再改（主取消保留租客資料）；
    status>=8 → 不可直改，複製重建或資料異動申請書＋藍字/DB 區分；歷史 → 申請書共用出口。
    """
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    status = contract.get("status", 0)
    lines = [f"合約「{title}」目前狀態：{get_current_stage(contract)}。"]

    # 歷史合約：使用者端不可編輯，資料調整走申請書（轉歷史共用出口）
    if contract.get("is_history") or contract.get("is_history_done"):
        lines.append("此合約已轉為歷史合約，使用者端無法編輯。")
        lines.append("如需調整歷史合約資料，請填寫資料異動申請書，由客服於後台處理。")
        return "\n".join(lines)

    if status == ContractStatus.READY:
        lines.append("出口判定：合約尚未發送簽約邀請，可直接編輯。")
        lines.append("操作路徑：進入該合約的編輯頁修改後儲存即可；此狀態下也可直接刪除合約。")
    elif status in (ContractStatus.INVITING, ContractStatus.INVITING_NEXT):
        lines.append("出口判定：合約已送出簽約邀請（簽署流程中），不可直接編輯。")
        lines.append("處理方式：先取消簽約、退回「待發送」狀態，修改後重新發送邀請。")
        lines.append("管理者主動取消會保留已填的租客資料；"
                     "但若是租客按「不同意」或邀請逾期自動退回，租客資料會被清空、需重新填寫。")
    elif isinstance(status, int) and status >= ContractStatus.SIGNED:
        lines.append("出口判定：合約已完成雙方簽署，不可直接修改。")
        lines.append("兩條出口：一、複製合約重建新約重新簽署（可分區塊複製既有內容）；"
                     "二、填寫資料異動申請書，由客服於後台調整資料。")
        lines.append("藍字區分：合約上的藍字參數（簽署後印在 PDF 上的內容，如租金、電價、租期）"
                     "簽後不可改；資料異動申請書調整的是系統資料庫（DB）中的資料。"
                     "若僅調整系統資料而未重簽，PDF 藍字與實際收款內容將不一致，此風險需由申請人自行承擔。")
    else:
        lines.append("出口判定：無法辨識此合約的狀態，請聯繫客服確認。")

    return "\n".join(lines)


def build_closeout_facts(contract: dict, user_question: str = "") -> str:
    """退租收尾步驟鏈（R3.1–3.5；research.md §二）。

    步驟序：提前解約(256/512)／點退(64/128) → 帳單封存（G3 前通用指引＝常態降級）
    → 轉歷史（過終止/到期日後每日排程自動轉；逾期未轉導客服）。
    未發起 → 重用 check_can_move_out（點交點退互不相依）＋提前解約發起路徑。
    """
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    bit_status = contract.get("bit_status", 0)
    lines = [f"合約「{title}」目前狀態：{get_current_stage(contract)}。"]

    # 已轉歷史 → 收尾全部完成
    if contract.get("is_history") or contract.get("is_history_done"):
        lines.append("步驟判定：合約已轉為歷史合約，退租收尾流程已全部完成，無需其他操作。")
        return "\n".join(lines)

    done_moveout = has_bit(bit_status, ContractBit.MOVE_OUT_DONE)
    done_early = has_bit(bit_status, ContractBit.EARLY_TERMINATION_DONE)
    if done_moveout or done_early:
        what = "點退" if done_moveout else "提前解約"
        lines.append(f"步驟判定：{what}已完成。下一步：封存這份合約剩餘未結的帳單。")
        lines.append("帳單封存指引：至帳單總表以合約編號搜尋，將剩餘帳單批次封存。")
        lines.append("轉歷史時點：過終止/到期日後，系統每日排程會自動轉為歷史合約，無需手動操作。")
        end = _parse_date_int(contract.get("date_end"))
        if end and datetime.now() > end:
            lines.append(f"注意：此合約已過到期/終止日（{_format_date(end)}）但尚未轉為歷史合約；"
                         "若隔日排程執行後仍未轉，請聯繫客服盤查。")
        return "\n".join(lines)

    if has_bit(bit_status, ContractBit.EARLY_TERMINATION):
        lines.append("步驟判定：提前解約申請已送出，等待租客回簽同意（回簽效期預設 30 天）。")
        lines.append("下一步：待租客同意後提前解約完成，再進行帳單封存。")
        return "\n".join(lines)

    if has_bit(bit_status, ContractBit.MOVE_OUT):
        lines.append("步驟判定：點退已送出，等待租客同意。")
        lines.append("下一步：待租客同意後點退完成，再進行帳單封存。")
        return "\n".join(lines)

    # 收尾尚未發起：到期退租（點退）與提前解約兩條路都給
    mo = check_can_move_out(contract)
    if mo["can_do"]:
        pair_note = ("（點退不以點交為前提，可略過點交直接點退）"
                     if not has_bit(bit_status, ContractBit.MOVE_IN_DONE) else "")
        lines.append(f"到期退租：目前可直接發送點退{pair_note}。")
    else:
        lines.append("到期退租：目前尚不可點退——" + "；".join(mo["blockers"]) + "。")
    lines.append("提前解約：尚未發起。發起路徑：於合約操作中選「提前解約」、填寫希望終止日並送出，"
                 "租客回簽效期預設 30 天；提前解約造成的已產出帳單需封存處理。")
    return "\n".join(lines)


def _mask_email(email: str) -> str:
    """個資遮罩：g***@gmail.com 形式（登入信箱僅用於錯配事實句，不完整揭露）"""
    local, sep, domain = email.partition("@")
    if not sep or not local:
        return "***"
    return f"{local[0]}***@{domain}"


def _parse_datetime_any(val):
    """解析 datetime 字串（'YYYY-MM-DD HH:MM:SS'/ISO）或日期整數；解不了回 None"""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.strip())
        except ValueError:
            pass
    return _parse_date_int(val)


def build_sign_facts(contract: dict, user_question: str = "") -> str:
    """簽署排障（R6.1–6.4；research.md §一）。

    位元決定「還差誰簽」（bit 2 已發送、4 租客已簽、8 回簽完成）＋發送通道＋綁定狀態；
    G1（邀請效期）/G2（登入信箱）存在性驅動：欄位在才判、缺則略過不虛構（R7.4/R10.3）。
    """
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    bit_status = contract.get("bit_status", 0)
    lines = [f"合約「{title}」目前狀態：{get_current_stage(contract)}。"]

    signed = has_bit(bit_status, ContractBit.SIGNED)
    if signed:
        lines.append("簽署進度：雙方簽名皆已完成，簽署流程已結束。")
    elif has_bit(bit_status, ContractBit.INVITING_NEXT):
        lines.append("簽署進度：租客已簽名，還差管理者回簽。")
    elif has_bit(bit_status, ContractBit.INVITING):
        lines.append("簽署進度：簽約邀請已發送，還差租客簽名。")
    else:
        lines.append("簽署進度：尚未發送簽約邀請。")

    # 發送通道（管理者自填欄位；發送後未選通道會被清空，留下的就是邀請通道）
    email = (contract.get("to_user_email") or "").strip()
    phone = (contract.get("to_user_phone") or "").strip()
    if email or phone:
        parts = ([f"Email {email}"] if email else []) + ([f"電話 {phone}"] if phone else [])
        lines.append(f"邀請發送通道：{'、'.join(parts)}。")
    else:
        lines.append("合約上未設定租客聯絡方式（Email 與電話皆空），邀請無法送達。")

    lines.append("租客已綁定 JGB 會員帳號。" if contract.get("to_user_connect")
                 else "租客尚未綁定 JGB 會員帳號。")

    # G1：邀請效期（欄位存在才判；雙簽完成後無效期議題）
    expire_raw = contract.get("contract_inviting_expire_at")
    if expire_raw and not signed:
        expire = _parse_datetime_any(expire_raw)
        if expire:
            if datetime.now() > expire:
                lines.append(f"邀請效期已於 {expire:%Y/%m/%d %H:%M} 過期："
                             "系統會自動將合約退回「待發送」並清空租客資料，"
                             "需重新填寫租客資料後重新發送邀請。")
            else:
                lines.append(f"邀請效期至 {expire:%Y/%m/%d %H:%M}，目前仍在有效期間。")

    # G2：發送信箱 vs 租客登入信箱錯配（欄位存在才比；登入信箱遮罩輸出）
    login_raw = (contract.get("to_user_login_email") or "").strip()
    if login_raw and email:
        if login_raw.lower() != email.lower():
            lines.append(f"信箱比對：邀請發送至 {email}，但租客登入帳號信箱為 "
                         f"{_mask_email(login_raw)}，兩者不一致——租客登入後會看不到這份合約；"
                         "請改用租客登入信箱重新發送邀請。")
        else:
            lines.append("信箱比對：邀請發送信箱與租客登入信箱一致。")

    return "\n".join(lines)


def build_renew_facts(contract: dict, user_question: str = "") -> str:
    """續約（R4.1, R4.3, R4.5；research.md §三）。

    date_end 剩餘/逾期天數＋可否系統續約（包裝既有 check_can_renew）＋
    免註冊單方確認/已註冊重簽 72h（欄位存在才判）＋G4 is_newest 已被續約提示＋father_id 鏈。
    """
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    lines = [f"合約「{title}」目前狀態：{get_current_stage(contract)}。"]

    end = _parse_date_int(contract.get("date_end"))
    if end:
        days = (end.date() - datetime.now().date()).days
        if days >= 0:
            lines.append(f"合約到期日 {_format_date(end)}，剩餘 {days} 天。")
        else:
            lines.append(f"合約已於 {_format_date(end)} 到期（逾 {-days} 天）。")

    # G4：is_newest 存在且 =0 → 已有較新續約（缺欄位則略過，存在性驅動）
    is_newest = contract.get("is_newest")
    if is_newest is not None and int(is_newest) == 0:
        lines.append("此合約已有較新的續約合約：列表僅顯示最新一筆，"
                     "原合約以分頁呈現續約增補文件，開啟舊約會自動跳轉至最新續約。")

    # 可否系統續約（重用 check_can_renew：雙簽完成＋未過期＋非點退/解約流程等）
    renew_check = check_can_renew(contract)
    if renew_check["can_do"]:
        lines.append("可走系統續約（原約雙簽完成且未過期）。")
    else:
        lines.append("目前不可走系統續約——" + "；".join(renew_check["blockers"]) +
                     "。可改走重建新約重新簽訂。")

    # 重簽規則（is_tenant_registered 存在才判）
    registered = contract.get("is_tenant_registered")
    if registered is not None:
        if registered:
            lines.append("租客已註冊：續約需雙方重新簽署（邀請效期 72 小時）。")
        else:
            lines.append("租客為免註冊：續約由管理者單方確認即生效，不需租客重簽。")

    # father_id 鏈（isRenewContract：father_id 非空且 ≠id）
    father_id = contract.get("father_id")
    contract_id = contract.get("id")
    if father_id and father_id != contract_id:
        lines.append(f"本約為續約合約（同一續約鏈父約編號 {father_id}）。")

    return "\n".join(lines)


# ── 面向 fact-builder 註冊表（contract-conversational-facets 元件 2）────────
#
# face（當輪對話面向）命中 → 該面向的決定性 fact-builder 接手；未命中/None →
# 現行意圖關鍵字/狀態路由。面向字面只允許出現在本檔與資料列（引擎/handler 僅透傳）。
# 「狀態判斷」永不註冊 → 既有面向天然 fallback（零回歸）。

class CheckResult(TypedDict):
    ok: bool                  # 可否執行該操作
    reasons: list[str]        # 不可時的缺件（人可讀）
    facts: list[str]          # 決定性事實句（餵 LLM）


FaceBuilder = Callable[[dict, str], str]   # (contract_row, user_question) -> facts 文字

FACE_BUILDERS: dict[str, FaceBuilder] = {
    "合約異動": build_change_exit_facts,
    "退租收尾": build_closeout_facts,
    "簽署排障": build_sign_facts,
    "續約": build_renew_facts,
}


# ── 主要入口：回應格式化 ───────────────────────────────────

def format_contract_response(contracts, user_question: str = "", keyword: str = "", face: str | None = None) -> str:
    """
    根據合約資料 + 用戶問題，產出客戶理解的自然語言回應。

    contracts: JGB API 回傳的 data（list 或 dict）
    user_question: 用戶的原始問題
    keyword: 用戶在表單中輸入的合約編號或物件名稱（用於過濾）
    face: 當輪對話面向（FACE_BUILDERS 命中則走面向 fact-builder；None/未命中 → 現行路由）
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

    # face 命中註冊表 → 面向 fact-builder；未命中/None → 現行路由（零回歸）
    builder = FACE_BUILDERS.get(face) if face else None
    if builder:
        return builder(contract, user_question)

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

    if date_start == "未設定" and date_end == "未設定":
        header = f"您好，合約「{title}」目前為{stage}。\n"
    else:
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

    # 已完成的歷程（bit_status 逐位元機械解碼）：讓「某流程做了沒/完成沒」有據可答。
    bit_status_val = contract.get("bit_status", 0)
    milestones = decode_bit_status(bit_status_val)
    if milestones:
        lines.append(f"• 已完成的歷程：{'、'.join(milestones)}")

    # 進行中未完成（送出位元有、完成位元無 → 程式判定）：「缺某位元＝未完成」這種
    # 缺席推理 LLM 做不可靠（會把「已發送」腦補成「已完成」），由程式明講。
    pending = [text for sent, done, text in [
        (ContractBit.MOVE_OUT, ContractBit.MOVE_OUT_DONE, "點退已送出但租客尚未同意（點退未完成）"),
        (ContractBit.MOVE_IN, ContractBit.MOVE_IN_DONE, "點交已送出但租客尚未同意（點交未完成）"),
        (ContractBit.EARLY_TERMINATION, ContractBit.EARLY_TERMINATION_DONE,
         "提前解約申請中、尚未確認（未完成）"),
    ] if has_bit(bit_status_val, sent) and not has_bit(bit_status_val, done)]
    if pending:
        lines.append(f"• 進行中未完成：{'、'.join(pending)}")

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
        # 效力聲明：各 check_can_* 為系統獨立判定（jgb2 真規則），列出即可直接做——
        # 明講「彼此獨立/未列出者不可」，堵 LLM 用常識自加前置條件（如「要先點交才能點退」）。
        note = "以上操作皆可立即進行、彼此獨立無先後依賴；未列出的操作目前不可進行"
        if "點交" in available and "點退" in available:
            # 模型最常腦補的一點（「退租前須先交屋」常識先驗）直接講死——jgb2 canMoveOut
            # 不要求先點交，此為忠實語意陳述（決定性），非猜測。
            note += "。點退不以點交為前提，可略過點交直接點退"
        lines.append(f"\n目前可進行的操作：{'、'.join(available)}（{note}）")
    else:
        lines.append("\n目前沒有可進行的操作。")

    return "\n".join(lines)




# ── 工具函式 ────────────────────────────────────────────────

def _parse_date_int(date_val):
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
    if not date_val:
        return "未設定"
    dt = _parse_date_int(date_val)
    if dt:
        return _format_date(dt)
    return str(date_val)
