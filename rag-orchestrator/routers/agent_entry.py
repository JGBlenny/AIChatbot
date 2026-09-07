"""agent 路徑入口（spec agentic-mcp-orchestration・任務 2.2；design 元件 8）。

`/api/v1/message` 的分流：`audience_of(request) ∈ AGENT_AUDIENCES` 且 app 已建
`agent_runtime` ⇒ 走 `AgentRuntime`；否則回 `None` 讓 `routers/chat.py` 照舊鏈走。
對外契約不變：非串流回 `VendorChatResponse`（沿用 `_conversational_to_response`），
串流沿用 start／intent／answer_chunk／metadata／done 事件序；工具呼叫期間以 SSE
**註解行**（`: keepalive`）當心跳——EventSource 規格會忽略註解行，⛔ 不新增事件型別
（前端契約未驗證新型別，R1.4 只要求連線不靜默 >10 秒）。

狀態：REST 路徑沿用舊鏈的 `form_sessions`（`form_id='conversational'`）列，透過
`EngineStateStore` 呼叫 `ConversationalEngine.get_state／_start／_save`，⛔ 不另寫 SQL；
agent 會話的 `config_key='agent:<audience>'`。回退：`state["agent"]["fixed_streak"] >= 3`
⇒ 標 `fallback_old_chain` 並回 `None`（design 元件 1 預算表・元件 8）。
⚠️ 回退後舊鏈 `prepare()` 讀到 `config_key='agent:*'` 會查無設定而降級到一般 RAG 流程，
這是可接受的降級（不是資料損壞），2.2 收案註記有記。

影子（design 元件 7／任務 4.1）：`schedule_shadow(...)` 由 chat.py 在舊鏈產出答案後呼叫；
`ShadowRunner` 不在 app.state 時為 no-op。
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional, Protocol

from fastapi.responses import StreamingResponse

from services.agent.identity import (
    DEFAULT_ENTRY_MODE,
    ENTRY_MODES,
    Identity,
    audience_of,
    normalize_entry_mode,
)

logger = logging.getLogger(__name__)

CONVERSATIONAL_FORM_ID = "conversational"
KEEPALIVE_INTERVAL_S = 5.0          # R1.4：連線靜默 ≤10 秒；5 秒一則註解行
FIXED_STREAK_FALLBACK = 3           # design 元件 1 預算表：連續 3 回合固定句 ⇒ 回退舊鏈


def agent_audiences() -> frozenset[str]:
    raw = os.getenv("AGENT_AUDIENCES", "")
    return frozenset(a.strip() for a in raw.split(",") if a.strip())


def build_identity(request) -> Identity:
    """從 `/api/v1/message` 的請求欄位組 Identity——上游信任輸入（DSP-011），⛔ 不驗真偽。

    任務 4.2（Plan §4.1-1）：mode 由 `identity.normalize_entry_mode` 決定——
    prospect **一律 b2b**（售前池是 b2b 池：`business_types && ['system_provider']`）。
    ⚠️ 這修掉的是 `VendorChatRequest.mode` 的 pydantic 預設 `'b2c'`：舊式
    `mode or ("b2b" if prospect …)` 只在明送 null／空字串才觸發，**沒帶 mode 的
    prospect 會落 b2c**、進而在候選選取變成靜默零內容。
    ⚠️ REST 入口沒有 `_STATS`（那是 `/mcp` 的前提偵測計數器）⇒ 這裡**只 log 不計數**
    （明列取捨，Plan §4.1-1）。

    ⚠️ **`entry` 刻意不帶**（DSP-038-1，⛔ 勿「補齊」）：`Identity.entry` 預設
    `"rest"`＝fail-closed，於是 `mcp_only=True` 的寫入型工具對 REST 入口
    **看不到也呼叫不到**（`ToolRegistry.specs_for`／`call` 同一條規則），
    `AgentRuntime.run_turn` 的確認兌現段也整段不執行。這是 S-6／S-7 的緩解：
    REST 目前沒有 session 命名空間、token 表也沒有 vendor 欄，唯一的隔離就靠
    這個預設值。⛔ 不得在此改成 `"mcp"`，也不得讓呼叫端 payload 決定它。
    """
    target_user = getattr(request, "target_user", None) or "tenant"
    raw_mode = getattr(request, "mode", None)
    # 正規化前的基準＝值域守門後的值（合法原樣、其餘落預設）——⛔ 不印 `raw_mode`
    # 本身：它是呼叫端自由字串，印出去就是把 payload 帶進 log。
    mode_before = raw_mode if raw_mode in ENTRY_MODES else DEFAULT_ENTRY_MODE
    mode = normalize_entry_mode(target_user, raw_mode)
    if mode != mode_before:
        # ⚠️ 進到這裡代表正規化真的改寫了 mode ⇒ `target_user` 必為字面值
        # `prospect`（唯一會改寫的分支），印它不等於印 payload。
        logger.info(
            "[agent] 入口 mode 正規化：target_user=%s mode %s -> %s",
            target_user, mode_before, mode,
        )
    role_id = getattr(request, "role_id", None)
    return Identity(
        vendor_id=getattr(request, "vendor_id", None) or 0,
        target_user=target_user,
        mode=mode,
        role_id=role_id,
        user_id=getattr(request, "user_id", None),
        session_id=getattr(request, "session_id", None) or "",
        audience=audience_of(mode, target_user, role_id),
    )


class StateStore(Protocol):
    async def load(self, session_id: str) -> Optional[dict]: ...
    async def start(self, session_id: str, user_id: str, vendor_id: int,
                    role_id: Optional[str], config_key: str) -> dict: ...
    async def save(self, session_id: str, state: dict) -> None: ...


class EngineStateStore:
    """包 `ConversationalEngine` 的三個狀態方法（同一張 `form_sessions` 列、同一 SQL）。"""

    def __init__(self, engine) -> None:
        self._engine = engine

    async def load(self, session_id: str) -> Optional[dict]:
        return await self._engine.get_state(session_id)

    async def start(self, session_id, user_id, vendor_id, role_id, config_key) -> dict:
        return await self._engine._start(session_id, user_id, vendor_id, config_key, role_id=role_id)

    async def save(self, session_id: str, state: dict) -> None:
        await self._engine._save(session_id, state)


def _resolve(app, name: str, override):
    if override is not None:
        return override
    return getattr(app.state, name, None)


def _outline_for(app, audience: Optional[str]):
    """該受眾的行程級大綱（DSP-037／S1b）；沒有 ⇒ `None`（維持現況＝不塞）。

    `app.state.agent_outlines`（複數）是權威對照表——查無該受眾 ⇒ `None`，
    ⛔ 不回退到 prospect 那一份（把售前正本餵給 pm／tenant 回合正是 S1b 修掉的洞）。
    沒有複數對照表的舊形狀 ⇒ 只有 prospect 讀得到單數 `app.state.agent_outline`。
    """
    outlines = getattr(app.state, "agent_outlines", None)
    if isinstance(outlines, dict) and outlines:
        return outlines.get(audience)
    return getattr(app.state, "agent_outline", None) if audience == "prospect" else None


async def handle_agent_entry(request, req, ctx, *, runtime=None, store=None,
                             sse_event=None, metered=None, to_response=None):
    """回最終 Response（stream 或 JSON），或 `None`（不啟用／回退／runtime 缺）。

    `sse_event`／`metered`／`to_response` 由 chat.py 注入既有 helper（避免循環 import）。
    """
    app = req.app
    identity = build_identity(request)
    if identity.audience not in agent_audiences():
        return None
    rt = _resolve(app, "agent_runtime", runtime)
    if rt is None:
        return None
    st = store or (EngineStateStore(app.state.conversational_engine)
                   if getattr(app.state, "conversational_engine", None) else None)
    if st is None:
        return None

    session_id = identity.session_id
    state = await st.load(session_id)
    if state is None:
        state = await st.start(session_id, request.user_id or "anonymous",
                               request.vendor_id or 0, request.role_id,
                               f"agent:{identity.audience}")
    agent_state = state.setdefault("agent", {})
    if agent_state.get("fallback_old_chain"):
        return None
    # 大綱只在記憶體：runtime 從 state["agent"]["outline"] 讀（2.1 做法），
    # ⛔ 不得序列化進 form_sessions —— `_persist` 存檔前 pop。
    outline = _outline_for(app, identity.audience)
    if outline is not None:
        agent_state["outline"] = outline

    if request.stream:
        gen = _agent_sse(rt, st, identity, request.message, state, session_id, sse_event)
        body = metered(gen, app.state.db_pool) if metered else gen
        return StreamingResponse(body, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                                          "X-Accel-Buffering": "no"})

    result = await rt.run_turn(identity, request.message, state)
    await _persist(st, session_id, state)
    payload = {"answer": result.answer, "handoff": result.handoff,
               "quick_replies": result.quick_replies or None, "converged": False}
    return to_response(payload, request) if to_response else payload


async def _persist(store, session_id: str, state: dict) -> None:
    agent_state = state.setdefault("agent", {})
    agent_state.pop("outline", None)            # 大綱不落地（見 handle_agent_entry）
    if agent_state.get("fixed_streak", 0) >= FIXED_STREAK_FALLBACK:
        agent_state["fallback_old_chain"] = True
    await store.save(session_id, state)


async def _agent_sse(rt, store, identity, message, state, session_id, sse_event):
    """start → intent → keepalive 註解行* → answer_chunk → metadata → done。"""
    async def ev(kind, data):
        return await sse_event(kind, data) if sse_event else f"event: {kind}\ndata: {data}\n\n"
    try:
        yield await ev("start", {"cached": False, "message": "開始輸出答案..."})
        yield await ev("intent", {"intent_type": "conversational", "intent_name": "agent", "confidence": 1.0})
        task = asyncio.ensure_future(rt.run_turn(identity, message, state))
        while True:
            try:
                result = await asyncio.wait_for(asyncio.shield(task), timeout=KEEPALIVE_INTERVAL_S)
                break
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
        await _persist(store, session_id, state)
        if result.answer:
            yield await ev("answer_chunk", {"chunk": result.answer})
        metadata = {"intent_type": "conversational", "action_type": "conversational",
                    "cache_hit": False, "trace_id": result.trace.trace_id}
        if result.quick_replies:
            metadata["quick_replies"] = result.quick_replies
        if result.handoff:
            metadata["handoff"] = result.handoff
        yield await ev("metadata", metadata)
        yield await ev("done", {"success": True, "cached": False, "message": "答案生成完成"})
    except Exception as e:  # noqa: BLE001 — 對外只給錯誤型別，⛔ 不洩內部細節
        yield await ev("error", {"success": False, "error": type(e).__name__})


def schedule_shadow(app, request, state_snapshot: Optional[dict], old_answer: str) -> None:
    """舊鏈產出答案後呼叫；`ShadowRunner` 缺或未啟用 ⇒ no-op（design 元件 7）。"""
    shadow = getattr(app.state, "shadow_runner", None)
    if shadow is None:
        return
    identity = build_identity(request)
    try:
        if shadow.enabled(identity):
            state = dict(state_snapshot or {})
            # DSP-022 附帶：影子回合也要看得到大綱（與 handle_agent_entry 同一份
            # `app.state.agent_outline`、同樣只在記憶體）。真線路 2026-09-05：影子
            # prompt_tokens 只有 2.4k、每題 no_grounding，就是這裡沒塞。
            outline = _outline_for(app, identity.audience)
            if outline is not None:
                agent_state = dict(state.get("agent") or {})
                agent_state["outline"] = outline
                state["agent"] = agent_state
            shadow.schedule(identity, request.message, state, old_answer)
    except Exception:  # noqa: BLE001 — 影子絕不影響主回應
        return
