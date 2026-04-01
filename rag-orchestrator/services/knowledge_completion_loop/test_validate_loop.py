"""
測試 LoopCoordinator.validate_loop() 方法

測試覆蓋：
- 驗證當前狀態必須為 REVIEWING
- 三種驗證範圍：failed_only, all, failed_plus_sample
- 執行驗證回測並記錄結果
- 檢測 regression
- 更新狀態與記錄事件
"""

import asyncio
import sys
import os
import random
from datetime import datetime
from unittest.mock import Mock, MagicMock, AsyncMock

# 添加路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop')

# 直接導入 models 模組
import importlib.util

# 載入 models 模組
spec_models = importlib.util.spec_from_file_location(
    "models",
    "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/models.py"
)
models = importlib.util.module_from_spec(spec_models)
spec_models.loader.exec_module(models)

LoopStatus = models.LoopStatus
LoopConfig = models.LoopConfig
InvalidStateError = models.InvalidStateError


def create_mock_coordinator():
    """建立 mock coordinator 用於測試"""
    # Mock 所有依賴
    sys.modules['services.knowledge_completion_loop.gap_analyzer'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.backtest_client'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.action_type_classifier'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.knowledge_generator'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.cost_tracker'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.gap_classifier'] = MagicMock()
    sys.modules['services.knowledge_completion_loop.sop_generator'] = MagicMock()

    spec_coord = importlib.util.spec_from_file_location(
        "coordinator",
        "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/coordinator.py"
    )
    coordinator = importlib.util.module_from_spec(spec_coord)
    spec_coord.loader.exec_module(coordinator)

    return coordinator.LoopCoordinator


def mock_db_pool():
    """建立 mock 資料庫連接池"""
    pool = Mock()
    conn = MagicMock()
    cursor = MagicMock()

    cursor.fetchone = Mock(return_value=None)
    cursor.fetchall = Mock(return_value=[])
    conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)

    pool.getconn = Mock(return_value=conn)
    pool.putconn = Mock()

    return pool


async def test_validate_loop_requires_reviewing_status():
    """測試 1: validate_loop 需要 REVIEWING 狀態"""
    print("\n[測試 1] validate_loop 需要 REVIEWING 狀態...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 設定為非 REVIEWING 狀態
    coordinator.loop_id = 1
    coordinator.current_status = LoopStatus.RUNNING

    # 應該拋出 InvalidStateError
    try:
        await coordinator.validate_loop()
        assert False, "應該拋出 InvalidStateError"
    except InvalidStateError as e:
        assert "RUNNING" in str(e) or "running" in str(e)
        print("✅ 測試 1 通過：正確拋出 InvalidStateError")


async def test_validate_loop_failed_only_scope():
    """測試 2: validation_scope='failed_only' 只測試失敗案例"""
    print("\n[測試 2] validation_scope='failed_only' 只測試失敗案例...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 設定狀態
    coordinator.loop_id = 1
    coordinator.current_status = LoopStatus.REVIEWING
    coordinator.config = LoopConfig(
        batch_size=50,
        max_iterations=10,
        target_pass_rate=0.85
    )

    # Mock 方法
    failed_ids = [1, 2, 3, 4, 5]
    coordinator._get_failed_scenario_ids = AsyncMock(return_value=failed_ids)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=0)

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.6,
        "total": 5,
        "passed": 3,
        "failed": 2
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    # 執行驗證
    result = await coordinator.validate_loop(validation_scope="failed_only")

    # 驗證
    coordinator.backtest_client.execute_backtest.assert_called_once()
    call_args = coordinator.backtest_client.execute_backtest.call_args
    assert call_args.kwargs['scenario_ids'] == failed_ids
    assert result["validation_result"]["pass_rate"] == 0.6

    print("✅ 測試 2 通過：正確執行 failed_only 驗證")


async def test_validate_loop_all_scope():
    """測試 3: validation_scope='all' 測試所有案例"""
    print("\n[測試 3] validation_scope='all' 測試所有案例...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 設定狀態
    coordinator.loop_id = 1
    coordinator.current_status = LoopStatus.REVIEWING
    coordinator.config = LoopConfig(
        batch_size=50,
        max_iterations=10,
        target_pass_rate=0.85
    )

    # Mock 方法
    all_scenario_ids = list(range(1, 51))  # 50 個測試案例
    coordinator._get_scenario_ids = AsyncMock(return_value=all_scenario_ids)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=2)  # 檢測到 2 個 regression

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.8,
        "total": 50,
        "passed": 40,
        "failed": 10
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    # 執行驗證
    result = await coordinator.validate_loop(validation_scope="all")

    # 驗證
    coordinator._get_scenario_ids.assert_called_once()
    coordinator._detect_regression.assert_called_once()
    assert result["regression_detected"] == True
    assert result["regression_count"] == 2

    print("✅ 測試 3 通過：正確執行 all 驗證並檢測 regression")


async def test_validate_loop_failed_plus_sample_scope():
    """測試 4: validation_scope='failed_plus_sample' 失敗案例 + 抽樣"""
    print("\n[測試 4] validation_scope='failed_plus_sample' 失敗案例 + 抽樣...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 設定狀態
    coordinator.loop_id = 1
    coordinator.current_status = LoopStatus.REVIEWING
    coordinator.config = LoopConfig(
        batch_size=50,
        max_iterations=10,
        target_pass_rate=0.85
    )

    # Mock 方法
    all_scenario_ids = list(range(1, 51))  # 50 個測試案例
    failed_ids = [1, 2, 3, 4, 5]  # 5 個失敗
    coordinator._get_scenario_ids = AsyncMock(return_value=all_scenario_ids)
    coordinator._get_failed_scenario_ids = AsyncMock(return_value=failed_ids)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=0)

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.85,
        "total": 14,  # 5 failed + 9 sampled (45 * 0.2)
        "passed": 12,
        "failed": 2
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    # 執行驗證
    result = await coordinator.validate_loop(
        validation_scope="failed_plus_sample",
        sample_pass_rate=0.2
    )

    # 驗證：應該測試失敗案例 + 抽樣的通過案例
    call_args = coordinator.backtest_client.execute_backtest.call_args
    test_scenario_ids = call_args.kwargs['scenario_ids']

    # 驗證失敗案例都包含在內
    for fid in failed_ids:
        assert fid in test_scenario_ids, f"失敗案例 {fid} 應該在測試集中"

    # 驗證測試集大小合理（5 個失敗 + 約 9 個抽樣）
    assert len(test_scenario_ids) >= 5, "測試集應該至少包含 5 個失敗案例"
    assert len(test_scenario_ids) <= 20, "測試集大小應該合理"

    print(f"✅ 測試 4 通過：測試集大小 = {len(test_scenario_ids)} (5 失敗 + 抽樣)")


async def test_validate_loop_updates_status_and_logs_event():
    """測試 5: validate_loop 正確更新狀態並記錄事件"""
    print("\n[測試 5] validate_loop 正確更新狀態並記錄事件...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 設定狀態
    coordinator.loop_id = 1
    coordinator.current_status = LoopStatus.REVIEWING
    coordinator.config = LoopConfig(
        batch_size=50,
        max_iterations=10,
        target_pass_rate=0.85
    )

    # Mock 方法
    failed_ids = [1, 2, 3]
    coordinator._get_failed_scenario_ids = AsyncMock(return_value=failed_ids)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=0)

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.75,
        "total": 3,
        "passed": 2,
        "failed": 1
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    # 執行驗證
    result = await coordinator.validate_loop(validation_scope="failed_only")

    # 驗證狀態轉換
    assert coordinator._update_loop_status.call_count == 2
    calls = coordinator._update_loop_status.call_args_list
    assert calls[0][0][0] == LoopStatus.VALIDATING  # 第一次：轉為 VALIDATING
    assert calls[1][0][0] == LoopStatus.RUNNING  # 第二次：轉回 RUNNING

    # 驗證事件記錄
    coordinator._log_event.assert_called_once()
    event_call = coordinator._log_event.call_args
    assert event_call.kwargs['event_type'] == "validation_completed"
    assert 'pass_rate' in event_call.kwargs['event_data']
    assert 'regression_detected' in event_call.kwargs['event_data']

    print("✅ 測試 5 通過：正確更新狀態並記錄事件")


async def main():
    """執行所有測試"""
    print("=" * 60)
    print("開始執行 validate_loop 方法測試")
    print("=" * 60)

    try:
        await test_validate_loop_requires_reviewing_status()
        await test_validate_loop_failed_only_scope()
        await test_validate_loop_all_scope()
        await test_validate_loop_failed_plus_sample_scope()
        await test_validate_loop_updates_status_and_logs_event()

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
