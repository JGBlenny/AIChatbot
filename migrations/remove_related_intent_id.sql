-- Migration: 移除 vendor_sop_items 表的 related_intent_id 欄位
-- Date: 2025-10-22
-- Description: 移除已廢棄的 related_intent_id 欄位，全面使用 vendor_sop_item_intents 多對多關聯表

-- 1. 移除 related_intent_id 欄位
ALTER TABLE vendor_sop_items
DROP COLUMN IF EXISTS related_intent_id;

-- 2. 添加註釋
COMMENT ON TABLE vendor_sop_items IS 'Vendor SOP 項目表（使用 vendor_sop_item_intents 進行意圖關聯）';

-- 驗證：確認 vendor_sop_item_intents 表有資料
-- SELECT COUNT(*) FROM vendor_sop_item_intents;
