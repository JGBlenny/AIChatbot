#!/usr/bin/env python3
"""
驗證知識庫分類追蹤功能
檢查欄位、索引、API 功能是否正常
"""
import psycopg2
import requests
import sys
import json

# 資料庫配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aichatbot_admin',
    'user': 'aichatbot',
    'password': 'aichatbot_password'
}

API_BASE = 'http://localhost:8100/api/v1/knowledge'

def check_database_columns():
    """檢查資料庫欄位"""
    print("=" * 70)
    print("1. 檢查資料庫欄位")
    print("=" * 70)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 檢查欄位是否存在
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'knowledge_base'
            AND column_name IN ('intent_classified_at', 'needs_reclassify')
            ORDER BY column_name
        """)

        columns = cursor.fetchall()

        expected_columns = {
            'intent_classified_at': 'timestamp without time zone',
            'needs_reclassify': 'boolean'
        }

        all_passed = True
        for col_name, data_type, default in columns:
            expected_type = expected_columns.get(col_name)
            if expected_type == data_type:
                print(f"✅ {col_name:30} {data_type:30} (default: {default})")
            else:
                print(f"❌ {col_name:30} {data_type:30} (expected: {expected_type})")
                all_passed = False

        # 檢查是否所有欄位都存在
        found_columns = {col[0] for col in columns}
        missing = set(expected_columns.keys()) - found_columns
        if missing:
            print(f"\n❌ 缺少欄位: {', '.join(missing)}")
            all_passed = False

        cursor.close()
        conn.close()

        return all_passed

    except Exception as e:
        print(f"❌ 資料庫檢查失敗: {e}")
        return False

def check_indexes():
    """檢查索引"""
    print("\n" + "=" * 70)
    print("2. 檢查索引")
    print("=" * 70)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 檢查索引是否存在
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'knowledge_base'
            AND indexname IN ('idx_kb_needs_reclassify', 'idx_kb_intent_confidence', 'idx_kb_intent_id')
            ORDER BY indexname
        """)

        indexes = cursor.fetchall()

        expected_indexes = {
            'idx_kb_needs_reclassify',
            'idx_kb_intent_confidence',
            'idx_kb_intent_id'
        }

        all_passed = True
        found_indexes = set()
        for idx_name, idx_def in indexes:
            found_indexes.add(idx_name)
            print(f"✅ {idx_name}")
            print(f"   {idx_def}")

        missing = expected_indexes - found_indexes
        if missing:
            print(f"\n⚠️  缺少索引（可能不是必須的）: {', '.join(missing)}")

        cursor.close()
        conn.close()

        return all_passed

    except Exception as e:
        print(f"❌ 索引檢查失敗: {e}")
        return False

def check_data_integrity():
    """檢查資料完整性"""
    print("\n" + "=" * 70)
    print("3. 檢查資料完整性")
    print("=" * 70)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 檢查已分類的知識是否有 intent_classified_at
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(intent_id) as classified,
                COUNT(CASE WHEN intent_id IS NOT NULL AND intent_classified_at IS NULL THEN 1 END) as missing_timestamp,
                COUNT(CASE WHEN needs_reclassify THEN 1 END) as needs_reclassify
            FROM knowledge_base
        """)

        total, classified, missing_timestamp, needs_reclassify = cursor.fetchone()

        print(f"總知識數:           {total}")
        print(f"已分類知識數:       {classified}")
        print(f"缺少分類時間戳:     {missing_timestamp}")
        print(f"需要重新分類:       {needs_reclassify}")

        all_passed = True
        if missing_timestamp > 0:
            print(f"⚠️  有 {missing_timestamp} 筆已分類知識缺少分類時間戳")
            all_passed = False
        else:
            print("✅ 所有已分類知識都有分類時間戳")

        cursor.close()
        conn.close()

        return all_passed

    except Exception as e:
        print(f"❌ 資料完整性檢查失敗: {e}")
        return False

def check_api_stats():
    """檢查統計 API"""
    print("\n" + "=" * 70)
    print("4. 檢查統計 API")
    print("=" * 70)

    try:
        response = requests.get(f"{API_BASE}/stats", timeout=5)

        if response.status_code == 200:
            data = response.json()

            print("✅ API 回應成功")
            print(f"\n整體統計:")
            overall = data.get('overall', {})
            for key, value in overall.items():
                print(f"  {key:30} {value}")

            print(f"\n按意圖統計 (前 5 個):")
            by_intent = data.get('by_intent', [])[:5]
            for intent in by_intent:
                print(f"  [{intent['id']}] {intent['name']:20} 知識數: {intent['knowledge_count']:3} 需重分類: {intent['needs_reclassify_count']:3}")

            # 檢查是否包含必要欄位
            required_fields = ['needs_reclassify_count']
            all_passed = True
            for field in required_fields:
                if field not in overall:
                    print(f"❌ 缺少欄位: {field}")
                    all_passed = False

            return all_passed
        else:
            print(f"❌ API 回應失敗: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"❌ API 檢查失敗: {e}")
        return False

def main():
    """主程式"""
    print("\n" + "=" * 70)
    print("知識庫分類追蹤功能驗證")
    print("=" * 70 + "\n")

    results = []

    # 執行檢查
    results.append(("資料庫欄位", check_database_columns()))
    results.append(("索引", check_indexes()))
    results.append(("資料完整性", check_data_integrity()))
    results.append(("統計 API", check_api_stats()))

    # 總結
    print("\n" + "=" * 70)
    print("📊 檢查總結")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n✅ 所有檢查通過！分類追蹤功能可以正常使用")
        return 0
    else:
        print("\n❌ 部分檢查失敗，請查看上方詳細資訊")
        return 1

if __name__ == "__main__":
    sys.exit(main())
