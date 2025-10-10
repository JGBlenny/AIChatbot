-- ========================================
-- 知識庫自動分類追蹤 - 資料庫遷移腳本
-- ========================================

-- 新增知識分類追蹤欄位到 knowledge_base 表
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS intent_classified_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS needs_reclassify BOOLEAN DEFAULT false;

-- 建立索引以提升查詢效能
CREATE INDEX IF NOT EXISTS idx_kb_needs_reclassify ON knowledge_base(needs_reclassify)
    WHERE needs_reclassify = true;  -- 部分索引，只索引需要重新分類的

CREATE INDEX IF NOT EXISTS idx_kb_intent_confidence ON knowledge_base(intent_confidence);

-- 註解說明
COMMENT ON COLUMN knowledge_base.intent_id IS '關聯的意圖 ID';
COMMENT ON COLUMN knowledge_base.intent_confidence IS '分類信心度 (0-1)';
COMMENT ON COLUMN knowledge_base.intent_assigned_by IS '分配方式: auto (自動) / manual (手動)';
COMMENT ON COLUMN knowledge_base.intent_classified_at IS '最後分類時間';
COMMENT ON COLUMN knowledge_base.needs_reclassify IS '是否需要重新分類';

-- 顯示統計資訊
SELECT
    '✅ 知識庫分類追蹤欄位已建立' AS status,
    COUNT(*) AS total_knowledge,
    COUNT(intent_id) AS classified_count,
    COUNT(*) - COUNT(intent_id) AS unclassified_count
FROM knowledge_base;
