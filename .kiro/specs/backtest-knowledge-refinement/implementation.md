# 知識完善迴圈 - 實作細節

> **執行指南請參考**：[.kiro/steering/testing.md](../../steering/testing.md)

## 📌 唯一執行入口

```bash
cd /Users/lenny/jgb/AIChatbot/rag-orchestrator
docker exec -e VENDOR_ID=2 aichatbot-rag-orchestrator \
  bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"
```

---

## ⚠️ 已知限制與實作缺陷

### P1: 跨 Session 迭代續接功能缺失

**狀態**: ❌ 未實作
**影響**: `run_next_iteration.sh` 和 `quick_verification.sh` 腳本無法按原設計使用
**詳細說明**: 請參考 `requirements.md` Section 10.6.1

**當前限制**：
- ✅ 支援：同一 Python session 內連續執行多次迭代
- ❌ 不支援：載入已存在的 loop 並繼續執行下一次迭代
- ❌ 不支援：使用者審核完知識後，從命令列繼續執行下一次迭代
- ❌ 不支援：在同一 loop 內追蹤改善幅度（quick_verification.sh 需要此功能）

**錯誤訊息**：
```
models.InvalidStateError: 無法從狀態 'UNINITIALIZED' 轉換至 'execute_iteration'
```

**原設計的完整流程**（批次迭代模式）：

```bash
# ========================================
# Loop #84（第一批次：50 題）
# ========================================

# === 迭代 1：首次生成知識 ===
./run_50_verification.sh              # Loop #84, 迭代 1
# 執行回測 + 分析缺口 + 生成知識
# 輸出：通過率: 50%, 生成 5 個知識

# 人工審核、修正、批准
# 滿意後批准 → 立即同步

# === 迭代 2：驗證知識效果 ===
./run_next_iteration.sh 84            # ⚠️ 目前無法執行（P1 缺陷）
# 執行回測（使用相同 50 題）
# 輸出：通過率: 60%（改善 +10%）

# 人工修正/優化知識內容
# 調整效果不好的 SOP

# === 迭代 3：驗證修正效果 ===
./run_next_iteration.sh 84            # ⚠️ 目前無法執行（P1 缺陷）
# 輸出：通過率: 70%（改善 +20%）

# === 持續迭代直到達標 ===
# 重複「迭代 → 審核/修正 → 批准」流程
# 直到通過率 >= 85%（目標達成）

# === [Loop #84 完成，滿意] ===

# ========================================
# Loop #85（第二批次：另外 50 題）
# ========================================

# === 迭代 1：新批次首次生成 ===
./run_50_verification.sh              # Loop #85, 迭代 1
# 測試新的 50 題，生成對應知識

# 人工審核、批准

# === 迭代 2-N：持續優化 ===
./run_next_iteration.sh 85            # ⚠️ 目前無法執行（P1 缺陷）
# 重複迭代直到 Loop #85 達標

# === [Loop #85 完成，滿意] ===

# ========================================
# Loop #86（第三批次：再 50 題）
# ========================================
# 以此類推，直到處理完所有題庫

# === 輔助工具：quick_verification.sh（可選）===
./quick_verification.sh 84
# 查看指定 loop 的統計：狀態、通過率、迭代次數、生成知識數
```

**當前可用的替代流程**（因 P1 缺陷）：
```bash
# === 第一次測試（Loop #84）===
./run_50_verification.sh
# 輸出：Loop ID: 84, 通過率: 50%, 生成 5 個知識

# === 前端審核並批准 ===
# 批准後立即同步到知識庫

# === 第二次測試（Loop #85，建立新 loop）===
./run_50_verification.sh
# 輸出：Loop ID: 85, 通過率: 60%（知識庫已有 Loop #84 的知識）

# === 人工比較改善幅度 ===
# Loop #84: 50% → Loop #85: 60% [改善 +10%]
```

**P1 缺陷導致的功能缺失**：
1. ❌ 無法執行 `run_next_iteration.sh`（無法在同一 loop 內繼續迭代）
2. ❌ 無法追蹤單一 loop 的改善趨勢（必須建立多個 loop 間接比較）
3. ⚠️ `quick_verification.sh` 作為輔助查詢工具仍可使用，但無法比較同一 loop 的多次迭代數據

**需要實作**：
在 `coordinator.py` 中新增 `load_loop(loop_id)` 方法，支援載入現有 loop 並初始化協調器狀態。

### P2: 資料庫架構與文件不完全匹配

**狀態**: ⚠️ 部分實作
**影響**: 部分功能受限，驗證腳本已適配實際架構
**詳細說明**: 請參考 `requirements.md` Section 10.6.2

**主要差異**：
- `scenario_ids` 欄位未實作（使用 `total_scenarios` 整數替代）
- `max_iterations` 儲存在 `config` JSONB 中而非獨立欄位
- `gap_type` 實際為 `failure_reason`
- `cluster_id` 聚類功能未實作

**已修正**：
- ✅ `quick_verification.sh` 已適配實際架構
- ✅ `run_next_iteration.sh` 已適配實際架構

### P3: total_scenarios 欄位記錄錯誤

**狀態**: 🐛 Bug
**影響**: 統計顯示不正確，但不影響功能運作
**詳細說明**: 請參考 `requirements.md` Section 10.6.3

**實際行為**：`run_first_loop.py` 將 `total_scenarios` 設定為整個資料庫的情境總數（3043），而非當前批次使用的數量（50/500/3000）。

**位置**：`services/knowledge_completion_loop/run_first_loop.py`

---

## 🔄 完整流程與文件對應

### 第 1 步：執行回測

**使用文件**：
```
services/knowledge_completion_loop/run_first_loop.py
  ↓ 調用
scripts/backtest/backtest_framework_async.py
  ↓ 使用
services/backtest_service.py
```

**資料庫表**：
- `test_scenarios` (讀取測試情境)
- `backtest_results` (寫入測試結果)

**關鍵函數**：
- `run_first_loop.py:main()` - 入口函數
- `backtest_framework_async.py:AsyncBacktestFramework` - 並發回測框架

---

### 第 2 步：分析失敗案例

**使用文件**：
```
services/knowledge_completion_loop/coordinator.py
  ↓ 函數：analyze_failures()
```

**資料來源**：
- 從回測結果篩選失敗的測試案例
- 收集問題、期望答案、實際回答

**關鍵函數**：
- `coordinator.py:analyze_failures()` - 分析失敗案例

---

### 第 3 步：智能分類 (OpenAI)

**使用文件**：
```
services/knowledge_completion_loop/gap_classifier.py
  ↓ 函數：classify_gaps_batch()
  ↓ 調用 OpenAI API
```

**分類結果**：
- `sop_knowledge` - SOP 流程知識
- `form_fill` - 表單填寫
- `system_config` - 系統配置知識
- `api_query` - API 查詢（不生成靜態知識）

**資料庫表**：
- `loop_execution_logs` (記錄分類事件)

**關鍵函數**：
- `gap_classifier.py:classify_gaps_batch()` - 批次分類
- 使用 OpenAI API: `gpt-4o-mini`, temperature=0.3

---

### 第 4 步：按類別分離 + 第 5 步：分別聚類

**使用文件**：
```
services/knowledge_completion_loop/gap_classifier.py
  ↓ 函數：get_clusters_for_generation()  ⭐ 核心修改處
  ↓ 函數：_cluster_by_category()         ⭐ 新增函數
```

**處理邏輯**：
```python
# 第 4 步：按類別分離
sop_questions = []      # sop_knowledge + form_fill
knowledge_questions = [] # system_config

# 第 5 步：分別聚類
sop_clusters = _cluster_by_category(sop_questions, "SOP")
knowledge_clusters = _cluster_by_category(knowledge_questions, "Knowledge")
```

**使用資源**：
- `services/knowledge_completion_loop/cluster_rules.json` (聚類規則)

**資料庫表**：
- `loop_execution_logs` (記錄聚類事件)

**關鍵函數**：
- `gap_classifier.py:get_clusters_for_generation()` [第 513-657 行] ⭐
- `gap_classifier.py:_cluster_by_category()` [新增]
- 使用 OpenAI API: `gpt-4o-mini`, temperature=0.3

---

### 第 6 步：生成知識

#### 6.1 SOP 生成

**使用文件**：
```
services/knowledge_completion_loop/coordinator.py
  ↓ 函數：_generate_sops()
  ↓ 調用
services/knowledge_completion_loop/sop_generator.py
  ↓ 函數：generate_sop_batch()
  ↓ 調用 OpenAI API
```

**資料庫表**：
- `vendor_sop_categories` (讀取分類)
- `vendor_sop_groups` (讀取群組)
- `loop_generated_knowledge` (寫入待審核 SOP)

**關鍵函數**：
- `sop_generator.py:generate_sop_batch()` - 批次生成 SOP
- 使用 OpenAI API: `gpt-4o-mini`, temperature=0.7

---

#### 6.2 一般知識生成

**使用文件**：
```
services/knowledge_completion_loop/coordinator.py
  ↓ 函數：_generate_general_knowledge()
  ↓ 調用
services/knowledge_completion_loop/knowledge_generator.py
  ↓ 函數：generate_knowledge_batch()
  ↓ 調用 OpenAI API
```

**資料庫表**：
- `loop_generated_knowledge` (寫入待審核知識)

**關鍵函數**：
- `knowledge_generator.py:generate_knowledge_batch()` - 批次生成知識
- 使用 OpenAI API: `gpt-4o-mini`, temperature=0.7

---

### 第 7 步：人工審核

**使用文件**：
（人工操作，無程式文件）

**資料庫操作**：
- 查詢 `loop_generated_knowledge`
- 篩選 `review_status = 'pending'`
- 審核後更新為 `approved` 或 `rejected`
- 批准後同步到 `vendor_sop_items` 或 `knowledge_base`

---

### 第 8 步：檢查通過率並決定是否迭代

**使用文件**：
```
services/knowledge_completion_loop/coordinator.py
  ↓ 函數：run_iteration()
  ↓ 檢查 pass_rate < target_pass_rate (85%)
  ↓ 如果未達標且未超過最大迭代次數 (10)，重複步驟 1-7
```

**資料庫表**：
- `knowledge_completion_loops` (更新迴圈狀態)
- `loop_execution_logs` (記錄迭代事件)

**關鍵函數**：
- `coordinator.py:run_iteration()` - 執行單次迭代
- `coordinator.py:should_continue_loop()` - 判斷是否繼續迭代

---

## 📁 核心文件清單

### 入口文件

- `services/knowledge_completion_loop/run_first_loop.py`

### 核心協調器

- `services/knowledge_completion_loop/coordinator.py`

### 回測框架

- `scripts/backtest/backtest_framework_async.py`
- `services/backtest_service.py`

### 智能分類與聚類 ⭐ 修改處

- `services/knowledge_completion_loop/gap_classifier.py`
  - `get_clusters_for_generation()` [第 513-657 行]
  - `_cluster_by_category()` [新增]

### 知識生成器

- `services/knowledge_completion_loop/sop_generator.py`
- `services/knowledge_completion_loop/knowledge_generator.py`

### 配置文件

- `services/knowledge_completion_loop/cluster_rules.json`

---

## 🗄️ 資料庫表清單

### 迴圈管理

- `knowledge_completion_loops` - 迴圈記錄
- `loop_execution_logs` - 執行日誌
- `loop_generated_knowledge` - 生成的知識（待審核）

### 回測相關

- `test_scenarios` - 測試情境
- `backtest_results` - 測試結果

### 知識庫

- `vendor_sop_items` - SOP 項目
- `vendor_sop_categories` - SOP 分類
- `vendor_sop_groups` - SOP 群組
- `knowledge_base` - 一般知識庫

---

## 🔧 關鍵修改點

### gap_classifier.py 修改

**位置**：`services/knowledge_completion_loop/gap_classifier.py:513-657`

**修改內容**：
1. 新增 `_cluster_by_category()` 函數，支援按類別分別聚類
2. 修改 `get_clusters_for_generation()` 函數，按類別分離後再聚類

**原因**：
- SOP 知識和一般知識的聚類規則不同
- 避免過度聚類（將不同類型的知識強行合併）
- 提高知識生成的精準度

---

## 📊 資料流向圖

```
test_scenarios (approved)
      ↓
[執行回測] backtest_framework_async.py
      ↓
backtest_results (is_pass = false)
      ↓
[分析失敗] coordinator.py:analyze_failures()
      ↓
[AI 分類] gap_classifier.py:classify_gaps_batch()
      ↓
sop_knowledge / form_fill / system_config / api_query
      ↓
[按類別分離] gap_classifier.py:get_clusters_for_generation()
      ↓
sop_clusters + knowledge_clusters
      ↓
[生成知識] sop_generator.py / knowledge_generator.py
      ↓
loop_generated_knowledge (pending_review)
      ↓
[人工審核] 批准後同步到正式表
      ↓
vendor_sop_items / knowledge_base
      ↓
[重新回測] 驗證改善效果
```

---

## 🎯 Debug 參考

### 常見問題與排查

**問題 1：OpenAI API 調用失敗**
- 檢查文件：`gap_classifier.py`, `sop_generator.py`, `knowledge_generator.py`
- 檢查 API Key：環境變數 `OPENAI_API_KEY`
- 檢查重試機制：使用 `tenacity` 庫

**問題 2：聚類結果不符預期**
- 檢查文件：`gap_classifier.py:_cluster_by_category()`
- 檢查配置：`cluster_rules.json`
- 檢查分類結果：查詢 `loop_execution_logs` 表

**問題 3：知識生成後未同步**
- 檢查審核狀態：`loop_generated_knowledge.review_status`
- 檢查同步邏輯：`coordinator.py:_sync_approved_knowledge()`

---

## 📝 開發建議

### 修改程式碼時

1. **修改分類邏輯**：編輯 `gap_classifier.py:classify_gaps_batch()`
2. **修改聚類規則**：編輯 `cluster_rules.json`
3. **修改生成 Prompt**：編輯 `sop_generator.py` 或 `knowledge_generator.py`
4. **修改迭代邏輯**：編輯 `coordinator.py:run_iteration()`

### Code Review 時

- 檢查 ⭐ 標記的核心修改處
- 確認資料庫表的讀寫操作正確
- 驗證 OpenAI API 呼叫的 temperature 設定
- 檢查錯誤處理與重試機制

---

## 🔗 相關文件

- **執行指南**：`.kiro/steering/testing.md` - 如何執行回測、環境變數配置、新對話恢復流程
- **知識系統**：`.kiro/steering/knowledge.md` - 知識分類、資料表架構
- **AI 使用**：`.kiro/steering/ai-usage.md` - OpenAI 模型選擇、成本控制
- **技術棧**：`.kiro/steering/tech.md` - 技術架構、開發慣例
