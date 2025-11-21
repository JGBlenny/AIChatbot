-- Migration: 統一 Job 系統 - 創建 unified_jobs 表
-- Date: 2025-11-21
-- Description: 創建統一異步作業管理表，支援匯入、匯出、轉換等所有 job 類型
-- Related Doc: docs/planning/UNIFIED_JOB_SYSTEM_DESIGN.md

-- ==================== 統一 Job 系統 ====================
-- 用途：管理所有異步作業（匯入、匯出、轉換、備份等）
-- 特點：使用 JSONB 存儲類型特定配置，支援彈性擴展

CREATE TABLE IF NOT EXISTS unified_jobs (
    -- ==================== 主鍵與分類 ====================
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(50) NOT NULL,  -- 'knowledge_import', 'knowledge_export', 'document_convert', 'backup', 'restore', 'vector_rebuild'

    -- ==================== 關聯資源 ====================
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,  -- 業者 ID（NULL = 通用知識）
    user_id VARCHAR(100) NOT NULL,  -- 建立者 ID

    -- ==================== 通用狀態 ====================
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- pending: 待處理
    -- processing: 處理中
    -- completed: 已完成
    -- failed: 失敗
    -- cancelled: 已取消

    progress JSONB,  -- 進度資訊（彈性格式）
    -- 範例: {"stage": "processing", "current": 500, "total": 1000, "percentage": 50, "message": "已處理 500/1000 筆"}

    -- ==================== 類型特定配置（JSONB 彈性存儲）====================
    job_config JSONB NOT NULL,  -- 作業配置（各類型 job 的特定參數）
    job_result JSONB,            -- 作業結果（各類型 job 的結果資料）
    error_message TEXT,          -- 錯誤訊息（失敗時）
    error_details JSONB,         -- 詳細錯誤資訊（堆疊、context 等）

    -- ==================== 通用統計欄位 ====================
    total_records INTEGER,      -- 總筆數
    processed_records INTEGER,  -- 已處理筆數
    success_records INTEGER,    -- 成功筆數
    failed_records INTEGER,     -- 失敗筆數
    skipped_records INTEGER,    -- 跳過筆數

    -- ==================== 檔案相關 ====================
    file_path VARCHAR(500),     -- 檔案路徑（匯入來源或匯出目標）
    file_name VARCHAR(255),     -- 檔案名稱
    file_size_bytes BIGINT,     -- 檔案大小

    -- ==================== 審計欄位 ====================
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,       -- 開始處理時間
    completed_at TIMESTAMP,     -- 完成時間
    expires_at TIMESTAMP,       -- 檔案過期時間（用於自動清理）

    -- ==================== 效能追蹤 ====================
    processing_time_seconds INTEGER  -- 處理耗時（秒），由觸發器自動計算
);

-- ==================== 索引優化 ====================

-- 複合索引：按類型和狀態查詢（常用組合）
CREATE INDEX IF NOT EXISTS idx_unified_jobs_type_status
    ON unified_jobs(job_type, status);

-- 複合索引：按業者和類型查詢
CREATE INDEX IF NOT EXISTS idx_unified_jobs_vendor_type
    ON unified_jobs(vendor_id, job_type)
    WHERE vendor_id IS NOT NULL;

-- 單欄索引：按使用者查詢（用戶歷史記錄）
CREATE INDEX IF NOT EXISTS idx_unified_jobs_user
    ON unified_jobs(user_id);

-- 單欄索引：按創建時間倒序（最新作業）
CREATE INDEX IF NOT EXISTS idx_unified_jobs_created_at
    ON unified_jobs(created_at DESC);

-- 複合索引：清理過期檔案（定時任務用）
CREATE INDEX IF NOT EXISTS idx_unified_jobs_expires
    ON unified_jobs(expires_at)
    WHERE expires_at IS NOT NULL AND status = 'completed';

-- JSONB 索引：加速 config 查詢（如：按 import_mode 查詢）
CREATE INDEX IF NOT EXISTS idx_unified_jobs_config_gin
    ON unified_jobs USING GIN (job_config);

-- JSONB 索引：加速 result 查詢
CREATE INDEX IF NOT EXISTS idx_unified_jobs_result_gin
    ON unified_jobs USING GIN (job_result);

-- ==================== 觸發器：自動更新 updated_at 與計算處理時間 ====================
CREATE OR REPLACE FUNCTION update_unified_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;

    -- 自動設置 started_at（當狀態變為 processing 時）
    IF NEW.status = 'processing' AND OLD.status != 'processing' AND NEW.started_at IS NULL THEN
        NEW.started_at = CURRENT_TIMESTAMP;
    END IF;

    -- 自動設置 completed_at（當狀態變為終止狀態時）
    IF NEW.status IN ('completed', 'failed', 'cancelled') AND OLD.status NOT IN ('completed', 'failed', 'cancelled') THEN
        NEW.completed_at = CURRENT_TIMESTAMP;
    END IF;

    -- 自動計算處理時間
    IF NEW.status IN ('completed', 'failed', 'cancelled') AND NEW.started_at IS NOT NULL AND NEW.completed_at IS NOT NULL THEN
        NEW.processing_time_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_unified_jobs_updated_at
    BEFORE UPDATE ON unified_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_unified_jobs_updated_at();

-- ==================== 註釋 ====================
COMMENT ON TABLE unified_jobs IS '統一異步作業管理表（匯入、匯出、轉換等）';
COMMENT ON COLUMN unified_jobs.job_id IS '作業唯一識別碼';
COMMENT ON COLUMN unified_jobs.job_type IS '作業類型：knowledge_import, knowledge_export, document_convert, backup, restore, vector_rebuild';
COMMENT ON COLUMN unified_jobs.vendor_id IS '業者 ID（NULL 表示通用知識）';
COMMENT ON COLUMN unified_jobs.user_id IS '建立者（使用者 ID）';
COMMENT ON COLUMN unified_jobs.status IS '作業狀態：pending, processing, completed, failed, cancelled';
COMMENT ON COLUMN unified_jobs.progress IS '進度資訊（JSONB，包含 stage, current, total, percentage, message）';
COMMENT ON COLUMN unified_jobs.job_config IS '作業配置（JSONB，類型特定參數）';
COMMENT ON COLUMN unified_jobs.job_result IS '作業結果（JSONB，類型特定結果）';
COMMENT ON COLUMN unified_jobs.error_message IS '錯誤訊息（簡短摘要）';
COMMENT ON COLUMN unified_jobs.error_details IS '詳細錯誤資訊（JSONB，包含堆疊追蹤等）';
COMMENT ON COLUMN unified_jobs.total_records IS '總筆數（適用於批次處理）';
COMMENT ON COLUMN unified_jobs.processed_records IS '已處理筆數';
COMMENT ON COLUMN unified_jobs.success_records IS '成功筆數';
COMMENT ON COLUMN unified_jobs.failed_records IS '失敗筆數';
COMMENT ON COLUMN unified_jobs.skipped_records IS '跳過筆數';
COMMENT ON COLUMN unified_jobs.file_path IS '檔案路徑（匯入來源或匯出目標）';
COMMENT ON COLUMN unified_jobs.file_name IS '檔案名稱';
COMMENT ON COLUMN unified_jobs.file_size_bytes IS '檔案大小（bytes）';
COMMENT ON COLUMN unified_jobs.started_at IS '開始處理時間（由觸發器自動設置）';
COMMENT ON COLUMN unified_jobs.completed_at IS '完成時間（由觸發器自動設置）';
COMMENT ON COLUMN unified_jobs.processing_time_seconds IS '處理耗時（秒），由觸發器自動計算';
COMMENT ON COLUMN unified_jobs.expires_at IS '檔案過期時間（用於自動清理定時任務）';

-- ==================== 權限設置（如果需要）====================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON unified_jobs TO aichatbot;

-- ==================== 驗證安裝 ====================
-- 顯示建立結果
DO $$
BEGIN
    RAISE NOTICE '✅ unified_jobs 表創建完成';
    RAISE NOTICE '✅ 已創建 8 個索引';
    RAISE NOTICE '✅ 已創建自動更新觸發器';
    RAISE NOTICE '📖 詳細設計文件: docs/planning/UNIFIED_JOB_SYSTEM_DESIGN.md';
END $$;
