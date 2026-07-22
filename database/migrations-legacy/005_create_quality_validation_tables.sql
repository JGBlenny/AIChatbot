-- Migration: 建立回測品質驗證資料表
-- 日期: 2026-03-21
-- 任務: 1.5 建立回測品質驗證資料表
-- 用途: 建立回測人工抽查、邏輯變更、迭代回滾歷史表

-- ============================================
-- 1. backtest_manual_reviews（回測人工抽查）
-- ============================================

CREATE TABLE IF NOT EXISTS backtest_manual_reviews (
    id SERIAL PRIMARY KEY,
    loop_id INT NOT NULL REFERENCES knowledge_completion_loops(id) ON DELETE CASCADE,
    iteration INT NOT NULL,
    backtest_result_id INT NOT NULL REFERENCES backtest_results(id),

    -- 抽樣資訊
    sample_strategy VARCHAR(50),  -- random, critical_threshold, intent_balanced

    -- 人工評估
    manual_judgment VARCHAR(20),  -- correct, incorrect
    correct_pass_status BOOLEAN,  -- 人工認為應該是 pass 或 fail
    review_notes TEXT,
    error_type VARCHAR(50),  -- too_strict, too_loose, logic_error, other

    -- 審核人員
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_judgment CHECK (manual_judgment IN ('correct', 'incorrect')),
    CONSTRAINT valid_error_type CHECK (error_type IN ('too_strict', 'too_loose', 'logic_error', 'other'))
);

CREATE INDEX IF NOT EXISTS idx_manual_reviews_loop_iteration ON backtest_manual_reviews(loop_id, iteration);
CREATE INDEX IF NOT EXISTS idx_manual_reviews_judgment ON backtest_manual_reviews(manual_judgment);

COMMENT ON TABLE backtest_manual_reviews IS '回測人工抽查記錄';
COMMENT ON COLUMN backtest_manual_reviews.manual_judgment IS '人工判斷回測評分是否正確';
COMMENT ON COLUMN backtest_manual_reviews.error_type IS '錯誤類型：過嚴、過鬆、邏輯錯誤、其他';

-- ============================================
-- 2. backtest_logic_changes（回測邏輯變更歷史）
-- ============================================

CREATE TABLE IF NOT EXISTS backtest_logic_changes (
    id SERIAL PRIMARY KEY,
    loop_id INT REFERENCES knowledge_completion_loops(id) ON DELETE SET NULL,
    change_type VARCHAR(50) NOT NULL,  -- parameter, logic_modification, new_dimension

    -- 變更內容
    description TEXT NOT NULL,
    changed_files TEXT[],  -- 修改的程式碼檔案
    git_commit_hash VARCHAR(40),  -- Git commit hash（如有）

    -- A/B 測試結果
    test_cases_count INT,
    old_accuracy FLOAT,
    new_accuracy FLOAT,
    improvement FLOAT,  -- (new_accuracy - old_accuracy)

    -- 套用範圍
    applied_to_future BOOLEAN DEFAULT true,
    reevaluated_history BOOLEAN DEFAULT false,
    reevaluation_report JSONB,  -- 重新評估的詳細結果

    -- 時間與人員
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(100),

    CONSTRAINT valid_change_type CHECK (change_type IN ('parameter', 'logic_modification', 'new_dimension'))
);

CREATE INDEX IF NOT EXISTS idx_logic_changes_loop ON backtest_logic_changes(loop_id);

COMMENT ON TABLE backtest_logic_changes IS '回測邏輯變更歷史';
COMMENT ON COLUMN backtest_logic_changes.change_type IS '變更類型：參數調整、邏輯修改、新評估維度';
COMMENT ON COLUMN backtest_logic_changes.applied_to_future IS '是否套用至未來回測';
COMMENT ON COLUMN backtest_logic_changes.reevaluated_history IS '是否已重新評估歷史資料';

-- ============================================
-- 3. loop_rollback_history（迭代回滾歷史）
-- ============================================

CREATE TABLE IF NOT EXISTS loop_rollback_history (
    id SERIAL PRIMARY KEY,
    loop_id INT NOT NULL REFERENCES knowledge_completion_loops(id) ON DELETE CASCADE,
    rollback_from_iteration INT NOT NULL,
    rollback_to_iteration INT NOT NULL,
    rollback_reason TEXT NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,  -- manual_intervention, automatic_alert

    -- 影響範圍
    affected_loop_knowledge_count INT,
    affected_kb_knowledge_count INT,
    rolled_back_loop_knowledge_ids INT[],
    deleted_kb_ids INT[],

    -- 執行人員
    executed_by VARCHAR(100),
    executed_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_trigger_type CHECK (trigger_type IN ('manual_intervention', 'automatic_alert'))
);

CREATE INDEX IF NOT EXISTS idx_rollback_history_loop ON loop_rollback_history(loop_id);

COMMENT ON TABLE loop_rollback_history IS '迭代回滾歷史記錄';
COMMENT ON COLUMN loop_rollback_history.affected_loop_knowledge_count IS '影響的 loop_generated_knowledge 記錄數';
COMMENT ON COLUMN loop_rollback_history.affected_kb_knowledge_count IS '從 knowledge_base 刪除的記錄數';
COMMENT ON COLUMN loop_rollback_history.trigger_type IS '觸發類型：人工介入、自動告警';
