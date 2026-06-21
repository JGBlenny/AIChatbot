# 🚀 通用部署指南

> 適用於日常更新和維護部署（沒有特殊遷移需求時使用）

## 📌 使用說明

**何時使用本文件：**
- 小修小補的代碼更新
- 沒有資料庫遷移
- 沒有特殊配置變更
- 日常維護部署

**何時使用版本特定文件：**
- 有資料庫遷移（查看 `docs/deployment/版本號/`）
- 有重大功能更新
- 需要特殊部署步驟

---

## 🔄 標準部署流程

### 步驟 1：部署前檢查

```bash
cd /path/to/AIChatbot

# 檢查當前分支和狀態
git status
git branch

# 查看最近的提交
git log --oneline -5
```

**確認：**
- [ ] 當前在 main 分支
- [ ] 工作目錄乾淨
- [ ] 了解要部署的更新內容

---

### 步驟 2：拉取最新代碼

```bash
git pull origin main
```

**預期結果：**
- 看到更新的文件列表
- 沒有合併衝突

---

### 步驟 3：檢查是否有資料庫遷移

⚠️ **重要：每次推版前必須執行此步驟！**

```bash
# 預覽待執行的 migration（不會實際執行）
./database/run_migrations.sh docker-compose.prod.yml --dry-run
```

**預期結果：**
- **情況 A**：`✓ 所有 migration 都已執行，無需執行`
  - 表示無資料庫變更，直接跳到步驟 4

- **情況 B**：`⚠️ 發現 N 個待執行的 migration`
  - 表示有資料庫變更，必須先執行 migration

#### 3.1 如果有待執行的 migration

```bash
# 方法 1: 自動執行（推薦，會自動備份）
./database/run_migrations.sh docker-compose.prod.yml

# 方法 2: 交互式執行（需要手動確認）
./database/run_migrations.sh docker-compose.prod.yml --interactive

# 執行完成後驗證
./database/run_migrations.sh docker-compose.prod.yml --dry-run
# 應該顯示：✓ 所有 migration 都已執行
```

**Migration 腳本特性：**
- ✅ 自動備份資料庫到 `database/backups/`
- ✅ 冪等性：已執行的 migration 自動跳過
- ✅ 失敗自動停止並顯示回滾命令
- ✅ 記錄執行歷史到 `schema_migrations` 表

**如果 migration 失敗：**
```bash
# 查看錯誤日誌
ls -lt /tmp/migration_*.log | head -1

# 使用自動生成的備份回滾
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/backups/backup_before_migration_*.sql
```

---

### 步驟 4：判斷是否需要重新構建

#### 4.1 檢查變更的文件類型

```bash
# 查看本次更新變更了哪些文件
git diff HEAD@{1} --name-only
```

#### 4.2 根據變更決定操作

| 變更內容 | 需要做什麼 |
|---------|----------|
| 只有後端 Python 文件 | 重啟後端服務即可 |
| 前端文件（.vue, .js） | 需要重新 build 前端 + 重啟前端服務 |
| Dockerfile 或 requirements.txt | 需要完整重新構建 |
| docker-compose.yml | 需要重新啟動所有服務 |
| database/migrations/*.sql | 已在步驟 3 處理，無需額外操作 |
| **換庫 / 大量知識變更** | ⚠️ **必一併重建 `semantic-model`（reranker）+ `embedding-api`**，否則檢索排序/表單觸發會與新資料不同步（`docker compose -f docker-compose.prod.yml up -d --build --no-deps semantic-model embedding-api`） |

---

### 步驟 5：執行部署

#### 方案 A：只改了後端代碼（最快）

```bash
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
docker-compose -f docker-compose.prod.yml restart knowledge-admin-api
```

#### 方案 B：改了前端代碼

```bash
# 1. 重新構建前端
cd knowledge-admin/frontend
npm install  # 如果 package.json 有變更
npm run build
cd ../..

# 2. 重啟前端服務
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
```

#### 方案 C：Dockerfile 或依賴有變更（完整重建）

```bash
# 停止服務
docker-compose -f docker-compose.prod.yml down

# 重新構建（使用 --no-cache 確保更新）
docker-compose -f docker-compose.prod.yml build --no-cache

# 啟動服務
docker-compose -f docker-compose.prod.yml up -d
```

---

### 步驟 6：驗證部署

#### 6.1 檢查服務狀態

```bash
docker-compose -f docker-compose.prod.yml ps
```

**預期結果：**
- 所有服務狀態都是 `Up`
- 沒有服務在 `Restarting`

#### 6.2 檢查日誌

```bash
# 查看主要服務日誌
docker-compose -f docker-compose.prod.yml logs --tail=50 rag-orchestrator
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-api
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-web
```

**確認：**
- [ ] 沒有錯誤訊息
- [ ] 服務正常啟動

#### 6.3 功能測試

1. 訪問前端：`http://your-domain`
2. 測試登入功能
3. 測試主要功能是否正常
4. 檢查本次更新的功能

---

## 🐛 常見問題

### 問題 1：服務不斷重啟

```bash
# 查看詳細日誌
docker-compose -f docker-compose.prod.yml logs --tail=100 [service_name]
```

**常見原因：**
- Python 模組缺失 → 需要重新構建（方案 C）
- 環境變數錯誤 → 檢查 .env 文件
- 資料庫連接失敗 → 檢查 postgres 服務

### 問題 2：前端顯示舊版本

```bash
# 1. 確認 dist 目錄已更新
ls -la knowledge-admin/frontend/dist/

# 2. 重啟前端服務
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web

# 3. 清除瀏覽器快取（Ctrl+Shift+R）
```

### 問題 3：API 返回 404

```bash
# 檢查路由是否正確註冊
docker-compose -f docker-compose.prod.yml logs rag-orchestrator | grep "route"
```

**如果路由沒有註冊 → 需要重啟或重建服務**

---

## 🔄 回滾步驟

如果部署失敗，立即回滾：

```bash
# 1. 查看上一個版本
git log --oneline -5

# 2. 回滾代碼
git checkout [previous_commit_hash]

# 3. 重新構建（如果需要）
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 4. 驗證
docker-compose -f docker-compose.prod.yml ps
```

---

## 📋 快速參考

### 常用命令

```bash
# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f [service_name]

# 重啟單個服務
docker-compose -f docker-compose.prod.yml restart [service_name]

# 停止所有服務
docker-compose -f docker-compose.prod.yml down

# 啟動所有服務
docker-compose -f docker-compose.prod.yml up -d
```

### 服務名稱

- `postgres` - PostgreSQL 資料庫
- `redis` - Redis 快取
- `embedding-api` - Embedding 服務
- `rag-orchestrator` - RAG 主服務
- `knowledge-admin-api` - 管理後台 API
- `knowledge-admin-web` - 管理後台前端

---

## ⚠️ 重要提醒

1. **部署前先備份資料庫**（如果是重要更新）
2. **確認在正確的服務器和目錄**
3. **查看 git log 了解本次更新內容**
4. **有問題立即回滾，不要在線修復**
5. **搭配 `DEPLOY_CHECKLIST.md` 使用確保不遺漏步驟**

---

## 🔗 相關文檔

- **標準檢查清單**：`DEPLOY_CHECKLIST.md`
- **特定版本部署**：`docs/deployment/版本號/`
- **最新版本**：`docs/deployment/2026-01-10/`

---

**最後更新**：2026-01-22
**維護者**：DevOps Team
