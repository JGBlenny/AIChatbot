-- =====================================================
-- contract-conversational-facets 任務 3.1：合約面向分類擴充 v2（category_config 子分類 ×5）
-- 於母『系統合約』下新增 5 個子面向：合約異動／退租收尾／續約／建約引導／簽署排障。
-- 供 get_system_context 沿父鏈疊加（母共用+子面向）、config_for_category 進場路由、
-- _domain_faces 由母分類自動衍生換面向集合（含既有子『狀態判斷』共 6 面向）。
-- 前置：add_contract_facet_categories.sql（母『系統合約』＋子『狀態判斷』）；
--       本檔自帶母分類冪等補建，單獨套用亦可。
-- 套用：psql "$DATABASE_URL" -f database/migrations/add_contract_facet_categories_v2.sql
-- 冪等：category_value 已存在則不重插。
-- =====================================================

-- 母分類保底（與 v1 相同條件，冪等）
INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '系統合約', '系統合約', '合約診斷領域（母分類）：合約領域共用的系統脈絡與面向', NULL, TRUE, 100
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='系統合約');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '合約異動', '合約異動', '合約面向（子）：改合約內容的出口分流（直改/取消退回/複製重建或異動申請書）', '系統合約', TRUE, 110
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='合約異動');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '退租收尾', '退租收尾', '合約面向（子）：退租/提前解約的收尾步驟推進（點退→封存→轉歷史）', '系統合約', TRUE, 120
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='退租收尾');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '續約', '續約', '合約面向（子）：系統續約 vs 重建新約取捨、重簽方式、續約鏈', '系統合約', TRUE, 130
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='續約');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '建約引導', '建約引導', '合約面向（子）：建約方式/對象型態兩輪分流後知識收尾（無 API grounding）', '系統合約', TRUE, 140
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='建約引導');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '簽署排障', '簽署排障', '合約面向（子）：簽署卡關排查（還差誰簽/發送通道/效期/信箱錯配）', '系統合約', TRUE, 150
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='簽署排障');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM category_config
    WHERE parent_value='系統合約' AND is_active
      AND category_value IN ('狀態判斷','合約異動','退租收尾','續約','建約引導','簽署排障');
    RAISE NOTICE '✅ 系統合約子面向：% / 6（狀態判斷＋新 5 面向；_domain_faces 據此衍生換面向集合）', n;
END $$;
