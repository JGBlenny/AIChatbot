-- =====================================================
-- iot-conversational-facets 任務 2.1：智慧設備面向分類（category_config 母子）
-- 母『智慧設備』→ 子：電表排障／IoT設定引導。
-- 供三層脈絡疊加、config_for_category 進場、_domain_faces 衍生換面向集合。
-- 套用：psql "$DATABASE_URL" -f database/migrations/add_iot_facet_categories.sql
-- 冪等：category_value 已存在則不重插。
-- =====================================================

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '智慧設備', '智慧設備', 'IoT 對話領域（母分類）：電表/門鎖等智慧設備共用薄層脈絡與面向', NULL, TRUE, 400
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='智慧設備');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '電表排障', '電表排障', 'IoT 面向（子）：未給電/離線/度數異常的決定性判因（ground 電表現值）', '智慧設備', TRUE, 410
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='電表排障');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT 'IoT設定引導', 'IoT設定引導', 'IoT 面向（子）：電表串接/儲值單價/門鎖密碼/起始日的輕引導', '智慧設備', TRUE, 420
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='IoT設定引導');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM category_config
    WHERE parent_value='智慧設備' AND is_active;
    RAISE NOTICE '✅ 智慧設備子面向：% / 2', n;
END $$;
