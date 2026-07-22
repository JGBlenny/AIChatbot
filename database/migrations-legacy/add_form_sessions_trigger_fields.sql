-- ==========================================
-- 表單會話觸發資訊欄位遷移腳本
-- 版本: 1.3.0
-- 日期: 2026-01-11
-- 說明: 為 form_sessions 表新增 trigger_question 和 knowledge_id 欄位
-- ==========================================

BEGIN;

-- 檢查欄位是否已存在,如果不存在才新增
DO $$
BEGIN
    -- 新增 trigger_question 欄位(觸發表單的用戶問題)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_sessions' AND column_name = 'trigger_question'
    ) THEN
        ALTER TABLE form_sessions
        ADD COLUMN trigger_question TEXT;

        COMMENT ON COLUMN form_sessions.trigger_question IS '觸發表單的用戶問題(用於記錄用戶最初的需求)';
        RAISE NOTICE '✅ 新增 trigger_question 欄位';
    ELSE
        RAISE NOTICE 'ℹ️  trigger_question 欄位已存在,跳過';
    END IF;

    -- 新增 knowledge_id 欄位(關聯的知識ID)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'form_sessions' AND column_name = 'knowledge_id'
    ) THEN
        ALTER TABLE form_sessions
        ADD COLUMN knowledge_id INTEGER;

        COMMENT ON COLUMN form_sessions.knowledge_id IS '觸發表單的知識ID(用於追蹤表單來源)';
        RAISE NOTICE '✅ 新增 knowledge_id 欄位';
    ELSE
        RAISE NOTICE 'ℹ️  knowledge_id 欄位已存在,跳過';
    END IF;
END $$;

-- 新增索引(如果不存在)
CREATE INDEX IF NOT EXISTS idx_form_sessions_knowledge_id ON form_sessions(knowledge_id);

COMMIT;

-- ==========================================
-- 驗證遷移
-- ==========================================

-- 顯示新增的欄位
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'form_sessions'
    AND column_name IN ('trigger_question', 'knowledge_id')
ORDER BY ordinal_position;
