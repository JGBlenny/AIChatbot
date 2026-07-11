-- ============================================================
-- trigger-vocabulary-debt M2：刪除三個死欄位（spec trigger-vocabulary-debt 任務 4.1）
--
-- 刪除對象：
--   knowledge_base.trigger_form_condition
--   knowledge_base.trigger_conditions
--   knowledge_base.auto_keywords
--
-- 佐證（spec gap-analysis）：
--   - 全庫 grep 零程式碼讀取（.py/.vue/.js/.ts/.sql）
--   - 資料全為預設值（trigger_form_condition='always'、JSONB 為固定模板）
--   - 零資訊量，視同空欄位
--
-- 資料不可回復已接受。prod 由使用者手動執行。
-- 冪等：DROP … IF EXISTS。
--
-- ⚠️  破壞性 migration：prod 由使用者手動執行，不得由自動化流程觸發 ⚠️
-- ============================================================

-- 1. 移除 CHECK 約束（依賴欄位，須先於欄位刪除）
ALTER TABLE knowledge_base
    DROP CONSTRAINT IF EXISTS check_trigger_form_condition;

-- 2. 移除索引
DROP INDEX IF EXISTS idx_kb_trigger_form_condition;

-- 3. 刪除三個死欄位
ALTER TABLE knowledge_base
    DROP COLUMN IF EXISTS trigger_form_condition,
    DROP COLUMN IF EXISTS trigger_conditions,
    DROP COLUMN IF EXISTS auto_keywords;

-- 自檢
DO $$
DECLARE
    col_count INT;
    idx_count INT;
    con_count INT;
BEGIN
    SELECT count(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'knowledge_base'
      AND column_name IN ('trigger_form_condition', 'trigger_conditions', 'auto_keywords');

    SELECT count(*) INTO idx_count
    FROM pg_indexes
    WHERE tablename = 'knowledge_base'
      AND indexname = 'idx_kb_trigger_form_condition';

    SELECT count(*) INTO con_count
    FROM pg_constraint
    WHERE conrelid = 'knowledge_base'::regclass
      AND conname = 'check_trigger_form_condition';

    IF col_count = 0 AND idx_count = 0 AND con_count = 0 THEN
        RAISE NOTICE '✅ M2 完成：trigger_form_condition / trigger_conditions / auto_keywords 已刪除，約束與索引已移除';
    ELSE
        RAISE EXCEPTION '❌ M2 自檢失敗：仍有殘留（欄位 %，索引 %，約束 %）', col_count, idx_count, con_count;
    END IF;
END $$;
