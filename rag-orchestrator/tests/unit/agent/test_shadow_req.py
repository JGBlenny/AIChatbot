"""unit：`services.agent.shadow.ShadowRunner`（spec agentic-mcp-orchestration
任務 4.1｜design 元件 7）。

全部離線：假 `runtime_factory`／假 `db_pool`／假時鐘，`usage_metering` 的
`begin`／`add_llm_usage`／`set_path`／`set_decision`／`finalize` 四／五個
呼叫點以 monkeypatch 換成間諜函式，只驗證 `ShadowRunner` 傳給它們的參數
（本檔不驗 `usage_metering` 本身的行為，那是它自己的測試檔的事）。
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from services.agent.identity import Identity
from services.agent.output_schema import VerifierVerdict
from services.agent.runtime import TurnResult, TurnTrace
from services.agent.shadow import ShadowRecord, ShadowRunner, _looks_like_handoff_text
from services.conversational_config import effective_handoff_message

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:4.1"


# ---------------------------------------------------------------------------
# 共用假物件
# ---------------------------------------------------------------------------


def _identity(target_user: str = "prospect", mode: str = "b2b", session_id: str = "s1") -> Identity:
    return Identity(vendor_id=1, target_user=target_user, mode=mode, session_id=session_id)


def _trace(prompt_tokens: int = 10, completion_tokens: int = 5) -> TurnTrace:
    return TurnTrace(
        trace_id="trace-1",
        tool_calls=[],
        llm_calls=1,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        verifier=[VerifierVerdict(ok=True, reason=None, sent=None, term_id=None, quote_len=None)],
        final_kind="answer",
        handoff_reason=None,
        latency_ms=12,
        violations=[],
        rules_sha="rulesha",
        outline_sha="outsha",
    )


def _result(kind: str = "answer", answer: str = "新答案", trace: Optional[TurnTrace] = None) -> TurnResult:
    return TurnResult(
        kind=kind,
        answer=answer,
        handoff=None,
        quick_replies=[],
        trace=trace or _trace(),
    )


class FakeRuntime:
    def __init__(self, result: TurnResult, *, error: Optional[Exception] = None):
        self._result = result
        self._error = error
        self._model = "gpt-4o-mini"
        self.run_turn_calls: list[tuple] = []

    async def run_turn(self, identity, user_message, state):
        self.run_turn_calls.append((identity, user_message, state))
        if self._error is not None:
            raise self._error
        return self._result


@dataclass
class FakeFactory:
    """記錄呼叫參數的 `runtime_factory`。"""

    runtime: FakeRuntime
    calls: list = field(default_factory=list)

    def __call__(self, readonly_view: bool = False) -> FakeRuntime:
        self.calls.append({"readonly_view": readonly_view})
        return self.runtime


class FakePool:
    def __init__(self, fetchval_result: float = 0.0):
        self.fetchval_result = fetchval_result
        self.fetchval_calls: list = []
        self.execute_calls: list = []

    async def fetchval(self, sql, *args):
        self.fetchval_calls.append((sql, args))
        return self.fetchval_result

    async def execute(self, sql, *args):
        self.execute_calls.append((sql, args))


class FakeClock:
    def __init__(self, start: float = 1_000.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, delta: float) -> None:
        self.t += delta


class MeteringSpy:
    """monkeypatch 掉 `usage_metering` 的五個呼叫點，記錄參數。"""

    def __init__(self):
        self.begin_calls: list = []
        self.add_llm_usage_calls: list = []
        self.set_path_calls: list = []
        self.set_decision_calls: list = []
        self.finalize_calls: list = []

    def begin(self, fields):
        self.begin_calls.append(fields)

    def add_llm_usage(self, model, usage):
        self.add_llm_usage_calls.append((model, usage))

    def set_path(self, processing_path=None, answer_source=None):
        self.set_path_calls.append(processing_path)

    def set_decision(self, snapshot=None, facet_event=None):
        self.set_decision_calls.append(snapshot)

    def finalize(self, status="success", http_status=200, db_pool=None):
        self.finalize_calls.append(db_pool)


@pytest.fixture
def metering_spy(monkeypatch):
    spy = MeteringSpy()
    import services.agent.shadow as shadow_mod

    monkeypatch.setattr(shadow_mod.usage_metering, "begin", spy.begin)
    monkeypatch.setattr(shadow_mod.usage_metering, "add_llm_usage", spy.add_llm_usage)
    monkeypatch.setattr(shadow_mod.usage_metering, "set_path", spy.set_path)
    monkeypatch.setattr(shadow_mod.usage_metering, "set_decision", spy.set_decision)
    monkeypatch.setattr(shadow_mod.usage_metering, "finalize", spy.finalize)
    return spy


async def _run_and_collect(runner: ShadowRunner, identity, message, state, old_answer, monkeypatch):
    """呼叫 `schedule()`，攔截它建立的 task，等它跑完再回傳。"""
    created: list[asyncio.Task] = []
    real_create_task = asyncio.create_task

    def _capture(coro, **kwargs):
        task = real_create_task(coro, **kwargs)
        created.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", _capture)
    # `schedule()` 用 `loop.create_task`，不是模組層 `asyncio.create_task`——
    # 兩者最終等價（`AbstractEventLoop.create_task` 與 `asyncio.create_task`
    # 都是把 coroutine 包成 Task 掛進同一個迴圈），改用同一個攔截點即可。
    loop = asyncio.get_running_loop()
    real_loop_create_task = loop.create_task

    def _capture_loop(coro, **kwargs):
        task = real_loop_create_task(coro, **kwargs)
        created.append(task)
        return task

    monkeypatch.setattr(loop, "create_task", _capture_loop)

    runner.schedule(identity, message, state, old_answer)
    assert created, "schedule() 應該立刻建立一顆 task"
    await asyncio.gather(*created)


# ---------------------------------------------------------------------------
# 1. enabled() 三態
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_enabled_false_when_audience_not_allowed(monkeypatch):
    monkeypatch.setenv("AGENT_SHADOW_AUDIENCES", "property_manager")
    runner = ShadowRunner(lambda readonly_view=False: None, FakePool())
    assert runner.enabled(_identity(target_user="prospect", mode="b2b")) is False


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_enabled_true_when_audience_allowed_and_under_cap(monkeypatch):
    monkeypatch.setenv("AGENT_SHADOW_AUDIENCES", "prospect")
    monkeypatch.setenv("AGENT_SHADOW_MONTHLY_USD_CAP", "50")
    pool = FakePool(fetchval_result=1.23)
    runner = ShadowRunner(lambda readonly_view=False: None, pool, clock=FakeClock())
    assert runner.enabled(_identity()) is True
    await asyncio.sleep(0)  # 讓背景刷新 task 有機會跑
    assert pool.fetchval_calls, "應該觸發一次月成本查詢"


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_enabled_false_when_over_monthly_cap(monkeypatch, caplog):
    monkeypatch.setenv("AGENT_SHADOW_AUDIENCES", "prospect")
    monkeypatch.setenv("AGENT_SHADOW_MONTHLY_USD_CAP", "10")
    runner = ShadowRunner(lambda readonly_view=False: None, FakePool(), clock=FakeClock())
    runner._cost_cached_usd = 10.0  # 直接種快取，避開背景查詢的非同步時序
    runner._cost_cached_at = runner._clock()
    with caplog.at_level("WARNING"):
        assert runner.enabled(_identity()) is False
    assert any("上限" in r.message for r in caplog.records)


@pytest.mark.req(_SPEC)
def test_enabled_cap_warning_throttled_to_one_hour(monkeypatch, caplog):
    monkeypatch.setenv("AGENT_SHADOW_AUDIENCES", "prospect")
    monkeypatch.setenv("AGENT_SHADOW_MONTHLY_USD_CAP", "10")
    clock = FakeClock()
    runner = ShadowRunner(lambda readonly_view=False: None, FakePool(), clock=clock)
    runner._cost_cached_usd = 10.0
    runner._cost_cached_at = clock()
    with caplog.at_level("WARNING"):
        runner.enabled(_identity())
        first_count = len(caplog.records)
        clock.advance(10)  # 遠小於 1 小時節流窗
        runner.enabled(_identity())
        second_count = len(caplog.records)
    assert second_count == first_count, "1 小時內第二次超限不應再告警"


# ---------------------------------------------------------------------------
# 2. schedule() 立刻返回 + task 完成後計量落地
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_schedule_returns_immediately(monkeypatch, metering_spy):
    factory = FakeFactory(FakeRuntime(_result()))
    runner = ShadowRunner(factory, FakePool())
    t0 = time.perf_counter()
    runner.schedule(_identity(), "問題", {}, "舊答案")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 10, f"schedule() 應該幾乎立即返回，實際 {elapsed_ms:.2f}ms"
    await asyncio.sleep(0.05)  # 讓背景 task 跑完，避免 pending task 洩漏警告


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_schedule_factory_called_with_readonly_view_true(monkeypatch):
    factory = FakeFactory(FakeRuntime(_result()))
    runner = ShadowRunner(factory, FakePool())
    await _run_and_collect(runner, _identity(), "問題", {}, "舊答案", monkeypatch)
    assert factory.calls == [{"readonly_view": True}]


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_schedule_set_decision_uses_whitelisted_keys_only(monkeypatch, metering_spy):
    factory = FakeFactory(FakeRuntime(_result(answer="這是新答案")))
    runner = ShadowRunner(factory, FakePool())
    await _run_and_collect(runner, _identity(), "問題", {}, "這是舊答案", monkeypatch)

    assert len(metering_spy.set_decision_calls) == 1
    snapshot = metering_spy.set_decision_calls[0]
    assert set(snapshot.keys()) == {"agent_shadow"}
    record = snapshot["agent_shadow"]
    assert set(record.keys()) == set(ShadowRecord.model_fields.keys())

    # ⛔ 無原文鍵——遞迴掃過整個 snapshot，任何字串值都不得等於送進去的原文。
    def _walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from _walk(v)
        else:
            yield obj

    leaked = [v for v in _walk(snapshot) if v in ("這是新答案", "這是舊答案", "問題")]
    assert leaked == [], f"decision_snapshot 洩漏原文：{leaked}"
    for forbidden_key in ("answer", "old_answer", "quote", "user_message"):
        assert forbidden_key not in record


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_schedule_emits_begin_is_internal_and_shadow_processing_path(monkeypatch, metering_spy):
    factory = FakeFactory(FakeRuntime(_result()))
    runner = ShadowRunner(factory, FakePool())
    await _run_and_collect(runner, _identity(), "問題", {}, "舊答案", monkeypatch)

    assert len(metering_spy.begin_calls) == 1
    assert metering_spy.begin_calls[0]["disable_answer_synthesis"] is True
    assert metering_spy.set_path_calls == ["shadow:agent"]
    assert metering_spy.finalize_calls == [runner._db_pool]


# ---------------------------------------------------------------------------
# 3. 影子回合不寫任何 save／state 隔離
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_shadow_never_calls_any_save(monkeypatch, metering_spy):
    """`ShadowRunner` 完全不持有任何 state store 參照——本測試證明：
    傳入的 `state_snapshot` 在整個流程中只被 `deepcopy`，原物件不被修改，
    且 `ShadowRunner` 沒有任何屬性指向一個帶 `save` 方法的物件。
    """
    state = {"agent": {"slots": {"a": 1}}}
    factory = FakeFactory(FakeRuntime(_result()))
    runner = ShadowRunner(factory, FakePool())
    await _run_and_collect(runner, _identity(), "問題", dict(state), "舊答案", monkeypatch)

    assert not hasattr(runner, "store") and not hasattr(runner, "_store")
    # 原始傳入物件本身在呼叫端仍是它自己那份（此處另建一份 `dict(state)` 傳入，
    # 這裡驗證的是 `FakeRuntime.run_turn` 收到的不是同一個物件參照）。
    received_state = factory.runtime.run_turn_calls[0][2]
    assert received_state is not state


# ---------------------------------------------------------------------------
# 4. diff_flags 五態
# ---------------------------------------------------------------------------


_HANDOFF_TEXT = effective_handoff_message(None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_kind,agent_answer,old_answer,expected",
    [
        ("answer", "相同答案", "相同答案", "same"),
        ("answer", "新答案A", "舊答案B", "different"),
        ("handoff", "轉人固定句", "老鏈也回答了", "agent_handoff_old_answered"),
        ("answer", "新鏈答上了", _HANDOFF_TEXT, "old_handoff_agent_answered"),
        ("handoff", "轉人固定句", _HANDOFF_TEXT, "both_handoff"),
    ],
)
@pytest.mark.req(_SPEC)
async def test_diff_flags_five_states(
    monkeypatch, metering_spy, agent_kind, agent_answer, old_answer, expected
):
    factory = FakeFactory(FakeRuntime(_result(kind=agent_kind, answer=agent_answer)))
    runner = ShadowRunner(factory, FakePool())
    await _run_and_collect(runner, _identity(), "問題", {}, old_answer, monkeypatch)

    record = metering_spy.set_decision_calls[0]["agent_shadow"]
    assert record["diff_flags"] == [expected]


def test_looks_like_handoff_text_matches_effective_message():
    assert _looks_like_handoff_text(_HANDOFF_TEXT) is True
    assert _looks_like_handoff_text("完全不相關的一句話") is False
    assert _looks_like_handoff_text("") is False
    assert _looks_like_handoff_text(None) is False


# ---------------------------------------------------------------------------
# 5. prospect 才寫 agent_shadow_texts，tenant 不寫
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_writes_texts_only_for_prospect(monkeypatch, metering_spy):
    pool = FakePool()
    factory = FakeFactory(FakeRuntime(_result()))
    runner = ShadowRunner(factory, pool)
    await _run_and_collect(
        runner, _identity(target_user="prospect", mode="b2b"), "問題", {}, "舊答案", monkeypatch
    )
    assert len(pool.execute_calls) == 1


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_does_not_write_texts_for_tenant(monkeypatch, metering_spy):
    pool = FakePool()
    factory = FakeFactory(FakeRuntime(_result()))
    runner = ShadowRunner(factory, pool)
    await _run_and_collect(
        runner, _identity(target_user="tenant", mode="b2c"), "問題", {}, "舊答案", monkeypatch
    )
    assert pool.execute_calls == []


# ---------------------------------------------------------------------------
# 6. 例外不外洩
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_exception_in_run_turn_does_not_propagate(monkeypatch, caplog):
    factory = FakeFactory(FakeRuntime(_result(), error=RuntimeError("boom")))
    runner = ShadowRunner(factory, FakePool())
    with caplog.at_level("ERROR"):
        await _run_and_collect(runner, _identity(), "問題", {}, "舊答案", monkeypatch)
    assert any("影子回合失敗" in r.message for r in caplog.records)


@pytest.mark.asyncio
@pytest.mark.req(_SPEC)
async def test_exception_in_runtime_factory_does_not_propagate(monkeypatch, caplog):
    def _boom(readonly_view=False):
        raise RuntimeError("factory 炸了")

    runner = ShadowRunner(_boom, FakePool())
    with caplog.at_level("ERROR"):
        await _run_and_collect(runner, _identity(), "問題", {}, "舊答案", monkeypatch)
    assert any("影子回合失敗" in r.message for r in caplog.records)


@pytest.mark.req(_SPEC)
def test_schedule_without_running_loop_does_not_raise(caplog):
    """沒有事件迴圈（例如同步呼叫端）⇒ 略過、不拋例外（`schedule_shadow` 呼叫端
    另有自己的 try/except，但 `ShadowRunner` 本身也不該假設一定有迴圈）。
    """
    runner = ShadowRunner(lambda readonly_view=False: None, FakePool())
    with caplog.at_level("WARNING"):
        runner.schedule(_identity(), "問題", {}, "舊答案")
    assert any("無事件迴圈" in r.message for r in caplog.records)
