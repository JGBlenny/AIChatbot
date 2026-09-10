"""unit：R1 回放等價 golden（Plan R `inputs/plan-structural-refactor-20260910.md` §1.3）。

本檔是 **R1 結構整理的回退證明**：整理前以 regen 模式由同一組腳本化替身
（`FakeProvider`／`FakeRegistry`／`FakeVerifier`／`FakeAssembler`／`FakeClock`）
產出 `tests/fixtures/agent/pipeline_golden.json`，整理後逐位比對。

⛔ **本檔 ⛔ 不驗任何判定的對錯**——那是各既有 `_req` 測試的事。它只驗
「同樣的輸入，整理前後產出逐位相同」。

**決定性**（缺一即不可比對）：
- `new_nonce`（`runtime.new_nonce`）→ 常數 ⇒ 九個保留 id 固定；
- `uuid.uuid4` → 常數 ⇒ `trace_id` 固定；
- `_clock` → `FakeClock` ⇒ `latency_ms == 0`；
- `bills._today` → 凍結日 ⇒ 確認卡的日期閘不隨真實時鐘漂；
- `violations` 比對前把 `replayed_from:<trace_id>` 正規化成 `replayed_from:<id>`。

**比對欄位**（Plan §1.3／r2 #4）：`kind`／`outcome`／`answer`／`quick_replies`／
`TurnResult.handoff` 全鍵／`TurnTrace` 全欄位（`dataclasses.fields` 逐欄，含非數值）／
`agent_state` 鍵集合與各鍵序列化值。另記每情境的**覆蓋標籤**——標籤一律
**由實際觀察導出**（送進模型的訊息裡有沒有那個保留 id 的標記、violations／outcome／
trace 欄位長什麼樣），⛔ 不是人手宣告的字串。

**重跑產生 golden**（腳本內建，Plan §1.3）：

    AGENT_GOLDEN_REGEN=1 python3 -m pytest tests/unit/agent/test_pipeline_golden_req.py -s

它會覆寫 fixture、印出覆蓋矩陣與比對欄位清單。
"""
from __future__ import annotations

import dataclasses
import json
import os
import uuid as _uuid_mod
from pathlib import Path
from typing import Any

import pytest

from services.agent import runtime as runtime_mod
from services.agent.budget import Budget
from services.agent.completed_actions import COMPLETED_ACTIONS_KEY
from services.agent.document_extract import DocumentTurnInput
from services.agent.identity import Identity
from services.agent.output_schema import VerifierVerdict
from services.agent.runtime import (
    ESTATE_CARRY_KEY,
    LAST_ASK_TARGET_KEY,
    PENDING_CONFIRM_KEY,
    SELECT_SCOPE_KEY,
    AgentRuntime,
    ImageTurnInput,
    TurnTrace,
    _cache_key,
)
from services.agent.tools.confirm import pending_id_for, sha256_hex
from services.agent.tools.registry import Provenance, ToolResult

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
)

pytestmark = pytest.mark.unit

from datetime import date as _date  # noqa: E402  — 見 `_determinism`

from services.agent import confirm_card as _confirm_card  # noqa: E402
from services.jgb import bills as _bills  # noqa: E402

_REQ = "knowledge-outline-and-intent-architecture:R1"

GOLDEN_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "agent" / "pipeline_golden.json"
)

#: 固定 nonce（16 位十六進位，符合 `_require_nonce` 的 `^[0-9A-Za-z]{8,64}$`）。
FIXED_NONCE = "0123456789abcdef"
#: 固定 trace_id（`uuid.uuid4().hex` 的形狀）。
FIXED_TRACE_ID = "ffffffffffffffffffffffffffffffff"
FROZEN_TODAY = _date(2026, 8, 15)

#: 九個保留 id 前綴（`_run_turn_body` 由 nonce 導出的那一組）。
RESERVED_PREFIXES: tuple = (
    "img-", "done-", "entry-", "aff-", "ctx-", "pre-", "ref-", "doc-", "est-",
)

REGEN = os.environ.get("AGENT_GOLDEN_REGEN", "") == "1"


# ---------------------------------------------------------------------------
# 決定性：全域 autouse
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _determinism(monkeypatch):
    monkeypatch.setattr(runtime_mod, "new_nonce", lambda: FIXED_NONCE)
    monkeypatch.setattr(_uuid_mod, "uuid4", lambda: _uuid_mod.UUID(hex=FIXED_TRACE_ID))
    monkeypatch.setattr(_bills, "_today", lambda: FROZEN_TODAY)


# ---------------------------------------------------------------------------
# 替身補強（既有替身缺的兩個管道；⛔ 不改既有替身）
# ---------------------------------------------------------------------------
class GoldenRegistry(FakeRegistry):
    """`FakeRegistry` ＋ `specs_for`（文件回合的寫入面過濾用）。"""

    def __init__(self, *, specs=None, **kwargs):
        super().__init__(**kwargs)
        self._specs = list(specs or [])

    def specs_for(self, identity, stage, *, readonly_view=False, for_model=False):
        return list(self._specs)


class GoldenVerifier(FakeVerifier):
    """`FakeVerifier` ＋ `_verify_routes`（清單點選段的 facts 出口複查）。"""

    def _verify_routes(self, text):  # noqa: D401 — 一律放行（golden ⛔ 不驗判定）
        return None


class FakePool:
    """`redeem_pending` 用得到的唯一方法（同 `test_runtime_confirm_segment_req`）。"""

    def __init__(self, rows):
        self._rows = list(rows)
        self.calls: list = []

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows.pop(0) if self._rows else None


def _spec(openai_name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": openai_name,
            "description": "",
            "strict": True,
            "parameters": {
                "type": "object", "properties": {}, "required": [],
                "additionalProperties": False,
            },
        },
    }


_TOOL_SPECS = [_spec("kb__get"), _spec("jgb2__query__bills"), _spec("confirm__request")]

_WRITE_SPECS = [
    {"name": "confirm.request", "scope": "read", "mcp_only": None, "mutates_session": True},
    {"name": "jgb2.action.bill_due_extend", "scope": "write", "mcp_only": None,
     "mutates_session": False},
]


def _final(*, kind="answer", text="答案內容", fact_class="feature",
           handoff_reason=None, ask_target=None, refs=None):
    payload = {
        "kind": kind,
        "sentences": [] if not text else [
            {"text": text, "kind": "greeting", "refs": list(refs or [])}
        ],
        "fact_class": fact_class,
        "handoff_reason": handoff_reason,
        "ask_target": ask_target,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _tool_call(name: str, args: dict, call_id: str = "call_1"):
    return _fake_response(_fake_message(tool_calls=[_fake_tool_call(name, args, call_id)]))


def _identity(**overrides) -> Identity:
    base = dict(vendor_id=1, target_user="property_manager", mode="b2b",
                api_key_id=1, session_id="mcp:1:1:s1", entry="mcp", user_id=77)
    base.update(overrides)
    return Identity(**base)


def _registry(**kwargs) -> GoldenRegistry:
    return GoldenRegistry(specs=_WRITE_SPECS, tool_specs=_TOOL_SPECS, **kwargs)


def _runtime(*, provider=None, registry=None, verifier=None, budget=None,
             pool=None, readonly_view=False) -> AgentRuntime:
    return AgentRuntime(
        provider if provider is not None else _empty_provider(),
        registry if registry is not None else _registry(),
        verifier if verifier is not None else GoldenVerifier(),
        FakeAssembler(),
        budget or Budget(),
        stage="M1",
        clock=FakeClock(),
        db_pool=pool,
        readonly_view=readonly_view,
        model="golden-model",
    )


def _prov(text: str) -> list:
    return [Provenance(source="tool", text=text, citable=True)]


# ---------------------------------------------------------------------------
# 確認鏈素材（與 `test_runtime_confirm_segment_req` 同一份凍結 payload）
# ---------------------------------------------------------------------------
_PAYLOAD = {
    "action": "bill_due_extend",
    "bill_id": "900001",
    "date_expire_before": "20260815",
    "days": 3,
    "date_expire_after": "20260818",
}
_CARD = _confirm_card.render("bill_due_extend", _PAYLOAD)
_TOKEN = "tok-secret-value-must-never-leak-0123456789"
_PID = pending_id_for(_TOKEN)


def _redeem_row():
    from services.agent.tools.confirm import payload_digest

    return {"token": _TOKEN, "payload_sha256": payload_digest(_PAYLOAD),
            "summary_sha256": sha256_hex(_CARD)}


def _pending_state(**overrides) -> dict:
    pending = {"action": "bill_due_extend", "payload": dict(_PAYLOAD),
               "card_sha256": sha256_hex(_CARD)}
    pending.update(overrides)
    return {"agent": {PENDING_CONFIRM_KEY: {_PID: pending}}}


# ═══════════════════════════════════════════════════════════════════════
# 情境表（≥17 條；每條回 `(runtime, identity, message, state, kwargs)`）
# ═══════════════════════════════════════════════════════════════════════
def _s_plain_answer():
    rt = _runtime(provider=FakeProvider([_final(text="這是一般回答")]))
    return rt, _identity(), "請問這個系統怎麼用呢", {}, {}


def _s_tool_then_answer():
    rt = _runtime(
        provider=FakeProvider([_tool_call("kb.get", {"kb_id": "3600"}),
                               _final(text="工具查完後的回答")]),
        registry=_registry(call_results=[
            ToolResult(ok=True, data={"id": 3600}, text_for_model="工具原文")]),
    )
    return rt, _identity(), "幫我查一下知識庫的內容", {}, {}


def _s_entry_context():
    rt = _runtime(provider=FakeProvider([_final(text="收到進場句後的回答")]))
    return rt, _identity(), "我想了解一下服務範圍", {}, {"context": "您好，這裡是租客服務窗口。"}


def _s_affirmative_carry():
    state = {"agent": {LAST_ASK_TARGET_KEY: "confirm_intent",
                       "dialog": [{"role": "assistant", "content": "要我幫你送出嗎"}]}}
    rt = _runtime(provider=FakeProvider([_final(text="好的，我來處理")]))
    return rt, _identity(), "好", state, {}


def _s_empty_session_note():
    """dialog 長度 0 ⇒ `ctx-` 空會話註記段。"""
    rt = _runtime(provider=FakeProvider([_final(text="這是全新對話的第一句")]))
    return rt, _identity(), "你剛剛跟我說了什麼呢", {}, {}


def _s_pre_lookup_id_found():
    rt = _runtime(
        provider=FakeProvider([_final(text="這張帳單的狀況如下")]),
        registry=_registry(call_results=[
            ToolResult(ok=True, data={"facts": "帳單 756248 應繳 3200 元。"},
                       provenance=_prov("帳單 756248 應繳 3200 元。"))]),
    )
    return rt, _identity(), "756248", {}, {}


def _s_pre_lookup_keyword_carry():
    rt = _runtime(
        provider=FakeProvider([_final(text="這個物件的資料如下")]),
        registry=_registry(call_results=[
            ToolResult(
                ok=True,
                data={"facts": "物件 台科電 位於台北。",
                      "scope": {"estate_id": "456400", "name": "台科電"}},
                provenance=_prov("物件 台科電 位於台北。"),
            )]),
    )
    return rt, _identity(), "台科電", {}, {}


def _s_recent_refs():
    state = {"agent": {"dialog": [
        {"role": "user", "content": "756248 這張怎麼了"},
        {"role": "assistant", "content": "帳單 756248 已經逾期。"},
    ]}}
    rt = _runtime(provider=FakeProvider([_final(text="我先確認你說的那一筆")]))
    return rt, _identity(), "那張後來怎麼樣了呢", state, {}


def _s_completed_actions():
    state = {"agent": {COMPLETED_ACTIONS_KEY: [
        {"ref_type": "repair", "ref_id": "12345", "estate_id": None,
         "estate_name": "測試物件"},
    ]}}
    rt = _runtime(provider=FakeProvider([_final(text="剛才那張單已經建立了")]))
    return rt, _identity(), "剛剛那張報修單處理得怎麼樣", state, {}


def _s_image_turn():
    rt = _runtime(provider=FakeProvider([_final(text="照片收到了")]))
    image = ImageTurnInput(status="ok", facts="照片顯示浴室天花板有水漬，共 1 張。",
                           processed=1, total=1, suggested_category="漏水",
                           suggested_item="天花板", suggested_reason="滲水",
                           suggested_description="天花板出現水漬")
    return rt, _identity(), "這是照片", {}, {"image": image}


def _s_image_with_estate_carry():
    state = {"agent": {ESTATE_CARRY_KEY: {"name": "基隆獨立共生公寓", "id": "456400"}}}
    rt = _runtime(provider=FakeProvider([_final(text="照片與物件都收到了")]))
    image = ImageTurnInput(status="ok", facts="照片顯示牆面剝落，共 1 張。",
                           processed=1, total=1)
    return rt, _identity(), "這是剛剛講的那一戶的照片", state, {"image": image}


def _s_document_turn():
    rt = _runtime(provider=FakeProvider([_final(text="文件內容已讀取")]))
    doc = DocumentTurnInput(status="ok", kind="bill_receipt",
                            facts="開立單位：台電。金額：1200。", pages_seen=1, pages_total=1)
    return rt, _identity(), "這份收據幫我看一下", {}, {"document": doc}


def _s_handoff_cache_replay():
    msg = "你們有什麼保證嗎"
    state = {"agent": {"handoff_cache": {_cache_key(msg): {
        "answer": "已為你轉真人客服，請稍候。",
        "handoff": {"reason": "sensitive_no_grounding", "fact_class": "pricing",
                    "channel": "line", "message": "已為你轉真人客服，請稍候。"},
        "quick_replies": [],
        "trace_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }}}}
    return _runtime(), _identity(), msg, state, {}


def _s_gate_scope_exit():
    state = {"agent": {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "456400"}}}
    rt = _runtime(
        provider=FakeProvider([_tool_call("jgb2.query.bills", {"ref": "900002"}),
                               _final(text="這一筆的狀況如下")]),
        registry=_registry(call_results=[
            ToolResult(ok=True,
                       data={"facts": "別戶的帳單。", "scope": {"estate_id": "999999"}},
                       provenance=_prov("別戶的帳單。"),
                       text_for_model="別戶的帳單。")]),
    )
    return rt, _identity(), "900002 這張怎麼樣了", state, {}


def _s_gate_handoff_without_lookup():
    rt = _runtime(provider=FakeProvider([
        _final(kind="handoff", text="", fact_class="feature", handoff_reason="no_grounding"),
    ]))
    return rt, _identity(), "幫我看一下這件事情要怎麼處理", {}, {}


def _s_gate_ask_target():
    rt = _runtime(provider=FakeProvider([
        _final(kind="ask", text="你要問哪一件事", ask_target=None)]))
    return rt, _identity(), "我有個問題想請教一下", {}, {}


def _s_gate_handoff_no_data():
    rt = _runtime(
        provider=FakeProvider([_tool_call("jgb2.query.bills", {"ref": "900003"}),
                               _final(kind="handoff", text="", fact_class="feature",
                                      handoff_reason="no_grounding")]),
        registry=_registry(call_results=[
            ToolResult(ok=True, data={"facts": ""}, text_for_model="")]),
    )
    return rt, _identity(), "900003 這張帳單的狀況", {}, {}


def _s_gate_handoff_no_judgement():
    """有資料的 `no_grounding` ⇒ 迴圈內改寫用罄後仍轉人 ⇒ NO_JUDGEMENT 出口。"""
    rt = _runtime(
        provider=FakeProvider([
            _tool_call("kb.get", {"kb_id": "1"}),
            _final(kind="handoff", text="", fact_class="feature", handoff_reason="no_grounding"),
            _final(kind="handoff", text="", fact_class="feature", handoff_reason="no_grounding"),
            _final(kind="handoff", text="", fact_class="feature", handoff_reason="no_grounding"),
        ]),
        registry=_registry(call_results=[
            ToolResult(ok=True, data={"id": 1}, text_for_model="有內容的工具原文")]),
    )
    return rt, _identity(), "你覺得我該不該催他繳款", {}, {}


def _s_budget_exhausted_fixed():
    """deadline 命中 ⇒ `_build_fixed` 固定句出口。"""
    clock = FakeClock(start=0.0)

    def _slow(_kwargs):
        clock.advance(100.0)
        return _tool_call("kb.get", {"kb_id": "1"})

    rt = AgentRuntime(
        FakeProvider([_slow, _final(text="不該走到這裡")]),
        _registry(call_results=[ToolResult(ok=True, data={"id": 1}, text_for_model="x")]),
        GoldenVerifier(), FakeAssembler(), Budget(deadline_s=5.0),
        stage="M1", clock=clock, model="golden-model",
    )
    return rt, _identity(), "幫我查一下這個東西", {}, {}


def _s_confirm_card():
    confirm_result = ToolResult(ok=True, data={
        "pending_id": _PID, "action": "bill_due_extend", "payload": dict(_PAYLOAD),
        "card": _CARD,
        "quick_replies": [{"label": "✅ 確認送出", "value": f"confirm_submit:{_PID}"}],
    })
    rt = _runtime(
        provider=FakeProvider([_fake_response(_fake_message(tool_calls=[
            _fake_tool_call("confirm.request",
                            {"summary": "模型摘要", "payload": json.dumps(_PAYLOAD)})]))]),
        registry=_registry(call_results=[confirm_result]),
    )
    return rt, _identity(), "900001 逾期了，幫我延 3 天", {}, {}


def _s_confirm_submit_redeemed():
    rt = _runtime(
        registry=_registry(call_results=[
            ToolResult(ok=True, data={"receipt": {"id": "BILL-77"}})]),
        pool=FakePool([_redeem_row()]),
    )
    return rt, _identity(), f"confirm_submit:{_PID}", _pending_state(), {}


def _s_confirm_cancel():
    rt = _runtime(pool=FakePool([_redeem_row()]))
    return rt, _identity(), f"confirm_cancel:{_PID}", _pending_state(), {}


def _s_confirm_unknown_pid():
    rt = _runtime(pool=FakePool([]))
    return rt, _identity(), "confirm_submit:" + "a" * 16, {"agent": {}}, {}


def _s_select_hit():
    rt = _runtime(registry=_registry(call_results=[
        ToolResult(ok=True,
                   data={"facts": "帳單 900001 應繳 3200 元。",
                         "scope": {"estate_id": "456400"}},
                   provenance=_prov("帳單 900001 應繳 3200 元。"))]))
    return rt, _identity(), "select:bill:900001", {}, {}


def _s_select_not_found():
    rt = _runtime(registry=_registry(call_results=[ToolResult(ok=False, error="NO_MATCH")]))
    return rt, _identity(), "select:bill:000000", {}, {}


def _s_document_unreadable():
    doc = DocumentTurnInput(status="failed", kind=None, facts="", pages_seen=0, pages_total=2)
    return _runtime(), _identity(), "這份檔案幫我看", {}, {"document": doc}


def _s_verifier_reject_then_fixed():
    rt = _runtime(
        provider=FakeProvider([_final(text="被拒的答案一"), _final(text="被拒的答案二")]),
        verifier=GoldenVerifier([VerifierVerdict(ok=False, reason="UNCITED_ASSERTION"),
                                 VerifierVerdict(ok=False, reason="UNCITED_ASSERTION")]),
        budget=Budget(max_rewrites=2),
    )
    return rt, _identity(), "有什麼保證可以給我嗎", {}, {}


SCENARIOS: dict = {
    "plain_answer": _s_plain_answer,
    "tool_then_answer": _s_tool_then_answer,
    "entry_context": _s_entry_context,
    "affirmative_carry": _s_affirmative_carry,
    "empty_session_note": _s_empty_session_note,
    "pre_lookup_id_found": _s_pre_lookup_id_found,
    "pre_lookup_keyword_carry": _s_pre_lookup_keyword_carry,
    "recent_refs": _s_recent_refs,
    "completed_actions": _s_completed_actions,
    "image_turn": _s_image_turn,
    "image_with_estate_carry": _s_image_with_estate_carry,
    "document_turn": _s_document_turn,
    "handoff_cache_replay": _s_handoff_cache_replay,
    "gate_scope_exit": _s_gate_scope_exit,
    "gate_handoff_without_lookup": _s_gate_handoff_without_lookup,
    "gate_ask_target": _s_gate_ask_target,
    "gate_handoff_no_data": _s_gate_handoff_no_data,
    "gate_handoff_no_judgement": _s_gate_handoff_no_judgement,
    "budget_exhausted_fixed": _s_budget_exhausted_fixed,
    "confirm_card": _s_confirm_card,
    "confirm_submit_redeemed": _s_confirm_submit_redeemed,
    "confirm_cancel": _s_confirm_cancel,
    "confirm_unknown_pid": _s_confirm_unknown_pid,
    "select_hit": _s_select_hit,
    "select_not_found": _s_select_not_found,
    "document_unreadable": _s_document_unreadable,
    "verifier_reject_then_fixed": _s_verifier_reject_then_fixed,
}


# ---------------------------------------------------------------------------
# 快照與正規化
# ---------------------------------------------------------------------------
def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(v) for v in value)
    return f"<{type(value).__name__}>"


def _normalize_violations(violations: Any) -> list:
    out = []
    for v in list(violations or []):
        s = str(v)
        out.append("replayed_from:<id>" if s.startswith("replayed_from:") else s)
    return out


#: 比對欄位清單（regen 模式會印出來）。
COMPARED_TOP_FIELDS: tuple = ("kind", "answer", "quick_replies", "outcome",
                              "handoff", "ask_target", "trace", "agent_state_keys",
                              "agent_state", "covers")
COMPARED_TRACE_FIELDS: tuple = tuple(f.name for f in dataclasses.fields(TurnTrace))


def _snapshot(result, state: dict, provider) -> dict:
    trace = {}
    for f in dataclasses.fields(TurnTrace):
        value = getattr(result.trace, f.name)
        trace[f.name] = (_normalize_violations(value) if f.name == "violations"
                         else _jsonable(value))
    agent_state = state.get("agent", {})
    return {
        "kind": result.kind,
        "answer": result.answer,
        "quick_replies": _jsonable(result.quick_replies),
        "outcome": _jsonable(result.outcome),
        "handoff": _jsonable(result.handoff),
        "ask_target": getattr(result, "ask_target", None),
        "trace": trace,
        "agent_state_keys": sorted(str(k) for k in agent_state.keys()),
        "agent_state": _jsonable(agent_state),
        "covers": _covers(result, provider),
    }


def _covers(result, provider) -> dict:
    """**由實際觀察導出**的覆蓋標籤，⛔ 不由情境自己宣告。

    保留 id 的證據＝送進模型的訊息裡真的出現了 `[nonce:<id>:source§i]` 標記
    （`prompt_assembler.unit_marker` 的唯一格式）。
    """
    sent = json.dumps([c.get("messages") for c in getattr(provider, "calls", [])],
                      ensure_ascii=False, default=str)
    reserved = [p for p in RESERVED_PREFIXES if f":{p}{FIXED_NONCE[:8]}:" in sent]
    violations = list(result.trace.violations or [])
    gates = []
    if result.answer == runtime_mod.SCOPE_EXIT_TEXT or result.answer.endswith(
        "\n" + runtime_mod.SCOPE_EXIT_TEXT
    ):
        gates.append("scope_exit")
    if "handoff_without_lookup" in violations:
        gates.append("handoff_without_lookup")
    if "ask_target_invalid" in violations:
        gates.append("ask_target_gate")
    if "handoff_no_data" in violations or "handoff_no_judgement" in violations:
        gates.append("handoff_data_exits")
    flows = []
    if any(str(v).startswith("replayed_from:") for v in violations):
        flows.append("cache_replay")
    if result.trace.select_type is not None:
        flows.append("select")
    if (result.outcome or {}).get("state") == "cancelled":
        flows.append("confirm_cancel")
    if result.trace.receipt_id:
        flows.append("confirm_redeem")
    if (result.outcome or {}).get("state") == "confirm_pending":
        flows.append("confirm_card")
    return {"reserved_ids": reserved, "gates": gates, "flows": flows}


async def _run(name: str) -> dict:
    rt, identity, message, state, kwargs = SCENARIOS[name]()
    result = await rt.run_turn(identity, message, state, **kwargs)
    return _snapshot(result, state, rt.provider)


def _matrix(snapshots: dict) -> dict:
    reserved: dict = {p: [] for p in RESERVED_PREFIXES}
    gates: dict = {g: [] for g in ("scope_exit", "handoff_without_lookup",
                                   "ask_target_gate", "handoff_data_exits")}
    flows: dict = {f: [] for f in ("cache_replay", "select", "confirm_cancel",
                                   "confirm_redeem", "confirm_card")}
    for name, snap in snapshots.items():
        covers = snap["covers"]
        for p in covers["reserved_ids"]:
            reserved.setdefault(p, []).append(name)
        for g in covers["gates"]:
            gates.setdefault(g, []).append(name)
        for f in covers["flows"]:
            flows.setdefault(f, []).append(name)
    return {"scenarios": len(snapshots), "reserved_ids": reserved,
            "gates": gates, "flows": flows}


def _print_matrix(matrix: dict) -> None:
    print("\n===== R1 golden 覆蓋矩陣 =====")
    print(f"情境數：{matrix['scenarios']}（Plan §1.3 下限 17）")
    for title, group in (("保留 id", "reserved_ids"), ("出口閘", "gates"), ("流程", "flows")):
        print(f"-- {title} --")
        for key, names in matrix[group].items():
            mark = "OK " if names else "MISS"
            print(f"  {mark} {key:<26} {len(names)}  {', '.join(names) or '（無）'}")


# ---------------------------------------------------------------------------
# 測試
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
@pytest.mark.skipif(not REGEN, reason="[gate] 只在 AGENT_GOLDEN_REGEN=1 時產生 golden")
async def test_regen_golden(capsys):
    snapshots = {name: await _run(name) for name in SCENARIOS}
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(
        json.dumps(snapshots, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with capsys.disabled():
        _print_matrix(_matrix(snapshots))
        print("\n===== 比對欄位 =====")
        print("頂層：" + "、".join(COMPARED_TOP_FIELDS))
        print(f"TurnTrace 全欄位（{len(COMPARED_TRACE_FIELDS)}）："
              + "、".join(COMPARED_TRACE_FIELDS))
        print(f"\n已寫入 {GOLDEN_PATH}")


@pytest.mark.req(_REQ)
@pytest.mark.skipif(REGEN, reason="[gate] regen 模式不比對")
async def test_golden_matches_fixture():
    """整理前後逐位相同——本檔的**唯一收案條件**。"""
    assert GOLDEN_PATH.exists(), (
        f"golden 不存在：{GOLDEN_PATH}；先跑 AGENT_GOLDEN_REGEN=1 產生"
    )
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert set(golden) == set(SCENARIOS), "情境集合與 golden 不一致（⛔ 不得靜默增刪）"
    for name in sorted(SCENARIOS):
        actual = await _run(name)
        assert actual == golden[name], f"情境 {name} 與 golden 不符"


@pytest.mark.req(_REQ)
@pytest.mark.skipif(REGEN, reason="[gate] regen 模式不比對")
async def test_two_consecutive_runs_are_bit_identical():
    """決定性正對照：同一情境連跑兩次逐位相同（否則 golden 本身沒有意義）。"""
    for name in sorted(SCENARIOS):
        first = json.dumps(await _run(name), ensure_ascii=False, sort_keys=True)
        second = json.dumps(await _run(name), ensure_ascii=False, sort_keys=True)
        assert first == second, f"情境 {name} 兩次結果不同 ⇒ 先修不決定性"


@pytest.mark.req(_REQ)
async def test_coverage_matrix_meets_minimums(capsys):
    """覆蓋矩陣（缺一不得收案）：九個保留 id、四道閘、快取重播、確認兌現／取消／清單點選各 ≥1。"""
    snapshots = {name: await _run(name) for name in SCENARIOS}
    matrix = _matrix(snapshots)
    with capsys.disabled():
        _print_matrix(matrix)
    assert matrix["scenarios"] >= 17, matrix["scenarios"]
    missing_ids = [k for k, v in matrix["reserved_ids"].items() if not v]
    assert not missing_ids, f"保留 id 未覆蓋：{missing_ids}"
    missing_gates = [k for k, v in matrix["gates"].items() if not v]
    assert not missing_gates, f"出口閘未覆蓋：{missing_gates}"
    missing_flows = [k for k, v in matrix["flows"].items() if not v]
    assert not missing_flows, f"流程未覆蓋：{missing_flows}"


def _mutate(value: Any) -> Any:
    if value is None:
        return "<mutated>"
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + 1
    if isinstance(value, str):
        return value + "<mutated>"
    if isinstance(value, list):
        return list(value) + ["<mutated>"]
    if isinstance(value, dict):
        return {**value, "<mutated>": True}
    return "<mutated>"


@pytest.mark.req(_REQ)
@pytest.mark.skipif(REGEN, reason="[gate] regen 模式不比對")
async def test_mutation_positive_control():
    """**變異正對照**：比對欄位任一被漏傳／改值，比對必紅。

    ⚠️ 沒有這一條，`test_golden_matches_fixture` 可能只是在比對一份**空殼**——
    例如 `pre_lookup` 根本沒進快照時，漏傳它也不會有人發現。
    """
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    # (a) Plan 指名的那一欄：`pre_lookup` 漏傳（None）必紅。
    name = "pre_lookup_id_found"
    assert golden[name]["trace"]["pre_lookup"] is not None, (
        "正對照不成立：該情境的 golden 本來就沒有 pre_lookup 值"
    )
    mutated = json.loads(json.dumps(golden[name]))
    mutated["trace"]["pre_lookup"] = None
    assert mutated != golden[name]

    # (b) 逐欄掃：`TurnTrace` 每一欄在**至少一個情境**上都能被變異抓到。
    unchecked = []
    for field in COMPARED_TRACE_FIELDS:
        caught = False
        for snap in golden.values():
            before = snap["trace"][field]
            if {**snap["trace"], field: _mutate(before)} != snap["trace"]:
                caught = True
                break
        if not caught:
            unchecked.append(field)
    assert not unchecked, f"這些 trace 欄位變異抓不到（比對可能是空殼）：{unchecked}"

    # (c) 頂層欄位同理。
    snap = golden["confirm_submit_redeemed"]
    for field in ("kind", "answer", "quick_replies", "outcome", "handoff",
                  "ask_target", "agent_state_keys", "agent_state", "covers"):
        assert field in snap, f"比對快照缺欄位 {field}"
        mutated = json.loads(json.dumps(snap))
        mutated[field] = _mutate(snap[field])
        assert mutated != snap, f"欄位 {field} 變異抓不到"
