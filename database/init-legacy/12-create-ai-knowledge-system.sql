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
    intent_ids INTEGER[],  -- AI 推薦的意圖 ID 列表

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
CREATE INDEX idx_ai_candidates_intent_ids ON ai_generated_knowledge_candidates USING GIN (intent_ids);

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
-- 支援多意圖、embedding、編輯版本選擇
CREATE OR REPLACE FUNCTION approve_ai_knowledge_candidate(
    p_candidate_id INTEGER,
    p_reviewed_by VARCHAR(100),
    p_review_notes TEXT DEFAULT NULL,
    p_use_edited BOOLEAN DEFAULT TRUE
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_candidate RECORD;
    v_final_question TEXT;
    v_final_answer TEXT;
    v_new_knowledge_id INTEGER;
    v_generation_metadata JSONB;
    v_intent_id INTEGER;
BEGIN
    -- 1. 取得候選記錄
    SELECT * INTO v_candidate
    FROM ai_generated_knowledge_candidates
    WHERE id = p_candidate_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION '候選知識不存在: %', p_candidate_id;
    END IF;

    IF v_candidate.status != 'pending_review' AND v_candidate.status != 'needs_revision' THEN
        RAISE EXCEPTION '只能批准狀態為 pending_review 或 needs_revision 的候選知識，當前狀態: %', v_candidate.status;
    END IF;

    -- 2. 決定使用原始版本還是編輯版本
    IF p_use_edited AND v_candidate.edited_answer IS NOT NULL THEN
        v_final_question := COALESCE(v_candidate.edited_question, v_candidate.question);
        v_final_answer := v_candidate.edited_answer;
    ELSE
        v_final_question := v_candidate.question;
        v_final_answer := v_candidate.generated_answer;
    END IF;

    -- 3. 從候選記錄的 intent_ids 獲取第一個 intent（如果有的話）
    IF v_candidate.intent_ids IS NOT NULL AND array_length(v_candidate.intent_ids, 1) > 0 THEN
        v_intent_id := v_candidate.intent_ids[1];
    ELSE
        v_intent_id := NULL;
    END IF;

    -- 4. 準備 generation_metadata
    v_generation_metadata := JSONB_BUILD_OBJECT(
        'ai_model', v_candidate.ai_model,
        'confidence_score', v_candidate.confidence_score,
        'generated_at', v_candidate.created_at,
        'reviewed_by', p_reviewed_by,
        'reviewed_at', NOW(),
        'was_edited', (v_candidate.edited_answer IS NOT NULL),
        'edit_summary', v_candidate.edit_summary,
        'reasoning', v_candidate.generation_reasoning,
        'warnings', v_candidate.warnings
    );

    -- 5. 插入正式知識庫
    INSERT INTO knowledge_base (
        question_summary,
        answer,
        intent_id,
        embedding,
        source_type,
        source_test_scenario_id,
        generation_metadata,
        target_user,
        is_active
    )
    VALUES (
        v_final_question,
        v_final_answer,
        v_intent_id,
        v_candidate.question_embedding,
        'ai_generated',
        v_candidate.test_scenario_id,
        v_generation_metadata,
        ARRAY['tenant']::text[],  -- 預設對象為租客
        TRUE  -- 預設啟用
    )
    RETURNING id INTO v_new_knowledge_id;

    -- 6. 更新候選狀態
    UPDATE ai_generated_knowledge_candidates
    SET status = 'approved',
        reviewed_by = p_reviewed_by,
        reviewed_at = NOW(),
        review_notes = p_review_notes,
        updated_at = NOW()
    WHERE id = p_candidate_id;

    -- 7. 插入 knowledge_intent_mapping（支援多意圖）
    IF v_candidate.intent_ids IS NOT NULL AND array_length(v_candidate.intent_ids, 1) > 0 THEN
        FOR i IN 1..array_length(v_candidate.intent_ids, 1) LOOP
            INSERT INTO knowledge_intent_mapping (
                knowledge_id,
                intent_id,
                intent_type,
                confidence,
                assigned_by,
                created_at,
                updated_at
            ) VALUES (
                v_new_knowledge_id,
                v_candidate.intent_ids[i],
                CASE WHEN i = 1 THEN 'primary' ELSE 'secondary' END,
                0.95,
                'reviewer',
                NOW(),
                NOW()
            );
        END LOOP;
    END IF;

    -- 8. 更新 test_scenario 的關聯
    UPDATE test_scenarios
    SET related_knowledge_ids = array_append(
            COALESCE(related_knowledge_ids, ARRAY[]::integer[]),
            v_new_knowledge_id
        ),
        updated_at = NOW()
    WHERE id = v_candidate.test_scenario_id;

    RETURN v_new_knowledge_id;
END;
$$;

COMMENT ON FUNCTION approve_ai_knowledge_candidate IS '批准 AI 生成的知識候選，轉為正式知識庫內容（4 參數版本，支援多意圖、embedding、編輯版本選擇）';

-- ========================================
-- 顯示統計資訊
-- ========================================

SELECT
    '✅ AI 知識管理系統已建立' AS status;
