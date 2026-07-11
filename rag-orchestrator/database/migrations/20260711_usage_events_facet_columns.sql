-- Migration M3：usage_events 面向標注兩欄（spec conversational-repair 任務 1.2｜R7.1）
-- 日期: 2026-07-11
-- 目的：對話面向的輪數可觀測（P50/P90 SQL 可查）。usage_events 是每請求一事件
--       的計量表，本 migration 僅補「面向標注」兩欄，不動任何既有欄位/資料。
--
-- 加性冪等：ADD COLUMN IF NOT EXISTS，重跑安全、無破壞性。應用層以
--   information_schema 偵測降級（services/usage_metering.py），欄位未建時
--   事件本體照寫、兩新欄略過 → 部署順序（先套 migration 或先推程式）皆安全。
--
--   facet_key    ── 對話面向鍵（如 contract/billing/account/iot/estate/repair），
--                   對齊 processing_path 慣例 VARCHAR，截斷 [:60]。
--   turn_number  ── 該面向對話的輪次序號（SMALLINT 足夠；P50/P90 依此聚合）。

ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS facet_key VARCHAR(60);
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS turn_number SMALLINT;

COMMENT ON COLUMN usage_events.facet_key IS '對話面向鍵（conversational-repair R7.1；截斷 60）';
COMMENT ON COLUMN usage_events.turn_number IS '面向對話輪次序號（P50/P90 聚合用）';
