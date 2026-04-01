"""
測試 SOP 重複檢測功能

驗收標準：
- 生成 SOP 標題的 embedding
- 使用 pgvector 搜尋 vendor_sop_items 表（cosine similarity）
- 閾值：similarity > 0.85 視為相似
- 同時搜尋 loop_generated_knowledge 表（knowledge_type='sop', status IN ('pending', 'approved')）
- 返回相似 SOP 列表（id, title, similarity_score）
- 若檢測到相似 SOP，標註到 sop_config.similar_sops 欄位
"""

import asyncio
import os
import sys
import json
import psycopg2.pool
from typing import Dict, List

# 確保可以導入 sop_generator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sop_generator import SOPGenerator


async def test_detect_duplicate_sops():
    """測試 SOP 重複檢測功能"""

    print("=" * 60)
    print("測試 SOP 重複檢測功能")
    print("=" * 60)

    # 初始化資料庫連接
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5433')),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot_admin'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_admin_password')
    }

    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        **db_config
    )

    # 初始化 SOPGenerator
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ OPENAI_API_KEY 未設定，跳過測試")
        return

    generator = SOPGenerator(
        db_pool=db_pool,
        openai_api_key=openai_api_key,
        model="gpt-4o-mini"
    )

    # 測試案例 1: 檢測已存在的 SOP（假設已有租金繳納相關 SOP）
    print("\n測試 1: 檢測與已存在 SOP 的相似度")
    print("-" * 60)

    test_sop_title_1 = "租金繳納時間規定"
    test_sop_content_1 = """
    租金必須在每月 5 日前繳納至指定帳戶。
    逾期繳納將產生滯納金。
    如有特殊情況請提前聯繫客服。
    """

    result_1 = await generator._detect_duplicate_sops(
        vendor_id=2,  # 假設 vendor_id=2 有測試資料
        sop_title=test_sop_title_1,
        sop_content=test_sop_content_1
    )

    print(f"✅ 檢測結果: detected={result_1['detected']}")
    if result_1['detected']:
        print(f"   找到 {len(result_1['items'])} 個相似 SOP:")
        for item in result_1['items']:
            print(f"   - [{item['source_table']}] ID={item['id']}: {item['item_name']}")
            print(f"     相似度: {item['similarity_score']:.2%}")
    else:
        print("   未找到相似 SOP")

    # 測試案例 2: 完全不同的 SOP（應該不會檢測到相似）
    print("\n測試 2: 檢測完全不同的 SOP")
    print("-" * 60)

    test_sop_title_2 = "辦公室綠化植栽管理辦法"
    test_sop_content_2 = """
    辦公室綠化植栽應每週澆水一次。
    定期修剪葉片，保持美觀。
    如有枯萎現象請立即更換。
    """

    result_2 = await generator._detect_duplicate_sops(
        vendor_id=2,
        sop_title=test_sop_title_2,
        sop_content=test_sop_content_2
    )

    print(f"✅ 檢測結果: detected={result_2['detected']}")
    if result_2['detected']:
        print(f"   找到 {len(result_2['items'])} 個相似 SOP:")
        for item in result_2['items']:
            print(f"   - [{item['source_table']}] ID={item['id']}: {item['item_name']}")
            print(f"     相似度: {item['similarity_score']:.2%}")
    else:
        print("   未找到相似 SOP（符合預期）")

    # 測試案例 3: 測試整合到 _persist_sop() 流程
    print("\n測試 3: 測試 similar_knowledge 欄位儲存")
    print("-" * 60)

    # 準備測試 SOP 資料
    test_sop_data = {
        'item_name': '測試重複檢測 SOP',
        'content': '這是一個測試用的 SOP 內容，用於驗證重複檢測功能是否正常運作。',
        'trigger_mode': 'auto',
        'trigger_keywords': ['測試', '重複檢測'],
        'next_action': 'none',
        'next_form_id': None,
        'immediate_prompt': '',
        'keywords': ['測試', '重複'],
        'category_id': None,
        'group_id': None
    }

    # 生成 embedding
    combined_text = f"{test_sop_data['item_name']}\n\n{test_sop_data['content']}"
    test_embedding = await generator._generate_embedding(combined_text)

    if test_embedding:
        print(f"✅ 成功生成 embedding (維度: {len(test_embedding)})")

        # 測試持久化（包含重複檢測）
        try:
            sop_id = await generator._persist_sop(
                vendor_id=2,
                loop_id=999,  # 測試用的 loop_id
                gap_id=None,
                iteration=1,
                sop_data=test_sop_data,
                primary_embedding=test_embedding
            )

            if sop_id:
                print(f"✅ SOP 已保存 (ID: {sop_id})")

                # 檢查 similar_knowledge 欄位是否正確儲存
                conn = db_pool.getconn()
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT similar_knowledge
                        FROM loop_generated_knowledge
                        WHERE id = %s
                    """, (sop_id,))

                    row = cur.fetchone()
                    if row and row[0]:
                        similar_knowledge = json.loads(row[0])
                        print(f"✅ similar_knowledge 欄位已儲存:")
                        print(f"   detected: {similar_knowledge.get('detected')}")
                        print(f"   items count: {len(similar_knowledge.get('items', []))}")
                    else:
                        print("   similar_knowledge 欄位為空（可能沒有相似 SOP）")

                    # 清理測試資料
                    cur.execute("""
                        DELETE FROM loop_generated_knowledge
                        WHERE id = %s
                    """, (sop_id,))
                    conn.commit()
                    print("✅ 測試資料已清理")

                finally:
                    cur.close()
                    db_pool.putconn(conn)
            else:
                print("⚠️  SOP 保存失敗（可能因為重複檢查）")

        except Exception as e:
            print(f"❌ 測試失敗: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ 無法生成 embedding")

    # 關閉連接池
    db_pool.closeall()

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


async def test_pgvector_similarity_query():
    """測試 pgvector 相似度查詢的正確性"""

    print("\n" + "=" * 60)
    print("測試 pgvector 向量相似度查詢")
    print("=" * 60)

    # 初始化資料庫連接
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5433')),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot_admin'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_admin_password')
    }

    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        **db_config
    )

    # 初始化 SOPGenerator
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ OPENAI_API_KEY 未設定，跳過測試")
        return

    generator = SOPGenerator(
        db_pool=db_pool,
        openai_api_key=openai_api_key,
        model="gpt-4o-mini"
    )

    # 生成測試 embedding
    test_text = "租金每個月幾號要繳？"
    test_embedding = await generator._generate_embedding(test_text)

    if not test_embedding:
        print("❌ 無法生成 embedding")
        return

    print(f"✅ 成功生成測試 embedding (維度: {len(test_embedding)})")

    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        # 測試 vendor_sop_items 表的向量搜尋
        print("\n測試 vendor_sop_items 表:")
        cur.execute("""
            SELECT
                id,
                item_name,
                1 - (primary_embedding <=> %s::vector) AS similarity_score
            FROM vendor_sop_items
            WHERE vendor_id = 2
              AND primary_embedding IS NOT NULL
            ORDER BY primary_embedding <=> %s::vector ASC
            LIMIT 5
        """, (test_embedding, test_embedding))

        rows = cur.fetchall()
        print(f"找到 {len(rows)} 個結果:")
        for row in rows:
            print(f"  - ID={row[0]}: {row[1]}")
            print(f"    相似度: {row[2]:.2%}")

        # 測試 loop_generated_knowledge 表的向量搜尋
        print("\n測試 loop_generated_knowledge 表:")
        cur.execute("""
            SELECT
                id,
                question,
                knowledge_type,
                status,
                1 - (embedding <=> %s::vector) AS similarity_score
            FROM loop_generated_knowledge
            WHERE knowledge_type = 'sop'
              AND status IN ('pending', 'approved')
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector ASC
            LIMIT 5
        """, (test_embedding, test_embedding))

        rows = cur.fetchall()
        print(f"找到 {len(rows)} 個結果:")
        for row in rows:
            print(f"  - ID={row[0]}: {row[1]}")
            print(f"    類型: {row[2]}, 狀態: {row[3]}")
            print(f"    相似度: {row[4]:.2%}")

    finally:
        cur.close()
        db_pool.putconn(conn)
        db_pool.closeall()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 執行測試
    asyncio.run(test_detect_duplicate_sops())
    asyncio.run(test_pgvector_similarity_query())
