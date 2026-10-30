# Structure Steering

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。

## 專案組織

```
AIChatbot/
├── .kiro/                              # Kiro 專案管理
│   ├── steering/                       # 專案記憶與指導
│   │   ├── product.md                  # 產品定位
│   │   ├── tech.md                     # 技術規範
│   │   ├── structure.md                # 專案結構
│   │   ├── knowledge.md                # 知識資料結構
│   │   ├── dialogue.md                 # 對話流程摘要
│   │   ├── ai-usage.md                 # AI 模型與成本
│   │   ├── debugging-workflow.md  testing-code.md
│   │   ├── answer-eval-and-probe.md    # 評估骨架與先探測
│   │   └── plan-touchpoint-checklist.md # 計畫前接點盤查清單
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
│   │   ├── agent.py                    # /api/v1/agent 的 openapi.json／health／trace（/mcp 是 mcp_facade 的 Mount）
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
│   │   │   ├── affirmative.py  bill_period.py  limits.py  text_norm.py  # 回合內輔助判斷
│   │   │   ├── trace_view.py  provenance_units.py                      # 軌跡檢視／引用單元
│   │   │   ├── bootstrap.py  agent_session.py  output_schema.py        # 組裝／會話／輸出結構
│   │   │   ├── write_forms.py  completed_actions.py                    # 寫入表單／已完成動作
│   │   │   ├── image_fetch.py  document_extract.py                     # 附件取得與抽取
│   │   │   ├── canon/                  # 知識路 A：git canon 正本
│   │   │   │   ├── canon_parser.py     canon_assembler.py
│   │   │   │   ├── fine_index.py       candidate_selector.py（K=5 餘弦）
│   │   │   │   └── review_state.py
│   │   │   └── tools/                  # 工具註冊表（registry.call 走 in-process）
│   │   │       ├── registry.py  jgb2.py（六域 16 face）  kb.py（知識路 B）
│   │   │       └── action.py  confirm.py  handoff.py  help.py  session.py  jgb2_stats.py
│   │   │
│   │   ├── jgb/                        # 六域 face builders ＋ jgb2 轉接
│   │   │   ├── bills.py  contracts.py  repairs.py  estates.py  accounts.py  iot.py  invoices.py
│   │   │   ├── fixture_store.py  fixtures.py  point_refund_selection.py
│   │   │   ├── transport.py            # jgb2 API 轉接（替身 15 端點／真 external/v1）
│   │   │   └── *_fixtures.py           # 替身資料（contract/estate/meter/repair/team）
│   │   │
│   │   ├── ocr_mapping/                # OCR 合約映射（clause_splitter／contract_mapper／
│   │   │                               #   deposit_rule／field_normalizer／name_splitter…）
│   │   │
│   │   ├── knowledge_completion_loop/  # ⚠️ 程式只剩 embedding_client.py（另有 __init__.py、create_missing_indexes.sql）——
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
│   │   ├── vendor_parameter_resolver.py # ⚠️ resolve_template 僅檔內自呼叫，檔外（非測試）無呼叫端
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
│   │   ├── business_types.py           # 業態類型配置
│   │   └── agent_verifier_rules.json   # Verifier 的機敏／極性詞表
│   │
│   ├── tests/                          # 測試檔案（unit/integration/e2e 三層，見 testing-code.md）
│   │   ├── unit/agent/                 # /mcp 新線 unit 測試主力
│   │   ├── integration/agent/          # /mcp 新線 integration 驗收
│   │   └── ...
│   │
│   ├── tools/                          # 工具腳本（見上方「命名模式」節）
│   │   ├── agent_eval.py               # 回測（run_turn 的四個非測試呼叫端之一）
│   │   ├── agent_trace.py  agent_outline_dump.py  agent_attempts_report.py
│   │   └── import_facet_knowledge.py  audit_config.py  embed_missing.py
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
│   ├── audit/                          # make audit 的不變量檢查器（checks/ 一支一條）
│   ├── smoke/                          # 真模型 smoke 對照計分尺
│   ├── knowledge-batches/              # 部署重放依賴的知識批次
│   └── deployment/
│
├── docs/                               # 文檔目錄
│   ├── backtest/                       # 回測文檔
│   │   ├── assistant-report-workflow.md
│   │   ├── assistant-report-regression.md
│   │   └── corpus-20260810/
│   └── SOP*.md                         # SOP 文檔
│
├── docker-compose.dev.yml              # Docker Compose 配置 (開發)
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
- **覆蓋率腳本**: `review_coverage.py`、`check_embedding_coverage.py`
- **生成腳本**: `generate_{content}.py`（`generate_test_scenario_embeddings.py`）
- **匯入腳本**: `import_{source}.py`（`rag-orchestrator/tools/import_facet_knowledge.py`）

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
from services.agent.runtime import AgentRuntime

# 工具層（無獨立 utils/ 目錄，檔案在 services/ 下）
from services.db_utils import get_db_connection
from services.embedding_utils import get_embedding_client

# 配置層
from config.business_types import get_all_business_types
```

### 相對匯入
- **避免使用**: 優先使用絕對匯入
- **同級模組**: 可使用相對匯入 (如 `from .base_retriever import BaseRetriever`)

## 資料庫表結構模式

### 核心表

⚠️ **權威 schema 不在 repo 的現行 migrations 內**：下列多數表的 `CREATE TABLE` 只存在於 `database/init-legacy/`、`database/migrations-legacy/`、`database/backups/` 與 `docs/architecture/DATABASE_SCHEMA.md`；`usage_events`／`vendor_quotas` 的 CREATE 在 `rag-orchestrator/database/migrations/`（`add_usage_events.sql`、`add_vendor_quotas.sql`）。repo 內有三個 migration 目錄：`rag-orchestrator/database/migrations/`（現行）、`rag-orchestrator/migrations/`（舊檔，例：`add_loop_features.sql`）、`database/migrations-legacy/`。下方 test_scenarios／backtest_results 的欄位清單未對 DB 實況核過（見 d5-steering-inventory.md）。
- **test_scenarios**: 測試場景管理
  - 欄位: id, vendor_id, test_question, expected_answer, difficulty, source, status, created_at, updated_at
  - 索引: vendor_id, source, status, created_at

- **backtest_results**: 回測結果
  - 欄位: id, vendor_id, scenario_id, run_id, pass, reason, retrieved_docs, answer, created_at
  - 索引: vendor_id, scenario_id, run_id, pass, created_at

- **knowledge_base**: 通用知識庫
  - 欄位（依 `database/init-legacy/02-create-knowledge-base.sql` 與檢索器實際讀取）: id, question_summary, answer, vendor_id, scope, target_user, business_types, keywords, embedding, created_at, updated_at 等；完整欄位見 knowledge.md

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

🔴 **2026-09-12 逐鍵對碼：以下每一顆都有 `rag-orchestrator` 非測試 `.py` 讀者。**
同日刪掉 22 顆 0 命中的（意圖分類／答案合成／信心度／優先級加成／SOP 門檻／回測旗標
等系列，主體隨舊鏈於 2026-09-11 刪除）。⛔ 不留退役標記，要看舊清單請 `git log`。

- `OPENAI_MODEL`: `runtime.py`／`query_rewriter.py` 用（預設 gpt-4o-mini）
- `AGENT_MODEL`／`AGENT_REASONING_EFFORT`: 對話回合的模型與推理強度；程式回退鏈 `AGENT_MODEL`→`OPENAI_MODEL`→`gpt-4o-mini`，採用哪個模型見 `.claude/DECISIONS.md` DSP-075／DSP-080
- `IMAGE_RECOGNITION_MODEL`: 報修照片前處理
- `KNOWLEDGE_GEN_MODEL`: 知識生成（prod compose 預設 gpt-3.5-turbo；程式 fallback 依檔不同：`knowledge_generator.py` gpt-4o-mini，`knowledge_import_service.py`／`document_converter_service.py` gpt-4o）
- `DOCUMENT_CONVERTER_MODEL`: 文件轉換（prod compose 預設 gpt-4o-mini；程式 fallback 鏈 `DOCUMENT_CONVERTER_MODEL`→`KNOWLEDGE_GEN_MODEL`→gpt-4o，見 `services/document_converter_service.py`）
- `QUERY_REWRITE_MODEL`／`QUERY_REWRITE_TEMPERATURE`（**0**，非 0.3）／`QUERY_REWRITE_MAX_TOKENS`
- `EMBEDDING_MODEL`: 預設 text-embedding-3-small（`services/llm_provider.py` 讀；`tools/canon/ruler_eval.py` 只把它記進報告）

### 檢索配置
- `KB_SIMILARITY_THRESHOLD`: 0.65（⛔ 不得改回 0.55，見 `decision_layer.py` docstring）
- `ENABLE_QUERY_REWRITE`（程式 fallback **false**，見 `query_rewriter.py`／`base_retriever.py`；prod compose false，dev compose 未宣告此鍵）／`ENABLE_QUERY_REWRITE_B2B`（程式 fallback **true**，見 `base_retriever.py`；兩份 compose 皆宣告 false）
- `ENABLE_RERANKER` / `RERANKER_INPUT_LIMIT`(20) / `RERANKER_MIN_VECTOR_SIMILARITY`(0.3) / `RERANKER_HTTP_TIMEOUT`(60)

### Agent 線配置
- `AGENT_TURN_ENABLED` / `AGENT_STAGE` / `AGENT_VERIFIER_MODE`
  （⚠️ compose 預設 `enforce`，與某些示範值相反）
- `AGENT_WRITE_TOOLS_ENABLED`: 寫入類工具可見性
- `JGB2_CANDIDATE_CAP`: 候選列表上限
- `USE_MOCK_JGB_API`: true＝走 `services/jgb/transport.py` 的替身 15 端點
- `AGENT_SHADOW_AUDIENCES` / `AGENT_SHADOW_MONTHLY_USD_CAP` / `AGENT_ATTEMPT_LOG_PATH`
- `AGENT_AUDIENCES`: ⚠️ 仍被讀、兩份 compose 仍宣告，但**沒有生效對象**（分流入口不存在）

### Redis
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `CACHE_ENABLED`, `CACHE_TTL_QUESTION`, `CACHE_TTL_VECTOR`, `CACHE_TTL_RAG_RESULT`

### AWS S3
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME`, `CLOUDFRONT_DOMAIN`

### 外部 API
- ⛔ `BILLING_API_BASE_URL`／`BILLING_API_KEY`／`USE_MOCK_BILLING_API`：非測試程式無讀者，視為未使用
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

## 2026-07 現況增補（本節為最新，與上文衝突時以本節與 `docs/architecture/SYSTEM_ARCHITECTURE.md` 為準）

- **對話面向體系（🔴 2026-09-12 逐項對碼更正）**：**16 個 face、六域**
  （帳單 5／合約 5／帳號 2／電表 1／物件 1／修繕 2），在註冊時由
  `_jgb2_spec(domain, sorted(builders.keys()))` **現算**——⛔ 不是「資料驅動、一筆設定＝一個面向」，
  ⛔ 也不是 21＋、⛔ 不是五域。加一個 face 要改 `services/jgb/<域>.py` 的 `*_FACE_BUILDERS`（寫程式）。
  機械判定用 `*_FACE_BUILDERS` 決定性算 facts、LLM 只照 facts 組話（這條仍成立）。
  - **寫入類**改走 `services/agent/tools/action.py` 的兩支（`bill_due_extend`／`repair_create`）
    ＋ `services/agent/confirm_card.py::render` 產確認卡；⛔ 不再有 `grounding_scope.execute_endpoint`
    這種配置驅動（`conversational_engine.py` 已於 2026-09-11 刪除）。
  - **可見性**改為 `AGENT_WRITE_TOOLS_ENABLED` AND `ToolSpec.stage`（DSP-038-1）。
  - **SOP 對話路徑零讀取**：後台 CRUD 仍活，但改 SOP 不影響機器人回答。
  - 擴充判準見 `docs/guides/development/how-to-add-a-query-capability.md`。
- **資料體系分工（定案）**：`vendor_configs`＝通用單值參數（{{param}} 模板）；`lookup_tables`＝案場級（Excel 匯入＋錨點）；SOP＝b2c 專用（b2b 不走）；jgb API＝個資（role_id+user_id 雙證）。
- **計量與額度**：usage_events 每請求計量（token/成本/內部流量標記）；vendor_quotas 月額度（達限攔截/警示寄信）。
- **品質三層**：unit（make test-unit）／系統回測（迴圈＋多輪模擬＋v3 評審＋金標，按受眾分庫）／不變量稽核（make audit，修一類 bug＝加一條）。驗收鐵則：改引擎行為以系統路徑實跑收案。
- **單一真相源**：`docs/architecture/SYSTEM_ARCHITECTURE.md`（全景）；`docs/architecture-overview.md` 現為指路檔；部署走 `docs/deployment-runbook.md`。
