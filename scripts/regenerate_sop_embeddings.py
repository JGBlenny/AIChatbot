#!/usr/bin/env python3
"""
重新生成所有 SOP Embeddings
修復 Primary Embedding 稀釋問題後的資料更新
"""

import asyncio
import asyncpg
import httpx
from typing import List

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "aichatbot_admin",
    "user": "aichatbot",
    "password": "aichatbot_password"
}

EMBEDDING_API_URL = "http://localhost:5001/api/v1/embeddings"


async def get_embedding(text: str) -> List[float]:
    """調用 Embedding API"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            EMBEDDING_API_URL,
            json={"text": text}
        )
        data = response.json()
        return data.get("embedding")


def to_pgvector_format(embedding: List[float]) -> str:
    """轉換為 pgvector 格式"""
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def regenerate_all_embeddings(vendor_id: int = 2):
    """重新生成指定 vendor 的所有 SOP embeddings"""

    print("="*100)
    print(f"🔄 開始重新生成 Vendor {vendor_id} 的 SOP Embeddings")
    print("="*100)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 1. 查詢所有需要更新的 SOP
        rows = await conn.fetch("""
            SELECT
                vsi.id,
                vsi.item_name,
                vsi.content,
                vsg.group_name
            FROM vendor_sop_items vsi
            LEFT JOIN vendor_sop_groups vsg ON vsi.group_id = vsg.id
            WHERE vsi.vendor_id = $1
              AND vsi.is_active = TRUE
            ORDER BY vsi.id
        """, vendor_id)

        total = len(rows)
        print(f"\n📊 找到 {total} 個 SOP 需要更新\n")

        success_count = 0
        failed_count = 0

        # 2. 逐個重新生成 embedding
        for i, row in enumerate(rows, 1):
            sop_id = row['id']
            item_name = row['item_name']
            content = row['content']
            group_name = row['group_name']

            print(f"[{i}/{total}] 處理 SOP ID: {sop_id} - {item_name}")

            try:
                # 生成 Primary Embedding (只使用 item_name)
                print(f"  🔄 生成 Primary: {item_name}")
                primary_embedding = await get_embedding(item_name)

                if not primary_embedding:
                    print(f"  ❌ Primary embedding 生成失敗")
                    failed_count += 1
                    continue

                # 生成 Fallback Embedding (content)
                print(f"  🔄 生成 Fallback: {content[:50]}...")
                fallback_embedding = await get_embedding(content)

                if not fallback_embedding:
                    print(f"  ❌ Fallback embedding 生成失敗")
                    failed_count += 1
                    continue

                # 轉換格式
                primary_vector = to_pgvector_format(primary_embedding)
                fallback_vector = to_pgvector_format(fallback_embedding)

                # 更新資料庫
                await conn.execute("""
                    UPDATE vendor_sop_items
                    SET primary_embedding = $1::vector,
                        fallback_embedding = $2::vector
                    WHERE id = $3
                """, primary_vector, fallback_vector, sop_id)

                print(f"  ✅ 成功更新")
                success_count += 1

                # 避免 API rate limit
                if i % 5 == 0:
                    await asyncio.sleep(0.5)

            except Exception as e:
                print(f"  ❌ 處理失敗: {e}")
                failed_count += 1

        # 3. 顯示結果
        print("\n" + "="*100)
        print("📊 重新生成完成")
        print("="*100)
        print(f"✅ 成功: {success_count}/{total}")
        print(f"❌ 失敗: {failed_count}/{total}")
        print(f"成功率: {success_count/total*100:.1f}%")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(regenerate_all_embeddings(vendor_id=2))
