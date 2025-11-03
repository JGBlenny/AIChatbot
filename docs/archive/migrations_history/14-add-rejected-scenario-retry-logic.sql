-- ================================================
-- Migration: Add rejected scenario retry logic
-- Purpose: Allow re-creation of test scenarios for rejected high-frequency questions
-- Date: 2025-10-12
-- ================================================

-- ========================================
-- 步驟 1: 修改創建函數，添加 allow_retry 參數
-- ========================================

CREATE OR REPLACE FUNCTION create_test_scenario_from_unclear_question(
    p_unclear_question_id INTEGER,
    p_expected_category VARCHAR(100) DEFAULT NULL,
    p_difficulty VARCHAR(20) DEFAULT 'medium',
    p_created_by VARCHAR(100) DEFAULT 'system',
    p_allow_retry BOOLEAN DEFAULT false  -- 新增：允許重試參數
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

    -- 2. 檢查是否已經存在相同 source_question_id 的 test_scenario
    SELECT id, status
    INTO v_existing_scenario_id, v_existing_status
    FROM test_scenarios
    WHERE source_question_id = p_unclear_question_id
    ORDER BY created_at DESC
    LIMIT 1;

    -- 3. 如果已存在，根據狀態決定處理方式
    IF v_existing_scenario_id IS NOT NULL THEN
        -- 3a. pending_review: 直接返回現有 ID
        IF v_existing_status = 'pending_review' THEN
            RAISE NOTICE '測試情境已存在且待審核中: test_scenario #%, 直接返回', v_existing_scenario_id;
            RETURN v_existing_scenario_id;
        END IF;

        -- 3b. approved: 提示已審核通過
        IF v_existing_status = 'approved' THEN
            RAISE EXCEPTION '測試情境已審核通過: test_scenario #%, 無需重複建立', v_existing_scenario_id;
        END IF;

        -- 3c. rejected: 根據 allow_retry 參數決定
        IF v_existing_status = 'rejected' THEN
            IF p_allow_retry THEN
                -- 允許重試：繼續創建新情境
                RAISE NOTICE '允許重試：舊情境 #% 已被拒絕，創建新情境', v_existing_scenario_id;
            ELSE
                -- 不允許重試：拋出異常
                RAISE EXCEPTION '測試情境已被拒絕: test_scenario #%. 如需重新審核，請先將該記錄狀態改為 draft 或直接刪除舊記錄。', v_existing_scenario_id;
            END IF;
        END IF;
    END IF;

    -- 4. 建立新的測試情境
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
        FORMAT('從用戶問題 #%s 創建，問題被問 %s 次%s',
            p_unclear_question_id,
            (SELECT frequency FROM unclear_questions WHERE id = p_unclear_question_id),
            CASE WHEN v_existing_scenario_id IS NOT NULL
                THEN FORMAT(' (原情境 #%s 已被拒絕)', v_existing_scenario_id)
                ELSE ''
            END)
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

-- ========================================
-- 步驟 2: 更新觸發器函數：添加 rejected 情境的高頻重試邏輯
-- ========================================

CREATE OR REPLACE FUNCTION auto_create_test_scenario_from_unclear()
RETURNS TRIGGER AS $$
DECLARE
    v_scenario_id INTEGER;
    v_existing_scenario INTEGER;
    v_scenario_status VARCHAR(20);
    v_high_freq_threshold INTEGER := 5;  -- 高頻重試閾值
BEGIN
    -- 只處理頻率達到 2 次或以上的問題
    IF NEW.frequency < 2 THEN
        RETURN NEW;
    END IF;

    -- 只在頻率增加時觸發（避免重複觸發）
    IF TG_OP = 'UPDATE' AND (OLD.frequency >= NEW.frequency) THEN
        RETURN NEW;
    END IF;

    -- 檢查是否已經創建過測試情境，並獲取其狀態
    SELECT id, status INTO v_existing_scenario, v_scenario_status
    FROM test_scenarios
    WHERE source_question_id = NEW.id
    ORDER BY created_at DESC  -- 取最新的情境
    LIMIT 1;

    -- 如果已存在情境，進行狀態判斷
    IF v_existing_scenario IS NOT NULL THEN
        -- 情況1：rejected 情境 + 達到高頻閾值 = 允許重新創建
        IF v_scenario_status = 'rejected' AND NEW.frequency >= v_high_freq_threshold THEN
            RAISE NOTICE '🔄 用戶問題 #% 的情境 #% 曾被拒絕，但頻率已達 %次（閾值：%），允許重新創建',
                NEW.id, v_existing_scenario, NEW.frequency, v_high_freq_threshold;
            -- 繼續執行創建邏輯
        ELSE
            -- 情況2：其他狀態（pending_review, approved）或未達閾值 = 跳過創建
            RAISE NOTICE '⚠️  用戶問題 #% 已有對應的測試情境 #%（狀態：%），跳過創建',
                NEW.id, v_existing_scenario, v_scenario_status;
            RETURN NEW;
        END IF;
    END IF;

    -- 自動創建測試情境（pending_review 狀態）
    -- 如果是重試場景，傳入 allow_retry = true
    BEGIN
        SELECT create_test_scenario_from_unclear_question(
            p_unclear_question_id := NEW.id,
            p_expected_category := NEW.intent_type,
            p_difficulty := 'medium',
            p_created_by := 'auto_trigger',
            p_allow_retry := (v_existing_scenario IS NOT NULL AND v_scenario_status = 'rejected')
        ) INTO v_scenario_id;

        IF v_existing_scenario IS NOT NULL AND v_scenario_status = 'rejected' THEN
            RAISE NOTICE '✅ 重新創建測試情境 #% (來源：用戶問題 #%, 頻率：%次，原情境 #% 已被拒絕)',
                v_scenario_id, NEW.id, NEW.frequency, v_existing_scenario;
        ELSE
            RAISE NOTICE '✅ 自動創建測試情境 #% (來源：用戶問題 #%, 頻率：%次)',
                v_scenario_id, NEW.id, NEW.frequency;
        END IF;

    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING '❌ 自動創建測試情境失敗 (問題 #%): %', NEW.id, SQLERRM;
    END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- 更新註解說明
-- ========================================

COMMENT ON FUNCTION auto_create_test_scenario_from_unclear IS
'自動將高頻率（>=2次）的 unclear_questions 轉換為 test_scenarios。
對於 rejected 情境，當頻率達到更高閾值（>=5次）時，允許重新創建。';

-- ========================================
-- 測試場景
-- ========================================

-- 測試說明：
-- 1. 頻率 2 → 創建情境 A → 審核員拒絕
-- 2. 頻率 3-4 → 不會重新創建（未達閾值）
-- 3. 頻率 5 → 重新創建情境 B（高頻重試）
-- 4. 情境 B 如果批准 → 不會再創建第三個

COMMIT;
