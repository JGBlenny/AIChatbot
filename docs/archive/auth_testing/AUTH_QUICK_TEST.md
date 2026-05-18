# 登入功能快速測試指南

## 🚀 快速開始

### 1. 執行資料庫遷移

```bash
# 確保 PostgreSQL 正在運行
docker-compose ps postgres

# 執行遷移
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_admins_table.sql
```

**驗證遷移成功**：
```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT username FROM admins;"
```

應該看到：
```
 username
----------
 admin
```

---

### 2. 安裝後端依賴

```bash
cd knowledge-admin/backend
pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4
```

---

### 3. 安裝前端依賴

```bash
cd knowledge-admin/frontend
npm install pinia@^2.1.7
```

---

### 4. 重啟服務

```bash
# 回到項目根目錄
cd ../..

# 重啟 Docker 服務
docker-compose restart knowledge-admin-api knowledge-admin-web
```

---

## ✅ 測試流程

### 測試 1: 後端登入 API

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**預期結果**：返回 JWT token 和用戶資料

---

### 測試 2: 前端登入流程

1. **訪問管理後台**
   ```
   http://localhost:8087/
   ```
   → 應該自動跳轉到 `/login`

2. **登入**
   - 帳號：`admin`
   - 密碼：`admin123`
   - 點擊「登入」

3. **驗證登入成功**
   - 應該跳轉到首頁（知識庫頁面）
   - 可以正常瀏覽管理後台

4. **測試路由保護**
   - 開啟新分頁訪問 `http://localhost:8087/intents`
   - 應該可以正常訪問（因為已登入）

5. **測試展示頁（無需登入）**
   ```
   http://localhost:8087/VENDOR_A/chat
   ```
   → 應該直接顯示展示頁，無需登入

6. **登出測試**
   - 打開瀏覽器開發者工具 Console
   - 執行：
   ```javascript
   localStorage.removeItem('auth_token')
   location.reload()
   ```
   - 應該跳轉回登入頁

---

### 測試 3: Token 驗證

```bash
# 1. 先登入獲取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 2. 使用 token 訪問受保護的 API
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**：返回當前用戶資料

---

### 測試 4: 401 錯誤處理

```bash
# 使用無效 token
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer invalid-token"
```

**預期結果**：
```json
{
  "detail": "Invalid authentication credentials"
}
```

---

## 🐛 常見問題

### 問題：登入後顯示空白頁

**解決方法**：
1. 檢查瀏覽器 Console 是否有錯誤
2. 確認前端已安裝 Pinia：`npm list pinia`
3. 重新 build 前端：
   ```bash
   cd knowledge-admin/frontend
   npm run build
   ```

---

### 問題：登入 API 返回 500 錯誤

**可能原因**：
- Python 套件未安裝
- 資料庫遷移未執行

**解決方法**：
```bash
# 檢查後端日誌
docker-compose logs knowledge-admin-api

# 重新安裝依賴
docker exec aichatbot-knowledge-admin-api pip install python-jose[cryptography] passlib[bcrypt]
```

---

### 問題：前端無法連接後端

**檢查**：
1. 後端是否正常運行
   ```bash
   curl http://localhost:8000/health
   ```

2. CORS 設定是否正確（app.py）
   ```python
   allow_origins=["*"]  # 開發環境
   ```

---

## 📊 功能檢查清單

- [ ] 資料庫遷移成功
- [ ] 後端依賴已安裝
- [ ] 前端依賴已安裝
- [ ] 登入 API 正常工作
- [ ] 前端登入頁面顯示正常
- [ ] 登入成功後跳轉首頁
- [ ] 未登入訪問管理後台跳轉登入頁
- [ ] 展示頁無需登入可訪問
- [ ] Token 驗證正常
- [ ] 登出功能正常

---

## 🔍 調試技巧

### 查看瀏覽器中的 Token

```javascript
// 在瀏覽器 Console 中執行
localStorage.getItem('auth_token')
```

### 解碼 JWT Token

訪問：https://jwt.io/

貼上 token 查看內容

### 檢查 API 請求

1. 打開瀏覽器開發者工具
2. 切換到 Network 標籤
3. 登入時觀察請求
4. 檢查 Request Headers 是否包含 `Authorization: Bearer <token>`

---

## 📝 下一步

測試通過後，可以：

1. **更改預設密碼**
   ```sql
   -- 生成新密碼的 hash（使用 Python）
   from passlib.context import CryptContext
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
   print(pwd_context.hash("new-password"))

   -- 更新密碼
   UPDATE admins SET password_hash = '$2b$12$...' WHERE username = 'admin';
   ```

2. **設定強 JWT 密鑰**
   ```bash
   # 生成密鑰
   openssl rand -hex 32

   # 添加到 .env 或 docker-compose.yml
   JWT_SECRET_KEY=<生成的密鑰>
   ```

3. **新增更多管理員**
   參考：`docs/AUTH_DEPLOYMENT_GUIDE.md`

---

---

## 📎 相關文檔

- [完整測試流程指南](./AUTH_FINAL_TEST_GUIDE.md) ⭐ **推薦**
- [詳細測試報告](./AUTH_TEST_RESULTS.md)
- [實作總結](../implementation/AUTH_IMPLEMENTATION_SUMMARY.md)
- [部署指南](../../guides/deployment/AUTH_DEPLOYMENT_GUIDE.md)

---

**最後更新**: 2025-12-30
**版本**: 2.0.0

**測試完成時間**: _________
**測試人員**: _________
**測試結果**: ✅ 通過 / ❌ 失敗
**備註**: _________
