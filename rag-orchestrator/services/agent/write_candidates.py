"""A-2a 片（DSP-103）：寫入時「名稱對到多筆」的**程式候選集**——純函式與固定詞彙。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-a2a-write-candidates-20261020.md` §4.1～§4.6；
規則與凍結清單 `acceptance-a2a-write-candidates-20261020.md`（A2-R1～A2-R10）。

分工（DSP-091）：理解「使用者指的是哪一筆」可以由 AI（意圖判斷呼叫的 `pick_id`）；**選定是否成立、
選定的那筆紀錄、按鈕、下一步**一律由程式。本模組只放無副作用的判準：

- 封閉表 `CANDIDATE_TYPES`：動作 × 欄位 ⇒ 允許的候選型別（⛔ 表外組合一律不成立）；
- 候選集形狀（`agent_state["write_candidates"]`，`load_write_candidates` 驗形狀，比照 `load_draft`）：
  `{action, field, type, ids, has_more, name_fp, creator, picked}`。**⛔ 存名稱或列內容**——只存編號、
  該欄位名稱值的指紋與建立者；
- 入向機器值 `pick:<contract|estate|bill>:<id>`（`fullmatch`、⛔ NFKC、⛔ strip）；
- 給人看的固定句（只插筆數）、按鈕文字、trace 標記（只記型別與筆數）。
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Final, Iterable, List, Mapping, Optional, Tuple

from services.agent.confirm_card import CONTRACT_CREATE_ACTION, MANUAL_BILL_CREATE_ACTION
from services.agent.tools import jgb2 as _jgb2
from services.agent.write_forms import BILL_DUE_EXTEND_FORM, REPAIR_CREATE_FORM

#: 候選型別（封閉值域）＝ `pick:` 機器值的第二段。
TYPE_CONTRACT: Final[str] = "contract"
TYPE_ESTATE: Final[str] = "estate"
TYPE_BILL: Final[str] = "bill"
CANDIDATE_TYPE_DOMAIN: Final[Tuple[str, ...]] = (TYPE_CONTRACT, TYPE_ESTATE, TYPE_BILL)

#: 動作 × 欄位 ⇒ 允許的候選型別（計畫 §4.1、DSP-103 Q1「全部含帳單」）。
#: `manual_bill_create` 的 `estate_name` 有兩種：物件名稱多筆（型別 estate）、該物件有多份有效合約（型別 contract）。
CANDIDATE_TYPES: Final[Mapping[Tuple[str, str], frozenset]] = {
    (MANUAL_BILL_CREATE_ACTION, "contract_ref"): frozenset({TYPE_CONTRACT}),
    (MANUAL_BILL_CREATE_ACTION, "estate_name"): frozenset({TYPE_ESTATE, TYPE_CONTRACT}),
    (CONTRACT_CREATE_ACTION, "estate_name"): frozenset({TYPE_ESTATE}),
    (REPAIR_CREATE_FORM.action, "estate_name"): frozenset({TYPE_ESTATE}),
    (BILL_DUE_EXTEND_FORM.action, "estate_name"): frozenset({TYPE_BILL}),
}
CANDIDATE_ACTIONS: Final[frozenset] = frozenset(a for a, _f in CANDIDATE_TYPES)

#: 型別 ⇒ `jgb2` 投影 domain（給人看的清單與給意圖呼叫的資料段共用同一張投影表）。
DOMAIN_OF_TYPE: Final[Mapping[str, str]] = {
    TYPE_CONTRACT: "contracts", TYPE_ESTATE: "estates", TYPE_BILL: "bills",
}

#: 候選集保存同一次查詢的全部列，程式截 20（A2-R7 (a)）；畫面只列前 5 筆（`CANDIDATES_SHOWN_MAX`，
#: ＝ `runtime.CONFIRM_CANDIDATES_MAX`、`JGB2_CANDIDATE_CAP` 預設值）。
WRITE_CANDIDATES_MAX: Final[int] = 20
CANDIDATES_SHOWN_MAX: Final[int] = 5

#: 編號的合法形狀（候選集 `ids`／`picked` 與 `pick:` 第三段同一條）。
CANDIDATE_ID_RE: Final = re.compile(r"[A-Za-z0-9_-]{1,32}")
#: 入向機器值：`fullmatch`（⛔ NFKC、⛔ strip——前後空白、全形冒號一律不是機器值，照一般文字進模型）。
PICK_VALUE_RE: Final = re.compile(r"pick:(contract|estate|bill):([A-Za-z0-9_-]{1,32})")
PICK_VALUE_PREFIX: Final[str] = "pick:"

#: 候選集的封閉鍵（`load_write_candidates`）。
CANDIDATE_SET_KEYS: Final[frozenset] = frozenset(
    {"action", "field", "type", "ids", "has_more", "name_fp", "creator", "picked"})
_NAME_FP_RE: Final = re.compile(r"[0-9a-f]{32}")

# ── 固定句（只插筆數；⛔ 使用者值、⛔ 查詢字串、⛔ 給模型的提示句）────────────────────────────
#: 合約／物件兩句的 `{count}` 只會是 `candidate_count_text` 的產出（「6 份」「20 份以上」）。
CANDIDATES_CONTRACT_TEXT: Final[str] = "這個名稱對到 {count}合約，請點選要用的那一份。"
CANDIDATES_ESTATE_TEXT: Final[str] = "這個名稱對到 {count}物件，請點選要用的那一個。"
#: 帳單沿用現行句（`runtime.CONFIRM_CANDIDATES_TEXT` 同字）。
CANDIDATES_BILL_TEXT: Final[str] = "這戶對到不只一張帳單，請點選要處理的那一張。"
#: 多於畫面筆數或上游還有下一頁（A2-R7 (a)(d)；三處統一同一句）。
CANDIDATES_MORE_TEXT: Final[str] = "還有其他筆，不在其中請講編號。"
#: 按鈕／機器值不成立（A2-R3）。⛔ 插值。
CANDIDATE_PICK_INVALID_TEXT: Final[str] = "這個選項已經失效了。要處理哪一筆，請重新告訴我。"
#: dialog 只寫程式摘要（P4-1；⛔ 清單文字、⛔ `pick:` 原值）。
CANDIDATES_DIALOG_SUMMARY: Final[str] = "已列出 {n} 筆候選{noun}，請使用者選一筆"
CANDIDATE_PICK_DIALOG_USER: Final[str] = "（使用者點選了候選清單中的一筆）"

_NOUN_OF_TYPE: Final[Mapping[str, str]] = {
    TYPE_CONTRACT: "合約", TYPE_ESTATE: "物件", TYPE_BILL: "帳單",
}
_UNIT_OF_TYPE: Final[Mapping[str, str]] = {
    TYPE_CONTRACT: "份", TYPE_ESTATE: "個", TYPE_BILL: "張",
}

# ── trace 標記（只記型別與筆數）──────────────────────────────────────────────────────────
V_CANDIDATES_SHOWN_PREFIX: Final[str] = "write_candidates_shown:"
V_CANDIDATE_PICK_BUTTON: Final[str] = "write_candidate_pick:button"
V_CANDIDATE_PICK_TYPED: Final[str] = "write_candidate_pick:typed"
V_CANDIDATE_PICK_INVALID: Final[str] = "write_candidate_pick_invalid"
V_CANDIDATE_REASK: Final[str] = "write_candidate_reask"
V_CANDIDATES_SHAPE_INVALID: Final[str] = "write_candidates_shape_invalid"
#: 修正 2（verifier F1）：卡後更正時「綁定卡帶著的選定」帶不帶回的程式判定（⛔ 記編號）。
#: `same`＝AI 恰回 `record_rechoice=same`、帶回；`declined`＝其他前提都成立、但 AI 沒恰回 `same` ⇒ 不帶。
V_CANDIDATE_CARRY_SAME: Final[str] = "write_candidate_carry:same"
V_CANDIDATE_CARRY_DECLINED: Final[str] = "write_candidate_carry:declined"
#: 修正 2：AI 恰回 `record_rechoice=other`（使用者要改用另一筆）⇒ 程式作廢綁定卡、依草稿名稱重新解析。
V_CANDIDATE_RECHOICE: Final[str] = "write_candidate_rechoice"


def shown_marker(cand_type: str, n: int) -> str:
    return f"{V_CANDIDATES_SHOWN_PREFIX}{cand_type}:{int(n)}"


def name_fp(value: Any) -> str:
    """該欄位**名稱值**的指紋（sha256 前 32 位）。缺值／非字串一律以空字串計（⛔ 存原值）。"""
    text = value.strip() if isinstance(value, str) else ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def allowed(action: Any, field: Any, cand_type: Any) -> bool:
    """`(action, field, type)` 在封閉表內。"""
    if not isinstance(action, str) or not isinstance(field, str) or not isinstance(cand_type, str):
        return False
    return cand_type in CANDIDATE_TYPES.get((action, field), frozenset())


def candidate_id(value: Any) -> Optional[str]:
    """列上的編號 → `str(id).strip()`；不合 `CANDIDATE_ID_RE`（含 bool、None）⇒ `None`。"""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text if CANDIDATE_ID_RE.fullmatch(text) else None


def parse_pick_value(message: Any) -> Optional[Tuple[str, str]]:
    """`pick:<型別>:<編號>` ⇒ `(型別, 編號)`；其餘（含前後空白、全形冒號）⇒ `None`。"""
    if not isinstance(message, str):
        return None
    m = PICK_VALUE_RE.fullmatch(message)
    return (m.group(1), m.group(2)) if m else None


def new_candidate_set(*, action: str, field: str, cand_type: str, ids: Iterable[Any],
                      has_more: bool, field_value: Any, creator: Mapping[str, Any]) -> Optional[dict]:
    """組一份候選集（程式出口的唯一建構點）；組不出合法形狀 ⇒ `None`（呼叫端不寫、不列）。"""
    if not allowed(action, field, cand_type) or not isinstance(creator, Mapping):
        return None
    kept: List[str] = []
    for raw in ids:
        cid = candidate_id(raw)
        if cid is not None and cid not in kept:
            kept.append(cid)
    total = len(kept)
    kept = kept[:WRITE_CANDIDATES_MAX]
    if not kept:
        return None
    value = {
        "action": action, "field": field, "type": cand_type, "ids": kept,
        "has_more": bool(has_more) or total > WRITE_CANDIDATES_MAX,
        "name_fp": name_fp(field_value),
        "creator": {"user_id": creator.get("user_id"), "role_id": creator.get("role_id")},
        "picked": None,
    }
    loaded, _invalid = load_write_candidates(value)
    return loaded


def load_write_candidates(raw: Any) -> Tuple[Optional[dict], bool]:
    """讀回候選集（**一律視為不可信**，比照 `write_forms.load_draft`）⇒ `(候選集或 None, 形狀不合)`。

    封閉鍵、`(action, field, type)` 在封閉表內、`ids` 為 1～20 個合法且不重複的編號字串、`has_more`
    為布林、`name_fp` 為 32 位十六進位、`creator` 為只含 `user_id`／`role_id` 的物件、`picked` 為
    `None` 或合法編號。缺值（`None`）⇒ `(None, False)`；其餘不合 ⇒ `(None, True)`。"""
    if raw is None:
        return None, False
    if not isinstance(raw, dict) or set(raw) != CANDIDATE_SET_KEYS:
        return None, True
    if not allowed(raw.get("action"), raw.get("field"), raw.get("type")):
        return None, True
    ids = raw.get("ids")
    if (not isinstance(ids, list) or not ids or len(ids) > WRITE_CANDIDATES_MAX
            or len(set(i for i in ids if isinstance(i, str))) != len(ids)
            or not all(isinstance(i, str) and CANDIDATE_ID_RE.fullmatch(i) for i in ids)):
        return None, True
    if not isinstance(raw.get("has_more"), bool):
        return None, True
    fp = raw.get("name_fp")
    if not isinstance(fp, str) or not _NAME_FP_RE.fullmatch(fp):
        return None, True
    creator = raw.get("creator")
    if not isinstance(creator, dict) or set(creator) != {"user_id", "role_id"}:
        return None, True
    picked = raw.get("picked")
    if picked is not None and not (isinstance(picked, str) and CANDIDATE_ID_RE.fullmatch(picked)):
        return None, True
    return {
        "action": raw["action"], "field": raw["field"], "type": raw["type"], "ids": list(ids),
        "has_more": raw["has_more"], "name_fp": fp,
        "creator": {"user_id": creator["user_id"], "role_id": creator["role_id"]},
        "picked": picked,
    }, False


def program_pick_of(cands: Mapping[str, Any], picked: str) -> dict:
    """程式專用選定通道的形狀（計畫 §4.5）：`{action, field, type, id}`，由候選集組出。"""
    return {"action": cands["action"], "field": cands["field"], "type": cands["type"],
            "id": str(picked)}


#: 修正 1（A2-R5「回原流程」「其他欄位值保留」）：出卡後候選集照清（A2-R6 (a)），由 `program_pick` 出的那張卡
#: 在**待確認筆**（`agent_state["pending_confirm"][pid]`）帶著選定，卡後更正、程式依草稿重出卡時由 runtime
#: 讀回、經同一個 `program_pick` 通道帶回。⛔ 存進草稿、⛔ 進卡文字以外的對外位置、⛔ 進 trace。
CARD_PICK_KEY: Final[str] = "candidate_pick"
CARD_PICK_KEYS: Final[frozenset] = frozenset({"action", "field", "type", "id", "name_fp", "creator"})


def card_pick_of(program_pick: Any, *, name_fp: Any, creator: Any) -> Optional[dict]:
    """出卡當下的 `program_pick`＋該欄位名稱指紋＋建立者 ⇒ 待確認筆要存的選定；組不出合法形狀 ⇒ `None`（不存）。"""
    if not isinstance(program_pick, Mapping):
        return None
    action = program_pick.get("action")
    if valid_program_pick(program_pick, action) is None:
        return None
    if not isinstance(creator, Mapping):
        return None
    value = {
        "action": action, "field": program_pick["field"], "type": program_pick["type"],
        "id": program_pick["id"], "name_fp": name_fp,
        "creator": {"user_id": creator.get("user_id"), "role_id": creator.get("role_id")},
    }
    return load_card_pick(value, action=action)


def load_card_pick(raw: Any, *, action: Any) -> Optional[dict]:
    """讀回待確認筆存的選定（**一律視為不可信**）：封閉六鍵、`{action, field, type, id}` 過
    `valid_program_pick`（動作＝`action`、封閉表內、編號合形狀）、`name_fp` 為 32 位十六進位、`creator`
    為只含 `user_id`／`role_id` 的物件；任一不合 ⇒ `None`（⛔ 拋例外、⛔ 半信）。
    指紋與建立者「等不等於本回合」由呼叫端比對。"""
    if not isinstance(raw, dict) or set(raw) != CARD_PICK_KEYS:
        return None
    pick = {k: raw[k] for k in ("action", "field", "type", "id")}
    if valid_program_pick(pick, action) is None:
        return None
    fp = raw.get("name_fp")
    if not isinstance(fp, str) or not _NAME_FP_RE.fullmatch(fp):
        return None
    creator = raw.get("creator")
    if not isinstance(creator, dict) or set(creator) != {"user_id", "role_id"}:
        return None
    return {**pick, "name_fp": fp,
            "creator": {"user_id": creator["user_id"], "role_id": creator["role_id"]}}


def valid_program_pick(program_pick: Any, action: Any) -> Optional[Tuple[str, str, str]]:
    """`confirm.request` 收到的 `program_pick` ⇒ `(field, type, id)`；形狀不合、動作不符、
    `(action, field, type)` 不在封閉表、編號不合形狀 ⇒ `None`（照名稱解析，⛔ 半信）。"""
    if not isinstance(program_pick, Mapping) or set(program_pick) != {"action", "field", "type", "id"}:
        return None
    if program_pick.get("action") != action:
        return None
    field, cand_type = program_pick.get("field"), program_pick.get("type")
    if not allowed(action, field, cand_type):
        return None
    cid = program_pick.get("id")
    if not isinstance(cid, str) or not CANDIDATE_ID_RE.fullmatch(cid):
        return None
    return field, cand_type, cid


def candidate_count_text(cand_type: str, n: int, has_more: bool) -> str:
    unit = _UNIT_OF_TYPE.get(cand_type, "筆")
    return f"{int(n)} {unit}以上" if has_more else f"{int(n)} {unit}"


def candidates_lead_text(cand_type: str, n: int, has_more: bool) -> str:
    """三句固定句之一（只插筆數）。"""
    if cand_type == TYPE_BILL:
        return CANDIDATES_BILL_TEXT
    template = CANDIDATES_CONTRACT_TEXT if cand_type == TYPE_CONTRACT else CANDIDATES_ESTATE_TEXT
    return template.format(count=candidate_count_text(cand_type, n, has_more))


def dialog_summary(cand_type: str, n: int) -> str:
    return CANDIDATES_DIALOG_SUMMARY.format(n=int(n), noun=_NOUN_OF_TYPE.get(cand_type, ""))


def button_label(cand_type: str, row: Mapping[str, Any]) -> str:
    """候選按鈕文字：編號＋區分用的一個欄位（合約：到期日；物件：狀態；帳單：到期日）。
    ⛔ 放名稱——同名紀錄的名稱都一樣，細節在清單文字裡。"""
    label = f"編號 {row.get('id')}"
    if cand_type == TYPE_CONTRACT and row.get("date_end"):
        label += f"｜到期 {_jgb2._contract_format_date(row.get('date_end'))}"
    elif cand_type == TYPE_ESTATE and row.get("status") is not None:
        label += f"｜{_jgb2.estate_status_zh(row.get('status'))}"
    elif cand_type == TYPE_BILL and row.get("date_expire"):
        label += f"｜到期 {_jgb2._bill_format_date(row.get('date_expire'))}"
    return label


def user_list_text(cand_type: str, rows: List[Mapping[str, Any]]) -> str:
    """給人看的清單（`jgb2.candidates_text_for_user`，同一張投影表）。"""
    return _jgb2.candidates_text_for_user(DOMAIN_OF_TYPE[cand_type], list(rows))


def data_piece_text(cand_type: str, rows: List[Mapping[str, Any]]) -> str:
    """給意圖判斷呼叫的資料段內文：每列只放投影欄、逐列過 `sanitize_data_piece`（呼叫端再以 nonce 包住）。"""
    from services.agent.completed_actions import sanitize_data_piece

    projector = _jgb2._ROW_PROJECTORS[DOMAIN_OF_TYPE[cand_type]]
    return "\n".join(sanitize_data_piece(projector(dict(r))) for r in rows)


def minimize_row(cand_type: str, row: Mapping[str, Any]) -> dict:
    """候選列只留投影與按鈕要用的鍵（最小揭露；合約列另有承租人電話／Email 等，⛔ 帶出）。
    帳單列沿用現行（投影要讀金額與狀態的多個來源鍵，`_bill_candidates_result` 原樣）。"""
    if cand_type == TYPE_CONTRACT:
        keep = ("id", "title", "date_end", "estate_id", "is_history")
    elif cand_type == TYPE_ESTATE:
        keep = ("id", "title", "status")
    else:
        return dict(row)
    return {k: row.get(k) for k in keep if k in row}


__all__ = [
    "TYPE_CONTRACT", "TYPE_ESTATE", "TYPE_BILL", "CANDIDATE_TYPE_DOMAIN", "CANDIDATE_TYPES",
    "CANDIDATE_ACTIONS", "DOMAIN_OF_TYPE", "WRITE_CANDIDATES_MAX", "CANDIDATES_SHOWN_MAX",
    "CANDIDATE_ID_RE", "PICK_VALUE_RE", "PICK_VALUE_PREFIX", "CANDIDATE_SET_KEYS",
    "CANDIDATES_CONTRACT_TEXT", "CANDIDATES_ESTATE_TEXT", "CANDIDATES_BILL_TEXT",
    "CANDIDATES_MORE_TEXT", "CANDIDATE_PICK_INVALID_TEXT", "CANDIDATES_DIALOG_SUMMARY",
    "CANDIDATE_PICK_DIALOG_USER", "V_CANDIDATES_SHOWN_PREFIX", "V_CANDIDATE_PICK_BUTTON",
    "V_CANDIDATE_PICK_TYPED", "V_CANDIDATE_PICK_INVALID", "V_CANDIDATE_REASK",
    "V_CANDIDATES_SHAPE_INVALID", "V_CANDIDATE_CARRY_SAME", "V_CANDIDATE_CARRY_DECLINED",
    "V_CANDIDATE_RECHOICE", "shown_marker", "name_fp", "allowed", "candidate_id",
    "parse_pick_value", "new_candidate_set", "load_write_candidates", "program_pick_of",
    "valid_program_pick", "CARD_PICK_KEY", "CARD_PICK_KEYS", "card_pick_of", "load_card_pick",
    "candidate_count_text", "candidates_lead_text", "dialog_summary",
    "button_label", "user_list_text", "data_piece_text", "minimize_row",
]
