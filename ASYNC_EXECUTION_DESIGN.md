# 非同步執行模式設計（解決前端 Timeout 問題）

## 問題描述

### 當前設計的 Timeout 風險

| 測試規模 | 執行時間 | HTTP Timeout | 結果 |
|---------|---------|-------------|------|
| 50 題 | 10-15 分鐘 | 30-60 秒 | ❌ 超時 |
| 500 題 | 60-90 分鐘 | 30-60 秒 | ❌ 超時 |
| 3000 題 | 90-120 分鐘 | 30-60 秒 | ❌ 超時 |

### 問題場景

```
用戶操作：點擊「執行下一次迭代」按鈕
前端：POST /api/v1/loops/12/execute-iteration
後端：開始執行（需要 60 分鐘）
前端：60 秒後 → ❌ Timeout Error

問題：
1. 前端顯示錯誤，用戶以為失敗
2. 但後端仍在正常執行
3. 用戶可能重複點擊（建立多個並發執行）
4. 無法追蹤執行進度
```

---

## 解決方案 1：非同步執行 + 狀態輪詢（推薦）

### 執行流程

```
1. 前端發送請求
   POST /api/v1/loops/12/execute-iteration

2. 後端立即返回（< 1 秒）
   Response:
   {
     "loop_id": 12,
     "status": "RUNNING",
     "current_iteration": 2,
     "started_at": "2026-03-27T10:00:00Z",
     "estimated_duration_minutes": 60
   }

3. 後端在背景執行
   - 使用背景任務（Celery / asyncio Task / 獨立 Thread）
   - 更新 loop 狀態到資料庫

4. 前端輪詢狀態（每 5-10 秒）
   GET /api/v1/loops/12
   Response:
   {
     "loop_id": 12,
     "status": "RUNNING",
     "current_iteration": 2,
     "progress": {
       "current_step": "backtest",
       "step_progress": "250/500",
       "percentage": 50
     }
   }

5. 執行完成後
   Loop 狀態：RUNNING → REVIEWING
   前端檢測到狀態變更，停止輪詢，顯示完成訊息
```

### API 設計變更

#### 啟動迭代（非同步）

```
POST /api/v1/loops/{loop_id}/execute-iteration

Request Body:
{
  "async": true  // 預設 true，前端強制使用非同步模式
}

Response (立即返回):
{
  "loop_id": 12,
  "status": "RUNNING",
  "current_iteration": 2,
  "started_at": "2026-03-27T10:00:00Z",
  "estimated_duration_minutes": 60,
  "message": "迭代已開始執行，請輪詢狀態以追蹤進度"
}
```

#### 查詢狀態（支援進度）

```
GET /api/v1/loops/{loop_id}

Response:
{
  "loop_id": 12,
  "loop_name": "500題測試",
  "vendor_id": 1,
  "status": "RUNNING",
  "current_iteration": 2,
  "max_iterations": 10,
  "current_pass_rate": 0.65,
  "target_pass_rate": 0.85,
  "scenario_ids": [1, 5, 8, ...],

  // 新增：執行進度
  "progress": {
    "current_step": "backtest",          // backtest/analysis/classification/generation/syncing
    "step_name": "執行回測",
    "step_progress": "250/500",          // 當前步驟進度
    "percentage": 50,                    // 整體百分比
    "elapsed_seconds": 1800,             // 已執行時間（秒）
    "estimated_remaining_seconds": 1800  // 預估剩餘時間（秒）
  },

  "created_at": "2026-03-27T09:00:00Z",
  "updated_at": "2026-03-27T10:30:00Z"
}
```

#### 查詢執行日誌（新增）

```
GET /api/v1/loops/{loop_id}/logs?limit=10

Response:
{
  "logs": [
    {
      "id": 145,
      "event_type": "backtest_progress",
      "message": "回測進度：250/500 (50%)",
      "metadata": {
        "completed": 250,
        "total": 500,
        "passed": 150,
        "failed": 100
      },
      "created_at": "2026-03-27T10:30:00Z"
    },
    {
      "event_type": "backtest_started",
      "message": "開始執行回測（500 題）",
      "created_at": "2026-03-27T10:00:00Z"
    }
  ]
}
```

### 前端實作範例

```javascript
// 1. 啟動迭代（非同步）
async function executeIteration(loopId) {
  const response = await fetch(`/api/v1/loops/${loopId}/execute-iteration`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ async: true })
  })

  const data = await response.json()

  // 立即返回，開始輪詢
  console.log('迭代已啟動，開始輪詢狀態...')
  pollLoopStatus(loopId)
}

// 2. 輪詢狀態
function pollLoopStatus(loopId) {
  const pollInterval = 5000 // 每 5 秒輪詢一次

  const intervalId = setInterval(async () => {
    const response = await fetch(`/api/v1/loops/${loopId}`)
    const loop = await response.json()

    // 更新 UI
    updateProgressBar(loop.progress)
    updateStatusText(loop.status, loop.progress)

    // 檢查是否完成
    if (loop.status === 'REVIEWING') {
      clearInterval(intervalId)
      showCompletionMessage('迭代完成！請進行人工審核。')
    } else if (loop.status === 'FAILED') {
      clearInterval(intervalId)
      showErrorMessage('迭代執行失敗，請查看日誌。')
    }
  }, pollInterval)

  // 存儲 intervalId 以便取消
  return intervalId
}

// 3. 更新進度條
function updateProgressBar(progress) {
  if (!progress) return

  document.getElementById('progress-bar').style.width = `${progress.percentage}%`
  document.getElementById('progress-text').textContent =
    `${progress.step_name}: ${progress.step_progress} (${progress.percentage}%)`
  document.getElementById('time-remaining').textContent =
    `預估剩餘時間: ${Math.ceil(progress.estimated_remaining_seconds / 60)} 分鐘`
}
```

### 後端實作範例

```python
# routers/knowledge_completion_loop.py

from fastapi import BackgroundTasks

@router.post("/loops/{loop_id}/execute-iteration")
async def execute_iteration(
    loop_id: int,
    async_mode: bool = True,  # 預設非同步
    background_tasks: BackgroundTasks
):
    """執行下一次迭代（非同步模式）"""

    # 檢查 loop 狀態
    loop = get_loop(loop_id)
    if loop.status != 'RUNNING':
        raise HTTPException(400, f"Loop 狀態必須為 RUNNING，目前為 {loop.status}")

    # 檢查是否已有執行中的迭代
    if is_iteration_running(loop_id):
        raise HTTPException(409, "迭代已在執行中，請等待完成")

    if async_mode:
        # 非同步模式：立即返回，背景執行
        background_tasks.add_task(run_iteration_async, loop_id)

        return {
            "loop_id": loop_id,
            "status": "RUNNING",
            "current_iteration": loop.current_iteration + 1,
            "started_at": datetime.now(),
            "estimated_duration_minutes": estimate_duration(loop.batch_size),
            "message": "迭代已開始執行，請輪詢狀態以追蹤進度"
        }
    else:
        # 同步模式（僅供測試/調試）
        result = await run_iteration_sync(loop_id)
        return result

async def run_iteration_async(loop_id: int):
    """背景執行迭代"""
    try:
        coordinator = get_coordinator(loop_id)

        # 執行迭代，定期更新進度
        await coordinator.execute_iteration_with_progress(
            progress_callback=lambda progress: update_loop_progress(loop_id, progress)
        )

    except Exception as e:
        # 錯誤處理
        update_loop_status(loop_id, 'FAILED')
        log_error(loop_id, str(e))
```

---

## 解決方案 2：WebSocket 即時推送（進階）

### 優勢
- 即時推送進度（無需輪詢）
- 降低伺服器負載
- 更好的用戶體驗

### 劣勢
- 實作複雜度高
- 需要維護 WebSocket 連線
- 需要處理斷線重連

### 實作概要

```python
# WebSocket 端點
@router.websocket("/ws/loops/{loop_id}")
async def loop_progress_ws(websocket: WebSocket, loop_id: int):
    await websocket.accept()

    try:
        # 訂閱 loop 進度更新
        async for progress in subscribe_loop_progress(loop_id):
            await websocket.send_json(progress)

    except WebSocketDisconnect:
        pass
```

```javascript
// 前端訂閱
const ws = new WebSocket(`ws://localhost:8100/ws/loops/${loopId}`)

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data)
  updateProgressBar(progress)
}
```

---

## 解決方案 3：命令列執行 + 前端查看（當前可用）

### 適用場景
- 暫時沒有實作非同步 API
- 快速驗證測試
- 開發/調試階段

### 執行方式

```bash
# 後台執行腳本
./run_500_verification.sh > /tmp/loop_execution.log 2>&1 &

# 記錄 PID
echo $! > /tmp/loop_pid

# 前端定期檢查資料庫狀態
# 查看日誌追蹤進度
```

**優點**：
- 無需改動 API
- 可立即使用
- 穩定可靠

**缺點**：
- 用戶體驗較差（需切換終端機）
- 無法從前端控制（暫停/取消）
- 不適合正式環境

---

## 建議實作優先級

### P0 - 立即可用（測試階段）
✅ **使用命令列 + 前端審核模式**
- 執行：`./run_500_verification.sh`
- 審核：前端界面
- 狀態查詢：`./quick_verification.sh`

### P1 - 短期目標（1-2 週）
🎯 **實作非同步執行 + 狀態輪詢**
- 修改 API 為非同步模式
- 新增進度查詢 API
- 前端實作輪詢機制
- 顯示進度條與預估時間

### P2 - 長期目標（可選）
⭐ **實作 WebSocket 即時推送**
- WebSocket 端點
- 即時進度推送
- 斷線重連機制

---

## requirements.md 需要補充的內容

### Section 11.1 - API 規格

需要補充：

1. **非同步執行模式**
   - `POST /api/v1/loops/{loop_id}/execute-iteration` 應支援非同步模式
   - 預設為非同步（`async: true`）
   - 立即返回狀態，背景執行

2. **進度追蹤**
   - `GET /api/v1/loops/{loop_id}` 應包含 `progress` 欄位
   - 顯示當前步驟、進度百分比、預估剩餘時間

3. **執行日誌查詢**
   - 新增 `GET /api/v1/loops/{loop_id}/logs` 端點
   - 支援即時查看執行日誌

4. **並發控制**
   - 同一 loop 不應同時執行多個迭代
   - API 應返回 409 Conflict 錯誤

### Section 15 - 非功能性需求

需要補充：

1. **前端 Timeout 處理**
   - 所有長時間執行的操作（>60 秒）必須使用非同步模式
   - 前端必須實作狀態輪詢機制
   - 建議輪詢間隔：5-10 秒

2. **進度可見性**
   - 系統應提供執行進度資訊
   - 包含當前步驟、完成百分比、預估剩餘時間

3. **用戶體驗**
   - 執行中應顯示進度條
   - 提供取消功能（任何時候可中斷）
   - 執行失敗應顯示清楚的錯誤訊息

---

## 總結

**當前狀況**：
- ❌ requirements.md 的 API 設計是同步模式
- ❌ 50 題以上的測試會遇到 timeout 問題
- ✅ 命令列腳本可以正常執行（繞過 timeout）

**建議**：
1. **立即**：使用命令列腳本進行測試（暫時方案）
2. **短期**：補充 requirements.md，加入非同步執行模式設計
3. **中期**：實作非同步 API + 前端輪詢
4. **長期**：考慮 WebSocket 即時推送（可選）

**是否需要更新 requirements.md？**
- ✅ **是的，必須更新**
- 補充非同步執行模式的完整設計
- 明確說明 timeout 風險與解決方案
- 提供前端輪詢機制的規範
