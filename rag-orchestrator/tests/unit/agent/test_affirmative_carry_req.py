"""unit：T3 肯定語＝授權、空會話註記、文字假確認統計（Plan
`inputs/plan-walkthrough-fixes-batch2-20260909.md` §4｜
knowledge-outline-and-intent-architecture:T3）。

守的五件事：
1. **凍結元組**：`AFFIRMATIVE_WORDS` 逐字等於 Plan §4 那一行；`is_affirmative`
   只做整句等值（去標點空白），⛔ 不做包含比對。
2. **承接時序**：只在「緊鄰上一回合出口寫入之值」＝`confirm_intent` 時觸發；
   select 段、handoff_cache 重播、confirm 兌現段各自的早退（皆寫 `None`）都
   會讓下一句「對」不觸發。
3. **不可引用**：承接段以 `citable=False` 的程式資料段進場，模型引用它
   ⇒ `SOURCE_NOT_CITABLE`；不進 dialog；⛔ 不寫 `PENDING_CONFIRM_KEY`、
   不呼叫任何 `jgb2.action.*`。
4. **空會話註記**：dialog 長度 0 時注入固定句，第二輪起不再注入。
5. **文字假確認統計**：`kind=ask` ∧ `ask_target=confirm_intent` ∧ 本回合沒有
   `confirm.request` 呼叫 ⇒ 記 `prose_confirm_suspect`，⛔ 不改寫。

⛔ 不接真 OpenAI、不接真 DB（沿用 `test_runtime_req.py`／`test_ask_target_req.py`
的假件）。
"""
from __future__ import annotations

import json

import pytest

from services.agent import agent_rules
from services.agent.affirmative import AFFIRMATIVE_WORDS, is_affirmative
from services.agent.budget import Budget
from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import resolve_refs
from services.agent.runtime import (
    CALLER_AFFIRMATIVE_LABEL,
    CALLER_AFFIRMATIVE_PROVENANCE_SOURCE,
    CONTEXT_EMPTY_SESSION_LABEL,
    AFFIRMATIVE_CARRY_TEXT,
    EMPTY_SESSION_TEXT,
    LAST_ASK_TARGET_KEY,
    PENDING_CONFIRM_KEY,
    AgentRuntime,
    Provenance,
    ToolResult,
)
from services.agent.verifier import OutputVerifier, _UNIT_MARKER_RE

from tests.unit.agent.test_ask_target_req import _identity as _target_identity, _model_ask
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _empty_provider,
    _fake_message,
    _fake_response,
    _fake_tool_call,
    _final_response,
)
from tests.unit.agent.test_runtime_req import VerifierVerdict
from tests.unit.agent.test_verifier_req import _RULES_PATH

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:T3"

_FROZEN_TUPLE = (
    "對", "好", "是", "嗯", "可以", "好的", "好啊", "對啊", "對呀",
    "是的", "沒錯", "請", "ok", "OK", "okay",
)


def _runtime(*, provider=None, registry=None, verifier=None, budget=None, assembler=None):
    return AgentRuntime(
        provider if provider is not None else _empty_provider(),
        registry or FakeRegistry(),
        verifier or FakeVerifier(),
        assembler or FakeAssembler(),
        budget or Budget(),
        stage="M1",
        clock=FakeClock(),
    )


def _data_blocks(provider) -> list[str]:
    assert provider.calls, "provider 沒被呼叫——這個測試的前提就不成立"
    return [
        str(m.get("content") or "")
        for m in provider.calls[-1]["messages"]
        if m.get("role") == "user"
    ]


# ---------------------------------------------------------------------------
# 1. 凍結元組與整句等值
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_affirmative_words_is_the_frozen_plan_tuple_verbatim():
    assert AFFIRMATIVE_WORDS == _FROZEN_TUPLE
    assert len(set(AFFIRMATIVE_WORDS)) == len(AFFIRMATIVE_WORDS)


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("message", ["對。", " 好 ", "OK!"])
def test_is_affirmative_true_cases(message):
    assert is_affirmative(message) is True


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("message", ["對 查", "好像", "對，列出來"])
def test_is_affirmative_false_cases_substring_must_not_match(message):
    """正面案例＋反面案例同一份斷言：包含比對一律不算——「對 查」「對，列出來」
    都含肯定字但不是整句等值，⛔ 不得誤判。"""
    assert is_affirmative(message) is False


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("value", [None, 123, [], {}])
def test_is_affirmative_non_string_is_false(value):
    assert is_affirmative(value) is False


# ---------------------------------------------------------------------------
# 2. 承接時序：只在緊鄰上一回合 confirm_intent 時觸發
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_ask_confirm_intent_then_affirmative_fires_positive_control():
    """正對照：ask(confirm_intent) → 「對」⇒ 觸發承接、進資料段。"""
    state: dict = {}
    first_provider = FakeProvider([_model_ask("confirm_intent", answer="要送出這張修繕單嗎？")])
    first = await _runtime(provider=first_provider).run_turn(
        _target_identity(), "我要報修", state
    )
    assert first.ask_target == "confirm_intent"
    assert state["agent"][LAST_ASK_TARGET_KEY] == "confirm_intent"

    second_provider = FakeProvider([_final_response(answer="好的，已送出。")])
    second = await _runtime(provider=second_provider).run_turn(
        _target_identity(), "對", state
    )
    assert "affirmative_carry" in second.trace.violations
    block = next(
        b for b in _data_blocks(second_provider) if CALLER_AFFIRMATIVE_LABEL in b
    )
    assert AFFIRMATIVE_CARRY_TEXT in block


@pytest.mark.req(_REQ)
async def test_ask_non_confirm_intent_then_affirmative_does_not_fire():
    """`last_ask_target` 是 `confirm_intent` 以外的值 ⇒ 不觸發。"""
    state: dict = {}
    first = await _runtime(provider=FakeProvider([_model_ask("address")])).run_turn(
        _target_identity(), "信仰", state
    )
    assert state["agent"][LAST_ASK_TARGET_KEY] == "address"

    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_target_identity(), "對", state)
    assert "affirmative_carry" not in result.trace.violations
    assert all(CALLER_AFFIRMATIVE_LABEL not in b for b in _data_blocks(provider))


@pytest.mark.req(_REQ)
async def test_ask_then_select_turn_then_affirmative_does_not_fire():
    """ask → select 回合（寫 `None`）→「對」不觸發。"""
    state: dict = {}
    await _runtime(provider=FakeProvider([_model_ask("confirm_intent")])).run_turn(
        _target_identity(), "我要報修", state
    )
    assert state["agent"][LAST_ASK_TARGET_KEY] == "confirm_intent"

    select_result = await _runtime(registry=FakeRegistry()).run_turn(
        _target_identity(), "select:bill:900001", state
    )
    assert select_result.trace.select_type == "bill"
    assert state["agent"][LAST_ASK_TARGET_KEY] is None

    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_target_identity(), "對", state)
    assert "affirmative_carry" not in result.trace.violations
    assert all(CALLER_AFFIRMATIVE_LABEL not in b for b in _data_blocks(provider))


@pytest.mark.req(_REQ)
async def test_ask_then_handoff_cache_replay_then_affirmative_does_not_fire():
    """ask(confirm_intent) → 快取重播出口（寫 `None`）→「對」不觸發。"""
    state: dict = {}
    await _runtime(provider=FakeProvider([_model_ask("confirm_intent")])).run_turn(
        _target_identity(), "我要報修", state
    )
    assert state["agent"][LAST_ASK_TARGET_KEY] == "confirm_intent"

    budget = Budget(max_rewrites=0)
    first = await _runtime(
        provider=FakeProvider([_final_response(answer="不確定。")]),
        verifier=FakeVerifier([VerifierVerdict(ok=False, reason="UNCITED_ASSERTION")]),
        budget=budget,
    ).run_turn(_target_identity(), "這題會轉人嗎？", state)
    assert first.kind == "handoff"

    # 人為把載體塞回 confirm_intent，證明重播出口真的會把它清掉
    state["agent"][LAST_ASK_TARGET_KEY] = "confirm_intent"
    replay = await _runtime(budget=budget).run_turn(
        _target_identity(), "這題會轉人嗎？", state
    )
    assert replay.trace.llm_calls == 0
    assert state["agent"][LAST_ASK_TARGET_KEY] is None

    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_target_identity(), "對", state)
    assert "affirmative_carry" not in result.trace.violations
    assert all(CALLER_AFFIRMATIVE_LABEL not in b for b in _data_blocks(provider))


@pytest.mark.req(_REQ)
async def test_confirm_redeem_turn_then_affirmative_does_not_fire():
    """ask(confirm_intent) → confirm 兌現段早退（寫 `None`）→「對」不觸發。"""
    from services.agent.tools.confirm import pending_id_for

    state: dict = {}
    await _runtime(provider=FakeProvider([_model_ask("confirm_intent")])).run_turn(
        _target_identity(), "我要報修", state
    )
    assert state["agent"][LAST_ASK_TARGET_KEY] == "confirm_intent"
    state["agent"][PENDING_CONFIRM_KEY] = {}

    pid = pending_id_for("tok-not-in-state-0123456789")
    confirm_result = await _runtime().run_turn(
        _target_identity(), f"confirm_submit:{pid}", state
    )
    assert confirm_result.kind == "answer"
    assert state["agent"][LAST_ASK_TARGET_KEY] is None

    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_target_identity(), "對", state)
    assert "affirmative_carry" not in result.trace.violations
    assert all(CALLER_AFFIRMATIVE_LABEL not in b for b in _data_blocks(provider))


@pytest.mark.req(_REQ)
async def test_confirm_and_replay_turns_leave_last_ask_target_none():
    """收斂斷言：確認兌現回合後與重播回合後 `agent_state[LAST_ASK_TARGET_KEY]`
    皆為 `None`（前兩個情境測試已各自驗過，這裡把兩個結論放同一條測試裡收斂）。"""
    from services.agent.tools.confirm import pending_id_for

    state: dict = {"agent": {LAST_ASK_TARGET_KEY: "confirm_intent", PENDING_CONFIRM_KEY: {}}}
    pid = pending_id_for("tok-not-in-state-0123456789")
    confirm_result = await _runtime().run_turn(
        _target_identity(), f"confirm_submit:{pid}", state
    )
    assert confirm_result.kind == "answer"
    assert state["agent"][LAST_ASK_TARGET_KEY] is None


# ---------------------------------------------------------------------------
# 3. 不可引用；不進 dialog；不寫 PENDING_CONFIRM_KEY／不呼叫工具
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_affirmative_segment_not_in_dialog():
    state: dict = {}
    await _runtime(provider=FakeProvider([_model_ask("confirm_intent")])).run_turn(
        _target_identity(), "我要報修", state
    )
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_target_identity(), "對", state)
    dialog_text = json.dumps(state["agent"].get("dialog", []), ensure_ascii=False)
    assert AFFIRMATIVE_CARRY_TEXT not in dialog_text
    assert "對" in dialog_text  # 正對照：dialog 真的有寫東西


@pytest.mark.req(_REQ)
async def test_affirmative_carry_never_writes_pending_confirm_or_calls_tools():
    state: dict = {}
    await _runtime(provider=FakeProvider([_model_ask("confirm_intent")])).run_turn(
        _target_identity(), "我要報修", state
    )
    registry = FakeRegistry()
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider, registry=registry).run_turn(
        _target_identity(), "對", state
    )
    assert state["agent"].get(PENDING_CONFIRM_KEY) in (None, {})
    assert registry.call_args == []  # 沒有工具呼叫（模型腳本本身就沒送 tool_calls）


@pytest.mark.req(_REQ)
async def test_model_citing_the_affirmative_segment_gets_source_not_citable():
    """尺自證：先跑一輪拿真標記，再用真 Verifier 驗一個引用它的輸出。"""
    state: dict = {}
    await _runtime(provider=FakeProvider([_model_ask("confirm_intent")])).run_turn(
        _target_identity(), "我要報修", state
    )
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_target_identity(), "對", state)

    block = next(b for b in _data_blocks(provider) if CALLER_AFFIRMATIVE_LABEL in b)
    marker = None
    for line in block.split("\n"):
        m = _UNIT_MARKER_RE.search(line)
        if m is not None:
            marker = m.group(0)
            break
    assert marker is not None, "資料段裡沒有承接句的行首標記"
    nonce, tool_call_id = marker.strip("[]").split(":")[0:2]

    aff_result = ToolResult(
        ok=True,
        data={},
        provenance=[
            Provenance(
                source=CALLER_AFFIRMATIVE_PROVENANCE_SOURCE,
                text=AFFIRMATIVE_CARRY_TEXT,
                citable=False,
            )
        ],
        text_for_model="",
    )
    out = AgentOutput.model_validate(
        {
            "kind": "answer",
            "sentences": [
                {"text": AFFIRMATIVE_CARRY_TEXT, "kind": "fact", "refs": [marker]}
            ],
            "fact_class": "feature",
            "handoff_reason": None,
        }
    )
    tool_results = {tool_call_id: aff_result}
    resolved, resolve_errors = resolve_refs(out, tool_results, nonce)
    assert resolve_errors == {}
    assert resolved[(0, 0)].citable is False

    verdict = OutputVerifier(VerifierRules.load(_RULES_PATH)).verify(
        out, tool_results, "對", None,
        resolved=resolved, resolve_errors=resolve_errors,
    )
    assert verdict.ok is False
    assert verdict.reason == "SOURCE_NOT_CITABLE"


@pytest.mark.req(_REQ)
async def test_reserved_id_collision_for_affirmative_and_context_ids():
    """`aff-{nonce[:8]}`／`ctx-{nonce[:8]}` 同樣是保留字——模型送同名
    tool_call 一律拒收（本回合沒有肯定語承接也沒有空會話以外的條件成立時
    照樣拒收，理由同 entry-…：id 不該取決於這回合是否真的用到它）。"""
    assembler = FakeAssembler()

    def _collision_step(prefix):
        def step(kwargs):
            assert assembler.calls, "assembler 還沒被呼叫——撈不到本回合 nonce"
            nonce = assembler.calls[0]["nonce"]
            call_id = f"{prefix}-{nonce[:8]}"
            return _fake_response(
                _fake_message(
                    tool_calls=[_fake_tool_call("kb.get", {"kb_id": "1"}, call_id)]
                )
            )
        return step

    for prefix in ("aff", "ctx"):
        assembler = FakeAssembler()
        provider = FakeProvider([_collision_step(prefix), _final_response(answer="好的。")])
        result = await _runtime(provider=provider, assembler=assembler).run_turn(
            _target_identity(), "一般問題", {}
        )
        assert "tool_call_id_collides_with_reserved" in result.trace.violations


# ---------------------------------------------------------------------------
# 4. 空會話註記
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_empty_session_segment_present_on_first_turn():
    provider = FakeProvider([_final_response(answer="這段剛開始，還沒有先前訊息。")])
    state: dict = {}
    result = await _runtime(provider=provider).run_turn(
        _target_identity(), "我剛剛問了什麼？", state
    )
    block = next(b for b in _data_blocks(provider) if CONTEXT_EMPTY_SESSION_LABEL in b)
    assert EMPTY_SESSION_TEXT in block
    assert result.kind == "answer"


@pytest.mark.req(_REQ)
async def test_empty_session_segment_absent_on_later_turns():
    state: dict = {}
    await _runtime(provider=FakeProvider([_final_response(answer="好的。")])).run_turn(
        _target_identity(), "第一句", state
    )
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_target_identity(), "第二句", state)
    assert all(CONTEXT_EMPTY_SESSION_LABEL not in b for b in _data_blocks(provider))


# ---------------------------------------------------------------------------
# 5. 文字假確認統計（只統計，⛔ 不改寫）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_prose_confirm_suspect_recorded_when_conditions_hold():
    """`kind=ask` ∧ `ask_target=confirm_intent` ∧ 本回合沒有 `confirm.request`
    呼叫 ⇒ 記 `prose_confirm_suspect`；答句逐字不變（⛔ 不改寫）。"""
    answer_text = "要送出這張修繕單嗎？請確認是否送出。"
    provider = FakeProvider([_model_ask("confirm_intent", answer=answer_text)])
    result = await _runtime(provider=provider).run_turn(
        _target_identity(), "我要報修", {}
    )
    assert result.kind == "ask"
    assert "prose_confirm_suspect" in result.trace.violations
    assert result.answer == answer_text


@pytest.mark.req(_REQ)
async def test_prose_confirm_suspect_not_recorded_for_other_ask_targets():
    """正對照：`ask_target` 不是 `confirm_intent` ⇒ 不記——證明上面那條不是恆真。"""
    provider = FakeProvider([_model_ask("address")])
    result = await _runtime(provider=provider).run_turn(_target_identity(), "信仰", {})
    assert result.kind == "ask"
    assert "prose_confirm_suspect" not in result.trace.violations


@pytest.mark.req(_REQ)
async def test_prose_confirm_suspect_not_recorded_when_confirm_request_was_called():
    """反對照：`confirm.request` **成功**會立刻結束回合（走
    `_begin_pending_confirm`），根本到不了 `kind=ask` 這條判定；但**失敗**的
    `confirm.request`（data 形狀不符）不會結束回合，回合會繼續、
    `tool_call_records` 裡留下這一筆——這裡驗的正是這一格：即使最終輸出仍是
    `kind=ask/confirm_intent`，只要本回合的 `tool_call_records` 裡有一筆
    `confirm.request`，就 ⛔ 不記 `prose_confirm_suspect`（沿用
    `test_runtime_confirm_segment_req.test_malformed_confirm_data_does_not_end_the_turn`
    的「data 形狀不符 ⇒ 回合照常走完」構造）。"""
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"pending_id": "p1"})])
    provider = FakeProvider(
        [
            _fake_response(
                _fake_message(
                    tool_calls=[
                        _fake_tool_call(
                            "confirm.request",
                            {"summary": "摘要", "payload": "{}"},
                            "c1",
                        )
                    ]
                )
            ),
            _model_ask("confirm_intent", answer="要送出嗎？"),
        ]
    )
    result = await _runtime(provider=provider, registry=registry).run_turn(
        _target_identity(), "幫我延 3 天", {}
    )
    assert "confirm_request_data_shape_invalid" in result.trace.violations
    assert result.kind == "ask"
    assert result.ask_target == "confirm_intent"
    assert "prose_confirm_suspect" not in result.trace.violations


# ---------------------------------------------------------------------------
# 6. 政策文：三句定義只在 `_POLICY_TEXT_NON_PROSPECT`，不含例子標記
# ---------------------------------------------------------------------------
_EXAMPLE_MARKERS = ("（如", "(如", "例如", "例：", "像是")


@pytest.mark.req(_REQ)
def test_policy_sentences_present_only_in_non_prospect_and_no_example_markers():
    sentences = (
        "查詢不需要確認，直接查；確認只用在寫入。",
        "使用者以肯定語回應上一句追問，視為授權執行上一句提議的事，⛔ 不再確認一次。",
        "寫入的確認只透過確認卡；⛔ 不以文字詢問是否送出。",
    )
    for sentence in sentences:
        assert sentence in agent_rules._POLICY_TEXT_NON_PROSPECT
        assert sentence not in agent_rules._POLICY_TEXT
        for marker in _EXAMPLE_MARKERS:
            assert marker not in sentence
