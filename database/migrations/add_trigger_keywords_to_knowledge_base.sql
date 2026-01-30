-- ========================================
-- Migration: 為 knowledge_base 表新增 trigger_keywords 欄位
-- Date: 2026-01-30
-- Purpose: 完善 knowledge_base 表單觸發邏輯，支援 manual 模式的觸發關鍵詞
-- ========================================

BEGIN;

-- 1. 新增 trigger_keywords 欄位（與 vendor_sop_items 一致）
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS trigger_keywords TEXT[];

-- 2. 添加註釋
COMMENT ON COLUMN knowledge_base.trigger_keywords IS '觸發關鍵詞陣列。manual模式：自定義（例如：["還是不行", "試過了"]）；immediate模式：通用肯定詞（["是", "要", "好"]）';

-- 3. 創建索引（優化查詢）
CREATE INDEX IF NOT EXISTS idx_kb_trigger_keywords
ON knowledge_base USING GIN (trigger_keywords)
WHERE trigger_keywords IS NOT NULL;

-- 4. 記錄遷移（如果 migration_history 表存在）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_history') THEN
        INSERT INTO migration_history (filename, applied_at, description)
        VALUES (
            'add_trigger_keywords_to_knowledge_base.sql',
            NOW(),
            '為 knowledge_base 表新增 trigger_keywords 欄位，支援 manual 模式的觸發關鍵詞'
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
AND column_name = 'trigger_keywords'
ORDER BY ordinal_position;

-- 顯示有 trigger_mode 但沒有 trigger_keywords 的記錄
SELECT
    id,
    question_summary,
    action_type,
    trigger_mode,
    trigger_keywords
FROM knowledge_base
WHERE trigger_mode IN ('manual', 'immediate')
LIMIT 10;
