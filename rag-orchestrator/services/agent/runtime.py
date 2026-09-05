"""`AgentRuntime`（spec agentic-mcp-orchestration・任務 2.1｜design 元件 1）。

模型迴圈：Chat Completions tool loop（`parallel_tool_calls=false`）＋預算表
＋Verifier 拒因重寫＋同題重問快取。契約基準見
`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 1（`Identity`／
`Budget`／`TurnTrace`／`AgentRuntime`／`TurnResult`、預算計數表、同題重問
快取段）。

**2.5 收尾註記（本檔已接妥的三條，取代下方舊的「刻意留白」敘述）**：
- `AgentOutput`／`VerifierVerdict`／`Citation`／`SentenceCite` 的權威定義已
  搬到 `services/agent/output_schema.py`（任務 2.3），本檔全部改
  `from services.agent.output_schema import ...`，⛔ 不再本地重複定義。
- 工具回傳的 `text_for_model` 已改經 `services.agent.prompt_assembler.wrap_tool_data
  (name, text_for_model, nonce)` 包裝成資料段才進 `role="tool"` 訊息。
- `assembler.build(...)` 與 `assembler.build_messages(...)` 二選一：本檔選
  `build_messages()`——它直接回傳 `list[dict]`，與 `AssemblerProtocol` 的
  既有形狀（本檔、`services/agent/mcp_facade.py` 等呼叫端）一致，不必額外
  拆 `BuiltPrompt(messages, meta)`；`outline_sha`／`rules_sha` 這兩個 trace
  欄位本檔已經直接從 `outline.sha256`／`self.verifier.rules_sha` 讀（見下方
  `_outline_sha`／`_rules_sha`），不需要 `build()` 回傳的 `PromptMeta`。

**本任務刻意留白（由後續任務補上，⛔ 不是這裡漏做）**：
- `AgentOutput.model_json_schema()` 轉成 OpenAI strict `json_schema` 目前只
  在頂層補 `additionalProperties: false`／`required`，未遞迴處理巢狀
  `Citation`／`SentenceCite`／`$defs`——這支任務全程用假 provider（⛔ 不呼叫
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
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Protocol

from pydantic import ValidationError

from services import usage_metering
from services.agent.budget import Budget, BudgetCounters
from services.agent.identity import Identity, Stage
from services.agent.mcp_facade import current_stage
from services.agent.output_schema import AgentOutput, VerifierVerdict
from services.agent.prompt_assembler import new_nonce, wrap_tool_data
from services.agent.tools.registry import ToolRegistry, ToolResult, tool_name_from_openai
from services.conversational_config import (
    effective_handoff_channel,
    effective_handoff_message,
)
from services.presales_gate import FactClass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# `AgentOutput`／`VerifierVerdict` 權威定義在 `services/agent/output_schema.py`
# （任務 2.3）；本檔只 import，⛔ 不再本地重複定義（2.5 收尾註記，見模組
# docstring）。`Citation`／`SentenceCite` 本檔不直接使用，不重複 import。
# ---------------------------------------------------------------------------


class VerifierProtocol(Protocol):
    def verify(
        self,
        out: AgentOutput,
        tool_results: dict[str, ToolResult],
        user_message: str,
        handoff: Optional[dict],
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


def _agent_output_response_format() -> dict:
    """`response_format={"type":"json_schema","json_schema":{"strict":True,...}}`

    只在頂層補 `additionalProperties`／`required`（見模組 docstring「本任務
    刻意留白」段——巢狀 `$defs` 的 strict 轉換留給 2.2 對真 API 驗證時處理）。
    """
    schema = AgentOutput.model_json_schema()
    schema["additionalProperties"] = False
    schema["required"] = list(schema.get("properties", {}).keys())
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
    """
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
                }
                for v in trace.verifier
            ],
            "final_kind": trace.final_kind,
            "handoff_reason": trace.handoff_reason,
            "latency_ms": trace.latency_ms,
            "rules_sha": trace.rules_sha,
            "outline_sha": trace.outline_sha,
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
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.verifier = verifier
        self.assembler = assembler
        self.budget = budget
        self.readonly_view = readonly_view
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

        # `new_nonce()`（`services.agent.prompt_assembler`）＝ 16 位十六進位，
        # 符合 `wrap_tool_data`／`PromptAssembler` 的 nonce 形狀守門；
        # ⛔ 不用 `secrets.token_urlsafe`——它會產出 `-`／`_`，被 `_require_nonce`
        # 的 `^[0-9A-Za-z]{8,64}$` 擋下（2.5 接線時發現，見任務回報）。
        nonce = new_nonce()
        # 2.9 路徑對齊：槽位在 **`collected_data` 頂層**（見 `_slots_for_prompt`）。
        slots = _slots_for_prompt(state)
        dialog = agent_state.get("dialog", [])
        outline = agent_state.get("outline")

        tool_specs = self.registry.to_openai_tools(
            identity, self._stage, readonly_view=self.readonly_view
        )
        visible_names = {tool_name_from_openai(t["function"]["name"]) for t in tool_specs}   # 解回 registry 名

        messages = self.assembler.build_messages(identity, outline, slots, dialog, tool_specs, nonce)

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
                    # 2.5 接線：工具回傳一律經 wrap_tool_data 包成資料段
                    # （同回合共用一個 nonce，見上方 `nonce = new_nonce()`）。
                    raw_tool_text = tool_result.text_for_model or json.dumps(
                        {"ok": tool_result.ok, "error": tool_result.error},
                        ensure_ascii=False,
                    )
                    try:
                        tool_content = wrap_tool_data(name, raw_tool_text, nonce)
                    except ValueError:
                        # 模型送的 tool 名不合 wrap_tool_data 的形狀守門（例如空白／
                        # 標記字元）——registry.call 已經用它判過 NO_MATCH／
                        # FORBIDDEN，這裡只是包裝層，⛔ 不因此讓整回合崩潰。
                        violations.append(f"BAD_TOOL_NAME:{name!r}")
                        tool_content = wrap_tool_data("tool", raw_tool_text, nonce)
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
            content = getattr(message, "content", None) or ""
            try:
                payload = json.loads(content)
                out = AgentOutput.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, TypeError):
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

            verdict = self.verifier.verify(out, tool_results_by_id, user_message, handoff_dict)
            verifier_verdicts.append(verdict)
            if not verdict.ok:
                counters.rewrites += 1
                logger.info(
                    "agent_verifier_reject trace_id=%s reason=%s rewrites=%d/%d",
                    trace_id, verdict.reason, counters.rewrites, self.budget.max_rewrites,
                )
                if counters.rewrite_exhausted(self.budget):
                    return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)
                messages.append({"role": "assistant", "content": content})
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
            )
            result = TurnResult(
                kind=out.kind,
                answer=out.answer,
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
