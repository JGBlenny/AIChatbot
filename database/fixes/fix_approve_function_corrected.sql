-- 修復 approve_ai_knowledge_candidate 函數
-- 修正：
-- 1. 添加第 4 個參數 p_use_edited
-- 2. 將 linked_knowledge_ids 改為 related_knowledge_ids
-- 3. 移除 has_knowledge 欄位引用（該欄位不存在）

CREATE OR REPLACE FUNCTION public.approve_ai_knowledge_candidate(
    p_candidate_id integer,
    p_reviewed_by character varying,
    p_review_notes text DEFAULT NULL::text,
    p_use_edited boolean DEFAULT true
)
RETURNS integer
LANGUAGE plpgsql
AS $function$
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
                CASE WHEN i = 1 THEN 'primary' ELSE 'secondary' END,  -- 第一個為主要意圖
                0.95,  -- 人工審核批准的意圖，給予高信心度
                'reviewer',
                NOW(),
                NOW()
            );
        END LOOP;
    END IF;

    -- 8. 更新 test_scenario 的關聯
    -- 修正：使用 related_knowledge_ids 而非 linked_knowledge_ids
    -- 移除：has_knowledge 欄位不存在
    UPDATE test_scenarios
    SET related_knowledge_ids = array_append(
            COALESCE(related_knowledge_ids, ARRAY[]::integer[]),
            v_new_knowledge_id
        ),
        updated_at = NOW()
    WHERE id = v_candidate.test_scenario_id;

    RETURN v_new_knowledge_id;
END;
$function$;

COMMENT ON FUNCTION approve_ai_knowledge_candidate IS '批准 AI 生成的知識候選，轉為正式知識庫內容（4 參數版本，支援多意圖，使用 related_knowledge_ids）';

-- 顯示修復訊息
SELECT '✅ approve_ai_knowledge_candidate 函數已更新' as status;
SELECT '   - 參數：4 個（candidate_id, reviewed_by, review_notes, use_edited）' as info
UNION ALL
SELECT '   - 修正：linked_knowledge_ids → related_knowledge_ids'
UNION ALL
SELECT '   - 移除：has_knowledge 欄位引用';
