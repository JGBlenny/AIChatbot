# 知識管理 API 參考

## 概述
知識管理 API 提供管理知識庫條目的端點，包括 CRUD 操作和業者特定的知識管理。

## 基本資訊

**基礎 URL：** `http://localhost:8084`

**認證：** 基於 JWT 的認證

**Content-Type：** `application/json`

---

## 目錄

- [認證](#認證)
- [知識管理](#知識管理)
- [業者 API](#業者-api)
- [錯誤處理](#錯誤處理)

---

## 認證

### POST /api/login

使用者登入端點

#### 請求

```json
{
  "username": "admin",
  "password": "password"
}
```

#### 回應

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

---

## 知識管理

### GET /api/knowledge

取得知識庫條目與選擇性篩選

#### 查詢參數

| 參數 | 類型 | 說明 | 預設值 |
|-----------|------|-------------|---------|
| `page` | integer | 頁碼 | 1 |
| `page_size` | integer | 每頁項目數 | 20 |
| `search` | string | 搜尋詞 | - |
| `vendor_id` | integer | 按業者篩選 | - |
| `intent_id` | integer | 按意圖篩選 | - |

#### 回應

```json
{
  "items": [
    {
      "id": 1,
      "question": "如何繳納租金？",
      "answer": "租金可透過轉帳或現金繳納",
      "vendor_id": null,
      "intent_id": 5,
      "trigger_mode": null,
      "created_at": "2026-02-09T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### POST /api/knowledge

建立新的知識條目

#### 請求主體

| 欄位 | 類型 | 必填 | 說明 |
|-------|------|----------|-------------|
| `question` | string | ✅ | 問題文字 |
| `answer` | string | ✅ | 答案文字 |
| `vendor_id` | integer | ❌ | 業者 ID（null 為全域） |
| `intent_id` | integer | ❌ | 關聯的意圖 ID |
| `trigger_mode` | string | ❌ | 觸發模式（null 或特定模式） |

#### 請求範例

```json
{
  "question": "如何申請續約？",
  "answer": "請在合約到期前30天提出申請",
  "vendor_id": null,  // 全域知識
  "intent_id": 10,
  "trigger_mode": null
}
```

#### 回應

```json
{
  "id": 1301,
  "message": "知識創建成功"
}
```

### PUT /api/knowledge/{id}

更新現有的知識條目

#### 請求主體

與 POST /api/knowledge 相同

#### 回應

```json
{
  "message": "知識更新成功"
}
```

### DELETE /api/knowledge/{id}

刪除知識條目

#### 回應

```json
{
  "message": "知識刪除成功"
}
```

---

## 業者 API

### GET /api/vendors

取得所有業者列表以供知識指派

#### 說明

返回系統中所有業者的列表。主要用於知識創建/編輯表單中的業者選擇下拉選單。

#### 請求

**URL：** `GET /api/vendors`

**標頭：**
```
Authorization: Bearer <token>
```

#### 回應

**狀態：** 200 OK

**主體：**
```json
{
  "vendors": [
    {
      "id": 1,
      "name": "業者A"
    },
    {
      "id": 2,
      "name": "業者B"
    },
    {
      "id": 3,
      "name": "業者C"
    }
  ]
}
```

#### 前端使用

此端點用於知識管理 UI 中填充業者選擇下拉選單：

```javascript
// Vue 元件範例
async loadVendors() {
  try {
    const response = await axios.get('/api/vendors', {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });
    this.availableVendors = response.data.vendors;
  } catch (error) {
    console.error('載入業者失敗：', error);
  }
}
```

#### 業者選擇 UI

業者在下拉選單中顯示，並有清楚的視覺指示：
- 🌐 全域知識（vendor_id = null）- 對所有業者可見
- 🏢 業者專屬知識（vendor_id = id）- 僅對該業者可見

---

## 錯誤處理

### 常見錯誤回應

#### 400 錯誤請求
```json
{
  "detail": "無效的請求參數",
  "error_code": "INVALID_REQUEST"
}
```

#### 401 未授權
```json
{
  "detail": "無效或過期的令牌",
  "error_code": "UNAUTHORIZED"
}
```

#### 404 找不到
```json
{
  "detail": "找不到知識條目",
  "error_code": "NOT_FOUND"
}
```

#### 500 內部伺服器錯誤
```json
{
  "detail": "資料庫約束違反",
  "error_code": "DATABASE_ERROR"
}
```

### 特定錯誤情況

#### Trigger Mode 約束違反
- **原因**：設定 trigger_mode 為 'none' 而非 null
- **解決方案**：使用 null 值而非 'none'
- **錯誤訊息**：「新列違反檢查約束 'check_kb_trigger_mode'」

---

## 遷移注意事項

### 從基於 Scope 到基於 Vendor 的邏輯

自 2026-02-09 起，系統已從使用雙欄位方法（scope + vendor_id）簡化為單一 vendor_id 欄位：

**舊邏輯：**
- 需要檢查 `scope` 欄位和 `vendor_id`
- 查詢中的複雜 WHERE 子句
- Scope 值：'global'、'vendor'、'customized'

**新邏輯：**
- 僅檢查 `vendor_id`
- `vendor_id = NULL`：全域知識
- `vendor_id = <id>`：業者專屬知識

### 對 API 使用的影響

1. **知識創建/更新**：
   - 直接設定 `vendor_id`
   - 忽略 `scope` 欄位（為向後相容而保留）

2. **業者選擇**：
   - 使用 `/api/vendors` 端點取得業者列表
   - 為全域知識設定 `vendor_id` 為 null

3. **篩選**：
   - 查詢自動處理業者可見性
   - 不需要在篩選中指定 scope

---

## 相關文件

- [知識範圍簡化](../features/KNOWLEDGE_SCOPE_SIMPLIFICATION.md)
- [前端使用指南](../guides/development/FRONTEND_USAGE_GUIDE.md)
- [API 參考第一階段](./API_REFERENCE_PHASE1.md)