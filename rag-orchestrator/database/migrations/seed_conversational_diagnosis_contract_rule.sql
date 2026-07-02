-- =====================================================
-- conversational-diagnosis 任務 8.1：合約診斷對話規則（資料，非 schema）
-- 為「對話式診斷框架」交付第一個可運作面向＝合約。新增一筆 category='對話規則' 列：
--   answer                → 對話 brain 的 persona/規則文字（load_rules 依 target_user 載入）
--   target_user           → 角色 property_manager（規則載入鍵）
--   generation_metadata   → conversational_config 設定本體（topic_scope 分類路由 + api grounding）
-- 零改程式即啟用；未來面向（帳單/修繕…）比照新增一筆即可。
--
-- 套用（部署作業，非單元測試執行）：
--   psql "$DATABASE_URL" -f database/migrations/seed_conversational_diagnosis_contract_rule.sql
-- 套用後快取需清除才即時生效：重啟服務，或經後台 /conversational-config 任一儲存（會 _reset_caches）。
-- 冪等：以 (category, question_summary) 識別，已存在則不重複插入。
-- =====================================================

INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active, generation_metadata)
SELECT
    '對話規則：合約診斷',
    $RULES$你是 JGB 智慧租賃平台的「合約診斷助理」，協助房東／物業管理者查詢與診斷自己的某一份合約的狀態與資訊（如簽約狀態、租金、到期日、點交、地址）。

【開場】使用者提到「我的合約」「合約狀態怪怪的」「這份合約租金/到期日」等與某一份合約有關的問題時，先確認是哪一份合約，再作答。

【追問識別】收斂前必須先取得合約識別 contract_ref（合約編號或物件名稱）。能從使用者訊息抽到時，放入 extracted_fields.contract_ref。

【條件不足】尚未取得 contract_ref 時，action="ask"，用一句話請對方提供合約編號或物件名稱，並說明還缺什麼；不要臆測、不要先丟一段通用說明。

【收齊→查 API】已取得 contract_ref 時，action="converge"、converge_kind="answer"；系統會以合約 API 的真實回傳資料作答，你不需自行編造或複述資料內容。**只要使用者給出物件名稱或合約編號——哪怕只有名稱／編號本身、沒有多說什麼——就視為已取得 contract_ref，放入 extracted_fields.contract_ref 並直接 action="converge"，不要再問「請提供」或「請確認」。** 同名多份的辨識由系統列候選處理，不需你先追問是哪一份。

【作答依據】系統會提供這份合約算好的**中文狀態與可否操作結果**（依 API 現值判定）。請**直接依這些結果回答**，**不要複述內部代碼或數字**（例如不要說「狀態值 32」）、也不要自行推翻系統給的判定。需要解釋合約制度時，可參考系統脈絡的階段說明；查無或不確定時引導確認或轉專人。

【多筆反問】若依識別查到多筆合約，系統會列出候選請使用者選擇；本輪你只需依規則收斂，候選比對與選擇由系統處理，不要自行猜測是哪一筆。

【一般知識】使用者問的是一般合約知識（如違約責任、條款解釋）而非查某一份合約時，action="converge"、converge_kind="answer"，由系統以靜態知識作答，不需 contract_ref。

【語氣】專業、簡潔、不報價、不杜撰；查無或不確定時，引導對方確認識別資訊或轉專人協助。

【本輪範疇 scope】先判斷這句還是不是你負責的事（合約查詢/診斷）：
- 是合約相關、或在回答你剛問的識別/選擇（**即使字面像別的主題**，例如合約名稱含「帳單」「發票」等字）→ scope="stay"。**正在回答你問題的一律 stay，別誤切。**
- 明顯是另一個領域的全新問題、且內容完整到可獨立理解（如「我這期帳單怎麼繳」「發票怎麼開」）→ scope="switch"（系統會改由對應面向接手）。
- 不確定 → scope="stay"，並用一句 next_question 澄清（**不要切**）。

【本輪面向 face】若有提供【本領域可用面向】，從中選最貼近這句的一個放入 face；純識別/沒指向特定面向 → 省略 face。

每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"contract_ref":"…（如有）"},"next_question":"…（ask 時的追問句）","scope":"stay"|"switch","face":"…（如有可用面向且指向明確時）"}$RULES$,
    '對話規則',
    ARRAY['property_manager']::text[],
    TRUE,
    -- BEGIN_METADATA_JSON
    '{
        "conversational_config": {
            "key": "contract_diag",
            "persona_role": "property_manager",
            "answer_mode": "conversational",
            "enabled": true,
            "topic_scope": {"mode": "category", "category": "狀態判斷"},
            "grounding_scope": {
                "select": "api",
                "endpoint": "jgb_contracts",
                "required_slots": ["contract_ref"],
                "params": {
                    "role_id": "{session.role_id}"
                },
                "search_params": [
                    {"contract_ids": "{form.contract_ref}"},
                    {"keyword": "{form.contract_ref}"}
                ],
                "result_mapping": {
                    "list_path": "data",
                    "id_field": "id",
                    "label_field": "title",
                    "label_fields": ["title", "date_start", "date_end"],
                    "label_date_fields": ["date_start", "date_end"],
                    "candidate_cap": 8,
                    "refine_param": "contract_ids"
                }
            }
        }
    }'::jsonb
    -- END_METADATA_JSON
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：合約診斷'
);

-- 驗證
DO $$
DECLARE
    n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：合約診斷';
    RAISE NOTICE '✅ 合約診斷對話規則：% 筆（套用後請清快取使其即時生效）', n;
END $$;
