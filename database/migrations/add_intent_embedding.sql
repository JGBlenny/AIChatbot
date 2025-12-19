-- 添加 embedding 欄位到 intents 表以支持語義化意圖匹配
-- Migration: add_intent_embedding
-- Date: 2025-12-18
-- Purpose: 支持方案2（語義化意圖匹配）- 為意圖添加向量表示

-- 1. 添加 embedding 欄位（1536 維度，適配 OpenAI text-embedding-ada-002）
ALTER TABLE intents
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 2. 為 embedding 欄位添加註解
COMMENT ON COLUMN intents.embedding IS '意圖描述的向量表示（用於語義相似度計算）';

-- 3. 創建 IVFFlat 索引以加速向量相似度查詢
-- 注意：需要先有數據才能創建索引，這裡先準備語句
-- CREATE INDEX IF NOT EXISTS idx_intents_embedding ON intents
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 10);

-- 4. 顯示結果
\d intents
