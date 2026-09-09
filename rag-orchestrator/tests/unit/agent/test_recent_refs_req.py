"""unit：V2 有前文的零查詢（Plan
`inputs/plan-walkthrough-fixes-batch4-20260909.md` §3）＋
§5 畫面提示前綴／空會話措辭。

守四件事：
1. **抽編號**（`_recent_ref_ids`／`_recent_ref_ids_from_text`）：重用
   `_PRE_LOOKUP_ID_RE` 整詞比對（⛔ 不另開一條 id 判定正則）、去重保留最近
   序、上限 5；日期／金額同落 4–9 位數字值域，設計上照單全收。
2. **注入紀律**：釘住範圍（`SELECT_SCOPE_KEY` 非 `None`）不注入；非空時以
   `citable=False` 資料段注入，`ref-{nonce[:8]}` 無條件進 `reserved_ids`；
   ⛔ 不進 dialog；trace／決策快照只記 `has_recent_refs: bool`。
3. **迴圈內改寫**：零查詢轉人＋有 recent refs 命中 ⇒ 消耗一次
   `max_rewrites`、重回模型；預算已耗盡 ⇒ 不消耗、照舊落
   `_apply_handoff_without_lookup` 的 `ASK_TARGET_TEXT`（⛔ 不是
   `NO_JUDGEMENT_TEXT` 那條固定句）。
4. §5：`context` 資料段的常數前綴（先 sanitize 再加）；`EMPTY_SESSION_TEXT`
   新措辭。

⛔ 不接真 OpenAI、不接真 DB。
"""
from __future__ import annotations

import json

import pytest

from services.agent.budget import Budget
from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import resolve_refs
from services.agent.runtime import (
    ASK_TARGET_TEXT,
    CALLER_CONTEXT_LABEL,
    CALLER_CONTEXT_PREFIX,
    CALLER_CONTEXT_PROVENANCE_SOURCE,
    EMPTY_SESSION_TEXT,
    NO_JUDGEMENT_TEXT,
    RECENT_REFS_LABEL,
    RECENT_REFS_PROVENANCE_SOURCE,
    RECENT_REFS_REWRITE_HINT,
    SELECT_SCOPE_KEY,
    AgentRuntime,
    Provenance,
    _recent_ref_ids,
    _recent_ref_ids_from_text,
)
from services.agent.tools.registry import ToolResult
from services.agent.verifier import OutputVerifier, _UNIT_MARKER_RE

from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    VerifierVerdict,
    _fake_message,
    _fake_response,
    _fake_tool_call,
    _final_response,
    _identity,
    _tool_call_response,
)
from tests.unit.agent.test_verifier_req import _RULES_PATH

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:V2"


def _runtime(*, provider=None, registry=None, verifier=None, budget=None, assembler=None):
    return AgentRuntime(
        provider if provider is not None else FakeProvider([_final_response(answer="好的。")]),
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
        for m in provider.calls[0]["messages"]
        if m.get("role") == "user"
    ]


def _recent_refs_block(provider) -> str:
    for content in _data_blocks(provider):
        if RECENT_REFS_LABEL in content:
            return content
    raise AssertionError("資料段裡沒有 recent_refs 段")


def _handoff_no_grounding_response(fact_class="feature"):
    payload = {
        "kind": "handoff",
        "sentences": [],
        "fact_class": fact_class,
        "handoff_reason": "no_grounding",
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _dialog_state(*contents: str) -> dict:
    dialog = []
    for i, text in enumerate(contents):
        role = "user" if i % 2 == 0 else "assistant"
        dialog.append({"role": role, "content": text})
    return {"agent": {"dialog": dialog}}


# ---------------------------------------------------------------------------
# 1. 抽編號：重用既有正則、去重保留最近序、上限 5、日期金額照單全收
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_from_text_matches_whole_token_ids_only():
    text = "帳單 756248 逾期了，另外 12 元罰款、abc123456 不算，聯絡 0912345678。"
    # 「12」只有 2 位（不足 4 位）不算；「abc123456」不是整詞純數字不算；
    # 「0912345678」10 位超過 9 位值域不算；「756248」6 位整詞純數字才算。
    assert _recent_ref_ids_from_text(text) == ["756248"]


@pytest.mark.req(_REQ)
def test_from_text_non_string_or_empty_returns_empty_list():
    assert _recent_ref_ids_from_text(None) == []
    assert _recent_ref_ids_from_text("") == []
    assert _recent_ref_ids_from_text(123) == []


@pytest.mark.req(_REQ)
def test_dates_and_amounts_are_included_by_design_positive_control():
    """8 位日期／金額同落 4–9 位數字值域，設計上刻意照單全收
    （不是漏判，正對照：本來就該出現在結果裡）。"""
    assert _recent_ref_ids_from_text("到期日 20260901，滯納金 12345") == ["20260901", "12345"]


@pytest.mark.req(_REQ)
def test_dedupe_preserves_recency_and_caps_at_five():
    agent_state = {"completed_actions": [{"ref_type": "bill", "ref_id": "111111"}]}
    dialog = [
        {"role": "user", "content": "111111"},
        {"role": "assistant", "content": "222222"},
        {"role": "user", "content": "333333"},
        {"role": "assistant", "content": "444444"},
        {"role": "user", "content": "555555"},
        {"role": "assistant", "content": "666666"},
        {"role": "user", "content": "777777"},  # 超過視窗 6 則，最舊的這則不算
    ]
    ids = _recent_ref_ids(agent_state, dialog)
    # 視窗只看最近 6 則（222222…777777 之後 6 則，即扣掉最舊的 111111 那則）；
    # 由近到遠去重、上限 5；completed_actions 的 111111 排在最後補（但已被
    # dialog 裡的重複值去重，仍在集合裡只是位置在尾巴——這裡 dialog 視窗已
    # 排除第一則 111111，completed_actions 補回它）。
    assert len(ids) == 5
    assert ids[0] == "777777"  # 最新
    assert ids == ["777777", "666666", "555555", "444444", "333333"]


@pytest.mark.req(_REQ)
def test_completed_actions_ref_id_included_when_not_in_dialog():
    agent_state = {"completed_actions": [{"ref_type": "bill", "ref_id": "999999"}]}
    dialog = [{"role": "user", "content": "沒有提到編號"}]
    assert _recent_ref_ids(agent_state, dialog) == ["999999"]


@pytest.mark.req(_REQ)
def test_no_ids_anywhere_returns_empty_list():
    assert _recent_ref_ids({}, []) == []
    assert _recent_ref_ids({"completed_actions": []}, [{"role": "user", "content": "你好"}]) == []


# ---------------------------------------------------------------------------
# 2. 注入紀律：釘住範圍不注入、非空才注入、trace 只記 bool、不進 dialog
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_no_segment_when_scope_pinned():
    state = _dialog_state("756248 這張單", "已為你查詢。")
    state["agent"][SELECT_SCOPE_KEY] = {"type": "bill", "estate_id": "e1"}
    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_identity(), "還有嗎", state)
    assert all(RECENT_REFS_LABEL not in b for b in _data_blocks(provider))
    assert result.trace.has_recent_refs is False


@pytest.mark.req(_REQ)
async def test_segment_injected_when_ids_present_and_scope_not_pinned():
    state = _dialog_state("756248 這張單怎麼樣", "已為你查詢，到期日已延。")
    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_identity(), "還有嗎", state)
    block = _recent_refs_block(provider)
    assert "756248" in block
    assert result.trace.has_recent_refs is True


@pytest.mark.req(_REQ)
async def test_no_segment_when_no_recent_ids():
    state: dict = {}
    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_identity(), "一般問題", state)
    assert all(RECENT_REFS_LABEL not in b for b in _data_blocks(provider))
    assert result.trace.has_recent_refs is False


@pytest.mark.req(_REQ)
async def test_recent_refs_text_not_written_into_dialog():
    state = _dialog_state("756248 這張單", "已為你查詢。")
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_identity(), "還有嗎", state)
    dialog_text = json.dumps(state["agent"].get("dialog", []), ensure_ascii=False)
    assert RECENT_REFS_LABEL not in dialog_text
    assert "本對話最近出現的數字編號" not in dialog_text


@pytest.mark.req(_REQ)
async def test_trace_and_violations_never_carry_the_raw_id():
    state = _dialog_state("756248 這張單", "已為你查詢。")
    provider = FakeProvider([_final_response(answer="好的。")])
    result = await _runtime(provider=provider).run_turn(_identity(), "還有嗎", state)
    assert result.trace.has_recent_refs is True
    assert "756248" not in json.dumps(result.trace.violations, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 3. 保留 id：`ref-{nonce[:8]}` 撞名拒收（每回合無條件保留，即使沒有注入）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
@pytest.mark.parametrize("has_refs", [False, True])
async def test_reserved_id_collision_every_turn(has_refs):
    def _collision_step(assembler):
        def step(kwargs):
            assert assembler.calls, "assembler 還沒被呼叫——撈不到本回合 nonce"
            nonce = assembler.calls[0]["nonce"]
            call_id = f"ref-{nonce[:8]}"
            return _fake_response(
                _fake_message(
                    tool_calls=[_fake_tool_call("kb.get", {"kb_id": "1"}, call_id)]
                )
            )
        return step

    assembler = FakeAssembler()
    state = _dialog_state("756248 這張單", "已為你查詢。") if has_refs else {}
    provider = FakeProvider([_collision_step(assembler), _final_response(answer="好的。")])
    result = await _runtime(provider=provider, assembler=assembler).run_turn(
        _identity(), "一般問題", state
    )
    assert "tool_call_id_collides_with_reserved" in result.trace.violations


# ---------------------------------------------------------------------------
# 4. 不可引用：模型引用 recent_refs 段 ⇒ SOURCE_NOT_CITABLE
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_model_citing_recent_refs_gets_source_not_citable():
    state = _dialog_state("756248 這張單", "已為你查詢。")
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_identity(), "還有嗎", state)

    block = _recent_refs_block(provider)
    line = next(
        ln for ln in block.split("\n") if _UNIT_MARKER_RE.search(ln) is not None
    )
    marker = _UNIT_MARKER_RE.search(line).group(0)
    nonce, tool_call_id = marker.strip("[]").split(":")[0:2]

    text = "本對話最近出現的數字編號（可能含日期或金額）：756248"
    ref_result = ToolResult(
        ok=True,
        data={},
        provenance=[
            Provenance(source=RECENT_REFS_PROVENANCE_SOURCE, text=text, citable=False)
        ],
        text_for_model="",
    )
    out = AgentOutput.model_validate(
        {
            "kind": "answer",
            "sentences": [{"text": text, "kind": "fact", "refs": [marker]}],
            "fact_class": "feature",
            "handoff_reason": None,
        }
    )
    tool_results = {tool_call_id: ref_result}
    resolved, resolve_errors = resolve_refs(out, tool_results, nonce)
    assert resolve_errors == {}
    assert resolved[(0, 0)].citable is False

    verdict = OutputVerifier(VerifierRules.load(_RULES_PATH)).verify(
        out, tool_results, "還有嗎", None,
        resolved=resolved, resolve_errors=resolve_errors,
    )
    assert verdict.ok is False
    assert verdict.reason == "SOURCE_NOT_CITABLE"


# ---------------------------------------------------------------------------
# 5. 迴圈內改寫：命中消耗一次、預算耗盡落 ASK_TARGET_TEXT（⛔ 不是轉人固定句）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_rewrite_consumes_one_and_reenters_verifier():
    state = _dialog_state("756248 這張單怎麼樣", "已為你查詢，到期日已延。")
    provider = FakeProvider(
        [
            _handoff_no_grounding_response(),
            _final_response(answer="依資料段，756248 已延期。"),
        ]
    )
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    budget = Budget(max_rewrites=1)
    runtime = _runtime(provider=provider, verifier=verifier, budget=budget)

    result = await runtime.run_turn(_identity(), "那我要不要打電話給他", state)

    assert result.kind == "answer"
    assert result.answer == "依資料段，756248 已延期。"
    assert len(verifier.calls) == 1  # 原始 no_grounding 那次沒進 Verifier
    assert len(provider.calls) == 2  # 零查詢：沒有工具呼叫，只有兩次「最終輸出」嘗試
    sent_contents = [
        m["content"] for call in provider.calls for m in call["messages"]
        if m.get("role") == "user"
    ]
    assert any(RECENT_REFS_REWRITE_HINT in (c or "") for c in sent_contents)


@pytest.mark.req(_REQ)
async def test_budget_exhausted_skips_rewrite_falls_to_ask_target_text():
    """預算已耗盡 ⇒ ⛔ 不消耗（`counters.rewrite_exhausted` 那條坑）、⛔ 不落
    `NO_JUDGEMENT_TEXT`——照常往下走進 Verifier、最終落
    `_apply_handoff_without_lookup` 的 `ASK_TARGET_TEXT`。"""
    state = _dialog_state("756248 這張單怎麼樣", "已為你查詢，到期日已延。")
    provider = FakeProvider([_handoff_no_grounding_response()])
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    budget = Budget(max_rewrites=0)
    runtime = _runtime(provider=provider, verifier=verifier, budget=budget)

    result = await runtime.run_turn(_identity(), "那我要不要打電話給他", state)

    assert result.kind == "answer"
    assert result.answer == ASK_TARGET_TEXT
    assert result.answer != NO_JUDGEMENT_TEXT
    assert result.handoff is None
    assert len(provider.calls) == 1  # 沒有多耗一次「改寫」呼叫


@pytest.mark.req(_REQ)
async def test_no_recent_refs_path_unchanged_falls_to_ask_target_text():
    """沒有 recent refs 時現行行為不變——同樣落 `ASK_TARGET_TEXT`
    （既有 S4 §5 行為，這裡只證明新分支沒有意外攔截這條既有路）。"""
    state: dict = {}
    provider = FakeProvider([_handoff_no_grounding_response()])
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    budget = Budget(max_rewrites=1)
    runtime = _runtime(provider=provider, verifier=verifier, budget=budget)

    result = await runtime.run_turn(_identity(), "這題會轉人嗎？", state)

    assert result.kind == "answer"
    assert result.answer == ASK_TARGET_TEXT
    assert len(provider.calls) == 1  # 沒有 recent refs ⇒ 新分支不觸發改寫


# ---------------------------------------------------------------------------
# 6. §5：`context` 常數前綴（先 sanitize 再加）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_context_prefix_present_and_applied_after_sanitization():
    dirty = "要建立哪個​社區的物件？\x07"  # 含零寬與 C0，sanitize 後才加前綴
    provider = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider).run_turn(_identity(), "信仰", {}, context=dirty)

    block = next(b for b in _data_blocks(provider) if CALLER_CONTEXT_LABEL in b)
    body = _UNIT_MARKER_RE.sub("", block)
    assert CALLER_CONTEXT_PREFIX in body
    # 前綴之後緊接著已清乾淨的內容——零寬／C0 不在其中。
    assert "​" not in body
    assert "\x07" not in body
    assert "要建立哪個社區的物件？" in body


@pytest.mark.req(_REQ)
async def test_context_prefix_is_a_pure_constant_not_from_caller_input():
    """反對照：前綴本身不含任何呼叫端輸入——換一個完全不同的 `context`，
    前綴逐字不變。"""
    provider1 = FakeProvider([_final_response(answer="好的。")])
    provider2 = FakeProvider([_final_response(answer="好的。")])
    await _runtime(provider=provider1).run_turn(_identity(), "信仰", {}, context="第一句")
    await _runtime(provider=provider2).run_turn(_identity(), "信仰", {}, context="完全不同的第二句")

    block1 = next(b for b in _data_blocks(provider1) if CALLER_CONTEXT_LABEL in b)
    block2 = next(b for b in _data_blocks(provider2) if CALLER_CONTEXT_LABEL in b)
    assert CALLER_CONTEXT_PREFIX in _UNIT_MARKER_RE.sub("", block1)
    assert CALLER_CONTEXT_PREFIX in _UNIT_MARKER_RE.sub("", block2)


# ---------------------------------------------------------------------------
# 7. §5：`EMPTY_SESSION_TEXT` 新措辭
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_empty_session_text_value():
    assert EMPTY_SESSION_TEXT == "這段對話裡使用者還沒有說過話。"
