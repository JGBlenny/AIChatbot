"""
LoopCoordinator 擴展功能整合測試

測試任務 4.1-4.4 的所有功能：
- load_loop: 載入已存在的迴圈
- validate_loop: 驗證效果回測
- _detect_regression: Regression 檢測
- _mark_knowledge_need_improvement: 知識標記

整合測試重點：
- 跨方法的協作流程
- 完整的驗證回測工作流程
- 狀態機完整性
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
LoopNotFoundError = models.LoopNotFoundError
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
    conn.commit = Mock()

    pool.getconn = Mock(return_value=conn)
    pool.putconn = Mock()

    return pool


async def test_complete_workflow_load_and_validate():
    """
    整合測試 1: 完整工作流程 - 載入迴圈並執行驗證回測

    測試流程：
    1. 載入已存在的迴圈（狀態為 REVIEWING）
    2. 執行驗證回測（failed_plus_sample）
    3. 檢測 regression
    4. 驗證狀態轉換正確
    """
    print("\n[整合測試 1] 完整工作流程：載入 → 驗證回測...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="整合測試迴圈",
        openai_api_key="test-key"
    )

    # Step 1: 載入迴圈
    loop_id = 123
    mock_loop_record = {
        "id": loop_id,
        "vendor_id": 2,
        "loop_name": "整合測試迴圈",
        "status": "reviewing",
        "config": {
            "batch_size": 50,
            "max_iterations": 10,
            "target_pass_rate": 0.85,
            "action_type_mode": "ai_assisted",
            "filters": {},
            "backtest_config": {}
        },
        "current_iteration": 2,
        "budget_limit_usd": 100.0,
        "scenario_ids": list(range(1, 51)),  # 50 個測試案例
        "created_at": datetime.now()
    }

    conn = pool.getconn()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = mock_loop_record

    load_result = await coordinator.load_loop(loop_id)

    # 驗證載入成功
    assert load_result["loop_id"] == loop_id
    assert load_result["status"] == "reviewing"
    assert coordinator.current_status == LoopStatus.REVIEWING
    print("  ✅ Step 1: 成功載入迴圈（狀態 = REVIEWING）")

    # Step 2: 執行驗證回測
    failed_ids = [1, 2, 3, 4, 5]
    all_scenario_ids = list(range(1, 51))

    # Mock 所需方法
    coordinator._get_scenario_ids = AsyncMock(return_value=all_scenario_ids)
    coordinator._get_failed_scenario_ids = AsyncMock(return_value=failed_ids)
    coordinator._get_current_iteration = AsyncMock(return_value=2)
    coordinator._get_last_pass_rate = AsyncMock(return_value=0.70)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=0)
    coordinator._mark_knowledge_need_improvement = AsyncMock()

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.80,
        "total": 14,  # 5 failed + 9 sampled
        "passed": 11,
        "failed": 3,
        "results": []
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    validate_result = await coordinator.validate_loop(
        validation_scope="failed_plus_sample",
        sample_pass_rate=0.2
    )

    # 驗證結果
    assert validate_result["validation_result"]["pass_rate"] == 0.80
    assert validate_result["improvement"] == 0.10  # 0.80 - 0.70
    assert validate_result["validation_passed"] == True  # improvement >= 0.05
    assert validate_result["regression_detected"] == False
    print("  ✅ Step 2: 成功執行驗證回測（通過率從 70% → 80%）")

    # Step 3: 驗證狀態轉換
    assert coordinator._update_loop_status.call_count == 2
    calls = coordinator._update_loop_status.call_args_list
    assert calls[0][0][0] == LoopStatus.VALIDATING
    assert calls[1][0][0] == LoopStatus.RUNNING
    print("  ✅ Step 3: 狀態轉換正確（REVIEWING → VALIDATING → RUNNING）")

    # Step 4: 驗證事件記錄
    coordinator._log_event.assert_called_once()
    event_call = coordinator._log_event.call_args
    assert event_call.kwargs['event_type'] == "validation_completed"
    print("  ✅ Step 4: 驗證事件已記錄")

    print("✅ 整合測試 1 通過：完整工作流程正常運作")


async def test_load_nonexistent_loop_then_create_new():
    """
    整合測試 2: 錯誤處理 - 載入不存在的迴圈

    測試：
    1. 嘗試載入不存在的迴圈
    2. 正確拋出 LoopNotFoundError
    """
    print("\n[整合測試 2] 錯誤處理：載入不存在的迴圈...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    loop_id = 999

    # Mock 資料庫查詢返回 None
    conn = pool.getconn()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = None

    # 應該拋出 LoopNotFoundError
    try:
        await coordinator.load_loop(loop_id)
        assert False, "應該拋出 LoopNotFoundError"
    except LoopNotFoundError as e:
        assert f"Loop {loop_id} 不存在" in str(e)
        print("  ✅ 正確拋出 LoopNotFoundError")

    print("✅ 整合測試 2 通過：錯誤處理正確")


async def test_validate_with_regression_detection():
    """
    整合測試 3: Regression 檢測流程

    測試：
    1. 載入迴圈（REVIEWING 狀態）
    2. 執行驗證回測（all 範圍）
    3. 檢測到 regression（2 個案例）
    4. 驗證未通過，標記知識需要改善
    """
    print("\n[整合測試 3] Regression 檢測與知識標記...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 載入迴圈
    coordinator.loop_id = 123
    coordinator.current_status = LoopStatus.REVIEWING
    coordinator.config = LoopConfig(
        batch_size=50,
        max_iterations=10,
        target_pass_rate=0.85
    )

    # Mock 方法
    all_scenario_ids = list(range(1, 51))
    coordinator._get_scenario_ids = AsyncMock(return_value=all_scenario_ids)
    coordinator._get_current_iteration = AsyncMock(return_value=2)
    coordinator._get_last_pass_rate = AsyncMock(return_value=0.75)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=2)  # 檢測到 2 個 regression
    coordinator._mark_knowledge_need_improvement = AsyncMock()

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.78,  # 通過率提升不足 5%
        "total": 50,
        "passed": 39,
        "failed": 11,
        "results": []
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    # 執行驗證
    validate_result = await coordinator.validate_loop(validation_scope="all")

    # 驗證結果
    assert validate_result["regression_detected"] == True
    assert validate_result["regression_count"] == 2
    assert validate_result["validation_passed"] == False  # 因為有 regression
    assert validate_result["next_action"] == "adjust_knowledge"
    print("  ✅ Step 1: 檢測到 2 個 regression 案例")

    # 驗證知識標記被調用
    coordinator._mark_knowledge_need_improvement.assert_called_once()
    print("  ✅ Step 2: 知識已標記為需要改善")

    # 驗證 regression 檢測被調用
    coordinator._detect_regression.assert_called_once()
    print("  ✅ Step 3: Regression 檢測邏輯已執行")

    print("✅ 整合測試 3 通過：Regression 檢測與知識標記正常運作")


async def test_validate_invalid_state():
    """
    整合測試 4: 狀態驗證 - 非 REVIEWING 狀態無法執行驗證

    測試：
    1. 迴圈狀態為 RUNNING
    2. 嘗試執行驗證回測
    3. 正確拋出 InvalidStateError
    """
    print("\n[整合測試 4] 狀態驗證：非 REVIEWING 狀態無法驗證...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 設定為 RUNNING 狀態
    coordinator.loop_id = 123
    coordinator.current_status = LoopStatus.RUNNING

    # 應該拋出 InvalidStateError
    try:
        await coordinator.validate_loop()
        assert False, "應該拋出 InvalidStateError"
    except InvalidStateError as e:
        assert "running" in str(e).lower() or "RUNNING" in str(e)
        print("  ✅ 正確拋出 InvalidStateError")

    print("✅ 整合測試 4 通過：狀態驗證正確")


async def test_validation_scope_comparison():
    """
    整合測試 5: 比較三種驗證範圍的行為

    測試：
    1. failed_only: 只測試失敗案例
    2. all: 測試所有案例
    3. failed_plus_sample: 失敗案例 + 抽樣

    驗證每種範圍的測試集大小正確
    """
    print("\n[整合測試 5] 比較三種驗證範圍...")

    LoopCoordinator = create_mock_coordinator()
    pool = mock_db_pool()

    validation_scopes = [
        ("failed_only", 5),        # 只有 5 個失敗案例
        ("all", 50),               # 所有 50 個案例
        ("failed_plus_sample", 14) # 5 失敗 + 9 抽樣 (45*0.2)
    ]

    for scope, expected_count in validation_scopes:
        coordinator = LoopCoordinator(
            db_pool=pool,
            vendor_id=2,
            loop_name="測試迴圈",
            openai_api_key="test-key"
        )

        coordinator.loop_id = 123
        coordinator.current_status = LoopStatus.REVIEWING
        coordinator.config = LoopConfig(
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.85
        )

        # Mock 方法
        all_scenario_ids = list(range(1, 51))
        failed_ids = [1, 2, 3, 4, 5]
        coordinator._get_scenario_ids = AsyncMock(return_value=all_scenario_ids)
        coordinator._get_failed_scenario_ids = AsyncMock(return_value=failed_ids)
        coordinator._get_current_iteration = AsyncMock(return_value=1)
        coordinator._get_last_pass_rate = AsyncMock(return_value=0.60)
        coordinator._update_loop_status = AsyncMock()
        coordinator._log_event = AsyncMock()
        coordinator._detect_regression = AsyncMock(return_value=0)

        # Mock backtest_client
        mock_backtest_result = {
            "pass_rate": 0.75,
            "total": expected_count,
            "passed": int(expected_count * 0.75),
            "failed": int(expected_count * 0.25),
            "results": []
        }
        coordinator.backtest_client = MagicMock()
        coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

        # 執行驗證
        await coordinator.validate_loop(
            validation_scope=scope,
            sample_pass_rate=0.2
        )

        # 驗證測試集大小
        call_args = coordinator.backtest_client.execute_backtest.call_args
        test_scenario_ids = call_args.kwargs['scenario_ids']

        if scope == "failed_only":
            assert len(test_scenario_ids) == 5
            print(f"  ✅ {scope}: 測試集大小 = {len(test_scenario_ids)} (正確)")
        elif scope == "all":
            assert len(test_scenario_ids) == 50
            print(f"  ✅ {scope}: 測試集大小 = {len(test_scenario_ids)} (正確)")
        else:  # failed_plus_sample
            # 允許一些隨機抽樣的誤差
            assert 10 <= len(test_scenario_ids) <= 18
            print(f"  ✅ {scope}: 測試集大小 = {len(test_scenario_ids)} (正確)")

    print("✅ 整合測試 5 通過：三種驗證範圍行為正確")


async def main():
    """執行所有整合測試"""
    print("=" * 60)
    print("開始執行 LoopCoordinator 擴展功能整合測試")
    print("=" * 60)

    try:
        await test_complete_workflow_load_and_validate()
        await test_load_nonexistent_loop_then_create_new()
        await test_validate_with_regression_detection()
        await test_validate_invalid_state()
        await test_validation_scope_comparison()

        print("\n" + "=" * 60)
        print("✅ 所有整合測試通過！(5/5)")
        print("=" * 60)
        print("\n測試摘要：")
        print("- 完整工作流程（載入 → 驗證）✅")
        print("- 錯誤處理（LoopNotFoundError）✅")
        print("- Regression 檢測與知識標記 ✅")
        print("- 狀態驗證（InvalidStateError）✅")
        print("- 三種驗證範圍比較 ✅")
    except Exception as e:
        print(f"\n❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
