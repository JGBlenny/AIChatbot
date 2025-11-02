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
- [業務範圍重構](architecture/BUSINESS_SCOPE_REFACTORING.md) - 架構演進記錄

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

**Phase 3 新功能** ⭐ NEW:
- [緩存系統指南](features/CACHE_SYSTEM_GUIDE.md) - Redis 三層緩存架構 (問題/向量/RAG 結果)
- [流式聊天指南](features/STREAMING_CHAT_GUIDE.md) - Server-Sent Events (SSE) 即時反饋
- [意圖建議語義去重](features/INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md) - pgvector 語義相似度檢查

**測試與品質**:
- [測試場景防重複](features/DUPLICATE_TEST_SCENARIO_PREVENTION.md) - 避免重複測試
- [測試場景狀態管理](features/TEST_SCENARIO_STATUS_MANAGEMENT.md) - 場景生命週期

### 📘 使用指南

**部署與配置**:
- [Docker Compose 指南](guides/DOCKER_COMPOSE_GUIDE.md) - 容器部署
- [環境變數參考](guides/ENVIRONMENT_VARIABLES.md) - 完整環境變數說明（46 個變數）⭐ 已更新

**開發指南**:
- [開發工作流程](guides/DEVELOPMENT_WORKFLOW.md) - 開發最佳實踐
- [前端開發模式](guides/FRONTEND_DEV_MODE.md) - 前端熱重載開發
- [知識提取指南](guides/KNOWLEDGE_EXTRACTION_GUIDE.md) - 從對話提取知識
- [回測優化指南](guides/BACKTEST_OPTIMIZATION_GUIDE.md) - 提升系統效能

**SOP 系統指南** ⭐ 已整合:
- [SOP 完整指南](SOP_COMPLETE_GUIDE.md) - 系統架構、資料庫、使用方式（完整版）
- [SOP 快速參考](SOP_QUICK_REFERENCE.md) - 5分鐘快速上手（操作卡）

### 🧪 回測系統

- [回測索引](BACKTEST_INDEX.md) - 回測文檔導覽
- [回測快速開始](BACKTEST_QUICKSTART.md) - 5分鐘運行回測
- [回測架構評估](BACKTEST_ARCHITECTURE_EVALUATION.md) - 設計評估
- [回測知識優化](backtest/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md) - 優化知識庫
- [答案合成測試](backtest/ANSWER_SYNTHESIS_TESTING_GUIDE.md) - 測試答案合成
- [回測品質整合](backtest/BACKTEST_QUALITY_INTEGRATION.md) - 品質評估

**回測變更日誌**:
- [Phase 2](BACKTEST_PHASE2_CHANGELOG.md) - 測試場景數據庫化
- [Phase 3](BACKTEST_PHASE3_CHANGELOG.md) - 趨勢分析與視覺化

### 🎯 規劃文檔

- [Phase 1 多業者實作](planning/PHASE1_MULTI_VENDOR_IMPLEMENTATION.md) - 多業者支援規劃
- [Phase 2 規劃](planning/PHASE2_PLANNING.md) - 下一階段計劃

### 🗄️ 歸檔文檔

完成報告、評估報告、廢棄指南等歷史文檔請查看 [archive](archive/) 目錄。

## 🔍 常見任務

### 我想...

**基礎操作**:
- **部署系統** → [快速開始](../QUICKSTART.md)
- **調用 API** → [API 參考](api/API_REFERENCE_PHASE1.md)
- **配置環境變數** → [環境變數參考](guides/ENVIRONMENT_VARIABLES.md)
- **查看資料庫結構** → [Database Schema + ERD](DATABASE_SCHEMA_ERD.md) ⭐ NEW

**知識管理**:
- **添加新意圖** → [意圖管理](features/INTENT_MANAGEMENT_README.md)
- **匯入 LINE 對話** → [知識匯入](features/KNOWLEDGE_IMPORT_FEATURE.md)
- **管理 SOP 項目** → [SOP 完整指南](SOP_COMPLETE_GUIDE.md) ⭐ 已整合
- **快速新增 SOP** → [SOP 快速參考](SOP_QUICK_REFERENCE.md)
- **優化知識庫** → [回測知識優化](backtest/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md)

**性能優化** ⭐ NEW:
- **配置緩存系統** → [緩存系統指南](features/CACHE_SYSTEM_GUIDE.md)
- **使用流式聊天** → [流式聊天指南](features/STREAMING_CHAT_GUIDE.md)
- **避免重複建議** → [意圖建議語義去重](features/INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md)

**開發與測試**:
- **運行回測** → [回測快速開始](BACKTEST_QUICKSTART.md)
- **開發新功能** → [開發工作流程](guides/DEVELOPMENT_WORKFLOW.md)

## 📊 系統報告

**架構與資料庫**:
- [Database Schema + ERD](DATABASE_SCHEMA_ERD.md) - 完整資料庫架構（16 表 + ERD 圖）⭐ NEW
- [系統盤查報告 (2025-10-13)](SYSTEM_AUDIT_REPORT_2025-10-13.md) - 系統健康檢查
- [審計清理完成報告 (2025-10-13)](AUDIT_CLEANUP_COMPLETION_REPORT.md) - 系統清理執行結果

**文檔維護**:
- [文檔審計報告 (2025-10-22)](DOCUMENTATION_AUDIT_2025-10-22.md) - 130+ 文檔盤點與優化建議 ⭐ NEW
- [文檔更新完成報告 (2025-10-22)](DOCUMENTATION_UPDATE_COMPLETION_2025-10-22.md) - 文檔更新執行結果 ⭐ NEW

**Phase 3 增強**:
- [Phase 3 去重增強報告 (2025-10-22)](PHASE3_DEDUPLICATION_ENHANCEMENTS_2025-10-22.md) - 語義去重系統實現 ⭐ NEW

**歷史報告**:
- [業務範圍重構總結](BUSINESS_SCOPE_REFACTORING_SUMMARY.md)
- [文檔更新總結](DOCUMENTATION_UPDATE_SUMMARY.md)

## 🆘 需要幫助？

1. **查看主 README**: [../README.md](../README.md)
2. **查看部署文檔**: [../README_DEPLOYMENT.md](../README_DEPLOYMENT.md)
3. **查看變更日誌**: [../CHANGELOG.md](../CHANGELOG.md)

---

## 🆕 最近更新

### 2025-11-02: SOP 複製與 Embedding 修復 ⭐ NEW
- ✅ **修復 SOP 複製 API**: 自動生成 primary + fallback embeddings
  - [修復報告](SOP_COPY_EMBEDDING_FIX_2025-11-02.md) - 完整問題分析與解決方案
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

**文檔更新日期**: 2025-10-23
**維護者**: 開發團隊
**下次審計**: 2025-11-22
