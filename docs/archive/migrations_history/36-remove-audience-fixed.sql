-- Migration: 36-remove-audience.sql (修復版)
-- 目的: 移除 audience 欄位和相關配置表，簡化權限控制
-- 決策: 使用 user_role 就足夠，不需要細分對象（租客/房東/管理師）

BEGIN;

-- 1. 備份 audience 數據（以防需要回滾）
CREATE TABLE IF NOT EXISTS audience_backup_20250127 AS
SELECT id, question_summary, audience, created_at
FROM knowledge_base
WHERE audience IS NOT NULL;

-- 2. 移除 knowledge_base 的 audience 欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS audience;

-- 3. 先刪除依賴的視圖
DROP VIEW IF EXISTS v_audience_by_scope CASCADE;

-- 4. 刪除 audience_config 表
DROP TABLE IF EXISTS audience_config CASCADE;

-- 4. 清理任何相關的索引
DROP INDEX IF EXISTS idx_knowledge_base_audience;

-- 5. 更新表註釋
COMMENT ON TABLE knowledge_base IS '知識庫表 - 已移除 audience 欄位（2025-01-27），使用 user_role 即可';

COMMIT;

-- 完成通知
\echo '══════════════════════════════════════════'
\echo '  Migration 36 完成'
\echo '  已移除 audience 權限控制'
\echo '  備份表: audience_backup_20250127'
\echo '══════════════════════════════════════════'
