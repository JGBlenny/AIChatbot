-- =====================================================
-- Lookup Table System - 數據庫遷移
-- =====================================================
-- 創建日期: 2026-02-04
-- 用途: 創建通用 Lookup Table 系統
-- 功能: 支持鍵值對查詢、模糊匹配、多租戶隔離
-- =====================================================

-- 啟用 pg_trgm 擴展（用於模糊查詢優化）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 創建 lookup_tables 表
CREATE TABLE IF NOT EXISTS lookup_tables (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,           -- 類別 ID (如 billing_interval)
    category_name VARCHAR(200),               -- 類別顯示名稱 (如 "電費寄送區間")
    lookup_key TEXT NOT NULL,                 -- 查詢鍵 (如地址)
    lookup_value TEXT NOT NULL,               -- 查詢值 (如 "雙月")
    metadata JSONB DEFAULT '{}',              -- 額外數據 (如電號、備註)
    is_active BOOLEAN DEFAULT true,           -- 是否啟用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 唯一約束：同一業者、同一類別下的鍵不能重複
    CONSTRAINT unique_vendor_category_key
        UNIQUE(vendor_id, category, lookup_key)
);

-- 建立索引優化查詢性能
-- 索引 1: 類別查詢優化（常用查詢路徑）
CREATE INDEX IF NOT EXISTS idx_lookup_category
    ON lookup_tables(vendor_id, category, is_active);

-- 索引 2: 精確匹配優化
CREATE INDEX IF NOT EXISTS idx_lookup_key
    ON lookup_tables(vendor_id, category, lookup_key)
    WHERE is_active = true;

-- 索引 3: 模糊匹配優化（GIN 索引 + pg_trgm）
CREATE INDEX IF NOT EXISTS idx_lookup_key_gin
    ON lookup_tables USING gin(lookup_key gin_trgm_ops);

-- 索引 4: JSON 字段查詢優化（如果需要查詢 metadata）
CREATE INDEX IF NOT EXISTS idx_lookup_metadata
    ON lookup_tables USING gin(metadata);

-- 添加表註釋
COMMENT ON TABLE lookup_tables IS 'Lookup Table System - 通用鍵值對查詢表，支持精確和模糊匹配';
COMMENT ON COLUMN lookup_tables.vendor_id IS '業者 ID，支持多租戶隔離';
COMMENT ON COLUMN lookup_tables.category IS '類別 ID，用於區分不同類型的查詢（如 billing_interval, property_manager）';
COMMENT ON COLUMN lookup_tables.category_name IS '類別顯示名稱，用於前端展示';
COMMENT ON COLUMN lookup_tables.lookup_key IS '查詢鍵，用戶輸入的查詢內容（如地址、車牌號）';
COMMENT ON COLUMN lookup_tables.lookup_value IS '查詢值，返回給用戶的結果（如單月/雙月）';
COMMENT ON COLUMN lookup_tables.metadata IS '額外數據，JSONB 格式，可存儲任意結構化信息';
COMMENT ON COLUMN lookup_tables.is_active IS '是否啟用，支持軟刪除';

-- 創建更新時間觸發器函數
CREATE OR REPLACE FUNCTION update_lookup_tables_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 創建觸發器
DROP TRIGGER IF EXISTS trigger_update_lookup_tables_updated_at ON lookup_tables;
CREATE TRIGGER trigger_update_lookup_tables_updated_at
    BEFORE UPDATE ON lookup_tables
    FOR EACH ROW
    EXECUTE FUNCTION update_lookup_tables_updated_at();

-- 插入測試數據（可選，僅用於驗證）
INSERT INTO lookup_tables (
    vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active
) VALUES
    (1, 'billing_interval', '電費寄送區間', '測試地址-新北市板橋區', '雙月', '{"electric_number": "TEST001", "note": "測試數據"}'::jsonb, true),
    (1, 'billing_interval', '電費寄送區間', '測試地址-台北市大安區', '單月', '{"electric_number": "TEST002"}'::jsonb, true)
ON CONFLICT (vendor_id, category, lookup_key) DO NOTHING;

-- 驗證表創建
DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
    test_count INTEGER;
BEGIN
    -- 檢查表是否創建
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_name = 'lookup_tables';

    -- 檢查索引是否創建
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename = 'lookup_tables';

    -- 檢查測試數據
    SELECT COUNT(*) INTO test_count
    FROM lookup_tables
    WHERE category = 'billing_interval';

    -- 輸出結果
    RAISE NOTICE '=================================================';
    RAISE NOTICE '✅ Lookup Tables 創建完成';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '📊 表狀態: %', CASE WHEN table_count > 0 THEN '已創建' ELSE '創建失敗' END;
    RAISE NOTICE '📊 索引數量: %', index_count;
    RAISE NOTICE '📊 測試數據: % 筆', test_count;
    RAISE NOTICE '=================================================';
END $$;
