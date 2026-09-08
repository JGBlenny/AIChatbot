"""unit：Runtime 的確認段守門與確認回合（子 spec `agent-write-tools` W3｜DSP-038）。

離線：假 provider／假 registry／假 pool，⛔ 不接觸真 DB。真 DB 的兌現語義
（單述句競爭、過期、跨 session、token 不外洩）在
`tests/integration/agent/test_confirmation_tokens_req.py`。

守的三件事：
1. **守門順序**：`entry != "mcp"` 或 `readonly_view` ⇒ 整段不執行；訊息必須
   **等值**匹配機器值且該 `pending_id` 在狀態裡。
2. **確認回合**：模型呼叫 `confirm.request` 成功 ⇒ 立刻結束回合、`answer` 逐字
   等於卡、Verifier 不跑。
3. **重送**：同一個 `pending_id` 再送 ⇒ 回同一個結果，⛔ 不重複呼叫寫入工具。
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from services.agent.confirm_card import (
    ACTION_FAILED_TEXT,
    CANCELLED_TEXT,
    CONFIRMATION_REQUIRED_TEXT,
    render as render_card,
)
from services.agent.identity import Identity
from services.agent.runtime import PENDING_CONFIRM_KEY, PENDING_CONFIRM_MAX, AgentRuntime
from services.agent.tools.confirm import pending_id_for, sha256_hex
from services.agent.tools.registry import ToolResult
from services.agent.budget import Budget

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

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R4.2"

_PAYLOAD = {
    "action": "bill_due_extend",
    "bill_id": "900001",
    "date_expire_before": "20260815",
    "days": 3,
    "date_expire_after": "20260818",
}
_CARD = render_card("bill_due_extend", _PAYLOAD)
_TOKEN = "tok-secret-value-must-never-leak-0123456789"
_PID = pending_id_for(_TOKEN)


class FakePool:
    """只實作 `fetchrow`：`redeem_pending` 用得到的唯一方法。

    `rows` 是依序回傳的清單；`None` 代表「UPDATE 沒中」（已兌現／過期／跨 session）。
    """

    def __init__(self, rows):
        self._rows = list(rows)
        self.calls: list[tuple] = []

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows.pop(0) if self._rows else None


def _redeem_row(payload_sha=None, summary_sha=None):
    from services.agent.tools.confirm import payload_digest

    return {
        "token": _TOKEN,
        "payload_sha256": payload_sha or payload_digest(_PAYLOAD),
        "summary_sha256": summary_sha or sha256_hex(_CARD),
    }


def _identity(**overrides) -> Identity:
    base = dict(
        vendor_id=1, target_user="property_manager", mode="b2b",
        api_key_id=1, session_id="mcp:1:1:s1", entry="mcp",
    )
    base.update(overrides)
    return Identity(**base)


def _state_with_pending(**pending_overrides) -> dict:
    pending = {"action": "bill_due_extend", "payload": dict(_PAYLOAD),
               "card_sha256": sha256_hex(_CARD)}
    pending.update(pending_overrides)
    return {"agent": {PENDING_CONFIRM_KEY: {_PID: pending}}}


def _runtime(*, provider=None, registry=None, pool=None, readonly_view=False, verifier=None):
    return AgentRuntime(
        provider or _empty_provider(),
        registry or FakeRegistry(),
        verifier or FakeVerifier(),
        FakeAssembler(),
        Budget(),
        stage="M1",
        clock=FakeClock(),
        db_pool=pool,
        readonly_view=readonly_view,
    )


def _receipt_registry():
    """假 `jgb2.action.bill_due_extend`：回一張 receipt。"""
    return FakeRegistry(
        call_results=[ToolResult(ok=True, data={"receipt": {"id": "BILL-77"}})]
    )


# ---------------------------------------------------------------------------
# 1. 守門：三個條件缺一就不觸發
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
async def test_rest_entry_never_redeems(monkeypatch):
    """① `entry != "mcp"` ⇒ 整段不執行：⛔ 一次 DB 都不碰、⛔ 一次工具都不呼叫。

    正對照組：同一份狀態＋同一句訊息，換成 MCP 身分就兌現得到。
    """
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(provider=FakeProvider([_final_response(answer="模型接手了")]),
                  registry=registry, pool=pool)

    result = await rt.run_turn(_identity(entry="rest"), f"confirm_submit:{_PID}",
                               _state_with_pending())
    assert pool.calls == [], "REST 入口 ⛔ 不得下任何兌現 SQL"
    assert registry.call_args == [], "REST 入口 ⛔ 不得呼叫寫入工具"
    assert result.answer == "模型接手了"     # 照常進模型

    # 正對照組
    ok = await _runtime(registry=_receipt_registry(), pool=FakePool([_redeem_row()])).run_turn(
        _identity(), f"confirm_submit:{_PID}", _state_with_pending()
    )
    assert "2026/08/18" in ok.answer


@pytest.mark.req(_REQ)
async def test_readonly_view_never_redeems():
    """② 影子回合整段不執行（DSP-016：影子與正式共用 session_id）。"""
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(provider=FakeProvider([_final_response(answer="影子的回答")]),
                  registry=registry, pool=pool, readonly_view=True)
    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", _state_with_pending())
    assert pool.calls == [] and registry.call_args == []
    assert result.answer == "影子的回答"


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("message", [
    "好，送出",                       # 自由文字
    "confirm_submit",                 # 裸機器值（無 pid）
    # ⚠️ 「錯 pid（狀態裡沒有）」自 W8 (5) 起改回固定句、不進模型——見
    #    test_unknown_pending_id_returns_fixed_sentence_and_never_reaches_the_model
    f" confirm_submit:{_PID}",        # 前綴空白 ⇒ 不等值
    f"confirm_submit:{_PID} 謝謝",     # 後綴 ⇒ 不等值
    f"confirm_submit:{_PID.upper()}",  # 大寫十六進位 ⇒ 形狀不符
])
async def test_non_machine_values_do_not_trigger(message):
    """③ 等值比對：只要不是**整句**的機器值，⛔ 一律不觸發任何寫入。"""
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(provider=FakeProvider([_final_response(answer="模型接手了")]),
                  registry=registry, pool=pool)
    result = await rt.run_turn(_identity(), message, _state_with_pending())
    assert pool.calls == [], message
    assert registry.call_args == [], message
    assert result.answer == "模型接手了"


# ---------------------------------------------------------------------------
# 2. 確認回合：卡逐字成為 answer、Verifier 不跑
# ---------------------------------------------------------------------------


def _confirm_tool_response():
    return _fake_response(
        _fake_message(tool_calls=[_fake_tool_call("confirm.request", {
            "summary": "模型自己寫的摘要", "payload": json.dumps(_PAYLOAD),
        })])
    )


@pytest.mark.req(_REQ)
async def test_confirm_request_ends_the_turn_with_the_card_verbatim():
    confirm_result = ToolResult(ok=True, data={
        "pending_id": _PID, "action": "bill_due_extend", "payload": dict(_PAYLOAD),
        "card": _CARD,
        "quick_replies": [{"label": "✅ 確認送出", "value": f"confirm_submit:{_PID}"}],
    })
    registry = FakeRegistry(call_results=[confirm_result])
    verifier = FakeVerifier()
    # 腳本只有一步：模型呼叫 confirm.request。若回合沒有立刻結束，
    # 迴圈會再叫一次 provider ⇒ 假 provider 腳本耗盡 ⇒ 斷言失敗（哨兵）。
    rt = _runtime(provider=FakeProvider([_confirm_tool_response()]),
                  registry=registry, verifier=verifier)

    state: dict = {}
    result = await rt.run_turn(_identity(), "900001 逾期了，幫我延 3 天", state)

    assert result.kind == "ask"
    assert result.answer == _CARD                      # 逐字
    assert result.quick_replies == confirm_result.data["quick_replies"]
    assert verifier.calls == [], "確認回合 ⛔ 不跑 Verifier（卡不是模型寫的）"
    assert result.trace.pending_id == _PID
    # 狀態存 `{action, payload, card_sha256}`，⛔ 不存卡原文、⛔ 不存 token
    pending = state["agent"][PENDING_CONFIRM_KEY][_PID]
    assert pending == {"action": "bill_due_extend", "payload": _PAYLOAD,
                       "card_sha256": sha256_hex(_CARD)}
    assert _CARD not in json.dumps(state, ensure_ascii=False)


@pytest.mark.req(_REQ)
async def test_malformed_confirm_data_does_not_end_the_turn():
    """`data` 形狀不符 ⇒ ⛔ 不印半成品的卡，回合照常走完。"""
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"pending_id": _PID})])
    rt = _runtime(
        provider=FakeProvider([_confirm_tool_response(), _final_response(answer="照常回答")]),
        registry=registry,
    )
    state: dict = {}
    result = await rt.run_turn(_identity(), "幫我延 3 天", state)
    assert result.answer == "照常回答"
    assert PENDING_CONFIRM_KEY not in state.get("agent", {})
    assert "confirm_request_data_shape_invalid" in result.trace.violations


@pytest.mark.req(_REQ)
async def test_pending_confirm_is_capped_fifo():
    """狀態跟著 `collected_data` 落 DB ⇒ 筆數必須有上限（比照 handoff_cache）。"""
    rt = _runtime()
    agent_state: dict = {}
    for i in range(PENDING_CONFIRM_MAX + 5):
        pid = f"{i:016x}"
        rt._begin_pending_confirm(
            agent_state,
            {"pending_id": pid, "action": "bill_due_extend",
             "payload": dict(_PAYLOAD), "card": _CARD, "quick_replies": []},
            trace_id="t", start=0.0, user_message="m", tool_calls=[], violations=[],
        )
    pending_all = agent_state[PENDING_CONFIRM_KEY]
    assert len(pending_all) == PENDING_CONFIRM_MAX
    assert f"{0:016x}" not in pending_all          # 最早的被擠掉（FIFO）
    assert f"{PENDING_CONFIRM_MAX + 4:016x}" in pending_all


# ---------------------------------------------------------------------------
# 3. 兌現：正向、雜湊不符、工具失敗、重送、取消
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
async def test_submit_calls_write_tool_with_token_and_stores_receipt():
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=pool)
    state = _state_with_pending()

    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)

    assert result.kind == "answer"
    assert result.answer == "已將帳單 900001 的到期日延至 2026/08/18。（單號 BILL-77）"
    assert result.trace.llm_calls == 0, "兌現段 ⛔ 不進模型"
    assert result.trace.receipt_id == "BILL-77"
    call = registry.call_args[0]
    assert call["name"] == "jgb2.action.bill_due_extend"
    assert call["args"] == {"payload": _PAYLOAD, "confirmation_token": _TOKEN}
    assert call["for_model"] is True and call["readonly_view"] is False
    assert state["agent"][PENDING_CONFIRM_KEY][_PID]["receipt"] == {"id": "BILL-77"}


@pytest.mark.req(_REQ)
async def test_token_never_appears_in_turn_result_state_or_trace():
    """不變量：token 只在 `run_turn` 那一格行程內存活。
    正對照組＝`pending_id` **有**出現（證明這個 grep 看得見東西）。"""
    pool = FakePool([_redeem_row()])
    rt = _runtime(registry=_receipt_registry(), pool=pool)
    state = _state_with_pending()
    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)

    blobs = [
        json.dumps(state, ensure_ascii=False, default=str),
        json.dumps(result.__dict__, ensure_ascii=False, default=str),
        json.dumps(result.trace.__dict__, ensure_ascii=False, default=str),
    ]
    for blob in blobs:
        assert _TOKEN not in blob
    assert any(_PID in blob for blob in blobs), "正對照組：pending_id 應該找得到"


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("row", [
    _redeem_row(payload_sha="0" * 64),   # payload 被換掉
    _redeem_row(summary_sha="0" * 64),   # 卡被換掉
])
async def test_hash_mismatch_refuses_without_calling_the_write_tool(row):
    pool = FakePool([row])
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=pool)
    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", _state_with_pending())
    assert result.answer == CONFIRMATION_REQUIRED_TEXT
    assert registry.call_args == [], "雜湊不符 ⇒ ⛔ 一次工具都不得呼叫"


@pytest.mark.req(_REQ)
async def test_expired_or_used_token_returns_confirmation_required():
    """`redeem_pending` 沒中且狀態裡沒有 receipt ⇒ 固定句。"""
    rt = _runtime(registry=_receipt_registry(), pool=FakePool([None]))
    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", _state_with_pending())
    assert result.answer == CONFIRMATION_REQUIRED_TEXT


@pytest.mark.req(_REQ)
async def test_resend_returns_the_same_receipt_without_calling_the_tool_again():
    """R4.3：重送同一個 pid ⇒ 同一個結果、⛔ 不重複建單。"""
    pool = FakePool([_redeem_row(), None])       # 第二次 UPDATE 沒中（已燒）
    registry = FakeRegistry(call_results=[
        ToolResult(ok=True, data={"receipt": {"id": "BILL-77"}}),
        ToolResult(ok=True, data={"receipt": {"id": "BILL-99"}}),   # ⛔ 不該被用到
    ])
    rt = _runtime(registry=registry, pool=pool)
    state = _state_with_pending()

    first = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    second = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)

    assert second.answer == first.answer
    assert "BILL-99" not in second.answer
    assert len(registry.call_args) == 1, "第二次 ⛔ 不得再呼叫寫入工具"


@pytest.mark.req(_REQ)
async def test_tool_failure_is_reported_honestly_and_recorded():
    pool = FakePool([_redeem_row()])
    registry = FakeRegistry(call_results=[ToolResult(ok=False, error="NO_MATCH")])
    rt = _runtime(registry=registry, pool=pool)
    state = _state_with_pending()
    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert result.answer == ACTION_FAILED_TEXT
    assert state["agent"][PENDING_CONFIRM_KEY][_PID]["receipt"] == {"error": "NO_MATCH"}
    # 重送 ⇒ 回同一句（⛔ 不變成「已完成」）
    again = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert again.answer == ACTION_FAILED_TEXT


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("verb", ["confirm_cancel", "confirm_edit"])
async def test_cancel_and_edit_burn_the_token_without_calling_the_tool(verb):
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=pool)
    state = _state_with_pending()
    result = await rt.run_turn(_identity(), f"{verb}:{_PID}", state)
    assert result.answer == CANCELLED_TEXT
    assert registry.call_args == []
    assert len(pool.calls) == 1, "取消／修改也要把 token 燒掉"
    assert state["agent"][PENDING_CONFIRM_KEY][_PID]["receipt"] == {"cancelled": True}


@pytest.mark.req(_REQ)
async def test_cancel_after_success_does_not_overwrite_the_receipt():
    """先送出、再按取消 ⇒ ⛔ 不得把 receipt 換成「沒有送出」（那是謊報）。"""
    pool = FakePool([_redeem_row(), None])
    rt = _runtime(registry=_receipt_registry(), pool=pool)
    state = _state_with_pending()
    await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    await rt.run_turn(_identity(), f"confirm_cancel:{_PID}", state)
    assert state["agent"][PENDING_CONFIRM_KEY][_PID]["receipt"] == {"id": "BILL-77"}


@pytest.mark.req(_REQ)
async def test_unknown_pending_id_returns_fixed_sentence_and_never_reaches_the_model():
    """W8 (5) 後可達：會話過期、舊列連同 pending 一起作廢，使用者按到舊卡按鈕 ⇒
    機器值格式合法但 pid 不在本 session ⇒ 固定句，⛔ 不進模型（模型會把 pid 念回去，
    實測 L3-H「確認碼 de34…」）、⛔ 不呼叫工具、⛔ 不碰 DB（本 session 沒有這個 token）。
    正對照：同一 pid 在 pending 裡 ⇒ 走原本的兌現路（test_submit_calls_write_tool_…）。"""
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    provider = FakeProvider([_final_response(answer="模型接手了")])
    rt = _runtime(provider=provider, registry=registry, pool=pool)
    state = _state_with_pending()
    state["agent"]["pending_confirm"] = {}          # 過期後：待確認表已隨舊列作廢
    for verb in ("confirm_submit", "confirm_edit", "confirm_cancel"):
        result = await rt.run_turn(_identity(), f"{verb}:{_PID}", state)
        assert result.answer == CONFIRMATION_REQUIRED_TEXT, verb
        assert _PID not in result.answer
    assert pool.calls == []
    assert registry.call_args == []
    assert provider.calls == [] if hasattr(provider, "calls") else True


@pytest.mark.req(_REQ)
async def test_no_db_pool_fails_closed():
    """沒有 pool ⇒ 回固定句，⛔ 不「先呼叫工具再說」。"""
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=None)
    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", _state_with_pending())
    assert result.answer == CONFIRMATION_REQUIRED_TEXT
    assert registry.call_args == []


@pytest.mark.req(_REQ)
async def test_unknown_action_in_state_never_builds_a_tool_name():
    """`agent_state` 是會落 DB 的資料 ⇒ ⛔ 不讓其中的字串決定呼叫哪一支工具。"""
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=pool)
    state = _state_with_pending(action="drop_everything")
    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}", state)
    assert result.answer == CONFIRMATION_REQUIRED_TEXT
    assert registry.call_args == []
