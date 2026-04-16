# 需求規格：retriever-similarity-refactor

> **功能名稱**：Retriever Similarity 欄位重構 — 分離向量分數與 boost/rerank 後的最終分數
> **建立時間**：2026-04-16T14:39:12Z
> **語言**：Traditional Chinese (zh-TW)

---

## 1. 專案概述

### 1.1 核心目標

重構 SOP 與知識庫 retriever 的分數欄位設計，將「原始向量相似度」、「關鍵字加成」、「Reranker 重排序」等多階段分數分離為獨立欄位，避免單一 `similarity` 欄位被多層覆寫，導致前端 `base_similarity` 顯示誤導性的固定值（如 0.77）。

### 1.2 問題現況

#### 觀察到的異常

1. 前端 chat-test 頁面顯示「基礎相似度」(`base_similarity`) 對多個 SOP 都是相同數值（如 0.770）
2. 不同 SOP 之間真實的向量語義差異無法從 `base_similarity` 看出
3. 排序差異實質上由 `rerank_score` 決定，但前端命名暗示 `base_similarity` 應為向量分數

#### 根本原因

`similarity` 欄位在 retriever pipeline 中被多階段覆寫：

1. **`_vector_search`**：SQL 算出 cosine similarity，寫到 `similarity`，並在 SQL 端用 threshold 過濾
2. **`_keyword_search`**（fallback）：自己算 normalized score，cap 在 0.70，**覆寫** `similarity`
3. **`_apply_keyword_boost`**：`similarity *= (1 + boost)`，**覆寫** `similarity`
4. **`_apply_semantic_reranker`**：用 reranker 分數覆寫 `similarity`

當查詢走 keyword fallback + boost 路徑時，最終 `similarity = 0.70 × 1.1 = 0.77`（固定值），且原始向量分數（可能是 0.62、0.58 等）已遺失。

### 1.3 業務影響

| 影響面向 | 說明 |
|---------|------|
| Debug 顯示 | chat-test 開發者無法判斷向量真實匹配度 |
| 知識完善迴圈 | 無法分析「向量找不到但 keyword 命中」的 gap pattern |
| 閾值調校 | 無法針對純向量分數調整 SOP_SIMILARITY_THRESHOLD |
| 回測分析 | backtest 結果中的 similarity 語意不一致 |

### 1.4 設計原則

1. **欄位職責單一**：每個分數欄位只代表一個階段的結果
2. **不可變性**：原始分數寫入後不被後續階段覆寫
3. **向後相容**：保留現有 `similarity` 欄位作為「最終分數」，新增分離欄位
4. **可觀測性**：所有中間分數可在 debug_info 中查看
5. **決策邏輯透明**：閾值比較明確指定使用哪個欄位

---

## 2. 範圍

### 2.1 包含

- `BaseRetriever`、`VendorSOPRetrieverV2`、`VendorKnowledgeRetrieverV2` 的分數欄位重構
- `_apply_keyword_boost`、`_apply_semantic_reranker`、`sop_keywords_handler` 的覆寫邏輯改造
- `chat.py`、`chat_shared.py` 中讀取 similarity 的地方更新為對應的新欄位
- `llm_answer_optimizer.py` 中閾值決策邏輯的明確化（`perfect_match`、合成觸發）
- `backtest_framework_async.py` debug_info 欄位讀取更新
- 前端 chat-test debug 顯示欄位的對應更新（如有需要）

### 2.2 不包含

- 修改向量模型本身或 embedding 生成邏輯
- 變更 reranker 服務本身
- 重新訓練或調整 embedding 維度
- 變更 retriever 的整體流程（向量 → keyword fallback → boost → rerank 的順序不變）

---

## 3. 需求

### Requirement 1：分數欄位定義

retriever 系統**應**在每筆檢索結果中明確分離以下分數欄位：

**驗收標準**：

- 系統**應**在每筆 retriever 結果中提供 `vector_similarity` 欄位，代表 query 與項目 embedding 的原始 cosine similarity（範圍 0.0–1.0）
- 系統**應**在每筆結果中提供 `keyword_score` 欄位，代表關鍵字配對的計算分數；無關鍵字命中時為 `null`
- 系統**應**在每筆結果中提供 `keyword_boost` 欄位，代表 boost 倍率（如 1.1、1.2）；未套用 boost 時為 `1.0`
- 系統**應**在每筆結果中提供 `rerank_score` 欄位，代表 SemanticReranker 的分數；未經 rerank 時為 `null`
- 系統**應**保留 `similarity` 欄位作為最終排序使用的綜合分數
- 各欄位之間**不得**互相覆寫

### Requirement 2：向量搜尋分數保留

`_vector_search` **應**回傳每筆結果的真實向量相似度，且後續流程**不得**修改此值。

**驗收標準**：

- `_vector_search` SQL 回傳的 cosine similarity **必須**寫入 `vector_similarity` 欄位
- 即使項目相似度低於閾值，仍**應**保留向量分數供後續分析（不在 SQL 端過濾掉）
- `_apply_keyword_boost`、`_apply_semantic_reranker` **不得**修改 `vector_similarity` 欄位
- 純 keyword fallback 路徑命中的項目，`vector_similarity` **應**為實際算出的向量分數（而非 0 或 null）

### Requirement 3：Keyword 路徑分數獨立記錄

`_keyword_search` 與 `_apply_keyword_boost` **應**將計算結果寫入獨立欄位。

**驗收標準**：

- `_keyword_search` 的 normalized score **應**寫入 `keyword_score` 欄位
- `_keyword_search` **不應**對 `keyword_score` 套用 0.70 的硬上限（保留原始計算結果）
- `_apply_keyword_boost` 計算的 boost 倍率**應**寫入 `keyword_boost` 欄位
- `_apply_keyword_boost` **不應**直接修改 `vector_similarity` 或 `keyword_score`，僅更新 `keyword_boost` 與 `similarity`

### Requirement 4：最終分數計算公式

`similarity` 欄位**應**依明確公式從前述獨立欄位計算而來。

**驗收標準**：

- 最終 `similarity` **應**依以下優先順序與公式計算：
  1. 若有 `rerank_score`：`similarity = 0.1 × vector_similarity + 0.9 × rerank_score`
  2. 否則若有 `keyword_score`：`similarity = max(vector_similarity, keyword_score) × keyword_boost`
  3. 否則：`similarity = vector_similarity × keyword_boost`
- 計算公式**應**明文記錄於程式碼註解或 docstring
- 系統**應**在 debug_info 中提供計算來源（例如 `score_source: "rerank" | "keyword" | "vector"`）

### Requirement 5：決策邏輯明確化

下游服務（`llm_answer_optimizer`、`chat_shared` 等）**應**明確指定使用哪個欄位進行決策。

**驗收標準**：

- `llm_answer_optimizer._has_perfect_match()` **應**明確使用 `vector_similarity`（純語義匹配）作為 perfect_match 判定
- `llm_answer_optimizer._should_synthesize()` **應**明確使用 `similarity`（最終分數）作為合成觸發判定
- `chat_shared.has_sop_results()` **應**改用 `scope == 'vendor_sop'` 判定，不依賴 `similarity == 1.0`
- 所有閾值比較**必須**在程式碼註解中說明使用的欄位語意

### Requirement 6：前端 debug 顯示對應

chat.py 構建 debug_info 時**應**將分數欄位對應到正確的 retriever 欄位。

**驗收標準**：

- `base_similarity` debug 欄位**必須**對應到 retriever 的 `vector_similarity`
- `boosted_similarity` debug 欄位**必須**對應到 `vector_similarity × keyword_boost` 或實作中的等價值
- `rerank_score` debug 欄位**必須**對應到 retriever 的 `rerank_score`
- 前端「基礎相似度」欄位顯示的數字**應**反映實際向量語義匹配（不同項目間應有差異）

### Requirement 7：回測欄位語意一致

回測框架（`backtest_framework_async.py`）讀取 similarity 時**應**使用一致的欄位語意。

**驗收標準**：

- 回測 debug_info 萃取**應**優先使用 `similarity`（最終分數）作為主要排序依據
- 回測**應**額外記錄 `vector_similarity` 供後續分析
- 回測 evaluation 邏輯**不應**依賴特定固定值（如 0.77）

### Requirement 8：閾值校準

重構後**應**重新校準現有閾值，確保系統行為不退化。

**驗收標準**：

- 系統**應**比較重構前後的對話品質：使用既有測試集（test_scenarios）執行回測，pass_rate 變化**不應**超過 ±5%
- `SOP_SIMILARITY_THRESHOLD`、`KB_SIMILARITY_THRESHOLD`、`PERFECT_MATCH_THRESHOLD` 等環境變數的語意**應**在 .env.example 與 docker-compose.prod.yml 註解中明確標註對應的分數欄位
- 若閾值需要調整，**應**在 docs/architecture/ 提供調整依據與比較數據

### Requirement 9：向後相容

重構**不應**破壞現有 API 回應結構。

**驗收標準**：

- `/api/v1/message` 的 response payload 結構**不應**變更（除新增欄位外）
- 既有的 `sop_candidates[].base_similarity`、`sop_candidates[].boosted_similarity`、`sop_candidates[].rerank_score` 欄位**必須**保留
- 新欄位（如 `vector_similarity`）**應**作為新增欄位，不破壞舊版前端

### Requirement 10：可觀測性

系統**應**在 debug log 中清楚標示分數計算過程。

**驗收標準**：

- 系統**應**在 retriever 執行時 log 出 `[向量檢索] 找到 N 個結果 (similarity 範圍: X.XX–Y.YY)`
- 系統**應**在 keyword boost 階段 log 出 `[關鍵字加成] 命中 K 個關鍵字, boost ×Z`
- 系統**應**在 reranker 階段 log 出 `[Reranker] 重排序 N 個項目, 分數變化: ...`
- 系統**應**避免冗餘 log（不重複輸出相同資訊）

---

## 4. 非功能需求

### 4.1 效能

- 重構**不應**顯著增加 retriever 延遲（目標 < 5%）
- 取消 SQL 端 threshold 過濾後，回傳 row 數可能增加，**應**評估對 PostgreSQL 查詢效能的影響並設定合理的 LIMIT

### 4.2 測試

- **應**為新分數欄位邏輯撰寫 unit test
- **應**驗證重構後的 perfect_match、synthesis 觸發行為與原本一致
- **應**執行至少一次完整回測，確認 pass_rate 無顯著下降

### 4.3 文件

- **應**更新 `.kiro/steering/tech.md` 中向量處理相關章節
- **應**在 `docs/architecture/` 新增說明文件，描述 retriever pipeline 各階段分數的轉換邏輯

---

## 5. 驗證方式

1. **chat-test 顯示**：問同一個 query，前端「基礎相似度」對不同 SOP 顯示不同的真實向量分數
2. **單元測試**：新分數欄位邏輯通過所有 test case
3. **回測對比**：重構前後 pass_rate 差異 < 5%
4. **Log 檢查**：retriever log 清楚呈現各階段分數變化

---

## 下一步

需求審核通過後執行：

```bash
# 選擇性：盤查現有實作差距
/kiro:validate-gap retriever-similarity-refactor

# 進入設計階段
/kiro:spec-design retriever-similarity-refactor
```
