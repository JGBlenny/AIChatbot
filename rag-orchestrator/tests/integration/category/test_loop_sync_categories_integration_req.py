"""整合測試（真實 DB）：loop 同步寫入 knowledge_base 時 categories 正確落地。

驗證 category-multi-select 任務 4.2 之寫入接線：實際呼叫生產函式
`_sync_knowledge_to_production`，斷言新建之 knowledge_base 列 categories 由 to_categories
正規化而來（單值→單元素陣列；保留值剔除）。embedding client 以 fake 取代（不依賴外部）。
對應需求 1.1, 6.2, 2.2。
"""
import os

import asyncpg
import pytest

from routers.loop_knowledge import _sync_knowledge_to_production

pytestmark = pytest.mark.integration

_LOOP_ID = 163  # 既有 loop（vendor_id=2）


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


class _FakeEmbeddingClient:
    async def generate_embedding(self, text):
        return [0.0] * 1536

    def to_pgvector_format(self, emb):
        return "[" + ",".join(str(x) for x in emb) + "]"


@pytest.mark.req("category-multi-select:1.1")
async def test_loop_sync_populates_categories(monkeypatch):
    monkeypatch.setattr(
        "services.knowledge_completion_loop.embedding_client.get_loop_embedding_client",
        lambda: _FakeEmbeddingClient(),
    )
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    synced_id = None
    try:
        item = {
            "id": None,  # source_loop_knowledge_id（避免 FK，設 None）
            "loop_id": _LOOP_ID,
            "iteration": 1,
            "knowledge_type": "general",
            "question": "category-multi-select 整合測試問題",
            "answer": "整合測試答案",
            "category": "付款金流",
        }
        async with pool.acquire() as conn:
            result = await _sync_knowledge_to_production(conn, item)
            assert result["synced"] is True, result
            assert result["synced_to"] == "knowledge_base"
            synced_id = result["synced_id"]

            row = await conn.fetchrow(
                "SELECT category, categories FROM knowledge_base WHERE id = $1", synced_id
            )
            # 單值正規化為單元素陣列，作為主題 SoT
            assert list(row["categories"]) == ["付款金流"]
            # 單數 category 已退役：寫入路徑不再填單數欄位（主題一律走 categories）
            assert row["category"] is None
    finally:
        if synced_id is not None:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM knowledge_base WHERE id = $1", synced_id)
        await pool.close()
