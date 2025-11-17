# 變更日誌 (Changelog)

本文檔記錄 AIChatbot 專案的所有重要變更。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

### 新增 ✨
- **知識優先級系統重構** (2025-11-17)
  - 從 0-10 分級制（乘法加成）改為 0/1 開關制（固定加成）
  - 加成方式：`base_similarity + (priority > 0 ? 0.15 : 0)`
  - 前端 UI 改進：
    - ✅ 數字輸入改為 checkbox（更直觀）
    - ✅ 表格顯示優先級標記（☑/☐）
    - ✅ 批量匯入時可統一設定優先級
  - 後端優化：
    - ✅ 知識管理 API 完整支持 priority 欄位（GET/PUT/POST）
    - ✅ 知識匯入支持 `default_priority` 參數
    - ✅ 環境變數：`PRIORITY_BOOST_MULTIPLIER` → `PRIORITY_BOOST`
  - 數據遷移：
    - ✅ 所有 priority > 1 的記錄改為 1
    - ✅ 更新 RAG 引擎公式（4 處 SQL 查詢）
  - 完整測試驗證：
    - ✅ 數據庫 priority 值正確
    - ✅ RAG 加成公式 +0.15 正確應用
    - ✅ 前端 API 功能完整
    - ✅ 批量匯入統一優先級功能正常
  - 修改檔案：
    - `rag-orchestrator/services/rag_engine.py` - RAG 公式修改
    - `knowledge-admin/frontend/src/views/KnowledgeView.vue` - 前端 UI
    - `knowledge-admin/frontend/src/views/KnowledgeImportView.vue` - 匯入優先級選項
    - `knowledge-admin/backend/app.py` - API priority 支持
    - `rag-orchestrator/routers/knowledge_import.py` - 匯入參數
    - `rag-orchestrator/services/knowledge_import_service.py` - 匯入邏輯
    - `.env` & `.env.example` - 環境變數
    - `docker-compose.yml` - 容器配置
  - 完整文檔：[知識優先級系統](docs/features/PRIORITY_SYSTEM.md)

### 修復 🐛
- **Critical: SOP 複製與 Embedding 自動生成修復** (2025-11-02)
  - 修復 SOP 複製 API (`copy_all_templates`) 三個關鍵缺陷：
    1. **Embedding 缺失**: 複製後 `embedding_status` 停留在 'pending'，導致向量檢索失敗
    2. **Embedding 結構錯誤**: 缺少 `group_name` 資訊，無法精準匹配群組語意查詢
    3. **群組結構缺失**: 沒有創建 `vendor_sop_groups`，導致前端無法顯示三層結構
  - 修復內容：
    - ✅ 添加自動 embedding 生成（primary: group_name + item_name, fallback: content）
    - ✅ 自動創建 vendor_sop_groups 並正確映射 group_id
    - ✅ 同步生成確保 API 返回時 embeddings 100% 可用
  - 驗證結果：
    - 28/28 items embeddings 生成成功（100%）
    - 9 個群組正確創建
    - 檢索成功率從 0% → 100%
  - 修復檔案：`rag-orchestrator/routers/vendors.py:1555-1763`
  - 新增工具：`generate_vendor_sop_embeddings.py` 補救腳本
  - 完整報告：[SOP 複製與 Embedding 修復報告](docs/SOP_COPY_EMBEDDING_FIX_2025-11-02.md)

- **業者參數處理優化** (2025-11-02)
  - 修復業者參數在 LLM 答案合成時未正確處理 `display_name` 和 `unit` 資訊
  - 後端保留完整業者參數結構（不只是 value）
  - LLM 參數替換時自動附加單位（如 "5號"、"300元"）
  - 前端優化業者參數顯示：
    - 自動過濾空值參數
    - 支援單位顯示和換行符處理
    - 格式化繳費方式（\n → 、）
  - 修復檔案：
    - `rag-orchestrator/routers/chat.py:402`
    - `rag-orchestrator/services/llm_answer_optimizer.py:501-513`
    - `rag-orchestrator/services/vendor_config_service.py:199-208`
    - `knowledge-admin/frontend/src/views/ChatTestView.vue:159-194`
  - 配置優化：`docker-compose.yml` LLM_SYNTHESIS_TEMP: 0.5 → 0.1（提高參數替換準確性）

- **Critical: Business Types 欄位名稱錯誤修復** (2025-10-29)
  - 修復 `vendor_parameter_resolver.py` 中 `business_type` → `business_types` 欄位名稱錯誤
  - 影響：B2C 模式下通用知識（`business_types: null`）無法被檢索
  - 根本原因：單數/複數欄位名稱不一致，導致空陣列參數並過濾掉所有通用知識
  - 修復檔案：`rag-orchestrator/services/vendor_parameter_resolver.py:272`

- **資料結構鍵值一致性修復** (2025-10-29)
  - 修復 `chat.py` 中 `'title'` → `'question_summary'` 鍵值錯誤
  - 修復 `chat.py` 中移除不存在的 `'category'` 欄位引用
  - 影響：避免 `llm_answer_optimizer.py` 中的 `KeyError: 'question_summary'`
  - 修復檔案：`rag-orchestrator/routers/chat.py:456, 631-633`

### 改進 🔧
- **多意圖獨立信心度評分（Solution A）** (2025-10-29)
  - 改進：副意圖不再使用固定衰減值（0.85），改為 LLM 獨立評分
  - LLM Function Schema 返回結構化物件：`{name: string, confidence: number}`
  - 主意圖與副意圖皆由 LLM 獨立評估信心度（範圍 0-1）
  - 資料庫 `knowledge_intent_mapping.confidence` 直接儲存 LLM 原始信心度
  - 修復檔案：`intent_classifier.py:211-377`, `knowledge_classifier.py:150-190`

- **前端 UI 標準化** (2025-10-29)
  - 統一頁面寬度控制（App.vue 全局設定）
  - 新增全局底部間距 80px（改善內容可見性）
  - 移除知識重新分類頁面的進階設定區塊（245 行）
  - 移除「需意圖分類」統計卡片（未實作功能）
  - 移除審核中心頁面的滾輪滑動行為
  - 修復知識頁面分頁控制項顯示條件
  - 新增統一說明面板組件（InfoPanel.vue）和配置檔案（help-texts.js）

### 資料庫修復
- **一次性信心度資料修復** (Migration 49)
  - 修復現有 86 筆 mapping 記錄的錯誤信心度（69 primary + 17 secondary）
  - 從 `knowledge_base.confidence` 複製到 `knowledge_intent_mapping.confidence`
  - 執行檔案：`database/migrations/49-fix-mapping-confidence.sql`

### 新增 ⭐
- **Target User Config 管理系統** (2025-10-28)
  - 完整的目標用戶配置 CRUD 管理介面
  - 軟刪除機制（is_active）
  - 知識庫可指定多個目標用戶（如：租客、房東、物業管理師）
  - 支援未來用戶身份過濾（需整合用戶登入系統）
  - 管理頁面：`/target-users-config`
  - API 端點：GET/POST/PUT/DELETE `/api/target-users-config`

- **Redis 緩存系統整合** (2025-10-21)
  - 3 層緩存架構：問題緩存、向量緩存、RAG 結果緩存
  - 事件驅動 + TTL 混合失效策略
  - 緩存管理 API：失效、清除、統計、健康檢查
  - Knowledge Admin 自動觸發緩存失效通知
  - 環境變量配置 TTL（CACHE_TTL_QUESTION, CACHE_TTL_VECTOR, CACHE_TTL_RAG_RESULT）

### 改進 🔧
- **配置管理系統優化** (2025-10-28)
  - 移除不必要的 `icon` 欄位（前端顯示、表單輸入、資料庫資料）
  - 移除 `display_order` 排序機制，改用 `ORDER BY id`
  - 簡化 UI 設計，減少技術債
  - 影響範圍：Target User Config、Business Types Config、Category Config
  - 資料庫清理：所有 icon 欄位設為 NULL

- **路由遷移與重定向** (2025-10-28)
  - `/audience-config` 重定向到 `/target-users-config`
  - 移除舊的 Audience Config 頁面
  - 更新導航選單：「受眾配置」→「目標用戶」👥

- **RAG Orchestrator 性能優化**
  - 緩存命中時跳過 RAG 處理，提升響應速度
  - 關聯追蹤：knowledge、intent、vendor 三維度失效管理
  - 完整的事件驅動緩存失效流程

### 文檔
- 新增 [Target User Config 實作完成報告](docs/archive/completion_reports/TARGET_USER_CONFIG_IMPLEMENTATION.md)
- 新增 [配置管理更新摘要](docs/CONFIG_MANAGEMENT_UPDATE_SUMMARY.md)

### 規劃中
- 整合用戶登入/認證系統（啟用 target_user 過濾功能）
- Phase 2: 外部 API 整合框架
- 資料查詢 API（租約、帳務）
- 操作執行 API（報修、預約）
- 考慮移除資料庫中不再使用的欄位（icon, display_order）

---

## [1.5.0] - 2025-10-13

### 新增 ⭐
- **系統審計與清理**
  - 完整系統盤查報告，涵蓋架構、代碼質量、文檔結構
  - 文檔中心創建（docs/README.md），統一導覽 90+ 文檔
  - 遺留代碼歸檔（backend → docs/archive/legacy/）
  - 配置文件清理，移除重複的 .env 文件

### 改進
- **主 README 更新**
  - 新增文檔中心入口
  - 新增系統報告區塊
  - 更新專案狀態表（新增系統審計任務）
  - 更新最新功能說明

### 文檔
- 新增 [系統盤查報告 (2025-10-13)](docs/SYSTEM_AUDIT_REPORT_2025-10-13.md)
- 新增 [文檔中心](docs/README.md) - 完整文檔導覽與分類索引
- 新增 [DEPRECATED.md](docs/archive/legacy/backend/DEPRECATED.md) - 遺留代碼說明

### 系統健康狀況
- ✅ 7 個服務正常運行
- ✅ 代碼質量良好（僅 3 個 TODO）
- ✅ 架構清晰，無重複路由
- ✅ 文檔已重組完成

---

## [1.4.0] - 2025-10-12

### 新增 ⭐
- **知識匯入系統**
  - 支援 Excel/JSON/TXT 批量匯入知識
  - 雙層去重機制：文字精確匹配 + 向量語意相似度（閾值 0.85）
  - AI 自動處理：問題生成、向量嵌入、意圖推薦
  - 自動創建測試情境（B2C 知識）
  - 所有知識進入審核佇列，需人工審核
  - 背景任務處理，支援大量數據匯入

- **測試情境管理系統**
  - 測試題庫資料庫（test_scenarios 表）
  - 測試情境 CRUD API
  - 用戶問題自動轉換（頻率 ≥2 自動創建測試情境）
  - 智能重試機制（被拒絕情境達高頻 ≥5 自動重試）
  - 審核中心統一介面（測試情境、用戶問題、意圖建議、AI 知識候選）
  - AI 知識生成器（從測試情境自動生成知識）

- **Business Scope 重構**
  - 基於 `user_role` 動態決定 B2B/B2C 業務範圍
  - 雙場景支援（customer / staff）
  - 每個業者可同時服務客戶（B2C）和員工（B2B）
  - 移除 `vendor_parameters` 中的 `business_scope` 欄位（簡化架構）

- **回測框架 Phase 2 - 智能測試策略** 📊
  - 三種測試選擇策略：
    - **Incremental（增量）**: 自動選擇新測試、失敗測試、長期未測試（預設 100 個）
    - **Full（完整）**: 測試所有已批准測試（無限制）
    - **Failed Only（僅失敗）**: 只測試低分或高失敗率測試（預設 50 個）
  - 優先級評分系統（新測試 100 分、高失敗率 90 分、低分 85 分、長期未測試 70 分）
  - 統計資訊展示（組成分布、選擇原因）
  - 環境變數配置（BACKTEST_SELECTION_STRATEGY、BACKTEST_INCREMENTAL_LIMIT）
  - 向後相容性（保留所有舊環境變數）
  - 詳見：[回測 Phase 2 變更日誌](docs/backtest/BACKTEST_PHASE2_CHANGELOG.md)

- **回測框架 Phase 3 - 趨勢分析與視覺化** 📈
  - 趨勢分析 API：
    - `/api/backtest/trends/overview` - 趨勢總覽（7/30/90天/全部）
    - `/api/backtest/trends/comparison` - 期間對比分析
    - `/api/backtest/trends/alerts` - 自動品質警報（critical / warning / info）
    - `/api/backtest/trends/metrics/{metric_name}` - 特定指標詳情
  - 前端視覺化界面（/backtest/trends）：
    - 🚨 警報區塊（即時顯示 critical 和 warning）
    - 📊 趨勢摘要卡片（通過率、分數、信心度）
    - 📈 互動式圖表（Chart.js）：通過率趨勢圖、分數與信心度雙軸圖
    - 📊 期間對比分析（當前 vs 前一期間）
  - 自動警報系統：
    - 可配置閾值（通過率、分數、信心度）
    - 三個警報級別（critical / warning / info）
    - 智能建議（根據警報類型提供優化建議）
  - 詳見：[回測 Phase 3 變更日誌](docs/backtest/BACKTEST_PHASE3_CHANGELOG.md)

### 改進
- **前端開發模式**
  - 支援熱重載（Vite HMR）
  - 前端代碼掛載到容器
  - 開發效率大幅提升

- **RAG 問題記錄邏輯**
  - 修復：原先只有 unclear 意圖才記錄問題
  - 改進：所有知識缺口都記錄（不論意圖是否清楚）
  - 雙重記錄：
    - `test_scenarios` 表（主要目的：補充測試案例）
    - `suggested_intents` 表（次要目的：發現新意圖）

### 修復
- 修復 multi-intent 欄位在部分返回路徑為 null 的問題
- 修復 RAG fallback 時未觸發知識缺口記錄的問題
- 修復測試情境未出現在審核中心的問題

### 資料庫變更
- 新增 `test_scenarios` 表（測試題庫）
- 新增 `backtest_runs` 表（回測執行記錄）
- 新增 `backtest_results` 表（回測結果詳情）
- 擴展 `ai_generated_knowledge_candidates` 表（新增 source_test_scenario_id）
- 移除 `vendor_parameters.business_scope` 欄位
- 新增自動創建測試情境觸發器（頻率 ≥2）
- 新增拒絕重試機制（頻率 ≥5）

### 效能提升
- **回測通過率**: 66.67% → 83.33% (+25%)
- **測試時間**: 日常測試節省 80%（使用 incremental 策略）
- **Embedding 快取命中率**: 70-90%（Redis 快取）

### 文檔
- 新增 [知識匯入功能文檔](docs/features/KNOWLEDGE_IMPORT_FEATURE.md)
- 新增 [知識匯入 API 參考](docs/api/KNOWLEDGE_IMPORT_API.md)
- 新增 [測試情境狀態管理](docs/features/TEST_SCENARIO_STATUS_MANAGEMENT.md)
- 新增 [拒絕情境智能重試](docs/features/REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md)
- 新增 [測試情境遷移指南](docs/guides/TEST_SCENARIOS_MIGRATION_GUIDE.md)
- 新增 [Business Scope 重構文檔](docs/architecture/BUSINESS_SCOPE_REFACTORING.md)
- 新增 [認證與業務範圍整合](docs/architecture/AUTH_AND_BUSINESS_SCOPE.md)
- 新增 [Business Scope 測試報告](docs/architecture/BUSINESS_SCOPE_REFACTORING_TEST_REPORT.md)
- 新增 [前端開發模式指南](docs/guides/FRONTEND_DEV_MODE.md)
- 新增 [回測策略指南](docs/backtest/backtest_strategies.md)
- 新增 [環境變數參考](docs/backtest/backtest_env_vars.md)
- 新增 [回測 Phase 2 變更日誌](docs/BACKTEST_PHASE2_CHANGELOG.md)
- 新增 [回測 Phase 3 變更日誌](docs/BACKTEST_PHASE3_CHANGELOG.md)

---

## [1.3.0] - 2025-10-11

### 新增 ⭐
- **多 Intent 分類系統**
  - 支援一個問題同時匹配主要意圖和次要意圖（最多 2 個次要意圖）
  - OpenAI Function Calling 返回 `primary_intent` + `secondary_intents[]`
  - API 響應包含 `all_intents`, `secondary_intents`, `intent_ids` 欄位

- **混合檢索差異化加成策略**
  - 主要 Intent: 1.5x 相似度加成
  - 次要 Intent: 1.2x 相似度加成
  - 其他 Intent: 1.0x（無加成）
  - 日誌使用 ★/☆/○ 標記不同 Intent 的知識

- **回測框架增強**
  - 支援多 Intent 評估邏輯
  - 模糊匹配功能（帳務問題 ≈ 帳務查詢）
  - 清楚標示多意圖匹配情況

### 改進
- **Intent Classifier**
  - 增強的系統提示，指導 LLM 識別多個相關意圖
  - 提供分類範例（租金計算、退租押金等）
  - 從資料庫批次查詢所有意圖 IDs

- **Vendor Knowledge Retriever**
  - `retrieve_knowledge_hybrid()` 新增 `all_intent_ids` 參數
  - SQL 查詢支援多 Intent 陣列匹配
  - 增強的日誌輸出，顯示原始相似度、boost、加成後相似度

- **Chat API Response**
  - `VendorChatResponse` 模型擴展，包含多 Intent 欄位
  - 所有返回路徑確保設置默認值（避免 None）

### 修復
- 修復 `all_intents` 為 None 時的 TypeError
- 修復回測框架處理空 `all_intents` 的邊界情況
- 確保 fallback 路徑正確設置多 Intent 欄位

### 效能提升
- **回測通過率**: 40% → 60% (+50%)
- **平均分數**: 0.56 → 0.62 (+10.7%)
- **「租金如何計算？」案例**: 0.57 (FAIL) → 0.87 (PASS) (+53%)

### 文檔
- 新增 [多 Intent 分類系統完整文檔](docs/MULTI_INTENT_CLASSIFICATION.md)
- 新增 [文檔導覽索引](docs/README.md)
- 更新主 README 反映最新功能
- 更新 API 使用範例

---

## [1.2.0] - 2025-10-10

### 新增
- **Intent 管理 Phase B**
  - 意圖建議引擎（OpenAI 自動分析未知問題）
  - 建議審核機制（人工審核後建立新意圖）
  - 建議合併功能（合併相似建議）

- **知識分類系統**
  - 知識與意圖關聯管理
  - 批量分類功能
  - 分類建議機制

### 改進
- 回測框架優化
- 知識庫質量提升
- 意圖管理介面改進

### 文檔
- 新增 [Intent 管理完成記錄](INTENT_MANAGEMENT_COMPLETE.md)
- 新增 [知識分類完成文檔](docs/KNOWLEDGE_CLASSIFICATION_COMPLETE.md)
- 新增 [回測優化指南](BACKTEST_OPTIMIZATION_GUIDE.md)

---

## [1.1.0] - 2025-10-09

### 新增 - Phase 1: 多業者支援 ⭐

- **業者管理系統**
  - 業者 CRUD API（創建、讀取、更新、刪除）
  - 業者啟用/停用控制
  - 業者統計資訊

- **業者參數配置系統**
  - 四大類參數：帳務、合約、服務、聯絡
  - 參數繼承與覆蓋機制
  - 參數歷史記錄

- **LLM 智能參數注入**
  - 取代傳統模板變數（`{{variable}}`）系統
  - GPT-4o-mini 自動根據業者參數調整答案
  - 智能判斷是否需要替換（當參數與通用值相同時保持原值）

- **多租戶知識隔離**
  - 三層知識範圍：global（全局）、vendor（業者專屬）、customized（客製化）
  - 優先級權重：customized (1000) > vendor (500) > global (100)
  - Scope-first 檢索策略

- **B2C Chat API**
  - `/api/v1/message` 端點
  - 租客對業者的智能客服對話
  - Intent 過濾 + 向量相似度混合檢索
  - RAG fallback 機制

- **管理介面**
  - 業者管理頁面（Vue.js）
  - 業者配置頁面
  - Chat 測試頁面
  - 即時參數預覽

### 資料庫變更
- 新增 `vendors` 表（業者資料）
- 新增 `vendor_configs` 表（業者參數配置）
- 新增 `config_categories` 表（參數分類）
- 擴展 `knowledge_base` 表（新增 `vendor_id`, `scope`, `priority` 欄位）
- 移除模板變數系統相關欄位

### 文檔
- 新增 [Phase 1 多業者實作文檔](docs/PHASE1_MULTI_VENDOR_IMPLEMENTATION.md)
- 新增 [API 參考文檔](docs/API_REFERENCE_PHASE1.md)
- 新增 [前端使用指南](docs/frontend_usage_guide.md)

---

## [1.0.0] - 2025-10-08

### 新增 - RAG Orchestrator 基礎功能

- **意圖分類系統**
  - 11 種意圖類型（知識查詢、資料查詢、操作執行等）
  - OpenAI Function Calling 自動分類
  - 意圖配置管理（YAML + 資料庫）
  - 動態意圖重載

- **RAG 檢索引擎**
  - pgvector 向量相似度搜尋
  - 可配置的相似度閾值（預設 0.65）
  - Top-K 檢索（預設 5）

- **信心度評估系統**
  - 三級評估：high（直接回答）、medium（需確認）、low（轉人工）
  - 綜合評分機制（相似度 60% + 關鍵字匹配 40%）
  - 動態閾值調整

- **未釐清問題管理**
  - 自動記錄低信心度問題
  - 關聯檢索結果保存
  - 待改善問題清單

- **LLM 答案優化** (Phase 3)
  - GPT-4o-mini 優化答案格式和語氣
  - 整合多個知識來源
  - 根據信心度調整答案策略
  - Markdown 格式化輸出

- **Intent 管理 Phase A**
  - Intent CRUD API
  - 訓練語句管理
  - Intent 啟用/停用
  - 業務範圍管理

### 資料庫
- PostgreSQL 16 + pgvector extension
- `intents` 表（意圖定義）
- `intent_training_phrases` 表（訓練語句）
- `conversation_logs` 表（對話記錄）
- `unclear_questions` 表（未釐清問題）
- `business_scope` 表（業務範圍）

### API 端點
- `POST /api/v1/chat` - 智能問答
- `GET /api/v1/conversations` - 對話記錄
- `POST /api/v1/conversations/{id}/feedback` - 用戶反饋
- `GET /api/v1/intents` - 意圖列表
- `POST /api/v1/intents` - 創建意圖
- `GET /api/v1/unclear-questions` - 未釐清問題

### 文檔
- 新增 [系統架構文檔](docs/architecture/SYSTEM_ARCHITECTURE.md)
- 新增 [Intent 管理指南](docs/INTENT_MANAGEMENT_README.md)
- 新增 [Phase 2 規劃文檔](docs/PHASE2_PLANNING.md)

---

## [0.9.0] - 2025-10-07

### 新增 - 知識庫管理系統

- **知識管理後台**（Vue.js 3）
  - Markdown 編輯器（SimpleMDE）
  - 即時預覽
  - 知識 CRUD 操作
  - 分類篩選
  - 搜尋功能

- **知識管理 API**（FastAPI）
  - RESTful API
  - 自動向量更新
  - 批量操作支援

- **Embedding API**
  - 統一向量生成服務
  - Redis 快取（70-90% 成本節省）
  - OpenAI text-embedding-3-small
  - 批量處理支援

### 資料庫
- PostgreSQL + pgvector
- `knowledge_base` 表
- 向量索引優化

### Docker 部署
- docker-compose.yml 配置
- 所有服務容器化
- 網路隔離與通信

---

## [0.5.0] - 2025-10-06

### 新增 - LINE 對話分析

- **LINE 對話處理腳本**
  - 自動解析 LINE 對話記錄（.txt 格式）
  - OpenAI GPT-4o-mini 提取客服 Q&A
  - Excel 輸出（問題、答案、分類、受眾）

- **資料處理流程**
  - 對話分組（依時間間隔）
  - 重複問題過濾
  - 分類標籤化

### 文檔
- 新增 [知識提取指南](docs/KNOWLEDGE_EXTRACTION_GUIDE.md)
- 新增 [Markdown 撰寫指南](docs/MARKDOWN_GUIDE.md)

---

## [0.1.0] - 2024

### 新增
- 專案初始化
- 基礎架構設計
- PostgreSQL + pgvector 環境設置

---

## 變更類型說明

- **新增** (Added): 新功能
- **改進** (Changed): 現有功能的變更
- **棄用** (Deprecated): 即將移除的功能
- **移除** (Removed): 已移除的功能
- **修復** (Fixed): Bug 修復
- **安全** (Security): 安全性更新
- **效能提升** (Performance): 效能改進
- **文檔** (Documentation): 文檔更新

---

**維護者**: Claude Code
**最後更新**: 2025-10-28
