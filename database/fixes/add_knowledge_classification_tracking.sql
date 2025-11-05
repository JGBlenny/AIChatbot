-- ========================================
-- 知識庫自動分類追蹤欄位修復
-- ========================================
-- 用途：為 knowledge_base 表添加意圖分類追蹤欄位
-- 相關功能：意圖分配（KnowledgeReclassifyView）、自動分類統計
-- ========================================

-- 新增知識分類追蹤欄位到 knowledge_base 表
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS intent_classified_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS needs_reclassify BOOLEAN DEFAULT false;

-- 建立索引以提升查詢效能
-- 部分索引：只索引需要重新分類的知識，提高篩選效率
CREATE INDEX IF NOT EXISTS idx_kb_needs_reclassify ON knowledge_base(needs_reclassify)
    WHERE needs_reclassify = true;

-- 為意圖信心度添加索引（用於查詢低信心度知識）
CREATE INDEX IF NOT EXISTS idx_kb_intent_confidence ON knowledge_base(intent_confidence);

-- 為已有 intent_id 的知識設置 intent_classified_at（假設在創建時已分類）
UPDATE knowledge_base
SET intent_classified_at = created_at
WHERE intent_id IS NOT NULL
  AND intent_classified_at IS NULL;

-- 註解說明
COMMENT ON COLUMN knowledge_base.intent_id IS '關聯的意圖 ID';
COMMENT ON COLUMN knowledge_base.intent_confidence IS '分類信心度 (0-1)';
COMMENT ON COLUMN knowledge_base.intent_assigned_by IS '分配方式: auto (自動) / manual (手動)';
COMMENT ON COLUMN knowledge_base.intent_classified_at IS '最後分類時間';
COMMENT ON COLUMN knowledge_base.needs_reclassify IS '是否需要重新分類（當意圖更新時標記為 true）';

-- 顯示統計資訊
SELECT
    '✅ 知識庫分類追蹤欄位已建立' AS status,
    COUNT(*) AS total_knowledge,
    COUNT(intent_id) AS classified_count,
    COUNT(*) - COUNT(intent_id) AS unclassified_count,
    COUNT(CASE WHEN needs_reclassify THEN 1 END) AS needs_reclassify_count
FROM knowledge_base;
