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
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional, Protocol

from pydantic import ValidationError

from services import usage_metering
from services.agent.agent_session import AgentSession
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
from services.agent.document_extract import DocumentTurnInput
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
from services.agent.question_sensitivity import question_sensitive
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
from services.agent.tools.jgb2 import _bill_format_date as _jgb2_bill_format_date
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
CONFIRM_CANDIDATES_MAX = 5
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
#: 描述沒人講時填 `IMAGE_DESCRIPTION_TEMPLATE`（業主 2026-09-10 撤銷 S9-11：辨識描述（淨化、
#: 截長）優先，缺則部位＋原因短標籤，再缺退分類名；⛔ 這些文字只進修繕單描述，不進模型資料段）。
#: 一次性：任何 `confirm.request` 呼叫即清；新照片覆寫。
IMAGE_SUGGESTION_KEY = "image_suggestion"
IMAGE_DESCRIPTION_TEMPLATE = "照片辨識：{label}"


def _image_description_label(suggestion: dict) -> str:
    """描述用的文字：辨識描述優先（業主 2026-09-10）；缺 ⇒ 部位＋原因；都缺 ⇒ 分類名。"""
    desc = suggestion.get("description")
    if isinstance(desc, str) and desc.strip():
        return desc.strip()
    item = suggestion.get("item") if isinstance(suggestion.get("item"), str) else ""
    reason = suggestion.get("reason") if isinstance(suggestion.get("reason"), str) else ""
    label = f"{item}{reason}".strip()
    return label or str(suggestion.get("category_name") or "").strip()


def _apply_image_suggestion_to_confirm_args(raw_args: Any, suggestion: Any) -> tuple:
    """`confirm.request`／`repair_create` 的 payload 缺 `category_name`／`description`
    時由照片建議補上。回 `(new_args, applied)`；`applied` 是補了哪些欄位的清單
    （空＝原樣）。任何形狀不對（非 dict、payload 非 JSON 物件、action 非
    repair_create、建議缺值）一律原樣回傳，⛔ 不在此 raise——形狀由 confirm 工具自己驗。
    只補**缺值**（鍵不存在、None、去空白為空）；模型有給就不動。"""
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
    if not isinstance(payload, dict) or payload.get("action") not in CONFIRM_ACTIONS:
        return raw_args, []
    existing = payload.get("estate_name")
    if existing is not None and not (isinstance(existing, str) and not existing.strip()):
        return raw_args, []
    payload["estate_name"] = name.strip()
    new_args = dict(raw_args)
    new_args["payload"] = json.dumps(payload, ensure_ascii=False)
    return new_args, ["estate_name"]


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
        ref_id = item.get("ref_id")
        if isinstance(ref_id, str) and _PRE_LOOKUP_ID_RE.match(ref_id):
            _add(ref_id)
    return ordered[:_RECENT_REFS_MAX]


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
    **只走修繕單描述**（業主 2026-09-10 撤銷 S9-11「照片內文字不進修繕單」），
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
    #: 業主 2026-09-10 裁：辨識的部位／原因**短標籤**（門面 `_short_label` 過濾：只留中英字母、
    #: ≤12 字）；只用來組修繕單描述「照片辨識：{部位}{原因}」，⛔ 不進模型資料段。
    suggested_item: Optional[str] = None
    suggested_reason: Optional[str] = None
    #: 業主 2026-09-10 撤銷 S9-11：辨識描述（淨化、≤200 字）可進修繕單描述；⛔ 不進模型資料段。
    suggested_description: Optional[str] = None

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
        document_trace: Optional[dict] = None,
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
        # T1：三個寫點之一（⛔ 不得移到函式尾端）——R3：與下方 `fixed_streak`／
        # `dialog` 兩個寫點一起收進 `AgentSession.end_turn`（見下方單一呼叫；
        # `ask_target=None`／`is_fixed=False` 逐字＝原本這裡與下方兩行各自的值，
        # 這條路徑 ⛔ 不進 `handoff_cache`——不傳 `cache`）。
        session = AgentSession(agent_state)
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
            ask_target=None,
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
            if tool_result.error == _PRE_LOOKUP_NOT_FOUND_ERROR:
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
            AgentSession(agent_state).write_select_scope(
                {"type": select_type, "estate_id": str(row_estate)}
            )

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
                cand_payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
                query = " ".join(
                    str(cand_payload.get(k) or "") for k in ("estate_name", "period")
                ).strip() or None
                text = CONFIRM_CANDIDATES_TEXT + "\n" + _jgb2_candidates_text(domain, query, rows)
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
                    dialog_answer=text,
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
            or action not in CONFIRM_ACTIONS
            or not isinstance(payload, dict)
        ):
            violations.append("confirm_request_data_shape_invalid")
            return None
        session = AgentSession(agent_state)
        # 出卡成功 ⇒ 照片建議用掉了，清掉（⛔ 不讓它再補到下一張無關的單）。
        session.consume_image_suggestion()
        # 第六批 #10 **寫點 (a)**：出卡成功 ⇒ 這張卡上的物件就是「本對話最近提到
        # 的物件」。兩個值都是**封閉來源**：`estate_name` 是使用者剛才會在卡上看到
        # 的那一行（`confirm_card._render_repair_create` 的「物件」），`estate_id`
        # 是 `confirm.request` 自己查出來的（`tools/confirm.py::_open_repairs_hint`）。
        # ⛔ 不在這裡另外查一次；釘住範圍時 `_write_estate_carry` 自己不寫。
        _write_estate_carry(agent_state, payload.get("estate_name"), estate_id)
        pending_entry: dict = {
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
        if document is None or document.facts.strip():
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

        # ── 第三段：模型迴圈（第四段的四道出口閘由 `exit_gates.finalize` 收尾）──
        return await self._run_model_loop(
            acc, identity, user_message, state, agent_state,
            document=document, cache=cache, tool_specs=tool_specs,
            visible_names=visible_names, doc_write_face=doc_write_face,
            reserved_ids=reserved_ids, scope_estate_id=scope_estate_id,
        )

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
            identity, outline, user_message, dialog, acc.violations
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
        pre_trigger = _pre_lookup_trigger(user_message)
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

        # DSP-022：當前這句一定是最後一則 user 訊息（歷史由 assembler 從 `dialog` 放前面）。
        acc.messages.append({"role": "user", "content": user_message})
        # W8 (2)：影像事實以**可引用的工具事實**進場（r1 裁定接線）——包法與工具
        # 回傳完全相同（`wrap_provenance_data` ＋ 同回合 nonce），故模型引用它的
        # 句子解析得出來、過得了 Verifier（驗收 (xii)）。
        # ⛔ 不併進 `message`（那會變成使用者說的話）、⛔ 不經 `agent_state`。
        if image is not None and image.status in ("ok", "partial"):
            # 照片建議（封閉值）進 session：給之後回合的 `confirm.request` 補分類用。
            # 新照片一律覆寫（沒辨識出分類就寫 None，⛔ 不讓上一張的分類殘留到這張）。
            AgentSession(agent_state).write_image_suggestion(
                {
                    "category_name": image.suggested_category,
                    "item": image.suggested_item,
                    "reason": image.suggested_reason,
                    "description": image.suggested_description,
                }
                if isinstance(image.suggested_category, str) and image.suggested_category.strip()
                else None
            )
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
        return frozenset(
            s["name"]
            for s in self.registry.specs_for(
                identity, self._stage,
                readonly_view=self.readonly_view, for_model=True,
            )
            if s.get("scope") == "write" or s.get("mcp_only") or s.get("mutates_session")
        )

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
            return exit_gates.finalize(
                acc, result, is_fixed=is_fixed, verifier=self.verifier,
                cache=cache, agent_state=agent_state, user_message=user_message,
            )
        while True:
            if (self._clock() - acc.start) >= self.budget.deadline_s:
                return _finalize(acc.build_fixed("budget_exhausted", clock=self._clock), is_fixed=True)

            acc.llm_calls += 1
            create_kwargs = dict(
                model=self._model,
                messages=acc.messages,
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
            message = response.choices[0].message
            tool_calls = list(getattr(message, "tool_calls", None) or [])

            if tool_calls:
                acc.messages.append(_assistant_tool_call_message(message, tool_calls))
                budget_hit = False
                for tc in tool_calls:
                    if acc.counters.tool_call_exhausted(self.budget):
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

                    acc.counters.tool_calls += 1
                    if name == CONFIRM_TOOL_NAME:
                        raw_args, _applied = _apply_image_suggestion_to_confirm_args(
                            raw_args, agent_state.get(IMAGE_SUGGESTION_KEY)
                        )
                        for _field in _applied:
                            acc.violations.append(f"image_suggestion_applied:{_field}")
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
                        # 一次性：任何 `confirm.request` 呼叫（不論成敗）都把照片建議用掉，
                        # ⛔ 不讓上一張照片的分類補到之後另一張無關的單。
                        AgentSession(agent_state).consume_image_suggestion()
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
                        acc.violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
                        return _finalize(acc.build_fixed("tool_unavailable", clock=self._clock), is_fixed=True)

                    if tool_result.error == "TOOL_TIMEOUT":
                        if acc.counters.tool_call_exhausted(self.budget):
                            budget_hit = True
                            break
                        acc.counters.tool_calls += 1  # 重試也計（design 預算表）
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
                            acc.violations.append(f"REGISTRY_EXC:{type(exc).__name__}")
                            return _finalize(acc.build_fixed("tool_unavailable", clock=self._clock), is_fixed=True)
                        if tool_result.error == "TOOL_TIMEOUT":
                            return _finalize(
                                acc.build_fixed("tool_unavailable", clock=self._clock), is_fixed=True
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
                    acc.tool_call_records.append(
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
                        acc.violations.append("tool_call_id_collides_with_reserved")
                    else:
                        acc.tool_results_by_id[tc.id] = tool_result
                    # DSP-038-2／W3「確認回合」：`confirm.request` 一成功，這一回合
                    # **立刻結束**——`TurnResult.answer` 逐字＝程式產出的確認卡，
                    # 模型當回合的輸出丟棄、Verifier 不跑（卡不是模型寫的，沒有可
                    # 驗的引用）。⛔ 不把卡交回模型讓它「潤飾一下」：那一潤，
                    # 使用者看到的字就不再等於 `summary_sha256` 綁住的那一份。
                    if name == CONFIRM_TOOL_NAME and tool_result.ok:
                        # W9-1 第三道網：文件回合 ⛔ 不出確認卡。排在
                        # `_scope_gate_confirm_request` **之前**（形狀與落點比照
                        # 它）——`confirm.request` 已經在上面被擋掉執行，走到這裡
                        # 代表 `doc_write_face` 算漏了（例如某支寫入工具兩個旗標
                        # 都沒設），這一道是那種情況下的最後一擋。
                        if document is not None:
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
                            return scope_turn
                        confirm_turn = self._begin_pending_confirm(
                            agent_state,
                            tool_result.data,
                            trace_id=acc.trace_id,
                            start=acc.start,
                            user_message=user_message,
                            tool_calls=acc.tool_call_records,
                            violations=acc.violations,
                            llm_calls=acc.llm_calls,
                            prompt_tokens=acc.prompt_tokens,
                            completion_tokens=acc.completion_tokens,
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
                continue  # 工具結果已回填，回到迴圈頂端再叫一次模型

            # 無 tool_calls ⇒ 這一回合模型嘗試給最終答案
            acc.attempt_no += 1
            content = getattr(message, "content", None) or ""
            try:
                payload = json.loads(content)
                out = AgentOutput.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, TypeError):
                if self._attempt_sink is not None:
                    self._emit_attempt(
                        {
                            "attempt": acc.attempt_no,
                            "kind": None,
                            "raw_len": len(content),
                            "verdict": {"reason": "SCHEMA_PARSE"},
                        }
                    )
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
            # `counters.rewrite_exhausted` ⇒ `build_fixed("budget_exhausted")`
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
                    and acc.tool_call_records
                    and not all(r.status == "ok" and r.empty for r in acc.tool_call_records)
                    and not acc.counters.rewrite_exhausted(self.budget)
                ):
                    acc.counters.rewrites += 1
                    acc.messages.append({"role": "assistant", "content": content})
                    acc.messages.append(
                        {"role": "user", "content": rewrite_feedback("HANDOFF_DATA", HANDOFF_DATA_REWRITE_HINT)}
                    )
                    continue

            # V2（Plan batch4 §3）：**有前文的零查詢**——與上面那條 T2 改寫分支
            # 互斥（上面要求 `tool_call_records` 非空，這裡要求為空），⛔ 不會
            # 同回合觸發兩次改寫。條件全為封閉欄位：`out.kind=="handoff"`、
            # `handoff_reason` 非敏感、`fact_class` 不在敏感五類、本回合完全沒
            # 呼叫工具、且本回合真的注入過「最近編號」資料段。命中且改寫預算
            # 未耗盡 ⇒ 消耗一次 `max_rewrites`、帶固定定義句重回模型；
            # **預算已耗盡 ⇒ 直接跳過改寫**（同上一條分支的坑：⛔ 不走
            # `counters.rewrite_exhausted` ⇒ `build_fixed("budget_exhausted")`
            # 那條，否則 `handoff_reason` 會變成 `budget_exhausted`，到不了
            # `_apply_handoff_without_lookup` 的 `ASK_TARGET_TEXT` 出口），讓輸出
            # 照常往下走，最終落到 `_apply_handoff_without_lookup` 的既有行為。
            if (
                out.kind == "handoff"
                and out.handoff_reason in NON_SENSITIVE_HANDOFF_REASONS
                and not acc.tool_call_records
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

            # T3（Plan §4）：**文字假確認**——只做統計，⛔ 不改寫、⛔ 不改文字。
            # 三個封閉條件都成立（`kind=ask` ∧ `ask_target=confirm_intent` ∧ 本回合
            # 沒有 `confirm.request` 呼叫）才記一個旗標；第四個條件（模型散文是否
            # 真的在問「要不要送出」）是開放語義，Plan 明講⛔ 不做，故不判。
            if (
                out.kind == "ask"
                and out.ask_target == "confirm_intent"
                and not any(tc.name == CONFIRM_TOOL_NAME for tc in acc.tool_call_records)
            ):
                acc.violations.append("prose_confirm_suspect")

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
