# 需求規格：backtest-scoring-answer-quality

> **功能名稱**：回測評分對齊與 AI 答案品質驗證
> **建立時間**：2026-04-17T00:00:00+08:00
> **語言**：Traditional Chinese (zh-TW)

---

## 簡介

本規格確保 retriever-similarity-refactor 重構後的分離式分數欄位（`vector_similarity`、`keyword_score`、`keyword_boost`、`rerank_score`、`similarity`）在回測（`/backtest`）流程中被正確消費與判定，並確保回測中 AI 生成的答案品質符合 backtest-knowledge-refinement 規格所定義的優質 AI 客服標準。

## 範圍

- **包含**：
  - 回測評分邏輯（`evaluate_answer_v2`）與新分數欄位的對齊驗證
  - 回測 confidence 計算公式中 `max_similarity` 欄位語意的明確化
  - 回測結果記錄中新分數欄位（`vector_similarity`、`score_source`）的完整保留
  - AI 生成答案的品質評估基準，參照 backtest-knowledge-refinement 規格中知識生成的品質要求
  - 回測 pass/fail 判定在重構前後的一致性驗證

- **不包含**：
  - retriever pipeline 本身的分數計算邏輯（屬於 retriever-similarity-refactor）
  - 知識完善迴圈的流程編排（屬於 backtest-knowledge-refinement）
  - 前端 UI 變更
  - API endpoint 變更

- **相鄰期望**：
  - 本功能假設 retriever-similarity-refactor 已完成部署，`similarity` 欄位語意為 `_finalize_scores` 計算的最終組合分數
  - 本功能假設 backtest-knowledge-refinement 的知識生成器（`KnowledgeGenerator`、`SOPGenerator`）已可運作，生成的答案內容為本規格的品質評估對象

---

## 需求

### Requirement 1：回測 confidence 計算與新分數欄位對齊

**Objective:** As a 回測執行者, I want 回測的 confidence 計算公式使用語意正確的分數欄位, so that 重構後的回測判定結果與預期一致。

#### Acceptance Criteria

1. The 回測評分系統 shall 在 `evaluate_answer_v2()` 計算 `max_similarity` 時，使用 sources 中的 `similarity` 欄位（最終組合分數），而非 `vector_similarity`
2. The 回測評分系統 shall 維持現有 confidence 公式：`confidence_score = max_similarity × 0.7 + result_count_score × 0.2 + keyword_match_rate × 0.1`，其中 `max_similarity` 對應 retriever 的 final `similarity`
3. When 回測取得的 sources 中包含 `vector_similarity` 欄位時, the 回測評分系統 shall 額外記錄 `max_vector_similarity`（所有 sources 中 `vector_similarity` 的最大值）供後續分析
4. The 回測評分系統 shall 在 confidence 計算結果中包含 `score_fields_used` 標註（例如 `{"max_similarity_field": "similarity", "value": 0.92}`），明確記錄使用了哪個欄位

### Requirement 2：回測 pass/fail 判定一致性

**Objective:** As a 品質負責人, I want 重構前後的回測 pass/fail 判定邏輯保持一致, so that 回測結果可作為可靠的品質指標。

#### Acceptance Criteria

1. The 回測系統 shall 維持現有 pass/fail 閾值邏輯：`confidence_score >= 0.70 → pass`；`confidence_score >= 0.60 → pass`；`confidence_score < 0.60 → fail`
2. When 回測使用重構後的 retriever 時, the 回測系統 shall 確保 pass_rate 變化不超過 ±5%（與重構前 baseline 比較）
3. If 回測發現「無資料」關鍵字（如「查無資料」、「目前沒有」）, the 回測系統 shall 將該案例判定為 fail，不受 confidence_score 影響
4. The 回測系統 shall 對表單類知識（`form_fill`、`form_then_api`）維持特殊判定邏輯：表單成功觸發即視為 pass

### Requirement 3：回測結果中新分數欄位的完整記錄

**Objective:** As a 知識分析師, I want 回測結果記錄所有 retriever 分數欄位, so that 可分析不同 pipeline 階段對回測結果的影響。

#### Acceptance Criteria

1. The 回測框架 shall 在每筆回測結果的 `evaluation` 欄位（JSONB）中記錄以下分數：
   - `max_similarity`（final 組合分數最大值）
   - `max_vector_similarity`（純向量分數最大值）
   - `top_score_source`（最高分結果的 `score_source`：`"rerank"` / `"keyword"` / `"vector"`）
2. When 回測從 debug_info 萃取 sources 時, the 回測框架 shall 保留每個 source 的 `similarity`、`vector_similarity`、`score_source` 欄位
3. The 回測框架 shall 在回測批次（`backtest_runs`）的摘要統計中，新增以下欄位：
   - `avg_vector_similarity`：所有通過案例的平均 `vector_similarity`
   - `score_source_distribution`：各 `score_source` 類型的案例數量分布

### Requirement 4：AI 生成答案的品質評估基準

**Objective:** As a 知識完善迴圈的審核者, I want 回測中 AI 生成的答案遵循明確的品質標準, so that 答案符合 AI 客服的優質回應要求。

#### Acceptance Criteria

1. The 回測系統 shall 以下列維度評估 AI 答案品質（參照 backtest-knowledge-refinement 知識生成規格）：
   - **完整性**：答案是否涵蓋問題的核心要點
   - **準確性**：答案內容是否與知識庫/SOP 內容一致
   - **可操作性**：答案是否提供明確的行動步驟或指引
2. When 回測答案的 confidence_score >= 0.70 但答案內容包含模糊語句（如「請洽客服」、「視情況而定」）且無具體後續步驟時, the 回測系統 shall 在 evaluation 中標註 `quality_warning: "vague_answer"`
3. When 知識完善迴圈（backtest-knowledge-refinement）生成的知識已同步到正式庫後, the 回測系統 shall 能透過重新回測驗證該知識是否有效改善了對應案例的回答品質
4. The 回測系統 shall 在 evaluation 中記錄 `answer_source` 欄位，標註答案來源類型（`"sop_direct"` / `"knowledge_direct"` / `"llm_synthesis"` / `"template"`），以便追蹤不同來源的答案品質差異

### Requirement 5：回測與知識完善迴圈的品質回饋閉環

**Objective:** As a 系統維運者, I want 回測結果能回饋到知識完善迴圈的改善決策, so that 迭代改善有明確的數據依據。

#### Acceptance Criteria

1. When 回測中一個案例連續 2 次迭代仍為 fail 時, the 回測系統 shall 在 `knowledge_gap_analysis` 中標註 `persistent_failure: true`，提供給知識完善迴圈優先處理
2. The 回測系統 shall 提供每次迭代的分數趨勢比較，包含：
   - 迭代間 `pass_rate` 變化
   - 迭代間 `avg_confidence_score` 變化
   - 迭代間 `avg_vector_similarity` 變化（新增）
3. When 知識完善迴圈新增或修改知識後重新回測時, the 回測系統 shall 在結果中標註 `knowledge_changed: true` 及對應的 `source_loop_id`，以便追蹤知識變更對回測的影響
4. If 重新回測後 pass_rate 未改善（差異 < 1%）, the 回測系統 shall 在迭代摘要中標註 `stagnation_warning: true`，提示可能需要調整知識生成策略

### Requirement 6：回測環境閾值校準驗證

**Objective:** As a 部署工程師, I want 回測環境的閾值設定與 retriever 重構後的分數語意一致, so that 回測判定不因閾值語意變更而產生偏差。

#### Acceptance Criteria

1. The 回測系統 shall 使用與正式對話相同的閾值環境變數（`SOP_SIMILARITY_THRESHOLD`、`KB_SIMILARITY_THRESHOLD`、`PERFECT_MATCH_THRESHOLD`）
2. The 回測系統 shall 在每次回測批次開始時，記錄當前使用的所有閾值設定到 `backtest_runs` 的 metadata 中
3. When `PERFECT_MATCH_THRESHOLD` 語意從「含 boost 的 similarity」改為「純 vector_similarity」後, the 回測系統 shall 驗證 perfect_match 觸發比例與 baseline 差異不超過 ±10%
4. If 回測偵測到閾值設定與預期不符（例如 `PERFECT_MATCH_THRESHOLD > 0.95` 導致零觸發）, the 回測系統 shall 在 log 中輸出警告訊息

---

## 下一步

需求審核通過後執行：

```bash
# 選擇性：盤查現有實作差距
/kiro-validate-gap backtest-scoring-answer-quality

# 進入設計階段
/kiro-spec-design backtest-scoring-answer-quality
```
