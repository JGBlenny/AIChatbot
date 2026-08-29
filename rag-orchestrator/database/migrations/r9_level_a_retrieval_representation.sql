-- =====================================================
-- Level-A scope（bill_diagnosis）10 筆 `retrieval_representation`（業主逐筆裁定 2026-08-29）
--
-- ⚠️ D3 **reviewed migration only**：legacy summary／keywords／answer 只能作 proposal
--   evidence；⛔ 自動拼接／自動摘要**不得**成為 contract truth。本檔每一筆都經過
--   逐筆 review，provenance = `reviewed_product_declaration`。
--
-- ⚠️ 裁量規則（業主定案，**兩類 row 不能用同一把尺**）：
--     general row  → representation 對齊 **Knowledge answer responsibility**
--     instance row → representation 對齊 **Face／downstream capability responsibility**
--   ⇒ 3406／3519 是 general，⛔ 不因 `_format_bill_status` 沒有那些能力而收窄。
--
-- ⚠️ 紅線：representation ⛔ 不得替 answer **發明** truth。判準是 answer 裡
--   「有沒有」，⛔ 不是「寫得完不完整」：
--     3519 answer 明文寫了正負語義 → 可以表示 ✅
--     3499 answer 說「常見三種」卻沒列 → ⛔ 不可由 representation 補造
--
-- ⚠️ 4657 的前提是 `POINT_REFUND_BILL_SELECTION` 已實作且經 6 道 guard ＋ 3 個
--   mutation 證實（type=2 為唯一身分依據、provenance 不斷鏈）。
--   ⛔ 本輪**不**宣稱「某合約某類帳單的通用 selection capability 已完成」——
--     證明的只有 point-refund 這一條。
--   ⚠️ 「多筆時列候選」**刻意不寫進 representation**：那是 execution／
--     disambiguation contract，⛔ 不是這筆 Knowledge 承接的 semantic intent。
--
-- 冪等：已宣告者不覆寫。
-- =====================================================

WITH ruling(kid, repr) AS (VALUES
  (3402, '點退完成後系統何時／在什麼條件下自動產生點退帳單，以及該帳單如何進入費用結算。'),
  (3406, '如何取得帳單收據／繳費證明：下載的位置與方式、收據可作為繳費證明、未繳費的帳單無法產生收據，以及收據與統一發票的區別。'),
  (3495, '診斷某一筆帳單為什麼無法發送給租客，包含發送失敗、寄不出、按發送無反應等情形。'),
  (3496, '診斷某一筆帳單為什麼無法取消或作廢，包含取消按鈕不可用、取消時失敗等情形，以及可取消所需的帳單狀態條件。'),
  (3498, '診斷某一筆帳單為什麼被收取逾期費、延遲金或滯納金，以及該筆費用的計算依據與金額如何得出。'),
  (3499, '查詢／診斷特定帳單手動到帳失敗、無法完成手動入帳的原因。'),
  (3519, '點退帳單金額如何計算：加總哪些結算項目、如何扣抵押金，以及金額為正負時分別代表退款或需補繳差額。'),
  (4640, '查詢某一張收據的實際金額，例如某筆帳單的收據實收多少錢。'),
  (4656, '找出並查詢某一筆帳單目前的狀態，包括是否已繳費、是否已寄出或仍為草稿、到期情形，以及該筆帳單的現況。'),
  (4657, '查詢某份合約的點退帳單，包含該筆點退帳單的實際金額與目前狀態。')
)
UPDATE knowledge_base k
SET generation_metadata =
      COALESCE(k.generation_metadata, '{}'::jsonb)
      || jsonb_build_object(
           'retrieval_representation', r.repr,
           'retrieval_representation_provenance',
           jsonb_build_object('source', 'reviewed_product_declaration',
                              'ruling', 'R9 Level-A representation 逐筆裁定 2026-08-29',
                              'scope', 'bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)',
                              'recorded', '2026-08-29'))
FROM ruling r
WHERE k.id = r.kid
  AND k.is_active
  AND NOT (COALESCE(k.generation_metadata, '{}'::jsonb) ? 'retrieval_representation');
