# BacktestView.vue 現有頁面盤查與分析報告

> **任務 11.1**：完整盤查現有 BacktestView.vue 的功能、程式碼結構與不足之處
>
> **文件建立時間**：2026-03-27
>
> **分析對象**：`knowledge-admin/frontend/src/views/BacktestView.vue` (2695 行)

---

## 執行摘要

BacktestView.vue 是一個功能完善的回測管理介面，已實作回測執行、結果查詢、統計顯示等核心功能。然而，**尚未整合知識完善迴圈（Knowledge Completion Loop）的 8 步驟流程**，缺少知識生成、審核、迭代管理等關鍵功能。

**主要發現**：
- ✅ 回測執行功能完整（Smart Batch 模式、分批執行、連續執行）
- ✅ 回測結果查詢與顯示完善（歷史記錄、分頁、詳情查看）
- ✅ 統計卡片與品質評估完整呈現
- ❌ **缺少知識完善迴圈管理功能**（迴圈生命週期、迭代執行、狀態追蹤）
- ❌ **缺少知識審核介面**（待審核知識查詢、單一審核、批量審核）
- ❌ **缺少驗證回測功能**（可選功能，快速驗證知識改善效果）

---

## 一、程式碼結構統計

### 1.1 整體統計

| 項目 | 行數 | 佔比 |
|------|------|------|
| **總行數** | 2695 | 100% |
| **Template** | 523 行 (1-523) | 19.4% |
| **Script** | 685 行 (524-1208) | 25.4% |
| **Style** | 1487 行 (1209-2695) | 55.2% |

### 1.2 Script 分佈

| 區塊 | 行號 | 行數 |
|------|------|------|
| **Imports & Config** | 525-530 | 6 |
| **Component Definition** | 531-535 | 5 |
| **data()** | 536-574 | 39 |
| **computed** | 575-579 | 5 |
| **Lifecycle Hooks** | 580-601 | 22 |
| **methods** | 602-1205 | 604 |

---

## 二、功能清單與程式碼引用

### 2.1 回測執行功能

#### 2.1.1 Smart Batch 模式（智能分批）

**功能描述**：支援設定批量大小、狀態、來源、難度等篩選條件，執行分批回測。

**相關程式碼**：
- UI 控制面板：L104-164（Smart Batch Toggle & Controls）
- 批次資訊更新：`updateBatchInfo()` L852-870
- 執行單批回測：`runSmartBatch()` L872-926
- 連續分批執行：`runContinuousBatch()` L928-998

**API 端點**：
- `POST /api/backtest/run/smart-batch` - 執行單批回測
- `POST /api/backtest/run/continuous-batch` - 連續分批執行
- `POST /api/test-scenarios/count` - 統計符合條件的題目數量

**資料模型**：
```javascript
// data() L563-572
enableSmartBatch: false,
smartBatchConfig: {
  batch_size: 200,           // 批量大小
  quality_mode: 'hybrid',    // 品質模式
  status: '',                // 題目狀態篩選
  source: '',                // 題目來源篩選
  difficulty: ''             // 難度篩選
},
batchInfo: null              // 批次資訊
```

---

#### 2.1.2 回測執行狀態監控

**功能描述**：執行回測後自動輪詢狀態，顯示進度條與預估時間，支援中斷與停止監控。

**相關程式碼**：
- 狀態檢查：`checkBacktestStatus()` L1000-1012
- 啟動監控：`startStatusMonitoring()` L1014-1080
- 中斷回測：`cancelBacktest()` L1082-1113
- 強制停止監控：`forceStopMonitoring()` L1115-1135
- UI 顯示：L198-221（執行狀態提示 & 進度條）

**監控機制**：
- 輪詢間隔：5 秒（L1020）
- 進度計算：已執行/總測試數 × 100%（L1032）
- 預估剩餘時間：(剩餘題數 × 平均每題時間) / 60（L1038-1041）

**資料模型**：
```javascript
// data() L557-562
isRunning: false,            // 是否正在執行
lastRunTime: null,           // 最後執行時間
statusCheckInterval: null,   // 輪詢定時器
runningProgress: {           // 執行進度（動態更新）
  executed_scenarios: 0,
  total_scenarios: 0,
  progress_pct: 0,
  elapsed: '0分0秒',
  estimated_remaining: '約0分鐘',
  total_batches: 0,          // 連續分批時顯示
  completed_batches: 0
}
```

---

### 2.2 回測結果查詢與顯示

#### 2.2.1 歷史記錄管理

**功能描述**：載入回測執行記錄列表，支援選擇特定記錄查看詳細結果。

**相關程式碼**：
- 載入記錄列表：`loadBacktestRuns()` L603-613
- 記錄選擇器：L67-75（回測記錄下拉選單）
- 記錄切換：`onRunSelected()` L615-619
- 自動選擇最新記錄：L584-588（mounted hook）

**API 端點**：
- `GET /api/backtest/runs?limit=20&offset=0` - 取得歷史記錄列表

**資料模型**：
```javascript
// data() L560-561
backtestRuns: [],            // 歷史回測執行記錄列表
selectedRunId: null,         // 當前選擇的執行 ID
```

**記錄格式**（後端提供）：
```javascript
{
  id: 123,
  started_at: '2026-03-27T10:00:00Z',
  quality_mode: 'detailed',
  executed_scenarios: 200,
  total_scenarios: 200,
  pass_rate: 85.5,
  duration_seconds: 120
}
```

---

#### 2.2.2 測試結果分頁查詢

**功能描述**：分頁載入測試結果，支援狀態篩選（全部/失敗/通過）。

**相關程式碼**：
- 載入結果：`loadResults()` L621-663
- 分頁控制：L290-314（分頁按鈕 & 每頁筆數選擇）
- 上一頁：`previousPage()` L675-680
- 下一頁：`nextPage()` L682-687
- 改變每頁筆數：`changePageSize()` L689-692
- 當前頁碼計算：`currentPage()` computed L576-578

**API 端點**：
- `GET /api/backtest/runs/{run_id}/results?status_filter=all&limit=50&offset=0` - 取得測試結果

**資料模型**：
```javascript
// data() L539-552
results: [],                 // 當前頁結果
total: 0,                    // 總結果數
pagination: {
  limit: 50,                 // 每頁筆數
  offset: 0                  // 偏移量
},
statusFilter: 'all',         // 狀態篩選（all/failed/passed）
```

---

#### 2.2.3 測試詳情 Modal

**功能描述**：點擊「詳情」按鈕彈出 Modal，顯示完整測試資訊、信心度計算細節、知識來源、優化建議。

**相關程式碼**：
- Modal UI：L323-507（詳情 Modal）
- 顯示詳情：`showDetail(result)` L694-697
- 關閉 Modal：`closeDetailModal()` L699-702
- 優化知識：`optimizeKnowledge(result)` L708-760
- 優化按鈕文字：`getOptimizeButtonText(result)` L762-778

**詳情內容包含**：
1. **測試資訊**（L329-364）：ID、狀態、信心度分數、信心等級、難度
2. **問題與答案**（L366-377）：測試問題、系統回答（含表單標記）
3. **信心度計算詳情**（L379-458）：
   - 最高文檔相似度（權重 70%）
   - 檢索文檔數量（權重 20%）
   - 關鍵字匹配率（權重 10%）
   - 計算公式說明
   - 通過/失敗原因
4. **知識來源**（L460-488）：來源摘要、知識 ID 連結
5. **優化建議**（L490-496）：系統生成的優化提示

**優化知識智能導向**（L708-760）：
- **無知識 OR 相關性 < 5.0 OR 完整性 < 5.0** → 新增知識（`/knowledge?action=create&question=...`）
- **多個知識來源** → 批量查詢（`/knowledge?ids=1,2,3&context=...`）
- **單個知識來源** → 直接編輯（`/knowledge?ids=1&edit=true`）

---

### 2.3 統計與報表

#### 2.3.1 統計卡片

**功能描述**：顯示回測整體統計（總測試數、通過測試、失敗測試、通過率、平均分數）。

**相關程式碼**：
- UI 顯示：L8-30（統計卡片）
- 資料來源：`statistics` 來自 `loadResults()` 回應（L644）

**資料模型**：
```javascript
// data() L540
statistics: {
  total_tests: 200,
  passed_tests: 170,
  failed_tests: 30,
  pass_rate: 85.0,
  avg_score: 0.78
}
```

---

#### 2.3.2 品質評估統計卡片

**功能描述**：顯示 LLM 品質評估統計（相關性、完整性、準確性、意圖匹配、綜合評分）。

**相關程式碼**：
- UI 顯示：L32-62（品質評估統計卡片）
- 品質評級：`getQualityRating(score)` L845-850
- 分數格式化：`formatQualityScore(score)` L825-836
- CSS 樣式類別：`getQualityClass(score)` L817-823

**資料模型**：
```javascript
// statistics.quality（從 API 回應）
statistics: {
  quality: {
    count: 150,                      // 有品質評估的測試數
    avg_relevance: 8.5,              // 平均相關性
    avg_completeness: 7.8,           // 平均完整性
    avg_accuracy: 8.2,               // 平均準確性
    avg_intent_match: 8.0,           // 平均意圖匹配
    avg_quality_overall: 8.1         // 綜合評分
  }
}
```

**品質評級規則**（L845-850）：
- ≥ 8.0：🎉 優秀
- ≥ 7.0：✅ 良好
- ≥ 6.0：⚠️ 中等
- < 6.0：❌ 需改善

---

#### 2.3.3 摘要報告

**功能描述**：點擊「查看摘要」按鈕彈出 Modal，顯示文字摘要報告。

**相關程式碼**：
- 顯示摘要：`showSummary()` L665-673
- Modal UI：L509-520（摘要 Modal）
- 關閉 Modal：`closeSummaryModal()` L704-706

**API 端點**：
- `GET /api/backtest/summary` - 取得摘要報告

---

### 2.4 UI/UX 功能

#### 2.4.1 通知系統

**功能描述**：顯示操作通知（info/success/warning/error），3 秒後自動消失。

**相關程式碼**：
- 顯示通知：`showNotification(type, title, message)` L780-803
- 調用位置：`optimizeKnowledge()` L759（優化知識完成後）

**通知樣式**：
- info: ℹ️
- success: ✅
- warning: ⚠️
- error: ❌

---

#### 2.4.2 說明面板

**功能描述**：顯示回測功能說明，使用可摺疊 InfoPanel 元件。

**相關程式碼**：
- UI 顯示：L5-6（說明區塊）
- 元件引入：`import InfoPanel from '@/components/InfoPanel.vue'` L526
- 說明文字配置：`helpTexts` 來自 `@/config/help-texts.js` L527

---

#### 2.4.3 載入狀態與錯誤處理

**功能描述**：顯示載入中狀態、錯誤訊息、空狀態提示。

**相關程式碼**：
- 載入中：L223-226
- 錯誤訊息：L228-232
- 空狀態：L317-321

**資料模型**：
```javascript
// data() L542-543
loading: false,              // 載入中狀態
error: null,                 // 錯誤訊息
```

---

## 三、元件結構分析

### 3.1 Data 屬性清單（39 行）

| 屬性 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `helpTexts` | Object | 引入 | 說明文字配置 |
| `results` | Array | `[]` | 當前頁測試結果 |
| `statistics` | Object | `null` | 統計資訊 |
| `total` | Number | `0` | 總結果數 |
| `loading` | Boolean | `false` | 載入中狀態 |
| `error` | String | `null` | 錯誤訊息 |
| `statusFilter` | String | `'all'` | 狀態篩選 |
| `backtestConfig.quality_mode` | String | `'detailed'` | 品質模式 |
| `backtestConfig.vendor_id` | Number | `2` | 測試業者 ID |
| `pagination.limit` | Number | `50` | 每頁筆數 |
| `pagination.offset` | Number | `0` | 偏移量 |
| `showDetailModal` | Boolean | `false` | 顯示詳情 Modal |
| `selectedResult` | Object | `null` | 選擇的測試結果 |
| `showSummaryModal` | Boolean | `false` | 顯示摘要 Modal |
| `summaryText` | String | `''` | 摘要文字 |
| `isRunning` | Boolean | `false` | 是否正在執行 |
| `lastRunTime` | String | `null` | 最後執行時間 |
| `statusCheckInterval` | Object | `null` | 輪詢定時器 |
| `backtestRuns` | Array | `[]` | 歷史記錄列表 |
| `selectedRunId` | Number | `null` | 選擇的執行 ID |
| `runningProgress` | Object | `null` | 執行進度資訊 |
| `enableSmartBatch` | Boolean | `false` | 啟用智能分批 |
| `smartBatchConfig.batch_size` | Number | `200` | 批量大小 |
| `smartBatchConfig.quality_mode` | String | `'hybrid'` | 品質模式 |
| `smartBatchConfig.status` | String | `''` | 狀態篩選 |
| `smartBatchConfig.source` | String | `''` | 來源篩選 |
| `smartBatchConfig.difficulty` | String | `''` | 難度篩選 |
| `batchInfo` | Object | `null` | 批次資訊 |

---

### 3.2 Computed 屬性清單（1 個）

| 屬性 | 說明 | 計算邏輯 |
|------|------|---------|
| `currentPage` | 當前頁碼 | `Math.floor(pagination.offset / pagination.limit) + 1` |

---

### 3.3 Methods 方法清單（30+ 個）

#### 回測執行相關（4 個）

| 方法 | 行號 | 說明 |
|------|------|------|
| `runSmartBatch()` | L872-926 | 執行單批回測 |
| `runContinuousBatch()` | L928-998 | 連續分批執行全部 |
| `cancelBacktest()` | L1082-1113 | 中斷回測 |
| `forceStopMonitoring()` | L1115-1135 | 停止監控 |

#### 狀態監控相關（2 個）

| 方法 | 行號 | 說明 |
|------|------|------|
| `checkBacktestStatus()` | L1000-1012 | 檢查回測狀態 |
| `startStatusMonitoring()` | L1014-1080 | 啟動狀態監控（5 秒輪詢） |

#### 資料載入相關（4 個）

| 方法 | 行號 | 說明 |
|------|------|------|
| `loadBacktestRuns()` | L603-613 | 載入歷史記錄列表 |
| `loadResults()` | L621-663 | 載入測試結果 |
| `showSummary()` | L665-673 | 顯示摘要報告 |
| `updateBatchInfo()` | L852-870 | 更新批次資訊 |

#### 分頁控制相關（4 個）

| 方法 | 行號 | 說明 |
|------|------|------|
| `previousPage()` | L675-680 | 上一頁 |
| `nextPage()` | L682-687 | 下一頁 |
| `changePageSize()` | L689-692 | 改變每頁筆數 |
| `onRunSelected()` | L615-619 | 切換回測記錄 |

#### Modal 控制相關（5 個）

| 方法 | 行號 | 說明 |
|------|------|------|
| `showDetail(result)` | L694-697 | 顯示詳情 Modal |
| `closeDetailModal()` | L699-702 | 關閉詳情 Modal |
| `closeSummaryModal()` | L704-706 | 關閉摘要 Modal |
| `optimizeKnowledge(result)` | L708-760 | 優化知識（導向新增/編輯） |
| `getOptimizeButtonText(result)` | L762-778 | 取得優化按鈕文字 |

#### UI/UX 輔助方法（11 個）

| 方法 | 行號 | 說明 |
|------|------|------|
| `showNotification(type, title, message)` | L780-803 | 顯示通知 |
| `getScoreClass(score)` | L805-809 | 取得分數 CSS 類別 |
| `getConfidenceClass(confidence)` | L811-815 | 取得信心度 CSS 類別 |
| `getQualityClass(score)` | L817-823 | 取得品質 CSS 類別 |
| `formatQualityScore(score)` | L825-836 | 格式化品質分數 |
| `parseSourceIds(sourceIdsStr)` | L838-843 | 解析來源 ID 字串 |
| `getQualityRating(score)` | L845-850 | 取得品質評級 |
| `formatRunTime(isoString)` | L1137-1154 | 格式化執行時間（相對時間） |
| `formatRunDate(isoString)` | L1156-1165 | 格式化執行日期 |
| `formatConfidenceScore(score)` | L1167-1172 | 格式化信心度分數 |
| `formatConfidenceLevel(level)` | L1174-1181 | 格式化信心等級 |
| `formatFloat(value)` | L1183-1188 | 格式化浮點數 |
| `getSourceIdArray(sourceIds)` | L1190-1193 | 取得來源 ID 陣列 |
| `getSourceCount(sourceIds)` | L1195-1197 | 取得來源數量 |
| `getConfidenceScoreClass(score)` | L1199-1204 | 取得信心度分數 CSS 類別 |

---

### 3.4 Lifecycle Hooks（2 個）

| Hook | 行號 | 說明 |
|------|------|------|
| `mounted()` | L580-596 | 載入歷史記錄、自動選擇最新記錄、載入結果、預載入批次資訊 |
| `beforeUnmount()` | L597-601 | 清除定時器 |

---

## 四、API 調用分析

### 4.1 當前使用的 API 端點

| 端點 | 方法 | 說明 | 使用位置 |
|------|------|------|---------|
| `/api/backtest/runs` | GET | 取得歷史記錄列表 | `loadBacktestRuns()` L605 |
| `/api/backtest/runs/{run_id}/results` | GET | 取得特定執行的測試結果 | `loadResults()` L640 |
| `/api/backtest/summary` | GET | 取得摘要報告 | `showSummary()` L667 |
| `/api/backtest/status` | GET | 檢查回測狀態 | `checkBacktestStatus()` L1002, `startStatusMonitoring()` L1022 |
| `/api/backtest/cancel` | POST | 中斷回測 | `cancelBacktest()` L1085 |
| `/api/test-scenarios/count` | POST | 統計符合條件的題目數量 | `updateBatchInfo()` L860 |
| `/api/backtest/run/smart-batch` | POST | 執行單批回測 | `runSmartBatch()` L904 |
| `/api/backtest/run/continuous-batch` | POST | 連續分批執行 | `runContinuousBatch()` L974 |

### 4.2 缺少的 API 端點（對應知識完善迴圈 8 步驟）

根據 `design.md` 第 1030-1053 行的 API 端點清單，**以下端點尚未整合**：

#### 迴圈管理 API (`/api/v1/loops`)

| 端點 | 方法 | 說明 | 對應需求 |
|------|------|------|---------|
| `/api/v1/loops/start` | POST | 啟動新迴圈 | 需求 10.1, 10.4 |
| `/api/v1/loops/{loop_id}/execute-iteration` | POST | 執行迭代 | 需求 10.2 |
| `/api/v1/loops/{loop_id}` | GET | 查詢迴圈狀態 | 需求 10.2 |
| `/api/v1/loops/{loop_id}/validate` | POST | 驗證效果回測（可選） | 需求 9 |
| `/api/v1/loops/{loop_id}/complete-batch` | POST | 完成批次 | 需求 10.4 |
| `/api/v1/loops/{loop_id}/pause` | POST | 暫停迴圈 | 需求 10.5 |
| `/api/v1/loops/{loop_id}/resume` | POST | 恢復迴圈 | 需求 10.5 |
| `/api/v1/loops/{loop_id}/cancel` | POST | 取消迴圈 | 需求 10.5 |
| `/api/v1/loops/start-next-batch` | POST | 啟動下一批次 | 需求 10.4 |
| `/api/v1/loops` | GET | 列出迴圈（分頁） | 需求 10.2 |

#### 知識審核 API (`/api/v1/loop-knowledge`)

| 端點 | 方法 | 說明 | 對應需求 |
|------|------|------|---------|
| `/api/v1/loop-knowledge/pending` | GET | 查詢待審核知識 | 需求 8.1 |
| `/api/v1/loop-knowledge/{knowledge_id}/review` | POST | 單一知識審核 | 需求 8.2 |
| `/api/v1/loop-knowledge/batch-review` | POST | 批量知識審核 | 需求 8.3 |

---

## 五、不足功能清單

### 5.1 缺少的核心功能

根據 `tasks.md` 第 1214-1289 行的需求描述，**以下功能尚未實作**：

#### 1. **迴圈管理介面**（對應知識完善迴圈 8 步驟流程）

**缺失功能**：
- ❌ 啟動新迴圈（設定迴圈名稱、批量大小、最大迭代次數、目標通過率）
- ❌ 迴圈列表顯示（包含迴圈狀態、當前迭代次數、通過率、建立時間）
- ❌ 迴圈詳情頁（顯示固定測試集、迭代歷史、統計圖表）
- ❌ 執行迭代按鈕（觸發完整的 8 步驟流程）
- ❌ 迭代進度監控（顯示當前步驟：回測 → 分析 → 分類 → 聚類 → 生成 → 審核）
- ❌ 暫停、恢復、取消迴圈操作
- ❌ 完成批次操作（標記迴圈為 COMPLETED）
- ❌ 啟動下一批次（自動選取未處理的測試情境）

**對應 API**：`/api/v1/loops/*`

---

#### 2. **知識審核中心**（對應第 7 步：人工審核）

**缺失功能**：
- ❌ 待審核知識列表（支援篩選：迴圈 ID、業者、知識類型、狀態）
- ❌ 知識審核 UI（顯示問題、答案、知識類型、SOP 配置、相似知識警告）
- ❌ 單一審核功能（批准/拒絕，支援修改內容與備註）
- ❌ 批量審核功能（一次審核 10-50 個知識項目）
- ❌ 重複檢測警告顯示（⚠️ 檢測到相似知識：XXX（相似度 93%））
- ❌ 審核後立即同步到正式庫（`knowledge_base` / `vendor_sop_items`）

**對應 API**：`/api/v1/loop-knowledge/*`

---

#### 3. **驗證回測功能**（可選功能，對應需求 9）

**缺失功能**：
- ❌ 驗證回測觸發按鈕（在迴圈詳情頁）
- ❌ 驗證範圍選擇（failed_only / all / failed_plus_sample）
- ❌ 抽樣比例設定（failed_plus_sample 模式使用）
- ❌ 驗證結果顯示（通過率、改善幅度、Regression 檢測）
- ❌ Regression 警告（檢測到 X 個原本通過的案例現在失敗）
- ❌ 標記知識需要改善（驗證失敗時）

**對應 API**：`/api/v1/loops/{loop_id}/validate`

---

#### 4. **迴圈執行狀態視覺化**（對應需求 10.2）

**缺失功能**：
- ❌ 8 步驟流程進度條（顯示當前步驟、已完成步驟）
- ❌ 每步驟詳細資訊（執行時間、結果摘要）
- ❌ 迭代歷史時間軸（顯示歷次迭代的通過率變化）
- ❌ 成本追蹤顯示（已使用預算、預算上限）

**對應設計**：`design.md` 第 1119-1169 行（流程 2：非同步執行迭代）

---

### 5.2 功能對應關係

| 知識完善迴圈步驟 | 現有功能 | 缺失功能 |
|------------------|---------|---------|
| 第 1 步：執行回測 | ✅ Smart Batch 回測執行 | ❌ 迴圈內嵌的固定測試集回測 |
| 第 2 步：分析失敗案例 | ⚠️ 僅顯示失敗原因 | ❌ 缺口分析結果顯示 |
| 第 3 步：智能分類 (OpenAI) | ❌ 無 | ❌ 分類結果顯示（sop_knowledge/form_fill/system_config/api_query） |
| 第 4 步：按類別分離 | ❌ 無 | ❌ 分類統計顯示 |
| 第 5 步：分別聚類 | ❌ 無 | ❌ 聚類結果顯示（每個聚類的問題列表） |
| 第 6 步：生成知識 | ⚠️ 僅手動新增/編輯 | ❌ 自動生成知識（SOP + 一般知識） |
| 第 7 步：人工審核 | ⚠️ 僅在知識管理頁面審核 | ❌ 迴圈內嵌的批量審核介面 |
| 第 8 步：檢查通過率並決定迭代 | ⚠️ 僅手動觸發新回測 | ❌ 自動判斷是否繼續迭代 |

---

## 六、重構建議

### 6.1 架構重構建議

#### 6.1.1 採用 Tab 架構（推薦）

**問題**：
- 當前 BacktestView.vue 將所有功能塞在單一頁面，程式碼行數達 2695 行，難以維護
- 回測執行與知識完善迴圈是兩個不同的工作流程，混在一起容易混淆

**建議**：
將 BacktestView.vue 拆分為 **Tab 架構**，包含 3 個 Tab：

```
┌─────────────────────────────────────────────────┐
│ 🧪 回測結果與優化                                 │
├─────────────────────────────────────────────────┤
│ [回測執行] [知識完善迴圈] [審核中心]               │
│                                                  │
│ Tab 1: 回測執行                                   │
│   - 保留現有回測執行功能（Smart Batch、連續執行）    │
│   - 回測結果查詢與顯示                             │
│   - 統計卡片與品質評估                             │
│                                                  │
│ Tab 2: 知識完善迴圈                               │
│   - 迴圈列表與建立                                 │
│   - 迴圈詳情與迭代執行                             │
│   - 8 步驟流程進度顯示                             │
│   - 驗證回測（可選）                               │
│                                                  │
│ Tab 3: 審核中心                                   │
│   - 待審核知識列表（支援篩選）                      │
│   - 單一審核 / 批量審核                            │
│   - 重複檢測警告                                   │
│   - 審核歷史記錄                                   │
└─────────────────────────────────────────────────┘
```

**實作方式**：
- 使用 Vue Router 的子路由（推薦）：
  ```javascript
  {
    path: '/backtest',
    component: BacktestView,
    children: [
      { path: '', redirect: '/backtest/execution' },
      { path: 'execution', component: BacktestExecutionTab },
      { path: 'loops', component: KnowledgeCompletionLoopTab },
      { path: 'review', component: ReviewCenterTab }
    ]
  }
  ```
- 或使用 Vue 動態元件（`<component :is="currentTab" />`）

**優點**：
- ✅ 清晰的功能分離，降低認知負擔
- ✅ 每個 Tab 獨立開發與測試
- ✅ 減少單一檔案行數（預估每個 Tab 800-1000 行）
- ✅ 更好的程式碼維護性

---

#### 6.1.2 元件拆分建議

**問題**：
- 當前所有功能都在 BacktestView.vue 中，難以重用與測試
- Modal、統計卡片、進度條等 UI 元件混在主邏輯中

**建議**：
將以下功能拆分為獨立元件：

```
components/
├── backtest/
│   ├── BacktestExecutionPanel.vue        # 回測執行面板（Smart Batch）
│   ├── BacktestResultsTable.vue          # 回測結果表格
│   ├── BacktestStatisticsCards.vue       # 統計卡片
│   ├── BacktestDetailModal.vue           # 測試詳情 Modal
│   ├── BacktestSummaryModal.vue          # 摘要報告 Modal
│   ├── BacktestProgressBar.vue           # 進度條
│   └── BacktestRunSelector.vue           # 回測記錄選擇器
│
├── knowledge-loop/
│   ├── LoopListTable.vue                 # 迴圈列表
│   ├── LoopCreateForm.vue                # 建立迴圈表單
│   ├── LoopDetailCard.vue                # 迴圈詳情卡片
│   ├── LoopIterationHistory.vue          # 迭代歷史時間軸
│   ├── LoopProgressSteps.vue             # 8 步驟流程進度
│   ├── LoopValidationModal.vue           # 驗證回測 Modal
│   └── LoopCostTracker.vue               # 成本追蹤器
│
└── review/
    ├── PendingKnowledgeTable.vue         # 待審核知識表格
    ├── KnowledgeReviewModal.vue          # 知識審核 Modal
    ├── BatchReviewPanel.vue              # 批量審核面板
    ├── DuplicateDetectionAlert.vue       # 重複檢測警告
    └── ReviewHistoryTimeline.vue         # 審核歷史時間軸
```

**優點**：
- ✅ 元件可重用（例如 BacktestStatisticsCards 可用於多個頁面）
- ✅ 單一職責原則，更易測試
- ✅ 減少主元件複雜度

---

### 6.2 狀態管理建議

#### 6.2.1 引入 Vuex/Pinia（推薦）

**問題**：
- 當前所有狀態都在元件 `data()` 中管理，跨元件共享困難
- 回測狀態、迴圈狀態、審核狀態需要在多個元件間共享

**建議**：
引入 **Pinia**（Vue 3 官方推薦）管理全域狀態：

```javascript
// stores/backtest.js
export const useBacktestStore = defineStore('backtest', {
  state: () => ({
    runs: [],              // 歷史記錄列表
    selectedRunId: null,   // 當前選擇的執行 ID
    isRunning: false,      // 是否正在執行
    progress: null         // 執行進度
  }),
  actions: {
    async loadRuns() { /* ... */ },
    async loadResults(runId) { /* ... */ },
    startMonitoring() { /* ... */ },
    stopMonitoring() { /* ... */ }
  }
})

// stores/knowledgeLoop.js
export const useKnowledgeLoopStore = defineStore('knowledgeLoop', {
  state: () => ({
    loops: [],             // 迴圈列表
    currentLoop: null,     // 當前迴圈
    iterationHistory: []   // 迭代歷史
  }),
  actions: {
    async startLoop(config) { /* ... */ },
    async executeIteration(loopId) { /* ... */ },
    async loadLoopStatus(loopId) { /* ... */ }
  }
})

// stores/review.js
export const useReviewStore = defineStore('review', {
  state: () => ({
    pendingKnowledge: [],  // 待審核知識列表
    selectedItems: []      // 已選擇的項目
  }),
  actions: {
    async loadPendingKnowledge(filters) { /* ... */ },
    async reviewKnowledge(knowledgeId, action) { /* ... */ },
    async batchReview(knowledgeIds, action) { /* ... */ }
  }
})
```

**優點**：
- ✅ 集中管理狀態，避免 prop drilling
- ✅ 狀態持久化（可使用 `pinia-plugin-persistedstate`）
- ✅ 更好的開發者工具支援（Vue DevTools）

---

### 6.3 API 管理建議

**問題**：
- 當前 API 調用散落在各個方法中，難以統一管理
- 缺少統一的錯誤處理與重試機制

**建議**：
建立 API 管理模組：

```javascript
// api/backtest.js
import axios from 'axios'

const API_BASE = '/api'

export const backtestAPI = {
  getRuns: (params) => axios.get(`${API_BASE}/backtest/runs`, { params }),
  getResults: (runId, params) => axios.get(`${API_BASE}/backtest/runs/${runId}/results`, { params }),
  getStatus: () => axios.get(`${API_BASE}/backtest/status`),
  getSummary: () => axios.get(`${API_BASE}/backtest/summary`),
  cancel: () => axios.post(`${API_BASE}/backtest/cancel`),
  runSmartBatch: (data) => axios.post(`${API_BASE}/backtest/run/smart-batch`, data),
  runContinuousBatch: (data) => axios.post(`${API_BASE}/backtest/run/continuous-batch`, data),
  countScenarios: (filters) => axios.post(`${API_BASE}/test-scenarios/count`, filters)
}

// api/knowledgeLoop.js
export const knowledgeLoopAPI = {
  startLoop: (config) => axios.post(`${API_BASE}/v1/loops/start`, config),
  executeIteration: (loopId, data) => axios.post(`${API_BASE}/v1/loops/${loopId}/execute-iteration`, data),
  getLoopStatus: (loopId) => axios.get(`${API_BASE}/v1/loops/${loopId}`),
  validateLoop: (loopId, data) => axios.post(`${API_BASE}/v1/loops/${loopId}/validate`, data),
  completeBatch: (loopId) => axios.post(`${API_BASE}/v1/loops/${loopId}/complete-batch`),
  pauseLoop: (loopId) => axios.post(`${API_BASE}/v1/loops/${loopId}/pause`),
  resumeLoop: (loopId) => axios.post(`${API_BASE}/v1/loops/${loopId}/resume`),
  cancelLoop: (loopId) => axios.post(`${API_BASE}/v1/loops/${loopId}/cancel`),
  startNextBatch: (config) => axios.post(`${API_BASE}/v1/loops/start-next-batch`, config),
  getLoops: (params) => axios.get(`${API_BASE}/v1/loops`, { params })
}

// api/review.js
export const reviewAPI = {
  getPendingKnowledge: (params) => axios.get(`${API_BASE}/v1/loop-knowledge/pending`, { params }),
  reviewKnowledge: (knowledgeId, data) => axios.post(`${API_BASE}/v1/loop-knowledge/${knowledgeId}/review`, data),
  batchReview: (data) => axios.post(`${API_BASE}/v1/loop-knowledge/batch-review`, data)
}
```

**優點**：
- ✅ 統一 API 管理，易於維護
- ✅ 可統一處理錯誤（使用 axios interceptors）
- ✅ 易於測試（可 mock API 模組）

---

### 6.4 效能優化建議

#### 6.4.1 虛擬滾動（針對大量結果）

**問題**：
- 當回測結果超過 1000 筆時，表格渲染可能卡頓

**建議**：
使用虛擬滾動庫（如 `vue-virtual-scroller`）：

```vue
<RecycleScroller
  :items="results"
  :item-size="80"
  key-field="test_id"
  v-slot="{ item }"
>
  <BacktestResultRow :result="item" />
</RecycleScroller>
```

---

#### 6.4.2 防抖與節流

**問題**：
- 狀態輪詢每 5 秒執行一次，可能造成不必要的請求

**建議**：
- 使用 `lodash` 的 `throttle` 限制輪詢頻率
- 當頁面不可見時暫停輪詢（使用 `document.visibilityState`）

---

## 七、實作優先級建議

根據功能重要性與開發成本，建議以下實作順序：

### Phase 1：基礎架構重構（1-2 週）

- [ ] **1.1** 引入 Pinia 狀態管理
- [ ] **1.2** 建立 API 管理模組（`api/backtest.js`, `api/knowledgeLoop.js`, `api/review.js`）
- [ ] **1.3** 拆分 Tab 架構（3 個 Tab）
- [ ] **1.4** 建立共用元件（統計卡片、進度條、Modal）

### Phase 2：知識完善迴圈管理（2-3 週）

- [ ] **2.1** 迴圈列表與建立介面（Tab 2）
- [ ] **2.2** 迴圈詳情與迭代執行（Tab 2）
- [ ] **2.3** 8 步驟流程進度顯示（Tab 2）
- [ ] **2.4** 迭代歷史時間軸（Tab 2）
- [ ] **2.5** 成本追蹤顯示（Tab 2）

### Phase 3：知識審核中心（1-2 週）

- [ ] **3.1** 待審核知識列表（Tab 3）
- [ ] **3.2** 單一審核 Modal（Tab 3）
- [ ] **3.3** 批量審核面板（Tab 3）
- [ ] **3.4** 重複檢測警告顯示（Tab 3）

### Phase 4：驗證回測功能（可選，1 週）

- [ ] **4.1** 驗證回測觸發按鈕（Tab 2）
- [ ] **4.2** 驗證範圍選擇（Tab 2）
- [ ] **4.3** 驗證結果顯示與 Regression 檢測（Tab 2）

### Phase 5：優化與測試（1 週）

- [ ] **5.1** 虛擬滾動優化
- [ ] **5.2** 防抖與節流優化
- [ ] **5.3** 單元測試（關鍵元件與 Store）
- [ ] **5.4** 端對端測試（關鍵使用者流程）

---

## 八、結論

### 8.1 當前狀態總結

BacktestView.vue 已完成**回測執行與結果查詢的基礎功能**，但**尚未整合知識完善迴圈的 8 步驟流程**。

**優勢**：
- ✅ 回測執行功能完善（Smart Batch、連續執行、進度監控）
- ✅ 回測結果查詢與顯示完整（歷史記錄、分頁、詳情 Modal）
- ✅ 統計與報表完整（統計卡片、品質評估、摘要報告）
- ✅ UI/UX 完善（通知系統、載入狀態、錯誤處理）

**不足**：
- ❌ 缺少迴圈管理介面（啟動、執行迭代、狀態追蹤）
- ❌ 缺少知識審核中心（批量審核、重複檢測警告）
- ❌ 缺少驗證回測功能（可選，快速驗證知識改善效果）
- ❌ 程式碼架構需重構（單一檔案 2695 行，難以維護）

### 8.2 後續行動建議

1. **短期（1-2 週）**：完成基礎架構重構（Pinia、API 管理、Tab 拆分）
2. **中期（2-3 週）**：實作知識完善迴圈管理介面（迴圈列表、迭代執行、進度顯示）
3. **中期（1-2 週）**：實作知識審核中心（待審核列表、批量審核）
4. **長期（可選）**：實作驗證回測功能（驗證範圍、Regression 檢測）
5. **持續**：優化效能（虛擬滾動、防抖節流）與測試覆蓋

---

## 附錄：程式碼行號快速索引

### Template（1-523 行）

- L1-7：標題與說明面板
- L8-30：統計卡片
- L32-62：品質評估統計卡片
- L64-102：工具列（回測記錄選擇器、狀態篩選、品質模式、測試業者）
- L104-164：Smart Batch 控制面板
- L166-196：操作按鈕（執行分批回測、連續執行、重新載入、中斷、停止監控、查看摘要）
- L198-221：執行狀態提示 & 進度條
- L223-232：載入中 & 錯誤訊息
- L234-315：回測結果表格 & 分頁控制
- L317-321：空狀態
- L323-507：詳情 Modal
- L509-520：摘要 Modal

### Script（524-1208 行）

- L525-530：Imports & Config
- L531-535：Component Definition
- L536-574：data()
- L575-579：computed
- L580-596：mounted()
- L597-601：beforeUnmount()
- L602-1205：methods

### Methods 快速索引

- L603-613：`loadBacktestRuns()`
- L615-619：`onRunSelected()`
- L621-663：`loadResults()`
- L665-673：`showSummary()`
- L675-680：`previousPage()`
- L682-687：`nextPage()`
- L689-692：`changePageSize()`
- L694-697：`showDetail()`
- L699-702：`closeDetailModal()`
- L704-706：`closeSummaryModal()`
- L708-760：`optimizeKnowledge()`
- L762-778：`getOptimizeButtonText()`
- L780-803：`showNotification()`
- L805-809：`getScoreClass()`
- L811-815：`getConfidenceClass()`
- L817-823：`getQualityClass()`
- L825-836：`formatQualityScore()`
- L838-843：`parseSourceIds()`
- L845-850：`getQualityRating()`
- L852-870：`updateBatchInfo()`
- L872-926：`runSmartBatch()`
- L928-998：`runContinuousBatch()`
- L1000-1012：`checkBacktestStatus()`
- L1014-1080：`startStatusMonitoring()`
- L1082-1113：`cancelBacktest()`
- L1115-1135：`forceStopMonitoring()`
- L1137-1154：`formatRunTime()`
- L1156-1165：`formatRunDate()`
- L1167-1172：`formatConfidenceScore()`
- L1174-1181：`formatConfidenceLevel()`
- L1183-1188：`formatFloat()`
- L1190-1193：`getSourceIdArray()`
- L1195-1197：`getSourceCount()`
- L1199-1204：`getConfidenceScoreClass()`

### Style（1209-2695 行）

- L1209-1487：CSS 樣式（統計卡片、工具列、按鈕、表格、Modal、通知等）

---

*本報告由 AI 自動生成，包含完整的程式碼分析與重構建議。*
