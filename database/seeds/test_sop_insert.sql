-- 測試 SOP 資料插入腳本
-- 用途：測試金流模式分支邏輯

-- ========================================
-- 1. 為業者 1（包租型）建立測試分類
-- ========================================

INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
VALUES
  (1, '租金繳費相關', '租金繳費方式、收據、遲付處理等', 1);

-- 獲取分類 ID
DO $$
DECLARE
    cat_id_1 INTEGER;
    intent_id_billing INTEGER := 6;  -- 帳務查詢意圖
BEGIN
    -- 獲取剛才建立的分類 ID
    SELECT id INTO cat_id_1 FROM vendor_sop_categories WHERE vendor_id = 1 AND category_name = '租金繳費相關';

    -- 項目 1：租金支付方式（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id_1, 1, 1, '租金支付方式',
        '您的租金可通過多種方式繳納',  -- 基礎內容
        TRUE,  -- 需要金流模式判斷
        '登入JGB系統查看公司收款帳號，可通過銀行轉帳、信用卡支付或超商代碼繳款。系統會在收款後主動通知您。',  -- 金流過我家
        '請向房東索取收款帳號，建議使用銀行轉帳並留存交易記錄。JGB系統僅提供繳款提醒服務。',  -- 金流不過我家
        intent_id_billing, 100
    );

    -- 項目 2：收據或發票（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id_1, 1, 2, '收據或發票如何取得',
        '租金繳費後可取得收據或發票',
        TRUE,
        '支付後，JGB系統會自動生成收據或電子發票，並通過郵件發送給您。您也可以登入管理系統查閱歷史記錄。',
        '請向房東索取收據，JGB系統僅保存繳款提醒記錄供您參考。',
        intent_id_billing, 90
    );

    -- 項目 3：租金遲付處理（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id_1, 1, 3, '如果租客遲付租金',
        '若未按時繳納租金，將會有相關處理流程',
        TRUE,
        'JGB系統會自動發送催繳通知並依約收取滯納金。請您儘速完成繳款，避免影響您的信用記錄。',
        '房東會處理遲付事宜，JGB系統僅協助發送提醒通知。請您主動聯繫房東說明情況。',
        intent_id_billing, 80
    );

    -- 項目 4：押金退還（金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id_1, 1, 4, '押金退還方式',
        '租約結束後，押金將依據房屋狀況退還',
        TRUE,
        '押金由公司收取並專戶保管，租約結束後我們會進行房屋檢查，確認狀況良好後將於7個工作天內退還至您指定帳戶。',
        '押金由房東收取並保管，租約結束後請與房東確認退還時間與方式。JGB可協助提供標準的點交檢核表。',
        1, 70  -- 關聯到退租流程
    );

    -- 項目 5：租金金額查詢（非金流敏感）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id_1, 1, 5, '如何查詢當月租金',
        '您可以登入JGB管理系統查看當月租金帳單，包含租金、管理費、水電費等明細。系統會在每月初自動產生帳單。',
        FALSE,  -- 不需要金流模式判斷
        intent_id_billing, 60
    );

END $$;

-- ========================================
-- 2. 為業者 2（代管型）建立測試分類
-- ========================================

INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
VALUES
  (2, '租金繳費相關', '租金繳費方式、收據、遲付處理等', 1);

-- 獲取分類 ID 並插入項目
DO $$
DECLARE
    cat_id_2 INTEGER;
    intent_id_billing INTEGER := 6;
BEGIN
    SELECT id INTO cat_id_2 FROM vendor_sop_categories WHERE vendor_id = 2 AND category_name = '租金繳費相關';

    -- 為業者 2 建立相同結構的SOP（會根據金流模式自動調整內容）
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES
      (cat_id_2, 2, 1, '租金支付方式', '您的租金可通過多種方式繳納', TRUE,
       '登入JGB系統查看公司收款帳號，可通過銀行轉帳、信用卡支付或超商代碼繳款。',
       '請向房東索取收款帳號，建議使用銀行轉帳並留存交易記錄。JGB系統僅提供繳款提醒服務。',
       intent_id_billing, 100),

      (cat_id_2, 2, 2, '收據或發票如何取得', '租金繳費後可取得收據或發票', TRUE,
       '支付後，JGB系統會自動生成收據或電子發票。',
       '請向房東索取收據，JGB系統僅保存繳款提醒記錄。',
       intent_id_billing, 90);
END $$;

-- ========================================
-- 完成
-- ========================================

-- 查詢插入結果
SELECT
    v.id AS vendor_id,
    v.name AS vendor_name,
    v.business_type,
    v.cashflow_model,
    sc.id AS category_id,
    sc.category_name,
    COUNT(si.id) AS item_count
FROM vendors v
LEFT JOIN vendor_sop_categories sc ON v.id = sc.vendor_id
LEFT JOIN vendor_sop_items si ON sc.id = si.category_id
WHERE v.id IN (1, 2)
GROUP BY v.id, v.name, v.business_type, v.cashflow_model, sc.id, sc.category_name
ORDER BY v.id;

\echo '✅ 測試 SOP 資料插入完成'
