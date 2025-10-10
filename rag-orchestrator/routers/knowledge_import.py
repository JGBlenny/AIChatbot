"""
知識庫匯入 API
支援上傳 LINE 聊天記錄 txt 文件，自動提取知識庫並去重
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import tempfile
import os
import hashlib
from datetime import datetime

router = APIRouter(prefix="/api/v1/knowledge-import", tags=["Knowledge Import"])


class ImportJobStatus(BaseModel):
    """匯入任務狀態"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0-100
    total_messages: int
    processed_messages: int
    extracted_qa_pairs: int
    duplicates_skipped: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ImportOptions(BaseModel):
    """匯入選項"""
    mode: str = "new"  # new（新增） or optimize（優化現有）
    batch_size: int = 50
    enable_deduplication: bool = True
    vendor_id: Optional[int] = None


# 全域任務存儲（實際應使用 Redis 或資料庫）
import_jobs: Dict[str, Dict] = {}


def calculate_content_hash(content: str) -> str:
    """計算內容雜湊值（用於去重）"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def check_duplicate_knowledge(question_summary: str, answer: str) -> bool:
    """
    檢查知識是否已存在

    Returns:
        True if duplicate, False if new
    """
    # TODO: 實作資料庫查詢
    # 使用問題摘要和答案的相似度檢查
    # 可以使用向量相似度或模糊匹配

    from services.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    # 簡單的精確匹配檢查
    cursor.execute("""
        SELECT COUNT(*) FROM knowledge_base
        WHERE question_summary = %s
        LIMIT 1
    """, (question_summary,))

    result = cursor.fetchone()
    cursor.close()
    conn.close()

    return result[0] > 0 if result else False


async def process_import_job(
    job_id: str,
    file_path: str,
    options: ImportOptions
):
    """處理匯入任務（背景任務）"""

    try:
        # 更新狀態為處理中
        import_jobs[job_id]['status'] = 'processing'
        import_jobs[job_id]['updated_at'] = datetime.now()

        # 讀取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 簡單解析（實際應使用完整的解析器）
        lines = content.split('\n')
        total_lines = len(lines)

        import_jobs[job_id]['total_messages'] = total_lines

        # TODO: 整合 extract_knowledge_and_tests.py 的邏輯
        # 這裡簡化為模擬處理

        extracted_count = 0
        duplicates_count = 0

        for i, line in enumerate(lines):
            # 更新進度
            progress = (i + 1) / total_lines * 100
            import_jobs[job_id]['progress'] = progress
            import_jobs[job_id]['processed_messages'] = i + 1

            # 模擬處理邏輯
            # 實際應呼叫 LLM 提取問答對

            import time
            time.sleep(0.01)  # 模擬處理時間

        # 完成
        import_jobs[job_id]['status'] = 'completed'
        import_jobs[job_id]['progress'] = 100
        import_jobs[job_id]['extracted_qa_pairs'] = extracted_count
        import_jobs[job_id]['duplicates_skipped'] = duplicates_count
        import_jobs[job_id]['updated_at'] = datetime.now()

    except Exception as e:
        import_jobs[job_id]['status'] = 'failed'
        import_jobs[job_id]['error_message'] = str(e)
        import_jobs[job_id]['updated_at'] = datetime.now()

    finally:
        # 清理臨時文件
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/upload", response_model=ImportJobStatus)
async def upload_chat_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = "new",
    enable_deduplication: bool = True,
    vendor_id: Optional[int] = None
):
    """
    上傳 LINE 聊天記錄文件並開始匯入

    Args:
        file: txt 文件
        mode: new（新增）或 optimize（優化）
        enable_deduplication: 是否啟用去重
        vendor_id: 業者 ID（可選）

    Returns:
        ImportJobStatus: 匯入任務狀態
    """

    # 驗證文件類型
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="只支援 .txt 文件")

    # 生成任務 ID
    job_id = hashlib.md5(f"{file.filename}{datetime.now()}".encode()).hexdigest()

    # 儲存臨時文件
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, f"{job_id}_{file.filename}")

    with open(temp_file_path, 'wb') as f:
        content = await file.read()
        f.write(content)

    # 建立任務記錄
    import_jobs[job_id] = {
        'job_id': job_id,
        'status': 'pending',
        'progress': 0.0,
        'total_messages': 0,
        'processed_messages': 0,
        'extracted_qa_pairs': 0,
        'duplicates_skipped': 0,
        'error_message': None,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'filename': file.filename,
        'mode': mode,
        'enable_deduplication': enable_deduplication,
        'vendor_id': vendor_id
    }

    # 啟動背景任務
    options = ImportOptions(
        mode=mode,
        enable_deduplication=enable_deduplication,
        vendor_id=vendor_id
    )

    background_tasks.add_task(
        process_import_job,
        job_id,
        temp_file_path,
        options
    )

    return ImportJobStatus(**import_jobs[job_id])


@router.get("/jobs/{job_id}", response_model=ImportJobStatus)
async def get_import_job_status(job_id: str):
    """
    獲取匯入任務狀態

    Args:
        job_id: 任務 ID

    Returns:
        ImportJobStatus: 任務狀態
    """

    if job_id not in import_jobs:
        raise HTTPException(status_code=404, detail="任務不存在")

    return ImportJobStatus(**import_jobs[job_id])


@router.get("/jobs", response_model=List[ImportJobStatus])
async def list_import_jobs(limit: int = 20):
    """
    列出所有匯入任務

    Args:
        limit: 返回數量限制

    Returns:
        List[ImportJobStatus]: 任務列表
    """

    jobs = sorted(
        import_jobs.values(),
        key=lambda x: x['created_at'],
        reverse=True
    )

    return [ImportJobStatus(**job) for job in jobs[:limit]]


@router.post("/preview")
async def preview_chat_file(file: UploadFile = File(...)):
    """
    預覽 txt 文件內容（不呼叫 LLM，不消耗 token）

    Args:
        file: txt 文件

    Returns:
        Dict: 預覽資訊
    """

    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="只支援 .txt 文件")

    content = await file.read()
    content_str = content.decode('utf-8')

    # 簡單統計
    lines = content_str.split('\n')
    total_lines = len(lines)

    # 計算文件雜湊
    file_hash = hashlib.md5(content).hexdigest()

    # 提取前 20 行作為預覽
    preview_lines = lines[:20]

    # 簡單估算可能的問答對數量（不呼叫 LLM）
    estimated_qa_pairs = total_lines // 10  # 粗略估算

    return {
        "filename": file.filename,
        "file_hash": file_hash,
        "total_lines": total_lines,
        "estimated_qa_pairs": estimated_qa_pairs,
        "preview_lines": preview_lines,
        "file_size_kb": len(content) / 1024,
        "message": "這是預覽模式，尚未消耗任何 token"
    }


@router.delete("/jobs/{job_id}")
async def delete_import_job(job_id: str):
    """
    刪除匯入任務記錄

    Args:
        job_id: 任務 ID

    Returns:
        Dict: 刪除結果
    """

    if job_id not in import_jobs:
        raise HTTPException(status_code=404, detail="任務不存在")

    del import_jobs[job_id]

    return {"message": "任務已刪除", "job_id": job_id}
