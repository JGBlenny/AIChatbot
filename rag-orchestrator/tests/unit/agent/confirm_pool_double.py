"""測試替身：讓 `AsyncMock()` 池支援 `confirm.request` 的 token 寫入交易（第 3 步 A7）。

A7 之後 `confirm_request` 寫 token 改為：

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(_LOCK_SESSION_SQL, session_id)          # DSP-092 session 鎖
            await conn.execute(_BURN_SESSION_TOKENS_SQL, session_id)   # 燒本 session 舊卡
            await conn.execute(_INSERT_TOKEN_SQL, token, session_id, p_sha, s_sha, ttl, pid)

原本各測試對 `pool.execute` 的 INSERT 斷言，現在改對 `pool.insert`（只收 INSERT 那一句，
參數形狀與原本 `pool.execute.await_args.args` **逐位相同**：`[0]`=SQL、`[1]`=token、
`[2]`=session_id、`[3]`=payload_sha256、`[4]`=summary_sha256、`[5]`=ttl、`[6]`=pending_id）。
燒卡那一句記在 `pool.burn`、鎖那一句記在 `pool.lock`。`pool.tx_log` 依序記交易事件
（`begin`／`lock`／`commit`／`rollback`）。

⚠️ 只**擴充**替身：`pool.execute`／`pool.fetchrow` 原樣保留（AsyncMock），⛔ 改變它們。
"""
from __future__ import annotations

from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

from services.agent.tools import confirm as _C

__all__ = ["attach_token_tx", "token_pool"]


class _AsyncCM:
    def __init__(self, enter_value: Any, on_exit=None, on_enter=None):
        self._enter_value = enter_value
        self._on_exit = on_exit
        self._on_enter = on_enter

    async def __aenter__(self):
        if self._on_enter is not None:
            self._on_enter()
        return self._enter_value

    async def __aexit__(self, exc_type, exc, tb):
        if self._on_exit is not None:
            self._on_exit(exc_type)
        return False


def attach_token_tx(pool: Any, *, insert_error: Optional[BaseException] = None) -> Any:
    """在既有池替身上掛 `acquire()`／`transaction()`，並把兩句 SQL 分流到 `pool.burn`／`pool.insert`。

    `insert_error`：給定時 INSERT 那一句拋它（驗「INSERT 前例外 ⇒ 整筆回滾」）。
    """
    pool.insert = AsyncMock(return_value="INSERT 0 1")
    pool.burn = AsyncMock(return_value="UPDATE 0")
    pool.lock = AsyncMock(return_value="SELECT 1")
    pool.tx_log = []

    async def _conn_execute(sql: str, *args: Any):
        text = " ".join(str(sql).split())
        if text == " ".join(_C._LOCK_SESSION_SQL.split()):
            pool.tx_log.append("lock")
            return await pool.lock(sql, *args)
        if text.startswith("INSERT INTO agent_confirmation_tokens"):
            if insert_error is not None:
                pool.tx_log.append("insert_error")
                raise insert_error
            return await pool.insert(sql, *args)
        if text.startswith("UPDATE agent_confirmation_tokens SET redeemed = true"):
            return await pool.burn(sql, *args)
        raise AssertionError(f"token 交易內出現未預期的 SQL：{text[:80]!r}")

    conn = MagicMock(name="conn")
    conn.execute = AsyncMock(side_effect=_conn_execute)

    def _tx_exit(exc_type):
        pool.tx_log.append("commit" if exc_type is None else "rollback")

    conn.transaction = MagicMock(
        side_effect=lambda: _AsyncCM(None, on_exit=_tx_exit,
                                     on_enter=lambda: pool.tx_log.append("begin"))
    )
    pool.conn = conn
    pool.acquire = MagicMock(side_effect=lambda: _AsyncCM(conn))
    return pool


def token_pool(**kwargs: Any) -> Any:
    """與各檔原本 `_pool()`／`_confirm_pool()` 相同的 `AsyncMock` 池，再掛上 token 交易。"""
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    return attach_token_tx(pool, **kwargs)
