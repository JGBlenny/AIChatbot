"""unit：`AGENT_REASONING_EFFORT` 只在設定時才送 `reasoning_effort`（spec knowledge-outline-and-intent-architecture，
探針 5.x 報告 `inputs/probe-report-52-20260907.md` §3-3：gpt-5 系列預設推理 ⇒ p95 38 s）。

⛔ 未設時不得送——gpt-4o-mini 等模型不接受此參數；非法值建構期即炸。
傳遞形式＝`extra_body={"reasoning_effort": …}`（openai SDK 1.54 無具名參數）。
"""
from __future__ import annotations

import pytest

from services.agent import runtime as runtime_mod
from tests.unit.agent.test_runtime_req import (
    FakeProvider, FakeRegistry, FakeVerifier, _final_response, _identity, _runtime,
)

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:5.1")]


def _provider():
    return FakeProvider([_final_response(kind="handoff", handoff_reason="no_grounding")])


async def _one_turn(rt):
    await rt.run_turn(_identity(), "問句", {})


async def test_unset_env_sends_no_reasoning_effort(monkeypatch):
    monkeypatch.delenv("AGENT_REASONING_EFFORT", raising=False)
    prov = _provider()
    rt = _runtime(provider=prov, registry=FakeRegistry(), verifier=FakeVerifier())
    await _one_turn(rt)
    assert prov.async_client.chat.completions.calls, "假 provider 未被呼叫——測試沒跑到 create"
    assert all("extra_body" not in c and "reasoning_effort" not in c for c in prov.async_client.chat.completions.calls)


async def test_env_minimal_is_sent(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_EFFORT", "minimal")
    prov = _provider()
    rt = _runtime(provider=prov, registry=FakeRegistry(), verifier=FakeVerifier())
    await _one_turn(rt)
    assert [c.get("extra_body", {}).get("reasoning_effort") for c in prov.async_client.chat.completions.calls] == ["minimal"]


async def test_constructor_kwarg_overrides_env(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_EFFORT", "high")
    prov = _provider()
    # 既有 `_runtime` 夾具不收 reasoning_effort，直接建構：
    from tests.unit.agent.test_runtime_req import FakeAssembler, FakeClock
    rt = runtime_mod.AgentRuntime(prov, FakeRegistry(), FakeVerifier(), FakeAssembler(), runtime_mod.Budget(),
                                  stage="M1", clock=FakeClock(), reasoning_effort="low")
    await _one_turn(rt)
    assert [c.get("extra_body", {}).get("reasoning_effort") for c in prov.async_client.chat.completions.calls] == ["low"]


@pytest.mark.parametrize("bad", ["max", "MINIMAL", "1"])
def test_invalid_value_fails_loud_at_construction(monkeypatch, bad):
    monkeypatch.setenv("AGENT_REASONING_EFFORT", bad)
    with pytest.raises(ValueError):
        _runtime(provider=_provider(), registry=FakeRegistry(), verifier=FakeVerifier())


def test_value_domain_is_closed():
    assert runtime_mod.REASONING_EFFORT_VALUES == frozenset({"none", "minimal", "low", "medium", "high"})  # 2026-09-10 加 none（gpt-5.6 帶工具只接受 none）
