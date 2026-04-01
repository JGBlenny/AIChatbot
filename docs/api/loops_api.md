# 迴圈管理 API 文檔

> **版本**: v1
> **基礎路徑**: `/api/v1/loops`
> **建立時間**: 2026-03-27

## 概述

迴圈管理 API 提供知識完善迴圈的完整生命週期管理功能，支援：

- ✅ 啟動新迴圈（固定測試集選取）
- ✅ 執行迭代（同步/非同步模式）
- ✅ 查詢迴圈狀態與進度
- ✅ 驗證效果回測（可選功能）
- ✅ 暫停、恢復、取消迴圈
- ✅ 完成批次、啟動下一批次

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
| `/start` | POST | 啟動新迴圈 | 10.1, 10.4 |
| `/{loop_id}/execute-iteration` | POST | 執行迭代 | 10.2 |
| `/{loop_id}` | GET | 查詢迴圈狀態 | 10.2 |
| `/{loop_id}/validate` | POST | 驗證效果回測 | 9 |
| `/{loop_id}/complete-batch` | POST | 完成批次 | 10.4 |
| `/{loop_id}/pause` | POST | 暫停迴圈 | 10.5 |
| `/{loop_id}/resume` | POST | 恢復迴圈 | 10.5 |
| `/{loop_id}/cancel` | POST | 取消迴圈 | 10.5 |
| `/start-next-batch` | POST | 啟動下一批次 | 10.4 |
| `/` | GET | 列出迴圈（分頁） | 10.1 |

---

## 資料模型

### LoopStartRequest

啟動迴圈的請求參數。

```typescript
interface LoopStartRequest {
  loop_name: string;              // 迴圈名稱（必填，最多 200 字元）
  vendor_id: number;              // 業者 ID（必填，> 0）
  batch_size: number;             // 批次大小（1-3000，預設 50）
  max_iterations: number;         // 最大迭代次數（1-50，預設 10）
  target_pass_rate: number;       // 目標通過率（0.0-1.0，預設 0.85）
  scenario_filters?: object;      // 測試情境篩選條件（可選）
  parent_loop_id?: number;        // 父迴圈 ID（批次關聯，可選）
  budget_limit_usd?: number;      // 成本預算上限（USD，可選）
}
```

**範例**：
```json
{
  "loop_name": "包租業知識完善-第1批",
  "vendor_id": 2,
  "batch_size": 50,
  "max_iterations": 10,
  "target_pass_rate": 0.85,
  "budget_limit_usd": 50.0
}
```

### LoopStartResponse

啟動迴圈的回應資料。

```typescript
interface LoopStartResponse {
  loop_id: number;                           // 迴圈 ID
  loop_name: string;                         // 迴圈名稱
  vendor_id: number;                         // 業者 ID
  status: string;                            // 迴圈狀態（pending/running）
  scenario_ids: number[];                    // 固定測試集 ID 列表
  scenario_selection_strategy: string;       // 選取策略
  difficulty_distribution: {                 // 難度分布
    easy: number;
    medium: number;
    hard: number;
  };
  initial_statistics: object;                // 初始統計資訊
  created_at: string;                        // 創建時間（ISO 8601 格式）
}
```

**範例**：
```json
{
  "loop_id": 123,
  "loop_name": "包租業知識完善-第1批",
  "vendor_id": 2,
  "status": "pending",
  "scenario_ids": [1, 5, 12, 23, 45, ...],
  "scenario_selection_strategy": "stratified_random",
  "difficulty_distribution": {
    "easy": 10,
    "medium": 25,
    "hard": 15
  },
  "initial_statistics": {
    "total_scenarios": 50,
    "estimated_duration_minutes": "10-15"
  },
  "created_at": "2026-03-27T10:00:00Z"
}
```

### ExecuteIterationRequest

執行迭代的請求參數。

```typescript
interface ExecuteIterationRequest {
  async_mode: boolean;  // 是否非同步執行（預設 true）
}
```

### ExecuteIterationResponse

執行迭代的回應資料。

```typescript
interface ExecuteIterationResponse {
  loop_id: number;
  current_iteration: number;
  status: string;
  message: string;
  backtest_result?: object;      // 同步模式時返回完整結果
  execution_task_id?: string;    // 非同步模式時返回任務 ID
}
```

**非同步模式範例**：
```json
{
  "loop_id": 123,
  "current_iteration": 1,
  "status": "running",
  "message": "迭代執行已在背景啟動，請輪詢狀態查詢進度",
  "execution_task_id": "task_123_1711526400.123"
}
```

**同步模式範例**：
```json
{
  "loop_id": 123,
  "current_iteration": 1,
  "status": "reviewing",
  "message": "迭代執行完成，請審核生成的知識",
  "backtest_result": {
    "pass_rate": 0.72,
    "total_tests": 50,
    "passed": 36,
    "failed": 14,
    "duration_seconds": 845
  }
}
```

### LoopStatusResponse

迴圈狀態回應資料。

```typescript
interface LoopStatusResponse {
  loop_id: number;
  loop_name: string;
  vendor_id: number;
  status: string;                 // pending/running/reviewing/validating/completed/failed/paused/cancelled
  current_iteration: number;
  max_iterations: number;
  current_pass_rate?: number;     // 當前通過率（0.0-1.0）
  target_pass_rate: number;       // 目標通過率
  scenario_ids: number[];         // 固定測試集 ID 列表
  total_scenarios: number;
  progress: {                     // 進度資訊
    phase: string;                // backtest/analyzing/generating/reviewing/validating
    percentage: number;           // 0-100
    message: string;              // 進度說明文字
  };
  created_at: string;             // ISO 8601 格式
  updated_at: string;
  completed_at?: string;          // 完成時間（若已完成）
}
```

**範例**：
```json
{
  "loop_id": 123,
  "loop_name": "包租業知識完善-第1批",
  "vendor_id": 2,
  "status": "running",
  "current_iteration": 1,
  "max_iterations": 10,
  "current_pass_rate": null,
  "target_pass_rate": 0.85,
  "scenario_ids": [1, 5, 12, 23, 45],
  "total_scenarios": 50,
  "progress": {
    "phase": "backtest",
    "percentage": 45,
    "message": "正在執行回測：已完成 22/50 個測試情境"
  },
  "created_at": "2026-03-27T10:00:00Z",
  "updated_at": "2026-03-27T10:15:30Z",
  "completed_at": null
}
```

### ValidateLoopRequest

驗證效果回測請求參數。

```typescript
interface ValidateLoopRequest {
  validation_scope: string;       // 驗證範圍（failed_only/all/failed_plus_sample，預設 failed_plus_sample）
  sample_pass_rate: number;       // 抽樣比例（0.0-1.0，預設 0.2）
}
```

### ValidateLoopResponse

驗證效果回測回應資料。

```typescript
interface ValidateLoopResponse {
  loop_id: number;
  validation_result: {
    pass_rate: number;
    total_tests: number;
    passed: number;
    failed: number;
    improvement: number;          // 改善幅度
  };
  validation_passed: boolean;     // 驗證是否通過
  affected_knowledge_ids: number[];
  regression_detected: boolean;   // 是否檢測到 regression
  regression_count: number;       // regression 案例數量
  next_action: string;            // 建議下一步動作
}
```

### CompleteBatchResponse

完成批次回應資料。

```typescript
interface CompleteBatchResponse {
  loop_id: number;
  status: string;                 // completed
  summary: {
    total_iterations: number;
    final_pass_rate: number;
    total_knowledge_generated: number;
    total_knowledge_approved: number;
    total_cost_usd: number;
  };
  message: string;
}
```

---

## 端點詳細說明

### 1. POST /start - 啟動新迴圈

**請求**：
```http
POST /api/v1/loops/start
Content-Type: application/json

{
  "loop_name": "包租業知識完善-第1批",
  "vendor_id": 2,
  "batch_size": 50,
  "max_iterations": 10,
  "target_pass_rate": 0.85,
  "budget_limit_usd": 50.0
}
```

**成功回應** (201 Created):
```json
{
  "loop_id": 123,
  "loop_name": "包租業知識完善-第1批",
  "vendor_id": 2,
  "status": "pending",
  "scenario_ids": [1, 5, 12, 23, 45, 67, 89, ...],
  "scenario_selection_strategy": "stratified_random",
  "difficulty_distribution": {
    "easy": 10,
    "medium": 25,
    "hard": 15
  },
  "initial_statistics": {
    "total_scenarios": 50
  },
  "created_at": "2026-03-27T10:00:00Z"
}
```

**錯誤回應**:
- `400 Bad Request` - 參數驗證錯誤（batch_size 超出範圍、target_pass_rate 不合法等）
- `500 Internal Server Error` - 伺服器內部錯誤

**功能說明**：
- 建立新的迴圈記錄到 `knowledge_completion_loops` 表
- 使用分層隨機抽樣選取固定測試集（按難度分層：easy 20%, medium 50%, hard 30%）
- 若提供 `parent_loop_id`，自動排除父迴圈已使用的測試情境（避免批次間重複）
- 初始化成本追蹤器（若有 `budget_limit_usd`）
- 記錄選取策略與難度分布到資料庫

---

### 2. POST /{loop_id}/execute-iteration - 執行迭代

**請求**：
```http
POST /api/v1/loops/123/execute-iteration
Content-Type: application/json

{
  "async_mode": true
}
```

**成功回應 - 非同步模式** (202 Accepted):
```json
{
  "loop_id": 123,
  "current_iteration": 1,
  "status": "running",
  "message": "迭代執行已在背景啟動，請輪詢狀態查詢進度",
  "execution_task_id": "task_123_1711526400.123"
}
```

**成功回應 - 同步模式** (200 OK):
```json
{
  "loop_id": 123,
  "current_iteration": 1,
  "status": "reviewing",
  "message": "迭代執行完成，請審核生成的知識",
  "backtest_result": {
    "pass_rate": 0.72,
    "total_tests": 50,
    "passed": 36,
    "failed": 14,
    "duration_seconds": 845,
    "knowledge_generated": {
      "sop_count": 5,
      "knowledge_count": 9
    }
  }
}
```

**錯誤回應**:
- `404 Not Found` - 迴圈不存在
- `409 Conflict` - 迴圈已在執行中（並發執行衝突）
- `422 Unprocessable Entity` - 狀態不允許執行（如：已完成、已取消）
- `500 Internal Server Error` - 執行失敗

**功能說明**：
- **非同步模式**（預設）：
  - 使用 `asyncio.create_task()` 在背景執行完整的 8 步驟流程
  - 立即返回 `execution_task_id`，前端需輪詢 `GET /{loop_id}` 查詢進度
  - 避免 HTTP 請求超時（迭代耗時 10-120 分鐘）
  - 檢測並發執行，同一迴圈不能同時執行兩次
- **同步模式**：
  - 等待迭代執行完成後返回完整結果
  - 適用於小批次測試（< 50 題）
  - 可能超時（建議設定 HTTP 客戶端 timeout > 20 分鐘）

**8 步驟流程**（在背景執行）：
1. 執行回測（使用固定測試集 `scenario_ids`）
2. 分析失敗案例
3. 智能分類（OpenAI 分類為 sop_knowledge/form_fill/system_config/api_query）
4. 按類別分離
5. 分別聚類
6. 生成知識（SOP 或通用知識）
7. 更新狀態為 REVIEWING（等待人工審核）
8. 記錄執行事件到 `loop_execution_logs`

---

### 3. GET /{loop_id} - 查詢迴圈狀態

**請求**：
```http
GET /api/v1/loops/123
```

**成功回應** (200 OK):
```json
{
  "loop_id": 123,
  "loop_name": "包租業知識完善-第1批",
  "vendor_id": 2,
  "status": "running",
  "current_iteration": 1,
  "max_iterations": 10,
  "current_pass_rate": null,
  "target_pass_rate": 0.85,
  "scenario_ids": [1, 5, 12, 23, 45],
  "total_scenarios": 50,
  "progress": {
    "phase": "generating",
    "percentage": 75,
    "message": "正在生成知識：已處理 10/14 個失敗案例"
  },
  "created_at": "2026-03-27T10:00:00Z",
  "updated_at": "2026-03-27T10:25:30Z",
  "completed_at": null
}
```

**錯誤回應**:
- `404 Not Found` - 迴圈不存在

**功能說明**：
- 前端輪詢使用（建議每 5 秒輪詢一次）
- 返回當前執行狀態與進度
- `progress.phase` 可能值：
  - `backtest` - 執行回測中
  - `analyzing` - 分析失敗案例中
  - `classifying` - 智能分類中
  - `generating` - 生成知識中
  - `reviewing` - 等待人工審核
  - `validating` - 驗證回測中
- `progress.percentage` 範圍 0-100
- `status` 狀態機：
  - `pending` → `running` → `reviewing` → `validating` → `running` （繼續迭代）
  - `pending` → `running` → `completed` （達成目標）
  - `pending` → `running` → `failed` （執行失敗）
  - `running` → `paused` （暫停）
  - `paused` → `running` （恢復）
  - `running` → `cancelled` （取消）

---

### 4. POST /{loop_id}/validate - 驗證效果回測（可選功能）

**請求**：
```http
POST /api/v1/loops/123/validate
Content-Type: application/json

{
  "validation_scope": "failed_plus_sample",
  "sample_pass_rate": 0.2
}
```

**成功回應** (200 OK):
```json
{
  "loop_id": 123,
  "validation_result": {
    "pass_rate": 0.78,
    "total_tests": 25,
    "passed": 19,
    "failed": 6,
    "improvement": 0.06
  },
  "validation_passed": true,
  "affected_knowledge_ids": [456, 457, 458],
  "regression_detected": false,
  "regression_count": 0,
  "next_action": "continue"
}
```

**錯誤回應**:
- `404 Not Found` - 迴圈不存在
- `422 Unprocessable Entity` - 狀態不允許驗證（需要 REVIEWING 狀態）

**功能說明**：
- **驗證範圍**（`validation_scope`）：
  - `failed_only` - 只測試失敗案例
  - `all` - 測試所有案例（完整驗證）
  - `failed_plus_sample` - 失敗案例 + 抽樣通過案例（預設）
- **Regression 檢測**：檢測原本通過的案例是否因新知識而失敗
- **驗證通過條件**：
  - 改善幅度 ≥ 5% 或 通過率 ≥ 70%
  - 且無 regression 檢測到
- **驗證失敗處理**：
  - 知識標記為 `need_improvement`
  - 保留在正式庫（不刪除）
  - `next_action` 為 `adjust_knowledge`

---

### 5. POST /{loop_id}/complete-batch - 完成批次

**請求**：
```http
POST /api/v1/loops/123/complete-batch
```

**成功回應** (200 OK):
```json
{
  "loop_id": 123,
  "status": "completed",
  "summary": {
    "total_iterations": 5,
    "final_pass_rate": 0.88,
    "total_knowledge_generated": 45,
    "total_knowledge_approved": 38,
    "total_cost_usd": 32.50
  },
  "message": "批次已完成，可啟動下一批次"
}
```

**錯誤回應**:
- `404 Not Found` - 迴圈不存在
- `422 Unprocessable Entity` - 狀態不允許完成（需要 REVIEWING 或 RUNNING 狀態）

**功能說明**：
- 標記迴圈狀態為 `COMPLETED`
- 計算並返回統計摘要（迭代次數、最終通過率、生成知識數量、成本）
- 記錄完成時間到 `completed_at` 欄位
- 可作為啟動下一批次的前置條件

---

### 6. POST /{loop_id}/pause - 暫停迴圈

**請求**：
```http
POST /api/v1/loops/123/pause
```

**成功回應** (200 OK):
```json
{
  "loop_id": 123,
  "status": "paused",
  "message": "迴圈已暫停，可稍後恢復"
}
```

**錯誤回應**:
- `404 Not Found` - 迴圈不存在
- `422 Unprocessable Entity` - 狀態不允許暫停（需要 RUNNING 狀態）

**功能說明**：
- 將迴圈狀態更新為 `PAUSED`
- 若背景任務正在執行，等待當前步驟完成後暫停
- 已生成但未審核的知識保留在 `loop_generated_knowledge` 表

---

### 7. POST /{loop_id}/resume - 恢復迴圈

**請求**：
```http
POST /api/v1/loops/123/resume
```

**成功回應** (200 OK):
```json
{
  "loop_id": 123,
  "status": "running",
  "message": "迴圈已恢復"
}
```

**錯誤回應**:
- `404 Not Found` - 迴圈不存在
- `422 Unprocessable Entity` - 狀態不允許恢復（需要 PAUSED 狀態）

**功能說明**：
- 將迴圈狀態從 `PAUSED` 更新為 `RUNNING`
- 可繼續執行迭代

---

### 8. POST /{loop_id}/cancel - 取消迴圈

**請求**：
```http
POST /api/v1/loops/123/cancel
```

**成功回應** (200 OK):
```json
{
  "loop_id": 123,
  "status": "cancelled",
  "message": "迴圈已取消"
}
```

**錯誤回應**:
- `404 Not Found` - 迴圈不存在

**功能說明**：
- 將迴圈狀態更新為 `CANCELLED`
- 若背景任務正在執行，調用 `AsyncExecutionManager.cancel_task()` 取消任務
- 已生成但未審核的知識保留在 `loop_generated_knowledge` 表（可稍後審核）

---

### 9. POST /start-next-batch - 啟動下一批次

**請求**：
```http
POST /api/v1/loops/start-next-batch
Content-Type: application/json

{
  "loop_name": "包租業知識完善-第2批",
  "vendor_id": 2,
  "batch_size": 50,
  "max_iterations": 10,
  "target_pass_rate": 0.85,
  "parent_loop_id": 123,
  "budget_limit_usd": 50.0
}
```

**成功回應** (201 Created):
```json
{
  "loop_id": 124,
  "loop_name": "包租業知識完善-第2批",
  "vendor_id": 2,
  "status": "pending",
  "scenario_ids": [34, 56, 78, 90, 102, ...],
  "scenario_selection_strategy": "stratified_random",
  "difficulty_distribution": {
    "easy": 10,
    "medium": 25,
    "hard": 15
  },
  "initial_statistics": {
    "total_scenarios": 50,
    "excluded_from_parent": 50
  },
  "created_at": "2026-03-27T12:00:00Z"
}
```

**功能說明**：
- 創建新迴圈並關聯 `parent_loop_id`
- 自動排除父迴圈（及其所有子迴圈）已使用的測試情境
- 確保批次間測試情境不重複
- 其他行為與 `POST /start` 相同

---

### 10. GET / - 列出迴圈（分頁）

**請求**：
```http
GET /api/v1/loops?vendor_id=2&status=running&limit=20&offset=0
```

**查詢參數**：
- `vendor_id` (number, required) - 業者 ID
- `status` (string, optional) - 篩選狀態（pending/running/reviewing/completed/failed/paused/cancelled）
- `limit` (number, optional) - 返回數量（1-200，預設 50）
- `offset` (number, optional) - 偏移量（預設 0）

**成功回應** (200 OK):
```json
{
  "total": 15,
  "items": [
    {
      "loop_id": 123,
      "loop_name": "包租業知識完善-第1批",
      "vendor_id": 2,
      "status": "completed",
      "current_iteration": 5,
      "max_iterations": 10,
      "current_pass_rate": 0.88,
      "target_pass_rate": 0.85,
      "total_scenarios": 50,
      "created_at": "2026-03-27T10:00:00Z",
      "completed_at": "2026-03-27T11:30:00Z"
    },
    {
      "loop_id": 124,
      "loop_name": "包租業知識完善-第2批",
      "vendor_id": 2,
      "status": "running",
      "current_iteration": 2,
      "max_iterations": 10,
      "current_pass_rate": 0.75,
      "target_pass_rate": 0.85,
      "total_scenarios": 50,
      "created_at": "2026-03-27T12:00:00Z",
      "completed_at": null
    }
  ]
}
```

---

## 錯誤處理

### 標準錯誤回應格式

```json
{
  "error_code": "LOOP_NOT_FOUND",
  "message": "迴圈不存在",
  "details": {
    "loop_id": 123
  },
  "timestamp": "2026-03-27T10:00:00Z"
}
```

### HTTP 狀態碼

| 狀態碼 | 說明 | 常見錯誤碼 |
|--------|------|-----------|
| 200 OK | 請求成功 | - |
| 201 Created | 資源創建成功 | - |
| 202 Accepted | 非同步請求已接受 | - |
| 400 Bad Request | 參數驗證錯誤 | INVALID_PARAMETERS |
| 404 Not Found | 資源不存在 | LOOP_NOT_FOUND |
| 409 Conflict | 並發執行衝突、狀態不允許操作 | CONCURRENT_EXECUTION, INVALID_STATE |
| 422 Unprocessable Entity | 業務邏輯錯誤 | BUDGET_EXCEEDED, INVALID_STATE_TRANSITION |
| 500 Internal Server Error | 系統錯誤 | DATABASE_ERROR, OPENAI_API_ERROR |
| 503 Service Unavailable | 外部服務不可用 | OPENAI_API_TIMEOUT |

### 錯誤碼清單

| 錯誤碼 | HTTP 狀態碼 | 說明 |
|--------|------------|------|
| `INVALID_PARAMETERS` | 400 | 參數驗證錯誤（batch_size, target_pass_rate 等） |
| `LOOP_NOT_FOUND` | 404 | 迴圈不存在 |
| `CONCURRENT_EXECUTION` | 409 | 迴圈已在執行中，不允許並發執行 |
| `INVALID_STATE` | 422 | 狀態不允許操作（如：completed 狀態不允許執行迭代） |
| `BUDGET_EXCEEDED` | 422 | 成本預算超出上限 |
| `DATABASE_ERROR` | 500 | 資料庫操作錯誤 |
| `OPENAI_API_ERROR` | 500 | OpenAI API 調用失敗 |
| `OPENAI_API_TIMEOUT` | 503 | OpenAI API 超時 |

---

## 使用場景範例

### 場景 1：快速驗證（50 題）

**目標**：快速驗證知識庫效果，迭代 2-3 次即可。

```bash
# 1. 啟動迴圈
curl -X POST http://localhost:8100/api/v1/loops/start \
  -H "Content-Type: application/json" \
  -d '{
    "loop_name": "快速驗證-50題",
    "vendor_id": 2,
    "batch_size": 50,
    "max_iterations": 3,
    "target_pass_rate": 0.75,
    "budget_limit_usd": 20.0
  }'

# 回應：loop_id = 123

# 2. 執行第一次迭代（非同步）
curl -X POST http://localhost:8100/api/v1/loops/123/execute-iteration \
  -H "Content-Type: application/json" \
  -d '{"async_mode": true}'

# 回應：execution_task_id = "task_123_1711526400.123"

# 3. 輪詢狀態（每 5 秒）
while true; do
  curl http://localhost:8100/api/v1/loops/123
  sleep 5
done

# 4. 當狀態變為 "reviewing" 時，前往審核中心批量審核知識
# 使用 loop_knowledge API（參見 loop_knowledge_api.md）

# 5. 審核完成後，若通過率未達標（< 0.75），執行下一次迭代
curl -X POST http://localhost:8100/api/v1/loops/123/execute-iteration \
  -H "Content-Type: application/json" \
  -d '{"async_mode": true}'

# 6. 重複步驟 3-5 直到通過率達標或達到最大迭代次數（3 次）

# 7. 完成批次
curl -X POST http://localhost:8100/api/v1/loops/123/complete-batch
```

---

### 場景 2：標準測試（500 題）

**目標**：全面測試知識庫，允許多次迭代（最多 10 次）。

```bash
# 1. 啟動迴圈
curl -X POST http://localhost:8100/api/v1/loops/start \
  -H "Content-Type: application/json" \
  -d '{
    "loop_name": "標準測試-500題",
    "vendor_id": 2,
    "batch_size": 500,
    "max_iterations": 10,
    "target_pass_rate": 0.85,
    "budget_limit_usd": 100.0
  }'

# 2-7. 與場景 1 相同，但預期執行時間更長（60-90 分鐘/次迭代）
```

---

### 場景 3：批次處理（第 1 批 50 題 → 第 2 批 50 題）

**目標**：分批處理大量測試情境，避免單次測試集過大。

```bash
# 1. 啟動第 1 批次
curl -X POST http://localhost:8100/api/v1/loops/start \
  -H "Content-Type: application/json" \
  -d '{
    "loop_name": "包租業知識完善-第1批",
    "vendor_id": 2,
    "batch_size": 50,
    "max_iterations": 10,
    "target_pass_rate": 0.85
  }'

# 回應：loop_id = 123, scenario_ids = [1, 5, 12, ...]

# 2. 執行迭代、審核知識、完成第 1 批次（參考場景 1）
curl -X POST http://localhost:8100/api/v1/loops/123/complete-batch

# 3. 啟動第 2 批次（自動排除第 1 批次使用的測試情境）
curl -X POST http://localhost:8100/api/v1/loops/start-next-batch \
  -H "Content-Type: application/json" \
  -d '{
    "loop_name": "包租業知識完善-第2批",
    "vendor_id": 2,
    "batch_size": 50,
    "max_iterations": 10,
    "target_pass_rate": 0.85,
    "parent_loop_id": 123
  }'

# 回應：loop_id = 124, scenario_ids = [34, 56, 78, ...]（不包含第 1 批的 scenario_ids）

# 4. 重複步驟 2-3 處理第 2 批次
```

---

### 場景 4：驗證效果回測（可選功能）

**目標**：審核知識後，快速驗證改善效果，檢測 regression。

```bash
# 1. 執行迭代並審核知識（狀態變為 REVIEWING）
# （參考場景 1 步驟 1-4）

# 2. 執行驗證回測（只測試失敗案例 + 抽樣 20% 通過案例）
curl -X POST http://localhost:8100/api/v1/loops/123/validate \
  -H "Content-Type: application/json" \
  -d '{
    "validation_scope": "failed_plus_sample",
    "sample_pass_rate": 0.2
  }'

# 回應：
# {
#   "validation_passed": true,
#   "validation_result": {"pass_rate": 0.82, "improvement": 0.10},
#   "regression_detected": false,
#   "next_action": "continue"
# }

# 3. 若驗證通過，繼續下一次迭代或完成批次
# 若驗證失敗（regression_detected = true），調整知識並重新審核
```

---

## 前端整合建議

### 輪詢機制

```typescript
// 前端輪詢範例（Vue 3 + TypeScript）
import { ref, onMounted, onUnmounted } from 'vue';

const loopStatus = ref<LoopStatusResponse | null>(null);
let pollingInterval: number | null = null;

async function startPolling(loopId: number) {
  pollingInterval = setInterval(async () => {
    try {
      const response = await fetch(`/api/v1/loops/${loopId}`);
      loopStatus.value = await response.json();

      // 停止輪詢條件
      if (['reviewing', 'completed', 'failed', 'cancelled'].includes(loopStatus.value.status)) {
        stopPolling();
      }
    } catch (error) {
      console.error('輪詢狀態失敗:', error);
    }
  }, 5000); // 每 5 秒輪詢一次
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

onUnmounted(() => {
  stopPolling();
});
```

### 進度顯示

```vue
<template>
  <div v-if="loopStatus">
    <h3>{{ loopStatus.loop_name }}</h3>
    <p>狀態：{{ statusText[loopStatus.status] }}</p>
    <p>迭代次數：{{ loopStatus.current_iteration }} / {{ loopStatus.max_iterations }}</p>
    <p>當前通過率：{{ (loopStatus.current_pass_rate * 100).toFixed(1) }}%</p>

    <!-- 進度條 -->
    <div class="progress-bar">
      <div class="progress-bar-fill" :style="{ width: loopStatus.progress.percentage + '%' }"></div>
    </div>
    <p>{{ loopStatus.progress.message }}</p>
  </div>
</template>

<script setup lang="ts">
const statusText: Record<string, string> = {
  pending: '等待執行',
  running: '執行中',
  reviewing: '等待審核',
  validating: '驗證中',
  completed: '已完成',
  failed: '執行失敗',
  paused: '已暫停',
  cancelled: '已取消'
};
</script>
```

---

## 變更歷史

| 日期 | 版本 | 變更內容 | 修改者 |
|------|------|---------|--------|
| 2026-03-27 | 1.0 | 初始版本 | AI Assistant |

---

**相關文件**：
- [知識審核 API 文檔](./loop_knowledge_api.md)
- [設計文件](../../.kiro/specs/backtest-knowledge-refinement/design.md)
- [需求文件](../../.kiro/specs/backtest-knowledge-refinement/requirements.md)
