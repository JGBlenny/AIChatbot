# 實作任務：brain-kb-grounding（Brain 知識庫落地）

> 建立時間：2026-07-20
> 需求：requirements.md（R1–R6）｜設計：design.md（3 元件＋路線 B）｜落差：gap-analysis.md｜研究：research.md（3 決策）
> 標記：`(P)` = 可與同層其他 `(P)` 平行
> 鐵律：**寫入 gate 不得觸碰**（required_slots／confirm 機器值／execute／冪等全不動）；**Brain 輸出 JSON schema 不變**（action/extracted_fields/next_question/inline_answer，工具圈不新增輸出欄位）；**安全降級 = 現行行為**（kb_search=None／檢索失敗／第二呼失敗三態皆回退，SHALL NOT 建單）；`search_kb` 純唯讀；檢索管線＋embedding 零改動（僅新增呼叫方）；閾值與 FAQ 主路徑同源（`KB_SIMILARITY_THRESHOLD`，非決策樹 0.6）；TDD 先紅後綠。

## 1. 計量底座（前向、加性）

- [x] 1.1 (P) migration＋`set_search_kb_status` hook（TDD）：`usage_events` 加 `search_kb_status VARCHAR(16) NULL`（IF NOT EXISTS、可空預設 null、向後相容非破壞）＋rollback 檔；usage_metering 新增 `set_search_kb_status(status)` 比照 `set_facet_info` 慣式（ctx None/finalized 靜默、沿用欄位偵測降級——欄位未建時事件本體不受波及）；unit 矩陣：null/hit/miss 三態落庫、欄位缺失時靜默降級。
  - 需求：5.1, 5.2

## 2. Brain 工具圈（核心，改 async）

- [x] 2.1 Brain async 化＋工具圈＋NO_MATCH（TDD，元件 1）：`conversational_step` 由 sync 改 async；新增模組常數 `SEARCH_KB_TOOL`（單參 query）／`NO_MATCH_SENTINEL`／`MAX_TOOL_CALLS=1`；`kb_search=None` 時**維持單次 json_object 呼叫、輸出與現行逐位一致**（回歸鎖）；`kb_search` 提供時首呼帶 `tools`＋`tool_choice='auto'`，回 tool_call → `await kb_search(query)`（上限 1）→ 注入 tool result 續呼取最終 JSON，達上限或第二呼 → 去 tools 強制收斂；最終 JSON 沿用既有驗證（action 列舉/型別/inline_answer str/scope 正規化）；任一步例外 → 回 None（呼叫端既有降級）。unit：kb_search=None 逐位一致／命中路徑第二呼帶 result／NO_MATCH 路徑／上限強制收斂／kb_search 拋錯回 NO_MATCH／第二呼失敗回 None／schema 驗證。
  - 需求：1.1, 1.2, 1.3, 1.4, 4.2
- [x] 2.2 async 測試遷移（一級交付，2.1 同步進行）——27 檔遷移完成，獨立驗證全 unit 864 passed/0 failed（基線 836＋28 新測），零 skip/xfail 掩蓋：`conversational_step` 改 async 波及約 25 個測試檔——(a) brain 單元測試（`test_brain_dialog_history_req.py`／`test_brain_transaction_req.py`／`test_step_scope_face_req.py`）改 async 測試取回傳；(b) 引擎測試 `conversational_step` 的 `MagicMock.return_value=dict` 全改 `AsyncMock`（`test_deterministic_slot_fill_req.py`／`test_hybrid_grounding_req.py`／`test_engine_scope_face_req.py`／`test_engine_transaction_req.py`／`test_prepare_api_converge_req.py`／`test_non_regression_domain_facets_req.py` 等十餘檔）；(c) 整合測試假 optimizer 的 sync `def conversational_step` 改 async def（`tests/integration/conversational/*_req.py` 8 檔）。收案＝既有 unit/integration 全綠（此為 R6.2 前提）。
  - 需求：6.2

## 3. 引擎注入與落地規則

- [x] 3.1 引擎 `_make_kb_search` closure＋呼叫點 await（TDD，2.1 完成後，元件 2）——含 `_tx` gate（只注入交易面向、診斷零改）＋`SEARCH_KB_ENABLED` 快速回退；整合測試 4 passed（真 retriever×closure，命中/NO_MATCH/隔離/失敗降級）：引擎新增 `_make_kb_search(config, state)` 回 async closure——bake `vendor_id=state.get("vendor_id")`／`target_user=config.persona_role`／`mode='b2c'`／`kb_threshold=env KB_SIMILARITY_THRESHOLD(0.55)`（與 FAQ 主路徑同源）；內呼既有 `retrieve_knowledge_hybrid`（零改動）、空結果或例外回 `NO_MATCH_SENTINEL`、命中經 `_format_kb_hits_for_tool` 序列化；呼叫點 `conversational_engine.py:631` 加 `await` 並傳 `kb_search=self._make_kb_search(config, state)`；工具呼叫/命中經 `set_search_kb_status` 埋點（hit/miss）。integration：真 retriever 驗脈絡過濾（vendor/target_user）與閾值一致、失敗降級回 NO_MATCH。
  - 需求：2.1, 2.2, 2.3, 4.1, 4.4, 5.2
- [x] 3.2 (P) 落地規則 prompt 契約（TDD，2.1 完成後，元件 3）——tool_note gated on kb_search（None 路徑 prompt 逐字不變），prompt-contract unit 綠：擴充 Brain `schema_note`——(a) 僅對事實性岔題（費用/時程/規定）呼叫 search_kb，純槽位/閒聊/規則可答者不呼叫；(b) 有命中據檢索文字組話、不引入庫外事實；(c) 收到 NO_MATCH 誠實告知無法確認或回退規則指引、**不補庫外事實**（R3.2 封閉回退話術）；(d) 岔題答完接回 next_question（沿用 R3.1）。
  - 需求：1.1, 3.1, 3.2, 3.3

## 4. 情境 e2e 與收案

- [x] 4.1 岔題三態 e2e＋NO_MATCH 決定性 gate（3.1／3.2 完成後）——**決定性三態已綠**：命中/NO_MATCH/失敗降級由 unit（test_brain_kb_grounding 工具圈）＋integration（_make_kb_search closure）覆蓋；NO_MATCH negative gate（不含金額/歸屬結論）在 unit。**e2e 真 LLM 實跑 1 passed（2026-07-21，dev compose＋真檢索＋mock JGB）**：進面向→費用岔題被回答→search_kb_status='hit' 埋點落地。修正：e2e 檔與 runbook §14-3 的 trigger_facet_key 筆誤 `repair`→`repair_create`（正確鍵以 DB config registry 為準，同 test_repair_scenarios_e2e）。：**有命中**——修繕面向中問費用→查庫、inline_answer 與檢索 answer 語義一致（正向斷言）、接回槽位；**無命中**——問庫中無知識岔題→inline_answer 落封閉回退話術、**negative 斷言不得含金額/天數/「由房東負擔」「由租客負擔」等歸屬結論詞**（決策 2 gate，R3.2/R6.3 可執行判準取代人工對照）；**檢索失敗降級**——注入 retriever 故障→行為等同現行、面向不中斷；每案斷言 `search_kb_status` 埋點正確。
  - 需求：3.1, 3.2, 4.1, 6.3
- [x] 4.2 回歸＋計量驗收＋收案（4.1 完成後）——**unit 864 passed/0 failed 獨立驗證（基線 836，零回歸 R6.1/R6.2；2026-07-21 複驗仍 864 綠）**；integration 151 passed/1 failed（唯一 failed=test_facet_entry_routing「帳單為什麼發不出去」路由，KB row id=3495 既有 seed 造成、與本案零程式交集，屬 billing 域另案）；`make audit` 不變量 1/2/5/6 PASS，不變量 3 FAIL＝baked-image drift（部署 rebuild 自解，runbook §14 已註），不變量 4 WARN＝修繕報修免脈絡（既有預期）；runbook §14＋驗收 SQL 落地。**憑印象 vs 查庫對照已留檔（kb-comparison-r63.md，2026-07-21 真 LLM 實測 3 題）**：查庫 3/3 hit、與 KB 一致；憑印象在歸屬題斷言「通常由房東負擔」（幻覺風險實證）；岔題輪延遲增量約 +3.3s（dev 樣本 3，prod P90 以 §14-5 SQL 為準）。dev 庫已套 search_kb_status migration。**剩（使用者執行）：prod 部署（1 加性 migration＋rebuild，runbook §14）＋prod 驗收 SQL（R5.2/R5.3）**。：既有全測試綠（FAQ 快路徑/診斷面向/無岔題交易面向/表單流程零回歸，R6.1）；無岔題 A 類情境 ≤3 輪不退步（R6.4）；`make audit` 全綠；R5.2/R5.3 驗收 SQL 實跑（design 資料模型節：call_rate/hit_rate／工具輪 vs 一般輪 P90 增量 ≤3s 目標）；費用/規定實測集「憑印象 vs 查庫」對照留檔（R6.3，供 B 區價值判定與 A 區評估）；runbook 增補本案節（部署順序：search_kb_status migration→推程式；無 embedding/semantic-model 重建；可選 SEARCH_KB_ENABLED 開關；redis 檢索快取沿用既有清法）。
  - 需求：4.3, 5.3, 6.1, 6.2, 6.3, 6.4

---
## 需求覆蓋對照

| 需求 | 任務 |
|---|---|
| 1.1 | 2.1, 3.2 |
| 1.2 | 2.1 |
| 1.3 | 2.1 |
| 1.4 | 2.1 |
| 2.1 | 3.1 |
| 2.2 | 3.1 |
| 2.3 | 3.1 |
| 3.1 | 3.2, 4.1 |
| 3.2 | 3.2, 4.1 |
| 3.3 | 3.2 |
| 4.1 | 3.1, 4.1 |
| 4.2 | 2.1 |
| 4.3 | 4.2 |
| 4.4 | 3.1 |
| 5.1 | 1.1 |
| 5.2 | 1.1, 3.1 |
| 5.3 | 4.2 |
| 6.1 | 4.2 |
| 6.2 | 2.2, 4.2 |
| 6.3 | 4.1, 4.2 |
| 6.4 | 4.2 |

---
## 實作收案註記（2026-07-20）

- **生產碼全落地**：1.1 計量欄位＋hook｜2.1 `conversational_step` 改 async＋`_brain_tool_loop`（tools/tool_choice 透傳既有 llm_provider，raw_response.tool_calls 解析）｜3.1 引擎 `_make_kb_search` closure＋呼叫點 await＋`_tx` gate＋`SEARCH_KB_ENABLED`｜3.2 prompt tool_note（gated on kb_search，None 路徑逐字不變）。
- **測試綠**：unit 全套 864 passed/0 failed（獨立驗證，基線 836＋28 新測，零 skip/xfail 掩蓋）；新增 brain-kb 工具圈 unit 13＋metering unit 18＋整合 4（真 retriever×closure，host.docker.internal 接 running services）。
- **async 遷移（2.2）**：27 檔（18 unit＋9 integration 假替身）由 mech-executor 機械遷移，規則 A（await）/B（AsyncMock）/C（async def＋kb_search=None），無斷言弱化。
- **integration 唯一 failed 非本案**：test_facet_entry_routing「帳單為什麼發不出去」sim=0.999 進 billing 診斷面向，KB row id=3495 既有 seed 造成；該測試零 LLM、重演 retriever＋config_for_category 路由，與本案改動檔（engine/optimizer/metering）零交集——billing 域 seed 調校另案。
- **make audit**：不變量 1/2/5/6 PASS；不變量 3 FAIL＝baked-image drift（本案改的 engine/optimizer/metering 容器未 rebuild，部署自解）；不變量 4 WARN＝修繕報修交易面向免脈絡（既有預期，同 §13）。
- **migration 位置**：`rag-orchestrator/database/migrations/20260720_usage_events_search_kb_status.sql`（＋rollback），加性可空、向後相容、部署順序皆安全。
- **未 commit／未 push**（照 commit 紀律待使用者指示）。

## 收案補記（2026-07-21）

- **4.1 e2e 真跑收綠**：1 passed（真 LLM＋真檢索＋mock JGB，dev compose）。過程修 2 缺陷：①dev 庫未套 search_kb_status migration（已套，加性冪等）；②e2e 檔＋runbook §14-3 trigger_facet_key 筆誤 `repair`→`repair_create`（DB config registry 的正確鍵；錯鍵時防呆落回既有管線、根本沒進面向）。
- **4.2 對照留檔收案**：`kb-comparison-r63.md`——查庫 3/3 hit 且與 KB（id 2968/2966）一致；憑印象在「房東出還是我出」斷言「通常由房東負擔」＝幻覺風險實證、時程題錯引租客直接聯繫修繕公司；延遲增量約 +3.3s（dev 樣本 3，prod P90 待 §14-5 驗收 SQL）。
- **程式收案完成（9/9）**；剩 prod 部署＋prod 驗收 SQL（使用者依 runbook §14 執行）。

掛帳（不阻塞本 spec 程式收案）：
- **A 區（進場路由 agent 化）** 前置於回測現代化，另案；本案 R5.2/R6.3 產出的呼叫率/命中率/事實一致性數據供其評估。
- **知識內容缺口**：實測發現費用/規定岔題無可命中知識時，走既有知識營運/審核流程補建，不阻塞本案程式收案。
- **多工具擴充**（SOP/lookup/API 工具）：本案工具圈框架可複用，另案。
- **prod 部署**：search_kb_status migration 為加性可空，非破壞性；由使用者依 runbook 執行。
