"""unit：T2 兩出口——資料裡沒有 vs 不做判斷（Plan
`inputs/plan-walkthrough-fixes-batch2-20260909.md` §3）。

守四件事：
1. **空結果的計算**（`_tool_result_empty`）：只有 `status=="ok"` 才可能為
   `True`；`error`／`timeout`／`rejected` 一律 `False`。
2. **出口閘真值表**（`_apply_handoff_data_exits`）：敏感類不動、混合空／非空
   ⇒ NO_JUDGEMENT、全空 ⇒ NO_DATA、任一筆逾時／撞名保留 id ⇒ 不動。
3. **迴圈內改寫提示**：命中時消耗一次 `max_rewrites`、重試輸出照常進
   Verifier 與所有出口閘（含敏感樣式仍被擋）；預算已耗盡 ⇒ 不呼叫
   `_build_fixed`，直接落到出口閘給 `NO_JUDGEMENT_TEXT`。
4. 三句固定句彼此不同、無插值。

⛔ 不接真 OpenAI、不接真 DB——沿用 `test_runtime_req.py` 的假件；「重試輸出仍
被 Verifier 擋」那一條用真 `OutputVerifier`（`test_handoff_without_lookup_req.py`
同一套規則檔），其餘用假 Verifier。
"""
from __future__ import annotations

import json

import pytest

from services.agent.budget import Budget
from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.runtime import (
    HANDOFF_DATA_REWRITE_HINT,
    NO_DATA_TEXT,
    NO_JUDGEMENT_TEXT,
    ToolCallRecord,
    TurnResult,
    TurnTrace,
    VerifierVerdict,
    _apply_handoff_data_exits,
    _tool_result_empty,
)
from services.agent.tools.registry import ToolResult
from services.agent.verifier import OutputVerifier
from services.presales_gate import FactClass

from tests.unit.agent.test_runtime_req import (
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _fake_message,
    _fake_response,
    _final_response,
    _identity,
    _runtime,
    _tool_call_response,
)
from tests.unit.agent.test_verifier_req import _RULES_PATH

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:T2"


# ---------------------------------------------------------------------------
# 1. `_tool_result_empty`：只有 `status=="ok"` 才可能為 True
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_empty_true_for_facts_empty_string_and_found_false():
    """正對照——`{"facts":"","found":False}` 是設計裡標準的「查無」哨兵形狀。"""
    result = ToolResult(ok=True, data={"facts": "", "found": False})
    assert _tool_result_empty(result, "ok") is True


@pytest.mark.req(_REQ)
def test_empty_true_for_found_false_alone():
    result = ToolResult(ok=True, data={"found": False})
    assert _tool_result_empty(result, "ok") is True


@pytest.mark.req(_REQ)
def test_empty_true_for_empty_dict_data():
    result = ToolResult(ok=True, data={})
    assert _tool_result_empty(result, "ok") is True


@pytest.mark.req(_REQ)
def test_empty_true_for_none_data():
    result = ToolResult(ok=True, data=None)
    assert _tool_result_empty(result, "ok") is True


@pytest.mark.req(_REQ)
def test_not_empty_for_nonempty_facts():
    result = ToolResult(ok=True, data={"facts": "押金全額退還。"})
    assert _tool_result_empty(result, "ok") is False


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("status", ["error", "timeout", "rejected"])
def test_empty_forced_false_when_status_not_ok(status):
    """plan-verifier r2 #1：「沒查成」⛔ 不得講成「不存在」——即使 data 形狀
    長得像哨兵空值，非 ok 一律 `False`。"""
    result = ToolResult(ok=False, data={"facts": "", "found": False}, error="TOOL_TIMEOUT")
    assert _tool_result_empty(result, status) is False


@pytest.mark.req(_REQ)
def test_tool_call_record_default_empty_is_false():
    """select／confirm 兩段建構點不傳 `empty`，逐字用預設值 `False`。"""
    record = ToolCallRecord(id="x", name="n", args_summary={}, ms=1, status="ok", n_items=0)
    assert record.empty is False


# ---------------------------------------------------------------------------
# 2. `_apply_handoff_data_exits` 真值表
# ---------------------------------------------------------------------------
def _record(status="ok", empty=False, id_="call-1") -> ToolCallRecord:
    return ToolCallRecord(id=id_, name="jgb2.query.bills", args_summary={}, ms=1,
                           status=status, n_items=0, empty=empty)


def _handoff_result(
    *,
    handoff_reason: str = "no_grounding",
    fact_class: str = FactClass.feature.value,
    tool_calls: list | None = None,
    violations: list | None = None,
) -> TurnResult:
    trace = TurnTrace(
        trace_id="t-1",
        tool_calls=list(tool_calls if tool_calls is not None else [_record()]),
        final_kind="handoff",
        handoff_reason=handoff_reason,
        violations=list(violations or []),
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


@pytest.mark.req(_REQ)
def test_all_empty_ok_records_gives_no_data():
    """正對照：全部工具結果 `status=="ok"` 且 `empty` ⇒ NO_DATA（五欄一起改）。"""
    result = _handoff_result(tool_calls=[_record(empty=True)])
    out = _apply_handoff_data_exits(result)

    assert out.answer == NO_DATA_TEXT
    assert out.kind == "answer"
    assert out.handoff is None
    assert out.trace.final_kind == "answer"
    assert out.trace.handoff_reason is None
    assert out.outcome["state"] == "answered"
    assert out.outcome["expects"] == "text"
    assert "handoff_no_data" in out.trace.violations


@pytest.mark.req(_REQ)
def test_mixed_empty_and_nonempty_gives_no_judgement():
    result = _handoff_result(
        tool_calls=[_record(empty=True, id_="a"), _record(empty=False, id_="b")]
    )
    out = _apply_handoff_data_exits(result)

    assert out.answer == NO_JUDGEMENT_TEXT
    assert out.kind == "answer"
    assert out.handoff is None
    assert out.trace.final_kind == "answer"
    assert out.trace.handoff_reason is None
    assert out.ask_target == "confirm_intent"
    assert out.outcome["state"] == "clarifying"
    assert out.outcome["expects"] == "text"
    assert "handoff_no_judgement" in out.trace.violations


@pytest.mark.req(_REQ)
def test_all_nonempty_gives_no_judgement():
    result = _handoff_result(tool_calls=[_record(empty=False)])
    out = _apply_handoff_data_exits(result)
    assert out.answer == NO_JUDGEMENT_TEXT
    assert out.ask_target == "confirm_intent"
    assert "handoff_no_judgement" in out.trace.violations


@pytest.mark.req(_REQ)
def test_untouched_when_kind_is_not_handoff():
    result = _handoff_result(tool_calls=[_record(empty=True)])
    result.kind = "answer"
    result.trace.final_kind = "answer"
    out = _apply_handoff_data_exits(result)
    assert out.kind == "answer"
    assert "handoff_no_data" not in out.trace.violations
    assert "handoff_no_judgement" not in out.trace.violations


@pytest.mark.req(_REQ)
def test_untouched_when_reason_is_not_no_grounding():
    result = _handoff_result(handoff_reason="tool_unavailable", tool_calls=[_record(empty=True)])
    out = _apply_handoff_data_exits(result)
    assert out.kind == "handoff"
    assert out.handoff is not None


@pytest.mark.req(_REQ)
def test_llm_mentioned_handoff_with_data_takes_no_judgement_exit():
    """verifier F1（2026-09-09）：`llm_mentioned_handoff` 與 `no_grounding` 同屬非敏感
    轉人原因，有資料時一樣走 NO_JUDGEMENT 出口。"""
    result = _handoff_result(handoff_reason="llm_mentioned_handoff", tool_calls=[_record(empty=False)])
    out = _apply_handoff_data_exits(result)
    assert out.kind == "answer"
    assert "handoff_no_judgement" in out.trace.violations


@pytest.mark.req(_REQ)
def test_untouched_when_fact_class_is_sensitive():
    result = _handoff_result(
        handoff_reason="sensitive_no_grounding",
        fact_class=FactClass.pricing.value,
        tool_calls=[_record(empty=True)],
    )
    out = _apply_handoff_data_exits(result)
    assert out.kind == "handoff"
    assert out.handoff is not None


@pytest.mark.req(_REQ)
def test_untouched_when_tool_calls_empty():
    result = _handoff_result(tool_calls=[])
    out = _apply_handoff_data_exits(result)
    assert out.kind == "handoff"
    assert out.handoff is not None


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("status", ["error", "timeout", "rejected"])
def test_untouched_when_any_record_not_ok(status):
    """正對照的鏡像：一筆逾時／錯誤／拒絕 ⇒ ⛔ 不得輸出 NO_DATA_TEXT——
    「沒查成」不是「查無資料」。"""
    result = _handoff_result(
        tool_calls=[_record(status=status, empty=False, id_="a"), _record(empty=True, id_="b")]
    )
    out = _apply_handoff_data_exits(result)
    assert out.kind == "handoff"
    assert out.answer != NO_DATA_TEXT
    assert out.answer != NO_JUDGEMENT_TEXT
    assert "handoff_no_data" not in out.trace.violations
    assert "handoff_no_judgement" not in out.trace.violations


@pytest.mark.req(_REQ)
def test_untouched_when_reserved_id_collision_present():
    """撞名保留 id 那筆即使 `status=="ok"` 也不得被當成「查了但查無」——
    整段維持既有出口。"""
    result = _handoff_result(
        tool_calls=[_record(empty=True)],
        violations=["tool_call_id_collides_with_reserved"],
    )
    out = _apply_handoff_data_exits(result)
    assert out.kind == "handoff"
    assert out.answer != NO_DATA_TEXT
    assert out.answer != NO_JUDGEMENT_TEXT


@pytest.mark.req(_REQ)
def test_llm_mentioned_handoff_all_empty_takes_no_data_exit():
    """verifier F1（2026-09-09）：`llm_mentioned_handoff` 與 `no_grounding` 同組
    （`NON_SENSITIVE_HANDOFF_REASONS`）——全部查無時走 NO_DATA 出口，不再放行。"""
    result = _handoff_result(handoff_reason="llm_mentioned_handoff", tool_calls=[_record(empty=True)])
    out = _apply_handoff_data_exits(result)
    assert out.kind == "answer"
    assert "handoff_no_data" in out.trace.violations


@pytest.mark.req(_REQ)
def test_budget_exhausted_untouched():
    result = _handoff_result(handoff_reason="budget_exhausted", tool_calls=[_record(empty=True)])
    out = _apply_handoff_data_exits(result)
    assert out.kind == "handoff"
    assert out.handoff is not None


# ---------------------------------------------------------------------------
# 3. 迴圈內改寫提示（整回合 `run_turn`）
# ---------------------------------------------------------------------------
def _handoff_no_grounding_response(fact_class="feature"):
    payload = {
        "kind": "handoff",
        "sentences": [],
        "fact_class": fact_class,
        "handoff_reason": "no_grounding",
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


@pytest.mark.req(_REQ)
async def test_rewrite_consumes_one_and_original_handoff_attempt_skips_verifier():
    """命中改寫時消耗 `max_rewrites` 一次；⛔ 出口閘另開模型呼叫（security
    r1 #1）——原始的 `no_grounding` 那次輸出根本不進 Verifier，只有改寫後那
    次才進。用 `Budget(max_rewrites=1)`：第二次模型仍回 `no_grounding`
    （模擬「模型改寫後還是不改」）⇒ 這一次改寫預算已耗盡，落到出口閘變成
    `NO_JUDGEMENT_TEXT`（正是下面「預算已耗盡」條所量的行為，這裡先證消耗
    確實只發生一次）。
    """
    provider = FakeProvider(
        [
            _tool_call_response("kb.get", {"kb_id": "1"}),
            _handoff_no_grounding_response(),
            _handoff_no_grounding_response(),
        ]
    )
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "押金全額退還政策"}, text_for_model="押金政策原文")]
    )
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    budget = Budget(max_rewrites=1)
    runtime = _runtime(provider=provider, registry=registry, verifier=verifier, budget=budget)

    result = await runtime.run_turn(_identity(), "我的押金到底會不會退", {})

    # 第一次 no_grounding 被改寫掉、⛔ 未進 Verifier；第二次改寫預算已耗盡，
    # 落到出口閘 ⇒ 這才是第一次真正呼叫 Verifier 的一次。
    assert len(verifier.calls) == 1
    assert result.kind == "answer"
    assert result.answer == NO_JUDGEMENT_TEXT
    assert result.handoff is None
    assert "handoff_no_judgement" in result.trace.violations
    # 三次模型呼叫：一次工具、兩次最終輸出嘗試。
    assert len(provider.calls) == 3


@pytest.mark.req(_REQ)
async def test_retried_output_answers_and_goes_through_verifier_normally():
    """改寫後模型改口正常作答 ⇒ 那次輸出照常進 Verifier 與所有出口閘，
    使用者拿到的是模型改寫後的答案（⛔ 不是固定句）。"""
    provider = FakeProvider(
        [
            _tool_call_response("kb.get", {"kb_id": "1"}),
            _handoff_no_grounding_response(),
            _final_response(answer="依系統資料，押金全額退還。"),
        ]
    )
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "押金全額退還政策"}, text_for_model="押金政策原文")]
    )
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    budget = Budget(max_rewrites=2)
    runtime = _runtime(provider=provider, registry=registry, verifier=verifier, budget=budget)

    result = await runtime.run_turn(_identity(), "我的押金到底會不會退", {})

    assert result.kind == "answer"
    assert result.answer == "依系統資料，押金全額退還。"
    assert len(verifier.calls) == 1
    assert verifier.calls[0]["out"].kind == "answer"
    # 改寫的固定句真的送進了模型上下文
    sent_contents = [
        m["content"] for call in provider.calls for m in call["messages"]
        if m.get("role") == "user"
    ]
    assert any(HANDOFF_DATA_REWRITE_HINT in (c or "") for c in sent_contents)


@pytest.mark.req(_REQ)
async def test_sensitive_pattern_retry_output_still_blocked_by_verifier():
    """重試輸出若含敏感樣式（價格），⛔ 不因為是「改寫後的輸出」就繞過
    Verifier——用真 `OutputVerifier` 證明它仍被擋（`SENSITIVE_TOPIC`），
    兩次都拒（`max_rewrites=1`：一次給 T2 改寫、一次是 Verifier 真的拒）
    後落固定句，⛔ 不是模型的敏感文字直接送出去。
    """
    provider = FakeProvider(
        [
            _tool_call_response("kb.get", {"kb_id": "1"}),
            _handoff_no_grounding_response(),
            _final_response(answer="退租押金要收1000元。"),
        ]
    )
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "退租押金相關規則"}, text_for_model="押金政策原文")]
    )
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    budget = Budget(max_rewrites=1)
    runtime = _runtime(provider=provider, registry=registry, verifier=verifier, budget=budget)

    result = await runtime.run_turn(_identity(), "我的押金到底會不會退", {})

    # T2 改寫用掉唯一一次預算；敏感樣式那次是 Verifier 真的拒（第二次
    # rewrite），budget 隨即耗盡 ⇒ 固定句收場，⛔ 敏感文字沒有送出去。
    assert result.kind == "handoff"
    assert result.handoff["reason"] == "budget_exhausted"
    assert "1000元" not in result.answer
    assert "退租押金要收1000元。" not in result.answer


@pytest.mark.req(_REQ)
async def test_budget_already_exhausted_skips_rewrite_and_falls_to_no_judgement():
    """改寫預算已為 0：⛔ 不消耗（不遞增）、⛔ 不走 `_build_fixed
    ("budget_exhausted")`——輸出照常往下走進 Verifier（handoff 對真
    Verifier 恆為 `ok=True`），最終落到出口閘給 `NO_JUDGEMENT_TEXT`
    （plan-verifier r1 #6）。"""
    provider = FakeProvider(
        [
            _tool_call_response("kb.get", {"kb_id": "1"}),
            _handoff_no_grounding_response(),
        ]
    )
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "押金全額退還政策"}, text_for_model="押金政策原文")]
    )
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    budget = Budget(max_rewrites=0)
    runtime = _runtime(provider=provider, registry=registry, verifier=verifier, budget=budget)

    result = await runtime.run_turn(_identity(), "我的押金到底會不會退", {})

    assert result.kind == "answer"
    assert result.answer == NO_JUDGEMENT_TEXT
    assert result.handoff is None
    assert result.trace.handoff_reason is None
    assert result.trace.final_kind == "answer"
    assert "handoff_no_judgement" in result.trace.violations
    # 只呼叫了兩次模型（工具＋一次最終輸出）——沒有多耗一次「改寫」呼叫。
    assert len(provider.calls) == 2


# ---------------------------------------------------------------------------
# 4. 三句固定句互不相同、無插值
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_three_fixed_sentences_are_distinct_and_interpolation_free():
    sentences = [NO_DATA_TEXT, NO_JUDGEMENT_TEXT, HANDOFF_DATA_REWRITE_HINT]
    assert len(set(sentences)) == 3
    for s in sentences:
        assert "{" not in s and "}" not in s
        assert "%s" not in s and "%d" not in s
