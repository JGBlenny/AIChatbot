-- =====================================================
-- responsibility.delegates 第一版 backfill（spec face-exit-before-grounding）
--
-- 目的：把已由 authoritative persona wording 支持、且經 gated validation 實測走通的
--       **兩條** delegation edge 正式落成 machine-readable contract。
--
--   bill_diagnosis   → billing_anomaly     when: 帳單金額組成/看不到帳單
--   billing_anomaly  → contract_closeout   when: 封存/點退帳單處理
--
-- ⚠️ **只放這兩條**：不掃全站、不把其餘 persona 的自然語言規則批次轉成 delegates
--     （那是 V2 的 responsibility-contract rollout，範圍另計）。
--
-- 本檔同時做兩件必要的事——缺任一條 delegation 都不會發生：
--   (1) metadata.conversational_config.responsibility.delegates
--   (2) 規則 answer 的「每輪輸出 JSON」形狀補上 delegate_facet_key ＋ 三條語義規則
--       （v3 實證：模型只產出 persona 宣告形狀內的欄位；附加在規則之後的 instruction
--         不會進 output——故 (2) 是 (1) 生效的前提）
--
-- 冪等：兩段皆先判是否已套用；重跑不會重複插入或重複改寫。
-- 回滾：seed_responsibility_delegates_v1_rollback.sql
-- =====================================================

BEGIN;

-- (1) delegates 契約 ------------------------------------------------------
UPDATE knowledge_base
SET generation_metadata = jsonb_set(
        generation_metadata,
        '{conversational_config,responsibility}',
        '{"delegates":[{"target":"billing_anomaly","when":"帳單金額組成/看不到帳單"}]}'::jsonb,
        true)
WHERE category = '對話規則'
  AND is_active
  AND generation_metadata->'conversational_config'->>'key' = 'bill_diagnosis'
  AND generation_metadata->'conversational_config'->'responsibility' IS NULL;

UPDATE knowledge_base
SET generation_metadata = jsonb_set(
        generation_metadata,
        '{conversational_config,responsibility}',
        '{"delegates":[{"target":"contract_closeout","when":"封存/點退帳單處理"}]}'::jsonb,
        true)
WHERE category = '對話規則'
  AND is_active
  AND generation_metadata->'conversational_config'->>'key' = 'billing_anomaly'
  AND generation_metadata->'conversational_config'->'responsibility' IS NULL;

-- (2) 輸出契約：把 delegate_facet_key 納入規則宣告的每輪輸出形狀 -------------
--     作法：在「每輪輸出 JSON：{…}」該行最後一個 } 之前插入欄位，並於行末附語義規則。
--     ⚠️ 只對上面兩個面向；其餘 Face 的規則**逐位元不動**。
UPDATE knowledge_base kb
SET answer = regexp_replace(
        kb.answer,
        '(每輪輸出 JSON：\{[^\n]*)\}',
        '\1,"delegate_facet_key":"…（見下）"}' || chr(10) ||
        '【delegate_facet_key 規則】scope="stay" → 必須為 ""；' ||
        'scope="switch" 且符合上列已宣告的轉交對象 → 必須填該對象的鍵；' ||
        'scope="switch" 但無法對應合法轉交對象 → ""。'
    )
WHERE kb.category = '對話規則'
  AND kb.is_active
  AND kb.generation_metadata->'conversational_config'->>'key' IN ('bill_diagnosis', 'billing_anomaly')
  AND kb.answer LIKE '%每輪輸出 JSON：%'
  AND kb.answer NOT LIKE '%delegate_facet_key%';

COMMIT;

-- 執行後補帳本（runbook §17 範式）：
-- INSERT INTO schema_migrations (migration_name, created_by)
-- VALUES ('seed_responsibility_delegates_v1', 'runbook-<date>')
-- ON CONFLICT DO NOTHING;
