# R10 決策紀錄 ＋ R10-P responsibility population review 設計（2026-08-29）

## 一、正式決策（業主裁定，四題綁成一個決策）

```text
R10-Q1  A per-row  = REJECTED_AS_TARGET
        B per-facet = REJECTED_AS_TARGET（locally representable only）
        C explicit responsibility_id = **SELECTED_TARGET_ARCHITECTURE**
        collapse variant = **C2**

R10-Q2  ALIAS_ROLE = NOMINATION_ONLY（⛔ no semantic authority、⛔ no voting weight）

R10-Q3  APPLICABILITY_AUTHORITY = **RESPONSIBILITY_LEVEL**；alias rows 繼承

R10-Q4  RESPONSIBILITY_REVIEW_REQUIRED —— 在任何 schema／scoring migration **之前**
        automatic facet／row clustering = **proposal only, never authority**
```

### B 被淘汰的理由是 **current production-domain fact**，⛔ 不是 future-proofing

```text
facet = late_fee
  responsibility A  late_fee_mechanism_general   applicability = general（3531／3532）
  responsibility B  late_fee_instance_diagnosis  applicability = instance（3939／3940）
⇒ 同一 facet 內**已經**存在相反的 authority semantics ⇒ facet ≠ responsibility
```

### C2 的 target pipeline（切點已對齊現行斷點）

```text
query
→ row/alias recall
→ embedding ／ keyword fallback ／ keyword boost
→ map row → responsibility_id
→ **collapse responsibility candidates**
→ threshold
→ top-N truncation
→ canonical responsibility representation rerank
→ responsibility candidate
→ authority ／ routing
```
⚠️ collapse 放在 boost 後、**threshold／truncation 之前**（比「reranker 前」更精確）。
理由：它要防的不只是 reranker 內部競爭，而是
**同 responsibility 的多個 alias 在真正 semantic scoring 前就先吃掉有限的 candidate slots**
（現行 `RERANKER_MIN_VECTOR_SIMILARITY=0.3` 下限與 `RERANKER_INPUT_LIMIT=20` 截斷就在那裡）。

### ALIAS_ROLE 的正式語義（架構不變量，⛔ 非 implementation preference）

```text
ENTRY_ALIAS MAY       貢獻 lexical recall／embedding recall／keyword match；
                      使某 responsibility **進入** candidate set
ENTRY_ALIAS MUST NOT  定義 canonical semantic responsibility
                      獨立取得 commit authority
                      獨立參與 semantic reranking
                      因 alias 數量較多而取得額外權重
```
> **alias 的分數只能回答「這個 responsibility 要不要被考慮」，
> ⛔ 不能回答「這個 responsibility 有多正確」。**

⇒ collapse 時 ⛔ 不採 `sum` ／ `average` ／ count-weighted；
⚠️ 連 `max(alias score)` 也**只**適合當 recall evidence，⛔ 不得成為最終 semantic authority score。

```text
alias hit              → RESPONSIBILITY_NOMINATED
canonical representation → RESPONSIBILITY_SEMANTIC_SCORE
（兩種證據來源分開）
```

### applicability 上移的遷移限制

```text
responsibility declaration = **authoritative**
row declaration            = inherited ／ historical compatibility
⛔ 現在**不要**刪 row-level declarations —— 仍是「失效不失憶」。
   等 population migration 完成、invariant 穩定後再考慮移除 legacy authority。
```

### 終局 invariant（R10 收口時取代 TRANSITIONAL_GUARD 16）

```text
ENTRY_ALIAS MUST reference exactly one active responsibility_id
ENTRY_ALIAS MUST NOT own authoritative retrieval_representation
ENTRY_ALIAS MUST NOT own authoritative applicability
canonical retrieval_representation MUST belong to responsibility
applicability MUST belong to responsibility
multiple aliases of same responsibility
  MUST collapse before threshold／truncation／reranking
```

---

# 二、R10-P：responsibility population review 設計（⛔ 本文件不執行）

## 為什麼 review 是 **必要前置**，不是 nice-to-have

```text
C 把風險從「某一 row 分錯」放大成
「某個 responsibility 定義錯 → aliases → representation → applicability
 → scoring → routing **全部一起錯**」
⇒ responsibility_id ⛔ 不得由「同 facet 自動 group」「同 Face 自動 group」
  「相似 summary 自動 cluster」任一種直接生成——那些只能是 **proposal evidence**。
```

## Scope（機械界定，實查）

```text
LEVEL_A_V1                10 筆（含已退役的 3498）
ENTRY_ALIAS registry      12 筆
APPLICABILITY_DECLARED    44 筆
UNION（去重）             **54 筆**  ← R10-P 的母體
```
⚠️ 母體以**機械聯集**界定，⛔ 不看內容挑；日後擴充需另立 scope 決策。

## Review contract（每個 responsibility 必備欄位）

```text
responsibility_id
canonical responsibility statement
applicability               general ／ instance ／ …
owner                       Face ／ Knowledge ／ downstream capability
member rows                 answer rows ／ entry aliases
evidence                    · original authoring spec
                            · deterministic capability
                            · reviewed answer responsibility
                            · provenance commit ／ batch
review_status ／ reviewed_by ／ reviewed_at
source_digest ／ evidence digest
```

### ⚠️ 最重要的一條

> **member rows 是結果，⛔ 不是 authority source。**

⛔ 不得因為 3939、3940 都叫 late_fee 就自動得到
`responsibility_id = late_fee_instance_diagnosis`。
我們現在敢這樣分，是因為**已經有四項獨立證據**：

```text
① H2 VARIANTS_BY_DESIGN（建立時「一種講法一筆」的明文）
② B sole-owner capability（T1 判 A 為 partial，Step 2 收斂）
③ positive instance declarations（T3 逐筆理由）
④ deterministic engine evidence（build_late_fee_facts 的實測輸出）
```
⇒ **這才叫 reviewed responsibility。**

## 執行順序（⛔ 不得顛倒）

```text
candidate responsibility grouping   （proposal，機械產生，⛔ 無 authority）
→ **human review**
→ authoritative responsibility registry
→ applicability migration
→ canonical representation population
→ retrieval implementation（C2 collapse）
```
⚠️ 若顛倒成「先建 responsibility_id → 自動搬 representation → 再人工看」，
就只是把 per-row 的人工分類錯誤**批次放大**。

## A05 的狀態與解鎖條件

```text
A05_STATUS = PAUSED_BEFORE_PROTOCOL_FREEZE
reason     = judgment unit（validation／scoring／applicability／authority 共用）尚未 review 完
```

⚠️ 先前那項旁證（A04 的 MULTI_OWNER 叢集全部落在 N 層、Level-A 9 rows 未撞到
alias cluster；4640／4656／4657 與 12 錨點**不同批**）是
**strong diagnostic evidence，⛔ 不能取代 responsibility census**。

```text
解鎖條件：R10-P 完成後若 census 顯示 LEVEL_A_V2 的 9 rows = 9 個相異 responsibility，
A05 的 denominator 可維持 9 ——
⚠️ 但理由會從「看起來沒有 aliases」升級成**機器可追溯的 responsibility census**。
```

## 底線

> **⛔ 我們不是把「row」換成另一個看起來更漂亮的欄位；
> 而是在重新定義 validation／scoring／applicability／authority
> 共同使用的 judgment unit。這個 unit 沒 review 完，A05 就不該開。**
