# 📦 部署文件目錄

此目錄存放所有部署相關文件，包括通用部署指南和特定版本的部署文件。

## 🚀 快速開始

### 日常小更新（沒有資料庫遷移）
```bash
cat docs/deployment/DEPLOY_GUIDE.md
```

### 首次部署 2026-01-10 版本（有遷移）
```bash
cat docs/deployment/2026-01-10/QUICK_DEPLOY_2026-01-10.md
# 或
bash docs/deployment/2026-01-10/deploy_2026-01-10.sh
```

### 搭配檢查清單使用
```bash
cat docs/deployment/DEPLOY_CHECKLIST.md
```

## 📂 目錄結構

```
deployment/
├── README.md                    ← 本文件（部署索引）
├── DEPLOY_GUIDE.md              ← 通用部署指南
├── DEPLOY_CHECKLIST.md          ← 通用檢查清單
└── 2026-01-10/                  ← 2026-01-10 版本部署
    ├── DEPLOY_README_2026-01-10.md
    ├── QUICK_DEPLOY_2026-01-10.md
    ├── PRODUCTION_DEPLOY_2026-01-10.md
    └── deploy_2026-01-10.sh
```

## 🎯 使用說明

### 📋 通用部署文件

**DEPLOY_GUIDE.md** - 通用部署指南
- 適用於日常小更新
- 沒有資料庫遷移
- 沒有特殊配置需求
- 包含標準部署流程（拉取代碼 → 判斷變更 → 選擇方案 → 驗證）

**DEPLOY_CHECKLIST.md** - 標準檢查清單
- 每次部署都可參考
- 確保不遺漏步驟
- 適合搭配其他部署文件使用

### 🚀 特定版本部署文件

**使用情境：**
- ✅ 首次部署某個特定版本
- ✅ 該版本包含資料庫遷移
- ✅ 該版本有特殊的部署步驟
- ✅ 需要追溯歷史部署記錄

**文件位置：**
- 按日期（版本號）組織在子目錄下
- 例如：`2026-01-10/`

## 📋 版本列表

### 2026-01-10
**主要更新：**
- 動態表單收集系統
- 表單審核與編輯
- 表單狀態管理與備註
- 知識庫缺失欄位補充（form_id, video_url, trigger_form_condition 等）
- 修復前端 sidebarCollapsed 錯誤

**部署文件：**
- [DEPLOY_README_2026-01-10.md](2026-01-10/DEPLOY_README_2026-01-10.md) - 部署索引
- [QUICK_DEPLOY_2026-01-10.md](2026-01-10/QUICK_DEPLOY_2026-01-10.md) - 快速部署
- [PRODUCTION_DEPLOY_2026-01-10.md](2026-01-10/PRODUCTION_DEPLOY_2026-01-10.md) - 完整部署
- [deploy_2026-01-10.sh](2026-01-10/deploy_2026-01-10.sh) - 自動化腳本

**資料庫遷移：**
- `database/migrations/add_knowledge_base_missing_columns.sql`
- `database/migrations/create_form_tables.sql`
- `database/migrations/add_form_schema_description_fields.sql`
- `database/migrations/add_form_sessions_trigger_fields.sql`
- `rag-orchestrator/database/migrations/create_digression_config.sql`
- `database/migrations/add_form_submission_status.sql`

---

### 2026-01-21
**主要更新：**
- **Critical P0**：Knowledge Admin API 整合修復（action_type 和 api_config 欄位支援）
- API Endpoints 動態管理功能
- 表單系統增強
- 文檔結構重組優化

**部署文件：**
- [DEPLOY_2026-01-21.md](archive/2026-01-21/DEPLOY_2026-01-21.md) - 完整部署指南

**資料庫遷移：**
- `database/migrations/add_action_type_and_api_config.sql` - 新增知識庫動作類型和 API 配置
- `database/migrations/create_api_endpoints_table.sql` - 創建 API 端點管理表
- `database/migrations/upgrade_api_endpoints_dynamic.sql` - 升級為動態 API 管理
- `database/migrations/configure_billing_inquiry_examples.sql` - 配置帳單查詢範例
- `database/migrations/remove_handler_function_column.sql` - 移除已棄用欄位

**相關文檔：**
- [API 整合完整修復報告](../fixes/2026-01-21-api-integration-fix.md)
- [API 整合深度分析](../fixes/2026-01-21-api-integration-analysis.md)
- [API 整合測試指南](../testing/api-integration-testing-guide.md)
- [文檔重組報告](../DOCS_REORGANIZATION_REPORT_2026-01-21.md)

---

### 2026-01-13
**主要更新：**
- 統一檢索路徑（commit cbf4c4f）- 使意圖成為純排序因子
- 前端表單編輯器增加 prompt 欄位必填驗證（commit ba503d3）
- 移除 form_intro 欄位，統一使用表單 default_intro（commit 781a7c0）

**部署文件：**
- [DEPLOY_2026-01-13.md](archive/2026-01-13/DEPLOY_2026-01-13.md) - 整合部署指南（包含所有更新）

**資料庫遷移：**
- `database/migrations/remove_form_intro_2026-01-13.sql` - 刪除 knowledge_base.form_intro 欄位

**相關文檔：**
- [統一檢索路徑實施報告](../implementation/FINAL_2026-01-13.md)
- [表單引導語改善報告](../features/FORM_GUIDANCE_IMPROVEMENT_2026-01-13.md)

---

### 2026-01-22 ⭐ 最新
**主要更新：**
- **Migration 追蹤系統**：建立 `schema_migrations` 表，解決推版漏掉欄位問題
- **自動執行腳本**：`database/run_migrations.sh` 支援 dry-run、自動備份、交互式確認
- **安全機制**：冪等性、錯誤停止、執行記錄、回滾指南
- **文檔完善**：完整的 Migration 使用說明和 FAQ

**部署文件：**
- [DEPLOY_2026-01-22.md](archive/2026-01-22/DEPLOY_2026-01-22.md) - Migration 系統部署指南

**資料庫遷移：**
- `database/migrations/000_create_schema_migrations.sql` - 創建 Migration 追蹤表
- 所有歷史 migration (17 個) - 自動追蹤和執行

**核心工具：**
- `database/run_migrations.sh` - Migration 自動執行腳本（安全加強版）
- `database/migrations/README.md` - Migration 完整文檔

**重要特性：**
- ✅ 自動追蹤已執行的 migration
- ✅ Dry-run 模式預覽變更
- ✅ 自動備份資料庫
- ✅ 失敗自動停止並提供回滾命令
- ✅ 防止重複執行

**使用方法：**
```bash
# 預覽即將執行的 migration
./database/run_migrations.sh docker-compose.prod.yml --dry-run

# 執行 migration（自動備份）
./database/run_migrations.sh docker-compose.prod.yml

# 交互式執行（需要確認）
./database/run_migrations.sh docker-compose.prod.yml --interactive
```

---

## 🆕 新增版本

當有新版本需要特殊部署步驟時，請按以下方式組織：

1. 創建新目錄：`docs/deployment/YYYY-MM-DD/`
2. 複製模板文件並修改內容
3. 更新本 README，添加版本記錄
4. 在 `docs/DEPLOYMENT_CLEANUP_YYYY-MM-DD.md` 記錄整理過程

---

**最後更新**：2026-01-22
