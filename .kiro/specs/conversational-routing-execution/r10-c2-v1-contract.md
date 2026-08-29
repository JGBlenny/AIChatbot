# R10-C2-v1 契約（業主凍結 2026-08-30）＋ ⛔ 一個開工前的阻斷發現

## ⛔ 阻斷發現（先讀這段）

業主凍結的停止條件二**已經成立**：

> 「若實作盤查發現 downstream final score hard-coded 必須 `vector_score + rerank_score`，
> **先停**，⛔ 不要拿 alias vector score 冒充 responsibility semantic vector score。」

唯讀實查：

```text
rag-orchestrator/services/base_retriever.py:584-586  _finalize_scores 分支一
    if rerank is not None:
        r['similarity'] = 0.1 * vector + 0.9 * rerank
        r['score_source'] = 'rerank'
```

⇒ **最終 similarity 硬性含 `vector_similarity` 的 10% 權重。** collapse 之後，一個
responsibility 手上唯一可得的 vector 值就是「某個 contributing row 的 recall 分數」——
把它填進這條公式，就是業主明文禁止的：

```text
⛔ final score += alias score
⛔ 默默把 alias nomination score 塞進 final similarity
```

**故 C2-v1 的 Stage 3–5 ⛔ 不得開工**，直到 `C2-SCORE` 另案裁定
（responsibility-level vector semantic scoring 要不要成立、是否為此建立 30 個 canonical embeddings）。

⚠️ 這**不是**建議改公式；改不改是業主的裁定。本檔只記錄阻斷條件已觸發。

---

## 一、業主正式裁定（原文保真）

```text
C2-v1 threshold        = 0.3 UNCHANGED
C2-v1 input limit      = 20  UNCHANGED
collapse nomination score
                       = MAX contributing alias/member recall score
                       = **nomination evidence ONLY**
responsibility embeddings  = DO NOT BUILD ／ DO NOT REBUILD for C2-v1
row embeddings             = retain for recall
canonical responsibility text = **sole** responsibility-level semantic reranker surface
```

理由：C2 這一刀只回答「**把 candidate unit 從 row 改成 responsibility，並在 threshold／
truncation 前 collapse，是否正確接線？**」。同時調 threshold 或 top-k，之後任何差異都無法乾淨歸因。

```text
BEFORE  row candidates → threshold .3 → top20 rows          → rerank rows
AFTER   row/alias recall → **collapse** → threshold .3 → top20 responsibilities
                                                            → rerank responsibilities
```

### 0.3 的語義正式定義為 nomination threshold

collapse 後每個 responsibility 必須同時保留**兩種完全不同**的分數：

```text
nomination_score = MAX(boosted recall score of its contributing rows)
semantic_score   = canonical reranker score
```

`nomination_score` **只用於**：0.3 門檻、top20 提名截斷。
⛔ 不得用於：最終 semantic authority／responsibility 間最終排序／與 canonical reranker score 加總／alias 數量加權。

⚠️ 這裡的 `MAX` 合法，是因為先前禁止的是「`max(alias score)` 成為**最終 semantic authority score**」。
現在它只回答：**至少有沒有一個 entry surface 足以把這個 responsibility 提名進來？**
且 **5 個 alias ⛔ 不會比 1 個 alias 多五票**。

### multi-membership row 同規則

3511 命中時可同時 nominate R-08／R-09／R-03／R-04——這是 P4 已確認的
「一個 row 可對 1..N responsibilities 提供 nomination evidence」，
⛔ 不是 voting amplification；每個 responsibility 最後**仍只是一個 candidate**。

### 為什麼 C2-v1 ⛔ 不建 responsibility embeddings

目前 canonical 的 semantic authority 路徑是 `canonical text → reranker`，
⛔ 不是 `canonical embedding → vector retrieval`。現在替 30 個責任建 embedding 並讓它參與 scoring，
等於偷偷新增一條 `canonical vector semantic score`，並立刻撞上尚未裁過的問題：

```text
alias recall score ／ canonical embedding score ／ canonical rerank score —— 三者怎麼融合？
```

⇒ 不在 R10 frozen decision 內。且 ⛔ **不得拿 canonical 取代 row embedding**，否則等於把 C2 滑回 C1
（把 lexical／alias recall surface 拿掉）。

需要 responsibility embeddings 的情況只有兩種，皆另案：
① 未來要讓 canonical 本身參與 vector recall；② final score formula 硬性要求 post-collapse vector score。
**⚠️ ② 已於本次盤查證實成立 —— 見開頭阻斷發現。**

## 二、C2-v1 五階段契約

```text
Stage 1 Recall              既有 row embeddings ＋ keyword fallback／boost —— UNCHANGED
Stage 2 Responsibility 映射  row_id → 0..N responsibility_ids
                            ⚠️ unresolved／historical rows ⛔ MUST NOT 產生 active semantic
                               authority candidate；⛔ 不得因缺 responsibility_id 就自動創一個
Stage 3 Collapse            group by active responsibility_id
                            nomination_score = MAX(contributing boosted row scores)
                            alias／member count → **no weight**
Stage 4 Nomination 過濾      nomination_score >= 0.3 → 再取 top 20 **RESPONSIBILITIES**
Stage 5 Semantic authority   rerank(query, responsibility.canonical_responsibility)
                            semantic_score = canonical reranker score
禁止：final score += alias score／final score *= alias count／semantic_score = max(alias scores)
```

## 三、第一批 deterministic guards（業主指定）

```text
G1 alias collapse      3939＋3940 同時 recall → reranker input **只能有 R-28 一筆**
G2 no voting weight    同責任第二個 alias hit → 可提高／保持 nomination evidence，
                       ⛔ 不得增加 candidate 數、⛔ 不得直接增加 semantic score
G3 slot recovery       同責任多 alias 原佔 2 個 top20 slots → collapse 後只佔 1，
                       第 21 名的另一 responsibility **應有機會進 top20**
                       （這條正面驗證 C2 真正要解的 production defect）
G4 multi-membership    3511 hit → nominate 恰好 R-08／R-09／R-03／R-04，⛔ 不產生 responsibility_3511
G5 historical          3498 hit／mutation fixture → ⛔ 不得形成 active responsibility candidate
G6 unresolved          3512／3513／4255 等 → ⛔ 不得自動生成 authority responsibility candidate
```

### mutation（guard exists ≠ guard can fail）

```text
M1 collapse 移到 top20 之後            → slot-recovery guard 必紅
M2 改用 SUM(alias scores)              → voting-weight guard 必紅
M3 row id 自動 fallback 成 responsibility_id → unresolved guard 必紅
M4 reranker 仍吃 row representation／summary 而非 V2 canonical → canonical transport guard 必紅
```

## 四、A05 仍不開

C2 完成後還須證明
`DB／registry V2 → row-responsibility mapping → collapse → canonical transport → reranker`
是**真的 production path**，⛔ 不是 hand-crafted fixture。屆時才清除
`A05.current_blocker = TARGET_CANDIDATE_NOT_IMPLEMENTED`，然後 freeze 全新 A05 protocol。

## 五、現行程式的其他接線事實（唯讀盤查，供 C2-SCORE 裁定參考）

```text
base_retriever.py:298-299  RERANKER_INPUT_LIMIT=20／RERANKER_MIN_VECTOR_SIMILARITY=0.3 讀 env
base_retriever.py:300-340  兩層過濾：① vector 項 <0.3 丟棄（keyword_fallback **不受下限影響**，
                           其 vector_similarity=0 是「走 keyword 路徑」的設計預設值，⛔ 非低相關）
                           ② 超過 20 筆時**優先保留 keyword_fallback**，再以 vector_similarity 補足
base_retriever.py:352      _finalize_scores（融合出口，⚠️ SCORE_SHIFT_PROBE 探針也掛在這裡）
base_retriever.py:357-367  threshold 過濾 → 依 similarity 排序 → top_k
base_retriever.py:410      keyword_boost 上限 1.0–1.3（最多 30%），⚠️ 分支一（rerank）**不套 boost**
```

⚠️ 第 ② 點對 C2 有直接影響：現行截斷規則是**以 row 為單位**且對 keyword_fallback 有優先權；
collapse 到 responsibility 後，「優先保留 keyword_fallback」要怎麼在責任層表達，
⛔ 尚未在 frozen contract 內定義——這是 C2-v1 開工前的第二個待裁點。
