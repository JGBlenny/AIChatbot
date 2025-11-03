-- ========================================
-- AI 知識管理系統
-- 用途：AI 生成知識候選、知識導入作業追蹤
-- ========================================

-- ========================================
-- 1. AI 生成知識候選表
-- ========================================

CREATE TABLE IF NOT EXISTS ai_generated_knowledge_candidates (
    id SERIAL PRIMARY KEY,
    test_scenario_id INTEGER NOT NULL REFERENCES test_scenarios(id) ON DELETE CASCADE,

    -- 生成內容
    question TEXT NOT NULL,
    generated_answer TEXT NOT NULL,
    confidence_score DECIMAL(3,2),  -- AI 生成的信心度 (0.00-1.00)

    -- 生成詳情
    generation_prompt TEXT,
    ai_model VARCHAR(50),
    generation_reasoning TEXT,
    suggested_sources TEXT[],
    warnings TEXT[],

    -- 審核狀態
    status VARCHAR(20) DEFAULT 'pending_review',  -- pending_review, approved, rejected, needs_revision
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- 編輯記錄
    edited_question TEXT,
    edited_answer TEXT,
    edit_summary TEXT,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_candidates_test_scenario ON ai_generated_knowledge_candidates(test_scenario_id);
CREATE INDEX idx_ai_candidates_status ON ai_generated_knowledge_candidates(status);
CREATE INDEX idx_ai_candidates_created ON ai_generated_knowledge_candidates(created_at DESC);
CREATE INDEX idx_ai_candidates_confidence ON ai_generated_knowledge_candidates(confidence_score DESC);

CREATE TRIGGER update_ai_candidates_updated_at
    BEFORE UPDATE ON ai_generated_knowledge_candidates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE ai_generated_knowledge_candidates IS 'AI 生成知識候選表：存儲 AI 生成的知識，需人工審核';
COMMENT ON COLUMN ai_generated_knowledge_candidates.status IS 'pending_review（待審核）, approved（已核准）, rejected（已拒絕）, needs_revision（需修改）';
COMMENT ON COLUMN ai_generated_knowledge_candidates.confidence_score IS 'AI 生成的信心度（0.00-1.00）';

-- ========================================
-- 2. 知識導入作業表
-- ========================================

CREATE TABLE IF NOT EXISTS knowledge_import_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE CASCADE,

    -- 文件信息
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_type VARCHAR(50),  -- excel, csv, json
    file_size_bytes BIGINT,

    -- 導入配置
    import_mode VARCHAR(50) DEFAULT 'append',  -- append, replace, merge
    enable_deduplication BOOLEAN DEFAULT TRUE,
    target_intent_id INTEGER REFERENCES intents(id),

    -- 作業狀態
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed, cancelled
    progress JSONB DEFAULT '{"current": 0, "total": 0, "percentage": 0}',

    -- 統計信息
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    imported_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,

    -- 結果信息
    result JSONB,  -- 詳細結果：成功項目、錯誤項目、跳過項目
    error_message TEXT,
    error_details JSONB,

    -- 審計
    created_by VARCHAR(100) DEFAULT 'admin',
    started_by VARCHAR(100),
    completed_by VARCHAR(100),

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_jobs_status ON knowledge_import_jobs(status);
CREATE INDEX idx_import_jobs_vendor ON knowledge_import_jobs(vendor_id);
CREATE INDEX idx_import_jobs_created ON knowledge_import_jobs(created_at DESC);
CREATE INDEX idx_import_jobs_intent ON knowledge_import_jobs(target_intent_id);

CREATE TRIGGER update_knowledge_import_jobs_updated_at
    BEFORE UPDATE ON knowledge_import_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE knowledge_import_jobs IS '知識導入作業表：追蹤批量導入知識的進度和結果';
COMMENT ON COLUMN knowledge_import_jobs.status IS 'pending（待處理）, processing（處理中）, completed（已完成）, failed（失敗）, cancelled（已取消）';
COMMENT ON COLUMN knowledge_import_jobs.import_mode IS 'append（追加）, replace（替換）, merge（合併）';
COMMENT ON COLUMN knowledge_import_jobs.progress IS '進度資訊 JSON：{current, total, percentage}';

-- ========================================
-- 3. AI 知識審核函數
-- ========================================

-- 審核通過：將 AI 生成的知識插入到 knowledge_base
CREATE OR REPLACE FUNCTION approve_ai_knowledge_candidate(
    candidate_id INTEGER,
    reviewer VARCHAR(100),
    review_note TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    new_knowledge_id INTEGER;
    candidate_record RECORD;
BEGIN
    -- 獲取候選知識
    SELECT * INTO candidate_record
    FROM ai_generated_knowledge_candidates
    WHERE id = candidate_id AND status = 'pending_review';

    IF NOT FOUND THEN
        RAISE EXCEPTION '候選知識不存在或已審核';
    END IF;

    -- 插入到 knowledge_base
    INSERT INTO knowledge_base (
        question_summary,
        answer,
        source_type,
        source_test_scenario_id,
        generation_metadata,
        created_by
    )
    VALUES (
        COALESCE(candidate_record.edited_question, candidate_record.question),
        COALESCE(candidate_record.edited_answer, candidate_record.generated_answer),
        'ai_generated',
        candidate_record.test_scenario_id,
        jsonb_build_object(
            'model', candidate_record.ai_model,
            'confidence', candidate_record.confidence_score,
            'reasoning', candidate_record.generation_reasoning,
            'reviewed_by', reviewer,
            'reviewed_at', NOW()
        ),
        reviewer
    )
    RETURNING id INTO new_knowledge_id;

    -- 更新候選狀態
    UPDATE ai_generated_knowledge_candidates
    SET
        status = 'approved',
        reviewed_by = reviewer,
        reviewed_at = NOW(),
        review_notes = review_note,
        updated_at = NOW()
    WHERE id = candidate_id;

    RETURN new_knowledge_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION approve_ai_knowledge_candidate IS '審核通過 AI 生成的知識候選，插入到 knowledge_base';

-- ========================================
-- 顯示統計資訊
-- ========================================

SELECT
    '✅ AI 知識管理系統已建立' AS status;
