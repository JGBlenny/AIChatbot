"""
測試重複檢測統計記錄功能 (Task 7.3)

驗收標準：
- 生成知識後執行重複檢測
- 檢測結果寫入 loop_generated_knowledge 表（similar_knowledge 欄位）
- 記錄檢測統計到 loop_execution_logs（檢測到的相似知識數量、相似度分布）
- 統計資訊格式正確（total_generated, detected_duplicates, duplicate_rate, similarity_scores）
"""

import asyncio
import os
import sys
import json
import psycopg2.pool
from typing import Dict, List

# 確保可以導入模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sop_generator import SOPGenerator
from knowledge_generator import KnowledgeGeneratorClient


async def test_sop_stats_logging():
    """測試 SOP 重複檢測統計記錄"""

    print("=" * 60)
    print("測試 SOP 重複檢測統計記錄功能")
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

    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ OPENAI_API_KEY 未設定，跳過測試")
        return

    generator = SOPGenerator(
        db_pool=db_pool,
        openai_api_key=openai_api_key,
        model="gpt-4o-mini"
    )

    # 測試案例：模擬生成的 SOP 項目（包含 similar_knowledge）
    print("\n測試 1: 直接測試統計記錄方法")
    print("-" * 60)

    test_generated_sops = [
        {
            'id': 1,
            'item_name': 'SOP 1',
            'similar_knowledge': {
                'detected': True,
                'items': [
                    {'id': 100, 'item_name': '相似 SOP 1', 'similarity_score': 0.92},
                    {'id': 101, 'item_name': '相似 SOP 2', 'similarity_score': 0.87}
                ]
            }
        },
        {
            'id': 2,
            'item_name': 'SOP 2',
            'similar_knowledge': {
                'detected': False,
                'items': []
            }
        },
        {
            'id': 3,
            'item_name': 'SOP 3',
            'similar_knowledge': {
                'detected': True,
                'items': [
                    {'id': 102, 'item_name': '相似 SOP 3', 'similarity_score': 0.89}
                ]
            }
        }
    ]

    # 創建測試用的 loop
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        # 創建測試 loop
        cur.execute("""
            INSERT INTO knowledge_completion_loops (
                loop_name, vendor_id, status, current_iteration,
                target_pass_rate, max_iterations, config,
                created_at
            ) VALUES ('test_stats_loop', 2, 'running', 1, 0.85, 10, '{}', NOW())
            RETURNING id
        """)
        test_loop_id = cur.fetchone()[0]
        conn.commit()

        print(f"✅ 創建測試 loop (ID: {test_loop_id})")

        # 測試統計記錄
        await generator._log_duplicate_detection_stats(
            loop_id=test_loop_id,
            iteration=1,
            knowledge_type='sop',
            generated_items=test_generated_sops
        )

        # 驗證統計記錄
        cur.execute("""
            SELECT event_type, event_data
            FROM loop_execution_logs
            WHERE loop_id = %s
              AND event_type = 'duplicate_detection_sop'
            ORDER BY created_at DESC
            LIMIT 1
        """, (test_loop_id,))

        log_row = cur.fetchone()
        if log_row:
            event_type, event_data = log_row
            # event_data 已經是字典（JSONB 類型）
            stats = event_data if isinstance(event_data, dict) else json.loads(event_data)

            print(f"\n✅ 統計記錄已儲存:")
            print(f"   Event Type: {event_type}")
            print(f"   總生成數: {stats['total_generated']}")
            print(f"   檢測到重複: {stats['detected_duplicates']}")
            print(f"   重複率: {stats['duplicate_rate']}")
            print(f"   相似度統計:")
            print(f"     - 數量: {stats['similarity_scores']['count']}")
            print(f"     - 平均: {stats['similarity_scores']['avg']:.2%}")
            print(f"     - 最大: {stats['similarity_scores']['max']:.2%}")
            print(f"     - 最小: {stats['similarity_scores']['min']:.2%}")

            # 驗證數據正確性
            assert stats['total_generated'] == 3, "總生成數應為 3"
            assert stats['detected_duplicates'] == 2, "檢測到重複應為 2"
            assert stats['duplicate_rate'] == "66.7%", "重複率應為 66.7%"
            assert stats['similarity_scores']['count'] == 3, "相似度數量應為 3"
            assert abs(stats['similarity_scores']['avg'] - 0.8933) < 0.001, "平均相似度應為 89.33%"
            assert stats['similarity_scores']['max'] == 0.92, "最大相似度應為 92%"
            assert stats['similarity_scores']['min'] == 0.87, "最小相似度應為 87%"

            print("\n✅ 所有驗證通過！")
        else:
            print("❌ 未找到統計記錄")

        # 清理測試資料
        cur.execute("DELETE FROM loop_execution_logs WHERE loop_id = %s", (test_loop_id,))
        cur.execute("DELETE FROM knowledge_completion_loops WHERE id = %s", (test_loop_id,))
        conn.commit()
        print("✅ 測試資料已清理")

    finally:
        cur.close()
        db_pool.putconn(conn)

    db_pool.closeall()

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


async def test_knowledge_stats_logging():
    """測試一般知識重複檢測統計記錄"""

    print("\n" + "=" * 60)
    print("測試一般知識重複檢測統計記錄功能")
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

    openai_api_key = os.getenv('OPENAI_API_KEY')

    generator = KnowledgeGeneratorClient(
        openai_api_key=openai_api_key,
        db_pool=db_pool,
        model="gpt-4o-mini"
    )

    # 測試案例：模擬生成的知識項目（包含 similar_knowledge）
    print("\n測試 1: 直接測試統計記錄方法")
    print("-" * 60)

    test_generated_knowledge = [
        {
            'id': 1,
            'question': '租金何時繳納？',
            'similar_knowledge': {
                'detected': True,
                'items': [
                    {'id': 200, 'question_summary': '租金繳納時間', 'similarity_score': 0.95}
                ]
            }
        },
        {
            'id': 2,
            'question': '可以養寵物嗎？',
            'similar_knowledge': None  # 無相似知識
        },
        {
            'id': 3,
            'question': '如何申請停車位？',
            'similar_knowledge': {
                'detected': False,
                'items': []
            }
        }
    ]

    # 創建測試用的 loop
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        # 創建測試 loop
        cur.execute("""
            INSERT INTO knowledge_completion_loops (
                loop_name, vendor_id, status, current_iteration,
                target_pass_rate, max_iterations, config,
                created_at
            ) VALUES ('test_stats_loop', 2, 'running', 1, 0.85, 10, '{}', NOW())
            RETURNING id
        """)
        test_loop_id = cur.fetchone()[0]
        conn.commit()

        print(f"✅ 創建測試 loop (ID: {test_loop_id})")

        # 測試統計記錄
        await generator._log_duplicate_detection_stats(
            loop_id=test_loop_id,
            iteration=1,
            knowledge_type='knowledge',
            generated_items=test_generated_knowledge
        )

        # 驗證統計記錄
        cur.execute("""
            SELECT event_type, event_data
            FROM loop_execution_logs
            WHERE loop_id = %s
              AND event_type = 'duplicate_detection_knowledge'
            ORDER BY created_at DESC
            LIMIT 1
        """, (test_loop_id,))

        log_row = cur.fetchone()
        if log_row:
            event_type, event_data = log_row
            # event_data 已經是字典（JSONB 類型）
            stats = event_data if isinstance(event_data, dict) else json.loads(event_data)

            print(f"\n✅ 統計記錄已儲存:")
            print(f"   Event Type: {event_type}")
            print(f"   總生成數: {stats['total_generated']}")
            print(f"   檢測到重複: {stats['detected_duplicates']}")
            print(f"   重複率: {stats['duplicate_rate']}")
            print(f"   相似度統計:")
            print(f"     - 數量: {stats['similarity_scores']['count']}")
            if stats['similarity_scores']['count'] > 0:
                print(f"     - 平均: {stats['similarity_scores']['avg']:.2%}")
                print(f"     - 最大: {stats['similarity_scores']['max']:.2%}")
                print(f"     - 最小: {stats['similarity_scores']['min']:.2%}")

            # 驗證數據正確性
            assert stats['total_generated'] == 3, "總生成數應為 3"
            assert stats['detected_duplicates'] == 1, "檢測到重複應為 1"
            assert stats['duplicate_rate'] == "33.3%", "重複率應為 33.3%"
            assert stats['similarity_scores']['count'] == 1, "相似度數量應為 1"

            print("\n✅ 所有驗證通過！")
        else:
            print("❌ 未找到統計記錄")

        # 清理測試資料
        cur.execute("DELETE FROM loop_execution_logs WHERE loop_id = %s", (test_loop_id,))
        cur.execute("DELETE FROM knowledge_completion_loops WHERE id = %s", (test_loop_id,))
        conn.commit()
        print("✅ 測試資料已清理")

    finally:
        cur.close()
        db_pool.putconn(conn)

    db_pool.closeall()

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


if __name__ == "__main__":
    # 執行測試
    asyncio.run(test_sop_stats_logging())
    asyncio.run(test_knowledge_stats_logging())
