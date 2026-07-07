# 資料庫檔案稽核報告

**日期**: 2026-04-22
**範圍**: `database/migrations/`, `database/fixes/`, `database/init/`, `database/tests/`, `database/test_data/`
**過時關鍵字**: `knowledge_intent_mapping`, `suggested_intents`, `gpt-3.5-turbo`

---

## 1. Migrations 檔案清單

### 1.1 正式遷移 (遷移)

| # | 檔案 | 過時引用 | 狀態 |
|---|------|---------|------|
| 0 | `000_create_schema_migrations.sql` | 無 | 已執行 |
| 1 | `add_intent_embedding.sql` | 無 | 已執行 |
| 2 | `add_admins_table.sql` | 無 | 已執行 |
| 3 | `add_permission_system.sql` | 無 | 已執行 |
| 4 | `create_form_tables.sql` | 無 | 已執行 |
| 5 | `verify_form_tables.sql` | 無 | 已執行 |
| 6 | `add_form_submission_status.sql` | 無 | 已執行 |
| 7 | `add_form_schema_description_fields.sql` | 無 | 已執行 |
| 8 | `add_form_sessions_trigger_fields.sql` | 無 | 已執行 |
| 9 | `add_knowledge_base_missing_columns.sql` | 無 | 已執行 |
| 10 | `rename_chat_history_user_role_to_target_user.sql` | 無 | 已執行 |
| 11 | `remove_form_intro_2026-01-13.sql` | 無 | 已執行 |
| 12 | `add_action_type_and_api_config.sql` | 無 | 已執行 |
| 13 | `configure_billing_inquiry_examples.sql` | 無 | 已執行 |
| 14 | `create_api_endpoints_table.sql` | 無 | 已執行 |
| 15 | `upgrade_api_endpoints_dynamic.sql` | 無 | 已執行 |
| 16 | `remove_handler_function_column.sql` | 無 | 已執行 |
| 17 | `insert_maintenance_sop_examples.sql` | 無 | 已執行 |
| 18 | `add_sop_next_action_fields.sql` | 無 | 已執行 |
| 19 | `add_form_sessions_metadata.sql` | 無 | 已執行 |
| 20 | `add_trigger_mode_to_knowledge_base.sql` | 無 | 已執行 |
| 21 | `add_trigger_keywords_to_knowledge_base.sql` | 無 | 已執行 |
| 22 | `add_followup_prompt_to_knowledge_base.sql` | 無 | 已執行 |
| 23 | `create_lookup_tables.sql` | 無 | 已執行 |
| 24 | `add_lookup_api_endpoint.sql` | 無 | 已執行 |
| 25 | `create_billing_address_form.sql` | 無 | 已執行 |
| 26 | `create_billing_knowledge.sql` | 無 | 已執行 |
| 27 | `add_skip_review_to_form_schemas.sql` | 無 | 已執行 |
| 28 | `add_knowledge_form_auto_option.sql` | 無 | 已執行 |
| 29 | `add_keywords_to_sop_2026-02-11.sql` | 無 | 已執行 |
| 30 | `consolidate_lookup_electricity_data.sql` | 無 | 已執行 |
| 31 | `fix_api_endpoint_kb_sync_trigger.sql` | 無 | 已執行 |
| 32 | `add_vendor_ids_array.sql` | 無 | 已執行 |
| 33 | `add_api_endpoints_related_kb_ids.sql` | 無 | 已執行 |

### 1.2 知識完善迴圈遷移 (001-008 系列)

| # | 檔案 | 過時引用 | 狀態 |
|---|------|---------|------|
| 1 | `001_create_knowledge_completion_loops_table.sql` | 無 | 已執行 |
| 2 | `002_create_knowledge_gap_analysis_table.sql` | 無 | 已執行 |
| 3 | `003_create_loop_generated_knowledge_table.sql` | 無 | 已執行 |
| 3b | `003b_add_gap_analysis_foreign_key.sql` | 無 | 已執行 |
| 4 | `004_extend_knowledge_base_table.sql` | 無 | 已執行 |
| 5 | `005_create_quality_validation_tables.sql` | 無 | 已執行 |
| 6 | `006_create_openai_cost_tracking_table.sql` | `gpt-3.5-turbo`（註解列舉模型名） | 已執行 |
| 7 | `007_create_loop_execution_logs_table.sql` | 無 | 已執行 |
| 8 | `008_create_constraints_and_triggers.sql` | 無 | 已執行 |
| - | `add_loop_features.sql` | 無 | 已執行 |
| - | `rollback_add_loop_features.sql` | 無 | 已執行 |

### 1.3 修復腳本 (fix_*)

| 檔案 | 過時引用 | 狀態 |
|------|---------|------|
| `fix_knowledge_base_fk_on_delete.sql` | 無 | 已執行 |
| `fix_conversation_logs_drop_fk.sql` | `suggested_intents`（註解提及） | 已執行 |
| `fix_knowledge_base_intent_fk.sql` | `suggested_intents`（ALTER TABLE suggested_intents） | 已執行 |
| `fix_all_unsafe_fk_constraints.sql` | `suggested_intents`（ALTER TABLE suggested_intents） | 已執行 |
| `fix_sop_intent_mapping_fk.sql` | 無 | 已執行 |
| `fix_remaining_unsafe_fk_constraints.sql` | `knowledge_intent_mapping`（ALTER TABLE） | 已執行 |
| `fix_backtest_runs_test_type_constraint.sql` | 無 | 已執行 |
| `fix_knowledge_base_loop_fk_on_delete_set_null.sql` | 無 | 已執行 |

### 1.4 同步腳本 (sync_*)

| 檔案 | 過時引用 | 狀態 |
|------|---------|------|
| `sync_prod_api_forms_knowledge.sql` | `knowledge_intent_mapping`（INSERT INTO） | 已執行（線上專用） |
| `sync_prod_sop_data.sql` | 無 | 已執行（線上專用） |

### 1.5 測試腳本 (test_*)

| 檔案 | 過時引用 | 狀態 |
|------|---------|------|
| `test_001_kc_loops_table.sql` | 無 | 測試用 |
| `test_002_gap_analysis_table.sql` | 無 | 測試用 |
| `test_003_loop_generated_knowledge_table.sql` | 無 | 測試用 |
| `test_004_knowledge_base_extension.sql` | 無 | 測試用 |
| `test_005_quality_validation_tables.sql` | 無 | 測試用 |
| `test_006_openai_cost_tracking_table.sql` | `gpt-3.5-turbo`（測試資料插入） | 測試用 |
| `test_007_loop_execution_logs_table.sql` | 無 | 測試用 |
| `test_008_constraints_and_triggers.sql` | 無 | 測試用 |

### 1.6 文件

| 檔案 | 過時引用 | 備註 |
|------|---------|------|
| `README.md` | `knowledge_intent_mapping`（第 290 行描述 sync 腳本內容） | 需更新描述 |

---

## 2. Fixes 檔案清單

| 檔案 | 過時引用 | 狀態 | 理由 |
|------|---------|------|------|
| `fix_approve_function.sql` | `knowledge_intent_mapping`（INSERT INTO，步驟 7） | 可刪除 | 被 `fix_approve_function_corrected.sql` 取代 |
| `fix_approve_function_corrected.sql` | `knowledge_intent_mapping`（INSERT INTO，步驟 7） | 可刪除 | 函數已在 init/12 定義；且引用已廢棄的 `knowledge_intent_mapping` 表 |
| `fix_check_knowledge_function.sql` | 無 | 仍需保留 | 修復 `check_test_scenario_has_knowledge` 函數，移除不存在的 category 欄位 |
| `add_similarity_check_functions.sql` | 無 | 仍需保留 | 知識匯入語意相似度檢查函數 |
| `fix_test_scenario_similarity.sql` | 無 | 仍需保留 | 暫時禁用 test_scenarios 向量相似度（缺 embedding 欄位） |
| `add_test_scenario_embedding_column.sql` | 無 | 仍需保留 | 為 test_scenarios 添加 question_embedding 欄位 |
| `add_knowledge_classification_tracking.sql` | 無（提及「意圖分配」但無過時表名） | 已合併 | 內容已合併至 `init/13-add-knowledge-classification-tracking.sql` |
| `add_knowledge_base_category_column.sql` | 無 | 仍需保留 | 添加 knowledge_base.category 欄位 |
| `add_knowledge_generation_columns.sql` | `gpt-3.5-turbo`（註解列舉模型名） | 已合併 | 內容已合併至 `init/12-create-ai-knowledge-system.sql`（ai_generated_knowledge_candidates 表） |
| `add_test_scenario_answer_fields.sql` | 無 | 仍需保留 | 添加 test_scenarios 的 expected_answer 和 min_quality_score 欄位 |
| `add_vendor_sop_cashflow_columns.sql` | 無 | 仍需保留 | 為 vendor_sop_items 添加金流相關欄位 |
| `add_vendor_sop_groups_group_embedding.sql` | 無 | 仍需保留 | 為 vendor_sop_groups 添加 group_embedding 欄位 |

---

## 3. Init 腳本

| 檔案 | 過時引用 | 備註 |
|------|---------|------|
| `01-enable-pgvector.sql` | 無 | — |
| `02-create-knowledge-base.sql` | 無 | — |
| `03-create-rag-tables.sql` | 無 | — |
| `04-create-intent-management-tables.sql` | `suggested_intents`（CREATE TABLE） | 建立 intents + suggested_intents 表；suggested_intents 已廢棄但 intents 仍在用 |
| `05-create-knowledge-intent-mapping.sql` | `knowledge_intent_mapping`（CREATE TABLE） | 整張表已廢棄（知識改用 category 分類） |
| `06-vendors-and-configs.sql` | 無 | — |
| `07-extend-knowledge-base.sql` | 無（INSERT 用 intent_id 引用 intents 表，非過時） | — |
| `08-remove-templates-use-generic-values.sql` | 無 | — |
| `09-create-test-scenarios.sql` | 無 | — |
| `10-create-configuration-tables.sql` | 無 | — |
| `11-create-sop-system.sql` | 無 | — |
| `12-create-ai-knowledge-system.sql` | 無（ai_model 欄位註解提及模型名但非 knowledge_intent_mapping） | — |
| `13-add-knowledge-classification-tracking.sql` | 無 | — |

---

## 4. 測試資料

| 檔案 | 過時引用 | 備註 |
|------|---------|------|
| `test_data/insert_comprehensive_test_data.sql` | 無 | — |
| `test_data/generate_test_embeddings.py` | 無 | — |
| `test_data/fix_test_data_intent_mapping.sql` | `knowledge_intent_mapping`（DELETE FROM / INSERT INTO） | 測試資料修復腳本，操作已廢棄的 mapping 表 |
| `test_data/fix_sop_complete.sql` | 無 | — |
| `tests/test_business_types_null_filtering.sql` | `knowledge_intent_mapping`（JOIN 查詢，測試 5） | 測試腳本，JOIN 已廢棄的 mapping 表 |

---

## 5. 過時引用摘要

### knowledge_intent_mapping（共 8 處）

此表已在 `abdfc06` commit 中廢棄（知識庫改用類別分類，移除意圖關聯）。

| 檔案 | 引用方式 | 影響程度 |
|------|---------|---------|
| `migrations/fix_remaining_unsafe_fk_constraints.sql` | ALTER TABLE（修改 FK） | 低：已執行的歷史遷移，不影響運行 |
| `migrations/sync_prod_api_forms_knowledge.sql` | INSERT INTO（寫入資料） | 低：一次性同步腳本，已執行 |
| `migrations/README.md` | 文字描述 | 低：文件需更新 |
| `fixes/fix_approve_function.sql` | INSERT INTO（函數內） | 中：函數若重新部署會寫入已廢棄表 |
| `fixes/fix_approve_function_corrected.sql` | INSERT INTO（函數內） | 中：同上 |
| `init/05-create-knowledge-intent-mapping.sql` | CREATE TABLE | 中：新環境初始化會建立已廢棄的表 |
| `test_data/fix_test_data_intent_mapping.sql` | DELETE / INSERT | 低：測試資料腳本 |
| `tests/test_business_types_null_filtering.sql` | LEFT JOIN | 低：測試腳本 |

### suggested_intents（共 3 處）

此表在 `7e77ccb` commit 中功能已移除（移除意圖設定與意圖分配功能）。

| 檔案 | 引用方式 | 影響程度 |
|------|---------|---------|
| `migrations/fix_knowledge_base_intent_fk.sql` | ALTER TABLE（修改 FK） | 低：已執行的歷史遷移 |
| `migrations/fix_conversation_logs_drop_fk.sql` | 註解提及 | 無：僅文字 |
| `migrations/fix_all_unsafe_fk_constraints.sql` | ALTER TABLE（修改 FK） | 低：已執行的歷史遷移 |
| `init/04-create-intent-management-tables.sql` | CREATE TABLE | 中：新環境初始化會建立已廢棄的表 |

### gpt-3.5-turbo（共 3 處）

此模型已不再使用，但引用僅為註解或範例值。

| 檔案 | 引用方式 | 影響程度 |
|------|---------|---------|
| `migrations/006_create_openai_cost_tracking_table.sql` | 註解（列舉模型名） | 無：不影響邏輯 |
| `migrations/test_006_openai_cost_tracking_table.sql` | 測試資料插入 | 無：測試腳本 |
| `fixes/add_knowledge_generation_columns.sql` | 註解（列舉模型名） | 無：不影響邏輯 |

---

## 6. 建議行動

### P0 — 新環境初始化會產生問題

| 行動 | 檔案 | 說明 |
|------|------|------|
| 標記廢棄或移除 | `init/05-create-knowledge-intent-mapping.sql` | 新環境不應再建立此表 |
| 移除 suggested_intents 區塊 | `init/04-create-intent-management-tables.sql` | 保留 intents 表建立，移除 suggested_intents 部分 |

### P1 — 功能腳本引用已廢棄表

| 行動 | 檔案 | 說明 |
|------|------|------|
| 刪除 | `fixes/fix_approve_function.sql` | 已被 corrected 版取代 |
| 更新或刪除 | `fixes/fix_approve_function_corrected.sql` | 移除 knowledge_intent_mapping INSERT 區塊 |
| 刪除 | `fixes/add_knowledge_classification_tracking.sql` | 已合併至 init/13 |
| 刪除 | `fixes/add_knowledge_generation_columns.sql` | 已合併至 init/12 |

### P2 — 測試與文件更新

| 行動 | 檔案 | 說明 |
|------|------|------|
| 更新 | `migrations/README.md` | 移除 knowledge_intent_mapping 相關描述 |
| 更新 | `tests/test_business_types_null_filtering.sql` | 移除測試 5 的 knowledge_intent_mapping JOIN |
| 刪除或標記廢棄 | `test_data/fix_test_data_intent_mapping.sql` | 整個腳本操作已廢棄的 mapping 表 |

### 不需處理 — 已執行的歷史遷移

以下檔案雖引用過時關鍵字，但為已執行的歷史遷移記錄，不應修改或刪除：

- `migrations/fix_remaining_unsafe_fk_constraints.sql`
- `migrations/fix_knowledge_base_intent_fk.sql`
- `migrations/fix_conversation_logs_drop_fk.sql`
- `migrations/fix_all_unsafe_fk_constraints.sql`
- `migrations/sync_prod_api_forms_knowledge.sql`
- `migrations/006_create_openai_cost_tracking_table.sql`
- `migrations/test_006_openai_cost_tracking_table.sql`
