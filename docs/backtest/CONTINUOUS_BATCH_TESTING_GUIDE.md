# 連續分批回測功能測試指南

## 實作完成摘要

### ✅ 已完成的功能

1. **資料庫擴展**
   - 新增 `total_batches` 欄位 (INT)
   - 新增 `completed_batches` 欄位 (INT, DEFAULT 0)
   - 位置: `backtest_runs` 表

2. **後端 API**
   - `POST /api/test-scenarios/count` - 統計符合條件的測試題數
   - `POST /api/backtest/run/smart-batch` - 智能分批執行（單批）
   - `POST /api/backtest/run/continuous-batch` - 連續分批執行（全部）
   - 位置: `/Users/lenny/jgb/AIChatbot/knowledge-admin/backend/app.py`

3. **回測腳本**
   - 支援 `BACKTEST_PARENT_RUN_ID` 環境變數
   - 連續分批模式：累加結果到 parent run
   - 單次執行模式：正常更新並標記為 completed
   - 位置: `/Users/lenny/jgb/AIChatbot/scripts/backtest/run_backtest_with_db_progress.py`

4. **前端 UI**
   - 新增「🚀 連續分批執行全部」按鈕
   - 顯示批次進度：「📦 批次進度: 35/60 (58.3%)」
   - 詳細確認對話框，包含總批次數、預估時間等
   - 位置: `/Users/lenny/jgb/AIChatbot/knowledge-admin/frontend/src/views/BacktestView.vue`

---

## 測試步驟

### 前置條件

1. 確認服務運行：
   ```bash
   # 前端 (port 8087)
   docker ps | grep knowledge-admin-web

   # 後端 (port 8000)
   docker ps | grep knowledge-admin-api
   ```

2. 確認測試題目數量：
   ```bash
   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
     -c "SELECT COUNT(*) FROM test_scenarios;"
   ```
   目前應該有 **3064 題**

### 測試 1: 小規模測試（推薦）

**目的**: 驗證連續分批功能正常運作

**步驟**:

1. 開啟瀏覽器，前往 http://localhost:8087/backtest

2. 登入系統（如需要）

3. 啟用智能分批模式：
   - 勾選「🎯 智能分批模式」

4. 設定小規模測試參數：
   - 批量大小：選擇「50 題/批」
   - 篩選條件：可選（例如選擇特定 source 或 difficulty）

5. 點擊「🚀 連續分批執行全部」按鈕

6. 確認對話框會顯示：
   - 符合條件總數（例如：3064 題）
   - 批量設定（50 題/批）
   - 總批次數（例如：62 批）
   - 預估耗時（例如：約 306 分鐘）

7. **重要**: 為了快速測試，可以先設定篩選條件，例如：
   - 批量大小：50 題/批
   - 使用篩選條件縮小範圍到 100 題左右
   - 這樣只需要 2 批，約 10 分鐘即可完成

8. 點擊「確定」開始執行

9. 觀察進度顯示：
   ```
   ⏳ 回測執行中...
   📦 批次進度: 1/2 (50.0%)
   進度: 50/100 (50.0%)
   [進度條]
   已運行: 5 分鐘 | 預估剩餘: 5 分鐘
   ```

10. 等待完成後，檢查結果：
    - 所有批次的結果應該合併在同一個 Run ID 下
    - 可以查看完整的測試報告

### 測試 2: 驗證資料庫記錄

**步驟**:

1. 查詢最新的 run 記錄：
   ```bash
   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
   SELECT
     id,
     test_type,
     total_scenarios,
     executed_scenarios,
     total_batches,
     completed_batches,
     status,
     passed_count,
     failed_count
   FROM backtest_runs
   ORDER BY id DESC
   LIMIT 1;"
   ```

2. 預期結果：
   - `test_type`: 'batch'
   - `total_batches`: 應該等於計算的批次數（例如 2 或 62）
   - `completed_batches`: 完成後應該等於 `total_batches`
   - `status`: 'completed'
   - `executed_scenarios`: 應該等於 `total_scenarios`

3. 驗證所有批次的結果都在同一個 run_id 下：
   ```bash
   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
   SELECT
     run_id,
     COUNT(*) as result_count
   FROM backtest_results
   GROUP BY run_id
   ORDER BY run_id DESC
   LIMIT 5;"
   ```

### 測試 3: 前端 UI 測試

**驗證項目**:

1. ✅ 批次進度顯示正確
   - 應顯示「📦 批次進度: X/Y (Z%)」

2. ✅ 題目進度顯示正確
   - 應顯示「進度: X/Y (Z%)」

3. ✅ 進度條正確更新
   - 每 5 秒更新一次

4. ✅ 完成後狀態正確
   - 顯示通過數、失敗數、錯誤數
   - 顯示通過率

5. ✅ 可以關閉瀏覽器，執行繼續
   - 關閉瀏覽器後重新開啟
   - 進度應該繼續更新（如果還在執行中）

---

## 全量測試（3000+ 題）

**警告**: 全量測試需要 2-5 小時，請確保：
- 系統資源充足
- 網絡連接穩定
- RAG API 服務正常運行

**建議設定**:
- 批量大小：50 或 100 題/批
- 品質模式：hybrid（平衡速度和品質）
- 並發數：5（預設）

**執行步驟**:
1. 確認沒有其他回測正在執行
2. 選擇適當的批量大小
3. 點擊「🚀 連續分批執行全部」
4. 確認執行參數
5. 可以關閉瀏覽器，稍後回來查看結果

---

## 預期結果

### 成功指標

1. **批次執行**
   - 所有批次依序執行完成
   - 每個批次完成後 `completed_batches` 增加 1

2. **結果統計**
   - `executed_scenarios` = `total_scenarios`
   - `passed_count` + `failed_count` + `error_count` = `total_scenarios`
   - 通過率計算正確

3. **資料庫記錄**
   - 單一 run_id 包含所有測試結果
   - `backtest_results` 表中有正確數量的記錄

4. **前端顯示**
   - 批次進度正確顯示
   - 題目進度正確顯示
   - 完成後自動刷新結果列表

### 可能的問題

1. **API Timeout**
   - 症狀：單個批次執行超過預期時間
   - 解決：檢查 RAG API 服務是否正常

2. **資料庫連接錯誤**
   - 症狀：進度更新失敗
   - 解決：檢查資料庫連接設定

3. **記憶體不足**
   - 症狀：執行中斷或容器重啟
   - 解決：減少批量大小或並發數

---

## 後續步驟

測試完成後，可以：

1. **分析測試結果**
   - 查看 `/logs/batch_tests/` 目錄下的分析報告
   - 識別知識缺口

2. **補充知識**
   - 根據失敗問題補充知識庫
   - 重新測試驗證改進

3. **持續改進**
   - 調整品質評估標準
   - 優化回測策略

---

## 技術細節

### API 端點規格

**POST /api/backtest/run/continuous-batch**

Request:
```json
{
  "batch_size": 50,
  "quality_mode": "hybrid",
  "status": null,
  "source": null,
  "difficulty": null
}
```

Response:
```json
{
  "success": true,
  "message": "連續分批回測已啟動",
  "run_id": 123,
  "total_batches": 62,
  "total_scenarios": 3064,
  "estimated_time": "預估耗時: 約 306 分鐘"
}
```

### 資料庫 Schema

```sql
ALTER TABLE backtest_runs
ADD COLUMN IF NOT EXISTS total_batches INT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS completed_batches INT DEFAULT 0;
```

---

*文檔生成時間: 2026-03-14*

*相關文件:
- `/docs/backtest/LOOKUP_REFACTORING_COMPLETE_SUMMARY.md`
- `/docs/features/lookup/LOOKUP_REFACTORING_COMPLETE_SUMMARY.md`
