#!/usr/bin/env python3
"""
測試增強版重複問題檢測（三層策略）

測試目標：
1. 精確匹配
2. 組合策略：語義相似度 ≥ 0.80 OR 編輯距離 ≤ 2
3. 拼音檢測：語義 0.60-0.80 + 拼音相似度 ≥ 0.80
"""
import asyncio
import asyncpg
import os
import sys

# 添加 rag-orchestrator 到 Python 路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator')

from services.unclear_question_manager import UnclearQuestionManager


async def setup_test_db():
    """設置測試資料庫連接"""
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        min_size=2,
        max_size=10
    )
    return pool


async def clean_test_data(pool):
    """清理測試數據"""
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM unclear_questions
            WHERE question LIKE '%租金%' OR question LIKE '%住金%'
        """)
    print("🧹 已清理測試數據")


async def test_detection():
    """測試檢測功能"""
    print("=" * 80)
    print("測試增強版重複問題檢測")
    print("=" * 80)

    # 設置資料庫連接
    pool = await setup_test_db()
    manager = UnclearQuestionManager(pool)

    try:
        # 清理舊的測試數據
        await clean_test_data(pool)

        print("\n" + "=" * 80)
        print("測試案例 1: 記錄原始問題")
        print("=" * 80)
        original_id = await manager.record_unclear_question(
            question="每月租金幾號要繳",
            user_id="test_user",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"✅ 原始問題 ID: {original_id}")

        print("\n" + "=" * 80)
        print("測試案例 2: 精確匹配（完全相同問題）")
        print("=" * 80)
        test_id = await manager.record_unclear_question(
            question="每月租金幾號要繳",
            user_id="test_user2",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"期望: ID={original_id}, 實際: ID={test_id}")
        print(f"{'✅ 通過' if test_id == original_id else '❌ 失敗'}: 精確匹配")

        print("\n" + "=" * 80)
        print("測試案例 3: 組合策略 - 輕微同音錯誤（語義 0.8363, 編輯 2）")
        print("=" * 80)
        test_id = await manager.record_unclear_question(
            question="每月租金幾號較腳",
            user_id="test_user3",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"期望: ID={original_id}, 實際: ID={test_id}")
        print(f"{'✅ 通過' if test_id == original_id else '❌ 失敗'}: 組合策略（語義或編輯距離）")

        print("\n" + "=" * 80)
        print("測試案例 4: 組合策略 - 單字錯誤（語義 0.7633, 編輯 1）")
        print("=" * 80)
        test_id = await manager.record_unclear_question(
            question="每月住金幾號要繳",
            user_id="test_user4",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"期望: ID={original_id}, 實際: ID={test_id}")
        print(f"{'✅ 通過' if test_id == original_id else '❌ 失敗'}: 組合策略（編輯距離）")

        print("\n" + "=" * 80)
        print("測試案例 5: 拼音檢測 - 嚴重同音錯誤（語義 0.6039, 編輯 4）")
        print("=" * 80)
        test_id = await manager.record_unclear_question(
            question="美越租金幾號較腳",
            user_id="test_user5",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"期望: ID={original_id}, 實際: ID={test_id}")
        print(f"{'✅ 通過' if test_id == original_id else '⚠️  拼音檢測未命中（可能需要調整閾值）'}: 拼音檢測")

        print("\n" + "=" * 80)
        print("測試案例 6: 語義改寫（應該合併）")
        print("=" * 80)
        test_id = await manager.record_unclear_question(
            question="租金每個月幾號繳納",
            user_id="test_user6",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"期望: ID={original_id}, 實際: ID={test_id}")
        print(f"{'✅ 通過' if test_id == original_id else '❌ 失敗'}: 語義改寫檢測")

        # 查詢最終結果
        print("\n" + "=" * 80)
        print("最終結果統計")
        print("=" * 80)
        questions = await manager.get_unclear_questions(status="pending", limit=10)
        for q in questions:
            if '租金' in q['question'] or '住金' in q['question']:
                print(f"ID: {q['id']}, 問題: {q['question']}, 頻率: {q['frequency']}")

        # 查看統計
        stats = await manager.get_stats()
        print(f"\n總問題數: {stats['total']}")
        print(f"待處理: {stats['pending']}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_detection())
