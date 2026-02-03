-- ========================================
-- Migration: 為 knowledge_base 表新增 followup_prompt 欄位
-- Date: 2026-01-30
-- Purpose: 補齊 knowledge_base 後續動作功能，與 platform_sop_templates 對齊
-- ========================================

BEGIN;

-- 1. 新增 followup_prompt 欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS followup_prompt TEXT;

-- 2. 添加註釋
COMMENT ON COLUMN knowledge_base.followup_prompt IS '後續動作的提示詞，在觸發表單/API 前顯示（例如：「好的，我來協助您填寫表單」）';

-- 3. 記錄遷移（如果 migration_history 表存在）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_history') THEN
        INSERT INTO migration_history (filename, applied_at, description)
        VALUES (
            'add_followup_prompt_to_knowledge_base.sql',
            NOW(),
            '為 knowledge_base 表新增 followup_prompt 欄位，補齊後續動作功能'
        ) ON CONFLICT (filename) DO UPDATE
        SET applied_at = NOW(), description = EXCLUDED.description;
    ELSE
        RAISE NOTICE 'migration_history 表不存在，跳過記錄';
    END IF;
END $$;

COMMIT;

-- ========================================
-- 驗證遷移結果
-- ========================================

-- 查看新增欄位
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'knowledge_base'
AND column_name = 'followup_prompt'
ORDER BY ordinal_position;

-- 顯示有後續動作的知識記錄
SELECT
    id,
    question_summary,
    action_type,
    trigger_mode,
    followup_prompt
FROM knowledge_base
WHERE action_type IN ('form_fill', 'api_call', 'form_then_api')
LIMIT 10;
