-- =====================================================
-- 20260803 客服回報 20260724 批標準答案補匯入（重跑稽核逼出）
-- 依據：docs/backtest/assistant-report-regression.md 批次 20260803（R-38 起）
-- 背景：7/24 批 30 筆回報中，客服已在問題描述寫好標準答案的 14 案，
--   當時的知識匯入未落地（loop 187 待審核／loop 190 失敗），2026-08-03
--   以現行系統重跑仍 fallback 或答非所問。本檔將客服標準答案轉為 KB 條目。
-- 內容為客服團隊提供之 ground truth，僅轉寫為知識風格（先述情境再帶條件）。
-- 冪等：以 question_summary 判重。新列 embedding 留 NULL，套用後需補嵌。
-- =====================================================

-- R-38a（#13）帳單品名
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '帳單品名修改 租金改停車位費',
       '帳單的「品名」是依合約的租金項目命名的，所以會固定顯示為「租金」，現有合約無法直接改品名。若希望品名顯示為停車位費等其他名稱，需在建立合約時把租金金額設為 0、再單獨設定該筆費用，品項名稱就會依設定的費用名稱顯示；已存在的合約要套用此做法需重新簽立。',
       '{業者操作指引,帳單管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '帳單品名修改 租金改停車位費');

-- R-38b（#15）帳單建立即寄送與聯絡方式未驗證
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '帳單無法寄送 租客聯絡方式未驗證',
       '系統在建立帳單時會同時寄送給租客；若該租客的聯絡方式尚未驗證，帳單會無法寄出。解法：將租客「轉為註冊」，或維持免註冊但補驗證聯絡方式（Email 或電話），驗證完成後帳單即可正常發送。之後遇到同樣情況都是相同處理方式。',
       '{業者操作指引,帳單管理,租客管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '帳單無法寄送 租客聯絡方式未驗證');

-- R-38c（#16）簽名防呆
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '租客簽名檢查 少簽防呆',
       '系統不會檢查租客簽名的內容——租客只要在簽名頁面有觸碰紀錄（即使只是難以辨識的一點）就會視為已簽、可進行下一步，因此可能發生少簽而系統未擋下的情況（例如送租補因缺簽名被退件）。把關時機在管理者「回簽」：回簽位置與租客簽名位置相同，回簽時逐頁確認租客都已確實簽立再完成當頁回簽，即可避免缺簽名。',
       '{業者操作指引,合約管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '租客簽名檢查 少簽防呆');

-- R-38d（#17/#18/#20）雙人簽約填寫
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '雙人簽約 兩位承租人填寫方式',
       '兩人共同簽約時：身分證欄位請把證件種類改選「其他身分證」（此選項不檢核格式），即可一次輸入兩位的證號；姓名欄建議填「姓：第一位全名、名：/第二位全名」（例如 姓：宋維光、名：/宋紹光），兩位簽約人就會完整顯示、不會跑版。',
       '{業者操作指引,合約管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '雙人簽約 兩位承租人填寫方式');

-- R-38e（#19）已議定修改的合約更新
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '合約修改後更新 改租金要重填嗎 複製合約',
       '已與房客議定修改內容、要更新現有合約時：可用「複製合約」功能，依需要的項目選擇複製再調整，不必整份重填；若合約還在待發送、內容已與房客確認，建議直接創建新合約（房客同意即可，不必再次線上簽名）。舊合約可提交異動單移至歷史合約、過去帳單手動封存，之後以新合約與新帳單為準。',
       '{業者操作指引,合約管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary IN ('合約修改後更新 改租金要重填嗎 複製合約','合約修改後更新 複製合約 不重填'));

-- R-38f（#21）未發送帳單批次編輯限制
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '未發送帳單一次編輯 批次調整範圍',
       '一次編輯未發送帳單的功能，目前僅支援批次調整水電費用。若要新增帳單品項（例如加收項目），請單獨為該項目「新增一筆週期帳單」，即可套用到後續未發送的帳單。',
       '{業者操作指引,帳單管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '未發送帳單一次編輯 批次調整範圍');

-- R-38g（#22）即時出租率計算
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '即時物件出租率 已出租數字來源',
       '首頁「即時物件出租率」的已出租數字，是以「合約中的物件總數量 ÷ 物件總數」計算出來的百分比，會隨合約綁定的物件數量即時變動。',
       '{業者操作指引,物件管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '即時物件出租率 已出租數字來源');

-- R-38h（#23）直接匯款補帳單紀錄
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '租客直接匯款 補建帳單紀錄',
       '租客直接匯款（例如儲值電費）而沒有走後台儲值時，系統不會有帳單紀錄。可到「待發送帳單」為他新增一筆帳單建立紀錄，並手動在電表加上對應度數，儲值與用電紀錄就完整了。',
       '{業者操作指引,帳單管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '租客直接匯款 補建帳單紀錄');

-- R-38i（#24）新增帳單入口
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '新增帳單 開帳單給租客 操作入口',
       '要在系統新增帳單，到「待發送帳單」頁面即可直接新增：選擇物件、設定繳費截止日與收費項目金額後建立，確認無誤再發送給租客。',
       '{業者操作指引,帳單管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary IN ('新增帳單 開帳單給租客 操作入口','新增帳單 操作入口'));

-- R-38j（#25）逾期虛擬帳號與年繳拆分
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '逾期帳單虛擬帳號 可否繳款 年繳拆分',
       '租客逾期未繳費時，原本帳單提供的虛擬帳號仍然可以繳款，通常可沿用很長一段時間，不需要重新發號。另外，年繳合約的帳單目前無法自動拆分為今年與跨年度兩部分，建議在帳單品項備註註明，或請客服人工另開一張帳單拆算。',
       '{業者操作指引,帳單管理,付款金流}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '逾期帳單虛擬帳號 可否繳款 年繳拆分');

-- R-38k（#26）頁面亂碼＝瀏覽器自動翻譯
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '頁面文字不正常 亂碼 自動翻譯',
       '頁面文字突然變得不正常（出現奇怪的英文或怪字）通常不是系統設定錯誤，而是瀏覽器開啟了 Google 自動翻譯造成的。請關閉自動翻譯，或點瀏覽器網址列的翻譯圖示選「繁體中文」，畫面就會恢復正常。',
       '{業者操作指引,綜合指引}', '{system_provider}', '{property_manager,tenant}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '頁面文字不正常 亂碼 自動翻譯');

-- R-38l（#27）帳單封存退回
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '帳單封存後退回 重開帳單',
       '帳單封存後若要退回，需透過異動單申請變更；若只是需要再開一張帳單，可直接在「待發送帳單」頁新增，重新選取物件、繳費截止日與金額等項目即可。',
       '{業者操作指引,帳單管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '帳單封存後退回 重開帳單');

-- R-38m（#28）修繕多品項一張單
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '報修多個品項 一張報修單',
       '同一次報修有多個品項（例如浴室三個設備）時，不必分開建立多張報修單：修繕品項選「其他」自行輸入，即可把多個品項整合寫在同一張報修單裡。',
       '{業者操作指引,修繕管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '報修多個品項 一張報修單');

-- R-38n（#30）物件總表到期＋無合約篩選
INSERT INTO knowledge_base (question_summary, answer, categories, business_types, target_user, action_type, source, is_active)
SELECT '物件總表篩選 本月到期 無合約',
       '要同時看到本月到期與目前沒有合約的物件，可在物件總表上方欄位篩選：選「本月到期」後，標籤顯示「無合約／洽談中」的就是目前沒有合約的物件，標籤「合約中」的則是本月即將到期的物件。',
       '{業者操作指引,物件管理}', '{system_provider}', '{property_manager}', 'direct_answer', 'manual', true
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '物件總表篩選 本月到期 無合約');

-- R-38o（#4）「查帳單ID<編號>」短句錨點（同 R-31 範式：短句相似度不足 0.55 需專屬錨點）
INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '查帳單 帳單編號查詢', '', ARRAY['條件診斷：帳單']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['帳單','查詢','編號']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '查帳單 帳單編號查詢');

-- ── 情境回測 F1（P1）：3863 與 4645 矛盾調和 ──
--   3863（建約引導面向用）缺「其他身分證放兩位證號」填法，多輪時把使用者導向「只填一位證號」；
--   4645（客服標準答案）缺「電子簽署由一位代表完成」限制。雙向補齊，兩筆一致。
UPDATE knowledge_base
SET answer = '遇到兩位承租人要共同承租時，資料填寫方式：身分證欄位把證件種類改選「其他身分證」（此選項不檢核格式），即可一次輸入兩位的證號；姓名欄填「姓：第一位全名、名：/第二位全名」（例如 姓：宋維光、名：/宋紹光），兩位簽約人會完整並列顯示。電子簽署部分，系統一份合約由一位承租人代表完成電子簽署即可。若希望兩位都親簽，可改用紙本：線下完成雙方簽立後以「上傳合約」存入系統，或用系統產生合約後列印給兩位簽名再上傳。',
    updated_at = CURRENT_TIMESTAMP
WHERE id = (SELECT id FROM knowledge_base WHERE question_summary = '共同承租 兩位承租人 做法' AND answer LIKE '%只支援一位簽署人%' LIMIT 1);

UPDATE knowledge_base
SET answer = '兩人共同簽約時：身分證欄位請把證件種類改選「其他身分證」（此選項不檢核格式），即可一次輸入兩位的證號；姓名欄建議填「姓：第一位全名、名：/第二位全名」（例如 姓：宋維光、名：/宋紹光），兩位簽約人就會完整顯示、不會跑版。電子簽署由其中一位承租人代表完成即可。',
    updated_at = CURRENT_TIMESTAMP
WHERE question_summary = '雙人簽約 兩位承租人填寫方式'
  AND answer NOT LIKE '%代表完成%';

-- ── 情境回測 D-3：「合約N的點退帳單金額」措辭變體錨點 ──
--   3519 已掛面向分類，但此句型相似度落在 0.55-0.75 區間→直答搶答（門檻脆弱性）。
INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '合約的點退帳單金額 查點退金額', '', ARRAY['條件診斷：帳單']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['合約','點退','金額']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '合約的點退帳單金額 查點退金額');


-- ── 情境回測第二輪：三筆摘要口語化（A-4/B-5/C-2 第一輪失守——口語句與摘要語義距離過遠，
--    被面向搶接或 IoT 知識蓋台）。已套環境改名＋清嵌重算；新環境 INSERT 已是最終版。──
UPDATE knowledge_base SET question_summary='新增帳單 開帳單給租客 操作入口', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='新增帳單 操作入口';
UPDATE knowledge_base SET question_summary='帳單批次匯入 整批電費帳單 批次建立', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='帳單批次匯入 批次建立';
UPDATE knowledge_base SET question_summary='合約修改後更新 改租金要重填嗎 複製合約', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='合約修改後更新 複製合約 不重填';
