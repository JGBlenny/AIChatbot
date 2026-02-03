-- 清理舊測試資料
DELETE FROM knowledge_base WHERE question_summary LIKE '測試-%' AND vendor_id = 1;

-- 插入各種測試資料
INSERT INTO knowledge_base (
    vendor_id, question_summary, answer,
    action_type, form_id,
    trigger_mode, trigger_keywords, immediate_prompt,
    business_types, target_user, priority, is_active
)
VALUES
    -- 1. NULL 觸發模式 (當 action_type = 'direct_answer' 時)
    (1, '測試-無後續動作', '社區規定說明：

• 禁止在陽台晾曬衣物
• 垃圾需分類投放
• 寵物需牽繩
• 保持安靜時段：22:00-08:00', 'direct_answer', NULL, NULL, NULL, NULL, '{"full_service"}', '{"customer"}', 60, true),

    -- 2. NULL 觸發模式 (當 action_type = 'form_fill' 時 - 模擬舊資料)
    (1, '測試-舊資料-NULL', '這是舊資料，trigger_mode 為 NULL

排查步驟：
1. 檢查電源
2. 檢查開關
3. 等待30秒

若問題仍存在，請提交報修。', 'form_fill', 'maintenance_request', NULL, NULL, NULL, '{"full_service"}', '{"customer"}', 50, true),

    -- 3. manual 觸發模式 (排查型) - 完整資料
    (1, '測試-排查型-完整', '冷氣不冷排查步驟：

1️⃣ 檢查溫度設定（建議 24-26°C）
2️⃣ 檢查濾網是否堵塞
3️⃣ 確認室外機運轉
4️⃣ 等待 10-15 分鐘

若排查後仍不冷，請提交維修請求。', 'form_fill', 'maintenance_request', 'manual', '{"還是不冷", "還是不行", "試過了還是不冷"}', NULL, '{"full_service"}', '{"customer"}', 80, true),

    -- 4. manual 觸發模式 - 空關鍵詞 (測試驗證)
    (1, '測試-排查型-空關鍵詞', '網路不通排查步驟：

1. 檢查路由器電源
2. 重啟路由器（拔插頭等 30 秒）
3. 檢查網路線是否鬆脫
4. 測試其他設備是否能連網

若仍無法連接，請提交報修。', 'form_fill', 'repair_request', 'manual', '{}', NULL, '{"full_service"}', '{"customer"}', 75, true),

    -- 5. immediate 觸發模式 (行動型) - 完整資料
    (1, '測試-行動型-完整', '租屋申請流程說明：

1️⃣ 填寫租屋申請表
2️⃣ 提供證件影本
3️⃣ 提供收入證明
4️⃣ 等待審核結果', 'form_fill', 'rental_application', 'immediate', NULL, '是否要填寫租屋申請表？', '{"full_service"}', '{"customer"}', 90, true),

    -- 6. immediate 觸發模式 - 空提示詞 (測試選填)
    (1, '測試-行動型-空提示詞', '維修申請說明：

1️⃣ 描述問題
2️⃣ 上傳照片
3️⃣ 選擇時段', 'form_fill', 'repair_request', 'immediate', NULL, '', '{"full_service"}', '{"customer"}', 70, true),

    -- 7. immediate 觸發模式 - NULL 提示詞
    (1, '測試-行動型-NULL提示詞', '報修流程：

1️⃣ 選擇報修類型
2️⃣ 填寫問題描述
3️⃣ 選擇時段', 'form_fill', 'maintenance_request', 'immediate', NULL, NULL, '{"full_service"}', '{"customer"}', 85, true);

-- 顯示插入結果
SELECT
    id,
    question_summary,
    action_type,
    COALESCE(trigger_mode, 'NULL') AS trigger_mode,
    form_id,
    COALESCE(array_length(trigger_keywords, 1), 0) AS keywords_count,
    LENGTH(COALESCE(immediate_prompt, '')) AS prompt_len
FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1
ORDER BY id DESC;

-- 詳細資訊
SELECT
    '=== 測試資料詳細資訊 ===' AS info;

SELECT
    id,
    LEFT(question_summary, 30) AS title,
    action_type AS action,
    trigger_mode AS mode,
    form_id AS form,
    trigger_keywords AS keywords,
    LEFT(COALESCE(immediate_prompt, 'NULL'), 40) AS prompt
FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1
ORDER BY trigger_mode NULLS FIRST, id;

-- 統計
SELECT '✅ 已準備 ' || COUNT(*) || ' 筆測試資料' AS message
FROM knowledge_base
WHERE question_summary LIKE '測試-%' AND vendor_id = 1;
