"""integration（真 PG）：主線第 3 步 A7——同 session 兩回合**交錯**出卡後，可兌現 pid ≤ 1。

凍結驗收清單 `.kiro/specs/agentic-mcp-orchestration/acceptance-conversation-architecture-step3-20261018.md`
#9p（業主 2026-10-19 變更裁定、DSP-092）：出卡交易開頭取 `pg_advisory_xact_lock(hashtext(session_id))`；
同 session 兩回合同時出卡 ⇒ 第二個交易被擋到第一個 commit 之後才燒卡；最終可兌現 pid ≤ 1；
逐一送出所有 pid，寫入 ≤ 1；正對照：拿掉鎖的同一排程重現 2 張。

排程：第一個 `confirm_request` 的連線在「燒本 session 未兌現 token」那一句**執行完之後**停住
（尚未 INSERT／commit）；此時啟動第二個 `confirm_request`，看它 ≥ 0.5 秒內有沒有執行到燒卡句；
再放行第一個。⛔ 改流程函式——`confirm_request` 與 `redeem_pending` 走正式碼，替身只包連線。
「寫入」以 `redeem_pending` 成功次數計（兌現段唯一的寫入前閘門：沒兌現到 token 就不呼叫寫入工具）。

DB 安全：`tests/conftest.py` 的守門（`DB_ENV` 已設且非 production、`DB_NAME` 非產線預設、
`RUN_INTEGRATION=1`）；本檔只碰 `session_id` 以 `_SESSION_PREFIX` 開頭的列，finally 清掉。
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import date

import pytest

from services.agent.identity import Identity
from services.agent.tools import confirm as C
from services.jgb import bills as _bills

pytestmark = pytest.mark.integration

_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
_MIGRATIONS = (
    "20260905_agent_confirmation_tokens.sql",
    "20260908_agent_confirmation_tokens_pending_id.sql",
)
_SESSION_PREFIX = "backtest_session_step3_9p_"
TODAY = date(2026, 10, 17)


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture
async def pool():
    import asyncpg
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=2, max_size=4)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"無法連 DB：{e}")
        return
    for name in _MIGRATIONS:
        with open(os.path.join(_MIGRATIONS_DIR, name), encoding="utf-8") as f:
            await p.execute(f.read())
    try:
        yield p
    finally:
        await p.execute("DELETE FROM agent_confirmation_tokens WHERE session_id LIKE $1",
                        _SESSION_PREFIX + "%")
        await p.close()


def _norm(sql) -> str:
    return " ".join(str(sql).split())


class _HookConn:
    """真 asyncpg 連線的薄包裝：只在「燒本 session 未兌現 token」那一句**前後**呼叫掛鉤。

    ⛔ 改 SQL、⛔ 改流程——`confirm_request` 照正式碼對真 PG 下每一句。唯一例外：正對照 (i)
    把鎖常數換成 `SELECT 1`（無參數）時，asyncpg 不收多餘的 `$1` 參數，這裡把該句的參數丟掉
    （只為讓「拿掉鎖」的同一排程跑得起來；正常路徑永遠不會出現 `SELECT 1`）。
    """

    def __init__(self, conn, *, before_burn=None, after_burn=None):
        self._conn = conn
        self._before = before_burn
        self._after = after_burn

    def transaction(self):
        return self._conn.transaction()

    async def execute(self, sql, *args):
        is_burn = _norm(sql) == _norm(C._BURN_SESSION_TOKENS_SQL)
        if is_burn and self._before is not None:
            await self._before()
        if _norm(sql) == "SELECT 1":
            args = ()
        out = await self._conn.execute(sql, *args)
        if is_burn and self._after is not None:
            await self._after()
        return out


class _HookPool:
    def __init__(self, pool, **hooks):
        self._pool = pool
        self._hooks = hooks

    def acquire(self):
        pool, hooks = self._pool, self._hooks

        class _CM:
            async def __aenter__(self_inner):
                self_inner._cm = pool.acquire()
                conn = await self_inner._cm.__aenter__()
                return _HookConn(conn, **hooks)

            async def __aexit__(self_inner, *exc):
                return await self_inner._cm.__aexit__(*exc)

        return _CM()


def _identity(session_id: str) -> Identity:
    return Identity(vendor_id=1, target_user="tenant", mode="b2c", role_id="20151", user_id="1",
                    session_id=session_id, api_key_id=1)


def _payload(days: int) -> dict:
    # 以 `render` 自洽的一組（原到期日晚於 TODAY ⇒ 起算日＝原到期日）。
    return {"action": "bill_due_extend", "bill_id": "900001", "date_expire_before": "20261101",
            "days": days, "date_expire_after": f"202611{1 + days:02d}"}


async def _issue(db, session_id: str, days: int):
    return await C.confirm_request(
        _identity(session_id),
        {"summary": "確認", "payload": json.dumps(_payload(days), ensure_ascii=False)},
        db_pool=db,
    )


async def _live_pids(pool, session_id: str) -> list:
    rows = await pool.fetch(
        "SELECT pending_id FROM agent_confirmation_tokens "
        "WHERE session_id = $1 AND redeemed = false AND expires_at > now()", session_id)
    return [r["pending_id"] for r in rows]


_HOLD_S = 0.5


async def _interleave(pool, sid: str):
    """排程（驗收 #9p 變更裁定）：第一個交易**燒卡後、commit 前**停住；此時啟動第二個交易；
    觀察第二個交易在 ≥ `_HOLD_S` 秒內有沒有執行到燒卡那句；再放行第一個，兩者跑完。

    回傳 (r1, r2, second_reached_burn_while_first_held)。
    """
    burned1 = asyncio.Event()
    release1 = asyncio.Event()
    reached2 = asyncio.Event()

    async def _hold_first():
        burned1.set()
        await asyncio.wait_for(release1.wait(), timeout=20)

    async def _mark_second():
        reached2.set()

    p1 = _HookPool(pool, after_burn=_hold_first)
    p2 = _HookPool(pool, before_burn=_mark_second)
    t1 = asyncio.create_task(_issue(p1, sid, 3))
    await asyncio.wait_for(burned1.wait(), timeout=10)          # 第一個交易已燒卡、尚未 INSERT／commit
    t2 = asyncio.create_task(_issue(p2, sid, 5))
    try:
        await asyncio.wait_for(reached2.wait(), timeout=_HOLD_S)
        reached_while_held = True
    except asyncio.TimeoutError:
        reached_while_held = False
    release1.set()
    r1, r2 = await asyncio.wait_for(asyncio.gather(t1, t2), timeout=20)
    return r1, r2, reached_while_held, reached2.is_set()


async def _assert_both_written(pool, sid, pids):
    rows = await pool.fetch("SELECT pending_id FROM agent_confirmation_tokens WHERE session_id = $1", sid)
    assert sorted(r["pending_id"] for r in rows) == sorted(pids)


async def test_9p_interleaved_issue_leaves_at_most_one_redeemable_card(pool, monkeypatch):
    """#9p（DSP-092）：第一個交易燒卡後停住時啟動第二個 ⇒ 第二個在放行前**到不了**燒卡那句
    （被 session advisory lock 擋住）；放行後兩者都完成；最終可兌現 pid ≤ 1、逐一兌現成功 ≤ 1。"""
    # A6 預檢會呼叫 JGB 讀帳單；本條驗的是 token 交易，預檢關閉（開關 off）不影響 A7（A7 不掛開關）。
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")
    assert C._LOCK_SESSION_SQL == "SELECT pg_advisory_xact_lock(hashtext($1))"
    sid = _SESSION_PREFIX + uuid.uuid4().hex[:12]
    r1, r2, reached_while_held, reached_eventually = await _interleave(pool, sid)
    assert reached_while_held is False, "第二個交易在第一個 commit 前就執行到燒卡句（鎖沒擋住）"
    assert reached_eventually is True                               # 放行後確實跑到燒卡
    assert r1.ok and r2.ok, (r1, r2)
    pids = [r1.data["pending_id"], r2.data["pending_id"]]
    await _assert_both_written(pool, sid, pids)                     # 前提自證：兩筆都真的寫進表
    live = await _live_pids(pool, sid)
    assert len(live) <= 1, f"可兌現 pid {len(live)} 張（>1）：{live}"
    assert live == [pids[1]]                                        # 後 commit 的那張
    redeemed = [pid for pid in pids if await C.redeem_pending(pool, sid, pid) is not None]
    assert len(redeemed) <= 1, redeemed


async def test_9p_positive_control_without_lock_same_schedule_leaves_two(pool, monkeypatch):
    """正對照 (i)：同一排程，以 monkeypatch 把鎖常數換成 `SELECT 1`（＝拿掉鎖）⇒ 第二個交易在第一個
    放行前就燒完卡，重現可兌現 2 張、兩張都兌現得到（證明上一條的通過來自鎖，不是排程碰巧）。"""
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")
    monkeypatch.setattr(C, "_LOCK_SESSION_SQL", "SELECT 1")
    sid = _SESSION_PREFIX + uuid.uuid4().hex[:12]
    r1, r2, reached_while_held, _ = await _interleave(pool, sid)
    assert reached_while_held is True
    assert r1.ok and r2.ok, (r1, r2)
    pids = [r1.data["pending_id"], r2.data["pending_id"]]
    await _assert_both_written(pool, sid, pids)
    live = await _live_pids(pool, sid)
    assert sorted(live) == sorted(pids), live
    redeemed = [pid for pid in pids if await C.redeem_pending(pool, sid, pid) is not None]
    assert sorted(redeemed) == sorted(pids)


async def test_9p_positive_control_sequential_issue_leaves_exactly_one(pool, monkeypatch):
    """正對照 (ii)：不交錯（依序）出兩張 ⇒ 恰一張可兌現（＝後出的那張）。"""
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")
    sid = _SESSION_PREFIX + uuid.uuid4().hex[:12]
    r1 = await _issue(pool, sid, 3)
    r2 = await _issue(pool, sid, 5)
    assert r1.ok and r2.ok
    assert await _live_pids(pool, sid) == [r2.data["pending_id"]]
    assert await C.redeem_pending(pool, sid, r1.data["pending_id"]) is None
    assert await C.redeem_pending(pool, sid, r2.data["pending_id"]) is not None
