-- Migration: 知識庫匯出功能 - 作業追蹤表
-- Date: 2025-11-21
-- Description: 創建 knowledge_export_jobs 表以追蹤 Excel 匯出作業狀態

-- 1. 創建匯出作業表
CREATE TABLE IF NOT EXISTS knowledge_export_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,  -- 業者 ID（NULL = 通用知識）

    -- 匯出配置
    export_mode VARCHAR(20) NOT NULL,        -- basic, formatted, optimized
    include_intents BOOLEAN DEFAULT TRUE,    -- 是否包含意圖對照表
    include_metadata BOOLEAN DEFAULT TRUE,   -- 是否包含匯出資訊
    created_by VARCHAR(100) NOT NULL,        -- 建立者（使用者 ID）

    -- 狀態追蹤
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    progress JSONB,                          -- 進度資訊 {stage, current, total, percentage, message}

    -- 結果
    result JSONB,                            -- 結果資訊 {exported, file_path, file_size_kb, file_size_bytes}
    error_message TEXT,                      -- 錯誤訊息
    exported_count INTEGER,                  -- 匯出筆數
    file_size_bytes BIGINT,                  -- 檔案大小（bytes）

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP                   -- 完成時間
);

-- 2. 創建索引以優化查詢
CREATE INDEX IF NOT EXISTS idx_export_jobs_vendor_id
    ON knowledge_export_jobs(vendor_id);

CREATE INDEX IF NOT EXISTS idx_export_jobs_status
    ON knowledge_export_jobs(status);

CREATE INDEX IF NOT EXISTS idx_export_jobs_created_at
    ON knowledge_export_jobs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_export_jobs_export_mode
    ON knowledge_export_jobs(export_mode);

-- 3. 添加註釋
COMMENT ON TABLE knowledge_export_jobs IS '知識庫 Excel 匯出作業追蹤表';
COMMENT ON COLUMN knowledge_export_jobs.job_id IS '作業唯一識別碼';
COMMENT ON COLUMN knowledge_export_jobs.vendor_id IS '業者 ID（NULL 表示通用知識）';
COMMENT ON COLUMN knowledge_export_jobs.export_mode IS '匯出模式：basic=基礎匯出, formatted=進階格式化, optimized=效能優化';
COMMENT ON COLUMN knowledge_export_jobs.include_intents IS '是否包含意圖對照表工作表';
COMMENT ON COLUMN knowledge_export_jobs.include_metadata IS '是否包含匯出資訊工作表';
COMMENT ON COLUMN knowledge_export_jobs.status IS '作業狀態：pending=待處理, processing=處理中, completed=已完成, failed=失敗';
COMMENT ON COLUMN knowledge_export_jobs.progress IS '進度資訊（JSON 格式）';
COMMENT ON COLUMN knowledge_export_jobs.result IS '匯出結果（JSON 格式，包含檔案路徑和統計資訊）';
COMMENT ON COLUMN knowledge_export_jobs.exported_count IS '成功匯出的知識筆數';
COMMENT ON COLUMN knowledge_export_jobs.file_size_bytes IS '匯出檔案大小（bytes）';
COMMENT ON COLUMN knowledge_export_jobs.created_by IS '建立者（使用者 ID）';

-- 4. 創建更新 updated_at 的觸發器
CREATE OR REPLACE FUNCTION update_knowledge_export_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_knowledge_export_jobs_updated_at
    BEFORE UPDATE ON knowledge_export_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_knowledge_export_jobs_updated_at();

-- 5. 權限設置（如果需要）
-- GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_export_jobs TO aichatbot;
