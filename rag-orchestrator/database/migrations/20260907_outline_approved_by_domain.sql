-- =====================================================
-- knowledge-outline-and-intent-architecture 任務 3.1：outline_approved_by 值域 CHECK
--   （design 元件 5／決策 8／不變量 32；Plan inputs/plan-3.1-review-state-20260907.md §3）
--
-- 背景：`20260905_knowledge_base_outline_approval.sql` 只加了欄位，值域是**任意 text**。
--   於是「誰核可的」可以是空字串、可以是任何舊標記——審核紀錄形同無約束。
--   業主 2026-09-07 裁 (a)（收嚴並回寫 design）：值域只有兩種值加 NULL。
--
-- 值域（唯一定義在 `services/agent/canon/review_state.py:DOMAIN_REGEX`，
--   本檔的 regex 字串**逐位元組**等於該常數，由
--   `tests/unit/agent/test_review_state_req.py` 比對，drift 必紅）：
--     ・`reviewed:<who>`         內容已審（who 非空、不含空白）→ agent 路徑**可見**
--     ・`pool-marked-<YYYYMMDD>` 池標記                        → agent 路徑**不可見**
--     ・NULL                     未標記                        → 不可見
--   ⚠️ 可見 ⊂ 允許：池標記通過 CHECK 但**不是**內容已審（design 元件 5）。
--
-- ⚠️ 為什麼是 `NOT VALID`：現況 29 列的值是 `owner-20260905`（值域外，
--   實查 2026-09-07：NULL 1,019、owner-20260905 29、其他 0）。不加 `NOT VALID`
--   的 `ADD CONSTRAINT` 會驗既有列 ⇒ 整個 ALTER 中止。`NOT VALID` 讓約束
--   **即刻對新寫入生效**、既有列暫不驗。
--
-- 冪等：`DO $$` 先查 `pg_constraint`，已存在即跳過。重跑無副作用。
-- 執行：由業主以 database/migrate.sh --apply 執行；⛔ 本任務只寫檔不跑、
--   不對 aichatbot_admin 執行任何 SQL。
-- 回滾：database/migrations/rollback/20260907_outline_approved_by_domain_rollback.sql
-- =====================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'chk_outline_approved_by_domain'
           AND conrelid = 'knowledge_base'::regclass
    ) THEN
        ALTER TABLE knowledge_base
            ADD CONSTRAINT chk_outline_approved_by_domain
            CHECK (outline_approved_by IS NULL
                   OR outline_approved_by ~ '^(reviewed:[^[:space:]]+|pool-marked-[0-9]{8})$')
            NOT VALID;
        RAISE NOTICE '✅ 已加上 chk_outline_approved_by_domain（NOT VALID）';
    ELSE
        RAISE NOTICE 'ⓘ chk_outline_approved_by_domain 已存在，跳過（冪等）';
    END IF;
END $$;

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n
      FROM pg_constraint
     WHERE conname = 'chk_outline_approved_by_domain'
       AND conrelid = 'knowledge_base'::regclass;
    IF n <> 1 THEN
        RAISE EXCEPTION 'chk_outline_approved_by_domain 未就緒（實際 % 筆）——大聲失敗', n;
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────
-- D1 後置步驟（⛔ 本檔執行時**不要**跑這一段；由業主在改寫 29 列之後另跑）
--
-- 順序（⛔ 不可對調）：
--   ① 先把 29 列 `owner-20260905` 改寫進值域：
--        UPDATE knowledge_base
--           SET outline_approved_by = 'pool-marked-20260905'
--         WHERE outline_approved_by = 'owner-20260905';
--      ⚠️ 這是「池標記」不是「內容已審」——改完那 29 列在 agent 路徑**仍然不可見**，
--         這是預期（要到正本細目匯入寫進 `reviewed:<who>` 才進場）。
--      ⚠️ 任何 knowledge_base 的 UPDATE 都會撞 updated_at trigger ⇒ 不變量 10 連鎖，
--         執行前後各跑一次 `make audit` 並在 runbook 標明預期反應。
--   ② 再驗既有列（此時應無違規列，命令才不會失敗）：
--        ALTER TABLE knowledge_base VALIDATE CONSTRAINT chk_outline_approved_by_domain;
--   ③ 之後不變量 32 的 DB 子檢查會從 `SKIP(pending-D1)` 轉成實跑
--      （scripts/audit/checks/agent_boundary.py:check_32_review_state_single_source）。
-- ─────────────────────────────────────────────────────────────────────────
