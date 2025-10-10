# AIChatbot 文檔導覽

本目錄包含 JGB 包租代管 AI 客服系統的完整技術文檔。

---

## 📚 文檔目錄

### 🚀 快速開始

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [../QUICKSTART.md](../QUICKSTART.md) | 快速啟動指南 | ✅ 完成 |
| [../README_DEPLOYMENT.md](../README_DEPLOYMENT.md) | 部署指南 | ✅ 完成 |
| [../README.md](../README.md) | 專案主文檔 | ✅ 完成 |

### 🏗️ 系統架構

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [architecture/SYSTEM_ARCHITECTURE.md](./architecture/SYSTEM_ARCHITECTURE.md) | 系統架構文檔 | ✅ 完成 |
| [PHASE2_PLANNING.md](./PHASE2_PLANNING.md) | Phase 2 規劃文檔 | ✅ 完成 |

### 🎯 核心功能

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [MULTI_INTENT_CLASSIFICATION.md](./MULTI_INTENT_CLASSIFICATION.md) | **多 Intent 分類系統** | ✅ 完成 |
| [INTENT_MANAGEMENT_README.md](./INTENT_MANAGEMENT_README.md) | Intent 管理指南 | ✅ 完成 |
| [KNOWLEDGE_CLASSIFICATION_COMPLETE.md](./KNOWLEDGE_CLASSIFICATION_COMPLETE.md) | 知識分類指南 | ✅ 完成 |
| [KNOWLEDGE_EXTRACTION_GUIDE.md](./KNOWLEDGE_EXTRACTION_GUIDE.md) | 知識提取指南 | ✅ 完成 |

### 🧪 測試與優化

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [../BACKTEST_OPTIMIZATION_GUIDE.md](../BACKTEST_OPTIMIZATION_GUIDE.md) | 回測優化指南 | ✅ 完成 |
| [frontend_usage_guide.md](./frontend_usage_guide.md) | 前端使用指南 | ✅ 完成 |

### 🛠️ 技術參考

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [../PGVECTOR_SETUP.md](../PGVECTOR_SETUP.md) | pgvector 安裝指南 | ✅ 完成 |
| [API_REFERENCE_PHASE1.md](./API_REFERENCE_PHASE1.md) | Phase 1 API 參考 | ✅ 完成 |
| [MARKDOWN_GUIDE.md](./MARKDOWN_GUIDE.md) | Markdown 撰寫指南 | ✅ 完成 |

### 📝 完成記錄

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [../INTENT_MANAGEMENT_COMPLETE.md](../INTENT_MANAGEMENT_COMPLETE.md) | Intent 管理完成記錄 | ✅ 完成 |
| [KNOWLEDGE_EXTRACTION_COMPLETION.md](./KNOWLEDGE_EXTRACTION_COMPLETION.md) | 知識提取完成記錄 | ✅ 完成 |
| [intent_management_phase_b_complete.md](./intent_management_phase_b_complete.md) | Intent 管理 Phase B 完成 | ✅ 完成 |
| [../PATH_FIXES_SUMMARY.md](../PATH_FIXES_SUMMARY.md) | 路徑修復摘要 | ⚠️ 可歸檔 |

---

## 🗂️ 按主題導覽

### 新手入門

1. 開始前請先閱讀 [README.md](../README.md) 了解專案概況
2. 按照 [QUICKSTART.md](../QUICKSTART.md) 快速啟動系統
3. 查看 [SYSTEM_ARCHITECTURE.md](./architecture/SYSTEM_ARCHITECTURE.md) 理解系統架構

### Intent 管理

1. [INTENT_MANAGEMENT_README.md](./INTENT_MANAGEMENT_README.md) - Intent 基礎概念
2. [MULTI_INTENT_CLASSIFICATION.md](./MULTI_INTENT_CLASSIFICATION.md) - **多 Intent 分類系統（最新功能）**
3. [INTENT_MANAGEMENT_COMPLETE.md](../INTENT_MANAGEMENT_COMPLETE.md) - Intent 管理完成記錄

### 知識庫管理

1. [KNOWLEDGE_EXTRACTION_GUIDE.md](./KNOWLEDGE_EXTRACTION_GUIDE.md) - 知識提取流程
2. [KNOWLEDGE_CLASSIFICATION_COMPLETE.md](./KNOWLEDGE_CLASSIFICATION_COMPLETE.md) - 知識分類指南
3. [BACKTEST_OPTIMIZATION_GUIDE.md](../BACKTEST_OPTIMIZATION_GUIDE.md) - 回測與優化

### 系統開發

1. [SYSTEM_ARCHITECTURE.md](./architecture/SYSTEM_ARCHITECTURE.md) - 系統架構
2. [API_REFERENCE_PHASE1.md](./API_REFERENCE_PHASE1.md) - API 文檔
3. [PHASE2_PLANNING.md](./PHASE2_PLANNING.md) - Phase 2 規劃

### 部署運維

1. [README_DEPLOYMENT.md](../README_DEPLOYMENT.md) - 部署指南
2. [PGVECTOR_SETUP.md](../PGVECTOR_SETUP.md) - 向量資料庫設置

---

## 🆕 最新更新

### 2025-10-11
- ✅ **新增**：[多 Intent 分類系統文檔](./MULTI_INTENT_CLASSIFICATION.md)
  - 完整的技術實作說明
  - 回測結果從 40% 提升到 60%
  - 差異化檢索策略（1.5x / 1.2x / 1.0x boost）

### 2025-10-10
- ✅ 更新：Intent 管理系統
- ✅ 更新：回測框架支援模糊匹配

---

## 📖 文檔撰寫指南

如需新增或更新文檔，請參考 [MARKDOWN_GUIDE.md](./MARKDOWN_GUIDE.md)。

**文檔撰寫原則**：
1. 使用清晰的標題層級
2. 提供實際範例和代碼片段
3. 包含圖表說明（如適用）
4. 標註文檔狀態和更新時間
5. 提供相關文檔的連結

---

## 🔍 搜尋建議

### 按關鍵字搜尋

- **Intent（意圖）**: INTENT_MANAGEMENT_README.md, MULTI_INTENT_CLASSIFICATION.md
- **Knowledge（知識）**: KNOWLEDGE_EXTRACTION_GUIDE.md, KNOWLEDGE_CLASSIFICATION_COMPLETE.md
- **Backtest（回測）**: BACKTEST_OPTIMIZATION_GUIDE.md, MULTI_INTENT_CLASSIFICATION.md
- **API**: API_REFERENCE_PHASE1.md
- **Architecture（架構）**: SYSTEM_ARCHITECTURE.md
- **Deployment（部署）**: README_DEPLOYMENT.md, QUICKSTART.md

### 按開發階段搜尋

- **Phase 1（多業者支援）**: API_REFERENCE_PHASE1.md, SYSTEM_ARCHITECTURE.md
- **Phase 2（規劃中）**: PHASE2_PLANNING.md
- **Phase 3（LLM 優化）**: SYSTEM_ARCHITECTURE.md

---

## 📞 支援

如有文檔相關問題或建議，請：
1. 檢查本導覽是否有相關文檔
2. 查閱具體文檔的「故障排除」章節
3. 聯繫開發團隊

**文檔維護負責人**：開發團隊
**最後更新時間**：2025-10-11
