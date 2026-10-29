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
import copy
import hashlib
import hmac
import inspect
import json
import logging
import os
import re
import string
import time
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable, Literal, Optional, Protocol

from openai import APITimeoutError
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function as _ToolCallFunction
from pydantic import ValidationError

from services import usage_metering
from services.agent.agent_session import DOCUMENT_CARRY_MAX_TURNS, AgentSession
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
    CLOSED_ACTION_FIELDS,
    CONFIRMATION_REQUIRED_TEXT,
    PHOTO_PAYLOAD_KEYS,
    PHOTO_REUPLOAD_TEXT,
    PHOTOS_UNAVAILABLE_KEY,
    RECEIPT_DATE_HINT_TEMPLATE,
    REPAIR_PHOTOS_MAX,
    fields_before_today,
    receipt_id_of,
    render_receipt,
)
# A8（單一動作登錄）：動作值域一律在呼叫當下以模組參照讀 `confirm_card.CONFIRM_ACTIONS`，
# ⛔ 在 import 期複製一份——否則在登錄表加一個動作，這裡看到的仍是舊集合。
from services.agent import confirm_card as _confirm_card
from services.agent import upload_store as _upload_store
from services.agent.canon.candidate_selector import CandidateSelector
from services.agent.canon.candidate_selector import K as _CANDIDATE_K
from services.agent.canon.canon_assembler import (
    CanonSectionInvisibleError,
    build_canon_toc,
    get_canon,
)
from services.agent.document_extract import (
    DOCUMENT_NOTICE_TEXTS,
    DOCUMENT_TURN_WRITABLE,
    DocumentTurnInput,
    document_writable_action,
)
from services.agent.identity import (
    DEFAULT_ENTRY_CHANNEL,
    Identity,
    Stage,
    derive_identity_source,
)
from services.agent.mcp_facade import current_stage
from services.agent.outline import (
    CANON_VIEW_AUDIENCES,
    CandidateOutlineDoc,
    resolve_vendor_business_types,
)
from services.agent.output_schema import ASK_TARGETS, AgentOutput, VerifierVerdict, WriteIntent
from services.agent.prompt_assembler import new_nonce, wrap_provenance_data, wrap_tool_data
from services.agent.question_sensitivity import question_sensitive
from services.agent.provenance_units import (  # OUTLINE_TOOL_CALL_ID 下沉至葉模組（DSP-029 落地取捨④）
    OUTLINE_TOOL_CALL_ID,
    provenance_units,
    resolve_refs,
)
from services.agent.text_norm import normalize_terminal_punctuation
from services.agent.tools.confirm import (
    CANDIDATE_TYPE_KEY,
    NAME_LENIENT_KEY,
    NAME_LENIENT_MISSING_KEY,
    NAME_LENIENT_MISSING_LEAD_TEXT,
    NAME_LENIENT_TRUNCATED_KEY,
    NameLenientTurnCtx,
    is_name_not_found,
    missing_name_lenient,
    name_early_lookup,
    name_lenient_picked_title,
    name_lenient_rows_for_ids,
    name_precheck_ids,
    name_said_key as _confirm_name_said_key,
    PICK_ESTATE_ID_KEY,
    PICK_NOTE_KEY,
    PICK_NOTE_TEXT_KEY,
    SAID_AMOUNT_KEY as _PR_SAID_AMOUNT,
    SAID_RANGE_KEY as _PR_SAID_RANGE,
    CONFIRM_QUICK_REPLY_VALUES,
    CONFIRM_SPEC,
    candidate_fallback_result,
    CONFIRM_VALUE_SEP,
    PENDING_STATE_EXPIRED,
    PENDING_STATE_LIVE,
    _is_valid_repair_category,
    closed_action_missing_labels,
    confirm_quick_replies,
    is_candidate_shape,
    pick_matches_name,
    write_name_candidates,
    document_confirm_description,
    missing_fields_ask_text,
    missing_labels_ask_text,
    payload_digest,
    pending_token_state,
    redeem_pending,
    sha256_hex,
)
from services.agent import llm_output as LO
from services.agent import write_forms as WF
from services.agent import write_candidates as _wc
from services.agent import name_match as NM
from services.agent import state_claim as SC
from services.agent.bill_period import UNPAID_TERMS as _UNPAID_TERMS
from services.agent.bill_period import parse_period as _parse_period
from services.agent.bill_period import parse_periods as _parse_periods
from services.agent.bill_period import parse_said_range as _parse_said_range
from services.agent.write_forms import write_draft_enabled_from_env
from services.agent.write_forms import write_lifecycle_enabled_from_env
from services.agent.write_forms import write_proposal_enabled_from_env
from services.agent.tools.jgb2 import NOT_FOUND_SOURCE as _JGB2_NOT_FOUND_SOURCE
from services.agent.tools.jgb2 import _candidates_text as _jgb2_candidates_text
from services.agent.tools.jgb2 import candidates_text_for_user as _jgb2_candidates_text_for_user
from services.agent.tools.jgb2 import _bill_format_date as _jgb2_bill_format_date
from services.agent.tools.registry import Provenance, ToolRegistry, ToolResult, tool_name_from_openai
from services.agent.tools.session import write_slot
from services.conversational_config import (
    effective_handoff_channel,
    effective_handoff_message,
)
from services.presales_gate import (
    MODEL_VISIBLE_HANDOFF_REASONS, SENSITIVE, FactClass, HandoffReason,
)
# ⚠️ **import 模組、⛔ 不 `from … import _today`**：兌現閘要在呼叫點取時鐘，
# 與 `tools/confirm` 的閘一同一支函式、同一個時鐘（S1）。
from services.jgb import bills
# ---------------------------------------------------------------------------
# R1 四段管線（Plan `inputs/plan-structural-refactor-20260910.md` §0）：
# 回合資料契約與狀態容器住 `turn_context`、模型前程式段住 `turn_segments`、
# 四道出口閘與 `finalize` 住 `exit_gates`。⛔ 三者都**不 import 本檔**（那會成環）。
#
# ⚠️ 下面這一串 re-export **不是為了好看**：`TurnResult`／`TurnTrace`／
#    `ToolCallRecord`／`make_outcome`／四道閘等名字有 30 幾個既有測試檔與
#    `shadow.py`／`trace_view.py`／`mcp_facade.py` 以 `from services.agent.runtime
#    import …` 取用。R1 是**行為不變的結構整理**，⛔ 不得順手要求那些呼叫端改
#    import——名字留在這裡，搬的只有定義的位置。
# ---------------------------------------------------------------------------
from services.agent import exit_gates
from services.agent.exit_gates import (  # noqa: F401  — re-export（見上方註記）
    ASK_TARGET_TEXT,
    NO_DATA_TEXT,
    NO_JUDGEMENT_TEXT,
    NON_SENSITIVE_HANDOFF_REASONS,
    SCOPE_EXIT_TEXT,
    _apply_ask_target_gate,
    _apply_handoff_data_exits,
    _apply_handoff_without_lookup,
    _apply_scope_exit,
    _handoff_fact_class,
    _sensitive_self_report_overridden,
)
from services.agent.turn_context import (  # noqa: F401  — re-export（見上方註記）
    DIALOG_MAX_MESSAGES,
    ESTATE_CARRY_KEY,
    HANDOFF_CACHE_MAX,
    LAST_ASK_TARGET_KEY,
    OUTCOME_EXPECTS,
    OUTCOME_REF_TYPES,
    OUTCOME_STATES,
    SELECT_SCOPE_KEY,
    _ASK_TARGET_EXPECTS,
    ReservedCallIds,
    ToolCallRecord,
    TurnAccumulator,
    TurnInputsSnapshot,
    TurnResult,
    TurnTrace,
    _append_dialog,
    _candidate_ids_shape_valid,
    _emit_agent_decision,
    _replayed_from,
    _trim_handoff_cache,
    zero_lookup,
    default_outcome,
    make_outcome,
    receipt_ref,
)
from services.agent.turn_segments import run_program_segments

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

#: 第六批 #2（A 交接）：`confirm.request` 以物件＋期別對帳單對到**多筆**時，工具回既有候選形狀
#: （`data["candidates"]`＋`action`／`payload`、無 `card`）。Runtime 把它收成一個 **ask 回合**：
#: 固定句＋候選清單文字（`jgb2._candidates_text` 同一份投影）＋ `select:bill:<id>` 按鈕
#: （與 LIFF 清單點選同一條入向機器值，⛔ 不另開形狀）；⛔ 不建 pending、不出卡。
CONFIRM_CANDIDATES_TEXT = "這戶對到不只一張帳單，請點選要處理的那一張。"
#: B 片 B4：候選清單回合進 dialog 的**程式摘要**（⛔ 清單文字、⛔ 查詢字串；比照 `SELECT_DIALOG_SUMMARY`）。
CONFIRM_CANDIDATES_DIALOG_SUMMARY = "已列出 {n} 筆候選帳單，請使用者點選要處理的那一張"
CONFIRM_CANDIDATES_MAX = 5
#: 打字選定回合給意圖判斷呼叫的候選清單資料段標籤（nonce 包住，`wrap_tool_data`）。
WRITE_CANDIDATES_DATA_LABEL = "write_candidates"
#: action ⇒ (候選清單 domain, select 型別)。封閉表，只有會走期別解析的動作才有列。
_CONFIRM_CANDIDATE_DOMAIN: dict = {"bill_due_extend": ("bills", "bill")}


def _candidate_button_label(row: dict) -> str:
    """候選按鈕文字：編號＋到期日（有才印）。⛔ 不放金額／標題——按鈕要短，細節在清單文字裡。"""
    label = f"編號 {row.get('id')}"
    due = row.get("date_expire")
    if due:
        label += f"｜到期 {_jgb2_bill_format_date(due)}"
    return label

#: line-bot 2026-09-10 回報（單號 12357／12358 vs 對照 12356）：照片辨識出的分類（已過分類樹
#: 封閉映射的 `ImageTurnInput.suggested_category`）沒接到建單參數——`CONFIRM_SPEC` 要模型
#: 「業務沒講分類就不要填」，模型照做，卡就落回「其他（未指定）」、描述「（未填寫）」。
#: 修法在程式層、⛔ 不改提示詞：照片回合把**封閉值**（分類樹名稱）存進 `agent_state[
#: IMAGE_SUGGESTION_KEY]`（照片與出卡常常不同回合：照片→問急不急→答「不急」→出卡），
#: `confirm.request`（`repair_create`）執行前由程式補進 payload 缺的 `category_name`；
#: 描述沒人講時填 `IMAGE_DESCRIPTION_TEMPLATE`（辨識描述（淨化、
#: 截長）優先，缺則部位＋原因短標籤，再缺退分類名；⛔ 這些文字只進修繕單描述，不進模型資料段）。
#: 一次性：任何 `confirm.request` 呼叫即清；新照片覆寫。
IMAGE_SUGGESTION_KEY = "image_suggestion"
IMAGE_DESCRIPTION_TEMPLATE = "照片辨識：{label}"


def _image_description_label(suggestion: dict) -> str:
    """描述用的文字：辨識描述優先；缺 ⇒ 部位＋原因；都缺 ⇒ 分類名。"""
    desc = suggestion.get("description")
    if isinstance(desc, str) and desc.strip():
        return desc.strip()
    item = suggestion.get("item") if isinstance(suggestion.get("item"), str) else ""
    reason = suggestion.get("reason") if isinstance(suggestion.get("reason"), str) else ""
    label = f"{item}{reason}".strip()
    return label or str(suggestion.get("category_name") or "").strip()


def _apply_image_suggestion_to_confirm_args(raw_args: Any, suggestion: Any, *,
                                            leaf_swap: bool = True) -> tuple:
    """`confirm.request`／`repair_create` 的 payload 缺 `category_name`／`description`
    時由照片建議補上；`category_name` 恰是照片葉節點的父分類時換成葉節點。回 `(new_args, applied)`；`applied` 是補了哪些欄位的清單
    （空＝原樣）。任何形狀不對（非 dict、payload 非 JSON 物件、action 非
    repair_create、建議缺值）一律原樣回傳，⛔ 不在此 raise——形狀由 confirm 工具自己驗。
    只補**缺值**（鍵不存在、None、去空白為空）；模型有給就不動（唯一例外：父分類換葉節點）。

    UD-3：`leaf_swap=False`（照片分類由被取代的待確認卡帶到更正後的新卡）⇒ 只補缺值、⛔ 換葉節點
    ——卡後更正時 payload 已有的分類是客人（經草稿）講的，客人的話為準。"""
    if not isinstance(raw_args, dict) or not isinstance(suggestion, dict):
        return raw_args, []
    category = suggestion.get("category_name")
    if not isinstance(category, str) or not category.strip():
        return raw_args, []
    payload_raw = raw_args.get("payload")
    if not isinstance(payload_raw, str):
        return raw_args, []
    try:
        payload = json.loads(payload_raw)
    except (TypeError, ValueError):
        return raw_args, []
    if not isinstance(payload, dict) or payload.get("action") != "repair_create":
        return raw_args, []
    applied: list = []
    def _blank(v: Any) -> bool:
        return v is None or (isinstance(v, str) and not v.strip())
    if _blank(payload.get("category_name")):
        payload["category_name"] = category.strip()
        applied.append("category_name")
    elif (
        # 站內幫手 S3-live A7：模型自填的正是照片葉節點的**父分類**（例：家具 vs 椅子）⇒
        # 換成葉節點（同一大類底下更細，不與模型矛盾）。其他值 ⛔ 不動。
        leaf_swap
        and isinstance(suggestion.get("parent_category_name"), str)
        and isinstance(payload.get("category_name"), str)
        and payload["category_name"].strip() == suggestion["parent_category_name"].strip()
        and category.strip() != suggestion["parent_category_name"].strip()
    ):
        payload["category_name"] = category.strip()
        applied.append("category_name_leaf")
    if _blank(payload.get("description")):
        payload["description"] = IMAGE_DESCRIPTION_TEMPLATE.format(label=_image_description_label(suggestion))
        applied.append("description")
    if not applied:
        return raw_args, []
    new_args = dict(raw_args)
    new_args["payload"] = json.dumps(payload, ensure_ascii=False)
    return new_args, applied


# ════════════════════════════════════════════════════════════════════
# 第六批 #10：物件記憶（`estate_carry`）——line-bot 2026-09-10 回報
# ════════════════════════════════════════════════════════════════════
#
# 病灶：使用者先講「基隆獨立共生公寓」再傳照片／再說「幫我報修」，模型手上沒有
# 任何「剛剛講的是哪個物件」的東西，於是回頭反問物件名稱（或把 `estate_name`
# 留空 ⇒ `confirm.request` 直接 `INVALID_INPUT`）。
#
# ⚠️ **與 `SELECT_SCOPE_KEY` 是兩件事，⛔ 不得混用**：那個是點清單釘住的**授權
#    範圍**（`_enforce_tool_scope` 拿它擋別戶）；這個只是「使用者最近講到哪個
#    物件」的**記憶**，⛔ 不具任何授權意義、⛔ 不參與任何範圍比對。
#    範圍釘住時本鍵一律**不寫也不注入**（同 `recent_refs`／`completed_actions`
#    的 L15 紀律：釘住的對話不該再讓另一戶的名字漏進來）。
# ⛔⛔ **名稱不得進 trace／log／`decision_snapshot`**：物件名稱等同識別碼，
#    trace 與計量表都會序列化落地（同 `has_ref`／`pre_lookup` 那一套紀律）。


#: 物件名稱的長度上限（超過即不記）。比 `_pre_lookup_trigger` 的 6 字寬，因為
#: 物件全名（「基隆獨立共生公寓」）本來就過不了那道短名詞閘；但仍要有上限——
#: 沒有上限時，一段被判成「唯一命中」的長句會整段被當成物件名稱送進確認卡。
ESTATE_CARRY_NAME_MAX_CHARS = 40

#: 照片回合注入資料段的固定前綴（⛔ 常數，名稱由程式接在後面）。
ESTATE_CARRY_TEXT_PREFIX = "本對話最近提到的物件："
ESTATE_CARRY_PROVENANCE_SOURCE = "session:estate_carry#1"
ESTATE_CARRY_LABEL = "session.estate_carry"


def _estate_carry_of(agent_state: Any) -> Optional[dict]:
    """讀出物件記憶；不是封閉形狀（非 dict／`name` 非字串或空）⇒ `None`。

    ⚠️ 這份狀態會被序列化進 `form_sessions.collected_data` 再讀回來，所以讀出來
    的東西 ⛔ 不得假設形狀正確——舊 session 沒有這個鍵，別的版本可能寫成別的樣子。
    """
    if not isinstance(agent_state, dict):
        return None
    # verifier 2026-09-10 P3：範圍釘住時讀點也一律 None——⛔ 不靠下游 `_scope_gate_confirm_request`
    # 救「舊物件補進 payload」；寫點與注入點本來就擋，讀點補齊同一紀律。
    if agent_state.get(SELECT_SCOPE_KEY) is not None:
        return None
    carry = agent_state.get(ESTATE_CARRY_KEY)
    if not isinstance(carry, dict):
        return None
    name = carry.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    estate_id = carry.get("id")
    return {
        "name": name.strip(),
        # ⚠️ `id` 與 `name` **同樣去空白**：讀出來的東西來自
        # `form_sessions.collected_data`（別的版本／舊 session 可能寫成別的樣子），
        # 兩格只正規化其中一格的話，`" 77 "` 這種值會原樣流到下游做等值比對。
        "id": estate_id.strip() if isinstance(estate_id, str) and estate_id.strip() else None,
    }


def _write_estate_carry(agent_state: dict, name: Any, estate_id: Any = None) -> bool:
    """三個寫點共用的唯一寫入口；寫成功回 `True`。

    ⛔ **釘住範圍時不寫**（`SELECT_SCOPE_KEY` 有值）：那一段對話的物件由範圍決定，
    再記一個「最近提到的物件」只會多一條讓別戶名字漏進來的路。
    名稱一律過 `sanitize_data_piece`（控制字元／零寬／假標記）並截長度上限，
    ⛔ 不接受非字串、空白、超長。`estate_id` 缺值就是 `None`（⛔ 不猜）。
    """
    if not isinstance(agent_state, dict):
        return False
    if _scope_estate_id(agent_state) is not None:
        return False
    if not isinstance(name, str):
        return False
    clean = sanitize_data_piece(name).strip()
    if not clean or len(clean) > ESTATE_CARRY_NAME_MAX_CHARS:
        return False
    rid: Optional[str] = None
    if isinstance(estate_id, (str, int)) and str(estate_id).strip():
        rid = str(estate_id).strip()
    AgentSession(agent_state).write_estate_carry({"name": clean, "id": rid})
    return True


def _estate_carry_from_estates_data(data: Any, keyword: str) -> Optional[tuple]:
    """`jgb2.query.estates`（keyword 查詢）的回傳 → `(name, estate_id)`；
    **判不出唯一一個物件就回 `None`**（⛔ 不挑第一筆）。

    兩種「唯一」的形狀，都來自 `tools/jgb2.py` 同一支 `query_estates`：
      * `_ok_single(scoped=True)`：keyword 恰好命中一列 ⇒ `data["scope"]["estate_id"]`。
        這條路 `data` 裡沒有列上的 `title`（`facts` 是組好的句子），所以名稱用
        **查進去的那個關鍵字**——那正是 `repair_create` 的 `estate_name` 契約
        （`tools/action.py::_resolve_estate`「業務口述的物件名稱，由系統比對」），
        ⛔ 不去解析 `facts` 字串把標題挖出來（那是把另一支的輸出格式當契約）。
      * `_ok_candidates` 恰好一列：列上有 `title`，用它（比關鍵字精確）。
    sentinel（查無）不帶 `scope` 鍵也沒有候選 ⇒ 自然落空，⛔ 不靠巧合。
    """
    if not isinstance(data, dict):
        return None
    candidates = data.get("candidates")
    if isinstance(candidates, list) and len(candidates) == 1:
        row = candidates[0]
        if isinstance(row, dict) and row.get("found") is not False:
            title = row.get("title")
            if isinstance(title, str) and title.strip():
                return title, row.get("id")
    scope = data.get("scope")
    if isinstance(scope, dict):
        return keyword, scope.get("estate_id")
    return None


def _apply_estate_carry_to_confirm_args(raw_args: Any, carry: Any) -> tuple:
    """`confirm.request` 的 payload 缺 `estate_name` 時由物件記憶補上。
    回 `(new_args, applied)`；`applied` 是補了哪些欄位的清單（空＝原樣）。

    形狀比照 `_apply_image_suggestion_to_confirm_args`（同一個落點、同一條紀律）：
    只補**缺值**（鍵不存在、None、去空白為空），模型有給就不動；任何形狀不對
    （非 dict、payload 非 JSON 物件、action 不在 `CONFIRM_ACTIONS`、記憶缺名稱）
    一律原樣回傳，⛔ 不在此 raise——形狀由 confirm 工具自己驗。
    ⚠️ `CONFIRM_ACTIONS` 兩支都補：`repair_create` 的卡直接印「物件」那一行；
       `bill_due_extend` 今天的卡不印它，但 payload 多一個鍵不影響
       `payload_digest`／`render`（保留鍵只有 `today`），而缺編號時要靠物件名稱
       對帳單的那條路（第六批 #2，單元 A）讀的就是這一格。
    """
    if not isinstance(raw_args, dict) or not isinstance(carry, dict):
        return raw_args, []
    name = carry.get("name")
    if not isinstance(name, str) or not name.strip():
        return raw_args, []
    payload_raw = raw_args.get("payload")
    if not isinstance(payload_raw, str):
        return raw_args, []
    try:
        payload = json.loads(payload_raw)
    except (TypeError, ValueError):
        return raw_args, []
    if not isinstance(payload, dict) or payload.get("action") not in _confirm_card.CONFIRM_ACTIONS:
        return raw_args, []
    existing = payload.get("estate_name")
    if existing is not None and not (isinstance(existing, str) and not existing.strip()):
        return raw_args, []
    payload["estate_name"] = name.strip()
    new_args = dict(raw_args)
    new_args["payload"] = json.dumps(payload, ensure_ascii=False)
    return new_args, ["estate_name"]


# ════════════════════════════════════════════════════════════════════
# 站內幫手 S3（§3h 第 1～3、6 點；DSP-073／DSP-076）：文件與照片進 `confirm.request`
# ════════════════════════════════════════════════════════════════════
#: 文件回合／文件暫存有效時，`total` 這類「文件對照表會填、但這次沒填」的數字欄位，
#: 模型給的值必須出自使用者原話（⛔ 讓模型從文件資料段抄一個金額進卡）。
_DOCUMENT_GUARDED_NUMBER_FIELDS: dict = {"manual_bill_create": ("total",)}


def _payload_of(raw_args: Any) -> Optional[dict]:
    """`confirm.request` 參數裡的 payload（JSON 物件字串）⇒ dict；形狀不對 ⇒ `None`。"""
    if not isinstance(raw_args, dict) or not isinstance(raw_args.get("payload"), str):
        return None
    try:
        payload = json.loads(raw_args["payload"])
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _with_payload(raw_args: dict, payload: dict) -> dict:
    new_args = dict(raw_args)
    new_args["payload"] = json.dumps(payload, ensure_ascii=False)
    return new_args


def _apply_photos_to_confirm_args(raw_args: Any, suggestion: Any) -> tuple:
    """`repair_create`：**無條件**刪掉模型帶的照片相關鍵，再由本回合／照片建議裡的
    伺服端中繼資料寫入（F10／S3-5）。回 `(new_args, 標記清單)`；非 repair_create ⇒ 原樣。

    照片相關鍵＝`PHOTO_PAYLOAD_KEYS` ∪ 名稱含 photo／image 的任何鍵（不分大小寫）。
    超過 `REPAIR_PHOTOS_MAX` 張 ⇒ **全部不附**，只寫張數讓卡上說明。
    """
    payload = _payload_of(raw_args)
    if payload is None or payload.get("action") != "repair_create":
        return raw_args, []
    marks: list = []
    for key in list(payload):
        lowered = str(key).lower()
        if key in PHOTO_PAYLOAD_KEYS or "photo" in lowered or "image" in lowered:
            payload.pop(key, None)
            marks.append("photo_keys_dropped")
    photos = suggestion.get("photos") if isinstance(suggestion, dict) else None
    omitted = suggestion.get("photos_omitted") if isinstance(suggestion, dict) else None
    if isinstance(photos, list) and photos:
        if len(photos) > REPAIR_PHOTOS_MAX:
            payload["broken_photos_omitted"] = len(photos)
            marks.append("photos_omitted")
        else:
            payload["broken_photos"] = [dict(p) for p in photos if isinstance(p, dict)]
            marks.append("photos_attached")
    elif (isinstance(omitted, int) and not isinstance(omitted, bool)
          and omitted > REPAIR_PHOTOS_MAX):
        # UD-3：被取代的舊卡是「超過上限、全部不附」⇒ 新卡照樣說明（張數由程式帶，⛔ 模型）。
        payload["broken_photos_omitted"] = omitted
        marks.append("photos_omitted")
    if not marks:
        return raw_args, []
    return _with_payload(raw_args, payload), sorted(set(marks))


# ════════════════════════════════════════════════════════════════════
# UD-3：照片隨卡（出卡時重新編碼、卡後更正帶到新卡、兌現／作廢釋放暫存）
# ════════════════════════════════════════════════════════════════════
#: 待確認筆存「這張卡用到的照片建議（⛔ 照片中繼資料）」的鍵：卡後更正重出卡時，照片
#: 判出的分類／描述由這裡帶到新卡（照片本身在 payload 的 `broken_photos`）。⛔ 進卡、⛔ 進雜湊。
PENDING_PHOTO_SUGGESTION_KEY = "photo_suggestion"
#: 待確認筆的照片已釋放（兌現或作廢）⇒ 之後 ⛔ 再帶到別張卡。
PENDING_PHOTOS_RELEASED_KEY = "photos_released"
#: 照片建議裡可以跟著卡走的欄位（全是封閉來源：分類樹名稱、辨識結果的短字串）。
_PHOTO_SUGGESTION_FIELDS = ("category_name", "item", "reason", "description", "parent_category_name")
#: 兌現時照片不可用的收據錯誤碼（只在 `pending["receipt"]`，⛔ 進 `ToolError` 值域）。
PHOTOS_UNAVAILABLE_RECEIPT_ERROR = "PHOTOS_UNAVAILABLE"
V_PHOTOS_CARRIED = "card_photos_carried"
V_PHOTOS_UNAVAILABLE_AT_REDEEM = "photos_unavailable_at_redeem"


def _photo_suggestion_fields(suggestion: Any) -> Optional[dict]:
    """照片建議 ⇒ 只留可跟卡走的欄位（值是字串或 `None`）；沒有分類 ⇒ `None`（不存）。

    ⚠️ 讀回的待確認筆會落 DB 再讀回，⛔ 假設形狀正確：非 dict、值型別不對一律丟。"""
    if not isinstance(suggestion, dict):
        return None
    out = {k: suggestion.get(k) for k in _PHOTO_SUGGESTION_FIELDS
           if isinstance(suggestion.get(k), str) and suggestion.get(k).strip()}
    if not isinstance(out.get("category_name"), str):
        return None
    return out


def _payload_photo_shas(payload: Any) -> list:
    photos = payload.get("broken_photos") if isinstance(payload, dict) else None
    if not isinstance(photos, list):
        return []
    return [p["sha256"] for p in photos
            if isinstance(p, dict) and isinstance(p.get("sha256"), str)]


async def _encode_card_photos(identity: Any, photos: list) -> list:
    """S11：照片建議（原檔 sha256）⇒ 卡上的照片中繼資料（**重新編碼後**那一份）。

    每張：以本回合身分重算綁定、在暫存找到那一筆（`photo_source`）⇒ 用 Pillow 重新編碼成 JPEG
    （`documind_client.reencode_photo_jpeg`：`exif_transpose`、轉 RGB、長邊 ≤ 2400、⛔ EXIF／GPS、
    解碼再編碼所以檔尾夾帶的內容也不會留下）⇒ 存回暫存（原檔丟掉）⇒ `{photo-N.jpg, image/jpeg,
    size, sha256}`。已編過的同一筆 ⇒ 沿用（同一筆只有一份「卡上那一份」）。

    找不到（網址回滾模式、服務重啟、到期）、編碼失敗、編完超過上限 ⇒ 該張**保留原中繼資料**：
    卡照樣印張數，兌現時 `repair_create` 對不到 ⇒ ⛔ 寫入、回固定句（S5，fail-closed）。"""
    from services.documind_client import reencode_photo_jpeg

    out = [dict(p) for p in photos if isinstance(p, dict)]
    try:
        binding = _upload_store.binding_from_identity(identity, "repair")
    except ValueError:
        return out
    used: list = []
    for i, meta in enumerate(out):
        found = _upload_store.STORE.photo_source(meta.get("sha256"), binding, exclude_refs=used)
        if found is None:
            continue
        ref, data, done_sha = found
        used.append(ref)
        if done_sha is None:
            try:
                jpeg = await asyncio.to_thread(reencode_photo_jpeg, data)
            except Exception:  # noqa: BLE001 — 解不出／炸彈閘 ⇒ 保留原中繼資料（兌現時 fail-closed）
                continue
            done_sha = _upload_store.STORE.set_photo(ref, binding, jpeg)
            if done_sha is None:
                continue
            size = len(jpeg)
        else:
            size = len(data)
        out[i] = {"filename": f"photo-{i + 1}.jpg", "content_type": "image/jpeg",
                  "size": size, "sha256": done_sha}
    return out


def _document_carry_of(agent_state: Any) -> Optional[dict]:
    """讀出文件暫存並驗**封閉形狀**；不合 ⇒ `None`（呼叫端據此清掉）。

    ⚠️ 狀態會序列化進 `form_sessions.collected_data` 再讀回來，⛔ 不假設形狀正確。
    """
    if not isinstance(agent_state, dict):
        return None
    carry = AgentSession(agent_state).get_document_carry()
    if carry is None or set(carry) != {"action", "typed_fields", "receipt_date", "turns"}:
        return None
    action = carry.get("action")
    if action not in DOCUMENT_TURN_WRITABLE.values():
        return None
    allowed_keys = {f.key for f in CLOSED_ACTION_FIELDS[action]}
    typed = carry.get("typed_fields")
    if not isinstance(typed, list) or not all(
        isinstance(p, list) and len(p) == 2 and p[0] in allowed_keys
        and isinstance(p[1], (str, int, float)) and not isinstance(p[1], bool)
        for p in typed
    ):
        return None
    turns = carry.get("turns")
    if isinstance(turns, bool) or not isinstance(turns, int) or not 0 <= turns < DOCUMENT_CARRY_MAX_TURNS:
        return None
    receipt_date = carry.get("receipt_date")
    if receipt_date is not None and not (
        isinstance(receipt_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", receipt_date)
    ):
        return None
    return {"action": action, "typed_fields": [tuple(p) for p in typed],
            "receipt_date": receipt_date, "turns": turns}


#: DSP-091 分工防偏離片 DG-1：`confirm.request` 出卡來源標記的前綴（寫進 `acc.violations`，只加字串）。
CONFIRM_SOURCE_PREFIX = "confirm_source:"


def _confirm_model_reason(*, proposal_active: bool, document: Any, agent_state: Any,
                          readonly_view: bool) -> str:
    """DG-1：模型自呼 `confirm.request` 且照舊執行時，依狀態判定「為什麼是模型來源」。

    純函式、⛔ 引用 A+ 提議分支的同一個布林運算式（要獨立判定，才抓得到該條件被改壞）。
    值域：`flag_off`（三開關任一 off＝回復組態）、`document`（文件回合）、`document_carry`（文件暫存
    有效）、`select_scope`（點選範圍）、`readonly_view`（影子回合）；都不成立 ⇒ `unregistered`
    （一般寫入回合卻由模型參數出卡＝分工被打穿，不變量 45 判 FAIL）。
    """
    if not proposal_active:
        return "flag_off"
    if document is not None:
        return "document"
    if _document_carry_of(agent_state) is not None:
        return "document_carry"
    if isinstance(agent_state, dict) and agent_state.get(SELECT_SCOPE_KEY) is not None:
        return "select_scope"
    if readonly_view:
        return "readonly_view"
    return "unregistered"


def _document_user_texts(agent_state: dict, user_message: str, turns: int) -> list:
    """「使用者原話」＝`dialog` 裡 user 項的最後 `turns` 則＋本回合訊息（§3h 第 3 點）。

    ⛔ 不複製進暫存或任何新鍵；`dialog` FIFO 截斷後不足就以現存者為準。
    """
    texts = [user_message] if isinstance(user_message, str) else []
    if turns > 0:
        users = [m.get("content") for m in (agent_state.get("dialog") or [])
                 if isinstance(m, dict) and m.get("role") == "user"]
        texts = [t for t in users[-turns:] if isinstance(t, str)] + texts
    return texts


def _number_in_texts(value: Any, texts: list) -> bool:
    """數字是否以**完整數字 token** 出現在使用者原話裡（千分位逗號視同不存在）。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        if not value.is_integer():
            return False
        value = int(value)
    for text in texts:
        normalized = re.sub(r"(?<=\d)[,，](?=\d{3}(?!\d))", "", text)
        if str(value) in re.findall(r"\d+", normalized):
            return True
    return False


def _apply_document_to_payload(
    payload: dict, *, action: str, typed_fields: list, user_texts: list,
    free_text: tuple,
) -> Optional[str]:
    """文件回合／暫存有效時對 payload 的**就地**處置；回 `None`＝可送，否則回拒因代碼。

    依序（§3h 第 2、3 點）：
      ① 不在 `typed_fields` 的 `text` 型欄位必須是使用者原話的逐字子字串，否則刪掉
         （＝缺 ⇒ 缺欄追問）；`_DOCUMENT_GUARDED_NUMBER_FIELDS` 的數字欄同理；
      ② `typed_fields` **覆寫**進 payload（模型給的同名值丟棄）；
      ③ `estate_create.title` 缺值 ⇒ 程式取 `address`；
      ④ 縱深：任何字串欄位含本回合擷取的自由文字值 ⇒ 拒（`document_free_text_in_payload`）。
    """
    typed_keys = {k for k, _ in typed_fields}
    for f in CLOSED_ACTION_FIELDS.get(action, ()):
        if f.kind != "text" or f.key in typed_keys or f.key not in payload:
            continue
        value = payload.get(f.key)
        if not (isinstance(value, str) and value.strip()
                and any(value.strip() in t for t in user_texts)):
            payload.pop(f.key, None)
    for key in _DOCUMENT_GUARDED_NUMBER_FIELDS.get(action, ()):
        if key in typed_keys or key not in payload:
            continue
        if not _number_in_texts(payload.get(key), user_texts):
            payload.pop(key, None)
    for key, value in typed_fields:
        payload[key] = value
    if action == "estate_create":
        title = payload.get("title")
        address = payload.get("address")
        if not (isinstance(title, str) and title.strip()) and isinstance(address, str) and address.strip():
            payload["title"] = address
    needles = [t for t in (free_text or ()) if isinstance(t, str) and t.strip()]
    if needles:
        for value in payload.values():
            if isinstance(value, str) and any(n in value for n in needles):
                return "document_free_text_in_payload"
    return None


#: 使用者按下按鈕送回來的機器值：`^confirm_(submit|edit|cancel):<16 位十六進位>$`。
#: ⚠️ **等值**比對（`fullmatch`、無前後綴）——⛔ 不做子字串比對：那會讓
#: 「confirm_submit:abcd… 這是什麼意思？」這種自由文字誤觸發一次真實寫入。
#: 三個前綴**由 `CONFIRM_QUICK_REPLY_VALUES` 組出來**（那組常數又轉引
#: `services/form_contract.py` 的 `QR_*`——舊鏈隔離 S3 從 `conversational_engine`
#: 抽出，值不變），⛔ 不在此另抄字面量。
_CONFIRM_VALUE_RE = re.compile(
    r"^(?:%s)%s([0-9a-f]{16})$"
    % (
        "|".join(re.escape(v) for v in CONFIRM_QUICK_REPLY_VALUES),
        re.escape(CONFIRM_VALUE_SEP),
    )
)


def _parse_confirm_value(message: Any) -> Optional[tuple]:
    """`"confirm_submit:0123456789abcdef"` → `("confirm_submit", "0123…")`；不是機器值 ⇒ `None`。

    🔴 **2026-09-12：`.match` → `.fullmatch`（獨立驗證抓到，業主裁示後改）。**
    上方常數的註解一直寫著「**等值**比對（`fullmatch`、無前後綴）」，實作卻是
    `.match` 配 `^…$`——**Python 的 `$` 允許結尾換行**，於是
    `"confirm_submit:<pid>\n"` 會命中並**兌現一次真實寫入**，正是那段註解宣稱
    要防的形狀。對照 `_parse_select_value` 用的一直都是 `fullmatch`。
    ⛔ 不得改回 `.match`：失敗方向是「多執行一次寫入」，不可回復。
    釘住的測試：`tests/unit/agent/test_runtime_confirm_segment_req.py`
    的 `test_parse_confirm_value_*`。
    """
    if not isinstance(message, str):
        return None
    m = _CONFIRM_VALUE_RE.fullmatch(message)
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

# ════════════════════════════════════════════════════════════════════
# V2（Plan `plan-walkthrough-fixes-batch4-20260909.md` §3）：有前文的零查詢
# ════════════════════════════════════════════════════════════════════
#
# 「本對話最近出現的數字編號」——**不可引用**的資料段，供模型判斷「對象不明
# 但最近提過某個編號」時先當它是那一筆，⛔ 不是可引用的事實來源（編號本身不是
# 一筆查證過的事實，只是「這串數字最近出現過」這件事）。

#: 切詞用的分隔字集：既有的空白／標點字集（`_PRE_LOOKUP_TRIM_CHARS`）加上
#: 一般空白——⛔ 這是切詞用的分隔規則，不是又一條 id 判定規則；id 判定仍只
#: 靠下面重用的 `_PRE_LOOKUP_ID_RE.match`（整詞比對，同 U3 trigger A）。
_RECENT_REFS_SPLIT_RE = re.compile(r"[\s" + re.escape(_PRE_LOOKUP_TRIM_CHARS) + r"]+")

#: 掃描 dialog 的視窗（最近 6 則，user／assistant 各算一則）與去重後上限。
_RECENT_REFS_DIALOG_WINDOW = 6
_RECENT_REFS_MAX = 5

RECENT_REFS_PROVENANCE_SOURCE = "session:recent_refs#1"
RECENT_REFS_LABEL = "session.recent_refs"

#: security r1 #6：8 位數字同時涵蓋日期／金額，刻意照單全收（封閉值域無法
#: 分辨「這串數字是編號還是日期」）——標籤如實講清楚，⛔ 不假裝只有編號。
RECENT_REFS_TEXT_PREFIX = "本對話最近出現的數字編號（可能含日期或金額）："

#: T2 改寫分支專用的固定定義句——無插值、⛔ 不編造範例名稱／編號。
RECENT_REFS_REWRITE_HINT = (
    "對象不明但本對話最近提到編號時，先當它是那一筆："
    "依資料段回答或先查詢，⛔ 不反問哪一戶。"
)

def _recent_ref_ids_from_text(text: Any) -> list[str]:
    """從一段自由文字裡切出整詞為 4–9 位數字的 token（重用 `_PRE_LOOKUP_ID_RE`，
    ⛔ 不另開一條 id 判定正則）。非字串／空字串 ⇒ 空列表。"""
    if not isinstance(text, str) or not text:
        return []
    return [tok for tok in _RECENT_REFS_SPLIT_RE.split(text) if _PRE_LOOKUP_ID_RE.match(tok)]


def _recent_ref_ids(agent_state: dict, dialog: list) -> list[str]:
    """V2（§3）：本對話最近出現過的編號——來源＝`dialog` 最近 6 則（user／
    assistant 皆掃）＋ `completed_actions` 的 `ref_id`；由近到遠去重、上限 5。

    ⚠️ dialog 由近到遠先掃（新的優先），`completed_actions` 接在後面補（同一
    筆通常已經在 dialog 的助理回覆文字裡出現過，這裡只是補漏，⛔ 不是另一套
    優先序判定）。
    """
    ordered: list[str] = []
    seen: set = set()

    def _add(token: str) -> None:
        if token not in seen:
            seen.add(token)
            ordered.append(token)

    recent_dialog = dialog[-_RECENT_REFS_DIALOG_WINDOW:] if dialog else []
    for row in reversed(recent_dialog):
        content = row.get("content") if isinstance(row, dict) else None
        for token in _recent_ref_ids_from_text(content):
            _add(token)
    for item in reversed(agent_state.get(COMPLETED_ACTIONS_KEY) or []):
        if not isinstance(item, dict):
            continue
        if item.get("ref_type") == "estate":
            # 站內幫手 S5（S5-15，業主「印物件名稱，不印 id」）：物件 id 是內部值，
            # ⛔ 進「最近編號」資料段（那一段會被模型念出來）。
            continue
        ref_id = item.get("ref_id")
        if isinstance(ref_id, str) and _PRE_LOOKUP_ID_RE.match(ref_id):
            _add(ref_id)
    return ordered[:_RECENT_REFS_MAX]


def _is_stats_not_supported(name: str, result: Any) -> bool:
    """2026-10-15 正式機：`jgb2.stats.*`／`confirm.request`（新寫入動作）接真 JGB 時回
    「尚未開放」標記（`data.not_supported`）；固定句就是 `data.facts`（工具端的程式常數）。"""
    data = getattr(result, "data", None)
    return (
        (name.startswith("jgb2.stats.") or name == CONFIRM_TOOL_NAME)
        and bool(getattr(result, "ok", False))
        and isinstance(data, dict)
        and data.get("not_supported") is True
    )


def _is_marked_not_found(result: Any) -> bool:
    """站內幫手 S5（§3i 第 2 點）：這個 `NO_MATCH` 是不是**真的查過、確定沒有**——
    只認帶查無標記（`jgb2.NOT_FOUND_SOURCE` 來源的 provenance）的那一種；其餘
    `NO_MATCH`（上游失敗、缺身分、registry 吞例外…）一律是「沒查成」。"""
    if getattr(result, "ok", True) or getattr(result, "error", None) != _PRE_LOOKUP_NOT_FOUND_ERROR:
        return False
    return any(getattr(p, "source", None) == _JGB2_NOT_FOUND_SOURCE
               for p in (getattr(result, "provenance", None) or []))


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


def _pending_creator(identity: Any) -> dict:
    """待確認筆的建立者鍵（F1）：`{"user_id", "role_id"}`——**原值**、⛔ 正規化。"""
    return {"user_id": getattr(identity, "user_id", None),
            "role_id": getattr(identity, "role_id", None)}


#: 2026-10-15 A2：上一回合追問的是名稱類（物件／社區／地址，`last_ask_target` 封閉值）時，使用者
#: 這句若是 7～30 字、無句讀的一串名稱，也拿去比對物件（正式機：回答「學生獨立套房可租補」被當成
#: 新的知識題轉人，或被模型拆成物件「學生獨立套房」＋描述「可租補」）。空白、括號、連字號是物件
#: 名稱常見字元，不擋；句讀（逗號、句號、問號、驚嘆號、分號、冒號）才擋。
_PRE_LOOKUP_ANSWER_MAX_CHARS = 30
_PRE_LOOKUP_SENTENCE_PUNCT: frozenset = frozenset("，。！？；：,.!?;:")
_PRE_LOOKUP_NAME_ASK_TARGETS: frozenset = frozenset({"estate", "community", "address"})


def _pre_lookup_trigger(message: str, *, after_name_ask: bool = False) -> Optional[tuple[str, str]]:
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
    # A2：上一回合追問名稱 ⇒ 較長的一串名稱也當成可能的物件名稱（查無不注入，同短名詞規則）。
    if after_name_ask and len(core) <= _PRE_LOOKUP_ANSWER_MAX_CHARS:
        if any(ch in _PRE_LOOKUP_SENTENCE_PUNCT for ch in core):
            return None
        return "keyword", core
    return None


# ════════════════════════════════════════════════════════════════════
# L15 (a)：清單進場後的**會話範圍**（戶＝物件 `estate_id`）
# ════════════════════════════════════════════════════════════════════
#
# ⚠️ **程式判定、⛔ 不交模型**（`feedback_no_llm_mechanical_decode`）：「是不是
#    同一戶」是 `estate_id` 等值，封閉可算；讓模型判等於把資料邊界交給一個會
#    被說服的東西。
# ⚠️ **fail-closed**：有範圍而某一筆算不出 `estate_id`（缺欄位／`None`）一律
#    當成範圍外，⛔ 不放行——放行的失敗方向是別戶資料進答案。


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


#: 迴圈內改寫提示的固定句（定義，⛔ 無插值）——與 `_REASON_HINTS`／
#: `_SCHEMA_CAUSE_HINTS` 同一條紀律：只有方法，無原文。
HANDOFF_DATA_REWRITE_HINT = "資料段有內容；判斷題依資料段給建議並引用，⛔ 不轉人。"

#: 迴圈內每一則「回模型的回饋」共用的外殼。這些訊息依 PromptAssembler 契約只能走
#: role="user"（system 整回合只有一則），模型會把它讀成使用者說的話而**回覆它**
#: ——線上 2026-09-09 實測：最近編號改寫句被複誦成「收到，我會把本對話最近出現的
#: 編號當成那筆…」，使用者原題沒答。外殼把身分講清楚：系統回饋、不是使用者說的、
#: ⛔ 不回覆／不複述／不確認它，要做的是重新回答使用者最後一則訊息。
#: 四個改寫點（SCHEMA／VERIFIER_REJECT／資料段改寫／最近編號改寫）一律經
#: `rewrite_feedback()` 組裝，⛔ 不各自手寫；定義句本身（⛔ 無插值）不變。
REWRITE_FEEDBACK_SUFFIX = (
    "　這則是系統回饋，不是使用者說的話：⛔ 不回覆、不複述、不確認它；"
    "請重新回答使用者最後一則訊息，輸出符合 AgentOutput schema 的 JSON。"
)


def rewrite_feedback(tag: str, body: str) -> str:
    """組一則回模型的迴圈內回饋：`<TAG>: <定義句或結構化拒因>` ＋固定外殼。"""
    return f"{tag}: {body}{REWRITE_FEEDBACK_SUFFIX}"


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


#: `reasoning_effort` 允許值（OpenAI gpt-5 系列）；封閉集合，⛔ 不在程式內以字串推導。
#: 2026-09-10 加 `none`：gpt-5.6 系列在 chat.completions 帶 function tools 時只接受
#: `reasoning_effort="none"`（其餘值回 400「use /v1/responses or set reasoning_effort to 'none'」）；
#: `minimal` 對它反而不支援。值域仍封閉，實際能用哪個由模型決定、由啟動實測守。
REASONING_EFFORT_VALUES: frozenset = frozenset({"none", "minimal", "low", "medium", "high"})

#: 每次模型呼叫的輸出上限預設值（env `AGENT_MAX_COMPLETION_TOKENS` 覆寫；依據見 `AgentRuntime.__init__`）。
DEFAULT_MAX_COMPLETION_TOKENS = 2000

#: 輸出被上限截斷（`finish_reason == "length"`）時記進 `violations` 的旗標（⛔ 不帶任何內容）。
LLM_OUTPUT_TRUNCATED = "llm_output_truncated"

#: 正式接線（`plan-oss-wiring-step1-20261018.md` §3.2）：只在 `clean_llm_output=True` 時記。
#: 回應 content 夾了推理標籤並已剝除（⛔ 不帶任何內容）。
LLM_OUTPUT_REASONING_STRIPPED = "llm_output_reasoning_stripped"
#: 最終輸出原文 `json.loads` 失敗、改以逐 `{` 解碼擷取到合法 `AgentOutput`。
LLM_OUTPUT_JSON_EXTRACTED = "llm_output_json_extracted"

#: W2（`plan-truncation-w2-20261017.md`）：逾時的呼叫拿不到 usage ⇒ 以已收到的字元數估算（1 字元 ＝ 1 token，寧可高估）。
LLM_USAGE_ESTIMATED = "llm_usage_estimated"
#: ⛔ 不在串流中因連續空白提早中止：灌空白的呼叫約七成最後仍 `finish=stop` 且輸出可用，中止會把它們變成
#: 失敗、重寫又常再灌空白 ⇒ 轉人（W2 C2～C5 與對照重放，DSP-116）。卡太久由回合期限切斷。
#: 截斷之後要走 SCHEMA 重寫時，剩餘期限低於此值就不重寫、直接 `budget_exhausted` 固定句。
#: 來源：W2 第 0 步 run2 正常主呼叫（`finish=stop`，126 筆）p95 2.63 秒（STEP0「補充量測」）。
SCHEMA_REWRITE_MIN_REMAINING_S = 2.6


class _DialogActPreempt(Exception):
    """對話動作標籤先於主模型完成、且結果是程式出口（轉人／無未決收尾）⇒ 取消進行中的
    主模型呼叫。⚠️ 與 `_ModelCallDeadline` **分流**：`_run_model_loop` 接住後走 `_dialog_act_exit`，
    ⛔ 落入 `budget_exhausted`（W2 期限中斷是 `asyncio.timeout` 丟 `_ModelCallDeadline`）。"""


class _ModelCallDeadline(Exception):
    """主模型呼叫碰到回合期限（`Budget.deadline_s`）被中斷；`_run_model_loop` 接住走 `budget_exhausted` 固定句。"""


async def _close_stream(stream: Any) -> None:
    """關閉串流（SDK `AsyncStream.close()` 為 coroutine；假串流可為同步）。"""
    close = getattr(stream, "close", None)
    if close is None:
        return
    res = close()
    if inspect.isawaitable(res):
        await res

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

#: T1（Plan §2）：**呼叫端進場句** `context` 在本回合資料段裡的來源代碼與工具
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
CALLER_CONTEXT_PROVENANCE_SOURCE = "caller:context#1"
CALLER_CONTEXT_LABEL = "caller.context"

#: V4（Plan batch4 §5）：常數前綴，讓模型分得清「呼叫端畫面上印給使用者看的
#: 字」跟「使用者自己說的話」——⛔ 不含任何呼叫端輸入（純常數字串），加在
#: `sanitize_data_piece(context)` **之後**（先清乾淨再貼前綴，前綴本身不需要
#: 再清一次）。
CALLER_CONTEXT_PREFIX = "畫面提示（呼叫端顯示給使用者的，不是使用者說的話）："

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
EMPTY_SESSION_TEXT = "這段對話裡使用者還沒有說過話。"

#: W9 U2：文件事實在本回合資料段裡的來源代碼與工具標籤——同影像事實**同一套**
#: 注入紀律。一回合只有**一段**文件事實（多頁的擷取結果在門面就已合併成一段
#: 程式組的句子），故序號固定 1。
#: ⚠️ `citable=True`（與 T1 的 `context` **不是同一個處置**）：歸納必須引用它。
#:    這個代價由兩件事承擔——W9-1（文件回合關寫入面）與 W9-2（欄位值不得自成
#:    一個可引用 unit）。S9-11 封閉值原則在文件回合的可接受條件＝「文字只能被
#:    引用、不能被執行、不能進任何寫入 payload」。
DOCUMENT_PROVENANCE_SOURCE = "document:extraction#1"
DOCUMENT_DATA_LABEL = "document.extraction"

#: W9 U2：擷取不到任何欄位（`unreadable`／全 null／`failed`）時的固定句。
#: ⛔ **不進模型**（同 `IMAGE_FAILED_TEXT` 三句的紀律）：沒有可引用的東西時
#: 讓模型講話，講出來的只會是它自己編的。
DOC_UNREADABLE_TEXT = "這份文件我讀不出可用的欄位；換一張清楚一點的，或直接把重點打字給我。"

#: W9-1：文件回合碰到寫入面時的固定句。文件回合的**非目標**就是寫回 JGB，
#: 這道閘是邊界層的封閉（⛔ 不靠模型自律、⛔ 不靠正本的指示）。
DOC_NO_WRITE_TEXT = "這一回合只做文件歸納，沒辦法在這裡送出申請或異動；要辦的話請回 JGB 平台操作。"

#: `ImageTurnInput.status` 的封閉值域。
IMAGE_STATUSES: frozenset = frozenset({"ok", "partial", "failed", "timeout"})


@dataclass(frozen=True)
class ImageTurnInput:
    """門面交給 Runtime 的**照片回合輸入**——**全封閉值**（Plan W8 (2)／r2 裁 (a)）。

    ⛔ **沒有 bytes、沒有網址**：照片的原始 bytes 只在 `mcp_facade` 的記憶體裡活過
    抓檔→縮圖→辨識那一段。vision 自由文字（`suggested_description`／部位／原因）
    **只走修繕單描述**，
    ⛔ 不進模型資料段——模型看到的 `facts` 仍是程式組句。

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
    #: 辨識的部位／原因**短標籤**（門面 `_short_label` 過濾：只留中英字母、
    #: ≤12 字）；只用來組修繕單描述「照片辨識：{部位}{原因}」，⛔ 不進模型資料段。
    suggested_item: Optional[str] = None
    suggested_reason: Optional[str] = None
    #: 辨識描述（淨化、≤200 字）可進修繕單描述；⛔ 不進模型資料段。
    suggested_description: Optional[str] = None
    #: `suggested_category` 是葉節點時，它所屬的大類名（否則 `None`）。
    #: 只供 `_apply_image_suggestion_to_confirm_args` 判斷「模型填的是不是這個葉節點的父分類」。
    suggested_parent_category: Optional[str] = None
    #: 站內幫手 S3（F10／S3-5）：本回合**已過閘、已完成辨識**的照片中繼資料
    #: `({filename, content_type, size, sha256}, …)`——⛔ 沒有 bytes、⛔ 沒有網址。
    #: 只用來附進修繕單（經一次性的照片建議），⛔ 不進模型資料段。
    photos: tuple = ()

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


#: `session.slots.set` 的工具名。⚠️ **這是第二份字面量**——唯一正本是
#: `services/agent/tools/session.py:SLOTS_SET_SPEC["name"]`。⛔ 不在本檔 import
#: 那個模組：runtime 已被 `mcp_facade` import，鏈路越長越容易繞成環——這是一般性
#: 的循環 import 風險考量，⛔ 不因為 `session.py` 現在的依賴變輕（舊鏈隔離 S3
#: 之前它會連帶拉進 `services.conversational_engine`；S3 之後只拉 `services.
#: form_contract` 這種輕量葉模組）就當作理由消失——runtime→session→…→runtime
#: 的環路風險與 session.py 具體 import 了什麼無關，是拓樸本身的風險。
#: 兩份不得漂：`tests/unit/agent/test_session_confirm_tools_req.py` 有一條把兩者
#: 釘在一起的回歸案，改名時它會紅。
SLOTS_SET_TOOL_NAME = "session.slots.set"

#: state 內槽位表的鍵——**頂層**（`form_sessions.collected_data.slots`）。
#: ⚠️ 2.9 對齊：2.1 原本讀 `state["agent"]["slots"]`，而 2.4 的
#: `session.slots.set` 寫的是頂層 `slots`（原與舊鏈 `conversational_engine.
#: TransactionState.slots` 同一個位置——舊鏈的交易面向也讀它，該模組已隨舊鏈
#: 於 2026-09-10 退役，位置本身**不因此改變**：頂層 `slots` 仍是唯一正本，
#: 只是不再有第二個讀者）。兩處不一致 ⇒ 工具寫進去的槽位 runtime 永遠讀不到。
#: 以 design（元件 3／`form_sessions.collected_data`）為準取**頂層**。
#: ⛔ 別改回 `state["agent"]["slots"]`。
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
      - 儲存側（`services/agent/tools/session.py:write_slot`）存的是
        `{key: {"value": ..., "source": ..., "confirmed": ...}}`——這個形狀
        原是與舊鏈 `conversational_engine.SlotValue` 共用同一格 jsonb 的代價
        （該模組已隨舊鏈於 2026-09-10 退役）；形狀本身**不因此改變**，改了
        既有 DB 資料列讀不到，⛔ 不是「舊鏈沒了就可以自由改」。
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
            {"type": "string", "enum": list(MODEL_VISIBLE_HANDOFF_REASONS)},
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
        # gpt-oss 第一片：值域寫進說明（由 `ASK_TARGETS` 產生，⛔ 不另抄字面量）——gpt-oss 不讀 enum
        # （推理原文「The allowed ask_target values? Not given explicitly」），漏填即被 ask_target_invalid 擋。
        "description": (
            "kind=ask 時必填：這一句要問使用者的東西，只能是下列其中一個值："
            + "、".join(ASK_TARGETS)
            + "；其他 kind 填 null。"
        ),
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


def _document_confirm_tool_specs(tool_specs: list, document: Any) -> list:
    """放行的文件回合 ⇒ `confirm.request` 的說明後面附上該動作的 payload 欄位定義（R4(2)）。

    站內幫手 S3-live 修正：S3-live A14 收據回合模型兩度以猜的鍵名呼叫 `confirm.request`，
    被封閉鍵擋下後轉人——欄位定義寫在 `jgb2.action.<action>` 的說明裡，而那支工具在
    文件回合不可見（W9-1）。**只改這一回合 `tool_specs` 的說明文字**（新 dict，⛔ 改
    registry 那一份）；工具集合、可見性與 W9-1 三道擋一律不動。非文件回合／不放行 ⇒ 原樣。
    """
    action = document_writable_action(document)
    if action is None:
        return tool_specs
    extra = document_confirm_description(action)
    if not extra:
        return tool_specs
    out: list = []
    for t in tool_specs:
        fn = t.get("function") if isinstance(t, dict) else None
        if isinstance(fn, dict) and tool_name_from_openai(fn.get("name", "")) == CONFIRM_TOOL_NAME:
            t = {**t, "function": {**fn, "description": (fn.get("description") or "") + extra}}
        out.append(t)
    return out


#: 站內幫手 S3-live 修正 R3：謄本回合**程式驅動**的那一次 `confirm.request` 的固定摘要
#: （`summary` 只進紀錄、⛔ 不出示，見 `CONFIRM_SPEC`）。純常數。
DOCUMENT_PROGRAM_CONFIRM_SUMMARY = "依使用者上傳的建物謄本建立物件。"

#: 程式驅動只用在這些動作——卡值**全部**來自 `typed_fields`（D4）＋程式導出（`title`＝
#: `address`），模型在這一步沒有可貢獻的值。收據（`manual_bill_create`）⛔ 列入：合約、
#: 帳單項目、繳費期限都在使用者原話裡，只有模型讀得出來（程式驅動會把使用者已講過的
#: 再問一次）。
DOCUMENT_PROGRAM_CONFIRM_ACTIONS: frozenset = frozenset({"estate_create"})


class _ProgramFunction:
    __slots__ = ("name", "arguments")

    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _ProgramToolCall:
    __slots__ = ("id", "function")

    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.function = _ProgramFunction(name, arguments)


class _ProgramMessage:
    """形狀同 provider 回的 `message`（`content`＋`tool_calls`），讓程式驅動的那一次
    `confirm.request` 走**同一條**工具迴圈（暫存、覆寫、出卡／缺欄追問、範圍閘）。"""

    __slots__ = ("content", "tool_calls")

    def __init__(self, tool_calls: list) -> None:
        self.content = None
        self.tool_calls = tool_calls


def _document_program_message(document: Any, nonce: str) -> Optional["_ProgramMessage"]:
    """謄本回合放行 ⇒ 程式自己的一次 `confirm.request`（payload 只有 `action`）；否則 `None`。

    payload ⛔ 帶任何值：`typed_fields` 與 `title`＝`address` 由同一條迴圈的
    `_apply_document_to_payload` 寫進去（與模型呼叫時逐位同一段程式）。
    tool_call id 由 nonce 導出、前綴不在 `ReservedCallIds` 的九個之內。
    """
    action = document_writable_action(document)
    if action not in DOCUMENT_PROGRAM_CONFIRM_ACTIONS:
        return None
    args = json.dumps(
        {"summary": DOCUMENT_PROGRAM_CONFIRM_SUMMARY,
         "payload": json.dumps({"action": action}, ensure_ascii=False)},
        ensure_ascii=False,
    )
    return _ProgramMessage([_ProgramToolCall(f"docprog-{nonce[:8]}", CONFIRM_TOOL_NAME, args)])


# ════════════════════════════════════════════════════════════════════
# 寫入草稿由程式掌握（DSP-085）
# 意圖改由專用的意圖判斷呼叫取得、續答由程式依上一句程式追問的欄位接收
# ════════════════════════════════════════════════════════════════════
#
# 程式掌握「要不要進寫入流程、還缺什麼、何時出卡」；模型只負責抽出使用者話裡的欄位值
# （W1b：**另發一次**意圖判斷呼叫，與主模型並行；主輸出 `AgentOutput` 不再帶寫入意圖）與講話。
# 卡、雜湊綁卡、兌現（DSP-038）一律不變：程式觸發的那一次 `confirm.request` 走**同一條**工具
# 迴圈（範圍閘、`WRITE_NOT_SUPPORTED_ACTIONS`、照片覆寫、物件記憶補值、保留 id 檢查全部照舊）。
# ⛔ 草稿值不進 trace／`decision_snapshot`（只記動作名與鍵名，見 `write_forms.draft_trace_marks`）。

#: 程式觸發那一次 `confirm.request` 的固定摘要（`summary` 只進紀錄、⛔ 不出示，見 `CONFIRM_SPEC`）。
WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY = "依對話中使用者提供的欄位建立。"
#: 程式觸發的 tool_call id 前綴（＋nonce；⛔ 不在 `ReservedCallIds` 內——它是工具呼叫不是資料段）。
WRITE_DRAFT_PROGRAM_ID_PREFIX = "wdprog-"
#: 觸發門檻：剩餘期限至少這麼多秒（涵蓋非終結結果時多一次模型呼叫；否則不觸發、保留模型原輸出）。
WRITE_DRAFT_PROGRAM_MIN_REMAINING_S = 6.0
#: 草稿注入段的來源代碼與工具標籤（同其他程式資料段的注入紀律；`citable=False`）。
WRITE_DRAFT_PROVENANCE_SOURCE = "session:write_draft#1"
WRITE_DRAFT_LABEL = "session.write_draft"
#: W1b §8.5-4：觸發判斷點等意圖判斷呼叫的上限＝`min(這個秒數, 剩餘期限 − 觸發門檻)`
#: （probe2 有 4/63 筆 5.5～7.3 秒）。等待用 `asyncio.wait`（⛔ 自動取消）。
WRITE_INTENT_WAIT_MAX_S = 8.0
#: W1c §9.1-1／§9.7 F1：程式優先入口等意圖判斷呼叫的上限（秒）。`asyncio.wait` 只判「task 是否
#: 完成」（⛔ 自動取消）；未完成 ⇒ 不走程式優先，task 原樣留給輸出後觸發點（W1b）與 trace 收尾。
WRITE_DRAFT_PROGRAM_FIRST_WAIT_S = 3.0
#: W1c §9.11-3：程式優先等待分級——上限 `WRITE_DRAFT_PROGRAM_FIRST_WAIT_S` 只用在**回合開始時已有草稿**
#: 的回合；無草稿的回合（多數是知識題）只等這麼多秒（§9.10 根因 4：每個知識回合都先等意圖）。
#: 未完成的處理不變（§9.7 F1：不消耗、留給輸出後觸發點）。
WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S = 1.0
#: E 片 §4.1-3 (c)：主模型最終輸出要進 `_write_draft_after_output` 與出口閘之前，對話動作標籤未完成時至多再等的秒數
#: （仍未完成 ⇒ 用主模型輸出、記 `dialog_act_fallback`）。
DIALOG_ACT_AFTER_OUTPUT_WAIT_S = 1.0
#: E 片：追問欄位中第一次標籤為 `resolved` ⇒ 另發一次同輸入的標籤確認呼叫，至多等這麼多秒（以回合剩餘期限
#: 為界）；未完成 ⇒ 重問缺欄。
DIALOG_ACT_FIELD_CONFIRM_WAIT_S = 3.0
#: W1b §8.6-3b：意圖判斷呼叫在組 trace 時仍未完成 ⇒ `cancel()`，prompt token 以
#: 「輸入字元數 ÷ 這個比值」估算計入（中文正本約 1.1 字元／token，`reference_canon_token_ratio`）。
WRITE_INTENT_CANCEL_CHARS_PER_TOKEN = 1.1
#: W1b §8.1-2／安全處置 5b：問句判準（結構規則，⛔ 語意詞表）。先 `sanitize_data_piece`＋NFKC，
#: 再去尾端空白與句末字元，最後一字是問號或「嗎／呢」⇒ 問句。
_QUESTION_TRAILING_CHARS = "。！!～~、.…"
_QUESTION_MARKS = ("？", "?", "﹖")
_QUESTION_PARTICLES = ("嗎", "呢")


def _is_question(text: Any) -> bool:
    """當句是不是問句（W1b §8.1-2：結構規則）。⚠️「冷氣不冷嗎」這類會被判成問句——業主
    選項原文已知並接受（再追問一次）。"""
    s = unicodedata.normalize("NFKC", sanitize_data_piece(text))
    while True:
        trimmed = s.rstrip().rstrip(_QUESTION_TRAILING_CHARS)
        if trimmed == s:
            break
        s = trimmed
    return s.endswith(_QUESTION_MARKS) or s.endswith(_QUESTION_PARTICLES)


@dataclass
class _WriteDraftTurn:
    """本回合的草稿**回合內狀態**（掛在 `TurnAccumulator.write_draft`；⛔ 不落地）。

    - `draft`：目前的草稿（已過 `write_forms.load_draft` 驗形狀）或 `None`；
    - `owner`：建立者鍵（`_write_draft_owner`）；
    - `user_texts`：本會話使用者訊息（`dialog` 的 user 端＋本句）——值閘的唯一比對來源；
    - `asked`：**上一回合**程式缺欄追問所問欄位的表單鍵（回合開頭從草稿讀出，草稿裡的那一份
      已立刻寫回 `[]`，W1b 安全處置 1c）；
    - `had_draft`：回合開始時即有草稿（W1b 安全處置 2d：物件補值只對它生效）；
    - `frozen`：`asked` 非空且當句是問句 ⇒ 本回合凍結（W1b §8.5-3）；
    - `created`／`merged`／`caught`／`filled`：觸發條件（W1b §8.1-4：意圖呼叫建立或合併了
      草稿，或程式接收了值）；
    - `activity`：本回合有寫入相關動作——沒有就 `idle_turns+1`；
    - `intent_consumed`：本回合的意圖判斷結果已取用過（只取一次）；
    - `triggered`：本回合已程式觸發過（每回合上限 1 次）；
    - `model_confirm_ok`：本回合模型自己呼叫 `confirm.request` 且成功；
    - `caught_name`／`caught_segment`：本回合前置查詢唯一命中而寫進草稿的物件名稱（系統值）與
      當句被判為物件名稱的那一段（查詢關鍵字）——W1c §9.11-2 的比對來源（⛔ 落地、⛔ 進 trace）。
    """

    draft: Optional[dict]
    owner: str
    user_texts: list
    asked: list = field(default_factory=list)
    had_draft: bool = False
    frozen: bool = False
    created: bool = False
    merged: bool = False
    caught: bool = False
    filled: bool = False
    activity: bool = False
    intent_consumed: bool = False
    triggered: bool = False
    model_confirm_ok: bool = False
    caught_name: Optional[str] = None
    caught_segment: Optional[str] = None
    #: 第 3 步 A2：本回合**由使用者句子**寫進草稿的鍵（意圖合併過值閘的鍵、整句填入的鍵、
    #: 前置查詢補的物件名稱）——卡後改欄位只比對這些鍵與綁定卡的值（⛔ 比整份草稿）。
    touched: set = field(default_factory=set)
    #: 第 3 步 A2／A7(2)：要重出卡、但綁定那張卡燒不到（已兌現／過期／不是本 session）⇒
    #: 不重出卡，回合由程式固定句結束（`_write_draft_reissue_exit`）。
    reissue_blocked: bool = False
    #: A2 這一關本回合已判「不重出卡」⇒ 輸出後觸發點 ⛔ 再判一次（同一回合只判一次）。
    reissue_held: bool = False
    #: 第 3 步 #9b（Q5）：本回合 A2 已成功燒掉綁定卡 ⇒ 之後程式觸發的 `confirm.request` 若沒出成卡
    #: （非終結結果），回合由程式固定句結束（⛔ 交模型）。
    reissue_burned: bool = False
    #: A-2a 修正 1：本回合以 `redeem_pending` **燒成功、且燒之前為 live** 的綁定卡 pid（`redeem_pending` 綁
    #: pid＋session＋未兌現＋未過期；同值支另要 `pending_token_state` 為 live）。只供
    #: `_write_candidates_card_pick` 判「綁定卡帶著的選定」可不可以帶回；過期後才燒的 ⛔ 設。
    reissue_live_pid: Optional[str] = None
    #: 第 3 步 #9g：回合開始時讀回、已驗形狀的「最近送出」標記（`WF.load_last_submitted`）或 `None`。
    last_submitted: Optional[dict] = None
    #: 第 3 步 #9g：意圖判斷呼叫的布林欄位（`WF.MODIFIES_SUBMITTED_KEY`）恰為 `true`。
    modifies_submitted: bool = False
    #: 第 3 步 #9g：本回合判為「修改剛送出的那一筆」⇒ 不建草稿、不出卡，程式固定句結束回合。
    submitted_edit: bool = False
    #: A+ 片 AP-2：綁定卡有效、值相同 ⇒ `{"pid", "card", "action"}`（卡文字＝以存下的 payload
    #: 帶當日重排版、雜湊已核對）；回合由 `_write_draft_card_still_valid_exit` 結束。
    card_still_valid: Optional[dict] = None
    #: A+ 片 AP-2（業主裁 Q2）：本回合**使用者句子**帶出的值（意圖合併、整句填入）有被值閘丟掉。
    #: 模型提議被丟的值 ⛔ 算（模型參數常夾帶原話沒有的值）。
    user_value_dropped: bool = False
    #: 回合開頭讀回、已驗形狀且綁定本草稿／本建立者／本欄位名稱的候選集，或 `None`。
    candidates: Optional[dict] = None
    #: 本回合使用者原話——名稱寬鬆比對的整句來源（只活在本回合；⛔ 落地、⛔ 進 trace）。
    user_message: str = ""
    #: F12：本回合的名稱寬鬆比對脈絡（`name_match.NameLenientTurn`，首次需要時建立；每回合寬鬆最多 1 次、
    #: 畫面清單與候選集同一份結果）。
    name_lenient: Any = None
    #: A-2a：本回合候選集選定成立（按鈕或打字）⇒ 程式依草稿觸發 `confirm.request`（`program_pick`）。
    picked: bool = False
    #: A-2a：本回合是 `pick:` 按鈕選定（⛔ 呼叫主模型與意圖判斷呼叫）。
    pick_button: bool = False
    #: A-2a（A2-R4、A2-R7 (d)）：本回合打字選定不成立 ⇒ 程式依草稿重發、重列同一份候選。
    reask: bool = False
    #: E 片 §4.1-7（E-R13）：追問欄位中、AI 把當句標成 `resolved`（確認呼叫也不是 `none`）或標籤未完成 ⇒ 程式依草稿重發
    #: （回缺欄追問，⛔ 交主模型；`_dialog_act_not_field_answer`）。
    fill_reask: bool = False
    #: 意圖判斷呼叫回的 `pick_id`（動態 enum 值）；未附候選段 ⇒ `None`。
    intent_pick_id: Optional[str] = None
    #: A-2a：本回合實際附給意圖判斷呼叫的候選編號（＝動態 enum 去掉 `none`）。
    pick_offered: tuple = ()
    #: A-2a 修正 2（verifier F1）：本回合意圖判斷呼叫有附 `record_rechoice` 欄位（`_write_candidates_carry_open`
    #: 成立的回合）。沒附 ⇒ 綁定卡帶著的選定一律不帶回。
    rechoice_offered: bool = False
    #: 修正 2：意圖判斷呼叫回的 `record_rechoice`（`WF.intent_record_rechoice`：值域內字串或 `None`）。
    record_rechoice: Optional[str] = None
    #: 修正 2：AI 恰回 `other` ⇒ 程式作廢綁定卡、依草稿名稱重新解析（即使本句沒有改到任何欄位值）。
    rechoice: bool = False
    #: 「選對紀錄」片 §4.2-1：回合開始時草稿的 `(estate_name, period)`（延期繳費）；本回合變動了 ⇒ 客人
    #: 先前講的比對值（`said_amount`／`said_range`）清掉（本回合又講了新的值則保留新的）。
    pr_anchor: Optional[tuple] = None
    #: 「選對紀錄」片 §4.2-3：本回合附給意圖判斷呼叫的候選列（編號 ⇒ 列）；打字選定時比對客人講的值用。
    pick_rows: dict = field(default_factory=dict)
    #: F12 r6（§11.4 第 1、4 點；R6-S9）：本回合帶身分取得、候選集 `ids` 內的列（編號 ⇒ 列；不分開關一律保留）——
    #: 「候選集內講法」比對系統正名、已撤回重列、r6-3 告知句的唯一來源。⛔ 落地、⛔ 進 trace。
    offered_rows: dict = field(default_factory=dict)
    #: 選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.3「讀不讀 `target`」）：本回合意圖判斷呼叫
    #: **真的送出**指令版 schema（候選集已選定、`_write_candidates_intent_kwargs` 附得出候選段；系統句帶現選定編號）。
    #: 沒設（候選段附不出、未選定、已撤回、無候選集）⇒ ⛔ 讀 `target`（假模型照回也不讀）。
    cmd_offered: bool = False
    #: 同上 §4.3「名稱值一律規則」：**回合開始時**候選集已選定、仍綁定本草稿（`_write_draft_begin` 取快照）。⛔ 沿用
    #: `post_pick_start`（後者已撤回時也為 `True`；已撤回回合照第 5 輪，Q1 (a)）。換動作時不清（原話 38 修 W1）。
    cmd_scope_start: bool = False
    #: 意圖判斷呼叫回的原始 `target`（`WF.intent_pick_target`：**未驗證**，缺鍵 ⇒ `None`）；只在 `cmd_offered` 且
    #: 解析成功的回合讀（`_write_candidates_cmd_effect` 逐項驗）。
    intent_target: Any = None
    #: F12 r6（§11.4 第 2 點「判定順序」）：本回合程式驗證過的改選目標（`pick_id` 或整句只打的編號，∈ `ids` 且
    #: ≠ 現選定），名稱欄合併之前算出；名稱合併依它丟棄名稱值（⛔ 名稱合併先解綁、使改選失效）。
    repick_target: Optional[str] = None
    #: F12 r6：本回合打字改選成立的編號（r6-3 告知句用）；`None` ⇒ 本回合沒有改選。
    repick_id: Optional[str] = None
    #: F12 r6：本回合寬鬆改寫寫進草稿的系統正名（`name_lenient_picked_title`，已過 `sanitize_data_piece`）與其編號。
    rewrite_title: Optional[tuple] = None
    #: F12 r6（第 2、7a 點）：候選集已撤回、本回合要由程式重列同一份 `ids`（觸發條件之一；出卡入口的關口重列）。
    relist: bool = False
    #: F12 r6（§11.4 第 2 點「判定順序」）：模型提議合併（早於意圖呼叫）暫存不併的名稱欄值 `(表單鍵, 原值)`，
    #: 留到 `_write_draft_decide` 拿到 `pick_id` 後依名稱合併規則處理。
    deferred_names: list = field(default_factory=list)
    #: **回合開始時**候選集已選定或已撤回、且仍綁定本草稿
    #: （`_write_draft_begin` 讀回綁定檢查後取快照）⇒ 本回合 ⛔ 整句填入（`_write_draft_fill_answer`，所有文字欄）。
    post_pick_start: bool = False
    #: 第 5 輪 §11.15.3 第 6 點：本回合意圖判斷呼叫解析成功且過 `WriteIntent` 驗證（含 `action=none`）。
    #: 解析失敗（含第 5 點重送後仍失敗）⇒ `False`，名稱合併照現行。
    intent_parsed: bool = False
    #: 第 5 輪 §11.15.3 第 6 點：本回合名稱值先收集、不合併（`_write_candidates_name_rule` 回 `"collect"`），等算出
    #: 驗過且未被退回的改選目標 X 之後再決定去向（⛔ 名稱合併先解綁、使改選或矛盾判定失效）。
    name_collect: bool = False
    #: 第 5 輪：收集到的名稱值 `(來源, 原值)`；來源＝`"intent"`（同一支動作的意圖結果）／`"blocked"`（被擋下的另一
    #: 動作，§11.15.3 第 4 點）／`"deferred"`（主模型提議暫存）。⛔ 落地、⛔ 進 trace。
    collected_names: list = field(default_factory=list)
    #: 第 5 輪 §11.15.3 第 6 點決定 2：本回合判為矛盾 ⇒ 之後同一回合的名稱值（含主模型再提議的）一律丟棄、不解綁。
    name_conflict: bool = False
    # ── 填欄只填答覆（plan-fill-answer-only-20261027 §4.1）。以下全部只活在本回合（B7：⛔ 落地、⛔ 進 agent_state、
    #    草稿、trace、決策快照、日誌；violation 只記 `WF.V_FILL_*` 固定字串）。──
    #: 本回合送出的寫入意圖呼叫帶了資料段規則與 schema（開關 on 的寫入回合）。`False` ⇒ 本節全部不生效（改前行為）。
    fill_active: bool = False
    #: 追問回合：送出意圖呼叫之前依已知狀態判一次——回合開始即有草稿、`asked` 非空、非凍結。
    fill_followup: bool = False
    #: 回合開始那份草稿（物件本身）。B4、B5、`answer_text` 只在目前草稿**就是它**時生效；任何路徑換成新草稿 ⇒ 不生效。
    fill_start_draft: Optional[dict] = None
    #: 回合開始那份草稿當時已填的欄位值（複本；B5「已填的非追問欄」依它判）。
    fill_start_fields: dict = field(default_factory=dict)
    #: 追問回合附給意圖呼叫的追問欄位標籤（表單標籤；有附才讀 `answer_text`）。
    fill_asked_labels: tuple = ()
    #: 驗過的資料段：最新一句**原句**裡對應各段的原字（依序；空段已略過）。`None` ⇒ 資料段未知。
    fill_data: Optional[list] = None
    #: 驗過的答覆段：原句原字（`""` ⇒ 沒有答覆）；`None` ⇒ 未附、未知或資料段未知。
    fill_answer: Optional[str] = None
    #: 模型提議（③／②）在意圖結果取用前就到 ⇒ 本回合資料段未知（之後讀到的資料段一律不用）。
    fill_proposal_first: bool = False
    #: 本回合至少一個與草稿現值不同的新值沒套用（資料段未知、資料段外拒收、追問回合不覆寫已填欄）。
    fill_not_applied: bool = False
    # ── 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.1～4.3）。與上一節（單欄追問回合）互斥；全部只活在本回合
    #    （§4.3 第 10 點：⛔ 落地、⛔ 進 agent_state、草稿、trace、決策快照、日誌；`repr` 也不帶）。──
    #: 本回合是寬回合：送出的寫入意圖呼叫帶資料段規則與 schema（`_fill_begin_intent_call` 唯一設定點）。
    fill_wide: bool = field(default=False, repr=False)
    #: 寬回合種類：`FILL_WIDE_FIRST`（首句）／`FILL_WIDE_CARD`（卡後）／`FILL_WIDE_MULTI`（多欄）；非寬回合 ⇒ `None`。
    fill_wide_kind: Optional[str] = field(default=None, repr=False)
    #: 寬回合驗過的資料段（最新一句原句原字，依序）；`None` ⇒ 未知（含沒讀到、逾時、例外、值域外、切斷）。
    fill_wide_data: Optional[list] = field(default=None, repr=False)
    #: 寬回合「提議先到」的等待本回合已做過（每回合只等一次，結果鎖住；⛔ 沿用 `fill_proposal_first`）。
    fill_wide_waited: bool = field(default=False, repr=False)
    #: 寬回合卡後：被資料段拒收、本回合最後仍沒套用的欄位（表單鍵 ⇒ 表單標籤；依拒收順序）。
    fill_wide_rejected: dict = field(default_factory=dict, repr=False)
    #: §4.1 (b)（§11 r1c）：**回合開始時**草稿綁定的那張卡還活著——`_write_draft_bound_card` 找得到、`receipt` 不是 dict、
    #: `invalidated` 非 `True`（與 `_write_draft_reissue_gate` 判綁定卡同一組條件）。`_write_draft_begin` 設一次；無草稿 ⇒ `False`。
    bound_card_live: bool = field(default=False, repr=False)
    #: §4.1 (b)（§11 r1c）：本回合是候選回合——寫入候選清單還在等使用者選：`_write_candidates_pick_open` 有回、候選集
    #: `picked` 為 `None`（意圖呼叫走 `pick_rule=True`、接 `DATA_TEXTS_PICK_NOTE` 的同一組狀態）。`_fill_begin_intent_call`
    #: 在送出意圖呼叫之前設一次。
    pick_list_open: bool = field(default=False, repr=False)


def _write_intent_needs_retry(resp: Any) -> bool:
    """附候選段的意圖判斷回應要不要以同一份輸入重送——
    `finish_reason=length`（截斷）或內容解析不出（`WF.PARSE_UNPARSED`；回應形狀不對也算）⇒ `True`。
    多個內容不同的 action 物件（`PARSE_AMBIGUOUS`）、值域外（pydantic）⇒ `False`（照現行處理，⛔ 重送）。"""
    try:
        choice = resp.choices[0]
        content = choice.message.content
    except Exception:  # noqa: BLE001 — 回應形狀不對 ⇒ 當解析不出
        return True
    if getattr(choice, "finish_reason", None) == "length":
        return True
    _obj, status = WF.parse_write_intent_content(content)
    return status == WF.PARSE_UNPARSED


class _RetriedIntentResponse:
    """第 5 輪 §11.15.3 第 5 點：重送過一次的意圖判斷結果。`choices`＝重送那次的回應（重送仍截斷或解析不出、或重送
    丟例外 ⇒ `failed=True`，`_await_write_intent` 照現行回 `None`）；`usage`＝兩次實際用量相加（計量照實）。"""

    __slots__ = ("choices", "usage", "failed")

    def __init__(self, first: Any, second: Any, *, failed: bool) -> None:
        self.choices = getattr(second, "choices", None) if second is not None else getattr(first, "choices", None)
        self.failed = failed
        pt = ct = 0
        for resp in (first, second):
            usage = getattr(resp, "usage", None) if resp is not None else None
            pt += int(getattr(usage, "prompt_tokens", 0) or 0)
            ct += int(getattr(usage, "completion_tokens", 0) or 0)
        self.usage = SimpleNamespace(prompt_tokens=pt, completion_tokens=ct)


class _WriteIntentCall:
    """本回合的一次**意圖判斷呼叫**（W1b §8.1-1、§8.5-4、§8.6-3a／3b）。

    task 由 `AgentRuntime._start_write_intent_call` 建立（`run_program_segments` 未結束回合、
    `_build_turn_context` 之後）；觸發判斷點以 `asyncio.wait` 等（⛔ 自動取消）。
    **收尾只在組 trace 的兩處**——`TurnAccumulator.build_trace`（經 `settle_into`）與
    `AgentRuntime._finish_confirm_turn` 組 `TurnTrace(` 之前（經 `settle`）：
      - 已完成 ⇒ `usage_metering.add_llm_usage` 計量、token 計入本回合、記 `write_intent_call`；
      - 已完成但失敗（例外）⇒ 無 token 可計、記 `write_intent_call_failed`；
      - 未完成 ⇒ `cancel()`、記 `write_intent_call_cancelled`，prompt token 以輸入字元數估算計入。
    `settle` 冪等（第二次回 `(0, 0, [])`）。
    """

    #: E 片：只含 `dialog_act` 的標籤呼叫（`_DialogActCall`）為 `True`——不是寫入意圖，⛔ 進 `_await_write_intent`
    #: 與程式優先入口的等待。
    label_only: bool = False

    def __init__(self, task: "asyncio.Task", *, model: str, input_chars: int,
                 registry: dict, trace_id: str, partial: Optional[list] = None) -> None:
        self.task = task
        self.model = model
        self.input_chars = int(input_chars)
        self._registry = registry
        self._trace_id = trace_id
        self.settled = False
        #: 第 5 輪 §11.15.3 第 5 點：重送前已完成的那一次回應（task 內 append）；task 在重送途中被取消時，
        #: 已完成那次的實際 usage 照計（⛔ 只剩估算）。
        self._partial = partial if partial is not None else []

    def settle(self) -> tuple:
        if self.settled:
            return 0, 0, []
        self.settled = True
        if self._registry.get(self._trace_id) is self:
            self._registry.pop(self._trace_id, None)
        task = self.task
        if not task.done():
            task.cancel()
            pt = int(self.input_chars / WRITE_INTENT_CANCEL_CHARS_PER_TOKEN)
            ct = 0
            marks = [WF.V_CALL_CANCELLED]
            for resp in self._partial:
                usage = getattr(resp, "usage", None)
                pt += int(getattr(usage, "prompt_tokens", 0) or 0)
                ct += int(getattr(usage, "completion_tokens", 0) or 0)
                if _wc.V_CANDIDATE_INTENT_RETRY not in marks:
                    marks.append(_wc.V_CANDIDATE_INTENT_RETRY)
            usage_metering.add_llm_usage(self.model, {"prompt_tokens": pt, "completion_tokens": ct})
            return pt, ct, marks
        if task.cancelled():
            return 0, 0, [WF.V_CALL_CANCELLED]
        if task.exception() is not None:
            return 0, 0, [WF.V_CALL_FAILED]
        result = task.result()
        usage = getattr(result, "usage", None)
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
        usage_metering.add_llm_usage(self.model, {"prompt_tokens": pt, "completion_tokens": ct})
        if isinstance(result, _RetriedIntentResponse):
            return pt, ct, [WF.V_CALL, _wc.V_CANDIDATE_INTENT_RETRY]
        return pt, ct, [WF.V_CALL]

    def settle_into(self, acc: Any) -> None:
        """`TurnAccumulator.build_trace` 的收尾掛點：token 就地加進 `acc`、標記進 `acc.violations`。"""
        pt, ct, marks = self.settle()
        acc.prompt_tokens += pt
        acc.completion_tokens += ct
        for mark in marks:
            if mark not in acc.violations:
                acc.violations.append(mark)

    def abort(self) -> None:
        """回合以例外離開（沒有 trace 可組）⇒ 只撤掉 task 與登記，⛔ 計量（沒有出口可記）。"""
        self.settled = True
        if self._registry.get(self._trace_id) is self:
            self._registry.pop(self._trace_id, None)
        if not self.task.done():
            self.task.cancel()


class _DialogActCall(_WriteIntentCall):
    """每個使用者文字回合另建的**只含 `dialog_act`** 的標籤呼叫（存 `acc.dialog_act_call`）。
    收尾、計量、取消估算與寫入意圖呼叫共用同一套（`settle_into`），差別只有 trace 標記名稱。"""

    label_only = True
    _MARKS = {
        WF.V_CALL: WF.V_DIALOG_ACT_CALL,
        WF.V_CALL_FAILED: WF.V_DIALOG_ACT_CALL_FAILED,
        WF.V_CALL_CANCELLED: WF.V_DIALOG_ACT_CALL_CANCELLED,
    }

    def settle(self) -> tuple:
        pt, ct, marks = super().settle()
        return pt, ct, [self._MARKS.get(m, m) for m in marks]


def _write_draft_owner(identity: Any) -> str:
    """草稿建立者鍵：受眾＋role＋user（原值、⛔ 正規化；比照 `_pending_creator`）。
    下一回合身分與它不同 ⇒ 清掉草稿。"""
    audience = identity.resolved_audience() if hasattr(identity, "resolved_audience") else None
    return f"{audience}|{getattr(identity, 'role_id', None)}|{getattr(identity, 'user_id', None)}"


def _write_draft_user_texts(agent_state: dict, user_message: str) -> list:
    """值閘的比對來源＝本會話使用者訊息（`dialog` 的 user 端＋本句）。⛔ 不含助理回覆、資料段。"""
    texts = [m.get("content") for m in (agent_state.get("dialog") or [])
             if isinstance(m, dict) and m.get("role") == "user" and isinstance(m.get("content"), str)]
    if isinstance(user_message, str):
        texts.append(user_message)
    return texts


def _no_ws(text: str) -> str:
    return "".join(text.split())


def _fill_cuts(left: str, right: str) -> bool:
    """填欄只填答覆 B1 的邊界：相鄰兩字同為數字、或同為 ASCII 英數 ⇒ 切斷（空白、標點、中文都算邊界）。"""
    if left.isdigit() and right.isdigit():
        return True
    return left.isascii() and left.isalnum() and right.isascii() and right.isalnum()


def _fill_locate(message: str, segment: str, lo: int = 0, hi: Optional[int] = None) -> Optional[tuple]:
    """填欄只填答覆 B1：`segment` 去空白後是 `message[lo:hi]` 去空白後的子字串，且它在**原句**（未去空白）對應那一段的
    起訖不切斷數字或 ASCII 英數連續字串（起點前一字與第一字、終點最後一字與後一字；邊界判斷看整句 `message`）。原句
    出現多次時任一處成立即可。成立 ⇒ 原句上的 `(起, 迄)`；否則（含去空白後為空）⇒ `None`。純計算（⛔ 記錄任何字串）。
    邊界檢查只把「AI 切錯」導向 fail-closed，不是安全邊界（數字由值閘的整數 token 比對另擋）。"""
    if not isinstance(message, str) or not isinstance(segment, str):
        return None
    needle = _no_ws(segment)
    if not needle:
        return None
    end = len(message) if hi is None else hi
    pos = [i for i in range(lo, end) if not message[i].isspace()]
    compact = "".join(message[i] for i in pos)
    start = compact.find(needle)
    while start != -1:
        s = pos[start]
        e = pos[start + len(needle) - 1] + 1
        if not ((s > 0 and _fill_cuts(message[s - 1], message[s]))
                or (e < len(message) and _fill_cuts(message[e - 1], message[e]))):
            return s, e
        start = compact.find(needle, start + 1)
    return None


def _fill_data_spans(message: str, texts: list, marks: Optional[list] = None) -> Optional[list]:
    """B1 資料段逐段驗（單欄追問回合 `_fill_read_data` 與寬回合 `_fill_wide_read_data` 共用）：空段、全空白段略過；完全不
    出現在最新一句的段略過並記 `fill_segment_not_in_message`（`marks` 為 `None` ⇒ 不記）；出現在最新一句、但每一處起訖
    都切斷數字或英數 ⇒ `None`（整回合未知）。其餘 ⇒ 原句上的 `(起, 迄)` 清單（依序）。純計算（⛔ 記錄任何字串）。"""
    compact_message = _no_ws(message)
    spans: list = []
    for seg in texts:
        needle = _no_ws(seg)
        if not needle:
            continue
        if needle not in compact_message:
            if marks is not None and WF.V_FILL_SEGMENT_NOT_IN_MESSAGE not in marks:
                marks.append(WF.V_FILL_SEGMENT_NOT_IN_MESSAGE)
            continue
        span = _fill_locate(message, seg)
        if span is None:
            return None
        spans.append(span)
    return spans


#: 寬回合種類（plan-fill-wide-20261028 §4.1）：首句（回合開始無草稿）、卡後（有草稿、上回合沒追問）、多欄（追問 ≥2 欄）。
FILL_WIDE_FIRST = "first"
FILL_WIDE_CARD = "card"
FILL_WIDE_MULTI = "multi"

#: 意圖判斷結果的判讀狀態（`_peek_write_intent`；`_await_write_intent` 依它記標記，寬回合等意圖只讀不記）。
_PEEK_PENDING = "pending"
_PEEK_FAILED = "failed"
_PEEK_RETRY_FAILED = "retry_failed"
_PEEK_AMBIGUOUS = "ambiguous"
_PEEK_UNPARSED = "unparsed"
_PEEK_OUT_OF_DOMAIN = "out_of_domain"
_PEEK_OK = "ok"


def _peek_write_intent(call: Any) -> tuple:
    """判讀本回合意圖判斷呼叫的結果，**無副作用**（⛔ 記 violation、⛔ 寫回合狀態、⛔ 取用）——`_await_write_intent` 與寬回合
    「提議先到、等意圖」（plan-fill-wide-20261028 §4.3 第 4 點）共用同一檢查順序：`call.settled`／`label_only` → 未完成 →
    `task.cancelled()` → `task.exception()` → `_RetriedIntentResponse.failed` → `parse_write_intent_content` →
    `WriteIntent.model_validate`（接 `ValidationError`）。回 `(狀態, 原始物件, WriteIntent)`；值域檢查（`_fill_intent_in_domain`）
    由呼叫端接著做。"""
    if call is None or call.settled or call.label_only:
        return _PEEK_PENDING, None, None
    task = call.task
    if not task.done():
        return _PEEK_PENDING, None, None
    if task.cancelled() or task.exception() is not None:
        return _PEEK_FAILED, None, None
    result = task.result()
    if isinstance(result, _RetriedIntentResponse) and result.failed:
        return _PEEK_RETRY_FAILED, None, None
    try:
        content = result.choices[0].message.content
    except Exception:  # noqa: BLE001 — 回應形狀不對 ⇒ 當無法解析
        content = None
    obj, status = WF.parse_write_intent_content(content)
    if status == WF.PARSE_AMBIGUOUS:
        return _PEEK_AMBIGUOUS, None, None
    if status != WF.PARSE_OK:
        return _PEEK_UNPARSED, None, None
    try:
        intent = WriteIntent.model_validate(obj)
    except ValidationError:
        return _PEEK_OUT_OF_DOMAIN, obj, None
    return _PEEK_OK, obj, intent


#: 期別片 P-2：期別草稿值的**唯一**合法形狀（程式正規化；⛔ 模型原值）。
_PERIOD_DRAFT_VALUE_RE = re.compile(r"^\d{4}/\d{2}( 未繳)?$|^未繳$")
#: 期別草稿值的「未繳」後綴／單獨值（與 `_PERIOD_DRAFT_VALUE_RE` 同一個字面）。
_PERIOD_UNPAID_MARK = "未繳"


def _period_gate_value(value: str, texts: list, today: date) -> Optional[str]:
    """期別值閘（期別片 P-2／R4；純函式，`today` 由呼叫端傳 `bills._today()`）：
    模型值 `parse_period` 解析 → 與使用者原話集合 U（每則 `parse_periods` 的聯集）比**年月**；
    過 ⇒ 回**程式正規化**的存值，不過 ⇒ `None`（呼叫端記 `V_NOT_IN_USER_WORDS`）。

    - 模型值解析不到 ⇒ `None`。
    - 模型值有年月 ⇒ U 須含同年月（⛔ 比字面：「去年九月」的 U 是 2025/09，模型給「九月」⇒
      2026/09 ⇒ 不收）；存 `YYYY/MM`，模型值**與**使用者原話都含未繳詞才加「 未繳」。
    - 模型值只有「未繳」⇒ 使用者原話有未繳詞才收、存「未繳」。
    - 存值一律再過 `_PERIOD_DRAFT_VALUE_RE`（縱深；⛔ 存模型原值）。
    """
    spec = _parse_period(value, today)
    if spec is None:
        return None
    user_texts = [t for t in texts if isinstance(t, str)]
    user_unpaid = any(term in t for t in user_texts for term in _UNPAID_TERMS)
    if spec.has_month:
        said = {(p.year, p.month) for t in user_texts for p in _parse_periods(t, today)}
        if (spec.year, spec.month) not in said:
            return None
        stored = f"{spec.year:04d}/{spec.month:02d}"
        if spec.unpaid_only and user_unpaid:
            stored = f"{stored} {_PERIOD_UNPAID_MARK}"
    elif spec.unpaid_only and user_unpaid:
        stored = _PERIOD_UNPAID_MARK
    else:
        return None
    return stored if _PERIOD_DRAFT_VALUE_RE.fullmatch(stored) else None


def _name_overlap_key(text: str) -> str:
    """W1c §9.11-2 子字串比對的正規化：NFKC＋去空白（值閘 `text` 比對同樣去空白）。"""
    return _no_ws(unicodedata.normalize("NFKC", text))


def _name_said_key(text: str) -> str:
    """F12 整句來源判準的正規化：`_name_overlap_key`（NFKC＋去空白）再 casefold、去標點（Unicode P 類）。
    與 `confirm.name_said_key`（r4 整句來源 `name_lenient_sentence` 用）同一支，⛔ 兩套各寫。"""
    return _confirm_name_said_key(text)


def _name_said_in_message(name: Any, message: Any) -> bool:
    """草稿名稱欄值 `name` 是否出現在本回合使用者原話 `message` 裡（`_name_said_key`
    正規化後的子字串）。任一邊不是字串或正規化後為空 ⇒ `False`。"""
    if not isinstance(name, str) or not isinstance(message, str):
        return False
    key = _name_said_key(name)
    return bool(key) and key in _name_said_key(message)


#: F12 r6 §11.14 第 1 點：使用者原話（NFKC 後）的數字段＝以非數字為界的最長連續數字（含非 ASCII 數字，
#: 讓「٣26007」這類混寫整段不算 ASCII 編號）；只有整段皆 ASCII 數字者才可能等於候選編號。
_SAID_DIGIT_RUN_RE = re.compile(r"\d+")


def _said_id_is_pick_id(user_message: Any, ids: Any, pick_id: Any) -> bool:
    """F12 r6 §11.14 第 1 點（根因 (i)）：使用者這句（NFKC）以非數字為界的數字段中，**恰有一段**（依出現次數計）
    屬於候選集 `ids`，且該段等於 AI 回的 `pick_id` ⇒ `True`（該 `pick_id` 視為客人講出，選對紀錄「分不出」退回
    不套用）。數字段只作佐證：本函式 ⛔ 選定或改選任何一筆（金額、電話可能撞號）；金額期間不符照舊套用。"""
    if not isinstance(user_message, str) or not isinstance(pick_id, str) or not isinstance(ids, list):
        return False
    said = unicodedata.normalize("NFKC", user_message)
    allowed = {i for i in ids if isinstance(i, str)}
    hits = [run for run in _SAID_DIGIT_RUN_RE.findall(said) if run.isascii() and run in allowed]
    return len(hits) == 1 and hits[0] == pick_id


#: 選定後回合改指令式：客人原話（NFKC 後）結構上含序數＝「第」接阿拉伯或國字數字、或含「最後」。
_SAID_ORDINAL_RE = re.compile(r"第\s*[0-9一二三四五六七八九十兩零〇百]|最後")
#: `nth` 指令的值：NFKC 後恰為 1～99 的阿拉伯數字（⛔ `int()`：`1_0`、`+2`、前後空白都不收）。
_NTH_VALUE_RE = re.compile(r"[1-9][0-9]?")


def _said_has_ordinal(user_message: Any) -> bool:
    """選定後回合改指令式：客人原話結構上含序數（NFKC 後「第」接阿拉伯或國字數字、或含「最後」）⇒
    `True`。只作 `nth` 指令「分不出」退回的佐證（免除這一條）：本函式 ⛔ 選定或改選任何一筆；「大的那間」之類依描述
    猜的包成序數 ⇒ `False`（照 `pick` 退回）。"""
    if not isinstance(user_message, str):
        return False
    return _SAID_ORDINAL_RE.search(unicodedata.normalize("NFKC", user_message)) is not None


def _intent_has_value(intent: Any) -> bool:
    """F12 r6 §11.14 第 3 點：意圖的 `fields` 是否至少有一筆值為去頭尾空白後非空的字串（非字串不算）。
    第 5 輪 §11.15.3 第 4 點（R20-2）：名稱欄（`WF.NAME_KEYS`）不算新動作的值——只有名稱 ⇒ `False`（不換動作）。"""
    for item in getattr(intent, "fields", None) or []:
        if getattr(item, "key", None) in WF.NAME_KEYS:
            continue
        value = getattr(item, "value", None)
        if isinstance(value, str) and value.strip():
            return True
    return False


class _NameSaidThisTurn:
    """名稱在前一回合講、這回合只補欄位 ⇒ 用草稿裡既有的名稱欄值當整句：交給
    `NameLenientTurn.touched` 的唯讀視圖。非名稱鍵＝`wd.touched` 原樣；名稱鍵（`WF.NAME_KEYS`）另要求
    草稿裡該欄的值**出現在本回合原話**（`_name_said_in_message`）——意圖呼叫或模型提議依對話歷史把前一
    回合的名稱再吐一次，值閘比對整段會話原話而放行、鍵進了 `touched`，但這回合使用者沒講名稱 ⇒ 不算
    （整句改用草稿名稱值）。每次查詢時才讀 `wd`（與原本傳 `wd.touched` 參照同樣是即時值）；⛔ 另存原句。"""

    __slots__ = ("_wd",)

    def __init__(self, wd: Any) -> None:
        self._wd = wd

    def __contains__(self, key: object) -> bool:
        wd = self._wd
        if key not in wd.touched:
            return False
        if key not in WF.NAME_KEYS:
            return True
        fields = wd.draft.get("fields") if isinstance(wd.draft, dict) else None
        value = fields.get(key) if isinstance(fields, dict) else None
        return _name_said_in_message(value, wd.user_message)


def _name_lenient_typed_turn(wd: Any) -> bool:
    """(乙)：本回合使用者是**打字**——非候選按鈕回合（`wd.pick_button`）、本句不是
    `pick:`／`select:` 機器值、不是確認／修改／取消機器值（`_parse_confirm_value`），且非空白。
    只有 `True` 時 (乙) 缺名稱觸發才可能發生。"""
    msg = getattr(wd, "user_message", None)
    if getattr(wd, "pick_button", False) or not isinstance(msg, str) or not msg.strip():
        return False
    return (_parse_confirm_value(msg) is None and _wc.parse_pick_value(msg) is None
            and _parse_select_value(msg) is None)


def _name_lenient_reask_key(wd: Any) -> Optional[str]:
    """上一回合 (甲)「找不到這個名稱」追問的名稱欄：`asked` 恰為單一名稱鍵 ⇒ 該鍵；否則 `None`
    （與 `_name_lenient_reask_labels` 同一判準）。"""
    asked = list(getattr(wd, "asked", None) or [])
    return asked[0] if len(asked) == 1 and asked[0] in WF.NAME_KEYS else None


def _write_draft_program_message(draft: dict, nonce: str) -> "_ProgramMessage":
    """程式自己的一次 `confirm.request`：payload＝`{action, **to_payload(草稿欄位)}`。"""
    action = draft["action"]
    payload = {"action": action, **WF.to_payload(action, draft.get("fields") or {})}
    args = json.dumps(
        {"summary": WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY,
         "payload": json.dumps(payload, ensure_ascii=False)},
        ensure_ascii=False,
    )
    return _ProgramMessage([
        _ProgramToolCall(f"{WRITE_DRAFT_PROGRAM_ID_PREFIX}{nonce[:8]}", CONFIRM_TOOL_NAME, args)
    ])


#: A+ 片 AP-4：待確認筆存「出卡當時程式送出的草稿正規化值」的鍵名。⚠️ **只拿來比對**
#: （`_pending_draft_payload`）：reissue gate，與 r3 AP-7 (2)(a) 的 `_write_proposal_card_unchanged`
#: （草稿＝卡才重出同卡）；⛔ 進草稿、卡或 `confirm.request`（安全審查 4-1 (iii)）。
PENDING_DRAFT_PAYLOAD_KEY = "draft_payload"


def _draft_payload_shape_ok(value: Any) -> bool:
    """`draft_payload` 的合法形狀：dict、鍵為字串、值為 `str`／`int`／`float`／`None`（⛔ bool）。"""
    if not isinstance(value, dict):
        return False
    for k, v in value.items():
        if not isinstance(k, str) or isinstance(v, bool):
            return False
        if v is not None and not isinstance(v, (str, int, float)):
            return False
    return True


def _pending_draft_payload(entry: Any) -> Optional[dict]:
    """A+ 片 AP-4：讀待確認筆的 `draft_payload`（**一律視為不可信**，比照 `WF.load_draft`）：
    舊筆沒有、或形狀不合 ⇒ `None`（呼叫端沿用現行比對；安全審查 4-1 (i)）。"""
    if not isinstance(entry, dict):
        return None
    value = entry.get(PENDING_DRAFT_PAYLOAD_KEY)
    return value if _draft_payload_shape_ok(value) else None


def _program_payload_keys(raw_args: Any) -> Optional[frozenset]:
    """程式依草稿發出的 `confirm.request`（payload＝`{action, **to_payload(草稿)}`）中，屬於
    `to_payload(草稿)` 的鍵（＝除 `action` 外的鍵）。在任何 `_apply_*` 前處理**之前**取。"""
    payload = _payload_of(raw_args)
    if payload is None:
        return None
    return frozenset(k for k in payload if isinstance(k, str) and k != "action")


def _sent_draft_payload(raw_args: Any, keys: Optional[frozenset]) -> Optional[dict]:
    """A+ 片 AP-4：**這次呼叫送出的 payload**（前處理之後、交給 `registry.call` 的那一份）中屬於
    `keys` 的鍵與值。拿不到 ⇒ `None`（不存 `draft_payload`，reissue gate 沿用現行比對）。"""
    if keys is None:
        return None
    payload = _payload_of(raw_args)
    if payload is None:
        return None
    return {k: payload[k] for k in sorted(keys) if k in payload}


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
        max_completion_tokens: Optional[int] = None,
        tool_timeout_s: float = 3.0,
        status_interval_s: float = 5.0,
        attempt_sink: Optional[Callable[[dict], None]] = None,
        candidate_selector: Optional[CandidateSelector] = None,
        candidate_selectors: Optional[dict] = None,
        db_pool: Any = None,
        clean_llm_output: bool = False,
    ) -> None:
        self.provider = provider
        # 正式接線 §3.2：對話端點開關（`app.py` 只在 `build_agent_provider_from_env()` 非 None 時傳 True）。
        # False（正式機現況）⇒ 推理剝除與 JSON 擷取都不執行，路徑與改前逐位相同；⛔ 不依模型名分岔。
        self._clean_llm_output = bool(clean_llm_output)
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
        # 模型名稱不在 design 契約內明列，沿用專案既有慣例——`OPENAI_MODEL` env
        # 是舊鏈（原 `services/llm_answer_optimizer.py`，已隨舊鏈於 2026-09-10
        # 退役）就在用的既有變數名，這裡延用同一把 env 是刻意的相容選擇，不是
        # 巧合；另開 `AGENT_MODEL` 供獨立覆寫，兩者皆缺才落 "gpt-4o-mini"。
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
        # gpt-oss 第一片（2026-10-17，plan-oss-slice1）：每次模型呼叫的輸出上限。Bedrock gpt-oss 實測
        # 會在 strict JSON 裡灌空白換行到 8,192 tokens（38～79 秒）；正常輸出 p99 1,408、最大 1,871，
        # gpt-6-luna 最大 333 ⇒ 預設 2000。非正整數在建構期就炸（同上方 effort 的 fail loud）。
        cap = max_completion_tokens if max_completion_tokens is not None else (
            os.environ.get("AGENT_MAX_COMPLETION_TOKENS", "").strip() or DEFAULT_MAX_COMPLETION_TOKENS
        )
        try:
            cap = int(cap)
        except (TypeError, ValueError):
            cap = 0
        if cap <= 0:
            raise ValueError("AGENT_MAX_COMPLETION_TOKENS 必須是正整數")
        self._max_completion_tokens: int = cap
        # W1（§2.1(6)）：`AGENT_WRITE_DRAFT`（on／off；未設或空字串＝on）。其他值 ⇒ 建構期就炸
        # 並印原因（同上方 effort／cap 的 fail loud）。
        try:
            self._write_draft_on: bool = write_draft_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # 主線第 3 步 A 片：`AGENT_WRITE_LIFECYCLE`（on／off；未設或空字串＝on）——A1 草稿生命週期、
        # A2 卡後改欄位、A3「修改」按鈕、A4 enum 由程式轉碼共用（A6 預檢在 `confirm.request` 內
        # 於呼叫當下讀同一個開關）。off ⇒ 現行行為。⚠️ A7 唯一有效卡 ⛔ 隨本開關關閉。
        try:
            self._write_lifecycle_on: bool = write_lifecycle_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # A+ 片 AP-0：`AGENT_WRITE_PROPOSAL`（on／off；未設或空字串＝on）。本片行為只在三個開關
        # 皆 on 時生效（`_write_proposal_active`）；off ⇒ 現行行為。
        try:
            self._write_proposal_on: bool = write_proposal_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # B 片 B6：`AGENT_WRITE_REPLY_PROGRAM`（B1、B2、B5）與 `AGENT_STATE_CLAIM_GATE`（B3）；
        # on／off、未設或空字串＝on；off ⇒ 與改前逐字相同。
        try:
            self._write_reply_program_on: bool = WF.write_reply_program_enabled_from_env()
            self._state_claim_gate_on: bool = SC.state_claim_gate_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # `AGENT_WRITE_CANDIDATES`（on／off；未設或空字串＝on）；只在 A+ 三開關
        # 皆 on 時生效（`_write_candidates_active`）；off ⇒ 不啟用候選。
        try:
            self._write_candidates_on: bool = WF.write_candidates_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # 「選對紀錄」片（plan-pick-right-record-20261021 §4）：`AGENT_PICK_RIGHT`（on／off；未設或空字串＝on）；
        # 只在 A-2a 生效時有作用（`_pick_right_active`）；off ⇒ 與 A-2a 逐字相同。
        try:
            self._pick_right_on: bool = WF.pick_right_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # F12（plan-name-lenient-f12-20261022 §4.5、資安 S-10）：`AGENT_NAME_LENIENT`（on／off；未設或空字串＝on；
        # 其他值 ⇒ 啟動即 `ValueError`）；只在 A-2a 生效時有作用（`_name_lenient_active`）；off ⇒ 與現行逐字相同。
        try:
            self._name_lenient_on: bool = NM.name_lenient_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # E 片（plan-closing-handoff-e-20261026 §4.1-5）：`AGENT_CLOSING_HANDOFF`（on／off；未設或空字串＝on；
        # 其他值 ⇒ 啟動即 `ValueError`）。off ⇒ 不加欄、不建標籤呼叫、不走程式轉人／收尾，行為與改前逐位元組相同。
        try:
            self._closing_handoff_on: bool = WF.closing_handoff_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # 填欄只填答覆（plan-fill-answer-only-20261027 §4.1「開關」）：`AGENT_FILL_DATA_TEXT`（on／off；未設或空字串＝on；
        # 其他值 ⇒ 啟動即 `ValueError`）。off ⇒ 寫入意圖呼叫的系統句與 schema、六個值閘呼叫點、整句填入與改前逐字相同。
        # 讀取一律走 `_fill_data_text_on` 屬性本身（⛔ 預設 off 的 getattr：漏設時大聲失敗，不默默退回改前行為）。
        try:
            self._fill_data_text_on: bool = WF.fill_data_text_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.4）：`AGENT_FILL_DATA_TEXT_WIDE`（on／off；未設或空字串＝on；
        # 其他值 ⇒ 啟動即 `ValueError`）。只在 `_fill_data_text_on` 也 on 時生效；off ⇒ 三種寫入回合與改前逐字相同。
        # 讀取一律走屬性本身（⛔ 預設 off 的 getattr）。
        try:
            self._fill_data_text_wide_on: bool = WF.fill_data_text_wide_enabled_from_env()
        except ValueError as exc:
            logger.error("agent_runtime_config_invalid %s", exc)
            raise
        # W1b（§8.6-3b）：進行中的意圖判斷呼叫，依 `trace_id` 登記——`_finish_confirm_turn` 組
        # `TurnTrace(` 前據此收尾（那一支只拿得到 `trace_id`）；收尾即移除，回合以例外離開時
        # 由 `_run_turn_body` 撤掉（`_WriteIntentCall.abort`）。
        self._write_intent_calls: dict = {}
        #: E 片（計畫 r5 附錄）：對話動作標籤呼叫的登記（同上，另一個表、各自收尾）。
        self._dialog_act_calls: dict = {}
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
        user_message: str,
        dialog: list,
        violations: list,
    ) -> tuple[Any, Optional[dict]]:
        """Plan §2.1-2：每回合從正本現組 K=5 候選節＋目錄（受眾只由
        `identity.resolved_audience()` 推導，⛔ 不當參數）。

        適用條件：`identity.resolved_audience()` 是有 git 正本視圖的受眾
        （`CANON_VIEW_AUDIENCES`）、正本已註冊（`get_canon()`），且
        `_selector_for(audience)` 取得到 selector 或至少設了對照表；
        canon 未註冊／根本沒有候選機制 ⇒ `(None, None)`（這**不是**降級——
        是這條路根本沒有候選機制）。

        命中 ⇒ `CandidateOutlineDoc.from_canon(canon, identity, candidate_ids, toc,
        vendor_business_types=...)`（內部呼叫 `canon_assembler.build_canon_sections`，
        逐 id 過 `canon_visible`，不可見 ⇒ raise `CanonSectionInvisibleError`——
        由本函式的外層 `except` 接住，⛔ 不產生空節）。

        任何未命中／失敗（`none_visible`／`no_candidate`／索引不可用／selector
        例外／F1 的 `CanonSectionInvisibleError`）⇒ **降級只注入目錄**
        （`from_canon(canon, identity, [], toc, ...)`，零細目節＋toc），violation
        `candidate_fallback_toc_only`（F1 額外記 `candidate_invisible_id`）。

        外層 guard：`build_canon_toc` 本身失敗 ⇒ `(None, {"miss_kind": "empty_toc"})`
        ＋violation `candidate_toc_error`——例外不逸出這個回合。

        回傳 `(outline, sel_meta)`；`sel_meta` 為 `None` 或
        `{"candidate_ids", "winning_key_kind", "miss_kind"}`。
        """
        audience = identity.resolved_audience()
        canon = get_canon() if audience in CANON_VIEW_AUDIENCES else None
        if canon is None:
            return None, None
        selector = self._selector_for(audience)
        if selector is None and not self._candidate_selectors:
            # 這條路根本沒有候選機制（單數與複數都沒設）⇒ 無 outline，⛔ 不記 violation。
            return None, None

        # `vendor_business_types` 每回合最多解析一次（元件 6／F5），
        # 結果傳給下面三個呼叫點——⛔ 不在 FineIndex／canon_visible／from_canon 內部再解析。
        vendor_business_types = resolve_vendor_business_types(identity)

        try:
            toc = build_canon_toc(canon, identity, vendor_business_types=vendor_business_types)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — 外層 guard：toc 失敗，回合仍要完成
            logger.warning(
                "agent_select_outline_toc_failed reason=%s", type(exc).__name__
            )
            violations.append("candidate_toc_error")
            return None, {
                "candidate_ids": [], "winning_key_kind": {}, "miss_kind": "empty_toc",
            }

        def _toc_only() -> Any:
            return CandidateOutlineDoc.from_canon(
                canon, identity, [], toc, vendor_business_types=vendor_business_types
            )

        if selector is None:
            # 有對照表、卻缺這個受眾 ⇒ 產線正在降級服務（目錄only），
            # 與「索引不可用」同一個 trace 值域，⛔ 不靜默當成「沒有候選機制」。
            violations.append("candidate_fallback_toc_only")
            return _toc_only(), {
                "candidate_ids": [], "winning_key_kind": {}, "miss_kind": "index_unavailable",
            }

        try:
            query = _candidate_query(user_message, dialog)
            sel = await selector.select(
                canon, identity, query, vendor_business_types=vendor_business_types
            )

            if sel is None:
                violations.append("candidate_fallback_toc_only")
                return _toc_only(), {
                    "candidate_ids": [], "winning_key_kind": {}, "miss_kind": "index_unavailable",
                }

            miss_kind = sel["miss_kind"]
            if miss_kind == "none_visible":
                violations.append("candidate_none_visible")
                return _toc_only(), {
                    "candidate_ids": [], "winning_key_kind": {}, "miss_kind": miss_kind,
                }
            if miss_kind == "no_candidate":
                # `ready` 狀態下不可達（見 candidate_selector.py 模組 docstring），
                # 保留於列舉是為了讓 trace 值域封閉；不記 violation（不是機制故障）。
                return _toc_only(), {
                    "candidate_ids": [], "winning_key_kind": {}, "miss_kind": miss_kind,
                }

            return CandidateOutlineDoc.from_canon(
                canon, identity, sel["candidate_ids"], toc,
                vendor_business_types=vendor_business_types,
            ), {
                "candidate_ids": sel["candidate_ids"],
                "winning_key_kind": sel["winning_key_kind"],
                "miss_kind": "hit",
            }
        except asyncio.CancelledError:
            raise
        except CanonSectionInvisibleError as exc:
            # F1：命中後的候選 id 裡有一個對這個身分不可見／未審——⛔ 不產空節，
            # 整回合降級為 toc-only，且**額外**記 `candidate_invisible_id`。
            logger.warning(
                "agent_select_outline_invisible_id reason=%s", type(exc).__name__
            )
            violations.append("candidate_invisible_id")
            violations.append("candidate_fallback_toc_only")
            return _toc_only(), {
                "candidate_ids": [], "winning_key_kind": {}, "miss_kind": "index_unavailable",
            }
        except Exception as exc:  # noqa: BLE001 — 一回合內：選取失敗一律退回 toc-only
            logger.warning(
                "agent_select_outline_failed reason=%s", type(exc).__name__
            )
            violations.append("candidate_selector_error")
            return _toc_only(), {
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
        document_trace: Optional[dict] = None,
        ask_target: Optional[str] = None,
        trace: Optional[TurnTrace] = None,
    ) -> TurnResult:
        """確認段各出口共用的收尾：組 trace → 落 decision snapshot → 寫回 dialog。

        `trace`（B 片）：模型迴圈一般出口已由 `acc.build_trace` 組好的 trace（含 Verifier 結果、候選、
        觀察計數）——B 片的換句與乙′ 出口經本函式收尾時傳入，沿用它並覆寫本出口的欄位（`final_kind`、
        `pending_id`、`receipt_id`、`latency_ms`、token、`violations`）；`None` ⇒ 現行（新組一份）。

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
        # T1：三個寫點之一（⛔ 不得移到函式尾端）——R3：與下方 `fixed_streak`／
        # `dialog` 兩個寫點一起收進 `AgentSession.end_turn`（見下方單一呼叫；
        # `ask_target=None`／`is_fixed=False` 逐字＝原本這裡與下方兩行各自的值，
        # 這條路徑 ⛔ 不進 `handoff_cache`——不傳 `cache`）。
        session = AgentSession(agent_state)
        # W1b（§8.6-3b／§8.7 #1）：意圖判斷呼叫的收尾掛點之一（另一處是
        # `TurnAccumulator.build_trace`）——**組 `TurnTrace(` 之前**：已完成 ⇒ 計量並把 token
        # 加進本回合；未完成 ⇒ `cancel()` 並以估算計入。本回合沒有發意圖呼叫 ⇒ 什麼都不做。
        for intent_call in (getattr(self, "_write_intent_calls", {}).get(trace_id),
                            getattr(self, "_dialog_act_calls", {}).get(trace_id)):
            if intent_call is None:
                continue
            _pt, _ct, _marks = intent_call.settle()
            prompt_tokens += _pt
            completion_tokens += _ct
            violations = list(violations or [])
            violations += [m for m in _marks if m not in violations]
        if trace is not None:
            trace.llm_calls = llm_calls
            trace.prompt_tokens = prompt_tokens
            trace.completion_tokens = completion_tokens
            trace.final_kind = kind
            trace.latency_ms = int((self._clock() - start) * 1000)
            trace.violations = list(violations or [])
            trace.pending_id = pending_id
            trace.receipt_id = receipt_id or None
        else:
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
                # W9 U2：文件回合的四鍵（⛔ 無任何欄位值，見 `TurnTrace` 的說明）。
                **(document_trace or {}),
            )
        session.end_turn(
            user_message=user_message,
            dialog_text=answer if dialog_answer is None else dialog_answer,
            # 2026-10-15 A9：缺欄追問出口傳入封閉值（物件⇒estate），下一回合 A2 才接得上。
            ask_target=ask_target if ask_target in ASK_TARGETS else None,
            is_fixed=False,
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
                # S5：只有帶查無標記的 NO_MATCH 才是查無（試下一域）；其餘是沒查成。
                if _is_marked_not_found(tool_result):
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
    ) -> tuple[str, Optional[str], Optional[tuple]]:
        """trigger B：只開既有的 estates keyword 查詢（S8-13：⛔ 不開
        `estate`／`meter` 的新 `ref` 語義）。

        回 `(outcome, facts, carry)`：前兩格同 `_pre_lookup_id_result`；
        第三格是第六批 #10 的物件記憶候選 `(name, estate_id)`——**這一次查詢真的
        對到唯一一個物件**時才有值（`_estate_carry_from_estates_data`），
        其餘一律 `None`。⚠️ 本方法自己 ⛔ 不寫 `agent_state`：寫入紀律（範圍釘住
        不寫、名稱正規化）集中在 `_write_estate_carry` 一支，⛔ 不分兩處各做一半。
        """
        clean = sanitize_data_piece(keyword).strip()
        if not clean:
            return "not_found", None, None
        try:
            tool_result = await self.registry.call(
                identity, _PRE_LOOKUP_ESTATE_TOOL,
                {"face": _PRE_LOOKUP_ESTATE_FACE, "keyword": clean},
                self._tool_timeout_s, stage=self._stage,
                readonly_view=self.readonly_view, for_model=True,
            )
        except Exception:  # noqa: BLE001 — 沒查成，⛔ 不是查無
            return "error", None, None
        if not tool_result.ok:
            if _is_marked_not_found(tool_result):            # S5：同上
                return "not_found", None, None
            return "error", None, None
        data = tool_result.data if isinstance(tool_result.data, dict) else {}
        carry = _estate_carry_from_estates_data(data, clean)
        facts = data.get("facts")
        if not isinstance(facts, str) or not facts.strip():
            return "not_found", None, carry
        # estates 工具對「查無」回的是 `found=False` 哨兵單筆：`ok=True`、facts 是
        # 「在對外刊登清單中找不到…」的決定性說明、**不帶 `scope` 鍵**（L15 (a)①）。
        # 封閉判定：真的命中恰一筆 ⇒ 帶 `scope`；多筆 ⇒ `candidates` 非空；兩者皆無
        # ⇒ 視為查無（2026-09-09 實測：「延三天」被注入「找不到物件」誤導模型答查無）。
        if "scope" not in data and not data.get("candidates"):
            return "not_found", None, carry
        if scope_estate_id is not None:
            scope_outcome = _enforce_tool_scope(
                _PRE_LOOKUP_ESTATE_TOOL, tool_result, scope_estate_id, clean, violations
            )
            if scope_outcome == "out":
                return "out_of_scope", None, None
        return "found", facts, carry

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
        AgentSession(agent_state).write_select_scope(None)

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
        # A7(3)（唯一有效卡，⛔ 隨開關關閉）：狀態標記之外，**同步在 DB 燒掉**那張 token
        #    （重用 `redeem_pending`，綁 pid＋session；回傳的 token 直接丟棄）。
        #    只標狀態不燒 DB 的話，舊 pid 仍是一張「表裡活著」的卡。
        #    燒卡失敗 ⇒ 只記違規、不中斷回答：狀態已標 `invalidated`，確認段看到標記
        #    會再燒一次並回固定句（fail-closed 仍成立）。
        pending_all = agent_state.get(PENDING_CONFIRM_KEY)
        if isinstance(pending_all, dict):
            voided: list = []
            for burn_pid, entry in pending_all.items():
                if isinstance(entry, dict) and not isinstance(entry.get("receipt"), dict):
                    entry["invalidated"] = True
                    voided.append(burn_pid)
                    if self._db_pool is not None:
                        try:
                            await redeem_pending(
                                self._db_pool, identity.session_id, burn_pid
                            )
                        except Exception as exc:  # noqa: BLE001 — 見上：標記仍在、確認段會再燒
                            violations.append(f"SELECT_BURN_EXC:{type(exc).__name__}")
            # UD-3（縮減 ①）：作廢的卡 ⇒ 照片暫存釋放（全部標完作廢之後才判「仍被活卡引用」）。
            for burn_pid in voided:
                self._release_card_photos(identity, agent_state, burn_pid)

        # L15 (a)②：命中 ⇒ 這一段對話的範圍＝該列的物件（`_ok_single(scoped=True)`
        # 放進 `data["scope"]`）。⛔ 列上算不出 `estate_id` 就維持 `None`——沒有
        # 範圍等於「這一段不受限」，而不是「擋掉所有東西」；擋不擋由 (a)③ 在有
        # 範圍時才做，這裡少寫一個猜出來的值。
        scope = data.get("scope")
        row_estate = scope.get("estate_id") if isinstance(scope, dict) else None
        if row_estate is not None and str(row_estate):
            AgentSession(agent_state).write_select_scope(
                {"type": select_type, "estate_id": str(row_estate)}
            )
            # W1（§2.1(3) 清除條件）：`select:` 釘住範圍 ⇒ 進行中的寫入草稿作廢。
            AgentSession(agent_state).clear_write_draft()

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
        # 站內幫手 S5（§3i 第 3 點，F1／S5-3）：**拿到 pending 立刻比對建立者**
        # (user_id, role_id)——不符（含沒有建立者的舊 pending）走與「不認得的 pid」同一個
        # 出口：⛔ 燒 token、⛔ 回 receipt、⛔ 改 pending。
        if isinstance(pending, dict) and pending.get("creator") != _pending_creator(identity):
            pending = None
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

        # W1（§2.1(3) 清除條件）：使用者兌現或取消確認卡 ⇒ 進行中的寫入草稿一律清掉
        # （出卡那一刻其實已清；這裡是縱深）。
        # 第 3 步 A1（開關 on）：⛔ 在分岔前清——草稿只在「取消」與「任何 receipt 寫入」時清
        # （見下方各分支的 `_clear_draft_on_close()`）；「修改」保留草稿（A3）。
        lifecycle_on = getattr(self, "_write_lifecycle_on", False)
        if not lifecycle_on:
            AgentSession(agent_state).clear_write_draft()

        def _clear_draft_on_close() -> None:
            # A1：任何 receipt 寫入、或按取消 ⇒ 清草稿（草稿含個資，⛔ 留到 session 關閉）。
            # 開關 off 時草稿已在上面清掉，這裡是同一個動作的冪等重複。
            AgentSession(agent_state).clear_write_draft()

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
                if isinstance(pending_payload, dict) and pending.get("action") == "estate_create":
                    # S5（S5-15）：新建物件的名稱＝卡上確認過的物件名稱（`title`）。
                    pending_payload = {"estate_name": pending_payload.get("title")}
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
            if verb == CONFIRM_QUICK_REPLY_VALUES[2]:
                # A1：對已作廢的卡按「取消」＝使用者不要了 ⇒ 草稿一併清（回應句不變）。
                _clear_draft_on_close()
                AgentSession(agent_state).clear_last_submitted()     # #9g：取消 ⇒ 清標記
                # UD-3：作廢的卡再按取消 ⇒ 照片釋放（仍被活卡引用的照片不動）。
                self._release_card_photos(identity, agent_state, pending_id)
            return _finish(CONFIRMATION_REQUIRED_TEXT)

        submit = verb == CONFIRM_QUICK_REPLY_VALUES[0]
        if lifecycle_on and verb == CONFIRM_QUICK_REPLY_VALUES[1]:
            # A3「修改」：token 照現行**立即燒掉**（⛔ 留著讓「修改完再按送出」還能通）、
            # ⛔ 寫 receipt（新增標記會落入 `_answer_for_receipt` 的預設成功收據）、草稿保留且
            # `idle_turns` 歸 0、程式固定句問要改哪一項（標籤取自表單宣告）。
            # 卡以既有 `invalidated` 標記作廢：之後同一個 pid 的三顆按鈕都走上方作廢分支
            # （燒不到、回固定句），A2 也不再把它當「綁定的卡」。
            if self._db_pool is not None:
                await redeem_pending(self._db_pool, identity.session_id, pending_id)
            existing_receipt = pending.get("receipt")
            if isinstance(existing_receipt, dict):
                # 已經有結果的那一筆（先送出、再按修改）⇒ R4.3 回同一個結果，⛔ 改寫。
                return self._answer_for_receipt(pending, existing_receipt, _finish)
            pending["invalidated"] = True
            session = AgentSession(agent_state)
            draft = session.get_write_draft()
            if isinstance(draft, dict):
                draft["idle_turns"] = 0
                session.write_write_draft(draft)
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message, trace_id=trace_id,
                start=start, kind="ask",
                answer=WF.edit_ask_text(pending.get("action"), pending.get("payload")),
                pending_id=pending_id, tool_calls=None,
                violations=["confirm_edit_ask"], receipt_id="",
                outcome=make_outcome("clarifying", expects="text",
                                     action=pending.get("action")),
            )
        if not submit:
            # 修改／取消：**一律先燒 token**（⛔ 不留著讓「取消完再送出」還能通），
            # 不呼叫任何寫入工具。站內幫手 S3：按取消也清文件暫存（DSP-076）。
            AgentSession(agent_state).clear_document_carry()
            if self._db_pool is not None:
                await redeem_pending(self._db_pool, identity.session_id, pending_id)
            # ⚠️ ⛔ 不覆蓋既有 receipt：這一筆若已經執行過（使用者先送出、再按取消），
            #    把 receipt 換成 `{"cancelled": true}` 會讓 R4.3 的「重送回同一結果」
            #    變成謊報「沒有送出」。
            if not isinstance(pending.get("receipt"), dict):
                pending["receipt"] = {"cancelled": True}
            _clear_draft_on_close()
            AgentSession(agent_state).clear_last_submitted()         # #9g：取消 ⇒ 清標記
            self._release_card_photos(identity, agent_state, pending_id)   # UD-3：作廢 ⇒ 釋放
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
        if action not in _confirm_card.CONFIRM_ACTIONS or not isinstance(payload, dict):
            return _finish(CONFIRMATION_REQUIRED_TEXT)
        try:
            payload_sha = payload_digest(payload)
        except (TypeError, ValueError):
            return _finish(CONFIRMATION_REQUIRED_TEXT)
        # 兩把雜湊都要對：payload 對的是「將被執行的參數」，卡對的是「使用者
        # 看到的字」。⛔ 只對其中一把等於留下另一半可以被換掉。
        if not hmac.compare_digest(payload_sha, redemption.payload_sha256):
            self._release_card_photos(identity, agent_state, pending_id)   # UD-3：token 已燒＝卡死了
            return _finish(CONFIRMATION_REQUIRED_TEXT)
        if not isinstance(card_sha, str) or not hmac.compare_digest(
            card_sha, redemption.summary_sha256
        ):
            self._release_card_photos(identity, agent_state, pending_id)
            return _finish(CONFIRMATION_REQUIRED_TEXT)

        # S1／H1 **閘二：兌現前的日期有效性**。與閘一（`confirm.request`）是
        # **同一個純函式、同一個時鐘**（`bills._today()` 在呼叫點取值）。
        # ⚠️ **一個時鐘（`bills._today()`）、三個呼叫點**（V3）：出卡
        # （`confirm.request`）、兌現閘（本處）、寫入形狀驗算
        # （`action._validated_payload`）。三處各自在呼叫點取同一個時鐘，
        # ⛔ 沒有任何一處自己讀 `date.today()`、⛔ 也沒有第二套判定：
        # 本處判的是**日期語義**（`fields_before_today`），`action.py` 那一處
        # 只是把同一個時鐘餵給 render 的**形狀驗算**（起算日基準）。
        # 為什麼兌現時要再判一次：出卡與按下確認之間可以跨過午夜，也可以在
        # 表被人為改動後才兌現；「使用者按過確認」證明不了「這個日期還沒過」。
        # ⚠️ token 在上面 `redeem_pending` 已經燒掉（刻意，S-12）⇒ 使用者要重新
        #    確認一次；此處**不呼叫任何寫入工具**，pending 以「這一筆失敗了」關掉
        #    （與工具回 `ok=False` 同一條路：重送回同一句 `ACTION_FAILED_TEXT`，R4.3）。
        # 稽核出口＝`trace.violations` 的 `date_before_today_at_redeem`（F9）。
        if fields_before_today(action, payload, bills._today()):
            logger.info("[agent] 兌現閘：日期早於今天 ⇒ ⛔ 不呼叫寫入工具（⛔ 不記日期值）")
            pending["receipt"] = {"error": "INVALID_INPUT"}
            _clear_draft_on_close()
            self._release_card_photos(identity, agent_state, pending_id)   # UD-3：兌現失敗也釋放
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

        # UD-3（縮減 ①）：兌現了（寫入成功或失敗）⇒ 這張卡的照片暫存釋放。
        self._release_card_photos(identity, agent_state, pending_id)
        if not tool_result.ok:
            if (action == "repair_create" and isinstance(tool_result.data, dict)
                    and tool_result.data.get(PHOTOS_UNAVAILABLE_KEY) is True):
                # S5／A13：卡上照片的暫存不在或 sha256 不符 ⇒ 寫入工具 ⛔ 寫入；回固定句請使用者
                # 重新上傳（⛔ 改成不附照片照送）。同一個 pid 重按回同一句（R4.3，`_answer_for_receipt`）。
                pending["receipt"] = {"error": PHOTOS_UNAVAILABLE_RECEIPT_ERROR}
                _clear_draft_on_close()
                return _finish(PHOTO_REUPLOAD_TEXT, tool_calls=records,
                               violations=violations + [V_PHOTOS_UNAVAILABLE_AT_REDEEM],
                               outcome=make_outcome("failed", expects="none",
                                                    action=pending.get("action")))
            # 誠實回錯（S-12：token 已燒是刻意的——要再做一次就要重新確認）。
            pending["receipt"] = {"error": tool_result.error or "TOOL_FAILED"}
            _clear_draft_on_close()
            return _finish(ACTION_FAILED_TEXT, tool_calls=records, violations=violations,
                           outcome=make_outcome("failed", expects="none",
                                                action=pending.get("action")))

        data = tool_result.data if isinstance(tool_result.data, dict) else {}
        receipt = data.get("receipt")
        if not isinstance(receipt, dict):
            receipt = data
        pending["receipt"] = receipt
        _clear_draft_on_close()
        if lifecycle_on and getattr(self, "_write_draft_on", False) and action in WF.FORMS:
            # 第 3 步 #9g：送出成功 ⇒ 記「最近送出」標記（動作名＋pid；⛔ token、⛔ payload）。
            # 只在草稿機制開著時寫：標記唯一的讀者是草稿的兩個程式判斷點（意圖判斷的布林），
            # `AGENT_WRITE_DRAFT=off` 時下一回合開頭就會被清掉——寫了只是多一個無人讀的鍵。
            AgentSession(agent_state).write_last_submitted(
                WF.new_last_submitted(action, pending_id))
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
        if receipt.get("error") == PHOTOS_UNAVAILABLE_RECEIPT_ERROR:
            # UD-3：照片失效那一筆重按 ⇒ 同一句（R4.3）。
            return finish(PHOTO_REUPLOAD_TEXT,
                          outcome=make_outcome("failed", expects="none", action=action),
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
            # 站內幫手 S5（S5-12）：釘住範圍時解析不出物件（`estate_id` 為 None）⇒ **擋**
            # （fail-closed；原本放行，靠兌現端 `NO_MATCH` 兜底）。
            estate_id = data.get("estate_id")
            if estate_id is not None and str(estate_id) and str(estate_id) == scope_estate_id:
                return None
        elif action == "contract_create":
            # S5（業主移入、S5-12）：比出卡端以帶 viewer 的查詢解析、寫進 payload 的物件編號。
            card_estate = payload.get("estate_id") if isinstance(payload, dict) else None
            if card_estate is not None and str(card_estate).strip() == scope_estate_id:
                return None
        elif action == "manual_bill_create":
            # S5（S5-13）：比出卡時以精確 id 比對到的合約列上的物件（`scope_estate_id`；
            # ⛔ 重用 `estate_id`、⛔ 動物件記憶）。取不到 ⇒ 擋。
            row_estate = data.get("scope_estate_id")
            if row_estate is not None and str(row_estate).strip() == scope_estate_id:
                return None
        elif action == "estate_create":
            # S5：釘住範圍（正在談某一戶）時建立新物件一律擋。
            pass
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
        identity: Optional[Identity] = None, draft_payload: Optional[dict] = None,
        write_candidates: bool = False, candidate_field_value: Any = None,
        card_pick: Optional[dict] = None, candidate_reask: bool = False,
        lead: Optional[str] = None, photo_suggestion: Optional[dict] = None,
    ) -> Optional[TurnResult]:
        """`confirm.request` 成功 ⇒ 把待確認動作存進 session 狀態並結束回合。

        UD-3：`photo_suggestion`＝這張卡用到的照片建議欄位（分類／部位／原因／描述，⛔ 照片中繼資料）；
        修繕卡才存進待確認筆 `PENDING_PHOTO_SUGGESTION_KEY`（⛔ 進卡、⛔ 進雜湊），卡後更正重出卡時
        `_card_photo_inputs` 由這裡帶回。

        填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.3 第 8 點）：`lead`＝程式固定句（寬回合卡後部分套用時
        點名沒套用的欄位標籤）⇒ 接在卡文字之前（只進 `TurnResult.answer`；⛔ 進 `card`／`card_sha256`／dialog）。`None` ⇒
        與改前逐字相同。

        A-2a 修正 1：`card_pick` 只由 `wd_program` 呼叫點在「這次呼叫帶了 `program_pick`」時傳入
        （`_write_candidates_card_pick_record`）；形狀合法且動作＝這張卡的動作 ⇒ 存進待確認筆
        `_wc.CARD_PICK_KEY`（⛔ 進卡、⛔ 進雜湊、⛔ 進草稿）。候選集照清（A2-R6 (a)）。

        `write_candidates` 只由呼叫端在「候選形狀、且這次呼叫是程式依草稿發出
        （`wd_program`／提議轉成的程式呼叫）、非文件／文件暫存／點選範圍／影子回合」時設 `True`
        （`_write_candidates_eligible`）⇒ 程式列候選清單、寫候選集、結束回合（⛔ 出卡、⛔ 建 token）。
        `candidate_field_value`＝草稿該欄位的名稱值（候選集 `name_fp` 的來源）。

        A+ 片 AP-4：`draft_payload` 只由呼叫端在「這次呼叫是程式依草稿發出（`wd_program` 或 AP-1 的
        區域旗標）」時傳入＝**這次呼叫送出的 payload** 中屬於 `to_payload(草稿)` 的鍵；三個開關皆 on
        且形狀合法才存進待確認筆（⛔ 在這裡讀「當下草稿」：文件暫存或模型自呼出的卡會帶上不對應的值）。

        `data` 形狀不符（缺 `card`／`action` 不在值域／`payload` 不是物件）⇒ 回
        `None` 讓回合照常走下去：⛔ 不在這裡硬印一張半成品的卡。

        存進狀態的是 `{action, payload, card_sha256}`——**⛔ 沒有 token**
        （r1 B2）也**⛔ 沒有卡的原文**（原文每次都重算得出來，存它只是多一份
        會跟著 `collected_data` 落 DB 的副本）。
        """
        if not isinstance(data, dict):
            return None
        if write_candidates:
            return self._write_candidates_exit(
                agent_state, data, identity=identity, field_value=candidate_field_value,
                trace_id=trace_id, start=start, user_message=user_message, tool_calls=tool_calls,
                violations=violations, llm_calls=llm_calls, prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens, reask=candidate_reask,
            )
        # 第六批 #2：多筆候選 ⇒ ask 回合＋按鈕（見 `CONFIRM_CANDIDATES_TEXT`）。
        # 排在形狀檢查之前：候選形狀本來就沒有 `card`／`pending_id`，⛔ 不該被記成
        # `confirm_request_data_shape_invalid`。範圍釘住時 `_scope_gate_confirm_request`
        # 已在更前面 fail-closed（候選結果帶 `action`／`payload` 就是為了那一關）。
        candidates = data.get("candidates")
        cand_action = data.get("action")
        if (
            isinstance(candidates, list) and candidates and not data.get("card")
            and cand_action in _CONFIRM_CANDIDATE_DOMAIN
        ):
            domain, select_type = _CONFIRM_CANDIDATE_DOMAIN[cand_action]
            rows = [
                c for c in candidates
                if isinstance(c, dict) and c.get("id") is not None
            ][:CONFIRM_CANDIDATES_MAX]
            if rows:
                violations.append("confirm_request_candidates")
                # B 片 B4（B-R7）：給人看的格式器——同一列投影、⛔ 給模型的兩句提示、⛔ 回顯模型
                # payload 的查詢字串（安全審查 S11）；dialog 只寫程式摘要（比照 `SELECT_DIALOG_SUMMARY`）。
                text = CONFIRM_CANDIDATES_TEXT + "\n" + _jgb2_candidates_text_for_user(domain, rows)
                quick = [
                    {"label": _candidate_button_label(c), "value": f"select:{select_type}:{c['id']}"}
                    for c in rows
                ]
                return self._finish_confirm_turn(
                    agent_state=agent_state,
                    user_message=user_message,
                    trace_id=trace_id,
                    start=start,
                    kind="ask",
                    outcome=make_outcome("clarifying", expects="choice"),
                    answer=text,
                    dialog_answer=CONFIRM_CANDIDATES_DIALOG_SUMMARY.format(n=len(rows)),
                    pending_id=None,
                    quick_replies=quick,
                    tool_calls=tool_calls,
                    violations=violations,
                    llm_calls=llm_calls,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
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
            or action not in _confirm_card.CONFIRM_ACTIONS
            or not isinstance(payload, dict)
        ):
            violations.append("confirm_request_data_shape_invalid")
            return None
        if self._pick_right_active() and action == WF.BILL_DUE_EXTEND_FORM.action:
            # 「選對紀錄」片 §4.6：卡上帳單（系統值）與客人先前講的值不符（按鈕照按出卡＋提醒行，業主裁 Q4）
            # ⇒ 記不符的碼（⛔ 金額、期間）。
            display = payload.get(_confirm_card.PICK_DISPLAY_KEY)
            if isinstance(display, dict):
                bill_like = {"total": display.get("amount"), "date_start": display.get("date_start"),
                             "date_end": display.get("date_end")}
                for mark in _wc.said_mismatch_marks(
                        bill_like, said_amount=display.get("said_amount"),
                        said_range=display.get("said_range")):
                    if mark not in violations:
                        violations.append(mark)
        session = AgentSession(agent_state)
        # 出卡成功 ⇒ 照片建議用掉了，清掉（⛔ 不讓它再補到下一張無關的單）。
        session.consume_image_suggestion()
        # A-2a（§11 P3-2；A2-R6 (a)）：出了確認卡 ⇒ 候選集作廢（之後按舊候選按鈕一律失效句）。
        # 修正 1：選定改由這張卡的待確認筆帶著（下方 `card_pick`），只供卡後更正重出卡時經 `program_pick` 帶回。
        if self._write_candidates_active():
            session.clear_write_candidates()
        # 第 3 步 #9g：新的一張卡出了 ⇒「最近送出」標記清掉（之後的更正對象是這張新卡）。
        session.clear_last_submitted()
        # W1（§2.1(3) 清除條件）：出卡成功（`confirm_pending`）⇒ 寫入草稿清掉。
        # 第 3 步 A1（開關 on）：出卡 ⇒ 草稿**保留**（送出／取消／逾時才清），且草稿與 pending
        # 綁同一個動作——草稿是別的動作（模型自呼出了另一支的卡）⇒ 那份草稿與這張卡無關，清掉。
        if not getattr(self, "_write_lifecycle_on", False):
            session.clear_write_draft()
        else:
            kept = session.get_write_draft()
            if isinstance(kept, dict) and kept.get("action") != action:
                session.clear_write_draft()
        # 站內幫手 S3（§3h 第 5 點；DSP-076）：收據日期**只作卡外提示**——由文件暫存
        # 取出、接在卡文字之後（⛔ 不進卡、⛔ 不進雜湊、⛔ 不進 dialog）；出卡即清暫存。
        carry = _document_carry_of(agent_state)
        if (
            carry is not None and carry["action"] == action and carry["receipt_date"]
            and not (isinstance(hint, str) and hint.strip())
        ):
            ymd = carry["receipt_date"].replace("-", "/")
            hint = RECEIPT_DATE_HINT_TEMPLATE.format(date=ymd)
        session.clear_document_carry()
        # 第六批 #10 **寫點 (a)**：出卡成功 ⇒ 這張卡上的物件就是「本對話最近提到
        # 的物件」。兩個值都是**封閉來源**：`estate_name` 是使用者剛才會在卡上看到
        # 的那一行（`confirm_card._render_repair_create` 的「物件」），`estate_id`
        # 是 `confirm.request` 自己查出來的（`tools/confirm.py::_open_repairs_hint`）。
        # ⛔ 不在這裡另外查一次；釘住範圍時 `_write_estate_carry` 自己不寫。
        _write_estate_carry(agent_state, payload.get("estate_name"), estate_id)
        pending_entry: dict = {
            # 站內幫手 S5（F1）：建立者 (user_id, role_id)——兌現前比對，不符視同不認得的 pid。
            "creator": _pending_creator(identity),
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
            pending_entry["estate_id"] = estate_id
        # A+ 片 AP-4：出卡當時程式送出的草稿正規化值（只供 reissue gate 比對；⛔ 進卡、⛔ 進雜湊）。
        if (draft_payload is not None and self._write_proposal_active()
                and _draft_payload_shape_ok(draft_payload)):
            pending_entry[PENDING_DRAFT_PAYLOAD_KEY] = dict(draft_payload)
        # A-2a 修正 1：由 `program_pick` 出的卡帶著選定（讀回時 `_write_candidates_card_pick` 再驗一次）。
        if card_pick is not None and self._write_candidates_active():
            rec = _wc.load_card_pick(card_pick, action=action)
            if rec is not None and rec["creator"] == pending_entry["creator"]:
                pending_entry[_wc.CARD_PICK_KEY] = rec
        # UD-3：照片分類跟著卡走（照片本身在 payload，已綁雜湊）。
        if action == "repair_create":
            kept = _photo_suggestion_fields(photo_suggestion)
            if kept is not None:
                pending_entry[PENDING_PHOTO_SUGGESTION_KEY] = kept
        # FIFO 上限（dict 保序）；⛔ 不是 LRU——重送命中時不重排，那會讓一筆被
        # 反覆重送的確認永遠擠不掉別人的。R3：落地與修剪收進
        # `AgentSession.write_pending_confirm`（⛔ 上限值不變，同一個
        # `PENDING_CONFIRM_MAX`）。
        session.write_pending_confirm(pending_id, pending_entry)
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
            answer=(f"{lead}\n" if isinstance(lead, str) and lead else "") + (
                card if not (isinstance(hint, str) and hint.strip()) else f"{card}\n{hint}"),
            dialog_answer=card,
            pending_id=pending_id,
            quick_replies=list(quick_replies or []),
            tool_calls=tool_calls,
            violations=violations,
            llm_calls=llm_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def _write_candidates_exit(
        self, agent_state: dict, data: dict, *, identity: Optional[Identity], field_value: Any,
        trace_id: str, start: float, user_message: str, tool_calls: list, violations: list,
        llm_calls: int = 0, prompt_tokens: int = 0, completion_tokens: int = 0,
        prefix: Optional[str] = None, trace: Optional[TurnTrace] = None, reask: bool = False,
    ) -> TurnResult:
        """候選形狀 ⇒ **程式**列候選清單並結束回合。

        「選對紀錄」片（開關生效時）：畫面列 `candidates_shown_max()`（10）筆；帳單候選來自已選物件 ⇒ 候選集
        帶物件範圍；0 張相符 ⇒ 前導句換成「對不上」固定句（程式由碼與已過值閘的值組，`tools.confirm`）＋標記；
        `reask`（打字選定不成立的重列）⇒ 前導句換成「依您目前說的，仍對到 N 筆」；延期繳費的物件候選記
        `pick_right:estate_first`。標記只記碼（S-F11）。"""
        pr_on = self._pick_right_active()
        return self._write_candidates_exit_body(
            agent_state, data, identity=identity, field_value=field_value, trace_id=trace_id,
            start=start, user_message=user_message, tool_calls=tool_calls, violations=violations,
            llm_calls=llm_calls, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            prefix=prefix, trace=trace, reask=reask and pr_on, pr_on=pr_on)

    def _write_candidates_exit_body(
        self, agent_state: dict, data: dict, *, identity: Optional[Identity], field_value: Any,
        trace_id: str, start: float, user_message: str, tool_calls: list, violations: list,
        llm_calls: int, prompt_tokens: int, completion_tokens: int,
        prefix: Optional[str], trace: Optional[TurnTrace], reask: bool, pr_on: bool,
    ) -> TurnResult:
        """`_write_candidates_exit` 的本體（A-2a 原文說明如下）。

        候選形狀 ⇒ **程式**列候選清單並結束回合。

        - 候選集與畫面清單出自**同一份** `data["candidates"]`（＝出卡前解析同一次帶 viewer 查詢的列，
          §11 P3-6）；候選集存全部 ≤20 個編號，畫面列前 `CANDIDATES_SHOWN_MAX` 筆＋每筆一顆
          `pick:<型別>:<編號>` 按鈕；多於畫面筆數或上游還有下一頁 ⇒ 接 `CANDIDATES_MORE_TEXT`；
        - 前導句是三句固定句之一（只插筆數），清單由 `jgb2` 給人看的格式器產（同一張投影表）；
        - dialog 只寫程式摘要（P4-1；⛔ 清單文字）；trace 只記型別與筆數；
        - ⛔ 出卡、⛔ 建 token、⛔ 寫草稿；新清單取代舊候選集（A2-R6 (b)）。
        `prefix`＝乙′ 已過 B3 與出口閘的模型文字（B2 狀態行）；`None`＝整則程式回話。
        組不出合法候選集（編號形狀全不合）⇒ 退回現行缺欄追問（`missing_label`），⛔ 列清單。"""
        action = data.get("action")
        cand_type = data.get(CANDIDATE_TYPE_KEY)
        rows_by_id: dict = {}
        for row in data.get("candidates") or []:
            cid = _wc.candidate_id(row.get("id")) if isinstance(row, dict) else None
            if cid is not None and cid not in rows_by_id:
                rows_by_id[cid] = row
        scope_kw: dict = {}
        if pr_on and cand_type == _wc.TYPE_BILL:
            scope = data.get(PICK_ESTATE_ID_KEY)
            if isinstance(scope, str) and _wc.candidate_id(scope) == scope:
                scope_kw["scope_estate_id"] = scope
        cands = _wc.new_candidate_set(
            action=action, field=data.get("field"), cand_type=cand_type, ids=list(rows_by_id),
            has_more=data.get("has_more") is True, field_value=field_value,
            creator=_pending_creator(identity), **scope_kw,
            # F12（§5.1 (A)）：寬鬆路徑的候選集帶標記（選定後程式改寫草稿名稱用）；A-2a 精確名稱 ⇒ 同改動前。
            **({"lenient": True} if data.get(NAME_LENIENT_KEY) is True else {}),
        )
        head = f"{prefix}\n\n" if prefix else ""
        common = dict(
            agent_state=agent_state, user_message=user_message, trace_id=trace_id, start=start,
            tool_calls=tool_calls, violations=violations, llm_calls=llm_calls,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, trace=trace,
        )
        session = AgentSession(agent_state)
        if cands is None:
            session.clear_write_candidates()
            label = data.get("missing_label")
            ask = missing_labels_ask_text([label]) if isinstance(label, str) else None
            return self._finish_confirm_turn(
                kind="ask", outcome=make_outcome("clarifying", expects="text"),
                answer=f"{head}{ask or WF.WRITE_NOT_ISSUED_TEXT}", pending_id=None, **common,
            )
        session.write_write_candidates(cands)
        shown_ids = cands["ids"][:self._write_candidates_shown_limit(pr_on)]
        shown = [rows_by_id[cid] for cid in shown_ids]
        total = len(cands["ids"])
        lead = _wc.candidates_lead_text(cand_type, total, cands["has_more"])
        if pr_on:
            note = data.get(PICK_NOTE_KEY)
            note_text = data.get(PICK_NOTE_TEXT_KEY)
            if note in _wc.PICK_NOTE_DOMAIN and isinstance(note_text, str) and note_text:
                lead = note_text
                for mark in _wc.pick_note_marks(note):
                    if mark not in violations:
                        violations.append(mark)
            elif reask:
                lead = _wc.pr_reask_text(cand_type, total, cands["has_more"])
            if action == WF.BILL_DUE_EXTEND_FORM.action and cand_type == _wc.TYPE_ESTATE:
                violations.append(_wc.V_PICK_RIGHT_ESTATE_FIRST)
        if data.get(NAME_LENIENT_KEY) is True:
            # 寬鬆路徑的候選 ⇒ 程式固定前言（⛔ 回顯原話；清單可能超過第一頁 ⇒ 接
            # 「只比對了前 200 筆」）。清單、按鈕、候選集與精確名稱的候選相同。
            # r4 (乙)（缺名稱觸發；使用者沒講過名稱）⇒ (乙) 專用固定句（⛔「找不到完全相同的名稱」）。
            truncated = data.get(NAME_LENIENT_TRUNCATED_KEY) is True
            if data.get(NAME_LENIENT_MISSING_KEY) is True:
                lead = NAME_LENIENT_MISSING_LEAD_TEXT + (NM.NAME_LENIENT_TRUNCATED_NOTE if truncated else "")
            else:
                lead = NM.lead_text(truncated)
        text = lead + "\n" + _wc.user_list_text(cand_type, shown)
        if pr_on and _wc.pr_indistinct_ids(cand_type, shown):
            text += "\n" + _wc.PR_INDISTINCT_TEXT
        if cands["has_more"] or total > len(shown):
            text += "\n" + _wc.CANDIDATES_MORE_TEXT
        quick = [
            {"label": _wc.button_label(cand_type, row),
             "value": f"{_wc.PICK_VALUE_PREFIX}{cand_type}:{cid}"}
            for cid, row in zip(shown_ids, shown)
        ]
        violations.append(_wc.shown_marker(cand_type, total))
        return self._finish_confirm_turn(
            kind="ask", outcome=make_outcome("clarifying", expects="choice", action=action),
            answer=f"{head}{text}", dialog_answer=f"{head}{_wc.dialog_summary(cand_type, len(shown))}",
            pending_id=None, quick_replies=quick, ask_target=None, **common,
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

    # ------------------------------------------------------------------
    # W9 U2：文件回合的程式路徑（⛔ 一律由 Runtime 產出）
    # ------------------------------------------------------------------
    @staticmethod
    def _document_trace(document: Optional[DocumentTurnInput]) -> dict:
        """文件回合的 trace 四鍵。⛔ **只有封閉標籤與計數，無任何欄位值**。"""
        if document is None:
            return {}
        return {
            "has_document": True,
            "document_status": document.status,
            "document_kind": document.kind,
            "pages_seen": document.pages_seen,
        }

    def _document_program_turn(
        self, document: Optional[DocumentTurnInput], *, agent_state: dict,
        user_message: str, trace_id: str, start: float,
    ) -> Optional[TurnResult]:
        """擷取不出可用欄位 ⇒ 固定句收尾；其餘 ⇒ `None`（回合照常跑）。

        命中條件＝`facts` 為空：`unreadable`、全欄 null、`failed`、`timeout`
        四種情況在 `prepare_document_turn`／`build_document_facts` 都收斂成
        「沒有可引用的資料段」這一件事，⛔ 這裡不再分四條路各給一句
        （分四條路的失敗方向是「其中一條忘了收」＝帶文件的回合默默進模型，
        而模型手上沒有任何文件事實 ⇒ 它只能編）。

        ⛔ **不進模型**（`llm_calls == 0`）、⛔ Verifier 不跑（沒有可驗的引用）；
        走既有的 `_finish_confirm_turn`（S9-14：⛔ 不在門面直接產 `TurnResult`，
        那會繞過寫入閘與 dialog 紀律）。
        """
        if document is None:
            return None
        # 站內幫手 S3（§3h 第 4 點；D1～D3、D9）：謄本的程式終止句（DocuMind 未啟用／
        # 沒查成／一次一份／不是謄本）——封閉代碼 ⇒ 固定句，⛔ 不進模型。
        notice = getattr(document, "notice", None)
        if notice is not None:
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message,
                trace_id=trace_id, start=start, kind="answer",
                answer=DOCUMENT_NOTICE_TEXTS[notice], pending_id=None,
                violations=[f"document_notice:{notice}"],
                outcome=make_outcome("answered", expects="text"),
                document_trace=self._document_trace(document),
            )
        if document.facts.strip():
            return None
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message,
            trace_id=trace_id, start=start, kind="answer",
            answer=DOC_UNREADABLE_TEXT, pending_id=None,
            violations=[f"document_{document.status}"],
            outcome=make_outcome("answered", expects="text"),
            document_trace=self._document_trace(document),
        )

    def _document_turn_no_write(
        self, document: Optional[DocumentTurnInput], *, agent_state: dict,
        user_message: str, trace_id: str, start: float,
        violations: Optional[list] = None, tool_calls: Optional[list] = None,
        llm_calls: int = 0, prompt_tokens: int = 0, completion_tokens: int = 0,
    ) -> TurnResult:
        """W9-1：文件回合的**寫入面 per-turn 閘**——⛔ 不出確認卡、⛔ 不兌現。

        形狀與落點比照 `_scope_gate_confirm_request`：**不建 pending**、整回合就是
        一句固定句。兩個落點——
          ① `confirm_submit:<pid>` 機器值（排在確認段之前，⇒ ⛔ 不接受兌現）；
          ② 模型仍然呼到 `confirm.request`（第二道網；第一道是工具規格列表過濾）。

        ⚠️ 這是**邊界層**的封閉，⛔ 不靠模型自律、⛔ 不靠正本寫「不要送出」：
        文件段是本系統唯一「攻擊者可控的長文字＋`citable=True`」的組合，
        它與寫入面之間必須有一道與模型無關的閘。
        """
        vs = list(violations or [])
        vs.append("document_turn_no_write")
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message,
            trace_id=trace_id, start=start, kind="answer",
            answer=DOC_NO_WRITE_TEXT, pending_id=None,
            tool_calls=tool_calls, violations=vs,
            llm_calls=llm_calls, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            outcome=make_outcome("failed", expects="none"),
            document_trace=self._document_trace(document),
        )

    async def run_turn(
        self, identity: Identity, user_message: str, state: dict,
        *, image: Optional[ImageTurnInput] = None,
        context: Optional[str] = None,
        document: Optional[DocumentTurnInput] = None,
    ) -> TurnResult:
        """一個回合。`image`（W8 (2)）＝門面已抓檔／縮圖／辨識完的**封閉值**輸入。

        `context`（T1）＝呼叫端**進場時印給使用者的那一句**（選填）。⛔ 它不是
        使用者說的話：不併進 `user_message`、不進 dialog 歷史，只以一段
        **不可引用**的程式資料段進場（見 `_run_turn_body` 的注入區塊）。

        ⚠️ 本層只做一件本體外的事：`status=="partial"` 時把「只看了前 N 張」接在
        `TurnResult.answer` **最後**——時機在 `_append_dialog`／`card_sha256`／trace
        都定案之後，故那三者逐位元不受影響（同 W8 (3) `hint` 的紀律）。
        """
        result = await self._run_turn_body(
            identity, user_message, state, image=image, context=context,
            document=document,
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
        context: Optional[str] = None,
        document: Optional[DocumentTurnInput] = None,
    ) -> TurnResult:
        """四段管線的**接線**（Plan R R1）：程式段 → 資料注入 → 模型迴圈 → 出口閘。

        ⛔ 這一支本身 **不做任何判定**——每一段的條件、順序、文案都在各自的模組裡
        （`turn_segments`／`turn_context`／`_run_model_loop`／`exit_gates`），
        本函式只負責把同一個 `TurnAccumulator` 串過去。
        """
        start = self._clock()
        trace_id = uuid.uuid4().hex
        agent_state = state.setdefault("agent", {})
        # W9 U2：文件回合的四鍵，一次算好餵給本回合裡的每一個 trace 建構點。
        doc_trace = self._document_trace(document)

        # ── 第一段：模型前的程式段（六條終止路徑，順序即契約）────────────────
        # ⚠️ `_parse_confirm_value`／`_cache_key` 都是**純函式**，在這裡先算好傳進去
        #    ⛔ 不改變任何行為（段內唯一有副作用的 `handoff_cache` setdefault 仍留在
        #    清單點選段之後，見 `turn_segments` 模組 docstring）。
        segments = await run_program_segments(
            self, identity, user_message, agent_state,
            image=image, document=document, trace_id=trace_id, start=start,
            doc_trace=doc_trace,
            confirm_value=_parse_confirm_value(user_message),
            cache_key=_cache_key(user_message),
        )
        if segments.result is not None:
            return segments.result
        cache, cache_key = segments.cache, segments.cache_key

        acc, tool_specs, visible_names, doc_write_face, reserved_ids, scope_estate_id = (
            await self._build_turn_context(
                identity, user_message, state, agent_state,
                image=image, context=context, document=document,
                trace_id=trace_id, start=start, doc_trace=doc_trace,
                cache_key=cache_key,
            )
        )

        # `pick:` 機器值（`fullmatch`、⛔ NFKC、⛔ strip）在草稿讀回與建立者比對
        # （`_build_turn_context` → `_write_draft_begin`）之後判定：不成立 ⇒ 失效固定句結束回合；成立 ⇒
        # 不建意圖判斷呼叫，模型迴圈由程式依草稿出卡（⛔ 呼叫主模型），dialog 的使用者端只寫程式摘要。
        # 格式不合（前後空白、全形冒號…）⇒ `None` ⇒ 照一般文字進模型。開關未生效 ⇒ 一律不認。
        loop_message = user_message
        pick_value = (_wc.parse_pick_value(user_message)
                      if self._write_candidates_active() else None)
        if pick_value is not None:
            pick_exit = self._write_candidate_pick_begin(
                acc, identity, agent_state, pick_value, document)
            if pick_exit is not None:
                return pick_exit
            # F12（§5.1 (A)）：寬鬆來源的選定 ⇒ 程式依本身分清單改寫草稿名稱（程式出卡之前）。
            await self._name_lenient_pick_rewrite(acc, identity, agent_state)
            loop_message = _wc.CANDIDATE_PICK_DIALOG_USER
        else:
            # W1b（§8.6-3a）：意圖判斷呼叫 task 在這裡建立——程式段未結束回合、`_build_turn_context`
            # 之後；與下面的主模型迴圈並行。收尾在組 trace 的兩處（見 `_WriteIntentCall`）。
            self._start_write_intent_call(acc, identity, agent_state, user_message, document)

        # ── 第三段：模型迴圈（第四段的四道出口閘由 `exit_gates.finalize` 收尾）──
        try:
            return await self._run_model_loop(
                acc, identity, loop_message, state, agent_state,
                document=document, cache=cache, tool_specs=tool_specs,
                visible_names=visible_names, doc_write_face=doc_write_face,
                reserved_ids=reserved_ids, scope_estate_id=scope_estate_id,
            )
        except BaseException:
            # 回合以例外離開（沒有 trace 可組、收尾掛點走不到）⇒ 撤掉意圖 task 與登記，
            # ⛔ 留下孤兒呼叫。正常出口一律在組 trace 時收尾，這裡不計量。
            if acc.write_intent_call is not None:
                acc.write_intent_call.abort()
            if acc.dialog_act_call is not None:
                acc.dialog_act_call.abort()
            raise

    async def _build_turn_context(
        self, identity: Identity, user_message: str, state: dict, agent_state: dict,
        *, image, context: Optional[str], document, trace_id: str, start: float,
        doc_trace: dict, cache_key: str,
    ) -> tuple:
        """第二段：回合狀態容器 ＋ prompt 組裝 ＋ **九段資料注入**（Plan R R1）。

        ⛔ 逐字搬自原 `_run_turn_body`——九段的**條件、順序、文案**都沒有改；
        差別只有九段各自那 25 行的注入樣板收斂成 `TurnAccumulator.inject()` 一支
        （形狀只有一種），與保留 id 改由 `ReservedCallIds` 統一派生。

        回 `(acc, tool_specs, visible_names, doc_write_face, reserved_ids,
        scope_estate_id)`——後五格是模型迴圈要用的**不變輸入**。
        """
        # ── 回合狀態容器（Plan §0c：閉包捕獲的可變名稱一律收進這一個物件）──────
        # `new_nonce()`（`services.agent.prompt_assembler`）＝ 16 位十六進位，
        # 符合 `wrap_tool_data`／`PromptAssembler` 的 nonce 形狀守門；
        # ⛔ 不用 `secrets.token_urlsafe`——它會產出 `-`／`_`，被 `_require_nonce`
        # 的 `^[0-9A-Za-z]{8,64}$` 擋下（2.5 接線時發現，見任務回報）。
        acc = TurnAccumulator(
            cache_key=cache_key, nonce=new_nonce(), trace_id=trace_id, start=start,
        )
        # S2 §3（plan-verifier r2 #3／r3 #1）：**保留 tool_call id 集合**——本回合
        # 程式會產出的資料段 id 一律由 nonce 導出、在回合最開始就固定下來
        # （派生與無條件性的理由見 `turn_context.ReservedCallIds`）。
        ids = acc.reserved
        reserved_ids: frozenset[str] = ids.all
        # L15 (a)③④：本回合的會話範圍（`select:` 段寫的），與範圍內／外的工具
        # 結果計數（`acc.scope_counts`）。⛔ 不進 trace 新鍵（L15-11：只用既有的
        # `violations`）。
        scope_estate_id = _scope_estate_id(agent_state)
        # T1：正規化與記憶行走**同一支** `sanitize_data_piece`（控制字元／零寬／
        # 雙向／換行／假標記逐類剝除）。非字串或剝完為空 ⇒ 空字串＝不注入。
        entry_text = sanitize_data_piece(context).strip()
        # T3（Plan §4）：讀「緊鄰上一回合出口寫入之值」——T1 保證每一個回合出口
        # （`finalize`／`_finish_confirm_turn`／`handoff_cache` 重播）都會寫
        # `agent_state[LAST_ASK_TARGET_KEY]`，故這裡讀到的必是上一回合的值，
        # ⛔ 不會讀到更早以前殘留的舊訊號。
        last_ask_target = agent_state.get(LAST_ASK_TARGET_KEY)
        # W1（§2.1(3)）：讀回並驗證寫入草稿、套用回合開頭的清除條件（開關 off／身分不同／
        # 釘住範圍／看不到寫入工具），建立本回合的草稿狀態（影子回合 ⇒ 不跑，`acc.write_draft=None`）。
        # W1b：同時讀出上一回合程式追問的欄位（`asked`，讀出即清）與本句是否凍結（問句）。
        self._write_draft_begin(acc, identity, agent_state, user_message)
        # 2.9 路徑對齊：槽位在 **`collected_data` 頂層**（見 `_slots_for_prompt`）。
        slots = _slots_for_prompt(state)
        # 任務 4.2（Plan §4.1-2）：身分槽位一律由**入口身分**現算後覆寫。
        # ⛔ 不用 `setdefault`（那等於讓儲存側／模型寫的值贏）；⛔ 不回寫
        # `state`（`_slots_for_prompt` 回的是新 dict，覆寫只影響本回合 prompt）；
        # ⛔ 不落 DB。模型能寫的是 `identity_detail`（角色子類），它動不到這兩鍵。
        slots["identity"] = identity.resolved_audience()
        slots["identity_source"] = derive_identity_source(identity)
        dialog = agent_state.get("dialog", [])
        # `_select_outline` 每回合從正本現組 K=5 候選節＋目錄（或降級的
        # toc-only）；**同一個** outline 物件接著餵 `_seed_outline_provenance`
        # 與 `assembler.build_messages`（下方）。
        outline, sel_meta = await self._select_outline(
            identity, user_message, dialog, acc.violations
        )
        # Plan §0c r2 #4：段落產生後寫入、之後唯讀的 trace 輸入。
        acc.snapshot = TurnInputsSnapshot(
            candidate_ids=list(sel_meta["candidate_ids"]) if sel_meta else [],
            winning_key_kind=dict(sel_meta["winning_key_kind"]) if sel_meta else {},
            miss_kind=sel_meta["miss_kind"] if sel_meta else None,
            entry_text=entry_text,
            doc_trace=doc_trace,
            outline_sha=getattr(outline, "sha256", "") if outline is not None else "",
            rules_sha=getattr(self.verifier, "rules_sha", "") or "",
        )
        seeded_outline = _seed_outline_provenance(outline)
        if seeded_outline is not None:
            acc.tool_results_by_id[OUTLINE_TOOL_CALL_ID] = seeded_outline

        tool_specs = self.registry.to_openai_tools(
            identity, self._stage, readonly_view=self.readonly_view
        )
        doc_write_face = self._doc_write_face(identity, document)
        if doc_write_face:
            tool_specs = [
                t for t in tool_specs
                if tool_name_from_openai(t["function"]["name"]) not in doc_write_face
            ]
        tool_specs = _document_confirm_tool_specs(tool_specs, document)
        visible_names = {tool_name_from_openai(t["function"]["name"]) for t in tool_specs}   # 解回 registry 名

        acc.messages = self.assembler.build_messages(
            identity, outline, slots, dialog, tool_specs, acc.nonce
        )

        # ── 第二段：九段資料注入（形狀唯一，見 `TurnAccumulator.inject`）──────
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
            acc.violations.append("affirmative_carry")
            acc.inject(CALLER_AFFIRMATIVE_LABEL, ids.affirmative, AFFIRMATIVE_CARRY_TEXT,
                       citable=False, source=CALLER_AFFIRMATIVE_PROVENANCE_SOURCE)

        # T3（Plan §4）：**空會話註記**——dialog 長度 0（封閉條件）⇒ 注入固定句，
        # 讓模型能誠實回答「你剛剛問了我什麼」這類問題，而不是在沒有歷史時
        # 憑印象幻覺。同樣排在 DSP-022 那句之前，理由同上。
        if not dialog:
            acc.inject(CONTEXT_EMPTY_SESSION_LABEL, ids.context_empty, EMPTY_SESSION_TEXT,
                       citable=False, source=CONTEXT_EMPTY_SESSION_PROVENANCE_SOURCE)

        # U3（Plan `plan-walkthrough-fixes-batch3-20260909.md` §4）：純編號／
        # 短名詞一句 ⇒ 程式先查一次，把結果當可引用資料段注入——模型才不會反問
        #「哪一種類型」。⛔ 不代模型作答、不改變 outcome；⛔ 原 ref／關鍵字不進
        # trace／決策快照（只記 `pre_lookup_trace`）。⚠️ 同 T3 兩段的排法：
        # 排在 DSP-022 那句**之前**——這是使用者這句之前的背景資料。
        # W1b §8.1-3：草稿缺物件名稱（且符合安全處置 2b／2d／5a 的條件）⇒ 同一條既有前置查詢以
        # `after_name_ask=True` 跑（⛔ 另開第二條查詢路徑；查無照舊不注入）。
        # A-2a（A2-R3）：`pick:` 機器值回合由程式處理（`_write_candidate_pick_begin`），⛔ 前置查詢
        # （失效時 0 次 JGB 查詢；成立時只有出卡前那一次帶 viewer 的精確編號查詢）。
        pick_turn = (self._write_candidates_active()
                     and _wc.parse_pick_value(user_message) is not None)
        pre_trigger = None if pick_turn else _pre_lookup_trigger(
            user_message,
            after_name_ask=(last_ask_target in _PRE_LOOKUP_NAME_ASK_TARGETS
                            or self._write_draft_name_catch_eligible(acc)),
        )
        if pre_trigger is not None:
            pre_kind, pre_candidate = pre_trigger
            pre_carry: Optional[tuple] = None
            if pre_kind == "id":
                pre_outcome, pre_facts = await self._pre_lookup_id_result(
                    identity, pre_candidate, scope_estate_id, acc.violations
                )
            else:
                pre_outcome, pre_facts, pre_carry = await self._pre_lookup_keyword_result(
                    identity, pre_candidate, scope_estate_id, acc.violations
                )
            # 第六批 #10 **寫點 (b)**：前置查詢命中**唯一一個物件** ⇒ 記起來。
            # ⛔ 只記 name／id 兩鍵；釘住範圍時 `_write_estate_carry` 自己不寫。
            # ⛔ violation 只留一個無名稱的標記（名稱不得進 trace／決策快照）。
            if pre_carry is not None and _write_estate_carry(agent_state, *pre_carry):
                acc.violations.append("estate_carry_set")
            # W1b §8.1-3：草稿缺物件、這句經前置查詢對到**唯一**物件 ⇒ 物件名稱（系統查得的值，
            # ⛔ 用模型輸出）寫進草稿（條件與凍結判斷在 `_write_draft_catch_name` 內）。
            if pre_carry is not None:
                self._write_draft_catch_name(acc, agent_state, pre_carry[0], segment=pre_candidate)
            acc.snapshot.pre_lookup_trace = {
                "kind": pre_kind, "hits": 1 if pre_outcome == "found" else 0,
            }
            # L15：範圍外 ⇒ **完全不注入**（連查無固定句也不印——範圍檢查本身
            # 就已經在別的路徑上有指路句，這裡多印一句等於多一個揭露面）。
            # `"error"`（逾時／速率限制／例外）同樣**完全不注入**——這種情況
            # 是「沒查成」，⛔ 不得講成「查不到」（那是把沒查講成查過沒有）；
            # 也 ⛔ 不把工具錯誤碼露給使用者，直接讓這一回合當成沒觸發過。
            # 短名詞（keyword）查無**不注入**：≤6 字無標點的短句大多不是名詞（「怎麼辦」
            # 「取消」「延三天」），對它們印「查不到這個編號或名稱」會誤導模型；只有
            # 純編號（id）查無才有意義（編號一定是在指一筆資料）。名詞查到才注入。
            keyword_miss = pre_kind == "keyword" and pre_outcome == "not_found"
            if pre_outcome not in ("out_of_scope", "error") and not keyword_miss:
                inject_text = pre_facts if pre_outcome == "found" else PRE_LOOKUP_NOT_FOUND_TEXT
                inject_text = sanitize_data_piece(inject_text)
                if inject_text:
                    acc.inject(PRE_LOOKUP_LABEL, ids.pre_lookup, inject_text,
                               citable=True, source=PRE_LOOKUP_PROVENANCE_SOURCE)

        # V2（Plan batch4 §3）：**有前文的零查詢**——釘住範圍時不注入（同
        # `completed_actions_line`／前置查詢那一套 L15 紀律：範圍內的對話不該
        # 再讓「最近提過的編號」跨戶漏出去）；非空時以不可引用資料段注入，
        # 供模型在對象不明時先當它是那一筆（見下方 T2 迴圈內改寫分支）。
        # R3：與下方（第六批 #10）的 `estate_carry` 同一道門檻——
        # `AgentSession.prompt_segments` 收斂兩段各自的
        # 「if scope_estate_id is None」判斷成唯一一處（⛔ 判定值不變：
        # `_scope_estate_id` 對本檔唯一的 `SELECT_SCOPE_KEY` 寫點
        # `_run_select_segment` 而言與舊的 `SELECT_SCOPE_KEY is None` 檢查
        # 等價——該寫點只會寫 `None` 或帶非空 `estate_id` 的 dict）。兩段的
        # 實際計算仍是各自的純函式，本呼叫只做門檻，⛔ 不改計算內容。
        _prompt_segments = AgentSession(agent_state).prompt_segments(
            scope_estate_id,
            recent_refs_ids=_recent_ref_ids(agent_state, dialog),
            estate_carry=_estate_carry_of(agent_state),
        )
        recent_refs_ids: list[str] = _prompt_segments["recent_refs_ids"]
        acc.snapshot.has_recent_refs = bool(recent_refs_ids)
        if acc.snapshot.has_recent_refs:
            recent_refs_text = sanitize_data_piece(
                RECENT_REFS_TEXT_PREFIX + "、".join(recent_refs_ids)
            )
            acc.inject(RECENT_REFS_LABEL, ids.recent_refs, recent_refs_text,
                       citable=False, source=RECENT_REFS_PROVENANCE_SOURCE)

        # W9 U2／W9-22：**文件事實排在使用者訊息之前**。
        # ⚠️ 這是本回合最大的一段「不可信文字」，⛔ 不得是模型看到的最後一則訊息
        #    ——最後一則的位置在既有紀律裡屬於使用者這一句（DSP-022）。
        # ⚠️ 既有的影像／完成動作／進場句三段排在使用者訊息**之後**，與 T3 兩段
        #    的紀律不一致；那是既有債（Plan 列後續 L-W9-a），⛔ 不在本單元一併改
        #    ——動它會改變照片線送給模型的訊息順序，而「照片線逐位不變」是本
        #    單元的回退證明。
        # ⛔ 不併進 `user_message`（那會變成使用者說的話）、⛔ 不進 dialog
        #    （`_append_dialog` 不動）、⛔ 不進 `agent_state`、⛔ 不進 trace 欄位值。
        if document is not None and document.facts.strip():
            acc.inject(DOCUMENT_DATA_LABEL, ids.document, document.facts,
                       citable=True, source=DOCUMENT_PROVENANCE_SOURCE,
                       data={"pages_seen": document.pages_seen,
                             "pages_total": document.pages_total})

        # W1（§2.1(3)）：**進行中的寫入草稿**——只放動作中文名與欄位標籤（⛔ 放使用者值：值
        # 已在對話歷史裡）；`citable=False`（會話記憶類）、保留 id `wd-<head>`、過
        # `sanitize_data_piece`；排在 DSP-022 那句**之前**（同 T3 兩段的紀律）。
        # ⚠️ 問句凍結回合（§8.5-3）⛔ 注入：業主原文「交主模型正常回答」——實測注入這行會把
        # 主模型推回追問寫入欄位（W1c verifier F1：T 第二句自寫「物件名稱和問題描述」追問）。
        wd = acc.write_draft
        if wd is not None and wd.draft is not None and not wd.frozen:
            draft_text = sanitize_data_piece(WF.draft_injection_text(wd.draft))
            if draft_text:
                acc.inject(WRITE_DRAFT_LABEL, ids.write_draft, draft_text,
                           citable=False, source=WRITE_DRAFT_PROVENANCE_SOURCE)

        # DSP-022：當前這句一定是最後一則 user 訊息（歷史由 assembler 從 `dialog` 放前面）。
        acc.messages.append({"role": "user", "content": user_message})
        # W8 (2)：影像事實以**可引用的工具事實**進場（r1 裁定接線）——包法與工具
        # 回傳完全相同（`wrap_provenance_data` ＋ 同回合 nonce），故模型引用它的
        # 句子解析得出來、過得了 Verifier（驗收 (xii)）。
        # ⛔ 不併進 `message`（那會變成使用者說的話）、⛔ 不經 `agent_state`。
        if image is not None and image.status in ("ok", "partial"):
            # 照片建議（封閉值）進 session：給之後回合的 `confirm.request` 補分類用。
            # 新照片一律覆寫（沒辨識出分類就寫 None，⛔ 不讓上一張的分類殘留到這張）。
            # 站內幫手 S3（F10）：照片中繼資料併進**同一個**一次性建議（⛔ 不新增鍵）；
            # 有照片才多一個 `photos`，沒照片的建議逐字不變。
            has_category = (
                isinstance(image.suggested_category, str) and image.suggested_category.strip()
            )
            photos = [dict(p) for p in (image.photos or ()) if isinstance(p, dict)]
            suggestion = None
            if has_category or photos:
                suggestion = {
                    "category_name": image.suggested_category if has_category else None,
                    "item": image.suggested_item,
                    "reason": image.suggested_reason,
                    "description": image.suggested_description,
                }
                # 站內幫手 S3-live A7：分類是葉節點才多記父分類（沒有就不加鍵，建議逐字不變）。
                if has_category and image.suggested_parent_category:
                    suggestion["parent_category_name"] = image.suggested_parent_category
                if photos:
                    suggestion["photos"] = photos
            AgentSession(agent_state).write_image_suggestion(suggestion)
        if image is not None and image.status in ("ok", "partial") and image.facts.strip():
            acc.inject(IMAGE_DATA_LABEL, ids.image, image.facts,
                       citable=True, source=IMAGE_PROVENANCE_SOURCE,
                       data={"processed": image.processed, "total": image.total})

        # 第六批 #10 **讀點**：照片回合多一句「本對話最近提到的物件：X」。
        # ⚠️ 病灶是「先講物件、再傳照片」——照片段本身沒有物件資訊，模型只好反問。
        # ⛔ `citable=False`（同呼叫端進場句那一段的紀律）：這是**程式組的一句
        #    會話記憶**，⛔ 不是可引用的事實來源，模型不得拿它當 `refs` 的依據。
        # ⛔ 不進 `user_message`、⛔ 不進 dialog、⛔ 不進 trace（名稱是識別碼）。
        # ⚠️ 釘住範圍時 `_estate_carry_of` 讀到的一定是舊值或空——寫入口本來就
        #    不在釘住時寫；這裡再擋一次，理由同 `recent_refs`（釘住的對話 ⛔ 不
        #    讓另一戶的名字漏進來）。
        estate_carry = _prompt_segments["estate_carry"]
        if image is not None and estate_carry is not None:
            estate_carry_text = sanitize_data_piece(
                ESTATE_CARRY_TEXT_PREFIX + estate_carry["name"]
            )
            if estate_carry_text:
                acc.inject(ESTATE_CARRY_LABEL, ids.estate_carry, estate_carry_text,
                           citable=False, source=ESTATE_CARRY_PROVENANCE_SOURCE)

        # S2／H3：完成動作記憶——與影像事實**同一套**注入紀律（可引用資料段、
        # 同回合 nonce、⛔ 不進 dialog、⛔ 不經 `agent_state` 以外的任何管道）。
        # 只有非空且（有釘範圍時）有同戶項目才真的注入——沒有東西可引用時
        # 不佔一段 messages。
        completed_line = completed_actions_line(
            agent_state.get(COMPLETED_ACTIONS_KEY), scope_estate_id
        )
        if completed_line:
            acc.inject(COMPLETED_ACTIONS_LABEL, ids.completed, completed_line,
                       citable=True, source=COMPLETED_ACTIONS_PROVENANCE_SOURCE)

        # T1（Plan §2）：**呼叫端進場句**——與影像事實／完成動作記憶行同一套注入
        # 紀律，只差一個旗標：`citable=False`（進場句是呼叫端印的字，⛔ 不是可
        # 引用的事實來源）。
        # ⛔ 不併進 `user_message`（那會變成使用者說的話）、⛔ 不進 dialog 歷史
        #    （`_append_dialog` 不動）、⛔ 不進 trace／決策快照（只記 bool）。
        # ⚠️ **一定要登記進 `tool_results_by_id`**：不登記的話模型引用它會落
        #    `ref_source_not_found`，而正確的訊號是 `SOURCE_NOT_CITABLE`
        #    （`TurnAccumulator.inject` 兩件事一起做，⛔ 不得只做一半）。
        if entry_text:
            # V4（Plan batch4 §5）：**先 sanitize 再加常數前綴**——前綴不含任何
            # 呼叫端輸入，不需要也不應該再過一次 `sanitize_data_piece`；
            # `has_context`／空值判斷仍以未加前綴的 `entry_text` 為準。
            entry_display_text = CALLER_CONTEXT_PREFIX + entry_text
            acc.inject(CALLER_CONTEXT_LABEL, ids.entry, entry_display_text,
                       citable=False, source=CALLER_CONTEXT_PROVENANCE_SOURCE)

        return (acc, tool_specs, visible_names, doc_write_face,
                reserved_ids, scope_estate_id)

    def _doc_write_face(self, identity: Identity, document) -> frozenset:
        """W9-1 落點②：**文件回合的寫入面對模型不可見**——回這一回合要藏起來的
        工具名集合（非文件回合 ⇒ 空集合）。

        判準沿用 registry 對「會改狀態的工具」的三個旗標聯集：`scope == "write"`
        **或** `mcp_only` **或** `mutates_session`——第三個旗標是 verifier
        2026-09-09 F1 補的：`confirm.request` 的正本規格是 `scope=read,
        mcp_only=None, mutates_session=True`（見 `tools/confirm.py::CONFIRM_SPEC`），
        只看前兩個旗標會漏掉它，文件回合就會多執行一次確認登記、留一列孤兒 token
        （不可兌現，但不該發生）。與 `registry.specs_for` 的 `readonly_view` 判準
        （`scope=="write" or mutates_session`）同一族，⛔ 不在此另列一張工具名單：
        名單會漏掉之後新加的寫入工具，而漏掉的那一支不會有任何徵兆。第二道網在
        `_run_model_loop`（模型硬造名字時擋執行），第三道在
        `_document_turn_no_write`（⛔ 三道都不得單獨拿掉）。
        """
        if document is None:
            return frozenset()
        # 站內幫手 S3（§3h 第 1 點，S3-4）：**只在**放行對照內的文件回合把
        # `confirm.request` 移出寫入面（其餘寫入工具與其他 kind 照舊）。放行條件的唯一
        # 來源是 `document_extract.DOCUMENT_TURN_WRITABLE`（經 `document_writable_action`）。
        keep_confirm = document_writable_action(document) is not None
        return frozenset(
            s["name"]
            for s in self.registry.specs_for(
                identity, self._stage,
                readonly_view=self.readonly_view, for_model=True,
            )
            if (s.get("scope") == "write" or s.get("mcp_only") or s.get("mutates_session"))
            and not (keep_confirm and s["name"] == CONFIRM_TOOL_NAME)
        )

    # ------------------------------------------------------------------
    # 寫入草稿與意圖判斷呼叫
    # ------------------------------------------------------------------
    def _write_draft_specs(self, identity: Identity) -> Optional[list]:
        """`registry.specs_for(identity, stage, for_model=False)`；拿不到（替身沒有 `specs_for`／
        例外）⇒ `None`（呼叫端一律當看不到，fail-closed）。"""
        if self.readonly_view:
            return None
        specs_for = getattr(self.registry, "specs_for", None)
        if not callable(specs_for):
            return None
        try:
            return list(specs_for(identity, self._stage, readonly_view=False, for_model=False) or [])
        except Exception:  # noqa: BLE001 — 拿不到可見性 ⇒ 當看不到
            return None

    def _write_draft_visible(self, identity: Identity, action: Any) -> bool:
        """可見性閘：`registry.specs_for(identity, stage, for_model=False)` 看得到
        `jgb2.action.<action>`、且非 `readonly_view`（比照 `_prepare_closed_action`「別的受眾
        ⛔ 出一張永遠兌現不了的卡」）。查不到可見性（替身沒有 `specs_for`／例外）⇒ 看不到
        （fail-closed）。"""
        if not isinstance(action, str) or action not in WF.FORMS:
            return False
        name = f"jgb2.action.{action}"
        return any(isinstance(s, dict) and s.get("name") == name
                   for s in (self._write_draft_specs(identity) or []))

    def _write_draft_any_visible(self, identity: Identity) -> bool:
        """W1b §8.6-3a：看得到**任一** `jgb2.action.*`（意圖判斷呼叫的建立條件之一）。"""
        names = {f"jgb2.action.{action}" for action in WF.FORMS}
        return any(isinstance(s, dict) and s.get("name") in names
                   for s in (self._write_draft_specs(identity) or []))

    def _write_draft_persist(self, acc: TurnAccumulator, agent_state: dict) -> None:
        """草稿落地（`AgentSession`）＋稽核兩字串（只有動作名與鍵名，⛔ 值）。"""
        wd = acc.write_draft
        if wd is None or wd.draft is None:
            return
        # 「選對紀錄」片 §4.2-1：落地前一律再判一次（其他合併路徑也可能改了物件或期別；判過即同步錨點，⛔ 遞迴）。
        self._pick_right_said_reset(acc, agent_state)
        AgentSession(agent_state).write_write_draft(wd.draft)
        for mark in WF.draft_trace_marks(wd.draft):
            if mark.startswith(WF.TRACE_DRAFT_KEYS_PREFIX):
                # 鍵名清單會隨本回合合併而變：只留最新一筆。
                acc.violations[:] = [v for v in acc.violations
                                     if not str(v).startswith(WF.TRACE_DRAFT_KEYS_PREFIX)]
            if mark not in acc.violations:
                acc.violations.append(mark)

    def _write_draft_clear(self, acc: TurnAccumulator, agent_state: dict) -> None:
        AgentSession(agent_state).clear_write_draft()
        if acc.write_draft is not None:
            acc.write_draft.draft = None

    def _write_draft_begin(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
    ) -> None:
        """回合開頭：讀回草稿（**一律視為不可信**，`write_forms.load_draft` 驗形狀）並套用
        清除條件；建立 `acc.write_draft`。影子回合 ⇒ 完全不碰（⛔ 清、⛔ 寫、⛔ 注入）。

        W1b：`asked`（上一回合程式缺欄追問的欄位鍵）讀進回合內狀態後，草稿裡的那一份**立刻
        經 `AgentSession` 寫回 `[]`**（安全處置 1c：只對緊接的下一回合有效，⛔ 只清副本）；
        `asked` 非空且當句是問句 ⇒ 本回合凍結（§8.5-3）。"""
        acc.write_draft = None
        if self.readonly_view:
            return
        session = AgentSession(agent_state)
        lifecycle_on = bool(getattr(self, "_write_lifecycle_on", False))
        if not getattr(self, "_write_draft_on", False):
            # 開關 off ⇒ 撤回草稿機制：殘留的草稿清掉（清≠寫），本回合不建、不觸發。
            session.clear_write_draft()
            session.clear_last_submitted()
            return
        # 第 3 步 #9g：「最近送出」標記只在 `AGENT_WRITE_LIFECYCLE` on 時有效；off ⇒ 殘留清掉。
        last_submitted: Optional[dict] = None
        if not lifecycle_on:
            session.clear_last_submitted()
        else:
            last_submitted, mark_invalid = WF.load_last_submitted(session.get_last_submitted())
            if mark_invalid:
                acc.violations.append(WF.V_LAST_SUBMITTED_SHAPE_INVALID)
                session.clear_last_submitted()
        draft, invalid = WF.load_draft(session.get_write_draft())
        if invalid:
            acc.violations.append(WF.V_DRAFT_SHAPE_INVALID)
            session.clear_write_draft()
        if agent_state.get(SELECT_SCOPE_KEY) is not None:
            # 釘住範圍（`select:`）⇒ 草稿清掉，本回合整個草稿機制不跑（不建、不注入、不觸發；
            # 比照 `_estate_carry_of`）。
            session.clear_write_draft()
            return
        owner = _write_draft_owner(identity)
        if draft is not None and (
            draft["created_by_role"] != owner
            or not self._write_draft_visible(identity, draft["action"])
        ):
            session.clear_write_draft()
            draft = None
        asked: list = []
        if draft is not None:
            asked = list(draft.get("asked") or [])
            if asked:
                draft["asked"] = []
                session.write_write_draft(draft)
        frozen = bool(asked) and _is_question(user_message)
        # plan-fill-wide-20261028 §4.1 (b)、§11 r1c：綁定卡活不活，判準同 `_write_draft_reissue_gate`。
        bound = (self._write_draft_bound_card(identity, agent_state, draft["action"])
                 if draft is not None else None)
        bound_card_live = (bound is not None and not isinstance(bound[1].get("receipt"), dict)
                           and bound[1].get("invalidated") is not True)
        acc.write_draft = _WriteDraftTurn(
            draft=draft, owner=owner,
            user_texts=_write_draft_user_texts(agent_state, user_message),
            asked=asked, had_draft=draft is not None, frozen=frozen,
            last_submitted=last_submitted,
            user_message=user_message if isinstance(user_message, str) else "",
            bound_card_live=bound_card_live,
        )
        if frozen:
            acc.violations.append(WF.V_QUESTION_FROZEN)
        if self._write_candidates_active():
            acc.write_draft.candidates = self._write_candidates_load(acc, identity, session, draft)
            # F12 r6 復原第 5 輪 §11.15.3 第 1 點：回合開始的快照（`_write_candidates_load` 已做綁定檢查）。
            loaded = acc.write_draft.candidates
            acc.write_draft.post_pick_start = loaded is not None and (
                loaded.get("picked") is not None or _wc.is_withdrawn(loaded))
            # 選定後回合改指令式（名稱值一律規則）：只有回合開始已選定（已撤回不算）。
            acc.write_draft.cmd_scope_start = loaded is not None and loaded.get("picked") is not None
        if (self._pick_right_active() and isinstance(draft, dict)
                and draft.get("action") == WF.BILL_DUE_EXTEND_FORM.action):
            fields = draft.get("fields") or {}
            acc.write_draft.pr_anchor = (fields.get("estate_name"), fields.get("period"))

    def _write_candidates_load(
        self, acc: TurnAccumulator, identity: Identity, session: AgentSession, draft: Optional[dict],
    ) -> Optional[dict]:
        """讀回候選集（**一律視為不可信**，`load_write_candidates` 驗形狀；
        不合 ⇒ 丟棄並記標記，比照 `load_draft`），再綁定檢查——建立者＝本回合身分、草稿存在且動作相同、
        該欄位的名稱指紋與列出候選時相同；任一不符 ⇒ 清掉（⛔ 半信）。呼叫點在草稿讀回、建立者比對、
        `SELECT_SCOPE_KEY` 清草稿之後（那幾處清草稿時已一併清掉候選集）。"""
        raw = session.get_write_candidates()
        if raw is None:
            return None
        cands, invalid = _wc.load_write_candidates(raw)
        if invalid or cands is None:
            if invalid:
                acc.violations.append(_wc.V_CANDIDATES_SHAPE_INVALID)
            session.clear_write_candidates()
            return None
        if not self._write_candidates_bound(cands, identity, draft):
            session.clear_write_candidates()
            return None
        return cands

    @staticmethod
    def _write_candidates_bound(cands: dict, identity: Identity, draft: Optional[dict]) -> bool:
        """候選集仍綁定這份草稿：建立者（原值比對，同 `_pending_creator`）、動作、該欄位名稱指紋。"""
        if cands.get("creator") != _pending_creator(identity):
            return False
        if not isinstance(draft, dict) or draft.get("action") != cands.get("action"):
            return False
        value = WF.to_payload(draft["action"], draft.get("fields") or {}).get(cands.get("field"))
        return _wc.name_fp(value) == cands.get("name_fp")

    def _write_candidates_field_value(self, acc: TurnAccumulator, data: Any) -> Any:
        """候選形狀 `data["field"]` 在**本回合草稿**的名稱值（候選集 `name_fp` 的來源；⛔ 取 payload 裡
        `confirm.request` 改寫過的值）。"""
        wd = acc.write_draft
        draft = wd.draft if wd is not None else None
        if not isinstance(draft, dict) or not isinstance(data, dict):
            return None
        return WF.to_payload(draft["action"], draft.get("fields") or {}).get(data.get("field"))

    def _write_candidates_eligible(
        self, acc: TurnAccumulator, agent_state: dict, data: Any, *, document: Any,
        program_call: bool,
    ) -> bool:
        """這次 `confirm.request` 的候選形狀可不可以寫候選集。
        只在：開關生效、程式依草稿發出（`wd_program`／提議轉成的程式呼叫）、非文件回合、非文件暫存回合、
        非點選範圍回合、非影子回合、且草稿動作＝候選形狀的動作。其餘 ⇒ `False`（呼叫端換回現行出口）。"""
        if not program_call or not self._write_candidates_active():
            return False
        if document is not None or document_writable_action(document) is not None:
            return False
        if _document_carry_of(agent_state) is not None:
            return False
        if agent_state.get(SELECT_SCOPE_KEY) is not None or self.readonly_view:
            return False
        wd = acc.write_draft
        draft = wd.draft if wd is not None else None
        return (isinstance(draft, dict) and isinstance(data, dict)
                and draft.get("action") == data.get("action"))

    def _write_candidates_program_pick(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
    ) -> Optional[dict]:
        """程式專用選定通道的值——候選集已選定（`picked`）、仍綁定本草稿（建立者、
        動作、該欄位名稱指紋）⇒ `{action, field, type, id}`；其餘 ⇒ `None`。只由 `wd_program` 呼叫點使用。

        修正 1（A2-R5「回原流程」）：沒有候選集（出卡時已清，A2-R6 (a)）⇒ 退回讀本草稿綁定卡帶著的選定
        （`_write_candidates_card_pick`）；有候選集但未選定（新清單取代舊的，A2-R6 (b)）⇒ `None`。"""
        if not self._write_candidates_active():
            return None
        wd = acc.write_draft
        if wd is None:
            return None
        cands = wd.candidates
        if cands is None:
            return self._write_candidates_card_pick(acc, identity, agent_state)
        if cands.get("picked") is None:
            # 「選對紀錄」片 §4.1-1：已選物件的帳單候選未選定（客人改講金額／期間）⇒ 重查只在該物件；
            # 開關 off 或不是這種候選集 ⇒ `None`（同改動前）。
            return self._pick_right_scope_pick(acc, identity)
        if not self._write_candidates_bound(cands, identity, wd.draft):
            return None
        return _wc.program_pick_of(cands, cands["picked"])

    def _write_candidates_proposal_pick(self, acc: TurnAccumulator, identity: Identity) -> Optional[dict]:
        """F12 r6（§11.4 第 2 點「出卡入口的關口」；V7-2）：提議轉成的程式呼叫（`proposal_program`）的程式專用選定——
        候選集已選定、仍綁定本草稿 ⇒ `{action, field, type, id}`；其餘 ⇒ `None`（與改動前相同：不帶）。
        ⛔ 帶綁定卡的選定、⛔ 帶「選對紀錄」物件範圍（那兩條只在 `wd_program`，維持現行）。"""
        cands = self._write_candidates_post_pick(acc, identity)
        if cands is None or cands.get("picked") is None:
            return None
        return _wc.program_pick_of(cands, cands["picked"])

    def _write_candidates_card_pick(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
    ) -> Optional[dict]:
        """修正 1：本草稿目前綁定的那張卡（`_write_draft_bound_card`：最後一筆同動作、同建立者）帶著的選定 ⇒
        `{action, field, type, id}`；其餘 ⇒ `None`（照名稱重新解析）。全部成立才帶：

        - 草稿是回合開始就有、本回合沒換（`had_draft and not created`）——新草稿＝舊草稿已清，選定一併作廢；
        - 綁定卡＝本回合 A2 以 `redeem_pending` 燒成功、且燒之前判為 live 的那一張（`reissue_live_pid`；
          已兌現／已取消／過期／不是本 session ⇒ 燒不到或不算 live）、無收據；
        - 存的選定讀回過 `load_card_pick`（**不可信**：封閉鍵、`valid_program_pick` 以草稿動作驗）、建立者＝
          本回合身分且＝該卡建立者；
        - 草稿該欄位現值的名稱指紋＝存的指紋（使用者把名稱改成別的 ⇒ 不帶）；
        - 修正 2（verifier F1）：本回合意圖判斷呼叫有附 `record_rechoice`、且 AI **恰回** `same`（這句沒有要改用
          另一筆）。`other`、缺、型別或值不合、呼叫失敗或解析不出、沒附欄位 ⇒ 不帶（依草稿名稱重新解析 ⇒
          重列候選）。前提都成立時記 `write_candidate_carry:same`／`:declined`（⛔ 記編號）。"""
        wd = acc.write_draft
        draft = wd.draft if wd is not None else None
        if not isinstance(draft, dict) or not wd.had_draft or wd.created:
            return None
        pid = wd.reissue_live_pid
        if not isinstance(pid, str) or not pid:
            return None
        rec = self._write_candidates_bound_card_pick(identity, agent_state, draft, pid=pid)
        if rec is None:
            return None
        if not (wd.rechoice_offered and wd.record_rechoice == WF.RECORD_RECHOICE_SAME):
            acc.violations.append(_wc.V_CANDIDATE_CARRY_DECLINED)
            return None
        acc.violations.append(_wc.V_CANDIDATE_CARRY_SAME)
        return _wc.program_pick_of(rec, rec["id"])

    def _write_candidates_bound_card_pick(
        self, identity: Identity, agent_state: dict, draft: dict, *, pid: Optional[str] = None,
    ) -> Optional[dict]:
        """修正 1／2 共用：本草稿目前綁定的那張卡（`pid` 有給時須同一張）無收據、存的選定讀回過
        `load_card_pick`（不可信）、建立者＝本回合身分且＝該卡建立者、草稿該欄位現值的名稱指紋＝存的指紋
        ⇒ 讀回的選定；其餘 ⇒ `None`。⛔ 查 DB、⛔ 寫任何狀態（純讀 `agent_state`）。"""
        action = draft.get("action")
        bound = self._write_draft_bound_card(identity, agent_state, action)
        if bound is None or (pid is not None and bound[0] != pid):
            return None
        entry = bound[1]
        if entry.get("receipt") is not None:
            return None
        rec = _wc.load_card_pick(entry.get(_wc.CARD_PICK_KEY), action=action)
        creator = _pending_creator(identity)
        if rec is None or rec["creator"] != creator or entry.get("creator") != creator:
            return None
        value = WF.to_payload(action, draft.get("fields") or {}).get(rec["field"])
        if not hmac.compare_digest(_wc.name_fp(value), rec["name_fp"]):
            return None
        return rec

    def _write_candidates_carry_open(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
    ) -> Optional[str]:
        """修正 2（verifier F1）：本回合意圖判斷呼叫要不要附 `record_rechoice`——修正 1 帶回選定的**回合開始時
        就判得出的**前提都成立：開關生效、回合開始就有草稿、非按鈕回合、沒有有效候選集（有則走打字選定）、
        綁定卡未作廢且 `_write_candidates_bound_card_pick` 成立 ⇒ 該選定的候選型別（規則句名詞用）；其餘 ⇒
        `None`（系統句與 schema 與修正前逐字相同）。「本回合燒成功且燒前 live」要到觸發點才知道，仍由
        `_write_candidates_card_pick` 判；這裡多附一次欄位最多是不帶，⛔ 放寬帶回條件。"""
        if not self._write_candidates_active():
            return None
        wd = acc.write_draft
        draft = wd.draft if wd is not None else None
        if not isinstance(draft, dict) or not wd.had_draft or wd.pick_button:
            return None
        if wd.candidates is not None:
            return None
        bound = self._write_draft_bound_card(identity, agent_state, draft.get("action"))
        if bound is None or bound[1].get("invalidated") is True:
            return None
        rec = self._write_candidates_bound_card_pick(identity, agent_state, draft, pid=bound[0])
        if rec is None or WF.record_rechoice_rule(rec["type"]) is None:
            return None
        return rec["type"]

    def _write_candidates_card_pick_record(
        self, acc: TurnAccumulator, identity: Optional[Identity], pick: Any,
    ) -> Optional[dict]:
        """修正 1：出卡當下由 `program_pick` 出的卡要存進待確認筆的選定（`{action, field, type, id, name_fp,
        creator}`）；`name_fp`＝本回合草稿該欄位的名稱值指紋（與候選集同一把，⛔ 取 `confirm.request` 改寫過的
        payload）。開關未生效、沒帶 `program_pick`、組不出合法形狀 ⇒ `None`（不存）。"""
        if pick is None or identity is None or not self._write_candidates_active():
            return None
        wd = acc.write_draft
        draft = wd.draft if wd is not None else None
        if not isinstance(draft, dict) or not isinstance(pick, dict):
            return None
        value = WF.to_payload(draft["action"], draft.get("fields") or {}).get(pick.get("field"))
        return _wc.card_pick_of(pick, name_fp=_wc.name_fp(value), creator=_pending_creator(identity))

    def _write_candidate_button_turn(self, acc: TurnAccumulator) -> bool:
        """本回合是 `pick:` 按鈕選定成立的回合（⛔ 呼叫主模型）。"""
        wd = acc.write_draft
        return bool(wd is not None and wd.pick_button and self._write_candidates_active())

    def _write_candidate_pick_begin(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
        pick_value: tuple, document: Any,
    ) -> Optional[TurnResult]:
        """`pick:<型別>:<編號>` 機器值（已 `fullmatch`）的判定，
        呼叫點在 `_write_draft_begin`（草稿讀回、建立者比對、點選範圍清草稿、候選集讀回與綁定檢查）之後。

        成立條件（全部）：候選集存在且形狀合法、建立者＝本回合身分、`(型別, 欄位, 編號)` 與候選集吻合
        （型別不符即不成立）、草稿存在且動作＝候選集動作、`entry == "mcp"`、非影子回合、非文件回合與文件
        暫存回合、非點選範圍回合、看得到該寫入動作。
        - 不成立 ⇒ 失效固定句結束回合：⛔ 任何 JGB 查詢、⛔ 動草稿、⛔ 動 token、⛔ 呼叫模型；
        - 成立 ⇒ 候選集寫 `picked`（選定編號**只存在候選集**，⛔ 寫進草稿），回 `None`：本回合由程式依
          草稿觸發 `confirm.request`（`program_pick`），⛔ 呼叫主模型與意圖判斷呼叫。
        dialog 的使用者端只寫程式摘要（P4-1；⛔ `pick:` 原值）。"""
        cand_type, pick_id = pick_value
        wd = acc.write_draft
        cands = wd.candidates if wd is not None else None
        draft = wd.draft if wd is not None else None
        ok = (
            cands is not None
            and isinstance(draft, dict) and draft.get("action") == cands.get("action")
            and cands.get("creator") == _pending_creator(identity)
            and cand_type == cands.get("type")
            and _wc.allowed(cands.get("action"), cands.get("field"), cand_type)
            and str(pick_id).strip() in cands.get("ids", [])
            and getattr(identity, "entry", None) == "mcp"
            and not self.readonly_view
            and document is None
            and _document_carry_of(agent_state) is None
            and agent_state.get(SELECT_SCOPE_KEY) is None
            and self._write_draft_visible(identity, cands.get("action"))
        )
        if not ok:
            acc.violations.append(_wc.V_CANDIDATE_PICK_INVALID)
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=_wc.CANDIDATE_PICK_DIALOG_USER,
                trace_id=acc.trace_id, start=acc.start, kind="ask",
                answer=_wc.CANDIDATE_PICK_INVALID_TEXT, pending_id=None,
                tool_calls=acc.tool_call_records, violations=acc.violations,
                llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
                completion_tokens=acc.completion_tokens,
                outcome=make_outcome("clarifying", expects="text"),
            )
        if _wc.is_withdrawn(cands):
            # F12 r6（§11.4 第 2 點）：已撤回的候選集按舊按鈕 ⇒ 重新選定（拿掉已撤回標記）。
            cands = _wc.repick(cands, str(pick_id).strip()) or cands
        else:
            cands = dict(cands, picked=str(pick_id).strip())
        AgentSession(agent_state).write_write_candidates(cands)
        wd.candidates = cands
        wd.picked = True
        wd.pick_button = True
        wd.activity = True
        wd.intent_consumed = True          # 按鈕回合不建意圖判斷呼叫
        acc.violations.append(_wc.V_CANDIDATE_PICK_BUTTON)
        return None

    async def _name_lenient_pick_rewrite(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
    ) -> None:
        """F12（主會話裁 §5.1 (A)）：**寬鬆來源**的候選集（`_wc.is_lenient`）本回合選定成立（按鈕或打字甲′，
        選定編號在候選集 `ids` 內）、仍綁定本草稿 ⇒ 由程式把草稿該名稱欄改寫成那一列在本身分清單上的系統
        名稱（`name_lenient_picked_title`；⛔ 模型或使用者給的值），並把候選集的名稱指紋同步成新值。兩段式流程的
        第二段（S-F2 `_pr_fill_bill_display`、`_estate_of_contract`，檢查邏輯 ⛔ 改動）因此以系統名稱比對。

        F12 r6（§11.4 第 3 點）：寬鬆標記保留到出卡（改選另一筆時名稱跟著改寫成新那筆的正名）；第一次改寫時另記
        已改寫鍵與原講法（改寫前草稿該欄值的正規化字串＝列候選時的值，綁定保證指紋相同；(乙) ⇒ 空字串）。

        - 程式改寫 ⛔ 算使用者講的：不進 `touched`；「選對紀錄」比對錨點同步成新值（客人講過的金額／期間不因此被清）；
        - 任一條件不合、清單沒查成、沒有這一筆、名稱過不了值閘（清洗後不等於原值或超長）⇒ 不改寫（照現行，
          第二段名稱對不上 ⇒ 查無固定句，⛔ 出錯卡）；
        - trace 只記碼 `V_NAME_LENIENT_REWRITE`（⛔ 名稱、編號）。"""
        wd = acc.write_draft
        cands = wd.candidates if wd is not None else None
        draft = wd.draft if wd is not None else None
        if not _wc.is_lenient(cands) or not isinstance(draft, dict):
            return
        picked = cands.get("picked")
        if not isinstance(picked, str) or picked not in cands.get("ids", []):
            return
        if not self._write_candidates_bound(cands, identity, draft):
            return
        form = WF.FORMS.get(draft.get("action"))
        f = form.field(cands.get("field")) if form is not None else None
        if f is None or f.source != WF.SOURCE_USER_WORDS or f.kind != "text":
            return
        title = await name_lenient_picked_title(
            identity, action=cands["action"], field=cands["field"], cand_type=cands["type"],
            pick_id=picked)
        if not isinstance(title, str):
            return
        clean = sanitize_data_piece(title).strip()
        if not clean or clean != title or len(clean) > WF.value_max_len(f):
            return
        new_fields = dict(draft.get("fields") or {})
        new_fields[f.key] = clean
        new_value = WF.to_payload(draft["action"], new_fields).get(cands["field"])
        if new_value != clean:
            return
        rewritten = dict(cands)
        rewritten["name_fp"] = _wc.name_fp(new_value)
        if not _wc.is_rewritten(cands):
            before = WF.to_payload(draft["action"], draft.get("fields") or {}).get(cands["field"])
            origin = _name_said_key(before) if isinstance(before, str) else ""
            if len(origin) > WF.value_max_len(f):
                origin = ""                  # 正規化後超長（NFKC 展開）⇒ 只套正名那一條（§11.4 第 4 點）
            rewritten[_wc.REWRITTEN_KEY] = True
            rewritten[_wc.ORIGIN_KEY] = origin
            rewritten[_wc.ORIGIN_FP_KEY] = _wc.name_fp(origin)
        loaded, _invalid = _wc.load_write_candidates(rewritten)
        if loaded is None:
            return
        wd.rewrite_title = (picked, clean)
        draft["fields"][f.key] = clean
        if wd.pr_anchor is not None:
            fields = draft["fields"]
            wd.pr_anchor = (fields.get("estate_name"), fields.get("period"))
        session = AgentSession(agent_state)
        session.write_write_candidates(loaded)
        wd.candidates = loaded
        self._write_draft_persist(acc, agent_state)
        acc.violations.append(_wc.V_NAME_LENIENT_REWRITE)

    def _write_candidates_post_pick(self, acc: TurnAccumulator, identity: Identity) -> Optional[dict]:
        """F12 r6：本回合的候選集已選定或已撤回、仍綁定本草稿（建立者、動作、名稱指紋）⇒ 該候選集；其餘
        （開關未生效、沒有候選集、未選定且未撤回、解綁）⇒ `None`。純讀（⛔ 查 DB、⛔ 寫狀態）。"""
        if not self._write_candidates_active():
            return None
        wd = acc.write_draft
        cands = wd.candidates if wd is not None else None
        if cands is None or (cands.get("picked") is None and not _wc.is_withdrawn(cands)):
            return None
        if not self._write_candidates_bound(cands, identity, wd.draft):
            return None
        return cands

    @staticmethod
    def _write_candidates_origin(cands: dict, draft: dict) -> str:
        """F12 r6（§11.4 第 4 點）：候選集的原講法（正規化字串）。寬鬆且已改寫 ⇒ 候選集存的那一份；其餘（名稱未被
        程式改寫）⇒ 草稿該欄現值的正規化（呼叫端已確認綁定 ⇒ 指紋＝列候選時的值）。"""
        if _wc.is_rewritten(cands):
            return cands.get(_wc.ORIGIN_KEY) or ""
        value = WF.to_payload(draft["action"], draft.get("fields") or {}).get(cands.get("field"))
        return _name_said_key(value) if isinstance(value, str) else ""

    def _write_candidates_name_rule(
        self, acc: TurnAccumulator, identity: Identity, f: Any, raw: Any, *, defer: bool,
    ) -> Optional[str]:
        """F12 r6（§11.4 第 2 點「判定順序」、第 4 點；r6-2 (a)）：候選集已選定或已撤回、仍綁定時，合併（意圖呼叫、
        模型提議）要寫進候選集那一欄 `f` 的名稱值 `raw` 怎麼處理。回：

        - `None`：規則不適用（不是候選集那一欄、值不是非空字串、未選定且未撤回、解綁、開關未生效）⇒ 照現行合併；
        - `"defer"`：（只在 `defer=True`、意圖結果還沒取用時）模型提議的名稱值暫存不併，留到拿到 `pick_id` 之後；
        - `"drop"`：丟棄（記 `write_candidate_name_kept`）——本回合已改選；回合開始已選定、仍綁定（`wd.cmd_scope_start`，
          選定後回合改指令式 §4.3「名稱值一律規則」：所有來源的名稱值一律丟棄，只有指令路徑驗過的 `name` 指令例外）；
          `pick_id` 等於現選定；值是**候選集內
          講法**（`_name_said_key` 正規化後等於或被包含於原講法，或被包含於本回合帶身分取得的任一列系統正名；
          ⛔ 把「包含原講法」的較長名稱算進來）；其餘且值不出自本回合原話（模型從上下文填回的舊講法）；
        - `"same"`：同 `"drop"` 的判定、但值與草稿現值相同 ⇒ 照現行合併（值不變、仍綁定）並記 `write_candidate_name_kept`；
        - `"new"`：候選集外、出自本回合原話（`_name_said_in_message`）⇒ 照現行合併（解綁 ⇒ 依新名稱重查），
          合併成功後記 `write_candidate_name_new`；
        - `"collect"`（第 5 輪 §11.15.3 第 6 點；`wd.name_collect` 期間）：收集、⛔ 合併，由
          `_write_candidates_post_pick_names` 算出改選目標 X 之後決定去向；本回合已判矛盾（`wd.name_conflict`）⇒ `"drop"`。
        `wd.repick_target`（第 5 輪起＝驗過且**未被退回**的改選目標 X）有值 ⇒ 丟棄（同值 ⇒ `"same"`）。
        ⛔ 讀任何原話位置標記（FR-15）。"""
        cands = self._write_candidates_post_pick(acc, identity)
        if cands is None:
            return None
        wd = acc.write_draft
        draft = wd.draft
        form = WF.FORMS.get(draft.get("action"))
        cf = form.field(cands.get("field")) if form is not None else None
        if cf is None or getattr(f, "key", None) != cf.key:
            return None
        if not isinstance(raw, str) or not raw.strip():
            return None
        if defer and not wd.intent_consumed:
            return "defer"
        if wd.cmd_scope_start:
            # 選定後回合改指令式（名稱值一律規則）：回合開始已選定、本草稿仍綁定（上方 `_write_candidates_post_pick`
            # 已確認）⇒ 意圖結果的名稱欄、主模型提議（取用前暫存的與取用後的）、被擋下動作的名稱一律丟棄（與草稿現值相同
            # 者回 `"same"`，照現行合併、值不變）。不看 `rechoice`／`pick_id`／改選目標（fail-closed：意圖解析失敗、
            # 沒設 `cmd_offered`、換動作合併被拒的回合同樣適用）；只有 `_write_candidates_cmd_turn` 驗過的 `name` 指令
            # 經 `_write_candidates_apply_name` 寫進候選集那一欄。
            return "same" if raw.strip() == (draft.get("fields") or {}).get(cf.key) else "drop"
        if wd.name_conflict:
            # 第 5 輪 §11.15.3 第 6 點決定 2：本回合已判矛盾 ⇒ 名稱值一律丟棄（含同值；⛔ 解綁）。
            return "drop"
        if wd.name_collect:
            # 第 5 輪 §11.15.3 第 6 點：先收集、等算出驗過且未被退回的改選目標再決定去向。
            return "collect"
        same = raw.strip() == (draft.get("fields") or {}).get(cf.key)
        kept = "same" if same else "drop"
        if wd.repick_target is not None:
            return kept
        return "new" if self._write_candidates_name_is_new(wd, cands, raw) else kept

    def _write_candidates_name_is_new(self, wd: Any, cands: dict, raw: Any) -> bool:
        """F12 r6（§11.4 第 4 點）：名稱欄值 `raw`（意圖結果或主模型提議）算不算「改講新名稱」——
        `pick_id` 等於現選定 ⇒ 否；候選集內講法 ⇒ 否；其餘出自本回合原話（`_name_said_in_message`）⇒ 是。
        ⛔ 看改選目標（呼叫端另判）。回合開始已選定的回合（`wd.cmd_scope_start`）不會到這裡——名稱值一律規則
        （`_write_candidates_name_rule`）已先丟棄；這裡的第二支留給「回合開始未選定、回合中依 `pick_id` 選定、同回合再走
        提議合併」（C-2 未選定回合不變）與已撤回回合。"""
        picked = cands.get("picked")
        if picked is not None and wd.intent_pick_id == picked and picked in wd.pick_offered:
            return False
        if self._write_candidates_in_set(wd, cands, raw):
            return False
        return _name_said_in_message(raw, wd.user_message)

    def _write_candidates_name_hits(self, wd: Any, cands: dict, raw: Any) -> tuple:
        """名稱值 `raw` 對到哪裡（`_name_said_key` 正規化）：回 `(原講法命中, 對到的列編號)`——原講法命中＝正規化後等於或被包含於
        原講法（`_write_candidates_origin`）；對到的列編號＝本回合帶身分取得的列（`offered_rows`）裡系統正名包含它的那幾列
        （候選編號，依 `offered_rows` 順序）。正規化後為空 ⇒ `(True, [])`（算候選集內講法）。⛔ 把「包含原講法」的較長名稱算進來。
        `_write_candidates_in_set`（名稱合併）與 `_write_candidates_cmd_effect`（`name` 指令）共用這一支（⛔ 兩套各寫）。"""
        key = _name_said_key(raw) if isinstance(raw, str) else ""
        if not key:
            return True, []
        origin = self._write_candidates_origin(cands, wd.draft)
        origin_hit = bool(origin and (key == origin or key in origin))
        matched = []
        for cid, row in wd.offered_rows.items():
            title = row.get("title") if isinstance(row, dict) else None
            title_key = _name_said_key(title) if isinstance(title, str) else ""
            if title_key and key in title_key:
                matched.append(cid)
        return origin_hit, matched

    def _write_candidates_in_set(self, wd: Any, cands: dict, raw: Any) -> bool:
        """F12 r6（§11.4 第 4 點）：名稱值 `raw` 是不是**候選集內講法**——`_name_said_key` 正規化後為空、等於或被包含
        於原講法，或被包含於本回合帶身分取得的任一列系統正名（⛔ 把「包含原講法」的較長名稱算進來；判法見
        `_write_candidates_name_hits`）。第 5 輪 §11.15.3 第 2 點的 `new_name` 與名稱合併共用這一支（⛔ 兩套各寫）。"""
        origin_hit, matched = self._write_candidates_name_hits(wd, cands, raw)
        return origin_hit or bool(matched)

    @staticmethod
    def _write_candidates_name_mark(acc: TurnAccumulator, rule: Optional[str]) -> None:
        """名稱合併規則的 trace 標記（只記碼；同一回合同一碼只記一次）。"""
        mark = (_wc.V_CANDIDATE_NAME_NEW if rule == "new"
                else _wc.V_CANDIDATE_NAME_KEPT if rule in ("drop", "same") else None)
        if mark is not None and mark not in acc.violations:
            acc.violations.append(mark)

    def _write_candidates_repick_target(self, acc: TurnAccumulator, identity: Identity,
                                        user_message: Any) -> None:
        """F12 r6（§11.4 第 2 點「判定順序」；N-1）：意圖結果取用之後、名稱欄合併之前，算出本回合程式驗證過的改選
        目標——`pick_id` ∈ 本回合附上的編號 ∩ `ids`，或整句只打 `ids` 內的編號；等於現選定 ⇒ 沒有目標。只供名稱
        合併規則判「本回合已改選」；改選成立與否仍由 `_write_candidates_typed` 決定。"""
        wd = acc.write_draft
        wd.repick_target = None
        cands = self._write_candidates_post_pick(acc, identity)
        if cands is None:
            return
        target = self._write_candidates_typed_target(wd, cands, user_message, changed=False)
        if target is not None and target != cands.get("picked"):
            wd.repick_target = target

    @staticmethod
    def _write_candidates_typed_target(wd: Any, cands: dict, user_message: Any, *,
                                       changed: bool) -> Optional[str]:
        """選定後（或已撤回）打字回合的程式驗證目標：`pick_id` ∈ 本回合附上的編號 ∩ `ids` ⇒ 它；否則草稿值沒變、
        整句只打編號（NFKC 後純 ASCII 數字）且在 `ids` 內 ⇒ 它；其餘 ⇒ `None`。⛔ `pick_matches_name`（R6-S1：
        選定後整句打候選集外編號 ⇒ 不動）。
        選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.3）：已選定的回合 ⛔ 讀 `pick_id`（該回合的 schema
        沒有它，`pick_id` 只在 `picked is None` 時算）；只剩整句只打編號的分支（`changed=False` 且在 `ids` 內）。
        已撤回（`picked` 為 None）照舊。"""
        pid = wd.intent_pick_id
        picked = cands.get("picked")
        if picked is None and isinstance(pid, str) and pid in wd.pick_offered and pid in cands["ids"]:
            return pid
        if changed:
            return None
        said = unicodedata.normalize("NFKC", user_message if isinstance(user_message, str) else "").strip()
        if said.isascii() and said.isdigit() and _wc.candidate_id(said) == said and said in cands["ids"]:
            return said
        return None

    def _write_candidates_pick_open(self, acc: TurnAccumulator) -> Optional[tuple]:
        """打字選定要附候選段的回合：開關生效、候選集有效、草稿動作相同、非按鈕回合 ⇒
        `(候選集, 回合開始時的草稿 payload)`（同步取快照，⛔ 在並行的 task 內讀會變動的草稿）；其餘 ⇒ `None`。
        F12 r6（§11.4 第 1 點）：選定後與已撤回（出卡前；出卡即清候選集）同樣附——客人改口才有理解管道。"""
        if not self._write_candidates_active():
            return None
        wd = acc.write_draft
        if wd is None or wd.candidates is None or wd.draft is None or wd.pick_button:
            return None
        cands = wd.candidates
        if wd.draft.get("action") != cands.get("action"):
            return None
        return cands, WF.to_payload(wd.draft["action"], wd.draft.get("fields") or {})

    def _pick_right_rows_scope(self, acc: TurnAccumulator, identity: Identity) -> Optional[dict]:
        """F12 r6：取候選列用的物件範圍——「選對紀錄」片生效、候選集仍綁定 ⇒ `write_candidates.scope_rows_pick_of`
        （不看選定狀態；未選定時與 `_pick_right_scope_pick` 相同）；其餘 ⇒ `None`。"""
        if not self._pick_right_active():
            return None
        wd = acc.write_draft
        cands = wd.candidates if wd is not None else None
        if cands is None or not self._write_candidates_bound(cands, identity, wd.draft):
            return None
        return _wc.scope_rows_pick_of(cands)

    async def _write_candidates_fetch_rows(
        self, acc: TurnAccumulator, identity: Identity, cands: dict, payload: dict,
    ) -> Optional[list]:
        """候選集的列（帶 role 與 viewer 的查詢；呼叫端只留 `ids` 內的編號）——`pick_id` 資料段與已撤回重列同一套
        （§11.4 第 1 點、V7-3）：

        - 寬鬆且已改寫（`_wc.is_rewritten`）⇒ 一律以 `name_lenient_rows_for_ids` 依 `ids` 取列（草稿名稱已是選定
          那筆的正名，依名稱重查可能只剩同正名者）；
        - 其餘 ⇒ 出卡前解析同一組函式 `write_name_candidates`（帳單候選帶物件範圍）；回 `None`（例：寬鬆路徑的
          候選、其他欄位仍缺時列出的精確同名候選）⇒ `name_lenient_rows_for_ids` 依 `ids` 取列；
        - 型別或欄位對不上、取不到 ⇒ `None`。F12 off ⇒ `name_lenient_rows_for_ids` 不查（與改動前相同）。"""
        result = None
        if not _wc.is_rewritten(cands):
            scope = self._pick_right_rows_scope(acc, identity)
            result = (await write_name_candidates(identity, cands["action"], payload, scope_pick=scope)
                      if scope is not None else
                      await write_name_candidates(identity, cands["action"], payload))
        if result is None:
            # AI 打字選定照 DSP-110 甲′：寬鬆路徑列出的候選，名稱重查本來就查無 ⇒
            # 以同一支專用清單查詢取列、只留候選集內的編號（0 次模型呼叫；開關 off ⇒ 照現行 `None`）。
            if not self._name_lenient_active():
                return None
            nl_rows = await name_lenient_rows_for_ids(
                identity, action=cands["action"], field=cands["field"], cand_type=cands["type"],
                ids=cands["ids"])
            if not nl_rows:
                return None
            data = {CANDIDATE_TYPE_KEY: cands["type"], "field": cands["field"], "candidates": nl_rows}
        else:
            data = result.data
        if data.get(CANDIDATE_TYPE_KEY) != cands["type"] or data.get("field") != cands["field"]:
            return None
        return list(data.get("candidates") or [])

    @staticmethod
    def _write_candidates_shown_limit(pr_on: bool) -> int:
        """畫面列幾筆的上限 K（列候選與重列兩個出口、`nth` 指令換編號共用同一個式子；只算 K）。"""
        return _wc.candidates_shown_max() if pr_on else _wc.CANDIDATES_SHOWN_MAX

    async def _write_candidates_relist_rows(self, acc: TurnAccumulator, identity: Identity) -> list:
        """F12 r6（§11.4 第 2 點；V7-3）：已撤回重列的列——本回合 `pick_id` 資料段已取過 ⇒ 用同一份
        （`offered_rows`）；沒取過或沒取到 ⇒ 同一套 `_write_candidates_fetch_rows` 再取一次。只留 `ids` 內、
        本人查得到的列，依 `ids` 順序。"""
        wd = acc.write_draft
        cands = wd.candidates
        if wd.offered_rows:
            source = list(wd.offered_rows.values())
        else:
            payload = WF.to_payload(wd.draft["action"], wd.draft.get("fields") or {})
            source = await self._write_candidates_fetch_rows(acc, identity, cands, payload) or []
            rows, _ids = self._write_candidates_rows_in_ids(cands, source)
            wd.offered_rows = {_wc.candidate_id(r.get("id")): r for r in rows}
            if self._pick_right_active():
                wd.pick_rows = dict(wd.offered_rows)
        by_id = {cid: row for cid, row in wd.offered_rows.items() if cid in cands["ids"]}
        return [by_id[cid] for cid in cands["ids"] if cid in by_id]

    def _write_candidates_relist_exit(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
        rows: list, *, prefix: Optional[str] = None, trace: Optional[TurnTrace] = None,
    ) -> TurnResult:
        """F12 r6（§11.4 第 2、7a 點；r6-7 (a)）：已撤回 ⇒ 程式重列**同一份** `ids` 結束回合（列候選回合的按鈕與
        固定句；⛔ 出卡、⛔ 建 token、⛔ `confirm.request`、⛔ 重新解析名稱）。候選集逐位不動（仍已撤回，客人按
        按鈕或打字重新選定）。`rows` 為空（全都看不到了）⇒ 清掉候選集與草稿名稱欄、照現行追問名稱。
        前導句：寬鬆來源 ⇒ `NAME_LENIENT_MISSING_LEAD_TEXT`（⛔ 回顯原話、⛔「找不到完全相同」）；其餘 ⇒ 列候選
        同一句（只插筆數）。dialog 只寫程式摘要；trace 記 `write_candidates_shown:<型別>:<n>`。"""
        wd = acc.write_draft
        cands = wd.candidates
        cand_type = cands["type"]
        action = cands["action"]
        head = f"{prefix}\n\n" if prefix else ""
        common = dict(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens, trace=trace,
        )
        if not rows:
            AgentSession(agent_state).clear_write_candidates()
            wd.candidates = None
            form = WF.FORMS.get(action)
            f = form.field(cands["field"]) if form is not None else None
            label = (self._name_lenient_mark_not_found(acc, identity, agent_state, action, f.key, None)
                     if f is not None else None)
            ask = missing_labels_ask_text([label]) if isinstance(label, str) else None
            return self._finish_confirm_turn(
                kind="ask", outcome=make_outcome("clarifying", expects="text", action=action),
                answer=f"{head}{ask or WF.WRITE_NOT_ISSUED_TEXT}", pending_id=None,
                ask_target=(None if prefix else
                            (WF.ask_target_for_missing([label]) if isinstance(label, str) else None)),
                **common,
            )
        pr_on = self._pick_right_active()
        shown = rows[:self._write_candidates_shown_limit(pr_on)]
        total = len(rows)
        if _wc.is_lenient(cands):
            lead = NAME_LENIENT_MISSING_LEAD_TEXT
        else:
            lead = _wc.candidates_lead_text(cand_type, total, cands["has_more"])
        text = lead + "\n" + _wc.user_list_text(cand_type, shown)
        if pr_on and _wc.pr_indistinct_ids(cand_type, shown):
            text += "\n" + _wc.PR_INDISTINCT_TEXT
        if cands["has_more"] or total > len(shown):
            text += "\n" + _wc.CANDIDATES_MORE_TEXT
        quick = [
            {"label": _wc.button_label(cand_type, row),
             "value": f"{_wc.PICK_VALUE_PREFIX}{cand_type}:{_wc.candidate_id(row.get('id'))}"}
            for row in shown
        ]
        acc.violations.append(_wc.shown_marker(cand_type, total))
        return self._finish_confirm_turn(
            kind="ask", outcome=make_outcome("clarifying", expects="choice", action=action),
            answer=f"{head}{text}", dialog_answer=f"{head}{_wc.dialog_summary(cand_type, len(shown))}",
            pending_id=None, quick_replies=quick, ask_target=None, **common,
        )

    def _write_candidates_repick_notice(self, acc: TurnAccumulator) -> Optional[str]:
        """F12 r6-3 (a)（§11.8 R6-S2）：本回合打字改選成立、還沒出卡 ⇒ 告知固定句「已改成：{title}（編號 {id}）。」。
        名稱只取本身分清單上新那筆的系統列（本回合帶身分取得的列 `offered_rows`，或寬鬆改寫取得的
        `name_lenient_picked_title`），過 `sanitize_data_piece` 且等值、不超過名稱欄上限；⛔ 取草稿、使用者或
        模型值。取不到 ⇒ `None`（不加句）。"""
        wd = acc.write_draft
        rid = wd.repick_id if wd is not None else None
        if not isinstance(rid, str) or _wc.candidate_id(rid) != rid:
            return None
        title = None
        row = wd.offered_rows.get(rid)
        if isinstance(row, dict) and isinstance(row.get("title"), str):
            title = row["title"]
        elif isinstance(wd.rewrite_title, tuple) and wd.rewrite_title[0] == rid:
            title = wd.rewrite_title[1]
        cands = wd.candidates
        form = WF.FORMS.get(cands.get("action")) if isinstance(cands, dict) else None
        f = form.field(cands.get("field")) if form is not None else None
        if not isinstance(title, str) or f is None:
            return None
        clean = sanitize_data_piece(title).strip()
        if not clean or clean != title or len(clean) > WF.value_max_len(f):
            return None
        return _wc.CANDIDATE_REPICK_TEXT.format(title=clean, id=rid)

    async def _write_candidates_intent_kwargs(
        self, acc: TurnAccumulator, identity: Identity, pick_open: tuple, kwargs: dict, *,
        enum_labels: bool, fill_kw: Optional[dict] = None,
    ) -> Optional[dict]:
        """意圖判斷呼叫的候選段與動態 enum。列以出卡前解析同一組函式、
        帶 viewer 重查（`write_name_candidates`），只留候選集內的編號（⛔ 讓重查多出來的列進 enum）；
        型別或欄位對不上、取不到 ⇒ `None`（照現行呼叫）。資料段排在使用者這句之前（使用者這句仍是最後
        一則）；系統句接 `PICK_ID_RULE`。

        F12 r6（§11.4 第 1 點）：已選定或已撤回時同樣附（取列見 `_write_candidates_fetch_rows`）。
        選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.2）：**已選定**的回合系統句＝
        `write_intent_system_prompt(enum_labels)`（不帶 `pick_rule`）＋「\\n」＋指令規則句（`{picked}`＝`_wc.candidate_id`
        驗過形狀的 `cands["picked"]`，程式值）、schema＝`write_intent_call_schema` 加必填 `target`（不帶 `pick_id`、
        `rechoice`、`new_name`），並設 `wd.cmd_offered`；現選定編號形狀不合（讀回已驗，理應不發生）⇒ `None`（不附候選段，
        fail-closed：⛔ 讀 `target`）。未選定、已撤回 ⇒ 系統句與 schema 與改動前逐字相同（C-2、Q1 (a)）。
        填欄只填答覆（§4.1 A.3）：兩支系統句與 schema 一律接 `fill_kw`（`_fill_begin_intent_call` 的同一份；off ⇒ 空）。"""
        fill_kw = fill_kw or {}
        cands, payload = pick_open
        picked = cands.get("picked")
        picked_id: Optional[str] = None
        if picked is not None:
            picked_id = _wc.candidate_id(picked)
            if picked_id is None or picked_id != picked or WF.pick_target_rule(picked_id) is None:
                return None
        source = await self._write_candidates_fetch_rows(acc, identity, cands, payload)
        if source is None:
            return None
        rows, offered = self._write_candidates_rows_in_ids(cands, source)
        if not offered:
            return None
        messages = list(kwargs["messages"])
        if picked_id is not None:
            system = WF.write_intent_system_prompt(enum_labels=enum_labels, target_picked=picked_id, **fill_kw)
            response_format = WF.write_intent_response_format(
                enum_labels=enum_labels, target_picked=picked_id, **fill_kw)
        else:
            system = WF.write_intent_system_prompt(enum_labels=enum_labels, pick_rule=True, **fill_kw)
            response_format = WF.write_intent_response_format(
                enum_labels=enum_labels, pick_ids=offered, **fill_kw)
        messages[0] = {"role": "system", "content": system}
        messages.insert(len(messages) - 1, {
            "role": "user",
            "content": wrap_tool_data(WRITE_CANDIDATES_DATA_LABEL,
                                      _wc.data_piece_text(cands["type"], rows), acc.nonce),
        })
        acc.write_draft.pick_offered = tuple(offered)
        acc.write_draft.cmd_offered = picked_id is not None
        acc.write_draft.offered_rows = {
            _wc.candidate_id(r.get("id")): r for r in rows if isinstance(r, dict)}
        if self._pick_right_active():
            acc.write_draft.pick_rows = {
                _wc.candidate_id(r.get("id")): r for r in rows if isinstance(r, dict)}
        return dict(kwargs, messages=messages, response_format=response_format)

    @staticmethod
    def _write_candidates_rows_in_ids(cands: dict, source: list) -> tuple:
        """只留候選集 `ids` 內、不重複的列（依 `source` 順序）⇒ `(列, 編號)`。⛔ 讓重查多出來的列進來。"""
        allowed_ids = set(cands["ids"])
        rows: list = []
        offered: list = []
        for row in source:
            cid = _wc.candidate_id(row.get("id")) if isinstance(row, dict) else None
            if cid is not None and cid in allowed_ids and cid not in offered:
                offered.append(cid)
                rows.append(row)
        return rows, offered

    async def _write_candidates_typed(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str, *,
        fields_before: Optional[dict],
    ) -> None:
        """打字選定的判定（意圖判斷結果合併之後、觸發條件
        之前；每回合一次）。AI 只回「指哪一筆」（`pick_id`），成立與否由程式決定：

        - 候選集不再綁定本草稿（換動作、草稿被清、該欄位改成別的名稱）⇒ 作廢（新名稱由程式依草稿照常
          重新解析）；已選定或已撤回 ⇒ 見 `_write_candidates_typed_post_pick`（F12 r6）；
        - `pick_id` 屬於本回合實際附上的候選編號 ⇒ 選定成立；
        - 使用者這句整句是編號（NFKC 後純 ASCII 數字）、且本回合草稿值沒變：在候選集內 ⇒ 成立；不在 ⇒
          帶 viewer 的編號精確查、名稱相同才成立（`pick_matches_name`）；
        - 其餘、非問句、且草稿值沒變 ⇒ 重列同一份候選（`reask`，程式依草稿重發）。問句回合交 AI 作答，
          狀態行由 B2 列候選（乙′）。⛔ 猜、⛔ 挑第一筆、⛔ 程式解析日期詞或序數。"""
        wd = acc.write_draft
        cands = wd.candidates
        session = AgentSession(agent_state)
        if not self._write_candidates_bound(cands, identity, wd.draft):
            session.clear_write_candidates()
            wd.candidates = None
            return
        changed = (wd.draft.get("fields") or {}) != (fields_before or {})
        if cands.get("picked") is not None or _wc.is_withdrawn(cands):
            self._write_candidates_typed_post_pick(
                acc, agent_state, cands, user_message, changed=changed)
            return
        chosen: Optional[str] = None
        pid = wd.intent_pick_id
        if (isinstance(pid, str) and pid != WF.PICK_ID_NONE
                and pid in wd.pick_offered and pid in cands["ids"]):
            chosen = pid
        elif not changed:
            said = unicodedata.normalize("NFKC", user_message if isinstance(user_message, str) else "")
            said = said.strip()
            if said.isascii() and said.isdigit() and _wc.candidate_id(said) == said:
                if said in cands["ids"]:
                    chosen = said
                elif await pick_matches_name(
                        identity, action=cands["action"], field=cands["field"],
                        cand_type=cands["type"], pick_id=said,
                        field_value=self._write_candidates_field_value(
                            acc, {"field": cands["field"]})):
                    chosen = said
        if (chosen is not None and chosen == pid and self._pick_right_active()
                and chosen in _wc.pr_indistinct_ids(cands["type"], wd.pick_rows.values())
                and not _said_id_is_pick_id(user_message, cands["ids"], pid)):
            # PR-2／PR-7：AI 依客人描述回的那筆，畫面上與另一筆除編號外全同 ⇒ 客人的話分不出是哪筆，
            # ⛔ 收 AI 的猜測；重列（清單後印分不出句）。客人整句打編號或按按鈕照常成立。
            # F12 r6 §11.14 第 1 點：客人句中講出的編號（恰一段屬於 `ids` 且等於 `pick_id`）⇒ 不算 AI 猜測、不退回
            # （只免除本條；金額期間不符照舊套用）。
            acc.violations.append(_wc.V_PICK_RIGHT_INDISTINCT)
            wd.reask = True
            wd.activity = True
            acc.violations.append(_wc.V_CANDIDATE_REASK)
            return
        mismatch = (self._pick_right_typed_mismatch(acc, cands, chosen)
                    if chosen is not None else None)
        if mismatch is not None:
            # 「選對紀錄」片 §4.2-3（業主裁 Q4）：打字選定的帳單與客人先前講的金額／計費期間不符 ⇒ 不收，
            # 重列候選（按鈕選定才照按的出卡並在卡上提醒）。標記只記碼（S-F11）。
            for mark in mismatch:
                if mark not in acc.violations:
                    acc.violations.append(mark)
            wd.reask = True
            wd.activity = True
            acc.violations.append(_wc.V_CANDIDATE_REASK)
            return
        if chosen is not None:
            cands = dict(cands, picked=chosen)
            session.write_write_candidates(cands)
            wd.candidates = cands
            wd.picked = True
            wd.activity = True
            acc.violations.append(_wc.V_CANDIDATE_PICK_TYPED)
            return
        if not changed and not _is_question(user_message):
            wd.reask = True
            wd.activity = True
            acc.violations.append(_wc.V_CANDIDATE_REASK)

    def _write_candidates_typed_post_pick(
        self, acc: TurnAccumulator, agent_state: dict, cands: dict, user_message: Any, *,
        changed: bool,
    ) -> None:
        """F12 r6（§11.4 第 2、7a 點；r6-1 (a) 套用所有寫入候選集；r6-7 (a)）：候選集已選定或已撤回、仍綁定時的
        打字回合，由 `_write_candidates_typed` 進入。已撤回回合（AI 只回 `pick_id`）與已選定回合的**沒走指令路徑**
        的情形（意圖解析失敗、換動作合併被拒；計畫 `plan-post-pick-commands-20261024.md` §4.3 第 7 點）走這裡；已選定且
        `cmd_offered`、意圖解析成功、沒換動作的回合由 `_write_candidates_cmd_turn` 接手（⛔ 進本函式）。改不改選由程式
        決定（DSP-091）：

        - 程式驗證過的目標（`_write_candidates_typed_target`：已撤回 ⇒ `pick_id` ∈ 本回合附上的編號 ∩ `ids`；已選定 ⇒
          只剩整句只打 `ids` 內編號且草稿值沒變；⛔ `pick_matches_name`）且 ≠ 現選定 ⇒ 改選（已撤回 ⇒ 重新選定），記
          `write_candidate_repick:typed`；選對紀錄的分不出、金額期間不符照未選定時同一套規則套在目標上（分不出另免除
          客人句中講出的編號，§11.14 第 1 點），被退回 ⇒ 清掉選定、進入已撤回（⛔ 留著舊選定），重列同一份 `ids`
          （`_write_candidates_repick_apply`）；
        - 沒有目標，或目標等於現選定 ⇒ 不動（已選定：其他欄位的更正照常觸發、選定照帶；已撤回：非問句且草稿值沒變 ⇒
          重列，其餘交出卡入口的關口重列、問句由 B2 列候選）。
        撤回 ⛔ 動草稿名稱、⛔ 重新解析名稱（`_wc.withdraw` 保留 `ids`、寬鬆鍵、已改寫鍵）。"""
        wd = acc.write_draft
        picked = cands.get("picked")
        target = self._write_candidates_typed_target(wd, cands, user_message, changed=changed)
        if target is not None and target == picked:
            target = None
        if target is None:
            if picked is None and not changed and not _is_question(user_message):
                wd.relist = True
                wd.activity = True
            return
        self._write_candidates_repick_apply(acc, agent_state, cands, target, user_message)

    def _write_candidates_repick_apply(
        self, acc: TurnAccumulator, agent_state: dict, cands: dict, target: str, user_message: Any, *,
        via: Optional[str] = None,
    ) -> None:
        """改選目標 `target`（程式驗證過、≠ 現選定）的執行：先過「選對紀錄」退回（`_write_candidates_refusal`，`via` 見
        該函式）——被退回 ⇒ 清掉選定、進入已撤回、重列同一份 `ids`（已撤回 ⇒ 只重列），記退回標記與
        `write_candidate_reask`；否則改選（`_wc.repick`），記 `write_candidate_repick:typed`。
        `_write_candidates_typed_post_pick`（已撤回、整句編號）與 `_write_candidates_cmd_turn`（`pick`／`nth`／整句編號）
        共用這一支（⛔ 兩套各寫）。"""
        wd = acc.write_draft
        session = AgentSession(agent_state)
        picked = cands.get("picked")
        refused = self._write_candidates_refusal(acc, cands, target, user_message, via=via)
        if refused is not None:
            # §11.8 N-2：改選目標被退回 ⇒ 清掉選定（⛔ 留著舊選定讓程式出舊那筆的卡），重列同一份 `ids`。
            for mark in refused:
                if mark not in acc.violations:
                    acc.violations.append(mark)
            acc.violations.append(_wc.V_CANDIDATE_REASK)
            if picked is not None:
                self._write_candidates_withdraw(acc, agent_state, cands)
            else:
                wd.relist = True
                wd.activity = True
            return
        repicked = _wc.repick(cands, target)
        if repicked is None:
            return
        session.write_write_candidates(repicked)
        wd.candidates = repicked
        wd.picked = True
        wd.activity = True
        wd.repick_id = target
        acc.violations.append(_wc.V_CANDIDATE_REPICK_TYPED)

    def _write_candidates_refusal(self, acc: TurnAccumulator, cands: dict, target: str,
                                  user_message: Any, *, via: Optional[str] = None) -> Optional[tuple]:
        """F12 r6（§11.8 N-2）：選定後（或已撤回）改選目標 `target` 是否被「選對紀錄」退回——分不出（AI 依描述回的
        那筆與另一筆除編號外全同；客人句中講出的編號免除，§11.14 第 1 點）或金額期間不符 ⇒ 退回標記（tuple）；
        不退回 ⇒ `None`。純判定（⛔ 寫狀態、⛔ 記標記）。第 5 輪 §11.15.3 第 6 點在決定名稱去向**之前**呼叫（讀的是
        本回合非名稱欄合併後的比對值），`_write_candidates_typed_post_pick` 共用同一支（⛔ 兩套各寫）。

        `via`（選定後回合改指令式）：指令路徑傳指令種類——`"pick"`：分不出判定的「AI 的猜測」＝該
        `pick` 指令，客人句中講出該編號（`_said_id_is_pick_id`）才免除；`"nth"`：只在客人原話結構上含序數
        （`_said_has_ordinal`；NFKC 後「第」接數字或含「最後」，由程式判，只作佐證）時免除，否則同 `pick` 退回（擋 AI
        把依描述猜的包成序數）；`"name"`（修復輪 1 R1-1，名稱唯一對到一筆）：分不出判定不套；金額期間不符一律套用。不傳（`None`）⇒ 照現行讀 `wd.intent_pick_id`（已撤回回合；整句
        編號的目標 ≠ `pick_id` 不套分不出）。"""
        wd = acc.write_draft
        if via is None:
            pid = wd.intent_pick_id
            guessed = target == pid
            excused = guessed and _said_id_is_pick_id(user_message, cands["ids"], pid)
        elif via == WF.PICK_TARGET_OP_NAME:
            # 修復輪 1 R1-1：程式依客人原字的名稱唯一對到（不是 AI 依描述猜）⇒ 分不出判定不套；金額期間不符照套。
            guessed = False
            excused = False
        else:
            guessed = True
            excused = (_said_id_is_pick_id(user_message, cands["ids"], target) if via == WF.PICK_TARGET_OP_PICK
                       else _said_has_ordinal(user_message))
        if (guessed and self._pick_right_active()
                and target in _wc.pr_indistinct_ids(cands["type"], wd.pick_rows.values())
                and not excused):
            # §11.14 第 1 點：客人句中講出的編號（恰一段屬於 `ids` 且等於 `pick_id`）⇒ 不算 AI 猜測、不退回。
            return (_wc.V_PICK_RIGHT_INDISTINCT,)
        mismatch = self._pick_right_typed_mismatch(acc, cands, target)
        return tuple(mismatch) if mismatch is not None else None

    @staticmethod
    def _write_candidates_withdraw(acc: TurnAccumulator, agent_state: dict, cands: dict) -> None:
        """F12 r6：清掉選定、進入已撤回（`_wc.withdraw`：`ids`、名稱指紋、寬鬆鍵、已改寫鍵逐位保留；⛔ 動草稿），
        本回合由程式重列同一份 `ids`。組不出合法形狀 ⇒ 清掉候選集（fail-closed：⛔ 留著舊選定）。"""
        wd = acc.write_draft
        session = AgentSession(agent_state)
        withdrawn = _wc.withdraw(cands)
        if withdrawn is None:
            session.clear_write_candidates()
            wd.candidates = None
            return
        session.write_write_candidates(withdrawn)
        wd.candidates = withdrawn
        wd.relist = True
        wd.activity = True

    def _write_draft_name_catch_eligible(self, acc: TurnAccumulator) -> bool:
        """W1b §8.1-3 的執行條件（安全處置 2b／2d／5a 收窄後）：**回合開始即存在**的草稿、
        其動作表單有物件名稱欄位且尚缺、`asked` 為空或含 `estate_name`、本回合未凍結。
        （`asked` 恰為一個非名稱文字欄位時整句會填進那一欄 ⇒ 依 2b 已被第二個條件排除。）"""
        wd = acc.write_draft
        if wd is None or wd.draft is None or not wd.had_draft or wd.frozen:
            return False
        f = WF.FORMS[wd.draft["action"]].field("estate_name")
        if f is None or f.source != WF.SOURCE_USER_WORDS or f.kind != "text":
            return False
        if wd.draft["fields"].get(f.key):
            return False
        return not wd.asked or f.key in wd.asked

    def _write_draft_catch_name(
        self, acc: TurnAccumulator, agent_state: dict, name: Any, *, segment: Any = None,
    ) -> None:
        """W1b §8.1-3 物件名稱補值：本句前置查詢對到**唯一**物件 ⇒ 名稱（系統查得：列上有
        `title` 用 `title`，單筆命中只拿得到查詢關鍵字時用關鍵字，見 `_estate_carry_from_estates_data`；
        ⛔ 用模型輸出）寫進草稿的 `estate_name`。⛔ 寫進 `contract_ref`（前置查詢只查物件）。
        凍結判斷包住本呼叫（安全處置 5a：`_write_draft_name_catch_eligible` 對凍結回合回 False）。
        W1c §9.11-2：寫入的名稱與 `segment`（當句被判為物件名稱的那一段＝前置查詢關鍵字）記進回合內
        狀態，供意圖合併時「系統名稱優先、同一段原話不填兩欄」比對。"""
        if not self._write_draft_name_catch_eligible(acc):
            return
        wd = acc.write_draft
        target = WF.FORMS[wd.draft["action"]].field("estate_name")
        if not isinstance(name, str):
            return
        clean = sanitize_data_piece(name).strip()
        if not clean or len(clean) > WF.value_max_len(target):
            return
        wd.activity = True
        wd.caught = True
        wd.draft["idle_turns"] = 0
        wd.draft["fields"][target.key] = clean
        wd.touched.add(target.key)
        wd.caught_name = clean
        seg = sanitize_data_piece(segment).strip() if isinstance(segment, str) else ""
        wd.caught_segment = seg or None
        acc.violations.append(WF.V_NAME_CAUGHT)
        self._write_draft_persist(acc, agent_state)

    # -- 意圖判斷呼叫（W1b §8.1-1、§8.5-4、§8.6-3a／3b／3c）------------------
    def _start_write_intent_call(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
        user_message: str, document: Any,
    ) -> None:
        """建立本回合的意圖判斷呼叫 task（安全處置 3a：`run_program_segments` 未結束回合、
        `_build_turn_context` 之後才會走到這裡）。條件：草稿機制可跑（`acc.write_draft` 非
        `None`＝開關 on、非影子、非 `select:` 釘住範圍）、非文件回合、看得到任一 `jgb2.action.*`。

        同一個模型、同一個 client（`self.provider.async_client`）、輸入＝系統句＋本會話對話
        （`dialog`）＋當句（主呼叫輸入的子集，⛔ 資料段、⛔ 草稿注入行）；`max_completion_tokens`
        800；與主模型迴圈**並行**（這裡只建立，⛔ await）。"""
        if document is not None:
            return
        if self._closing_active():
            # E 片：每個使用者文字回合都另建只含 `dialog_act` 的標籤呼叫（同模型、同輸出上限、同 dialog 輸入、
            # 同建立時點、與主模型及寫入意圖呼叫並行）；寫入意圖呼叫 ⛔ 帶 `dialog_act`——合併在同一個呼叫裡誤判明顯較多。
            self._start_dialog_act_call(acc, agent_state, user_message)
        if acc.write_draft is None or not self._write_draft_any_visible(identity):
            return
        # 第 3 步 A4：開關 on ⇒ enum 欄位只列標籤（程式轉代碼）；off ⇒ 現行列代碼。
        enum_labels = bool(getattr(self, "_write_lifecycle_on", False))
        # A-2a 修正 2（verifier F1）：卡後可帶回選定的回合 ⇒ 系統句與 schema 多附 `record_rechoice`（AI 只回
        # same／other，帶不帶回由程式定）；其餘回合 `rechoice_type is None` ⇒ 兩者與修正前逐字相同。
        rechoice_type = self._write_candidates_carry_open(acc, identity, agent_state)
        if rechoice_type is not None:
            acc.write_draft.rechoice_offered = True
        # 填欄只填答覆（§4.1 A）：開關 on 的寫入回合 ⇒ 三個建構點（這裡＋`_write_candidates_intent_kwargs` 兩支）一律
        # 接同一段資料段規則與 schema（`fill_kw`）；追問回合另附追問欄位標籤與 `answer_text`。off ⇒ `fill_kw` 為空、
        # 系統句與 schema 與改前逐字相同。
        fill_kw = self._fill_begin_intent_call(acc)
        messages: list = [{"role": "system",
                           "content": WF.write_intent_system_prompt(
                               enum_labels=enum_labels, rechoice_type=rechoice_type, **fill_kw)}]
        for m in agent_state.get("dialog") or []:
            if (isinstance(m, dict) and m.get("role") in ("user", "assistant")
                    and isinstance(m.get("content"), str)):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_message if isinstance(user_message, str) else ""})
        kwargs: dict = dict(
            model=self._model,
            messages=messages,
            response_format=WF.write_intent_response_format(
                enum_labels=enum_labels, rechoice_type=rechoice_type, **fill_kw),
            max_completion_tokens=WF.WRITE_INTENT_MAX_COMPLETION_TOKENS,
        )
        if self._reasoning_effort is not None:
            kwargs["extra_body"] = {"reasoning_effort": self._reasoning_effort}
        create = self.provider.async_client.chat.completions.create
        # DSP-103：候選集有效且尚未選定的回合，意圖判斷呼叫多帶一段候選清單
        # 資料段（候選集全部 ≤20 列、每列只放投影欄、逐列過 `sanitize_data_piece`、nonce 包住，排在使用者
        # 這句之前）與 `pick_id` 欄位（動態 enum＝實際附上的編號＋`none`）。列由出卡前解析同一組函式、帶
        # viewer 重查（`write_name_candidates`），只留候選集內的編號；取不到 ⇒ 照現行呼叫（⛔ 附段）。
        pick_open = self._write_candidates_pick_open(acc)
        partial: list = []

        async def _call() -> Any:
            if pick_open is not None:
                picked_kwargs = await self._write_candidates_intent_kwargs(
                    acc, identity, pick_open, kwargs, enum_labels=enum_labels, fill_kw=fill_kw)
                if picked_kwargs is not None:
                    first = await create(**picked_kwargs)
                    if not _write_intent_needs_retry(first):
                        return first
                    # F12 r6 復原第 5 輪 §11.15.3 第 5 點（根因 S22）：附候選段的呼叫截斷或解析不出 ⇒ 同一份輸入重送
                    # 一次（同一個 task，等待上限仍是 `_await_write_intent` 那一個；逾時照現行）。仍失敗或重送丟例外
                    # ⇒ `failed`（照現行回 `None`）。未附候選段的呼叫 ⛔ 重送（與現行逐字相同）。
                    partial.append(first)
                    try:
                        second = await create(**picked_kwargs)
                    except Exception:  # noqa: BLE001 — 重送失敗 ⇒ 照第一次的失敗處理（`None`）
                        return _RetriedIntentResponse(first, None, failed=True)
                    return _RetriedIntentResponse(
                        first, second, failed=_write_intent_needs_retry(second))
            return await create(**kwargs)

        call = _WriteIntentCall(
            asyncio.create_task(_call()), model=self._model,
            input_chars=sum(len(m["content"]) for m in messages),
            registry=self._write_intent_calls, trace_id=acc.trace_id, partial=partial,
        )
        self._write_intent_calls[acc.trace_id] = call
        acc.write_intent_call = call

    # -- 填欄只填答覆（plan-fill-answer-only-20261027 §4.1）------------------------------------------
    # 分工（DSP-091）：哪部分是資料、哪部分回答追問欄位由 AI 在寫入意圖呼叫標出（`data_texts`／`answer_text`）；
    # 填不填、併不併、要不要重問由程式決定。⛔ 本節任何地方以道謝或寒暄的詞表判斷。
    def _fill_begin_intent_call(self, acc: TurnAccumulator) -> dict:
        """寫入意圖呼叫建立當下（§4.1 適用範圍）：開關 on 且本回合是**單欄追問回合** ⇒ 啟用本片（`fill_active`），
        記下回合開始那份草稿，回三個建構點共用的系統句／schema 參數 `{"data_text": True, "asked_labels": (標籤,)}`
        （表單欄位標籤，⛔ 使用者原話）。
        修復輪 3（業主 10-27 §6 第 10 點「縮小到追問回合」）：單欄追問回合＝送出之前依已知狀態判一次——回合開始即有
        草稿、`asked` 非空、非凍結、草稿非 `None`（現行 `fill_followup` 條件），**且** `asked` 恰好 1 個鍵、對得到表單
        欄位標籤。其餘寫入回合（第一句無草稿、確認卡出現後打字 `asked` 空、多欄追問 `asked` ≥2、其他非追問寫入回合）
        與開關 off ⇒ `{}`、⛔ 設 `fill_active`：系統句、schema、①～⑥ 值閘、整句填入、B5、B6 與 off 逐字相同。
        填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.1、§4.2）：首句、卡後、多欄三種回合另由
        `_fill_wide_begin` 判（`AGENT_FILL_DATA_TEXT_WIDE` on）⇒ 回 `{"data_text": True}`（⛔ `asked_labels`）、設 `fill_wide`；
        與單欄追問回合互斥。"""
        wd = acc.write_draft
        if not self._fill_data_text_on or wd is None:
            return {}
        if not (wd.had_draft and wd.asked and not wd.frozen and wd.draft is not None) or len(wd.asked) != 1:
            # §4.1 (b)、§11 r1c：候選回合＝`_start_write_intent_call` 走 `pick_rule=True` 那一支的同一組狀態。
            pick_open = self._write_candidates_pick_open(acc)
            wd.pick_list_open = pick_open is not None and pick_open[0].get("picked") is None
            return self._fill_wide_begin(wd)
        form = WF.FORMS.get(wd.draft.get("action"))
        key = wd.asked[0]
        f = form.field(key) if form is not None and isinstance(key, str) else None
        if f is None or not isinstance(f.label, str) or not f.label:
            return {}
        wd.fill_active = True
        wd.fill_start_draft = wd.draft
        wd.fill_start_fields = (dict(wd.draft.get("fields") or {}) if isinstance(wd.draft, dict) else {})
        wd.fill_followup = True
        wd.fill_asked_labels = (f.label,)
        return {"data_text": True, "asked_labels": (f.label,)}

    @staticmethod
    def _fill_followup_now(wd: Any) -> bool:
        """追問回合，且目前草稿就是回合開始那一份（B4、B5、`answer_text` 只在這時生效；§4.1 適用範圍）。"""
        return bool(wd is not None and wd.fill_active and wd.fill_followup
                    and wd.draft is not None and wd.draft is wd.fill_start_draft)

    @staticmethod
    def _fill_data_unknown(wd: Any) -> bool:
        """本回合資料段未知（B1）：沒讀到驗過的資料段，或模型提議比意圖結果先到。"""
        return wd.fill_data is None or wd.fill_proposal_first

    def _fill_value_not_applied(self, wd: Any) -> bool:
        """B2「本回合有值沒套用」：至少一個與草稿現值不同的新值沒套用——資料段未知而帶新值、資料段外拒收（含空陣列）、
        追問回合不覆寫已填欄。資料段未知但值全是同值重述 ⇒ `False`（狀態句與改前相同；主會話 10-27 裁待查 3）。
        off ⇒ `False`。
        填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.3 第 8 點）：寬回合卡後有值被資料段拒收、本回合最後仍
        沒套用 ⇒ 同樣 `True`（資料段未知時值照現行收，不設）。"""
        if wd is not None and wd.fill_active and wd.fill_not_applied:
            return True
        return bool(self._fill_wide_not_applied_labels(wd))

    @staticmethod
    def _fill_mark(acc: TurnAccumulator, mark: str) -> None:
        if mark not in acc.violations:
            acc.violations.append(mark)

    def _fill_reask_if_missing(self, acc: TurnAccumulator) -> None:
        """B6：追問回合、草稿仍是回合開始那份，追問的欄位（任一）本回合仍是空的 ⇒ 設 `fill_reask`（觸發條件；程式依
        草稿回缺欄追問，與 E 片「逾時就重問缺欄」同一出口）。非追問回合、開關 off ⇒ 不動（與改前相同）。"""
        wd = acc.write_draft
        if not self._fill_followup_now(wd):
            return
        fields = wd.draft.get("fields") or {}
        if any(fields.get(key) in (None, "") for key in wd.asked):
            wd.fill_reask = True
            wd.activity = True
            self._fill_mark(acc, WF.V_FILL_REASK)

    @staticmethod
    def _fill_intent_in_domain(intent: Any) -> bool:
        """B1：意圖是否在值域內（與 `_write_draft_merge_intent` 的值域外丟棄條件同一組：動作在 `FORMS`、每個鍵都在該
        表單且為 `user_words` 來源；`action=none` 算值域內）。值域外 ⇒ 資料段未知。"""
        action = getattr(intent, "action", None)
        if action == WF.INTENT_NONE:
            return True
        form = WF.FORMS.get(action) if isinstance(action, str) else None
        if form is None:
            return False
        for item in list(getattr(intent, "fields", None) or []):
            key = getattr(item, "key", None)
            f = form.field(key) if isinstance(key, str) else None
            if f is None or f.source != WF.SOURCE_USER_WORDS:
                return False
        return True

    @staticmethod
    def _fill_read_data(wd: Any, obj: Any, marks: Optional[list] = None) -> None:
        """B1：由 `_await_write_intent` 驗過（`WriteIntent` 驗證通過，含 `action=none`）的**原始物件**讀兩鍵並驗：
        每一段（空段、全空白段略過）都要在最新一句原句裡、起訖不切斷數字或英數（`_fill_locate`）；`answer_text`（只在
        追問回合附了才讀）要落在某一段**留下來的**資料段之內、同樣兩條。全部成立 ⇒ 存原句原字（`fill_data`、
        `fill_answer`）；任一不成立、鍵缺、`null`、型別不對 ⇒ 不存（資料段未知）。⛔ 存模型回的字串本身。
        修復輪 1（RC2）：完全不出現在最新一句的段（去空白後不是最新一句去空白後的子字串；AI 把前面回合的話抄進來）⇒
        略過該段（不算資料、也不讓整回合未知），記 `fill_segment_not_in_message`（固定字串，進 `marks`）；全部段都被
        略過 ⇒ `fill_data=[]`（B3 空陣列：不併任何新值）。出現在最新一句、但每一處起訖都切斷數字或英數 ⇒ 仍是整回合
        未知（AI 切錯 ⇒ fail-closed）。只縮不擴：留下的段仍全是最新一句的原字，前面回合的值照舊擋在 (iii)。
        修復輪 1 追加 2（RC4 形狀 A）：`answer_text` 不成立能讓整回合未知，只限**恰好追問一欄**（`len(wd.asked) == 1`，
        與 `_write_draft_fill_answer` 用答覆段的條件同一個）；追問兩欄以上 ⇒ 只當沒有答覆段（`fill_answer=None`）。"""
        if not wd.fill_active or wd.fill_proposal_first:
            return
        texts = WF.intent_data_texts(obj)
        if texts is None:
            return
        message = wd.user_message if isinstance(wd.user_message, str) else ""
        spans = _fill_data_spans(message, texts, marks)
        if spans is None:
            return
        answer: Optional[str] = None
        if wd.fill_asked_labels:
            # 修復輪 1 追加 2（RC4 形狀 A）：`answer_text` 只在**恰好追問一欄**時有用途（`_write_draft_fill_answer` 的
            # `len(wd.asked) != 1` ⇒ 不填），也只在那時能讓整回合未知（fail-closed 照舊）。追問兩欄以上 ⇒ `answer_text`
            # 鍵缺、型別不對、或不落在留下的資料段內，一律只當沒有答覆段（`fill_answer=None`），`fill_data` 照留下的段存。
            single = len(wd.asked) == 1
            raw_answer = WF.intent_answer_text(obj)
            if raw_answer is None:
                if single:
                    return
            else:
                answer = ""
                if _no_ws(raw_answer):
                    found = None
                    for s, e in spans:
                        found = _fill_locate(message, raw_answer, s, e)
                        if found is not None:
                            break
                    if found is None:
                        if single:
                            return
                        answer = None
                    else:
                        answer = message[found[0]:found[1]]
        wd.fill_data = [message[s:e] for s, e in spans]
        wd.fill_answer = answer

    # -- 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.1～4.3）-----------------------------------
    # 分工（DSP-091）：資料段由 AI 在寫入意圖呼叫標出（`data_texts`）；收不收、要不要說沒套用由程式決定。
    # ⛔ 本節任何地方以道謝或寒暄的詞表判斷。資料段只活在本回合（§4.3 第 10 點）。
    def _fill_wide_begin(self, wd: Any) -> dict:
        """§4.1 寬回合判定（只由 `_fill_begin_intent_call` 呼叫＝送出意圖呼叫之前判一次）：`AGENT_FILL_DATA_TEXT_WIDE` on、
        非凍結、非 `pick:` 按鈕回合，且 (a) 首句（`had_draft` 為 `False`）、(b) 卡後（`had_draft`、`asked` 空，且下列之一：
        回合開始時草稿綁定的那張卡還活著＝`bound_card_live`〔`_write_draft_bound_card` 找得到、無 `receipt`、`invalidated`
        非 `True`〕；寫入候選清單還在等使用者選＝`pick_list_open`〔候選回合，意圖呼叫走 `pick_rule=True`〕）、
        (c) 多欄（`had_draft`、`len(asked) >= 2`）之一 ⇒ 設 `fill_wide`／`fill_wide_kind`，回三個建構點共用的
        `{"data_text": True}`（⛔ `asked_labels`：§4.2）。`had_draft`、`asked` 空，但既沒有活卡、也沒有等選的候選清單（例：
        插問知識題後 `asked` 已清空、還沒出過卡也沒列候選）⇒ 不是寬回合。其餘（含單欄追問回合）⇒ `{}`：系統句、schema、
        值閘照現行（plan-fill-wide-20261028 §4.1 (b)、§11 r1c）。"""
        if not self._fill_data_text_wide_on or wd.frozen or wd.pick_button:
            return {}
        if not wd.had_draft:
            kind = FILL_WIDE_FIRST
        elif not wd.asked:
            if not (wd.bound_card_live or wd.pick_list_open):
                return {}
            kind = FILL_WIDE_CARD
        elif len(wd.asked) >= 2:
            kind = FILL_WIDE_MULTI
        else:
            return {}
        wd.fill_wide = True
        wd.fill_wide_kind = kind
        return {"data_text": True}

    @staticmethod
    def _fill_wide_read_data(wd: Any, obj: Any, marks: Optional[list] = None) -> None:
        """§4.2：寬回合由驗過（`WriteIntent` 驗證通過、值域內，含 `action=none`）的**原始物件**讀 `data_texts`，逐段驗
        （`_fill_data_spans`，與單欄追問回合同一支）；成立 ⇒ `fill_wide_data`＝最新一句原句原字；鍵缺、`null`、型別不對、
        切斷數字或英數 ⇒ 不存（資料段未知）。⛔ 讀 `answer_text`、⛔ 存模型回的字串本身。"""
        if wd is None or not wd.fill_wide:
            return
        texts = WF.intent_data_texts(obj)
        if texts is None:
            return
        message = wd.user_message if isinstance(wd.user_message, str) else ""
        spans = _fill_data_spans(message, texts, marks)
        if spans is None:
            return
        wd.fill_wide_data = [message[s:e] for s, e in spans]

    async def _fill_wide_await_data(self, acc: TurnAccumulator) -> None:
        """§4.3 第 4 點「主模型提議比意圖先到」：寬回合、意圖尚未取用 ⇒ 以 `asyncio.wait`（⛔ 取消）等本回合
        `acc.write_intent_call`（⛔ 讀 `self._write_intent_calls`），上限與 `_await_write_intent` 同式
        `max(0.0, min(WRITE_INTENT_WAIT_MAX_S, 剩餘期限 − WRITE_DRAFT_PROGRAM_MIN_REMAINING_S))`。每回合只等一次
        （`fill_wide_waited` 鎖住；⛔ 逐值重等、⛔ 沿用 `fill_proposal_first`）。完成 ⇒ 由同一個結果物件無副作用判讀
        （`_peek_write_intent`）讀資料段；未完成、失敗、無法解析、值域外、任何例外 ⇒ 資料段未知（照現行收值）。
        ⛔ 在此記 violation、寫意圖相關欄位、設 `intent_consumed`（意圖的合併照現行時點：`_write_draft_decide`）。"""
        wd = acc.write_draft
        if wd is None or not wd.fill_wide or wd.fill_wide_waited or wd.intent_consumed:
            return
        wd.fill_wide_waited = True
        call = acc.write_intent_call
        if call is None or call.settled or call.label_only:
            return
        try:
            remaining = self.budget.deadline_s - (self._clock() - acc.start)
            timeout = max(0.0, min(WRITE_INTENT_WAIT_MAX_S, remaining - WRITE_DRAFT_PROGRAM_MIN_REMAINING_S))
            done, _pending = await asyncio.wait({call.task}, timeout=timeout)
            if not done:
                return
            status, obj, intent = _peek_write_intent(call)
            if status != _PEEK_OK or not self._fill_intent_in_domain(intent):
                return
            self._fill_wide_read_data(wd, obj, None)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — 判讀失敗 ⇒ 資料段未知（⛔ 記例外字串：§4.3 第 10 點）
            wd.fill_wide_data = None

    @staticmethod
    def _fill_wide_not_applied_labels(wd: Any) -> list:
        """§4.3 第 8 點：寬回合卡後、本回合被資料段拒收且最後仍沒套用的欄位標籤（依序）；非寬回合卡後 ⇒ `[]`。"""
        if wd is None or not wd.fill_wide or wd.fill_wide_kind != FILL_WIDE_CARD:
            return []
        action = wd.draft.get("action") if isinstance(wd.draft, dict) else None
        return [label for (act, _key), label in wd.fill_wide_rejected.items() if act == action]

    def _fill_wide_notice(self, wd: Any) -> Optional[str]:
        """§4.3 第 8 點「部分套用、卡重出」：點名沒套用的欄位標籤的程式固定句（⛔ 帶值）；沒有 ⇒ `None`。"""
        return WF.fill_wide_not_applied_text(self._fill_wide_not_applied_labels(wd))

    @staticmethod
    def _fill_wide_slot(wd: Any, f: Any) -> tuple:
        """寬回合拒收紀錄的鍵：`(目前草稿動作, 表單鍵)`（回合中換動作時只點名目前草稿的欄位）。"""
        return (wd.draft.get("action") if isinstance(wd.draft, dict) else None, f.key)

    def _fill_wide_precheck(self, acc: TurnAccumulator, f: Any, value: str) -> Optional[tuple]:
        """§4.3 B 寬回合、(iii) 之前（`value`＝(i) 現行值閘的輸出）：(ii) 等於草稿現值 ⇒ 照併；資料段未知或空陣列
        （第 3、5 點）⇒ 照現行收值、記 `fill_wide_data_unknown`。回 `(值, False)` ⇒ 到此為止；`None` ⇒ 接著做 (iii)。"""
        wd = acc.write_draft
        fields = (wd.draft.get("fields") or {}) if isinstance(wd.draft, dict) else {}
        current = fields.get(f.key)
        if current is not None and value == current:
            return value, False
        if not wd.fill_wide_data:
            self._fill_mark(acc, WF.V_FILL_WIDE_DATA_UNKNOWN)
            wd.fill_wide_rejected.pop(self._fill_wide_slot(wd, f), None)
            return value, False
        return None

    def _fill_wide_verdict(
        self, acc: TurnAccumulator, identity: Identity, f: Any, value: str, inside: bool,
    ) -> tuple:
        """§4.3 B 寬回合 (iii) 的結果：值在某一段資料段內（enum／category 不比，恆為內）⇒ 收；不在 ⇒ 只拒收這一個值
        （`fill_value_outside_data`；候選集綁定欄 `_fill_bound_field_exempt` 只過 (i)，第 9 點）；卡後拒收記進
        `fill_wide_rejected`（第 8 點）。⛔ B4、B5、B6、fail-closed。存進草稿的一律是 (i) 的輸出；新拒收 ⛔ 計入
        `user_value_dropped`（第二格 `False`）。"""
        wd = acc.write_draft
        slot = self._fill_wide_slot(wd, f)
        if not inside:
            if self._fill_bound_field_exempt(identity, wd, f):
                self._fill_mark(acc, WF.V_FILL_BOUND_FIELD_EXEMPT)
                return value, False
            if wd.fill_wide_kind == FILL_WIDE_CARD and isinstance(f.label, str) and f.label:
                wd.fill_wide_rejected[slot] = f.label
            self._fill_mark(acc, WF.V_FILL_VALUE_OUTSIDE_DATA)
            return None, False
        wd.fill_wide_rejected.pop(slot, None)
        return value, False

    # -- E 片：對話動作標籤與程式出口（plan-closing-handoff-e-20261026 §4.1）------------
    # 分工（DSP-091、P7）：理解由 AI（`dialog_act` 標籤）；轉不轉人、收不收尾、回什麼由程式依標籤與程式持有的
    # 狀態決定。⛔ 本節任何地方以關鍵字或詞表判斷使用者要什麼（E-R5）。
    def _closing_active(self) -> bool:
        """E 片生效：`AGENT_CLOSING_HANDOFF` on。off ⇒ 不加欄、不建標籤呼叫、不走程式轉人／收尾。"""
        return bool(getattr(self, "_closing_handoff_on", False))

    def _start_dialog_act_call(self, acc: TurnAccumulator, agent_state: dict, user_message: str) -> None:
        """每個使用者文字回合的標籤呼叫（計畫 r5 附錄）：同模型、同 client、`max_completion_tokens` 800、輸入＝系統句＋
        本會話對話（`dialog`）＋當句；與主模型迴圈、寫入意圖呼叫**並行**（只建立、⛔ await）。影子回合不建。
        存 `acc.dialog_act_call`、登記 `self._dialog_act_calls`（⛔ 佔寫入意圖呼叫的欄位與登記）。
        取 client 與呼叫都在 task 內：取不到或呼叫失敗 ⇒ task 例外 ⇒ 標籤未提供（後備＝主模型輸出）。"""
        if self.readonly_view:
            return
        # ⚠️ 系統句勿附「正在追問哪一欄」：附了之後追問物件名稱時，AI 會把「OK 3q」讀成名稱而出錯筆卡。
        # 代價是「好 名稱叫 X 謝謝」這類答覆＋道謝會被標成 resolved，由程式重問一次（已知偏離，見 E 片收案報告）。
        messages: list = [{"role": "system", "content": WF.dialog_act_only_system_prompt()}]
        for m in agent_state.get("dialog") or []:
            if (isinstance(m, dict) and m.get("role") in ("user", "assistant")
                    and isinstance(m.get("content"), str)):
                messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_message if isinstance(user_message, str) else ""})
        kwargs: dict = dict(
            model=self._model,
            messages=messages,
            response_format=WF.dialog_act_only_response_format(),
            max_completion_tokens=WF.WRITE_INTENT_MAX_COMPLETION_TOKENS,
        )
        if self._reasoning_effort is not None:
            kwargs["extra_body"] = {"reasoning_effort": self._reasoning_effort}

        async def _call() -> Any:
            return await self.provider.async_client.chat.completions.create(**kwargs)

        call = _DialogActCall(
            asyncio.create_task(_call()), model=self._model,
            input_chars=sum(len(m["content"]) for m in messages),
            registry=self._dialog_act_calls, trace_id=acc.trace_id,
        )
        #: 追問欄位中的標籤確認呼叫用同一份輸入（`_dialog_act_field_confirm`）。
        call.kwargs = kwargs
        self._dialog_act_calls[acc.trace_id] = call
        acc.dialog_act_call = call

    @staticmethod
    def _dialog_act_label(acc: TurnAccumulator) -> Optional[str]:
        """本回合標籤呼叫（`acc.dialog_act_call`）**已完成**時的 `dialog_act` 值；
        未完成、失敗、被取消、解析不出、值域外 ⇒ `None`（唯讀、⛔ await）。"""
        call = acc.dialog_act_call
        if call is None:
            return None
        task = call.task
        if not task.done() or task.cancelled() or task.exception() is not None:
            return None
        result = task.result()
        if isinstance(result, _RetriedIntentResponse) and result.failed:
            return None
        try:
            content = result.choices[0].message.content
        except Exception:  # noqa: BLE001 — 回應形狀不對 ⇒ 標籤未提供
            return None
        return WF.parse_dialog_act_content(content)

    def _closing_pending_state(self, acc: TurnAccumulator, identity: Identity, agent_state: dict) -> bool:
        """E-R3 的「未決狀態」（程式持有的狀態，唯讀）：`pending_confirm` 有本建立者未兌現且未作廢的卡、
        寫入草稿存在（進行中欄位）、候選集未開（有效候選集存在）。任一成立 ⇒ `True`。"""
        wd = acc.write_draft
        if wd is not None and (wd.draft is not None or wd.candidates is not None):
            return True
        pending_all = agent_state.get(PENDING_CONFIRM_KEY) if isinstance(agent_state, dict) else None
        if isinstance(pending_all, dict):
            creator = _pending_creator(identity)
            for entry in pending_all.values():
                if (isinstance(entry, dict) and entry.get("creator") == creator
                        and entry.get("invalidated") is not True and entry.get("receipt") is None):
                    return True
        return False

    def _dialog_act_decision(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
        act: Optional[str] = None,
    ) -> Optional[str]:
        """標籤 ＋ 程式持有的狀態 ⇒ 程式出口：`WF.DIALOG_ACT_WANTS_HUMAN`（程式轉人）、`WF.DIALOG_ACT_RESOLVED`
        （程式收尾）或 `None`（照現行）。純函式（唯讀）。當句命中 `question_sensitive`（或規則集拿不到，fail-closed）
        ⇒ `None`（照現行敏感路徑，E-R6）；`resolved` 有未決狀態 ⇒ `None`（E-R3）。"""
        if not self._closing_active():
            return None
        label = act if act is not None else self._dialog_act_label(acc)
        if label not in (WF.DIALOG_ACT_WANTS_HUMAN, WF.DIALOG_ACT_RESOLVED):
            return None
        rules = getattr(self.verifier, "rules", None)
        if rules is None or question_sensitive(user_message, rules):
            return None
        if label == WF.DIALOG_ACT_RESOLVED and self._closing_pending_state(acc, identity, agent_state):
            return None
        return label

    def _dialog_act_exit(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str, *,
        cache: dict, act: Optional[str] = None,
    ) -> Optional[TurnResult]:
        """E 片程式出口（E-R1～E-R4、E-R6）：
        - `wants_human` ⇒ 程式轉人：`kind=handoff`、`handoff.reason=user_request`、回覆 `USER_REQUEST_HANDOFF_TEXT`；
          ⛔ 經 `_apply_handoff_without_lookup`（該閘只認 `NON_SENSITIVE_HANDOFF_REASONS`，`user_request` 不在其內）；
          程式來源以 `acc._program_handoff` 標記辨識（⛔ 以 reason 字串辨識）。
        - `resolved` 且無未決狀態 ⇒ 程式收尾：`kind=answer`、`outcome=answered/text`、回覆 `CLOSING_TEXT`。
        - 其他 ⇒ `None`（照現行）。回合經 `exit_gates.finalize` 收尾（dialog、handoff cache、決策快照照常）。"""
        decision = self._dialog_act_decision(acc, identity, agent_state, user_message, act)
        if decision is None:
            return None
        acc.violations.append(WF.V_DIALOG_ACT_EXIT)
        self._write_draft_end_turn(acc, agent_state)
        if decision == WF.DIALOG_ACT_WANTS_HUMAN:
            acc._program_handoff = True
            handoff_dict = {
                "reason": HandoffReason.user_request.value,
                "fact_class": FactClass.other.value,
                "channel": effective_handoff_channel(None),
                "message": WF.USER_REQUEST_HANDOFF_TEXT,
            }
            result = TurnResult(
                kind="handoff", answer=WF.USER_REQUEST_HANDOFF_TEXT, handoff=handoff_dict,
                quick_replies=[],
                trace=acc.build_trace(
                    final_kind="handoff", handoff_reason=HandoffReason.user_request.value,
                    clock=self._clock, copy_lists=True),
            )
            return exit_gates.finalize(
                acc, result, is_fixed=True, verifier=self.verifier,
                cache=cache, agent_state=agent_state, user_message=user_message)
        result = TurnResult(
            kind="answer", answer=WF.CLOSING_TEXT, handoff=None, quick_replies=[],
            trace=acc.build_trace(
                final_kind="answer", handoff_reason=None, clock=self._clock, copy_lists=True),
            outcome=make_outcome("answered", expects="text"),
        )
        return exit_gates.finalize(
            acc, result, is_fixed=False, verifier=self.verifier,
            cache=cache, agent_state=agent_state, user_message=user_message)

    @staticmethod
    def _pre_loop_program_exit_pending(acc: TurnAccumulator) -> bool:
        """迴圈前的三個程式出口（重送、卡仍有效、剛送出）會不會回（只看旗標，⛔ 呼叫出口函式——它們有收尾副作用）。"""
        wd = acc.write_draft
        return bool(wd is not None and (
            wd.reissue_blocked or isinstance(wd.card_still_valid, dict) or wd.submitted_edit))

    async def _dialog_act_pre_loop(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str, *,
        cache: dict, program_first: bool = False,
    ) -> Optional[TurnResult]:
        """決定點 (a)：主模型迴圈之前。標籤已完成 ⇒ 依 `_dialog_act_exit` 決定。迴圈前程式出口
        （重送、卡仍有效、剛送出）或程式優先入口的程式訊息（`program_first`：這一輪不叫主模型，程式回話可能直接
        結束回合）要回之前標籤未完成 ⇒ 至多等 1 秒（回合開始時已有草稿 3 秒，同 W1c 分級；程式優先入口已等滿
        逾時 ⇒ 不再多等），仍未完成 ⇒ 記 `dialog_act_fallback`（後備，KD-5 (3)）。
        其他回合不新增迴圈前等待（由 (b) 競速）。候選按鈕回合沒有使用者文字，呼叫端不進本函式。"""
        call = acc.dialog_act_call
        if call is None:
            return None
        program_pending = program_first or self._pre_loop_program_exit_pending(acc)
        if (not call.task.done() and program_pending
                and WF.V_PROGRAM_FIRST_WAIT_TIMEOUT not in acc.violations):
            wd = acc.write_draft
            wait_s = (WRITE_DRAFT_PROGRAM_FIRST_WAIT_S if wd is not None and wd.had_draft
                      else WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S)
            await asyncio.wait({call.task}, timeout=wait_s)
        if not call.task.done():
            if program_pending:
                acc.violations.append(WF.V_DIALOG_ACT_FALLBACK)
            return None
        return self._dialog_act_exit(acc, identity, agent_state, user_message, cache=cache)

    async def _dialog_act_settle_wait(self, acc: TurnAccumulator) -> None:
        """標籤呼叫未完成 ⇒ 至多等 `DIALOG_ACT_AFTER_OUTPUT_WAIT_S`（以回合剩餘期限為界；⛔ 取消）。"""
        call = acc.dialog_act_call
        if call is None or call.settled or call.task.done():
            return
        remaining = self.budget.deadline_s - (self._clock() - acc.start)
        await asyncio.wait({call.task}, timeout=max(0.0, min(DIALOG_ACT_AFTER_OUTPUT_WAIT_S, remaining)))

    async def _dialog_act_after_output(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str, *,
        cache: dict,
    ) -> Optional[TurnResult]:
        """決定點 (c)：主模型最終輸出要進 `_write_draft_after_output` 與出口閘之前。標籤未完成 ⇒
        至多再等 1 秒；仍未完成 ⇒ 用主模型輸出、記 `dialog_act_fallback`。已完成 ⇒ 依 `_dialog_act_exit` 決定。"""
        call = acc.dialog_act_call
        if call is None or not self._closing_active():
            return None
        if not call.task.done():
            remaining = self.budget.deadline_s - (self._clock() - acc.start)
            await asyncio.wait({call.task}, timeout=max(0.0, min(DIALOG_ACT_AFTER_OUTPUT_WAIT_S, remaining)))
            if not call.task.done():
                acc.violations.append(WF.V_DIALOG_ACT_FALLBACK)
                return None
        return self._dialog_act_exit(acc, identity, agent_state, user_message, cache=cache)

    async def _await_write_intent(self, acc: TurnAccumulator) -> Optional[WriteIntent]:
        """觸發判斷點取用意圖判斷結果：`asyncio.wait`（⛔ 自動取消）等
        `min(WRITE_INTENT_WAIT_MAX_S, 剩餘期限 − 觸發門檻)` 秒。逾時／失敗 ⇒ `None`＋
        `write_intent_call_failed`（⛔ 影響主回合；task 留給 trace 收尾處理）；無法解析 ⇒
        `None`＋`write_intent_unparsed`；多個內容不同的 action 物件 ⇒ `None`＋
        `write_intent_ambiguous`；`action="none"` ⇒ `None`。形狀不合 pydantic ⇒ 值域外。"""
        call = acc.write_intent_call
        if call is None or call.settled or call.label_only:
            return None
        remaining = self.budget.deadline_s - (self._clock() - acc.start)
        timeout = max(0.0, min(WRITE_INTENT_WAIT_MAX_S, remaining - WRITE_DRAFT_PROGRAM_MIN_REMAINING_S))
        done, _pending = await asyncio.wait({call.task}, timeout=timeout)
        # 判讀與寬回合「提議先到、等意圖」共用同一支無副作用函式（plan-fill-wide-20261028 §4.3 第 4 點）；標記只在這裡記。
        status, obj, intent = _peek_write_intent(call) if done else (_PEEK_FAILED, None, None)
        if status in (_PEEK_FAILED, _PEEK_PENDING):
            acc.violations.append(WF.V_CALL_FAILED)
            return None
        if status == _PEEK_RETRY_FAILED:
            # F12 r6 復原第 5 輪 §11.15.3 第 5 點：重送後仍截斷或解析不出 ⇒ 照現行（`None`＋無法解析）。
            acc.violations.append(WF.V_UNPARSED)
            return None
        if status == _PEEK_AMBIGUOUS:
            acc.violations.append(WF.V_AMBIGUOUS)
            return None
        if status == _PEEK_UNPARSED:
            acc.violations.append(WF.V_UNPARSED)
            return None
        if status == _PEEK_OUT_OF_DOMAIN:
            acc.violations.append(WF.V_OUT_OF_DOMAIN)
            return None
        if acc.write_draft is not None and getattr(self, "_write_lifecycle_on", False):
            # 第 3 步 #9g：`WriteIntent` 忽略多餘鍵 ⇒ 布林欄位由原始物件讀（恰為 `true` 才算）。
            acc.write_draft.modifies_submitted = WF.intent_modifies_submitted(obj)
        if (acc.write_draft is not None and acc.write_draft.pick_offered
                and not acc.write_draft.cmd_offered):
            # A-2a：`pick_id` 由原始物件讀（**未驗證**；`_write_candidates_typed` 再比對候選集）。
            # 選定後回合改指令式：`cmd_offered` 的回合 schema 沒有 `pick_id` ⇒ ⛔ 讀（假模型照回也不讀）。
            acc.write_draft.intent_pick_id = WF.intent_pick_id(obj)
        if acc.write_draft is not None:
            # F12 r6 復原第 5 輪 §11.15.3 第 6 點：解析成功且過驗證（含 `action=none`）⇒ 選定後的名稱去向走單次決定。
            acc.write_draft.intent_parsed = True
        if acc.write_draft is not None and acc.write_draft.cmd_offered:
            # 選定後回合改指令式：只有本回合真的送出指令版 schema 才讀 `target`（**未驗證**；
            # `_write_candidates_cmd_effect` 逐項驗）。沒設 `cmd_offered` ⇒ ⛔ 讀。
            acc.write_draft.intent_target = WF.intent_pick_target(obj)
        if acc.write_draft is not None and acc.write_draft.rechoice_offered:
            # A-2a 修正 2：`record_rechoice` 由原始物件讀（值域內字串才算；帶不帶回只認 `same`）。
            acc.write_draft.record_rechoice = WF.intent_record_rechoice(obj)
        if (acc.write_draft is not None and acc.write_draft.fill_active
                and self._fill_intent_in_domain(intent)):
            # 填欄只填答覆 B1：資料段的唯一來源＝這個驗過的物件（`action=none` 同樣由原始物件讀，比照 `pick_id`）。
            # 值域外（動作不在表單、或夾帶表單外／非 user_words 鍵，`_write_draft_merge_intent` 會整份丟棄）⇒ ⛔ 讀，
            # 本回合資料段未知（§4.1 B1「意圖回 None（…值域外）」）。
            self._fill_read_data(acc.write_draft, obj, acc.violations)
        if (acc.write_draft is not None and acc.write_draft.fill_wide
                and self._fill_intent_in_domain(intent)):
            # 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.2）：資料段同樣只由這個驗過、值域內的物件讀。
            self._fill_wide_read_data(acc.write_draft, obj, acc.violations)
        if intent.action == WF.INTENT_NONE:
            return None
        return intent

    async def _write_draft_gate_value(
        self, f: Any, raw: Any, identity: Identity, texts: list, violations: list,
        *, from_intent: bool = False,
    ) -> Optional[str]:
        """值閘（§2.1(3) 型別×規則表）：過 ⇒ 要存進草稿的字串；不過 ⇒ `None`＋固定字串
        violation（⛔ 帶值）。空值／沒給 ⇒ `None` 且不記 violation。
        W1c §9.11-1：`from_intent`（值來自意圖判斷呼叫）時 `int`／`number` 取值改用
        `parse_number_token`（恰好一個數字 token ⇒ 取它），仍須過 `_number_in_texts`。"""
        if f is None or f.source != WF.SOURCE_USER_WORDS:
            return None
        if isinstance(raw, bool):
            violations.append(WF.V_NOT_IN_USER_WORDS)
            return None
        if isinstance(raw, (int, float)):
            raw = str(raw)
        if not isinstance(raw, str):
            violations.append(WF.V_NOT_IN_USER_WORDS)
            return None
        value = raw.strip()
        if not value:
            return None
        if len(value) > WF.value_max_len(f):
            violations.append(WF.V_VALUE_TOO_LONG)
            return None
        kind = f.kind
        if kind == "text":
            needle = _no_ws(value)
            if (sanitize_data_piece(value) != value
                    or not any(needle in _no_ws(t) for t in texts)):
                violations.append(WF.V_NOT_IN_USER_WORDS)
                return None
            return value
        if kind in ("int", "number"):
            num = (WF.parse_number_token(value, kind) if from_intent
                   else WF.parse_number(value, kind))
            # 沿用既有 `_number_in_texts`（完整數字 token 出現在使用者原話；國字數字不收）。
            if num is None or not _number_in_texts(num, texts):
                violations.append(WF.V_NOT_IN_USER_WORDS)
                return None
            return str(num)
        if kind == "date":
            parsed = WF.parse_model_date(value)
            if parsed is None or parsed not in WF.user_text_dates(texts, bills._today()):
                violations.append(WF.V_NOT_IN_USER_WORDS)
                return None
            return WF.iso_date(parsed)
        if kind == "email":
            needle = _no_ws(value)                 # 兩邊都只去空白（⛔ 去連字號）
            if not any(needle in _no_ws(t) for t in texts):
                violations.append(WF.V_NOT_IN_USER_WORDS)
                return None
            return value                            # 草稿存模型給的原值
        if kind == "phone":
            needle = _no_ws(value).replace("-", "")
            if not needle or not any(needle in _no_ws(t).replace("-", "") for t in texts):
                violations.append(WF.V_NOT_IN_USER_WORDS)
                return None
            return value
        if kind == "enum":
            if from_intent and getattr(self, "_write_lifecycle_on", False):
                # 第 3 步 A4：意圖判斷呼叫只收**標籤**（表單 `choice_labels`），程式依表單轉代碼；
                # 不是標籤（含直接填代碼）⇒ 值域外＝缺值（照表單追問）。⛔ 欄位名分支。
                code = WF.enum_code_for_label(f, value)
                if code is None:
                    violations.append(WF.V_VALUE_OUT_OF_DOMAIN)
                    return None
                return code
            if value not in f.choices:              # ⛔ 語意詞表比對（只認封閉值域）
                violations.append(WF.V_VALUE_OUT_OF_DOMAIN)
                return None
            return value
        if kind == "category":
            try:
                ok = await _is_valid_repair_category(value, identity)
            except Exception:  # noqa: BLE001 — 分類樹查不成 ⇒ 不收（fail-closed）
                ok = False
            if not ok:
                violations.append(WF.V_CATEGORY_INVALID)
                return None
            return value
        if kind == "period":
            # 期別片 P-2：比**解析後的年月**（同 `date` 分支：同一個時鐘 `bills._today()`）；
            # 存程式從原話解析出的正規化值，⛔ 存模型原值。
            stored = _period_gate_value(value, texts, bills._today())
            if stored is None:
                violations.append(WF.V_NOT_IN_USER_WORDS)
                return None
            return stored
        if kind == "range":
            # 「選對紀錄」片 §4.2-1：客人講的計費起訖——由**程式**從原話解析（`bill_period.parse_said_range`
            # 封閉語法；解析不到＝沒講）；模型值解析後須等於某一則原話解析出的值，存程式正規化值（⛔ 模型原值）。
            stored = _parse_said_range(value)
            if stored is None or stored not in {
                    _parse_said_range(t) for t in texts if isinstance(t, str)}:
                violations.append(WF.V_NOT_IN_USER_WORDS)
                return None
            return stored
        return None                                 # sys_id 等：一律不進草稿

    def _fill_bound_field_exempt(self, identity: Identity, wd: Any, f: Any) -> bool:
        """修復輪 2（P3-2，業主 10-27 §6 第 9 點）：`f` 是候選集綁定的那一欄，且候選集**未選定或已撤回**
        （`picked` 為 `None`）、回合開始時不是已選定（`cmd_scope_start` 為 `False`：已選定的指令式回合名稱值照舊由
        `_write_candidates_name_rule`／指令路徑處理，含回合中才撤回的情形）、此刻仍綁定本草稿（建立者、動作、名稱指紋，
        `_write_candidates_bound`）⇒ `True`（呼叫端只過 (i)：值仍須在客人原話裡）。候選集只在回合開始讀回
        （`_write_candidates_load`），回合中新列的候選集在值閘之後才建立 ⇒ 此刻存在者即回合開始就有的那一份（或其
        撤回／改選後的同一份）。⛔ 由本例外選定候選；名稱解析與選定照現行規則。"""
        cands = wd.candidates
        if not isinstance(cands, dict) or wd.cmd_scope_start or cands.get("picked") is not None:
            return False
        if getattr(f, "key", None) != cands.get("field"):
            return False
        return self._write_candidates_bound(cands, identity, wd.draft)

    async def _write_draft_turn_gate(
        self, acc: TurnAccumulator, identity: Identity, f: Any, raw: Any, *, from_intent: bool = False,
    ) -> tuple:
        """**本回合閘門原話**（填欄只填答覆 §4.1 B；§3 G6 六個值閘呼叫點 ①～⑥ 一律經這一支，⛔ 各點各寫）。
        回 `(要存進草稿的值或 None, 現行值閘是否丟掉使用者的值)`——第二格＝改前「值閘拒收且有記 violation」，呼叫端照
        改前規則決定記不記 `user_value_dropped`（本節新增的拒收一律 `False`：B2 ⛔ 計入值被丟）。

        (i) 現行值閘照舊比 `wd.user_texts`（⛔ 改）；不過 ⇒ 照現行拒收。非寫入回合（`fill_active` 為 `False`：開關 off、
        文件回合、`pick:` 回合）到此為止 ⇒ 與改前逐字相同。寫入回合另依序：
        (ii) (i) 的正規化結果等於草稿該欄現值 ⇒ 照現行同值重併（資料段未知時也一樣）；
        B2 資料段未知 ⇒ 拒收（`fill_data_text_unknown`）；B3 資料段空陣列 ⇒ 拒收（任何型別，含 enum／category，業主裁
        C1 (a)）；(iii) 非空 ⇒ 同一值閘只拿資料段**逐段**比（⛔ 串接；enum／category 的值閘不比原話，不再跑），
        都不過 ⇒ 拒收（`fill_value_outside_data`）；
        B5 追問回合（草稿仍是回合開始那份）已填的非追問欄、且不是候選集綁定那一欄 ⇒ 不覆寫（`fill_filled_field_kept`）。
        修復輪 2（P3-2）：候選集綁定那一欄（`_fill_bound_field_exempt`）⇒ 不套 B2／B3／(iii)，只過 (i)（比全部
        `user_texts`）；例外實際放行時記 `fill_bound_field_exempt`。
        存進草稿的一律是 (i) 的輸出。"""
        wd = acc.write_draft
        marks_before = len(acc.violations)
        value = await self._write_draft_gate_value(
            f, raw, identity, wd.user_texts, acc.violations, from_intent=from_intent)
        if value is None:
            return None, len(acc.violations) > marks_before
        if wd.fill_wide:
            # 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.3）：與單欄追問回合互斥（⛔ 設 `fill_proposal_first`）。
            early = self._fill_wide_precheck(acc, f, value)
            if early is not None:
                return early
            inside = f.kind in ("enum", "category")
            draft_fields = (wd.draft.get("fields") or {}) if isinstance(wd.draft, dict) else {}
            if (not inside and draft_fields.get(f.key) in (None, "")
                    and not self._fill_bound_field_exempt(identity, wd, f)):
                # 修復輪 1 RC-W1（計畫 §11 改動第 1 點）：(i) 已過、值卻不在最新一句（只出現在前面回合的使用者訊息：前一句講過、
                # AI 這一句才補上）⇒ 照 (i) 的輸出收、記 `fill_wide_carry_over`、清該欄拒收紀錄；最新一句裡有 ⇒ 照第 6 點 (iii)。
                # 放行的一律是 (i) 的輸出（＝改前行為，⛔ 比改前寬）；候選綁定欄照現行例外（不經本段）。
                # 修復輪 1 追加（R1-W1b，X4 FA1c-rep-06）：只限草稿該欄目前為空（「補上」）；已有值 ⇒ ⛔ 走本段、照 (iii)
                # （前句值的改寫版不得覆寫已填欄）。
                latest = wd.user_message if isinstance(wd.user_message, str) else ""
                scratch_latest: list = []
                if await self._write_draft_gate_value(
                        f, raw, identity, [latest], scratch_latest, from_intent=from_intent) is None:
                    self._fill_mark(acc, WF.V_FILL_WIDE_CARRY_OVER)
                    wd.fill_wide_rejected.pop(self._fill_wide_slot(wd, f), None)
                    return value, False
            if not inside:
                scratch_wide: list = []
                for seg in wd.fill_wide_data:
                    if await self._write_draft_gate_value(
                            f, raw, identity, [seg], scratch_wide, from_intent=from_intent) is not None:
                        inside = True
                        break
            return self._fill_wide_verdict(acc, identity, f, value, inside)
        if not wd.fill_active:
            return value, False
        if not wd.intent_consumed:
            # B1：模型提議比意圖結果先到 ⇒ 本回合資料段未知（⛔ 直接解析 task 原始回應）。
            wd.fill_proposal_first = True
        fields = (wd.draft.get("fields") or {}) if isinstance(wd.draft, dict) else {}
        current = fields.get(f.key)
        if current is not None and value == current:
            return value, False
        if self._fill_data_unknown(wd):
            if self._fill_bound_field_exempt(identity, wd, f):
                self._fill_mark(acc, WF.V_FILL_BOUND_FIELD_EXEMPT)
                return value, False
            # 到這裡的值必與草稿現值不同（同值已由 (ii) 照併）⇒ 本回合有新值沒套用（主會話 10-27 裁待查 3）。
            wd.fill_not_applied = True
            self._fill_mark(acc, WF.V_FILL_DATA_TEXT_UNKNOWN)
            return None, False
        inside = False
        if wd.fill_data and f.kind in ("enum", "category"):
            inside = True
        elif wd.fill_data:
            scratch: list = []
            for seg in wd.fill_data:
                if await self._write_draft_gate_value(
                        f, raw, identity, [seg], scratch, from_intent=from_intent) is not None:
                    inside = True
                    break
        if not inside:
            if self._fill_bound_field_exempt(identity, wd, f):
                self._fill_mark(acc, WF.V_FILL_BOUND_FIELD_EXEMPT)
                return value, False
            wd.fill_not_applied = True
            self._fill_mark(acc, WF.V_FILL_VALUE_OUTSIDE_DATA)
            return None, False
        bound = wd.candidates.get("field") if isinstance(wd.candidates, dict) else None
        if (self._fill_followup_now(wd) and wd.fill_start_fields.get(f.key) not in (None, "")
                and f.key not in wd.asked and f.key != bound):
            wd.fill_not_applied = True
            self._fill_mark(acc, WF.V_FILL_FILLED_FIELD_KEPT)
            return None, False
        return value, False

    def _write_draft_target(self, acc: TurnAccumulator, action: str, *, from_intent: bool) -> dict:
        """取（或換新）本回合要合併的草稿：動作不同 ⇒ 換新草稿（W1b 安全處置 1b：一併清
        `asked`——新草稿的 `asked` 本就是 `[]`，回合內那一份上回合追問欄位也清掉）。"""
        wd = acc.write_draft
        if wd.draft is None or wd.draft["action"] != action:
            wd.draft = WF.new_draft(action, wd.owner)
            wd.asked = []
            if from_intent:
                wd.created = True
        wd.draft["idle_turns"] = 0
        return wd.draft

    async def _write_draft_merge_intent(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, intent: Any,
    ) -> set:
        """意圖判斷呼叫的結果合併進草稿（§2.1(2)(3)；W1b §8.1-1）。回本回合由意圖呼叫提供、
        且**通過值閘**的鍵集合（整句填入的同欄優先序用，§8.5-2）。"""
        wd = acc.write_draft
        if await self._dialog_act_not_field_answer(acc, agent_state):
            # E 片 §4.1-7（E-R13）：當句不是欄位答覆 ⇒ 意圖抽出的值也 ⛔ 合併（獨立意圖呼叫曾把「OK 3q」的「3q」
            # 抽成物件名稱而出卡，`e/x7-verifier/x7/fill1`）。
            return set()
        action = getattr(intent, "action", None)
        form = WF.FORMS.get(action) if isinstance(action, str) else None
        if form is None:
            acc.violations.append(WF.V_OUT_OF_DOMAIN)
            return set()
        if not self._write_draft_visible(identity, action):
            acc.violations.append(WF.V_NOT_VISIBLE)
            return set()
        items = list(getattr(intent, "fields", None) or [])
        if any(not isinstance(getattr(item, "key", None), str)
               or form.field(item.key) is None
               or form.field(item.key).source != WF.SOURCE_USER_WORDS
               for item in items):
            # 鍵在該動作表單之外（含 `system` 來源鍵、身分鍵）⇒ **整份意圖丟棄**
            # （偏保守：⛔ 從一份夾帶域外鍵的意圖裡挑幾個看起來對的值來用）。
            acc.violations.append(WF.V_OUT_OF_DOMAIN)
            return set()
        wd.activity = True
        draft = self._write_draft_target(acc, action, from_intent=True)
        # W1c §9.11-2：本回合前置查詢唯一命中而寫進**這份**草稿的物件名稱（系統值）優先——意圖的
        # `estate_name` 不覆寫它；意圖其他文字欄位值為該名稱或當句物件名稱那一段的子字串 ⇒ 丟棄。
        # （動作不同而換新草稿時，名稱不在新草稿內 ⇒ 不套用。）
        name_hit = (wd.caught_name is not None
                    and draft["fields"].get("estate_name") == wd.caught_name)
        name_spans = ([_name_overlap_key(s) for s in (wd.caught_name, wd.caught_segment) if s]
                      if name_hit else [])
        provided: set = set()
        for item in items:
            f = form.field(item.key)
            raw_value = getattr(item, "value", None)
            if name_hit and f.key == "estate_name":
                continue
            # F12 r6（§11.4 第 4 點）：候選集已選定或已撤回、仍綁定 ⇒ 名稱欄值依規則丟棄或改用新名稱。
            name_rule = self._write_candidates_name_rule(acc, identity, f, raw_value, defer=False)
            if name_rule == "collect":
                # 第 5 輪 §11.15.3 第 6 點：名稱值先收集，算出改選目標 X 之後再決定（`_write_candidates_post_pick_names`）。
                wd.collected_names.append(("intent", raw_value))
                continue
            if name_rule in ("drop", "same"):
                self._write_candidates_name_mark(acc, name_rule)
            if name_rule == "drop":
                continue
            # 期別片 P-3：`period` 型同樣套用（安全審查 C1：改型別後 ⛔ 讓這項檢查失效）。
            if (name_spans and f.kind in ("text", "period") and isinstance(raw_value, str)
                    and raw_value.strip()
                    and any(_name_overlap_key(raw_value) in span for span in name_spans)):
                acc.violations.append(WF.V_VALUE_OVERLAPS_NAME)
                continue
            range_f = form.field(_PR_SAID_RANGE)
            if (f.kind == "period" and range_f is not None and range_f.kind == "range"
                    and isinstance(raw_value, str) and _parse_said_range(raw_value) is not None
                    and _parse_period(raw_value, bills._today()) is None):
                # 「選對紀錄」片：AI 把客人講的計費起訖（「6/29到6/30那期」）放進期別欄——期別值閘只認月份會
                # 丟掉它（2026-10-21 意圖探針同句 3 次有 2 次這樣填）。值是封閉語法的起訖 ⇒ 改走起訖欄的值閘
                # （仍須在客人原話裡）；⛔ 由程式判斷客人在講哪一期。
                acc.violations.append(_wc.V_PICK_RIGHT_PERIOD_AS_RANGE)
                f = range_f
            value, dropped = await self._write_draft_turn_gate(acc, identity, f, raw_value, from_intent=True)
            if value is None:
                # A+ 片 AP-2（Q2）：值閘拒收（有記 violation；空值不算）⇒ 使用者句子的值被丟。
                if dropped:
                    wd.user_value_dropped = True
                continue
            provided.add(f.key)
            wd.touched.add(f.key)
            wd.merged = True
            draft["fields"][f.key] = value
            if name_rule == "new":
                self._write_candidates_name_mark(acc, name_rule)
        self._write_draft_persist(acc, agent_state)
        return provided

    async def _dialog_act_not_field_answer(self, acc: TurnAccumulator, agent_state: dict) -> bool:
        """E 片（E-R13）：追問欄位中（回合開始已有草稿、上一回合程式追問了欄位），當句不是欄位答覆 ⇒
        ⛔ 意圖抽值合併、⛔ 整句填入，草稿原樣保留（含追問中的欄位）。判斷只看 AI 標籤（⛔ 詞表）：
        - `wants_human` ⇒ 不是答覆（程式轉人出口另行處理）；
        - `resolved` ⇒ 另發一次同輸入的標籤確認呼叫：確認也是 `resolved`／`wants_human` 或確認未完成 ⇒ 不是答覆、
          程式依草稿重問缺欄（`fill_reask`）；確認為 `none` ⇒ 是答覆；
        - 標籤未完成、失敗或解析不出 ⇒ 不是答覆、程式重問缺欄（⚠️ 勿改回整句填入：會把「ok thx」「我想找真人客」
          填進欄位出卡）；
        - `none` ⇒ 是答覆（照現行）。
        標籤呼叫與寫入意圖呼叫分開 ⇒ 第一次標籤未完成時至多再等 1 秒（同決定點 (c) 的上限，以回合剩餘期限為界）。
        同回合第二次呼叫回第一次的判定。開關 off、沒有標籤呼叫（影子回合）⇒ 照現行。"""
        wd = acc.write_draft
        if (wd is None or wd.draft is None or not wd.had_draft or not wd.asked
                or not self._closing_active() or acc.dialog_act_call is None):
            return False
        cached = getattr(acc, "_dialog_act_field_decision", None)
        if cached is not None:
            return cached
        await self._dialog_act_settle_wait(acc)
        label = self._dialog_act_label(acc)
        acc.violations.append(f"{WF.V_DIALOG_ACT_FIELD_LABEL_PREFIX}{label}")
        reask = False
        if label is None:
            acc.violations.append(WF.V_DIALOG_ACT_FIELD_UNSETTLED_REASK)
            reask = True
        elif label == WF.DIALOG_ACT_RESOLVED:
            confirm = await self._dialog_act_field_confirm(acc)
            acc.violations.append(f"{WF.V_DIALOG_ACT_FIELD_CONFIRM_PREFIX}{confirm}")
            if confirm == WF.DIALOG_ACT_NONE:
                acc._dialog_act_field_decision = False
                return False
            reask = True
        elif label != WF.DIALOG_ACT_WANTS_HUMAN:
            acc._dialog_act_field_decision = False
            return False
        acc._dialog_act_field_decision = True
        acc.violations.append(WF.V_DIALOG_ACT_FILL_SKIPPED)
        # `_write_draft_begin` 回合開始已取走 `asked`，這裡放回，下一句照現行整句填入（缺欄追問問的就是這一欄）。
        wd.draft["asked"] = list(wd.asked)
        AgentSession(agent_state).write_write_draft(wd.draft)
        if reask:
            wd.fill_reask = True
            wd.activity = True
        return True

    async def _dialog_act_field_confirm(self, acc: TurnAccumulator) -> Optional[str]:
        """同輸入（`acc.dialog_act_call.kwargs`）再發一次標籤呼叫，至多等 `DIALOG_ACT_FIELD_CONFIRM_WAIT_S`
        （以回合剩餘期限為界）；回標籤值，未完成／失敗／解析不出 ⇒ `None`。當場收尾：token 計入本回合、記
        `dialog_act_confirm_call`（未完成 ⇒ 取消並以輸入字元估算計入、另記 `dialog_act_confirm_call_cancelled`）。"""
        first = acc.dialog_act_call
        kwargs = getattr(first, "kwargs", None)
        if kwargs is None:
            return None

        async def _call() -> Any:
            return await self.provider.async_client.chat.completions.create(**kwargs)

        call = _DialogActCall(
            asyncio.create_task(_call()), model=self._model,
            input_chars=sum(len(m["content"]) for m in kwargs["messages"]),
            registry={}, trace_id=acc.trace_id,
        )
        remaining = self.budget.deadline_s - (self._clock() - acc.start)
        await asyncio.wait({call.task}, timeout=max(0.0, min(DIALOG_ACT_FIELD_CONFIRM_WAIT_S, remaining)))
        label: Optional[str] = None
        task = call.task
        if task.done() and not task.cancelled() and task.exception() is None:
            result = task.result()
            try:
                label = WF.parse_dialog_act_content(result.choices[0].message.content)
            except Exception:  # noqa: BLE001 — 回應形狀不對 ⇒ 標籤未提供
                label = None
        pt, ct, marks = call.settle()
        acc.prompt_tokens += pt
        acc.completion_tokens += ct
        acc.violations.append(WF.V_DIALOG_ACT_CONFIRM_CALL)
        if WF.V_DIALOG_ACT_CALL_CANCELLED in marks:   # `_DialogActCall.settle` 已換成標籤呼叫的標記名
            acc.violations.append(WF.V_DIALOG_ACT_CONFIRM_CALL_CANCELLED)
        return label

    async def _write_draft_fill_answer(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str, provided: set,
    ) -> None:
        """W1b §8.5-2 整句填入：上一回合程式追問**恰好一個**欄位、且該欄位為 `user_words`
        來源、`text` 型、非名稱欄位（`NAME_KEYS`）⇒ 以當句原文填入（過 `sanitize_data_piece`、
        超過長度上限 ⇒ 拒收、⛔ 截斷，安全處置 Q-c）。同欄優先序：意圖呼叫值已通過值閘
        （`provided`）⇒ 用它，不整句填。呼叫端已排除凍結回合與「意圖呼叫回傳另一支寫入動作」
        （安全處置 1a）。
        F12 r6 復原第 5 輪 §11.15.3 第 1 點（R19-2；Q15-1、Q15-2）：回合開始時候選集已選定或已撤回、仍綁定本草稿
        （`post_pick_start`）⇒ ⛔ 整句填入（所有文字欄）；追問欄位只收意圖抽出、過值閘的值，沒抽到 ⇒ 程式照現行追問。"""
        wd = acc.write_draft
        if wd is None or wd.draft is None or len(wd.asked) != 1:
            return
        if wd.post_pick_start:
            return
        if await self._dialog_act_not_field_answer(acc, agent_state):
            return
        key = wd.asked[0]
        f = WF.FORMS[wd.draft["action"]].field(key)
        if (f is None or f.source != WF.SOURCE_USER_WORDS or f.kind != "text"
                or key in WF.NAME_KEYS or key in provided):
            return
        if wd.fill_active:
            # 填欄只填答覆 B4（§4.1）：寫入回合 ⛔ 整句填入，改填程式從原句切出的答覆段原字（⛔ 用模型回的字串）；
            # 只在追問回合、草稿仍是回合開始那份時；資料段未知 ⇒ 不填（B6 由程式重問）；答覆段為空 ⇒ 不填。
            if not self._fill_followup_now(wd):
                return
            if self._fill_data_unknown(wd):
                self._fill_mark(acc, WF.V_FILL_DATA_TEXT_UNKNOWN)
                return
            if wd.fill_answer is None:
                return
            value = sanitize_data_piece(wd.fill_answer).strip()
        else:
            value = sanitize_data_piece(user_message).strip()
        if not value:
            return
        if len(value) > WF.value_max_len(f):
            # A+ 片 AP-2（Q2）：整句填入因超過長度上限被拒收 ⇒ 使用者句子的值被丟。
            wd.user_value_dropped = True
            return
        wd.activity = True
        wd.filled = True
        wd.touched.add(key)
        wd.draft["idle_turns"] = 0
        wd.draft["fields"][key] = value
        acc.violations.append(WF.V_ANSWER_FILLED)
        if wd.fill_active:
            acc.violations.append(WF.V_FILL_ANSWER_SEGMENT)
        self._write_draft_persist(acc, agent_state)

    async def _write_draft_merge_model_confirm(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, raw_args: Any,
    ) -> None:
        """模型**自己**呼叫 `confirm.request` 的參數合併進草稿——只取模型原始參數
        （任何 `_apply_*`／`_prepare_closed_action` 就地改寫之前），過同一道值閘；
        `system` 來源鍵（系統解析的編號、原／新到期日）與表外鍵一律不進。
        ⚠️ 這一次呼叫本身 ⛔ 改（非目標：gpt-6-luna 現行出卡路徑）；這裡的值只供之後的回合用，
        故 ⛔ 計入本回合的觸發條件（那一次呼叫已經用這些值執行過了）。
        W1b：凍結回合（§8.5-3「草稿除 `asked` 清空外原樣保留」）不合併。"""
        wd = acc.write_draft
        if wd is None or wd.frozen:
            return
        payload = _payload_of(raw_args)
        action = payload.get("action") if payload is not None else None
        form = WF.FORMS.get(action) if isinstance(action, str) else None
        if form is None or not self._write_draft_visible(identity, action):
            return
        wd.activity = True
        draft = self._write_draft_target(acc, action, from_intent=False)
        for key, raw in payload.items():
            f = form.field(key) if isinstance(key, str) else None
            if f is None or f.source != WF.SOURCE_USER_WORDS or raw is None:
                continue
            value, _dropped = await self._write_draft_turn_gate(acc, identity, f, raw)
            if value is not None:
                draft["fields"][f.key] = value
        self._write_draft_persist(acc, agent_state)

    def _write_proposal_active(self) -> bool:
        """A+ 片 AP-0：`AGENT_WRITE_DRAFT`、`AGENT_WRITE_LIFECYCLE`、`AGENT_WRITE_PROPOSAL` 三者皆 on。"""
        return bool(getattr(self, "_write_draft_on", False)
                    and getattr(self, "_write_lifecycle_on", False)
                    and getattr(self, "_write_proposal_on", False))

    def _write_candidates_active(self) -> bool:
        """`AGENT_WRITE_CANDIDATES` on，且 A+ 三開關皆 on（候選集只由程式依草稿
        出卡的路徑寫）。off ⇒ 候選所有分支都不進、`write_candidates` 鍵不讀不寫。"""
        return bool(getattr(self, "_write_candidates_on", False) and self._write_proposal_active())

    def _pick_right_active(self) -> bool:
        """「選對紀錄」片：`AGENT_PICK_RIGHT` on 且 A-2a 生效。off ⇒ 本片所有分支都不進（與 A-2a 逐字相同）。"""
        return bool(getattr(self, "_pick_right_on", False) and self._write_candidates_active())

    def _name_lenient_active(self) -> bool:
        """F12：`AGENT_NAME_LENIENT` on 且 A-2a 生效。off ⇒ 不建脈絡、`confirm.request` 不收到 `name_lenient`
        （0 次模型呼叫、0 次額外查詢，與現行逐字相同）。"""
        return bool(getattr(self, "_name_lenient_on", False) and self._write_candidates_active())

    def _name_lenient_ctx(
        self, acc: TurnAccumulator, agent_state: dict, document: Any, action: Any,
        *, identity: Optional[Identity] = None,
    ) -> Optional["NM.NameLenientTurn"]:
        """本回合的名稱寬鬆比對脈絡——條件同 `_write_candidates_eligible`（候選集可寫的那幾種
        回合：非文件回合、非文件暫存回合、非點選範圍回合、非影子回合、草稿存在且動作相同）；呼叫端另限
        「程式依草稿發出的 `confirm.request`」或 B2 (3)。不合 ⇒ `None`（不觸發寬鬆比對）。
        模型呼叫走服務既有 provider（同意圖判斷呼叫、判讀閘；⛔ 自讀金鑰），token 計入本回合。

        r4：脈絡是 `confirm.NameLenientTurnCtx`——`user_texts` 即時讀 `wd.user_texts`（(甲) R4 整句來源；
        ⛔ 另存原句）、`typed`（本回合打字 ⇒ (乙) 缺名稱觸發才可能發生）、`reask_key`（上一回合「找不到
        這個名稱」追問的名稱欄）。(甲)(乙) 共用這一份的 `run_once`（每回合 ≤1 次寬鬆、≤1 次模型呼叫）。

        r5 (丙)：`program_selected` 是純讀判斷（⛔ 查 DB、⛔ 寫狀態、⛔ 記 trace）——本回合選定成立（`wd.picked`）、
        候選集已選定或已撤回（F12 r6）、「選對紀錄」已選物件（`_pick_right_scope_pick`）、綁定卡帶著的選定
        （`_write_candidates_bound_card_pick`）任一成立 ⇒ `True`。脈絡每回合建一次，`identity` 取第一次建立時
        呼叫端給的；沒給 ⇒ 恆 `True`（(丙) 不觸發，fail-closed）。"""
        if not self._name_lenient_active():
            return None
        if document is not None or document_writable_action(document) is not None:
            return None
        if _document_carry_of(agent_state) is not None:
            return None
        if agent_state.get(SELECT_SCOPE_KEY) is not None or self.readonly_view:
            return None
        wd = acc.write_draft
        if wd is None or not isinstance(wd.draft, dict) or wd.draft.get("action") != action:
            return None
        if wd.name_lenient is None:
            def _usage(pt: int, ct: int) -> None:
                acc.prompt_tokens += pt
                acc.completion_tokens += ct

            def _model_call() -> None:
                acc.llm_calls += 1

            def _program_selected(_ident=identity) -> bool:
                if _ident is None or wd.picked:
                    return True
                cands = wd.candidates
                if isinstance(cands, dict) and (cands.get("picked") is not None
                                                or _wc.is_withdrawn(cands)):
                    # F12 r6：已撤回同已選定（⛔ 依名稱重新解析；重列由出卡入口的關口做）。
                    return True
                if self._pick_right_scope_pick(acc, _ident) is not None:
                    return True
                draft = wd.draft
                return (isinstance(draft, dict)
                        and self._write_candidates_bound_card_pick(_ident, agent_state, draft) is not None)

            wd.name_lenient = NameLenientTurnCtx(
                create_factory=lambda: self.provider.async_client.chat.completions.create,
                model=self._model, reasoning_effort=self._reasoning_effort,
                user_message=wd.user_message, touched=_NameSaidThisTurn(wd),
                remaining_s=lambda: self.budget.deadline_s - (self._clock() - acc.start),
                marks=acc.violations, on_usage=_usage, on_model_call=_model_call,
                user_texts=lambda: wd.user_texts,
                typed=_name_lenient_typed_turn(wd),
                reask_key=_name_lenient_reask_key(wd),
                program_selected=_program_selected,
            )
        return wd.name_lenient

    def _name_lenient_mark_not_found(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, action: Any,
        field_key: str, document: Any,
    ) -> Optional[str]:
        """寬鬆也落空 ⇒ 該欄標為已追問（經 `asked` 唯一寫點 `_write_draft_record_asked`，
        以該欄位的表單標籤）、清掉草稿裡查不到的名稱（⛔ 另存原句或原名稱）。回該欄位標籤（追問對象用）。"""
        form = WF.FORMS.get(action) if isinstance(action, str) else None
        f = form.field(field_key) if form is not None else None
        label = f.label if f is not None else None
        if not isinstance(label, str):
            return None
        self._write_draft_record_asked(
            acc, identity, agent_state,
            ToolResult(ok=False, error="INVALID_INPUT",
                       data={"action": action, "missing_fields": [label]}),
            None, document)
        wd = acc.write_draft
        if (wd is not None and isinstance(wd.draft, dict) and wd.draft.get("action") == action
                and isinstance(wd.draft.get("fields"), dict)
                and wd.draft["fields"].pop(field_key, None) is not None):
            self._write_draft_persist(acc, agent_state)
        return label

    def _name_lenient_reask_labels(self, acc: TurnAccumulator, action: Any, labels: Any) -> Any:
        """下一句只補其他欄位 ⇒ 只重問名稱：上一回合「找不到這個名稱」
        出口把名稱欄 K 標為已追問（`asked == [K]`），而 K 所屬的「擇一必填」要求在追問時印的是**另一個欄位**
        的標籤（手動帳單：物件 `estate_name` 與合約 `contract_ref` 擇一、追問印「合約」）⇒ 本回合缺欄追問改印
        K 的標籤（重問同一個名稱欄）。其餘（開關未生效、`asked` 不是單一名稱鍵、K 本來就在追問組裡、
        標籤裡沒有該組的標籤）⇒ 原樣回傳（與改動前逐字相同）。"""
        if not isinstance(labels, list) or not self._name_lenient_active():
            return labels
        wd = acc.write_draft
        asked = list(wd.asked) if wd is not None else []
        form = WF.FORMS.get(action) if isinstance(action, str) else None
        if form is None or len(asked) != 1 or asked[0] not in WF.NAME_KEYS:
            return labels
        key = asked[0]
        f = form.field(key)
        if f is None:
            return labels
        out = list(labels)
        for req in form.requirements:
            if (key,) not in req.required_any_of or key in req.ask_group:
                continue
            group_labels = ([req.group_label] if req.group_label is not None else
                            [form.field(k).label for k in req.ask_group if form.field(k) is not None])
            if not any(lb in out for lb in group_labels):
                continue
            replaced: list = []
            for lb in out:
                target = f.label if lb in group_labels else lb
                if target not in replaced:
                    replaced.append(target)
            out = replaced
        return out

    def _name_lenient_not_found_exit(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
        tool_result: Any, document: Any,
    ) -> Optional[TurnResult]:
        """程式依草稿發出的 `confirm.request` 回「找不到這個名稱」⇒ 固定句
        `NAME_NOT_FOUND_TEXT` 結束回合（⛔ 回顯原話、⛔ 交模型改寫），該欄標為已追問、清掉查不到的名稱。"""
        field_key = is_name_not_found(tool_result)
        if field_key is None:
            return None
        data = tool_result.data if isinstance(tool_result.data, dict) else {}
        label = self._name_lenient_mark_not_found(
            acc, identity, agent_state, data.get("action"), field_key, document)
        acc.violations.append(NM.V_NAME_LENIENT_NOT_FOUND_EXIT)
        return self._finish_confirm_turn(
            ask_target=WF.ask_target_for_missing([label]) if label else None,
            agent_state=agent_state,
            user_message=user_message,
            trace_id=acc.trace_id,
            start=acc.start,
            kind="ask",
            outcome=make_outcome("clarifying", expects="text"),
            answer=NM.NAME_NOT_FOUND_TEXT,
            pending_id=None,
            tool_calls=acc.tool_call_records,
            violations=acc.violations,
            llm_calls=acc.llm_calls,
            prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens,
        )

    def _pick_right_scope_pick(self, acc: TurnAccumulator, identity: Identity) -> Optional[dict]:
        """「選對紀錄」片 §4.1-1：本回合的候選集是「已選物件的帳單候選」、仍綁定本草稿、未選定 ⇒ 該物件的
        程式專用選定（`write_candidates.scope_pick_of`；改講金額／期間時只在同一個物件重查）；其餘 ⇒ `None`。"""
        if not self._pick_right_active():
            return None
        wd = acc.write_draft
        cands = wd.candidates if wd is not None else None
        if cands is None or not self._write_candidates_bound(cands, identity, wd.draft):
            return None
        return _wc.scope_pick_of(cands)

    def _pick_right_said(self, draft: Any) -> tuple:
        """延期繳費草稿裡客人講的比對值 `(said_amount, said_range)`（`to_payload` 後；沒講 ⇒ `None`）。"""
        if not isinstance(draft, dict) or draft.get("action") != WF.BILL_DUE_EXTEND_FORM.action:
            return None, None
        values = WF.to_payload(draft["action"], draft.get("fields") or {})
        amount = values.get(_PR_SAID_AMOUNT)
        if isinstance(amount, bool) or not isinstance(amount, int):
            amount = None
        rng = values.get(_PR_SAID_RANGE)
        return amount, (rng if isinstance(rng, str) and rng else None)

    def _pick_right_said_reset(self, acc: TurnAccumulator, agent_state: dict) -> None:
        """「選對紀錄」片 §4.2-1：延期繳費草稿的物件或期別在本回合變了 ⇒ 客人先前講的比對值清掉
        （本回合使用者又講了新的值——在 `touched` 裡——則保留新的）。"""
        wd = acc.write_draft
        if wd is None or wd.pr_anchor is None or not self._pick_right_active():
            return
        draft = wd.draft
        if not isinstance(draft, dict) or draft.get("action") != WF.BILL_DUE_EXTEND_FORM.action:
            return
        fields = draft.get("fields")
        if not isinstance(fields, dict):
            return
        anchor = (fields.get("estate_name"), fields.get("period"))
        if anchor == wd.pr_anchor:
            return
        wd.pr_anchor = anchor
        dropped = False
        for key in (_PR_SAID_AMOUNT, _PR_SAID_RANGE):
            if key in fields and key not in wd.touched:
                fields.pop(key, None)
                dropped = True
        if dropped:
            self._write_draft_persist(acc, agent_state)

    def _pick_right_typed_mismatch(self, acc: TurnAccumulator, cands: dict,
                                   chosen: str) -> Optional[tuple]:
        """「選對紀錄」片 §4.2-3（業主裁 Q4 的打字那一半）：打字選定的帳單與客人先前講的金額／計費期間
        不符 ⇒ 不符的標記（可能為空：列不在本回合附上的候選列裡，無從比對 ⇒ 一律視為不符，fail-closed）；
        相符、沒講、不是延期帳單候選 ⇒ `None`。"""
        if not self._pick_right_active():
            return None
        if cands.get("type") != _wc.TYPE_BILL or cands.get("action") != WF.BILL_DUE_EXTEND_FORM.action:
            return None
        wd = acc.write_draft
        said_amount, said_range = self._pick_right_said(wd.draft if wd is not None else None)
        if said_amount is None and said_range is None:
            return None
        row = wd.pick_rows.get(chosen) if wd is not None else None
        if not isinstance(row, dict):
            return ()
        marks = _wc.said_mismatch_marks(row, said_amount=said_amount, said_range=said_range)
        return marks if marks else None

    async def _write_proposal_merge(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, raw_args: Any,
    ) -> bool:
        """A+ 片 AP-1 (1)：模型自己呼叫 `confirm.request` 的參數**只當提議**合併進草稿，觸發語義與
        意圖合併相同（安全審查 1-8）：值閘不變（`from_intent=False`）；新建草稿算 `created`；通過
        值閘的鍵加入 `touched` 並設 `merged`；本回合前置查詢命中的物件名稱優先、與物件名重疊的
        文字值丟棄（比照 `_write_draft_merge_intent` 的 W1c 規則）。之後 `_write_draft_decide` 取用的
        意圖結果後合併，同欄以意圖為準。被值閘丟掉的值 ⛔ 設 `user_value_dropped`（Q2：模型提議
        不算）。

        回 `False` ⇒ 提議的動作不在 `FORMS` 或看不到（呼叫端回封閉結果 `NO_MATCH`、不觸發）。
        凍結回合（§8.5-3）⇒ 不合併（回 `True`：動作合法，觸發與否交 `_write_draft_decide`）。

        巢狀提議 `{action, payload:{…}}` **解一層**——外層除 `action` 外
        沒有任何 `form.keys` 鍵（含系統來源鍵；外層帶任何表單鍵就不解），且 `payload` 是 dict 或能解析
        成 dict 的 JSON 字串 ⇒ 以內層 dict 的表單鍵合併（值閘、W1c 名稱規則、`touched`／`merged` 照上）。
        內層**有 `action` 鍵**（不論值）且值 ≠ 外層 ⇒ 回 `False`（`NO_MATCH`、不觸發）。只解一層（內層的
        `payload` 不是表單鍵，自然略過）。解開與內層動作比對都在 `wd.activity`／`_write_draft_target`
        **之前**（安全審查 r3 F1：動作不合 ⇒ 草稿、`created` 都不變）；內層字串解析接 `TypeError`、
        `ValueError`、`RecursionError`（r3 F3），失敗 ⇒ 視同不解開。解開邏輯只在這裡（⛔ 改 `_payload_of`，
        它是文件回合判動作、照片處理、`_write_draft_record_asked` 共用的）。"""
        wd = acc.write_draft
        payload = _payload_of(raw_args)
        action = payload.get("action") if payload is not None else None
        form = WF.FORMS.get(action) if isinstance(action, str) else None
        if form is None or not self._write_draft_visible(identity, action):
            return False
        source = payload
        unwrapped = False
        if not any(k in form.keys for k in payload if k != "action"):
            inner = payload.get("payload")
            if isinstance(inner, str):
                try:
                    inner = json.loads(inner)
                except (TypeError, ValueError, RecursionError):
                    inner = None
            if isinstance(inner, dict):
                if "action" in inner and inner.get("action") != action:
                    return False
                source = inner
                unwrapped = True
        if unwrapped:
            acc.violations.append(WF.V_WRITE_PROPOSAL_UNWRAPPED)
        if wd.frozen or wd.submitted_edit:
            return True
        wd.activity = True
        draft = self._write_draft_target(acc, action, from_intent=True)
        name_hit = (wd.caught_name is not None
                    and draft["fields"].get("estate_name") == wd.caught_name)
        name_spans = ([_name_overlap_key(s) for s in (wd.caught_name, wd.caught_segment) if s]
                      if name_hit else [])
        # 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.3 第 4 點）：寬回合、意圖尚未取用 ⇒ 進逐值迴圈之前
        # 等意圖一次讀資料段（每回合只等一次；⛔ 取用意圖、⛔ 記標記）。非寬回合不動。
        await self._fill_wide_await_data(acc)
        for key, raw in source.items():
            f = form.field(key) if isinstance(key, str) else None
            if f is None or f.source != WF.SOURCE_USER_WORDS or raw is None:
                continue
            if name_hit and f.key == "estate_name":
                continue
            # F12 r6（§11.4 第 2 點「判定順序」）：已選定或已撤回 ⇒ 名稱欄值暫存不併，留到拿到 `pick_id` 之後。
            name_rule = self._write_candidates_name_rule(acc, identity, f, raw, defer=True)
            if name_rule == "defer":
                wd.deferred_names.append((f.key, raw))
                continue
            if name_rule == "collect":
                # 第 5 輪：收集期間（只在 `_write_draft_decide` 單次決定內）的提議名稱同暫存處理。
                wd.collected_names.append(("deferred", raw))
                continue
            if name_rule in ("drop", "same"):
                self._write_candidates_name_mark(acc, name_rule)
            if name_rule == "drop":
                continue
            if (name_spans and f.kind in ("text", "period") and isinstance(raw, str)
                    and raw.strip()
                    and any(_name_overlap_key(raw) in span for span in name_spans)):
                acc.violations.append(WF.V_VALUE_OVERLAPS_NAME)
                continue
            value, _dropped = await self._write_draft_turn_gate(acc, identity, f, raw)
            if value is None:
                continue
            wd.touched.add(f.key)
            wd.merged = True
            draft["fields"][f.key] = value
            if name_rule == "new":
                self._write_candidates_name_mark(acc, name_rule)
        self._write_draft_persist(acc, agent_state)
        return True

    async def _write_candidates_deferred_names(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
    ) -> None:
        """F12 r6（§11.4 第 2 點「判定順序」）：`_write_proposal_merge` 暫存不併的名稱欄值，在拿到 `pick_id`（意圖
        結果取用、改選目標算出）之後依名稱合併規則處理——丟棄者記 `write_candidate_name_kept`；其餘照模型提議的
        合併（值閘 `from_intent=False`、W1c 名稱規則、`touched`／`merged`）。只處理一次（處理完即清空）。"""
        wd = acc.write_draft
        pending, wd.deferred_names = list(wd.deferred_names), []
        if not pending or wd.draft is None:
            return
        draft = wd.draft
        form = WF.FORMS.get(draft.get("action"))
        if form is None:
            return
        name_hit = (wd.caught_name is not None
                    and draft["fields"].get("estate_name") == wd.caught_name)
        name_spans = ([_name_overlap_key(s) for s in (wd.caught_name, wd.caught_segment) if s]
                      if name_hit else [])
        merged_any = False
        for key, raw in pending:
            f = form.field(key)
            if f is None or f.source != WF.SOURCE_USER_WORDS:
                continue
            if name_hit and f.key == "estate_name":
                continue
            name_rule = self._write_candidates_name_rule(acc, identity, f, raw, defer=False)
            if name_rule == "collect":
                # 第 5 輪 §11.15.3 第 6 點：暫存名稱同樣先收集，與意圖結果的名稱一起決定去向。
                wd.collected_names.append(("deferred", raw))
                continue
            if name_rule in ("drop", "same"):
                self._write_candidates_name_mark(acc, name_rule)
            if name_rule == "drop":
                continue
            if (name_spans and f.kind in ("text", "period") and isinstance(raw, str)
                    and raw.strip()
                    and any(_name_overlap_key(raw) in span for span in name_spans)):
                acc.violations.append(WF.V_VALUE_OVERLAPS_NAME)
                continue
            value, _dropped = await self._write_draft_turn_gate(acc, identity, f, raw)
            if value is None:
                continue
            wd.touched.add(f.key)
            wd.merged = True
            draft["fields"][f.key] = value
            merged_any = True
            if name_rule == "new":
                self._write_candidates_name_mark(acc, name_rule)
        if merged_any:
            self._write_draft_persist(acc, agent_state)

    async def _write_candidates_apply_name(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, cf: Any,
        source: str, raw: Any,
    ) -> bool:
        """第 5 輪 §11.15.3 第 6 點決定 3：「改講新名稱」的名稱 N 寫進候選集那一欄（過既有值閘；W1c 名稱規則同意圖
        合併）。寫進且因此解綁 ⇒ `True`（呼叫端清候選集、記 `write_candidate_name_new`；觸發條件 `merged` ⇒ 程式
        依草稿重查新名稱）；值閘不過、或寫進後仍綁定 ⇒ `False`（呼叫端當作沒有 N）。使用者句子的值（意圖結果、
        `new_name`、被擋下動作）被值閘丟掉 ⇒ `user_value_dropped`（主模型提議不算，比照 A+ AP-2 Q2）。"""
        wd = acc.write_draft
        draft = wd.draft
        name_hit = (wd.caught_name is not None
                    and draft["fields"].get("estate_name") == wd.caught_name)
        if name_hit and cf.key == "estate_name":
            return False
        name_spans = ([_name_overlap_key(s) for s in (wd.caught_name, wd.caught_segment) if s]
                      if name_hit else [])
        if (name_spans and isinstance(raw, str) and raw.strip()
                and any(_name_overlap_key(raw) in span for span in name_spans)):
            acc.violations.append(WF.V_VALUE_OVERLAPS_NAME)
            return False
        from_user = source != "deferred"
        value, dropped = await self._write_draft_turn_gate(acc, identity, cf, raw, from_intent=from_user)
        if value is None:
            if from_user and dropped:
                wd.user_value_dropped = True
            return False
        wd.activity = True
        draft["idle_turns"] = 0
        draft["fields"][cf.key] = value
        wd.touched.add(cf.key)
        wd.merged = True
        self._write_draft_persist(acc, agent_state)
        return not self._write_candidates_bound(wd.candidates, identity, draft)

    async def _write_candidates_replay_names(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, cf: Any,
    ) -> None:
        """第 5 輪 §11.15.3 第 6 點決定 4、5：沒有成立的新名稱 ⇒ 收集到的名稱值照現行名稱合併規則處理（`repick_target`
        已設成 X）：丟棄者記 `write_candidate_name_kept`；與草稿現值相同者照現行合併（值不變、仍綁定）；被擋下動作的
        名稱一律丟棄（§11.15.3 第 4 點：候選集內講法或不是本回合講的）；規則判「新名稱」者已在決定 3 試過（值閘不過）
        ⇒ ⛔ 再併。"""
        wd = acc.write_draft
        pending, wd.collected_names = list(wd.collected_names), []
        draft = wd.draft
        merged_any = False
        for source, raw in pending:
            if source == "blocked":
                self._write_candidates_name_mark(acc, "drop")
                continue
            rule = self._write_candidates_name_rule(acc, identity, cf, raw, defer=False)
            if rule in ("drop", "same"):
                self._write_candidates_name_mark(acc, rule)
            if rule != "same":
                continue
            value, _dropped = await self._write_draft_turn_gate(
                acc, identity, cf, raw, from_intent=source == "intent")
            if value is None:
                continue
            wd.touched.add(cf.key)
            wd.merged = True
            draft["fields"][cf.key] = value
            merged_any = True
        if merged_any:
            self._write_draft_persist(acc, agent_state)

    async def _write_candidates_post_pick_names(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
        intent: Any, *, blocked: bool, fields_before: Optional[dict],
    ) -> set:
        """回合開始時候選集已選定或已撤回、仍綁定本草稿，
        且意圖判斷結果解析成功（含 `action=none`）的回合——**單次**意圖呼叫的結果，由程式依序決定（DSP-091：AI 只回理解
        結果）。呼叫端已排除「另一動作帶非名稱值」（決定 1：照 §11.14 第 3 點換動作，走現行）。

        1. 名稱值先收集、⛔ 合併（主模型提議暫存的、意圖結果的名稱欄、被擋下動作 `blocked` 的同一欄名稱）；非名稱欄照
           現行合併（被擋下動作的欄位 ⛔ 合併，記 `write_candidate_action_kept`）；整句填入照 `_write_draft_fill_answer`
           （第 1 點：選定後不跑）；「選對紀錄」比對值依物件／期別重設。
        2. 驗過且未被退回的改選目標 X：`_write_candidates_typed_target`（已撤回：`pick_id` ∈ `ids`；整句只打 `ids` 內
           編號；已選定只剩整句編號）≠ 現選定，且 `_write_candidates_refusal` 不退回（分不出、金額期間不符——讀的是本回合
           非名稱欄合併後的比對值）。
        3. 改講新名稱：意圖結果或暫存的名稱欄值算新名稱（`_write_candidates_name_is_new`）；被擋下動作的名稱候選集外、
           本回合講 ⇒ 算。**回合開始已選定**（`wd.cmd_scope_start`）⇒ 這一步不收任何名稱（計畫 `plan-post-pick-commands-
           20261024.md` §4.3 第 7 點：沒設 `cmd_offered` 的已選定回合）。
        4. 決定：有 X 且有新名稱 ⇒ 矛盾（已選定 ⇒ 撤回並重列同一份 `ids`；已撤回 ⇒ 重列；所有名稱值
           丟棄、⛔ 解綁；記 `write_candidate_name_conflict`；已選定回合因 `cmd_scope_start` 不會到這條）；有新名稱 ⇒
           寫進候選集那一欄、解綁（清候選集）、依新名稱重查（記 `write_candidate_name_new`；X 被退回的標記照記）；其餘 ⇒
           `repick_target`＝X、名稱照現行規則處理後交 `_write_candidates_typed`（有 X ⇒ 改選；X 被退回 ⇒ 重列）。
        回本回合意圖合併過值閘的鍵（同 `_write_draft_merge_intent`）。"""
        wd = acc.write_draft
        cands = wd.candidates
        form = WF.FORMS.get(wd.draft.get("action"))
        cf = form.field(cands.get("field")) if form is not None else None
        provided: set = set()
        wd.collected_names = []
        wd.name_collect = True
        try:
            await self._write_candidates_deferred_names(acc, identity, agent_state)
            if blocked:
                acc.violations.append(_wc.V_CANDIDATE_ACTION_KEPT)
                for item in getattr(intent, "fields", None) or []:
                    value = getattr(item, "value", None)
                    if (cf is not None and getattr(item, "key", None) == cf.key
                            and isinstance(value, str) and value.strip()):
                        wd.collected_names.append(("blocked", value))
            elif intent is not None:
                provided = await self._write_draft_merge_intent(acc, identity, agent_state, intent)
        finally:
            wd.name_collect = False
        if not blocked:
            await self._write_draft_fill_answer(acc, agent_state, user_message, provided)
        self._pick_right_said_reset(acc, agent_state)
        session = AgentSession(agent_state)
        if cf is None or not self._write_candidates_bound(cands, identity, wd.draft):
            # 理應不發生（名稱未併、動作未換）；fail-closed：同 `_write_candidates_typed` 的解綁處置。
            wd.collected_names = []
            session.clear_write_candidates()
            wd.candidates = None
            return provided
        changed = (wd.draft.get("fields") or {}) != (fields_before or {})
        picked = cands.get("picked")
        target = self._write_candidates_typed_target(wd, cands, user_message, changed=changed)
        if target is not None and target == picked:
            target = None
        refused = (self._write_candidates_refusal(acc, cands, target, user_message)
                   if target is not None else None)
        x = target if refused is None else None
        names: list = []
        for source, raw in wd.collected_names:
            if wd.cmd_scope_start:
                # 選定後回合改指令式：回合開始已選定 ⇒ 這個函式不收任何新名稱（名稱值一律規則；
                # 被擋下動作的 `ok` 判定與 `_write_candidates_name_is_new` 都不跑），故不會到矛盾、新名稱兩條決定。
                continue
            if source == "blocked":
                ok = (not self._write_candidates_in_set(wd, cands, raw)
                      and _name_said_in_message(raw, wd.user_message))
            else:
                ok = self._write_candidates_name_is_new(wd, cands, raw)
            if ok:
                names.append((source, raw))
        if x is not None and names:
            # 決定 2：矛盾 ⇒ 視同 retract；本回合所有名稱值丟棄、⛔ 解綁（之後同回合的提議名稱也丟，`name_conflict`）。
            wd.name_conflict = True
            wd.collected_names = []
            acc.violations.append(_wc.V_CANDIDATE_NAME_CONFLICT)
            if picked is not None:
                self._write_candidates_withdraw(acc, agent_state, cands)
            else:
                wd.relist = True
                wd.activity = True
            return provided
        for source, raw in names:
            if await self._write_candidates_apply_name(acc, identity, agent_state, cf, source, raw):
                # 決定 3：改講新名稱（含 X 被退回）⇒ 解綁、依新名稱重查（觸發條件 `merged`）。
                wd.collected_names = []
                session.clear_write_candidates()
                wd.candidates = None
                for mark in refused or ():
                    if mark not in acc.violations:
                        acc.violations.append(mark)
                self._write_candidates_name_mark(acc, "new")
                self._pick_right_said_reset(acc, agent_state)
                return provided
        # 決定 4、5：名稱照現行規則（X 有值 ⇒ 丟棄），改選／撤回／重列交現行打字判定。
        wd.repick_target = x
        await self._write_candidates_replay_names(acc, identity, agent_state, cf)
        self._pick_right_said_reset(acc, agent_state)
        await self._write_candidates_typed(
            acc, identity, agent_state, user_message, fields_before=fields_before)
        return provided

    @staticmethod
    def _write_candidates_cmd_code(item: Any) -> str:
        """指令清單一項的 trace 封閉碼：非物件、`op` 非字串或值域外 ⇒ `invalid`（⛔ 記模型原字串）。"""
        op = item.get("op") if isinstance(item, dict) else None
        return op if isinstance(op, str) and op in WF.PICK_TARGET_OP_DOMAIN else "invalid"

    def _write_candidates_cmd_effect(
        self, wd: Any, cands: dict, user_message: Any, item: Any,
    ) -> tuple:
        """選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.3 第 3 點）：一個指令解成效果，程式驗證、⛔ 猜。
        回 `("keep",)`、`("target", X, via)`（`via` 為 `"pick"`／`"nth"`／`"name"`）、`("name", N)`、`("withdraw",)`、`("invalid",)`。
        純判定（⛔ 查 DB、⛔ 寫狀態）。"""
        if not isinstance(item, dict):
            return ("invalid",)
        op, value = item.get("op"), item.get("value")
        if not isinstance(op, str) or op not in WF.PICK_TARGET_OP_DOMAIN or not isinstance(value, str):
            return ("invalid",)
        ids = cands["ids"]
        picked = cands.get("picked")
        if op == WF.PICK_TARGET_OP_CLEAR:
            return ("withdraw",)
        if op == WF.PICK_TARGET_OP_PICK:
            x = value
            if x and x in wd.pick_offered and x in ids:
                return ("keep",) if x == picked else ("target", x, WF.PICK_TARGET_OP_PICK)
            return ("invalid",)
        if op == WF.PICK_TARGET_OP_NTH:
            # NFKC 後整串 `[1-9][0-9]?`（⛔ 去頭尾空白：` 2 `、`+2`、`1_0` 皆無效）；畫面清單＝列候選出口同一個上限 K。
            n_text = unicodedata.normalize("NFKC", value)
            if not _NTH_VALUE_RE.fullmatch(n_text):
                return ("invalid",)
            shown = ids[:self._write_candidates_shown_limit(self._pick_right_active())]
            n = int(n_text)
            if n > len(shown) or any(s not in wd.pick_offered for s in shown):
                return ("invalid",)
            x = shown[n - 1]
            return ("keep",) if x == picked else ("target", x, WF.PICK_TARGET_OP_NTH)
        # name
        name = value.strip()
        key = _name_said_key(name)
        if not name or sanitize_data_piece(name) != name or not key:
            return ("invalid",)
        origin_hit, matched = self._write_candidates_name_hits(wd, cands, name)
        if picked in matched or origin_hit:
            return ("keep",)
        said = _name_said_in_message(name, wd.user_message)
        if len(matched) == 1 and said and matched[0] in ids:
            # 清單裡只有一筆（≠現選定）的系統正名包含這個名稱、且名稱是本句講的
            # （客人原字；擋 AI 依描述猜出正名）⇒ 改選那筆，過「選對紀錄」退回（`via="name"`：分不出不套、金額期間照套）。
            return ("target", matched[0], WF.PICK_TARGET_OP_NAME)
        if matched:
            return ("withdraw",)
        if said:
            return ("name", name)
        return ("invalid",)

    async def _write_candidates_name_precheck(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, cands: dict,
    ) -> bool:
        """`name` 指令已把名稱寫進草稿、將解綁，解綁**之前**用解綁後重查會走的同一組
        查找（`name_precheck_ids`：身分閘 → 精確查找 → 查無才寬鬆，同一把 `run_once` 鍵 ⇒ 重查取同一份、本回合寬鬆模型呼叫
        ≤1）查一次；查到的列編號含現選定 ⇒ `True`（呼叫端還原草稿、候選集與選定不動）。比對編號：estate／contract+
        `contract_ref` ⇒ `picked`；bill ⇒ 物件範圍（`_wc.scope_rows_pick_of`）；contract+`estate_name`（手開帳單一物件多合約）
        ⇒ 選定合約列的 `estate_id`（`wd.offered_rows`）；取不到 ⇒ 不比對（⛔ 出向查找，回 `False`）。其餘（身分閘不過、查找
        失敗、沒比中）⇒ `False`（照現行解綁重查）。唯讀；⛔ 記名稱、編號。"""
        wd = acc.write_draft
        draft = wd.draft
        action, field, cand_type = cands["action"], cands["field"], cands["type"]
        picked = cands.get("picked")
        if cand_type == _wc.TYPE_ESTATE or (cand_type == _wc.TYPE_CONTRACT and field == "contract_ref"):
            lookup_type, compare_id = cand_type, picked
        elif cand_type == _wc.TYPE_BILL:
            scope = _wc.scope_rows_pick_of(cands)
            lookup_type, compare_id = _wc.TYPE_ESTATE, scope["id"] if scope is not None else None
        elif cand_type == _wc.TYPE_CONTRACT and field == "estate_name":
            row = wd.offered_rows.get(picked) if picked is not None else None
            lookup_type = _wc.TYPE_ESTATE
            compare_id = _wc.candidate_id(row.get("estate_id")) if isinstance(row, dict) else None
        else:
            return False
        form = WF.FORMS.get(action)
        cf = form.field(field) if form is not None else None
        name = (draft.get("fields") or {}).get(field)
        if compare_id is None or cf is None or not isinstance(name, str):
            return False
        payload = {"action": action, **WF.to_payload(action, draft.get("fields") or {})}
        ids = await name_precheck_ids(
            identity, action, payload, field=field, cand_type=lookup_type, name=name, missing_label=cf.label,
            name_lenient=self._name_lenient_ctx(acc, agent_state, None, action, identity=identity))
        return bool(ids) and compare_id in ids

    async def _write_candidates_cmd_turn(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
        intent: Any, *, blocked: bool, fields_before: Optional[dict],
    ) -> set:
        """選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.3；DSP-091：AI 只回理解結果，下一步由程式決定）：
        回合開始已選定、仍綁定本草稿、本回合送出指令版 schema（`wd.cmd_offered`）、意圖解析成功、沒換動作。
        ⛔ 呼叫 `_write_candidates_post_pick_names`、`_write_candidates_typed_post_pick`（F1 (k) spy）。

        1. 名稱值一律規則：暫存提議、意圖 `fields` 的名稱欄、被擋下動作的名稱一律丟棄（記 `write_candidate_name_kept`）；
           非名稱欄照現行合併（被擋下動作的欄位 ⛔ 合併，記 `write_candidate_action_kept`）；不整句填入。
        2. 指令逐項解成效果（`_write_candidates_cmd_effect`），取最後一項（空陣列 ⇒ 維持；`target` 缺鍵或不是陣列 ⇒ 無效）；
           整句只打 `ids` 內編號且草稿值沒變 ⇒ 該編號（程式路徑優先於指令）。
        3. 執行：維持 ⇒ 不動；目標 ⇒ `_write_candidates_repick_apply`（選對紀錄退回）；新名稱 ⇒ `_write_candidates_apply_name`
           寫進候選集那一欄、解綁、依新名稱重查（值閘不過 ⇒ 撤回）；撤回或無效 ⇒ 撤回並重列同一份 `ids`。
        回本回合意圖合併過值閘的鍵。trace 只記封閉碼。"""
        wd = acc.write_draft
        cands = wd.candidates
        form = WF.FORMS.get(wd.draft.get("action"))
        cf = form.field(cands.get("field")) if form is not None else None
        provided: set = set()
        await self._write_candidates_deferred_names(acc, identity, agent_state)
        if blocked:
            acc.violations.append(_wc.V_CANDIDATE_ACTION_KEPT)
            for item in getattr(intent, "fields", None) or []:
                value = getattr(item, "value", None)
                if (cf is not None and getattr(item, "key", None) == cf.key
                        and isinstance(value, str) and value.strip()):
                    self._write_candidates_name_mark(acc, "drop")
        elif intent is not None:
            provided = await self._write_draft_merge_intent(acc, identity, agent_state, intent)
            await self._write_draft_fill_answer(acc, agent_state, user_message, provided)
        self._pick_right_said_reset(acc, agent_state)
        session = AgentSession(agent_state)
        if cf is None or not self._write_candidates_bound(cands, identity, wd.draft):
            # 理應不發生（名稱未併、動作未換）；fail-closed：同 `_write_candidates_typed` 的解綁處置。
            session.clear_write_candidates()
            wd.candidates = None
            return provided
        raw = wd.intent_target
        items = raw if isinstance(raw, list) else []
        codes = [self._write_candidates_cmd_code(i) for i in items][:8]
        if not isinstance(raw, list):
            codes, last_code = ["invalid"], "invalid"
        else:
            last_code = self._write_candidates_cmd_code(items[-1]) if items else "none"
        acc.violations.append(_wc.V_CANDIDATE_CMDS_PREFIX + ",".join(codes))
        acc.violations.append(_wc.V_CANDIDATE_CMD_LAST_PREFIX + last_code)
        effect = (self._write_candidates_cmd_effect(wd, cands, user_message, items[-1])
                  if items else (("keep",) if isinstance(raw, list) else ("invalid",)))
        changed = (wd.draft.get("fields") or {}) != (fields_before or {})
        said_target = (self._write_candidates_typed_target(wd, cands, user_message, changed=changed)
                       if not changed else None)
        if said_target is not None:
            effect = ("keep",) if said_target == cands.get("picked") else ("target", said_target, None)
        kind = effect[0]
        if kind == "keep":
            return provided
        if kind == "target":
            self._write_candidates_repick_apply(
                acc, agent_state, cands, effect[1], user_message, via=effect[2])
            return provided
        if kind == "name":
            # 寫名稱前記下草稿狀態；將解綁時先做解綁前查找，含現選定 ⇒ 還原、維持。
            draft = wd.draft
            snapshot = (copy.deepcopy(draft.get("fields") or {}), set(wd.touched), wd.merged, wd.activity,
                        draft.get("idle_turns"))
            if await self._write_candidates_apply_name(acc, identity, agent_state, cf, "intent", effect[1]):
                if await self._write_candidates_name_precheck(acc, identity, agent_state, cands):
                    draft["fields"], wd.touched, wd.merged, wd.activity, draft["idle_turns"] = snapshot
                    self._write_draft_persist(acc, agent_state)
                    acc.violations.append(_wc.V_CANDIDATE_NAME_PRECHECK_KEEP)
                    return provided
                acc.violations.append(_wc.V_CANDIDATE_NAME_PRECHECK_MISS)
                session.clear_write_candidates()
                wd.candidates = None
                self._write_candidates_name_mark(acc, "new")
                self._pick_right_said_reset(acc, agent_state)
                return provided
        if kind == "invalid":
            acc.violations.append(_wc.V_CANDIDATE_CMD_INVALID)
        # 撤回（`clear`、`name` 對到清單內另一筆、新名稱值閘不過）或無效 ⇒ 撤回並重列同一份 `ids`。
        acc.violations.append(_wc.V_CANDIDATE_RETRACT_TYPED)
        self._write_candidates_withdraw(acc, agent_state, wd.candidates if wd.candidates is not None else cands)
        return provided

    async def _write_proposal_handle(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
        user_message: str, document: Any, raw_args: Any,
    ) -> tuple:
        """A+ 片 AP-1 (1)～(4)：模型提議的處置（下一步一律由程式決定）。回 `(kind, value)`：

        - `("program", args)`：程式依草稿發出的 `confirm.request` 參數（`_write_draft_decide` 產出，
          payload＝`{action, **to_payload(草稿)}`、`summary`＝常數）——呼叫端以模型這次的 tool call id 執行；
        - `("exit", None)`：程式固定句出口成立（綁定卡燒不到、卡片還在、修改已送出）——呼叫端記完
          這次 tool call 後以 `_write_proposal_exit` 結束回合；
        - `("no_value", 處置)`：r3 AP-7 (2)——提議沒有任何值進草稿（`_write_proposal_no_value`）——呼叫端
          記完這次 tool call 後以 `_write_proposal_no_value_exit` 結束回合（⛔ 交模型寫回覆）；
        - `("closed", 錯誤碼)`：回模型封閉工具結果（`NO_MATCH`：動作不在 `FORMS` 或看不到，或巢狀提議
          內層動作不合；`HANDLED_BY_PROGRAM`：其餘，含 `write_draft` 為 `None`——⛔ 退回以模型參數執行，
          1-7；凍結回合、本回合已觸發後的同回合第二次提議——AP-R10 收窄）。"""
        wd = acc.write_draft
        if wd is None:
            return "closed", "HANDLED_BY_PROGRAM"
        pre_draft = copy.deepcopy(wd.draft)
        if await self._dialog_act_not_field_answer(acc, agent_state):
            # E 片（E-R13）：AI 把當句標成「不是欄位答覆」（道謝／要真人）⇒ 模型自呼的提議也 ⛔ 合併（⚠️ 勿拿掉：模型會把
            # 「3Q」提議成帳單項目而出卡），由程式回缺欄追問或同卡。在這裡判斷、⛔ 只看
            # 標記：程式優先入口沒成立（意圖等待逾時）時，提議比意圖合併先到。
            no_value = await self._write_proposal_no_value(acc, identity, agent_state, raw_args)
            return ("no_value", no_value) if no_value is not None else ("closed", "HANDLED_BY_PROGRAM")
        if not await self._write_proposal_merge(acc, identity, agent_state, raw_args):
            return "closed", "NO_MATCH"
        message = await self._write_draft_decide(acc, identity, agent_state, user_message, document)
        if message is not None:
            try:
                args = json.loads(message.tool_calls[0].function.arguments)
            except (AttributeError, IndexError, TypeError, ValueError):
                args = None
            if isinstance(args, dict):
                return "program", args
            return "closed", "HANDLED_BY_PROGRAM"
        if wd.submitted_edit:
            # #9g：「修改剛送出的那一筆」⛔ 建草稿、⛔ 合併——提議剛才寫進的草稿撤回到提議之前。
            wd.draft = pre_draft
            session = AgentSession(agent_state)
            if pre_draft is None:
                session.clear_write_draft()
            else:
                session.write_write_draft(pre_draft)
        if wd.reissue_blocked or isinstance(wd.card_still_valid, dict) or wd.submitted_edit:
            return "exit", None
        no_value = await self._write_proposal_no_value(acc, identity, agent_state, raw_args)
        if no_value is not None:
            return "no_value", no_value
        return "closed", "HANDLED_BY_PROGRAM"

    async def _write_proposal_no_value(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, raw_args: Any,
    ) -> Optional[dict]:
        """`_write_draft_decide` 回 `None`、既有三個出口都不成立之後，
        提議**沒有任何值進草稿**時改由程式結束回合。條件全成立才回處置，否則 `None`（照 AP-1 (4) 回模型
        封閉結果）：草稿存在且動作＝提議動作；本回合 `created`／`merged`／`caught`／`filled` 皆不成立；
        非凍結（`frozen`）；本回合程式未觸發（`triggered`）。

        - (a) `{"kind": "card", "pid", "card", "action"}`：`_write_proposal_card_unchanged` 成立；
        - (b) `{"kind": "text", "action", "answer"}`：其他（`WF.proposal_no_value_text`，只有表單宣告的標籤）。

        **唯讀**（安全審查 r3 F2）：⛔ 呼叫 `_write_draft_same_values`、`redeem_pending`；⛔ 改待確認筆
        （含 `invalidated`）；⛔ 設 `reissue_blocked`、`reissue_burned`、`card_still_valid`。"""
        wd = acc.write_draft
        if wd is None:
            return None
        payload = _payload_of(raw_args)
        action = payload.get("action") if payload is not None else None
        draft = wd.draft
        if (draft is None or not isinstance(action, str) or draft.get("action") != action
                or wd.created or wd.merged or wd.caught or wd.filled
                or wd.frozen or wd.triggered):
            return None
        draft_values = WF.to_payload(action, draft.get("fields") or {})
        unchanged = await self._write_proposal_card_unchanged(identity, agent_state, action, draft_values)
        if unchanged is not None:
            pid, card, card_action = unchanged
            return {"kind": "card", "pid": pid, "card": card, "action": card_action}
        return {"kind": "text", "action": action,
                "answer": WF.proposal_no_value_text(action, draft_values)}

    async def _write_proposal_card_unchanged(
        self, identity: Identity, agent_state: dict, action: str, draft_values: dict,
    ) -> Optional[tuple]:
        """r3 AP-7 (2)(a) 的判定（**唯讀**）：同動作綁定卡、未作廢、無收據；`draft_values`
        （＝`to_payload(草稿)`）與該卡 `draft_payload` **全部鍵相等**（安全審查 r3 F7；舊筆或形狀不合 ⇒
        不成立）；AP-2 有效四項——`pending_token_state`（帶 `card_sha256`、`payload_sha256`，以 DB `now()`
        判）`live`＋`_write_draft_bound_card_text`（重排版雜湊相符、卡上日期未早於今天、排版不拋例外）。
        成立 ⇒ `(pid, 卡文字, 動作)`；否則 `None`。`draft_payload` 在這裡只拿來比對（⛔ 進草稿、卡或
        `confirm.request`）。"""
        bound = self._write_draft_bound_card(identity, agent_state, action)
        if bound is None:
            return None
        pid, entry = bound
        if entry.get("invalidated") is True or entry.get("receipt") is not None:
            return None
        card_draft = _pending_draft_payload(entry)
        if card_draft is None or card_draft != draft_values:
            return None
        payload = entry.get("payload")
        try:
            p_sha = payload_digest(payload) if isinstance(payload, dict) else None
        except (TypeError, ValueError):
            p_sha = None
        state = await pending_token_state(
            self._db_pool, identity.session_id, pid,
            card_sha256=entry.get("card_sha256"), payload_sha256=p_sha or "",
        )
        if state.state != PENDING_STATE_LIVE:
            return None
        card = self._write_draft_bound_card_text(entry, state)
        if card is None:
            return None
        return pid, card, entry.get("action")

    def _write_proposal_no_value_exit(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str, handling: dict,
    ) -> TurnResult:
        """r3 AP-7 (2)：程式結束回合（⛔ 交模型寫回覆；⛔ 建、燒 token）。出口另寫——⛔ 重用
        `_write_draft_card_still_valid_exit` 的開頭句判斷。

        - (a)：`PROPOSAL_NO_VALUE_CARD_TEXT`＋換行＋同一張卡、同 pid 三顆鍵、`confirm_pending`；記
          `write_proposal_no_value_card` 並同記 `write_draft_card_still_valid`（V2 以它計入程式重出同卡；
          ）。卡外提示行不重出。
        - (b)：`proposal_no_value_text`、`clarifying`、expects text、action＝草稿動作；記 `write_proposal_no_value`。"""
        if handling.get("kind") == "card":
            pid = handling["pid"]
            card = handling["card"]
            acc.violations.append(WF.V_WRITE_PROPOSAL_NO_VALUE_CARD)
            acc.violations.append(WF.V_CARD_STILL_VALID)
            return self._finish_confirm_turn(
                agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
                start=acc.start, kind="ask",
                outcome=make_outcome("confirm_pending", expects="button", action=handling["action"]),
                answer=f"{WF.PROPOSAL_NO_VALUE_CARD_TEXT}\n{card}", dialog_answer=card, pending_id=pid,
                quick_replies=confirm_quick_replies(pid),
                tool_calls=acc.tool_call_records, violations=acc.violations,
                llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
                completion_tokens=acc.completion_tokens,
            )
        acc.violations.append(WF.V_WRITE_PROPOSAL_NO_VALUE)
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, kind="ask",
            outcome=make_outcome("clarifying", expects="text", action=handling["action"]),
            answer=handling["answer"], pending_id=None,
            tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens,
        )

    def _write_proposal_exit(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str,
    ) -> Optional[TurnResult]:
        """AP-1 (4)：提議沒轉成程式呼叫時的既有程式出口（與另兩個檢查點同一組、同一順序）。"""
        return (self._write_draft_reissue_exit(acc, agent_state, user_message)
                or self._write_draft_card_still_valid_exit(acc, agent_state, user_message)
                or self._write_draft_submitted_exit(acc, agent_state, user_message))

    def _write_draft_record_asked(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
        tool_result: Any, raw_args: Any, document: Any,
    ) -> None:
        """W1b §8.5-1：`asked` 的**唯一寫點**——`confirm_missing_fields_ask` 出口（程式觸發或模型
        自呼 `confirm.request` 得缺欄；兩者的追問句都是程式產出）。草稿不存在（或動作不同）⇒
        先建草稿再寫（安全處置 4a：一律經可見性閘）。文件回合、`doc_action`、文件暫存有效 ⇒
        ⛔ 寫（安全處置 1d）。模型自寫的追問（`kind=ask` 經 Verifier）不經這裡 ⇒ ⛔ 寫。
        「找不到這個名稱」出口（`_name_lenient_mark_not_found`）也經這裡寫該欄位
        （同為程式產出的追問句；傳入以該欄位標籤組的缺欄結果）。"""
        wd = acc.write_draft
        if wd is None or document is not None or document_writable_action(document) is not None:
            return
        if _document_carry_of(agent_state) is not None:
            return
        data = tool_result.data if isinstance(tool_result.data, dict) else {}
        action = data.get("action")
        if not isinstance(action, str):
            payload = _payload_of(raw_args)
            action = payload.get("action") if payload is not None else None
        if not isinstance(action, str) or action not in WF.FORMS:
            return
        if not self._write_draft_visible(identity, action):
            return
        keys = WF.asked_keys_for_labels(action, data.get("missing_fields") or [])
        if wd.draft is None or wd.draft["action"] != action:
            wd.draft = WF.new_draft(action, wd.owner)
        wd.draft["asked"] = keys
        self._write_draft_persist(acc, agent_state)

    async def _write_draft_decide(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
        user_message: str, document: Any, *, allow_trigger: bool = True,
    ) -> Optional["_ProgramMessage"]:
        """程式觸發的**唯一判斷函式**（W1c §9.1-1：程式優先入口 `_write_draft_program_first` 與
        輸出後觸發點 `_write_draft_after_output` 共用這一支，⛔ 複製兩份）：

        1. 取用意圖判斷呼叫的結果（每回合只取一次，`intent_consumed`）並合併、整句填入
           （安全處置 1a：意圖回傳**另一支寫入動作** ⇒ 不整句填入）；
        2. 觸發條件（§2.1(5)；W1b §8.1-4；W1c §9.7 F2 入口條件與輸出後觸發點**同一條件**）：
           `created`／`merged`／`caught`／`filled` 任一成立，且本回合模型未自己成功出卡、
           `allow_trigger`（呼叫端在取用之後的否決，例：模型輸出是敏感轉人）、非文件回合
           （`document is not None or document_writable_action(document) is not None ⇒ None`，
           §9.7 末段）、文件暫存的動作相同、看得到該動作、非 `select:`、剩餘期限 ≥ 觸發門檻。
        凍結回合（§8.5-3）⇒ 不合併、不填、不觸發（意圖 task 交給 trace 收尾）。"""
        wd = acc.write_draft
        if wd is None or wd.triggered or wd.frozen or wd.submitted_edit:
            return None
        if not wd.intent_consumed:
            wd.intent_consumed = True
            start_action = wd.draft["action"] if wd.draft is not None else None
            # A-2a：打字選定判「值有沒有變」用（意圖呼叫常把前文同值再抽一次，`merged` 不足以判斷）。
            fields_before = (copy.deepcopy(wd.draft.get("fields") or {})
                             if wd.draft is not None else None)
            intent = await self._await_write_intent(acc)
            if intent is not None and self._write_draft_is_submitted_edit(wd, intent):
                # 第 3 步 #9g：修改剛送出的那一筆 ⇒ ⛔ 合併、⛔ 整句填入、⛔ 觸發；回合由程式固定句
                # 結束（`_write_draft_submitted_exit`）。
                wd.submitted_edit = True
                acc.violations.append(WF.V_SUBMITTED_EDIT_BLOCKED)
                return None
            provided: set = set()
            # 安全處置 1a：意圖呼叫回傳**另一支寫入動作** ⇒ 不整句填入（岔題不被當成答覆）。
            other_action = (intent is not None and start_action is not None
                            and isinstance(intent.action, str) and intent.action in WF.FORMS
                            and intent.action != start_action)
            if (wd.intent_parsed and self._write_candidates_post_pick(acc, identity) is not None
                    and not (other_action and _intent_has_value(intent))):
                # 候選集已選定或已撤回、仍綁定本草稿（名稱合併之前
                # 取）且意圖解析成功 ⇒ 單次決定。§11.14 第 3 點（第 5 輪第 4 點改寫）：另一支寫入動作只帶名稱（名稱不算
                # 新動作的值）⇒ 不換草稿、不合併、不整句填入，名稱另依規則分類。
                if wd.cmd_offered and wd.cmd_scope_start:
                    # 選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.3）：本回合送出指令版 schema、
                    # 回合開始已選定 ⇒ 指令路徑（⛔ 進 `_write_candidates_post_pick_names`）。
                    provided = await self._write_candidates_cmd_turn(
                        acc, identity, agent_state, user_message, intent,
                        blocked=other_action, fields_before=fields_before)
                else:
                    provided = await self._write_candidates_post_pick_names(
                        acc, identity, agent_state, user_message, intent,
                        blocked=other_action, fields_before=fields_before)
            else:
                if (wd.cmd_offered and wd.cmd_scope_start and wd.intent_parsed
                        and other_action and _intent_has_value(intent)):
                    # 換動作回合（另一動作帶非名稱值）：⛔ 讀 `target`。
                    acc.violations.append(_wc.V_CANDIDATE_CMD_SKIPPED)
                # 現行：無候選集、未選定、解綁、意圖解析失敗（含第 5 點重送後仍失敗），或另一動作帶非名稱值（§11.15.3
                # 第 6 點決定 1：照 §11.14 第 3 點換動作）。
                # F12 r6（§11.4 第 2 點「判定順序」；N-1）：先算程式驗證過的改選目標，再做名稱欄合併（模型提議暫存
                # 的名稱值、意圖的名稱值），⛔ 名稱合併先解綁、使改選失效。
                self._write_candidates_repick_target(acc, identity, user_message)
                await self._write_candidates_deferred_names(acc, identity, agent_state)
                if intent is not None:
                    provided = await self._write_draft_merge_intent(acc, identity, agent_state, intent)
                if not other_action:
                    await self._write_draft_fill_answer(acc, agent_state, user_message, provided)
                # 「選對紀錄」片 §4.2-1：物件或期別變了 ⇒ 先前講的比對值清掉（打字選定比對之前）。
                self._pick_right_said_reset(acc, agent_state)
                if wd.candidates is not None and self._write_candidates_active():
                    await self._write_candidates_typed(
                        acc, identity, agent_state, user_message, fields_before=fields_before)
            # F12（§5.1 (A)）：打字選定（甲′，程式驗證過、在候選集內）成立且候選集出自寬鬆路徑 ⇒ 同按鈕。
            if wd.candidates is not None and wd.picked and self._write_candidates_active():
                await self._name_lenient_pick_rewrite(acc, identity, agent_state)
            # A-2a 修正 2（verifier F1）：AI 恰回 `record_rechoice=other`（使用者要改用另一筆）、草稿是回合開始那份
            # 且動作沒換 ⇒ 程式作廢綁定卡、依草稿名稱重新解析（名稱多筆 ⇒ 重列候選）；本句沒改到任何欄位值也
            # 一樣。AI 只回理解結果；下一步由程式決定（DSP-091）。
            if (wd.rechoice_offered and wd.record_rechoice == WF.RECORD_RECHOICE_OTHER
                    and not other_action and wd.had_draft and not wd.created
                    and wd.draft is not None and wd.draft.get("action") == start_action
                    and self._write_candidates_active()):
                wd.rechoice = True
                wd.activity = True
                acc.violations.append(_wc.V_CANDIDATE_RECHOICE)
            # 填欄只填答覆 B6（§4.1）：追問回合（草稿仍是回合開始那份）追問的欄位本回合仍缺 ⇒ 程式依草稿照現行缺欄
            # 追問句重問（⛔ 交主模型、⛔ 整句填入）。資料段未知、答覆段為空、值被拒收都走這裡。
            self._fill_reask_if_missing(acc)
        draft = wd.draft
        if draft is None or not (wd.created or wd.merged or wd.caught or wd.filled
                                 or wd.picked or wd.reask or wd.rechoice or wd.relist or wd.fill_reask):
            return None
        if wd.model_confirm_ok:
            return None
        if not allow_trigger:
            return None
        # 文件回合維持既有路徑（`doc_action` 是工具迴圈內的區域變數，這裡另算）。
        if document is not None or document_writable_action(document) is not None:
            return None
        carry = _document_carry_of(agent_state)
        if carry is not None and carry["action"] != draft["action"]:
            return None
        if not self._write_draft_visible(identity, draft["action"]):
            return None
        if agent_state.get(SELECT_SCOPE_KEY) is not None:
            return None
        if self.budget.deadline_s - (self._clock() - acc.start) < WRITE_DRAFT_PROGRAM_MIN_REMAINING_S:
            return None
        if getattr(self, "_write_lifecycle_on", False):
            if wd.reissue_held:
                return None
            if not await self._write_draft_reissue_gate(acc, identity, agent_state, draft):
                wd.reissue_held = True
                return None
        wd.triggered = True
        acc.violations.append(WF.V_PROGRAM_CONFIRM)
        return _write_draft_program_message(draft, acc.nonce)

    def _write_draft_is_submitted_edit(self, wd: "_WriteDraftTurn", intent: Any) -> bool:
        """開關 on、回合開始時有「最近送出」標記、意圖的動作
        等於標記的動作、且意圖判斷的布林欄位恰為 `true` ⇒ 是「修改剛送出的那一筆」。
        比較用變數（⛔ 動作名字面，R1）。"""
        if not getattr(self, "_write_lifecycle_on", False):
            return False
        mark = wd.last_submitted
        action = getattr(intent, "action", None)
        return (isinstance(mark, dict) and isinstance(action, str)
                and action == mark.get("action") and wd.modifies_submitted is True)

    def _write_draft_submitted_exit(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str,
    ) -> Optional[TurnResult]:
        """#9g：程式固定句結束回合（⛔ 交模型改寫；⛔ 建草稿；⛔ 出卡）。標記保留（同一句再說一次
        ⇒ 同一句回覆），由出卡／取消／閒置回合清。"""
        wd = acc.write_draft
        if wd is None or not wd.submitted_edit:
            return None
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, kind="answer", answer=WF.SUBMITTED_EDIT_TEXT, pending_id=None,
            tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens,
            outcome=make_outcome("answered", expects="text"),
        )

    def _write_draft_reissue_not_issued_exit(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str,
    ) -> Optional[TurnResult]:
        """#9b（Q5）：本回合 A2 已燒掉綁定卡，程式觸發的 `confirm.request` 卻是非終結結果（沒出卡）
        ⇒ 程式固定句結束回合（⛔ 交模型：模型可能自由寫「請確認」而手上沒有任何可送出的卡）。"""
        wd = acc.write_draft
        if wd is None or not wd.reissue_burned:
            return None
        acc.violations.append(WF.V_REISSUE_NOT_ISSUED)
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, kind="answer", answer=WF.REISSUE_NOT_ISSUED_TEXT, pending_id=None,
            tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens,
            outcome=make_outcome("failed", expects="text"),
        )

    # ── UD-3：照片隨卡 ────────────────────────────────────────────────
    async def _card_photo_inputs(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, raw_args: Any,
    ) -> tuple:
        """這次 `confirm.request` 的照片來源 ⇒ `(欄位用的建議, 照片用的建議, 是否由舊卡帶來)`。

        - 不是 `repair_create` ⇒ 原樣（兩個 `_apply_*` 對非修繕本來就不動）。
        - 有一次性照片建議（新照片）⇒ 用它；照片先重新編碼（S11，`_encode_card_photos`），卡上
          sha256 綁重新編碼後那一份。超過 `REPAIR_PHOTOS_MAX` 張 ⇒ 不編（`_apply_photos_to_confirm_args`
          照舊全部不附、只寫張數）。
        - 沒有新照片 ⇒ `_card_photo_carry`：被這次更正取代的待確認卡上的照片（payload 原樣，⛔ 重新
          編碼 ⇒ sha256 與舊卡相同）與照片分類。⛔ 改成「建議不消耗」（會補到之後另一張無關的單）。"""
        fresh = agent_state.get(IMAGE_SUGGESTION_KEY)
        payload = _payload_of(raw_args)
        if payload is None or payload.get("action") != "repair_create":
            return fresh, fresh, False
        if isinstance(fresh, dict):
            photos = fresh.get("photos")
            if isinstance(photos, list) and 1 <= len(photos) <= REPAIR_PHOTOS_MAX:
                return fresh, dict(fresh, photos=await _encode_card_photos(identity, photos)), False
            return fresh, fresh, False
        carry = self._card_photo_carry(acc, identity, agent_state)
        if carry is None:
            return None, None, False
        return carry[0], carry[1], True

    def _card_photo_carry(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
    ) -> Optional[tuple]:
        """被更正取代的那張修繕卡 ⇒ `(照片分類建議或 None, {"photos": …} 或 {"photos_omitted": n})`；
        沒有 ⇒ `None`。全部成立才帶：

        - 寫入草稿是**回合開始就有、本回合沒換**的修繕草稿（`had_draft and not created`）——程式本來
          就把這一句當成同一張卡的更正（A2）；新草稿＝舊草稿已清（送出／取消／逾時／換動作），⛔ 帶；
        - 綁定卡（`_write_draft_bound_card`：最後一筆同動作、同建立者）無收據、照片未釋放；作廢與否
          不論（A2 燒卡、按「修改」都會先標 `invalidated`，那正是被取代的那一張）；
        - 照片取自它的 payload（出卡時程式寫入、已綁雜湊），讀回時重驗形狀（`repair_photos_of`）。"""
        wd = acc.write_draft
        draft = wd.draft if wd is not None else None
        if (not isinstance(draft, dict) or not wd.had_draft or wd.created
                or draft.get("action") != "repair_create"):
            return None
        bound = self._write_draft_bound_card(identity, agent_state, "repair_create")
        if bound is None:
            return None
        entry = bound[1]
        if isinstance(entry.get("receipt"), dict) or entry.get(PENDING_PHOTOS_RELEASED_KEY) is True:
            return None
        old_payload = entry.get("payload")
        if not isinstance(old_payload, dict):
            return None
        try:
            photos = _confirm_card.repair_photos_of(old_payload)
        except _confirm_card.ConfirmCardError:
            return None
        omitted = old_payload.get("broken_photos_omitted")
        if photos:
            photo_part: dict = {"photos": photos}
        elif (isinstance(omitted, int) and not isinstance(omitted, bool)
              and omitted > REPAIR_PHOTOS_MAX):
            photo_part = {"photos_omitted": omitted}
        else:
            photo_part = {}
        field_part = _photo_suggestion_fields(entry.get(PENDING_PHOTO_SUGGESTION_KEY))
        if not photo_part and field_part is None:
            return None
        return field_part, photo_part

    def _release_card_photos(self, identity: Identity, agent_state: dict, pending_id: Any) -> None:
        """縮減 ①：這張卡兌現（寫入成功或失敗）或作廢 ⇒ 刪掉它引用的照片暫存（`STORE.release_photos`，
        綁定以本回合身分重算、六欄逐一等值）。

        ⛔ 刪仍被另一張**活著**的卡（無收據、未作廢、未釋放）引用的照片——被更正取代的舊卡把照片
        交給新卡，⛔ 因為舊卡作廢就刪掉新卡的照片。⛔ 拋例外（釋放失敗只會留到 30 分鐘到期）。"""
        pending_all = agent_state.get(PENDING_CONFIRM_KEY)
        entry = pending_all.get(pending_id) if isinstance(pending_all, dict) else None
        if (not isinstance(entry, dict) or entry.get("action") != "repair_create"
                or entry.get(PENDING_PHOTOS_RELEASED_KEY) is True):
            return
        entry[PENDING_PHOTOS_RELEASED_KEY] = True
        shas = _payload_photo_shas(entry.get("payload"))
        if not shas:
            return
        live: set = set()
        for pid, other in pending_all.items():
            if (pid == pending_id or not isinstance(other, dict)
                    or isinstance(other.get("receipt"), dict) or other.get("invalidated") is True
                    or other.get(PENDING_PHOTOS_RELEASED_KEY) is True):
                continue
            live.update(_payload_photo_shas(other.get("payload")))
        try:
            binding = _upload_store.binding_from_identity(identity, "repair")
            _upload_store.STORE.release_photos([s for s in shas if s not in live], binding)
        except Exception:  # noqa: BLE001 — 釋放失敗 ⇒ 留到到期（⛔ 讓例外吃掉這次回答）
            logger.warning("[agent] 確認卡照片暫存釋放失敗（留到到期）")

    def _write_draft_bound_card(
        self, identity: Identity, agent_state: dict, action: Any,
    ) -> Optional[tuple[str, dict]]:
        """第 3 步 A2：與草稿綁定的那張卡＝`pending_confirm` 裡**最後一筆**同動作、同建立者的
        待確認筆（`_begin_pending_confirm` 是 pending 的唯一寫點、依出卡順序插入）。沒有 ⇒ `None`。"""
        pending_all = agent_state.get(PENDING_CONFIRM_KEY)
        if not isinstance(pending_all, dict):
            return None
        creator = _pending_creator(identity)
        for pid in reversed(list(pending_all)):
            entry = pending_all.get(pid)
            if (isinstance(entry, dict) and entry.get("action") == action
                    and entry.get("creator") == creator):
                return pid, entry
        return None

    async def _write_draft_reissue_gate(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, draft: dict,
    ) -> bool:
        """第 3 步 A2（卡後改欄位）＋A7(2)：程式觸發前的最後一道。回 `True` ⇒ 照常觸發。

        只在「回合開始就有、且本回合沒換動作」的草稿（`had_draft and not created`）與一張**還活著**
        的綁定卡同時存在時動作（其餘 ⇒ `True`＝現行觸發）：
          - 綁定卡已有 receipt ⇒ ⛔ 重出卡（回 `False`）；
          - 本回合使用者句子寫進草稿的鍵（`touched`），經 `to_payload` 後的值與綁定卡 payload
            同鍵的值**全相同** ⇒ ⛔ 重出卡（原 pid 仍可送出，§7 F4）；
          - 有不同 ⇒ 先以既有 `redeem_pending()`（綁 pid＋session＋未兌現＋未過期）**燒綁定卡**、
            丟掉回傳的 token，再照常觸發程式 `confirm.request`（新卡由 `to_payload(草稿)` 產生，
            ⛔ 讀 `pending["payload"]` 進草稿、⛔ 改 pending 的 payload）；燒不到（`None`）⇒
            ⛔ 重出卡，回合以程式固定句結束（`reissue_blocked`）。
        燒過（或燒不到）的綁定卡一律標既有的 `invalidated`（只是旗標，payload 不動）：之後同一個
        pid 的按鈕走作廢分支、下一次更正也不會再把它當綁定卡。

        A+ 片（三個開關皆 on，`_write_proposal_active`）：
          - **Q3**：進入條件放寬為「草稿動作與綁定卡相同」——本回合新建的草稿（`created` 或回合開始
            無草稿）**只走值相同那一支**：本回合寫進的鍵全相同 ⇒ `_write_draft_same_values`；有不同、
            沒有可比的鍵、綁定卡有收據或已作廢 ⇒ 照現行觸發（⛔ 燒、交 A7）。⛔ 從卡回填草稿。
          - **AP-4**：比對改用綁定卡的 `draft_payload`（出卡當時程式送出的草稿正規化值，逐鍵 `==`，
            ⛔ `str()`）；舊筆或形狀不合 ⇒ 沿用上列字串比對。
          - **AP-2／AP-3**：值相同 ⇒ `_write_draft_same_values`（卡片還在／燒舊卡出新卡／S3）。"""
        wd = acc.write_draft
        if wd is None:
            return True
        proposal_on = self._write_proposal_active()
        new_draft = wd.created or not wd.had_draft
        if new_draft and not proposal_on:
            return True
        bound = self._write_draft_bound_card(identity, agent_state, draft.get("action"))
        if bound is None:
            return True
        pid, entry = bound
        if isinstance(entry.get("receipt"), dict):
            if new_draft:
                return True
            acc.violations.append("write_draft_reissue_skipped_has_receipt")
            return False
        if entry.get("invalidated") is True:
            return True
        old_payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        new_payload = WF.to_payload(draft.get("action"), draft.get("fields") or {})
        compared = [k for k in sorted(wd.touched) if k in new_payload]
        draft_payload = _pending_draft_payload(entry) if proposal_on else None
        if draft_payload is not None:
            # AP-4：正規化值逐鍵相等（⛔ `str()`；⛔ 比 `confirm.request` 改寫後的 payload）。
            changed = [k for k in compared if new_payload[k] != draft_payload.get(k)]
        else:
            changed = [k for k in compared if str(new_payload[k]) != str(old_payload.get(k))]
        if new_draft:
            # Q3：本回合新建的草稿只走值相同那一支；有不同或沒有可比的鍵 ⇒ 照現行觸發（不燒）。
            if changed or not compared:
                return True
            return await self._write_draft_same_values(acc, identity, pid, entry)
        # A-2a 修正 2：AI 恰回 `record_rechoice=other`（`wd.rechoice`）⇒ 視同有改：燒綁定卡、依草稿名稱重新解析
        # （⛔ 走值相同那一支回「卡片還在」）。
        if not changed and not wd.rechoice:
            if proposal_on:
                return await self._write_draft_same_values(acc, identity, pid, entry)
            acc.violations.append("write_draft_reissue_skipped_same_values")
            return False
        # A-2a 修正 1：綁定卡帶著選定時，燒之前先以 B 片判 live 的同一支（`_live_entry`：未作廢、無收據、
        # `pending_token_state` live 且卡與 payload 雜湊相符）確認仍有效（唯讀；沒帶選定 ⇒ ⛔ 多查一次）。
        card_live = (self._write_candidates_active()
                     and entry.get(_wc.CARD_PICK_KEY) is not None
                     and await self._live_entry(identity, pid, entry) is not None)
        redemption = None
        if self._db_pool is not None:
            redemption = await redeem_pending(self._db_pool, identity.session_id, pid)
        entry["invalidated"] = True
        if redemption is None:
            # A7(2)／§7 Q1（S3）：燒不到＝舊卡已被兌現／過期／不是本 session ⇒ ⛔ 重出卡。
            wd.reissue_blocked = True
            acc.violations.append("write_draft_reissue_burn_failed")
            return False
        # 回傳的 token ⛔ 留用（燒卡只為作廢）。
        del redemption
        wd.reissue_burned = True
        # A-2a 修正 1：判定時 live、且燒成功（`redeem_pending` 綁 pid＋session＋未兌現＋未過期）。
        if card_live:
            wd.reissue_live_pid = pid
        acc.violations.append("write_draft_card_reissue")
        return True

    def _write_draft_bound_card_text(self, entry: dict, token_state: Any) -> Optional[str]:
        """A+ 片 AP-2 (ii)～(iv)：綁定卡（DB 已判 `live`）的卡文字仍有效 ⇒ 回重排版的卡文字；否則 `None`。

        (ii) 以存下的 payload **帶當日**（`bills._today()`，與出卡同一個時鐘；安全審查 2-1）重排版，
             雜湊＝待確認筆 `card_sha256`，且 DB 該列 `summary_sha256`／`payload_sha256` 都對得上；
        (iii) `fields_before_today` 為空（卡上日期未早於今天，否則兌現閘二必擋；2-3）；
        (iv) 排版拋例外（逾期帳單延期卡跨日的 `ConfirmCardError` 等）⇒ 不成立，⛔ 讓例外離開回合。"""
        action = entry.get("action")
        payload = entry.get("payload")
        stored = entry.get("card_sha256")
        if not isinstance(payload, dict) or not isinstance(stored, str):
            return None
        if token_state.summary_match is not True or token_state.payload_match is not True:
            return None
        today = bills._today()
        try:
            card = _confirm_card.render(action, payload, today=today)
        except Exception:  # noqa: BLE001 — (iv) 排版失敗 ⇒ 不成立（⛔ 讓例外離開回合）
            return None
        if not isinstance(card, str) or not hmac.compare_digest(sha256_hex(card), stored):
            return None
        try:
            if fields_before_today(action, payload, today):
                return None
        except Exception:  # noqa: BLE001 — 判不出 ⇒ 不成立（fail-closed）
            return None
        return card

    async def _write_draft_same_values(
        self, acc: TurnAccumulator, identity: Identity, pid: str, entry: dict,
    ) -> bool:
        """A+ 片 AP-2／AP-3：本回合寫進草稿的值與綁定卡相同。回 `True` ⇒ 照常觸發（出新卡）。

        - DB 唯讀查詢 `pending_token_state` 判 `live` 且 `_write_draft_bound_card_text` 成立 ⇒
          `card_still_valid`（回合由 `_write_draft_card_still_valid_exit` 結束；⛔ 新 token）；
        - `expired`，或 (ii)～(iv) 不成立（d）⇒ 比照 A2：先 `redeem_pending` 燒掉綁定卡，燒成功 ⇒
          `invalidated`、`reissue_burned`、照常觸發（A7 在同一交易燒掉本 session 其他 token；新卡沒
          出成 ⇒ #9b 固定句）。燒不到 ⇒ 再查一次：仍是**已真的過期**（`redeemed=false`）⇒ 同燒成功；
          其他（含期間被兌現）⇒ `reissue_blocked`（安全審查 3-1：已兌現優先）；
        - `redeemed`／`missing` ⇒ 沿用 S3「燒不到 ⇒ ⛔ 重出卡」：`invalidated`＋`reissue_blocked`。"""
        wd = acc.write_draft
        db_pool = self._db_pool
        session_id = identity.session_id
        payload = entry.get("payload")
        try:
            p_sha = payload_digest(payload) if isinstance(payload, dict) else None
        except (TypeError, ValueError):
            p_sha = None
        state = await pending_token_state(
            db_pool, session_id, pid,
            card_sha256=entry.get("card_sha256"), payload_sha256=p_sha or "",
        )
        if state.state == PENDING_STATE_LIVE:
            card = self._write_draft_bound_card_text(entry, state)
            if card is not None:
                wd.card_still_valid = {"pid": pid, "card": card, "action": entry.get("action")}
                acc.violations.append(WF.V_CARD_STILL_VALID)
                return False
            acc.violations.append("write_draft_bound_card_stale")
        elif state.state == PENDING_STATE_EXPIRED:
            acc.violations.append("write_draft_bound_card_expired")
        else:
            # (b) redeemed／missing ⇒ S3：⛔ 重出卡。
            entry["invalidated"] = True
            wd.reissue_blocked = True
            acc.violations.append(f"write_draft_bound_card_{state.state}")
            return False
        redemption = None
        if db_pool is not None:
            redemption = await redeem_pending(db_pool, session_id, pid)
        entry["invalidated"] = True
        if redemption is None:
            again = await pending_token_state(db_pool, session_id, pid)
            if not (again.state == PENDING_STATE_EXPIRED and again.lapsed):
                wd.reissue_blocked = True
                acc.violations.append("write_draft_reissue_burn_failed")
                return False
        # A-2a 修正 1：只有「判定時為 live（卡與 payload 雜湊皆相符，同 `_live_entry`）、且燒成功」才算綁定卡
        # 仍有效；過期後才燒的 ⛔ 帶選定。
        if (redemption is not None and state.state == PENDING_STATE_LIVE
                and state.summary_match is True and state.payload_match is True):
            wd.reissue_live_pid = pid
        # 回傳的 token ⛔ 留用（燒卡只為作廢）。
        del redemption
        wd.reissue_burned = True
        acc.violations.append("write_draft_card_reissue")
        return True

    def _write_draft_card_still_valid_exit(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str,
    ) -> Optional[TurnResult]:
        """A+ 片 AP-2：綁定卡有效、值相同 ⇒ 程式結束回合：固定句＋換行＋同一張卡文字、
        `confirm_pending`、原 pid 的三顆鍵；⛔ 建 token；⛔ 交模型。出卡當時的卡外提示行（未結單、
        `BILL_MATCH_HINT`）不重出。本回合使用者句子的值被值閘丟掉 ⇒
        `CARD_UNCHANGED_TEXT`（業主裁 Q2）。
        填欄只填答覆修復輪 3（業主 10-27 §6 第 10 點；開關 on／off 皆生效）：B 片生效時，本回合沒讀到任何值
        （`_write_reply_read_values_line` 回 `None`）⇒ `CARD_NO_CHANGE_TEXT`（⛔ 說「卡片還在，請按確認。」）。
        修復輪 4（同第 10 點）：B 片生效、讀到值且與卡相同 ⇒ 前導句改 `CARD_READ_SAME_LEAD`＋讀到行（程式分不出
        「沒要改」與「AI 漏讀要改的欄」，⛔ 依詞分；DSP-091）；B 片關的舊路徑照舊 `CARD_STILL_VALID_TEXT`。"""
        wd = acc.write_draft
        if wd is None or not isinstance(wd.card_still_valid, dict):
            return None
        pid = wd.card_still_valid["pid"]
        card = wd.card_still_valid["card"]
        # 填欄只填答覆 B2：本回合有值沒套用（資料段未知、資料段外拒收、追問回合不覆寫）同樣說沒套用（⛔ 叫客人按確認送出舊值）。
        lead = (WF.CARD_UNCHANGED_TEXT
                if wd.user_value_dropped or self._fill_value_not_applied(wd) else WF.CARD_STILL_VALID_TEXT)
        if lead == WF.CARD_STILL_VALID_TEXT and self._write_reply_active():
            # B 片 B5（W-R3，業主裁 Q4）：本回合使用者句子帶出的值都與卡相同 ⇒ 列出讀到的值（卡上顯示值）。
            read_line = self._write_reply_read_values_line(
                wd.card_still_valid["action"], wd.touched, card)
            if read_line is not None:
                # 修復輪 4：讀到的值都與卡相同 ⇒ 中性前導句（⛔「卡片還在，請按確認。」；AI 可能漏讀要改的欄）。
                lead = f"{WF.CARD_READ_SAME_LEAD}\n{read_line}"
            else:
                # 修復輪 3：沒讀到任何值（依狀態，⛔ 依詞；DSP-091）⇒ 中性句，⛔ 叫客人按確認。
                lead = WF.CARD_NO_CHANGE_TEXT
                self._fill_mark(acc, WF.V_CARD_NO_VALUE_READ)
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, kind="ask",
            outcome=make_outcome("confirm_pending", expects="button",
                                 action=wd.card_still_valid["action"]),
            answer=f"{lead}\n{card}", dialog_answer=card, pending_id=pid,
            quick_replies=confirm_quick_replies(pid),
            tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens,
        )

    def _write_draft_reissue_exit(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str,
    ) -> Optional[TurnResult]:
        """A2 燒不到綁定卡 ⇒ 程式固定句結束回合（⛔ 交模型改寫；⛔ 重出卡）。"""
        wd = acc.write_draft
        if wd is None or not wd.reissue_blocked:
            return None
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, kind="answer", answer=CONFIRMATION_REQUIRED_TEXT, pending_id=None,
            tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens,
            outcome=make_outcome("failed", expects="none"),
        )

    # -- B 片：寫入進行中回話由程式產生（B1、B2、B5）＋帶狀態句判讀閘（B3）------------
    # 分工（DSP-091）：理解由 AI（判讀呼叫只回「回覆宣稱了哪類狀態」）；送不送、送什麼一律由程式
    # 依狀態決定。本節的出口 ⛔ 出新卡、⛔ 建 token（⛔ 呼叫 `_begin_pending_confirm`／`confirm.request`）：
    # 只以唯讀判定（`_write_proposal_card_unchanged`、`pending_token_state`）重出同一張卡（同 pid）。
    # A-2a（A2-R8）：分支 (3) 名稱多筆 ⇒ 列候選清單——⛔ 出卡、⛔ 建 token，**只寫候選集**（session 狀態）。
    def _write_reply_active(self) -> bool:
        """B1／B2／B5 生效：`AGENT_WRITE_REPLY_PROGRAM` on，且 A+ 提議路徑生效（B2 依卡 `draft_payload`）。"""
        return bool(getattr(self, "_write_reply_program_on", False) and self._write_proposal_active())

    def _state_claim_active(self) -> bool:
        """B3 生效：`AGENT_STATE_CLAIM_GATE` on。"""
        return bool(getattr(self, "_state_claim_gate_on", False))

    async def _session_live_card(
        self, identity: Identity, agent_state: dict, *, action: Any = None,
    ) -> Optional[tuple]:
        """本 session、本建立者最後一筆**仍可兌現**的待確認筆 ⇒ `(pid, entry, token_state)`；否則 `None`（**唯讀**）。

        條件：同建立者（`_pending_creator`）、未作廢、無收據、`pending_token_state` 為 `live` 且卡與
        payload 雜湊皆相符（DB `now()` 判；查不到 ⇒ `missing`＝不成立，fail-closed）。`action` 給定 ⇒
        只看同動作（＝草稿的綁定卡，`_write_draft_bound_card` 同一規則）。"""
        pending_all = agent_state.get(PENDING_CONFIRM_KEY) if isinstance(agent_state, dict) else None
        if not isinstance(pending_all, dict):
            return None
        creator = _pending_creator(identity)
        for pid in reversed(list(pending_all)):
            entry = pending_all.get(pid)
            if not isinstance(entry, dict) or entry.get("creator") != creator:
                continue
            if action is not None and entry.get("action") != action:
                continue
            if action is not None:
                # 綁定卡＝最後一筆同動作、同建立者（⛔ 往前找更舊的同動作筆）。
                return await self._live_entry(identity, pid, entry)
            hit = await self._live_entry(identity, pid, entry)
            if hit is not None:
                return hit
        return None

    async def _live_entry(self, identity: Identity, pid: str, entry: dict) -> Optional[tuple]:
        if entry.get("invalidated") is True or entry.get("receipt") is not None:
            return None
        payload = entry.get("payload")
        try:
            p_sha = payload_digest(payload) if isinstance(payload, dict) else None
        except (TypeError, ValueError):
            p_sha = None
        state = await pending_token_state(
            self._db_pool, identity.session_id, pid,
            card_sha256=entry.get("card_sha256"), payload_sha256=p_sha or "",
        )
        if (state.state != PENDING_STATE_LIVE or state.summary_match is not True
                or state.payload_match is not True):
            return None
        return pid, entry, state

    def _write_draft_survives_turn(self, acc: TurnAccumulator) -> bool:
        """回合結束時草稿還在（`_write_draft_end_turn` 的閒置清除規則先行預測；⛔ 改任何狀態）。"""
        wd = acc.write_draft
        if wd is None or wd.draft is None:
            return False
        if wd.activity or wd.frozen:
            return True
        return int(wd.draft.get("idle_turns") or 0) + 1 < WF.DRAFT_IDLE_LIMIT

    async def _write_context_turn(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, *, entry: dict,
    ) -> bool:
        """驗收檔第二節「寫入情境回合」：非文件回合、非文件暫存有效回合、非點選範圍回合、非影子回合
        （`entry`＝進模型迴圈當下記下的三旗標），且任一成立：回合結束時草稿存在；本 session 有 live
        綁定卡；本回合有 `write_proposal` 或程式觸發。⛔ 改任何狀態。"""
        if entry.get("document") or entry.get("doc_carry") or entry.get("select_scope"):
            return False
        if self.readonly_view:
            return False
        wd = acc.write_draft
        if self._write_draft_survives_turn(acc):
            return True
        if WF.V_WRITE_PROPOSAL in acc.violations or (wd is not None and wd.triggered):
            return True
        return await self._session_live_card(identity, agent_state) is not None

    def _write_reply_read_values_line(self, action: Any, touched: Any, card: Any) -> Optional[str]:
        """B5：`touched`（本回合寫進草稿的鍵）對應的卡上 `(標籤, 顯示值)` ⇒ 一行；無 ⇒ `None`。
        值取卡文字（同一 formatter 的顯示值，`card_display_rows`），⛔ 使用者原句。"""
        form = WF.FORMS.get(action) if isinstance(action, str) else None
        if form is None or not touched:
            return None
        rows: dict = {}
        for label, value in _confirm_card.card_display_rows(card):
            rows.setdefault(label, value)
        pairs: list = []
        for f in form.fields:
            if f.key in touched and f.label in rows and (f.label, rows[f.label]) not in pairs:
                pairs.append((f.label, rows[f.label]))
        return WF.card_read_values_text(pairs)

    async def _write_reply_state(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
    ) -> dict:
        """B2：依狀態挑程式回話（⛔ 出新卡、⛔ 建 token；⛔ 以動作名分支；A-2a 起唯一的寫入是候選集，見 (3)）。
        順序：
        (1) 綁定卡有效且草稿＝卡 ⇒ 同卡；(2) 綁定卡 live、草稿≠卡 ⇒ 同卡＋`CARD_DIFFERS_TEXT`；
        (3) 缺欄 ⇒ 追問句（`WF.missing_labels` 判不缺時，封閉三動作改用出卡路徑同一支
        `closed_action_missing_labels`：名稱對到多筆／物件無唯一有效合約 ⇒ 同出卡路徑的缺欄「合約」／「物件」）；
        A-2a（A2-R8，開關生效）：`WF.missing_labels` 判不缺、且出卡前解析是「名稱多筆」
        （`write_name_candidates`，出卡路徑同一組函式、同一次查詢）⇒ 候選清單分支——由
        `_write_reply_state_exit` 列清單並**只寫候選集**（⛔ 出卡、⛔ 建 token）；
        F12 r4 (乙)：(3) 要追問、追問含空的名稱欄且本回合打字 ⇒ 先試 `missing_name_lenient`，有候選 ⇒ 同上
        候選清單分支，回空 ⇒ 照現行追問；
        F12 r5 (丙)（第二接入點）：(3) 表單缺欄、名稱本回合講 ⇒ 在 (乙) 之前先試 `name_early_lookup`——多筆 ⇒
        候選清單分支、查無且寬鬆落空 ⇒ 找不到固定句分支、其餘 ⇒ 照現行；
        (4) `WRITE_NOT_ISSUED_TEXT`；(5) 無草稿、無 live 卡 ⇒ `NO_PENDING_WRITE_TEXT`。"""
        wd = acc.write_draft
        draft = wd.draft if wd is not None else None
        if draft is not None:
            action = draft.get("action")
            values = WF.to_payload(action, draft.get("fields") or {})
            unchanged = await self._write_proposal_card_unchanged(identity, agent_state, action, values)
            if unchanged is not None:
                pid, card, card_action = unchanged
                if wd.user_value_dropped or self._fill_value_not_applied(wd):
                    lead, branch = WF.CARD_UNCHANGED_TEXT, WF.WRITE_REPLY_STATE_CARD_UNCHANGED
                else:
                    lead, branch = WF.CARD_STILL_VALID_TEXT, WF.WRITE_REPLY_STATE_CARD_STILL_VALID
                    read_line = self._write_reply_read_values_line(action, wd.touched, card)
                    if read_line is not None:
                        # 填欄只填答覆修復輪 4（開關 on／off 皆生效）：讀到的值都與卡相同 ⇒ 中性前導句
                        # `CARD_READ_SAME_LEAD`（⛔「卡片還在，請按確認。」）；B 片關照舊；分支名照舊。
                        if self._write_reply_active():
                            lead = WF.CARD_READ_SAME_LEAD
                        lead = f"{lead}\n{read_line}"
                    else:
                        # 填欄只填答覆修復輪 3（開關 on／off 皆生效）：本回合沒讀到任何值 ⇒ 中性句（⛔ 說「卡片還在，
                        # 請按確認。」）；分支名照舊（`card_still_valid`），另記固定字串標記。
                        lead = WF.CARD_NO_CHANGE_TEXT
                        self._fill_mark(acc, WF.V_CARD_NO_VALUE_READ)
                return {"branch": branch, "lead": lead, "pid": pid, "card": card,
                        "action": card_action}
            bound = await self._session_live_card(identity, agent_state, action=action)
            if bound is not None:
                pid, entry, token_state = bound
                card = (self._write_draft_bound_card_text(entry, token_state)
                        if _pending_draft_payload(entry) is not None else None)
                if card is not None:
                    # 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.3 第 8 點）：同句部分套用、另有欄位被資料段
                    # 拒收 ⇒ 前導句後加點名欄位標籤的固定句（⛔ 帶值）；非寬回合、沒有拒收 ⇒ 與改前逐字相同。
                    notice = self._fill_wide_notice(wd)
                    lead = WF.CARD_DIFFERS_TEXT if notice is None else f"{WF.CARD_DIFFERS_TEXT}\n{notice}"
                    return {"branch": WF.WRITE_REPLY_STATE_CARD_DIFFERS, "lead": lead,
                            "pid": pid, "card": card, "action": entry.get("action")}
            # F12 r6（§11.4 第 2 點；§11.13 P3）：候選集已撤回且仍綁定 ⇒ 重列同一份 `ids`（⛔ 重新解析名稱、⛔ 追問
            # 其他欄位——客人重新選定之前不出卡）；狀態行與整則程式回話同一支出口。
            post = self._write_candidates_post_pick(acc, identity)
            if post is not None and _wc.is_withdrawn(post):
                acc.violations.append(_wc.V_CANDIDATE_RELIST_WITHDRAWN)
                return {"branch": WF.WRITE_REPLY_STATE_CANDIDATES, "action": action,
                        "identity": identity,
                        "relist": await self._write_candidates_relist_rows(acc, identity)}
            labels = WF.missing_labels(action, values)
            # r5 (丙)：只在表單缺欄（`WF.missing_labels` 非空）時試；`closed_action_missing_labels` 補出的
            # 「名稱多筆／無唯一有效合約」缺欄 ⛔ 觸發（那是欄位齊的出卡前解析，見上面 A-2a 分支）。
            form_missing = bool(labels)
            picked = wd.candidates is not None and wd.candidates.get("picked") is not None
            if not labels and self._write_candidates_active() and not picked:
                scope = self._pick_right_scope_pick(acc, identity)
                # 名稱解析零筆 ⇒ 寬鬆比對（本回合同一份脈絡；每回合最多 1 次）。
                nl_kw: dict = {}
                nl = self._name_lenient_ctx(acc, agent_state, None, action, identity=identity)
                if nl is not None:
                    nl_kw["name_lenient"] = nl
                cand = (await write_name_candidates(identity, action, values, scope_pick=scope, **nl_kw)
                        if scope is not None else
                        await write_name_candidates(identity, action, values, **nl_kw))
                nf_field = is_name_not_found(cand) if nl is not None else None
                if nf_field is not None:
                    return {"branch": WF.WRITE_REPLY_STATE_NAME_NOT_FOUND,
                            "text": NM.NAME_NOT_FOUND_TEXT, "action": action,
                            "field": nf_field, "identity": identity}
                if cand is not None:
                    return {"branch": WF.WRITE_REPLY_STATE_CANDIDATES, "data": cand.data,
                            "action": action, "identity": identity,
                            "field_value": values.get(cand.data.get("field"))}
            if not labels:
                labels = await closed_action_missing_labels(identity, action, values)
            labels = self._name_lenient_reask_labels(acc, action, labels)
            ask = missing_labels_ask_text(labels)
            if ask is not None:
                # (乙) 程式即將追問、追問含空的名稱欄、本回合打字 ⇒ 本回合原話寬鬆比對
                # （`confirm.missing_name_lenient`，與 (甲) 同一份脈絡與 `run_once`）；有候選 ⇒ 候選清單分支，
                # 其餘 ⇒ 照現行追問、逐字不變。
                nl = self._name_lenient_ctx(acc, agent_state, None, action, identity=identity)
                if nl is not None:
                    if form_missing:
                        # (丙) 第二接入點：程式先行沒發確認請求的缺欄回合——
                        # 名稱本回合講 ⇒ 先查（入口與閘門、每回合計數器全在 `confirm.name_early_lookup`；
                        # runtime ⛔ 另發出向）。多筆 ⇒ 候選清單分支；查無且寬鬆落空 ⇒ 找不到固定句分支；
                        # 唯一／沒查成／不合閘 ⇒ `None`，往下照現行（(乙) 與追問句逐字不變）。
                        early = await name_early_lookup(identity, action, values, labels=labels,
                                                        name_lenient=nl)
                        nf_field = is_name_not_found(early) if early is not None else None
                        if nf_field is not None:
                            return {"branch": WF.WRITE_REPLY_STATE_NAME_NOT_FOUND,
                                    "text": NM.NAME_NOT_FOUND_TEXT, "action": action,
                                    "field": nf_field, "identity": identity}
                        if early is not None and is_candidate_shape(early):
                            return {"branch": WF.WRITE_REPLY_STATE_CANDIDATES, "data": early.data,
                                    "action": action, "identity": identity,
                                    "field_value": values.get(early.data.get("field"))}
                    miss = await missing_name_lenient(identity, action, values, labels=labels,
                                                      name_lenient=nl)
                    if miss is not None:
                        return {"branch": WF.WRITE_REPLY_STATE_CANDIDATES, "data": miss.data,
                                "action": action, "identity": identity,
                                "field_value": values.get(miss.data.get("field"))}
                return {"branch": WF.WRITE_REPLY_STATE_MISSING, "text": ask,
                        "ask_target": WF.ask_target_for_missing(labels), "action": action}
            return {"branch": WF.WRITE_REPLY_STATE_NOT_ISSUED, "text": WF.WRITE_NOT_ISSUED_TEXT}
        if await self._session_live_card(identity, agent_state) is not None:
            return {"branch": WF.WRITE_REPLY_STATE_NOT_ISSUED, "text": WF.WRITE_NOT_ISSUED_TEXT}
        return {"branch": WF.WRITE_REPLY_STATE_NO_PENDING, "text": WF.NO_PENDING_WRITE_TEXT}

    def _write_reply_state_exit(
        self, acc: TurnAccumulator, agent_state: dict, user_message: str, state: dict, *,
        source: str, prefix: Optional[str] = None, trace: Optional[TurnTrace] = None,
    ) -> TurnResult:
        """B2 結束回合（一律經 `_finish_confirm_turn`，⛔ 經 `_finalize`／T1，S7）。`prefix`＝乙′ 已過
        B3 與出口閘的模型文字（`model_plus_status`）；`None`＝整則程式回話（`program`）。
        送出的 `ask_target` 只會是程式缺欄追問的封閉值或 `None`（⛔ `confirm_intent`，S8）。"""
        branch = state["branch"]
        acc.violations.append(f"{WF.TRACE_WRITE_REPLY_STATE_PREFIX}{branch}")
        acc.violations.append(f"{WF.TRACE_WRITE_REPLY_SOURCE_PREFIX}{source}")
        head = f"{prefix}\n\n" if prefix else ""
        common = dict(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens, trace=trace,
        )
        if "card" in state:
            pid = state["pid"]
            card = state["card"]
            if branch in (WF.WRITE_REPLY_STATE_CARD_STILL_VALID, WF.WRITE_REPLY_STATE_CARD_UNCHANGED):
                acc.violations.append(WF.V_CARD_STILL_VALID)
            # DSP-038：卡文字逐字接在最後、不經模型與 Verifier；dialog 只寫卡（卡外前導句 ⛔ 進歷史）。
            return self._finish_confirm_turn(
                kind="ask",
                outcome=make_outcome("confirm_pending", expects="button", action=state["action"]),
                answer=f"{head}{state['lead']}\n{card}", dialog_answer=f"{head}{card}",
                pending_id=pid, quick_replies=confirm_quick_replies(pid), **common,
            )
        if branch == WF.WRITE_REPLY_STATE_CANDIDATES:
            if "relist" in state:
                # F12 r6：已撤回 ⇒ 重列同一份 `ids`（候選集逐位不動）。
                return self._write_candidates_relist_exit(
                    acc, state["identity"], agent_state, user_message, state["relist"],
                    prefix=prefix, trace=trace)
            # A-2a（A2-R8）：清單與候選集出自同一份 `data`（同一次查詢）；乙′ 的模型文字接在前面。
            return self._write_candidates_exit(
                agent_state, state["data"], identity=state["identity"],
                field_value=state["field_value"], trace_id=acc.trace_id, start=acc.start,
                user_message=user_message, tool_calls=acc.tool_call_records,
                violations=acc.violations, llm_calls=acc.llm_calls,
                prompt_tokens=acc.prompt_tokens, completion_tokens=acc.completion_tokens,
                prefix=prefix, trace=trace,
            )
        if branch == WF.WRITE_REPLY_STATE_NAME_NOT_FOUND:
            # 寬鬆也落空 ⇒ 固定句（⛔ 回顯原話），該欄標為已追問、清掉查不到的名稱。
            label = self._name_lenient_mark_not_found(
                acc, state["identity"], agent_state, state["action"], state["field"], None)
            acc.violations.append(NM.V_NAME_LENIENT_NOT_FOUND_EXIT)
            return self._finish_confirm_turn(
                kind="ask",
                outcome=make_outcome("clarifying", expects="text", action=state["action"]),
                answer=f"{head}{state['text']}", pending_id=None,
                ask_target=(None if prefix else
                            (WF.ask_target_for_missing([label]) if label else None)),
                **common,
            )
        if branch == WF.WRITE_REPLY_STATE_MISSING:
            return self._finish_confirm_turn(
                kind="ask",
                outcome=make_outcome("clarifying", expects="text", action=state["action"]),
                answer=f"{head}{state['text']}", pending_id=None,
                # 乙′（有 `prefix`）送出的 `ask_target` 強制 `None`（計畫 B2 S8、驗收 V4 (5)）；整則程式回話
                # 才帶程式缺欄追問的封閉值。
                ask_target=None if prefix else state.get("ask_target"), **common,
            )
        outcome = (make_outcome("answered", expects="text")
                   if branch == WF.WRITE_REPLY_STATE_NO_PENDING
                   else make_outcome("failed", expects="text"))
        return self._finish_confirm_turn(
            kind="answer", outcome=outcome, answer=f"{head}{state['text']}", pending_id=None, **common,
        )

    async def _write_reply_program_exit(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str, *,
        trace: Optional[TurnTrace] = None,
    ) -> TurnResult:
        """B1／B2：整則程式狀態回話結束回合（模型文字 ⛔ 送出、⛔ 進 dialog）。先跑模型迴圈出口的
        草稿閒置計數（取代 `_finalize` 那一次），再依狀態挑句。"""
        self._write_draft_end_turn(acc, agent_state)
        state = await self._write_reply_state(acc, identity, agent_state)
        return self._write_reply_state_exit(
            acc, agent_state, user_message, state, source=WF.WRITE_REPLY_SOURCE_PROGRAM, trace=trace)

    async def _write_reply_kd3_exit(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str, *,
        write_entry: dict,
    ) -> Optional[TurnResult]:
        """B1：提議未發／程式呼叫非終結 ⇒ 開關 on、寫入情境的**非問句**回合由程式結束回合
        （⛔ 再叫主模型）；先過現行 #9b 出口。問句回合（Q1 乙′）與其他回合 ⇒ `None`（照現行回填結果、
        交回模型——模型只寫知識作答（DSP-091 歸 AI），之後經 B3 與乙′ 狀態行）。"""
        if not self._write_reply_active() or _is_question(user_message):
            return None
        if not await self._write_context_turn(acc, identity, agent_state, entry=write_entry):
            return None
        not_issued = self._write_draft_reissue_not_issued_exit(acc, agent_state, user_message)
        if not_issued is not None:
            return not_issued
        acc.violations.append(WF.V_WRITE_REPLY_KD3_EXIT)
        return await self._write_reply_program_exit(acc, identity, agent_state, user_message)

    async def _state_claim_events(self, identity: Identity, agent_state: dict) -> set:
        """驗收檔第二節「程式狀態事件」（一般出口用；本回合的卡、收據、取消、轉人出口都不經這裡）：
        等待確認＝session 有 live 卡；完成＝`completed_actions` 非空或 `pending_confirm` 有成功收據；
        取消＝`pending_confirm` 有 `{"cancelled": true}` 收據；轉人＝本回合 `final_kind=handoff`
        （一般出口的 handoff 不經判讀閘，故這裡恆不成立）。**唯讀**。"""
        events: set = set()
        if await self._session_live_card(identity, agent_state) is not None:
            events.add(SC.CLAIM_AWAITING)
        if agent_state.get(COMPLETED_ACTIONS_KEY):
            events.add(SC.CLAIM_COMPLETED)
        pending_all = agent_state.get(PENDING_CONFIRM_KEY)
        if isinstance(pending_all, dict):
            for entry in pending_all.values():
                receipt = entry.get("receipt") if isinstance(entry, dict) else None
                if not isinstance(receipt, dict):
                    continue
                if receipt.get("cancelled") is True:
                    events.add(SC.CLAIM_CANCELLED)
                elif "cancelled" not in receipt and "error" not in receipt:
                    events.add(SC.CLAIM_COMPLETED)
        return events

    async def _state_claim_gate(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, out: AgentOutput,
        *, card_capable: bool,
    ) -> Optional[tuple]:
        """B3：將送出的模型文字（`kind` ∈ answer／ask／recommend）⇒ 放行回 `None`；擋下回
        `(未對到的類別 tuple,)`（判讀失敗且 fail-closed ⇒ 空 tuple）。

        - 現行 `prose_confirm_suspect` 三條件成立 ⇒ 不呼叫判讀，直接當「等待確認」未對到；
        - 判讀失敗：可出卡的回合 fail-closed；其他回合照送並記 `state_claim_check_failed`；
        - 只記類別與耗時（⛔ 任何原文進 trace／log）。"""
        if not self._state_claim_active() or out.kind == "handoff":
            return None
        if (out.kind == "ask" and out.ask_target == "confirm_intent"
                and not any(tc.name == CONFIRM_TOOL_NAME for tc in acc.tool_call_records)):
            acc.violations.append(f"{SC.TRACE_STATE_CLAIM_UNBACKED_PREFIX}{SC.CLAIM_AWAITING}")
            return (SC.CLAIM_AWAITING,)
        remaining = self.budget.deadline_s - (self._clock() - acc.start)
        judged = await SC.judge_state_claims(
            self.provider.async_client.chat.completions.create,
            model=self._model, reasoning_effort=self._reasoning_effort,
            reply_text=out.answer, timeout_s=min(SC.STATE_CLAIM_TIMEOUT_S, remaining),
            clock=self._clock,
        )
        acc.prompt_tokens += judged.prompt_tokens
        acc.completion_tokens += judged.completion_tokens
        acc.violations.append(SC.V_STATE_CLAIM_CHECK)
        acc.violations.append(f"{SC.TRACE_STATE_CLAIM_MS_PREFIX}{judged.elapsed_ms}")
        if judged.claims is None:
            acc.violations.append(SC.V_STATE_CLAIM_CHECK_FAILED)
            return () if card_capable else None
        if not judged.claims:
            return None
        events = await self._state_claim_events(identity, agent_state)
        unbacked = tuple(c for c in judged.claims if c not in events)
        for c in unbacked:
            acc.violations.append(f"{SC.TRACE_STATE_CLAIM_UNBACKED_PREFIX}{c}")
        return unbacked or None

    async def _state_claim_replace_exit(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
        unbacked: tuple, *, write_ctx: bool, trace: TurnTrace,
    ) -> TurnResult:
        """B3 換句（模型文字 ⛔ 送出、⛔ 進 dialog；一律經 `_finish_confirm_turn`，S7）：未對到「已轉人」
        ⇒ `HANDOFF_OFFER_TEXT`；寫入情境回合（B2 生效）⇒ B2 狀態回話；其他 ⇒ `NO_PENDING_WRITE_TEXT`。
        換回句只說本回合或不宣稱狀態（S4）。"""
        if SC.CLAIM_HANDED_OFF not in unbacked and write_ctx and self._write_reply_active():
            return await self._write_reply_program_exit(
                acc, identity, agent_state, user_message, trace=trace)
        self._write_draft_end_turn(acc, agent_state)
        text = (WF.HANDOFF_OFFER_TEXT if SC.CLAIM_HANDED_OFF in unbacked
                else WF.NO_PENDING_WRITE_TEXT)
        return self._finish_confirm_turn(
            agent_state=agent_state, user_message=user_message, trace_id=acc.trace_id,
            start=acc.start, kind="answer", answer=text, pending_id=None,
            tool_calls=acc.tool_call_records, violations=acc.violations,
            llm_calls=acc.llm_calls, prompt_tokens=acc.prompt_tokens,
            completion_tokens=acc.completion_tokens,
            outcome=make_outcome("answered", expects="text"), trace=trace,
        )

    async def _write_reply_model_plus_status(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict, user_message: str,
        result: TurnResult, *, cache: dict,
    ) -> TurnResult:
        """乙′（Q1）：寫入情境問句回合、模型 `answer`（已過 Verifier 與 B3）⇒ 模型文字＋程式狀態行。
        `ask_target` 強制 `None`（S8）。(1)(2) ⇒ 模型文字經出口閘後＋空行＋前導句＋整張卡、同 pid
        三顆鍵，經 `_finish_confirm_turn`（卡文字在判讀閘與 Verifier 之後接上，DSP-038／S1）；
        (3) ⇒ 接缺欄追問句（A-2a：名稱多筆 ⇒ 接候選清單與 `pick:` 按鈕，A2-R8）；(4)(5) ⇒ 不接，照一般
        出口收尾。"""
        result.ask_target = None
        self._write_draft_end_turn(acc, agent_state)
        state = await self._write_reply_state(acc, identity, agent_state)
        if state["branch"] in (WF.WRITE_REPLY_STATE_NOT_ISSUED, WF.WRITE_REPLY_STATE_NO_PENDING):
            acc.violations.append(f"{WF.TRACE_WRITE_REPLY_STATE_PREFIX}{state['branch']}")
            acc.violations.append(
                f"{WF.TRACE_WRITE_REPLY_SOURCE_PREFIX}{WF.WRITE_REPLY_SOURCE_MODEL_PLUS_STATUS}")
            # 草稿閒置計數已在上面跑過 ⇒ 直接 `exit_gates.finalize`（⛔ 經 `_finalize` 再算一次）。
            return exit_gates.finalize(
                acc, result, is_fixed=False, verifier=self.verifier, cache=cache,
                agent_state=agent_state, user_message=user_message,
            )
        gated = exit_gates.apply_exit_gates(
            acc, result, verifier=self.verifier, agent_state=agent_state, user_message=user_message)
        return self._write_reply_state_exit(
            acc, agent_state, user_message, state, source=WF.WRITE_REPLY_SOURCE_MODEL_PLUS_STATUS,
            prefix=gated.answer, trace=gated.trace,
        )

    async def _write_draft_program_first(
        self, acc: TurnAccumulator, identity: Identity, agent_state: dict,
        user_message: str, document: Any,
    ) -> Optional["_ProgramMessage"]:
        """W1c 程式優先入口（§9.1-1，§9.7 F1／F2／F3 覆寫）：`_run_model_loop` 進 `while` 之前、
        謄本程式訊息之後（僅當沒有謄本程式訊息）。條件成立 ⇒ 回程式自己的 `confirm.request`，
        由呼叫端設為迴圈第一輪的程式訊息（主模型這一輪不被呼叫）；否則 `None` ⇒ 照現行。

        - 敏感（§9.1-2／F3）：`verifier.rules` 缺 ⇒ 不走；當句命中問句側敏感判準
          （`question_sensitive`，⛔ 新增詞表）⇒ 不走（輸出後觸發點仍可用）。
        - 等意圖（F1）：`asyncio.wait({task}, timeout=…)` 只判是否完成（上限依 §9.11-3 分級：回合開始時
          已有草稿 ⇒ `WRITE_DRAFT_PROGRAM_FIRST_WAIT_S`，無草稿 ⇒ `WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S`）
          （⛔ 自動取消）；**未完成** ⇒ 記 `write_draft_program_first_wait_timeout`，⛔ 設
          `intent_consumed`、⛔ 記 `write_intent_call_failed`、⛔ 合併／整句填入／觸發——全部留給
          輸出後觸發點。
        - 其餘（取用、合併、整句填入、入口條件、排除條件、期限）一律走 `_write_draft_decide`。"""
        wd = acc.write_draft
        if wd is None or wd.triggered or wd.frozen:
            return None
        rules = getattr(self.verifier, "rules", None)
        # A-2a：按鈕選定回合沒有使用者文字可判敏感（訊息是程式驗過的機器值）⇒ 直接交 `_write_draft_decide`。
        if not wd.pick_button and (rules is None or question_sensitive(user_message, rules)):
            return None
        call = acc.write_intent_call
        if not wd.intent_consumed and call is not None and not call.settled and not call.label_only:
            # W1c §9.11-3：回合開始時已有草稿 ⇒ 3 秒；無草稿 ⇒ 1 秒（未完成照 F1）。
            wait_s = (WRITE_DRAFT_PROGRAM_FIRST_WAIT_S if wd.had_draft
                      else WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S)
            done, _pending = await asyncio.wait({call.task}, timeout=wait_s)
            if not done:
                acc.violations.append(WF.V_PROGRAM_FIRST_WAIT_TIMEOUT)
                return None
        return await self._write_draft_decide(acc, identity, agent_state, user_message, document)

    async def _write_draft_after_output(
        self, acc: TurnAccumulator, out: AgentOutput, identity: Identity, agent_state: dict,
        user_message: str, document: Any,
    ) -> Optional["_ProgramMessage"]:
        """模型最終輸出通過 `AgentOutput.model_validate` 之後、T2／V2／Verifier 之前（觸發判斷點，
        W1c 起為程式優先的後備）：判斷交 `_write_draft_decide`（與程式優先共用）；這裡只多一道
        「敏感轉人優先（⛔ 觸發）」的否決——在取用意圖之後套用（意圖照常合併進草稿）。"""
        sensitive_handoff = False
        if out.kind == "handoff":
            try:
                fact_class = FactClass(out.fact_class)
            except ValueError:
                fact_class = None
            sensitive_handoff = (fact_class in SENSITIVE
                                 or out.handoff_reason == HandoffReason.sensitive_no_grounding.value)
        return await self._write_draft_decide(
            acc, identity, agent_state, user_message, document, allow_trigger=not sensitive_handoff)

    def _write_draft_end_turn(self, acc: TurnAccumulator, agent_state: dict) -> None:
        """模型迴圈出口（`_finalize`）：本回合沒有任何寫入相關動作 ⇒ `idle_turns+1`；
        連續 `DRAFT_IDLE_LIMIT` 回合 ⇒ 清掉（使用者改談別的）。凍結回合（程式追問後的問句）
        ⛔ 加計數（W1b §8.1-2）。"""
        wd = acc.write_draft
        if wd is not None and not wd.activity and not wd.frozen and wd.last_submitted is not None:
            # 第 3 步 #9g：「最近送出」標記同一條閒置規則（`DRAFT_IDLE_LIMIT` 個無關回合 ⇒ 清）。
            # 以落地那一份重讀（本回合其他寫點可能已清掉它；⛔ 用回合開頭的副本覆寫回去）。
            session = AgentSession(agent_state)
            mark, _invalid = WF.load_last_submitted(session.get_last_submitted())
            if mark is not None:
                mark_idle = mark["idle_turns"] + 1
                if mark_idle >= WF.DRAFT_IDLE_LIMIT:
                    session.clear_last_submitted()
                    acc.violations.append(WF.V_LAST_SUBMITTED_CLEARED_IDLE)
                else:
                    mark["idle_turns"] = mark_idle
                    session.write_last_submitted(mark)
        if wd is None or wd.draft is None or wd.activity or wd.frozen:
            return
        idle = int(wd.draft.get("idle_turns") or 0) + 1
        if idle >= WF.DRAFT_IDLE_LIMIT:
            self._write_draft_clear(acc, agent_state)
            acc.violations.append(WF.V_DRAFT_CLEARED_IDLE)
            return
        wd.draft["idle_turns"] = idle
        AgentSession(agent_state).write_write_draft(wd.draft)

    async def _consume_model_stream(self, create_kwargs: dict, state: dict) -> None:
        """建立串流並消費到結束；進度寫進 `state`（逾時取消時 `_next_model_message` 還讀得到）。"""
        stream = await self.provider.async_client.chat.completions.create(**create_kwargs)
        state["stream"] = stream
        async for chunk in stream:
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                state["usage"] = usage
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            choice = choices[0]
            finish = getattr(choice, "finish_reason", None)
            if finish:
                state["finish_reason"] = finish
            delta = getattr(choice, "delta", None)
            if delta is None:
                continue
            for tcd in getattr(delta, "tool_calls", None) or []:
                slot = state["tool_calls"].setdefault(
                    int(getattr(tcd, "index", 0) or 0), {"id": None, "name": "", "arguments": ""})
                if getattr(tcd, "id", None):
                    slot["id"] = tcd.id
                fn = getattr(tcd, "function", None)
                if fn is not None:
                    slot["name"] += getattr(fn, "name", None) or ""
                    slot["arguments"] += getattr(fn, "arguments", None) or ""
            piece = getattr(delta, "content", None)
            if piece:
                state["text"] += piece

    def _meter_main_call(self, acc: TurnAccumulator, state: dict, *, estimate: bool) -> None:
        """主模型呼叫計量：有 usage 用 usage；沒有且 `estimate`（逾時）⇒ 估算並記 `llm_usage_estimated`。"""
        usage = state.get("usage")
        if usage is not None:
            turn_pt = int(getattr(usage, "prompt_tokens", 0) or 0)
            turn_ct = int(getattr(usage, "completion_tokens", 0) or 0)
            acc._w2_last_main_prompt_tokens = turn_pt
        elif estimate:
            # 1 字元 ＝ 1 token，上限 `max_completion_tokens`（寧可高估）；prompt 取本回合上一次主呼叫的值，沒有就 0。
            turn_ct = min(len(state["text"]), self._max_completion_tokens)
            turn_pt = int(getattr(acc, "_w2_last_main_prompt_tokens", 0) or 0)
            acc.violations.append(LLM_USAGE_ESTIMATED)
        else:
            turn_pt = turn_ct = 0
        acc.prompt_tokens += turn_pt
        acc.completion_tokens += turn_ct
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

    async def _next_model_message(self, acc: TurnAccumulator, tool_specs: list) -> tuple:
        """叫一次模型（串流）、計量，回 `(message, cut_short)`（搬自 `_run_model_loop` 迴圈頂端；
        站內幫手 S3-live 修正 R3 抽出，好讓程式驅動的那一輪不叫模型）。

        W2：串流拼回與非串流同形的 `ChatCompletionMessage`；`cut_short`＝這次輸出被截斷
        （`finish_reason == "length"`）。呼叫以回合剩餘期限為上限（`asyncio.timeout` ＋ SDK 單次請求 `timeout`），
        逾時 ⇒ 關閉串流並丟 `_ModelCallDeadline`（`_run_model_loop` 接住走 `budget_exhausted`）。"""
        # E 片 §4.1-3 (b)：標籤已先完成且是程式出口 ⇒ 不叫主模型（`_run_model_loop` 接 `_DialogActPreempt`）。
        decide = getattr(acc, "_dialog_act_decide", None)
        if decide is not None and decide() is not None:
            acc.violations.append(WF.V_DIALOG_ACT_LATE)
            raise _DialogActPreempt()
        acc.llm_calls += 1
        create_kwargs = dict(
            model=self._model,
            messages=acc.messages,
            tools=tool_specs,
            parallel_tool_calls=False,
            response_format=_agent_output_response_format(),
            max_completion_tokens=self._max_completion_tokens,
        )
        if self._reasoning_effort is not None:
            # openai SDK 1.54（requirements）尚無 `reasoning_effort` 具名參數，走 `extra_body`
            # 直接進 JSON body（各版本皆收）；⛔ 不升 SDK 換參數名（那是另一個變因）。
            create_kwargs["extra_body"] = {"reasoning_effort": self._reasoning_effort}
        # 期限在真正呼叫模型前這一刻算（迴圈頂端的檢查之後還有程式分支會花時間）。
        remaining = self.budget.deadline_s - (self._clock() - acc.start)
        if remaining <= 0:
            raise _ModelCallDeadline()
        create_kwargs["stream"] = True
        create_kwargs["stream_options"] = {"include_usage": True}
        create_kwargs["timeout"] = remaining
        state: dict = {"stream": None, "text": "", "tool_calls": {}, "finish_reason": None,
                       "usage": None}
        # E 片 §4.1-3 (b)：主模型串流與標籤呼叫競速。標籤呼叫完成的回呼（事件迴圈回呼，⛔ 另開 task）在「標籤是
        # 程式出口」時取消**本 task** 的串流；取消以旗標分流（`acc._dialog_act_preempted`），⛔ 落入
        # `budget_exhausted`（W2 期限中斷是下面 `asyncio.timeout` 丟 `_ModelCallDeadline`）。
        label_call = acc.dialog_act_call if decide is not None else None
        label_cb = None
        if label_call is not None and not label_call.task.done():
            main_task = asyncio.current_task()

            def label_cb(_t: "asyncio.Task") -> None:
                if state.get("finished") or main_task is None or main_task.done():
                    return
                if decide() is not None:
                    acc._dialog_act_preempted = True
                    main_task.cancel()

            label_call.task.add_done_callback(label_cb)
        try:
            # `asyncio.timeout`（3.11，容器 `python:3.11-slim`）而非 `asyncio.wait_for`：後者另開一個 task，
            # 會讓同回合並行的寫入意圖呼叫（`_WriteIntentCall`）搶在主呼叫之前執行，改變既有的呼叫順序。
            async with asyncio.timeout(remaining):
                await self._consume_model_stream(create_kwargs, state)
        except (TimeoutError, APITimeoutError):
            if state["stream"] is not None:
                await _close_stream(state["stream"])
            self._meter_main_call(acc, state, estimate=True)
            raise _ModelCallDeadline()
        except asyncio.CancelledError:
            if state["stream"] is not None:
                await _close_stream(state["stream"])
            if getattr(acc, "_dialog_act_preempted", False):
                # E 片：標籤搶先 ⇒ 沿用 W2 估算計量（`llm_usage_estimated`），改回程式結果（不是回合被取消）。
                acc._dialog_act_preempted = False
                asyncio.current_task().uncancel()
                self._meter_main_call(acc, state, estimate=True)
                acc.violations.append(WF.V_DIALOG_ACT_LATE)
                raise _DialogActPreempt()
            raise
        finally:
            state["finished"] = True
            if label_cb is not None:
                label_call.task.remove_done_callback(label_cb)
        self._meter_main_call(acc, state, estimate=False)
        truncated = state["finish_reason"] == "length"
        # 被上限截斷 ⇒ 只記旗標；截斷的輸出照既有 SCHEMA 重寫／預算邏輯走，⛔ 不另開出口。
        if truncated:
            acc.violations.append(LLM_OUTPUT_TRUNCATED)
        tool_calls = None
        if state["tool_calls"]:
            tool_calls = [
                ChatCompletionMessageToolCall(
                    id=slot["id"] or "", type="function",
                    function=_ToolCallFunction(name=slot["name"], arguments=slot["arguments"]),
                )
                for _, slot in sorted(state["tool_calls"].items())
            ]
        message = ChatCompletionMessage(
            role="assistant", content=state["text"] or None, tool_calls=tool_calls)
        if self._clean_llm_output and LO.has_reasoning(getattr(message, "content", None)):
            # 推理段在這裡就剝掉：之後 append 進 messages（工具呼叫訊息、四條改寫）與解析的都是
            # 剝除後內容。Bedrock 不收 assistant 的推理欄位（第 0 步 Q3）⇒ 工具呼叫訊息也剝。
            message.content = (LO.final_segment(message.content) or "").strip()
            acc.violations.append(LLM_OUTPUT_REASONING_STRIPPED)
        return message, truncated

    def _extract_agent_output(self, content: str) -> Optional[tuple]:
        """`json.loads` 失敗後的擷取（只在 `clean_llm_output=True` 時呼叫）：逐 `{` 解碼，回第一個
        通過 `AgentOutput.model_validate` 的 `(payload, out)`；都不過 ⇒ `None`。"""
        for obj in LO.iter_json_objects(content):
            if not isinstance(obj, dict):
                continue
            try:
                return obj, AgentOutput.model_validate(obj)
            except (ValidationError, TypeError):
                continue
        return None

    async def _run_model_loop(
        self, acc: TurnAccumulator, identity: Identity, user_message: str,
        state: dict, agent_state: dict, *, document, cache: dict,
        tool_specs: list, visible_names: set, doc_write_face: frozenset,
        reserved_ids: frozenset, scope_estate_id: Optional[str],
    ) -> TurnResult:
        """第三段：工具迴圈＋Verifier＋兩條迴圈內改寫（Plan R R1）。

        ⛔ 逐字搬自原 `_run_turn_body`——**一個判定、一個順序、一個文案都沒有改**；
        差別只有可變狀態改走 `acc`（Plan §0c：整數就地加、list／dict 同一物件）。
        出口一律經 `exit_gates.finalize`（四道閘依序表＋三個狀態寫點）。
        """
        def _finalize(result: TurnResult, *, is_fixed: bool) -> TurnResult:
            # W1（§2.1(3)）：模型迴圈出口——本回合沒有寫入相關動作 ⇒ 草稿閒置計數 +1。
            self._write_draft_end_turn(acc, agent_state)
            return exit_gates.finalize(
                acc, result, is_fixed=is_fixed, verifier=self.verifier,
                cache=cache, agent_state=agent_state, user_message=user_message,
            )
        # B 片：「寫入情境回合」的三個排除條件以進模型迴圈當下為準（下面的分支可能清掉文件暫存，
        # 同 DG-1 的判定時點）。只讀、⛔ 改任何狀態；開關 off 時沒有讀者。
        write_entry = {
            "document": document is not None,
            "doc_carry": _document_carry_of(agent_state) is not None,
            "select_scope": agent_state.get(SELECT_SCOPE_KEY) is not None,
        }
        # 站內幫手 S3-live 修正 R3：放行的謄本回合，第一輪不叫模型——程式自己發一次
        # `confirm.request`，走下面同一條工具迴圈（欄位齊 ⇒ 出卡；缺 ⇒ 程式追問句）。
        program_message = _document_program_message(document, acc.nonce)
        # W1（§2.1(5)）：哪一種程式訊息（`"doc"`＝謄本回合；`"wd"`＝寫入草稿觸發）。
        # ⚠️ 只有 `"wd"` 不計工具預算、不受 `tool_call_exhausted` 限制（每回合上限 1 次，故有界）；
        #    判定只看**本迴圈自己設的這個變數**，⛔ 看 tool_call id（模型可以偽造同名 id）。
        program_kind: Optional[str] = None
        if program_message is not None:
            program_kind = "doc"
            acc.violations.append("document_program_confirm")
        else:
            # W1c（§9.1-1）：程式優先——寫入回合先由程式處理、不等主模型。條件成立 ⇒ 第一輪就是
            # 程式自己的 `confirm.request`（同下方輸出後觸發點的 `"wd"`）：終結出口直接結束回合、
            # 主模型本回合不被呼叫；非終結 ⇒ 工具結果回填、再叫主模型（每回合程式觸發上限 1 次）。
            wd_first = await self._write_draft_program_first(
                acc, identity, agent_state, user_message, document)
            if wd_first is not None:
                program_message, program_kind = wd_first, "wd"
            if self._closing_active() and acc.dialog_act_call is not None:
                # E 片 §4.1-3：標籤的程式決定（(b) 競速用；唯讀）與決定點 (a)。候選按鈕回合沒有使用者文字
                # （也沒有標籤呼叫）⇒ 不進。
                acc._dialog_act_decide = lambda: self._dialog_act_decision(
                    acc, identity, agent_state, user_message)
                if not self._write_candidate_button_turn(acc):
                    act_exit = await self._dialog_act_pre_loop(
                        acc, identity, agent_state, user_message, cache=cache,
                        program_first=wd_first is not None)
                    if act_exit is not None:
                        return act_exit
            reissue_exit = (self._write_draft_reissue_exit(acc, agent_state, user_message)
                            or self._write_draft_card_still_valid_exit(acc, agent_state, user_message)
                            or self._write_draft_submitted_exit(acc, agent_state, user_message))
            if reissue_exit is not None:
                return reissue_exit
            if program_message is None and self._write_candidate_button_turn(acc):
                # 按鈕選定成立、程式卻沒觸發（期限不足等）⇒ 程式狀態回話結束回合
                # （⛔ 呼叫主模型）。
                return await self._write_reply_program_exit(acc, identity, agent_state, user_message)
        while True:
            if (self._clock() - acc.start) >= self.budget.deadline_s:
                return _finalize(acc.build_fixed("budget_exhausted", clock=self._clock), is_fixed=True)

            wd_program = False
            doc_program = False
            cut_short = False
            if program_message is not None:
                message, program_message = program_message, None
                wd_program = program_kind == "wd"
                doc_program = program_kind == "doc"
                program_kind = None
            else:
                try:
                    message, cut_short = await self._next_model_message(acc, tool_specs)
                except _ModelCallDeadline:
                    return _finalize(acc.build_fixed("budget_exhausted", clock=self._clock), is_fixed=True)
                except _DialogActPreempt:
                    # E 片 §4.1-3 (b)：標籤搶先 ⇒ 程式出口（⛔ `budget_exhausted`）。
                    act_exit = self._dialog_act_exit(
                        acc, identity, agent_state, user_message, cache=cache)
                    if act_exit is not None:
                        return act_exit
                    continue
            tool_calls = list(getattr(message, "tool_calls", None) or [])

            if tool_calls:
                acc.messages.append(_assistant_tool_call_message(message, tool_calls))
                budget_hit = False
                # B 片 B1：本則 message 有提議未發或提議轉成的程式呼叫非終結 ⇒ 整則 tool call 照現行
                # 逐一處理、回填完之後（下面 `for` 迴圈結束、再叫主模型之前）才判程式狀態回話出口——
                # 同則其餘提議照樣計入預算與標記（V1 (f)），出口位置與 `wd_program` 區塊一致。
                kd3_hand_back = False
                for tc in tool_calls:
                    if not wd_program and acc.counters.tool_call_exhausted(self.budget):
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
                        acc.violations.append(f"IDENTITY_KEY:{key}")
                    if name not in visible_names:
                        acc.violations.append(f"FORBIDDEN:{name}")

                    # A+ 片 AP-1／AP-4：本次 tool call **專屬**的區域旗標（⛔ 設或重用 `wd_program`——
                    # 它是整則 message 共用變數；⛔ 以 `tc.id` 或其前綴判斷來源，模型造得出同名 id）。
                    #   - `proposal_program`：模型的提議已轉成程式依草稿發出的 `confirm.request`；
                    #   - `program_payload_keys`：程式依草稿發出時，payload 中屬於 `to_payload(草稿)` 的鍵
                    #     （出卡時存 `draft_payload` 用）。
                    proposal_program = False
                    program_payload_keys: Optional[frozenset] = (
                        _program_payload_keys(raw_args)
                        if wd_program and name == CONFIRM_TOOL_NAME else None
                    )
                    # DSP-091 DG-1：模型來源的理由要在下面任何分支改動 `agent_state`（例如清文件暫存）
                    # **之前**判定，標記才反映進場當下的狀態。
                    confirm_model_reason: Optional[str] = (
                        _confirm_model_reason(
                            proposal_active=self._write_proposal_active(), document=document,
                            agent_state=agent_state, readonly_view=self.readonly_view)
                        if name == CONFIRM_TOOL_NAME and not wd_program else None
                    )
                    # A+ 片 AP-1：模型**自己**呼叫 `confirm.request` ⇒ 參數只當提議（合併進草稿、下一步
                    # 由程式決定）；⛔ 以模型參數呼叫 `registry.call`。
                    # AP-5：文件回合、文件暫存有效回合、點選範圍回合維持模型自呼路徑——
                    # 過渡修正、不新增 AI 決定權：A+ 非目標；點選範圍由 A-2 接手（KD-1）；文件回合、
                    # 文件暫存由「文件回合」片接手（KD-2；文件回合各有程式先發與 DSP-076 覆寫規則）。
                    # 影子回合（`readonly_view`）維持現行（9i：不動 token 表與 `agent_state`）。
                    if (
                        name == CONFIRM_TOOL_NAME and not wd_program
                        and self._write_proposal_active()
                        and document is None
                        and _document_carry_of(agent_state) is None
                        and agent_state.get(SELECT_SCOPE_KEY) is None
                        and not self.readonly_view
                    ):
                        acc.violations.append(WF.V_WRITE_PROPOSAL)
                        p_kind, p_value = await self._write_proposal_handle(
                            acc, identity, agent_state, user_message, document, raw_args)
                        if p_kind == "program":
                            # 程式的 `confirm.request`（args 整份取代 `raw_args`，含 `summary` 常數），
                            # 以模型這次 tool call 的 id 走下方同一條路（照片、物件記憶前處理照舊；
                            # 出卡、缺欄追問、查無、範圍閘照現行出口）。計入 `tool_calls` 預算照現行。
                            raw_args = p_value
                            proposal_program = True
                            program_payload_keys = _program_payload_keys(raw_args)
                        else:
                            # 這次不轉成程式呼叫：模型的呼叫照現行計入預算、照跑保留 id 撞名檢查。
                            acc.counters.tool_calls += 1
                            acc.tool_call_records.append(
                                ToolCallRecord(
                                    id=tc.id, name=name,
                                    args_summary=_args_summary(raw_args),
                                    ms=0, status="error", n_items=0, empty=False,
                                )
                            )
                            if tc.id in reserved_ids:
                                acc.violations.append("tool_call_id_collides_with_reserved")
                            if p_kind == "no_value":
                                # r3 AP-7 (2)：提議沒有任何值進草稿 ⇒ 程式結束回合（⛔ 交模型寫回覆）。
                                return self._write_proposal_no_value_exit(
                                    acc, agent_state, user_message, p_value)
                            if p_kind == "exit":
                                exit_turn = self._write_proposal_exit(acc, agent_state, user_message)
                                if exit_turn is not None:
                                    return exit_turn
                                p_value = "HANDLED_BY_PROGRAM"
                            # AP-1 (4) 封閉結果：常數、⛔ 含草稿值（比照 `doc_write_face` 分支直接組
                            # tool message；⛔ 建 `ToolResult(error=...)`，`ToolError` 是封閉 Literal）。
                            # r3 AP-7 之後仍走到這裡的：動作不合（`NO_MATCH`，含巢狀內層動作不合）、
                            # 凍結回合（回答提問屬 AI，DSP-091）、本回合已觸發後的第二次提議、期限不足等
                            # （收窄範圍）。
                            acc.violations.append(WF.V_WRITE_PROPOSAL_NOT_ISSUED)
                            # B 片 B1：寫入情境的非問句回合 ⇒ 本則 tool call 回填完後（`kd3_hand_back`）先過
                            # #9b，再由程式狀態回話結束回合（⛔ 再叫主模型）。問句回合（Q1 乙′）與非寫入情境
                            # 回合照下方回填封閉結果、交回模型：模型只能寫知識作答（DSP-091 歸 AI）——寫入
                            # 情境裡 `ask`／`recommend` 在一般出口換成程式狀態回話，`answer` 經 B3 判讀閘後
                            # 由程式接狀態行（寫入回話仍由程式）。
                            kd3_hand_back = True
                            acc.messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "content": wrap_tool_data(
                                        "tool",
                                        json.dumps(
                                            {"ok": False, "error": p_value},
                                            ensure_ascii=False,
                                        ),
                                        acc.nonce,
                                    ),
                                }
                            )
                            continue
                    # W1（§2.1(3)）：模型**自己**呼叫 `confirm.request` ⇒ 原始參數（任何
                    # `_apply_*` 與 `_prepare_closed_action` 就地改寫之前）過值閘後合併進草稿。
                    # 文件回合與文件暫存有效時不合併；程式觸發的那一次（`wd_program`）不合併。
                    # 走到這個 `elif` 有兩種情形：(i) 三開關任一 off——回復開關（AP-R7＝改前行為），
                    # 非目標組態；(ii) 三開關 on 的點選範圍、唯讀檢視回合（上一支 `if` 不接）——KD-1
                    # 過渡修正、不新增 AI 決定權，由 A-2 接手。文件回合、文件暫存兩種情形此處不合併。
                    # ⛔ 新增分支（A+ 只把 `if` 改成 `elif`）。
                    elif (
                        name == CONFIRM_TOOL_NAME and not wd_program
                        and acc.write_draft is not None and document is None
                        and _document_carry_of(agent_state) is None
                    ):
                        await self._write_draft_merge_model_confirm(
                            acc, identity, agent_state, raw_args)

                    # W9-1 第二道網：文件回合的寫入面**不得執行**。
                    # ⚠️ 只把它從 `tool_specs` 拿掉是不夠的——`registry.call` 的
                    #    可見性判斷不知道這一回合帶了文件，模型硬打那個名字仍然
                    #    會真的執行（`FORBIDDEN:` 只是記一筆 violation，⛔ 不擋）。
                    #    ⇒ 這裡直接回一個封閉錯誤、⛔ 不呼叫 registry。
                    if name in doc_write_face:
                        acc.violations.append(f"DOCUMENT_TURN_WRITE_BLOCKED:{name}")
                        acc.counters.tool_calls += 1
                        acc.tool_call_records.append(
                            ToolCallRecord(
                                id=tc.id, name=name,
                                args_summary=_args_summary(raw_args),
                                ms=0, status="error", n_items=0, empty=False,
                            )
                        )
                        acc.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": wrap_tool_data(
                                    "tool",
                                    json.dumps(
                                        {"ok": False, "error": "NO_MATCH"},
                                        ensure_ascii=False,
                                    ),
                                    acc.nonce,
                                ),
                            }
                        )
                        continue

                    # 站內幫手 S3（§3h 第 1 點）：放行的文件回合裡 `confirm.request` 對模型
                    # 可見，但**只准**該 kind 對應的那一個動作——在 `registry.call` **之前**
                    # 解析 payload 的 `action`，不符 ⇒ 封閉錯誤、⛔ 不呼叫工具（token 表零新增）。
                    doc_action = document_writable_action(document)
                    if name == CONFIRM_TOOL_NAME and document is not None:
                        _doc_payload = _payload_of(raw_args)
                        _blocked = None
                        if doc_action is None or (_doc_payload or {}).get("action") != doc_action:
                            _blocked = "document_turn_action_blocked"
                        else:
                            # 建立一次性文件暫存（DSP-076；只在「放行對照內的文件回合、模型對
                            # 該 kind 對應動作呼叫 confirm.request」這一刻建立）。
                            AgentSession(agent_state).write_document_carry(
                                doc_action, list(document.typed_fields), document.receipt_date,
                            )
                            _blocked = _apply_document_to_payload(
                                _doc_payload, action=doc_action,
                                typed_fields=list(document.typed_fields),
                                user_texts=[user_message], free_text=document.free_text,
                            )
                            if _blocked is None:
                                raw_args = _with_payload(raw_args, _doc_payload)
                                acc.violations.append("document_typed_fields_applied")
                        if _blocked is not None:
                            acc.violations.append(_blocked)
                            acc.counters.tool_calls += 1
                            acc.tool_call_records.append(
                                ToolCallRecord(
                                    id=tc.id, name=name,
                                    args_summary=_args_summary(raw_args),
                                    ms=0, status="error", n_items=0, empty=False,
                                )
                            )
                            acc.messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc.id,
                                    "content": wrap_tool_data(
                                        "tool",
                                        json.dumps(
                                            {"ok": False, "error": "INVALID_INPUT"
                                             if _blocked == "document_free_text_in_payload"
                                             else "NO_MATCH"},
                                            ensure_ascii=False,
                                        ),
                                        acc.nonce,
                                    ),
                                }
                            )
                            continue
                    elif name == CONFIRM_TOOL_NAME:
                        # 文件暫存有效的後續回合：同一動作 ⇒ 同樣的覆寫與原話限制；
                        # 下一個**非本動作**的 `confirm.request` ⇒ 清掉暫存。
                        _carry = _document_carry_of(agent_state)
                        if _carry is None:
                            AgentSession(agent_state).clear_document_carry()
                        else:
                            _carry_payload = _payload_of(raw_args)
                            if (_carry_payload or {}).get("action") == _carry["action"]:
                                _apply_document_to_payload(
                                    _carry_payload, action=_carry["action"],
                                    typed_fields=_carry["typed_fields"],
                                    user_texts=_document_user_texts(
                                        agent_state, user_message, _carry["turns"]
                                    ),
                                    free_text=(),
                                )
                                raw_args = _with_payload(raw_args, _carry_payload)
                                acc.violations.append("document_carry_applied")
                            else:
                                AgentSession(agent_state).clear_document_carry()
                                acc.violations.append("document_carry_cleared")

                    if not wd_program:
                        acc.counters.tool_calls += 1
                    # UD-3：這次 `confirm.request` 用到的照片建議欄位（出卡時存進待確認筆，卡後更正帶到新卡）。
                    _card_photo_suggestion: Optional[dict] = None
                    if name == CONFIRM_TOOL_NAME:
                        # UD-3：照片來源二選一——本回合／照片建議（出卡前重新編碼，S11），或沒有新照片時
                        # 由被取代的待確認卡帶過來（照片＋照片分類；客人講的分類為準）。
                        _field_sugg, _photos_sugg, _carried = await self._card_photo_inputs(
                            acc, identity, agent_state, raw_args)
                        _card_photo_suggestion = _photo_suggestion_fields(_field_sugg)
                        raw_args, _applied = _apply_image_suggestion_to_confirm_args(
                            raw_args, _field_sugg, leaf_swap=not _carried
                        )
                        for _field in _applied:
                            acc.violations.append(f"image_suggestion_applied:{_field}")
                        # 站內幫手 S3（F10）：照片相關鍵**無條件**刪掉、再由程式寫入。
                        raw_args, _photo_marks = _apply_photos_to_confirm_args(
                            raw_args, _photos_sugg
                        )
                        if _carried:
                            acc.violations.append(V_PHOTOS_CARRIED)
                        for _mark in _photo_marks:
                            acc.violations.append(_mark)
                        # 第六批 #10 **讀點**：payload 缺 `estate_name` ⇒ 由物件記憶補。
                        # ⚠️ 排在照片建議之後、`registry.call` 之前（同一個落點，
                        #    ⛔ 不另開一段）；模型有給就不動（`_apply_...` 自己判）。
                        # ⛔ 一次性語義**不適用**：物件記憶不是「用完就丟」的建議，
                        #    同一段對話可能連開兩張單，故這裡 ⛔ 不清掉它。
                        raw_args, _applied_carry = _apply_estate_carry_to_confirm_args(
                            raw_args, _estate_carry_of(agent_state)
                        )
                        for _field in _applied_carry:
                            acc.violations.append(f"estate_carry_applied:{_field}")
                    # 程式專用選定通道 `program_pick` 的**唯一設定點**——程式依草稿
                    # 發出（`wd_program`；F12 r6 起含提議轉成的程式呼叫 `proposal_program`）的 `confirm.request`、
                    # 且本回合候選集已選定；其餘呼叫一律不帶（`ToolRegistry.call` 預設 `None`）。
                    # ⛔ 讀 `raw_args`／`args.payload`。
                    call_kwargs: dict = {}
                    if (wd_program or proposal_program) and name == CONFIRM_TOOL_NAME:
                        # F12 r6（§11.4 第 2 點「出卡入口的關口」；V7-2）：程式依草稿發出的兩個入口同一個關口——
                        # 候選集已撤回且仍綁定 ⇒ 整次改成重列同一份 `ids`（`confirm.request` ⛔ 執行、選對紀錄
                        # `scope_pick` 帳單解析 ⛔ 做）。
                        _post = self._write_candidates_post_pick(acc, identity)
                        if _post is not None and _wc.is_withdrawn(_post):
                            acc.violations.append(_wc.V_CANDIDATE_RELIST_WITHDRAWN)
                            _relist_rows = await self._write_candidates_relist_rows(acc, identity)
                            return self._write_candidates_relist_exit(
                                acc, identity, agent_state, user_message, _relist_rows)
                        # F12 r6（V7-2）：提議轉成的程式呼叫在候選集已選定且仍綁定時也帶 `program_pick`（⛔ 重列蓋掉
                        # 選定）；其餘（未選定、沒有候選集、解綁）⇒ 與改動前相同（不帶）。
                        _program_pick = (
                            self._write_candidates_program_pick(acc, identity, agent_state)
                            if wd_program else self._write_candidates_proposal_pick(acc, identity))
                        if _program_pick is not None:
                            call_kwargs["program_pick"] = _program_pick
                    # 名稱寬鬆比對脈絡 `name_lenient` 的**唯一設定點**（B2 (3) 另經
                    # `write_name_candidates`／r4 `missing_name_lenient` 傳）——`confirm.request` 內 (甲) 查無與
                    # (乙) 缺名稱兩個觸發點共用它。程式依草稿發出（`wd_program`／提議轉成的程式呼叫）的
                    # `confirm.request`、本回合未帶程式選定、候選集可寫的回合。帶它的呼叫 registry 逾時加長
                    # `NAME_LENIENT_EXTRA_TOOL_TIMEOUT_S`（內含一次模型呼叫＋一次清單查詢）。
                    call_timeout_s = self._tool_timeout_s
                    if ((wd_program or proposal_program) and name == CONFIRM_TOOL_NAME
                            and "program_pick" not in call_kwargs):
                        _cp = _payload_of(raw_args)
                        _nl = self._name_lenient_ctx(
                            acc, agent_state, document, _cp.get("action") if _cp is not None else None,
                            identity=identity)
                        if _nl is not None:
                            call_kwargs["name_lenient"] = _nl
                            call_timeout_s = self._tool_timeout_s + NM.NAME_LENIENT_EXTRA_TOOL_TIMEOUT_S
                    call_start = self._clock()
                    try:
                        tool_result = await self.registry.call(
                            identity,
                            name,
                            raw_args,
                            call_timeout_s,
                            stage=self._stage,
                            readonly_view=self.readonly_view,
                            for_model=True,
                            **call_kwargs,
                        )
                    except Exception as exc:  # registry 不可用（例外）
                        acc.violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
                        return _finalize(acc.build_fixed("tool_unavailable", clock=self._clock), is_fixed=True)

                    if tool_result.error == "TOOL_TIMEOUT":
                        # W1：程式觸發的那一次跳過預算檢查點（迴圈前段與這裡兩處）且不計入。
                        if not wd_program and acc.counters.tool_call_exhausted(self.budget):
                            budget_hit = True
                            break
                        if not wd_program:
                            acc.counters.tool_calls += 1  # 重試也計（design 預算表）
                        try:
                            tool_result = await self.registry.call(
                                identity,
                                name,
                                raw_args,
                                call_timeout_s,
                                stage=self._stage,
                                readonly_view=self.readonly_view,
                                for_model=True,
                                **call_kwargs,
                            )
                        except Exception as exc:
                            acc.violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
                            return _finalize(acc.build_fixed("tool_unavailable", clock=self._clock), is_fixed=True)
                        if tool_result.error == "TOOL_TIMEOUT":
                            return _finalize(
                                acc.build_fixed("tool_unavailable", clock=self._clock), is_fixed=True
                            )

                    # DSP-091 DG-1：每次 `confirm.request` 經 registry 執行（出卡或回缺欄）⇒ 本回合加且只加
                    # 一筆來源標記（只加字串，⛔ 改任何分支、出卡、執行或回傳）。
                    if name == CONFIRM_TOOL_NAME:
                        if wd_program:
                            _csrc = "program_draft"
                        elif proposal_program:
                            _csrc = "program_proposal"
                        elif doc_program:
                            _csrc = "program_document"
                        else:
                            _csrc = f"model:{confirm_model_reason}"
                        acc.violations.append(CONFIRM_SOURCE_PREFIX + _csrc)

                    # 候選形狀只在**程式依草稿發出**的呼叫（`wd_program`／
                    # 提議轉成的程式呼叫）寫候選集、列清單；文件回合、文件暫存回合、點選範圍回合、影子回合、
                    # 模型自呼 ⇒ 換回現行出口（帳單 `select:bill`、其餘缺欄追問）。開關未生效時
                    # `confirm.request` 不回候選形狀，這段不動任何東西。
                    cand_write = False
                    if name == CONFIRM_TOOL_NAME and is_candidate_shape(tool_result):
                        cand_write = self._write_candidates_eligible(
                            acc, agent_state, tool_result.data, document=document,
                            program_call=wd_program or proposal_program)
                        if not cand_write:
                            tool_result = candidate_fallback_result(tool_result)

                    # 一次性照片建議：`confirm.request` 一回來就用掉（⛔ 不讓上一張照片補到
                    # 之後另一張無關的單）——**唯一例外**是 `INVALID_INPUT`（缺欄／形狀不合 ⇒
                    # 要先追問）：站內幫手 S3（§3h 第 6 點）「缺欄追問失敗不消耗」，使
                    # 「先追問再出卡」仍附得到照片。出卡那一刻另在 `_begin_pending_confirm` 清。
                    # A-2a：列寫入候選（還沒出卡、選定後回原流程出卡）同「先追問」，不消耗。
                    # F12：「找不到這個名稱」同「先追問」（請使用者重講名稱），不消耗。
                    name_not_found = (name == CONFIRM_TOOL_NAME and "name_lenient" in call_kwargs
                                      and is_name_not_found(tool_result) is not None)
                    if (name == CONFIRM_TOOL_NAME and tool_result.error != "INVALID_INPUT"
                            and not cand_write and not name_not_found):
                        AgentSession(agent_state).consume_image_suggestion()
                    # W1（§2.1(5)）：本回合模型**自己**成功呼叫過 `confirm.request` ⇒ 不再程式觸發。
                    # A+ 片 AP-1：三個開關皆 on ⇒ 不再設（模型自呼只是提議）。
                    if (name == CONFIRM_TOOL_NAME and not wd_program and not proposal_program
                            and tool_result.ok and acc.write_draft is not None
                            and not self._write_proposal_active()):
                        acc.write_draft.model_confirm_ok = True

                    # L15 (a)③：**範圍比對排在這裡**——`registry.call` 一回來、
                    # 進 trace／`tool_results_by_id`／`_wrap`／messages 之前。
                    # 替換是就地改同一個 `ToolResult` 物件 ⇒ 底下每一個下游拿到
                    # 的都是替換後那一份（⛔ 原 facts 不進 messages／provenance）。
                    if scope_estate_id is not None:
                        _q = raw_args.get("ref") or raw_args.get("keyword")
                        _outcome = _enforce_tool_scope(
                            name, tool_result, scope_estate_id,
                            _q if _q is None or isinstance(_q, str) else str(_q),
                            acc.violations,
                        )
                        if _outcome == "in":
                            acc.scope_counts["in"] += 1
                        elif _outcome == "out":
                            acc.scope_counts["out"] += 1

                    # 第六批 #10 **寫點 (c)**：模型自己查 estates 且**對到唯一一個
                    # 物件** ⇒ 記起來（Plan 第六批 B 欄的來源①「查詢工具回傳唯一
                    # 物件」）。使用者整句就是物件名稱（「基隆獨立共生公寓」8 字，
                    # 過不了 `_pre_lookup_trigger` 的 6 字閘）時，模型本來就會拿
                    # 整句當 `keyword` 查一次——**接在那一次查詢上**，因此
                    # ⛔ 不另打一次 API、⛔ 不另建物件名稱表。
                    # ⚠️ 排在範圍比對**之後**：範圍外的結果已經被 `_scope_replace_result`
                    #    換成空殼（沒有 `scope`／`candidates`）⇒ 自然寫不進去。
                    # ⚠️ 只認 `keyword` 查詢：`ref` 查詢的「名稱」會是一個編號，
                    #    那不是物件名稱（`_write_estate_carry` 對空名稱直接不寫）。
                    if name == _PRE_LOOKUP_ESTATE_TOOL and tool_result.ok:
                        _kw = raw_args.get("keyword")
                        _carry = _estate_carry_from_estates_data(
                            tool_result.data, _kw if isinstance(_kw, str) else ""
                        )
                        if _carry is not None and _write_estate_carry(agent_state, *_carry):
                            acc.violations.append("estate_carry_set")

                    ms = int((self._clock() - call_start) * 1000)
                    status_value = _tool_result_status(tool_result)
                    # T2：撞名保留 id 的那筆沒有真的登記進 `tool_results_by_id`——
                    # 它不是「查了、查無資料」，`empty` 一律 `False`（§2）。
                    is_reserved_collision = tc.id in reserved_ids
                    record_empty = (
                        False if is_reserved_collision
                        else _tool_result_empty(tool_result, status_value)
                    )
                    # Plan 9.11 §2 D：`grounded` 的**唯一計算點**——純由
                    # `ToolResult` 算，⛔ 不查 registry、⛔ 不讀工具名。與
                    # `empty` 互斥（`not record_empty`）；撞保留 id 的那筆
                    # 一律 `False`（它不是「查了、查無資料」，也不是「查到
                    # 資料」——這筆根本沒有真的登記進 `tool_results_by_id`）。
                    record_grounded = (
                        not is_reserved_collision
                        and status_value == "ok"
                        and not record_empty
                        and any(
                            p.citable and p.text.strip()
                            for p in (tool_result.provenance or [])
                        )
                    )
                    acc.tool_call_records.append(
                        ToolCallRecord(
                            id=tc.id,
                            name=name,
                            args_summary=_args_summary(raw_args),
                            ms=ms,
                            status=status_value,
                            n_items=_tool_result_n_items(tool_result),
                            empty=record_empty,
                            grounded=record_grounded,
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
                        acc.violations.append("tool_call_id_collides_with_reserved")
                    else:
                        acc.tool_results_by_id[tc.id] = tool_result
                    # DSP-038-2／W3「確認回合」：`confirm.request` 一成功，這一回合
                    # **立刻結束**——`TurnResult.answer` 逐字＝程式產出的確認卡，
                    # 模型當回合的輸出丟棄、Verifier 不跑（卡不是模型寫的，沒有可
                    # 驗的引用）。⛔ 不把卡交回模型讓它「潤飾一下」：那一潤，
                    # 使用者看到的字就不再等於 `summary_sha256` 綁住的那一份。
                    # 站內幫手 S2（§3f 2，S2-live 修正）：`confirm.request` 回缺欄清單 ⇒
                    # **程式直接追問、結束回合**（同確認卡：程式產出、⛔ 交模型改寫）。
                    # 模型自己寫的追問常含「請提供／需要」，命中 Verifier `assertion_terms`
                    # 被降級成無引用斷言、重寫兩次後轉人。文件回合不走這裡（照舊交模型、
                    # 由文件寫入禁令處理）；清單含詞彙外的值 ⇒ `None` ⇒ 照原路交模型。
                    # 寬鬆也落空 ⇒ 程式固定句結束回合（只會出現在帶 `name_lenient` 的
                    # 程式呼叫；排在缺欄追問與查無出口之前——它不帶查無標記、也不是缺欄結果）。
                    if name_not_found:
                        nf_turn = self._name_lenient_not_found_exit(
                            acc, identity, agent_state, user_message, tool_result, document)
                        if nf_turn is not None:
                            return nf_turn
                    if name == CONFIRM_TOOL_NAME and isinstance(tool_result.data, dict) \
                            and isinstance(tool_result.data.get("missing_fields"), list):
                        # F12（§4.4；主會話裁第 3 項）：上回合「找不到這個名稱」追問的名稱欄，本回合重問同一欄。
                        _relabeled = self._name_lenient_reask_labels(
                            acc, tool_result.data.get("action") or (_payload_of(raw_args) or {}).get("action"),
                            tool_result.data["missing_fields"])
                        if _relabeled != tool_result.data["missing_fields"]:
                            tool_result = tool_result.model_copy(
                                update={"data": dict(tool_result.data, missing_fields=_relabeled)})
                    missing_ask = (
                        missing_fields_ask_text(tool_result)
                        if name == CONFIRM_TOOL_NAME and document is None else None
                    )
                    # 站內幫手 S3（§3h 第 3 點）：程式追問出口擴大到「放行對照內的文件回合」
                    # （文件暫存有效的回合本來就沒有 `document`，已在上一條路上）。
                    if missing_ask is None and name == CONFIRM_TOOL_NAME and doc_action is not None:
                        missing_ask = missing_fields_ask_text(tool_result)
                    if missing_ask is not None:
                        acc.violations.append("confirm_missing_fields_ask")
                        _missing = (tool_result.data or {}).get("missing_fields") or []
                        # W1b §8.5-1：程式缺欄追問出口是 `asked` 的唯一寫點。
                        self._write_draft_record_asked(
                            acc, identity, agent_state, tool_result, raw_args, document)
                        # F12 r6-3 (a)：本回合打字改選成立、還沒出卡 ⇒ 追問前加告知固定句（系統正名與編號）；
                        # dialog 寫不含名稱的程式摘要。其餘回合 `_repick_notice is None` ⇒ 與改動前逐字相同。
                        _repick_notice = (self._write_candidates_repick_notice(acc)
                                          if (wd_program or proposal_program) else None)
                        if _repick_notice is not None:
                            return self._finish_confirm_turn(
                                ask_target=WF.ask_target_for_missing(_missing),
                                agent_state=agent_state, user_message=user_message,
                                trace_id=acc.trace_id, start=acc.start, kind="ask",
                                outcome=make_outcome("clarifying", expects="text"),
                                answer=f"{_repick_notice}\n{missing_ask}",
                                dialog_answer=f"{_wc.CANDIDATE_REPICK_DIALOG_SUMMARY}\n{missing_ask}",
                                pending_id=None, tool_calls=acc.tool_call_records,
                                violations=acc.violations, llm_calls=acc.llm_calls,
                                prompt_tokens=acc.prompt_tokens,
                                completion_tokens=acc.completion_tokens,
                            )
                        return self._finish_confirm_turn(
                            # W1（§2.1(1)）：追問對象由表導出（與改動前逐位相同）。
                            ask_target=WF.ask_target_for_missing(_missing),
                            agent_state=agent_state,
                            user_message=user_message,
                            trace_id=acc.trace_id,
                            start=acc.start,
                            kind="ask",
                            outcome=make_outcome("clarifying", expects="text"),
                            answer=missing_ask,
                            pending_id=None,
                            tool_calls=acc.tool_call_records,
                            violations=acc.violations,
                            llm_calls=acc.llm_calls,
                            prompt_tokens=acc.prompt_tokens,
                            completion_tokens=acc.completion_tokens,
                        )
                    # 2026-10-15 正式機：統計端點（jgb2-req#16～#18）JGB 尚未開放 ⇒ **程式固定句
                    # 結束回合**（同下方查無出口：程式產出、⛔ 交模型改寫——實測模型會改成轉人或
                    # 反問「想處理哪一件事？」）。
                    if document is None and _is_stats_not_supported(name, tool_result):
                        acc.violations.append("jgb2_stats_not_supported_exit")
                        if name == CONFIRM_TOOL_NAME:
                            # W1（§2.1(5)）：`WRITE_NOT_SUPPORTED` ⇒ 草稿清掉（⛔ 留 Email／電話）。
                            self._write_draft_clear(acc, agent_state)
                        return self._finish_confirm_turn(
                            agent_state=agent_state,
                            user_message=user_message,
                            trace_id=acc.trace_id,
                            start=acc.start,
                            kind="answer",
                            outcome=make_outcome("answered", expects="text"),
                            answer=tool_result.data["facts"],
                            pending_id=None,
                            tool_calls=acc.tool_call_records,
                            violations=acc.violations,
                            llm_calls=acc.llm_calls,
                            prompt_tokens=acc.prompt_tokens,
                            completion_tokens=acc.completion_tokens,
                        )
                    # 站內幫手 S5 修正輪（§3i 第 2 點停止條件、A1／A3(b)）：**查無 ⇒ 程式固定句
                    # 結束回合**（同上方缺欄追問：程式產出、⛔ 交模型改寫）。S5-live 11 次只有 4 次
                    # 引用查無句，其餘被模型改成反問或轉人。條件全為封閉值：
                    #   ① `jgb2.query.*` 或 `confirm.request`（出卡端物件／合約解析零筆）；
                    #   ② 帶查無標記（`_is_marked_not_found`：`jgb2.NOT_FOUND_SOURCE`）——
                    #      無標記的 `NO_MATCH`＝沒查成，照舊交模型（⛔ 說查不到）；
                    #   ③ 非文件回合（`document is None`）；
                    #   ④ 本回合還沒有任何查到的資料（工具 `grounded` 紀錄或前置查詢命中）——
                    #      已有資料時程式說「查不到」會與那份資料矛盾，照舊交模型（手上有可引用的
                    #      查無句）。
                    if (
                        document is None
                        and (name.startswith(_JGB2_QUERY_PREFIX) or name == CONFIRM_TOOL_NAME)
                        and _is_marked_not_found(tool_result)
                        and not any(r.grounded for r in acc.tool_call_records)
                        and not (acc.snapshot.pre_lookup_trace or {}).get("hits")
                    ):
                        acc.violations.append("jgb2_not_found_exit")
                        return self._finish_confirm_turn(
                            agent_state=agent_state,
                            user_message=user_message,
                            trace_id=acc.trace_id,
                            start=acc.start,
                            kind="answer",
                            outcome=make_outcome("answered", expects="text"),
                            answer=PRE_LOOKUP_NOT_FOUND_TEXT,
                            pending_id=None,
                            tool_calls=acc.tool_call_records,
                            violations=acc.violations,
                            llm_calls=acc.llm_calls,
                            prompt_tokens=acc.prompt_tokens,
                            completion_tokens=acc.completion_tokens,
                        )
                    if name == CONFIRM_TOOL_NAME and tool_result.ok:
                        # W9-1 第三道網：文件回合 ⛔ 不出確認卡。排在
                        # `_scope_gate_confirm_request` **之前**（形狀與落點比照
                        # 它）——`confirm.request` 已經在上面被擋掉執行，走到這裡
                        # 代表 `doc_write_face` 算漏了（例如某支寫入工具兩個旗標
                        # 都沒設），這一道是那種情況下的最後一擋。
                        # 站內幫手 S3：條件改為「kind 不在放行對照、或出卡的動作不是該 kind
                        # 對應的動作」（放行對照的唯一來源同上）。
                        _card_action = (
                            tool_result.data.get("action")
                            if isinstance(tool_result.data, dict) else None
                        )
                        if document is not None and (
                            doc_action is None or _card_action != doc_action
                        ):
                            return self._document_turn_no_write(
                                document, agent_state=agent_state,
                                user_message=user_message, trace_id=acc.trace_id,
                                start=acc.start, violations=acc.violations,
                                tool_calls=acc.tool_call_records, llm_calls=acc.llm_calls,
                                prompt_tokens=acc.prompt_tokens,
                                completion_tokens=acc.completion_tokens,
                            )
                        # L15 (a)⑥／L15-03：**寫入路徑的邊界**。⛔ 不靠讀路徑
                        # 的比對——`confirm.request` 的 payload 是模型自己填的，
                        # 它可以完全不查就直接出一張別戶的卡。
                        # ⚠️ 閘門放在**呼叫點**而非 `_begin_pending_confirm` 內：
                        #    那支是同步函式，而 `bill_due_extend` 的邊界要現查一次
                        #    帳單（await registry.call）。兩者相鄰、同一個出口，
                        #    行為等同「有範圍且別戶 ⇒ 不建 pending、回固定句」。
                        scope_turn = await self._scope_gate_confirm_request(
                            identity, agent_state, tool_result.data,
                            trace_id=acc.trace_id,
                            start=acc.start,
                            user_message=user_message,
                            tool_calls=acc.tool_call_records,
                            violations=acc.violations,
                            llm_calls=acc.llm_calls,
                            prompt_tokens=acc.prompt_tokens,
                            completion_tokens=acc.completion_tokens,
                        )
                        if scope_turn is not None:
                            # W1（§2.1(5)）：範圍閘不過 ⇒ 草稿清掉。
                            self._write_draft_clear(acc, agent_state)
                            return scope_turn
                        confirm_turn = self._begin_pending_confirm(
                            agent_state,
                            tool_result.data,
                            identity=identity,
                            trace_id=acc.trace_id,
                            start=acc.start,
                            user_message=user_message,
                            tool_calls=acc.tool_call_records,
                            violations=acc.violations,
                            llm_calls=acc.llm_calls,
                            prompt_tokens=acc.prompt_tokens,
                            completion_tokens=acc.completion_tokens,
                            # A+ 片 AP-4：只有程式依草稿發出的呼叫（`wd_program` 或 AP-1 區域旗標）
                            # 才帶「這次送出的 payload 中屬於 to_payload(草稿) 的鍵」。
                            draft_payload=(
                                _sent_draft_payload(raw_args, program_payload_keys)
                                if wd_program or proposal_program else None
                            ),
                            # A-2a：候選形狀且本呼叫可寫候選集（上方 `cand_write`）⇒ 列清單結束回合。
                            write_candidates=cand_write,
                            candidate_field_value=(
                                self._write_candidates_field_value(acc, tool_result.data)
                                if cand_write else None
                            ),
                            # A-2a 修正 1：這次呼叫帶了 `program_pick`（只有 `wd_program` 呼叫點會設）⇒ 出的卡
                            # 在待確認筆帶著選定（卡後更正重出卡時帶回）。
                            card_pick=self._write_candidates_card_pick_record(
                                acc, identity, call_kwargs.get("program_pick")),
                            # UD-3：照片分類跟著卡走（卡後更正重出卡時帶回）。
                            photo_suggestion=_card_photo_suggestion,
                            # 「選對紀錄」片 §4.3：打字選定不成立的重列、或回合開始就有未選定的候選集而重查後
                            # 仍多筆 ⇒ 前導句說「依您目前說的仍對到 N 筆」（開關 off 時 exit 不用這個值）。
                            candidate_reask=bool(
                                cand_write and acc.write_draft is not None
                                and (acc.write_draft.reask
                                     or (acc.write_draft.candidates is not None
                                         and not acc.write_draft.picked))),
                            # 填欄擴及首句、卡後、多欄回合（plan-fill-wide-20261028 §4.3 第 8 點）：程式依草稿出卡（卡＝草稿值）
                            # 且寬回合卡後有欄位被資料段拒收 ⇒ 卡前加點名欄位標籤的固定句（⛔ 帶值）。其餘 ⇒ `None`。
                            lead=(self._fill_wide_notice(acc.write_draft)
                                  if wd_program or proposal_program else None),
                        )
                        if confirm_turn is not None:
                            return confirm_turn
                    if proposal_program:
                        # A+ 片 AP-1 (3)：提議轉成的程式呼叫是**非終結**結果（無缺欄清單的
                        # `INVALID_INPUT`、無查無標記的 `NO_MATCH`、`DATE_BEFORE_TODAY`…）⇒ 比照
                        # `wd_program` 區塊：記 `V_PROGRAM_NONTERMINAL`，先過 #9b 出口（綁定卡已燒、這次
                        # 沒出成新卡 ⇒ 固定句結束回合；安全審查 1-1）。B 片 B1：寫入情境的非問句回合 ⇒
                        # 程式狀態回話結束回合（⛔ 再叫主模型）；問句回合（Q1 乙′）才回填結果、交回模型
                        # ——模型只寫知識作答（DSP-091 歸 AI），寫入回話仍由程式（一般出口的 B2／乙′）。
                        acc.violations.append(WF.V_PROGRAM_NONTERMINAL)
                        not_issued = self._write_draft_reissue_not_issued_exit(
                            acc, agent_state, user_message)
                        if not_issued is not None:
                            return not_issued
                        kd3_hand_back = True
                    # ⚠️ **槽位寫回 state（2.9，⛔ 勿刪）**：`session.slots.set` 是
                    #    以 `jsonb_set` 直接改 `form_sessions.collected_data.slots`
                    #    的，但回合結束時呼叫端（`mcp_facade._agent_turn`）
                    #    會用手上這份 `state`
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
                    # 見 `_build_turn_context` 的 `TurnAccumulator(nonce=new_nonce(), …)`）。
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
                                acc.nonce,
                            )
                        return wrap_tool_data(tool_label, raw_tool_text, acc.nonce)

                    try:
                        tool_content = _wrap(name)
                    except ValueError:
                        # 模型送的 tool 名不合形狀守門（例如空白／標記字元）——
                        # registry.call 已經用它判過 NO_MATCH／FORBIDDEN，這裡只是
                        # 包裝層，⛔ 不因此讓整回合崩潰。
                        acc.violations.append(f"BAD_TOOL_NAME:{name!r}")
                        tool_content = _wrap("tool")
                    acc.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_content,
                        }
                    )

                if budget_hit:
                    return _finalize(acc.build_fixed("budget_exhausted", clock=self._clock), is_fixed=True)
                if wd_program:
                    # W1（§2.1(5)）：程式觸發的結果是**非終結**（無缺欄清單的 `INVALID_INPUT`、未帶
                    # 查無標記的 `NO_MATCH`…）⇒ ⛔ 撤回任何東西：工具結果已照常回填，迴圈再叫一次
                    # 模型，模型的下一個輸出走 T2／V2／Verifier／出口閘的正常路徑（同
                    # `_document_program_message`）；本回合不再觸發（`triggered`）。
                    acc.violations.append(WF.V_PROGRAM_NONTERMINAL)
                    # 第 3 步 #9b（Q5）：A2 已燒掉綁定卡、這次又沒出成新卡 ⇒ 程式固定句結束回合。
                    not_issued = self._write_draft_reissue_not_issued_exit(
                        acc, agent_state, user_message)
                    if not_issued is not None:
                        return not_issued
                    # B 片 B1：寫入情境的非問句回合 ⇒ 程式狀態回話結束回合（⛔ 再叫主模型）；問句回合
                    # （Q1 乙′）照上面註解回填、交回模型——模型只寫知識作答（DSP-091 歸 AI；同提議分支）。
                    kd3_hand_back = True
                if kd3_hand_back:
                    kd3_exit = await self._write_reply_kd3_exit(
                        acc, identity, agent_state, user_message, write_entry=write_entry)
                    if kd3_exit is not None:
                        return kd3_exit
                if wd_program and self._write_candidate_button_turn(acc):
                    # 按鈕選定回合 ⛔ 呼叫主模型——程式觸發的結果非終結 ⇒ 由程式狀態
                    # 回話結束回合（B 片開關 off 時亦同）。
                    return await self._write_reply_program_exit(acc, identity, agent_state, user_message)
                continue  # 工具結果已回填，回到迴圈頂端再叫一次模型

            # 無 tool_calls ⇒ 這一回合模型嘗試給最終答案
            acc.attempt_no += 1
            content = getattr(message, "content", None) or ""
            try:
                payload = json.loads(content)
                out = AgentOutput.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, TypeError):
                # 正式接線 §3.2：開關關閉 ⇒ `extracted` 恆為 None，走下方與改前逐字相同的 SCHEMA 改寫。
                extracted = self._extract_agent_output(content) if self._clean_llm_output else None
                if extracted is not None:
                    # 之後各改寫路徑 append 的 assistant 內容＝擷取出的那個物件（⛔ 帶前後雜字）。
                    payload, out = extracted
                    content = json.dumps(payload, ensure_ascii=False)
                    acc.violations.append(LLM_OUTPUT_JSON_EXTRACTED)
                else:
                    if self._attempt_sink is not None:
                        self._emit_attempt(
                            {
                                "attempt": acc.attempt_no,
                                "kind": None,
                                "raw_len": len(content),
                                "verdict": {"reason": "SCHEMA_PARSE"},
                            }
                        )
                    if cut_short:
                        # W2（W-R2／W-R9）：截斷 ⇒ 剩餘期限不足一次正常主呼叫就不重寫；
                        # 附回的內容一律剝推理段（若有）並去頭尾空白（不論 `clean_llm_output`、有無推理段）。
                        if (self.budget.deadline_s - (self._clock() - acc.start)) < SCHEMA_REWRITE_MIN_REMAINING_S:
                            return _finalize(acc.build_fixed("budget_exhausted", clock=self._clock), is_fixed=True)
                        content = (LO.final_segment(content) or "").strip()
                    acc.counters.rewrites += 1
                    if acc.counters.rewrite_exhausted(self.budget):
                        return _finalize(acc.build_fixed("budget_exhausted", clock=self._clock), is_fixed=True)
                    acc.messages.append({"role": "assistant", "content": content})
                    acc.messages.append(
                        {
                            "role": "user",
                            "content": rewrite_feedback("SCHEMA", "輸出不符 AgentOutput schema。"),
                        }
                    )
                    continue

            # E 片 §4.1-2（E-R4）：開關 on 時，主模型輸出的 `handoff_reason` 不在模型可見值域（含程式專用的
            # `user_request`）⇒ 視同自報 `no_grounding`，走現行降級閘（決定性，與 Verifier 觀察模式無關）。
            # off ⇒ 不加這道（與改前相同）。轉人由程式出口決定，主模型自報不是觸發來源。
            if (self._closing_active() and out.kind == "handoff"
                    and out.handoff_reason is not None
                    and out.handoff_reason not in MODEL_VISIBLE_HANDOFF_REASONS):
                acc.violations.append(WF.V_DIALOG_ACT_REASON_OUT_OF_DOMAIN)
                out = out.model_copy(update={"handoff_reason": HandoffReason.no_grounding.value})
            # E 片 §4.1-3 (c)：標籤未完成 ⇒ 至多再等 1 秒；已完成且是程式出口 ⇒ 改回程式結果。
            act_exit = await self._dialog_act_after_output(
                acc, identity, agent_state, user_message, cache=cache)
            if act_exit is not None:
                return act_exit

            # W1（§2.1(5)）插入點：`model_validate` 成功之後、`handoff_dict`／T2／V2／Verifier 之前——
            # 取用意圖判斷呼叫的結果（W1b：在這裡 await）並合併、整句填入，條件成立 ⇒ 程式自己發
            # 一次 `confirm.request`（模型這一輪的原始文字丟棄：卡與追問句皆為程式產出）。
            wd_message = await self._write_draft_after_output(
                acc, out, identity, agent_state, user_message, document)
            if wd_message is not None:
                program_message, program_kind = wd_message, "wd"
                continue
            reissue_exit = (self._write_draft_reissue_exit(acc, agent_state, user_message)
                            or self._write_draft_card_still_valid_exit(acc, agent_state, user_message)
                            or self._write_draft_submitted_exit(acc, agent_state, user_message))
            if reissue_exit is not None:
                return reissue_exit

            # B2：只看封閉欄位 `kind` 與結構規則 `_is_question`）：寫入情境回合中，
            # 非問句回合的任何非 handoff 回覆、問句回合的 `ask`／`recommend`（不論 `ask_target`）⇒ 模型文字
            # 丟棄、程式狀態回話結束回合；問句回合的 `answer` ⇒ 乙′（往下過 Verifier 與 B3，最後由程式
            # 接狀態行）。`handoff` 維持現行（DSP-021 固定句，轉人屬 E 片）。開關 off ⇒ 這段不跑。
            write_ctx: Optional[bool] = None
            write_reply_yi_prime = False
            if self._write_reply_active() and out.kind != "handoff":
                write_ctx = await self._write_context_turn(
                    acc, identity, agent_state, entry=write_entry)
                if write_ctx:
                    if _is_question(user_message) and out.kind == "answer":
                        write_reply_yi_prime = True
                    else:
                        return await self._write_reply_program_exit(
                            acc, identity, agent_state, user_message)

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

            # T2（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §3；
            # 條件改由 Plan 9.11 §2 D 重寫）：
            # 迴圈內改寫提示——與 `_reason_hint`／`_schema_reject_hint` 同形，
            # 介於模型輸出與 Verifier 之間。⛔ **不在出口閘另開一次模型呼叫**
            # （security r1 #1：那條路會跳過 Verifier 全部檢查且沒有 deadline
            # 檢查，正式站觀察模式不可用）。條件全為封閉欄位：`out.kind==
            # "handoff"` 且 `out.handoff_reason=="no_grounding"`（字面值，⛔ 不看
            # `handoff_dict` 那個已經套過 fallback 的版本）、`fact_class` 不在
            # 敏感五類、**本回合存在至少一筆 `grounded` 紀錄**（⚠️ 換掉了原本
            # 「非空且非全 empty」——只呼叫 `handoff.request`／只開導航清單／
            # 只 `kb.search` 不再算「查到資料」，那些回合現在走零查詢路徑
            # ③／A，見 Plan 9.11 §2 D「預期行為變化」）。命中且改寫預算未耗盡
            # ⇒ 消耗一次 `max_rewrites`、帶固定修法句重回模型；**預算已耗盡 ⇒
            # 直接跳過改寫**（⛔ 不走 `counters.rewrite_exhausted` ⇒
            # `build_fixed("budget_exhausted")` 那條，否則 `handoff_reason`
            # 會變成 `budget_exhausted`，T2 出口閘永遠到不了——plan-verifier
            # r1 #6），讓輸出照常往下走進 Verifier，最終落到
            # `_apply_handoff_data_exits` 換成 `NO_JUDGEMENT_TEXT`。
            if out.kind == "handoff" and out.handoff_reason in NON_SENSITIVE_HANDOFF_REASONS:
                try:
                    rewrite_fact_class = FactClass(out.fact_class)
                except ValueError:
                    rewrite_fact_class = None
                if (
                    rewrite_fact_class not in SENSITIVE
                    and any(r.grounded for r in acc.tool_call_records)
                    and not acc.counters.rewrite_exhausted(self.budget)
                ):
                    acc.counters.rewrites += 1
                    acc.messages.append({"role": "assistant", "content": content})
                    acc.messages.append(
                        {"role": "user", "content": rewrite_feedback("HANDOFF_DATA", HANDOFF_DATA_REWRITE_HINT)}
                    )
                    continue

            # V2（Plan batch4 §3；條件改由 Plan 9.11 §2 D 重寫）：**有前文的
            # 零查詢**——與上面那條 T2 改寫分支互斥（上面要求存在 `grounded`
            # 紀錄，這裡要求 `zero_lookup`，兩者不可能同時成立），⛔ 不會同回合
            # 觸發兩次改寫。條件全為封閉欄位：`out.kind=="handoff"`、
            # `handoff_reason` 非敏感、`fact_class` 不在敏感五類、
            # **`zero_lookup(acc.tool_call_records, acc.violations)`**
            # （⚠️ 換掉了原本「`tool_call_records` 為空」——只呼叫
            # `handoff.request`／只開導航清單的回合現在也算零查詢，同 T2 的
            # 放寬）、且本回合真的注入過「最近編號」資料段。命中且改寫預算
            # 未耗盡 ⇒ 消耗一次 `max_rewrites`、帶固定定義句重回模型；
            # **預算已耗盡 ⇒ 直接跳過改寫**（同上一條分支的坑：⛔ 不走
            # `counters.rewrite_exhausted` ⇒ `build_fixed("budget_exhausted")`
            # 那條，否則 `handoff_reason` 會變成 `budget_exhausted`，到不了
            # `_apply_handoff_without_lookup` 的 `ASK_TARGET_TEXT` 出口），讓輸出
            # 照常往下走，最終落到 `_apply_handoff_without_lookup` 的既有行為。
            if (
                out.kind == "handoff"
                and out.handoff_reason in NON_SENSITIVE_HANDOFF_REASONS
                and zero_lookup(acc.tool_call_records, acc.violations)
                and acc.snapshot.has_recent_refs
            ):
                try:
                    zero_lookup_fact_class = FactClass(out.fact_class)
                except ValueError:
                    zero_lookup_fact_class = None
                if (
                    zero_lookup_fact_class not in SENSITIVE
                    and not acc.counters.rewrite_exhausted(self.budget)
                ):
                    acc.counters.rewrites += 1
                    acc.messages.append({"role": "assistant", "content": content})
                    acc.messages.append(
                        {"role": "user", "content": rewrite_feedback("RECENT_REFS", RECENT_REFS_REWRITE_HINT)}
                    )
                    continue

            # DSP-029 F-A：引用解析在 Runtime 做，結果**另傳**給 Verifier——
            # ⛔ 不寫回 `out`／`Sentence` 任何欄位（解析後的原文一旦掛在 AgentOutput
            # 上，就會跟著 `decision_snapshot`／trace 外流）。
            # DSP-029a：**本回合的 `nonce` 一起傳進去**——標記裡的 nonce 必須等於它，
            # 否則 `ref_invalid`。這是「這串標記真的出自本回合資料段」的唯一憑據，
            # ⛔ 不得改成不檢查或用固定值。
            resolved, resolve_errors = resolve_refs(out, acc.tool_results_by_id, acc.nonce)
            # U3／W9-11：`audience` 傳的是 `identity.resolved_audience()` 的
            # **解析後封閉值**（`identity.Audience` 三值），⛔ 不傳 `target_user`
            # 原字串——那是上游可控的自由文字，Verifier 端對值域外一律照擋
            # （fail-closed），傳原字串只會讓「pm 放寬」在某些寫法下靜靜失效。
            # 第六批（單元 E 接線）：`document_turn` ＝**這一回合真的有文件事實
            # 進場**（有 `document` 且 `facts` 非空）。⚠️ 兩個條件都要：`facts`
            # 為空的文件回合走 `_document_program_turn` 的固定句、根本到不了這裡，
            # 而這一格若寫成「有沒有 document 物件」，日後那條早退一旦鬆動，
            # ⑥' 就會對一個沒有文件事實的回合生效。⛔ 非文件回合一律 `False`
            # ——那張表（「已建立」「要我匯入嗎」）在正常寫入回合是**正確的話**。
            verdict = self.verifier.verify(
                out, acc.tool_results_by_id, user_message, handoff_dict,
                resolved=resolved, resolve_errors=resolve_errors,
                audience=identity.resolved_audience(),
                document_turn=bool(document is not None and document.facts.strip()))
            acc.verifier_verdicts.append(verdict)
            # R1b（Plan R §0b／DSP-040 絆線）：**觀察模式下「本來會擋、這次只記錄」的
            # 類別要看得見**——`verdict.observed` 是封閉列舉（`"<reason>"` 或
            # `"SCHEMA:<cause>"`），⛔ 不攜帶任何模型文字或來源原文。就地累加：一個
            # 回合可能跑好幾次 Verifier（被拒→重寫→再驗），⛔ 不得只留最後一次。
            # ⛔ 不依賴 R2 的 `VerifierVerdict.observed_counts`（那一片還沒進來）。
            acc.verifier_observed_counts.update(
                Counter(acc.verifier_observed_counts) + Counter(verdict.observed)
            )
            if self._attempt_sink is not None:
                self._emit_attempt(
                    {
                        "attempt": acc.attempt_no,
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
                acc.counters.rewrites += 1
                logger.info(
                    "agent_verifier_reject trace_id=%s reason=%s rewrites=%d/%d",
                    acc.trace_id, verdict.reason, acc.counters.rewrites, self.budget.max_rewrites,
                )
                if acc.counters.rewrite_exhausted(self.budget):
                    return _finalize(acc.build_fixed("budget_exhausted", clock=self._clock), is_fixed=True)
                acc.messages.append({"role": "assistant", "content": content})
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
                acc.messages.append(
                    {
                        "role": "user",
                        "content": rewrite_feedback(
                            "VERIFIER_REJECT",
                            json.dumps(verdict.model_dump(), ensure_ascii=False)
                            + "　請依上述結構化拒因修正。"
                            + schema_hint,
                        ),
                    }
                )
                continue

            # T3（Plan §4）：**文字假確認**的旗標——三個封閉條件都成立（`kind=ask` ∧
            # `ask_target=confirm_intent` ∧ 本回合沒有 `confirm.request` 呼叫）才記；第四個條件
            # （模型散文是否真的在問「要不要送出」）是開放語義，⛔ 不判。這裡只記旗標；處置在下方
            # B 片 B3 判讀閘（開關 on：同三條件直接當「等待確認」未對到事件、換程式句；off：只記旗標）。
            if (
                out.kind == "ask"
                and out.ask_target == "confirm_intent"
                and not any(tc.name == CONFIRM_TOOL_NAME for tc in acc.tool_call_records)
            ):
                acc.violations.append("prose_confirm_suspect")

            # B 片 B3：帶狀態句判讀閘——一般出口唯一組裝點（下方 `normalize_terminal_punctuation`）之前、
            # Verifier 之後；`handoff` 不經。判讀只回類別（AI 理解），送不送、改送什麼由程式依狀態事件決定。
            claim_block: Optional[tuple] = None
            if self._state_claim_active() and out.kind != "handoff":
                card_capable = bool(write_entry["document"] or write_entry["doc_carry"]
                                    or write_entry["select_scope"])
                if not card_capable:
                    if write_ctx is None:
                        write_ctx = await self._write_context_turn(
                            acc, identity, agent_state, entry=write_entry)
                    card_capable = bool(write_ctx)
                claim_block = await self._state_claim_gate(
                    acc, identity, agent_state, out, card_capable=card_capable)

            trace = acc.build_trace(
                final_kind=out.kind,
                handoff_reason=(handoff_dict or {}).get("reason"),
                clock=self._clock,
                # R1b：**只有這個出口**寫實值（Plan §0b）；其餘三個 `TurnTrace(`
                # 建構點一律取 `default_factory=dict` 的空 dict。
                observed_counts=acc.verifier_observed_counts,
                # 一般出口：`tool_calls`／`verifier`／`violations` 傳**同一個物件**
                # ——`_emit_agent_decision` 的形狀守門會就地改 `trace.candidate_ids`
                # 與 `trace.violations`，那個修正必須反映到呼叫端讀到的 `result.trace`
                # 上（⛔ 不得改成副本；固定句出口才是副本，見 `build_fixed`）。
                copy_lists=False,
            )
            if claim_block is not None:
                # B3：未對到事件（或可出卡回合判讀失敗）⇒ 模型文字 ⛔ 送出、⛔ 進 dialog，程式換句。
                return await self._state_claim_replace_exit(
                    acc, identity, agent_state, user_message, claim_block,
                    write_ctx=bool(write_ctx), trace=trace)
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
            if write_reply_yi_prime:
                # B 片乙′：模型文字（已過 Verifier、B3）＋程式狀態行；`ask_target` 強制 `None`。
                return await self._write_reply_model_plus_status(
                    acc, identity, agent_state, user_message, result, cache=cache)
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
