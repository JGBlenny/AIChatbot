"""
測試 loop_knowledge router 的 Pydantic 模型

驗證所有請求/回應模型的結構、驗證規則與資料完整性。

Author: AI Assistant
Created: 2026-03-27
"""

import pytest
from pydantic import ValidationError
from datetime import datetime


def test_import_models():
    """測試 1: 驗證模型可正確導入"""
    from routers.loop_knowledge import (
        PendingKnowledgeQuery,
        PendingKnowledgeItem,
        PendingKnowledgeResponse,
        ReviewKnowledgeRequest,
        ReviewKnowledgeResponse,
        BatchReviewRequest,
        BatchReviewFailedItem,
        BatchReviewResponse,
    )

    assert PendingKnowledgeQuery is not None
    assert PendingKnowledgeItem is not None
    assert PendingKnowledgeResponse is not None
    assert ReviewKnowledgeRequest is not None
    assert ReviewKnowledgeResponse is not None
    assert BatchReviewRequest is not None
    assert BatchReviewFailedItem is not None
    assert BatchReviewResponse is not None


def test_pending_knowledge_query_valid():
    """測試 2: PendingKnowledgeQuery 有效資料"""
    from routers.loop_knowledge import PendingKnowledgeQuery

    # 最小有效資料（只有必填欄位）
    query = PendingKnowledgeQuery(vendor_id=2)
    assert query.vendor_id == 2
    assert query.loop_id is None
    assert query.knowledge_type is None
    assert query.status == "pending"
    assert query.limit == 50
    assert query.offset == 0

    # 完整資料
    query_full = PendingKnowledgeQuery(
        loop_id=123,
        vendor_id=2,
        knowledge_type="sop",
        status="approved",
        limit=100,
        offset=50
    )
    assert query_full.loop_id == 123
    assert query_full.vendor_id == 2
    assert query_full.knowledge_type == "sop"
    assert query_full.status == "approved"
    assert query_full.limit == 100
    assert query_full.offset == 50


def test_pending_knowledge_query_validation():
    """測試 3: PendingKnowledgeQuery 驗證規則"""
    from routers.loop_knowledge import PendingKnowledgeQuery

    # vendor_id 必填
    with pytest.raises(ValidationError) as exc_info:
        PendingKnowledgeQuery()
    assert "vendor_id" in str(exc_info.value)

    # limit 範圍檢查（應在 1-200）
    with pytest.raises(ValidationError):
        PendingKnowledgeQuery(vendor_id=2, limit=0)

    with pytest.raises(ValidationError):
        PendingKnowledgeQuery(vendor_id=2, limit=201)

    # offset 不能為負數
    with pytest.raises(ValidationError):
        PendingKnowledgeQuery(vendor_id=2, offset=-1)


def test_pending_knowledge_item_structure():
    """測試 4: PendingKnowledgeItem 資料結構"""
    from routers.loop_knowledge import PendingKnowledgeItem

    item = PendingKnowledgeItem(
        id=1,
        loop_id=123,
        iteration=2,
        question="租金每月幾號繳納？",
        answer="租金應於每月 5 日前繳納。",
        knowledge_type="sop",
        sop_config={"category_id": 1, "group_id": 2},
        similar_knowledge={
            "detected": True,
            "items": [{
                "id": 456,
                "source_table": "knowledge_base",
                "question_summary": "租金繳納日期",
                "similarity_score": 0.93
            }]
        },
        duplication_warning="檢測到 1 個高度相似的知識（相似度 93%）",
        status="pending",
        created_at="2026-03-27T10:00:00Z"
    )

    assert item.id == 1
    assert item.loop_id == 123
    assert item.iteration == 2
    assert item.question == "租金每月幾號繳納？"
    assert item.knowledge_type == "sop"
    assert item.similar_knowledge["detected"] is True
    assert item.duplication_warning is not None


def test_pending_knowledge_response_structure():
    """測試 5: PendingKnowledgeResponse 資料結構"""
    from routers.loop_knowledge import PendingKnowledgeResponse, PendingKnowledgeItem

    response = PendingKnowledgeResponse(
        total=150,
        items=[
            PendingKnowledgeItem(
                id=1,
                loop_id=123,
                iteration=1,
                question="測試問題",
                answer="測試答案",
                knowledge_type=None,
                sop_config=None,
                similar_knowledge=None,
                duplication_warning=None,
                status="pending",
                created_at="2026-03-27T10:00:00Z"
            )
        ]
    )

    assert response.total == 150
    assert len(response.items) == 1
    assert response.items[0].id == 1


def test_review_knowledge_request_valid():
    """測試 6: ReviewKnowledgeRequest 有效資料與驗證"""
    from routers.loop_knowledge import ReviewKnowledgeRequest

    # 批准請求
    request_approve = ReviewKnowledgeRequest(action="approve")
    assert request_approve.action == "approve"
    assert request_approve.modifications is None
    assert request_approve.review_notes is None

    # 拒絕請求（帶備註）
    request_reject = ReviewKnowledgeRequest(
        action="reject",
        review_notes="內容不夠精準，需要重新生成"
    )
    assert request_reject.action == "reject"
    assert request_reject.review_notes is not None

    # 批准請求（帶修改）
    request_modify = ReviewKnowledgeRequest(
        action="approve",
        modifications={
            "question": "修改後的問題",
            "answer": "修改後的答案"
        }
    )
    assert request_modify.action == "approve"
    assert request_modify.modifications is not None


def test_review_knowledge_response_structure():
    """測試 7: ReviewKnowledgeResponse 資料結構"""
    from routers.loop_knowledge import ReviewKnowledgeResponse

    # 批准並成功同步
    response = ReviewKnowledgeResponse(
        knowledge_id=1,
        action="approve",
        synced=True,
        synced_to="knowledge_base",
        synced_id=456,
        message="知識已批准並同步到 knowledge_base (ID: 456)"
    )

    assert response.knowledge_id == 1
    assert response.action == "approve"
    assert response.synced is True
    assert response.synced_to == "knowledge_base"
    assert response.synced_id == 456

    # 拒絕（未同步）
    response_reject = ReviewKnowledgeResponse(
        knowledge_id=2,
        action="reject",
        synced=False,
        synced_to=None,
        synced_id=None,
        message="知識已拒絕"
    )

    assert response_reject.action == "reject"
    assert response_reject.synced is False


def test_batch_review_request_valid():
    """測試 8: BatchReviewRequest 有效資料與驗證"""
    from routers.loop_knowledge import BatchReviewRequest

    # 最小批次（1 個）
    request_min = BatchReviewRequest(
        knowledge_ids=[1],
        action="approve"
    )
    assert len(request_min.knowledge_ids) == 1

    # 中等批次（20 個）
    request_medium = BatchReviewRequest(
        knowledge_ids=list(range(1, 21)),
        action="approve"
    )
    assert len(request_medium.knowledge_ids) == 20

    # 最大批次（100 個）
    request_max = BatchReviewRequest(
        knowledge_ids=list(range(1, 101)),
        action="reject"
    )
    assert len(request_max.knowledge_ids) == 100

    # 帶批量修改
    request_modify = BatchReviewRequest(
        knowledge_ids=[1, 2, 3],
        action="approve",
        modifications={"keywords": ["租金", "繳納"]}
    )
    assert request_modify.modifications is not None


def test_batch_review_request_validation():
    """測試 9: BatchReviewRequest 驗證規則"""
    from routers.loop_knowledge import BatchReviewRequest

    # knowledge_ids 不能為空
    with pytest.raises(ValidationError) as exc_info:
        BatchReviewRequest(knowledge_ids=[], action="approve")
    assert "min_items" in str(exc_info.value).lower() or "at least 1 item" in str(exc_info.value).lower()

    # knowledge_ids 不能超過 100 個
    with pytest.raises(ValidationError):
        BatchReviewRequest(
            knowledge_ids=list(range(1, 102)),
            action="approve"
        )

    # action 必填
    with pytest.raises(ValidationError):
        BatchReviewRequest(knowledge_ids=[1, 2, 3])


def test_batch_review_response_structure():
    """測試 10: BatchReviewResponse 資料結構"""
    from routers.loop_knowledge import BatchReviewResponse, BatchReviewFailedItem

    response = BatchReviewResponse(
        total=10,
        successful=8,
        failed=2,
        failed_items=[
            BatchReviewFailedItem(knowledge_id=3, error="知識不存在"),
            BatchReviewFailedItem(knowledge_id=7, error="資料庫錯誤")
        ],
        duration_ms=1234
    )

    assert response.total == 10
    assert response.successful == 8
    assert response.failed == 2
    assert len(response.failed_items) == 2
    assert response.failed_items[0].knowledge_id == 3
    assert response.duration_ms == 1234


def test_batch_review_failed_item_structure():
    """測試 11: BatchReviewFailedItem 資料結構"""
    from routers.loop_knowledge import BatchReviewFailedItem

    item = BatchReviewFailedItem(
        knowledge_id=123,
        error="同步失敗：embedding API 超時"
    )

    assert item.knowledge_id == 123
    assert item.error == "同步失敗：embedding API 超時"


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v", "--tb=short"])
