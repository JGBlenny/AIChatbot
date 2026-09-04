"""`AgentRuntime`（spec agentic-mcp-orchestration・任務 2.1｜design 元件 1）。

模型迴圈：Chat Completions tool loop（`parallel_tool_calls=false`）＋預算表
＋Verifier 拒因重寫＋同題重問快取。契約基準見
`.kiro/specs/agentic-mcp-orchestration/design.md` 元件 1（`Identity`／
`Budget`／`TurnTrace`／`AgentRuntime`／`TurnResult`、預算計數表、同題重問
快取段）。

**本任務刻意留白（由後續任務補上，⛔ 不是這裡漏做）**：
- `Verifier`（元件 6）本體是任務 2.3；這裡只定義它的呼叫介面
  `verify(out, tool_results, user_message, handoff) -> VerifierVerdict`，
  `VerifierVerdict` 也只先給 `ok`／`reason` 兩欄的最小形狀——2.3 落地後那邊
  的完整 `VerifierRules`／11 拒因值域才是唯一權威，這裡的定義屆時應改成
  `from services.agent.verifier import VerifierVerdict` 之類的 import。
- `PromptAssembler`（元件 5）本體是任務 3.1／3.2；這裡只呼叫
  `assembler.build(identity, outline, slots, dialog, tool_specs, nonce)`，
  `outline`／`slots`／`dialog` 從 `state["agent"]` 讀（3.2 的 `OutlineAssembler`
  接妥前，呼叫端自行決定要不要填）。`wrap_tool_data(nonce)` 是 3.1 的
  函式，目前尚不存在——工具回傳的 `text_for_model` **暫時原樣**塞進
  `role="tool"` 訊息，3.1 落地後這裡要改成
  `wrap_tool_data(name, text_for_model, nonce)`（見下方 `_TOOL_MESSAGE_TODO`
  常數旁的呼叫點）。
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
import os
import secrets
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Protocol

from pydantic import BaseModel, ValidationError

from services.agent.budget import Budget, BudgetCounters
from services.agent.identity import Identity, Stage
from services.agent.mcp_facade import current_stage
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.conversational_config import (
    effective_handoff_channel,
    effective_handoff_message,
)
from services.presales_gate import FactClass

# ---------------------------------------------------------------------------
# `AgentOutput`（design 元件 6 的形狀；本任務只需拿它做「模型最終輸出」的
# 契約與 schema 來源，Verifier 的判定邏輯是 2.3 的事）。
# ---------------------------------------------------------------------------


class Citation(BaseModel):
    tool_call_id: str
    source: str
    quote: str


class SentenceCite(BaseModel):
    sent: int
    kind: Literal["fact", "question", "greeting", "routing"]
    cite: list[int] = []


class AgentOutput(BaseModel):
    kind: Literal["answer", "ask", "recommend", "handoff"]
    answer: str
    citations: list[Citation] = []
    sentence_map: list[SentenceCite] = []
    fact_class: FactClass
    handoff_reason: Optional[str] = None


class VerifierVerdict(BaseModel):
    """佔位形狀——2.3 的 `OutputVerifier` 本體會有完整 11 拒因值域與
    `sent`／`term_id`／`quote_len`。這裡的迴圈只讀 `ok`／`reason` 兩欄，
    ⛔ 不對外洩原文（`reason` 是結構化代碼，不是自然語言）。
    """

    ok: bool
    reason: Optional[str] = None


class VerifierProtocol(Protocol):
    def verify(
        self,
        out: AgentOutput,
        tool_results: dict[str, ToolResult],
        user_message: str,
        handoff: Optional[dict],
    ) -> VerifierVerdict: ...


class AssemblerProtocol(Protocol):
    def build(
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
    id: str
    name: str
    args_hash: str
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

        nonce = secrets.token_urlsafe(16)
        slots = agent_state.get("slots", {})
        dialog = agent_state.get("dialog", [])
        outline = agent_state.get("outline")

        tool_specs = self.registry.to_openai_tools(
            identity, self._stage, readonly_view=self.readonly_view
        )
        visible_names = {t["function"]["name"] for t in tool_specs}

        messages = self.assembler.build(identity, outline, slots, dialog, tool_specs, nonce)

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
            agent_state["fixed_streak"] = (
                agent_state.get("fixed_streak", 0) + 1 if is_fixed else 0
            )
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
            prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens += getattr(usage, "completion_tokens", 0) or 0
            message = response.choices[0].message
            tool_calls = list(getattr(message, "tool_calls", None) or [])

            if tool_calls:
                messages.append(_assistant_tool_call_message(message, tool_calls))
                budget_hit = False
                for tc in tool_calls:
                    if counters.tool_call_exhausted(self.budget):
                        budget_hit = True
                        break
                    name = tc.function.name
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
                            args_hash=hashlib.sha256(
                                json.dumps(raw_args, sort_keys=True, ensure_ascii=False).encode(
                                    "utf-8"
                                )
                            ).hexdigest(),
                            args_summary=_args_summary(raw_args),
                            ms=ms,
                            status=_tool_result_status(tool_result),
                            n_items=_tool_result_n_items(tool_result),
                        )
                    )
                    tool_results_by_id[tc.id] = tool_result
                    # 3.1 落地前的暫時作法，見模組 docstring「本任務刻意留白」段：
                    # 這裡本應是 wrap_tool_data(name, tool_result.text_for_model, nonce)。
                    tool_content = tool_result.text_for_model or json.dumps(
                        {"ok": tool_result.ok, "error": tool_result.error},
                        ensure_ascii=False,
                    )
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
                handoff_dict = {
                    "reason": out.handoff_reason or "no_grounding",
                    "fact_class": out.fact_class.value,
                    "channel": effective_handoff_channel(None),
                    "message": effective_handoff_message(None),
                }

            verdict = self.verifier.verify(out, tool_results_by_id, user_message, handoff_dict)
            verifier_verdicts.append(verdict)
            if not verdict.ok:
                counters.rewrites += 1
                if counters.rewrite_exhausted(self.budget):
                    return _finalize(_build_fixed("budget_exhausted"), is_fixed=True)
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": f"VERIFIER_REJECT:{verdict.reason or 'UNKNOWN'}",
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
