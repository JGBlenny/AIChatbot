-- 修復 backtest_runs.test_type CHECK constraint
-- 新增 'batch' 和 'continuous_batch' 以支援知識完善迴圈的分批��測
--
-- 背景：backtest_client.py 使用 'batch'，app.py continuous-batch endpoint 使用 'continuous_batch'
-- 但線上 DB 的 constraint 只有 ('smoke', 'full', 'custom')，導致回測執行失敗

ALTER TABLE backtest_runs DROP CONSTRAINT IF EXISTS backtest_runs_test_type_check;

ALTER TABLE backtest_runs ADD CONSTRAINT backtest_runs_test_type_check
  CHECK (test_type IN ('smoke', 'full', 'custom', 'batch', 'continuous_batch'));
