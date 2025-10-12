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

- [多意圖分類](features/MULTI_INTENT_CLASSIFICATION.md) - 支援一個問題多個意圖
- [意圖管理](features/INTENT_MANAGEMENT_README.md) - 意圖系統說明
- [知識匯入](features/KNOWLEDGE_IMPORT_FEATURE.md) - LINE 對話匯入功能
- [AI 知識生成](features/AI_KNOWLEDGE_GENERATION_FEATURE.md) - 自動生成知識
- [測試場景防重複](features/DUPLICATE_TEST_SCENARIO_PREVENTION.md) - 避免重複測試
- [測試場景狀態管理](features/TEST_SCENARIO_STATUS_MANAGEMENT.md) - 場景生命週期

### 📘 使用指南

- [Docker Compose 指南](guides/DOCKER_COMPOSE_GUIDE.md) - 容器部署
- [開發工作流程](guides/DEVELOPMENT_WORKFLOW.md) - 開發最佳實踐
- [前端開發模式](guides/FRONTEND_DEV_MODE.md) - 前端熱重載開發
- [環境變數參考](guides/ENVIRONMENT_VARIABLES.md) - 完整環境變數說明 ⭐ NEW
- [知識提取指南](guides/KNOWLEDGE_EXTRACTION_GUIDE.md) - 從對話提取知識
- [回測優化指南](guides/BACKTEST_OPTIMIZATION_GUIDE.md) - 提升系統效能

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

- **部署系統** → [快速開始](../QUICKSTART.md)
- **調用 API** → [API 參考](api/API_REFERENCE_PHASE1.md)
- **添加新意圖** → [意圖管理](features/INTENT_MANAGEMENT_README.md)
- **匯入 LINE 對話** → [知識匯入](features/KNOWLEDGE_IMPORT_FEATURE.md)
- **運行回測** → [回測快速開始](BACKTEST_QUICKSTART.md)
- **優化知識庫** → [回測知識優化](backtest/BACKTEST_KNOWLEDGE_OPTIMIZATION_GUIDE.md)
- **開發新功能** → [開發工作流程](guides/DEVELOPMENT_WORKFLOW.md)

## 📊 系統報告

- [系統盤查報告 (2025-10-13)](SYSTEM_AUDIT_REPORT_2025-10-13.md) - 最新系統健康檢查
- [審計清理完成報告 (2025-10-13)](AUDIT_CLEANUP_COMPLETION_REPORT.md) - 系統清理執行結果 ⭐ NEW
- [業務範圍重構總結](BUSINESS_SCOPE_REFACTORING_SUMMARY.md)
- [文檔更新總結](DOCUMENTATION_UPDATE_SUMMARY.md)

## 🆘 需要幫助？

1. **查看主 README**: [../README.md](../README.md)
2. **查看部署文檔**: [../README_DEPLOYMENT.md](../README_DEPLOYMENT.md)
3. **查看變更日誌**: [../CHANGELOG.md](../CHANGELOG.md)

---

**文檔更新日期**: 2025-10-13
**維護者**: 開發團隊
