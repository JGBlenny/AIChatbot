"""unit：主線第 3 步 A 片——既有測試改在 `AGENT_WRITE_LIFECYCLE=off` 驗原斷言之後，對應的 **on 版本**。

增補合約（2026-10-19）§4：單元層先前改 off 跑原斷言的各條，交件時逐條列對應 on 版本；沒有就補。
本檔補的是「既有檔案裡沒有現成 on 對應」的那幾條：每條測試名＝原測試名＋`_on`，斷言開關 on
（預設）時的行為——A6 出卡前預檢（有帳單編號 ⇒ 以 viewer 單筆讀那張帳單、由讀到的列重算原／新到期日）、
A3「修改」（燒 token、⛔ 寫 receipt、程式問改哪一項）、A1（出卡保留草稿）。

資料：真 `JGBSystemAPI`＋`JGBMockTransport`（`assistant_demo_vendor4.json`），全部離線；
`_pm()`（role 20151／user 12291）看得到帳單 709744（`date_expire` 20261101，人工查證同
`test_step3_write_lifecycle_req.py` 模組 docstring）。看不到的帳單編號 900001 為負向正對照。
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from services import jgb_system_api as api_mod
from services.agent import write_forms as WF
from services.agent.confirm_card import (
    CANCELLED_TEXT, ConfirmCardError, DATE_BEFORE_TODAY_TEXT, render as render_card,
)
from services.agent.tools import confirm as C
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.confirm import (
    confirm_quick_replies, confirm_request, payload_digest, pending_id_for,
)
from services.agent.agent_session import PENDING_CONFIRM_KEY
from services.jgb import bills as _bills
from services.jgb import fixture_store
from services.jgb.transport import MOCK_WRITE_LOG_ENV, RecordingTransport

from tests.unit.agent.confirm_pool_double import token_pool
from tests.unit.agent import test_runtime_confirm_segment_req as SEG
from tests.unit.agent.test_write_draft_flow_req import (
    FIXTURE, KEELUNG_ESTATE, SCRIPT_D2, _draft, _intent, _main_spy, _out, _pm, _program_records,
    _seed, _turn,
)
from services.agent import runtime as runtime_mod

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-conversation-architecture-step3-A")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


TODAY = date(2026, 10, 17)
BILL = "709744"
BILL_DUE = date(2026, 11, 1)
HIDDEN_BILL = "900001"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)
    monkeypatch.delenv("AGENT_WRITE_DRAFT", raising=False)
    monkeypatch.delenv(WF.WRITE_LIFECYCLE_ENV, raising=False)       # 未設＝on
    monkeypatch.delenv(WF.WRITE_REPLY_PROGRAM_ENV, raising=False)   # B 片：未設＝on
    monkeypatch.delenv("AGENT_STATE_CLAIM_GATE", raising=False)     # B 片：未設＝on
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    assert WF.write_lifecycle_enabled_from_env() is True             # 前提：本檔全部在 on 下跑


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    monkeypatch.delenv(MOCK_WRITE_LOG_ENV, raising=False)
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    fixture_store.load_from(FIXTURE)
    a = api_mod.JGBSystemAPI()
    a._mock_transport = RecordingTransport(a._mock_transport)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", a)
    return a


def _ymd(d: date) -> str:
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


def _fmt(d: date) -> str:
    return f"{d.year:04d}/{d.month:02d}/{d.day:02d}"


def _payload(*, bill: str = BILL, days: int = 7, before: date = BILL_DUE,
             after: date | None = None) -> dict:
    after = after if after is not None else max(before, _bills._today()) + timedelta(days=days)
    return {"action": "bill_due_extend", "bill_id": bill, "date_expire_before": _ymd(before),
            "days": days, "date_expire_after": _ymd(after)}


def _args(payload, summary: str = "延期") -> dict:
    return {"summary": summary, "payload": json.dumps(payload, ensure_ascii=False)}


def _set_today(monkeypatch, d: date) -> None:
    monkeypatch.setattr(_bills, "_today", lambda: d)


def _viewer_reads(api) -> list:
    return [params for _m, path, params in api._mock_transport.calls
            if path.endswith("/bills") and (params or {}).get("bill_id") is not None]


# ════════════════════════════════════════════════════════════════════
# test_session_confirm_tools_req.py 的 7 條
# ════════════════════════════════════════════════════════════════════
async def test_confirm_request_returns_three_machine_values_reusing_engine_constants_on(api):
    from services.form_contract import (
        DEFAULT_QR_LABELS as _LABELS, QR_CANCEL as _CANCEL, QR_EDIT as _EDIT, QR_SUBMIT as _SUBMIT,
    )
    result = await confirm_request(_pm(), _args(_payload()), db_pool=token_pool())
    assert result.ok is True, (result.error, result.text_for_model)
    pid = result.data["pending_id"]
    assert result.data["quick_replies"] == [
        {"label": _LABELS[_SUBMIT], "value": f"confirm_submit:{pid}"},
        {"label": _LABELS[_EDIT], "value": f"confirm_edit:{pid}"},
        {"label": _LABELS[_CANCEL], "value": f"confirm_cancel:{pid}"},
    ]
    assert result.data["quick_replies"] == confirm_quick_replies(pid)
    assert _viewer_reads(api)                                        # on：預檢真的讀了那張帳單


async def test_confirm_request_data_carries_card_action_payload_but_never_token_on(api):
    """on：模型填錯的原／新到期日被 viewer 讀到的列重算；`card`＝render(重算後 payload)，
    summary_sha256＝卡文字雜湊（⛔ 模型 summary）；pending_id 落表（$6）。"""
    pool = token_pool()
    wrong = _payload(before=date(2099, 1, 1), after=date(2099, 1, 8))
    result = await confirm_request(_pm(), _args(wrong, "模型自己寫的摘要（⛔ 不會成為卡）"), db_pool=pool)
    assert result.ok is True
    assert set(result.data) >= {"pending_id", "action", "payload", "card", "quick_replies"}
    assert result.data["payload"]["date_expire_before"] == _ymd(BILL_DUE)       # 重算
    assert result.data["payload"]["date_expire_after"] == _ymd(BILL_DUE + timedelta(days=7))
    assert result.data["card"] == render_card("bill_due_extend", result.data["payload"], today=TODAY)
    insert_args = pool.insert.await_args.args
    assert insert_args[4] == C.sha256_hex(result.data["card"])
    assert insert_args[4] != C.sha256_hex("模型自己寫的摘要（⛔ 不會成為卡）")
    assert insert_args[6] == result.data["pending_id"]


async def test_confirm_request_rejects_payload_without_valid_action_on(api):
    pool = token_pool()
    valid = _payload()
    for payload in (
        {k: v for k, v in valid.items() if k != "action"},
        {**valid, "action": "delete_everything"},
        {**valid, "action": None},
        {k: v for k, v in valid.items() if k != "days"},
    ):
        result = await confirm_request(_pm(), _args(payload), db_pool=pool)
        assert result.ok is False and result.error == "INVALID_INPUT", payload
    assert pool.insert.await_count == 0 and pool.burn.await_count == 0
    ok = await confirm_request(_pm(), _args(valid), db_pool=pool)     # 正對照：形狀正確就會過
    assert ok.ok is True


async def test_confirm_request_never_returns_the_token_on(api):
    pool = token_pool()
    result = await confirm_request(_pm(), _args(_payload(), "確認送出"), db_pool=pool)
    insert_args = pool.insert.await_args.args
    token = insert_args[1]
    assert isinstance(token, str) and len(token) >= 40                # 正對照：token 真的寫進表
    assert insert_args[3] == payload_digest(result.data["payload"])
    assert insert_args[6] == pending_id_for(token)
    assert token not in result.model_dump_json()
    assert result.data["pending_id"] == pending_id_for(token)
    assert result.provenance == []


async def test_confirm_request_rejects_malformed_input_on(api):
    pool = token_pool()
    valid = json.dumps(_payload())
    for args in (
        {"summary": "", "payload": valid},
        {"summary": "   ", "payload": valid},
        {"summary": 1, "payload": valid},
        {"summary": "ok", "payload": _payload()},
        {"summary": "ok", "payload": "not-json"},
        {"summary": "ok", "payload": "[1, 2]"},
        {"summary": "ok", "payload": json.dumps("just a string")},
        {"summary": "ok", "payload": "x" * 8001},
        {"summary": "ok", "payload": "{}"},
    ):
        result = await confirm_request(_pm(), args, db_pool=pool)
        assert result.ok is False and result.error == "INVALID_INPUT", args
    assert pool.insert.await_count == 0 and pool.burn.await_count == 0
    ok = await confirm_request(_pm(), {"summary": "ok", "payload": valid}, db_pool=pool)
    assert ok.ok is True


async def test_confirm_request_digest_matches_redeem_side_object_digest_on(api, monkeypatch):
    """字串進、dict 出：存進 DB 的雜湊＝兌現端對（預檢重算後）dict 算的雜湊；鍵序／空白不影響。"""
    # 第二句斷言寫死的是改前 payload（「選對紀錄」片 on 時預檢另寫系統顯示鍵 `sys_pick_display`；
    # on 的雜湊往返由 test_pick_right_record_req 驗）。
    monkeypatch.setenv(WF.PICK_RIGHT_ENV, "off")
    pool = token_pool()
    payload = dict(reversed(list(_payload().items())))
    result = await confirm_request(_pm(), {"summary": "s", "payload": json.dumps(payload, indent=1)},
                                   db_pool=pool)
    assert pool.insert.await_args.args[3] == payload_digest(result.data["payload"])
    assert payload_digest(result.data["payload"]) == payload_digest(_payload())


async def test_confirm_request_requires_session_id_on(api):
    pool = token_pool()
    from dataclasses import replace
    ident = replace(_pm(), session_id="")
    assert not ident.session_id and _pm().session_id                   # 前提：只差 session_id
    result = await confirm_request(ident, _args(_payload()), db_pool=pool)
    assert result.ok is False and result.error == "INVALID_INPUT"
    assert pool.insert.await_count == 0 and pool.burn.await_count == 0


# ════════════════════════════════════════════════════════════════════
# test_confirm_date_gate_req.py 的 5 條、test_due_extend_base_req.py 的 1 條
# ════════════════════════════════════════════════════════════════════
async def test_confirm_request_rejects_a_past_new_due_date_and_writes_no_pending_row_on(api):
    """on：有編號的延期卡，模型給的「過去的新到期日」被讀到的列重算 ⇒ 卡上新到期日＝起算日＋days
    （不在過去）；看不到的帳單 ⇒ 查無固定句、⛔ 落 pending 列。"""
    pool = token_pool()
    past = _payload(after=TODAY - timedelta(days=7))
    result = await confirm_request(_pm(), _args(past, "延 7 天"), db_pool=pool)
    assert result.ok is True
    assert f"・新到期日：{_fmt(BILL_DUE + timedelta(days=7))}" in result.data["card"]
    assert result.data["payload"]["date_expire_after"] > _ymd(TODAY)
    hidden_pool = token_pool()
    hidden = await confirm_request(_pm(), _args(_payload(bill=HIDDEN_BILL)), db_pool=hidden_pool)
    nf = C._not_found_result()
    assert (hidden.ok, hidden.error, hidden.text_for_model) == (nf.ok, nf.error, nf.text_for_model)
    assert hidden_pool.insert.await_count == 0 and hidden_pool.burn.await_count == 0


@pytest.mark.parametrize("delta", [0, 1, 30])
async def test_today_or_later_still_issues_the_card_on(api, monkeypatch, delta):
    """on：原到期日（讀到的列）＝今天＋delta ⇒ 照常出卡，卡逐字＝render(重算後 payload, today)。"""
    today = BILL_DUE - timedelta(days=delta)
    _set_today(monkeypatch, today)
    pool = token_pool()
    result = await confirm_request(_pm(), _args(_payload(days=3)), db_pool=pool)
    assert result.ok is True
    assert result.data["card"] == render_card("bill_due_extend", result.data["payload"], today=today)
    assert pool.insert.await_count == 1


async def test_an_overdue_original_due_date_is_not_a_reason_to_refuse_on(api, monkeypatch):
    today = BILL_DUE + timedelta(days=3)                              # 原到期日已逾期 3 天
    _set_today(monkeypatch, today)
    pool = token_pool()
    result = await confirm_request(_pm(), _args(_payload(days=3)), db_pool=pool)
    assert result.ok is True and pool.insert.await_count == 1
    assert result.data["payload"]["date_expire_after"] == _ymd(today + timedelta(days=3))
    assert f"・起算日：{_fmt(today)}" in result.data["card"]


async def test_confirm_request_issues_the_card_for_an_overdue_bill_on(api, monkeypatch):
    """test_due_extend_base_req 那一題的 on 版本：原到期日（列上）11/01、今天 11/09、延三天
    ⇒ 出卡、新到期日 11/12、起算日 11/09；卡逐字＝同一時鐘下的 render。"""
    today = date(2026, 11, 9)
    _set_today(monkeypatch, today)
    pool = token_pool()
    result = await confirm_request(_pm(), _args(_payload(days=3), "延三天"), db_pool=pool)
    assert result.ok is True and pool.insert.await_count == 1
    card = result.data["card"]
    assert f"・起算日：{_fmt(today)}" in card and f"・新到期日：{_fmt(date(2026, 11, 12))}" in card
    assert card == render_card("bill_due_extend", result.data["payload"], today=today)


async def test_render_failure_is_distinguishable_from_the_date_gate_on(api, monkeypatch):
    """on：缺帳單編號的延期 payload 不預檢（沒有編號可讀）⇒ render 失敗 `text_for_model==""`；
    正對照：閘一換成一律擋 ⇒ 同一張看得到的帳單帶 `DATE_BEFORE_TODAY_TEXT`、⛔ 落列。"""
    pool = token_pool()
    broken = {k: v for k, v in _payload().items() if k != "bill_id"}
    result = await confirm_request(_pm(), _args(broken), db_pool=pool)
    assert result.ok is False and result.error == "INVALID_INPUT"
    assert result.text_for_model == ""
    assert pool.insert.await_count == 0 and pool.burn.await_count == 0
    monkeypatch.setattr(C, "fields_before_today", lambda action, payload, today: ["date_expire_after"])
    gate_pool = token_pool()
    gated = await confirm_request(_pm(), _args(_payload()), db_pool=gate_pool)
    assert gated.ok is False and gated.error == "INVALID_INPUT"
    assert gated.text_for_model == DATE_BEFORE_TODAY_TEXT
    assert gate_pool.insert.await_count == 0 and gate_pool.burn.await_count == 0


async def test_unmarked_action_is_completely_unaffected_on(api, monkeypatch):
    """on：時鐘換到 2099 ⇒ 修繕（無預檢、無日期欄）照常出卡；有編號的延期卡在 on 時由讀到的列＋
    當下時鐘重算（起算日＝2099/01/01），不再因模型算的日期與時鐘不一致而擋。"""
    far = date(2099, 1, 1)
    _set_today(monkeypatch, far)
    pool = token_pool()
    repair = {"action": "repair_create", "estate_name": KEELUNG_ESTATE, "description": "門鎖壞了"}
    result = await confirm_request(_pm(), _args(repair, "開修繕單"), db_pool=pool)
    assert result.ok is True and pool.insert.await_count == 1
    assert result.data["card"] == render_card("repair_create", result.data["payload"])
    bill = await confirm_request(_pm(), _args(_payload(before=BILL_DUE, after=BILL_DUE + timedelta(days=3),
                                                       days=3)), db_pool=token_pool())
    assert bill.ok is True
    assert f"・起算日：{_fmt(far)}" in bill.data["card"]
    assert bill.data["payload"]["date_expire_after"] == _ymd(far + timedelta(days=3))


# ════════════════════════════════════════════════════════════════════
# test_bill_period_resolve_req.py 的 1 條
# ════════════════════════════════════════════════════════════════════
async def test_bill_id_present_never_touches_resolver_on(api, monkeypatch):
    """on：有帳單編號 ⇒ 期別解析一步都不查（只做宣告的單筆可見性讀取）；出卡、hint 空。"""
    called = []

    async def _boom(*a, **kw):
        called.append(a)
        raise AssertionError("有 bill_id 時 ⛔ 不得去查帳單清單（期別解析）")

    monkeypatch.setattr(C, "_bills_of_estate", _boom)
    result = await confirm_request(_pm(), _args(_payload(days=3)), db_pool=token_pool())
    assert result.ok is True
    assert result.data["payload"]["bill_id"] == BILL
    assert result.data["hint"] == ""
    assert called == []
    assert [p.get("bill_id") for p in _viewer_reads(api)] == [BILL]


# ════════════════════════════════════════════════════════════════════
# test_runtime_confirm_segment_req.py 的 2 條（×2 參數）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("verb", ["confirm_cancel", "confirm_edit"])
async def test_cancel_and_edit_burn_the_token_without_calling_the_tool_on(verb):
    """on：取消＝現行（CANCELLED_TEXT、receipt cancelled）；修改（A3）＝燒 token、⛔ 呼叫寫入工具、
    ⛔ 寫 receipt、程式問改哪一項（`edit_ask_text`）。"""
    pool = SEG.FakePool([SEG._redeem_row()])
    registry = SEG._receipt_registry()
    rt = SEG._runtime(registry=registry, pool=pool)
    state = SEG._state_with_pending()
    entry = state["agent"][PENDING_CONFIRM_KEY][SEG._PID]
    result = await rt.run_turn(SEG._identity(), f"{verb}:{SEG._PID}", state)
    assert registry.call_args == []
    assert len(pool.calls) == 1, "取消／修改都要把 token 燒掉"
    if verb == "confirm_cancel":
        assert result.answer == CANCELLED_TEXT
        assert entry["receipt"] == {"cancelled": True}
    else:
        assert result.answer == WF.edit_ask_text(entry["action"], entry["payload"])
        assert result.answer != CANCELLED_TEXT
        assert "receipt" not in entry and entry.get("invalidated") is True


@pytest.mark.parametrize("verb", ["confirm_cancel", "confirm_edit"])
async def test_outcome_cancelled_on_cancel_or_edit_on(verb):
    pool = SEG.FakePool([SEG._redeem_row()])
    rt = SEG._runtime(registry=SEG._receipt_registry(), pool=pool)
    result = await rt.run_turn(SEG._identity(), f"{verb}:{SEG._PID}", SEG._state_with_pending())
    if verb == "confirm_cancel":
        assert result.outcome["state"] == "cancelled" and result.outcome["expects"] == "none"
    else:
        assert result.outcome["state"] == "clarifying" and result.outcome["expects"] == "text"
    assert result.outcome["action"] == "bill_due_extend"


# ════════════════════════════════════════════════════════════════════
# test_write_draft_flow_req.py 的 3 條（A4 那條的 on 對應在 step3 #6，見交件對照表）
# ════════════════════════════════════════════════════════════════════
async def test_bill_draft_program_trigger_reaches_confirm_pending_on(api):
    """on：同一份草稿經程式觸發得 `confirm_pending`；卡上帳單 709744、延後 7 天、新到期日 11/08；
    A1：出卡**保留**草稿（綁同一動作）；一張 token。"""
    ident = _pm()
    state = _seed(ident, "bill_due_extend", {"estate_name": KEELUNG_ESTATE, "period": "11月那期"},
                  users=["我想把一張帳單延後繳", SCRIPT_D2], asked=["days"])
    res, _reg, provider, pool = await _turn(ident, "延 7 天", state, [_out()],
                                            intents=[_intent("bill_due_extend", days="7")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・帳單編號：709744" in res.answer and "・延後天數：7 天" in res.answer
    assert "・新到期日：2026/11/08" in res.answer
    assert "write_draft_program_confirm" in res.trace.violations
    assert len(_program_records(res)) == 1 and len(provider.calls) == 1
    assert _draft(state) is not None and _draft(state)["action"] == "bill_due_extend"
    pool.insert.assert_called_once()


def _render_boom(monkeypatch):
    def _boom(*_a, **_k):
        raise ConfirmCardError("injected")
    monkeypatch.setattr(C, "render", _boom)


async def test_nonterminal_program_result_goes_back_to_model_once_on(api, monkeypatch):
    """on：「帳單 709744 延 7 天」在 on 時預檢補齊日期、本來會出卡——以注入讓 render 失敗，製造同一種
    非終結結果（無缺欄清單的 INVALID_INPUT；本回合沒有 A2 燒卡）⇒ 工具結果回填、再叫一次模型。
    B 片開關 off（改前行為）：on 時非問句寫入情境回合改由程式狀態回話結束（B1），見
    `test_b_write_replies_program_req.py` V3。"""
    monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")
    _render_boom(monkeypatch)
    res, reg, provider, _ = await _turn(_pm(), "帳單 709744 延 7 天", {}, [
        _out(),
        _out("請問要延後幾天？", kind="ask", ask_target="date"),
    ], intents=[_intent("bill_due_extend", bill_id="709744", days="7")])
    (args, first), = reg.confirm_calls()
    assert json.loads(args["payload"]) == {"action": "bill_due_extend", "bill_id": 709744, "days": 7}
    assert (first.ok, first.error, first.data) == (False, "INVALID_INPUT", None)
    assert "write_draft_program_confirm_nonterminal" in res.trace.violations
    assert WF.V_REISSUE_NOT_ISSUED not in res.trace.violations
    assert len(provider.calls) == 2 and len(_program_records(res)) == 1
    assert len(provider.intent_calls) == 1
    assert res.answer == "請問要延後幾天？"


async def test_w1c_program_first_nonterminal_result_calls_main_model_once_with_the_result_on(
        api, monkeypatch):
    # B 片開關 off（改前行為）：on 時程式先發非終結即由程式狀態回話結束（B1），見
    # `test_b_write_replies_program_req.py` V3。
    monkeypatch.setenv(WF.WRITE_REPLY_PROGRAM_ENV, "off")
    _render_boom(monkeypatch)
    events: list = []
    res, reg, provider, _ = await _turn(_pm(), "帳單 709744 延 7 天", {}, [
        _main_spy(events, _out("請問要延後幾天？", kind="ask", ask_target="date"))],
        intents=[_intent("bill_due_extend", bill_id="709744", days="7")], program_first=True)
    (_args_, first), = reg.confirm_calls()
    assert (first.ok, first.error, first.data) == (False, "INVALID_INPUT", None)
    assert events == [("main", True)]
    tool_msgs = [m for m in provider.calls[0]["messages"]
                 if str(m.get("tool_call_id", "")).startswith(runtime_mod.WRITE_DRAFT_PROGRAM_ID_PREFIX)]
    assert len(tool_msgs) == 1 and tool_msgs[0]["role"] == "tool"
    assert res.trace.violations.count("write_draft_program_confirm") == 1
    assert len(_program_records(res)) == 1 and res.trace.llm_calls == 1
    assert res.answer == "請問要延後幾天？"
