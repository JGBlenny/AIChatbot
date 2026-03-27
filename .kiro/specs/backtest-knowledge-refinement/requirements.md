# 需求規格：backtest-knowledge-refinement

> **功能名稱**：包租/代管業知識庫完善系統 - 回測驅動的知識迭代完善流程
> **建立時間**：2026-03-26T15:25:00Z
> **語言**：Traditional Chinese (zh-TW)

---

## 1. 專案概述

### 1.1 核心目標

本專案旨在建立一套完整的「回測驅動的知識缺口發現與修補系統」，針對包租/代管業的測試情境，透過迭代流程自動化發現知識缺口、智能分類、生成知識文檔與 SOP，並透過人工審核與驗證，持續完善知識庫品質。

### 1.2 核心價值

- **自動化知識缺口發現**：透過回測自動識別 RAG 系統回答失敗的問題
- **AI 驅動的智能分類**：使用 OpenAI API 將問題分類為 4 大類別並聚類
- **批次迭代驗證**：支援分批處理（如首批 50 題），確認有效性後進行後續批次
- **人工審核機制**：AI 生成內容需經過人工審核才正式加入知識庫
- **立即同步驗證**：審核通過立即同步，透過回測驗證改善效果

### 1.3 系統限制與設計原則

1. **禁止推測**：所有需求必須基於實際代碼實現，不得憑空推測系統行為
2. **現有系統改良**：基於已存在的 `services/knowledge_completion_loop/` 模組進行完善
3. **批次控制**：支援多種測試規模（50/500/3000 題），採用循序漸進的測試策略
4. **前端驅動**：日常操作優先使用前端界面（http://localhost:8087），命令列腳本僅供調試

---

## 2. 系統架構

### 2.1 三層回測架構

系統使用三層架構執行回測：

```
LoopCoordinator (coordinator.py)
    ↓ 協調整體流程
BacktestFrameworkClient (backtest_client.py)
    ↓ 場景載入、記錄創建、結果持久化
AsyncBacktestFramework (backtest_framework_async.py)
    ↓ 並發 HTTP 請求與 LLM 評估
RAG API (/api/v1/message)
    ↓ 正式對話處理流程
```

**關鍵特性**：
- 回測使用與正式對話**相同的 API 端點**（`/api/v1/message`）
- 執行完整的對話處理流程（意圖分類、知識檢索、信心度評估、LLM 優化）
- 透過特殊參數區分回測請求（`include_debug_info: true`、獨立 session_id）

### 2.2 完整處理流程（8 步驟）

```
1. 執行回測 → 測試 50 題，記錄結果
2. 分析失敗案例 → 篩選未通過的問題
3. 智能分類 → 分為 4 類：SOP/表單/系統配置/API查詢
4. 類別分離 → SOP組（SOP+表單）vs Knowledge組（系統配置）
5. 分別聚類 → 將相似問題聚類（2-5 題/cluster）
6. 生成知識 → SOP組→SOPGenerator，Knowledge組→KnowledgeGenerator
7. 人工審核與同步 → 前端審核、修改、批准 → 立即同步到 knowledge_base/vendor_sop_items
8. 驗證效果 → 執行回測驗證改善幅度 → 通過則繼續，失敗則標記待改善
```

### 2.3 人工控制點

系統在三個關鍵點暫停等待人工操作：

1. **迭代完成後**：狀態轉為 `REVIEWING`，等待人工審核知識
2. **審核完成後**：知識立即同步到正式庫，人工決定是否執行驗證回測
3. **驗證完成後**：狀態轉回 `RUNNING`，人工決定繼續迭代或完成批次

### 2.4 執行方式

**主要方式：前端界面**
- 管理界面：`http://localhost:8087/test-scenarios`
- 審核界面：`http://localhost:8087/review-center`
- 透過 RESTful API 與後端溝通

**輔助方式：命令列腳本**
- 路徑：`services/knowledge_completion_loop/run_first_loop.py`
- 用途：調試、CI/CD、自動化

---

## 3. 資料模型

### 3.1 核心資料表

#### test_scenarios（測試情境 - 全域共用）
```sql
CREATE TABLE test_scenarios (
    id SERIAL PRIMARY KEY,
    test_question TEXT NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'medium',  -- easy/medium/hard
    status VARCHAR(20) DEFAULT 'pending_review',  -- approved/pending_review/rejected
    expected_intent_id INTEGER,
    tags TEXT[],
    priority INTEGER DEFAULT 0,
    source VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**重要**：此表為全域共用，無 `vendor_id` 欄位，所有業者使用相同測試題庫。

#### backtest_runs（回測批次記錄）
```sql
CREATE TABLE backtest_runs (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,  -- 執行回測的業者 ID
    test_type VARCHAR(50),
    total_scenarios INTEGER,
    executed_scenarios INTEGER,
    passed_count INTEGER,
    failed_count INTEGER,
    pass_rate DECIMAL(5,2),
    status VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### backtest_results（回測結果明細）
```sql
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES backtest_runs(id),
    scenario_id INTEGER REFERENCES test_scenarios(id),
    test_question TEXT,
    system_answer TEXT,
    actual_intent VARCHAR(100),
    confidence DECIMAL(5,2),
    passed BOOLEAN,
    evaluation JSONB,
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### knowledge_completion_loops（迴圈管理）
```sql
CREATE TABLE knowledge_completion_loops (
    id SERIAL PRIMARY KEY,
    loop_name VARCHAR(200),
    vendor_id INTEGER NOT NULL,
    parent_loop_id INTEGER REFERENCES knowledge_completion_loops(id),  -- 批次關聯
    status VARCHAR(20),  -- pending/running/reviewing/validating/completed/failed
    target_pass_rate DECIMAL(5,2) DEFAULT 0.85,
    max_iterations INTEGER DEFAULT 10,
    current_iteration INTEGER DEFAULT 0,
    current_pass_rate DECIMAL(5,2),
    scenario_ids INTEGER[],  -- 本批次使用的測試情境 ID 列表
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### loop_generated_knowledge（生成的知識）
```sql
CREATE TABLE loop_generated_knowledge (
    id SERIAL PRIMARY KEY,
    loop_id INTEGER REFERENCES knowledge_completion_loops(id),
    iteration INTEGER,
    question TEXT,
    answer TEXT,
    knowledge_type VARCHAR(20),  -- 'sop' 或 null
    status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected
    sop_config JSONB,  -- SOP 配置（category_id, group_id, etc.）
    similar_knowledge JSONB,  -- 重複檢測結果（若檢測到相似知識）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**similar_knowledge 欄位格式**（可選，當檢測到相似知識時填寫）：
```json
{
  "detected": true,
  "items": [
    {
      "id": 456,
      "source_table": "knowledge_base",  // 或 "vendor_sop_items" 或 "loop_generated_knowledge"
      "question_summary": "租金繳納日期",  // 或 SOP 標題
      "similarity_score": 0.93
    }
  ]
}
```

#### knowledge_gap_analysis（知識缺口分析）
```sql
CREATE TABLE knowledge_gap_analysis (
    id SERIAL PRIMARY KEY,
    loop_id INTEGER REFERENCES knowledge_completion_loops(id),
    iteration INTEGER,
    scenario_id INTEGER REFERENCES test_scenarios(id),
    test_question TEXT,
    gap_type VARCHAR(20),  -- sop_knowledge/form_fill/system_config/api_query
    failure_reason VARCHAR(50),  -- NO_MATCH/LOW_CONFIDENCE/WRONG_INTENT/etc.
    priority VARCHAR(10),  -- p0/p1/p2
    cluster_id INTEGER,  -- 聚類 ID（同一 cluster 的問題會合併生成）
    should_generate_knowledge BOOLEAN DEFAULT true,  -- 是否生成靜態知識
    classification_metadata JSONB,  -- OpenAI 分類的完整結果
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**用途**：
- 記錄每次迭代的失敗案例與分類結果
- 用於驗證回測時查詢失敗案例 ID（`LoopCoordinator._get_failed_scenario_ids()`）
- 用於統計知識缺口分布（按類型、優先級統計）
- 用於追蹤知識生成前的原始問題

**索引建議**：
```sql
CREATE INDEX idx_gap_analysis_loop_iteration ON knowledge_gap_analysis(loop_id, iteration);
CREATE INDEX idx_gap_analysis_scenario ON knowledge_gap_analysis(scenario_id);
CREATE INDEX idx_gap_analysis_cluster ON knowledge_gap_analysis(cluster_id);
```

#### loop_execution_logs（執行日誌）
```sql
CREATE TABLE loop_execution_logs (
    id SERIAL PRIMARY KEY,
    loop_id INTEGER REFERENCES knowledge_completion_loops(id),
    iteration INTEGER,
    event_type VARCHAR(50),  -- loop_started/backtest_executed/gaps_analyzed/etc.
    event_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 目標資料表（知識同步目標）

#### knowledge_base（一般知識庫）
```sql
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    vendor_ids INTEGER[],  -- 支援多業者共享知識
    scope VARCHAR(20) DEFAULT 'vendor',  -- global/vendor/customized
    question_summary TEXT,  -- 問題摘要
    answer TEXT,  -- 答案內容
    keywords TEXT[],
    trigger_mode VARCHAR(20),  -- auto/manual/none
    embedding VECTOR(1536),  -- 向量嵌入（用於語義檢索）
    review_status VARCHAR(20) DEFAULT 'pending_review',  -- pending_review/approved/rejected/need_improvement
    source VARCHAR(50) DEFAULT 'manual',  -- manual/auto_generated/loop
    source_loop_id INTEGER REFERENCES knowledge_completion_loops(id),  -- 來源迴圈 ID（若為 loop 生成）
    source_loop_knowledge_id INTEGER REFERENCES loop_generated_knowledge(id),  -- 來源知識 ID（若為 loop 生成）
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**關鍵欄位說明**：
- `vendor_ids`：支援多業者共享知識（例如：`{1, 2, 3}` 表示三個業者都可使用）
- `scope`：知識範圍優先級（customized > vendor > global）
- `review_status`：
  - `approved`：已批准，驗證通過
  - `need_improvement`：需要改善，驗證失敗但保留
  - `pending_review`：待審核
  - `rejected`：已拒絕
- `source`：追蹤知識來源，loop 生成的知識必須填寫 `source_loop_id` 和 `source_loop_knowledge_id`

#### vendor_sop_items（SOP 項目）
```sql
CREATE TABLE vendor_sop_items (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    category_id INTEGER REFERENCES vendor_sop_categories(id),
    group_id INTEGER REFERENCES vendor_sop_groups(id),
    item_name VARCHAR(200),  -- SOP 項目名稱
    content TEXT,  -- SOP 內容（步驟說明）
    trigger_mode VARCHAR(20) DEFAULT 'auto',  -- auto/manual/none/immediate
    trigger_keywords TEXT[],  -- 觸發關鍵字
    keywords TEXT[],  -- 搜尋關鍵字
    next_action VARCHAR(50),  -- none/form_fill/api_call/form_then_api
    immediate_prompt TEXT,  -- 立即提示文字
    review_status VARCHAR(20) DEFAULT 'pending_review',  -- pending_review/approved/rejected/need_improvement
    source VARCHAR(50) DEFAULT 'manual',  -- manual/auto_generated/loop
    source_loop_id INTEGER REFERENCES knowledge_completion_loops(id),  -- 來源迴圈 ID（若為 loop 生成）
    source_loop_knowledge_id INTEGER REFERENCES loop_generated_knowledge(id),  -- 來源知識 ID（若為 loop 生成）
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**關鍵欄位說明**：
- `item_name`：SOP 項目名稱（需與內容精準匹配，避免過於籠統）
- `content`：完整的 SOP 內容（清晰的步驟說明）
- `trigger_mode`：
  - `auto`：自動觸發（關鍵字或語義匹配）
  - `manual`：僅手動觸發
  - `immediate`：立即觸發（高優先級）
  - `none`：不觸發（已停用）
- `review_status`：與 knowledge_base 相同，支援 `need_improvement` 狀態
- `source`：追蹤來源，loop 生成時必須關聯原始迴圈

---

## 4. 測試情境管理

### 4.1 測試情境資料源

系統**應**使用 `test_scenarios` 資料表作為測試情境的唯一資料源。

**驗收標準**：
- 當執行回測時，系統**應**從 `test_scenarios` 表讀取測試情境
- `test_scenarios` 表**應**為全域共用，所有業者使用相同的測試題庫
- 每個測試情境**應**包含以下欄位：
  - `test_question`：測試問題
  - `difficulty`：難度等級（`easy`/`medium`/`hard`）
  - `status`：情境狀態（`approved`/`pending_review`/`rejected`）
  - `expected_intent_id`：預期意圖 ID（可選）
  - `tags`：標籤（可選）

### 4.2 測試情境篩選

系統**應**支援根據狀態篩選測試情境。

**驗收標準**：
- 系統**應**優先讀取狀態為 `approved` 的測試情境
- 當狀態過濾後題目不足時，系統**可**讀取其他狀態的情境
- `VENDOR_ID` 環境變數**應**用於指定執行回測時使用的業者 RAG 配置，而非篩選測試情境
- 當未指定 `VENDOR_ID` 時，系統**應**預設使用 `vendor_id=2`

### 4.3 批次大小與測試規模

系統**應**支援批次大小限制，控制每次回測的題目數量。

**驗收標準**：
- 系統**應**支援透過 `LoopConfig.batch_size` 參數設定批次大小
- 系統**應**支援任意批次大小（1 至測試情境總數）
- 當測試情境總數小於批次大小時，系統**應**使用實際可用的題目數量

**常見測試規模與使用場景**（建議）：

| 測試規模 | batch_size | 使用場景 | 預計耗時 | 說明 |
|---------|-----------|---------|---------|------|
| 快速驗證 | 50 | 驗證系統穩定性、測試核心功能 | 10-15 分鐘/迭代 | 適合首次測試、功能驗證、快速迭代 |
| 標準測試 | 500 | 正式測試流程、穩定後的常規測試 | 60-90 分鐘/迭代 | 知識生成數量合理（30-50 個）、審核工作量可控 |
| 全面評估 | 3000 | 接近完整題庫的大規模測試 | 90-120 分鐘/迭代 | 適合最終驗證、系統壓力測試 |
| 自訂規模 | 任意數值 | 特殊測試需求 | 依規模而定 | 彈性配置，支援任意批次大小 |

**測試策略建議**：
- **循序漸進原則**：建議按照 50 → 500 → 3000 的順序執行測試
- **先驗證再擴展**：50 題測試通過後再進行更大規模測試
- **多批次策略**：大規模測試可考慮分批執行（例如 6×500 代替 1×3000）
  - 優點：審核工作量分散、可及早發現問題、成本可控
  - 每批次獨立建立新 loop，使用不同的測試集

### 4.4 測試情境選取策略

系統**應**根據明確的策略選取測試情境用於回測，確保測試覆蓋的有效性和系統性。

**驗收標準**：

**初次建立迴圈時的選取策略**：
- 系統**應**從狀態為 `approved` 的測試情境中選取
- 系統**應**支援以下選取方式（擇一實現，建議優先實現選項 A）：
  - **選項 A（建議）**：**分層隨機抽樣**
    - 按難度等級（`easy`/`medium`/`hard`）分層
    - 每層按比例隨機選取（例如：easy 20%、medium 50%、hard 30%）
    - 確保涵蓋不同難度的測試情境
  - **選項 B**：**順序選取**
    - 按 `test_scenarios.id` 順序選取前 N 題
    - 適用於測試情境已按優先級排序的情況
  - **選項 C**：**完全隨機**
    - 從符合條件的測試情境中完全隨機選取 N 題
    - 實現簡單但可能導致難度分布不均
- 選取的測試情境 ID **應**儲存到 `knowledge_completion_loops.scenario_ids` 欄位
- 選取邏輯**應**記錄到 `loop_execution_logs` 表（例如：「選取策略：分層隨機抽樣，共選取 50 題（easy: 10, medium: 25, hard: 15）」）

**驗證回測時的選取策略**：
- 系統**應**只測試本次迭代失敗的測試案例
- 系統**應**透過 `LoopCoordinator._get_failed_scenario_ids()` 方法獲取失敗案例 ID
- 失敗案例 ID **應**從 `knowledge_gap_analysis` 表查詢（條件：`loop_id` 和 `iteration` 匹配）
- 驗證回測**不應**重複測試已通過的案例（節省時間和成本）

**批次間避免重複**：
- 當同一業者建立多個迴圈批次時（透過 `parent_loop_id` 關聯），系統**應**優先選取未在其他批次測試過的情境
- 系統**可**透過查詢關聯批次的 `scenario_ids` 欄位來識別已測試的情境
- 當所有情境都已測試過時，系統**應**允許重複選取，並在日誌中記錄「所有情境已測試，開始重複選取」

**特殊情況處理**：
- 當符合條件的測試情境少於批次大小時，系統**應**使用所有可用情境
- 當測試情境表為空時，系統**應**返回錯誤並記錄到日誌

### 4.5 迭代間測試情境一致性（Critical）

系統**必須**確保同一迴圈的所有迭代使用相同的測試情境，以保證結果的可比較性。

**驗收標準**：

**固定測試集原則**：
- 系統**必須**在第一次迭代（`iteration = 1`）時選取測試情境
- 選取的 scenario_ids **必須**儲存到 `knowledge_completion_loops.scenario_ids` 欄位
- 後續所有迭代（`iteration = 2, 3, ...`）**必須**使用相同的 scenario_ids
- **禁止**在迭代過程中重新選取或變更測試情境

**實現方式**：
- 迴圈啟動時（`POST /api/v1/loops/start`），系統**應**：
  1. 根據策略選取測試情境（例如：分層隨機抽樣 50 題）
  2. 將選取的 scenario_ids 儲存到 `knowledge_completion_loops` 表
  3. 記錄選取策略和分布到 `loop_execution_logs`
- 每次迭代執行時（`POST /api/v1/loops/{loop_id}/execute-iteration`），系統**應**：
  1. 從 `knowledge_completion_loops.scenario_ids` 讀取固定的測試集
  2. 使用此固定測試集執行回測
  3. **不得**重新選取或變更測試情境
- 驗證回測時（`POST /api/v1/loops/{loop_id}/validate`），系統**應**：
  1. 從 `knowledge_completion_loops.scenario_ids` 讀取固定的測試集
  2. 根據驗證範圍配置（failed_only / all / failed_plus_sample）選取子集
  3. 但子集來源**必須**是固定的 scenario_ids

**一致性驗證**：
- 系統**應**在每次迭代前檢查 `scenario_ids` 是否存在
- 如果 `scenario_ids` 為空（資料完整性錯誤），系統**應**：
  - 標記迴圈為 `FAILED`
  - 記錄錯誤：「測試情境 ID 列表遺失，無法保證測試一致性」
  - 拒絕執行迭代

**前端顯示**：
- 迴圈詳情對話框**應**顯示固定測試集資訊：
  - 測試情境總數（例如：50 題）
  - 選取策略（例如：分層隨機抽樣）
  - 難度分布（例如：easy: 10, medium: 25, hard: 15）
  - 測試情境 ID 範圍（例如：ID 1-500 中選取 50 題）
- 提示訊息：「本迴圈使用固定測試集，所有迭代結果可直接比較」

**可比較性保證**：
- 使用固定測試集後，系統可準確追蹤改善幅度：
  ```
  第 1 次迭代：30/50 通過（60%）
  第 2 次迭代：35/50 通過（70%）← 相同的 50 題
  改善幅度：+10%（可靠）
  ```
- 如果每次迭代重新選取，改善幅度將無意義：
  ```
  第 1 次迭代：30/50 通過（60%）← 題目 A
  第 2 次迭代：40/50 通過（80%）← 題目 B（不同題目）
  改善幅度：+20%（❌ 不可靠，無法比較）
  ```

**批次間關係**：
- 不同批次（不同 loop_id）**可以**使用不同的測試集
- 但同一批次內（相同 loop_id）**必須**使用固定測試集
- 範例：
  ```
  Loop 1（批次 1）：scenario_ids = [1, 5, 10, ...]（50 題）
  Loop 2（批次 2）：scenario_ids = [51, 60, 72, ...]（50 題）← 不同測試集，OK

  Loop 1 的所有迭代都使用 [1, 5, 10, ...]
  Loop 2 的所有迭代都使用 [51, 60, 72, ...]
  ```

---

## 5. 回測執行

### 5.1 回測執行架構

系統**應**透過與正式對話流程相同的 API 端點執行回測，確保回測結果能真實反映生產環境表現。

**驗收標準**：

**API 端點與流程**：
- 回測**應**調用 `/api/v1/message` API 端點（與正式對話相同）
- 回測**應**執行完整的對話處理流程：
  - 意圖分類
  - SOP/知識庫檢索
  - 信心度評估
  - LLM 答案優化
  - 業者參數注入

**回測專用配置**：
- 回測請求**應**包含以下特殊參數：
  - `include_debug_info: true`：獲取相似度等調試數據用於評估
  - `session_id: "backtest_session_{scenario_id}"`：每個測試案例使用獨立 session ID，避免表單狀態互相干擾
  - `user_id: "backtest_user_{scenario_id}"`：每個測試案例使用獨立 user ID
  - `mode: "tenant"`：目前僅測試租客場景
  - `skip_sop: false`：允許檢索 SOP
  - `include_sources: true`：包含知識來源

**三層架構**：
- 系統**應**使用三層架構執行回測：
  1. `LoopCoordinator`（`coordinator.py`）：迴圈協調器，管理整體流程
  2. `BacktestFrameworkClient`（`backtest_client.py`）：客戶端封裝層，負責場景載入、記錄創建、結果持久化
  3. `AsyncBacktestFramework`（`scripts/backtest/backtest_framework_async.py`）：底層並發回測引擎，負責並發 HTTP 請求與 LLM 評估

**並發與效能**：
- 回測引擎**應**支援並發執行（預設並發數：5）
- 回測引擎**應**支援超時控制（預設 60 秒）
- 回測引擎**應**支援失敗重試（預設重試 2 次）
- 回測引擎**應**使用 aiohttp 進行異步 HTTP 請求

### 5.2 回測結果記錄

系統**應**記錄每次回測的詳細結果，包括通過/失敗狀態與實際回答內容。

**驗收標準**：
- 每個測試情境**應**記錄以下結果到 `backtest_results` 表：
  - `scenario_id`：對應的測試情境 ID
  - `test_question`：問題內容
  - `system_answer`：RAG 系統實際回答
  - `passed`：是否通過（布林值）
  - `run_id`：回測批次 ID
  - `confidence`：信心度分數
  - `actual_intent`：實際識別的意圖
  - `evaluation`：評估詳情（JSON 格式）
- 系統**應**在 `backtest_runs` 表記錄批次統計：
  - `vendor_id`：執行回測的業者 ID
  - `total_scenarios`：總測試數
  - `passed_count`：通過數
  - `failed_count`：失敗數
  - `pass_rate`：通過率

### 5.3 僅回測模式

系統**應**支援僅執行回測而不進行後續知識生成的模式。

**驗收標準**：
- 當環境變數 `BACKTEST_ONLY=true` 時，系統**應**只執行回測步驟
- 僅回測模式**應**跳過知識缺口分析、分類、生成等步驟
- 僅回測模式**應**輸出回測統計結果後正常結束

---

## 6. 知識缺口分析與分類

### 6.1 知識缺口識別

系統**應**從回測結果中篩選出失敗案例，作為知識缺口進行分析。

**驗收標準**：
- 系統**應**篩選 `passed = false` 的回測結果
- 系統**應**收集失敗案例的以下資訊：
  - 失敗的問題
  - 預期答案
  - 實際答案（RAG 系統給出的錯誤答案）
  - 失敗原因類別
- 系統**應**統計失敗案例總數並記錄到 `loop_execution_logs`

### 6.2 OpenAI 智能分類（4 類）

系統**應**使用 OpenAI API (GPT-4o-mini) 對失敗案例進行 4 類分類。

**驗收標準**：
- 系統**應**調用 `GapClassifier.classify_gaps_batch()` 方法
- 系統**應**將失敗案例分類為以下 4 類：
  1. **sop_knowledge**：SOP 業務流程知識（如：退租流程、續約流程、寵物政策）
  2. **form_fill**：表單填寫流程（如：我想找房、我想退租、申請維修）
  3. **system_config**：系統操作與配置（如：如何切換團隊、忘記密碼、匯出發票）
  4. **api_query**：API 動態查詢（如：租金多少、我的合約何時到期）
- 分類**應**基於問題的語意內容，而非關鍵字匹配
- 每個問題**應**被明確歸類到唯一一個分類

### 6.3 分類結果標注

系統**應**為每個分類標注是否需要生成靜態知識，並對 api_query 類型的問題進行特殊處理。

**驗收標準**：

**靜態知識生成標記**：
- `sop_knowledge`、`form_fill`、`system_config` **應**標記為 `should_generate_knowledge: true`
- `api_query` **應**標記為 `should_generate_knowledge: false`
- 系統**應**過濾掉 `should_generate_knowledge: false` 的問題，不進行聚類與生成步驟

**api_query 類型的後續處理**：
- 系統**應**將 api_query 類型的問題記錄到 `loop_execution_logs`，event_type = `api_implementation_needed`
- 記錄的 `event_data` **應**包含以下資訊：
  ```json
  {
    "api_queries": [
      {
        "scenario_id": 123,
        "question": "我的租金多少？",
        "frequency": 1,
        "priority": "p0"
      },
      {
        "scenario_id": 124,
        "question": "我的合約何時到期？",
        "frequency": 1,
        "priority": "p1"
      }
    ],
    "total_count": 2,
    "high_priority_count": 1
  }
  ```
- 系統**應**在迭代結果中返回 api_query 統計：
  - `api_queries_count`：api_query 類型問題總數
  - `high_priority_api_queries`：高優先級（p0）的 api_query 數量
- 前端迴圈詳情對話框**應**顯示「待實現 API 清單」區塊：
  - 顯示 api_query 類型問題列表
  - 按優先級排序（p0 > p1 > p2）
  - 顯示問題內容和優先級標籤
  - 提供「匯出清單」按鈕（CSV 或 JSON 格式）
- 管理員**可**根據此清單優先實現高頻、高優先級的 API 查詢功能

**特殊情況處理**：
- 如果一次迭代所有問題都被分類為 api_query（無靜態知識可生成），系統**應**：
  - 跳過聚類與生成步驟
  - 記錄事件到 `loop_execution_logs`：「所有問題需 API 實現，無靜態知識可生成」
  - 將狀態轉為 `REVIEWING`（雖無知識可審核，但需人工決定下一步）
  - 前端顯示提示：「本次迭代識別出 N 個 API 查詢需求，無靜態知識生成。請查看待實現 API 清單」

### 6.4 類別分離與聚類

系統**應**將需要生成知識的問題按類別分離，並分別聚類。

**驗收標準**：

**類別分離**：
- **SOP 組**：包含 `sop_knowledge` 和 `form_fill` 類別的問題
- **Knowledge 組**：包含 `system_config` 類別的問題

**分別聚類**：
- 系統**應**對 SOP 組與 Knowledge 組分別執行聚類
- 系統**應**調用 `GapClassifier.get_clusters_for_generation()` 方法
- 聚類**應**使用 OpenAI API 進行語意相似度判斷
- 每個聚類（cluster）**應**包含 2-5 個高度相關的問題
- 聚類**應**遵循「適度聚類」原則：只有可用同一 SOP/知識完整回答的問題才聚類
- 每個聚類**應**選出一個代表性問題作為主問題
- 聚類結果**應**包含：
  - `cluster_id`：聚類 ID
  - `cluster_name`：聚類名稱（如：「租金支付流程」）
  - `questions`：包含的問題列表
  - `representative_question`：代表性問題

---

## 7. 知識生成

### 7.1 知識生成路由

系統**應**根據聚類所屬的組別，將聚類路由到對應的生成器。

**驗收標準**：
- SOP 組的聚類**應**路由到 `SOPGenerator`
- Knowledge 組的聚類**應**路由到 `KnowledgeGeneratorClient`
- 路由決策**應**基於聚類的分類標籤

### 7.2 SOP 生成

系統**應**使用 OpenAI API 為 SOP 組聚類生成結構化 SOP 文檔，並在生成前檢測是否存在重複或相似的 SOP。

**驗收標準**：

**基本生成要求**：
- 系統**應**調用 `SOPGenerator.generate_sop_batch()` 方法
- 生成的 SOP **應**包含以下欄位：
  - `title`：SOP 標題
  - `steps`：步驟列表（JSON 格式）
  - `keywords`：關鍵字列表
  - `applicable_questions`：可回答的問題列表
  - `category_id`：建議的 SOP 分類 ID
  - `group_id`：建議的 SOP 群組 ID
- 系統**應**自動選擇最合適的 `category_id` 和 `group_id`（從 `vendor_sop_categories` 和 `vendor_sop_groups` 表讀取）
- 生成的 SOP **應**寫入 `loop_generated_knowledge` 表，狀態設為 `pending`
- `loop_generated_knowledge.knowledge_type` **應**設為 `'sop'`
- `loop_generated_knowledge.sop_config` **應**包含 SOP 配置（JSON）

**重複 SOP 檢測機制**：
- 系統**應**在生成 SOP 前檢查是否存在相似的 SOP，避免生成重複知識
- 檢查範圍**應**包含：
  - `vendor_sop_items` 表中的現有 SOP（條件：同業者 `vendor_id`）
  - `loop_generated_knowledge` 表中的待審核/已批准 SOP（條件：`knowledge_type = 'sop'` 且 `status IN ('pending', 'approved')`）
- 相似度判斷**應**基於以下方式之一（擇一實現，建議優先實現選項 A）：
  - **選項 A（建議）**：**Embedding 語義相似度**
    - 計算待生成 SOP 標題的 embedding 與現有 SOP 標題的 cosine similarity
    - 閾值建議：similarity > 0.85 視為相似
    - 優點：能識別語義相同但表述不同的 SOP（例如「續約流程」與「租約續訂流程」）
  - **選項 B**：**關鍵字重疊度**
    - 計算待生成 SOP 與現有 SOP 的關鍵字交集比例
    - 閾值建議：交集比例 > 0.7 視為相似
    - 優點：實現簡單，無需調用 embedding API
  - **選項 C**：**LLM 語義判斷**
    - 使用 LLM（例如 GPT-4o-mini）判斷兩個 SOP 是否語義相似
    - 優點：準確度最高，能理解複雜語義關係
    - 缺點：成本較高，延遲較大
- 當檢測到相似 SOP 時，系統**應**執行以下操作之一（擇一實現，建議優先實現選項 B）：
  - **選項 A**：**跳過生成**
    - 不生成該 SOP
    - 記錄到 `loop_execution_logs` 表（例如：「跳過 SOP 生成：檢測到相似 SOP (ID: 123, 相似度: 0.92)」）
    - 優點：避免生成重複知識，節省成本
    - 缺點：可能誤判而錯過有價值的 SOP
  - **選項 B（建議）**：**標註相似度供人工判斷**
    - 仍生成 SOP 並寫入 `loop_generated_knowledge` 表
    - 在 `sop_config` 中新增 `similar_sops` 欄位，記錄相似的現有 SOP 資訊（包含 ID、標題、相似度分數）
    - 前端審核介面**應**顯示相似 SOP 警告，供審核人員判斷是否保留
    - 優點：保留最終決策權給人工，避免誤判
  - **選項 C**：**合併到現有 SOP**
    - 不生成新 SOP，而是更新現有 SOP 的內容（例如補充步驟或適用問題）
    - 優點：避免重複，同時改善現有 SOP
    - 缺點：實現複雜度高，可能破壞現有 SOP 結構
- 重複檢測結果**應**記錄到 `loop_execution_logs` 表，包含以下資訊：
  - 檢測到的相似 SOP 數量
  - 被跳過或標註的 SOP 清單
  - 相似度分數分布（例如：「0.85-0.90: 2 個，0.90-0.95: 1 個」）

**檢測效能要求**：
- 當現有 SOP 數量超過 1000 時，系統**應**使用向量索引（例如 pgvector 的 IVFFlat 索引）加速相似度搜尋
- 重複檢測**不應**顯著延長知識生成時間（建議增加時間 < 10%）

### 7.3 一般知識生成

系統**應**使用 OpenAI API 為 Knowledge 組聚類生成問答式知識文檔，並在生成前檢測是否存在重複或相似的知識。

**驗收標準**：

**基本生成要求**：
- 系統**應**調用 `KnowledgeGeneratorClient.generate_knowledge_batch()` 方法
- 生成的知識**應**包含以下欄位：
  - `question`：問題（使用聚類的代表性問題）
  - `answer`：答案（由 OpenAI 生成）
  - `keywords`：關鍵字列表
  - `related_questions`：相關問題列表（聚類中的其他問題）
- 生成的知識**應**寫入 `loop_generated_knowledge` 表，狀態設為 `pending`
- `loop_generated_knowledge.knowledge_type` **應**設為 `null`（表示一般知識）

**重複知識檢測機制**：
- 系統**應**在生成知識前檢查是否存在相似的知識，避免生成重複內容
- 檢查範圍**應**包含：
  - `knowledge_base` 表中的現有知識（條件：同業者 `vendor_id` 或 `vendor_ids` 包含該業者 ID）
  - `loop_generated_knowledge` 表中的待審核/已批准知識（條件：`knowledge_type IS NULL` 且 `status IN ('pending', 'approved')`）
- 相似度判斷**應**基於以下方式之一（擇一實現，建議優先實現選項 A）：
  - **選項 A（建議）**：**Embedding 語義相似度**
    - 計算待生成知識的 `question_summary` 的 embedding 與現有知識的 `question_summary` 的 cosine similarity
    - 閾值建議：similarity > 0.90 視為相似（比 SOP 更嚴格，因為問答式知識更精確）
    - 優點：能識別語義相同但表述不同的問題（例如「租金幾號繳？」與「每月租金繳納日期是？」）
  - **選項 B**：**關鍵字重疊度**
    - 計算待生成知識與現有知識的關鍵字交集比例
    - 閾值建議：交集比例 > 0.75 視為相似
    - 優點：實現簡單，無需調用 embedding API
  - **選項 C**：**LLM 語義判斷**
    - 使用 LLM（例如 GPT-4o-mini）判斷兩個問題是否語義相似
    - 優點：準確度最高，能理解問題間的細微差異
    - 缺點：成本較高，延遲較大
- 當檢測到相似知識時，系統**應**執行以下操作之一（擇一實現，建議優先實現選項 B）：
  - **選項 A**：**跳過生成**
    - 不生成該知識
    - 記錄到 `loop_execution_logs` 表（例如：「跳過知識生成：檢測到相似知識 (KB ID: 456, 相似度: 0.93)」）
    - 優點：避免生成重複知識，節省成本
    - 缺點：可能誤判而錯過有價值的知識
  - **選項 B（建議）**：**標註相似度供人工判斷**
    - 仍生成知識並寫入 `loop_generated_knowledge` 表
    - 在記錄中新增 `similar_knowledge` 欄位（JSON），記錄相似的現有知識資訊（包含 ID、問題摘要、相似度分數、來源表）
    - 前端審核介面**應**顯示相似知識警告，供審核人員判斷是否保留或合併
    - 優點：保留最終決策權給人工，避免誤判
  - **選項 C**：**合併到現有知識**
    - 不生成新知識，而是更新現有知識的答案內容（例如補充資訊）
    - 優點：避免重複，同時改善現有知識
    - 缺點：實現複雜度高，可能破壞現有答案結構
- 重複檢測結果**應**記錄到 `loop_execution_logs` 表，包含以下資訊：
  - 檢測到的相似知識數量
  - 被跳過或標註的知識清單
  - 相似度分數分布（例如：「0.90-0.92: 3 個，0.92-0.95: 2 個」）

**檢測效能要求**：
- 當現有知識數量超過 5000 時，系統**應**使用向量索引（pgvector 的 `embedding` 欄位已有 IVFFlat 索引）加速相似度搜尋
- 重複檢測**不應**顯著延長知識生成時間（建議增加時間 < 10%）

**欄位使用說明**（選項 B 實現時）：
- 系統**應**將相似知識資訊寫入 `loop_generated_knowledge.similar_knowledge` 欄位
- 欄位格式參見 Section 3.1 的 `loop_generated_knowledge` 表定義
- 前端審核介面**應**讀取此欄位並顯示相似知識警告

### 7.4 生成結果記錄

系統**應**記錄每次知識生成的元數據到迴圈執行日誌。

**驗收標準**：
- 系統**應**在 `loop_execution_logs` 表記錄以下事件：
  - 生成開始時間
  - 生成的知識數量（SOP 與一般知識分別統計）
  - OpenAI API 調用次數與成本
  - 生成完成時間
- 系統**應**將生成的知識關聯到對應的 `loop_id` 和 `iteration`

---

## 8. 人工審核

### 8.1 待審核知識查詢

系統**應**提供 API 端點供前端查詢待審核的知識。

**驗收標準**：
- 系統**應**提供 `GET /api/v1/loop-knowledge/pending` 端點
- 端點**應**返回狀態為 `pending` 的所有知識項目
- 返回結果**應**包含：
  - 知識 ID
  - 問題
  - 答案
  - 知識類型（`sop` 或 `null`）
  - SOP 配置（若為 SOP）
  - 生成時間

### 8.2 知識審核與立即同步

系統**應**提供 API 端點供使用者審核知識，審核通過後立即同步到正式知識庫。

**驗收標準**：

**審核操作**：
- 系統**應**提供 `POST /api/v1/loop-knowledge/{knowledge_id}/review` 端點
- 審核請求**應**支援以下操作：
  - `approve`：通過審核
  - `reject`：拒絕審核
- 審核請求**應**允許修改以下欄位：
  - `question`：修改問題
  - `answer`：修改答案
  - `keywords`：修改關鍵字
  - SOP 特有欄位：`vendor_id`、`category_id`、`group_id`

**立即同步機制**：
- 當一般知識審核通過時，系統**應**立即將其同步到 `knowledge_base` 表
- 當 SOP 審核通過時，系統**應**立即將其同步到 `vendor_sop_items` 表
- 同步時**應**生成對應的 `embedding` 向量（調用 embedding API）
- 同步時**應**設定正確的 `trigger_mode`（關鍵字觸發映射為 `auto`）
- 同步時**應**設定 `review_status = 'approved'`
- 同步完成後，`loop_generated_knowledge` 的狀態**應**更新為 `synced`
- 同步失敗時，系統**應**保持 `approved` 狀態並記錄錯誤訊息

**RAG 查詢即時生效**：
- 同步完成後，RAG API（`/api/v1/message`）**應**立即能夠檢索到新增的知識
- 無需重啟服務或刷新緩存

### 8.3 批量審核功能（Critical）

系統**應**提供批量審核功能，支援一次性審核多個知識項目，以提升審核效率。

**驗收標準**：

**批量審核 API**：
- 系統**應**提供 `POST /api/v1/loop-knowledge/batch-review` 端點
- 端點**應**接受以下請求參數：
  ```json
  {
    "knowledge_ids": [123, 124, 125, ...],  // 待審核的知識 ID 列表
    "action": "approve",                     // 'approve' 或 'reject'
    "modifications": {                       // 可選：批量修改欄位
      "keywords": ["關鍵字1", "關鍵字2"]     // 例如：統一添加關鍵字
    }
  }
  ```
- 端點**應**返回批量處理結果：
  ```json
  {
    "total": 10,
    "successful": 9,
    "failed": 1,
    "failed_items": [
      {
        "knowledge_id": 125,
        "error": "同步失敗：embedding 生成超時"
      }
    ]
  }
  ```

**批量處理邏輯**：
- 系統**應**按順序處理每個知識項目（避免併發衝突）
- 對每個項目執行與單一審核相同的操作：
  - 更新狀態（approved / rejected）
  - 立即同步到正式庫（若為 approve）
  - 生成 embedding
  - 記錄到 loop_execution_logs
- 如果某個項目失敗，系統**應**：
  - 繼續處理剩餘項目（不中斷整個批次）
  - 記錄失敗項目到返回結果
  - 失敗項目保持原狀態（pending），可稍後重試
- 批量處理完成後，系統**應**記錄統計資訊到 `loop_execution_logs`：
  ```json
  {
    "event_type": "batch_review_completed",
    "event_data": {
      "total": 10,
      "approved": 9,
      "rejected": 0,
      "failed": 1,
      "duration_ms": 1500
    }
  }
  ```

**前端批量選取功能**：
- 審核中心的迴圈知識審核 Tab **應**提供批量操作界面：

  **全選功能**：
  - 列表頂部**應**顯示「全選」核取方塊
  - 點擊「全選」**應**選取當前頁面所有待審核知識
  - 或提供「全選所有」按鈕，選取所有待審核知識（跨頁）

  **篩選後全選**：
  - 系統**應**支援先篩選再全選：
    - 例如：篩選「知識類型 = SOP」→ 全選 → 批量批准
    - 例如：篩選「相似度警告 = 無」→ 全選 → 批量批准

  **個別選取**：
  - 每個知識項目**應**顯示核取方塊
  - 使用者**可**勾選特定項目（支援 Shift 多選）

  **批量操作按鈕**：
  - 當選取 ≥ 1 個項目時，**應**顯示批量操作工具列：
    - 「批量批准」按鈕（綠色）
    - 「批量拒絕」按鈕（紅色）
    - 顯示已選取數量：「已選取 15 個項目」

  **確認對話框**：
  - 點擊批量操作按鈕時，**應**彈出確認對話框：
    ```
    批量批准確認

    您即將批准 15 個知識項目，這些知識將立即同步到正式知識庫並生效。

    知識類型分布：
    - SOP: 8 個
    - 一般知識: 7 個

    其中 2 個項目有相似知識警告，請確認是否繼續。

    [取消] [確認批准]
    ```

  **處理進度顯示**：
  - 批量處理時**應**顯示進度條：
    - 「處理中...（5/15）」
    - 顯示當前處理的項目名稱
  - 完成後**應**顯示結果摘要：
    ```
    批量審核完成

    總計：15 個項目
    成功：14 個
    失敗：1 個

    失敗項目：
    - [ID: 125] 租金繳納流程：同步失敗（embedding 生成超時）

    [關閉] [重試失敗項目]
    ```

**批量修改功能（可選）**：
- 系統**可**支援批量修改共同欄位：
  - 批量添加關鍵字
  - 批量設定 vendor_id（針對 SOP）
  - 批量設定 trigger_mode
- 修改界面**應**清楚標示哪些欄位會被統一修改
- 修改後**應**在確認對話框中預覽變更

**效能要求**：
- 批量審核 10 個項目**應**在 5 秒內完成（不含 embedding 生成時間）
- 批量審核 50 個項目**應**在 20 秒內完成
- 系統**應**使用資料庫事務確保批次處理的原子性（同一批次內的多個 knowledge 同時成功或失敗）

**使用場景範例**：
```
場景 1：快速批准無爭議知識
1. 篩選「相似度警告 = 無」
2. 全選（10 個項目）
3. 點擊「批量批准」
4. 確認對話框 → 確認
5. 5 秒內完成，所有知識已同步

場景 2：分類審核
1. 篩選「知識類型 = 一般知識」
2. 逐一檢視，勾選 7 個合格項目
3. 批量批准 7 個
4. 切換篩選「知識類型 = SOP」
5. 勾選 5 個合格 SOP
6. 批量批准 5 個

場景 3：大批次審核（500 題回測）
- 生成 40 個知識項目
- 分段審核：
  - 第 1 段：1-20 號（批量批准 15 個）
  - 第 2 段：21-40 號（批量批准 18 個）
- 總審核時間：15 分鐘（vs 逐一審核需 40 分鐘）
```

### 8.4 SOP 欄位預填

系統**應**為 SOP 類型的知識提供智能欄位預填功能。

**驗收標準**：
- SOP 的 `vendor_id`、`category_id`、`group_id` **應**從 `sop_config` 自動預填到審核表單
- 使用者**應**能夠在審核時修改預填的欄位值
- 修改後的欄位值**應**在同步時使用

---

## 9. 驗證效果回測

> **⚠️ 功能狀態**：可選功能（Optional Feature）
>
> **說明**：本章節描述的「驗證效果回測」功能在實務上為**可選功能**，原因如下：
> 1. 每次迭代已經執行完整回測，自然驗證知識改善效果
> 2. 下一次迭代的回測結果即可反映知識效果，無需額外驗證步驟
> 3. 人工審核階段已經對知識品質進行把關
>
> **建議使用場景**：
> - 需要在迭代之間快速驗證特定知識的改善效果
> - 需要檢測 regression（新知識是否影響原本通過的案例）
> - 對知識品質有特別高的要求
>
> **標準工作流程**：
> ```
> 迭代 1 → 審核批准 → 迭代 2 → 審核批准 → 迭代 3 → ...
> （每次迭代的回測已經驗證知識效果）
> ```

### 9.1 流程概述

系統**可**提供驗證回測功能，用於在迭代之間快速確認已同步知識的改善效果。

**驗證流程**：
```
審核通過 → 立即同步到 knowledge_base/vendor_sop_items
    ↓
RAG 查詢立即生效
    ↓
執行驗證回測（測試原本失敗的案例）
    ↓
計算改善幅度
    ↓
驗證通過：保持 review_status = 'approved'，繼續迭代
驗證失敗：標記 review_status = 'need_improvement'，可選擇調整或繼續迭代
```

### 9.2 驗證回測執行

> **⚠️ 提醒**：此功能為可選實作，標準工作流程使用每次迭代的回測即可驗證知識效果。

**驗收標準**（如果選擇實作此功能）：

**API 端點**：
- 系統**可**提供 `POST /api/v1/loops/{loop_id}/validate` 端點
- 端點**應**調用 `LoopCoordinator.validate_loop()` 方法

**驗證回測邏輯**：
- 驗證回測**應**使用正式的 RAG API（`/api/v1/message`），自然包含已同步的新知識
- 驗證回測**應**計算改善幅度（新通過率 - 舊通過率）
- 驗證回測**應**記錄測試結果到 `backtest_results` 表

**驗證範圍選項**（擇一實現，建議優先實現選項 A）：
- **選項 A（當前，快速但可能遺漏 regression）**：
  - 只測試原本失敗的案例（透過 `_get_failed_scenario_ids()` 獲取）
  - 優點：快速、成本低（例如：50 題中僅測試 20 個失敗案例）
  - 缺點：無法發現新知識是否導致原本通過的案例反而失敗（regression）
  - 適用場景：快速迭代、成本敏感
- **選項 B（完整但成本高）**：
  - 測試所有案例（本批次的全部 50 題）
  - 優點：能發現 regression，確保整體質量不下降
  - 缺點：時間和成本較高（每次驗證都需測試完整批次）
  - 適用場景：質量要求高、預算充足
- **選項 C（建議，折衷方案）**：
  - 測試失敗案例 + 隨機抽樣 20% 通過案例
  - 例如：20 個失敗案例 + 6 個隨機抽樣的通過案例（總共 26 題）
  - 優點：平衡成本與 regression 檢測
  - 缺點：仍有小概率遺漏 regression
  - 適用場景：大多數生產環境

**驗證範圍配置**：
- 系統**應**支援透過 `LoopConfig.validation_scope` 參數配置驗證範圍：
  - `failed_only`：僅失敗案例（選項 A）
  - `all`：所有案例（選項 B）
  - `failed_plus_sample`：失敗案例 + 抽樣（選項 C，預設）
- 系統**應**支援透過 `LoopConfig.sample_pass_rate` 參數配置抽樣比例（預設 0.2，即 20%）
- 驗證範圍**應**記錄到 `loop_execution_logs`，包含測試案例總數和選取策略

**Regression 檢測（選項 B 和 C）**：
- 如果檢測到原本通過的案例現在失敗（regression），系統**應**：
  - 記錄 regression 案例到 `loop_execution_logs`，event_type = `regression_detected`
  - 在驗證結果中返回 `regression_count` 和 `regression_scenarios`
  - 前端**應**顯示警告：「檢測到 N 個 regression 案例，新知識可能影響現有回答」
  - 驗證判定為失敗（即使改善幅度達標）

**驗證通過條件**：
- 改善幅度 >= 5% **或** 通過率 >= 70%
- **且** 無 regression（如果使用選項 B 或 C）

### 9.3 驗證結果處理

> **⚠️ 提醒**：此功能為可選實作。

**驗收標準**（如果選擇實作此功能）：

**驗證通過後操作**：
- 系統**應**保持已同步知識的 `review_status = 'approved'`
- 系統**應**將迴圈狀態轉換為 `RUNNING`
- 系統**應**記錄驗證成功事件到 `loop_execution_logs`

**驗證失敗後操作**：
- 系統**應**將本次迭代同步的知識標記為 `review_status = 'need_improvement'`
- 系統**應**保持知識在 knowledge_base/vendor_sop_items 表中（不刪除）
- 系統**應**將迴圈狀態保持為 `REVIEWING` 或轉回 `RUNNING`（根據用戶選擇）
- 系統**應**記錄驗證失敗事件到 `loop_execution_logs`

**返回內容**：
- 端點**應**返回驗證結果：
  - `validation_result`：
    - `pass_rate`：新通過率
    - `improvement`：改善幅度（百分比）
    - `total`：測試總數
    - `passed`：通過數
    - `failed`：失敗數
  - `validation_passed`：是否通過驗證（布林值）
  - `affected_knowledge_ids`：受影響的知識 ID 列表
  - `status`：當前迴圈狀態
  - `next_action`：下一步操作建議（`continue` 或 `adjust_knowledge`）

### 9.4 待改善知識處理

> **⚠️ 提醒**：此功能為可選實作，僅在實作 Section 9.2 驗證效果回測時需要。

**驗收標準**（如果選擇實作此功能）：

**標記機制**：
- 系統**應**在 `knowledge_base` 和 `vendor_sop_items` 表的 `review_status` 欄位支援以下狀態：
  - `approved`：已批准，驗證通過
  - `need_improvement`：需要改善，驗證失敗
  - `pending_review`：待審核

**後續處理選項**：
- 用戶**可**選擇重新調整待改善的知識內容
- 用戶**可**選擇保留這些知識，繼續下一次迭代累積更多知識
- 用戶**可**選擇刪除這些知識（手動操作）

### 9.5 完整驗證流程範例

> **⚠️ 提醒**：以下範例描述可選的驗證效果回測流程。標準工作流程使用每次迭代的回測即可驗證知識效果。

**範例：使用驗證效果回測（可選）**
```
1. 用戶在審核中心審核 8 個 AI 生成的知識
   → 修改 2 個內容
   → 批准 6 個，拒絕 2 個

2. 批准時立即同步
   → 6 個知識同步到 knowledge_base/vendor_sop_items
   → review_status = 'approved'
   → RAG 查詢立即可以搜尋到這些知識

3. 用戶點擊「驗證效果」（可選步驟）
   → POST /api/v1/loops/{loop_id}/validate
   → 系統執行回測（只測原本失敗的 20 題）
   → 計算改善幅度

4. 驗證通過（改善幅度 12%，從 60% → 72%）：
   → 知識保持 review_status = 'approved'
   → 迴圈狀態轉回 RUNNING
   → 可繼續下一次迭代

5. 驗證失敗（改善幅度 2%，從 60% → 62%）：
   → 6 個知識標記為 review_status = 'need_improvement'
   → 知識仍保留在正式庫（RAG 仍可搜尋）
   → 用戶選擇：
     A. 調整這些知識內容，重新驗證
     B. 繼續下一次迭代，累積更多知識後一併驗證
```

**標準工作流程（推薦）**
```
1. 迭代 1：回測 + 生成知識
   → 通過率: 50%

2. 人工審核並批准
   → 立即同步到知識庫

3. 迭代 2：回測驗證
   → 通過率: 60%（自然反映知識效果）
   → 無需額外的驗證步驟

4. 人工修正/優化知識

5. 迭代 3：繼續驗證
   → 通過率: 70%
```

---

## 10. 迭代控制與批次管理

### 10.1 迴圈狀態管理

系統**應**透過狀態機管理完整的迴圈生命週期。

**驗收標準**：
- 系統**應**在 `knowledge_completion_loops` 表記錄迴圈執行記錄
- 迴圈狀態**應**包含：
  - `PENDING`：待執行
  - `RUNNING`：執行中（可執行迭代）
  - `REVIEWING`：審核中（等待人工審核知識）
  - `VALIDATING`：驗證中（執行驗證回測）
  - `SYNCING`：同步中（同步知識到正式庫）
  - `COMPLETED`：已完成
  - `FAILED`：失敗
  - `PAUSED`：已暫停
  - `CANCELLED`：已取消
- 每次啟動新迴圈時，系統**應**創建新的 `loop_id`
- 迴圈記錄**應**包含：
  - 目標通過率（target_pass_rate，預設 0.85）
  - 最大迭代次數（max_iterations，預設 10）
  - 當前迭代次數
  - 當前通過率
  - 測試情境 ID 列表（scenario_ids）

### 10.2 人工控制迭代模式與非同步執行

系統**應**支援人工控制的迭代模式，每次迭代完成後等待人工決策。

**驗收標準**：

**迭代執行 API**：
- 系統**應**提供 `POST /api/v1/loops/{loop_id}/execute-iteration` 端點
- 端點**應**調用 `LoopCoordinator.execute_iteration()` 方法
- 只有當迴圈狀態為 `RUNNING` 時才能執行
- 端點**應**執行完整的 8 步驟流程（回測 → 分析 → 分類 → 聚類 → 生成）

**非同步執行模式（Critical）**：
- 端點**必須**支援非同步執行模式，以避免前端 HTTP 請求超時
- 非同步模式**應**為預設行為（`async: true`）
- 非同步執行流程：
  1. API 立即返回（< 1 秒），狀態為 `RUNNING`
  2. 後端在背景執行迭代（使用背景任務或獨立執行緒）
  3. 執行期間持續更新 loop 狀態與進度到資料庫
  4. 前端透過輪詢 `GET /api/v1/loops/{loop_id}` 追蹤進度
  5. 執行完成後狀態轉為 `REVIEWING`
- 系統**應**防止同一 loop 並發執行多個迭代
  - 當迭代執行中時，再次調用**應**返回 409 Conflict 錯誤
  - 錯誤訊息：「迭代已在執行中，請等待完成」

**Timeout 風險與解決方案**：
- **問題**：測試規模較大時（50 題：10-15 分鐘，500 題：60-90 分鐘，3000 題：90-120 分鐘），同步執行會導致前端 HTTP 請求超時（一般為 30-60 秒）
- **解決方案**：使用非同步執行 + 前端輪詢狀態的方式
- **同步模式**：僅供命令列腳本使用（調試用），前端**不應**使用同步模式

**返回內容**：
- 端點**應**返回迭代結果：
  - `current_iteration`：當前迭代次數
  - `backtest_result`：回測結果（通過率、總數、通過數、失敗數）
  - `gap_analysis`：知識缺口分析（總數、分類統計）
  - `generated_knowledge`：生成的知識統計（SOP 數、一般知識數）
  - `cost_summary`：成本統計（總成本、API 調用次數、token 數）
  - `next_action`：下一步操作（`wait_for_review`）

**迭代後狀態管理**：
- 每次迭代執行完成後，系統**應**將狀態轉換為 `REVIEWING`
- 系統**應**等待人工審核知識
- 人工審核完成後（批准的知識立即同步到正式庫），可觸發 `POST /api/v1/loops/{loop_id}/validate` 驗證效果
- 驗證完成後，狀態**應**轉回 `RUNNING`，可執行下一次迭代或完成批次

**自動完成條件檢查**：
- 系統**應**在每次迭代後檢查完成條件：
  - 通過率 >= 目標通過率（預設 85%）
  - 達到最大迭代次數（預設 10）
- 當達到完成條件時，系統**應**在返回結果中提示，但不自動標記為 `COMPLETED`
- 人工**應**透過 `complete-batch` API 明確標記批次完成

### 10.3 同批次重測驗證

系統**應**在每次迭代後，使用相同的測試批次重新執行回測，驗證新增知識的有效性。

**驗收標準**：
- 系統**應**保存第一次迭代使用的測試情境 ID 列表到 `scenario_ids` 欄位
- 後續迭代**應**使用相同的測試情境 ID 列表進行回測
- 系統**應**記錄每次迭代的通過率變化趨勢

### 10.4 批次完成與下一批次管理

系統**應**支援人工標記當前批次完成，並啟動下一批次的回測與完善流程。

**批次迭代流程說明**：
```
Loop #84（第一批次：50 題）
  ├─ 迭代 1：回測 + 生成知識 → 審核批准
  ├─ 迭代 2：回測驗證 → 修正知識
  ├─ 迭代 3：回測驗證 → 持續優化
  └─ 達標（通過率 >= 85%）→ 批次完成

[Loop #84 完成，滿意]

Loop #85（第二批次：另 50 題）
  ├─ 迭代 1：回測 + 生成知識 → 審核批准
  ├─ 迭代 2-N：持續迭代優化
  └─ 達標 → 批次完成

[Loop #85 完成，滿意]

Loop #86（第三批次：再 50 題）
  └─ 以此類推...
```

**關鍵概念**：
- **批次（Loop）**：一組固定的測試情境（例如 50 題），對應一個 `loop_id`
- **迭代（Iteration）**：在同一批次內反覆執行回測、生成知識、優化流程
- **批次完成**：當前批次達到目標通過率，人工滿意後標記完成
- **下一批次**：啟動新的 `loop_id`，測試新的一組題目

**驗收標準**：

**批次完成 API**：
- 系統**應**提供 `POST /api/v1/loops/{loop_id}/complete-batch` 端點
- 端點**應**執行以下操作：
  - 驗證迴圈狀態為 `RUNNING`
  - 記錄批次完成事件到 `loop_execution_logs`
  - 將迴圈狀態標記為 `COMPLETED`
  - 記錄完成時間到 `completed_at`
  - 返回批次統計摘要（總迭代次數、最終通過率、總成本、生成知識數）

**下一批次啟動 API**：
- 系統**應**提供 `POST /api/v1/loops/start-next-batch` 端點
- 端點**應**接受以下參數：
  - `previous_loop_id`：前一批次的迴圈 ID（可選）
  - `vendor_id`：業者 ID
  - `batch_size`：批次大小（可選，預設繼承前批次）
  - `target_pass_rate`：目標通過率（可選，預設繼承前批次）
  - `scenario_filters`：測試情境篩選條件（可選）
- 端點**應**執行以下操作：
  - 創建新的迴圈記錄（新的 `loop_id`）
  - 記錄 `parent_loop_id`（如果提供）以關聯批次
  - 繼承前批次配置（如果提供 `previous_loop_id`）
  - 自動識別尚未處理的測試情境
  - 返回新迴圈的基本資訊

**批次關聯追蹤**：
- `knowledge_completion_loops` 表**應**使用 `parent_loop_id` 欄位追蹤批次關聯
- 系統**應**支援查詢批次關聯樹狀結構
- 系統**應**記錄每個批次的測試情境範圍（scenario_ids）

### 10.5 暫停、恢復與取消

系統**應**支援迴圈的暫停、恢復與取消操作，確保流程可控與可追溯。

**驗收標準**：

**暫停行為（Pause）**：
- 系統**應**在當前步驟完成後才執行暫停（不中斷正在執行的 LLM 調用或資料庫事務）
- 暫停時**應**將狀態從當前狀態（`RUNNING`/`REVIEWING`/`VALIDATING`）轉為 `PAUSED`
- 暫停時**應**記錄以下資訊到 `loop_execution_logs`：
  - 暫停前的狀態
  - 當前進度（迭代次數、已生成知識數、已審核知識數）
  - 暫停時間
- 前端**應**在以下狀態顯示「暫停」按鈕：
  - `RUNNING`：可暫停（等待下次迭代執行）
  - `REVIEWING`：可暫停（審核進行中）
  - `VALIDATING`：不建議暫停（驗證回測進行中，應等待完成）
- 暫停時前端**應**彈出確認對話框：「確定暫停迴圈？已生成但未審核的知識將保留」

**恢復行為（Resume）**：
- 恢復時**應**檢查資料完整性：
  - 是否有待審核知識未處理（`status = 'pending'`）
  - 是否有失敗的驗證需要重試
- 恢復時**應**將狀態從 `PAUSED` 轉回暫停前的狀態（記錄在 `loop_execution_logs` 中）
- 恢復時**應**記錄恢復事件到 `loop_execution_logs`，包含：
  - 恢復時間
  - 恢復後的狀態
  - 待處理任務摘要
- 前端**應**在狀態為 `PAUSED` 時顯示「恢復」按鈕
- 恢復後系統**應**從上次暫停的位置繼續執行（不重複已完成的步驟）

**取消行為（Cancel）**：
- 取消**應**將狀態從任何狀態轉為 `CANCELLED`
- 取消後迴圈**不可恢復**，無法再執行任何操作
- 取消時**應**執行以下操作：
  - 將所有待審核知識（`status = 'pending'`）標記為 `rejected`
  - 記錄取消事件到 `loop_execution_logs`，包含取消時間和取消前的狀態
  - 保留已審核通過並同步的知識（`status = 'approved'`）
  - 保留所有執行日誌與統計資料（用於追溯分析）
- 前端**應**在所有狀態（除了 `COMPLETED` 和 `CANCELLED`）顯示「取消」按鈕
- 前端**應**彈出確認對話框：「取消後無法恢復，已生成但未審核的知識將被拒絕，確定取消嗎？」

**冪等性保證**：
- 暫停操作**應**具備冪等性（多次暫停同一迴圈，狀態保持 `PAUSED`）
- 恢復操作**應**檢查當前狀態，只有 `PAUSED` 狀態才能恢復
- 取消操作**應**具備冪等性（多次取消同一迴圈，狀態保持 `CANCELLED`）

**API 端點**：
- `POST /api/v1/loops/{loop_id}/pause` - 暫停迴圈
- `POST /api/v1/loops/{loop_id}/resume` - 恢復迴圈
- `POST /api/v1/loops/{loop_id}/cancel` - 取消迴圈

**狀態轉換圖**：
```
任何狀態 → [Pause] → PAUSED → [Resume] → 原狀態
任何狀態 → [Cancel] → CANCELLED（終態）
```

### 10.6 已知限制與實作缺陷

本小節記錄當前實作的已知限制與需要改進的部分。

#### 10.6.1 P1: 跨 Session 迭代續接功能缺失

**問題描述**：
當前 `LoopCoordinator` 無法載入已存在的 loop 並繼續執行下一次迭代。

**當前支援的場景**：
```python
# ✅ 支援：同一個 session 內連續執行
coordinator = LoopCoordinator(...)
await coordinator.start_loop(config)  # 建立 Loop #84
await coordinator.execute_iteration()  # 迭代 1
await coordinator.execute_iteration()  # 迭代 2
```

**不支援的場景**：
```python
# ❌ 不支援：載入已存在的 loop 繼續執行
coordinator = LoopCoordinator(...)
coordinator.loop_id = 84  # 手動設定
await coordinator.execute_iteration()  # 錯誤：UNINITIALIZED 狀態
```

**錯誤訊息**：
```
models.InvalidStateError: 無法從狀態 'UNINITIALIZED' 轉換至 'execute_iteration'
```

**影響範圍**：
1. 無法執行跨 session 的迭代：使用者審核完知識後，無法從命令列執行下一次迭代
2. 腳本 `run_next_iteration.sh` 無法使用
3. 改善幅度驗證困難：無法在同一個 loop 內執行多次迭代並比較改善幅度

**根本原因**：
`LoopCoordinator.__init__()` 初始化時 `self.current_status = LoopStatus.UNINITIALIZED`，執行 `execute_iteration()` 時會檢查狀態並拋出例外。手動設定 `loop_id` 和 `current_status` 無法通過所有驗證。

**建議解決方案**：
新增 `load_loop()` 方法：
```python
async def load_loop(self, loop_id: int) -> Dict:
    """
    載入已存在的 loop 並初始化協調器狀態

    Args:
        loop_id: 要載入的 loop ID

    Returns:
        Loop 的當前狀態資訊
    """
    # 查詢 loop 資訊並設定協調器狀態
    # 初始化 cost_tracker
    # 返回狀態資訊
```

**暫時替代方案**：
```bash
# 1. 第一次測試
./run_50_verification.sh        # 建立 Loop #84，迭代 1

# 2. 前端審核知識

# 3. 第二次測試（建立新 loop）
./run_50_verification.sh        # 建立 Loop #85，迭代 1

# 4. 手動比較改善幅度
# Loop #84 通過率 vs Loop #85 通過率
```

**優先級**：P1 - 高（影響正常的迭代工作流程）

**驗收標準**：
實作完成後應通過以下測試：
```bash
# 1. 執行第一次迭代
./run_50_verification.sh
# → 建立 Loop #84

# 2. 前端審核完成

# 3. 執行第二次迭代
./run_next_iteration.sh 84
# → ✅ 成功執行迭代 2

# 4. 驗證改善幅度
./quick_verification.sh 84
# → 顯示：迭代 1 (50%) vs 迭代 2 (60%) [改善 +10%]
```

#### 10.6.2 P2: 資料庫架構與文件不完全匹配

**問題描述**：
Requirements.md 規劃的資料庫欄位與實際架構不完全匹配。

**缺少的欄位**：
- `knowledge_completion_loops.scenario_ids` - 固定測試集（當前使用 `total_scenarios` 整數欄位）
- `knowledge_completion_loops.max_iterations` - 在 config JSONB 中而非獨立欄位
- `knowledge_gap_analysis.gap_type` - 實際為 `failure_reason`
- `knowledge_gap_analysis.cluster_id` - 未實作聚類功能

**影響**：
- 驗證腳本需要適配實際架構（`quick_verification.sh` 已修正）
- 測試集固定性驗證功能部分失效
- 聚類分析功能未實作

**建議**：
1. 評估是否需要嚴格按 requirements.md 實作所有欄位
2. 或調整 requirements.md 以反映實際實作狀況
3. 統一命名慣例（`gap_type` vs `failure_reason`）

**優先級**：P2 - 中（部分功能受限，但有替代方案）

#### 10.6.3 P3: total_scenarios 欄位記錄錯誤

**問題描述**：
`run_first_loop.py` 將 `total_scenarios` 設定為整個資料庫的測試情境總數，而非當前批次使用的測試情境數量。

**實際行為**：
```python
# Loop #84 使用 50 題
# 但 total_scenarios = 3043（整個資料庫的題數）
```

**預期行為**：
```python
# Loop #84 使用 50 題
# total_scenarios 應為 50
```

**影響**：統計資料不正確，但不影響功能運作。

**優先級**：P3 - 低（僅影響統計顯示）

---

## 11. API 規格（後端）

### 11.1 迴圈管理 API

**啟動新迴圈（非同步）**：
```
POST /api/v1/loops/start
Request Body:
{
  "vendor_id": 2,
  "loop_name": "第一批次知識完善",
  "batch_size": 50,
  "target_pass_rate": 0.85,
  "max_iterations": 10,
  "async": true  // 預設 true，前端必須使用非同步模式
}
Response (立即返回):
{
  "loop_id": 1,
  "status": "RUNNING",
  "scenario_ids": [1, 2, 3, ...],
  "created_at": "2026-03-26T10:00:00Z",
  "estimated_duration_minutes": 10,
  "message": "迴圈已啟動，正在執行第一次迭代"
}
```

**執行迭代**：
```
POST /api/v1/loops/{loop_id}/execute-iteration
Response:
{
  "current_iteration": 1,
  "backtest_result": {
    "total": 50,
    "passed": 30,
    "failed": 20,
    "pass_rate": 0.60
  },
  "gap_analysis": {
    "total_gaps": 20,
    "sop_knowledge": 8,
    "form_fill": 5,
    "system_config": 7,
    "api_query": 0
  },
  "generated_knowledge": {
    "sop_count": 5,
    "knowledge_count": 3
  },
  "cost_summary": {
    "total_cost_usd": 0.45,
    "api_calls": 25,
    "total_tokens": 12000
  },
  "next_action": "wait_for_review"
}
```

**驗證效果**：
```
POST /api/v1/loops/{loop_id}/validate
Response:
{
  "validation_result": {
    "pass_rate": 0.72,
    "improvement": 0.12,
    "total": 20,
    "passed": 14,
    "failed": 6
  },
  "validation_passed": true,
  "affected_knowledge_ids": [101, 102, 103, 104, 105, 106],
  "status": "RUNNING",
  "next_action": "continue"
}
```

**查詢迴圈狀態**：
```
GET /api/v1/loops/{loop_id}/status
Response:
{
  "loop_id": 1,
  "loop_name": "第一批次知識完善",
  "vendor_id": 2,
  "status": "RUNNING",
  "current_iteration": 2,
  "current_pass_rate": 0.72,
  "target_pass_rate": 0.85,
  "max_iterations": 10,
  "total_scenarios": 50,
  "created_at": "2026-03-26T10:00:00Z",
  "updated_at": "2026-03-26T11:30:00Z",
  "can_continue": true,
  "is_target_reached": false,
  "iterations_remaining": 8,
  "recommendation": "繼續迭代（通過率 72%，未達目標 85%）",
  "total_cost_usd": 1.25,
  "total_knowledge_generated": 15,
  "total_knowledge_approved": 8,
  "total_api_calls": 80,

  // 新增：執行進度（當迭代執行中時）
  "progress": {
    "current_step": "backtest",              // backtest/analysis/classification/clustering/generation/syncing
    "step_name": "執行回測",
    "step_progress": "25/50",                // 當前步驟進度
    "percentage": 50,                        // 整體完成百分比
    "elapsed_seconds": 300,                  // 已執行時間（秒）
    "estimated_remaining_seconds": 300,      // 預估剩餘時間（秒）
    "started_at": "2026-03-26T11:25:00Z"
  }
}

說明：
- progress 欄位僅在迭代執行中時存在
- 前端應每 5-10 秒輪詢此端點以更新進度條
- 當 status 變為 REVIEWING 時，表示迭代完成，停止輪詢
```

**查詢執行日誌（新增）**：
```
GET /api/v1/loops/{loop_id}/logs?limit=20&event_type=progress
Response:
{
  "logs": [
    {
      "id": 145,
      "loop_id": 1,
      "iteration": 2,
      "event_type": "backtest_progress",
      "message": "回測進度：25/50 (50%)",
      "metadata": {
        "completed": 25,
        "total": 50,
        "passed": 15,
        "failed": 10
      },
      "created_at": "2026-03-26T11:30:00Z"
    },
    {
      "event_type": "backtest_started",
      "message": "開始執行回測（50 題）",
      "created_at": "2026-03-26T11:25:00Z"
    }
  ]
}
```

**完成批次**：
```
POST /api/v1/loops/{loop_id}/complete-batch
Response:
{
  "loop_id": 1,
  "status": "COMPLETED",
  "summary": {
    "total_iterations": 3,
    "final_pass_rate": 0.88,
    "total_cost_usd": 1.25,
    "knowledge_generated": 15,
    "knowledge_approved": 12
  },
  "completed_at": "2026-03-26T12:00:00Z"
}
```

**啟動下一批次**：
```
POST /api/v1/loops/start-next-batch
Request Body:
{
  "previous_loop_id": 1,
  "vendor_id": 2
}
Response:
{
  "loop_id": 2,
  "parent_loop_id": 1,
  "status": "RUNNING",
  "batch_size": 50,
  "target_pass_rate": 0.85,
  "scenario_ids": [51, 52, 53, ...],
  "created_at": "2026-03-26T12:05:00Z"
}
```

**查詢迴圈列表**：
```
GET /api/v1/loops?vendor_id=2&status=RUNNING&page=1&page_size=20
Response:
{
  "loops": [
    {
      "loop_id": 2,
      "loop_name": "第二批次知識完善",
      "vendor_id": 2,
      "status": "RUNNING",
      "current_iteration": 1,
      "current_pass_rate": 0.65,
      "target_pass_rate": 0.85,
      "created_at": "2026-03-26T12:05:00Z"
    },
    ...
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

**暫停/恢復/取消迴圈**：
```
POST /api/v1/loops/{loop_id}/pause
POST /api/v1/loops/{loop_id}/resume
POST /api/v1/loops/{loop_id}/cancel
```

### 11.2 知識審核 API

**查詢待審核知識**：
```
GET /api/v1/loop-knowledge/pending?loop_id={loop_id}
Response:
{
  "knowledge_items": [
    {
      "id": 101,
      "loop_id": 1,
      "iteration": 1,
      "question": "租金每個月幾號要繳？",
      "answer": "租金應於每月 5 日前繳納...",
      "knowledge_type": null,
      "status": "pending",
      "created_at": "2026-03-26T10:30:00Z"
    },
    ...
  ]
}
```

**審核知識**：
```
POST /api/v1/loop-knowledge/{knowledge_id}/review
Request Body:
{
  "action": "approve",  // approve 或 reject
  "question": "租金每個月幾號要繳？",  // 可選修改
  "answer": "租金應於每月 5 日前繳納...",  // 可選修改
  "keywords": ["租金", "繳納日期"],  // 可選修改
  "vendor_id": 2,  // SOP 專用
  "category_id": 1,  // SOP 專用
  "group_id": 3  // SOP 專用
}
Response:
{
  "knowledge_id": 101,
  "status": "approved",
  "updated_at": "2026-03-26T11:00:00Z"
}
```

**批量審核知識**：
```
POST /api/v1/loop-knowledge/batch-review
Request Body:
{
  "knowledge_ids": [123, 124, 125, 126, 127],
  "action": "approve",  // approve 或 reject
  "modifications": {  // 可選：批量修改
    "keywords": ["批量關鍵字"]
  }
}
Response:
{
  "total": 5,
  "successful": 4,
  "failed": 1,
  "results": [
    {
      "knowledge_id": 123,
      "status": "success",
      "synced": true
    },
    {
      "knowledge_id": 124,
      "status": "success",
      "synced": true
    },
    {
      "knowledge_id": 125,
      "status": "failed",
      "error": "embedding 生成超時"
    },
    {
      "knowledge_id": 126,
      "status": "success",
      "synced": true
    },
    {
      "knowledge_id": 127,
      "status": "success",
      "synced": true
    }
  ],
  "processing_time_ms": 1850
}
```

### 11.3 API 路由模組

系統**應**提供獨立的 API 路由模組，建議路徑：`rag-orchestrator/routers/knowledge_completion_loop.py`

**API 路由清單**：
- `POST /api/v1/loops/start` → `LoopCoordinator.start_loop()`
- `POST /api/v1/loops/{loop_id}/execute-iteration` → `LoopCoordinator.execute_iteration()`
- `POST /api/v1/loops/{loop_id}/validate` → `LoopCoordinator.validate_loop()`
- `GET /api/v1/loops/{loop_id}/status` → 查詢迴圈狀態
- `GET /api/v1/loops` → 查詢迴圈列表
- `POST /api/v1/loops/{loop_id}/complete-batch` → `LoopCoordinator.complete_batch()`
- `POST /api/v1/loops/start-next-batch` → 啟動下一批次
- `POST /api/v1/loops/{loop_id}/pause` → `LoopCoordinator.pause_loop()`
- `POST /api/v1/loops/{loop_id}/resume` → `LoopCoordinator.resume_loop()`
- `POST /api/v1/loops/{loop_id}/cancel` → `LoopCoordinator.cancel_loop()`
- `GET /api/v1/loop-knowledge/pending` → 查詢待審核知識
- `POST /api/v1/loop-knowledge/{knowledge_id}/review` → 審核知識並立即同步
- `POST /api/v1/loop-knowledge/batch-review` → 批量審核知識

---

## 12. 前端管理界面

### 12.1 知識完善迴圈管理頁面

系統**應**在前端管理界面（`http://localhost:8087`）提供知識完善迴圈的操作界面。

**驗收標準**：

**頁面位置**：
- 系統**應**在現有 `/test-scenarios` 頁面增加迴圈管理區塊
- 或新增獨立頁面 `/knowledge-completion-loop`

**迴圈列表區塊**：
- 頁面**應**顯示迴圈列表，包含：
  - 迴圈 ID、名稱
  - 業者名稱
  - 當前狀態（使用顏色標籤：RUNNING 藍色、REVIEWING 橙色、COMPLETED 綠色、FAILED 紅色）
  - 當前迭代次數 / 最大迭代次數
  - 當前通過率 / 目標通過率（進度條顯示，使用漸變顏色：紅→黃→綠）
  - 創建時間
  - 操作按鈕
- 列表**應**支援按狀態篩選（RUNNING/REVIEWING/COMPLETED）
- 列表**應**支援按業者篩選

**啟動新迴圈對話框**：
- 頁面**應**提供「啟動新迴圈」按鈕
- 點擊後彈出配置對話框，包含：
  - 選擇業者（下拉選單）
  - 設定批次大小（預設 50）
  - 設定目標通過率（預設 85%）
  - 設定最大迭代次數（預設 10）
  - 輸入迴圈名稱（文字輸入）

**迴圈操作按鈕**：
- 每個迴圈**應**根據狀態顯示對應操作按鈕：
  - 狀態為 `RUNNING`：顯示「執行下一次迭代」按鈕
  - 狀態為 `REVIEWING`：顯示「前往審核」按鈕（跳轉到審核中心）
  - 狀態為 `RUNNING`：顯示「完成批次」按鈕
  - 所有狀態：顯示「查看詳情」按鈕

**迴圈詳情對話框**：
- 點擊「查看詳情」**應**彈出對話框，顯示：
  - 基本資訊（迴圈名稱、業者、狀態、創建時間）
  - 進度資訊（迭代次數、通過率、剩餘迭代）
  - 成本統計（累計成本、API 調用次數、生成知識數、審核通過數）
  - 建議操作（根據當前狀態和通過率提供建議）
  - 迭代歷史表格（每次迭代的通過率、生成知識數、成本）

**批次管理區塊**：
- 對於已完成的迴圈（`COMPLETED`），**應**顯示「啟動下一批次」按鈕
- 點擊後**應**自動繼承前批次配置並創建新迴圈

### 12.2 審核中心增強

系統**應**在現有審核中心（`/review-center`）增強迴圈知識審核功能。

**驗收標準**：

**迴圈知識審核 Tab**（LoopKnowledgeReviewTab）：
- Tab **應**顯示待審核知識列表（已實現）
- Tab **應**在頂部顯示當前迴圈資訊卡片：
  - 迴圈名稱、迭代次數
  - 待審核知識數量
  - 已審核通過並同步數量 / 已審核拒絕數量
  - 最近一次驗證結果（通過率、改善幅度）

**審核與同步功能**：
- 用戶**應**能夠逐一審核知識項目
- 點擊「批准」時：
  - 知識立即同步到 knowledge_base/vendor_sop_items
  - review_status = 'approved'
  - 顯示「已同步」提示訊息
  - RAG 查詢立即可搜尋到該知識
- 點擊「拒絕」時：
  - 知識標記為 rejected
  - 不同步到正式庫

**驗證效果按鈕**：
- Tab **應**提供「驗證效果」按鈕：
  - 按鈕**應**在有已同步知識時啟用
  - 點擊後調用 `POST /api/v1/loops/{loop_id}/validate`
  - 顯示驗證進度（loading 狀態，顯示「執行回測中...」）
  - 驗證完成後顯示結果對話框

**驗證結果對話框**：
- 對話框**應**顯示驗證回測結果：
  - 驗證通過率（百分比）
  - 改善幅度（百分比，顏色標示：正數綠色、負數紅色）
  - 測試題數統計（總數、通過數、失敗數）
  - 受影響的知識數量
- **驗證通過時**：
  - 顯示成功訊息：「驗證通過！改善幅度達到 {X}%」
  - 顯示知識狀態：「{N} 個知識保持 approved 狀態」
  - 提供「繼續下一次迭代」和「完成批次」兩個選項按鈕
- **驗證失敗時**：
  - 顯示失敗原因（例如：「改善幅度未達 5%，當前改善 2%」）
  - 顯示知識狀態：「{N} 個知識已標記為 need_improvement」
  - 提示：「知識仍保留在正式庫，您可以：」
    - 選項 A：調整這些知識內容，重新驗證
    - 選項 B：繼續下一次迭代，累積更多知識
  - 提供「返回審核」和「繼續下一次迭代」按鈕

### 12.3 測試情境頁面增強

系統**應**在測試情境頁面（`/test-scenarios`）增加迴圈相關功能。

**驗收標準**：

**快速啟動區塊**：
- 頁面頂部**應**顯示快速啟動卡片（當有已批准的測試情境時）：
  - 顯示可測試題目數量
  - 顯示「快速啟動知識完善迴圈」按鈕
  - 點擊後彈出啟動配置對話框

**迴圈狀態指示**：
- 頁面**應**顯示當前進行中的迴圈狀態（如有）：
  - 迴圈名稱、進度（迭代次數、通過率）
  - 快速操作按鈕（執行迭代/前往審核）

### 12.4 API 配置與錯誤處理

前端**應**正確調用後端 API 並處理各種情況。

**驗收標準**：

**API 配置**：
- 前端**應**在 `src/config/api.js` 新增迴圈管理相關端點：
  ```javascript
  // 知識完善迴圈
  loopStart: `${API_BASE_URL}/rag-api/v1/loops/start`,
  loopList: `${API_BASE_URL}/rag-api/v1/loops`,
  loopStatus: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/status`,
  loopExecuteIteration: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/execute-iteration`,
  loopValidate: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/validate`,
  loopCompleteBatch: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/complete-batch`,
  loopStartNextBatch: `${API_BASE_URL}/rag-api/v1/loops/start-next-batch`,
  loopPause: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/pause`,
  loopResume: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/resume`,
  loopCancel: (loopId) => `${API_BASE_URL}/rag-api/v1/loops/${loopId}/cancel`,

  // 知識審核
  loopKnowledgePending: `${API_BASE_URL}/rag-api/v1/loop-knowledge/pending`,
  loopKnowledgeReview: (knowledgeId) => `${API_BASE_URL}/rag-api/v1/loop-knowledge/${knowledgeId}/review`,
  loopKnowledgeBatchReview: `${API_BASE_URL}/rag-api/v1/loop-knowledge/batch-review`,
  ```

**Loading 狀態**：
- 所有 API 調用**應**顯示 loading 狀態
- 長時間操作（執行迭代、驗證回測）**應**顯示進度提示：
  - 執行迭代：顯示當前階段（正在回測... → 正在分析缺口... → 正在分類聚類... → 正在生成知識... → 完成！）
  - 驗證回測：顯示「執行回測中...」

**錯誤處理**：
- API 錯誤**應**顯示友善的錯誤訊息
- 網路錯誤**應**提示重試
- 狀態錯誤（如在 REVIEWING 狀態執行迭代）**應**顯示明確的錯誤提示

**自動刷新**：
- 執行迭代完成後，**應**自動刷新迴圈狀態
- 驗證同步完成後，**應**自動刷新迴圈列表和待審核知識數量

### 12.5 用戶體驗優化

系統**應**提供良好的用戶體驗。

**驗收標準**：

**操作確認**：
- 關鍵操作（執行迭代、完成批次、啟動新批次、取消迴圈）**應**彈出確認對話框
- 確認對話框**應**說明操作影響

**響應式設計**：
- 界面**應**在不同螢幕尺寸下正常顯示
- 表格**應**支援水平滾動（小螢幕）

---

## 13. 日誌與監控

### 13.1 執行日誌記錄

系統**應**在 `loop_execution_logs` 表詳細記錄每個步驟的執行情況。

**驗收標準**：
- 系統**應**記錄以下事件類型：
  - `loop_started`：迴圈啟動
  - `backtest_executed`：回測執行完成
  - `gaps_analyzed`：知識缺口分析完成
  - `gaps_classified`：智能分類完成
  - `knowledge_generated`：知識生成完成
  - `iteration_completed`：迭代完成
  - `validation_started`：驗證回測開始
  - `validation_completed`：驗證回測完成
  - `sync_completed`：知識同步完成
  - `batch_completed`：批次完成
  - `error`：錯誤發生
- 每條日誌**應**包含：
  - `loop_id`
  - `iteration`
  - `event_type`
  - `event_data`（JSON 格式，包含詳細資訊）
  - `created_at`

### 13.2 成本追蹤

系統**應**追蹤 OpenAI API 調用的成本。

**驗收標準**：
- 系統**應**記錄每次 OpenAI API 調用的：
  - 使用的模型（如：gpt-4o-mini）
  - 輸入 token 數
  - 輸出 token 數
  - 估算成本（USD）
- 系統**應**彙總每次迭代的總成本
- 系統**應**在迴圈狀態 API 中返回累計成本

### 13.3 錯誤處理與恢復

系統**應**具備健全的錯誤處理機制，區分可恢復與不可恢復錯誤，並支援從中斷點恢復執行。

**驗收標準**：

**可恢復錯誤（Recoverable Errors）**：
- **OpenAI API 錯誤**：
  - Rate Limit 錯誤（429）：使用 exponential backoff 重試，最多 3 次，間隔為 1s、2s、4s
  - 超時錯誤（Timeout）：立即重試，最多 3 次
  - 暫時性網路錯誤（5xx）：重試最多 3 次
  - 重試失敗後**應**記錄錯誤到 `loop_execution_logs`，event_type = `error`
- **資料庫暫時性錯誤**：
  - 連接失敗：重試最多 3 次，間隔 2 秒
  - 死鎖（Deadlock）：回滾事務後重試，最多 2 次
  - 連接池耗盡：等待 5 秒後重試，最多 2 次
- **HTTP 請求錯誤（回測 API）**：
  - 超時：重試最多 2 次
  - 5xx 錯誤：重試最多 2 次
- 所有可恢復錯誤**應**在重試前記錄警告日誌（不記錄到 `loop_execution_logs`）
- 重試成功後**應**繼續執行，不影響流程

**不可恢復錯誤（Non-Recoverable Errors）**：
- **配置錯誤**：
  - OpenAI API 金鑰無效（401 Unauthorized）
  - 缺少必要的環境變數
  - 無效的業者 ID（vendor_id 不存在）
- **資料結構錯誤**：
  - 資料表不存在
  - 必要欄位缺失
  - 外鍵約束違反（參照的記錄不存在）
- **資料完整性錯誤**：
  - loop_id 不存在
  - 必填欄位為 NULL
  - 資料類型不匹配
- **業務邏輯錯誤**：
  - 迴圈狀態不允許執行操作（例如：COMPLETED 狀態無法執行迭代）
  - 測試情境表為空（無法執行回測）
- 發生不可恢復錯誤時，系統**應**：
  - 立即停止執行當前操作
  - 將迴圈狀態標記為 `FAILED`
  - 記錄詳細錯誤到 `loop_execution_logs`，event_type = `error`，包含：
    - 錯誤類型（error_type）
    - 錯誤訊息（error_message）
    - 錯誤堆疊（stack_trace，可選）
    - 發生錯誤的步驟（failed_step）
    - 當前迭代次數（iteration）
  - 前端**應**顯示錯誤訊息並提供「查看日誌」按鈕

**中斷點恢復機制**：
- 系統**應**支援從中斷點恢復執行（適用於可恢復錯誤或人工暫停後恢復）
- 恢復依據：
  - 透過 `loop_id` 識別迴圈
  - 透過 `iteration` 識別當前迭代次數
  - 透過 `loop_execution_logs` 查詢最後完成的步驟
- 恢復邏輯：
  - 檢查最後一條 `event_type` 記錄
  - 從下一個未完成的步驟繼續執行
  - 例如：最後記錄為 `gaps_classified`，恢復時從「聚類」步驟開始
- 冪等性保證：
  - 知識生成前**應**檢查是否已生成（透過 `loop_id` 和 `iteration` 查詢 `loop_generated_knowledge`）
  - 如已生成，跳過生成步驟，直接進入審核階段
  - 回測執行前**應**檢查是否已執行（透過 `loop_id` 和 `iteration` 查詢 `backtest_results`）
  - 如已執行，讀取現有結果，不重複執行
- 恢復時**應**記錄恢復事件到 `loop_execution_logs`，event_type = `recovery_started`，包含：
  - 恢復時間
  - 恢復的步驟
  - 恢復原因（manual_resume / auto_retry）

**錯誤日誌格式**：
```json
{
  "error_type": "OpenAIAPIError",
  "error_message": "Rate limit exceeded",
  "failed_step": "knowledge_generation",
  "iteration": 2,
  "retry_count": 3,
  "stack_trace": "...",
  "context": {
    "loop_id": 123,
    "vendor_id": 2,
    "gaps_count": 15
  }
}
```

**前端錯誤處理**：
- 迴圈狀態為 `FAILED` 時，前端**應**：
  - 顯示紅色錯誤標籤
  - 提供「查看錯誤詳情」按鈕
  - 顯示錯誤訊息和建議操作（例如：「請檢查 OpenAI API 金鑰配置」）
  - 提供「重試」按鈕（如果錯誤可能已解決，例如暫時性網路問題）
- 點擊「重試」**應**將狀態轉回 `RUNNING` 並觸發恢復機制

---

## 14. 配置與環境

### 14.1 環境變數配置

系統**應**支援透過環境變數配置關鍵參數。

**驗收標準**：

**基礎配置**：
- 系統**應**支援以下環境變數：
  - `VENDOR_ID`：業者 ID，用於指定使用哪個業者的 RAG 配置（預設：2）
  - `OPENAI_API_KEY`：OpenAI API 金鑰（必需）
  - `DB_HOST`：資料庫主機（預設：postgres）
  - `DB_PORT`：資料庫端口（預設：5432）
  - `DB_NAME`：資料庫名稱（預設：aichatbot_admin）
  - `DB_USER`：資料庫使用者（預設：aichatbot）
  - `DB_PASSWORD`：資料庫密碼（預設：aichatbot_password）
  - `RAG_API_URL`：RAG API 基礎 URL（預設：http://localhost:8100）
  - `BACKTEST_ONLY`：僅回測模式（預設：false）

**回測引擎配置**：
- 系統**應**支援以下回測引擎環境變數：
  - `BACKTEST_CONCURRENCY`：並發數（預設：5）
  - `BACKTEST_TIMEOUT`：超時時間（秒，預設：60）
  - `BACKTEST_RETRY_TIMES`：重試次數（預設：2）
  - `BACKTEST_BATCH_LLM_EVAL`：批量 LLM 評估（預設：true）
  - `BACKTEST_LLM_BATCH_SIZE`：LLM 批量大小（預設：10）
  - `BACKTEST_DISABLE_ANSWER_SYNTHESIS`：禁用答案合成（預設：false）

**錯誤處理**：
- 當必需的環境變數未設定時，系統**應**輸出清楚的錯誤訊息並退出

### 14.2 迴圈配置參數

系統**應**支援透過 `LoopConfig` 物件或 API 參數配置迴圈參數。

**驗收標準**：
- 可配置參數**應**包含：
  - `batch_size`：批次大小
    - 預設：50（快速驗證）
    - 常用值：50（快速）、500（標準）、3000（全面）
    - 範圍：1 至測試情境總數
    - 說明：參考 Section 4.3 的測試規模策略
  - `target_pass_rate`：目標通過率（預設：0.85）
  - `max_iterations`：最大迭代次數（預設：10）
  - `action_type_mode`：回應類型判斷模式（預設：ai_assisted）

**參數選擇建議**：
- `batch_size` 選擇：
  - 首次測試：使用 50（快速驗證核心功能）
  - 正式測試：使用 500（平衡效率與覆蓋度）
  - 最終評估：使用 3000（全面驗證知識庫品質）
- 不同的 `batch_size` 應建立不同的 loop，而非在同一 loop 中變更

---

## 15. 非功能性需求

### 15.1 性能需求

**回測效能目標**：
- 50 題回測**應**在 10 分鐘內完成（單次迭代）
- 500 題回測**應**在 90 分鐘內完成（單次迭代）
- 3000 題回測**應**在 120 分鐘內完成（單次迭代）

**系統優化要求**：
- OpenAI API 調用**應**使用批次處理以降低成本
- 資料庫查詢**應**使用適當的索引以保證查詢效率
- 回測引擎**應**支援並發執行（預設並發數：5）
- 大規模測試（3000 題）**應**考慮分批執行以避免超時與記憶體問題

### 15.2 可靠性需求

- 系統**應**能夠從中斷點恢復執行（透過 `loop_id` 和 `iteration` 識別）
- 關鍵操作**應**使用資料庫事務確保資料一致性
- OpenAI API 調用失敗**應**進行重試（預設重試 2 次）

### 15.3 可維護性需求

- 程式碼**應**遵循模組化設計原則
- 各功能模組**應**具備明確的職責分工
- 關鍵函數**應**包含文件字串（docstring）說明

### 15.4 安全性需求

- OpenAI API 金鑰**應**透過環境變數傳遞，不得硬編碼
- 資料庫連接參數**應**支援環境變數配置
- 敏感資料（如 API 金鑰）**不應**記錄到日誌

---

## 附錄：實現參考

### A.1 核心文件清單

- `services/knowledge_completion_loop/coordinator.py` - 流程協調器（LoopCoordinator）
- `services/knowledge_completion_loop/backtest_client.py` - 回測客戶端（BacktestFrameworkClient）
- `services/knowledge_completion_loop/gap_classifier.py` - 智能分類與聚類（GapClassifier）
- `services/knowledge_completion_loop/sop_generator.py` - SOP 生成器（SOPGenerator）
- `services/knowledge_completion_loop/knowledge_generator.py` - 一般知識生成器（KnowledgeGeneratorClient）
- `services/knowledge_completion_loop/run_first_loop.py` - 命令列執行腳本（調試用）
- `scripts/backtest/backtest_framework_async.py` - 並發回測引擎（AsyncBacktestFramework）
- `rag-orchestrator/routers/knowledge_completion_loop.py` - API 路由模組（待實現）
- `knowledge-admin/frontend/src/views/TestScenariosView.vue` - 測試情境頁面（待增強）
- `knowledge-admin/frontend/src/views/ReviewCenterView.vue` - 審核中心（待增強）
- `knowledge-admin/frontend/src/components/review/LoopKnowledgeReviewTab.vue` - 迴圈知識審核 Tab（已存在）

### A.2 命令列執行方式（僅供調試）

```bash
# 基本執行（Vendor 2，預設）
# 註：VENDOR_ID 用於指定使用哪個業者的 RAG 配置，測試題庫為全域共用
docker exec aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"

# 指定其他 Vendor ID（使用 Vendor 1 的 RAG 配置）
docker exec -e VENDOR_ID=1 aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"

# 僅回測模式（只執行測試，不生成知識）
docker exec -e VENDOR_ID=2 -e BACKTEST_ONLY=true aichatbot-rag-orchestrator bash -c "cd /app && python3 services/knowledge_completion_loop/run_first_loop.py"
```

**注意**：命令列腳本僅供調試使用，日常操作應使用前端界面。

---

**文件版本**：2.2
**最後更新**：2026-03-27

---

## 變更歷史

### v2.2 (2026-03-27)
- **新增 Section 4.5**：迭代間測試情境一致性（Critical）
  - 強制要求同一迴圈的所有迭代使用相同的測試集
  - 確保改善幅度的可比較性
  - 防止因測試集變更導致結果失真
- **新增 Section 8.3**：批量審核功能（Critical）
  - 新增批量審核 API：`POST /api/v1/loop-knowledge/batch-review`
  - 前端支援全選、篩選後全選、個別選取
  - 批量操作工具列：批量批准、批量拒絕
  - 效能要求：10 個項目 < 5 秒，50 個項目 < 20 秒
- 補充 API 規格（Section 11.2）和前端配置（Section 12.4）
- 原 Section 8.3 改為 8.4（SOP 欄位預填）

### v2.1 (2026-03-27)
- 簡化驗證流程：從三階段改為兩階段（審核立即同步 → 驗證效果）
- 移除「啟用測試環境」和「人工手動測試」階段
- 審核通過時立即同步到 knowledge_base/vendor_sop_items
- 驗證失敗時標記為 need_improvement 而非刪除
- 更新 API 端點：移除 enable/disable-temp-knowledge，新增 validate
- 更新前端界面需求以反映簡化流程

### v2.0 (2026-03-27)
- 重新整理文件結構，提升邏輯清晰度
- 新增系統架構章節
- 資料模型前置到第 3 章
- 功能需求按執行流程排序
