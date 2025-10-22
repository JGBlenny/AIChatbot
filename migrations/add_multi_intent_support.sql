-- Migration: 支援 SOP 項目多意圖關聯
-- Date: 2025-10-22
-- Description: 允許一個 SOP 項目關聯多個意圖

-- 1. 創建關聯表
CREATE TABLE IF NOT EXISTS vendor_sop_item_intents (
    sop_item_id INTEGER NOT NULL REFERENCES vendor_sop_items(id) ON DELETE CASCADE,
    intent_id INTEGER NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sop_item_id, intent_id)
);

-- 2. 創建索引以優化查詢
CREATE INDEX IF NOT EXISTS idx_sop_item_intents_item
    ON vendor_sop_item_intents(sop_item_id);

CREATE INDEX IF NOT EXISTS idx_sop_item_intents_intent
    ON vendor_sop_item_intents(intent_id);

-- 3. 遷移現有數據
INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id)
SELECT id, related_intent_id
FROM vendor_sop_items
WHERE related_intent_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- 4. 添加註釋
COMMENT ON TABLE vendor_sop_item_intents IS 'SOP 項目與意圖的多對多關聯表';
COMMENT ON COLUMN vendor_sop_item_intents.sop_item_id IS 'SOP 項目 ID';
COMMENT ON COLUMN vendor_sop_item_intents.intent_id IS '意圖 ID';

-- 注意：暫時保留 vendor_sop_items.related_intent_id 欄位以向下兼容
-- 未來可以在確認新系統穩定後移除
