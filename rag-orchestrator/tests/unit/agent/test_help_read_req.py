"""unit：help.read 工具（agentic-mcp-orchestration 任務 1.6）。

假 pool（mock fetchrow）驗形狀：命中／查無 NO_MATCH／非法 slug INVALID_INPUT／
citable=false 列可讀且 provenance.citable 為 False。
"""
from unittest.mock import AsyncMock

import pytest

from services.agent.tools.help import HelpPage, help_read, read_help_page

pytestmark = pytest.mark.unit


def _pool(row):
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=row)
    return pool


def _row(**over):
    base = {
        "slug": "how-to-pay",
        "title": "怎麼繳費",
        "text": "請至租客頁面點選繳費。",
        "version": "v1",
        "citable": False,
    }
    base.update(over)
    return base


@pytest.mark.req("agentic-mcp-orchestration:1.6")
async def test_read_help_page_hit_returns_dataclass():
    pool = _pool(_row())
    page = await read_help_page(pool, "how-to-pay")
    assert page == HelpPage(
        slug="how-to-pay", title="怎麼繳費", text="請至租客頁面點選繳費。",
        version="v1", citable=False,
    )
    pool.fetchrow.assert_awaited_once()


@pytest.mark.req("agentic-mcp-orchestration:1.6")
async def test_read_help_page_miss_returns_none():
    pool = _pool(None)
    assert await read_help_page(pool, "no-such-slug") is None


@pytest.mark.req("agentic-mcp-orchestration:1.6")
async def test_help_read_hit_shape():
    pool = _pool(_row())
    result = await help_read(identity=None, args={"slug": "how-to-pay"}, db_pool=pool)
    assert result == {
        "ok": True,
        "data": {
            "slug": "how-to-pay",
            "title": "怎麼繳費",
            "text": "請至租客頁面點選繳費。",
            "version": "v1",
            "citable": False,
        },
        "provenance": [
            {"source": "help:how-to-pay", "text": "請至租客頁面點選繳費。", "citable": False}
        ],
        "text_for_model": "請至租客頁面點選繳費。",
    }


@pytest.mark.req("agentic-mcp-orchestration:1.6")
async def test_help_read_no_match():
    pool = _pool(None)
    result = await help_read(identity=None, args={"slug": "missing-page"}, db_pool=pool)
    assert result == {"ok": False, "error": "NO_MATCH"}


@pytest.mark.req("agentic-mcp-orchestration:1.6")
@pytest.mark.parametrize("bad_slug", ["", "Has-Upper", "with space", "emoji😀", "a" * 65, None, 123])
async def test_help_read_invalid_slug(bad_slug):
    pool = _pool(_row())
    result = await help_read(identity=None, args={"slug": bad_slug}, db_pool=pool)
    assert result == {"ok": False, "error": "INVALID_INPUT"}
    pool.fetchrow.assert_not_awaited()


@pytest.mark.req("agentic-mcp-orchestration:1.6")
async def test_help_read_citable_false_row_readable_and_provenance_matches():
    pool = _pool(_row(slug="not-yet-approved", citable=False))
    result = await help_read(identity=None, args={"slug": "not-yet-approved"}, db_pool=pool)
    assert result["ok"] is True
    assert result["data"]["citable"] is False
    assert result["provenance"][0]["citable"] is False
