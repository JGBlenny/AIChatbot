"""A-2a 片（DSP-103）：寫入時「名稱對到多筆」的**程式候選集**——純函式與固定詞彙。

計畫與凍結清單：`.kiro/specs/agentic-mcp-orchestration/plan-a2a-write-candidates-20261020.md`、
`acceptance-a2a-write-candidates-20261020.md`。

分工（DSP-091）：理解「使用者指的是哪一筆」可以由 AI（意圖判斷呼叫的 `pick_id`）；**選定是否成立、
選定的那筆紀錄、按鈕、下一步**一律由程式。本模組只放無副作用的判準：

- 封閉表 `CANDIDATE_TYPES`：動作 × 欄位 ⇒ 允許的候選型別（⛔ 表外組合一律不成立）；
- 候選集形狀（`agent_state["write_candidates"]`，`load_write_candidates` 驗形狀，比照 `load_draft`）：
  `{action, field, type, ids, has_more, name_fp, creator, picked}`。**⛔ 存名稱或列內容**——只存編號、
  該欄位名稱值的指紋與建立者；
- 入向機器值 `pick:<contract|estate|bill>:<id>`（`fullmatch`、⛔ NFKC、⛔ strip）；
- 給人看的固定句（只插筆數，或系統正名與編號）、按鈕文字、trace 標記（只記型別與筆數）。

選定後、出卡前仍可改選——選定與否由程式依 AI 的
`pick_id`（驗證在 `ids` 內）、整句只打候選集內編號、本回合講出的候選集外名稱決定；只撤回或改選目標被退回
⇒ 候選集進「已撤回」（`withdrawn: True`、`picked` 為 `None`，`ids` 與名稱指紋不變），使用者重新選定前程式
只重列同一份 `ids`、⛔ 出卡。寬鬆來源改寫名稱後保留 `LENIENT_KEY`、另記已改寫鍵與原講法（正規化字串＋指紋，
只供「候選集內講法」比對，⛔ 寫回草稿）。
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Final, Iterable, List, Mapping, Optional, Tuple

from services.agent.confirm_card import CONTRACT_CREATE_ACTION, MANUAL_BILL_CREATE_ACTION
from services.agent.tools import jgb2 as _jgb2
from services.agent.write_forms import (
    BILL_DUE_EXTEND_FORM,
    FORMS,
    PICK_ID_NONE,
    PICK_TARGET_OP_DOMAIN,
    REPAIR_CREATE_FORM,
    pick_right_effective_from_env,
    value_max_len,
)

#: 候選型別（封閉值域）＝ `pick:` 機器值的第二段。
TYPE_CONTRACT: Final[str] = "contract"
TYPE_ESTATE: Final[str] = "estate"
TYPE_BILL: Final[str] = "bill"
CANDIDATE_TYPE_DOMAIN: Final[Tuple[str, ...]] = (TYPE_CONTRACT, TYPE_ESTATE, TYPE_BILL)

#: 動作 × 欄位 ⇒ 允許的候選型別（DSP-103：全部含帳單）。
#: `manual_bill_create` 的 `estate_name` 有兩種：物件名稱多筆（型別 estate）、該物件有多份有效合約（型別 contract）。
CANDIDATE_TYPES: Final[Mapping[Tuple[str, str], frozenset]] = {
    (MANUAL_BILL_CREATE_ACTION, "contract_ref"): frozenset({TYPE_CONTRACT}),
    (MANUAL_BILL_CREATE_ACTION, "estate_name"): frozenset({TYPE_ESTATE, TYPE_CONTRACT}),
    (CONTRACT_CREATE_ACTION, "estate_name"): frozenset({TYPE_ESTATE}),
    (REPAIR_CREATE_FORM.action, "estate_name"): frozenset({TYPE_ESTATE}),
    (BILL_DUE_EXTEND_FORM.action, "estate_name"): frozenset({TYPE_BILL}),
}
CANDIDATE_ACTIONS: Final[frozenset] = frozenset(a for a, _f in CANDIDATE_TYPES)

#: 開關生效時，延期繳費的物件名稱同名多筆 ⇒ 先列物件候選（客人先選物件），
#: 帳單候選一律來自已選物件。只在 `pick_right_effective_from_env()` 為真時併入封閉表。
PICK_RIGHT_EXTRA_TYPES: Final[Mapping[Tuple[str, str], frozenset]] = {
    (BILL_DUE_EXTEND_FORM.action, "estate_name"): frozenset({TYPE_ESTATE}),
}


def candidate_types_of(action: Any, field: Any) -> frozenset:
    """`(action, field)` 允許的候選型別（呼叫當下讀開關；off ⇒ 與 `CANDIDATE_TYPES` 逐位相同）。"""
    base = CANDIDATE_TYPES.get((action, field), frozenset())
    extra = PICK_RIGHT_EXTRA_TYPES.get((action, field))
    if extra and pick_right_effective_from_env():
        return base | extra
    return base

#: 型別 ⇒ `jgb2` 投影 domain（給人看的清單與給意圖呼叫的資料段共用同一張投影表）。
DOMAIN_OF_TYPE: Final[Mapping[str, str]] = {
    TYPE_CONTRACT: "contracts", TYPE_ESTATE: "estates", TYPE_BILL: "bills",
}

#: 候選集保存同一次查詢的全部列，程式截 20（A2-R7 (a)）；畫面只列前 5 筆（`CANDIDATES_SHOWN_MAX`，
#: ＝ `runtime.CONFIRM_CANDIDATES_MAX`、`JGB2_CANDIDATE_CAP` 預設值）。
WRITE_CANDIDATES_MAX: Final[int] = 20
CANDIDATES_SHOWN_MAX: Final[int] = 5
#: 開關生效時畫面列 10 筆（候選集仍 ≤20）。jgb2 前端按鈕上限：
#: origin/preview `AgentTurnClient::MAX_QUICK_REPLIES = 10`（origin/master 無該檔、`ChatMessage.vue` 無上限）。
CANDIDATES_SHOWN_MAX_PICK_RIGHT: Final[int] = 10


def candidates_shown_max() -> int:
    """畫面列幾筆（呼叫當下讀開關；off ⇒ `CANDIDATES_SHOWN_MAX`＝改動前）。"""
    return CANDIDATES_SHOWN_MAX_PICK_RIGHT if pick_right_effective_from_env() else CANDIDATES_SHOWN_MAX

#: 編號的合法形狀（候選集 `ids`／`picked` 與 `pick:` 第三段同一條）。
CANDIDATE_ID_RE: Final = re.compile(r"[A-Za-z0-9_-]{1,32}")
#: 入向機器值：`fullmatch`（⛔ NFKC、⛔ strip——前後空白、全形冒號一律不是機器值，照一般文字進模型）。
PICK_VALUE_RE: Final = re.compile(r"pick:(contract|estate|bill):([A-Za-z0-9_-]{1,32})")
PICK_VALUE_PREFIX: Final[str] = "pick:"

#: 候選集的封閉鍵（`load_write_candidates`）。
CANDIDATE_SET_KEYS: Final[frozenset] = frozenset(
    {"action", "field", "type", "ids", "has_more", "name_fp", "creator", "picked"})
#: 帳單候選來自已選物件時，候選集另帶該物件編號（只在開關生效、型別 bill 時合法）。
#: runtime 依它把「改講金額／期間」的重查限定在同一個物件（`scope_pick_of`）。
SCOPE_ESTATE_KEY: Final[str] = "scope_estate_id"
CANDIDATE_SET_KEYS_SCOPED: Final[frozenset] = CANDIDATE_SET_KEYS | {SCOPE_ESTATE_KEY}
#: 候選集出自**名稱寬鬆比對**時另帶
#: `name_lenient: True`（只在型別 estate／contract 時合法）。選定成立後由 runtime 依它把草稿該名稱欄改寫成
#: 本身分清單上那一列的系統名稱。A-2a 精確名稱的候選集 ⛔ 帶此鍵（形狀與改動前逐字相同）。
#: 改寫後 ⛔ 拿掉此鍵（改選另一筆時名稱要跟著改寫），另記 `REWRITTEN_KEY`。
LENIENT_KEY: Final[str] = "name_lenient"
CANDIDATE_SET_KEYS_LENIENT: Final[frozenset] = CANDIDATE_SET_KEYS | {LENIENT_KEY}
#: 已撤回——`picked` 為 `None` 時才可出現、值須 `is True`。
WITHDRAWN_KEY: Final[str] = "withdrawn"
#: 寬鬆來源的草稿名稱已由程式改寫成系統正名——值須 `is True`、只與
#: `LENIENT_KEY` 同時出現、型別限 estate／contract、`picked` 非 `None` 或已撤回；與原講法兩鍵同進同出。
REWRITTEN_KEY: Final[str] = "name_rewritten"
#: 原講法＝第一次改寫前草稿該名稱欄值的正規化字串（`confirm.name_said_key`，
#: 與 `name_fp` 同源：`_write_candidates_field_value`；⛔ 整句、⛔ 送模型的 messages、⛔ provenance）與其指紋。
#: (乙) 缺名稱觸發（列候選時名稱欄為空）⇒ 空字串。只供「候選集內講法」比對，⛔ 寫回草稿。
ORIGIN_KEY: Final[str] = "origin_said"
ORIGIN_FP_KEY: Final[str] = "origin_fp"
_REWRITE_GROUP: Final[frozenset] = frozenset({REWRITTEN_KEY, ORIGIN_KEY, ORIGIN_FP_KEY})
#: 候選集可帶的選用鍵（封閉；其餘一律形狀不合）。
_OPTIONAL_KEYS: Final[frozenset] = frozenset(
    {SCOPE_ESTATE_KEY, LENIENT_KEY, WITHDRAWN_KEY}) | _REWRITE_GROUP
#: 理解層保留值與候選編號同字形空間 ⇒ 編號等於保留值一律拒收（縱深防禦：讀回竄改的編號 ⛔ 與任一理解層保留值
#: 同字）。選定後回合改指令式：保留值＝`pick_id` 的 `none` 與指令
#: `op` 值域（`PICK_TARGET_OP_DOMAIN`），與 `{picked}` 保留值拒收（`write_forms.pick_target_rule`）同一集合。
RESERVED_IDS: Final[frozenset] = frozenset({PICK_ID_NONE}) | frozenset(PICK_TARGET_OP_DOMAIN)
_NAME_FP_RE: Final = re.compile(r"[0-9a-f]{32}")

# ── 固定句（只插筆數，或系統正名與編號；⛔ 使用者值、⛔ 查詢字串、⛔ 給模型的提示句）─────────────
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
#: 打字改選成立、該回合沒出卡（其他欄位仍缺）⇒ 追問前加這句。
#: `{title}` 只會是本回合帶身分取得的系統列 `title`（過 `sanitize_data_piece` 且等值），`{id}` 只會是候選集內
#: 編號；⛔ 草稿、使用者或模型的值。dialog 只寫 `CANDIDATE_REPICK_DIALOG_SUMMARY`（⛔ 名稱）。
CANDIDATE_REPICK_TEXT: Final[str] = "已改成：{title}（編號 {id}）。"
CANDIDATE_REPICK_DIALOG_SUMMARY: Final[str] = "已依使用者的改口，改選候選清單中的另一筆"

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
#: 寬鬆來源的選定成立後，草稿名稱欄已由程式改寫成系統名稱（只記碼，⛔ 名稱、編號）。
V_NAME_LENIENT_REWRITE: Final[str] = "name_lenient:picked_rewrite"
#: 已選定（或已撤回）後打字改選成立／只撤回（選定後回合改指令式：
#: 最後一個指令為 `clear`、`name` 對到清單內另一筆或指令無效 ⇒ 撤回並重列）。
V_CANDIDATE_REPICK_TYPED: Final[str] = "write_candidate_repick:typed"
V_CANDIDATE_RETRACT_TYPED: Final[str] = "write_candidate_retract:typed"
#: 出卡入口的關口：已撤回時程式依草稿發 `confirm.request` 的入口改成重列同一份 `ids`。
V_CANDIDATE_RELIST_WITHDRAWN: Final[str] = "write_candidate_relist:withdrawn"
#: 選定後（或已撤回）名稱欄合併的程式判定——丟棄（候選集內講法、不是本回合講的、
#: 本回合已改選、`pick_id` 等於現選定）／改用新名稱（候選集外且本回合講）。只記碼（⛔ 名稱、編號）。
V_CANDIDATE_NAME_KEPT: Final[str] = "write_candidate_name_kept"
V_CANDIDATE_NAME_NEW: Final[str] = "write_candidate_name_new"
#: 候選集已選定或已撤回、仍綁定本草稿時，意圖回另一支寫入動作卻
#: 沒有任何非空欄位值 ⇒ 程式不換草稿、不合併、不整句填入。只記碼（⛔ 動作名、⛔ 值）。
V_CANDIDATE_ACTION_KEPT: Final[str] = "write_candidate_action_kept"
#: 同一次意圖結果裡既有驗過且未被退回的改選目標、又「改講新名稱」
#: 成立 ⇒ 矛盾：視同 retract（已選定 ⇒ 撤回並重列同一份 ids；已撤回 ⇒ 重列），本回合所有名稱值丟棄、不解綁。
#: 只記碼（⛔ 名稱、編號）。
V_CANDIDATE_NAME_CONFLICT: Final[str] = "write_candidate_name_conflict"
#: 選定後回合改指令式：指令清單的 trace 標記——只記封閉碼（⛔ 模型原字串、⛔ 名稱、⛔ 編號）。
#: `write_candidate_cmds:<碼依序，逗號連，最多 8 個>`、`write_candidate_cmd_last:<pick|nth|name|clear|none|invalid>`；
#: 碼＝{pick, nth, name, clear, invalid}。`write_candidate_cmd_invalid`＝最後一項效果「無效」（⇒ 撤回重列）；
#: `write_candidate_cmd_skipped`＝換動作回合（另一動作帶非名稱值）⇒ ⛔ 讀 `target`。
V_CANDIDATE_CMDS_PREFIX: Final[str] = "write_candidate_cmds:"
V_CANDIDATE_CMD_LAST_PREFIX: Final[str] = "write_candidate_cmd_last:"
V_CANDIDATE_CMD_INVALID: Final[str] = "write_candidate_cmd_invalid"
V_CANDIDATE_CMD_SKIPPED: Final[str] = "write_candidate_cmd_skipped"
#: `name` 指令將解綁時，解綁前先用解綁後重查同一組查找查一次——結果含現選定
#: （帳單候選：選定物件；手開帳單一物件多合約：選定合約所屬物件）⇒ `keep`（維持選定、名稱欄回改前值）；沒比中或
#: 不比對（身分閘不過、查找失敗、取不到比對編號）⇒ `miss`（照現行解綁重查）。只記這兩個封閉碼（⛔ 名稱、編號）。
V_CANDIDATE_NAME_PRECHECK_KEEP: Final[str] = "write_candidate_name_precheck:keep"
V_CANDIDATE_NAME_PRECHECK_MISS: Final[str] = "write_candidate_name_precheck:miss"
#: 附候選段的意圖呼叫第一次截斷（`finish_reason=length`）或解析不出 ⇒ 程式以同一份
#: 輸入重送一次（算在同一個等待上限內）。只記碼。
V_CANDIDATE_INTENT_RETRY: Final[str] = "write_candidate_intent_retry"
V_CANDIDATE_PICK_INVALID: Final[str] = "write_candidate_pick_invalid"
V_CANDIDATE_REASK: Final[str] = "write_candidate_reask"
V_CANDIDATES_SHAPE_INVALID: Final[str] = "write_candidates_shape_invalid"
#: 卡後更正時「綁定卡帶著的選定」帶不帶回的程式判定（⛔ 記編號）。
#: `same`＝AI 恰回 `record_rechoice=same`、帶回；`declined`＝其他前提都成立、但 AI 沒恰回 `same` ⇒ 不帶。
V_CANDIDATE_CARRY_SAME: Final[str] = "write_candidate_carry:same"
V_CANDIDATE_CARRY_DECLINED: Final[str] = "write_candidate_carry:declined"
#: AI 恰回 `record_rechoice=other`（使用者要改用另一筆）⇒ 程式作廢綁定卡、依草稿名稱重新解析。
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
    return cand_type in candidate_types_of(action, field)


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
                      has_more: bool, field_value: Any, creator: Mapping[str, Any],
                      scope_estate_id: Any = None, lenient: bool = False) -> Optional[dict]:
    """組一份候選集（程式出口的唯一建構點）；組不出合法形狀 ⇒ `None`（呼叫端不寫、不列）。
    `scope_estate_id`（「選對紀錄」片）：帳單候選來自已選物件 ⇒ 該物件編號（`None` ⇒ 與改動前同形）。
    `lenient`（F12）：候選出自名稱寬鬆比對 ⇒ 帶 `LENIENT_KEY`（`False` ⇒ 與改動前同形）。"""
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
    if scope_estate_id is not None:
        value[SCOPE_ESTATE_KEY] = candidate_id(scope_estate_id)
    if lenient:
        value[LENIENT_KEY] = True
    loaded, _invalid = load_write_candidates(value)
    return loaded


def is_lenient(cands: Any) -> bool:
    """F12：這份（已讀回的）候選集出自名稱寬鬆比對。"""
    return isinstance(cands, Mapping) and cands.get(LENIENT_KEY) is True


def _scope_allowed(raw: Mapping[str, Any]) -> bool:
    """帶物件範圍的候選集形狀只在：開關生效、延期繳費、欄位 estate_name、型別 bill、編號合形狀。"""
    scope = raw.get(SCOPE_ESTATE_KEY)
    return (pick_right_effective_from_env()
            and raw.get("action") == BILL_DUE_EXTEND_FORM.action
            and raw.get("field") == "estate_name" and raw.get("type") == TYPE_BILL
            and isinstance(scope, str) and bool(CANDIDATE_ID_RE.fullmatch(scope)))


def scope_pick_of(cands: Any) -> Optional[dict]:
    """「選對紀錄」片：未選定的帳單候選集帶著物件範圍 ⇒ 程式專用選定通道的**物件**選定
    `{action, field: estate_name, type: estate, id: 範圍}`（重查只在同一個物件）；其餘 ⇒ `None`。
    已撤回（`is_withdrawn`）⇒ `None`（已撤回期間程式 ⛔ 依範圍出卡；取列另用 `scope_rows_pick_of`）。"""
    if not isinstance(cands, Mapping) or cands.get("picked") is not None or is_withdrawn(cands):
        return None
    return scope_rows_pick_of(cands)


def scope_rows_pick_of(cands: Any) -> Optional[dict]:
    """取候選列（`pick_id` 資料段、已撤回重列）用的物件範圍——同 `scope_pick_of`
    但不看選定狀態（選定後、已撤回的帳單候選集仍只在同一個物件取列）。⛔ 當程式專用選定送 `confirm.request`。"""
    if not isinstance(cands, Mapping):
        return None
    scope = cands.get(SCOPE_ESTATE_KEY)
    if scope is None or not _scope_allowed(cands):
        return None
    pick = {"action": cands["action"], "field": "estate_name", "type": TYPE_ESTATE, "id": scope}
    return pick if valid_program_pick(pick, cands["action"]) is not None else None


def load_write_candidates(raw: Any) -> Tuple[Optional[dict], bool]:
    """讀回候選集（**一律視為不可信**，比照 `write_forms.load_draft`）⇒ `(候選集或 None, 形狀不合)`。

    封閉鍵、`(action, field, type)` 在封閉表內、`ids` 為 1～20 個合法且不重複的編號字串、`has_more`
    為布林、`name_fp` 為 32 位十六進位、`creator` 為只含 `user_id`／`role_id` 的物件、`picked` 為
    `None` 或 `ids` 內的編號。缺值（`None`）⇒ `(None, False)`；其餘不合 ⇒ `(None, True)`。

    選用鍵（封閉）：物件範圍（只在開關生效、帳單型別）與寬鬆標記（只在 estate／contract）互斥；
    `WITHDRAWN_KEY` 只能在 `picked` 為 `None` 時出現、值須 `is True`；已改寫鍵與
    原講法兩鍵同進同出——已改寫鍵 `is True`、須有寬鬆標記、`picked` 非 `None` 或已撤回，原講法為長度不超過
    該名稱欄上限的字串、`origin_fp`＝其指紋；編號等於 `pick_id` 保留值（`RESERVED_IDS`）一律不合。"""
    if raw is None:
        return None, False
    if not isinstance(raw, dict):
        return None, True
    keys = set(raw)
    if not CANDIDATE_SET_KEYS <= keys or not keys - CANDIDATE_SET_KEYS <= _OPTIONAL_KEYS:
        return None, True
    scoped = SCOPE_ESTATE_KEY in keys
    lenient = LENIENT_KEY in keys
    if scoped and (lenient or not _scope_allowed(raw)):
        return None, True
    if lenient and not (raw.get(LENIENT_KEY) is True and raw.get("type") in (TYPE_ESTATE, TYPE_CONTRACT)):
        return None, True
    if not allowed(raw.get("action"), raw.get("field"), raw.get("type")):
        return None, True
    ids = raw.get("ids")
    if (not isinstance(ids, list) or not ids or len(ids) > WRITE_CANDIDATES_MAX
            or len(set(i for i in ids if isinstance(i, str))) != len(ids)
            or not all(isinstance(i, str) and CANDIDATE_ID_RE.fullmatch(i) for i in ids)
            or any(i in RESERVED_IDS for i in ids)):
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
    if picked is not None and not (isinstance(picked, str) and CANDIDATE_ID_RE.fullmatch(picked)
                                   and picked in ids):
        return None, True
    withdrawn = WITHDRAWN_KEY in keys
    if withdrawn and (raw.get(WITHDRAWN_KEY) is not True or picked is not None):
        return None, True
    rewrite = keys & _REWRITE_GROUP
    if rewrite and rewrite != _REWRITE_GROUP:
        return None, True
    origin: Optional[str] = None
    if rewrite:
        origin = raw.get(ORIGIN_KEY)
        origin_fp = raw.get(ORIGIN_FP_KEY)
        if (raw.get(REWRITTEN_KEY) is not True or not lenient
                or (picked is None and not withdrawn)
                or not isinstance(origin, str) or len(origin) > _name_value_max(raw)
                or not isinstance(origin_fp, str) or not _NAME_FP_RE.fullmatch(origin_fp)
                or origin_fp != name_fp(origin)):
            return None, True
    out = {
        "action": raw["action"], "field": raw["field"], "type": raw["type"], "ids": list(ids),
        "has_more": raw["has_more"], "name_fp": fp,
        "creator": {"user_id": creator["user_id"], "role_id": creator["role_id"]},
        "picked": picked,
    }
    if scoped:
        out[SCOPE_ESTATE_KEY] = raw[SCOPE_ESTATE_KEY]
    if lenient:
        out[LENIENT_KEY] = True
    if withdrawn:
        out[WITHDRAWN_KEY] = True
    if rewrite:
        out[REWRITTEN_KEY] = True
        out[ORIGIN_KEY] = origin
        out[ORIGIN_FP_KEY] = name_fp(origin)
    return out, False


def _name_value_max(raw: Mapping[str, Any]) -> int:
    """候選集那一欄（表單名稱欄）的值長度上限（`value_max_len`）；表單或欄位查不到 ⇒ 0（原講法只能是空字串）。"""
    form = FORMS.get(raw.get("action"))
    f = form.field(raw.get("field")) if form is not None else None
    return value_max_len(f) if f is not None else 0


def is_withdrawn(cands: Any) -> bool:
    """這份（已讀回的）候選集處於已撤回狀態（`picked` 為 `None`、`WITHDRAWN_KEY` 為 `True`）。"""
    return (isinstance(cands, Mapping) and cands.get(WITHDRAWN_KEY) is True
            and cands.get("picked") is None)


def is_rewritten(cands: Any) -> bool:
    """寬鬆來源的候選集，草稿名稱已由程式改寫成選定那筆的系統正名。"""
    return isinstance(cands, Mapping) and is_lenient(cands) and cands.get(REWRITTEN_KEY) is True


def withdraw(cands: Mapping[str, Any]) -> Optional[dict]:
    """清掉選定、進入已撤回——`ids`、名稱指紋、寬鬆標記、已改寫鍵與原講法原樣保留
    （⛔ 動草稿名稱、⛔ 重新解析名稱）。組不出合法形狀 ⇒ `None`。"""
    value = dict(cands, picked=None)
    value[WITHDRAWN_KEY] = True
    loaded, _invalid = load_write_candidates(value)
    return loaded


def repick(cands: Mapping[str, Any], pick_id: str) -> Optional[dict]:
    """選定改成 `pick_id`（須在 `ids` 內）並拿掉已撤回標記；組不出合法形狀 ⇒ `None`。"""
    value = {k: v for k, v in cands.items() if k != WITHDRAWN_KEY}
    value["picked"] = pick_id
    loaded, _invalid = load_write_candidates(value)
    return loaded


def program_pick_of(cands: Mapping[str, Any], picked: str) -> dict:
    """程式專用選定通道的形狀：`{action, field, type, id}`，由候選集組出。"""
    return {"action": cands["action"], "field": cands["field"], "type": cands["type"],
            "id": str(picked)}


#: 出卡後候選集照清，由 `program_pick` 出的那張卡
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
    """給人看的清單（`jgb2.candidates_text_for_user`，同一張投影表）。
    開關生效時改用寫入候選專用投影（`_PR_PROJECTORS`；唯讀查詢的 `_ROW_PROJECTORS`
    ⛔ 改）。"""
    if pick_right_effective_from_env():
        return "\n".join(_PR_PROJECTORS[cand_type](dict(r)) for r in rows)
    return _jgb2.candidates_text_for_user(DOMAIN_OF_TYPE[cand_type], list(rows))


def data_piece_text(cand_type: str, rows: List[Mapping[str, Any]]) -> str:
    """給意圖判斷呼叫的資料段內文：每列只放投影欄、逐列過 `sanitize_data_piece`（呼叫端再以 nonce 包住）。
    開關生效時投影換成 `_PR_PROJECTORS`（仍逐列 sanitize）。"""
    from services.agent.completed_actions import sanitize_data_piece

    if pick_right_effective_from_env():
        projector = _PR_PROJECTORS[cand_type]
    else:
        projector = _jgb2._ROW_PROJECTORS[DOMAIN_OF_TYPE[cand_type]]
    return "\n".join(sanitize_data_piece(projector(dict(r))) for r in rows)


#: 開關生效時寫入候選列的**白名單**。
#: 物件多留縣市區、樓層、租金、狀態、有無有效合約（`has_valid_contract`：由 `tools.confirm` 以同一次
#: `_viewer_contract_rows` 推得後寫上；`None`＝合約清單還有下一頁、判不出）；合約多留起訖、租金、狀態
#: （`get_current_stage` 讀 `status`／`bit_status`／`is_history`／`is_history_done`）；帳單留標題、計費起訖、
#: 繳費期限、金額（`total`，`bills._bill_amount_due`）、狀態（`status`／`bit_status`，`bills._bill_status`）。
#: ⛔ `to_user_*`、地址類（`address`／`full_address`／`display_address`）、經緯度、`user_id`、`sub_title`、
#: `payment_id`、`invoice_number`、承租人姓名——不在白名單 ⇒ 一律不帶。
PICK_RIGHT_ROW_KEYS: Final[Mapping[str, Tuple[str, ...]]] = {
    TYPE_ESTATE: ("id", "title", "city", "district", "floor", "rent", "status",
                  "has_valid_contract"),
    TYPE_CONTRACT: ("id", "title", "date_start", "date_end", "rent", "status", "bit_status",
                    "estate_id", "is_history", "is_history_done"),
    TYPE_BILL: ("id", "title", "date_start", "date_end", "date_expire", "total", "status",
                "bit_status"),
}
#: 物件列上「有無有效合約」的鍵（`tools.confirm` 寫、投影讀）。
HAS_VALID_CONTRACT_KEY: Final[str] = "has_valid_contract"


def minimize_row(cand_type: str, row: Mapping[str, Any]) -> dict:
    """候選列只留投影與按鈕要用的鍵（最小揭露；合約列另有承租人電話／Email 等，⛔ 帶出）。
    帳單列沿用現行（投影要讀金額與狀態的多個來源鍵，`_bill_candidates_result` 原樣）。
    「選對紀錄」片：開關生效時三種型別一律照 `PICK_RIGHT_ROW_KEYS` 白名單（帳單列也縮減）。"""
    if pick_right_effective_from_env():
        keep = PICK_RIGHT_ROW_KEYS[cand_type]
    elif cand_type == TYPE_CONTRACT:
        keep = ("id", "title", "date_end", "estate_id", "is_history")
    elif cand_type == TYPE_ESTATE:
        keep = ("id", "title", "status")
    else:
        return dict(row)
    return {k: row.get(k) for k in keep if k in row}


# ── 寫入候選專用投影（給人看的清單與給 AI 的資料段共用；唯讀查詢的投影不動）──────
#: 缺值或判不出時印的字（同確認卡 `confirm_card.PICK_DISPLAY_NONE`）。
PR_NONE: Final[str] = "—"


def _pr_text(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _pr_money(value: Any) -> Optional[str]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return _jgb2._bill_money(value)


def _pr_period(start: Any, end: Any, fmt) -> Optional[str]:
    if not start and not end:
        return None
    return f"{fmt(start) if start else PR_NONE}～{fmt(end) if end else PR_NONE}"


def _pr_estate_row(row: dict) -> str:
    parts = [f"編號 {row.get('id', '?')}", str(row.get("title") or "")]
    area = "".join(t for t in (_pr_text(row.get("city")), _pr_text(row.get("district"))) if t)
    if area:
        parts.append(area)
    floor = row.get("floor")
    if isinstance(floor, int) and not isinstance(floor, bool):
        parts.append(f"{floor}樓")
    elif _pr_text(floor):
        parts.append(_pr_text(floor))
    rent = _pr_money(row.get("rent"))
    if rent:
        parts.append(f"租金 {rent}")
    parts.append(f"狀態 {_jgb2.estate_status_zh(row.get('status'))}")
    flag = row.get(HAS_VALID_CONTRACT_KEY)
    parts.append(f"有效合約 {'有' if flag is True else '無' if flag is False else PR_NONE}")
    return "、".join(parts)


def _pr_contract_row(row: dict) -> str:
    from services.jgb.contracts import get_current_stage

    parts = [f"編號 {row.get('id', '?')}", str(row.get("title") or "")]
    period = _pr_period(row.get("date_start"), row.get("date_end"), _jgb2._contract_format_date)
    if period:
        parts.append(f"期間 {period}")
    rent = _pr_money(row.get("rent"))
    if rent:
        parts.append(f"租金 {rent}")
    parts.append(f"狀態 {get_current_stage(dict(row))}")
    return "、".join(parts)


def _pr_bill_row(row: dict) -> str:
    parts = [f"編號 {row.get('id', '?')}", str(row.get("title") or "")]
    parts.append(f"狀態 {_jgb2._bill_status_label(_jgb2._bill_status_of(row))}")
    period = _pr_period(row.get("date_start"), row.get("date_end"), _jgb2._bill_format_date)
    if period:
        parts.append(f"計費期間 {period}")
    if row.get("date_expire"):
        parts.append(f"到期日 {_jgb2._bill_format_date(row.get('date_expire'))}")
    amount = _jgb2._bill_amount(row)
    if amount is not None:
        parts.append(f"金額 {_jgb2._bill_money(amount)}")
    return "、".join(parts)


_PR_PROJECTORS: Final[Mapping[str, Any]] = {
    TYPE_ESTATE: _pr_estate_row, TYPE_CONTRACT: _pr_contract_row, TYPE_BILL: _pr_bill_row,
}


# ── 重列與「對不上」的固定句（只插筆數與**程式解析過值閘**的數字）──────────
#: 依客人目前講的條件仍有多筆（AI 回 none、打字選定與先前講的金額或期間不符、未變更重問）。
#: ⚠️ 不回顯客人原話（「依您說的○○」的○○由清單本身呈現；⛔ 插使用者字串）。
PR_REASK_TEXT: Final[str] = "依您目前說的，仍對到 {count}，請點選要用的那一筆。"
#: 0 張相符：說明對不上，並列該物件該期（無期別則全部）帳單。
PR_AMOUNT_MISMATCH_TEXT: Final[str] = "這個物件{scope}沒有 {amount} 元的帳單，以下是{scope_list}的帳單，請點選要處理的那一張。"
PR_RANGE_MISMATCH_TEXT: Final[str] = "這個物件{scope}沒有計費期間 {range} 的帳單，以下是{scope_list}的帳單，請點選要處理的那一張。"
PR_BOTH_MISMATCH_TEXT: Final[str] = "這個物件{scope}沒有 {amount} 元、計費期間 {range} 的帳單，以下是{scope_list}的帳單，請點選要處理的那一張。"

#: trace 標記（只記碼，⛔ 金額、名稱、期間）。
V_PICK_RIGHT_AMOUNT_MISMATCH: Final[str] = "pick_right:amount_mismatch"
V_PICK_RIGHT_RANGE_MISMATCH: Final[str] = "pick_right:range_mismatch"
V_PICK_RIGHT_ESTATE_FIRST: Final[str] = "pick_right:estate_first"
#: 「對不上」的碼（`tools.confirm` 寫進候選形狀 `data["pick_note"]`；值域封閉）。
PICK_NOTE_AMOUNT: Final[str] = "amount_mismatch"
PICK_NOTE_RANGE: Final[str] = "range_mismatch"
PICK_NOTE_BOTH: Final[str] = "both_mismatch"
PICK_NOTE_DOMAIN: Final[frozenset] = frozenset({PICK_NOTE_AMOUNT, PICK_NOTE_RANGE, PICK_NOTE_BOTH})


def pick_note_marks(code: Any) -> Tuple[str, ...]:
    """「對不上」碼 ⇒ trace 標記（值域外 ⇒ 空）。"""
    if code == PICK_NOTE_AMOUNT:
        return (V_PICK_RIGHT_AMOUNT_MISMATCH,)
    if code == PICK_NOTE_RANGE:
        return (V_PICK_RIGHT_RANGE_MISMATCH,)
    if code == PICK_NOTE_BOTH:
        return (V_PICK_RIGHT_AMOUNT_MISMATCH, V_PICK_RIGHT_RANGE_MISMATCH)
    return ()


def pick_note_text(code: Any, *, said_amount: Any, said_range: Any, has_period: bool) -> Optional[str]:
    """「對不上」前言（只插已過值閘的整數與正規化 `MM/DD~MM/DD`）；碼或值不合 ⇒ `None`（用一般前言）。"""
    from services.agent.bill_period import said_range_parts

    scope = "該期" if has_period else ""
    scope_list = "該期" if has_period else "這個物件全部"
    amount = (f"{said_amount:,}" if isinstance(said_amount, int) and not isinstance(said_amount, bool)
              else None)
    parts = said_range_parts(said_range)
    rng = (f"{parts[0][0]:02d}/{parts[0][1]:02d}～{parts[1][0]:02d}/{parts[1][1]:02d}"
           if parts is not None else None)
    if code == PICK_NOTE_AMOUNT and amount:
        return PR_AMOUNT_MISMATCH_TEXT.format(scope=scope, amount=amount, scope_list=scope_list)
    if code == PICK_NOTE_RANGE and rng:
        return PR_RANGE_MISMATCH_TEXT.format(scope=scope, range=rng, scope_list=scope_list)
    if code == PICK_NOTE_BOTH and amount and rng:
        return PR_BOTH_MISMATCH_TEXT.format(scope=scope, amount=amount, range=rng,
                                            scope_list=scope_list)
    return None


def pr_reask_text(cand_type: str, n: int, has_more: bool) -> str:
    return PR_REASK_TEXT.format(count=candidate_count_text(cand_type, n, has_more))


# ── PR-2「全同時照實說分不出、請講編號」與 PR-7：畫面上除編號外全同的候選 ─────────────────────────────
#: 清單裡有兩筆以上除編號外一字不差時，接在清單後。
PR_INDISTINCT_TEXT: Final[str] = "其中有幾筆除了編號，畫面上的資料都一樣，系統分不出是哪一筆，請講編號或直接點選。"
#: AI 打字選定的那筆與另一筆畫面全同 ⇒ 不收、重列（否則會寫錯筆）。
V_PICK_RIGHT_INDISTINCT: Final[str] = "pick_right:indistinct"
#: 意圖呼叫把計費起訖填進期別欄 ⇒ 改走起訖欄值閘（runtime `_write_draft_merge_intent`）。
V_PICK_RIGHT_PERIOD_AS_RANGE: Final[str] = "pick_right:period_as_range"


def pr_signature(cand_type: str, row: Mapping[str, Any]) -> str:
    """清單上這一列去掉「編號 N、」之後的文字——客人與 AI 能拿來分辨的全部內容。"""
    text = _PR_PROJECTORS[cand_type](dict(row))
    return text.split("、", 1)[1] if "、" in text else ""


def pr_indistinct_ids(cand_type: str, rows: Iterable[Mapping[str, Any]]) -> frozenset:
    """畫面上與至少另一列除編號外全同的候選編號。"""
    groups: dict = {}
    for row in rows:
        cid = candidate_id(row.get("id")) if isinstance(row, Mapping) else None
        if cid is not None:
            groups.setdefault(pr_signature(cand_type, row), []).append(cid)
    return frozenset(cid for ids in groups.values() if len(ids) > 1 for cid in ids)


def said_mismatch_marks(row: Mapping[str, Any], *, said_amount: Any, said_range: Any) -> Tuple[str, ...]:
    """帳單列與客人先前講的金額／計費期間比對 ⇒ 不符的 trace 標記（皆符或沒講 ⇒ 空）。
    比法與 `tools.confirm` 篩帳單同一條（`bill_matches_said`）。"""
    marks: list = []
    if said_amount is not None and not bill_amount_matches(row, said_amount):
        marks.append(V_PICK_RIGHT_AMOUNT_MISMATCH)
    if said_range is not None and not bill_range_matches(row, said_range):
        marks.append(V_PICK_RIGHT_RANGE_MISMATCH)
    return tuple(marks)


def bill_amount_matches(row: Mapping[str, Any], said_amount: Any) -> bool:
    """`_bill_amount(row) == said_amount`（金額缺值 ⇒ 不符）。"""
    amount = _jgb2._bill_amount(dict(row))
    if amount is None or isinstance(said_amount, bool) or not isinstance(said_amount, int):
        return False
    return amount == said_amount


def bill_range_matches(row: Mapping[str, Any], said_range: Any) -> bool:
    """`date_start`／`date_end` 的**月日**與 `said_range` 相符（任一缺值 ⇒ 不符）。"""
    from services.agent.bill_period import said_range_parts
    from services.agent.confirm_card import ConfirmCardError, _parse_date

    parts = said_range_parts(said_range)
    if parts is None:
        return False
    try:
        start = _parse_date(row.get("date_start"), "date_start", "pick_right")
        end = _parse_date(row.get("date_end"), "date_end", "pick_right")
    except ConfirmCardError:
        return False
    return ((start.month, start.day), (end.month, end.day)) == parts


__all__ = [
    "TYPE_CONTRACT", "TYPE_ESTATE", "TYPE_BILL", "CANDIDATE_TYPE_DOMAIN", "CANDIDATE_TYPES",
    "CANDIDATE_ACTIONS", "DOMAIN_OF_TYPE", "WRITE_CANDIDATES_MAX", "CANDIDATES_SHOWN_MAX",
    "CANDIDATE_ID_RE", "PICK_VALUE_RE", "PICK_VALUE_PREFIX", "CANDIDATE_SET_KEYS",
    "LENIENT_KEY", "CANDIDATE_SET_KEYS_LENIENT", "is_lenient", "V_NAME_LENIENT_REWRITE",
    # 已撤回／改寫
    "WITHDRAWN_KEY", "REWRITTEN_KEY", "ORIGIN_KEY", "ORIGIN_FP_KEY", "RESERVED_IDS",
    "is_withdrawn", "is_rewritten", "withdraw", "repick", "scope_rows_pick_of",
    "CANDIDATE_REPICK_TEXT", "CANDIDATE_REPICK_DIALOG_SUMMARY", "V_CANDIDATE_REPICK_TYPED",
    "V_CANDIDATE_RETRACT_TYPED", "V_CANDIDATE_RELIST_WITHDRAWN", "V_CANDIDATE_NAME_KEPT", "V_CANDIDATE_NAME_NEW",
    "V_CANDIDATE_ACTION_KEPT", "V_CANDIDATE_NAME_CONFLICT", "V_CANDIDATE_INTENT_RETRY",
    "V_CANDIDATE_CMDS_PREFIX", "V_CANDIDATE_CMD_LAST_PREFIX", "V_CANDIDATE_CMD_INVALID",
    "V_CANDIDATE_CMD_SKIPPED",
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
    # 「選對紀錄」片
    "PICK_RIGHT_EXTRA_TYPES", "candidate_types_of", "CANDIDATES_SHOWN_MAX_PICK_RIGHT",
    "candidates_shown_max", "SCOPE_ESTATE_KEY", "CANDIDATE_SET_KEYS_SCOPED", "scope_pick_of",
    "PICK_RIGHT_ROW_KEYS", "HAS_VALID_CONTRACT_KEY", "PR_NONE", "PR_REASK_TEXT",
    "PR_AMOUNT_MISMATCH_TEXT", "PR_RANGE_MISMATCH_TEXT", "PR_BOTH_MISMATCH_TEXT",
    "V_PICK_RIGHT_AMOUNT_MISMATCH", "V_PICK_RIGHT_RANGE_MISMATCH", "V_PICK_RIGHT_ESTATE_FIRST",
    "PICK_NOTE_AMOUNT", "PICK_NOTE_RANGE", "PICK_NOTE_BOTH", "PICK_NOTE_DOMAIN",
    "pick_note_marks", "pick_note_text", "pr_reask_text", "said_mismatch_marks",
    "bill_amount_matches", "bill_range_matches",
]
