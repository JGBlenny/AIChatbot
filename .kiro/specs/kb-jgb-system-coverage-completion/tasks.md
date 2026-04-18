# 實作任務：kb-jgb-system-coverage-completion

- [ ] 1. Foundation：基礎設定與環境準備

- [x] 1.1 建立覆蓋率工具目錄結構與共用資料模型
  - 建立 `scripts/kb_system_coverage/` 目錄
  - 定義共用 dataclass：Module、Feature、SystemQuestion、GapItem、CoverageReport、ModuleCoverage、RoleCoverage
  - 建立 `__init__.py` 匯出所有 dataclass
  - 完成後 `from scripts.kb_system_coverage import Module, SystemQuestion, CoverageReport` 可正常匯入
  - _Requirements: 1.1, 1.2, 2.4, 3.4_

- [ ] 1.2 chat.py 新增 role_id 支援
  - VendorChatRequest model 新增 `role_id: Optional[str] = None` 欄位
  - `_handle_api_call` 方法中 session_data 新增 `role_id: request.role_id`
  - 現有 target_user 欄位維持不變（KB 過濾用途與 role_id 資料權限用途分離）
  - 完成後發送含 role_id 的 chat 請求，session_data 中可取得 role_id 值
  - _Requirements: 7.3, 7.4_
  - _Boundary: chat.py_

- [ ] 2. JGB 模組盤點與問題清單（Core）

- [ ] 2.1 ModuleMapper — 從 JGB 程式碼爬梳模組清單
  - 掃描 JGB routes、controllers、views（路徑：/Users/lenny/jgb/project/jgb/jgb2）
  - 識別並整理 16+ 功能模組（物件管理、合約管理、帳務管理、修繕系統、支付金流、IoT 設備、社區管理、大房東管理、委託合約、差額發票、電子簽章、使用者帳號、通知系統等）
  - 每個模組列出子功能，標註適用角色（tenant/landlord/property_manager/major_landlord/agent）與入口（app/admin/both）
  - 完成後產出 `jgb_module_inventory.json`，每個模組包含 module_id、module_name、features 陣列
  - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - _Boundary: ModuleMapper_

- [ ] 2.2 QuestionGenerator — 各角色操作問題清單生成
  - 讀取 jgb_module_inventory.json，依模組×角色組合用 LLM（gpt-4o-mini）生成操作問題
  - 每個模組至少生成三類問題：基本操作、常見疑問、異常處理
  - 每個問題標註 topic_id（{模組縮寫}_{流水號}）、角色、入口、優先級（p0/p1/p2）、query_type（static/dynamic）
  - 完成後產出 `system_questions_checklist.json`，p0 問題優先覆蓋高頻操作情境
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 7.1_
  - _Boundary: QuestionGenerator_

- [ ] 3. JGB API 服務建立（Core）

- [ ] 3.1 JGB API 需求規格定義（基於 JGB 實際 model）
  - 分析 JGB 程式碼中的實際 model 結構：Bill（prepare→ready→payed→complete→expired）、Invoice（not_issued→issued→invalid→allowance）、Contract（ready→inviting→signed→move_in→move_out→history）、Payment（多金流商）、Repair（apply→assign→process→complete→finish→archive）、ExistedLessee
  - 依據各 model 的實際欄位定義 7 個 API 端點規格：路徑、HTTP method、必要參數（role_id + user_id）、選填參數、回應欄位（對應 model 實際欄位）、狀態碼對照表
  - 每個端點包含 mock response 範例資料（正常情境 + 查無資料 + 無權限 等異常情境），假資料欄位與 JGB model 一致
  - 沿用 JGB 現有 External API 模式（X-API-Key 認證、`{success, data, pagination, error}` 格式、ExternalApiKeyWhitelist 權限機制）
  - 撰寫 `docs/api/jgb_external_api_spec.md`，可直接作為 JGB 團隊的開發依據
  - 完成後 API 規格文件中每個端點的回應欄位都能對應到 JGB model 的實際欄位
  - _Requirements: 7.2, 7.3, 7.4, 7.7_
  - _Boundary: JGB API Spec_

- [ ] 3.2 JGBSystemAPI 服務實作（mock 模式）
  - 建立 `rag-orchestrator/services/jgb_system_api.py`
  - 依據 3.1 的 API 規格實作 7 個查詢方法：get_bills、get_invoices、get_contracts、get_contract_checkin_eligibility、get_payments、get_repairs、get_tenant_summary
  - mock 假資料依據 3.1 規格中的 mock response 範例，確保欄位與格式一致
  - 每個方法包含 role_id/user_id 前置驗證——為空時直接回傳降級回答，不發送 API 請求
  - 環境變數 `USE_MOCK_JGB_API` 控制 mock/real 切換；mock 模式回傳預設假資料（含各種狀態組合）
  - API 錯誤或逾時（10 秒）時回傳 `{success: False, error: ..., message: fallback}` 結構
  - 完成後 mock 模式下呼叫任一方法可取得格式正確的回應
  - _Requirements: 7.2, 7.3, 7.4, 7.6, 7.8_
  - _Depends: 3.1_
  - _Boundary: JGBSystemAPI_

- [ ] 3.3 api_call_handler registry 擴充
  - 在 api_call_handler.py 的 `__init__` 中匯入 JGBSystemAPI 並註冊 7 個端點到 api_registry
  - 註冊 key：jgb_bills、jgb_invoices、jgb_contracts、jgb_contract_checkin、jgb_payments、jgb_repairs、jgb_tenant_summary
  - 完成後 api_call_handler.execute_api_call 可路由到 JGBSystemAPI 的對應方法
  - _Requirements: 7.5_
  - _Depends: 3.2_
  - _Boundary: api_call_handler_

- [ ] 3.4 JGB API Mock 模式測試
  - 單元測試 JGBSystemAPI 每個方法的 mock 回傳格式正確性（7 端點 × 正常/異常情境）
  - 測試 role_id/user_id 為空時回傳降級回答，不嘗試發送 HTTP 請求
  - 測試 api_call_handler 路由：傳入 jgb_bills 等端點名稱可正確呼叫 JGBSystemAPI 對應方法
  - 測試 response_template 變數替換：帳單、合約、修繕等模板的欄位替換結果正確
  - 完成後所有 mock 模式測試通過，確認假資料格式與 API 規格一致
  - _Requirements: 7.6, 7.8_
  - _Depends: 3.3_
  - _Boundary: JGBSystemAPI, api_call_handler_

- [ ] 4. 覆蓋缺口分析（Core）

- [ ] 4.1 CoverageAnalyzer — 覆蓋率比對與缺口報告
  - 讀取 system_questions_checklist.json，對每個問題用 embedding similarity 比對現有 knowledge_base 和 vendor_sop_items
  - 標記覆蓋狀態：已由 KB 覆蓋 / 已由 SOP 覆蓋 / 未覆蓋 / 部分覆蓋
  - 識別品質不佳的現有項目（內容 < 50 字、僅「請洽管理師」）標記為「需改善」
  - 依模組×角色雙維度統計覆蓋率百分比
  - 缺口項目區分建議：add_kb / add_sop / improve_existing
  - 完成後產出 `coverage_report.json`，包含 total、covered、uncovered、gaps 陣列
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - _Depends: 2.2_
  - _Boundary: CoverageAnalyzer_

- [ ] 5. KB 內容生成與審核驗證（Core）

- [ ] 5.1 (P) SystemKBGenerator — 靜態系統操作 KB 批量生成
  - 讀取 coverage_report.json 中 recommendation=add_kb 且 query_type=static 的缺口
  - 讀取 jgb_module_inventory.json 作為 LLM 生成上下文，確保內容與實際 JGB 功能一致
  - 使用 gpt-4o-mini 生成 KB：question_summary（≤20 字）、answer（100-500 字，含入口路徑）、keywords、category（模組名稱）、target_user、business_types
  - 品質驗證：長度 ≥ 50 字、無工程術語、含操作入口路徑、語義去重（similarity < 0.85）
  - 寫入 ai_generated_knowledge_candidates 表，狀態 pending_review
  - 完成後 ai_generated_knowledge_candidates 中有新增的系統操作 KB 候選項
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - _Depends: 4.1, 2.1_
  - _Boundary: SystemKBGenerator_

- [ ] 5.2 (P) ApiKBBuilder — 動態查詢 KB 條目建立
  - 讀取 coverage_report.json 中 query_type=dynamic 的缺口
  - 參照 JGB API 規格（docs/api/jgb_external_api_spec.md）取得端點對應與回應欄位
  - 為每個動態查詢問題建立 knowledge_base 條目：action_type='api_call'、api_config（endpoint + params mapping + response_template + fallback_message + combine_with_knowledge=true）
  - 同步在 api_endpoints 表新增或確認對應端點設定
  - 完成後 knowledge_base 中存在 action_type='api_call' 的系統查詢 KB 條目，api_config 指向正確的 JGB 端點
  - _Requirements: 7.5_
  - _Depends: 4.1, 3.1, 3.2_
  - _Boundary: ApiKBBuilder_

- [ ] 5.3 審核 pipeline 相容性驗證
  - 驗證 ai_generated_knowledge_candidates 表可正確接收系統知識的 metadata（source module、topic_id、generation time 寫入 generation_metadata JSONB）
  - 驗證 approve_ai_knowledge_candidate() SQL function 對 scope='global' + category=模組名稱 的 KB 條目可正常同步到 knowledge_base
  - 驗證同步時自動填入 source_type='ai_generated' 與 generation_metadata
  - 驗證向量嵌入自動生成流程正常運作
  - 完成後手動審核一筆系統操作 KB 候選項可正確同步到 knowledge_base 並產生 embedding
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  - _Depends: 5.1_
  - _Boundary: 審核 pipeline_

- [ ] 6. Pipeline 編排（Integration）

- [ ] 6.1 Orchestrator — 多階段 pipeline 編排腳本
  - 建立 `scripts/kb_system_coverage/orchestrator.py`，編排 7 階段 pipeline：P1 Module Mapping → P2 Question Generation → P3 Coverage Analysis → P4 Static KB Generation → P5 API KB Building → P6 Review Pause → P7 Backtest Validation
  - 支援 CLI 參數：--vendor-id、--skip-phases、--batch-size
  - P6 暫停等待人工審核完成後才進入 P7
  - 整合所有離線工具元件（ModuleMapper、QuestionGenerator、CoverageAnalyzer、SystemKBGenerator、ApiKBBuilder）
  - 完成後可執行 `python orchestrator.py --vendor-id=1` 跑完整 pipeline（各階段可獨立 skip）
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1_
  - _Depends: 5.1, 5.2, 5.3_
  - _Boundary: Orchestrator_

- [ ] 7. 驗證（Validation）

- [ ] 7.1 端到端整合測試 — KB 檢索到 API 回答完整流程
  - 測試完整流程：chat 請求（帶 role_id）→ RAG 檢索到 action_type='api_call' 的 KB → 呼叫 JGBSystemAPI mock → response_template 組合回答 → 回傳用戶
  - 驗證 session_data 中 role_id 從前端到 JGBSystemAPI 的完整傳遞鏈
  - 驗證 KB 條目的 api_config 正確觸發對應端點，combine_with_knowledge 正確合併靜態知識與 API 資料
  - 驗證 API 失敗時 fallback_message 正確降級（回傳靜態 KB 回答 + 建議聯繫客服）
  - 完成後模擬用戶問「帳單為什麼沒產生發票」可從 mock API 取得帳單資料並組合成完整回答
  - _Requirements: 7.3, 7.4, 7.5, 7.8_
  - _Depends: 1.2, 3.4, 5.2_
  - _Boundary: chat.py, api_call_handler, JGBSystemAPI, knowledge_base_

- [ ] 7.2 回測驗證 — 系統知識覆蓋率改善
  - 建立系統操作問題測試場景（test_scenarios），keywords 包含模組名稱供分組統計
  - 測試場景需同時包含靜態操作問題（如「怎麼在 APP 繳費」）與動態查詢問題（如「帳單為什麼沒產生發票」，搭配 mock API）
  - 執行完整回測（AsyncBacktestFramework），比較補齊前後 pass_rate 變化
  - 依模組分組統計 pass_rate，標記低於平均的模組為「需優先補強」
  - 沿用 LLM 答案品質判定（yes/partial/no）評估回答品質
  - 完成後產出包含模組分組統計的回測結果摘要，可識別覆蓋率改善幅度
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  - _Depends: 6.1_
  - _Boundary: AsyncBacktestFramework_
