# 測試檔案有效性報告

**日期**: 2026-04-22
**範圍**: `rag-orchestrator/tests/`

---

## 狀態說明

| 狀態 | 說明 |
|------|------|
| 可執行 | 無過時引用，功能正常 |
| 需修正 | 部分過時引用，可修正後繼續使用 |
| 可刪除 | 測試已移除的功能，無保留價值 |
| 可歸檔 | 有參考價值但非活躍測試 |

---

## 測試檔案狀態

| 檔案路徑 | 狀態 | 原因 |
|----------|------|------|
| tests/test_answer_synthesis.py | 可執行 | 答案合成測試，無過時引用 |
| tests/test_backtest_similarity_injection.py | 可執行 | 回測 similarity 注入測試，無過時引用 |
| tests/test_base_retriever_pipeline.py | 可執行 | BaseRetriever pipeline 改造測試 |
| tests/test_chat_debug_fields.py | 可執行 | chat debug 欄位測試 |
| tests/test_chat_role_id.py | 可執行 | chat role_id 支援測試 |
| tests/test_chat_shared_has_sop_results.py | 可執行 | has_sop_results 判定測試 |
| tests/test_finalize_scores.py | 可執行 | _finalize_scores 公式測試 |
| tests/test_form_services.py | 可執行 | 表單服務測試 |
| tests/test_intent_manager.py | 可執行 | IntentManager 服務測試；模組 `services/intent_manager.py` 仍存在 |
| tests/test_intent_suggestion.py | 可執行 | IntentSuggestionEngine 測試；模組 `services/intent_suggestion_engine.py` 仍存在 |
| tests/test_jgb_api_integration.py | 可執行 | JGB API handler 路由整合測試 |
| tests/test_jgb_system_api.py | 可執行 | JGB System API mock 模式測試 |
| tests/test_llm_answer_optimizer_perfect_match.py | 可執行 | LLM perfect_match 判定測試 |
| tests/test_llm_answer_optimizer_should_synthesize.py | 可執行 | LLM _should_synthesize 測試 |
| tests/test_loop_knowledge_integration.py | 可執行 | 知識審核 API 整合測試 |
| tests/test_migration_1_1.py | 可執行 | migration 1.1 測試（knowledge_completion_loops 表） |
| tests/test_real_database.py | 需修正 | 呼叫 `retrieve_sop_by_intent(intent_id=...)` — 方法仍存在於 `chat_shared.py` 但使用意圖 ID 參數，需確認是否仍有效 |
| tests/test_retrieval_types.py | 可執行 | RetrievalResult TypedDict 測試 |
| tests/test_sop_modules.py | 可執行 | SOP 四核心模組測試 |
| tests/test_sop_orchestrator.py | 可執行 | SOP Orchestrator 完整流程測試 |
| tests/test_sop_orchestrator_simple.py | 可執行 | SOP Orchestrator 簡化測試 |
| tests/test_synthesis_override.py | 可執行 | 答案合成動態覆蓋測試 |
| tests/test_vendor_knowledge_retriever_fields.py | 可執行 | VendorKnowledgeRetrieverV2 分數欄位測試 |
| tests/test_vendor_sop_retriever_fields.py | 可執行 | VendorSOPRetrieverV2 分數欄位測試；第 140 行 `intent_boost` 僅為註解說明，非功能引用 |
| tests/verify_migration_1_1.py | 可執行 | migration 1.1 驗證腳本（無 pytest 依賴） |

---

## solution_a_validation/ 目錄

| 檔案路徑 | 狀態 | 原因 |
|----------|------|------|
| tests/solution_a_validation/README.md | 可歸檔 | 方案 A 驗證文件，有歷史參考價值 |
| tests/solution_a_validation/INDEX.md | 可歸檔 | 文檔索引 |
| tests/solution_a_validation/TEST_REPORT.md | 可歸檔 | 測試報告 |
| tests/solution_a_validation/IMPLEMENTATION_SUMMARY.md | 可歸檔 | 實作摘要 |
| tests/solution_a_validation/BUGFIX_REPORT.md | 可歸檔 | 修正報告 |
| tests/solution_a_validation/test_1_payment_query.json | 可歸檔 | 測試案例（繳費查詢） |
| tests/solution_a_validation/test_2_application_process.json | 可歸檔 | 測試案例（申請流程） |
| tests/solution_a_validation/test_3_repair_request.json | 可歸檔 | 測試案例（報修請求） |

> **說明**: `solution_a_validation/` 為方案 A（參數注入 + 業種語氣調整）的驗證記錄。內容為靜態文件與 JSON 測試案例，不含可執行程式碼。有歷史參考價值，建議歸檔至 `tests/archive/` 而非刪除。

---

## 統計

| 狀態 | 數量 |
|------|------|
| 可執行 | 24 |
| 需修正 | 1 |
| 可刪除 | 0 |
| 可歸檔 | 8 |
| **總計** | **33** |

---

## 關鍵發現

1. **test_intent_manager.py** 和 **test_intent_suggestion.py** — 對應的服務模組（`services/intent_manager.py`、`services/intent_suggestion_engine.py`）仍存在，測試可執行。若後續移除這些服務，測試需同步移除。

2. **test_vendor_sop_retriever_fields.py 第 140 行** — `intent_boost` 僅出現在註解中（`# 不應再有作為主分數別名的 as similarity（intent_boost 不算）`），不影響測試執行，無需修正。

3. **test_real_database.py** — 使用 `retrieve_sop_by_intent(intent_id=...)` 呼叫，需確認此方法在移除意圖關聯後是否仍正常運作。

4. **solution_a_validation/** — 純文件目錄，有歷史參考價值，建議歸檔而非刪除。
