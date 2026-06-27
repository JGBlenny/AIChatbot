"""補測試：主檢索 search() SELECT 夾帶 categories 唯讀 metadata（spec category-multi-select・任務 5.1・需求 5.2, 5.4）。

離線 unit：mock embedding + db_pool，捕捉 search() 送出的向量檢索 SQL，
斷言「凡選 kb.category 的分支亦夾帶 kb.categories」（兩者同進同出）。
備註：search() 共 6 個 SELECT 分支，僅 2 個（意圖×無 target_user×無業態 等）原本選 kb.category，
其餘 4 個本就不選——印證 category 為非承載性 metadata（無下游消費），Phase 2 清空安全。
本測試打中「帶意圖、無 target_users、vendor_id=None」分支（選 kb.category 者）。
"""
from unittest.mock import AsyncMock

import pytest

from services.rag_engine import RAGEngine

pytestmark = pytest.mark.unit


@pytest.mark.req("category-multi-select:5.2")
async def test_search_select_includes_categories(mock_db_pool):
    captured = {}

    async def fake_fetch(sql, *args):
        captured["sql"] = sql
        return []

    mock_db_pool._conn.fetch = fake_fetch
    eng = RAGEngine(db_pool=mock_db_pool)
    eng._get_embedding = AsyncMock(return_value=[0.1] * 1536)

    # 帶意圖 + 無 target_users + vendor_id=None → 走「選 kb.category」的分支
    await eng.search("測試查詢", intent_ids=[1], primary_intent_id=1,
                     target_users=None, vendor_id=None)

    assert "kb.category" in captured["sql"]       # 該分支原本即選單數 category
    assert "kb.categories" in captured["sql"]     # 唯讀多值 metadata 與之配對並存
