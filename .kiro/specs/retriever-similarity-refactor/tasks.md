# 實作任務：retriever-similarity-refactor

> **建立時間**：2026-04-16T15:00:52Z
> **需求文件**：requirements.md
> **設計文件**：design.md
> **語言**：Traditional Chinese (zh-TW)

---

## 任務概述

本文件定義「Retriever Similarity 欄位重構」的實作任務，將 SOP 與知識庫 retriever 的多階段分數欄位分離，避免 `similarity` 被多層覆寫，使 `base_similarity` 顯示真實向量相似度。

**實作範圍**：
- ✅ 新增 `vector_similarity`、`keyword_score`、`keyword_boost`、`rerank_score` 獨立欄位
- ✅ retriever pipeline 各 stage 改為純資料增補，不互相覆寫
- ✅ 新增 `_finalize_scores` 階段統一計算最終 similarity
- ✅ 下游消費者欄位讀取更新（chat.py、chat_shared.py、llm_answer_optimizer.py、backtest）
- ✅ 移除死碼 `services/sop_keywords_handler.py`
- ✅ PERFECT_MATCH_THRESHOLD 校準
- ✅ 效能基準測試

**任務編號說明**：
- 主任務編號順序遞增（0, 1, 2, ...）
- 階段 0 為前置清理任務
- 子任務使用主任務編號.序號（如 1.1, 1.2）
- 任務標記 `(P)` 表示可並行執行

---

## 0. 前置清理（Critical - 優先執行）

### 0.1 移除死碼 sop_keywords_handler.py ✅

**需求覆蓋**：3, 9

刪除已確認無外部調用點的死碼，避免重構時誤改。

**驗收標準**：
- [x] 刪除檔案 `rag-orchestrator/services/sop_keywords_handler.py`
- [x] 全 codebase 確認無 import / 調用殘留（grep 確認）
- [x] `rag-orchestrator` 容器啟動正常（已 restart 驗證）

---

## 1. 資料模型與基礎設施

### 1.1 定義 RetrievalResult 型別契約 ✅

**需求覆蓋**：1

在 `services/retrieval_types.py`（新檔）定義 `RetrievalResult` TypedDict，包含所有分數欄位與 metadata。

**驗收標準**：
- [x] 新建 `rag-orchestrator/services/retrieval_types.py`
- [x] 定義 `RetrievalResult` TypedDict（vector_similarity / keyword_score / keyword_boost / rerank_score / similarity / score_source / 既有欄位）
- [x] 提供 `make_default_result()` 工廠函式（用於 `_format_result` 預設值）
- [x] 加上完整 docstring 說明各欄位語意

### 1.2 在 BaseRetriever 新增 _finalize_scores 方法 (P) ✅

**需求覆蓋**：4

實作統一的最終分數計算公式（rerank → keyword → vector 三分支）。

**驗收標準**：
- [x] `base_retriever.py` 新增 `_finalize_scores(results)` 方法
- [x] 依設計決策 4 的公式計算 similarity 與 score_source
- [x] log 顯示 `[Finalize] 計算 N 筆，分數來源: rerank=X, keyword=Y, vector=Z`

---

## 2. SOP Retriever 重構

### 2.1 _vector_search 移除 SQL threshold 過濾 ✅

**需求覆蓋**：2

`vendor_sop_retriever_v2.py._vector_search` 改為不在 SQL 端過濾，加上 `LIMIT 50` 控制單次回傳量。

**驗收標準**：
- [x] 移除 SQL 中 `WHERE GREATEST(...) >= %s` 的 threshold 條件
- [x] 加 `LIMIT 50`（可由參數覆寫）
- [x] SQL 仍計算 GREATEST(primary, fallback) 為 vector_similarity
- [x] 移除 `similarity_threshold` 參數的 SQL 端使用（只用於後續 application 過濾）

### 2.2 _vector_search 結果寫入 vector_similarity 欄位 (P) ✅

**需求覆蓋**：2

確保 SQL 算出的 cosine similarity 寫入 `vector_similarity` 欄位（不只 `similarity`）。

**驗收標準**：
- [x] SQL SELECT 中 `as similarity` 改名 `as vector_similarity`
- [x] _format_result 從 row 讀取 vector_similarity

### 2.3 _keyword_search 不再 cap 0.70，寫入 keyword_score ✅

**需求覆蓋**：3

`_keyword_search` 移除 0.70 上限，改寫入 `keyword_score` 獨立欄位；vector_similarity 預設 0.0。

**驗收標準**：
- [x] 移除 `result['similarity'] = min(0.70, normalized_score)` 邏輯
- [x] 改為 `result['keyword_score'] = normalized_score`、`result['vector_similarity'] = 0.0`
- [x] search_method 仍為 'keyword'

### 2.4 _format_result 包含所有新欄位 (P) ✅

**需求覆蓋**：1, 9

更新 `_format_result` 回傳 RetrievalResult 結構，含所有新欄位預設值。

**驗收標準**：
- [x] vector_similarity 從 row['vector_similarity'] 取（vector path）或預設 0.0（keyword path）
- [x] keyword_score / rerank_score 預設 None
- [x] keyword_boost 預設 1.0
- [x] similarity 暫時等於 vector_similarity（由 _finalize_scores 重算）
- [x] 保留 original_similarity = vector_similarity 作為向後相容 alias

---

## 3. 知識庫 Retriever 重構（與 SOP 邏輯一致）

### 3.1 _vector_search 移除 SQL threshold 過濾 (P) ✅

**需求覆蓋**：2

`vendor_knowledge_retriever_v2.py._vector_search` 同步改造（與 2.1 邏輯相同）。

**驗收標準**：
- [x] 移除 SQL threshold 條件
- [x] 加 `LIMIT 100`（知識庫資料量較大，但仍受控）
- [x] vector_similarity 從 SQL 寫入

### 3.2 _keyword_search 改寫入 keyword_score (P) ✅

**需求覆蓋**：3

知識庫 _keyword_search 同步改造（與 2.3 邏輯相同）。

**驗收標準**：
- [x] 移除 0.70 cap（若有）
- [x] 寫入 keyword_score；vector_similarity 預設 0.0

### 3.3 _format_result 包含所有新欄位 (P) ✅

**需求覆蓋**：1, 9

知識庫 _format_result 同步更新（與 2.4 邏輯相同）。

**驗收標準**：
- [x] 同 2.4，欄位齊全
- [x] 保留 original_similarity alias

---

## 4. BaseRetriever Pipeline 改造

### 4.1 _apply_keyword_boost 不覆寫 similarity ✅

**需求覆蓋**：3

`_apply_keyword_boost` 改為只更新 `keyword_boost` 與 `keyword_matches`，不修改 `vector_similarity` 或 `similarity`。

**驗收標準**：
- [x] 移除 `result['similarity'] = original_score * (1 + boost)` 的寫入
- [x] 改為 `result['keyword_boost'] = 1 + boost`
- [x] 仍計算 matched_keywords 並寫入 `result['keyword_matches']`
- [x] 排序由 _finalize_scores 後再做

### 4.2 _apply_semantic_reranker 不覆寫 vector_similarity，保留欄位映射 ✅

**需求覆蓋**：5, 9

reranker 只寫 `rerank_score`，不修改 vector_similarity / keyword_score / keyword_boost。

**驗收標準**：
- [x] 不再寫 `item['original_similarity'] = original_score`（由 _format_result 設定）
- [x] 不再寫 `item['similarity'] = ...`
- [x] 只寫 `item['rerank_score'] = semantic_score`
- [x] ⚠️ **必須保留** SOP→KB 欄位映射（`content→answer`、`item_name→question_summary`）供 reranker HTTP 服務使用

### 4.3 retrieve() 末端呼叫 _finalize_scores 並過濾 threshold ✅

**需求覆蓋**：4

`retrieve()` 主流程末端加入 `_finalize_scores(results)`，再依 application 端 threshold 過濾。

**驗收標準**：
- [x] 順序：vector_search → keyword_fallback → keyword_boost → semantic_reranker → finalize_scores → application threshold 過濾 → top_k 排序
- [x] 過濾用 `final similarity >= similarity_threshold`
- [x] 最終回傳 top_k 筆

---

## 5. 下游消費者更新

### 5.1 chat.py debug response 改用 vector_similarity ✅

**需求覆蓋**：6

chat.py 構建 debug response 時，`base_similarity` 對應到 `vector_similarity`，新增 `score_source` 欄位。

**驗收標準**：
- [x] 修改 chat.py 中所有 `'base_similarity': sop_item.get('similarity', 0.0)` 改為 `vector_similarity`（共 10 處左右）
- [x] 新增 `'score_source': sop_item.get('score_source', 'vector')`
- [x] 保留 `boosted_similarity`、`rerank_score`、`similarity` 欄位
- [x] CandidateSOP / CandidateKnowledge Pydantic 模型新增 `score_source` 欄位
- [x] 前端 chat-test 顯示驗證：不同 SOP 的 base_similarity 有差異（留待手測 7.5）

### 5.2 chat_shared.has_sop_results 改用 scope 判定 (P) ✅

**需求覆蓋**：5

移除 `similarity == 1.0` 比對，改用 `scope == 'vendor_sop'`。

**驗收標準**：
- [x] `chat_shared.py:202` 改為 `result.get('scope') == 'vendor_sop'`
- [x] 不再依賴 similarity 寫死數值
- [x] 確認 `format_sop_as_search_result` 仍設定 `scope='vendor_sop'`

### 5.3 llm_answer_optimizer._has_perfect_match 用 vector_similarity ✅

**需求覆蓋**：5

`_has_perfect_match` 改用 `vector_similarity` 判定（純語義匹配）。

**驗收標準**：
- [x] 修改 `llm_answer_optimizer.py:205` 從 `r.get('original_similarity', r['similarity'])` 改為 `r.get('vector_similarity', 0)`
- [x] log 訊息更新對應欄位名稱
- [x] 配合 task 8 的閾值校準

### 5.4 llm_answer_optimizer._should_synthesize 用 similarity (P) ✅

**需求覆蓋**：5

`_should_synthesize` 明確使用 `similarity`（最終分數）做合成觸發判定。

**驗收標準**：
- [x] `llm_answer_optimizer.py:446` 加上註解明示使用「final similarity」
- [x] 變數重新命名為 `max_final_similarity`，log 訊息同步標註 final similarity

### 5.5 backtest_framework_async 欄位讀取對齊 (P) ✅

**需求覆蓋**：7

回測注入 sources similarity 時，使用 final `similarity` 作為主排序，額外記錄 `vector_similarity`。

**驗收標準**：
- [x] `backtest_framework_async.py:177` 改為 `candidate.get('similarity', 0.0)` 為主、`vector_similarity` 為輔
- [x] source 中新增 `vector_similarity` 欄位
- [x] `rag-orchestrator/scripts/backtest/` 與 `scripts/backtest/` 兩份同步更新
- [x] 不影響既有 backtest_results 表結構

---

## 6. 環境變數註解更新

### 6.1 .env.example 註解標註各閾值對應欄位 (P) ✅

**需求覆蓋**：8

在 `.env.example` 註解中明確標註每個 threshold 環境變數對應的分數欄位語意。

**驗收標準**：
- [x] 新增 `Retriever Similarity Thresholds` 區塊，說明 `vector_similarity` / `similarity` 欄位語意
- [x] `PERFECT_MATCH_THRESHOLD` 註解：「比對 vector_similarity（純向量分數）」
- [x] `SOP_SIMILARITY_THRESHOLD` 註解：「比對 final similarity（application 端過濾）」
- [x] `KB_SIMILARITY_THRESHOLD` 註解：「同上」
- [x] `HIGH_QUALITY_THRESHOLD` 註解：「比對 final similarity（高品質判定）」
- [x] `SYNTHESIS_THRESHOLD` 註解：「比對 final similarity（合成觸發）」

### 6.2 docker-compose.prod.yml 註解同步 (P) ✅

**需求覆蓋**：8

`docker-compose.prod.yml` 中相關環境變數加上同樣註解。

**驗收標準**：
- [x] 同 6.1 對應欄位的註解加入 docker-compose.prod.yml
- [x] 註解放於環境變數同行尾
- [x] 加入引用 `docs/architecture/retriever-pipeline.md`

---

## 7. 測試與驗證

### 7.1 單元測試：BaseRetriever._finalize_scores (P) ✅

**需求覆蓋**：4

已於 `tests/test_finalize_scores.py` 實作（9 cases 通過）。

**驗收標準**：
- [x] 測試 case 1：有 rerank_score → similarity = 0.1×vector + 0.9×rerank
- [x] 測試 case 2：無 rerank、有 keyword → similarity = max(vector, keyword) × boost
- [x] 測試 case 3：純 vector → similarity = vector × boost
- [x] 三 case 的 score_source 正確標記
- [x] Edge cases（cap 1.0、missing field、empty input、不 mutate 前階段欄位）
- [x] log 格式驗證

### 7.2 單元測試：_apply_keyword_boost 不覆寫前階段欄位 (P) ✅

**需求覆蓋**：3

已於 `tests/test_base_retriever_pipeline.py:69-114` 實作（6 cases 通過）。

**驗收標準**：
- [x] 測試前後對比 vector_similarity 不變
- [x] 測試前後對比 keyword_score 不變
- [x] 測試前後對比 similarity 不變
- [x] keyword_boost 正確寫入為 multiplier（1 + boost）
- [x] keyword_matches 正確寫入
- [x] 無命中時 keyword_boost 維持 1.0

### 7.3 單元測試：_apply_semantic_reranker 保留欄位映射 (P) ✅

**需求覆蓋**：5, 9

已於 `tests/test_base_retriever_pipeline.py:143-198` 實作（7 cases 通過）。

**驗收標準**：
- [x] rerank_score 正確寫入
- [x] vector_similarity / keyword_score / keyword_boost 不變
- [x] 不覆寫 original_similarity
- [x] 不寫 similarity
- [x] SOP→KB 欄位映射保留（`content→answer`、`item_name→question_summary`）

### 7.4 整合測試：完整 retrieve pipeline 欄位累積 ✅

**需求覆蓋**：1, 2, 3, 4

已於 `tests/test_base_retriever_pipeline.py:235-281` 實作（4 cases 通過）。

**驗收標準**：
- [x] retrieve() 流程呼叫 _finalize_scores
- [x] 過濾用 final similarity >= threshold
- [x] 最終回傳 top_k 排序
- [x] finalize_scores 在 threshold 過濾前執行

### 7.5 手動驗證：chat-test base_similarity 顯示

**需求覆蓋**：6

在 chat-test 介面測試多種查詢，驗證不同 SOP 的 base_similarity 有差異（不再固定為 0.77）。

**驗收標準**：
- 測試「我想退租」：3 筆退租 SOP 的 base_similarity 為不同數值
- 測試「入住流程」：候選 SOP 的 base_similarity 反映真實向量分數
- 純 keyword 路徑命中的項目顯示 base_similarity = 0（符合設計）

---

## 8. PERFECT_MATCH_THRESHOLD 校準

### 8.1 建立 baseline（重構前回測）

**需求覆蓋**：8

部署重構前的程式碼到 staging（或本地），跑 vendor_id=2 完整回測，記錄 baseline 指標。

**驗收標準**：
- 跑完一次 BacktestFrameworkClient.execute_batch_backtest（vendor_id=2、approved scenarios）
- 記錄：每題的 system_answer、optimization_method、pass_rate
- 統計 perfect_match 觸發比例（baseline_perfect_match_rate）
- 結果存到 baseline_metrics.json 供後續比對

### 8.2 重構後跑相同測試集

**需求覆蓋**：8

部署重構版本到 staging，跑相同測試集，記錄重構後指標。

**驗收標準**：
- 同 8.1 的回測流程
- 記錄相同指標
- 結果存到 refactored_metrics.json

### 8.3 比對與校準閾值

**需求覆蓋**：8

依設計決策 6 的判斷規則決定是否調整 `PERFECT_MATCH_THRESHOLD`。

**驗收標準**：
- 比對 baseline vs refactored 的 pass_rate / perfect_match_rate
- 若 perfect_match_rate 變化 > 10% → 調整閾值，重跑 8.2 直到變化 ≤ 10%
- 若 pass_rate 下降 > 5% → 檢查 retriever 排序邏輯（可能需要回頭修 task 4）
- 預估閾值映射：原 0.90 → 新約 0.82（依實測微調）

### 8.4 記錄校準結果

**需求覆蓋**：8

校準完成後在 `docs/architecture/retriever-pipeline.md`（新檔）記錄校準資料。

**驗收標準**：
- 新建 `docs/architecture/retriever-pipeline.md`
- 記錄 baseline vs refactored 比對表
- 最終閾值決定與理由
- 更新 docker-compose.prod.yml 與 .env.example 中的閾值

---

## 9. 效能基準測試

### 9.1 重構前測量延遲 baseline

**需求覆蓋**：4.1, 7

對 vendor_id=2 跑 100 次相同 query 的 `/api/v1/message`，記錄平均延遲。

**驗收標準**：
- 設計測試腳本（可重用 baseline_metrics 流程）
- 記錄總延遲、retriever 階段延遲、reranker 階段延遲
- 結果存為 baseline_perf.json

### 9.2 重構後測量延遲 (P)

**需求覆蓋**：4.1, 7

部署重構版後跑相同測試。

**驗收標準**：
- 同 9.1 的腳本
- 結果存為 refactored_perf.json

### 9.3 比對效能差異與調整

**需求覆蓋**：4.1

比對重構前後延遲差異，若 > 10% 則調整。

**驗收標準**：
- 對比表：總延遲 / retriever / reranker
- 若 `/api/v1/message` 平均延遲增加 > 10% → 縮小 vector LIMIT（從 50 調至 30）或排查 reranker bottleneck
- 結果記錄到 docs/architecture/retriever-pipeline.md

---

## 10. 文件更新

### 10.1 更新 .kiro/steering/tech.md 向量處理章節 (P) ✅

**需求覆蓋**：4.3

steering tech.md 的「向量處理」章節更新分數欄位設計與檢索策略。

**驗收標準**：
- [x] 新增「Retriever Pipeline 分數欄位」章節
- [x] 分數欄位定義（vector_similarity / keyword_score / keyword_boost / rerank_score / similarity / score_source）
- [x] 更新檢索策略描述（Stage 1-5 pipeline）
- [x] 寫出 final similarity 階層式公式
- [x] 標註 SQL 不再過濾 threshold 的設計
- [x] 閾值對應欄位對照
- [x] 引用 docs/architecture/retriever-pipeline.md

### 10.2 補完 docs/architecture/retriever-pipeline.md (P) ✅

**需求覆蓋**：4.3, 8

完整文件描述 retriever pipeline 各階段、分數計算公式、閾值校準結果。

**驗收標準**：
- [x] 新建 `docs/architecture/retriever-pipeline.md`
- [x] pipeline 流程圖（mermaid）
- [x] 各 stage 欄位轉換表
- [x] 閾值對應欄位表
- [x] 下游消費者欄位對照
- [x] 校準歷史表格（待填入實測數據）
- [x] 效能基準目標

### 10.2 補完 docs/architecture/retriever-pipeline.md (P)

**需求覆蓋**：4.3, 8

完整文件描述 retriever pipeline 各階段、分數計算公式、閾值校準結果。

**驗收標準**：
- pipeline 流程圖（mermaid）
- 各 stage 欄位轉換表
- 閾值對應欄位表
- 校準歷史紀錄
