"""
Pipeline 健康檢查路由

提供 pipeline 元件健康檢查與端到端測試端點
"""
import logging
from fastapi import APIRouter, HTTPException

from services.pipeline_health_service import PipelineHealthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["system_health"])

# Module-level singleton — PipelineHealthService 無需建構參數
_health_service = PipelineHealthService()


@router.get("/pipeline-health")
async def get_pipeline_health():
    """
    聚合檢查所有 pipeline 元件健康狀態

    並行檢查 7 個元件（PostgreSQL、Redis、Embedding API、Reranker、LLM API、
    Vector Search、Keyword Search），每個 checker 5 秒 timeout，整體 15 秒內完成。

    回傳 overall_status:
    - healthy: 所有元件正常
    - degraded: 核心元件正常，非核心元件異常
    - unhealthy: 任一核心元件異常

    NOTE: 此端點目前無認證保護。rag-orchestrator 沒有既有的 admin auth 機制，
    與 knowledge-admin backend 的認證系統獨立。若未來需要保護，需先建立
    rag-orchestrator 的認證中間件。
    """
    try:
        result = await _health_service.check_all_components()
        return result
    except Exception as e:
        logger.error(f"Pipeline health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"健康檢查失敗: {str(e)}")


@router.post("/pipeline-e2e-test")
async def run_pipeline_e2e_test():
    """
    執行端到端 pipeline 測試

    使用固定測試查詢依序驗證：Embedding → Vector Search → Keyword Search → Reranker。
    任一階段失敗則後續階段標記為 skipped。

    NOTE: 此端點目前無認證保護（同上述說明）。
    """
    try:
        result = await _health_service.run_e2e_test()
        return result
    except Exception as e:
        logger.error(f"Pipeline E2E test failed: {e}")
        raise HTTPException(status_code=500, detail=f"端到端測試失敗: {str(e)}")
