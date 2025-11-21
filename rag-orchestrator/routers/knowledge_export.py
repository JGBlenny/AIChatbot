"""
知識庫匯出 API
支援匯出知識庫為 Excel 格式（基礎、進階格式化、效能優化三種模式）
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from pathlib import Path
import os

router = APIRouter(prefix="/api/v1/knowledge-export", tags=["Knowledge Export"])


class ExportJobStatus(BaseModel):
    """匯出任務狀態"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[Dict] = None  # {current: 5000, total: 10000, percentage: 50}
    result: Optional[Dict] = None  # {exported: 10000, file_size_kb: 1234, file_path: "..."}
    error: Optional[str] = None
    vendor_id: Optional[int] = None
    export_mode: Optional[str] = None  # basic, formatted, optimized
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExportRequest(BaseModel):
    """匯出請求"""
    vendor_id: Optional[int] = None
    export_mode: str = "formatted"  # basic, formatted, optimized
    include_intents: bool = True  # 是否包含意圖對照表
    include_metadata: bool = True  # 是否包含匯出資訊工作表


@router.post("/export")
async def create_export_job(
    request: Request,
    background_tasks: BackgroundTasks,
    export_request: ExportRequest
):
    """
    創建匯出任務

    支援三種匯出模式：
    1. basic: 基礎匯出（單工作表，基本格式）
    2. formatted: 進階格式化（多工作表，專業格式，推薦使用）
    3. optimized: 效能優化（支援 10 萬+ 筆資料，分批處理）

    Args:
        export_request: 匯出請求參數
            - vendor_id: 業者 ID（可選，留空表示匯出通用知識）
            - export_mode: 匯出模式（basic, formatted, optimized）
            - include_intents: 是否包含意圖對照表
            - include_metadata: 是否包含匯出資訊

    Returns:
        Dict: 包含 job_id 的回應
    """
    print(f"\n{'='*60}")
    print(f"📥 收到匯出請求")
    print(f"   業者 ID: {export_request.vendor_id or '通用知識'}")
    print(f"   匯出模式: {export_request.export_mode}")
    print(f"   包含意圖: {export_request.include_intents}")
    print(f"   包含資訊: {export_request.include_metadata}")
    print(f"{'='*60}\n")

    # 1. 驗證匯出模式
    allowed_modes = ['basic', 'formatted', 'optimized']
    if export_request.export_mode not in allowed_modes:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的匯出模式: {export_request.export_mode}. 支援的模式: {', '.join(allowed_modes)}"
        )

    # 2. 驗證業者 ID（如果提供）
    db_pool = request.app.state.db_pool
    if export_request.vendor_id:
        async with db_pool.acquire() as conn:
            vendor_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM vendors WHERE id = $1)",
                export_request.vendor_id
            )
            if not vendor_exists:
                raise HTTPException(status_code=404, detail=f"業者 ID {export_request.vendor_id} 不存在")

    # 3. 使用統一 Job 服務創建作業記錄
    from services.knowledge_export_service import KnowledgeExportService
    service = KnowledgeExportService(db_pool)

    job_id = await service.create_job(
        job_type='knowledge_export',
        vendor_id=export_request.vendor_id,
        user_id="admin",  # TODO: 從認證取得真實使用者 ID
        job_config={
            'export_mode': export_request.export_mode,
            'include_intents': export_request.include_intents,
            'include_metadata': export_request.include_metadata
        }
    )

    print(f"✅ 匯出作業已建立 (job_id: {job_id})")

    # 4. 啟動背景任務
    print(f"🚀 啟動背景匯出任務 (job_id: {job_id})")

    background_tasks.add_task(
        service.process_export_job,
        job_id=job_id,
        vendor_id=export_request.vendor_id,
        export_mode=export_request.export_mode,
        include_intents=export_request.include_intents,
        include_metadata=export_request.include_metadata,
        user_id="admin"  # TODO: 從認證取得真實使用者 ID
    )

    # 根據模式返回不同訊息
    mode_descriptions = {
        'basic': '基礎匯出模式（單工作表，快速匯出）',
        'formatted': '進階格式化模式（多工作表，專業格式）',
        'optimized': '效能優化模式（支援大量資料，分批處理）'
    }

    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"匯出任務已建立，開始處理中。{mode_descriptions[export_request.export_mode]}",
        "export_mode": export_request.export_mode,
        "vendor_id": export_request.vendor_id
    }


@router.get("/jobs/{job_id}")
async def get_export_job_status(job_id: str, request: Request):
    """
    獲取匯出任務狀態（供前端輪詢）

    Args:
        job_id: 任務 ID

    Returns:
        ExportJobStatus: 任務狀態
    """
    from services.knowledge_export_service import KnowledgeExportService
    db_pool = request.app.state.db_pool
    service = KnowledgeExportService(db_pool)

    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="任務不存在")

    # 從 config 中提取 export_mode
    export_mode = job.get('config', {}).get('export_mode', 'formatted')

    return {
        "job_id": str(job['job_id']),
        "status": job['status'],
        "progress": job.get('progress'),
        "result": job.get('result'),
        "error": job.get('error_message'),
        "vendor_id": job.get('vendor_id'),
        "export_mode": export_mode,
        "created_at": job['created_at'],
        "updated_at": job['updated_at'],
        "completed_at": job.get('completed_at')
    }


@router.get("/jobs/{job_id}/download")
async def download_export_file(job_id: str, request: Request):
    """
    下載匯出的 Excel 檔案

    Args:
        job_id: 任務 ID

    Returns:
        FileResponse: Excel 檔案
    """
    from services.knowledge_export_service import KnowledgeExportService
    db_pool = request.app.state.db_pool
    service = KnowledgeExportService(db_pool)

    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="任務不存在")

    if job['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"任務尚未完成（狀態: {job['status']}），無法下載"
        )

    # 從 result 取得檔案路徑
    result = job.get('result', {})
    file_path = result.get('file_path')

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="匯出檔案不存在")

    # 生成下載檔名
    vendor_id = job.get('vendor_id')
    vendor_name = "通用知識" if vendor_id is None else f"業者{vendor_id}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_filename = f"知識庫匯出_{vendor_name}_{timestamp}.xlsx"

    print(f"📥 下載匯出檔案: {download_filename} (job_id: {job_id})")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=download_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"'
        }
    )


@router.get("/jobs")
async def list_export_jobs(
    request: Request,
    vendor_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    列出匯出任務歷史

    Args:
        vendor_id: 業者 ID（可選，過濾特定業者）
        limit: 返回數量限制（1-100）
        offset: 偏移量

    Returns:
        Dict: 任務列表
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        if vendor_id is not None:
            jobs = await conn.fetch("""
                SELECT
                    job_id,
                    vendor_id,
                    job_config,
                    status,
                    success_records,
                    file_size_bytes,
                    created_at,
                    completed_at
                FROM unified_jobs
                WHERE vendor_id = $1 AND job_type = 'knowledge_export'
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """, vendor_id, limit, offset)

            total = await conn.fetchval("""
                SELECT COUNT(*) FROM unified_jobs
                WHERE vendor_id = $1 AND job_type = 'knowledge_export'
            """, vendor_id)
        else:
            jobs = await conn.fetch("""
                SELECT
                    job_id,
                    vendor_id,
                    job_config,
                    status,
                    success_records,
                    file_size_bytes,
                    created_at,
                    completed_at
                FROM unified_jobs
                WHERE job_type = 'knowledge_export'
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)

            total = await conn.fetchval("""
                SELECT COUNT(*) FROM unified_jobs WHERE job_type = 'knowledge_export'
            """)

        return {
            "jobs": [
                {
                    "job_id": str(job['job_id']),
                    "vendor_id": job['vendor_id'],
                    "export_mode": job['job_config'].get('export_mode', 'formatted') if job['job_config'] else 'formatted',
                    "status": job['status'],
                    "exported_count": job['success_records'],
                    "file_size_kb": round(job['file_size_bytes'] / 1024, 2) if job['file_size_bytes'] else None,
                    "created_at": job['created_at'].isoformat() if job['created_at'] else None,
                    "completed_at": job['completed_at'].isoformat() if job['completed_at'] else None
                }
                for job in jobs
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.delete("/jobs/{job_id}")
async def delete_export_job(job_id: str, request: Request):
    """
    刪除匯出任務記錄與檔案

    Args:
        job_id: 任務 ID

    Returns:
        Dict: 刪除結果
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        # 取得檔案路徑
        job = await conn.fetchrow("""
            SELECT result FROM unified_jobs WHERE job_id = $1
        """, uuid.UUID(job_id))

        if not job:
            raise HTTPException(status_code=404, detail="任務不存在")

        # 刪除實體檔案
        if job['result']:
            import json
            result = json.loads(job['result'])
            file_path = result.get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"✅ 已刪除匯出檔案: {file_path}")
                except Exception as e:
                    print(f"⚠️ 無法刪除檔案: {e}")

        # 刪除資料庫記錄
        deleted = await conn.fetchval("""
            DELETE FROM unified_jobs
            WHERE job_id = $1
            RETURNING job_id
        """, uuid.UUID(job_id))

    return {
        "message": "匯出任務已刪除",
        "job_id": job_id
    }


@router.get("/statistics")
async def get_export_statistics(
    request: Request,
    vendor_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    """
    取得匯出統計資訊

    Args:
        vendor_id: 業者 ID（可選）
        days: 統計天數（1-365）

    Returns:
        Dict: 統計資訊
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        # 基礎統計
        if vendor_id is not None:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_jobs,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_jobs,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_jobs,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing_jobs,
                    COALESCE(SUM(success_records), 0) as total_exported,
                    COALESCE(SUM(file_size_bytes), 0) as total_file_size,
                    COALESCE(AVG(success_records) FILTER (WHERE status = 'completed'), 0) as avg_exported_per_job
                FROM unified_jobs
                WHERE vendor_id = $1
                  AND job_type = 'knowledge_export'
                  AND created_at > CURRENT_TIMESTAMP - ($2 || ' days')::INTERVAL
            """, vendor_id, days)
        else:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_jobs,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_jobs,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_jobs,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing_jobs,
                    COALESCE(SUM(success_records), 0) as total_exported,
                    COALESCE(SUM(file_size_bytes), 0) as total_file_size,
                    COALESCE(AVG(success_records) FILTER (WHERE status = 'completed'), 0) as avg_exported_per_job
                FROM unified_jobs
                WHERE job_type = 'knowledge_export'
                  AND created_at > CURRENT_TIMESTAMP - ($1 || ' days')::INTERVAL
            """, days)

        # 計算成功率
        total_jobs = stats['total_jobs'] or 0
        completed_jobs = stats['completed_jobs'] or 0
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

        # 模式統計
        if vendor_id is not None:
            mode_stats = await conn.fetch("""
                SELECT
                    job_config->>'export_mode' as export_mode,
                    COUNT(*) as count,
                    COALESCE(AVG(success_records), 0) as avg_exported
                FROM unified_jobs
                WHERE vendor_id = $1
                  AND job_type = 'knowledge_export'
                  AND created_at > CURRENT_TIMESTAMP - ($2 || ' days')::INTERVAL
                  AND status = 'completed'
                GROUP BY job_config->>'export_mode'
            """, vendor_id, days)
        else:
            mode_stats = await conn.fetch("""
                SELECT
                    job_config->>'export_mode' as export_mode,
                    COUNT(*) as count,
                    COALESCE(AVG(success_records), 0) as avg_exported
                FROM unified_jobs
                WHERE job_type = 'knowledge_export'
                  AND created_at > CURRENT_TIMESTAMP - ($1 || ' days')::INTERVAL
                  AND status = 'completed'
                GROUP BY job_config->>'export_mode'
            """, days)

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": stats['failed_jobs'],
            "processing_jobs": stats['processing_jobs'],
            "total_exported": stats['total_exported'],
            "total_file_size_mb": round(stats['total_file_size'] / 1024 / 1024, 2),
            "avg_exported_per_job": round(float(stats['avg_exported_per_job']), 2),
            "success_rate": round(success_rate, 2),
            "mode_statistics": [
                {
                    "mode": mode['export_mode'],
                    "count": mode['count'],
                    "avg_exported": round(float(mode['avg_exported']), 2)
                }
                for mode in mode_stats
            ],
            "days": days
        }


@router.get("/preview")
async def preview_export(
    request: Request,
    vendor_id: Optional[int] = Query(None)
):
    """
    預覽匯出資料（不實際匯出，只返回統計資訊）

    Args:
        vendor_id: 業者 ID（可選）

    Returns:
        Dict: 預覽資訊
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        # 統計知識數量
        if vendor_id is not None:
            knowledge_count = await conn.fetchval("""
                SELECT COUNT(*) FROM knowledge WHERE vendor_id = $1
            """, vendor_id)

            intent_count = await conn.fetchval("""
                SELECT COUNT(*) FROM intents WHERE vendor_id = $1
            """, vendor_id)
        else:
            knowledge_count = await conn.fetchval("""
                SELECT COUNT(*) FROM knowledge WHERE vendor_id IS NULL
            """)

            intent_count = await conn.fetchval("""
                SELECT COUNT(*) FROM intents WHERE vendor_id IS NULL
            """)

        # 估算檔案大小（粗略計算）
        # 假設每筆知識約 500 bytes，加上格式化開銷
        estimated_size_kb = (knowledge_count * 0.5) + (intent_count * 0.2)

        # 推薦匯出模式
        if knowledge_count < 10000:
            recommended_mode = "formatted"
            recommendation = "推薦使用進階格式化模式，提供最佳閱讀體驗"
        elif knowledge_count < 50000:
            recommended_mode = "formatted"
            recommendation = "資料量適中，推薦使用進階格式化模式"
        else:
            recommended_mode = "optimized"
            recommendation = "資料量較大，推薦使用效能優化模式"

        return {
            "knowledge_count": knowledge_count,
            "intent_count": intent_count,
            "estimated_file_size_kb": round(estimated_size_kb, 2),
            "estimated_file_size_mb": round(estimated_size_kb / 1024, 2),
            "recommended_mode": recommended_mode,
            "recommendation": recommendation,
            "vendor_id": vendor_id,
            "message": "這是預覽模式，尚未實際執行匯出"
        }
