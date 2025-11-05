#!/usr/bin/env python3
"""
檢查知識庫 Embedding 覆蓋率
用於確認批量生成向量是否成功
"""
import psycopg2
import sys

# 資料庫配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aichatbot_admin',
    'user': 'aichatbot',
    'password': 'aichatbot_password'
}

def check_embedding_coverage():
    """檢查 embedding 覆蓋率"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("\n" + "=" * 70)
        print("📊 知識庫 Embedding 覆蓋率檢查")
        print("=" * 70 + "\n")

        # 1. 總體統計
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(embedding) as has_embedding,
                COUNT(*) - COUNT(embedding) as missing_embedding,
                ROUND(100.0 * COUNT(embedding) / NULLIF(COUNT(*), 0), 2) as coverage_rate
            FROM knowledge_base
        """)

        total, has_embedding, missing_embedding, coverage_rate = cursor.fetchone()

        print(f"總知識數:           {total}")
        print(f"已有向量:           {has_embedding}")
        print(f"缺少向量:           {missing_embedding}")
        print(f"覆蓋率:             {coverage_rate}%")
        print()

        # 2. 按來源類型統計
        print("=" * 70)
        print("📋 按來源類型統計")
        print("=" * 70 + "\n")

        cursor.execute("""
            SELECT
                COALESCE(source_type, 'unknown') as source_type,
                COUNT(*) as total,
                COUNT(embedding) as has_embedding,
                COUNT(*) - COUNT(embedding) as missing_embedding,
                ROUND(100.0 * COUNT(embedding) / NULLIF(COUNT(*), 0), 2) as coverage_rate
            FROM knowledge_base
            GROUP BY source_type
            ORDER BY total DESC
        """)

        rows = cursor.fetchall()

        print(f"{'來源類型':<20} {'總數':<10} {'有向量':<10} {'缺少':<10} {'覆蓋率':<10}")
        print("-" * 70)
        for source_type, total, has_emb, missing, rate in rows:
            print(f"{source_type:<20} {total:<10} {has_emb:<10} {missing:<10} {rate}%")
        print()

        # 3. 按意圖統計
        print("=" * 70)
        print("📌 按意圖統計（前 10 個）")
        print("=" * 70 + "\n")

        cursor.execute("""
            SELECT
                COALESCE(i.name, '未分類') as intent_name,
                COUNT(kb.id) as total,
                COUNT(kb.embedding) as has_embedding,
                COUNT(kb.id) - COUNT(kb.embedding) as missing_embedding,
                ROUND(100.0 * COUNT(kb.embedding) / NULLIF(COUNT(kb.id), 0), 2) as coverage_rate
            FROM knowledge_base kb
            LEFT JOIN intents i ON kb.intent_id = i.id
            GROUP BY i.name
            ORDER BY total DESC
            LIMIT 10
        """)

        rows = cursor.fetchall()

        print(f"{'意圖名稱':<20} {'總數':<10} {'有向量':<10} {'缺少':<10} {'覆蓋率':<10}")
        print("-" * 70)
        for intent_name, total, has_emb, missing, rate in rows:
            print(f"{intent_name:<20} {total:<10} {has_emb:<10} {missing:<10} {rate}%")
        print()

        # 4. 列出缺少 embedding 的知識（限制前 20 筆）
        if missing_embedding > 0:
            print("=" * 70)
            print(f"⚠️  缺少 Embedding 的知識（顯示前 20 筆）")
            print("=" * 70 + "\n")

            cursor.execute("""
                SELECT id, question_summary, source_type, created_at
                FROM knowledge_base
                WHERE embedding IS NULL
                ORDER BY id
                LIMIT 20
            """)

            rows = cursor.fetchall()

            print(f"{'ID':<8} {'問題摘要':<50} {'來源':<15} {'建立時間':<20}")
            print("-" * 120)
            for kb_id, question, source, created in rows:
                question_truncated = (question[:47] + '...') if question and len(question) > 50 else (question or 'N/A')
                print(f"{kb_id:<8} {question_truncated:<50} {source or 'N/A':<15} {str(created):<20}")

            if missing_embedding > 20:
                print(f"\n... 還有 {missing_embedding - 20} 筆缺少向量")
            print()

        # 5. 最近更新的向量（驗證批量生成是否執行）
        print("=" * 70)
        print("🕐 最近更新的向量（最新 10 筆）")
        print("=" * 70 + "\n")

        cursor.execute("""
            SELECT id, question_summary, source_type, updated_at
            FROM knowledge_base
            WHERE embedding IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 10
        """)

        rows = cursor.fetchall()

        print(f"{'ID':<8} {'問題摘要':<50} {'來源':<15} {'更新時間':<20}")
        print("-" * 120)
        for kb_id, question, source, updated in rows:
            question_truncated = (question[:47] + '...') if question and len(question) > 50 else (question or 'N/A')
            print(f"{kb_id:<8} {question_truncated:<50} {source or 'N/A':<15} {str(updated):<20}")
        print()

        cursor.close()
        conn.close()

        # 6. 總結
        print("=" * 70)
        print("📊 總結")
        print("=" * 70 + "\n")

        if missing_embedding == 0:
            print("✅ 所有知識都已生成向量！")
            return 0
        else:
            print(f"⚠️  還有 {missing_embedding} 筆知識缺少向量")
            print(f"   覆蓋率: {coverage_rate}%")
            print(f"\n建議執行批量生成向量：")
            print(f"   1. 前端：知識庫管理 -> 批量生成向量")
            print(f"   2. API: POST http://localhost:8000/api/knowledge/regenerate-embeddings")
            return 1

    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_embedding_coverage())
