-- 更新測試情境創建函數：移除 expected_category 參數
-- 原因：測試情境簡化，不再使用 expected_category 字段（已在 40-simplify-test-scenarios-for-llm-eval.sql 中移除）

-- 更新函數：移除 p_expected_category 參數
CREATE OR REPLACE FUNCTION create_test_scenario_from_unclear_question(
    p_unclear_question_id INTEGER,
    p_difficulty VARCHAR(20) DEFAULT 'medium',
    p_created_by VARCHAR(100) DEFAULT 'system'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_scenario_id INTEGER;
    v_question TEXT;
    v_intent_type VARCHAR(50);
    v_existing_scenario_id INTEGER;
    v_existing_status VARCHAR(20);
BEGIN
    -- 1. 檢查 unclear_question 是否存在
    SELECT question, intent_type
    INTO v_question, v_intent_type
    FROM unclear_questions
    WHERE id = p_unclear_question_id;

    IF v_question IS NULL THEN
        RAISE EXCEPTION 'Unclear question not found: %', p_unclear_question_id;
    END IF;

    -- 2. ⭐ 檢查是否已經存在相同 source_question_id 的 test_scenario
    SELECT id, status
    INTO v_existing_scenario_id, v_existing_status
    FROM test_scenarios
    WHERE source_question_id = p_unclear_question_id
    ORDER BY created_at DESC
    LIMIT 1;

    -- 3. 如果已存在，根據狀態決定處理方式
    IF v_existing_scenario_id IS NOT NULL THEN
        -- 3a. 如果狀態是 pending_review，直接返回現有 ID（避免重複建立）
        IF v_existing_status = 'pending_review' THEN
            RAISE NOTICE '測試情境已存在且待審核中: test_scenario #%, 直接返回', v_existing_scenario_id;
            RETURN v_existing_scenario_id;
        END IF;

        -- 3b. 如果狀態是 approved，提示已審核通過
        IF v_existing_status = 'approved' THEN
            RAISE EXCEPTION '測試情境已審核通過: test_scenario #%, 無需重複建立', v_existing_scenario_id;
        END IF;

        -- 3c. 如果狀態是 rejected，拋出異常
        IF v_existing_status = 'rejected' THEN
            RAISE EXCEPTION '測試情境已被拒絕: test_scenario #%. 如需重新審核，請先將該記錄狀態改為 draft 或直接刪除舊記錄。', v_existing_scenario_id;
        END IF;
    END IF;

    -- 4. 建立新的測試情境（只有在沒有 pending_review/approved 記錄時才會執行到這裡）
    -- 注意：移除了 expected_category 字段
    INSERT INTO test_scenarios (
        test_question,
        difficulty,
        status,
        source,
        source_question_id,
        created_by,
        notes
    ) VALUES (
        v_question,
        p_difficulty,
        'pending_review',
        'user_question',
        p_unclear_question_id,
        p_created_by,
        FORMAT('從用戶問題 #%s 創建（意圖類型: %s），問題被問 %s 次',
            p_unclear_question_id,
            v_intent_type,
            (SELECT frequency FROM unclear_questions WHERE id = p_unclear_question_id))
    )
    RETURNING id INTO v_scenario_id;

    -- 5. 更新 unclear_questions 的處理狀態
    UPDATE unclear_questions
    SET
        status = 'in_progress',
        resolution_note = FORMAT('已創建測試情境 #%s，待審核', v_scenario_id),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_unclear_question_id;

    RETURN v_scenario_id;
END;
$$;

COMMENT ON FUNCTION create_test_scenario_from_unclear_question IS '
從用戶問題創建測試情境（已移除 expected_category 參數）
參數：
- p_unclear_question_id: 用戶問題 ID
- p_difficulty: 難度（easy/medium/hard，默認 medium）
- p_created_by: 創建者（默認 system）
';
