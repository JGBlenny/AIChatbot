"""
測試查詢待審核知識端點

驗證 GET /api/v1/loop-knowledge/pending 端點的功能：
- 篩選參數（loop_id, vendor_id, knowledge_type, status）
- 分頁參數（limit, offset）
- 資料庫查詢邏輯
- 重複檢測警告顯示

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


def test_get_pending_knowledge_basic(client):
    """測試 1: 基本查詢功能（必填參數）"""
    # Mock 資料庫查詢
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        # Mock 查詢結果
        mock_conn.fetch.return_value = [
            {
                'id': 1,
                'loop_id': 123,
                'iteration': 1,
                'question': '租金每月幾號繳納？',
                'answer': '租金應於每月 5 日前繳納。',
                'knowledge_type': None,
                'sop_config': None,
                'similar_knowledge': None,
                'status': 'pending',
                'created_at': '2026-03-27T10:00:00Z'
            }
        ]
        mock_conn.fetchval.return_value = 1  # total count

        # 發送請求
        response = client.get("/api/v1/loop-knowledge/pending?vendor_id=2")

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1
        assert len(data['items']) == 1
        assert data['items'][0]['id'] == 1
        assert data['items'][0]['question'] == '租金每月幾號繳納？'


def test_get_pending_knowledge_with_filters(client):
    """測試 2: 篩選參數（loop_id, knowledge_type, status）"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch.return_value = []
        mock_conn.fetchval.return_value = 0

        # 測試多個篩選參數
        response = client.get(
            "/api/v1/loop-knowledge/pending?"
            "vendor_id=2&loop_id=123&knowledge_type=sop&status=pending"
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert len(data['items']) == 0


def test_get_pending_knowledge_pagination(client):
    """測試 3: 分頁參數（limit, offset）"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        # 模擬 100 筆資料，取第 2 頁（offset=50, limit=50）
        mock_conn.fetch.return_value = [
            {
                'id': i,
                'loop_id': 123,
                'iteration': 1,
                'question': f'問題 {i}',
                'answer': f'答案 {i}',
                'knowledge_type': None,
                'sop_config': None,
                'similar_knowledge': None,
                'status': 'pending',
                'created_at': '2026-03-27T10:00:00Z'
            }
            for i in range(51, 101)
        ]
        mock_conn.fetchval.return_value = 100

        response = client.get("/api/v1/loop-knowledge/pending?vendor_id=2&limit=50&offset=50")

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 100
        assert len(data['items']) == 50
        assert data['items'][0]['id'] == 51  # 第 51 筆開始


def test_get_pending_knowledge_with_duplication_warning(client):
    """測試 4: 重複檢測警告顯示"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch.return_value = [
            {
                'id': 1,
                'loop_id': 123,
                'iteration': 1,
                'question': '租金繳納日期',
                'answer': '租金應於每月 5 日前繳納。',
                'knowledge_type': None,
                'sop_config': None,
                'similar_knowledge': {
                    'detected': True,
                    'items': [{
                        'id': 456,
                        'source_table': 'knowledge_base',
                        'question_summary': '租金繳納日期說明',
                        'similarity_score': 0.93
                    }]
                },
                'status': 'pending',
                'created_at': '2026-03-27T10:00:00Z'
            }
        ]
        mock_conn.fetchval.return_value = 1

        response = client.get("/api/v1/loop-knowledge/pending?vendor_id=2")

        assert response.status_code == 200
        data = response.json()
        item = data['items'][0]

        # 驗證重複檢測結果
        assert item['similar_knowledge'] is not None
        assert item['similar_knowledge']['detected'] is True
        assert len(item['similar_knowledge']['items']) == 1

        # 驗證警告文字（由後端生成）
        assert item['duplication_warning'] is not None
        assert '相似' in item['duplication_warning']
        assert '93%' in item['duplication_warning']


def test_get_pending_knowledge_missing_vendor_id(client):
    """測試 5: 缺少必填參數 vendor_id"""
    response = client.get("/api/v1/loop-knowledge/pending")

    assert response.status_code == 422  # Validation Error
    data = response.json()
    assert 'detail' in data


def test_get_pending_knowledge_invalid_limit(client):
    """測試 6: 無效的 limit 參數（超出範圍）"""
    # limit 超過 200
    response = client.get("/api/v1/loop-knowledge/pending?vendor_id=2&limit=201")
    assert response.status_code == 422

    # limit 小於 1
    response = client.get("/api/v1/loop-knowledge/pending?vendor_id=2&limit=0")
    assert response.status_code == 422


def test_get_pending_knowledge_empty_result(client):
    """測試 7: 查詢結果為空"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch.return_value = []
        mock_conn.fetchval.return_value = 0

        response = client.get("/api/v1/loop-knowledge/pending?vendor_id=2")

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert len(data['items']) == 0


def test_get_pending_knowledge_sop_type(client):
    """測試 8: 查詢 SOP 類型知識"""
    with patch('routers.loop_knowledge.asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch.return_value = [
            {
                'id': 1,
                'loop_id': 123,
                'iteration': 1,
                'question': '如何申請停車位？',
                'answer': '請按照以下步驟申請...',
                'knowledge_type': 'sop',
                'sop_config': {
                    'category_id': 1,
                    'group_id': 2,
                    'item_name': '停車位申請流程'
                },
                'similar_knowledge': None,
                'status': 'pending',
                'created_at': '2026-03-27T10:00:00Z'
            }
        ]
        mock_conn.fetchval.return_value = 1

        response = client.get("/api/v1/loop-knowledge/pending?vendor_id=2&knowledge_type=sop")

        assert response.status_code == 200
        data = response.json()
        assert data['items'][0]['knowledge_type'] == 'sop'
        assert data['items'][0]['sop_config'] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
