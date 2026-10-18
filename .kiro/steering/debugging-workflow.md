# 除錯與問題解決工作流程

## 核心原則：先盤查，後行動

**絕對禁止猜測和推論。** 每個問題都必須透過盤查現有代碼來找到解決方案。

## 標準除錯流程

### 1. 問題發生時的第一步：盤查現有實現

當遇到任何問題（API 錯誤、顯示問題、功能不work等），**強制執行以下檢查順序**：

```
1. 找出「正常工作」的類似功能
2. 檢查該功能的完整實現
3. 對比問題代碼與正常代碼的差異
4. 照抄正確的模式
```

### 2. 前端問題的盤查清單

遇到前端問題時，**按順序**檢查：

- [ ] **檢查 `src/config/api.js`** - 是否有統一的 API 配置？
- [ ] **找出類似頁面** - 哪個頁面有相同功能且正常工作？
- [ ] **檢查該頁面的實現** - 它怎麼調用 API？怎麼處理數據？
- [ ] **檢查構建方式** - `docker-compose.dev.yml`／`docker-compose.prod.yml` 中前端是如何構建和部署的？
- [ ] **對比差異** - 問題代碼與正常代碼有什麼不同？

### 3. 後端問題的盤查清單

遇到後端問題時，**按順序**檢查：

- [ ] **檢查類似的 API 端點** - 找出功能相似且正常工作的端點
- [ ] **檢查路由定義** - 對比路由模式、參數、返回格式
- [ ] **檢查數據庫查詢** - 對比 SQL 語句、欄位名稱
- [ ] **檢查錯誤處理** - 對比 try-catch 結構、HTTPException 處理
- [ ] **檢查依賴調用** - 對比函數調用方式、參數傳遞

### 3b. 對話問題的盤查清單（「為什麼這樣回答／為什麼被轉人」）

⛔ **不要從意圖分類、SOP 觸發、表單狀態機、答案優化查起——這四個子系統
2026-09-11 已整批刪除**（DSP-046）。現行唯一活線是 `/mcp` → `AgentRuntime.run_turn`。
檢索門檻不是整個刪除：`services/decision_layer.py` 還在，其中 `DecisionConfig.kb_threshold`
（env `KB_SIMILARITY_THRESHOLD`）仍被 `services/agent/tools/kb.py` 讀取，是 `kb.search` 的現行門檻；
`form_trigger_threshold`／`knowledge_min` 等其餘欄位才是無消費者。

按順序：

- [ ] **先看 log 那一行**：`agent_turn trace_id=… kind=… handoff_reason=… tool_calls=… verifier_rejects=… llm_calls=…`
      （`services/agent/turn_context.py::_emit_agent_decision`）。它一行就把回合分類完了。
- [ ] **`handoff_reason` 決定往哪查**——轉人有**五個來源**，判讀法見
      `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` §4b 表 A：
      模型自報／`budget_exhausted`（Verifier 擋兩次）／範圍退出／程式降級／**工具查無或身分不足**。
- [ ] **最常見的是最後一個**：`jgb2.query.*` 回 `NO_MATCH` ⇒ 該筆 `status="error"`
      ⇒ 兩道降級閘都不接管 ⇒ 使用者看到轉人固定句而**不是** `NO_DATA_TEXT`。
      ⚠️ pm 查 `bills`／`contracts` 缺 `role_id` 也走這條（門面選填、下游必填）。
- [ ] **查線上組態**：`GET /api/v1/agent/health` 看 `verifier_mode`／`use_mock_jgb_api`／`limits`。
      ⛔ 不要拿文件表格當現行部署值——`AGENTIC_MCP_ARCHITECTURE.md` §6 自己說那不是。
- [ ] **看單一回合**：`GET /api/v1/agent/trace/{trace_id}`；或查 `usage_events.decision_snapshot`。
- [ ] **⛔ 不能動的東西**：`KB_SIMILARITY_THRESHOLD`（docstring 明寫不得改回 0.55）、
      `NON_SENSITIVE_HANDOFF_REASONS`（封閉白名單，測試釘死）、出口閘順序。
      清單見 `docs/architecture/SYSTEM_ARCHITECTURE.md`「⛔ 調鬆一點時不能動的東西」。

⚠️ **有日期的盤查報告是舊鏈的快照**（`presales-assistant-quality-audit-20260902.md`、
`retrieval-recall-audit-20260822.md` 等，都早於 2026-09-08 agentic-MCP 上線）——
它們的結論 ⛔ 不適用於現況診斷。

### 4. 禁止的行為

以下行為會浪費時間且無效，**絕對禁止**：

- ❌ 猜測可能的原因
- ❌ 憑空推論解決方案
- ❌ 未經盤查就修改配置（nginx, docker, etc）
- ❌ 在沒有參考範例的情況下寫新代碼
- ❌ 重複嘗試類似的失敗方案
- ❌ 說「應該」、「可能」、「也許」

### 5. 實際案例：API 調用問題

**錯誤做法（禁止）**：
1. 猜測是 nginx 重定向問題
2. 猜測是 FastAPI 路由問題
3. 猜測是斜線問題
4. 反覆嘗試不同的 URL 格式
5. 修改 nginx 配置

**正確做法（強制）**：
1. 找出正常工作的類似頁面（LoopManagementTab.vue）
2. 檢查它怎麼調用 API
3. 檢查是否有統一的 API 配置文件（src/config/api.js）
4. 照抄相同的模式
5. 完成

## 時間控制

如果在**同一個方向**嘗試超過 **15 分鐘**仍未解決：

1. **立即停止**當前方法
2. **強制執行盤查流程**
3. 找出正常工作的參考實現
4. 重新開始

## 用戶提示的處理

當用戶說：
- 「其他頁怎麼做的」
- 「你為什麼不看...」
- 「你一直在猜」
- 「其他服務沒問題」

**立即**執行盤查流程，找出正常工作的範例。

## 檢查表：開始任何修改前

在修改任何代碼之前，**必須回答**：

1. [ ] 我是否找到了正常工作的類似功能？
2. [ ] 我是否完整檢查了該功能的實現？
3. [ ] 我是否理解了兩者的差異？
4. [ ] 我是否在照抄已驗證的模式？
5. [ ] 我是否在猜測？（如果是，停止）

## 項目特定慣例

### 前端

- **API 配置**：統一在 `src/config/api.js`
- **構建方式**：本地 npm build，然後掛載 dist 目錄
- **API 調用**：使用 `API_ENDPOINTS.xxx`
- **參考頁面**：LoopManagementTab.vue（迴圈管理）

### 後端

- **路由定義**：檢查 `routers/loops.py`
- **數據庫連接**：使用 `req.app.state.db_pool`
- **錯誤處理**：HTTPException 要在 generic Exception 之前捕獲

## 記住

**盤查，不要猜測。**
**參考，不要發明。**
**對比，不要推論。**
