# 📦 Archive - 歸檔文件索引

**目的**: 存放已完成階段的歷史文件、舊版本設計文件、過時報告等
**最後更新**: 2026-01-14
**總文件數**: 116 個 (.md 文件)
**佔 docs/ 比例**: 46.2%

---

## 📋 目錄結構

### 版本化歸檔

| 目錄 | 說明 |
|------|------|
| **2026-01-13/** | 2026-01-13 檢索邏輯實施相關文件 |

### 主題分類歸檔

| 目錄 | 說明 |
|------|------|
| **completion_reports/** | 各階段完成報告（最多文件） |
| **cleanup_reports/** | 清理與重構報告 |
| **evaluation_reports/** | 評估與分析報告 |
| **sop_reports/** | SOP 系統相關報告 |
| **auth_testing/** | 認證系統測試文件 |
| **fix_reports/** | 修復報告 |
| **design_research_2025-10/** | 2025-10 設計研究文件 |
| **design_docs/** | 設計文件 |
| **audience_research/** | 目標受眾研究 |
| **sop_guides/** | SOP 指南（舊版） |
| **sop_implementation/** | SOP 實作文件 |
| **api/** | API 舊版文件 |
| **architecture/** | 架構舊版文件 |
| **database_migrations/** | Migration 歷史 |
| **migrations_history/** | Migration 記錄 |
| **backups/** | 備份文件 |
| **planning/** | 規劃文件 |

---

## 🔍 如何使用

### 查找特定主題

1. **完成報告** → `completion_reports/`
2. **清理報告** → `cleanup_reports/`
3. **評估分析** → `evaluation_reports/`
4. **設計研究** → `design_docs/` 或 `design_research_2025-10/`
5. **SOP 相關** → `sop_guides/`, `sop_implementation/`, `sop_reports/`
6. **認證系統** → `auth_testing/`

### 查找特定時期

- **2025-10** → `design_research_2025-10/`, 各目錄中 2025-10 開頭的文件
- **2026-01-13** → `2026-01-13/`

---

## 🗑️ 清理政策

### 保留規則

- ✅ **重要里程碑報告** - 永久保留
- ✅ **設計決策文件** - 永久保留
- ✅ **評估分析報告** - 至少保留 2 年
- ✅ **完成報告** - 至少保留 1 年

### 定期清理

- ⚠️ **每季度審查** - 檢查是否有可刪除的過時文件
- ⚠️ **2024 年以前** - 評估是否需要保留
- ⚠️ **重複文件** - 合併或刪除

### 下次清理建議時間

**2026-04-14** (3 個月後)

---

## 📊 清理歷史

**最後清理**: 2025-10-21
- ❌ `legacy/backend/` - 舊後端代碼（已刪除 152KB）
- ❌ `deprecated_guides/` - 過時指南（已刪除 56KB）
- 🎯 優化比例: 27%

---

## 已歸檔功能

### suggested_knowledge（用戶問題建議）
- **棄用日期：** 2025-10-12
- **原因：** 與 `ai_generated_knowledge_candidates` 功能重複，已合併為統一系統
- **取代方案：** 使用 `ai_generated_knowledge_candidates` 表，並通過 `source_type` 欄位區分來源
  - `source_type = 'test_scenario'`: 來自測試情境
  - `source_type = 'unclear_question'`: 來自用戶問題
  - `source_type = 'manual'`: 手動創建

**相關文檔：**
- [KNOWLEDGE_SUGGESTION_DESIGN.md](./KNOWLEDGE_SUGGESTION_DESIGN.md) - 原始設計文檔
- [KNOWLEDGE_SUGGESTIONS_TEST_REPORT.md](KNOWLEDGE_SUGGESTIONS_TEST_REPORT.md) - 測試報告

**資料庫遷移：**
- 創建：`database/migrations/10-create-suggested-knowledge.sql`
- 移除：`database/migrations/12-remove-suggested-knowledge.sql`
