# Implementation Plan

- [ ] 1. Foundation：流程清單與工具函數
- [ ] 1.1 建立 process_checklist.json（13 大類 ~72 子題）
  - 依需求 1.1 的 13 大類建立完整清單結構
  - 每個子題包含：topic_id、question（租客問題）、business_type、keywords、cashflow_relevant、priority
  - 參考 `data/20250305 租管業 SOP_1 客戶常見QA.xlsx` 和 `data/20250305 租管業 SOP_2 管理模式 基礎-改.xlsx` 確保涵蓋實務常見問題
  - 每個子題標註適用業態（sublease / management / both）
  - 完成後 JSON 可被 Python json.load() 成功解析，且子題數量 >= 60
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 1.2 建立 coverage_utils.py（停用、建分類、格式轉換）
  - 實作 `deactivate_existing_sops(db_pool, vendor_id, exclude_ids)` — 批量停用現有 SOP（is_active=false），回傳停用清單與統計
  - 實作 `create_categories_from_checklist(db_pool, vendor_id, checklist)` — 批量建立 13 大類 category（已存在則跳過），回傳 category_name → category_id 映射
  - 實作 `checklist_to_gaps(checklist, category_map, exclude_topic_ids)` — 將子題轉為 SOPGenerator 接受的 gaps 格式，包含 category_id 直接指定
  - 包含 DB 連線池取得（asyncpg）與 knowledge_completion_loops 記錄建立的 helper 函數
  - 完成後三個函數可獨立呼叫、排除邏輯（exclude_ids / exclude_topic_ids）正確運作
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 4.1, 4.2_

- [ ] 2. Core：SOP 生成與 LLM 評估
- [ ] 2.1 (P) 擴展 SOPGenerator 新增 generate_from_checklist()
  - 在 sop_generator.py 新增 `generate_from_checklist()` 方法，封裝 `generate_sop_items()`
  - gaps 中已包含 category_id，直接使用而非呼叫 LLM 選分類
  - gaps 中的 cashflow_relevant 決定是否標註金流模式
  - 保留現有品質驗證（2-pass AI QA）與重複偵測（pgvector 0.75）
  - 完成後用 1 筆測試 gap 呼叫 generate_from_checklist()，結果寫入 loop_generated_knowledge 且 category_id 正確
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - _Depends: 1.2_
  - _Boundary: SOPGenerator_

- [ ] 2.2 (P) 建立 llm_answer_evaluator.py
  - 實作 `evaluate_answer_quality(question, answer)` — 單筆聚焦 LLM 判定（yes/partial/no + 理由）
  - 實作 `evaluate_batch(results, concurrency=5)` — 批量判定回測結果
  - Prompt 核心：「這個回答是否從租客角度回答了租客的問題？」
  - 回傳格式解析包含 fallback 處理（格式異常時回傳 partial + 判定失敗）
  - 完成後用一組 question+answer 呼叫 evaluate_answer_quality()，回傳 verdict 為 yes/partial/no 之一
  - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - _Boundary: LLMAnswerEvaluator_

- [ ] 3. Integration：Pipeline 編排
- [ ] 3.1 建立 orchestrator.py Phase 1-5（生成 pipeline）
  - 實作 CLI 入口（argparse：--vendor-id, --exclude-sop-ids, --skip-phases, --scenario-ids）
  - Phase 1：讀取 process_checklist.json
  - Phase 2：呼叫 deactivate_existing_sops() 停用現有 SOP
  - Phase 3：呼叫 create_categories_from_checklist() 批量建分類
  - Phase 4：呼叫 checklist_to_gaps() + generate_from_checklist() 批量生成 SOP
  - Phase 5：暫停並輸出提示訊息（「N 筆 SOP 待審核，請至審核介面操作」）
  - 驗證：Phase 4 完成後，loop_generated_knowledge 中有 status=pending 的記錄，且可被現有 `/loop-knowledge/pending` API 查到
  - 完成後可透過 CLI 執行 Phase 1-5，生成的 SOP 出現在審核介面
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 3.1, 4.1, 4.2, 4.3, 4.4, 5.1_
  - _Depends: 1.1, 1.2, 2.1_

- [ ] 3.2 擴展 orchestrator.py Phase 6-7（回測驗證 pipeline）
  - Phase 6：呼叫 BacktestFrameworkClient.execute_batch_backtest() 執行回測
  - Phase 7：呼叫 evaluate_batch() 對回測結果執行聚焦 LLM 判定
  - 當 LLM 判定為 no 時，將 final_passed 改為 fail
  - 輸出覆蓋率報告：pass_rate、失敗原因分布、LLM 判定統計（yes/partial/no 數量與比例）
  - 將 llm_judgment 寫入 backtest_results.evaluation JSONB
  - 完成後可透過 --skip-phases 跳過 Phase 1-5 直接執行 Phase 6-7，輸出包含 LLM 判定統計
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.5, 7.6_
  - _Depends: 2.2, 3.1_

- [ ] 4. Validation：測試
- [ ] 4.1 (P) Unit tests
  - 測試 checklist_to_gaps() 格式轉換正確性（含 category_id 映射）
  - 測試 deactivate_existing_sops() 停用邏輯（含 exclude_ids 排除 — Req 2.4）
  - 測試 create_categories_from_checklist() upsert 邏輯（已存在不重建）
  - 測試 checklist_to_gaps() 的 exclude_topic_ids 排除邏輯
  - 測試 evaluate_answer_quality() 回傳格式解析（mock OpenAI，含異常格式 fallback）
  - 完成後所有 unit tests 通過（pytest 綠燈）
  - _Requirements: 2.4, 3.1, 4.4, 7.3, 7.4_
  - _Depends: 1.2, 2.2_
  - _Boundary: coverage_utils, LLMAnswerEvaluator_

- [ ] 4.2 (P) Integration test（小規模端到端）
  - 用測試 vendor 執行完整 pipeline Phase 1-4（5 筆子題的迷你清單）
  - 驗證 SOP 停用、分類建立、SOP 生成、loop_generated_knowledge 記錄正確
  - 驗證生成的記錄可被現有審核 API（`/loop-knowledge/pending`）查到
  - 驗證 Phase 6-7 回測 + LLM 判定結果包含 llm_judgment 欄位
  - 完成後 integration test 通過，覆蓋 Phase 1-7 完整流程
  - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.2, 7.5, 7.6_
  - _Depends: 3.1, 3.2_
  - _Boundary: orchestrator_
