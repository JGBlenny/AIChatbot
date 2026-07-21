-- Rollback：移除 usage_events.search_kb_status（spec brain-kb-grounding 任務 1.1）
-- 日期: 2026-07-20
-- 加性欄位的回復——DROP COLUMN IF EXISTS，重跑安全。回復後應用層偵測降級（欄位不存在
-- → 事件本體照寫、此欄略過），無破壞性。

ALTER TABLE usage_events DROP COLUMN IF EXISTS search_kb_status;
