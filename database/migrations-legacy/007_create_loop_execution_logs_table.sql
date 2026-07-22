-- Migration: 建立迴圈執行日誌資料表
-- 日期: 2026-03-21
-- 任務: 1.7 建立迴圈執行日誌資料表
-- 用途: 記錄所有迴圈執行事件，支援除錯與審計

CREATE TABLE IF NOT EXISTS loop_execution_logs (
    log_id BIGSERIAL PRIMARY KEY,
    loop_id INT NOT NULL REFERENCES knowledge_completion_loops(id) ON DELETE CASCADE,

    -- 事件資訊
    event_type VARCHAR(50) NOT NULL,  -- 事件類型
    event_data JSONB,  -- 事件詳細資料（JSON 格式）

    -- 時間戳記
    created_at TIMESTAMP DEFAULT NOW()
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_logs_loop_id ON loop_execution_logs(loop_id);
CREATE INDEX IF NOT EXISTS idx_logs_event_type ON loop_execution_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON loop_execution_logs(created_at DESC);

-- 建立 GIN 索引（支援 JSONB 查詢）
CREATE INDEX IF NOT EXISTS idx_logs_event_data ON loop_execution_logs USING GIN(event_data);

-- 建立註釋
COMMENT ON TABLE loop_execution_logs IS '迴圈執行日誌（所有事件記錄）';
COMMENT ON COLUMN loop_execution_logs.event_type IS '事件類型：status_changed, iteration_started, backtest_completed, gap_analysis_completed, knowledge_generated, sync_completed, error_occurred, warning_issued 等';
COMMENT ON COLUMN loop_execution_logs.event_data IS '事件詳細資料（JSONB 格式），內容依事件類型而異';
