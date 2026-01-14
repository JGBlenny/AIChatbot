# Knowledge Admin API 參考文件

**Base URL:** `http://localhost:8000`
**版本:** v1.0
**最後更新:** 2026-01-14

---

## 📋 目錄

- [認證說明](#認證說明)
- [知識管理 API](#知識管理-api)
- [意圖管理 API](#意圖管理-api)
- [測試情境 API](#測試情境-api)
- [回測 API](#回測-api)
- [認證 API](#認證-api)
- [管理員管理 API](#管理員管理-api)
- [角色管理 API](#角色管理-api)
- [配置管理 API](#配置管理-api)
- [錯誤代碼](#錯誤代碼)

---

## 認證說明

### 認證方式

Knowledge Admin API 使用 **JWT Token** 認證。

**流程**:
1. 呼叫 `/api/auth/login` 取得 Token
2. 在後續請求的 Header 中帶入 Token:
   ```
   Authorization: Bearer <your-token>
   ```

**Token 有效期**: 24 小時

---

## 知識管理 API

### GET /api/knowledge

列出所有知識（支援搜尋、分頁、過濾）

**權限**: `knowledge:view`

**Query Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `search` | string | ❌ | 搜尋關鍵字（問題或答案） |
| `business_scope` | string | ❌ | 業務範圍過濾 (external/internal/both) |
| `vendor_id` | integer | ❌ | 業者 ID 過濾 |
| `page` | integer | ❌ | 頁碼（預設: 1） |
| `page_size` | integer | ❌ | 每頁筆數（預設: 20） |
| `sort_by` | string | ❌ | 排序欄位 (created_at/priority) |
| `order` | string | ❌ | 排序方向 (asc/desc) |

**範例**:

```bash
# 列出所有知識
curl http://localhost:8000/api/knowledge

# 搜尋關鍵字「租金」
curl "http://localhost:8000/api/knowledge?search=租金"

# 過濾 B2C 外部知識
curl "http://localhost:8000/api/knowledge?business_scope=external"

# 分頁查詢
curl "http://localhost:8000/api/knowledge?page=2&page_size=10"
```

**回應 (200 OK)**:

```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 123,
      "question_summary": "每月租金繳費日",
      "answer": "租金繳費日為每月 1 號...",
      "keywords": ["租金", "繳費"],
      "business_types": ["rent"],
      "target_user": ["租客"],
      "priority": 5,
      "business_scope": "external",
      "vendor_id": null,
      "created_at": "2026-01-10T10:00:00",
      "updated_at": "2026-01-10T10:00:00"
    }
  ]
}
```

---

### GET /api/knowledge/{knowledge_id}

取得單一知識詳情

**權限**: `knowledge:view`

**Path Parameters**:
- `knowledge_id` (integer): 知識 ID

**範例**:

```bash
curl http://localhost:8000/api/knowledge/123
```

**回應 (200 OK)**:

```json
{
  "id": 123,
  "question_summary": "每月租金繳費日",
  "answer": "# 租金繳費日\n\n租金繳費日為每月 1 號...",
  "keywords": ["租金", "繳費"],
  "business_types": ["rent"],
  "target_user": ["租客"],
  "priority": 5,
  "business_scope": "external",
  "vendor_id": null,
  "form_id": null,
  "video_url": null,
  "category": "帳務",
  "intents": [
    {
      "id": 5,
      "name": "帳務查詢",
      "is_primary": true
    }
  ],
  "created_at": "2026-01-10T10:00:00",
  "updated_at": "2026-01-10T10:00:00"
}
```

---

### POST /api/knowledge

新增知識

**權限**: `knowledge:create`

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `question_summary` | string | ✅ | 問題摘要 |
| `answer` | string | ✅ | 答案內容（支援 Markdown） |
| `keywords` | array[string] | ❌ | 關鍵字 |
| `business_types` | array[string] | ❌ | 業態類型 |
| `target_user` | array[string] | ❌ | 目標用戶 |
| `priority` | integer | ❌ | 優先級 (0-10，預設 0) |
| `business_scope` | string | ❌ | 業務範圍 (預設 both) |
| `vendor_id` | integer | ❌ | 業者 ID |
| `form_id` | string | ❌ | 關聯表單 ID |
| `video_url` | string | ❌ | 影片連結 |
| `category` | string | ❌ | 分類 |
| `intent_ids` | array[integer] | ❌ | 意圖 ID 列表 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/knowledge \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "question_summary": "退租流程",
    "answer": "# 退租流程\n\n1. 提前 30 天通知\n2. 清潔房屋\n3. 辦理交屋",
    "keywords": ["退租", "流程"],
    "business_types": ["rent"],
    "target_user": ["租客"],
    "priority": 7,
    "business_scope": "external",
    "intent_ids": [3, 8]
  }'
```

**回應 (201 Created)**:

```json
{
  "id": 456,
  "question_summary": "退租流程",
  "message": "知識已建立並生成向量",
  "embedding_generated": true,
  "created_at": "2026-01-14T10:00:00"
}
```

---

### PUT /api/knowledge/{knowledge_id}

更新知識

**權限**: `knowledge:update`

**Path Parameters**:
- `knowledge_id` (integer): 知識 ID

**Body Parameters**: 同新增知識，所有欄位皆選填

**範例**:

```bash
curl -X PUT http://localhost:8000/api/knowledge/456 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "priority": 10,
    "answer": "# 退租流程（更新版）\n\n..."
  }'
```

**回應 (200 OK)**:

```json
{
  "id": 456,
  "message": "知識已更新並重新生成向量",
  "embedding_regenerated": true,
  "updated_at": "2026-01-14T10:30:00"
}
```

---

### DELETE /api/knowledge/{knowledge_id}

刪除知識

**權限**: `knowledge:delete`

**Path Parameters**:
- `knowledge_id` (integer): 知識 ID

**範例**:

```bash
curl -X DELETE http://localhost:8000/api/knowledge/456 \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "message": "知識已刪除",
  "id": 456
}
```

---

### POST /api/knowledge/regenerate-embeddings

批量重新生成 embedding

**權限**: `knowledge:update`

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `knowledge_ids` | array[integer] | ❌ | 知識 ID 列表（留空則全部重新生成） |

**範例**:

```bash
# 重新生成所有 embedding
curl -X POST http://localhost:8000/api/knowledge/regenerate-embeddings \
  -H "Authorization: Bearer <token>"

# 重新生成特定知識
curl -X POST http://localhost:8000/api/knowledge/regenerate-embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "knowledge_ids": [123, 456, 789]
  }'
```

**回應 (200 OK)**:

```json
{
  "message": "Embedding 重新生成完成",
  "total_processed": 150,
  "successful": 148,
  "failed": 2,
  "failed_ids": [234, 567]
}
```

---

### POST /api/knowledge/{knowledge_id}/intents

新增知識意圖關聯

**權限**: `knowledge:update`

**Path Parameters**:
- `knowledge_id` (integer): 知識 ID

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `intent_id` | integer | ✅ | 意圖 ID |
| `is_primary` | boolean | ❌ | 是否為主要意圖（預設 false） |

**範例**:

```bash
curl -X POST http://localhost:8000/api/knowledge/123/intents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "intent_id": 5,
    "is_primary": true
  }'
```

**回應 (201 Created)**:

```json
{
  "message": "意圖關聯已建立",
  "knowledge_id": 123,
  "intent_id": 5,
  "is_primary": true
}
```

---

### DELETE /api/knowledge/{knowledge_id}/intents/{intent_id}

移除知識意圖關聯

**權限**: `knowledge:update`

**Path Parameters**:
- `knowledge_id` (integer): 知識 ID
- `intent_id` (integer): 意圖 ID

**範例**:

```bash
curl -X DELETE http://localhost:8000/api/knowledge/123/intents/5 \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "message": "意圖關聯已移除",
  "knowledge_id": 123,
  "intent_id": 5
}
```

---

## 意圖管理 API

### GET /api/intents

取得所有意圖

**範例**:

```bash
curl http://localhost:8000/api/intents
```

**回應 (200 OK)**:

```json
{
  "total": 25,
  "items": [
    {
      "id": 5,
      "name": "帳務查詢",
      "type": "knowledge",
      "description": "租金、費用、繳費相關查詢",
      "keywords": ["租金", "繳費", "費用"],
      "confidence_threshold": 0.80,
      "is_enabled": true,
      "priority": 5,
      "created_at": "2025-10-01T00:00:00"
    }
  ]
}
```

---

## 測試情境 API

### GET /api/test/scenarios

列出所有測試情境

**Query Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `status` | string | ❌ | 狀態過濾 (pending/approved/rejected) |
| `difficulty` | string | ❌ | 難度過濾 (easy/medium/hard) |
| `source` | string | ❌ | 來源過濾 (manual/auto/ai) |

**範例**:

```bash
# 列出所有測試情境
curl http://localhost:8000/api/test/scenarios

# 列出待審核情境
curl "http://localhost:8000/api/test/scenarios?status=pending"

# 列出困難題目
curl "http://localhost:8000/api/test/scenarios?difficulty=hard"
```

**回應 (200 OK)**:

```json
{
  "total": 50,
  "items": [
    {
      "id": 10,
      "question": "退租要怎麼辦理？",
      "expected_answer": "提前 30 天通知...",
      "expected_intents": ["退租流程", "租約管理"],
      "difficulty": "medium",
      "status": "pending",
      "source": "manual",
      "created_at": "2026-01-10T10:00:00"
    }
  ]
}
```

---

### POST /api/test/scenarios

新增測試情境

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `question` | string | ✅ | 測試問題 |
| `expected_answer` | string | ❌ | 預期答案 |
| `expected_intents` | array[string] | ❌ | 預期意圖列表 |
| `difficulty` | string | ❌ | 難度 (easy/medium/hard) |
| `vendor_id` | integer | ❌ | 業者 ID |
| `business_type` | string | ❌ | 業態類型 |
| `target_user` | string | ❌ | 目標用戶 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/test/scenarios \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "question": "每個月什麼時候要繳房租？",
    "expected_answer": "租金繳費日為每月 1 號",
    "expected_intents": ["帳務查詢"],
    "difficulty": "easy",
    "target_user": "租客"
  }'
```

**回應 (201 Created)**:

```json
{
  "id": 51,
  "question": "每個月什麼時候要繳房租？",
  "status": "pending",
  "created_at": "2026-01-14T10:00:00"
}
```

---

### POST /api/test/scenarios/{scenario_id}/review

審核測試情境

**Path Parameters**:
- `scenario_id` (integer): 測試情境 ID

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `status` | string | ✅ | 審核結果 (approved/rejected) |
| `reviewed_by` | string | ✅ | 審核者 |
| `review_notes` | string | ❌ | 審核備註 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/test/scenarios/51/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "status": "approved",
    "reviewed_by": "admin",
    "review_notes": "測試情境合理"
  }'
```

**回應 (200 OK)**:

```json
{
  "message": "測試情境已審核",
  "id": 51,
  "status": "approved",
  "reviewed_at": "2026-01-14T10:30:00"
}
```

---

### GET /api/test/unclear-questions/candidates

列出可轉換的用戶問題

**說明**: 列出頻率 ≥2 的未釐清問題，可轉換為測試情境

**範例**:

```bash
curl http://localhost:8000/api/test/unclear-questions/candidates
```

**回應 (200 OK)**:

```json
{
  "total": 15,
  "items": [
    {
      "id": 100,
      "question": "怎麼退租？",
      "frequency": 5,
      "avg_confidence": 0.65,
      "similar_questions": [
        "退租流程",
        "如何退租",
        "退租要準備什麼"
      ],
      "suggested_intent": "退租流程",
      "created_at": "2026-01-10T10:00:00"
    }
  ]
}
```

---

### POST /api/test/unclear-questions/{question_id}/convert

將用戶問題轉換為測試情境

**Path Parameters**:
- `question_id` (integer): 用戶問題 ID

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `difficulty` | string | ❌ | 難度 (預設 medium) |
| `created_by` | string | ❌ | 建立者 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/test/unclear-questions/100/convert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "difficulty": "medium",
    "created_by": "admin"
  }'
```

**回應 (201 Created)**:

```json
{
  "message": "用戶問題已轉換為測試情境",
  "scenario_id": 52,
  "question_id": 100
}
```

---

## 回測 API

### POST /api/backtest/run

執行回測

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `quality_mode` | string | ✅ | 品質模式 (basic/detailed/hybrid) |
| `difficulty` | string | ❌ | 難度過濾 (easy/medium/hard) |
| `sample_size` | integer | ❌ | 抽樣數量 (預設全部) |
| `vendor_id` | integer | ❌ | 業者 ID 過濾 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "quality_mode": "hybrid",
    "difficulty": "medium",
    "sample_size": 20
  }'
```

**回應 (202 Accepted)**:

```json
{
  "message": "回測已啟動",
  "run_id": 15,
  "status": "running",
  "estimated_time_seconds": 120
}
```

---

### GET /api/backtest/status

檢查回測執行狀態

**範例**:

```bash
curl http://localhost:8000/api/backtest/status
```

**回應 (200 OK)**:

```json
{
  "status": "running",
  "run_id": 15,
  "progress": {
    "completed": 12,
    "total": 20,
    "percentage": 60
  },
  "started_at": "2026-01-14T10:00:00",
  "estimated_completion": "2026-01-14T10:02:00"
}
```

---

### GET /api/backtest/results

取得回測結果

**Query Parameters**:
- `run_id` (integer, 選填): 指定回測執行 ID（預設最新）

**範例**:

```bash
# 取得最新回測結果
curl http://localhost:8000/api/backtest/results

# 取得特定回測結果
curl "http://localhost:8000/api/backtest/results?run_id=15"
```

**回應 (200 OK)**:

```json
{
  "run_id": 15,
  "run_name": "2026-01-14 回測",
  "quality_mode": "hybrid",
  "summary": {
    "total_scenarios": 20,
    "passed": 18,
    "failed": 2,
    "pass_rate": 0.90,
    "avg_confidence": 0.82,
    "avg_processing_time_ms": 856
  },
  "results": [
    {
      "scenario_id": 10,
      "question": "退租要怎麼辦理？",
      "expected_intent": "退租流程",
      "actual_intent": "退租流程",
      "confidence": 0.88,
      "passed": true,
      "processing_time_ms": 750
    }
  ],
  "started_at": "2026-01-14T10:00:00",
  "completed_at": "2026-01-14T10:02:00"
}
```

---

## 認證 API

### POST /api/auth/login

用戶登入

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `username` | string | ✅ | 用戶名或郵箱 |
| `password` | string | ✅ | 密碼 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

**回應 (200 OK)**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "roles": ["super_admin"]
  }
}
```

---

### POST /api/auth/logout

用戶登出

**範例**:

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "message": "登出成功"
}
```

---

### GET /api/auth/me

取得當前用戶資訊

**範例**:

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "is_active": true,
  "roles": [
    {
      "id": 1,
      "name": "super_admin",
      "description": "超級管理員"
    }
  ],
  "permissions": [
    "knowledge:view",
    "knowledge:create",
    "knowledge:update",
    "knowledge:delete",
    "admin:view",
    "admin:create"
  ],
  "last_login_at": "2026-01-14T09:00:00"
}
```

---

### GET /api/auth/permissions

取得用戶權限

**範例**:

```bash
curl http://localhost:8000/api/auth/permissions \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "permissions": [
    "knowledge:view",
    "knowledge:create",
    "knowledge:update",
    "knowledge:delete",
    "admin:view",
    "admin:create",
    "admin:update",
    "admin:delete",
    "role:view",
    "role:create"
  ]
}
```

---

## 管理員管理 API

### GET /api/admins

列出所有管理員

**權限**: `admin:view`

**範例**:

```bash
curl http://localhost:8000/api/admins \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "total": 5,
  "items": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "is_active": true,
      "roles": ["super_admin"],
      "last_login_at": "2026-01-14T09:00:00",
      "created_at": "2025-10-01T00:00:00"
    }
  ]
}
```

---

### POST /api/admins

建立管理員

**權限**: `admin:create`

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `username` | string | ✅ | 用戶名 (唯一) |
| `email` | string | ✅ | 郵箱 (唯一) |
| `password` | string | ✅ | 密碼 (最少 8 字元) |
| `role_ids` | array[integer] | ❌ | 角色 ID 列表 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/admins \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "username": "editor1",
    "email": "editor1@example.com",
    "password": "SecurePass123",
    "role_ids": [2]
  }'
```

**回應 (201 Created)**:

```json
{
  "id": 6,
  "username": "editor1",
  "email": "editor1@example.com",
  "is_active": true,
  "roles": [
    {
      "id": 2,
      "name": "editor"
    }
  ],
  "created_at": "2026-01-14T10:00:00"
}
```

---

### PUT /api/admins/{admin_id}

更新管理員

**權限**: `admin:update`

**Path Parameters**:
- `admin_id` (integer): 管理員 ID

**Body Parameters**: 所有欄位選填

**範例**:

```bash
curl -X PUT http://localhost:8000/api/admins/6 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "is_active": false
  }'
```

**回應 (200 OK)**:

```json
{
  "message": "管理員已更新",
  "id": 6,
  "updated_at": "2026-01-14T10:30:00"
}
```

---

### DELETE /api/admins/{admin_id}

刪除管理員

**權限**: `admin:delete`

**Path Parameters**:
- `admin_id` (integer): 管理員 ID

**範例**:

```bash
curl -X DELETE http://localhost:8000/api/admins/6 \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "message": "管理員已刪除",
  "id": 6
}
```

---

## 角色管理 API

### GET /api/roles

列出所有角色

**權限**: `role:view`

**範例**:

```bash
curl http://localhost:8000/api/roles \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "total": 4,
  "items": [
    {
      "id": 1,
      "name": "super_admin",
      "description": "超級管理員",
      "is_system": true,
      "permissions": [
        {
          "id": 1,
          "name": "knowledge:view",
          "description": "查看知識"
        }
      ],
      "created_at": "2025-10-01T00:00:00"
    }
  ]
}
```

---

### POST /api/roles

建立角色

**權限**: `role:create`

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `name` | string | ✅ | 角色名稱 (唯一) |
| `description` | string | ❌ | 描述 |
| `permission_ids` | array[integer] | ❌ | 權限 ID 列表 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/roles \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "content_manager",
    "description": "內容管理員",
    "permission_ids": [1, 2, 3, 4]
  }'
```

**回應 (201 Created)**:

```json
{
  "id": 5,
  "name": "content_manager",
  "description": "內容管理員",
  "permissions_count": 4,
  "created_at": "2026-01-14T10:00:00"
}
```

---

## 配置管理 API

### GET /api/target-users

取得所有目標用戶類型（僅啟用）

**範例**:

```bash
curl http://localhost:8000/api/target-users
```

**回應 (200 OK)**:

```json
{
  "items": [
    {
      "value": "租客",
      "label": "租客",
      "is_enabled": true
    },
    {
      "value": "房東",
      "label": "房東",
      "is_enabled": true
    },
    {
      "value": "物業管理師",
      "label": "物業管理師",
      "is_enabled": true
    }
  ]
}
```

---

### GET /api/target-users-config

取得目標用戶配置（管理介面）

**權限**: `config:view`

**範例**:

```bash
curl http://localhost:8000/api/target-users-config \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "total": 5,
  "items": [
    {
      "id": 1,
      "value": "租客",
      "label": "租客",
      "is_enabled": true,
      "created_at": "2025-10-01T00:00:00"
    },
    {
      "id": 2,
      "value": "房東",
      "label": "房東",
      "is_enabled": true,
      "created_at": "2025-10-01T00:00:00"
    }
  ]
}
```

---

### POST /api/target-users-config

新增目標用戶類型

**權限**: `config:create`

**Body Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `value` | string | ✅ | 值 (唯一) |
| `label` | string | ✅ | 顯示名稱 |

**範例**:

```bash
curl -X POST http://localhost:8000/api/target-users-config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "value": "仲介",
    "label": "房屋仲介"
  }'
```

**回應 (201 Created)**:

```json
{
  "id": 6,
  "value": "仲介",
  "label": "房屋仲介",
  "is_enabled": true,
  "created_at": "2026-01-14T10:00:00"
}
```

---

### DELETE /api/target-users-config/{user_value}

停用目標用戶類型

**權限**: `config:delete`

**Path Parameters**:
- `user_value` (string): 目標用戶值

**範例**:

```bash
curl -X DELETE "http://localhost:8000/api/target-users-config/仲介" \
  -H "Authorization: Bearer <token>"
```

**回應 (200 OK)**:

```json
{
  "message": "目標用戶類型已停用",
  "value": "仲介"
}
```

---

### GET /api/category-config

取得所有 Category 配置

**範例**:

```bash
curl http://localhost:8000/api/category-config
```

**回應 (200 OK)**:

```json
{
  "total": 10,
  "items": [
    {
      "id": 1,
      "value": "帳務",
      "label": "帳務",
      "is_enabled": true,
      "usage_count": 25,
      "created_at": "2025-10-01T00:00:00"
    }
  ]
}
```

---

## 錯誤代碼

### HTTP 狀態碼

| 狀態碼 | 說明 | 常見原因 |
|--------|------|---------|
| 200 | OK | 成功 |
| 201 | Created | 資源建立成功 |
| 400 | Bad Request | 參數錯誤、必填欄位缺失 |
| 401 | Unauthorized | 未認證或 Token 過期 |
| 403 | Forbidden | 無權限 |
| 404 | Not Found | 資源不存在 |
| 409 | Conflict | 資源衝突（如重複建立） |
| 422 | Unprocessable Entity | 資料驗證失敗 |
| 500 | Internal Server Error | 伺服器錯誤 |

### 錯誤回應格式

```json
{
  "detail": "錯誤訊息說明",
  "error_code": "KNOWLEDGE_NOT_FOUND",
  "timestamp": "2026-01-14T10:00:00"
}
```

### 常見錯誤代碼

| 錯誤代碼 | HTTP | 說明 |
|---------|------|------|
| `TOKEN_EXPIRED` | 401 | Token 已過期 |
| `INVALID_CREDENTIALS` | 401 | 帳號或密碼錯誤 |
| `PERMISSION_DENIED` | 403 | 無權限執行此操作 |
| `KNOWLEDGE_NOT_FOUND` | 404 | 知識不存在 |
| `INTENT_NOT_FOUND` | 404 | 意圖不存在 |
| `DUPLICATE_USERNAME` | 409 | 用戶名已存在 |
| `DUPLICATE_EMAIL` | 409 | 郵箱已存在 |
| `VALIDATION_ERROR` | 422 | 資料驗證失敗 |
| `EMBEDDING_GENERATION_FAILED` | 500 | Embedding 生成失敗 |
| `DATABASE_ERROR` | 500 | 資料庫錯誤 |

---

## 相關文件

- [RAG Orchestrator API 參考](./API_REFERENCE_PHASE1.md)
- [資料庫架構文件](../database/DATABASE_SCHEMA.md)
- [系統架構文件](../architecture/SYSTEM_ARCHITECTURE.md)
- [快速開始指南](../guides/QUICKSTART.md)

---

**維護者**: Claude Code
**最後更新**: 2026-01-14
**版本**: 1.0
