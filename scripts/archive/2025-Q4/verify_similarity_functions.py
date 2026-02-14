#!/usr/bin/env python3
"""
驗證相似度檢查函數
測試知識去重功能是否正常運作
"""
import os
import asyncio
import asyncpg
from openai import AsyncOpenAI

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'aichatbot',
    'password': 'aichatbot_password',
    'database': 'aichatbot_admin'
}


async def verify_similarity_functions():
    """驗證相似度檢查函數"""
    print("🔍 驗證相似度檢查函數\n")
    print("=" * 60)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 1. 檢查函數是否存在
        print("\n📋 檢查資料庫函數...")
        functions = await conn.fetch("""
            SELECT proname, pg_get_function_result(oid)
            FROM pg_proc
            WHERE proname IN (
                'find_similar_knowledge',
                'find_similar_knowledge_candidate',
                'find_similar_test_scenario',
                'check_knowledge_exists_by_similarity'
            )
            ORDER BY proname
        """)

        for func in functions:
            print(f"   ✅ {func['proname']}")

        # 2. 檢查必要欄位
        print("\n📊 檢查資料表欄位...")

        # knowledge_base.embedding
        kb_count = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'knowledge_base' AND column_name = 'embedding'
        """)
        print(f"   {'✅' if kb_count > 0 else '❌'} knowledge_base.embedding")

        # ai_generated_knowledge_candidates.question_embedding
        candidate_count = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'ai_generated_knowledge_candidates'
            AND column_name = 'question_embedding'
        """)
        print(f"   {'✅' if candidate_count > 0 else '❌'} ai_generated_knowledge_candidates.question_embedding")

        # test_scenarios.question_embedding
        scenario_count = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'test_scenarios'
            AND column_name = 'question_embedding'
        """)
        print(f"   {'✅' if scenario_count > 0 else '❌'} test_scenarios.question_embedding")

        # 3. 檢查 embedding 數據
        print("\n📈 Embedding 統計...")

        kb_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(embedding) as with_embedding
            FROM knowledge_base
        """)
        print(f"   知識庫: {kb_stats['with_embedding']}/{kb_stats['total']} 有 embedding")

        candidate_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(question_embedding) as with_embedding
            FROM ai_generated_knowledge_candidates
        """)
        print(f"   審核佇列: {candidate_stats['with_embedding']}/{candidate_stats['total']} 有 embedding")

        scenario_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(question_embedding) as with_embedding
            FROM test_scenarios
        """)
        print(f"   測試情境: {scenario_stats['with_embedding']}/{scenario_stats['total']} 有 embedding")

        # 4. 測試相似度查詢功能
        print("\n🧪 測試相似度查詢功能...")

        # 使用現有的測試情境 embedding 進行測試
        if scenario_stats['with_embedding'] > 0:
            test_scenario = await conn.fetchrow("""
                SELECT id, test_question, question_embedding
                FROM test_scenarios
                WHERE question_embedding IS NOT NULL
                LIMIT 1
            """)

            if test_scenario:
                print(f"\n   測試問題: {test_scenario['test_question'][:60]}...")

                # 測試綜合查詢函數
                result = await conn.fetchrow("""
                    SELECT * FROM check_knowledge_exists_by_similarity($1::vector, 0.85)
                """, test_scenario['question_embedding'])

                if result:
                    print(f"\n   查詢結果:")
                    print(f"   - 知識庫中存在: {result['exists_in_knowledge_base']}")
                    print(f"   - 審核佇列中存在: {result['exists_in_review_queue']}")
                    print(f"   - 測試情境中存在: {result['exists_in_test_scenarios']}")
                    if result['matched_question']:
                        print(f"   - 匹配問題: {result['matched_question'][:60]}...")
                        print(f"   - 相似度: {result['similarity_score']}")
                        print(f"   - 來源: {result['source_table']}")
                    print("\n   ✅ 相似度查詢功能正常")
                else:
                    print("   ⚠️  未找到相似知識（這是正常的）")

        # 5. 總結
        print("\n" + "=" * 60)
        print("📊 驗證結果總結")
        print("=" * 60)

        all_functions_exist = len(functions) == 4
        all_columns_exist = kb_count > 0 and candidate_count > 0 and scenario_count > 0

        if all_functions_exist and all_columns_exist:
            print("✅ 所有函數和欄位都已就緒")
            print("✅ 知識匯入的語意去重功能可以正常使用")
        else:
            print("⚠️  部分功能缺失，請檢查上方詳細資訊")

        print("\n💡 使用建議:")
        print("   1. 知識匯入時會自動生成 embedding")
        print("   2. 文字去重會檢查完全相同的問答")
        print("   3. 語意去重會檢查相似度 >= 0.85 的知識")
        print("   4. 去重會同時檢查：知識庫、審核佇列、測試情境")

    except Exception as e:
        print(f"\n❌ 驗證過程發生錯誤: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(verify_similarity_functions())
