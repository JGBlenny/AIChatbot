-- =====================================================
-- P1e population 第一批：**只寫 34 筆 deterministic instance**（業主裁定① 2026-08-29）
--
-- ⚠️ 裁定原文的關鍵理由（⛔ 不得簡化成「錯得起就寫」）：
--   > `instance_applicability` 是**事實契約**，不是風險控制參數。
--   「判錯 instance 比判錯 general 安全」可以影響 rollout policy，
--   ⛔ **不能降低資料真值的證據門檻**——否則就是把「安全偏好」偷偷寫成「事實」。
--
-- 因此只有具備**可重播 machine evidence**（E1 引擎 docstring／E2 識別碼表單／
-- E3 動作端點）的 34 筆進入 authority contract。
--   76 筆 blind-consensus instance → **INSTANCE_PROPOSAL，不寫入**（見 ledger）
--  742 筆 consensus general        → **不寫入**（正對照 3509 已證此法會產生 false general）
--   21 筆分歧                       → UNKNOWN
--
-- provenance 與值同時落地：半年後看到 instance_applicability='instance'，
-- 必須分得出它是引擎契約推出來的、還是標註者判的。
-- 冪等：已宣告者不覆寫。
-- =====================================================

WITH prov(kid, meta) AS (VALUES
  (3361, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_bill_query → jgb_bills（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3362, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_invoice_query → jgb_invoices（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3365, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_repair_query → jgb_repairs（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3366, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_payment_query → jgb_payments（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3368, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3370, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3371, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3372, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3490, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3491, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3492, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3493, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3494, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3495, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/bills.py::_diagnose_cannot_send（B01）", "form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3496, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/bills.py::_diagnose_cannot_cancel（B02）", "form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3497, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/payments.py::_diagnose_payment_not_reflected（P01）", "form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3498, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3499, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3500, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/payments.py::_diagnose_credit_card_failure（P02）", "form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3501, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3502, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3503, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/invoices.py::_diagnose_issue_failure（I01）", "form=jgb_invoice_diagnosis → jgb_invoice_logs（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3504, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/invoices.py::_diagnose_invalid_failure（I02）", "form=jgb_invoice_diagnosis → jgb_invoice_logs（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3505, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/subscription.py::_diagnose_cannot_add_estate（E01）", "form=jgb_subscription_diagnosis → jgb_subscription（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3506, '{"source": "deterministic", "evidence_source": ["E1_ENGINE_TITLE", "E2_IDENTIFIER_FORM"], "evidence_detail": ["services/jgb/subscription.py::_diagnose_estates_delisted（E02）", "form=jgb_subscription_diagnosis → jgb_subscription（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3507, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3508, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_iot_diagnosis → jgb_iot_manufacturers（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3510, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3511, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3512, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3513, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (3514, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_tenant_query → jgb_tenant_summary（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (4255, '{"source": "deterministic", "evidence_source": ["E2_IDENTIFIER_FORM"], "evidence_detail": ["form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb),
  (4420, '{"source": "deterministic", "evidence_source": ["E3_ACTION_API"], "evidence_detail": ["action=api_call → jgb_repairs"], "recorded": "2026-08-29", "ruling": "P1e-1 業主裁定①"}'::jsonb)
)
UPDATE knowledge_base k
SET generation_metadata =
      COALESCE(k.generation_metadata, '{}'::jsonb)
      || jsonb_build_object('instance_applicability', 'instance',
                            'instance_applicability_provenance', p.meta)
FROM prov p
WHERE k.id = p.kid
  AND k.is_active
  AND NOT (COALESCE(k.generation_metadata, '{}'::jsonb) ? 'instance_applicability');
