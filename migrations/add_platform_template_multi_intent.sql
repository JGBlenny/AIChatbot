-- Migration: 支援平台 SOP 範本多意圖關聯
-- Date: 2025-10-22
-- Description: 允許一個平台 SOP 範本關聯多個意圖

-- 1. 創建關聯表
CREATE TABLE IF NOT EXISTS platform_sop_template_intents (
    template_id INTEGER NOT NULL REFERENCES platform_sop_templates(id) ON DELETE CASCADE,
    intent_id INTEGER NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (template_id, intent_id)
);

-- 2. 創建索引以優化查詢
CREATE INDEX IF NOT EXISTS idx_platform_template_intents_template
    ON platform_sop_template_intents(template_id);

CREATE INDEX IF NOT EXISTS idx_platform_template_intents_intent
    ON platform_sop_template_intents(intent_id);

-- 3. 遷移現有數據
INSERT INTO platform_sop_template_intents (template_id, intent_id)
SELECT id, related_intent_id
FROM platform_sop_templates
WHERE related_intent_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- 4. 添加註釋
COMMENT ON TABLE platform_sop_template_intents IS '平台 SOP 範本與意圖的多對多關聯表';
COMMENT ON COLUMN platform_sop_template_intents.template_id IS '平台 SOP 範本 ID';
COMMENT ON COLUMN platform_sop_template_intents.intent_id IS '意圖 ID';

-- 5. 顯示遷移結果
SELECT
    COUNT(*) as migrated_associations,
    COUNT(DISTINCT template_id) as templates_with_intents,
    COUNT(DISTINCT intent_id) as unique_intents
FROM platform_sop_template_intents;
