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
import json
import logging
import os
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Protocol

from pydantic import ValidationError

from services import usage_metering
from services.agent.budget import Budget, BudgetCounters
from services.agent.canon.candidate_selector import CandidateSelector
from services.agent.canon.candidate_selector import K as _CANDIDATE_K
from services.agent.canon.canon_assembler import build_canon_toc, get_canon
from services.agent.identity import Identity, Stage, derive_identity_source
from services.agent.mcp_facade import current_stage
from services.agent.outline import CandidateOutlineDoc
from services.agent.output_schema import AgentOutput, VerifierVerdict
from services.agent.prompt_assembler import new_nonce, wrap_provenance_data, wrap_tool_data
from services.agent.provenance_units import (  # OUTLINE_TOOL_CALL_ID 下沉至葉模組（DSP-029 落地取捨④）
    OUTLINE_TOOL_CALL_ID,
    provenance_units,
    resolve_refs,
)
from services.agent.tools.registry import Provenance, ToolRegistry, ToolResult, tool_name_from_openai
from services.conversational_config import (
    effective_handoff_channel,
    effective_handoff_message,
)
from services.presales_gate import FactClass, HandoffReason

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
        tool_timeout_s: float = 3.0,
        status_interval_s: float = 5.0,
        attempt_sink: Optional[Callable[[dict], None]] = None,
        candidate_selector: Optional[CandidateSelector] = None,
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
        self._tool_timeout_s = tool_timeout_s
        self._status_interval_s = status_interval_s

    def _emit_attempt(self, record: dict) -> None:
        """呼叫 `attempt_sink`（若有），任何例外一律吞掉＋`logger.warning`——
        儀表化 ⛔ 不得影響回合本身（tasks 4.3c brief）。"""
        if self._attempt_sink is None:
            return
        try:
            self._attempt_sink(record)
        except Exception:  # noqa: BLE001 — 儀表化，任何 sink 例外都不可外溢
            logger.warning("agent_attempt_sink_failed", exc_info=True)

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

        適用條件：`self._candidate_selector` 有設、`outline` 非 None、
        `get_canon(outline.audience)` 已註冊、且 `outline.audience` 與
        `identity.resolved_audience()` 相同；不適用 ⇒ 原 `outline` 原樣、
        `sel_meta=None`（這**不是**降級——是這條路根本沒有候選機制）。

        回傳 `(outline, sel_meta)`；`sel_meta` 為 `None` 或
        `{"candidate_ids", "winning_key_kind", "miss_kind"}`。
        """
        selector = self._candidate_selector
        if selector is None or outline is None:
            return outline, None
        audience = getattr(outline, "audience", None)
        canon = get_canon(audience) if audience is not None else None
        if canon is None or audience != identity.resolved_audience():
            return outline, None

        toc = build_canon_toc(canon, identity, vendor_business_types=frozenset())

        def _fallback_visible() -> Any:
            visible = selector.index.visible_subset(
                identity, canon, vendor_business_types=frozenset()
            )
            return CandidateOutlineDoc.from_visible(outline, visible, toc)

        try:
            query = _candidate_query(user_message, dialog)
            sel = await selector.select(canon, identity, query, vendor_business_types=frozenset())

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
    async def run_turn(self, identity: Identity, user_message: str, state: dict) -> TurnResult:
        start = self._clock()
        trace_id = uuid.uuid4().hex
        agent_state = state.setdefault("agent", {})
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
            return TurnResult(
                kind="handoff",
                answer=cached.get("answer", ""),
                handoff=cached.get("handoff"),
                quick_replies=list(cached.get("quick_replies", [])),
                trace=trace,
            )

        counters = BudgetCounters()
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
        # DSP-022：當前這句一定是最後一則 user 訊息（歷史由 assembler 從 `dialog` 放前面）。
        messages.append({"role": "user", "content": user_message})

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
            )
            return TurnResult(
                kind="handoff",
                answer=message_text,
                handoff=handoff_dict,
                quick_replies=[],
                trace=trace,
            )

        def _finalize(result: TurnResult, *, is_fixed: bool) -> TurnResult:
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
            _append_dialog(agent_state, user_message, result.answer)
            _emit_agent_decision(result.trace)
            return result

        while True:
            if (self._clock() - start) >= self.budget.deadline_s:
                return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)

            llm_calls += 1
            response = await self.provider.async_client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tool_specs,
                parallel_tool_calls=False,
                response_format=_agent_output_response_format(),
            )
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

                    ms = int((self._clock() - call_start) * 1000)
                    tool_call_records.append(
                        ToolCallRecord(
                            id=tc.id,
                            name=name,
                            args_summary=_args_summary(raw_args),
                            ms=ms,
                            status=_tool_result_status(tool_result),
                            n_items=_tool_result_n_items(tool_result),
                        )
                    )
                    # DSP-029 r13 #3：`OUTLINE_TOOL_CALL_ID` 是**保留字**，模型送來同名
                    # tool_call id 一律拒收 ＋ 記 violation——⛔ 不再加
                    # `and seeded_outline is not None` 這個條件：沒有大綱時放行等於
                    # 讓模型自己造一個叫 `outline` 的來源，之後所有 `outline:*` 引用
                    # 都會解析到它自己塞進來的文字（自證變成自說自話）。
                    if tc.id == OUTLINE_TOOL_CALL_ID:
                        violations.append("tool_call_id_collides_with_outline")
                    else:
                        tool_results_by_id[tc.id] = tool_result
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
                        "sentences": [
                            {"text": s.text, "kind": s.kind, "refs": list(s.refs)}
                            for s in out.sentences
                        ],
                        "verdict": verdict.model_dump(),
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
            )
            result = TurnResult(
                kind=out.kind,
                # DSP-021：模型自判轉人 ⇒ 使用者看到的是固定句（design 元件 7
                # `effective_handoff_message`），⛔ 不是模型自己寫的轉人文字
                # （Verifier 對 handoff 不跑逐句檢查，模型文字沒過尺就不能出去）。
                # DSP-028：`out.answer` 是 `"".join(s.text for s in out.sentences)` 這個
                # 純 property 導出的字串（⛔ 模型不再輸出 `answer` 欄）——Verifier 步①⑤⑥⑦
                # 掃的就是同一個導出點，「掃的字串＝送出的字串」因此是定義而非巧合。
                answer=handoff_dict["message"] if handoff_dict is not None else out.answer,
                handoff=handoff_dict,
                quick_replies=[],
                trace=trace,
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
