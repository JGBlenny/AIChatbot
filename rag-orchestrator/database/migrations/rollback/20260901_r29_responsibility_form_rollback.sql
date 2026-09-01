-- rollback of 20260901_r29_responsibility_form
-- ⚠️ 只刪**本次新增的那一個 stable identity**。
-- ⛔ 不得依欄位名稱刪「所有收 bill_ref 的 form」、⛔ 不得碰任何 legacy form。
DELETE FROM form_schemas WHERE form_id = 'resp_r29_receipt_actual_amount';
DELETE FROM schema_migrations WHERE migration_name = '20260901_r29_responsibility_form';
