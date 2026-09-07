# 給 line-bot-platform：LINE OA 對話經 `/mcp` `agent.turn` 的接入契約（草案 v0，2026-09-07）

> 用途：demo（展示對話與 MCP 功能，非上線準確度）。受眾 `property_manager`（b2b，系統內代管業務／房東）。本檔只寫 AIChatbot 側**現行程式**的契約與**尚未就緒**的前置；⛔ 不含任何金鑰值。每條附可 grep 的符號；標「待核」者表示程式尚未支援或形狀未定，⛔ 呼叫端不要先寫死。

## 0. 一句話

伺服器對伺服器，MCP streamable HTTP 掛在 `POST /mcp`（`app.py` `Mount("/mcp", …)`），呼叫工具 `agent.turn`，輸入只有一個 `message`，對話歷史由 AIChatbot 依 `session_id` 保存；身分用 header `X-JGB-Identity` 帶、金鑰用 `X-API-Key`。瀏覽器／LIFF **不走這條**（它們走 REST `/rag-api/v1/message`）。

## 1. 傳輸與工具

| 項 | 值 | 證據 |
|---|---|---|
| 端點 | `POST /mcp`（MCP SDK `MCPServer("jgb-tools")`，streamable HTTP；方法名依 SDK：`tools/list`、`tools/call`） | `mcp_facade.py` `build_asgi_app`、`MCPServer(` |
| 工具名 | `agent.turn` | `mcp_facade.py` `AGENT_TURN_NAME`、`AGENT_TURN_SPEC` |
| 輸入 | `{"message": "<1–2000 字>"}`，⛔ 沒有 `dialog_ref`（刻意移除） | `AGENT_TURN_SPEC["input_schema"]` |
| 輸出（`ok=true`） | `{"answer": str, "kind": str, "handoff": dict\|null, "quick_replies": list, "trace_id": str}` | `class AgentTurnOutput` |
| `kind` 值域 | 依 runtime 輸出契約（`answer`／`ask`／`handoff`…）；**待核**：demo 前以 `trace_id` 對 `/api/v1/agent/trace/{id}` 抽樣確認 | `services/agent/output_contract.py` |
| `quick_replies[]` 形狀 | **待核**（runtime 現行輸出；請以實跑一次的回應為準，⛔ 不先寫死欄位名） | `output_contract.py` `quick_replies` |
| `handoff` | 轉人時非空，含 `handoff_reason`（如 `sensitive_no_grounding`、`budget_exhausted`、`no_grounding`）；呼叫端只要「非 null ⇒ 顯示固定轉人句＋提供真人入口」 | `output_contract.py` `handoff_reason` |
| 逾時 | 服務端 `AGENT_TURN_TIMEOUT_S`（預設 30 s），逾時回工具錯 `TOOL_TIMEOUT`；呼叫端逾時請 ≥35 s，逾時後**同一 `session_id` 可重送** | `mcp_facade.py` `agent_turn_timeout_s` |
| 每小時上限 | `AGENT_TURN_CAP`（預設 120／(api_key_id, vendor_id)，行程內計數）⇒ 超過回 `RATE_LIMITED` | `mcp_facade.py` `check_and_record_agent_turn` |

## 2. 請求 header

```jsonc
X-API-Key: <由 AIChatbot 側以 runbook §19-2 手工 SQL 發的 is_internal key；只存 line-bot 側>
Origin: （伺服器對伺服器**不要送**；送了必須在 MCP_ALLOWED_ORIGINS 內，否則 403）
X-JGB-Identity: {
  "mode": "b2b",
  "target_user": "property_manager",   // 一律明送
  "vendor_id": <int>,                  // 必填；必須存在於 vendors 表且在 key 的 vendor_ids 內（403 否則）
  "role_id": "<業務的 JGB role>",      // 選填字串；demo 固定 20151
  "user_id": "<業務的 users.id>",      // 選填字串；demo 固定 12291
  "session_id": "<穩定假名>"           // 必填；⛔ 不要直接放 LINE userId（見 §4 G7）；服務端會加前綴 mcp:{api_key_id}:{vendor_id}:，總長 ≤100
}
```

證據：`mcp_facade.py` `parse_identity`（`IDENTITY_MALFORMED`／`IDENTITY_MISSING_VENDOR_ID`／`IDENTITY_MISSING_SESSION_ID`）、`namespaced_identity`、`check_origin`。

## 3. 錯誤對照（呼叫端只看碼）

| 狀態／碼 | 何時 | 呼叫端呈現 |
|---|---|---|
| 401 `API_KEY_REQUIRED` | 缺／錯 key（無條件，不看 `RAG_API_AUTH_ENFORCE`） | 「對話服務暫時無法使用」＋error log |
| 403 `ORIGIN_NOT_ALLOWED`／`VENDOR_UNKNOWN`／`VENDOR_NOT_IN_KEY_SCOPE` | Origin 不在白名單／vendor 不存在／不在 key 範圍 | 同上（設定錯，不是使用者錯） |
| 400 `IDENTITY_*` | header JSON 壞／缺 vendor_id／缺 session_id | 同上 |
| 429 `QUOTA_EXCEEDED`；`METERING_UNAVAILABLE` | 額度（`is_internal` key 不計額度，實務上不會撞）；計量服務不可用 | 「稍後再試」 |
| 工具層 `ok=false`：`INVALID_INPUT`／`NO_MATCH`／`TOOL_TIMEOUT`／`AGENT_UNAVAILABLE`／`RATE_LIMITED` | message 空或超長／工具不可見（旗標或 stage 未開）／逾時／runtime 未建／每小時上限 | `NO_MATCH`＝AIChatbot 側前置未開（§4），不是呼叫端錯 |

## 4. AIChatbot 側尚未就緒的前置（呼叫端別等錯地方）

| # | 前置 | 現況 | 誰動 |
|---|---|---|---|
| 1 | `AGENT_TURN_ENABLED=true`（現 false ⇒ 工具根本不註冊 ⇒ `NO_MATCH`） | 未開；⚠️ 開了之後 agent 組裝失敗會讓整個服務啟動 raise（`app.py` `_init_agent_runtime`） | AIChatbot，security Plan 後 |
| 2 | `agent.turn` 的 `stage` 對照表加 `property_manager`（現只有 `{"prospect": "M1"}`，缺鍵永不可見） | 設計變更，需 DSP | AIChatbot，業主裁 |
| 3 | `property_manager` 正本 `rag-orchestrator/canon/property_manager-line.md`（tasks 6.2）＋P3-b 業態解析 | 6.2 進行中（步 2）；P3-b executor 進行中 | AIChatbot |
| 4 | `is_internal` key（runbook §19-2 手工 SQL；後台 UI 發的 key 缺 `is_internal` 會踩 DSP-011 紅旗） | 未發 | AIChatbot 業主親跑 |
| 5 | `RAG_API_AUTH_ENFORCE=true`（否則第一筆 `/mcp` 流量讓 `/api/v1/agent/health` 轉紅：`enforce_off_with_mcp_traffic`） | prod 現值未讀 | AIChatbot 部署 |
| 6 | `/mcp` 不對公網開（缺 Origin 一律放行是刻意的 server-to-server 設計；程式層無 IP 白名單） | 部署層，本 repo 查無 line-bot 入口 | 部署 |

G7（隱私）：`session_id` 裸值會落 `usage_events.session_id`（保存 18 個月）與 `form_sessions` ⇒ line-bot 側用 `HMAC(secret, lineUserId)` 之類的穩定假名當 `session_id`，⛔ 不要直接帶 LINE userId。

## 5. line-bot 側要做的（最小）

1. webhook 收到文字 → 依綁定推出 `role_id`／`user_id`／`vendor_id`（⛔ 不接受前端帶進來的值，與既有 §5 規則同）→ 組 `X-JGB-Identity` → `tools/call agent.turn {message}`。
2. `answer` 畫成泡泡；`quick_replies` 畫成按鈕（形狀待核，先以實跑回應為準）；`handoff` 非 null ⇒ 固定轉人句＋真人入口；`ok=false` 依 §3 對照。
3. 逾時 ≥35 s；`session_id` 一個 LINE 使用者一條（假名）；日誌 ⛔ 不記整包回應（`answer` 可能含個資）、只記 `trace_id`／狀態碼。
4. 第一次串接前先用 `tools/list` 確認 `agent.turn` 在清單裡（不在＝§4 的 1 或 2 未開）。

## 6. 查證指令

```bash
rg -n "AGENT_TURN_SPEC|class AgentTurnOutput|def parse_identity|def check_origin|def namespaced_identity|def agent_turn_timeout_s|check_and_record_agent_turn|^ERR_" rag-orchestrator/services/agent/mcp_facade.py
rg -n 'Mount\("/mcp"' rag-orchestrator/app.py
rg -n "def specs_for|audience not in spec_stage" rag-orchestrator/services/agent/tools/registry.py
```
