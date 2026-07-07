-- =====================================================
-- domain-conversational-facets（面向模型）：合約面向分類（category_config 母子）
-- 建立領域面向的分類骨架：母『系統合約』→ 子『狀態判斷』。
-- 供 get_system_context 沿父鏈疊加（母共用+子面向）、config_for_category 子→母路由展開。
-- 套用：psql "$DATABASE_URL" -f database/migrations/add_contract_facet_categories.sql
-- 冪等：category_value 已存在則不重插。
-- =====================================================

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '系統合約', '系統合約', '合約診斷領域（母分類）：合約領域共用的系統脈絡與面向', NULL, TRUE, 100
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='系統合約');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '狀態判斷', '狀態判斷', '合約面向（子）：合約狀態/流轉/下一步判斷', '系統合約', TRUE, 100
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='狀態判斷');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM category_config WHERE category_value IN ('系統合約','狀態判斷');
    RAISE NOTICE '✅ 合約面向分類：% / 2（系統合約母 + 狀態判斷子）', n;
END $$;
