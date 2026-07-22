-- 知識庫多業者支援：vendor_id → vendor_ids 陣列升級
-- 日期: 2026-03-11
-- 目的: 支援單一知識關聯多個業者

-- 1. 新增 vendor_ids 陣列欄位
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS vendor_ids INTEGER[];

-- 2. 遷移現有資料（將單一 vendor_id 轉為陣列）
UPDATE knowledge_base
SET vendor_ids = ARRAY[vendor_id]
WHERE vendor_id IS NOT NULL AND vendor_ids IS NULL;

-- 3. 為 vendor_ids 建立 GIN 索引以加速陣列查詢
CREATE INDEX IF NOT EXISTS idx_knowledge_base_vendor_ids ON knowledge_base USING GIN (vendor_ids);
