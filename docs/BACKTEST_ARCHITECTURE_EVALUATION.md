# 🔍 回測系統架構評估與改進建議

**評估日期**: 2025-10-12
**評估者**: Claude Code
**當前版本**: 回測框架 v1.0 (Excel-based)

---

## 📊 現況分析

### ✅ 優點

1. **完整的資料庫 Schema 設計**
   - `backtest_runs` 表：記錄每次回測執行
   - `backtest_results` 表：記錄每個測試的詳細結果
   - `test_scenarios` 表：已有統計欄位（total_runs, pass_count, fail_count, avg_score）
   - Trigger `update_scenario_statistics()` 自動更新測試統計

2. **智能測試選擇已實作**
   - `prioritize_failed`: 優先測試失敗率高的案例
   - `difficulty` 篩選
   - `min_avg_score` 篩選低分測試

3. **品質評估模式完善**
   - Basic: 快速評估
   - Hybrid: 混合評估（推薦）
   - Detailed: LLM 深度評估

### ❌ 問題

#### 1. **回測結果儲存架構問題** 🚨 高優先級

**現狀**：
```
回測框架 → 生成 Excel 檔案 → 前端讀取 Excel
              ↓
         output/backtest/backtest_results.xlsx
```

**問題**：
- ❌ 資料庫表 `backtest_runs` 和 `backtest_results` **完全沒有使用**（0 筆資料）
- ❌ 只保留最新一次回測結果，**無歷史記錄**
- ❌ 無法追蹤測試題的表現趨勢
- ❌ 無法比較不同版本/時間的回測結果
- ❌ 1000+ 測試題時，Excel 效能差

**資料庫檢查結果**：
```sql
SELECT COUNT(*) FROM backtest_runs;     -- 0 筆
SELECT COUNT(*) FROM backtest_results;  -- 0 筆
```

#### 2. **用戶困惑：審核 6 個但只顯示 5 個**

**問題原因**：
- 前端顯示的是舊的 Excel 檔案（2025-10-12 02:57）
- 新審核的 6 個測試題在資料庫中（10:45-13:26 審核通過）
- 需要重新執行回測才會更新 Excel

**這暴露了架構問題**：沒有即時性，依賴手動觸發

#### 3. **智能測試選擇策略未充分利用**

雖然已實作 `prioritize_failed`，但：
- ❌ 沒有歷史資料，無法真正發揮作用
- ❌ 第一次執行測試題時，所有 avg_score 都是 NULL
- ❌ 只有在多次回測後才能累積統計

---

## 🎯 改進建議

### Phase 1: 資料庫整合 (高優先級 - 2-3 天)

#### 1.1 修改回測框架，寫入資料庫

**修改 `backtest_framework.py`**：

```python
def save_results_to_database(self, results: List[Dict], run_metadata: Dict):
    """儲存回測結果到資料庫"""
    conn = self.get_db_connection()
    cur = conn.cursor()

    try:
        # 1. 建立 backtest_run 記錄
        cur.execute("""
            INSERT INTO backtest_runs (
                quality_mode, test_type, total_scenarios, executed_scenarios,
                status, rag_api_url, vendor_id, passed_count, failed_count,
                pass_rate, avg_score, avg_confidence,
                avg_relevance, avg_completeness, avg_accuracy,
                avg_intent_match, avg_quality_overall, ndcg_score,
                started_at, completed_at, duration_seconds,
                output_file_path, summary_file_path, executed_by
            ) VALUES (
                %s, %s, %s, %s, 'completed', %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """, (
            self.quality_mode,
            run_metadata.get('test_type', 'full'),
            len(results),
            len(results),
            self.base_url,
            self.vendor_id,
            run_metadata.get('passed_tests', 0),
            run_metadata.get('failed_tests', 0),
            run_metadata.get('pass_rate', 0),
            run_metadata.get('avg_score', 0),
            run_metadata.get('avg_confidence', 0),
            # ... quality metrics
            run_metadata['started_at'],
            datetime.now(),
            run_metadata.get('duration_seconds', 0),
            run_metadata.get('output_path'),
            run_metadata.get('summary_path'),
            'backtest_framework'
        ))

        run_id = cur.fetchone()['id']

        # 2. 插入每個測試結果
        for result in results:
            cur.execute("""
                INSERT INTO backtest_results (
                    run_id, scenario_id, test_question, expected_category,
                    actual_intent, all_intents, system_answer, confidence,
                    score, overall_score, passed, category_match, keyword_coverage,
                    relevance, completeness, accuracy, intent_match,
                    quality_overall, quality_reasoning,
                    source_ids, source_count, knowledge_sources, optimization_tips,
                    evaluation, response_metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                run_id,
                result.get('scenario_id'),  # 需要從 test_scenarios 查詢
                result['test_question'],
                result['expected_category'],
                result['actual_intent'],
                result.get('all_intents'),
                result['system_answer'],
                result['confidence'],
                result['score'],
                result.get('overall_score', result['score']),
                result['passed'],
                # ... 其他欄位
            ))

        conn.commit()
        print(f"✅ 回測結果已儲存到資料庫 (Run ID: {run_id})")
        return run_id

    except Exception as e:
        conn.rollback()
        print(f"❌ 儲存到資料庫失敗: {e}")
        raise
    finally:
        cur.close()
        conn.close()
```

**在 `generate_report()` 中調用**：
```python
def generate_report(self, results: List[Dict], output_path: str):
    # ... 現有的 Excel 生成邏輯 ...

    # 新增：儲存到資料庫
    run_metadata = {
        'test_type': 'full',
        'passed_tests': passed_tests,
        'failed_tests': total_tests - passed_tests,
        'pass_rate': pass_rate,
        'avg_score': avg_score,
        'avg_confidence': avg_confidence,
        'started_at': self.run_started_at,
        'output_path': output_path,
        'summary_path': summary_path,
        # ... 其他統計
    }

    self.save_results_to_database(results, run_metadata)
```

#### 1.2 前端支援資料庫查詢

**新增 API (`knowledge-admin/backend/app.py`)**：

```python
@app.get("/api/backtest/runs")
async def list_backtest_runs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """列出歷史回測執行記錄"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                id, quality_mode, test_type,
                passed_count, failed_count, pass_rate,
                avg_score, avg_confidence,
                started_at, completed_at, duration_seconds,
                executed_scenarios
            FROM backtest_runs
            WHERE status = 'completed'
            ORDER BY started_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

        runs = []
        for row in cur.fetchall():
            run = dict(row)
            run['started_at'] = run['started_at'].isoformat()
            if run['completed_at']:
                run['completed_at'] = run['completed_at'].isoformat()
            runs.append(run)

        # 總數
        cur.execute("SELECT COUNT(*) FROM backtest_runs WHERE status = 'completed'")
        total = cur.fetchone()['count']

        return {
            "runs": runs,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    finally:
        cur.close()
        conn.close()


@app.get("/api/backtest/runs/{run_id}/results")
async def get_run_results(
    run_id: int,
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """取得特定回測執行的詳細結果"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT * FROM backtest_results
            WHERE run_id = %s
        """
        params = [run_id]

        if status_filter == "failed":
            query += " AND passed = FALSE"
        elif status_filter == "passed":
            query += " AND passed = TRUE"

        query += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        results = [dict(row) for row in cur.fetchall()]

        # 轉換日期
        for r in results:
            if r.get('tested_at'):
                r['tested_at'] = r['tested_at'].isoformat()

        return {
            "results": results,
            "total": len(results),
            "run_id": run_id
        }

    finally:
        cur.close()
        conn.close()
```

**前端更新 (`BacktestView.vue`)**：
```vue
<template>
  <div class="backtest-view">
    <!-- 新增：回測歷史選擇器 -->
    <div class="run-selector">
      <label>回測記錄：</label>
      <select v-model="selectedRunId" @change="loadRunResults">
        <option :value="null">最新回測</option>
        <option v-for="run in historicalRuns" :key="run.id" :value="run.id">
          {{ formatDate(run.started_at) }} -
          {{ run.quality_mode }} -
          通過率 {{ run.pass_rate }}%
        </option>
      </select>
      <button @click="loadHistoricalRuns">📜 查看歷史</button>
    </div>

    <!-- 現有的結果顯示 -->
    ...
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedRunId: null,
      historicalRuns: [],
      // ... 其他資料
    }
  },
  methods: {
    async loadHistoricalRuns() {
      const response = await axios.get('/api/backtest/runs');
      this.historicalRuns = response.data.runs;
    },

    async loadRunResults() {
      if (this.selectedRunId) {
        // 從資料庫載入特定回測的結果
        const response = await axios.get(`/api/backtest/runs/${this.selectedRunId}/results`);
        this.results = response.data.results;
      } else {
        // 載入最新的 Excel 結果（向後相容）
        this.loadResults();
      }
    }
  }
}
</script>
```

---

### Phase 2: 智能測試選擇優化 (中優先級 - 1-2 天)

#### 2.1 測試策略設計

**日常增量測試** (每日執行)：
```sql
-- 優先測試以下測試題
SELECT * FROM test_scenarios
WHERE status = 'approved' AND is_active = TRUE
  AND (
    -- 1. 從未測試過的新題目
    total_runs = 0
    OR
    -- 2. 失敗率 > 50%
    (fail_count::float / NULLIF(total_runs, 0)) > 0.5
    OR
    -- 3. 平均分數 < 0.6
    avg_score < 0.6
    OR
    -- 4. 已經一週沒測試過
    last_run_at < NOW() - INTERVAL '7 days'
  )
ORDER BY
  -- 失敗率高的優先
  (fail_count::float / NULLIF(total_runs, 0)) DESC,
  -- 分數低的優先
  COALESCE(avg_score, 0) ASC,
  -- 優先級高的優先
  priority DESC
LIMIT 100;  -- 每日測試 100 題
```

**完整回測** (每週執行)：
```sql
-- 全部測試
SELECT * FROM test_scenarios
WHERE status = 'approved' AND is_active = TRUE
ORDER BY priority DESC, id;
```

**修改 `backtest_framework.py`**：
```python
def load_test_scenarios_from_db(
    self,
    strategy: str = "incremental",  # incremental, full, failed_only
    limit: int = None
) -> List[Dict]:
    """智能載入測試情境

    Args:
        strategy: 測試策略
            - incremental: 增量測試（新題目 + 失敗題 + 一週未測）
            - full: 完整測試
            - failed_only: 僅失敗題
    """

    if strategy == "incremental":
        query = """
            SELECT * FROM test_scenarios
            WHERE status = 'approved' AND is_active = TRUE
              AND (
                total_runs = 0 OR
                (fail_count::float / NULLIF(total_runs, 0)) > 0.5 OR
                avg_score < 0.6 OR
                last_run_at < NOW() - INTERVAL '7 days'
              )
            ORDER BY
              (fail_count::float / NULLIF(total_runs, 0)) DESC NULLS LAST,
              COALESCE(avg_score, 0) ASC,
              priority DESC
        """
    elif strategy == "failed_only":
        query = """
            SELECT * FROM test_scenarios
            WHERE status = 'approved' AND is_active = TRUE
              AND avg_score < 0.6
            ORDER BY avg_score ASC, priority DESC
        """
    else:  # full
        query = """
            SELECT * FROM test_scenarios
            WHERE status = 'approved' AND is_active = TRUE
            ORDER BY priority DESC, id
        """

    if limit:
        query += f" LIMIT {limit}"

    # ... 執行查詢 ...
```

#### 2.2 環境變數配置

```bash
# 測試策略
BACKTEST_STRATEGY=incremental  # incremental, full, failed_only

# 每日增量測試
BACKTEST_STRATEGY=incremental BACKTEST_SAMPLE_SIZE=100

# 每週完整測試
BACKTEST_STRATEGY=full

# 僅測試失敗的案例
BACKTEST_STRATEGY=failed_only BACKTEST_SAMPLE_SIZE=50
```

---

### Phase 3: 進階分析與可視化 (低優先級 - 3-5 天)

#### 3.1 趨勢分析

**新增 API**：
```python
@app.get("/api/backtest/trends/{scenario_id}")
async def get_scenario_trends(scenario_id: int):
    """取得測試題的歷史表現趨勢"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                br.tested_at,
                br.score,
                br.passed,
                br.confidence,
                brun.quality_mode
            FROM backtest_results br
            JOIN backtest_runs brun ON br.run_id = brun.id
            WHERE br.scenario_id = %s
            ORDER BY br.tested_at DESC
            LIMIT 30
        """, (scenario_id,))

        trends = [dict(row) for row in cur.fetchall()]

        return {"scenario_id": scenario_id, "trends": trends}

    finally:
        cur.close()
        conn.close()
```

**前端圖表** (使用 Chart.js)：
```vue
<canvas ref="trendChart"></canvas>

<script>
import Chart from 'chart.js/auto';

methods: {
  async showTrendChart(scenarioId) {
    const response = await axios.get(`/api/backtest/trends/${scenarioId}`);
    const trends = response.data.trends;

    const ctx = this.$refs.trendChart.getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: trends.map(t => t.tested_at),
        datasets: [{
          label: '分數趨勢',
          data: trends.map(t => t.score),
          borderColor: 'rgb(75, 192, 192)',
        }]
      }
    });
  }
}
</script>
```

#### 3.2 自動警報

**定期任務檢查**：
```python
async def check_test_regression():
    """檢查測試退化（原本通過現在失敗）"""

    query = """
        WITH recent_results AS (
            SELECT DISTINCT ON (scenario_id)
                scenario_id, passed, score
            FROM backtest_results
            ORDER BY scenario_id, tested_at DESC
        ),
        previous_results AS (
            SELECT DISTINCT ON (scenario_id)
                scenario_id, passed, score
            FROM backtest_results br1
            WHERE NOT EXISTS (
                SELECT 1 FROM backtest_results br2
                WHERE br2.scenario_id = br1.scenario_id
                  AND br2.tested_at > br1.tested_at
                LIMIT 1
            )
            ORDER BY scenario_id, tested_at DESC
        )
        SELECT
            ts.test_question,
            pr.score as previous_score,
            rr.score as recent_score
        FROM recent_results rr
        JOIN previous_results pr ON rr.scenario_id = pr.scenario_id
        JOIN test_scenarios ts ON ts.id = rr.scenario_id
        WHERE pr.passed = TRUE
          AND rr.passed = FALSE;
    """

    # 發送通知/建立警報
```

---

## 🚀 實作優先順序

### 立即執行（本週）
1. ✅ **修復 expected_keywords NULL bug** - 已完成
2. 🔥 **實作資料庫儲存** - Phase 1.1 (2-3 天)
   - 修改 `backtest_framework.py` 寫入資料庫
   - 保持 Excel 輸出（向後相容）
   - 測試驗證

### 下週執行
3. 📊 **前端支援歷史查詢** - Phase 1.2 (2 天)
   - 新增 API 端點
   - 更新 `BacktestView.vue`
   - 支援選擇歷史回測記錄

4. 🎯 **智能測試策略** - Phase 2 (1-2 天)
   - 實作 incremental/full/failed_only 策略
   - 環境變數配置
   - 文檔更新

### 後續優化（2-4 週後）
5. 📈 **趨勢分析與可視化** - Phase 3 (選配)
6. 🔔 **自動警報系統** - Phase 3 (選配)

---

## 💡 當前 1000+ 測試題的實作建議

假設你有 1000+ 個審核通過的測試題：

### 方案 A：分批測試（推薦）⭐

**每日增量測試** (自動排程)：
```bash
# cron: 每天凌晨 2:00 執行
BACKTEST_STRATEGY=incremental \
BACKTEST_SAMPLE_SIZE=100 \
BACKTEST_QUALITY_MODE=basic \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**結果**：
- 每天測試 100 個最需要關注的題目
- 優先測試：新題目、失敗題、一週未測題
- 約 5-10 分鐘完成

**每週完整測試** (週末執行)：
```bash
# cron: 每週日凌晨 2:00 執行
BACKTEST_STRATEGY=full \
BACKTEST_QUALITY_MODE=hybrid \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**結果**：
- 測試全部 1000+ 題
- 使用 hybrid 模式（LLM 評估）
- 約 2-3 小時完成

### 方案 B：持續整合（進階）

**整合到 CI/CD 流程**：
```yaml
# .github/workflows/backtest.yml
name: Backtest RAG System

on:
  schedule:
    - cron: '0 2 * * *'  # 每日凌晨 2:00
  workflow_dispatch:     # 手動觸發

jobs:
  incremental-test:
    runs-on: ubuntu-latest
    steps:
      - name: Run Incremental Backtest
        run: |
          BACKTEST_STRATEGY=incremental \
          BACKTEST_SAMPLE_SIZE=100 \
          python3 scripts/knowledge_extraction/backtest_framework.py

      - name: Check Regression
        run: |
          # 檢查是否有退化（原本通過現在失敗）
          python3 scripts/check_regression.py

      - name: Send Notification
        if: failure()
        run: |
          # 發送 Slack/Email 通知
```

---

## 📈 預期效益

### 短期效益（實作 Phase 1 後）
- ✅ 解決「審核 6 個但只顯示 5 個」的困惑
- ✅ 保留歷史回測記錄，可以追蹤趨勢
- ✅ 支援 1000+ 測試題的高效管理
- ✅ 回測統計自動更新（透過 trigger）

### 中期效益（實作 Phase 2 後）
- ✅ 智能測試選擇，減少不必要的測試
- ✅ 每日增量測試 + 每週完整測試
- ✅ 開發效率提升（只測試需要關注的）
- ✅ 成本優化（減少不必要的 LLM 呼叫）

### 長期效益（實作 Phase 3 後）
- ✅ 完整的品質監控系統
- ✅ 自動發現知識庫退化
- ✅ 資料驅動的知識優化
- ✅ 支援 A/B 測試（比較不同配置）

---

## 🎯 決策建議

**給團隊的建議**：

1. **立即執行 Phase 1.1** (本週)
   - 資料庫儲存是必要的，架構已經設計好了
   - 不破壞現有流程（保留 Excel）
   - 為未來優化打基礎

2. **如果測試題 < 100 個**
   - 暫時用 Excel 也可以
   - 但建議先做資料庫整合，避免未來重構

3. **如果測試題 > 100 個**
   - 必須做資料庫整合 + 智能測試策略
   - 否則回測時間會越來越長
   - 成本會越來越高

4. **如果測試題 > 1000 個**
   - Phase 1 + Phase 2 必須做
   - Phase 3 強烈建議
   - 考慮分散式回測（並行執行）

---

**下一步行動**：

1. [ ] Review 這份評估報告
2. [ ] 決定實作範圍（Phase 1 / Phase 1+2 / 全部）
3. [ ] 排定開發時程
4. [ ] 開始實作 Phase 1.1

**預估開發時間**：
- Phase 1: 3-4 天
- Phase 2: 1-2 天
- Phase 3: 3-5 天
- **總計**: 7-11 天（完整實作）

---

**評估完成** ✅
**建議**: 立即實作 Phase 1.1（資料庫整合）
