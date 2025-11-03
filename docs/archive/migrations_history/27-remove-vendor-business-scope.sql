-- Migration: 27-remove-vendor-business-scope.sql
-- Description: Remove business_scope_name from vendors table
-- Date: 2025-10-12
-- Author: Claude Code
-- Reason: Business scope should be determined per request, not per vendor
--         Vendors serve both B2B (internal) and B2C (external) scenarios

-- ============================================================
-- Background
-- ============================================================
-- Previously, each vendor was forced to choose either 'external' (B2C) or
-- 'internal' (B2B) business scope. However, in reality, every vendor needs
-- to serve both scenarios:
-- - B2B: Internal management by vendor staff
-- - B2C: External customer service (tenants, landlords)
--
-- The business scope should be determined at request time based on:
-- - User role (staff vs customer)
-- - Request context
-- - Authentication token

-- ============================================================
-- 1. Drop foreign key constraint
-- ============================================================

ALTER TABLE vendors
DROP CONSTRAINT IF EXISTS vendors_business_scope_fkey;

-- ============================================================
-- 2. Drop index
-- ============================================================

DROP INDEX IF EXISTS idx_vendors_business_scope;

-- ============================================================
-- 3. Remove business_scope_name column
-- ============================================================

ALTER TABLE vendors
DROP COLUMN IF EXISTS business_scope_name;

-- ============================================================
-- Migration Complete
-- ============================================================

-- Verification query:
-- \d vendors
-- Should NOT show business_scope_name column

-- Update chat API to accept business_scope parameter:
-- POST /api/v1/message
-- {
--   "vendor_id": 1,
--   "message": "退租流程",
--   "business_scope": "external"  // or "internal"
-- }
