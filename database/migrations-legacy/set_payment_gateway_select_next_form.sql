-- =====================================================
-- Migration: 設定金流商選擇表單的串接目標
-- =====================================================
-- 日期: 2026-06-20
-- 功能: form-chaining（表單串接機制）任務 5.2
-- 目的: 讓 payment_gateway_select 完成後自動串接 payment_gateway_followup
--       （制式追問選單）。依賴：next_form_id 欄位（1.2）+ 後續表單（5.1）已就緒。
-- 需求: 2.1
--
-- 冪等：直接設值，可安全重跑。
-- =====================================================

BEGIN;

UPDATE form_schemas
SET next_form_id = 'payment_gateway_followup',
    updated_at = NOW()
WHERE form_id = 'payment_gateway_select';

COMMIT;

-- 驗證
DO $$
DECLARE
    linked TEXT;
BEGIN
    SELECT next_form_id INTO linked FROM form_schemas WHERE form_id = 'payment_gateway_select';
    IF linked = 'payment_gateway_followup' THEN
        RAISE NOTICE '✅ payment_gateway_select → payment_gateway_followup 串接設定成功';
    ELSE
        RAISE EXCEPTION '❌ 串接設定失敗：next_form_id=%', linked;
    END IF;
END $$;

-- =====================================================
-- 套用:
--   docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
--     database/migrations/set_payment_gateway_select_next_form.sql
-- 回滾:
--   UPDATE form_schemas SET next_form_id = NULL WHERE form_id = 'payment_gateway_select';
-- =====================================================
