# ⚡ 快速部署指南（2026-01-10）

> 從 commit `b03d649` 開始的完整部署流程

## 📋 快速檢查清單

### 部署前
- [ ] 在服務器上操作
- [ ] 當前在 `/path/to/AIChatbot` 目錄
- [ ] Git 工作目錄乾淨
- [ ] 已備份資料庫（可選但推薦）

---

## 🚀 5 步驟部署

### 1️⃣ 拉取代碼
```bash
cd /path/to/AIChatbot
git pull origin main
```

### 2️⃣ 執行資料庫遷移
```bash
# ⚠️ 重要：知識庫缺失欄位（表單、影片、觸發條件）- 2026-01-12 新增
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_knowledge_base_missing_columns.sql

# 建立表單資料表
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/create_form_tables.sql

# 新增表單描述欄位
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_form_schema_description_fields.sql

# 新增表單會話觸發欄位
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_form_sessions_trigger_fields.sql

# 建立離題檢測配置（注意路徑在 rag-orchestrator 目錄下）
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < rag-orchestrator/database/migrations/create_digression_config.sql

# 新增狀態管理欄位
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_form_submission_status.sql

# 驗證表單資料表
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U aichatbot -d aichatbot_admin -c "\dt" | grep form

# 驗證 knowledge_base 欄位
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U aichatbot -d aichatbot_admin -c "\d knowledge_base" | grep -E "form_id|video_url|trigger_form"
```

**預期**：
- 看到 `form_schemas`, `form_sessions`, `form_submissions` 表
- knowledge_base 包含 form_id, video_url, trigger_form_condition 欄位

### 3️⃣ 構建前端
```bash
cd knowledge-admin/frontend
npm install
npm run build
cd ../..
```

**預期**：看到 `dist` 目錄更新

### 4️⃣ 重新構建服務
```bash
# 停止服務
docker-compose -f docker-compose.prod.yml down

# 重新構建（重要：使用 --no-cache）
docker-compose -f docker-compose.prod.yml build --no-cache

# 啟動服務
docker-compose -f docker-compose.prod.yml up -d
```

**預期**：所有容器啟動成功

### 5️⃣ 驗證部署
```bash
# 檢查服務狀態
docker-compose -f docker-compose.prod.yml ps

# 檢查日誌（無錯誤）
docker-compose -f docker-compose.prod.yml logs --tail=50 rag-orchestrator
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-api

# 測試 API
curl -s http://localhost:8100/api/v1/forms | head -1
```

**預期**：所有服務 `Up`，API 返回 JSON

---

## ✅ 功能驗證

### 管理後台
1. 訪問 `http://your-domain`
2. 登入系統
3. 檢查側邊欄：
   - [ ] 「📋 表單管理」存在
   - [ ] 「📝 表單提交」存在
4. 進入「業者管理」：
   - [ ] 看到「📋 表單」欄位

### 業者頁面
1. 訪問 `http://your-domain/jgb/form-submissions`
2. 檢查：
   - [ ] 頁面沒有系統側邊欄
   - [ ] 可以看到搜尋框和狀態篩選
   - [ ] 點擊「詳情」可以修改狀態和備註

---

## 🐛 快速故障排除

### API 返回 500 錯誤 - 欄位不存在
**症狀**: `column "form_id" does not exist` 或類似錯誤

**解決**:
```bash
# 執行知識庫欄位遷移
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin < database/migrations/add_knowledge_base_missing_columns.sql
```

### 分頁按鈕無法點擊
**症狀**: 前端按鈕無反應，Console 有 Vue 警告

**解決**:
```bash
# 重新 build 前端
cd knowledge-admin/frontend && npm run build && cd ../..
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
```
→ 瀏覽器按 Ctrl+Shift+R 強制刷新

### 服務不斷重啟
```bash
docker-compose -f docker-compose.prod.yml logs --tail=100 [service_name] | grep -i error
```
→ 如果是 ModuleNotFoundError，執行 `docker-compose -f docker-compose.prod.yml build --no-cache`

### 前端 404 錯誤
```bash
cd knowledge-admin/frontend && npm run build && cd ../..
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
```
→ 瀏覽器按 Ctrl+Shift+R 強制刷新

### API 404 錯誤
```bash
docker-compose -f docker-compose.prod.yml logs rag-orchestrator | grep "forms"
```
→ 檢查路由是否註冊，如果沒有則重新構建

### 資料表不存在
```bash
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U aichatbot -d aichatbot_admin -c "\dt" | grep form
```
→ 如果沒有，重新執行步驟 2

---

## 🔄 回滾（如果失敗）

```bash
git checkout b03d649
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

---

## ⏱️ 預估時間

- 拉取代碼：< 1 分鐘
- 資料庫遷移：< 2 分鐘
- 構建前端：2-5 分鐘
- 構建服務：5-10 分鐘
- 驗證測試：5 分鐘

**總計**：約 15-20 分鐘

---

## 📞 完整文檔

詳細步驟和問題排查請參考：`PRODUCTION_DEPLOY_2026-01-10.md`
