# 系統整理執行摘要

**日期**: 2025-10-12
**完整報告**: [SYSTEM_CLEANUP_REPORT.md](./SYSTEM_CLEANUP_REPORT.md)

---

## 核心發現

### 🔴 需立即處理

1. **資料庫重複數據** - test_scenarios 表有 5 組重複記錄
2. **文檔散亂** - 根目錄有 18 個 .md 文件，應保留 7 個
3. **Migration 未版控** - 15 個 migration 文件未追蹤

### 🟡 建議處理

1. **文檔重複** - 回測相關文檔有 11 個重複
2. **備份文件** - 3 個 .backup/.bak 文件未清理
3. **測試腳本散落** - 5 個測試 .py 文件在根目錄

---

## 快速執行指令

### 1️⃣ 清理資料庫（5 分鐘）

```bash
# 備份
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d).sql

# 清理重複（保留最佳狀態的記錄）
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin << 'EOF'
WITH duplicates AS (
  SELECT id, test_question, status,
         ROW_NUMBER() OVER (
           PARTITION BY test_question
           ORDER BY CASE status
             WHEN 'approved' THEN 1
             WHEN 'pending_review' THEN 2
             WHEN 'rejected' THEN 3
           END, created_at ASC
         ) as rn
  FROM test_scenarios
)
DELETE FROM test_scenarios WHERE id IN (
  SELECT id FROM duplicates WHERE rn > 1
);
EOF
```

### 2️⃣ 一鍵整理文件（30 分鐘）

```bash
# 下載並執行整理腳本（見完整報告 Phase 2-5）
cd /Users/lenny/jgb/AIChatbot

# 創建目錄結構
mkdir -p docs/{backtest/archive/{completion_reports,evaluation_reports},archive/{completion_reports,evaluation_reports,fix_reports,design_docs,deprecated_guides},examples/{test_data,extracted_data},guides,features,api,planning}
mkdir -p tests/integration

# 執行整理（詳見 SYSTEM_CLEANUP_REPORT.md 中的腳本）
```

### 3️⃣ 提交變更

```bash
git add .
git commit -m "docs: 系統文件整理與歸檔

- 清理重複的測試場景數據（17→12 條）
- 整合並歸檔文檔（回測、完成報告、評估報告等）
- 刪除 3 個備份文件
- 重組文檔結構（guides, features, api, archive）
- 將 15 個 database migrations 納入版本控制
- 移動 5 個測試腳本至 tests/ 目錄
"
```

---

## 預期改善

| 項目 | 現況 | 整理後 | 改善 |
|------|------|--------|------|
| 根目錄 .md | 18 個 | 7 個 | ⬇️ 61% |
| 測試場景重複 | 5 組 | 0 組 | ✅ 100% |
| 備份文件 | 3 個 | 0 個 | ✅ 清理 |
| Migration 版控 | 0% | 100% | ⬆️ 100% |
| 文檔結構 | 混亂 | 清晰 | ✅ 重組 |

---

## 時間估算

- ⏱️ Phase 1 (資料庫清理): 5 分鐘
- ⏱️ Phase 2 (文件歸檔): 30 分鐘
- ⏱️ Phase 3 (刪除臨時): 10 分鐘
- ⏱️ Phase 4 (Migration): 15 分鐘
- ⏱️ Phase 5 (提交): 5 分鐘

**總計**: ~65 分鐘

---

## 風險評估

### 🔒 安全措施
- ✅ 資料庫備份（Phase 1 前）
- ✅ Git 版本控制（可回滾）
- ✅ 分階段執行（可暫停）

### ⚠️ 潛在風險
- Migration 編號修改可能影響已執行追蹤（低風險，因目前無追蹤機制）
- 文檔路徑變更可能影響外部引用（中風險，建議檢查）

### 🛡️ 緩解措施
- 執行前完整備份
- 分階段提交，易於回滾
- 保留歸檔，不直接刪除重要文檔

---

## 下一步

1. ✅ **審閱完整報告** - [SYSTEM_CLEANUP_REPORT.md](./SYSTEM_CLEANUP_REPORT.md)
2. ⏸️ **執行 Phase 1** - 資料庫清理
3. ⏸️ **執行 Phase 2-4** - 文件整理
4. ⏸️ **執行 Phase 5** - 提交變更
5. ⏸️ **驗證功能** - 確保系統正常運作

---

**需要協助？** 查看完整報告或聯繫開發團隊。
