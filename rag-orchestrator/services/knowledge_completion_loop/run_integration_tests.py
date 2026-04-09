"""
LoopCoordinator 擴展功能整合測試 (Docker 版本)

直接測試已實作的方法，不依賴硬編碼路徑
"""

import asyncio
import sys
from datetime import datetime
from unittest.mock import Mock, MagicMock, AsyncMock

# 導入模組
from models import LoopStatus, LoopConfig, LoopNotFoundError, InvalidStateError
from coordinator import LoopCoordinator


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


async def test_load_loop():
    """測試 1: load_loop 方法"""
    print("\n[測試 1] load_loop 載入已存在的迴圈...")

    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # Mock 資料庫查詢
    loop_id = 123
    mock_loop_record = {
        "id": loop_id,
        "vendor_id": 2,
        "loop_name": "測試迴圈",
        "status": "reviewing",
        "config": {
            "batch_size": 50,
            "target_pass_rate": 0.85,
            "action_type_mode": "ai_assisted",
            "filters": {},
            "backtest_config": {}
        },
        "current_iteration": 2,
        "budget_limit_usd": 100.0,
        "scenario_ids": list(range(1, 51)),
        "created_at": datetime.now()
    }

    conn = pool.getconn()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = mock_loop_record

    # 執行 load_loop
    result = await coordinator.load_loop(loop_id)

    # 驗證
    assert result["loop_id"] == loop_id, f"loop_id 錯誤: {result['loop_id']}"
    assert result["status"] == "reviewing", f"status 錯誤: {result['status']}"
    assert coordinator.current_status == LoopStatus.REVIEWING, "current_status 錯誤"
    assert coordinator.loop_id == loop_id, "coordinator.loop_id 未設定"

    print("  ✅ load_loop 方法正常運作")
    print(f"  ✅ 載入迴圈 ID: {loop_id}, 狀態: {result['status']}")
    return True


async def test_load_nonexistent_loop():
    """測試 2: load_loop 處理不存在的迴圈"""
    print("\n[測試 2] load_loop 載入不存在的迴圈...")

    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    loop_id = 999
    conn = pool.getconn()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = None

    # 應該拋出 LoopNotFoundError
    try:
        await coordinator.load_loop(loop_id)
        print("  ❌ 應該拋出 LoopNotFoundError")
        return False
    except LoopNotFoundError as e:
        assert f"Loop {loop_id} 不存在" in str(e)
        print(f"  ✅ 正確拋出 LoopNotFoundError: {e}")
        return True


async def test_validate_loop_state_check():
    """測試 3: validate_loop 狀態檢查"""
    print("\n[測試 3] validate_loop 需要 REVIEWING 狀態...")

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
        print("  ❌ 應該拋出 InvalidStateError")
        return False
    except InvalidStateError as e:
        print(f"  ✅ 正確拋出 InvalidStateError: {e}")
        return True


async def test_validate_loop_workflow():
    """測試 4: validate_loop 完整工作流程"""
    print("\n[測試 4] validate_loop 完整工作流程...")

    pool = mock_db_pool()
    coordinator = LoopCoordinator(
        db_pool=pool,
        vendor_id=2,
        loop_name="測試迴圈",
        openai_api_key="test-key"
    )

    # 設定狀態
    coordinator.loop_id = 123
    coordinator.current_status = LoopStatus.REVIEWING
    coordinator.config = LoopConfig(
        batch_size=50,
        target_pass_rate=0.85
    )

    # Mock 所有必要方法
    failed_ids = [1, 2, 3, 4, 5]
    all_scenario_ids = list(range(1, 51))

    coordinator._get_scenario_ids = AsyncMock(return_value=all_scenario_ids)
    coordinator._get_failed_scenario_ids = AsyncMock(return_value=failed_ids)
    coordinator._get_current_iteration = AsyncMock(return_value=1)
    coordinator._get_last_pass_rate = AsyncMock(return_value=0.70)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=0)
    coordinator._mark_knowledge_need_improvement = AsyncMock()

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.80,
        "total": 5,
        "passed": 4,
        "failed": 1,
        "results": []
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    # 執行驗證
    result = await coordinator.validate_loop(validation_scope="failed_only")

    # 驗證結果
    assert result["validation_result"]["pass_rate"] == 0.80, "通過率錯誤"
    assert abs(result["improvement"] - 0.10) < 0.001, f"改善幅度錯誤: {result['improvement']}"
    assert result["validation_passed"] == True, "驗證應該通過"

    # 驗證狀態轉換
    assert coordinator._update_loop_status.call_count == 2, "狀態更新次數錯誤"
    calls = coordinator._update_loop_status.call_args_list
    assert calls[0][0][0] == LoopStatus.VALIDATING, "第一次應轉為 VALIDATING"
    assert calls[1][0][0] == LoopStatus.RUNNING, "第二次應轉為 RUNNING"

    print("  ✅ validate_loop 工作流程正常")
    print(f"  ✅ 通過率從 70% → 80%（改善 10%）")
    print(f"  ✅ 狀態轉換: REVIEWING → VALIDATING → RUNNING")
    return True


async def test_validate_loop_with_regression():
    """測試 5: validate_loop regression 檢測"""
    print("\n[測試 5] validate_loop regression 檢測...")

    pool = mock_db_pool()
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
        target_pass_rate=0.85
    )

    # Mock 方法
    all_scenario_ids = list(range(1, 51))
    coordinator._get_scenario_ids = AsyncMock(return_value=all_scenario_ids)
    coordinator._get_current_iteration = AsyncMock(return_value=2)
    coordinator._get_last_pass_rate = AsyncMock(return_value=0.75)
    coordinator._update_loop_status = AsyncMock()
    coordinator._log_event = AsyncMock()
    coordinator._detect_regression = AsyncMock(return_value=3)  # 檢測到 3 個 regression
    coordinator._mark_knowledge_need_improvement = AsyncMock()

    # Mock backtest_client
    mock_backtest_result = {
        "pass_rate": 0.78,
        "total": 50,
        "passed": 39,
        "failed": 11,
        "results": []
    }
    coordinator.backtest_client = MagicMock()
    coordinator.backtest_client.execute_backtest = AsyncMock(return_value=mock_backtest_result)

    # 執行驗證
    result = await coordinator.validate_loop(validation_scope="all")

    # 驗證結果
    assert result["regression_detected"] == True, "應檢測到 regression"
    assert result["regression_count"] == 3, f"regression 數量錯誤: {result['regression_count']}"
    assert result["validation_passed"] == False, "有 regression 時驗證應失敗"

    # 驗證知識標記被調用
    coordinator._mark_knowledge_need_improvement.assert_called_once()

    print("  ✅ regression 檢測正常（檢測到 3 個案例）")
    print("  ✅ 知識已標記為需要改善")
    return True


async def main():
    """執行所有整合測試"""
    print("=" * 60)
    print("LoopCoordinator 擴展功能整合測試")
    print("=" * 60)

    results = []

    try:
        results.append(("load_loop 載入已存在迴圈", await test_load_loop()))
        results.append(("load_loop 載入不存在迴圈", await test_load_nonexistent_loop()))
        results.append(("validate_loop 狀態檢查", await test_validate_loop_state_check()))
        results.append(("validate_loop 完整工作流程", await test_validate_loop_workflow()))
        results.append(("validate_loop regression 檢測", await test_validate_loop_with_regression()))

        print("\n" + "=" * 60)
        print("測試結果摘要")
        print("=" * 60)

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            status = "✅ 通過" if result else "❌ 失敗"
            print(f"{status} - {name}")

        print(f"\n總計: {passed}/{total} 測試通過")

        if passed == total:
            print("\n✅ 所有整合測試通過！")
            return 0
        else:
            print(f"\n❌ {total - passed} 個測試失敗")
            return 1

    except Exception as e:
        print(f"\n❌ 測試執行錯誤：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
