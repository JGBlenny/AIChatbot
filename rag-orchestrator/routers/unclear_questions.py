"""
未釐清問題 API 路由
管理低信心度的未釐清問題
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from models.unclear_question import (
    UnclearQuestionUpdate,
    UnclearQuestionResponse,
    UnclearQuestionStatus
)

router = APIRouter()


@router.get("/unclear-questions")
async def get_unclear_questions(
    req: Request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "frequency"
):
    """
    取得未釐清問題列表

    - **status**: 狀態篩選 (pending/in_progress/resolved/ignored)
    - **limit**: 返回數量
    - **offset**: 偏移量
    - **order_by**: 排序欄位 (frequency/last_asked_at/created_at)
    """
    try:
        manager = req.app.state.unclear_question_manager
        questions = await manager.get_unclear_questions(
            status=status,
            limit=limit,
            offset=offset,
            order_by=order_by
        )

        return {
            "questions": questions,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得未釐清問題失敗: {str(e)}"
        )


@router.get("/unclear-questions/{question_id}")
async def get_unclear_question(question_id: int, req: Request):
    """
    取得特定未釐清問題的詳細資訊
    """
    try:
        manager = req.app.state.unclear_question_manager
        question = await manager.get_unclear_question_by_id(question_id)

        if not question:
            raise HTTPException(status_code=404, detail="問題不存在")

        return question

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得問題詳情失敗: {str(e)}"
        )


@router.put("/unclear-questions/{question_id}")
async def update_unclear_question(
    question_id: int,
    update: UnclearQuestionUpdate,
    req: Request
):
    """
    更新未釐清問題

    可更新：
    - status: 狀態 (pending/in_progress/resolved/ignored)
    - assigned_to: 指派給誰
    - resolution_note: 解決說明
    - suggested_answers: 建議答案
    """
    try:
        manager = req.app.state.unclear_question_manager

        # 檢查問題是否存在
        existing = await manager.get_unclear_question_by_id(question_id)
        if not existing:
            raise HTTPException(status_code=404, detail="問題不存在")

        # 更新
        success = await manager.update_unclear_question(
            question_id=question_id,
            status=update.status.value if update.status else None,
            assigned_to=update.assigned_to,
            resolution_note=update.resolution_note,
            suggested_answers=update.suggested_answers
        )

        if not success:
            raise HTTPException(status_code=400, detail="更新失敗")

        # 返回更新後的資料
        updated = await manager.get_unclear_question_by_id(question_id)
        return updated

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新問題失敗: {str(e)}"
        )


@router.delete("/unclear-questions/{question_id}")
async def delete_unclear_question(question_id: int, req: Request):
    """
    刪除未釐清問題
    """
    try:
        manager = req.app.state.unclear_question_manager
        success = await manager.delete_unclear_question(question_id)

        if not success:
            raise HTTPException(status_code=404, detail="問題不存在")

        return {
            "message": "問題已刪除",
            "question_id": question_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"刪除問題失敗: {str(e)}"
        )


@router.get("/unclear-questions-stats")
async def get_unclear_questions_stats(req: Request):
    """
    取得未釐清問題統計資訊
    """
    try:
        manager = req.app.state.unclear_question_manager
        stats = await manager.get_stats()
        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得統計失敗: {str(e)}"
        )


@router.get("/unclear-questions-search")
async def search_unclear_questions(
    req: Request,
    keyword: str,
    limit: int = 20
):
    """
    搜尋未釐清問題

    - **keyword**: 搜尋關鍵字
    - **limit**: 返回數量
    """
    try:
        manager = req.app.state.unclear_question_manager
        results = await manager.search_unclear_questions(
            keyword=keyword,
            limit=limit
        )

        return {
            "results": results,
            "keyword": keyword,
            "count": len(results)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜尋失敗: {str(e)}"
        )


class BatchUpdateRequest(BaseModel):
    """批次更新請求"""
    question_ids: List[int] = Field(..., description="問題 ID 列表")
    status: Optional[UnclearQuestionStatus] = None
    assigned_to: Optional[str] = None


@router.post("/unclear-questions-batch-update")
async def batch_update_unclear_questions(
    request: BatchUpdateRequest,
    req: Request
):
    """
    批次更新未釐清問題狀態
    """
    try:
        manager = req.app.state.unclear_question_manager
        updated_count = 0

        for question_id in request.question_ids:
            success = await manager.update_unclear_question(
                question_id=question_id,
                status=request.status.value if request.status else None,
                assigned_to=request.assigned_to
            )
            if success:
                updated_count += 1

        return {
            "message": "批次更新完成",
            "updated_count": updated_count,
            "total": len(request.question_ids)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批次更新失敗: {str(e)}"
        )
