-- ============================================================
-- trigger-vocabulary-debt M2 Rollback（spec trigger-vocabulary-debt 任務 4.1）
--
-- 依 database/migrations/add_knowledge_form_auto_option.sql 原始定義
-- 重建三欄 + CHECK 約束 + 索引 + 預設值。
-- 注意：資料不回復（僅重建結構）。
-- 冪等：ADD COLUMN IF NOT EXISTS、IF NOT EXISTS。
-- ============================================================

-- 1. 重建 trigger_form_condition 欄位（VARCHAR(20)，預設 'always'）
ALTER TABLE knowledge_base
    ADD COLUMN IF NOT EXISTS trigger_form_condition VARCHAR(20) DEFAULT 'always';

-- 2. 重建 trigger_conditions 欄位（JSONB，無預設）
ALTER TABLE knowledge_base
    ADD COLUMN IF NOT EXISTS trigger_conditions JSONB;

-- 3. 重建 auto_keywords 欄位（JSONB，含固定預設值）
ALTER TABLE knowledge_base
    ADD COLUMN IF NOT EXISTS auto_keywords JSONB DEFAULT '{
    "action_words": ["申請", "辦理", "報名", "預約", "登記", "提交", "要求"],
    "query_words": ["多少", "什麼", "哪裡", "何時", "是否", "有沒有", "怎麼"]
}'::jsonb;

-- 4. 重建 CHECK 約束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_trigger_form_condition'
          AND conrelid = 'knowledge_base'::regclass
    ) THEN
        ALTER TABLE knowledge_base
            ADD CONSTRAINT check_trigger_form_condition
            CHECK (trigger_form_condition IN ('always', 'auto', 'never', 'conditional'));
        RAISE NOTICE '✅ check_trigger_form_condition 約束已重建';
    ELSE
        RAISE NOTICE 'ℹ️ check_trigger_form_condition 約束已存在';
    END IF;
END $$;

-- 5. 重建索引
CREATE INDEX IF NOT EXISTS idx_kb_trigger_form_condition
    ON knowledge_base(trigger_form_condition)
    WHERE form_id IS NOT NULL;

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

    IF col_count = 3 AND idx_count = 1 AND con_count = 1 THEN
        RAISE NOTICE '✅ Rollback 完成：三欄 + 索引 + 約束已重建（資料不回復）';
    ELSE
        RAISE EXCEPTION '❌ Rollback 自檢失敗（欄位 %/3，索引 %/1，約束 %/1）', col_count, idx_count, con_count;
    END IF;
END $$;
