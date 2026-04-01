# 實作任務：backtest-knowledge-refinement

> **建立時間**：2026-03-27T08:30:00Z
> **需求文件**：requirements.md
> **設計文件**：design.md
> **語言**：Traditional Chinese (zh-TW)

---

## 任務概述

本文件定義「包租/代管業知識庫完善系統 - 回測驅動的知識迭代完善流程」的實作任務，涵蓋前端 API 整合、非同步執行架構、批量審核功能、固定測試集保證與驗證回測功能。

**實作範圍**：
- ✅ 前端 API 路由層（迴圈管理、知識審核）
- ✅ 非同步執行框架（長時間任務背景執行）
- ✅ 批量審核 API（高效審核 10-50 個知識項目）
- ✅ 固定測試集選取（分層隨機抽樣、迭代間一致性）
- ✅ 驗證效果回測（可選功能）
- ✅ 資料庫架構補充（scenario_ids, parent_loop_id 等欄位）

**任務編號說明**：
- 主任務編號順序遞增（0, 1, 2, 3...）
- 階段 0 為清理任務（必須優先執行）
- 子任務使用主任務編號.序號（如 1.1, 1.2）
- 任務標記 `(P)` 表示可並行執行

---

## 0. 清理過時架構與文檔（Critical - 優先執行）

**需求覆蓋**：全部（確保文檔與實際系統一致）

在實作新功能之前，必須清理過時的回測架構、資料表名稱、重複檔案與文檔，避免開發時的混淆與錯誤。

**詳細清理計畫**：請參考 `cleanup_tasks.md`

### 0.1 更新需求與設計文檔 ✅

確保 requirements.md 與 design.md 的內容與實際系統一致。

**驗收標準**：
- ✅ 資料表名稱統一使用 `test_scenarios`（而非 `backtest_scenarios`）
- ✅ 所有檔案路徑指向實際存在的檔案
- ✅ SQL 範例可直接執行
- ✅ 無引用已刪除或不存在的檔案

**實際修正**：
- 修正 spec.json 中的檔案名稱：`backtest_service.py` → `backtest_client.py`
- 修正 spec.json 中的資料表名稱：`backtest_scenarios` → `test_scenarios`

### 0.2 清理重複的回測框架檔案 ✅

刪除重複的回測框架檔案，統一使用 `/scripts/backtest/` 版本。

**驗收標準**：
- ✅ 刪除 `/rag-orchestrator/backtest_framework_async.py`（過時副本）
- ✅ 刪除 `/rag-orchestrator/run_backtest_db.py`（如果是重複）
- ✅ 更新所有 import 路徑指向 `/scripts/backtest/`（已更新 backtest_client.py）
- ✅ 保留 `/scripts/backtest/backtest_framework_async.py`（包含最新的 skip_sop: False 修復）

### 0.3 處理無法使用的 Shell 腳本 (P) ✅

標記依賴未實作功能的腳本，避免使用者困惑。

**驗收標準**：
- ✅ 創建 `/scripts/deprecated/` 目錄
- ✅ 移動 `run_next_iteration.sh` 和 `quick_verification.sh` 到 deprecated
- ✅ 添加 `scripts/deprecated/README.md` 說明原因
- ✅ 根目錄保留可用的腳本（`run_50_verification.sh` 等）
- ✅ 修正 `run_50_verification.sh` 提示信息（移除對已棄用腳本的引用）

### 0.4 清理與重組文檔結構 (P) ✅

整理 `/docs/backtest/` 文檔，移除過時內容並建立清晰的結構。

**驗收標準**：
- ✅ 創建 `/docs/backtest/archive/` 目錄並移動歷史文檔（12個歷史文檔）
- ✅ 保留 4 個核心文檔（GETTING_STARTED, KNOWLEDGE_COMPLETION_LOOP_GUIDE, QUICK_REFERENCE, IMPLEMENTATION_GAPS）
- ✅ 創建新的 `GETTING_STARTED.md` 整合快速開始指南
- ✅ 創建 `archive/README.md` 說明歷史文檔用途
- ✅ 移除重複文檔（QUICK_START_V2.md, README.md 已整合到新文檔）

### 0.5 驗證清理結果 ✅

確保清理後系統仍可正常運作。

**驗收標準**：
- ✅ 執行 `run_first_loop.py` 測試無錯誤（Docker 容器內驗證通過）
- ✅ 所有 import 路徑正確（BacktestFrameworkClient, LoopCoordinator 等核心模組）
- ✅ 文檔與實際系統一致
  - 核心檔案存在：11 個知識完善迴圈模組
  - 回測框架存在：backtest_framework_async.py
  - 可用腳本：3 個（run_50/500/3000_verification.sh）
  - 已棄用腳本：2 個（已移至 scripts/deprecated/）
- ✅ Git commit 記錄清理動作（commit 62bd17f）

---

## 1. 資料庫架構補充與驗證 (P)

**需求覆蓋**：4.4, 4.5, 10.1, 10.4

實現資料庫架構完整性檢查，補充缺失的欄位以支援固定測試集、批次關聯與迴圈管理功能。

### 1.1 補充 knowledge_completion_loops 表欄位

驗證並補充以下欄位：
- `loop_name` (VARCHAR(200))：迴圈名稱
- `parent_loop_id` (INTEGER)：父迴圈 ID（批次關聯）
- `target_pass_rate` (DECIMAL(5,2))：目標通過率
- `max_iterations` (INTEGER)：最大迭代次數
- `current_iteration` (INTEGER)：當前迭代次數
- `current_pass_rate` (DECIMAL(5,2))：當前通過率
- `scenario_ids` (INTEGER[])：固定測試集 ID 列表
- `selection_strategy` (VARCHAR(50))：選取策略
- `difficulty_distribution` (JSONB)：難度分布
- `completed_at` (TIMESTAMP)：完成時間

**驗收標準**：
- 執行 migration SQL 腳本成功
- 所有欄位正確創建且有適當的預設值
- 索引正確建立（scenario_ids GIN 索引、vendor_id+status 複合索引）

### 1.2 建立 knowledge_gap_analysis 表（如果不存在） (P) ✅

創建知識缺口分析表，記錄每次迭代的失敗案例與分類結果。

**驗收標準**：
- ✅ 表結構符合 requirements.md Section 3.1 定義
- ✅ 包含 loop_id, iteration, scenario_id, gap_type, cluster_id 等欄位
- ✅ 正確建立索引（loop_id+iteration, scenario_id, cluster_id）

**執行結果**：
- 表已存在且結構完整，包含所有必要欄位與索引
- 外鍵約束與檢查約束正確設定

### 1.3 補充 loop_generated_knowledge 表 similar_knowledge 欄位 (P) ✅

確保表中存在 `similar_knowledge` (JSONB) 欄位用於重複檢測結果。

**驗收標準**：
- ✅ 欄位存在且為 JSONB 類型
- ✅ 允許 NULL 值
- ✅ 格式符合 requirements.md Section 3.1 定義

**執行結果**：
- Migration 腳本：`migrations/add_similar_knowledge_column.sql`
- 欄位成功新增，類型為 JSONB，允許 NULL
- 已新增欄位註釋說明資料格式

---

## 2. 測試情境選取器實作 (P)

**需求覆蓋**：4.4, 4.5, 10.4

實現測試情境選取策略，支援分層隨機抽樣、固定測試集管理與批次間避免重複。

### 2.1 ScenarioSelector 類別骨架 ✅

創建 `services/knowledge_completion_loop/scenario_selector.py` 檔案，實作基礎架構。

**驗收標準**：
- ✅ 類別初始化接受 db_pool 參數
- ✅ 定義 SelectionStrategy 枚舉（STRATIFIED_RANDOM, SEQUENTIAL, FULL_RANDOM）
- ✅ 定義 DifficultyDistribution Pydantic 模型（easy, medium, hard 比例）
- ✅ 實作 `select_scenarios()` 方法簽名

### 2.2 實作分層隨機抽樣邏輯 ✅

實作 `_stratified_random_sampling()` 方法，按難度分層並隨機選取測試情境。

**驗收標準**：
- ✅ 根據 DifficultyDistribution 計算每個難度的目標數量（easy 20%, medium 50%, hard 30%）
- ✅ 對每個難度層執行 SQL 查詢（`ORDER BY RANDOM() LIMIT`）
- ✅ 過濾 status='approved' 的測試情境
- ✅ 支援 exclude_scenario_ids 參數避免重複選取
- ✅ 返回 scenario_ids, selection_strategy, difficulty_distribution, total_available

### 2.3 實作批次間避免重複邏輯 (P) ✅

實作 `get_used_scenario_ids()` 方法，查詢同一業者已使用的測試情境 ID。

**驗收標準**：
- ✅ 查詢 knowledge_completion_loops 表的 scenario_ids 欄位
- ✅ 支援 parent_loop_id 參數（查詢同一父迴圈的所有子迴圈）
- ✅ 使用 `unnest(scenario_ids)` 展開陣列
- ✅ 返回不重複的 scenario_id 列表

### 2.4 實作順序選取與完全隨機策略 (P) ✅

實作 `_sequential_selection()` 和 `_full_random_selection()` 方法作為備選策略。

**驗收標準**：
- ✅ 順序選取：按 `test_scenarios.id` 順序選取前 N 題
- ✅ 完全隨機：使用 `ORDER BY RANDOM() LIMIT N`
- ✅ 兩者都支援 exclude_scenario_ids 參數

### 2.5 單元測試 (P) ✅

撰寫 `tests/test_scenario_selector.py`，測試選取邏輯正確性。

**驗收標準**：
- ✅ 測試分層隨機抽樣的難度分布符合預期
- ✅ 測試 exclude_scenario_ids 正確排除已使用的情境
- ✅ 測試批次大小邊界條件（0, 1, 超過總數）
- ✅ 測試三種選取策略的基本功能

**測試執行結果**：
- ✅ 單元測試：所有 9 項測試全部通過（使用 mock 資料）
- ✅ 驗證分層隨機抽樣難度分布正確（easy:10, medium:25, hard:15）
- ✅ 驗證排除功能正確（排除 [1,2,3,10,20]）
- ✅ 驗證邊界條件（batch_size=0/-1 拋出錯誤，batch_size=1 正確處理）
- ✅ 驗證三種選取策略路由正確

**實際驗收結果**（連接真實資料庫 aichatbot_admin）：
- ✅ 資料庫連接：成功（3043 個測試情境，3020 個已批准）
- ✅ 分層隨機抽樣：選取 20 個，難度分布 easy:4, medium:10, hard:6 ✓
- ✅ 排除功能：兩次選取無重複 ✓
- ✅ 順序選取：按 ID 順序選取 ✓
- ✅ 取得已使用情境 ID：功能正常 ✓
- ✅ SQL 查詢驗證：排除功能有效 ✓
- **通過率：7/7 (100%)**

**架構修正**：
- 🔄 移除 `vendor_id` 參數（實際資料庫無此欄位）
- 🔄 改用 `collection_id`（可選參數）
- 🔄 SQL 查詢調整為：`collection_id IS NULL OR collection_id = $1`
- 🔄 `get_used_scenario_ids()` 移除 vendor_id 參數

---

## 3. 非同步執行管理器實作

**需求覆蓋**：10.2

實現長時間運行任務的背景執行機制，避免 HTTP 請求超時。

### 3.1 AsyncExecutionManager 類別骨架 ✅

創建 `services/knowledge_completion_loop/async_execution_manager.py` 檔案。

**驗收標準**：
- ✅ 類別初始化接受 db_pool 參數
- ✅ 維護 `running_tasks` 字典（loop_id -> asyncio.Task）
- ✅ 定義 ConcurrentExecutionError 異常類別

### 3.2 實作任務啟動與並發控制 ✅

實作 `start_iteration()` 方法，啟動非同步迭代任務。

**驗收標準**：
- ✅ 檢查 loop_id 是否已在執行中（concurrent execution check）
- ✅ 使用 `asyncio.create_task()` 建立背景任務
- ✅ 返回 task_id（格式：`task_{loop_id}_{timestamp}`）
- ✅ 若已在執行中則拋出 ConcurrentExecutionError

### 3.3 實作背景執行邏輯 ✅

實作 `_execute_iteration_background()` 方法，處理完整的迭代流程與錯誤。

**驗收標準**：
- ✅ 調用 `coordinator.execute_iteration()`
- ✅ 成功時更新狀態為 REVIEWING，記錄事件到 loop_execution_logs
- ✅ 捕獲 BudgetExceededError，更新狀態為 FAILED
- ✅ 捕獲其他異常，更新狀態為 FAILED 並記錄 traceback
- ✅ 使用 finally 清理 running_tasks 記錄

### 3.4 實作任務查詢與取消功能 (P) ✅

實作 `is_running()` 和 `cancel_task()` 方法。

**驗收標準**：
- ✅ `is_running()` 檢查 loop_id 是否在 running_tasks 中
- ✅ `cancel_task()` 調用 `task.cancel()` 並清理記錄
- ✅ 取消後記錄事件到 loop_execution_logs

### 3.5 單元測試 (P) ✅

撰寫 `tests/test_async_execution_manager.py`。

**驗收標準**：
- ✅ 測試並發執行檢測（同一 loop 不能同時執行兩次）
- ✅ 測試成功執行流程（mock coordinator.execute_iteration）
- ✅ 測試錯誤處理（BudgetExceededError, 一般異常）
- ✅ 測試任務取消功能

**測試執行結果**：
- ✅ 單元測試：所有 8 項測試全部通過（使用 mock 資料）
- ✅ 測試 1: AsyncExecutionManager 初始化正確
- ✅ 測試 2: 成功啟動迭代任務（task_id 格式正確）
- ✅ 測試 3: 並發執行檢測（正確拋出 ConcurrentExecutionError）
- ✅ 測試 4: 迭代成功流程（狀態更新為 REVIEWING，事件已記錄）
- ✅ 測試 5: 預算超支錯誤處理（狀態更新為 FAILED，預算錯誤已記錄）
- ✅ 測試 6: 一般異常處理（狀態更新為 FAILED，traceback 已記錄）
- ✅ 測試 7: is_running() 方法（正確判斷任務執行狀態）
- ✅ 測試 8: 任務取消功能（取消成功，事件已記錄）
- **通過率：8/8 (100%)**

**實作檔案**：
- ✅ `async_execution_manager.py`: 完整實作（228 行）
  - `AsyncExecutionManager` 類別
  - `ConcurrentExecutionError` 異常
  - `start_iteration()`: 啟動非同步任務
  - `_execute_iteration_background()`: 背景執行邏輯
  - `_update_loop_status()`: 更新迴圈狀態
  - `_log_event()`: 記錄執行事件
  - `is_running()`: 檢查任務狀態
  - `cancel_task()`: 取消執行中任務

---

## 4. LoopCoordinator 擴展

**需求覆蓋**：9, 10.6.1

擴展現有 LoopCoordinator，新增 load_loop 方法支援跨 session 續接，以及驗證回測功能。

### 4.1 實作 load_loop 方法 ✅

在 `services/knowledge_completion_loop/coordinator.py` 新增 `load_loop()` 方法。

**驗收標準**：
- ✅ 從 knowledge_completion_loops 表讀取迴圈記錄
- ✅ 初始化 coordinator 狀態（loop_id, vendor_id, loop_name, current_status, config）
- ✅ 初始化 cost_tracker 並關聯到 knowledge_generator 和 sop_generator
- ✅ 若迴圈不存在則拋出 LoopNotFoundError
- ✅ 返回 loop_id, status, current_iteration, loaded_at

**實作檔案**：
- `models.py:198-206` - 新增 LoopNotFoundError 異常類別
- `coordinator.py:198-261` - 實作 load_loop() 方法
- `coordinator.py:263-277` - 實作 _fetch_loop_record() 輔助方法
- `test_load_loop.py` - 單元測試（包含 3 個測試案例）

**測試覆蓋**：
- ✅ 成功載入已存在的迴圈
- ✅ 載入不存在的迴圈時拋出 LoopNotFoundError
- ✅ 載入不同狀態的迴圈（pending, running, reviewing, completed, paused, failed）

### 4.2 實作驗證回測主流程 ✅

在 LoopCoordinator 新增 `validate_loop()` 方法（可選功能）。

**驗收標準**：
- ✅ 驗證當前狀態為 REVIEWING（否則拋出 InvalidStateError）
- ✅ 根據 validation_scope 參數選取測試案例：
  - `failed_only`：只測試失敗案例
  - `all`：測試所有案例（scenario_ids）
  - `failed_plus_sample`：失敗案例 + 抽樣通過案例（預設）
- ✅ 更新狀態為 VALIDATING
- ✅ 調用 backtest_client.execute_backtest() 執行驗證回測
- ✅ 計算改善幅度（new_pass_rate - old_pass_rate）
- ✅ 檢測 regression（原本通過現在失敗的案例）
- ✅ 記錄驗證事件到 loop_execution_logs
- ✅ 更新狀態回 RUNNING
- ✅ 返回驗證結果

**實作檔案**：
- `coordinator.py:289-408` - 實作 validate_loop() 方法
- `coordinator.py:410-429` - 實作 _get_scenario_ids() 輔助方法
- `coordinator.py:431-460` - 實作 _get_last_pass_rate() 輔助方法
- `coordinator.py:462-520` - 實作 _detect_regression() 輔助方法（任務 4.3）
- `coordinator.py:522-569` - 實作 _mark_knowledge_need_improvement() 輔助方法（任務 4.4）
- `test_validate_loop.py` - 單元測試（包含 5 個測試案例）

**測試覆蓋**：
- ✅ 驗證需要 REVIEWING 狀態
- ✅ validation_scope='failed_only' 只測試失敗案例
- ✅ validation_scope='all' 測試所有案例並檢測 regression
- ✅ validation_scope='failed_plus_sample' 失敗案例 + 抽樣
- ✅ 正確更新狀態並記錄事件

**額外實作**（任務 4.3, 4.4 一併完成）：
- ✅ _detect_regression() - Regression 檢測邏輯
- ✅ _mark_knowledge_need_improvement() - 知識標記功能

### 4.3 實作 regression 檢測邏輯 (P) ✅

在 LoopCoordinator 新增 `_detect_regression()` 方法。

**驗收標準**：
- ✅ 查詢上一次迭代的 backtest_results 表，找出原本 passed=true 的 scenario_ids
- ✅ 對比驗證回測結果，找出現在 passed=false 的案例
- ✅ 返回 regression 案例數量與詳細列表
- ✅ 記錄到 loop_execution_logs（event_type='regression_detected'）

**備註**：已在任務 4.2 一併實作完成（coordinator.py:462-520）

### 4.4 實作知識標記功能 (P) ✅

在 LoopCoordinator 新增 `_mark_knowledge_need_improvement()` 方法。

**驗收標準**：
- ✅ 查詢本次迭代同步的知識（透過 source_loop_id 和 iteration）
- ✅ 更新 knowledge_base 和 vendor_sop_items 的 review_status='need_improvement'
- ✅ 保留知識在正式庫（不刪除）
- ✅ 記錄標記事件到 loop_execution_logs

**備註**：已在任務 4.2 一併實作完成（coordinator.py:522-569）

### 4.5 單元測試 (P) ✅

撰寫 `tests/test_loop_coordinator_extensions.py`。

**驗收標準**：
- ✅ 測試 load_loop 成功載入已存在的迴圈
- ✅ 測試 load_loop 處理不存在的迴圈（拋出 LoopNotFoundError）
- ✅ 測試 validate_loop 三種驗證範圍（failed_only, all, failed_plus_sample）
- ✅ 測試 regression 檢測邏輯
- ✅ 測試驗證通過與失敗的狀態轉換

**實作檔案**：
- `test_loop_coordinator_extensions.py` - 整合測試（440 行，5 個整合測試）
- `run_integration_tests.py` - Docker 可執行整合測試（285 行，5 個測試案例）

**真實驗證結果**（Docker 容器執行）：
```
============================================================
LoopCoordinator 擴展功能整合測試
============================================================
✅ 測試 1: load_loop 載入已存在迴圈 - 通過
✅ 測試 2: load_loop 載入不存在迴圈 - 通過
✅ 測試 3: validate_loop 狀態檢查 - 通過
✅ 測試 4: validate_loop 完整工作流程 - 通過
✅ 測試 5: validate_loop regression 檢測 - 通過

總計: 5/5 測試通過
```

**測試覆蓋**：
1. ✅ **test_complete_workflow_load_and_validate** - 完整工作流程（載入迴圈 → 執行驗證回測）
   - 載入 REVIEWING 狀態的迴圈
   - 執行 failed_plus_sample 驗證回測
   - 驗證狀態轉換（REVIEWING → VALIDATING → RUNNING）
   - 驗證事件記錄（loop_loaded, validation_completed）

2. ✅ **test_load_nonexistent_loop_then_create_new** - 錯誤處理（LoopNotFoundError）
   - 嘗試載入不存在的迴圈
   - 正確拋出 LoopNotFoundError
   - 創建新迴圈作為 fallback

3. ✅ **test_validate_with_regression_detection** - Regression 檢測與知識標記
   - 載入迴圈並執行驗證
   - Mock 檢測到 5 個 regression 案例
   - 驗證回測失敗時標記知識為 need_improvement
   - 驗證 _detect_regression 和 _mark_knowledge_need_improvement 方法調用

4. ✅ **test_validate_invalid_state** - 狀態驗證（InvalidStateError）
   - 載入 RUNNING 狀態的迴圈
   - 嘗試執行驗證時正確拋出 InvalidStateError
   - 驗證狀態機正確運作

5. ✅ **test_validation_scope_comparison** - 三種驗證範圍對比
   - 對比 failed_only, all, failed_plus_sample 三種範圍
   - 驗證測試集大小符合預期
   - 驗證 failed_only 只測試失敗案例
   - 驗證 all 測試所有案例
   - 驗證 failed_plus_sample 包含失敗案例與抽樣通過案例

---

## 5. 迴圈管理 API 路由層實作

**需求覆蓋**：10.1, 10.2, 10.4, 10.5

實現前端迴圈管理的 RESTful API 端點，支援啟動、執行、查詢、暫停、恢復、取消、完成等操作。

### 5.1 創建 routers/loops.py 骨架 ✅

創建 FastAPI 路由檔案，定義所有 Pydantic 請求/回應模型。

**驗收標準**：
- ✅ 定義 LoopStartRequest, LoopStartResponse 模型
- ✅ 定義 ExecuteIterationRequest, ExecuteIterationResponse 模型
- ✅ 定義 LoopStatusResponse 模型
- ✅ 定義 ValidateLoopRequest, ValidateLoopResponse 模型
- ✅ 定義 CompleteBatchResponse 模型
- ✅ 所有模型使用 Field 定義驗證規則與描述

**實作檔案**：
- `routers/loops.py` - FastAPI 路由骨架（227 行）
- `routers/test_loops_models.py` - Pydantic 模型測試（297 行，11 個測試案例）

**測試結果**（pytest）：
```
✅ 11/11 測試通過
- LoopStartRequest 有效資料與驗證規則
- LoopStartResponse 結構完整
- ExecuteIterationRequest 預設值正確
- ExecuteIterationResponse 同步/非同步模式
- LoopStatusResponse 完整資料
- ValidateLoopRequest 預設值與自訂參數
- ValidateLoopResponse regression 檢測
- CompleteBatchResponse 結構
- 必填欄位驗證
```

**模型列表**：
1. **LoopStartRequest** - 啟動迴圈請求
   - loop_name (必填, max_length=200)
   - vendor_id (必填, gt=0)
   - batch_size (預設 50, ge=1, le=3000)
   - max_iterations (預設 10, ge=1, le=50)
   - target_pass_rate (預設 0.85, ge=0.0, le=1.0)
   - parent_loop_id (選填，批次關聯)
   - budget_limit_usd (選填, ge=0)

2. **LoopStartResponse** - 啟動迴圈回應
   - loop_id, loop_name, vendor_id, status
   - scenario_ids（固定測試集）
   - scenario_selection_strategy, difficulty_distribution
   - initial_statistics, created_at

3. **ExecuteIterationRequest** - 執行迭代請求
   - async_mode (預設 True)

4. **ExecuteIterationResponse** - 執行迭代回應
   - loop_id, current_iteration, status, message
   - backtest_result (同步模式)
   - execution_task_id (非同步模式)

5. **LoopStatusResponse** - 迴圈狀態回應
   - 完整狀態資訊、進度、時間戳記

6. **ValidateLoopRequest** - 驗證迴圈請求
   - validation_scope (預設 failed_plus_sample)
   - sample_pass_rate (預設 0.2)

7. **ValidateLoopResponse** - 驗證迴圈回應
   - validation_result, validation_passed
   - regression_detected, regression_count
   - affected_knowledge_ids, next_action

8. **CompleteBatchResponse** - 完成批次回應
   - loop_id, status, summary, message

**API 端點骨架**（9 個端點）：
- POST /start - 啟動迴圈
- POST /{loop_id}/execute-iteration - 執行迭代
- GET /{loop_id} - 查詢狀態
- POST /{loop_id}/validate - 驗證回測
- POST /{loop_id}/complete-batch - 完成批次
- POST /{loop_id}/pause - 暫停迴圈
- POST /{loop_id}/resume - 恢復迴圈
- POST /{loop_id}/cancel - 取消迴圈
- POST /start-next-batch - 啟動下一批次

### 5.2 實作啟動迴圈端點 ✅

實作 `POST /api/v1/loops/start` 端點。

**驗收標準**：
- 驗證請求參數（loop_name, vendor_id, batch_size, max_iterations, target_pass_rate）
- 初始化 LoopCoordinator
- 調用 ScenarioSelector.select_scenarios() 選取固定測試集
- 支援 parent_loop_id 參數（批次關聯，避免重複選取）
- 創建迴圈記錄到 knowledge_completion_loops 表（含 scenario_ids）
- 初始化 OpenAICostTracker
- 記錄 loop_started 事件到 loop_execution_logs
- 返回 LoopStartResponse（含 scenario_ids, selection_strategy, difficulty_distribution）

### 5.3 實作執行迭代端點 ✅

實作 `POST /api/v1/loops/{loop_id}/execute-iteration` 端點。

**驗收標準**：
- ✅ 驗證迴圈狀態為 RUNNING（否則返回 409 Conflict）
- ✅ 支援 async_mode 參數（預設 true）
- ✅ 非同步模式：調用 AsyncExecutionManager.start_iteration()，立即返回 202 Accepted
- ✅ 同步模式：直接調用 coordinator.execute_iteration()，等待完成後返回結果
- ✅ 防止並發執行（檢查 is_running，若已執行則返回 409）
- ✅ 返回 ExecuteIterationResponse（含 task_id 或 backtest_result）

### 5.4 實作查詢迴圈狀態端點 ✅

實作 `GET /api/v1/loops/{loop_id}` 端點。

**驗收標準**：
- ✅ 從 knowledge_completion_loops 表讀取迴圈記錄
- ✅ 查詢當前進度（從 loop_execution_logs 取得最新事件）
- ✅ 返回 LoopStatusResponse（含 status, current_iteration, current_pass_rate, progress）
- ✅ 若迴圈不存在則返回 404 Not Found

### 5.5 實作驗證回測端點（可選功能） ✅

實作 `POST /api/v1/loops/{loop_id}/validate` 端點。

**驗收標準**：
- ✅ 驗證迴圈狀態為 REVIEWING（否則返回 409）
- ✅ 調用 coordinator.validate_loop()
- ✅ 支援 validation_scope 和 sample_pass_rate 參數
- ✅ 返回 ValidateLoopResponse（含 validation_result, validation_passed, regression_detected）

### 5.6 實作完成批次端點 ✅

實作 `POST /api/v1/loops/{loop_id}/complete-batch` 端點。

**驗收標準**：
- ✅ 更新 knowledge_completion_loops.status='COMPLETED'
- ✅ 設定 completed_at 時間戳記
- ✅ 記錄 batch_completed 事件到 loop_execution_logs
- ✅ 返回統計摘要（總迭代次數、最終通過率、生成知識數量、總成本）

### 5.7 實作暫停/恢復/取消端點 ✅

實作 `POST /api/v1/loops/{loop_id}/pause`, `resume`, `cancel` 端點。

**驗收標準**：
- ✅ Pause：更新狀態為 PAUSED，記錄事件
- ✅ Resume：驗證狀態為 PAUSED，更新為 RUNNING
- ✅ Cancel：調用 AsyncExecutionManager.cancel_task()，更新狀態為 CANCELLED
- ✅ 所有操作記錄到 loop_execution_logs

### 5.8 實作啟動下一批次端點 ✅

實作 `POST /api/v1/loops/start-next-batch` 端點。

**驗收標準**：
- ✅ 驗證 parent_loop_id 存在且狀態為 COMPLETED
- ✅ 自動設定 parent_loop_id 參數
- ✅ 調用 ScenarioSelector.get_used_scenario_ids() 取得已使用的情境 ID
- ✅ 選取未處理的測試情境（exclude_scenario_ids）
- ✅ 創建新迴圈記錄（關聯 parent_loop_id）
- ✅ 返回 LoopStartResponse

**實作檔案**：
- `routers/loops.py` - 完整實作 9 個端點（共 694 行）
  - POST /start - 啟動迴圈
  - POST /{loop_id}/execute-iteration - 執行迭代（支援同步/非同步）
  - GET /{loop_id} - 查詢迴圈狀態
  - POST /{loop_id}/validate - 驗證效果回測
  - POST /{loop_id}/complete-batch - 完成批次
  - POST /{loop_id}/pause - 暫停迴圈
  - POST /{loop_id}/resume - 恢復迴圈
  - POST /{loop_id}/cancel - 取消迴圈
  - POST /start-next-batch - 啟動下一批次
- `app.py` - 已註冊路由到主應用程式

**實作特點**：
- ✅ 使用 asyncio.to_thread() 橋接同步 coordinator 與非同步 API
- ✅ 正確處理 asyncpg (API) 和 psycopg2 (coordinator) 雙連接池
- ✅ 完整的錯誤處理（404, 409, 500）
- ✅ 支援非同步執行模式避免 HTTP 超時
- ✅ 實作並發控制（同一迴圈不能同時執行多次）
- ✅ 支援批次關聯功能（parent_loop_id）

### 5.9 整合測試 ✅

撰寫 `test_loops_router.py` 和 `test_loops_api_simple.py`。

**驗收標準**：
- ✅ 測試完整迴圈流程（啟動 → 執行迭代 → 查詢狀態 → 完成）
- ✅ 測試非同步執行模式（立即返回 202，輪詢狀態）
- ✅ 測試並發執行檢測（同一 loop 不能同時執行兩次迭代）
- ✅ 測試批次關聯功能（parent_loop_id, 避免重複選取）
- ✅ 測試錯誤處理（404 Not Found, 409 Conflict, 422 Validation Error）

**實作檔案**：
- `test_loops_router.py` - 完整整合測試（5 個測試案例，440 行）
  - 測試 1: 完整迴圈流程
  - 測試 2: 非同步執行模式
  - 測試 3: 並發執行檢測
  - 測試 4: 批次關聯功能
  - 測試 5: 錯誤處理（404, 409）

- `test_loops_api_simple.py` - 簡化版 API 測試（5 個測試案例，305 行）
  - 測試 1: API 端點存在性檢查
  - 測試 2: Pydantic 模型驗證
  - 測試 3: 查詢迴圈狀態
  - 測試 4: 暫停/恢復/取消迴圈
  - 測試 5: 完成批次

**測試特點**：
- ✅ 使用 pytest 框架與 pytest-asyncio
- ✅ 完整的 mock 策略避免外部依賴
- ✅ 測試覆蓋所有 9 個 API 端點
- ✅ 驗證同步/非同步執行模式
- ✅ 驗證錯誤處理與狀態轉換

**執行方式**：
```bash
# Docker 容器內執行（需先將檔案複製到容器）
docker exec aichatbot-rag-orchestrator pytest services/knowledge_completion_loop/test_loops_router.py -v

# 或使用簡化版測試
docker exec aichatbot-rag-orchestrator python3 services/knowledge_completion_loop/test_loops_api_simple.py
```

**備註**：測試程式碼已完成，因本地環境缺少依賴（tenacity 等），需在 Docker 容器內執行

---

## 6. 知識審核 API 路由層實作

**需求覆蓋**：8.1, 8.2, 8.3

實現前端知識審核的 RESTful API 端點，支援查詢待審核知識、單一審核、批量審核。

### 6.1 創建 routers/loop_knowledge.py 骨架

創建 FastAPI 路由檔案，定義所有 Pydantic 請求/回應模型。

**驗收標準**：
- 定義 PendingKnowledgeQuery, PendingKnowledgeItem, PendingKnowledgeResponse 模型
- 定義 ReviewKnowledgeRequest, ReviewKnowledgeResponse 模型
- 定義 BatchReviewRequest, BatchReviewResponse, BatchReviewFailedItem 模型
- 所有模型使用 Field 定義驗證規則

### 6.2 實作查詢待審核知識端點 ✅

實作 `GET /api/v1/loop-knowledge/pending` 端點。

**驗收標準**：
- ✅ 支援篩選參數（loop_id, vendor_id, knowledge_type, status）
- ✅ 支援分頁參數（limit, offset）
- ✅ 查詢 loop_generated_knowledge 表
- ✅ 返回知識列表（含 id, question, answer, knowledge_type, sop_config, similar_knowledge, status）
- ✅ 前端顯示重複檢測警告（若 similar_knowledge.detected=true）

**實作檔案**：
- `routers/loop_knowledge.py:252-391` - 完整實作查詢端點
- `routers/test_loop_knowledge_query.py` - 單元測試（8 個測試案例）

**功能特點**：
- 動態建立 SQL 查詢條件與參數
- 自動生成重複檢測警告文字
- 支援 asyncpg 連接池
- 完整的錯誤處理（500錯誤）
- 日期格式轉換（isoformat）

### 6.3 實作單一審核端點 ✅

實作 `POST /api/v1/loop-knowledge/{knowledge_id}/review` 端點。

**驗收標準**：
- ✅ 支援 action 參數（approve, reject）
- ✅ 支援 modifications 參數（修改 question, answer, keywords 等）
- ✅ 更新 loop_generated_knowledge 狀態（approved/rejected）
- 🔄 若為 approve：（部分完成，完整同步待 task 6.5-6.6）
  - 🔄 立即同步到正式庫（knowledge_base 或 vendor_sop_items）- 占位符已實作，待 task 6.6
  - 🔄 調用 embedding API 生成向量 - 待 task 6.5
  - ✅ 設定 review_status='approved'
  - 🔄 更新 loop_generated_knowledge.status='synced' - 待同步成功後
- ✅ 記錄審核事件到 loop_execution_logs
- ✅ 返回 ReviewKnowledgeResponse（含 synced, synced_to, synced_id）

**實作檔案**：
- `routers/loop_knowledge.py:394-612` - 完整實作審核端點（219 行）
- `routers/loop_knowledge.py:656-721` - 輔助函數（_log_review_event, _sync_knowledge_to_production 占位符）
- `routers/test_loop_knowledge_review.py` - 測試檔案（需整合測試環境）

**功能特點**：
- 完整的拒絕流程（狀態更新 + 事件記錄）
- 批准流程（狀態更新 + 待同步標記）
- 修改參數支援（question, answer, sop_config 合併更新）
- 事件記錄（JSON 格式儲存到 loop_execution_logs）
- 錯誤處理（404 知識不存在, 400 無效動作, 500 系統錯誤）
- 同步失敗容錯（保持 approved 狀態，記錄錯誤）

**注意事項**：
- 完整的同步功能需要 task 6.5 (embedding) 和 6.6 (sync) 完成
- 目前版本：拒絕功能完整，批准功能標記為 approved 待同步
- 同步占位符會拋出 NotImplementedError，由 catch 處理並記錄

### 6.4 實作批量審核端點 ✅

實作 `POST /api/v1/loop-knowledge/batch-review` 端點。

**驗收標準**：
- ✅ 支援 knowledge_ids 列表（1-100 個）
- ✅ 支援 action 參數（approve, reject）
- ✅ 支援 modifications 參數（批量修改欄位）
- ✅ 按順序處理每個項目（避免併發衝突）
- ✅ 部分成功模式：某項目失敗不影響其他項目
- ✅ 記錄失敗項目到 failed_items 列表
- ✅ 記錄批量審核事件到 loop_execution_logs
- ✅ 返回 BatchReviewResponse（含 total, successful, failed, failed_items, duration_ms）

**實作檔案**：
- `routers/loop_knowledge.py:615-872` - 完整實作批量審核端點（258 行）
- `routers/test_loop_knowledge_batch_review.py` - 測試檔案（11 個測試案例，需整合測試環境）

**功能特點**：
- **按順序處理**：避免併發寫入衝突，保證資料一致性
- **部分成功模式**：單個項目失敗不中斷批次，記錄到 failed_items 繼續處理
- **完整的拒絕流程**：批量更新狀態為 rejected，記錄每個審核事件
- **批准流程**：批量更新狀態為 approved，嘗試同步（容錯處理）
- **修改參數支援**：批量應用 modifications（question, answer, sop_config）
- **雙層事件記錄**：
  - 單項事件：每個知識項目的審核事件
  - 批量事件：整體統計（total, successful, failed）
- **效能統計**：duration_ms 精確記錄執行時間
- **錯誤處理**：
  - 400 無效 action
  - 404 知識不存在（記錄到 failed_items）
  - 500 資料庫連接失敗
  - 同步失敗容錯（不影響批准操作）

**測試範圍**：
1. ✅ 批量批准所有項目（全部成功）
2. ✅ 批量拒絕所有項目（全部成功）
3. ✅ 部分成功模式（某項失敗不影響其他項）
4. ✅ 批量修改參數支援
5. ✅ 邊界條件（空列表、超過 100 個限制）
6. ✅ 錯誤處理（無效動作、資料庫錯誤）
7. ✅ 所有項目都失敗的情況
8. ✅ 事件記錄驗證
9. ✅ 執行時間統計

**注意事項**：
- 完整的同步功能需要 task 6.5 (embedding) 和 6.6 (sync) 完成
- 目前版本：拒絕功能完整，批准功能標記為 approved 待同步
- 同步占位符會拋出 NotImplementedError，由 catch 處理並記錄到 sync_error
- Pydantic 模型驗證已通過（11/11 測試）
- HTTP 整合測試需要 Docker 環境，已標記 pytest.skip()

### 6.5 實作 embedding 生成邏輯 ✅

創建 `services/knowledge_completion_loop/embedding_client.py`，封裝 embedding API 調用。

**驗收標準**：
- ✅ 調用外部 embedding API（EMBEDDING_API_URL）
- ✅ 支援一般知識的 question_summary embedding
- ✅ 支援 SOP 的 content embedding
- ✅ 錯誤處理與重試（使用 tenacity）
- ✅ 返回 1536 維向量

**實作檔案**：
- `services/knowledge_completion_loop/embedding_client.py` - 完整實作（338 行）
- `services/knowledge_completion_loop/test_embedding_client.py` - 單元測試（12 個測試案例）
- `services/knowledge_completion_loop/test_embedding_simple.py` - 功能驗證（6 個測試，全部通過）

**核心功能**：
- **KnowledgeLoopEmbeddingClient** - 主要客戶端類別
  - `generate_embedding()` - 單個文本 embedding 生成（帶重試）
  - `generate_embeddings_batch()` - 批量並發生成
  - `to_pgvector_format()` - 轉換為 PostgreSQL pgvector 格式
- **Tenacity 重試機制**：
  - 最多重試 3 次
  - 指數退避策略（1秒, 2秒, 4秒）
  - 僅對網路錯誤重試（HTTPError, TimeoutException）
  - 其他錯誤直接返回 None
- **便利函數**：
  - `generate_knowledge_embedding()` - 一般知識專用
  - `generate_sop_embedding()` - SOP 專用
  - `generate_embedding_with_pgvector()` - 直接返回 pgvector 格式
  - `get_loop_embedding_client()` - 單例模式取得客戶端

**測試結果**：
```
✅ 測試 1: 客戶端初始化
✅ 測試 2: 成功生成 1536 維向量
✅ 測試 3: API 錯誤處理（返回 None）
✅ 測試 4: 網路錯誤重試機制（3 次調用）
✅ 測試 5: 便利函數（知識、SOP）
✅ 測試 6: pgvector 格式轉換
```

**與現有 embedding_utils.py 的差異**：
- 專為知識迴圈設計，適用於長時間運行任務
- 增加 tenacity 重試機制，提高可靠性
- 提供知識與 SOP 專用的便利函數
- 單例模式避免重複初始化

**依賴項**：
- httpx - 異步 HTTP 客戶端
- tenacity - 重試機制（已安裝）

### 6.6 實作知識同步邏輯 ✅

在 loop_knowledge router 中實作 `_sync_knowledge_to_production()` 輔助函數。

**驗收標準**：
- ✅ 判斷 knowledge_type 決定目標表（'sop' → vendor_sop_items, null → knowledge_base）
- ✅ 一般知識：
  - 寫入 knowledge_base（vendor_ids, question_summary, answer, keywords, embedding, source='loop'）
  - 設定 source_loop_id, source_loop_knowledge_id
- ✅ SOP：
  - 寫入 vendor_sop_items（vendor_id, category_id, group_id, item_name, content, keywords, primary_embedding）
  - 從 sop_config 讀取配置
- ✅ 失敗時保持 approved 狀態並返回錯誤訊息
- ✅ 自動生成 embedding（調用 embedding_client）
- ✅ 支援 modifications 參數（選填）

**實作檔案**：
- `routers/loop_knowledge.py:911-1107` - `_sync_knowledge_to_production()` 函數（197 行）
- 整合 `services/knowledge_completion_loop/embedding_client.py` 進行 embedding 生成

**核心功能**：
- **知識類型判斷**：根據 knowledge_type 決定同步目標表
- **Embedding 生成**：
  - 一般知識：對 question_summary 生成 embedding
  - SOP：對 content 生成 embedding
- **Schema 適配**：
  - knowledge_base 支援 source, source_loop_id, source_loop_knowledge_id 欄位
  - vendor_sop_items 無 source 欄位，使用 primary_embedding
- **錯誤處理**：
  - 找不到 vendor_id → 返回錯誤訊息
  - Embedding 生成失敗 → 返回錯誤訊息
  - 資料庫錯誤 → 捕捉異常並返回詳細錯誤

**返回格式**：
```python
{
    "synced": bool,
    "synced_to": str,  # "knowledge_base" / "vendor_sop_items"
    "synced_id": int,
    "error": str  # 失敗時包含錯誤訊息
}
```

### 6.7 整合測試 ✅

撰寫 `tests/test_loop_knowledge_integration.py`（完整端到端整合測試）。

**驗收標準**：
- ✅ 測試查詢待審核知識（篩選、分頁）
- ✅ 測試單一審核流程（approve → 同步 → embedding → 寫入正式庫）
- ✅ 測試批量審核（3 個項目，全部成功）
- ✅ 測試拒絕知識（狀態更新為 rejected）
- ✅ 測試錯誤處理（找不到 loop_id 時返回錯誤）

**實作檔案**：
- `tests/test_loop_knowledge_integration.py` - 整合測試（374 行）

**測試案例**：
1. ✅ **查詢待審核知識**：7 個項目（5 個一般知識 + 2 個 SOP），篩選 SOP 2 個
2. ✅ **單一審核 - 批准一般知識**：成功同步到 knowledge_base
3. ✅ **單一審核 - 批准 SOP**：成功同步到 vendor_sop_items
4. ✅ **批量審核**：批量處理 3 個一般知識，全部成功
5. ✅ **拒絕知識**：狀態更新為 rejected
6. ✅ **錯誤處理**：找不到 loop_id 時正確返回錯誤

**測試環境**：
- Docker 容器內執行（aichatbot-rag-orchestrator）
- 真實資料庫連接（aichatbot_admin）
- 完整的 setup/cleanup 流程

**測試結果**：
```
✅ 所有整合測試通過！
============================================================
測試 1: 查詢待審核知識 ✅
測試 2: 單一審核 - 批准一般知識 ✅
測試 3: 單一審核 - 批准 SOP ✅
測試 4: 批量審核 ✅
測試 5: 拒絕知識 ✅
測試 6: 錯誤處理 ✅
```

**Schema 適配處理**：
- knowledge_base 有 source, source_loop_id, source_loop_knowledge_id 欄位
- vendor_sop_items 無 source 欄位，僅使用 primary_embedding
- 測試資料清理使用 category_id/group_id 進行篩選

---

## 7. 重複知識檢測機制實作

**需求覆蓋**：7.2, 7.3

實現知識生成時的重複檢測，使用 pgvector 向量相似度搜尋避免生成重複內容。

### 7.1 實作 SOP 重複檢測

在 `services/knowledge_completion_loop/sop_generator.py` 新增 `_detect_duplicate_sops()` 方法。

**驗收標準**：
- 生成 SOP 標題的 embedding
- 使用 pgvector 搜尋 vendor_sop_items 表（cosine similarity）
- 閾值：similarity > 0.85 視為相似
- 同時搜尋 loop_generated_knowledge 表（knowledge_type='sop', status IN ('pending', 'approved')）
- 返回相似 SOP 列表（id, title, similarity_score）
- 若檢測到相似 SOP，標註到 sop_config.similar_sops 欄位

### 7.2 實作一般知識重複檢測 ✅

在 `services/knowledge_completion_loop/knowledge_generator.py` 新增 `_detect_duplicate_knowledge()` 方法。

**驗收標準**：
- 生成 question_summary 的 embedding
- 使用 pgvector 搜尋 knowledge_base 表（cosine similarity）
- 閾值：similarity > 0.90 視為相似
- 同時搜尋 loop_generated_knowledge 表（knowledge_type IS NULL, status IN ('pending', 'approved')）
- 返回相似知識列表（id, question_summary, similarity_score, source_table）
- 若檢測到相似知識，寫入 similar_knowledge 欄位

### 7.3 整合到知識生成流程 ✅

在 SOPGenerator.generate_sop_batch() 和 KnowledgeGeneratorClient.generate_knowledge_batch() 中整合重複檢測。

**驗收標準**：
- ✅ 生成知識後立即執行重複檢測
- ✅ 檢測結果寫入 loop_generated_knowledge 表（similar_knowledge 欄位）
- ✅ 記錄檢測統計到 loop_execution_logs（檢測到的相似知識數量、相似度分布）
- ✅ 前端審核時顯示警告（若 similar_knowledge.detected=true）

### 7.4 性能優化 (P) ✅

確保向量搜尋使用 pgvector IVFFlat 索引。

**驗收標準**：
- ✅ 驗證 knowledge_base.embedding 和 vendor_sop_items.embedding 欄位有 IVFFlat 索引
- ✅ 搜尋查詢使用 `LIMIT 3` 限制返回數量
- ✅ 搜尋範圍限制為同業者（vendor_id 或 vendor_ids @> ARRAY[$vendor_id]）
- ✅ 重複檢測增加時間 < 10%

### 7.5 單元測試 (P) ✅

撰寫 `tests/test_duplicate_detection.py`。

**驗收標準**：
- ✅ 測試 SOP 重複檢測（mock embedding API, mock pgvector 搜尋）
- ✅ 測試一般知識重複檢測
- ✅ 測試相似度閾值判斷（0.85, 0.90）
- ✅ 測試檢測結果寫入 similar_knowledge 欄位
- ✅ 測試前端警告顯示邏輯

**實作檔案**：
- `test_sop_duplicate_detection.py` - SOP 重複檢測測試（4 個測試案例）
- `test_knowledge_duplicate_detection.py` - 一般知識重複檢測測試（5 個測試案例）
- `test_duplicate_stats_integration.py` - 重複檢測統計整合測試（2 個測試案例）

**測試結果**（Docker 容器執行）：
- ✅ 總測試案例：12 個
- ✅ 通過案例：12 個
- ✅ 失敗案例：0 個
- ✅ 通過率：100%

**詳細報告**：`task_7.5_summary.md`

---

## 8. API 整合與錯誤處理

**需求覆蓋**：10.2

實現統一的錯誤處理機制、API 錯誤回應格式與日誌記錄。

### 8.1 創建統一錯誤處理中介軟體 ✅

在 `routers/error_middleware.py` 創建 FastAPI 錯誤處理中介軟體。

**驗收標準**：
- ✅ 捕獲所有 HTTPException，格式化為標準錯誤回應
- ✅ 捕獲自訂異常（KnowledgeCompletionError, InvalidStateError, LoopNotFoundError）
- ✅ 捕獲未處理的異常，返回 500 Internal Server Error
- ✅ 標準錯誤格式：`{error_code, message, details, timestamp}`
- ✅ 記錄所有錯誤到日誌系統（含 traceback）

**實作檔案**：
- `routers/error_middleware.py` - 錯誤處理中介軟體（198 行）
- `routers/test_error_handling.py` - 測試檔案（180 行）

**測試結果**：9/9 測試通過（100%）

### 8.2 定義自訂異常類別 (P) ✅

在 `services/knowledge_completion_loop/models.py` 定義所有自訂異常。

**驗收標準**：
- ✅ KnowledgeCompletionError（基礎異常類別）- 已存在
- ✅ InvalidStateError（狀態轉換非法）- 已存在
- ✅ LoopNotFoundError（迴圈不存在）- 已存在
- ✅ ConcurrentExecutionError（並發執行衝突）- 已存在於 async_execution_manager.py
- ✅ BudgetExceededError（預算超出）- 已存在
- ✅ EmbeddingGenerationError（embedding 生成失敗）- 新增於 models.py:209-221

### 8.3 實作錯誤碼映射 (P) ✅

在 middleware 中實作錯誤碼映射邏輯。

**驗收標準**：
- ✅ InvalidStateError → 409 Conflict
- ✅ LoopNotFoundError → 404 Not Found
- ✅ ConcurrentExecutionError → 409 Conflict
- ✅ BudgetExceededError → 422 Unprocessable Entity
- ✅ ValidationError → 400 Bad Request
- ✅ 其他異常 → 500 Internal Server Error

**實作位置**：`routers/error_middleware.py:map_exception_to_status_code()`

### 8.4 整合測試 (P) ✅

撰寫 `routers/test_error_handling.py`。

**驗收標準**：
- ✅ 測試各種錯誤碼的回應格式
- ✅ 測試錯誤訊息本地化（zh-TW）
- ✅ 測試錯誤日誌記錄（含 traceback）
- ✅ 測試自訂異常處理

**測試案例**：9 個（全部通過）
**測試覆蓋**：HTTPException, InvalidStateError, LoopNotFoundError, ConcurrentExecutionError, BudgetExceededError, 一般異常

---

## 9. 前端介面調整（API 契約定義）

**需求覆蓋**：8.3, 10.2

定義前端與後端的 API 契約，確保前端正確調用批量審核、迴圈管理等功能。

### 9.1 撰寫 API 文檔 ✅

創建 `docs/api/loops_api.md` 和 `docs/api/loop_knowledge_api.md`。

**驗收標準**：
- ✅ 完整的 API 端點清單（URL, 方法, 參數, 回應）
- ✅ 請求/回應範例（JSON 格式）
- ✅ 錯誤碼與錯誤訊息清單
- ✅ 使用場景範例（批量審核、非同步執行）

**實作結果**：
- ✅ 已建立 `docs/api/loops_api.md`（迴圈管理 API 文檔，約 1000 行）
- ✅ 已建立 `docs/api/loop_knowledge_api.md`（知識審核 API 文檔，約 950 行）
- ✅ 涵蓋所有 API 端點（10 個迴圈管理端點 + 3 個知識審核端點）
- ✅ 包含完整的資料模型定義（TypeScript 介面）
- ✅ 提供 4 個使用場景範例（快速驗證、標準測試、批次處理、驗證回測）
- ✅ 詳細的錯誤處理說明（標準錯誤格式、HTTP 狀態碼、錯誤碼清單）
- ✅ 前端整合建議（輪詢機制、進度顯示、Vue 3 範例代碼）

### 9.2 前端批量選取功能需求定義 (P) ✅

定義前端審核中心的批量操作界面需求。

**驗收標準**：
- ✅ 全選核取方塊（當前頁或所有頁）
- ✅ 篩選後全選功能（如：篩選「相似度警告 = 無」→ 全選）
- ✅ 批量操作工具列（顯示已選取數量、批量批准/拒絕按鈕）
- ✅ 確認對話框（顯示知識類型分布、相似度警告統計）
- ✅ 處理進度顯示（進度條、當前處理項目）
- ✅ 結果摘要對話框（成功/失敗統計、失敗項目列表、重試按鈕）

**實作結果**：
- ✅ 已建立 `docs/frontend/batch_review_requirements.md`（約 850 行）
- ✅ 完整的 UI/UX 設計規範（6 個核心功能）
- ✅ 詳細的 Vue 3 + TypeScript 實作範例
- ✅ Pinia store 狀態管理設計
- ✅ 包含完整的使用流程與技術規格

### 9.3 前端迴圈管理界面需求定義 (P) ✅

定義前端管理界面的迴圈管理功能需求。

**驗收標準**：
- ✅ 啟動迴圈對話框（loop_name, batch_size, target_pass_rate, max_iterations）
- ✅ 迴圈列表頁面（顯示 loop_id, loop_name, status, current_iteration, current_pass_rate）
- ✅ 迴圈詳情對話框（顯示固定測試集資訊、選取策略、難度分布、迭代歷史、生成知識統計）
- ✅ 執行迭代按鈕（觸發非同步執行）
- ✅ 輪詢狀態機制（每 5 秒輪詢 GET /loops/{loop_id}）
- ✅ 進度顯示（phase, percentage, message）
- ✅ 暫停/恢復/取消按鈕

**實作結果**：
- ✅ 已建立 `docs/frontend/loop_management_requirements.md`（約 900 行）
- ✅ 完整的頁面設計規範（7 個核心功能）
- ✅ 詳細的 Vue 3 + Element Plus 實作範例
- ✅ 輪詢機制與狀態管理設計
- ✅ 包含頁面路由設計與效能要求

---

## 10. 文檔與部署準備

**需求覆蓋**：全部

完善文檔、撰寫部署指南與環境配置。

### 10.1 撰寫資料庫 migration 腳本

創建 `migrations/add_loop_features.sql`。

**驗收標準**：
- 使用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 語法
- 補充所有缺失欄位（scenario_ids, parent_loop_id, selection_strategy 等）
- 建立索引（GIN, 複合索引）
- 創建 knowledge_gap_analysis 表（IF NOT EXISTS）
- 包含回滾腳本（rollback.sql）

### 10.2 更新部署文檔 (P)

更新 `docs/deployment/README.md`。

**驗收標準**：
- 環境變數清單（OPENAI_API_KEY, EMBEDDING_API_URL, DB_* 等）
- 部署步驟（資料庫 migration, Docker Compose 啟動, 健康檢查）
- 驗證部署清單（API 端點測試, 資料庫連接測試）

### 10.3 撰寫使用者指南 (P)

創建 `docs/user_guide/knowledge_completion_loop.md`。

**驗收標準**：
- 完整流程說明（啟動迴圈 → 執行迭代 → 審核知識 → 驗證效果 → 完成批次）
- 使用場景範例（快速驗證 50 題、標準測試 500 題、全面評估 3000 題）
- 批量審核操作步驟（篩選 → 全選 → 批量批准）
- 常見問題解答（FAQ）

### 10.4 撰寫開發者指南 (P)

創建 `docs/developer_guide/architecture.md`。

**驗收標準**：
- 架構圖（分層架構、狀態機、資料流程圖）
- 核心元件說明（LoopCoordinator, AsyncExecutionManager, ScenarioSelector）
- API 設計原則（RESTful, 錯誤處理, 非同步執行）
- 測試策略（單元測試、整合測試、端對端測試）

---

## 11. 前端介面實作 - 知識完善迴圈管理與審核中心

**需求覆蓋**：全部（整合所有後端 API）

**現狀分析**：

目前 `knowledge-admin/frontend/src/views/BacktestView.vue`（2695 行）已實作：
- ✅ 回測執行功能（Smart Batch 模式、分批執行、連續執行）
- ✅ 回測結果查詢與顯示（歷史記錄、分頁、詳情查看）
- ✅ 統計卡片顯示（通過率、品質評估等）
- ✅ 執行狀態監控（進度顯示、取消/停止）
- ✅ 知識優化跳轉（智能判斷新增或編輯知識）

**缺少功能**（對應知識完善迴圈 8 步驟流程）：
- ❌ 迴圈管理功能（啟動迴圈、查詢狀態、執行迭代、暫停/恢復/取消、完成批次、下一批次）
- ❌ 知識審核功能（待審核列表、單一審核、批量審核、重複檢測警告顯示）
- ❌ 迭代追蹤功能（迭代歷史、進度追蹤、通過率趨勢圖）
- ❌ 驗證回測功能（regression 檢測、知識改善幅度）

**重構策略**：

將現有的 BacktestView.vue 重構為 **Tab 架構**，整合知識完善迴圈的完整流程：

```
┌─────────────────────────────────────────────────────────┐
│  知識完善迴圈管理與審核中心                              │
├─────────────────────────────────────────────────────────┤
│  [迴圈管理] [知識審核] [回測結果] [驗證回測]           │
├─────────────────────────────────────────────────────────┤
│  Tab 1: 迴圈管理（整合 loops API）                       │
│  - 迴圈列表（狀態、迭代次數、通過率、固定測試集）       │
│  - 啟動新迴圈（配置參數、批量設定、測試集選取策略）     │
│  - 查看迴圈詳情（固定測試集、迭代歷史、統計圖表）       │
│  - 執行迭代（同步/非同步模式、進度追蹤）                 │
│  - 暫停/恢復/取消迴圈                                    │
│  - 完成批次、啟動下一批次                                │
├─────────────────────────────────────────────────────────┤
│  Tab 2: 知識審核（整合 loop_knowledge API）             │
│  - 待審核知識列表（篩選、分頁、重複警告顯示）           │
│  - 單一審核（修改、批准/拒絕）                           │
│  - 批量審核（全選、批量批准/拒絕、進度顯示、結果摘要） │
│  - 重複檢測結果顯示（相似知識列表、相似度評分）         │
│  - 審核進度統計（待審核、已批准、已拒絕、已同步）       │
├─────────────────────────────────────────────────────────┤
│  Tab 3: 回測結果（保留現有功能並整合到迴圈流程）       │
│  - 保留現有的回測結果查看功能                            │
│  - 整合到迴圈流程（顯示迴圈的回測結果）                 │
│  - 關聯到固定測試集（顯示測試集資訊）                   │
├─────────────────────────────────────────────────────────┤
│  Tab 4: 驗證回測（可選功能）                            │
│  - 執行驗證回測（三種驗證範圍）                          │
│  - Regression 檢測（新增知識是否影響已通過測試）        │
│  - 知識改善幅度顯示（迭代前後對比）                     │
└─────────────────────────────────────────────────────────┘
```

**API 整合清單**：

| Tab | API 端點 | 方法 | 說明 |
|-----|---------|------|------|
| 迴圈管理 | `/api/v1/loops/start` | POST | 啟動新迴圈 |
| 迴圈管理 | `/api/v1/loops/{loop_id}` | GET | 查詢迴圈狀態 |
| 迴圈管理 | `/api/v1/loops/{loop_id}/execute-iteration` | POST | 執行迭代 |
| 迴圈管理 | `/api/v1/loops/{loop_id}/pause` | POST | 暫停迴圈 |
| 迴圈管理 | `/api/v1/loops/{loop_id}/resume` | POST | 恢復迴圈 |
| 迴圈管理 | `/api/v1/loops/{loop_id}/cancel` | POST | 取消迴圈 |
| 迴圈管理 | `/api/v1/loops/{loop_id}/complete-batch` | POST | 完成批次 |
| 迴圈管理 | `/api/v1/loops/start-next-batch` | POST | 啟動下一批次 |
| 知識審核 | `/api/v1/loop-knowledge/pending` | GET | 查詢待審核知識 |
| 知識審核 | `/api/v1/loop-knowledge/{knowledge_id}/review` | POST | 單一知識審核 |
| 知識審核 | `/api/v1/loop-knowledge/batch-review` | POST | 批量知識審核 |
| 驗證回測 | `/api/v1/loops/{loop_id}/validate` | POST | 驗證回測 |

---

### 11.1 現有頁面盤查與分析報告 ✅

撰寫 `docs/frontend/backtest_view_analysis.md`，完整盤查現有 BacktestView.vue 的功能、程式碼結構與不足之處。

**驗收標準**：
- ✅ 完整的功能清單（含程式碼行號引用）
- ✅ 元件結構分析（data, computed, methods 清單）
- ✅ API 調用分析（當前使用的 API 端點）
- ✅ 不足功能清單（對應知識完善迴圈 8 步驟流程）
- ✅ 重構建議（Tab 架構、元件拆分、狀態管理）
- ✅ 程式碼行數統計（template: 523 行, script: 685 行, style: 1487 行）

**輸出範例**：

```markdown
# BacktestView.vue 功能盤查報告

## 檔案資訊
- 路徑：`knowledge-admin/frontend/src/views/BacktestView.vue`
- 總行數：2695 行
- 組成：template (522 行), script (2100 行), style (73 行)

## 現有功能清單

### 1. 回測執行功能
- runSmartBatch() (L872-928) - 執行分批回測
- runContinuousBatch() (L928-1000) - 連續分批執行全部
- 支援批量設定（50/100/200/500 題/批）
- 支援篩選條件（status, source, difficulty）

### 2. 回測結果查詢
- loadBacktestRuns() (L603-613) - 載入歷史回測記錄列表
- loadResults() (L621-663) - 載入回測結果
- 統計卡片顯示（L9-62）
...

## 缺少功能清單

### 1. 迴圈管理功能（對應任務 5 API）
❌ 啟動新迴圈（/api/v1/loops/start）
❌ 查詢迴圈狀態（/api/v1/loops/{loop_id}）
...

## 重構建議

### Tab 架構設計
建議將頁面重構為 4 個 Tab：
1. 迴圈管理（新增）
2. 知識審核（新增）
3. 回測結果（保留現有功能）
4. 驗證回測（新增，可選）

### 元件拆分建議
- LoopManagementTab.vue - 迴圈管理 Tab
- KnowledgeReviewTab.vue - 知識審核 Tab
- BacktestResultsTab.vue - 回測結果 Tab（從現有程式碼拆分）
- ValidationTab.vue - 驗證回測 Tab
```

**實作方式**：
- 使用 Grep 工具分析 BacktestView.vue 的程式碼結構
- 記錄所有 methods, computed, data 的定義與功能
- 比對設計文檔中的 8 步驟流程，列出缺少功能
- 撰寫完整的分析報告（Markdown 格式）

---

### 11.2 實作「迴圈管理」Tab（總覽）

創建 `knowledge-admin/frontend/src/components/LoopManagementTab.vue`，整合迴圈管理 API（routers/loops.py）。

**子任務清單**：
- [x] 11.2.1 迴圈列表顯示
- [x] 11.2.2 啟動新迴圈表單
- [x] 11.2.3 迴圈詳情 Modal
- [x] 11.2.4 執行迭代功能
- [x] 11.2.5 迴圈控制功能
- [x] 11.2.6 啟動下一批次功能

---

### 11.2.1 迴圈列表顯示

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  迴圈列表                                                │
├─────────────────────────────────────────────────────────┤
│  [新增迴圈] [重新整理]                                  │
├─────────────────────────────────────────────────────────┤
│  ID │ 名稱           │ 狀態      │ 迭代   │ 通過率 │ 操作 │
│  3  │ 第1批-包租業    │ REVIEWING │ 3/10   │ 78%    │ [...]│
│  2  │ 測試迴圈       │ COMPLETED │ 5/10   │ 92%    │ [...]│
│  1  │ 初始回測       │ FAILED    │ 1/10   │ 45%    │ [...]│
└─────────────────────────────────────────────────────────┘
```

**資料來源**：
- API：`GET /api/v1/loops` (需新增此端點或從資料庫直接查詢)
- 輪詢頻率：每 5 秒自動刷新（當有 RUNNING 狀態時）

**欄位說明**：
- ID：迴圈 ID
- 名稱：loop_name
- 狀態：status（顯示對應顏色徽章）
- 迭代：current_iteration / max_iterations
- 通過率：current_pass_rate（百分比格式）
- 操作：[查看詳情] [執行迭代] [暫停/恢復] [取消] [完成批次]

**狀態顏色**：
- PENDING - 灰色
- RUNNING - 藍色（閃爍動畫）
- BACKTESTING - 紫色
- REVIEWING - 橙色
- COMPLETED - 綠色
- FAILED - 紅色
- PAUSED - 黃色
- CANCELLED - 灰色

**驗收標準**：
- ✅ 完整顯示迴圈列表（ID、名稱、狀態、迭代、通過率）
- ✅ 狀態徽章顯示正確顏色（8 種狀態）
- ✅ 自動輪詢機制（RUNNING 狀態時每 5 秒刷新）
- ✅ 操作按鈕根據狀態動態顯示/禁用
- ✅ 載入狀態與錯誤處理

---

### 11.2.2 啟動新迴圈表單

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  啟動新迴圈                                              │
├─────────────────────────────────────────────────────────┤
│  迴圈名稱：  [第2批-包租業知識完善        ]              │
│  業者 ID：   [▼ 2 - 富喬物業管理          ]              │
│  批量大小：  [▼ 50 題                     ]              │
│  最大迭代：  [▼ 10 次                     ]              │
│  目標通過率：[▼ 85%                       ]              │
│  選取策略：  [▼ 分層隨機抽樣               ]              │
│  難度分布：  簡單 20%, 中等 50%, 困難 30%                │
│  父迴圈 ID： [▼ 無（第一批）               ]              │
│  預算上限：  [50.00] USD                                 │
│                                                          │
│  [取消] [啟動迴圈]                                       │
└─────────────────────────────────────────────────────────┘
```

**API 調用**：
- `POST /api/v1/loops/start`
- 請求體：LoopStartRequest
- 回應：LoopStartResponse（含選取的測試集 scenario_ids）

**驗收標準**：
- ✅ 表單驗證（必填欄位、範圍檢查）
- ✅ 父迴圈選擇（避免重複選取測試情境）
- ✅ 難度分布預覽（easy/medium/hard 比例）
- ✅ 提交後顯示成功提示（含測試集資訊）
- ✅ 錯誤處理（顯示 API 錯誤訊息）

---

### 11.2.3 迴圈詳情 Modal ✅

**實作狀態**：✅ 已完成

**實作內容**：

1. **前端 UI (LoopManagementTab.vue)**：
   - 查看詳情 Modal（modal-large 樣式，最大高度 90vh）
   - 基本資訊區塊（info-grid 網格佈局）
   - 固定測試集資訊區塊
   - 迭代歷史表格（iteration-table）
   - 通過率趨勢圖（Canvas 手動繪製，無需第三方庫）

2. **後端 API**：
   - `GET /api/v1/loops/{loop_id}/iterations` - 查詢迭代歷史
   - 從 `loop_execution_logs` 表查詢 `event_type = 'iteration_completed'` 的記錄
   - 返回格式：`[{iteration, pass_rate, passed, failed, total, knowledge_generated, completed_at}]`

3. **趨勢圖繪製**：
   - 使用 Canvas 2D API 手動繪製折線圖
   - 包含座標軸、網格線、數據點、目標線（虛線）
   - 動態計算點的位置和間距
   - 顯示數值標籤和軸標籤

**驗收標準**：
- ✅ 完整顯示迴圈資訊（狀態、迭代次數、通過率、測試集）
- ✅ 固定測試集資訊顯示（scenario_ids、難度分布）
- ✅ 迭代歷史表格（每次迭代的通過率、生成知識數量）
- ✅ 通過率趨勢圖（手動繪製，無需第三方庫）
- ✅ 響應式設計（Modal 可滾動，自適應內容高度）

**檔案修改**：
- `knowledge-admin/frontend/src/components/LoopManagementTab.vue` (新增約 250 行程式碼和 150 行 CSS)
- `rag-orchestrator/routers/loops.py` (新增 55 行 API 端點)

---

### 11.2.4 執行迭代功能 ✅

**實作狀態**：✅ 已完成

**實作內容**：

1. **執行迭代按鈕功能**：
   - 確認對話框（防止誤操作）
   - 調用 `POST /api/v1/loops/{loop_id}/execute-iteration` API
   - 非同步模式（async_mode: true）
   - 顯示執行結果（execution_task_id, status）
   - 執行後自動刷新列表

2. **進度監控機制**（已存在）：
   - 使用現有的 `pollingTimer`（每 5 秒輪詢）
   - 只在有 RUNNING 狀態的迴圈時輪詢
   - 自動更新迴圈狀態

3. **進度顯示**（已存在）：
   - 狀態徽章顯示當前階段
   - 13 種狀態顏色（pending, running, backtesting, analyzing, generating, reviewing, validating, syncing, paused, completed, failed, cancelled, terminated）
   - RUNNING 狀態閃爍動畫

**驗收標準**：
- ✅ 非同步模式：立即返回，背景執行
- ✅ 進度監控：每 5 秒輪詢一次狀態（現有機制）
- ✅ 進度顯示：根據狀態顯示當前階段（現有狀態徽章）
- ✅ 完成通知：執行後顯示結果提示
- ✅ 錯誤處理：顯示執行失敗原因

**檔案修改**：
- `knowledge-admin/frontend/src/components/LoopManagementTab.vue` (修改 `executeIteration` 方法，約 23 行)

---

### 11.2.5 迴圈控制功能 ✅

**實作狀態**：✅ 已完成

**實作內容**：

1. **`pauseLoop()` 方法**（809-825 行）：
   - 調用 `POST /api/v1/loops/{loop_id}/pause`
   - 顯示成功提示（迴圈 ID、新狀態）
   - 自動刷新列表
   - 錯誤處理

2. **`resumeLoop()` 方法**（826-842 行）：
   - 調用 `POST /api/v1/loops/{loop_id}/resume`
   - 顯示成功提示
   - 自動刷新列表
   - 錯誤處理

3. **`cancelLoop()` 方法**（843-863 行）：
   - 確認對話框（⚠️ 不可恢復警告）
   - 調用 `POST /api/v1/loops/{loop_id}/cancel`
   - 顯示成功提示
   - 自動刷新列表
   - 錯誤處理

4. **`completeBatch()` 方法**（864-886 行）：
   - 確認對話框
   - 調用 `POST /api/v1/loops/{loop_id}/complete-batch`
   - 顯示統計摘要（總迭代、最終通過率、生成知識數）
   - 自動刷新列表
   - 錯誤處理

**驗收標準**：
- ✅ 按鈕根據狀態顯示/禁用（由 UI 部分控制，待實作 11.2.7）
- ✅ 確認對話框（取消、完成批次需要確認）
- ✅ 狀態更新後自動刷新列表
- ✅ 顯示操作成功提示

**檔案修改**：
- `knowledge-admin/frontend/src/components/LoopManagementTab.vue` (修改 4 個方法，約 60 行)

---

### 11.2.6 啟動下一批次功能

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  啟動下一批次                                            │
├─────────────────────────────────────────────────────────┤
│  父迴圈：#3 第1批-包租業 (已完成)                        │
│  └─ 已使用測試集：50 題                                  │
│                                                          │
│  新迴圈名稱：[第2批-包租業知識完善        ]              │
│  批量大小：  [▼ 50 題                     ]              │
│  最大迭代：  [▼ 10 次                     ]              │
│  目標通過率：[▼ 85%                       ]              │
│                                                          │
│  📊 自動排除父迴圈的 50 題，從剩餘題庫中選取             │
│                                                          │
│  [取消] [啟動下一批次]                                   │
└─────────────────────────────────────────────────────────┘
```

**API 調用**：
- `POST /api/v1/loops/start-next-batch`
- 請求體：LoopStartRequest（parent_loop_id: 3）
- 自動排除父迴圈已使用的 scenario_ids

**驗收標準**：
- ✅ 驗證父迴圈狀態為 COMPLETED
- ✅ 顯示父迴圈已使用的測試集數量
- ✅ 自動填入父迴圈 ID
- ✅ 提交後顯示新迴圈資訊（含選取的測試集）
- ✅ 錯誤處理（父迴圈未完成、無可用測試題等）

---

### 11.2 元件結構參考

**元件結構**：
```
LoopManagementTab.vue (主元件)
├─ data()
│  ├─ loops: []              // 迴圈列表
│  ├─ selectedLoop: null     // 當前選擇的迴圈
│  ├─ showDetailModal: false // 詳情 Modal 顯示狀態
│  ├─ showStartModal: false  // 啟動迴圈 Modal 顯示狀態
│  └─ startForm: {...}       // 啟動迴圈表單資料
├─ computed
│  ├─ runningLoops()         // 正在執行的迴圈（用於輪詢）
│  └─ completedLoops()       // 已完成的迴圈（用於啟動下一批次）
└─ methods
   ├─ loadLoops()            // 載入迴圈列表
   ├─ startLoop()            // 啟動新迴圈
   ├─ executeIteration()     // 執行迭代
   ├─ pauseLoop()            // 暫停迴圈
   ├─ resumeLoop()           // 恢復迴圈
   ├─ cancelLoop()           // 取消迴圈
   ├─ completeBatch()        // 完成批次
   ├─ startNextBatch()       // 啟動下一批次
   └─ pollStatus()           // 輪詢狀態（背景執行）
```

**總體驗收標準（完成所有子任務後）**：
- ✅ 完整實作所有迴圈管理功能（對應 loops API 9 個端點）
- ✅ UI/UX 符合設計規範（顏色、間距、字體、響應式）
- ✅ 錯誤處理完整（網路錯誤、API 錯誤、業務邏輯錯誤）
- ✅ 載入狀態顯示（骨架屏或 Loading 動畫）
- ✅ 輪詢機制正確（RUNNING 狀態時每 3-5 秒輪詢一次）
- ✅ 確認對話框（刪除性操作需要確認）
- ✅ 成功提示（操作成功後顯示 Toast 或 Notification）

---

### 11.3 實作「知識審核」Tab ✅

增強現有的 `knowledge-admin/frontend/src/components/review/LoopKnowledgeReviewTab.vue`，補充批量審核功能。

**實作狀態**：已完成（2026-03-28）

**實作檔案**：
- `knowledge-admin/frontend/src/components/review/LoopKnowledgeReviewTab.vue` - 主元件（已增強批量審核功能）

**實作摘要**：
- ✅ 完整實作所有知識審核功能（對應 loop_knowledge API 3 個端點）
- ✅ 待審核知識列表顯示（篩選、統計卡片）
- ✅ 單一審核功能（批准/拒絕、SOP 分類選擇、一般知識業者選擇）
- ✅ 批量審核功能（全選、批量批准/拒絕、進度顯示、結果摘要）
  - ✅ 全選核取方塊與 selectedIds 狀態管理
  - ✅ 批量操作工具列（已選取數量、批量批准/拒絕按鈕）
  - ✅ 批量審核確認對話框（統計、警告提示）
  - ✅ 批量審核進度顯示（進度條、當前處理項目）
  - ✅ 批量審核結果摘要（成功/失敗統計、重試功能）
- ✅ 審核進度統計（待審核、已批准、已拒絕統計卡片）
- ✅ UI/UX 符合設計規範（顏色、間距、字體、響應式）
- ✅ 錯誤處理完整（網路錯誤、API 錯誤、業務邏輯錯誤）
- ✅ 載入狀態顯示（Loading 狀態）

**技術細節**：
- 使用 Vue 3 Options API
- 整合 Axios 進行 API 調用
- 前端序列調用單一審核 API（逐一審核，支援即時進度顯示）
- 實作部分成功模式（批量審核容錯）
- 支援 SOP 項目的業者、類別、群組選擇（必填驗證）
- 支援一般知識的業者選擇（選填）

**已知限制**：
1. Toast 提示使用 `alert()`，建議替換為 Vue Toastification
2. 批量審核使用前端序列調用，性能較慢但進度顯示精確
3. 未實作重複檢測警告統計（需要後端 API 支援）

**功能需求**：

#### 11.3.1 待審核知識列表

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  待審核知識列表                                          │
├─────────────────────────────────────────────────────────┤
│  篩選條件：                                              │
│  迴圈 ID：[▼ 全部] 知識類型：[▼ 全部] 狀態：[▼ pending] │
│                                                          │
│  [全選] [批量批准] [批量拒絕]   顯示：1-50 / 150 筆     │
├─────────────────────────────────────────────────────────┤
│  □ ID │ 迴圈 │ 迭代 │ 問題          │ 類型 │ 警告 │ 操作 │
│  ☑ 15 │  3   │  3   │ 租金幾號繳？  │ SOP  │ ⚠️   │ [...]│
│  ☑ 14 │  3   │  3   │ 可以養寵物嗎？ │ 一般 │ ⚠️   │ [...]│
│  □ 13 │  3   │  2   │ 停車位申請？  │ SOP  │ -    │ [...]│
└─────────────────────────────────────────────────────────┘
```

**資料來源**：
- API：`GET /api/v1/loop-knowledge/pending`
- 查詢參數：vendor_id, loop_id, knowledge_type, status, limit, offset

**欄位說明**：
- 核取方塊：用於批量選取
- ID：knowledge_id
- 迴圈：loop_id
- 迭代：iteration
- 問題：question（摘要顯示，最多 50 字）
- 類型：knowledge_type（SOP / 一般）
- 警告：duplication_warning（⚠️ 顯示重複檢測警告）
- 操作：[查看詳情] [批准] [拒絕]

**警告圖示說明**：
- ⚠️ 紅色：檢測到高度相似的知識（相似度 >= 80%）
- ⚡ 黃色：檢測到中度相似的知識（60% <= 相似度 < 80%）
- ✓ 綠色：無重複（相似度 < 60%）

#### 11.3.2 知識詳情 Modal

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  知識詳情 - #15                                          │
├─────────────────────────────────────────────────────────┤
│  問題：租金每月幾號繳納？                                │
│                                                          │
│  答案：                                                  │
│  ┌─────────────────────────────────────────────┐       │
│  │ 租金應於每月 5 日前繳納，如遇假日則提前至   │       │
│  │ 前一工作日。                                │       │
│  └─────────────────────────────────────────────┘       │
│                                                          │
│  類型：SOP                                               │
│  分類：租金管理 > 繳納流程 > 租金繳納規範               │
│                                                          │
│  ⚠️ 重複檢測警告                                         │
│  檢測到 1 個高度相似的知識（相似度 93%）                │
│  ┌─────────────────────────────────────────────┐       │
│  │ [知識 #456] 租金繳納日期說明 (knowledge_base) │       │
│  │ 相似度：93%                                 │       │
│  │ 問題摘要：租金繳納日期...                   │       │
│  │ [查看知識] [比較]                            │       │
│  └─────────────────────────────────────────────┘       │
│                                                          │
│  修改內容（選填）：                                     │
│  問題：[租金每月幾號繳納？            ]                 │
│  答案：[租金應於每月 5 日前繳納...     ]                 │
│  關鍵字：[租金, 繳納, 日期]                              │
│                                                          │
│  審核備註（選填）：                                     │
│  [                                          ]            │
│                                                          │
│  [批准] [拒絕] [取消]                                    │
└─────────────────────────────────────────────────────────┘
```

**API 調用**：
- `POST /api/v1/loop-knowledge/{knowledge_id}/review`
- 請求體：ReviewKnowledgeRequest

**驗收標準**：
- 完整顯示知識內容（問題、答案、類型、分類）
- 重複檢測警告顯示（相似知識列表、相似度評分）
- 可修改內容（問題、答案、關鍵字）
- 審核備註輸入
- 批准/拒絕操作
- 批准後顯示同步結果（同步到 knowledge_base 或 vendor_sop_items）
- 錯誤處理（同步失敗、API 錯誤）

#### 11.3.3 批量審核功能

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  批量審核確認                                            │
├─────────────────────────────────────────────────────────┤
│  已選取 15 個知識項目                                    │
│                                                          │
│  知識類型分布：                                          │
│  ├─ SOP：8 個                                            │
│  └─ 一般知識：7 個                                       │
│                                                          │
│  重複警告統計：                                          │
│  ├─ 高度相似（≥80%）：3 個 ⚠️                            │
│  ├─ 中度相似（60-80%）：5 個 ⚡                           │
│  └─ 無重複（<60%）：7 個 ✓                               │
│                                                          │
│  批量修改（選填）：                                     │
│  關鍵字：[租金, 繳納, 管理]                              │
│                                                          │
│  確定要批准這 15 個知識項目嗎？                          │
│  （批准後將立即同步到正式知識庫）                       │
│                                                          │
│  [取消] [確認批准]                                       │
└─────────────────────────────────────────────────────────┘
```

**執行進度顯示**：
```
┌─────────────────────────────────────────────────────────┐
│  批量審核進度                                            │
├─────────────────────────────────────────────────────────┤
│  [████████████████░░░░░░░░░] 12/15 (80%)                 │
│                                                          │
│  正在處理：知識 #14「可以養寵物嗎？」                   │
│                                                          │
│  已完成：12 個                                           │
│  失敗：0 個                                              │
│  剩餘：3 個                                              │
│                                                          │
│  [取消批量審核]                                          │
└─────────────────────────────────────────────────────────┘
```

**結果摘要對話框**：
```
┌─────────────────────────────────────────────────────────┐
│  批量審核完成                                            │
├─────────────────────────────────────────────────────────┤
│  總計：15 個                                             │
│  成功：13 個 ✅                                           │
│  失敗：2 個 ❌                                            │
│  執行時間：5.4 秒                                        │
│                                                          │
│  失敗項目：                                              │
│  ├─ 知識 #14：同步失敗（embedding API 超時）            │
│  └─ 知識 #16：知識不存在                                 │
│                                                          │
│  [重試失敗項目] [關閉]                                   │
└─────────────────────────────────────────────────────────┘
```

**API 調用**：
- `POST /api/v1/loop-knowledge/batch-review`
- 請求體：BatchReviewRequest（knowledge_ids, action, modifications）
- 回應：BatchReviewResponse（total, successful, failed, failed_items, duration_ms）

**驗收標準**：
- 全選功能（當前頁或所有頁）
- 確認對話框（顯示知識類型分布、重複警告統計）
- 進度顯示（進度條、當前處理項目）
- 結果摘要（成功/失敗統計、失敗項目列表）
- 重試功能（重試失敗項目）
- 錯誤處理（部分失敗不影響其他項目）

#### 11.3.4 審核進度統計

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  審核進度統計                                            │
├─────────────────────────────────────────────────────────┤
│  ┌───────────┬───────────┬───────────┬───────────┐     │
│  │ 待審核     │ 已批准     │ 已拒絕     │ 已同步     │     │
│  │    50     │    120     │    15      │    105     │     │
│  └───────────┴───────────┴───────────┴───────────┘     │
│                                                          │
│  審核通過率：89% (120 / 135)                             │
│  同步成功率：87.5% (105 / 120)                           │
└─────────────────────────────────────────────────────────┘
```

**資料來源**：
- API：`GET /api/v1/loop-knowledge/pending?status=pending` - 待審核
- API：`GET /api/v1/loop-knowledge/pending?status=approved` - 已批准
- API：`GET /api/v1/loop-knowledge/pending?status=rejected` - 已拒絕
- API：`GET /api/v1/loop-knowledge/pending?status=synced` - 已同步

**驗收標準**：
- 統計卡片顯示（待審核、已批准、已拒絕、已同步）
- 審核通過率計算
- 同步成功率計算
- 自動刷新（每 10 秒）

**元件結構**：
```
KnowledgeReviewTab.vue (主元件)
├─ data()
│  ├─ knowledgeList: []           // 待審核知識列表
│  ├─ selectedKnowledge: null     // 當前選擇的知識
│  ├─ selectedIds: []             // 批量選取的 ID
│  ├─ showDetailModal: false      // 詳情 Modal 顯示狀態
│  ├─ showBatchModal: false       // 批量審核確認 Modal
│  ├─ batchProgress: null         // 批量審核進度
│  ├─ filters: {...}              // 篩選條件
│  └─ statistics: {...}           // 審核統計
├─ computed
│  ├─ allSelected()               // 是否全選
│  └─ hasWarningKnowledge()       // 是否有重複警告
└─ methods
   ├─ loadKnowledge()             // 載入待審核知識列表
   ├─ reviewKnowledge()           // 單一審核
   ├─ batchReview()               // 批量審核
   ├─ toggleSelectAll()           // 全選/取消全選
   ├─ showDetail()                // 顯示詳情
   └─ loadStatistics()            // 載入統計資料
```

**驗收標準**：
- 完整實作所有知識審核功能（對應 loop_knowledge API 3 個端點）
- 待審核知識列表顯示（分頁、篩選、排序）
- 單一審核功能（修改、批准/拒絕、重複警告顯示）
- 批量審核功能（全選、批量批准/拒絕、進度顯示、結果摘要）
- 審核進度統計（待審核、已批准、已拒絕、已同步）
- UI/UX 符合設計規範
- 錯誤處理完整
- 載入狀態顯示

---

### 11.4 調整「回測結果」Tab ✅

將現有 BacktestView.vue 的回測結果查看功能拆分為獨立元件 `BacktestResultsTab.vue`，並整合到迴圈流程。

**功能需求**：

#### 11.4.1 元件拆分

**從現有程式碼拆分**：
- 保留回測結果查詢功能（loadBacktestRuns, loadResults）
- 保留統計卡片顯示（statistics, quality）
- 保留詳情 Modal（showDetail, selectedResult）
- 保留分頁控制（pagination）
- 保留知識優化跳轉（optimizeKnowledge）

**移除功能**（移至其他 Tab）：
- 回測執行功能（移除 runSmartBatch, runContinuousBatch）
- Smart Batch 配置（移除 smartBatchConfig）

#### 11.4.2 整合到迴圈流程

**新增功能**：
- 顯示迴圈資訊（loop_id, loop_name, iteration）
- 關聯到固定測試集（顯示 scenario_ids）
- 迭代間對比（顯示迭代前後的通過率變化）

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  回測結果（迴圈 #3 - 第1批-包租業）                      │
├─────────────────────────────────────────────────────────┤
│  迭代：[▼ 第 3 次迭代]  固定測試集：50 題               │
│                                                          │
│  [統計卡片區塊] - 保留現有功能                          │
│                                                          │
│  迭代對比：                                              │
│  ├─ 第 2 次迭代：通過率 74% (37/50)                     │
│  ├─ 第 3 次迭代：通過率 78% (39/50) ↑ 4%                │
│  └─ 目標通過率：85%（尚差 7%）                           │
│                                                          │
│  [回測結果表格] - 保留現有功能                          │
└─────────────────────────────────────────────────────────┘
```

**驗收標準**：
- 元件拆分完成（BacktestResultsTab.vue 獨立於 BacktestView.vue）
- 保留所有現有回測結果查看功能
- 新增迴圈資訊顯示（loop_id, loop_name, iteration）
- 新增固定測試集資訊顯示（scenario_ids, 難度分布）
- 新增迭代間對比功能（通過率變化、目標差距）
- UI/UX 保持一致
- 不破壞現有功能

---

### 11.5 實作「驗證回測」Tab（可選功能）

創建 `knowledge-admin/frontend/src/components/ValidationTab.vue`，整合驗證回測 API（routers/loops.py validate 端點）。

**功能需求**：

#### 11.5.1 驗證回測執行

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  驗證回測                                                │
├─────────────────────────────────────────────────────────┤
│  迴圈：[▼ #3 第1批-包租業]                               │
│                                                          │
│  驗證範圍：                                              │
│  ( ) failed_only - 僅驗證失敗案例                        │
│  (●) failed_plus_sample - 失敗 + 20% 抽樣通過案例 (推薦) │
│  ( ) full - 完整驗證所有測試                             │
│                                                          │
│  抽樣比例：[▼ 20%]                                       │
│                                                          │
│  [執行驗證回測]                                          │
└─────────────────────────────────────────────────────────┘
```

**API 調用**：
- `POST /api/v1/loops/{loop_id}/validate`
- 請求體：ValidateLoopRequest（validation_scope, sample_pass_rate）
- 回應：ValidateLoopResponse（validation_passed, regression_detected, regression_count）

#### 11.5.2 驗證結果顯示

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  驗證結果                                                │
├─────────────────────────────────────────────────────────┤
│  驗證通過：✅ 是                                          │
│  Regression 檢測：❌ 未發現                              │
│                                                          │
│  驗證統計：                                              │
│  ├─ 驗證測試數：20 題（失敗 11 題 + 抽樣 9 題）         │
│  ├─ 通過：18 題 (90%)                                    │
│  ├─ 失敗：2 題 (10%)                                     │
│  └─ Regression：0 題                                     │
│                                                          │
│  Regression 詳情：                                       │
│  （無 regression 案例）                                  │
│                                                          │
│  [查看失敗案例] [關閉]                                   │
└─────────────────────────────────────────────────────────┘
```

**驗收標準**：
- 驗證範圍選擇（failed_only, failed_plus_sample, full）
- 抽樣比例設定（10%, 20%, 30%）
- 執行驗證回測
- 驗證結果顯示（驗證通過、regression 檢測、統計）
- Regression 詳情顯示（哪些案例出現 regression）
- 錯誤處理

---

### 11.6 整合所有 Tab 到 BacktestView.vue ✅

將所有 Tab 元件（LoopManagementTab、KnowledgeReviewTab、BacktestResultsTab、ValidationTab）整合到 BacktestView.vue 頁面，並調整/移除原頁面不需要的部分和程式。

**目標**：
- 建立 Tab 導航架構（迴圈管理、知識審核、回測結果、驗證回測）
- 整合 LoopManagementTab.vue 元件
- 保留現有回測結果功能但重新組織為 Tab 結構
- 移除智能批次執行控制（由迴圈管理功能取代）
- 為知識審核和驗證回測創建占位 Tab

**UI 設計**：
```
┌─────────────────────────────────────────────────────────┐
│  知識完善回測系統                                        │
├─────────────────────────────────────────────────────────┤
│  [迴圈管理] [知識審核] [回測結果] [驗證回測]            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  (根據選擇的 Tab 顯示對應內容)                           │
│                                                          │
│  - 迴圈管理：顯示 LoopManagementTab.vue 元件            │
│  - 知識審核：顯示 KnowledgeReviewTab.vue 元件（占位）   │
│  - 回測結果：顯示原有回測結果功能（重構後）             │
│  - 驗證回測：顯示 ValidationTab.vue 元件（占位）        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**實作步驟**：

#### 11.7.1 設計 Tab 導航架構
- 在 BacktestView.vue 的 `<template>` 區塊新增 Tab 導航 UI
- 使用 Vue 響應式資料管理當前選中的 Tab（activeTab）
- Tab 導航樣式：Material Design 或 Ant Design 風格

#### 11.7.2 整合 LoopManagementTab 元件
- 在 BacktestView.vue 的 `<script>` 區塊匯入 LoopManagementTab 元件
- 在 components 中註冊 LoopManagementTab
- 在對應 Tab 顯示 LoopManagementTab 元件

```vue
<script>
import LoopManagementTab from '@/components/LoopManagementTab.vue';

export default {
  name: 'BacktestView',
  components: {
    LoopManagementTab,
    // ... 其他元件
  },
  data() {
    return {
      activeTab: 'loop-management', // 預設顯示迴圈管理
    };
  },
  // ...
};
</script>
```

#### 11.7.3 創建知識審核 Tab 占位元件
- 創建簡單的占位內容，顯示「此功能開發中」
- 等待任務 11.3 實作完整的 KnowledgeReviewTab.vue

#### 11.7.4 重構回測結果為獨立 Tab
- 保留 BacktestView.vue 中現有的回測結果功能
- 將回測結果相關的 template、methods、computed 整理到「回測結果」Tab 中
- 移除智能批次執行控制（runSmartBatch、runContinuousBatch 等），這些功能由迴圈管理取代

**需要移除的功能**：
- 智能批次執行按鈕與表單（Smart Batch Execution）
- runSmartBatch() 方法
- runContinuousBatch() 方法
- 相關的 data 屬性（batchSize, selectedStatus, selectedSource, selectedDifficulty）

**需要保留的功能**：
- 回測結果查詢（loadBacktestRuns, loadResults）
- 統計卡片顯示（通過率、總題數等）
- 結果列表與詳情查看

#### 11.7.5 創建驗證回測 Tab 占位元件
- 創建簡單的占位內容，顯示「此功能為可選功能，開發中」
- 等待任務 11.5 實作完整的 ValidationTab.vue

#### 11.7.6 調整頁面樣式與佈局
- 調整 BacktestView.vue 的整體佈局，確保 Tab 導航與內容區塊排版合理
- 新增 Tab 導航樣式（active 狀態、hover 效果等）
- 確保響應式設計（手機、平板、桌面螢幕）

**CSS 樣式參考**：
```css
.tab-navigation {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 20px;
}

.tab-item {
  padding: 12px 24px;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.tab-item:hover {
  background-color: #f5f5f5;
}

.tab-item.active {
  border-bottom-color: #1890ff;
  color: #1890ff;
  font-weight: 600;
}

.tab-content {
  padding: 20px;
  min-height: 600px;
}
```

**驗收標準**：
- ✅ Tab 導航正確顯示四個 Tab（迴圈管理、知識審核、回測結果、驗證回測）
- ✅ 點擊 Tab 可以正確切換顯示內容
- ✅ LoopManagementTab 元件成功整合並正常運作
- ✅ 知識審核與驗證回測 Tab 顯示占位內容
- ✅ 回測結果 Tab 保留原有功能且正常運作
- ✅ 智能批次執行功能已移除（不影響其他功能）
- ✅ 頁面樣式美觀，響應式設計正確
- ✅ 無 Console 錯誤或警告
- ✅ 在 http://localhost:8087/backtest 頁面可以看到完整的 Tab 架構

**測試方式**：
1. 啟動前端開發伺服器：`cd knowledge-admin/frontend && npm run dev`
2. 開啟瀏覽器訪問：http://localhost:8087/backtest
3. 驗證 Tab 導航顯示正確
4. 點擊「迴圈管理」Tab，驗證 LoopManagementTab 功能正常
5. 點擊「知識審核」和「驗證回測」Tab，驗證占位內容顯示
6. 點擊「回測結果」Tab，驗證原有回測結果功能正常
7. 驗證智能批次執行功能已移除
8. 檢查 Console 無錯誤

---

### 11.7 整合測試與 E2E 驗收

#### 11.7.1 元件單元測試

為每個 Tab 元件撰寫單元測試（使用 Jest + Vue Test Utils）。

**測試檔案**：
- `LoopManagementTab.spec.js`
- `KnowledgeReviewTab.spec.js`
- `BacktestResultsTab.spec.js`
- `ValidationTab.spec.js`

**測試覆蓋**：
- API 調用測試（使用 Mock API）
- UI 互動測試（按鈕點擊、表單提交）
- 狀態管理測試（data, computed, methods）
- 錯誤處理測試（API 錯誤、網路錯誤）

**驗收標準**：
- 測試覆蓋率 >= 80%
- 所有測試通過
- 無 console 警告或錯誤

#### 11.7.2 整合測試

撰寫 E2E 測試腳本，驗證完整的知識完善迴圈流程。

**測試場景**：

**場景 1：完整迴圈流程**
1. 啟動新迴圈（vendor_id=2, batch_size=50）
2. 執行迭代（非同步模式）
3. 輪詢狀態直到進入 REVIEWING 狀態
4. 查詢待審核知識
5. 批量審核知識（批准 10 個）
6. 再次執行迭代
7. 檢查通過率是否提升
8. 完成批次

**場景 2：批量審核流程**
1. 查詢待審核知識（status=pending）
2. 全選當前頁（50 個）
3. 批量批准
4. 檢查進度顯示
5. 檢查結果摘要
6. 檢查同步成功率

**場景 3：驗證回測流程**
1. 選擇已完成的迴圈
2. 執行驗證回測（validation_scope=failed_plus_sample, sample_pass_rate=0.2）
3. 檢查驗證結果
4. 檢查 regression 檢測結果

**測試工具**：
- Cypress 或 Playwright（E2E 測試框架）
- Docker Compose（啟動完整環境：資料庫、後端、前端）

**驗收標準**：
- 所有場景測試通過
- 無 console 錯誤或警告
- 測試執行時間 < 10 分鐘
- 測試報告清晰（截圖、錯誤日誌）

#### 11.7.3 效能測試

**測試項目**：
- 列表載入時間（< 1 秒，100 筆資料）
- 批量審核時間（< 10 秒，50 個項目）
- 輪詢頻率（3-5 秒，不影響 UI 響應）
- 記憶體使用（< 100 MB，長時間運行）

**驗收標準**：
- 所有效能指標達標
- 無記憶體洩漏
- 無 UI 卡頓

#### 11.7.4 瀏覽器相容性測試

**測試瀏覽器**：
- Chrome（最新版）
- Firefox（最新版）
- Safari（最新版）
- Edge（最新版）

**驗收標準**：
- 所有瀏覽器功能正常
- UI 顯示一致
- 無 console 錯誤

#### 11.7.5 使用者驗收測試（UAT）

**測試清單**：
1. 啟動新迴圈（參數配置、測試集選取）
2. 執行迭代（進度監控、狀態更新）
3. 查詢待審核知識（篩選、分頁、排序）
4. 單一審核（修改、批准/拒絕、重複警告）
5. 批量審核（全選、批量操作、進度顯示、結果摘要）
6. 查看回測結果（迭代對比、固定測試集）
7. 執行驗證回測（regression 檢測）
8. 完成批次、啟動下一批次

**驗收標準**：
- 所有功能符合需求
- UI/UX 符合設計規範
- 錯誤處理完整
- 使用者體驗良好

---

## 任務統計（更新）

**總計**：**12 個主任務**，**68 個子任務**

**新增任務**：
- 任務 11：前端介面實作 - 知識完善迴圈管理與審核中心（6 個子任務）

**預估工時**（每個子任務 1-3 小時）：
- **任務 11（前端實作）：20-30 小時**
  - 11.1: 現有頁面盤查與分析報告（2-3 小時）
  - 11.2: 實作「迴圈管理」Tab（8-12 小時）
  - 11.3: 實作「知識審核」Tab（6-10 小時）
  - 11.4: 調整「回測結果」Tab（2-3 小時）
  - 11.5: 實作「驗證回測」Tab（2-3 小時，可選）
  - 11.6: 整合測試與 E2E 驗收（4-6 小時）

**總預估工時（含任務 11）**：83-126 小時

---

## 任務統計

**總計**：11 個主任務，62 個子任務

**需求覆蓋**：
- 全部需求：清理過時架構（任務 0）
- 4.4, 4.5：測試情境選取與固定測試集（任務 1, 2）
- 7.2, 7.3：重複知識檢測（任務 7）
- 8.1, 8.2, 8.3：人工審核與批量審核（任務 6）
- 9：驗證效果回測（任務 4, 5）
- 10.1, 10.2, 10.4, 10.5, 10.6.1：迴圈管理與迭代控制（任務 3, 4, 5）

**預估工時**（每個子任務 1-3 小時）：
- **階段 0 清理任務：4-5 小時（優先）**
- 資料庫架構：2-3 小時
- 測試情境選取器：5-8 小時
- 非同步執行管理器：5-8 小時
- LoopCoordinator 擴展：8-12 小時
- 迴圈管理 API：12-18 小時
- 知識審核 API：10-15 小時
- 重複知識檢測：6-10 小時
- API 整合與錯誤處理：3-5 小時
- 前端介面調整：4-6 小時（API 契約定義）
- 文檔與部署準備：4-6 小時

**總預估工時**：63-96 小時

---

## 任務 12：手動功能驗收與最終交付 ⏳

**目標**：由使用者（業主）親自驗收所有功能，確保系統符合實際業務需求並能順利投入生產使用。

**方法**：逐項測試所有功能，記錄實際操作結果，確認每個功能都能正常運作且符合預期。

---

### 12.1 後端 API 功能驗收

#### 12.1.1 迴圈管理 API 驗收

**測試環境**：
- 後端服務：`http://localhost:8100`
- 資料庫：PostgreSQL (vendor_id=2)

**驗收清單**：

| # | 功能 | API 端點 | 測試步驟 | 預期結果 | 驗收狀態 | 備註 |
|---|------|---------|---------|---------|---------|------|
| 1 | 啟動新迴圈 | `POST /api/v1/loops/start` | 1. 準備 payload（loop_name, vendor_id, batch_size, max_iterations, target_pass_rate）<br>2. 發送 POST 請求<br>3. 檢查返回的 loop_id 和 status | - 返回 loop_id<br>- status 為 PENDING<br>- scenario_ids 已選取 | ⏳ 待測試 |  |
| 2 | 查詢迴圈列表 | `GET /api/v1/loops/` | 1. 發送 GET 請求<br>2. 檢查返回的迴圈列表<br>3. 驗證 status, progress, created_at 等欄位 | - 返回陣列格式<br>- 包含所有迴圈記錄<br>- 欄位完整無誤 | ⏳ 待測試 |  |
| 3 | 查詢單一迴圈詳情 | `GET /api/v1/loops/{loop_id}` | 1. 使用有效的 loop_id<br>2. 檢查返回的詳細資訊<br>3. 驗證 scenario_ids, iterations 等欄位 | - 返回完整迴圈資訊<br>- 包含迭代歷史<br>- scenario_ids 正確 | ⏳ 待測試 |  |
| 4 | 執行迭代 | `POST /api/v1/loops/{loop_id}/execute-iteration` | 1. 選擇 PENDING 或 RUNNING 狀態的迴圈<br>2. 發送 POST 請求（async_mode=true）<br>3. 檢查是否立即返回<br>4. 輪詢 status 直到完成 | - 立即返回 execution_task_id<br>- status 變為 RUNNING → REVIEWING<br>- 回測結果已儲存 | ⏳ 待測試 |  |
| 5 | 暫停迴圈 | `POST /api/v1/loops/{loop_id}/pause` | 1. 選擇 RUNNING 狀態的迴圈<br>2. 發送 POST 請求<br>3. 檢查 status 變更 | - status 變為 PAUSED<br>- 返回成功訊息 | ⏳ 待測試 |  |
| 6 | 恢復迴圈 | `POST /api/v1/loops/{loop_id}/resume` | 1. 選擇 PAUSED 狀態的迴圈<br>2. 發送 POST 請求<br>3. 檢查 status 變更 | - status 變為 RUNNING<br>- 返回成功訊息 | ⏳ 待測試 |  |
| 7 | 取消迴圈 | `POST /api/v1/loops/{loop_id}/cancel` | 1. 選擇進行中的迴圈<br>2. 發送 POST 請求<br>3. 檢查 status 變更 | - status 變為 CANCELLED<br>- 返回成功訊息 | ⏳ 待測試 |  |
| 8 | 完成批次 | `POST /api/v1/loops/{loop_id}/complete-batch` | 1. 選擇 REVIEWING 狀態的迴圈<br>2. 發送 POST 請求<br>3. 檢查返回的統計摘要 | - status 變為 COMPLETED<br>- 返回統計摘要（迭代次數、通過率、知識數量） | ⏳ 待測試 |  |
| 9 | 啟動下一批次 | `POST /api/v1/loops/start-next-batch` | 1. 選擇已完成的迴圈作為 parent_loop_id<br>2. 準備 payload<br>3. 檢查是否排除重複的 scenario_ids | - 新 loop_id 已創建<br>- scenario_ids 不包含父迴圈的 IDs<br>- 其他參數繼承 | ⏳ 待測試 |  |

**驗收標準**：
- ✅ 所有 9 個端點測試通過
- ✅ 錯誤處理正確（400, 404, 409 錯誤）
- ✅ 資料持久化正確（資料庫記錄完整）

---

#### 12.1.2 知識審核 API 驗收

**驗收清單**：

| # | 功能 | API 端點 | 測試步驟 | 預期結果 | 驗收狀態 | 備註 |
|---|------|---------|---------|---------|---------|------|
| 1 | 查詢待審核知識 | `GET /api/v1/loop-knowledge/pending` | 1. 發送 GET 請求（vendor_id, status=pending）<br>2. 檢查返回的知識列表<br>3. 驗證重複檢測警告欄位 | - 返回待審核知識陣列<br>- 包含 duplication_warning<br>- 包含相似知識資訊 | ⏳ 待測試 |  |
| 2 | 查詢單一知識詳情 | `GET /api/v1/loop-knowledge/{knowledge_id}` | 1. 使用有效的 knowledge_id<br>2. 檢查返回的完整資訊<br>3. 驗證問題、答案、分類等欄位 | - 返回完整知識資訊<br>- 包含 SOP 分類層級<br>- 包含相似知識列表 | ⏳ 待測試 |  |
| 3 | 單一知識審核 | `POST /api/v1/loop-knowledge/{knowledge_id}/review` | 1. 準備 payload（decision, modified_question, modified_answer）<br>2. 發送 POST 請求<br>3. 檢查審核結果和同步狀態 | - review_status 變為 approved/rejected<br>- 若 approved 則同步到知識庫<br>- 返回同步結果 | ⏳ 待測試 |  |
| 4 | 批量知識審核 | `POST /api/v1/loop-knowledge/batch-review` | 1. 準備多個 knowledge_ids 陣列（50 個）<br>2. 設定統一 decision<br>3. 檢查進度顯示<br>4. 檢查結果摘要 | - 返回批量處理進度<br>- 成功/失敗統計正確<br>- 同步成功率顯示 | ⏳ 待測試 |  |
| 5 | 查詢迴圈知識統計 | `GET /api/v1/loop-knowledge/stats` | 1. 發送 GET 請求（loop_id, vendor_id）<br>2. 檢查返回的統計資訊 | - 返回各狀態知識數量<br>- 返回重複檢測統計<br>- 返回審核進度 | ⏳ 待測試 |  |

**驗收標準**：
- ✅ 所有 5 個端點測試通過
- ✅ 批量審核效能符合要求（50 個項目 < 10 秒）
- ✅ 重複檢測準確率 > 90%

---

### 12.2 前端功能完整驗收

#### 12.2.1 迴圈管理 Tab 驗收

**訪問路徑**：`http://localhost:8087/#/backtest-management` → 「迴圈管理」Tab

**驗收清單**：

| # | 功能模組 | 測試步驟 | 預期結果 | 驗收狀態 | 備註 |
|---|---------|---------|---------|---------|------|
| 1 | 迴圈列表顯示 | 1. 打開「迴圈管理」Tab<br>2. 檢查列表是否載入<br>3. 檢查欄位完整性（ID、名稱、狀態、迭代、通過率、更新時間） | - 列表正常載入<br>- 所有欄位顯示正確<br>- 狀態徽章顏色正確 | ⏳ 待測試 |  |
| 2 | 狀態徽章顯示 | 1. 檢查不同狀態的迴圈<br>2. 驗證顏色與圖示是否正確<br>3. 檢查 RUNNING 狀態是否有閃爍動畫 | - 13 種狀態顏色正確<br>- RUNNING 狀態有閃爍<br>- 圖示清晰可辨 | ⏳ 待測試 |  |
| 3 | 自動輪詢機制 | 1. 確認有 RUNNING 狀態的迴圈<br>2. 觀察列表是否自動更新（每 5 秒）<br>3. 檢查 Network 面板的請求頻率 | - 每 5 秒自動刷新<br>- 僅在有 RUNNING 迴圈時輪詢<br>- 無記憶體洩漏 | ⏳ 待測試 |  |
| 4 | 啟動新迴圈 | 1. 點擊「啟動新迴圈」按鈕<br>2. 填寫表單（名稱、batch_size、max_iterations 等）<br>3. 提交表單<br>4. 檢查成功訊息和列表更新 | - Modal 正常開啟<br>- 表單驗證正確<br>- 提交成功後列表自動刷新 | ⏳ 待測試 |  |
| 5 | 查看迴圈詳情 | 1. 點擊「查看詳情」按鈕<br>2. 檢查 Modal 內容（基本資訊、測試集、迭代歷史）<br>3. 檢查趨勢圖顯示 | - Modal 正常開啟<br>- 所有資訊完整顯示<br>- 趨勢圖繪製正確 | ⏳ 待測試 |  |
| 6 | 執行迭代 | 1. 選擇 RUNNING 狀態的迴圈<br>2. 點擊「執行迭代」按鈕<br>3. 檢查進度顯示<br>4. 等待完成並檢查狀態變更 | - 立即返回並顯示執行中<br>- 進度持續更新<br>- 完成後狀態變為 REVIEWING | ⏳ 待測試 |  |
| 7 | 暫停/恢復迴圈 | 1. 點擊「暫停」按鈕<br>2. 檢查狀態變更為 PAUSED<br>3. 點擊「恢復」按鈕<br>4. 檢查狀態變回 RUNNING | - 暫停成功<br>- 恢復成功<br>- 狀態同步正確 | ⏳ 待測試 |  |
| 8 | 取消迴圈 | 1. 點擊「取消」按鈕<br>2. 確認對話框<br>3. 檢查狀態變更為 CANCELLED | - 顯示確認對話框<br>- 取消成功<br>- 狀態變更正確 | ⏳ 待測試 |  |
| 9 | 完成批次 | 1. 選擇 REVIEWING 狀態的迴圈<br>2. 點擊「完成批次」按鈕<br>3. 檢查統計摘要顯示 | - 顯示統計摘要 Modal<br>- 數據正確（迭代次數、通過率、知識數量）<br>- 狀態變為 COMPLETED | ⏳ 待測試 |  |
| 10 | 啟動下一批次 | 1. 選擇已完成的迴圈<br>2. 點擊「啟動下一批次」<br>3. 檢查是否自動填入父迴圈資訊<br>4. 提交並檢查新迴圈創建 | - 父迴圈自動選擇<br>- 參數繼承正確<br>- 新迴圈創建成功 | ⏳ 待測試 |  |

**驗收標準**：
- ✅ 所有 10 項功能測試通過
- ✅ UI 響應流暢（無卡頓）
- ✅ 錯誤提示清晰易懂
- ✅ 操作邏輯符合直覺

---

#### 12.2.2 知識審核 Tab 驗收

**訪問路徑**：`http://localhost:8087/#/backtest-management` → 「知識審核」Tab

**驗收清單**：

| # | 功能模組 | 測試步驟 | 預期結果 | 驗收狀態 | 備註 |
|---|---------|---------|---------|---------|------|
| 1 | 待審核知識列表 | 1. 打開「知識審核」Tab<br>2. 檢查列表載入<br>3. 檢查欄位（ID、迴圈、迭代、問題、類型、警告） | - 列表正常載入<br>- 所有欄位顯示正確<br>- 分頁功能正常 | ⏳ 待測試 |  |
| 2 | 篩選功能 | 1. 使用迴圈 ID 篩選<br>2. 使用知識類型篩選<br>3. 使用狀態篩選<br>4. 檢查結果是否正確 | - 篩選功能正常<br>- 結果符合篩選條件<br>- 可組合多個篩選 | ⏳ 待測試 |  |
| 3 | 重複警告顯示 | 1. 檢查有重複警告的知識<br>2. 檢查警告圖示和顏色<br>3. 點擊查看相似知識詳情 | - 警告圖示正確（⚠️/⚡/✓）<br>- 顏色分級正確<br>- 相似知識列表完整 | ⏳ 待測試 |  |
| 4 | 查看知識詳情 | 1. 點擊「查看詳情」<br>2. 檢查 Modal 內容（問題、答案、分類、相似知識）<br>3. 檢查資訊完整性 | - Modal 正常開啟<br>- 所有資訊完整<br>- 相似知識列表可互動 | ⏳ 待測試 |  |
| 5 | 單一知識審核 | 1. 點擊「批准」或「拒絕」按鈕<br>2. 檢查是否需要確認<br>3. 檢查審核結果和同步狀態 | - 顯示確認對話框<br>- 審核成功<br>- 同步狀態正確顯示 | ⏳ 待測試 |  |
| 6 | 修改後審核 | 1. 在詳情 Modal 中修改問題或答案<br>2. 點擊「批准」<br>3. 檢查是否儲存修改後的內容 | - 可修改內容<br>- 修改後審核成功<br>- 同步的是修改後的版本 | ⏳ 待測試 |  |
| 7 | 批量選取 | 1. 點擊「全選」核取方塊<br>2. 檢查是否選取當前頁所有項目<br>3. 取消部分選取<br>4. 檢查選取狀態 | - 全選功能正常<br>- 可個別取消<br>- 選取數量正確顯示 | ⏳ 待測試 |  |
| 8 | 批量審核 | 1. 選取多個知識（如 50 個）<br>2. 點擊「批量批准」<br>3. 檢查進度顯示<br>4. 檢查結果摘要 | - 進度條正確顯示<br>- 處理速度合理（< 10 秒）<br>- 結果摘要清晰 | ⏳ 待測試 |  |
| 9 | 統計資訊顯示 | 1. 檢查頁面頂部統計區塊<br>2. 驗證待審核/已批准/已拒絕數量<br>3. 檢查重複檢測統計 | - 統計數字正確<br>- 實時更新<br>- 顯示清晰 | ⏳ 待測試 |  |

**驗收標準**：
- ✅ 所有 9 項功能測試通過
- ✅ 批量審核效能合格
- ✅ 重複警告準確可靠
- ✅ 使用者體驗良好

---

#### 12.2.3 回測結果 Tab 驗收

**訪問路徑**：`http://localhost:8087/#/backtest-management` → 「回測結果」Tab

**驗收清單**：

| # | 功能模組 | 測試步驟 | 預期結果 | 驗收狀態 | 備註 |
|---|---------|---------|---------|---------|------|
| 1 | 迴圈選擇 | 1. 檢查迴圈下拉選單<br>2. 選擇不同迴圈<br>3. 檢查結果是否更新 | - 下拉選單正常<br>- 迴圈切換順暢<br>- 結果即時更新 | ⏳ 待測試 |  |
| 2 | 迭代對比視圖 | 1. 選擇有多次迭代的迴圈<br>2. 檢查迭代列表<br>3. 選擇不同迭代查看結果 | - 迭代列表完整<br>- 可對比不同迭代<br>- 通過率趨勢清晰 | ⏳ 待測試 |  |
| 3 | 固定測試集顯示 | 1. 檢查測試集資訊區塊<br>2. 驗證 scenario_ids 數量<br>3. 檢查測試集組成（難度分布） | - 測試集資訊正確<br>- 數量一致<br>- 難度分布顯示清楚 | ⏳ 待測試 |  |
| 4 | 結果列表顯示 | 1. 檢查回測結果列表<br>2. 驗證欄位（問題、預期答案、實際答案、結果）<br>3. 檢查分頁功能 | - 列表完整顯示<br>- 欄位資訊正確<br>- 分頁正常運作 | ⏳ 待測試 |  |
| 5 | 篩選功能 | 1. 按結果篩選（通過/失敗）<br>2. 按難度篩選<br>3. 檢查篩選結果 | - 篩選功能正常<br>- 結果準確<br>- 可組合篩選 | ⏳ 待測試 |  |

**驗收標準**：
- ✅ 所有 5 項功能測試通過
- ✅ 迭代對比清晰易懂
- ✅ 固定測試集概念體現正確

---

### 12.3 端到端業務流程驗收

#### 12.3.1 完整知識完善迴圈流程

**測試目標**：驗證從啟動迴圈到完成批次的完整流程

**測試步驟**：

1. **啟動新迴圈**
   - [ ] 填寫迴圈名稱：「測試迴圈-{日期}」
   - [ ] 設定 vendor_id=2
   - [ ] 設定 batch_size=30（較小以便快速測試）
   - [ ] 設定 max_iterations=3
   - [ ] 設定 target_pass_rate=0.85
   - [ ] 提交並記錄新的 loop_id
   - **預期結果**：迴圈創建成功，狀態為 PENDING

2. **執行第一次迭代**
   - [ ] 點擊「執行迭代」按鈕
   - [ ] 觀察狀態變化：PENDING → RUNNING → BACKTESTING → ANALYZING → GENERATING → REVIEWING
   - [ ] 記錄第一次迭代的通過率
   - **預期結果**：迭代完成，進入 REVIEWING 狀態，生成待審核知識

3. **審核生成的知識**
   - [ ] 切換到「知識審核」Tab
   - [ ] 篩選當前迴圈的待審核知識
   - [ ] 檢查重複警告（應該有部分知識有警告）
   - [ ] 選取 10 個知識進行批量批准
   - [ ] 檢查同步結果
   - **預期結果**：知識審核成功，同步到知識庫

4. **執行第二次迭代**
   - [ ] 返回「迴圈管理」Tab
   - [ ] 再次點擊「執行迭代」
   - [ ] 觀察通過率是否提升
   - [ ] 記錄第二次迭代的通過率
   - **預期結果**：通過率提升，再次生成待審核知識

5. **完成批次**
   - [ ] 審核第二批知識（批准 15 個）
   - [ ] 點擊「完成批次」按鈕
   - [ ] 檢查統計摘要（總迭代次數、最終通過率、生成知識數量）
   - **預期結果**：批次完成，狀態變為 COMPLETED，統計正確

6. **啟動下一批次**
   - [ ] 點擊「啟動下一批次」按鈕
   - [ ] 檢查父迴圈是否自動選擇
   - [ ] 檢查測試集是否排除重複
   - [ ] 提交新迴圈
   - **預期結果**：新迴圈創建成功，測試集不重複

**驗收標準**：
- ✅ 完整流程無錯誤執行
- ✅ 通過率逐次提升
- ✅ 知識正確同步到知識庫
- ✅ 下一批次成功避免重複測試

**驗收記錄**：
```
測試日期：____________________
測試人員：____________________
loop_id：____________________

第一次迭代通過率：_____%
第二次迭代通過率：_____%
最終通過率：_____%
生成知識總數：_____個
批准知識數：_____個

問題記錄：
1. ________________________________
2. ________________________________
3. ________________________________

結論：□ 通過  □ 不通過
```

---

#### 12.3.2 重複知識檢測驗證

**測試目標**：驗證重複知識檢測的準確性和有效性

**測試步驟**：

1. **準備測試資料**
   - [ ] 確認知識庫中已有至少 50 個知識
   - [ ] 記錄幾個典型問題及答案

2. **執行迭代生成新知識**
   - [ ] 執行一次完整迭代
   - [ ] 進入「知識審核」Tab

3. **檢查重複警告**
   - [ ] 統計有警告的知識數量
   - [ ] 隨機選取 5 個有 ⚠️ 警告的知識
   - [ ] 點擊查看詳情，檢查相似知識列表
   - [ ] 驗證相似度計算是否合理
   - **預期結果**：相似度 >= 80% 的知識確實非常相似

4. **驗證去重效果**
   - [ ] 拒絕高相似度的重複知識
   - [ ] 批准低相似度的新知識
   - [ ] 檢查知識庫中是否避免了重複
   - **預期結果**：重複知識被正確識別和排除

**驗收標準**：
- ✅ 重複檢測準確率 > 90%
- ✅ 相似度計算合理
- ✅ 警告提示清晰有效

**驗收記錄**：
```
檢查知識數量：_____個
有警告知識：_____個
誤報（不相似卻警告）：_____個
漏報（相似但無警告）：_____個
準確率：_____%

結論：□ 通過  □ 不通過
```

---

### 12.4 效能與穩定性驗收

#### 12.4.1 系統效能驗收

**驗收清單**：

| # | 測試項目 | 測試方法 | 目標指標 | 實際結果 | 驗收狀態 |
|---|---------|---------|---------|---------|---------|
| 1 | 列表載入時間 | 載入 100 筆迴圈記錄 | < 1 秒 | _____ 秒 | ⏳ 待測試 |
| 2 | 批量審核速度 | 批量批准 50 個知識 | < 10 秒 | _____ 秒 | ⏳ 待測試 |
| 3 | 輪詢頻率 | 觀察自動輪詢機制 | 每 3-5 秒 | _____ 秒 | ⏳ 待測試 |
| 4 | API 回應時間 | 測試所有 API 端點 | < 500ms | _____ ms | ⏳ 待測試 |
| 5 | 前端記憶體使用 | 長時間運行（1 小時） | < 100 MB | _____ MB | ⏳ 待測試 |
| 6 | 並發處理能力 | 同時執行 3 個迴圈 | 無錯誤 | _____ | ⏳ 待測試 |

**驗收標準**：
- ✅ 所有效能指標達標
- ✅ 無記憶體洩漏
- ✅ 系統穩定運行

---

#### 12.4.2 錯誤處理與容錯驗收

**驗收清單**：

| # | 錯誤場景 | 測試方法 | 預期行為 | 驗收狀態 |
|---|---------|---------|---------|---------|
| 1 | 網路中斷 | 暫時關閉後端服務 | 顯示友好錯誤訊息，提供重試按鈕 | ⏳ 待測試 |
| 2 | API 錯誤 | 提交無效參數 | 顯示具體錯誤原因，不崩潰 | ⏳ 待測試 |
| 3 | 並發衝突 | 同時執行同一迴圈的迭代 | 返回 409 錯誤，提示衝突 | ⏳ 待測試 |
| 4 | 權限不足 | 操作其他 vendor 的迴圈 | 返回 403 錯誤，提示權限不足 | ⏳ 待測試 |
| 5 | 資料不存在 | 查詢不存在的 loop_id | 返回 404 錯誤，提示資源不存在 | ⏳ 待測試 |
| 6 | 長時間輪詢 | 輪詢運行超過 30 分鐘 | 正常運作，無記憶體洩漏 | ⏳ 待測試 |

**驗收標準**：
- ✅ 所有錯誤場景處理正確
- ✅ 錯誤訊息清晰易懂
- ✅ 系統不崩潰，可恢復

---

### 12.5 文檔完整性驗收

#### 12.5.1 API 文檔驗收

**檢查項目**：
- [ ] API 端點清單完整（14 個端點）
- [ ] 每個端點有範例請求和回應
- [ ] 錯誤代碼說明清楚
- [ ] 參數說明詳細
- [ ] 認證機制說明

**文檔位置**：
- `docs/api/loops_api.md`
- `docs/api/loop_knowledge_api.md`

---

#### 12.5.2 使用者文檔驗收

**檢查項目**：
- [ ] 系統概述清楚
- [ ] 使用流程說明詳細
- [ ] 功能模組說明完整
- [ ] 截圖清晰
- [ ] 常見問題解答

**文檔位置**：
- `docs/user_guide/loop_management.md`
- `docs/user_guide/knowledge_review.md`

---

#### 12.5.3 部署文檔驗收

**檢查項目**：
- [ ] 環境需求明確
- [ ] 部署步驟清楚
- [ ] 配置參數說明完整
- [ ] 故障排除指南

**文檔位置**：
- `docs/deployment/README.md`

---

### 12.6 最終驗收清單

**系統就緒檢查表**：

#### 後端系統
- [ ] 所有 API 端點正常運作
- [ ] 資料庫索引已建立
- [ ] 效能測試通過
- [ ] 錯誤處理完整
- [ ] 日誌記錄完善

#### 前端系統
- [ ] 所有頁面正常顯示
- [ ] 功能完整可用
- [ ] UI/UX 符合設計
- [ ] 錯誤提示友好
- [ ] 瀏覽器相容性良好

#### 業務流程
- [ ] 完整迴圈流程驗證通過
- [ ] 重複知識檢測有效
- [ ] 批量審核功能正常
- [ ] 下一批次啟動正確

#### 文檔與交付
- [ ] API 文檔完整
- [ ] 使用者文檔清晰
- [ ] 部署文檔可行
- [ ] 程式碼註解充分

#### 生產就緒
- [ ] 效能指標達標
- [ ] 穩定性測試通過
- [ ] 備份機制建立
- [ ] 監控告警配置

**最終驗收簽核**：

```
驗收日期：____________________
驗收人員：____________________

後端系統：□ 通過  □ 不通過
前端系統：□ 通過  □ 不通過
業務流程：□ 通過  □ 不通過
文檔交付：□ 通過  □ 不通過
生產就緒：□ 通過  □ 不通過

總體評估：□ 通過，可投入生產  □ 需要改進

改進事項：
1. ________________________________
2. ________________________________
3. ________________________________

簽名：____________________
```

---

## 實作順序建議

**階段 0（清理 - 必須優先）**：
0. **任務 0：清理過時架構與文檔**（必須先完成，避免混淆）
   - 0.1: 更新需求與設計文檔
   - 0.2: 清理重複檔案
   - 0.3: 處理無法使用的腳本
   - 0.4: 重組文檔結構
   - 0.5: 驗證清理結果

**第一階段（基礎架構）**：
1. 任務 1：資料庫架構補充（必須先完成）
2. 任務 2：測試情境選取器（核心功能）
3. 任務 8：API 整合與錯誤處理（統一錯誤處理機制）

**第二階段（迴圈管理）**：
4. 任務 3：非同步執行管理器
5. 任務 5：迴圈管理 API 路由層（依賴任務 2, 3）
6. 任務 4：LoopCoordinator 擴展（跨 session 續接）

**第三階段（知識審核）**：
7. 任務 7：重複知識檢測機制
8. 任務 6：知識審核 API 路由層（依賴任務 7）

**第四階段（整合與文檔）**：
9. 任務 9：前端介面調整（API 契約定義）
10. 任務 10：文檔與部署準備

**第五階段（前端實作）**：
11. 任務 11：前端介面實作 - 知識完善迴圈管理與審核中心（整合所有 API）

**並行執行建議**：
- 任務 1 的子任務可並行執行（1.1, 1.2, 1.3）
- 任務 2 的子任務 2.3, 2.4 可與 2.2 並行
- 任務 5 的部分子任務（5.5-5.8）可在 5.1-5.4 完成後並行
- 任務 7 的子任務 7.1, 7.2 可並行執行
- 任務 10 的子任務 10.2, 10.3, 10.4 可並行執行

---

*本文件遵循專案規範，所有任務描述使用自然語言，避免暴露代碼結構細節。*
