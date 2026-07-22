-- 修正 SOP 意圖 mapping table 的 FK 約束
-- 日期: 2026-04-14
-- 原因: 刪除意圖不應連帶刪除 SOP 的 mapping 紀錄

-- vendor_sop_item_intents.intent_id
ALTER TABLE vendor_sop_item_intents DROP CONSTRAINT IF EXISTS vendor_sop_item_intents_intent_id_fkey;
ALTER TABLE vendor_sop_item_intents ADD CONSTRAINT vendor_sop_item_intents_intent_id_fkey
  FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE SET NULL;

-- platform_sop_template_intents.intent_id
ALTER TABLE platform_sop_template_intents DROP CONSTRAINT IF EXISTS platform_sop_template_intents_intent_id_fkey;
ALTER TABLE platform_sop_template_intents ADD CONSTRAINT platform_sop_template_intents_intent_id_fkey
  FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE SET NULL;
