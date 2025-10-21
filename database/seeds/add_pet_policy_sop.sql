-- ========================================
-- 新增「寵物飼養規定」SOP
-- ========================================
-- 用途：解決回測報告中發現的知識缺口
-- 問題：「我可以養寵物嗎？」類問題無知識來源
-- 建立日期：2025-10-18
-- ========================================

-- ========================================
-- Step 1: 確認或建立「寵物飼養」意圖
-- ========================================

-- 先檢查意圖是否已存在
SELECT id, name, keywords FROM intents WHERE name = '寵物飼養';

-- 如果不存在，建立新意圖；如果存在，更新關鍵字
INSERT INTO intents (name, description, keywords, is_active)
VALUES (
    '寵物飼養',
    '寵物飼養許可、規範、費用、押金等相關問題',
    '["寵物", "養貓", "養狗", "飼養", "寵物押金", "寵物費用", "飼養規定", "可以養寵物嗎", "能養動物嗎", "寵物政策", "允許養寵物", "寵物許可", "貓狗"]',
    TRUE
)
ON CONFLICT (name) DO UPDATE
SET keywords = '["寵物", "養貓", "養狗", "飼養", "寵物押金", "寵物費用", "飼養規定", "可以養寵物嗎", "能養動物嗎", "寵物政策", "允許養寵物", "寵物許可", "貓狗"]',
    description = '寵物飼養許可、規範、費用、押金等相關問題'
RETURNING id;  -- 記下返回的 ID，假設為 15


-- ========================================
-- Step 2: 為業者 1 建立「寵物飼養規定」SOP
-- ========================================

DO $$
DECLARE
    cat_id INTEGER;
    intent_id_pet INTEGER;
    intent_id_contract INTEGER := 1;  -- 合約規定意圖
    vendor_id_target INTEGER := 1;  -- 甲山林（包租型、金流過我家）
BEGIN
    -- 獲取寵物飼養意圖 ID
    SELECT id INTO intent_id_pet FROM intents WHERE name = '寵物飼養';

    IF intent_id_pet IS NULL THEN
        RAISE EXCEPTION '❌ 找不到「寵物飼養」意圖，請先執行 Step 1';
    END IF;

    -- 建立分類
    INSERT INTO vendor_sop_categories (vendor_id, category_name, description, display_order)
    VALUES (vendor_id_target, '寵物飼養規定', '寵物飼養許可、限制、費用、押金、責任與違規處理', 11)
    RETURNING id INTO cat_id;

    RAISE NOTICE '✅ 建立分類成功 (ID: %)', cat_id;

    -- ========================================
    -- 項目 1: 寵物飼養許可（通用型，關聯「寵物飼養」&「合約規定」）
    -- ========================================
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 1, '是否允許飼養寵物',
        '本物業允許房客飼養寵物，但需遵守以下規定：

1️⃣ **事前申請**：需事前提出書面申請並獲得公司同意，未經許可不得飼養
2️⃣ **寵物限制**：僅限小型犬貓，體重不超過10公斤，每戶最多2隻
3️⃣ **押金繳納**：需額外繳交寵物押金NT$5,000元
4️⃣ **遵守規範**：須遵守社區寵物管理規範及本公司寵物飼養守則

申請方式：登入JGB系統填寫「寵物飼養申請表」，上傳寵物照片及疫苗證明，我們會在3個工作天內回覆審核結果。',
        FALSE,  -- 不需要金流判斷
        intent_id_pet,
        100
    );

    -- ========================================
    -- 項目 2: 寵物押金繳納（金流敏感）
    -- ========================================
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 2, '寵物押金如何繳納',
        '寵物押金為NT$5,000元，可透過多種方式繳納',
        TRUE,  -- 需要金流判斷
        '登入JGB系統查看公司收款帳號，寵物押金NT$5,000元可透過以下方式繳納：
- 銀行轉帳：轉入指定公司帳戶
- 信用卡支付：系統線上刷卡
- 超商代碼繳款：產生繳款代碼至超商繳納

系統會在收款後主動發送確認通知，並在您的帳戶中顯示押金記錄。',
        '請向房東索取收款帳號，寵物押金NT$5,000元建議使用銀行轉帳並留存交易記錄作為憑證。

JGB系統僅提供繳款提醒服務，實際收款由房東負責。完成繳款後請通知房東確認，並索取收據或證明文件。',
        intent_id_pet,
        95
    );

    -- ========================================
    -- 項目 3: 寵物飼養規範與責任（通用型）
    -- ========================================
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 3, '寵物飼養規範',
        '為維護社區環境品質與鄰居居住安寧，房客需遵守以下寵物飼養規範：

🔊 **噪音控制**
- 訓練寵物避免過度吠叫，特別是夜間（22:00-07:00）
- 若鄰居投訴噪音問題，需積極改善

🧹 **環境衛生**
- 定期清潔居住環境，保持衛生無異味
- 不得讓寵物在陽台、走廊等公共區域排泄
- 外出遛狗需立即清理排泄物

🚶 **外出規範**
- 外出時須使用牽繩或寵物籠
- 搭乘電梯時若有其他住戶，應詢問是否介意
- 不得讓寵物進入社區兒童遊戲區、游泳池等特定區域

⚠️ **安全責任**
- 房客需對寵物行為負完全責任
- 若寵物造成他人受傷或財物損壞，由房客負責賠償
- 需確保寵物疫苗接種完整，定期健康檢查

違規處理：
- 首次違規：書面警告
- 再次違規：加收清潔費或違約金
- 嚴重或屢次違規：可能終止租約',
        FALSE,
        intent_id_pet,
        85
    );

    -- ========================================
    -- 項目 4: 寵物造成損壞的處理（金流敏感）
    -- ========================================
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 4, '寵物造成損壞如何處理',
        '若寵物造成房屋設施損壞，將依據實際損壞狀況處理',
        TRUE,
        '租約期間若寵物造成房屋設施損壞（如牆面抓痕、地板咬痕、傢俱損壞等），公司會進行評估：

1️⃣ **輕微損壞**：從寵物押金中扣除修繕費用
2️⃣ **嚴重損壞**：若超過押金金額，房客需額外支付差額

我們會提供損壞照片、修繕報價單供您確認，所有扣款項目都會詳細記錄在系統中。若您對扣款金額有疑問，可申請複查。',
        '租約期間若寵物造成房屋設施損壞，房東會進行評估並與您協商修繕費用。

建議您：
- 在入住時拍照記錄原始狀況
- 與房東保持良好溝通
- 若有爭議，JGB可協助提供第三方修繕報價參考',
        intent_id_pet,
        75
    );

    -- ========================================
    -- 項目 5: 寵物押金退還（金流敏感）
    -- ========================================
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 5, '寵物押金退還方式',
        '租約結束後，寵物押金將依據房屋狀況退還',
        TRUE,
        '寵物押金由公司專戶保管，租約結束退租時會進行以下流程：

1️⃣ **房屋檢查**：公司人員會檢查房屋是否有寵物造成的損壞
2️⃣ **扣款計算**：若有損壞，會從押金中扣除修繕費用，並提供明細
3️⃣ **退款處理**：確認無損壞或扣除費用後，將於7個工作天內退還至您指定帳戶

您會在系統中看到完整的退款記錄與扣款明細（如有）。',
        '寵物押金由房東收取並保管，租約結束後：

1️⃣ **與房東協商**：請與房東確認退還時間與方式
2️⃣ **房屋檢查**：建議雙方共同檢查房屋狀況，拍照存證
3️⃣ **扣款憑證**：若有扣款，請房東提供修繕收據或照片

JGB可協助提供標準的退租檢核表，幫助您與房東順利完成退租程序。',
        intent_id_contract,  -- 也關聯到合約規定
        70
    );

    -- ========================================
    -- 項目 6: 不允許飼養的寵物類型（通用型）
    -- ========================================
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check, related_intent_id, priority
    ) VALUES (
        cat_id, vendor_id_target, 6, '哪些寵物不允許飼養',
        '基於安全、衛生及社區規範考量，以下寵物類型不允許飼養：

❌ **禁止飼養的寵物**
- 大型犬（體重超過10公斤）
- 具攻擊性品種（如比特犬、土佐犬等）
- 爬蟲類（蛇、蜥蜴等）
- 大型鳥類（鸚鵡除外）
- 任何具有危險性或異味嚴重的動物

⚠️ **特殊說明**
- 若您的寵物接近10公斤重量上限，申請時請提供體重證明
- 導盲犬、導聽犬等工作犬不受品種限制，但需提供相關證明

若不確定您的寵物是否符合規定，請在申請時詳細描述品種與體型，我們會協助判斷。',
        FALSE,
        intent_id_pet,
        65
    );

    RAISE NOTICE '✅ 寵物飼養規定 SOP 建立完成！';
    RAISE NOTICE '   - 分類ID: %', cat_id;
    RAISE NOTICE '   - 項目數: 6';
    RAISE NOTICE '   - 金流敏感項目: 3（押金繳納、損壞處理、押金退還）';

END $$;


-- ========================================
-- Step 3: 驗證建立結果
-- ========================================

SELECT
    sc.category_name,
    si.item_number,
    si.item_name,
    si.requires_cashflow_check,
    CASE
        WHEN si.cashflow_through_company IS NOT NULL THEN '✓'
        ELSE '✗'
    END AS 金流過我家版本,
    CASE
        WHEN si.cashflow_direct_to_landlord IS NOT NULL THEN '✓'
        ELSE '✗'
    END AS 金流不過我家版本,
    i.name AS 關聯意圖,
    si.priority AS 優先級
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
LEFT JOIN intents i ON si.related_intent_id = i.id
WHERE sc.category_name = '寵物飼養規定' AND si.vendor_id = 1
ORDER BY si.item_number;


-- ========================================
-- Step 4: 複製到其他業者（可選）
-- ========================================

-- 如需複製到業者 2（信義，代管型、金流不過我家）
-- 請取消以下註解並執行：

/*
DO $$
DECLARE
    source_vendor_id INTEGER := 1;
    target_vendor_id INTEGER := 2;  -- 修改為目標業者 ID
    old_cat_id INTEGER;
    new_cat_id INTEGER;
BEGIN
    -- 獲取來源分類 ID
    SELECT id INTO old_cat_id
    FROM vendor_sop_categories
    WHERE vendor_id = source_vendor_id AND category_name = '寵物飼養規定';

    IF old_cat_id IS NULL THEN
        RAISE EXCEPTION '❌ 找不到來源分類';
    END IF;

    -- 複製分類
    INSERT INTO vendor_sop_categories (
        vendor_id, category_name, description, display_order
    )
    SELECT
        target_vendor_id, category_name, description, display_order
    FROM vendor_sop_categories
    WHERE id = old_cat_id
    RETURNING id INTO new_cat_id;

    -- 複製所有項目
    INSERT INTO vendor_sop_items (
        category_id, vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    )
    SELECT
        new_cat_id, target_vendor_id, item_number, item_name, content,
        requires_cashflow_check,
        cashflow_through_company,
        cashflow_direct_to_landlord,
        related_intent_id, priority
    FROM vendor_sop_items
    WHERE category_id = old_cat_id AND is_active = TRUE;

    RAISE NOTICE '✅ SOP 已複製到業者 %', target_vendor_id;
END $$;
*/


-- ========================================
-- Step 5: 測試查詢（模擬 RAG 檢索）
-- ========================================

-- 模擬問題：「我可以養寵物嗎？」
-- 預期應該檢索到「是否允許飼養寵物」項目

SELECT
    item_name,
    LEFT(content, 200) AS 內容預覽,
    priority
FROM vendor_sop_items si
INNER JOIN vendor_sop_categories sc ON si.category_id = sc.id
WHERE si.vendor_id = 1
  AND sc.category_name = '寵物飼養規定'
  AND si.item_name LIKE '%允許%'
ORDER BY priority DESC
LIMIT 1;


-- ========================================
-- 完成
-- ========================================

\echo ''
\echo '✅ 寵物飼養規定 SOP 新增完成！'
\echo ''
\echo '📊 統計資訊：'
\echo '   - 新增分類：寵物飼養規定'
\echo '   - SOP 項目：6 個'
\echo '   - 金流敏感：3 個（押金繳納、損壞處理、押金退還）'
\echo '   - 通用項目：3 個（飼養許可、規範、禁止類型）'
\echo ''
\echo '🎯 下一步建議：'
\echo '   1. 執行回測驗證：python3 scripts/knowledge_extraction/backtest_framework.py'
\echo '   2. 測試問題：「我可以養寵物嗎？」應有正確答案'
\echo '   3. 如需複製到其他業者，請執行 Step 4 的腳本'
\echo ''
