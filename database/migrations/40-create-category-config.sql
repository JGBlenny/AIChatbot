-- Migration 40: 創建 Category 配置管理表
-- 目的：提供可配置的知識分類管理功能，取代硬編碼的分類選項
-- 日期：2025-10-25

-- ==================== Category 配置表 ====================

CREATE TABLE IF NOT EXISTS category_config (
    id SERIAL PRIMARY KEY,
    category_value VARCHAR(50) NOT NULL UNIQUE,  -- 實際儲存值（與 knowledge_base.category 對應）
    display_name VARCHAR(100) NOT NULL,          -- 顯示名稱
    description TEXT,                            -- 分類說明
    display_order INT DEFAULT 0,                 -- 顯示順序（越小越前）
    is_active BOOLEAN DEFAULT true,              -- 是否啟用
    usage_count INT DEFAULT 0,                   -- 使用次數（自動計算）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 索引 ====================

CREATE INDEX idx_category_config_active ON category_config(is_active);
CREATE INDEX idx_category_config_order ON category_config(display_order);
CREATE INDEX idx_category_config_value ON category_config(category_value);

-- ==================== 觸發器 ====================

-- 更新時間戳觸發器
CREATE TRIGGER update_category_config_updated_at
    BEFORE UPDATE ON category_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==================== 初始化資料 ====================

-- 從現有 knowledge_base 遷移資料
INSERT INTO category_config (category_value, display_name, usage_count, display_order, description)
SELECT
    category as category_value,
    category as display_name,
    COUNT(*) as usage_count,
    CASE category
        WHEN '合約問題' THEN 1
        WHEN '帳務問題' THEN 2
        WHEN '服務問題' THEN 3
        WHEN '設備報修' THEN 4
        WHEN '設施使用' THEN 5
        WHEN '設施問題' THEN 6
        ELSE 999
    END as display_order,
    CASE category
        WHEN '合約問題' THEN '租約合約相關規定、簽約流程、合約內容等'
        WHEN '帳務問題' THEN '帳單、費用、繳費記錄等財務相關問題'
        WHEN '服務問題' THEN 'JGB 服務內容、申請流程、入住手續等'
        WHEN '設備報修' THEN '設備故障報修、維修進度查詢'
        WHEN '設施使用' THEN '社區公共設施使用相關問題'
        WHEN '設施問題' THEN '設施故障、問題回報'
        ELSE NULL
    END as description
FROM knowledge_base
WHERE category IS NOT NULL
GROUP BY category
ON CONFLICT (category_value) DO NOTHING;

-- 添加未使用但應該保留的標準分類
INSERT INTO category_config (category_value, display_name, display_order, description, usage_count)
VALUES
    ('物件問題', '物件問題', 7, '租賃物件地址、資訊相關問題', 0),
    ('帳號問題', '帳號問題', 8, '帳號註冊、登入、密碼重設等問題', 0),
    ('其他', '其他', 999, '其他未分類問題', 0)
ON CONFLICT (category_value) DO NOTHING;

-- ==================== 資料清理建議 ====================

-- 注意：以下 UPDATE 需要人工審核後執行

-- 建議合併的重複分類：
-- UPDATE knowledge_base SET category = '帳務問題' WHERE category IN ('帳務查詢', '繳費問題');
-- UPDATE knowledge_base SET category = '設備報修' WHERE category = '設施維修';

-- 需要重新分類的：
-- SELECT id, title, category FROM knowledge_base WHERE category = 'unclear';

-- ==================== 註釋 ====================

COMMENT ON TABLE category_config IS 'Category 配置表：管理知識庫分類選項';
COMMENT ON COLUMN category_config.category_value IS '實際儲存值，與 knowledge_base.category 對應';
COMMENT ON COLUMN category_config.display_name IS '前端顯示名稱';
COMMENT ON COLUMN category_config.display_order IS '顯示順序，數字越小越靠前';
COMMENT ON COLUMN category_config.is_active IS '是否啟用，停用後前端不顯示';
COMMENT ON COLUMN category_config.usage_count IS '使用次數，可通過 API 同步更新';

-- ==================== 驗證 ====================

-- 驗證資料遷移
SELECT
    cc.category_value,
    cc.display_name,
    cc.display_order,
    cc.usage_count,
    cc.is_active
FROM category_config cc
ORDER BY cc.display_order, cc.category_value;
