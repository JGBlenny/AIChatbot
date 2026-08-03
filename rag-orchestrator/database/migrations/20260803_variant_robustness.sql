-- =====================================================
-- 20260803 變形題韌性補強（口語同義詞入摘要）
-- 依據：docs/backtest/assistant-report-regression.md「變形題掃描」節——
--   30 題口語變形 HIT 43%，MISS 主因＝口語同義詞不在 question_summary 詞面
--   （繳費證明/收回來/漏簽提醒/百分比怎麼算/變英文/快到期空房…），embedding 撐不住。
-- 修法：對明確同義詞做摘要補詞（改名→清嵌→重算）；無法窮舉的長尾歸 E-4
--   （查詢改寫器的口語正規化，引擎級立案）。
-- 冪等：UPDATE 以舊名定位（改名後不再命中）。本檔會把多列 embedding 設 NULL，
--   套用後需在 orchestrator 容器內跑 embed_missing.py 補嵌。
-- 執行順序：需在 20260731/20260803_batch24 兩支之後（runner 依檔名排序天然成立）。
-- =====================================================

-- #1/#3 手動開帳單（被 3401 概論搶答，補「手動」拉開操作入口語義）
UPDATE knowledge_base SET question_summary='新增帳單 手動開帳單給租客 操作入口', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='新增帳單 開帳單給租客 操作入口';

-- #13 繳費證明＝收據同義詞
UPDATE knowledge_base SET question_summary='帳單收據 繳費證明 PDF 下載', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='帳單收據 PDF 下載';

-- #12 「發出去想收回來」被封存知識搶答，收回知識補口語
UPDATE knowledge_base SET question_summary='帳單收回重發 發出去想收回 影響與時機', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='帳單收回重發 影響與時機';

-- B3 「漏簽名不會提醒嗎」被通知知識搶答
UPDATE knowledge_base SET question_summary='租客簽名檢查 漏簽提醒 少簽防呆', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='租客簽名檢查 少簽防呆';

-- B6 「百分比怎麼算」被計費知識搶答
UPDATE knowledge_base SET question_summary='即時物件出租率 百分比怎麼算 已出租數字來源', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='即時物件出租率 已出租數字來源';

-- B11 具體品項詞（馬桶跟水龍頭都壞了）零命中
UPDATE knowledge_base SET question_summary='報修多個品項 都壞了分開報嗎 一張報修單', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='報修多個品項 一張報修單';

-- B7 「快到期又空著的房子」零命中
UPDATE knowledge_base SET question_summary='物件總表篩選 快到期空房 本月到期 無合約', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='物件總表篩選 本月到期 無合約';

-- B8 「畫面變英文」零命中
UPDATE knowledge_base SET question_summary='頁面文字不正常 變英文亂碼 自動翻譯', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='頁面文字不正常 亂碼 自動翻譯';

-- B12 「銀行來函查入帳」零命中
UPDATE knowledge_base SET question_summary='帳單總表 虛擬帳號查交易 銀行抽查入帳', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='帳單總表 虛擬帳號查交易';

-- B9 「幫我找某某的租約」零命中（保持姓名反查聚焦，勿吸編號句）
UPDATE knowledge_base SET question_summary='用租客姓名找合約 找某租客的租約 姓名反查合約編號', embedding=NULL, updated_at=CURRENT_TIMESTAMP
WHERE question_summary='用租客姓名找合約 姓名反查合約編號';

-- B13 「還有沒有下一份約」續約口語錨點（一種講法一筆、空答案、掛面向）
INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '合約有沒有續約 下一份約', '', ARRAY['續約']::text[],
       ARRAY['property_manager']::text[], ARRAY['system_provider']::text[],
       ARRAY['合約','續約']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '合約有沒有續約 下一份約');
