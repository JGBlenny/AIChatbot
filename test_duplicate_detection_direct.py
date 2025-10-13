#!/usr/bin/env python3
"""
直接測試未釐清問題管理器的去重功能
在 Docker 容器內執行，可以正確訪問 Embedding API
"""
import asyncio
import asyncpg
import os
import sys

async def test_duplicate_detection():
    """測試重複問題檢測"""
    print("=" * 80)
    print("測試增強版重複問題檢測（直接測試）")
    print("=" * 80)

    # 建立資料庫連接（使用 Docker 內部連接）
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        min_size=2,
        max_size=10
    )

    # 導入服務
    sys.path.insert(0, '/app')
    from services.unclear_question_manager import UnclearQuestionManager

    manager = UnclearQuestionManager(pool)

    try:
        # 清理測試數據
        print("\n🧹 清理測試數據...")
        async with pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM unclear_questions
                WHERE question LIKE '%租金%' OR question LIKE '%住金%'
            """)
        print("✅ 測試數據已清理")

        # 測試案例
        print("\n" + "=" * 80)
        print("測試案例 1: 記錄原始問題")
        print("=" * 80)
        original_id = await manager.record_unclear_question(
            question="每月租金幾號要繳",
            user_id="test_user",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"\n原始問題 ID: {original_id}")

        print("\n" + "=" * 80)
        print("測試案例 2: 精確匹配（完全相同問題）")
        print("=" * 80)
        test_id = await manager.record_unclear_question(
            question="每月租金幾號要繳",
            user_id="test_user2",
            intent_type="unclear",
            similarity_score=0.65
        )
        result = "✅ 通過" if test_id == original_id else "❌ 失敗"
        print(f"\n{result}: 期望 ID={original_id}, 實際 ID={test_id}")

        print("\n" + "=" * 80)
        print("測試案例 3: 組合策略 - 輕微同音錯誤")
        print("=" * 80)
        print("問題: 每月租金幾號較腳")
        print("預期: 語義相似度 0.8363, 編輯距離 2 → 應該合併")
        test_id = await manager.record_unclear_question(
            question="每月租金幾號較腳",
            user_id="test_user3",
            intent_type="unclear",
            similarity_score=0.65
        )
        result = "✅ 通過" if test_id == original_id else "❌ 失敗"
        print(f"\n{result}: 期望 ID={original_id}, 實際 ID={test_id}")

        print("\n" + "=" * 80)
        print("測試案例 4: 組合策略 - 單字錯誤")
        print("=" * 80)
        print("問題: 每月住金幾號要繳")
        print("預期: 語義相似度 0.7633, 編輯距離 1 → 應該合併")
        test_id = await manager.record_unclear_question(
            question="每月住金幾號要繳",
            user_id="test_user4",
            intent_type="unclear",
            similarity_score=0.65
        )
        result = "✅ 通過" if test_id == original_id else "❌ 失敗"
        print(f"\n{result}: 期望 ID={original_id}, 實際 ID={test_id}")

        print("\n" + "=" * 80)
        print("測試案例 5: 拼音檢測 - 嚴重同音錯誤")
        print("=" * 80)
        print("問題: 美越租金幾號較腳")
        print("預期: 語義相似度 0.6039, 編輯距離 4 → 需要拼音檢測")
        test_id = await manager.record_unclear_question(
            question="美越租金幾號較腳",
            user_id="test_user5",
            intent_type="unclear",
            similarity_score=0.65
        )
        if test_id == original_id:
            print(f"\n✅ 通過: 拼音檢測成功命中！ID={test_id}")
        else:
            print(f"\n⚠️  拼音檢測未命中: 期望 ID={original_id}, 實際 ID={test_id}")
            print("   這可能需要調整拼音相似度閾值")

        print("\n" + "=" * 80)
        print("測試案例 6: 語義改寫")
        print("=" * 80)
        print("問題: 租金每個月幾號繳納")
        print("預期: 語義相似度 > 0.85 → 應該合併")
        test_id = await manager.record_unclear_question(
            question="租金每個月幾號繳納",
            user_id="test_user6",
            intent_type="unclear",
            similarity_score=0.65
        )
        result = "✅ 通過" if test_id == original_id else "❌ 失敗"
        print(f"\n{result}: 期望 ID={original_id}, 實際 ID={test_id}")

        # 查詢最終結果
        print("\n" + "=" * 80)
        print("最終結果統計")
        print("=" * 80)
        questions = await manager.get_unclear_questions(status="pending", limit=10)

        rental_questions = [q for q in questions if '租金' in q['question'] or '住金' in q['question']]

        print(f"\n找到 {len(rental_questions)} 個租金相關的未釐清問題:")
        for q in rental_questions:
            print(f"\n  ID: {q['id']}")
            print(f"  問題: {q['question']}")
            print(f"  頻率: {q['frequency']}")

        # 評估結果
        print("\n" + "=" * 80)
        print("檢測效果評估")
        print("=" * 80)

        if len(rental_questions) == 1:
            freq = rental_questions[0]['frequency']
            print(f"✅ 完美！所有 6 個問題都被正確合併為 1 個")
            print(f"   合併後頻率: {freq}/6")
            if freq == 6:
                print("   ✅ 頻率計數完全正確！")
            elif freq >= 4:
                print("   ⚠️  部分合併成功")
            else:
                print("   ❌ 多數合併失敗")
        elif len(rental_questions) <= 3:
            total_freq = sum(q['frequency'] for q in rental_questions)
            print(f"⚠️  部分成功：6 個問題合併為 {len(rental_questions)} 個")
            print(f"   總頻率: {total_freq}/6")
        else:
            print(f"❌ 檢測效果不佳：6 個問題只合併為 {len(rental_questions)} 個")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_duplicate_detection())
