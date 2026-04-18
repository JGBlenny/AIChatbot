"""
SOP Embedding 背景生成服務

提供異步、非阻塞的 embedding 生成功能，用於 CRUD 操作後的背景更新。
"""
import asyncio
import asyncpg
from typing import List, Optional
import os
from .embedding_utils import get_embedding_client


async def generate_sop_embeddings_async(
    db_pool: asyncpg.Pool,
    sop_item_id: int
) -> bool:
    """
    異步生成單個 SOP 的 embeddings（primary + fallback）

    Args:
        db_pool: 資料庫連接池
        sop_item_id: SOP 項目 ID

    Returns:
        bool: 是否成功生成
    """
    embedding_client = get_embedding_client()

    try:
        async with db_pool.acquire() as conn:
            # 1. 查詢 SOP 資料（包含 keywords）
            row = await conn.fetchrow("""
                SELECT
                    vsi.id,
                    vsi.item_name,
                    vsi.content,
                    vsi.keywords,
                    vsg.group_name
                FROM vendor_sop_items vsi
                LEFT JOIN vendor_sop_groups vsg ON vsi.group_id = vsg.id
                WHERE vsi.id = $1
            """, sop_item_id)

            if not row:
                print(f"❌ [SOP Embedding] SOP ID {sop_item_id} 不存在")
                return False

            item_name = row['item_name']
            content = row['content']
            group_name = row['group_name']
            keywords = row.get('keywords', [])

            # 2. 生成 primary embedding (只用 item_name，不包含 keywords)
            # 根據測試結果：keywords 透過獨立機制處理，不包含在 embedding 中
            # 這樣可以保持語意純度，避免關鍵字稀釋效應
            primary_text = item_name

            # 記錄但不使用關鍵字
            if keywords and len(keywords) > 0:
                print(f"📝 [SOP Embedding] 關鍵字將透過獨立機制處理: {keywords[:5]}")  # 只顯示前5個

            print(f"🔄 [SOP Embedding] 生成 primary embedding for SOP {sop_item_id}: {primary_text[:50]}...")
            primary_embedding = await embedding_client.get_embedding(primary_text)

            if not primary_embedding:
                print(f"❌ [SOP Embedding] Primary embedding 生成失敗 (ID: {sop_item_id})")
                await _mark_embedding_failed(conn, sop_item_id)
                return False

            # 3. 生成 fallback embedding (content)
            print(f"🔄 [SOP Embedding] 生成 fallback embedding for SOP {sop_item_id}: {content[:50]}...")
            fallback_embedding = await embedding_client.get_embedding(content)

            if not fallback_embedding:
                print(f"❌ [SOP Embedding] Fallback embedding 生成失敗 (ID: {sop_item_id})")
                await _mark_embedding_failed(conn, sop_item_id)
                return False

            # 4. 轉換為 pgvector 格式
            primary_vector_str = embedding_client.to_pgvector_format(primary_embedding)
            fallback_vector_str = embedding_client.to_pgvector_format(fallback_embedding)

            # 5. 更新資料庫（含 embedding_status）
            await conn.execute("""
                UPDATE vendor_sop_items
                SET primary_embedding = $1::vector,
                    fallback_embedding = $2::vector,
                    embedding_status = 'completed',
                    embedding_updated_at = NOW()
                WHERE id = $3
            """,
                primary_vector_str,
                fallback_vector_str,
                sop_item_id
            )

            print(f"✅ [SOP Embedding] 成功生成 embeddings for SOP {sop_item_id}")
            return True

    except Exception as e:
        print(f"❌ [SOP Embedding] 生成失敗 (ID: {sop_item_id}): {e}")
        try:
            async with db_pool.acquire() as conn:
                await _mark_embedding_failed(conn, sop_item_id)
        except:
            pass
        return False


async def generate_batch_sop_embeddings_async(
    db_pool: asyncpg.Pool,
    sop_item_ids: List[int],
    batch_size: int = 5
) -> dict:
    """
    批次生成多個 SOP 的 embeddings

    Args:
        db_pool: 資料庫連接池
        sop_item_ids: SOP 項目 ID 列表
        batch_size: 批次大小（避免同時太多請求）

    Returns:
        dict: 生成結果統計 {"success": int, "failed": int, "total": int}
    """
    print(f"🔄 [SOP Embedding] 開始批次生成 {len(sop_item_ids)} 個 SOP embeddings")

    success_count = 0
    failed_count = 0

    # 分批處理，避免同時發送太多請求
    for i in range(0, len(sop_item_ids), batch_size):
        batch = sop_item_ids[i:i + batch_size]

        # 並發處理當前批次
        tasks = [
            generate_sop_embeddings_async(db_pool, sop_id)
            for sop_id in batch
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
            elif result:
                success_count += 1
            else:
                failed_count += 1

        print(f"📊 [SOP Embedding] 批次進度: {i + len(batch)}/{len(sop_item_ids)} ({success_count} 成功, {failed_count} 失敗)")

        # 批次間短暫延遲，避免 API rate limit
        if i + batch_size < len(sop_item_ids):
            await asyncio.sleep(0.5)

    print(f"✅ [SOP Embedding] 批次生成完成: {success_count}/{len(sop_item_ids)} 成功")

    return {
        "success": success_count,
        "failed": failed_count,
        "total": len(sop_item_ids)
    }


async def _mark_embedding_failed(conn: asyncpg.Connection, sop_item_id: int):
    """標記 embedding 生成失敗（記錄日誌）"""
    # 由於 embedding_status 欄位不存在於資料庫，僅記錄日誌
    print(f"❌ [SOP Embedding] SOP {sop_item_id} embedding 生成失敗")
    pass


def start_background_embedding_generation(
    db_pool: asyncpg.Pool,
    sop_item_id: int
):
    """
    啟動背景 embedding 生成任務（同步包裝函數）

    用於在同步函數中觸發異步任務
    """
    asyncio.create_task(
        generate_sop_embeddings_async(db_pool, sop_item_id)
    )


def start_batch_background_embedding_generation(
    db_pool: asyncpg.Pool,
    sop_item_ids: List[int]
):
    """
    啟動批次背景 embedding 生成任務（同步包裝函數）
    """
    asyncio.create_task(
        generate_batch_sop_embeddings_async(db_pool, sop_item_ids)
    )
