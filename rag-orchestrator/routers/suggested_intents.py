"""
建議意圖 API 路由
管理 OpenAI 建議的新意圖
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter()


class ApproveRequest(BaseModel):
    """採納建議請求"""
    reviewed_by: str = Field(..., description="審核人員")
    review_note: Optional[str] = Field(None, description="審核備註")
    create_intent: bool = Field(True, description="是否自動建立意圖")


class RejectRequest(BaseModel):
    """拒絕建議請求"""
    reviewed_by: str = Field(..., description="審核人員")
    review_note: Optional[str] = Field(None, description="拒絕原因")


class MergeRequest(BaseModel):
    """合併建議請求"""
    suggestion_ids: List[int] = Field(..., description="要合併的建議 ID 列表")
    merged_name: str = Field(..., description="合併後的意圖名稱")
    merged_type: str = Field(..., description="合併後的意圖類型")
    merged_description: str = Field(..., description="合併後的描述")
    merged_keywords: List[str] = Field(..., description="合併後的關鍵字")
    reviewed_by: str = Field(..., description="審核人員")
    create_intent: bool = Field(True, description="是否建立意圖")


@router.get("/suggested-intents")
async def get_suggestions(
    req: Request,
    status: Optional[str] = None,
    order_by: str = 'frequency'
):
    """
    取得建議意圖列表

    Args:
        status: 過濾狀態（pending/approved/rejected/merged）
        order_by: 排序方式（frequency/latest/score）
    """
    try:
        suggestion_engine = req.app.state.suggestion_engine
        suggestions = suggestion_engine.get_suggestions(
            status=status,
            order_by=order_by
        )

        return {
            "suggestions": suggestions,
            "total": len(suggestions)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得建議列表失敗: {str(e)}"
        )


@router.get("/suggested-intents/stats")
async def get_suggestion_stats(req: Request):
    """取得建議統計資訊"""
    try:
        suggestion_engine = req.app.state.suggestion_engine
        stats = suggestion_engine.get_suggestion_stats()

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得統計資訊失敗: {str(e)}"
        )


@router.get("/suggested-intents/{suggestion_id}")
async def get_suggestion(suggestion_id: int, req: Request):
    """取得特定建議的詳細資訊"""
    try:
        suggestion_engine = req.app.state.suggestion_engine
        suggestions = suggestion_engine.get_suggestions()

        suggestion = next(
            (s for s in suggestions if s['id'] == suggestion_id),
            None
        )

        if not suggestion:
            raise HTTPException(
                status_code=404,
                detail=f"找不到建議 ID: {suggestion_id}"
            )

        return suggestion

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得建議詳情失敗: {str(e)}"
        )


@router.post("/suggested-intents/{suggestion_id}/approve")
async def approve_suggestion(
    suggestion_id: int,
    request: ApproveRequest,
    req: Request
):
    """
    採納建議意圖

    成功後會自動建立新意圖（如果 create_intent=True）
    """
    try:
        suggestion_engine = req.app.state.suggestion_engine

        intent_id = suggestion_engine.approve_suggestion(
            suggestion_id=suggestion_id,
            reviewed_by=request.reviewed_by,
            review_note=request.review_note,
            create_intent=request.create_intent
        )

        if not intent_id and request.create_intent:
            raise HTTPException(
                status_code=404,
                detail=f"找不到待審核的建議 ID: {suggestion_id}"
            )

        # 如果建立了新意圖，重新載入意圖分類器
        if intent_id:
            intent_classifier = req.app.state.intent_classifier
            intent_classifier.reload_intents()

        return {
            "message": "建議已採納",
            "suggestion_id": suggestion_id,
            "intent_id": intent_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"採納建議失敗: {str(e)}"
        )


@router.post("/suggested-intents/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: int,
    request: RejectRequest,
    req: Request
):
    """拒絕建議意圖"""
    try:
        suggestion_engine = req.app.state.suggestion_engine

        success = suggestion_engine.reject_suggestion(
            suggestion_id=suggestion_id,
            reviewed_by=request.reviewed_by,
            review_note=request.review_note
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"找不到待審核的建議 ID: {suggestion_id}"
            )

        return {
            "message": "建議已拒絕",
            "suggestion_id": suggestion_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"拒絕建議失敗: {str(e)}"
        )


@router.post("/suggested-intents/merge")
async def merge_suggestions(request: MergeRequest, req: Request):
    """
    合併多個建議為單一意圖

    適用於多個相似的建議應該整合為一個意圖的情況
    """
    try:
        suggestion_engine = req.app.state.suggestion_engine

        intent_id = suggestion_engine.merge_suggestions(
            suggestion_ids=request.suggestion_ids,
            merged_name=request.merged_name,
            merged_type=request.merged_type,
            merged_description=request.merged_description,
            merged_keywords=request.merged_keywords,
            reviewed_by=request.reviewed_by,
            create_intent=request.create_intent
        )

        if not intent_id and request.create_intent:
            raise HTTPException(
                status_code=400,
                detail="合併失敗，可能是部分建議已被處理"
            )

        # 如果建立了新意圖，重新載入意圖分類器
        if intent_id:
            intent_classifier = req.app.state.intent_classifier
            intent_classifier.reload_intents()

        return {
            "message": f"成功合併 {len(request.suggestion_ids)} 個建議",
            "intent_id": intent_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"合併建議失敗: {str(e)}"
        )
