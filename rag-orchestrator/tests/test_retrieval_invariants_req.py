"""T2 主幹確定性：檢索不變式（碰真實 DB、不碰 LLM）→ integration。

不斷言「該回哪一筆」（資料會變），改斷言「永遠該成立的規則」：
- 保留分類（系統脈絡／對話規則）永不出現在檢索結果。
- b2b + prospect 查詢只回 prospect 知識或 NULL（公開）——售前/業者隔離。

前提資料不存在時明確 skip（不假綠燈）。對應 testing-traceability R5.3。
需 RUN_INTEGRATION=1 與可連的 DB（沿用既有 integration 機制）。
"""
import os

import asyncpg
import pytest

from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2 as KB

pytestmark = [pytest.mark.integration]

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))


async def _connect():
    return await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.mark.req("testing-traceability:5.3")
async def test_reserved_categories_never_returned_as_answers():
    """不變式：任何查詢結果都不含 category∈{系統脈絡,對話規則} 的列。"""
    conn = await _connect()
    try:
        rows = await conn.fetch(
            "SELECT id FROM knowledge_base "
            "WHERE category = ANY($1::text[]) AND is_active = TRUE",
            [KB.SYSTEM_DOC_CATEGORY, KB.RULES_DOC_CATEGORY],
        )
    finally:
        await conn.close()
    reserved_ids = {r["id"] for r in rows}
    if not reserved_ids:
        pytest.skip("DB 無保留分類列 → 無法驗證排除（明確略過，非假綠燈）")

    retriever = KB()
    queried = False
    for q in ["對話規則", "系統脈絡", "售前顧問", "方案"]:
        results = await retriever.retrieve(
            q, vendor_id=VENDOR_ID, top_k=10, target_user="prospect", mode="b2b")
        queried = queried or bool(results)
        leaked = {r.get("id") for r in results} & reserved_ids
        assert not leaked, f"查詢 {q!r} 洩漏保留分類列 id={leaked}"
    if not queried:
        pytest.skip("所有查詢皆無結果（DB/embedding 環境）→ 無法實質驗證")


@pytest.mark.req("testing-traceability:5.3")
async def test_b2b_prospect_query_returns_only_prospect_or_public():
    """不變式：b2b + prospect 查詢，每筆 target_user 為 NULL 或含 prospect。"""
    retriever = KB()
    results = await retriever.retrieve(
        "我想了解方案適不適合我", vendor_id=VENDOR_ID, top_k=10,
        target_user="prospect", mode="b2b")
    if not results:
        pytest.skip("此查詢無結果 → 無法驗證隔離")
    for r in results:
        tu = r.get("target_user")
        assert tu is None or "prospect" in tu, \
            f"b2b prospect 查詢回了非 prospect 知識：id={r.get('id')} target_user={tu}"
