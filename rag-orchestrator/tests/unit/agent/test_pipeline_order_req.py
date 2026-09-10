"""unit：四道出口閘的**順序表**與回合收尾（Plan R R1｜§1.2、§0c 驗收）。

被測的三件事：

1. **恰好命中一道**——對四道閘各給一個最小 `TurnResult` 形狀，逐閘**單獨**跑一次，
   斷言只有預期的那一道會改動結果，其餘三道逐欄不動。
   ⚠️ 「有沒有改動」是**比對前後快照**算出來的，⛔ 不是由測試自己宣告哪一道該動。
2. **同回合先後**——`scope_exit` 觸發後其餘三道皆為 no-op；
   `_apply_handoff_data_exits` 的 NO_JUDGEMENT 分支設了 `ask_target=confirm_intent`
   之後，`_apply_ask_target_gate` ⛔ 不得動它。
3. **§0c 驗收**——模型迴圈各加一筆計數與 violation 後走固定句出口，
   `trace.llm_calls`／`violations` 反映**最新值**（容器欄位就地加的直接後果；
   舊寫法重新綁定區域變數時這條只是巧合）。

⛔ 本檔 ⛔ 不驗任何一道閘自己的判定真值表——那些在
`test_select_scope_req.py`／`test_handoff_without_lookup_req.py`／
`test_ask_target_req.py`／`test_handoff_data_exits_req.py` 各自有整份。
"""
from __future__ import annotations

import pytest

from services.agent import exit_gates
from services.agent.exit_gates import (
    ASK_TARGET_TEXT,
    NO_JUDGEMENT_TEXT,
    SCOPE_EXIT_TEXT,
    _apply_ask_target_gate,
    _apply_handoff_data_exits,
    finalize,
)
from services.agent.turn_context import (
    LAST_ASK_TARGET_KEY,
    ToolCallRecord,
    TurnAccumulator,
    TurnResult,
    TurnTrace,
)
from services.presales_gate import FactClass

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:R1"

_GATE_ORDER = ("scope_exit", "handoff_without_lookup", "ask_target_gate", "handoff_data_exits")


# ---------------------------------------------------------------------------
# 素材
# ---------------------------------------------------------------------------
def _tool_call(*, empty: bool = False, status: str = "ok") -> ToolCallRecord:
    return ToolCallRecord(
        id="call-1", name="jgb2.query.bills", args_summary={},
        ms=1, status=status, n_items=0 if empty else 2, empty=empty,
    )


def _result(
    *, kind: str = "answer", answer: str = "原本的答案",
    handoff_reason: str | None = None, fact_class: str = FactClass.feature.value,
    tool_calls: list | None = None, ask_target: str | None = None,
) -> TurnResult:
    trace = TurnTrace(
        trace_id="t-order",
        tool_calls=list(tool_calls or []),
        final_kind=kind,
        handoff_reason=handoff_reason,
    )
    handoff = None
    if kind == "handoff":
        handoff = {
            "reason": handoff_reason, "fact_class": fact_class,
            "channel": "line", "message": "已為你轉真人客服，請稍候。",
        }
        answer = handoff["message"]
    return TurnResult(
        kind=kind, answer=answer, handoff=handoff, quick_replies=[],
        trace=trace, ask_target=ask_target,
    )


def _snapshot(result: TurnResult) -> tuple:
    """逐欄快照——「這道閘有沒有動到東西」的**唯一判定**。"""
    return (
        result.kind, result.answer, repr(result.handoff), result.ask_target,
        repr(result.outcome), result.trace.final_kind, result.trace.handoff_reason,
        tuple(result.trace.violations),
    )


def _which_gates_fire(make_result, *, agent_state=None, user_message="", scope_counts=None) -> list:
    """逐閘**單獨**跑一次（每次都用一份新的 `TurnResult`），回實際動到東西的那幾道。"""
    fired = []
    for name, gate in exit_gates.EXIT_GATES:
        result = make_result()
        before = _snapshot(result)
        after = gate(
            result, dict(agent_state or {}), user_message, None,
            dict(scope_counts or {"in": 0, "out": 0}),
        )
        if _snapshot(after) != before:
            fired.append(name)
    return fired


# ---------------------------------------------------------------------------
# 0. 順序表本身
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_exit_gates_order_is_frozen():
    """`EXIT_GATES` 是四道閘順序的**唯一來源**；順序即契約，⛔ 不得重排。"""
    assert tuple(name for name, _ in exit_gates.EXIT_GATES) == _GATE_ORDER
    assert len(exit_gates.EXIT_GATES) == 4


# ---------------------------------------------------------------------------
# 1. 恰好命中一道
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_scope_exit_only():
    fired = _which_gates_fire(
        lambda: _result(), scope_counts={"in": 0, "out": 1},
    )
    assert fired == ["scope_exit"], fired


@pytest.mark.req(_REQ)
def test_handoff_without_lookup_only():
    """零查詢的 `no_grounding` 轉人（`tool_calls` 為空）⇒ 只有第二道動。"""
    fired = _which_gates_fire(
        lambda: _result(kind="handoff", handoff_reason="no_grounding"),
        user_message="幫我看一下這件事",
    )
    assert fired == ["handoff_without_lookup"], fired


@pytest.mark.req(_REQ)
def test_ask_target_gate_only():
    """`kind=ask` 且追問對象值域外 ⇒ 只有第三道動。"""
    fired = _which_gates_fire(lambda: _result(kind="ask", ask_target=None))
    assert fired == ["ask_target_gate"], fired


@pytest.mark.req(_REQ)
def test_handoff_data_exits_only():
    """有資料的 `no_grounding` 轉人 ⇒ 只有第四道動（第二道要求零查詢）。"""
    fired = _which_gates_fire(
        lambda: _result(kind="handoff", handoff_reason="no_grounding",
                        tool_calls=[_tool_call(empty=False)]),
        user_message="你覺得我該不該催他",
    )
    assert fired == ["handoff_data_exits"], fired


@pytest.mark.req(_REQ)
def test_nothing_fires_on_a_plain_answer():
    """正對照：一般回答 ⇒ 四道全不動（否則上面四條的「恰好一道」沒有意義）。"""
    assert _which_gates_fire(lambda: _result()) == []


# ---------------------------------------------------------------------------
# 2. 同回合先後
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_scope_exit_makes_the_other_three_no_ops():
    """①觸發後，②③④ 逐欄不動——範圍外的回合已經是固定句，⛔ 不該再被降級一次。"""
    result = _result(kind="handoff", handoff_reason="no_grounding")
    agent_state: dict = {}
    scope_counts = {"in": 0, "out": 1}

    ran = []
    for name, gate in exit_gates.EXIT_GATES:
        before = _snapshot(result)
        result = gate(result, agent_state, "幫我看一下這件事", None, scope_counts)
        if _snapshot(result) != before:
            ran.append(name)

    assert ran == ["scope_exit"], ran
    assert result.answer == SCOPE_EXIT_TEXT
    assert result.kind == "answer"
    assert "handoff_without_lookup" not in result.trace.violations
    assert "handoff_no_judgement" not in result.trace.violations
    assert "ask_target_invalid" not in result.trace.violations


@pytest.mark.req(_REQ)
def test_ask_target_gate_leaves_no_judgement_confirm_intent_alone():
    """NO_JUDGEMENT 設 `ask_target=confirm_intent` 之後，③ ⛔ 不得動它。

    ⚠️ 這正是 ③ 排在 ④ **之前**的理由：④ 會把 `kind` 從 `handoff` 換成 `answer`
    並另設一個合法的 `ask_target`；③ 只認 `kind=="ask"`，所以就算之後再跑一次
    也碰不到它——這條就是在釘那個「碰不到」。
    """
    result = _apply_handoff_data_exits(
        _result(kind="handoff", handoff_reason="no_grounding",
                tool_calls=[_tool_call(empty=False)]),
        "你覺得我該不該催他", None,
    )
    assert result.answer == NO_JUDGEMENT_TEXT
    assert result.ask_target == "confirm_intent"

    before = _snapshot(result)
    after = _apply_ask_target_gate(result)
    assert _snapshot(after) == before
    assert after.ask_target == "confirm_intent"
    assert after.answer != ASK_TARGET_TEXT


# ---------------------------------------------------------------------------
# 3. §0c 驗收：固定句出口反映**最新**的計數與 violations
# ---------------------------------------------------------------------------
class _FakeClock:
    def __init__(self, now: float = 0.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.mark.req(_REQ)
def test_fixed_exit_reflects_latest_counters_and_violations():
    """模型迴圈各加一筆計數與 violation 後走固定句出口 ⇒ trace 反映最新值。

    ⚠️ 這是 §0c「整數計數在迴圈中**改為對容器欄位就地加**」的直接驗收：舊寫法
    重新綁定區域變數時，這條成立只是因為閉包剛好抓得到同一個 cell；改成容器之後
    它是**定義**。
    """
    acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t-acc", start=0.0)
    clock = _FakeClock(0.0)

    # 模型迴圈跑了兩輪、記了兩筆 violation、吃了 token
    acc.llm_calls += 1
    acc.llm_calls += 1
    acc.prompt_tokens += 10
    acc.completion_tokens += 5
    acc.violations.append("FORBIDDEN:kb.get")
    acc.violations.append("affirmative_carry")
    acc.tool_call_records.append(_tool_call())

    clock.now = 1.25
    result = acc.build_fixed("budget_exhausted", clock=clock)

    assert result.trace.llm_calls == 2
    assert result.trace.prompt_tokens == 10
    assert result.trace.completion_tokens == 5
    assert result.trace.violations == ["FORBIDDEN:kb.get", "affirmative_carry"]
    assert len(result.trace.tool_calls) == 1
    assert result.trace.latency_ms == 1250
    assert result.handoff["reason"] == "budget_exhausted"


@pytest.mark.req(_REQ)
def test_fixed_exit_trace_lists_are_copies_but_general_exit_shares():
    """固定句出口傳**副本**、一般出口傳**同一個物件**——⛔ 兩者不得統一。

    一般出口共用同一個 list 是 `_emit_agent_decision` 形狀守門的前提：它會就地改
    `trace.candidate_ids`／追一筆 `trace.violations`，而那個修正必須反映到呼叫端
    讀到的 `result.trace` 上。
    """
    acc = TurnAccumulator(cache_key="k", nonce="0" * 16, trace_id="t", start=0.0)
    acc.violations.append("one")

    fixed = acc.build_fixed("budget_exhausted", clock=_FakeClock())
    assert fixed.trace.violations is not acc.violations
    assert fixed.trace.violations == ["one"]

    general = acc.build_trace(
        final_kind="answer", handoff_reason=None, clock=_FakeClock(), copy_lists=False,
    )
    assert general.violations is acc.violations


# ---------------------------------------------------------------------------
# 4. `finalize` 的三個狀態寫點
# ---------------------------------------------------------------------------
class _FakeVerifier:
    rules = None


@pytest.mark.req(_REQ)
def test_finalize_writes_the_three_state_points():
    """`LAST_ASK_TARGET_KEY`／`handoff_cache`／`fixed_streak` 三個寫點都在 `finalize`。"""
    acc = TurnAccumulator(cache_key="ck", nonce="0" * 16, trace_id="t-fin", start=0.0)
    agent_state: dict = {"fixed_streak": 3}
    cache: dict = {}

    out = finalize(
        acc, _result(kind="ask", answer="要處理哪一件事？", ask_target="confirm_intent"),
        is_fixed=False, verifier=_FakeVerifier(), cache=cache,
        agent_state=agent_state, user_message="嗨",
    )

    assert agent_state[LAST_ASK_TARGET_KEY] == "confirm_intent"
    assert agent_state["fixed_streak"] == 0          # 非固定句 ⇒ 歸零
    assert cache == {}                                # 非 handoff ⇒ ⛔ 不進快取
    assert agent_state["dialog"][-2:] == [
        {"role": "user", "content": "嗨"},
        {"role": "assistant", "content": "要處理哪一件事？"},
    ]
    assert out.outcome == {"state": "clarifying", "expects": "text",
                           "action": None, "ref": None}


@pytest.mark.req(_REQ)
def test_finalize_caches_handoff_and_counts_fixed_streak():
    """轉人收場 ⇒ 進 `handoff_cache`（鍵＝`acc.cache_key`）＋ `fixed_streak` 累加。"""
    acc = TurnAccumulator(cache_key="ck", nonce="0" * 16, trace_id="t-fin2", start=0.0)
    agent_state: dict = {"fixed_streak": 2}
    cache: dict = {}

    out = finalize(
        acc, _result(kind="handoff", handoff_reason="sensitive_no_grounding",
                     fact_class=FactClass.pricing.value),
        is_fixed=True, verifier=_FakeVerifier(), cache=cache,
        agent_state=agent_state, user_message="你們抽成幾成",
    )

    assert out.kind == "handoff"                      # 敏感類 ⇒ 四道閘都不動
    assert set(cache) == {"ck"}
    # 快取存的是 **result.trace** 的 trace_id（`_result()` 素材固定 `t-order`），
    # ⛔ 不是 `acc.trace_id`——重播出口靠它回填 `replayed_from:`。
    assert cache["ck"]["trace_id"] == "t-order"
    assert agent_state["fixed_streak"] == 3
    assert agent_state[LAST_ASK_TARGET_KEY] is None
