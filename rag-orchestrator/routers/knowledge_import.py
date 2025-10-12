"""
知識庫匯入 API
支援上傳多種格式的檔案（Excel, TXT, JSON），自動提取知識庫並去重
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request, Form
from pydantic import BaseModel
from typing import List, Dict, Optional
import tempfile
import os
import uuid
from datetime import datetime
from pathlib import Path

router = APIRouter(prefix="/api/v1/knowledge-import", tags=["Knowledge Import"])


class ImportJobStatus(BaseModel):
    """匯入任務狀態"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[Dict] = None  # {current: 50, total: 100, stage: "生成向量"}
    result: Optional[Dict] = None  # {imported: 40, skipped: 5, errors: 0}
    error: Optional[str] = None
    file_name: Optional[str] = None
    vendor_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ImportOptions(BaseModel):
    """匯入選項"""
    mode: str = "append"  # append, replace, merge
    enable_deduplication: bool = True
    vendor_id: Optional[int] = None


@router.post("/upload")
async def upload_knowledge_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    vendor_id: Optional[int] = Form(None),
    import_mode: str = Form("append"),
    enable_deduplication: bool = Form(True)
):
    """
    上傳知識檔案並開始匯入

    ⚠️ 重要：所有匯入的知識都會先進入審核佇列，
    需經過人工審核通過後才會加入正式知識庫。

    支援格式：
    - Excel (.xlsx, .xls)
    - 純文字 (.txt)
    - JSON (.json)

    Args:
        file: 上傳的檔案
        vendor_id: 業者 ID（可選，留空表示通用知識）
        import_mode: 匯入模式（append=追加, replace=替換, merge=合併）
        enable_deduplication: 是否啟用去重

    Returns:
        Dict: 包含 job_id 的回應
    """
    print(f"\n{'='*60}")
    print(f"📤 收到檔案上傳請求")
    print(f"   檔案名稱: {file.filename}")
    print(f"   Content-Type: {file.content_type}")
    print(f"   業者 ID: {vendor_id or '通用知識'}")
    print(f"   匯入模式: {import_mode}")
    print(f"   啟用去重: {enable_deduplication}")
    print(f"   審核模式: 強制（所有知識都需審核）")
    print(f"{'='*60}\n")

    # 1. 驗證檔案類型
    allowed_extensions = ['.xlsx', '.xls', '.txt', '.json']
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的檔案格式: {file_ext}. 支援的格式: {', '.join(allowed_extensions)}"
        )

    # 2. 驗證檔案大小（50MB 限制）
    content = await file.read()
    file_size = len(content)

    if file_size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"檔案大小超過 50MB 限制（當前: {file_size / 1024 / 1024:.2f}MB）"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="檔案為空")

    print(f"✅ 檔案驗證通過（大小: {file_size / 1024:.2f}KB）")

    # 3. 儲存臨時檔案
    job_id = str(uuid.uuid4())
    temp_dir = tempfile.gettempdir()
    safe_filename = f"{job_id}_{Path(file.filename).name}"
    temp_file_path = os.path.join(temp_dir, safe_filename)

    with open(temp_file_path, 'wb') as f:
        f.write(content)

    print(f"✅ 檔案已儲存到臨時目錄: {temp_file_path}")

    # 4. 取得資料庫連接池
    db_pool = request.app.state.db_pool

    # 5. 建立作業記錄（在啟動背景任務前）
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO knowledge_import_jobs (
                job_id, vendor_id, file_name, file_type, file_size_bytes, file_path,
                import_mode, enable_deduplication, created_by, status,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
            uuid.UUID(job_id),
            vendor_id,
            file.filename,
            file_ext[1:],  # Remove the leading dot
            file_size,
            temp_file_path,
            import_mode,
            enable_deduplication,
            "admin",  # TODO: 從認證取得真實使用者 ID
            "pending"
        )

    print(f"✅ 作業記錄已建立 (job_id: {job_id})")

    # 6. 啟動背景任務
    from services.knowledge_import_service import KnowledgeImportService

    service = KnowledgeImportService(db_pool)

    print(f"🚀 啟動背景處理任務 (job_id: {job_id})")

    background_tasks.add_task(
        service.process_import_job,
        job_id=job_id,
        file_path=temp_file_path,
        vendor_id=vendor_id,
        import_mode=import_mode,
        enable_deduplication=enable_deduplication,
        user_id="admin"  # TODO: 從認證取得真實使用者 ID
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "檔案上傳成功，開始處理中。所有知識將進入審核佇列，需經人工審核後才會正式加入知識庫。",
        "file_name": file.filename,
        "review_mode": "mandatory"
    }


@router.get("/jobs/{job_id}")
async def get_import_job_status(job_id: str, request: Request):
    """
    獲取匯入任務狀態（供前端輪詢）

    Args:
        job_id: 任務 ID

    Returns:
        ImportJobStatus: 任務狀態
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        job = await conn.fetchrow("""
            SELECT
                job_id,
                vendor_id,
                file_name,
                status,
                progress,
                result,
                error_message,
                created_at,
                updated_at
            FROM knowledge_import_jobs
            WHERE job_id = $1
        """, uuid.UUID(job_id))

        if not job:
            raise HTTPException(status_code=404, detail="任務不存在")

        # 解析 JSON 欄位
        import json
        progress = json.loads(job['progress']) if job['progress'] else None
        result = json.loads(job['result']) if job['result'] else None

        return {
            "job_id": str(job['job_id']),
            "status": job['status'],
            "progress": progress,
            "result": result,
            "error": job['error_message'],
            "file_name": job['file_name'],
            "vendor_id": job['vendor_id'],
            "created_at": job['created_at'].isoformat() if job['created_at'] else None,
            "updated_at": job['updated_at'].isoformat() if job['updated_at'] else None
        }


@router.get("/jobs")
async def list_import_jobs(
    request: Request,
    vendor_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    列出匯入任務歷史

    Args:
        vendor_id: 業者 ID（可選，過濾特定業者）
        limit: 返回數量限制
        offset: 偏移量

    Returns:
        List[Dict]: 任務列表
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        if vendor_id:
            jobs = await conn.fetch("""
                SELECT
                    job_id,
                    vendor_id,
                    file_name,
                    status,
                    imported_count,
                    skipped_count,
                    error_count,
                    created_at,
                    completed_at
                FROM knowledge_import_jobs
                WHERE vendor_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """, vendor_id, limit, offset)
        else:
            jobs = await conn.fetch("""
                SELECT
                    job_id,
                    vendor_id,
                    file_name,
                    status,
                    imported_count,
                    skipped_count,
                    error_count,
                    created_at,
                    completed_at
                FROM knowledge_import_jobs
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)

        # 取得總數
        if vendor_id:
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM knowledge_import_jobs WHERE vendor_id = $1
            """, vendor_id)
        else:
            total = await conn.fetchval("SELECT COUNT(*) FROM knowledge_import_jobs")

        return {
            "jobs": [
                {
                    "job_id": str(job['job_id']),
                    "vendor_id": job['vendor_id'],
                    "file_name": job['file_name'],
                    "status": job['status'],
                    "imported_count": job['imported_count'],
                    "skipped_count": job['skipped_count'],
                    "error_count": job['error_count'],
                    "created_at": job['created_at'].isoformat() if job['created_at'] else None,
                    "completed_at": job['completed_at'].isoformat() if job['completed_at'] else None
                }
                for job in jobs
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.post("/preview")
async def preview_knowledge_file(file: UploadFile = File(...)):
    """
    預覽檔案內容（不呼叫 LLM，不消耗 token）

    Args:
        file: 上傳的檔案

    Returns:
        Dict: 預覽資訊
    """
    # 驗證檔案類型
    allowed_extensions = ['.xlsx', '.xls', '.txt', '.json']
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的檔案格式: {file_ext}"
        )

    content = await file.read()
    file_size = len(content)

    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="檔案大小超過 50MB 限制")

    # 根據檔案類型預覽
    preview_data = {}

    if file_ext in ['.xlsx', '.xls']:
        # Excel 預覽
        import pandas as pd
        import io

        df = pd.read_excel(io.BytesIO(content), engine='openpyxl')

        preview_data = {
            "file_type": "excel",
            "total_rows": len(df),
            "columns": list(df.columns),
            "preview_rows": df.head(5).to_dict(orient='records'),
            "estimated_knowledge": len(df)  # 粗略估算
        }

    elif file_ext == '.txt':
        # 純文字預覽
        content_str = content.decode('utf-8', errors='ignore')
        lines = content_str.split('\n')

        preview_data = {
            "file_type": "text",
            "total_lines": len(lines),
            "preview_lines": lines[:20],
            "estimated_knowledge": len(lines) // 10  # 粗略估算
        }

    elif file_ext == '.json':
        # JSON 預覽
        import json
        data = json.loads(content.decode('utf-8'))

        if 'knowledge' in data:
            knowledge_list = data['knowledge']
        elif 'knowledge_list' in data:
            knowledge_list = data['knowledge_list']
        elif isinstance(data, list):
            knowledge_list = data
        else:
            knowledge_list = []

        preview_data = {
            "file_type": "json",
            "total_items": len(knowledge_list),
            "preview_items": knowledge_list[:5] if knowledge_list else [],
            "estimated_knowledge": len(knowledge_list)
        }

    return {
        "filename": file.filename,
        "file_size_kb": file_size / 1024,
        **preview_data,
        "message": "這是預覽模式，尚未消耗任何 OpenAI token"
    }


@router.delete("/jobs/{job_id}")
async def delete_import_job(job_id: str, request: Request):
    """
    刪除匯入任務記錄

    Args:
        job_id: 任務 ID

    Returns:
        Dict: 刪除結果
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        deleted = await conn.fetchval("""
            DELETE FROM knowledge_import_jobs
            WHERE job_id = $1
            RETURNING job_id
        """, uuid.UUID(job_id))

        if not deleted:
            raise HTTPException(status_code=404, detail="任務不存在")

    return {
        "message": "任務已刪除",
        "job_id": job_id
    }


@router.get("/statistics")
async def get_import_statistics(
    request: Request,
    vendor_id: Optional[int] = None,
    days: int = 30
):
    """
    取得匯入統計資訊

    Args:
        vendor_id: 業者 ID（可選）
        days: 統計天數

    Returns:
        Dict: 統計資訊
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT * FROM get_import_statistics($1, $2)
        """, vendor_id, days)

        return {
            "total_jobs": stats['total_jobs'],
            "completed_jobs": stats['completed_jobs'],
            "failed_jobs": stats['failed_jobs'],
            "processing_jobs": stats['processing_jobs'],
            "total_imported": stats['total_imported'],
            "total_skipped": stats['total_skipped'],
            "total_errors": stats['total_errors'],
            "avg_imported_per_job": float(stats['avg_imported_per_job']) if stats['avg_imported_per_job'] else 0,
            "success_rate": float(stats['success_rate']) if stats['success_rate'] else 0,
            "days": days
        }
