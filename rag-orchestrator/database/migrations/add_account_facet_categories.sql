-- =====================================================
-- account-conversational-facets 任務 2.1：帳號面向分類（category_config 母子）
-- 母『帳號中心』→ 子：註冊驗證排障／登入排障／帳號綁定異動／團隊成員權限。
-- 外部類（註冊驗證排障/登入排障：進不了系統的人、業者代問）與內部類（綁定異動/團隊權限：
-- 已登入業者）同母——母層脈絡刻意薄（僅名詞對照），兩類機制細節全在子層（R1.3）。
-- 套用：psql "$DATABASE_URL" -f database/migrations/add_account_facet_categories.sql
-- 冪等：category_value 已存在則不重插。
-- =====================================================

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '帳號中心', '帳號中心', '帳號對話領域（母分類）：註冊/登入/綁定/團隊權限共用薄層脈絡與面向', NULL, TRUE, 300
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='帳號中心');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '註冊驗證排障', '註冊驗證排障', '帳號面向（子/外部類）：租客註冊卡住/驗證失敗的分支排障', '帳號中心', TRUE, 310
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='註冊驗證排障');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '登入排障', '登入排障', '帳號面向（子/外部類）：登不進去/登入後看不到資料的判因（可查合約現值）', '帳號中心', TRUE, 320
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='登入排障');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '帳號綁定異動', '帳號綁定異動', '帳號面向（子/內部類）：換綁/解綁/帳號資料修改的自助與申請分流', '帳號中心', TRUE, 330
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='帳號綁定異動');

INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '團隊成員權限', '團隊成員權限', '帳號面向（子/內部類）：成員可見範圍與權限設定的判因引導', '帳號中心', TRUE, 340
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='團隊成員權限');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM category_config
    WHERE parent_value='帳號中心' AND is_active;
    RAISE NOTICE '✅ 帳號中心子面向：% / 4', n;
END $$;
