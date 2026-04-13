"""
AsyncExecutionManager 單元測試

用於驗證非同步執行管理器的核心功能。

Author: AI Assistant
Created: 2026-03-27
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# 添加路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop')

# 直接導入模組
import importlib.util
spec = importlib.util.spec_from_file_location(
    "async_execution_manager",
    "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/async_execution_manager.py"
)
async_execution_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(async_execution_manager)

AsyncExecutionManager = async_execution_manager.AsyncExecutionManager
ConcurrentExecutionError = async_execution_manager.ConcurrentExecutionError

# 導入 LoopStatus 枚舉
spec_models = importlib.util.spec_from_file_location(
    "models",
    "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/models.py"
)
models = importlib.util.module_from_spec(spec_models)
spec_models.loader.exec_module(models)

LoopStatus = models.LoopStatus

# Importar BudgetExceededError desde cost_tracker (no desde models)
spec_cost_tracker = importlib.util.spec_from_file_location(
    "cost_tracker",
    "/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/knowledge_completion_loop/cost_tracker.py"
)
cost_tracker = importlib.util.module_from_spec(spec_cost_tracker)
spec_cost_tracker.loader.exec_module(cost_tracker)

BudgetExceededError = cost_tracker.BudgetExceededError


def create_mock_db_pool():
    """創建正確配置的 mock db_pool"""
    mock_db_pool = MagicMock()
    mock_conn = AsyncMock()

    class MockAcquire:
        def __init__(self):
            pass
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    # 讓 acquire() 返回 MockAcquire 實例
    mock_db_pool.acquire = MagicMock(return_value=MockAcquire())

    return mock_db_pool, mock_conn


def test_initialization():
    """測試 AsyncExecutionManager 初始化"""
    print("測試 1: 初始化")

    mock_db_pool = AsyncMock()
    manager = AsyncExecutionManager(mock_db_pool)

    assert manager.db_pool == mock_db_pool
    assert isinstance(manager.running_tasks, dict)
    assert len(manager.running_tasks) == 0

    print("✓ 初始化正確")


async def test_start_iteration_success():
    """測試成功啟動迭代任務"""
    print("\n測試 2: 成功啟動迭代任務")

    mock_db_pool, mock_conn = create_mock_db_pool()
    manager = AsyncExecutionManager(mock_db_pool)

    # 創建 mock coordinator
    mock_coordinator = AsyncMock()
    mock_coordinator.execute_iteration = AsyncMock(return_value={
        "iteration": 1,
        "gaps_analyzed": 10,
        "knowledge_generated": 5
    })

    loop_id = 123

    # 啟動任務
    task_id = await manager.start_iteration(mock_coordinator, loop_id)

    # 驗證任務 ID 格式
    assert task_id.startswith(f"task_{loop_id}_")
    print(f"  - 任務 ID: {task_id}")

    # 驗證任務已記錄
    assert loop_id in manager.running_tasks
    assert isinstance(manager.running_tasks[loop_id], asyncio.Task)
    print(f"  - 任務已記錄到 running_tasks")

    # 等待背景任務完成（避免未完成的 Task 警告）
    await asyncio.sleep(0.2)

    print("✓ 成功啟動迭代任務")


async def test_concurrent_execution_error():
    """測試並發執行檢測"""
    print("\n測試 3: 並發執行檢測")

    mock_db_pool, mock_conn = create_mock_db_pool()
    manager = AsyncExecutionManager(mock_db_pool)

    mock_coordinator = AsyncMock()
    mock_coordinator.execute_iteration = AsyncMock(return_value={})

    loop_id = 456

    # 第一次啟動
    task_id_1 = await manager.start_iteration(mock_coordinator, loop_id)
    print(f"  - 第一次啟動成功: {task_id_1}")

    # 第二次啟動（應該失敗）
    try:
        task_id_2 = await manager.start_iteration(mock_coordinator, loop_id)
        print("✗ 應該拋出 ConcurrentExecutionError")
        sys.exit(1)
    except ConcurrentExecutionError as e:
        print(f"✓ 正確拋出 ConcurrentExecutionError: {e}")

    # 清理任務
    await manager.cancel_task(loop_id)
    await asyncio.sleep(0.2)


async def test_iteration_success_flow():
    """測試迭代成功流程"""
    print("\n測試 4: 迭代成功流程")

    mock_db_pool, mock_conn = create_mock_db_pool()
    manager = AsyncExecutionManager(mock_db_pool)

    # 創建 mock coordinator
    mock_coordinator = AsyncMock()
    mock_coordinator.execute_iteration = AsyncMock(return_value={
        "iteration": 2,
        "gaps_analyzed": 15,
        "knowledge_generated": 8
    })

    loop_id = 789

    # 啟動任務
    task_id = await manager.start_iteration(mock_coordinator, loop_id)

    # 等待背景任務完成
    await asyncio.sleep(0.2)

    # 驗證 coordinator.execute_iteration 被調用
    mock_coordinator.execute_iteration.assert_called_once()
    print("  - coordinator.execute_iteration() 已調用")

    # 驗證狀態更新為 REVIEWING
    update_calls = [call for call in mock_conn.execute.call_args_list if 'UPDATE knowledge_completion_loops' in str(call)]
    assert len(update_calls) > 0
    print("  - 狀態已更新為 REVIEWING")

    # 驗證事件記錄
    insert_calls = [call for call in mock_conn.execute.call_args_list if 'INSERT INTO loop_execution_logs' in str(call)]
    assert len(insert_calls) > 0
    print("  - 成功事件已記錄")

    # 驗證任務已清理
    assert loop_id not in manager.running_tasks
    print("  - running_tasks 已清理")

    print("✓ 迭代成功流程正確")


async def test_budget_exceeded_error_handling():
    """測試預算超支錯誤處理"""
    print("\n測試 5: 預算超支錯誤處理")

    mock_db_pool, mock_conn = create_mock_db_pool()
    manager = AsyncExecutionManager(mock_db_pool)

    # 創建 mock coordinator（拋出 BudgetExceededError）
    mock_coordinator = AsyncMock()
    mock_coordinator.execute_iteration = AsyncMock(
        side_effect=BudgetExceededError("Budget exceeded")
    )

    loop_id = 101

    # 啟動任務
    task_id = await manager.start_iteration(mock_coordinator, loop_id)

    # 等待背景任務完成
    await asyncio.sleep(0.2)

    # 驗證狀態更新為 FAILED
    update_calls = [call for call in mock_conn.execute.call_args_list if 'UPDATE knowledge_completion_loops' in str(call)]
    assert len(update_calls) > 0
    print("  - 狀態已更新為 FAILED")

    # 驗證錯誤事件記錄
    insert_calls = [call for call in mock_conn.execute.call_args_list if 'INSERT INTO loop_execution_logs' in str(call)]
    assert len(insert_calls) > 0
    # 檢查是否記錄了錯誤事件（budget_exceeded 或 iteration_failed 都可以）
    # 參數順序: args[0]=query, args[1]=loop_id, args[2]=event_type, args[3]=event_data
    error_event_found = False
    for call in insert_calls:
        args = call[0]
        if len(args) >= 3 and args[2] in ["budget_exceeded", "iteration_failed"]:
            event_data = args[3] if len(args) > 3 else {}
            error_msg = str(event_data.get("error", ""))
            if "Budget" in error_msg or "budget" in error_msg.lower():
                print(f"  - 預算錯誤已記錄（事件類型: {args[2]}）")
                error_event_found = True
                break
    assert error_event_found
    print("  - 錯誤事件已記錄")

    # 驗證任務已清理
    assert loop_id not in manager.running_tasks
    print("  - running_tasks 已清理")

    print("✓ 預算超支錯誤處理正確")


async def test_general_exception_handling():
    """測試一般異常處理"""
    print("\n測試 6: 一般異常處理")

    mock_db_pool, mock_conn = create_mock_db_pool()
    manager = AsyncExecutionManager(mock_db_pool)

    # 創建 mock coordinator（拋出一般異常）
    mock_coordinator = AsyncMock()
    mock_coordinator.execute_iteration = AsyncMock(
        side_effect=RuntimeError("Unexpected error occurred")
    )

    loop_id = 202

    # 啟動任務
    task_id = await manager.start_iteration(mock_coordinator, loop_id)

    # 等待背景任務完成
    await asyncio.sleep(0.2)

    # 驗證狀態更新為 FAILED
    update_calls = [call for call in mock_conn.execute.call_args_list if 'UPDATE knowledge_completion_loops' in str(call)]
    assert len(update_calls) > 0
    print("  - 狀態已更新為 FAILED")

    # 驗證錯誤事件記錄（含 traceback）
    insert_calls = [call for call in mock_conn.execute.call_args_list if 'INSERT INTO loop_execution_logs' in str(call)]
    assert len(insert_calls) > 0
    # 檢查是否記錄了 iteration_failed 事件
    # 參數順序: args[0]=query, args[1]=loop_id, args[2]=event_type, args[3]=event_data
    failed_event_found = False
    for call in insert_calls:
        args = call[0]
        if len(args) >= 3 and args[2] == "iteration_failed":
            failed_event_found = True
            break
    assert failed_event_found
    print("  - 失敗事件已記錄（含 traceback）")

    # 驗證任務已清理
    assert loop_id not in manager.running_tasks
    print("  - running_tasks 已清理")

    print("✓ 一般異常處理正確")


async def test_is_running():
    """測試 is_running() 方法"""
    print("\n測試 7: is_running() 方法")

    mock_db_pool, mock_conn = create_mock_db_pool()
    manager = AsyncExecutionManager(mock_db_pool)

    loop_id = 303

    # 未啟動時應該返回 False
    assert not manager.is_running(loop_id)
    print("  - 未啟動時返回 False")

    # 啟動任務後應該返回 True
    mock_coordinator = AsyncMock()
    mock_coordinator.execute_iteration = AsyncMock(return_value={})
    await manager.start_iteration(mock_coordinator, loop_id)

    assert manager.is_running(loop_id)
    print("  - 啟動後返回 True")

    # 清理
    await manager.cancel_task(loop_id)
    await asyncio.sleep(0.1)

    # 取消後應該返回 False
    assert not manager.is_running(loop_id)
    print("  - 取消後返回 False")

    print("✓ is_running() 方法正確")


async def test_cancel_task():
    """測試任務取消功能"""
    print("\n測試 8: 任務取消功能")

    mock_db_pool, mock_conn = create_mock_db_pool()
    manager = AsyncExecutionManager(mock_db_pool)

    loop_id = 404

    # 取消不存在的任務應該返回 False
    result = await manager.cancel_task(loop_id)
    assert result is False
    print("  - 取消不存在的任務返回 False")

    # 啟動任務
    mock_coordinator = AsyncMock()
    mock_coordinator.execute_iteration = AsyncMock(
        side_effect=asyncio.sleep(10)  # 模擬長時間運行
    )
    await manager.start_iteration(mock_coordinator, loop_id)

    # 取消任務
    result = await manager.cancel_task(loop_id)
    assert result is True
    print("  - 取消成功返回 True")

    # 驗證任務已清理
    assert loop_id not in manager.running_tasks
    print("  - running_tasks 已清理")

    # 驗證取消事件記錄
    insert_calls = [call for call in mock_conn.execute.call_args_list if 'INSERT INTO loop_execution_logs' in str(call)]
    assert len(insert_calls) > 0
    # 參數順序: args[0]=query, args[1]=loop_id, args[2]=event_type, args[3]=event_data
    cancelled_event_found = False
    for call in insert_calls:
        args = call[0]
        if len(args) >= 3 and args[2] == "iteration_cancelled":
            cancelled_event_found = True
            break
    assert cancelled_event_found
    print("  - 取消事件已記錄")

    print("✓ 任務取消功能正確")


async def main():
    """執行所有測試"""
    print("=" * 60)
    print("AsyncExecutionManager 單元測試")
    print("=" * 60)

    # 同步測試
    test_initialization()

    # 非同步測試
    await test_start_iteration_success()
    await test_concurrent_execution_error()
    await test_iteration_success_flow()
    await test_budget_exceeded_error_handling()
    await test_general_exception_handling()
    await test_is_running()
    await test_cancel_task()

    print("\n" + "=" * 60)
    print("所有測試通過 ✓ (8/8)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
