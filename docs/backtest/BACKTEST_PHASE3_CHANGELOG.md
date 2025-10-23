# Phase 3: 趨勢分析與視覺化 - 更新日誌

## 版本資訊

- **版本：** Phase 3.0
- **日期：** 2025-10-12
- **狀態：** ✅ 已完成

## 概述

Phase 3 為回測系統引入全面的趨勢分析與視覺化功能，幫助團隊更好地監控測試品質、追蹤改進效果、及早發現問題。

## 新功能

### 1. 趨勢分析 API ⭐

#### `/api/backtest/trends/overview` - 趨勢總覽
- **功能：** 獲取指定時間範圍內的回測趨勢數據
- **時間範圍：** 7天 / 30天 / 90天 / 全部
- **返回數據：**
  - 每次回測的數據點（通過率、分數、信心度等）
  - 趨勢摘要統計（最小值、最大值、平均值、最新值）
  - 趨勢方向判斷（improving / declining / stable）

**範例輸出：**
```json
{
  "time_range": "30d",
  "data_points": [
    {
      "run_id": 1,
      "timestamp": "2025-10-12T21:38:44",
      "pass_rate": 50.0,
      "avg_score": 0.45,
      "avg_confidence": 0.85,
      ...
    }
  ],
  "summary": {
    "total_runs": 2,
    "pass_rate": {
      "min": 50.0,
      "max": 100.0,
      "avg": 75.0,
      "latest": 100.0,
      "trend": "improving"
    }
  }
}
```

#### `/api/backtest/trends/comparison` - 統計對比
- **功能：** 對比當前期間與前一期間的統計數據
- **可配置：** 期間天數（預設 7 天）
- **返回數據：**
  - 當前期間統計
  - 前一期間統計
  - 變化率與變化方向

**使用場景：**
- 週度品質回顧：對比本週 vs 上週
- 發布前後對比：對比發布前 7 天 vs 發布後 7 天
- 優化效果驗證：對比優化前後的數據

#### `/api/backtest/trends/alerts` - 品質警報 🚨
- **功能：** 自動檢測品質問題並生成警報
- **可配置閾值：**
  - 通過率閾值（預設 80%）
  - 平均分數閾值（預設 0.6）
  - 平均信心度閾值（預設 0.7）
  - 檢查最近 N 次回測（預設 3 次）

**警報級別：**
- **Critical（嚴重）：** 指標低於閾值 20% 以上
- **Warning（警告）：** 指標低於閾值但差距 < 20%
- **Info（資訊）：** 趨勢下降提示

**範例輸出：**
```json
{
  "alerts": [
    {
      "level": "critical",
      "metric": "pass_rate",
      "run_id": 1,
      "current_value": 50.0,
      "threshold": 80.0,
      "message": "通過率 50.00% 低於閾值 80.0%",
      "recommendation": "建議檢查失敗測試案例,優化知識庫內容或調整意圖設定"
    }
  ],
  "summary": {
    "total_alerts": 2,
    "critical_count": 1,
    "warning_count": 1
  }
}
```

#### `/api/backtest/trends/metrics/{metric_name}` - 特定指標詳情
- **功能：** 深入查看單一指標的趨勢
- **支援指標：**
  - pass_rate（通過率）
  - avg_score（平均分數）
  - avg_confidence（平均信心度）
  - avg_relevance（平均相關性）
  - avg_completeness（平均完整性）
  - avg_accuracy（平均準確性）
  - avg_intent_match（平均意圖匹配）
  - avg_quality_overall（綜合品質）

### 2. 前端視覺化界面 📊

#### 趨勢分析頁面（/backtest/trends）
全新的趨勢分析頁面，提供：

**🚨 警報區塊**
- 即時顯示所有 critical 和 warning 警報
- 卡片式設計，清晰展示：
  - 警報級別與圖標
  - 觸發指標
  - 當前值 vs 閾值
  - 優化建議
  - 觸發時間

**📊 趨勢摘要卡片**
- 通過率、平均分數、平均信心度
- 顯示：
  - 最新值（大字體突出）
  - 值域範圍（最小-最大）
  - 趨勢方向（improving 📈 / declining 📉 / stable ➡️）

**📈 互動式圖表（Chart.js）**
1. **通過率趨勢圖**
   - 折線圖展示通過率變化
   - 綠色主題（成功指標）
   - Y 軸範圍 0-100%

2. **分數與信心度趨勢圖**
   - 雙軸折線圖
   - 藍色：平均分數
   - 橙色：平均信心度
   - Y 軸範圍 0-1

**📊 期間對比分析**
- 卡片式對比：當前期間 vs 前一期間
- 顯示：
  - 回測次數
  - 平均通過率
  - 平均分數
- 變化卡片：
  - ▲ 上升（綠色）
  - ▼ 下降（紅色）
  - ✨ 新數據（藍色）
  - 變化百分比

#### 導航整合
- 在「測試與監控」組新增「📈 趨勢分析」鏈接
- 與「回測結果」並列，方便快速切換

### 3. 技術實作

#### 後端 (FastAPI)
**新文件：** `knowledge-admin/backend/routes_backtest_trends.py`

**核心特性：**
- 複用 `backtest_runs` 和 `backtest_results` 資料表
- 高效 SQL 查詢，支援時間範圍過濾
- 自動計算趨勢方向
- 智能警報邏輯
- 完整的錯誤處理

**效能優化：**
- 使用資料庫索引（`started_at`, `status`）
- 一次性查詢，避免 N+1 問題
- Float 類型處理，避免序列化問題

#### 前端 (Vue 3 + Chart.js)
**新文件：** `knowledge-admin/frontend/src/views/BacktestTrendsView.vue`

**技術選型：**
- **Chart.js 4.5.0** - 輕量級圖表庫
- Vue 3 Composition API
- Axios 非同步請求
- 響應式設計

**核心功能：**
- 並發載入多個 API（Promise.all）
- 圖表自動更新
- 優雅的載入與錯誤狀態
- 時間範圍切換
- 圖表實例管理（防止內存洩漏）

## 使用範例

### API 調用

```bash
# 1. 獲取 30 天趨勢
curl "http://localhost:8000/api/backtest/trends/overview?time_range=30d"

# 2. 對比最近 7 天 vs 前 7 天
curl "http://localhost:8000/api/backtest/trends/comparison?current_days=7"

# 3. 檢查警報（自訂閾值）
curl "http://localhost:8000/api/backtest/trends/alerts?pass_rate_threshold=85&avg_score_threshold=0.7"

# 4. 查看通過率指標詳情
curl "http://localhost:8000/api/backtest/trends/metrics/pass_rate?time_range=30d"
```

### 前端使用

1. **訪問趨勢分析頁面**
   ```
   http://localhost:5173/backtest/trends
   ```

2. **查看警報**
   - 頁面頂部自動顯示所有警報
   - Critical 警報以紅色高亮
   - 點擊可查看詳細建議

3. **切換時間範圍**
   - 使用下拉選單選擇：7天 / 30天 / 90天 / 全部
   - 圖表自動更新

4. **分析趨勢**
   - 查看趨勢摘要卡片（improving / declining）
   - 在圖表中查看具體變化
   - 對比期間數據，量化改進效果

## 測試驗證

### API 測試

```bash
# 測試環境
- 後端：http://localhost:8000
- 資料庫：2 次歷史回測
- 結果：所有端點正常運作

# 測試結果
✅ /api/backtest/trends/overview
   - 返回 2 個數據點
   - 趨勢判斷正確（improving）
   - 摘要統計準確

✅ /api/backtest/trends/comparison
   - 當前期間：2 次回測
   - 前一期間：0 次回測
   - 變化標記為 "new"

✅ /api/backtest/trends/alerts
   - 檢測到 1 個 critical 警報（通過率 50% < 80%）
   - 檢測到 1 個 warning 警報（平均分數 0.45 < 0.6）
   - 建議內容準確
```

### 前端測試

```bash
# 測試環境
- 前端：http://localhost:5173
- Chart.js：4.5.0
- Vue：3.3.8

# 測試結果
✅ 頁面載入
   - 無控制台錯誤
   - Chart.js 正確引入
   - 路由正常工作

✅ 警報顯示
   - Critical 警報正確顯示（紅色）
   - Warning 警報正確顯示（黃色）
   - 建議文字完整

✅ 趨勢摘要
   - 3 個摘要卡片正確渲染
   - 趨勢圖標顯示正確（📈）
   - 漸變色背景美觀

✅ 圖表渲染
   - 通過率圖表正確繪製
   - 分數圖表正確繪製
   - 鼠標懸停顯示數值
   - 時間範圍切換更新圖表

✅ 期間對比
   - 3 個對比卡片正確顯示
   - 變化方向標記正確（✨ NEW）
```

## 效益與價值

### 1. 及早發現問題 🚨
- **自動警報：** 無需人工檢查，問題自動浮出
- **多維度監控：** 通過率、分數、信心度全面監控
- **閾值可調：** 根據團隊標準自訂警報條件

### 2. 追蹤改進效果 📈
- **視覺化趨勢：** 一眼看出改善或退步
- **量化對比：** 百分比變化，改進效果可量化
- **歷史回顧：** 查看任意時間範圍的數據

### 3. 數據驅動決策 📊
- **優先級排序：** 根據警報級別決定處理順序
- **資源分配：** 根據趨勢決定投入重點
- **效果驗證：** 優化後立即看到效果

### 4. 團隊協作 👥
- **共享視圖：** 全員可見，統一理解
- **會議支援：** 週會、回顧會的數據支撐
- **知識傳承：** 新成員快速了解品質狀況

## 架構設計

### 資料流
```
┌─────────────┐
│  User       │
│  Browser    │
└──────┬──────┘
       │ HTTP Request
       ↓
┌─────────────────────────────┐
│  FastAPI Backend            │
│  routes_backtest_trends.py  │
└──────┬──────────────────────┘
       │ SQL Query
       ↓
┌─────────────────────────────┐
│  PostgreSQL Database        │
│  - backtest_runs            │
│  - backtest_results         │
└─────────────────────────────┘
       ↑
       │ Write (Phase 1)
┌──────┴──────────────────────┐
│  Backtest Framework         │
│  backtest_framework.py      │
└─────────────────────────────┘
```

### 前端架構
```
┌────────────────────────────────┐
│  BacktestTrendsView.vue        │
│                                │
│  ┌──────────────────────────┐ │
│  │  Alert Section           │ │
│  │  - Critical Alerts       │ │
│  │  - Warning Alerts        │ │
│  └──────────────────────────┘ │
│                                │
│  ┌──────────────────────────┐ │
│  │  Summary Cards           │ │
│  │  - Pass Rate             │ │
│  │  - Avg Score             │ │
│  │  - Avg Confidence        │ │
│  └──────────────────────────┘ │
│                                │
│  ┌──────────────────────────┐ │
│  │  Charts (Chart.js)       │ │
│  │  - Pass Rate Line Chart  │ │
│  │  - Score & Conf Chart    │ │
│  └──────────────────────────┘ │
│                                │
│  ┌──────────────────────────┐ │
│  │  Comparison Cards        │ │
│  │  - Current Period        │ │
│  │  - Previous Period       │ │
│  │  - Changes               │ │
│  └──────────────────────────┘ │
└────────────────────────────────┘
```

## 已知限制與改進方向

### 當前限制

1. **數據依賴**
   - 需要至少 2 次回測才能看到趨勢
   - 新系統初期數據較少

2. **圖表功能**
   - 僅支援折線圖
   - 尚未支援縮放、導出等進階功能

3. **警報系統**
   - 警報不會持久化
   - 沒有警報通知（郵件、Slack 等）

### 未來改進（Phase 4 候選）

- [ ] **進階圖表**
  - 支援柱狀圖、餅圖
  - 圖表縮放與拖曳
  - 數據導出（PNG、CSV）

- [ ] **警報通知**
  - 郵件通知
  - Slack / Teams 整合
  - 警報歷史記錄

- [ ] **自訂看板**
  - 使用者自訂指標
  - 拖曳式看板配置
  - 保存個人偏好

- [ ] **測試覆蓋率分析**
  - 哪些知識被測試過
  - 哪些意圖覆蓋不足
  - 推薦新增測試案例

- [ ] **A/B 測試支援**
  - 對比兩個配置的效果
  - RAG 參數調優
  - 模型版本對比

## 文檔

### 新增文檔
- **[Phase 3 更新日誌](./BACKTEST_PHASE3_CHANGELOG.md)**（本文件）

### 更新文檔
- **[文檔索引](./BACKTEST_INDEX.md)** - 新增 Phase 3 章節
- **[快速開始](./BACKTEST_QUICKSTART.md)** - 待更新（新增趨勢分析使用方法）

## 升級指南

### 從 Phase 2 升級

**後端：**
1. 確保後端已更新到最新版本（包含 `routes_backtest_trends.py`）
2. 確認 `app.py` 已引入趨勢路由
3. 重啟後端服務

```bash
cd knowledge-admin/backend
python3 app.py
```

**前端：**
1. 安裝 Chart.js 依賴
   ```bash
   cd knowledge-admin/frontend
   npm install chart.js
   ```

2. 確認文件已新增：
   - `src/views/BacktestTrendsView.vue`
   - `src/router.js`（已更新）
   - `src/App.vue`（已更新）

3. 重啟前端服務
   ```bash
   npm run dev
   ```

**訪問：**
```
前端：http://localhost:5173/backtest/trends
後端：http://localhost:8000/docs（查看 API 文檔）
```

## 貢獻者

- **主要開發：** Claude Code
- **測試驗證：** Lenny
- **文檔編寫：** Claude Code

## 相關鏈接

- [Phase 1.1 更新日誌](./BACKTEST_PHASE1_CHANGELOG.md)
- [Phase 1.2 更新日誌](./BACKTEST_PHASE1.2_CHANGELOG.md)
- [Phase 2 更新日誌](./BACKTEST_PHASE2_CHANGELOG.md)
- [回測策略指南](../BACKTEST_STRATEGIES.md)
- [環境變數參考](../BACKTEST_ENV_VARS.md)
- [文檔索引](./BACKTEST_INDEX.md)

## 回饋與支援

如有問題或建議，請：
1. 查閱 [故障排除文檔](../BACKTEST_STRATEGIES.md#故障排除)
2. 檢查 [API 文檔](http://localhost:8000/docs)
3. 提交 Issue 到專案 GitHub

---

**最後更新：** 2025-10-12
**版本：** Phase 3.0
**狀態：** ✅ 已完成並測試
