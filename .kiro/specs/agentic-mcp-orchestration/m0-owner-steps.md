# M0 要業主動手的步驟（本機，逐條指令＋預期輸出；⛔ 不打包腳本、⛔ 線上不適用）

> 2026-09-04。全部在 `~/jgb/AIChatbot` 執行。金鑰只在你的 shell 變數裡，⛔ 不貼進對話。

## 1. 套 migration（help_center_pages、api_keys 兩欄）— ✅ 2026-09-05 主 session 代跑（業主「幫我加」）：只套 agent 五支並記帳 `created_by='main-session-selective'`；⛔ 未跑其餘 9 支他線 migration 與 2 個 seed

```bash
bash rag-orchestrator/database/migrate.sh
```
預期（dry-run）：列出未套清單含 `20260904_create_help_center_pages.sql`、`20260904_api_keys_agent_scope.sql`，⛔ 不會真跑。

```bash
bash rag-orchestrator/database/migrate.sh --apply
```
預期：兩支各印一行套用成功並記帳；再跑一次 `bash rag-orchestrator/database/migrate.sh` 應顯示已套（冪等）。

驗證：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='api_keys' AND column_name IN ('is_internal','vendor_ids') ORDER BY 1;"
```
預期：兩行 `is_internal`、`vendor_ids`。
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c "SELECT count(*) FROM help_center_pages;"
```
預期：`0`（表存在、尚無資料，D3 裁後才匯入）。

## 2. 發一把內部 MCP key（給 Claude Code／回測工具用）

```bash
KEY=$(python3 -c "import secrets;print('rgk_'+secrets.token_urlsafe(32))")
HASH=$(python3 -c "import hashlib;print(hashlib.sha256('$KEY'.encode()).hexdigest())")
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "INSERT INTO api_keys (name, key_hash, key_prefix, description, is_active, is_internal, vendor_ids)
   VALUES ('mcp-internal-local', '$HASH', '${KEY:0:8}', 'M0 本機 MCP 內部呼叫者', TRUE, TRUE, NULL);"
echo "MCP_INTERNAL_API_KEY=$KEY" >> .env
```
預期：`INSERT 0 1`。`is_internal=TRUE` ⇒ `/mcp` 呼叫計量標內部、不扣額度；`vendor_ids NULL` ⇒ 不限業者。⛔ 不要把 `$KEY` 貼給我。

自檢（直打本機 rag；1.7b 重建 image 後才會有 `/api/v1/agent/health`）：
```bash
curl -s http://localhost:8100/api/v1/agent/health -H "X-API-Key: $KEY" \
  -H 'X-JGB-Identity: {"mode":"b2c","target_user":"tenant","vendor_id":1,"session_id":"backtest_session_m0_probe"}' | head -c 400; echo
```
預期：JSON `{"status": "ok" ...}`；`mcp_sdk` 欄在 1.7b 前為 `unavailable (DSP-014)`。缺 key 時應 `401`。

## 3. jgb2 端：確認本機 `JGB_API_KEY` 的 resource 讀權（在 jgb2 主機／checkout 執行）

```bash
cd ~/jgb/project/jgb/jgb2
php artisan external-api-key:run list
php artisan external-api-key:run permission-list --key-id=<本機 .env 那把 key 的 id>
```
預期：`bills`、`contracts`、`estates`、`meters`、`roles` 五個 resource 皆有 `read`。缺的：
```bash
php artisan external-api-key:run permission-add --key-id=<id> --resource=<缺的> --action=read
```
完成後告訴我「五個都有」，我再跑對測試團隊 role 20151 的真 API smoke（`RUN_INTEGRATION=1`，容器內讀 env，⛔ 金鑰不進 argv）。

## 4. 1.7b 回來後（我做）：重建本機 image、跑 M0 整合六案＋MCP client 端到端、派 1.9 security review。

## 5. 售前池審核旗標（M1 前置，任務 3.3，R11.6） — ✅ 2026-09-05 主 session 代跑：v2 b2b 謂詞預覽 31 → UPDATE 31 → 驗證 31（v1 b2c 謂詞預覽 81 已停並修正）

> 背景：DSP-012 裁決發現 `knowledge_base` 查無任何審核旗標，售前大綱組裝現況等於
> 「有 KB 寫入權＝有 system prompt 寫入權」。`build_prospect_outline`（3.2）SHALL
> 只取 `outline_approved_by IS NOT NULL` 的列，故上線前要先把現有售前池標記為已審核。

```bash
bash rag-orchestrator/database/migrate.sh --apply
```
預期：印出套用 `20260905_knowledge_base_outline_approval.sql` 成功並記帳；再跑一次
`bash rag-orchestrator/database/migrate.sh`（不帶 `--apply`）應顯示已套（冪等）。

驗證欄位就緒：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='knowledge_base' AND column_name IN ('outline_approved_by','outline_approved_at') ORDER BY 1;"
```
預期：兩行 `outline_approved_at`、`outline_approved_by`。

預覽要標記的列數（`.kiro/specs/agentic-mcp-orchestration/sql/mark-prospect-pool-approved-20260905.sql` Step 1）：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -tA -f \
  <(sed -n '/^SELECT count(\*) AS matched/,/^-- 預期：31$/p' .kiro/specs/agentic-mcp-orchestration/sql/mark-prospect-pool-approved-20260905.sql | sed '$d')
```
預期：`31`。⚠️ 若不是 31，⛔ 不要往下執行 UPDATE——回報實際數字，回到 SQL 檔核對
`build_visibility_predicate` 條件是否與售前池現況仍一致（售前池可能已變動）。

確認為 31 後，執行標記（Step 2）與驗證（Step 3）：
```bash
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  < .kiro/specs/agentic-mcp-orchestration/sql/mark-prospect-pool-approved-20260905.sql
```
預期：`UPDATE 31`，最後一段 `SELECT count(*) FROM knowledge_base WHERE outline_approved_by IS NOT NULL;` 印出 `31`。

Rollback（僅在標記錯誤時使用，還原本次以 `owner-20260905` 寫入的列）：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "UPDATE knowledge_base SET outline_approved_by = NULL, outline_approved_at = NULL WHERE outline_approved_by = 'owner-20260905';"
```


## 6.（事後補）不變量 10 連鎖 — ✅ 2026-09-05 業主「授權」：第 5 節的 UPDATE 觸發 `updated_at` trigger，17 列售前知識需補宣告 `instance_applicability=general`（DSP-019），已執行並登記 exclusions；`make audit` PASS。線上部署照做（runbook §19-4 需補此步）。
