# 回測智能測試策略指南

## 概述

回測框架支援三種智能測試選擇策略，可根據不同場景選擇最適合的測試方式。

## 策略類型

### 1. Incremental（增量測試）⭐ 推薦日常使用

**用途：** 每日回歸測試，快速發現新問題

**選擇邏輯：**
- **新測試**（優先級 100）：從未執行過的測試（total_runs = 0）
- **高失敗率測試**（優先級 90）：失敗率 > 50%
- **低分測試**（優先級 85）：平均分數 < 0.6
- **長期未測試**（優先級 70）：超過 7 天未執行

**預設限制：** 100 個測試

**使用場景：**
- ✅ 每日 CI/CD 自動化測試
- ✅ Pull Request 驗證
- ✅ 快速回歸檢查

**範例：**
```bash
BACKTEST_SELECTION_STRATEGY=incremental \
BACKTEST_QUALITY_MODE=basic \
BACKTEST_NON_INTERACTIVE=true \
BACKTEST_USE_DATABASE=true \
PROJECT_ROOT=/path/to/project \
python3 scripts/knowledge_extraction/backtest_framework.py
```

### 2. Full（完整測試）

**用途：** 週度或版本發布前的完整驗證

**選擇邏輯：**
- 所有已批准（status = 'approved'）且啟用（is_active = TRUE）的測試
- 按優先級排序

**預設限制：** 無（可選自訂）

**使用場景：**
- ✅ 每週完整回測
- ✅ 重大版本發布前驗證
- ✅ 季度品質審查

**範例：**
```bash
BACKTEST_SELECTION_STRATEGY=full \
BACKTEST_QUALITY_MODE=basic \
BACKTEST_NON_INTERACTIVE=true \
BACKTEST_USE_DATABASE=true \
PROJECT_ROOT=/path/to/project \
python3 scripts/knowledge_extraction/backtest_framework.py
```

### 3. Failed Only（僅失敗測試）

**用途：** 快速驗證修復效果

**選擇邏輯：**
- 必須已測試過（total_runs > 0）
- 平均分數 < 0.6 **或** 失敗率 > 50%
- 按失敗率降序、分數升序排序

**預設限制：** 50 個測試

**使用場景：**
- ✅ 修復 bug 後快速驗證
- ✅ 知識庫優化後驗證效果
- ✅ 意圖調整後測試影響

**範例：**
```bash
BACKTEST_SELECTION_STRATEGY=failed_only \
BACKTEST_QUALITY_MODE=basic \
BACKTEST_NON_INTERACTIVE=true \
BACKTEST_USE_DATABASE=true \
PROJECT_ROOT=/path/to/project \
python3 scripts/knowledge_extraction/backtest_framework.py
```

## 環境變數配置

### 策略控制

| 變數名稱 | 說明 | 預設值 | 可選值 |
|---------|------|--------|--------|
| `BACKTEST_SELECTION_STRATEGY` | 測試選擇策略 | `full` | `incremental`, `full`, `failed_only` |
| `BACKTEST_INCREMENTAL_LIMIT` | incremental 模式限制 | `100` | 任何正整數 |
| `BACKTEST_FAILED_LIMIT` | failed_only 模式限制 | `50` | 任何正整數 |
| `BACKTEST_LIMIT` | 通用限制（覆蓋策略預設） | 無 | 任何正整數 |

### 其他配置（向後相容）

| 變數名稱 | 說明 | 預設值 |
|---------|------|--------|
| `BACKTEST_USE_DATABASE` | 啟用資料庫模式 | `true` |
| `BACKTEST_QUALITY_MODE` | 品質評估模式 | `basic` |
| `BACKTEST_NON_INTERACTIVE` | 非互動模式 | `false` |
| `BACKTEST_SAMPLE_SIZE` | 抽樣數量 | 無（全部測試） |
| `BACKTEST_DIFFICULTY` | 難度篩選（向後相容） | 無 |
| `BACKTEST_PRIORITIZE_FAILED` | 優先失敗測試（向後相容） | `true` |

## 使用建議

### 日常開發流程

```bash
# 1. 每日早上 - 增量測試（快速）
BACKTEST_SELECTION_STRATEGY=incremental python3 scripts/knowledge_extraction/backtest_framework.py

# 2. 修復失敗案例後 - 僅失敗測試驗證
BACKTEST_SELECTION_STRATEGY=failed_only python3 scripts/knowledge_extraction/backtest_framework.py

# 3. 每週五 - 完整測試（全面）
BACKTEST_SELECTION_STRATEGY=full python3 scripts/knowledge_extraction/backtest_framework.py
```

### CI/CD 整合

```yaml
# .github/workflows/backtest.yml 範例
name: Knowledge Base Backtest

on:
  schedule:
    - cron: '0 9 * * 1-5'  # 每日 9:00 (工作日)
  pull_request:
    branches: [ main ]

jobs:
  incremental-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Run Incremental Backtest
        env:
          BACKTEST_SELECTION_STRATEGY: incremental
          BACKTEST_QUALITY_MODE: basic
          BACKTEST_NON_INTERACTIVE: true
          BACKTEST_USE_DATABASE: true
        run: |
          python3 scripts/knowledge_extraction/backtest_framework.py

      - name: Check Pass Rate
        run: |
          # 檢查通過率是否 >= 80%
          pass_rate=$(grep "通過率" output/backtest/backtest_results_summary.txt | awk '{print $2}' | cut -d'%' -f1)
          if (( $(echo "$pass_rate < 80" | bc -l) )); then
            echo "❌ Pass rate too low: $pass_rate%"
            exit 1
          fi
```

## 輸出說明

### 增量測試輸出範例

```
📖 從資料庫載入測試情境（策略: incremental）...
   策略: 增量測試（新測試 + 失敗測試 + 長期未測試）
   限制: 100 個
   ✅ 載入 45 個測試情境
   📊 組成：新測試 20 | 失敗測試 15 | 長期未測試 10
```

**組成說明：**
- **新測試**：從未執行過，需要首次驗證
- **失敗測試**：之前失敗過，需要持續關注
- **長期未測試**：可能因需求變更需要重新測試

### 失敗測試輸出範例

```
📖 從資料庫載入測試情境（策略: failed_only）...
   策略: 僅失敗測試（avg_score < 0.6 或失敗率 > 50%）
   限制: 50 個
   ✅ 載入 12 個測試情境
```

## 最佳實踐

### 1. 測試頻率建議

| 策略 | 頻率 | 時機 |
|-----|------|------|
| **incremental** | 每日 | 早上自動執行 |
| **failed_only** | 按需 | 修復後立即驗證 |
| **full** | 每週 | 週五下班前 |

### 2. 限制數量設定

```bash
# 開發環境：快速驗證
BACKTEST_INCREMENTAL_LIMIT=30
BACKTEST_FAILED_LIMIT=20

# 測試環境：中等覆蓋
BACKTEST_INCREMENTAL_LIMIT=100  # 預設值
BACKTEST_FAILED_LIMIT=50        # 預設值

# 生產環境：完整覆蓋
BACKTEST_SELECTION_STRATEGY=full  # 不設限制
```

### 3. 品質閾值監控

設定警報閾值：
- **通過率 < 80%**：發送警報通知
- **平均分數 < 0.5**：觸發緊急審查
- **信心度 < 0.7**：需要知識庫優化

## 資料庫更新

測試執行後會自動更新以下統計：
- `total_runs`: 總執行次數 +1
- `pass_count` / `fail_count`: 通過/失敗次數
- `avg_score`: 平均分數（加權平均）
- `last_run_at`: 最後執行時間

這些統計會影響下次 incremental 策略的選擇。

## 故障排除

### 問題 1：載入 0 個測試

**原因：** 所有測試都不符合策略條件

**解決：**
```bash
# 檢查測試情境狀態
SELECT status, is_active, COUNT(*)
FROM test_scenarios
GROUP BY status, is_active;

# 確認有 approved 且 active 的測試
```

### 問題 2：incremental 總是選擇相同的測試

**原因：** 測試一直失敗，分數未改善

**解決：**
1. 分析失敗原因（查看 optimization_tips）
2. 優化相關知識或意圖
3. 使用 `failed_only` 策略快速驗證

### 問題 3：想臨時測試特定測試

**解決：** 使用向後相容的難度篩選
```bash
# 只測試困難的測試
BACKTEST_DIFFICULTY=hard python3 scripts/knowledge_extraction/backtest_framework.py
```

## 進階用法

### 自訂 SQL 策略（進階）

如需更複雜的選擇邏輯，可以修改 `backtest_framework.py` 中的 `load_test_scenarios_by_strategy()` 方法。

範例：選擇特定業務場景的測試
```python
query = """
    SELECT * FROM test_scenarios ts
    WHERE ts.is_active = TRUE
      AND ts.status = 'approved'
      AND ts.notes LIKE '%B2C%'  -- 自訂條件
    ORDER BY ts.priority DESC
    LIMIT %s
"""
```

### 組合多個策略

```bash
# 先測試失敗案例，再測試新測試
BACKTEST_SELECTION_STRATEGY=failed_only BACKTEST_FAILED_LIMIT=20 python3 scripts/...
BACKTEST_SELECTION_STRATEGY=incremental BACKTEST_LIMIT=30 python3 scripts/...
```

## 相關文件

- [回測框架使用指南](./backtest_usage.md)
- [資料庫 Schema 說明](./database_schema.md)
- [API 端點文檔](./api_endpoints.md)
