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

### 2026-01-13
**主要更新：**
- 統一檢索路徑（commit cbf4c4f）- 使意圖成為純排序因子
- 前端表單編輯器增加 prompt 欄位必填驗證（commit ba503d3）
- 移除 form_intro 欄位，統一使用表單 default_intro（commit 781a7c0）

**部署文件：**
- [DEPLOY_2026-01-13.md](2026-01-13/DEPLOY_2026-01-13.md) - 整合部署指南（包含所有更新）

**資料庫遷移：**
- `database/migrations/remove_form_intro_2026-01-13.sql` - 刪除 knowledge_base.form_intro 欄位

**相關文檔：**
- [統一檢索路徑實施報告](../implementation/FINAL_2026-01-13.md)
- [表單引導語改善報告](../features/FORM_GUIDANCE_IMPROVEMENT_2026-01-13.md)

---

## 🆕 新增版本

當有新版本需要特殊部署步驟時，請按以下方式組織：

1. 創建新目錄：`docs/deployment/YYYY-MM-DD/`
2. 複製模板文件並修改內容
3. 更新本 README，添加版本記錄
4. 在 `docs/DEPLOYMENT_CLEANUP_YYYY-MM-DD.md` 記錄整理過程

---

**最後更新**：2026-01-13
