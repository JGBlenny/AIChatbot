# 管理員人員管理功能規劃

**規劃日期**: 2025-12-30
**版本**: 1.0.0
**狀態**: 📋 規劃中

---

## 📋 目錄

1. [功能概述](#功能概述)
2. [資料庫設計](#資料庫設計)
3. [後端 API 設計](#後端-api-設計)
4. [前端頁面設計](#前端頁面設計)
5. [安全性設計](#安全性設計)
6. [用戶體驗設計](#用戶體驗設計)
7. [實作步驟](#實作步驟)
8. [測試計畫](#測試計畫)

---

## 🎯 功能概述

### 目標
為管理後台添加完整的管理員帳號管理功能，讓管理員能夠自行管理其他管理員帳號，而無需直接操作資料庫。

### 核心功能
- ✅ 管理員列表查看（含搜尋、篩選）
- ✅ 新增管理員帳號
- ✅ 編輯管理員資料
- ✅ 啟用/停用管理員帳號
- ✅ 重設管理員密碼
- ✅ 查看管理員最後登入時間

### 使用者角色
- **超級管理員**（目前的 admin）：可以管理所有管理員
- **一般管理員**（未來擴展）：僅能查看，無法編輯

---

## 🗄️ 資料庫設計

### 現有 `admins` 表結構

```sql
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ✅ 評估：表結構已完整

現有欄位已足夠支援人員管理功能：
- ✅ `id` - 主鍵
- ✅ `username` - 登入帳號（唯一）
- ✅ `password_hash` - bcrypt 加密密碼
- ✅ `email` - Email（可用於通知）
- ✅ `full_name` - 顯示名稱
- ✅ `is_active` - 啟用狀態
- ✅ `last_login_at` - 最後登入時間
- ✅ `created_at` - 創建時間
- ✅ `updated_at` - 更新時間

### 建議擴展欄位（可選，未來實作）

```sql
-- Phase 2: 進階權限管理（未來）
ALTER TABLE admins ADD COLUMN role VARCHAR(20) DEFAULT 'admin';
-- 可能值: 'super_admin', 'admin', 'viewer'

-- Phase 2: 審計追蹤（未來）
ALTER TABLE admins ADD COLUMN created_by INTEGER REFERENCES admins(id);
ALTER TABLE admins ADD COLUMN updated_by INTEGER REFERENCES admins(id);
```

**本次實作**: 使用現有表結構即可，無需擴展。

---

## 🔌 後端 API 設計

### API 端點規劃

#### 1. 列出所有管理員
```
GET /api/admins
```

**Query Parameters**:
- `search` (optional): 搜尋關鍵字（搜尋 username, email, full_name）
- `is_active` (optional): 篩選啟用狀態 (true/false/all)
- `limit` (optional): 每頁筆數（預設 50）
- `offset` (optional): 偏移量（預設 0）

**Response**:
```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@aichatbot.com",
      "full_name": "系統管理員",
      "is_active": true,
      "last_login_at": "2025-12-30T12:00:00",
      "created_at": "2024-12-19T10:00:00",
      "updated_at": "2025-12-30T12:00:00"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

**注意**: 不返回 `password_hash`

---

#### 2. 獲取單一管理員資料
```
GET /api/admins/{admin_id}
```

**Response**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@aichatbot.com",
  "full_name": "系統管理員",
  "is_active": true,
  "last_login_at": "2025-12-30T12:00:00",
  "created_at": "2024-12-19T10:00:00",
  "updated_at": "2025-12-30T12:00:00"
}
```

---

#### 3. 新增管理員
```
POST /api/admins
```

**Request Body**:
```json
{
  "username": "manager",
  "password": "Manager@123",
  "email": "manager@example.com",
  "full_name": "經理"
}
```

**Validation Rules**:
- `username`: 必填，3-50 字元，只能包含英數字和底線，唯一
- `password`: 必填，至少 8 字元，必須包含大小寫字母和數字
- `email`: 選填，必須是有效 Email 格式
- `full_name`: 選填，最多 100 字元

**Response** (201 Created):
```json
{
  "id": 2,
  "username": "manager",
  "email": "manager@example.com",
  "full_name": "經理",
  "is_active": true,
  "created_at": "2025-12-30T13:00:00"
}
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "帳號已存在"
}
```

---

#### 4. 更新管理員資料
```
PUT /api/admins/{admin_id}
```

**Request Body**:
```json
{
  "email": "new-email@example.com",
  "full_name": "新名稱",
  "is_active": false
}
```

**注意**:
- 不允許修改 `username`（帳號創建後不可變）
- 不允許在此 API 修改密碼（使用專用的重設密碼 API）

**Response** (200 OK):
```json
{
  "id": 2,
  "username": "manager",
  "email": "new-email@example.com",
  "full_name": "新名稱",
  "is_active": false,
  "updated_at": "2025-12-30T14:00:00"
}
```

---

#### 5. 重設管理員密碼
```
POST /api/admins/{admin_id}/reset-password
```

**Request Body**:
```json
{
  "new_password": "NewPassword@123"
}
```

**Validation Rules**:
- `new_password`: 必填，至少 8 字元，必須包含大小寫字母和數字

**Response** (200 OK):
```json
{
  "message": "密碼已重設成功"
}
```

**安全性**:
- 管理員不能重設自己的密碼（必須使用「修改密碼」功能）
- 記錄操作日誌

---

#### 6. 刪除管理員（軟刪除）
```
DELETE /api/admins/{admin_id}
```

**實作方式**: 軟刪除（設定 `is_active = false`）

**Response** (200 OK):
```json
{
  "message": "管理員已停用"
}
```

**Error Response** (403 Forbidden):
```json
{
  "detail": "無法停用自己的帳號"
}
```

---

#### 7. 修改自己的密碼
```
POST /api/admins/me/change-password
```

**Request Body**:
```json
{
  "current_password": "OldPassword@123",
  "new_password": "NewPassword@123"
}
```

**Response** (200 OK):
```json
{
  "message": "密碼修改成功"
}
```

**Error Response** (401 Unauthorized):
```json
{
  "detail": "舊密碼錯誤"
}
```

---

### API 權限設計

| API 端點 | 需要認證 | 權限要求 | 備註 |
|---------|---------|---------|------|
| GET /api/admins | ✅ | 已登入管理員 | 可查看所有管理員 |
| GET /api/admins/{id} | ✅ | 已登入管理員 | 可查看單一管理員 |
| POST /api/admins | ✅ | 已登入管理員 | 可新增管理員 |
| PUT /api/admins/{id} | ✅ | 已登入管理員 | 可編輯管理員 |
| POST /api/admins/{id}/reset-password | ✅ | 已登入管理員 | 不能重設自己 |
| DELETE /api/admins/{id} | ✅ | 已登入管理員 | 不能刪除自己 |
| POST /api/admins/me/change-password | ✅ | 已登入管理員 | 修改自己密碼 |

**未來擴展**: 可加入角色權限（super_admin / admin / viewer）

---

## 🎨 前端頁面設計

### 1. 管理員列表頁

**路由**: `/admin-management`

**頁面結構**:
```
┌─────────────────────────────────────────────────────┐
│ 🔍 搜尋管理員...                    [新增管理員 +]   │
├─────────────────────────────────────────────────────┤
│ 篩選: [全部 ▼] [啟用狀態 ▼]                        │
├─────────────────────────────────────────────────────┤
│ ID │ 帳號    │ 姓名    │ Email │ 狀態 │ 最後登入 │ 操作 │
├────┼────────┼────────┼──────┼─────┼─────────┼─────┤
│ 1  │ admin  │ 系統... │ a... │ ✅   │ 2分鐘前  │ 編輯 │
│ 2  │ manager│ 經理   │ m... │ ✅   │ 1小時前  │ 編輯 │
│ 3  │ viewer │ 查看者 │ v... │ ❌   │ 3天前    │ 編輯 │
└─────────────────────────────────────────────────────┘
│ 顯示 1-3 / 共 3 筆                    [< 上一頁 下一頁 >] │
└─────────────────────────────────────────────────────┘
```

**功能列表**:
- ✅ 搜尋（帳號、姓名、Email）
- ✅ 篩選（全部/啟用/停用）
- ✅ 分頁
- ✅ 排序（按創建時間、最後登入時間）
- ✅ 操作按鈕（編輯、重設密碼、停用/啟用）

---

### 2. 新增管理員表單

**彈出式對話框** (Modal)

```
┌──────────────────────────────────────┐
│ 新增管理員                      [✕]   │
├──────────────────────────────────────┤
│                                      │
│ 帳號 *                               │
│ [________________]                   │
│ 3-50 字元，只能包含英數字和底線       │
│                                      │
│ 密碼 *                               │
│ [________________] [👁️]              │
│ 至少 8 字元，需包含大小寫字母和數字   │
│                                      │
│ 姓名                                 │
│ [________________]                   │
│                                      │
│ Email                                │
│ [________________]                   │
│                                      │
│         [取消]  [確認新增]            │
└──────────────────────────────────────┘
```

**驗證規則**:
- 帳號: 即時檢查是否已存在（debounce 500ms）
- 密碼: 即時顯示強度指示器（弱/中/強）
- Email: 格式驗證

---

### 3. 編輯管理員表單

**彈出式對話框** (Modal)

```
┌──────────────────────────────────────┐
│ 編輯管理員 - admin              [✕]   │
├──────────────────────────────────────┤
│                                      │
│ 帳號                                 │
│ [admin] (不可修改)                   │
│                                      │
│ 姓名                                 │
│ [系統管理員___]                      │
│                                      │
│ Email                                │
│ [admin@aichatbot.com]                │
│                                      │
│ 狀態                                 │
│ [✅ 啟用]  [ ] 停用                   │
│                                      │
│ 創建時間: 2024-12-19 10:00:00        │
│ 最後登入: 2025-12-30 12:00:00        │
│                                      │
│         [取消]  [儲存變更]            │
└──────────────────────────────────────┘
```

**注意**:
- 帳號欄位為只讀
- 如果是編輯自己，顯示警告「你正在編輯自己的帳號」
- 不能停用自己

---

### 4. 重設密碼對話框

**彈出式對話框** (Modal)

```
┌──────────────────────────────────────┐
│ 重設密碼 - manager              [✕]   │
├──────────────────────────────────────┤
│                                      │
│ ⚠️  此操作將重設 manager 的密碼       │
│                                      │
│ 新密碼 *                             │
│ [________________] [👁️]              │
│ 至少 8 字元，需包含大小寫字母和數字   │
│                                      │
│ 確認新密碼 *                         │
│ [________________] [👁️]              │
│                                      │
│         [取消]  [確認重設]            │
└──────────────────────────────────────┘
```

**驗證**:
- 兩次密碼必須一致
- 密碼強度檢查
- 不能重設自己的密碼（使用「修改密碼」功能）

---

### 5. 修改自己的密碼

**路由**: 在右上角用戶選單中

```
┌──────────────────────────────────────┐
│ 修改密碼                        [✕]   │
├──────────────────────────────────────┤
│                                      │
│ 舊密碼 *                             │
│ [________________] [👁️]              │
│                                      │
│ 新密碼 *                             │
│ [________________] [👁️]              │
│ 至少 8 字元，需包含大小寫字母和數字   │
│                                      │
│ 確認新密碼 *                         │
│ [________________] [👁️]              │
│                                      │
│         [取消]  [確認修改]            │
└──────────────────────────────────────┘
```

---

### 6. 確認對話框

**停用管理員**:
```
┌──────────────────────────────────────┐
│ ⚠️  確認停用管理員                    │
├──────────────────────────────────────┤
│                                      │
│ 確定要停用管理員「manager」嗎？       │
│                                      │
│ 停用後該管理員將無法登入系統。        │
│ 你可以隨時重新啟用此帳號。            │
│                                      │
│         [取消]  [確認停用]            │
└──────────────────────────────────────┘
```

---

## 🔒 安全性設計

### 1. 密碼安全

**密碼強度要求**:
- 最少 8 字元
- 必須包含大寫字母（A-Z）
- 必須包含小寫字母（a-z）
- 必須包含數字（0-9）
- 建議包含特殊字元（!@#$%^&*）

**密碼加密**:
- 使用 bcrypt，12 rounds
- 密碼永不明文儲存
- 密碼永不通過 API 返回

**正則驗證**:
```python
# 至少 8 字元，包含大小寫字母和數字
PASSWORD_PATTERN = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'
```

---

### 2. 帳號保護

**防止自我刪除**:
```python
# 後端檢查
if admin_id == current_user["id"]:
    raise HTTPException(status_code=403, detail="無法停用自己的帳號")
```

**防止重設自己密碼**:
```python
# 重設密碼 API 檢查
if admin_id == current_user["id"]:
    raise HTTPException(status_code=403, detail="請使用「修改密碼」功能")
```

---

### 3. 操作審計

**記錄關鍵操作** (未來實作):
- 管理員創建
- 管理員停用/啟用
- 密碼重設

**審計日誌格式** (未來):
```json
{
  "action": "admin_created",
  "operator_id": 1,
  "operator_name": "admin",
  "target_id": 2,
  "target_name": "manager",
  "timestamp": "2025-12-30T13:00:00",
  "ip_address": "192.168.1.1"
}
```

---

### 4. API 速率限制（未來）

防止暴力破解和濫用：
- 新增管理員: 10 次/小時
- 重設密碼: 5 次/小時
- 修改密碼: 5 次/小時

---

## 🎨 用戶體驗設計

### 1. 即時反饋

**表單驗證**:
- ✅ 即時驗證（輸入時）
- ✅ 顯示錯誤訊息（紅色，圖示）
- ✅ 顯示成功狀態（綠色，圖示）

**操作反饋**:
- ✅ Loading 狀態（按鈕顯示 spinner）
- ✅ 成功提示（Toast 通知，3 秒後消失）
- ✅ 錯誤提示（Toast 通知，需手動關閉）

---

### 2. 密碼強度指示器

```
密碼: [________________]
      ████░░░░░░ 弱 (40%)
```

**強度評分**:
- 長度 >= 8: +20%
- 長度 >= 12: +10%
- 包含大寫: +20%
- 包含小寫: +20%
- 包含數字: +20%
- 包含特殊字元: +10%

---

### 3. 確認對話框

**關鍵操作需要確認**:
- ✅ 停用管理員
- ✅ 重設密碼
- ❌ 新增管理員（直接提交）
- ❌ 編輯資料（直接提交）

---

### 4. 錯誤處理

**友善的錯誤訊息**:
```javascript
// 後端錯誤訊息映射
const ERROR_MESSAGES = {
  'DUPLICATE_USERNAME': '此帳號已存在，請使用其他帳號',
  'WEAK_PASSWORD': '密碼強度不足，請包含大小寫字母和數字',
  'INVALID_EMAIL': 'Email 格式不正確',
  'CANNOT_DISABLE_SELF': '無法停用自己的帳號',
  'WRONG_PASSWORD': '舊密碼錯誤'
}
```

---

### 5. 空狀態

**沒有管理員時**:
```
┌─────────────────────────────────────┐
│                                     │
│        👥                           │
│     尚無管理員帳號                   │
│                                     │
│   [+ 新增第一個管理員]               │
│                                     │
└─────────────────────────────────────┘
```

---

## 🚀 實作步驟

### Phase 1: 後端 API（第 1-2 天）

#### Step 1.1: 創建管理員路由文件
**檔案**: `knowledge-admin/backend/routes_admins.py`

- [ ] 導入必要套件
- [ ] 建立 Pydantic 模型（Request/Response）
- [ ] 實作密碼驗證函數
- [ ] 實作 7 個 API 端點

**預估時間**: 3 小時

---

#### Step 1.2: 註冊路由到主應用
**檔案**: `knowledge-admin/backend/app.py`

- [ ] 導入 `routes_admins`
- [ ] 註冊路由 `app.include_router(admins_router)`

**預估時間**: 10 分鐘

---

#### Step 1.3: 更新登入邏輯記錄最後登入時間
**檔案**: `knowledge-admin/backend/routes_auth.py`

- [ ] 在登入成功後更新 `last_login_at`

**預估時間**: 15 分鐘

---

### Phase 2: 前端頁面（第 3-4 天）

#### Step 2.1: 創建管理員列表頁
**檔案**: `knowledge-admin/frontend/src/views/AdminManagementView.vue`

- [ ] 實作頁面佈局
- [ ] 實作搜尋功能
- [ ] 實作篩選功能
- [ ] 實作分頁
- [ ] 實作表格顯示
- [ ] 整合 API 調用

**預估時間**: 4 小時

---

#### Step 2.2: 創建新增/編輯對話框組件
**檔案**: `knowledge-admin/frontend/src/components/AdminFormModal.vue`

- [ ] 實作表單佈局
- [ ] 實作表單驗證
- [ ] 實作密碼強度指示器
- [ ] 整合 API 調用

**預估時間**: 3 小時

---

#### Step 2.3: 創建重設密碼對話框
**檔案**: `knowledge-admin/frontend/src/components/ResetPasswordModal.vue`

- [ ] 實作表單佈局
- [ ] 實作密碼驗證
- [ ] 整合 API 調用

**預估時間**: 1 小時

---

#### Step 2.4: 創建修改密碼對話框
**檔案**: `knowledge-admin/frontend/src/components/ChangePasswordModal.vue`

- [ ] 實作表單佈局
- [ ] 實作舊密碼驗證
- [ ] 整合 API 調用
- [ ] 添加到用戶選單

**預估時間**: 1.5 小時

---

#### Step 2.5: 添加路由
**檔案**: `knowledge-admin/frontend/src/router.js`

- [ ] 添加 `/admin-management` 路由
- [ ] 設定權限保護

**預估時間**: 10 分鐘

---

#### Step 2.6: 添加導航選單
**檔案**: `knowledge-admin/frontend/src/App.vue`

- [ ] 在側邊欄添加「人員管理」連結

**預估時間**: 15 分鐘

---

### Phase 3: 測試（第 5 天）

#### Step 3.1: 後端單元測試
- [ ] 測試所有 API 端點
- [ ] 測試驗證規則
- [ ] 測試安全性限制

**預估時間**: 2 小時

---

#### Step 3.2: 前端功能測試
- [ ] 測試列表查詢
- [ ] 測試新增管理員
- [ ] 測試編輯管理員
- [ ] 測試重設密碼
- [ ] 測試修改密碼
- [ ] 測試停用/啟用

**預估時間**: 2 小時

---

#### Step 3.3: 整合測試
- [ ] 測試完整用戶流程
- [ ] 測試錯誤處理
- [ ] 測試邊界條件

**預估時間**: 1 小時

---

### Phase 4: 文檔（第 5 天）

#### Step 4.1: 創建使用手冊
**檔案**: `docs/ADMIN_MANAGEMENT_GUIDE.md`

- [ ] 功能說明
- [ ] 操作步驟
- [ ] 常見問題

**預估時間**: 1 小時

---

#### Step 4.2: 更新 API 文檔
**檔案**: `docs/API_DOCUMENTATION.md`

- [ ] 添加管理員管理 API 說明

**預估時間**: 30 分鐘

---

## 📊 預估時間表

| 階段 | 任務 | 預估時間 | 累計時間 |
|-----|------|---------|---------|
| **Phase 1** | 後端 API 開發 | 3.5 小時 | 3.5 小時 |
| **Phase 2** | 前端頁面開發 | 10 小時 | 13.5 小時 |
| **Phase 3** | 測試 | 5 小時 | 18.5 小時 |
| **Phase 4** | 文檔 | 1.5 小時 | 20 小時 |

**總預估時間**: 20 小時（約 2.5 個工作日）

---

## 🧪 測試計畫

### 後端 API 測試案例

#### 1. GET /api/admins
- [ ] 返回所有管理員列表
- [ ] 搜尋功能正常
- [ ] 篩選功能正常
- [ ] 分頁功能正常
- [ ] 不返回 password_hash

#### 2. POST /api/admins
- [ ] 成功創建管理員
- [ ] 帳號重複返回錯誤
- [ ] 密碼強度驗證
- [ ] Email 格式驗證

#### 3. PUT /api/admins/{id}
- [ ] 成功更新管理員資料
- [ ] 不允許修改 username
- [ ] 不允許修改 password

#### 4. POST /api/admins/{id}/reset-password
- [ ] 成功重設密碼
- [ ] 不能重設自己的密碼
- [ ] 密碼強度驗證

#### 5. DELETE /api/admins/{id}
- [ ] 成功停用管理員
- [ ] 不能停用自己

#### 6. POST /api/admins/me/change-password
- [ ] 成功修改自己密碼
- [ ] 舊密碼錯誤返回錯誤
- [ ] 新密碼強度驗證

---

### 前端測試案例

#### 列表頁
- [ ] 正確顯示管理員列表
- [ ] 搜尋功能有效
- [ ] 篩選功能有效
- [ ] 分頁正常切換
- [ ] 狀態標籤正確顯示

#### 新增管理員
- [ ] 表單驗證正確
- [ ] 成功新增後列表更新
- [ ] 錯誤訊息正確顯示
- [ ] 密碼強度指示器正常

#### 編輯管理員
- [ ] 正確載入管理員資料
- [ ] 帳號欄位為只讀
- [ ] 成功更新後列表刷新

#### 重設密碼
- [ ] 確認對話框正確顯示
- [ ] 成功重設顯示提示
- [ ] 不能重設自己

#### 停用/啟用
- [ ] 確認對話框正確顯示
- [ ] 狀態切換成功
- [ ] 不能停用自己

---

## 📋 驗收標準

### 功能完整性
- ✅ 所有 7 個 API 端點正常運作
- ✅ 前端頁面完整實現
- ✅ 所有驗證規則正確執行
- ✅ 錯誤處理完善

### 安全性
- ✅ 密碼正確加密
- ✅ 無法停用/重設自己
- ✅ API 需要認證
- ✅ 敏感資料不外洩

### 用戶體驗
- ✅ 操作流暢，無明顯延遲
- ✅ 錯誤訊息清晰友善
- ✅ 確認對話框適當出現
- ✅ 成功提示明確

### 測試覆蓋
- ✅ 後端測試覆蓋率 > 80%
- ✅ 前端主要流程測試完成
- ✅ 邊界條件測試通過

---

## 🔄 未來擴展

### Phase 2 功能（未來）
- [ ] 角色權限管理（super_admin / admin / viewer）
- [ ] 操作審計日誌
- [ ] 管理員活動追蹤
- [ ] Email 通知（帳號創建、密碼重設）
- [ ] 雙因素認證 (2FA)
- [ ] 登入失敗次數限制
- [ ] API 速率限制
- [ ] 批量操作（批量啟用/停用）

---

## 📎 相關文檔

- [認證功能實作總結](./AUTH_IMPLEMENTATION_SUMMARY.md)
- [認證部署指南](../../guides/deployment/AUTH_DEPLOYMENT_GUIDE.md)
- [API 保護指南](../auth_testing/API_PROTECTION_GUIDE.md)

---

**規劃者**: Claude Code
**規劃日期**: 2025-12-30
**版本**: 1.0.0
**預計實作時間**: 20 小時（2.5 個工作日）
