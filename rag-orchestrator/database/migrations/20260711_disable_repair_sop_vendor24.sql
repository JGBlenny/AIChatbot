-- Migration: 停用 vendor 2/4 的修繕表單 SOP
-- Spec: conversational-repair tasks.md 4.1，需求 R6.3/R6.5
-- 目的: 對話式修繕新形態全業者切換，停用舊表單式修繕 SOP（next_form_id='jgb_repair_create'）
-- 可逆: 是，使用 rollback/20260711_disable_repair_sop_vendor24.rollback.sql 還原
-- Prod: 由使用者親自執行，本 migration 僅 dev 套用
--
-- 前提查證（2026-07-11 dev 查核）：
--   vendor 2/4 中 is_active=false 的修繕 SOP 原本為 0 筆，rollback 不需排除清單

UPDATE vendor_sop_items
SET is_active = false,
    updated_at = NOW()
WHERE vendor_id IN (2, 4)
  AND next_form_id = 'jgb_repair_create'
  AND is_active = true;
