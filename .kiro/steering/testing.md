# Testing Steering

> **相關文件**：知識系統請參考 [knowledge.md](./knowledge.md)、對話流程請參考 [dialogue.md](./dialogue.md)

## 1. 回測策略（核心配置）

### 預設配置

```python
LoopConfig(
    batch_size=50,           # 批次大小：50 題（首批驗證）
    target_pass_rate=0.85,   # 目標通過率：85%
    max_iterations=10,       # 最大迭代次數：10 次
    action_type_mode="ai_assisted"  # AI 輔助判斷
)
```

### 批次控制原則

**首批小規模驗證**：
- 第一批次：50 題
- 目的：快速驗證知識完善流程有效性
- 控制成本：避免大規模執行產生過高 API 成本

**後續批次擴展**：
- 支援調整批次範圍（例如：51-100, 101-200）
- 獨立創建新的 loop_id
- 不影響前批次記錄

### 通過率目標

| 等級 | 通過率 | 判定 |
|------|--------|------|
| 優秀 | ≥ 85% | 達成目標 |
| 良好 | 70-85% | 需持續改善 |
| 不足 | < 70% | 重點補強 |

## 2. 測試場景管理

### test_scenarios 資料表

**核心欄位**：
```sql
test_scenarios
├── id
├── question                -- 測試問題
├── expected_answer         -- 預期答案（可選）
├── status                  -- 'approved'/'pending_review'/'rejected'
├── vendor_id               -- 業者 ID
├── category                -- 問題分類（可選）
├── source                  -- 'manual'/'user_question'/'auto_generated'
├── difficulty              -- 'easy'/'medium'/'hard'
└── created_at
```

### 狀態管理

**3 種狀態**：
1. **approved**：已批准，用於回測
2. **pending_review**：待審核，不用於回測
3. **rejected**：已拒絕，不用於回測

**篩選原則**：
- 回測只讀取 `status = 'approved'` 的場景
- 按業者 ID 過濾（支援多業者隔離）

### 測試場景來源

| 來源 | 說明 | 品質 |
|------|------|------|
| manual | 人工編寫 | 高 |
| user_question | 用戶真實問題 | 中高 |
| auto_generated | AI 輔助生成 | 中 |
| imported | 批量匯入 | 視來源而定 |

## 3. 回測執行

### 執行入口

```bash
# 完整流程（包含知識生成）
docker exec -e VENDOR_ID=2 aichatbot-rag-orchestrator \
  bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"

# 僅回測模式（不生成知識）
docker exec -e VENDOR_ID=2 -e BACKTEST_ONLY=true aichatbot-rag-orchestrator \
  bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"
```

### 回測框架

**使用模組**：
- `scripts/backtest/backtest_framework_async.py`（非同步框架）
- `services/backtest_service.py`（回測服務）

**回測流程**：
1. 從 `test_scenarios` 讀取已批准的測試場景
2. 調用 RAG API (`http://localhost:8100`) 進行問答
3. 記錄結果到 `backtest_results` 表
4. 計算通過率

### backtest_results 資料表

```sql
backtest_results
├── id
├── run_id                  -- 回測批次 ID（用於追蹤同批次重測）
├── scenario_id             -- 對應的 test_scenarios.id
├── question
├── expected_answer
├── actual_answer           -- RAG 系統實際回答
├── is_pass                 -- 是否通過（布林值）
├── execution_time          -- 回答耗時（毫秒）
└── created_at
```

## 4. 失敗案例分析

### 知識缺口識別

**篩選條件**：
- `is_pass = false` 的回測結果
- 收集失敗原因與實際回答

**失敗類型分類**（由 AI 自動判斷）：
1. **sop_knowledge**：缺少 SOP 流程知識
2. **form_fill**：缺少表單填寫流程
3. **system_config**：缺少系統配置知識
4. **api_query**：需即時 API 查詢（不生成靜態知識）

### 失敗案例統計

**關鍵指標**：
- 失敗案例總數
- 失敗率（fail_rate = 1 - pass_rate）
- 按分類統計失敗分佈

**記錄到**：
- `loop_execution_logs` 表（event_type = 'gaps_analyzed'）

## 5. 迭代控制邏輯

### 迭代完成條件

**3 種情況會結束迭代**：

```python
# Case 1: 達到目標通過率
if latest_pass_rate >= target_pass_rate:  # >= 85%
    status = 'completed'
    reason = f"達到目標通過率 {latest_pass_rate:.1%}"

# Case 2: 超過最大迭代次數
if current_iteration >= max_iterations:  # >= 10
    status = 'completed'
    reason = f"超過最大迭代次數 {current_iteration}/{max_iterations}"

# Case 3: 無新的知識缺口（無法再改善）
if failed_count == 0:
    status = 'completed'
    reason = "無失敗案例"
```

### 同批次重測驗證

**核心原則**：
- 每次迭代使用**相同的測試批次** (run_id)
- 驗證新增知識的有效性
- 追蹤通過率變化趨勢

**實現方式**：
```python
# 第一次迭代：記錄 run_id 和測試場景 ID 列表
initial_run_id = generate_run_id()
scenario_ids = [s.id for s in selected_scenarios]

# 後續迭代：使用相同的 scenario_ids
# 但生成新的 run_id 以區分不同迭代
```

### knowledge_completion_loops 資料表

```sql
knowledge_completion_loops
├── id (loop_id)
├── vendor_id
├── status                  -- 'pending'/'running'/'completed'/'failed'
├── target_pass_rate        -- 目標通過率（預設 0.85）
├── max_iterations          -- 最大迭代次數（預設 10）
├── current_iteration       -- 當前迭代次數
├── current_pass_rate       -- 當前通過率
└── created_at
```

## 6. 品質標準

### 回測性能要求

- 單次回測（50 題）：**應**在 5 分鐘內完成
- API 回應時間：平均 < 3 秒/題
- 系統可用性：> 99%

### 測試覆蓋率

**多維度覆蓋**：
1. **來源覆蓋**：manual、user_question、auto_generated 都應有代表性測試
2. **難度覆蓋**：easy、medium、hard 比例建議為 3:5:2
3. **主題覆蓋**：租金、裝潢、緊急、稅務、法律等核心主題都應涵蓋

### 知識品質標準

**生成的知識應滿足**：
- SOP 步驟清晰、可執行
- 答案完整、準確
- 關鍵字設定合理
- 觸發條件精準（避免誤觸發）

## 7. 執行模式

### 完整流程模式（預設）

**8 步驟**：
1. 執行回測
2. 分析失敗案例
3. AI 智能分類
4. 按類別分離
5. 分別聚類
6. 生成知識
7. 人工審核
8. 同批次回測檢驗

### 僅回測模式（BACKTEST_ONLY=true）

**用途**：
- 快速驗證當前知識庫效果
- 檢查特定批次的通過率
- 不觸發知識生成流程

**使用時機**：
- 知識審核批准後，驗證改善效果
- 定期檢查系統表現
- Debug 回測框架

## 8. 監控與日誌

### loop_execution_logs

**記錄事件類型**：
```python
EVENT_TYPES = [
    'loop_started',          # 迴圈啟動
    'backtest_executed',     # 回測執行完成
    'gaps_analyzed',         # 知識缺口分析完成
    'gaps_classified',       # 智能分類完成
    'knowledge_generated',   # 知識生成完成
    'iteration_completed',   # 迭代完成
    'loop_completed',        # 迴圈完成
    'error'                  # 錯誤發生
]
```

**日誌結構**：
```sql
loop_execution_logs
├── id
├── loop_id
├── iteration               -- 迭代次數
├── event_type
├── event_data (JSONB)      -- 詳細資料
└── created_at
```

### 關鍵指標追蹤

**每次迭代記錄**：
- 通過率變化
- 失敗案例數量
- 生成知識數量（SOP vs 一般知識）
- OpenAI API 成本
- 執行耗時

## 9. 迭代開發工作流程（避免上下文丟失）

### 問題與挑戰

**常見問題**：
1. 修改後重新回測時容易創建新腳本
2. 回測步驟容易遺漏
3. Token 耗盡後整個上下文丟失
4. 難以從中斷處恢復

### 固定腳本路徑策略

**核心原則**：使用固定的標準腳本位置，避免重複創建

**標準腳本位置**：
```bash
# ============================================================================
# 主要回測腳本（已存在於專案中，禁止重複創建）
# ============================================================================

# 1. 完整知識完善迴圈（回測 + 知識生成）
services/knowledge_completion_loop/run_first_loop.py
# 用途：執行完整的知識完善迴圈
# 流程：回測 → 分析缺口 → AI 分類 → 聚類 → 生成知識 → 人工審核
# 環境變數：
#   - VENDOR_ID=2（必需）
#   - OPENAI_API_KEY（知識生成時必需）
#   - BACKTEST_ONLY=true（僅回測模式，不生成知識）
# 執行方式：
docker exec -e VENDOR_ID=2 -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  aichatbot-rag-orchestrator \
  bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"

# 2. 純回測模式（不生成知識）
rag-orchestrator/run_backtest_db.py
# 用途：僅執行回測，記錄結果到資料庫
# 流程：讀取測試場景 → 調用 RAG API → 記錄結果 → 計算通過率
# 環境變數：
#   - VENDOR_ID=2（必需）
#   - BACKTEST_BATCH_LIMIT=50（限制測試數量）
#   - BACKTEST_FILTER_STATUS=approved（篩選已批准的測試）
# 執行方式：
docker exec -e VENDOR_ID=2 -e BACKTEST_BATCH_LIMIT=50 \
  aichatbot-rag-orchestrator \
  bash -c "cd /app && python3 run_backtest_db.py"

# 3. 回測框架（底層框架，被上述腳本調用）
scripts/backtest/backtest_framework_async.py
# 用途：並發回測框架 V2（提供 5-10x 性能提升）
# 特性：並發執行、異步 HTTP、智能重試、實時進度、批量 LLM 評估
# 注意：這是底層框架，不直接執行，由 run_backtest_db.py 和 run_first_loop.py 調用

# ============================================================================
# 臨時分析腳本（可重用，使用固定檔名）
# ============================================================================
/tmp/analyze_coverage.py           # 覆蓋率分析
/tmp/analyze_latest_run.py         # 最新執行分析
/tmp/query_backtest_results.py     # 回測結果查詢
/tmp/check_loop_status.py          # 迴圈狀態恢復查詢
```

**命名原則**：
- 主要功能腳本：使用專案路徑，納入版控
- 臨時分析腳本：使用 `/tmp/` 路徑，固定檔名便於重用
- **禁止**：隨意創建 `run_backtest_v2.py`、`run_backtest_final.py` 等變體

### 上下文持久化策略

**Steering 作為項目記憶**：
- 所有重要配置、流程、原則寫入 `.kiro/steering/`
- 新對話時透過讀取 steering 快速恢復上下文
- Steering 是跨對話的持久化記憶

**檢查清單管理**：
```markdown
# 回測執行檢查清單（記錄到 .kiro/steering/testing.md）

## 執行前檢查
- [ ] 確認 test_scenarios 中有足夠的 approved 測試案例
- [ ] 確認 VENDOR_ID 設定正確
- [ ] 確認環境變數載入（OPENAI_API_KEY）
- [ ] 確認回測模式（BACKTEST_ONLY=true/false）

## 執行中監控
- [ ] 檢查 API 調用成功率
- [ ] 監控通過率變化
- [ ] 追蹤 OpenAI 成本

## 執行後驗證
- [ ] 檢查 backtest_results 表記錄完整
- [ ] 分析失敗案例分佈
- [ ] 驗證知識生成品質（若非 BACKTEST_ONLY）
- [ ] 記錄關鍵指標到日誌
```

### 新對話恢復流程

**標準開場流程**（新對話時執行）：

**步驟 1：載入 Steering 上下文**
```
請幫我讀取以下 steering 文件：
- .kiro/steering/testing.md
- .kiro/steering/knowledge.md
- .kiro/steering/ai-usage.md
- .kiro/steering/dialogue.md
```

**步驟 2：說明當前任務**
```
我要執行 [具體任務]，例如：
- 回測 vendor_id=2 的測試案例
- 分析最新一次回測的失敗原因
- 執行知識完善迴圈第二次迭代
```

**步驟 3：提供關鍵上下文**
```
當前狀態：
- 上次執行到：[具體步驟]
- 上次遇到的問題：[問題描述]
- 需要繼續的工作：[下一步計劃]
```

### 中斷恢復機制

**資料庫作為真實來源**：
- 所有執行狀態記錄在資料庫中（`knowledge_completion_loops`、`backtest_results`）
- 中斷後可從資料庫恢復執行進度
- 不依賴對話上下文

**恢復查詢腳本**：
```python
# /tmp/check_loop_status.py（固定腳本，可重用）
import psycopg2

conn = psycopg2.connect(...)
cursor = conn.cursor()

# 查詢最新迴圈狀態
cursor.execute("""
    SELECT id, current_iteration, current_pass_rate, status
    FROM knowledge_completion_loops
    WHERE vendor_id = 2
    ORDER BY created_at DESC LIMIT 1
""")

# 查詢最新回測結果
cursor.execute("""
    SELECT run_id, COUNT(*) as total,
           SUM(CASE WHEN is_pass THEN 1 ELSE 0 END) as passed
    FROM backtest_results
    WHERE run_id = (SELECT MAX(run_id) FROM backtest_results)
    GROUP BY run_id
""")
```

### 工作流程範例

**場景：執行回測並分析失敗原因**

**第一次對話**：
1. 讀取 steering 文件
2. 執行回測
3. 分析失敗原因
4. 記錄關鍵發現到 steering（若有重要模式）

**Token 用盡，開啟新對話**：
1. 讀取 steering 文件（快速恢復上下文）
2. 查詢資料庫確認上次執行狀態
3. 繼續未完成的工作（例如：生成知識、批准 SOP）

**第三次對話（批准後重測）**：
1. 讀取 steering 文件
2. 執行同批次回測（驗證改善效果）
3. 對比前後通過率
4. 記錄迭代結果

### 最佳實踐總結

**DO（推薦做法）**：
- ✅ 使用專案中已存在的腳本路徑
- ✅ 臨時腳本使用固定檔名（`/tmp/analyze_coverage.py`）
- ✅ 重要發現記錄到 steering 文件
- ✅ 新對話開始時讀取相關 steering
- ✅ 從資料庫查詢恢復執行狀態
- ✅ 使用檢查清單確保步驟完整

**DON'T（避免做法）**：
- ❌ 創建新的變體腳本（`run_backtest_v2.py`）
- ❌ 依賴對話記憶而不查詢資料庫
- ❌ 忘記記錄重要配置到 steering
- ❌ 新對話時重新摸索流程
- ❌ 跳過檢查清單中的步驟

## 10. 實作細節參考

**詳細實作文件**：
- 位置：`.kiro/specs/backtest-knowledge-refinement/implementation.md`
- 包含：具體檔案路徑、函數呼叫鏈、資料庫表關係、核心修改處

**何時參考**：
- 🔧 修改程式碼時：查找具體文件和函數
- 🐛 Debug 問題時：追蹤呼叫鏈
- 📝 Code Review 時：了解影響範圍

**快速索引**：
- 步驟 3（智能分類）：`services/knowledge_completion_loop/gap_classifier.py`
- 步驟 4-5（分離+聚類）：`gap_classifier.py:513-657` ⭐ 核心修改
- 步驟 6（生成知識）：`sop_generator.py`, `knowledge_generator.py`
- 資料庫表關係：查看 implementation.md「資料流向圖」章節

## 核心原則總結

### 1. 測試驅動知識完善
- 知識缺口應先有測試案例
- 回測驗證知識改善效果
- 迭代直到達成目標通過率

### 2. 批次控制與成本管理
- 首批 50 題小規模驗證
- 避免大規模執行產生過高成本
- 支援後續批次擴展

### 3. 同批次重測驗證
- 使用相同測試批次驗證改善
- 追蹤通過率變化趨勢
- 確保知識補充有效

### 4. 多維度測試覆蓋
- 來源多樣化（手動、用戶、AI 生成）
- 難度分級（easy/medium/hard）
- 主題全面（租金、裝潢、稅務、法律等）

### 5. 迭代控制
- 目標通過率：85%
- 最大迭代次數：10 次
- 三種完成條件：達標、超限、無缺口
