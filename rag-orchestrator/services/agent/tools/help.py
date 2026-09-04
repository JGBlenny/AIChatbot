"""help.read 工具（agentic-mcp-orchestration 任務 1.6）。

讀取 help_center_pages（見 database/migrations/20260904_create_help_center_pages.sql）。
匯入工具與 citable=true 的人工核可流程屬子 spec help-center-source，本檔只做讀取。
"""
import re
from dataclasses import dataclass
from typing import Any, Optional

_SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class HelpPage:
    slug: str
    title: str
    text: str
    version: str
    citable: bool


async def read_help_page(db_pool, slug: str) -> Optional[HelpPage]:
    """依 slug 讀單一 help_center_pages 列；查無回 None。"""
    row = await db_pool.fetchrow(
        "SELECT slug, title, text, version, citable FROM help_center_pages WHERE slug = $1",
        slug,
    )
    if row is None:
        return None
    return HelpPage(
        slug=row["slug"],
        title=row["title"],
        text=row["text"],
        version=row["version"],
        citable=row["citable"],
    )


async def help_read(identity, args: dict, *, db_pool) -> dict[str, Any]:
    """MCP 工具入口：{"slug": str} → ToolResult 形狀的 dict。"""
    slug = args.get("slug")
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        return {"ok": False, "error": "INVALID_INPUT"}

    page = await read_help_page(db_pool, slug)
    if page is None:
        return {"ok": False, "error": "NO_MATCH"}

    return {
        "ok": True,
        "data": {
            "slug": page.slug,
            "title": page.title,
            "text": page.text,
            "version": page.version,
            "citable": page.citable,
        },
        "provenance": [
            {"source": f"help:{page.slug}", "text": page.text, "citable": page.citable}
        ],
        "text_for_model": page.text,
    }
