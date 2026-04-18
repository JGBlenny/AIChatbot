# Gap Analysis：backtest-scoring-answer-quality

> 分析時間：2026-04-17
> 需求文件：requirements.md
> 相關規格：retriever-similarity-refactor、backtest-knowledge-refinement

---

## 1. 關鍵發現：「答案品質」在系統中沒有統一定義

現有系統對「答案品質」有 **三套獨立且不互通的定義**：

### 定義 A：回測 confidence 分數（量化指標，自動判定）

**位置**：`scripts/backtest/backtest_framework_async.py` → `evaluate_answer_v2()`

```
confidence_score = max_similarity × 0.7 + result_count_score × 0.2 + keyword_match_rate × 0.1
```

| 閾值 | 判定 | 語意 |
|------|------|------|
| >= 0.85 | PASS（高品質） | 檢索到高相似度結果 |
| >= 0.70 | PASS（中品質） | 檢索到中等相似度結果 |
| >= 0.60 | PASS（低品質） | 勉強通過 |
| < 0.60 | FAIL | 信心不足 |

**問題**：此公式衡量的是「**檢索品質**」（找到多好的知識），而非「**答案品質**」（回答得多好）。一個 confidence = 0.90 的結果可能回傳一段模糊的「請洽管理師」答案，仍然會 PASS。

### 定義 B：DB schema 的 1-5 分評分（LLM 評審，存在但部分啟用）

**位置**：`backtest_results` 表有 5 個 1-5 分欄位

| 欄位 | 用途 |
|------|------|
| `relevance` | 答案與問題的相關性 |
| `completeness` | 答案的完整性 |
| `accuracy` | 答案的準確性 |
| `intent_match` | 意圖匹配度 |
| `quality_overall` | 綜合品質 |

**現況**：`backtest_runs.quality_mode` 支援 `basic`（預設）/ `hybrid` / `detailed` 三種模式。`basic` 模式只算 confidence，**不啟用** LLM 評審。`detailed` 模式會用 GPT 對答案做 1-5 分評分，但因成本高（每題多一次 OpenAI 呼叫），日常回測不使用。

### 定義 C：知識生成的 prompt 品質要求（質性標準，寫在 prompt 中）

**位置**：`knowledge_generator.py`（lines 38-95）、`sop_generator.py`（lines 71-153）

**KnowledgeGenerator prompt 定義的品質**：
- 直接回答（無前言），100-300 字
- 從租客（房客）角度出發，強調權益
- 不得捏造資訊、不用行話
- 只在不確定時引導「詢問管理師」

**SOPGenerator prompt 定義的品質**：
- 自然友善，像 LINE 聊天
- 第一句就直接回答
- 一個 SOP = 一個具體面向（不打包）
- 不用花式開場、不提「SOP/流程/規範」字眼

**問題**：這些品質要求只存在於 prompt 文字中，**回測系統完全不知道也不檢查**這些標準。

---

## 2. 現有實作與需求的差距對照

### Requirement 1：回測 confidence 與新分數欄位對齊

| 需求項 | 現有實作 | Gap |
|--------|---------|-----|
| `max_similarity` 使用 final `similarity` | ✅ 已實作：`sources[0].get('similarity', 0.0)` | **無 gap**（重構後 similarity 仍為 final score） |
| 額外記錄 `max_vector_similarity` | ⚠️ 部分：debug_info 萃取了 `vector_similarity` 注入到 sources，但 evaluate_answer_v2 未讀取 | **小 gap**：evaluate 函數需新增讀取 |
| `score_fields_used` 標註 | ❌ 不存在 | **新功能** |

### Requirement 2：pass/fail 判定一致性

| 需求項 | 現有實作 | Gap |
|--------|---------|-----|
| 閾值邏輯維持 | ✅ 已實作 | **無 gap** |
| pass_rate 差異 ≤ ±5% | ❌ 無自動比較機制 | **需新增**：baseline 比較邏輯 |
| 「無資料」關鍵字偵測 | ✅ 已實作（多個中文關鍵字匹配） | **無 gap** |
| 表單類特殊判定 | ✅ 已實作 | **無 gap** |

### Requirement 3：回測結果新分數欄位完整記錄

| 需求項 | 現有實作 | Gap |
|--------|---------|-----|
| evaluation 記錄 max_vector_similarity | ❌ evaluation dict 只有 max_similarity | **小 gap**：新增欄位 |
| evaluation 記錄 top_score_source | ❌ 不存在 | **新功能** |
| backtest_runs 摘要統計 | ❌ 無 avg_vector_similarity、score_source_distribution | **小 gap**：新增摘要欄位 |

### Requirement 4：AI 生成答案品質評估基準 ⚠️ 主要 Gap

| 需求項 | 現有實作 | Gap |
|--------|---------|-----|
| 完整性/準確性/可操作性評估 | ⚠️ DB schema 有 1-5 分欄位，但 basic 模式不啟用 | **核心 gap**：需決定用哪套機制 |
| 模糊答案偵測 (`quality_warning`) | ⚠️ knowledge_generator 有簡單檢查（< 30 字），但 evaluate_answer_v2 沒有 | **中等 gap** |
| 知識同步後驗證改善 | ✅ BacktestFrameworkClient.execute_validation_backtest() 已存在 | **無 gap** |
| `answer_source` 記錄 | ❌ 不存在 | **需新增**：從 response 中萃取 optimization_method |

### Requirement 5：品質回饋閉環

| 需求項 | 現有實作 | Gap |
|--------|---------|-----|
| persistent_failure 標註 | ❌ 不存在 | **新功能**：需比對歷史回測結果 |
| 迭代趨勢比較 | ⚠️ loop_execution_logs 有 event_data，但無結構化趨勢 | **中等 gap** |
| knowledge_changed 標註 | ❌ 不存在 | **新功能** |
| stagnation_warning | ❌ 不存在 | **新功能** |

### Requirement 6：閾值校準驗證

| 需求項 | 現有實作 | Gap |
|--------|---------|-----|
| 使用相同閾值 | ✅ 回測走 `/api/v1/message` 正式 API | **無 gap** |
| 記錄閾值到 metadata | ❌ backtest_runs 無 metadata/config 欄位 | **小 gap**：可用 notes 或新增 JSONB 欄位 |
| perfect_match 觸發比例驗證 | ❌ 不追蹤 optimization_method 分布 | **新功能** |
| 閾值異常警告 | ❌ 不存在 | **新功能** |

---

## 3. 核心決策點：「答案品質」該怎麼定義？

這是本規格最關鍵的問題。現有三套定義各有局限：

### 選項 1：沿用 confidence（檢索品質代理指標）

**做法**：維持 `evaluate_answer_v2` 現有公式，僅補充 `vector_similarity` 等欄位記錄。

- ✅ 零成本、零延遲增加
- ✅ 與現有回測結果可直接比較
- ❌ **不衡量答案內容品質**（confidence 高不代表答案好）
- ❌ 無法偵測「高 confidence + 模糊答案」的情況

**適用場景**：只需確認 retriever 重構不影響回測判定

### 選項 2：啟用 LLM 評審（detailed mode）

**做法**：回測切換到 `quality_mode = 'detailed'`，啟用 GPT 對每題答案做 1-5 分評審（relevance, completeness, accuracy, intent_match, quality_overall）。

- ✅ 直接評估答案內容品質
- ✅ DB schema 已存在，不需改表
- ❌ **成本高**：每題多一次 GPT 呼叫（50 題 ≈ 50 次額外 API call）
- ❌ 速度慢：回測時間翻倍
- ❌ LLM 評審本身有不穩定性

**適用場景**：品質要求高的里程碑驗證（非日常回測）

### 選項 3：規則式答案品質檢查（混合模式）

**做法**：在 `evaluate_answer_v2` 中新增**規則式品質檢查層**，不呼叫 LLM，用字串匹配/正則偵測品質問題：

```
品質檢查項目：
1. 模糊答案偵測：包含「請洽客服」「視情況而定」「依合約規定」但無後續步驟 → quality_warning
2. 答案長度檢查：< 20 字且非表單觸發 → too_short
3. 答案來源追蹤：從 response_metadata 萃取 optimization_method → answer_source
4. 重複內容偵測：答案中同一句話重複出現 → repetitive_content
```

- ✅ 零額外 API 成本
- ✅ 確定性（不受 LLM 隨機性影響）
- ✅ 可與 confidence 並行，不影響 pass/fail 判定
- ❌ 規則有限，無法偵測語意層面的品質問題
- ❌ 需要持續維護規則

**適用場景**：日常回測的輕量品質篩查

### 選項 4：分層品質模式（推薦）

**做法**：保留 `quality_mode` 三層架構，強化每一層：

| 模式 | 日常回測 | 里程碑驗證 | 品質深度 |
|------|---------|-----------|---------|
| `basic`（預設） | ✅ | - | confidence + 規則式品質標記 |
| `hybrid` | - | ✅ | confidence + 規則式 + 抽樣 LLM 評審（20%） |
| `detailed` | - | ✅ | confidence + 規則式 + 全量 LLM 評審 |

- ✅ 日常回測零額外成本
- ✅ 里程碑驗證有深度品質分析
- ✅ 與現有 quality_mode 機制對齊
- ❌ hybrid 模式需新實作

---

## 4. 現有程式碼關鍵位置

| 檔案 | 行號 | 用途 | 需變更 |
|------|------|------|--------|
| `scripts/backtest/backtest_framework_async.py` | 540-552 | max_similarity 取值 | 需新增 max_vector_similarity |
| 同上 | 574-579 | confidence 公式 | 公式不變，需新增 score_fields_used |
| 同上 | 597-728 | evaluate_answer_v2 完整邏輯 | 需新增規則式品質檢查 |
| 同上 | 719-728 | evaluation dict 輸出 | 需擴充欄位 |
| 同上 | 165-189 | debug_info → sources 注入 | ✅ 已處理 vector_similarity |
| `rag-orchestrator/services/confidence_evaluator.py` | - | 生產 confidence 計算 | 不需變更（保持一致） |
| `rag-orchestrator/services/knowledge_completion_loop/gap_analyzer.py` | 129-183 | 失敗分類 | 需新增 persistent_failure |
| `rag-orchestrator/services/knowledge_completion_loop/backtest_client.py` | 73-182 | 回測執行與結果記錄 | 需擴充摘要統計 |
| `rag-orchestrator/services/knowledge_completion_loop/knowledge_generator.py` | 38-95 | 知識生成 prompt | 不需變更（品質定義在 prompt 中） |
| `rag-orchestrator/services/knowledge_completion_loop/sop_generator.py` | 71-153 | SOP 生成 prompt | 不需變更 |

---

## 5. 實作複雜度與風險

### 整體評估

- **Effort**：**M**（3-7 天）— 主要工作在 evaluate_answer_v2 擴充與回饋閉環邏輯，無架構變更
- **Risk**：**Medium** — 核心風險在「答案品質定義」的決策會影響所有下游邏輯；規則式品質檢查的維護成本需評估

### 按需求分解

| 需求 | Effort | Risk | 說明 |
|------|--------|------|------|
| Req 1：confidence 欄位對齊 | S | Low | 只需擴充 evaluate_answer_v2 |
| Req 2：pass/fail 一致性 | S | Low | 邏輯不變，需新增 baseline 比較 |
| Req 3：新分數欄位記錄 | S | Low | 擴充 evaluation dict + 摘要統計 |
| Req 4：答案品質評估 | M | **Medium** | 核心決策：用哪套品質定義 |
| Req 5：回饋閉環 | M | Medium | 需跨迭代比對歷史數據 |
| Req 6：閾值校準 | S | Low | 記錄 + 警告邏輯 |

---

## 6. 推薦方案

### 設計階段優先決策

1. **答案品質定義**：建議採用**選項 3（規則式品質檢查）**作為 `basic` 模式的預設行為，日常回測零額外成本；選項 4（分層模式）作為完整規劃但可延後 hybrid/detailed 強化
2. **品質指標與 pass/fail 的關係**：建議品質檢查結果**只標記不改判定**（quality_warning 欄位），避免影響現有 pass_rate 基線
3. **Requirement 4 需求調整建議**：「完整性/準確性/可操作性」三維度在規則式模式中難以完整實現，設計階段需降級為可行的規則集

### 設計階段研究項目

- [ ] 確認 `optimization_method`（perfect_match / synthesis / template / llm）是否已在 response_metadata 中回傳，可直接萃取為 `answer_source`
- [ ] 確認 `backtest_runs` 表是否需要新增 JSONB 欄位（metadata/config），或可沿用現有 `notes` 欄位
- [ ] 盤查 `quality_mode = 'hybrid'` 是否有現成實作或只是 schema 佔位
- [ ] 評估跨迭代 persistent_failure 查詢的效能（需 JOIN backtest_results + knowledge_gap_analysis）
