# Phase 1 API 參考文件

## 基本資訊

**Base URL:** `http://localhost:8100`

**認證：** 目前無需認證（Phase 1）

**Content-Type:** `application/json`

---

## 目錄

- [Chat API](#chat-api)
  - [POST /api/v1/message](#post-apiv1message) - 聊天端點（支援串流與非串流）
- [Cache Management API](#cache-management-api) ⭐ NEW
  - [POST /api/v1/cache/invalidate](#post-apiv1cacheinvalidate) - 失效特定緩存
  - [DELETE /api/v1/cache/clear](#delete-apiv1cacheclear) - 清空所有緩存
  - [GET /api/v1/cache/stats](#get-apiv1cachestats) - 緩存統計資訊
  - [GET /api/v1/cache/health](#get-apiv1cachehealth) - 緩存健康檢查
- [Vendors API](#vendors-api)
- [錯誤代碼](#錯誤代碼)
- [範例集合](#範例集合)

---

## Chat API

### POST /api/v1/message

多業者通用聊天端點（標準回應）

#### 描述

根據業者 ID 和使用者訊息，返回客製化的 AI 回應。系統會自動：
1. 進行意圖分類
2. 根據 user_role 檢索相關知識範圍（B2B/B2C 業務場景）
3. 使用 LLM 智能參數注入，調整業者專屬參數
4. 返回格式化答案

#### 請求

**URL:** `POST /api/v1/message`

**Headers:**
```
Content-Type: application/json
```

**Body Parameters:**

| 參數 | 類型 | 必填 | 說明 | 範例 |
|------|------|------|------|------|
| `message` | string | ✅ | 使用者訊息 | "每月繳費日期是什麼時候？" |
| `vendor_id` | integer | ✅ | 業者 ID | 1 |
| `target_user` | string | ❌ | 目標用戶角色（預設：tenant） 🆕 推薦 | "tenant", "landlord", "property_manager", "system_admin" |
| `mode` | string | ❌ | 業務模式（預設：b2c） 🆕 推薦 | "b2c" (終端用戶), "b2b" (業者員工) |
| `user_role` | string | ❌ | [已廢棄] 使用者角色，請改用 target_user ⚠️ 將於 2026-03 移除 | "customer" or "staff" |
| `stream` | boolean | ❌ | 啟用串流模式（預設：false） 🆕 2026-02-14 | true |
| `session_id` | string | ❌ | 會話 ID（用於追蹤） | "session_123" |
| `user_id` | string | ❌ | 使用者 ID | "user_456" |
| `top_k` | integer | ❌ | 返回知識數量（預設：5） | 5 |
| `include_sources` | boolean | ❌ | 是否包含知識來源（預設：true） | true |
| `include_debug_info` | boolean | ❌ | 是否包含調試資訊（預設：false） | false |
| `disable_answer_synthesis` | boolean | ❌ | 禁用答案合成，僅用於回測（預設：false） | false |
| `skip_sop` | boolean | ❌ | 跳過 SOP 檢索，僅用於回測（預設：false） | false |

**stream 參數說明**（串流回應控制） 🆕 2026-02-14：

| stream值 | 回應格式 | Content-Type | 使用場景 | 用戶體驗 |
|---------|---------|--------------|---------|---------|
| `false` (預設) | **標準 JSON** | application/json | API 整合、批次處理 | 等待完整回應 |
| `true` | **Server-Sent Events** | text/event-stream | 即時聊天、網頁前端 | 逐字顯示（打字機效果） |

**SSE 事件類型**（當 `stream=true` 時）：
- `start` - 開始輸出（含 cached 狀態）
- `intent` - 意圖分類結果
- `answer_chunk` - 答案片段（逐字傳輸）
- `metadata` - 完整元數據（表單、影片、來源等）
- `done` - 串流完成

**target_user 參數說明**（目標用戶角色） 🆕 推薦：

| target_user | 說明 | 典型使用場景 |
|------------|------|-------------|
| `tenant` | 租客（預設值） | 繳費查詢、報修申請、合約問題 |
| `landlord` | 房東 | 收租資訊、物業管理、稅務相關 |
| `property_manager` | 物業管理師 | 系統操作、內部流程、業務規範 |
| `system_admin` | 系統管理員 | 系統配置、權限管理、技術支援 |

**mode 參數說明**（業務模式控制） 🆕 推薦：

| mode | 業務場景 | 知識範圍 | 使用者類型 | 典型問題 |
|------|---------|---------|-----------|---------|
| `b2c` | **B2C 終端用戶**（預設值） | external + both | 租客、房東 | 繳費、報修、合約續約 |
| `b2b` | **B2B 業者員工** | internal + both | 物管師、系統管理員 | 系統操作、內部流程、業務規範 |

**business_scope 說明**（知識庫的 business_scope 欄位）：
- `external`: 僅限 B2C 終端用戶（mode=b2c）可存取
- `internal`: 僅限 B2B 業者員工（mode=b2b）可存取
- `both`: 雙方都可存取的通用知識

**請求範例：**

```json
// B2C 場景 - 租客詢問繳費（推薦寫法）
{
  "message": "每月繳費日期是什麼時候？",
  "vendor_id": 1,
  "target_user": "tenant",
  "mode": "b2c",
  "stream": false,
  "include_sources": true
}

// B2B 場景 - 物管師查詢內部流程（推薦寫法）
{
  "message": "租賃申請的審核流程是什麼？",
  "vendor_id": 1,
  "target_user": "property_manager",
  "mode": "b2b",
  "stream": false,
  "include_sources": true
}

// 串流模式範例 - 租客詢問，逐字顯示答案
{
  "message": "租金每個月幾號要繳？",
  "vendor_id": 1,
  "target_user": "tenant",
  "mode": "b2c",
  "stream": true,
  "session_id": "session_123",
  "user_id": "tenant_456"
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
      "vendor_id": null
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
| `sources[].vendor_id` | integer/null | 業者ID（NULL=全域, 非NULL=業者專屬） |
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
# B2C 場景 - 租客詢問繳費日（標準 JSON 回應）
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "每月繳費日期是什麼時候？",
    "vendor_id": 1,
    "target_user": "tenant",
    "mode": "b2c",
    "stream": false,
    "include_sources": true
  }'

# B2B 場景 - 物管師查詢內部流程（標準 JSON 回應）
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "租賃申請的審核流程是什麼？",
    "vendor_id": 1,
    "target_user": "property_manager",
    "mode": "b2b",
    "stream": false
  }'

# 串流模式 - 逐字返回答案（Server-Sent Events）
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "租金每個月幾號要繳？",
    "vendor_id": 1,
    "target_user": "tenant",
    "mode": "b2c",
    "stream": true
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

## Cache Management API

⭐ NEW - Phase 3 緩存系統管理端點

### 緩存架構概述

系統採用 **Redis 三層緩存架構**，顯著提升效能並降低 API 成本：

| 緩存層 | 鍵格式 | TTL | 用途 | 成本節省 |
|-------|-------|-----|------|---------|
| **Layer 1 - 問題快取** | `question:{vendor_id}:{hash}` | 1 小時 | 完全相同的問題直接返回 | 90% |
| **Layer 2 - 向量快取** | `embedding:{hash}` | 24 小時 | 相同問題不重複呼叫 embedding API | 70% |
| **Layer 3 - 結果快取** | `result:{vendor_id}:{question_hash}:{vector_hash}` | 30 分鐘 | 相同檢索結果快取 | 50% |

---

### POST /api/v1/cache/invalidate

失效特定緩存鍵

#### 描述

手動失效特定的緩存鍵，用於知識庫更新後強制重新生成回應。

#### 請求

**URL:** `POST /api/v1/cache/invalidate`

**Headers:**
```
Content-Type: application/json
```

**Body Parameters:**

| 參數 | 類型 | 必填 | 說明 | 範例 |
|------|------|------|------|------|
| `cache_type` | string | ✅ | 緩存類型 | "question", "embedding", "result", "all" |
| `vendor_id` | integer | ❌ | 業者 ID（僅 question/result 需要） | 1 |
| `pattern` | string | ❌ | 鍵模式（支援萬用字元 *） | "question:1:*" |

**請求範例：**

```json
// 失效業者 1 的所有問題快取
{
  "cache_type": "question",
  "vendor_id": 1
}

// 失效所有 embedding 快取
{
  "cache_type": "embedding"
}

// 使用模式匹配失效
{
  "cache_type": "result",
  "pattern": "result:1:*"
}
```

#### 回應

**成功回應 (200 OK):**

```json
{
  "success": true,
  "message": "緩存已失效",
  "invalidated_keys": 45,
  "cache_type": "question",
  "vendor_id": 1,
  "timestamp": "2025-10-22T12:00:00"
}
```

#### cURL 範例

```bash
# 失效業者 1 的問題快取
curl -X POST http://localhost:8100/api/v1/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{
    "cache_type": "question",
    "vendor_id": 1
  }'
```

---

### DELETE /api/v1/cache/clear

清空所有緩存

#### 描述

清空所有緩存層的資料。**謹慎使用**：此操作會導致短期內 API 成本上升。

#### 請求

**URL:** `DELETE /api/v1/cache/clear`

**Query Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `confirm` | boolean | ✅ | 確認參數（必須為 true） |

#### 回應

**成功回應 (200 OK):**

```json
{
  "success": true,
  "message": "所有緩存已清空",
  "cleared_keys": 1234,
  "layers_cleared": ["question", "embedding", "result"],
  "timestamp": "2025-10-22T12:00:00",
  "warning": "緩存重建期間 API 成本會暫時上升"
}
```

#### cURL 範例

```bash
curl -X DELETE "http://localhost:8100/api/v1/cache/clear?confirm=true"
```

---

### GET /api/v1/cache/stats

獲取緩存統計資訊

#### 描述

獲取三層緩存的命中率、鍵數量、記憶體使用等統計資訊。

#### 請求

**URL:** `GET /api/v1/cache/stats`

**Query Parameters:**

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `vendor_id` | integer | ❌ | 過濾特定業者（可選） |

#### 回應

**成功回應 (200 OK):**

```json
{
  "overall": {
    "total_keys": 1234,
    "memory_used_mb": 45.6,
    "hit_rate": 0.78,
    "total_hits": 5678,
    "total_misses": 1234
  },
  "layers": {
    "question": {
      "keys": 456,
      "hit_rate": 0.85,
      "hits": 2000,
      "misses": 350,
      "avg_ttl_seconds": 3600,
      "cost_savings_percentage": 90
    },
    "embedding": {
      "keys": 678,
      "hit_rate": 0.72,
      "hits": 3000,
      "misses": 800,
      "avg_ttl_seconds": 86400,
      "cost_savings_percentage": 70
    },
    "result": {
      "keys": 100,
      "hit_rate": 0.65,
      "hits": 678,
      "misses": 234,
      "avg_ttl_seconds": 1800,
      "cost_savings_percentage": 50
    }
  },
  "by_vendor": {
    "1": {
      "vendor_name": "甲山林",
      "question_cache_keys": 150,
      "result_cache_keys": 45
    }
  },
  "timestamp": "2025-10-22T12:00:00"
}
```

#### cURL 範例

```bash
# 獲取所有緩存統計
curl http://localhost:8100/api/v1/cache/stats

# 獲取業者 1 的緩存統計
curl "http://localhost:8100/api/v1/cache/stats?vendor_id=1"
```

---

### GET /api/v1/cache/health

檢查緩存健康狀態

#### 描述

檢查 Redis 連線狀態和緩存系統健康度。

#### 請求

**URL:** `GET /api/v1/cache/health`

#### 回應

**成功回應 (200 OK):**

```json
{
  "status": "healthy",
  "redis_connected": true,
  "redis_version": "7.0.11",
  "uptime_seconds": 123456,
  "connected_clients": 5,
  "used_memory_mb": 45.6,
  "max_memory_mb": 512.0,
  "memory_usage_percentage": 8.9,
  "cache_layers_active": ["question", "embedding", "result"],
  "last_check": "2025-10-22T12:00:00"
}
```

**錯誤回應 (503 Service Unavailable):**

```json
{
  "status": "unhealthy",
  "redis_connected": false,
  "error": "無法連接到 Redis 伺服器",
  "detail": "Connection refused"
}
```

#### cURL 範例

```bash
curl http://localhost:8100/api/v1/cache/health
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

### HTTP 狀態碼總覽

| 狀態碼 | 說明 | 常見原因 | 解決方案 |
|--------|------|----------|---------|
| 400 | Bad Request | 請求參數錯誤、必填欄位缺失、資料格式錯誤 | 檢查請求參數格式和必填欄位 |
| 403 | Forbidden | 業者未啟用、權限不足 | 確認業者狀態或檢查權限設定 |
| 404 | Not Found | 業者不存在、資源不存在 | 確認 ID 是否正確 |
| 422 | Unprocessable Entity | 資料驗證失敗 | 檢查資料格式和業務邏輯 |
| 429 | Too Many Requests | 請求頻率過高 | 減少請求頻率或使用緩存 |
| 500 | Internal Server Error | 伺服器錯誤、資料庫錯誤 | 檢查日誌，聯絡技術支援 |
| 503 | Service Unavailable | 服務暫時無法使用（如 Redis 斷線） | 檢查緩存健康狀態 |

### 詳細錯誤代碼

#### Chat API 錯誤

| 錯誤碼 | HTTP 狀態 | 錯誤訊息 | 原因 |
|-------|----------|---------|------|
| VENDOR_NOT_FOUND | 404 | "業者不存在: {vendor_id}" | 指定的業者 ID 不存在 |
| VENDOR_INACTIVE | 403 | "業者未啟用: {vendor_id}" | 業者已停用 |
| INVALID_USER_ROLE | 400 | "無效的 user_role: {role}" | user_role 必須為 customer 或 staff |
| INTENT_CLASSIFICATION_FAILED | 500 | "意圖分類失敗" | LLM 呼叫失敗或回應格式錯誤 |
| KNOWLEDGE_RETRIEVAL_FAILED | 500 | "知識檢索失敗" | 向量搜尋錯誤 |
| LLM_GENERATION_FAILED | 500 | "答案生成失敗" | LLM API 錯誤 |

#### Cache API 錯誤

| 錯誤碼 | HTTP 狀態 | 錯誤訊息 | 原因 |
|-------|----------|---------|------|
| REDIS_CONNECTION_FAILED | 503 | "無法連接到 Redis 伺服器" | Redis 服務未啟動或網路問題 |
| INVALID_CACHE_TYPE | 400 | "無效的緩存類型: {type}" | cache_type 必須為 question/embedding/result/all |
| CACHE_CLEAR_DENIED | 403 | "必須提供 confirm=true 參數" | 清空緩存需要明確確認 |

#### Vendors API 錯誤

| 錯誤碼 | HTTP 狀態 | 錯誤訊息 | 原因 |
|-------|----------|---------|------|
| VENDOR_CODE_EXISTS | 400 | "業者代碼已存在: {code}" | 業者代碼重複 |
| VENDOR_CODE_IMMUTABLE | 400 | "業者代碼不可修改" | 嘗試修改 code 欄位 |
| CONFIG_VALIDATION_FAILED | 422 | "配置驗證失敗: {detail}" | 配置參數格式錯誤 |

### 通用錯誤回應格式

**標準格式：**

```json
{
  "detail": "錯誤訊息說明",
  "error_code": "VENDOR_NOT_FOUND",
  "timestamp": "2025-10-22T12:00:00"
}
```

**驗證錯誤（422）：**

```json
{
  "detail": [
    {
      "loc": ["body", "vendor_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
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

echo "=== 測試 1: B2C 場景 - 租客詢問繳費日（標準 JSON） ==="
curl -X POST "$BASE_URL/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "每月繳費日期是什麼時候？",
    "vendor_id": 1,
    "target_user": "tenant",
    "mode": "b2c",
    "stream": false
  }' | jq '.answer'

echo -e "\n=== 測試 2: B2B 場景 - 物管師查詢內部流程（標準 JSON） ==="
curl -X POST "$BASE_URL/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "租賃申請的審核流程是什麼？",
    "vendor_id": 1,
    "target_user": "property_manager",
    "mode": "b2b",
    "stream": false
  }' | jq '.answer'

echo -e "\n=== 測試 3: 串流模式聊天（前 20 個事件） ==="
curl -X POST "$BASE_URL/api/v1/message" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "租金每個月幾號要繳？",
    "vendor_id": 1,
    "target_user": "tenant",
    "mode": "b2c",
    "stream": true
  }' | head -20

echo -e "\n=== 測試 4: 緩存健康檢查 ==="
curl "$BASE_URL/api/v1/cache/health" | jq '.status, .redis_connected'

echo -e "\n=== 測試 5: 緩存統計資訊 ==="
curl "$BASE_URL/api/v1/cache/stats" | jq '.overall.hit_rate, .layers'

echo -e "\n=== 測試 6: 獲取業者列表 ==="
curl "$BASE_URL/api/v1/vendors" | jq '.[].name'

echo -e "\n=== 測試 7: 測試業者配置 ==="
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
- **文件版本：** 3.1
- **最後更新：** 2026-02-14
- **適用系統版本：** Phase 1 完成 + Phase 3 性能優化（緩存系統 + 串流回應 + B2B/B2C 業務場景）

### 變更紀錄

#### v3.1 (2026-02-14) - 文檔修正與參數更新
**重大修正：**
- ❌ **移除不存在的端點**: 刪除 `/api/v1/chat/stream` 文檔（該端點不存在）
- ✅ **串流模式正確說明**: 通過 `/api/v1/message` 端點的 `stream` 參數控制
- 🆕 **參數遷移指引**: `user_role` → `target_user` + `mode`（user_role 將於 2026-03 移除）
- 📝 **補充缺失參數**: 新增 `include_debug_info`, `disable_answer_synthesis`, `skip_sop` 文檔
- ✅ **修正預設值**: `top_k` 預設值從 3 → 5，`mode` 預設值從 "tenant" → "b2c"

**新增參數說明：**
- `target_user`: 目標用戶角色（tenant/landlord/property_manager/system_admin）
- `mode`: 業務模式（b2c/b2b）
- `stream`: 啟用串流模式（true/false）

**文檔改進：**
- 更新所有範例使用推薦參數（target_user + mode）
- 更新測試腳本使用正確端點和參數
- 標記已廢棄參數（user_role）並提供遷移建議

#### v3.0 (2025-10-22) - Phase 3 完整更新
**重大變更：**
- ✅ **端點路徑修正**: `/chat/v1/message` → `/api/v1/message`
- ⭐ **新增緩存管理 API**: 4 個端點（invalidate/clear/stats/health）
- 📊 **新增三層緩存架構說明**: 問題快取、向量快取、結果快取
- 📝 **擴充錯誤代碼表**: 新增詳細錯誤碼和解決方案

**文檔改進：**
- 新增 B2B/B2C 業務場景說明和範例
- 新增 business_scope 欄位說明（external/internal/both）
- 更新所有測試腳本使用正確端點

#### v2.1 (2025-10-13)
- 新增多意圖分類欄位（all_intents, secondary_intents, intent_ids）
- 更新回應格式包含次要意圖

#### v2.0 (2025-10-10)
- 更新為 LLM 智能參數注入系統
- 移除舊版模板變數系統
- 新增 vendor_configs 整合

#### v1.0 (2025-01-XX)
- 初始版本（模板變數系統）

## 相關文檔

- [知識匯入 API 參考](KNOWLEDGE_IMPORT_API.md) - 批量匯入知識 API
- [系統架構文檔](../architecture/SYSTEM_ARCHITECTURE.md)
- [多意圖分類文檔](../features/MULTI_INTENT_CLASSIFICATION.md)
- [開發工作流程](../guides/DEVELOPMENT_WORKFLOW.md)
