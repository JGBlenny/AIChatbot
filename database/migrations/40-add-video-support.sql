-- Migration 40: 新增影片支援功能
-- 在 knowledge_base 表新增影片相關欄位

-- 1. 新增影片欄位到 knowledge_base
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS video_s3_key VARCHAR(500),
ADD COLUMN IF NOT EXISTS video_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS video_thumbnail_s3_key VARCHAR(500),
ADD COLUMN IF NOT EXISTS video_thumbnail_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS video_duration INTEGER,
ADD COLUMN IF NOT EXISTS video_file_size BIGINT,
ADD COLUMN IF NOT EXISTS video_format VARCHAR(20),
ADD COLUMN IF NOT EXISTS video_uploaded_at TIMESTAMP;

-- 2. 建立索引（加速查詢有影片的知識）
CREATE INDEX IF NOT EXISTS idx_kb_video_s3_key
ON knowledge_base(video_s3_key)
WHERE video_s3_key IS NOT NULL;

-- 3. 註解說明
COMMENT ON COLUMN knowledge_base.video_s3_key IS 'S3 物件鍵（例: videos/1/kb-123.mp4）';
COMMENT ON COLUMN knowledge_base.video_url IS '公開播放 URL（CloudFront 或 S3 直接連結）';
COMMENT ON COLUMN knowledge_base.video_thumbnail_s3_key IS '影片縮圖 S3 鍵';
COMMENT ON COLUMN knowledge_base.video_thumbnail_url IS '縮圖 URL';
COMMENT ON COLUMN knowledge_base.video_duration IS '影片時長（秒）';
COMMENT ON COLUMN knowledge_base.video_file_size IS '檔案大小（位元組）';
COMMENT ON COLUMN knowledge_base.video_format IS '影片格式（mp4, webm, mov）';
COMMENT ON COLUMN knowledge_base.video_uploaded_at IS '影片上傳時間';

-- 4. 驗證
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'knowledge_base'
  AND column_name LIKE 'video_%'
ORDER BY ordinal_position;
