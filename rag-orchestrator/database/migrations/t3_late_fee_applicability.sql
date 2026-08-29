-- ============================================================
-- 滯納金域 applicability 補齊（業主逐筆裁定 2026-08-29）
--
-- ⚠️ 這是 **positive declaration**，⛔ 不是「沒看到 instance 證據所以當 general」。
-- ⚠️ 補這一刀的原因：late-fee instance owner 已收斂成 B（滯納金 face），
--    但 B 的主要 entry anchors（3939／3940）**沒有 applicability authority 宣告**
--    ⇒ 是 ownership 收斂後留下的空窗，⛔ 不能留到 A05 之後才補。
--
-- ⚠️ ⛔ **不因此把任何一列加進 LEVEL_A_V2**——內容／責任 successor
--    ⛔ 不等於 routing-scope successor。要擴 scope 需另立 LEVEL_A_V3 決策。
--
-- 冪等：已宣告者不覆寫。
-- ============================================================

WITH ruling(kid, value, reason) AS (VALUES
  (3531, 'general',
   '承接的是規則／機制說明：付款後結算的延遲金機制、公式與適用條件。即使完全不知道使用者是哪份合約、哪張帳單，仍能完整正確回答「系統的滯納金怎麼運作」。⛔ 不需要 runtime data 才成立。'),
  (3532, 'general',
   '承接的是不同客製版本的計算機制差異（延遲金版／階梯式版／固定金額版）。回答「各版本行為差異」不需先讀任一使用者的合約或帳單實值。'),
  (3939, 'instance',
   'empty-answer entry anchor，責任由唯一 owner 的 late_fee face／build_late_fee_facts 決定。該能力提供的是某一筆的實際金額、實際狀態、合約設定實值、實際結算備註與付款／到帳時間——沒有特定 referent 就無法完成 intent。'),
  (3940, 'instance',
   'empty-answer entry anchor，同上：由 build_late_fee_facts 以該筆的存值與結算備註作答。「這筆怎麼算的」必須讀該筆實際資料。')
)
UPDATE knowledge_base k
SET generation_metadata =
      COALESCE(k.generation_metadata, '{}'::jsonb)
      || jsonb_build_object(
           'instance_applicability', r.value,
           'instance_applicability_provenance',
           jsonb_build_object('source', 'reviewed_product_declaration',
                              'ruling', '滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath）',
                              'scope', 'late_fee face（⛔ 不在 LEVEL_A_V2 內）',
                              'reason', r.reason,
                              'recorded', '2026-08-29'))
FROM ruling r
WHERE k.id = r.kid
  AND k.is_active
  AND NOT (COALESCE(k.generation_metadata, '{}'::jsonb) ? 'instance_applicability');
