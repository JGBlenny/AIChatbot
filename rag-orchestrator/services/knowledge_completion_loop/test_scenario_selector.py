"""
ScenarioSelector 單元測試

用於驗證測試情境選取器的核心功能。

Author: AI Assistant
Created: 2026-03-27
Updated: 2026-03-27 (移除 vendor_id，改用 collection_id)
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# 添加路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop')

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


def test_difficulty_distribution():
    """測試 DifficultyDistribution 模型"""
    print("測試 1: DifficultyDistribution 預設值")
    dist = DifficultyDistribution()
    assert dist.easy == 0.2
    assert dist.medium == 0.5
    assert dist.hard == 0.3
    print("✓ 預設值正確")

    print("\n測試 2: DifficultyDistribution 驗證總和（有效）")
    dist = DifficultyDistribution(easy=0.3, medium=0.4, hard=0.3)
    dist.validate_sum()
    print("✓ 驗證通過")

    print("\n測試 3: DifficultyDistribution 驗證總和（無效）")
    dist = DifficultyDistribution(easy=0.3, medium=0.4, hard=0.4)
    try:
        dist.validate_sum()
        print("✗ 應該拋出 ValueError")
        sys.exit(1)
    except ValueError as e:
        print(f"✓ 正確拋出 ValueError: {e}")


async def test_stratified_sampling():
    """測試分層隨機抽樣"""
    print("\n測試 4: 分層隨機抽樣")

    # 創建 mock db_pool
    mock_db_pool = AsyncMock()

    # 模擬查詢結果
    # easy: 10 個, medium: 25 個, hard: 15 個
    mock_db_pool.fetch.side_effect = [
        [{"id": i} for i in range(1, 11)],   # easy
        [{"id": i} for i in range(11, 36)],  # medium
        [{"id": i} for i in range(36, 51)],  # hard
    ]
    mock_db_pool.fetchrow.return_value = {"total": 100}

    selector = ScenarioSelector(mock_db_pool)
    result = await selector.select_scenarios(
        batch_size=50,
        strategy=SelectionStrategy.STRATIFIED_RANDOM
    )

    assert len(result["scenario_ids"]) == 50
    assert result["selection_strategy"] == "stratified_random"
    assert result["difficulty_distribution"]["easy"] == 10
    assert result["difficulty_distribution"]["medium"] == 25
    assert result["difficulty_distribution"]["hard"] == 15
    assert result["total_available"] == 100

    print("✓ 分層隨機抽樣功能正確")
    print(f"  - 選取數量: {len(result['scenario_ids'])}")
    print(f"  - 難度分布: {result['difficulty_distribution']}")


async def test_exclude_scenario_ids():
    """測試排除功能"""
    print("\n測試 5: 排除指定情境 ID")

    mock_db_pool = AsyncMock()
    exclude_ids = [1, 2, 3, 10, 20]

    # 模擬排除後的結果（確保返回的 ID 不包含 exclude_ids）
    # easy: batch_size=20, easy=0.2*20=4, 排除 1,2,3，返回 4,5,6,7
    # medium: 0.5*20=10, 排除 10,20，返回 11-19,21
    # hard: 0.3*20=6, 返回 30-35
    mock_db_pool.fetch.side_effect = [
        [{"id": i} for i in range(4, 8)],     # easy: 4,5,6,7 (排除 1,2,3)
        [{"id": i} for i in [11,12,13,14,15,16,17,18,19,21]],  # medium: 排除 10,20
        [{"id": i} for i in range(30, 36)],   # hard: 30-35
    ]
    mock_db_pool.fetchrow.return_value = {"total": 80}

    selector = ScenarioSelector(mock_db_pool)
    result = await selector.select_scenarios(
        batch_size=20,
        strategy=SelectionStrategy.STRATIFIED_RANDOM,
        exclude_scenario_ids=exclude_ids
    )

    # 驗證排除功能
    for excluded_id in exclude_ids:
        if excluded_id in result["scenario_ids"]:
            print(f"✗ 錯誤: ID {excluded_id} 應該被排除")
            print(f"  - 實際選取: {result['scenario_ids']}")
            sys.exit(1)

    print("✓ 排除功能正確")
    print(f"  - 排除 ID: {exclude_ids}")
    print(f"  - 實際選取: {result['scenario_ids'][:10]}...")


async def test_sequential_selection():
    """測試順序選取"""
    print("\n測試 6: 順序選取")

    mock_db_pool = AsyncMock()
    mock_db_pool.fetch.return_value = [
        {"id": i, "difficulty": "medium"} for i in range(1, 21)
    ]
    mock_db_pool.fetchrow.return_value = {"total": 100}

    selector = ScenarioSelector(mock_db_pool)
    result = await selector.select_scenarios(
        batch_size=20,
        strategy=SelectionStrategy.SEQUENTIAL
    )

    assert result["selection_strategy"] == "sequential"
    assert len(result["scenario_ids"]) == 20

    print("✓ 順序選取功能正確")
    print(f"  - 選取數量: {len(result['scenario_ids'])}")


async def test_full_random_selection():
    """測試完全隨機選取"""
    print("\n測試 7: 完全隨機選取")

    mock_db_pool = AsyncMock()
    mock_db_pool.fetch.return_value = [
        {"id": i, "difficulty": "medium"} for i in range(1, 31)
    ]
    mock_db_pool.fetchrow.return_value = {"total": 100}

    selector = ScenarioSelector(mock_db_pool)
    result = await selector.select_scenarios(
        batch_size=30,
        strategy=SelectionStrategy.FULL_RANDOM
    )

    assert result["selection_strategy"] == "full_random"
    assert len(result["scenario_ids"]) == 30

    print("✓ 完全隨機選取功能正確")
    print(f"  - 選取數量: {len(result['scenario_ids'])}")


async def test_get_used_scenario_ids():
    """測試取得已使用情境 ID"""
    print("\n測試 8: 取得已使用情境 ID")

    mock_db_pool = AsyncMock()
    mock_db_pool.fetch.return_value = [
        {"scenario_id": 1},
        {"scenario_id": 5},
        {"scenario_id": 10},
        {"scenario_id": 20},
    ]

    selector = ScenarioSelector(mock_db_pool)
    result = await selector.get_used_scenario_ids()

    assert result == [1, 5, 10, 20]

    print("✓ 取得已使用情境 ID 功能正確")
    print(f"  - 已使用 ID: {result}")


async def test_batch_size_boundary():
    """測試批次大小邊界條件"""
    print("\n測試 9: 批次大小邊界條件")

    # 測試 batch_size = 0
    mock_db_pool1 = AsyncMock()
    selector1 = ScenarioSelector(mock_db_pool1)
    try:
        await selector1.select_scenarios(batch_size=0)
        print("✗ 應該拋出 ValueError")
        sys.exit(1)
    except ValueError:
        print("✓ batch_size=0 正確拋出錯誤")

    # 測試 batch_size = -1
    mock_db_pool2 = AsyncMock()
    selector2 = ScenarioSelector(mock_db_pool2)
    try:
        await selector2.select_scenarios(batch_size=-1)
        print("✗ 應該拋出 ValueError")
        sys.exit(1)
    except ValueError:
        print("✓ batch_size=-1 正確拋出錯誤")

    # 測試 batch_size = 1
    # batch_size=1: easy=0, medium=0, hard=1（因為 int() 向下取整）
    mock_db_pool3 = AsyncMock()
    # 只有 hard 難度會被查詢（target_easy=0, target_medium=0 會被跳過）
    mock_db_pool3.fetch.return_value = [{"id": 1}]  # hard: 1
    mock_db_pool3.fetchrow.return_value = {"total": 10}

    selector3 = ScenarioSelector(mock_db_pool3)
    result = await selector3.select_scenarios(
        batch_size=1,
        strategy=SelectionStrategy.STRATIFIED_RANDOM
    )

    if len(result["scenario_ids"]) != 1:
        print(f"✗ batch_size=1 錯誤: 預期 1，實際 {len(result['scenario_ids'])}")
        print(f"  - 難度分布: {result['difficulty_distribution']}")
        sys.exit(1)

    print("✓ batch_size=1 正確處理")


async def main():
    """執行所有測試"""
    print("=" * 60)
    print("ScenarioSelector 單元測試")
    print("=" * 60)

    # 同步測試
    test_difficulty_distribution()

    # 非同步測試
    await test_stratified_sampling()
    await test_exclude_scenario_ids()
    await test_sequential_selection()
    await test_full_random_selection()
    await test_get_used_scenario_ids()
    await test_batch_size_boundary()

    print("\n" + "=" * 60)
    print("所有測試通過 ✓ (9/9)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
