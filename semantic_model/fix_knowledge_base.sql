-- 修正知識庫：確保電費帳單查詢對應到表單 1296
-- ================================================

-- 1. 先檢查是否已有電費相關的知識點
SELECT id, question_summary, form_id, action_type
FROM knowledge_base
WHERE question_summary LIKE '%電費%'
  AND (question_summary LIKE '%帳單%' OR question_summary LIKE '%寄送%')
LIMIT 10;

-- 2. 更新現有電費相關知識點，設定正確的表單 ID
UPDATE knowledge_base
SET form_id = 1296,
    action_type = 'form_fill',
    updated_at = NOW()
WHERE question_summary LIKE '%電費%帳單%'
   OR question_summary LIKE '%電費%寄送%'
   OR question_summary LIKE '%查詢%電費%';

-- 3. 如果沒有找到相關知識點，則新增
INSERT INTO knowledge_base (
    question_summary,
    answer,
    form_id,
    action_type,
    priority,
    keywords,
    scope,
    is_active,
    created_at,
    updated_at
)
SELECT
    '電費帳單寄送區間查詢',
    '請填寫表單查詢您的電費帳單寄送區間。電費帳單會在單月或雙月寄送，具體時間依據您的用電區域。',
    1296,
    'form_fill',
    100,
    ARRAY['電費', '帳單', '寄送', '區間', '單月', '雙月', '查詢', '何時', '幾號', '週期'],
    'billing',
    true,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE form_id = 1296
    AND question_summary LIKE '%電費%'
);

-- 4. 確保各種變化型都能匹配（新增多個相關知識點）
INSERT INTO knowledge_base (
    question_summary,
    answer,
    form_id,
    action_type,
    priority,
    keywords,
    scope,
    is_active
) VALUES
    ('電費帳單何時寄送', '電費帳單寄送時間依據單雙月區分，請填寫查詢表單。', 1296, 'form_fill', 100, ARRAY['電費', '帳單', '何時', '寄送'], 'billing', true),
    ('電費幾號寄', '電費帳單寄送日期查詢，請使用查詢表單。', 1296, 'form_fill', 100, ARRAY['電費', '幾號', '寄'], 'billing', true),
    ('單月電費寄送時間', '單月電費帳單寄送時間查詢。', 1296, 'form_fill', 100, ARRAY['單月', '電費', '寄送', '時間'], 'billing', true),
    ('雙月電費寄送時間', '雙月電費帳單寄送時間查詢。', 1296, 'form_fill', 100, ARRAY['雙月', '電費', '寄送', '時間'], 'billing', true),
    ('查詢電費寄送區間', '查詢您的電費帳單寄送區間。', 1296, 'form_fill', 100, ARRAY['查詢', '電費', '寄送', '區間'], 'billing', true)
ON CONFLICT DO NOTHING;

-- 5. 驗證修正結果
SELECT COUNT(*) as total_1296_forms,
       STRING_AGG(question_summary, ', ') as questions
FROM knowledge_base
WHERE form_id = 1296;

-- 6. 確認電費相關知識點都有正確設定
SELECT id, question_summary, form_id, action_type, priority
FROM knowledge_base
WHERE question_summary LIKE '%電費%'
   OR keywords @> ARRAY['電費']
ORDER BY
    CASE WHEN form_id = 1296 THEN 0 ELSE 1 END,
    priority DESC
LIMIT 20;