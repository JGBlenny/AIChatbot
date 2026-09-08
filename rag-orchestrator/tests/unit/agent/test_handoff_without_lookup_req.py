"""unit：S4 §5——零查詢轉人的出口降級（`_apply_handoff_without_lookup`）
＋ Verifier 敏感類配對 schema（`handoff_reason_mismatch`）
（Plan `inputs/plan-walkthrough-fixes-20260909.md` §5）。

⛔ 不接完整 `run_turn`——直接對 `_apply_handoff_without_lookup` 下手，這正是
`runtime.py` `_finalize` 實際呼叫的同一個函式（同 `test_candidate_trace_req.py`
對 `_emit_agent_decision` 的做法）。
"""
from __future__ import annotations

import pytest

from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.runtime import (
    ASK_TARGET_TEXT,
    SELECT_SCOPE_KEY,
    ToolCallRecord,
    TurnResult,
    TurnTrace,
    _apply_handoff_without_lookup,
)
from services.agent.verifier import OutputVerifier
from services.presales_gate import FactClass

from tests.unit.agent.test_verifier_req import _RULES_PATH

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:S4"


# ---------------------------------------------------------------------------
# 素材
# ---------------------------------------------------------------------------
def _handoff_result(
    *,
    handoff_reason: str = "no_grounding",
    fact_class: str = FactClass.feature.value,
    tool_calls: list | None = None,
) -> TurnResult:
    trace = TurnTrace(
        trace_id="t-1",
        tool_calls=list(tool_calls or []),
        final_kind="handoff",
        handoff_reason=handoff_reason,
    )
    handoff_dict = {
        "reason": handoff_reason,
        "fact_class": fact_class,
        "channel": "line",
        "message": "已為你轉真人客服，請稍候。",
    }
    return TurnResult(
        kind="handoff",
        answer=handoff_dict["message"],
        handoff=handoff_dict,
        quick_replies=[],
        trace=trace,
    )


def _one_tool_call() -> ToolCallRecord:
    return ToolCallRecord(
        id="call-1", name="jgb2.query.bills", args_summary={},
        ms=1, status="ok", n_items=0,
    )


# ---------------------------------------------------------------------------
# 真值表：五條件缺任一 ⇒ 不降級
# ---------------------------------------------------------------------------
def test_downgrades_when_all_five_conditions_hold():
    result = _handoff_result()
    out = _apply_handoff_without_lookup(result, agent_state={})

    assert out.answer == ASK_TARGET_TEXT
    assert out.kind == "answer"
    assert out.handoff is None
    assert out.trace.final_kind == "answer"
    assert out.trace.handoff_reason is None
    assert out.outcome["state"] == "clarifying"
    assert out.outcome["expects"] == "text"
    assert "handoff_without_lookup" in out.trace.violations


def test_not_downgraded_when_kind_is_not_handoff():
    result = _handoff_result()
    result.kind = "answer"
    result.trace.final_kind = "answer"
    out = _apply_handoff_without_lookup(result, agent_state={})
    assert out.kind == "answer"
    assert out.trace.final_kind == "answer"
    assert "handoff_without_lookup" not in out.trace.violations


def test_not_downgraded_when_reason_is_not_no_grounding():
    result = _handoff_result(handoff_reason="tool_unavailable")
    out = _apply_handoff_without_lookup(result, agent_state={})
    assert out.kind == "handoff"
    assert out.handoff is not None
    assert "handoff_without_lookup" not in out.trace.violations


def test_not_downgraded_when_fact_class_is_sensitive():
    result = _handoff_result(
        handoff_reason="sensitive_no_grounding", fact_class=FactClass.pricing.value
    )
    out = _apply_handoff_without_lookup(result, agent_state={})
    assert out.kind == "handoff"
    assert out.handoff is not None
    assert "handoff_without_lookup" not in out.trace.violations


def test_not_downgraded_when_tool_calls_nonempty():
    result = _handoff_result(tool_calls=[_one_tool_call()])
    out = _apply_handoff_without_lookup(result, agent_state={})
    assert out.kind == "handoff"
    assert "handoff_without_lookup" not in out.trace.violations


def test_not_downgraded_when_select_scope_pinned():
    result = _handoff_result()
    out = _apply_handoff_without_lookup(
        result, agent_state={SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "1"}}
    )
    assert out.kind == "handoff"
    assert "handoff_without_lookup" not in out.trace.violations


def test_downgrade_leaves_llm_mentioned_handoff_untouched():
    """`llm_mentioned_handoff` 不是本函式管的 handoff_reason 值——不在 no_grounding
    的降級範圍內，理應不動（正對照：reason 不合 ⇒ 上面的專用測試已覆蓋這條邏輯，
    這裡用實際會出現的另一個合法 reason 值再證一次）。"""
    result = _handoff_result(handoff_reason="llm_mentioned_handoff")
    out = _apply_handoff_without_lookup(result, agent_state={})
    assert out.kind == "handoff"
    assert "handoff_without_lookup" not in out.trace.violations


# ---------------------------------------------------------------------------
# Verifier：敏感類配對 schema
# ---------------------------------------------------------------------------
def _verifier() -> OutputVerifier:
    return OutputVerifier(VerifierRules.load(_RULES_PATH))


def _agent_output(*, kind: str, fact_class: str, handoff_reason: str | None) -> AgentOutput:
    return AgentOutput(
        kind=kind,
        fact_class=fact_class,
        handoff_reason=handoff_reason,
        sentences=[],
    )


def test_verifier_rejects_sensitive_fact_class_with_no_grounding_reason():
    """`fact_class=pricing`＋`no_grounding`（非敏感原因）⇒ Verifier 回
    `handoff_reason_mismatch`（不因零查詢降級——降級只對非敏感類生效，見上）。"""
    out = _agent_output(kind="handoff", fact_class=FactClass.pricing.value, handoff_reason="no_grounding")
    verdict = _verifier().verify(
        out, {}, "問報價多少", None, resolved={}, resolve_errors={}
    )
    assert verdict.ok is False
    assert verdict.reason == "SCHEMA"
    assert verdict.schema_cause == "handoff_reason_mismatch"


def test_verifier_accepts_sensitive_handoff_with_correct_reason():
    out = _agent_output(
        kind="handoff", fact_class=FactClass.pricing.value, handoff_reason="sensitive_no_grounding"
    )
    verdict = _verifier().verify(
        out, {}, "問報價多少", None, resolved={}, resolve_errors={}
    )
    assert verdict.ok is True


def test_verifier_accepts_non_sensitive_handoff_with_no_grounding_reason():
    out = _agent_output(
        kind="handoff", fact_class=FactClass.feature.value, handoff_reason="no_grounding"
    )
    verdict = _verifier().verify(
        out, {}, "問怎麼操作", None, resolved={}, resolve_errors={}
    )
    assert verdict.ok is True
