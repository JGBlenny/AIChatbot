#!/usr/bin/env python3
"""
全面檢查審核函數的相關依賴
確保所有必要的表、欄位、函數都正確配置
"""
import asyncio
import asyncpg

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'aichatbot',
    'password': 'aichatbot_password',
    'database': 'aichatbot_admin'
}


async def comprehensive_check():
    """全面檢查審核功能的所有依賴"""
    print("=" * 70)
    print("🔍 全面檢查 approve_ai_knowledge_candidate 函數依賴")
    print("=" * 70)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # ============================================================
        # 1. 檢查函數簽名
        # ============================================================
        print("\n📋 1. 檢查函數簽名")
        print("-" * 70)

        functions = await conn.fetch("""
            SELECT
                p.proname,
                pg_get_function_arguments(p.oid) as arguments,
                pg_get_function_result(p.oid) as return_type
            FROM pg_proc p
            WHERE p.proname = 'approve_ai_knowledge_candidate'
        """)

        if len(functions) == 0:
            print("   ❌ 函數不存在")
        elif len(functions) > 1:
            print(f"   ⚠️  發現 {len(functions)} 個同名函數（應該只有 1 個）")
            for func in functions:
                print(f"      - {func['arguments']}")
        else:
            func = functions[0]
            print(f"   ✅ 函數存在")
            print(f"      參數: {func['arguments']}")
            print(f"      返回: {func['return_type']}")

            # 檢查參數數量
            arg_count = len([a for a in func['arguments'].split(',') if a.strip()])
            if arg_count == 4:
                print(f"      ✅ 參數數量正確：4 個")
            else:
                print(f"      ❌ 參數數量錯誤：{arg_count} 個（應為 4 個）")

        # ============================================================
        # 2. 檢查 knowledge_base 表欄位
        # ============================================================
        print("\n📋 2. 檢查 knowledge_base 表欄位")
        print("-" * 70)

        kb_columns = await conn.fetch("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'knowledge_base'
              AND column_name IN (
                  'question_summary', 'answer', 'intent_id', 'embedding',
                  'source_type', 'source_test_scenario_id', 'generation_metadata',
                  'target_user', 'is_active'
              )
            ORDER BY column_name
        """)

        required_kb_columns = {
            'question_summary', 'answer', 'intent_id', 'embedding',
            'source_type', 'source_test_scenario_id', 'generation_metadata',
            'target_user', 'is_active'
        }

        found_kb_columns = {col['column_name'] for col in kb_columns}

        for col in required_kb_columns:
            if col in found_kb_columns:
                col_info = next(c for c in kb_columns if c['column_name'] == col)
                print(f"   ✅ {col:30} {col_info['data_type']}")
            else:
                print(f"   ❌ {col:30} 缺失")

        # ============================================================
        # 3. 檢查 ai_generated_knowledge_candidates 表欄位
        # ============================================================
        print("\n📋 3. 檢查 ai_generated_knowledge_candidates 表欄位")
        print("-" * 70)

        candidate_columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'ai_generated_knowledge_candidates'
              AND column_name IN (
                  'question', 'generated_answer', 'edited_question', 'edited_answer',
                  'question_embedding', 'test_scenario_id', 'ai_model',
                  'confidence_score', 'generation_reasoning', 'warnings',
                  'intent_ids', 'status', 'edit_summary'
              )
            ORDER BY column_name
        """)

        required_candidate_columns = {
            'question', 'generated_answer', 'edited_question', 'edited_answer',
            'question_embedding', 'test_scenario_id', 'ai_model',
            'confidence_score', 'generation_reasoning', 'warnings',
            'intent_ids', 'status', 'edit_summary'
        }

        found_candidate_columns = {col['column_name'] for col in candidate_columns}

        for col in required_candidate_columns:
            if col in found_candidate_columns:
                col_info = next(c for c in candidate_columns if c['column_name'] == col)
                print(f"   ✅ {col:30} {col_info['data_type']}")
            else:
                print(f"   ❌ {col:30} 缺失")

        # ============================================================
        # 4. 檢查 test_scenarios 表欄位
        # ============================================================
        print("\n📋 4. 檢查 test_scenarios 表欄位")
        print("-" * 70)

        scenario_columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'test_scenarios'
              AND column_name IN ('related_knowledge_ids', 'linked_knowledge_ids', 'has_knowledge')
            ORDER BY column_name
        """)

        print("   檢查項:")

        has_related = any(c['column_name'] == 'related_knowledge_ids' for c in scenario_columns)
        has_linked = any(c['column_name'] == 'linked_knowledge_ids' for c in scenario_columns)
        has_knowledge_flag = any(c['column_name'] == 'has_knowledge' for c in scenario_columns)

        if has_related:
            print(f"   ✅ related_knowledge_ids    存在（正確）")
        else:
            print(f"   ❌ related_knowledge_ids    缺失")

        if has_linked:
            print(f"   ⚠️  linked_knowledge_ids     存在（不應該存在，與 related_knowledge_ids 重複）")
        else:
            print(f"   ✅ linked_knowledge_ids     不存在（正確）")

        if has_knowledge_flag:
            print(f"   ⚠️  has_knowledge            存在（函數已不使用此欄位）")
        else:
            print(f"   ✅ has_knowledge            不存在（正確）")

        # ============================================================
        # 5. 檢查 knowledge_intent_mapping 表
        # ============================================================
        print("\n📋 5. 檢查 knowledge_intent_mapping 表")
        print("-" * 70)

        mapping_table = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'knowledge_intent_mapping'
        """)

        if mapping_table > 0:
            print(f"   ✅ knowledge_intent_mapping 表存在")

            mapping_columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'knowledge_intent_mapping'
                  AND column_name IN (
                      'knowledge_id', 'intent_id', 'intent_type', 'confidence', 'assigned_by'
                  )
                ORDER BY column_name
            """)

            for col in mapping_columns:
                print(f"      - {col['column_name']:20} {col['data_type']}")
        else:
            print(f"   ❌ knowledge_intent_mapping 表不存在")

        # ============================================================
        # 6. 檢查外鍵約束
        # ============================================================
        print("\n📋 6. 檢查外鍵約束")
        print("-" * 70)

        fk_constraints = await conn.fetch("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name IN ('knowledge_base', 'ai_generated_knowledge_candidates')
              AND (
                  kcu.column_name = 'intent_id' OR
                  kcu.column_name = 'source_test_scenario_id' OR
                  kcu.column_name = 'test_scenario_id'
              )
        """)

        for fk in fk_constraints:
            print(f"   ✅ {fk['table_name']}.{fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")

        # ============================================================
        # 7. 總結
        # ============================================================
        print("\n" + "=" * 70)
        print("📊 檢查總結")
        print("=" * 70)

        # 計算問題
        issues = []

        if len(functions) != 1:
            issues.append("函數數量不正確")
        elif arg_count != 4:
            issues.append("函數參數數量不正確")

        if not has_related:
            issues.append("test_scenarios.related_knowledge_ids 缺失")

        if has_linked:
            issues.append("test_scenarios.linked_knowledge_ids 不應該存在")

        missing_kb = required_kb_columns - found_kb_columns
        if missing_kb:
            issues.append(f"knowledge_base 缺少欄位: {', '.join(missing_kb)}")

        missing_candidate = required_candidate_columns - found_candidate_columns
        if missing_candidate:
            issues.append(f"ai_generated_knowledge_candidates 缺少欄位: {', '.join(missing_candidate)}")

        if mapping_table == 0:
            issues.append("knowledge_intent_mapping 表不存在")

        if len(issues) == 0:
            print("\n✅ 所有檢查通過！")
            print("   審核函數可以正常使用")
        else:
            print(f"\n⚠️  發現 {len(issues)} 個問題：")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")

    except Exception as e:
        print(f"\n❌ 檢查過程發生錯誤: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(comprehensive_check())
