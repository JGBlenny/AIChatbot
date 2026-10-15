"""確認卡的**決定性** render（DSP-038-2｜子 spec `agent-write-tools` W2）。

## 為什麼卡文字不能是模型寫的 `summary`
`confirm.request(summary, payload)` 的 `summary` 是**模型**產生的自由文字，
而 `payload` 才是真正會被送去執行的參數。兩者由模型分別填 ⇒ 它們可以不一致：
卡上寫「延 3 天」、payload 寫 90 天，使用者按下確認時同意的是他看到的那一張卡，
系統執行的卻是 payload。DSP-038-2 的處置是把兩者**綁死**：

    卡文字 = render(action, payload)          ← 只從 payload 導出，模型碰不到
    summary_sha256 = sha256(卡文字)           ← 存進 agent_confirmation_tokens
    TurnResult.answer = 卡文字（逐字）         ← 使用者看到的就是這一份

於是「使用者看到的字」「表裡的雜湊」「將被執行的 payload」三者是同一份資料的
三種形式，⛔ 中間沒有模型可以插手的縫。

## 決定性的定義（本檔的硬約束）
- **同 payload 必得同一個字串**：⛔ 不讀時鐘、⛔ 不讀 env、⛔ 不查 DB、⛔ 不呼叫
  LLM、⛔ 不依賴 dict 的插入順序（每個 action 的欄位順序寫死在 render 裡）。
- **缺欄位就 raise**（`ConfirmCardError`）：呼叫端（`confirm.request`）把它翻成
  `INVALID_INPUT`。⛔ 不用預設值補、⛔ 不「盡力而為」印半張卡——半張卡會讓使用者
  對著一個他沒看到的欄位按下確認。
- **不推測**：`date_expire_after` 必須由呼叫端明給，本檔只**驗算**它等於
  `起算日 + days`（起算日＝原到期日與 `today` 較晚者；`today` 缺省時就是原到期日，
  見檔尾「日期有效性」段）；⛔ 不在缺值時自己算出來當成使用者確認過的事實。
  ⚠️ `today` 一律是**關鍵字參數**、由呼叫點傳入，⛔ 不從 payload 讀——payload 是
  模型控制的資料，讓它決定起算基準等於把驗算交回給被驗的那一方。

## `emergency_status` 是已知地雷（⛔ 不可望文生義）
`1＝非緊急、2＝緊急`（jgb2 DB 真值）。jgb2 對外 `mapping` 曾把它標反，
本 repo 的既有處置是「一律用自家真值對照，⛔ 不信任回應附的 mapping」。
⚠️ 舊鏈曾有第二份同義對照表（`services/jgb_response_formatter.py` 的
`_EMERGENCY_STATUS_LABELS`），本檔的 `_EMERGENCY_ZH` 曾與它逐鍵對帳防漂移；
該模組已隨舊鏈於 2026-09-10 退役，對帳測試一併移除——**這裡的真值本身不變**，
只是失去了跨模組的重複校驗，⛔ 改這兩個鍵前務必重查 jgb2 DB 真值，不能只憑
「原本兩邊都這樣寫」當依據。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Final, Mapping, Tuple, Optional

# 自由文字欄位的正規化判準（T1 共用落點，⛔ 不另寫一份）。見 `_closed_text`。
from services.agent.completed_actions import sanitize_data_piece

#: 站內幫手 S2（plan-assistant-11-items-20261014 §3f；jgb2-req#19～#21）三個**封閉欄位表**動作。
ESTATE_CREATE_ACTION: Final[str] = "estate_create"
CONTRACT_CREATE_ACTION: Final[str] = "contract_create"
MANUAL_BILL_CREATE_ACTION: Final[str] = "manual_bill_create"

#: `payload.action` 的**封閉值域**（DSP-038-2）。⛔ 不在此之外接受任何 action——
#: 沒有 render 分支的 action 等於「使用者看到的卡由誰決定」沒有答案。
#: 新增動作＝新增一個 render 分支＋一組欄位契約，⛔ 不是在這裡加一個字串。
CONFIRM_ACTIONS: Final[Tuple[str, ...]] = (
    "bill_due_extend", "repair_create",
    ESTATE_CREATE_ACTION, CONTRACT_CREATE_ACTION, MANUAL_BILL_CREATE_ACTION,
)

#: 欄位屬性的**已知值域**（S1）。⛔ 新屬性要先進這個集合才准出現在下面那張表裡，
#: 否則「表裡寫了一個沒有人實作的屬性」會靜默地什麼都不擋。
CONFIRM_FIELD_ATTR_NAMES: Final[frozenset] = frozenset({"not_before_today"})

#: 屬性名常數：兩道閘與表都只認這個符號，⛔ 不在別處抄字面量。
NOT_BEFORE_TODAY: Final[str] = "not_before_today"

#: **欄位屬性表**（S1｜H1）：`action → {欄位 → {屬性…}}`。
#: `not_before_today`＝這一欄的語義是「今天或以後的日期」——⛔ 不是
#: `bill_due_extend` 的特例：兩道閘一律**以屬性迭代這張表**（見
#: `fields_before_today`），未來任何帶未來日期語義的動作**只加表項、不加程式**，
#: ⛔ 任何地方都不得出現以 action 名為條件的分支。
#: ⚠️ 被標記的欄位必須是該 action 的 render 真的會解析的日期欄位——
#: `tests/unit/agent/test_confirm_date_gate_req.py` 以「缺值必拋 `ConfirmCardError`、
#: 給合法日期 render 成功」逐欄證明，⛔ 不靠人工對照。
CONFIRM_FIELD_ATTRS: Final[dict[str, dict[str, frozenset]]] = {
    "bill_due_extend": {"date_expire_after": frozenset({NOT_BEFORE_TODAY})},
    # S2 §3f 1c：手動帳單的繳費期限 ⛔ 早於今天（防誤打成立即逾期的帳單）。
    # ⚠️ `contract_create.date_start`／`date_end` **刻意不標**：登錄既有租約時起始日
    #    早於今天是常態；那兩欄只驗格式與「結束晚於起始」（見 `_closed_cross_check`）。
    MANUAL_BILL_CREATE_ACTION: {"date_expire": frozenset({NOT_BEFORE_TODAY})},
}
# 值域與分支表必須同步（啟動期就炸，同 `_RENDERERS` 的紀律）
assert set(CONFIRM_FIELD_ATTRS) <= set(CONFIRM_ACTIONS)
assert all(
    attrs <= CONFIRM_FIELD_ATTR_NAMES
    for fields in CONFIRM_FIELD_ATTRS.values()
    for attrs in fields.values()
)

#: `emergency_status` 的中文（jgb2 DB 真值；見模組 docstring 的地雷說明）。
_EMERGENCY_ZH: Final[dict[int, str]] = {1: "非緊急", 2: "緊急"}

#: 描述留空時卡上顯示的字（⛔ 不是推測出來的內容，是「這一欄使用者沒填」的明示）。
EMPTY_DESCRIPTION_ZH: Final[str] = "（未填寫）"

#: delta4（業主 2026-09-08「delta4 採」）：分類與急迫**缺值由程式補、模型不反問**。
#: 分類缺值 ⇒ 歸到分類樹的「其他」大類（`DEFAULT_CATEGORY_NAME`，`repair_create` 依名稱在
#: 分類樹裡解出 id，⛔ 不寫死 id）；卡上明示「（未指定，歸其他）」，⛔ 不假裝是使用者選的。
#: 急迫缺值 ⇒ `DEFAULT_EMERGENCY_STATUS`＝1（非緊急；正本 A/repair-ticket-urgency-judgment）。
#: 「缺值」＝鍵不存在、`None`、或去空白後為空字串——三者對這兩欄同義（與 `description`
#: 「鍵必須存在」的紀律不同：那一欄的空字串是使用者的內容，這兩欄的空值是「交給系統」）。
DEFAULT_CATEGORY_NAME: Final[str] = "其他"
UNSPECIFIED_CATEGORY_ZH: Final[str] = f"{DEFAULT_CATEGORY_NAME}（未指定，歸其他）"
DEFAULT_EMERGENCY_STATUS: Final[int] = 1


def category_name_of(payload: Mapping[str, Any]) -> Optional[str]:
    """payload 裡的分類名稱；缺值（無鍵／None／空白）⇒ `None`＝交給系統歸「其他」。"""
    value = payload.get("category_name")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfirmCardError("repair_create: 欄位 'category_name' 必須是字串或不填")
    return value.strip() or None


def emergency_status_of(payload: Mapping[str, Any]) -> int:
    """payload 裡的急迫值；缺值 ⇒ `DEFAULT_EMERGENCY_STATUS`；給了就必須在值域內。"""
    value = payload.get("emergency_status")
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_EMERGENCY_STATUS
    if isinstance(value, bool) or value not in _EMERGENCY_ZH:
        raise ConfirmCardError(
            "repair_create: 欄位 'emergency_status' 必須是 1（非緊急）或 2（緊急）或不填"
        )
    return int(value)

#: **保留鍵**：這些名字是 `render()` 自己的關鍵字參數，⛔ payload 裡出現一律
#: `ConfirmCardError`（呼叫端翻成 `INVALID_INPUT`）。理由：`today` 是驗算的**基準**，
#: 基準若能由 payload 帶進來，模型就能自訂「延 N 天從哪一天起算」——那等於把驗算
#: 交回給被驗的那一方。⚠️ 二擇一固定為**拒絕**（⛔ 不是靜默忽略）：靜默忽略會讓
#: 一份帶著 `today` 的 payload 看起來被接受了，使用者無從得知它沒有生效。
RESERVED_PAYLOAD_KEYS: Final[frozenset] = frozenset({"today"})

#: 每張卡的收尾句。⛔ 不在此複述三顆按鈕的文案——按鈕 label 的唯一來源是
#: `conversational_engine._DEFAULT_QR_LABELS`（`confirm.confirm_quick_replies` 取用），
#: 在卡文字裡抄一份等於多一處會各自演化的字面量。
CARD_FOOTER: Final[str] = "請從下方按鈕擇一。"


class ConfirmCardError(ValueError):
    """payload 缺欄位／型別不對／`action` 不在封閉值域內。

    ⚠️ 訊息只寫**欄位名與 action**，⛔ 不回填欄位值——這個例外的字串會被
    `confirm.request` 記進 log，把使用者的合約編號／描述印進 log 就是新的外洩面。
    """


def _require(payload: Mapping[str, Any], key: str, action: str) -> Any:
    if not isinstance(payload, Mapping) or key not in payload:
        raise ConfirmCardError(f"{action}: payload 缺必填欄位 {key!r}")
    return payload[key]


def _require_text(payload: Mapping[str, Any], key: str, action: str) -> str:
    value = _require(payload, key, action)
    if not isinstance(value, str) or not value.strip():
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須是非空字串")
    return value.strip()


def _require_ref(payload: Mapping[str, Any], key: str, action: str) -> str:
    """識別碼：允許字串或整數（jgb2 的 id 兩種形狀都出現過），一律轉字串。"""
    value = _require(payload, key, action)
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須是字串或整數")
    text = str(value).strip()
    if not text:
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 不得為空")
    return text


def _parse_date(value: Any, key: str, action: str) -> date:
    """`YYYYMMDD`（int 或 str）⇒ `date`。

    形狀取自 jgb2 的日期整數欄位慣例（舊鏈 `jgb_response_formatter.DATE_INT_KEYS`
    曾是這個慣例的同源引用，該模組已隨舊鏈於 2026-09-10 退役；`YYYYMMDD` 本身
    是 jgb2 API 的欄位慣例，不隨舊鏈存廢而變）。
    ⛔ 不接受其他寫法——多接受一種寫法就多一種「同一天算出兩張不同卡」的可能。
    """
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須是 YYYYMMDD 的字串或整數")
    text = str(value).strip()
    if len(text) != 8 or not text.isdigit():
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 不是 YYYYMMDD 形狀")
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:]))
    except ValueError as exc:
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 不是合法日期") from exc


def _fmt_date(value: date) -> str:
    return f"{value.year:04d}/{value.month:02d}/{value.day:02d}"


def _require_days(payload: Mapping[str, Any], key: str, action: str) -> int:
    value = _require(payload, key, action)
    if isinstance(value, bool) or not isinstance(value, int):
        # ⛔ 不收 "3" 這種字串：位移天數是要拿來算日期的，字串轉數字這一步
        #    一旦容忍，"03"／" 3 " 就會產出同語義但不同來源的卡。
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須是整數")
    if value <= 0:
        raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須為正整數")
    return value


def _lines_to_card(title: str, rows: list[tuple[str, str]]) -> str:
    body = "\n".join(f"・{label}：{value}" for label, value in rows)
    return f"{title}\n{body}\n{CARD_FOOTER}"


def _render_bill_due_extend(payload: Mapping[str, Any], today: Optional[date]) -> str:
    action = "bill_due_extend"
    bill_id = _require_ref(payload, "bill_id", action)
    before = _parse_date(_require(payload, "date_expire_before", action),
                         "date_expire_before", action)
    days = _require_days(payload, "days", action)
    after = _parse_date(_require(payload, "date_expire_after", action),
                        "date_expire_after", action)
    # ⚠️ **起算日＝原到期日與今天較晚者**（V3）。走查病灶：原到期日已逾期時，
    #    「延三天」以原到期日起算會算出一個**仍在過去**的新到期日，S1 閘門把它
    #    擋掉，使用者只看到「不能延」。語義上「延三天」是從今天起再給三天。
    #    ⚠️ `today` 缺省（`None`）⇒ 起算日就是原到期日＝**舊行為逐字不變**，
    #    留給沒有時鐘的呼叫端與純形狀測試用。
    base = max(before, today) if today else before
    # ⚠️ **驗算而不是代算**（見模組 docstring「不推測」）：新到期日必須是呼叫端
    #    明給的那一個，且必須等於 起算日 + 天數。三個數字彼此矛盾時 ⛔ 不挑一個
    #    來印——那等於替使用者決定他同意的是哪一個。
    #    ⛔ 不得以「放寬 days 驗算」來解決逾期帳單：這條等式與 `payload_digest`
    #    一起構成卡↔payload 的綁定，放寬它就是把綁定拆開。
    if base + timedelta(days=days) != after:
        raise ConfirmCardError(
            f"{action}: 起算日 + days 與 date_expire_after 不一致"
        )
    return _lines_to_card(
        "即將調整帳單到期日，請確認：",
        [
            ("帳單編號", bill_id),
            ("原到期日", _fmt_date(before)),
            # 起算日**印在卡上**：「原到期日 8/15、延 3 天、新到期日 9/12」單看
            # 三個數字對不起來，使用者會遲疑。⛔ 不靠模型在 summary 裡解釋。
            ("起算日", _fmt_date(base)),
            ("延後天數", f"{days} 天"),
            ("新到期日", _fmt_date(after)),
        ],
    )


# ---------------------------------------------------------------------------
# 站內幫手 S3（F10／S3-5／S3-13）：修繕單附照片——卡上「附照片」一行
#
# ⚠️ 兩個鍵**只由程式寫入**（`runtime` 在 `confirm.request` 前無條件刪掉模型帶的
#    照片相關鍵，再由本回合已過閘的伺服端照片中繼資料寫入），與其他欄位一樣進
#    `payload_sha256`、由本函式驗形狀並印在卡上 ⇒ 使用者確認的張數＝送出的張數。
# ---------------------------------------------------------------------------
#: 修繕單一次最多附幾張（jgb2-req#22 提案 `photo_policy.max_count`）。
REPAIR_PHOTOS_MAX: Final[int] = 5
#: payload 的照片鍵：`broken_photos`＝中繼資料清單；`broken_photos_omitted`＝超過上限
#: 時「全部不附」的張數（只上卡說明，⛔ 不送）。
PHOTO_PAYLOAD_KEYS: Final[Tuple[str, str]] = ("broken_photos", "broken_photos_omitted")
_PHOTO_META_KEYS: Final[frozenset] = frozenset({"filename", "content_type", "size", "sha256"})
_PHOTO_CONTENT_TYPES: Final[frozenset] = frozenset({"image/jpeg", "image/png", "image/webp"})
_SHA256_RE: Final = re.compile(r"[0-9a-f]{64}")
_PHOTO_NAME_RE: Final = re.compile(r"photo-[0-9]{1,2}\.(?:jpg|png|webp)")


def repair_photos_of(payload: Mapping[str, Any]) -> list:
    """payload 的照片中繼資料（驗過形狀）；沒有 ⇒ `[]`。不合 ⇒ `ConfirmCardError`。"""
    photos = payload.get("broken_photos")
    if photos is None:
        return []
    if not isinstance(photos, list) or not 1 <= len(photos) <= REPAIR_PHOTOS_MAX:
        raise ConfirmCardError("repair_create: 欄位 'broken_photos' 張數不合")
    for p in photos:
        if (not isinstance(p, Mapping) or set(p) != _PHOTO_META_KEYS
                or not isinstance(p["filename"], str) or not _PHOTO_NAME_RE.fullmatch(p["filename"])
                or p["content_type"] not in _PHOTO_CONTENT_TYPES
                or isinstance(p["size"], bool) or not isinstance(p["size"], int)
                or not 0 < p["size"] <= 5_000_000
                or not isinstance(p["sha256"], str) or not _SHA256_RE.fullmatch(p["sha256"])):
            raise ConfirmCardError("repair_create: 欄位 'broken_photos' 形狀不合")
    return [dict(p) for p in photos]


def _photo_row(payload: Mapping[str, Any]) -> Optional[tuple]:
    """卡上「附照片」那一行；沒有照片 ⇒ `None`（⛔ 印「0 張」）。"""
    photos = repair_photos_of(payload)
    omitted = payload.get("broken_photos_omitted")
    if omitted is not None:
        if photos or isinstance(omitted, bool) or not isinstance(omitted, int) \
                or omitted <= REPAIR_PHOTOS_MAX:
            raise ConfirmCardError("repair_create: 欄位 'broken_photos_omitted' 不合")
        return ("附照片", f"未附（本次 {omitted} 張，超過 {REPAIR_PHOTOS_MAX} 張上限）")
    if photos:
        return ("附照片", f"{len(photos)} 張")
    return None


def _render_repair_create(payload: Mapping[str, Any], today: Optional[date]) -> str:
    # ⚠️ 簽章與 `_render_bill_due_extend` 一致（`_RENDERERS` 統一傳 `today`），
    #    ⛔ 不在 `render()` 裡按 action 名決定要不要傳——本 action 沒有日期語義，
    #    單純不用它。
    action = "repair_create"
    estate = _require_text(payload, "estate_name", action)
    # 分類**允許父節點**（line-bot 線③：分類樹涵蓋不到時退回大類，
    # ⛔ 不編一個不存在的葉節點）；**允許缺值**（delta4）⇒ 卡上明示歸「其他」。
    # 本檔不驗它是不是分類樹裡的節點——那是 `repair_create` 範圍讀的事。
    category = category_name_of(payload) or UNSPECIFIED_CATEGORY_ZH
    # 描述**允許空字串**，但鍵必須存在：「沒填」與「忘了帶這個欄位」是兩件事，
    # 後者代表呼叫端的 payload 形狀有問題，⛔ 不得靜默當成前者。
    description = _require(payload, "description", action)
    if not isinstance(description, str):
        raise ConfirmCardError(f"{action}: 欄位 'description' 必須是字串（可為空字串）")
    emergency = emergency_status_of(payload)   # 缺值 ⇒ 非緊急（delta4）
    rows = [
        ("物件", estate),
        ("修繕分類", category),
        ("急迫程度", _EMERGENCY_ZH[emergency]),
        ("問題描述", description.strip() or EMPTY_DESCRIPTION_ZH),
    ]
    # S3：有照片才多印一行（沒照片的卡逐字不變）。
    photo_row = _photo_row(payload)
    if photo_row is not None:
        rows.append(photo_row)
    return _lines_to_card("即將建立修繕單，請確認：", rows)


# ---------------------------------------------------------------------------
# 站內幫手 S2（§3f 1／F3）：三個**封閉欄位表**動作
#
# ⚠️ **一張表、三個用途**：同一份 `_ClosedField` 表同時決定
#      ① 卡上印哪幾行（`_render_closed`）、
#      ② 送給 jgb2 的 body 有哪幾欄（`closed_body`，`tools/action.py` 用）、
#      ③ 缺必填時回給模型的缺欄清單（`missing_required_labels`，`tools/confirm.py` 用）。
#    三者都由同一個「這一欄有沒有給」判準（`_given`）與同一套正規化導出 ⇒
#    「卡上沒有的欄位卻被送出」「使用者沒給的選填被補值」在結構上不可能。
# ⚠️ **封閉**：payload 只准出現表內的鍵＋`action`＋該動作明列的「收下但不用」鍵；
#    身分／歸屬鍵（`IDENTITY_OWNERSHIP_KEYS`）或任何未知鍵一律 `ConfirmCardError`
#    （呼叫端翻 `INVALID_INPUT`）。⛔ 不靜默丟掉——丟掉會讓一份夾帶 `role_id` 的
#    payload 看起來被接受了。歸屬一律只取自 identity（`tools/action._identity_pair`）。
# ⚠️ **系統填的編號**（`contract_create.estate_id`、`manual_bill_create.contract_id`）
#    由 `confirm.request` 在出卡**之前**以帶 viewer 的查詢解析後寫入（§3f 1d），
#    卡上與名稱印在同一行；兌現時直接用、⛔ 不依名稱重解。
# ---------------------------------------------------------------------------

#: 身分鍵＋歸屬鍵（F3／jgb2-req#23）。payload 出現任一個 ⇒ `ConfirmCardError`。
#: ⚠️ 歸屬鍵與替身 `JGBMockTransport._OWNERSHIP_KEYS` 同一份清單（測試以集合包含互證，
#:    ⛔ 不在此 import 替身——agent 層不依賴 mock transport）。
IDENTITY_OWNERSHIP_KEYS: Final[frozenset] = frozenset({
    "role_id", "user_id",
    "team_id", "owner_user_id", "owner_role_id", "vendor_id", "to_user_id",
    "agent_user_id", "created_by", "issue_target_role_id",
})


@dataclass(frozen=True)
class _ClosedField:
    """封閉欄位表的一列。

    kind：`text`（字串，過 `sanitize_data_piece`、限長）／`enum`（封閉值域，卡上印中文）／
    `int`（整數，⛔ 收字串與布林）／`number`（整數或小數）／`date`（`YYYYMMDD`，送出轉
    `YYYY-MM-DD`）／`email`／`phone`／`sys_id`（系統解析後寫入的編號）。
    `in_body=False` ⇒ 只上卡、⛔ 不進 body（名稱指稱鍵）。
    """

    key: str
    label: str
    kind: str
    required: bool = False
    max_len: int = 0
    lo: Any = None
    hi: Any = None
    choices: Optional[Mapping[str, str]] = None
    in_body: bool = True
    unit: str = ""


#: `use_for` 的封閉值域（jgb2-req#19）與卡上中文。
USE_FOR_ZH: Final[dict[str, str]] = {
    "residential": "住宅", "business": "商用", "parking_space": "車位",
}

_EMAIL_RE: Final = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_PHONE_RE: Final = re.compile(r"[0-9+\-]{8,15}")

#: jgb2-req#19 建立物件。值域照總帳該列（⛔ 不自創更嚴或更鬆的範圍）；
#: 未寫上限的文字欄位沿用替身 `_assistant_create_estate` 的長度。
ESTATE_CREATE_FIELDS: Final[Tuple[_ClosedField, ...]] = (
    _ClosedField("title", "物件名稱", "text", required=True, max_len=60),
    _ClosedField("city", "縣市", "text", required=True, max_len=20),
    _ClosedField("district", "行政區", "text", required=True, max_len=20),
    _ClosedField("address", "地址", "text", required=True, max_len=100),
    _ClosedField("use_for", "用途", "enum", required=True, choices=USE_FOR_ZH),
    _ClosedField("space_type", "空間類型", "text", max_len=20),
    _ClosedField("building", "建物類型", "text", max_len=20),
    _ClosedField("room_count", "房間數", "int", lo=0, hi=99),
    _ClosedField("size", "面積", "number", lo=0, hi=100000),
    _ClosedField("rent", "租金", "int", lo=0, hi=99_999_999, unit="元"),
    _ClosedField("floor", "樓層", "text", max_len=10),
)

#: jgb2-req#20 建立合約。`estate_name` 是物件指稱鍵（使用者口述／物件記憶補上，出卡時
#: 改寫成解析後的物件名稱），`estate_id` 是系統解析後寫入的編號（§3f 1b／1d）。
CONTRACT_CREATE_FIELDS: Final[Tuple[_ClosedField, ...]] = (
    _ClosedField("estate_name", "物件", "text", required=True, max_len=60, in_body=False),
    _ClosedField("estate_id", "物件編號", "sys_id", required=True),
    _ClosedField("date_start", "起租日", "date", required=True),
    _ClosedField("date_end", "到期日", "date", required=True),
    _ClosedField("rent", "租金", "int", required=True, lo=1, hi=99_999_999, unit="元"),
    _ClosedField("to_user_email", "承租人 Email", "email", max_len=100),
    _ClosedField("to_user_phone", "承租人電話", "phone"),
    _ClosedField("deposit_amount", "押金", "int", lo=0, hi=99_999_999, unit="元"),
    _ClosedField("title", "合約名稱", "text", max_len=60),
)

#: jgb2-req#21 建立手動帳單。`contract_ref` 是合約指稱鍵（出卡時改寫成解析後的合約名稱），
#: `contract_id` 是系統解析後寫入的編號（§3f 1b／1d）。
MANUAL_BILL_CREATE_FIELDS: Final[Tuple[_ClosedField, ...]] = (
    _ClosedField("contract_ref", "合約", "text", required=True, max_len=60, in_body=False),
    _ClosedField("contract_id", "合約編號", "sys_id", required=True),
    _ClosedField("title", "帳單項目", "text", required=True, max_len=60),
    _ClosedField("total", "金額", "int", required=True, lo=1, hi=9_999_999, unit="元"),
    _ClosedField("date_expire", "繳費期限", "date", required=True),
    _ClosedField("sub_title", "說明", "text", max_len=100),
)

CLOSED_ACTION_FIELDS: Final[dict[str, Tuple[_ClosedField, ...]]] = {
    ESTATE_CREATE_ACTION: ESTATE_CREATE_FIELDS,
    CONTRACT_CREATE_ACTION: CONTRACT_CREATE_FIELDS,
    MANUAL_BILL_CREATE_ACTION: MANUAL_BILL_CREATE_FIELDS,
}

#: 「收下但 ⛔ 上卡、⛔ 進 body」的鍵（§3f 1b）：`runtime._apply_estate_carry_to_confirm_args`
#: 對 `CONFIRM_ACTIONS` 內任何 action 都可能補上 `estate_name`（⛔ 改 runtime），
#: 所以這三個動作都得收這個鍵；`contract_create` 的 `estate_name` 本來就在表內。
#: `manual_bill_create` 缺 `contract_ref` 時由 `confirm.request` 以它解析合約。
CLOSED_ACTION_EXTRA_KEYS: Final[dict[str, frozenset]] = {
    ESTATE_CREATE_ACTION: frozenset({"estate_name"}),
    CONTRACT_CREATE_ACTION: frozenset(),
    MANUAL_BILL_CREATE_ACTION: frozenset({"estate_name"}),
}

#: 「至少給一個」的欄位組（jgb2-req#20：`to_user_email`／`to_user_phone` 至少一個）。
#: 缺欄清單裡印的是這一組的標籤（固定詞彙）。
CLOSED_ACTION_ANY_OF: Final[dict[str, Tuple[Tuple[Tuple[str, ...], str], ...]]] = {
    ESTATE_CREATE_ACTION: (),
    CONTRACT_CREATE_ACTION: ((("to_user_email", "to_user_phone"), "承租人 Email 或電話"),),
    MANUAL_BILL_CREATE_ACTION: (),
}

#: 名稱指稱鍵在「系統尚未解析」時的替代來源（缺欄清單用；⛔ 不影響 render）：
#: `manual_bill_create` 缺 `contract_ref` 但有 `estate_name` ⇒ 「合約」不算缺（由物件解析）。
_REF_ALTERNATIVES: Final[dict[str, dict[str, Tuple[str, ...]]]] = {
    MANUAL_BILL_CREATE_ACTION: {"contract_ref": ("estate_name",)},
}

_CLOSED_CARD_TITLES: Final[dict[str, str]] = {
    ESTATE_CREATE_ACTION: "即將建立物件，請確認：",
    CONTRACT_CREATE_ACTION: "即將建立合約，請確認：",
    MANUAL_BILL_CREATE_ACTION: "即將建立手動帳單，請確認：",
}

#: 系統編號與名稱指稱鍵**合印一行**：`(名稱鍵, 編號鍵)`，卡上印「名稱（編號 N）」。
_CLOSED_REF_LINES: Final[dict[str, Tuple[str, str]]] = {
    CONTRACT_CREATE_ACTION: ("estate_name", "estate_id"),
    MANUAL_BILL_CREATE_ACTION: ("contract_ref", "contract_id"),
}

assert set(CLOSED_ACTION_FIELDS) == set(CLOSED_ACTION_EXTRA_KEYS) == set(CLOSED_ACTION_ANY_OF)
assert set(CLOSED_ACTION_FIELDS) <= set(CONFIRM_ACTIONS)


def _given(value: Any) -> bool:
    """「這一欄有給」＝不是 `None`、也不是去空白後為空的字串。

    ⚠️ 卡、body、缺欄清單三處共用這一個判準：選填給 `null`／空字串＝沒給 ⇒
    卡上不出現、body 不送（⛔ 不補值）；必填給 `null`／空字串＝缺。
    """
    if value is None:
        return False
    return not (isinstance(value, str) and not value.strip())


def _closed_value(action: str, f: _ClosedField, value: Any) -> Any:
    """驗一欄並回**正規化後**的值（卡與 body 共用）；不合 ⇒ `ConfirmCardError`。

    ⚠️ 訊息只寫欄位名，⛔ 不回填欄位值（同 `ConfirmCardError` 的紀律）。
    """
    key = f.key
    if f.kind == "text":
        if not isinstance(value, str):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須是字串")
        # ⚠️ 過 `sanitize_data_piece`（換行／控制字元／零寬／雙向控制／假標記）：
        #    會被它改動的值一律**拒絕**，⛔ 不靜默改寫——卡上印的、body 送的必須是
        #    同一個字串，改寫後再送等於送出一個使用者沒在卡上看過的版本。
        if sanitize_data_piece(value) != value:
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 含不允許的字元")
        text = value.strip()
        if not text or len(text) > f.max_len:
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 長度須為 1～{f.max_len} 字")
        return text
    if f.kind == "enum":
        if not isinstance(value, str) or value not in (f.choices or {}):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 不在允許的值域內")
        return value
    if f.kind in ("int", "sys_id"):
        if f.kind == "sys_id" and isinstance(value, str) and value.strip().isdigit():
            # 系統編號：jgb2 的 id 兩種形狀都出現過（同 `_require_ref`）。
            value = int(value.strip())
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須是整數")
        lo = 1 if f.kind == "sys_id" else f.lo
        if (lo is not None and value < lo) or (f.hi is not None and value > f.hi):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 超出允許範圍")
        return value
    if f.kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 必須是數字")
        # `lo` 是**開區間**（> 0）；NaN／inf 在比較上必然不成立 ⇒ 一併擋下。
        if not (f.lo < value <= f.hi):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 超出允許範圍")
        return value
    if f.kind == "date":
        return _parse_date(value, key, action)
    if f.kind == "email":
        if (not isinstance(value, str) or sanitize_data_piece(value) != value
                or not _EMAIL_RE.fullmatch(value.strip()) or len(value.strip()) > f.max_len):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 不是合法的 Email")
        return value.strip()
    if f.kind == "phone":
        if not isinstance(value, str) or not _PHONE_RE.fullmatch(value.strip()):
            raise ConfirmCardError(f"{action}: 欄位 {key!r} 不是合法的電話")
        return value.strip()
    raise ConfirmCardError(f"{action}: 欄位 {key!r} 的型別未定義")   # 表寫錯（大聲失敗）


def check_closed_keys(action: str, payload: Mapping[str, Any]) -> None:
    """封閉鍵集合：身分／歸屬鍵與未知鍵一律拒（⛔ 靜默丟掉）。"""
    keys = set(payload) - {"action"}
    forbidden = keys & IDENTITY_OWNERSHIP_KEYS
    if forbidden:
        raise ConfirmCardError(
            f"{action}: payload ⛔ 不得含身分或歸屬欄位 {sorted(forbidden)}"
        )
    allowed = {f.key for f in CLOSED_ACTION_FIELDS[action]} | CLOSED_ACTION_EXTRA_KEYS[action]
    unknown = keys - allowed
    if unknown:
        raise ConfirmCardError(f"{action}: payload 含未定義的欄位 {sorted(unknown)}")


def closed_values(action: Any, payload: Any) -> list:
    """封閉欄位表動作的**完整驗證**：回 `[(欄位, 正規化值), …]`（只含有給的欄位，表的順序）。

    卡（`_render_closed`）與 body（`closed_body`）都從這裡取值，⛔ 各自再驗一次。
    Raises: `ConfirmCardError`——鍵不在封閉表、缺必填、值不合、日期先後不對。
    """
    if action not in CLOSED_ACTION_FIELDS:
        raise ConfirmCardError(f"未知的封閉欄位表動作：{action!r}")
    if not isinstance(payload, Mapping):
        raise ConfirmCardError(f"{action}: payload 必須是物件")
    check_closed_keys(action, payload)
    out: list = []
    for f in CLOSED_ACTION_FIELDS[action]:
        value = payload.get(f.key)
        if not _given(value):
            if f.required:
                raise ConfirmCardError(f"{action}: payload 缺必填欄位 {f.key!r}")
            continue
        out.append((f.key, _closed_value(action, f, value)))
    present = {k for k, _ in out}
    for keys, _label in CLOSED_ACTION_ANY_OF[action]:
        if not present & set(keys):
            raise ConfirmCardError(f"{action}: payload 須至少給 {list(keys)} 其中之一")
    values = dict(out)
    # 跨欄規則（jgb2-req#20）：結束日必須晚於起始日。⛔ 不比今天（§3f 1c）。
    if action == CONTRACT_CREATE_ACTION and values["date_end"] <= values["date_start"]:
        raise ConfirmCardError(f"{action}: date_end 必須晚於 date_start")
    return out


def missing_required_labels(action: Any, payload: Any) -> list:
    """缺必填欄位的**中文標籤**清單（固定詞彙，⛔ 不含任何使用者值）；不是封閉表動作 ⇒ `[]`。

    §3f 2：`confirm.request` 缺必填時仍回 `INVALID_INPUT`、⛔ 出卡，但把這份清單
    交給模型追問。⚠️ 系統填的編號（`sys_id`）不算缺——它在出卡前由系統解析；
    名稱指稱鍵若有替代來源（`_REF_ALTERNATIVES`）有給也不算缺。
    """
    if action not in CLOSED_ACTION_FIELDS or not isinstance(payload, Mapping):
        return []
    alternatives = _REF_ALTERNATIVES.get(action, {})
    labels: list = []
    for f in CLOSED_ACTION_FIELDS[action]:
        if not f.required or f.kind == "sys_id" or _given(payload.get(f.key)):
            continue
        if any(_given(payload.get(alt)) for alt in alternatives.get(f.key, ())):
            continue
        labels.append(f.label)
    for keys, label in CLOSED_ACTION_ANY_OF[action]:
        if not any(_given(payload.get(k)) for k in keys):
            labels.append(label)
    return labels


def _closed_display(f: _ClosedField, value: Any) -> str:
    if f.kind == "enum":
        return (f.choices or {})[value]
    if f.kind == "date":
        return _fmt_date(value)
    if f.kind == "int" and f.unit:
        return f"{value:,} {f.unit}"
    return str(value)


def _render_closed(payload: Mapping[str, Any], today: Optional[date], *, action: str) -> str:
    # ⚠️ 簽章同其他 renderer（`today` 一律傳入）；本組動作的日期政策在閘一／閘二
    #    （`fields_before_today`），⛔ 不在 render 裡比今天。
    values = closed_values(action, payload)
    by_key = dict(values)
    fields = {f.key: f for f in CLOSED_ACTION_FIELDS[action]}
    rows: list[tuple[str, str]] = []
    ref_line = _CLOSED_REF_LINES.get(action)
    if ref_line is not None:
        name_key, id_key = ref_line
        # 卡上編號＝寫入編號（§3f 1d）：名稱與編號合印一行，使用者確認的就是這一筆。
        rows.append((fields[name_key].label, f"{by_key[name_key]}（編號 {by_key[id_key]}）"))
    for key, value in values:
        if ref_line is not None and key in ref_line:
            continue
        rows.append((fields[key].label, _closed_display(fields[key], value)))
    return _lines_to_card(_CLOSED_CARD_TITLES[action], rows)


def closed_body(action: Any, payload: Any) -> dict:
    """送給 jgb2（#19～#21）的**業務欄位** body：只含有給的、`in_body` 的欄位。

    ⚠️ 身分欄位（`role_id`／`user_id`）與冪等鍵 ⛔ 在這裡——由 `JGBSystemAPI._assistant_write`
    從 identity 帶入。日期轉 `YYYY-MM-DD`（接口 B 的形狀）。
    """
    fields = {f.key: f for f in CLOSED_ACTION_FIELDS[action]}
    body: dict = {}
    for key, value in closed_values(action, payload):
        f = fields[key]
        if not f.in_body:
            continue
        body[key] = value.isoformat() if f.kind == "date" else value
    return body


def _render_estate_create(payload: Mapping[str, Any], today: Optional[date]) -> str:
    return _render_closed(payload, today, action=ESTATE_CREATE_ACTION)


def _render_contract_create(payload: Mapping[str, Any], today: Optional[date]) -> str:
    return _render_closed(payload, today, action=CONTRACT_CREATE_ACTION)


def _render_manual_bill_create(payload: Mapping[str, Any], today: Optional[date]) -> str:
    return _render_closed(payload, today, action=MANUAL_BILL_CREATE_ACTION)


_RENDERERS: Final[dict] = {
    "bill_due_extend": _render_bill_due_extend,
    "repair_create": _render_repair_create,
    ESTATE_CREATE_ACTION: _render_estate_create,
    CONTRACT_CREATE_ACTION: _render_contract_create,
    MANUAL_BILL_CREATE_ACTION: _render_manual_bill_create,
}
assert set(_RENDERERS) == set(CONFIRM_ACTIONS)   # 值域與分支表必須同步（啟動期就炸）


def render(action: Any, payload: Any, *, today: Optional[date] = None) -> str:
    """`(action, payload[, today]) → 確認卡文字`。純函式、決定性、無副作用。

    Args:
        today: 驗算的**基準日**（`bill_due_extend` 的起算日＝原到期日與它較晚者）。
            **關鍵字參數**，由呼叫點以 `bills._today()` 取值傳入；⛔ 本檔不讀時鐘
            （見模組 docstring 的決定性硬約束），⛔ 也不從 `payload` 讀。
            缺省 `None` ⇒ 起算日就是原到期日＝舊行為逐字不變。

    Raises:
        ConfirmCardError: `action` 不在 `CONFIRM_ACTIONS` 內、payload 不是物件、
            payload 帶了 `RESERVED_PAYLOAD_KEYS` 裡的鍵、或缺欄位／型別不符／
            日期數字彼此矛盾。呼叫端一律翻成 `INVALID_INPUT`。
    """
    if action not in _RENDERERS:
        raise ConfirmCardError(f"未知的 action：{action!r}（值域 {list(CONFIRM_ACTIONS)}）")
    if not isinstance(payload, Mapping):
        raise ConfirmCardError(f"{action}: payload 必須是物件")
    # ⚠️ 保留鍵檢查在**所有 action 之前**（通用規則，⛔ 不是某一支的 if）：
    #    payload 是模型控制的，它 ⛔ 不得攜帶任何會改寫驗算基準的鍵。
    reserved = RESERVED_PAYLOAD_KEYS & set(payload)
    if reserved:
        raise ConfirmCardError(
            f"{action}: payload ⛔ 不得含保留鍵 {sorted(reserved)}"
        )
    return _RENDERERS[action](payload, today)


# ---------------------------------------------------------------------------
# 日期有效性（S1｜H1｜V3）：**一個時鐘（`bills._today()`）、三個呼叫點**
#
#   出卡          `tools/confirm.confirm_request`
#   兌現閘        `runtime._run_confirm_segment`（兌現分支）
#   寫入形狀驗算  `tools/action._validated_payload`
#
# 三處各自在**呼叫點**取 `bills._today()`，把它當關鍵字參數傳進本檔的純函式
# （`render(..., today=)`／`fields_before_today(..., today)`）。⛔ 本檔不 import
# 時鐘——那會讓本檔變成不決定性的，也會讓測試的 monkeypatch 失效。
#
# 為什麼判定在這一層：`render()` 只驗形狀與那條等式，三個數字彼此自洽的一組
# **過去**日期照樣出得了卡、兌現得了（H1 走查實測）。「不得早於今天」是這一欄的
# **語義**，語義屬於契約層，⛔ 不是某支工具的 if。
#
# ⚠️ 三個呼叫點的時鐘語義不完全相同，這是刻意的：出卡端是嚴格等式（只有一個
# `today`）；兌現端的 `_validated_payload` 允許等式對 `today` 或 `today − 1 天`
# 任一成立——token TTL 600 s 最多跨一個午夜，出卡日只可能是兌現日或前一天。
# 那是**驗算**的容忍度，⛔ 不是閘門的：`fields_before_today` 在兌現端仍以當日
# 新時鐘嚴格檢查（縱深）。
# ---------------------------------------------------------------------------

#: 站內幫手 S3（§3h 第 5 點；DSP-076）：收據日期的**卡外提示**——⛔ 不進卡文字、
#: ⛔ 不進 payload／雜湊；繳費期限一律由使用者另給。
RECEIPT_DATE_HINT_TEMPLATE: Final[str] = "收據日期：{date}（僅供參考，不會寫入帳單）"

#: 閘一（出卡前）回給**模型**的訊息（⛔ 無插值、⛔ 不舉例、⛔ 不回顯日期值）。
DATE_BEFORE_TODAY_TEXT: Final[str] = (
    "這個日期早於今天，不能以它出確認卡；請改問使用者要用今天以後的哪一天，再重新提出確認。"
)


def date_not_before_today(value: Any, today: date) -> bool:
    """`value`（`YYYYMMDD`）是不是**今天或以後**。純函式、⛔ 不讀時鐘。

    Raises:
        ConfirmCardError: `value` 不是 `YYYYMMDD` 形狀／不是合法日期
            （沿用 `_parse_date` 的唯一解析規則，⛔ 不另立第二套）。
            呼叫端 `fields_before_today` 把它折成「擋下」，見該函式。
    """
    return _parse_date(value, "date", "date_not_before_today") >= today


def fields_before_today(action: Any, payload: Any, today: date) -> list:
    """規格裡標了 `not_before_today` 而**實際早於今天**的欄位名（沒有 ⇒ `[]`）。

    ⚠️ **以屬性迭代 `CONFIRM_FIELD_ATTRS`**，⛔ 不看 action 叫什麼名字：表裡沒有
    這個 action、或它沒有被標記的欄位 ⇒ 空清單＝行為完全不變。

    ⚠️ **讀不出來的值一律算擋下**（fail-closed）：缺鍵、`None`、形狀不對的值都
    無法證明它「是今天或以後」，⛔ 不得因為解析不了就放行。呼叫本函式的兩道閘
    （閘一在 `render()` 之後、閘二在兩把雜湊比對之後）在正常路徑上都已經確認過
    形狀，所以這條路只在契約被破壞時才會走到——那時候擋下才是對的。
    """
    offenders: list = []
    for field, attrs in CONFIRM_FIELD_ATTRS.get(action, {}).items():
        if NOT_BEFORE_TODAY not in attrs:
            continue
        value = payload.get(field) if isinstance(payload, Mapping) else None
        try:
            ok = date_not_before_today(value, today)
        except ConfirmCardError:
            ok = False
        if not ok:
            offenders.append(field)
    return offenders


# ---------------------------------------------------------------------------
# 執行後的回覆句（W3 用；同樣決定性、同樣不經模型）
# ---------------------------------------------------------------------------

#: 工具回 `ok=False` 時的**誠實固定句**（Plan W3 逐字）。⛔ 不加「請稍後再試」
#: 之類的補語：我們並不知道重試會不會成功，多一句就是多一個沒有根據的承諾。
ACTION_FAILED_TEXT: Final[str] = "這筆操作目前無法執行"

#: 確認已失效（過期／已用掉／雜湊對不上／找不到）時的固定句。
#: ⚠️ 四種原因共用同一句，⛔ 不細分——細分等於把 token 表變成可探測的預言機
#: （與 `confirm.RedeemResult` 只有一個錯誤碼是同一條紀律）。
CONFIRMATION_REQUIRED_TEXT: Final[str] = "這筆確認已失效，請重新確認一次。"

#: 取消／改內容的短句。
CANCELLED_TEXT: Final[str] = "好的，這筆操作沒有送出。"

#: receipt 裡可以進 trace／回覆句的識別碼形狀（⛔ 只收這個形狀）。
#: receipt 是**下游系統**回來的資料，其中任何一個自由文字欄位都可能是原文；
#: 只放行這種形狀的短識別碼，才不會讓「把單號印給使用者」順手變成把下游訊息
#: 原樣透出去。
#: S2：`contract_id`／`estate_id` 接在**最後**——既有兩支的 receipt 一定先命中
#: `repair_id`／`bill_id`（順序不變 ⇒ 既有回覆句逐字不變）。
_RECEIPT_ID_KEYS: Final[Tuple[str, ...]] = (
    "receipt_id", "id", "repair_id", "bill_id", "contract_id", "estate_id",
)
_RECEIPT_ID_MAX = 64


def receipt_id_of(receipt: Any) -> str:
    """從 receipt 取一個**形狀安全**的識別碼；取不到 ⇒ `""`。

    形狀＝`[A-Za-z0-9_.:-]{1,64}`。⛔ 不回傳任何不符這個形狀的值（那多半是
    一段訊息而不是識別碼）。
    """
    if not isinstance(receipt, Mapping):
        return ""
    for key in _RECEIPT_ID_KEYS:
        value = receipt.get(key)
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            continue
        text = str(value).strip()
        if not text or len(text) > _RECEIPT_ID_MAX:
            continue
        if all(c.isalnum() or c in "_.:-" for c in text):
            return text
    return ""


def render_receipt(action: Any, payload: Any, receipt: Any) -> str:
    """執行成功後給使用者的句子。

    ⚠️ **句子的內容只從 `action`＋`payload` 導出**（那份 payload 正是使用者剛才
    在卡上確認過的），receipt 只貢獻一個經 `receipt_id_of` 過形狀的識別碼。
    ⛔ 不把 receipt 裡的自由文字拼進句子——下游回什麼我們並不控制，把它原樣
    透出去等於在確認鏈的末端開一個沒有人檢查的輸出口。
    ⚠️ 這裡刻意**不重跑** `render()` 的完整驗證：能走到這一步代表卡已經產出過、
    payload 也已經與表裡的 `payload_sha256` 對過帳；缺欄位時退回不帶細節的
    保底句，⛔ 不在回合末端丟例外把一次已經成功的寫入變成錯誤訊息。
    """
    ident = receipt_id_of(receipt)
    suffix = f"（單號 {ident}）" if ident else ""
    if action == "bill_due_extend" and isinstance(payload, Mapping):
        try:
            after = _parse_date(payload.get("date_expire_after"), "date_expire_after", "bill_due_extend")
            bill_id = _require_ref(payload, "bill_id", "bill_due_extend")
        except ConfirmCardError:
            return f"已完成這筆帳單到期日調整。{suffix}"
        return f"已將帳單 {bill_id} 的到期日延至 {_fmt_date(after)}。{suffix}"
    if action == "repair_create" and isinstance(payload, Mapping):
        try:
            estate = _require_text(payload, "estate_name", "repair_create")
        except ConfirmCardError:
            return f"已建立修繕單。{suffix}"
        return f"已為「{estate}」建立修繕單。{suffix}"
    # S2：三個封閉表動作——句子只取卡上已確認過的欄位（`closed_values` 驗過才用），
    # 驗不過退回不帶細節的保底句（同上：⛔ 不把已成功的寫入變成錯誤訊息）。
    if action in CLOSED_ACTION_FIELDS and isinstance(payload, Mapping):
        try:
            values = dict(closed_values(action, payload))
        except ConfirmCardError:
            values = {}
        if action == ESTATE_CREATE_ACTION:
            # 站內幫手 S5（S5-15，業主「印物件名稱，不印 id」）：物件只印名稱，⛔ 印單號。
            name = values.get("title")
            return f"已建立物件「{name}」。" if name else "已建立物件。"
        if action == CONTRACT_CREATE_ACTION:
            name = values.get("estate_name")
            return (f"已為「{name}」建立合約。{suffix}" if name else f"已建立合約。{suffix}")
        name = values.get("title")
        return (f"已建立手動帳單「{name}」。{suffix}" if name else f"已建立手動帳單。{suffix}")
    return f"已完成這筆操作。{suffix}"


__all__ = [
    "CONFIRM_ACTIONS",
    "PHOTO_PAYLOAD_KEYS",
    "RECEIPT_DATE_HINT_TEMPLATE",
    "REPAIR_PHOTOS_MAX",
    "repair_photos_of",
    "ESTATE_CREATE_ACTION",
    "CONTRACT_CREATE_ACTION",
    "MANUAL_BILL_CREATE_ACTION",
    "IDENTITY_OWNERSHIP_KEYS",
    "CLOSED_ACTION_FIELDS",
    "check_closed_keys",
    "closed_values",
    "closed_body",
    "missing_required_labels",
    "CONFIRM_FIELD_ATTRS",
    "CONFIRM_FIELD_ATTR_NAMES",
    "NOT_BEFORE_TODAY",
    "RESERVED_PAYLOAD_KEYS",
    "DATE_BEFORE_TODAY_TEXT",
    "date_not_before_today",
    "fields_before_today",
    "CARD_FOOTER",
    "EMPTY_DESCRIPTION_ZH",
    "ACTION_FAILED_TEXT",
    "CONFIRMATION_REQUIRED_TEXT",
    "CANCELLED_TEXT",
    "ConfirmCardError",
    "render",
    "render_receipt",
    "receipt_id_of",
]
