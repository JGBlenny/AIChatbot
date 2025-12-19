#!/usr/bin/env python3
"""
更新所有知識的 embedding 以包含 keywords（方案 A）
不會將 embedding 設為 NULL，直接更新以避免影響系統運作
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

def update_all_embeddings_with_keywords():
    """更新所有知識的 embedding 以包含 keywords"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # 1. 查詢所有知識（包含已有 embedding 的）
        cursor.execute("""
            SELECT id, question_summary, answer, keywords
            FROM knowledge_base
            ORDER BY id
        """)

        rows = cursor.fetchall()
        total = len(rows)

        if total == 0:
            print("⚠️  資料庫中沒有任何知識")
            return

        print(f"📋 找到 {total} 筆知識需要更新 embedding")
        print("-" * 60)

        # 確認執行（支援 --yes 參數跳過確認）
        if '--yes' not in sys.argv and '-y' not in sys.argv:
            confirm = input(f"\n⚠️  即將更新 {total} 筆知識的 embedding（包含 keywords）\n這將會呼叫 {total} 次 Embedding API\n確認繼續？(y/N): ").strip().lower()
            if confirm != 'y':
                print("❌ 已取消更新")
                return 1
        else:
            print("\n✅ 使用 --yes 參數，自動確認執行")

        # 2. 逐筆更新 embedding
        success_count = 0
        fail_count = 0
        skip_count = 0

        for i, (kb_id, question, answer, keywords) in enumerate(rows, 1):
            print(f"\n[{i}/{total}] 處理 ID {kb_id}: {question}")

            # ✅ 方案 A：將 keywords 融入 embedding
            keywords_str = ", ".join(keywords) if keywords else ""
            base_text = question if question else answer[:200]

            if keywords_str:
                text_for_embedding = f"{base_text}. 關鍵字: {keywords_str}"
                print(f"   📝 包含關鍵字: {keywords_str}")
            else:
                text_for_embedding = base_text
                print(f"   ⚠️  無關鍵字，僅使用問題摘要")

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
                print(f"   ✓ 成功更新 embedding")
            else:
                fail_count += 1
                print(f"   ✗ 更新失敗")

            # 避免 API 請求過快
            time.sleep(0.1)

            # 每 50 筆顯示進度
            if i % 50 == 0:
                print(f"\n{'='*60}")
                print(f"進度: {i}/{total} ({i*100//total}%)")
                print(f"成功: {success_count}, 失敗: {fail_count}")
                print(f"{'='*60}")

        print("\n" + "=" * 60)
        print("✅ 更新完成！")
        print("=" * 60)
        print(f"總數：{total}")
        print(f"成功：{success_count}")
        print(f"失敗：{fail_count}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        conn.rollback()
        return 1
    finally:
        cursor.close()
        conn.close()

    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    print("=" * 60)
    print("更新知識庫 Embedding（包含 Keywords）")
    print("方案 A：將 keywords 融入 embedding")
    print("=" * 60)
    sys.exit(update_all_embeddings_with_keywords())
