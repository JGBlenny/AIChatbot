# AIChatbot 知識系統全面盤查報告

## 執行日期
2026-03-27

## 調查範圍
AIChatbot 專案中所有與知識（knowledge）相關的邏輯、參數、配置和模式，包括：
- 資料庫 Schema
- 服務層邏輯
- 路由層 API
- 關鍵參數與配置
- 知識分類體系
- 知識完善迴圈流程
- OpenAI API 使用模式

---

## 1. 資料庫 Schema 摘要

### 1.1 核心表：knowledge_base
**位置**：`database/init/02-create-knowledge-base.sql`

| 欄位名 | 類型 | 說明 | 約束 |
|-------|------|------|-----|
| id | SERIAL | 主鍵 | PRIMARY KEY |
| question_summary | TEXT | 問題摘要 | NOT NULL |
| answer | TEXT | 答案內容 | NOT NULL |
| intent_id | INTEGER | 關聯意圖 ID | 外鍵到 intents(id) |
| intent_confidence | FLOAT | 分類信心度 | 0-1 範圍 |
| intent_assigned_by | VARCHAR(20) | 分配方式 | auto/manual，預設 auto |
| business_types | TEXT[] | 業態類型陣列 | NULL=所有業態 |
| target_user | TEXT[] | 目標用戶陣列 | tenant/landlord/property_manager/system_admin |
| keywords | TEXT[] | 關鍵字陣列 | GIN 索引 |
| vendor_id | INTEGER | 業者 ID | 外鍵到 vendors(id) |
| scope | VARCHAR(20) | 知識範圍 | global/vendor/customized，預設 global |
| priority | INTEGER | 優先級 | 數字越大優先級越高，預設 0 |
| is_template | BOOLEAN | 是否為模板 | 預設 FALSE |
| template_vars | JSONB | 模板變數列表 | JSON 陣列 |
| embedding | vector(1536) | 向量嵌入 | pgvector，IVFFlat 索引 |
| video_s3_key | VARCHAR(500) | S3 影片鍵 | 可為 NULL |
| video_url | VARCHAR(500) | 影片 URL | 可為 NULL |
| source_type | VARCHAR(20) | 知識來源 | manual/ai_generated/imported/ai_assisted |
| source_test_scenario_id | INTEGER | 測試場景來源 | 可為 NULL |
| generation_metadata | JSONB | 生成元數據 | {model, prompt, confidence, reviewed_by, edited} |
| category | VARCHAR(50) | 業務分類 | 參考 category_config 表 |
| is_active | BOOLEAN | 是否啟用 | 預設 TRUE |
| created_at | TIMESTAMP | 建立時間 | 預設 CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | 更新時間 | 觸發器自動更新 |
| created_by | VARCHAR(100) | 建立人 | 可為 NULL |
| updated_by | VARCHAR(100) | 更新人 | 可為 NULL |

**重要索引**：
- `idx_kb_scope`：scope 欄位
- `idx_kb_template`：is_template 欄位
- `idx_kb_embedding`：向量搜尋（IVFFlat，lists=100）
- `idx_kb_keywords`：GIN 索引（陣列）
- `idx_kb_business_types`：GIN 索引
- `idx_kb_target_user`：GIN 索引
- `idx_kb_category`：category 欄位

### 1.2 SOP 相關表

#### platform_sop_categories
平台 SOP 分類表（管理員用）
- 主要欄位：category_name, description, display_order, template_notes, is_active

#### platform_sop_templates
平台 SOP 範本表
- 主要欄位：category_id, group_id, item_number, item_name, content, business_type
- related_intent_id：關聯意圖（已廢棄，改用 group-based embedding）
- priority：優先級（已廢棄，現改用向量相似度）

#### platform_sop_groups
平台 SOP 群組表（邏輯分組）
- group_name, description, display_order, is_active

#### vendor_sop_items
業者 SOP 項目表（最重要的運行表）
- 主要欄位：category_id, vendor_id, group_id, item_number, item_name, content
- primary_embedding：主要向量（group_name + item_name）
- fallback_embedding：備用向量（content）
- template_id：來源範本
- related_intent_id：關聯意圖（已廢棄）
- priority：優先級（已廢棄）

#### vendor_sop_categories & vendor_sop_groups
業者專屬 SOP 分類和群組表

### 1.3 意圖管理表

#### intents
意圖配置表
- 主要欄位：name (UNIQUE), type, description, keywords
- confidence_threshold：信心度閾值，預設 0.80
- is_enabled：是否啟用，預設 TRUE
- priority：優先級
- api_required：是否需要外部 API
- api_endpoint, api_action：API 配置

#### knowledge_intent_mapping
知識-意圖多對多映射表
- knowledge_id + intent_id (UNIQUE)
- intent_type：primary/secondary
- confidence：信心度 (0-1)
- assigned_by：分配方式

#### suggested_intents
建議新增意圖表（人工審核前）
- status：pending/approved/rejected/merged
- relevance_score：相關性分數
- frequency：出現頻率

### 1.4 測試相關表

#### test_scenarios
測試題庫表
- 主要欄位：test_question, expected_intent_id, difficulty, tags, priority
- status：pending_review/approved/rejected/draft
- source：manual/user_question/auto_generated/imported
- expected_min_confidence, expected_answer
- pass_count, fail_count, avg_score

#### test_collections
測試集合表（smoke/full/regression/edge_cases）

#### backtest_runs
回測執行記錄表
- status：pending/running/completed/failed/cancelled
- passed_count, failed_count, pass_rate, avg_score
- quality_mode：basic/hybrid/detailed
- test_type：smoke/full/custom

### 1.5 AI 知識系統表

#### ai_generated_knowledge_candidates
AI 生成知識候選表
- status：pending_review/approved/rejected/needs_revision
- confidence_score：AI 生成的信心度
- ai_model, generation_reasoning
- intent_ids：推薦意圖列表

#### knowledge_import_jobs
知識導入作業表
- status：pending/processing/completed/failed/cancelled
- import_mode：append/replace/merge
- progress, result：JSON 資訊

### 1.6 配置表

#### business_types_config
業態類型配置
- 預設值：system_provider（系統商）, full_service（包租型）, property_management（代管型）

#### target_user_config
目標用戶配置
- 預設值：tenant（租客）, landlord（房東）, property_manager（物業管理師）, system_admin（系統管理員）

#### category_config
分類配置表（當前未使用，保留供未來擴展）

---

## 2. 知識分類體系

### 2.1 知識類型分類（Gap Classifier）

根據 `gap_classifier.py` 定義，知識分為 4 大類：

#### 1. sop_knowledge（SOP 業務流程知識）
- **定義**：包租代管的業務流程、政策規則類知識
- **特徵**：流程性、規則性、系統化的步驟說明
- **核心判斷**：涉及房東、租客、合約、房源、租賃等業務實體的流程與規則
- **範例**：「如何續約」、「如何退租」、「可以養寵物嗎」、「可以帶朋友回來過夜嗎」
- **生成方式**：應生成 SOP 到 vendor_sop_items 表
- **should_generate_knowledge**：true

#### 2. form_fill（表單填寫流程）
- **定義**：需要用戶提供資訊的互動式流程
- **特徵**：引導用戶完成特定業務操作
- **範例**：「我想找房」、「我想退租」、「申請維修」
- **生成方式**：生成表單引導流程到 vendor_sop_items 表
- **should_generate_knowledge**：true

#### 3. system_config（系統操作與配置）
- **定義**：單獨情境的問題解答，主要是系統功能使用、帳戶設定、技術操作
- **特徵**：情境性、問答導向、針對單一問題的解答（非流程性）
- **與 SOP 的區別**：這類問題是單點解答，不涉及業務流程規則
- **範例**：「可以用 Google 登入嗎」、「如何切換團隊」、「如何產出12個月帳單」
- **生成方式**：生成單獨情境的問答知識到 knowledge_base 表
- **should_generate_knowledge**：true

#### 4. api_query（API 動態查詢）
- **定義**：需要查詢即時資料的問題
- **特徵**：與具體房源/合約/業者相關，答案因物件而異
- **範例**：「租金多少」、「房租包含哪些費用」、「我的合約何時到期」
- **生成方式**：使用 API 查詢，不生成靜態知識
- **should_generate_knowledge**：false

### 2.2 回應類型分類（Action Type）

根據 `action_type_classifier.py` 定義，回應類型分為 4 種：

| 類型 | 模型欄位 | 說明 | 使用情景 |
|-----|---------|------|---------|
| direct_answer | DIRECT_ANSWER | 純知識問答 | 問題可以直接用文字回答，不需要互動 |
| form_fill | FORM_FILL | 表單+知識 | 需要用戶填寫表單才能完成操作 |
| api_call | API_CALL | API+知識 | 需要調用 API 查詢即時資料 |
| form_then_api | FORM_THEN_API | 表單+API+知識 | 先填表單，再調用 API |

**判斷原則**：
- 答案包含「請填寫」、「申請表單」 → form_fill
- 答案包含「即時查詢」、「目前狀態」 → api_call
- 答案是固定資訊（時間、規則、流程） → direct_answer
- 信心度 < 0.8 時，設定 needs_manual_review = true

### 2.3 知識範圍（Scope）

| 值 | 說明 | 優先級 | 用途 |
|----|------|--------|------|
| global | 全域知識，適用所有業者 | 低 | 通用問答（如基本概念） |
| vendor | 業者專屬知識，只有該業者會用到 | 中 | 業者獨有服務 |
| customized | 業者客製化知識，覆蓋全域知識 | 高 | 同樣問題不同答案 |

**查詢優先級**：customized > vendor > global

### 2.4 知識來源（Source Type）

| 來源 | 說明 |
|-----|------|
| manual | 人工輸入 |
| ai_generated | AI 自動生成 |
| imported | 從文件匯入 |
| ai_assisted | AI 輔助人工編寫 |

---

## 3. 關鍵參數列表

### 3.1 回測配置參數

**LoopConfig 模型**（定義於 `models.py`）：

| 參數 | 類型 | 預設值 | 範圍 | 說明 |
|------|------|--------|------|------|
| batch_size | int | 50 | 1-100 | 每批回測題數 |
| max_iterations | int | 20 | 1-50 | 最大迭代次數 |
| target_pass_rate | float | 0.8 | 0.0-1.0 | 目標通過率 |
| action_type_mode | str | ai_assisted | manual_only/ai_assisted/auto | 回應類型判斷模式 |

### 3.2 知識缺口分析參數

**失敗原因分類**（FailureReason 枚舉）：

| 原因 | 判斷條件 | 說明 |
|-----|---------|------|
| NO_MATCH | similarity < 0.6 | 無匹配知識 |
| LOW_CONFIDENCE | confidence_score < 0.7 | 信心度不足 |
| SEMANTIC_MISMATCH | semantic_overlap < 0.4 | 語義攔截 |
| SYSTEM_ERROR | error_type IS NOT NULL | 系統錯誤（timeout, 5xx） |

**缺口優先級**（GapPriority 枚舉）：

| 優先級 | 分類規則 | 說明 |
|--------|---------|------|
| P0 | similarity < 0.6 | 高優先級：高頻問題且無匹配知識 |
| P1 | confidence < 0.7 && similarity >= 0.6 | 中優先級：信心度不足但有部分匹配 |
| P2 | SEMANTIC_MISMATCH 或 SYSTEM_ERROR | 低優先級：系統錯誤或邊緣案例 |

### 3.3 環境變數配置

#### LLM 相關
```bash
# 提供商設定
LLM_PROVIDER=openai  # 全域預設
INTENT_CLASSIFIER_PROVIDER=openai
ANSWER_OPTIMIZER_PROVIDER=openai
EMBEDDING_PROVIDER=openai
DOCUMENT_CONVERTER_PROVIDER=openai
KNOWLEDGE_GEN_PROVIDER=openai

# 模型選擇
INTENT_CLASSIFIER_MODEL=gpt-3.5-turbo
KNOWLEDGE_GEN_MODEL=gpt-3.5-turbo
DOCUMENT_CONVERTER_MODEL=gpt-4o

# 溫度設定
INTENT_CLASSIFIER_TEMPERATURE=0.1
LLM_PARAM_INJECTION_TEMP=0.1
LLM_SYNTHESIS_TEMP=0.1
```

#### 相似度閾值
```bash
RAG_SIMILARITY_THRESHOLD=0.6          # RAG 檢索最低相似度
SOP_SIMILARITY_THRESHOLD=0.75         # SOP 檢索相似度
KB_SIMILARITY_THRESHOLD=0.65          # 知識庫檢索相似度
PERFECT_MATCH_THRESHOLD=0.90          # 完美匹配閾值
SYNTHESIS_THRESHOLD=0.80              # 答案合成觸發閾值
HIGH_QUALITY_THRESHOLD=0.65           # 高質量知識過濾閾值
SOP_SIMILARITY_SCORE=0.70             # SOP 項目相似度分數
```

#### 信心度配置
```bash
CONFIDENCE_HIGH_THRESHOLD=0.85        # 高信心度閾值（>= 0.85）
CONFIDENCE_MEDIUM_THRESHOLD=0.70      # 中等信心度閾值（>= 0.70）
FAST_PATH_THRESHOLD=0.75              # 快速路徑閾值（>= 此值觸發）
TEMPLATE_MIN_SCORE=0.55               # 模板格式化最低信心度
TEMPLATE_MAX_SCORE=0.75               # 模板格式化最高信心度
```

#### 質量評估
```bash
QUALITY_EVALUATION_ENABLED=true       # 是否啟用質量評估
QUALITY_EVALUATION_THRESHOLD=6        # 質量評估門檻（1-10，預設 6）
```

#### 意圖建議引擎
```bash
INTENT_SUGGESTION_TEMP=0.2            # 溫度設定
INTENT_SUGGESTION_MAX_TOKENS=800      # 最大 tokens
INTENT_SUGGESTION_SIMILARITY_THRESHOLD=0.80
```

#### 未釐清問題管理
```bash
UNCLEAR_SEMANTIC_THRESHOLD=0.80       # 語意相似度閾值
UNCLEAR_PINYIN_THRESHOLD=0.80         # 拼音相似度閾值
```

#### 知識合成配置
```bash
ENABLE_ANSWER_SYNTHESIS=true
SYNTHESIS_MIN_RESULTS=2               # 最少需要 2 個結果
SYNTHESIS_MAX_RESULTS=5               # 最多合成 5 個答案來源
```

#### 資料庫
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
```

#### Redis 快取
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
CACHE_TTL_QUESTION=3600              # 1 小時
CACHE_TTL_VECTOR=7200                # 2 小時
CACHE_TTL_RAG_RESULT=1800            # 30 分鐘
```

---

## 4. 服務模組清單

### 4.1 知識相關服務

| 模組 | 位置 | 主要功能 | 關鍵類別 |
|------|------|---------|---------|
| knowledge_classifier | services/knowledge_classifier.py | 知識自動分類（分配意圖） | KnowledgeClassifier |
| knowledge_generator | services/knowledge_generator.py | 知識內容生成 | KnowledgeGenerator |
| knowledge_import_service | services/knowledge_import_service.py | 知識批量匯入 | KnowledgeImportService |
| knowledge_export_service | services/knowledge_export_service.py | 知識匯出 | KnowledgeExportService |
| vendor_knowledge_retriever | services/vendor_knowledge_retriever_v2.py | 知識檢索 | VendorKnowledgeRetrieverV2 |

### 4.2 知識完善迴圈模組

| 模組 | 位置 | 主要功能 | 關鍵類別 |
|------|------|---------|---------|
| coordinator | knowledge_completion_loop/coordinator.py | 迴圈協調 + 狀態機 | LoopCoordinator |
| gap_analyzer | knowledge_completion_loop/gap_analyzer.py | 知識缺口分析 | GapAnalyzer |
| gap_classifier | knowledge_completion_loop/gap_classifier.py | 缺口分類 + 聚類 | GapClassifier |
| action_type_classifier | knowledge_completion_loop/action_type_classifier.py | 回應類型判斷 | ActionTypeClassifier |
| knowledge_generator | knowledge_completion_loop/knowledge_generator.py | 知識內容生成 | KnowledgeGeneratorClient |
| sop_generator | knowledge_completion_loop/sop_generator.py | SOP 流程生成 | SOPGenerator |
| cost_tracker | knowledge_completion_loop/cost_tracker.py | OpenAI API 成本追蹤 | OpenAICostTracker |
| backtest_client | knowledge_completion_loop/backtest_client.py | 回測框架客戶端 | BacktestFrameworkClient |
| models | knowledge_completion_loop/models.py | 資料模型 + 枚舉 | 所有 Pydantic & Enum |

### 4.3 SOP 相關服務

| 模組 | 位置 | 主要功能 | 關鍵類別 |
|------|------|---------|---------|
| sop_orchestrator | services/sop_orchestrator.py | SOP 檢索協調 | SOPOrchestrator |
| sop_utils | services/sop_utils.py | SOP 工具函數 | - |
| vendor_sop_retriever | services/vendor_sop_retriever_v2.py | SOP 檢索 | VendorSOPRetrieverV2 |
| sop_embedding_generator | services/sop_embedding_generator.py | SOP 向量生成 | - |
| sop_trigger_handler | services/sop_trigger_handler.py | SOP 觸發邏輯 | - |
| sop_keywords_handler | services/sop_keywords_handler.py | SOP 關鍵字匹配 | - |
| sop_next_action_handler | services/sop_next_action_handler.py | SOP 後續動作 | - |

---

## 5. API 端點清單

### 5.1 知識管理 API

**路由**：`routers/knowledge.py` (前綴：`/api/v1/knowledge`)

| 方法 | 端點 | 功能 | 請求模型 | 說明 |
|------|------|------|---------|------|
| POST | /classify | 分類單一知識 | ClassifySingleRequest | 為知識分配意圖類型 |
| POST | /classify/batch | 批次分類知識 | ClassifyBatchRequest | 支援過濾、預覽、後台處理 |
| POST | /mark-reclassify | 標記需要重新分類 | MarkReclassifyRequest | 標記意圖或所有知識 |
| GET | /stats | 獲取分類統計 | - | 按意圖統計 |

**ClassifySingleRequest**：
```json
{
  "knowledge_id": int,
  "question_summary": "optional string",
  "answer": "string",
  "assigned_by": "auto|manual"
}
```

**ClassifyBatchRequest**：
```json
{
  "filters": {
    "intent_ids": [1, 2],
    "max_confidence": 0.7,
    "assigned_by": "auto",
    "older_than_days": 30,
    "needs_reclassify": true
  },
  "batch_size": 100,
  "dry_run": false
}
```

### 5.2 知識匯入/匯出 API

**知識匯入路由**：`routers/knowledge_import.py` (前綴：`/api/v1/knowledge-import`)

| 方法 | 端點 | 功能 | 參數 |
|------|------|------|-----|
| POST | /upload | 上傳並開始匯入 | file, vendor_id, import_mode, enable_deduplication, skip_review, enable_quality_evaluation, business_types |
| GET | /job-status/{job_id} | 查詢匯入狀態 | - |
| GET | /job-status/{job_id}/logs | 查詢匯入日誌 | - |

**匯入選項**：
- mode：append（追加）, replace（替換）, merge（合併）
- skip_review：true（直接加入）, false（需審核，預設）

**支援檔案格式**：.xlsx, .xls, .csv, .txt, .json

### 5.3 知識匯出 API

**路由**：`routers/knowledge_export.py`

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | /export | 匯出知識庫 |
| GET | /export-template | 匯出模板 |

### 5.4 Platform SOP API

**路由**：`routers/platform_sop.py` (前綴：`/api/v1/platform/sop`)

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | /categories | 取得所有分類 |
| POST | /categories | 建立新分類 |
| GET | /categories/{id} | 取得單一分類 |
| PUT | /categories/{id} | 更新分類 |
| DELETE | /categories/{id} | 刪除分類 |
| GET | /templates | 取得所有範本 |
| POST | /templates | 建立新範本 |
| PUT | /templates/{id} | 更新範本 |
| DELETE | /templates/{id} | 刪除範本 |
| POST | /templates/import | 從 Excel 批量匯入 |
| GET | /templates/export | 匯出為 Excel |

---

## 6. 知識完善迴圈流程詳解

### 6.1 迴圈狀態機（13 個狀態）

定義於 `models.py` 的 `LoopStatus` 枚舉：

```python
PENDING = "pending"          # 待啟動
RUNNING = "running"          # 執行中（等待下一輪迭代）
BACKTESTING = "backtesting"  # 回測中
ANALYZING = "analyzing"      # 分析缺口中
GENERATING = "generating"    # 生成知識中
REVIEWING = "reviewing"      # 人工審核中
VALIDATING = "validating"    # 迭代驗證中
SYNCING = "syncing"          # 同步知識中
PAUSED = "paused"            # 已暫停
COMPLETED = "completed"      # 已完成
FAILED = "failed"            # 失敗
CANCELLED = "cancelled"      # 已取消
TERMINATED = "terminated"    # 已終止
```

### 6.2 8 步迴圈流程

**Coordinator 協調的完整流程**：

1. **Start Loop**（協調器.start_loop）
   - 驗證狀態：PENDING → RUNNING
   - 計算初始統計：總題數、預估迭代次數、目標通過率
   - 建立 loop 記錄到資料庫
   - 返回：loop_id, vendor_id, status, initial_statistics

2. **Execute Iteration**（協調器.execute_iteration）
   - 狀態轉移：RUNNING → BACKTESTING
   - 調用回測框架執行回測

3. **Backtest**（BacktestFrameworkClient）
   - 批次執行測試情境
   - 記錄每個測試的：passed/failed, confidence, similarity_score
   - 返回 backtest_run_id

4. **Analyze Gaps**（GapAnalyzer.analyze_failures）
   - 狀態轉移：BACKTESTING → ANALYZING
   - 讀取失敗案例
   - 分類失敗原因（5 種啟發式規則）
   - 判斷優先級（P0, P1, P2）
   - 去重合併相似缺口
   - 持久化到 knowledge_gap_analysis 表
   - 返回：缺口列表（gap_id, scenario_id, question, failure_reason, priority）

5. **Classify Gaps**（GapClassifier.classify）
   - 狀態轉移：ANALYZING → GENERATING
   - 調用 OpenAI API（gpt-4o-mini，temperature=0.3，max_tokens=4000）
   - 分類問題類型（4 種：sop_knowledge, form_fill, system_config, api_query）
   - 識別相似/重複問題
   - 適度聚類（2-5 個問題為一個聚類）
   - 返回：分類結果 + 聚類建議

6. **Generate Knowledge**（KnowledgeGeneratorClient）
   - 針對每個聚類的代表問題生成知識
   - 調用 OpenAI API（gpt-3.5-turbo，temperature=0.7，max_tokens=500）
   - 生成類型區分：
     * should_generate_knowledge=true：生成知識到 loop_generated_knowledge 表
     * should_generate_knowledge=false：標記為 api_query（不生成）
   - 記錄 generation_metadata：model, prompt, confidence, reviewed_by, edited
   - 返回：生成的知識候選列表

7. **Classify Action Type**（ActionTypeClassifier）
   - 針對生成的知識判斷回應類型（4 種：direct_answer, form_fill, api_call, form_then_api）
   - 調用 OpenAI API（gpt-4o-mini）
   - 判斷所需表單或 API
   - 設定 needs_manual_review 標誌（如果信心度 < 0.8）
   - 返回：ActionTypeJudgment（action_type, confidence, reasoning, form_id, api_id）

8. **Generate SOP**（SOPGenerator）
   - 針對 sop_knowledge 類型的缺口生成 SOP 內容
   - 調用 OpenAI API（gpt-4o-mini，temperature=0.3，max_tokens=1500）
   - 生成內容格式：item_name, content, trigger_mode, next_action, keywords
   - 寫入 vendor_sop_items 表
   - 同時更新 gap_classifier 的 should_generate_knowledge 狀態

9. **Manual Review & Approval**（人工審核）
   - 狀態轉移：GENERATING → REVIEWING
   - 人工審核生成的知識和 SOP
   - 批准（approved）、拒絕（rejected）、編輯（edited）

10. **Validate & Sync**（驗證與同步）
    - 狀態轉移：REVIEWING → VALIDATING → SYNCING
    - 將批准的知識同步到 knowledge_base 表（使用 approve_ai_knowledge_candidate 函數）
    - 將批准的 SOP 同步到生產環境

11. **Complete or Iterate**（完成或迭代）
    - 檢查是否達成目標通過率
    - 如果 pass_rate >= target_pass_rate：狀態 = COMPLETED
    - 如果 iterations < max_iterations：狀態 = RUNNING，繼續下一輪
    - 否則：狀態 = FAILED

### 6.3 資料庫表的狀態追蹤

知識完善迴圈涉及的關鍵表流轉：

```
backtest_runs（回測執行）
    ↓ 失敗案例
knowledge_gap_analysis（缺口分析）
    ↓ 分類 & 聚類
gap_classifications（缺口分類）
    ↓ 生成
loop_generated_knowledge（生成的知識）
    ↓ 判斷
action_type_judgments（回應類型判斷）
    ↓ 人工審核
loop_review_queue（審核佇列）
    ↓ 批准
knowledge_base（正式知識庫）
vendor_sop_items（SOP 項目）
```

---

## 7. OpenAI API 使用模式

### 7.1 模型選擇策略

| 用途 | 推薦模型 | 替代模型 | 選擇理由 |
|------|---------|---------|---------|
| 意圖分類 | gpt-3.5-turbo | gpt-4o-mini | 成本低（30% 成本），準確度足夠 |
| 答案優化 | gpt-4o-mini/gpt-4o | claude-3.5 | 品質高（需要精準回答） |
| 知識生成 | gpt-3.5-turbo | gpt-4o-mini | 成本低（1% 成本） |
| 文件轉換 | gpt-4o | claude-opus | 支援 128K context，適合大文件 |
| 缺口分類 | gpt-4o-mini | gpt-4o | 平衡成本與品質 |
| SOP 生成 | gpt-4o-mini | gpt-4o | 平衡成本與品質 |
| 回應類型判斷 | gpt-4o-mini | gpt-4o | 邏輯判斷任務 |

### 7.2 Temperature 配置

| 任務 | Temperature | 說明 |
|------|-------------|------|
| 意圖分類 | 0.1 | 極低，保證一致分類 |
| 知識生成 | 0.7 | 中等，允許創意但保持準確 |
| SOP 生成 | 0.3 | 較低，確保結構化輸出 |
| 缺口分類 | 0.3 | 較低，保證穩定分類 |
| 回應類型判斷 | 0.1 | 極低，邏輯判斷需要確定性 |
| 參數注入 | 0.1 | 極低，避免參數替換錯誤 |
| 答案合成 | 0.1 | 極低，提高參數替換準確性 |

### 7.3 Max Tokens 配置

| 任務 | Max Tokens | 說明 |
|------|-----------|------|
| 意圖分類 | 500 | 短答案 |
| 知識生成 | 500 | 100-300 字答案 |
| SOP 生成 | 1500 | 200-500 字 SOP 內容 |
| 缺口分類 | 4000 | 多問題聚類分析 |
| 回應類型判斷 | 300 | 短判斷結果 |

### 7.4 Prompt 工程範例

#### 7.4.1 缺口分類 Prompt

關鍵特徵：
- 將問題分類為 4 種：sop_knowledge, form_fill, system_config, api_query
- 聚類相似問題（2-5 個為一個聚類）
- 輸出 JSON 格式，包含：classifications + clusters + summary

#### 7.4.2 知識生成 Prompt

關鍵特徵：
- 提供上下文：failure_reason（為什麼失敗）、suggested_action_type（建議回應類型）、vendor_type（業者類型）
- 參考現有相似知識
- 輸出 JSON：answer + keywords + confidence_explanation + needs_verification

#### 7.4.3 SOP 生成 Prompt

關鍵特徵：
- 精準匹配原則：SOP 名稱必須與內容精準匹配，避免過於籠統
- 每個 SOP 只處理一個具體流程或政策，不要合併不相關的主題
- trigger_mode + next_action 判斷
- 輸出 JSON：item_name + content + trigger_mode + trigger_keywords + next_action + next_form_id

---

## 8. 配置與環境變數全集

### 8.1 LLM Provider 配置

```bash
# 全域設定
LLM_PROVIDER=openai

# 分服務 Provider（留空使用全域設定）
INTENT_CLASSIFIER_PROVIDER=openai
ANSWER_OPTIMIZER_PROVIDER=openai
EMBEDDING_PROVIDER=openai
DOCUMENT_CONVERTER_PROVIDER=openai
KNOWLEDGE_GEN_PROVIDER=openai

# API Keys
OPENAI_API_KEY=sk-proj-...
OPENROUTER_API_KEY=sk-or-...  # 可選
OLLAMA_API_URL=http://localhost:11434  # 可選
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 8.2 模型配置

```bash
INTENT_CLASSIFIER_MODEL=gpt-3.5-turbo
INTENT_CLASSIFIER_TEMPERATURE=0.1
INTENT_CLASSIFIER_MAX_TOKENS=500

KNOWLEDGE_GEN_MODEL=gpt-3.5-turbo
DOCUMENT_CONVERTER_MODEL=gpt-4o
```

### 8.3 相似度閾值

```bash
RAG_SIMILARITY_THRESHOLD=0.6
SOP_SIMILARITY_THRESHOLD=0.75
KB_SIMILARITY_THRESHOLD=0.65
HIGH_QUALITY_THRESHOLD=0.65
PERFECT_MATCH_THRESHOLD=0.90
SYNTHESIS_THRESHOLD=0.80
SOP_SIMILARITY_SCORE=0.70
```

### 8.4 信心度配置

```bash
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.70
FAST_PATH_THRESHOLD=0.75
TEMPLATE_MIN_SCORE=0.55
TEMPLATE_MAX_SCORE=0.75
LLM_PARAM_INJECTION_TEMP=0.1
LLM_SYNTHESIS_TEMP=0.1
```

### 8.5 答案合成配置

```bash
ENABLE_ANSWER_SYNTHESIS=true
SYNTHESIS_THRESHOLD=0.80
SYNTHESIS_MIN_RESULTS=2
SYNTHESIS_MAX_RESULTS=5
```

### 8.6 品質評估

```bash
QUALITY_EVALUATION_ENABLED=true
QUALITY_EVALUATION_THRESHOLD=6
```

### 8.7 意圖建議

```bash
INTENT_SUGGESTION_TEMP=0.2
INTENT_SUGGESTION_MAX_TOKENS=800
INTENT_SUGGESTION_SIMILARITY_THRESHOLD=0.80
```

### 8.8 未釐清問題

```bash
UNCLEAR_SEMANTIC_THRESHOLD=0.80
UNCLEAR_PINYIN_THRESHOLD=0.80
```

### 8.9 資料庫

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
```

### 8.10 Redis 快取

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
CACHE_TTL_QUESTION=3600
CACHE_TTL_VECTOR=7200
CACHE_TTL_RAG_RESULT=1800
```

### 8.11 AWS S3 影片儲存

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-northeast-1
S3_BUCKET_NAME=jgb2-production-upload
CLOUDFRONT_DOMAIN=d1h2hzes3rmzug.cloudfront.net
```

### 8.12 優先級加成

```bash
PRIORITY_BOOST=0.15
PRIORITY_QUALITY_THRESHOLD=0.70
```

### 8.13 帳單 API

```bash
BILLING_API_BASE_URL=http://localhost:8000
BILLING_API_KEY=...
BILLING_API_TIMEOUT=10.0
USE_MOCK_BILLING_API=true
```

---

## 9. 重要常量與枚舉

### 9.1 Knowledge Base 常量

**業態類型（business_types）**：
- system_provider：系統商
- full_service：包租型
- property_management：代管型

**目標用戶（target_user）**：
- tenant：租客
- landlord：房東
- property_manager：物業管理師
- system_admin：系統管理員

**知識範圍（scope）**：
- global：全域
- vendor：業者專屬
- customized：業者客製化

**知識來源（source_type）**：
- manual：人工輸入
- ai_generated：AI 生成
- imported：匯入
- ai_assisted：AI 輔助

**知識狀態（status）**：
- pending_review：待審核
- approved：已批准
- rejected：已拒絕
- draft：草稿

### 9.2 意圖相關常量

**意圖類型（type）**：
- knowledge：知識類
- data_query：資料查詢
- action：動作
- hybrid：混合

**意圖狀態（is_enabled）**：
- true：啟用
- false：禁用

### 9.3 知識缺口常量

**失敗原因（FailureReason）**：
- no_match：無匹配知識（similarity < 0.6）
- low_confidence：信心度不足（confidence < 0.7）
- semantic_mismatch：語義不符（semantic_overlap < 0.4）
- system_error：系統錯誤

**缺口優先級（GapPriority）**：
- p0：高優先級
- p1：中優先級
- p2：低優先級

### 9.4 回應類型常量（ActionType）

- DIRECT_ANSWER：純知識問答
- FORM_FILL：表單+知識
- API_CALL：API+知識
- FORM_THEN_API：表單+API+知識

### 9.5 迴圈狀態常量（LoopStatus）

13 個狀態如 6.1 所述

---

## 10. 程式碼範例

### 10.1 知識分類範例

```python
from services.knowledge_classifier import KnowledgeClassifier

# 初始化分類器
classifier = KnowledgeClassifier()

# 分類單一知識
result = classifier.classify_single_knowledge(
    knowledge_id=123,
    question_summary="如何續約？",
    answer="租約續約步驟如下...",
    assigned_by='auto'
)

# result 包含：
# {
#   'knowledge_id': 123,
#   'classified': True,
#   'intent_id': 5,
#   'intent_name': '租約查詢',
#   'confidence': 0.95,
#   'all_intents': [5],
#   'secondary_intents': [],
#   'reason': 'Classified successfully'
# }
```

### 10.2 缺口分析範例

```python
from services.knowledge_completion_loop.gap_analyzer import GapAnalyzer
import psycopg2.pool

# 初始化
db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, **db_config)
analyzer = GapAnalyzer(db_pool)

# 分析失敗案例
gaps = await analyzer.analyze_failures(
    loop_id=1,
    iteration=1,
    backtest_run_id=100
)

# gaps 是缺口列表，包含：
# [
#   {
#     'gap_id': 1,
#     'scenario_id': 45,
#     'question': '租金包含哪些費用？',
#     'failure_reason': 'no_match',
#     'priority': 'p0',
#     'suggested_action_type': 'direct_answer',
#     'confidence_score': 0.45,
#     'max_similarity': 0.55,
#     'intent_id': None,
#     'intent_name': None,
#     'frequency': 3
#   },
#   ...
# ]
```

### 10.3 知識生成範例

```python
from services.knowledge_completion_loop.knowledge_generator import KnowledgeGeneratorClient
import os

# 初始化
openai_api_key = os.getenv('OPENAI_API_KEY')
generator = KnowledgeGeneratorClient(
    openai_api_key=openai_api_key,
    db_pool=db_pool,
    model='gpt-3.5-turbo'  # 低成本模型
)

# 批次生成知識
knowledge_list = await generator.generate_knowledge(
    loop_id=1,
    gaps=[...],  # gap list
    action_type_judgments={...},
    iteration=1,
    vendor_id=1
)

# 返回：生成的知識列表（已存到 loop_generated_knowledge 表）
```

### 10.4 SOP 生成範例

```python
from services.knowledge_completion_loop.sop_generator import SOPGenerator

# 初始化
sop_gen = SOPGenerator(
    db_pool=db_pool,
    openai_api_key=openai_api_key,
    cost_tracker=cost_tracker,
    model='gpt-4o-mini'  # 平衡成本與品質
)

# 生成 SOP
sop_items = await sop_gen.generate_sop(
    gap_list=[...],
    vendor_id=1,
    action_type_judgments={...}
)

# 返回：生成的 SOP 列表（已存到 vendor_sop_items 表）
```

### 10.5 API 使用範例

#### 知識分類 API
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/classify \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_id": 123,
    "question_summary": "如何續約？",
    "answer": "租約續約步驟如下...",
    "assigned_by": "auto"
  }'
```

#### 知識匯入 API
```bash
curl -X POST http://localhost:8000/api/v1/knowledge-import/upload \
  -F "file=@knowledge.xlsx" \
  -F "vendor_id=1" \
  -F "import_mode=append" \
  -F "enable_deduplication=true" \
  -F "skip_review=false"
```

#### Platform SOP API
```bash
curl -X GET http://localhost:8000/api/v1/platform/sop/categories
curl -X POST http://localhost:8000/api/v1/platform/sop/categories \
  -H "Content-Type: application/json" \
  -d '{
    "category_name": "租約管理",
    "description": "與租約相關的 SOP",
    "display_order": 1
  }'
```

---

## 11. 數據流圖

```
用戶提問 → RAG 檢索 → 低信心度/無匹配
    ↓
回測框架執行回測
    ↓
Gap Analyzer 分析失敗
    ↓ （分類原因、判斷優先級、去重合併）
Gap Classifier 分類缺口
    ↓ （4 種類型、聚類）
Action Type Classifier 判斷回應類型
    ↓ （4 種類型、所需表單/API）
Knowledge Generator 生成知識
    ↓ （只針對 should_generate_knowledge=true）
SOP Generator 生成 SOP
    ↓ （針對 sop_knowledge 類型）
人工審核佇列
    ↓
批准 → 同步到 knowledge_base / vendor_sop_items
拒絕 → 標記為需修改
```

---

## 12. 總結

AIChatbot 的知識系統是一個複雜的、多層次的、完全可追蹤的系統：

1. **資料層**：基於 PostgreSQL + pgvector，支援向量檢索和多維度過濾
2. **分類層**：4 種知識類型 + 4 種回應類型，清晰的分類體系
3. **生成層**：AI 輔助的知識和 SOP 生成，人工審核機制
4. **迴圈層**：8 步完整的知識完善迴圈，從缺口分析到知識生成
5. **配置層**：100+ 環境變數，精細化的閾值控制
6. **API 層**：RESTful 路由，支援單條和批量操作

所有組件通過 LoopCoordinator 協調，形成一個自動化的、可控的、可觀測的知識管理平台。

