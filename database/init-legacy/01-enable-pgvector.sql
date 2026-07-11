-- 啟用 pgvector 擴充套件
CREATE EXTENSION IF NOT EXISTS vector;

-- 驗證安裝
SELECT * FROM pg_extension WHERE extname = 'vector';

-- ========================================
-- 創建通用函數
-- ========================================

-- 自動更新 updated_at 欄位的觸發器函數
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS '自動更新 updated_at 欄位的觸發器函數';
