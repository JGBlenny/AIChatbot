-- =====================================================
-- 新增業者：JGB TW-住宅
-- =====================================================
-- 創建日期: 2026-04-22
-- 用途: 建立 JGB 台灣住宅業者，含 jgb_role_id 設定
-- =====================================================

INSERT INTO vendors (
    code,
    name,
    short_name,
    business_types,
    subscription_plan,
    subscription_status,
    subscription_start_date,
    settings,
    is_active,
    created_by
) VALUES (
    'JGB_TW_RESIDENTIAL',
    'JGB TW-住宅',
    'JGB住宅',
    ARRAY['property_management'],
    'premium',
    'active',
    '2026-04-22',
    '{"jgb_role_id": "20151"}'::jsonb,
    true,
    'system'
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    short_name = EXCLUDED.short_name,
    settings = EXCLUDED.settings,
    updated_at = CURRENT_TIMESTAMP;

-- 驗證結果
DO $$
DECLARE
    v RECORD;
BEGIN
    SELECT id, code, name, settings->>'jgb_role_id' AS jgb_role_id
    INTO v
    FROM vendors
    WHERE code = 'JGB_TW_RESIDENTIAL';

    RAISE NOTICE '=================================================';
    RAISE NOTICE '✅ 業者建立完成';
    RAISE NOTICE '=================================================';
    RAISE NOTICE '📋 ID: %', v.id;
    RAISE NOTICE '📋 代碼: %', v.code;
    RAISE NOTICE '📋 名稱: %', v.name;
    RAISE NOTICE '📋 JGB Role ID: %', v.jgb_role_id;
    RAISE NOTICE '=================================================';
END $$;
