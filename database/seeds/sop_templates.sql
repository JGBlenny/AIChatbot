-- ========================================
-- SOP 新增 SQL 範本集
-- ========================================
-- 用途：提供常用的 SOP 新增範本，方便快速複製使用
-- 使用方式：根據需求選擇對應範本，修改參數後執行
-- 建立日期：2025-10-18
-- ========================================

-- ========================================
-- 範本 1: 新增簡單 SOP（不需金流判斷）
-- ========================================
-- 適用場景：物業規定、設備說明、一般流程等與金流無關的內容

INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
VALUES
    (1, '新分類名稱', '分類說明文字', 10)  -- 修改這裡
RETURNING id;  -- 記下返回的 category_id

-- 使用上一步返回的 category_id
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    item_number,
    item_name,
    content,
    requires_cashflow_check,
    related_intent_id,
    priority
) VALUES (
    123,  -- ← 修改為上一步返回的 category_id
    1,    -- ← 修改為目標 vendor_id
    1,    -- ← 修改為項次編號
    '項目名稱',  -- ← 修改為實際項目名稱
    '項目的詳細內容說明...',  -- ← 修改為實際內容
    FALSE,  -- 不需要金流判斷
    NULL,   -- ← 如有關聯意圖，填入 intent_id，否則保持 NULL
    100     -- ← 修改優先級（100=最高，0=最低）
);


-- ========================================
-- 範本 2: 新增金流敏感 SOP
-- ========================================
-- 適用場景：租金繳納、押金、收據發票等與金流相關的內容

INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    item_number,
    item_name,
    content,
    requires_cashflow_check,
    cashflow_through_company,
    cashflow_direct_to_landlord,
    related_intent_id,
    priority
) VALUES (
    123,  -- ← 修改為實際 category_id
    1,    -- ← 修改為目標 vendor_id
    2,    -- ← 修改為項次編號
    '項目名稱（如：租金繳納方式）',
    '基礎內容（通用版本）',
    TRUE,  -- 需要金流判斷
    '金流過我家版本內容：強調「公司收款」「系統自動處理」「主動通知」...',  -- ← 修改
    '金流不過我家版本內容：強調「房東收款」「自行確認」「系統僅提醒」...',  -- ← 修改
    6,     -- ← 修改為關聯的 intent_id（如：6=帳務查詢）
    90     -- ← 修改優先級
);


-- ========================================
-- 範本 3: 批次新增完整分類與多個項目
-- ========================================
-- 適用場景：新增一整個分類及其下的多個 SOP 項目

DO $$
DECLARE
    cat_id INTEGER;
    intent_id_target INTEGER := 15;  -- ← 修改為目標意圖 ID
    vendor_id_target INTEGER := 1;   -- ← 修改為目標業者 ID
BEGIN
    -- Step 1: 建立分類
    INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
    VALUES (vendor_id_target, '分類名稱', '分類說明', 10)  -- ← 修改這裡
    RETURNING id INTO cat_id;

    -- Step 2: 新增項目 1（通用型）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 1, '項目1名稱',  -- ← 修改
        '項目1的內容...',  -- ← 修改
        FALSE, intent_id_target, 100
    );

    -- Step 3: 新增項目 2（金流敏感型）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 2, '項目2名稱（金流敏感）',  -- ← 修改
        '基礎內容',  -- ← 修改
        TRUE,
        '金流過我家版本...',  -- ← 修改
        '金流不過我家版本...',  -- ← 修改
        intent_id_target, 90
    );

    -- Step 4: 新增項目 3（通用型）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 3, '項目3名稱',  -- ← 修改
        '項目3的內容...',  -- ← 修改
        FALSE, intent_id_target, 80
    );

    RAISE NOTICE '✅ 分類與項目建立完成（分類ID: %）', cat_id;
END $$;


-- ========================================
-- 範本 4: 為現有分類新增單一項目
-- ========================================
-- 適用場景：分類已存在，只需新增一個 SOP 項目

-- 先查詢分類 ID
SELECT id, category_name FROM vendor_sop_categories WHERE vendor_id = 1;

-- 使用查詢到的 category_id 新增項目
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    item_number,
    item_name,
    content,
    requires_cashflow_check,
    related_intent_id,
    priority
) VALUES (
    123,  -- ← 使用查詢到的 category_id
    1,    -- ← vendor_id
    10,   -- ← 新項目的編號（建議比現有最大編號+1）
    '新項目名稱',
    '新項目內容...',
    FALSE,
    NULL,
    60
);


-- ========================================
-- 範本 5: 建立或更新意圖
-- ========================================
-- 適用場景：需要新增意圖或更新現有意圖的關鍵字

-- 方案 A: 新增意圖（如果不存在）
INSERT INTO intents (name, description, keywords, is_active)
VALUES (
    '意圖名稱',  -- ← 修改
    '意圖描述',  -- ← 修改
    '["關鍵字1", "關鍵字2", "關鍵字3"]',  -- ← 修改（JSON 格式）
    TRUE
)
ON CONFLICT (name) DO NOTHING
RETURNING id;

-- 方案 B: 更新現有意圖的關鍵字
UPDATE intents
SET keywords = '["舊關鍵字1", "舊關鍵字2", "新關鍵字1", "新關鍵字2"]'  -- ← 修改
WHERE name = '意圖名稱';  -- ← 修改


-- ========================================
-- 範本 6: 更新現有 SOP 項目
-- ========================================
-- 適用場景：修改已存在的 SOP 內容

-- 先查詢要修改的項目
SELECT id, item_name, content
FROM vendor_sop_items
WHERE vendor_id = 1 AND item_name LIKE '%關鍵字%';

-- 更新項目內容
UPDATE vendor_sop_items
SET
    content = '更新後的內容...',  -- ← 修改
    requires_cashflow_check = TRUE,  -- ← 如需修改
    cashflow_through_company = '金流過我家版本...',  -- ← 如需新增/修改
    cashflow_direct_to_landlord = '金流不過我家版本...',  -- ← 如需新增/修改
    related_intent_id = 15,  -- ← 如需修改
    priority = 95,  -- ← 如需修改
    updated_at = CURRENT_TIMESTAMP
WHERE id = 456;  -- ← 使用查詢到的項目 ID


-- ========================================
-- 範本 7: 刪除 SOP 項目（軟刪除）
-- ========================================
-- 適用場景：停用某個 SOP 項目（不實際刪除）

UPDATE vendor_sop_items
SET
    is_active = FALSE,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 456;  -- ← 修改為要停用的項目 ID


-- ========================================
-- 範本 8: 複製 SOP 到其他業者
-- ========================================
-- 適用場景：將某業者的 SOP 複製給其他業者

DO $$
DECLARE
    source_vendor_id INTEGER := 1;    -- ← 來源業者 ID
    target_vendor_id INTEGER := 2;    -- ← 目標業者 ID
    old_cat_id INTEGER;
    new_cat_id INTEGER;
BEGIN
    -- 複製分類與項目
    FOR old_cat_id IN
        SELECT id FROM vendor_sop_categories
        WHERE vendor_id = source_vendor_id AND is_active = TRUE
    LOOP
        -- 複製分類
        INSERT INTO vendor_sop_categories (
            vendor_id, category_name, description, display_order
        )
        SELECT
            target_vendor_id, category_name, description, display_order
        FROM vendor_sop_categories
        WHERE id = old_cat_id
        RETURNING id INTO new_cat_id;

        -- 複製該分類下的所有項目
        INSERT INTO vendor_sop_items (
            category_id, vendor_id, item_number, item_name, content,
            requires_cashflow_check,
            cashflow_through_company,
            cashflow_direct_to_landlord,
            cashflow_mixed,
            requires_business_type_check,
            business_type_full_service,
            business_type_management,
            related_intent_id, priority
        )
        SELECT
            new_cat_id, target_vendor_id, item_number, item_name, content,
            requires_cashflow_check,
            cashflow_through_company,
            cashflow_direct_to_landlord,
            cashflow_mixed,
            requires_business_type_check,
            business_type_full_service,
            business_type_management,
            related_intent_id, priority
        FROM vendor_sop_items
        WHERE category_id = old_cat_id AND is_active = TRUE;

    END LOOP;

    RAISE NOTICE '✅ SOP 複製完成：業者 % → 業者 %', source_vendor_id, target_vendor_id;
END $$;


-- ========================================
-- 實用查詢腳本
-- ========================================

-- 查詢 1: 查看所有可用意圖
SELECT id, name, description, keywords
FROM intents
WHERE is_active = TRUE
ORDER BY name;

-- 查詢 2: 查看某業者的所有 SOP 分類
SELECT
    id,
    category_name,
    description,
    display_order,
    (SELECT COUNT(*) FROM vendor_sop_items WHERE category_id = vendor_sop_categories.id) AS item_count
FROM vendor_sop_categories
WHERE vendor_id = 1  -- ← 修改為目標業者 ID
ORDER BY display_order;

-- 查詢 3: 查看某分類下的所有 SOP 項目
SELECT
    item_number,
    item_name,
    LEFT(content, 50) AS content_preview,
    requires_cashflow_check,
    related_intent_id,
    priority
FROM vendor_sop_items
WHERE category_id = 123  -- ← 修改為目標分類 ID
ORDER BY item_number;

-- 查詢 4: 查看金流敏感的 SOP 項目
SELECT
    sc.category_name,
    si.item_name,
    si.requires_cashflow_check,
    CASE WHEN si.cashflow_through_company IS NOT NULL THEN '✓' ELSE '✗' END AS has_company_version,
    CASE WHEN si.cashflow_direct_to_landlord IS NOT NULL THEN '✓' ELSE '✗' END AS has_landlord_version
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
WHERE si.vendor_id = 1 AND si.requires_cashflow_check = TRUE
ORDER BY sc.display_order, si.item_number;

-- 查詢 5: 查看未關聯意圖的 SOP 項目（可能需要關聯）
SELECT
    sc.category_name,
    si.item_name,
    LEFT(si.content, 100) AS content_preview
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
WHERE si.vendor_id = 1
  AND si.related_intent_id IS NULL
  AND si.is_active = TRUE
ORDER BY sc.display_order, si.item_number;

-- 查詢 6: 檢查金流版本是否完整
SELECT
    sc.category_name,
    si.item_name,
    CASE
        WHEN si.cashflow_through_company IS NULL THEN '⚠️ 缺少金流過我家版本'
        WHEN si.cashflow_direct_to_landlord IS NULL THEN '⚠️ 缺少金流不過我家版本'
        ELSE '✓ 完整'
    END AS status
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
WHERE si.vendor_id = 1
  AND si.requires_cashflow_check = TRUE
  AND (si.cashflow_through_company IS NULL OR si.cashflow_direct_to_landlord IS NULL);

-- 查詢 7: 查看完整的 SOP 結構（使用內建檢視）
SELECT
    vendor_name,
    category_name,
    item_number,
    item_name,
    LEFT(content, 80) AS content_preview,
    requires_cashflow_check,
    related_intent_name,
    priority
FROM v_vendor_sop_full
WHERE vendor_id = 1  -- ← 修改為目標業者 ID
ORDER BY category_id, item_number;

-- 查詢 8: 統計各分類的 SOP 項目數量
SELECT
    sc.category_name,
    COUNT(si.id) AS total_items,
    COUNT(CASE WHEN si.requires_cashflow_check = TRUE THEN 1 END) AS cashflow_sensitive_items,
    COUNT(CASE WHEN si.related_intent_id IS NOT NULL THEN 1 END) AS items_with_intent
FROM vendor_sop_categories sc
LEFT JOIN vendor_sop_items si ON sc.id = si.category_id AND si.is_active = TRUE
WHERE sc.vendor_id = 1 AND sc.is_active = TRUE
GROUP BY sc.id, sc.category_name
ORDER BY sc.display_order;


-- ========================================
-- 完成
-- ========================================
\echo '📚 SOP 範本腳本載入完成'
\echo '💡 請根據需求選擇對應範本，修改參數後執行'
