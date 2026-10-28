"""unit：W2 主模型輸出失控（灌空白至上限）處置——第 1 步 1-2～1-6。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-truncation-w2-20261017.md` §4 第 1 步；
凍結驗收清單 `acceptance-truncation-w2-20261017.md` C6（W-R1、W-R2、W-R6、W-R7、W-R9）。

覆蓋：
- 串流拼回後與非串流逐欄相同（含 tool_calls 多片段、依 `index` 累加）；
- 灌空白不提早中止（DSP-116）：串流讀到結束，空白後正常收尾的輸出照常採用；
- 截斷之後重寫附回的內容＝剝推理、去頭尾空白的半截輸出＋SCHEMA 回饋（有、無推理段，開關開、關各一）；
- 截斷後剩餘期限 < 2.6 秒 ⇒ 不重寫；
- 回合期限中斷進行中的呼叫（建立串流卡住、串流吐一半卡住）；
- 計量：有 usage 用 usage；逾時以字元數估算並記 `llm_usage_estimated`；
- 明示 JSON 句在 `system_content` 末尾且與 `SYSJSON` 逐字相同；`DEFAULT_MAX_COMPLETION_TOKENS == 2000`。
"""
from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace

import pytest
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function

from services.agent import runtime as runtime_mod
from services.agent.budget import Budget
from services.agent.prompt_assembler import OUTPUT_JSON_INSTRUCTION
from services.agent.runtime import (
    DEFAULT_MAX_COMPLETION_TOKENS,
    LLM_OUTPUT_REASONING_STRIPPED,
    LLM_OUTPUT_TRUNCATED,
    LLM_USAGE_ESTIMATED,
    SCHEMA_REWRITE_MIN_REMAINING_S,
    AgentRuntime,
    rewrite_feedback,
)
from services.agent.state_claim import STATE_CLAIM_SCHEMA_NAME as _STATE_CLAIM_SCHEMA
from services.agent.turn_context import TurnAccumulator
from tests.unit.agent.test_prompt_assembler_req import NONCE_A
from tests.unit.agent.test_prompt_assembler_req import _Outline as _PAOutline
from tests.unit.agent.test_prompt_assembler_req import _assembler as _pa_assembler
from tests.unit.agent.test_prompt_assembler_req import _identity as _pa_identity
from tests.unit.agent.test_prompt_assembler_req import _tool_specs as _pa_tool_specs
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeRegistry,
    FakeStream,
    FakeVerifier,
    _fake_message,
    _fake_response,
    _final_response,
    _identity,
)
from services.agent.tools.registry import ToolResult

pytestmark = pytest.mark.unit

@pytest.fixture
def closing_handoff_off(monkeypatch):
    """E 片：這類「送出內容與改前逐字相同」的測試釘住 `AGENT_CLOSING_HANDOFF=off`（E 片 on 的行為見 test_closing_handoff_e_req.py）。"""
    monkeypatch.setenv("AGENT_CLOSING_HANDOFF", "off")


#: 第 0 步實測的明示 JSON 原句（`w2/shim/replay.py` `SYSJSON`），逐字。
SYSJSON = (
    "Always respond with a single valid JSON object that matches the schema; "
    "do not output any text before or after the JSON."
)

SCHEMA_FEEDBACK = rewrite_feedback("SCHEMA", "輸出不符 AgentOutput schema。")
PARTIAL_JSON = '{"kind": "answer", "sentences": [{"text": "半截'


# ---------------------------------------------------------------------------
# 假串流 client
# ---------------------------------------------------------------------------


def _chunk(content=None, tool_calls=None, finish=None, usage=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            delta=SimpleNamespace(content=content, tool_calls=tool_calls), finish_reason=finish)],
        usage=None,
    ) if usage is None else SimpleNamespace(choices=[], usage=usage)


def _tcd(index, *, id=None, name=None, arguments=None):
    return SimpleNamespace(index=index, id=id, type="function" if id else None,
                           function=SimpleNamespace(name=name, arguments=arguments))


def _usage(pt, ct):
    return SimpleNamespace(prompt_tokens=pt, completion_tokens=ct)


class CountingStream(FakeStream):
    """記下實際被消費的 chunk 數，驗證串流讀到結束。"""

    def __init__(self, chunks):
        super().__init__(chunks)
        self.consumed = 0

    async def _iter(self):
        for c in self._chunks:
            self.consumed += 1
            yield c


class HangingStream(FakeStream):
    """吐完 `chunks` 之後卡住（模擬 Bedrock 極慢吐字）。"""

    async def _iter(self):
        for c in self._chunks:
            yield c
        await asyncio.sleep(3600)


class StreamCompletions:
    """腳本項目：`list[chunk]`（包成 CountingStream）、`FakeStream`、`callable(kwargs)->stream`、或
    `"hang"`（建立串流本身就卡住）。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[dict] = []
        self.streams: list = []

    async def create(self, **kwargs):
        rf = kwargs.get("response_format") or {}
        if (rf.get("json_schema") or {}).get("name") == _STATE_CLAIM_SCHEMA:
            # 帶狀態句判讀呼叫（非串流、不吃主腳本、不計入 calls）
            return _fake_response(_fake_message(content='{"claims": []}'), prompt_tokens=0, completion_tokens=0)
        if (rf.get("json_schema") or {}).get("name") == "DialogAct":
            # E 片：只判斷 dialog_act 的獨立呼叫（非串流、不吃主腳本、不計入 calls）
            return _fake_response(_fake_message(content='{"dialog_act": "none"}'), prompt_tokens=0, completion_tokens=0)
        self.calls.append(kwargs)
        assert self.script, "假 provider 腳本已耗盡——測試少寫了一步"
        step = self.script.pop(0)
        if step == "hang":
            await asyncio.sleep(3600)
        if callable(step):
            step = step(kwargs)
        if isinstance(step, list):
            step = CountingStream(step)
        self.streams.append(step)
        return step


def _provider(script):
    comp = StreamCompletions(script)
    prov = SimpleNamespace(async_client=SimpleNamespace(chat=SimpleNamespace(completions=comp)))
    prov.comp = comp
    return prov


def _runtime(provider, *, clean=True, budget=None, clock=None, max_completion_tokens=None):
    return AgentRuntime(
        provider, FakeRegistry(), FakeVerifier(), FakeAssembler(), budget or Budget(),
        stage="M1", clock=clock or FakeClock(), clean_llm_output=clean,
        max_completion_tokens=max_completion_tokens,
    )


def _text_chunks(text, *, size=50, finish="stop", usage=None):
    chunks = [_chunk(content=text[i:i + size]) for i in range(0, len(text), size)]
    chunks.append(_chunk(finish=finish))
    if usage is not None:
        chunks.append(_chunk(usage=usage))
    return chunks


def _final_json_chunks(**kw):
    resp = _final_response(**kw)
    return _text_chunks(resp.choices[0].message.content, usage=_usage(10, 5))


def _acc(messages=None):
    acc = TurnAccumulator()
    acc.messages = list(messages or [{"role": "system", "content": "persona"}])
    return acc


# ---------------------------------------------------------------------------
# 1. 串流拼回與非串流逐欄相同
# ---------------------------------------------------------------------------


async def test_stream_reassembly_equals_non_stream_message_with_multi_fragment_tool_calls():
    full = ChatCompletionMessage(
        role="assistant", content="前言",
        tool_calls=[
            ChatCompletionMessageToolCall(
                id="call_a", type="function",
                function=Function(name="kb__get", arguments='{"kb_id": "12", "x": "中文"}')),
            ChatCompletionMessageToolCall(
                id="call_b", type="function",
                function=Function(name="kb__search", arguments='{"q": "租金"}')),
        ])
    chunks = [
        _chunk(content="前"),
        _chunk(tool_calls=[_tcd(0, id="call_a", name="kb__get", arguments="")]),
        _chunk(tool_calls=[_tcd(0, arguments='{"kb_id"')]),
        _chunk(tool_calls=[_tcd(1, id="call_b", name="kb__search", arguments='{"q"')]),   # 兩個 index 交錯
        _chunk(tool_calls=[_tcd(0, arguments=': "12", "x": ')]),
        _chunk(content="言"),
        _chunk(tool_calls=[_tcd(1, arguments=': "租金"}')]),
        _chunk(tool_calls=[_tcd(0, arguments='"中文"}')]),
        _chunk(finish="tool_calls"),
        _chunk(usage=_usage(111, 22)),
    ]
    prov = _provider([chunks])
    acc = _acc()
    message, cut_short = await _runtime(prov)._next_model_message(acc, [])

    assert cut_short is False
    assert isinstance(message, ChatCompletionMessage)
    assert message.model_dump() == full.model_dump()           # 逐欄（含 role／refusal 等其餘欄位）
    assert message.content == full.content
    assert [(t.id, t.function.name, t.function.arguments) for t in message.tool_calls] == \
           [(t.id, t.function.name, t.function.arguments) for t in full.tool_calls]
    assert (acc.prompt_tokens, acc.completion_tokens, acc.llm_calls) == (111, 22, 1)
    assert LLM_OUTPUT_TRUNCATED not in acc.violations
    # 呼叫參數：串流、帶 usage、帶單次請求逾時；其餘鍵不變
    kw = prov.comp.calls[0]
    assert kw["stream"] is True and kw["stream_options"] == {"include_usage": True}
    assert 0 < kw["timeout"] <= Budget().deadline_s
    assert kw["max_completion_tokens"] == DEFAULT_MAX_COMPLETION_TOKENS


async def test_stream_text_only_reassembly_has_no_tool_calls_and_length_flag_is_recorded():
    prov = _provider([_text_chunks(PARTIAL_JSON, finish="length", usage=_usage(40, 2000))])
    acc = _acc()
    message, cut_short = await _runtime(prov)._next_model_message(acc, [])
    assert message.content == PARTIAL_JSON and message.tool_calls is None
    assert cut_short is True
    assert acc.violations == [LLM_OUTPUT_TRUNCATED]            # 真的 length ⇒ 只記 TRUNCATED
    assert (acc.prompt_tokens, acc.completion_tokens) == (40, 2000)


async def test_reasoning_is_stripped_from_reassembled_content_when_clean_on():
    prov = _provider([_text_chunks(f"<reasoning>想</reasoning>  {PARTIAL_JSON}\n", finish="length")])
    acc = _acc()
    message, _ = await _runtime(prov, clean=True)._next_model_message(acc, [])
    assert message.content == PARTIAL_JSON
    assert LLM_OUTPUT_REASONING_STRIPPED in acc.violations


# ---------------------------------------------------------------------------
# 2. 灌空白不提早中止（DSP-116）
# ---------------------------------------------------------------------------


async def test_whitespace_flood_after_reasoning_is_read_to_the_end_without_abort():
    chunks = (
        [_chunk(content="<reasoning>想</reasoning>")]
        + [_chunk(tool_calls=[_tcd(0, id="call_x", name="kb__get", arguments='{"kb_id": "1"}')])]
        + [_chunk(content="{")]
        + [_chunk(content="\n\t \r" * 250) for _ in range(10)]          # 10,000 個連續空白
        + [_chunk(finish="tool_calls"), _chunk(usage=_usage(9, 1500))]
    )
    prov = _provider([chunks])
    acc = _acc()
    message, cut_short = await _runtime(prov, clean=False)._next_model_message(acc, [])
    stream = prov.comp.streams[0]
    assert cut_short is False
    assert stream.closed == 0 and stream.consumed == len(chunks)              # 讀到結束、沒有關閉
    assert [(t.id, t.function.name) for t in message.tool_calls] == [("call_x", "kb__get")]
    assert acc.violations == []
    assert (acc.prompt_tokens, acc.completion_tokens) == (9, 1500)


async def test_whitespace_flood_then_valid_json_is_answered_with_a_single_call():
    """灌一段空白後仍正常收尾（對照重放 10 次退化中 7 次如此）⇒ 照常採用，不重寫。"""
    body = _final_response().choices[0].message.content
    text = body[:1] + " " * 3000 + body[1:]
    prov = _provider([_text_chunks(text, usage=_usage(10, 3000))])
    result = await _runtime(prov).run_turn(_identity(), "問題", {})
    assert result.kind == "answer"
    assert len(prov.comp.calls) == 1
    assert LLM_OUTPUT_TRUNCATED not in result.trace.violations


# ---------------------------------------------------------------------------
# 3. 截斷之後走現行 SCHEMA 重寫；附回內容剝推理、去頭尾空白
# ---------------------------------------------------------------------------


def _truncated_first(prefix: str):
    """第一次呼叫的輸出：`prefix` ＋ 半截 JSON ＋ 尾端大量空白，`finish=length`。"""
    return _text_chunks(prefix + PARTIAL_JSON + " " * 400, finish="length", usage=_usage(30, 2000))


@pytest.mark.parametrize("clean", [True, False])
@pytest.mark.parametrize("with_reasoning", [True, False])
async def test_truncated_output_is_rewritten_with_stripped_content_and_schema_feedback(clean, with_reasoning):
    prefix = "<reasoning>先想一下</reasoning>\n\n  " if with_reasoning else "\n  "
    prov = _provider([_truncated_first(prefix), _final_json_chunks()])
    rt = _runtime(prov, clean=clean)
    result = await rt.run_turn(_identity(), "問題", {})

    assert result.kind == "answer"
    assert len(prov.comp.calls) == 2
    second = prov.comp.calls[1]["messages"]
    assert second[-2] == {"role": "assistant", "content": PARTIAL_JSON}       # 剝推理段、去頭尾空白
    assert second[-1] == {"role": "user", "content": SCHEMA_FEEDBACK}
    assert LLM_OUTPUT_TRUNCATED in result.trace.violations
    assert prov.comp.streams[0].closed == 0


async def test_rewrite_after_truncation_counts_against_max_rewrites():
    """占 `max_rewrites`（預設 2）：連兩次截斷 ⇒ 第二次已達上限，固定句，不新增另一種重試。"""
    prov = _provider([_truncated_first(""), _truncated_first(""), _final_json_chunks()])
    result = await _runtime(prov).run_turn(_identity(), "問題", {})
    assert result.kind == "handoff" and result.handoff["reason"] == "budget_exhausted"
    assert len(prov.comp.calls) == 2


async def test_non_truncated_parse_failure_keeps_current_behaviour_verbatim():
    """非截斷的解析失敗：附回原文（含前後空白），逐字不變。"""
    bad = "  不是 JSON 的輸出 \n"
    prov = _provider([_text_chunks(bad, finish="stop", usage=_usage(5, 5)), _final_json_chunks()])
    result = await _runtime(prov, clean=False).run_turn(_identity(), "問題", {})
    assert result.kind == "answer"
    second = prov.comp.calls[1]["messages"]
    assert second[-2] == {"role": "assistant", "content": bad}
    assert second[-1] == {"role": "user", "content": SCHEMA_FEEDBACK}


# ---------------------------------------------------------------------------
# 4. 剩餘期限 < 2.6 秒不重寫
# ---------------------------------------------------------------------------


async def test_no_schema_rewrite_when_remaining_deadline_below_threshold():
    assert SCHEMA_REWRITE_MIN_REMAINING_S == 2.6
    clock = FakeClock()

    def _slow_first(_kw):
        clock.advance(20.0 - 2.0)            # 剩 2.0 秒 < 2.6
        return CountingStream(_truncated_first(""))

    prov = _provider([_slow_first, _final_json_chunks()])
    result = await _runtime(prov, clock=clock).run_turn(_identity(), "問題", {})
    assert result.kind == "handoff" and result.handoff["reason"] == "budget_exhausted"
    assert len(prov.comp.calls) == 1                                          # 沒有第二次呼叫


async def test_schema_rewrite_still_happens_when_remaining_deadline_above_threshold():
    clock = FakeClock()

    def _slow_first(_kw):
        clock.advance(20.0 - 3.0)            # 剩 3.0 秒 ≥ 2.6
        return CountingStream(_truncated_first(""))

    prov = _provider([_slow_first, _final_json_chunks()])
    result = await _runtime(prov, clock=clock).run_turn(_identity(), "問題", {})
    assert result.kind == "answer" and len(prov.comp.calls) == 2


# ---------------------------------------------------------------------------
# 5. 回合期限中斷進行中的呼叫
# ---------------------------------------------------------------------------


async def test_deadline_interrupts_call_that_never_returns_a_stream():
    prov = _provider(["hang"])
    rt = _runtime(prov, budget=Budget(deadline_s=0.3))              # 假時鐘不動 ⇒ 剩餘 0.3 秒，由 wait_for 實際計時
    t0 = time.monotonic()
    result = await rt.run_turn(_identity(), "問題", {})
    elapsed = time.monotonic() - t0
    assert result.kind == "handoff" and result.handoff["reason"] == "budget_exhausted"
    assert 0.25 <= elapsed < 2.0
    assert prov.comp.calls[0]["timeout"] == pytest.approx(0.3, abs=0.05)    # SDK 單次請求逾時也帶了


@pytest.mark.usefixtures("closing_handoff_off")
async def test_deadline_interrupts_stream_that_stalls_midway_closes_it_and_meters_an_estimate(monkeypatch):
    metered: list = []
    monkeypatch.setattr(runtime_mod.usage_metering, "add_llm_usage", lambda model, u: metered.append(dict(u)))
    stalled = HangingStream([_chunk(content=PARTIAL_JSON)])
    prov = _provider([stalled])
    rt = _runtime(prov, budget=Budget(deadline_s=0.3))
    t0 = time.monotonic()
    result = await rt.run_turn(_identity(), "問題", {})
    assert time.monotonic() - t0 < 2.0
    assert result.kind == "handoff" and result.handoff["reason"] == "budget_exhausted"
    assert stalled.closed == 1
    assert metered == [{"prompt_tokens": 0, "completion_tokens": len(PARTIAL_JSON)}]
    assert LLM_USAGE_ESTIMATED in result.trace.violations


async def test_deadline_already_passed_before_the_call_does_not_call_the_model():
    """迴圈頂端檢查之後、真正呼叫前期限已過（B 片程式分支花時間）⇒ 不送請求，直接固定句。"""
    clock = FakeClock()
    rt = _runtime(_provider([]), clock=clock)
    acc = _acc()
    acc.start = 0.0
    clock.advance(21.0)
    with pytest.raises(runtime_mod._ModelCallDeadline):
        await rt._next_model_message(acc, [])


# ---------------------------------------------------------------------------
# 6. 計量
# ---------------------------------------------------------------------------


async def test_metering_uses_usage_when_present_and_estimates_on_deadline(monkeypatch):
    metered: list = []
    monkeypatch.setattr(runtime_mod.usage_metering, "add_llm_usage", lambda model, u: metered.append(dict(u)))
    tool_call_stream = [
        _chunk(tool_calls=[_tcd(0, id="c1", name="kb__get", arguments='{"kb_id": "1"}')]),
        _chunk(finish="tool_calls"), _chunk(usage=_usage(123, 7)),
    ]
    prov = _provider([tool_call_stream, HangingStream([_chunk(content=PARTIAL_JSON)])])
    rt = AgentRuntime(
        prov, FakeRegistry(call_results=[ToolResult(ok=True, data={"id": 1}, text_for_model="x")]),
        FakeVerifier(), FakeAssembler(), Budget(deadline_s=0.3), stage="M1", clock=FakeClock(),
        clean_llm_output=True)
    result = await rt.run_turn(_identity(), "問題", {})
    assert result.kind == "handoff" and result.handoff["reason"] == "budget_exhausted"
    assert metered[0] == {"prompt_tokens": 123, "completion_tokens": 7}
    assert metered[1] == {"prompt_tokens": 123, "completion_tokens": len(PARTIAL_JSON)}   # prompt 取本回合上一次主呼叫
    assert result.trace.violations.count(LLM_USAGE_ESTIMATED) == 1
    assert result.trace.prompt_tokens == 123 + 123
    assert result.trace.completion_tokens == 7 + len(PARTIAL_JSON)


async def test_estimate_without_previous_call_uses_zero_prompt_and_is_capped(monkeypatch):
    metered: list = []
    monkeypatch.setattr(runtime_mod.usage_metering, "add_llm_usage", lambda model, u: metered.append(dict(u)))
    prov = _provider([HangingStream([_chunk(content="{" + " " * 600)])])
    acc = _acc()
    rt = _runtime(prov, budget=Budget(deadline_s=0.3), max_completion_tokens=100)
    with pytest.raises(runtime_mod._ModelCallDeadline):
        await rt._next_model_message(acc, [])
    assert metered == [{"prompt_tokens": 0, "completion_tokens": 100}]            # 上限 max_completion_tokens
    assert acc.violations.count(LLM_USAGE_ESTIMATED) == 1
    assert (acc.prompt_tokens, acc.completion_tokens) == (0, 100)


# ---------------------------------------------------------------------------


def test_system_content_ends_with_the_explicit_json_instruction_verbatim():
    msgs, _ = _pa_assembler().build(_pa_identity(), _PAOutline(), {}, [], _pa_tool_specs(), NONCE_A)
    system = msgs[0]["content"]
    assert OUTPUT_JSON_INSTRUCTION == SYSJSON
    assert system.endswith(OUTPUT_JSON_INSTRUCTION)
    assert system.count(SYSJSON) == 1


def test_default_max_completion_tokens_is_unchanged_at_2000():
    assert DEFAULT_MAX_COMPLETION_TOKENS == 2000
    assert _runtime(_provider([]))._max_completion_tokens == 2000
