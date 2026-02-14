# 📚 使用指南索引

**最後更新**: 2026-02-14

本目錄包含 AIChatbot 系統的各類使用指南，已按功能分類便於查找。

---

## 🗂️ 目錄結構

```
guides/
├── getting-started/    # 快速開始 (3 個文件)
├── development/        # 開發相關 (7 個文件)
├── deployment/         # 部署相關 (4 個文件)
├── api/               # API 相關 (3 個文件)
├── features/          # 功能使用 (7 個文件)
├── migration/         # 遷移指南 (2 個文件)
└── reference/         # 快速參考 (3 個文件)
```

---

## 🚀 快速開始

**適合**: 新手入門、快速了解系統

| 文檔 | 說明 | 閱讀時間 |
|------|------|---------|
| [QUICKSTART.md](./getting-started/QUICKSTART.md) | 系統快速入門指南 | 10 分鐘 |
| [USER_MANUAL_NON_TECHNICAL.md](./getting-started/USER_MANUAL_NON_TECHNICAL.md) | 非技術人員使用手冊 | 30 分鐘 |
| [PERMISSION_QUICK_START.md](./getting-started/PERMISSION_QUICK_START.md) | 權限系統快速上手 | 15 分鐘 |

---

## 💻 開發相關

**適合**: 開發人員、需要修改代碼

| 文檔 | 說明 |
|------|------|
| [FRONTEND_DEV_MODE.md](./development/FRONTEND_DEV_MODE.md) | 前端開發模式設置 |
| [FRONTEND_USAGE_GUIDE.md](./development/FRONTEND_USAGE_GUIDE.md) | 前端使用指南 |
| [FRONTEND_VERIFY.md](./development/FRONTEND_VERIFY.md) | 前端驗證步驟 |
| [KNOWLEDGE_EXTRACTION_GUIDE.md](./development/KNOWLEDGE_EXTRACTION_GUIDE.md) | 知識庫提取指南 |
| [MARKDOWN_GUIDE.md](./development/MARKDOWN_GUIDE.md) | Markdown 使用指南 |
| [MARKDOWN_TO_PDF_GUIDE.md](./development/MARKDOWN_TO_PDF_GUIDE.md) | Markdown 轉 PDF 指南 |
| [SIMPLIFICATION_IMPLEMENTATION_GUIDE.md](./development/SIMPLIFICATION_IMPLEMENTATION_GUIDE.md) | 簡化實施指南 |

---

## 🚀 部署相關

**適合**: DevOps、系統管理員

| 文檔 | 說明 |
|------|------|
| [AUTH_DEPLOYMENT_GUIDE.md](./deployment/AUTH_DEPLOYMENT_GUIDE.md) | 認證系統部署指南 |
| [AWS_S3_VIDEO_SETUP.md](./deployment/AWS_S3_VIDEO_SETUP.md) | AWS S3 視頻設置 |
| [ENVIRONMENT_VARIABLES.md](./deployment/ENVIRONMENT_VARIABLES.md) | 環境變量配置完整說明 |
| [PGVECTOR_SETUP.md](./deployment/PGVECTOR_SETUP.md) | pgVector 向量資料庫設置 |

---

## 🔌 API 相關

**適合**: API 開發、後端整合

| 文檔 | 說明 |
|------|------|
| [api-path-conventions.md](./api/api-path-conventions.md) | API 路徑命名規範 |
| [how-to-add-api-endpoints.md](./api/how-to-add-api-endpoints.md) | 如何添加 API 端點 |
| [how-to-add-complete-api.md](./api/how-to-add-complete-api.md) | 如何添加完整 API |

---

## ⚙️ 功能使用

**適合**: 系統使用者、功能配置

| 文檔 | 說明 |
|------|------|
| [CACHE_SYSTEM_GUIDE.md](./features/CACHE_SYSTEM_GUIDE.md) | 快取系統使用指南 |
| [KNOWLEDGE_IMPORT_EXPORT_GUIDE.md](./features/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md) | 知識庫匯入匯出指南 |
| [PERMISSION_SYSTEM_QUICK_GUIDE.md](./features/PERMISSION_SYSTEM_QUICK_GUIDE.md) | 權限系統快速指南 |
| [SOP_EXCEL_IMPORT_GUIDE.md](./features/SOP_EXCEL_IMPORT_GUIDE.md) | SOP Excel 匯入指南 |
| [SOP_GUIDE.md](./features/SOP_GUIDE.md) | SOP 系統完整指南 ⭐ |
| [SOP_OPTIMIZATION_README.md](./features/SOP_OPTIMIZATION_README.md) | SOP 優化說明 |
| [STREAMING_CHAT_GUIDE.md](./features/STREAMING_CHAT_GUIDE.md) | 串流對話功能指南 |

---

## 🔄 遷移指南

**適合**: 系統升級、資料遷移

| 文檔 | 說明 |
|------|------|
| [KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md](./migration/KNOWLEDGE_SCOPE_MIGRATION_GUIDE.md) | 知識庫範圍遷移指南 |
| [TEST_SCENARIOS_MIGRATION_GUIDE.md](./migration/TEST_SCENARIOS_MIGRATION_GUIDE.md) | 測試場景遷移指南 |

---

## 📋 快速參考

**適合**: 日常查詢、速查表

| 文檔 | 說明 |
|------|------|
| [LOOKUP_TABLE_QUICK_REFERENCE.md](./reference/LOOKUP_TABLE_QUICK_REFERENCE.md) | 查找表快速參考 |
| [PRIORITY_QUICK_REFERENCE.md](./reference/PRIORITY_QUICK_REFERENCE.md) | 優先級快速參考 |
| [SOP_QUICK_REFERENCE.md](./reference/SOP_QUICK_REFERENCE.md) | SOP 快速參考 |

---

## 🎯 常見任務導航

### 任務 1: 我是新手，想快速上手系統
1. 閱讀 [QUICKSTART.md](./getting-started/QUICKSTART.md)
2. 如果是非技術人員，閱讀 [USER_MANUAL_NON_TECHNICAL.md](./getting-started/USER_MANUAL_NON_TECHNICAL.md)

### 任務 2: 我要配置 SOP 系統
1. 閱讀 [SOP_GUIDE.md](./features/SOP_GUIDE.md)
2. 參考 [SOP_QUICK_REFERENCE.md](./reference/SOP_QUICK_REFERENCE.md)
3. 如需從 Excel 匯入，參考 [SOP_EXCEL_IMPORT_GUIDE.md](./features/SOP_EXCEL_IMPORT_GUIDE.md)

### 任務 3: 我要部署到生產環境
1. 配置 [ENVIRONMENT_VARIABLES.md](./deployment/ENVIRONMENT_VARIABLES.md)
2. 設置 [PGVECTOR_SETUP.md](./deployment/PGVECTOR_SETUP.md)
3. 參考 README.md 中的 Docker 操作指令

### 任務 4: 我要開發 API
1. 了解 [api-path-conventions.md](./api/api-path-conventions.md)
2. 按照 [how-to-add-api-endpoints.md](./api/how-to-add-api-endpoints.md) 添加端點
3. 或完整流程參考 [how-to-add-complete-api.md](./api/how-to-add-complete-api.md)

### 任務 5: 我要開發前端功能
1. 設置 [FRONTEND_DEV_MODE.md](./development/FRONTEND_DEV_MODE.md)
2. 參考 [FRONTEND_USAGE_GUIDE.md](./development/FRONTEND_USAGE_GUIDE.md)
3. 驗證 [FRONTEND_VERIFY.md](./development/FRONTEND_VERIFY.md)

### 任務 6: 我要匯入知識庫
1. 閱讀 [KNOWLEDGE_IMPORT_EXPORT_GUIDE.md](./features/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md)
2. 如需提取，參考 [KNOWLEDGE_EXTRACTION_GUIDE.md](./development/KNOWLEDGE_EXTRACTION_GUIDE.md)

---

## 📞 相關資源

- **主文檔索引**: [docs/INDEX.md](../INDEX.md) - 任務導向指南
- **技術更新**: [docs/README.md](../README.md) - 技術演進記錄
- **API 文檔**: [docs/api/](../api/) - API 詳細參考
- **功能文檔**: [docs/features/](../features/) - 功能設計文檔

---

**維護者**: AIChatbot Team
**最後更新**: 2026-02-14
**重組日期**: 2026-02-14 (P1 文檔整理)
