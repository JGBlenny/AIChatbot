-- 售前池一次性標記已審核（DSP-012 選項 A、R11.6；任務 3.3）— v2 2026-09-05
-- ⚠️ v1 用 b2c 謂詞預覽得 81（多抓 50 筆通用列），主 session 改為 **b2b 謂詞**：prospect ＝ b2b ＋ 無 role_id
--（jgb2 面板送 mode=b2b；tools/gapmap/presales_gap_map.py:POOL_PRED 亦為 business_types && ['system_provider']）。
-- 條件逐條對應 vendor_knowledge_retriever_v2.build_visibility_predicate 的 b2b 分支：
--   1 is_active；2 保留分類排除；3 vendor_ids IS NULL OR && [1]；
--   4 target_user IS NULL OR && ['prospect']（b2b ⛔ 無 all_users）；
--   6a business_types && ['system_provider']（b2b ⛔ 無 IS NULL 放行，D-002）。
-- 預期影響 31 列；預覽不是 31 ⇒ ⛔ 停，回報。
-- rollback：UPDATE knowledge_base SET outline_approved_by=NULL, outline_approved_at=NULL WHERE outline_approved_by='owner-20260905';

-- Step 1：預覽
SELECT count(*) AS matched
FROM knowledge_base kb
WHERE (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && ARRAY[1]::int[])
  AND kb.is_active = TRUE
  AND kb.category IS DISTINCT FROM '系統脈絡'
  AND kb.category IS DISTINCT FROM '對話規則'
  AND kb.business_types && ARRAY['system_provider']::text[]
  AND (kb.target_user IS NULL OR kb.target_user && ARRAY['prospect']::text[])
  AND kb.outline_approved_by IS NULL;

-- Step 2：標記（與 Step 1 同 WHERE）
UPDATE knowledge_base kb
SET outline_approved_by = 'owner-20260905', outline_approved_at = now()
WHERE (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && ARRAY[1]::int[])
  AND kb.is_active = TRUE
  AND kb.category IS DISTINCT FROM '系統脈絡'
  AND kb.category IS DISTINCT FROM '對話規則'
  AND kb.business_types && ARRAY['system_provider']::text[]
  AND (kb.target_user IS NULL OR kb.target_user && ARRAY['prospect']::text[])
  AND kb.outline_approved_by IS NULL;

-- Step 3：驗證（預期 31）
SELECT count(*) AS approved FROM knowledge_base WHERE outline_approved_by = 'owner-20260905';
