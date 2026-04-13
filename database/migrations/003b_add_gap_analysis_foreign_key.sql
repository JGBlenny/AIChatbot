-- Migration: 為 knowledge_gap_analysis 表新增外鍵約束
-- 日期: 2026-03-21
-- 任務: 1.3 建立迴圈生成知識資料表（補充）
-- 用途: 建立 knowledge_gap_analysis.loop_knowledge_id 到 loop_generated_knowledge 的外鍵關聯

-- 新增外鍵約束
ALTER TABLE knowledge_gap_analysis
ADD CONSTRAINT fk_gap_analysis_loop_knowledge
FOREIGN KEY (loop_knowledge_id)
REFERENCES loop_generated_knowledge(id)
ON DELETE SET NULL;

-- 建立索引以提升查詢效能
CREATE INDEX IF NOT EXISTS idx_gap_analysis_loop_knowledge_id ON knowledge_gap_analysis(loop_knowledge_id);
