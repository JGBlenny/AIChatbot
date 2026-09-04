# M0 要業主動手的步驟（本機，逐條指令＋預期輸出；⛔ 不打包腳本、⛔ 線上不適用）

> 2026-09-04。全部在 `~/jgb/AIChatbot` 執行。金鑰只在你的 shell 變數裡，⛔ 不貼進對話。

## 1. 套 migration（help_center_pages、api_keys 兩欄）

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
