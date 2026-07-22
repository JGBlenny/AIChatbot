-- Migration: 移除 api_endpoints 表的 handler_function 欄位
-- 日期: 2026-01-21
-- 原因: handler_function 欄位已棄用，改用 custom_handler_name
--
-- 說明:
-- - handler_function 是舊版欄位，僅用於提示開發者，系統不使用
-- - 新版使用 custom_handler_name (配合 implementation_type) 來指定自定義處理器
-- - 此遷移會完全移除 handler_function 欄位

-- ============================================================
-- 備份提醒
-- ============================================================
-- 執行前請確保已備份資料庫！
-- 此遷移會刪除欄位，無法自動回滾。

-- ============================================================
-- 檢查現有數據
-- ============================================================
-- 執行前可以先檢查 handler_function 的使用情況：
-- SELECT endpoint_id, handler_function, custom_handler_name, implementation_type
-- FROM api_endpoints
-- WHERE handler_function IS NOT NULL;

-- ============================================================
-- 移除欄位
-- ============================================================

-- Step 1: 移除 handler_function 欄位
ALTER TABLE api_endpoints
DROP COLUMN IF EXISTS handler_function;

-- ============================================================
-- 驗證
-- ============================================================
-- 執行後驗證：
-- \d api_endpoints
--
-- 應該看到 handler_function 欄位已被移除
-- custom_handler_name 欄位保留

-- ============================================================
-- 回滾（手動）
-- ============================================================
-- 如果需要回滾，執行以下 SQL：
--
-- ALTER TABLE api_endpoints
-- ADD COLUMN handler_function VARCHAR(100);
--
-- -- 如果需要從 custom_handler_name 恢復數據：
-- UPDATE api_endpoints
-- SET handler_function = custom_handler_name
-- WHERE custom_handler_name IS NOT NULL;
