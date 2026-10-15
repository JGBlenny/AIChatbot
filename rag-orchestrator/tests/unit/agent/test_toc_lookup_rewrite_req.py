"""unit：Plan 9.11（`inputs/plan-9.11-zero-lookup-navigation-20260924.md`）
D——「查到資料」改看回傳結果（零查詢轉人的固定優先序分類）。

⚠️ **A 已撤案**（業主 2026-09-24 裁定：KEEP D、REMOVE A）——真回合證據顯示
A（零查詢轉人 ⇒ 先翻目錄的迴圈內改寫）在 gpt-5-mini low／medium 兩種
reasoning effort 下，目標粗目 15 回合只開得到 1 次，且每次觸發都消耗一次
`max_rewrites` 並推高 `budget_exhausted`，淨效益為負。詳見
`.kiro/specs/knowledge-outline-and-intent-architecture/HANDOFF-20260923.md`
§9。本檔原本同時測 D＋A，A 撤案後這裡**只留 D**；原本的 A 測試（正例＋
6 個負對照＋兩條 fresh-verifier F1 補的負對照）已整批移除，⛔ 不是被判定
「測試寫錯」，是它測的行為本身不存在了。檔名沿用（業主裁定不必改檔名）。

覆蓋（對照 Plan §4 D 驗收逐條）：
1. `grounded` 計算真值表（§4-1）。
2. 零查詢／有資料／全空／導航清單四種轉人出口真值表（§4-2）。
3. `handoff.request`＋`has_recent_refs` ⇒ 恰一次 `RECENT_REFS`（§4-3）。
4. `_ok_candidates` 真實形狀 ⇒ 分類 `empty`；撞保留 id ⇒ 分類 `failed`，
   ③／V2 皆不觸發、④ 不動（§4-3b）。
5. `jgb2.query` 空結果 → `handoff.request` → 轉人 ⇒ T2 改寫 0 次、`NO_DATA_TEXT`
   （§4-3c）。

⛔ 不接真 OpenAI、不接真 DB、不接真正本。
"""
from __future__ import annotations

import json

import pytest

from services.agent.budget import Budget
from services.agent.output_schema import VerifierVerdict
from services.agent.runtime import (
    ASK_TARGET_TEXT,
    HANDOFF_DATA_REWRITE_HINT,
    NO_DATA_TEXT,
    NO_JUDGEMENT_TEXT,
    RECENT_REFS_REWRITE_HINT,
    rewrite_feedback,
)
from services.agent.tools.registry import Provenance, ToolResult

from tests.unit.agent.test_recent_refs_req import _dialog_state
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _fake_message,
    _fake_response,
    _fake_tool_call,
    _final_response,
    _identity,
    _runtime,
    _tool_call_response,
)

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:9.11"


def _handoff_response(fact_class="feature", reason="no_grounding"):
    payload = {
        "kind": "handoff", "sentences": [], "fact_class": fact_class,
        "handoff_reason": reason,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _messages_after_first(provider, user_message: str) -> list[str]:
    msgs = provider.calls[-1]["messages"]
    idx = [i for i, m in enumerate(msgs) if m.get("role") == "user" and m.get("content") == user_message]
    assert idx, "最後一次呼叫裡找不到使用者原話——前提不成立"
    return [str(m.get("content") or "") for m in msgs[idx[-1] + 1:] if m.get("role") == "user"]


def _no_outline(rt):
    """把 `runtime._select_outline` 換成一支永遠回 `(None, None)` 的假函式
    ——D 完全不依賴大綱是否預載，這裡只是保證「沒有大綱」這件事顯式、
    不依賴 `get_canon()` 的真實註冊表狀態（那要真正本，unit 層不該碰）。"""
    async def _fake_select_outline(identity, user_message, dialog, violations):
        return None, None

    rt._select_outline = _fake_select_outline
    return rt


# ═══════════════════════════════════════════════════════════════════
# 1. `grounded` 計算真值表（§4-1）
# ═══════════════════════════════════════════════════════════════════
async def _single_tool_turn_grounded(*, tool_result=None, registry=None, call_id="call_1") -> bool:
    """跑一回合「一次工具呼叫 → 一般作答」，回傳第一筆 `tool_calls` 的 `grounded`。"""
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[_fake_tool_call("some.tool", {}, call_id)])),
        _final_response(answer="好的"),
    ])
    reg = registry if registry is not None else FakeRegistry(call_results=[tool_result])
    rt = _runtime(provider=provider, registry=reg, verifier=FakeVerifier([VerifierVerdict(ok=True)]))
    result = await rt.run_turn(_identity(), "請幫我查一下這個問題", {})
    assert len(result.trace.tool_calls) == 1, result.trace.tool_calls
    return result.trace.tool_calls[0].grounded


@pytest.mark.req(_REQ)
async def test_grounded_true_when_ok_with_citable_nonblank_provenance():
    """`jgb2.query`／`kb.get` 細目同一種形狀：`ok=True`＋`citable=True` 非空文字。"""
    tr = ToolResult(ok=True, data={"facts": "帳單 756248 應繳 3200 元。"},
                    provenance=[Provenance(source="jgb2:bills#1", text="帳單 756248 應繳 3200 元。", citable=True)])
    assert await _single_tool_turn_grounded(tool_result=tr) is True


@pytest.mark.req(_REQ)
async def test_grounded_false_for_toc_or_coarse_navigation():
    """`kb.get` 目錄／粗目：provenance 存在但 `citable=False`（導航，非可引用內容）。"""
    tr = ToolResult(ok=True, data={"sections": 1},
                    provenance=[Provenance(source="outline:toc", text="A｜帳號｜3", citable=False)])
    assert await _single_tool_turn_grounded(tool_result=tr) is False


@pytest.mark.req(_REQ)
async def test_grounded_false_for_kb_search_no_provenance():
    tr = ToolResult(ok=True, data={"hits": []}, provenance=[], text_for_model="")
    assert await _single_tool_turn_grounded(tool_result=tr) is False


@pytest.mark.req(_REQ)
async def test_grounded_false_for_handoff_request_shape():
    """`handoff.request` 真實回傳形狀：`provenance=[]`（見 `tools/handoff.py` 決定 3）。"""
    tr = ToolResult(ok=True, data={"message": "轉人固定句", "handoff": {"reason": "no_grounding"}},
                    provenance=[], text_for_model="轉人固定句")
    assert await _single_tool_turn_grounded(tool_result=tr) is False


@pytest.mark.req(_REQ)
async def test_grounded_false_for_session_slots_shape():
    tr = ToolResult(ok=True, data={"slots": {}}, provenance=[])
    assert await _single_tool_turn_grounded(tool_result=tr) is False


@pytest.mark.req(_REQ)
async def test_grounded_false_for_hallucinated_tool_name_no_match():
    """幻覺工具名：`FakeRegistry` 空 `call_results` 時的既有預設 ⇒ `NO_MATCH`。"""
    assert await _single_tool_turn_grounded(registry=FakeRegistry(call_results=[])) is False


@pytest.mark.req(_REQ)
async def test_grounded_false_for_reserved_id_collision_even_with_citable_provenance():
    """撞保留 id：即使底層 `ToolResult` 真的帶 `citable=True` 非空 provenance，
    這一筆也 ⛔ 不算 `grounded`（它沒有真的登記進 `tool_results_by_id`）。"""
    assembler = FakeAssembler()

    def _collision_step(kwargs=None):
        nonce = assembler.calls[0]["nonce"]
        call_id = f"pre-{nonce[:8]}"
        return _fake_response(_fake_message(
            tool_calls=[_fake_tool_call("jgb2.query.bills", {"ref": "1"}, call_id)]
        ))

    provider = FakeProvider([_collision_step, _final_response(answer="好的")])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"facts": "帳單資料"},
                   provenance=[Provenance(source="jgb2:bills#1", text="帳單資料", citable=True)])
    ])
    rt = _runtime(provider=provider, registry=registry, assembler=assembler,
                 verifier=FakeVerifier([VerifierVerdict(ok=True)]))
    result = await rt.run_turn(_identity(), "請幫我查一下這個問題", {})
    assert "tool_call_id_collides_with_reserved" in result.trace.violations
    assert len(result.trace.tool_calls) == 1
    assert result.trace.tool_calls[0].grounded is False


# ═══════════════════════════════════════════════════════════════════
# 2. 四種轉人出口真值表（§4-2）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_handoff_request_only_takes_zero_lookup_exit_not_no_judgement():
    """只呼叫 `handoff.request` 後轉人 ⇒ ③ 零查詢出口（`ASK_TARGET_TEXT`），
    ⛔ 不出 `NO_JUDGEMENT_TEXT`、⛔ 不觸發 T2 改寫。"""
    provider = FakeProvider([
        _tool_call_response("handoff.request", {"reason": "no_grounding", "fact_class": "feature"}),
        _handoff_response(),
    ])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"message": "轉人固定句", "handoff": {"reason": "no_grounding"}},
                   provenance=[], text_for_model="轉人固定句")
    ])
    rt = _no_outline(_runtime(provider=provider, registry=registry,
                              verifier=FakeVerifier([VerifierVerdict(ok=True)])))
    result = await rt.run_turn(_identity(), "幫我看一下這件事情要怎麼處理", {})

    assert result.kind == "answer"
    assert result.answer == ASK_TARGET_TEXT
    assert result.answer != NO_JUDGEMENT_TEXT
    feedback = _messages_after_first(provider, "幫我看一下這件事情要怎麼處理")
    assert not any(HANDOFF_DATA_REWRITE_HINT in f for f in feedback)


@pytest.mark.req(_REQ)
async def test_kb_get_with_data_then_handoff_still_takes_no_judgement_existing_behavior():
    """`kb.get` 細目有資料後轉人 ⇒ T2 改寫一次後仍轉人 ⇒ `NO_JUDGEMENT_TEXT`
    （既有行為，Plan 9.11 D 不改）。"""
    provider = FakeProvider([
        _tool_call_response("kb.get", {"kb_id": "1"}),
        _handoff_response(),
        _handoff_response(),
    ])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"facts": "押金全額退還政策"},
                   provenance=[Provenance(source="kb:1", text="押金全額退還政策", citable=True)])
    ])
    rt = _runtime(provider=provider, registry=registry,
                 verifier=FakeVerifier([VerifierVerdict(ok=True)]), budget=Budget(max_rewrites=1))
    result = await rt.run_turn(_identity(), "我的押金到底會不會退", {})

    assert result.kind == "answer"
    assert result.answer == NO_JUDGEMENT_TEXT
    feedback = _messages_after_first(provider, "我的押金到底會不會退")
    assert any(HANDOFF_DATA_REWRITE_HINT in f for f in feedback)


@pytest.mark.req(_REQ)
async def test_jgb2_query_all_empty_gives_no_data_existing_behavior():
    """`jgb2.query` 全 empty ⇒ `NO_DATA_TEXT`（既有行為）。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills", {"ref": "900003"}),
        _handoff_response(),
    ])
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"facts": ""}, text_for_model="")])
    rt = _no_outline(_runtime(provider=provider, registry=registry,
                              verifier=FakeVerifier([VerifierVerdict(ok=True)])))
    result = await rt.run_turn(_identity(), "900003 這張帳單的狀況", {})

    assert result.kind == "answer"
    assert result.answer == NO_DATA_TEXT


@pytest.mark.req(_REQ)
async def test_navigation_list_then_handoff_no_rewrite_no_no_judgement():
    """只開了導航清單（`kb.get` 目錄，`citable=False`）後轉人 ⇒ ⛔ 無
    `HANDOFF_DATA` 改寫、⛔ 無 `NO_JUDGEMENT_TEXT`。"""
    provider = FakeProvider([
        _tool_call_response("kb.get", {"kb_id": "toc"}),
        _handoff_response(),
    ])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"sections": 1},
                   provenance=[Provenance(source="outline:toc", text="A｜帳號｜3", citable=False)])
    ])
    rt = _no_outline(_runtime(provider=provider, registry=registry,
                              verifier=FakeVerifier([VerifierVerdict(ok=True)])))
    result = await rt.run_turn(_identity(), "幫我看一下這件事情要怎麼處理", {})

    assert result.answer != NO_JUDGEMENT_TEXT
    feedback = _messages_after_first(provider, "幫我看一下這件事情要怎麼處理")
    assert not any(HANDOFF_DATA_REWRITE_HINT in f for f in feedback)


# ═══════════════════════════════════════════════════════════════════
# 3. `handoff.request`＋`has_recent_refs`（§4-3）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_handoff_request_with_recent_refs_fires_v2_once():
    """恰一次 `RECENT_REFS` 改寫：`feedback == [...]` 是逐位相等比對，本身就
    排除了任何其他改寫訊息混進來的可能，⛔ 不需要另外斷言「不含別的改寫」
    ——那是 A 還在時才需要的區辨（A 已撤案，見本檔模組 docstring）。"""
    state = _dialog_state("756248 這張單怎麼樣", "已為你查詢，到期日已延。")
    provider = FakeProvider([
        _tool_call_response("handoff.request", {"reason": "no_grounding", "fact_class": "feature"}),
        _handoff_response(),
        _final_response(answer="依資料段，756248 已延期。"),
    ])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"message": "轉人固定句", "handoff": {"reason": "no_grounding"}},
                   provenance=[], text_for_model="轉人固定句")
    ])
    rt = _no_outline(_runtime(provider=provider, registry=registry,
                              verifier=FakeVerifier([VerifierVerdict(ok=True)]),
                              budget=Budget(max_rewrites=1)))
    result = await rt.run_turn(_identity(), "那我要不要打電話給他", state)

    assert result.kind == "answer"
    feedback = _messages_after_first(provider, "那我要不要打電話給他")
    assert feedback == [rewrite_feedback("RECENT_REFS", RECENT_REFS_REWRITE_HINT)]


# ═══════════════════════════════════════════════════════════════════
# 4. `_ok_candidates` 真實形狀／撞保留 id（§4-3b）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_ok_candidates_shape_classified_empty_gives_no_data():
    """`facts==""`＋`candidates`＋`citable=True` 非空 provenance（`_ok_candidates`
    真實形狀）⇒ 分類為 `empty`、出口 `NO_DATA_TEXT`（與改動前相同）。"""
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills", {"ref": "900003"}),
        _handoff_response(),
    ])
    registry = FakeRegistry(call_results=[
        ToolResult(
            ok=True,
            data={"facts": "", "candidates": [{"id": "1"}], "candidate_cap": 5, "skip_refine": False},
            provenance=[Provenance(source="jgb2:bills#candidates", text="候選清單：帳單1", citable=True)],
            text_for_model="候選清單：帳單1",
        )
    ])
    rt = _no_outline(_runtime(provider=provider, registry=registry,
                              verifier=FakeVerifier([VerifierVerdict(ok=True)])))
    result = await rt.run_turn(_identity(), "900003 這張帳單的狀況", {})

    assert result.trace.tool_calls[0].empty is True
    assert result.trace.tool_calls[0].grounded is False
    assert result.kind == "answer"
    assert result.answer == NO_DATA_TEXT


@pytest.mark.req(_REQ)
async def test_reserved_id_collision_turn_none_of_gate3_v2_fire_gate4_unchanged():
    """撞保留 id 的回合轉人 ⇒ 分類為 `failed`，③／V2 皆不觸發，④ 不動
    （＝既有「撞名不動」語義）。"""
    assembler = FakeAssembler()

    def _collision_step(kwargs=None):
        nonce = assembler.calls[0]["nonce"]
        call_id = f"pre-{nonce[:8]}"
        return _fake_response(_fake_message(
            tool_calls=[_fake_tool_call("jgb2.query.bills", {"ref": "1"}, call_id)]
        ))

    provider = FakeProvider([_collision_step, _handoff_response()])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"facts": "帳單資料"},
                   provenance=[Provenance(source="jgb2:bills#1", text="帳單資料", citable=True)])
    ])
    rt = _no_outline(_runtime(provider=provider, registry=registry, assembler=assembler,
                              verifier=FakeVerifier([VerifierVerdict(ok=True)])))
    result = await rt.run_turn(_identity(), "請幫我查一下這個問題", {})

    assert "tool_call_id_collides_with_reserved" in result.trace.violations
    assert result.kind == "handoff"          # ④ 不動
    assert result.answer != NO_DATA_TEXT
    assert result.answer != NO_JUDGEMENT_TEXT
    assert result.answer != ASK_TARGET_TEXT  # ③ 也沒動


# ═══════════════════════════════════════════════════════════════════
# 5. `jgb2.query` 空結果 → `handoff.request` → 轉人（§4-3c）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_mixed_empty_then_handoff_request_gives_no_data_zero_t2_rewrites():
    provider = FakeProvider([
        _tool_call_response("jgb2.query.bills", {"ref": "900003"}, "call_1"),
        _tool_call_response("handoff.request", {"reason": "no_grounding", "fact_class": "feature"}, "call_2"),
        _handoff_response(),
    ])
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"facts": ""}, text_for_model=""),
        ToolResult(ok=True, data={"message": "轉人固定句", "handoff": {"reason": "no_grounding"}},
                   provenance=[], text_for_model="轉人固定句"),
    ])
    rt = _no_outline(_runtime(provider=provider, registry=registry,
                              verifier=FakeVerifier([VerifierVerdict(ok=True)])))
    result = await rt.run_turn(_identity(), "900003 這張帳單的狀況", {})

    assert result.kind == "answer"
    assert result.answer == NO_DATA_TEXT
    feedback = _messages_after_first(provider, "900003 這張帳單的狀況")
    assert not any(HANDOFF_DATA_REWRITE_HINT in f for f in feedback)

