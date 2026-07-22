-- =====================================================
-- 電費寄送區間查詢知識項目
-- =====================================================
-- 創建日期: 2026-02-04
-- 用途: 創建知識庫條目，觸發電費寄送區間查詢表單
-- 流程: 用戶詢問電費寄送區間 → 觸發表單 → 收集地址 → 調用 Lookup API → 返回結果
-- =====================================================

-- 插入知識庫條目
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    trigger_mode,
    trigger_keywords,
    vendor_id,
    business_types,
    target_user,
    keywords,
    scope,
    priority,
    is_active,
    source_type,
    created_by,
    updated_by,
    created_at,
    updated_at
) VALUES (
    '電費寄送區間查詢',
    '📬 **電費寄送區間查詢服務**

我可以協助您查詢物件的電費寄送區間（單月或雙月）。

查詢方式：
1. 提供完整的物件地址
2. 系統會自動查詢該地址的電費寄送區間
3. 立即告知您帳單寄送時間

支援模糊匹配，即使地址不完全相同也能找到相近結果。',
    'form_fill',
    'billing_address_form',
    'immediate',
    ARRAY['電費', '寄送', '區間', '單月', '雙月', '帳單'],
    1,
    ARRAY['物業管理'],
    ARRAY['customer', 'manager'],
    ARRAY['電費', '寄送區間', '單月', '雙月', '繳費時間', '帳單'],
    'global',
    5,
    true,
    'manual',
    'system',
    'system',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT DO NOTHING;

-- 獲取插入的 ID 並生成 embedding（需要調用 API）
DO $$
DECLARE
    kb_id INTEGER;
BEGIN
    -- 獲取剛插入的知識項目 ID
    SELECT id INTO kb_id
    FROM knowledge_base
    WHERE question_summary = '電費寄送區間查詢'
      AND vendor_id = 1
    ORDER BY id DESC
    LIMIT 1;

    RAISE NOTICE '=================================================';
    RAISE NOTICE '✅ 電費寄送區間查詢知識項目創建完成';
    RAISE NOTICE '=================================================';

    IF kb_id IS NOT NULL THEN
        RAISE NOTICE '📚 知識 ID: %', kb_id;
        RAISE NOTICE '📚 問題摘要: 電費寄送區間查詢';
        RAISE NOTICE '📚 動作類型: form_fill';
        RAISE NOTICE '📚 表單 ID: billing_address_form';
        RAISE NOTICE '📚 觸發模式: immediate';
        RAISE NOTICE '📚 業者 ID: 1';
        RAISE NOTICE '📚 狀態: ✅ 啟用';
        RAISE NOTICE '';
        RAISE NOTICE '⚠️  注意: 需要手動生成 embedding 向量';
        RAISE NOTICE '   可通過知識管理後台或 API 觸發';
    ELSE
        RAISE WARNING '❌ 知識項目創建失敗或已存在';
    END IF;

    RAISE NOTICE '=================================================';
END $$;
