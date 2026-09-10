"""unit：第六批 #2（單元 A 交接）——`confirm.request` 以物件＋期別對到多筆帳單時，Runtime 收成
ask 回合＋`select:bill:<id>` 按鈕；⛔ 不建 pending、不出卡、不記 `confirm_request_data_shape_invalid`。
正對照：同一 registry 回單筆卡片形狀時照舊建 pending 出卡。"""
from __future__ import annotations

import json

import pytest

from services.agent.budget import Budget
from services.agent.runtime import (
    AgentRuntime, CONFIRM_CANDIDATES_MAX, CONFIRM_CANDIDATES_TEXT, PENDING_CONFIRM_KEY, _SELECT_VALUE_RE,
)
from services.agent.tools.registry import ToolResult
from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeProvider, FakeRegistry, FakeVerifier, VerifierVerdict,
    _fake_message, _fake_response, _fake_tool_call, _final_response, _identity,
)

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:batch6-2")]


def _runtime(provider, registry):
    return AgentRuntime(provider, registry, FakeVerifier([VerifierVerdict(ok=True)] * 4), FakeAssembler(),
                        Budget(), stage="M1", clock=FakeClock())


def _rows(n):
    return [{"id": 756240 + i, "title": "基隆獨立共生公寓雅房", "status": 1, "date_expire": f"2026-0{8 + i % 2}-01", "amount": 7500}
            for i in range(n)]


def _candidates_result(n=2):
    payload = {"action": "bill_due_extend", "estate_name": "基隆獨立共生公寓雅房", "period": "九月", "days": 3}
    return ToolResult(ok=True, data={"facts": "", "candidates": _rows(n), "action": "bill_due_extend", "payload": payload},
                      text_for_model="候選")


def _confirm_call(payload):
    return _fake_response(_fake_message(tool_calls=[_fake_tool_call(
        "confirm.request", {"summary": "延後", "payload": json.dumps(payload, ensure_ascii=False)}, call_id="c1")]))


async def _turn(result):
    state = {"agent": {}}
    registry = FakeRegistry(call_results=[result])
    provider = FakeProvider([
        _confirm_call({"action": "bill_due_extend", "estate_name": "基隆獨立共生公寓雅房", "period": "九月", "days": 3}),
        _final_response(answer="不該走到這"),
    ])
    r = await _runtime(provider, registry).run_turn(_identity(), "基隆獨立共生公寓雅房九月的房租晚三天繳", state)
    return r, state, provider


async def test_multiple_candidates_become_an_ask_turn_with_select_buttons():
    r, state, provider = await _turn(_candidates_result(2))
    assert r.kind == "ask"
    assert r.outcome["state"] == "clarifying" and r.outcome["expects"] == "choice"
    assert r.answer.startswith(CONFIRM_CANDIDATES_TEXT)
    assert "756240" in r.answer and "756241" in r.answer
    values = [q["value"] for q in r.quick_replies]
    assert values == ["select:bill:756240", "select:bill:756241"]
    assert all(_SELECT_VALUE_RE.fullmatch(v) for v in values)
    assert all(q["label"].startswith("編號 ") for q in r.quick_replies)
    assert PENDING_CONFIRM_KEY not in state["agent"], "候選回合⛔ 不建 pending"
    assert "confirm_request_candidates" in r.trace.violations
    assert "confirm_request_data_shape_invalid" not in r.trace.violations
    assert len(provider.calls) == 1, "候選回合直接收尾，⛔ 不再回模型"


async def test_candidates_are_capped():
    r, _, _ = await _turn(_candidates_result(CONFIRM_CANDIDATES_MAX + 3))
    assert len(r.quick_replies) == CONFIRM_CANDIDATES_MAX


async def test_single_card_result_still_builds_pending_positive_control():
    card = ToolResult(ok=True, data={
        "pending_id": "0123456789abcdef", "card": "即將調整帳單到期日", "action": "bill_due_extend",
        "payload": {"action": "bill_due_extend", "bill_id": "756248"}, "quick_replies": [], "hint": None, "estate_id": "1",
    }, text_for_model="")
    r, state, _ = await _turn(card)
    assert r.outcome["state"] == "confirm_pending"
    assert PENDING_CONFIRM_KEY in state["agent"]
    assert "confirm_request_candidates" not in r.trace.violations


async def test_candidates_without_known_action_fall_through_unchanged():
    bad = ToolResult(ok=True, data={"candidates": _rows(2), "action": "repair_create", "payload": {}}, text_for_model="x")
    r, state, provider = await _turn(bad)
    assert r.kind != "ask" or "confirm_request_candidates" not in r.trace.violations
    assert PENDING_CONFIRM_KEY not in state["agent"]
    assert len(provider.calls) == 2  # 照舊回模型
