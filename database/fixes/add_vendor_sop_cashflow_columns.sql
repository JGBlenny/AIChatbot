-- ========================================
-- 為 vendor_sop_items 添加金流相關欄位
-- 日期: 2025-12-03
-- 目的: 支援 Excel 匯入功能的金流判斷
-- ========================================

-- 檢查並添加金流相關欄位
DO $$
BEGIN
    -- 添加 requires_cashflow_check 欄位
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'requires_cashflow_check'
    ) THEN
        ALTER TABLE vendor_sop_items
        ADD COLUMN requires_cashflow_check BOOLEAN DEFAULT FALSE;

        RAISE NOTICE '✅ 已添加 requires_cashflow_check 欄位';
    ELSE
        RAISE NOTICE '⏭️  requires_cashflow_check 欄位已存在';
    END IF;

    -- 添加 cashflow_through_company 欄位
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'cashflow_through_company'
    ) THEN
        ALTER TABLE vendor_sop_items
        ADD COLUMN cashflow_through_company TEXT;

        RAISE NOTICE '✅ 已添加 cashflow_through_company 欄位';
    ELSE
        RAISE NOTICE '⏭️  cashflow_through_company 欄位已存在';
    END IF;

    -- 添加 cashflow_direct_to_landlord 欄位
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'cashflow_direct_to_landlord'
    ) THEN
        ALTER TABLE vendor_sop_items
        ADD COLUMN cashflow_direct_to_landlord TEXT;

        RAISE NOTICE '✅ 已添加 cashflow_direct_to_landlord 欄位';
    ELSE
        RAISE NOTICE '⏭️  cashflow_direct_to_landlord 欄位已存在';
    END IF;

    -- 添加 embedding_text 欄位（用於記錄生成 embedding 的文本）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE vendor_sop_items
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE '✅ 已添加 embedding_text 欄位';
    ELSE
        RAISE NOTICE '⏭️  embedding_text 欄位已存在';
    END IF;

    -- 添加 embedding_status 欄位
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'embedding_status'
    ) THEN
        ALTER TABLE vendor_sop_items
        ADD COLUMN embedding_status VARCHAR(20) DEFAULT 'pending';

        RAISE NOTICE '✅ 已添加 embedding_status 欄位';
    ELSE
        RAISE NOTICE '⏭️  embedding_status 欄位已存在';
    END IF;

    -- 添加 embedding_updated_at 欄位
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'embedding_updated_at'
    ) THEN
        ALTER TABLE vendor_sop_items
        ADD COLUMN embedding_updated_at TIMESTAMP;

        RAISE NOTICE '✅ 已添加 embedding_updated_at 欄位';
    ELSE
        RAISE NOTICE '⏭️  embedding_updated_at 欄位已存在';
    END IF;

    -- 添加 embedding_version 欄位
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vendor_sop_items'
        AND column_name = 'embedding_version'
    ) THEN
        ALTER TABLE vendor_sop_items
        ADD COLUMN embedding_version VARCHAR(50);

        RAISE NOTICE '✅ 已添加 embedding_version 欄位';
    ELSE
        RAISE NOTICE '⏭️  embedding_version 欄位已存在';
    END IF;
END $$;

-- 添加註釋
COMMENT ON COLUMN vendor_sop_items.requires_cashflow_check IS '是否需要金流模式判斷';
COMMENT ON COLUMN vendor_sop_items.cashflow_through_company IS '金流過公司的內容版本';
COMMENT ON COLUMN vendor_sop_items.cashflow_direct_to_landlord IS '金流直接給房東的內容版本';
COMMENT ON COLUMN vendor_sop_items.embedding_text IS '用於生成 embedding 的文本（用於調試）';
COMMENT ON COLUMN vendor_sop_items.embedding_status IS 'Embedding 生成狀態：pending, processing, completed, failed';
COMMENT ON COLUMN vendor_sop_items.embedding_updated_at IS 'Embedding 最後更新時間';
COMMENT ON COLUMN vendor_sop_items.embedding_version IS 'Embedding 模型版本（如：text-embedding-3-small）';

-- 顯示結果
SELECT '✅ vendor_sop_items 金流欄位遷移完成' AS status;
