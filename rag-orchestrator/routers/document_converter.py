"""
文件轉換 API 路由

提供規格書轉知識庫的 RESTful API
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
import shutil
from pathlib import Path

from services.document_converter_service import DocumentConverterService

router = APIRouter(prefix="/api/v1/document-converter", tags=["document-converter"])

# 全局服務實例（db_pool 會在每次請求時動態設定）
converter_service = DocumentConverterService()


def _get_service(request: Request) -> DocumentConverterService:
    """
    獲取帶有 db_pool 的服務實例

    Args:
        request: FastAPI Request 對象

    Returns:
        配置好的 DocumentConverterService
    """
    # 動態設定 db_pool（如果尚未設定）
    if converter_service.db_pool is None and hasattr(request.app.state, 'db_pool'):
        converter_service.db_pool = request.app.state.db_pool
    return converter_service


# ==================== 請求/響應模型 ====================

class QAItem(BaseModel):
    """Q&A 項目"""
    question_summary: str
    content: str
    keywords: List[str]
    selected_intent_id: Optional[int] = None
    recommended_intent: Optional[Dict] = None


class QAListUpdate(BaseModel):
    """Q&A 列表更新"""
    qa_list: List[QAItem]


class ConvertRequest(BaseModel):
    """轉換請求"""
    custom_prompt: Optional[str] = None


# ==================== API 端點 ====================

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
):
    """
    上傳規格書文件

    支援格式：.docx, .pdf
    文件大小限制：50MB

    Returns:
        {
            "job_id": "uuid",
            "status": "uploaded",
            "file_name": "example.docx",
            "file_size": 1024000,
            "file_type": "docx",
            "created_at": "2025-11-18T10:00:00"
        }
    """
    try:
        # 獲取服務實例（會自動設置 db_pool）
        service = _get_service(request)

        # 驗證文件格式
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.docx', '.pdf']:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的檔案格式: {file_ext}。僅支援 .docx 和 .pdf"
            )

        # 保存上傳文件到臨時位置
        temp_file = Path(f"/tmp/{file.filename}")
        with temp_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 使用服務處理
        result = await service.upload_document(
            file_path=str(temp_file),
            original_filename=file.filename
        )

        return JSONResponse(content=result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 上傳失敗: {e}")
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")


@router.post("/{job_id}/parse")
async def parse_document(request: Request, job_id: str):
    """
    解析文件內容

    Args:
        job_id: 任務 ID

    Returns:
        {
            "job_id": "uuid",
            "status": "parsed",
            "content": "文件純文字內容...",
            "updated_at": "2025-11-18T10:01:00"
        }
    """
    try:
        service = _get_service(request)
        result = await service.parse_document(job_id)
        return JSONResponse(content=result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 解析失敗: {e}")
        raise HTTPException(status_code=500, detail=f"解析失敗: {str(e)}")


@router.post("/{job_id}/convert")
async def convert_to_qa(job_id: str, convert_request: ConvertRequest, request: Request):
    """
    將文件內容轉換為 Q&A

    使用 AI 自動提取問題和答案

    Args:
        job_id: 任務 ID
        convert_request: 轉換請求（可包含自訂 prompt）
        request: FastAPI Request 對象

    Returns:
        {
            "job_id": "uuid",
            "status": "completed",
            "qa_list": [
                {
                    "question_summary": "如何使用?",
                    "content": "使用方法...",
                    "keywords": ["使用", "方法"],
                    "recommended_intent": {
                        "intent_id": 1,
                        "intent_name": "帳務查詢",
                        "confidence": 0.85,
                        "reasoning": "此問題涉及租金繳費查詢"
                    }
                }
            ],
            "updated_at": "2025-11-18T10:05:00"
        }
    """
    try:
        service = _get_service(request)
        result = await service.convert_to_qa(
            job_id=job_id,
            custom_prompt=convert_request.custom_prompt
        )
        return JSONResponse(content=result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 轉換失敗: {e}")
        raise HTTPException(status_code=500, detail=f"轉換失敗: {str(e)}")


@router.get("/{job_id}")
async def get_job_status(request: Request, job_id: str):
    """
    獲取任務狀態和結果

    Args:
        job_id: 任務 ID

    Returns:
        完整的任務資訊
    """
    service = _get_service(request)
    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"任務不存在: {job_id}")

    return JSONResponse(content=job)


@router.put("/{job_id}/qa-list")
async def update_qa_list(request: Request, job_id: str, update: QAListUpdate):
    """
    更新 Q&A 列表（人工編輯後）

    Args:
        job_id: 任務 ID
        update: 更新的 Q&A 列表

    Returns:
        更新後的任務資訊
    """
    try:
        service = _get_service(request)
        # 轉換 Pydantic 模型為字典
        qa_list = [qa.model_dump() for qa in update.qa_list]

        result = await service.update_qa_list(
            job_id=job_id,
            qa_list=qa_list
        )

        return JSONResponse(content=result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 更新失敗: {e}")
        raise HTTPException(status_code=500, detail=f"更新失敗: {str(e)}")


@router.post("/{job_id}/estimate-cost")
async def estimate_conversion_cost(job_id: str):
    """
    估算轉換成本

    Args:
        job_id: 任務 ID

    Returns:
        {
            "content_length": 10000,
            "estimated_input_tokens": 15000,
            "estimated_output_tokens": 7500,
            "estimated_cost_usd": 1.23,
            "model": "gpt-4"
        }
    """
    job = await converter_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"任務不存在: {job_id}")

    if not job.get('content'):
        raise HTTPException(status_code=400, detail="文件尚未解析，無法估算成本")

    estimate = await converter_service.estimate_cost(len(job['content']))

    return JSONResponse(content=estimate)


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """
    刪除任務並清理文件

    Args:
        job_id: 任務 ID

    Returns:
        {"message": "任務已刪除"}
    """
    try:
        await converter_service.cleanup_job(job_id)
        return JSONResponse(content={"message": "任務已刪除", "job_id": job_id})

    except Exception as e:
        print(f"❌ 刪除失敗: {e}")
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")


@router.post("/{job_id}/export-csv")
async def export_to_csv(job_id: str):
    """
    匯出為 CSV 格式

    Args:
        job_id: 任務 ID

    Returns:
        CSV 格式的文本
    """
    job = await converter_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"任務不存在: {job_id}")

    if not job.get('qa_list'):
        raise HTTPException(status_code=400, detail="尚無 Q&A 列表")

    # 生成 CSV（包含意圖資訊）
    csv_lines = ["question_summary,content,keywords,intent_id"]

    for qa in job['qa_list']:
        question = qa['question_summary'].replace(',', '，')  # 替換逗號避免CSV錯誤
        content = qa['content'].replace(',', '，')  # 保留換行符以維持排版
        keywords = ','.join(qa['keywords'])
        # 使用 selected_intent_id（使用者選擇的）或 recommended_intent 中的 intent_id
        intent_id = qa.get('selected_intent_id') or qa.get('recommended_intent', {}).get('intent_id') or ''

        csv_lines.append(f'"{question}","{content}","{keywords}","{intent_id}"')

    csv_content = '\n'.join(csv_lines)

    return JSONResponse(content={
        "csv_content": csv_content,
        "filename": f"{job['file_name']}_qa.csv"
    })
