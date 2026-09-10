"""回合狀態容器與回合資料契約（Plan R R1｜`inputs/plan-structural-refactor-20260910.md` §0c）。

**本檔是純搬移＋一支新容器**：`ToolCallRecord`／`TurnTrace`／`TurnResult`／
`outcome` 契約／`dialog` 與 `handoff_cache` 兩支收尾工具／`_emit_agent_decision`
逐字從 `runtime.py` 搬來，⛔ 一個判定、一個文案都沒有改。`runtime.py` 原樣
re-export 它們，既有 import 路徑（`from services.agent.runtime import TurnResult`
之類）**一律不變**。

新增的只有三支：

- `ReservedCallIds`——九個保留 `tool_call_id` **由 nonce 派生**（原本在
  `_run_turn_body` 裡九行各算一次）。⚠️ 派生一律**無條件**：模型能不能偽造一個
  `img-…` ⛔ 不該取決於這一回合是否真的有影像（見 `runtime.py` 原註記）。
- `TurnInputsSnapshot`——段落產生後寫入、之後唯讀的七個 trace 輸入
  （§0c r2 #4），外加 `outline_sha`／`rules_sha` 兩個在回合內不變的值。
- `TurnAccumulator`——`_run_turn_body` 的閉包 `_finalize`／`_build_fixed` 捕獲的
  **全部可變名稱**（§0c 逐項）。⚠️ 整數計數一律**就地加**（`acc.llm_calls += 1`），
  ⛔ 不再重新綁定區域變數；list／dict 一律同一個物件、⛔ 不在段邊界複製。

⛔ **本檔不 import `runtime`**（那會成環）：`turn_context` → `exit_gates`／
`turn_segments` → `runtime` 是單向的。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional

from services import usage_metering
from services.agent.budget import BudgetCounters
from services.agent.canon.candidate_selector import K as _CANDIDATE_K
from services.agent.output_schema import VerifierVerdict
from services.agent.prompt_assembler import wrap_provenance_data
from services.agent.provenance_units import OUTLINE_TOOL_CALL_ID, provenance_units
from services.agent.tools.registry import Provenance, ToolResult
from services.conversational_config import (
    effective_handoff_channel,
    effective_handoff_message,
)
from services.presales_gate import FactClass

logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# 資料模型（design 元件 1／「資料模型」節）
# ---------------------------------------------------------------------------


@dataclass
class ToolCallRecord:
    """⛔ **無 `args_hash`**（2.6 前置 security review P2）：低熵參數（`kb_id`、
    `face` enum、短 `keyword`）的 sha256 可字典反解，等於把原值以另一種形式
    落進 `decision_snapshot`。只留 `args_summary` 的形狀摘要。
    """

    id: str
    name: str
    args_summary: dict
    ms: int
    status: Literal["ok", "error", "timeout", "rejected"]
    n_items: int
    #: T2（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §3）：這一筆
    #: 工具結果是不是「查了、但查無資料」。⚠️ **只有 `status=="ok"` 時才可能為
    #: `True`**——`error`／`timeout`／`rejected` 一律 `False`（plan-verifier r2 #1：
    #: 「沒查成」⛔ 不得講成「不存在」）；由主模型迴圈在 `tool_results_by_id`
    #: 登記處以程式算出。select／confirm 兩段建構點只用預設值 `False`
    #: （那兩段本來就不會走 T2 的兩出口分流）。
    empty: bool = False


@dataclass
class TurnTrace:
    trace_id: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    verifier: list[VerifierVerdict] = field(default_factory=list)
    final_kind: str = ""
    handoff_reason: Optional[str] = None
    latency_ms: int = 0
    violations: list[str] = field(default_factory=list)
    rules_sha: str = ""
    outline_sha: str = ""
    #: 任務 4.1（Plan §2.1-3）：候選選取結果。重播路徑一律留預設
    #: （`[]`／`{}`／`None`）——那條路根本沒跑過 `_select_outline`。
    candidate_ids: list[str] = field(default_factory=list)
    winning_key_kind: dict[str, str] = field(default_factory=dict)
    miss_kind: Optional[str] = None
    #: DSP-038／S-11（稽核落點）：確認回合與兌現回合各記一個 `pending_id`；
    #: 兌現成功時另記 receipt 的識別碼。⛔ 兩者都**不是原文**——`pending_id` 是
    #: token 的單向摘要，`receipt_id` 經 `confirm_card.receipt_id_of` 過形狀
    #: （`[A-Za-z0-9_.:-]{1,64}`），下游回來的自由文字進不了這裡。
    pending_id: Optional[str] = None
    receipt_id: Optional[str] = None
    #: W8 (1)／S8-6：清單點選回合的稽核三鍵。
    #: ⛔⛔ **`ref` 原值不得進來**——`has_ref` 只記「有沒有」，`select_type` 是
    #:     封閉表的鍵。trace 與 `usage_events` 都會被序列化落地，把使用者點的
    #:     那張帳單／合約編號寫進去，等於把識別碼從對話狀態外溢到計量表。
    select_type: Optional[str] = None
    has_ref: Optional[bool] = None
    #: 槽位有沒有真的寫進去（找不到 COLLECTING 列 ⇒ False，回合照樣回 facts）。
    slot_written: Optional[bool] = None
    #: T1／security r1 #7：本回合**有沒有注入呼叫端進場句資料段**。
    #: ⛔⛔ **進場句的文字不得進來**——`context` 是呼叫端送的自由文字，trace 與
    #:     `usage_events.decision_snapshot` 都會被序列化落地，記文字等於把外部
    #:     輸入原封不動抄進計量表。只記一個 bool。
    has_context: bool = False
    #: U3（Plan `plan-walkthrough-fixes-batch3-20260909.md` §4）：本回合有沒有
    #: 觸發純編號／短名詞前置查詢。⛔⛔ **原 ref／關鍵字不得進來**——只記
    #: `{"kind": "id"|"keyword", "hits": <int>}`；未觸發 ⇒ `None`。
    pre_lookup: Optional[dict] = None
    #: V2（Plan batch4 §3）：本回合有沒有注入「最近出現的編號」資料段。
    #: ⛔⛔ **編號原值不得進來**——同 `has_context`／`has_ref` 一套紀律，只記 bool。
    has_recent_refs: bool = False
    #: W9 U2：文件回合的稽核四鍵。
    #: ⛔⛔ **任何欄位值都不得進來**——`document_status`／`document_kind` 都是
    #:     封閉值域裡的標籤（`DOCUMENT_STATUSES`／`DOCUMENT_KINDS`），`pages_seen`
    #:     是計數。trace 與 `usage_events.decision_snapshot` 都會被序列化落地，
    #:     記一個金額或一個地址進去，等於把使用者上傳的文件內容抄進計量表。
    has_document: bool = False
    document_status: Optional[str] = None
    document_kind: Optional[str] = None
    pages_seen: Optional[int] = None
    #: 第六批 #8：呼叫端帶了 `attachment_purpose="document"` 但**一張照片、一份
    #: 檔案都沒帶** ⇒ 這一回合當一般回合跑，這個旗標記下「那個鍵被忽略了」。
    #: ⛔ 只有 bool，無任何附件資訊。寫入點是 `mcp_facade._agent_turn`（門面才
    #: 知道 `attachment_purpose`），⛔ 不由 Runtime 猜。
    attachment_purpose_ignored: bool = False
    #: R1b（Plan R §0b／DSP-040 絆線）：本回合 Verifier **觀察到而未擋**的違規
    #: 類別 → 次數（`Counter(VerifierVerdict.observed)` 逐次累加）。
    #: ⛔⛔ **只有列舉的類別名與整數**——`observed` 本身就 ⛔ 不攜帶任何模型文字或
    #:     來源原文（見 `output_schema.VerifierVerdict.observed`），這一格同一條紀律。
    #: ⚠️ `default_factory=dict`：三個 `TurnTrace(` 建構點（確認／清單／照片段的共用
    #:    收尾、handoff 快取重播、固定句出口）一律取空 dict——**只有取得 verdict 的
    #:    一般出口寫入實值**（Plan §0b 明列）。⛔ 不用 `None` 假裝這一格不存在：
    #:    觀察模式下「這回合沒有被觀察到的違規」與「這回合根本沒跑 Verifier」在
    #:    稽核上都要看得見，前者是 `{}`、後者也是 `{}`，差別由 `llm_calls` 分辨。
    verifier_observed_counts: dict = field(default_factory=dict)


@dataclass
class TurnResult:
    kind: str
    answer: str
    handoff: Optional[dict]
    quick_replies: list
    trace: TurnTrace
    #: T1：本回合的**追問對象**（`AgentOutput.ask_target` 帶進來的封閉值）。
    #: ⚠️ **內部欄位**：`/mcp` `agent.turn` 的輸出契約仍是七鍵，`ask_target`
    #:     ⛔ 不對外——它的用途是寫進 `agent_state[LAST_ASK_TARGET_KEY]` 給
    #:     下一回合的程式判定讀，不是給呼叫端畫面用的。
    ask_target: Optional[str] = None
    #: DSP-043（2026-09-08）：機器可讀的回合結果（第七鍵 `outcome`）。`None` ⇒
    #: 由 `default_outcome()` 依 `kind`／`quick_replies` 導出；確認鏈、清單點選、
    #: 範圍外、照片終止路徑在各自出口**以程式**明設。⛔ 不由模型、不由字串判。
    outcome: Optional[dict] = None


# ════════════════════════════════════════════════════════════════════
# DSP-043：`outcome`——回合結果的封閉描述（與畫面無關，任何呼叫端共用）
# ════════════════════════════════════════════════════════════════════
#: `state`：這回合發生了什麼（封閉八值）。
OUTCOME_STATES: tuple = (
    "answered",         # 一般回答（含清單點選直答、查無此筆）
    "clarifying",       # 反問／請選分類（等使用者補一句或選一個）
    "confirm_pending",  # 出了確認卡，等三顆按鈕
    "confirmed",        # 兌現成功（含 R4.3 重送同一 receipt）
    "cancelled",        # 按了取消／修改而燒掉卡（含重送已取消那一筆）
    "failed",           # 寫入失敗、確認已失效、照片處理失敗／逾時
    "handoff",          # 轉專人固定句
    "out_of_scope",     # 清單點選後問別戶／別戶寫入被擋
)
#: `expects`：接下來等使用者什麼（封閉六值）。
#: 第六批 #4：加 `image`／`file`——「請拍張照片給我」與「請把那份文件傳上來」
#: 這兩種追問，呼叫端畫面要出的是**傳檔鍵**而不是輸入框，而 `text` 讓 LIFF／
#: line-bot 只能出輸入框（實測：使用者被要求傳照片卻只看得到打字列）。
OUTCOME_EXPECTS: tuple = ("text", "choice", "button", "image", "file", "none")

#: 第六批 #4：**追問對象 → `expects`** 的封閉對映，且是「哪個追問對象要傳檔」
#: 的**唯一**來源（`ASK_TARGETS` 的 `photo`／`document` 兩項）。表外的追問對象
#: 照舊由 `quick_replies` 決定 `text`／`choice`。
#: ⛔ 不得在別處另開一個判 `ask_target` 的 if——那就會有第二份「要傳檔的對象」
#: 清單，而兩份清單只會各自演化。
_ASK_TARGET_EXPECTS: dict = {"photo": "image", "document": "file"}
#: `ref.type` 封閉值域（與 `select:<type>` 同源）。
OUTCOME_REF_TYPES: tuple = ("repair", "bill", "contract")


def make_outcome(state: str, *, expects: str, action: Optional[str] = None,
                 ref: Optional[dict] = None) -> dict:
    """組 `outcome`；值域外一律 ValueError（⛔ 不靜默降級成別的狀態）。"""
    if state not in OUTCOME_STATES:
        raise ValueError(f"outcome.state 不在值域: {state!r}")
    if expects not in OUTCOME_EXPECTS:
        raise ValueError(f"outcome.expects 不在值域: {expects!r}")
    if ref is not None:
        if not isinstance(ref, dict) or ref.get("type") not in OUTCOME_REF_TYPES \
                or not isinstance(ref.get("id"), str) or not ref["id"]:
            raise ValueError("outcome.ref 形狀不合")
        ref = {"type": ref["type"], "id": ref["id"]}
    return {"state": state, "expects": expects, "action": action, "ref": ref}


def default_outcome(result: "TurnResult") -> dict:
    """沒有明設時由 `kind`／`ask_target`／`quick_replies` 決定性導出（模型迴圈的一般出口）。

    第六批 #4：`ask_target ∈ _ASK_TARGET_EXPECTS`（`photo`／`document`）時
    `expects` 改成 `image`／`file`，**且贏過 `quick_replies`**——這一輪要的是一個
    檔案，出幾顆選項鍵不會改變這件事。⚠️ 讀的是**過完所有出口閘之後**的
    `ask_target`（`_finalize` 的呼叫順序），故被 `_apply_ask_target_gate` 歸零的
    非法值不會走到這裡。
    ⚠️ `getattr`：`mcp_facade._outcome_of` 會拿舊的假 runtime 物件進來（那些沒有
    `ask_target` 欄位），⛔ 不讓一個替身的形狀把正式路徑炸掉。
    """
    has_choice = bool(result.quick_replies)
    attachment = _ASK_TARGET_EXPECTS.get(getattr(result, "ask_target", None) or "")
    if result.kind == "handoff":
        return make_outcome("handoff", expects="none")
    if result.kind == "ask":
        return make_outcome("clarifying", expects=attachment or ("choice" if has_choice else "text"))
    return make_outcome("answered", expects=attachment or ("choice" if has_choice else "text"))


def receipt_ref(action: Optional[str], receipt: Any) -> Optional[dict]:
    """receipt → `outcome.ref`（決定性；只認識兩個寫入動作的識別碼欄位）。"""
    if not isinstance(receipt, dict):
        return None
    if action == "repair_create" and receipt.get("repair_id"):
        return {"type": "repair", "id": str(receipt["repair_id"])}
    if action == "bill_due_extend" and receipt.get("bill_id"):
        return {"type": "bill", "id": str(receipt["bill_id"])}
    return None


# ---------------------------------------------------------------------------
# `state["agent"]` 的三個回合狀態鍵（逐字搬自 `runtime.py`）
# ---------------------------------------------------------------------------
#: `state["agent"]` 底下的物件記憶：`{"name": str, "id": str|None}` 或不存在。
#: **封閉兩鍵**——多存一個欄位就會有人把它當成可引用的事實來源。
ESTATE_CARRY_KEY = "estate_carry"

#: `state["agent"]` 底下的會話範圍鍵：`{"type": <select_type>, "estate_id": str}`
#: 或 `None`。**每個 `select:` 回合都會覆寫它**（含失敗回合寫 `None`，L15-05：
#: ⛔ 舊範圍不得殘留到下一次點選）。
SELECT_SCOPE_KEY = "select_scope"

#: `state["agent"]` 底下的**上一回合追問對象**。⚠️ 與 `SELECT_SCOPE_KEY` 同一條
#: 鐵則：**每一個回合出口都要寫**（`_finalize`／`_finish_confirm_turn`／
#: `handoff_cache` 重播共三個寫點），不寫就會殘留上一回合的授權訊號——下游
#: （T3 的肯定語＝授權）讀的是「緊鄰上一回合出口寫入之值」，殘留等於讓一句
#: 「對」去授權一個早就結束的提議。
LAST_ASK_TARGET_KEY = "last_ask_target"


#: DSP-022：`state["agent"]["dialog"]` 保留的訊息數上限（user＋assistant 各一則算 2）。
#: 10 輪對話；超過丟最舊——歷史全靠這裡，⛔ 不另存工具訊息（design 元件 5：dialog 只有 user／assistant）。
DIALOG_MAX_MESSAGES = 20


def _append_dialog(agent_state: dict, user_message: str, answer: str) -> None:
    """DSP-022：回合收尾把「使用者這句＋助理回覆（使用者實際看到的字，固定句亦然）」
    寫回 `dialog`，下一回合 `PromptAssembler._normalized_dialog` 才有歷史可放。
    ⚠️ 真線路 2026-09-05 才發現：run_turn 先前**從未**把當前 `user_message` 放進 messages、
    也從未寫回歷史——模型只看到 system prompt，五題全在對著大綱自由發揮。"""
    dialog = agent_state.setdefault("dialog", [])
    dialog.append({"role": "user", "content": user_message})
    dialog.append({"role": "assistant", "content": answer})
    if len(dialog) > DIALOG_MAX_MESSAGES:
        del dialog[: len(dialog) - DIALOG_MAX_MESSAGES]


#: `state["agent"]["handoff_cache"]` 每 session 的筆數上限（2.6 前置 security
#: review P3）。快取跟著 `form_sessions.collected_data` 一起序列化，無上限等於讓
#: 呼叫端用不同訊息把單一 jsonb 列無限撐大。超過即以 **FIFO** 擠掉最早插入的一筆
#: （dict 保序；⛔ 不是 LRU——重問命中時不重排，那會讓熱門題永遠擠不掉冷門題）。
HANDOFF_CACHE_MAX = 50


def _trim_handoff_cache(cache: dict, limit: int = HANDOFF_CACHE_MAX) -> None:
    """把 `cache` 修到 `limit` 筆以內，先進先出。"""
    while len(cache) > limit:
        cache.pop(next(iter(cache)))


#: 候選細目 id 的形狀（任務 4.1／Plan §2.1-4）：`<audience>/<粗目字母>/<細目 slug>`。
#: 形狀守門在 `_emit_agent_decision` 前，⛔ 不在此另外定義第二套形狀規則
#: （唯一權威在 `canon_parser.py` 的細目 id 產法，這裡只驗形狀、不驗存在性）。
_CANDIDATE_ID_RE = re.compile(r"[a-z_]+/[A-Z]/[a-z0-9-]+")

#: `winning_key_kind` 值域（`services.agent.canon.fine_index.KeyKind` 的三個字面值）。
_VALID_WINNING_KEY_KINDS = frozenset({"title", "phrasing", "content"})


def _candidate_ids_shape_valid(candidate_ids: list, winning_key_kind: dict) -> bool:
    """形狀守門（Plan §2.1-4）：任一 id 不 `fullmatch`、或 `len > K`、或
    `winning_key_kind` 的鍵不在 `candidate_ids` 內、或值不在允許值域 ⇒ `False`。
    """
    if len(candidate_ids) > _CANDIDATE_K:
        return False
    if not all(isinstance(cid, str) and _CANDIDATE_ID_RE.fullmatch(cid) for cid in candidate_ids):
        return False
    id_set = set(candidate_ids)
    for key, value in winning_key_kind.items():
        if key not in id_set or value not in _VALID_WINNING_KEY_KINDS:
            return False
    return True


def _replayed_from(violations: list) -> Optional[str]:
    for v in violations:
        if v.startswith("replayed_from:"):
            return v.split(":", 1)[1]
    return None


def _emit_agent_decision(trace: TurnTrace) -> None:
    """每回合把結構化 trace 落 `decision_snapshot.agent`（design 附錄 B
    不變量 30／任務 2.5）。

    ⚠️ 呼叫點必須是**字面 dict**（不得先組成變數再傳入）——
    `scripts/audit/checks/agent_boundary.py:check_30_decision_snapshot_no_verbatim`
    是靜態掃描這個呼叫的 dict 字面量鍵名，傳變數等於讓這條不變量看不見
    自己在保護什麼。⛔ 鍵集合是封閉白名單（任務 brief），多一鍵就是這條
    不變量要抓的事：無 `answer`／`quote`／`text`／`user_message`。
    `schema_cause`（DSP-029 r13 #7）是封閉列舉值，⛔ 不攜帶任何模型或來源文字。

    任務 4.1（Plan §2.1-4）：寫入前先跑形狀守門——不合格 ⇒ `candidate_ids`／
    `winning_key_kind` 落空、`trace.violations` 補一筆 `candidate_ids_shape_invalid`
    （fail-closed，⛔ 不 raise 進熱路徑）。`trace` 是與 `TurnResult` 共用的同一個
    物件，這裡的修正會反映到呼叫端讀到的 `result.trace` 上。
    """
    candidate_ids = list(trace.candidate_ids)
    winning_key_kind = dict(trace.winning_key_kind)
    if not _candidate_ids_shape_valid(candidate_ids, winning_key_kind):
        candidate_ids = []
        winning_key_kind = {}
        trace.candidate_ids = []
        trace.winning_key_kind = {}
        trace.violations.append("candidate_ids_shape_invalid")

    usage_metering.set_agent_decision(
        {
            "trace_id": trace.trace_id,
            "tool_calls": [
                {
                    "name": tc.name,
                    "args_summary": tc.args_summary,
                    "ms": tc.ms,
                    "status": tc.status,
                    "n_items": tc.n_items,
                }
                for tc in trace.tool_calls
            ],
            "llm_calls": trace.llm_calls,
            "prompt_tokens": trace.prompt_tokens,
            "completion_tokens": trace.completion_tokens,
            "verifier": [
                {
                    "reason": v.reason,
                    "sent": v.sent,
                    "term_id": v.term_id,
                    "quote_len": v.quote_len,
                    "schema_cause": v.schema_cause,
                }
                for v in trace.verifier
            ],
            "final_kind": trace.final_kind,
            "handoff_reason": trace.handoff_reason,
            "latency_ms": trace.latency_ms,
            "rules_sha": trace.rules_sha,
            "outline_sha": trace.outline_sha,
            "candidate_ids": candidate_ids,
            "winning_key_kind": winning_key_kind,
            "miss_kind": trace.miss_kind,
            # DSP-038／S-11：確認鏈的稽核兩鍵（⛔ 皆非原文，見 `TurnTrace` 註記）。
            "pending_id": trace.pending_id,
            "receipt_id": trace.receipt_id,
            # W8 (1)／S8-6：⛔ 只有型別與「有沒有 ref」，**沒有 ref 原值**。
            "select_type": trace.select_type,
            "has_ref": trace.has_ref,
            "slot_written": trace.slot_written,
            # T1／security r1 #7：⛔ 只有 bool，**沒有進場句原文**。
            "has_context": trace.has_context,
            # U3：⛔ 只有種類與命中數，**沒有 ref／關鍵字原文**。
            "pre_lookup": trace.pre_lookup,
            # V2：⛔ 只有 bool，**沒有編號原值**。
            "has_recent_refs": trace.has_recent_refs,
            # R1b：⛔ 只有類別名→整數，**沒有任何原文**（見 `TurnTrace` 該欄註記）。
            "verifier_observed_counts": trace.verifier_observed_counts,
            "violations": trace.violations,
            "replayed_from": _replayed_from(trace.violations),
        }
    )
    # 日誌只印 kind／拒因／計數，⛔ 不印 answer／quote 原文（任務 brief）。
    logger.info(
        "agent_turn trace_id=%s kind=%s handoff_reason=%s tool_calls=%d "
        "verifier_rejects=%d llm_calls=%d",
        trace.trace_id,
        trace.final_kind,
        trace.handoff_reason,
        len(trace.tool_calls),
        sum(1 for v in trace.verifier if not v.ok),
        trace.llm_calls,
    )


# ---------------------------------------------------------------------------
# R1：保留 id／輸入快照／回合累加器（Plan §0c）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReservedCallIds:
    """本回合**保留的 `tool_call_id` 集合**（S2 §3／DSP-029 r13 #3）。

    ⚠️ 九個 id 一律在回合最開始由 nonce **無條件**派生，⛔ 不等到「這回合真的
    有影像／完成動作／進場句／…」才算——模型能不能偽造一個同名 id 不該取決於
    這回合是否真的用到它（那會讓「沒有影像時 `img-…` 可以被模型自己造」這種
    邊界情況變成漏洞）。`OUTLINE_TOOL_CALL_ID` 是固定字串，一併收進 `all`；
    工具迴圈只認 `all` 這一個集合。
    """

    image: str
    completed: str
    entry: str
    affirmative: str
    context_empty: str
    pre_lookup: str
    recent_refs: str
    document: str
    estate_carry: str
    all: frozenset

    @classmethod
    def from_nonce(cls, nonce: str) -> "ReservedCallIds":
        head = nonce[:8]
        ids = {
            "image": f"img-{head}",
            "completed": f"done-{head}",
            "entry": f"entry-{head}",
            "affirmative": f"aff-{head}",
            "context_empty": f"ctx-{head}",
            "pre_lookup": f"pre-{head}",
            "recent_refs": f"ref-{head}",
            "document": f"doc-{head}",
            "estate_carry": f"est-{head}",
        }
        return cls(**ids, all=frozenset({OUTLINE_TOOL_CALL_ID, *ids.values()}))


@dataclass
class TurnInputsSnapshot:
    """段落產生後寫入、之後**唯讀**的 trace 輸入（Plan §0c r2 #4）。

    ⚠️ `has_context` 是 `bool(entry_text)` 的導出值——對帳時以 `entry_text` 為準
    （Plan §0c 明列）。`outline_sha`／`rules_sha` 在一個回合內不變（`outline` 於
    `_select_outline` 之後不再重新綁定，`verifier.rules_sha` 是實例屬性），故在
    這裡算一次即可，⛔ 不在每個 trace 建構點各算一次。
    """

    candidate_ids: list = field(default_factory=list)
    winning_key_kind: dict = field(default_factory=dict)
    miss_kind: Optional[str] = None
    entry_text: str = ""
    has_recent_refs: bool = False
    pre_lookup_trace: Optional[dict] = None
    doc_trace: dict = field(default_factory=dict)
    outline_sha: str = ""
    rules_sha: str = ""

    @property
    def has_context(self) -> bool:
        return bool(self.entry_text)


@dataclass
class TurnAccumulator:
    """一次 `_run_turn_body` 的**全部可變狀態**（Plan §0c）。

    ⚠️ 規則（⛔ 不得繞過）：
    - 整數計數（`llm_calls`／`prompt_tokens`／`completion_tokens`／`attempt_no`）
      一律**就地加**在這裡的欄位上，⛔ 不再重新綁定區域變數——重新綁定就會讓
      「走固定句出口時 trace 反映的是最新值」這條變成巧合。
    - `violations`／`tool_call_records`／`verifier_verdicts`／`messages`／
      `tool_results_by_id`／`scope_counts` 一律傳**同一個物件**，⛔ 不在段邊界複製。
    """

    counters: BudgetCounters = field(default_factory=BudgetCounters)
    scope_counts: dict = field(default_factory=lambda: {"in": 0, "out": 0})
    violations: list = field(default_factory=list)
    tool_call_records: list = field(default_factory=list)
    verifier_verdicts: list = field(default_factory=list)
    messages: list = field(default_factory=list)
    tool_results_by_id: dict = field(default_factory=dict)
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    #: tasks 4.3c：模型「最終輸出」嘗試計數，從 1 起（工具呼叫不計）
    attempt_no: int = 0
    cache_key: str = ""
    nonce: str = ""
    trace_id: str = ""
    start: float = 0.0
    #: R1b：Verifier **觀察到而未擋**的類別 → 次數，逐次 verdict 就地累加
    #: （⛔ 不重新綁定；同 §0c 的整數計數紀律）。只有一般出口的 trace 讀它。
    verifier_observed_counts: dict = field(default_factory=dict)
    snapshot: TurnInputsSnapshot = field(default_factory=TurnInputsSnapshot)

    @property
    def reserved(self) -> ReservedCallIds:
        """九個保留 id（由 `nonce` 派生；同一個 nonce 每次派生的結果相同）。"""
        return ReservedCallIds.from_nonce(self.nonce)

    # -- 九段資料注入的唯一落點 ------------------------------------------
    def inject(
        self, label: str, call_id: str, text: str, *,
        citable: bool, source: str, data: Optional[dict] = None,
    ) -> None:
        """把一段程式組的資料注入本回合：登記進 `tool_results_by_id` ＋ 追一則
        `role="user"` 的資料段訊息（`wrap_provenance_data`，同回合 nonce）。

        ⚠️ **一定要登記進 `tool_results_by_id`**：不登記的話模型引用它會落
        `ref_source_not_found`，而正確的訊號是 `SOURCE_NOT_CITABLE`。
        ⚠️ `citable` 是這九段唯一的差別旗標——呼叫端進場句／空會話註記／肯定語
        承接／最近編號／物件記憶是 `False`（程式組的會話記憶，⛔ 不是可引用的
        事實來源），影像／文件／前置查詢／完成動作是 `True`。
        ⛔ **順序由呼叫端決定**：這一支不排序、不判斷要不要注入（那些條件各段
        自己判），它只保證九段的**形狀**只有一種。
        """
        self.tool_results_by_id[call_id] = ToolResult(
            ok=True,
            data=dict(data) if data else {},
            provenance=[Provenance(source=source, text=text, citable=citable)],
            text_for_model="",
        )
        self.messages.append(
            {
                "role": "user",
                "content": wrap_provenance_data(
                    label, call_id, [(source, provenance_units(text))], self.nonce,
                ),
            }
        )

    # -- 兩個 trace／result 建構點 ---------------------------------------
    def build_trace(
        self, *, final_kind: str, handoff_reason: Optional[str],
        clock: Callable[[], float], copy_lists: bool,
        observed_counts: Optional[dict] = None,
    ) -> TurnTrace:
        """本回合的 `TurnTrace`。

        ⚠️ `copy_lists` 逐字保留原本兩個建構點的差異：固定句出口（`_build_fixed`）
        傳的是 `list(...)`／`dict(...)` 副本，模型迴圈的一般出口傳的是**同一個
        物件**（`_emit_agent_decision` 的形狀守門會就地改 `trace.candidate_ids`，
        而那個修正必須反映到呼叫端讀到的 `result.trace` 上）。⛔ 不得統一。
        """
        snap = self.snapshot
        return TurnTrace(
            trace_id=self.trace_id,
            tool_calls=list(self.tool_call_records) if copy_lists else self.tool_call_records,
            llm_calls=self.llm_calls,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            verifier=list(self.verifier_verdicts) if copy_lists else self.verifier_verdicts,
            final_kind=final_kind,
            handoff_reason=handoff_reason,
            latency_ms=int((clock() - self.start) * 1000),
            violations=list(self.violations) if copy_lists else self.violations,
            rules_sha=snap.rules_sha,
            outline_sha=snap.outline_sha,
            candidate_ids=list(snap.candidate_ids),
            winning_key_kind=dict(snap.winning_key_kind),
            miss_kind=snap.miss_kind,
            has_context=snap.has_context,
            has_recent_refs=snap.has_recent_refs,
            pre_lookup=snap.pre_lookup_trace,
            # R1b：⛔ 只有取得 verdict 的一般出口傳實值（Plan §0b）；其餘出口留空 dict。
            verifier_observed_counts=dict(observed_counts or {}),
            # W9 U2：文件回合四鍵（⛔ 無任何欄位值）。
            **snap.doc_trace,
        )

    def build_fixed(self, reason: str, *, clock: Callable[[], float]) -> TurnResult:
        """固定句轉人出口（原 `_run_turn_body` 的閉包 `_build_fixed`，逐字搬移）。"""
        message_text = effective_handoff_message(None)
        channel = effective_handoff_channel(None)
        handoff_dict = {
            "reason": reason,
            "fact_class": FactClass.other.value,
            "channel": channel,
            "message": message_text,
        }
        return TurnResult(
            kind="handoff",
            answer=message_text,
            handoff=handoff_dict,
            quick_replies=[],
            trace=self.build_trace(
                final_kind="handoff", handoff_reason=reason,
                clock=clock, copy_lists=True,
            ),
        )
