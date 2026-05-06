"""
圖片上傳 API

提供修繕報修圖片上傳功能，整合 S3ImageService 進行圖片儲存
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/images", tags=["Images"])


class ImageUploadResponse(BaseModel):
    image_id: Optional[int] = None
    image_url: str
    s3_key: str
    file_size: int
    width: int
    height: int


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    vendor_id: int = Form(...),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
):
    """
    上傳圖片至 S3

    - 格式限制：JPEG, PNG, WebP
    - 大小限制：10MB
    - 自動壓縮至 max 1024px
    - 回傳 presigned URL（7 天有效）
    """
    from services.s3_image_service import get_s3_image_service

    # 讀取檔案內容
    file_content = await file.read()

    if not file_content:
        raise HTTPException(status_code=400, detail="未收到圖片檔案")

    try:
        s3_service = get_s3_image_service()
        db_pool = getattr(request.app.state, "db_pool", None)

        result = await s3_service.upload_image(
            file_content=file_content,
            vendor_id=vendor_id,
            filename=file.filename or "unknown.jpg",
            content_type=file.content_type or "application/octet-stream",
            session_id=session_id,
            user_id=user_id,
            db_pool=db_pool,
        )

        return ImageUploadResponse(
            image_id=result["image_id"],
            image_url=result["s3_url"],
            s3_key=result["s3_key"],
            file_size=result["file_size"],
            width=result["width"],
            height=result["height"],
        )

    except ValueError as e:
        # 格式/大小驗證錯誤
        error_msg = str(e)
        if "10MB" in error_msg:
            raise HTTPException(status_code=413, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    except Exception as e:
        logger.error(f"圖片上傳失敗: {e}")
        raise HTTPException(status_code=500, detail="圖片上傳失敗，請重試")
