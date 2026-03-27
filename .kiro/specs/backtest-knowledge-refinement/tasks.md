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

### 0.5 驗證清理結果

確保清理後系統仍可正常運作。

**驗收標準**：
- 執行 `run_first_loop.py` 測試無錯誤
- 所有 import 路徑正確
- 文檔與實際系統一致
- Git commit 記錄清理動作

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

### 1.2 建立 knowledge_gap_analysis 表（如果不存在） (P)

創建知識缺口分析表，記錄每次迭代的失敗案例與分類結果。

**驗收標準**：
- 表結構符合 requirements.md Section 3.1 定義
- 包含 loop_id, iteration, scenario_id, gap_type, cluster_id 等欄位
- 正確建立索引（loop_id+iteration, scenario_id, cluster_id）

### 1.3 補充 loop_generated_knowledge 表 similar_knowledge 欄位 (P)

確保表中存在 `similar_knowledge` (JSONB) 欄位用於重複檢測結果。

**驗收標準**：
- 欄位存在且為 JSONB 類型
- 允許 NULL 值
- 格式符合 requirements.md Section 3.1 定義

---

## 2. 測試情境選取器實作 (P)

**需求覆蓋**：4.4, 4.5, 10.4

實現測試情境選取策略，支援分層隨機抽樣、固定測試集管理與批次間避免重複。

### 2.1 ScenarioSelector 類別骨架

創建 `services/knowledge_completion_loop/scenario_selector.py` 檔案，實作基礎架構。

**驗收標準**：
- 類別初始化接受 db_pool 參數
- 定義 SelectionStrategy 枚舉（STRATIFIED_RANDOM, SEQUENTIAL, FULL_RANDOM）
- 定義 DifficultyDistribution Pydantic 模型（easy, medium, hard 比例）
- 實作 `select_scenarios()` 方法簽名

### 2.2 實作分層隨機抽樣邏輯

實作 `_stratified_random_sampling()` 方法，按難度分層並隨機選取測試情境。

**驗收標準**：
- 根據 DifficultyDistribution 計算每個難度的目標數量（easy 20%, medium 50%, hard 30%）
- 對每個難度層執行 SQL 查詢（`ORDER BY RANDOM() LIMIT`）
- 過濾 status='approved' 的測試情境
- 支援 exclude_scenario_ids 參數避免重複選取
- 返回 scenario_ids, selection_strategy, difficulty_distribution, total_available

### 2.3 實作批次間避免重複邏輯 (P)

實作 `get_used_scenario_ids()` 方法，查詢同一業者已使用的測試情境 ID。

**驗收標準**：
- 查詢 knowledge_completion_loops 表的 scenario_ids 欄位
- 支援 parent_loop_id 參數（查詢同一父迴圈的所有子迴圈）
- 使用 `unnest(scenario_ids)` 展開陣列
- 返回不重複的 scenario_id 列表

### 2.4 實作順序選取與完全隨機策略 (P)

實作 `_sequential_selection()` 和 `_full_random_selection()` 方法作為備選策略。

**驗收標準**：
- 順序選取：按 `test_scenarios.id` 順序選取前 N 題
- 完全隨機：使用 `ORDER BY RANDOM() LIMIT N`
- 兩者都支援 exclude_scenario_ids 參數

### 2.5 單元測試 (P)

撰寫 `tests/test_scenario_selector.py`，測試選取邏輯正確性。

**驗收標準**：
- 測試分層隨機抽樣的難度分布符合預期
- 測試 exclude_scenario_ids 正確排除已使用的情境
- 測試批次大小邊界條件（0, 1, 超過總數）
- 測試三種選取策略的基本功能

---

## 3. 非同步執行管理器實作

**需求覆蓋**：10.2

實現長時間運行任務的背景執行機制，避免 HTTP 請求超時。

### 3.1 AsyncExecutionManager 類別骨架

創建 `services/knowledge_completion_loop/async_execution_manager.py` 檔案。

**驗收標準**：
- 類別初始化接受 db_pool 參數
- 維護 `running_tasks` 字典（loop_id -> asyncio.Task）
- 定義 ConcurrentExecutionError 異常類別

### 3.2 實作任務啟動與並發控制

實作 `start_iteration()` 方法，啟動非同步迭代任務。

**驗收標準**：
- 檢查 loop_id 是否已在執行中（concurrent execution check）
- 使用 `asyncio.create_task()` 建立背景任務
- 返回 task_id（格式：`task_{loop_id}_{timestamp}`）
- 若已在執行中則拋出 ConcurrentExecutionError

### 3.3 實作背景執行邏輯

實作 `_execute_iteration_background()` 方法，處理完整的迭代流程與錯誤。

**驗收標準**：
- 調用 `coordinator.execute_iteration()`
- 成功時更新狀態為 REVIEWING，記錄事件到 loop_execution_logs
- 捕獲 BudgetExceededError，更新狀態為 FAILED
- 捕獲其他異常，更新狀態為 FAILED 並記錄 traceback
- 使用 finally 清理 running_tasks 記錄

### 3.4 實作任務查詢與取消功能 (P)

實作 `is_running()` 和 `cancel_task()` 方法。

**驗收標準**：
- `is_running()` 檢查 loop_id 是否在 running_tasks 中
- `cancel_task()` 調用 `task.cancel()` 並清理記錄
- 取消後記錄事件到 loop_execution_logs

### 3.5 單元測試 (P)

撰寫 `tests/test_async_execution_manager.py`。

**驗收標準**：
- 測試並發執行檢測（同一 loop 不能同時執行兩次）
- 測試成功執行流程（mock coordinator.execute_iteration）
- 測試錯誤處理（BudgetExceededError, 一般異常）
- 測試任務取消功能

---

## 4. LoopCoordinator 擴展

**需求覆蓋**：9, 10.6.1

擴展現有 LoopCoordinator，新增 load_loop 方法支援跨 session 續接，以及驗證回測功能。

### 4.1 實作 load_loop 方法

在 `services/knowledge_completion_loop/coordinator.py` 新增 `load_loop()` 方法。

**驗收標準**：
- 從 knowledge_completion_loops 表讀取迴圈記錄
- 初始化 coordinator 狀態（loop_id, vendor_id, loop_name, current_status, config）
- 初始化 cost_tracker 並關聯到 knowledge_generator 和 sop_generator
- 若迴圈不存在則拋出 LoopNotFoundError
- 返回 loop_id, status, current_iteration, loaded_at

### 4.2 實作驗證回測主流程

在 LoopCoordinator 新增 `validate_loop()` 方法（可選功能）。

**驗收標準**：
- 驗證當前狀態為 REVIEWING（否則拋出 InvalidStateError）
- 根據 validation_scope 參數選取測試案例：
  - `failed_only`：只測試失敗案例
  - `all`：測試所有案例（scenario_ids）
  - `failed_plus_sample`：失敗案例 + 抽樣通過案例（預設）
- 更新狀態為 VALIDATING
- 調用 backtest_client.execute_backtest() 執行驗證回測
- 計算改善幅度（new_pass_rate - old_pass_rate）
- 檢測 regression（原本通過現在失敗的案例）
- 記錄驗證事件到 loop_execution_logs
- 更新狀態回 RUNNING
- 返回驗證結果

### 4.3 實作 regression 檢測邏輯 (P)

在 LoopCoordinator 新增 `_detect_regression()` 方法。

**驗收標準**：
- 查詢上一次迭代的 backtest_results 表，找出原本 passed=true 的 scenario_ids
- 對比驗證回測結果，找出現在 passed=false 的案例
- 返回 regression 案例數量與詳細列表
- 記錄到 loop_execution_logs（event_type='regression_detected'）

### 4.4 實作知識標記功能 (P)

在 LoopCoordinator 新增 `_mark_knowledge_need_improvement()` 方法。

**驗收標準**：
- 查詢本次迭代同步的知識（透過 source_loop_id 和 iteration）
- 更新 knowledge_base 和 vendor_sop_items 的 review_status='need_improvement'
- 保留知識在正式庫（不刪除）
- 記錄標記事件到 loop_execution_logs

### 4.5 單元測試 (P)

撰寫 `tests/test_loop_coordinator_extensions.py`。

**驗收標準**：
- 測試 load_loop 成功載入已存在的迴圈
- 測試 load_loop 處理不存在的迴圈（拋出 LoopNotFoundError）
- 測試 validate_loop 三種驗證範圍（failed_only, all, failed_plus_sample）
- 測試 regression 檢測邏輯
- 測試驗證通過與失敗的狀態轉換

---

## 5. 迴圈管理 API 路由層實作

**需求覆蓋**：10.1, 10.2, 10.4, 10.5

實現前端迴圈管理的 RESTful API 端點，支援啟動、執行、查詢、暫停、恢復、取消、完成等操作。

### 5.1 創建 routers/loops.py 骨架

創建 FastAPI 路由檔案，定義所有 Pydantic 請求/回應模型。

**驗收標準**：
- 定義 LoopStartRequest, LoopStartResponse 模型
- 定義 ExecuteIterationRequest, ExecuteIterationResponse 模型
- 定義 LoopStatusResponse 模型
- 定義 ValidateLoopRequest, ValidateLoopResponse 模型
- 定義 CompleteBatchResponse 模型
- 所有模型使用 Field 定義驗證規則與描述

### 5.2 實作啟動迴圈端點

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

### 5.3 實作執行迭代端點

實作 `POST /api/v1/loops/{loop_id}/execute-iteration` 端點。

**驗收標準**：
- 驗證迴圈狀態為 RUNNING（否則返回 409 Conflict）
- 支援 async_mode 參數（預設 true）
- 非同步模式：調用 AsyncExecutionManager.start_iteration()，立即返回 202 Accepted
- 同步模式：直接調用 coordinator.execute_iteration()，等待完成後返回結果
- 防止並發執行（檢查 is_running，若已執行則返回 409）
- 返回 ExecuteIterationResponse（含 task_id 或 backtest_result）

### 5.4 實作查詢迴圈狀態端點

實作 `GET /api/v1/loops/{loop_id}` 端點。

**驗收標準**：
- 從 knowledge_completion_loops 表讀取迴圈記錄
- 查詢當前進度（從 loop_execution_logs 取得最新事件）
- 返回 LoopStatusResponse（含 status, current_iteration, current_pass_rate, progress）
- 若迴圈不存在則返回 404 Not Found

### 5.5 實作驗證回測端點（可選功能） (P)

實作 `POST /api/v1/loops/{loop_id}/validate` 端點。

**驗收標準**：
- 驗證迴圈狀態為 REVIEWING（否則返回 409）
- 調用 coordinator.validate_loop()
- 支援 validation_scope 和 sample_pass_rate 參數
- 返回 ValidateLoopResponse（含 validation_result, validation_passed, regression_detected）

### 5.6 實作完成批次端點 (P)

實作 `POST /api/v1/loops/{loop_id}/complete-batch` 端點。

**驗收標準**：
- 更新 knowledge_completion_loops.status='COMPLETED'
- 設定 completed_at 時間戳記
- 記錄 batch_completed 事件到 loop_execution_logs
- 返回統計摘要（總迭代次數、最終通過率、生成知識數量、總成本）

### 5.7 實作暫停/恢復/取消端點 (P)

實作 `POST /api/v1/loops/{loop_id}/pause`, `resume`, `cancel` 端點。

**驗收標準**：
- Pause：更新狀態為 PAUSED，記錄事件
- Resume：驗證狀態為 PAUSED，更新為 RUNNING
- Cancel：調用 AsyncExecutionManager.cancel_task()，更新狀態為 CANCELLED
- 所有操作記錄到 loop_execution_logs

### 5.8 實作啟動下一批次端點 (P)

實作 `POST /api/v1/loops/start-next-batch` 端點。

**驗收標準**：
- 驗證 parent_loop_id 存在且狀態為 COMPLETED
- 自動設定 parent_loop_id 參數
- 調用 ScenarioSelector.get_used_scenario_ids() 取得已使用的情境 ID
- 選取未處理的測試情境（exclude_scenario_ids）
- 創建新迴圈記錄（關聯 parent_loop_id）
- 返回 LoopStartResponse

### 5.9 整合測試 (P)

撰寫 `tests/test_loops_router.py`。

**驗收標準**：
- 測試完整迴圈流程（啟動 → 執行迭代 → 查詢狀態 → 完成）
- 測試非同步執行模式（立即返回 202，輪詢狀態）
- 測試並發執行檢測（同一 loop 不能同時執行兩次迭代）
- 測試批次關聯功能（parent_loop_id, 避免重複選取）
- 測試錯誤處理（404 Not Found, 409 Conflict, 422 Validation Error）

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

### 6.2 實作查詢待審核知識端點

實作 `GET /api/v1/loop-knowledge/pending` 端點。

**驗收標準**：
- 支援篩選參數（loop_id, vendor_id, knowledge_type, status）
- 支援分頁參數（limit, offset）
- 查詢 loop_generated_knowledge 表
- 返回知識列表（含 id, question, answer, knowledge_type, sop_config, similar_knowledge, status）
- 前端顯示重複檢測警告（若 similar_knowledge.detected=true）

### 6.3 實作單一審核端點

實作 `POST /api/v1/loop-knowledge/{knowledge_id}/review` 端點。

**驗收標準**：
- 支援 action 參數（approve, reject）
- 支援 modifications 參數（修改 question, answer, keywords 等）
- 更新 loop_generated_knowledge 狀態（approved/rejected）
- 若為 approve：
  - 立即同步到正式庫（knowledge_base 或 vendor_sop_items）
  - 調用 embedding API 生成向量
  - 設定 review_status='approved'
  - 更新 loop_generated_knowledge.status='synced'
- 記錄審核事件到 loop_execution_logs
- 返回 ReviewKnowledgeResponse（含 synced, synced_to, synced_id）

### 6.4 實作批量審核端點

實作 `POST /api/v1/loop-knowledge/batch-review` 端點。

**驗收標準**：
- 支援 knowledge_ids 列表（1-100 個）
- 支援 action 參數（approve, reject）
- 支援 modifications 參數（批量修改欄位）
- 按順序處理每個項目（避免併發衝突）
- 部分成功模式：某項目失敗不影響其他項目
- 記錄失敗項目到 failed_items 列表
- 記錄批量審核事件到 loop_execution_logs
- 返回 BatchReviewResponse（含 total, successful, failed, failed_items, duration_ms）

### 6.5 實作 embedding 生成邏輯 (P)

創建 `services/knowledge_completion_loop/embedding_client.py`，封裝 embedding API 調用。

**驗收標準**：
- 調用外部 embedding API（EMBEDDING_API_URL）
- 支援一般知識的 question_summary embedding
- 支援 SOP 的 content embedding
- 錯誤處理與重試（使用 tenacity）
- 返回 1536 維向量

### 6.6 實作知識同步邏輯 (P)

在 loop_knowledge router 中實作 `_sync_knowledge_to_production()` 輔助函數。

**驗收標準**：
- 判斷 knowledge_type 決定目標表（'sop' → vendor_sop_items, null → knowledge_base）
- 一般知識：
  - 寫入 knowledge_base（vendor_ids, question_summary, answer, keywords, embedding, review_status='approved', source='loop'）
  - 設定 source_loop_id, source_loop_knowledge_id
- SOP：
  - 寫入 vendor_sop_items（vendor_id, category_id, group_id, item_name, content, keywords, embedding, review_status='approved', source='loop'）
  - 從 sop_config 讀取配置
- 失敗時保持 approved 狀態並返回錯誤訊息

### 6.7 整合測試 (P)

撰寫 `tests/test_loop_knowledge_router.py`。

**驗收標準**：
- 測試查詢待審核知識（篩選、分頁）
- 測試單一審核流程（approve → 同步 → embedding → status 更新）
- 測試批量審核（10 個項目，2 個失敗）
- 測試重複檢測警告顯示（similar_knowledge.detected=true）
- 測試錯誤處理（404 Not Found, 422 Validation Error）

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

### 7.2 實作一般知識重複檢測

在 `services/knowledge_completion_loop/knowledge_generator.py` 新增 `_detect_duplicate_knowledge()` 方法。

**驗收標準**：
- 生成 question_summary 的 embedding
- 使用 pgvector 搜尋 knowledge_base 表（cosine similarity）
- 閾值：similarity > 0.90 視為相似
- 同時搜尋 loop_generated_knowledge 表（knowledge_type IS NULL, status IN ('pending', 'approved')）
- 返回相似知識列表（id, question_summary, similarity_score, source_table）
- 若檢測到相似知識，寫入 similar_knowledge 欄位

### 7.3 整合到知識生成流程

在 SOPGenerator.generate_sop_batch() 和 KnowledgeGeneratorClient.generate_knowledge_batch() 中整合重複檢測。

**驗收標準**：
- 生成知識後立即執行重複檢測
- 檢測結果寫入 loop_generated_knowledge 表（similar_knowledge 欄位）
- 記錄檢測統計到 loop_execution_logs（檢測到的相似知識數量、相似度分布）
- 前端審核時顯示警告（若 similar_knowledge.detected=true）

### 7.4 性能優化 (P)

確保向量搜尋使用 pgvector IVFFlat 索引。

**驗收標準**：
- 驗證 knowledge_base.embedding 和 vendor_sop_items.embedding 欄位有 IVFFlat 索引
- 搜尋查詢使用 `LIMIT 3` 限制返回數量
- 搜尋範圍限制為同業者（vendor_id 或 vendor_ids @> ARRAY[$vendor_id]）
- 重複檢測增加時間 < 10%

### 7.5 單元測試 (P)

撰寫 `tests/test_duplicate_detection.py`。

**驗收標準**：
- 測試 SOP 重複檢測（mock embedding API, mock pgvector 搜尋）
- 測試一般知識重複檢測
- 測試相似度閾值判斷（0.85, 0.90）
- 測試檢測結果寫入 similar_knowledge 欄位
- 測試前端警告顯示邏輯

---

## 8. API 整合與錯誤處理

**需求覆蓋**：10.2

實現統一的錯誤處理機制、API 錯誤回應格式與日誌記錄。

### 8.1 創建統一錯誤處理中介軟體

在 `routers/middleware.py` 創建 FastAPI 錯誤處理中介軟體。

**驗收標準**：
- 捕獲所有 HTTPException，格式化為標準錯誤回應
- 捕獲自訂異常（KnowledgeCompletionError, InvalidStateError, LoopNotFoundError）
- 捕獲未處理的異常，返回 500 Internal Server Error
- 標準錯誤格式：`{error_code, message, details, timestamp}`
- 記錄所有錯誤到日誌系統（含 traceback）

### 8.2 定義自訂異常類別 (P)

在 `services/knowledge_completion_loop/exceptions.py` 定義所有自訂異常。

**驗收標準**：
- KnowledgeCompletionError（基礎異常類別）
- InvalidStateError（狀態轉換非法）
- LoopNotFoundError（迴圈不存在）
- ConcurrentExecutionError（並發執行衝突）
- BudgetExceededError（預算超出）
- EmbeddingGenerationError（embedding 生成失敗）

### 8.3 實作錯誤碼映射 (P)

在 middleware 中實作錯誤碼映射邏輯。

**驗收標準**：
- InvalidStateError → 409 Conflict
- LoopNotFoundError → 404 Not Found
- ConcurrentExecutionError → 409 Conflict
- BudgetExceededError → 422 Unprocessable Entity
- ValidationError → 400 Bad Request
- 其他異常 → 500 Internal Server Error

### 8.4 整合測試 (P)

撰寫 `tests/test_error_handling.py`。

**驗收標準**：
- 測試各種錯誤碼的回應格式
- 測試錯誤訊息本地化（zh-TW）
- 測試錯誤日誌記錄（含 traceback）
- 測試自訂異常處理

---

## 9. 前端介面調整（API 契約定義）

**需求覆蓋**：8.3, 10.2

定義前端與後端的 API 契約，確保前端正確調用批量審核、迴圈管理等功能。

### 9.1 撰寫 API 文檔

創建 `docs/api/loops_api.md` 和 `docs/api/loop_knowledge_api.md`。

**驗收標準**：
- 完整的 API 端點清單（URL, 方法, 參數, 回應）
- 請求/回應範例（JSON 格式）
- 錯誤碼與錯誤訊息清單
- 使用場景範例（批量審核、非同步執行）

### 9.2 前端批量選取功能需求定義 (P)

定義前端審核中心的批量操作界面需求。

**驗收標準**：
- 全選核取方塊（當前頁或所有頁）
- 篩選後全選功能（如：篩選「相似度警告 = 無」→ 全選）
- 批量操作工具列（顯示已選取數量、批量批准/拒絕按鈕）
- 確認對話框（顯示知識類型分布、相似度警告統計）
- 處理進度顯示（進度條、當前處理項目）
- 結果摘要對話框（成功/失敗統計、失敗項目列表、重試按鈕）

### 9.3 前端迴圈管理界面需求定義 (P)

定義前端管理界面的迴圈管理功能需求。

**驗收標準**：
- 啟動迴圈對話框（loop_name, batch_size, target_pass_rate, max_iterations）
- 迴圈列表頁面（顯示 loop_id, loop_name, status, current_iteration, current_pass_rate）
- 迴圈詳情對話框（顯示固定測試集資訊、選取策略、難度分布、迭代歷史、生成知識統計）
- 執行迭代按鈕（觸發非同步執行）
- 輪詢狀態機制（每 5 秒輪詢 GET /loops/{loop_id}）
- 進度顯示（phase, percentage, message）
- 暫停/恢復/取消按鈕

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

**並行執行建議**：
- 任務 1 的子任務可並行執行（1.1, 1.2, 1.3）
- 任務 2 的子任務 2.3, 2.4 可與 2.2 並行
- 任務 5 的部分子任務（5.5-5.8）可在 5.1-5.4 完成後並行
- 任務 7 的子任務 7.1, 7.2 可並行執行
- 任務 10 的子任務 10.2, 10.3, 10.4 可並行執行

---

*本文件遵循專案規範，所有任務描述使用自然語言，避免暴露代碼結構細節。*
