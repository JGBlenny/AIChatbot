-- Migration：usage_events 加 search_kb_status 單欄（spec brain-kb-grounding 任務 1.1｜R5.2）
-- 日期: 2026-07-20
-- 目的：Brain search_kb 工具的岔題輪可觀測（呼叫率/命中率 SQL 可查、P90 延遲增量可切分）。
--       usage_events 是每請求一事件的計量表，本 migration 僅補「search_kb 狀態」一欄，
--       不動任何既有欄位/資料。
--
-- 加性冪等：ADD COLUMN IF NOT EXISTS，重跑安全、無破壞性。應用層以
--   information_schema 偵測降級（services/usage_metering.py），欄位未建時
--   事件本體照寫、此新欄略過 → 部署順序（先套 migration 或先推程式）皆安全。
--
--   search_kb_status ── 本輪 search_kb 工具狀態：
--                       null＝未呼叫工具（一般輪）｜'hit'＝呼叫且命中｜'miss'＝呼叫但 NO_MATCH。
--                       切分鍵：岔題輪 = search_kb_status IS NOT NULL；命中率 = hit/(hit+miss)；
--                       P90 增量 = duration_ms P90(工具輪) − P90(一般輪)。

ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS search_kb_status VARCHAR(16);

COMMENT ON COLUMN usage_events.search_kb_status IS 'Brain search_kb 工具本輪狀態（brain-kb-grounding R5.2；null/hit/miss）';
