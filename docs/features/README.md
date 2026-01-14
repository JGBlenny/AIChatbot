# 🎯 Features - 功能文檔索引

**最後更新**: 2026-01-14
**文件總數**: 20 個功能文件

本目錄包含 AIChatbot 系統所有功能的詳細文檔，包括設計說明、實作指南、使用教學。

---

## 📋 功能分類

### 🤖 AI 核心功能 (6 個)

| 文件 | 說明 | 狀態 |
|------|------|------|
| [INTENT_MANAGEMENT_README.md](./INTENT_MANAGEMENT_README.md) | Intent 意圖管理系統 | ✅ |
| [MULTI_INTENT_CLASSIFICATION.md](./MULTI_INTENT_CLASSIFICATION.md) | 多意圖分類功能 | ✅ |
| [MULTI_INTENT_SCORING.md](./MULTI_INTENT_SCORING.md) | 多意圖評分機制 | ✅ |
| [AI_KNOWLEDGE_GENERATION_FEATURE.md](./AI_KNOWLEDGE_GENERATION_FEATURE.md) | AI 自動知識生成 | ✅ |
| [INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md](./INTENT_SUGGESTION_SEMANTIC_DEDUP_IMPLEMENTATION.md) | Intent 建議語意去重 | ✅ |
| [SOP_Group_Embedding_Optimization.md](./SOP_Group_Embedding_Optimization.md) | SOP 分組 Embedding 優化 | ✅ |

### 📚 知識庫管理 (4 個)

| 文件 | 說明 | 狀態 |
|------|------|------|
| [KNOWLEDGE_IMPORT_FEATURE.md](./KNOWLEDGE_IMPORT_FEATURE.md) | 知識匯入功能 | ✅ |
| [MULTI_FILE_IMPORT.md](./MULTI_FILE_IMPORT.md) | 多檔案批次匯入 | ✅ |
| [LINE_CHAT_IMPORT_FINAL_SUMMARY.md](./LINE_CHAT_IMPORT_FINAL_SUMMARY.md) | LINE 對話匯入（完整優化） | ✅ |
| [DOCUMENT_CONVERTER.md](./DOCUMENT_CONVERTER.md) | 文件轉換功能（Word/PDF → Q&A） | ✅ |
| [PRIORITY_SYSTEM.md](./PRIORITY_SYSTEM.md) | 知識優先級系統 | ✅ |

### 📋 表單系統 (2 個)

| 文件 | 說明 | 狀態 |
|------|------|------|
| [FORM_MANAGEMENT_SYSTEM.md](./FORM_MANAGEMENT_SYSTEM.md) | 動態表單收集系統（完整） | ✅ |
| [FORM_GUIDANCE_IMPROVEMENT_2026-01-13.md](./FORM_GUIDANCE_IMPROVEMENT_2026-01-13.md) | 表單引導改善 | ✅ |

### 🧪 測試管理 (3 個)

| 文件 | 說明 | 狀態 |
|------|------|------|
| [TEST_SCENARIO_STATUS_MANAGEMENT.md](./TEST_SCENARIO_STATUS_MANAGEMENT.md) | 測試情境狀態管理 | ✅ |
| [DUPLICATE_TEST_SCENARIO_PREVENTION.md](./DUPLICATE_TEST_SCENARIO_PREVENTION.md) | 重複測試情境防止 | ✅ |
| [REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md](./REJECTED_SCENARIO_RETRY_IMPLEMENTATION.md) | 被拒情境重試機制 | ✅ |

### 🔐 系統管理 (3 個)

| 文件 | 說明 | 狀態 |
|------|------|------|
| [AUTH_SYSTEM_README.md](./AUTH_SYSTEM_README.md) | 認證系統說明 | ✅ |
| [PERMISSION_SYSTEM_README.md](./PERMISSION_SYSTEM_README.md) | 權限系統（RBAC） | ✅ |
| [B2B_API_INTEGRATION.md](./B2B_API_INTEGRATION.md) | B2B API 整合 | ✅ |

---

## 🌟 重點功能推薦

### 對管理員

1. **[FORM_MANAGEMENT_SYSTEM.md](./FORM_MANAGEMENT_SYSTEM.md)** - 建立動態表單，AI 引導填寫
2. **[DOCUMENT_CONVERTER.md](./DOCUMENT_CONVERTER.md)** - 批次將 Word/PDF 轉為 Q&A 知識
3. **[PERMISSION_SYSTEM_README.md](./PERMISSION_SYSTEM_README.md)** - 角色權限管理

### 對開發者

1. **[INTENT_MANAGEMENT_README.md](./INTENT_MANAGEMENT_README.md)** - 理解 Intent 系統架構
2. **[MULTI_INTENT_CLASSIFICATION.md](./MULTI_INTENT_CLASSIFICATION.md)** - 多意圖分類實作
3. **[AUTH_SYSTEM_README.md](./AUTH_SYSTEM_README.md)** - JWT 認證系統

### 對知識維護者

1. **[LINE_CHAT_IMPORT_FINAL_SUMMARY.md](./LINE_CHAT_IMPORT_FINAL_SUMMARY.md)** - 從 LINE 對話匯入知識
2. **[KNOWLEDGE_IMPORT_FEATURE.md](./KNOWLEDGE_IMPORT_FEATURE.md)** - Excel/JSON 批次匯入
3. **[PRIORITY_SYSTEM.md](./PRIORITY_SYSTEM.md)** - 設定知識優先級

---

## 📚 詳細功能說明

### 表單管理系統 ⭐ 推薦

**文件**: [FORM_MANAGEMENT_SYSTEM.md](./FORM_MANAGEMENT_SYSTEM.md)

完整的動態表單系統，支援：
- 📝 管理員建立自訂表單（JSON Schema）
- 🤖 AI 聊天引導使用者逐欄填寫
- ✅ 欄位驗證（正則、必填、類型）
- 📊 提交記錄審核與編輯
- 💾 會話狀態管理

**使用情境**: 租戶報修單、租金繳款單、退租申請

---

### 文件轉換功能 ⭐ 推薦

**文件**: [DOCUMENT_CONVERTER.md](./DOCUMENT_CONVERTER.md)

AI 自動將 Word/PDF 文件轉為 Q&A 知識庫：
- 📄 支援 `.docx`, `.pdf`, `.txt`
- 🤖 OpenAI GPT 自動拆分問答
- 💰 成本估算（Token 計算）
- 👁️ 預覽與審核機制
- ✅ 批次確認入庫

**使用情境**: SOP 文件、FAQ 文件、政策文件批次轉換

---

### LINE 對話匯入 ⭐ 推薦

**文件**: [LINE_CHAT_IMPORT_FINAL_SUMMARY.md](./LINE_CHAT_IMPORT_FINAL_SUMMARY.md)

從 LINE 對話記錄提取知識與測試情境：
- 📱 LINE 對話格式解析
- 🧠 AI 自動分類（測試情境 vs 知識）
- 🔄 分段處理長對話（避免 Token 限制）
- ⚡ 自動速率限制處理
- 📊 前端結果顯示

**最後更新**: 2025-11-25

---

### 多意圖分類系統

**主文件**: [MULTI_INTENT_CLASSIFICATION.md](./MULTI_INTENT_CLASSIFICATION.md)
**評分機制**: [MULTI_INTENT_SCORING.md](./MULTI_INTENT_SCORING.md)

支援單一問題匹配多個意圖：
- 🎯 主要意圖 + 次要意圖
- 📊 差異化加成（1.5x / 1.2x）
- 🔍 Intent 過濾 + 向量相似度
- 🧠 OpenAI 意圖分類

---

### Intent 管理系統

**文件**: [INTENT_MANAGEMENT_README.md](./INTENT_MANAGEMENT_README.md)

完整的 Intent 管理：
- 📝 CRUD 操作
- 🔍 向量搜尋（pgvector）
- 🔗 知識關聯（多對多）
- 🎯 Intent 建議引擎

---

### 權限系統（RBAC）

**文件**: [PERMISSION_SYSTEM_README.md](./PERMISSION_SYSTEM_README.md)

完整的角色權限管理：
- 👥 角色管理（Role）
- 🔐 權限管理（Permission）
- 👤 管理員角色關聯
- 🎯 細粒度權限控制

---

### 認證系統

**文件**: [AUTH_SYSTEM_README.md](./AUTH_SYSTEM_README.md)

JWT Token 認證系統：
- 🔑 登入/登出
- 🔄 Token 刷新
- 🔐 密碼加密（bcrypt）
- ⏰ Session 管理

---

## 🔗 相關資源

- [主項目 README](../../README.md)
- [API 參考文件](../api/API_REFERENCE_KNOWLEDGE_ADMIN.md)
- [系統架構](../architecture/SYSTEM_ARCHITECTURE.md)
- [快速開始指南](../guides/QUICKSTART.md)

---

## 📝 新增功能文件指南

### 文件命名規範

- 使用全大寫 + 底線：`FEATURE_NAME.md`
- 包含功能關鍵字：`FORM_`, `INTENT_`, `AUTH_` 等
- 完整文件加 `_SYSTEM` 或 `_FEATURE` 後綴

### 必須包含的章節

1. **概述** - 功能簡介、使用情境
2. **功能特色** - 核心功能列表
3. **系統架構** - 前後端互動、資料流
4. **API 端點** - 完整 API 文件
5. **使用指南** - 操作步驟、範例
6. **資料庫設計** - 相關資料表
7. **故障排除** - 常見問題

### 更新索引

新增功能文件後，請更新本 README.md 索引。

---

**維護者**: Claude Code
**建立日期**: 2026-01-14
**下次檢查**: 每次新增功能文件時更新
