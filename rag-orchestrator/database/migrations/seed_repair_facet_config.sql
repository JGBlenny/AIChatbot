-- =====================================================
-- conversational-repair 任務 3.3：修繕交易面向配置（資料，非 schema）
-- 產出①：category_config 分類 '修繕報修'（分類路由 1:1 進場錨點）
--        ＋ knowledge_base 一筆 category='對話規則' 的修繕交易面向配置列。
--
-- 交易面向＝grounding_scope 宣告 execute_endpoint（引擎 _is_transaction_scope 判定，
-- conversational_engine.py:305）。此列驅動：prefill（prefill_api/inference_confidence/
-- candidate_max/degraded_messages）、confirm gate（confirm_template/confirm_qr_labels）、
-- execute（execute_endpoint/execute_params/execute_result_path/receipt_template）、
-- 埋點（facet_key）、進場 gate（enabled_gate）。全鍵塞 grounding_scope，不膨脹 dataclass。
--
-- persona rules_text（answer 欄）＝ 修繕面向開場人格 ＋ 交易面向共用行為範本
-- （conversational_rules.TRANSACTION_FACET_RULES 的三條：收齊→confirm／否定→重確認／
-- 岔題→先答再接）。範本文字內嵌於此（載入慣例：load_rules 只讀 DB answer 欄，
-- 不做常量引用組裝，故內嵌全文；與 conversational_rules.py:77 TRANSACTION_FACET_RULES
-- 常量上方註記的「於 DB 對話規則列內嵌本範本文字」用法一致）。
--
-- ⚠️ execute_params / confirm_template 的槽位名以「修正後 prefill 應產出的扁平標量槽位」
--    為目標形態（estate_id/contract_id/category_id/item_id/estate_display）。現行 prefill
--    （repair_prefill.py）產 estate=dict{estate_id,contract_id,display}、category/item=Vision
--    名稱字串——與本配置對不齊，缺口見同批 README 與交回報告（gap A/B/C，須 2.2/2.3 對齊）。
--    先按目標形態寫入，避免配置被現行實作缺口反向妥協。
--
-- 套用：psql "$DATABASE_URL" -f database/migrations/seed_repair_facet_config.sql
-- 冪等：category_value / (category='對話規則', question_summary) 已存在則不重插。
-- 套用後：清 conversational_config / conversational_rules 快取（重啟 orchestrator 或 reset_cache）。
-- =====================================================

-- ── 0. 分類 '修繕報修'（分類路由進場：意圖錨點知識掛此分類 → config_for_category 命中）──
INSERT INTO category_config (category_value, display_name, description, parent_value, is_active, display_order)
SELECT '修繕報修', '修繕報修', '修繕交易面向（conversational-repair）：租客報修意圖進場分類，1:1 對應修繕面向配置', NULL, TRUE, 500
WHERE NOT EXISTS (SELECT 1 FROM category_config WHERE category_value='修繕報修');

-- ── 1. 修繕交易面向對話規則列（config 本體）──
INSERT INTO knowledge_base (question_summary, answer, category, target_user, business_types, vendor_ids, is_active, generation_metadata)
SELECT
    '對話規則：修繕報修',
    $RULES$你是 JGB 智慧租賃平台的「修繕報修助理」，協助租客用最少的來回把報修單建起來。系統知道的事不要再問（物件由租約帶入、損壞由照片/描述推斷），只問推不出來的（如急迫性），全部齊備後出一次確認摘要讓租客核對再送出——這是會實際建單的交易，收齊不等於送出。

【必要槽位】estate_id（物件，租約帶入的確認型槽位）、category_id（修繕分類）、item_id（損壞項目）、broken_reason（損壞原因）、emergency_status（急迫性，1=緊急/2=一般）。系統已推斷/預填的槽位以「陳述＋允許否定」呈現，不重問。

【交易面向行為（本面向會實際執行寫入，收齊≠送出，務必照下列三條）】
(a) 收齊→確認：當必要槽位（含系統已推斷/預填的確認型槽位）全部齊備時，action="confirm"——輸出一次性確認摘要供租客核對後同意；不要直接送出、confirm 不需 next_question。缺任何必要槽位時才 action="ask"、一次只問一個推不出的槽位。
(b) 否定/修正→更新後重確認：租客否定或修改任一槽位（含對推斷/預填值說「不是…」）時，把更正值填入 extracted_fields，然後重新 action="confirm"（只更新受影響處，不重跑整個流程）。
(c) 岔題→先答再接：租客在收集過程中插入問題（費用/時程/規定等），把即答內容放 inline_answer，並於同一輪的 next_question 自然接回還缺的槽位收集（先答再接，不中斷面向；答案以提供的知識/現況為依據，缺的據實導向出口）。

【抽取】extracted_fields 填本輪能確定的槽位值（含租客對確認型槽位的否定/修正）。
【誠實】知識/現況沒有的細節不杜撰；建單失敗誠實告知可重試，絕不假裝成功。
【輸出 JSON】action="ask"|"confirm"（confirm 時 next_question 可省）、extracted_fields、選填 next_question（ask 必填）、選填 inline_answer（有岔題才放）。$RULES$,
    '對話規則',
    -- target_user 必須含 persona_role（tenant_repair）——load_rules 以 category='對話規則'
    -- ＋target_user @> persona_role 撈規則；不符會找不到規則→引擎降級（e2e 驗出並修正）。
    ARRAY['tenant_repair']::text[],
    NULL,                       -- business_types 空＝全業態通用
    ARRAY[]::integer[],         -- vendor_ids 空＝全業者通用
    TRUE,
    -- BEGIN_METADATA_JSON repair_create
    '{
        "conversational_config": {
            "key": "repair_create",
            "persona_role": "tenant_repair",
            "answer_mode": "conversational",
            "enabled": true,
            "topic_scope": {"mode": "category", "category": "修繕報修"},
            "grounding_scope": {
                "facet_key": "repair",
                "enabled_gate": "repair_enabled",
                "target_user": "tenant",
                "mode": "b2c",

                "prefill_api": "get_tenant_contracts",
                "inference_confidence": 0.7,
                "candidate_max": 3,
                "degraded_messages": {
                    "no_contract": "查不到您名下的有效租約，請先與管理師確認租約狀態，確認後我再協助您報修。"
                },

                "required_slots": ["estate_id", "category_id", "item_id", "broken_reason", "emergency_status"],

                "execute_endpoint": "jgb_create_repair",
                "execute_params": {
                    "role_id": "{session.role_id}",
                    "estate_id": "estate_id",
                    "contract_id": "contract_id",
                    "category_id": "category_id",
                    "item_id": "item_id",
                    "broken_reason": "broken_reason",
                    "broken_note": "broken_note",
                    "emergency_status": "emergency_status",
                    "broken_photos": "broken_photos"
                },
                "execute_result_path": "data.id",

                "confirm_template": "為您確認報修內容，沒問題再送出：\n・物件：{estate_display}\n・設備：{item}\n・狀況：{category}／{broken_reason}\n・急迫性：{emergency_status}\n\n以上正確嗎？",
                "confirm_qr_labels": {
                    "confirm_submit": "✅ 確認送出",
                    "confirm_edit": "✏️ 我要修改",
                    "confirm_cancel": "❌ 取消"
                },
                "receipt_template": "已為您建立報修單 #{ticket_no}，我們會盡快安排處理。之後隨時問我「修得怎樣了」就能查進度。"
            }
        }
    }'::jsonb
    -- END_METADATA_JSON repair_create
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge_base
    WHERE category = '對話規則' AND question_summary = '對話規則：修繕報修'
);

DO $$
DECLARE n_cat INT; n_cfg INT;
BEGIN
    SELECT COUNT(*) INTO n_cat FROM category_config WHERE category_value='修繕報修' AND is_active;
    SELECT COUNT(*) INTO n_cfg FROM knowledge_base
        WHERE category='對話規則' AND question_summary='對話規則：修繕報修' AND is_active;
    RAISE NOTICE '✅ 修繕面向：category_config 修繕報修 %/1，對話規則配置列 %/1', n_cat, n_cfg;
END $$;
