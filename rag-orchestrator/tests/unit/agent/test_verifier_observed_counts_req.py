"""unit：R1b——Verifier「觀察到而未擋」的類別計數進 trace（Plan R §0b／§6b｜DSP-040 絆線）。

病灶：`AGENT_VERIFIER_MODE=grounding_observe` 下，Verifier 判到違規但**放行**，
`VerifierVerdict.observed` 記了類別卻**沒有任何落點**——線上要回答「觀察模式這一週
本來會擋幾次、擋哪幾類」時，只能一筆一筆翻 attempt log（dev 專用旗，線上不開）。
R1b 把它累加進 `TurnTrace.verifier_observed_counts`，並經
`_emit_agent_decision` 落 `usage_events.decision_snapshot.agent`。

⛔⛔ **只有列舉的類別名與整數**——`observed` 本身就不攜帶模型文字或來源原文
（見 `output_schema.VerifierVerdict.observed`），這一格沿用同一條紀律。

三案（Plan §6b）：
1. observe 模式的回合：計數與 `verdict.observed` 一致（多次 verdict 要累加）；
2. enforce（`observed` 為空）：計數為空 dict，⛔ 不是 `None`；
3. **變異正對照**：拿掉賦值行 ⇒ 必紅。
"""
from __future__ import annotations

import json
from collections import Counter
from types import SimpleNamespace

import pytest

from services.agent import runtime as runtime_mod
from services.agent.budget import Budget
from services.agent.identity import Identity
from services.agent.output_schema import VerifierVerdict
from services.agent.runtime import AgentRuntime
from services.agent.tools.registry import ToolResult

from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _final_response,
    _tool_call_response,
)

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:R1b"


def _identity() -> Identity:
    return Identity(vendor_id=1, target_user="property_manager", mode="b2b",
                    api_key_id=1, session_id="s-obs")


def _runtime(*, provider, verifier, registry=None, budget=None) -> AgentRuntime:
    return AgentRuntime(
        provider, registry or FakeRegistry(), verifier, FakeAssembler(),
        budget or Budget(), stage="M1", clock=FakeClock(), model="obs-model",
    )


# ---------------------------------------------------------------------------
# 1. observe 模式：計數與 `verdict.observed` 一致
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_observe_mode_counts_match_verdict_observed():
    verdict = VerifierVerdict(ok=True, observed=["UNCITED_ASSERTION", "SCHEMA:ask_target_invalid"])
    runtime = _runtime(
        provider=FakeProvider([_final_response(answer="觀察模式照樣出去的答案")]),
        verifier=FakeVerifier([verdict]),
    )

    result = await runtime.run_turn(_identity(), "這題觀察模式怎麼判", {})

    assert result.kind == "answer"                      # 觀察模式 ⇒ 放行
    assert result.trace.verifier_observed_counts == dict(Counter(verdict.observed))
    assert result.trace.verifier_observed_counts == {
        "UNCITED_ASSERTION": 1, "SCHEMA:ask_target_invalid": 1,
    }


@pytest.mark.req(_REQ)
async def test_counts_accumulate_across_rewrites():
    """一個回合跑好幾次 Verifier（被拒→重寫→再驗）⇒ **逐次累加**，⛔ 不只留最後一次。"""
    runtime = _runtime(
        provider=FakeProvider([
            _final_response(answer="第一次的答案"),
            _final_response(answer="重寫後的答案"),
        ]),
        verifier=FakeVerifier([
            VerifierVerdict(ok=False, reason="UNCITED_ASSERTION", observed=["POLARITY_MISMATCH"]),
            VerifierVerdict(ok=True, observed=["POLARITY_MISMATCH", "QUOTE_TOO_SHORT"]),
        ]),
        budget=Budget(max_rewrites=2),
    )

    result = await runtime.run_turn(_identity(), "有什麼保證", {})

    assert result.kind == "answer"
    assert result.trace.verifier_observed_counts == {
        "POLARITY_MISMATCH": 2, "QUOTE_TOO_SHORT": 1,
    }


# ---------------------------------------------------------------------------
# 2. enforce（`observed` 為空）⇒ 空 dict；其餘出口同樣是空 dict、⛔ 不是 None
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_enforce_mode_counts_are_empty_dict():
    runtime = _runtime(
        provider=FakeProvider([_final_response(answer="一般回答")]),
        verifier=FakeVerifier([VerifierVerdict(ok=True)]),
    )
    result = await runtime.run_turn(_identity(), "一般問題請教一下", {})

    assert result.trace.verifier_observed_counts == {}
    assert result.trace.verifier_observed_counts is not None


@pytest.mark.req(_REQ)
async def test_fixed_sentence_exit_keeps_the_default_empty_dict():
    """固定句出口（`build_fixed`）⛔ 不寫實值——Plan §0b：只有取得 verdict 的一般出口寫。

    正對照：同一個回合真的有被觀察到的類別（下面 `observed` 非空），出口仍是空 dict
    ⇒ 證明這一格不是「剛好沒有東西可記」。
    """
    runtime = _runtime(
        provider=FakeProvider([
            _final_response(answer="第一次"),
            _final_response(answer="第二次"),
        ]),
        verifier=FakeVerifier([
            VerifierVerdict(ok=False, reason="UNCITED_ASSERTION", observed=["POLARITY_MISMATCH"]),
            VerifierVerdict(ok=False, reason="UNCITED_ASSERTION", observed=["POLARITY_MISMATCH"]),
        ]),
        budget=Budget(max_rewrites=2),
    )
    result = await runtime.run_turn(_identity(), "有什麼保證", {})

    assert result.kind == "handoff"
    assert result.handoff["reason"] == "budget_exhausted"
    assert result.trace.verifier_observed_counts == {}
    # 正對照：兩次 verdict 的 observed 都非空（⇒ 上一行不是因為沒東西可記）
    assert [list(v.observed) for v in result.trace.verifier] == [
        ["POLARITY_MISMATCH"], ["POLARITY_MISMATCH"],
    ]


# ---------------------------------------------------------------------------
# 3. 變異正對照：拿掉賦值行必紅
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_assignment_line_removed_is_red():
    """把 `_run_model_loop` 的累加行拿掉 ⇒ 上面三條的判準必須失效。

    ⚠️ 這裡以**原始碼字面**證明賦值行存在且形狀正確（`Counter(verdict.observed)`
    累加、⛔ 不依賴 R2 的 `observed_counts`），再以字串變異證明這條檢查不是恆真。
    """
    import inspect

    src = " ".join(inspect.getsource(runtime_mod.AgentRuntime._run_model_loop).split())

    def _wired(text: str) -> bool:
        return (
            "acc.verifier_observed_counts.update( Counter(acc.verifier_observed_counts) "
            "+ Counter(verdict.observed) )" in text
            and "observed_counts=acc.verifier_observed_counts," in text
        )

    assert _wired(src), "正對照不成立：賦值行或 build_trace 的傳遞不見了"
    assert not _wired(src.replace("Counter(verdict.observed)", "Counter()"))
    assert not _wired(src.replace("observed_counts=acc.verifier_observed_counts,", ""))
    # ⛔ 不得改成讀 R2 才會有的 `verdict.observed_counts`
    assert "verdict.observed_counts" not in src


# ---------------------------------------------------------------------------
# 4. 決策快照：新鍵真的落地，且 ⛔ 不夾帶原文
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_decision_snapshot_carries_the_counts_without_verbatim(monkeypatch):
    captured: list = []
    monkeypatch.setattr(
        runtime_mod.usage_metering, "set_agent_decision", lambda d: captured.append(d)
    )
    runtime = _runtime(
        provider=FakeProvider([_final_response(answer="觀察模式的答案")]),
        verifier=FakeVerifier([VerifierVerdict(ok=True, observed=["SENSITIVE_TOPIC"])]),
    )
    await runtime.run_turn(_identity(), "這題觀察模式怎麼判", {})

    assert captured, "決策快照沒有落地（正對照不成立）"
    snap = captured[0]
    assert snap["verifier_observed_counts"] == {"SENSITIVE_TOPIC": 1}
    blob = json.dumps(snap, ensure_ascii=False, default=str)
    for banned in ("觀察模式的答案", "這題觀察模式怎麼判"):
        assert banned not in blob, f"決策快照夾帶原文：{banned}"
