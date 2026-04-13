-- Migration: 擴充 knowledge_base 表新增來源追溯欄位
-- 日期: 2026-03-21
-- 任務: 1.4 擴充 knowledge_base 表
-- 用途: 新增來源追溯欄位（source, source_loop_id, source_loop_knowledge_id），用於標記從迴圈同步來的知識

-- 新增欄位
ALTER TABLE knowledge_base
ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS source_loop_id INT REFERENCES knowledge_completion_loops(id),
ADD COLUMN IF NOT EXISTS source_loop_knowledge_id INT REFERENCES loop_generated_knowledge(id);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_kb_source_loop ON knowledge_base(source_loop_id);

-- 新增 CHECK 約束
-- 確保 source='loop' 時必須有 source_loop_id 和 source_loop_knowledge_id
-- 確保 source!='loop' 時不能有 source_loop_id 和 source_loop_knowledge_id
ALTER TABLE knowledge_base
ADD CONSTRAINT check_loop_source CHECK (
    (source = 'loop' AND source_loop_id IS NOT NULL AND source_loop_knowledge_id IS NOT NULL)
    OR
    (source != 'loop' AND source_loop_id IS NULL AND source_loop_knowledge_id IS NULL)
);

-- 建立欄位註釋
COMMENT ON COLUMN knowledge_base.source IS '知識來源：manual（人工新增）、loop（迴圈生成）、import（匯入）、api（API 呼叫）';
COMMENT ON COLUMN knowledge_base.source_loop_id IS '來源迴圈 ID（當 source=loop 時）';
COMMENT ON COLUMN knowledge_base.source_loop_knowledge_id IS '來源迴圈生成知識 ID（當 source=loop 時）';
