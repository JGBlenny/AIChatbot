"""測試替身：有狀態的 `agent_confirmation_tokens` 記憶體表（主線第 3 步 A 片）。

只認 `services.agent.tools.confirm` 的六句 SQL（以模組常數比對，⛔ 另抄字面量）：
  - `_LOCK_SESSION_SQL`、`_BURN_SESSION_TOKENS_SQL`、`_INSERT_TOKEN_SQL`（`acquire()`＋`transaction()` 內；
    鎖句只記進 `tx_log`／`locks`，單執行緒替身不模擬等待）；
  - `_REDEEM_PENDING_SQL`、`_ASSERT_REDEEMED_SQL`（`fetchrow`）；
  - `_REDEEM_SQL`（`fetchrow`，只為完整；正式碼無呼叫點）；
  - `_PENDING_TOKEN_STATE_SQL`（`fetch`，A+ 片 AP-3 唯讀查詢；`state_error` 給定時拋它，
    `state_calls` 記每次查詢的 `(pending_id, session_id)`）。
其他 SQL：`fetchrow` ⇒ `None`、`execute` ⇒ `"UPDATE 0"`、`fetch` ⇒ `[]`（槽位等與本表無關的查詢）。

交易語義：`transaction()` 進入時對整張表取快照；區塊內拋例外 ⇒ 還原快照（＝回滾）。
`insert_error` 給定時 INSERT 那一句拋它（驗「INSERT 前例外 ⇒ 整筆回滾」）。

⚠️ 這是單元層的「DB 證據」：`redeemed` 欄位真的被改、兌現真的看 `session_id`／`pending_id`／
   `redeemed`／`expires_at` 四個條件。並行交錯（同 session 兩邊同時燒卡）不在本替身範圍——
   那一條（驗收 #9p）在 `tests/integration/agent/test_step3_unique_card_pg_req.py` 以真 PG 驗。
"""
from __future__ import annotations

import copy
import time
from typing import Any, Optional

from services.agent.tools import confirm as C

__all__ = ["FakeTokenDB"]


def _norm(sql: Any) -> str:
    return " ".join(str(sql).split())


_LOCK = _norm(C._LOCK_SESSION_SQL)
_BURN = _norm(C._BURN_SESSION_TOKENS_SQL)
_INSERT = _norm(C._INSERT_TOKEN_SQL)
_REDEEM_PENDING = _norm(C._REDEEM_PENDING_SQL)
_ASSERT_REDEEMED = _norm(C._ASSERT_REDEEMED_SQL)
_REDEEM = _norm(C._REDEEM_SQL)
_STATE = _norm(C._PENDING_TOKEN_STATE_SQL)


class _CM:
    def __init__(self, enter, exit_=None):
        self._enter = enter
        self._exit = exit_

    async def __aenter__(self):
        return self._enter()

    async def __aexit__(self, exc_type, exc, tb):
        if self._exit is not None:
            self._exit(exc_type)
        return False


class _Conn:
    def __init__(self, db: "FakeTokenDB"):
        self._db = db

    def transaction(self):
        snapshot: dict = {}

        def _enter():
            snapshot["rows"] = copy.deepcopy(self._db.rows)
            self._db.tx_log.append("begin")

        def _exit(exc_type):
            if exc_type is not None:
                self._db.rows = snapshot["rows"]
                self._db.tx_log.append("rollback")
            else:
                self._db.tx_log.append("commit")

        return _CM(_enter, _exit)

    async def execute(self, sql: str, *args: Any):
        text = _norm(sql)
        if text == _LOCK:
            (session_id,) = args
            self._db.tx_log.append("lock")
            self._db.locks.append(session_id)
            return "SELECT 1"
        if text == _BURN:
            (session_id,) = args
            self._db.tx_log.append("burn")
            n = 0
            for row in self._db.rows:
                if row["session_id"] == session_id and not row["redeemed"]:
                    row["redeemed"] = True
                    n += 1
            return f"UPDATE {n}"
        if text == _INSERT:
            token, session_id, p_sha, s_sha, ttl, pending_id = args
            if self._db.insert_error is not None:
                self._db.tx_log.append("insert_error")
                raise self._db.insert_error
            self._db.tx_log.append("insert")
            self._db.rows.append({
                "token": token, "session_id": session_id, "payload_sha256": p_sha,
                "summary_sha256": s_sha, "expires_at": self._db.now() + int(ttl),
                "redeemed": False, "pending_id": pending_id,
            })
            return "INSERT 0 1"
        raise AssertionError(f"token 交易內出現未預期的 SQL：{text[:80]!r}")


class FakeTokenDB:
    def __init__(self, *, insert_error: Optional[BaseException] = None):
        self.rows: list = []
        self.tx_log: list = []
        self.locks: list = []
        self.insert_error = insert_error
        self.redeem_calls: list = []
        self.state_calls: list = []
        self.state_error: Optional[BaseException] = None
        self._clock_offset = 0.0

    # ── 時鐘（過期測試用） ───────────────────────────────────────────
    def now(self) -> float:
        return time.time() + self._clock_offset

    def advance(self, seconds: float) -> None:
        self._clock_offset += seconds

    # ── asyncpg pool 介面 ─────────────────────────────────────────────
    def acquire(self):
        return _CM(lambda: _Conn(self))

    async def fetchrow(self, sql: str, *args: Any):
        text = _norm(sql)
        if text == _REDEEM_PENDING:
            pending_id, session_id = args
            self.redeem_calls.append((pending_id, session_id))
            for row in self.rows:
                if (row["pending_id"] == pending_id and row["session_id"] == session_id
                        and not row["redeemed"] and row["expires_at"] > self.now()):
                    row["redeemed"] = True
                    return {"token": row["token"], "payload_sha256": row["payload_sha256"],
                            "summary_sha256": row["summary_sha256"]}
            return None
        if text == _ASSERT_REDEEMED:
            token, session_id = args
            for row in self.rows:
                if row["token"] == token and row["session_id"] == session_id and row["redeemed"]:
                    return {"?column?": 1}
            return None
        if text == _REDEEM:
            token, session_id = args
            for row in self.rows:
                if (row["token"] == token and row["session_id"] == session_id
                        and not row["redeemed"] and row["expires_at"] > self.now()):
                    row["redeemed"] = True
                    return {"payload_sha256": row["payload_sha256"],
                            "summary_sha256": row["summary_sha256"]}
            return None
        return None

    async def execute(self, sql: str, *args: Any):
        return "UPDATE 0"

    async def fetch(self, sql: str, *args: Any):
        if _norm(sql) == _STATE:
            pending_id, session_id = args
            self.state_calls.append((pending_id, session_id))
            if self.state_error is not None:
                raise self.state_error
            # 純 SELECT：⛔ 改任何列；只回 redeemed／剩餘秒數／兩把雜湊（⛔ token）。
            return [{"redeemed": r["redeemed"],
                     "remaining_s": float(r["expires_at"] - self.now()),
                     "summary_sha256": r["summary_sha256"],
                     "payload_sha256": r["payload_sha256"]}
                    for r in self.rows
                    if r["pending_id"] == pending_id and r["session_id"] == session_id]
        return []

    async def fetchval(self, sql: str, *args: Any):
        return None

    # ── 查表（斷言用） ───────────────────────────────────────────────
    def row(self, pending_id: str) -> Optional[dict]:
        return next((r for r in self.rows if r["pending_id"] == pending_id), None)

    def redeemed(self, pending_id: str) -> Optional[bool]:
        r = self.row(pending_id)
        return None if r is None else r["redeemed"]

    def live_pids(self, session_id: str) -> list:
        """同 session 目前**可兌現**的 pid（未兌現且未過期）。"""
        return [r["pending_id"] for r in self.rows
                if r["session_id"] == session_id and not r["redeemed"]
                and r["expires_at"] > self.now()]

    def pids(self, session_id: str) -> list:
        return [r["pending_id"] for r in self.rows if r["session_id"] == session_id]
