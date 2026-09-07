# DSP 草案（待業主裁）：`agent.turn` 對 `property_manager` 受眾開放（demo 範圍）——2026-09-07

> 狀態：**已裁（業主 2026-09-07「裁 DSP，先改 S1a 做 S1b，用 pm 跑」）→ DSP-037 已落 `.claude/DECISIONS.md`**；S1a／S1b 派 security-executor；agentic-mcp design 元件 4／決策 15 回寫待 S1 收案一併做。以下保留裁決當時的草案原文。

## 決定（擬）

在 `AGENT_TURN_SPEC["stage"]` 加 `"property_manager": "M1"`（`services/agent/mcp_facade.py`），使 b2b 系統內用戶（LINE OA「JGB 房東管家」）可經 `/mcp` `agent.turn` 走 agent 回合；範圍限 **demo**（展示對話與 MCP 功能，非上線準確度）。tenant 缺鍵維持永不可見。

## 為什麼要裁（現況與設計的衝突）

- agentic-mcp-orchestration design 元件 4：「本 spec 對話對象只有 prospect（範圍聲明）；tenant／pm **缺鍵＝永不可見**」；`AGENT_TURN_SPEC["stage"] = {"prospect": "M1"}`（查證：`rg -n '"stage": \{"prospect": "M1"\}' rag-orchestrator/services/agent/mcp_facade.py`）。
- 同 design 元件 3：`jgb2.query.*` 五支對 pm 在 **M0** 已可見；pm／tenant 的 REST agent 入口由 `AGENT_AUDIENCES` 決定（M4／M5）。所以「pm 走 agent」在設計上是**里程碑問題**，不是安全邊界問題——安全邊界（授權由 jgb2 API 全權處理、本系統只管額度，DSP-011）不變。
- OA 使用者是系統內用戶，⛔ 不是 prospect（業主 2026-09-07 更正）；沒有這條，line-bot 呼叫 `agent.turn` 一律 `NO_MATCH`。

## 前置（缺一不得開）

1. **pm 正本**：`rag-orchestrator/canon/property_manager.md`（tasks 6.2，進行中）＋ **P3-b** `vendor_business_types` 由 `VendorParameterResolver` 解析（進行中）。沒有正本時 `_select_outline` 對 pm 會退到什麼——**待核**（`app.state.agent_outline` 只在 `identity.audience == "prospect"` 時注入，見 `routers/agent_entry.py`；`agent.turn` 路徑對 pm 的大綱注入需查 `mcp_facade._agent_turn`）。
2. `AGENT_TURN_ENABLED=true`（另見 security Plan；G1 啟動 raise 風險）。
3. `is_internal` key 的 `vendor_ids` 收斂到 demo 業者（G4：持 key 者改 `target_user` 可開 `jgb2.query.*` 五支個資工具——demo 語境下這是需求，但範圍必須靠 `vendor_ids` 收到單一業者）。

## 否決的替代方案

- (a) 讓 OA 用戶以 prospect 身分走 `agent.turn`：可立即跑，但受眾錯（售前正本對系統內用戶答非所問），業主 2026-09-07 否決。
- (b) OA 走 REST `/api/v1/message` 舊鏈面向（③④⑤）：demo 目標是「對話＋MCP」，舊鏈不經 MCP；且③④⑤已裁先不併。
- (c) 直接把 `AGENT_AUDIENCES` 開 pm（M4）：管的是 REST 入口，與 `/mcp` 互不管轄（security review E），對本 demo 無效。

## 回滾

還原 `AGENT_TURN_SPEC["stage"]` 為 `{"prospect": "M1"}`（單行 revert）；旗標 `AGENT_TURN_ENABLED=false` 即工具不註冊。

## 影響面（查證清單）

```bash
rg -n "AGENT_TURN_SPEC|\"stage\":" rag-orchestrator/services/agent/mcp_facade.py
rg -n "def specs_for|audience not in spec_stage" rag-orchestrator/services/agent/tools/registry.py
rg -n "agent_outline|identity.audience == \"prospect\"" rag-orchestrator/routers/agent_entry.py rag-orchestrator/services/agent/mcp_facade.py
rg -n "AGENT_OUTLINE_TOKEN_LIMIT_PM" rag-orchestrator/ docker-compose.prod.yml
```
