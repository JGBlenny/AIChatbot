# 研究記錄：retriever-similarity-refactor

> 建立時間：2026-04-16T14:39:12Z
> 目的：記錄技術調查、架構決策、相依性分析的過程與結果

## 摘要

### 調查範圍

針對現有 retriever pipeline（`base_retriever.py`、`vendor_sop_retriever_v2.py`、`vendor_knowledge_retriever_v2.py`）進行盤查，理解 similarity 欄位被多階段覆寫的問題根源，並評估重構對下游消費者（`chat.py`、`chat_shared.py`、`llm_answer_optimizer.py`、`backtest_framework_async.py`）的影響。

### 關鍵發現

- `similarity` 欄位在 retriever pipeline 中被 4 個階段（vector_search → keyword_search → keyword_boost → semantic_reranker）依序覆寫，導致原始向量分數遺失
- `_keyword_search` 對 keyword 命中項目給定固定上限 0.70，搭配 `_apply_keyword_boost` 的 ×1.1 加成，產生 0.77 這個固定數值，使不同 SOP 在前端顯示同樣的「基礎相似度」
- `chat_shared.py:202` 用 `similarity == 1.0` 判定 SOP，與重構後 similarity 不再固定為 1.0 的設計有衝突
- `llm_answer_optimizer.py:205` 已嘗試用 `original_similarity` 做 fallback，顯示開發者意識到問題但未徹底修正
- `backtest_framework_async.py:177` 使用 `boosted_similarity` 與 `base_similarity` 兩個欄位（命名與 retriever 不一致），是另一處需要對齊的點

## 研究主題

### 主題 1：similarity 欄位在 retriever pipeline 中的轉換流程

**調查問題**：
`similarity` 欄位從 `_vector_search` 開始到下游消費者讀取為止，經歷哪些轉換？哪些階段覆寫此欄位？

**研究方法**：
- [x] 現有程式碼分析

**發現**：

| 階段 | 檔案:行 | 對 similarity 的操作 | 副作用 |
|------|---------|-------------------|--------|
| 1. SQL 算 cosine | `vendor_sop_retriever_v2.py:97-100` 等 | 從 SQL `1 - (embedding <=> %s::vector)` 寫入 | 保留 |
| 2. SQL 端閾值過濾 | `vendor_sop_retriever_v2.py:115-118` | `WHERE GREATEST(...) >= threshold` | **過濾掉低分項目（資料遺失）** |
| 3. keyword fallback 給分 | `vendor_sop_retriever_v2.py:254` | `min(0.70, normalized_score)` | **覆寫 similarity，cap 至 0.70** |
| 4. keyword boost | `base_retriever.py:229` | `similarity = original × (1 + boost)` | **覆寫 similarity** |
| 5. semantic reranker | `base_retriever.py:262` | `similarity = original × 0.1 + rerank × 0.9` | **覆寫 similarity，但 `original_similarity` 與 `rerank_score` 已分離** |

**結論與建議**：
- 階段 2、3、4 是污染的主要來源
- 階段 5 已有部分隔離（`original_similarity`、`rerank_score`），可作為設計參考
- 重構應將每個階段的分數寫入獨立欄位，`similarity` 改為由公式組合而成

---

### 主題 2：下游消費者對 similarity 的依賴

**調查問題**：
哪些檔案讀取 retriever 結果中的 `similarity`？依賴的語意是什麼？

**研究方法**：
- [x] Grep 全 codebase

**發現**：

| 檔案:行 | 讀取欄位 | 用途 | 風險 |
|---------|---------|------|------|
| `chat.py:1210, 1782, 2061` | `similarity` | 寫入 `base_similarity` debug 欄位 | 中 — 命名誤導 |
| `chat.py:599, 615, 1168` | `base_similarity`, `original_similarity` | 構建 debug response | 低 — 已嘗試分離 |
| `chat_shared.py:138-139` | `similarity`, `original_similarity` | 排序與完美匹配 | 中 |
| `chat_shared.py:202` | `similarity == 1.0` | 判定 SOP | **高 — 寫死數值比較** |
| `llm_answer_optimizer.py:205-209` | `original_similarity` 優先，fallback `similarity` | perfect_match 判定 | **高 — 閾值決策** |
| `llm_answer_optimizer.py:446` | `similarity` | synthesis 觸發判定 | **高 — 閾值決策** |
| `confidence_evaluator.py:99-101` | `similarity` | 計算 max/avg | 低 — 純加權 |
| `backtest_framework_async.py:177` | `boosted_similarity` 優先，fallback `base_similarity` | 注入 debug 分數 | 中 — 欄位命名不一致 |
| `sop_keywords_handler.py:78` | `similarity` | 覆寫加成（與 base_retriever 重複邏輯？） | 中 |

**結論與建議**：
- 6 個檔案需要更新欄位讀取，2 個有閾值決策需重新校準
- `chat_shared.py:202` 與 `llm_answer_optimizer.py:205, 446` 是高風險變更點
- `sop_keywords_handler.py` 與 `base_retriever._apply_keyword_boost` 邏輯似乎重複，需釐清

---

### 主題 3：與正式對話相關的閾值現況

**調查問題**：
`PERFECT_MATCH_THRESHOLD`、`SOP_SIMILARITY_THRESHOLD`、`KB_SIMILARITY_THRESHOLD` 目前各自比對的欄位語意為何？

**研究方法**：
- [x] 現有程式碼分析
- [x] 環境變數調查

**發現**：

| 環境變數 | 預設值 | 比對欄位 | 實際語意 |
|---------|-------|---------|---------|
| `PERFECT_MATCH_THRESHOLD` | 0.90 | `original_similarity`（fallback `similarity`） | 「未經 boost 的原始向量相似度」 |
| `SOP_SIMILARITY_THRESHOLD` | 0.75 | SQL 端 `similarity >= threshold` | 「向量原始 cosine」 |
| `KB_SIMILARITY_THRESHOLD` | 0.65 | SQL 端 `similarity >= threshold` | 「向量原始 cosine」 |
| `HIGH_QUALITY_THRESHOLD` | 0.80 | `similarity` | 「最終分數」 |
| `SYNTHESIS_THRESHOLD` | 0.99 | `similarity` | 「最終分數」 |

**結論與建議**：
- 三個 retriever 端閾值（PERFECT_MATCH/SOP/KB）期待的是純向量分數
- 兩個 LLM 端閾值（HIGH_QUALITY/SYNTHESIS）期待的是最終分數
- 重構後須在環境變數註解明確標註對應欄位

---

## 技術選型

### 選型 1：分數欄位命名

**候選方案**：

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| A. 完全重新命名（廢棄 similarity） | 語意清楚 | 破壞向後相容、影響範圍大 | greenfield |
| B. 保留 similarity 為最終分數，新增獨立欄位 | 向後相容、漸進式重構 | 命名仍可能誤導 | brownfield ✓ |
| C. 用 namespace 包覆（scores: { vector: ..., keyword: ..., final: ... }） | 結構化 | API response 結構變更大 | 全新 API |

**評估標準**：
- 向後相容性 ✓
- 重構工作量
- 程式碼可讀性

**最終選擇**：方案 B

**理由**：
本專案已有 `original_similarity`、`rerank_score` 等欄位的命名慣例，沿用此風格新增 `vector_similarity`、`keyword_score`、`keyword_boost` 即可。`similarity` 保留作為最終排序使用的綜合分數，下游不需要立刻全部改寫。

---

### 選型 2：keyword_search 的分數計算

**候選方案**：

| 方案 | 優點 | 缺點 |
|------|------|------|
| A. 維持現有 0.70 cap | 不影響既有行為 | 仍有「固定值」問題 |
| B. 移除 cap，回傳真實 normalized_score（0–1） | 真實反映匹配度 | 可能與向量分數混淆 |
| C. 拆兩欄位：keyword_score + 由公式組合 final | 最清楚 | 公式設計需驗證 |

**評估標準**：
- 是否反映真實匹配度
- 對排序的影響

**最終選擇**：方案 C（搭配選型 1）

**理由**：
keyword_score 獨立記錄不受限，由統一公式計算 final similarity 時再套用 boost 與 vector 比較。這與向量分數語意完全分離。

---

### 選型 3：是否取消 SQL 端 threshold 過濾

**候選方案**：

| 方案 | 優點 | 缺點 |
|------|------|------|
| A. 保留 SQL 端 threshold | 效能好（DB 早過濾） | 低分項目資料遺失，無法給 chat-test debug 顯示 |
| B. 取消 SQL threshold，回傳全部加 vector_similarity | 可顯示低分項目，符合 Req 6 | 回傳量大，需設 LIMIT 與 row 上限 |
| C. SQL 端用較寬鬆的 floor（如 0.0），應用層再過濾 | 折衷 | 等於方案 B |

**最終選擇**：方案 B/C

**理由**：
本專案 SOP 規模 ~50 筆/業者、知識庫 ~1500 筆/業者，回傳全部不會造成顯著效能問題。設定合理 LIMIT（SOP 500、KB 1000）作為安全上限。

---

## 相依性分析

### 外部 API 與服務

| 服務名稱 | 版本 | 用途 | 文件連結 | 注意事項 |
|---------|------|------|---------|---------|
| pgvector | pg16 | 向量相似度 SQL | https://github.com/pgvector/pgvector | `<=>` 為 cosine distance |
| semantic-model | internal | reranker HTTP API | http://semantic-model:8000 | 內部容器 |
| embedding-api | internal | embedding HTTP API | http://embedding-api:5000 | 內部容器 |

### 函式庫與套件

| 套件名稱 | 版本 | 用途 | 授權 | 風險評估 |
|---------|------|------|------|---------|
| psycopg2-binary | 2.9.9 | PostgreSQL 同步 driver | LGPL | 既有 |
| jieba | 0.42.1 | 中文分詞 | MIT | 既有 |

無新增依賴。

## 現有程式碼分析

### 相關模式與慣例

**檔案位置**：
- `rag-orchestrator/services/base_retriever.py:200-235` — `_apply_keyword_boost` 已具備分離欄位雛形（`keyword_matches`、`keyword_boost`）
- `rag-orchestrator/services/base_retriever.py:255-265` — `_apply_semantic_reranker` 已分離 `original_similarity`、`rerank_score`
- `rag-orchestrator/routers/chat.py:1210, 1782, 2061` — 統一從 `sop_item['similarity']` 讀取
- `rag-orchestrator/routers/chat_shared.py:138-139` — 已嘗試保留 `original_similarity` 供完美匹配判定

**發現的模式**：
- Pipeline 風格：`retrieve()` 主流程串接多個 stage 函數
- Stage 函數透過修改傳入的 dict 進行資料增補（in-place 修改）
- 每個 stage 累積資料而非取代原始資料（除了 `similarity` 這個欄位）

**整合點**：
- 修改 `_apply_keyword_boost` 不再 in-place 寫 `similarity`，改為寫獨立欄位
- 修改 `_apply_semantic_reranker` 已有部分分離，需補齊
- 新增 stage：在 retrieve 末端統一計算 final `similarity`
- 子類 `_format_result` 增補新欄位

## 效能考量

### 效能基準

| 指標 | 目標值 | 測試方法 | 備註 |
|------|--------|---------|------|
| retriever 延遲增加 | < 5% | 比對重構前後同樣 query 的耗時 | - |
| SQL 回傳 row 數 | < 1000 | EXPLAIN ANALYZE | LIMIT 上限 |

### 瓶頸分析

- 取消 SQL 端 threshold 過濾後，pgvector 仍會用索引（IVFFlat/HNSW）做 top-k 檢索，效能影響有限
- 主要新增成本：`_apply_keyword_boost` 對所有候選做 jieba tokenize，但 boost 階段本來就要做

## 安全性考量

### 威脅模型
- 無新增資料外洩風險（不變更 API 結構）
- debug_info 仍受 `include_debug_info` 參數控制

### 緩解措施
- 保持既有的 `include_debug_info` 開關行為

## 風險登記

| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|------|------|------|------|---------|------|
| `chat_shared.py:202` 改用 scope 判定可能影響 SOP 觸發行為 | 技術 | 高 | 中 | 完整回測驗證 + 比對 conversation_logs | 開放 |
| `PERFECT_MATCH_THRESHOLD` 語意改變需重新校準 | 商業 | 高 | 高 | 在 staging 環境跑回測，比較 pass_rate | 開放 |
| `_apply_keyword_boost` 不再覆寫 similarity 後，排序順序改變 | 技術 | 中 | 高 | 在 retrieve 末端用 final similarity 重新排序 | 開放 |
| `sop_keywords_handler.py` 邏輯重複導致改不完整 | 技術 | 中 | 中 | 在重構前釐清兩處邏輯關係 | 開放 |
| 既有 backtest 結果無法直接與重構後比較 | 商業 | 低 | 中 | 重構後重新跑 baseline 回測作為新基準 | 開放 |

## 開放問題

### 問題 1：sop_keywords_handler 與 base_retriever 的關係
**描述**：
`services/sop_keywords_handler.py` 也有 boost 邏輯，與 `base_retriever._apply_keyword_boost` 看起來重複。

**影響範圍**：
不確定 sop_keywords_handler 是否仍被調用、調用時機是什麼。

**盤查結果（2026-04-16）**：

```bash
grep -rn "from services.sop_keywords_handler\|import sop_keywords_handler\|SOPKeywordsHandler\|get_sop_keywords_handler"
```

整個 `rag-orchestrator/` 中**僅有檔案自身定義**（`SOPKeywordsHandler` class、`get_sop_keywords_handler()` getter），無任何外部 import 或調用點。

**決策**：解法 A — 屬於死碼，重構時一併移除整個 `services/sop_keywords_handler.py` 檔案。

**狀態**：已決定

### 問題 2：keyword_score 是否需要 cap

**描述**：
原本 0.70 cap 的設計意圖是「keyword 命中不應等同於完美語義匹配」。移除 cap 後，是否會有 keyword 路徑分數壓過 vector 路徑的情況？

**影響範圍**：
排序行為。

**可能解法**：
- 解法 A：完全不 cap，由公式中的權重控制
- 解法 B：在 final similarity 公式中對 keyword_score 賦予較低權重

**決策狀態**：採方案 B（公式：`max(vector, keyword) × boost`，vector 通常較大）

---

## 時間軸

| 日期 | 活動 | 結果 | 後續行動 |
|------|------|------|---------|
| 2026-04-16 | 研究啟動 | 完成 pipeline 與消費者盤查 | 進入設計階段 |

## 參考資源

### 官方文件
- [pgvector README](https://github.com/pgvector/pgvector)

### 相關討論
- 內部 issue：chat-test base_similarity 顯示固定 0.77 的問題（本 spec 起源）

---

*本文件持續更新，記錄設計階段的所有重要調查與決策過程。*
