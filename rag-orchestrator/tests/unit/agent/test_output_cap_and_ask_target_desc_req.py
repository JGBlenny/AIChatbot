"""gpt-oss 第一片（`.kiro/specs/agentic-mcp-orchestration/plan-oss-slice1-20261017.md`）。

1. 每次模型呼叫帶 `max_completion_tokens`（env `AGENT_MAX_COMPLETION_TOKENS`，預設 2000）；
   非正整數建構期就炸；`finish_reason == "length"` ⇒ `violations` 記 `llm_output_truncated`。
2. 給模型的 `ask_target` 說明列出 `ASK_TARGETS` 全部值（enum 本身不變）。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.agent.output_schema import ASK_TARGETS
from services.agent.runtime import (
    DEFAULT_MAX_COMPLETION_TOKENS,
    LLM_OUTPUT_TRUNCATED,
    _agent_output_response_format,
)
from tests.unit.agent.test_ask_target_req import _identity, _runtime
from tests.unit.agent.test_runtime_req import FakeProvider, _final_response

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:plan-oss-slice1"


def _with_finish(response, reason):
    response.choices[0] = SimpleNamespace(message=response.choices[0].message, finish_reason=reason)
    return response


@pytest.mark.req(_REQ)
async def test_default_cap_is_sent_on_every_model_call(monkeypatch):
    monkeypatch.delenv("AGENT_MAX_COMPLETION_TOKENS", raising=False)
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_identity(), "謝謝", {})
    assert DEFAULT_MAX_COMPLETION_TOKENS == 2000
    assert provider.calls and all(c["max_completion_tokens"] == 2000 for c in provider.calls)


@pytest.mark.req(_REQ)
async def test_env_overrides_the_cap(monkeypatch):
    monkeypatch.setenv("AGENT_MAX_COMPLETION_TOKENS", "1500")
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_identity(), "謝謝", {})
    assert provider.calls[0]["max_completion_tokens"] == 1500


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("bad", ["0", "-5", "abc", "1.5"])
def test_invalid_cap_fails_loud_at_construction(monkeypatch, bad):
    monkeypatch.setenv("AGENT_MAX_COMPLETION_TOKENS", bad)
    with pytest.raises(ValueError):
        _runtime()


@pytest.mark.req(_REQ)
async def test_truncated_output_is_flagged(monkeypatch):
    monkeypatch.delenv("AGENT_MAX_COMPLETION_TOKENS", raising=False)
    provider = FakeProvider([_with_finish(_final_response(answer="好的。"), "length")])
    result = await _runtime(provider=provider).run_turn(_identity(), "謝謝", {})
    assert LLM_OUTPUT_TRUNCATED in result.trace.violations


@pytest.mark.req(_REQ)
async def test_normal_finish_is_not_flagged(monkeypatch):
    monkeypatch.delenv("AGENT_MAX_COMPLETION_TOKENS", raising=False)
    provider = FakeProvider([_with_finish(_final_response(answer="好的。"), "stop")])
    result = await _runtime(provider=provider).run_turn(_identity(), "謝謝", {})
    assert LLM_OUTPUT_TRUNCATED not in result.trace.violations


@pytest.mark.req(_REQ)
def test_ask_target_description_lists_every_allowed_value():
    prop = _agent_output_response_format()["json_schema"]["schema"]["properties"]["ask_target"]
    desc = prop["description"]
    assert all(v in desc for v in ASK_TARGETS), [v for v in ASK_TARGETS if v not in desc]
    # enum 本身不變（值域仍只由 ASK_TARGETS 決定）
    assert prop["anyOf"][0]["enum"] == list(ASK_TARGETS)
    assert prop["anyOf"][1] == {"type": "null"}
