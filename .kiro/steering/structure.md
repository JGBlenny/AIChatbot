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
│   ├── routers/                        # API 路由層（全部在 app.py include_router）
│   │   ├── agent.py                    # /mcp 門面掛載（prefix 在 router 內）
│   │   ├── agent_entry.py              # ⚠️ strangler 遷移橋：新架構為遷移寫的，
│   │   │                               #   上游（chat.py 的 VendorChatRequest 等 5 個符號）
│   │   │                               #   已隨舊鏈刪除 ⇒ 檔在、無 APIRouter、⛔ 掛不起來
│   │   ├── vendors.py                  # 業者管理
│   │   ├── platform_sop.py             # 平台管理員的 SOP 範本後台 CRUD（15 條路由）
│   │   ├── knowledge_generation.py     # 知識生成
│   │   ├── knowledge_import.py         # 知識匯入
│   │   ├── knowledge_export.py         # 知識匯出
│   │   ├── forms.py                    # 表單後台 CRUD（對話填單引擎已退役）
│   │   ├── unclear_questions.py        # 未釐清問題
│   │   ├── loops.py                    # 知識完善迴圈（後台管理面）
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
│   │   └── system_health.py            # 系統健康檢查
│   │
│   ├── services/                       # 業務邏輯層
│   │   ├── agent/                      # ⭐ 現役核心（30 檔＋2 子套件）
│   │   │   ├── runtime.py              # AgentRuntime.run_turn——一整回合；
│   │   │   │                           #   建構依賴裡⛔ 沒有任何協定或門面
│   │   │   ├── turn_segments.py        # 段一：程式段（六條終止路徑）
│   │   │   ├── turn_context.py         # 段二：九段注入（user_message 永遠最後）
│   │   │   ├── exit_gates.py           # 段四：四道出口閘，順序即契約
│   │   │   ├── verifier.py             # Output Verifier（逐句驗引用，9 步）
│   │   │   ├── mcp_facade.py           # /mcp 門面（13 步進場契約＋三件門面專屬工作）
│   │   │   ├── agent_rules.py          # 對話規則（按受眾分支）
│   │   │   ├── identity.py             # X-JGB-Identity 解析、audience_of
│   │   │   ├── session_persistence.py  # 會話狀態層（借用 form_sessions 表）
│   │   │   ├── state_store.py          # 回合狀態存取點
│   │   │   ├── outline.py              # 受眾大綱組裝
│   │   │   ├── prompt_assembler.py     # 提示組裝
│   │   │   ├── budget.py               # 回合預算
│   │   │   ├── confirm_card.py         # 確認卡（程式決定性產卡文字）
│   │   │   ├── question_sensitivity.py # 問句機敏分類
│   │   │   ├── shadow.py               # 影子跑動
│   │   │   ├── health.py               # 健康檢查（verifier_mode 唯一讀值點）
│   │   │   ├── canon/                  # 知識路 A：git canon 正本
│   │   │   │   ├── canon_parser.py     canon_assembler.py
│   │   │   │   ├── fine_index.py       candidate_selector.py（K=5 餘弦）
│   │   │   │   └── review_state.py
│   │   │   └── tools/                  # 工具註冊表（registry.call 走 in-process）
│   │   │       ├── registry.py  jgb2.py（六域 15 face）  kb.py（知識路 B）
│   │   │       └── action.py  confirm.py  handoff.py  help.py  session.py
│   │   │
│   │   ├── jgb/                        # 六域 face builders ＋ jgb2 轉接
│   │   │   ├── bills.py  contracts.py  repairs.py  estates.py  accounts.py  iot.py
│   │   │   ├── transport.py            # jgb2 API 轉接（替身 15 端點／真 external/v1）
│   │   │   └── *_fixtures.py           # 替身資料（contract/estate/meter/repair/team）
│   │   │
│   │   ├── ocr_mapping/                # OCR 合約映射（clause_splitter／contract_mapper／
│   │   │                               #   deposit_rule／field_normalizer／name_splitter…）
│   │   │
│   │   ├── knowledge_completion_loop/  # ⚠️ 只剩 embedding_client.py——
│   │   │                               #   協調器／缺口分析／生成器等執行面已刪，
│   │   │                               #   後台頁面與資料表仍在，零執行器
│   │   │
│   │   ├── decision_layer.py           # 檢索門檻（kb_threshold 讀 KB_SIMILARITY_THRESHOLD）
│   │   ├── base_retriever.py           # 基礎檢索器（_apply_keyword_boost 每詞 +0.1、上限 +0.3）
│   │   ├── vendor_knowledge_retriever_v2.py # 三軸過濾（build_visibility_predicate 單一來源）
│   │   ├── semantic_reranker.py        # 語義重排序（⚠️ 會靜默永久停用，三處都看不出來）
│   │   ├── form_contract.py            # 表單契約常數（⛔ 值一個都不准改）
│   │   ├── conversational_config.py    # 對話式設定讀取
│   │   ├── presales_gate.py            # 售前 grounding 閘門（HandoffReason 值域）
│   │   ├── grounding_presentation.py   # grounding 呈現
│   │   ├── retrieval_representation.py # representation 契約（general／instance 兩把尺）
│   │   ├── retrieval_types.py          # 檢索型別
│   │   ├── responsibility_*.py         # 責任分攤系列（artifacts／completion／session／
│   │   │                               #   entity_resolution／bill_resolution）
│   │   ├── usage_metering.py           # 額度計量（門面是 usage_events 唯一寫入者）
│   │   ├── api_key_auth.py             # API key 驗證
│   │   ├── instance_applicability.py   # 面向實例可適用性
│   │   ├── fulfillment_registry.py     # 履行動作登記
│   │   ├── cache_service.py            # 三層快取（⚠️ 不在對話回合路徑上）
│   │   ├── knowledge_generator.py      # 知識生成服務
│   │   ├── knowledge_import_service.py knowledge_export_service.py
│   │   ├── unclear_question_manager.py
│   │   ├── sop_embedding_generator.py  sop_utils.py  # SOP 資料維護（對話路徑零讀取）
│   │   ├── vendor_parameter_resolver.py # ⚠️ resolve_template 零呼叫端
│   │   ├── document_converter_service.py image_recognition_service.py
│   │   ├── s3_image_service.py         s3_video_service.py
│   │   ├── llm_provider.py             # LLM 提供者（{SERVICE}_PROVIDER 只有 query_rewriter 用）
│   │   ├── query_rewriter.py           embedding_utils.py  category_utils.py
│   │   ├── db_utils.py                 pipeline_health_service.py  unified_job_service.py
│   │   └── jgb_system_api.py           # JGB 系統 API（_validate_identity 雙證）
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

⚠️ **範例一律取自現存檔**（2026-09-12 對碼）。舊鏈退役後有幾種後綴已無存活範例，
⛔ 不再列出——需要新後綴時比照本表形態命名即可。

- **檢索器**: `{domain}_retriever.py` / `_v2.py`（`vendor_knowledge_retriever_v2.py`、`base_retriever.py`）
- **管理器**: `{domain}_manager.py`（`unclear_question_manager.py`）
- **生成器**: `{domain}_generator.py`（`knowledge_generator.py`、`sop_embedding_generator.py`）
- **解析器**: `{domain}_resolver.py` / `{domain}_parser.py`（`vendor_parameter_resolver.py`、`agent/canon/canon_parser.py`）
- **組裝器**: `{domain}_assembler.py`（`agent/prompt_assembler.py`、`agent/canon/canon_assembler.py`）
- **選取器**: `{domain}_selector.py`（`agent/canon/candidate_selector.py`）
- **重排器**: `{domain}_reranker.py`（`semantic_reranker.py`）
- **工具服務**: `{service_name}_service.py`（`cache_service.py`、`pipeline_health_service.py`、`unified_job_service.py`）
- **契約常數**: `{domain}_contract.py`（`form_contract.py`——⛔ 純常數、不含邏輯）
- **閘門**: `{domain}_gate.py` / `{domain}_gates.py`（`presales_gate.py`、`agent/exit_gates.py`）

### 路由模組 (routers/)
- **資源路由**: `{resource}.py`（`forms.py`、`vendors.py`、`lookup.py`）
- **操作路由**: `{resource}_{operation}.py`（`knowledge_import.py`、`knowledge_export.py`、`knowledge_generation.py`）

### 配置模組 (config/)
- **靜態資料**: `{domain}.py`（`business_types.py`）

### 工具腳本 (rag-orchestrator/tools/)
- **傾印／報表**: `{subject}_dump.py` / `{subject}_report.py`（`agent_outline_dump.py`、`agent_attempts_report.py`）
- **回測**: `agent_eval.py`（`AgentRuntime.run_turn` 的四個非測試呼叫端之一）
- **匯入**: `import_{source}.py`（`import_facet_knowledge.py`）

### 測試檔案 (tests/)
- **單元測試**: `test_{module}_req.py`（`_req` 對應追溯標記，見 `.kiro/steering/testing-code.md`；
  如 `tests/unit/security/test_api_key_auth_req.py`）
- **整合測試**: `test_{module}_integration.py`
- **端到端測試**: `test_e2e_{scenario}.py`

### 腳本檔案 (scripts/, /tmp/)
- **遷移腳本**: `migrate_{description}.py`
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
