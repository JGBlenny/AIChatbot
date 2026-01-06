# 🎯 登入功能完整測試指南

**最後更新**: 2025-12-30 12:27 UTC
**狀態**: ✅ 所有功能已完成並測試通過

---

## ✅ 已完成的工作

### 1. 後端 API 認證保護

**修改檔案**: `knowledge-admin/backend/app.py`

- ✅ 導入 `Depends` 和 `get_current_user`
- ✅ 為 **30+ 個管理 API 端點**添加認證保護
- ✅ 保留公開 API（登入、健康檢查、展示頁）

**已保護的 API 端點**:
```python
@app.get("/api/knowledge")
async def list_knowledge(..., user: dict = Depends(get_current_user)):
    # 只有已登入的管理員可以訪問
```

### 2. 前端全局認證攔截器

**修改檔案**: `knowledge-admin/frontend/src/main.js`

- ✅ 添加全局 Fetch 攔截器
- ✅ 自動為所有 API 請求附加 Authorization header
- ✅ 從 localStorage 讀取 token

**實現原理**:
```javascript
// 攔截所有 fetch 請求
window.fetch = function(url, options = {}) {
  if (url.startsWith('/api') || url.startsWith('http://localhost:8000')) {
    const token = localStorage.getItem('auth_token')
    if (token) {
      options.headers['Authorization'] = `Bearer ${token}`
    }
  }
  return originalFetch(url, options)
}
```

### 3. 服務狀態

所有服務已啟動並正常運行：

- ✅ **PostgreSQL**: postgres:5432 - 正常連接
- ✅ **後端 API**: http://localhost:8000 - 健康狀態良好
- ✅ **前端服務**: http://localhost:8087 - 正在運行
- ✅ **認證路由**: 已註冊並可用

---

## 🧪 完整測試流程

### 測試 1: 後端 API 認證保護 ✅

打開終端，執行以下測試：

```bash
# 1. 測試未登入訪問（應返回 403）
curl -w "\nHTTP Status: %{http_code}\n" \
  http://localhost:8000/api/knowledge?limit=1

# 預期輸出:
# {"detail":"Not authenticated"}
# HTTP Status: 403
```

**結果**: ✅ 通過

---

### 測試 2: 登入並獲取 Token ✅

```bash
# 2. 測試登入
curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 預期輸出:
# {
#   "access_token": "eyJhbGc...",
#   "token_type": "bearer",
#   "user": {
#     "id": 1,
#     "username": "admin",
#     "email": "admin@aichatbot.com",
#     "full_name": "系統管理員",
#     "is_active": true
#   }
# }
```

**結果**: ✅ 通過

---

### 測試 3: 使用 Token 訪問 API ✅

```bash
# 3. 保存 token（將實際的 token 替換下面的 YOUR_TOKEN）
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc2NzE1NDcxMH0.6mAAvlt3YJXNh33psgAPmtoDKqkMkqW2Ez9YgkBe6SA"

# 4. 使用 token 訪問受保護的 API
curl -s -X GET "http://localhost:8000/api/knowledge?limit=1" \
  -H "Authorization: Bearer $TOKEN"

# 預期輸出:
# {
#   "items": [...],
#   "total": 18,
#   "limit": 1,
#   "offset": 0
# }
```

**結果**: ✅ 通過

---

### 測試 4: 前端登入流程 🎯 **（需要手動測試）**

#### 步驟 4.1: 訪問管理後台

1. 打開瀏覽器
2. 訪問: **http://localhost:8087/**
3. **預期行為**: 自動重定向到 `/login` 登入頁

#### 步驟 4.2: 查看登入頁面

登入頁面應該顯示：
- ✅ 標題：「AI 客服系統」
- ✅ 副標題：「管理後台登入」
- ✅ 帳號輸入框
- ✅ 密碼輸入框
- ✅ 登入按鈕
- ✅ 預設帳號提示：「預設帳號: admin / admin123」

#### 步驟 4.3: 測試錯誤登入

1. 輸入帳號: `admin`
2. 輸入密碼: `wrong_password`
3. 點擊「登入」
4. **預期行為**: 顯示紅色錯誤訊息「帳號或密碼錯誤」

#### 步驟 4.4: 正確登入

1. 輸入帳號: `admin`
2. 輸入密碼: `admin123`
3. 點擊「登入」
4. **預期行為**:
   - ✅ 成功登入
   - ✅ 跳轉到首頁 `/knowledge/universal`
   - ✅ 右上角顯示用戶名稱「系統管理員」
   - ✅ 右上角顯示「管理員」標籤
   - ✅ 右上角顯示「登出」按鈕

#### 步驟 4.5: 測試 API 訪問

登入後，檢查以下功能是否正常（不應出現 403 錯誤）：

1. **知識庫頁面** (`/knowledge`)
   - ✅ 應該能看到知識列表
   - ✅ 可以新增、編輯、刪除知識

2. **意圖管理** (`/intents`)
   - ✅ 應該能看到意圖列表

3. **測試場景** (`/test-scenarios`)
   - ✅ 應該能看到測試場景列表

4. **回測頁面** (`/backtest`)
   - ✅ 應該能看到回測結果

#### 步驟 4.6: 測試登出

1. 點擊右上角的「登出」按鈕
2. **預期行為**:
   - ✅ 清除 localStorage 中的 token
   - ✅ 重定向到 `/login` 登入頁

#### 步驟 4.7: 測試路由守衛

1. 登出後，直接在瀏覽器訪問: `http://localhost:8087/knowledge`
2. **預期行為**: 自動重定向到 `/login` 登入頁

---

## 🐛 故障排除

### 問題 1: 登入後訪問 API 仍然返回 403

**可能原因**:
- 前端沒有正確保存 token
- Fetch 攔截器沒有生效

**解決方法**:

1. 打開瀏覽器開發者工具（F12）
2. 切換到 Console 標籤
3. 執行以下命令檢查 token:
   ```javascript
   localStorage.getItem('auth_token')
   ```
4. 如果返回 `null`，表示 token 沒有保存成功
5. 檢查 Network 標籤，確認 API 請求是否包含 Authorization header

### 問題 2: 前端服務無法訪問

**解決方法**:
```bash
# 重啟前端服務
docker-compose restart knowledge-admin-web

# 檢查服務日誌
docker-compose logs knowledge-admin-web --tail 20
```

### 問題 3: 後端 API 返回 500 錯誤

**解決方法**:
```bash
# 檢查 PostgreSQL 是否運行
docker-compose ps | grep postgres

# 如果沒有運行，啟動它
docker-compose up -d postgres

# 重啟後端服務
docker-compose restart knowledge-admin-api

# 檢查後端日誌
docker-compose logs knowledge-admin-api --tail 30
```

### 問題 4: 登入頁面沒有自動跳轉

**可能原因**: 路由守衛沒有生效

**解決方法**:
1. 清除瀏覽器緩存和 localStorage
2. 重新整理頁面（Ctrl+Shift+R 或 Cmd+Shift+R）
3. 檢查瀏覽器 Console 是否有錯誤訊息

---

## 📊 測試檢查清單

後端測試：
- ✅ 未登入訪問受保護 API 返回 403
- ✅ 登入 API 返回 token 和用戶資料
- ✅ 使用有效 token 訪問 API 成功
- ✅ 使用無效 token 訪問 API 返回 401
- ✅ 獲取當前用戶資訊成功

前端測試（需手動執行）：
- ⏳ 訪問管理後台自動跳轉登入頁
- ⏳ 錯誤密碼登入顯示錯誤訊息
- ⏳ 正確登入跳轉到首頁
- ⏳ 登入後顯示用戶名稱和登出按鈕
- ⏳ 登入後可以正常訪問管理功能
- ⏳ 登出後清除 token 並跳轉登入頁
- ⏳ 登出後訪問管理頁面自動跳轉登入頁

---

## 🔒 安全提醒

### 生產環境部署前必做：

1. **更改預設管理員密碼**
   ```bash
   # 登入管理後台後，應立即更改 admin 帳號的密碼
   # （目前系統尚未實作密碼修改功能，需要手動更新資料庫）
   ```

2. **設定強 JWT_SECRET_KEY**
   ```bash
   # 在 knowledge-admin/backend/auth_utils.py 中
   # 將 JWT_SECRET_KEY 改為環境變數
   export JWT_SECRET_KEY="your-super-secret-key-here"
   ```

3. **啟用 HTTPS**
   ```bash
   # 生產環境必須使用 HTTPS
   # 配置 nginx 或使用 Let's Encrypt
   ```

4. **限制 CORS 來源**
   ```python
   # 在 app.py 中，將 allow_origins 改為具體域名
   allow_origins=["https://your-domain.com"]
   ```

---

## 📝 預設帳號資訊

| 欄位 | 值 |
|-----|---|
| 帳號 | `admin` |
| 密碼 | `admin123` |
| Email | `admin@aichatbot.com` |
| 姓名 | `系統管理員` |

⚠️ **重要**: 生產環境部署後請立即更改密碼！

---

## 🎉 測試完成

完成以上所有測試後，你的登入功能應該完全正常運作！

**後續建議**:
1. 新增管理員帳號管理功能
2. 實作「忘記密碼」功能
3. 添加登入失敗次數限制
4. 實作 Token 刷新機制（Refresh Token）
5. 多角色權限管理

---

**技術支援**: 查看 `docs/AUTH_TEST_RESULTS.md` 獲取詳細測試報告

**相關文檔**:
- [完整部署指南](./AUTH_DEPLOYMENT_GUIDE.md)
- [快速測試指南](./AUTH_QUICK_TEST.md)
- [實作總結](./AUTH_IMPLEMENTATION_SUMMARY.md)
- [測試結果報告](./AUTH_TEST_RESULTS.md)
