-- =====================================================
-- 20260731 客服回報修正批（assistant-reports R-31~R-37）
-- 依據：docs/backtest/assistant-report-regression.md（批次 20260731）
--   1) R-33 知識內容錯誤：已發送（應到帳）帳單其實可收回
--      （jgb2 Bill::canCancel 查證：BILL_READY／BILL_PREPARE_TO_READY 可取消）
--      → 修「帳單排定發送」知識與「帳單診斷」系統脈絡的同一錯誤
--   2) T-1 路由缺口：查資料型知識只掛後台分類，top-1 命中時不進面向
--      → 補掛面向診斷分類（點退/收據→條件診斷：帳單、續約歷史→續約）
--   3) R-32／R-34／R-36 知識缺漏：新增三筆（虛擬帳號查交易／批次匯入帳單／租客姓名查合約）
-- 冪等：UPDATE 以內容特徵定位（修正後不再命中）；INSERT 以 question_summary 判重。
-- 注意：新增列 embedding 為 NULL，套用後需在 orchestrator 容器內跑 embed_missing.py 補嵌。
-- =====================================================

-- ── 1. R-33：帳單排定發送知識——「已發送無法撤回」為誤，改為可收回（與 id3926 收回知識一致）──
UPDATE knowledge_base
SET answer = '帳單建立後可選擇立即發送或排定發送時間。排定發送的帳單狀態為「排定發送」，系統會在指定時間自動將帳單發送給租客，狀態變為「應到帳」。若帳單尚未發送且不再需要，可將其設為失效。已發送（應到帳）或排定發送的帳單仍可「收回（取消發送）」退回待發送，修改金額或明細後重新發送；收回會斷開原繳費資訊，重發時會產生新的虛擬帳號／繳費代碼。租客已付款（待對帳）或已到帳的帳單則不能收回。',
    updated_at = CURRENT_TIMESTAMP
WHERE question_summary = '帳單排定發送 預約機制'
  AND answer LIKE '%已發送的帳單無法撤回%';

-- ── 2. R-33：帳單診斷系統脈絡——「只有草稿可發送與取消」同一錯誤 ──
UPDATE knowledge_base
SET answer = replace(answer,
    '- 只有「草稿」狀態可以發送與取消；已發送的帳單不能重發送，要改內容須先取消（若狀態允許）再重建。',
    '- 發送僅限「草稿（待發送）」；取消（收回）適用「應到帳（待繳費）」與「排定發送」，收回後退回待發送、可修改再重新發送（重發會產生新的繳費資訊）；租客已付款（待對帳）或已到帳的帳單不能收回。'),
    updated_at = CURRENT_TIMESTAMP
WHERE question_summary = '系統脈絡：帳務領域-帳單診斷(子面向)'
  AND answer LIKE '%只有「草稿」狀態可以發送與取消%';

-- ── 3. T-1：查資料型知識補面向分類（top-1 命中也能進面向查實值）──
UPDATE knowledge_base
SET categories = array_append(categories, '條件診斷：帳單'), updated_at = CURRENT_TIMESTAMP
WHERE question_summary IN ('點退帳單金額計算 押金結算', '點退帳單 自動產生 費用結算', '帳單收據 PDF 下載')
  AND NOT ('條件診斷：帳單' = ANY(coalesce(categories, '{}')));

UPDATE knowledge_base
SET categories = array_append(categories, '續約'), updated_at = CURRENT_TIMESTAMP
WHERE question_summary = '續約歷史紀錄 原合約保留查詢'
  AND NOT ('續約' = ANY(coalesce(categories, '{}')));

-- ── 4. R-32：金流抽查——帳單總表以虛擬帳號查交易 ──
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '帳單總表 虛擬帳號查交易',
       '遇到金流商（如永豐）通知抽查特定交易、需要提供系統畫面存證時，可在後台「帳單總表」查詢：開啟帳單總表後，於下拉篩選選擇「虛擬帳號」，輸入該筆交易的虛擬帳號即可找到對應帳單，點開帳單明細畫面即可截圖提供。多筆交易請逐筆以虛擬帳號搜尋。',
       '{業者操作指引,帳單管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '帳單總表 虛擬帳號查交易');

-- ── 5. R-34：批次建立帳單（jgb2 bills.excel.batch.import 通用路由查證）──
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '帳單批次匯入 批次建立',
       '需要一次為多位租客建立帳單（例如整批電費帳單）時，可使用帳單的 Excel 批次匯入：先在帳單頁面下載系統提供的匯入範例檔，填妥各租客的費用資料後上傳，系統會依檔案內容批次建立帳單。匯入建立的帳單為待發送狀態，可逐筆檢查後再發送。已發送帳單如需批次調整，請聯繫客服協助。',
       '{業者操作指引,帳單管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '帳單批次匯入 批次建立');

-- ── 6a. R-31：帳單收據金額進場錨點（口語錨點範式：一種講法一筆、空答案、掛面向分類）──
--   「716317 帳單收據金額是多少」這類短句對一般知識相似度不足 0.55，需專屬錨點帶進帳單診斷。
INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '帳單收據金額 收據多少錢', '', ARRAY['條件診斷：帳單']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['帳單','收據','金額']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '帳單收據金額 收據多少錢');

-- ── 6b-0. 合約資訊查詢錨點（20260803 重跑 #5 逼出的回歸防護）：
--   「查詢合約資訊 <編號>」語義離 6b 姓名引導知識太近會被搶答，
--   需本錨點把編號句吸進合約診斷面向；姓名句仍落在 6b。──
INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '查詢合約資訊 合約編號查詢', '', ARRAY['狀態判斷']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['合約','查詢','資訊']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '查詢合約資訊 合約編號查詢');

-- ── 6b. R-36：租客姓名反查合約——外部 API 不支援，誠實引導後台搜尋 ──
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
--   summary 聚焦「姓名反查」語義：泛「查詢合約資訊 <編號>」句不可被本筆搶答（20260803 重跑 #5 逼出，
--   帶編號的合約查詢必須留給合約面向錨點）。
SELECT '用租客姓名找合約 姓名反查合約編號',
       '智能助手目前無法直接用租客姓名反查合約編號，查詢合約資訊時請提供合約編號或物件名稱。若手邊只有租客姓名，可先到後台合約列表以租客姓名搜尋，找到對應合約後，再以該合約編號向助手查詢狀態或細節。',
       '{合約管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '用租客姓名找合約 姓名反查合約編號');
