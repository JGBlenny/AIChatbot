# 變更日誌 (Changelog)

本文檔記錄 AIChatbot 專案的所有重要變更。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

### 規劃中
- Phase 2: 外部 API 整合框架
- 租客身份識別系統
- 資料查詢 API（租約、帳務）
- 操作執行 API（報修、預約）

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
**最後更新**: 2025-10-11
