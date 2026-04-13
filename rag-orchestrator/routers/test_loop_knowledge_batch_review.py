"""
測試批量審核端點

驗證 POST /api/v1/loop-knowledge/batch-review 端點的功能：
- 批量審核多個知識項目（1-100 個）
- 部分成功模式（某項失敗不影響其他項）
- 失敗項目記錄與錯誤訊息
- 批量修改參數支援
- 效能統計（duration_ms）
- 錯誤處理

Author: AI Assistant
Created: 2026-03-27
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.fixture
def app():
    """創建測試用 FastAPI 應用"""
    from routers.loop_knowledge import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """創建測試客戶端"""
    return TestClient(app)


def test_batch_review_approve_all_success(client):
    """測試 1: 批量批准所有項目（全部成功）"""
    # Mock 資料庫查詢
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        # Mock 所有查詢成功
        mock_conn.fetchrow.side_effect = [
            # 第一個知識項目
            {
                'id': 1,
                'loop_id': 123,
                'iteration': 1,
                'question': '租金何時繳納？',
                'answer': '每月 5 日前',
                'knowledge_type': None,
                'sop_config': None,
                'status': 'pending'
            },
            # 第二個知識項目
            {
                'id': 2,
                'loop_id': 123,
                'iteration': 1,
                'question': '可以養寵物嗎？',
                'answer': '不可以',
                'knowledge_type': None,
                'sop_config': None,
                'status': 'pending'
            }
        ]

        # Mock execute 成功
        mock_conn.execute.return_value = None

        # 發送批量審核請求
        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1, 2],
                "action": "approve"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 2
        assert data['successful'] == 2
        assert data['failed'] == 0
        assert len(data['failed_items']) == 0
        assert data['duration_ms'] > 0


def test_batch_review_reject_all_success(client):
    """測試 2: 批量拒絕所有項目（全部成功）"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        # Mock 查詢結果
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'loop_id': 123, 'iteration': 1, 'question': 'Q1', 'answer': 'A1', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'},
            {'id': 2, 'loop_id': 123, 'iteration': 1, 'question': 'Q2', 'answer': 'A2', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'}
        ]
        mock_conn.execute.return_value = None

        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1, 2],
                "action": "reject",
                "review_notes": "不符合標準"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['successful'] == 2
        assert data['failed'] == 0


def test_batch_review_partial_success(client):
    """測試 3: 部分成功模式（某項失敗不影響其他項）"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        # Mock: 第一個成功，第二個不存在，第三個成功
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'loop_id': 123, 'iteration': 1, 'question': 'Q1', 'answer': 'A1', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'},
            None,  # 第二個不存在
            {'id': 3, 'loop_id': 123, 'iteration': 1, 'question': 'Q3', 'answer': 'A3', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'}
        ]
        mock_conn.execute.return_value = None

        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1, 2, 3],
                "action": "approve"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 3
        assert data['successful'] == 2  # 1 和 3 成功
        assert data['failed'] == 1  # 2 失敗
        assert len(data['failed_items']) == 1
        assert data['failed_items'][0]['knowledge_id'] == 2
        assert 'not found' in data['failed_items'][0]['error'].lower() or '不存在' in data['failed_items'][0]['error']


def test_batch_review_with_modifications(client):
    """測試 4: 批量修改參數支援"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'loop_id': 123, 'iteration': 1, 'question': 'Q1', 'answer': 'A1', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'},
            {'id': 2, 'loop_id': 123, 'iteration': 1, 'question': 'Q2', 'answer': 'A2', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'}
        ]
        mock_conn.execute.return_value = None

        # 批量修改 question
        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1, 2],
                "action": "approve",
                "modifications": {
                    "question": "統一修改的問題"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['successful'] == 2


def test_batch_review_empty_list(client):
    """測試 5: 空的 knowledge_ids 列表（驗證失敗）"""
    response = client.post(
        "/api/v1/loop-knowledge/batch-review",
        json={
            "knowledge_ids": [],
            "action": "approve"
        }
    )

    # Pydantic 驗證應拒絕空列表
    assert response.status_code == 422


def test_batch_review_exceed_max_limit(client):
    """測試 6: 超過最大數量限制（101 個）"""
    response = client.post(
        "/api/v1/loop-knowledge/batch-review",
        json={
            "knowledge_ids": list(range(1, 102)),  # 101 個
            "action": "approve"
        }
    )

    # Pydantic 驗證應拒絕超過 100 個
    assert response.status_code == 422


def test_batch_review_invalid_action(client):
    """測試 7: 無效的 action 參數"""
    response = client.post(
        "/api/v1/loop-knowledge/batch-review",
        json={
            "knowledge_ids": [1, 2],
            "action": "delete"  # 無效動作
        }
    )

    # 應該在處理時被拒絕（400 或 422）
    assert response.status_code in [400, 422]


def test_batch_review_all_failed(client):
    """測試 8: 所有項目都失敗"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        # Mock 所有項目都不存在
        mock_conn.fetchrow.side_effect = [None, None, None]

        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1, 2, 3],
                "action": "approve"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 3
        assert data['successful'] == 0
        assert data['failed'] == 3
        assert len(data['failed_items']) == 3


def test_batch_review_database_error(client):
    """測試 9: 資料庫錯誤處理"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        # Mock 資料庫連接失敗
        mock_connect.side_effect = Exception("Database connection failed")

        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1, 2],
                "action": "approve"
            }
        )

        # 應返回 500 錯誤
        assert response.status_code == 500


def test_batch_review_event_logging(client):
    """測試 10: 批量審核事件記錄"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'loop_id': 123, 'iteration': 1, 'question': 'Q1', 'answer': 'A1', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'},
            {'id': 2, 'loop_id': 123, 'iteration': 1, 'question': 'Q2', 'answer': 'A2', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'}
        ]
        mock_conn.execute.return_value = None

        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1, 2],
                "action": "approve"
            }
        )

        assert response.status_code == 200

        # 驗證是否調用了事件記錄（execute 應被調用多次）
        # 每個項目：更新 + 事件記錄 = 2 次
        # 加上批量事件記錄 = 1 次
        # 總共至少 5 次 execute
        assert mock_conn.execute.call_count >= 5


def test_batch_review_duration_measurement(client):
    """測試 11: 執行時間統計"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetchrow.return_value = {
            'id': 1, 'loop_id': 123, 'iteration': 1, 'question': 'Q1',
            'answer': 'A1', 'knowledge_type': None, 'sop_config': None, 'status': 'pending'
        }
        mock_conn.execute.return_value = None

        response = client.post(
            "/api/v1/loop-knowledge/batch-review",
            json={
                "knowledge_ids": [1],
                "action": "approve"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證 duration_ms 存在且為正數
        assert 'duration_ms' in data
        assert data['duration_ms'] > 0
        assert isinstance(data['duration_ms'], (int, float))


if __name__ == "__main__":
    print("批量審核端點測試")
    print("=" * 50)
    print("測試範圍：")
    print("  1. 批量批准/拒絕（全部成功）")
    print("  2. 部分成功模式（失敗不影響其他項）")
    print("  3. 修改參數支援")
    print("  4. 邊界條件（空列表、超過限制）")
    print("  5. 錯誤處理（無效動作、資料庫錯誤）")
    print("  6. 事件記錄")
    print("  7. 效能統計（duration_ms）")
    print()
    pytest.main([__file__, "-v", "--tb=short"])
