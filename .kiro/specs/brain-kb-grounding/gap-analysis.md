# 差距分析：brain-kb-grounding

> 建立時間：2026-07-20　語言：zh-TW　狀態：gap-analysis
> 對象需求：requirements.md（R1–R6）
> 分析方法：`.kiro/settings/rules/gap-analysis.md` 不存在，改用既有程式碼實查 + design-principles 分析框架；所有事實均附 file:line。

## 分析摘要

- **多數基礎設施已就位**：LLM 抽象層透傳 `**kwargs`（tools 可直達 SDK）、OpenAI 1.54.0（新 tools API 支援）、計量走 contextvars 自動涵蓋工具圈第二次呼叫、facet_key/turn_number 欄位已預留、既有 function calling 先例（intent_classifier 舊 functions API）。這些讓 R1/R2/R5 的骨架成本低。
- **唯一硬整合難點**：`conversational_step` 是 **sync** 方法，卻在 **運行中的 async event loop** 內被呼叫（conversational_engine.py:631 無 await 同步呼叫）；而知識庫檢索 `retrieve_knowledge_hybrid` 是 **async**。工具圈要在 sync Brain 內查 async 檢索，`asyncio.run()` 在既有 running loop 內會炸——這是 design 階段必須先解的架構決策點。
- **檢索入口需確認過濾傳遞**：`retrieve_knowledge_hybrid` 簽名已含 vendor_id/target_user/similarity_threshold/mode，但 business_types 經 vendor_info 帶入、Brain 呼叫處手上未必有這些脈絡——需確認脈絡從引擎穿到工具執行點的路徑。
- **建議實作路線**：混合式（extend）——擴充既有 sync Brain 加工具圈、重用既有 async 檢索，核心設計決策落在跨 sync/async 邊界的呼叫方式。

## 1. 現有元件盤點（可重用資產）

| 能力 | 位置 | 現況 | 對需求 |
|---|---|---|---|
| LLM 抽象層透傳 tools | `services/llm_provider.py:104-114` | `chat_completion(**kwargs)` 直透 OpenAI SDK；docstring 已註記支援 functions/function_call | R1 可直接傳 `tools`/`tool_choice`，抽象層零改動 |
| tool_calls 回傳 | `llm_provider.py:117-130` | 回傳含 `raw_response`，`choices[0].message.tool_calls` 可取 | R1 解析工具呼叫可行 |
| function calling 先例 | `services/intent_classifier.py:208-268, 322-341` | 用舊 `functions` API，`function_call={"name":...}` | R1 有慣例可循；本案改用新 `tools` API（SDK 相容） |
| Brain 呼叫 | `services/llm_answer_optimizer.py:825-918` | sync；`:890` 呼叫 provider（json_object）；`:900` 解析；`:910-912` inline_answer→next_question | R1/R3 工具圈與落地規則的植入點 |
| 知識庫檢索 | `services/vendor_knowledge_retriever_v2.py:355-396` | `async retrieve_knowledge_hybrid(query, vendor_id, top_k, similarity_threshold, target_user, mode, ...)` | R2 重用入口；閾值/過濾參數已具備 |
| 計量自動累計 | `services/llm_provider.py:129,161,179` + `services/usage_metering.py:161-174` | contextvars 會話級累計，每次 LLM 呼叫更新同一 context | R5.1 工具圈第二次呼叫自動計入，零額外掛點 |
| facet 標記欄位 | `usage_metering.py:36-41, 200-202` | `_FACET_COLS=("facet_key","turn_number")`、`set_facet_info()` | R5.2 呼叫率/命中率埋點可掛此機制 |
| inline_answer 語義 | `llm_answer_optimizer.py:910-912`（conversational-repair R3.1） | 先答再接 next_question 已實作 | R3.3 接回槽位行為既有，不需新建 |

## 2. 核心差距與挑戰

### 差距 A（阻斷級）：sync Brain × async 檢索 × running event loop

**事實**：
- `conversational_step` 全 sync（`llm_answer_optimizer.py:825`），類內無 async 依賴。
- 呼叫處在 async 方法內同步呼叫、無 await（`conversational_engine.py:631`）——即呼叫當下**事件迴圈正在運行**。
- `retrieve_knowledge_hybrid` 為 async（`vendor_knowledge_retriever_v2.py:355`），內部 `_vector_search`/`_keyword_search` 皆 async。
- codebase **無 `asyncio.run()` / `run_until_complete` 先例**（scout 查證）——在 running loop 內呼叫這兩者會 `RuntimeError`。

**這是 design 階段的頭號決策**。候選方向（design 定案，此處僅列供評估，不預選）：
1. **工具執行點上移到引擎（async）層**：Brain 不自己查，改為 Brain 回傳 tool call 後**由 async 的 conversational_engine 執行檢索**再回灌 Brain 二次呼叫。優點：檢索留在 async 世界、無跨界 hack；代價：Brain 的「單次呼叫」變成引擎與 Brain 來回兩段，`conversational_step` 需拆成「首呼→回傳待查訊號」與「續呼→帶檢索結果」兩階段（或改 async）。
2. **conversational_step 改 async**：最直接對齊 async 世界，但 `conversational_step` 及其呼叫鏈需全面 async 化，波及面較大（`optimize_answer` 等 sync 兄弟方法的邊界）。
3. **同步檢索路徑**：檢查是否有/可加一個 sync 檢索入口（psycopg2 同步查詢在批次腳本有先例，tech.md:105）。優點：Brain 內閉環；代價：等於在 async 服務裡開一條 sync DB 查詢，與「非同步優先」慣例相悖，且 reranker 服務呼叫可能仍是 async。

> 傾向記錄：方向 1（工具執行上移引擎層）最貼合現有 sync/async 分工與「引擎掌控寫入/查詢、Brain 只決策」的既有邊界，但需確認 `conversational_step` 兩階段化的改動量。design 階段須落定。

### 差距 B（中）：脈絡穿透到檢索過濾

**事實**：`retrieve_knowledge_hybrid` 需 vendor_id/target_user/mode，business_types 經 vendor_info 帶入（`vendor_knowledge_retriever_v2.py:373-385`）。Brain 呼叫處（`conversational_engine.py:631`）手上有 rules_text/system_md/state/faces，但**未明確持有 vendor_id/target_user/business_types**——需確認引擎層是否已有這些（引擎啟動時應有 persona_role/vendor，design 須追出確切變數）。
**對需求**：R2.2 要求隔離與 FAQ 主路徑一致，脈絡穿透若缺一項即違規，是 design 必須逐項對齊的點。

### 差距 C（低）：舊 functions API vs 新 tools API

**事實**：既有先例（intent_classifier）用舊 `functions` API；本案 requirements 寫 tools/function calling。SDK 1.54.0 兩者皆支援。
**對需求**：低風險，選新 `tools` API（回傳走 `message.tool_calls` 列表）即可，僅需注意與舊先例不同的回應遍歷方式。

### 差距 D（低）：無命中/失敗的落地規則

**事實**：inline_answer 現行僅來自 rules_text 與模型知識；R3.2 要求無命中時「回退規則文字或誠實告知、不憑印象補答」。這是 **prompt 契約 + 引擎後處理** 的設計，非基礎設施缺口。
**對需求**：R3 全落在 prompt 規則與工具結果注入格式的設計，design 需定「檢索結果如何呈現給 Brain 二次呼叫」與「無命中訊號怎麼傳」。

## 3. 實作路線評估

| 路線 | 描述 | 優點 | 代價 | 適配 |
|---|---|---|---|---|
| **A. Extend（引擎層執行工具）** | Brain 首呼回傳 tool call → async 引擎執行 `retrieve_knowledge_hybrid` → 帶結果二次呼叫 Brain | 貼合 sync/async 分工與「引擎掌控查詢」既有邊界；檢索留 async 世界；計量自動涵蓋 | conversational_step 需兩階段化；引擎新增工具圈編排 | ⭐ 推薦候選 |
| **B. Brain 改 async** | conversational_step 全面 async 化、內部 await 檢索 | Brain 內閉環、概念單純 | 波及 sync 兄弟方法與呼叫鏈，改動面大、回歸風險高 | 次選 |
| **C. Sync 檢索入口** | 新增/重用 sync 檢索查詢 | Brain 內閉環、不動 async | 違「非同步優先」慣例；reranker 若 async 仍卡；等於雙檢索路徑維護 | 不推薦 |

**建議**：以路線 A 為設計主軸，design 階段確認 `conversational_step` 兩階段化的實際改動量與脈絡穿透路徑，若改動過大再回頭比較 B。

## 4. Design 階段須解決的研究項

1. **sync/async 邊界決策**（差距 A）：定案工具執行點在 Brain 還是引擎、conversational_step 是否兩階段化或改 async——**本案架構主決策**。
2. **脈絡穿透清單**（差距 B）：逐項追出 vendor_id/target_user/business_types 在引擎層的確切來源變數，確保 R2.2 隔離一致。
3. **工具結果注入格式**（差距 D）：檢索命中/無命中如何序列化回灌 Brain 二次呼叫的 messages；無命中訊號的 prompt 契約。
4. **工具圈上限強制**（R1.2）：連續 tool call 的計數與強制收斂實作點。
5. **計量埋點細節**（R5.2）：search_kb 呼叫/命中如何寫入 usage_events（是否走 set_facet_info 或新欄位/metadata）。
6. **延遲預算驗證**（R5.3）：一次檢索 + 二次 LLM 的 P90 增量量測方式。

## 5. 不變量確認（實作全程不得破壞）

- 引擎寫入 gate（required_slots/確認機器值/execute/冪等）——R4.3，本案不觸碰。
- Brain 輸出 JSON schema（action/extracted_fields/next_question/inline_answer + 驗證）——R1.4，工具圈不新增輸出欄位。
- 檢索管線與 embedding 流程零改動——R2.1/R2.4，只新增呼叫方。
- FAQ 快路徑 / 診斷面向 / 表單流程行為一致——R6.1。
