-- ========================================
-- Migration: 為 knowledge_base 表新增表單觸發模式欄位
-- Date: 2026-01-27
-- Purpose: 統一 knowledge_base 與 vendor_sop_items 的表單觸發邏輯
-- ========================================

BEGIN;

-- 1. 新增 trigger_mode 欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS trigger_mode VARCHAR(20) DEFAULT 'none';

-- 2. 新增 immediate_prompt 欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS immediate_prompt TEXT;

-- 3. 添加檢查約束
ALTER TABLE knowledge_base
DROP CONSTRAINT IF EXISTS check_kb_trigger_mode;

ALTER TABLE knowledge_base
ADD CONSTRAINT check_kb_trigger_mode
CHECK (trigger_mode IN ('none', 'manual', 'immediate', 'auto'));

-- 4. 創建索引（優化查詢）
CREATE INDEX IF NOT EXISTS idx_kb_trigger_mode
ON knowledge_base(trigger_mode)
WHERE trigger_mode <> 'none';

-- 5. 數據遷移：根據現有 action_type 設置 trigger_mode
-- 邏輯：
--   - action_type='form_fill' 且有 form_id → trigger_mode='auto' (自動觸發，保持現有行為)
--   - action_type='form_then_api' 且有 form_id → trigger_mode='auto'
--   - 其他 → trigger_mode='none'

UPDATE knowledge_base
SET trigger_mode = CASE
    WHEN action_type IN ('form_fill', 'form_then_api') AND form_id IS NOT NULL THEN 'auto'
    ELSE 'none'
END
WHERE trigger_mode = 'none';  -- 只更新默認值的記錄

-- 6. 添加註釋
COMMENT ON COLUMN knowledge_base.trigger_mode IS '表單觸發模式：none(不觸發), manual(需觸發詞), immediate(主動詢問), auto(自動觸發)';
COMMENT ON COLUMN knowledge_base.immediate_prompt IS 'immediate 模式下的確認提示詞（如「需要我幫您填寫表單嗎？」）';

-- 7. 記錄遷移（如果 migration_history 表存在）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_history') THEN
        INSERT INTO migration_history (filename, applied_at, description)
        VALUES (
            'add_trigger_mode_to_knowledge_base.sql',
            NOW(),
            '為 knowledge_base 表新增 trigger_mode 和 immediate_prompt 欄位，統一表單觸發邏輯'
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
AND column_name IN ('trigger_mode', 'immediate_prompt')
ORDER BY ordinal_position;

-- 查看更新的記錄數量
SELECT
    trigger_mode,
    COUNT(*) as count
FROM knowledge_base
GROUP BY trigger_mode
ORDER BY trigger_mode;

-- 顯示有表單的知識記錄
SELECT
    id,
    question_summary,
    action_type,
    form_id,
    trigger_mode,
    immediate_prompt
FROM knowledge_base
WHERE form_id IS NOT NULL
LIMIT 5;
