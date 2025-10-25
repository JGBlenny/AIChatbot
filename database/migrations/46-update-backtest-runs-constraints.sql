-- 更新 backtest_runs 表的約束以支持新的測試策略

-- 1. 更新現有數據：將 'basic' 模式改為 'hybrid'（向後兼容）
UPDATE backtest_runs
SET quality_mode = 'hybrid'
WHERE quality_mode = 'basic';

-- 2. 更新現有數據：將 'smoke' 和 'custom' 改為 'incremental'（向後兼容）
UPDATE backtest_runs
SET test_type = 'incremental'
WHERE test_type IN ('smoke', 'custom');

-- 3. 更新 test_type 約束：從 smoke/full/custom 改為 incremental/full/failed_only
ALTER TABLE backtest_runs
DROP CONSTRAINT IF EXISTS backtest_runs_test_type_check;

ALTER TABLE backtest_runs
ADD CONSTRAINT backtest_runs_test_type_check
CHECK (test_type IN ('incremental', 'full', 'failed_only'));

-- 4. 更新 quality_mode 約束：移除已棄用的 'basic' 模式
ALTER TABLE backtest_runs
DROP CONSTRAINT IF EXISTS backtest_runs_quality_mode_check;

ALTER TABLE backtest_runs
ADD CONSTRAINT backtest_runs_quality_mode_check
CHECK (quality_mode IN ('detailed', 'hybrid'));

COMMENT ON COLUMN backtest_runs.test_type IS 'Testing strategy: incremental (new+failed+stale), full (all approved), failed_only (only failed)';
COMMENT ON COLUMN backtest_runs.quality_mode IS 'Quality evaluation mode: detailed (100% LLM), hybrid (confidence + LLM)';
