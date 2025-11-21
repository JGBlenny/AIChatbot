# Docs 文件整理計劃

**日期**: 2025-11-22
**目的**: 整理 docs 根目錄，建立清晰的文檔結構

---

## 現狀分析

### 📊 統計
- **根目錄文件數**: 44 個 .md 文件
- **子目錄**: 14 個
- **問題**: 根目錄過於雜亂，大量臨時報告、完成報告混雜

### 🎯 目標
1. **根目錄精簡化**: 只保留 README.md 和關鍵指南
2. **分類清晰**: 所有文檔放在適當的子目錄
3. **歸檔舊文件**: 完成報告、審計報告移到 archive/
4. **易於維護**: 建立清晰的文檔索引

---

## 整理計劃

### 第一階段：歸檔完成報告（10 個）

移動到 `archive/completion_reports/`：

- [x] AI_CHATBOT_LOGIC_IMPLEMENTATION_STATUS.md
- [x] AUDIT_CLEANUP_COMPLETION_REPORT.md
- [x] AUTOMATED_TESTING_SETUP_COMPLETE.md
- [x] COMPLETE_REFACTOR_SUMMARY.md
- [x] DEPLOYMENT_AUDIT_2025-10-31.md
- [x] DOCUMENTATION_AUDIT_2025-10-22.md
- [x] DOCUMENTATION_UPDATE_COMPLETION_2025-10-22.md
- [x] SYSTEM_AUDIT_REPORT_2025-10-13.md
- [x] TESTING_AND_VALIDATION_STATUS.md
- [x] DOCUMENTATION_UPDATE_SUMMARY.md

### 第二階段：歸檔清理報告（5 個）

移動到 `archive/cleanup_reports/`（新建目錄）：

- [x] DOCUMENTATION_CLEANUP_PHASE1_2025-10-23.md
- [x] DOCUMENTATION_CLEANUP_PHASE2_2025-10-23.md
- [x] DOCUMENTATION_CLEANUP_PHASE3_2025-10-23.md
- [x] FILE_CLEANUP_REPORT.md
- [x] FILE_STRUCTURE_ANALYSIS.md

### 第三階段：移動部署文檔（4 個）

移動到 `guides/deployment/`（新建目錄）：

- [x] DEPLOYMENT_PLAN_A.md
- [x] DEPLOYMENT_UPDATE_SUMMARY_2025-10-31.md
- [x] PRODUCTION_DEPLOYMENT_CHECKLIST.md
- [x] PRODUCTION_DEPLOYMENT_CHECKLIST_EC2.md

### 第四階段：移動 Backtest 文檔（8 個）

移動到 `backtest/`：

- [x] BACKTEST_ARCHITECTURE_EVALUATION.md
- [x] BACKTEST_ENV_VARS.md
- [x] BACKTEST_FRAMEWORK_UPDATE.md
- [x] BACKTEST_INDEX.md
- [x] BACKTEST_OPTIMIZATION_FLOW.md
- [x] BACKTEST_QUICKSTART.md
- [x] BACKTEST_STRATEGIES.md
- [x] ADVANCED_TESTS_EXECUTION_REPORT.md → backtest/archive/

### 第五階段：移動 SOP 文檔（2 個）

- [x] SOP_COMPLETE_GUIDE.md → guides/SOP_GUIDE.md（保留在顯眼位置）
- [x] SOP_QUICK_REFERENCE.md → guides/SOP_QUICK_REFERENCE.md
- [x] SOP_COPY_EMBEDDING_FIX_2025-11-02.md → fixes/SOP_COPY_EMBEDDING_FIX.md

### 第六階段：移動系統分析（2 個）

- [x] DATABASE_SCHEMA_ERD.md → architecture/DATABASE_SCHEMA.md
- [x] RESPONSE_QUALITY_ANALYSIS_REPORT.md → archive/evaluation_reports/

### 第七階段：整理其他臨時文件（8 個）

#### 移動到 fixes/
- [x] APPROVAL_FUNCTION_FIX.md
- [x] CLASSIFICATION_TRACKING_FIX.md
- [x] KNOWLEDGE_IMPORT_SIMILARITY_FIX.md

#### 移動到 features/
- [x] B2B_API_INTEGRATION_DESIGN.md → features/B2B_API_INTEGRATION.md

#### 移動到 archive/
- [x] BUSINESS_TYPES_TONE_PROMPTS_BACKUP.md → archive/backups/
- [x] INTENT_THRESHOLD_IMPROVEMENT_REPORT.md → archive/evaluation_reports/
- [x] PHASE3_DEDUPLICATION_ENHANCEMENTS_2025-10-22.md → archive/completion_reports/

#### 移動到 analysis/
- [x] ultrathink_group_field_missing.md

#### 功能實現報告
- [x] BUSINESS_SCOPE_REFACTORING_SUMMARY.md → archive/completion_reports/
- [x] CONFIG_MANAGEMENT_UPDATE_SUMMARY.md → archive/completion_reports/
- [x] SIMPLIFICATION_IMPLEMENTATION_GUIDE.md → guides/

---

## 整理後的目錄結構

```
docs/
├── README.md                          # 主索引（保留）
│
├── guides/                            # ✅ 使用指南
│   ├── deployment/                    # 🆕 部署指南
│   │   ├── DEPLOYMENT_PLAN_A.md
│   │   ├── PRODUCTION_DEPLOYMENT_CHECKLIST.md
│   │   └── PRODUCTION_DEPLOYMENT_CHECKLIST_EC2.md
│   ├── SOP_GUIDE.md                   # 重命名
│   ├── SOP_QUICK_REFERENCE.md
│   ├── SIMPLIFICATION_IMPLEMENTATION_GUIDE.md
│   └── ... (其他現有指南)
│
├── features/                          # ✅ 功能文檔
│   ├── B2B_API_INTEGRATION.md
│   └── ... (其他現有功能)
│
├── backtest/                          # ✅ Backtest 文檔
│   ├── BACKTEST_INDEX.md              # 索引
│   ├── BACKTEST_QUICKSTART.md
│   ├── BACKTEST_STRATEGIES.md
│   ├── BACKTEST_ENV_VARS.md
│   ├── BACKTEST_FRAMEWORK_UPDATE.md
│   ├── BACKTEST_OPTIMIZATION_FLOW.md
│   ├── BACKTEST_ARCHITECTURE_EVALUATION.md
│   └── archive/
│       └── ADVANCED_TESTS_EXECUTION_REPORT.md
│
├── architecture/                      # ✅ 系統架構
│   ├── DATABASE_SCHEMA.md             # 重命名
│   └── ... (其他架構文檔)
│
├── fixes/                             # ✅ 修復記錄
│   ├── APPROVAL_FUNCTION_FIX.md
│   ├── CLASSIFICATION_TRACKING_FIX.md
│   ├── KNOWLEDGE_IMPORT_SIMILARITY_FIX.md
│   ├── SOP_COPY_EMBEDDING_FIX.md
│   └── ... (其他修復)
│
├── analysis/                          # ✅ 系統分析
│   └── ultrathink_group_field_missing.md
│
└── archive/                           # ✅ 歸檔文件
    ├── completion_reports/            # 完成報告
    │   ├── AI_CHATBOT_LOGIC_IMPLEMENTATION_STATUS.md
    │   ├── AUDIT_CLEANUP_COMPLETION_REPORT.md
    │   ├── AUTOMATED_TESTING_SETUP_COMPLETE.md
    │   ├── COMPLETE_REFACTOR_SUMMARY.md
    │   ├── DEPLOYMENT_AUDIT_2025-10-31.md
    │   ├── DOCUMENTATION_AUDIT_2025-10-22.md
    │   ├── DOCUMENTATION_UPDATE_COMPLETION_2025-10-22.md
    │   ├── SYSTEM_AUDIT_REPORT_2025-10-13.md
    │   ├── TESTING_AND_VALIDATION_STATUS.md
    │   ├── DOCUMENTATION_UPDATE_SUMMARY.md
    │   ├── BUSINESS_SCOPE_REFACTORING_SUMMARY.md
    │   ├── CONFIG_MANAGEMENT_UPDATE_SUMMARY.md
    │   ├── PHASE3_DEDUPLICATION_ENHANCEMENTS_2025-10-22.md
    │   └── DEPLOYMENT_UPDATE_SUMMARY_2025-10-31.md
    │
    ├── cleanup_reports/               # 🆕 清理報告
    │   ├── DOCUMENTATION_CLEANUP_PHASE1_2025-10-23.md
    │   ├── DOCUMENTATION_CLEANUP_PHASE2_2025-10-23.md
    │   ├── DOCUMENTATION_CLEANUP_PHASE3_2025-10-23.md
    │   ├── FILE_CLEANUP_REPORT.md
    │   └── FILE_STRUCTURE_ANALYSIS.md
    │
    ├── evaluation_reports/            # 評估報告
    │   ├── RESPONSE_QUALITY_ANALYSIS_REPORT.md
    │   ├── INTENT_THRESHOLD_IMPROVEMENT_REPORT.md
    │   └── ... (其他評估報告)
    │
    └── backups/                       # 🆕 備份文件
        └── BUSINESS_TYPES_TONE_PROMPTS_BACKUP.md
```

---

## 執行清單

### ✅ 階段 1：準備工作
- [ ] 創建新目錄
  - [ ] `mkdir -p docs/guides/deployment`
  - [ ] `mkdir -p docs/archive/cleanup_reports`
  - [ ] `mkdir -p docs/archive/backups`

### ✅ 階段 2：執行移動
- [ ] 執行所有文件移動命令（批次執行）
- [ ] 重命名特定文件

### ✅ 階段 3：更新索引
- [ ] 更新 `docs/README.md` 索引
- [ ] 更新 `docs/backtest/BACKTEST_INDEX.md`
- [ ] 創建 `docs/archive/README.md` 說明

### ✅ 階段 4：驗證
- [ ] 檢查所有文件是否正確移動
- [ ] 檢查是否有斷裂的連結
- [ ] 確認根目錄只剩 README.md

---

## 預期結果

### 根目錄文件數
- **Before**: 44 個 .md 文件
- **After**: 1 個 .md 文件（README.md）

### 目錄結構
- ✅ 所有文檔分類清晰
- ✅ 歷史報告已歸檔
- ✅ 易於尋找和維護

---

**維護者**: Claude Code
**狀態**: 📝 規劃中
