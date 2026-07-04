"""
JGB 帳號領域檔（account-conversational-facets 元件 4）

登入排障 face 的決定性 fact-builder：由 jgb_contracts 合約現值判定
「租客未註冊／疑似登錯帳號／帳號正常」三分支（research.md 主題 2）。
面向字面只允許出現在本檔與資料列；G 欄位存在性驅動（缺則降級不虛構）。
機制數字以 research.md 為準寫死（快速驗證信 72 小時），LLM 不得自創。
"""

from typing import Callable

from services.jgb.contracts import _mask_email

AccountFaceBuilder = Callable[[dict, str], str]   # (contract_row, user_question) -> facts 文字


def _plain_email(raw) -> str:
    """明文信箱防護（沿 G2 教訓）：jgb2 曾回加密密文（users.email 密文儲存、
    select 未解密），非明文（無 @）視同欄位不可用，避免假錯配與密文外洩。"""
    val = (raw or "").strip()
    return val if "@" in val else ""


def build_login_trouble_facts(contract: dict, user_question: str = "") -> str:
    """登入排障（R3.3；research.md 主題 2）。

    is_tenant_registered=False → 未註冊引導（邀請/快速驗證信 72 小時）；
    True＋登入信箱與邀請信箱不一致 → 疑似登錯帳號/多帳號（登入信箱遮罩輸出）；
    一致 → 帳號正常，轉角色視角與忘記密碼自助路徑。
    欄位缺失 → 誠實降級（不虛構註冊狀態、不虛構比對結果）。
    """
    title = contract.get("title", f"合約 {contract.get('id', '?')}")
    invite_email = (contract.get("to_user_email") or "").strip()
    lines = [f"合約「{title}」的租客登入狀況（依系統現值）："]

    # G-A1 附掛（secondary_call：tenants/registration-status，單元素 list）優先——
    # found 當歸屬閘門、is_registered＋email_verify 驅動三態排查。
    # 嚴格遮罩：registration 帶 lessee_name/lessee_user_id，一律不進回話。
    reg_list = contract.get("registration")
    reg = reg_list[0] if isinstance(reg_list, list) and reg_list else None
    if reg is not None:
        faced = _login_facts_from_registration(reg, invite_email, lines)
        if faced is not None:
            return faced

    registered = contract.get("is_tenant_registered")

    if registered is None:
        # 欄位缺失（存在性驅動）：不虛構註冊狀態，給一般排查
        lines.append("目前無法從系統確認這位租客的帳號註冊狀態。")
        lines.append("一般排查：請租客以「當初註冊時的確切寫法」輸入信箱登入；"
                     "若忘記密碼可在登入頁自助重設（Email 或手機簡訊驗證擇一）；"
                     "登入成功但看不到資料時，請確認左上角是否切換到正確的租客身分。")
        return "\n".join(lines)

    if not registered:
        lines.append("這位租客尚未註冊 JGB 帳號——登不進去是因為帳號還不存在，不是密碼問題。")
        if invite_email:
            lines.append(f"合約邀請發送至 {invite_email}：請租客用邀請連結完成註冊"
                         "（免註冊快速驗證信的連結效期為 72 小時，逾期需重新發送邀請）。")
        else:
            lines.append("合約上未設定租客 Email：請先補上租客聯絡方式並重新發送邀請，"
                         "租客才能收到註冊連結（快速驗證信連結效期 72 小時）。")
        return "\n".join(lines)

    lines.append("這位租客已註冊 JGB 帳號。")

    login_email = _plain_email(contract.get("to_user_login_email"))
    if login_email and invite_email:
        if login_email.lower() != invite_email.lower():
            lines.append(f"信箱比對：邀請發送至 {invite_email}，但租客實際登入帳號的信箱為 "
                         f"{_mask_email(login_email)}，兩者不一致——租客很可能登錯帳號"
                         "（或有另一個帳號），登入後自然看不到這份合約。"
                         "請租客改用該登入信箱的帳號登入，或將邀請重新發送至租客實際使用的信箱。")
            return "\n".join(lines)
        lines.append("信箱比對：邀請發送信箱與租客登入信箱一致，帳號本身正常。")
    else:
        # 登入信箱欄位缺失或密文 → 不比對、不虛構結果
        lines.append("（系統目前無法比對租客登入信箱，略過帳號錯配檢查。）")

    lines.append("後續排查：登入時請用「當初註冊時的確切寫法」輸入信箱；"
                 "忘記密碼可在登入頁自助重設（Email 或手機簡訊驗證擇一）；"
                 "登入成功但看不到合約或帳單時，請租客確認左上角身分選單已切換到租客身分。")
    return "\n".join(lines)


def _login_facts_from_registration(reg: dict, invite_email: str, lines: list) -> str | None:
    """G-A1（tenants/registration-status）三態排查——嚴格遮罩，只讀不吐。

    輸入欄位僅取 found／is_registered／lessee_email_verify_status 決定分支；
    lessee_name／lessee_user_id 絕不進 lines（個資最小揭露，account-api-contract 承諾）。
    None → 交回合約層邏輯（本函式不處理的情況）。"""
    if not reg.get("found"):
        # 歸屬閘門：查無此人為此團隊名下租客 → 導客服，不揭露任何帳號細節
        lines.append("系統查不到這位是您名下合約的租客——可能是聯絡資訊不符或非本團隊租客，"
                     "請聯繫客服協助確認，不需在此提供更多個資。")
        return "\n".join(lines)

    if not reg.get("is_registered"):
        lines.append("這位租客尚未完成 JGB 帳號註冊——登不進去是因為註冊還沒完成，不是密碼問題。")
        if invite_email:
            lines.append(f"請租客用您發送的邀請連結（寄至 {invite_email}）完成註冊"
                         "（免註冊快速驗證信連結效期 72 小時，逾期需重新發送邀請）。")
        else:
            lines.append("請確認合約已填租客聯絡方式並重新發送邀請，租客才會收到註冊連結"
                         "（連結效期 72 小時）。")
        return "\n".join(lines)

    if not reg.get("lessee_email_verify_status"):
        lines.append("這位租客已建立帳號，但 Email 尚未完成驗證——請租客收驗證信、"
                     "點信中連結完成驗證後即可登入（驗證碼效期 5 分鐘、輸錯三次需重新取得）。")
        return "\n".join(lines)

    lines.append("這位租客的帳號已註冊且信箱已驗證，帳號本身正常——方向轉向登入操作：")
    lines.append("請租客以「當初註冊時的確切寫法」輸入信箱登入；忘記密碼可在登入頁自助重設"
                 "（Email 或手機簡訊驗證擇一）；登入成功卻看不到合約/帳單時，"
                 "請確認左上角身分選單已切換到租客身分。")
    return "\n".join(lines)


# 資源類型 → (全團隊旗標, 只看經手旗標) 對照（自訂角色亦適用，判定靠旗標非角色名）。
_VISIBILITY_FLAGS = {
    "帳單": ("show_bill", "show_owner_bill"),
    "合約": ("show_contract", "show_owner_contract"),
    "物件": ("show_estate", "show_owner_estate"),
}


def build_team_permission_facts(member: dict, user_question: str = "") -> str:
    """團隊成員權限（完整版；research 主題 4）——旗標驅動＋T2 具體可見性確認。

    主查 T1 成員列；secondary attach：permissions（abilities 旗標）、bill_visibility（T2）。
    擁有者→全看；成員依成對旗標（show_X/show_owner_X）決定性解釋可見範圍，
    T2 確認該具體資源看不看得到。嚴格遮罩：member_user_id 不進回話。
    無 permissions attach → 降級沿知識口徑（去成員列表變更角色）。
    """
    role_name = member.get("character_name") or "該成員"

    if member.get("is_owner"):
        return (f"這位是「{role_name}」（團隊擁有者）——擁有者可看團隊全部資料，"
                "看不到特定資料通常不是權限問題，請確認左上角身分是否切到此團隊、或重新整理。")

    perm_list = member.get("permissions")
    perm = perm_list[0] if isinstance(perm_list, list) and perm_list else None
    if perm is None:
        # 降級：無旗標資料 → 沿團隊權限知識口徑
        return (f"這位成員的角色是「{role_name}」。若他看不到應有的資料，"
                "多半是角色權限未開或未指派——請到團隊管理的成員列表對他「變更角色」檢視與調整權限。")

    abilities = perm.get("abilities") or {}
    role_name = perm.get("character_name") or role_name
    # 資源類型（問句含關鍵字 → 對應旗標；預設帳單）
    kind = next((k for k in _VISIBILITY_FLAGS if k in (user_question or "")), "帳單")
    show_all, show_owner = _VISIBILITY_FLAGS[kind]
    can_all = bool(abilities.get(show_all))
    can_owner = bool(abilities.get(show_owner))

    # T2：該具體資源可見性（bill_visibility attach 存在＝有問具體資源；非空＝看得到）
    has_t2 = isinstance(member.get("bill_visibility"), list)
    visible = has_t2 and bool(member.get("bill_visibility"))

    lines = [f"這位成員的角色是「{role_name}」。"]

    if not can_all and not can_owner:
        lines.append(f"這個角色沒有開啟「檢視{kind}」的權限——所以他看不到任何{kind}。"
                     f"解法：到成員列表為他變更角色、開啟{kind}檢視權限。")
        return "\n".join(lines)

    if can_all:
        lines.append(f"這個角色可看全團隊的{kind}。")
        if has_t2 and visible:
            lines.append(f"系統確認他其實看得到這筆{kind}——看不到多半不是權限問題，"
                         "請確認他左上角身分已切到此團隊、或重新整理頁面。")
        else:
            lines.append(f"若他反映看不到某筆{kind}，請確認該{kind}狀態正常（非草稿/封存），"
                         "或聯繫客服協助核查。")
        return "\n".join(lines)

    # 只看經手（show_owner_X）
    lines.append(f"這個角色只看得到「自己被指派為經理人」的{kind}（僅 show_owner，非全團隊）。")
    if not has_t2:
        # 泛問（未指定具體資源）：只解釋機制＋給自查方向
        lines.append(f"所以他只看得到被指派為經理人的{kind}；某筆看不到，多半是那筆對應的"
                     f"合約/物件沒指派他為經理人——請確認指派，或改用可看全團隊{kind}的角色。")
    elif visible:
        lines.append(f"系統確認他看得到這筆{kind}；若仍反映看不到，請確認身分切換或重新整理。")
    else:
        lines.append(f"系統確認他看不到這筆{kind}——因為這筆對應的合約/物件沒有指派他為經理人。"
                     f"解法：把該合約/物件指派他為經理人，或改用可看全團隊{kind}的角色。")
    return "\n".join(lines)


# ── 帳號面向 fact-builder 註冊表 ────────────────────────────────────────────
#
# face 命中 → builder 接手；未命中 → contracts.py 現行路由（零回歸）。
# G-A1/A2 查詢能力上線後，註冊驗證排障/團隊成員權限的 grounded builder 於此擴充。

ACCOUNT_FACE_BUILDERS: dict[str, AccountFaceBuilder] = {
    "登入排障": build_login_trouble_facts,
    "團隊成員權限": build_team_permission_facts,
}
