"""`ShadowRunner`（spec agentic-mcp-orchestration・任務 4.1｜design 元件 7）。

舊鏈（`routers/chat.py`）在把答案送出之後（`routers/agent_entry.py:schedule_shadow`
的呼叫點），額外用 `AgentRuntime`（`readonly_view=True`）背景跑一次同一題，
比對答案差異——**不影響、不阻塞使用者拿到的那個回應**。

三條紅線（design 元件 7 / 任務 brief）：
  ① ⛔ **不落答案原文**——`decision_snapshot.agent_shadow` 只落雜湊／長度／
     分類旗標／成本，逐字全文只進獨立表 `agent_shadow_texts`（僅 prospect、
     30 天、讀取另有 X-API-Key 端點，5.x 才做）。
  ② ⛔ **不阻塞 SSE**——`schedule()` 只 `asyncio.create_task` 就回，不 `await`；
     `deepcopy(state_snapshot)` 與整個影子回合都在背景 task 裡做。
  ③ ⛔ **不寫回真實 session**——`runtime_factory(readonly_view=True)` 建出的
     `AgentRuntime` 在 write 工具／`mutates_session` 工具上一律 `NO_MATCH`
     （`services/agent/tools/registry.py:specs_for` 已經擋，DSP-016）；本檔
     另外用 `deepcopy` 隔絕 state，且從不呼叫任何狀態儲存的 `save()`——
     影子回合的 `run_turn` 對它自己那份拷貝做的任何 `state["agent"][...]`
     寫入，跟著這份拷貝一起被丟棄。

**計量**：用一組全新的 `usage_metering` context（`begin()` 在目前這個
`asyncio.create_task` 建出的 task 內呼叫——contextvar 在 task 建立當下被複製，
task 內的 `_ctx.set(...)` 只影響這個 task 自己那份，不會動到孵化它的主請求
context，這就是「自建 ctx」的意思）：`is_internal=True`、
`processing_path="shadow:agent"`，成本累計進同一顆 `usage_events.est_cost_usd`
欄位供 `enabled()` 的月上限查詢用。`decision_snapshot.agent_shadow` 另外落一份
`ShadowRecord`（封閉白名單鍵）。

**已知取捨（brief 未完全鎖死、本檔的實作決定）**：
- `is_internal=True` 借用既有 `usage_metering.INTERNAL_RULES` 的
  `disable_answer_synthesis` 判準達成（⛔ 本任務不得改 `usage_metering.py`
  新增規則）；副作用是 `internal_kind` 會落 `"backtest"` 而非語意上更準確的
  `"shadow"`——brief 只要求 `is_internal=True`／`processing_path=shadow:agent`，
  沒鎖 `internal_kind` 值，這裡先接受這個副作用。
- `ShadowRecord.cost_usd` 用本檔自己的 `_estimate_cost_usd`（`DEFAULT_PRICING`
  公開常數）重算一次，⛔ 不讀 `usage_metering` 的私有 contextvar——與
  `usage_events.est_cost_usd`（`enabled()` 月上限查詢的來源）用同一張價目表，
  但不吃 `LLM_PRICING_PATH` 外部覆蓋（那張表是 `usage_metering._pricing()`
  的私有組裝結果）；兩邊分開算，價目表沒覆蓋時完全一致。
- `diff_flags` 的「舊鏈是否轉人」用文字比對（`effective_handoff_message`／
  `PRESALES_PARTIAL_TAIL`／`PRESALES_HANDOFF_ENTRY_HINT`）——舊鏈只回一個
  `old_answer: str`，沒有結構化的 `kind`，這是唯一能低成本判斷的訊號；
  vendor 客製過的轉人文案（`effective_handoff_message` 帶 `cfg` 參數的分支）
  比對不到會被計為「非轉人」，屬已知盲點。
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel

from services import usage_metering
from services.agent.identity import Identity
from services.agent.runtime import AgentRuntime, TurnResult, TurnTrace
from services.conversational_config import (
    PRESALES_HANDOFF_ENTRY_HINT,
    PRESALES_PARTIAL_TAIL,
    effective_handoff_message,
)

logger = logging.getLogger(__name__)

#: 月界比照 `usage_metering._TPE`（Asia/Taipei）——⛔ 不 import 私有名稱，
#: 這裡重算同一算式；若那邊改了時區這裡要跟著改（見 runtime.py 對
#: `_IDENTITY_ARG_KEYS` 的同款先例與註記）。
_TPE = timezone(timedelta(hours=8))

_DEFAULT_MONTHLY_CAP_USD = 50.0
_COST_CACHE_TTL_S = 300.0        # 5 分鐘（brief）
_CAP_WARN_THROTTLE_S = 3600.0    # 節流 1 小時（brief）

#: `usage_events.processing_path`／`enabled()` 月成本查詢共用同一個字面量。
SHADOW_PROCESSING_PATH = "shadow:agent"


def _shadow_audiences() -> frozenset[str]:
    raw = os.getenv("AGENT_SHADOW_AUDIENCES", "")
    return frozenset(a.strip() for a in raw.split(",") if a.strip())


def _monthly_cap_usd() -> float:
    raw = os.getenv("AGENT_SHADOW_MONTHLY_USD_CAP", "").strip()
    if not raw:
        return _DEFAULT_MONTHLY_CAP_USD
    try:
        return float(raw)
    except ValueError:
        return _DEFAULT_MONTHLY_CAP_USD


def _month_start_tpe() -> date:
    return datetime.now(_TPE).date().replace(day=1)


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """比照 `usage_metering._compute_cost`，用同一張公開價目表重算一次
    （見模組 docstring「已知取捨」）。缺價 ⇒ 0.0（⛔ 不臆造，但 `ShadowRecord.cost_usd`
    型別是 `float` 非 `Optional`，這裡跟主鏈 `est_cost_usd` 留 `None` 的慣例不同，
    取 0.0 只影響這顆診斷用欄位，不影響月上限查詢——那邊讀的是 `usage_events`
    真實欄位）。
    """
    price = usage_metering.DEFAULT_PRICING.get(model)
    if price is None:
        return 0.0
    prompt_cost = prompt_tokens * price[0]
    completion_cost = completion_tokens * price[1]
    return round((prompt_cost + completion_cost) / 1_000_000, 6)


def _looks_like_handoff_text(text: Optional[str]) -> bool:
    """舊鏈答案是否像轉人固定句（見模組 docstring「已知取捨」）。"""
    candidate = (text or "").strip()
    if not candidate:
        return False
    if candidate == (effective_handoff_message(None) or "").strip():
        return True
    return PRESALES_PARTIAL_TAIL in candidate or PRESALES_HANDOFF_ENTRY_HINT in candidate


def _trace_to_dict(trace: TurnTrace) -> dict:
    """把 `TurnTrace` 轉成 JSON 安全的 dict——⛔ 不用 `dataclasses.asdict`
    直接轉（`trace.verifier` 是 `list[VerifierVerdict]`，`VerifierVerdict`
    是 pydantic model，`asdict` 不會遞迴進 pydantic 物件），逐欄位字面量組裝，
    比照 `runtime.py:_emit_agent_decision` 同款寫法。全部欄位本來就不含
    `answer`／`quote`／`user_message` 原文（`TurnTrace` 的既有契約）。
    """
    return {
        "trace_id": trace.trace_id,
        "tool_calls": [
            {
                "name": tc.name,
                "args_summary": tc.args_summary,   # 2.6 刪 args_hash（低熵可反解）；M1 verifier 抓到此處仍讀 ⇒ 有工具呼叫即整輪靜默丟棄
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
                "ok": v.ok,
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
        "violations": list(trace.violations),
        "rules_sha": trace.rules_sha,
        "outline_sha": trace.outline_sha,
    }


class ShadowRecord(BaseModel):
    """`decision_snapshot.agent_shadow` 的封閉白名單（design 元件 7）。

    ⛔ 沒有 `answer`／`old_answer`／`quote` 這類欄位——`trace` 本身
    （`_trace_to_dict`）也不含原文，`agent_shadow_texts` 才是全文比對的落點。
    """

    trace: dict
    agent_answer_sha256: str
    agent_answer_len: int
    old_answer_sha256: str
    old_answer_len: int
    diff_flags: list[str]
    cost_usd: float


class ShadowRunner:
    """`enabled()`／`schedule()` 見模組 docstring 與 design 元件 7。

    `runtime_factory(readonly_view: bool) -> AgentRuntime`：呼叫端（2.2）
    的組裝責任，本檔只負責在背景 task 內以 `readonly_view=True` 呼叫它。
    """

    def __init__(
        self,
        runtime_factory: Callable[..., AgentRuntime],
        db_pool: Any,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._runtime_factory = runtime_factory
        self._db_pool = db_pool
        self._clock = clock
        # 月成本快取：`None` 代表尚未查過——`enabled()` fail-open 視為 0
        # （比照 usage_metering.quota_check 的 fail-open 哲學），觸發背景刷新。
        self._cost_cached_usd: Optional[float] = None
        self._cost_cached_at: float = float("-inf")   # 保證第一次呼叫必觸發刷新
        self._last_cap_warn_at: float = float("-inf")

    # ------------------------------------------------------------------
    def enabled(self, identity: Identity) -> bool:
        """`AGENT_SHADOW_AUDIENCES` 含 `identity.resolved_audience()`
        且當月累計成本 < `AGENT_SHADOW_MONTHLY_USD_CAP`（同步、不阻塞——
        月成本走 5 分鐘快取＋背景刷新，見 `_maybe_refresh_cost_cache`）。
        """
        if identity.resolved_audience() not in _shadow_audiences():
            return False
        self._maybe_refresh_cost_cache()
        cost = self._cost_cached_usd if self._cost_cached_usd is not None else 0.0
        cap = _monthly_cap_usd()
        if cost >= cap:
            self._warn_cap_exceeded(cost, cap)
            return False
        return True

    def _maybe_refresh_cost_cache(self) -> None:
        now = self._clock()
        if now - self._cost_cached_at < _COST_CACHE_TTL_S:
            return
        self._cost_cached_at = now  # 先蓋時間戳，避免同一視窗內重複觸發刷新
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # 沒有事件迴圈（例如同步呼叫端）⇒ 略過，下次呼叫再試
        asyncio.create_task(self._refresh_cost_cache())

    async def _refresh_cost_cache(self) -> None:
        if self._db_pool is None:
            return
        try:
            cost = await self._db_pool.fetchval(
                "SELECT COALESCE(SUM(est_cost_usd), 0) FROM usage_events "
                "WHERE is_internal = TRUE AND processing_path = $1 AND date_tpe >= $2",
                SHADOW_PROCESSING_PATH,
                _month_start_tpe(),
            )
            self._cost_cached_usd = float(cost or 0.0)
        except Exception as e:  # 查詢失敗 fail-open（沿用舊快取，不擋影子）
            logger.warning("[shadow] 月成本查詢失敗，沿用舊快取：%s", e)

    def _warn_cap_exceeded(self, cost: float, cap: float) -> None:
        now = self._clock()
        if now - self._last_cap_warn_at < _CAP_WARN_THROTTLE_S:
            return
        self._last_cap_warn_at = now
        logger.warning(
            "[shadow] 本月累計成本 $%.4f 已達上限 $%.2f，本月停用影子（%s）",
            cost, cap, SHADOW_PROCESSING_PATH,
        )

    # ------------------------------------------------------------------
    def schedule(
        self,
        identity: Identity,
        user_message: str,
        state_snapshot: dict,
        old_answer: str,
    ) -> None:
        """⛔ 不 `await`——立刻 `asyncio.create_task` 後返回。"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("[shadow] 無事件迴圈可排程，捨棄本輪影子")
            return
        loop.create_task(
            self._run_shadow_turn(identity, user_message, state_snapshot, old_answer)
        )

    async def _run_shadow_turn(
        self,
        identity: Identity,
        user_message: str,
        state_snapshot: dict,
        old_answer: str,
    ) -> None:
        """整個影子回合的例外邊界——任何失敗只 `logging.exception`，
        ⛔ 不外洩（本檔是 fire-and-forget task，沒有人在 await 它）。
        """
        try:
            # `deepcopy` 在 task 內做（brief 明示），隔絕與正式回合共用的
            # 那份 state 物件；影子回合對這份拷貝的任何寫入都跟著拷貝一起丟棄。
            shadow_state = copy.deepcopy(state_snapshot or {})
            runtime = self._runtime_factory(readonly_view=True)
            result: TurnResult = await runtime.run_turn(identity, user_message, shadow_state)
            # `runtime._model` 是私有屬性——`AgentRuntime` 沒有公開 accessor
            # （2.2 接線前不動 runtime.py，見任務邊界）；只在這裡讀一次，
            # `_build_record`（成本估算）與 `_emit_metering`（`add_llm_usage`）
            # 共用同一個值，避免兩處各自回退（env/預設）算出不一致的模型名。
            model_name = getattr(runtime, "_model", None) or "gpt-4o-mini"
            record = self._build_record(model_name, result, old_answer)
            self._emit_metering(identity, user_message, model_name, record)
            if identity.resolved_audience() == "prospect":
                await self._write_texts(identity, result, old_answer)
        except Exception:  # noqa: BLE001 — 影子絕不可讓例外外洩或影響正式回合
            logger.exception("[shadow] 影子回合失敗，本輪捨棄")

    # ------------------------------------------------------------------
    def _build_record(
        self, model_name: str, result: TurnResult, old_answer: Optional[str]
    ) -> ShadowRecord:
        agent_answer = result.answer or ""
        old_answer_text = old_answer or ""
        agent_sha = hashlib.sha256(agent_answer.encode("utf-8")).hexdigest()
        old_sha = hashlib.sha256(old_answer_text.encode("utf-8")).hexdigest()

        agent_is_handoff = result.kind == "handoff"
        old_is_handoff = _looks_like_handoff_text(old_answer_text)
        if agent_is_handoff and old_is_handoff:
            flag = "both_handoff"
        elif agent_is_handoff:
            flag = "agent_handoff_old_answered"
        elif old_is_handoff:
            flag = "old_handoff_agent_answered"
        elif agent_sha == old_sha:
            flag = "same"
        else:
            flag = "different"

        cost = _estimate_cost_usd(
            model_name, result.trace.prompt_tokens, result.trace.completion_tokens
        )

        return ShadowRecord(
            trace=_trace_to_dict(result.trace),
            agent_answer_sha256=agent_sha,
            agent_answer_len=len(agent_answer),
            old_answer_sha256=old_sha,
            old_answer_len=len(old_answer_text),
            diff_flags=[flag],
            cost_usd=cost,
        )

    def _emit_metering(
        self, identity: Identity, user_message: str, model_name: str, record: ShadowRecord
    ) -> None:
        """自建 `usage_metering` context（見模組 docstring）：`is_internal=True`
        借用既有 `disable_answer_synthesis` 判準（⛔ 不改 `usage_metering.py`）；
        `processing_path="shadow:agent"`；`decision_snapshot.agent_shadow` 落
        `ShadowRecord` 白名單鍵；`add_llm_usage` 讓這一列自己的 `est_cost_usd`
        累計進 `enabled()` 月上限查詢看得到的同一個欄位。
        """
        usage_metering.begin(
            {
                "vendor_id": identity.vendor_id,
                "mode": identity.mode,
                "target_user": identity.target_user,
                "role_id": identity.role_id,
                "user_id": identity.user_id,
                "session_id": identity.session_id,
                "channel": "web",
                "message": user_message,
                "disable_answer_synthesis": True,
            }
        )
        usage_metering.add_llm_usage(
            model_name,
            {
                "prompt_tokens": record.trace.get("prompt_tokens", 0),
                "completion_tokens": record.trace.get("completion_tokens", 0),
            },
        )
        usage_metering.set_path(processing_path=SHADOW_PROCESSING_PATH)
        usage_metering.set_decision({"agent_shadow": record.model_dump()})
        usage_metering.finalize(db_pool=self._db_pool)

    async def _write_texts(
        self, identity: Identity, result: TurnResult, old_answer: Optional[str]
    ) -> None:
        """全文比對落 `agent_shadow_texts`（僅 prospect，呼叫端已篩過）。"""
        try:
            await self._db_pool.execute(
                "INSERT INTO agent_shadow_texts "
                "(session_id, trace_id, agent_answer, old_answer) VALUES ($1, $2, $3, $4)",
                identity.session_id,
                result.trace.trace_id,
                result.answer or "",
                old_answer or "",
            )
        except Exception as e:  # 寧漏勿堵——全文表是輔助比對用途，非主鏈
            logger.warning("[shadow] agent_shadow_texts 寫入失敗（丟棄）：%s", e)


__all__ = ["ShadowRunner", "ShadowRecord", "SHADOW_PROCESSING_PATH"]
