"""unit：U3 純編號／短名詞的程式前置查詢（Plan
`inputs/plan-walkthrough-fixes-batch3-20260909.md` §4｜
knowledge-outline-and-intent-architecture:U3）。

守的事（逐條見各節）：
1. 觸發真值表：純數字 4–9 位、封閉標點／空白去頭尾、≤6 字無數字標點空白的
   短名詞；混合／過長／過短一律不觸發。
2. `ref` 字集拒收（`^[A-Za-z0-9_-]{1,32}$`）。
3. 查詢路徑**只走 `self.registry.call(...)`**（帶 identity／stage），
   ⛔ 不直呼 `tools/jgb2.py` 的函式。
4. trigger A 依序試帳單／修繕單／合約，第一個查到就停。
5. 查無 ⇒ 固定句；範圍外／逾時例外 ⇒ 完全不注入（兩者不同，⛔ 不得合流）。
6. 保留 id `pre-{nonce[:8]}` 每回合無條件算出、撞名一律拒收。
7. 注入段可引用、不進 dialog；trace 只有 `{"kind","hits"}`，⛔ 無原文。
8. select 範圍已釘住時，前置查詢的結果一樣過 `_enforce_tool_scope`。

⛔ 不接真 OpenAI、不接真 DB、不直接 import `services.agent.tools.jgb2`。
"""
from __future__ import annotations

import inspect
import json

import pytest

from services.agent.identity import Identity
from services.agent.output_schema import VerifierVerdict
from services.agent.runtime import (
    PRE_LOOKUP_LABEL,
    PRE_LOOKUP_NOT_FOUND_TEXT,
    PRE_LOOKUP_PROVENANCE_SOURCE,
    SELECT_SCOPE_KEY,
    AgentRuntime,
    _pre_lookup_trigger,
)
from services.agent.tools.registry import ToolResult

from tests.unit.agent.test_entry_line_req import _collision_provider
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _final_response,
    _identity,
)

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:U3"


def _runtime(*, provider=None, registry=None, verifier=None, budget=None, assembler=None):
    from services.agent.budget import Budget

    return AgentRuntime(
        provider if provider is not None else FakeProvider([_final_response(answer="好的。")]),
        registry if registry is not None else FakeRegistry(),
        verifier if verifier is not None else FakeVerifier(),
        assembler if assembler is not None else FakeAssembler(),
        budget or Budget(),
        stage="M1",
        clock=FakeClock(),
    )


def _data_blocks(provider) -> list[dict]:
    """假 provider 第一次呼叫時送出的完整 `messages` 清單（含角色）。"""
    assert provider.calls, "provider 沒被呼叫——這個測試的前提就不成立"
    return list(provider.calls[0]["messages"])


def _user_contents(provider) -> list[str]:
    return [str(m.get("content") or "") for m in _data_blocks(provider) if m.get("role") == "user"]


# ---------------------------------------------------------------------------
# 1. 觸發真值表
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
@pytest.mark.parametrize(
    "message,expected",
    [
        ("123", None),                    # 3 位數字：太短
        ("1234", ("id", "1234")),         # 4 位：下界
        ("123456789", ("id", "123456789")),  # 9 位：上界
        ("1234567890", None),             # 10 位：太長
        ("７５６２４８", None),            # 全形數字不算「純 ASCII 數字」
        ("756248！", ("id", "756248")),    # 帶標點：去頭尾後仍是 id
        ("，756248。", ("id", "756248")),  # 標點在頭尾兩側
        ("abc123", None),                 # 混合英數：兩種觸發都不算
        ("信仰", ("keyword", "信仰")),      # 2 字短名詞
        ("六個字的名詞喔", None),           # 7 字：超過短名詞上限（strip 後仍 7 字）
        ("六個字喔喔", ("keyword", "六個字喔喔")),  # 5 字：在短名詞範圍內
        ("  信仰  ", ("keyword", "信仰")),  # 前後空白
        ("信 仰", None),                   # 字中夾空白：不算短名詞
        ("信，仰", None),                  # 字中夾標點：不算短名詞
    ],
)
def test_pre_lookup_trigger_truth_table(message, expected):
    assert _pre_lookup_trigger(message) == expected


@pytest.mark.req(_REQ)
def test_affirmative_words_never_trigger_positive_control():
    """`AFFIRMATIVE_WORDS`（T3 既有凍結集合）整句一律不觸發——它們的既有語意
    是回應上一句提議，不是使用者在打編號或名稱。"""
    for word in ("對", "好", "是", "嗯", "可以", "好的", "OK"):
        assert _pre_lookup_trigger(word) is None, word


@pytest.mark.req(_REQ)
def test_non_string_message_does_not_trigger():
    assert _pre_lookup_trigger(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. ref 字集拒收
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_ref_charset_rejection_before_use():
    """`_pre_lookup_id_result` 對不合字集的 `ref` **不呼叫 registry**、直接查無
    ——即使呼叫端（假設性地）繞過了 `_pre_lookup_trigger` 直接餵一個壞字集。"""
    registry = FakeRegistry()
    runtime = _runtime(registry=registry)
    outcome, facts = await runtime._pre_lookup_id_result(
        _identity(), "123 456", None, []
    )
    assert outcome == "not_found"
    assert facts is None
    assert registry.call_args == []  # 字集不過關 ⇒ 連 registry 都沒打


# ---------------------------------------------------------------------------
# 3. 查詢路徑：只走 registry.call，⛔ 不直呼 tools/jgb2.py
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_pre_lookup_methods_source_never_references_jgb2_tool_functions():
    """靜態檢查：兩個查詢方法的原始碼裡沒有 `jgb2.query_*` 這種直呼字樣，
    也沒有 `from services.agent.tools import jgb2` 之類的直接匯入——
    唯一的呼叫落點是 `self.registry.call(...)`。"""
    src_id = inspect.getsource(AgentRuntime._pre_lookup_id_result)
    src_kw = inspect.getsource(AgentRuntime._pre_lookup_keyword_result)
    for src in (src_id, src_kw):
        assert "self.registry.call(" in src
        assert "jgb2.query_" not in src
        assert "import jgb2" not in src


@pytest.mark.req(_REQ)
async def test_registry_call_receives_identity_and_stage():
    identity = _identity()
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "帳單金額 1200 元，尚未繳費。"})]
    )
    runtime = _runtime(registry=registry)

    result = await runtime.run_turn(identity, "756248", {})

    assert registry.call_args, "registry.call 完全沒被呼叫"
    first = registry.call_args[0]
    assert first["identity"] is identity
    assert first["stage"] == "M1"
    assert first["for_model"] is True
    assert first["name"] in ("jgb2.query.bills", "jgb2.query.repairs", "jgb2.query.contracts")
    assert result.trace.pre_lookup == {"kind": "id", "hits": 1}


# ---------------------------------------------------------------------------
# 4. trigger A：第一個查到就停（帳單→修繕單→合約）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_id_trigger_stops_at_first_found_tool():
    registry = FakeRegistry(
        call_results=[
            ToolResult(ok=False, error="NO_MATCH"),                       # 帳單：查無
            ToolResult(ok=True, data={"facts": "修繕單狀態：處理中。"}),      # 修繕單：找到
        ]
    )
    runtime = _runtime(registry=registry)

    result = await runtime.run_turn(_identity(), "756248", {})

    assert len(registry.call_args) == 2   # 合約那一域根本沒被打
    assert registry.call_args[0]["name"] == "jgb2.query.bills"
    assert registry.call_args[1]["name"] == "jgb2.query.repairs"
    assert result.trace.pre_lookup == {"kind": "id", "hits": 1}


# ---------------------------------------------------------------------------
# 5. 查無 ⇒ 固定句；範圍外／錯誤 ⇒ 完全不注入
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_not_found_injects_the_fixed_line():
    registry = FakeRegistry(
        call_results=[
            ToolResult(ok=False, error="NO_MATCH"),
            ToolResult(ok=False, error="NO_MATCH"),
            ToolResult(ok=False, error="NO_MATCH"),
        ]
    )
    provider = FakeProvider([_final_response(answer="好的。")])
    runtime = _runtime(provider=provider, registry=registry)

    result = await runtime.run_turn(_identity(), "999999", {})

    assert len(registry.call_args) == 3  # 三域都查過、都查無
    blocks = _user_contents(provider)
    injected = next(b for b in blocks if PRE_LOOKUP_LABEL in b)
    assert PRE_LOOKUP_NOT_FOUND_TEXT in injected
    assert result.trace.pre_lookup == {"kind": "id", "hits": 0}


@pytest.mark.req(_REQ)
async def test_not_visible_role_id_gets_the_same_not_found_line():
    """純數字非本 role 的 id：identity 閘擋下＝工具層 `NO_MATCH`，
    走的正是同一句（L15-13：查無與看不到不細分）。"""
    registry = FakeRegistry(
        call_results=[
            ToolResult(ok=False, error="NO_MATCH"),
            ToolResult(ok=False, error="NO_MATCH"),
            ToolResult(ok=False, error="NO_MATCH"),
        ]
    )
    provider = FakeProvider([_final_response(answer="好的。")])
    runtime = _runtime(provider=provider, registry=registry)

    result = await runtime.run_turn(_identity(role_id="R-other"), "123456", {})

    blocks = _user_contents(provider)
    injected = next(b for b in blocks if PRE_LOOKUP_LABEL in b)
    assert PRE_LOOKUP_NOT_FOUND_TEXT in injected
    assert result.trace.pre_lookup == {"kind": "id", "hits": 0}


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("error_code", ["TOOL_TIMEOUT", "RATE_LIMITED", "INVALID_INPUT"])
async def test_error_or_timeout_injects_nothing_and_surfaces_no_error(error_code):
    """逾時／速率限制／例外 ⇒ **完全不注入**（⛔ 不是查無那句）——「沒查成」
    講成「查不到」是假話；也 ⛔ 讓工具錯誤碼露出去給使用者。"""
    registry = FakeRegistry(call_results=[ToolResult(ok=False, error=error_code)])
    provider = FakeProvider([_final_response(answer="好的。")])
    runtime = _runtime(provider=provider, registry=registry)

    result = await runtime.run_turn(_identity(), "756248", {})

    blocks = _user_contents(provider)
    assert not any(PRE_LOOKUP_LABEL in b for b in blocks)
    assert result.answer == "好的。"          # ⛔ 沒有任何工具錯誤碼混進答案
    assert error_code not in json.dumps(result.trace.violations, ensure_ascii=False)
    assert result.trace.pre_lookup == {"kind": "id", "hits": 0}


@pytest.mark.req(_REQ)
async def test_registry_exception_injects_nothing():
    registry = FakeRegistry(raise_on_call=RuntimeError("boom"))
    provider = FakeProvider([_final_response(answer="好的。")])
    runtime = _runtime(provider=provider, registry=registry)

    result = await runtime.run_turn(_identity(), "信仰", {})

    blocks = _user_contents(provider)
    assert not any(PRE_LOOKUP_LABEL in b for b in blocks)
    assert result.trace.pre_lookup == {"kind": "keyword", "hits": 0}


# ---------------------------------------------------------------------------
# 6. 保留 id：無條件存在、撞名拒收
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_reserved_pre_lookup_id_collision_is_rejected_even_without_trigger():
    """本回合訊息**沒有觸發**前置查詢（帶標點的長句），`pre-{nonce[:8]}`
    仍是保留字——模型能不能偽造這個 id 不該取決於這回合是否真的觸發過。"""
    assembler = FakeAssembler()
    provider = _collision_provider(assembler, lambda nonce: f"pre-{nonce[:8]}")
    result = await _runtime(provider=provider, assembler=assembler).run_turn(
        _identity(), "你好，這是一個不會觸發前置查詢的句子。", {}
    )
    assert "tool_call_id_collides_with_reserved" in result.trace.violations
    assert result.trace.pre_lookup is None  # 這句本來就沒觸發


@pytest.mark.req(_REQ)
async def test_reserved_pre_lookup_id_collision_is_rejected_when_triggered():
    assembler = FakeAssembler()
    provider = _collision_provider(assembler, lambda nonce: f"pre-{nonce[:8]}")
    registry = FakeRegistry(call_results=[ToolResult(ok=False, error="NO_MATCH")] * 3)
    result = await _runtime(provider=provider, assembler=assembler, registry=registry).run_turn(
        _identity(), "756248", {}
    )
    assert "tool_call_id_collides_with_reserved" in result.trace.violations


# ---------------------------------------------------------------------------
# 7. 注入段可引用、不進 dialog；trace 只有 kind／hits
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_injected_segment_is_citable_and_absent_from_dialog():
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "帳單金額 1200 元，尚未繳費。"})]
    )
    provider = FakeProvider([_final_response(answer="帳單金額是 1200 元。")])
    state: dict = {}
    result = await _runtime(provider=provider, registry=registry).run_turn(
        _identity(), "756248", state
    )

    blocks = _user_contents(provider)
    injected = next(b for b in blocks if PRE_LOOKUP_LABEL in b)
    assert "帳單金額 1200 元" in injected
    assert PRE_LOOKUP_PROVENANCE_SOURCE in injected
    # ⛔ 不進 dialog 歷史
    dialog_text = json.dumps(state["agent"].get("dialog", []), ensure_ascii=False)
    assert "帳單金額 1200 元" not in dialog_text
    assert "756248" in dialog_text  # 正對照：dialog 真的有寫使用者這句


@pytest.mark.req(_REQ)
async def test_trace_carries_only_kind_and_hits_never_raw_ref_or_keyword():
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "帳單金額 1200 元。"})]
    )
    result = await _runtime(registry=registry).run_turn(_identity(), "756248", {})

    assert result.trace.pre_lookup == {"kind": "id", "hits": 1}
    dumped = json.dumps(
        {"violations": result.trace.violations, "pre_lookup": result.trace.pre_lookup},
        ensure_ascii=False,
    )
    assert "756248" not in dumped

    registry2 = FakeRegistry(call_results=[ToolResult(ok=False, error="NO_MATCH")])
    result2 = await _runtime(registry=registry2).run_turn(_identity(), "信仰", {})
    assert result2.trace.pre_lookup == {"kind": "keyword", "hits": 0}
    dumped2 = json.dumps(
        {"violations": result2.trace.violations, "pre_lookup": result2.trace.pre_lookup},
        ensure_ascii=False,
    )
    assert "信仰" not in dumped2


# ---------------------------------------------------------------------------
# 8. 已釘住的 select 範圍：前置查詢的結果一樣過範圍檢查
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_scope_pinned_other_estate_result_injects_nothing():
    registry = FakeRegistry(
        call_results=[
            ToolResult(
                ok=True,
                data={"facts": "另一戶的帳單金額。", "scope": {"estate_id": "999"}},
            )
        ]
    )
    provider = FakeProvider([_final_response(answer="好的。")])
    state = {"agent": {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "100"}}}
    result = await _runtime(provider=provider, registry=registry).run_turn(
        _identity(), "756248", state
    )

    blocks = _user_contents(provider)
    assert not any(PRE_LOOKUP_LABEL in b for b in blocks)
    assert "另一戶的帳單金額" not in result.answer
    assert result.trace.pre_lookup == {"kind": "id", "hits": 0}


@pytest.mark.req(_REQ)
async def test_scope_pinned_same_estate_result_still_injects_positive_control():
    """正對照：同戶時前置查詢照常注入——上一條的「不注入」不是恆真。"""
    registry = FakeRegistry(
        call_results=[
            ToolResult(
                ok=True,
                data={"facts": "同一戶的帳單金額。", "scope": {"estate_id": "100"}},
            )
        ]
    )
    provider = FakeProvider([_final_response(answer="好的。")])
    state = {"agent": {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "100"}}}
    result = await _runtime(provider=provider, registry=registry).run_turn(
        _identity(), "756248", state
    )

    blocks = _user_contents(provider)
    injected = next(b for b in blocks if PRE_LOOKUP_LABEL in b)
    assert "同一戶的帳單金額" in injected
    assert result.trace.pre_lookup == {"kind": "id", "hits": 1}


# ---------------------------------------------------------------------------
# 9. end-to-end：純編號一句 ⇒ 資料段排在使用者這句之前
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_pre_lookup_segment_precedes_the_user_message():
    registry = FakeRegistry(
        call_results=[ToolResult(ok=True, data={"facts": "帳單金額 1200 元，尚未繳費。"})]
    )
    provider = FakeProvider([_final_response(answer="帳單金額是 1200 元，尚未繳費。")])

    result = await _runtime(provider=provider, registry=registry).run_turn(
        _identity(), "756248", {}
    )

    messages = _data_blocks(provider)
    pre_idx = next(i for i, m in enumerate(messages) if PRE_LOOKUP_LABEL in str(m.get("content") or ""))
    user_idx = next(
        i for i, m in enumerate(messages)
        if m.get("role") == "user" and m.get("content") == "756248"
    )
    assert pre_idx < user_idx
    assert result.kind == "answer"


@pytest.mark.req(_REQ)
async def test_keyword_not_found_injects_nothing():
    """短名詞查無**不注入**（主線 2026-09-09 收緊：「怎麼辦」「取消」這類 ≤6 字短句也會觸發
    keyword 查詢，印「查不到這個編號或名稱」會誤導模型）；trace 仍記 hits=0（正對照：
    純編號查無仍注入固定句，見 test_not_found_injects_the_fixed_line）。"""
    registry = FakeRegistry(call_results=[ToolResult(ok=False, error="NO_MATCH")])
    provider = FakeProvider([_final_response(answer="好的。")])
    runtime = _runtime(provider=provider, registry=registry)
    result = await runtime.run_turn(_identity(), "怎麼辦", {})
    blocks = _user_contents(provider)
    assert not any(PRE_LOOKUP_LABEL in b for b in blocks)  # 沒有注入段
    assert not any(PRE_LOOKUP_NOT_FOUND_TEXT in b for b in blocks)
    assert result.trace.pre_lookup == {"kind": "keyword", "hits": 0}
