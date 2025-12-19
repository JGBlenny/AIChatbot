#!/usr/bin/env python3
"""
生成意圖 Embeddings 腳本
用途：為所有意圖生成向量表示，支持語義意圖匹配

執行方式：
    python3 scripts/generate_intent_embeddings.py
    python3 scripts/generate_intent_embeddings.py --yes  # 自動確認
"""

import os
import sys
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# 資料庫配置
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'aichatbot_admin'),
    'user': os.getenv('POSTGRES_USER', 'aichatbot'),
    'password': os.getenv('POSTGRES_PASSWORD', 'aichatbot_password')
}

# Embedding API 配置
EMBEDDING_API_URL = os.getenv('EMBEDDING_API_URL', 'http://localhost:5001/api/v1/embeddings')

def get_db_connection():
    """建立資料庫連接"""
    return psycopg2.connect(**DB_CONFIG)

def generate_embedding(text: str) -> list:
    """
    調用 Embedding API 生成向量

    Args:
        text: 要生成向量的文本

    Returns:
        1536 維的向量列表，失敗返回 None
    """
    try:
        response = requests.post(
            EMBEDDING_API_URL,
            json={'input': text},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['embedding']

        print(f"⚠️  Embedding API 錯誤: {response.status_code} - {response.text}")
        return None

    except Exception as e:
        print(f"⚠️  Embedding API 調用失敗: {str(e)}")
        return None

def get_intents_without_embedding():
    """
    獲取所有沒有 embedding 或 embedding 為 NULL 的意圖

    Returns:
        意圖列表 [{'id': 1, 'name': '租金繳費', 'description': '...'}, ...]
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, description
                FROM intents
                WHERE embedding IS NULL
                ORDER BY id
            """)
            return cur.fetchall()
    finally:
        conn.close()

def get_all_intents():
    """
    獲取所有意圖（用於完整更新）

    Returns:
        意圖列表
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, description
                FROM intents
                ORDER BY id
            """)
            return cur.fetchall()
    finally:
        conn.close()

def update_intent_embedding(intent_id: int, embedding: list):
    """
    更新意圖的 embedding

    Args:
        intent_id: 意圖 ID
        embedding: 1536 維向量

    Returns:
        True 成功，False 失敗
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 將 embedding 轉換為 PostgreSQL 向量格式
            vector_str = '[' + ','.join(map(str, embedding)) + ']'

            cur.execute("""
                UPDATE intents
                SET embedding = %s::vector
                WHERE id = %s
            """, (vector_str, intent_id))

            conn.commit()
            return True

    except Exception as e:
        print(f"⚠️  更新 intent {intent_id} 失敗: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("生成意圖 Embeddings")
    print("用途：支持語義意圖匹配（方案2）")
    print("=" * 60)

    # 檢查是否自動確認
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    update_all = '--all' in sys.argv

    # 獲取需要更新的意圖
    if update_all:
        print("\n📋 模式：更新所有意圖（覆蓋現有 embedding）")
        intents = get_all_intents()
    else:
        print("\n📋 模式：只更新缺少 embedding 的意圖")
        intents = get_intents_without_embedding()

    if not intents:
        print("\n✅ 所有意圖都已有 embedding，無需更新")
        return

    print(f"📊 找到 {len(intents)} 個意圖需要生成 embedding")
    print("-" * 60)

    # 顯示意圖列表
    for intent in intents[:10]:  # 只顯示前 10 個
        print(f"   ID {intent['id']}: {intent['name']}")
        if intent['description']:
            desc_preview = intent['description'][:50] + '...' if len(intent['description']) > 50 else intent['description']
            print(f"      描述: {desc_preview}")

    if len(intents) > 10:
        print(f"   ... 還有 {len(intents) - 10} 個意圖")

    print("-" * 60)

    # 確認執行
    if not auto_confirm:
        confirm = input(f"\n是否繼續生成 {len(intents)} 個意圖的 embedding？(y/n): ")
        if confirm.lower() != 'y':
            print("❌ 已取消")
            return
    else:
        print("\n✅ 使用 --yes 參數，自動確認執行")

    # 執行更新
    print(f"\n🚀 開始生成 embeddings...")
    print("-" * 60)

    success_count = 0
    fail_count = 0
    start_time = time.time()

    for idx, intent in enumerate(intents, 1):
        # 生成用於 embedding 的文本
        # 結合意圖名稱和描述
        text_for_embedding = intent['name']
        if intent['description']:
            text_for_embedding += f". {intent['description']}"

        print(f"\n[{idx}/{len(intents)}] 處理 ID {intent['id']}: {intent['name']}")
        print(f"   📝 文本: {text_for_embedding[:80]}{'...' if len(text_for_embedding) > 80 else ''}")

        # 生成 embedding
        embedding = generate_embedding(text_for_embedding)

        if embedding:
            # 更新到資料庫
            if update_intent_embedding(intent['id'], embedding):
                print(f"   ✓ 成功生成並更新 embedding ({len(embedding)} 維)")
                success_count += 1
            else:
                print(f"   ✗ embedding 生成成功但更新資料庫失敗")
                fail_count += 1
        else:
            print(f"   ✗ embedding 生成失敗")
            fail_count += 1

        # 每 10 個顯示進度
        if idx % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / idx
            remaining = avg_time * (len(intents) - idx)
            print(f"\n{'=' * 60}")
            print(f"進度: {idx}/{len(intents)} ({idx*100//len(intents)}%)")
            print(f"成功: {success_count}, 失敗: {fail_count}")
            print(f"預計剩餘時間: {remaining:.1f} 秒")
            print(f"{'=' * 60}")

    # 最終統計
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)
    print(f"總處理數: {len(intents)}")
    print(f"成功: {success_count}")
    print(f"失敗: {fail_count}")
    print(f"成功率: {success_count * 100 // len(intents)}%")
    print(f"總耗時: {total_time:.1f} 秒")
    print(f"平均每個: {total_time / len(intents):.2f} 秒")
    print("=" * 60)

    if fail_count > 0:
        print(f"\n⚠️  有 {fail_count} 個意圖處理失敗，請檢查日誌")
        sys.exit(1)
    else:
        print("\n🎉 所有意圖的 embedding 都已成功生成！")
        print("\n💡 提示：現在可以使用語義意圖匹配功能了")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用戶中斷執行")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 執行失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
