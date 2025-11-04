#!/usr/bin/env python3
"""
重新生成知識庫 embedding 的腳本
用於為現有知識庫條目生成缺失的 embedding
"""

import psycopg2
import requests
import time
import sys

# 資料庫設定
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aichatbot_admin',
    'user': 'aichatbot',
    'password': 'aichatbot_password'
}

# Embedding API URL
EMBEDDING_API_URL = "http://localhost:5001/api/v1/embeddings"

def get_embedding(text):
    """呼叫 Embedding API 生成向量"""
    try:
        response = requests.post(
            EMBEDDING_API_URL,
            json={"text": text},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['embedding']
        else:
            print(f"   ❌ Embedding API 錯誤: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ 呼叫 Embedding API 失敗: {e}")
        return None

def regenerate_all_embeddings():
    """重新生成所有缺失的 embedding"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # 1. 查詢所有沒有 embedding 的知識
        cursor.execute("""
            SELECT id, question_summary, answer
            FROM knowledge_base
            WHERE embedding IS NULL
            ORDER BY id
        """)

        rows = cursor.fetchall()
        total = len(rows)

        if total == 0:
            print("✅ 所有知識庫條目都已有 embedding")
            return

        print(f"📋 找到 {total} 筆需要生成 embedding 的知識")
        print("-" * 60)

        # 2. 逐筆生成 embedding
        success_count = 0
        fail_count = 0

        for i, (kb_id, question, answer) in enumerate(rows, 1):
            print(f"[{i}/{total}] 處理 ID {kb_id}: {question}")

            # 使用問題摘要來生成 embedding
            text_for_embedding = question if question else answer[:200]

            embedding = get_embedding(text_for_embedding)

            if embedding:
                # 更新資料庫
                cursor.execute("""
                    UPDATE knowledge_base
                    SET embedding = %s, updated_at = NOW()
                    WHERE id = %s
                """, (embedding, kb_id))
                conn.commit()
                success_count += 1
                print(f"   ✓ 成功生成 embedding")
            else:
                fail_count += 1
                print(f"   ✗ 生成失敗")

            # 避免 API 請求過快
            time.sleep(0.1)

        print("-" * 60)
        print(f"✅ 完成！成功: {success_count}, 失敗: {fail_count}")

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        conn.rollback()
        return 1
    finally:
        cursor.close()
        conn.close()

    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(regenerate_all_embeddings())
