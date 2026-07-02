-- =====================================================
-- domain-conversational-facets（面向模型）：合約領域系統脈絡——母共用 + 子面向（資料，非 schema）
--
-- 面向化疊加（get_system_context 沿 category_config 父鏈組出多層）：
--   通用 base（target_user IS NULL）
--     └ 母『系統合約』(categories=['系統合約'])：合約領域共用框架（狀態模型/12 階段/續約/欄位）
--         └ 子面向『狀態判斷』(categories=['狀態判斷'])：各階段下一步/可否操作（問狀態才載）
--   → 只載入命中的面向，避免整個領域知識每輪常駐（面向一多仍精簡）。
--
-- 前置：先套 add_contract_facet_categories.sql（建 category_config 的 系統合約/狀態判斷 父子）。
-- 套用：psql "$DATABASE_URL" -f database/migrations/seed_domain_contract_system_context.sql
-- 套用後清快取（重啟或後台 /conversational-config 任一儲存）。
-- 冪等：以 (category, question_summary) 識別，已存在不重插。
-- 一般合約知識維持 direct_answer（三出口不變），不受影響。
-- =====================================================

-- 母『系統合約』：合約領域共用框架（所有合約面向都需要）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：合約領域-系統合約(母共用)',
    $CTX$## 合約 12 里程碑（階段參考）
| 值 | 里程碑 | 階段 | 白話 |
|--|--|--|--|
| 1 | 合約建立 | 簽約前 | 剛建好，未送邀請 |
| 2 | 已送簽約邀請 | 簽約前 | 等租客簽回 |
| 4 | 租客已簽 | 簽約前 | 等房東簽名 |
| 8 | 雙方簽名完成 | 執行中 | 正式生效 |
| 16 | 點交送出 | 執行中 | 已發點交(交屋)清單，等租客同意 |
| 32 | 點交完成 | 執行中 | 租客已同意(已交屋) |
| 64 | 點退送出 | 執行中 | 已發點退(退租)清單，等租客同意 |
| 128 | 點退完成 | 執行中 | 租客已同意(已退租) |
| 256 | 提前解約中 | 執行中 | 申請進行中 |
| 512 | 提前解約已確認 | 執行中 | 已確認 |
| 1024 | 歷史合約 | 歷史 | 合約結束 |
| 2048 | 生命週期結束 | 歷史 | 完全結束 |
用詞：點交＝交屋、點退＝退租。

## 續約與同名多份
- 續約是父子鏈（father_id 指向父約）；同物件同租客會有多份合約、title 相同；查詢只回最新有效列。
- 使用者只講物件名稱常對應多份 → 帶期間與狀態列候選讓對方選。

## 關鍵欄位
title(名稱)、date_start~date_end(租期)、rent/deposit_amount(月租/押金)、allow_early_termination(是否允許提前解約)、法定用途(1一般住宅/2社會住宅)。$CTX$,
    '系統脈絡', ARRAY['系統合約']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：合約領域-系統合約(母共用)');

-- 子面向『狀態判斷』：各階段下一步/可否操作（問合約狀態時才載）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：合約領域-狀態判斷(子面向)',
    $CTX$## 回答合約狀態時
直接依系統提供的「目前狀態」與「可進行的操作／無法的原因」作答，用白話向房東說明現況、下一步與可做什麼。
**可否點交/點退/提前解約/續約，一律以系統的判定與原因為準——不要自行推斷操作條件、不要編造規則、不要複述內部代碼。** 系統沒給的細節（如確切金額）就引導確認或轉專人。$CTX$,
-- 註：收斂「作答行為」鐵則（底稿在手直接答/禁推託/比較請補識別）不放這裡——
--   那是對話層行為，住 conversational_config.answer_rules（seed_conversational_diagnosis_contract_rule.sql），
--   隨對話設定走：換面向不消失、新診斷領域不用抄面向脈絡。此列只放領域框架。
    '系統脈絡', ARRAY['狀態判斷']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：合約領域-狀態判斷(子面向)');

-- 驗證
DO $$
DECLARE p_len INT; c_len INT;
BEGIN
    SELECT length(answer) INTO p_len FROM knowledge_base WHERE category='系統脈絡' AND '系統合約'=ANY(categories) AND is_active ORDER BY id DESC LIMIT 1;
    SELECT length(answer) INTO c_len FROM knowledge_base WHERE category='系統脈絡' AND '狀態判斷'=ANY(categories) AND is_active ORDER BY id DESC LIMIT 1;
    RAISE NOTICE '✅ 合約系統脈絡：母共用系統合約=% 字、子面向狀態判斷=% 字（問狀態時 base+母+子 疊加）', COALESCE(p_len,0), COALESCE(c_len,0);
END $$;
