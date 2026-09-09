"""`agent_state["completed_actions"]`——會話記憶：已完成動作的可引用摘要
（S2｜Plan `inputs/plan-walkthrough-fixes-20260909.md` §3、H3）。

## 為什麼這是程式寫、不是模型寫
H3 走查實測：建單成功之後下一句問「剛剛那張單號多少」答不出來——`receipt`
只進了 `trace`／`outcome.ref`，沒有進任何模型看得到的地方。這裡把它變成
程式產出的**封閉值**記憶行，模型只能引用、不能改寫（同影像事實資料段的
紀律：可引用資料段一律 `ToolResult(provenance=[...])`，⛔ 不進 dialog 歷史、
⛔ 讓模型自己填一個 `estate_name` 之類的自由字串）。

## 值域紀律
元素形狀＝`{action, ref_type, ref_id, estate_id, at_iso}`——全部封閉值
（action／ref_type 是既有的封閉列舉，`ref_id` 是 `outcome.ref` 已經過形狀驗證
的識別碼，`estate_id` 取不到就是 `None`，`at_iso` 是呼叫端的時鐘）。
`due_date` 是選填的第六欄——只有 `_DUE_DATE_RECEIPT_KEY` 表裡列出的 action，
才會從 receipt 多拿一個同樣封閉的日期值進來（見 `record_completed_action`）；
⛔ 這是唯一容許以 action 名分支的地方，而且只決定「要不要多存一個日期」，
不決定「這個動作算不算完成」。

## 去重與上限
依 `(ref_type, ref_id)` 去重：同一筆已經在記憶裡 ⇒ **完全不動**（不覆蓋、
不搬到尾端、不更新 `at_iso`）——重送同一個 `pending_id`（R4.3）不該讓「已
完成」這件事看起來像剛剛才發生。上限 5、FIFO（超過就砍最舊的）。

## 為什麼沒有獨立 TTL
記憶隨 `agent_state` 一起清（會話重新開始／`state_store.is_expired` 判過期
後呼叫端本就整包不續用舊 state）——另立一個 TTL 只會多一種「兩個時鐘算出
不同答案」的可能。
"""
from __future__ import annotations

import re
from typing import Any, Optional

from services.agent.verifier import _UNIT_MARKER_RE

#: `agent_state` 底下的鍵。
COMPLETED_ACTIONS_KEY = "completed_actions"

#: FIFO 上限。
MAX_COMPLETED_ACTIONS = 5

#: `ref_type` → 卡片標籤的封閉映射；沒有列在表裡的 `ref_type` ⇒ 那一筆
#: 不渲染成一行（⛔ 印一句「未知類型」用猜的）。
_REF_TYPE_LABEL: dict[str, str] = {
    "repair": "修繕單",
    "bill": "帳單",
}

#: 只有列在這張表的 action，記錄時才會從 receipt 多拿一個封閉值（到期日）
#: 進來（鍵＝`services.agent.tools.action` 那支動作的 receipt 欄位名，
#: 見 `jgb2.action.bill_due_extend` 的 `_receipt({..., "after": ...})`）。
_DUE_DATE_RECEIPT_KEY: dict[str, str] = {
    "bill_due_extend": "after",
}


def record_completed_action(
    agent_state: dict,
    *,
    action: Optional[str],
    ref_type: Optional[str],
    ref_id: Optional[str],
    estate_id: Optional[str],
    at_iso: str,
    receipt: Optional[dict] = None,
    estate_name: Optional[str] = None,
) -> None:
    """把一次成功兌現寫進 `agent_state[COMPLETED_ACTIONS_KEY]`。

    ⚠️ 呼叫端（`runtime._finish_confirm_turn`）必須先確認
    `outcome.state == "confirmed"` 且 `outcome.ref` 存在——本函式不重驗這件事，
    只管記憶行本身的形狀：去重＋上限＋封閉值。`ref_type`／`ref_id` 缺一 ⇒
    不寫（沒有可引用的識別碼，寫進去也組不出一行）。

    `estate_name`（T4｜Plan `plan-walkthrough-fixes-batch2-20260909.md` §5）：
    呼叫端只能從封閉來源帶進來（待確認 payload 的物件名稱欄位、或釘住範圍時
    的清單標題）——⛔ 不得是模型自由文字。這裡用既有的 `_sanitize_piece`
    剝一次（同記憶行其餘欄位的紀律），剝完是空字串就當沒有這個值。
    """
    if not ref_type or not ref_id:
        return
    items = agent_state.get(COMPLETED_ACTIONS_KEY)
    items = list(items) if isinstance(items, list) else []
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("ref_type") == ref_type
            and item.get("ref_id") == ref_id
        ):
            return  # 已記過這一筆——⛔ 不覆蓋、不搬到尾端（R4.3 重送語意）
    entry: dict[str, Any] = {
        "action": action,
        "ref_type": ref_type,
        "ref_id": ref_id,
        "estate_id": estate_id,
        "at_iso": at_iso,
    }
    if isinstance(estate_name, str):
        cleaned_name = _sanitize_piece(estate_name).strip()
        if cleaned_name:
            entry["estate_name"] = cleaned_name
    date_key = _DUE_DATE_RECEIPT_KEY.get(action or "")
    if date_key and isinstance(receipt, dict):
        value = receipt.get(date_key)
        if isinstance(value, str) and value:
            entry["due_date"] = value
    items.append(entry)
    if len(items) > MAX_COMPLETED_ACTIONS:
        items = items[-MAX_COMPLETED_ACTIONS:]
    agent_state[COMPLETED_ACTIONS_KEY] = items


def _slash_date(value: str) -> str:
    """`YYYY-MM-DD` 或 `YYYYMMDD` → `YYYY/MM/DD`；認不出的形狀就原樣印出
    （⛔ 不猜、不拋例外——這一步只是排版，不是驗證）。
    """
    digits = str(value).strip().replace("-", "")
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[0:4]}/{digits[4:6]}/{digits[6:8]}"
    return str(value).strip()


#: T1（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §2）：
#: **一律剝除**的不可見字元，逐類列舉（⛔ 不用「非可列印就砍」那種開放判定——
#: 那會連中文標點與表情符號一起吃掉）：
#:   - C0 控制字元 `U+0000–U+001F`（換行三種在下方先換成空白，故此處不含）
#:     與 DEL `U+007F`、C1 控制字元 `U+0080–U+009F`；
#:   - 行／段分隔 `U+2028`／`U+2029`（它們在很多渲染器裡等同換行）；
#:   - 零寬 `U+200B–U+200F`、`U+FEFF`（零寬字元可以把一個字串切成模型看不見
#:     的兩半，繞過任何以字面比對為基礎的檢查）；
#:   - 雙向控制 `U+202A–U+202E`、`U+2066–U+2069`（視覺上可以把一行字反轉，
#:     讓使用者看到的與資料段實際內容不同）。
_INVISIBLE_CHARS_RE = re.compile(
    "["
    "\u0000-\u0008\u000b-\u001f\u007f-\u009f"
    "\u2028\u2029"
    "\u200b-\u200f\ufeff"
    "\u202a-\u202e\u2066-\u2069"
    "]"
)


def sanitize_data_piece(text: Any) -> str:
    """把一段**程式產的**可引用文字正規化成單行、無不可見字元、無假標記的字串。

    T1 起這是「程式資料段」的共用正規化落點（記憶行與呼叫端進場句 `context`
    都走它），⛔ 不各寫一份：兩處各寫一份的失敗方向是「其中一處忘了剝某一類」，
    而那一處剛好是新開的外部輸入面。

    逐類處理，⛔ 不做開放語義的「看起來怪就砍」：
      1. 換行三種（CR LF／LF／CR）→ **空白**（沿用 F7c 既有行為：記憶行
         的既有測試斷言的是「結果不含換行」，不是「換行處的字被黏起來」）；
      2. `_INVISIBLE_CHARS_RE` 逐類剝除（見該常數的說明）；
      3. `_UNIT_MARKER_RE` 同形字串剝除——程式產的資料段 ⛔ 不得夾帶一個會被
         解析側誤判成真標記的子字串（真標記的不可偽造性靠 nonce，但「長得像」
         本身就足以讓模型抄一個解析不到的東西回來）。

    非字串（`None`／數字）一律回空字串：呼叫端據此判斷「沒有東西可注入」，
    ⛔ 不 raise 進熱路徑。
    """
    if not isinstance(text, str):
        return ""
    cleaned = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    cleaned = _INVISIBLE_CHARS_RE.sub("", cleaned)
    return _UNIT_MARKER_RE.sub("", cleaned)


#: F7c 時期的舊名。⛔ 不刪：`completed_actions` 既有測試與呼叫點都用它，
#: 而 T1 只是把同一支函式擴充成共用版本，不是換一支新語義。
_sanitize_piece = sanitize_data_piece


def completed_actions_line(items: Any, scope_estate_id: Optional[str]) -> str:
    """決定性、單行、⛔ 不含換行——完成動作記憶行（Plan §3 文字格式）。

    有釘住範圍（`scope_estate_id` 非 `None`）時**只放同戶的項目**（F8）：
    `estate_id` 對不上就跳過、`estate_id` 是 `None`（算不出物件）也跳過——
    有範圍時「算不出物件」不能被當成「這一筆在範圍內」。
    沒有可渲染的項目 ⇒ 回空字串，呼叫端據此判斷要不要注入這一段。
    """
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        ref_type = item.get("ref_type")
        ref_id = item.get("ref_id")
        label = _REF_TYPE_LABEL.get(ref_type)
        if not label or not ref_id:
            continue
        estate_id = item.get("estate_id")
        if scope_estate_id is not None and estate_id != scope_estate_id:
            continue
        due_date = item.get("due_date")
        if isinstance(due_date, str) and due_date:
            piece = f"{label} {ref_id} 到期日已延至 {_slash_date(due_date)}"
        else:
            # 只講使用者看得到的編號；`estate_id` 是內部值，只用於範圍過濾，
            # ⛔ 不進使用者面文字（2026-09-09 verifier P3：「物件 67652」外洩）。
            piece = f"{label} {ref_id}"
        estate_name = item.get("estate_name")
        if isinstance(estate_name, str) and estate_name:
            # 物件「名稱」允許出現在使用者面文字；`estate_id`（內部值）不允許——
            # 兩者是不同的東西，寫入時已用 `_sanitize_piece` 剝過一次。
            piece = f"{piece}（{estate_name}）"
        parts.append(_sanitize_piece(piece))
    if not parts:
        return ""
    return "本對話已完成的動作：" + "／".join(parts)


__all__ = [
    "COMPLETED_ACTIONS_KEY",
    "MAX_COMPLETED_ACTIONS",
    "record_completed_action",
    "completed_actions_line",
    "sanitize_data_piece",
]
