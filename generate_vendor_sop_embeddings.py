#!/usr/bin/env python3
"""為 vendor SOP 生成 embedding"""

import requests
import psycopg2
import time
from datetime import datetime

# 配置
EMBEDDING_API = "http://localhost:5001/api/v1/embeddings"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "aichatbot_admin",
    "user": "aichatbot",
    "password": "aichatbot_password"
}

VENDOR_ID = 4

def get_embedding(text):
    """調用 embedding API"""
    try:
        response = requests.post(
            EMBEDDING_API,
            json={"text": text},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("embedding")
        else:
            print(f"  ❌ Embedding API 錯誤: {response.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ 調用 embedding API 失敗: {e}")
        return None

def main():
    print(f"為 Vendor {VENDOR_ID} 的 SOP 生成 embeddings...")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # 獲取所有需要生成 embedding 的 SOP items（包含 group_name）
        cur.execute("""
            SELECT vsi.id, vsi.item_name, vsi.content, vsg.group_name
            FROM vendor_sop_items vsi
            LEFT JOIN vendor_sop_groups vsg ON vsi.group_id = vsg.id
            WHERE vsi.vendor_id = %s
            AND (vsi.embedding_status = 'pending' OR vsi.embedding_status IS NULL
                 OR vsi.primary_embedding IS NULL OR vsi.fallback_embedding IS NULL)
            ORDER BY vsi.id
        """, (VENDOR_ID,))

        items = cur.fetchall()
        total = len(items)

        if total == 0:
            print("✅ 所有 SOP 項目都已有 embedding")
            return

        print(f"找到 {total} 個需要生成 embedding 的 SOP 項目\n")

        success_count = 0
        fail_count = 0

        for idx, (item_id, item_name, content, group_name) in enumerate(items, 1):
            print(f"[{idx}/{total}] 處理: {item_name} (ID: {item_id})")

            # 準備 primary embedding 文本 (group_name + item_name)
            if group_name:
                primary_text = f"{group_name}：{item_name}"
            else:
                primary_text = item_name

            # 準備 fallback embedding 文本 (content only)
            fallback_text = content

            # 生成 primary embedding
            print(f"  🔄 生成 primary embedding: {primary_text[:60]}...")
            primary_embedding = get_embedding(primary_text)

            if not primary_embedding:
                print(f"  ❌ Primary embedding 失敗")
                cur.execute("""
                    UPDATE vendor_sop_items
                    SET embedding_status = 'failed'
                    WHERE id = %s
                """, (item_id,))
                conn.commit()
                fail_count += 1
                continue

            # 生成 fallback embedding
            print(f"  🔄 生成 fallback embedding: {fallback_text[:60]}...")
            fallback_embedding = get_embedding(fallback_text)

            if not fallback_embedding:
                print(f"  ❌ Fallback embedding 失敗")
                cur.execute("""
                    UPDATE vendor_sop_items
                    SET embedding_status = 'failed'
                    WHERE id = %s
                """, (item_id,))
                conn.commit()
                fail_count += 1
                continue

            # 準備 embedding_text (for debugging)
            embedding_text = f"primary: {primary_text} | fallback: {fallback_text[:100]}"

            # 更新資料庫（同時更新 primary 和 fallback）
            cur.execute("""
                UPDATE vendor_sop_items
                SET
                    primary_embedding = %s,
                    fallback_embedding = %s,
                    embedding_text = %s,
                    embedding_updated_at = %s,
                    embedding_version = 'text-embedding-3-small',
                    embedding_status = 'completed'
                WHERE id = %s
            """, (primary_embedding, fallback_embedding, embedding_text, datetime.now(), item_id))
            conn.commit()
            print(f"  ✅ 成功")
            success_count += 1

            # 避免請求過快
            time.sleep(0.5)

        print("\n" + "=" * 60)
        print(f"完成：✅ {success_count} 成功 / ❌ {fail_count} 失敗")

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
