-- 為 form_sessions 表添加 metadata 欄位
-- 用於存儲 PAUSED/CONFIRMING 狀態的額外資訊

-- 添加 metadata JSONB 欄位
ALTER TABLE form_sessions
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- 創建索引以加速 metadata 查詢（如果需要根據 metadata 查詢）
CREATE INDEX IF NOT EXISTS idx_form_sessions_metadata
ON form_sessions USING gin (metadata);

-- 添加註解
COMMENT ON COLUMN form_sessions.metadata IS '表單會話的額外元數據，用於 PAUSED/CONFIRMING 狀態等場景';
