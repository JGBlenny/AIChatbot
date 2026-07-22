-- Migration: 維護請求 SOP 範例資料
-- Date: 2026-01-22
-- Purpose: 插入維護相關的 SOP 項目，展示如何配置後續動作
--
-- 業務流程：
--   1. 用戶：「冷氣不冷」
--   2. 系統：返回 SOP 排查步驟
--   3. 用戶：「試過了，還是不行」
--   4. 系統：自動觸發維修表單

BEGIN;

-- ==========================================
-- 前置準備：確保維護分類存在
-- ==========================================
INSERT INTO vendor_sop_categories (vendor_id, category_name, display_order, is_active)
VALUES (NULL, '維護請求', 10, true)
ON CONFLICT DO NOTHING;

-- ==========================================
-- 冷氣維修 SOP 群組
-- ==========================================
INSERT INTO vendor_sop_groups (vendor_id, group_name, description, display_order, is_active)
VALUES (
    NULL,
    '冷氣維修',
    '冷氣相關問題的排查與處理流程',
    10,
    true
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- SOP 項目 1: 冷氣無法啟動
-- ==========================================
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    group_id,
    item_number,
    item_name,
    content,
    priority,
    is_active,

    -- 後續動作配置
    next_action,
    next_form_id,
    next_api_config,
    trigger_keywords,
    followup_prompt
)
VALUES (
    (SELECT id FROM vendor_sop_categories WHERE category_name = '維護請求' AND vendor_id IS NULL LIMIT 1),
    NULL,  -- 全局 SOP
    (SELECT id FROM vendor_sop_groups WHERE group_name = '冷氣維修' AND vendor_id IS NULL LIMIT 1),
    1,
    '空調無法啟動',

    -- SOP 內容（排查步驟）
    '【排查步驟】
1️⃣ 檢查電源插座是否正常
   - 確認插頭是否鬆脫
   - 嘗試插入其他電器測試插座

2️⃣ 檢查控制面板
   - 確認顯示燈是否亮起
   - 檢查是否有錯誤代碼顯示

3️⃣ 檢查遙控器
   - 更換遙控器電池
   - 確認遙控器對準室內機

4️⃣ 檢查電箱
   - 確認冷氣專用的斷路器是否跳掉
   - 如果跳掉，嘗試重新推上

若以上步驟都無法解決，請提交維修請求。',

    10,
    true,

    -- 後續動作：填寫維修表單並調用 API
    'form_then_api',
    'maintenance_troubleshooting',  -- 跳過分類表單，直接進入詳細排查表單
    '{
        "endpoint": "maintenance_request",
        "params": {
            "problem_category": "ac_maintenance",
            "specific_problem": "ac_not_starting",
            "urgency_level": "urgent"
        },
        "combine_with_knowledge": false
    }'::jsonb,

    -- 觸發關鍵詞（用戶說這些話時，自動觸發表單）
    ARRAY[
        '還是不行',
        '試過了',
        '沒用',
        '都試過了',
        '都不行',
        '需要維修',
        '請幫我報修',
        '請維修人員來',
        '無法解決'
    ],

    -- 觸發時的引導語
    '好的，我來協助您提交維修請求。請提供一些詳細資訊，以便我們安排最合適的維修人員。'
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- SOP 項目 2: 冷氣不冷
-- ==========================================
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    group_id,
    item_number,
    item_name,
    content,
    priority,
    is_active,
    next_action,
    next_form_id,
    next_api_config,
    trigger_keywords,
    followup_prompt
)
VALUES (
    (SELECT id FROM vendor_sop_categories WHERE category_name = '維護請求' AND vendor_id IS NULL LIMIT 1),
    NULL,
    (SELECT id FROM vendor_sop_groups WHERE group_name = '冷氣維修' AND vendor_id IS NULL LIMIT 1),
    2,
    '冷氣不冷',

    '【排查步驟】
1️⃣ 檢查設定溫度
   - 確認溫度設定是否低於室溫（建議 24-26°C）
   - 確認模式是否設定為「冷氣模式」（不是送風或除濕）

2️⃣ 檢查濾網
   - 打開室內機面板
   - 取出濾網檢查是否有灰塵堵塞
   - 用水清洗濾網並晾乾（建議每月清洗一次）

3️⃣ 檢查室外機
   - 確認室外機是否正常運轉（有聲音和震動）
   - 檢查室外機周圍是否有遮擋物

4️⃣ 等待時間
   - 剛開機需等待 10-15 分鐘才會明顯感到冷
   - 房間較大需要更長時間

若以上步驟都無法解決，或濾網清洗後仍不冷，請提交維修請求。',

    10,
    true,
    'form_then_api',
    'maintenance_troubleshooting',
    '{
        "endpoint": "maintenance_request",
        "params": {
            "problem_category": "ac_maintenance",
            "specific_problem": "ac_not_cooling",
            "urgency_level": "urgent"
        },
        "combine_with_knowledge": false
    }'::jsonb,
    ARRAY['還是不冷', '試過了', '濾網清過了', '需要維修', '請幫我報修', '都試過了', '無法解決'],
    '好的，我來協助您提交維修請求。請提供一些詳細資訊。'
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- SOP 項目 3: 冷氣漏水
-- ==========================================
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    group_id,
    item_number,
    item_name,
    content,
    priority,
    is_active,
    next_action,
    next_form_id,
    next_api_config,
    trigger_keywords,
    followup_prompt
)
VALUES (
    (SELECT id FROM vendor_sop_categories WHERE category_name = '維護請求' AND vendor_id IS NULL LIMIT 1),
    NULL,
    (SELECT id FROM vendor_sop_groups WHERE group_name = '冷氣維修' AND vendor_id IS NULL LIMIT 1),
    3,
    '冷氣漏水',

    '【緊急處理】
⚠️ 請先用容器收集漏水，避免損壞地板或家具。

【排查步驟】
1️⃣ 檢查排水管
   - 確認排水管是否堵塞
   - 檢查排水管出口是否有水流出

2️⃣ 檢查傾斜度
   - 室內機應保持水平或略向排水側傾斜
   - 目視檢查是否明顯歪斜

3️⃣ 檢查濾網
   - 濾網堵塞也可能導致漏水
   - 取出濾網清洗

若漏水嚴重或排查後仍漏水，請立即提交緊急維修請求。',

    20,  -- 高優先級
    true,
    'form_then_api',
    'maintenance_troubleshooting',
    '{
        "endpoint": "maintenance_request",
        "params": {
            "problem_category": "ac_maintenance",
            "specific_problem": "ac_water_leak",
            "urgency_level": "urgent"
        },
        "combine_with_knowledge": false
    }'::jsonb,
    ARRAY['還在漏', '漏水很嚴重', '需要維修', '請快來修', '緊急', '請幫我報修'],
    '了解，冷氣漏水需要盡快處理。我來協助您提交緊急維修請求。'
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- 漏水問題 SOP 群組
-- ==========================================
INSERT INTO vendor_sop_groups (vendor_id, group_name, description, display_order, is_active)
VALUES (
    NULL,
    '漏水問題',
    '漏水相關問題的緊急處理與排查流程',
    20,
    true
)
ON CONFLICT DO NOTHING;

-- ==========================================
-- SOP 項目 4: 天花板漏水
-- ==========================================
INSERT INTO vendor_sop_items (
    category_id,
    vendor_id,
    group_id,
    item_number,
    item_name,
    content,
    priority,
    is_active,
    next_action,
    next_form_id,
    next_api_config,
    trigger_keywords,
    followup_prompt
)
VALUES (
    (SELECT id FROM vendor_sop_categories WHERE category_name = '維護請求' AND vendor_id IS NULL LIMIT 1),
    NULL,
    (SELECT id FROM vendor_sop_groups WHERE group_name = '漏水問題' AND vendor_id IS NULL LIMIT 1),
    1,
    '天花板漏水',

    '【緊急處理】
🚨 這是緊急狀況！請立即採取以下措施：

1️⃣ 使用容器收集漏水
   - 放置水桶或臉盆接水
   - 移開漏水處下方的物品

2️⃣ 關閉電源
   - 如果漏水接近電器或電燈，請關閉該區域電源
   - 避免觸電風險

3️⃣ 通知樓上住戶
   - 如果是公寓，請聯絡樓上住戶檢查
   - 可能是樓上的水管或浴室漏水

4️⃣ 拍照記錄
   - 拍下漏水位置和損壞情況
   - 用於後續賠償和修繕

請立即提交緊急維修請求，我們會在 1 小時內安排人員處理。',

    30,  -- 最高優先級
    true,
    'form_then_api',
    'maintenance_troubleshooting',
    '{
        "endpoint": "maintenance_request",
        "params": {
            "problem_category": "water_leak",
            "specific_problem": "ceiling_leak",
            "urgency_level": "critical"
        },
        "combine_with_knowledge": false
    }'::jsonb,
    ARRAY['好的', '了解', '我要報修', '請快來', '緊急', '很嚴重', '漏很多'],
    '收到！天花板漏水是緊急狀況，我立即為您安排維修。請提供詳細資訊。'
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ==========================================
-- 驗證
-- ==========================================
DO $$
DECLARE
    sop_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO sop_count
    FROM vendor_sop_items
    WHERE next_action != 'none';

    IF sop_count > 0 THEN
        RAISE NOTICE '✓ 成功插入 % 個帶有後續動作的 SOP 項目', sop_count;
    ELSE
        RAISE WARNING '⚠ 沒有找到帶有後續動作的 SOP 項目';
    END IF;
END $$;
