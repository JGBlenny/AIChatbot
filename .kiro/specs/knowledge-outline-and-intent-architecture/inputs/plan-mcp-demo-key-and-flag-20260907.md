# Plan：LINE OA demo 的 `/mcp` 開關與憑證（security-sensitive）——2026-09-07 草案，待 plan-verifier 與業主核

> 依據：`inputs/security-review-mcp-demo-key-20260907.md`（security-reviewer 唯讀審查）、`inputs/dsp-draft-agent-turn-stage-pm-20260907.md`（stage 開 pm，待裁）、`inputs/mcp-client-contract-line-bot-20260907.md`。執行路由：`security-executor`（程式與 SQL 稿）＋業主親跑（發 key、改 `.env`、重建容器）。⛔ 本 Plan 不含任何金鑰值；⛔ 不 push、不動線上。

## 0. 目標與非目標

- **目標**：line-bot-platform 後端能以一把 `is_internal` key 打 `POST /mcp` 的 `agent.turn`，受眾 `property_manager`，在**本機 dev（`docker-compose.prod.yml` 五服務）**跑通一回合並留下 `usage_events` 一列、`/api/v1/agent/health` 可解釋。
- **非目標**：上線；額度控制；③④⑤ LIFF 線；`RAG_API_AUTH_ENFORCE` 全面開啟的回歸（另案）。

## 1. 切片（各自可核、可回滾）

### S1 stage 開 pm（程式，1 行＋測試）
- 改 `mcp_facade.AGENT_TURN_SPEC["stage"]` 加 `"property_manager": "M1"`。
- 測試：`tests/unit/agent/` 加一案——pm 身分 `specs_for(for_model=False)` 含 `agent.turn`、tenant 不含、prospect 不變；既有 `test_mcp_facade_req` 全綠。
- 前置：DSP 裁定；6.2 正本＋P3-b 收（否則 pm 回合沒大綱可組——**待核** `_agent_turn` 對 pm 的大綱來源）。
- 回滾：revert 該行。

### S2 啟動安全：`AGENT_TURN_ENABLED` 的 G1 演練（不改程式）
- 在本機以 `.env` 加 `AGENT_TURN_ENABLED=true`（＋常駐 `AGENT_MODEL=gpt-5-mini`、`AGENT_REASONING_EFFORT=low`、`AGENT_BUDGET_REWRITES=0`）重建 rag-orchestrator，**先證明啟動不 raise**（`docker logs` 無 `RuntimeError`、`/api/v1/agent/health` 回應可讀）。
- 驗收：容器 `Up`；`docker exec … python3 -c "from services.agent.mcp_facade import agent_turn_enabled; print(agent_turn_enabled())"` 印 `True`；`tools/list`（帶 key＋pm 身分）含 `agent.turn`。
- 若 raise ⇒ 停下回主 session（fail-soft 升級為 raise 是設計，⛔ 不改 `app.py`）。
- 回滾：`.env` 去掉旗標、重建。

### S3 發 key（業主親跑，逐條指令＋預期輸出）
- 走 `docs/deployment-runbook.md` §19-2 的手工 SQL 版（唯一能設 `is_internal=TRUE` 的路徑；後台 UI ⛔ 不用）：`secrets.token_urlsafe(32)`、`rgk_` 前綴、`sha256` 入 `key_hash`、`key_prefix`、`is_internal=TRUE`、**`vendor_ids=ARRAY[<demo vendor_id>]`（⛔ 不留 NULL）**。
- 明文只出現在產生它的 shell 與 line-bot 側；AIChatbot 這側不保存；`.env` 若要放，用 compose 未引用的鍵名（如 `LINE_BOT_MCP_API_KEY`），⛔ 不複用 `RAG_ADMIN_API_KEY`。
- 自檢 ⛔ 不用 `curl -H "X-API-Key: $KEY"`（明文進 argv）；改 `curl -H @<header 檔>` 或容器內讀 env。
- 撤銷：`UPDATE api_keys SET is_active=false WHERE key_prefix=…`（即時生效，`verify_api_key` 無快取）。

### S4 健檢與計量對帳（驗收）
- 打一回合後：`usage_events` 新一列 `processing_path='mcp:agent.turn'`、`channel='mcp'`；`/api/v1/agent/health` 的 `premise` 四旗：`mcp_calls_flagged_by_api_key` 空（key 是 internal）、`enforce_off_with_mcp_traffic` **預期會紅**（除非本機 `RAG_API_AUTH_ENFORCE=true`）——demo 期間接受或先開 enforce，**業主裁**。
- `make audit` 不變量 28／31 為靜態檢查，預期不變。

## 2. 風險處置（對 security review G1–G9）

| # | P | 處置 | 落在 |
|---|---|---|---|
| G1 啟動 raise | P1 | **FIX**：S2 先在本機演練；Plan 內含回切 | S2 |
| G2 health 轉紅 | P2 | **業主裁**：demo 接受紅／或本機開 `RAG_API_AUTH_ENFORCE=true`（需回歸 REST 呼叫方是否都帶 key） | S4 |
| G3 key 可打 REST | P2 | **DEFER**（DSP-011 已 REJECT 授權層）；`vendor_ids` 收斂＋監控 | S3 |
| G4 header 改受眾 | P2 | **改讀為需求**：pm 是目標受眾；`vendor_ids` 單業者 | S1／S3 |
| G5 額度歸零 | P2 | **DEFER 並明說**：demo 唯一節流 `AGENT_TURN_CAP`（行程內，多 worker ×N）；可調低 | S4 |
| G6 公網暴露 | P2 | **業主部署層確認** `/mcp` 不對公網 | 部署 |
| G7 session_id 裸值 | P3 | **FIX（line-bot 側）**：HMAC 假名——已寫進接入契約 §4 | 契約 |
| G8 argv 明文 | P3 | **FIX**：S3 指令改寫 | S3 |
| G9 runbook 自檢矛盾 | P3 | **交裁決**：實作（`GATED_PREFIXES` 含 `/api/v1/agent` ⇒ 缺身分 header 400）vs runbook §19-2（預期 200）；裁後修文件 | 文件 |

## 3. 驗收（primary user-visible）

line-bot 側（或本機以 header 檔模擬）對 `/mcp` `tools/call agent.turn {"message": "<pm 正本涵蓋的一句>"}` 回 `ok=true`、`answer` 非空、`trace_id` 可在 `/api/v1/agent/trace/{id}` 查到、`usage_events` 多一列。派 fresh `verifier` 對此 claim 實跑。

## 4. 停下條件

S2 啟動 raise；S3 後 `mcp_calls_flagged_by_api_key` 非空（代表 key 不是 internal）；S1 後 prospect 既有測試任何一案變紅。
