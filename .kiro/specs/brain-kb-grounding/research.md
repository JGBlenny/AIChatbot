# 研究記錄：brain-kb-grounding

> 建立時間：2026-07-20　目的：記錄設計階段的整合調查與架構決策（Extension／輕量發現流程）

## 摘要

### 調查範圍
在既有 sync `conversational_step`（Brain）上掛 OpenAI function calling 工具 `search_kb`，讓面向對話岔題即答（inline_answer）從「憑規則文字與模型印象」升級為「知識庫背書」。核心待決：sync Brain 與 async 檢索、running event loop 的跨界呼叫方式。

### 關鍵發現
- **`conversational_step` 僅單一呼叫點**（`conversational_engine.py:631`；其餘皆註解/docstring）——使「Brain 改 async」的改動退化為呼叫點加 `await`，差距分析原評「波及 sync 兄弟方法與呼叫鏈」被推翻（兄弟方法 async/sync 可共存、不需動）。
- **引擎在呼叫點已握全部脈絡**：`prepare(session_id, user_id, vendor_id, ...)` 的 `vendor_id` 在作用域（`:497`）、`config.persona_role`（=target_user，`:169/174`）、`self.retriever` 於 `__init__` 注入（`:393`）且引擎已有檢索先例（`_grounding_by_category`/`_grounding_by_api`，`:1073-1141`）。R2.2 脈絡穿透零障礙。
- **基礎設施就位**：`llm_provider.chat_completion(**kwargs)` 直透 SDK（`llm_provider.py:104-114`）、openai==1.54.0（新 tools API）、計量走 contextvars 自動涵蓋第二次呼叫（`usage_metering.py:161-174`）、facet 欄位 `set_facet_info` 已備（`:200-202`）。
- **架構翻轉**：差距分析原推「路線 A2 兩階段（引擎編排工具圈）」；讀實碼後改推「路線 B 精煉版（Brain 改 async + 引擎傳 async 檢索 callback）」——工具圈留在 Brain（其天然歸屬），檢索留 async 世界，脈絡經 closure 注入，surface 最小。

## 研究主題

### 主題 1：sync Brain × async 檢索 × running event loop（頭號決策）

**調查問題**：sync `conversational_step` 在運行中的 async loop 內被同步呼叫，如何讓工具圈查 async 檢索而不觸發 `RuntimeError`？

**研究方法**：[x] 現有程式碼分析

**發現**：
- `conversational_step` 全 sync，唯一呼叫點 `conversational_engine.py:631` 在 `async def prepare` 內、無 await、周圍皆 await（`_ground_by_api`/`_get_system_context`）。
- codebase 無 `asyncio.run`/`run_until_complete` 先例——running loop 內呼叫會炸。
- 引擎 `__init__` 已注入 `retriever`；引擎自身多處 `await` 檢索（`:1088`）。

**候選方案評估**：

| 方案 | 描述 | 優點 | 缺點 |
|---|---|---|---|
| **B（採用）Brain 改 async + async callback** | `conversational_step` 改 async；引擎傳入 async `kb_search` closure（bake vendor/target_user/business_types）；Brain 回 tool_call 時 `await kb_search(query)` | 呼叫點僅加 `await`（單一）；工具圈邏輯內聚於 Brain；檢索留 async 世界；脈絡經 closure 乾淨注入；計量自動涵蓋 | `conversational_step` 簽名/型別改 async（呼叫鏈單點） |
| A2 兩階段（引擎編排） | Brain 拆 plan/resume 兩方法；引擎 await 檢索夾在中間 | Brain 保持 sync | 兩個公開方法＋跨界攜帶 message 歷史；工具圈邏輯外洩到引擎；surface 較大 |
| C sync 檢索路徑 | 新增 sync DB 查詢入口 | Brain 內閉環 | 違「非同步優先」；reranker 若 async 仍卡；雙檢索路徑維護 |

**結論與建議**：採方案 B。經確認單一呼叫點與脈絡穿透可行後，B 的 surface 反而小於 A2，且工具圈歸屬正確（Brain＝決策核心）。

### 主題 2：脈絡穿透與檢索過濾一致性（R2.2）

**調查問題**：`search_kb` 的 vendor/target_user/business_types 是否與 FAQ 主路徑同源？

**發現**：
- 檢索入口 `retrieve_knowledge_hybrid(query, vendor_id, top_k, similarity_threshold, target_user, mode, ...)`（`vendor_knowledge_retriever_v2.py:355-396`）；business_types 經 vendor_info 帶入。
- 引擎持有 `vendor_id`（prepare 參數）、`config.persona_role`（=target_user）、mode（b2c/b2b 由 config）。
- FAQ 主路徑 `routers/chat.py:2793` 亦用同一 retriever。

**結論**：由引擎在 closure 內以 `config.persona_role` 對映 target_user、帶 vendor_id、沿用既有 KB 閾值建構 `kb_search`，即與 FAQ 同源。design 於元件契約逐項固定。

### 主題 3：新 tools API 與回傳解析

**發現**：既有先例 `intent_classifier.py:322-341` 用舊 `functions` API（`message.function_call`）。本案改用新 `tools` API（`tools=[{type:"function",...}]`、`tool_choice="auto"`、回傳走 `message.tool_calls` 列表）；SDK 1.54.0 相容。需在 provider 回傳結構取 `raw_response.choices[0].message`。

**結論**：低風險。以新 tools API 實作，注意與舊先例不同的回應遍歷。

## 現有程式碼分析

### 整合點
- **改 async**：`llm_answer_optimizer.conversational_step`（`:825`）；呼叫點 `conversational_engine.py:631` 加 `await`。
- **新增 callback 建構**：引擎於呼叫前組 `kb_search`（closure over vendor_id/persona_role/mode/db_pool/retriever）。
- **工具定義**：`search_kb` function schema（單參 `query:string`）。
- **落地規則**：Brain prompt 增「查得結果據實、無命中誠實回退」契約；工具結果注入格式（命中序列化、無命中訊號）。
- **計量**：`set_facet_info`/usage_events 記 `search_kb` 呼叫與命中（自動涵蓋 token）。

## 風險登記

| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|---|---|---|---|---|---|
| async 化破壞既有 Brain 呼叫 | 技術 | 高 | 低 | 單一呼叫點加 await；unit 覆蓋不掛工具（未帶 callback）＝現行行為 | 已緩解（設計） |
| 工具結果污染事實（幻覺） | 品質 | 高 | 中 | 無命中誠實回退、prompt 禁庫外事實；R6.3 對照留檔 | 開放（測試把關） |
| 岔題輪延遲增（二次 LLM＋檢索） | 效能 | 中 | 中 | 工具圈上限 1；P90≤3s 目標與量測；不命中快回退 | 開放（量測） |
| 脈絡漏帶致越權檢索 | 安全 | 高 | 低 | closure 固定三過濾、與 FAQ 同 retriever；R2.2 逐項驗 | 已緩解（設計） |
| 模型濫呼工具（每輪都查） | 成本 | 中 | 中 | tool_choice=auto＋prompt 限「僅事實性岔題」；呼叫率計量監控 | 開放（監控） |

## 開放問題

### 問題 1：工具結果無命中的訊號格式
**描述**：檢索 0 命中時，回灌 Brain 二次呼叫的 tool result 內容如何表達「查無」，使 Brain 走誠實回退而非硬編。
**可能解法**：(a) 回固定 sentinel 字串 `"NO_MATCH"`＋prompt 契約；(b) 回空結果＋結構化 flag。
**決策狀態**：design 元件契約定案（採 a，最簡且與現有 prompt 驅動一致）。

### 問題 2：工具圈上限的強制點
**描述**：R1.2 單輪至多 1 次 search_kb，連續要求時強制收斂。
**可能解法**：Brain 內迴圈計數，達上限則移除 tools 參數再呼叫一次強制產最終 JSON。
**決策狀態**：已決定（Brain 內計數 + 去 tools 收斂呼叫）。

## 時間軸
| 日期 | 活動 | 結果 | 後續行動 |
|---|---|---|---|
| 2026-07-20 | 輕量發現 | 定案路線 B；脈絡穿透可行；tools API 選定 | 產出 design.md |
