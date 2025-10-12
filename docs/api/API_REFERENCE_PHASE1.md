# Phase 1 API 參考文件

## 基本資訊

**Base URL:** `http://localhost:8100`

**認證：** 目前無需認證（Phase 1）

**Content-Type:** `application/json`

---

## 目錄

- [Chat API](#chat-api)
- [Vendors API](#vendors-api)
- [錯誤代碼](#錯誤代碼)
- [範例集合](#範例集合)

---

## Chat API

### POST /chat/v1/message

多業者通用聊天端點

#### 描述

根據業者 ID 和使用者訊息，返回客製化的 AI 回應。系統會自動：
1. 進行意圖分類
2. 檢索相關知識
3. 使用 LLM 智能參數注入，調整業者專屬參數
4. 返回格式化答案

#### 請求

**URL:** `POST /chat/v1/message`

**Headers:**
```
Content-Type: application/json
```

**Body Parameters:**

| 參數 | 類型 | 必填 | 說明 | 範例 |
|------|------|------|------|------|
| `message` | string | ✅ | 使用者訊息 | "每月繳費日期是什麼時候？" |
| `vendor_id` | integer | ✅ | 業者 ID | 1 |
| `mode` | string | ❌ | 模式（預設：tenant） | "tenant" or "customer_service" |
| `session_id` | string | ❌ | 會話 ID（用於追蹤） | "session_123" |
| `user_id` | string | ❌ | 使用者 ID | "user_456" |
| `top_k` | integer | ❌ | 返回知識數量（預設：3） | 5 |
| `include_sources` | boolean | ❌ | 是否包含知識來源（預設：true） | true |

**請求範例：**

```json
{
  "message": "每月繳費日期是什麼時候？",
  "vendor_id": 1,
  "mode": "tenant",
  "include_sources": true
}
```

#### 回應

**成功回應 (200 OK):**

```json
{
  "answer": "您的租金繳費日為每月 1 號，請務必在期限前完成繳費。如果超過繳費日 5 天仍未繳納，將加收 200 元的逾期手續費。",
  "intent_name": "帳務查詢",
  "intent_type": "knowledge",
  "confidence": 0.95,
  "all_intents": ["帳務查詢"],
  "secondary_intents": [],
  "intent_ids": [5],
  "sources": [
    {
      "id": 123,
      "question_summary": "每月繳費日期",
      "answer": "您的租金繳費日為每月 5 號...",
      "scope": "global"
    }
  ],
  "source_count": 1,
  "vendor_id": 1,
  "mode": "tenant",
  "session_id": null,
  "timestamp": "2024-01-01T12:00:00.000000",
  "llm_optimization": {
    "optimization_applied": true,
    "tokens_used": 456,
    "processing_time_ms": 1234,
    "vendor_params_injected": true
  }
}
```

**回應欄位說明：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `answer` | string | AI 回答（已替換模板變數） |
| `intent_name` | string | 主要意圖名稱 |
| `intent_type` | string | 意圖類型（knowledge, data_query, action, hybrid） |
| `confidence` | float | 意圖分類信心度 (0-1) |
| `all_intents` | array[string] | 所有匹配的意圖名稱（包含主要 + 次要） ⭐ NEW |
| `secondary_intents` | array[string] | 次要意圖名稱列表 ⭐ NEW |
| `intent_ids` | array[integer] | 所有意圖的 ID 列表 ⭐ NEW |
| `sources` | array | 知識來源列表 |
| `sources[].id` | integer | 知識 ID |
| `sources[].question_summary` | string | 問題摘要 |
| `sources[].answer` | string | 答案（原始知識庫內容） |
| `sources[].scope` | string | 知識範圍（global, vendor, customized） |
| `source_count` | integer | 知識來源數量 |
| `vendor_id` | integer | 業者 ID |
| `mode` | string | 模式 |
| `session_id` | string | 會話 ID（如有提供） |
| `timestamp` | string | 回應時間戳（ISO 8601） |
| `llm_optimization` | object | LLM 優化資訊 |
| `llm_optimization.optimization_applied` | boolean | 是否使用了 LLM 優化 |
| `llm_optimization.tokens_used` | integer | 使用的 tokens 數 |
| `llm_optimization.processing_time_ms` | integer | 處理時間（毫秒） |
| `llm_optimization.vendor_params_injected` | boolean | 是否進行了業者參數注入 |

**錯誤回應：**

```json
// 404 - 業者不存在
{
  "detail": "業者不存在: 999"
}

// 403 - 業者未啟用
{
  "detail": "業者未啟用: 1"
}

// 500 - 伺服器錯誤
{
  "detail": "處理聊天請求失敗: [錯誤訊息]"
}
```

#### cURL 範例

```bash
# 業者 A 詢問繳費日
curl -X POST http://localhost:8100/chat/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "每月繳費日期是什麼時候？",
    "vendor_id": 1,
    "mode": "tenant",
    "include_sources": true
  }'

# 業者 B 詢問客服專線
curl -X POST http://localhost:8100/chat/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "客服專線是多少？",
    "vendor_id": 2,
    "mode": "tenant"
  }'
```

---

### GET /chat/v1/vendors/{vendor_id}/test

測試業者配置

#### 描述

測試業者的參數配置是否正確，並預覽參數注入效果。

#### 請求

**URL:** `GET /chat/v1/vendors/{vendor_id}/test`

**Path Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ✅ | 業者 ID |

#### 回應

**成功回應 (200 OK):**

```json
{
  "vendor": {
    "id": 1,
    "code": "VENDOR_A",
    "name": "甲山林包租代管股份有限公司",
    "short_name": "甲山林",
    "contact_phone": "02-2345-6789",
    "contact_email": "service@vendorA.com",
    "is_active": true,
    "subscription_plan": "premium"
  },
  "param_count": 12,
  "parameters": {
    "payment_day": {
      "value": "1",
      "data_type": "number",
      "unit": "號",
      "display_name": "繳費日期",
      "description": "每月繳費日期"
    },
    "late_fee": {
      "value": "200",
      "data_type": "number",
      "unit": "元",
      "display_name": "逾期手續費",
      "description": "逾期繳費手續費"
    }
  },
  "test_template": {
    "original": "繳費日為 {{payment_day}}，逾期費 {{late_fee}}。",
    "resolved": "繳費日為 1 號，逾期費 200 元。"
  }
}
```

#### cURL 範例

```bash
curl http://localhost:8100/chat/v1/vendors/1/test
```

---

### POST /chat/v1/reload

重新載入多業者服務

#### 描述

清除參數快取，用於業者配置更新後重新載入。

#### 請求

**URL:** `POST /chat/v1/reload`

#### 回應

**成功回應 (200 OK):**

```json
{
  "success": true,
  "message": "多業者服務已重新載入",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

#### cURL 範例

```bash
curl -X POST http://localhost:8100/chat/v1/reload
```

---

## Vendors API

### GET /api/v1/vendors

獲取業者列表

#### 描述

獲取所有業者或根據條件過濾的業者列表。

#### 請求

**URL:** `GET /api/v1/vendors`

**Query Parameters:**

| 參數 | 類型 | 必填 | 說明 | 範例 |
|------|------|------|------|------|
| `is_active` | boolean | ❌ | 過濾啟用/停用狀態 | true |
| `subscription_plan` | string | ❌ | 過濾訂閱方案 | "premium" |

#### 回應

**成功回應 (200 OK):**

```json
[
  {
    "id": 1,
    "code": "VENDOR_A",
    "name": "甲山林包租代管股份有限公司",
    "short_name": "甲山林",
    "contact_phone": "02-2345-6789",
    "contact_email": "service@vendorA.com",
    "address": "台北市信義區信義路五段100號",
    "subscription_plan": "premium",
    "subscription_status": "active",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  },
  {
    "id": 2,
    "code": "VENDOR_B",
    "name": "信義包租代管股份有限公司",
    ...
  }
]
```

#### cURL 範例

```bash
# 獲取所有業者
curl http://localhost:8100/api/v1/vendors

# 只獲取已啟用的業者
curl "http://localhost:8100/api/v1/vendors?is_active=true"

# 獲取 premium 方案的業者
curl "http://localhost:8100/api/v1/vendors?subscription_plan=premium"
```

---

### POST /api/v1/vendors

建立新業者

#### 描述

建立新的包租代管業者。

#### 請求

**URL:** `POST /api/v1/vendors`

**Headers:**
```
Content-Type: application/json
```

**Body Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `code` | string | ✅ | 業者代碼（唯一，建立後不可修改） |
| `name` | string | ✅ | 業者名稱 |
| `short_name` | string | ❌ | 簡稱 |
| `contact_phone` | string | ❌ | 聯絡電話 |
| `contact_email` | string | ❌ | 聯絡郵箱 |
| `address` | string | ❌ | 公司地址 |
| `subscription_plan` | string | ❌ | 訂閱方案（預設：basic） |
| `created_by` | string | ❌ | 建立者（預設：admin） |

**請求範例：**

```json
{
  "code": "VENDOR_C",
  "name": "永慶包租代管股份有限公司",
  "short_name": "永慶",
  "contact_phone": "02-1234-5678",
  "contact_email": "service@vendorc.com",
  "address": "台北市松山區南京東路三段200號",
  "subscription_plan": "standard",
  "created_by": "admin"
}
```

#### 回應

**成功回應 (201 Created):**

```json
{
  "id": 3,
  "code": "VENDOR_C",
  "name": "永慶包租代管股份有限公司",
  "short_name": "永慶",
  "contact_phone": "02-1234-5678",
  "contact_email": "service@vendorc.com",
  "address": "台北市松山區南京東路三段200號",
  "subscription_plan": "standard",
  "subscription_status": "active",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:00:00"
}
```

**錯誤回應：**

```json
// 400 - 業者代碼已存在
{
  "detail": "業者代碼已存在: VENDOR_C"
}
```

#### cURL 範例

```bash
curl -X POST http://localhost:8100/api/v1/vendors \
  -H "Content-Type: application/json" \
  -d '{
    "code": "VENDOR_C",
    "name": "永慶包租代管股份有限公司",
    "short_name": "永慶",
    "contact_phone": "02-1234-5678",
    "subscription_plan": "standard"
  }'
```

---

### GET /api/v1/vendors/{vendor_id}

獲取業者詳情

#### 請求

**URL:** `GET /api/v1/vendors/{vendor_id}`

**Path Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ✅ | 業者 ID |

#### 回應

**成功回應 (200 OK):**

```json
{
  "id": 1,
  "code": "VENDOR_A",
  "name": "甲山林包租代管股份有限公司",
  "short_name": "甲山林",
  "contact_phone": "02-2345-6789",
  "contact_email": "service@vendorA.com",
  "address": "台北市信義區信義路五段100號",
  "subscription_plan": "premium",
  "subscription_status": "active",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**錯誤回應：**

```json
// 404 - 業者不存在
{
  "detail": "業者不存在"
}
```

#### cURL 範例

```bash
curl http://localhost:8100/api/v1/vendors/1
```

---

### PUT /api/v1/vendors/{vendor_id}

更新業者資訊

#### 請求

**URL:** `PUT /api/v1/vendors/{vendor_id}`

**Path Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ✅ | 業者 ID |

**Body Parameters:** （所有欄位皆為選填，只更新提供的欄位）

| 參數 | 類型 | 說明 |
|------|------|------|
| `name` | string | 業者名稱 |
| `short_name` | string | 簡稱 |
| `contact_phone` | string | 聯絡電話 |
| `contact_email` | string | 聯絡郵箱 |
| `address` | string | 公司地址 |
| `subscription_plan` | string | 訂閱方案 |
| `is_active` | boolean | 是否啟用 |
| `updated_by` | string | 更新者（預設：admin） |

**請求範例：**

```json
{
  "contact_phone": "02-9999-8888",
  "subscription_plan": "premium",
  "updated_by": "admin"
}
```

#### 回應

**成功回應 (200 OK):**

```json
{
  "id": 1,
  "code": "VENDOR_A",
  "name": "甲山林包租代管股份有限公司",
  "contact_phone": "02-9999-8888",
  "subscription_plan": "premium",
  ...
}
```

#### cURL 範例

```bash
curl -X PUT http://localhost:8100/api/v1/vendors/1 \
  -H "Content-Type: application/json" \
  -d '{
    "contact_phone": "02-9999-8888",
    "subscription_plan": "premium"
  }'
```

---

### DELETE /api/v1/vendors/{vendor_id}

停用業者

#### 描述

軟刪除業者（設定 `is_active = false`），不會實際刪除資料。

#### 請求

**URL:** `DELETE /api/v1/vendors/{vendor_id}`

**Path Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ✅ | 業者 ID |

#### 回應

**成功回應 (200 OK):**

```json
{
  "message": "業者已停用",
  "vendor_id": 1
}
```

#### cURL 範例

```bash
curl -X DELETE http://localhost:8100/api/v1/vendors/1
```

---

### GET /api/v1/vendors/{vendor_id}/configs

獲取業者配置參數

#### 描述

獲取業者的所有配置參數，按分類組織。

#### 請求

**URL:** `GET /api/v1/vendors/{vendor_id}/configs`

**Path Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ✅ | 業者 ID |

**Query Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `category` | string | ❌ | 過濾分類（payment, contract, service, contact） |

#### 回應

**成功回應 (200 OK):**

```json
{
  "payment": [
    {
      "id": 1,
      "category": "payment",
      "param_key": "payment_day",
      "param_value": "1",
      "data_type": "number",
      "display_name": "繳費日期",
      "description": "每月繳費日期",
      "unit": "號",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": null
    },
    {
      "id": 2,
      "category": "payment",
      "param_key": "late_fee",
      "param_value": "200",
      "data_type": "number",
      "display_name": "逾期手續費",
      "description": "逾期繳費手續費",
      "unit": "元",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": null
    }
  ],
  "service": [...]
}
```

#### cURL 範例

```bash
# 獲取所有配置
curl http://localhost:8100/api/v1/vendors/1/configs

# 只獲取帳務相關配置
curl "http://localhost:8100/api/v1/vendors/1/configs?category=payment"
```

---

### PUT /api/v1/vendors/{vendor_id}/configs

批次更新業者配置

#### 描述

批次更新或新增業者的配置參數。使用 UPSERT 策略（存在則更新，不存在則新增）。

#### 請求

**URL:** `PUT /api/v1/vendors/{vendor_id}/configs`

**Path Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ✅ | 業者 ID |

**Body Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `configs` | array | ✅ | 配置列表 |
| `configs[].category` | string | ✅ | 分類 |
| `configs[].param_key` | string | ✅ | 參數鍵 |
| `configs[].param_value` | string | ✅ | 參數值 |
| `configs[].data_type` | string | ❌ | 資料型別（預設：string） |
| `configs[].display_name` | string | ❌ | 顯示名稱 |
| `configs[].description` | string | ❌ | 參數說明 |
| `configs[].unit` | string | ❌ | 單位 |

**請求範例：**

```json
{
  "configs": [
    {
      "category": "payment",
      "param_key": "payment_day",
      "param_value": "1",
      "data_type": "number",
      "display_name": "繳費日期",
      "description": "每月繳費日期",
      "unit": "號"
    },
    {
      "category": "payment",
      "param_key": "late_fee",
      "param_value": "200",
      "data_type": "number",
      "display_name": "逾期手續費",
      "description": "逾期繳費手續費",
      "unit": "元"
    },
    {
      "category": "service",
      "param_key": "service_hotline",
      "param_value": "02-2345-6789",
      "data_type": "string",
      "display_name": "客服專線",
      "description": "24小時客服專線",
      "unit": null
    }
  ]
}
```

#### 回應

**成功回應 (200 OK):**

```json
{
  "message": "配置已更新",
  "vendor_id": 1,
  "updated_count": 3
}
```

#### cURL 範例

```bash
curl -X PUT http://localhost:8100/api/v1/vendors/1/configs \
  -H "Content-Type: application/json" \
  -d '{
    "configs": [
      {
        "category": "payment",
        "param_key": "payment_day",
        "param_value": "1",
        "data_type": "number",
        "display_name": "繳費日期",
        "unit": "號"
      }
    ]
  }'
```

---

### GET /api/v1/vendors/{vendor_id}/stats

獲取業者統計資訊

#### 描述

獲取業者的配置參數數量、知識數量等統計資訊。

#### 請求

**URL:** `GET /api/v1/vendors/{vendor_id}/stats`

**Path Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ✅ | 業者 ID |

#### 回應

**成功回應 (200 OK):**

```json
{
  "vendor": {
    "id": 1,
    "code": "VENDOR_A",
    "name": "甲山林包租代管股份有限公司",
    "is_active": true,
    ...
  },
  "config_counts": {
    "payment": 4,
    "contract": 3,
    "service": 3,
    "contact": 2
  },
  "total_configs": 12,
  "knowledge": {
    "total_knowledge": 1,
    "vendor_knowledge": 0,
    "customized_knowledge": 1
  }
}
```

#### cURL 範例

```bash
curl http://localhost:8100/api/v1/vendors/1/stats
```

---

## 錯誤代碼

| 狀態碼 | 說明 | 可能原因 |
|--------|------|----------|
| 400 | Bad Request | 請求參數錯誤、必填欄位缺失、資料格式錯誤 |
| 403 | Forbidden | 業者未啟用 |
| 404 | Not Found | 業者不存在、資源不存在 |
| 500 | Internal Server Error | 伺服器錯誤、資料庫錯誤、服務異常 |

**通用錯誤回應格式：**

```json
{
  "detail": "錯誤訊息說明"
}
```

---

## 範例集合

### Postman Collection

建議建立 Postman Collection 並匯入以下範例：

#### Collection: Phase 1 - Multi-Vendor Chat

**資料夾 1: Chat API**
- POST Chat Message (Vendor A)
- POST Chat Message (Vendor B)
- GET Test Vendor Config
- POST Reload Services

**資料夾 2: Vendors Management**
- GET List Vendors
- POST Create Vendor
- GET Vendor Details
- PUT Update Vendor
- DELETE Deactivate Vendor

**資料夾 3: Vendor Configs**
- GET Vendor Configs (All)
- GET Vendor Configs (Payment Only)
- PUT Update Vendor Configs
- GET Vendor Stats

### 測試腳本

```bash
#!/bin/bash
# test-api.sh - API 測試腳本

BASE_URL="http://localhost:8100"

echo "=== 測試 1: 業者 A 詢問繳費日 ==="
curl -X POST "$BASE_URL/chat/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "每月繳費日期是什麼時候？",
    "vendor_id": 1
  }' | jq '.answer'

echo -e "\n=== 測試 2: 業者 B 詢問繳費日 ==="
curl -X POST "$BASE_URL/chat/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "每月繳費日期是什麼時候？",
    "vendor_id": 2
  }' | jq '.answer'

echo -e "\n=== 測試 3: 獲取業者列表 ==="
curl "$BASE_URL/api/v1/vendors" | jq '.[].name'

echo -e "\n=== 測試 4: 測試業者配置 ==="
curl "$BASE_URL/chat/v1/vendors/1/test" | jq '.test_template'
```

使用方法：
```bash
chmod +x test-api.sh
./test-api.sh
```

---

## 版本資訊

- **API 版本：** v1
- **文件版本：** 2.1
- **最後更新：** 2025-10-13
- **適用系統版本：** Phase 1（LLM 智能參數注入 + 多意圖分類）
- **變更紀錄：**
  - v2.1 (2025-10-13): 新增多意圖分類欄位（all_intents, secondary_intents, intent_ids）
  - v2.0 (2025-10-10): 更新為 LLM 智能參數注入系統
  - v1.0 (2025-01-XX): 初始版本（模板變數系統）

## 相關文檔

- [知識匯入 API 參考](KNOWLEDGE_IMPORT_API.md) - 批量匯入知識 API
- [系統架構文檔](../architecture/SYSTEM_ARCHITECTURE.md)
- [多意圖分類文檔](../features/MULTI_INTENT_CLASSIFICATION.md)
- [開發工作流程](../guides/DEVELOPMENT_WORKFLOW.md)
