-- Migration 34: 修復審核流程 - 移除不存在的 expected_category 欄位
-- 日期: 2025-10-27
-- 問題: approve_ai_knowledge_candidate 函數引用了不存在的 ts.expected_category 欄位
-- 解決: 使用候選記錄中的 intent_ids，移除 expected_category 引用

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

    -- 3. 從候選記錄的 intent_ids 獲取第一個 intent（如果有的話）
    IF v_candidate.intent_ids IS NOT NULL AND array_length(v_candidate.intent_ids, 1) > 0 THEN
        v_intent_id := v_candidate.intent_ids[1];

        -- 從 intent 獲取 category
        SELECT name INTO v_category
        FROM intents
        WHERE id = v_intent_id AND is_enabled = TRUE;
    ELSE
        v_intent_id := NULL;
        v_category := NULL;
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

    -- 5. 插入正式知識庫（包含 embedding 和 intent_id）
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
    VALUES (
        LEFT(v_final_question, 200),  -- title 欄位
        v_final_question,
        v_final_answer,
        v_category,  -- 使用從 intent 獲取的 category
        v_intent_id,  -- 使用候選記錄中的 intent
        v_candidate.question_embedding,  -- 複製 embedding
        'ai_generated',
        v_candidate.test_scenario_id,
        v_generation_metadata,
        'tenant',  -- 預設對象為租客
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

    -- 7. 更新 test_scenario 的關聯
    UPDATE test_scenarios
    SET has_knowledge = TRUE,
        linked_knowledge_ids = ARRAY_APPEND(
            COALESCE(linked_knowledge_ids, ARRAY[]::INTEGER[]),
            v_new_knowledge_id
        )
    WHERE id = v_candidate.test_scenario_id;

    -- 8. 記錄日誌
    RAISE NOTICE '✅ 知識 ID % 已批准（來自候選 %），Intent: %, Category: %',
        v_new_knowledge_id, p_candidate_id, COALESCE(v_intent_id::TEXT, 'NULL'), COALESCE(v_category, 'NULL');

    RETURN v_new_knowledge_id;
END;
$$;

COMMENT ON FUNCTION approve_ai_knowledge_candidate IS '批准 AI 生成的知識候選，轉為正式知識庫內容（使用候選的 intent_ids）';

-- ====================
-- 2. 記錄 Migration
-- ====================

INSERT INTO schema_migrations (migration_file, description, executed_at)
VALUES ('34-fix-approval-remove-expected-category.sql', 'Fix approval function to remove non-existent expected_category column', NOW())
ON CONFLICT (migration_file) DO NOTHING;

-- ====================
-- 測試與驗證
-- ====================

-- 測試步驟：
-- 1. 確認函數已更新：
--    \df+ approve_ai_knowledge_candidate
-- 2. 在審核中心測試批准一個候選知識
-- 3. 驗證知識庫記錄：
--    SELECT id, question_summary, category, intent_id
--    FROM knowledge_base
--    WHERE source_type = 'ai_generated'
--    ORDER BY id DESC LIMIT 5;
