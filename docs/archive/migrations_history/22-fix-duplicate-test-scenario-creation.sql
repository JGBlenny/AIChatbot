-- 修復：防止同一個 unclear_question 重複建立 test_scenario
-- 問題：審核拒絕後，如果頻率繼續增加，可能會再次手動建立相同的測試情境

-- 1. 先新增唯一約束（可選，較嚴格）
-- 注意：這會防止同一個 source_question_id 建立多個 test_scenario
-- 如果已有重複資料，此指令會失敗
-- ALTER TABLE test_scenarios
-- ADD CONSTRAINT unique_source_question_id UNIQUE (source_question_id);

-- 2. 修改建立函數，加入重複檢查
CREATE OR REPLACE FUNCTION create_test_scenario_from_unclear_question(
    p_unclear_question_id INTEGER,
    p_expected_category VARCHAR(100) DEFAULT NULL,
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

        -- 3c. 如果狀態是 rejected，詢問是否要重新建立
        -- 選項 A：拋出異常，需要手動處理
        IF v_existing_status = 'rejected' THEN
            RAISE EXCEPTION '測試情境已被拒絕: test_scenario #%. 如需重新審核，請先將該記錄狀態改為 draft 或直接刪除舊記錄。', v_existing_scenario_id;
        END IF;

        -- 選項 B（替代方案）：自動將舊記錄改為 draft，建立新記錄
        -- IF v_existing_status = 'rejected' THEN
        --     UPDATE test_scenarios
        --     SET status = 'draft',
        --         notes = COALESCE(notes || E'\n', '') || FORMAT('[%s] 因頻率增加而重新審核', NOW())
        --     WHERE id = v_existing_scenario_id;
        --
        --     RAISE NOTICE '已將舊的被拒絕記錄 #% 改為 draft，現在建立新的待審核記錄', v_existing_scenario_id;
        -- END IF;
    END IF;

    -- 4. 建立新的測試情境（只有在沒有 pending_review/approved 記錄時才會執行到這裡）
    INSERT INTO test_scenarios (
        test_question,
        expected_category,
        difficulty,
        status,
        source,
        source_question_id,
        created_by,
        notes
    ) VALUES (
        v_question,
        COALESCE(p_expected_category, v_intent_type),
        p_difficulty,
        'pending_review',
        'user_question',
        p_unclear_question_id,
        p_created_by,
        FORMAT('從用戶問題 #%s 創建，問題被問 %s 次',
            p_unclear_question_id,
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

-- 3. 建立輔助函數：重新開啟已拒絕的測試情境審核
CREATE OR REPLACE FUNCTION reopen_rejected_test_scenario(
    p_scenario_id INTEGER,
    p_reopened_by VARCHAR(100) DEFAULT 'system'
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status VARCHAR(20);
BEGIN
    -- 檢查當前狀態
    SELECT status INTO v_current_status
    FROM test_scenarios
    WHERE id = p_scenario_id;

    IF v_current_status IS NULL THEN
        RAISE EXCEPTION '測試情境不存在: #%', p_scenario_id;
    END IF;

    IF v_current_status != 'rejected' THEN
        RAISE EXCEPTION '只能重新開啟狀態為 rejected 的測試情境，當前狀態: %', v_current_status;
    END IF;

    -- 重新開啟：改回 pending_review
    UPDATE test_scenarios
    SET
        status = 'pending_review',
        reviewed_by = NULL,
        reviewed_at = NULL,
        review_notes = COALESCE(review_notes || E'\n\n', '') ||
                       FORMAT('[%s] 由 %s 重新開啟審核', NOW(), p_reopened_by)
    WHERE id = p_scenario_id;

    RETURN TRUE;
END;
$$;

-- 4. 建立視圖：顯示有重複 source_question_id 的測試情境
CREATE OR REPLACE VIEW v_duplicate_test_scenarios AS
SELECT
    ts1.source_question_id,
    uq.question AS unclear_question,
    uq.frequency AS current_frequency,
    COUNT(ts1.id) AS scenario_count,
    STRING_AGG(
        FORMAT('ID:%s (status:%s, created:%s)',
            ts1.id,
            ts1.status,
            ts1.created_at::date
        ),
        ', '
        ORDER BY ts1.created_at DESC
    ) AS scenarios
FROM test_scenarios ts1
INNER JOIN unclear_questions uq ON ts1.source_question_id = uq.id
WHERE ts1.source_question_id IS NOT NULL
GROUP BY ts1.source_question_id, uq.question, uq.frequency
HAVING COUNT(ts1.id) > 1
ORDER BY COUNT(ts1.id) DESC, uq.frequency DESC;

COMMENT ON FUNCTION create_test_scenario_from_unclear_question IS
'從 unclear_question 建立測試情境（已加入防重複檢查）';

COMMENT ON FUNCTION reopen_rejected_test_scenario IS
'重新開啟已拒絕的測試情境審核';

COMMENT ON VIEW v_duplicate_test_scenarios IS
'顯示有重複 source_question_id 的測試情境（用於檢測異常）';
