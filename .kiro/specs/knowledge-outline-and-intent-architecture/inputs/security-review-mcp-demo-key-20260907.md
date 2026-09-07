# security-reviewer 唯讀審查——LINE OA demo 的 `/mcp` key 與 `AGENT_TURN_ENABLED`（2026-09-07）

> 用途：主 session 寫「demo 開關與憑證」Plan 的證據；⛔ 本檔不含任何金鑰值。審查者只用 Read／Glob／Grep，未執行指令。受眾更正：demo 對話受眾為 `property_manager`（b2b），⛔ 不是 prospect——G4 的「越權」在 demo 語境下反而是需求（agent.turn 的 stage 要開 pm），Plan 需改讀。

## 決定 Plan 形狀的六個事實

1. **G1 P1**：`app.py:_init_agent_runtime` 的 except 分支 `if _agent_configured(): raise RuntimeError`——`AGENT_TURN_ENABLED` 一開，agent 組裝失敗（正本取不到已審核列、token 超限、Verifier 自證失敗）從 fail-soft 升級為**啟動即 raise，舊鏈 `/api/v1/message` 一併掛**。⇒ 先在本機以同組 env 起一次成功再動任何共用環境；Plan 內含 runbook §19-7 回切。
2. **G2 P2**：兩條會把 `/api/v1/agent/health` 打紅——`RAG_API_AUTH_ENFORCE` 為 false 卻有 `/mcp` 流量（`mcp_facade.note_mcp_traffic` → `enforce_off_with_mcp_traffic`）；開旗標後 prospect `FineIndex` 非 `ready`（`health.py:agent_index_red`）。prod 現值未讀（邊界）。
3. **stage 閘**：`AGENT_TURN_SPEC["stage"] = {"prospect": "M1"}`、`tools/registry.py:specs_for` 缺鍵永不可見 ⇒ **pm 受眾要用 `agent.turn` 必須改 stage 對照表**（設計變更，需 DSP）；`jgb2.query.*` 五支個資工具對 pm 在 M0 已可見（`_jgb2_spec`）。
4. **發 key 的唯一正規路徑是 runbook §19-2 的手工 SQL**（`secrets.token_urlsafe(32)`、`rgk_` 前綴、INSERT 七欄含 `is_internal=TRUE`、`vendor_ids`）；後台 UI `POST /api/api-keys` 的 INSERT **不含 `is_internal`／`vendor_ids`** ⇒ 用它發的 key 第一筆呼叫就踩 DSP-011 第一旗。`verify_api_key` 無快取，停用即時生效；無 `expires_at`、無 scope 欄。
5. **G5 P2**：`is_internal=TRUE` ⇒ `usage_metering.quota_check` 回 `none`，額度歸零；唯一節流是 `AGENT_TURN_CAP`（行程內記憶體，多 worker ×N）。demo 期間要明說取捨。
6. **G7 P3**：`session_id` 裸值落 `usage_events.session_id`（18 個月）與 `form_sessions` ⇒ LINE userId 進來前上游先做穩定假名（HMAC）。

## 其餘

- G3 P2 demo key 可打 REST（無 scope 欄；⛔ 不建授權層，DSP-011 REJECT）——靠 `vendor_ids` 收斂＋監控。
- G6 P2 缺 Origin 一律放行是刻意（server-to-server）；`/mcp` 是否對公網開屬部署層，本 repo 查無 line-bot 入口。
- G8 P3 runbook §19-2 自檢 `curl -H "X-API-Key: $KEY"` 明文進 argv，Plan 逐條指令要改寫（既定紀律）。
- G9 P3 文件反證：runbook §19-2 預期 `/api/v1/agent/health` 不帶身分 header 回 200，但 `GATED_PREFIXES` 含 `/api/v1/agent` 且 `resolve_call` 含 `parse_identity` ⇒ 應 400；`m0-owner-steps.md` 自檢有帶 header。⛔ 未選邊，交裁決。
- 事實缺口：`api_keys` 建表 migration 檔（`create_api_keys_table.sql`）在 `rag-orchestrator/database/migrations/` 查無（正對照：`20260904_api_keys_agent_scope.sql` 在）。
- `make audit` 不變量 28／31 為靜態檢查，發 key＋開旗標不致紅。
- 建議 `.env` 鍵名用 compose 未引用的名字（如 `LINE_BOT_MCP_API_KEY`）；這把 key 其實只需存在 line-bot-platform 側。

## 查證指令（節錄，⛔ 不寫行號）

```bash
rg -n "def hash_key|_BASE_SELECT|_normalize_key_row" rag-orchestrator/services/api_key_auth.py
rg -n "INSERT INTO api_keys" knowledge-admin/backend/app.py docs/deployment-runbook.md .kiro/specs/agentic-mcp-orchestration/m0-owner-steps.md
rg -n "GATED_PREFIXES|async def resolve_call|def check_origin|def agent_turn_enabled|AGENT_TURN_SPEC|def note_mcp_traffic|enforce_off_with_mcp_traffic" rag-orchestrator/services/agent/mcp_facade.py
rg -n "def specs_for|audience not in spec_stage|facade_only" rag-orchestrator/services/agent/tools/registry.py
rg -n "_agent_configured\(\)|raise RuntimeError" rag-orchestrator/app.py
rg -n "agent_index_red|def _premise_flags" rag-orchestrator/services/agent/health.py
rg -n "if is_internal or not vendor_id" rag-orchestrator/services/usage_metering.py
```
