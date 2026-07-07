-- ============================================================
-- 條件診斷：帳單 面向收編（系統回測 run307「帳單發不出去」死路逼出）
--
-- 根因：帳務域五面向皆有對話規則，唯「條件診斷：帳單」（知識 3495 發不出去/
-- 3496 取消不了/3498 逾期費/3499 手動到帳失敗）漏 seed → 進場判定查無 config
-- → 落回 v1.1 表單（只收帳單編號）→ 無編號死路。
-- 修法沿合約診斷先例：規則識別鏈抄「繳費金流排障」(3915)，收斂 secondary_call
-- 改打 jgb_bill_detail、face 由 formatter 的決定性 diagnose_bill 引擎接手。
-- 冪等：WHERE NOT EXISTS。
-- ============================================================

-- ── 1. 對話規則：帳單診斷 ──
INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active, generation_metadata)
SELECT
    '對話規則：帳單診斷',
    $RULES$你是 JGB 智慧租賃平台的「帳單操作診斷助理」，協助管理者查「這筆帳單為什麼發不出去／取消不了／被收逾期費／手動到帳失敗」這類單筆操作問題。

【追問識別】收斂前必須取得帳單識別 bill_ref（帳單編號；沒有編號時可用合約編號或物件名稱，系統會列該合約的帳單候選）→ extracted_fields.bill_ref。只要給出編號或名稱就視為已取得，直接 action="converge"，不要再問。多筆由系統列候選處理。
【不重問現象】對方開頭已講明是哪種問題（發不出去/取消不了/逾期費/手動到帳）→ 全程記住，不再確認現象；symptom 非收斂必要條件，拿到 bill_ref 就 converge，系統會依原句判定診斷項。
【收齊→查 API】bill_ref 已有 → action="converge"、converge_kind="answer"；系統會依帳單現況判定該操作可否執行與阻擋原因（草稿才能發送/取消、明細完整性、手動到帳條件），你照系統判定作答，不自行推斷原因。
【金額紅線】金額一律引用系統提供的存值，禁止自行計算、加總或改寫數字。
【API 現值為準】一切以系統查得的現值為準；不複述內部狀態代碼，用狀態名稱講。
【本輪範疇 scope】是帳單操作可否/原因相關、或在回答你剛問的問題 → scope="stay"。帳單金額組成/看不到帳單（帳單異常）、繳費入帳（繳費金流排障）、其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
【本輪面向 face】若有提供【本領域可用面向】，從中選最貼近這句的一個放入 face；純識別/不明確 → 省略。
每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"bill_ref":"…","symptom":"…（如有）"},"next_question":"…","scope":"stay"|"switch","face":"…（如有）"}$RULES$,
    '對話規則',
    ARRAY['pm_bill_diagnosis']::text[],
    TRUE,
    -- BEGIN_METADATA_JSON bill_diagnosis
    '{
        "conversational_config": {
            "key": "bill_diagnosis",
            "persona_role": "pm_bill_diagnosis",
            "answer_mode": "conversational",
            "enabled": true,
            "topic_scope": {"mode": "category", "category": "條件診斷：帳單"},
            "answer_rules": "## 收斂作答鐵則\n- 底稿開頭「編號｜名稱」即對方問的那筆帳單，照底稿直接作答，不推託。\n- 可否發送/取消/手動到帳＝照底稿系統判定轉述，禁止自加原因；底稿列了阻擋原因就照列。\n- 金額只引用底稿存值，禁止計算或改寫數字。\n- 底稿導客服時附上底稿列出的事實（帳單編號/狀態），不憑印象斷言原因。\n- 一切以 API 現值為準，脈絡通則不覆寫這筆資料。",
            "grounding_scope": {
                "select": "api",
                "endpoint": "jgb_bills",
                "params": {"role_id": "{session.role_id}"},
                "search_params": [
                    {"bill_ref": "{form.bill_ref}"}
                ],
                "required_slots": ["bill_ref"],
                "result_mapping": {
                    "id_field": "id",
                    "list_path": "data",
                    "label_field": "title",
                    "label_fields": ["title", "sub_title", "date_expire", "total"],
                    "refine_param": "bill_ref",
                    "candidate_cap": 8,
                    "skip_refine": true,
                    "entity_noun": "帳單",
                    "label_date_fields": ["date_expire"]
                },
                "secondary_call": {
                    "endpoint": "jgb_bill_detail",
                    "params": {"bill_id": "{row.id}", "role_id": "{session.role_id}"},
                    "attach_as": "bill_detail",
                    "list_path": "data"
                }
            }
        }
    }'::jsonb
    -- END_METADATA_JSON bill_diagnosis
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：帳單診斷'
);

-- ── 2. 系統脈絡：帳務領域-帳單診斷（子面向）──
INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active)
SELECT
    '系統脈絡：帳務領域-帳單診斷(子面向)',
    $CTX$帳單操作診斷的解讀脈絡（制度通則，個案一律以 API 現值為準）：
- 帳單生命週期：草稿（待發送）→ 已發送 → 已繳費/已完成；封存與作廢為終態。
- 只有「草稿」狀態可以發送與取消；已發送的帳單不能重發送，要改內容須先取消（若狀態允許）再重建。
- 發送前系統會驗證明細完整性：至少一筆收費項目、度數類費用（電費等）本期度數已填且不小於上期、金額不為 0。
- 手動到帳（標記已收款）僅適用尚未透過線上金流繳費的帳單；已走金流的帳單由系統自動對帳，不能手動標記。
- 逾期費（延遲金/滯納金）依合約的滯納金設定與團隊結算機制產生；個案減免請聯繫客服。
- 不複述內部狀態代碼（bit_status），對使用者一律用狀態名稱。$CTX$,
    '條件診斷：帳單',
    ARRAY['property_manager']::text[],
    TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE question_summary = '系統脈絡：帳務領域-帳單診斷(子面向)'
);

-- ── 2.5 繳費金流排障同款候選旗標（盤查 run310 逼出：帳單候選>cap 時白耗補識別輪
--        且訊息喊「合約」——同一合約多期帳單補識別縮不了，直接列候選）──
UPDATE knowledge_base SET generation_metadata = jsonb_set(jsonb_set(generation_metadata,
  '{conversational_config,grounding_scope,result_mapping,skip_refine}', 'true'),
  '{conversational_config,grounding_scope,result_mapping,entity_noun}', '"帳單"')
WHERE category='對話規則' AND question_summary='對話規則：繳費金流排障'
  AND COALESCE(generation_metadata->'conversational_config'->'grounding_scope'->'result_mapping'->>'skip_refine','') <> 'true';

-- ── 3. 兄弟題補掛協同分類（稽核逼出；沿 3497/3502/3503 既有雙掛慣例）──
-- 3500/3501 信用卡付款失敗 → 補掛「繳費金流排障」（兄弟題 3497/3502 已雙掛）
UPDATE knowledge_base
SET categories = array_append(categories, '繳費金流排障')
WHERE id IN (3500, 3501)
  AND NOT ('繳費金流排障' = ANY(categories));

-- 3504 發票作廢不了 → 補掛「發票」（兄弟題 3503 已雙掛）
UPDATE knowledge_base
SET categories = array_append(categories, '發票')
WHERE id = 3504
  AND NOT ('發票' = ANY(categories));

-- 驗證
DO $$
DECLARE n INT; m INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category='對話規則' AND question_summary='對話規則：帳單診斷';
    SELECT COUNT(*) INTO m FROM knowledge_base
    WHERE id IN (3500,3501,3504,3495,3496,3498,3499) AND is_active
      AND EXISTS (
        SELECT 1 FROM knowledge_base r
        WHERE r.category='對話規則' AND r.is_active
          AND r.generation_metadata->'conversational_config'->'topic_scope'->>'category' = ANY(knowledge_base.categories));
    RAISE NOTICE '✅ 帳單診斷規則：% 筆；動作知識有面向接管：% / 7 筆（套用後請清設定快取/重啟）', n, m;
END $$;
