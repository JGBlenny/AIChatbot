-- 新增知識庫缺失的欄位
-- 執行日期: 2026-01-12
-- 說明: 修復生產環境缺少的欄位問題

BEGIN;

-- 1. 表單關聯欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS form_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS form_intro TEXT;

COMMENT ON COLUMN knowledge_base.form_id IS '關聯的表單 ID';
COMMENT ON COLUMN knowledge_base.form_intro IS '表單引導語';

-- 2. 影片相關欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS video_url TEXT,
ADD COLUMN IF NOT EXISTS video_s3_key VARCHAR(500),
ADD COLUMN IF NOT EXISTS video_file_size BIGINT,
ADD COLUMN IF NOT EXISTS video_duration INTEGER,
ADD COLUMN IF NOT EXISTS video_format VARCHAR(50);

COMMENT ON COLUMN knowledge_base.video_url IS '教學影片 URL';
COMMENT ON COLUMN knowledge_base.video_s3_key IS 'S3 儲存金鑰';
COMMENT ON COLUMN knowledge_base.video_file_size IS '影片檔案大小（bytes）';
COMMENT ON COLUMN knowledge_base.video_duration IS '影片時長（秒）';
COMMENT ON COLUMN knowledge_base.video_format IS '影片格式（mp4, webm 等）';

-- 3. 表單觸發條件欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS trigger_form_condition TEXT;

COMMENT ON COLUMN knowledge_base.trigger_form_condition IS '觸發表單的條件';

COMMIT;

-- 驗證
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'knowledge_base'
  AND column_name IN (
    'form_id', 'form_intro',
    'video_url', 'video_s3_key', 'video_file_size', 'video_duration', 'video_format',
    'trigger_form_condition'
  )
ORDER BY column_name;
