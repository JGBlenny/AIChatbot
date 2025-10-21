"""
緩存管理路由

提供緩存失效、統計和監控端點
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/api/v1", tags=["cache"])


class CacheInvalidationRequest(BaseModel):
    """緩存失效請求"""
    type: str  # "knowledge_update", "intent_update", "vendor_update"
    knowledge_id: Optional[int] = None
    intent_ids: Optional[List[int]] = None
    vendor_id: Optional[int] = None


class CacheInvalidationResponse(BaseModel):
    """緩存失效回應"""
    success: bool
    invalidated_count: int
    message: str


@router.post("/cache/invalidate", response_model=CacheInvalidationResponse)
async def invalidate_cache(request: CacheInvalidationRequest, req: Request):
    """
    接收緩存失效通知（事件驅動失效）

    Knowledge Admin 在更新知識時會呼叫此端點，通知 RAG Orchestrator 清除相關緩存

    Args:
        request: 失效請求，包含失效類型和相關 ID

    Returns:
        失效結果
    """
    cache_service = req.app.state.cache_service

    if not cache_service._is_available():
        return CacheInvalidationResponse(
            success=False,
            invalidated_count=0,
            message="緩存服務未啟用"
        )

    total_invalidated = 0

    try:
        if request.type == "knowledge_update" and request.knowledge_id:
            # 知識更新：清除相關緩存
            count = cache_service.invalidate_by_knowledge_id(request.knowledge_id)
            total_invalidated += count
            print(f"🗑️  知識更新失效: knowledge_id={request.knowledge_id}, 清除 {count} 條")

            # 同時清除相關 intent 的緩存
            if request.intent_ids:
                for intent_id in request.intent_ids:
                    count = cache_service.invalidate_by_intent_id(intent_id)
                    total_invalidated += count

        elif request.type == "intent_update" and request.intent_ids:
            # 意圖更新：清除相關緩存
            for intent_id in request.intent_ids:
                count = cache_service.invalidate_by_intent_id(intent_id)
                total_invalidated += count
            print(f"🗑️  意圖更新失效: intent_ids={request.intent_ids}, 清除 {total_invalidated} 條")

        elif request.type == "vendor_update" and request.vendor_id:
            # 業者配置更新：清除該業者所有緩存
            count = cache_service.invalidate_by_vendor_id(request.vendor_id)
            total_invalidated += count
            print(f"🗑️  業者更新失效: vendor_id={request.vendor_id}, 清除 {count} 條")

        else:
            raise HTTPException(
                status_code=400,
                detail=f"無效的失效請求類型或缺少必要參數: {request.type}"
            )

        return CacheInvalidationResponse(
            success=True,
            invalidated_count=total_invalidated,
            message=f"成功清除 {total_invalidated} 條緩存"
        )

    except Exception as e:
        print(f"⚠️  緩存失效失敗: {e}")
        return CacheInvalidationResponse(
            success=False,
            invalidated_count=total_invalidated,
            message=f"緩存失效部分失敗: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_all_cache(req: Request):
    """
    清除所有緩存（管理端點）

    Returns:
        清除結果
    """
    cache_service = req.app.state.cache_service

    if not cache_service._is_available():
        raise HTTPException(status_code=503, detail="緩存服務未啟用")

    try:
        success = cache_service.clear_all()

        if success:
            return {"success": True, "message": "所有緩存已清除"}
        else:
            raise HTTPException(status_code=500, detail="清除緩存失敗")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除緩存失敗: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats(req: Request) -> Dict[str, Any]:
    """
    獲取緩存統計資訊

    Returns:
        緩存統計數據
    """
    cache_service = req.app.state.cache_service
    return cache_service.get_stats()


@router.get("/cache/health")
async def cache_health_check(req: Request) -> Dict[str, Any]:
    """
    緩存健康檢查

    Returns:
        健康狀態
    """
    cache_service = req.app.state.cache_service
    return cache_service.health_check()
