-- =====================================================
-- P1e-2：23 個 Face 的 requires_instance_reference 全量 population
--
-- ⚠️ 判準＝業主裁定③ 的 (B) 定義，⛔ **不看 execution shape**：
--   > This Face is applicable only when correctly fulfilling the user's intent
--   > depends on user-specific or instance-specific runtime data.
--
-- ⛔ 以下捷徑一律不得作為依據（它們只是 execution shape）：
--   select=api → REQUIRED ／ 有 required_slots → REQUIRED ／
--   有 endpoint → REQUIRED ／ 名字像 diagnosis → REQUIRED
-- ⇒ 證據一律取自 **Face 自己宣告的責任**（persona 開頭句／scope 規則）。
--
-- ⚠️ NOT_REQUIRED **也要有正面證據**——⛔ 不重演 knowledge general 那個坑
--   （「沒看到 instance evidence」≠ NOT_REQUIRED）。
--
-- ⚠️ 不改 routing：`gate_active()` 是最外層守衛，`INSTANCE_REFERENCE_GATE` 未設
--   ⇒ `_instance_gate_decision` 回 None ⇒ 永不抑制。本次寫入的是**授權輸入**，
--   不是授權本身；gate 仍 PAUSED。
--
-- 冪等：已宣告者不覆寫。
-- =====================================================

-- ── REQUIRED（16）：責任本身就是查某個使用者自己的狀態／資料 ──
UPDATE knowledge_base
SET generation_metadata = jsonb_set(generation_metadata,
      '{conversational_config,grounding_scope,requires_instance_reference}', 'true'::jsonb, TRUE)
WHERE category = '對話規則' AND is_active
  AND generation_metadata->'conversational_config'->>'key' IN (
      'account_login',        -- 「租客登不進去/登入後看不到資料」→ 須查該租客的綁定與合約
      'account_team',         -- 「某成員看不到某帳單/合約/物件」→ 須查該成員權限
      'bill_diagnosis',       -- 「**這筆**帳單為什麼發不出去…」
      'billing_anomaly',      -- 「金額不對/帳單沒出現/租客看不到帳單」
      'billing_flow',         -- 「租客說繳了但錢沒進來/帳單狀態沒動」
      'billing_invoice',      -- 「發票開了沒」＝實值
      'billing_late_fee',     -- 「**這份合約/這筆帳單**的滯納金怎麼算」
      'contract_change',      -- 能不能改、能不能轉歷史/刪除 → 取決於該合約狀態
      'contract_closeout',    -- 把**這份**退租流程走完
      'contract_diag',        -- 「查詢與診斷**自己的某一份合約**」（責任明文）
      'contract_renew',       -- 「**可否**系統續約」→ 取決於該合約
      'contract_sign',        -- 簽署卡關排查 → 該合約/該租客
      'estate_diag',          -- 「查**特定物件**的現況」（責任明文）
      'iot_meter',            -- 「租客沒電/電表離線/度數怪怪的」→ 該顆電表
      'repair_create',        -- 責任明文「**物件由租約帶入**」→ 須讀該租客租約
      'subscription_diag')    -- 責任明文「**需要查該帳號實際訂閱狀態**」
  AND NOT (generation_metadata->'conversational_config'->'grounding_scope' ? 'requires_instance_reference');

-- ── NOT_REQUIRED（6）：**皆有正面證據**，非「沒看到 instance 跡象」 ──
UPDATE knowledge_base
SET generation_metadata = jsonb_set(generation_metadata,
      '{conversational_config,grounding_scope,requires_instance_reference}', 'false'::jsonb, TRUE)
WHERE category = '對話規則' AND is_active
  AND generation_metadata->'conversational_config'->>'key' IN (
      'account_register',       -- 責任明文「**當事人（租客）不在系統內**」⇒ 根本沒有可讀的個體資料
      'billing_setup_guide',    -- 責任明文「**本面向不查帳單 API**」
      'contract_create_guide',  -- 責任明文「**本面向不查合約 API**」
      'estate_guide',           -- 責任＝建立/編輯/刊登等**操作方法**（產品知識）
      'iot_setup',              -- 責任＝串接/單價/密碼規則等**設定方法**（產品知識）
      'presales')               -- 售前對象是**潛在客戶**，尚無帳號 ⇒ 無 user-specific runtime data
  AND NOT (generation_metadata->'conversational_config'->'grounding_scope' ? 'requires_instance_reference');

-- ── UNKNOWN（1）：⛔ 刻意不寫入 ──
--   account_binding「換綁手機/信箱、帳號資料修改、**帳號合併**」
--   ・「分流」看似產品知識，但**帳號合併的可行性取決於那兩個帳號的狀態**
--   ・且它**沒有**像 billing_setup_guide／contract_create_guide 那樣的「不查 API」明文
--   ⇒ 責任定義本身不足以判 ⇒ 維持 UNKNOWN，⛔ 不靠名字或 endpoint 猜。
