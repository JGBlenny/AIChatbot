"""端到端整合測試（真實 DB）：多主題知識可由其每一個主題接地撈得（spec category-multi-select・任務 8.1・需求 1.2, 3.1）。

實際插入一筆 categories=['退租結算','帳務問題'] 的知識，呼叫生產方法
`ConversationalEngine._grounding_by_category` 以「退租結算」與「帳務問題」分別接地，
兩者皆應撈得同一筆答案——證實一筆知識歸屬多主題時，任一主題接地皆涵蓋之。
"""
import os

import asyncpg
import pytest

from services.conversational_engine import ConversationalEngine

pytestmark = pytest.mark.integration

_MARK = "E2E多主題答案-category-multi-select"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.mark.req("category-multi-select:3.1")
async def test_multi_category_grounding_covers_every_topic():
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    kb_id = None
    try:
        async with pool.acquire() as conn:
            kb_id = await conn.fetchval(
                "INSERT INTO knowledge_base (question_summary, answer, categories, is_active) "
                "VALUES ($1, $2, $3, TRUE) RETURNING id",
                "多主題測試知識", _MARK, ["退租結算", "帳務問題"],
            )

        eng = ConversationalEngine(
            db_pool=pool, optimizer=None, retriever=None,
            get_system_context=None, rules_loader=None,
        )

        # 任一主題接地皆應涵蓋這筆多主題知識
        g1 = await eng._grounding_by_category("退租結算")
        g2 = await eng._grounding_by_category("帳務問題")
        assert _MARK in g1, "以『退租結算』接地應撈得多主題知識"
        assert _MARK in g2, "以『帳務問題』接地應撈得多主題知識"
    finally:
        if kb_id is not None:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM knowledge_base WHERE id = $1", kb_id)
        await pool.close()


@pytest.mark.req("category-multi-select:3.1")
async def test_grounding_by_parent_expands_to_children():
    """接地選父層『售前』應展開涵蓋子分類（如售前競品）的知識，與 admin 篩選一致。"""
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    kb_id = None
    try:
        async with pool.acquire() as conn:
            # priority 拉高，確保在父層群組(18 筆)的 LIMIT 8 內被撈到
            kb_id = await conn.fetchval(
                "INSERT INTO knowledge_base (question_summary, answer, categories, is_active, priority) "
                "VALUES ($1, $2, $3, TRUE, 99999) RETURNING id",
                "父層展開測試", _MARK, ["售前競品"],
            )
        eng = ConversationalEngine(
            db_pool=pool, optimizer=None, retriever=None,
            get_system_context=None, rules_loader=None,
        )
        # 選父層「售前」→ 應撈到掛子分類「售前競品」的這筆
        g = await eng._grounding_by_category("售前")
        assert _MARK in g, "以父層『售前』接地應展開涵蓋子分類『售前競品』的知識"
    finally:
        if kb_id is not None:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM knowledge_base WHERE id = $1", kb_id)
        await pool.close()
