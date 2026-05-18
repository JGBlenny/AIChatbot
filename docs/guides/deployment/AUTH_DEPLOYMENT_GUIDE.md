# 登入功能部署指南

## 📋 功能概述

本系統實作了管理員登入認證功能：
- ✅ 管理後台需要登入才能訪問
- ✅ 展示頁（`:vendorCode/chat`）無需登入
- ✅ JWT token 認證
- ✅ bcrypt 密碼加密
- ✅ 前端路由守衛
- ✅ API 自動認證

---

## 🚀 部署步驟

### 步驟 1: 資料庫遷移

執行資料庫遷移腳本以建立 admins 表：

```bash
# 開發環境
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_admins_table.sql

# 生產環境
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_admins_table.sql
```

**預期結果**：
- 建立 `admins` 表
- 插入預設管理員帳號（admin / admin123）

**驗證**：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT username, email, is_active FROM admins;"
```

應該看到：
```
 username |        email        | is_active
----------+---------------------+-----------
 admin    | admin@aichatbot.com | t
```

---

### 步驟 2: 後端依賴安裝

安裝認證相關的 Python 套件：

```bash
cd knowledge-admin/backend
pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

**必要套件**：
- `python-jose[cryptography]` - JWT token 處理
- `passlib[bcrypt]` - 密碼加密

---

### 步驟 3: 環境變數配置

在 `.env` 或 docker-compose 環境變數中添加：

```bash
# JWT 密鑰（生產環境務必更換為強密鑰）
JWT_SECRET_KEY=your-very-secure-secret-key-change-in-production

# API Base URL（前端使用）
VITE_API_BASE_URL=http://localhost:8000
```

**生成強密鑰**：
```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 步驟 4: 前端依賴安裝

安裝 Pinia 狀態管理套件：

```bash
cd knowledge-admin/frontend
npm install pinia@^2.1.7
```

---

### 步驟 5: 驗證全局 Fetch 攔截器

⭐ **重要更新 (2025-12-30)**: 前端已實現全局 Fetch 攔截器，無需修改任何組件即可自動附加認證 token。

檢查 `knowledge-admin/frontend/src/main.js` 是否包含以下代碼：

```javascript
// === 全局 Fetch 攔截器 - 自動附加認證 Token ===
const originalFetch = window.fetch
window.fetch = function(url, options = {}) {
  // 只攔截 API 請求（不攔截外部資源）
  if (url.startsWith('/api') || url.startsWith('http://localhost:8000')) {
    const token = localStorage.getItem('auth_token')
    if (token) {
      // 確保 headers 物件存在
      options.headers = options.headers || {}
      // 添加 Authorization header
      options.headers['Authorization'] = `Bearer ${token}`
    }
  }
  return originalFetch(url, options)
}
```

**如果不存在**，請參考 [AUTH_IMPLEMENTATION_SUMMARY.md](../../archive/implementation/AUTH_IMPLEMENTATION_SUMMARY.md#🌐-全局-fetch-攔截器) 添加此代碼。

---

### 步驟 6: 重建 Docker 容器

```bash
# 開發環境
docker-compose down
docker-compose build knowledge-admin-api knowledge-admin-web
docker-compose up -d

# 生產環境
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build knowledge-admin-api knowledge-admin-web
docker-compose -f docker-compose.prod.yml up -d
```

---

### 步驟 7: 驗證部署

#### 7.1 檢查服務狀態

```bash
# 檢查所有服務是否運行
docker-compose ps

# 檢查後端 API 健康狀態
curl http://localhost:8000/api/health

# 預期輸出: {"status":"healthy","database":"connected",...}
```

#### 7.2 測試後端 API 認證保護

```bash
# 測試未登入訪問（應返回 403）
curl -w "\nHTTP Status: %{http_code}\n" http://localhost:8000/api/knowledge?limit=1

# 預期輸出:
# {"detail":"Not authenticated"}
# HTTP Status: 403
```

#### 7.3 測試登入 API

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**預期回應**：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@aichatbot.com",
    "full_name": "系統管理員",
    "is_active": true
  }
}
```

#### 7.4 測試使用 Token 訪問受保護的 API

```bash
# 先取得 token
TOKEN="<從上面的回應中複製 access_token>"

# 測試 1: 獲取當前用戶資訊
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 預期輸出: {"id":1,"username":"admin",...}

# 測試 2: 訪問知識庫 API
curl http://localhost:8000/api/knowledge?limit=1 \
  -H "Authorization: Bearer $TOKEN"

# 預期輸出: {"items":[...],"total":...}

# 測試 3: 使用無效 token（應返回 401）
curl -w "\nHTTP Status: %{http_code}\n" \
  http://localhost:8000/api/knowledge?limit=1 \
  -H "Authorization: Bearer invalid_token"

# 預期輸出:
# {"detail":"Invalid authentication credentials"}
# HTTP Status: 401
```

#### 7.5 測試前端登入流程

1. 訪問 http://localhost:8087/
2. 應該自動重定向到 http://localhost:8087/login
3. 輸入帳號 `admin`，密碼 `admin123`
4. 登入成功後應跳轉到首頁
5. 訪問展示頁 http://localhost:8087/VENDOR_A/chat 應該無需登入

---

## 🔐 預設管理員帳號

| 欄位 | 值 |
|-----|---|
| 帳號 | admin |
| 密碼 | admin123 |
| Email | admin@aichatbot.com |
| 姓名 | 系統管理員 |

⚠️ **重要**：生產環境部署後請立即更改密碼！

---

## 🛡️ 安全性檢查清單

### 部署前檢查

- [ ] JWT_SECRET_KEY 已更換為強密鑰（至少 32 字元）
- [ ] 預設管理員密碼已更改
- [ ] CORS 設定為正確的域名（生產環境）
- [ ] HTTPS 已啟用（生產環境）

### 部署後檢查

- [ ] 管理後台頁面需要登入
- [ ] 展示頁可以直接訪問（無需登入）
- [ ] 登入/登出功能正常
- [ ] Token 過期後自動跳轉登入頁
- [ ] 401 錯誤正確處理

---

## 📝 管理員帳號管理

### 新增管理員

```sql
-- 登入資料庫
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

-- 新增管理員（密碼需要先用 Python 生成 bcrypt hash）
INSERT INTO admins (username, password_hash, email, full_name)
VALUES (
  'manager',
  '$2b$12$....',  -- 使用 bcrypt hash
  'manager@example.com',
  '經理'
);
```

### 生成密碼 hash

```python
# Python 腳本生成 bcrypt hash
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd_context.hash("your-password")
print(password_hash)
```

### 停用管理員

```sql
UPDATE admins SET is_active = false WHERE username = 'manager';
```

### 更改密碼

```sql
UPDATE admins
SET password_hash = '$2b$12$....'  -- 新的 bcrypt hash
WHERE username = 'admin';
```

---

## 🔧 故障排除

### 問題 1: 登入失敗「帳號或密碼錯誤」

**可能原因**：
- 帳號或密碼輸入錯誤
- 資料庫中沒有該帳號
- 帳號已停用

**解決方法**：
```sql
-- 檢查帳號是否存在
SELECT username, is_active FROM admins WHERE username = 'admin';

-- 重置密碼為 admin123
UPDATE admins
SET password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYuKxLLN.qC'
WHERE username = 'admin';
```

### 問題 2: Token 驗證失敗

**可能原因**：
- JWT_SECRET_KEY 不一致
- Token 已過期
- Token 格式錯誤

**解決方法**：
```bash
# 檢查環境變數
docker exec aichatbot-knowledge-admin-api env | grep JWT_SECRET_KEY

# 重新登入獲取新 token
```

### 問題 3: 前端無法訪問 API

**可能原因**：
- CORS 設定問題
- API Base URL 配置錯誤

**解決方法**：
```bash
# 檢查 CORS 設定（app.py）
# 確認 allow_origins 包含前端域名

# 檢查前端環境變數
echo $VITE_API_BASE_URL
```

### 問題 4: 展示頁需要登入

**可能原因**：
- 路由 meta 設定錯誤

**解決方法**：
檢查 `router.js` 中展示頁路由：
```javascript
{
  path: '/:vendorCode/chat',
  name: 'VendorChatDemo',
  component: VendorChatDemo,
  meta: { requiresAuth: false }  // 確認此行存在
}
```

---

## 📚 API 文檔

### 認證端點

#### POST /api/auth/login
登入並獲取 JWT token

**Request**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@aichatbot.com",
    "full_name": "系統管理員",
    "is_active": true
  }
}
```

#### POST /api/auth/logout
登出（僅記錄用，實際登出由前端清除 token 完成）

**Headers**:
```
Authorization: Bearer <token>
```

**Response**:
```json
{
  "message": "登出成功"
}
```

#### GET /api/auth/me
獲取當前用戶資料

**Headers**:
```
Authorization: Bearer <token>
```

**Response**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@aichatbot.com",
  "full_name": "系統管理員",
  "is_active": true
}
```

---

## 🔄 未來擴展建議

1. **多角色權限** - 不同管理員不同操作權限
2. **忘記密碼功能** - Email 重設密碼
3. **雙因素認證 (2FA)** - 提升安全性
4. **登入歷史記錄** - 審計追蹤
5. **Token 刷新機制** - Refresh token
6. **密碼複雜度要求** - 強制使用強密碼
7. **登入失敗鎖定** - 防止暴力破解

---

## 📎 相關文件

- [完整測試流程指南](../../archive/auth_testing/AUTH_FINAL_TEST_GUIDE.md) ⭐ **推薦**
- [詳細測試報告](../../archive/auth_testing/AUTH_TEST_RESULTS.md)
- [實作總結](../../archive/implementation/AUTH_IMPLEMENTATION_SUMMARY.md)
- [快速測試指南](../../archive/auth_testing/AUTH_QUICK_TEST.md)
- [API 保護指南](../../archive/auth_testing/API_PROTECTION_GUIDE.md)

---

**最後更新**: 2025-12-30
**版本**: 2.0.0
**更新日誌**:
- 2024-12-19: 初版（基礎認證架構）
- 2025-12-30: 添加全局 Fetch 攔截器步驟 + 完整測試驗證流程
