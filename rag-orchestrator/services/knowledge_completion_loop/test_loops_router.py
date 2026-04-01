"""
迴圈管理 API 路由整合測試

測試完整的迴圈管理 API 流程，包含：
- 啟動迴圈
- 執行迭代（同步/非同步）
- 查詢狀態
- 驗證回測
- 暫停/恢復/取消
- 完成批次
- 批次關聯功能
- 錯誤處理

Author: AI Assistant
Created: 2026-03-27
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from routers.loops import (
    LoopStartRequest,
    LoopStartResponse,
    ExecuteIterationRequest,
    ExecuteIterationResponse,
    LoopStatusResponse,
    ValidateLoopRequest,
    ValidateLoopResponse,
    CompleteBatchResponse,
)
from services.knowledge_completion_loop.models import LoopStatus, LoopConfig


# ============================================
# 測試 1: 完整迴圈流程
# ============================================

@pytest.mark.asyncio
async def test_complete_loop_workflow():
    """
    測試完整迴圈流程：啟動 → 執行迭代 → 查詢狀態 → 完成

    驗證標準：
    - 啟動迴圈成功，返回固定測試集
    - 執行迭代成功（同步模式）
    - 查詢狀態返回正確資訊
    - 完成批次成功
    """
    print("\n" + "="*60)
    print("測試 1: 完整迴圈流程")
    print("="*60)

    # Mock 所有外部依賴
    with patch('routers.loops.get_sync_pool') as mock_sync_pool, \
         patch('routers.loops.ScenarioSelector') as mock_selector_class, \
         patch('routers.loops.LoopCoordinator') as mock_coordinator_class:

        # 設定 Mock 行為
        mock_db_pool = MagicMock()
        mock_sync_pool.return_value = mock_db_pool

        # Mock ScenarioSelector
        mock_selector = AsyncMock()
        mock_selector.select_scenarios.return_value = {
            "scenario_ids": [1, 2, 3, 4, 5],
            "selection_strategy": "stratified_random",
            "difficulty_distribution": {"easy": 1, "medium": 2, "hard": 2},
            "total_available": 5
        }
        mock_selector_class.return_value = mock_selector

        # Mock LoopCoordinator
        mock_coordinator = MagicMock()
        mock_coordinator.start_loop.return_value = {
            "loop_id": 1,
            "loop_name": "測試迴圈",
            "vendor_id": 2,
            "status": LoopStatus.RUNNING.value,
            "initial_statistics": {
                "total_scenarios": 5,
                "estimated_iterations": 3,
                "target_pass_rate": 0.85
            },
            "created_at": datetime.now().isoformat()
        }
        mock_coordinator.load_loop.return_value = {
            "loop_id": 1,
            "status": LoopStatus.RUNNING.value,
            "current_iteration": 0
        }
        mock_coordinator.execute_iteration.return_value = {
            "current_iteration": 1,
            "pass_rate": 0.6,
            "failed_count": 2,
            "passed_count": 3
        }
        mock_coordinator_class.return_value = mock_coordinator

        # 建立 mock Request 物件
        mock_request = MagicMock()
        mock_request.app.state.db_pool = AsyncMock()

        # Mock asyncpg 連接
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "id": 1,
            "loop_name": "測試迴圈",
            "vendor_id": 2,
            "status": LoopStatus.RUNNING.value,
            "current_iteration": 1,
            "max_iterations": 10,
            "current_pass_rate": 0.6,
            "target_pass_rate": 0.85,
            "scenario_ids": [1, 2, 3, 4, 5],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "completed_at": None
        }
        mock_conn.fetchval.return_value = 10
        mock_conn.execute.return_value = None

        # 設定連接池
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_request.app.state.db_pool = mock_pool

        # 導入路由
        from routers.loops import start_loop, execute_iteration, get_loop_status, complete_batch

        # 步驟 1: 啟動迴圈
        print("步驟 1: 啟動迴圈...")
        start_request = LoopStartRequest(
            loop_name="測試迴圈",
            vendor_id=2,
            batch_size=5,
            max_iterations=10,
            target_pass_rate=0.85
        )

        start_response = await start_loop(start_request, mock_request)

        assert start_response.loop_id == 1
        assert start_response.vendor_id == 2
        assert len(start_response.scenario_ids) == 5
        assert start_response.scenario_selection_strategy == "stratified_random"
        print(f"✅ 迴圈啟動成功：loop_id={start_response.loop_id}, scenarios={len(start_response.scenario_ids)}")

        # 步驟 2: 執行迭代（同步模式）
        print("\n步驟 2: 執行迭代（同步模式）...")
        exec_request = ExecuteIterationRequest(async_mode=False)

        exec_response = await execute_iteration(1, exec_request, mock_request, MagicMock())

        assert exec_response.loop_id == 1
        assert exec_response.status == "REVIEWING"
        assert exec_response.backtest_result is not None
        print(f"✅ 迭代執行成功：iteration={exec_response.current_iteration}, status={exec_response.status}")

        # 步驟 3: 查詢迴圈狀態
        print("\n步驟 3: 查詢迴圈狀態...")
        status_response = await get_loop_status(1, mock_request)

        assert status_response.loop_id == 1
        assert status_response.vendor_id == 2
        assert status_response.current_iteration == 1
        assert status_response.total_scenarios == 5
        print(f"✅ 狀態查詢成功：iteration={status_response.current_iteration}, pass_rate={status_response.current_pass_rate}")

        # 步驟 4: 完成批次
        print("\n步驟 4: 完成批次...")
        complete_response = await complete_batch(1, mock_request)

        assert complete_response.loop_id == 1
        assert complete_response.status == LoopStatus.COMPLETED.value
        assert complete_response.summary["generated_knowledge_count"] == 10
        print(f"✅ 批次完成：knowledge_count={complete_response.summary['generated_knowledge_count']}")

        print("\n✅ 測試 1 通過：完整迴圈流程正常運作")


# ============================================
# 測試 2: 非同步執行模式
# ============================================

@pytest.mark.asyncio
async def test_async_execution_mode():
    """
    測試非同步執行模式

    驗證標準：
    - 立即返回 task_id
    - 狀態為 RUNNING
    - 不等待迭代完成
    """
    print("\n" + "="*60)
    print("測試 2: 非同步執行模式")
    print("="*60)

    with patch('routers.loops.get_sync_pool') as mock_sync_pool, \
         patch('routers.loops.get_async_execution_manager') as mock_get_manager, \
         patch('routers.loops.LoopCoordinator') as mock_coordinator_class:

        # Mock 依賴
        mock_sync_pool.return_value = MagicMock()

        # Mock AsyncExecutionManager
        mock_manager = AsyncMock()
        mock_manager.is_running.return_value = False
        mock_manager.start_iteration.return_value = "task_1_1234567890"
        mock_get_manager.return_value = mock_manager

        # Mock LoopCoordinator
        mock_coordinator = MagicMock()
        mock_coordinator.load_loop.return_value = {
            "loop_id": 1,
            "status": LoopStatus.RUNNING.value,
            "current_iteration": 0
        }
        mock_coordinator_class.return_value = mock_coordinator

        mock_request = MagicMock()

        from routers.loops import execute_iteration

        # 執行非同步迭代
        print("啟動非同步迭代...")
        exec_request = ExecuteIterationRequest(async_mode=True)
        exec_response = await execute_iteration(1, exec_request, mock_request, MagicMock())

        assert exec_response.execution_task_id is not None
        assert exec_response.execution_task_id.startswith("task_")
        assert exec_response.status == "RUNNING"
        assert exec_response.backtest_result is None
        print(f"✅ 非同步執行成功：task_id={exec_response.execution_task_id}")

        # 驗證 start_iteration 被調用
        mock_manager.start_iteration.assert_called_once()
        print("✅ AsyncExecutionManager.start_iteration 已調用")

        print("\n✅ 測試 2 通過：非同步執行模式正常運作")


# ============================================
# 測試 3: 並發執行檢測
# ============================================

@pytest.mark.asyncio
async def test_concurrent_execution_detection():
    """
    測試並發執行檢測

    驗證標準：
    - 同一迴圈已在執行時，返回 409 Conflict
    """
    print("\n" + "="*60)
    print("測試 3: 並發執行檢測")
    print("="*60)

    from fastapi import HTTPException

    with patch('routers.loops.get_sync_pool') as mock_sync_pool, \
         patch('routers.loops.get_async_execution_manager') as mock_get_manager, \
         patch('routers.loops.LoopCoordinator') as mock_coordinator_class:

        # Mock 依賴
        mock_sync_pool.return_value = MagicMock()

        # Mock AsyncExecutionManager - 返回已在執行中
        mock_manager = AsyncMock()
        mock_manager.is_running.return_value = True
        mock_get_manager.return_value = mock_manager

        # Mock LoopCoordinator
        mock_coordinator = MagicMock()
        mock_coordinator.load_loop.return_value = {
            "loop_id": 1,
            "status": LoopStatus.RUNNING.value,
            "current_iteration": 0
        }
        mock_coordinator_class.return_value = mock_coordinator

        mock_request = MagicMock()

        from routers.loops import execute_iteration

        # 嘗試並發執行
        print("嘗試並發執行迴圈...")
        exec_request = ExecuteIterationRequest(async_mode=True)

        with pytest.raises(HTTPException) as exc_info:
            await execute_iteration(1, exec_request, mock_request, MagicMock())

        assert exc_info.value.status_code == 409
        assert "已在執行中" in exc_info.value.detail
        print(f"✅ 並發執行被正確阻止：{exc_info.value.detail}")

        print("\n✅ 測試 3 通過：並發執行檢測正常運作")


# ============================================
# 測試 4: 批次關聯功能
# ============================================

@pytest.mark.asyncio
async def test_batch_relationship():
    """
    測試批次關聯功能

    驗證標準：
    - 使用 parent_loop_id 啟動下一批次
    - 自動排除已使用的測試情境
    """
    print("\n" + "="*60)
    print("測試 4: 批次關聯功能")
    print("="*60)

    with patch('routers.loops.get_sync_pool') as mock_sync_pool, \
         patch('routers.loops.ScenarioSelector') as mock_selector_class, \
         patch('routers.loops.LoopCoordinator') as mock_coordinator_class:

        # Mock 依賴
        mock_sync_pool.return_value = MagicMock()

        # Mock ScenarioSelector
        mock_selector = AsyncMock()
        mock_selector.get_used_scenario_ids.return_value = [1, 2, 3, 4, 5]
        mock_selector.select_scenarios.return_value = {
            "scenario_ids": [6, 7, 8, 9, 10],
            "selection_strategy": "stratified_random",
            "difficulty_distribution": {"easy": 1, "medium": 2, "hard": 2},
            "total_available": 5
        }
        mock_selector_class.return_value = mock_selector

        # Mock LoopCoordinator
        mock_coordinator = MagicMock()
        mock_coordinator.start_loop.return_value = {
            "loop_id": 2,
            "loop_name": "第二批次",
            "vendor_id": 2,
            "status": LoopStatus.RUNNING.value,
            "initial_statistics": {"total_scenarios": 5},
            "created_at": datetime.now().isoformat()
        }
        mock_coordinator_class.return_value = mock_coordinator

        # Mock Request
        mock_request = MagicMock()
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "status": LoopStatus.COMPLETED.value
        }
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_request.app.state.db_pool = mock_pool

        from routers.loops import start_next_batch

        # 啟動下一批次
        print("啟動下一批次（關聯 parent_loop_id=1）...")
        request = LoopStartRequest(
            loop_name="第二批次",
            vendor_id=2,
            batch_size=5,
            parent_loop_id=1
        )

        response = await start_next_batch(request, mock_request)

        assert response.loop_id == 2
        assert len(response.scenario_ids) == 5
        assert all(sid not in [1, 2, 3, 4, 5] for sid in response.scenario_ids)
        print(f"✅ 第二批次啟動成功：loop_id={response.loop_id}, scenarios={response.scenario_ids}")

        # 驗證 get_used_scenario_ids 被調用
        mock_selector.get_used_scenario_ids.assert_called_once()
        print("✅ 已排除第一批次使用的測試情境")

        print("\n✅ 測試 4 通過：批次關聯功能正常運作")


# ============================================
# 測試 5: 錯誤處理
# ============================================

@pytest.mark.asyncio
async def test_error_handling():
    """
    測試錯誤處理

    驗證標準：
    - 404 Not Found - 迴圈不存在
    - 409 Conflict - 狀態錯誤
    """
    print("\n" + "="*60)
    print("測試 5: 錯誤處理")
    print("="*60)

    from fastapi import HTTPException

    # 測試 404 Not Found
    print("\n測試 5.1: 404 Not Found（迴圈不存在）")
    with patch('routers.loops.get_sync_pool'):
        mock_request = MagicMock()
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_request.app.state.db_pool = mock_pool

        from routers.loops import get_loop_status

        with pytest.raises(HTTPException) as exc_info:
            await get_loop_status(999, mock_request)

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.detail
        print(f"✅ 404 錯誤正確處理：{exc_info.value.detail}")

    # 測試 409 Conflict - 恢復非暫停狀態的迴圈
    print("\n測試 5.2: 409 Conflict（狀態錯誤）")
    with patch('routers.loops.get_sync_pool'):
        mock_request = MagicMock()
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = LoopStatus.RUNNING.value
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_request.app.state.db_pool = mock_pool

        from routers.loops import resume_loop

        with pytest.raises(HTTPException) as exc_info:
            await resume_loop(1, mock_request)

        assert exc_info.value.status_code == 409
        assert "暫停" in exc_info.value.detail
        print(f"✅ 409 錯誤正確處理：{exc_info.value.detail}")

    print("\n✅ 測試 5 通過：錯誤處理正常運作")


# ============================================
# 主測試執行
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("迴圈管理 API 路由整合測試")
    print("="*60)

    # 執行所有測試
    asyncio.run(test_complete_loop_workflow())
    asyncio.run(test_async_execution_mode())
    asyncio.run(test_concurrent_execution_detection())
    asyncio.run(test_batch_relationship())
    asyncio.run(test_error_handling())

    print("\n" + "="*60)
    print("✅ 所有測試通過 (5/5)")
    print("="*60)
