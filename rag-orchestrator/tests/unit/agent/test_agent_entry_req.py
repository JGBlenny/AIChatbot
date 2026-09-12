"""2.2 agent 入口分流（design 元件 8；R1.4／R9.1／R9.3／R9.4）。"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from routers import agent_entry as ae
from services.agent.runtime import TurnResult, TurnTrace


def _req(**kw):
    base = dict(vendor_id=1, target_user="prospect", mode="b2c", role_id=None, user_id="u1",
                session_id="backtest_session_ae", message="可以線上簽約嗎", stream=False)
    base.update(kw)
    return SimpleNamespace(**base)


class FakeStore:
    def __init__(self, state=None):
        self.state = state
        self.saved = []
        self.started = []

    async def load(self, session_id):
        return self.state

    async def start(self, session_id, user_id, vendor_id, role_id, config_key):
        self.started.append(config_key)
        self.state = {"config_key": config_key, "collected_fields": {}}
        return self.state

    async def save(self, session_id, state):
        self.saved.append(json.loads(json.dumps(state)))


class FakeRuntime:
    def __init__(self, answer="好的", handoff=None, delay=0.0, fixed=False):
        self.answer, self.handoff, self.delay, self.fixed = answer, handoff, delay, fixed
        self.calls = 0

    async def run_turn(self, identity, message, state):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        agent = state.setdefault("agent", {})
        agent["fixed_streak"] = agent.get("fixed_streak", 0) + 1 if self.fixed else 0
        return TurnResult(kind="handoff" if self.handoff else "answer", answer=self.answer,
                          handoff=self.handoff, quick_replies=[], trace=TurnTrace(trace_id="t-1"))


def _app(runtime, engine=None):
    state = SimpleNamespace(agent_runtime=runtime, agent_session_store=engine, db_pool=None)
    return SimpleNamespace(state=state)


@pytest.mark.unit
def test_not_in_agent_audiences_returns_none(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIENCES", "tenant")
    store = FakeStore()
    out = asyncio.run(ae.handle_agent_entry(_req(), SimpleNamespace(app=_app(FakeRuntime())),
                                            None, store=store))
    assert out is None and store.started == []      # 正對照見下一測試


@pytest.mark.unit
def test_prospect_in_agent_audiences_runs_turn_and_persists(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIENCES", "prospect")
    store, rt = FakeStore(), FakeRuntime(answer="可以，租約管理支援線上簽章。")
    out = asyncio.run(ae.handle_agent_entry(_req(), SimpleNamespace(app=_app(rt)), None, store=store))
    assert rt.calls == 1 and store.started == ["agent:prospect"]
    assert out["answer"].startswith("可以") and out["handoff"] is None
    assert store.saved and store.saved[-1]["agent"]["fixed_streak"] == 0


@pytest.mark.unit
def test_runtime_missing_returns_none(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIENCES", "prospect")
    app = _app(None)
    out = asyncio.run(ae.handle_agent_entry(_req(), SimpleNamespace(app=app), None, store=FakeStore()))
    assert out is None


@pytest.mark.unit
def test_fixed_streak_three_marks_fallback_and_next_turn_routes_old_chain(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIENCES", "prospect")
    store = FakeStore(state={"config_key": "agent:prospect", "agent": {"fixed_streak": 2}})
    rt = FakeRuntime(answer="這題我幫您轉專人", handoff={"reason": "no_grounding"}, fixed=True)
    out = asyncio.run(ae.handle_agent_entry(_req(), SimpleNamespace(app=_app(rt)), None, store=store))
    assert out["handoff"] == {"reason": "no_grounding"}
    assert store.saved[-1]["agent"]["fallback_old_chain"] is True
    # 下一回合：已標回退 ⇒ None（走舊鏈），runtime 不再被呼叫
    out2 = asyncio.run(ae.handle_agent_entry(_req(), SimpleNamespace(app=_app(rt)), None, store=store))
    assert out2 is None and rt.calls == 1


@pytest.mark.unit
def test_stream_event_sequence_and_keepalive(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIENCES", "prospect")
    monkeypatch.setattr(ae, "KEEPALIVE_INTERVAL_S", 0.01)
    store = FakeStore()
    rt = FakeRuntime(answer="整段答案", handoff={"reason": "partial_grounding"}, delay=0.05)

    async def sse(kind, data):
        return f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def collect():
        resp = await ae.handle_agent_entry(_req(stream=True), SimpleNamespace(app=_app(rt)), None,
                                           store=store, sse_event=sse)
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return chunks

    chunks = asyncio.run(collect())
    events = [c.split("\n", 1)[0] for c in chunks if c.startswith("event:")]
    assert events == ["event: start", "event: intent", "event: answer_chunk", "event: metadata", "event: done"]
    assert any(c.startswith(": keepalive") for c in chunks)          # 心跳是註解行，不是事件
    meta = json.loads([c for c in chunks if c.startswith("event: metadata")][0].split("data: ", 1)[1])
    assert meta["handoff"] == {"reason": "partial_grounding"} and meta["trace_id"] == "t-1"
    assert store.saved                                                  # 串流結束才存


@pytest.mark.unit
def test_build_identity_is_trusted_input_and_audience_derived():
    ident = ae.build_identity(_req(target_user="property_manager", mode="b2b", role_id="20151"))
    assert ident.audience == "property_manager" and ident.role_id == "20151"
    ident2 = ae.build_identity(_req(target_user="prospect", role_id="99"))
    assert ident2.audience == "prospect"                                 # prospect ⛔ 不看 role_id


@pytest.mark.unit
def test_schedule_shadow_noop_without_runner_and_swallows_errors():
    app = SimpleNamespace(state=SimpleNamespace())
    ae.schedule_shadow(app, _req(), None, "old")                         # 無 runner ⇒ 不炸

    class Boom:
        def enabled(self, identity):
            raise RuntimeError("x")
    app2 = SimpleNamespace(state=SimpleNamespace(shadow_runner=Boom()))
    ae.schedule_shadow(app2, _req(), None, "old")                        # 例外被吞


@pytest.mark.unit
def test_schedule_shadow_injects_outline_for_prospect_only():
    """DSP-022 附帶：影子 state 要帶 `app.state.agent_outline`（prospect），tenant 不帶。"""
    seen = []

    class Runner:
        def enabled(self, identity):
            return True

        def schedule(self, identity, message, state, old_answer):
            seen.append(state)

    outline = SimpleNamespace(sha256="abc", sections=[], token_count=1)
    app = SimpleNamespace(state=SimpleNamespace(shadow_runner=Runner(), agent_outline=outline))
    ae.schedule_shadow(app, _req(), {"collected_data": {"x": 1}}, "old")
    assert seen[-1]["agent"]["outline"] is outline
    assert seen[-1]["collected_data"] == {"x": 1}                      # 其餘快照原樣帶過去

    tenant_req = _req(target_user="tenant")
    ae.schedule_shadow(app, tenant_req, None, "old")
    assert "outline" not in seen[-1].get("agent", {})                # 正對照：prospect 有、tenant 沒有


@pytest.mark.unit
def test_outline_injected_for_run_but_not_persisted(monkeypatch):
    monkeypatch.setenv("AGENT_AUDIENCES", "prospect")
    seen = {}

    class RT(FakeRuntime):
        async def run_turn(self, identity, message, state):
            seen["outline"] = state["agent"].get("outline")
            return await super().run_turn(identity, message, state)
    store, rt = FakeStore(), RT()
    app = _app(rt)
    app.state.agent_outline = SimpleNamespace(sha256="abc", sections=[], token_count=1)
    asyncio.run(ae.handle_agent_entry(_req(), SimpleNamespace(app=app), None, store=store))
    assert seen["outline"] is app.state.agent_outline          # 回合看得到
    assert "outline" not in store.saved[-1]["agent"]           # 存檔沒有（正對照：agent 鍵存在）
    assert "agent" in store.saved[-1]


@pytest.mark.unit
def test_app_agent_configured_is_plain_bool_and_lifespan_is_context_manager(monkeypatch):
    """2026-09-05 事故回歸：函式被插在 @asynccontextmanager 與 lifespan 之間，裝飾器套錯對象 ⇒
    `_agent_configured()` 回 context manager（恆真）⇒ 業主未跑 migration 時 app 起不來。"""
    for k in ("AGENT_AUDIENCES", "AGENT_SHADOW_AUDIENCES", "AGENT_TURN_ENABLED"):
        monkeypatch.delenv(k, raising=False)
    import app as app_module
    v = app_module._agent_configured()
    assert v is False                                   # 不是 truthy 物件
    monkeypatch.setenv("AGENT_AUDIENCES", "prospect")
    assert app_module._agent_configured() is True
    assert hasattr(app_module.lifespan, "__wrapped__") or app_module.lifespan.__name__ == "lifespan"
    import inspect
    assert not inspect.isasyncgenfunction(app_module.lifespan)   # 已被 asynccontextmanager 包裝


@pytest.mark.unit
def test_prospect_without_mode_defaults_to_b2b_pool():
    """售前池是 b2b 池（business_types && ['system_provider']）；prospect 缺 mode 不得落到 b2c（會掃進通用列）。"""
    assert ae.build_identity(_req(mode=None, target_user="prospect")).mode == "b2b"
    assert ae.build_identity(_req(mode=None, target_user="tenant")).mode == "b2c"     # 正對照
