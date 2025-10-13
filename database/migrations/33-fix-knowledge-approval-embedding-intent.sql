-- Migration 33: 修復知識審核流程 - 自動生成 embedding 和關聯 intent
-- 日期: 2025-10-13
-- 問題: 審核通過 AI 生成的知識時，沒有複製 embedding 也沒有關聯 intent_id
-- 影響: 導致審核通過的知識無法被 RAG 檢索到

-- ====================
-- 1. 更新 approve_ai_knowledge_candidate 函數
-- ====================

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
    v_category TEXT;
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

    -- 3. 從 test_scenarios 獲取 category（用於查找 intent）
    SELECT ts.expected_category INTO v_category
    FROM test_scenarios ts
    WHERE ts.id = v_candidate.test_scenario_id;

    -- 4. 根據 category 查找對應的 intent_id
    IF v_category IS NOT NULL THEN
        SELECT id INTO v_intent_id
        FROM intents
        WHERE name = v_category AND is_enabled = TRUE
        LIMIT 1;
    END IF;

    -- 5. 準備 generation_metadata
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

    -- 6. 插入正式知識庫（包含 embedding 和 intent_id）
    INSERT INTO knowledge_base (
        title,
        question_summary,
        answer,
        category,
        intent_id,
        embedding,
        source_type,
        source_test_scenario_id,
        generation_metadata,
        audience,
        is_active
    )
    SELECT
        LEFT(v_final_question, 200),  -- title 欄位
        v_final_question,
        v_final_answer,
        ts.expected_category,
        v_intent_id,  -- 🔧 新增：關聯 intent
        v_candidate.question_embedding,  -- 🔧 新增：複製 embedding
        'ai_generated',
        v_candidate.test_scenario_id,
        v_generation_metadata,
        'tenant',  -- 預設對象為租客
        TRUE  -- 預設啟用
    FROM test_scenarios ts
    WHERE ts.id = v_candidate.test_scenario_id
    RETURNING id INTO v_new_knowledge_id;

    -- 7. 更新候選狀態
    UPDATE ai_generated_knowledge_candidates
    SET status = 'approved',
        reviewed_by = p_reviewed_by,
        reviewed_at = NOW(),
        review_notes = p_review_notes,
        updated_at = NOW()
    WHERE id = p_candidate_id;

    -- 8. 更新 test_scenario 的關聯
    UPDATE test_scenarios
    SET has_knowledge = TRUE,
        linked_knowledge_ids = ARRAY_APPEND(
            COALESCE(linked_knowledge_ids, ARRAY[]::INTEGER[]),
            v_new_knowledge_id
        )
    WHERE id = v_candidate.test_scenario_id;

    -- 9. 記錄日誌
    RAISE NOTICE '✅ 知識 ID % 已批准（來自候選 %），Intent: %', v_new_knowledge_id, p_candidate_id, COALESCE(v_intent_id::TEXT, 'NULL');

    RETURN v_new_knowledge_id;
END;
$$;

COMMENT ON FUNCTION approve_ai_knowledge_candidate IS '批准 AI 生成的知識候選，轉為正式知識庫內容（包含 embedding 和 intent 關聯）';

-- ====================
-- 2. 記錄 Migration
-- ====================

INSERT INTO schema_migrations (migration_file, description, executed_at)
VALUES ('33-fix-knowledge-approval-embedding-intent.sql', 'Fix knowledge approval to include embedding and intent_id', NOW())
ON CONFLICT (migration_file) DO NOTHING;

-- ====================
-- 測試與驗證建議
-- ====================

-- 測試步驟：
-- 1. 在測試情境中 AI 生成知識
-- 2. 在審核中心審核通過
-- 3. 驗證知識庫是否有 embedding 和 intent_id：
--    SELECT id, question_summary, intent_id, LENGTH(embedding::text) as embedding_length
--    FROM knowledge_base WHERE source_type = 'ai_generated' ORDER BY id DESC LIMIT 5;
-- 4. 在 chat-test 測試是否能正確回答
