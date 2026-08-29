-- =====================================================
-- Level-A scope（bill_diagnosis）最後 6 筆 reviewed declaration（業主逐筆裁定 2026-08-29）
--
-- ⚠️ provenance = **reviewed_product_declaration**，與 deterministic 明確區分：
--   前者是產品裁定，後者是可重播的 machine evidence。半年後必須分得出來。
--
-- ⚠️ 裁定所依據的**正面證據**（⛔ 不是「answer 是空的」這一點本身）：
--   三件事同時成立才構成證據——
--     ① KB 對同一主題成對存在「general mechanism row」與「instance lookup anchor」
--     ② anchor row 的 answer 長度為 0、無任何動作
--     ③ `chat.py::_drop_empty_answer_rows` 明定：empty-answer／no-action row
--        **只供 Face 進場**，不得落回 single-shot answer
--   ⇒ 這是**產品設計本身**把同一主題拆成「規則說明」與「個別查值」兩個責任，
--     ⛔ 不是「看起來比較像 instance」。
--
-- ⚠️ general 側同樣有正面理由，⛔ 不是「沒看到 instance evidence」：
--   同一需求即使完全不知道使用者自己的帳單／合約狀態，仍能完整正確回答；
--   真正需要個別資料的版本已由另一筆 anchor 明確承接。
--
-- 冪等：已宣告者不覆寫。
-- =====================================================

WITH ruling(kid, value, reason) AS (VALUES
  (3402, 'general',
   '問的是系統流程與產生機制（是否自動產生、如何結算）；正確回答不需要知道使用者是哪份合約或哪張帳單。無成對 anchor，但產品命題本身正向成立：答案取決於系統規則，不取決於當下哪張帳單的實值。'),
  (3406, 'general',
   '問的是下載機制與操作位置。即使系統可查實際收據，回答「怎麼下載 PDF」不需先讀此人的付款資料。且 4640 已另立「查實際收據金額」錨點，形成正面語義分工。'),
  (3519, 'general',
   '190 字本身承載計算規則、算式與例子；不需讀某份合約即可正確解釋「怎麼算」。4657 另立實際金額查詢錨點，進一步證明 KB 有意把「規則」與「查值」拆開。'),
  (4640, 'instance',
   '問的是實際金額，不讀該帳單／收據資料無法知道「多少錢」。diagnose_bill 的 B05 確實取實值；且本列是 empty-answer Face-entry anchor，設計上就不是拿通用文字回答。'),
  (4656, 'instance',
   '要查某一筆帳單；bill_diagnosis 的 required_slots=[bill_ref]，後續走 _format_bill_status。沒有特定帳單 referent 就無法完成 intent。'),
  (4657, 'instance',
   '「查點退金額」要求該份合約／帳單的實際值，不讀 runtime data 無法回答。與 3519 的規則型 row 成對，且自身是 empty-answer entry anchor。')
)
UPDATE knowledge_base k
SET generation_metadata =
      COALESCE(k.generation_metadata, '{}'::jsonb)
      || jsonb_build_object(
           'instance_applicability', r.value,
           'instance_applicability_provenance',
           jsonb_build_object('source', 'reviewed_product_declaration',
                              'ruling', 'Level-A truth 逐筆裁定 2026-08-29',
                              'scope', 'bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)',
                              'reason', r.reason,
                              'recorded', '2026-08-29'))
FROM ruling r
WHERE k.id = r.kid
  AND k.is_active
  AND NOT (COALESCE(k.generation_metadata, '{}'::jsonb) ? 'instance_applicability');
