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
  `date_expire_before + days`；⛔ 不在缺值時自己算出來當成使用者確認過的事實。

## `emergency_status` 是已知地雷（⛔ 不可望文生義）
`1＝非緊急、2＝緊急`（jgb2 DB 真值）。jgb2 對外 `mapping` 曾把它標反，
本 repo 的既有處置是「一律用自家真值對照，⛔ 不信任回應附的 mapping」
（見 `services/jgb_response_formatter.py` 的 `_EMERGENCY_STATUS_LABELS`）。
本檔的 `_EMERGENCY_ZH` 與那張表由
`tests/unit/agent/test_confirm_card_req.py` 逐鍵對帳，⛔ 兩邊不得分岔。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Final, Mapping, Tuple

#: `payload.action` 的**封閉值域**（DSP-038-2）。⛔ 不在此之外接受任何 action——
#: 沒有 render 分支的 action 等於「使用者看到的卡由誰決定」沒有答案。
#: 新增動作＝新增一個 render 分支＋一組欄位契約，⛔ 不是在這裡加一個字串。
CONFIRM_ACTIONS: Final[Tuple[str, ...]] = ("bill_due_extend", "repair_create")

#: `emergency_status` 的中文（jgb2 DB 真值；見模組 docstring 的地雷說明）。
_EMERGENCY_ZH: Final[dict[int, str]] = {1: "非緊急", 2: "緊急"}

#: 描述留空時卡上顯示的字（⛔ 不是推測出來的內容，是「這一欄使用者沒填」的明示）。
EMPTY_DESCRIPTION_ZH: Final[str] = "（未填寫）"

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


def _render_bill_due_extend(payload: Mapping[str, Any]) -> str:
    action = "bill_due_extend"
    bill_id = _require_ref(payload, "bill_id", action)
    before = _parse_date(_require(payload, "date_expire_before", action),
                         "date_expire_before", action)
    days = _require_days(payload, "days", action)
    after = _parse_date(_require(payload, "date_expire_after", action),
                        "date_expire_after", action)
    # ⚠️ **驗算而不是代算**（見模組 docstring「不推測」）：新到期日必須是呼叫端
    #    明給的那一個，且必須等於 原到期 + 天數。三個數字彼此矛盾時 ⛔ 不挑一個
    #    來印——那等於替使用者決定他同意的是哪一個。
    if before + timedelta(days=days) != after:
        raise ConfirmCardError(
            f"{action}: date_expire_before + days 與 date_expire_after 不一致"
        )
    return _lines_to_card(
        "即將調整帳單到期日，請確認：",
        [
            ("帳單編號", bill_id),
            ("原到期日", _fmt_date(before)),
            ("延後天數", f"{days} 天"),
            ("新到期日", _fmt_date(after)),
        ],
    )


def _render_repair_create(payload: Mapping[str, Any]) -> str:
    action = "repair_create"
    estate = _require_text(payload, "estate_name", action)
    # 分類**允許父節點**（line-bot 線③：分類樹涵蓋不到時退回大類，
    # ⛔ 不編一個不存在的葉節點）——本檔只要求它是非空字串，
    # ⛔ 不在此驗它是不是葉節點。
    category = _require_text(payload, "category_name", action)
    # 描述**允許空字串**，但鍵必須存在：「沒填」與「忘了帶這個欄位」是兩件事，
    # 後者代表呼叫端的 payload 形狀有問題，⛔ 不得靜默當成前者。
    description = _require(payload, "description", action)
    if not isinstance(description, str):
        raise ConfirmCardError(f"{action}: 欄位 'description' 必須是字串（可為空字串）")
    emergency = _require(payload, "emergency_status", action)
    if isinstance(emergency, bool) or emergency not in _EMERGENCY_ZH:
        raise ConfirmCardError(
            "repair_create: 欄位 'emergency_status' 必須是 1（非緊急）或 2（緊急）"
        )
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


def render(action: Any, payload: Any) -> str:
    """`(action, payload) → 確認卡文字`。純函式、決定性、無副作用。

    Raises:
        ConfirmCardError: `action` 不在 `CONFIRM_ACTIONS` 內，或 payload 缺欄位／
            型別不符／三個日期數字彼此矛盾。呼叫端一律翻成 `INVALID_INPUT`。
    """
    if action not in _RENDERERS:
        raise ConfirmCardError(f"未知的 action：{action!r}（值域 {list(CONFIRM_ACTIONS)}）")
    if not isinstance(payload, Mapping):
        raise ConfirmCardError(f"{action}: payload 必須是物件")
    return _RENDERERS[action](payload)


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
