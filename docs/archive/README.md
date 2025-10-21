# 歸檔文檔

此目錄包含已棄用或被取代的功能文檔，保留作為歷史記錄參考。

**最後清理日期**: 2025-10-21
**大小**: 548 KB (已優化 27%)

## 📁 目錄結構

- `completion_reports/` - 功能完成報告（20 個）
- `database_migrations/` - 舊的資料庫遷移參考
- `design_docs/` - 歷史設計文檔
- `evaluation_reports/` - 評估報告
- `fix_reports/` - 問題修復報告

## 🗑️ 已刪除內容

- ❌ `legacy/backend/` - 舊後端代碼（已刪除 152KB）
- ❌ `deprecated_guides/` - 過時指南（已刪除 56KB）

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
- [KNOWLEDGE_SUGGESTIONS_TEST_REPORT.md](../../archive/KNOWLEDGE_SUGGESTIONS_TEST_REPORT.md) - 測試報告

**資料庫遷移：**
- 創建：`database/migrations/10-create-suggested-knowledge.sql`
- 移除：`database/migrations/12-remove-suggested-knowledge.sql`
