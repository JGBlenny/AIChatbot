-- ============================================
-- Phase 1 擴展：移除模板變數，改用通用數值
-- LLM 將根據業者參數動態調整這些數值
-- ============================================

-- 更新帳務查詢相關知識（使用通用值）
UPDATE knowledge_base
SET
    answer = '您的租金繳費日為每月 5 號，請務必在期限前完成繳費。如果超過繳費日 3 天仍未繳納，將加收 300 元的逾期手續費。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '每月繳費日期' AND scope = 'global';

UPDATE knowledge_base
SET
    answer = '我們提供以下繳費方式：ATM 轉帳、信用卡自動扣款、超商繳費。如有任何繳費問題，請撥打客服專線 02-1234-5678。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '繳費方式有哪些' AND scope = 'global';

UPDATE knowledge_base
SET
    answer = '如果您未在繳費日 5 號前完成繳費，我們會提供 3 天的寬限期。超過寬限期後，將加收逾期手續費 300 元。為避免額外費用，請盡早繳納。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '逾期繳費會怎樣' AND scope = 'global';

-- 更新合約相關知識
UPDATE knowledge_base
SET
    answer = '我們的最短租期為 12 個月。如果您需要提前解約，請於 30 天前提出申請。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '最短租期是多久' AND scope = 'global';

UPDATE knowledge_base
SET
    answer = '押金為月租金的 2 倍。退租時，如無損壞及欠費，押金將全額退還。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '押金是多少' AND scope = 'global';

UPDATE knowledge_base
SET
    answer = '如需提前解約，請於 30 天前通知我們。提前解約可能需要支付違約金，詳細規定請參考您的租賃合約或聯絡客服 02-1234-5678。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '提前解約怎麼辦' AND scope = 'global';

-- 更新服務相關知識
UPDATE knowledge_base
SET
    answer = '我們的客服專線是 02-1234-5678，服務時間為週一至週五 9:00-18:00。如有緊急維修需求，我們承諾 24 小時內回應。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '客服專線是多少' AND scope = 'global';

UPDATE knowledge_base
SET
    answer = E'您可以透過以下方式報修：\n1. 撥打客服專線：02-1234-5678\n2. LINE 官方帳號：@example\n3. 前往公司辦公室：台北市信義區範例路 123 號\n\n緊急報修我們會在 24 小時內處理。',
    is_template = false,
    template_vars = '[]'
WHERE question_summary = '如何報修' AND scope = 'global';

-- 更新業者 A 專屬知識
UPDATE knowledge_base
SET
    answer = '甲山林包租代管提供 24 小時專業客服！請撥打 02-2345-6789，我們隨時為您服務。LINE 官方帳號：@jsL_property。',
    is_template = false,
    template_vars = '[]'
WHERE vendor_id = 1 AND question_summary = '客服專線是多少' AND scope = 'customized';

-- 更新業者 B 專屬知識
UPDATE knowledge_base
SET
    answer = '信義包租代管提供便利的信用卡繳費服務！您可以使用 VISA、MasterCard、JCB 等主要信用卡繳納租金。繳費日為每月 5 號，系統會自動扣款。',
    is_template = false,
    template_vars = '[]'
WHERE vendor_id = 2 AND question_summary = '信用卡繳費說明' AND scope = 'vendor';

-- ============================================
-- 說明
-- ============================================
-- 這些知識現在使用通用的參考值（如：5 號、300 元、3 天）
-- LLM 會根據業者的實際參數（vendor_configs）動態調整這些數值
-- 例如：業者 A（payment_day=1）→ "5 號" 會被調整為 "1 號"
--       業者 B（payment_day=5）→ 保持 "5 號"
