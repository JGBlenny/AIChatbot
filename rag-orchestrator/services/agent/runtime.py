"""`AgentRuntime`（spec agentic-mcp-orchestration・任務 2.1｜design 元件 1）。

模型迴圈：Chat Completions tool loop（`parallel_tool_calls=false`）＋預算表
＋Verifier 拒因重寫＋同題重問快取。契約基準見
`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 1（`Identity`／
`Budget`／`TurnTrace`／`AgentRuntime`／`TurnResult`、預算計數表、同題重問
快取段）。

**2.5 收尾註記（本檔已接妥的三條，取代下方舊的「刻意留白」敘述）**：
- `AgentOutput`／`VerifierVerdict`／`Sentence` 的權威定義已
  搬到 `services/agent/output_schema.py`（任務 2.3），本檔全部改
  `from services.agent.output_schema import ...`，⛔ 不再本地重複定義。
- 工具回傳已包裝成資料段才進 `role="tool"` 訊息：**有 provenance** 的工具走
  `wrap_provenance_data(name, tool_call_id, [(source, provenance_units(text))…], nonce)`
  （DSP-029a：每個片段行首帶 `[{nonce}:{tool_call_id}:{source}§{i}]`，模型引用時
  把整串標記原樣照抄進 `Sentence.refs`）；
  **無 provenance** 的工具（handoff／session.slots／confirm）維持
  `wrap_tool_data(name, text_for_model, nonce)`，其 source 視為不存在、不可引用。
- `assembler.build(...)` 與 `assembler.build_messages(...)` 二選一：本檔選
  `build_messages()`——它直接回傳 `list[dict]`，與 `AssemblerProtocol` 的
  既有形狀（本檔、`services/agent/mcp_facade.py` 等呼叫端）一致，不必額外
  拆 `BuiltPrompt(messages, meta)`；`outline_sha`／`rules_sha` 這兩個 trace
  欄位本檔已經直接從 `outline.sha256`／`self.verifier.rules_sha` 讀（見下方
  `_outline_sha`／`_rules_sha`），不需要 `build()` 回傳的 `PromptMeta`。

**本任務刻意留白（由後續任務補上，⛔ 不是這裡漏做）**：
- `AgentOutput.model_json_schema()` 轉成 OpenAI strict `json_schema` 目前只
  在頂層補 `additionalProperties: false`／`required`，未遞迴處理巢狀
  `Sentence`／`$defs`——這支任務全程用假 provider（⛔ 不呼叫
  真 OpenAI），沒有機會踩到 strict 校驗的實際邊界；2.2 接真線路時要驗一次。
- HandoffReason（`services.presales_gate.HandoffReason`）是封閉 `str, Enum`
  （`no_grounding`／`sensitive_no_grounding`／`llm_mentioned_handoff`／
  `partial_grounding`），**沒有** `tool_unavailable`／`budget_exhausted` 這兩個
  design 要求的新值。依派工 brief 指示：⛔ 不改 `presales_gate.py`（那是紅線
  檔案外的既有正本，擅自加值等於在別的 spec 的封閉集合上開洞）。這裡改用
  **相容 dict**（不經 `Handoff`/`build_handoff`，因為那條路徑會把 reason
  塞進 enum 建構式而炸掉）直接組裝 `{"reason","fact_class","channel","message"}`，
  `fact_class` 固定填 `FactClass.other`（這兩種 handoff 是 Runtime 自己決定
  轉人，不是模型判斷出的事實類別）。**需要 2.4 擴充**：若 2.4／`handoff.request`
  工具要把這兩個 reason 值也送進同一個 `HandoffReason` enum，屆時要嘛把
  enum 加值（需要業主過一次「封閉集合開放」的裁決），要嘛統一改成本檔的
  dict 慣例、`Handoff` dataclass 降級為只給經 `build_handoff` 那四種既有原因
  使用。
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import string
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional, Protocol

from pydantic import ValidationError

from services import usage_metering
from services.agent.budget import Budget, BudgetCounters
from services.agent.affirmative import is_affirmative
from services.agent.completed_actions import (
    COMPLETED_ACTIONS_KEY,
    completed_actions_line,
    record_completed_action,
    sanitize_data_piece,
)
from services.agent.confirm_card import (
    ACTION_FAILED_TEXT,
    CANCELLED_TEXT,
    CONFIRMATION_REQUIRED_TEXT,
    CONFIRM_ACTIONS,
    fields_before_today,
    receipt_id_of,
    render_receipt,
)
from services.agent.canon.candidate_selector import CandidateSelector
from services.agent.canon.candidate_selector import K as _CANDIDATE_K
from services.agent.canon.canon_assembler import build_canon_toc, canon_visible, get_canon
from services.agent.identity import (
    DEFAULT_ENTRY_CHANNEL,
    Identity,
    Stage,
    derive_identity_source,
)
from services.agent.mcp_facade import current_stage
from services.agent.outline import CandidateOutlineDoc, resolve_vendor_business_types
from services.agent.output_schema import ASK_TARGETS, AgentOutput, VerifierVerdict
from services.agent.prompt_assembler import new_nonce, wrap_provenance_data, wrap_tool_data
from services.agent.provenance_units import (  # OUTLINE_TOOL_CALL_ID 下沉至葉模組（DSP-029 落地取捨④）
    OUTLINE_TOOL_CALL_ID,
    provenance_units,
    resolve_refs,
)
from services.agent.text_norm import normalize_terminal_punctuation
from services.agent.tools.confirm import (
    CONFIRM_QUICK_REPLY_VALUES,
    CONFIRM_SPEC,
    CONFIRM_VALUE_SEP,
    payload_digest,
    redeem_pending,
    sha256_hex,
)
from services.agent.tools.jgb2 import _candidates_text as _jgb2_candidates_text
from services.agent.tools.registry import Provenance, ToolRegistry, ToolResult, tool_name_from_openai
from services.agent.tools.session import write_slot
from services.conversational_config import (
    effective_handoff_channel,
    effective_handoff_message,
)
from services.presales_gate import SENSITIVE, FactClass, HandoffReason
# ⚠️ **import 模組、⛔ 不 `from … import _today`**：兌現閘要在呼叫點取時鐘，
# 與 `tools/confirm` 的閘一同一支函式、同一個時鐘（S1）。
from services.jgb import bills

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# `AgentOutput`／`VerifierVerdict` 權威定義在 `services/agent/output_schema.py`
# （任務 2.3）；本檔只 import，⛔ 不再本地重複定義（2.5 收尾註記，見模組
# docstring）。`Sentence` 本檔不直接使用，不重複 import。
# ---------------------------------------------------------------------------



#: DSP-020：大綱章節在回合開始即以這個保留 `tool_call_id` 預載成一筆 provenance，
#: 模型引用大綱時照抄的標記裡第二段就是它、第三段是章節 id（`outline:*`），
#: 不必先呼叫 `kb.get("outline:*")` 多花一輪。⚠️ 影子 2026-09-05 第一筆真流量
#: 就是因為缺這條——模型照鐵則引用大綱、Verifier 卻只認工具回傳 ⇒ 兩次
#: QUOTE_NOT_VERBATIM → budget_exhausted。OpenAI 的 tool_call id 一律 `call_…`，
#: 若模型偽造同名 id，下方以 `_seed_outline_provenance` 的結果為準、⛔ 不覆寫。

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



def _seed_outline_provenance(outline: Any) -> Optional[ToolResult]:
    """把 `OutlineDoc.sections` 轉成一筆 `ToolResult`（只有 provenance）。
    無大綱或無章節 ⇒ None（pm／tenant 目錄 `citable=False` 照樣預載——
    Verifier 會以 SOURCE_NOT_CITABLE 拒，語義與 `kb.get("outline:*")` 一致）。"""
    sections = getattr(outline, "sections", None) if outline is not None else None
    if not sections:
        return None
    provs = [
        Provenance(
            source=str(sec.id),
            text=str(sec.text),
            citable=bool(getattr(sec, "citable", True)),
        )
        for sec in sections
    ]
    return ToolResult(ok=True, data={"sections": len(provs)}, provenance=provs, text_for_model="")


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


def _candidate_query(user_message: str, dialog: list) -> str:
    """查詢＝`user_message` ＋ `dialog` 中最後一則 `role=="user"` 的 `content`
    （無則單句），單一空格連接（Plan §2.1-2 程式規則）。⛔ 不 log 這個字串。
    """
    last_user_content: Optional[str] = None
    for msg in reversed(dialog or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_content = msg.get("content")
            break
    if last_user_content:
        return f"{user_message} {last_user_content}"
    return user_message


class VerifierProtocol(Protocol):
    def verify(
        self,
        out: AgentOutput,
        tool_results: dict[str, ToolResult],
        user_message: str,
        handoff: Optional[dict],
        *,
        resolved: dict[int, str],
        resolve_errors: dict[int, str],
    ) -> VerifierVerdict: ...


class AssemblerProtocol(Protocol):
    def build_messages(
        self,
        identity: Identity,
        outline: Any,
        slots: dict,
        dialog: list[dict],
        tool_specs: list[dict],
        nonce: str,
    ) -> list[dict]: ...


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


#: DSP-038／W3：待確認動作的 session 狀態鍵。
#: `agent_state["pending_confirm"][pending_id] = {action, payload, card_sha256, receipt?}`
#: ——經既有 `state_store` 落 `form_sessions.collected_data`，與既有 `bill_ref`／
#: `contract_ref` 槽位同一敏感等級與同一保留期（DSP-038-4）。
#: ⛔ **token 不在其中**（r1 B2 的 P1 處置：token 落 session 狀態＝一份靜態憑證面）。
PENDING_CONFIRM_KEY = "pending_confirm"

#: 每 session 保留的待確認筆數上限（比照 `HANDOFF_CACHE_MAX` 的理由：這份狀態
#: 跟著 `collected_data` 一起序列化，無上限等於讓呼叫端把單一 jsonb 列撐大）。
#: 超過即 **FIFO** 擠掉最早插入的一筆（dict 保序）。
PENDING_CONFIRM_MAX = 20

#: `confirm.request` 的工具名（⛔ 不抄字面量，值域由 `CONFIRM_SPEC` 持有）。
CONFIRM_TOOL_NAME = CONFIRM_SPEC["name"]

#: 使用者按下按鈕送回來的機器值：`^confirm_(submit|edit|cancel):<16 位十六進位>$`。
#: ⚠️ **等值**比對（`fullmatch`、無前後綴）——⛔ 不做子字串比對：那會讓
#: 「confirm_submit:abcd… 這是什麼意思？」這種自由文字誤觸發一次真實寫入。
#: 三個前綴**由 `CONFIRM_QUICK_REPLY_VALUES` 組出來**（那組常數又轉引
#: `conversational_engine._QR_*`），⛔ 不在此另抄字面量。
_CONFIRM_VALUE_RE = re.compile(
    r"^(?:%s)%s([0-9a-f]{16})$"
    % (
        "|".join(re.escape(v) for v in CONFIRM_QUICK_REPLY_VALUES),
        re.escape(CONFIRM_VALUE_SEP),
    )
)


def _parse_confirm_value(message: Any) -> Optional[tuple]:
    """`"confirm_submit:0123456789abcdef"` → `("confirm_submit", "0123…")`；不是機器值 ⇒ `None`。"""
    if not isinstance(message, str):
        return None
    m = _CONFIRM_VALUE_RE.match(message)
    if m is None:
        return None
    verb, pending_id = message.split(CONFIRM_VALUE_SEP, 1)
    return verb, pending_id


# ════════════════════════════════════════════════════════════════════
# W8 (1)：LIFF 清單點選的機器值 `select:<type>:<id>`（R10-c／DSP-042）
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ **這一段的存在理由**：LIFF 只做入口與呈現，使用者從清單點一列時送回來的是
#    機器值，不是自由文字。既然目標那一列已經確定，就 ⛔ 不該再讓模型去猜要查
#    哪一筆——這一段從頭到尾沒有一次 `chat.completions.create`。
#
# ⚠️ **已知取捨（契約措辭，S8-10）**：機器值真人也打得出來。最壞情況＝查到
#    **整個 role 範圍內**（含其他租客）的資料——這在 pm 單證的既有身分閘下本
#    來就成立（`jgb2.py:_identity_gate_ok`），並非本段新增的揭露面。
#    ⛔ 日後若對 tenant 開 `agent.turn`，`select:` 必須另加雙證＋viewer 圈定。

#: `<type>` → 工具名。**封閉表**（S8-4：工具名複數、`<type>` 單數，兩者不對應，
#: ⛔ 不得用字串拼接推導出工具名）。
#: 第一版只開 bill／contract／repair（S8-13）：`estate`／`meter` 的 `ref` 在工具層
#: 是 keyword 語義，開了會把使用者點的那一列當成模糊字串去搜。
_SELECT_TYPE_TO_TOOL: dict[str, str] = {
    "bill": "jgb2.query.bills",
    "contract": "jgb2.query.contracts",
    "repair": "jgb2.query.repairs",
}

#: `<type>` → 該域的**最小揭露** face（S8-1／S8-2）。
#: ⛔⛔ **這張表是 email 面的唯一控制**：`_verify_routes` 只認 URL／電話／導流，
#:     **沒有 email 樣式**。contracts 的「簽署排障」face 的 facts 含租客
#:     email／電話明文，繞過模型即沒有 Verifier 會擋 ⇒ ⛔ 不得把任何一個值
#:     換成揭露面更大的 face。`tests/unit/agent/test_select_entry_req.py`
#:     釘住「三個 face 的 facts 不含 `@`」，並以「簽署排障」當正對照。
_SELECT_DEFAULT_FACE: dict[str, str] = {
    "bill": "帳單異常",
    "contract": "續約",
    "repair": "修繕進度",
}

#: 使用者從清單點一列時送回來的機器值：`select:<type>:<id>`。
#: `<type>` 由 `_SELECT_TYPE_TO_TOOL` 的鍵**組出來**（⛔ 不另抄字面量，兩張表
#: 與這條正則的值域因此不可能分岔）；`<id>` `^[A-Za-z0-9_-]{1,32}$`。
_SELECT_VALUE_RE = re.compile(
    r"select:(%s):([A-Za-z0-9_-]{1,32})"
    % "|".join(re.escape(t) for t in _SELECT_TYPE_TO_TOOL)
)

#: 查無／不在範圍／降級 一律回**同一句**（⛔ 不細分——細分等於用回話的差別
#: 告訴呼叫端「這筆存在但你看不到」）。
SELECT_NOT_FOUND_TEXT = "查無此筆"

#: 進 dialog 的**程式摘要**（S8-3：第三方 facts 原文 ⛔ 不以 assistant 身分
#: 進歷史——那等於把下游系統的自由文字餵回下一回合的模型上下文）。
SELECT_DIALOG_SUMMARY = "已提供 {select_type} {ref} 的資料"


# ════════════════════════════════════════════════════════════════════
# U3：純編號／短名詞一句的程式前置查詢
#（Plan `inputs/plan-walkthrough-fixes-batch3-20260909.md` §4）
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ **存在理由**：使用者整句只打一個編號或短名詞（「756248」「信仰」）時，
#    模型手上沒有既有的定義句可用，唯一合理反應是反問「哪一種類型」
#    （第二批 r1–r3 3/3 實測）。這一段在模型迴圈**之前**先用同一套 registry
#    四步紀律試著查一次，把結果當可引用資料段注入——模型仍自己決定怎麼答，
#    只是不必再猜要查哪一域。
# ⛔ 不代模型作答、不改變 outcome；⛔ 不直呼 `tools/jgb2.py`。

#: 觸發字集的**封閉標點集合**（ASCII `string.punctuation` ＋常見全形／CJK
#: 標點）。⛔ 不用開放語義的「非字母數字就當標點」——那會把合法短名詞用到的
#: 任何符號都算進去，值域必須看得見全部成員。
_PRE_LOOKUP_PUNCTUATION: frozenset = frozenset(string.punctuation) | frozenset(
    "，。！？、；：「」『』（）【】《》〈〉—…～·"
    "＂＇｀＾＿｜～｛｝［］＜＞＠＃＄％＆＊＋－／＝｡､"
)
_PRE_LOOKUP_TRIM_CHARS = "".join(sorted(_PRE_LOOKUP_PUNCTUATION))

#: 純數字觸發（trigger A）：4–9 位 ASCII 數字。
_PRE_LOOKUP_ID_RE = re.compile(r"^[0-9]{4,9}$")

#: `ref` 過封閉字集（security F9／S8-6：同 `_SELECT_VALUE_RE` 的 `<id>` 值域）。
_PRE_LOOKUP_REF_CHARSET_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")

#: 查無／範圍外一律回**同一句**（L15-13：不細分——細分等於用回話的差別揭露
#: 「這筆存在但你看不到」）。
PRE_LOOKUP_NOT_FOUND_TEXT = "系統裡查不到這個編號或名稱。"

#: `ToolResult.error` 裡唯一算「真的查過、確定沒有」的值——工具層 `_no_match()`
#: 固定回這個字串（`tools/jgb2.py`）。其餘錯誤碼（`TOOL_TIMEOUT`／
#: `RATE_LIMITED`／`INVALID_INPUT`）與例外一律是「沒查成」，⛔ 不得也講成
#: 「查不到」——那是把「沒查」講成「查過沒有」，一樣是假話。
_PRE_LOOKUP_NOT_FOUND_ERROR = "NO_MATCH"

#: 前置查詢資料段的來源代碼與工具標籤——同影像事實／完成動作記憶行／進場句
#: 同一套注入紀律。一回合只有一段，序號固定 1。
PRE_LOOKUP_PROVENANCE_SOURCE = "pre_lookup:query#1"
PRE_LOOKUP_LABEL = "pre_lookup.query"

#: trigger A 依序嘗試的域（brief 逐字順序：帳單／修繕單／合約）；
#: `_SELECT_TYPE_TO_TOOL`／`_SELECT_DEFAULT_FACE` 是唯一的工具名／face 來源，
#: ⛔ 不另抄字面量。
_PRE_LOOKUP_ID_TOOL_ORDER: tuple[str, ...] = ("bill", "repair", "contract")

#: trigger B 唯一開放的域（S8-13：⛔ 不開 `estate`／`meter` 的新 `ref` 語義，
#: 這裡走的是既有的 keyword 查詢，不是 `select:` 那套 ref 語義）。
_PRE_LOOKUP_ESTATE_TOOL = "jgb2.query.estates"
_PRE_LOOKUP_ESTATE_FACE = "物件現況診斷"


def _pre_lookup_strip_ws_punct(text: str) -> str:
    """去頭尾空白與標點（封閉字集），交替去除到穩定——處理「標點＋空白」交錯
    夾在頭尾的情形（例：「 ，756248。 」）。"""
    prev = None
    current = text
    while current != prev:
        prev = current
        current = current.strip()
        current = current.strip(_PRE_LOOKUP_TRIM_CHARS)
    return current


def _pre_lookup_trigger(message: str) -> Optional[tuple[str, str]]:
    """U3 觸發判定。回傳 `(kind, candidate)`；不觸發 ⇒ `None`。

    `kind` ∈ `{"id", "keyword"}`；`candidate` 已去頭尾空白與標點，⛔ 尚未過
    後續字集檢查——`id` 走 `_PRE_LOOKUP_REF_CHARSET_RE`、`keyword` 走
    `sanitize_data_piece`，兩者都在查詢那一步做。

    ⚠️ **`AFFIRMATIVE_WORDS` 整句一律不觸發**（重用 T3 既有的凍結集合，⛔ 不是
    另開一組詞表特例）：「對」「好」這類單字肯定語本身就落在 trigger B 的
    字集裡（短、無標點數字空白），但它們的既有語意是回應上一句提議
    （`is_affirmative`／`CALLER_AFFIRMATIVE_*`），不是使用者在打一個編號或
    名稱——兩段各自的資料段互不相干，讓肯定語又觸發一次查詢只是白打一次
    API 並注入一段無關的「查無」句。
    """
    if not isinstance(message, str):
        return None
    if is_affirmative(message):
        return None
    core = _pre_lookup_strip_ws_punct(message)
    if not core:
        return None
    if _PRE_LOOKUP_ID_RE.match(core):
        return "id", core
    if len(core) <= 6:
        if any(ch.isdigit() for ch in core):
            return None
        if any(ch in _PRE_LOOKUP_PUNCTUATION for ch in core):
            return None
        if any(ch.isspace() for ch in core):
            return None
        return "keyword", core
    return None


# ════════════════════════════════════════════════════════════════════
# L15 (a)：清單進場後的**會話範圍**（戶＝物件 `estate_id`；業主 2026-09-08 裁）
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ **程式判定、⛔ 不交模型**（`feedback_no_llm_mechanical_decode`）：「是不是
#    同一戶」是 `estate_id` 等值，封閉可算；讓模型判等於把資料邊界交給一個會
#    被說服的東西。
# ⚠️ **fail-closed**：有範圍而某一筆算不出 `estate_id`（缺欄位／`None`）一律
#    當成範圍外，⛔ 不放行——放行的失敗方向是別戶資料進答案。

#: `state["agent"]` 底下的會話範圍鍵：`{"type": <select_type>, "estate_id": str}`
#: 或 `None`。**每個 `select:` 回合都會覆寫它**（含失敗回合寫 `None`，L15-05：
#: ⛔ 舊範圍不得殘留到下一次點選）。
SELECT_SCOPE_KEY = "select_scope"

#: L15 (a)⑤：範圍外時使用者看到的**指路固定句**。單一句、對所有受眾一體適用；
#: ⛔ 無任何插值（L15-13：帶 id／名稱等於用回話的差別揭露存在性）。
SCOPE_EXIT_TEXT = "這個對話只看你點選的那一戶；要查別戶請回清單點那一戶。"

#: L15 (a)③：範圍外的工具結果替換成的**工具訊息**（模型看到的那一份）。
#: ⛔ 原 facts 不進 messages／provenance；⛔ 這一段不結束回合（L15-09：模型還要
#: 能把同一句裡查得到的那一題答完）。
SCOPE_TOOL_TEXT = "（這一筆不在本對話的範圍內）"

_JGB2_QUERY_PREFIX = "jgb2.query."

#: L15-01／L15-02：**候選清單**要過濾的封閉域表 → 該域列上代表「戶」的欄位。
#: ⛔ 表外的域（accounts）不過濾、不比對——它的列根本沒有物件維度，套過濾＝
#: 必空＝把整個域誤判成範圍外（plan-verifier r2）。
_SCOPE_CANDIDATE_ROW_KEY: dict[str, str] = {
    "jgb2.query.bills": "estate_id",
    "jgb2.query.contracts": "estate_id",
    "jgb2.query.repairs": "estate_id",
    "jgb2.query.meters": "estate_id",
    "jgb2.query.estates": "id",
}


def _scope_estate_id(agent_state: dict) -> Optional[str]:
    """本回合的會話範圍物件 id；沒有範圍（聊天進場／select 失敗）⇒ `None`。"""
    scope = agent_state.get(SELECT_SCOPE_KEY)
    if not isinstance(scope, dict):
        return None
    estate_id = scope.get("estate_id")
    return str(estate_id) if estate_id is not None and estate_id != "" else None


def _scope_replace_result(result: ToolResult) -> None:
    """把**同一個** `ToolResult` 物件改成「不在範圍內」的空殼。

    ⚠️ 三份都要換（plan-verifier r1）：`text_for_model` 是無 provenance 時模型看
    到的字，`provenance` 是有 provenance 時模型**實際**看到的字，`data` 是引用
    解析與下游計數看的那一份。只換其中一份＝fail-open。
    """
    result.ok = True
    result.error = None
    result.data = {"facts": "", "candidates": None, "skip_refine": True}
    result.provenance = []
    result.text_for_model = SCOPE_TOOL_TEXT


def _enforce_tool_scope(
    name: str, result: ToolResult, scope_estate_id: str,
    query: Optional[str], violations: list,
) -> Optional[str]:
    """L15 (a)③：把一次 `jgb2.query.*` 的結果對齊會話範圍。

    回傳 `"in"`（同戶）／`"out"`（範圍外，`result` 已就地替換）／`None`（不比對：
    非 jgb2 查詢、無物件維度的回傳、表外域的候選）。
    """
    if not name.startswith(_JGB2_QUERY_PREFIX):
        return None
    data = result.data if isinstance(result.data, dict) else {}

    # (3a) 單筆：`_ok_single(scoped=True)` 帶的 `scope` 鍵。
    scope = data.get("scope")
    if isinstance(scope, dict):
        row_estate = scope.get("estate_id")
        if row_estate is None:
            # L15-06：有範圍而列上算不出戶 ⇒ fail-closed，且要在 trace 看得見。
            violations.append("select_scope_unknown")
            _scope_replace_result(result)
            violations.append("select_scope_exit")
            return "out"
        if str(row_estate) != scope_estate_id:
            _scope_replace_result(result)
            violations.append("select_scope_exit")
            return "out"
        return "in"

    # (3b) 候選清單：封閉五域先過濾再重繪；⛔ 表外域不動。
    row_key = _SCOPE_CANDIDATE_ROW_KEY.get(name)
    candidates = data.get("candidates")
    if row_key is not None and isinstance(candidates, list):
        kept = [
            row for row in candidates
            if isinstance(row, dict)
            and row.get(row_key) is not None
            and str(row.get(row_key)) == scope_estate_id
        ]
        if not kept:
            _scope_replace_result(result)
            violations.append("select_scope_exit")
            return "out"
        domain = name[len(_JGB2_QUERY_PREFIX):]
        text = _jgb2_candidates_text(domain, query, kept)
        data["candidates"] = kept
        result.text_for_model = text
        if result.provenance:
            result.provenance[0].text = text
        return "in"

    # (3c) 無 scope 鍵、也不是要過濾的候選（分類樹／accounts／NO_MATCH）⇒ 不比對。
    return None


def _apply_scope_exit(result: TurnResult, *, scope_in: int, scope_out: int) -> TurnResult:
    """L15 (a)④：**唯一接句點**——模型迴圈產出的每一個 `TurnResult` 都經這裡。

    - 全部範圍外（`scope_out>0 and scope_in==0`）⇒ 整個答案換成固定句、
      `kind="answer"`、`handoff=None`（⛔ 不進 handoff cache：`_finalize` 只對
      `trace.final_kind == "handoff"` 寫快取，故這裡連 `final_kind` 一起改）。
    - 部分範圍外 ⇒ 答案末尾接一行固定句。
    - 沒有範圍外 ⇒ 逐字不動。
    """
    if scope_out <= 0:
        return result
    if scope_in == 0:
        result.answer = SCOPE_EXIT_TEXT
        result.kind = "answer"
        result.handoff = None
        result.trace.final_kind = "answer"
        result.trace.handoff_reason = None
        result.outcome = make_outcome("out_of_scope", expects="none")
        return result
    result.answer = result.answer.rstrip() + "\n" + SCOPE_EXIT_TEXT
    return result


#: S4 §5：零查詢轉人的追問固定句。單一句、⛔ 無任何插值（同 `SCOPE_EXIT_TEXT`
#: 的紀律——帶物件名稱等於用回話的差別揭露存在性）。
#: 非敏感的轉人原因（封閉集合）：兩道降級閘與 T2 改寫提示都只認這一組——
#: `no_grounding`（模型自報查無）與 `llm_mentioned_handoff`（模型在文字裡自己寫了轉人
#: 詞、後掃描補的訊號）。2026-09-09 verifier F1：模型用後者繞過兩出口 ⇒ 併入同一組；
#: 敏感類（`sensitive_no_grounding`）與預算耗盡一律不在此列。
NON_SENSITIVE_HANDOFF_REASONS: frozenset = frozenset({"no_grounding", "llm_mentioned_handoff"})

#: 各受眾共用（prospect 也會經過同一道閘），措辭不帶任何一條線的名詞。
ASK_TARGET_TEXT = "想處理哪一件事？講名稱或編號就可以。"


def _apply_handoff_without_lookup(result: TurnResult, agent_state: dict) -> TurnResult:
    """S4 §5：零查詢的 `no_grounding` 轉人降級成追問（與 `_apply_scope_exit` 同層）。

    條件全為封閉欄位（缺任一 ⇒ 不降級）：
    - `result.kind == "handoff"`
    - `result.trace.handoff_reason == "no_grounding"`
    - `fact_class` 不在敏感五類（敏感類一律不動，仍轉人）
    - 本回合沒有任何工具呼叫（`trace.tool_calls` 為空）
    - 沒有釘住的 select 範圍（`SELECT_SCOPE_KEY` 為 `None`）

    降級時**五欄一起改**（mirrors `_apply_scope_exit`）：`answer`／`kind`／
    `handoff`／`trace.final_kind`／`trace.handoff_reason`，另設
    `outcome=clarifying` 並記一筆 `violations`。
    """
    if result.kind != "handoff":
        return result
    if result.trace.handoff_reason not in NON_SENSITIVE_HANDOFF_REASONS:
        return result
    fact_class_value = (result.handoff or {}).get("fact_class")
    try:
        fact_class = FactClass(fact_class_value)
    except ValueError:
        fact_class = None
    if fact_class in SENSITIVE:
        return result
    if len(result.trace.tool_calls) != 0:
        return result
    if agent_state.get(SELECT_SCOPE_KEY) is not None:
        return result
    result.answer = ASK_TARGET_TEXT
    result.kind = "answer"
    result.handoff = None
    result.trace.final_kind = "answer"
    result.trace.handoff_reason = None
    result.outcome = make_outcome("clarifying", expects="text")
    result.trace.violations.append("handoff_without_lookup")
    return result


# ════════════════════════════════════════════════════════════════════
# T1：追問契約 `ask_target`（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §2）
# ════════════════════════════════════════════════════════════════════
#: `state["agent"]` 底下的**上一回合追問對象**。⚠️ 與 `SELECT_SCOPE_KEY` 同一條
#: 鐵則：**每一個回合出口都要寫**（`_finalize`／`_finish_confirm_turn`／
#: `handoff_cache` 重播共三個寫點），不寫就會殘留上一回合的授權訊號——下游
#: （T3 的肯定語＝授權）讀的是「緊鄰上一回合出口寫入之值」，殘留等於讓一句
#: 「對」去授權一個早就結束的提議。
LAST_ASK_TARGET_KEY = "last_ask_target"


def _apply_ask_target_gate(result: TurnResult) -> TurnResult:
    """T1：最終輸出是 `kind=ask` 卻沒有合法追問對象 ⇒ 換成指路固定句。

    ⚠️ 這是**保底閘**，不是主檢查：主檢查在 Verifier
    （`SCHEMA/ask_target_invalid`），但正式站的觀察模式
    （`AGENT_VERIFIER_OBSERVE_ONLY`）下 Verifier 不擋，所以出口這一層必須自己
    再判一次——⛔ 不得假設「Verifier 過了就一定合法」。

    條件全為封閉欄位：`kind == "ask"` 且 `ask_target ∉ ASK_TARGETS`
    （缺值與值域外同一條）。命中時四欄一起改（mirrors `_apply_handoff_without_lookup`）：
    `answer`／`outcome`／`trace.violations`，外加把 `ask_target` 歸零——
    ⚠️ **歸零是刻意的**：一個值域外的字串若留在 `TurnResult.ask_target` 上，
    `_finalize` 就會把它寫進 `agent_state[LAST_ASK_TARGET_KEY]`，讓「本會話的
    上一個追問對象」這個封閉欄位變成模型可以塞任意字串的地方。

    ⛔ **不改 `kind`**：這一回合仍然是在追問（`outcome=clarifying/expects=text`），
    改成 `answer` 會讓呼叫端以為問題已經答完。
    """
    if result.kind != "ask":
        return result
    if result.ask_target in ASK_TARGETS:
        return result
    result.answer = ASK_TARGET_TEXT
    result.ask_target = None
    result.outcome = make_outcome("clarifying", expects="text")
    result.trace.violations.append("ask_target_invalid")
    return result


# ════════════════════════════════════════════════════════════════════
# T2：兩出口——資料裡沒有 vs 不做判斷（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §3）
# ════════════════════════════════════════════════════════════════════

#: 全部工具結果為空（`status=="ok"` 且 `empty`）時的固定句。⛔ 無插值——
#: 帶物件名稱等於用回話的差別揭露存在性（同 `SCOPE_EXIT_TEXT`／`ASK_TARGET_TEXT`）。
NO_DATA_TEXT = "系統裡查不到這一筆或這一類資料；請確認名稱或編號，或換一個查法。"

#: 至少一筆工具結果有資料、但模型改寫後仍轉人（或改寫預算已耗盡）時的固定句。
#: ⛔ 無插值。
NO_JUDGEMENT_TEXT = "這題要看你的判斷；我這邊能給的是系統資料，要我列出來嗎？"

#: 迴圈內改寫提示的固定句（定義，⛔ 無插值）——與 `_REASON_HINTS`／
#: `_SCHEMA_CAUSE_HINTS` 同一條紀律：只有方法，無原文。
HANDOFF_DATA_REWRITE_HINT = "資料段有內容；判斷題依資料段給建議並引用，⛔ 不轉人。"


def _apply_handoff_data_exits(result: TurnResult) -> TurnResult:
    """T2：`no_grounding` 轉人依工具結果是否有資料分成兩個出口（與
    `_apply_ask_target_gate` 同層、在其之後）。

    條件全為封閉欄位（缺任一 ⇒ 不動）：
    - `result.kind == "handoff"`
    - `result.trace.handoff_reason == "no_grounding"`
    - `fact_class` 不在敏感五類（敏感類一律不動，仍轉人）
    - `result.trace.tool_calls` 非空

    命中後先看有沒有「不能拿 `ToolCallRecord.empty` 判定」的筆——任一筆
    `status != "ok"`（`error`／`timeout`／`rejected`），或本回合有
    `tool_call_id_collides_with_reserved`（撞名保留 id）⇒ **整段不動**，
    維持既有出口（`sensitive_no_grounding`／`llm_mentioned_handoff`／
    `budget_exhausted` 也在這條路上，本函式對它們同樣不動）。

    剩下的情況（全部工具結果 `status=="ok"`）依 `empty` 分流：
    - 全部 `empty` ⇒ `kind=answer`、`answer=NO_DATA_TEXT`、
      `outcome=answered`、`violations += ["handoff_no_data"]`。
    - 至少一筆非 `empty` ⇒ `kind=answer`、`answer=NO_JUDGEMENT_TEXT`、
      `ask_target=confirm_intent`、`outcome=clarifying`、
      `violations += ["handoff_no_judgement"]`（此路只有在模型迴圈內的
      改寫提示——§3 的「迴圈內改寫」——已經重試過仍轉人，或改寫預算已耗盡
      時才會走到這裡；本函式本身 ⛔ 不呼叫模型）。

    五欄一起改（mirrors `_apply_scope_exit`／`_apply_handoff_without_lookup`）：
    `answer`／`kind`／`handoff`／`trace.final_kind`／`trace.handoff_reason`，
    另設 `outcome` 並記一筆 `violations`；NO_JUDGEMENT 分支另外設
    `result.ask_target = "confirm_intent"`——`_finalize` 把
    `agent_state[LAST_ASK_TARGET_KEY]` 寫成「本回合 `ask_target` 是否落在
    `ASK_TARGETS` 值域內」（見 `_finalize` 的寫點，⛔ 不再只認 `kind=="ask"`），
    使這個 `kind=="answer"` 的回合一樣能把 `confirm_intent` 帶進下一回合，供
    T3 的肯定語＝授權判定使用。
    """
    if result.kind != "handoff":
        return result
    if result.trace.handoff_reason not in NON_SENSITIVE_HANDOFF_REASONS:
        return result
    fact_class_value = (result.handoff or {}).get("fact_class")
    try:
        fact_class = FactClass(fact_class_value)
    except ValueError:
        fact_class = None
    if fact_class in SENSITIVE:
        return result
    tool_calls = result.trace.tool_calls
    if not tool_calls:
        return result
    if "tool_call_id_collides_with_reserved" in result.trace.violations:
        return result
    if any(r.status != "ok" for r in tool_calls):
        return result
    if all(r.empty for r in tool_calls):
        result.answer = NO_DATA_TEXT
        result.kind = "answer"
        result.handoff = None
        result.trace.final_kind = "answer"
        result.trace.handoff_reason = None
        result.outcome = make_outcome("answered", expects="text")
        result.trace.violations.append("handoff_no_data")
        return result
    result.answer = NO_JUDGEMENT_TEXT
    result.kind = "answer"
    result.handoff = None
    result.trace.final_kind = "answer"
    result.trace.handoff_reason = None
    result.ask_target = "confirm_intent"
    result.outcome = make_outcome("clarifying", expects="text")
    result.trace.violations.append("handoff_no_judgement")
    return result


def _parse_select_value(message: Any) -> Optional[tuple]:
    """`"select:bill:12345"` → `("bill", "12345")`；不是機器值 ⇒ `None`。

    **`fullmatch`、⛔ 不 NFKC、⛔ 不 strip**（S8-8）：整句等值才算。前後多一個
    空白、或用全形冒號寫成「select：bill：12345」的，都是自由文字——那該進模型，
    ⛔ 不該觸發一次繞過模型的資料查詢。
    """
    if not isinstance(message, str):
        return None
    m = _SELECT_VALUE_RE.fullmatch(message)
    if m is None:
        return None
    return m.group(1), m.group(2)


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
    #: ⛔⛔ **進場句的文字不得進來**——`entry_line` 是呼叫端送的自由文字，trace 與
    #:     `usage_events.decision_snapshot` 都會被序列化落地，記文字等於把外部
    #:     輸入原封不動抄進計量表。只記一個 bool。
    has_entry_line: bool = False
    #: U3（Plan `plan-walkthrough-fixes-batch3-20260909.md` §4）：本回合有沒有
    #: 觸發純編號／短名詞前置查詢。⛔⛔ **原 ref／關鍵字不得進來**——只記
    #: `{"kind": "id"|"keyword", "hits": <int>}`；未觸發 ⇒ `None`。
    pre_lookup: Optional[dict] = None


#: `reasoning_effort` 允許值（OpenAI gpt-5 系列）；封閉集合，⛔ 不在程式內以字串推導。
REASONING_EFFORT_VALUES: frozenset = frozenset({"minimal", "low", "medium", "high"})

_REASON_HINTS: dict[str, str] = {
    # DSP-028 後續（2026-09-05 回歸集重跑）：拒一次就改轉人的回合佔 no_grounding 的 11/127，
    # 且 116/127 是第一次就轉人——拒因回饋要明說「修那一筆」而不是「放棄」。
    # 內容只有方法，⛔ 無任何原文。
    # DSP-029a：引文由系統依標記解析，模型端不再有「抄字」也不再有「填索引」這兩個
    # 動作——回饋一律講「把該筆 `refs` 換成真正講到這句內容的那一行行首標記」。
    "QUOTE_NOT_VERBATIM": "第 {sent} 筆的引用對不上來源：把該筆 `refs` 換成資料段裡真正講到這句內容的那一行行首標記（原樣照抄）。",
    "QUOTE_NOT_COVERING": "第 {sent} 筆的句子內容與它指到的那一行對不上：把該筆 `refs` 換成真正講到這句內容的那一行行首標記，或把句子改成那一行有講的內容（⛔ 不要多加那一行沒寫的資訊）。",
    "QUOTE_TOO_SHORT": "第 {sent} 筆指到的那一行太短、撐不起一個事實斷言（例如只是個標題行）：改指有實際內容的那一行的標記。",
    "UNCITED_ASSERTION": "第 {sent} 筆是陳述事實的句子卻沒有 `refs`：補上該句依據所在那一行行首的標記；大綱真的沒寫的話就刪掉那句，⛔ 不要留下沒有來源的斷言。",
    "POLARITY_MISMATCH": "第 {sent} 筆的肯定／否定與引文不一致（例如引文說「不支援」你寫成「支援」）：照原文的意思改。",
    "SOURCE_NOT_CITABLE": "第 {sent} 筆引到不可引用的來源（目錄類）：改引可引用的章節或工具回傳的標記。",
    "SENSITIVE_TOPIC": "這一題落在敏感五類或含價格／百分比等敏感樣式：改為 `kind=handoff`、填對應的 `fact_class` 與 `handoff_reason=sensitive_no_grounding`。",
}


def _reason_hint(verdict: VerifierVerdict) -> str:
    """把拒因翻成「怎麼修那一筆」；並明說 ⛔ 不得因被拒就改轉人（大綱有寫就要答）。"""
    text = _REASON_HINTS.get(verdict.reason or "", "")
    if text:
        text = "　" + text.format(sent=verdict.sent if verdict.sent is not None else "?")
    if verdict.reason != "SENSITIVE_TOPIC":
        text += "　⛔ 不要因為被拒就改成 `kind=handoff`——只修被指出的那一筆；只有大綱與工具都確實沒有這題的內容時才轉人。"
    return text


#: DSP-029a：`SCHEMA` 的八種子成因 → 給模型的修法一句話。
#: ⛔ 全部只有結構詞與索引，**無任何原文**（來源原文與模型原文都不放）——
#: 這段會被 append 進 `messages` 給模型看，也是 2.6 security review P2 的同一條紀律。
#: ⚠️ 鍵集合必須等於 `VerifierVerdict.schema_cause` 的 Literal 值域，由
#: `tests/unit/agent/test_runtime_req.py` 守住：少一個鍵，那個成因就會落到
#: `_schema_reject_hint` 的保底句，模型永遠得不到具體修法。
_SCHEMA_CAUSE_HINTS: dict[str, str] = {
    "empty_sentences": ("`sentences` 是空陣列：只有 `kind=handoff` 才允許留空，"
                        "其餘一律逐句給一筆 {text, kind, refs}。"),
    "empty_text": "`sentences` 的 `text` 是空白；每一筆都要有實際文字（含句尾標點）。",
    "ref_invalid": ("這一筆的 `refs` 不是本回合資料段裡的標記："
                    "標記要從該句依據所在那一行的行首**原樣照抄**整串，"
                    "⛔ 不要自己拼、⛔ 不要改動裡面任何一段。"),
    "ref_source_not_found": ("這一筆 `refs` 的標記形狀對，但它指的來源不在本回合的資料段裡："
                             "改抄資料段裡實際出現過的那一行的行首標記。"),
    "ref_ambiguous": ("這一筆 `refs` 的標記指到同一次工具回傳裡重複而內容不同的來源："
                      "改抄另一行的行首標記。"),
    "unit_out_of_range": ("這一筆 `refs` 的標記編號超出該來源的範圍："
                          "只能抄資料段裡實際出現過的那一行的行首標記。"),
    "marker_in_answer": ("回覆文字裡出現了資料段的行首標記：標記只放進 `refs`，"
                         "⛔ 不得抄進 `sentences` 的 `text`。"),
    "handoff_reason_invalid": "`handoff_reason` 不在允許值域內，請改填允許的值。",
    "handoff_reason_mismatch": "`fact_class` 屬敏感五類時 `handoff_reason` 必須是 `sensitive_no_grounding`，請改填。",
    "ask_target_invalid": "`kind=ask` 時 `ask_target` 必填且必須是值域內的項目，請改填。",
}


def _schema_reject_hint(verdict: VerifierVerdict) -> str:
    """把 `SCHEMA` 拒因翻成模型看得懂的**具體成因**。

    ⚠️ 成因**由 Verifier 的 `schema_cause` 決定，⛔ 不在這裡重算**（DSP-029 r13 #7）：
    DSP-028 時只有三種成因、且都能從 `out` 自己看出來，所以這裡曾經自己再判一次；
    之後多了要靠 `tool_results` 才判得出來的成因（來源不存在／編號越界／標記抄進
    text），重算就會出現「Verifier 說 A、回饋教他修 B」的分歧。
    ⚠️ DSP-029a 起本函式 ⛔ 不再收 `out`：唯一用到它的是 `cite_out_of_range` 那句
    「本次 `citations` 共 N 筆」，而 `citations` 已經不存在。
    """
    cause = verdict.schema_cause
    # 「第 N 筆」是**索引**（⛔ 無原文），DSP-028 起模型就靠它知道要修哪一筆。
    where = f"第 {verdict.sent} 筆 " if verdict.sent is not None else ""
    if cause in _SCHEMA_CAUSE_HINTS:
        return f"{where}{_SCHEMA_CAUSE_HINTS[cause]}"
    # 沒有子成因＝新的成因沒有同步到這張表：⛔ 不編一句假的修法給模型。
    return "輸出不符 `AgentOutput` 契約，請依 schema 重新輸出。"


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
#: `expects`：接下來等使用者什麼（封閉四值）。
OUTCOME_EXPECTS: tuple = ("text", "choice", "button", "none")
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
    """沒有明設時由 `kind`／`quick_replies` 決定性導出（模型迴圈的一般出口）。"""
    has_choice = bool(result.quick_replies)
    if result.kind == "handoff":
        return make_outcome("handoff", expects="none")
    if result.kind == "ask":
        return make_outcome("clarifying", expects="choice" if has_choice else "text")
    return make_outcome("answered", expects="choice" if has_choice else "text")


def receipt_ref(action: Optional[str], receipt: Any) -> Optional[dict]:
    """receipt → `outcome.ref`（決定性；只認識兩個寫入動作的識別碼欄位）。"""
    if not isinstance(receipt, dict):
        return None
    if action == "repair_create" and receipt.get("repair_id"):
        return {"type": "repair", "id": str(receipt["repair_id"])}
    if action == "bill_due_extend" and receipt.get("bill_id"):
        return {"type": "bill", "id": str(receipt["bill_id"])}
    return None


# ════════════════════════════════════════════════════════════════════
# W8 (2)：照片進場（`/mcp` `agent.turn` 的 `image_urls`）
# ════════════════════════════════════════════════════════════════════
#: 只看了前 N 張的**卡外附加段**（同 W8 (3) `hint`：⛔ 不進 `card`／`card_sha256`／
#: dialog；⛔ 不靜默截斷——使用者必須知道有幾張沒看）。
IMAGE_PARTIAL_TEXT = "只看了前 {n} 張照片（共 {m} 張）。"

#: vision 失敗／逾時／低信心的三句固定句。⛔ 全部**不進模型**：這三條路徑的
#: `answer` 逐字＝這裡的常數，Verifier 不跑（沒有可驗的引用）。
IMAGE_FAILED_TEXT = "照片處理失敗，請改用文字描述，或稍後再試。"
IMAGE_TIMEOUT_TEXT = "照片處理逾時，請少傳幾張或改用文字描述。"
IMAGE_PICK_CATEGORY_TEXT = "照片看起來可能是下列分類，請選一個："

#: 低信心門檻：`confidence <` 此值且樹內候選 ≥2 ⇒ 出卡前先問一個分類（不建 pending）。
IMAGE_CONFIDENCE_MIN = 0.6

#: 低信心 ask 回合的 `quick_replies` 顆數上限（⛔ 不含三顆確認鍵）。
IMAGE_CANDIDATE_MAX = 3

#: 影像事實在本回合資料段裡的來源代碼。⚠️ 一回合只有**一筆**影像事實（多張照片
#: 的辨識結果在門面就已合併成一段程式組的句子），故序號固定 1；⛔ 不隨張數變動，
#: 那會讓模型抄回來的標記與解析側對不上。
IMAGE_PROVENANCE_SOURCE = "image:recognition#1"

#: 影像事實資料段的工具標籤（`wrap_provenance_data` 的第一段）。
IMAGE_DATA_LABEL = "image.recognition"

#: S2／H3：完成動作記憶行在本回合資料段裡的來源代碼與工具標籤——
#: 同影像事實**同一套**注入紀律（見 `_run_turn_body` 的注入區塊）。一回合
#: 只有一行（`completed_actions_line` 決定性合成成單行），序號固定 1。
COMPLETED_ACTIONS_PROVENANCE_SOURCE = "session:completed_actions#1"
COMPLETED_ACTIONS_LABEL = "session.completed_actions"

#: T1（Plan §2）：**呼叫端進場句** `entry_line` 在本回合資料段裡的來源代碼與工具
#: 標籤——同影像事實／完成動作記憶行**同一套**注入紀律。一回合只有一句，序號固定 1。
#:
#: ⚠️ **`citable=False`**（security r1 #6）：進場句是呼叫端自己印給使用者的字，
#:    ⛔ 不是可引用的事實來源。它必須**真的登記進 `tool_results_by_id`、且 id 在
#:    `reserved_ids` 裡**——只有這樣模型引用它才會落在 `SOURCE_NOT_CITABLE`
#:    （「這個來源不可引用」），而不是 `ref_source_not_found`（「查無此來源」）。
#:    後者會誤導模型去改標記，前者才是真話。
#: ⚠️ 標籤形狀受 `prompt_assembler._TOOL_NAME_RE`（`[A-Za-z0-9._-]{1,64}`）管，
#:    來源代碼不受限（它進標記的第三段，允許 `:`）——兩者刻意分開兩個常數，
#:    比照 `IMAGE_DATA_LABEL`／`IMAGE_PROVENANCE_SOURCE`。
CALLER_ENTRY_PROVENANCE_SOURCE = "caller:entry_line#1"
CALLER_ENTRY_LABEL = "caller.entry_line"

#: T3（Plan §4）：**肯定語＝授權**的程式資料段——同進場句一套注入紀律
#: （`citable=False`、真的登記進 `tool_results_by_id`、id 在 `reserved_ids`
#: 裡）。文字固定、無插值；⛔ 不代模型執行工具、⛔ 不寫 `PENDING_CONFIRM_KEY`、
#: ⛔ 不產生 token——這一段只是把「上一句提議已獲授權」交給模型當事實依據，
#: 寫入仍只經 `confirm_submit:<pid>` 的確認鏈兌現。
CALLER_AFFIRMATIVE_PROVENANCE_SOURCE = "caller:affirmative_carry#1"
CALLER_AFFIRMATIVE_LABEL = "caller.affirmative_carry"
AFFIRMATIVE_CARRY_TEXT = "使用者已肯定上一句的提議，直接執行。"

#: T3（Plan §4）：**空會話註記**——dialog 長度為 0 時注入，讓模型能誠實回答
#: 「你剛剛問了我什麼」這類問題，而不是在沒有歷史時憑印象幻覺。同一套
#: 注入紀律；文字固定、無插值。
CONTEXT_EMPTY_SESSION_PROVENANCE_SOURCE = "caller:empty_session#1"
CONTEXT_EMPTY_SESSION_LABEL = "caller.empty_session"
EMPTY_SESSION_TEXT = "本會話沒有先前訊息。"

#: `ImageTurnInput.status` 的封閉值域。
IMAGE_STATUSES: frozenset = frozenset({"ok", "partial", "failed", "timeout"})


@dataclass(frozen=True)
class ImageTurnInput:
    """門面交給 Runtime 的**照片回合輸入**——**全封閉值**（Plan W8 (2)／r2 裁 (a)）。

    ⛔⛔ **沒有 bytes、沒有網址、沒有 vision 自由文字**：照片的原始 bytes 只在
    `mcp_facade` 的記憶體裡活過抓檔→縮圖→辨識那一段；`description` 這個欄位
    **刻意不存在**——照片裡的文字是提示詞注入的唯一出口（S9-11），它連進到
    Runtime 的資格都沒有，遑論上卡或進 `broken_reason`。

    - `status`：`ok`／`partial`（預算用罄但已完成 ≥1 批辨識）／`failed`／`timeout`。
    - `facts`：**程式組的句子**（分類、看不看得出損壞、張數），進模型迴圈時包成
      可引用的資料段（`wrap_provenance_data`）。
    - `candidates`：低信心時的分類樹節點名（≥2 才給），⇒ Runtime 出 ask 回合。
    - `suggested_category`／`suggested_emergency`：已過分類樹封閉映射／值域檢查的
      建議值（對不上 ⇒ `None`＝缺值）。⚠️ 急迫的**卡值唯一決定者仍是**
      `confirm_card.emergency_status_of`（缺值＝1），vision 的預設 2 ⛔ 不得傳播。
    """

    status: str
    facts: str = ""
    processed: int = 0
    total: int = 0
    candidates: tuple = ()
    suggested_category: Optional[str] = None
    suggested_emergency: Optional[int] = None

    def __post_init__(self) -> None:
        # 值域**當場驗**（fail loud）：`status` 一旦漂出封閉四值，下方三條終止
        # 路徑會安靜地全部不觸發＝帶圖回合默默當成沒帶圖，⛔ 那是最糟的失敗方向。
        if self.status not in IMAGE_STATUSES:
            raise ValueError(
                f"ImageTurnInput.status 只允許 {sorted(IMAGE_STATUSES)}，得到 {self.status!r}"
            )


SSEEvent = dict


# 不變量 27／18 的同一組身分鍵（`services.agent.tools.registry._IDENTITY_KEYS`
# 是它唯一的定義來源；這裡不 import 私有名稱，改抄同一份常數並在旁註記，
# ⛔ 若那邊改了這裡要跟著改——見任務回報的取捨欄）。
_IDENTITY_ARG_KEYS = frozenset(
    {"vendor_id", "role_id", "user_id", "target_user", "mode", "viewer_user_id"}
)


#: `state["agent"]["handoff_cache"]` 每 session 的筆數上限（2.6 前置 security
#: review P3）。快取跟著 `form_sessions.collected_data` 一起序列化，無上限等於讓
#: 呼叫端用不同訊息把單一 jsonb 列無限撐大。超過即以 **FIFO** 擠掉最早插入的一筆
#: （dict 保序；⛔ 不是 LRU——重問命中時不重排，那會讓熱門題永遠擠不掉冷門題）。
HANDOFF_CACHE_MAX = 50


def _trim_handoff_cache(cache: dict, limit: int = HANDOFF_CACHE_MAX) -> None:
    """把 `cache` 修到 `limit` 筆以內，先進先出。"""
    while len(cache) > limit:
        cache.pop(next(iter(cache)))


#: `session.slots.set` 的工具名。⚠️ **這是第二份字面量**——唯一正本是
#: `services/agent/tools/session.py:SLOTS_SET_SPEC["name"]`。⛔ 不在本檔 import
#: 那個模組：它會連帶把 `services.conversational_engine` 拉進 runtime 的
#: import 期（runtime 已被 `mcp_facade` import，鏈路越長越容易繞成環）。
#: 兩份不得漂：`tests/unit/agent/test_session_confirm_tools_req.py` 有一條把兩者
#: 釘在一起的回歸案，改名時它會紅。
SLOTS_SET_TOOL_NAME = "session.slots.set"

#: state 內槽位表的鍵——**頂層**（`form_sessions.collected_data.slots`）。
#: ⚠️ 2.9 對齊：2.1 原本讀 `state["agent"]["slots"]`，而 2.4 的
#: `session.slots.set` 寫的是頂層 `slots`（與 `conversational_engine.
#: TransactionState.slots` 同一個位置，舊鏈的交易面向也讀它）。兩處不一致 ⇒
#: 工具寫進去的槽位 runtime 永遠讀不到。以 design（元件 3／`form_sessions.
#: collected_data`）為準取**頂層**。⛔ 別改回 `state["agent"]["slots"]`。
SLOTS_STATE_KEY = "slots"

#: **派生**槽位鍵（任務 4.2／Plan §4.1-2、§4.1-3 第 (1) 道守門）。
#: 這兩個鍵每回合由 `run_turn` 依**入口身分**現算後覆寫進 prompt 槽位，
#: ⛔ 不是 `SlotKey` 的成員（模型寫不進來）、⛔ 不回寫 state、⛔ 不落 DB。
#: 儲存側（jsonb）若出現同名鍵——舊資料、或任何繞過 `write_slot` 的寫入——
#: 一律**丟棄**：留著會讓「儲存的身分」蓋掉「入口的身分」，那正是身分偽造的形狀。
DERIVED_SLOT_KEYS: tuple[str, ...] = ("identity", "identity_source")


def _slots_for_prompt(state: dict) -> dict:
    """從 state 取槽位表，並把 `SlotValue` 攤平成純量給 PromptAssembler。

    ⚠️ **兩份契約在這裡對接，⛔ 別把任何一邊改成另一邊**：
      - 儲存側（`services/agent/tools/session.py:write_slot`、以及舊鏈的
        `conversational_engine.SlotValue`）存的是
        `{key: {"value": ..., "source": ..., "confirmed": ...}}`——這個形狀
        是與舊鏈共用同一格 jsonb 的代價，改了舊鏈的交易面向就讀不到。
      - prompt 側（`prompt_assembler._slot_blocks`）**只收純量**
        （str／int／float／bool／None），巢狀一律 `raise ValueError`——那是
        刻意的注入面收斂（一 slot 一段、值不得自帶結構）。
    兩者直接對接會在**下一回合**炸掉整個回合（`build_messages` raise ⇒
    `run_turn` 拋 ⇒ registry 吞成 `NO_MATCH`），而且只在「模型真的用過
    `session.slots.set`」之後才出現。故在此攤平。

    ⚠️ design.md 元件 5 把簽名寫成 `slots: dict[SlotKey, SlotValue]`（巢狀），
    與 `prompt_assembler` 的實作（純量）相衝——**已記為爭議交人裁決**，本函式
    採「儲存巢狀、進 prompt 攤平」，⛔ 不自行改任何一邊的契約。
    """
    raw = state.get(SLOTS_STATE_KEY)
    if not isinstance(raw, dict):
        return {}
    flat: dict = {}
    for key, value in raw.items():
        if key in DERIVED_SLOT_KEYS:
            # 儲存側的同名鍵一律丟棄（見 `DERIVED_SLOT_KEYS`）。
            # ⛔ log 只有鍵名（封閉值域），不印值。
            logger.warning("[agent] 丟棄儲存側的派生槽位鍵：%s", key)
            continue
        if isinstance(value, dict):
            # `SlotValue`：只取 `value`；沒有 `value` 鍵的異常列直接跳過
            # （⛔ 不塞 `None` 佔位——那會讓 prompt 出現一個「已設定為空」的槽位）。
            if "value" in value:
                flat[key] = value["value"]
            continue
        flat[key] = value
    return flat


def _cache_key(user_message: str) -> str:
    """NFKC 正規化＋去空白後 sha256（design：同題重問快取 key）。"""
    normalized = unicodedata.normalize("NFKC", user_message or "")
    normalized = "".join(normalized.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def strict_json_schema(schema: dict) -> dict:
    """把 pydantic 的 JSON Schema 轉成 OpenAI structured outputs 的 strict 形：**每一層**
    object（root、`$defs`、巢狀 properties、array items、anyOf 分支）都 `additionalProperties:false`
    且 `required`＝全部 properties；移除 strict 不接受的 `default`。
    真線路 2026-09-05 影子 smoke：`response_format 'AgentOutput': 'additionalProperties' is required` 400 抓到
    （2.1 只補頂層）。回傳新 dict，不改入參。"""
    import copy

    def walk(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object" or "properties" in node:
                props = node.get("properties") or {}
                node["properties"] = props
                node["additionalProperties"] = False
                node["required"] = list(props.keys())
            for key in ("properties", "$defs"):
                if isinstance(node.get(key), dict):
                    for v in node[key].values():
                        walk(v)
            for key in ("items",):
                if key in node:
                    walk(node[key])
            for key in ("anyOf", "oneOf", "allOf"):
                if isinstance(node.get(key), list):
                    for v in node[key]:
                        walk(v)
        return node

    return walk(copy.deepcopy(schema))


def _agent_output_response_format() -> dict:
    """`response_format={"type":"json_schema","json_schema":{"strict":True,...}}`

    只在頂層補 `additionalProperties`／`required`（見模組 docstring「本任務
    刻意留白」段——巢狀 `$defs` 的 strict 轉換留給 2.2 對真 API 驗證時處理）。
    """
    schema = strict_json_schema(AgentOutput.model_json_schema())
    # DSP-021：值域交給 strict schema 管形狀（mini 委派分工定案：模型判語義、schema 管形狀）。
    # `AgentOutput.fact_class` 在 pydantic 端刻意是 Optional[str]（Verifier fail-closed 的
    # 第二道牆，見 output_schema.py 頂端），但給模型的 schema 收成封閉列舉——影子
    # 2026-09-05 首筆真流量模型回 `fact_class=null` 即被 ① 當敏感拒掉。
    props = schema["properties"]
    props["fact_class"] = {
        "type": "string",
        "enum": [fc.value for fc in FactClass],
        "description": "本輪問題的事實類別；產品功能／操作方式一律 feature，五類敏感值只配 kind=handoff。",
    }
    props["handoff_reason"] = {
        "anyOf": [
            {"type": "string", "enum": [r.value for r in HandoffReason]},
            {"type": "null"},
        ],
        "description": "kind=handoff 時必填：敏感五類 sensitive_no_grounding、查無資料 no_grounding；其他 kind 填 null。",
    }
    # T1：`ask_target` 比照 `handoff_reason`——`strict_json_schema` 把每個屬性都列
    # 進 `required`，所以「選填」在 strict schema 裡的表達方式是
    # `anyOf[封閉列舉, null]`，⛔ 不是把它從 `required` 拿掉（OpenAI strict 不收）。
    # 值域來源是 `output_schema.ASK_TARGETS`，⛔ 不在此另抄一份字面表。
    props["ask_target"] = {
        "anyOf": [
            {"type": "string", "enum": list(ASK_TARGETS)},
            {"type": "null"},
        ],
        "description": "kind=ask 時必填：這一句要問使用者的東西；其他 kind 填 null。",
    }
    return {
        "type": "json_schema",
        "json_schema": {"name": "AgentOutput", "strict": True, "schema": schema},
    }


def _args_summary(args: dict) -> dict:
    """`ToolCallRecord.args_summary`：只留形狀（`face`／有無 ref／keyword／k），
    ⛔ 不記 `ref`／`keyword`／`query` 原值（1.7 P2 註記、2.5 的紀律提前套用）。
    """
    summary: dict = {}
    if "face" in args:
        summary["face"] = args["face"]
    if "ref" in args:
        summary["has_ref"] = bool(args.get("ref"))
    if "keyword" in args:
        summary["has_keyword"] = bool(args.get("keyword"))
    if "k" in args:
        summary["k"] = args["k"]
    return summary


def _tool_result_n_items(result: ToolResult) -> int:
    if not isinstance(result.data, dict):
        return 0
    candidates = result.data.get("candidates")
    if isinstance(candidates, list):
        return len(candidates)
    return 1 if result.data else 0


def _tool_result_empty(result: ToolResult, status: Literal["ok", "error", "timeout", "rejected"]) -> bool:
    """T2：`ToolCallRecord.empty` 的計算——⚠️ 只有 `status=="ok"` 才可能為
    `True`（plan-verifier r2 #1：`error`／`timeout`／`rejected` ⛔ 一律 `False`，
    「沒查成」不得講成「不存在」）。`True` 條件（封閉三則）：`data` 為空（`None`
    或空 dict）、`data.get("facts")` 是空字串、或 `data.get("found") is False`。
    """
    if status != "ok":
        return False
    data = result.data
    if not data:
        return True
    if not isinstance(data, dict):
        return False
    facts = data.get("facts")
    if isinstance(facts, str) and facts == "":
        return True
    if data.get("found") is False:
        return True
    return False


def _tool_result_status(result: ToolResult) -> Literal["ok", "error", "timeout", "rejected"]:
    if result.ok:
        return "ok"
    if result.error == "TOOL_TIMEOUT":
        return "timeout"
    if result.error in ("RATE_LIMITED", "CONFIRMATION_REQUIRED"):
        return "rejected"
    return "error"


def _assistant_tool_call_message(message: Any, tool_calls: list) -> dict:
    return {
        "role": "assistant",
        "content": getattr(message, "content", None),
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ],
    }


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
            "has_entry_line": trace.has_entry_line,
            # U3：⛔ 只有種類與命中數，**沒有 ref／關鍵字原文**。
            "pre_lookup": trace.pre_lookup,
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


class AgentRuntime:
    """迴圈本體（design 元件 1）。

    `readonly_view` 給 `ShadowRunner`（任務 4.1）建構影子 Runtime 用；
    `stage` 預設讀 `AGENT_STAGE`（`services.agent.mcp_facade.current_stage`，
    與 registry／MCP 門面同一份，⛔ 不另立第二個讀值點）。
    """

    def __init__(
        self,
        provider: Any,
        registry: ToolRegistry,
        verifier: VerifierProtocol,
        assembler: AssemblerProtocol,
        budget: Budget,
        *,
        readonly_view: bool = False,
        stage: Optional[Stage] = None,
        clock: Callable[[], float] = time.monotonic,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        tool_timeout_s: float = 3.0,
        status_interval_s: float = 5.0,
        attempt_sink: Optional[Callable[[dict], None]] = None,
        candidate_selector: Optional[CandidateSelector] = None,
        candidate_selectors: Optional[dict] = None,
        db_pool: Any = None,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.verifier = verifier
        self.assembler = assembler
        self.budget = budget
        self.readonly_view = readonly_view
        # 任務 4.1（Plan §2.1-2）：`None` ⇒ 這條路沒有候選機制（例如評估工具
        # `--candidates off` 或未接線的受眾）——`run_turn` 對此原樣使用整份 outline，
        # ⛔ 這不是降級，見 `_select_outline` docstring。
        self._candidate_selector = candidate_selector
        # DSP-037／S1b：**依受眾**的 selector 對照表（`{audience: CandidateSelector}`）。
        # 非空時它是唯一權威——查無該受眾 ⇒ `None`，⛔ 不回退到單數
        # `candidate_selector`（那會拿甲受眾的索引去服務乙受眾的正本；
        # `CandidateSelector.select` 雖然會被 `canon_sha256 != prepared_sha` 擋成
        # 不服務，但那是最後一道網，⛔ 不該當第一道）。空 ⇒ 沿用單數（既有接線）。
        self._candidate_selectors: dict = dict(candidate_selectors or {})
        # tasks 4.3c（儀表化，非契約）：離線評估用的「被拒中間嘗試」旁路。
        # ⛔ 預設 None＝零行為改變；正式路徑 `bootstrap.build_runtime` 不設它
        # （見 `tests/unit/agent/test_bootstrap_req.py`）。`TurnTrace`／
        # `TurnResult`／decision snapshot 完全不動——這條 sink 只是額外通知，
        # 不影響回合本身的任何判斷或回傳值。
        self._attempt_sink = attempt_sink
        # 未顯式帶 stage ⇒ 建構當下讀一次 AGENT_STAGE（⛔ 不在函式簽名的預設值
        # 位置呼叫，那樣只會在模組 import 當下讀一次、之後 env 改了也不生效）。
        self._stage: Stage = stage if stage is not None else current_stage()
        self._clock = clock
        # 模型名稱不在 design 契約內明列，沿用專案既有慣例
        # （`OPENAI_MODEL` env，見 `services/llm_answer_optimizer.py` 等）；
        # 另開 `AGENT_MODEL` 供獨立覆寫，兩者皆缺才落 "gpt-4o-mini"。
        self._model = model or os.environ.get("AGENT_MODEL") or os.environ.get(
            "OPENAI_MODEL", "gpt-4o-mini"
        )
        # 5.x 探針（2026-09-07，`inputs/probe-report-52-20260907.md` §3-3）：gpt-5 系列預設推理，
        # p95 延遲 38 s。`AGENT_REASONING_EFFORT` 設了才送 `reasoning_effort`（值域封閉）；
        # 未設 ⛔ 不送——gpt-4o-mini 等不接受此參數，送了會 400。非法值在建構期就炸（fail loud）。
        effort = reasoning_effort if reasoning_effort is not None else os.environ.get("AGENT_REASONING_EFFORT", "")
        effort = (effort or "").strip()
        if effort and effort not in REASONING_EFFORT_VALUES:
            raise ValueError(
                f"AGENT_REASONING_EFFORT={effort!r} 不在允許值域 {sorted(REASONING_EFFORT_VALUES)}"
            )
        self._reasoning_effort: Optional[str] = effort or None
        self._tool_timeout_s = tool_timeout_s
        self._status_interval_s = status_interval_s
        # DSP-038／W3：確認兌現段要下的那句 `redeem_pending` 是 Runtime 自己的
        # DB 存取（⛔ 不經模型、⛔ 不經工具 registry——那條路會把 token 交出去）。
        # `None` ⇒ 兌現段**一律回「這筆確認已失效」**（fail-closed），
        # ⛔ 不「先呼叫工具再說」。
        self._db_pool = db_pool

    def _emit_attempt(self, record: dict) -> None:
        """呼叫 `attempt_sink`（若有），任何例外一律吞掉＋`logger.warning`——
        儀表化 ⛔ 不得影響回合本身（tasks 4.3c brief）。"""
        if self._attempt_sink is None:
            return
        try:
            self._attempt_sink(record)
        except Exception:  # noqa: BLE001 — 儀表化，任何 sink 例外都不可外溢
            logger.warning("agent_attempt_sink_failed", exc_info=True)

    def _selector_for(self, audience) -> Optional[CandidateSelector]:
        """該受眾的 `CandidateSelector`（DSP-037／S1b）。

        對照表非空 ⇒ 只認對照表（查無回 `None`，⛔ 不跨受眾回退）；
        對照表空 ⇒ 沿用單數 `candidate_selector`（3.3b／4.1 的既有單一受眾接線，
        prospect 逐位元不變）。
        """
        if self._candidate_selectors:
            return self._candidate_selectors.get(audience)
        return self._candidate_selector

    # ------------------------------------------------------------------
    async def _select_outline(
        self,
        identity: Identity,
        outline: Any,
        user_message: str,
        dialog: list,
        violations: list,
    ) -> tuple[Any, Optional[dict]]:
        """任務 4.1（Plan §2.1-2）：把整份 `outline` 換成這一回合的候選子集。

        適用條件：`outline` 非 None、`get_canon(outline.audience)` 已註冊、
        `outline.audience` 與 `identity.resolved_audience()` 相同，且
        `_selector_for(audience)` 取得到 selector；不適用 ⇒ 原 `outline` 原樣、
        `sel_meta=None`（這**不是**降級——是這條路根本沒有候選機制）。

        ⚠️ DSP-037／S1b 的例外：對照表（`candidate_selectors`）**有設但缺這個受眾**
        ⇒ 那是降級（可見細目全集＋toc）＋`candidate_fallback_full_outline`，
        ⛔ 不與「根本沒有候選機制」混為一談。

        回傳 `(outline, sel_meta)`；`sel_meta` 為 `None` 或
        `{"candidate_ids", "winning_key_kind", "miss_kind"}`。
        """
        if outline is None:
            return outline, None
        audience = getattr(outline, "audience", None)
        canon = get_canon(audience) if audience is not None else None
        if canon is None or audience != identity.resolved_audience():
            return outline, None
        selector = self._selector_for(audience)
        if selector is None and not self._candidate_selectors:
            # 這條路根本沒有候選機制（單數與複數都沒設）⇒ 原樣，⛔ 不記 violation。
            return outline, None

        # `vendor_business_types` 每回合最多解析一次（元件 6，tasks 6.2 前置 P3-b），
        # 結果傳給下面三個呼叫點——⛔ 不在 FineIndex／canon_visible 內部查 DB。
        vendor_business_types = resolve_vendor_business_types(identity)
        toc = build_canon_toc(canon, identity, vendor_business_types=vendor_business_types)

        def _fallback_visible() -> Any:
            if selector is not None:
                visible = selector.index.visible_subset(
                    identity, canon, vendor_business_types=vendor_business_types
                )
            else:
                # 沒有該受眾的索引 ⇒ 直接問 3.2 的 `canon_visible`（`visible_subset`
                # 本身就是它的薄集合包裝，⛔ 這不是第二份可見性真相）。
                visible = frozenset(
                    fine.id
                    for fine in canon.fines()
                    if canon_visible(
                        identity, fine, vendor_business_types=vendor_business_types
                    )
                )
            return CandidateOutlineDoc.from_visible(outline, visible, toc)

        if selector is None:
            # 有對照表、卻缺這個受眾 ⇒ 產線正在降級服務（可見細目全集＋toc），
            # 與「索引不可用」同一個 trace 值域，⛔ 不靜默當成「沒有候選機制」。
            violations.append("candidate_fallback_full_outline")
            return _fallback_visible(), {
                "candidate_ids": [], "winning_key_kind": {}, "miss_kind": "index_unavailable",
            }

        try:
            query = _candidate_query(user_message, dialog)
            sel = await selector.select(
                canon, identity, query, vendor_business_types=vendor_business_types
            )

            if sel is None:
                violations.append("candidate_fallback_full_outline")
                return _fallback_visible(), {
                    "candidate_ids": [], "winning_key_kind": {}, "miss_kind": "index_unavailable",
                }

            miss_kind = sel["miss_kind"]
            if miss_kind == "none_visible":
                violations.append("candidate_none_visible")
                return CandidateOutlineDoc.from_visible(outline, frozenset(), toc), {
                    "candidate_ids": [], "winning_key_kind": {}, "miss_kind": miss_kind,
                }
            if miss_kind == "no_candidate":
                # `ready` 狀態下不可達（見 candidate_selector.py 模組 docstring），
                # 保留於列舉是為了讓 trace 值域封閉；不記 violation（不是機制故障）。
                return _fallback_visible(), {
                    "candidate_ids": [], "winning_key_kind": {}, "miss_kind": miss_kind,
                }

            return CandidateOutlineDoc.from_selection(outline, sel, toc), {
                "candidate_ids": sel["candidate_ids"],
                "winning_key_kind": sel["winning_key_kind"],
                "miss_kind": "hit",
            }
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — 一回合內：選取失敗一律退回可見子集
            logger.warning(
                "agent_select_outline_failed reason=%s", type(exc).__name__
            )
            violations.append("candidate_selector_error")
            return _fallback_visible(), {
                "candidate_ids": [], "winning_key_kind": {}, "miss_kind": "index_unavailable",
            }

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # DSP-038／W3：確認段（機器值 → 兌現 → 寫入工具 → receipt）
    # ------------------------------------------------------------------
    def _finish_confirm_turn(
        self,
        *,
        agent_state: dict,
        user_message: str,
        trace_id: str,
        start: float,
        kind: str,
        answer: str,
        pending_id: Optional[str],
        quick_replies: Optional[list] = None,
        tool_calls: Optional[list] = None,
        violations: Optional[list] = None,
        receipt_id: str = "",
        llm_calls: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        dialog_answer: Optional[str] = None,
        select_type: Optional[str] = None,
        has_ref: Optional[bool] = None,
        slot_written: Optional[bool] = None,
        outcome: Optional[dict] = None,
        completed_action_estate_id: Optional[str] = None,
        completed_action_receipt: Optional[dict] = None,
        completed_action_estate_name: Optional[str] = None,
    ) -> TurnResult:
        """確認段各出口共用的收尾：組 trace → 落 decision snapshot → 寫回 dialog。

        ⚠️ 這條路徑**不進 `handoff_cache`**：確認與兌現是一次性的狀態轉移，
        重播它等於「同一句話再送出一次」。⛔ 不要為了「統一」而套 `_finalize`。

        `dialog_answer`（W8）：進 dialog 的文字與 `TurnResult.answer` **不同**時
        用它。兩個用途：(1) 清單點選回合 dialog 只寫程式摘要（S8-3，facts 原文
        ⛔ 不進歷史）；(2) 出卡回合 dialog 只寫卡文字，卡外提示行 ⛔ 不進歷史。
        `None` ⇒ 兩者相同（既有行為，⛔ 不變）。

        `completed_action_estate_id`／`completed_action_receipt`（S2／H3）：
        只在 `outcome.state == "confirmed"` 且 `outcome.ref` 存在時用得到——
        這是本函式**唯一**寫 `agent_state["completed_actions"]` 的地方（見下方），
        ⛔ 呼叫端不得自己另外寫這個鍵。兩者都是呼叫端已經手上有的封閉值
        （`select_scope`／pending 的 `estate_id`、redeem 回來的 receipt），
        本函式不猜、不另外查。

        `completed_action_estate_name`（T4）：同樣是呼叫端手上已有的封閉值——
        釘住範圍時的清單標題，或待確認 payload 的物件名稱欄位（`confirm_card`
        對外揭露為「物件」的那一欄）；⛔ 不是模型自由文字。缺值就是 `None`，
        記憶行照舊只印編號。

        T1：本函式是確認段／清單點選段／照片程式段**各出口的共用收尾**，故
        `agent_state[LAST_ASK_TARGET_KEY]` 一律在這裡寫 `None`——這條路徑不經
        `_finalize`，不寫就會殘留上一回合的追問對象（plan-verifier r2 #2：點選
        與確認兌現都走這裡）。⚠️ 寫在**組 trace 之前**，與 `SELECT_SCOPE_KEY`
        「先寫再走任何早退」同一鐵則。
        """
        # T1：三個寫點之一（⛔ 不得移到函式尾端）。
        agent_state[LAST_ASK_TARGET_KEY] = None
        trace = TurnTrace(
            trace_id=trace_id,
            tool_calls=list(tool_calls or []),
            # 兌現回合 `llm_calls=0`（⛔ 模型不在迴圈裡，design 元件 3 `jgb2.action` 列）；
            # 確認回合則是模型呼叫 `confirm.request` 之後才走到這裡，⇒ 由呼叫端把
            # 實際次數帶進來。⛔ 不在此硬填 0——計量會少算。
            llm_calls=llm_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            final_kind=kind,
            latency_ms=int((self._clock() - start) * 1000),
            violations=list(violations or []),
            rules_sha=str(getattr(self.verifier, "rules_sha", "") or ""),
            pending_id=pending_id,
            receipt_id=receipt_id or None,
            select_type=select_type,
            has_ref=has_ref,
            slot_written=slot_written,
        )
        agent_state["fixed_streak"] = 0
        _append_dialog(
            agent_state, user_message, answer if dialog_answer is None else dialog_answer
        )
        # S2／H3：兌現成功 ⇒ 記進會話記憶（下一句「剛剛那張單號多少」答得出來）。
        # ⚠️ **只看 `outcome`**（模型不在兌現路徑的迴圈裡，`outcome` 全是程式組的
        #    封閉值）；`state != "confirmed"` 或沒有 `ref`（取消／失敗／清單點選）
        #    ⇒ 什麼都不寫。
        if outcome is not None and outcome.get("state") == "confirmed":
            ref = outcome.get("ref")
            if isinstance(ref, dict):
                record_completed_action(
                    agent_state,
                    action=outcome.get("action"),
                    ref_type=ref.get("type"),
                    ref_id=ref.get("id"),
                    estate_id=completed_action_estate_id,
                    at_iso=datetime.fromtimestamp(self._clock(), tz=timezone.utc).isoformat(),
                    receipt=completed_action_receipt,
                    estate_name=completed_action_estate_name,
                )
        _emit_agent_decision(trace)
        result = TurnResult(
            kind=kind,
            answer=answer,
            handoff=None,
            quick_replies=list(quick_replies or []),
            trace=trace,
            outcome=outcome,
        )
        if result.outcome is None:
            result.outcome = default_outcome(result)
        return result

    # ------------------------------------------------------------------
    # U3：純編號／短名詞前置查詢——一律走 registry 四步（可見性／速率／schema／
    # 身分鍵剝除），⛔ 不直呼 `tools/jgb2.py`（同 `_run_select_segment` 的紀律）。
    # ------------------------------------------------------------------
    async def _pre_lookup_id_result(
        self, identity: Identity, ref: str, scope_estate_id: Optional[str],
        violations: list,
    ) -> tuple[str, Optional[str]]:
        """trigger A：依序試帳單／修繕單／合約，第一個查到就停。

        回傳 `(outcome, facts)`：`outcome` ∈
        `{"found","not_found","out_of_scope","error"}`；非 `"found"` 時
        `facts` 為 `None`。

        ⚠️ **`"not_found"` 與 `"error"` 分開**（⛔ 不得合流）：`NO_MATCH`
        是工具真的查過、確定沒有這筆／看不到——這才配得上「系統裡查不到」
        那句話；逾時／速率限制／例外是**沒查成**，講「查不到」等於講假話
        （L15-13 那句的前提是「真的查過」）。遇到後者**立刻整段放棄**、
        ⛔ 不再試下一個域——連哪一域失敗都不該影響「這回合有沒有東西可信」
        這個結論。
        """
        if not _PRE_LOOKUP_REF_CHARSET_RE.match(ref):
            return "not_found", None
        for select_type in _PRE_LOOKUP_ID_TOOL_ORDER:
            tool_name = _SELECT_TYPE_TO_TOOL[select_type]
            face = _SELECT_DEFAULT_FACE[select_type]
            try:
                tool_result = await self.registry.call(
                    identity, tool_name, {"face": face, "ref": ref},
                    self._tool_timeout_s, stage=self._stage,
                    readonly_view=self.readonly_view, for_model=True,
                )
            except Exception:  # noqa: BLE001 — registry 不可用 ⇒ 沒查成，⛔ 不是查無
                return "error", None
            if not tool_result.ok:
                if tool_result.error == _PRE_LOOKUP_NOT_FOUND_ERROR:
                    continue
                return "error", None
            data = tool_result.data if isinstance(tool_result.data, dict) else {}
            facts = data.get("facts")
            if not isinstance(facts, str) or not facts.strip():
                continue
            if scope_estate_id is not None:
                scope_outcome = _enforce_tool_scope(
                    tool_name, tool_result, scope_estate_id, ref, violations
                )
                if scope_outcome == "out":
                    return "out_of_scope", None
            return "found", facts
        return "not_found", None

    async def _pre_lookup_keyword_result(
        self, identity: Identity, keyword: str, scope_estate_id: Optional[str],
        violations: list,
    ) -> tuple[str, Optional[str]]:
        """trigger B：只開既有的 estates keyword 查詢（S8-13：⛔ 不開
        `estate`／`meter` 的新 `ref` 語義）。回傳形狀同 `_pre_lookup_id_result`。
        """
        clean = sanitize_data_piece(keyword).strip()
        if not clean:
            return "not_found", None
        try:
            tool_result = await self.registry.call(
                identity, _PRE_LOOKUP_ESTATE_TOOL,
                {"face": _PRE_LOOKUP_ESTATE_FACE, "keyword": clean},
                self._tool_timeout_s, stage=self._stage,
                readonly_view=self.readonly_view, for_model=True,
            )
        except Exception:  # noqa: BLE001 — 沒查成，⛔ 不是查無
            return "error", None
        if not tool_result.ok:
            if tool_result.error == _PRE_LOOKUP_NOT_FOUND_ERROR:
                return "not_found", None
            return "error", None
        data = tool_result.data if isinstance(tool_result.data, dict) else {}
        facts = data.get("facts")
        if not isinstance(facts, str) or not facts.strip():
            return "not_found", None
        if scope_estate_id is not None:
            scope_outcome = _enforce_tool_scope(
                _PRE_LOOKUP_ESTATE_TOOL, tool_result, scope_estate_id, clean, violations
            )
            if scope_outcome == "out":
                return "out_of_scope", None
        return "found", facts

    # ------------------------------------------------------------------
    # W8 (1)：清單點選段（機器值 `select:<type>:<id>` → 工具 → facts）
    # ------------------------------------------------------------------
    async def _run_select_segment(
        self, identity: Identity, user_message: str, agent_state: dict,
        trace_id: str, start: float,
    ) -> Optional[TurnResult]:
        """使用者從 LIFF 清單點一列時的整段處理；不是這種回合 ⇒ `None`（照常進模型）。

        **守門順序與確認段完全相同，⛔ 不得調換**（Plan W8）：
          ① `identity.entry != "mcp"` ⇒ 整段不執行（REST 入口沒有清單點選）。
          ② `self.readonly_view` ⇒ 整段不執行。影子回合與正式回合共用
             `session_id`（DSP-016），影子若寫槽位／作廢待確認筆，正式那一邊
             就被影子改掉了，而使用者根本沒點過任何東西。
          ③ 訊息**等值**匹配機器值（`fullmatch`、⛔ 不 NFKC、⛔ 不 strip）。

        **模型不在迴圈裡、Verifier 也不跑**：`answer` 逐字＝該域 face builder 的
        程式產出。⛔ 這不代表沒有出口檢查——facts 出去之前還要再過一次
        `_verify_routes`（見下方），而 email 面由 `_SELECT_DEFAULT_FACE` 封閉表擋。
        """
        if getattr(identity, "entry", DEFAULT_ENTRY_CHANNEL) != "mcp":
            return None
        if self.readonly_view:
            return None
        parsed = _parse_select_value(user_message)
        if parsed is None:
            return None
        select_type, ref = parsed

        # L15 (a)②／L15-05：**先寫再走任何早退**。這一行的存在理由就是「上一次
        # 點選的範圍 ⛔ 不得殘留」——下面每一個早退（NO_MATCH／空 facts／路由
        # 檢查不過）都代表這一次沒有確立任何一戶，範圍必須是 `None`。
        agent_state[SELECT_SCOPE_KEY] = None

        violations: list[str] = []

        def _finish(answer: str, *, dialog_answer=None, tool_calls=None, slot_written=None):
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message, trace_id=trace_id,
                start=start, kind="answer", answer=answer, pending_id=None,
                tool_calls=tool_calls, violations=violations,
                dialog_answer=dialog_answer,
                select_type=select_type, has_ref=bool(ref), slot_written=slot_written,
            )

        # S8-12：缺 `user_id` 時下游會**靜默降級成空**（`JGBSystemAPI.
        # _degraded_response`），使用者只看到「查無此筆」而稽核上完全無聲。
        # ⛔ 不在此擋掉整段（pm 單證是既有身分閘的刻意設計，見
        # `jgb2.py:_identity_gate_ok`）——只把這個事實記進 trace。
        if not getattr(identity, "user_id", None):
            violations.append("select_missing_user_id")

        tool_name = _SELECT_TYPE_TO_TOOL[select_type]
        face = _SELECT_DEFAULT_FACE[select_type]
        call_start = self._clock()
        try:
            # 走既有 registry 四步（可見性、速率、schema、身分鍵剝除）；
            # 授權由 jgb2 API 全權裁（DSP-011）。⛔ 不直呼工具函式。
            tool_result = await self.registry.call(
                identity,
                tool_name,
                {"face": face, "ref": ref},
                self._tool_timeout_s,
                stage=self._stage,
                readonly_view=False,
                for_model=True,
            )
        except Exception as exc:  # noqa: BLE001 — registry 不可用
            violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
            tool_result = ToolResult(ok=False, error="NO_MATCH")
        records = [
            ToolCallRecord(
                id=f"select:{select_type}",
                name=tool_name,
                # ⛔ `ref` 原值不進 trace（S8-6，同 `_args_summary` 的紀律）。
                args_summary={"face": face},
                ms=int((self._clock() - call_start) * 1000),
                status=_tool_result_status(tool_result),
                n_items=_tool_result_n_items(tool_result),
            )
        ]

        if not tool_result.ok:
            return _finish(SELECT_NOT_FOUND_TEXT, tool_calls=records)
        data = tool_result.data if isinstance(tool_result.data, dict) else {}
        facts = data.get("facts")
        if not isinstance(facts, str) or not facts.strip():
            # 空／不在範圍：與「查不到」**同一句**（⛔ 不洩存在性）。
            return _finish(SELECT_NOT_FOUND_TEXT, tool_calls=records)

        # facts 出口再過一次 `_verify_routes`（S8-1）：這條路沒有模型、也就沒有
        # Verifier，而 facts 是下游系統的字串。⛔ 命中不遮罩後送——遮罩等於承認
        # 「這一段可以只挑掉壞的部分」，而我們並不知道還有什麼沒被樣式認出來。
        # ⚠️ **拿不到這道檢查一律當成命中**（fail-closed）：Verifier 是注入的，
        #    換了一個沒有 `_verify_routes` 的實作時，正確的行為是不出這段 facts，
        #    ⛔ 不是「沒得檢查就放行」。
        verify_routes = getattr(self.verifier, "_verify_routes", None)
        if not callable(verify_routes):
            violations.append("select_route_check_unavailable")
            return _finish(SELECT_NOT_FOUND_TEXT, tool_calls=records)
        if verify_routes(unicodedata.normalize("NFKC", facts)) is not None:
            violations.append("select_route_not_allowed")
            return _finish(SELECT_NOT_FOUND_TEXT, tool_calls=records)

        # 槽位：`<type>_ref`（`bill_ref`／`contract_ref`／`repair_ref` 都在
        # `SlotKey` 封閉值域內；`meter` 第一版不開正是因為 `meter_ref` 不在，S8-5）。
        # ⚠️ 找不到 COLLECTING 列 ⇒ **仍回 facts**、trace 記 `slot_written=false`
        #    （⛔ 不因為記不住而不回答；也 ⛔ 不建列——`write_slot` 的既有紀律）。
        slot_written = False
        if self._db_pool is not None:
            try:
                slot_written = bool(
                    await write_slot(
                        self._db_pool, identity.session_id, f"{select_type}_ref", ref
                    )
                )
            except Exception as exc:  # noqa: BLE001 — 寫不進去不該吃掉這次回答
                violations.append(f"SLOT_WRITE_EXC:{type(exc).__name__}")
                slot_written = False

        # 使用者換了要談的那一筆 ⇒ 尚未兌現的待確認筆一律**作廢**。
        # ⛔ **不刪已有 `receipt` 的筆**：R4.3「同一個 pending_id 重送回同一個
        #    receipt」與「不覆蓋既有 receipt」的紀律不變，刪掉會讓已經送出的
        #    動作被謊報成沒送出。
        # ⛔ 也不刪 dict 本身、只標記——標記可回復（Plan §6 W8 回退欄）。
        pending_all = agent_state.get(PENDING_CONFIRM_KEY)
        if isinstance(pending_all, dict):
            for entry in pending_all.values():
                if isinstance(entry, dict) and not isinstance(entry.get("receipt"), dict):
                    entry["invalidated"] = True

        # L15 (a)②：命中 ⇒ 這一段對話的範圍＝該列的物件（`_ok_single(scoped=True)`
        # 放進 `data["scope"]`）。⛔ 列上算不出 `estate_id` 就維持 `None`——沒有
        # 範圍等於「這一段不受限」，而不是「擋掉所有東西」；擋不擋由 (a)③ 在有
        # 範圍時才做，這裡少寫一個猜出來的值。
        scope = data.get("scope")
        row_estate = scope.get("estate_id") if isinstance(scope, dict) else None
        if row_estate is not None and str(row_estate):
            agent_state[SELECT_SCOPE_KEY] = {
                "type": select_type, "estate_id": str(row_estate),
            }

        return _finish(
            facts,
            dialog_answer=SELECT_DIALOG_SUMMARY.format(select_type=select_type, ref=ref),
            tool_calls=records,
            slot_written=slot_written,
        )

    async def _run_confirm_segment(
        self, identity: Identity, user_message: str, agent_state: dict,
        trace_id: str, start: float,
    ) -> Optional[TurnResult]:
        """使用者按下三顆按鈕之一時的整段處理；不是這種回合 ⇒ `None`（照常進模型）。

        **守門順序固定，⛔ 不得調換**（Plan W3）：
          ① `identity.entry != "mcp"` ⇒ 整段不執行。REST 入口永遠兌現不了——
             它的 session 沒有命名空間、token 表也沒有 vendor 欄（S-6／S-7），
             這個 `entry` 判斷就是那兩條 DEFER 的緩解本身。
          ② `self.readonly_view` ⇒ 整段不執行。影子回合與正式回合**共用
             session_id**（DSP-016），影子若兌現，正式那一張 token 就沒了，
             而使用者根本沒按過任何按鈕。
          ③ 訊息**等值**匹配機器值 ⇒ 不進模型：該 `pending_id` 在 session 狀態裡
             有一筆待確認就走兌現；**不在**（錯 pid、會話過期後按舊卡）⇒ 固定句
             `CONFIRMATION_REQUIRED_TEXT`（`3bf28e79`：機器值不承載意圖，進模型只會
             把 pid 念回去）。①②不成立或不是機器值（自由文字「好，送出」、裸
             `confirm_submit`、前後綴）⇒ 照常走模型，⛔ 不觸發任何寫入。

        **模型不在迴圈裡**：這一段從頭到尾沒有一次 `chat.completions.create`。
        使用者按的是機器值，該執行什麼由狀態決定，⛔ 不由模型判讀同意詞（R4.2）。
        """
        if getattr(identity, "entry", DEFAULT_ENTRY_CHANNEL) != "mcp":
            return None
        if self.readonly_view:
            return None
        parsed = _parse_confirm_value(user_message)
        if parsed is None:
            return None
        verb, pending_id = parsed
        pending_all = agent_state.get(PENDING_CONFIRM_KEY)
        pending = pending_all.get(pending_id) if isinstance(pending_all, dict) else None
        if not isinstance(pending, dict):
            # 錯 pid／狀態已清（含 W8 (5) 會話過期後按到舊卡按鈕）⇒ 回固定句
            # `CONFIRMATION_REQUIRED_TEXT`，⛔ 不交給模型：機器值不承載使用者意圖，
            # 進模型只會把 pid（內部識別名）念回給使用者（實測 L3-H：「確認碼 de34…」）。
            # 沒有 token 可燒（本 session 從未持有它），也⛔ 不試著去兌現別的 session 的 pid。
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message, trace_id=trace_id,
                start=start, kind="answer", answer=CONFIRMATION_REQUIRED_TEXT,
                pending_id=pending_id, tool_calls=None,
                violations=["confirm_unknown_pending_id"], receipt_id="",
                outcome=make_outcome("failed", expects="none"),
            )

        def _finish(answer: str, *, receipt_id: str = "", tool_calls=None, violations=None,
                    outcome: Optional[dict] = None, receipt: Optional[dict] = None):
            if outcome is None:
                # 沒明設的確認段出口（CONFIRMATION_REQUIRED 各分支）＝確認已失效 ⇒ failed
                outcome = make_outcome("failed", expects="none", action=pending.get("action"))
            # S2／H3：兌現成功這一格才需要——`estate_id` 兩層來源都是封閉值
            # （L15 的會話範圍優先；沒有範圍時退回 `_begin_pending_confirm` 存進
            # `pending` 的那一格，見 `confirm.py:_open_repairs_hint`）。
            scope = agent_state.get(SELECT_SCOPE_KEY)
            completed_estate_id = None
            completed_estate_name = None
            if isinstance(scope, dict) and scope.get("estate_id"):
                completed_estate_id = str(scope["estate_id"])
                # T4：釘住範圍時，清單面若帶了標題（封閉來源，非模型自由文字）
                # 優先當物件名稱；目前開放的三個 select 面都還沒帶這一格，
                # 缺值時退回下面的 pending payload 來源。
                scope_title = scope.get("title")
                if isinstance(scope_title, str) and scope_title.strip():
                    completed_estate_name = scope_title.strip()
            else:
                pending_estate = pending.get("estate_id")
                if isinstance(pending_estate, str) and pending_estate:
                    completed_estate_id = pending_estate
            if completed_estate_name is None:
                # T4：待確認 payload 的物件名稱欄位——同一欄 `confirm_card.render()`
                # 對外揭露為「物件」那一行（見 `confirm_card.py::_require_text(...,
                # "estate_name", ...)`）；`bill_due_extend` 的 payload 沒有這一欄，
                # 這裡就維持 `None`，記憶行照舊只印帳單編號。
                pending_payload = pending.get("payload")
                if isinstance(pending_payload, dict):
                    payload_estate_name = pending_payload.get("estate_name")
                    if isinstance(payload_estate_name, str) and payload_estate_name.strip():
                        completed_estate_name = payload_estate_name.strip()
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message, trace_id=trace_id,
                start=start, kind="answer", answer=answer, pending_id=pending_id,
                tool_calls=tool_calls, violations=violations, receipt_id=receipt_id,
                outcome=outcome,
                completed_action_estate_id=completed_estate_id,
                completed_action_receipt=receipt,
                completed_action_estate_name=completed_estate_name,
            )

        # W8 (1)：被清單點選作廢掉的待確認筆 ⇒ **視同不存在**，回固定句。
        # ⚠️ 已經有 `receipt` 的筆 ⛔ 不受影響（`_run_select_segment` 根本不標
        #    記它們）——R4.3「重送回同一 receipt」的紀律不變。
        # ⛔ 不在此靜靜放行：使用者換了要談的那一筆之後，舊卡上的參數已經不是
        #    他現在要做的事；token 順手燒掉，避免「作廢後又被別的路徑兌現」。
        if pending.get("invalidated") is True and not isinstance(pending.get("receipt"), dict):
            if self._db_pool is not None:
                await redeem_pending(self._db_pool, identity.session_id, pending_id)
            return _finish(CONFIRMATION_REQUIRED_TEXT)

        submit = verb == CONFIRM_QUICK_REPLY_VALUES[0]
        if not submit:
            # 修改／取消：**一律先燒 token**（⛔ 不留著讓「取消完再送出」還能通），
            # 不呼叫任何寫入工具。
            if self._db_pool is not None:
                await redeem_pending(self._db_pool, identity.session_id, pending_id)
            # ⚠️ ⛔ 不覆蓋既有 receipt：這一筆若已經執行過（使用者先送出、再按取消），
            #    把 receipt 換成 `{"cancelled": true}` 會讓 R4.3 的「重送回同一結果」
            #    變成謊報「沒有送出」。
            if not isinstance(pending.get("receipt"), dict):
                pending["receipt"] = {"cancelled": True}
            return _finish(CANCELLED_TEXT,
                           outcome=make_outcome("cancelled", expects="none",
                                                action=pending.get("action")))

        existing = pending.get("receipt")
        if self._db_pool is None:
            # fail-closed：沒有 DB 就兌現不了，⛔ 不「先呼叫工具再說」。
            return _finish(CONFIRMATION_REQUIRED_TEXT)

        redemption = await redeem_pending(self._db_pool, identity.session_id, pending_id)
        if redemption is None:
            # 沒中＝不存在／已兌現／過期／不是這個 session 的（四者不細分）。
            # R4.3：已經執行過 ⇒ 回**同一個 receipt**，⛔ 不重複建單。
            if isinstance(existing, dict):
                return self._answer_for_receipt(pending, existing, _finish)
            return _finish(CONFIRMATION_REQUIRED_TEXT)

        action = pending.get("action")
        payload = pending.get("payload")
        card_sha = pending.get("card_sha256")
        # ⚠️ `action` 先過封閉值域再拿去組工具名：`agent_state` 是會被序列化進 DB 的
        #    資料，⛔ 不讓其中的字串直接決定要呼叫哪一支工具。
        if action not in CONFIRM_ACTIONS or not isinstance(payload, dict):
            return _finish(CONFIRMATION_REQUIRED_TEXT)
        try:
            payload_sha = payload_digest(payload)
        except (TypeError, ValueError):
            return _finish(CONFIRMATION_REQUIRED_TEXT)
        # 兩把雜湊都要對：payload 對的是「將被執行的參數」，卡對的是「使用者
        # 看到的字」。⛔ 只對其中一把等於留下另一半可以被換掉。
        if not hmac.compare_digest(payload_sha, redemption.payload_sha256):
            return _finish(CONFIRMATION_REQUIRED_TEXT)
        if not isinstance(card_sha, str) or not hmac.compare_digest(
            card_sha, redemption.summary_sha256
        ):
            return _finish(CONFIRMATION_REQUIRED_TEXT)

        # S1／H1 **閘二：兌現前的日期有效性**。與閘一（`confirm.request`）是
        # **同一個純函式、同一個時鐘**（`bills._today()` 在呼叫點取值），
        # ⛔ `action.py` 不再加第二套判定——一個判定、一個時鐘、兩個呼叫點。
        # 為什麼兌現時要再判一次：出卡與按下確認之間可以跨過午夜，也可以在
        # 表被人為改動後才兌現；「使用者按過確認」證明不了「這個日期還沒過」。
        # ⚠️ token 在上面 `redeem_pending` 已經燒掉（刻意，S-12）⇒ 使用者要重新
        #    確認一次；此處**不呼叫任何寫入工具**，pending 以「這一筆失敗了」關掉
        #    （與工具回 `ok=False` 同一條路：重送回同一句 `ACTION_FAILED_TEXT`，R4.3）。
        # 稽核出口＝`trace.violations` 的 `date_before_today_at_redeem`（F9）。
        if fields_before_today(action, payload, bills._today()):
            logger.info("[agent] 兌現閘：日期早於今天 ⇒ ⛔ 不呼叫寫入工具（⛔ 不記日期值）")
            pending["receipt"] = {"error": "INVALID_INPUT"}
            return _finish(
                ACTION_FAILED_TEXT,
                violations=["date_before_today_at_redeem"],
                outcome=make_outcome("failed", expects="none",
                                     action=pending.get("action")),
            )

        violations: list[str] = []
        call_start = self._clock()
        tool_name = f"jgb2.action.{action}"
        try:
            # ⚠️ token 只在這一格行程內出現：從 `redemption` 直接進參數，
            #    ⛔ 不寫回 `pending`、⛔ 不進 trace／log／模型上下文。
            tool_result = await self.registry.call(
                identity,
                tool_name,
                {"payload": payload, "confirmation_token": redemption.token},
                self._tool_timeout_s,
                stage=self._stage,
                readonly_view=False,
                for_model=True,
            )
        except Exception as exc:  # noqa: BLE001 — registry 不可用
            violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
            tool_result = ToolResult(ok=False, error="NO_MATCH")
        records = [
            ToolCallRecord(
                id=f"confirm:{pending_id}",
                name=tool_name,
                args_summary={},   # ⛔ payload 不進 trace（`_args_summary` 的同一條紀律）
                ms=int((self._clock() - call_start) * 1000),
                status=_tool_result_status(tool_result),
                n_items=_tool_result_n_items(tool_result),
            )
        ]

        if not tool_result.ok:
            # 誠實回錯（S-12：token 已燒是刻意的——要再做一次就要重新確認）。
            pending["receipt"] = {"error": tool_result.error or "TOOL_FAILED"}
            return _finish(ACTION_FAILED_TEXT, tool_calls=records, violations=violations,
                           outcome=make_outcome("failed", expects="none",
                                                action=pending.get("action")))

        data = tool_result.data if isinstance(tool_result.data, dict) else {}
        receipt = data.get("receipt")
        if not isinstance(receipt, dict):
            receipt = data
        pending["receipt"] = receipt
        return self._answer_for_receipt(
            pending, receipt, _finish, tool_calls=records, violations=violations
        )

    @staticmethod
    def _answer_for_receipt(pending: dict, receipt: dict, finish, **kwargs) -> TurnResult:
        """receipt → 使用者看到的句子（決定性 formatter，模型不在迴圈）。

        取消過的那一筆重送 ⇒ 回同一句「沒有送出」；失敗過的那一筆重送 ⇒ 回同一句
        「無法執行」——**同一個 `pending_id` 永遠得到同一個結果**（R4.3）。
        """
        action = pending.get("action")
        if receipt.get("cancelled"):
            return finish(CANCELLED_TEXT,
                          outcome=make_outcome("cancelled", expects="none", action=action),
                          **kwargs)
        if receipt.get("error"):
            return finish(ACTION_FAILED_TEXT,
                          outcome=make_outcome("failed", expects="none", action=action),
                          **kwargs)
        return finish(
            render_receipt(action, pending.get("payload"), receipt),
            receipt_id=receipt_id_of(receipt),
            outcome=make_outcome("confirmed", expects="none", action=action,
                                 ref=receipt_ref(action, receipt)),
            receipt=receipt,   # S2／H3：只有這一格 `_finish` 會拿去記完成動作記憶
            **kwargs,
        )

    async def _scope_gate_confirm_request(
        self, identity: Identity, agent_state: dict, data: Any, *,
        trace_id: str, start: float, user_message: str, tool_calls: list,
        violations: list, llm_calls: int = 0, prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Optional[TurnResult]:
        """L15 (a)⑥／L15-03：**寫入路徑的會話邊界**。

        回 `None` ⇒ 照常出卡；回 `TurnResult` ⇒ **不建 pending**、整回合就是
        `SCOPE_EXIT_TEXT`。

        兩個 action 的邊界維度都是**物件**（L15-08 業主裁）：
        - `repair_create`：比 `confirm.request` 回的 `estate_id`（＝
          `mcp_facade._open_repairs` 解析出的那一個物件）。**解析不出（`None`）⇒
          放行**——`jgb2.action.repair_create` 執行時走的是同一支 `_resolve_estate`，
          解析不出就必 `NO_MATCH`，跨戶寫入不可能發生（plan-verifier r1）。
        - `bill_due_extend`：payload 只有帳單編號，故**現查一次那張帳單的物件**
          （`for_model=False` ⇒ 結果 ⛔ 不進 messages、只讀 `data.scope.estate_id`）。
          查不到／查不出物件 ⇒ **fail-closed**（不出卡）：拿不到證據時放行等於
          讓「查不到的帳單」變成繞過邊界的方法。同物件的**不同帳單**照常出卡。
        """
        scope_estate_id = _scope_estate_id(agent_state)
        if scope_estate_id is None or not isinstance(data, dict):
            return None

        action = data.get("action")
        payload = data.get("payload")

        if action == "repair_create":
            estate_id = data.get("estate_id")
            if estate_id is None or not str(estate_id):
                return None
            if str(estate_id) == scope_estate_id:
                return None
        elif action == "bill_due_extend":
            bill_id = payload.get("bill_id") if isinstance(payload, dict) else None
            row_estate: Optional[str] = None
            if bill_id is not None and str(bill_id).strip():
                try:
                    probe = await self.registry.call(
                        identity,
                        "jgb2.query.bills",
                        {"face": _SELECT_DEFAULT_FACE["bill"], "ref": str(bill_id)},
                        self._tool_timeout_s,
                        stage=self._stage,
                        readonly_view=self.readonly_view,
                        for_model=False,
                    )
                except Exception as exc:  # noqa: BLE001 — registry 不可用＝拿不到證據
                    violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
                    probe = None
                probe_data = probe.data if (probe is not None and probe.ok
                                            and isinstance(probe.data, dict)) else {}
                scope = probe_data.get("scope")
                if isinstance(scope, dict) and scope.get("estate_id") is not None:
                    row_estate = str(scope["estate_id"])
            if row_estate is not None and row_estate == scope_estate_id:
                return None
        else:
            # 值域外的 action：形狀檢查是 `_begin_pending_confirm` 的事，這裡
            # ⛔ 不代它判（`CONFIRM_ACTIONS` 之外的值那邊會記 shape_invalid）。
            return None

        violations.append("select_scope_exit")
        return self._finish_confirm_turn(
            agent_state=agent_state,
            user_message=user_message,
            trace_id=trace_id,
            start=start,
            kind="answer",
            answer=SCOPE_EXIT_TEXT,
            outcome=make_outcome("out_of_scope", expects="none"),
            pending_id=None,
            tool_calls=tool_calls,
            violations=violations,
            llm_calls=llm_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def _begin_pending_confirm(
        self, agent_state: dict, data: Any, *, trace_id: str, start: float,
        user_message: str, tool_calls: list, violations: list,
        llm_calls: int = 0, prompt_tokens: int = 0, completion_tokens: int = 0,
    ) -> Optional[TurnResult]:
        """`confirm.request` 成功 ⇒ 把待確認動作存進 session 狀態並結束回合。

        `data` 形狀不符（缺 `card`／`action` 不在值域／`payload` 不是物件）⇒ 回
        `None` 讓回合照常走下去：⛔ 不在這裡硬印一張半成品的卡。

        存進狀態的是 `{action, payload, card_sha256}`——**⛔ 沒有 token**
        （r1 B2）也**⛔ 沒有卡的原文**（原文每次都重算得出來，存它只是多一份
        會跟著 `collected_data` 落 DB 的副本）。
        """
        if not isinstance(data, dict):
            return None
        pending_id = data.get("pending_id")
        card = data.get("card")
        action = data.get("action")
        payload = data.get("payload")
        quick_replies = data.get("quick_replies")
        # W8 (3)：卡外提示行與物件 id（`confirm.request` 回的兩個新欄位）。
        hint = data.get("hint")
        estate_id = data.get("estate_id")
        if (
            not isinstance(pending_id, str)
            or not pending_id
            or not isinstance(card, str)
            or not card
            or action not in CONFIRM_ACTIONS
            or not isinstance(payload, dict)
        ):
            violations.append("confirm_request_data_shape_invalid")
            return None
        pending_all = agent_state.setdefault(PENDING_CONFIRM_KEY, {})
        if not isinstance(pending_all, dict):
            pending_all = {}
            agent_state[PENDING_CONFIRM_KEY] = pending_all
        pending_all[pending_id] = {
            "action": action,
            "payload": payload,
            # ＝ `agent_confirmation_tokens.summary_sha256`（DSP-038-2）。兌現時
            # 兩邊比對，任一邊被換掉都對不上。
            # ⚠️ **逐字＝卡文字的雜湊**：W8 (3) 的提示行在卡外，⛔ 不進這個雜湊
            #    （DSP-038-2「同 payload 同卡」不動）。
            "card_sha256": sha256_hex(card),
        }
        # W8 (3)：物件 id 存進待確認筆（兌現時用；⛔ 不進卡、不進雜湊）。
        if isinstance(estate_id, str) and estate_id:
            pending_all[pending_id]["estate_id"] = estate_id
        # FIFO 上限（dict 保序）；⛔ 不是 LRU——重送命中時不重排，那會讓一筆被
        # 反覆重送的確認永遠擠不掉別人的。
        while len(pending_all) > PENDING_CONFIRM_MAX:
            pending_all.pop(next(iter(pending_all)))
        return self._finish_confirm_turn(
            agent_state=agent_state,
            user_message=user_message,
            trace_id=trace_id,
            start=start,
            kind="ask",
            outcome=make_outcome("confirm_pending", expects="button", action=action),
            # 逐字＝卡文字，⛔ 不經模型、不經 Verifier。W8 (3)：卡外提示行只接
            # 在**這裡**（`TurnResult.answer`），⛔ 不進 `card`／`card_sha256`／
            # dialog（下方 `dialog_answer=card`）。
            answer=card if not (isinstance(hint, str) and hint.strip()) else f"{card}\n{hint}",
            dialog_answer=card,
            pending_id=pending_id,
            quick_replies=list(quick_replies or []),
            tool_calls=tool_calls,
            violations=violations,
            llm_calls=llm_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    # ------------------------------------------------------------------
    # W8 (2)：照片回合的三條**程式終止路徑**（⛔ 一律由 Runtime 產出）
    # ------------------------------------------------------------------
    def _image_program_turn(
        self, image: Optional[ImageTurnInput], *, agent_state: dict,
        user_message: str, trace_id: str, start: float,
    ) -> Optional[TurnResult]:
        """`failed`／`timeout`／低信心候選 ⇒ 直接收尾；其餘 ⇒ `None`（回合照常跑）。

        三條路徑都走 `_finish_confirm_turn`（既有的 trace 發射＋`_append_dialog`）：
        ⛔ 不在門面直接產 `TurnResult`（S9-14：那會繞過寫入閘與 dialog 紀律），
        ⛔ 不進模型（沒有可驗的引用，Verifier 不跑）。
        """
        if image is None:
            return None
        if image.status == "failed":
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message,
                trace_id=trace_id, start=start, kind="answer",
                answer=IMAGE_FAILED_TEXT, pending_id=None,
                violations=["image_recognition_failed"],
                outcome=make_outcome("failed", expects="none"),
            )
        if image.status == "timeout":
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message,
                trace_id=trace_id, start=start, kind="answer",
                answer=IMAGE_TIMEOUT_TEXT, pending_id=None,
                violations=["image_timeout"],
                outcome=make_outcome("failed", expects="none"),
            )
        candidates = [c for c in (image.candidates or []) if isinstance(c, str) and c.strip()]
        if not candidates:
            return None
        picks = candidates[:IMAGE_CANDIDATE_MAX]
        # `label` 與 `value` **皆為分類樹節點名逐字**——⛔ 不另立機器值文法：
        # line-bot 把原字串送回來，下一回合它就是使用者打的分類名。
        # ⛔ 不含三顆確認鍵（那是出卡回合的事），⛔ 不建 pending。
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message,
            trace_id=trace_id, start=start, kind="ask",
            answer=IMAGE_PICK_CATEGORY_TEXT, pending_id=None,
            quick_replies=[{"label": name, "value": name} for name in picks],
            # dialog 末則要帶候選名，下一回合模型才看得懂使用者回的那個詞是什麼。
            dialog_answer=IMAGE_PICK_CATEGORY_TEXT + "、".join(picks),
        )

    async def run_turn(
        self, identity: Identity, user_message: str, state: dict,
        *, image: Optional[ImageTurnInput] = None,
        entry_line: Optional[str] = None,
    ) -> TurnResult:
        """一個回合。`image`（W8 (2)）＝門面已抓檔／縮圖／辨識完的**封閉值**輸入。

        `entry_line`（T1）＝呼叫端**進場時印給使用者的那一句**（選填）。⛔ 它不是
        使用者說的話：不併進 `user_message`、不進 dialog 歷史，只以一段
        **不可引用**的程式資料段進場（見 `_run_turn_body` 的注入區塊）。

        ⚠️ 本層只做一件本體外的事：`status=="partial"` 時把「只看了前 N 張」接在
        `TurnResult.answer` **最後**——時機在 `_append_dialog`／`card_sha256`／trace
        都定案之後，故那三者逐位元不受影響（同 W8 (3) `hint` 的紀律）。
        """
        result = await self._run_turn_body(
            identity, user_message, state, image=image, entry_line=entry_line
        )
        if (
            image is not None
            and image.status == "partial"
            and image.total > image.processed
        ):
            result.answer = (
                f"{result.answer}\n"
                + IMAGE_PARTIAL_TEXT.format(n=image.processed, m=image.total)
            )
        return result

    async def _run_turn_body(
        self, identity: Identity, user_message: str, state: dict,
        *, image: Optional[ImageTurnInput] = None,
        entry_line: Optional[str] = None,
    ) -> TurnResult:
        start = self._clock()
        trace_id = uuid.uuid4().hex
        agent_state = state.setdefault("agent", {})
        # W8 (2)：照片的三條程式終止路徑**排在最前**——失敗／逾時／要先問分類的
        # 回合根本不該進確認段、快取或模型。
        image_turn = self._image_program_turn(
            image, agent_state=agent_state, user_message=user_message,
            trace_id=trace_id, start=start,
        )
        if image_turn is not None:
            return image_turn
        # DSP-038／W3：⚠️ **排在同題重問快取之前**——機器值不是「一題」，
        # 它是一次狀態轉移；讓它先落進快取比對只會多一次無謂的字串雜湊。
        confirmed = await self._run_confirm_segment(
            identity, user_message, agent_state, trace_id, start
        )
        if confirmed is not None:
            return confirmed
        # W8 (1)：清單點選機器值同樣**排在同題重問快取之前**（理由同上：它是
        # 一次狀態轉移，不是「一題」）。兩段的正則值域互斥（`confirm_*:` vs
        # `select:`），⛔ 順序不影響結果，排在後面只是讓既有的確認鏈先判。
        selected = await self._run_select_segment(
            identity, user_message, agent_state, trace_id, start
        )
        if selected is not None:
            return selected
        cache = agent_state.setdefault("handoff_cache", {})
        cache_key = _cache_key(user_message)

        cached = cache.get(cache_key)
        if cached is not None:
            trace = TurnTrace(
                trace_id=trace_id,
                llm_calls=0,
                final_kind="handoff",
                handoff_reason=(cached.get("handoff") or {}).get("reason"),
                latency_ms=int((self._clock() - start) * 1000),
                violations=[f"replayed_from:{cached.get('trace_id', '')}"],
            )
            _emit_agent_decision(trace)
            _append_dialog(agent_state, user_message, cached.get("answer", ""))
            # T1：三個寫點之三（plan-verifier r3 #1）——重播出口既不經
            # `_finalize` 也不經 `_finish_confirm_turn`，⛔ 不寫就會讓上一回合的
            # 追問對象跨過一個完整回合殘留下來。
            agent_state[LAST_ASK_TARGET_KEY] = None
            return TurnResult(
                kind="handoff",
                answer=cached.get("answer", ""),
                handoff=cached.get("handoff"),
                quick_replies=list(cached.get("quick_replies", [])),
                trace=trace,
            )

        counters = BudgetCounters()
        # L15 (a)③④：本回合的會話範圍（`select:` 段寫的），與範圍內／外的工具
        # 結果計數。⛔ 不進 trace 新鍵（L15-11：只用既有的 `violations`）。
        scope_estate_id = _scope_estate_id(agent_state)
        scope_counts = {"in": 0, "out": 0}
        violations: list[str] = []
        tool_call_records: list[ToolCallRecord] = []
        verifier_verdicts: list[VerifierVerdict] = []
        tool_results_by_id: dict[str, ToolResult] = {}
        llm_calls = 0
        prompt_tokens = 0
        completion_tokens = 0
        attempt_no = 0  # tasks 4.3c：模型「最終輸出」嘗試計數，從 1 起（工具呼叫不計）

        # `new_nonce()`（`services.agent.prompt_assembler`）＝ 16 位十六進位，
        # 符合 `wrap_tool_data`／`PromptAssembler` 的 nonce 形狀守門；
        # ⛔ 不用 `secrets.token_urlsafe`——它會產出 `-`／`_`，被 `_require_nonce`
        # 的 `^[0-9A-Za-z]{8,64}$` 擋下（2.5 接線時發現，見任務回報）。
        nonce = new_nonce()
        # S2 §3（plan-verifier r2 #3／r3 #1）：**保留 tool_call id 集合**——本回合
        # 程式會產出的資料段 id 一律由 nonce 導出、在回合最開始就固定下來，
        # ⛔ 不等到「這回合真的有影像／完成動作」才算出來：模型能不能偽造一個
        # 同名 id 不該取決於這回合是否真的用到它（那會讓「沒有影像時 img-… 可以
        # 被模型自己造」這種邊界情況變成漏洞）。`OUTLINE_TOOL_CALL_ID` 是固定字串，
        # 另外兩個當回合才算得出來，故三者都在這裡收斂成同一個集合，下面的工具
        # 迴圈只認這一個集合（見 `tool_call_id_collides_with_reserved`）。
        image_call_id = f"img-{nonce[:8]}"
        completed_call_id = f"done-{nonce[:8]}"
        # T1：進場句資料段的 id 同樣**在回合最開始就固定**、⛔ 不等到「這回合真的
        # 有 entry_line」才算——模型能不能偽造一個 `entry-…` 不該取決於呼叫端這次
        # 有沒有帶進場句（否則「沒帶進場句時 entry-… 可以被模型自己造」就成了洞）。
        entry_call_id = f"entry-{nonce[:8]}"
        # T3：肯定語承接段／空會話註記段的 id 同樣**在回合最開始就固定**——
        # 理由同 `entry_call_id`：模型能不能偽造 `aff-…`／`ctx-…` 不該取決於
        # 這一回合是否真的會注入那一段。
        aff_call_id = f"aff-{nonce[:8]}"
        ctx_call_id = f"ctx-{nonce[:8]}"
        # U3（security F10）：前置查詢資料段的 id 同樣**在回合最開始就無條件
        # 算出並加入 `reserved_ids`**——理由同 `entry_call_id`：模型能不能偽造
        # 一個 `pre-…` 不該取決於這一回合是否真的觸發了前置查詢。
        pre_lookup_call_id = f"pre-{nonce[:8]}"
        reserved_ids: frozenset[str] = frozenset(
            {
                OUTLINE_TOOL_CALL_ID, image_call_id, completed_call_id,
                entry_call_id, aff_call_id, ctx_call_id, pre_lookup_call_id,
            }
        )
        # T1：正規化與記憶行走**同一支** `sanitize_data_piece`（控制字元／零寬／
        # 雙向／換行／假標記逐類剝除）。非字串或剝完為空 ⇒ 空字串＝不注入。
        entry_text = sanitize_data_piece(entry_line).strip()
        # T3（Plan §4）：讀「緊鄰上一回合出口寫入之值」——T1 保證每一個回合出口
        # （`_finalize`／`_finish_confirm_turn`／`handoff_cache` 重播）都會寫
        # `agent_state[LAST_ASK_TARGET_KEY]`，故這裡讀到的必是上一回合的值，
        # ⛔ 不會讀到更早以前殘留的舊訊號。
        last_ask_target = agent_state.get(LAST_ASK_TARGET_KEY)
        # 2.9 路徑對齊：槽位在 **`collected_data` 頂層**（見 `_slots_for_prompt`）。
        slots = _slots_for_prompt(state)
        # 任務 4.2（Plan §4.1-2）：身分槽位一律由**入口身分**現算後覆寫。
        # ⛔ 不用 `setdefault`（那等於讓儲存側／模型寫的值贏）；⛔ 不回寫
        # `state`（`_slots_for_prompt` 回的是新 dict，覆寫只影響本回合 prompt）；
        # ⛔ 不落 DB。模型能寫的是 `identity_detail`（角色子類），它動不到這兩鍵。
        slots["identity"] = identity.resolved_audience()
        slots["identity_source"] = derive_identity_source(identity)
        dialog = agent_state.get("dialog", [])
        outline = agent_state.get("outline")
        # 任務 4.1（Plan §2.1-2）：把整份 outline 換成這一回合的候選子集（或降級的
        # 可見子集）；**同一個** outline 物件接著餵 `_seed_outline_provenance` 與
        # `assembler.build_messages`（下方）。
        outline, sel_meta = await self._select_outline(
            identity, outline, user_message, dialog, violations
        )
        candidate_ids: list[str] = list(sel_meta["candidate_ids"]) if sel_meta else []
        winning_key_kind: dict[str, str] = dict(sel_meta["winning_key_kind"]) if sel_meta else {}
        miss_kind: Optional[str] = sel_meta["miss_kind"] if sel_meta else None
        seeded_outline = _seed_outline_provenance(outline)
        if seeded_outline is not None:
            tool_results_by_id[OUTLINE_TOOL_CALL_ID] = seeded_outline

        tool_specs = self.registry.to_openai_tools(
            identity, self._stage, readonly_view=self.readonly_view
        )
        visible_names = {tool_name_from_openai(t["function"]["name"]) for t in tool_specs}   # 解回 registry 名

        messages = self.assembler.build_messages(identity, outline, slots, dialog, tool_specs, nonce)

        # T3（Plan §4）：**肯定語＝授權**——本回合訊息整句屬 `AFFIRMATIVE_WORDS`
        # 且緊鄰上一回合出口寫入的 `last_ask_target == "confirm_intent"` ⇒ 以
        # 程式資料段注入「上一句提議已獲授權」，供模型直接執行（⛔ 不代模型執行
        # 工具、⛔ 不寫 `PENDING_CONFIRM_KEY`、⛔ 不產生 token——寫入仍只經
        # `confirm_submit:<pid>` 兌現）。`violations` 只記一個統計旗標。
        # ⚠️ 排在 DSP-022 那句**之前**——這一段是這一輪使用者訊息之前的背景資料，
        #    ⛔ 不得排在使用者訊息之後（那會破壞「使用者這句一定是送給模型的
        #    最後一則訊息」這個既有不變量，見
        #    `test_outline_citation_seed_req.test_current_user_message_is_last_message_sent_to_model`）。
        if last_ask_target == "confirm_intent" and is_affirmative(user_message):
            violations.append("affirmative_carry")
            tool_results_by_id[aff_call_id] = ToolResult(
                ok=True,
                data={},
                provenance=[
                    Provenance(
                        source=CALLER_AFFIRMATIVE_PROVENANCE_SOURCE,
                        text=AFFIRMATIVE_CARRY_TEXT,
                        citable=False,
                    )
                ],
                text_for_model="",
            )
            messages.append(
                {
                    "role": "user",
                    "content": wrap_provenance_data(
                        CALLER_AFFIRMATIVE_LABEL,
                        aff_call_id,
                        [(CALLER_AFFIRMATIVE_PROVENANCE_SOURCE, provenance_units(AFFIRMATIVE_CARRY_TEXT))],
                        nonce,
                    ),
                }
            )

        # T3（Plan §4）：**空會話註記**——dialog 長度 0（封閉條件）⇒ 注入固定句，
        # 讓模型能誠實回答「你剛剛問了我什麼」這類問題，而不是在沒有歷史時
        # 憑印象幻覺。同樣排在 DSP-022 那句之前，理由同上。
        if not dialog:
            tool_results_by_id[ctx_call_id] = ToolResult(
                ok=True,
                data={},
                provenance=[
                    Provenance(
                        source=CONTEXT_EMPTY_SESSION_PROVENANCE_SOURCE,
                        text=EMPTY_SESSION_TEXT,
                        citable=False,
                    )
                ],
                text_for_model="",
            )
            messages.append(
                {
                    "role": "user",
                    "content": wrap_provenance_data(
                        CONTEXT_EMPTY_SESSION_LABEL,
                        ctx_call_id,
                        [(CONTEXT_EMPTY_SESSION_PROVENANCE_SOURCE, provenance_units(EMPTY_SESSION_TEXT))],
                        nonce,
                    ),
                }
            )

        # U3（Plan `plan-walkthrough-fixes-batch3-20260909.md` §4）：純編號／
        # 短名詞一句 ⇒ 程式先查一次，把結果當可引用資料段注入——模型才不會反問
        #「哪一種類型」。⛔ 不代模型作答、不改變 outcome；⛔ 原 ref／關鍵字不進
        # trace／決策快照（只記 `pre_lookup_trace`，見下方）。⚠️ 同 T3 兩段的排法：
        # 排在 DSP-022 那句**之前**——這是使用者這句之前的背景資料。
        pre_lookup_trace: Optional[dict] = None
        pre_trigger = _pre_lookup_trigger(user_message)
        if pre_trigger is not None:
            pre_kind, pre_candidate = pre_trigger
            if pre_kind == "id":
                pre_outcome, pre_facts = await self._pre_lookup_id_result(
                    identity, pre_candidate, scope_estate_id, violations
                )
            else:
                pre_outcome, pre_facts = await self._pre_lookup_keyword_result(
                    identity, pre_candidate, scope_estate_id, violations
                )
            pre_lookup_trace = {"kind": pre_kind, "hits": 1 if pre_outcome == "found" else 0}
            # L15：範圍外 ⇒ **完全不注入**（連查無固定句也不印——範圍檢查本身
            # 就已經在別的路徑上有指路句，這裡多印一句等於多一個揭露面）。
            # `"error"`（逾時／速率限制／例外）同樣**完全不注入**——這種情況
            # 是「沒查成」，⛔ 不得講成「查不到」（那是把沒查講成查過沒有）；
            # 也 ⛔ 不把工具錯誤碼露給使用者，直接讓這一回合當成沒觸發過。
            if pre_outcome not in ("out_of_scope", "error"):
                inject_text = pre_facts if pre_outcome == "found" else PRE_LOOKUP_NOT_FOUND_TEXT
                inject_text = sanitize_data_piece(inject_text)
                if inject_text:
                    tool_results_by_id[pre_lookup_call_id] = ToolResult(
                        ok=True,
                        data={},
                        provenance=[
                            Provenance(
                                source=PRE_LOOKUP_PROVENANCE_SOURCE,
                                text=inject_text,
                                citable=True,
                            )
                        ],
                        text_for_model="",
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": wrap_provenance_data(
                                PRE_LOOKUP_LABEL,
                                pre_lookup_call_id,
                                [(PRE_LOOKUP_PROVENANCE_SOURCE, provenance_units(inject_text))],
                                nonce,
                            ),
                        }
                    )

        # DSP-022：當前這句一定是最後一則 user 訊息（歷史由 assembler 從 `dialog` 放前面）。
        messages.append({"role": "user", "content": user_message})
        # W8 (2)：影像事實以**可引用的工具事實**進場（r1 裁定接線）——包法與工具
        # 回傳完全相同（`wrap_provenance_data` ＋ 同回合 nonce），故模型引用它的
        # 句子解析得出來、過得了 Verifier（驗收 (xii)）。
        # ⛔ 不併進 `message`（那會變成使用者說的話）、⛔ 不經 `agent_state`。
        if image is not None and image.status in ("ok", "partial") and image.facts.strip():
            tool_results_by_id[image_call_id] = ToolResult(
                ok=True,
                data={"processed": image.processed, "total": image.total},
                provenance=[
                    Provenance(
                        source=IMAGE_PROVENANCE_SOURCE, text=image.facts, citable=True
                    )
                ],
                text_for_model="",
            )
            messages.append(
                {
                    "role": "user",
                    "content": wrap_provenance_data(
                        IMAGE_DATA_LABEL,
                        image_call_id,
                        [(IMAGE_PROVENANCE_SOURCE, provenance_units(image.facts))],
                        nonce,
                    ),
                }
            )

        # S2／H3：完成動作記憶——與影像事實**同一套**注入紀律（可引用資料段、
        # 同回合 nonce、⛔ 不進 dialog、⛔ 不經 `agent_state` 以外的任何管道）。
        # 只有非空且（有釘範圍時）有同戶項目才真的注入——沒有東西可引用時
        # 不佔一段 messages。
        completed_line = completed_actions_line(
            agent_state.get(COMPLETED_ACTIONS_KEY), scope_estate_id
        )
        if completed_line:
            tool_results_by_id[completed_call_id] = ToolResult(
                ok=True,
                data={},
                provenance=[
                    Provenance(
                        source=COMPLETED_ACTIONS_PROVENANCE_SOURCE,
                        text=completed_line,
                        citable=True,
                    )
                ],
                text_for_model="",
            )
            messages.append(
                {
                    "role": "user",
                    "content": wrap_provenance_data(
                        COMPLETED_ACTIONS_LABEL,
                        completed_call_id,
                        [(COMPLETED_ACTIONS_PROVENANCE_SOURCE, provenance_units(completed_line))],
                        nonce,
                    ),
                }
            )

        # T1（Plan §2）：**呼叫端進場句**——與影像事實／完成動作記憶行同一套注入
        # 紀律，只差一個旗標：`citable=False`（進場句是呼叫端印的字，⛔ 不是可
        # 引用的事實來源）。
        # ⛔ 不併進 `user_message`（那會變成使用者說的話）、⛔ 不進 dialog 歷史
        #    （`_append_dialog` 不動）、⛔ 不進 trace／決策快照（只記 bool）。
        # ⚠️ **一定要登記進 `tool_results_by_id`**：不登記的話模型引用它會落
        #    `ref_source_not_found`，而正確的訊號是 `SOURCE_NOT_CITABLE`。
        if entry_text:
            tool_results_by_id[entry_call_id] = ToolResult(
                ok=True,
                data={},
                provenance=[
                    Provenance(
                        source=CALLER_ENTRY_PROVENANCE_SOURCE,
                        text=entry_text,
                        citable=False,
                    )
                ],
                text_for_model="",
            )
            messages.append(
                {
                    "role": "user",
                    "content": wrap_provenance_data(
                        CALLER_ENTRY_LABEL,
                        entry_call_id,
                        [(CALLER_ENTRY_PROVENANCE_SOURCE, provenance_units(entry_text))],
                        nonce,
                    ),
                }
            )

        def _outline_sha() -> str:
            return getattr(outline, "sha256", "") if outline is not None else ""

        def _rules_sha() -> str:
            return getattr(self.verifier, "rules_sha", "") or ""

        def _build_fixed(reason: str) -> TurnResult:
            message_text = effective_handoff_message(None)
            channel = effective_handoff_channel(None)
            handoff_dict = {
                "reason": reason,
                "fact_class": FactClass.other.value,
                "channel": channel,
                "message": message_text,
            }
            trace = TurnTrace(
                trace_id=trace_id,
                tool_calls=list(tool_call_records),
                llm_calls=llm_calls,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                verifier=list(verifier_verdicts),
                final_kind="handoff",
                handoff_reason=reason,
                latency_ms=int((self._clock() - start) * 1000),
                violations=list(violations),
                rules_sha=_rules_sha(),
                outline_sha=_outline_sha(),
                candidate_ids=list(candidate_ids),
                winning_key_kind=dict(winning_key_kind),
                miss_kind=miss_kind,
                has_entry_line=bool(entry_text),
                pre_lookup=pre_lookup_trace,
            )
            return TurnResult(
                kind="handoff",
                answer=message_text,
                handoff=handoff_dict,
                quick_replies=[],
                trace=trace,
            )

        def _finalize(result: TurnResult, *, is_fixed: bool) -> TurnResult:
            # L15 (a)④：**唯一接句點**，排在 handoff cache 與 dialog 之前——
            # 全範圍外的回合在這裡就已經是 `kind="answer"`，故 ⛔ 不會進快取，
            # dialog 存的也是使用者看到的那一句（含接句）。
            result = _apply_scope_exit(
                result, scope_in=scope_counts["in"], scope_out=scope_counts["out"]
            )
            result = _apply_handoff_without_lookup(result, agent_state)
            # T1（security r1 #3）：新閘一律排在 `_apply_scope_exit` **之後**——
            # 範圍外的回合在上面已經被換成固定句，不該再被當成一次追問來判。
            result = _apply_ask_target_gate(result)
            # T2：新閘在 `_apply_ask_target_gate` **之後**——NO_JUDGEMENT 分支
            # 會把 `kind` 從 `handoff` 換成 `answer` 並另設 `ask_target=
            # "confirm_intent"`；排在 ask_target 閘之後，才不會被那道只認
            # `kind=="ask"` 的閘動到。
            result = _apply_handoff_data_exits(result)
            # T1：三個寫點之一（模型迴圈的一般出口與所有固定句出口都經這裡）。
            # ⚠️ 讀的是**過完所有出口閘之後**的 `ask_target`：閘門可能把一個
            #    `kind=ask` 的追問對象歸零，殘留舊值等於讓下一回合的程式判定
            #    拿到一個這一回合根本沒有出去的授權訊號。T2（NO_JUDGEMENT）把
            #    `kind` 換成 `answer` 但仍設了合法的 `ask_target=
            #    "confirm_intent"`——⛔ 不再只認 `kind=="ask"`，改認
            #    `ask_target` 是否落在 `ASK_TARGETS` 值域內：其他 `kind` 的
            #    `ask_target` 一律是模型依 schema 填的 `None`，這條件對它們
            #    等價於原本的 `kind=="ask"` 判定。
            agent_state[LAST_ASK_TARGET_KEY] = (
                result.ask_target if result.ask_target in ASK_TARGETS else None
            )
            if result.trace.final_kind == "handoff":
                cache[cache_key] = {
                    "answer": result.answer,
                    "handoff": result.handoff,
                    "quick_replies": list(result.quick_replies),
                    "trace_id": result.trace.trace_id,
                }
                _trim_handoff_cache(cache)
            agent_state["fixed_streak"] = (
                agent_state.get("fixed_streak", 0) + 1 if is_fixed else 0
            )
            if result.outcome is None:
                result.outcome = default_outcome(result)
            _append_dialog(agent_state, user_message, result.answer)
            _emit_agent_decision(result.trace)
            return result

        while True:
            if (self._clock() - start) >= self.budget.deadline_s:
                return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)

            llm_calls += 1
            create_kwargs = dict(
                model=self._model,
                messages=messages,
                tools=tool_specs,
                parallel_tool_calls=False,
                response_format=_agent_output_response_format(),
            )
            if self._reasoning_effort is not None:
                # openai SDK 1.54（requirements）尚無 `reasoning_effort` 具名參數，走 `extra_body`
                # 直接進 JSON body（各版本皆收）；⛔ 不升 SDK 換參數名（那是另一個變因）。
                create_kwargs["extra_body"] = {"reasoning_effort": self._reasoning_effort}
            response = await self.provider.async_client.chat.completions.create(**create_kwargs)
            usage = getattr(response, "usage", None)
            turn_pt = int(getattr(usage, "prompt_tokens", 0) or 0)
            turn_ct = int(getattr(usage, "completion_tokens", 0) or 0)
            prompt_tokens += turn_pt
            completion_tokens += turn_ct
            # 2.6 前置 security review P2：Runtime 直呼 `chat.completions.create`
            # 繞過 `services/llm_provider.py` 的統一出口 ⇒ token／費用不進事件層，
            # 而 `/mcp` 的內部 key 又免額度 ⇒ 這條路徑等於沒有量。這裡按
            # `usage_metering.add_llm_usage(model, usage_dict)` 的簽名把每一次
            # 模型呼叫灌回**當前請求的計量 context**（`/mcp` 由
            # `mcp_facade._invoke` 的 `begin()` 建、REST 由 middleware 建）；
            # 非計量路徑（ctx 為 None）它自己靜默略過，⛔ 這裡不另外判斷。
            usage_metering.add_llm_usage(
                self._model,
                {"prompt_tokens": turn_pt, "completion_tokens": turn_ct},
            )
            message = response.choices[0].message
            tool_calls = list(getattr(message, "tool_calls", None) or [])

            if tool_calls:
                messages.append(_assistant_tool_call_message(message, tool_calls))
                budget_hit = False
                for tc in tool_calls:
                    if counters.tool_call_exhausted(self.budget):
                        budget_hit = True
                        break
                    name = tool_name_from_openai(tc.function.name)   # kb__get → kb.get（OpenAI 名稱規則，registry.openai_tool_name）
                    try:
                        raw_args = json.loads(tc.function.arguments or "{}")
                        if not isinstance(raw_args, dict):
                            raw_args = {}
                    except (json.JSONDecodeError, TypeError):
                        raw_args = {}

                    for key in sorted(_IDENTITY_ARG_KEYS & set(raw_args.keys())):
                        violations.append(f"IDENTITY_KEY:{key}")
                    if name not in visible_names:
                        violations.append(f"FORBIDDEN:{name}")

                    counters.tool_calls += 1
                    call_start = self._clock()
                    try:
                        tool_result = await self.registry.call(
                            identity,
                            name,
                            raw_args,
                            self._tool_timeout_s,
                            stage=self._stage,
                            readonly_view=self.readonly_view,
                            for_model=True,
                        )
                    except Exception as exc:  # registry 不可用（例外）
                        violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
                        return _finalize(_build_fixed("tool_unavailable"), is_fixed=True)

                    if tool_result.error == "TOOL_TIMEOUT":
                        if counters.tool_call_exhausted(self.budget):
                            budget_hit = True
                            break
                        counters.tool_calls += 1  # 重試也計（design 預算表）
                        try:
                            tool_result = await self.registry.call(
                                identity,
                                name,
                                raw_args,
                                self._tool_timeout_s,
                                stage=self._stage,
                                readonly_view=self.readonly_view,
                                for_model=True,
                            )
                        except Exception as exc:
                            violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
                            return _finalize(_build_fixed("tool_unavailable"), is_fixed=True)
                        if tool_result.error == "TOOL_TIMEOUT":
                            return _finalize(
                                _build_fixed("tool_unavailable"), is_fixed=True
                            )

                    # L15 (a)③：**範圍比對排在這裡**——`registry.call` 一回來、
                    # 進 trace／`tool_results_by_id`／`_wrap`／messages 之前。
                    # 替換是就地改同一個 `ToolResult` 物件 ⇒ 底下每一個下游拿到
                    # 的都是替換後那一份（⛔ 原 facts 不進 messages／provenance）。
                    if scope_estate_id is not None:
                        _q = raw_args.get("ref") or raw_args.get("keyword")
                        _outcome = _enforce_tool_scope(
                            name, tool_result, scope_estate_id,
                            _q if _q is None or isinstance(_q, str) else str(_q),
                            violations,
                        )
                        if _outcome == "in":
                            scope_counts["in"] += 1
                        elif _outcome == "out":
                            scope_counts["out"] += 1

                    ms = int((self._clock() - call_start) * 1000)
                    status_value = _tool_result_status(tool_result)
                    # T2：撞名保留 id 的那筆沒有真的登記進 `tool_results_by_id`——
                    # 它不是「查了、查無資料」，`empty` 一律 `False`（§2）。
                    is_reserved_collision = tc.id in reserved_ids
                    tool_call_records.append(
                        ToolCallRecord(
                            id=tc.id,
                            name=name,
                            args_summary=_args_summary(raw_args),
                            ms=ms,
                            status=status_value,
                            n_items=_tool_result_n_items(tool_result),
                            empty=(
                                False if is_reserved_collision
                                else _tool_result_empty(tool_result, status_value)
                            ),
                        )
                    )
                    # DSP-029 r13 #3／S2 §3（plan-verifier r2 #3、r3 #1）：**保留
                    # tool_call id 集合**，模型送來同名 tool_call 一律拒收 ＋ 記
                    # violation——⛔ 不論這回合是否真的有影像／完成動作／大綱都要
                    # 拒（見上方 `reserved_ids` 的建構理由）：沒有大綱時放行等於
                    # 讓模型自己造一個叫 `outline` 的來源，之後所有 `outline:*` 引用
                    # 都會解析到它自己塞進來的文字（自證變成自說自話）；影像／完成
                    # 動作同理。原本只防 `OUTLINE_TOOL_CALL_ID` 一個保留字，
                    # 現在以集合迭代，⛔ 不分三個 if 各自處理。
                    if is_reserved_collision:
                        violations.append("tool_call_id_collides_with_reserved")
                    else:
                        tool_results_by_id[tc.id] = tool_result
                    # DSP-038-2／W3「確認回合」：`confirm.request` 一成功，這一回合
                    # **立刻結束**——`TurnResult.answer` 逐字＝程式產出的確認卡，
                    # 模型當回合的輸出丟棄、Verifier 不跑（卡不是模型寫的，沒有可
                    # 驗的引用）。⛔ 不把卡交回模型讓它「潤飾一下」：那一潤，
                    # 使用者看到的字就不再等於 `summary_sha256` 綁住的那一份。
                    if name == CONFIRM_TOOL_NAME and tool_result.ok:
                        # L15 (a)⑥／L15-03：**寫入路徑的邊界**。⛔ 不靠讀路徑
                        # 的比對——`confirm.request` 的 payload 是模型自己填的，
                        # 它可以完全不查就直接出一張別戶的卡。
                        # ⚠️ 閘門放在**呼叫點**而非 `_begin_pending_confirm` 內：
                        #    那支是同步函式，而 `bill_due_extend` 的邊界要現查一次
                        #    帳單（await registry.call）。兩者相鄰、同一個出口，
                        #    行為等同「有範圍且別戶 ⇒ 不建 pending、回固定句」。
                        scope_turn = await self._scope_gate_confirm_request(
                            identity, agent_state, tool_result.data,
                            trace_id=trace_id,
                            start=start,
                            user_message=user_message,
                            tool_calls=tool_call_records,
                            violations=violations,
                            llm_calls=llm_calls,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                        )
                        if scope_turn is not None:
                            return scope_turn
                        confirm_turn = self._begin_pending_confirm(
                            agent_state,
                            tool_result.data,
                            trace_id=trace_id,
                            start=start,
                            user_message=user_message,
                            tool_calls=tool_call_records,
                            violations=violations,
                            llm_calls=llm_calls,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                        )
                        if confirm_turn is not None:
                            return confirm_turn
                    # ⚠️ **槽位寫回 state（2.9，⛔ 勿刪）**：`session.slots.set` 是
                    #    以 `jsonb_set` 直接改 `form_sessions.collected_data.slots`
                    #    的，但回合結束時呼叫端（`mcp_facade._agent_turn`／
                    #    `routers/agent_entry._persist`）會用手上這份 `state`
                    #    **整包覆蓋** `collected_data`（`_save` 是
                    #    `SET collected_data=$2::jsonb`，不是 merge）。不同步回來，
                    #    剛寫進去的槽位會在同一回合結束時被自己抹掉——工具回 ok、
                    #    DB 卻沒東西，是最難查的那種失敗。
                    #    來源＝**工具自己回傳的全表**（`slots_set` 寫入後重讀的那份），
                    #    ⛔ 不在此另發一次 DB 查詢。
                    if (
                        name == SLOTS_SET_TOOL_NAME
                        and tool_result.ok
                        and isinstance(tool_result.data, dict)
                        and isinstance(tool_result.data.get(SLOTS_STATE_KEY), dict)
                    ):
                        state[SLOTS_STATE_KEY] = tool_result.data[SLOTS_STATE_KEY]
                    # 2.5 接線：工具回傳一律包成資料段（同回合共用一個 nonce，
                    # 見上方 `nonce = new_nonce()`）。
                    # DSP-029 P0-1：**有 provenance 的工具改送編號後的片段**——
                    # `text_for_model` ⛔ 不再是編號或送模型的輸入。理由：unit 的唯一
                    # 來源必須是 `Provenance.text`，否則模型看到的第 i 句與系統解析的
                    # 第 i 句可能不是同一句，而失敗方向是放行。無 provenance 的工具
                    # （handoff／session.slots／confirm）沒有可引用的原文，維持原樣。
                    provenance = list(tool_result.provenance or [])
                    raw_tool_text = tool_result.text_for_model or json.dumps(
                        {"ok": tool_result.ok, "error": tool_result.error},
                        ensure_ascii=False,
                    )

                    def _wrap(tool_label: str, tool_call_id: str = tc.id) -> str:
                        # DSP-029a：`tool_call_id` 進標記——模型照抄一次就把三段定址
                        # 一起帶回來，⛔ 不再要它自己另填一欄 `tool_call_id`。
                        if provenance:
                            return wrap_provenance_data(
                                tool_label,
                                tool_call_id,
                                [(p.source, provenance_units(p.text)) for p in provenance],
                                nonce,
                            )
                        return wrap_tool_data(tool_label, raw_tool_text, nonce)

                    try:
                        tool_content = _wrap(name)
                    except ValueError:
                        # 模型送的 tool 名不合形狀守門（例如空白／標記字元）——
                        # registry.call 已經用它判過 NO_MATCH／FORBIDDEN，這裡只是
                        # 包裝層，⛔ 不因此讓整回合崩潰。
                        violations.append(f"BAD_TOOL_NAME:{name!r}")
                        tool_content = _wrap("tool")
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_content,
                        }
                    )

                if budget_hit:
                    return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)
                continue  # 工具結果已回填，回到迴圈頂端再叫一次模型

            # 無 tool_calls ⇒ 這一回合模型嘗試給最終答案
            attempt_no += 1
            content = getattr(message, "content", None) or ""
            try:
                payload = json.loads(content)
                out = AgentOutput.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, TypeError):
                if self._attempt_sink is not None:
                    self._emit_attempt(
                        {
                            "attempt": attempt_no,
                            "kind": None,
                            "raw_len": len(content),
                            "verdict": {"reason": "SCHEMA_PARSE"},
                        }
                    )
                counters.rewrites += 1
                if counters.rewrite_exhausted(self.budget):
                    return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": "SCHEMA: 輸出不符 AgentOutput schema，請重新輸出符合格式的 JSON。",
                    }
                )
                continue

            handoff_dict: Optional[dict] = None
            if out.kind == "handoff":
                # `output_schema.AgentOutput.fact_class` 型別是 `Optional[str]`
                # （刻意放寬，讓 verifier 能判「缺／非法」，見 output_schema.py
                # 模組 docstring）——已經是字串，⛔ 不再 `.value`；缺值時落
                # `FactClass.other`（Runtime 自己決定轉人，不是模型判斷出的
                # 事實類別，沿用既有 `_build_fixed` 的慣例）。
                handoff_dict = {
                    "reason": out.handoff_reason or "no_grounding",
                    "fact_class": out.fact_class or FactClass.other.value,
                    "channel": effective_handoff_channel(None),
                    "message": effective_handoff_message(None),
                }

            # T2（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §3）：
            # 迴圈內改寫提示——與 `_reason_hint`／`_schema_reject_hint` 同形，
            # 介於模型輸出與 Verifier 之間。⛔ **不在出口閘另開一次模型呼叫**
            # （security r1 #1：那條路會跳過 Verifier 全部檢查且沒有 deadline
            # 檢查，正式站觀察模式不可用）。條件全為封閉欄位：`out.kind==
            # "handoff"` 且 `out.handoff_reason=="no_grounding"`（字面值，⛔ 不看
            # `handoff_dict` 那個已經套過 fallback 的版本）、`fact_class` 不在
            # 敏感五類、本回合工具結果非空、且不是「每一筆都 `status=="ok"` 且
            # `empty`」（那種情況本來就該轉走 T2 的 NO_DATA 出口，⛔ 不該被改寫
            # 成瞎編）。命中且改寫預算未耗盡 ⇒ 消耗一次 `max_rewrites`、帶固定
            # 修法句重回模型；**預算已耗盡 ⇒ 直接跳過改寫**（⛔ 不走
            # `counters.rewrite_exhausted` ⇒ `_build_fixed("budget_exhausted")`
            # 那條，否則 `handoff_reason` 會變成 `budget_exhausted`，T2 出口閘
            # 永遠到不了——plan-verifier r1 #6），讓輸出照常往下走進 Verifier，
            # 最終落到 `_apply_handoff_data_exits` 換成 `NO_JUDGEMENT_TEXT`。
            if out.kind == "handoff" and out.handoff_reason in NON_SENSITIVE_HANDOFF_REASONS:
                try:
                    rewrite_fact_class = FactClass(out.fact_class)
                except ValueError:
                    rewrite_fact_class = None
                if (
                    rewrite_fact_class not in SENSITIVE
                    and tool_call_records
                    and not all(r.status == "ok" and r.empty for r in tool_call_records)
                    and not counters.rewrite_exhausted(self.budget)
                ):
                    counters.rewrites += 1
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {"role": "user", "content": HANDOFF_DATA_REWRITE_HINT}
                    )
                    continue

            # DSP-029 F-A：引用解析在 Runtime 做，結果**另傳**給 Verifier——
            # ⛔ 不寫回 `out`／`Sentence` 任何欄位（解析後的原文一旦掛在 AgentOutput
            # 上，就會跟著 `decision_snapshot`／trace 外流）。
            # DSP-029a：**本回合的 `nonce` 一起傳進去**——標記裡的 nonce 必須等於它，
            # 否則 `ref_invalid`。這是「這串標記真的出自本回合資料段」的唯一憑據，
            # ⛔ 不得改成不檢查或用固定值。
            resolved, resolve_errors = resolve_refs(out, tool_results_by_id, nonce)
            verdict = self.verifier.verify(
                out, tool_results_by_id, user_message, handoff_dict,
                resolved=resolved, resolve_errors=resolve_errors)
            verifier_verdicts.append(verdict)
            if self._attempt_sink is not None:
                self._emit_attempt(
                    {
                        "attempt": attempt_no,
                        "kind": out.kind,
                        "fact_class": out.fact_class,
                        "handoff_reason": out.handoff_reason,
                        # U1（security-reviewer r1 F5）：`resolved_unit`＝這一筆各 ref
                        # **解析出來的引文原文**。極性誤殺量測要「句子＋引文並列」逐句
                        # 人看，沒有它重放算不出來。
                        # ⚠️ **只走 attempt sink**（`AGENT_ATTEMPT_LOG_PATH`，dev 專用旗，
                        # ⛔ 線上不設）——引文原文 ⛔ 不進 `TurnTrace`／`TurnResult`／
                        # `decision_snapshot`（那是 2.6 security review P2 擋掉的事）。
                        "sentences": [
                            {
                                "text": s.text,
                                "kind": s.kind,
                                "refs": list(s.refs),
                                "resolved_unit": [
                                    resolved[(si, sj)].quote
                                    for sj in range(len(s.refs))
                                    if (si, sj) in resolved
                                ],
                            }
                            for si, s in enumerate(out.sentences)
                        ],
                        "verdict": verdict.model_dump(),
                        # 觀察模式下「本來會擋、這次只記錄」的類別（`ok=True` 也可能非空）。
                        "observed": list(verdict.observed),
                        "resolve_errors": {
                            f"{i}:{j}": cause for (i, j), cause in resolve_errors.items()
                        },
                    }
                )
            if not verdict.ok:
                counters.rewrites += 1
                logger.info(
                    "agent_verifier_reject trace_id=%s reason=%s rewrites=%d/%d",
                    trace_id, verdict.reason, counters.rewrites, self.budget.max_rewrites,
                )
                if counters.rewrite_exhausted(self.budget):
                    return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)
                messages.append({"role": "assistant", "content": content})
                schema_hint = _reason_hint(verdict)
                if verdict.reason == "SCHEMA":
                    # DSP-028：只回 SCHEMA 模型不知道哪裡錯。DSP-029a 下 SCHEMA 有八種
                    # 成因（見 `_SCHEMA_CAUSE_HINTS`），直接指名成因與
                    # 筆索引即可——⛔ 不再回報「系統把你的 answer 切成幾句」那種提示：
                    # 逐句一筆之後句數不必再對齊，那句話只會誤導模型回頭去湊句數。
                    # 內容只有索引與長度，⛔ 無任何原文（來源原文與模型原文都不放）。
                    schema_hint += "　" + _schema_reject_hint(verdict)
                # 拒因回模型用 role="user"（⛔ 不用 role="system"）：system 訊息
                # 依 PromptAssembler 契約整回合只有一則（見 prompt_assembler.py
                # 「system 訊息只有一則」），迴圈裡補第二則 system 會破壞這個
                # 不變量；role="user" 與既有 SCHEMA 不符重寫走同一慣例（上面
                # `json.JSONDecodeError` 分支）。內容是 `VerifierVerdict.model_dump()`
                # 的結構化拒因（ok/reason/sent/term_id/quote_len），⛔ 無原文
                # ——被拒的 `answer` 只留在 `messages`（模型自己的重寫上下文），
                # ⛔ 不進 `TurnTrace`／`TurnResult`。
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "VERIFIER_REJECT: "
                            + json.dumps(verdict.model_dump(), ensure_ascii=False)
                            + "　請依上述結構化拒因修正後重新輸出符合 AgentOutput schema 的 JSON。"
                            + schema_hint
                        ),
                    }
                )
                continue

            # T3（Plan §4）：**文字假確認**——只做統計，⛔ 不改寫、⛔ 不改文字。
            # 三個封閉條件都成立（`kind=ask` ∧ `ask_target=confirm_intent` ∧ 本回合
            # 沒有 `confirm.request` 呼叫）才記一個旗標；第四個條件（模型散文是否
            # 真的在問「要不要送出」）是開放語義，Plan 明講⛔ 不做，故不判。
            if (
                out.kind == "ask"
                and out.ask_target == "confirm_intent"
                and not any(tc.name == CONFIRM_TOOL_NAME for tc in tool_call_records)
            ):
                violations.append("prose_confirm_suspect")

            trace = TurnTrace(
                trace_id=trace_id,
                tool_calls=tool_call_records,
                llm_calls=llm_calls,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                verifier=verifier_verdicts,
                final_kind=out.kind,
                handoff_reason=(handoff_dict or {}).get("reason"),
                latency_ms=int((self._clock() - start) * 1000),
                violations=violations,
                rules_sha=_rules_sha(),
                outline_sha=_outline_sha(),
                candidate_ids=list(candidate_ids),
                winning_key_kind=dict(winning_key_kind),
                miss_kind=miss_kind,
                has_entry_line=bool(entry_text),
                pre_lookup=pre_lookup_trace,
            )
            result = TurnResult(
                kind=out.kind,
                # DSP-021：模型自判轉人 ⇒ 使用者看到的是固定句（design 元件 7
                # `effective_handoff_message`），⛔ 不是模型自己寫的轉人文字
                # （Verifier 對 handoff 不跑逐句檢查，模型文字沒過尺就不能出去）。
                # DSP-028：`out.answer` 是 `"".join(s.text for s in out.sentences)` 這個
                # 純 property 導出的字串（⛔ 模型不再輸出 `answer` 欄）——Verifier 步①⑤⑥⑦
                # 掃的就是同一個導出點，「掃的字串＝送出的字串」因此是定義而非巧合。
                # T4（walkthrough batch2 §5）：句末標點正規化只在這個唯一組裝點套，
                # ⛔ 不動卡片文字／固定句／對話歷史。
                answer=(
                    handoff_dict["message"] if handoff_dict is not None
                    else normalize_terminal_punctuation(out.answer)
                ),
                handoff=handoff_dict,
                quick_replies=[],
                trace=trace,
                # T1：模型輸出的追問對象原樣帶進載體；正規化（值域外歸零）與
                # 寫進 `agent_state` 都由 `_finalize` 一手包辦，⛔ 不在這裡分兩處判。
                ask_target=out.ask_target,
            )
            return _finalize(result, is_fixed=False)

    # ------------------------------------------------------------------
    async def stream_turn(self, identity: Identity, user_message: str, state: dict):
        """骨架（2.2 接 SSE 線路前只需事件序列正確）：
        `status`（每 `status_interval_s` 秒，用建構時注入的 `clock`／此處另加
        真實 `asyncio.sleep` 輪詢，2.2 換成真正非阻塞等待）→ `answer_chunk`
        （整段一次性 yield，逐字串流是 2.2 的事）→ `metadata`（帶
        `handoff`／`quick_replies`／`trace_id`，見 design 元件 1／7）。
        """
        task = asyncio.ensure_future(self.run_turn(identity, user_message, state))
        last_status = self._clock()
        poll_s = min(0.05, self._status_interval_s)
        while not task.done():
            await asyncio.sleep(poll_s)
            now = self._clock()
            if now - last_status >= self._status_interval_s:
                yield {"event": "status", "data": {}}
                last_status = now
        result = await task
        yield {"event": "answer_chunk", "data": {"text": result.answer}}
        yield {
            "event": "metadata",
            "data": {
                "handoff": result.handoff,
                "quick_replies": result.quick_replies,
                "trace_id": result.trace.trace_id,
            },
        }
