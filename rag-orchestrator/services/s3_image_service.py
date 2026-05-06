"""
S3 圖片儲存服務

提供圖片壓縮、上傳、presigned URL 生成、格式驗證等功能
支援 AWS S3，用於修繕報修圖片上傳
"""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Dict
from io import BytesIO
import os
import uuid
import logging
from datetime import datetime

from PIL import Image

logger = logging.getLogger(__name__)

# 允許的圖片格式與對應 MIME type
ALLOWED_FORMATS = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

# Magic bytes 用於驗證真實檔案格式
MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpeg",       # JPEG
    b"\x89PNG": "png",              # PNG
    b"RIFF": "webp",               # WebP (RIFF....WEBP)
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class S3ImageService:
    """AWS S3 圖片服務 — 壓縮、上傳、presigned URL"""

    def __init__(self):
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "ap-northeast-1")
        self.bucket_name = os.getenv("S3_BUCKET_NAME")

        self.max_dimension = int(os.getenv("IMAGE_MAX_DIMENSION", "1024"))
        self.compress_quality = int(os.getenv("IMAGE_COMPRESS_QUALITY", "85"))

        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME 環境變數未設置")

        try:
            if self.aws_access_key and self.aws_secret_key:
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region,
                )
            else:
                self.s3_client = boto3.client("s3", region_name=self.aws_region)

            logger.info(f"S3ImageService 已初始化 | bucket={self.bucket_name}")
        except NoCredentialsError:
            raise ValueError("AWS 憑證未找到，請設定 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY")

    # ------------------------------------------------------------------
    # 格式驗證
    # ------------------------------------------------------------------

    @staticmethod
    def validate_format(file_content: bytes, content_type: str) -> str:
        """
        驗證圖片格式（MIME type + magic bytes）。

        Returns:
            正規化的格式名稱（jpeg / png / webp）

        Raises:
            ValueError: 格式不支援或 magic bytes 不符
        """
        # 1) MIME type 檢查
        mime_lower = content_type.lower()
        matched_format = None
        for fmt, mime in ALLOWED_FORMATS.items():
            if mime == mime_lower:
                matched_format = fmt if fmt != "jpg" else "jpeg"
                break
        if matched_format is None:
            raise ValueError(f"不支援的圖片格式，請上傳 JPEG、PNG 或 WebP")

        # 2) Magic bytes 檢查
        header = file_content[:12]
        magic_matched = False
        for magic, fmt in MAGIC_BYTES.items():
            if header.startswith(magic):
                # WebP 需額外檢查 RIFF....WEBP
                if fmt == "webp" and header[8:12] != b"WEBP":
                    continue
                magic_matched = True
                if fmt != matched_format:
                    raise ValueError("圖片內容與宣告的格式不符")
                break

        if not magic_matched:
            raise ValueError("無法辨識的圖片格式，請上傳 JPEG、PNG 或 WebP")

        return matched_format

    # ------------------------------------------------------------------
    # 圖片壓縮
    # ------------------------------------------------------------------

    def compress_image(
        self,
        file_content: bytes,
        max_dimension: int = None,
        quality: int = None,
    ) -> tuple[bytes, int, int, str]:
        """
        壓縮圖片至指定最大邊長。

        Args:
            file_content: 原始圖片 bytes
            max_dimension: 最大邊長（短邊不超過此值），預設從環境變數
            quality: JPEG/WebP 壓縮品質，預設從環境變數

        Returns:
            (compressed_bytes, width, height, format)
        """
        max_dim = max_dimension or self.max_dimension
        qual = quality or self.compress_quality

        img = Image.open(BytesIO(file_content))
        original_format = img.format  # JPEG / PNG / WEBP

        # EXIF 旋轉修正
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # 縮放：讓最長邊不超過 max_dim
        w, h = img.size
        if max(w, h) > max_dim:
            ratio = max_dim / max(w, h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        w, h = img.size

        # 輸出格式保持與原始相同
        out_format = original_format or "JPEG"
        buf = BytesIO()
        save_kwargs: dict = {}

        if out_format.upper() in ("JPEG", "JPG"):
            out_format = "JPEG"
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            save_kwargs["quality"] = qual
            save_kwargs["optimize"] = True
        elif out_format.upper() == "WEBP":
            save_kwargs["quality"] = qual
        # PNG 使用無損壓縮，不設 quality

        img.save(buf, format=out_format, **save_kwargs)
        compressed = buf.getvalue()

        fmt_lower = out_format.lower()
        if fmt_lower == "jpeg":
            fmt_lower = "jpeg"

        return compressed, w, h, fmt_lower

    # ------------------------------------------------------------------
    # 上傳
    # ------------------------------------------------------------------

    async def upload_image(
        self,
        file_content: bytes,
        vendor_id: int,
        filename: str,
        content_type: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db_pool=None,
    ) -> Dict:
        """
        驗證 → 壓縮 → 上傳 S3 → 寫入 DB → 回傳結果。

        Returns:
            {image_id, s3_key, s3_url, file_size, width, height}
        """
        original_size = len(file_content)

        # 大小限制
        if original_size > MAX_FILE_SIZE:
            raise ValueError(f"圖片大小超過 10MB 限制")

        # 格式驗證
        image_format = self.validate_format(file_content, content_type)

        # 壓縮
        compressed, width, height, fmt = self.compress_image(file_content)
        file_size = len(compressed)

        # S3 路徑: images/{vendor_id}/{year}/{month}/{uuid}.{ext}
        now = datetime.now()
        ext = "jpg" if fmt == "jpeg" else fmt
        s3_key = f"images/{vendor_id}/{now.year}/{now.month:02d}/{uuid.uuid4().hex}.{ext}"

        # 上傳 S3
        try:
            upload_mime = ALLOWED_FORMATS.get(fmt, "application/octet-stream")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed,
                ContentType=upload_mime,
                ACL="private",
            )
        except ClientError as e:
            logger.error(f"S3 圖片上傳失敗: {e}")
            raise Exception("圖片上傳失敗，請重試")

        # 產生 presigned URL
        s3_url = self.generate_presigned_url(s3_key)

        # 寫入 DB
        image_id = None
        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    image_id = await conn.fetchval(
                        """
                        INSERT INTO image_uploads
                            (vendor_id, session_id, user_id, s3_key, s3_url,
                             file_size, original_size, image_format, width, height)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        RETURNING id
                        """,
                        vendor_id, session_id, user_id, s3_key, s3_url,
                        file_size, original_size, image_format, width, height,
                    )
            except Exception as e:
                logger.error(f"image_uploads 寫入失敗: {e}")
                # DB 失敗不阻塞，圖片已上傳 S3

        logger.info(
            f"圖片上傳完成 | vendor={vendor_id} key={s3_key} "
            f"size={file_size} dim={width}x{height}"
        )

        return {
            "image_id": image_id,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "file_size": file_size,
            "width": width,
            "height": height,
        }

    # ------------------------------------------------------------------
    # Presigned URL
    # ------------------------------------------------------------------

    def generate_presigned_url(self, s3_key: str, expiration: int = 604800) -> str:
        """
        產生 S3 presigned URL。

        Args:
            s3_key: S3 物件鍵
            expiration: 有效秒數，預設 7 天 (604800)
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"產生 presigned URL 失敗: {e}")
            raise Exception("產生圖片存取 URL 失敗")


# ------------------------------------------------------------------
# 單例
# ------------------------------------------------------------------

_s3_image_service_instance = None


def get_s3_image_service() -> S3ImageService:
    """取得 S3ImageService 單例"""
    global _s3_image_service_instance
    if _s3_image_service_instance is None:
        _s3_image_service_instance = S3ImageService()
    return _s3_image_service_instance
