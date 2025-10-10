"""
知識庫分類 API Router
提供知識庫自動分類和批次重新分類功能
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from services.knowledge_classifier import KnowledgeClassifier


router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

# 全域 Knowledge Classifier 實例
knowledge_classifier = None


def get_classifier() -> KnowledgeClassifier:
    """獲取 Knowledge Classifier 實例（懶加載）"""
    global knowledge_classifier
    if knowledge_classifier is None:
        knowledge_classifier = KnowledgeClassifier()
    return knowledge_classifier


# ========== Schemas ==========

class ClassifySingleRequest(BaseModel):
    """分類單一知識請求"""
    knowledge_id: int = Field(..., description="知識庫 ID")
    question_summary: Optional[str] = Field(None, description="問題摘要")
    answer: str = Field(..., description="答案內容")
    assigned_by: str = Field('auto', description="分配方式: auto/manual")


class ClassifyBatchRequest(BaseModel):
    """批次分類請求"""
    filters: Optional[Dict] = Field(
        None,
        description="過濾條件",
        example={
            "intent_ids": [1, 2],
            "max_confidence": 0.7,
            "assigned_by": "auto",
            "older_than_days": 30,
            "needs_reclassify": True
        }
    )
    batch_size: int = Field(100, ge=1, le=1000, description="每批處理數量")
    dry_run: bool = Field(False, description="預覽模式（不實際更新）")


class MarkReclassifyRequest(BaseModel):
    """標記需要重新分類請求"""
    intent_ids: Optional[List[int]] = Field(None, description="意圖 ID 列表")
    all_knowledge: bool = Field(False, description="標記所有知識")


class ClassifyResponse(BaseModel):
    """分類回應"""
    knowledge_id: int
    classified: bool
    intent_id: Optional[int] = None
    intent_name: Optional[str] = None
    intent_type: Optional[str] = None
    confidence: Optional[float] = None
    keywords: Optional[List[str]] = None
    reason: Optional[str] = None
    error: Optional[str] = None


class BatchClassifyResponse(BaseModel):
    """批次分類回應"""
    dry_run: bool = False
    total_to_process: Optional[int] = None
    estimated_batches: Optional[int] = None
    preview_items: Optional[List[Dict]] = None
    preview_limit: Optional[int] = None
    has_more: Optional[bool] = None
    total_processed: Optional[int] = None
    success_count: Optional[int] = None
    failed_count: Optional[int] = None
    unclear_count: Optional[int] = None
    details: Optional[List[Dict]] = None


class StatsResponse(BaseModel):
    """統計資訊回應"""
    overall: Dict
    by_intent: List[Dict]


# ========== API 端點 ==========

@router.post("/classify", response_model=ClassifyResponse)
async def classify_single_knowledge(request: ClassifySingleRequest):
    """
    分類單一知識條目

    自動為知識分配意圖類型
    """
    try:
        classifier = get_classifier()
        result = classifier.classify_single_knowledge(
            knowledge_id=request.knowledge_id,
            question_summary=request.question_summary,
            answer=request.answer,
            assigned_by=request.assigned_by
        )

        return ClassifyResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分類失敗: {str(e)}")


@router.post("/classify/batch", response_model=BatchClassifyResponse)
async def classify_batch_knowledge(
    request: ClassifyBatchRequest,
    background_tasks: BackgroundTasks
):
    """
    批次分類知識庫

    支援過濾條件、預覽模式和後台處理
    """
    try:
        classifier = get_classifier()

        # 如果是 dry_run，直接執行並返回
        if request.dry_run:
            result = classifier.classify_batch(
                filters=request.filters,
                batch_size=request.batch_size,
                dry_run=True
            )
            return BatchClassifyResponse(**result)

        # 如果 batch_size 較大，使用後台任務
        if request.batch_size > 50:
            # 後台處理（這裡簡化處理，實際可使用 Celery）
            result = classifier.classify_batch(
                filters=request.filters,
                batch_size=request.batch_size,
                dry_run=False
            )
            return BatchClassifyResponse(**result)
        else:
            # 同步處理
            result = classifier.classify_batch(
                filters=request.filters,
                batch_size=request.batch_size,
                dry_run=False
            )
            return BatchClassifyResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次分類失敗: {str(e)}")


@router.post("/mark-reclassify")
async def mark_for_reclassify(request: MarkReclassifyRequest):
    """
    標記知識需要重新分類

    用於意圖更新後，標記相關知識需要重新分類
    """
    try:
        classifier = get_classifier()

        affected_count = classifier.mark_for_reclassify(
            intent_ids=request.intent_ids,
            all_knowledge=request.all_knowledge
        )

        return {
            "success": True,
            "affected_count": affected_count,
            "message": f"已標記 {affected_count} 筆知識需要重新分類"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"標記失敗: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_classification_stats():
    """
    獲取知識庫分類統計資訊

    返回整體統計和按意圖統計
    """
    try:
        classifier = get_classifier()
        stats = classifier.get_classification_stats()

        return StatsResponse(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取統計失敗: {str(e)}")


@router.post("/reload")
async def reload_intents():
    """
    重新載入意圖配置

    用於意圖更新後，重新載入分類器
    """
    try:
        classifier = get_classifier()
        success = classifier.reload_intents()

        if success:
            return {
                "success": True,
                "message": "意圖配置已重新載入"
            }
        else:
            raise HTTPException(status_code=500, detail="重新載入失敗")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新載入失敗: {str(e)}")


@router.get("/health")
async def health_check():
    """健康檢查"""
    try:
        classifier = get_classifier()
        stats = classifier.get_classification_stats()

        return {
            "status": "healthy",
            "total_knowledge": stats['overall']['total_knowledge'],
            "classified_count": stats['overall']['classified_count'],
            "service": "knowledge_classifier"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "knowledge_classifier"
        }
