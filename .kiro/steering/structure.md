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
│   │   ├── chat.py                     # 聊天對話
│   │   ├── knowledge.py                # 知識管理
│   │   ├── platform_sop.py             # SOP 編排
│   │   ├── forms.py                    # 表單管理
│   │   ├── api_endpoints.py            # 外部 API 管理
│   │   ├── lookup.py                   # Lookup 表管理
│   │   ├── intents.py                  # 意圖管理
│   │   ├── unclear_questions.py        # 未釐清問題
│   │   ├── suggested_intents.py        # 意圖建議
│   │   ├── knowledge_import.py         # 知識匯入
│   │   ├── knowledge_export.py         # 知識匯出
│   │   ├── videos.py                   # 視頻管理
│   │   ├── business_types.py           # 業態類型
│   │   ├── target_user_config.py       # 目標用戶配置
│   │   ├── document_converter.py       # 文檔轉換
│   │   └── cache.py                    # 快取管理
│   │
│   ├── services/                       # 業務邏輯層
│   │   ├── rag_engine.py               # RAG 檢索引擎
│   │   ├── intent_classifier.py        # 意圖分類器
│   │   ├── confidence_evaluator.py     # 信心度評估器
│   │   ├── llm_answer_optimizer.py     # LLM 答案優化器
│   │   ├── sop_orchestrator.py         # SOP 編排器
│   │   ├── form_manager.py             # 表單管理器
│   │   ├── intent_suggestion_engine.py # 意圖建議引擎
│   │   ├── vendor_config_service.py    # 業者配置服務
│   │   ├── cache_service.py            # 快取服務
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
│   │   ├── base_retriever.py           # 基礎檢索器
│   │   ├── vendor_knowledge_retriever_v2.py # 業者知識檢索器
│   │   ├── vendor_sop_retriever_v2.py  # 業者 SOP 檢索器
│   │   ├── semantic_reranker.py        # 語義重排序器
│   │   ├── knowledge_classifier.py     # 知識分類器
│   │   ├── knowledge_generator.py      # 知識生成服務
│   │   ├── knowledge_import_service.py # 知識匯入服務
│   │   ├── knowledge_export_service.py # 知識匯出服務
│   │   ├── digression_detector.py      # 離題檢測器
│   │   ├── unclear_question_manager.py # 未釐清問題管理器
│   │   ├── intent_manager.py           # 意圖管理器
│   │   ├── intent_semantic_matcher.py  # 意圖語義匹配器
│   │   ├── keyword_matcher.py          # 關鍵字匹配器
│   │   ├── sop_trigger_handler.py      # SOP 觸發處理器
│   │   ├── sop_keywords_handler.py     # SOP 關鍵字處理器
│   │   ├── sop_next_action_handler.py  # SOP 下一步處理器
│   │   ├── sop_embedding_generator.py  # SOP 嵌入生成器
│   │   ├── form_validator.py           # 表單驗證器
│   │   ├── vendor_parameter_resolver.py # 業者參數解析器
│   │   ├── api_call_handler.py         # API 呼叫處理器
│   │   ├── universal_api_handler.py    # 通用 API 處理器
│   │   ├── billing_api.py              # 計費 API
│   │   ├── document_converter_service.py # 文檔轉換服務
│   │   ├── s3_video_service.py         # S3 視頻服務
│   │   ├── answer_formatter.py         # 答案格式化器
│   │   ├── llm_provider.py             # LLM 提供者
│   │   └── ...
│   │
│   ├── models/                         # 資料模型
│   │   ├── unclear_question.py         # 未釐清問題模型
│   │   └── ...
│   │
│   ├── config/                         # 配置管理
│   │   ├── deduplication_config.py     # 去重配置
│   │   ├── business_types.py           # 業態類型配置
│   │   └── ...
│   │
│   ├── utils/                          # 工具函數
│   │   ├── db_utils.py                 # 資料庫工具
│   │   ├── embedding_utils.py          # 嵌入工具
│   │   ├── sop_utils.py                # SOP 工具
│   │   └── ...
│   │
│   ├── tests/                          # 測試檔案
│   │   ├── test_rag_engine.py
│   │   ├── test_intent_classifier.py
│   │   ├── test_sop_orchestrator.py
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
│   └── ...
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
- **核心引擎**: `{domain}_engine.py` (如 `rag_engine.py`)
- **分類器**: `{domain}_classifier.py` (如 `intent_classifier.py`, `action_type_classifier.py`)
- **管理器**: `{domain}_manager.py` (如 `form_manager.py`, `unclear_question_manager.py`)
- **編排器**: `{domain}_orchestrator.py` (如 `sop_orchestrator.py`)
- **檢索器**: `{domain}_retriever.py` 或 `{domain}_retriever_v2.py`
- **處理器**: `{domain}_handler.py` (如 `api_call_handler.py`, `sop_trigger_handler.py`)
- **評估器**: `{domain}_evaluator.py` (如 `confidence_evaluator.py`)
- **優化器**: `{domain}_optimizer.py` (如 `llm_answer_optimizer.py`)
- **生成器**: `{domain}_generator.py` (如 `knowledge_generator.py`, `sop_embedding_generator.py`)
- **驗證器**: `{domain}_validator.py` (如 `form_validator.py`)
- **解析器**: `{domain}_resolver.py` 或 `{domain}_matcher.py`
- **追蹤器**: `{domain}_tracker.py` (如 `cost_tracker.py`)
- **監控器**: `{domain}_monitor.py` (如 `review_timeout_monitor.py`)
- **工具服務**: `{service_name}_service.py` (如 `cache_service.py`, `vendor_config_service.py`)

### 路由模組 (routers/)
- **資源路由**: `{resource}.py` (如 `chat.py`, `knowledge.py`, `forms.py`)
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
- **單元測試**: `test_{module}.py` (如 `test_rag_engine.py`)
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

### 服務配置
- `RAG_RETRIEVAL_LIMIT`: RAG 檢索限制 (預設 5)
- `PRIORITY_BOOST`: 優先級加成 (預設 0.15)
- `PRIORITY_QUALITY_THRESHOLD`: 優先級品質門檻 (預設 0.70)
- `USE_SEMANTIC_RERANK`: 是否啟用語義重排序 (預設 false)
- `ENABLE_ANSWER_SYNTHESIS`: 是否啟用答案合成 (預設 false)
- `SYNTHESIS_THRESHOLD`: 答案合成閾值 (預設 0.7)

### 回測配置
- `VENDOR_ID`: 業者 ID
- `BACKTEST_BATCH_LIMIT`: 回測批次限制
- `BACKTEST_FILTER_STATUS`: 回測過濾狀態 (如 approved)
- `BACKTEST_ONLY`: 僅執行回測模式 (true/false)

### Redis
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`

### AWS S3
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`

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
