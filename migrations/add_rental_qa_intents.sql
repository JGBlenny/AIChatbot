-- ========================================
-- 新增租管業 QA 意圖分類
-- ========================================
-- 目的：支援租管業客戶常見 QA 匯入功能
-- 日期：2025-11-28
-- 來源：20250305 租管業 SOP_1 客戶常見QA.xlsx
-- ========================================

-- 插入 32 個租管業意圖分類
INSERT INTO intents (name, type, description, created_at, updated_at) VALUES
-- 合約相關 (4 個)
('合約條款／內容', 'knowledge', '租約條款、合約內容相關問題', NOW(), NOW()),
('合約', 'knowledge', '一般合約問題', NOW(), NOW()),
('租約變更／轉租', 'knowledge', '租約變更、轉租、換約相關', NOW(), NOW()),
('租期／到期', 'knowledge', '租期長度、到期日、續約相關', NOW(), NOW()),

-- 退租相關 (2 個)
('退租／解約流程', 'knowledge', '退租流程、解約手續相關', NOW(), NOW()),
('退租', 'knowledge', '一般退租問題', NOW(), NOW()),

-- 租金相關 (4 個)
('租金繳納', 'knowledge', '租金繳納方式、期限、管道', NOW(), NOW()),
('租金金額調整', 'knowledge', '租金調整、漲價相關', NOW(), NOW()),
('押金/退款', 'knowledge', '押金金額、退還流程、扣款相關', NOW(), NOW()),
('其他租金相關', 'knowledge', '其他租金類問題', NOW(), NOW()),

-- 帳務相關 (3 個)
('帳務', 'knowledge', '帳務查詢、對帳相關', NOW(), NOW()),
('收據問題', 'knowledge', '收據申請、補發、格式相關', NOW(), NOW()),
('其他合約相關', 'knowledge', '其他合約類問題', NOW(), NOW()),

-- 水電相關 (6 個)
('水電', 'knowledge', '水電費用、繳納、查詢', NOW(), NOW()),
('電費查詢', 'knowledge', '電費帳單、費用查詢', NOW(), NOW()),
('電表度數/抄表', 'knowledge', '電表讀數、抄表相關', NOW(), NOW()),
('儲值電/預付電', 'knowledge', '預付電、儲值電表相關', NOW(), NOW()),
('其他電費問題', 'knowledge', '其他電費類問題', NOW(), NOW()),
('網路/第四台', 'knowledge', '網路、第四台服務相關', NOW(), NOW()),

-- 設備相關 (6 個)
('設備', 'knowledge', '一般設備問題', NOW(), NOW()),
('電器設備', 'knowledge', '電器設備使用、故障', NOW(), NOW()),
('冷氣', 'knowledge', '冷氣使用、維修、清潔', NOW(), NOW()),
('家具/裝潢', 'knowledge', '家具、裝潢問題', NOW(), NOW()),
('其他設備問題', 'knowledge', '其他設備類問題', NOW(), NOW()),
('鑰匙', 'knowledge', '鑰匙遺失、複製、門鎖相關', NOW(), NOW()),

-- 鄰居與環境 (4 個)
('噪音問題', 'knowledge', '噪音投訴、鄰居吵鬧', NOW(), NOW()),
('鄰居', 'knowledge', '鄰居關係、糾紛', NOW(), NOW()),
('室友', 'knowledge', '室友問題、室友關係', NOW(), NOW()),
('垃圾回收', 'knowledge', '垃圾分類、回收、清運', NOW(), NOW()),

-- 服務相關 (2 個)
('廢棄物代收', 'knowledge', '大型廢棄物、代收服務', NOW(), NOW()),
('激動客訴問題', 'knowledge', '客戶激動投訴、緊急處理', NOW(), NOW()),

-- 其他 (1 個)
('情緒', 'knowledge', '客戶情緒安撫相關', NOW(), NOW())

ON CONFLICT (name) DO NOTHING;

-- 驗證插入結果
SELECT COUNT(*) as total_intents FROM intents;
SELECT name, description FROM intents ORDER BY name;
