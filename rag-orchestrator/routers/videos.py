"""
影片管理 API

提供影片上傳、刪除、查詢等功能
整合 S3VideoService 進行影片儲存
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from services.s3_video_service import get_s3_video_service
from typing import Optional
from io import BytesIO
import psycopg2
import os

router = APIRouter(prefix="/api/v1/videos", tags=["Videos"])


def get_db_connection():
    """建立資料庫連接"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER', 'aichatbot'),
        password=os.getenv('DB_PASSWORD', 'aichatbot_password'),
        database=os.getenv('DB_NAME', 'aichatbot_admin')
    )


@router.post("/upload")
async def upload_video(
    knowledge_id: int = Form(...),
    file: UploadFile = File(...)
):
    """
    上傳影片到 S3 並更新知識庫

    Args:
        knowledge_id: 知識 ID
        file: 影片檔案（最大 500MB）

    Returns:
        {
            "success": true,
            "message": "影片上傳成功",
            "data": {
                "s3_key": "...",
                "url": "...",
                "size": 1024000,
                "format": "mp4"
            }
        }
    """
    # 檔案大小限制（500MB）
    MAX_SIZE = 500 * 1024 * 1024

    # 檢查檔案類型
    allowed_types = ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的影片格式。允許：MP4, WebM, MOV"
        )

    # 讀取檔案
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"檔案過大（最大 500MB，目前 {len(contents)/(1024*1024):.1f}MB）"
        )

    print(f"📤 收到影片上傳請求:")
    print(f"   知識 ID: {knowledge_id}")
    print(f"   檔案名: {file.filename}")
    print(f"   大小: {len(contents)/(1024*1024):.2f} MB")

    try:
        # 上傳到 S3
        s3_service = get_s3_video_service()
        result = s3_service.upload_video(
            file=BytesIO(contents),
            knowledge_id=knowledge_id,
            filename=file.filename,
            content_type=file.content_type
        )

        # 更新資料庫
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE knowledge_base
            SET
                video_s3_key = %s,
                video_url = %s,
                video_file_size = %s,
                video_format = %s,
                video_uploaded_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (
            result['s3_key'],
            result['url'],
            result['size'],
            result['format'],
            knowledge_id
        ))

        affected_rows = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        if affected_rows == 0:
            raise HTTPException(
                status_code=404,
                detail="知識不存在或無權限修改"
            )

        print(f"✅ 資料庫已更新（知識 ID: {knowledge_id}）")

        return {
            "success": True,
            "message": "影片上傳成功",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 上傳失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上傳失敗: {str(e)}")


@router.delete("/{knowledge_id}")
async def delete_video(knowledge_id: int):
    """
    刪除知識庫中的影片

    Args:
        knowledge_id: 知識 ID

    Returns:
        {"success": true, "message": "影片已刪除"}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查詢影片資訊
        cursor.execute("""
            SELECT video_s3_key, video_url
            FROM knowledge_base
            WHERE id = %s
        """, (knowledge_id,))

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="知識不存在或無權限")

        video_s3_key, video_url = row

        if not video_s3_key:
            raise HTTPException(status_code=404, detail="此知識沒有關聯的影片")

        print(f"🗑️  刪除影片:")
        print(f"   知識 ID: {knowledge_id}")
        print(f"   S3 Key: {video_s3_key}")

        # 從 S3 刪除
        s3_service = get_s3_video_service()
        s3_service.delete_video(video_s3_key)

        # 更新資料庫（清除影片欄位）
        cursor.execute("""
            UPDATE knowledge_base
            SET
                video_s3_key = NULL,
                video_url = NULL,
                video_thumbnail_s3_key = NULL,
                video_thumbnail_url = NULL,
                video_duration = NULL,
                video_file_size = NULL,
                video_format = NULL,
                video_uploaded_at = NULL,
                updated_at = NOW()
            WHERE id = %s
        """, (knowledge_id,))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ 影片已刪除（知識 ID: {knowledge_id}）")

        return {
            "success": True,
            "message": "影片已刪除"
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        print(f"❌ 刪除失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")


@router.get("/{knowledge_id}/info")
async def get_video_info(knowledge_id: int):
    """
    獲取知識庫影片資訊

    Returns:
        {
            "has_video": true,
            "url": "...",
            "size": 1024000,
            "format": "mp4",
            "duration": 120,
            "uploaded_at": "2024-01-01T12:00:00"
        }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            video_s3_key,
            video_url,
            video_file_size,
            video_format,
            video_duration,
            video_uploaded_at
        FROM knowledge_base
        WHERE id = %s
    """, (knowledge_id,))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="知識不存在")

    video_s3_key, video_url, file_size, format, duration, uploaded_at = row

    return {
        "has_video": video_s3_key is not None,
        "url": video_url,
        "size": file_size,
        "format": format,
        "duration": duration,
        "uploaded_at": uploaded_at.isoformat() if uploaded_at else None
    }


@router.get("/health")
async def health_check():
    """檢查 S3 服務狀態"""
    try:
        s3_service = get_s3_video_service()
        bucket_exists = s3_service.check_bucket_exists()

        return {
            "status": "healthy" if bucket_exists else "unhealthy",
            "bucket": s3_service.bucket_name,
            "region": s3_service.aws_region,
            "cdn_enabled": s3_service.cloudfront_domain is not None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
