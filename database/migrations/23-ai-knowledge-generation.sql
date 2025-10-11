-- Migration: AI 知識生成功能
-- 用途：支援從測試情境自動生成知識庫候選內容
-- 日期：2025-10-11

-- 1. 擴展 test_scenarios 表：追蹤是否有對應知識
ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS has_knowledge BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS linked_knowledge_ids INTEGER[],
ADD COLUMN IF NOT EXISTS knowledge_generation_requested BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS knowledge_generation_requested_at TIMESTAMP;

COMMENT ON COLUMN test_scenarios.has_knowledge IS '是否已有對應的知識庫內容';
COMMENT ON COLUMN test_scenarios.linked_knowledge_ids IS '關聯的知識 ID 陣列';
COMMENT ON COLUMN test_scenarios.knowledge_generation_requested IS '是否已請求 AI 生成知識';

-- 2. 擴展 knowledge_base 表：標註知識來源
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS source_test_scenario_id INTEGER REFERENCES test_scenarios(id),
ADD COLUMN IF NOT EXISTS generation_metadata JSONB,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

COMMENT ON COLUMN knowledge_base.source_type IS '知識來源類型: manual (人工), ai_generated (AI生成), imported (匯入), ai_assisted (AI輔助)';
COMMENT ON COLUMN knowledge_base.source_test_scenario_id IS '來源測試情境 ID（如果由測試情境生成）';
COMMENT ON COLUMN knowledge_base.generation_metadata IS 'AI 生成的詳細資訊: {model, prompt, confidence, reviewed_by, edited}';
COMMENT ON COLUMN knowledge_base.is_active IS '知識是否啟用';

-- 3. 建立 AI 生成知識候選表（審核前的暫存區）
CREATE TABLE IF NOT EXISTS ai_generated_knowledge_candidates (
    id SERIAL PRIMARY KEY,
    test_scenario_id INTEGER NOT NULL REFERENCES test_scenarios(id) ON DELETE CASCADE,

    -- 生成內容
    question TEXT NOT NULL,
    generated_answer TEXT NOT NULL,
    confidence_score DECIMAL(3,2),  -- AI 生成的信心度 (0.00-1.00)

    -- 生成詳情
    generation_prompt TEXT,         -- 使用的 prompt
    ai_model VARCHAR(50),            -- 使用的模型 (gpt-4, gpt-3.5-turbo)
    generation_reasoning TEXT,       -- AI 的推理過程
    suggested_sources TEXT[],        -- AI 建議的參考來源
    warnings TEXT[],                 -- AI 標註的風險警告

    -- 審核狀態
    status VARCHAR(20) DEFAULT 'pending_review',
    -- pending_review: 待審核
    -- needs_revision: 需要修訂
    -- approved: 已批准（轉為正式知識）
    -- rejected: 已拒絕

    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- 編輯記錄
    edited_question TEXT,            -- 審核者編輯後的問題
    edited_answer TEXT,              -- 審核者編輯後的答案
    edit_summary TEXT,               -- 編輯摘要（記錄主要修改）

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_candidates_test_scenario ON ai_generated_knowledge_candidates(test_scenario_id);
CREATE INDEX idx_ai_candidates_status ON ai_generated_knowledge_candidates(status);
CREATE INDEX idx_ai_candidates_created ON ai_generated_knowledge_candidates(created_at DESC);

COMMENT ON TABLE ai_generated_knowledge_candidates IS 'AI 生成的知識候選（審核前暫存）';

-- 4. 建立函數：檢查測試情境是否有對應知識
CREATE OR REPLACE FUNCTION check_test_scenario_has_knowledge(
    p_test_scenario_id INTEGER,
    p_similarity_threshold DECIMAL DEFAULT 0.75
)
RETURNS TABLE (
    has_knowledge BOOLEAN,
    matched_knowledge_ids INTEGER[],
    match_count INTEGER,
    highest_similarity DECIMAL,
    related_knowledge JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_test_question TEXT;
    v_test_embedding vector(1536);
    v_has_knowledge BOOLEAN;
    v_matched_ids INTEGER[];
    v_match_count INTEGER;
    v_highest_sim DECIMAL;
    v_related JSONB;
BEGIN
    -- 取得測試問題和 embedding
    SELECT test_question, question_embedding
    INTO v_test_question, v_test_embedding
    FROM test_scenarios
    WHERE id = p_test_scenario_id;

    IF v_test_question IS NULL THEN
        RAISE EXCEPTION '測試情境不存在: %', p_test_scenario_id;
    END IF;

    -- 如果沒有 embedding，無法進行向量搜尋
    IF v_test_embedding IS NULL THEN
        RETURN QUERY SELECT
            FALSE,
            ARRAY[]::INTEGER[],
            0,
            0.0::DECIMAL,
            '[]'::JSONB;
        RETURN;
    END IF;

    -- 搜尋相似的知識（使用向量相似度）
    WITH similar_knowledge AS (
        SELECT
            k.id,
            k.question_summary,
            k.answer,
            k.category,
            ROUND((1 - (k.embedding <=> v_test_embedding))::numeric, 4) as similarity
        FROM knowledge_base k
        WHERE k.embedding IS NOT NULL
        ORDER BY similarity DESC
        LIMIT 10
    )
    SELECT
        COUNT(*) FILTER (WHERE similarity >= p_similarity_threshold) > 0,
        ARRAY_AGG(id) FILTER (WHERE similarity >= p_similarity_threshold),
        COUNT(*) FILTER (WHERE similarity >= p_similarity_threshold),
        MAX(similarity),
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'id', id,
                'question', question_summary,
                'answer', LEFT(answer, 200),
                'category', category,
                'similarity', similarity
            )
            ORDER BY similarity DESC
        ) FILTER (WHERE similarity >= 0.60)  -- 保留中等相似的作為參考
    INTO v_has_knowledge, v_matched_ids, v_match_count, v_highest_sim, v_related
    FROM similar_knowledge;

    RETURN QUERY SELECT
        COALESCE(v_has_knowledge, FALSE),
        COALESCE(v_matched_ids, ARRAY[]::INTEGER[]),
        COALESCE(v_match_count, 0),
        COALESCE(v_highest_sim, 0.0),
        COALESCE(v_related, '[]'::JSONB);
END;
$$;

COMMENT ON FUNCTION check_test_scenario_has_knowledge IS
'檢查測試情境是否已有對應的知識庫內容（基於向量相似度）';

-- 5. 建立函數：批准 AI 候選並轉為正式知識
CREATE OR REPLACE FUNCTION approve_ai_knowledge_candidate(
    p_candidate_id INTEGER,
    p_reviewed_by VARCHAR(100),
    p_review_notes TEXT DEFAULT NULL,
    p_use_edited BOOLEAN DEFAULT TRUE  -- 是否使用編輯後的版本
)
RETURNS INTEGER  -- 返回新建立的 knowledge ID
LANGUAGE plpgsql
AS $$
DECLARE
    v_candidate RECORD;
    v_final_question TEXT;
    v_final_answer TEXT;
    v_new_knowledge_id INTEGER;
    v_generation_metadata JSONB;
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

    -- 3. 準備 generation_metadata
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

    -- 4. 插入正式知識庫（重用現有 embedding，後續可由系統重新生成）
    INSERT INTO knowledge_base (
        title,
        question_summary,
        answer,
        category,
        source_type,
        source_test_scenario_id,
        generation_metadata,
        audience
    )
    SELECT
        LEFT(v_final_question, 200),  -- title 欄位
        v_final_question,
        v_final_answer,
        ts.expected_category,
        'ai_generated',
        v_candidate.test_scenario_id,
        v_generation_metadata,
        'tenant'  -- 預設對象為租客
    FROM test_scenarios ts
    WHERE ts.id = v_candidate.test_scenario_id
    RETURNING id INTO v_new_knowledge_id;

    -- 5. 更新候選狀態
    UPDATE ai_generated_knowledge_candidates
    SET status = 'approved',
        reviewed_by = p_reviewed_by,
        reviewed_at = NOW(),
        review_notes = p_review_notes,
        updated_at = NOW()
    WHERE id = p_candidate_id;

    -- 6. 更新 test_scenario 的關聯
    UPDATE test_scenarios
    SET has_knowledge = TRUE,
        linked_knowledge_ids = ARRAY_APPEND(
            COALESCE(linked_knowledge_ids, ARRAY[]::INTEGER[]),
            v_new_knowledge_id
        )
    WHERE id = v_candidate.test_scenario_id;

    RETURN v_new_knowledge_id;
END;
$$;

COMMENT ON FUNCTION approve_ai_knowledge_candidate IS
'批准 AI 生成的知識候選，轉為正式知識庫內容';

-- 6. 建立視圖：待審核的 AI 知識候選
CREATE OR REPLACE VIEW v_pending_ai_knowledge_candidates AS
SELECT
    kc.id as candidate_id,
    kc.test_scenario_id,
    ts.test_question as original_test_question,
    ts.expected_category,
    ts.difficulty,
    kc.question,
    kc.generated_answer,
    kc.confidence_score,
    kc.ai_model,
    kc.warnings,
    kc.status,
    kc.created_at,
    kc.edited_answer IS NOT NULL as has_edits,
    -- 來源問題的頻率
    CASE
        WHEN ts.source_question_id IS NOT NULL
        THEN (SELECT frequency FROM unclear_questions WHERE id = ts.source_question_id)
        ELSE NULL
    END as source_question_frequency
FROM ai_generated_knowledge_candidates kc
INNER JOIN test_scenarios ts ON kc.test_scenario_id = ts.id
WHERE kc.status IN ('pending_review', 'needs_revision')
ORDER BY
    kc.status DESC,  -- needs_revision 優先
    source_question_frequency DESC NULLS LAST,  -- 高頻問題優先
    kc.created_at ASC;  -- 先進先出

COMMENT ON VIEW v_pending_ai_knowledge_candidates IS
'待審核的 AI 生成知識候選（按優先順序排序）';

-- 7. 建立視圖：AI 生成知識的統計
CREATE OR REPLACE VIEW v_ai_knowledge_generation_stats AS
SELECT
    COUNT(*) FILTER (WHERE status = 'pending_review') as pending_count,
    COUNT(*) FILTER (WHERE status = 'needs_revision') as needs_revision_count,
    COUNT(*) FILTER (WHERE status = 'approved') as approved_count,
    COUNT(*) FILTER (WHERE status = 'rejected') as rejected_count,
    ROUND(AVG(confidence_score) FILTER (WHERE status = 'approved'), 2) as avg_confidence_approved,
    ROUND(AVG(confidence_score) FILTER (WHERE status = 'rejected'), 2) as avg_confidence_rejected,
    COUNT(*) FILTER (WHERE status = 'approved' AND edited_answer IS NOT NULL) as approved_with_edits,
    COUNT(*) FILTER (WHERE status = 'approved' AND edited_answer IS NULL) as approved_without_edits
FROM ai_generated_knowledge_candidates;

COMMENT ON VIEW v_ai_knowledge_generation_stats IS
'AI 知識生成的統計資訊（審核通過率、編輯率等）';

-- 8. 觸發器：自動更新 updated_at
CREATE OR REPLACE FUNCTION update_ai_candidate_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ai_candidate_updated_at
BEFORE UPDATE ON ai_generated_knowledge_candidates
FOR EACH ROW
EXECUTE FUNCTION update_ai_candidate_updated_at();

-- 9. 權限設定（根據實際需求調整）
-- GRANT SELECT, INSERT, UPDATE ON ai_generated_knowledge_candidates TO knowledge_admin_role;
-- GRANT SELECT ON v_pending_ai_knowledge_candidates TO knowledge_admin_role;

-- 10. 測試查詢範例
/*
-- 檢查測試情境 #20 是否有對應知識
SELECT * FROM check_test_scenario_has_knowledge(20);

-- 查看待審核的 AI 候選
SELECT * FROM v_pending_ai_knowledge_candidates;

-- 查看 AI 生成統計
SELECT * FROM v_ai_knowledge_generation_stats;

-- 批准候選 #1
SELECT approve_ai_knowledge_candidate(1, 'admin_name', '已審核，答案正確');
*/
