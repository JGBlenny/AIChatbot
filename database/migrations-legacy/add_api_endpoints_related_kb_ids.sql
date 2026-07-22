-- API Endpoints 新增 related_kb_ids 欄位
-- 日期: 2026-03-11
-- 目的: 關聯特定知識庫 ID 到 API 端點，支援多個 ID 陣列儲存

-- 1. 新增 related_kb_ids 陣列欄位
ALTER TABLE api_endpoints ADD COLUMN IF NOT EXISTS related_kb_ids INTEGER[];

-- 2. 為 related_kb_ids 建立 GIN 索引
CREATE INDEX IF NOT EXISTS idx_api_endpoints_related_kb_ids ON api_endpoints USING GIN (related_kb_ids);
