# 過時關鍵字掃描結果

**掃描日期**: 2026-04-22
**掃描範圍**: `docs/`（排除 `docs/archive/`）、`scripts/`（排除 `scripts/archive/`、`scripts/deprecated/`）、`rag-orchestrator/tests/`、`database/`、`.kiro/steering/`
**排除**: `.kiro/specs/`、`docs/archive/`、`scripts/archive/`、`scripts/deprecated/`、二進位檔案、`node_modules`、`dist`、`__pycache__`

## 摘要

| 類別 | 命中數 |
|------|--------|
| steering | 3 |
| docs | 77 |
| scripts | 13 |
| tests | 1 |
| database | 28 |
| **總計** | **122** |

---

## steering（`.kiro/steering/`）

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `.kiro/steering/dialogue.md` | `intent_boost` | 174 | `intent_boost = {` |
| `.kiro/steering/dialogue.md` | `intent_boost` | 180 | `boosted_similarity = base_similarity * intent_boost` |
| `.kiro/steering/tech.md` | `INTENT_CLASSIFIER_MODEL` | 160 | `- GPT-3.5-turbo: 意圖分類（INTENT_CLASSIFIER_MODEL）` |

> 注意：`structure.md` 中 `suggested_intents.py`（行 34）和 `intent_classifier.py`（行 45, 111, 155, 222）屬於檔案結構描述，其中 `intent_classifier` 相關引用屬 **有效**（表單流程仍在使用），`suggested_intents.py` 則需在 Task 2 中移除。

---

## docs（排除 `docs/archive/`）

### `intent_boost` 命中

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/implementation/FINAL_2026-01-13.md` | `intent_boost` | 401 | `END as sql_intent_boost` |
| `docs/implementation/FINAL_2026-01-13.md` | `intent_boost` | 510 | `排序（輔）：boosted_similarity = base * intent_boost` |
| `docs/implementation/DEDUPLICATION_SUMMARY.md` | `intent_boost` | 56 | `2. 计算每条记录的 intent_boost` |
| `docs/analysis/retrieval_logic_complete.md` | `intent_boost` | 128 | `END as sql_intent_boost,` |
| `docs/analysis/retrieval_logic_complete.md` | `intent_boost` | 322 | `# - intent_boost 先用簡單邏輯（精確匹配 1.3，其他 1.0）` |
| `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | `intent_boost` | 458 | `- 使用語義匹配動態計算 intent_boost` |
| `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | `intent_boost` | 487 | `3. SQL 計算 intent_boost（精確匹配 1.3x）` |
| `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | `intent_boost` | 488 | `4. Python 重新計算 intent_boost（語義相似度）` |
| `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | `intent_boost` | 489 | `5. 計算最終相似度 = base_similarity × intent_boost` |
| `docs/analysis/retrieval_philosophy.md` | `intent_boost` | 19 | `# - intent_boost 先用簡單邏輯（精確匹配 1.3，其他 1.0）` |
| `docs/analysis/retrieval_philosophy.md` | `intent_boost` | 122 | `knowledge['intent_boost'] = boost` |
| `docs/features/sop/implementation/VENDOR_SOP_RETRIEVAL_IMPROVEMENT.md` | `intent_boost` | 128 | `END as intent_boost,` |
| `docs/features/sop/implementation/VENDOR_SOP_RETRIEVAL_IMPROVEMENT.md` | `intent_boost` | 188 | `- 添加 intent_boost 計算欄位` |
| `docs/fixes/README.md` | `intent_boost` | 26 | `- 清理無效字段：scope_weight, sql_intent_boost, sql_boosted_sim...` |
| `docs/fixes/README.md` | `intent_boost` | 29 | `- 移除 SQL CASE WHEN intent_boost 計算 (-9 行, -15.5%)` |
| `docs/fixes/README.md` | `intent_boost` | 52 | `- ✅ retrieve_sop_hybrid 保留 intent_boost（不使用 Reranker）` |
| `docs/fixes/INTENT_BOOST_OPTIMIZATION_2026-01-28.md` | `intent_boost` | 多行 | 整份文件圍繞 intent_boost 優化（38, 94, 138, 162, 199, 211, 213, 256, 262, 266, 401, 405） |
| `docs/verification/report_2026-01-13.md` | `intent_boost` | 35 | `- 修改前：使用 boosted_similarity（base_similarity × intent_boost）` |

### `intent_mapping` / `knowledge_intent_mapping` 命中

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/features/MULTI_INTENT_SCORING.md` | `knowledge_intent_mapping` | 7 | `知识库使用 knowledge_intent_mapping 表来实现多对多关系` |
| `docs/features/MULTI_INTENT_SCORING.md` | `knowledge_intent_mapping` | 10, 35, 231, 248 | 多處 CREATE TABLE / LEFT JOIN / INSERT |
| `docs/analysis/retrieval_logic_complete.md` | `knowledge_intent_mapping` | 39 | `└─ LEFT JOIN knowledge_intent_mapping` |
| `docs/analysis/retrieval_logic_complete.md` | `knowledge_intent_mapping` | 139 | `LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id` |
| `docs/architecture/DATABASE_SCHEMA.md` | `knowledge_intent_mapping` | 34, 39, 44, 45, 114, 126, 311, 523, 526, 549, 955, 973, 1083, 1084 | ER 圖、表定義、索引定義 |
| `docs/fixes/2026-01-21-api-integration-fix.md` | `intent_mapping` | 261, 335, 349 | `intent_mappings: Optional[List[IntentMapping]] = []` |
| `docs/fixes/2026-01-21-api-integration-fix.md` | `knowledge_intent_mapping` | 659, 675 | `加入意圖資訊 - 使用 knowledge_intent_mapping` |
| `docs/fixes/2026-01-21-api-integration-analysis.md` | `intent_mapping` | 240, 399 | `intent_mappings: Optional[List[IntentMapping]] = []` |
| `docs/API_ENDPOINTS_COMPLETE_INVENTORY.md` | `/intents` | 35-43 | 列出 9 個 `/api/v1/intents` 端點 |
| `docs/api/API_REFERENCE_KNOWLEDGE_ADMIN.md` | `/intents` | 309, 328, 350, 363, 381, 388 | POST/DELETE/GET `/api/knowledge/{id}/intents` 等 |
| `docs/implementation/AUTH_IMPLEMENTATION_SUMMARY.md` | `/intents` | 395, 396, 399 | `POST /api/knowledge/{id}/intents` 等 |

### `IntentMapping` 命中

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/fixes/2026-01-21-api-integration-fix.md` | `IntentMapping` | 261, 335, 349 | `Optional[List[IntentMapping]]` |
| `docs/fixes/2026-01-21-api-integration-analysis.md` | `IntentMapping` | 240, 399 | `Optional[List[IntentMapping]]` |

### `/intents` 命中（docs，排除 archive）

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/API_ENDPOINTS_COMPLETE_INVENTORY.md` | `/intents` | 35-43 | 9 個 `/api/v1/intents/*` 端點 |
| `docs/api/API_REFERENCE_KNOWLEDGE_ADMIN.md` | `/intents` | 309, 328, 350, 363, 381, 388 | 意圖相關 API 端點文件 |
| `docs/implementation/AUTH_IMPLEMENTATION_SUMMARY.md` | `/intents` | 395, 396, 399 | 意圖 API 端點清單 |
| `docs/architecture/SYSTEM_ARCHITECTURE.md` | `/intents` | 674 | `/api/v1/intents/* - 意圖管理` |
| `docs/features/AUTH_SYSTEM_README.md` | `/intents` | 153 | `/api/intents/* - 意圖管理` |
| `docs/design/PERMISSION_SYSTEM_DESIGN.md` | `/intents` | 586 | `path: '/intents',` |
| `docs/guides/api/api-path-conventions.md` | `/intents` | 43, 44, 159, 160, 165, 329, 330, 333, 334, 337 | 多處 API path 慣例說明 |
| `docs/guides/development/FRONTEND_VERIFY.md` | `/intents` | 28, 230 | `URL 變更為: http://localhost:8080/intents` |
| `docs/guides/development/FRONTEND_USAGE_GUIDE.md` | `/intents` | 16, 17, 101, 128, 171-177 | 意圖管理頁面使用指南 |
| `docs/LLM_PROVIDER_MIXED_CONFIG_GUIDE.md` | `intent_classifier` | 137, 156, 348, 349 | LLM provider 設定（有效引用） |

### `suggested_intents` 命中

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/architecture/SYSTEM_ARCHITECTURE.md` | `suggested_intents` | 143, 551, 591 | 系統架構圖中的 suggested_intents 表 |

### `INTENT_CLASSIFIER_MODEL` 命中

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/guides/deployment/ENVIRONMENT_VARIABLES.md` | `INTENT_CLASSIFIER_MODEL` | 173 | `意圖分類使用的模型 gpt-3.5-turbo` |
| `docs/guides/deployment/ENVIRONMENT_VARIABLES.md` | `INTENT_CLASSIFIER_MODEL` | 186, 545 | `INTENT_CLASSIFIER_MODEL=gpt-3.5-turbo` |
| `docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md` | `INTENT_CLASSIFIER_MODEL` | 921 | `INTENT_CLASSIFIER_MODEL gpt-3.5-turbo 意圖分類模型` |

### `intent_classifier` 命中（docs，排除有效引用）

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/architecture/SYSTEM_ARCHITECTURE.md` | `intent_classifier` | 264, 299 | `intent_classifier.py # 意圖分類服務` |
| `docs/implementation/FINAL_2026-01-13.md` | `intent_classifier` | 95 | `嘗試：在 intent_classifier.py 添加名稱映射` |
| `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | `intent_classifier` | 292, 293 | `intent_classifier = req.app.state.intent_classifier` |
| `docs/analysis/CONVERSATION_LOGIC_COMPREHENSIVE_ANALYSIS_2026-02-04.md` | `intent_classifier` | 111, 146, 268, 429, 573 | 對話邏輯分析中的架構描述 |
| `docs/design/FORM_FILLING_CONFLICT_ANALYSIS.md` | `intent_classifier` | 238, 323, 324, 363, 379, 428, 429 | 表單填充設計中的 intent 引用（有效 — 表單流程） |
| `docs/design/FORM_FILLING_CODE_CHANGES.md` | `intent_classifier` | 34, 51, 214, 215 | 表單填充程式碼變更（有效 — 表單流程） |
| `docs/design/FORM_FILLING_INTEGRATION_PLAN.md` | `intent_classifier` | 18, 124, 144 | 表單填充整合計畫（有效 — 表單流程） |
| `docs/design/FORM_FILLING_DIALOG_DESIGN.md` | `intent_classifier` | 278 | 表單填充對話設計（有效 — 表單流程） |
| `docs/fixes/README.md` | `intent_classifier` | 127 | `修改檔案：intent_classifier.py:211-377` |
| `docs/rag-system/RAG_IMPLEMENTATION_PLAN.md` | `intent_classifier` | 832 | `intent_classifier.py # 意圖分類 (Phase 2)` |
| `docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md` | `intent_classifier` | 909, 953 | 意圖分類器檔案描述 |

### `gpt-3.5-turbo` 命中

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `docs/guides/deployment/ENVIRONMENT_VARIABLES.md` | `gpt-3.5-turbo` | 151, 157, 164, 173, 186, 197, 203, 231, 542, 545, 550 | 環境變數指南中多處提及 gpt-3.5-turbo 作為預設 |
| `docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md` | `gpt-3.5-turbo` | 921 | `INTENT_CLASSIFIER_MODEL gpt-3.5-turbo` |
| `docs/architecture/DATABASE_SCHEMA.md` | `gpt-3.5-turbo` | 712 | `ai_model VARCHAR(50), -- gpt-4, gpt-3.5-turbo` |
| `docs/LLM_PROVIDER_MIXED_CONFIG_GUIDE.md` | `gpt-3.5-turbo` | (未命中) | — |

---

## scripts（排除 `scripts/archive/`、`scripts/deprecated/`）

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `scripts/comprehensive_approval_check.py` | `knowledge_intent_mapping` | 165, 167, 173, 177, 182, 192, 254 | 檢查 knowledge_intent_mapping 表是否存在 |
| `scripts/fix_missing_intents.py` | `intent_mapping` | 108 | `def get_intent_mapping(conn):` |
| `scripts/fix_missing_intents.py` | `knowledge_intent_mapping` | 206, 220, 221, 223, 229 | 更新 knowledge_intent_mapping 表 |
| `scripts/README.md` | `intent_boost` | 183 | `analysis/compare_intent_boost_weights.py - Intent Boost 權重測試` |
| `scripts/kb_system_coverage/test_review_pipeline_compat.py` | `knowledge_intent_mapping` | 719, 724 | `test_approve_function_supports_intent_mapping` |

---

## tests（`rag-orchestrator/tests/`）

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `rag-orchestrator/tests/test_vendor_sop_retriever_fields.py` | `intent_boost` | 140 | `# 不應再有作為主分數別名的 as similarity（intent_boost 不算）` |

---

## database

| 檔案路徑 | 關鍵字 | 行號 | 內容（截取） |
|----------|--------|------|-------------|
| `database/MIGRATIONS_INFO.md` | `knowledge_intent_mapping` | 74 | `knowledge_intent_mapping - 知識-意圖映射` |
| `database/MIGRATIONS_INFO.md` | `suggested_intents` | 86 | `suggested_intents - 建議的意圖` |
| `database/tests/test_business_types_null_filtering.sql` | `knowledge_intent_mapping` | 77, 104, 208 | LEFT JOIN / INNER JOIN knowledge_intent_mapping |
| `database/test_data/fix_test_data_intent_mapping.sql` | `knowledge_intent_mapping` | 52, 57, 63, 69, 75, 97 | DELETE / INSERT INTO knowledge_intent_mapping |
| `database/migrations/fix_remaining_unsafe_fk_constraints.sql` | `knowledge_intent_mapping` | 8, 9, 10, 11 | ALTER TABLE knowledge_intent_mapping FK 修正 |
| `database/migrations/sync_prod_api_forms_knowledge.sql` | `knowledge_intent_mapping` | 116, 119 | INSERT INTO knowledge_intent_mapping |
| `database/migrations/README.md` | `knowledge_intent_mapping` | 290, 291 | 同步線上資料描述 |
| `database/migrations/fix_knowledge_base_intent_fk.sql` | `suggested_intents` | 28, 29, 30, 32, 33 | ALTER TABLE suggested_intents FK 修正 |
| `database/migrations/fix_conversation_logs_drop_fk.sql` | `suggested_intents` | 3 | 註解提及 suggested_intents |
| `database/migrations/fix_all_unsafe_fk_constraints.sql` | `suggested_intents` | 35, 38, 39 | ALTER TABLE suggested_intents FK 修正 |
| `database/migrations/test_006_openai_cost_tracking_table.sql` | `gpt-3.5-turbo` | 140 | `'gpt-3.5-turbo', 500, 100, 0.000350` |
| `database/migrations/006_create_openai_cost_tracking_table.sql` | `gpt-3.5-turbo` | 12, 32 | `model VARCHAR(50) -- gpt-3.5-turbo, gpt-4o-mini` |
| `database/init/12-create-ai-knowledge-system.sql` | `knowledge_intent_mapping` | 219, 222 | INSERT INTO knowledge_intent_mapping |
| `database/init/07-extend-knowledge-base.sql` | `knowledge_intent_mapping` | 140, 143 | 資料遷移 knowledge_intent_mapping |
| `database/init/05-create-knowledge-intent-mapping.sql` | `knowledge_intent_mapping` | 6, 31-45, 49 | CREATE TABLE / INDEX / TRIGGER / COMMENT |
| `database/init/04-create-intent-management-tables.sql` | `suggested_intents` | 51, 52, 90-99, 190 | CREATE TABLE / INDEX / TRIGGER |
| `database/fixes/fix_approve_function.sql` | `knowledge_intent_mapping` | 97, 100, 135 | INSERT INTO knowledge_intent_mapping |
| `database/fixes/fix_approve_function_corrected.sql` | `knowledge_intent_mapping` | 100, 103 | INSERT INTO knowledge_intent_mapping |
| `database/fixes/add_knowledge_classification_tracking.sql` | `意圖分配` | 5 | `相關功能：意圖分配（KnowledgeReclassifyView）` |
| `database/fixes/add_knowledge_generation_columns.sql` | `gpt-3.5-turbo` | 40 | `ai_model VARCHAR(50), -- 使用的模型 (gpt-4, gpt-3.5-turbo)` |

---

## 特殊標記：`intent_classifier` 有效引用（不列為過時）

以下為 **有效引用**，僅供記錄，不需清理：

| 檔案路徑 | 行號 | 說明 |
|----------|------|------|
| `rag-orchestrator/services/intent_classifier.py` | 全檔 | 服務本體，有效 |
| `rag-orchestrator/app.py` | 13, 29, 45, 62, 110, 194 | 初始化與 health check，有效 |
| `rag-orchestrator/routers/chat.py` | 1463, 1464, 3047, 3048, 3146, 3147 | 表單流程引用，有效 |
| `rag-orchestrator/services/knowledge_classifier.py` | 10, 20, 59, 498 | 知識分類器引用，有效 |
| `docs/design/FORM_FILLING_*.md` | 多行 | 表單填充設計文件，有效 |
