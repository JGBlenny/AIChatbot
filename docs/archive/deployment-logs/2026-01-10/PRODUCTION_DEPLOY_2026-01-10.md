# 🚀 生產環境部署步驟（2026-01-10）

> **部署範圍**：從 commit `b03d649` 到當前版本的所有功能更新

---

## 📦 更新內容摘要

### 主要新功能

#### 1. 動態表單收集系統與知識整合 (commit 99c71a3)
- ✅ 完整的表單管理系統（前端 + 後端）
- ✅ 表單填寫對話流程
- ✅ 離題檢測與處理機制
- ✅ 表單提交記錄管理
- ✅ 業者專屬表單展示頁面

#### 2. 表單審核與編輯功能 (commit bf24d81)
- ✅ 表單審核流程（REVIEWING 狀態）
- ✅ 表單編輯功能（EDITING 狀態）
- ✅ 審核通過/拒絕機制
- ✅ 編輯欄位驗證

#### 3. 表單狀態管理與備註系統（本次未提交）
- ✅ 4 種處理狀態（pending, processing, completed, rejected）
- ✅ 業者可新增處理備註
- ✅ 狀態變更追蹤（updated_at, updated_by）
- ✅ 業者管理頁面新增表單連結
- ✅ 表單提交頁面搜尋與篩選功能

---

## 🗄️ 資料庫變更

### 新增的資料表
1. **form_schemas** - 表單定義表
2. **form_sessions** - 表單會話表
3. **form_submissions** - 表單提交記錄表
4. **digression_config** - 離題檢測配置表

### 修改的資料表
- **form_submissions** 新增欄位：
  - `status` VARCHAR(50) - 處理狀態
  - `notes` TEXT - 備註說明
  - `updated_at` TIMESTAMP - 最後更新時間
  - `updated_by` VARCHAR(100) - 更新者

---

## 📂 新增的主要檔案

### 後端 (rag-orchestrator)
- `routers/forms.py` - 表單管理 API 路由
- `services/form_manager.py` - 表單管理核心服務
- `services/form_validator.py` - 表單驗證服務
- `services/digression_detector.py` - 離題檢測服務（記憶體版本）
- `services/digression_detector_db.py` - 離題檢測服務（資料庫版本）
- `tests/test_form_services.py` - 表單服務測試

### 前端 (knowledge-admin/frontend)
- `views/FormManagementView.vue` - 表單管理頁面
- `views/FormEditorView.vue` - 表單編輯器頁面
- `views/FormSubmissionsView.vue` - 表單提交記錄頁面（管理端）
- `views/VendorFormSubmissionsView.vue` - 表單提交記錄頁面（業者端）

### 資料庫遷移
- `database/migrations/create_form_tables.sql` - 建立表單相關資料表
- `database/migrations/verify_form_tables.sql` - 驗證表單資料表
- `database/migrations/create_digression_config.sql` - 建立離題檢測配置表
- `database/migrations/add_form_submission_status.sql` - 新增表單狀態欄位

---

## 🔄 部署步驟

### 前置檢查

```bash
# 確認當前位置和分支
cd /path/to/AIChatbot
git status
git branch

# 查看當前版本
git log --oneline -5
```

**檢查清單：**
- [ ] 當前分支是 `main`
- [ ] 工作目錄乾淨
- [ ] 確認要部署的版本

---

### 步驟 1：拉取最新代碼

```bash
cd /path/to/AIChatbot
git pull origin main
```

**預期結果：**
- 看到拉取的文件列表或 "Already up to date"
- 沒有合併衝突

---

### 步驟 2：執行資料庫遷移（重要！）

> ⚠️ **注意**：請依序執行以下遷移腳本

#### 2.1 建立表單相關資料表

```bash
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/create_form_tables.sql
```

**預期輸出：**
```
BEGIN
CREATE TABLE
CREATE TABLE
CREATE TABLE
...
COMMIT
```

#### 2.2 建立離題檢測配置表

```bash
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/create_digression_config.sql
```

#### 2.3 新增表單提交狀態欄位

```bash
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_form_submission_status.sql
```

#### 2.4 驗證遷移結果

```bash
# 驗證表單資料表
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/verify_form_tables.sql

# 檢查 form_submissions 表結構
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U aichatbot -d aichatbot_admin -c "\d form_submissions"
```

**預期結果：**
- 看到 `form_schemas`, `form_sessions`, `form_submissions`, `digression_config` 表
- `form_submissions` 包含 `status`, `notes`, `updated_at`, `updated_by` 欄位

---

### 步驟 3：安裝新的前端依賴

> 本次更新新增了 axios 依賴

```bash
cd knowledge-admin/frontend
npm install
```

**檢查項目：**
- [ ] npm install 成功完成
- [ ] 沒有警告或錯誤

---

### 步驟 4：重新構建前端

```bash
cd knowledge-admin/frontend
npm run build
cd ../..
```

**預期結果：**
- 看到 "build complete" 或類似訊息
- `dist` 目錄已更新

**檢查項目：**
- [ ] 前端構建成功
- [ ] dist 目錄包含最新檔案

---

### 步驟 5：重新構建並啟動服務

> ⚠️ **重要**：本次更新包含多個新的 Python 檔案和依賴，必須重新構建

```bash
cd /path/to/AIChatbot

# 停止舊服務
docker-compose -f docker-compose.prod.yml down

# 完整重新構建（清除快取）
docker-compose -f docker-compose.prod.yml build --no-cache rag-orchestrator
docker-compose -f docker-compose.prod.yml build --no-cache knowledge-admin-api
docker-compose -f docker-compose.prod.yml build --no-cache knowledge-admin-web

# 啟動所有服務
docker-compose -f docker-compose.prod.yml up -d

# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps
```

**預期結果：**
- 所有服務狀態都是 `Up`
- 沒有服務在 `Restarting`

---

### 步驟 6：驗證部署

#### 6.1 檢查服務狀態

```bash
docker-compose -f docker-compose.prod.yml ps
```

**檢查項目：**
- [ ] `rag-orchestrator` 狀態為 Up
- [ ] `knowledge-admin-api` 狀態為 Up
- [ ] `knowledge-admin-web` 狀態為 Up
- [ ] `postgres` 狀態為 Up

#### 6.2 檢查服務日誌

```bash
# RAG Orchestrator 日誌
docker-compose -f docker-compose.prod.yml logs --tail=50 rag-orchestrator

# 管理後端日誌
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-api

# 前端日誌
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-web
```

**檢查項目：**
- [ ] 沒有 Python 錯誤
- [ ] 沒有 import 錯誤
- [ ] 沒有資料庫連接錯誤

#### 6.3 驗證新路由

```bash
# 檢查表單管理 API
curl -s http://localhost:8100/api/v1/forms | python3 -m json.tool

# 檢查 API 文檔
curl -s http://localhost:8100/docs | grep -o "forms" | head -1
```

**預期結果：**
- 表單 API 返回 JSON 數據（可能是空陣列）
- API 文檔包含 "forms" 路由

#### 6.4 檢查前端路由

```bash
# 檢查前端是否包含新頁面
docker-compose -f docker-compose.prod.yml exec knowledge-admin-web \
  ls -la /usr/share/nginx/html/assets/*.js | wc -l
```

**預期結果：**
- 看到多個 JavaScript 檔案

---

### 步驟 7：功能測試

#### 7.1 登入管理系統

1. 訪問：`http://your-domain` 或 `http://your-server-ip`
2. 使用管理員帳號登入

#### 7.2 測試表單管理功能

1. **進入表單管理頁面**
   - 點擊側邊欄「📋 表單管理」
   - 應該看到表單列表頁面

2. **創建測試表單**
   - 點擊「新增表單」按鈕
   - 填寫表單資訊
   - 新增欄位
   - 儲存表單

3. **查看表單提交記錄**
   - 點擊側邊欄「📝 表單提交」
   - 應該看到提交記錄列表（可能為空）

#### 7.3 測試業者表單頁面

1. **進入業者管理頁面**
   - 點擊側邊欄「業者管理」
   - 應該看到新的「📋 表單」欄位

2. **訪問業者表單頁面**
   - 點擊任一業者的「📋 表單」按鈕
   - 應該開啟新分頁，顯示該業者的表單提交記錄
   - 頁面應該是獨立的（沒有系統側邊欄）

3. **測試狀態管理**
   - 點擊「詳情」查看某個提交記錄
   - 應該可以修改狀態和備註
   - 儲存後狀態應該更新

4. **測試搜尋和篩選**
   - 使用搜尋輸入框搜尋關鍵字
   - 使用狀態下拉選單篩選
   - 結果應該即時更新

#### 7.4 測試聊天表單填寫

1. **訪問業者聊天頁面**
   - 訪問：`http://your-domain/VENDOR_CODE/chat`
   - 例如：`http://your-domain/jgb/chat`

2. **觸發表單**
   - 輸入與表單相關的問題（根據 trigger_intents）
   - 系統應該啟動表單填寫流程
   - 依序回答表單問題

3. **測試離題處理**
   - 在填寫表單中途，詢問其他問題
   - 系統應該提示是否要離題或繼續填表

---

## ✅ 部署驗證清單

### 基礎服務
- [ ] 所有 Docker 容器正常運行
- [ ] 資料庫遷移全部成功
- [ ] 沒有服務錯誤日誌

### 後端功能
- [ ] `/api/v1/forms` 端點可訪問
- [ ] `/api/v1/form-submissions` 端點可訪問
- [ ] API 文檔顯示新路由

### 前端功能
- [ ] 表單管理頁面可訪問
- [ ] 表單編輯器可訪問
- [ ] 表單提交記錄頁面可訪問（管理端）
- [ ] 業者表單頁面可訪問（業者端）
- [ ] 業者管理頁面顯示「📋 表單」按鈕

### 核心功能
- [ ] 可以創建新表單
- [ ] 可以編輯表單
- [ ] 可以查看表單提交記錄
- [ ] 可以修改提交記錄的狀態和備註
- [ ] 搜尋和篩選功能正常
- [ ] 聊天頁面可以觸發表單填寫

---

## 🐛 常見問題排查

### 問題 1：服務啟動失敗，日誌顯示 ModuleNotFoundError

**原因**：新的 Python 模組沒有正確安裝

**解決方案**：
```bash
# 確保使用 --no-cache 重新構建
docker-compose -f docker-compose.prod.yml build --no-cache rag-orchestrator
docker-compose -f docker-compose.prod.yml up -d
```

---

### 問題 2：前端頁面 404 Not Found

**原因**：前端路由沒有正確配置或前端沒有重新構建

**解決方案**：
```bash
# 重新構建前端
cd knowledge-admin/frontend
npm run build
cd ../..

# 重新啟動前端容器
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web

# 清除瀏覽器緩存
# 按 Ctrl+Shift+R (或 Cmd+Shift+R) 強制刷新
```

---

### 問題 3：API 回應 404 或 500 錯誤

**原因**：資料庫遷移未執行或路由註冊失敗

**檢查步驟**：
```bash
# 1. 檢查資料表是否存在
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U aichatbot -d aichatbot_admin -c "\dt" | grep form

# 2. 檢查後端日誌
docker-compose -f docker-compose.prod.yml logs --tail=100 rag-orchestrator | grep -i error

# 3. 檢查路由註冊
docker-compose -f docker-compose.prod.yml logs rag-orchestrator | grep "forms"
```

---

### 問題 4：業者表單頁面仍顯示系統側邊欄

**原因**：前端代碼未正確更新

**解決方案**：
```bash
# 確認 App.vue 包含 VendorFormSubmissions 路由
docker-compose -f docker-compose.prod.yml exec knowledge-admin-web \
  grep -r "VendorFormSubmissions" /usr/share/nginx/html/assets/

# 如果沒有，重新構建前端
cd knowledge-admin/frontend
npm run build
cd ../..
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
```

---

### 問題 5：表單狀態更新失敗

**原因**：資料庫欄位未正確新增或後端 API 未更新

**檢查步驟**：
```bash
# 1. 檢查資料庫欄位
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U aichatbot -d aichatbot_admin -c "\d form_submissions" | grep status

# 2. 如果欄位不存在，執行遷移
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_form_submission_status.sql

# 3. 重啟後端
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
```

---

## 🔄 回滾步驟（如果部署失敗）

```bash
# 1. 記錄當前問題
docker-compose -f docker-compose.prod.yml logs > /tmp/deploy_error_$(date +%Y%m%d_%H%M%S).log

# 2. 回滾到上一個穩定版本
git log --oneline -10
git checkout b03d649  # 或其他穩定版本

# 3. 停止服務
docker-compose -f docker-compose.prod.yml down

# 4. 重新構建
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 5. 驗證服務
docker-compose -f docker-compose.prod.yml ps
```

---

## 📊 資料庫備份（建議在部署前執行）

```bash
# 備份資料庫
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U aichatbot aichatbot_admin > /tmp/backup_aichatbot_$(date +%Y%m%d_%H%M%S).sql

# 如果需要恢復
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < /tmp/backup_aichatbot_YYYYMMDD_HHMMSS.sql
```

---

## 📝 部署記錄

完成部署後，請記錄以下資訊：

```bash
# 記錄部署版本和時間
cat > /tmp/deploy_record_$(date +%Y%m%d_%H%M%S).txt <<EOF
部署日期: $(date)
部署版本: $(git log --oneline -1)
部署人員: $(whoami)
服務狀態:
$(docker-compose -f docker-compose.prod.yml ps)
EOF

cat /tmp/deploy_record_*.txt | tail -20
```

---

## ⚠️ 重要提醒

1. **資料庫遷移不可逆**：請確保在執行遷移前做好備份
2. **前端必須重新構建**：生產環境使用預構建的 dist 目錄
3. **完整重新構建**：本次更新包含大量新檔案，建議使用 `--no-cache`
4. **測試所有功能**：新增功能較多，請逐一測試
5. **監控日誌**：部署後持續監控服務日誌至少 30 分鐘

---

## 📞 需要協助？

如遇到無法解決的問題：
1. 保存完整的錯誤日誌
2. 記錄執行的步驟
3. 立即回滾到穩定版本
4. 查閱文檔：
   - `DEPLOY_CHECKLIST.md`
   - `docs/DEPLOYMENT_GUIDE.md`
   - `docs/features/FORM_MANAGEMENT_SYSTEM.md`

---

## 📚 相關文檔

- **功能文檔**：`docs/features/FORM_MANAGEMENT_SYSTEM.md`
- **測試報告**：
  - `docs/testing/FORM_REVIEW_EDIT_TEST_REPORT.md`
  - `docs/testing/FORM_STATUS_NOTES_TEST_REPORT.md`
- **設計文檔**：`docs/design/FORM_FILLING_*.md`
- **資料庫遷移**：`database/migrations/*.sql`

---

**部署文檔版本**: 2026-01-10
**適用 commit 範圍**: b03d649 ~ HEAD
**文檔狀態**: ✅ 可用於生產環境部署
