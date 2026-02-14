# AWS S3 影片儲存設定指南

本指南說明如何設定 AWS S3 儲存桶以支援知識庫影片上傳功能。

## 目錄

1. [功能概述](#功能概述)
2. [AWS S3 設定](#aws-s3-設定)
3. [環境變數設定](#環境變數設定)
4. [CloudFront CDN（選用）](#cloudfront-cdn選用)
5. [測試驗證](#測試驗證)
6. [常見問題](#常見問題)

---

## 功能概述

### 系統架構

```
前端上傳 → 後端 API → S3 儲存桶 → (可選) CloudFront CDN
                ↓
           PostgreSQL (metadata)
```

### 功能特性

- ✅ **支援格式**：MP4、WebM、MOV
- ✅ **檔案大小限制**：500 MB
- ✅ **儲存結構**：`videos/{vendor_id}/kb-{knowledge_id}_{timestamp}.{ext}`
- ✅ **CDN 支援**：可選配 CloudFront 加速
- ✅ **元數據管理**：URL、大小、格式、時長自動記錄
- ✅ **刪除功能**：S3 物件與資料庫記錄同步刪除

---

## AWS S3 設定

### 1. 建立 S3 儲存桶

登入 [AWS Console](https://console.aws.amazon.com/s3/)，建立新的 S3 儲存桶：

```bash
儲存桶名稱: aichatbot-knowledge-videos
區域: ap-northeast-1 (東京，或您偏好的區域)
```

### 2. 設定公開存取

為了讓影片可以在前端播放，系統會在上傳時自動將每個影片檔案設定為 `public-read` ACL。

**必要設定：啟用 ACL**

進入儲存桶 → **Permissions** → **Object Ownership**：
- 選擇 **ACLs enabled**
- 勾選 **Bucket owner preferred**

**（選用）儲存桶政策**

如果您想要使用 Bucket Policy 而非 ACL，可以進入 **Bucket Policy** 貼上：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::aichatbot-knowledge-videos/aichatbot/videos/*"
    }
  ]
}
```

> **推薦**：使用 ACL 方法（系統預設），因為可以針對每個檔案單獨控制權限，更安全靈活。

### 3. 設定 CORS

進入儲存桶 → **Permissions** → **Cross-origin resource sharing (CORS)**：

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": ["ETag"]
  }
]
```

> **注意**：生產環境建議將 `AllowedOrigins` 改為您的域名，例如 `["https://yourdomain.com"]`

### 4. 建立 IAM 使用者與金鑰

建立專用 IAM 使用者以存取 S3：

**Step 1: 建立 IAM 使用者**

- 進入 [IAM Console](https://console.aws.amazon.com/iam/)
- **Users** → **Add users**
- 使用者名稱：`aichatbot-s3-uploader`
- 存取類型：**Access key - Programmatic access**

**Step 2: 附加權限政策**

建立自訂政策（推薦最小權限原則）：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::aichatbot-knowledge-videos",
        "arn:aws:s3:::aichatbot-knowledge-videos/*"
      ]
    }
  ]
}
```

**Step 3: 儲存 Access Key**

建立完成後，下載並安全保存：
- **Access Key ID**
- **Secret Access Key**

---

## 環境變數設定

將 AWS 憑證加入環境變數檔案。

### 開發環境設定

編輯 `.env` 檔案（根據 `.env.example`）：

```bash
# AWS S3 (影片儲存)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=aichatbot-knowledge-videos
CLOUDFRONT_DOMAIN=                     # (可選) 稍後設定
```

### 生產環境設定

**方法 A：Docker Compose（推薦）**

編輯 `docker-compose.yml`：

```yaml
services:
  rag-orchestrator:
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_REGION: ap-northeast-1
      S3_BUCKET_NAME: aichatbot-knowledge-videos
      CLOUDFRONT_DOMAIN: ${CLOUDFRONT_DOMAIN:-}
```

**方法 B：使用 IAM Role（EC2/ECS）**

如果部署在 AWS EC2 或 ECS，可以使用 IAM Role 而非金鑰：

1. 為 EC2 Instance / ECS Task 附加 IAM Role
2. 賦予上述 S3 權限政策
3. 移除環境變數中的 `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY`

程式碼會自動偵測並使用 IAM Role。

---

## CloudFront CDN（選用）

使用 CloudFront CDN 可以加速全球影片傳輸，減少 S3 流量費用。

### 1. 建立 CloudFront Distribution

登入 [CloudFront Console](https://console.aws.amazon.com/cloudfront/)：

**Origin Settings:**
- **Origin Domain**: `aichatbot-knowledge-videos.s3.ap-northeast-1.amazonaws.com`
- **Origin Path**: 留空
- **Restrict Bucket Access**: No（已使用 Bucket Policy）

**Default Cache Behavior:**
- **Viewer Protocol Policy**: Redirect HTTP to HTTPS
- **Allowed HTTP Methods**: GET, HEAD
- **Cache Policy**: CachingOptimized（或自訂 1 年 TTL）

**Distribution Settings:**
- **Price Class**: Use All Edge Locations（或選擇 Asia/Europe）
- **Alternate Domain Names (CNAMEs)**: 可設定自訂域名

### 2. 等待部署完成

部署通常需要 15-20 分鐘。完成後取得 CloudFront 網域：

```
範例: d1a2b3c4d5e6f7.cloudfront.net
```

### 3. 更新環境變數

將 CloudFront 域名加入 `.env`：

```bash
CLOUDFRONT_DOMAIN=d1a2b3c4d5e6f7.cloudfront.net
```

### 4. 驗證 CDN

上傳影片後，URL 格式將變更為：

```
https://d1a2b3c4d5e6f7.cloudfront.net/videos/1/kb-123_20240101_120000.mp4
```

---

## 測試驗證

### 1. 檢查 S3 服務狀態

```bash
curl http://localhost:8100/api/v1/videos/health
```

**預期回應：**

```json
{
  "status": "healthy",
  "bucket": "aichatbot-knowledge-videos",
  "region": "ap-northeast-1",
  "cdn_enabled": true
}
```

### 2. 測試影片上傳

**使用知識管理介面：**

1. 登入 `http://localhost:3000`
2. 進入 **知識管理**
3. 新增或編輯知識
4. 上傳測試影片（< 500MB）
5. 檢查是否顯示播放器

**使用 API：**

```bash
curl -X POST http://localhost:8100/api/v1/videos/upload \
  -F "knowledge_id=1" \
  -F "vendor_id=1" \
  -F "file=@test_video.mp4"
```

**預期回應：**

```json
{
  "success": true,
  "message": "影片上傳成功",
  "data": {
    "s3_key": "videos/1/kb-1_20240101_120000.mp4",
    "url": "https://aichatbot-knowledge-videos.s3.ap-northeast-1.amazonaws.com/videos/1/kb-1_20240101_120000.mp4",
    "size": 1024000,
    "format": "mp4"
  }
}
```

### 3. 測試影片播放

在聊天測試介面測試知識回答時，若該知識有影片，應顯示播放器。

---

## 常見問題

### Q1: 上傳失敗：NoCredentialsError

**錯誤訊息：**
```
❌ AWS 憑證未找到。請設定 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY
```

**解決方法：**
- 檢查 `.env` 檔案是否正確設定
- 確認 Docker Compose 有正確載入環境變數
- 如使用 IAM Role，確認 Role 權限正確

### Q2: 上傳失敗：AccessDenied

**錯誤訊息：**
```
❌ S3 上傳失敗: Access Denied
```

**解決方法：**
- 檢查 IAM 使用者權限是否包含 `s3:PutObject`
- 確認儲存桶名稱正確
- 檢查儲存桶政策是否允許上傳

### Q3: 影片無法播放：403 Forbidden

**錯誤訊息：**
```
Video cannot be loaded: 403 Forbidden
```

**解決方法：**
- 檢查儲存桶政策是否允許 `s3:GetObject`
- 確認物件 ACL 為 `public-read`（或使用儲存桶政策）
- 如使用 CloudFront，檢查 Origin Access 設定

### Q4: CloudFront 回傳舊內容

**問題描述：**
重新上傳影片後，CloudFront 仍顯示舊版本。

**解決方法：**
- CloudFront 有快取機制（預設 24 小時）
- 方案 1：等待快取過期
- 方案 2：建立 CloudFront Invalidation（手動清除快取）
- 方案 3：修改檔名（系統已使用時間戳記，應不會發生）

### Q5: 影片上傳過慢

**問題描述：**
上傳大檔案（> 100MB）耗時過長。

**優化建議：**
- 使用影片壓縮工具減少檔案大小
- 考慮使用 S3 Multipart Upload（需修改程式碼）
- 檢查網路頻寬

### Q6: 如何限制影片存取權限？

**需求：**
希望影片僅對授權使用者可見。

**解決方法：**
1. 移除儲存桶的公開讀取政策
2. 使用 `S3VideoService.generate_presigned_url()` 生成臨時 URL
3. 修改 API 回傳 presigned URL 而非永久 URL

範例：

```python
presigned_url = s3_service.generate_presigned_url(
    s3_key='videos/1/kb-123.mp4',
    expiration=3600  # 1 小時有效
)
```

---

## 成本估算

### S3 儲存成本（東京區域）

| 項目 | 費用 | 說明 |
|------|------|------|
| 儲存費用 | $0.025/GB/月 | 100 個 10MB 影片 = 1GB ≈ $0.025/月 |
| PUT 請求 | $0.0047/1000 次 | 上傳 100 個影片 ≈ $0.0005 |
| GET 請求 | $0.00037/1000 次 | 每月 10,000 次播放 ≈ $0.004 |
| 資料傳輸 | $0.114/GB | 出站流量（可用 CloudFront 降低） |

### CloudFront CDN 成本

| 項目 | 費用 | 說明 |
|------|------|------|
| 資料傳輸（亞洲） | $0.120/GB | 前 10TB |
| HTTP 請求 | $0.0090/10,000 次 | GET 請求 |

**試算（每月 1,000 次播放，每個影片 10MB）：**
- 資料傳輸：10GB × $0.120 = **$1.20**
- 請求費用：1,000 ÷ 10,000 × $0.0090 = **$0.0009**
- **總計：約 $1.20/月**

---

## 進階設定

### 啟用 S3 生命週期規則（自動刪除舊影片）

如需節省儲存成本，可設定生命週期規則自動刪除未使用的影片：

```json
{
  "Rules": [
    {
      "Id": "DeleteOldVideos",
      "Status": "Enabled",
      "Prefix": "videos/",
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

### 啟用 S3 版本控制

如需保留影片歷史版本：

```bash
aws s3api put-bucket-versioning \
  --bucket aichatbot-knowledge-videos \
  --versioning-configuration Status=Enabled
```

### 啟用 S3 伺服器端加密

保護影片資料安全：

```bash
aws s3api put-bucket-encryption \
  --bucket aichatbot-knowledge-videos \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

---

## 相關文件

- [API 文件 - 影片管理](/docs/api/VIDEO_API.md)
- [系統架構](/docs/architecture/SYSTEM_ARCHITECTURE.md)
- [部署指南](/docs/guides/DEPLOYMENT.md)
- [AWS S3 官方文件](https://docs.aws.amazon.com/s3/)
- [CloudFront 官方文件](https://docs.aws.amazon.com/cloudfront/)

---

## 支援

如有問題，請聯繫開發團隊或提交 Issue。
