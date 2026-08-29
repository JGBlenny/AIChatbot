# R10-C2-v1 契約（業主凍結 2026-08-30）＋ ⛔ 一個開工前的阻斷發現

## ✅ 阻斷已解除（2026-08-30 業主裁定 C2-SCORE）——原始發現保留於下

```text
C2-SCORE 裁定
  建立 **30 個 reviewed_active canonical responsibility embeddings**
  final score 仍為 0.1 * canonical responsibility vector similarity
                 + 0.9 * canonical responsibility reranker similarity
  ⛔ row／alias vector score 僅用於 nomination，**不得進 final score**
⚠️ 業主明示收回上一輪「C2-v1 不建 canonical embeddings」的裁定——
   那是建立在「final score 不硬性依賴 vector」的**錯誤前提**上，production fact 已推翻該前提。
```

選這條路的理由（業主）：同時做到 ⛔ 不把 nomination evidence 偷渡成 semantic authority、
⛔ 不改既有 0.1／0.9 policy、⛔ 不引入 rerank-only 新 calibration，
且 **vector 與 rerank 都在同一個 authority unit：responsibility canonical**。

### canonical embedding 的角色鎖死

```text
row／alias embeddings              → nomination ／ recall
canonical responsibility embeddings → **collapse ＋ top20 之後**的 final semantic vector component
⛔ C2-v1 ⛔ 不新增 canonical vector recall arm（否則同時改 recall architecture，因果變髒）
```

### 30 個，不是 31 個

```text
建 30 個 reviewed_active；⛔ 不建 historical（3498）、⛔ 不建 16 個 unresolved rows
embedding 是 sealed Registry V2 的 **derived runtime artifact**，⛔ 不是 authority source
⇒ ⛔ 不得回寫 registry-v2.json
綁定：registry_v2_digest／responsibility_id／canonical_text_digest／
      embedding_model_id+version／embedding_dimension／embedding
重建條件：canonical text 改 ｜ Registry authority epoch 改 ｜ embedding model 改
```

---

## ⚠️ 對先前 contract 的**有 provenance 的修正**（2026-08-30）

```text
previous uniform-threshold statement:  **REFUTED_BY_PRODUCTION_FACT**
   舊寫法「responsibility.nomination_score >= 0.3」把 threshold 當成一律適用——
   但 production 實況是：**vector 路徑套 0.3、keyword_fallback 明確豁免**。
replacement:  **C2-NOMINATION-ADMISSIBILITY-1**
   A responsibility is nomination-admissible iff
       has_keyword_nomination
       OR best_vector_nomination_score >= 0.3
   ⇒ keyword fallback → threshold exempt；vector only → >= 0.3（與現行 row policy 一致）
```

⚠️ 舊句**不刪**，標記為 REFUTED 保留 provenance——⛔ 不得悄悄改寫舊文。

### collapse 後必須保留的三個 nomination facts

```text
has_keyword_nomination        = ANY contributing row came from keyword_fallback
has_vector_nomination         = ANY contributing vector row passes existing vector admissibility
best_vector_nomination_score  = MAX admissible contributing vector-row score
⚠️ 最後一項的 MAX **仍只是 nomination evidence**。
```

### top20：keyword **responsibility** 優先，⛔ 不是 keyword row 優先

```text
keyword_priority = has_keyword_nomination
一個 responsibility 同時由 keyword row A ＋ vector row B 提名
  → **ONE** candidate、keyword_priority=true —— ⛔ 不是兩票
順序：① keyword-priority responsibilities ② vector-only responsibilities
      ③ 補到 20 個 **distinct** responsibilities
```

混合來源 ⛔ 不加權：`R-X` 由 keyword alias1 ＋ vector .82 ＋ vector .71 提名 ⇒
`keyword_priority=true／best_vector_nomination_score=.82／candidate_count=1`。

### keyword bucket 內部排序：preserve-existing-order，⛔ 不發明新 score

```text
best_keyword_source_rank = earliest／highest-priority contributing keyword row
                           under the **existing pre-collapse selector ordering**
現有若為 stable input order → 取 contributing keyword rows 的**最小原始 ordinal**
現有若已有明確 keyword rank key → 沿用該 key
⛔ 不新造「keyword score」、⛔ 不 SUM／MAX keyword aliases
vector-only bucket → 沿用既有 vector selection ordering，取最佳 admissible contributor，⛔ 不相加
```

> **collapse 可以消除重複，⛔ 但不能趁機重新定義 keyword relevance。**

---

## 附加 guards（業主 2026-08-30 新增）

```text
G7 final-vector authority   同 query／同 responsibility，任意改 contributing alias vector score
                            但不改 canonical embedding → final responsibility_vector_similarity
                            **MUST NOT change**（直接防 alias score 偷渡）
G8 keyword exemption survives collapse
                            只有 keyword_fallback contributor、row vector=0
                            → responsibility 仍 admissible，⛔ 不得被 .3 丟掉
G9 mixed-source collapse    同責任同時 keyword ＋ vector → exactly 1 candidate、
                            keyword_priority=true、⛔ 無重複 slot
G10 canonical embedding completeness
                            30 reviewed_active ＝ 30 embeddings；canonical text digest 逐字相符；
                            model／version 相符；historical ＝ 0 —— 漏一筆／text drift／model drift 皆紅
M5 把 final vector 改回 max(contributing row vector) → **G7 必紅**
```

## R7.2 ／ SCORE_SHIFT_PROBE 必須版本化

```text
old probe unit = row        new probe unit = responsibility
⇒ **R7.2 舊量測 ⛔ 不得直接當 C2 responsibility score 的 calibration baseline**
⛔ 不刪舊 probe、⛔ 不改寫舊結論；新增標記：
    score_unit     = responsibility
    score_contract = canonical-vector-0.1 + canonical-rerank-0.9
C2 上線前建立**新的** local baseline——公式形式雖仍是 .1／.9，但輸入的 semantic unit 已換，
絕對值平移本來就可能不同。
```

---

## 原始阻斷發現（保留，⛔ 不刪：它是 C2-SCORE 的觸發證據）

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
