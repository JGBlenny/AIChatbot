-- =====================================================
-- routing-disambiguation｜design erratum 01（design v1.2）：
-- 為 `bill_diagnosis` 補上 Face 層第一級語義契約 `requires_instance_reference`。
--
-- 背景：erratum 01 裁定 membership 不得由 `required_slots` 推導
--   （實查 22 個 Face 中 13 個 required_slots 非空——那個等價會一次納管 13 個），
--   亦不得由 face key 或 `bill_ref` 推導。Face 必須**自己明示**這件事。
--
-- 語義：本面向的 Routing Hint 要成立，使用者問句**必須指涉某一個既存個體**。
--   ⚠️ 這與「執行時需要哪些欄位」（required_slots）**是兩件事**。
--
-- ⚠️ **逐 Face 裁定，禁止批次推導**：本檔**只**改 bill_diagnosis。
--   billing_anomaly／billing_invoice／billing_flow 各自的產品責任尚未逐一裁定，
--   不得因為它們同樣收 bill_ref 就一併補宣告——那是把已否決的 family 方案從後門裝回來。
--
-- ⚠️ 宣告 ≠ 啟用：實際納管還需 rollout scope（`in_gate_rollout_scope`）同時成立，
--   且 `INSTANCE_REFERENCE_GATE` 旗標預設 false、holdout 未過前不得啟用。
--
-- 套用：bash rag-orchestrator/database/migrate.sh --apply（帳本感知，冪等）
-- 套用後清快取（重啟或後台 /conversational-config 任一儲存）。
-- =====================================================

UPDATE knowledge_base
SET generation_metadata = jsonb_set(
        generation_metadata,
        '{conversational_config,grounding_scope,requires_instance_reference}',
        'true'::jsonb,
        true),
    updated_at = now()
WHERE category = '對話規則'
  AND question_summary = '對話規則：帳單診斷'
  AND is_active
  AND COALESCE(
        generation_metadata #> '{conversational_config,grounding_scope,requires_instance_reference}',
        'null'::jsonb) IS DISTINCT FROM 'true'::jsonb;
