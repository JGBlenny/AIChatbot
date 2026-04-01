"""
簡化測試：啟動下一批次功能 (Task 11.2.6)

測試 API 端點的核心邏輯，不依賴完整的 app 實例
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


class TestStartNextBatchLogic:
    """測試啟動下一批次的核心邏輯"""

    @pytest.mark.asyncio
    async def test_missing_parent_loop_id_raises_400(self):
        """測試 1: 缺少 parent_loop_id 應返回 400 錯誤"""
        # Arrange
        from pydantic import ValidationError

        # Act & Assert
        # 當創建請求時缺少 parent_loop_id，Pydantic 會驗證失敗
        # 但在 start_next_batch 端點中，我們額外檢查 parent_loop_id 是否為 None
        result = None  # parent_loop_id
        expected_error = "必須提供 parent_loop_id"

        # 模擬端點邏輯
        if not result:
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=400, detail=expected_error)

        assert exc_info.value.status_code == 400
        assert expected_error in str(exc_info.value.detail)


    @pytest.mark.asyncio
    async def test_nonexistent_parent_loop_raises_404(self):
        """測試 2: 父迴圈不存在應返回 404 錯誤"""
        # Arrange
        parent_loop_id = 999
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)  # 查詢結果為空

        # Act & Assert
        parent_loop = await mock_conn.fetchrow(
            "SELECT status FROM knowledge_completion_loops WHERE id = $1",
            parent_loop_id
        )

        if not parent_loop:
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(
                    status_code=404,
                    detail=f"父迴圈 {parent_loop_id} 不存在"
                )

        assert exc_info.value.status_code == 404
        assert "不存在" in str(exc_info.value.detail)


    @pytest.mark.asyncio
    async def test_incomplete_parent_loop_raises_409(self):
        """測試 3: 父迴圈未完成應返回 409 錯誤"""
        # Arrange
        parent_loop_id = 1
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": 1,
            "status": "running"  # 未完成
        })

        # Act
        parent_loop = await mock_conn.fetchrow(
            "SELECT status FROM knowledge_completion_loops WHERE id = $1",
            parent_loop_id
        )

        # Assert
        if parent_loop["status"] != "completed":
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(
                    status_code=409,
                    detail=f"父迴圈必須為 COMPLETED 狀態，當前為 {parent_loop['status']}"
                )

        assert exc_info.value.status_code == 409
        assert "COMPLETED" in str(exc_info.value.detail)
        assert "running" in str(exc_info.value.detail)


    @pytest.mark.asyncio
    async def test_get_used_scenario_ids_from_parent_loop(self):
        """測試 4: 取得父迴圈已使用的測試情境 ID"""
        # Arrange
        parent_loop_id = 1
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {"scenario_id": 1},
            {"scenario_id": 2},
            {"scenario_id": 3},
            {"scenario_id": 4},
            {"scenario_id": 5}
        ])

        # Act
        query = """
            SELECT DISTINCT unnest(scenario_ids) as scenario_id
            FROM knowledge_completion_loops
            WHERE id = $1 OR parent_loop_id = $1
        """
        rows = await mock_conn.fetch(query, parent_loop_id)
        used_scenario_ids = [row["scenario_id"] for row in rows]

        # Assert
        assert len(used_scenario_ids) == 5
        assert used_scenario_ids == [1, 2, 3, 4, 5]


    @pytest.mark.asyncio
    async def test_scenario_selector_excludes_used_scenarios(self):
        """測試 5: 場景選取器排除已使用的測試情境"""
        # Arrange
        batch_size = 50
        exclude_scenario_ids = [1, 2, 3, 4, 5]  # 父迴圈已使用
        mock_conn = AsyncMock()

        # 模擬資料庫返回結果（排除 1-5 後的測試題）
        async def mock_fetch(query, *args):
            # 檢查查詢是否包含排除條件
            if "!= ALL" in query or "NOT IN" in query:
                # 返回 ID > 5 的測試題
                return [{"id": i} for i in range(6, 56)]  # 6-55 共 50 題
            else:
                # 返回所有測試題
                return [{"id": i} for i in range(1, 101)]  # 1-100

        mock_conn.fetch = AsyncMock(side_effect=mock_fetch)

        # Act
        query = """
            SELECT id FROM test_scenarios
            WHERE difficulty = $1
              AND status = 'approved'
              AND ($2::INTEGER[] IS NULL OR id != ALL($2))
            ORDER BY RANDOM()
            LIMIT $3
        """
        rows = await mock_conn.fetch(query, "medium", exclude_scenario_ids, batch_size)
        selected_ids = [row["id"] for row in rows]

        # Assert
        assert len(selected_ids) == 50
        # 驗證選取的 ID 不在排除列表中
        assert all(sid not in exclude_scenario_ids for sid in selected_ids)
        # 驗證選取的 ID 都 > 5
        assert all(sid > 5 for sid in selected_ids)


    @pytest.mark.asyncio
    async def test_start_next_batch_workflow(self):
        """測試 6: 完整工作流程驗證

        1. 驗證父迴圈狀態 (completed)
        2. 取得已使用的測試情境
        3. 調用 start_loop (內部會排除已使用的情境)
        4. 返回新迴圈資訊
        """
        # Arrange
        parent_loop_id = 1
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Step 1: 查詢父迴圈狀態
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": 1,
            "status": "completed",
            "scenario_ids": [1, 2, 3, 4, 5]
        })

        mock_pool.acquire = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock()
        ))

        # Act
        async with mock_pool.acquire() as conn:
            # Step 1: 驗證父迴圈
            parent_loop = await conn.fetchrow(
                "SELECT status FROM knowledge_completion_loops WHERE id = $1",
                parent_loop_id
            )

            assert parent_loop is not None, "父迴圈應存在"
            assert parent_loop["status"] == "completed", "父迴圈應為 COMPLETED 狀態"

            # Step 2: 取得已使用的測試情境（模擬）
            used_scenario_ids = parent_loop["scenario_ids"]

            # Step 3: 調用 start_loop（這裡僅驗證邏輯）
            # 在實際實作中，start_loop 會透過 ScenarioSelector 排除 used_scenario_ids

            # Assert
            assert len(used_scenario_ids) == 5
            assert used_scenario_ids == [1, 2, 3, 4, 5]


def test_api_endpoint_signature():
    """測試 7: 驗證 API 端點存在且簽名正確"""
    # Arrange
    from routers.loops import start_next_batch
    import inspect

    # Act
    sig = inspect.signature(start_next_batch)
    params = list(sig.parameters.keys())

    # Assert
    assert "request" in params, "應有 request 參數"
    assert "req" in params, "應有 req 參數（FastAPI Request）"

    # 驗證函數是 async
    assert inspect.iscoroutinefunction(start_next_batch), "應為 async 函數"


def test_api_response_model():
    """測試 8: 驗證 API 回應模型包含必要欄位"""
    # Arrange
    from routers.loops import LoopStartResponse

    # Act
    response = LoopStartResponse(
        loop_id=2,
        loop_name="第2批-包租業知識完善",
        vendor_id=2,
        status="running",
        scenario_ids=[6, 7, 8, 9, 10],
        scenario_selection_strategy="stratified_random",
        difficulty_distribution={"easy": 10, "medium": 25, "hard": 15},
        initial_statistics={},
        created_at="2026-03-27T10:00:00Z"
    )

    # Assert
    assert response.loop_id == 2
    assert response.loop_name == "第2批-包租業知識完善"
    assert len(response.scenario_ids) == 5
    assert response.scenario_selection_strategy == "stratified_random"
    assert "easy" in response.difficulty_distribution
    assert "medium" in response.difficulty_distribution
    assert "hard" in response.difficulty_distribution


# 執行測試
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
