-- ============================================================
-- 3498 停用（業主裁定 2026-08-29，T2 逐 claim 涵蓋比對）
--
-- Verdict：K1 FULLY_SUBSUMED ＋ UNDER_QUALIFIED_DUPLICATE
--   3498 的 48 字全部被 union(3531, 3532) 承接（C5 = NONE，⛔ 無獨立責任殘留）；
--   且它把公式寫成**無條件**，對階梯式／固定金額版團隊會給出**錯誤金額**。
--   ⇒ 停用**不損失 truth**，反而移除誤導性斷言。
--
-- ⚠️ **失效，不失憶**：⛔ 不刪除任何既有宣告與 provenance。
--   `instance_applicability` 與 `retrieval_representation` 原值保留，
--   僅在 metadata 標記 retirement，使其
--   effective_for_routing / scoring / population 皆為 false。
--   保留的理由：未來要能回答「為什麼 A04 當時是 10 rows」。
--
-- ⚠️ 停用理由**不是** A04 的檢索表現——A04 根本沒跑 harness。
--
-- 冪等：已停用者不重複標記。
-- ============================================================

UPDATE knowledge_base
SET is_active = FALSE,
    generation_metadata =
      COALESCE(generation_metadata, '{}'::jsonb)
      || jsonb_build_object(
           'retirement',
           jsonb_build_object(
             'retired_at', '2026-08-29',
             'verdict', 'K1_FULLY_SUBSUMED + UNDER_QUALIFIED_DUPLICATE',
             'subsumed_by', jsonb_build_array(3531, 3532),
             'ownership_consolidated_to', 'late_fee face (build_late_fee_facts)',
             'not_because', 'A04 retrieval performance（A04 未執行 harness）',
             'declarations_status', 'historical retained; operationally inactive',
             'effective_for_routing', false,
             'effective_for_scoring', false,
             'effective_for_population', false,
             'ruling_doc', 't2-3498-knowledge-identity.md')),
    updated_at = NOW()
WHERE id = 3498
  AND is_active
  AND NOT (COALESCE(generation_metadata, '{}'::jsonb) ? 'retirement');
