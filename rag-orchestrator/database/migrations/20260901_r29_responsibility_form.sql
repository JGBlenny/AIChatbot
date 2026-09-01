-- 20260901_r29_responsibility_form
-- R-29（receipt.actual_amount.v1）專用的 responsibility-mode 輸入表單。
--
-- 為何需要（2026-09-01 於 S2 接線前 inspect 抓到）：
--   responsibility resolver 讀 collected_data["bill_ref"]
--     （_RESOLVER_SPECS["bill.by_ref.v1"]["form_ref_field"] = "bill_ref"）
--   而 legacy 的 jgb_bill_diagnosis 收的欄位叫 "bill_id"；
--   form_manager 以 field_name 逐字建 collected_data（⛔ 無改名層）
--   ⇒ 若讓 R-29 重用 legacy form，resolver 每次都拿到 None → INVALID_INPUT，
--     表面只會看到「請提供帳單編號」無限追問。
--   業主裁定：這是 INPUT_CONTRACT_MISMATCH，⛔ 不得用漂亮文案掩蓋。
--
-- 紀律（業主 2026-09-01 定）：
--   ✅ additive：只 INSERT 一筆新 definition
--   ⛔ 不 UPDATE jgb_bill_diagnosis、⛔ 不動既有 form、⛔ 不 backfill 任何 session
--   ✅ idempotent：靠 form_id UNIQUE，⛔ 不用「prompt 文字相同就跳過」這種寬鬆判斷
--   ⛔ 輸入 shape 相同 ⛔ 不等於 semantic responsibility 相同
--      ⇒ 其他責任即使也收 bill_ref，⛔ 不得自動共用本 form
--
-- prompt 暫維持「請提供帳單編號」：bill.by_ref.v1 雖也支援非數字 ref
-- （keyword → 唯一合約 → 帳單），但該分支的外部驗證（D1-R2）**尚未執行**，
-- ⇒ UI ⛔ 不承諾尚未 externally validated 的能力。放寬措辭需另裁。

INSERT INTO form_schemas
    (form_id, form_name, fields, vendor_id, is_active,
     description, on_complete_action, skip_review)
VALUES
    ('resp_r29_receipt_actual_amount',
     'R-29 收據實收金額（responsibility）',
     '[{"field_name": "bill_ref", "field_label": "帳單編號", "field_type": "text",
        "required": true, "prompt": "請提供帳單編號", "validation_type": "free_text"}]'::jsonb,
     NULL,
     TRUE,
     'R-29 / receipt.actual_amount.v1 專用 responsibility 輸入表單。field_name 必須逐字等於 bill.by_ref.v1 的 form_ref_field（bill_ref）——見 F-C27。⛔ 不得與 legacy jgb_bill_diagnosis 共用。',
     'show_knowledge',
     TRUE)
ON CONFLICT (form_id) DO NOTHING;
-- ⚠️ on_complete_action 對 responsibility mode **不生效**：
--    form_manager._complete_form 依 session_authority_mode 派發（T4-D1），
--    ⛔ 不讀本欄。此處填 schema 預設值僅為滿足 CHECK 約束。
