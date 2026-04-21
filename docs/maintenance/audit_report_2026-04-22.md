# 系統文件與腳本盤點行動清單

**日期**: 2026-04-22
**掃描基準**: 意圖系統移除（`7e77ccb`）、類別系統導入（`abdfc06`）
**方法**: 過時關鍵字批次掃描 + 人工判定

---

## P0（立即處理）— Steering 文件同步 + 活躍文件中引用已移除功能

### ✅ 已完成：Steering 文件修正

| 檔案 | 動作 | 修正內容 |
|------|------|---------|
| `.kiro/steering/structure.md` | 編輯 ✅ | 移除 `intents.py`、`suggested_intents.py`、`intent_suggestion_engine.py`；新增 `CategoryConfigView.vue` |
| `.kiro/steering/product.md` | 編輯 ✅ | 「意圖分類」→「類別分類」；「意圖」→「類別」 |
| `.kiro/steering/tech.md` | 編輯 ✅ | 更新模型描述：GPT-3.5-turbo → 表單流程意圖分類、查詢改寫 |
| `.kiro/steering/dialogue.md` | 編輯 ✅ | 移除 intent_boost 加成策略段落；更新模型選擇描述 |

### ✅ 已完成：程式碼修正

| 檔案 | 動作 | 修正內容 |
|------|------|---------|
| `rag-orchestrator/services/llm_answer_optimizer.py` | 編輯 ✅ | 預設模型從 `gpt-3.5-turbo` → `gpt-4o-mini` |

### ✅ 已完成：活躍文件過時引用

| 檔案 | 動作 | 修正內容 |
|------|------|---------|
| `docs/architecture/SYSTEM_ARCHITECTURE.md` | 編輯 ✅ | 移除 intents.py router、suggested_intents 表、/intents API、前端意圖頁面 |
| `docs/architecture/DATABASE_SCHEMA.md` | 編輯 ✅ | 移除 knowledge_intent_mapping 表定義、更新 gpt-3.5-turbo → gpt-4o-mini |
| `docs/API_ENDPOINTS_COMPLETE_INVENTORY.md` | 編輯 ✅ | 移除 9 個 /api/v1/intents 端點 |
| `docs/api/API_REFERENCE_KNOWLEDGE_ADMIN.md` | 編輯 ✅ | 移除「意圖管理 API」章節 |
| `docs/guides/deployment/ENVIRONMENT_VARIABLES.md` | 編輯 ✅ | 更新 INTENT_CLASSIFIER_MODEL（僅表單流程）、KNOWLEDGE_GEN_MODEL → gpt-4o-mini |
| `docs/guides/development/FRONTEND_USAGE_GUIDE.md` | 編輯 ✅ | 移除「意圖管理頁面」章節 |
| `docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md` | 編輯 ✅ | 更新 INTENT_CLASSIFIER_MODEL 描述 |
| `database/init/05-create-knowledge-intent-mapping.sql` | 標記廢棄 ✅ | 加入 DEPRECATED 註解 |
| `database/init/04-create-intent-management-tables.sql` | 編輯 ✅ | 移除 suggested_intents CREATE TABLE 區塊 |

**P0 全部完成**: 14/14 ✅

---

## P1（短期）— 過時文件歸檔 + 失效腳本處理 + 測試修正

### 過時文件歸檔（→ `docs/archive/2026-04/`）

| 檔案 | 原因 |
|------|------|
| `docs/implementation/FINAL_2026-01-13.md` | 核心內容為 intent_boost 過濾邏輯 |
| `docs/implementation/DEDUPLICATION_SUMMARY.md` | 核心內容為多意圖知識去重 |
| `docs/analysis/retrieval_logic_complete.md` | 「意圖加成機制」專章 |
| `docs/analysis/retrieval_philosophy.md` | 「意圖應該是加分」哲學討論 |
| `docs/features/sop/implementation/VENDOR_SOP_RETRIEVAL_IMPROVEMENT.md` | intent_boost SQL 改動 |
| `docs/fixes/INTENT_BOOST_OPTIMIZATION_2026-01-28.md` | 整份文件圍繞 intent_boost |
| `docs/verification/report_2026-01-13.md` | 驗證 intent_boost 修改 |
| `docs/features/MULTI_INTENT_SCORING.md` | knowledge_intent_mapping 表與 intent_boost 評分 |
| `docs/guides/development/FRONTEND_VERIFY.md` | 意圖管理頁面驗證（頁面已移除） |

### 過時腳本歸檔（→ `scripts/archive/`）

| 檔案 | 過時引用 |
|------|---------|
| `scripts/comprehensive_approval_check.py` | knowledge_intent_mapping 表 |
| `scripts/fix_missing_intents.py` | intent_mapping、knowledge_intent_mapping |
| `scripts/knowledge_extraction/reclassify_knowledge_intents.py` | 意圖重分類邏輯 |

### DB Fixes 清理

| 檔案 | 動作 | 原因 |
|------|------|------|
| `database/fixes/fix_approve_function.sql` | 刪除 | 被 corrected 版取代 |
| `database/fixes/fix_approve_function_corrected.sql` | 更新 | 移除 knowledge_intent_mapping INSERT |
| `database/fixes/add_knowledge_classification_tracking.sql` | 刪除 | 已合併至 init/13 |
| `database/fixes/add_knowledge_generation_columns.sql` | 刪除 | 已合併至 init/12 |

### 待更新 Docs（次要引用）

| 檔案 | 動作 |
|------|------|
| `docs/analysis/CHAT_FLOW_ANALYSIS_2026-01-24.md` | 移除 intent_boost 段落 |
| `docs/analysis/CONVERSATION_LOGIC_COMPREHENSIVE_ANALYSIS_2026-02-04.md` | 更新架構描述 |
| `docs/fixes/README.md` | 標記 intent_boost 條目為過時 |
| `docs/fixes/2026-01-21-api-integration-fix.md` | 標注 IntentMapping 段落 |
| `docs/fixes/2026-01-21-api-integration-analysis.md` | 標注 IntentMapping 段落 |
| `docs/implementation/AUTH_IMPLEMENTATION_SUMMARY.md` | 移除 intent API 端點 |
| `docs/features/AUTH_SYSTEM_README.md` | 移除 /intents 路徑 |
| `docs/design/PERMISSION_SYSTEM_DESIGN.md` | 移除 intent 權限定義 |
| `docs/guides/api/api-path-conventions.md` | 移除 /intents 路徑規範 |
| `docs/guides/getting-started/USER_MANUAL_NON_TECHNICAL.md` | 移除 INTENT_CLASSIFIER_MODEL 描述 |
| `docs/rag-system/RAG_IMPLEMENTATION_PLAN.md` | 更新意圖模組描述 |

### 測試修正

| 檔案 | 動作 | 原因 |
|------|------|------|
| `rag-orchestrator/tests/test_real_database.py` | 確認 | `retrieve_sop_by_intent(intent_id=...)` 是否仍有效 |

**P1 影響範圍**: 9 個歸檔 docs + 3 個歸檔 scripts + 4 個 DB fixes + 11 個待更新 docs + 1 個測試 = 28 個檔案

---

## P2（可延後）— Archive 整理 + 冗餘文件清理 + 遷移記錄

### 腳本目錄整體歸檔

| 目錄 | 檔案數 | 說明 |
|------|--------|------|
| `scripts/kb_coverage/` | 10 | KB 缺口分析（一次性） |
| `scripts/kb_system_coverage/` | 17 | 系統 KB 覆蓋率（一次性） |
| `scripts/sop_coverage/` | 6 | SOP 覆蓋率（一次性） |
| `scripts/knowledge_extraction/` | 7 | 知識萃取（一次性） |
| `scripts/testing/` | 7 | 驗證腳本（一次性） |

### 測試歸檔

| 目錄 | 檔案數 | 說明 |
|------|--------|------|
| `rag-orchestrator/tests/solution_a_validation/` | 8 | 方案 A 驗證記錄（靜態文件） |

### DB 文件與測試資料更新

| 檔案 | 動作 | 原因 |
|------|------|------|
| `database/migrations/README.md` | 編輯 | 移除 knowledge_intent_mapping 描述 |
| `database/tests/test_business_types_null_filtering.sql` | 編輯 | 移除 knowledge_intent_mapping JOIN |
| `database/test_data/fix_test_data_intent_mapping.sql` | 刪除 | 操作已廢棄的 mapping 表 |
| `scripts/README.md` | 編輯 | 移除過時的 intent_boost 引用 |
| `scripts/kb_system_coverage/test_review_pipeline_compat.py` | 歸檔 | knowledge_intent_mapping assert |

### 已執行歷史遷移（不需處理）

以下遷移雖引用過時關鍵字，但為已執行的歷史記錄，不應修改：
- `migrations/fix_remaining_unsafe_fk_constraints.sql`
- `migrations/fix_knowledge_base_intent_fk.sql`
- `migrations/fix_conversation_logs_drop_fk.sql`
- `migrations/fix_all_unsafe_fk_constraints.sql`
- `migrations/sync_prod_api_forms_knowledge.sql`
- `migrations/006_create_openai_cost_tracking_table.sql`

**P2 影響範圍**: 47 個腳本歸檔 + 8 個測試歸檔 + 5 個文件更新 = 60 個檔案

---

## 統計

### 掃描結果

| 類別 | 總掃描 | 命中 | 命中率 |
|------|--------|------|--------|
| steering | 8 | 3 | 37.5% |
| docs（非 archive） | ~220 | 23 | ~10% |
| scripts（非 archive/deprecated） | ~72 | 5 | ~7% |
| tests | ~33 | 1 | ~3% |
| database | ~108 | 14 | ~13% |
| **總計** | **~441** | **46** | **~10%** |

### 行動分類

| 優先級 | 檔案數 | 已完成 |
|--------|--------|--------|
| P0（立即處理） | 14 | 14/14 ✅ |
| P1（短期） | 28 | 28/28 ✅ |
| P2（可延後） | 60 | 60/60 ✅ |
| **總計** | **102** | **102/102 ✅** |

### 檔案狀態分布

| 狀態 | 數量 |
|------|------|
| 有效（無過時引用） | ~395 |
| 過時（需歸檔/刪除） | 16 |
| 待更新（部分過時引用） | 25 |
| 已棄用（在 archive/deprecated） | ~188 |
| 運維腳本（持續使用） | 13 |

---

## 詳細子報告

| 報告 | 路徑 |
|------|------|
| 掃描原始結果 | `docs/maintenance/scan_results_2026-04-22.md` |
| 文件狀態分類 | `docs/maintenance/docs_status_2026-04-22.md` |
| 腳本分類 | `docs/maintenance/scripts_status_2026-04-22.md` |
| 測試狀態 | `docs/maintenance/tests_status_2026-04-22.md` |
| 資料庫稽核 | `docs/maintenance/database_status_2026-04-22.md` |

---

> 本報告基於過時關鍵字掃描產出，可能遺漏未使用關鍵字搜尋發現的過時內容。建議搭配人工抽查確認完整性。
