# Structure Steering

## 專案組織

```
AIChatbot/
├── .kiro/                              # Kiro 專案管理
│   ├── steering/                       # 專案記憶與指導
│   │   ├── product.md                  # 產品定位
│   │   ├── tech.md                     # 技術規範
│   │   ├── structure.md                # 專案結構
│   │   └── operations.md               # 運維操作指南
│   ├── specs/                          # 功能規格
│   │   └── {feature-name}/
│   │       ├── spec.json               # 規格元數據
│   │       ├── requirements.md         # 需求文檔
│   │       ├── design.md               # 設計文檔
│   │       └── tasks.md                # 實作任務
│   └── settings/                       # Kiro 設定
│
├── rag-orchestrator/                   # 主服務 (RAG 編排器)
│   ├── app.py                          # FastAPI 應用入口
│   ├── requirements.txt                # Python 依賴
│   │
│   ├── routers/                        # API 路由層
│   │   ├── agent.py                    # /mcp 門面掛載（agentic-mcp-orchestration；prefix 在 router 內）
│   │   ├── vendors.py                  # 業者管理
│   │   ├── knowledge.py                # 知識 CRUD
│   │   ├── knowledge_generation.py     # 知識生成
│   │   ├── knowledge_import.py         # 知識匯入
│   │   ├── knowledge_export.py         # 知識匯出
│   │   ├── forms.py                    # 表單管理（後台 CRUD 仍活，對話填單引擎已退役——見 F4/archive）
│   │   ├── conversational_configs.py   # 對話式回答設定管理
│   │   ├── unclear_questions.py        # 未釐清問題
│   │   ├── loops.py                    # 知識完善迴圈
│   │   ├── loop_knowledge.py           # 迴圈知識審核
│   │   ├── api_endpoints.py            # 外部 API 管理
│   │   ├── lookup.py                   # Lookup 表管理
│   │   ├── images.py                   # 圖片上傳
│   │   ├── videos.py                   # 視頻管理
│   │   ├── document_converter.py       # 文檔轉換
│   │   ├── ocr_mapping.py              # OCR 合約映射
│   │   ├── business_types.py           # 業態類型
│   │   ├── target_user_config.py       # 目標用戶配置
│   │   ├── cache.py                    # 快取管理
│   │   ├── system_health.py            # 系統健康檢查
│   │   └── error_middleware.py         # 錯誤處理中介
│   │   （⚠️ 2026-09-11 舊鏈退役：`chat.py`／`chat_shared.py`／`platform_sop.py`／
│   │    `intents.py`／`suggested_intents.py`／`agent_entry.py` 等 31 個舊 REST
│   │    對話鏈模組已刪或未掛載，見 `.claude/DECISIONS.md` DSP-046）
│   │
│   ├── services/                       # 業務邏輯層
│   │   ├── form_contract.py            # 表單契約（結構化 schema，取代舊 form_manager）
│   │   ├── decision_layer.py           # 決策層
│   │   ├── conversational_config.py    # 對話式設定讀取
│   │   ├── conversational_rules.py     # 對話式規則
│   │   ├── presales_gate.py            # 售前 grounding 閘門
│   │   ├── grounding_presentation.py   # grounding 呈現
│   │   ├── retrieval_representation.py # representation 契約（general/instance 兩把尺）
│   │   ├── responsibility_*.py         # 責任分攤系列（artifacts/completion/session/entity_resolution/bill_resolution）
│   │   ├── usage_metering.py           # 額度計量
│   │   ├── api_key_auth.py             # API key 驗證
│   │   ├── instance_applicability.py   # 面向實例可適用性
│   │   ├── fulfillment_registry.py     # 履行動作登記
│   │   │
│   │   ├── agent/                      # agentic-mcp-orchestration 新線（現役核心）
│   │   │   ├── runtime.py              # AgentRuntime.run_turn——一整回合邏輯
│   │   │   ├── mcp_facade.py           # /mcp 工具面實作（tools/list、tools/call、agent.turn）
│   │   │   ├── agent_rules.py          # 對話規則
│   │   │   ├── identity.py             # X-JGB-Identity 解析、audience_of
│   │   │   ├── verifier.py             # Output Verifier（逐句驗引用）
│   │   │   ├── session_persistence.py  # /mcp 會話狀態層（取代舊鏈 ConversationalEngine 持久化）
│   │   │   ├── state_store.py          # 回合狀態存取點
│   │   │   ├── outline.py              # 面向大綱組裝
│   │   │   ├── shadow.py               # 影子跑動
│   │   │   ├── health.py               # 健康檢查
│   │   │   └── ...
│   │   │
│   │   ├── knowledge_completion_loop/  # 知識完善迴圈
│   │   │   ├── coordinator.py          # 迴圈協調器
│   │   │   ├── gap_analyzer.py         # 缺口分析器
│   │   │   ├── action_type_classifier.py # 動作類型分類器
│   │   │   ├── gap_classifier.py       # 缺口聚類分類器
│   │   │   ├── knowledge_generator.py  # 知識生成器
│   │   │   ├── cost_tracker.py         # 成本追蹤器
│   │   │   ├── review_timeout_monitor.py # 審核超時監控
│   │   │   ├── clients.py              # API 客戶端封裝
│   │   │   ├── models.py               # 資料模型
│   │   │   └── run_first_loop.py       # 執行腳本
│   │   │
│   │   ├── ocr_mapping/                # OCR 合約映射（clause_splitter/contract_mapper/deposit_rule…）
│   │   │
│   │   ├── jgb/                        # JGB 面向邏輯（帳單/合約/物件/IoT/修繕 fixtures 與轉接）
│   │   │   ├── bills.py                # 帳單
│   │   │   ├── contracts.py            # 合約
│   │   │   ├── repairs.py              # 修繕
│   │   │   ├── estates.py              # 物件
│   │   │   ├── iot.py                  # IoT
│   │   │   └── transport.py            # jgb2 API 轉接
│   │   │
│   │   ├── base_retriever.py           # 基礎檢索器
│   │   ├── vendor_knowledge_retriever_v2.py # 業者知識檢索器
│   │   ├── semantic_reranker.py        # 語義重排序器
│   │   ├── knowledge_classifier.py     # 知識分類器
│   │   ├── knowledge_generator.py      # 知識生成服務
│   │   ├── knowledge_import_service.py # 知識匯入服務
│   │   ├── knowledge_export_service.py # 知識匯出服務
│   │   ├── unclear_question_manager.py # 未釐清問題管理器
│   │   ├── intent_semantic_matcher.py  # 意圖語義匹配器
│   │   ├── sop_embedding_generator.py  # SOP 嵌入生成器
│   │   ├── sop_utils.py                # SOP 工具函式
│   │   ├── vendor_parameter_resolver.py # 業者參數解析器
│   │   ├── document_converter_service.py # 文檔轉換服務
│   │   ├── image_recognition_service.py # 圖片辨識服務
│   │   ├── s3_image_service.py         # S3 圖片服務
│   │   ├── s3_video_service.py         # S3 視頻服務
│   │   ├── llm_provider.py             # LLM 提供者
│   │   ├── query_rewriter.py           # 查詢改寫器
│   │   ├── intent_suggestion_engine.py # 意圖建議引擎
│   │   ├── embedding_utils.py          # Embedding 工具
│   │   ├── db_utils.py                 # 資料庫工具
│   │   ├── pipeline_health_service.py  # 管線健康檢查
│   │   ├── unified_job_service.py      # 統一背景任務
│   │   ├── jgb_system_api.py           # JGB 系統 API
│   │   └── ...
│   │   （⚠️ 2026-09-11 舊鏈退役：`sop_orchestrator.py`／`sop_trigger_handler.py`／
│   │    `sop_next_action_handler.py`／`conversational_engine.py`／
│   │    `llm_answer_optimizer.py`／`digression_detector.py`／`keyword_matcher.py`／
│   │    `universal_api_handler.py`／`billing_api.py`／`answer_formatter.py`／
│   │    `jgb_response_formatter.py`／`vendor_config_service.py`／
│   │    `vendor_sop_retriever_v2.py`／`form_manager.py`／`form_validator.py`／
│   │    `intent_manager.py` 已刪，職責由 `services/agent/**` 與
│   │    `services/form_contract.py` 等取代)
│   │
│   ├── models/                         # 資料模型
│   │   ├── unclear_question.py         # 未釐清問題模型
│   │   └── ...
│   │
│   ├── config/                         # 配置管理
│   │   ├── deduplication_config.py     # 去重配置
│   │   ├── business_types.py           # 業態類型配置
│   │   └── intents.yaml                # 意圖 YAML（DB fallback）
│   │
│   ├── utils/                          # 工具函數（目前為空，工具已移至 services/）
│   │   └── __init__.py
│   │
│   ├── tests/                          # 測試檔案（unit/integration/e2e 三層，見 testing-code.md）
│   │   ├── unit/agent/                 # /mcp 新線 unit 測試主力
│   │   ├── integration/agent/          # /mcp 新線 integration 驗收
│   │   └── ...
│   │
│   ├── scripts/                        # 工具腳本
│   │   ├── backtest/
│   │   │   └── backtest_framework_async.py  # 回測框架 V2（迴圈呼叫）
│   │   ├── migrate_yaml_intents_to_db.py
│   │   └── ...
│   │
│   └── Dockerfile                      # Docker 映像檔
│
├── embedding-service/                  # 嵌入服務
│   └── ...
│
├── knowledge-admin/                    # 管理後台
│   └── frontend/src/views/
│       ├── CategoryConfigView.vue      # 類別配置管理
│       └── ...
│
├── semantic_model/                     # 語義模型服務
│   └── ...
│
├── scripts/                            # 全域腳本
│   └── backtest/                       # 回測相關腳本
│       └── backtest_framework_async.py
│
├── docs/                               # 文檔目錄
│   ├── backtest/                       # 回測文檔
│   │   ├── QUICK_REFERENCE.md
│   │   ├── GAP_CLASSIFIER_INTEGRATION.md
│   │   └── ...
│   └── SOP*.md                         # SOP 文檔
│
├── docker-compose.yml                  # Docker Compose 配置 (開發)
├── docker-compose.prod.yml             # Docker Compose 配置 (生產)
├── .env                                # 環境變數 (不納入版控)
├── .gitignore                          # Git 忽略規則
├── README.md                           # 專案說明
└── CLAUDE.md                           # AI 開發指南
```

## 命名模式

### 服務模組 (services/)
- **核心引擎**: `{domain}_engine.py` (如 `intent_suggestion_engine.py`)
- **分類器**: `{domain}_classifier.py` (如 `intent_classifier.py`, `action_type_classifier.py`)
- **管理器**: `{domain}_manager.py` (如 `unclear_question_manager.py`)
- **編排器**: `{domain}_orchestrator.py`（⚠️ 2026-09-11 舊鏈退役後目前無存活範例——原範例
  `sop_orchestrator.py` 已刪；比照套用於未來新檔即可）
- **檢索器**: `{domain}_retriever.py` 或 `{domain}_retriever_v2.py` (如 `vendor_knowledge_retriever_v2.py`)
- **處理器**: `{domain}_handler.py`（⚠️ 舊鏈退役後目前無存活範例——原範例 `api_call_handler.py`／
  `sop_trigger_handler.py` 已刪；比照套用於未來新檔即可）
- **評估器**: `{domain}_evaluator.py` (如 `confidence_evaluator.py`)
- **優化器**: `{domain}_optimizer.py`（⚠️ 舊鏈退役後目前無存活範例——原範例
  `llm_answer_optimizer.py` 已刪；比照套用於未來新檔即可）
- **生成器**: `{domain}_generator.py` (如 `knowledge_generator.py`, `sop_embedding_generator.py`)
- **驗證器**: `{domain}_validator.py`（⚠️ 舊鏈退役後目前無存活範例——原範例
  `form_validator.py` 已刪；比照套用於未來新檔即可）
- **解析器**: `{domain}_resolver.py` 或 `{domain}_matcher.py` (如 `vendor_parameter_resolver.py`, `intent_semantic_matcher.py`)
- **追蹤器**: `{domain}_tracker.py` (如 `cost_tracker.py`)
- **監控器**: `{domain}_monitor.py` (如 `review_timeout_monitor.py`)
- **工具服務**: `{service_name}_service.py` (如 `cache_service.py`, `pipeline_health_service.py`)

### 路由模組 (routers/)
- **資源路由**: `{resource}.py` (如 `knowledge.py`, `forms.py`, `vendors.py`)
- **操作路由**: `{resource}_{operation}.py` (如 `knowledge_import.py`, `knowledge_export.py`)

### 配置模組 (config/)
- **配置檔**: `{config_name}_config.py` (如 `deduplication_config.py`)
- **靜態資料**: `{domain}.py` (如 `business_types.py`)

### 知識完善迴圈模組 (services/knowledge_completion_loop/)
- **協調器**: `coordinator.py` - 統籌整個迴圈流程
- **分析器**: `{domain}_analyzer.py` - 分析特定領域 (如 `gap_analyzer.py`)
- **分類器**: `{domain}_classifier.py` - 分類特定領域
- **生成器**: `{domain}_generator.py` - 生成特定內容
- **追蹤器**: `{domain}_tracker.py` - 追蹤特定指標
- **監控器**: `{domain}_monitor.py` - 監控特定狀態
- **客戶端**: `clients.py` - API 客戶端封裝
- **模型**: `models.py` - 資料模型定義
- **執行腳本**: `run_{task}.py` - 執行特定任務

### 測試檔案 (tests/)
- **單元測試**: `test_{module}_req.py`（`_req` 對應追溯標記，見 `.kiro/steering/testing-code.md`；
  如 `tests/unit/security/test_api_key_auth_req.py`）
- **整合測試**: `test_{module}_integration.py`
- **端到端測試**: `test_e2e_{scenario}.py`

### 腳本檔案 (scripts/, /tmp/)
- **遷移腳本**: `migrate_{description}.py`
- **執行腳本**: `run_{task}.py`（如 `run_first_loop.py`）
- **分析腳本**: `analyze_{subject}.py` (如 `analyze_coverage.py`)
- **生成腳本**: `generate_{content}.py` (如 `generate_test_scenarios.py`)
- **匯入腳本**: `import_{source}.py` (如 `import_generated_tests.py`)

## 匯入規範

### 標準庫匯入
```python
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
```

### 第三方庫匯入
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncpg
from openai import OpenAI
```

### 本地模組匯入
```python
# 服務層
from services.rag_engine import RAGEngine
from services.intent_classifier import IntentClassifier

# 工具層
from utils.db_utils import get_db_connection
from utils.embedding_utils import get_embedding_client

# 配置層
from config.deduplication_config import DeduplicationConfig
```

### 相對匯入
- **避免使用**: 優先使用絕對匯入
- **同級模組**: 可使用相對匯入 (如 `from .base_retriever import BaseRetriever`)

## 資料庫表結構模式

### 核心表
- **test_scenarios**: 測試場景管理
  - 欄位: id, vendor_id, test_question, expected_answer, difficulty, source, status, created_at, updated_at
  - 索引: vendor_id, source, status, created_at

- **backtest_results**: 回測結果
  - 欄位: id, vendor_id, scenario_id, run_id, pass, reason, retrieved_docs, answer, created_at
  - 索引: vendor_id, scenario_id, run_id, pass, created_at

- **knowledge_base**: 通用知識庫
  - 欄位: id, vendor_id, title, content, category, target_users, business_types, embedding, created_at, updated_at
  - 索引: vendor_id, category, target_users, business_types, embedding (pgvector index)

- **vendor_sop_categories**: SOP 分類
- **vendor_sop_groups**: SOP 群組
- **vendor_sop_items**: SOP 項目
- **knowledge_completion_loops**: 知識完善迴圈執行記錄
- **loop_execution_logs**: 迴圈執行日誌
- **vendors**: 業者資料
- **vendor_configs**: 業者配置

### 欄位命名規範
- **主鍵**: `id` (SERIAL or BIGSERIAL)
- **外鍵**: `{table}_id` (如 `vendor_id`, `scenario_id`)
- **時間戳**: `created_at`, `updated_at` (TIMESTAMP)
- **狀態**: `status` (VARCHAR 或 ENUM)
- **向量**: `embedding` (VECTOR type from pgvector)
- **JSON**: `{field}_json` 或直接使用有意義的名稱 (JSONB type)

## 環境變數模式

### 資料庫
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

### API Keys
- `OPENAI_API_KEY`

### LLM 模型配置
- `OPENAI_MODEL`: 答案優化模型 (預設 gpt-4o-mini)
- `INTENT_CLASSIFIER_MODEL`: 意圖分類模型 (預設 gpt-3.5-turbo)
- `KNOWLEDGE_GEN_MODEL`: 知識生成模型 (預設 gpt-4o-mini)
- `DOCUMENT_CONVERTER_MODEL`: 文件轉換模型 (預設 gpt-4o)
- `QUERY_REWRITE_MODEL`: 查詢改寫模型 (預設 gpt-3.5-turbo)
- `EMBEDDING_MODEL`: Embedding 模型 (預設 text-embedding-3-small)
- `LLM_ANSWER_TEMPERATURE`, `LLM_ANSWER_MAX_TOKENS`: 答案生成溫度/token
- `INTENT_CLASSIFIER_TEMPERATURE`, `INTENT_CLASSIFIER_MAX_TOKENS`
- `LLM_SYNTHESIS_TEMP`: 合成溫度 (預設 0.5)

### 服務配置
- `RAG_RETRIEVAL_LIMIT`: RAG 檢索限制 (預設 5)
- `PRIORITY_BOOST`: 優先級加成 (預設 0.15)
- `PRIORITY_QUALITY_THRESHOLD`: 優先級品質門檻 (預設 0.70)
- `USE_SEMANTIC_RERANK`: 是否啟用語義重排序 (預設 false)
- `ENABLE_ANSWER_SYNTHESIS`: 是否啟用答案合成 (預設 false)
- `SYNTHESIS_THRESHOLD`: 答案合成閾值 (預設 0.80)
- `PERFECT_MATCH_THRESHOLD`: 完美匹配閾值 (預設 0.90)
- `FAST_PATH_THRESHOLD`: 快速路徑閾值 (預設 0.75)
- `CONFIDENCE_HIGH_THRESHOLD`: 高信心度 (預設 0.85)
- `CONFIDENCE_MEDIUM_THRESHOLD`: 中信心度 (預設 0.70)
- `ENABLE_QUERY_REWRITE`: 是否啟用查詢改寫
- `ENABLE_RERANKER`: 是否啟用 Reranker
- `RERANKER_INPUT_LIMIT`: Reranker 輸入限制 (預設 20)
- `SEMANTIC_API_URL`: 語義模型 API URL

### SOP 配置
- `SOP_SIMILARITY_THRESHOLD`: SOP 相似度閾值 (預設 0.55)
- `KB_SIMILARITY_THRESHOLD`: 知識庫相似度閾值 (預設 0.6)

### 回測配置
- `VENDOR_ID`: 業者 ID
- `BACKTEST_ONLY`: 僅執行回測模式 (true/false)
- `BACKTEST_CONCURRENCY`, `BACKTEST_TIMEOUT`, `BACKTEST_QUALITY_MODE` 等

### Redis
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `CACHE_ENABLED`, `CACHE_TTL_QUESTION`, `CACHE_TTL_VECTOR`, `CACHE_TTL_RAG_RESULT`

### AWS S3
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME`, `CLOUDFRONT_DOMAIN`

### 外部 API
- `BILLING_API_BASE_URL`, `BILLING_API_KEY`, `USE_MOCK_BILLING_API`
- `JGB_API_BASE_URL`, `JGB_API_KEY`, `USE_MOCK_JGB_API`
- `ENABLE_IMAGE_RECOGNITION`, `IMAGE_RECOGNITION_MODEL`

## 文件組織模式

### 文檔目錄 (docs/)
- **功能文檔**: `{feature}/*.md`
- **操作手冊**: `{operation}_*.md` (如 `SOP_*.md`)
- **快速參考**: `QUICK_REFERENCE.md`
- **整合指南**: `*_INTEGRATION.md`
- **完成摘要**: `*_SUMMARY.md`
- **計劃文檔**: `*_PLAN.md`

### 規格目錄 (.kiro/specs/)
- **規格元數據**: `spec.json`
- **需求文檔**: `requirements.md`
- **設計文檔**: `design.md`
- **任務清單**: `tasks.md`
- **研究筆記**: `research.md`
- **驗證報告**: `validation_{type}.md`

### 臨時檔案 (/tmp/)
- **日誌**: `{task}_*.log`
- **分析結果**: `{analysis}_*.txt` 或 `{analysis}_*.json`
- **腳本**: `{task}_*.py` 或 `{task}_*.sh`
- **資料檔**: `{data}_*.csv` 或 `{data}_*.json`

---

## 2026-07 現況增補（本節為最新，與上文衝突時以本節與 docs/architecture-overview.md 為準）

- **對話面向體系**：資料驅動（`category='對話規則'` 一筆設定＝一個面向，新增零改程式），分**診斷（唯讀）＋交易（寫入）兩型**。診斷面向 21＋售前個，五域（合約/帳務/帳號/物件/IoT）機械判定用 `services/jgb/*` FACE_BUILDERS、LLM 只照 facts 組話。**交易面向**（2026-07-12 conversational-repair 收案，commit 646743a）：引擎長出交易語義（confirm gate／execute／冪等），修繕為第一個交易面向；判定＝面向配置 `grounding_scope.execute_endpoint` 存在，全配置驅動，下一個交易面向＝加配置與 seeds、引擎零改動（目標）。**b2c 租客報修改走對話面向**：vendor 2/4 修繕子集 SOP 已停用（M2，可逆），SOP 仍為 b2c 其餘場景專用。
- **資料體系分工（定案）**：`vendor_configs`＝通用單值參數（{{param}} 模板）；`lookup_tables`＝案場級（Excel 匯入＋錨點）；SOP＝b2c 專用（b2b 不走）；jgb API＝個資（role_id+user_id 雙證）。
- **計量與額度**：usage_events 每請求計量（token/成本/內部流量標記）；vendor_quotas 月額度（達限攔截/警示寄信）。
- **品質三層**：unit（make test-unit）／系統回測（迴圈＋多輪模擬＋v3 評審＋金標，按受眾分庫）／不變量稽核（make audit，修一類 bug＝加一條）。驗收鐵則：改引擎行為以系統路徑實跑收案。
- **單一真相源**：`docs/architecture-overview.md`（含已知債總表）；部署走 `docs/deployment-runbook.md`。
