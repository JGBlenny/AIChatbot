# 部署步驟：從 9efe5d6 到目前進度

> **起點 commit**: `9efe5d6` — fix: 修復表單 REVIEWING 狀態串流模式響應問題 (2026-02-26)
> **目標 commit**: `7b93aa2` (main HEAD，含 feature/backtest-knowledge-refinement 合併)
> **涵蓋 commit 數量**: 約 30 個

---

## 📌 變更摘要

| 類別 | 說明 |
|------|------|
| **資料庫** | `vendor_id` → `vendor_ids` 陣列升級、API Endpoint Trigger 修復、知識完善迴圈相關新表 |
| **後端 (rag-orchestrator)** | 新增 loops / loop_knowledge 路由、分類器改良、SOP 生成器、回測框架、知識完善迴圈系統 |
| **後端 (knowledge-admin-api)** | vendor_ids 支援、Lookup 批量匯入/匯出、Docker CLI 安裝 |
| **前端** | 回測結果頁、迴圈管理、審核中心改版、API 文件入口頁 |
| **基礎設施** | Dockerfile 變更、requirements.txt 新增套件、docker-compose.prod.yml 調整、nginx.conf 更新 |

---

## 🔄 部署流程

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

### 步驟 2：備份資料庫

⚠️ **本次有 schema 變更，必須先備份！**

```bash
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

### 步驟 3：拉取最新代碼

```bash
git pull origin main
```

**預期結果：**
- 看到更新的文件列表
- 沒有合併衝突

---

### 步驟 4：資料庫遷移

⚠️ **重要：本次有多項 schema 變更，必須依序執行！**

#### 4.1 自動遷移（優先嘗試）

```bash
./database/run_migrations.sh docker-compose.prod.yml --dry-run
```

如果腳本能正確偵測待執行的 migration，直接執行：

```bash
./database/run_migrations.sh docker-compose.prod.yml
```

#### 4.2 手動遷移（如自動腳本不適用）

##### 4.2.1 vendor_id → vendor_ids 欄位升級

```sql
-- 1. 新增 vendor_ids 陣列欄位
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS vendor_ids INTEGER[];

-- 2. 遷移現有資料
UPDATE knowledge_base
SET vendor_ids = ARRAY[vendor_id]
WHERE vendor_id IS NOT NULL AND vendor_ids IS NULL;

-- 3. 確認遷移完成後，再移除舊欄位（可選，確認應用正常後再執行）
-- ALTER TABLE knowledge_base DROP COLUMN vendor_id;
```

##### 4.2.2 知識完善迴圈相關新表

```bash
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/001_create_knowledge_completion_loops_table.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/002_create_knowledge_gap_analysis_table.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/003_add_gap_analysis_foreign_key.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/003_create_loop_generated_knowledge_table.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/004_extend_knowledge_base_table.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/005_create_quality_validation_tables.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/006_create_openai_cost_tracking_table.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/007_create_loop_execution_logs_table.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/008_create_constraints_and_triggers.sql
```

> 提示：migration 腳本多數使用 `IF NOT EXISTS`，重複執行應不會報錯，但建議先確認哪些已執行過。

##### 4.2.3 API Endpoint Trigger 修復

```bash
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/fix_api_endpoint_kb_sync_trigger.sql
```

##### 4.2.4 迴圈功能相關欄位

```bash
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/migrations/add_loop_features.sql
```

#### 4.3 驗證遷移結果

```bash
./database/run_migrations.sh docker-compose.prod.yml --dry-run
# 應該顯示：✓ 所有 migration 都已執行
```

**如果 migration 失敗：**
```bash
# 使用步驟 2 的備份回滾
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup_XXXXXXXX_XXXXXX.sql
```

---

### 步驟 5：重新構建前端

前端有大量變更（回測結果頁、迴圈管理、審核中心等），必須重新構建：

```bash
cd knowledge-admin/frontend
npm install
npm run build
cd ../..
```

**確認：**
- [ ] 構建成功
- [ ] `knowledge-admin/frontend/dist/` 目錄已更新

---

### 步驟 6：完整重新構建 Docker 映像

本次有 **Dockerfile 和 requirements.txt 變更**，必須使用方案 C（完整重建）。

**變更項目：**
- `knowledge-admin/backend/Dockerfile` — 新增 Docker CLI 安裝
- `knowledge-admin/backend/requirements.txt` — 新增 `aiohttp`, `tenacity`, `tqdm`
- `rag-orchestrator/requirements.txt` — 新增 `aiohttp`, `requests`, `tqdm`, `tenacity`, `xlsxwriter`
- `docker-compose.prod.yml` — 新增 docker.sock 掛載、api-docs.html 掛載

```bash
# 停止服務
docker-compose -f docker-compose.prod.yml down

# 重新構建（使用 --no-cache 確保更新）
docker-compose -f docker-compose.prod.yml build --no-cache

# 啟動服務
docker-compose -f docker-compose.prod.yml up -d
```

---

### 步驟 7：驗證部署

#### 7.1 檢查服務狀態

```bash
docker-compose -f docker-compose.prod.yml ps
```

**預期結果：**
- 所有服務狀態都是 `Up`
- 沒有服務在 `Restarting`

#### 7.2 檢查日誌

```bash
docker-compose -f docker-compose.prod.yml logs --tail=50 rag-orchestrator
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-api
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-web
```

**確認：**
- [ ] 沒有錯誤訊息
- [ ] 服務正常啟動

#### 7.3 功能測試

- [ ] 前端可登入
- [ ] API 文件入口頁 (`/api-docs`) 可訪問
- [ ] 知識庫編輯頁支援多業者 (vendor_ids)
- [ ] 回測頁面 (BacktestView) 可正常載入
- [ ] 迴圈管理頁面 (LoopManagementTab) 可正常載入
- [ ] 審核中心顯示表單/API 標籤
- [ ] 分類器正常運作（測試一則聊天）

---

## 🔄 回滾步驟

如果部署失敗，立即回滾：

```bash
# 1. 回滾代碼
git checkout 9efe5d61f9e2f60beca908722ab912cceb7b5857

# 2. 重新構建前端
cd knowledge-admin/frontend && npm install && npm run build && cd ../..

# 3. 完整重建
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 4. 驗證
docker-compose -f docker-compose.prod.yml ps
```

> ⚠️ 注意：如果已執行 vendor_ids 遷移，回滾需要恢復步驟 2 的 DB 備份。

---

## 🐛 常見問題

### 問題 1：服務不斷重啟

```bash
docker-compose -f docker-compose.prod.yml logs --tail=100 [service_name]
```

**常見原因：**
- Python 模組缺失 → 需要重新構建（`build --no-cache`）
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
docker-compose -f docker-compose.prod.yml logs rag-orchestrator | grep "route"
```

**如果路由沒有註冊 → 需要重啟或重建服務**

---

**最後更新**：2026-04-13
