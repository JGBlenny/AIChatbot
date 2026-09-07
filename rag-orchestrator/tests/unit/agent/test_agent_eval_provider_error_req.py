"""unit：`_run_scenario_agent` 單回合 provider 例外 ⇒ 記 `provider_error` 列、其餘回合照跑（探針 53：整輪炸掉）。"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

_RAG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _RAG)
from tools import agent_eval as ae  # noqa: E402
from services.agent.runtime import TurnResult, TurnTrace  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:4.3")]


class _Runtime:
    def __init__(self):
        self.calls = 0

    async def run_turn(self, identity, q, state):
        self.calls += 1
        if self.calls == 2:
            raise TimeoutError("simulated provider timeout")
        return TurnResult(kind="answer", answer="ok。", handoff=None, quick_replies=[],
                          trace=TurnTrace(trace_id=f"t{self.calls}", final_kind="answer"))


def test_provider_exception_becomes_error_row_and_run_continues():
    rt = _Runtime()
    turns = [ae.Turn(turn=i, q=f"q{i}", expect_kind="answer") for i in range(1, 4)]
    out = asyncio.run(ae._run_scenario_agent(rt, identity=None, turns=turns))
    assert rt.calls == 3, "第 2 回合例外後應繼續跑第 3 回合"
    kinds = [r.kind for _t, r, _ms, _a in out]
    assert kinds == ["answer", "handoff", "answer"]
    err = out[1][1]
    assert err.trace.handoff_reason == "provider_error"
    assert err.trace.violations == ["provider_error:TimeoutError"]
    assert err.answer == ""


def test_cancelled_error_is_not_swallowed():
    class _Cancel:
        async def run_turn(self, identity, q, state):
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(ae._run_scenario_agent(_Cancel(), identity=None, turns=[ae.Turn(turn=1, q="q", expect_kind="answer")]))
