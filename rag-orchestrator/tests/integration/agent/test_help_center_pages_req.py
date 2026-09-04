"""integration：help_center_pages 表約束＋help.read 真讀（agentic-mcp-orchestration 任務 1.6）。

真 DB：套 migration SQL（冪等）→ 插一列 citable=true 無 approved_by 應違反 CHECK →
插 approved_by 後成功 → read_help_page 讀回。無法連 DB → skip（非 fail）。
測試列於 finally 清掉。
"""
import os

import pytest

from services.agent.tools.help import HelpPage, read_help_page

pytestmark = pytest.mark.integration

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "migrations",
    "20260904_create_help_center_pages.sql",
)
_SLUG = "test-help-1-6-integration"


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
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    with open(_MIGRATION, encoding="utf-8") as f:
        await p.execute(f.read())
    try:
        yield p
    finally:
        await p.execute("DELETE FROM help_center_pages WHERE slug = $1", _SLUG)
        await p.close()


@pytest.mark.req("agentic-mcp-orchestration:1.6")
async def test_citable_true_without_approved_by_violates_check(pool):
    with pytest.raises(Exception, match="(?i)constraint|check"):
        await pool.execute(
            """
            INSERT INTO help_center_pages (slug, title, text, version, content_sha256, citable)
            VALUES ($1, 't', 'x', 'v1', 'sha', true)
            """,
            _SLUG,
        )


@pytest.mark.req("agentic-mcp-orchestration:1.6")
async def test_citable_true_with_approved_by_succeeds_and_reads_back(pool):
    await pool.execute(
        """
        INSERT INTO help_center_pages (slug, title, text, version, content_sha256, citable, approved_by)
        VALUES ($1, '怎麼繳費', '請至租客頁面點選繳費。', 'v1', 'sha256deadbeef', true, 'ops@jgbsmart.com')
        ON CONFLICT (slug) DO UPDATE SET approved_by = EXCLUDED.approved_by, citable = EXCLUDED.citable
        """,
        _SLUG,
    )

    page = await read_help_page(pool, _SLUG)
    assert page == HelpPage(
        slug=_SLUG, title="怎麼繳費", text="請至租客頁面點選繳費。", version="v1", citable=True,
    )
