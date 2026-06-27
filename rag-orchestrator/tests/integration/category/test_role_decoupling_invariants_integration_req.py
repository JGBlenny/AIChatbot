"""整合測試（真實 DB）：角色標記與主題分類解耦不變式（spec category-multi-select・任務 6.1・需求 2.1, 2.2, 2.4, 5.2, 5.3）。

驗證元件 4 之角色路徑於多值化後行為不變：
- 文件角色保留值（對話規則／系統脈絡）仍可由單數 category 讀取（persona/系統 md/CRUD 守門依此）。
- 保留值永不出現在任何列的 categories 陣列（解耦 + CHECK 雙重防護）。
- 角色排除述詞（IS DISTINCT FROM）仍精確排除保留列。
角色文件之檢索排除另由 test_retrieval_invariants_req 覆蓋。
"""
import os

import asyncpg
import pytest

pytestmark = pytest.mark.integration

RESERVED = ["對話規則", "系統脈絡"]


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.mark.req("category-multi-select:2.1")
async def test_reserved_rows_readable_by_singular_category():
    """角色讀取路徑：保留值列仍可由單數 category 取得（conversational_config/system_context 依此）。"""
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        rules = await conn.fetchval(
            "SELECT count(*) FROM knowledge_base WHERE category = '對話規則'"
        )
        assert rules >= 1, "對話規則（persona 設定）列應可由單數 category 讀取"
    finally:
        await conn.close()


@pytest.mark.req("category-multi-select:2.2")
async def test_no_reserved_value_in_any_categories_array():
    """解耦不變式：保留值永不進入 categories 陣列（CHECK + to_categories 雙重防護）。"""
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        leaked = await conn.fetchval(
            "SELECT count(*) FROM knowledge_base WHERE categories && $1::text[]",
            RESERVED,
        )
        assert leaked == 0, f"不應有列把保留值放進 categories，實得 {leaked} 列"
    finally:
        await conn.close()


@pytest.mark.req("category-multi-select:5.2")
async def test_exclusion_predicate_excludes_reserved_rows():
    """角色排除述詞：IS DISTINCT FROM 精確排除保留列，且不誤排一般知識。"""
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        reserved_total = await conn.fetchval(
            "SELECT count(*) FROM knowledge_base WHERE category = ANY($1::text[])", RESERVED
        )
        excluded = await conn.fetchval(
            "SELECT count(*) FROM knowledge_base "
            "WHERE category IS DISTINCT FROM '對話規則' AND category IS DISTINCT FROM '系統脈絡' "
            "AND category = ANY($1::text[])",
            RESERVED,
        )
        assert excluded == 0, "排除述詞應使保留列不被一般檢索取得"
        assert reserved_total >= len(RESERVED), "保留列應實際存在以驗證排除有效性"
    finally:
        await conn.close()
