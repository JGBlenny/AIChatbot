#!/usr/bin/env python3
"""
為測試數據生成 embedding - 2026-01-24
"""

import psycopg2
import requests
import json
import time

# 配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'aichatbot',
    'password': 'aichatbot_password',
    'database': 'aichatbot_admin'
}

EMBEDDING_API_URL = "http://localhost:5001/api/v1/embeddings"

def get_embedding(text):
    """調用 embedding API 生成向量"""
    try:
        response = requests.post(
            EMBEDDING_API_URL,
            json={"text": text},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result['embedding']
    except Exception as e:
        print(f"❌ 生成 embedding 失敗: {e}")
        return None

def update_knowledge_embeddings(conn):
    """更新 knowledge_base 的 embedding"""
    cursor = conn.cursor()

    # 獲取需要更新的知識
    cursor.execute("""
        SELECT id, question_summary
        FROM knowledge_base
        WHERE vendor_id = 1
        AND question_summary LIKE '【測試】%'
        AND embedding IS NULL
    """)

    records = cursor.fetchall()
    print(f"\n📝 找到 {len(records)} 條知識需要生成 embedding")

    for kid, question in records:
        print(f"\n處理知識 {kid}: {question[:50]}...")
        embedding = get_embedding(question)

        if embedding:
            cursor.execute("""
                UPDATE knowledge_base
                SET embedding = %s::vector
                WHERE id = %s
            """, (str(embedding), kid))
            print(f"✅ 已更新知識 {kid}")
            time.sleep(0.5)  # 避免 API 限流
        else:
            print(f"❌ 跳過知識 {kid}")

    conn.commit()
    cursor.close()

def update_sop_embeddings(conn):
    """更新 vendor_sop_items 的 primary_embedding"""
    cursor = conn.cursor()

    # 獲取需要更新的 SOP
    cursor.execute("""
        SELECT id, item_name, content
        FROM vendor_sop_items
        WHERE vendor_id = 1
        AND item_name LIKE '【測試】%'
        AND primary_embedding IS NULL
    """)

    records = cursor.fetchall()
    print(f"\n📝 找到 {len(records)} 條 SOP 需要生成 embedding")

    for sid, name, content in records:
        print(f"\n處理 SOP {sid}: {name[:50]}...")
        # 使用 item_name + content 生成 embedding
        text = f"{name}\n{content}"
        embedding = get_embedding(text)

        if embedding:
            cursor.execute("""
                UPDATE vendor_sop_items
                SET primary_embedding = %s::vector
                WHERE id = %s
            """, (str(embedding), sid))
            print(f"✅ 已更新 SOP {sid}")
            time.sleep(0.5)  # 避免 API 限流
        else:
            print(f"❌ 跳過 SOP {sid}")

    conn.commit()
    cursor.close()

def main():
    print("=" * 60)
    print("為測試數據生成 Embedding")
    print("=" * 60)

    # 連接資料庫
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ 資料庫連接成功")
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        return

    # 更新知識庫 embedding
    update_knowledge_embeddings(conn)

    # 更新 SOP embedding
    update_sop_embeddings(conn)

    # 驗證結果
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM knowledge_base
        WHERE vendor_id = 1 AND question_summary LIKE '【測試】%' AND embedding IS NOT NULL
    """)
    kb_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM vendor_sop_items
        WHERE vendor_id = 1 AND item_name LIKE '【測試】%' AND primary_embedding IS NOT NULL
    """)
    sop_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ 完成！")
    print(f"   - Knowledge embedding: {kb_count} 條")
    print(f"   - SOP embedding: {sop_count} 條")
    print("=" * 60)

if __name__ == "__main__":
    main()
