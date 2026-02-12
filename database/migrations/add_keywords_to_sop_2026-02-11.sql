-- Migration: 為 SOP 系統新增檢索關鍵字
-- Date: 2026-02-11
-- Purpose: 提升 SOP 項目的檢索準確度，與知識庫系統保持一致性
--
-- 設計理念：
--   - keywords: 用於檢索匹配的關鍵字（與 knowledge_base.keywords 一致）
--   - trigger_keywords: 用於觸發後續動作的關鍵字（保留現有功能）

BEGIN;

-- ==========================================
-- 1. 為 vendor_sop_items 新增 keywords 欄位
-- ==========================================
ALTER TABLE vendor_sop_items
ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT '{}';

-- ==========================================
-- 2. 為 platform_sop_templates 新增 keywords 欄位
-- ==========================================
ALTER TABLE platform_sop_templates
ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT '{}';

-- ==========================================
-- 3. 新增 GIN 索引以優化陣列搜尋
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_vendor_sop_items_keywords
ON vendor_sop_items USING GIN(keywords);

CREATE INDEX IF NOT EXISTS idx_platform_sop_templates_keywords
ON platform_sop_templates USING GIN(keywords);

-- ==========================================
-- 4. 新增註解說明
-- ==========================================
COMMENT ON COLUMN vendor_sop_items.keywords IS
'檢索關鍵字陣列：用於提升檢索準確度的關鍵字，與 knowledge_base.keywords 用途一致。
例如：["冷氣", "空調", "冷房", "AC", "air conditioner"]
注意：此欄位與 trigger_keywords 不同，keywords 用於搜尋，trigger_keywords 用於觸發動作';

COMMENT ON COLUMN platform_sop_templates.keywords IS
'平台範本檢索關鍵字：當業者從範本建立 SOP 時，這些關鍵字會被複製到 vendor_sop_items.keywords';

-- ==========================================
-- 5. 更新現有資料的預設關鍵字（選擇性執行）
-- ==========================================
-- 從 item_name 自動生成初始關鍵字（可選）
-- UPDATE vendor_sop_items
-- SET keywords = string_to_array(lower(item_name), ' ')
-- WHERE keywords = '{}' OR keywords IS NULL;

COMMIT;

-- ==========================================
-- 驗證 Migration 結果
-- ==========================================
DO $$
BEGIN
    -- 檢查 vendor_sop_items.keywords
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'keywords'
    ) THEN
        RAISE EXCEPTION 'vendor_sop_items.keywords 欄位新增失敗';
    END IF;

    -- 檢查 platform_sop_templates.keywords
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'platform_sop_templates'
        AND column_name = 'keywords'
    ) THEN
        RAISE EXCEPTION 'platform_sop_templates.keywords 欄位新增失敗';
    END IF;

    -- 檢查索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'vendor_sop_items'
        AND indexname = 'idx_vendor_sop_items_keywords'
    ) THEN
        RAISE EXCEPTION 'vendor_sop_items keywords 索引建立失敗';
    END IF;

    RAISE NOTICE '✅ SOP 系統 keywords 欄位新增成功';
    RAISE NOTICE '📝 請記得更新相關的 API 和服務層程式碼';
END $$;

-- ==========================================
-- 查詢範例
-- ==========================================
/*
-- 查看所有有關鍵字的 SOP
SELECT
    id,
    item_name,
    keywords,
    trigger_keywords,
    trigger_mode
FROM vendor_sop_items
WHERE keywords IS NOT NULL AND keywords != '{}'
ORDER BY id;

-- 搜尋包含特定關鍵字的 SOP
SELECT
    id,
    item_name,
    keywords
FROM vendor_sop_items
WHERE 'AC' = ANY(keywords)
   OR '冷氣' = ANY(keywords);

-- 統計關鍵字使用情況
SELECT
    unnest(keywords) as keyword,
    COUNT(*) as usage_count
FROM vendor_sop_items
WHERE keywords IS NOT NULL
GROUP BY keyword
ORDER BY usage_count DESC;
*/