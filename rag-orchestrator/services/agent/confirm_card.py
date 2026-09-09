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
本 repo 的既有處置是「一律用自家真值對照，⛔ 不信任回應附的 mapping」
（見 `services/jgb_response_formatter.py` 的 `_EMERGENCY_STATUS_LABELS`）。
本檔的 `_EMERGENCY_ZH` 與那張表由
`tests/unit/agent/test_confirm_card_req.py` 逐鍵對帳，⛔ 兩邊不得分岔。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Final, Mapping, Tuple, Optional

#: `payload.action` 的**封閉值域**（DSP-038-2）。⛔ 不在此之外接受任何 action——
#: 沒有 render 分支的 action 等於「使用者看到的卡由誰決定」沒有答案。
#: 新增動作＝新增一個 render 分支＋一組欄位契約，⛔ 不是在這裡加一個字串。
CONFIRM_ACTIONS: Final[Tuple[str, ...]] = ("bill_due_extend", "repair_create")

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

    形狀取自 jgb2 的日期整數欄位慣例（`jgb_response_formatter.DATE_INT_KEYS`）。
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
    return _lines_to_card(
        "即將建立修繕單，請確認：",
        [
            ("物件", estate),
            ("修繕分類", category),
            ("急迫程度", _EMERGENCY_ZH[emergency]),
            ("問題描述", description.strip() or EMPTY_DESCRIPTION_ZH),
        ],
    )


_RENDERERS: Final[dict] = {
    "bill_due_extend": _render_bill_due_extend,
    "repair_create": _render_repair_create,
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
_RECEIPT_ID_KEYS: Final[Tuple[str, ...]] = ("receipt_id", "id", "repair_id", "bill_id")
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
    return f"已完成這筆操作。{suffix}"


__all__ = [
    "CONFIRM_ACTIONS",
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
