-- ==========================================
-- Migration: 新增 suggested_embedding 欄位到 suggested_intents 表
-- 用途: 支援語義相似度去重檢查
-- 日期: 2025-10-22
-- ==========================================

-- 新增 suggested_embedding 欄位（vector 類型，1536 維度）
ALTER TABLE suggested_intents
ADD COLUMN IF NOT EXISTS suggested_embedding vector(1536);

-- 建立 ivfflat 索引以加速相似度搜尋
-- Note: 需要先有一些資料才能建立索引，此處註解掉
-- 執行時機：當表中有 100+ 筆資料後再執行
-- CREATE INDEX IF NOT EXISTS idx_suggested_intents_embedding
--     ON suggested_intents USING ivfflat (suggested_embedding vector_cosine_ops)
--     WITH (lists = 100);

-- 如果資料量較少，可以使用 hnsw 索引（更適合小數據集）
-- CREATE INDEX IF NOT EXISTS idx_suggested_intents_embedding
--     ON suggested_intents USING hnsw (suggested_embedding vector_cosine_ops);

-- 新增註解說明
COMMENT ON COLUMN suggested_intents.suggested_embedding IS '建議意圖的向量表示（1536維），用於語義相似度去重檢查（閾值 0.80）';

-- 記錄變更
INSERT INTO system_migrations (migration_name, description)
VALUES ('08-add-suggested-embedding-column', '新增 suggested_embedding 欄位支援語義去重')
ON CONFLICT DO NOTHING;
