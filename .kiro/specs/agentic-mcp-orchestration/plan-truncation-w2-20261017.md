# 計畫草稿：W2 主模型輸出失控（截斷）處置（2026-10-17）

> ⚠️ **草稿、未審**。送審時機：W1c 驗收通過後（W1c 會讓寫入回合不經主模型，截斷基準要在 W1c 之後重量）。
> 業主原話（2026-10-17）：「也這樣改 ?」（回應「模型輸出失控：另外用上限、重試或備援模型來兜底」）、「好 先起草 W2 和查詢的計畫」。
> 驗收清單草稿：`acceptance-truncation-w2-20261017.md`

## 0. 現況（已對碼／實測）

| 事實 | 查證 |
|---|---|
| gpt-oss 截斷頻率：W1b 實測 54 回合中 10 回合 `llm_output_truncated`，其中 8 回合最後轉人；gpt-6-luna 0/54 | `~/jgb-archive/bedrock-eval-20261017/w1/{R,D,T,P}_{A,B}.json` 的 `snap.violations` |
| 截斷成因：strict JSON 內灌空白換行直到輸出上限（第一片已設上限 2000） | DSP-080；`.claude/decisions/DSP-080.md`「約 5% 呼叫灌空白換行至上限」；`rag-orchestrator/services/agent/runtime.py` `DEFAULT_MAX_COMPLETION_TOKENS` |
| 現行處置：截斷只記旗標，輸出照 SCHEMA 解析失敗路徑走——**把截斷的原文附回 messages**＋改寫提示，再叫同一個模型；改寫上限 `max_rewrites=2`，用完 ⇒ `budget_exhausted` 固定句 | `grep -n "LLM_OUTPUT_TRUNCATED\|rewrite_feedback(\"SCHEMA\"" rag-orchestrator/services/agent/runtime.py`；`rag-orchestrator/services/agent/budget.py` `max_rewrites` |
| 截斷一次耗時 14～32 秒（輸出 2000 token 的時間） | 同上 JSON 的 `s` 欄 |
| 正常輸出 p99 1,408 token、最大 1,871（gpt-oss）；gpt-6-luna 最大 333 | `runtime.py` `AgentRuntime.__init__` 註解（plan-oss-slice1 量測） |

## 1. 業界做法（已渲染或標明未查）

- 輸出上限：已做（第一片）。
- 重試：只對偶發錯誤有效；能力不足時重試無效（MLflow、TDS 文章——只看搜尋摘要）。
- 備援模型：主模型錯／逾時／屢次驗證失敗時轉備援；須防備援輸出格式悄悄不同（同上，只看摘要）。
- 約束解碼可能本身陷入迴圈（Outlines issue #690，已渲染）；Bedrock 上不可控。

## 2. 第 0 步：量測（不改 repo，先決定處置組合）

在評估容器以 shim（repo 外）做：
1. **重放**：截斷回合的完整請求（shim 在 `finish_reason=length` 時存請求，存 `~/jgb-archive/bedrock-eval-20261017/w2/`，⛔ 存金鑰）各重放 5 次，量：(a) 同請求立即重試成功率；(b) 不附截斷原文、只重送原請求的成功率；(c) `gpt-oss-20b`（IAM 已開）成功率與品質；
2. **早停偵測可行性**：串流（`stream=True`）下偵測「連續空白／換行超過 N 字元」即中止，量中止前耗時與誤殺率（正常輸出是否也有長空白）。
3. 樣本：v2 題庫 30 題 ×2 輪＋R／D／T 腳本各 3 輪（gpt-oss）。

產出 `w2/STEP0.md`：各處置的救回率、延遲、成本，交業主選組合。

## 3. 處置候選（第 0 步後定案）

依序串接，每一步都有上限：
1. **早停**（若第 0 步證實可行）：串流偵測失控即中止，不等滿 2000 token。
2. **乾淨重試一次**：⛔ 把截斷原文附回 messages（現行做法會把 2000 token 空白塞回上下文）；以原請求重送一次。
3. **備援模型一次**：候選 `gpt-oss-20b`（IAM 已開）；Gemma 3 27B（IAM 待申請）；⛔ gpt-6-luna（閉源，與 DSP-080 方向衝突；驗收亦只量 gpt-oss，DSP-086）。
4. 仍失敗 ⇒ 現行固定句／轉人。
- 截斷回合記 violation：`llm_output_truncated`、`llm_retry_clean`、`llm_fallback_model:<名>`（固定字串）。

## 4. 不做

- 換掉主模型（DSP-080 方向不變）。
- 改知識章節選取、Verifier 規則。
- 寫入流程（W1c 已讓寫入回合不經主模型）。

## 5. 待業主決定（送審前）

- 備援模型選哪個（第 0 步數據出來後）。
- 早停若需要串流，是否接受改 `_next_model_message` 為串流呼叫。

## 6. 用量回報

不設 token 上限；每片收尾回報實際用量（子代理 token 加總＋Bedrock 費用估算）；停點只用結果條件。
