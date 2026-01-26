-- ============================================
-- 遷移: 為 Platform SOP Templates 添加流程配置欄位
-- 日期: 2026-01-24
-- 說明: 添加 trigger_mode, next_action 等流程配置欄位
-- ============================================

BEGIN;

-- 1. 添加觸發模式欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS trigger_mode VARCHAR(20) DEFAULT 'none';

-- 2. 添加後續動作欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS next_action VARCHAR(50) DEFAULT 'none';

-- 3. 添加表單 ID 欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS next_form_id VARCHAR(100);

-- 4. 添加 API 配置欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS next_api_config JSONB;

-- 5. 添加觸發關鍵詞欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS trigger_keywords TEXT[];

-- 6. 添加立即確認提示詞欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS immediate_prompt TEXT;

-- 7. 添加後續提示詞欄位
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS followup_prompt TEXT;

-- 8. 添加約束 (trigger_mode)
ALTER TABLE platform_sop_templates
DROP CONSTRAINT IF EXISTS check_trigger_mode;

ALTER TABLE platform_sop_templates
ADD CONSTRAINT check_trigger_mode
CHECK (trigger_mode IN ('none', 'manual', 'immediate', 'auto'));

-- 9. 添加約束 (next_action)
ALTER TABLE platform_sop_templates
DROP CONSTRAINT IF EXISTS check_next_action;

ALTER TABLE platform_sop_templates
ADD CONSTRAINT check_next_action
CHECK (next_action IN ('none', 'form_fill', 'api_call', 'form_then_api'));

-- 10. 添加索引以提升查詢效能
CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_trigger_mode
ON platform_sop_templates(trigger_mode)
WHERE trigger_mode <> 'none';

CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_next_action
ON platform_sop_templates(next_action)
WHERE next_action <> 'none';

-- 11. 註釋
COMMENT ON COLUMN platform_sop_templates.trigger_mode IS '觸發模式: none (資訊型), manual (排查型), immediate (緊急型), auto (自動執行型)';
COMMENT ON COLUMN platform_sop_templates.next_action IS '後續動作: none (無), form_fill (觸發表單), api_call (調用API), form_then_api (先填表單再調用API)';
COMMENT ON COLUMN platform_sop_templates.trigger_keywords IS '觸發關鍵詞（manual 模式使用）';
COMMENT ON COLUMN platform_sop_templates.immediate_prompt IS '確認提示詞（immediate 模式使用）';
COMMENT ON COLUMN platform_sop_templates.followup_prompt IS '後續提示詞（觸發後續動作時顯示）';
COMMENT ON COLUMN platform_sop_templates.next_form_id IS '關聯表單 ID (form_fill, form_then_api 使用)';
COMMENT ON COLUMN platform_sop_templates.next_api_config IS 'API 配置 JSON (api_call, form_then_api 使用)';

COMMIT;

-- 驗證
SELECT
  column_name,
  data_type,
  column_default,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'platform_sop_templates'
  AND column_name IN (
    'trigger_mode',
    'next_action',
    'trigger_keywords',
    'immediate_prompt',
    'followup_prompt',
    'next_form_id',
    'next_api_config'
  )
ORDER BY column_name;
