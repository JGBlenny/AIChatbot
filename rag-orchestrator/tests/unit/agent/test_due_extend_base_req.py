"""unit：`bill_due_extend` 的**起算日**（V3｜Plan 走查回修第四批 §4）。

治的病灶（line-bot 第二輪走查）：帳單 756248 到期日 9/01 已逾期，使用者說「延三天」，
舊算法以**原到期日**起算 ⇒ 新到期日 9/04 仍在過去 ⇒ S1 閘門擋掉，使用者只看到
「不能延」。V3 把 `days` 的基準改成「原到期日與**今天**較晚者」：

    起算日 base = max(date_expire_before, today)          # today 缺省 ⇒ base = before
    驗算       base + days == date_expire_after
    卡上多一行 「起算日：YYYY/MM/DD」

## 一個時鐘、三個呼叫點（本檔逐點驗）
    出卡          `tools/confirm.confirm_request`          嚴格等式
    兌現閘        `runtime._run_confirm_segment`           `fields_before_today`（縱深）
    寫入形狀驗算  `tools/action._validated_payload`        today 或 today−1（跨午夜）

三處各自在**呼叫點**取 `bills._today()`；`confirm_card` 本身 ⛔ 不讀時鐘
（決定性硬約束），`today` 一律是**關鍵字參數**、⛔ 不從 payload 讀。

## 安全面（security-reviewer r1 #1／#2、plan-verifier r1 #2）
- `today` 從 payload 讀 ⇒ 模型可控驗算基準 ⇒ **payload 帶 `today` 鍵一律 `INVALID_INPUT`**。
- 兌現端不帶 `today` ⇒ 每張 V3 卡都在 token 燒掉之後才 `INVALID_INPUT`（兌現不了）。
- 兌現端只用當日時鐘做嚴格等式 ⇒ 跨午夜的卡兌現不了 ⇒ `today` 或 `today − 1` 任一成立。
  ⚠️ 這是**驗算**的容忍度、⛔ 不是閘門的：兌現閘仍以當日新時鐘檢查。

⚠️ 每個「被擋下」的斷言旁都有**正對照組**（同一組裝置只換一個變因就會通過），
   裝置壞掉時正對照組會先紅，⛔ 不會被誤讀成「規則有效」。
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from services.agent.confirm_card import (
    ACTION_FAILED_TEXT,
    RESERVED_PAYLOAD_KEYS,
    ConfirmCardError,
    fields_before_today,
    render,
)
from services.agent.identity import Identity
from services.agent.tools import action as action_tools
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.confirm import (
    confirm_request,
    payload_digest,
    pending_id_for,
    sha256_hex,
)
from services.agent.tools.registry import ToolRegistry
from services.jgb import bills
from services.jgb_system_api import JGBSystemAPI

from tests.unit.agent.test_runtime_confirm_segment_req import FakePool, _runtime

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R4.2"

#: 走查那一題的三個數字（Plan §4 驗收逐字）。⛔ 不用 `date.today()`——
#: 測試自己讀時鐘，就沒有東西在驗時鐘。
_BEFORE = date(2026, 9, 1)      # 原到期日（已逾期）
_TODAY = date(2026, 9, 9)       # 出卡日
_DAYS = 3
_AFTER = date(2026, 9, 12)      # 起算日（＝今天）＋ 3

#: 替身 fixture 的既有資料（`services/jgb/fixture_data/demo_vendor4.json`）：
#: 帳單 900001 宣告可見於 role 20151／user 9001。
_ROLE = "20151"
_USER = "9001"
_BILL = "900001"

_TOKEN = "tok-secret-value-must-never-leak-0123456789"
_PID = pending_id_for(_TOKEN)


def _ymd(value: date) -> str:
    return f"{value.year:04d}{value.month:02d}{value.day:02d}"


def _fmt(value: date) -> str:
    return f"{value.year:04d}/{value.month:02d}/{value.day:02d}"


def _payload(before: date = _BEFORE, *, days: int = _DAYS, after: date = _AFTER,
             **over) -> dict:
    base = {
        "action": "bill_due_extend",
        "bill_id": _BILL,
        "date_expire_before": _ymd(before),
        "days": days,
        "date_expire_after": _ymd(after),
    }
    base.update(over)
    return base


def _identity(**over) -> Identity:
    base = dict(vendor_id=4, target_user="property_manager", mode="b2b",
                role_id=_ROLE, user_id=_USER, session_id="mcp:1:4:s1",
                api_key_id=1, entry="mcp")
    base.update(over)
    return Identity(**base)


@pytest.fixture()
def api(monkeypatch) -> JGBSystemAPI:
    """真 `JGBSystemAPI` ＋替身 transport（每個測試一份獨立 fixture 狀態）。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    instance = JGBSystemAPI()
    monkeypatch.setattr(jgb2_tools, "_api_singleton", instance)
    return instance


def _confirm_pool():
    """`confirm.request` 只用 `execute`（INSERT token 列）。"""
    from unittest.mock import AsyncMock

    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    return pool


def _write_registry() -> ToolRegistry:
    """**真** registry ＋ 真 `jgb2.action.*` handler（兌現查核一律放行）。

    ⚠️ 刻意 ⛔ 不用假 registry：本檔要驗的正是 `action._validated_payload`
    這個呼叫點，假 registry 會讓那段程式根本不執行 ⇒ 那是一條看不見任何東西的
    瞎斷言（同 `test_confirm_date_gate_req.py` 的註記）。
    """
    async def _always_redeemed(token, session_id):
        return True

    reg = ToolRegistry(write_tools_enabled=True, redeem_checker=_always_redeemed)
    for spec, fn in action_tools.ACTION_SPECS:
        reg.register(spec, fn)
    return reg


def _pending_state(card: str, payload: dict) -> dict:
    from services.agent.runtime import PENDING_CONFIRM_KEY

    return {"agent": {PENDING_CONFIRM_KEY: {_PID: {
        "action": "bill_due_extend",
        "payload": dict(payload),
        "card_sha256": sha256_hex(card),
    }}}}


def _redeem_row(card: str, payload: dict) -> dict:
    return {
        "token": _TOKEN,
        "payload_sha256": payload_digest(payload),
        "summary_sha256": sha256_hex(card),
    }


def _bill_due(api: JGBSystemAPI) -> int:
    """直接讀替身 fixture 的到期日（⛔ 不經被測的那條路，避免自證）。"""
    return api._mock_transport.fixtures.by_id(int(_BILL))["date_expire"]


# ---------------------------------------------------------------------------
# 1. 基準本身（純 render 層，⛔ 不讀時鐘）
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
def test_base_is_today_when_the_original_due_date_is_in_the_past():
    """`before < today` ⇒ 起算日＝**今天**（走查那一題的正解）。"""
    card = render("bill_due_extend", _payload(), today=_TODAY)
    assert f"・起算日：{_fmt(_TODAY)}" in card
    # 舊算法（以原到期日起算）算出來的那一張，在同一個 today 下 ⛔ 驗算不過
    with pytest.raises(ConfirmCardError):
        render("bill_due_extend",
               _payload(after=_BEFORE + timedelta(days=_DAYS)), today=_TODAY)


@pytest.mark.req(_REQ)
def test_base_is_the_original_due_date_when_it_is_today_or_later():
    """`before >= today` ⇒ 起算日＝**原到期日**（未逾期的帳單行為不變）。"""
    for delta in (0, 1, 30):
        before = _TODAY + timedelta(days=delta)
        after = before + timedelta(days=_DAYS)
        card = render("bill_due_extend", _payload(before=before, after=after),
                      today=_TODAY)
        assert f"・起算日：{_fmt(before)}" in card
        assert f"・新到期日：{_fmt(after)}" in card


@pytest.mark.req(_REQ)
def test_omitting_today_keeps_the_old_arithmetic_verbatim():
    """`today` 缺省 ⇒ 起算日＝原到期日＝**舊行為逐字不變**。"""
    old = _payload(after=_BEFORE + timedelta(days=_DAYS))
    card = render("bill_due_extend", old)
    assert f"・起算日：{_fmt(_BEFORE)}" in card
    # 正對照組：同一份 payload 帶上今天就過不了（證明上一行不是恆真）
    with pytest.raises(ConfirmCardError):
        render("bill_due_extend", old, today=_TODAY)


@pytest.mark.req(_REQ)
def test_the_card_prints_the_base_date_line():
    """卡上必須看得到起算日——「原到期日 9/01、延 3 天、新到期日 9/12」單看三個
    數字對不起來，⛔ 不靠模型在 `summary` 裡解釋。"""
    card = render("bill_due_extend", _payload(), today=_TODAY)
    assert card == (
        "即將調整帳單到期日，請確認：\n"
        f"・帳單編號：{_BILL}\n"
        f"・原到期日：{_fmt(_BEFORE)}\n"
        f"・起算日：{_fmt(_TODAY)}\n"
        f"・延後天數：{_DAYS} 天\n"
        f"・新到期日：{_fmt(_AFTER)}\n"
        "請從下方按鈕擇一。"
    )


# ---------------------------------------------------------------------------
# 2. `today` ⛔ 不從 payload 讀（security r1 #2）
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
def test_today_is_keyword_only_and_never_positional():
    """`render(action, payload, today)` ⛔ 傳不進去——基準只能由呼叫點具名傳。"""
    with pytest.raises(TypeError):
        render("bill_due_extend", _payload(), _TODAY)     # type: ignore[misc]


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("value", [_ymd(_TODAY), None, "", 0, {"x": 1}])
def test_a_payload_carrying_a_today_key_is_rejected_outright(value):
    """payload 帶 `today` ⇒ **一律 `ConfirmCardError`**（⛔ 不是靜默忽略）。

    靜默忽略會讓一份帶著 `today` 的 payload 看起來被接受了，使用者無從得知它
    沒有生效；而讀它就是把驗算基準交給模型。二擇一固定為拒絕。
    """
    assert "today" in RESERVED_PAYLOAD_KEYS
    with pytest.raises(ConfirmCardError):
        render("bill_due_extend", _payload(today=value), today=_TODAY)
    # 正對照組：拿掉那一個鍵，同一份 payload 就 render 得出來
    assert render("bill_due_extend", _payload(), today=_TODAY)


@pytest.mark.req(_REQ)
def test_the_reserved_key_rule_is_not_a_per_action_branch():
    """保留鍵規則對**每個 action** 都成立（通用規則，⛔ 不是某一支的 if）。"""
    repair = {"action": "repair_create", "estate_name": "信義好宅", "description": ""}
    assert render("repair_create", repair)                 # 正對照組
    with pytest.raises(ConfirmCardError):
        render("repair_create", {**repair, "today": _ymd(_TODAY)})


@pytest.mark.req(_REQ)
async def test_confirm_request_turns_a_today_key_into_invalid_input(monkeypatch):
    """出卡端把它翻成 `INVALID_INPUT`，且 ⛔ 不落 pending 列。"""
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    pool = _confirm_pool()
    result = await confirm_request(
        _identity(),
        {"summary": "延三天", "payload": json.dumps(_payload(today=_ymd(_TODAY)))},
        db_pool=pool,
    )
    assert result.ok is False and result.error == "INVALID_INPUT"
    assert pool.execute.await_count == 0
    # 正對照組：同一份 payload 去掉 `today` 鍵就出得了卡
    ok_pool = _confirm_pool()
    ok = await confirm_request(
        _identity(), {"summary": "延三天", "payload": json.dumps(_payload())},
        db_pool=ok_pool,
    )
    assert ok.ok is True and ok_pool.execute.await_count == 1


# ---------------------------------------------------------------------------
# 3. 出卡端：真的以今天起算
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
async def test_confirm_request_issues_the_card_for_an_overdue_bill(monkeypatch):
    """走查那一題：到期 9/01、今天 9/09、延三天 ⇒ 出卡、新到期日 9/12、起算日 9/09。"""
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    pool = _confirm_pool()

    result = await confirm_request(
        _identity(), {"summary": "延三天", "payload": json.dumps(_payload())},
        db_pool=pool,
    )

    assert result.ok is True
    assert pool.execute.await_count == 1
    card = result.data["card"]
    assert f"・起算日：{_fmt(_TODAY)}" in card
    assert f"・新到期日：{_fmt(_AFTER)}" in card
    # 卡逐字等於同一個時鐘下的 render（⛔ 中間沒有模型插手的縫）
    assert card == render("bill_due_extend", _payload(), today=_TODAY)


# ---------------------------------------------------------------------------
# 4. 兌現端：跨午夜規則（today 或 today − 1）
#
# ⚠️ 用**真** registry ＋真 handler ＋替身 transport：`_validated_payload` 是本節
#    的受測物，假 registry 會讓它根本不執行。負向斷言下在「替身的到期日有沒有變」
#    這個真實副作用上，正對照組證明同一組裝置本來會變。
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("redeem_day,expect_ok", [
    (_TODAY, True),                          # 出卡當日
    (_TODAY + timedelta(days=1), True),      # 跨一個午夜 ⇒ today − 1 成立
    (_TODAY + timedelta(days=2), False),     # 超過 TTL 語義（正對照）
])
async def test_the_write_path_accepts_today_or_yesterday_only(
    monkeypatch, api, redeem_day, expect_ok
):
    monkeypatch.setattr(bills, "_today", lambda: redeem_day)
    reg = _write_registry()
    before_due = _bill_due(api)

    result = await reg.call(
        _identity(), action_tools.BILL_DUE_EXTEND_NAME,
        {"payload": _payload(), "confirmation_token": _TOKEN},
        5, stage="M1", for_model=True,
    )

    assert result.ok is expect_ok, redeem_day
    if expect_ok:
        assert _bill_due(api) != before_due, "通過就必須真的寫下去"
    else:
        assert result.error == "INVALID_INPUT"
        assert _bill_due(api) == before_due, "⛔ 擋下就不得有任何寫入"


@pytest.mark.req(_REQ)
async def test_the_write_path_without_a_clock_keeps_the_old_arithmetic(api):
    """`_validated_payload` 缺省 `today` ⇒ 舊驗算（沒有日期語義的動作走這條）。"""
    old = _payload(after=_BEFORE + timedelta(days=_DAYS))
    assert action_tools._validated_payload(
        "bill_due_extend", {"payload": old}) == old
    # 正對照組：帶上今天就過不了（證明上一行不是恆真）
    assert action_tools._validated_payload(
        "bill_due_extend", {"payload": old}, today=_TODAY) is None


# ---------------------------------------------------------------------------
# 5. 出卡 → 兌現 **整鏈**（runtime 兌現段 ＋ 真 registry ＋ 真 handler）
# ---------------------------------------------------------------------------


async def _issue_card(monkeypatch) -> tuple:
    """真的走一次 `confirm.request`，回 `(card, payload)`。⛔ 不手捏卡文字。"""
    monkeypatch.setattr(bills, "_today", lambda: _TODAY)
    result = await confirm_request(
        _identity(), {"summary": "延三天", "payload": json.dumps(_payload())},
        db_pool=_confirm_pool(),
    )
    assert result.ok is True, "出卡就失敗 ⇒ 底下的兌現斷言全部沒有意義"
    return result.data["card"], result.data["payload"]


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("redeem_day", [_TODAY, _TODAY + timedelta(days=1)])
async def test_card_issued_today_redeems_today_and_tomorrow(monkeypatch, api, redeem_day):
    """整鏈：9/09 出的卡在 9/09 與 9/10 兌現得了，且**真的寫下去**。"""
    card, payload = await _issue_card(monkeypatch)
    monkeypatch.setattr(bills, "_today", lambda: redeem_day)
    reg = _write_registry()
    rt = _runtime(registry=reg, pool=FakePool([_redeem_row(card, payload)]))
    before_due = _bill_due(api)

    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}",
                               _pending_state(card, payload))

    assert result.outcome["state"] == "confirmed", redeem_day
    assert result.answer != ACTION_FAILED_TEXT
    assert _fmt(_AFTER) in result.answer
    assert _bill_due(api) != before_due, "兌現成功就必須真的寫下去"
    assert "date_before_today_at_redeem" not in result.trace.violations


@pytest.mark.req(_REQ)
async def test_the_same_card_no_longer_redeems_two_days_later(monkeypatch, api):
    """正對照：同一張卡在 9/11 兌現 ⇒ `_invalid_input()` ⇒ ⛔ 沒有任何寫入。

    ⚠️ 兌現閘（`fields_before_today`）在這一天**還放行**（新到期日 9/12 仍在未來），
    所以擋下來的確實是 `_validated_payload` 那一道，⛔ 不是閘門順手擋掉的。
    """
    card, payload = await _issue_card(monkeypatch)
    two_days_later = _TODAY + timedelta(days=2)
    monkeypatch.setattr(bills, "_today", lambda: two_days_later)
    # 裝置前提：閘門在這一天不開火（否則下面驗到的是閘門、不是驗算）
    assert fields_before_today("bill_due_extend", payload, two_days_later) == []

    reg = _write_registry()
    rt = _runtime(registry=reg, pool=FakePool([_redeem_row(card, payload)]))
    before_due = _bill_due(api)

    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}",
                               _pending_state(card, payload))

    assert result.answer == ACTION_FAILED_TEXT
    assert result.outcome["state"] == "failed"
    assert _bill_due(api) == before_due, "⛔ 擋下就不得有任何寫入"


@pytest.mark.req(_REQ)
async def test_the_s1_gate_still_blocks_a_new_due_date_that_has_passed(monkeypatch, api):
    """S1 兌現閘**沒有被 V3 拿掉**（縱深）：時鐘走過 9/12 ⇒ ⛔ 不呼叫寫入工具。

    正對照組＝上面兩條（9/09／9/10 同一張卡兌現得了）。
    """
    card, payload = await _issue_card(monkeypatch)
    past_due = _AFTER + timedelta(days=1)
    monkeypatch.setattr(bills, "_today", lambda: past_due)
    reg = _write_registry()
    rt = _runtime(registry=reg, pool=FakePool([_redeem_row(card, payload)]))
    before_due = _bill_due(api)

    result = await rt.run_turn(_identity(), f"confirm_submit:{_PID}",
                               _pending_state(card, payload))

    assert result.answer == ACTION_FAILED_TEXT
    assert "date_before_today_at_redeem" in result.trace.violations
    assert result.trace.tool_calls == []
    assert _bill_due(api) == before_due
