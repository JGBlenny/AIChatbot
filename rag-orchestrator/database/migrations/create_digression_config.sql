-- =====================================================
-- 離題偵測配置表（方案 B：資料庫配置）
-- 支援多業者、多語言、動態調整
-- =====================================================

-- 1. 建立配置表
CREATE TABLE IF NOT EXISTS digression_config (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER,                      -- 業者 ID（NULL = 全局默認配置）
    language VARCHAR(10) DEFAULT 'zh-TW',   -- 語言代碼（zh-TW, en, ja 等）
    keyword_type VARCHAR(50) NOT NULL,      -- 類型：exit, question, thresholds
    keywords JSONB,                         -- 關鍵字列表（JSON 陣列）
    thresholds JSONB,                       -- 閾值配置（JSON 物件）
    is_active BOOLEAN DEFAULT true,         -- 是否啟用
    priority INTEGER DEFAULT 0,             -- 優先級（數字越大優先級越高）
    description TEXT,                       -- 配置說明
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. 建立索引
CREATE INDEX IF NOT EXISTS idx_digression_config_vendor ON digression_config(vendor_id);
CREATE INDEX IF NOT EXISTS idx_digression_config_language ON digression_config(language);
CREATE INDEX IF NOT EXISTS idx_digression_config_type ON digression_config(keyword_type);
CREATE INDEX IF NOT EXISTS idx_digression_config_active ON digression_config(is_active);
CREATE INDEX IF NOT EXISTS idx_digression_config_lookup ON digression_config(vendor_id, language, keyword_type, is_active);

-- 3. 建立更新時間觸發器
CREATE OR REPLACE FUNCTION update_digression_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_digression_config_updated_at
    BEFORE UPDATE ON digression_config
    FOR EACH ROW
    EXECUTE FUNCTION update_digression_config_updated_at();

-- 4. 插入全局默認配置（繁體中文）

-- 4.1 退出關鍵字（繁體中文）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    NULL,
    'zh-TW',
    'exit',
    '["取消", "不填了", "算了", "不想填", "停止", "退出", "離開", "結束"]'::jsonb,
    0,
    '全局默認 - 繁體中文退出關鍵字'
);

-- 4.2 問題關鍵字（繁體中文）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    NULL,
    'zh-TW',
    'question',
    '["為什麼", "如何", "怎麼", "什麼", "哪裡", "多少", "幾", "嗎", "?", "？"]'::jsonb,
    0,
    '全局默認 - 繁體中文問題關鍵字'
);

-- 4.3 全局默認閾值
INSERT INTO digression_config (vendor_id, language, keyword_type, thresholds, priority, description)
VALUES (
    NULL,
    NULL,
    'thresholds',
    '{
        "intent_shift_threshold": 0.7,
        "semantic_similarity_threshold": 0.25,
        "short_answer_length_intent": 15,
        "short_answer_length_semantic": 10
    }'::jsonb,
    0,
    '全局默認閾值配置'
);

-- 5. 插入英文配置

-- 5.1 退出關鍵字（英文）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    NULL,
    'en',
    'exit',
    '["cancel", "stop", "quit", "exit", "no", "never mind", "forget it"]'::jsonb,
    0,
    '全局默認 - 英文退出關鍵字'
);

-- 5.2 問題關鍵字（英文）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    NULL,
    'en',
    'question',
    '["why", "how", "what", "where", "when", "who", "which", "?"]'::jsonb,
    0,
    '全局默認 - 英文問題關鍵字'
);

-- 6. 插入簡體中文配置

-- 6.1 退出關鍵字（簡體中文）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    NULL,
    'zh-CN',
    'exit',
    '["取消", "不填了", "算了", "不想填", "停止", "退出", "离开", "结束"]'::jsonb,
    0,
    '全局默認 - 簡體中文退出關鍵字'
);

-- 6.2 問題關鍵字（簡體中文）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    NULL,
    'zh-CN',
    'question',
    '["为什么", "如何", "怎么", "什么", "哪里", "多少", "几", "吗", "?", "？"]'::jsonb,
    0,
    '全局默認 - 簡體中文問題關鍵字'
);

-- 7. 範例：業者專屬配置（業者 1 - 較嚴格）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    1,
    'zh-TW',
    'exit',
    '["取消", "停止", "退出"]'::jsonb,
    10,
    '業者 1 專屬 - 僅接受正式退出關鍵字'
);

-- 8. 範例：業者 2 專屬配置（較寬鬆，支援口語）
INSERT INTO digression_config (vendor_id, language, keyword_type, keywords, priority, description)
VALUES (
    2,
    'zh-TW',
    'exit',
    '["取消", "不填了", "算了", "88", "bye", "掰掰", "不玩了"]'::jsonb,
    10,
    '業者 2 專屬 - 支援口語化退出'
);

-- 9. 範例：業者 2 調整閾值（更寬鬆）
INSERT INTO digression_config (vendor_id, language, keyword_type, thresholds, priority, description)
VALUES (
    2,
    NULL,
    'thresholds',
    '{
        "intent_shift_threshold": 0.85,
        "semantic_similarity_threshold": 0.2,
        "short_answer_length_intent": 20,
        "short_answer_length_semantic": 15
    }'::jsonb,
    10,
    '業者 2 專屬 - 更寬鬆的閾值（減少誤判）'
);

-- 10. 查詢配置的輔助函數
CREATE OR REPLACE FUNCTION get_digression_config(
    p_vendor_id INTEGER,
    p_language VARCHAR(10) DEFAULT 'zh-TW'
)
RETURNS TABLE (
    keyword_type VARCHAR(50),
    keywords JSONB,
    thresholds JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (dc.keyword_type)
        dc.keyword_type,
        dc.keywords,
        dc.thresholds
    FROM digression_config dc
    WHERE dc.is_active = true
      AND (dc.vendor_id = p_vendor_id OR dc.vendor_id IS NULL)
      AND (dc.language = p_language OR dc.language IS NULL)
    ORDER BY dc.keyword_type,
             dc.vendor_id NULLS LAST,      -- 業者配置優先於全局配置
             dc.priority DESC,              -- 高優先級優先
             dc.created_at DESC;            -- 最新配置優先
END;
$$ LANGUAGE plpgsql;

-- 11. 驗證安裝
DO $$
DECLARE
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO config_count FROM digression_config;
    RAISE NOTICE '✅ digression_config 表已建立';
    RAISE NOTICE '✅ 已插入 % 筆配置資料', config_count;

    -- 測試查詢函數
    RAISE NOTICE '測試查詢函數：get_digression_config(1, ''zh-TW'')';
    PERFORM * FROM get_digression_config(1, 'zh-TW');
    RAISE NOTICE '✅ 查詢函數運作正常';
END $$;

-- 12. 顯示當前配置
SELECT
    id,
    CASE
        WHEN vendor_id IS NULL THEN '全局默認'
        ELSE '業者 ' || vendor_id::TEXT
    END AS 配置範圍,
    COALESCE(language, '所有語言') AS 語言,
    keyword_type AS 類型,
    CASE
        WHEN keywords IS NOT NULL THEN jsonb_array_length(keywords) || ' 個關鍵字'
        WHEN thresholds IS NOT NULL THEN jsonb_object_keys(thresholds)::TEXT
        ELSE '-'
    END AS 內容,
    priority AS 優先級,
    is_active AS 啟用,
    description AS 說明
FROM digression_config
ORDER BY vendor_id NULLS FIRST, priority DESC, language, keyword_type;
