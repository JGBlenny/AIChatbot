-- Migration: 補充知識完善迴圈系統欄位
-- 日期: 2026-03-27
-- 任務: backtest-knowledge-refinement Task 10.1
-- 用途: 補充固定測試集、批次關聯、選取策略等欄位

-- ============================================
-- 1. knowledge_completion_loops 表補充欄位
-- ============================================

-- 補充固定測試集相關欄位
ALTER TABLE knowledge_completion_loops
ADD COLUMN IF NOT EXISTS scenario_ids INTEGER[],  -- 固定測試集 ID 列表
ADD COLUMN IF NOT EXISTS selection_strategy VARCHAR(50) DEFAULT 'stratified_random',  -- 選取策略
ADD COLUMN IF NOT EXISTS difficulty_distribution JSONB,  -- 難度分布 {easy: 10, medium: 25, hard: 15}
ADD COLUMN IF NOT EXISTS parent_loop_id INTEGER REFERENCES knowledge_completion_loops(id),  -- 父迴圈 ID（批次關聯）
ADD COLUMN IF NOT EXISTS max_iterations INTEGER DEFAULT 10;  -- 最大迭代次數

-- 補充約束：selection_strategy 必須是有效值
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_selection_strategy'
        AND conrelid = 'knowledge_completion_loops'::regclass
    ) THEN
        ALTER TABLE knowledge_completion_loops
        ADD CONSTRAINT check_selection_strategy CHECK (
            selection_strategy IN ('stratified_random', 'sequential', 'full_random')
        );
    END IF;
END $$;

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_loops_scenario_ids ON knowledge_completion_loops USING GIN (scenario_ids);
CREATE INDEX IF NOT EXISTS idx_loops_vendor_status ON knowledge_completion_loops(vendor_id, status);
CREATE INDEX IF NOT EXISTS idx_loops_parent ON knowledge_completion_loops(parent_loop_id) WHERE parent_loop_id IS NOT NULL;

-- 建立註釋
COMMENT ON COLUMN knowledge_completion_loops.scenario_ids IS '固定測試集 ID 列表（確保迭代間測試一致性）';
COMMENT ON COLUMN knowledge_completion_loops.selection_strategy IS '測試情境選取策略：stratified_random（分層隨機）、sequential（順序）、full_random（完全隨機）';
COMMENT ON COLUMN knowledge_completion_loops.difficulty_distribution IS '難度分布統計（JSON 格式）：{easy: 10, medium: 25, hard: 15}';
COMMENT ON COLUMN knowledge_completion_loops.parent_loop_id IS '父迴圈 ID（用於批次關聯，避免批次間重複選取測試情境）';
COMMENT ON COLUMN knowledge_completion_loops.max_iterations IS '最大迭代次數（1-50，預設 10）';

-- ============================================
-- 2. loop_generated_knowledge 表補充欄位
-- ============================================

-- 補充重複檢測相關欄位
ALTER TABLE loop_generated_knowledge
ADD COLUMN IF NOT EXISTS similar_knowledge JSONB,  -- 重複檢測結果
ADD COLUMN IF NOT EXISTS duplication_warning VARCHAR(500),  -- 重複警告文字
ADD COLUMN IF NOT EXISTS knowledge_type VARCHAR(20);  -- 知識類型：sop/null

-- 補充 SOP 相關欄位
ALTER TABLE loop_generated_knowledge
ADD COLUMN IF NOT EXISTS sop_config JSONB;  -- SOP 配置（category_id, group_id, step_number 等）

-- 建立註釋
COMMENT ON COLUMN loop_generated_knowledge.similar_knowledge IS '重複檢測結果（JSON 格式）：{detected: bool, items: [{id, source_table, question_summary, similarity_score}]}';
COMMENT ON COLUMN loop_generated_knowledge.duplication_warning IS '重複警告文字，例如：「檢測到 1 個高度相似的知識（相似度 93%）」';
COMMENT ON COLUMN loop_generated_knowledge.knowledge_type IS '知識類型：sop（SOP 知識）、null（一般知識）';
COMMENT ON COLUMN loop_generated_knowledge.sop_config IS 'SOP 配置（僅 knowledge_type = sop 時使用）：{category_id, group_id, step_number, ...}';

-- ============================================
-- 3. 補充 knowledge_gap_analysis 表欄位（002 建表後新增的欄位）
-- ============================================

ALTER TABLE knowledge_gap_analysis
ADD COLUMN IF NOT EXISTS test_question TEXT,
ADD COLUMN IF NOT EXISTS gap_type VARCHAR(20),
ADD COLUMN IF NOT EXISTS cluster_id INTEGER,
ADD COLUMN IF NOT EXISTS should_generate_knowledge BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS classification_metadata JSONB;

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_gap_analysis_scenario ON knowledge_gap_analysis(scenario_id);
CREATE INDEX IF NOT EXISTS idx_gap_analysis_cluster ON knowledge_gap_analysis(cluster_id);
CREATE INDEX IF NOT EXISTS idx_gap_analysis_gap_type ON knowledge_gap_analysis(gap_type);

-- 建立註釋
COMMENT ON COLUMN knowledge_gap_analysis.gap_type IS '缺口類型：sop_knowledge（SOP 流程）、form_fill（表單填寫）、system_config（系統配置）、api_query（API 查詢）';
COMMENT ON COLUMN knowledge_gap_analysis.cluster_id IS '聚類 ID（同一聚類的缺口會一起生成知識）';
COMMENT ON COLUMN knowledge_gap_analysis.should_generate_knowledge IS '是否應生成知識（false 表示 API 查詢類型，不生成靜態知識）';
COMMENT ON COLUMN knowledge_gap_analysis.classification_metadata IS 'OpenAI 分類的完整結果（JSON 格式）';

