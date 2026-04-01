"""
測試啟動下一批次功能 (Task 11.2.6)

測試範圍：
1. 驗證父迴圈狀態為 COMPLETED
2. 顯示父迴圈已使用的測試集數量
3. 自動填入父迴圈 ID
4. 提交後顯示新迴圈資訊（含選取的測試集）
5. 錯誤處理（父迴圈未完成、無可用測試題等）
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the rag-orchestrator directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app
from routers.loops import router


@pytest.fixture
def client():
    """創建測試客戶端"""
    return TestClient(app)


@pytest.fixture
def mock_db_pool():
    """模擬資料庫連接池"""
    pool = AsyncMock()
    conn = AsyncMock()

    # Mock context manager for connection
    async def acquire():
        return conn

    pool.acquire = MagicMock(return_value=MagicMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock()
    ))

    return pool, conn


class TestStartNextBatch:
    """測試啟動下一批次功能"""

    def test_start_next_batch_without_parent_loop_id_should_fail(self, client):
        """測試 1: 沒有提供 parent_loop_id 應該失敗"""
        # Arrange
        payload = {
            "loop_name": "第2批-包租業知識完善",
            "vendor_id": 2,
            "batch_size": 50,
            "max_iterations": 10,
            "target_pass_rate": 0.85
            # 缺少 parent_loop_id
        }

        # Act
        with patch('routers.loops.get_sync_pool'), \
             patch('routers.loops.ScenarioSelector'):
            response = client.post("/api/v1/loops/start-next-batch", json=payload)

        # Assert
        assert response.status_code == 400
        assert "必須提供 parent_loop_id" in response.json()["detail"]


    @pytest.mark.asyncio
    async def test_start_next_batch_with_nonexistent_parent_should_fail(self, mock_db_pool):
        """測試 2: 父迴圈不存在應該失敗"""
        # Arrange
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(return_value=None)  # 父迴圈不存在

        from routers.loops import start_next_batch, LoopStartRequest
        from fastapi import Request

        request_data = LoopStartRequest(
            loop_name="第2批-包租業知識完善",
            vendor_id=2,
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.85,
            parent_loop_id=999  # 不存在的父迴圈
        )

        # Mock Request object
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.db_pool = pool

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await start_next_batch(request_data, mock_request)

        # 驗證錯誤訊息
        assert "父迴圈" in str(exc_info.value) or "不存在" in str(exc_info.value)


    @pytest.mark.asyncio
    async def test_start_next_batch_with_incomplete_parent_should_fail(self, mock_db_pool):
        """測試 3: 父迴圈未完成應該失敗"""
        # Arrange
        pool, conn = mock_db_pool

        # 模擬父迴圈存在但狀態為 RUNNING
        conn.fetchrow = AsyncMock(return_value={
            "id": 1,
            "status": "running",
            "scenario_ids": [1, 2, 3]
        })

        from routers.loops import start_next_batch, LoopStartRequest
        from fastapi import Request

        request_data = LoopStartRequest(
            loop_name="第2批-包租業知識完善",
            vendor_id=2,
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.85,
            parent_loop_id=1
        )

        # Mock Request object
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.db_pool = pool

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await start_next_batch(request_data, mock_request)

        # 驗證錯誤訊息
        error_message = str(exc_info.value)
        assert "COMPLETED" in error_message or "completed" in error_message


    @pytest.mark.asyncio
    async def test_start_next_batch_success(self, mock_db_pool):
        """測試 4: 成功啟動下一批次"""
        # Arrange
        pool, conn = mock_db_pool

        # 模擬父迴圈已完成
        conn.fetchrow = AsyncMock(return_value={
            "id": 1,
            "status": "completed",
            "scenario_ids": [1, 2, 3, 4, 5]  # 已使用 5 題
        })

        from routers.loops import start_next_batch, LoopStartRequest
        from fastapi import Request

        request_data = LoopStartRequest(
            loop_name="第2批-包租業知識完善",
            vendor_id=2,
            batch_size=50,
            max_iterations=10,
            target_pass_rate=0.85,
            parent_loop_id=1
        )

        # Mock Request object
        mock_request = MagicMock(spec=Request)
        mock_request.app.state.db_pool = pool

        # Mock start_loop function
        with patch('routers.loops.start_loop') as mock_start_loop:
            mock_start_loop.return_value = AsyncMock(
                loop_id=2,
                loop_name="第2批-包租業知識完善",
                vendor_id=2,
                status="running",
                scenario_ids=[6, 7, 8, 9, 10],  # 新選取的測試集（排除 1-5）
                scenario_selection_strategy="stratified_random",
                difficulty_distribution={"easy": 10, "medium": 25, "hard": 15},
                initial_statistics={},
                created_at="2026-03-27T10:00:00Z"
            )

            # Act
            result = await start_next_batch(request_data, mock_request)

            # Assert
            assert result.loop_id == 2
            assert result.loop_name == "第2批-包租業知識完善"
            assert len(result.scenario_ids) == 5
            # 驗證新測試集不包含父迴圈的測試集
            parent_scenario_ids = [1, 2, 3, 4, 5]
            assert all(sid not in parent_scenario_ids for sid in result.scenario_ids)


    @pytest.mark.asyncio
    async def test_start_next_batch_excludes_parent_scenarios(self):
        """測試 5: 驗證新批次自動排除父迴圈的測試情境"""
        # Arrange
        from services.knowledge_completion_loop.scenario_selector import ScenarioSelector

        # Mock database pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock fetchrow for parent loop scenarios
        mock_conn.fetch = AsyncMock(return_value=[
            {"scenario_id": 1},
            {"scenario_id": 2},
            {"scenario_id": 3}
        ])

        mock_pool.acquire = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock()
        ))

        selector = ScenarioSelector(mock_pool)

        # Act
        used_scenario_ids = await selector.get_used_scenario_ids(parent_loop_id=1)

        # Assert
        assert used_scenario_ids == [1, 2, 3]

        # 驗證查詢條件包含 parent_loop_id
        call_args = mock_conn.fetch.call_args
        query = call_args[0][0]
        assert "parent_loop_id" in query.lower()


    @pytest.mark.asyncio
    async def test_start_next_batch_with_insufficient_scenarios_should_fail(self):
        """測試 6: 可用測試情境不足應該失敗"""
        # Arrange
        from services.knowledge_completion_loop.scenario_selector import ScenarioSelector

        # Mock database pool
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # 模擬情境：總共只有 60 題，父迴圈已使用 50 題，剩餘 10 題不足新批次的 50 題
        async def mock_fetch(query, *args):
            # 根據難度返回不同數量的測試題
            if "easy" in str(args):
                return [{"id": i} for i in range(61, 63)]  # 只有 2 題簡單題
            elif "medium" in str(args):
                return [{"id": i} for i in range(63, 68)]  # 只有 5 題中等題
            else:  # hard
                return [{"id": i} for i in range(68, 71)]  # 只有 3 題困難題

        mock_conn.fetch = AsyncMock(side_effect=mock_fetch)

        mock_pool.acquire = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock()
        ))

        selector = ScenarioSelector(mock_pool)

        # Act
        result = await selector.select_scenarios(
            batch_size=50,
            collection_id=None,
            exclude_scenario_ids=list(range(1, 51))  # 排除 1-50
        )

        # Assert
        # 應該只選取到 10 題（而非期望的 50 題）
        assert len(result["scenario_ids"]) == 10
        assert result["total_available"] == 10


class TestStartNextBatchIntegration:
    """整合測試：啟動下一批次的完整流程"""

    @pytest.mark.asyncio
    async def test_full_workflow_start_next_batch(self):
        """測試 7: 完整工作流程

        1. 創建第一個迴圈（50 題）
        2. 完成第一個迴圈
        3. 啟動下一批次（自動排除已使用的 50 題）
        4. 驗證新迴圈使用不同的測試集
        """
        # TODO: 需要實際資料庫連接才能進行整合測試
        # 這裡先跳過，建議在實際環境中手動測試
        pytest.skip("Integration test requires actual database connection")


# 執行測試
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
