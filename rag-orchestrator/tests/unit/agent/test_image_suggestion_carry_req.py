"""unit：照片辨識分類接到建單參數（line-bot 2026-09-10 回報，單號 12357／12358 對照 12356）。

守的事：
1. 照片回合把 `ImageTurnInput.suggested_category`（分類樹封閉值）寫進
   `agent_state[IMAGE_SUGGESTION_KEY]`；沒辨識出分類 ⇒ 寫 None（新照片覆寫、不殘留）。
2. 之後任一回合模型呼叫 `confirm.request`／`repair_create` 且 payload 缺 `category_name`
   ⇒ 程式補分類；缺 `description` ⇒ 補 `IMAGE_DESCRIPTION_TEMPLATE`（只含分類名）。
   模型有給的欄位不動；非 repair_create／payload 非 JSON／無建議 ⇒ 原樣。
3. 出卡成功 ⇒ 建議清掉。
正對照：同一回合不帶建議時 payload 原樣送進 registry（證明改動只在有建議時發生）。
"""
from __future__ import annotations

import json

import pytest

from services.agent.runtime import (
    IMAGE_DESCRIPTION_TEMPLATE,
    IMAGE_SUGGESTION_KEY,
    PENDING_CONFIRM_KEY,
    ImageTurnInput,
    _apply_image_suggestion_to_confirm_args,
)
from services.agent.tools.registry import ToolResult

from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeProvider, FakeRegistry, FakeVerifier, VerifierVerdict,
    _fake_message, _fake_response, _fake_tool_call, _final_response, _identity,
)
from services.agent.budget import Budget
from services.agent.runtime import AgentRuntime

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:linebot-20260910-repair-category")]


def _runtime(provider, registry):
    return AgentRuntime(provider, registry, FakeVerifier([VerifierVerdict(ok=True)] * 4), FakeAssembler(),
                        Budget(), stage="M1", clock=FakeClock())


def _confirm_args(payload: dict) -> dict:
    return {"summary": "建單", "payload": json.dumps(payload, ensure_ascii=False)}


# ── 1. 純函式 ────────────────────────────────────────────────────────────────
def test_fills_missing_category_and_description_only():
    args = _confirm_args({"action": "repair_create", "estate_name": "某物件", "description": ""})
    new, applied = _apply_image_suggestion_to_confirm_args(args, {"category_name": "房屋結構"})
    payload = json.loads(new["payload"])
    assert applied == ["category_name", "description"]
    assert payload["category_name"] == "房屋結構"
    assert payload["description"] == IMAGE_DESCRIPTION_TEMPLATE.format(category="房屋結構")
    assert payload["estate_name"] == "某物件"


def test_model_supplied_fields_are_untouched():
    args = _confirm_args({"action": "repair_create", "category_name": "水電", "description": "天花板在漏水"})
    new, applied = _apply_image_suggestion_to_confirm_args(args, {"category_name": "房屋結構"})
    assert applied == [] and new is args


@pytest.mark.parametrize("args,suggestion", [
    (_confirm_args({"action": "bill_due_extend", "bill_id": "1"}), {"category_name": "房屋結構"}),
    ({"summary": "x", "payload": "not json"}, {"category_name": "房屋結構"}),
    ({"summary": "x", "payload": json.dumps(["list"])}, {"category_name": "房屋結構"}),
    (_confirm_args({"action": "repair_create"}), None),
    (_confirm_args({"action": "repair_create"}), {"category_name": "  "}),
    ("not a dict", {"category_name": "房屋結構"}),
])
def test_untouched_when_shape_or_suggestion_is_off(args, suggestion):
    new, applied = _apply_image_suggestion_to_confirm_args(args, suggestion)
    assert applied == [] and new is args


def test_template_contains_only_the_category_name():
    assert "{category}" in IMAGE_DESCRIPTION_TEMPLATE
    assert not any(ch.isdigit() for ch in IMAGE_DESCRIPTION_TEMPLATE)


# ── 2. 照片回合寫入 session（含覆寫成 None）────────────────────────────────
async def test_photo_turn_stores_closed_suggestion_and_next_photo_overwrites():
    state = {"agent": {}}
    rt = _runtime(FakeProvider([_final_response(answer="請問急不急？")]), FakeRegistry())
    await rt.run_turn(_identity(), "基隆溫馨一人宅套房", state,
                      image=ImageTurnInput(status="ok", facts="看得出天花板有水漬。", processed=1, total=1,
                                           suggested_category="房屋結構"))
    assert state["agent"][IMAGE_SUGGESTION_KEY] == {"category_name": "房屋結構"}

    rt2 = _runtime(FakeProvider([_final_response(answer="看不出損壞。")]), FakeRegistry())
    await rt2.run_turn(_identity(), "再一張", state,
                       image=ImageTurnInput(status="ok", facts="看不出損壞。", processed=1, total=1))
    assert state["agent"][IMAGE_SUGGESTION_KEY] is None


# ── 3. 跨回合：照片 → 問急不急 → 「不急」→ confirm.request 被補 ───────────
def _confirm_ok_result():
    return ToolResult(ok=True, data={
        "pending_id": "0123456789abcdef", "card": "即將建立修繕單", "action": "repair_create",
        "payload": {"action": "repair_create"}, "quick_replies": [], "hint": None, "estate_id": "1",
    }, text_for_model="")


async def test_next_turn_confirm_request_gets_category_and_description_then_clears():
    state = {"agent": {IMAGE_SUGGESTION_KEY: {"category_name": "房屋結構"}}}
    registry = FakeRegistry(call_results=[_confirm_ok_result()])
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[_fake_tool_call(
            "confirm.request",
            _confirm_args({"action": "repair_create", "estate_name": "基隆溫馨一人宅套房", "description": ""}),
            call_id="c1")])),
        _final_response(answer="已出卡"),
    ])
    result = await _runtime(provider, registry).run_turn(_identity(), "不急", state)
    sent = [c for c in registry.call_args if c["name"] == "confirm.request"]
    assert sent, "confirm.request 沒被送進 registry——前提不成立"
    payload = json.loads(sent[0]["args"]["payload"])
    assert payload["category_name"] == "房屋結構"
    assert payload["description"] == "照片辨識：房屋結構"
    assert "image_suggestion_applied:category_name" in result.trace.violations
    assert IMAGE_SUGGESTION_KEY not in state["agent"], "出卡成功後建議應清掉"


async def test_without_suggestion_payload_goes_through_verbatim():
    state = {"agent": {}}
    registry = FakeRegistry(call_results=[_confirm_ok_result()])
    original = _confirm_args({"action": "repair_create", "estate_name": "基隆溫馨一人宅套房", "description": ""})
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[_fake_tool_call("confirm.request", original, call_id="c1")])),
        _final_response(answer="已出卡"),
    ])
    result = await _runtime(provider, registry).run_turn(_identity(), "不急", state)
    sent = [c for c in registry.call_args if c["name"] == "confirm.request"]
    assert sent and json.loads(sent[0]["args"]["payload"]) == json.loads(original["payload"])
    assert not any(v.startswith("image_suggestion_applied") for v in result.trace.violations)
