-- Migration: 38-add-target-user.sql
-- 目的: 新增 target_user 欄位，用於區分知識適用的用戶類型
-- 說明:
--   - target_user 是 text[] (陣列)，支援多選
--   - 可選值: tenant(租客), landlord(房東), property_manager(物業管理師), system_admin(系統管理員)
--   - NULL 表示通用知識，所有用戶都可見
--   - 與 business_types 正交：target_user 控制視角，business_types 控制語氣

BEGIN;

-- 1. 新增 target_user 欄位
ALTER TABLE knowledge_base
ADD COLUMN target_user text[] DEFAULT NULL;

-- 2. 新增欄位註釋
COMMENT ON COLUMN knowledge_base.target_user IS '目標用戶類型（可多選）：tenant=租客, landlord=房東, property_manager=物業管理師, system_admin=系統管理員, NULL=通用（所有人可見）';

-- 3. 建立 GIN 索引（支援陣列查詢）
CREATE INDEX idx_knowledge_base_target_user ON knowledge_base USING GIN(target_user);

-- 4. 從舊的 audience 備份遷移部分數據（可選）
-- 如果之前的 audience 設計合理，可以從備份表遷移
-- 這裡先不執行，等確認遷移邏輯後再手動執行

/*
-- 遷移範例（需要人工確認對應關係）：
UPDATE knowledge_base kb
SET target_user = CASE
    WHEN backup.audience = '租客' THEN ARRAY['tenant']
    WHEN backup.audience = '房東' THEN ARRAY['landlord']
    WHEN backup.audience = '管理師' THEN ARRAY['property_manager']
    WHEN backup.audience IS NULL THEN NULL
    ELSE NULL
END
FROM audience_backup_20251027 backup
WHERE kb.id = backup.id
  AND backup.audience IS NOT NULL;
*/

-- 5. 更新表註釋
COMMENT ON TABLE knowledge_base IS '知識庫表 - 使用 intents(意圖分類) + business_types(業態語氣) + target_user(用戶視角) 三維度過濾';

COMMIT;

-- 完成通知
\echo '══════════════════════════════════════════'
\echo '  Migration 38 完成'
\echo '  已新增 target_user 欄位'
\echo '  支援多目標用戶知識管理'
\echo '══════════════════════════════════════════'
