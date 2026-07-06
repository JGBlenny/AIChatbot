-- ============================================================
-- 參數雙軌收斂①：vendor_configs → lookup_tables 搬家（盤查 20260706）
-- 忠實搬遷（category/key/value 原樣，型別與顯示名入 metadata）——切讀零回歸；
-- 值矛盾（LINE/服務時間 等 lookup 已有豐富版）不在此裁決，待業者重匯統一。
-- 另補「客服專線」中文 key 進 customer_service（遠古錨點 1403 現查無的 key）。
-- 冪等：WHERE NOT EXISTS。
-- ============================================================

INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata)
SELECT vc.vendor_id, vc.category, vc.category, vc.param_key, vc.param_value,
       jsonb_build_object('data_type', vc.data_type, 'unit', vc.unit,
                          'display_name', vc.display_name, 'source', 'vendor_configs_migration')
FROM vendor_configs vc
WHERE vc.is_active
  AND NOT EXISTS (SELECT 1 FROM lookup_tables lt
                  WHERE lt.vendor_id = vc.vendor_id AND lt.category = vc.category
                    AND lt.lookup_key = vc.param_key);

-- 客服專線：中文 key 供 lookup 錨點語彙（值取 configs 現行為）
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata)
SELECT vc.vendor_id, 'customer_service', '客服聯絡', '客服專線',
       '聯絡資訊：' || vc.param_value || E'\n適用問題類型：電話諮詢、緊急聯繫',
       jsonb_build_object('source', 'vendor_configs_migration')
FROM vendor_configs vc
WHERE vc.is_active AND vc.param_key = 'service_hotline'
  AND NOT EXISTS (SELECT 1 FROM lookup_tables lt
                  WHERE lt.vendor_id = vc.vendor_id AND lt.category = 'customer_service'
                    AND lt.lookup_key = '客服專線');

DO $$
DECLARE n INT;
BEGIN
    SELECT count(*) INTO n FROM lookup_tables WHERE metadata->>'source' = 'vendor_configs_migration';
    RAISE NOTICE '✅ configs→lookup 搬家：% 筆（36 參數＋3 客服專線 alias 預期 39）', n;
END $$;
