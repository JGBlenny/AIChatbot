-- =====================================================
-- agentic-mcp-orchestration 任務 3.3：一次性把現有售前池標記為已審核（R11.6）
--
-- ⛔ 一次性操作，⛔ 不放 database/migrations/ 目錄（那裡只放結構遷移）。
-- ⛔ 本檔只寫檔、不執行；DB 寫入需業主授權，由業主自行執行。
--
-- 選列條件＝`services/vendor_knowledge_retriever_v2.py:build_visibility_predicate`
-- 對 prospect 身分（vendor_id=1, target_user='prospect', mode='b2c'）產生的謂詞，
-- 逐條翻成純 SQL（prospect 非 b2b ⇒ 走 b2c 分支，業態用「寬鬆＋vendor 1 業態」）：
--
--   條件 1（vendor_ids）  array_length(kb.vendor_ids,1) IS NULL OR kb.vendor_ids && ARRAY[1]::int[]
--   條件 2（is_active）   kb.is_active = TRUE
--   條件 3/6（保留分類）  kb.category IS DISTINCT FROM '系統脈絡' AND kb.category IS DISTINCT FROM '對話規則'
--   條件 6b（業態，b2c）  kb.business_types IS NULL OR kb.business_types && <vendor 1 的 business_types>
--                          （子查詢 `SELECT business_types FROM vendors WHERE id = 1`；
--                           業者 1 的實際業態值來源＝該子查詢本身，不在此檔寫死陣列字面）
--   條件 4（target_user） kb.target_user IS NULL OR kb.target_user && ARRAY['prospect','all_users']::text[]
--                          （'all_users' 是 b2c 分支追加的通用標記，見 build_visibility_predicate 條件 4 註解）
--
-- ⛔ 不落 `IS NULL` 到業態以外的任何 b2b 專屬分支——prospect 恆為 b2c 分支，本檔不含 b2b 條件。
--
-- 預期影響：31 列（design.md 元件 5 DSP-012 段；里程碑 M1 done 條件同數）。
-- 若預覽結果 ≠ 31：⛔ 不得逕行執行 UPDATE，回報實際數字與下方預覽 SQL 輸出，交回裁決
--   （售前池組成可能已變動，或 vendor 1 業態/資料已不同於立案當時）。
-- =====================================================

-- Step 0：先查 vendor 1 的 business_types，供人工核對（非查證步驟必經，僅供對照）
-- SELECT business_types FROM vendors WHERE id = 1;

-- Step 1：預覽——只 SELECT count(*)，不動資料
SELECT count(*) AS matched
FROM knowledge_base kb
WHERE (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && ARRAY[1]::int[])
  AND kb.is_active = TRUE
  AND kb.category IS DISTINCT FROM '系統脈絡'
  AND kb.category IS DISTINCT FROM '對話規則'
  AND (
        kb.business_types IS NULL
        OR kb.business_types && (SELECT business_types FROM vendors WHERE id = 1)
      )
  AND (kb.target_user IS NULL OR kb.target_user && ARRAY['prospect', 'all_users']::text[]);
-- 預期：31

-- Step 2：確認 Step 1 印出 31 後才執行本段（只標記尚未標記過的列，冪等）
UPDATE knowledge_base kb
SET outline_approved_by = 'owner-20260905',
    outline_approved_at = now()
WHERE (array_length(kb.vendor_ids, 1) IS NULL OR kb.vendor_ids && ARRAY[1]::int[])
  AND kb.is_active = TRUE
  AND kb.category IS DISTINCT FROM '系統脈絡'
  AND kb.category IS DISTINCT FROM '對話規則'
  AND (
        kb.business_types IS NULL
        OR kb.business_types && (SELECT business_types FROM vendors WHERE id = 1)
      )
  AND (kb.target_user IS NULL OR kb.target_user && ARRAY['prospect', 'all_users']::text[])
  AND kb.outline_approved_by IS NULL;
-- 預期：UPDATE 31

-- Step 3：驗證
SELECT count(*) FROM knowledge_base WHERE outline_approved_by IS NOT NULL;
-- 預期：31

-- =====================================================
-- Rollback（只還原本次以此標記寫入的列；⛔ 不動其他審核來源可能寫入的列）
-- =====================================================
-- UPDATE knowledge_base
-- SET outline_approved_by = NULL, outline_approved_at = NULL
-- WHERE outline_approved_by = 'owner-20260905';
