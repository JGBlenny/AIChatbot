-- ========================================
-- 知識庫分類欄位修復
-- ========================================
-- 用途：添加 category 欄位以支援業務分類功能
-- 相關：category_config 表已存在，前端管理介面已完成
-- ========================================

-- 1. 添加 category 欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS category VARCHAR(50);

-- 2. 添加外鍵約束（可選，確保資料完整性）
-- 注意：如果要強制約束，請取消註釋
-- ALTER TABLE knowledge_base
-- ADD CONSTRAINT fk_knowledge_category
-- FOREIGN KEY (category) REFERENCES category_config(category_value) ON DELETE SET NULL;

-- 3. 建立索引
CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base(category);

-- 4. 添加欄位註釋
COMMENT ON COLUMN knowledge_base.category IS '業務分類（參考 category_config 表）';

-- 5. 顯示統計
SELECT
    '✅ category 欄位已添加' AS status,
    COUNT(*) AS total_knowledge,
    COUNT(category) AS has_category,
    COUNT(*) - COUNT(category) AS missing_category
FROM knowledge_base;

-- ========================================
-- 使用說明
-- ========================================
--
-- category 欄位的值應該對應 category_config.category_value
-- 可用的分類值：
-- - 合約問題
-- - 帳務問題
-- - 服務問題
-- - 設備報修
-- - 設施使用
-- - 設施問題
-- - 物件問題
-- - 帳號問題
-- - 其他
--
-- 範例：
-- UPDATE knowledge_base SET category = '帳務問題' WHERE id = 1;
-- ========================================
