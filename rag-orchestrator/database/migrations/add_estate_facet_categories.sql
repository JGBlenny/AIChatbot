-- =====================================================
-- estate-conversational-facets 任務 2.1：物件管理面向分類（子分類掛既有母）
-- ⚠️ 母 `物件管理` 為既有分類（category_config id 61，10+ 筆知識已掛）——
--    重用不新建、不修改；本檔只補 2 子：物件操作引導／物件現況診斷。
-- 供三層脈絡疊加、config_for_category 進場、_domain_faces 衍生換面向集合。
-- 套用：psql "$DATABASE_URL" -f database/migrations/add_estate_facet_categories.sql
-- 冪等：category_value 已存在則不重插。
-- =====================================================

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '物件操作引導', '物件操作引導', '物件面向（子）：建立/批次上傳/編輯刊登/狀態功能/對外曝光與店舖的輕引導', '物件管理', TRUE, 510
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='物件操作引導');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '物件現況診斷', '物件現況診斷', '物件面向（子）：個案現況查詢（狀態/能否建約/租客可見性——ground 物件現值）', '物件管理', TRUE, 520
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='物件現況診斷');

DO $$
DECLARE n INT; m INT;
BEGIN
    SELECT COUNT(*) INTO n FROM category_config
    WHERE parent_value='物件管理' AND is_active;
    SELECT COUNT(*) INTO m FROM category_config
    WHERE category_value='物件管理' AND is_active;
    RAISE NOTICE '✅ 物件管理子面向：% / 2（母既存列：%，應為 1）', n, m;
END $$;
