"""
S3 影片儲存服務

提供影片上傳、刪除、URL 生成等功能
支援 AWS S3 + CloudFront CDN
"""
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, BinaryIO, Dict
import os
from datetime import datetime
from io import BytesIO


class S3VideoService:
    """AWS S3 影片服務"""

    def __init__(self):
        """
        初始化 S3 客戶端

        環境變數：
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_REGION
        - S3_BUCKET_NAME
        - CLOUDFRONT_DOMAIN (可選)
        """
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'ap-northeast-1')
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN')

        # 驗證必要參數
        if not self.bucket_name:
            raise ValueError("❌ S3_BUCKET_NAME 環境變數未設置")

        # 建立 S3 客戶端
        try:
            if self.aws_access_key and self.aws_secret_key:
                # 使用 Access Key/Secret Key
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                print(f"✅ S3 客戶端已初始化（使用 Access Key）")
            else:
                # 使用 IAM Role（適用於 EC2/ECS）
                self.s3_client = boto3.client('s3', region_name=self.aws_region)
                print(f"✅ S3 客戶端已初始化（使用 IAM Role）")

            print(f"   Bucket: {self.bucket_name}")
            print(f"   Region: {self.aws_region}")
            if self.cloudfront_domain:
                print(f"   CDN: https://{self.cloudfront_domain}")

        except NoCredentialsError:
            raise ValueError("❌ AWS 憑證未找到。請設定 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY")

    def upload_video(
        self,
        file: BinaryIO,
        knowledge_id: int,
        filename: str,
        content_type: str = 'video/mp4'
    ) -> Dict[str, any]:
        """
        上傳影片到 S3

        Args:
            file: 影片檔案（BinaryIO）
            knowledge_id: 知識 ID
            filename: 原始檔名
            content_type: MIME 類型

        Returns:
            {
                's3_key': 'aichatbot/videos/kb-123_20240101_120000.mp4',
                'url': 'https://xxx.cloudfront.net/aichatbot/videos/kb-123_20240101_120000.mp4',
                'size': 1024000,
                'format': 'mp4'
            }
        """
        # 生成唯一的 S3 鍵（檔案路徑）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = filename.split('.')[-1].lower()
        s3_key = f"aichatbot/videos/kb-{knowledge_id}_{timestamp}.{file_ext}"

        try:
            # 獲取檔案大小
            file.seek(0, 2)  # 移到檔案結尾
            file_size = file.tell()
            file.seek(0)     # 重置到開頭

            print(f"📤 開始上傳影片: {s3_key}")
            print(f"   檔案大小: {file_size / (1024*1024):.2f} MB")

            # 上傳到 S3
            # 注意：S3 Metadata 只支援 ASCII 字符，中文檔名需要 URL encode
            import urllib.parse
            safe_filename = urllib.parse.quote(filename)

            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read',  # 設定檔案為公開讀取
                    'CacheControl': 'max-age=31536000',  # 快取 1 年
                    'Metadata': {
                        'knowledge_id': str(knowledge_id),
                        'uploaded_at': datetime.now().isoformat(),
                        'original_filename': safe_filename  # URL encoded
                    }
                }
            )

            # 生成公開 URL
            if self.cloudfront_domain:
                # 使用 CloudFront URL（推薦）
                url = f"https://{self.cloudfront_domain}/{s3_key}"
            else:
                # 使用 S3 直接 URL
                url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"

            print(f"✅ 影片上傳成功！")
            print(f"   URL: {url}")

            return {
                's3_key': s3_key,
                'url': url,
                'size': file_size,
                'format': file_ext
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            print(f"❌ S3 上傳失敗: [{error_code}] {error_msg}")
            raise Exception(f"S3 上傳失敗: {error_msg}")
        except Exception as e:
            print(f"❌ 上傳過程發生錯誤: {str(e)}")
            raise

    def delete_video(self, s3_key: str) -> bool:
        """
        從 S3 刪除影片

        Args:
            s3_key: S3 物件鍵（例: aichatbot/videos/kb-123_20240101_120000.mp4）

        Returns:
            True if 刪除成功
        """
        try:
            print(f"🗑️  刪除影片: {s3_key}")

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            print(f"✅ 影片已刪除")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']

            # 404 錯誤視為成功（檔案本來就不存在）
            if error_code == 'NoSuchKey':
                print(f"⚠️  檔案不存在，視為已刪除: {s3_key}")
                return True

            print(f"❌ S3 刪除失敗: [{error_code}] {error_msg}")
            return False
        except Exception as e:
            print(f"❌ 刪除過程發生錯誤: {str(e)}")
            return False

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """
        生成臨時簽名 URL（用於私有影片）

        Args:
            s3_key: S3 物件鍵
            expiration: 過期時間（秒），預設 1 小時

        Returns:
            臨時 URL（可以直接播放但會過期）
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )

            print(f"🔗 生成臨時 URL（有效期 {expiration} 秒）")
            return url

        except ClientError as e:
            error_msg = e.response['Error']['Message']
            print(f"❌ 生成簽名 URL 失敗: {error_msg}")
            raise Exception(f"生成簽名 URL 失敗: {error_msg}")

    def check_bucket_exists(self) -> bool:
        """檢查 S3 Bucket 是否存在"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False

    def get_video_metadata(self, s3_key: str) -> Optional[Dict]:
        """
        獲取影片元數據

        Returns:
            {
                'size': 1024000,
                'last_modified': '2024-01-01T12:00:00',
                'content_type': 'video/mp4'
            }
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response['ContentType'],
                'metadata': response.get('Metadata', {})
            }

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                print(f"⚠️  檔案不存在: {s3_key}")
                return None
            raise


# 全域實例（懶加載）
_s3_service_instance = None


def get_s3_video_service() -> S3VideoService:
    """獲取 S3 影片服務實例（單例模式）"""
    global _s3_service_instance

    if _s3_service_instance is None:
        _s3_service_instance = S3VideoService()

    return _s3_service_instance
