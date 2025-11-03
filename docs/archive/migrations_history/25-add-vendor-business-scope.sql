-- Migration: 25-add-vendor-business-scope.sql
-- Description: Add business_scope_name to vendors table for vendor-level business scope assignment
-- Date: 2025-10-12
-- Author: Claude Code

-- ============================================================
-- 1. Add business_scope_name column to vendors table
-- ============================================================

ALTER TABLE vendors
ADD COLUMN business_scope_name VARCHAR(100) DEFAULT 'external';

COMMENT ON COLUMN vendors.business_scope_name IS 'Business scope type for this vendor (references business_scope_config.scope_name)';

-- ============================================================
-- 2. Add foreign key constraint
-- ============================================================

ALTER TABLE vendors
ADD CONSTRAINT vendors_business_scope_fkey
FOREIGN KEY (business_scope_name)
REFERENCES business_scope_config(scope_name)
ON UPDATE CASCADE
ON DELETE SET DEFAULT;

-- ============================================================
-- 3. Create index for performance
-- ============================================================

CREATE INDEX idx_vendors_business_scope ON vendors(business_scope_name);

-- ============================================================
-- 4. Update existing vendors
-- ============================================================

-- Set all existing vendors to use 'external' scope (B2C scenario)
UPDATE vendors
SET business_scope_name = 'external'
WHERE business_scope_name IS NULL;

-- ============================================================
-- 5. Remove is_active from business_scope_config (no longer needed)
-- ============================================================

-- Note: We're keeping is_active for backward compatibility during transition
-- It can be removed in a future migration after all code is updated

COMMENT ON COLUMN business_scope_config.is_active IS 'DEPRECATED: Business scopes are now assigned per vendor, not globally';

-- ============================================================
-- Migration Complete
-- ============================================================

-- Verification queries:
-- SELECT id, name, business_scope_name FROM vendors;
-- SELECT scope_name, scope_type, display_name FROM business_scope_config;
