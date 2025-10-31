-- ============================================
-- Phase 1: 擴展知識庫以支援多業者
-- ============================================

-- 擴展 knowledge_base 表格
ALTER TABLE knowledge_base
    ADD COLUMN IF NOT EXISTS vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS template_vars JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS scope VARCHAR(20) DEFAULT 'global',
    ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_knowledge_vendor ON knowledge_base(vendor_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_scope ON knowledge_base(scope);
CREATE INDEX IF NOT EXISTS idx_knowledge_template ON knowledge_base(is_template);

-- ============================================
-- 插入範例知識（包含模板變數）
-- ============================================

-- 全域知識（適用所有業者，使用模板變數）
INSERT INTO knowledge_base (question_summary, answer, intent_id, is_template, template_vars, scope, priority, title)
VALUES
    (
        '每月繳費日期',
        '您的租金繳費日為每月 {{payment_day}} 日，請務必在期限前完成繳費。如果超過繳費日 {{grace_period}} 天仍未繳納，將加收 {{late_fee}} 元的逾期手續費。',
        (SELECT id FROM intents WHERE name = '帳務查詢' LIMIT 1),
        true,
        '["payment_day", "grace_period", "late_fee"]',
        'global',
        1,
        'system'
    ),
    (
        '繳費方式有哪些',
        '我們提供以下繳費方式：{{payment_method}}。如有任何繳費問題，請撥打客服專線 {{service_hotline}}。',
        (SELECT id FROM intents WHERE name = '帳務查詢' LIMIT 1),
        true,
        '["payment_method", "service_hotline"]',
        'global',
        1,
        'system'
    ),
    (
        '逾期繳費會怎樣',
        '如果您未在繳費日 {{payment_day}} 號前完成繳費，我們會提供 {{grace_period}} 天的寬限期。超過寬限期後，將加收逾期手續費 {{late_fee}} 元。為避免額外費用，請盡早繳納。',
        (SELECT id FROM intents WHERE name = '帳務查詢' LIMIT 1),
        true,
        '["payment_day", "grace_period", "late_fee"]',
        'global',
        1,
        'system'
    );

-- 合約相關全域知識
INSERT INTO knowledge_base (question_summary, answer, intent_id, is_template, template_vars, scope, priority, title)
VALUES
    (
        '最短租期是多久',
        '我們的最短租期為 {{min_lease_period}} 個月。如果您需要提前解約，請於 {{termination_notice_days}} 天前提出申請。',
        (SELECT id FROM intents WHERE name = '退租流程' LIMIT 1),
        true,
        '["min_lease_period", "termination_notice_days"]',
        'global',
        1,
        'system'
    ),
    (
        '押金是多少',
        '押金為月租金的 {{deposit_months}} 倍。退租時，如無損壞及欠費，押金將全額退還。',
        (SELECT id FROM intents WHERE name = '退租流程' LIMIT 1),
        true,
        '["deposit_months"]',
        'global',
        1,
        'system'
    ),
    (
        '提前解約怎麼辦',
        '如需提前解約，請於 {{termination_notice_days}} 天前通知我們。提前解約可能需要支付違約金，詳細規定請參考您的租賃合約或聯絡客服 {{service_hotline}}。',
        (SELECT id FROM intents WHERE name = '退租流程' LIMIT 1),
        true,
        '["termination_notice_days", "service_hotline"]',
        'global',
        1,
        'system'
    );

-- 服務相關全域知識
INSERT INTO knowledge_base (question_summary, answer, intent_id, is_template, template_vars, scope, priority, title)
VALUES
    (
        '客服專線是多少',
        '我們的客服專線是 {{service_hotline}}，服務時間為 {{service_hours}}。如有緊急維修需求，我們承諾 {{repair_response_time}} 小時內回應。',
        (SELECT id FROM intents WHERE name = '報修問題' LIMIT 1),
        true,
        '["service_hotline", "service_hours", "repair_response_time"]',
        'global',
        1,
        'system'
    ),
    (
        '如何報修',
        '您可以透過以下方式報修：\n1. 撥打客服專線：{{service_hotline}}\n2. LINE 官方帳號：{{line_id}}\n3. 前往公司辦公室：{{office_address}}\n\n緊急報修我們會在 {{repair_response_time}} 小時內處理。',
        (SELECT id FROM intents WHERE name = '報修問題' LIMIT 1),
        true,
        '["service_hotline", "line_id", "office_address", "repair_response_time"]',
        'global',
        1,
        'system'
    );

-- 業者 A 專屬知識（覆蓋全域知識）
INSERT INTO knowledge_base (vendor_id, question_summary, answer, intent_id, is_template, template_vars, scope, priority, title)
VALUES
    (
        1,
        '客服專線是多少',
        '甲山林包租代管提供 24 小時專業客服！請撥打 {{service_hotline}}，我們隨時為您服務。LINE 官方帳號：{{line_id}}。',
        (SELECT id FROM intents WHERE name = '報修問題' LIMIT 1),
        true,
        '["service_hotline", "line_id"]',
        'customized',
        10,
        'system'
    );

-- 業者 B 專屬知識
INSERT INTO knowledge_base (vendor_id, question_summary, answer, intent_id, is_template, template_vars, scope, priority, title)
VALUES
    (
        2,
        '信用卡繳費說明',
        '信義包租代管提供便利的信用卡繳費服務！您可以使用 VISA、MasterCard、JCB 等主要信用卡繳納租金。繳費日為每月 {{payment_day}} 號，系統會自動扣款。',
        (SELECT id FROM intents WHERE name = '帳務查詢' LIMIT 1),
        true,
        '["payment_day"]',
        'vendor',
        5,
        'system'
    );

-- ============================================
-- 註解說明
-- ============================================

COMMENT ON COLUMN knowledge_base.vendor_id IS '業者 ID（NULL 表示全域知識）';
COMMENT ON COLUMN knowledge_base.is_template IS '是否為模板（包含變數）';
COMMENT ON COLUMN knowledge_base.template_vars IS '模板變數列表（JSON 陣列）';
COMMENT ON COLUMN knowledge_base.scope IS '知識範圍：global（全域）, vendor（業者專屬）, customized（覆蓋全域）';
COMMENT ON COLUMN knowledge_base.priority IS '優先級（數字越大優先級越高，用於排序）';

-- ============================================
-- 知識範圍說明
-- ============================================
-- scope 欄位用途：
-- - global: 全域知識，適用所有業者（如基本問答）
-- - vendor: 業者專屬知識，只有該業者會用到（如業者獨有服務）
-- - customized: 業者客製化知識，覆蓋全域知識（如同樣問題不同答案）
--
-- 查詢優先級：customized > vendor > global
-- priority 數字越大優先級越高
