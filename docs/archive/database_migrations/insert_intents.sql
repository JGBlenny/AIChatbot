-- 插入 YAML 中的 10 個意圖到資料庫

-- 1. 退租流程 (knowledge)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, created_by) VALUES
('退租流程', 'knowledge', '詢問退租相關流程和規定',
 ARRAY['退租', '解約', '搬離', '終止合約', '提前退租'],
 0.80, false, 'yaml_migration');

-- 2. 合約規定 (knowledge)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, created_by) VALUES
('合約規定', 'knowledge', '詢問租約合約相關規定',
 ARRAY['合約', '規定', '條款', '權益', '義務'],
 0.80, false, 'yaml_migration');

-- 3. 設備使用 (knowledge)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, created_by) VALUES
('設備使用', 'knowledge', '詢問 IOT 設備或房屋設備使用方式',
 ARRAY['設備', 'IOT', '門鎖', '智能', '使用方法', '操作'],
 0.80, false, 'yaml_migration');

-- 4. 服務說明 (knowledge)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, created_by) VALUES
('服務說明', 'knowledge', '詢問 JGB 提供的服務內容',
 ARRAY['服務', '包租代管', '提供', '包含'],
 0.75, false, 'yaml_migration');

-- 5. 租約查詢 (data_query)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, api_endpoint, api_action, created_by) VALUES
('租約查詢', 'data_query', '查詢租約到期日、合約編號等資訊',
 ARRAY['租約', '到期', '期限', '何時到期', '合約編號'],
 0.75, true, 'lease_system', 'get_contract', 'yaml_migration');

-- 6. 帳務查詢 (data_query)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, api_endpoint, api_action, created_by) VALUES
('帳務查詢', 'data_query', '查詢帳單、費用、繳費記錄',
 ARRAY['帳單', '費用', '繳費', '金額', '收據', '應繳', '已繳'],
 0.75, true, 'billing_system', 'get_invoice', 'yaml_migration');

-- 7. 物件資訊 (data_query)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, api_endpoint, api_action, created_by) VALUES
('物件資訊', 'data_query', '查詢租賃物件地址、資訊',
 ARRAY['地址', '物件', '房子', '位置'],
 0.75, true, 'property_system', 'get_property', 'yaml_migration');

-- 8. 設備報修 (action)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, api_endpoint, api_action, created_by) VALUES
('設備報修', 'action', '報修設備故障',
 ARRAY['報修', '壞了', '故障', '維修', '不能用', '無法使用'],
 0.80, true, 'maintenance_system', 'create_ticket', 'yaml_migration');

-- 9. 預約看房 (action)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, api_endpoint, api_action, created_by) VALUES
('預約看房', 'action', '預約看房或驗屋',
 ARRAY['預約', '看房', '驗屋', '參觀'],
 0.80, true, 'appointment_system', 'create_appointment', 'yaml_migration');

-- 10. 退租查詢 (hybrid)
INSERT INTO intents (name, type, description, keywords, confidence_threshold, api_required, api_endpoint, api_action, created_by) VALUES
('退租查詢', 'hybrid', '詢問退租流程並查詢租約狀態',
 ARRAY['退租', '租約', '到期'],
 0.75, true, 'lease_system', 'get_contract', 'yaml_migration');

-- 顯示結果
SELECT
    type,
    COUNT(*) as count,
    array_agg(name ORDER BY name) as intents
FROM intents
GROUP BY type
ORDER BY type;
