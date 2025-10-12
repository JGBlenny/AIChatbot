-- Migration: 26-remove-business-scope-is-active.sql
-- Description: Remove deprecated is_active column from business_scope_config table
-- Date: 2025-10-12
-- Author: Claude Code
-- Reference: Migration 25 marked this field as DEPRECATED

-- ============================================================
-- Background
-- ============================================================
-- The is_active column was used in the old architecture where business scopes
-- were globally switched. Now business scopes are assigned per vendor via
-- vendors.business_scope_name, making is_active obsolete.

-- ============================================================
-- 1. Drop index on is_active (if exists)
-- ============================================================

DROP INDEX IF EXISTS idx_business_scope_active;

-- ============================================================
-- 2. Remove is_active column
-- ============================================================

ALTER TABLE business_scope_config
DROP COLUMN IF EXISTS is_active;

-- ============================================================
-- Migration Complete
-- ============================================================

-- Verification query:
-- \d business_scope_config
-- Should NOT show is_active column

-- Check vendors still reference business_scope_config correctly:
-- SELECT v.id, v.name, v.business_scope_name, bsc.display_name
-- FROM vendors v
-- JOIN business_scope_config bsc ON v.business_scope_name = bsc.scope_name;
