"""
測試一般知識重複檢測功能

驗收標準：
- 生成 question_summary 的 embedding
- 使用 pgvector 搜尋 knowledge_base 表（cosine similarity）
- 閾值：similarity > 0.90 視為相似
- 同時搜尋 loop_generated_knowledge 表（knowledge_type IS NULL, status IN ('pending', 'approved')）
- 返回相似知識列表（id, question_summary, similarity_score, source_table）
- 若檢測到相似知識，寫入 similar_knowledge 欄位
"""

import asyncio
import os
import sys
import json
import psycopg2.pool

# 確保可以導入 knowledge_generator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_generator import KnowledgeGeneratorClient


async def test_detect_duplicate_knowledge():
    """測試一般知識重複檢測功能"""

    print("=" * 60)
    print("測試一般知識重複檢測功能")
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

    # 初始化 KnowledgeGeneratorClient
    openai_api_key = os.getenv('OPENAI_API_KEY')

    generator = KnowledgeGeneratorClient(
        openai_api_key=openai_api_key,
        db_pool=db_pool,
        model="gpt-4o-mini"
    )

    # 測試案例 1: 檢測與已存在知識的相似度（假設已有租金相關知識）
    print("\n測試 1: 檢測與已存在知識的相似度")
    print("-" * 60)

    test_question_1 = "租金每個月幾號要繳納？"

    result_1 = await generator._detect_duplicate_knowledge(
        vendor_id=2,  # 假設 vendor_id=2 有測試資料
        question_summary=test_question_1
    )

    print(f"✅ 檢測結果: detected={result_1['detected']}")
    if result_1['detected']:
        print(f"   找到 {len(result_1['items'])} 個相似知識:")
        for item in result_1['items']:
            print(f"   - [{item['source_table']}] ID={item['id']}: {item['question_summary'][:50]}...")
            print(f"     相似度: {item['similarity_score']:.2%}")
    else:
        print("   未找到相似知識")

    # 測試案例 2: 完全不同的問題（應該不會檢測到相似）
    print("\n測試 2: 檢測完全不同的問題")
    print("-" * 60)

    test_question_2 = "辦公室植栽每週需要澆水幾次？"

    result_2 = await generator._detect_duplicate_knowledge(
        vendor_id=2,
        question_summary=test_question_2
    )

    print(f"✅ 檢測結果: detected={result_2['detected']}")
    if result_2['detected']:
        print(f"   找到 {len(result_2['items'])} 個相似知識:")
        for item in result_2['items']:
            print(f"   - [{item['source_table']}] ID={item['id']}: {item['question_summary'][:50]}...")
            print(f"     相似度: {item['similarity_score']:.2%}")
    else:
        print("   未找到相似知識（符合預期）")

    # 關閉連接池
    db_pool.closeall()

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


async def test_pgvector_similarity_query():
    """測試 pgvector 相似度查詢的正確性"""

    print("\n" + "=" * 60)
    print("測試 pgvector 向量相似度查詢（一般知識）")
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

    # 初始化 KnowledgeGeneratorClient
    openai_api_key = os.getenv('OPENAI_API_KEY')

    generator = KnowledgeGeneratorClient(
        openai_api_key=openai_api_key,
        db_pool=db_pool,
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

        # 測試 knowledge_base 表的向量搜尋
        print("\n測試 knowledge_base 表:")
        cur.execute("""
            SELECT
                id,
                question_summary,
                1 - (embedding <=> %s::vector) AS similarity_score
            FROM knowledge_base
            WHERE vendor_ids @> ARRAY[2]
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector ASC
            LIMIT 5
        """, (test_embedding, test_embedding))

        rows = cur.fetchall()
        print(f"找到 {len(rows)} 個結果:")
        for row in rows:
            print(f"  - ID={row[0]}: {row[1][:50]}...")
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
            WHERE knowledge_type IS NULL
              AND status IN ('pending', 'approved')
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector ASC
            LIMIT 5
        """, (test_embedding, test_embedding))

        rows = cur.fetchall()
        print(f"找到 {len(rows)} 個結果:")
        for row in rows:
            print(f"  - ID={row[0]}: {row[1][:50]}...")
            print(f"    類型: {row[2]}, 狀態: {row[3]}")
            print(f"    相似度: {row[4]:.2%}")

    finally:
        cur.close()
        db_pool.putconn(conn)
        db_pool.closeall()

    print("\n" + "=" * 60)


async def test_embedding_generation():
    """測試 embedding 生成功能"""

    print("\n" + "=" * 60)
    print("測試 Embedding 生成功能")
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

    # 初始化 KnowledgeGeneratorClient
    openai_api_key = os.getenv('OPENAI_API_KEY')

    generator = KnowledgeGeneratorClient(
        openai_api_key=openai_api_key,
        db_pool=db_pool,
        model="gpt-4o-mini"
    )

    # 測試案例
    test_texts = [
        "租金繳納時間規定",
        "可以養寵物嗎？",
        "如何申請停車位？"
    ]

    for text in test_texts:
        print(f"\n測試文本: {text}")
        embedding = await generator._generate_embedding(text)

        if embedding:
            print(f"✅ 成功生成 embedding (維度: {len(embedding)})")
            print(f"   前 5 個值: {embedding[:5]}")
        else:
            print("❌ 生成失敗")

    db_pool.closeall()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 執行測試
    asyncio.run(test_embedding_generation())
    asyncio.run(test_detect_duplicate_knowledge())
    asyncio.run(test_pgvector_similarity_query())
