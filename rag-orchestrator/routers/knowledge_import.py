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
    enable_deduplication: bool = Form(True),
    skip_review: bool = Form(False),
    default_priority: int = Form(0),
    enable_quality_evaluation: bool = Form(True),
    business_types: Optional[str] = Form(None)  # JSON string of business type values
):
    """
    上傳知識檔案並開始匯入

    ⚠️ 重要提醒：
    - skip_review=False（預設）：知識會先進入審核佇列，需經人工審核後才會加入正式知識庫
    - skip_review=True：知識會直接加入正式知識庫（跳過審核，請謹慎使用）

    支援格式：
    - Excel (.xlsx, .xls)
    - 純文字 (.txt)
    - JSON (.json)
    - CSV (.csv)

    Args:
        file: 上傳的檔案
        vendor_id: 業者 ID（可選，留空表示通用知識）
        import_mode: 匯入模式（append=追加, replace=替換, merge=合併）
        enable_deduplication: 是否啟用去重
        skip_review: 是否跳過審核直接加入知識庫（預設 False）
        default_priority: 統一優先級（0=未啟用，1=已啟用，僅在 skip_review=True 時生效）
        enable_quality_evaluation: 是否啟用質量評估（預設 True，關閉可加速大量匯入）

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
    print(f"   質量評估: {'已啟用' if enable_quality_evaluation else '已關閉（快速模式）'}")
    print(f"   審核模式: {'跳過審核（直接加入知識庫）' if skip_review else '需要審核'}")
    if skip_review and default_priority > 0:
        print(f"   優先級: 統一啟用 (priority={default_priority})")
    print(f"{'='*60}\n")

    # 1. 驗證檔案類型
    allowed_extensions = ['.xlsx', '.xls', '.csv', '.txt', '.json']
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

    # 5. 使用統一 Job 服務建立作業記錄
    from services.knowledge_import_service import KnowledgeImportService
    service = KnowledgeImportService(db_pool)

    job_id = await service.create_job(
        job_type='knowledge_import',
        vendor_id=vendor_id,
        user_id="admin",  # TODO: 從認證取得真實使用者 ID
        job_config={
            'import_mode': import_mode,
            'enable_deduplication': enable_deduplication,
            'skip_review': skip_review,
            'default_priority': default_priority,
            'enable_quality_evaluation': enable_quality_evaluation,
            'file_type': file_ext[1:]
        },
        file_path=temp_file_path,
        file_name=file.filename,
        file_size_bytes=file_size
    )

    print(f"✅ 作業記錄已建立 (job_id: {job_id})")

    # 6. 啟動背景任務

    print(f"🚀 啟動背景處理任務 (job_id: {job_id})")

    # 解析業態類型
    business_types_list = []
    if business_types:
        try:
            import json
            business_types_list = json.loads(business_types)
            print(f"📋 業態類型: {business_types_list}")
        except Exception as e:
            print(f"⚠️ 無法解析業態類型: {e}")

    background_tasks.add_task(
        service.process_import_job,
        job_id=job_id,
        file_path=temp_file_path,
        vendor_id=vendor_id,
        import_mode=import_mode,
        enable_deduplication=enable_deduplication,
        skip_review=skip_review,
        default_priority=default_priority,
        enable_quality_evaluation=enable_quality_evaluation,
        business_types=business_types_list,
        user_id="admin"  # TODO: 從認證取得真實使用者 ID
    )

    # 根據模式返回不同訊息
    if skip_review:
        message = "檔案上傳成功，開始處理中。知識將直接加入正式知識庫（已跳過審核）。"
        review_mode = "skipped"
    else:
        message = "檔案上傳成功，開始處理中。所有知識將進入審核佇列，需經人工審核後才會正式加入知識庫。"
        review_mode = "mandatory"

    return {
        "job_id": job_id,
        "status": "processing",
        "message": message,
        "file_name": file.filename,
        "review_mode": review_mode,
        "skip_review": skip_review
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
                job_result,
                error_message,
                created_at,
                updated_at
            FROM unified_jobs
            WHERE job_id = $1
        """, uuid.UUID(job_id))

        if not job:
            raise HTTPException(status_code=404, detail="任務不存在")

        # 解析 JSON 欄位
        import json
        progress = json.loads(job['progress']) if job['progress'] else None
        result = json.loads(job['job_result']) if job['job_result'] else None

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
                    success_records,
                    skipped_records,
                    failed_records,
                    created_at,
                    completed_at
                FROM unified_jobs
                WHERE vendor_id = $1 AND job_type = 'knowledge_import'
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
                    success_records,
                    skipped_records,
                    failed_records,
                    created_at,
                    completed_at
                FROM unified_jobs
                WHERE job_type = 'knowledge_import'
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)

        # 取得總數
        if vendor_id:
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM unified_jobs
                WHERE vendor_id = $1 AND job_type = 'knowledge_import'
            """, vendor_id)
        else:
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM unified_jobs WHERE job_type = 'knowledge_import'
            """)

        return {
            "jobs": [
                {
                    "job_id": str(job['job_id']),
                    "vendor_id": job['vendor_id'],
                    "file_name": job['file_name'],
                    "status": job['status'],
                    "imported_count": job['success_records'],
                    "skipped_count": job['skipped_records'],
                    "error_count": job['failed_records'],
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
        Dict: 預覽資訊（包含來源類型偵測）
    """
    # 驗證檔案類型
    allowed_extensions = ['.xlsx', '.xls', '.csv', '.txt', '.json']
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

    # 初始化來源偵測變數
    source_type = "external_file"
    import_source = "external_unknown"
    detected_source_description = "外部檔案"

    if file_ext in ['.xlsx', '.xls']:
        # Excel 預覽
        import pandas as pd
        import io

        # 先讀取第一行，檢查是否有業者標籤（租管業 QA 格式）
        df_first_row = pd.read_excel(io.BytesIO(content), engine='openpyxl', header=None, nrows=1)

        has_vendor_label = False
        vendor_label = None
        if pd.notna(df_first_row.iloc[0, 0]) and '物業' in str(df_first_row.iloc[0, 0]):
            has_vendor_label = True
            if pd.notna(df_first_row.iloc[0, 1]):
                vendor_label = str(df_first_row.iloc[0, 1]).strip()

        # 根據格式選擇 header 行
        if has_vendor_label:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl', header=1)  # 第 2 行作為標題
            detected_source_description = f"租管業 QA 格式（業者: {vendor_label}）"
        else:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')  # 第 1 行作為標題

            # 來源偵測：檢查是否為系統匯出檔案
            expected_fields = {
                'question_summary', 'answer', 'scope', 'vendor_id',
                'business_types', 'target_user', 'intent_names',
                'keywords', 'priority'
            }
            actual_fields = set(df.columns)

            if expected_fields.issubset(actual_fields):
                # 系統匯出檔案
                source_type = "external_file"
                import_source = "system_export"
                detected_source_description = "系統匯出檔案（可直接匯入）"
            else:
                # 一般 Excel 檔案
                source_type = "external_file"
                import_source = "external_excel"
                detected_source_description = "外部 Excel 檔案"

        # 將 NaN 轉換為空字串，避免 JSON 序列化錯誤
        preview_df = df.head(5).fillna('')  # 用空字串取代 NaN

        preview_data = {
            "file_type": "excel",
            "total_rows": len(df),
            "columns": list(df.columns),
            "preview_rows": preview_df.to_dict(orient='records'),
            "estimated_knowledge": len(df),  # 粗略估算
            "vendor_label": vendor_label  # 新增：業者標籤
        }

    elif file_ext == '.csv':
        # CSV 預覽
        import pandas as pd
        import io

        try:
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig')

        # 將 NaN 轉換為空字串，避免 JSON 序列化錯誤
        preview_df = df.head(5).fillna('')

        preview_data = {
            "file_type": "csv",
            "total_rows": len(df),
            "columns": list(df.columns),
            "preview_rows": preview_df.to_dict(orient='records'),
            "estimated_knowledge": len(df)  # 粗略估算
        }

    elif file_ext == '.txt':
        # 純文字預覽
        content_str = content.decode('utf-8', errors='ignore')
        lines = content_str.split('\n')

        # 來源偵測：檢查檔名是否包含對話關鍵字
        filename_lower = file.filename.lower()
        if 'chat' in filename_lower or 'conversation' in filename_lower or '對話' in filename_lower or '聊天' in filename_lower:
            source_type = "line_chat"
            import_source = "line_chat_txt"
            detected_source_description = "對話記錄（將創建測試情境）"
        else:
            source_type = "external_file"
            import_source = "external_txt"
            detected_source_description = "純文字檔案"

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

        # 來源偵測：JSON 檔案預設為外部檔案
        source_type = "external_file"
        import_source = "external_json"
        detected_source_description = "外部 JSON 檔案"

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
        "source_type": source_type,
        "import_source": import_source,
        "detected_source_description": detected_source_description,
        "message": "這是預覽模式，尚未消耗任何 OpenAI token"
    }


@router.post("/jobs/{job_id}/confirm")
async def confirm_test_scenarios(
    job_id: str,
    request: Request,
    body: dict
):
    """
    確認創建選中的測試情境（對話記錄匯入專用）

    Args:
        job_id: 任務 ID
        body: 包含 selected_indices（用戶選中的測試情境索引列表）

    Returns:
        Dict: 創建結果
    """
    db_pool = request.app.state.db_pool
    selected_indices = body.get('selected_indices', [])

    if not selected_indices:
        raise HTTPException(status_code=400, detail="請至少選擇一個測試情境")

    # 獲取任務信息
    async with db_pool.acquire() as conn:
        job = await conn.fetchrow("""
            SELECT job_id, status, job_result, file_name, user_id
            FROM unified_jobs
            WHERE job_id = $1
        """, uuid.UUID(job_id))

        if not job:
            raise HTTPException(status_code=404, detail="任務不存在")

        if job['status'] != 'awaiting_confirmation':
            raise HTTPException(
                status_code=400,
                detail=f"任務狀態必須為 awaiting_confirmation（當前: {job['status']}）"
            )

    # 從 job_result 中獲取 scenarios
    import json
    result = job['job_result']
    if isinstance(result, str):
        result = json.loads(result)
    scenarios = result.get('scenarios', [])

    if not scenarios:
        raise HTTPException(status_code=400, detail="任務中沒有測試情境數據")

    # 創建選中的測試情境
    from services.knowledge_import_service import KnowledgeImportService
    service = KnowledgeImportService(db_pool)

    creation_result = await service._create_selected_scenarios(
        scenarios=scenarios,
        selected_indices=selected_indices,
        created_by=job['user_id']
    )

    # 更新任務狀態為完成
    await service.update_status(
        job_id=job_id,
        status="completed",
        progress={"current": 100, "total": 100},
        result=creation_result,
        success_records=creation_result.get('created', 0),
        skipped_records=creation_result.get('skipped', 0),
        failed_records=creation_result.get('errors', 0)
    )

    return {
        "message": "測試情境創建完成",
        "job_id": job_id,
        **creation_result
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
            DELETE FROM unified_jobs
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
        # ⛔ 原本呼叫 `get_import_statistics($1,$2)`——該函式**從未被任何 migration 建立**
        #    （`grep -rl` 於 database/ 零命中）⇒ 本端點一直回 500。改為直接聚合 unified_jobs。
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*)                                            AS total_jobs,
                COUNT(*) FILTER (WHERE status = 'completed')        AS completed_jobs,
                COUNT(*) FILTER (WHERE status = 'failed')           AS failed_jobs,
                COUNT(*) FILTER (WHERE status = 'processing')       AS processing_jobs,
                COALESCE(SUM(success_records), 0)                   AS total_imported,
                COALESCE(SUM(skipped_records), 0)                   AS total_skipped,
                COALESCE(SUM(failed_records), 0)                    AS total_errors,
                COALESCE(AVG(success_records) FILTER (WHERE status = 'completed'), 0)
                                                                    AS avg_imported_per_job,
                CASE WHEN COUNT(*) = 0 THEN 0
                     ELSE COUNT(*) FILTER (WHERE status = 'completed')::numeric
                          / COUNT(*)::numeric * 100 END             AS success_rate
            FROM unified_jobs
            WHERE job_type = 'knowledge_import'
              AND ($1::int IS NULL OR vendor_id = $1)
              AND created_at >= NOW() - ($2 || ' days')::interval
        """, vendor_id, str(days))

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
