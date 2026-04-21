# 腳本分類狀態報告

**日期**: 2026-04-22
**範圍**: `scripts/` 目錄（排除 `scripts/archive/`、`scripts/deprecated/`）

---

## 分類說明

| 分類 | 說明 |
|------|------|
| 運維（持續使用） | 部署、回測、embedding 生成等日常運維腳本 |
| 已棄用 | 位於 `scripts/deprecated/` 或 `scripts/archive/` |
| 一次性（可歸檔） | 一次性修正、遷移、分析腳本，任務已完成 |

---

## 一、運維（持續使用）

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/deploy_fix_online.sh | 無 | 線上部署修正 |
| scripts/deployment/deploy-frontend.sh | 無 | 前端部署 |
| scripts/deployment/setup.sh | 無 | 環境設定 |
| scripts/deployment/start_rag_services.sh | 無 | RAG 服務啟動 |
| scripts/deployment/README.md | 無 | 部署文件 |
| scripts/backtest/backtest_framework_async.py | 無 | 回測框架（核心） |
| scripts/backtest/run_backtest_with_db_progress.py | 無 | 回測含 DB 進度追蹤 |
| scripts/backtest/requirements.txt | 無 | 回測依賴 |
| scripts/backtest/README.md | 無 | 回測文件 |
| scripts/regenerate_all_embeddings.py | 無 | 全量 embedding 重生成 |
| scripts/generate_sop_embeddings.py | 無 | SOP embedding 生成 |
| scripts/clear_vendor_cache.py | 無 | 清除業者快取 |
| scripts/check_embedding_coverage.py | 無 | 檢查 embedding 涵蓋率 |

---

## 二、已棄用

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/deprecated/quick_verification.sh | — | 已棄用 |
| scripts/deprecated/run_next_iteration.sh | — | 已棄用 |
| scripts/deprecated/README.md | — | 已棄用說明 |
| scripts/archive/2025-Q4/test_intent_improvements.py | — | 已歸檔 |
| scripts/archive/2025-Q4/test_retrieval_validation.sh | — | 已歸檔 |
| scripts/archive/2025-Q4/verify_classification_tracking.py | — | 已歸檔 |
| scripts/archive/2025-Q4/verify_intent_threshold.sh | — | 已歸檔 |
| scripts/archive/2025-Q4/verify_similarity_functions.py | — | 已歸檔 |
| scripts/archive/2025-Q4/README.md | — | 已歸檔說明 |

---

## 三、一次性（可歸檔）

### 含過時模組引用（優先處理）

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/comprehensive_approval_check.py | `knowledge_intent_mapping` 表檢查 | 一次性審核檢查，引用已移除的表 |
| scripts/fix_missing_intents.py | `intent_mapping`、`knowledge_intent_mapping` | 一次性修正，操作已移除的表 |
| scripts/README.md | 提及 `intent_boost`、`test_intent_manager.py` | 文件內容過時，需更新或歸檔 |
| scripts/kb_system_coverage/test_review_pipeline_compat.py | `knowledge_intent_mapping` | 測試 assert 引用已移除的表 |
| scripts/knowledge_extraction/reclassify_knowledge_intents.py | 意圖重分類邏輯 | 意圖關聯已移除，此腳本失效 |

### 一般一次性腳本

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/generate_intent_embeddings.py | 無（模組仍存在） | 意圖 embedding 生成，功能可能仍需要 |
| scripts/generate_group_embeddings.py | 無 | Group embedding 生成，一次性 |
| scripts/generate_test_scenario_embeddings.py | 無 | 測試情境 embedding，一次性 |
| scripts/migrate_vendor_params.py | 無 | 業者參數遷移（2025-10 已完成） |
| scripts/process_line_chats.py | 無 | LINE 對話處理，一次性分析 |
| scripts/regenerate_kb_embeddings_background.sh | 無 | 背景 embedding 重生成，一次性 |
| scripts/cleanup_docs.sh | 無 | 2026-01-13 文檔清理（已執行） |
| scripts/organize_root.sh | 無 | 根目錄整理（已執行） |
| scripts/MIGRATION_REPORT.md | 無 | 遷移報告（2025-10-31） |

### kb_coverage/ 整個目錄（可歸檔）

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/kb_coverage/__init__.py | 無 | 套件初始化 |
| scripts/kb_coverage/analyze_gaps.py | 無 | KB 缺口分析 |
| scripts/kb_coverage/api_interpretation_checklist.json | 無 | API 解讀清單 |
| scripts/kb_coverage/api_interpretation_entries.json | 無 | API 解讀條目 |
| scripts/kb_coverage/apply_deactivations.py | 無 | 停用知識 |
| scripts/kb_coverage/boundary_classifier.py | 無 | 邊界分類器 |
| scripts/kb_coverage/boundary_definition.md | 無 | 邊界定義文件 |
| scripts/kb_coverage/generate_checklist.py | 無 | 產生清單 |
| scripts/kb_coverage/generate_kb_batch.py | 無 | 批次產生知識 |
| scripts/kb_coverage/insert_api_knowledge.py | 無 | 插入 API 知識 |

### kb_system_coverage/ 整個目錄（可歸檔）

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/kb_system_coverage/__init__.py | 無 | 套件初始化 |
| scripts/kb_system_coverage/api_kb_builder.py | 無 | API KB 建構器 |
| scripts/kb_system_coverage/backtest_analyzer.py | 無 | 回測分析 |
| scripts/kb_system_coverage/backtest_scenarios.py | 無 | 回測情境 |
| scripts/kb_system_coverage/coverage_analyzer.py | 無 | 覆蓋率分析 |
| scripts/kb_system_coverage/jgb_module_inventory.json | 無 | JGB 模組清單 |
| scripts/kb_system_coverage/models.py | 無 | 資料模型 |
| scripts/kb_system_coverage/module_mapper.py | 無 | 模組對應 |
| scripts/kb_system_coverage/orchestrator.py | 無 | 編排器 |
| scripts/kb_system_coverage/question_generator.py | 無 | 問題生成 |
| scripts/kb_system_coverage/system_kb_generator.py | 無 | 系統 KB 生成 |
| scripts/kb_system_coverage/test_api_kb_builder.py | 無 | 測試 |
| scripts/kb_system_coverage/test_backtest_analyzer.py | 無 | 測試 |
| scripts/kb_system_coverage/test_coverage_analyzer.py | 無 | 測試 |
| scripts/kb_system_coverage/test_e2e_api_flow.py | 無 | 測試 |
| scripts/kb_system_coverage/test_orchestrator.py | 無 | 測試 |
| scripts/kb_system_coverage/test_review_pipeline_compat.py | `knowledge_intent_mapping` | 見上方過時引用區 |
| scripts/kb_system_coverage/test_system_kb_generator.py | 無 | 測試 |

### sop_coverage/ 整個目錄（可歸檔）

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/sop_coverage/build_checklist.py | 無 | 建立清單 |
| scripts/sop_coverage/coverage_utils.py | 無 | 覆蓋率工具 |
| scripts/sop_coverage/enrich_keywords.py | 無 | 關鍵字充實 |
| scripts/sop_coverage/llm_answer_evaluator.py | 無 | LLM 答案評估 |
| scripts/sop_coverage/orchestrator.py | 無 | 編排器 |
| scripts/sop_coverage/process_checklist.json | 無 | 流程清單 |

### knowledge_extraction/ 整個目錄（可歸檔）

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/knowledge_extraction/create_test_scenarios.py | 無 | 建立測試情境 |
| scripts/knowledge_extraction/extract_knowledge_and_tests.py | 無 | 知識萃取 |
| scripts/knowledge_extraction/extract_knowledge_and_tests_optimized.py | 無 | 知識萃取（優化版） |
| scripts/knowledge_extraction/import_excel_to_kb.py | 無 | Excel 匯入 KB |
| scripts/knowledge_extraction/import_extracted_to_db.py | 無 | 匯入萃取結果到 DB |
| scripts/knowledge_extraction/monitor_and_autorun.sh | 無 | 監控自動執行 |
| scripts/knowledge_extraction/reclassify_knowledge_intents.py | 意圖分類邏輯 | 見上方過時引用區 |

### testing/ 整個目錄（可歸檔）

| 檔案路徑 | 過時引用 | 備註 |
|----------|----------|------|
| scripts/testing/cleanup_test_data.sql | 無 | 清理測試資料 |
| scripts/testing/prepare_sop_test_data_corrected.sql | 無 | 準備 SOP 測試資料 |
| scripts/testing/run_3000_verification.sh | 無 | 3000 題驗證 |
| scripts/testing/run_500_verification.sh | 無 | 500 題驗證 |
| scripts/testing/run_50_verification.sh | 無 | 50 題驗證 |
| scripts/testing/test_verification_queries.sql | 無 | 驗證查詢 |
| scripts/testing/verify_test_data.sql | 無 | 驗證測試資料 |

---

## 統計

| 分類 | 數量 |
|------|------|
| 運維（持續使用） | 13 |
| 已棄用 | 9 |
| 一次性（可歸檔） | 50 |
| **其中含過時引用** | **5** |
| **總計** | **72** |

---

## 建議行動

1. **立即歸檔**: 將含過時引用的 5 個腳本移至 `scripts/archive/`
2. **批次歸檔**: `kb_coverage/`、`kb_system_coverage/`、`sop_coverage/`、`knowledge_extraction/`、`testing/` 五個目錄整體移至 `scripts/archive/`
3. **更新文件**: `scripts/README.md` 需移除過時的 `intent_boost` 引用
