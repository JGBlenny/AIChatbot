# 管理後台認證系統

## 📋 系統概述

本系統實現了完整的管理員登入認證功能，保護所有管理後台 API。

### 主要功能

- ✅ JWT Token 認證機制
- ✅ bcrypt 密碼加密（12 rounds）
- ✅ 前端路由守衛（未登入自動跳轉）
- ✅ 所有管理 API 受保護
- ✅ 管理員帳號管理（CRUD）
- ✅ 密碼修改與重設功能
- ✅ 展示頁無需登入（客戶訪問）

---

## 🔑 預設帳號

**管理員帳號：**
- 帳號：`admin`
- 密碼：`admin123`

> ⚠️ **生產環境部署前請務必修改預設密碼！**

---

## 📁 系統架構

### 後端組件
```
knowledge-admin/backend/
├── app.py                 # 主應用程式（已添加認證保護）
├── auth_utils.py          # JWT 工具與密碼加密
├── routes_auth.py         # 認證路由（登入、登出、用戶資訊）
└── routes_admins.py       # 管理員管理路由（CRUD）
```

### 前端組件
```
knowledge-admin/frontend/src/
├── views/
│   ├── LoginView.vue              # 登入頁面
│   └── AdminManagementView.vue    # 管理員管理頁面
├── components/
│   ├── AdminFormModal.vue         # 管理員新增/編輯表單
│   ├── ChangePasswordModal.vue    # 修改密碼彈窗
│   └── ResetPasswordModal.vue     # 重設密碼彈窗
├── stores/
│   └── auth.js                    # Pinia 認證狀態管理
├── utils/
│   └── api.js                     # API 請求封裝
├── router.js                      # 路由配置（含守衛）
├── main.js                        # 主入口（Axios 攔截器）
└── App.vue                        # 主組件（登出功能）
```

### 資料庫
```
database/migrations/
└── add_admins_table.sql   # 管理員資料表遷移腳本
```

---

## 🚀 快速開始

### 1. 部署認證系統

請參考：[**AUTH_DEPLOYMENT_GUIDE.md**](./AUTH_DEPLOYMENT_GUIDE.md)

包含：
- 資料庫遷移步驟
- 後端依賴安裝
- 前端依賴安裝
- 服務重啟指令
- 安全配置建議

### 2. 管理員操作

請參考：[**ADMIN_MANAGEMENT_PLAN.md**](./ADMIN_MANAGEMENT_PLAN.md)

包含：
- 新增管理員
- 重設密碼
- 停用/啟用帳號
- 管理員列表查詢

### 3. 實作細節

請參考：[**AUTH_IMPLEMENTATION_SUMMARY.md**](./AUTH_IMPLEMENTATION_SUMMARY.md)

包含：
- 完整的技術架構
- API 端點清單
- 前後端實作細節
- 安全機制說明

---

## 🧪 測試文檔（已歸檔）

測試過程中產生的臨時文檔已移至 `docs/archive/auth_testing/`：

- ✅ AUTH_QUICK_TEST.md - 快速測試指南
- ✅ AUTH_TEST_RESULTS.md - 測試結果報告
- ✅ AUTH_FINAL_TEST_GUIDE.md - 最終測試指南
- ✅ AUTH_DOCUMENTATION_UPDATE_SUMMARY.md - 文檔更新總結
- ✅ API_PROTECTION_GUIDE.md - API 保護教學

這些文檔保留作為歷史參考，日常使用請參考上方的主要文檔。

---

## 🔒 安全建議

### 生產環境部署前必須：

1. **修改預設密碼**
   ```bash
   # 在管理後台介面中修改，或使用 SQL：
   UPDATE admins SET password_hash = '<新密碼的 bcrypt hash>' WHERE username = 'admin';
   ```

2. **設定強 JWT 密鑰**
   ```bash
   # 生成隨機密鑰
   openssl rand -hex 32

   # 設定環境變數或 docker-compose.yml
   JWT_SECRET_KEY=<生成的密鑰>
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_HOURS=24
   ```

3. **啟用 HTTPS**
   - 生產環境必須使用 HTTPS 傳輸
   - Token 僅在 HTTPS 連線中安全

4. **定期更新密碼**
   - 建議每 3-6 個月更換管理員密碼
   - 使用強密碼（至少 12 字元，包含大小寫、數字、符號）

---

## 📊 API 保護範圍

### 受保護的 API（需要登入）

所有管理後台 API 均受保護，包括：
- `/api/knowledge/*` - 知識庫管理
- `/api/intents/*` - 意圖管理
- `/api/backtest/*` - 回測功能
- `/api/test-scenarios/*` - 測試情境
- `/api/vendors/*` - 業者管理
- `/api/admins/*` - 管理員管理

### 公開的 API（無需登入）

- `/api/auth/login` - 登入
- `/api/health` - 健康檢查
- `/:vendorCode/chat` - 展示頁（客戶訪問）

---

## 🐛 疑難排解

### 問題：前端顯示 "Not authenticated"

**解決方法：**
1. 確認已登入
2. 清除瀏覽器緩存：`localStorage.clear()`
3. 重新登入
4. 檢查 Network 標籤是否有 Authorization header

### 問題：登入後跳轉空白頁

**解決方法：**
1. 檢查 Console 是否有錯誤
2. 確認 Pinia 已安裝：`npm list pinia`
3. 重啟前端服務：`docker-compose restart knowledge-admin-web`

### 問題：Token 過期

**預設設定：**
- Token 有效期：24 小時
- 過期後自動跳轉登入頁

**修改有效期：**
```python
# knowledge-admin/backend/auth_utils.py
JWT_EXPIRATION_HOURS = 24  # 修改此值
```

---

## 📞 聯絡資訊

如有問題或建議，請聯絡系統管理員。

---

**文檔版本：** 1.0.0
**最後更新：** 2026-01-06
**維護者：** AIChatbot Team
