-- 移除 conversation_logs.suggested_intent_id 的 FK 約束
-- 日期: 2026-04-14
-- 原因: 對話紀錄只需記錄 ID，不應因清除 suggested_intents 而連帶被清空

ALTER TABLE conversation_logs
DROP CONSTRAINT IF EXISTS conversation_logs_suggested_intent_id_fkey;
