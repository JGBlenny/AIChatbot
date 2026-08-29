-- Stage 1｜nomination funnel 的**凍結量測定義**（measurement contract，非一次性分析）
--
-- 規格：.kiro/specs/conversational-routing-execution/stage1-nomination-observability-spec.md
--
-- ⚠️ Claim ceiling（每次引用結果都適用）：
--   ✅ 可說：「production classification 請求中，N% 沒有產生 Face nomination」
--   ⛔ 不得說：「漏掉 N%」「category recall」「missing coverage」「漏接率」
--      ——那些需要 Layer 0 capability truth，而 Stage 1 沒有收使用者原文。
--
-- ⚠️ 母體一律鎖在 entry_source='classification'。
--   `sop_arbitration`／`existing_session`／`explicit_trigger`／`vision_redirect`／
--   `prospect_free_qa`／`transaction_form` **不得**進 denominator——混入會污染 S3。

-- ════════════════════════════════════════════════════════════════════
-- Q1｜S1–S5 funnel ＋ instrumentation sentinel
-- ════════════════════════════════════════════════════════════════════
--
-- ⚠️ S4／S5 **不得**用 `facet_key IS NULL` 判——technical fail-open／delegation／
--    compatibility path 已證明 facet_key 不能代表 authority（裁定 001 ④、001-A）。
--    一律讀 resolver.has_commit_authority。
-- ⚠️ ⛔ 不得用 COALESCE(..., '[]') 把缺 key 的列吃掉：那正是 sentinel 要抓的東西。

WITH classification AS (
    SELECT request_id, ts,
           decision_snapshot->'nomination' AS nom,
           decision_snapshot->'resolver'   AS res
    FROM usage_events
    WHERE decision_snapshot->'nomination'->>'entry_source' = 'classification'
      AND is_internal = FALSE
)
SELECT
    CASE
        -- telemetry regression sentinel：理論上新資料不該出現
        WHEN NOT (nom ? 'top1_knowledge_id')
          OR NOT (nom ? 'top1_categories')
          OR NOT (nom ? 'nomination_candidate_facet_keys')
          OR jsonb_typeof(nom->'nomination_candidate_facet_keys') NOT IN ('array')
            THEN 'INSTRUMENTATION_UNKNOWN'
        WHEN nom->>'top1_knowledge_id' IS NULL                    THEN 'S1_no_top1'
        WHEN nom->'top1_categories' = '[]'::jsonb                 THEN 'S2_top1_no_categories'
        WHEN nom->'nomination_candidate_facet_keys' = '[]'::jsonb THEN 'S3_categories_no_nomination'
        WHEN COALESCE((res->>'has_commit_authority')::boolean, FALSE) IS FALSE
            THEN 'S4_nomination_no_authoritative_commit'
        ELSE 'S5_authoritative_commit'
    END AS stage,
    count(*) AS requests,
    round(100.0 * count(*) / NULLIF(sum(count(*)) OVER (), 0), 1) AS pct
FROM classification
GROUP BY 1
ORDER BY 1;

-- ════════════════════════════════════════════════════════════════════
-- Q2｜top1 category → nomination
-- ════════════════════════════════════════════════════════════════════
--
-- ⚠️ 分析單位是 (request_id, category)：多 category 的請求 explode 後計算。
--   ⛔ 不得把 explode 後的列數當成 request 總數再宣稱 rate。
-- ⚠️ Claim ceiling：本表只說「某 category 出現在 top1 時，有多少次沒產生 nomination」。

WITH classification AS (
    SELECT request_id, decision_snapshot->'nomination' AS nom
    FROM usage_events
    WHERE decision_snapshot->'nomination'->>'entry_source' = 'classification'
      AND is_internal = FALSE
      AND jsonb_typeof(decision_snapshot->'nomination'->'top1_categories') = 'array'
), exploded AS (
    SELECT c.request_id,
           cat.value #>> '{}' AS category,
           (c.nom->'nomination_candidate_facet_keys' = '[]'::jsonb) AS candidate_zero
    FROM classification c,
         LATERAL jsonb_array_elements(c.nom->'top1_categories') AS cat
)
SELECT category,
       count(DISTINCT request_id)                             AS requests_with_category,
       count(*) FILTER (WHERE candidate_zero)                 AS candidate_zero,
       count(*) FILTER (WHERE NOT candidate_zero)             AS candidate_nonzero,
       round(100.0 * count(*) FILTER (WHERE candidate_zero) / NULLIF(count(*), 0), 1)
                                                              AS candidate_zero_rate
FROM exploded
GROUP BY 1
ORDER BY candidate_zero DESC, requests_with_category DESC;

-- ════════════════════════════════════════════════════════════════════
-- Q3｜nomination candidate → resolver outcome
-- ════════════════════════════════════════════════════════════════════
--
-- ⚠️ **最大的坑**：`nomination_candidate_facet_keys` 是**完整候選清單**，
--   不代表每個 candidate 都真的被 resolver 執行——first-commit-wins 之下
--   `[A,B,C]` 若 A 就 commit，B／C **根本沒進 resolver**。
--   ⛔ 因此不得把 B 記成「被 resolver 拒絕」。
--   本表以 hops 還原 invocation，分成三態：
--     resolver_invoked｜not_reached_due_to_prior_commit
--   （Stage 1 剛把 nomination 與 execution 拆開，分析 SQL 不得再把它們混回去。）
-- ⚠️ hops 內也含**被委派**的面向（非提名者）——那些不是本表的分析單位。

WITH classification AS (
    SELECT request_id,
           decision_snapshot->'nomination' AS nom,
           decision_snapshot->'resolver'   AS res
    FROM usage_events
    WHERE decision_snapshot->'nomination'->>'entry_source' = 'classification'
      AND is_internal = FALSE
      AND jsonb_typeof(decision_snapshot->'nomination'->'nomination_candidate_facet_keys') = 'array'
), nominated AS (
    SELECT c.request_id, c.res,
           k.value #>> '{}' AS candidate_facet
    FROM classification c,
         LATERAL jsonb_array_elements(c.nom->'nomination_candidate_facet_keys') AS k
), joined AS (
    SELECT n.candidate_facet,
           h.value->>'decision_source' AS decision_source,
           h.value->>'scope'           AS scope,
           (h.value IS NOT NULL)       AS resolver_invoked
    FROM nominated n
    LEFT JOIN LATERAL (
        SELECT hop.value
        FROM jsonb_array_elements(COALESCE(n.res->'hops', '[]'::jsonb)) AS hop
        WHERE hop.value->>'candidate_facet' = n.candidate_facet
        LIMIT 1
    ) h ON TRUE
)
SELECT candidate_facet,
       count(*)                                                          AS nominated,
       count(*) FILTER (WHERE resolver_invoked)                          AS resolver_invoked,
       count(*) FILTER (WHERE NOT resolver_invoked)                      AS not_reached_due_to_prior_commit,
       count(*) FILTER (WHERE decision_source = 'model' AND scope = 'stay')   AS model_stay,
       count(*) FILTER (WHERE decision_source = 'model' AND scope = 'switch') AS model_switch,
       count(*) FILTER (WHERE decision_source = 'technical_fail_open')    AS technical_fail_open,
       count(*) FILTER (WHERE decision_source = 'contract_salvage')       AS contract_salvage,
       count(*) FILTER (WHERE decision_source = 'guard')                  AS guard
FROM joined
GROUP BY 1
ORDER BY nominated DESC;

-- ════════════════════════════════════════════════════════════════════
-- Q4｜telemetry invariant sanity（**這張紅了就先修 instrumentation，不得解讀 funnel**）
-- ════════════════════════════════════════════════════════════════════

WITH n AS (
    SELECT request_id,
           decision_snapshot->'nomination' AS nom,
           decision_snapshot->'nomination'->>'entry_source' AS src
    FROM usage_events
    WHERE decision_snapshot ? 'nomination' AND is_internal = FALSE
)
SELECT 'classification 必須有三個 key' AS invariant,
       count(*) FILTER (WHERE src = 'classification'
                          AND NOT (nom ? 'top1_knowledge_id'
                                   AND nom ? 'top1_categories'
                                   AND nom ? 'nomination_candidate_facet_keys')) AS violations
FROM n
UNION ALL
SELECT '非 classification 的 candidate 欄位須為 null',
       count(*) FILTER (WHERE src <> 'classification'
                          AND jsonb_typeof(nom->'nomination_candidate_facet_keys') <> 'null')
FROM n
UNION ALL
SELECT 'top1 為 null 時 categories 須為 []',
       count(*) FILTER (WHERE src = 'classification'
                          AND nom->>'top1_knowledge_id' IS NULL
                          AND nom->'top1_categories' <> '[]'::jsonb)
FROM n
UNION ALL
SELECT 'candidate 欄位型別須為 array 或 null',
       count(*) FILTER (WHERE jsonb_typeof(nom->'nomination_candidate_facet_keys')
                              NOT IN ('array', 'null'))
FROM n;
