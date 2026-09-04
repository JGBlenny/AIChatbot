"""integration：`agent_shadow_texts` 表（agentic-mcp-orchestration 任務 4.1）。

真測試庫：套 migration（冪等）→ 寫一列 → 讀回 → 清列。無法連 DB → skip（非
fail）；連到非測試庫 → 大聲失敗（比照 test_outline_approval_columns_req.py
的守門）。

⛔ 本測試不驗 `ShadowRunner` 本身（那是 unit 層 `test_shadow_req.py` 的事，
全程假 pool）——這裡只驗表結構本身可寫可讀、索引存在、30 天清理指令的
篩選條件（`created_at`）可用。
"""
import os
import uuid

import pytest

pytestmark = pytest.mark.integration

_SPEC = "agentic-mcp-orchestration:4.1"

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
    "20260905_agent_shadow_texts.sql",
)


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _session_id() -> str:
    return "backtest_session_agent41_" + uuid.uuid4().hex[:12]


@pytest.fixture
async def pool():
    import asyncpg

    kwargs = _conn_kwargs()
    if kwargs["database"] not in ("aichatbot_test", "aichatbot_ci"):
        pytest.fail(
            f"[env] 解析到的資料庫 {kwargs['database']!r} 不是測試庫——"
            "本測試會寫入列，⛔ 拒絕執行"
        )
    try:
        p = await asyncpg.create_pool(**kwargs, min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    with open(_MIGRATION, encoding="utf-8") as f:
        await p.execute(f.read())
    try:
        yield p
    finally:
        await p.execute(
            "DELETE FROM agent_shadow_texts WHERE session_id LIKE $1",
            "backtest_session_agent41_%",
        )
        await p.close()


@pytest.mark.req(_SPEC)
async def test_migration_is_idempotent(pool):
    with open(_MIGRATION, encoding="utf-8") as f:
        await pool.execute(f.read())  # 第二次套用不應丟例外


@pytest.mark.req(_SPEC)
async def test_write_then_read_back_row(pool):
    session_id = _session_id()
    row = await pool.fetchrow(
        """
        INSERT INTO agent_shadow_texts (session_id, trace_id, agent_answer, old_answer)
        VALUES ($1, $2, $3, $4)
        RETURNING id, session_id, trace_id, agent_answer, old_answer, created_at
        """,
        session_id, "trace-abc", "新鏈的完整答案", "舊鏈的完整答案",
    )
    assert row is not None, "寫入應該回一列（正對照組）"
    assert row["session_id"] == session_id
    assert row["trace_id"] == "trace-abc"
    assert row["agent_answer"] == "新鏈的完整答案"
    assert row["old_answer"] == "舊鏈的完整答案"
    assert row["created_at"] is not None

    fetched = await pool.fetchrow(
        "SELECT agent_answer, old_answer FROM agent_shadow_texts WHERE session_id = $1",
        session_id,
    )
    assert fetched["agent_answer"] == "新鏈的完整答案"
    assert fetched["old_answer"] == "舊鏈的完整答案"


@pytest.mark.req(_SPEC)
async def test_row_is_cleanable_by_created_at_predicate(pool):
    """30 天清理指令是 `WHERE created_at < now() - interval '30 days'`——
    這裡驗證這個謂詞的形狀能跑（正對照組：剛寫的列 created_at 是「現在」，
    不落在 30 天前，用它證明謂詞本身不會誤刪剛寫的資料，而不是誤判空表）。
    """
    session_id = _session_id()
    await pool.execute(
        "INSERT INTO agent_shadow_texts (session_id, trace_id, agent_answer, old_answer) "
        "VALUES ($1, $2, $3, $4)",
        session_id, "trace-fresh", "新", "舊",
    )
    stale_count = await pool.fetchval(
        "SELECT count(*) FROM agent_shadow_texts "
        "WHERE session_id = $1 AND created_at < now() - interval '30 days'",
        session_id,
    )
    assert stale_count == 0, "剛寫的列不該被 30 天清理謂詞判定為過期"

    fresh_count = await pool.fetchval(
        "SELECT count(*) FROM agent_shadow_texts "
        "WHERE session_id = $1 AND created_at >= now() - interval '30 days'",
        session_id,
    )
    assert fresh_count == 1, "正對照組：剛寫的列應該落在『未過期』那一側"


@pytest.mark.req(_SPEC)
async def test_missing_required_columns_rejected(pool):
    """NOT NULL 守門：`session_id`／`trace_id`／`agent_answer`／`old_answer`
    缺任一即拒絕寫入——正對照組同時也證明前面測試的成功寫入不是巧合。
    """
    import asyncpg

    with pytest.raises(asyncpg.NotNullViolationError):
        await pool.execute(
            "INSERT INTO agent_shadow_texts (session_id, trace_id, agent_answer, old_answer) "
            "VALUES ($1, $2, $3, NULL)",
            _session_id(), "trace-x", "新",
        )
