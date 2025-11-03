-- Migration: 37-remove-category.sql
-- 目的: 移除 category 欄位，簡化知識分類
-- 決策: 使用 intents（意圖）和 business_types（業態類型）就足夠，不需要 category

BEGIN;

-- 1. 備份 category 數據（以防需要回滾）
CREATE TABLE IF NOT EXISTS category_backup_20251027 AS
SELECT id, question_summary, category, created_at
FROM knowledge_base
WHERE category IS NOT NULL;

-- 2. 先刪除依賴的視圖
DROP VIEW IF EXISTS v_similar_knowledge_clusters CASCADE;

-- 3. 移除 knowledge_base 的 category 欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS category CASCADE;

-- 3. 清理任何相關的索引
DROP INDEX IF EXISTS idx_knowledge_base_category;

-- 4. 更新表註釋
COMMENT ON TABLE knowledge_base IS '知識庫表 - 已移除 audience 和 category 欄位（2025-10-27），使用 intents 和 business_types 分類';

COMMIT;

-- 完成通知
\echo '══════════════════════════════════════════'
\echo '  Migration 37 完成'
\echo '  已移除 category 欄位'
\echo '  備份表: category_backup_20251027'
\echo '══════════════════════════════════════════'
