-- =====================================================
-- 不變量 9 逼出的能力回補（2026-08-29 業主裁定 YES/YES/YES）
--
-- 共同原則（業主定案）：**只恢復已存在、已被 KB／execution contract 證明的能力，
-- ⛔ 不趁機擴大 Face 的產品責任。**
--
-- 病灶：面向分支在表單分支之前且無條件 commit ⇒ 知識掛的 active 表單永不開啟。
-- 2026-07 面向化遷移逐 domain 開 spec，沒有做過「這筆知識原本由誰服務」的反向盤查。
--
-- ⚠️ 光加 endpoint **不等於**能力回補：診斷引擎是靠 **endpoint 分派**觸發的，
--    secondary_call 只把資料 attach 到主列。因此本次同時改了 consumer
--    （services/jgb/bills.py 以 attach 重用既有引擎，⛔ 不複製判斷邏輯），
--    並修掉 conversational_engine 把單物件 secondary 結果丟成 [] 的不一致。
--    ⇒ 驗收單位是「能力可以被使用」，不是「config 裡出現 endpoint 名稱」。
--
-- 冪等：三段皆以存在性守衛，可重複執行。套用後清面向設定快取（重啟服務）。
-- =====================================================

-- ─────────────────────────────────────────────────────
-- ① billing_invoice ＋ jgb_invoice_logs（證據最強）
--    knowledge 3503「發票為什麼沒有開出來」
--    ＝ services/jgb/invoices.py::_diagnose_issue_failure 的 docstring「I01：…」
--    觸發前提 = jgb_invoice_logs；而現行 grounding 只有 jgb_bills + jgb_invoices
--    ⇒ OWNER_EXISTS_PARTIAL → OWNER_EXISTS 的能力補全，非擴大 responsibility。
-- ─────────────────────────────────────────────────────
UPDATE knowledge_base
SET generation_metadata = jsonb_set(
        generation_metadata #- '{conversational_config,grounding_scope,secondary_call}',
        '{conversational_config,grounding_scope,secondary_calls}',
        jsonb_build_array(
            generation_metadata->'conversational_config'->'grounding_scope'->'secondary_call',
            jsonb_build_object(
                'endpoint',  'jgb_invoice_logs',
                'attach_as', 'invoice_logs',
                'list_path', 'data',
                'params',    jsonb_build_object('bill_id', '{row.id}',
                                                'role_id', '{session.role_id}'))),
        TRUE)
WHERE category = '對話規則' AND is_active
  AND generation_metadata->'conversational_config'->>'key' = 'billing_invoice'
  AND generation_metadata->'conversational_config'->'grounding_scope' ? 'secondary_call'
  AND NOT (generation_metadata->'conversational_config'->'grounding_scope' ? 'secondary_calls');

-- ─────────────────────────────────────────────────────
-- ② billing_flow ＋ jgb_bill_detail
--    knowledge 3502「虛擬帳號過期或轉帳失敗」原掛表單 jgb_bill_diagnosis
--    → endpoint jgb_bill_detail → _diagnose_atm_expired（docstring「P04：虛擬帳號過期」）
--    面向化後主查詢改成 jgb_bills ⇒ 該引擎不再被觸及。
-- ─────────────────────────────────────────────────────
UPDATE knowledge_base
SET generation_metadata = jsonb_set(
        generation_metadata #- '{conversational_config,grounding_scope,secondary_call}',
        '{conversational_config,grounding_scope,secondary_calls}',
        jsonb_build_array(
            generation_metadata->'conversational_config'->'grounding_scope'->'secondary_call',
            jsonb_build_object(
                'endpoint',  'jgb_bill_detail',
                'attach_as', 'bill_detail',
                'list_path', 'data',
                'params',    jsonb_build_object('bill_id', '{row.id}',
                                                'role_id', '{session.role_id}'))),
        TRUE)
WHERE category = '對話規則' AND is_active
  AND generation_metadata->'conversational_config'->>'key' = 'billing_flow'
  AND generation_metadata->'conversational_config'->'grounding_scope' ? 'secondary_call'
  AND NOT (generation_metadata->'conversational_config'->'grounding_scope' ? 'secondary_calls');

-- ─────────────────────────────────────────────────────
-- ③ 訂閱診斷面向（窄責任）
--    ⚠️ topic_scope 只掛 `條件診斷：訂閱`，**不掛** `訂閱方案`（5 筆制度說明）——
--    業主裁定：「不要開成『所有訂閱問題都進 Face』」，制度說明仍走 Knowledge 單發。
--    能力早已存在：jgb_subscription 端點 ＋ diagnose_subscription 引擎，
--    其三個分支與三筆知識一一對應：
--      _diagnose_cannot_add_estate    「E01：為什麼不能新增物件」   ＝ 3505
--      _diagnose_estates_delisted     （下架/全部下架/物件消失）    ＝ 3506
--      _diagnose_subscription_payment （扣款失敗/方案異常/功能異常）＝ 3509
--    ⇒ 2026-07 遷移時沒有 owner 承接，本段只是補上 owner。
-- ─────────────────────────────────────────────────────

-- 3-1 系統脈絡（不變量 4：每個面向 category 必有系統脈絡知識）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：訂閱領域-條件診斷：訂閱(子面向)',
       '【訂閱與物件額度】訂閱方案決定可用的物件額度；額度用滿即無法新增物件，可升級方案、加購額度，或刪除/下架不再使用的物件釋放額度。目前用量在「訂閱方案」頁查看。
【扣款失敗的連鎖效果】訂閱續約扣款失敗會使方案失效，方案失效時系統會**將物件全部自動下架**、多數功能暫時無法使用。處理路徑：到「訂閱方案」頁確認方案狀態與付款方式，完成續約後再將物件重新上架。
【與物件下架的區辨】方案正常但只有個別物件被下架，多半是修改資料後必填欄位驗證失敗導致的自動下架，補齊欄位重新刊登即可——這不是訂閱問題。
【與權限的區辨】無法新增物件也可能是帳號權限不足（需物件管理權限，由團隊管理者調整），與訂閱額度是兩件事，須依系統查得的額度現況判斷是哪一種。
【不代操作】升級方案、加購額度、變更付款方式一律只指路，不代執行、不承諾扣款結果。',
       '系統脈絡', ARRAY['條件診斷：訂閱']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
                  WHERE question_summary = '系統脈絡：訂閱領域-條件診斷：訂閱(子面向)');

-- 3-2 面向設定
INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active, generation_metadata)
SELECT '對話規則：訂閱診斷',
       $RULES$你是 JGB 智慧租賃平台的「訂閱診斷助理」，協助管理者處理「不能新增物件／物件突然全部下架／扣款失敗導致功能異常」這類**需要查該帳號實際訂閱狀態**的問題。

【確認現象】現象不明時用一句話確認是哪一種（不能新增物件？物件全部下架？扣款/方案異常？）→ extracted_fields.symptom。使用者已描述現象就**直接 converge，不重問**。
【收齊→查 API】action="converge"、converge_kind="answer"；系統會查該角色的訂閱方案並決定性判因（是否訂閱、方案別、額度用量、扣款狀態），你照系統判定作答，不自行推斷。
【區辨紅線】額度用滿與權限不足是兩件事；方案正常時個別物件下架多為必填欄位驗證失敗——依系統查得的現況判斷是哪一種，不臆測。
【不代操作】升級方案、加購額度、變更付款方式只指路（「訂閱方案」頁），不代執行、不承諾扣款結果。
【數值紅線】額度、用量、金額、日期一律引用系統查得的存值，禁止計算或改寫。
【本輪範疇 scope】訂閱方案/額度/扣款/因方案失效造成的功能異常 → scope="stay"。帳單與發票金流、物件本身的操作方式、合約問題 → scope="switch"。不確定 → stay 並澄清。
【制度型問題】純問方案有哪些、費用怎麼算這類**不需查個別狀態**的問題 → scope="switch"（由知識單發回答），不強行進本面向。
每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"symptom":"…"},"next_question":"…","scope":"stay"|"switch","face":"…（如有）"}$RULES$,
       '對話規則',
       ARRAY['pm_subscription_diag']::text[],
       TRUE,
       '{
           "conversational_config": {
               "key": "subscription_diag",
               "persona_role": "pm_subscription_diag",
               "answer_mode": "conversational",
               "enabled": true,
               "topic_scope": {"mode": "category", "category": "條件診斷：訂閱"},
               "answer_rules": "## 收斂作答鐵則\n- 底稿即該帳號的訂閱現況，照系統判定直接作答，不自加原因。\n- 額度用滿 vs 權限不足 vs 個別物件驗證失敗：依底稿判定講，不臆測。\n- 不代操作：升級方案/加購額度/變更付款方式只指路（訂閱方案頁），不代執行、不承諾扣款結果。\n- 額度、用量、金額、日期只引用底稿存值，禁止計算或改寫。\n- 方案失效導致物件自動下架時，明講需完成續約後**自行重新上架**，系統不代為復原。\n- 追問輪只答新問題，不整段重複已述的方案現況。\n- 制度型問題（方案有哪些、費用怎麼算）不在本面向範疇，交回知識單發。",
               "grounding_scope": {
                   "select": "api",
                   "endpoint": "jgb_subscription",
                   "target_user": "property_manager",
                   "required_slots": ["symptom"],
                   "params": {"role_id": "{session.role_id}"},
                   "result_mapping": {"label_field": "plan_type"}
               }
           }
       }'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
                  WHERE category = '對話規則' AND question_summary = '對話規則：訂閱診斷');

-- 3-3 讓 3505／3506 能提名訂閱診斷面向
--     ⚠️ **前置（array_prepend 不可省）**：first-commit-wins 之下候選順序具語義。
--     3505/3506 現有 categories = [條件診斷：物件, 物件操作引導]，
--     `物件操作引導` → estate_guide（select=category，無能力）會先 commit。
--     業主明示：「新增 Face 後 estate_guide 仍先 commit ＝ 配置成功、能力交接失敗，不算 PASS」。
--     ⇒ 必須 **prepend**，不是 append。
--     ⛔ 不動 3507（條件診斷：物件／狀態判斷／物件現況診斷）——它是合約建立受阻，非訂閱問題。
UPDATE knowledge_base
SET categories = array_prepend('條件診斷：訂閱', categories)
WHERE id IN (3505, 3506)
  AND is_active
  AND NOT ('條件診斷：訂閱' = ANY(COALESCE(categories, ARRAY[]::text[])));
