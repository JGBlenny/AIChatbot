-- =====================================================
-- billing-conversational-facets 任務 4.1：帳務面向分類（category_config 母子）
-- 母『系統帳務』→ 子：繳費金流排障／帳單異常／發票／滯納金／帳單設定引導。
-- 供三層脈絡疊加、config_for_category 進場、_domain_faces 衍生換面向集合。
-- 套用：psql "$DATABASE_URL" -f database/migrations/add_billing_facet_categories.sql
-- 冪等：category_value 已存在則不重插。
-- =====================================================

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '系統帳務', '系統帳務', '帳務對話領域（母分類）：帳單/金流/發票共用系統脈絡與面向', NULL, TRUE, 200
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='系統帳務');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '繳費金流排障', '繳費金流排障', '帳務面向（子）：繳了未入帳/狀態沒跳的金流階段診斷', '系統帳務', TRUE, 210
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='繳費金流排障');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '帳單異常', '帳單異常', '帳務面向（子）：金額不對/沒產生/看不到的決定性判因', '系統帳務', TRUE, 220
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='帳單異常');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '發票', '發票', '帳務面向（子）：發票開立狀態/補開/作廢診斷', '系統帳務', TRUE, 230
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='發票');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '滯納金', '滯納金', '帳務面向（子）：滯納金規則講解（兩機制）與該筆結算', '系統帳務', TRUE, 240
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='滯納金');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '帳單設定引導', '帳單設定引導', '帳務面向（子）：收款/週期/期限/發送設定的輕引導', '系統帳務', TRUE, 250
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='帳單設定引導');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM category_config
    WHERE parent_value='系統帳務' AND is_active;
    RAISE NOTICE '✅ 系統帳務子面向：% / 5', n;
END $$;
