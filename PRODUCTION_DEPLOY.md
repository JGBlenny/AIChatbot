# 🚀 生產環境部署步驟（此次更新）

## 📦 更新內容摘要
- ✅ 優化用戶管理 UI（checkbox 樣式統一）
- ✅ 新增角色分配功能
- ✅ 新增管理員創建腳本
- ✅ 修正權限系統相關問題
- ⚠️ **修正 Dockerfile（重要）**：現在會複製所有 Python 文件
- ⚠️ **修正前端 API 配置（重要）**：修正用戶管理和角色管理頁面的 CORS 問題

---

## 🔄 部署步驟

### 步驟 1：拉取最新代碼
```bash
cd /path/to/AIChatbot
git pull origin main
```

### 步驟 2：執行資料庫遷移（重要！）

**此次更新需要執行以下 SQL 遷移：**

#### 2.1 建立 admins 表（如果不存在）
```bash
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_admins_table.sql
```

#### 2.2 建立權限系統表
```bash
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_permission_system.sql
```

#### 2.3 驗證遷移成功
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U aichatbot -d aichatbot_admin -c "\dt" | grep -E "admins|permissions|roles"
```

**預期輸出：**
- admins
- admin_roles
- permissions
- roles
- role_permissions

### 步驟 3：重新構建前端
```bash
cd knowledge-admin/frontend
npm install
npm run build
cd ../..
```

### 步驟 4：重新構建並啟動服務
```bash
cd /path/to/AIChatbot

# 停止舊服務
docker-compose -f docker-compose.prod.yml down

# 重新構建並啟動（會套用新的掛載配置）
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps
```

### 步驟 6：驗證更新
```bash
# 1. 檢查腳本是否掛載成功
docker-compose -f docker-compose.prod.yml exec knowledge-admin-api ls -la /app/create_admin.py

# 2. 檢查服務日誌
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-api
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-web
```

### 步驟 7：測試功能
1. **訪問前端**: `http://your-domain` 或 `http://your-server-ip`
2. **登入系統**: 使用現有管理員帳號
3. **檢查 UI**: 進入「用戶管理」，查看新的樣式
4. **測試角色分配**: 編輯用戶，確認角色選擇功能正常

---

### 步驟 8：創建管理員（如需要）

**如果這是第一次部署，或者還沒有管理員帳號：**

```bash
# 方法 1：交互式創建（推薦）
docker-compose -f docker-compose.prod.yml exec knowledge-admin-api python create_admin.py

# 方法 2：命令行參數
docker-compose -f docker-compose.prod.yml exec knowledge-admin-api python create_admin.py \
  --username admin \
  --password YourSecurePassword123 \
  --email admin@example.com \
  --full-name "系統管理員"
```

---

## 📋 快速命令參考

```bash
# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f [service_name]

# 重啟特定服務
docker-compose -f docker-compose.prod.yml restart knowledge-admin-web
docker-compose -f docker-compose.prod.yml restart knowledge-admin-api

# 停止所有服務
docker-compose -f docker-compose.prod.yml down

# 啟動所有服務
docker-compose -f docker-compose.prod.yml up -d
```

---

## ✨ 此次更新的改進

### UI 優化
- **checkbox 樣式統一**: 啟用帳號、重設密碼、角色選擇都使用相同樣式
- **修正變形問題**: 使用 `flex: 0 0 16px` 確保 checkbox 寬度固定
- **更好的交互**: 支援點擊整行切換 checkbox 狀態
- **統一命名**: 將「系統用戶管理」改為「用戶管理」

### 功能增強
- **角色分配**: 用戶管理支援分配多個角色
- **管理員創建**: 新增便捷的腳本工具
- **權限完整性**: 修正權限系統的各種問題

---

## ⚠️ 注意事項

1. **前端必須重新構建**: 生產環境使用預構建的 dist 目錄
2. **不影響數據**: 此次更新不涉及數據庫結構變更
3. **向下兼容**: 現有用戶和權限不受影響
4. **零停機**: 可在業務低峰期執行，重啟約 30 秒

---

## 🔍 常見問題

### Q1: 前端沒有更新？
**A**: 檢查 dist 目錄是否正確上傳並掛載：
```bash
docker-compose -f docker-compose.prod.yml exec knowledge-admin-web ls -la /usr/share/nginx/html
```

### Q2: 腳本無法執行？
**A**: 確認腳本已正確掛載和權限：
```bash
docker-compose -f docker-compose.prod.yml exec knowledge-admin-api ls -la /app/create_admin.py
```

### Q3: 角色選擇器是空的？
**A**: 檢查數據庫中是否有角色：
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U aichatbot -d aichatbot_admin -c "SELECT * FROM roles"
```

---

## 📞 需要協助？

如遇問題：
1. 查看服務日誌
2. 檢查文檔：`docs/DEPLOYMENT_GUIDE.md`
3. 確認所有依賴服務正常運行
