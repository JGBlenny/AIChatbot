-- Migration: 建立知識庫完善迴圈系統 - 核心迴圈表
-- 日期: 2026-03-21
-- 任務: 1.1 建立核心迴圈資料表
-- 用途: 記錄知識庫完善迴圈的執行狀態、配置與統計資訊

-- 建立主表
CREATE TABLE IF NOT EXISTS knowledge_completion_loops (
    id SERIAL PRIMARY KEY,
    loop_name VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- pending, running, backtesting, analyzing, generating, reviewing, validating, syncing, paused, completed, failed, cancelled, terminated
    vendor_id INT NOT NULL,

    -- 配置
    config JSONB NOT NULL,  -- {batch_size, max_iterations, target_pass_rate, action_type_mode, filters, backtest_config}

    -- 統計
    total_scenarios INT,
    current_iteration INT DEFAULT 0,
    iterations_history JSONB[] DEFAULT '{}',  -- [{iteration, pass_rate, added_knowledge, synced_knowledge, duration, validated_at}]

    -- 進度
    initial_pass_rate FLOAT,
    current_pass_rate FLOAT,
    target_pass_rate FLOAT NOT NULL,

    -- 回測品質驗證
    manual_review_accuracy FLOAT,  -- 人工抽查準確率
    manual_review_samples INT DEFAULT 0,  -- 抽查樣本總數
    manual_review_alerts JSONB[] DEFAULT '{}',  -- 告警歷史
    backtest_config_changes JSONB[] DEFAULT '{}',  -- 回測參數變更歷史

    -- 審核超時監控欄位（設計擴充）
    review_timeout_reminder_sent BOOLEAN DEFAULT FALSE,
    review_timeout_reminder_sent_at TIMESTAMP,

    -- OpenAI 成本追蹤欄位（設計擴充）
    budget_limit_usd NUMERIC(10, 2),  -- 預算上限（USD）
    total_openai_cost_usd NUMERIC(10, 6) DEFAULT 0.0,  -- 累計成本（USD）

    -- 時間戳
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 約束：status 必須是有效的狀態值
    CONSTRAINT check_status CHECK (status IN (
        'pending', 'running', 'backtesting', 'analyzing', 'generating',
        'reviewing', 'validating', 'syncing', 'paused', 'completed',
        'failed', 'cancelled', 'terminated'
    ))
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_kc_loops_vendor_status ON knowledge_completion_loops(vendor_id, status);
CREATE INDEX IF NOT EXISTS idx_kc_loops_created_at ON knowledge_completion_loops(created_at DESC);

-- 建立註釋
COMMENT ON TABLE knowledge_completion_loops IS '知識庫完善迴圈主表';
COMMENT ON COLUMN knowledge_completion_loops.status IS '迴圈狀態（狀態機）';
COMMENT ON COLUMN knowledge_completion_loops.config IS '迴圈配置（batch_size, max_iterations, target_pass_rate, filters 等）';
COMMENT ON COLUMN knowledge_completion_loops.iterations_history IS '迭代歷史（JSONB 陣列）';
COMMENT ON COLUMN knowledge_completion_loops.review_timeout_reminder_sent IS '審核超時提醒是否已發送';
COMMENT ON COLUMN knowledge_completion_loops.budget_limit_usd IS '單次迴圈預算上限（USD）';
COMMENT ON COLUMN knowledge_completion_loops.total_openai_cost_usd IS '累計 OpenAI API 成本（USD）';
