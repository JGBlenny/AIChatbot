-- =====================================================
-- 回測金標斷言欄（2026-07-05）：表單/API/路徑/關鍵值的決定性驗證
-- 語義（皆選填，NULL=不檢查）：
--   expected_action_type：首輪回應的 action_type 必須相符
--     （conversational=面向對話/form_fill=表單/direct_answer=單發/api_call）
--   expected_form_id    ：首輪觸發的表單必須是這個（觸發正確性）
--   expected_path       ：首輪 debug_info.processing_path 需含此子串（選配，部分路徑無值）
--   expected_facts_tokens：最終對話全文必含全部 token（金標關鍵值，如金額/機制詞）
-- 任一金標不符 → 決定性判 GOLD_FAIL（優先於 LLM 評級；LLM 評級保留於 llm_grade）。
-- =====================================================
ALTER TABLE test_scenarios ADD COLUMN IF NOT EXISTS expected_action_type varchar(30);
ALTER TABLE test_scenarios ADD COLUMN IF NOT EXISTS expected_form_id varchar(100);
ALTER TABLE test_scenarios ADD COLUMN IF NOT EXISTS expected_path varchar(50);
ALTER TABLE test_scenarios ADD COLUMN IF NOT EXISTS expected_facts_tokens text[];
