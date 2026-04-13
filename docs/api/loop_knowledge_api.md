# 知識審核 API 文檔

> **版本**: v1
> **基礎路徑**: `/api/v1/loop-knowledge`
> **建立時間**: 2026-03-27

## 概述

知識審核 API 提供知識完善迴圈生成的知識審核功能，支援：

- ✅ 查詢待審核知識（支援篩選與分頁）
- ✅ 單一知識審核（批准/拒絕/修改）
- ✅ 批量知識審核（高效處理 10-100 個項目）
- ✅ 自動同步到正式知識庫（knowledge_base / vendor_sop_items）
- ✅ 重複檢測警告顯示

---

## 目錄

1. [API 端點清單](#api-端點清單)
2. [資料模型](#資料模型)
3. [端點詳細說明](#端點詳細說明)
4. [錯誤處理](#錯誤處理)
5. [使用場景範例](#使用場景範例)

---

## API 端點清單

| 端點 | 方法 | 說明 | 需求覆蓋 |
|------|------|------|---------|
| `/loop-knowledge/pending` | GET | 查詢待審核知識 | 8.1 |
| `/loop-knowledge/{knowledge_id}/review` | POST | 單一知識審核 | 8.2 |
| `/loop-knowledge/batch-review` | POST | 批量知識審核 | 8.3 |

---

## 資料模型

### PendingKnowledgeQuery

查詢待審核知識的參數。

```typescript
interface PendingKnowledgeQuery {
  vendor_id: number;              // 業者 ID（必填）
  loop_id?: number;               // 迴圈 ID（選填）
  knowledge_type?: string;        // 知識類型：'sop' 或 null（選填）
  status: string;                 // 狀態（預設 'pending'）
  limit: number;                  // 返回數量（1-200，預設 50）
  offset: number;                 // 偏移量（預設 0）
}
```

**範例**：
```json
{
  "vendor_id": 2,
  "knowledge_type": "sop",
  "status": "pending",
  "limit": 50,
  "offset": 0
}
```

### PendingKnowledgeItem

待審核知識項目。

```typescript
interface PendingKnowledgeItem {
  id: number;                     // 知識 ID
  loop_id: number;                // 迴圈 ID
  iteration: number;              // 迭代次數
  question: string;               // 問題摘要
  answer: string;                 // 答案內容
  knowledge_type?: string;        // 知識類型（'sop' 或 null）
  sop_config?: {                  // SOP 配置（僅 knowledge_type='sop' 時有值）
    category_id: number;
    group_id: number;
    item_name: string;
  };
  similar_knowledge?: {           // 重複檢測結果
    detected: boolean;
    items: Array<{
      id: number;
      source_table: string;       // 'knowledge_base' 或 'vendor_sop_items'
      question_summary: string;
      similarity_score: number;   // 0.0-1.0
    }>;
  };
  duplication_warning?: string;   // 重複警告文字
  status: string;                 // 'pending' / 'approved' / 'rejected'
  created_at: string;             // ISO 8601 格式
}
```

**範例**：
```json
{
  "id": 1,
  "loop_id": 123,
  "iteration": 1,
  "question": "租金每月幾號繳納？",
  "answer": "租金應於每月 5 日前繳納。若遇假日則順延至下一個工作日。逾期繳納將收取滯納金。",
  "knowledge_type": null,
  "sop_config": null,
  "similar_knowledge": {
    "detected": true,
    "items": [
      {
        "id": 456,
        "source_table": "knowledge_base",
        "question_summary": "租金繳納日期說明",
        "similarity_score": 0.93
      }
    ]
  },
  "duplication_warning": "檢測到 1 個高度相似的知識（相似度 93%）",
  "status": "pending",
  "created_at": "2026-03-27T10:00:00Z"
}
```

### PendingKnowledgeResponse

查詢待審核知識的回應。

```typescript
interface PendingKnowledgeResponse {
  total: number;                  // 符合條件的總數
  items: PendingKnowledgeItem[];  // 知識項目列表
}
```

### ReviewKnowledgeRequest

審核知識的請求參數。

```typescript
interface ReviewKnowledgeRequest {
  action: string;                 // 動作：'approve' 或 'reject'
  modifications?: {               // 修改內容（選填）
    question?: string;
    answer?: string;
    keywords?: string[];
    [key: string]: any;
  };
  review_notes?: string;          // 審核備註（選填）
}
```

**範例**：
```json
{
  "action": "approve",
  "modifications": {
    "question": "租金每月幾號繳納？",
    "answer": "租金應於每月 5 日前繳納。",
    "keywords": ["租金", "繳納", "期限"]
  },
  "review_notes": "已確認內容正確，補充關鍵字"
}
```

### ReviewKnowledgeResponse

審核知識的回應。

```typescript
interface ReviewKnowledgeResponse {
  knowledge_id: number;
  action: string;                 // 'approve' 或 'reject'
  synced: boolean;                // 是否已同步到正式庫
  synced_to?: string;             // 同步目標：'knowledge_base' 或 'vendor_sop_items'
  synced_id?: number;             // 同步後的 ID
  message: string;                // 回應訊息
}
```

**批准並同步範例**：
```json
{
  "knowledge_id": 1,
  "action": "approve",
  "synced": true,
  "synced_to": "knowledge_base",
  "synced_id": 456,
  "message": "知識已批准並同步到 knowledge_base (ID: 456)"
}
```

**拒絕範例**：
```json
{
  "knowledge_id": 2,
  "action": "reject",
  "synced": false,
  "synced_to": null,
  "synced_id": null,
  "message": "知識已拒絕，不同步"
}
```

### BatchReviewRequest

批量審核的請求參數。

```typescript
interface BatchReviewRequest {
  knowledge_ids: number[];        // 知識 ID 列表（1-100 個）
  action: string;                 // 動作：'approve' 或 'reject'
  modifications?: {               // 批量修改欄位（選填）
    keywords?: string[];
    [key: string]: any;
  };
}
```

**範例**：
```json
{
  "knowledge_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "action": "approve",
  "modifications": {
    "keywords": ["租金", "繳納", "管理"]
  }
}
```

### BatchReviewFailedItem

批量審核中失敗的項目。

```typescript
interface BatchReviewFailedItem {
  knowledge_id: number;
  error: string;                  // 錯誤訊息
}
```

### BatchReviewResponse

批量審核的回應。

```typescript
interface BatchReviewResponse {
  total: number;                  // 總項目數
  successful: number;             // 成功數量
  failed: number;                 // 失敗數量
  failed_items: BatchReviewFailedItem[];  // 失敗項目列表
  duration_ms: number;            // 執行時間（毫秒）
}
```

**範例**：
```json
{
  "total": 10,
  "successful": 8,
  "failed": 2,
  "failed_items": [
    {
      "knowledge_id": 3,
      "error": "知識不存在"
    },
    {
      "knowledge_id": 7,
      "error": "同步失敗：embedding API 超時"
    }
  ],
  "duration_ms": 5432
}
```

---

## 端點詳細說明

### 1. GET /loop-knowledge/pending - 查詢待審核知識

**請求**：
```http
GET /api/v1/loop-knowledge/pending?vendor_id=2&status=pending&limit=50&offset=0
```

**查詢參數**：
- `vendor_id` (number, **required**) - 業者 ID
- `loop_id` (number, optional) - 篩選特定迴圈的知識
- `knowledge_type` (string, optional) - 篩選知識類型（'sop' 或 null）
- `status` (string, optional) - 篩選狀態（預設 'pending'）
- `limit` (number, optional) - 返回數量（1-200，預設 50）
- `offset` (number, optional) - 偏移量（預設 0）

**成功回應** (200 OK):
```json
{
  "total": 150,
  "items": [
    {
      "id": 1,
      "loop_id": 123,
      "iteration": 1,
      "question": "租金每月幾號繳納？",
      "answer": "租金應於每月 5 日前繳納。",
      "knowledge_type": null,
      "sop_config": null,
      "similar_knowledge": {
        "detected": true,
        "items": [
          {
            "id": 456,
            "source_table": "knowledge_base",
            "question_summary": "租金繳納日期說明",
            "similarity_score": 0.93
          }
        ]
      },
      "duplication_warning": "檢測到 1 個高度相似的知識（相似度 93%）",
      "status": "pending",
      "created_at": "2026-03-27T10:00:00Z"
    },
    {
      "id": 2,
      "loop_id": 123,
      "iteration": 1,
      "question": "如何申請續約？",
      "answer": "租約到期前 30 天可提出續約申請。",
      "knowledge_type": "sop",
      "sop_config": {
        "category_id": 1,
        "group_id": 2,
        "item_name": "租約續約申請流程"
      },
      "similar_knowledge": null,
      "duplication_warning": null,
      "status": "pending",
      "created_at": "2026-03-27T10:05:00Z"
    }
  ]
}
```

**錯誤回應**:
- `400 Bad Request` - 參數驗證錯誤
- `500 Internal Server Error` - 查詢失敗

**功能說明**：
- 從 `loop_generated_knowledge` 表查詢知識
- 支援多維度篩選（迴圈、類型、狀態）
- 支援分頁（limit + offset）
- 自動生成 `duplication_warning` 文字（若有重複檢測結果）
- 返回結果按 `created_at` 降序排列（最新的在前）

**重複檢測警告邏輯**：
```typescript
// 前端顯示邏輯範例
function getWarningLevel(similarityScore: number): 'high' | 'medium' | 'low' {
  if (similarityScore >= 0.95) return 'high';      // 幾乎完全相同
  if (similarityScore >= 0.85) return 'medium';    // 高度相似
  return 'low';                                     // 相關知識
}

// 前端顯示範例
if (item.duplication_warning) {
  const level = getWarningLevel(item.similar_knowledge.items[0].similarity_score);
  const color = {
    high: 'red',
    medium: 'orange',
    low: 'yellow'
  }[level];

  // 顯示警告圖標與文字
  console.log(`⚠️ ${item.duplication_warning}`);
}
```

---

### 2. POST /loop-knowledge/{knowledge_id}/review - 單一知識審核

**請求**：
```http
POST /api/v1/loop-knowledge/1/review
Content-Type: application/json

{
  "action": "approve",
  "modifications": {
    "question": "租金每月幾號繳納？",
    "answer": "租金應於每月 5 日前繳納。若遇假日則順延至下一個工作日。",
    "keywords": ["租金", "繳納", "期限"]
  },
  "review_notes": "已確認內容正確，補充關鍵字"
}
```

**成功回應** (200 OK):
```json
{
  "knowledge_id": 1,
  "action": "approve",
  "synced": true,
  "synced_to": "knowledge_base",
  "synced_id": 456,
  "message": "知識已批准並同步到 knowledge_base (ID: 456)"
}
```

**錯誤回應**:
- `404 Not Found` - 知識不存在
- `400 Bad Request` - 參數驗證錯誤（action 不合法）
- `500 Internal Server Error` - 同步失敗

**功能說明**：

1. **審核流程**：
   - 更新 `loop_generated_knowledge` 表的 `status` 欄位（'approved' 或 'rejected'）
   - 若有 `modifications`，更新對應欄位
   - 記錄 `review_notes` 到 `review_notes` 欄位

2. **同步流程**（僅 action='approve' 時執行）：
   - 根據 `knowledge_type` 判斷同步目標：
     - `knowledge_type = 'sop'` → 同步到 `vendor_sop_items`
     - `knowledge_type = null` → 同步到 `knowledge_base`
   - 調用 Embedding API 生成向量（`embedding` 欄位）
   - 寫入正式知識庫
   - 更新 `loop_generated_knowledge.status = 'synced'`
   - 更新 `loop_generated_knowledge.synced_to` 和 `synced_id`

3. **SOP 知識同步詳情**：
   ```sql
   -- 同步到 vendor_sop_items
   INSERT INTO vendor_sop_items (
     vendor_id,
     category_id,
     group_id,
     item_name,
     sop_content,
     trigger_mode,
     embedding,
     source,
     source_loop_id,
     source_loop_knowledge_id,
     status,
     created_at
   ) VALUES (
     ...,
     'loop',      -- 來源標記
     123,         -- source_loop_id
     1,           -- source_loop_knowledge_id
     'approved',
     NOW()
   )
   ```

4. **通用知識同步詳情**：
   ```sql
   -- 同步到 knowledge_base
   INSERT INTO knowledge_base (
     question_summary,
     answer,
     embedding,
     vendor_ids,
     scope,
     keywords,
     source,
     source_loop_id,
     source_loop_knowledge_id,
     is_active,
     created_at
   ) VALUES (
     ...,
     ARRAY[vendor_id],  -- 業者 ID 陣列
     'vendor',          -- 業者專屬
     'loop',            -- 來源標記
     123,               -- source_loop_id
     1,                 -- source_loop_knowledge_id
     TRUE,
     NOW()
   )
   ```

---

### 3. POST /loop-knowledge/batch-review - 批量知識審核

**請求**：
```http
POST /api/v1/loop-knowledge/batch-review
Content-Type: application/json

{
  "knowledge_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "action": "approve",
  "modifications": {
    "keywords": ["租金", "繳納", "管理"]
  }
}
```

**成功回應** (200 OK):
```json
{
  "total": 10,
  "successful": 8,
  "failed": 2,
  "failed_items": [
    {
      "knowledge_id": 3,
      "error": "知識不存在"
    },
    {
      "knowledge_id": 7,
      "error": "同步失敗：embedding API 超時"
    }
  ],
  "duration_ms": 5432
}
```

**錯誤回應**:
- `400 Bad Request` - 參數驗證錯誤（knowledge_ids 超過 100 個、action 不合法）
- `500 Internal Server Error` - 批量處理失敗

**功能說明**：

1. **批量處理策略**：
   - **部分成功模式**：一個項目失敗不影響其他項目
   - 使用 `try-except` 包裹每個項目的處理邏輯
   - 記錄失敗項目到 `failed_items` 列表
   - 繼續處理剩餘項目

2. **處理流程**：
   ```python
   start_time = time.time()
   successful = 0
   failed = 0
   failed_items = []

   for knowledge_id in knowledge_ids:
       try:
           # 審核單一知識（與單一審核相同的邏輯）
           await review_single_knowledge(knowledge_id, action, modifications)
           successful += 1
       except Exception as e:
           failed += 1
           failed_items.append({
               "knowledge_id": knowledge_id,
               "error": str(e)
           })

   duration_ms = int((time.time() - start_time) * 1000)
   ```

3. **效能考量**：
   - **併發限制**：每次最多處理 100 個項目（Pydantic 驗證）
   - **並發處理**：可使用 `asyncio.gather()` 並發調用 embedding API
   - **超時控制**：單一項目處理超時時間 30 秒（避免長時間阻塞）
   - **預期耗時**：
     - 10 個項目：< 5 秒
     - 50 個項目：< 20 秒
     - 100 個項目：< 40 秒

4. **前端處理建議**：
   - 顯示處理進度條（`successful / total`）
   - 顯示失敗項目列表，提供重試按鈕
   - 記錄批量操作歷史（時間、數量、成功率）

---

## 錯誤處理

### 標準錯誤回應格式

```json
{
  "error_code": "KNOWLEDGE_NOT_FOUND",
  "message": "知識不存在",
  "details": {
    "knowledge_id": 123
  },
  "timestamp": "2026-03-27T10:00:00Z"
}
```

### HTTP 狀態碼

| 狀態碼 | 說明 | 常見錯誤碼 |
|--------|------|-----------|
| 200 OK | 請求成功 | - |
| 400 Bad Request | 參數驗證錯誤 | INVALID_PARAMETERS, INVALID_ACTION |
| 404 Not Found | 知識不存在 | KNOWLEDGE_NOT_FOUND |
| 500 Internal Server Error | 系統錯誤 | DATABASE_ERROR, EMBEDDING_API_ERROR, SYNC_FAILED |

### 錯誤碼清單

| 錯誤碼 | HTTP 狀態碼 | 說明 |
|--------|------------|------|
| `INVALID_PARAMETERS` | 400 | 參數驗證錯誤（knowledge_ids 超過 100 個、limit 超出範圍等） |
| `INVALID_ACTION` | 400 | action 不合法（非 'approve' 或 'reject'） |
| `KNOWLEDGE_NOT_FOUND` | 404 | 知識不存在 |
| `DATABASE_ERROR` | 500 | 資料庫操作錯誤 |
| `EMBEDDING_API_ERROR` | 500 | Embedding API 調用失敗 |
| `SYNC_FAILED` | 500 | 同步到正式庫失敗 |

---

## 使用場景範例

### 場景 1：查詢並篩選待審核知識

**目標**：查詢業者 ID = 2、迴圈 ID = 123 的待審核知識，只顯示無重複警告的項目。

```bash
# 1. 查詢待審核知識
curl "http://localhost:8100/api/v1/loop-knowledge/pending?vendor_id=2&loop_id=123&status=pending&limit=50&offset=0"

# 2. 前端篩選：過濾出無重複警告的項目
# （在前端 JavaScript 中處理）
const filteredItems = response.items.filter(item => !item.duplication_warning);

# 3. 顯示篩選後的列表
console.log(`共 ${filteredItems.length} 個無重複警告的知識項目`);
```

---

### 場景 2：單一審核並修改知識

**目標**：審核知識 ID = 1，修改問題與答案後批准。

```bash
curl -X POST http://localhost:8100/api/v1/loop-knowledge/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "modifications": {
      "question": "租金每月幾號繳納？",
      "answer": "租金應於每月 5 日前繳納。若遇假日則順延至下一個工作日。",
      "keywords": ["租金", "繳納", "期限"]
    },
    "review_notes": "已確認內容正確，補充關鍵字與假日規則"
  }'

# 回應：
# {
#   "knowledge_id": 1,
#   "action": "approve",
#   "synced": true,
#   "synced_to": "knowledge_base",
#   "synced_id": 456,
#   "message": "知識已批准並同步到 knowledge_base (ID: 456)"
# }
```

---

### 場景 3：批量審核無重複警告的知識

**目標**：批量批准所有無重複警告的知識（假設有 20 個）。

```bash
# 1. 查詢待審核知識
RESPONSE=$(curl -s "http://localhost:8100/api/v1/loop-knowledge/pending?vendor_id=2&loop_id=123&status=pending&limit=200")

# 2. 前端篩選：提取無重複警告的知識 ID
# （在前端 JavaScript 中處理）
const noWarningIds = response.items
  .filter(item => !item.duplication_warning)
  .map(item => item.id);

console.log(`已選取 ${noWarningIds.length} 個無重複警告的知識`);

# 3. 批量批准
curl -X POST http://localhost:8100/api/v1/loop-knowledge/batch-review \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_ids": [1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
    "action": "approve"
  }'

# 回應：
# {
#   "total": 18,
#   "successful": 17,
#   "failed": 1,
#   "failed_items": [
#     {
#       "knowledge_id": 7,
#       "error": "embedding API 超時"
#     }
#   ],
#   "duration_ms": 4320
# }

# 4. 處理失敗項目：重試 knowledge_id = 7
curl -X POST http://localhost:8100/api/v1/loop-knowledge/7/review \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
```

---

### 場景 4：處理重複檢測警告

**目標**：查看重複檢測警告，決定批准或拒絕。

```bash
# 1. 查詢待審核知識
curl "http://localhost:8100/api/v1/loop-knowledge/pending?vendor_id=2&status=pending&limit=50"

# 回應中包含重複警告：
# {
#   "id": 3,
#   "question": "租金繳納日期是幾號？",
#   "answer": "租金應於每月 5 日前繳納。",
#   "similar_knowledge": {
#     "detected": true,
#     "items": [
#       {
#         "id": 456,
#         "source_table": "knowledge_base",
#         "question_summary": "租金繳納日期說明",
#         "similarity_score": 0.93
#       }
#     ]
#   },
#   "duplication_warning": "檢測到 1 個高度相似的知識（相似度 93%）"
# }

# 2. 前端顯示警告對話框
# ⚠️ 重複檢測警告
#
# 檢測到 1 個高度相似的知識（相似度 93%）：
# - [knowledge_base #456] 租金繳納日期說明
#
# 建議：請人工判斷是否為重複內容。
# - 若內容重複 → 拒絕
# - 若有補充資訊 → 批准並修改

# 3a. 判斷為重複 → 拒絕
curl -X POST http://localhost:8100/api/v1/loop-knowledge/3/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "reject",
    "review_notes": "與現有知識 #456 重複"
  }'

# 3b. 判斷為補充資訊 → 批准並修改
curl -X POST http://localhost:8100/api/v1/loop-knowledge/3/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "modifications": {
      "question": "租金繳納日期與逾期規則",
      "answer": "租金應於每月 5 日前繳納。逾期將收取滯納金。"
    },
    "review_notes": "補充逾期規則，與 #456 互補"
  }'
```

---

## 前端整合建議

### 審核中心界面設計

```vue
<template>
  <div class="review-center">
    <!-- 篩選欄 -->
    <div class="filters">
      <select v-model="filters.loop_id">
        <option :value="null">所有迴圈</option>
        <option v-for="loop in loops" :key="loop.id" :value="loop.id">
          {{ loop.loop_name }}
        </option>
      </select>

      <select v-model="filters.knowledge_type">
        <option :value="null">所有類型</option>
        <option value="sop">SOP 知識</option>
        <option value="general">通用知識</option>
      </select>

      <label>
        <input type="checkbox" v-model="filters.hideWarnings" />
        隱藏重複警告
      </label>

      <button @click="fetchKnowledge">查詢</button>
    </div>

    <!-- 批量操作工具列 -->
    <div class="batch-actions" v-if="selectedIds.length > 0">
      <span>已選取 {{ selectedIds.length }} 個項目</span>
      <button @click="batchApprove">批量批准</button>
      <button @click="batchReject">批量拒絕</button>
    </div>

    <!-- 知識列表 -->
    <table class="knowledge-table">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleSelectAll" /></th>
          <th>ID</th>
          <th>問題</th>
          <th>答案</th>
          <th>類型</th>
          <th>重複檢測</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in filteredItems" :key="item.id">
          <td><input type="checkbox" :value="item.id" v-model="selectedIds" /></td>
          <td>{{ item.id }}</td>
          <td>{{ item.question }}</td>
          <td>{{ item.answer.substring(0, 50) }}...</td>
          <td>{{ item.knowledge_type || '通用' }}</td>
          <td>
            <span v-if="item.duplication_warning" class="warning">
              ⚠️ {{ item.duplication_warning }}
            </span>
            <span v-else class="ok">✓ 無重複</span>
          </td>
          <td>
            <button @click="reviewKnowledge(item.id, 'approve')">批准</button>
            <button @click="reviewKnowledge(item.id, 'reject')">拒絕</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 分頁 -->
    <div class="pagination">
      <button @click="prevPage" :disabled="offset === 0">上一頁</button>
      <span>第 {{ currentPage }} / {{ totalPages }} 頁</span>
      <button @click="nextPage" :disabled="offset + limit >= total">下一頁</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const filters = ref({
  loop_id: null,
  knowledge_type: null,
  hideWarnings: false
});

const knowledgeItems = ref<PendingKnowledgeItem[]>([]);
const selectedIds = ref<number[]>([]);
const limit = ref(50);
const offset = ref(0);
const total = ref(0);

const filteredItems = computed(() => {
  let items = knowledgeItems.value;

  // 隱藏重複警告
  if (filters.value.hideWarnings) {
    items = items.filter(item => !item.duplication_warning);
  }

  return items;
});

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const totalPages = computed(() => Math.ceil(total.value / limit.value));

async function fetchKnowledge() {
  const params = new URLSearchParams({
    vendor_id: '2',
    status: 'pending',
    limit: String(limit.value),
    offset: String(offset.value)
  });

  if (filters.value.loop_id) params.append('loop_id', String(filters.value.loop_id));
  if (filters.value.knowledge_type) params.append('knowledge_type', filters.value.knowledge_type);

  const response = await fetch(`/api/v1/loop-knowledge/pending?${params}`);
  const data = await response.json();

  knowledgeItems.value = data.items;
  total.value = data.total;
}

async function reviewKnowledge(knowledgeId: number, action: string) {
  const response = await fetch(`/api/v1/loop-knowledge/${knowledgeId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action })
  });

  if (response.ok) {
    // 移除已審核的項目
    knowledgeItems.value = knowledgeItems.value.filter(item => item.id !== knowledgeId);
    total.value--;
  }
}

async function batchApprove() {
  if (selectedIds.value.length === 0) return;

  const response = await fetch('/api/v1/loop-knowledge/batch-review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      knowledge_ids: selectedIds.value,
      action: 'approve'
    })
  });

  const result = await response.json();

  // 顯示結果摘要
  alert(`批量批准完成\n成功：${result.successful}\n失敗：${result.failed}`);

  // 移除成功的項目
  knowledgeItems.value = knowledgeItems.value.filter(
    item => !selectedIds.value.includes(item.id) ||
            result.failed_items.some(f => f.knowledge_id === item.id)
  );

  selectedIds.value = [];
  fetchKnowledge();
}

function toggleSelectAll(event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  selectedIds.value = checked ? filteredItems.value.map(item => item.id) : [];
}
</script>
```

---

## 變更歷史

| 日期 | 版本 | 變更內容 | 修改者 |
|------|------|---------|--------|
| 2026-03-27 | 1.0 | 初始版本 | AI Assistant |

---

**相關文件**：
- [迴圈管理 API 文檔](./loops_api.md)
- [設計文件](../../.kiro/specs/backtest-knowledge-refinement/design.md)
- [需求文件](../../.kiro/specs/backtest-knowledge-refinement/requirements.md)
