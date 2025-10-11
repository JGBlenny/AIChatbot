-- ================================================
-- Migration: Add auto-scenario creation trigger
-- Purpose: Automatically create test scenarios from high-frequency unclear questions
-- Date: 2025-10-12
-- ================================================

-- ========================================
-- 觸發器函數：自動創建測試情境
-- ========================================

CREATE OR REPLACE FUNCTION auto_create_test_scenario_from_unclear()
RETURNS TRIGGER AS $$
DECLARE
    v_scenario_id INTEGER;
    v_existing_scenario INTEGER;
BEGIN
    -- 只處理頻率達到 2 次或以上的問題
    IF NEW.frequency < 2 THEN
        RETURN NEW;
    END IF;

    -- 只在頻率增加時觸發（避免重複觸發）
    IF TG_OP = 'UPDATE' AND (OLD.frequency >= NEW.frequency) THEN
        RETURN NEW;
    END IF;

    -- 檢查是否已經創建過測試情境
    SELECT id INTO v_existing_scenario
    FROM test_scenarios
    WHERE source_question_id = NEW.id
    LIMIT 1;

    -- 如果已存在，跳過
    IF v_existing_scenario IS NOT NULL THEN
        RAISE NOTICE '⚠️  用戶問題 #% 已有對應的測試情境 #%，跳過創建', NEW.id, v_existing_scenario;
        RETURN NEW;
    END IF;

    -- 自動創建測試情境（pending_review 狀態）
    BEGIN
        SELECT create_test_scenario_from_unclear_question(
            p_unclear_question_id := NEW.id,
            p_expected_category := NEW.intent_type,
            p_difficulty := 'medium',
            p_created_by := 'auto_trigger'
        ) INTO v_scenario_id;

        RAISE NOTICE '✅ 自動創建測試情境 #% (來源：用戶問題 #%, 頻率：%次)',
            v_scenario_id, NEW.id, NEW.frequency;

    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING '❌ 自動創建測試情境失敗 (問題 #%): %', NEW.id, SQLERRM;
    END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- 創建觸發器
-- ========================================

-- 在 INSERT 時觸發（如果頻率直接 >= 2）
CREATE TRIGGER trigger_auto_create_scenario_on_insert
    AFTER INSERT ON unclear_questions
    FOR EACH ROW
    WHEN (NEW.frequency >= 2)
    EXECUTE FUNCTION auto_create_test_scenario_from_unclear();

-- 在 UPDATE 時觸發（頻率增加到 >= 2）
CREATE TRIGGER trigger_auto_create_scenario_on_update
    AFTER UPDATE OF frequency ON unclear_questions
    FOR EACH ROW
    WHEN (NEW.frequency >= 2 AND NEW.frequency > OLD.frequency)
    EXECUTE FUNCTION auto_create_test_scenario_from_unclear();

-- ========================================
-- 註解說明
-- ========================================

COMMENT ON FUNCTION auto_create_test_scenario_from_unclear IS
'自動將高頻率（>=2次）的 unclear_questions 轉換為 test_scenarios（待審核狀態）';

COMMENT ON TRIGGER trigger_auto_create_scenario_on_insert ON unclear_questions IS
'當插入新的 unclear_question 且頻率 >= 2 時，自動創建測試情境';

COMMENT ON TRIGGER trigger_auto_create_scenario_on_update ON unclear_questions IS
'當 unclear_question 的頻率增加到 >= 2 時，自動創建測試情境';

-- ========================================
-- 處理現有數據
-- ========================================

-- 為現有的高頻問題（frequency >= 2 且未創建測試情境）批量創建測試情境
DO $$
DECLARE
    v_unclear_record RECORD;
    v_scenario_id INTEGER;
    v_created_count INTEGER := 0;
    v_skipped_count INTEGER := 0;
BEGIN
    RAISE NOTICE '🔄 處理現有高頻用戶問題...';

    -- 遍歷所有符合條件的問題
    FOR v_unclear_record IN
        SELECT uq.id, uq.question, uq.frequency, uq.intent_type
        FROM unclear_questions uq
        WHERE uq.frequency >= 2
          AND uq.status IN ('pending', 'in_progress')
          AND NOT EXISTS (
              SELECT 1 FROM test_scenarios ts
              WHERE ts.source_question_id = uq.id
          )
        ORDER BY uq.frequency DESC
    LOOP
        BEGIN
            SELECT create_test_scenario_from_unclear_question(
                p_unclear_question_id := v_unclear_record.id,
                p_expected_category := v_unclear_record.intent_type,
                p_difficulty := 'medium',
                p_created_by := 'migration_batch'
            ) INTO v_scenario_id;

            v_created_count := v_created_count + 1;

            RAISE NOTICE '   ✅ 創建測試情境 #% (問題: "%" 頻率:%次)',
                v_scenario_id,
                LEFT(v_unclear_record.question, 30),
                v_unclear_record.frequency;

        EXCEPTION WHEN OTHERS THEN
            v_skipped_count := v_skipped_count + 1;
            RAISE WARNING '   ⚠️  跳過問題 #%: %', v_unclear_record.id, SQLERRM;
        END;
    END LOOP;

    RAISE NOTICE '✅ 批量處理完成：創建 % 個測試情境，跳過 % 個', v_created_count, v_skipped_count;
END $$;

COMMIT;
