#!/usr/bin/env python3
"""
端到端驗證：增強版重複問題檢測
清晰展示每個步驟和結果
"""
import asyncio
import asyncpg
import os
import sys

sys.path.insert(0, '/app')

async def verify():
    print("=" * 80)
    print("端到端驗證：增強版重複問題檢測")
    print("=" * 80)

    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        min_size=2,
        max_size=10
    )

    from services.unclear_question_manager import UnclearQuestionManager
    manager = UnclearQuestionManager(pool)

    try:
        # Step 1: 清理
        print("\n📌 步驟 1: 清理測試數據")
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM unclear_questions WHERE question LIKE '%測試驗證%'")
            count_before = await conn.fetchval("SELECT COUNT(*) FROM unclear_questions")
        print(f"   清理完成，當前總記錄數: {count_before}")

        # Step 2: 記錄原始問題
        print("\n📌 步驟 2: 記錄原始問題")
        q1 = "測試驗證每月租金幾號要繳"
        id1 = await manager.record_unclear_question(
            question=q1,
            user_id="verify_test",
            intent_type="unclear",
            similarity_score=0.65
        )
        print(f"   ✅ 原始問題記錄成功")
        print(f"      ID: {id1}")
        print(f"      問題: {q1}")

        # Step 3: 測試精確匹配
        print("\n📌 步驟 3: 測試精確匹配（完全相同）")
        id2 = await manager.record_unclear_question(
            question=q1,
            user_id="verify_test2",
            intent_type="unclear",
            similarity_score=0.65
        )
        if id2 == id1:
            print(f"   ✅ 精確匹配成功！ID 相同: {id2}")
        else:
            print(f"   ❌ 失敗：ID 不同 ({id1} vs {id2})")

        # Step 4: 測試編輯距離檢測
        print("\n📌 步驟 4: 測試編輯距離（單字錯誤）")
        q2 = "測試驗證每月住金幾號要繳"  # "租" → "住"
        print(f"   問題: {q2}")
        print(f"   差異: '租金' → '住金' (編輯距離 1)")
        id3 = await manager.record_unclear_question(
            question=q2,
            user_id="verify_test3",
            intent_type="unclear",
            similarity_score=0.65
        )
        if id3 == id1:
            print(f"   ✅ 編輯距離檢測成功！ID 相同: {id3}")
        else:
            print(f"   ❌ 失敗：ID 不同 ({id1} vs {id3})")

        # Step 5: 測試組合策略
        print("\n📌 步驟 5: 測試組合策略（輕微同音錯誤）")
        q3 = "測試驗證每月租金幾號較腳"  # "要繳" → "較腳"
        print(f"   問題: {q3}")
        print(f"   差異: '要繳' → '較腳' (同音錯誤，編輯距離 2)")
        id4 = await manager.record_unclear_question(
            question=q3,
            user_id="verify_test4",
            intent_type="unclear",
            similarity_score=0.65
        )
        if id4 == id1:
            print(f"   ✅ 組合策略成功！ID 相同: {id4}")
        else:
            print(f"   ❌ 失敗：ID 不同 ({id1} vs {id4})")

        # Step 6: 查詢最終結果
        print("\n📌 步驟 6: 查詢最終結果")
        async with pool.acquire() as conn:
            records = await conn.fetch("""
                SELECT id, question, frequency, status
                FROM unclear_questions
                WHERE question LIKE '%測試驗證%'
                ORDER BY id
            """)

        print(f"\n   共找到 {len(records)} 筆記錄：")
        for r in records:
            print(f"\n   ID: {r['id']}")
            print(f"   問題: {r['question']}")
            print(f"   頻率: {r['frequency']}")
            print(f"   狀態: {r['status']}")

        # 評估
        print("\n" + "=" * 80)
        print("驗證結果")
        print("=" * 80)

        if len(records) == 1:
            freq = records[0]['frequency']
            print(f"✅ 完美！4 個測試問題全部合併為 1 筆記錄")
            print(f"   最終頻率: {freq}/4")
            if freq == 4:
                print("   ✅ 頻率計數正確！")
                print("\n🎉 增強版去重檢測驗證通過！")
            else:
                print(f"   ⚠️  頻率不符: 期望 4，實際 {freq}")
        else:
            print(f"⚠️  發現 {len(records)} 筆記錄，期望 1 筆")
            print("   某些檢測策略可能未正常運作")

    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(verify())
