# 📋 部署文件整理摘要（2026-01-12）

## ✅ 完成的工作

### 1. 建立新的資料庫遷移文件

**檔案**: `database/migrations/add_knowledge_base_missing_columns.sql`

**內容**:
- 表單關聯欄位（form_id, form_intro）
- 影片相關欄位（video_url, video_s3_key, video_file_size, video_duration, video_format）
- 表單觸發條件（trigger_form_condition）

**原因**: 生產環境部署後發現缺少這些欄位，導致 500 錯誤。

---

### 2. 更新部署文件

**更新的檔案**:
- `QUICK_DEPLOY_2026-01-10.md`
  - ✅ 新增知識庫欄位遷移步驟
  - ✅ 新增故障排除：500 錯誤（欄位不存在）
  - ✅ 新增故障排除：分頁按鈕無法點擊
  - ✅ 更新驗證步驟

- `DEPLOY_README_2026-01-10.md`
  - ✅ 更新版本資訊到 2026-01-12
  - ✅ 新增最新更新說明

---

### 3. 部署文件結構調整

#### 通用部署文件（已移至 docs/deployment/）

| 檔案 | 用途 | 說明 |
|------|------|------|
| `docs/deployment/DEPLOY_GUIDE.md` | 通用部署指南 | 日常更新、小修小補時使用 |
| `docs/deployment/DEPLOY_CHECKLIST.md` | 標準部署檢查清單 | 流程檢查清單 |

**說明**：
- `DEPLOY_GUIDE.md` - 新建的真正通用文件，包含標準部署流程
- `DEPLOY_CHECKLIST.md` - 從根目錄移到 docs/deployment/
- 舊的 `PRODUCTION_DEPLOY.md`、`QUICK_DEPLOY.md` 已刪除（它們是舊版本特定文件，非通用）
- **所有部署文件統一放在 docs/deployment/ 目錄**

#### 特定版本部署文件（已移至 docs/deployment/2026-01-10/）

| 檔案 | 用途 | 說明 |
|------|------|------|
| `DEPLOY_README_2026-01-10.md` | 2026-01-10 版本索引 | 該次更新的部署指引 |
| `QUICK_DEPLOY_2026-01-10.md` | 2026-01-10 快速部署 | 該次更新的快速指南 |
| `PRODUCTION_DEPLOY_2026-01-10.md` | 2026-01-10 完整部署 | 該次更新的完整說明 |
| `deploy_2026-01-10.sh` | 2026-01-10 自動化腳本 | 該次更新的部署腳本 |

#### 刪除過時文件

已刪除：

| 檔案 | 原因 |
|------|------|
| `PRODUCTION_DEPLOY.md` | 舊版本部署說明（用戶管理更新），非通用文件 |
| `QUICK_DEPLOY.md` | 舊版本快速部署，非通用文件 |
| `Makefile` | 引用已刪除的 docker-compose.dev.yml，無法使用 |
| `DEPLOY_THIS_UPDATE.sh` | 舊的部署腳本，已被新版取代 |
| `docs/DEPLOYMENT_STEPS_2024-12-19.md` | 過時（2024年12月） |
| `docs/DEPLOYMENT_GUIDE.md` | 內容過時 |
| `docs/archive/deployment/` | 歸檔目錄已清空，不再需要 |
| `test_scenarios_full.xlsx` | 空目錄（命名錯誤） |
| `test_scenarios_smoke.xlsx` | 空目錄（命名錯誤） |

### 4. 刪除未使用的文件

已刪除：

| 檔案 | 原因 |
|------|------|
| `docker-compose.prod-prebuilt.yml` | 未使用的 Docker Compose 配置 |
| `docker-compose.dev.yml` | 未使用的 Docker Compose 配置 |

---

### 5. 修復的問題

#### 問題 1: 保存知識時 500 錯誤
**錯誤**: `column "form_id" does not exist`

**解決**:
- 建立遷移文件 `add_knowledge_base_missing_columns.sql`
- 更新部署文件，確保執行該遷移

#### 問題 2: 分頁按鈕無法點擊
**錯誤**: Vue 警告 `Property "sidebarCollapsed" was accessed during render but is not defined`

**解決**:
- 修復 `knowledge-admin/frontend/src/App.vue`
- 在 data() 中新增 `sidebarCollapsed: false`
- 更新部署文件的故障排除章節

---

## 📚 最終的部署文件結構

```
AIChatbot/
│
├── 📁 根目錄（極度精簡）
│   ├── README.md                        ← 項目說明
│   ├── CHANGELOG.md                     ← 變更記錄
│   ├── docker-compose.yml               ← 本地開發用（已加註解）
│   ├── docker-compose.prod.yml          ← 生產環境用
│   └── .env, .env.example, .gitignore   ← 配置文件
│
├── 📁 docs/
│   ├── DEPLOYMENT_CLEANUP_2026-01-12.md ← 本次整理摘要
│   │
│   └── deployment/                      ← 📦 所有部署文件統一在這裡
│       ├── README.md                    ← 部署索引（快速開始指南）
│       ├── DEPLOY_GUIDE.md              ← 🆕 通用部署指南
│       ├── DEPLOY_CHECKLIST.md          ← 通用檢查清單
│       │
│       └── 2026-01-10/                  ← 特定版本部署文件
│           ├── DEPLOY_README_2026-01-10.md      ← 該版本索引
│           ├── QUICK_DEPLOY_2026-01-10.md       ← 該版本快速部署
│           ├── PRODUCTION_DEPLOY_2026-01-10.md  ← 該版本完整部署
│           └── deploy_2026-01-10.sh             ← 該版本自動化腳本
│
├── 📁 database/migrations/
│   └── add_knowledge_base_missing_columns.sql   ← 🆕 今天新增
│
└── 📁 scripts/deployment/
    └── deploy-frontend.sh                       ← 前端部署腳本（可選）
```

### 結構說明

**根目錄**：極度精簡
- 只保留項目核心文件（README, CHANGELOG）和配置文件
- **不再有任何部署文件**

**docs/deployment/ - 所有部署文件統一在這裡**：
- `DEPLOY_GUIDE.md` - 通用部署指南（日常小更新）
- `DEPLOY_CHECKLIST.md` - 通用檢查清單
- `版本號/` - 特定版本部署文件（有遷移時使用）

**核心理念**：
- ✅ 根目錄極度乾淨
- ✅ 所有部署文件集中管理在 `docs/deployment/`
- ✅ 通用 vs 特定版本，清楚區分

---

## 🚀 如何部署

### 📋 部署文件選擇指南

**情境 1：日常小更新（沒有資料庫遷移）**
```bash
# 使用通用部署指南
cat docs/deployment/DEPLOY_GUIDE.md
```
適用於：
- ✅ 小修小補的代碼更新
- ✅ Bug 修復
- ✅ 沒有資料庫結構變更
- ✅ 沒有特殊配置需求

---

**情境 2：重大更新（有資料庫遷移或特殊步驟）**
```bash
# 使用特定版本部署文件
cat docs/deployment/2026-01-10/QUICK_DEPLOY_2026-01-10.md

# 或使用自動化腳本
bash docs/deployment/2026-01-10/deploy_2026-01-10.sh
```
適用於：
- ✅ 有資料庫遷移
- ✅ 重大功能更新
- ✅ 需要特殊部署步驟
- ✅ 首次部署該版本

---

### 📂 可用的部署文件

**通用部署文件（docs/deployment/）：**
- `docs/deployment/DEPLOY_GUIDE.md` - 通用部署指南（日常更新用）
- `docs/deployment/DEPLOY_CHECKLIST.md` - 標準檢查清單

**特定版本部署文件（docs/deployment/版本號/）：**
- `docs/deployment/2026-01-10/` - 2026-01-10 版本（目前最新）
  - `DEPLOY_README_2026-01-10.md` - 該版本索引
  - `QUICK_DEPLOY_2026-01-10.md` - 快速部署
  - `PRODUCTION_DEPLOY_2026-01-10.md` - 完整部署說明
  - `deploy_2026-01-10.sh` - 自動化腳本

---

### 💡 推薦用法

#### 日常更新流程
```bash
# 1. 查看通用部署指南
cat docs/deployment/DEPLOY_GUIDE.md

# 2. 搭配檢查清單使用
cat docs/deployment/DEPLOY_CHECKLIST.md

# 3. 執行部署（根據變更內容選擇方案 A/B/C）
```

#### 首次部署 2026-01-10 版本
```bash
# 1. 查看該版本索引了解更新內容
cat docs/deployment/2026-01-10/DEPLOY_README_2026-01-10.md

# 2. 使用快速部署指南
cat docs/deployment/2026-01-10/QUICK_DEPLOY_2026-01-10.md

# 3. 或使用自動化腳本
bash docs/deployment/2026-01-10/deploy_2026-01-10.sh
```

---

## ⚠️ 重要提醒

### 必須執行的新遷移

如果你之前已經部署過，**必須**執行：

```bash
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_knowledge_base_missing_columns.sql
```

這會修復：
- 保存知識時的 500 錯誤
- 表單關聯功能
- 影片上傳功能
- 聊天觸發表單功能

### 前端必須重新 build

如果遇到分頁按鈕無法點擊：

```bash
cd knowledge-admin/frontend
npm install
npm run build
cd ../..
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
```

---

## 📞 問題排查

如果遇到問題，請參考：

1. **docs/deployment/2026-01-10/QUICK_DEPLOY_2026-01-10.md** 的「🐛 快速故障排除」章節
2. **docs/deployment/2026-01-10/PRODUCTION_DEPLOY_2026-01-10.md** 的「🐛 常見問題排查」章節
3. 檢查日誌：`docker-compose -f docker-compose.prod.yml logs [service_name]`

---

## 🎯 下次部署注意事項

### 對開發者
- 新增資料庫欄位時，請同時建立 migration 文件
- 前端新增 data 屬性時，記得初始化
- 測試環境先驗證，再推到生產環境

### 對運維人員
- 部署前先閱讀 DEPLOY_README
- 執行遷移前先備份資料庫
- 前端變更後記得重新 build
- 瀏覽器測試時記得清除快取
- **注意區分 docker-compose.yml（本地）和 docker-compose.prod.yml（生產）**

---

## 📝 其他變更

### Docker Compose 配置文件註解
已在 `docker-compose.yml` 開頭加上明確註解：
```yaml
# ========================================
# 本地開發環境配置
# 用於本地開發和測試，不適用於生產環境
# 生產環境請使用 docker-compose.prod.yml
# ========================================
```

**目的**：防止誤用本地配置在生產環境

---

**整理者**: Claude Code
**整理日期**: 2026-01-12
**狀態**: ✅ 完成
