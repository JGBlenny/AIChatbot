-- Rollback：移除 usage_events 決策快照兩欄（spec retrieval-decision-layer 任務 1.2）
-- 日期: 2026-08-11
-- 加性欄位的回復——DROP COLUMN IF EXISTS，重跑安全。回復後應用層偵測降級（欄位不存在
-- → 事件本體照寫、兩欄略過），無破壞性。索引隨欄位一併消失，另下 DROP INDEX 只為冪等。

DROP INDEX IF EXISTS idx_usage_facet_event;
ALTER TABLE usage_events DROP COLUMN IF EXISTS decision_snapshot;
ALTER TABLE usage_events DROP COLUMN IF EXISTS facet_event;
