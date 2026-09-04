# 落差分析：agentic-mcp-orchestration（2026-09-04）

> 需求：requirements.md v1（未核可，本分析可回饋修訂）。方法：三個唯讀 scout 分工（A 入口與契約／B 可工具化服務／C 治理與依賴）＋外部依賴查證（mcp SDK 文件、OpenAI function-calling 文件）＋主 session 對照。⚠️ `gap-analysis.md` 規則檔缺席，沿用 presales-grounding-gate 的落差格式。
> ⚠️ 更正 scout C 兩條：`rag-orchestrator/tests/conftest.py` 與 `tests/support/brain_stub.py` **存在**（本 session 單元測試 `from tests.support.brain_stub import stub_step` 實跑綠），`retrieval_representation` 消費者＝`knowledge_import_service`、`vendor_knowledge_retriever_v2`（SQL 投影）、`semantic_reranker`（`scoring_surface`）、`scripts/regenerate_level_a_embeddings.py`。

## 一、可沿用的既有資產（對碼）

| 需求 | 既有元件（`檔案:符號`） | 沿用方式 |
|---|---|---|
| R1 Runtime 串流 | `routers/chat.py:_conversational_sse／stream_response_wrapper／_metered_stream`；事件序 start→intent→answer_chunk*→metadata→done | 原樣包，agent 最終回答走同一 SSE 產生器 |
| R1 session | `conversational_engine`：狀態存 `form_sessions.collected_data`（`CONVERSATIONAL_FORM_ID='conversational'`），鍵 `config_key／collected_fields／asked_count／dialog／slots／executed／awaiting_confirm／handoff_log` | `session.slots` 工具直接讀寫同一列 |
| R1 模型客戶端 | `services/llm_provider.py:OpenAIProvider`（sync＋`AsyncOpenAI`）、`get_llm_provider()`、`_meter_usage()` 鉤 | Runtime 用同一 provider，計量自動累計 token |
| R1 迴圈雛形 | `llm_answer_optimizer.py`：`MAX_TOOL_CALLS=1`、`tool_choice="auto"`、tool result 回填續呼、strict `CONVERSATIONAL_STEP_SCHEMA` | 迴圈骨架可抄，上限由 1 改成預算制 |
| R2 隔離謂詞 | `vendor_knowledge_retriever_v2.py:_vector_search`（`business_types && {system_provider}` 嚴格分支、`target_user`、`vendor_ids && %s::int[]`）、`_effective_target_user`、`KNOWN_TARGET_USERS` | ⛔ 不複製：工具直接呼叫 `retrieve()`，謂詞同源（R2.6） |
| R3 kb.search | `BaseRetriever.retrieve(query, vendor_id, top_k, similarity_threshold, …, return_unfiltered)` 回含 `similarity／score_source／provenance` 的列 | 包成工具，回摘要清單（截掉 answer） |
| R3 jgb2.query | `services/jgb_system_api.py:JGBSystemAPI.get_bills/get_contracts…（role_id, user_id）`；`services/jgb/{bills,contracts,estates,iot,subscription,accounts,payments,repairs,invoices}.py` 各自 `build_<domain>_facts(row, user_question)`；`jgb_response_formatter.py`（`FIELD_LABELS／MONEY_KEYS`，emergency_status 真值注入） | 包成工具回 facts；⚠️ 無中央 registry，design 要定 domain→builder 映射 |
| R3 通用 API | `universal_api_handler.py:execute_api_call(endpoint_id, session_data, form_data, user_input)`＋`api_endpoints` 表 | 查詢型端點包成 `jgb2.query.<endpoint_id>` |
| R4 確認契約 | `conversational_engine.py:_QR_SUBMIT/_QR_EDIT/_QR_CANCEL`、`TransactionState{slots, executed, awaiting_confirm}`、`_build_confirm_summary／_execute_endpoint／_build_receipt` | 機器值與冪等旗標沿用；token 綁 payload 雜湊為新增 |
| R5 大綱 | `system_context.py:get_system_context(db_pool, domain_key)`（base＝category=系統脈絡∧target_user NULL；角色層 `_fetch_appends`；面向父鏈 `_fetch_category_chain`；per-key 快取＋`reset_cache()`） | pm／tenant 目錄直接用；prospect 大綱另組（見缺口） |
| R6 Verifier 常數 | `presales_gate.py:SENSITIVE／HANDOFF_WORDS／FactClass／_sentences／analyze_ask`；`conversational_config.py:PRESALES_HANDOFF_MESSAGE／effective_handoff_message／channel` | 單一來源（R12.4） |
| R6 禁止詞 | `coverage-map/topics-v2.json` 的 `forbid`（附錄二三禁）、`sources/koyu-v2-phrasings.json` 的 must_ask_first | 進 Verifier 規則集（版本戳） |
| R7 轉人 | `chat.py:HandoffSignal`、`handoff.reason` 值域、`state["handoff_log"]` 重播 | 原樣沿用＋新 reason |
| R8 計量落點 | `usage_metering.py:set_decision(snapshot, facet_event)` → `usage_events.decision_snapshot`（既有子鍵 `presales／routing_verdict／facet_key／prior`）；事件層 `llm_calls／prompt_tokens／completion_tokens／est_cost_usd` | 加 `agent_shadow`／`agent` 子鍵；成本 ×3 檢查用事件層欄位 |
| R9 對外契約 | `chat.py:VendorChatResponse／QuickReply／HandoffSignal`；`docs/api/conversational-api.md`；`tests/unit/chat_flow/*_req.py` 8 檔 | 契約測試不動、全綠為切換前提 |
| R10 健檢 | `pipeline_health_service.py:check_all_components()`（核心 PostgreSQL／Embedding／LLM；非核心 Redis／Reranker／Vector／Keyword）、`/api/v1/system/pipeline-health` | 加 MCP server 與大綱版本 checker |
| R10 不變量 | `scripts/audit/check_invariants.sh` 26 條；本 spec 會碰 8（門檻唯一讀值）、10（applicability）、12（representation）、17（R10-P 母體） | 新增 4 條（工具 schema 無身分欄、謂詞同源、大綱 token、Verifier 尺自證） |
| R13 測試骨架 | `tests/conftest.py`（unit/integration/e2e marker、`req` marker）、`tests/support/brain_stub.py`、`scripts/run-tests.sh [unit|e2e]`（`RUN_E2E=1`） | 新測試歸 `tests/unit/agent/`＋`tests/e2e/agent/` |

## 二、缺口（需求 → 現況沒有的）

| # | 缺口 | 影響需求 | 大小 |
|---|---|---|---|
| G1 | **Agent Runtime 不存在**：現行只有單次工具呼叫（`MAX_TOOL_CALLS=1`）後取最終 JSON；沒有預算制迴圈、沒有工具結果隔離包裝、沒有降級路徑 | R1、R11 | 新元件 |
| G2 | **MCP server 不存在**：`mcp` 未在 requirements；無工具 registry、無 OpenAPI 同源描述 | R2、R3、R11 | 新元件＋依賴 |
| G3 | **kb.get 沒有對應函式**：現行只有 retrieve()（依查詢），沒有「依 id 取列且套同一隔離謂詞」 | R3.2 | 小 |
| G4 | **help.read 沒有資料源**：幫助中心 HTML 在業主本機 `~/jgb/幫助中心/…`，不在 repo、不在容器、不在 DB | R3.4、D3 | 中（要匯入或掛載，含版本戳） |
| G5 | **prospect 大綱組裝器不存在**：`get_system_context` 只組系統脈絡列；把 31 筆售前池整理成單一大綱（含邊界句、刻意不補、CTA）的程式與 token 預算檢查都沒有；`tiktoken` 不在 requirements | R5 | 中 |
| G6 | **Output Verifier 不存在**：引用契約 schema、逐字子串比對、斷言封閉詞集、句型豁免、敏感五類主題層拒答、重寫回圈全無；現行 `analyze_ask` 只做反問句拆解 | R6 | 新元件（核心） |
| G7 | **confirmation_token 契約不存在**：現行同意判定在引擎層比對機器值，沒有「token 綁 payload 雜湊、兌現一次」的物件 | R4 | 小–中 |
| G8 | **影子模式不存在**：沒有「同一則訊息跑兩條鏈、只回一條、另一條落 log」的機制；SSE 路徑上要避免阻塞回應 | R8 | 中 |
| G9 | **per-audience 切換開關不存在**：入口判定寫死 `CONVERSATIONAL_ENABLED_ROLES={'prospect'}` | R9 | 小 |
| G10 | **工具呼叫追蹤 id 與工具日誌**：計量只有事件層，無回合內工具序列 | R10 | 中 |
| G11 | **reranker 靜默停用**（記憶＋scout B：`available()` 失敗後 recheck 期間全走 vector 分支，健檢看不出）：agent 架構下 kb.search 若還用 reranker，同一風險延續 | R10.3、R13 | 既有債，設計要決定用不用 |
| G12 | **FACE_BUILDERS 中央 registry**：記憶稱有，scout B 查無；各 domain 模組各自 builder | R3.3 | 設計時對碼 |
| G13 | **e2e 層測試目錄**：`tests/e2e/` 未建；`RUN_E2E=1` 機制在 | R13.5 | 小 |

## 三、實作路線選項

### 選項 A：全在 rag-orchestrator 內（in-process 工具、MCP 只對外掛載）
- Runtime 與工具函式同一程序；Runtime 直接呼叫工具函式（不走網路），身分由 Runtime 明碼傳入；`MCPServer` 用 `streamable_http_app()` `Mount` 在 FastAPI 的 `/mcp`，主 app lifespan 進 `mcp.session_manager.run()`（SDK 文件明列，否則首次請求 `RuntimeError: Task group is not initialized`），供外部 agent（Claude Code、回測工具）使用，bearer 走 `TokenVerifier＋AuthSettings`，handler 內 `get_access_token()` 取身分。
- 優點：零額外延遲、一份程式、隔離謂詞天然同源、影子模式最容易做。
- 缺點：MCP 對內是形式（Runtime 不經協定），「決策搬進模型」與「工具可被外部共用」兩件事耦合在同一部署單元；擴大時要再拆。

### 選項 B：獨立 `mcp-tools` 服務（HTTP）
- 工具服務獨立容器；Runtime 以 MCP client（streamable HTTP）呼叫；身分以每請求 bearer token 的 claims 帶（`AccessToken.claims`），server 端不信任 payload。
- 優點：邊界最乾淨、可獨立 security review 與擴縮、外部與內部走同一條路。
- 缺點：每次工具呼叫多一次 HTTP 往返（50–200 ms ×4 次）；隔離謂詞要 import 同一模組（跨容器共享程式碼或抽套件）；多一個服務的健檢、部署、稽核。

### 選項 C：混合（建議）
- 工具以「純函式 registry」實作一次，兩個門面：in-process（Runtime 熱路徑）與 MCP `streamable_http_app()`（外部）。M0 先做 registry＋MCP 掛載（外部可用，證明契約）；M1 Runtime 走 in-process；若日後要獨立部署，門面已在。
- 代價：registry 的身分注入介面要設計成「呼叫端傳 `Identity` 物件、工具內不接受覆寫」，兩個門面都經它。

### 模型呼叫方式
- **Chat Completions 迴圈**（現行 SDK 1.54，`tool_choice`、`parallel_tool_calls=false`、strict schema）：Runtime 自己 dispatch 工具——與 `llm_answer_optimizer` 現有雛形一致，⛔ 不需要 MCP server 對 OpenAI 可達。
- **Responses API 內建 `mcp` 工具型**：需要 `server_url` 對 OpenAI 可達（或 Secure MCP Tunnel），且 `authorization` 每次請求要帶；線上服務在 bastion 後、EC2 無 public IP ⇒ 不適合當生產路徑；可留給外部 agent 實驗。
- 建議：Chat Completions 迴圈＋in-process dispatch；D1 若改 Claude，同形狀。

## 四、風險與待研究

| 項 | 說明 | 處置 |
|---|---|---|
| Verifier 判準 | 「含產品斷言的句子」封閉詞集要涵蓋否定式（「無法／不需要」）——第五輪 e2e 唯一漏就是否定式 | 設計時以五輪 e2e 抓到的句子做尺自證（R10.4） |
| 引用逐字子串 | 模型會改寫（全半形、標點、空白）；正規化規則要定；quote 太短（<4 字）的濫用要擋 | 設計定最小引用長度與正規化 |
| 大綱 token 預算 | `tiktoken` 未裝；中文估算 1.6 字/token 只是粗估 | 加依賴或用 provider 回的 usage 校準 |
| 幫助中心資料源 | 不在容器；版本戳 2026-08-18；DSP-010 顯示兩頁互相矛盾 | D3 裁後決定匯入方式；未裁前 `citable=false` |
| 影子模式成本 | 每回合 2–4 次模型呼叫 ×2 條鏈；prospect 流量小可承受，要有月上限（R8.5） | 計量既有欄位可算 |
| SSE 阻塞 | 影子 agent 必須在回應送出後以背景 task 跑，且標 `is_internal`（不變量 5） | 設計定 |
| reranker | 售前不用；pm／tenant 的 kb.search 是否保留 reranker 待反證 #1 的重評 | 列入 design 決策 |
| 不變量 10／12／17 | 本 spec 不動資料，但 agent 路徑不讀 applicability／representation ⇒ 不變量本身不紅；除役另案 | R12 |
| 決定性 | 快取重播只覆蓋逐字重問；改寫問法的重問會再進模型 | 接受（R13.4） |
| MCP SDK 細節未查 | structured output（回傳型別→schema）、`ToolError` 型別、`stateless_http` 對 session 的影響 | design 討論前補查 `servers/structured-output/`、`servers/handling-errors/` |

## 五、對需求的回饋建議
1. R3.4 加「幫助中心資料源與版本戳的匯入方式」為 D3 的一部分。
2. R2.6 明寫「同源」的機械判準：工具模組 import `vendor_knowledge_retriever_v2.retrieve`，⛔ 不得自寫 SQL（可寫成不變量）。
3. R8.1 加「影子執行以背景 task 在回應送出後進行，計量標 is_internal」。
4. R1.1 加「單回合 `parallel_tool_calls=false`」以維持工具序列可追蹤。
