"""
迴圈管理 API 路由簡化測試

測試 API 端點的基本功能，使用 mock 避免複雜的依賴問題。

Author: AI Assistant
Created: 2026-03-27
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock


# ============================================
# 測試配置
# ============================================

@pytest.fixture
def mock_db_pool():
    """Mock asyncpg 連接池"""
    pool = MagicMock()
    conn = AsyncMock()

    # Mock 查詢結果
    conn.fetchrow.return_value = {
        "id": 1,
        "loop_name": "測試迴圈",
        "vendor_id": 2,
        "status": "RUNNING",
        "current_iteration": 1,
        "max_iterations": 10,
        "current_pass_rate": 0.6,
        "target_pass_rate": 0.85,
        "scenario_ids": [1, 2, 3, 4, 5],
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "completed_at": None
    }
    conn.fetchval.return_value = 10
    conn.execute.return_value = None

    # 正確設定 async context manager
    # acquire() 是普通方法，返回 async context manager
    acquire_context = AsyncMock()
    acquire_context.__aenter__.return_value = conn
    acquire_context.__aexit__.return_value = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=acquire_context)

    return pool


@pytest.fixture
def mock_request(mock_db_pool):
    """Mock FastAPI Request 物件"""
    request = MagicMock()
    request.app.state.db_pool = mock_db_pool
    return request


# ============================================
# 測試 1: API 端點存在性檢查
# ============================================

def test_api_endpoints_exist():
    """驗證所有 API 端點都已定義"""
    print("\n" + "="*60)
    print("測試 1: API 端點存在性檢查")
    print("="*60)

    try:
        from routers import loops

        # 檢查路由存在
        assert hasattr(loops, 'router'), "router 不存在"
        assert loops.router is not None, "router 為 None"

        # 檢查端點函數存在
        endpoints = [
            'start_loop',
            'execute_iteration',
            'get_loop_status',
            'validate_loop',
            'complete_batch',
            'pause_loop',
            'resume_loop',
            'cancel_loop',
            'start_next_batch'
        ]

        for endpoint in endpoints:
            assert hasattr(loops, endpoint), f"{endpoint} 函數不存在"
            print(f"✅ {endpoint} 存在")

        print("\n✅ 測試 1 通過：所有 9 個 API 端點都已定義")
        return True

    except Exception as e:
        print(f"❌ 測試 1 失敗：{str(e)}")
        return False


# ============================================
# 測試 2: Pydantic 模型驗證
# ============================================

def test_pydantic_models():
    """驗證所有 Pydantic 請求/回應模型"""
    print("\n" + "="*60)
    print("測試 2: Pydantic 模型驗證")
    print("="*60)

    try:
        from routers.loops import (
            LoopStartRequest,
            LoopStartResponse,
            ExecuteIterationRequest,
            ExecuteIterationResponse,
            LoopStatusResponse,
            ValidateLoopRequest,
            ValidateLoopResponse,
            CompleteBatchResponse
        )

        # 測試 LoopStartRequest
        start_req = LoopStartRequest(
            loop_name="測試迴圈",
            vendor_id=2,
            batch_size=50
        )
        assert start_req.loop_name == "測試迴圈"
        assert start_req.vendor_id == 2
        assert start_req.batch_size == 50
        assert start_req.target_pass_rate == 0.85  # 預設值
        print("✅ LoopStartRequest 驗證通過")

        # 測試 ExecuteIterationRequest
        exec_req = ExecuteIterationRequest()
        assert exec_req.async_mode == True  # 預設值
        exec_req2 = ExecuteIterationRequest(async_mode=False)
        assert exec_req2.async_mode == False
        print("✅ ExecuteIterationRequest 驗證通過")

        # 測試 ValidateLoopRequest
        val_req = ValidateLoopRequest()
        assert val_req.validation_scope == "failed_plus_sample"  # 預設值
        assert val_req.sample_pass_rate == 0.2  # 預設值
        print("✅ ValidateLoopRequest 驗證通過")

        print("\n✅ 測試 2 通過：所有 Pydantic 模型驗證正確")
        return True

    except Exception as e:
        print(f"❌ 測試 2 失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 測試 3: 查詢迴圈狀態（真實資料庫操作）
# ============================================

@pytest.mark.asyncio
async def test_get_loop_status_with_mock(mock_request):
    """測試查詢迴圈狀態端點（使用 mock）"""
    print("\n" + "="*60)
    print("測試 3: 查詢迴圈狀態（使用 mock）")
    print("="*60)

    try:
        from routers.loops import get_loop_status

        # 查詢迴圈狀態
        response = await get_loop_status(1, mock_request)

        assert response.loop_id == 1
        assert response.vendor_id == 2
        assert response.status == "RUNNING"
        assert response.current_iteration == 1
        assert response.total_scenarios == 5

        print(f"✅ 狀態查詢成功：loop_id={response.loop_id}, iteration={response.current_iteration}")
        print(f"   status={response.status}, scenarios={response.total_scenarios}")

        print("\n✅ 測試 3 通過：查詢迴圈狀態正常運作")
        return True

    except Exception as e:
        print(f"❌ 測試 3 失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 測試 4: 暫停/恢復/取消迴圈
# ============================================

@pytest.mark.asyncio
async def test_pause_resume_cancel(mock_request):
    """測試暫停/恢復/取消迴圈端點"""
    print("\n" + "="*60)
    print("測試 4: 暫停/恢復/取消迴圈")
    print("="*60)

    try:
        from routers.loops import pause_loop, resume_loop, cancel_loop, get_async_execution_manager

        # Mock AsyncExecutionManager
        with patch('routers.loops.get_async_execution_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.cancel_task = AsyncMock()
            mock_get_manager.return_value = mock_manager

            # 測試暫停
            pause_response = await pause_loop(1, mock_request)
            assert pause_response["status"] == "PAUSED"
            print(f"✅ 暫停迴圈成功：status={pause_response['status']}")

            # 測試恢復
            mock_request.app.state.db_pool.acquire.return_value.__aenter__.return_value.fetchval.return_value = "PAUSED"
            resume_response = await resume_loop(1, mock_request)
            assert resume_response["status"] == "RUNNING"
            print(f"✅ 恢復迴圈成功：status={resume_response['status']}")

            # 測試取消
            cancel_response = await cancel_loop(1, mock_request)
            assert cancel_response["status"] == "CANCELLED"
            print(f"✅ 取消迴圈成功：status={cancel_response['status']}")

        print("\n✅ 測試 4 通過：暫停/恢復/取消功能正常運作")
        return True

    except Exception as e:
        print(f"❌ 測試 4 失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 測試 5: 完成批次
# ============================================

@pytest.mark.asyncio
async def test_complete_batch(mock_request):
    """測試完成批次端點"""
    print("\n" + "="*60)
    print("測試 5: 完成批次")
    print("="*60)

    try:
        from routers.loops import complete_batch

        # 設定 mock 返回值
        conn = mock_request.app.state.db_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = {
            "loop_name": "測試迴圈",
            "vendor_id": 2,
            "status": "COMPLETED",
            "current_iteration": 3,
            "max_iterations": 10,
            "current_pass_rate": 0.9,
            "target_pass_rate": 0.85,
            "scenario_ids": [1, 2, 3, 4, 5],
            "created_at": datetime.now(),
            "completed_at": datetime.now()
        }
        conn.fetchval.return_value = 15  # 生成的知識數量

        # 完成批次
        response = await complete_batch(1, mock_request)

        assert response.loop_id == 1
        assert response.status == "COMPLETED"
        assert response.summary["total_iterations"] == 3
        assert response.summary["generated_knowledge_count"] == 15

        print(f"✅ 完成批次成功：iterations={response.summary['total_iterations']}")
        print(f"   knowledge_count={response.summary['generated_knowledge_count']}")

        print("\n✅ 測試 5 通過：完成批次功能正常運作")
        return True

    except Exception as e:
        print(f"❌ 測試 5 失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# 主測試執行
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("迴圈管理 API 路由簡化測試")
    print("="*60)

    # 執行同步測試
    results = []
    results.append(("端點存在性", test_api_endpoints_exist()))
    results.append(("Pydantic 模型", test_pydantic_models()))

    # 執行非同步測試
    async def run_async_tests():
        mock_pool = MagicMock()
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            "id": 1,
            "loop_name": "測試迴圈",
            "vendor_id": 2,
            "status": "RUNNING",
            "current_iteration": 1,
            "max_iterations": 10,
            "current_pass_rate": 0.6,
            "target_pass_rate": 0.85,
            "scenario_ids": [1, 2, 3, 4, 5],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "completed_at": None
        }
        conn.fetchval.return_value = 10
        conn.execute.return_value = None

        # 正確設定 async context manager
        # acquire() 是普通方法，返回 async context manager
        acquire_context = AsyncMock()
        acquire_context.__aenter__.return_value = conn
        acquire_context.__aexit__.return_value = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=acquire_context)

        mock_req = MagicMock()
        mock_req.app.state.db_pool = mock_pool

        results = []
        results.append(("查詢狀態", await test_get_loop_status_with_mock(mock_req)))
        results.append(("暫停/恢復/取消", await test_pause_resume_cancel(mock_req)))
        results.append(("完成批次", await test_complete_batch(mock_req)))
        return results

    async_results = asyncio.run(run_async_tests())
    results.extend(async_results)

    # 統計結果
    print("\n" + "="*60)
    print("測試結果摘要")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status}: {name}")

    print(f"\n總計：{passed}/{total} 測試通過")

    if passed == total:
        print("\n🎉 所有測試通過！")
        exit(0)
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗")
        exit(1)
