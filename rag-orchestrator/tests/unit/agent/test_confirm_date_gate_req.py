"""unit：確認卡的**日期有效性閘門**（Plan S1／line-bot 走查 H1；DSP-038-2 契約層）。

治的病灶：`bill_due_extend` 只驗 `date_expire_before + days == date_expire_after`，
一組**彼此自洽的過去日期**照樣出得了卡、兌現得了（走查實測：9/04 的到期日還能延）。
「不得早於今天」是這一欄的**語義**，落在契約層：

    confirm_card.CONFIRM_FIELD_ATTRS        欄位屬性表（action → 欄位 → 屬性）
    confirm_card.date_not_before_today      唯一判定（純函式，⛔ 不讀時鐘）
    bills._today()                          唯一時鐘（兩個呼叫點各自在呼叫點取值）
    tools/confirm.confirm_request           閘一：出卡前（render 之後）
    runtime._run_confirm_segment            閘二：兌現前（兩把雜湊比對之後）

本檔驗的五件事：
1. `date_not_before_today` 昨天／今天／明天三態；
2. 表的自洽：鍵 ⊆ `CONFIRM_ACTIONS`、屬性 ⊆ `CONFIRM_FIELD_ATTR_NAMES`、
   被標記的欄位確實是該 action 的 render 會解析的日期欄位；
3. 閘一：過去日 ⇒ `INVALID_INPUT`＋`DATE_BEFORE_TODAY_TEXT`、**⛔ 不落 pending 列**；
4. 閘二：兌現時的過去日 ⇒ **⛔ 不呼叫寫入工具**、`ACTION_FAILED_TEXT`、
   trace 有 `date_before_today_at_redeem`、`outcome.state == "failed"`；
5. 表裡**沒有**標記的動作（`repair_create`）行為完全不變。

⚠️ 每個「被擋下／沒被呼叫」的斷言旁都有**正對照組**（同一組裝置只把日期或時鐘換到
   未來就會出卡／就會呼叫寫入工具）——閘門若因為裝置壞掉而「全部擋下」，正對照組
   會先紅，⛔ 不會被誤讀成「閘門有效」。
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from services.agent.confirm_card import (
    ACTION_FAILED_TEXT,
    CONFIRM_ACTIONS,
    CONFIRM_FIELD_ATTR_NAMES,
    CONFIRM_FIELD_ATTRS,
    DATE_BEFORE_TODAY_TEXT,
    NOT_BEFORE_TODAY,
    ConfirmCardError,
    date_not_before_today,
    fields_before_today,
    render,
)
from services.agent.tools.confirm import confirm_request
from services.jgb import bills

# 兌現段的裝置沿用既有那一檔（⛔ 不另抄一份假 pool／假 registry）。
# ⚠️ 該檔的 `_freeze_today` 是**模組層** autouse fixture，⛔ 不會跟著 import 過來——
#    本檔每一條案例自己設時鐘，這正是要驗的變因。
from tests.unit.agent.test_runtime_confirm_segment_req import (
    _PAYLOAD as _REDEEM_PAYLOAD,
    _PID,
    FakePool,
    _identity as _mcp_identity,
    _receipt_registry,
    _redeem_row,
    _runtime,
    _state_with_pending,
)

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R4.2"

#: 本檔的固定「今天」。⛔ 不用 `date.today()`——測試自己讀時鐘，就沒有東西在驗時鐘。
_TODAY = date(2026, 9, 9)


def _ymd(value: date) -> str:
    return f"{value.year:04d}{value.month:02d}{value.day:02d}"


def _bill_due_extend_payload(base: date, *, days: int = 3) -> dict:
    """`date_expire_after` ＝ `base + days`（render 的驗算契約必須成立）。"""
    return {
        "action": "bill_due_extend",
        "bill_id": "900001",
        "date_expire_before": _ymd(base),
        "days": days,
        "date_expire_after": _ymd(base + timedelta(days=days)),
    }


def _v3_payload(before: date, *, today: date = _TODAY, days: int = 3) -> dict:
    """V3 的正確 payload：`date_expire_after` ＝ **起算日**（原到期日與今天較晚者）＋ days。

    ⚠️ 與 `_bill_due_extend_payload` 的差別就是 V3 改掉的那一條：後者以原到期日
    起算（`today` 缺省時的舊行為），本函式以起算日起算。
    """
    return {
        "action": "bill_due_extend",
        "bill_id": "900001",
        "date_expire_before": _ymd(before),
        "days": days,
        "date_expire_after": _ymd(max(before, today) + timedelta(days=days)),
    }


def _repair_create_payload(base: date) -> dict:
    """⛔ 不填 `category_name`：缺值放行（delta4），因此不會去打分類樹 API。"""
    return {"action": "repair_create", "estate_name": "信義好宅", "description": ""}


#: 每個 action 一份「日期都合法」的 payload 工廠。新增 action 時本檔會先紅，
#: ⛔ 不讓「新動作沒人驗它的日期欄位」靜悄悄地過。
_PAYLOAD_FACTORIES = {
    "bill_due_extend": _bill_due_extend_payload,
    "repair_create": _repair_create_payload,
}


def _identity():
    from services.agent.identity import Identity

    return Identity(vendor_id=1, target_user="property_manager", mode="b2b",
                    api_key_id=1, session_id="mcp:1:1:s1", entry="mcp")


def _confirm_pool():
    """`confirm.request` 只用 `execute`（INSERT token 列）。"""
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    return pool


# ---------------------------------------------------------------------------
# 1. 判定本身：昨天／今天／明天
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("delta,expected", [(-1, False), (0, True), (1, True)])
def test_date_not_before_today_yesterday_today_tomorrow(delta, expected):
    """**今天算通過**（邊界含當日）；昨天不通過。"""
    value = _ymd(_TODAY + timedelta(days=delta))
    assert date_not_before_today(value, _TODAY) is expected
    # `_parse_date` 兩種形狀都收（jgb2 的日期欄位 int／str 都出現過）
    assert date_not_before_today(int(value), _TODAY) is expected


@pytest.mark.req(_REQ)
def test_date_not_before_today_is_pure_and_never_reads_the_clock(monkeypatch):
    """判定只看傳進來的 `today`：把 `bills._today` 換掉 ⛔ 不影響它。"""
    monkeypatch.setattr(bills, "_today", lambda: date(2099, 1, 1))
    assert date_not_before_today(_ymd(_TODAY), _TODAY) is True
    assert date_not_before_today(_ymd(_TODAY - timedelta(days=1)), _TODAY) is False


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("bad", [None, "", "2026-09-09", "20261301", 20260931, True, [], "abc"])
def test_unreadable_values_are_blocked_not_waved_through(bad):
    """讀不出來的值 ⇒ **fail-closed**：判定拋、helper 折成「擋下」。

    正對照組：同一支 helper 對合法的未來日期回空清單（證明它不是無條件擋）。
    """
    with pytest.raises(ConfirmCardError):
        date_not_before_today(bad, _TODAY)
    payload = {**_bill_due_extend_payload(_TODAY), "date_expire_after": bad}
    assert fields_before_today("bill_due_extend", payload, _TODAY) == ["date_expire_after"]
    assert fields_before_today("bill_due_extend", _bill_due_extend_payload(_TODAY), _TODAY) == []


# ---------------------------------------------------------------------------
# 2. 表的自洽（(a) 鍵、(b) 欄位真的存在於 render、(c) 屬性值域）
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
def test_table_keys_are_a_subset_of_confirm_actions():
    assert CONFIRM_FIELD_ATTRS, "空表 ⇒ 兩道閘什麼都不擋（正對照組：表必須非空）"
    assert set(CONFIRM_FIELD_ATTRS) <= set(CONFIRM_ACTIONS)


@pytest.mark.req(_REQ)
def test_every_attribute_value_is_a_known_attribute():
    """(c) 屬性 ⊆ 已知值域——表裡寫一個沒人實作的屬性會靜默地什麼都不擋。"""
    assert NOT_BEFORE_TODAY in CONFIRM_FIELD_ATTR_NAMES
    for fields in CONFIRM_FIELD_ATTRS.values():
        for attrs in fields.values():
            assert attrs, "空屬性集合＝這一欄被列了卻沒有任何約束"
            assert attrs <= CONFIRM_FIELD_ATTR_NAMES


@pytest.mark.req(_REQ)
def test_payload_factories_cover_every_confirm_action():
    """新增 action 時本檔先紅：⛔ 不讓新動作的日期欄位沒有人驗。"""
    assert set(_PAYLOAD_FACTORIES) == set(CONFIRM_ACTIONS)


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("action", sorted(CONFIRM_FIELD_ATTRS))
def test_marked_fields_are_really_render_parsed_date_fields(action):
    """(b) 被標記的欄位＝該 action 的 render 真的會解析的日期欄位。

    證法（⛔ 不靠人工對照）：給合法日期 ⇒ render 成功且不被閘門擋；把那一欄拿掉
    ⇒ render 必拋 `ConfirmCardError`，且 helper 把它算成擋下（fail-closed）。
    """
    payload = _PAYLOAD_FACTORIES[action](_TODAY)
    assert render(action, payload)                                   # 正對照組
    assert fields_before_today(action, payload, _TODAY) == []
    for field in CONFIRM_FIELD_ATTRS[action]:
        missing = {k: v for k, v in payload.items() if k != field}
        with pytest.raises(ConfirmCardError):
            render(action, missing)
        assert fields_before_today(action, missing, _TODAY) == [field]


@pytest.mark.req(_REQ)
def test_helper_iterates_the_table_and_ignores_unlisted_actions():
    """表裡沒有的 action ⇒ 空清單（行為完全不變），⛔ 不是「找不到就擋」。"""
    for action in CONFIRM_ACTIONS:
        if action in CONFIRM_FIELD_ATTRS:
            continue
        payload = _PAYLOAD_FACTORIES[action](_TODAY - timedelta(days=365))
        assert fields_before_today(action, payload, _TODAY) == []
    # 正對照組：表裡有的那一個，同樣一組過去日期就被列出來
    past = _bill_due_extend_payload(_TODAY - timedelta(days=365))
    assert fields_before_today("bill_due_extend", past, _TODAY) == ["date_expire_after"]


# ---------------------------------------------------------------------------
# 3. 閘一：`confirm.request`（render 之後、寫 token 列之前）
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
async def test_confirm_request_rejects_a_past_new_due_date_and_writes_no_pending_row(monkeypatch):
    """**過去的新到期日出不了卡**——V3 之後改由 render 的驗算擋（⛔ 不是閘一）。

    ⚠️ V3 起閘一對 `bill_due_extend` 是**結構上到不了**的：起算日＝max(原到期日,
    今天)、`days` 必為正整數 ⇒ `date_expire_after` 恆 > 今天，沒有任何 payload 能
    同時「驗算過」且「新到期日在過去」。所以這一題的擋點往前移到驗算，
    `text_for_model` 是空字串而不是 `DATE_BEFORE_TODAY_TEXT`。
    閘一本身沒有被刪（縱深，表裡未來的 action 仍走它），它仍在兌現端開火——
    見 `test_redeem_with_a_past_date_never_calls_the_write_tool`。
    """
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    payload = _bill_due_extend_payload(_TODAY - timedelta(days=10))   # 舊算法：after ＝ 今天−7
    pool = _confirm_pool()

    result = await confirm_request(
        _identity(), {"summary": "延三天", "payload": json.dumps(payload)}, db_pool=pool
    )

    assert result.ok is False
    assert result.error == "INVALID_INPUT"          # ⛔ 沿用封閉值域，不新增錯誤碼
    assert result.text_for_model == ""              # 驗算不過（⛔ 不是閘一那一支）
    assert result.data is None
    assert pool.execute.await_count == 0, "⛔ 不落 pending 列（沒有 token 可兌現）"

    # 正對照組①：同一張逾期帳單，改用 V3 的起算日算 ⇒ 出得了卡（證明擋的是算式不是帳單）
    ok_pool = _confirm_pool()
    ok = await confirm_request(
        _identity(),
        {"summary": "延三天",
         "payload": json.dumps(_v3_payload(_TODAY - timedelta(days=10)))},
        db_pool=ok_pool,
    )
    assert ok.ok is True and ok_pool.execute.await_count == 1

    # 正對照組②：閘一的判定本身還活著（純函式層），⛔ 不是被 V3 拿掉了
    assert fields_before_today(
        "bill_due_extend",
        {**payload, "date_expire_after": _ymd(_TODAY - timedelta(days=1))},
        _TODAY,
    ) == ["date_expire_after"]


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("delta", [0, 1, 30])
async def test_today_or_later_still_issues_the_card(monkeypatch, delta):
    """正對照組：今天／明天／一個月後照常出卡，且卡逐字等於 `render`。"""
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    payload = _bill_due_extend_payload(_TODAY + timedelta(days=delta))
    pool = _confirm_pool()

    result = await confirm_request(
        _identity(), {"summary": "延三天", "payload": json.dumps(payload)}, db_pool=pool
    )

    assert result.ok is True
    assert result.data["card"] == render("bill_due_extend", payload)
    assert pool.execute.await_count == 1


@pytest.mark.req(_REQ)
async def test_an_overdue_original_due_date_is_not_a_reason_to_refuse(monkeypatch):
    """`date_expire_before` 在過去 ⇒ **照常出卡**，新到期日以今天起算（V3）。

    走查病灶：原到期日已逾期時，舊算法算出的新到期日仍在過去，使用者只看到
    「不能延」。V3 起 `days` 從「原到期日與今天較晚者」起算 ⇒ 延三天就是今天＋3。
    """
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    payload = _v3_payload(_TODAY - timedelta(days=3), days=3)   # after ＝ 今天＋3
    pool = _confirm_pool()

    result = await confirm_request(
        _identity(), {"summary": "延三天", "payload": json.dumps(payload)}, db_pool=pool
    )

    assert result.ok is True and pool.execute.await_count == 1
    assert payload["date_expire_after"] == _ymd(_TODAY + timedelta(days=3))
    assert f"・起算日：{_TODAY.year:04d}/{_TODAY.month:02d}/{_TODAY.day:02d}" in result.data["card"]


@pytest.mark.req(_REQ)
async def test_render_failure_is_distinguishable_from_the_date_gate(monkeypatch):
    """兩支都是 `INVALID_INPUT`，差別只在 `text_for_model`（render 失敗是空字串）。

    ⚠️ 正對照組**不再用 `bill_due_extend` 的過去日期**：V3 之後那組 payload 連
    驗算都過不了、到不了閘一（見
    `test_confirm_request_rejects_a_past_new_due_date_and_writes_no_pending_row`）。
    改直接對閘一的注入點（`confirm_request` 呼叫的 `fields_before_today`）下手，
    證明那一支確實帶著固定句，⛔ 兩支不得混為一談。
    """
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    broken = {k: v for k, v in _bill_due_extend_payload(_TODAY).items() if k != "bill_id"}
    pool = _confirm_pool()

    result = await confirm_request(
        _identity(), {"summary": "延三天", "payload": json.dumps(broken)}, db_pool=pool
    )

    assert result.ok is False and result.error == "INVALID_INPUT"
    assert result.text_for_model == ""
    assert pool.execute.await_count == 0

    # 正對照組：把閘一的判定換成「一律擋」⇒ 同一組**驗算過得了**的 payload 走到
    # 閘一那一支，帶著固定句、且 ⛔ 不落 pending 列。
    import services.agent.tools.confirm as confirm_mod
    monkeypatch.setattr(confirm_mod, "fields_before_today",
                        lambda action, payload, today: ["date_expire_after"])
    gate_pool = _confirm_pool()
    gated = await confirm_request(
        _identity(),
        {"summary": "延三天", "payload": json.dumps(_v3_payload(_TODAY))},
        db_pool=gate_pool,
    )
    assert gated.ok is False and gated.error == "INVALID_INPUT"
    assert gated.text_for_model == DATE_BEFORE_TODAY_TEXT
    assert gate_pool.execute.await_count == 0


@pytest.mark.req(_REQ)
async def test_unmarked_action_is_completely_unaffected(monkeypatch):
    """正對照組：表裡沒有 `repair_create` ⇒ 時鐘怎麼設都不影響它。"""
    far_future = date(2099, 1, 1)
    monkeypatch.setattr(bills, "_today", lambda: far_future)
    payload = _repair_create_payload(_TODAY)
    pool = _confirm_pool()

    result = await confirm_request(
        _identity(), {"summary": "開修繕單", "payload": json.dumps(payload)}, db_pool=pool
    )

    assert result.ok is True
    assert result.data["card"] == render("repair_create", payload)
    assert pool.execute.await_count == 1
    assert fields_before_today("repair_create", payload, far_future) == []
    # 同一個時鐘下，`bill_due_extend` 會被擋（證明時鐘真的被換掉了）：以 `_TODAY`
    # 為起算日算出來的 payload，在 2099 的時鐘下起算日變成 2099 ⇒ 驗算不一致。
    blocked = await confirm_request(
        _identity(),
        {"summary": "延三天", "payload": json.dumps(_v3_payload(_TODAY))},
        db_pool=_confirm_pool(),
    )
    assert blocked.ok is False and blocked.error == "INVALID_INPUT"
    # 反向正對照組：把時鐘調回 `_TODAY`，同一份 payload 就出得了卡
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    ok_pool = _confirm_pool()
    unblocked = await confirm_request(
        _identity(),
        {"summary": "延三天", "payload": json.dumps(_v3_payload(_TODAY))},
        db_pool=ok_pool,
    )
    assert unblocked.ok is True and ok_pool.execute.await_count == 1


# ---------------------------------------------------------------------------
# 4. 閘二：兌現路徑（`_run_confirm_segment` 的送出分支）
#
# ⚠️ 負向斷言下在 **registry 邊界**（`registry.call_args == []`）而不是替身的
#    `transport._patch_bill`：本層用假 registry，寫入工具根本不會執行，對
#    `_patch_bill` 下的斷言在**兩個臂**都會是空的 ⇒ 那是一條看不見任何東西的
#    瞎斷言。呼叫 `jgb2.action.bill_due_extend` 是 `_patch_bill` 的唯一上游，
#    擋在這裡就是擋在它之前；正對照組（未來日期）證明這條線本來會被呼叫。
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
async def test_redeem_with_a_past_date_never_calls_the_write_tool(monkeypatch):
    # `_REDEEM_PAYLOAD` 的 `date_expire_after` 是 2026/08/18 ⇒ 相對於 _TODAY 已過期
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    assert _REDEEM_PAYLOAD["date_expire_after"] < _ymd(_TODAY)     # 裝置前提
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=pool)
    state = _state_with_pending()

    result = await rt.run_turn(_mcp_identity(), f"confirm_submit:{_PID}", state)

    assert registry.call_args == [], "⛔ 不呼叫 jgb2.action.*（替身 _patch_bill 因此到不了）"
    assert result.answer == ACTION_FAILED_TEXT
    assert "date_before_today_at_redeem" in result.trace.violations
    assert result.outcome["state"] == "failed"
    assert result.trace.tool_calls == []
    assert pool.calls, "token 仍被燒掉（兌現 SQL 有下）⇒ 要再做一次就得重新確認"


@pytest.mark.req(_REQ)
async def test_redeem_with_a_future_date_still_calls_the_write_tool(monkeypatch):
    """正對照組：只把時鐘挪到卡上日期之前，同一組裝置就會呼叫寫入工具。"""
    monkeypatch.setattr(bills, "_today", lambda: date(2026, 8, 1))
    pool = FakePool([_redeem_row()])
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=pool)

    result = await rt.run_turn(_mcp_identity(), f"confirm_submit:{_PID}",
                               _state_with_pending())

    assert registry.call_args[0]["name"] == "jgb2.action.bill_due_extend"
    assert result.outcome["state"] == "confirmed"
    assert "date_before_today_at_redeem" not in result.trace.violations


@pytest.mark.req(_REQ)
async def test_redeem_blocked_by_the_gate_answers_the_same_on_resend(monkeypatch):
    """R4.3：同一個 `pending_id` 重送 ⇒ 同一句，且仍然 ⛔ 不呼叫寫入工具。"""
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    pool = FakePool([_redeem_row()])          # 第二次 fetchrow 回 None（已兌現）
    registry = _receipt_registry()
    rt = _runtime(registry=registry, pool=pool)
    state = _state_with_pending()

    first = await rt.run_turn(_mcp_identity(), f"confirm_submit:{_PID}", state)
    second = await rt.run_turn(_mcp_identity(), f"confirm_submit:{_PID}", state)

    assert first.answer == second.answer == ACTION_FAILED_TEXT
    assert second.outcome["state"] == "failed"
    assert registry.call_args == []
