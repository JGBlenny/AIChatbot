"""
ScenarioSelector 整合測試 - 連接真實資料庫

驗收測試，使用真實的 PostgreSQL 資料庫。
"""

import asyncio
import sys
import os

# 添加路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop')
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator')

# 直接導入 scenario_selector 模組
import importlib.util
spec = importlib.util.spec_from_file_location(
    "scenario_selector",
    "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/scenario_selector.py"
)
scenario_selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scenario_selector)

ScenarioSelector = scenario_selector.ScenarioSelector
SelectionStrategy = scenario_selector.SelectionStrategy
DifficultyDistribution = scenario_selector.DifficultyDistribution

# 導入資料庫工具
import asyncpg


async def get_db_pool():
    """建立資料庫連接池"""
    return await asyncpg.create_pool(
        host='localhost',
        port=5432,
        database='aichatbot_admin',
        user='aichatbot',
        password='aichatbot_password',
        min_size=1,
        max_size=2
    )


async def test_database_connection(pool):
    """測試資料庫連接"""
    print("驗收測試 1: 資料庫連接")
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval('SELECT 1')
            assert result == 1
            print("✓ 資料庫連接成功")
            return True
    except Exception as e:
        print(f"✗ 資料庫連接失敗: {e}")
        return False


async def test_check_test_scenarios(pool):
    """檢查 test_scenarios 表是否有資料"""
    print("\n驗收測試 2: 檢查測試情境資料")
    try:
        async with pool.acquire() as conn:
            # 查詢測試情境統計（不使用 vendor_id）
            query = """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'approved') as approved,
                    COUNT(*) FILTER (WHERE difficulty = 'easy') as easy,
                    COUNT(*) FILTER (WHERE difficulty = 'medium') as medium,
                    COUNT(*) FILTER (WHERE difficulty = 'hard') as hard
                FROM test_scenarios
            """
            row = await conn.fetchrow(query)

            print(f"  - 總測試情境數: {row['total']}")
            print(f"  - 已批准數量: {row['approved']}")
            print(f"  - 難度分布: easy={row['easy']}, medium={row['medium']}, hard={row['hard']}")

            if row['approved'] < 10:
                print(f"⚠️  警告: 已批准的測試情境不足 10 個，可能無法完整測試")
                return False

            print("✓ 測試情境資料充足")
            return True
    except Exception as e:
        print(f"✗ 檢查測試情境失敗: {e}")
        return False


async def test_stratified_sampling_real(pool):
    """實際驗收：分層隨機抽樣"""
    print("\n驗收測試 3: 分層隨機抽樣（真實資料）")
    try:
        selector = ScenarioSelector(pool)

        # 選取 20 個測試情境（不指定 collection_id）
        result = await selector.select_scenarios(
            batch_size=20,
            strategy=SelectionStrategy.STRATIFIED_RANDOM
        )

        print(f"  - 選取數量: {len(result['scenario_ids'])}")
        print(f"  - 選取策略: {result['selection_strategy']}")
        print(f"  - 難度分布: {result['difficulty_distribution']}")
        print(f"  - 可用總數: {result['total_available']}")
        print(f"  - 選取 ID 範例: {result['scenario_ids'][:5]}...")

        # 驗證選取數量
        if len(result['scenario_ids']) == 0:
            print("✗ 沒有選取任何測試情境")
            return False

        # 驗證難度分布存在
        dist = result['difficulty_distribution']
        if dist['easy'] == 0 and dist['medium'] == 0 and dist['hard'] == 0:
            print("✗ 難度分布異常（全為 0）")
            return False

        print("✓ 分層隨機抽樣功能正常")
        return True
    except Exception as e:
        print(f"✗ 分層隨機抽樣失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_exclude_scenarios_real(pool):
    """實際驗收：排除功能"""
    print("\n驗收測試 4: 排除指定情境 ID（真實資料）")
    try:
        selector = ScenarioSelector(pool)

        # 先選取一次
        first_result = await selector.select_scenarios(
            batch_size=10,
            strategy=SelectionStrategy.STRATIFIED_RANDOM
        )

        first_ids = first_result['scenario_ids']
        print(f"  - 第一次選取: {first_ids[:5]}...")

        # 第二次選取時排除第一次的結果
        second_result = await selector.select_scenarios(
            batch_size=10,
            strategy=SelectionStrategy.STRATIFIED_RANDOM,
            exclude_scenario_ids=first_ids
        )

        second_ids = second_result['scenario_ids']
        print(f"  - 第二次選取: {second_ids[:5]}...")

        # 驗證沒有重複
        overlap = set(first_ids) & set(second_ids)
        if overlap:
            print(f"✗ 發現重複 ID: {overlap}")
            return False

        print("✓ 排除功能正常（無重複）")
        return True
    except Exception as e:
        print(f"✗ 排除功能測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sequential_selection_real(pool):
    """實際驗收：順序選取"""
    print("\n驗收測試 5: 順序選取（真實資料）")
    try:
        selector = ScenarioSelector(pool)

        result = await selector.select_scenarios(
            batch_size=10,
            strategy=SelectionStrategy.SEQUENTIAL
        )

        print(f"  - 選取數量: {len(result['scenario_ids'])}")
        print(f"  - 選取策略: {result['selection_strategy']}")
        print(f"  - 選取 ID: {result['scenario_ids']}")

        # 驗證是否按順序
        if len(result['scenario_ids']) > 1:
            is_sorted = all(
                result['scenario_ids'][i] <= result['scenario_ids'][i + 1]
                for i in range(len(result['scenario_ids']) - 1)
            )
            if not is_sorted:
                print("✗ 選取結果不是順序的")
                return False

        print("✓ 順序選取功能正常")
        return True
    except Exception as e:
        print(f"✗ 順序選取測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_used_scenario_ids_real(pool):
    """實際驗收：取得已使用情境 ID"""
    print("\n驗收測試 6: 取得已使用情境 ID（真實資料）")
    try:
        selector = ScenarioSelector(pool)

        # 查詢已使用的情境 ID（所有迴圈）
        used_ids = await selector.get_used_scenario_ids()

        print(f"  - 已使用情境數量: {len(used_ids)}")
        if len(used_ids) > 0:
            print(f"  - 已使用 ID 範例: {used_ids[:5]}...")
        else:
            print("  - 尚無已使用的情境 ID（可能是新業者）")

        print("✓ 取得已使用情境 ID 功能正常")
        return True
    except Exception as e:
        print(f"✗ 取得已使用情境 ID 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_verify_sql_query(pool):
    """實際驗收：驗證 SQL 查詢正確性"""
    print("\n驗收測試 7: 驗證 SQL 查詢（直接查詢）")
    try:
        async with pool.acquire() as conn:
            # 測試排除功能的 SQL
            exclude_ids = [1, 2, 3]
            query = """
                SELECT id FROM test_scenarios
                WHERE difficulty = $1
                  AND status = 'approved'
                  AND ($2::INTEGER[] IS NULL OR NOT (id = ANY($2)))
                ORDER BY RANDOM()
                LIMIT 5
            """

            rows = await conn.fetch(query, 'easy', exclude_ids)
            selected_ids = [row['id'] for row in rows]

            print(f"  - 查詢結果: {selected_ids}")

            # 驗證沒有包含排除的 ID
            for excluded_id in exclude_ids:
                if excluded_id in selected_ids:
                    print(f"✗ SQL 查詢錯誤: ID {excluded_id} 應該被排除")
                    return False

            print("✓ SQL 查詢正確（排除功能有效）")
            return True
    except Exception as e:
        print(f"✗ SQL 查詢驗證失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """執行所有驗收測試"""
    print("=" * 60)
    print("ScenarioSelector 實際驗收測試（真實資料庫）")
    print("=" * 60)

    # 建立資料庫連接池
    try:
        pool = await get_db_pool()
        print("✓ 資料庫連接池建立成功")
    except Exception as e:
        print(f"✗ 無法建立資料庫連接池: {e}")
        print("\n請確認：")
        print("1. PostgreSQL 服務正在運行")
        print("2. 資料庫連接參數正確（DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD）")
        print("3. Docker 容器 aichatbot-postgres 正在運行")
        return False

    try:
        # 執行驗收測試
        results = []

        results.append(await test_database_connection(pool))
        results.append(await test_check_test_scenarios(pool))
        results.append(await test_stratified_sampling_real(pool))
        results.append(await test_exclude_scenarios_real(pool))
        results.append(await test_sequential_selection_real(pool))
        results.append(await test_get_used_scenario_ids_real(pool))
        results.append(await test_verify_sql_query(pool))

        # 統計結果
        passed = sum(results)
        total = len(results)

        print("\n" + "=" * 60)
        if all(results):
            print(f"所有驗收測試通過 ✓ ({passed}/{total})")
            print("=" * 60)
            return True
        else:
            print(f"部分驗收測試失敗 ✗ ({passed}/{total})")
            print("=" * 60)
            return False

    finally:
        # 關閉連接池
        await pool.close()
        print("\n✓ 資料庫連接池已關閉")


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
