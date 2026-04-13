"""
測試迭代狀態管理的修復

驗證即使迭代執行失敗，current_iteration 也能正確更新
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from psycopg2.extras import RealDictCursor


class TestIterationStateManagement:
    """測試迭代狀態管理"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock 資料庫連接池"""
        pool = Mock()
        conn = Mock()
        cursor = Mock()

        # 設置基本的資料庫操作
        cursor.fetchone.return_value = {"current_iteration": 0}
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)

        conn.cursor.return_value = cursor
        conn.commit = Mock()
        conn.rollback = Mock()

        pool.getconn.return_value = conn
        pool.putconn = Mock()

        return pool

    @pytest.fixture
    def coordinator(self, mock_db_pool):
        """創建 Coordinator 實例"""
        from coordinator import LoopCoordinator

        coordinator = LoopCoordinator(
            db_pool=mock_db_pool,
            vendor_id=2,
            loop_name="測試迴圈",
            backtest_base_url="http://localhost:8100",
            openai_api_key="test-key"
        )
        coordinator.loop_id = 113

        return coordinator

    @pytest.mark.asyncio
    async def test_iteration_count_updated_before_backtest(self, coordinator, mock_db_pool):
        """
        測試：current_iteration 在回測前就更新

        驗證點：
        1. 開始執行迭代前，current_iteration = 0
        2. 執行 _update_iteration_count(1)
        3. 資料庫更新 current_iteration = 1
        4. 然後才執行回測
        """
        # Arrange
        cursor = mock_db_pool.getconn().cursor()

        # Act
        await coordinator._update_iteration_count(1)

        # Assert
        cursor.execute.assert_called()
        call_args = cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        # 驗證 SQL 更新 current_iteration
        assert "UPDATE knowledge_completion_loops" in sql
        assert "current_iteration = %s" in sql
        assert params[0] == 1  # new iteration number
        assert params[1] == 113  # loop_id

    @pytest.mark.asyncio
    async def test_iteration_count_persists_after_backtest_failure(self, coordinator, mock_db_pool):
        """
        測試：回測失敗後 current_iteration 仍然保持更新

        場景：
        1. current_iteration = 0
        2. 更新 current_iteration = 1
        3. 執行回測時失敗（拋出異常）
        4. 迴圈狀態變為 FAILED
        5. current_iteration 仍然是 1（不回滾）
        """
        # Arrange
        coordinator.backtest_client = Mock()
        coordinator.backtest_client.execute_batch_backtest = AsyncMock(
            side_effect=Exception("回測執行失敗")
        )

        cursor = mock_db_pool.getconn().cursor()
        cursor.fetchone.return_value = {"current_iteration": 0}

        # Act & Assert
        with pytest.raises(Exception, match="回測執行失敗"):
            await coordinator.execute_iteration()

        # 驗證 current_iteration 已經更新（在回測前）
        update_calls = [call for call in cursor.execute.call_args_list
                       if "current_iteration = %s" in str(call)]
        assert len(update_calls) > 0, "應該有更新 current_iteration 的呼叫"

    @pytest.mark.asyncio
    async def test_iteration_count_and_pass_rate_separated(self, coordinator, mock_db_pool):
        """
        測試：iteration count 和 pass_rate 更新分離

        邏輯：
        1. _update_iteration_count(next_iteration) - 在開始時更新次數
        2. _update_pass_rate(pass_rate) - 在回測完成後更新通過率
        """
        # Arrange
        cursor = mock_db_pool.getconn().cursor()

        # Act
        await coordinator._update_iteration_count(2)
        await coordinator._update_pass_rate(0.85)

        # Assert
        assert cursor.execute.call_count >= 2

        # 第一次呼叫：更新 iteration
        call1 = cursor.execute.call_args_list[0]
        assert "current_iteration = %s" in call1[0][0]

        # 第二次呼叫：更新 pass_rate
        call2 = cursor.execute.call_args_list[1]
        assert "current_pass_rate = %s" in call2[0][0]

    @pytest.mark.asyncio
    async def test_frontend_can_see_partial_iteration_result(self, coordinator, mock_db_pool):
        """
        測試：前端能看到部分完成的迭代結果

        場景：Loop 113 案例
        1. 迴圈執行迭代 1
        2. 回測完成（寫入 backtest_runs）
        3. 知識生成時失敗
        4. 迴圈狀態 = FAILED
        5. current_iteration = 1（已更新）
        6. 前端查詢 iterations API 應該能看到 Iteration 1 的回測結果
        """
        # Arrange
        coordinator.backtest_client = Mock()
        coordinator.backtest_client.execute_batch_backtest = AsyncMock(
            return_value={
                "backtest_run_id": 173,
                "pass_rate": 0.0,
                "total_tested": 50,
                "passed": 0,
                "failed": 50
            }
        )

        # 在知識生成階段失敗
        coordinator.gap_analyzer = Mock()
        coordinator.gap_analyzer.analyze_failures = AsyncMock(
            side_effect=Exception("分析失敗")
        )

        cursor = mock_db_pool.getconn().cursor()
        cursor.fetchone.return_value = {"current_iteration": 0}

        # Act
        with pytest.raises(Exception):
            await coordinator.execute_iteration()

        # Assert
        # 驗證 current_iteration 已經被更新為 1
        conn = mock_db_pool.getconn()
        update_calls = [call for call in cursor.execute.call_args_list
                       if "current_iteration = %s" in str(call)]

        assert len(update_calls) > 0, "current_iteration 應該已更新"

        # 此時前端查詢:
        # SELECT * FROM knowledge_completion_loops WHERE id = 113
        # 應該看到 current_iteration = 1

        # SELECT * FROM backtest_runs WHERE notes LIKE '%Loop 113%'
        # 應該看到 Iteration 1 的記錄

        # 兩者一致，前端可以正確顯示


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
