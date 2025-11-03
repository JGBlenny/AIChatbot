-- Migration 28: 建立知識匯入作業追蹤表
-- 用於追蹤知識匯入作業的狀態、進度和結果

-- ============================================================
-- 建立 knowledge_import_jobs 表
-- ============================================================

CREATE TABLE IF NOT EXISTS knowledge_import_jobs (
    -- 主鍵
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 業者資訊
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,

    -- 檔案資訊
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_type VARCHAR(50),  -- excel, pdf, txt, json
    file_size_bytes BIGINT,

    -- 匯入配置
    import_mode VARCHAR(50) DEFAULT 'append',  -- append, replace, merge
    enable_deduplication BOOLEAN DEFAULT TRUE,

    -- 作業狀態
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    progress JSONB,  -- {current: 50, total: 100, stage: "生成向量"}

    -- 統計資訊
    total_items INTEGER,
    processed_items INTEGER,
    imported_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,

    -- 結果資訊
    result JSONB,  -- 詳細的匯入結果統計

    -- 錯誤資訊
    error_message TEXT,

    -- 執行者
    created_by VARCHAR(100) DEFAULT 'admin',

    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 建立索引
-- ============================================================

-- 按狀態查詢
CREATE INDEX idx_import_jobs_status ON knowledge_import_jobs(status);

-- 按業者查詢
CREATE INDEX idx_import_jobs_vendor ON knowledge_import_jobs(vendor_id);

-- 按建立時間查詢（用於列出歷史記錄）
CREATE INDEX idx_import_jobs_created ON knowledge_import_jobs(created_at DESC);

-- 按狀態和建立時間查詢（用於列出進行中的作業）
CREATE INDEX idx_import_jobs_status_created ON knowledge_import_jobs(status, created_at DESC);

-- ============================================================
-- 建立自動更新 updated_at 的觸發器
-- ============================================================

CREATE OR REPLACE FUNCTION update_import_job_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_import_job_timestamp
    BEFORE UPDATE ON knowledge_import_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_import_job_updated_at();

-- ============================================================
-- 建立查詢函數
-- ============================================================

-- 取得作業詳情（供前端輪詢）
CREATE OR REPLACE FUNCTION get_import_job_status(p_job_id UUID)
RETURNS TABLE (
    job_id UUID,
    vendor_id INTEGER,
    file_name VARCHAR,
    status VARCHAR,
    progress JSONB,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        j.job_id,
        j.vendor_id,
        j.file_name,
        j.status,
        j.progress,
        j.result,
        j.error_message,
        j.created_at,
        j.started_at,
        j.completed_at,
        j.updated_at
    FROM knowledge_import_jobs j
    WHERE j.job_id = p_job_id;
END;
$$ LANGUAGE plpgsql;

-- 取得業者的匯入歷史
CREATE OR REPLACE FUNCTION get_vendor_import_history(
    p_vendor_id INTEGER,
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    job_id UUID,
    file_name VARCHAR,
    status VARCHAR,
    imported_count INTEGER,
    skipped_count INTEGER,
    error_count INTEGER,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        j.job_id,
        j.file_name,
        j.status,
        j.imported_count,
        j.skipped_count,
        j.error_count,
        j.created_at,
        j.completed_at
    FROM knowledge_import_jobs j
    WHERE j.vendor_id = p_vendor_id
    ORDER BY j.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- 取得匯入統計
CREATE OR REPLACE FUNCTION get_import_statistics(
    p_vendor_id INTEGER DEFAULT NULL,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_jobs BIGINT,
    completed_jobs BIGINT,
    failed_jobs BIGINT,
    processing_jobs BIGINT,
    total_imported BIGINT,
    total_skipped BIGINT,
    total_errors BIGINT,
    avg_imported_per_job NUMERIC,
    success_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_jobs,
        COUNT(*) FILTER (WHERE status = 'completed')::BIGINT as completed_jobs,
        COUNT(*) FILTER (WHERE status = 'failed')::BIGINT as failed_jobs,
        COUNT(*) FILTER (WHERE status = 'processing')::BIGINT as processing_jobs,
        COALESCE(SUM(imported_count), 0)::BIGINT as total_imported,
        COALESCE(SUM(skipped_count), 0)::BIGINT as total_skipped,
        COALESCE(SUM(error_count), 0)::BIGINT as total_errors,
        ROUND(AVG(imported_count), 2) as avg_imported_per_job,
        CASE
            WHEN COUNT(*) FILTER (WHERE status IN ('completed', 'failed')) > 0
            THEN ROUND(
                COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC /
                COUNT(*) FILTER (WHERE status IN ('completed', 'failed'))::NUMERIC * 100,
                2
            )
            ELSE 0
        END as success_rate
    FROM knowledge_import_jobs
    WHERE (p_vendor_id IS NULL OR vendor_id = p_vendor_id)
      AND created_at >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 清理舊作業的函數（可用於定期清理）
-- ============================================================

CREATE OR REPLACE FUNCTION cleanup_old_import_jobs(
    p_days_to_keep INTEGER DEFAULT 90
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM knowledge_import_jobs
    WHERE status IN ('completed', 'failed')
      AND completed_at < CURRENT_TIMESTAMP - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 插入測試資料（可選，用於開發測試）
-- ============================================================

-- COMMENT: 在生產環境可以移除此段落
/*
INSERT INTO knowledge_import_jobs (
    job_id,
    vendor_id,
    file_name,
    file_type,
    import_mode,
    status,
    progress,
    imported_count,
    skipped_count,
    error_count,
    created_by
) VALUES (
    gen_random_uuid(),
    1,
    'test_knowledge.xlsx',
    'excel',
    'append',
    'completed',
    '{"current": 100, "total": 100}'::jsonb,
    45,
    5,
    0,
    'admin'
);
*/

-- ============================================================
-- 建立視圖：進行中的匯入作業
-- ============================================================

CREATE OR REPLACE VIEW v_active_import_jobs AS
SELECT
    j.job_id,
    j.vendor_id,
    v.name as vendor_name,
    j.file_name,
    j.status,
    j.progress,
    j.created_at,
    j.updated_at,
    -- 計算執行時間
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - j.created_at)) as elapsed_seconds
FROM knowledge_import_jobs j
LEFT JOIN vendors v ON j.vendor_id = v.id
WHERE j.status IN ('pending', 'processing')
ORDER BY j.created_at DESC;

-- ============================================================
-- 建立視圖：最近的匯入歷史
-- ============================================================

CREATE OR REPLACE VIEW v_recent_import_history AS
SELECT
    j.job_id,
    j.vendor_id,
    v.name as vendor_name,
    j.file_name,
    j.status,
    j.imported_count,
    j.skipped_count,
    j.error_count,
    j.created_at,
    j.completed_at,
    -- 計算執行時間
    EXTRACT(EPOCH FROM (j.completed_at - j.created_at)) as execution_seconds
FROM knowledge_import_jobs j
LEFT JOIN vendors v ON j.vendor_id = v.id
WHERE j.status IN ('completed', 'failed')
ORDER BY j.completed_at DESC
LIMIT 50;

-- ============================================================
-- 授予權限
-- ============================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_import_jobs TO aichatbot;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO aichatbot;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO aichatbot;

-- ============================================================
-- Migration 完成
-- ============================================================

COMMENT ON TABLE knowledge_import_jobs IS '知識匯入作業追蹤表';
COMMENT ON COLUMN knowledge_import_jobs.job_id IS '作業唯一識別碼（UUID）';
COMMENT ON COLUMN knowledge_import_jobs.status IS '作業狀態：pending, processing, completed, failed';
COMMENT ON COLUMN knowledge_import_jobs.progress IS 'JSON 格式的進度資訊';
COMMENT ON COLUMN knowledge_import_jobs.result IS 'JSON 格式的匯入結果統計';

-- 記錄 migration 版本
-- INSERT INTO schema_migrations (version, applied_at) VALUES (28, CURRENT_TIMESTAMP);
