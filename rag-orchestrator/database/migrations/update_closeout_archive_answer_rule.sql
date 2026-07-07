-- =====================================================
-- contract-conversational-facets 收尾修正：退租收尾 answer_rules 釘死封存主詞
--
-- 背景：驗收實測（多輪示範第 4 輪）LLM 把「管理者手動封存」轉述成「系統會自動封存」，
-- 與 jgb2 事實相反（系統自動的只有過期轉歷史），會誤導管理者不動手、帳單持續掛帳。
-- 修法：answer_rules 加一行轉述約束（先例：狀態判斷的操作清單答句協定）。
--
-- 新裝環境由 seed_contract_facet_configs.sql（已含此行）建立；本檔僅更新既有列。
-- 套用：psql "$DATABASE_URL" -f database/migrations/update_closeout_archive_answer_rule.sql
-- 套用後清快取（重啟或後台 /conversational-config 任一儲存）。冪等：已含該句則不重複。
-- =====================================================

UPDATE knowledge_base
SET generation_metadata = jsonb_set(
        generation_metadata,
        '{conversational_config,answer_rules}',
        to_jsonb(replace(
            generation_metadata #>> '{conversational_config,answer_rules}',
            '封存步驟照底稿指引講（帳單總表搜合約編號批次封存）；',
            '封存步驟照底稿指引講（帳單總表搜合約編號批次封存）；封存是**管理者手動操作**，不得說成「系統會自動封存」——系統自動的只有過期後轉歷史；'))),
    updated_at = now()
WHERE category = '對話規則'
  AND question_summary = '對話規則：退租收尾'
  AND is_active
  AND (generation_metadata #>> '{conversational_config,answer_rules}') NOT LIKE '%不得說成「系統會自動封存」%';

-- 同步釘死系統脈絡的封存主詞（LLM 組話來源之一，雙保險）
UPDATE knowledge_base
SET answer = replace(answer, '- 帳單封存：至帳單總表以合約編號搜尋，把剩餘未結帳單批次封存；提前解約多產出的帳單也要封存，否則會持續掛帳。', '- 帳單封存（管理者手動操作，系統不會自動封存）：請自行至帳單總表以合約編號搜尋，把剩餘未結帳單批次封存；提前解約多產出的帳單也要封存，否則會持續掛帳。'), updated_at = now()
WHERE category = '系統脈絡' AND '退租收尾' = ANY(categories) AND is_active
  AND answer LIKE '%- 帳單封存：至帳單總表以合約編號搜尋，%';

DO $$
DECLARE ok BOOLEAN;
BEGIN
    SELECT (generation_metadata #>> '{conversational_config,answer_rules}') LIKE '%不得說成「系統會自動封存」%' INTO ok
    FROM knowledge_base WHERE category='對話規則' AND question_summary='對話規則：退租收尾' AND is_active
    ORDER BY id DESC LIMIT 1;
    RAISE NOTICE '✅ 退租收尾封存主詞轉述約束：%（套用後請清快取）', COALESCE(ok, FALSE);
END $$;
