# D5 docs 盤點（2026-10-18，三位唯讀 scout 查證、主會話彙整）

> 範圍：`docs/` 封存區（`docs/archive/`）以外 169 份。三組各自以 Glob 列舉核對數量：紀錄類組 61、guides＋features 47、其餘 61，合計 169。⚠️「判不出」多數是 scout 未逐段核對，**不是確認無誤**。
> 停點觸發：判不出約 69 份 > 計畫 D5 停點 30 份 ⇒ docs 部分處置前先交業主裁（計畫 §4 D5）。

## 一、建議刪除（確定錯且無現行對應；多為只剩一段指向封存副本的殘檔）

| 檔 | 理由（scout 證據） |
|---|---|
| docs/guides/api/how-to-add-api-endpoints.md | 描述動態 API 引擎，`services/api_call_handler.py` 已不存在；本檔只剩指向封存的殘段 |
| docs/guides/api/how-to-add-complete-api.md | 同上 |
| docs/guides/features/SOP_OPTIMIZATION_README.md | SOP 檢索優化，`services/vendor_sop_retriever_v2.py` 已不存在；殘段 |
| docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md | 描述 `routers/chat.py` 對話流程，已整個退役；殘段 |
| docs/features/DUAL_EMBEDDING_RETRIEVAL.md | SOP 檢索器已不存在；殘段 |
| docs/features/KNOWLEDGE_FORM_TRIGGER_IMPLEMENTATION.md | `routers/chat.py` 已不存在；殘段 |
| docs/features/conversational-presales.md | `llm_answer_optimizer.py`、`conversational_engine.py` 已不存在；殘段 |
| docs/features/sop/implementation/SOP_NEXT_ACTION_IMPLEMENTATION.md | 相關程式已不存在；殘段 |
| docs/features/sop/implementation/VENDOR_SOP_FLOW_CONFIGURATION.md | `sop_orchestrator.py` 已不存在；殘段 |

刪除前須 grep 全 repo 有無連到這些路徑的連結，有則一併改指封存副本或移除。

## 二、建議依程式更正

| 檔 | 要改的地方（scout 證據） |
|---|---|
| docs/api/conversational-api.md | 「`/api/v1/message` 改由 AgentRuntime 處理」一段未標退役（端點已刪，現行入口 `/mcp`） |
| docs/api/API_REFERENCE_PHASE1.md | 「通過 /api/v1/message 端點的 stream 參數」未標退役 |
| docs/architecture/SYSTEM_ARCHITECTURE.md | 「只剩 embedding_client.py」：目錄另有 `__init__.py`、`create_missing_indexes.sql` |
| docs/user-guides/knowledge-loop-status.md | 同上一句 |
| docs/architecture-overview.md | face 數 15 → 16；對話鏈段 |
| docs/jgb2-chat-integration.md | `/rag-api/v1/message` 串接規格段 |
| docs/guides/features/LOOKUP_IMPORT_EXPORT_GUIDE.md | 仍寫「表單整合：form_manager.py」（已不存在） |
| docs/guides/features/SOP_EXCEL_IMPORT_GUIDE.md | 自標 `routers/platform_sop.py` 已退役，但該檔仍在（標示與程式不符） |
| docs/guides/reference/LOOKUP_TABLE_QUICK_REFERENCE.md | 正文仍留 `/api/v1/message` 範例 |
| docs/guides/getting-started/QUICKSTART.md | 仍列 `llm_answer_optimizer: ready` |
| docs/guides/features/SOP_GUIDE.md | 開頭稱編排器與觸發器（`sop_orchestrator.py`／`sop_trigger_handler.py`），兩檔已不存在 |
| docs/features/DOCUMENT_CONVERTER.md | 模型預設寫 gpt-4o-mini；`services/document_converter_service.py` 為 `KNOWLEDGE_GEN_MODEL` → gpt-4o |

## 三、現行正確或有日期的紀錄（留）

- 紀錄（有日期，留）：約 67 份——`docs/backtest/` 40 份中 39 份（客服回報逐字與回歸登錄）、`docs/research/` 11 份、`docs/changelog/` 3 份、根目錄稽核與評估報告 5 份、`docs/deployment/records/` 2 份、`docs/maintenance/audit_2026-06-26.md`、`docs/design/agentic-tool-selection-design-20260904.md`、features 下 5 份歷史文件。
- 現行正確：約 15 份——`docs/api/mcp-facade.md`、`jgb2-web-assistant-integration.md`、`loops_api.md`、`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`、`retriever-pipeline.md`、`agent-path-retired-symbols.md`、`docs/design/LOOKUP_TABLE_SYSTEM_DESIGN.md`、`docs/testing/multiturn-smoke-scripts.md`、`LOOKUP_SYSTEM_TEST_GUIDE.md`、`docs/user-guides/VENDOR_SOP_USER_GUIDE.md`、`docs/retrieval-parameters.md`、`docs/guides/deployment/ENVIRONMENT_VARIABLES.md`、`docs/features/FORM_MANAGEMENT_SYSTEM.md`、`docs/features/README.md`、`docs/backtest/corpus-20260810/README.md`、`docs/research/README.md`；`docs/deployment-runbook.md`（他窗未提交，只判定）。

## 四、判不出（約 69 份；scout 未逐段核對）

- docs/api：`loop_knowledge_api.md`、`README.md`、`repair-api-contract.md`、`account-api-contract.md`、`iot-api-contract.md`、`billing-api-contract.md`、`estate-api-contract.md`、`g1-g4-api-contract.md`、`jgb_external_api_spec.md`、`jgb-contracts-api-spec.md`、`KNOWLEDGE_ADMIN_API.md`、`API_REFERENCE_KNOWLEDGE_ADMIN.md`
- docs/architecture：`COMPLETE_CONVERSATION_ARCHITECTURE.md`（有 gpt-4o-mini／gpt-4o 列為現行環境設定）、`BOUNDARY.md`、`DATABASE_SCHEMA.md`、`facet-architecture.md`
- docs/design：`PERMISSION_SYSTEM_DESIGN.md`、`PERMISSION_UI_DESIGN.md`、`API_CONFIGURATION_GUIDE.md`、`CORE_API_FUNCTIONS_REFERENCE.md`、`FORM_FILLING_DIALOG_DESIGN.md`
- docs/deployment：`DEPLOY_CHECKLIST.md`、`DEPLOY_GUIDE.md`、`README.md`
- docs/testing：`api-integration-testing-guide.md`、`BATCH_TEST_STANDARDS.md`
- docs/knowledge：`outline-architecture-proposal.md`、`jgb-domain-map.md`、`agent-readable-knowledge.md`、`jgb-product-facts.md`
- docs/user-guides：`README.md`；docs/frontend：`batch_review_requirements.md`、`loop_management_requirements.md`、`backtest_view_analysis.md`
- docs 根目錄：`README.md`、`INDEX.md`、`chat-architecture-overview.md`、`API_ENDPOINTS_COMPLETE_INVENTORY.md`、`LLM_PROVIDER_MIXED_CONFIG_GUIDE.md`、`KB_EMBEDDING_OPTIMIZATION.md`（結論與程式一致但無日期）
- docs/backtest：`assistant-report-workflow.md`（引 jgb2 外部路徑，本 repo 查不到）
- docs/guides：`reference/SOP_QUICK_REFERENCE.md`、`development/FRONTEND_DEV_MODE.md`、`development/MARKDOWN_TO_PDF_GUIDE.md`、`development/FRONTEND_USAGE_GUIDE.md`、`api/api-path-conventions.md`（`/rag-api/v1/chat` 在 *.py 無命中，可能是 nginx 改寫）、`deployment/AWS_S3_VIDEO_SETUP.md`、`features/PERMISSION_SYSTEM_QUICK_GUIDE.md`、`getting-started/PERMISSION_QUICK_START.md`、`deployment/AUTH_DEPLOYMENT_GUIDE.md`、`migration/TEST_SCENARIOS_MIGRATION_GUIDE.md`、`development/SIMPLIFICATION_IMPLEMENTATION_GUIDE.md`、`deployment/PGVECTOR_SETUP.md`（殘段）、`features/CACHE_SYSTEM_GUIDE.md`、`development/KNOWLEDGE_EXTRACTION_GUIDE.md`、`reference/PRIORITY_QUICK_REFERENCE.md`、`development/how-to-add-a-query-capability.md`、`features/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md`、`README.md`
- docs/features：`PERMISSION_SYSTEM_README.md`、`AUTH_SYSTEM_README.md`、`knowledge-form-auto-option.md`、`knowledge-form-auto-quick-ref.md`、`sop/testing/SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE.md`、`sop/README.md`
- 殘段待裁：`docs/SMART_RETRIEVAL_QUICK_REF.md`（3 行指向封存副本）

## 五、scout 順帶發現

- `services/knowledge_completion_loop/` 除 `embedding_client.py` 外還有 `__init__.py`、`create_missing_indexes.sql`（多份文件寫「只剩 embedding_client.py」略不精確）。
- `docs/deployment/README.md` 引用 `DEPLOY_KNOWLEDGE_COMPLETION_LOOP.md`，存在與否未查。
