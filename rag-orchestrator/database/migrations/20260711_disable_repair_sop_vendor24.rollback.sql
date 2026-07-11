-- Rollback: 還原 vendor 2/4 的修繕表單 SOP 為啟用
-- 對應 migration: 20260711_disable_repair_sop_vendor24.sql
-- 前提: 本 rollback 只回復本 migration 停用的筆數。
--   查證（2026-07-11）：執行 migration 前 vendor 2/4 無任何 is_active=false 的修繕 SOP，
--   故 WHERE 條件直接回寫 true，不會誤啟任何原本就停用的資料。

UPDATE vendor_sop_items
SET is_active = true,
    updated_at = NOW()
WHERE vendor_id IN (2, 4)
  AND next_form_id = 'jgb_repair_create'
  AND is_active = false;
