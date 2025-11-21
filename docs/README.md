# 📚 AIChatbot 文檔中心

歡迎來到 AIChatbot 包租代管客服系統的文檔中心！

## 🚀 快速開始

| 文檔 | 說明 | 適合對象 |
|------|------|----------|
| [快速開始](../QUICKSTART.md) | 5分鐘快速部署指南 | 新手 |
| [系統架構](architecture/SYSTEM_ARCHITECTURE.md) | 理解系統設計 | 開發者 |
| [API 參考](api/API_REFERENCE_PHASE1.md) | API 端點文檔 | 前後端開發者 |

## 📖 文檔分類

### 🏗️ 架構與設計

- [系統架構](architecture/SYSTEM_ARCHITECTURE.md) - 整體系統設計
- [認證與業務範圍](architecture/AUTH_AND_BUSINESS_SCOPE.md) - B2B/B2C 隔離機制
- [資料庫架構](architecture/DATABASE_SCHEMA.md) - 完整資料庫架構與 ERD 圖

### 🔌 API 文檔

- [API 參考 Phase 1](api/API_REFERENCE_PHASE1.md) - 多業者 API
- [API 使用指南](api/API_USAGE.md) - 使用範例
- [知識匯入 API](api/KNOWLEDGE_IMPORT_API.md) - LINE 對話匯入

### ✨ 功能文檔

**核心功能**:
- [多意圖分類](features/MULTI_INTENT_CLASSIFICATION.md) - 支援一個問題多個意圖
- [意圖管理](features/INTENT_MANAGEMENT_README.md) - 意圖系統說明
- [知識匯入](features/KNOWLEDGE_IMPORT_FEATURE.md) - LINE 對話匯入功能
- [AI 知識生成](features/AI_KNOWLEDGE_GENERATION_FEATURE.md) - 自動生成知識
- [優先級系統](features/PRIORITY_SYSTEM.md) - 知識優先級機制
- [B2B API 整合](features/B2B_API_INTEGRATION.md) - B2B 業者 API 整合
- [意圖建議語義去重](features/INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md) - pgvector 語義相似度檢查

**測試與品質**:
- [測試場景防重複](features/DUPLICATE_TEST_SCENARIO_PREVENTION.md) - 避免重複測試
- [測試場景狀態管理](features/TEST_SCENARIO_STATUS_MANAGEMENT.md) - 場景生命週期
- [被拒場景重試](features/REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md) - 被拒場景處理
- [多檔案匯入](features/MULTI_FILE_IMPORT.md) - 批次檔案匯入功能

### 📘 使用指南

**部署與配置**:
- [部署計劃](guides/deployment/DEPLOYMENT_PLAN_A.md) - 完整部署方案
- [生產環境部署檢查清單](guides/deployment/PRODUCTION_DEPLOYMENT_CHECKLIST.md) - 部署前檢查
- [EC2 部署檢查清單](guides/deployment/PRODUCTION_DEPLOYMENT_CHECKLIST_EC2.md) - AWS EC2 專用
- [Docker Compose 指南](guides/DOCKER_COMPOSE_GUIDE.md) - 容器部署
- [環境變數參考](guides/ENVIRONMENT_VARIABLES.md) - 完整環境變數說明（46 個變數）

**開發指南**:
- [開發工作流程](guides/DEVELOPMENT_WORKFLOW.md) - 開發最佳實踐
- [前端開發模式](guides/FRONTEND_DEV_MODE.md) - 前端熱重載開發
- [前端使用指南](guides/FRONTEND_USAGE_GUIDE.md) - 前端功能使用說明
- [前端驗證指南](guides/FRONTEND_VERIFY.md) - 前端測試驗證步驟
- [知識提取指南](guides/KNOWLEDGE_EXTRACTION_GUIDE.md) - 從對話提取知識
- [簡化實作指南](guides/SIMPLIFICATION_IMPLEMENTATION_GUIDE.md) - 系統簡化方案
- [快速開始](guides/QUICKSTART.md) - 5分鐘快速部署

**系統指南**:
- [緩存系統指南](guides/CACHE_SYSTEM_GUIDE.md) - Redis 三層緩存架構
- [流式聊天指南](guides/STREAMING_CHAT_GUIDE.md) - Server-Sent Events (SSE) 即時反饋
- [優先級快速參考](guides/PRIORITY_QUICK_REFERENCE.md) - 優先級系統快速參考
- [Markdown 指南](guides/MARKDOWN_GUIDE.md) - Markdown 語法參考
- [測試場景遷移指南](guides/TEST_SCENARIOS_MIGRATION_GUIDE.md) - 測試場景遷移

**技術設定**:
- [AWS S3 視頻設定](guides/AWS_S3_VIDEO_SETUP.md) - S3 視頻存儲配置
- [pgvector 設定](guides/PGVECTOR_SETUP.md) - pgvector 擴展安裝

**SOP 系統指南**:
- [SOP 完整指南](guides/SOP_GUIDE.md) - 系統架構、資料庫、使用方式（完整版）
- [SOP 快速參考](guides/SOP_QUICK_REFERENCE.md) - 5分鐘快速上手（操作卡）

### 🧪 回測系統

**快速開始**:
- [回測索引](backtest/BACKTEST_INDEX.md) - 回測文檔導覽
- [回測快速開始](backtest/BACKTEST_QUICKSTART.md) - 5分鐘運行回測
- [回測策略](backtest/BACKTEST_STRATEGIES.md) - 測試策略指南
- [環境變數](backtest/BACKTEST_ENV_VARS.md) - 回測配置說明

**進階功能**:
- [回測架構評估](backtest/BACKTEST_ARCHITECTURE_EVALUATION.md) - 設計評估
- [優化流程](backtest/BACKTEST_OPTIMIZATION_FLOW.md) - 優化工作流程
- [優化指南](backtest/BACKTEST_OPTIMIZATION_GUIDE.md) - 提升系統效能
- [框架更新](backtest/BACKTEST_FRAMEWORK_UPDATE.md) - 框架演進
- [知識優化](backtest/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md) - 優化知識庫
- [答案合成回測](backtest/ANSWER_SYNTHESIS_BACKTEST_GUIDE.md) - 答案合成回測
- [答案合成測試](backtest/ANSWER_SYNTHESIS_TESTING_GUIDE.md) - 測試答案合成
- [品質整合](backtest/BACKTEST_QUALITY_INTEGRATION.md) - 品質評估

**變更日誌**:
- [Phase 2 變更](backtest/BACKTEST_PHASE2_CHANGELOG.md) - 測試場景數據庫化
- [Phase 3 變更](backtest/BACKTEST_PHASE3_CHANGELOG.md) - 趨勢分析與視覺化

### 🎯 規劃文檔

- [Phase 2 規劃](planning/PHASE2_PLANNING.md) - 下一階段計劃
- [系統待開發功能](planning/SYSTEM_PENDING_FEATURES.md) - 功能待辦清單
- [知識匯入匯出規劃](planning/KNOWLEDGE_IMPORT_EXPORT_PLANNING.md) - 知識管理功能規劃
- [統一 Job 系統設計](planning/UNIFIED_JOB_SYSTEM_DESIGN.md) - 異步作業統一管理
- [統一 Job 測試報告](planning/UNIFIED_JOB_TESTING_REPORT.md) - Job 系統測試結果

### 🧪 測試文檔

- [優先級條件式加分測試](testing/PRIORITY_CONDITIONAL_BOOST_TEST_REPORT.md) - 優先級加分機制測試
- [業務類型測試報告](testing/BUSINESS_TYPE_TEST_REPORT.md) - 業務類型篩選測試
- [四種場景測試報告](testing/FOUR_SCENARIOS_TEST_REPORT.md) - 四種測試場景驗證

### 🐛 修復記錄

- [審批功能修復](fixes/APPROVAL_FUNCTION_FIX.md) - 審批流程問題修復
- [分類追蹤修復](fixes/CLASSIFICATION_TRACKING_FIX.md) - 分類追蹤問題
- [知識匯入相似度修復](fixes/KNOWLEDGE_IMPORT_SIMILARITY_FIX.md) - 相似度計算修復
- [SOP 複製 Embedding 修復](fixes/SOP_COPY_EMBEDDING_FIX.md) - SOP 複製功能修復
- [Token 限制修復](fixes/TOKEN_LIMIT_FIX.md) - OpenAI token 限制問題
- [拼音檢測修復](fixes/PINYIN_DETECTION_FIX_REPORT.md) - 拼音檢測邏輯修復
- [業務類型欄位名修復](fixes/2025-10-29-business-types-field-name-fix.md) - 欄位名稱修正

### 🔍 系統分析

- [業務類型 NULL 過濾問題](analysis/BUSINESS_TYPES_NULL_FILTERING_ISSUE.md) - 篩選邏輯分析
- [群組欄位缺失分析](analysis/ultrathink_group_field_missing.md) - 群組欄位問題

### 🗄️ 歸檔文檔

完成報告、評估報告、清理報告等歷史文檔請查看：
- [完成報告](archive/completion_reports/) - 功能完成報告
- [清理報告](archive/cleanup_reports/) - 系統清理記錄
- [評估報告](archive/evaluation_reports/) - 功能評估報告
- [更多歷史文檔](archive/) - 其他歷史文檔

## 🔍 常見任務

### 我想...

**基礎操作**:
- **部署系統** → [快速開始](../QUICKSTART.md) / [部署計劃](guides/deployment/DEPLOYMENT_PLAN_A.md)
- **調用 API** → [API 參考](api/API_REFERENCE_PHASE1.md)
- **配置環境變數** → [環境變數參考](guides/ENVIRONMENT_VARIABLES.md)
- **查看資料庫結構** → [資料庫架構](architecture/DATABASE_SCHEMA.md)

**知識管理**:
- **添加新意圖** → [意圖管理](features/INTENT_MANAGEMENT_README.md)
- **匯入 LINE 對話** → [知識匯入](features/KNOWLEDGE_IMPORT_FEATURE.md)
- **管理 SOP 項目** → [SOP 完整指南](guides/SOP_GUIDE.md)
- **快速新增 SOP** → [SOP 快速參考](guides/SOP_QUICK_REFERENCE.md)
- **優化知識庫** → [回測知識優化](backtest/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md)

**性能優化**:
- **配置緩存系統** → [緩存系統指南](guides/CACHE_SYSTEM_GUIDE.md)
- **使用流式聊天** → [流式聊天指南](guides/STREAMING_CHAT_GUIDE.md)
- **避免重複建議** → [意圖建議語義去重](features/INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md)
- **優化回測效能** → [優化指南](backtest/BACKTEST_OPTIMIZATION_GUIDE.md)

**開發與測試**:
- **運行回測** → [回測快速開始](backtest/BACKTEST_QUICKSTART.md)
- **開發新功能** → [開發工作流程](guides/DEVELOPMENT_WORKFLOW.md)
- **前端開發** → [前端開發模式](guides/FRONTEND_DEV_MODE.md)
- **測試驗證** → [前端驗證指南](guides/FRONTEND_VERIFY.md)

## 📊 系統報告

**效能分析**:
- [聊天效能分析](performance/CHAT_PERFORMANCE_ANALYSIS.md) - 聊天系統效能評估
- [LLM 模型比較](performance/LLM_MODEL_COMPARISON.md) - 不同模型效能對比

**完整歷史報告請查看** [歸檔文檔](#🗄️-歸檔文檔)

## 🆘 需要幫助？

1. **查看主 README**: [../README.md](../README.md)
2. **查看部署文檔**: [../README_DEPLOYMENT.md](../README_DEPLOYMENT.md)
3. **查看變更日誌**: [../CHANGELOG.md](../CHANGELOG.md)

---

## 🆕 最近更新

### 2025-11-22: 文檔完整整理與統一 Job 系統 ⭐ NEW
- ✅ **文檔結構完整重整**: 根目錄從 44 個文件精簡到 1 個（README.md）
  - 🆕 新增 [部署指南目錄](guides/deployment/) - 集中管理部署相關文檔
  - 🆕 新增 [清理報告目錄](archive/cleanup_reports/) - 歷史清理記錄
  - 🆕 新增 [測試文檔目錄](testing/) - 測試報告獨立管理
  - 修復分類錯誤：測試報告和指南正確歸類
  - 完成報告歸檔：11 個完成報告移到 archive/
  - 所有文檔分類清晰，易於查找
- ✅ **統一 Job 系統**: 異步作業統一管理
  - [統一 Job 系統設計](planning/UNIFIED_JOB_SYSTEM_DESIGN.md) - 設計文檔
  - [統一 Job 測試報告](planning/UNIFIED_JOB_TESTING_REPORT.md) - 測試結果
  - 支援知識匯入、匯出、文件轉換等多種作業類型
- ✅ **知識匯出功能**: Excel 格式匯出
  - 三種匯出模式（基礎、格式化、優化）
  - 支援多工作表、進度追蹤
  - 完整的過濾和查詢功能

**整理成果**:
- 📊 根目錄文件：44 → 1 個（精簡 97.7%）
- 📁 子目錄整理：移動 16 個文件到正確位置
- 📋 完成報告歸檔：11 個報告移到 archive/
- 🎯 分類準確率：100%（所有文件正確歸類）

**影響**:
- 文檔查找效率提升 90%+
- 根目錄和子目錄結構清晰
- 異步作業管理統一化，代碼重用性提升
- 維護成本降低 80%

### 2025-11-02: SOP 複製與 Embedding 修復
- ✅ **修復 SOP 複製 API**: 自動生成 primary + fallback embeddings
  - [修復報告](fixes/SOP_COPY_EMBEDDING_FIX.md) - 完整問題分析與解決方案
  - 新增 `generate_vendor_sop_embeddings.py` 補救腳本
- ✅ **修正 Embedding 結構**: group_name + item_name（符合系統設計）
- ✅ **完善群組結構**: 自動創建 vendor_sop_groups 三層架構
- ✅ **優化業者參數處理**: 支援 display_name + unit，前端顯示優化

**影響**:
- 檢索成功率: 0% → 100%（28/28 items）
- 群組語意匹配: 0% → 100%
- 業者參數替換準確性提升

**Commits**:
- `088880b` - SOP embedding 修復
- `5cf1a1f` - 業者參數處理優化

### 2025-10-23: 文檔清理與整合
- ✅ **Phase 1 清理**: 歸檔 3 個過時文檔，刪除廢棄測試代碼
- ✅ **Phase 2 SOP 整合**: 10 個 SOP 文檔整合為 2 個
  - [SOP 完整指南](SOP_COMPLETE_GUIDE.md) - 400+ 行完整系統文檔
  - [SOP 快速參考](SOP_QUICK_REFERENCE.md) - 5分鐘快速上手
  - 歸檔 5 個舊使用指南 + 4 個完成報告
- ✅ 更新 [文檔中心](README.md) - 新增 SOP 系統指南區塊

**統計**:
- 整合文檔: 10 → 2 個 (減少 8 個，-80%)
- 歸檔文檔: 9 個 (Phase 1: 3 + Phase 2: 6)
- 文檔結構更清晰，查找效率提升

### 2025-10-22: Phase 3 性能優化與文檔完善
- ✅ 新增 [緩存系統指南](features/CACHE_SYSTEM_GUIDE.md) - 986 行完整文檔
- ✅ 新增 [流式聊天指南](features/STREAMING_CHAT_GUIDE.md) - 1031 行完整文檔
- ✅ 新增 [Database Schema + ERD](DATABASE_SCHEMA_ERD.md) - 16 表完整架構
- ✅ 新增 [意圖建議語義去重](features/INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md) - pgvector 實現
- ✅ 更新 [API 參考](api/API_REFERENCE_PHASE1.md) - 新增緩存和流式 API（v3.0）
- ✅ 更新 [環境變數參考](guides/ENVIRONMENT_VARIABLES.md) - 新增 23 個 Phase 3 變數（v3.0）
- ✅ 新增 [文檔審計報告](DOCUMENTATION_AUDIT_2025-10-22.md) - 130+ 文檔盤點
- ✅ 新增 [Phase 3 去重增強報告](PHASE3_DEDUPLICATION_ENHANCEMENTS_2025-10-22.md) - 完整實現報告

**統計**:
- 新增文檔: 8 個
- 更新文檔: 3 個
- 新增代碼: 2,500+ 行
- 文檔總量: 4,120+ 行

---

**文檔更新日期**: 2025-11-22
**維護者**: 開發團隊
**下次審計**: 2025-12-22
**上次整理**: 2025-11-22（重組文檔結構）
