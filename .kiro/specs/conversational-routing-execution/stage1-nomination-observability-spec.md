# Stage 1｜Production Nomination Observability（實作規格）

> **在不收集使用者原文、不改 routing 行為的前提下，記錄 retrieval top1 的 KB 身分與
> categories，以及 responsibility resolver **之前**實際產生的 nomination candidates，
> 以定位 production routing funnel 的結構性斷點。**

- 日期：2026-08-29｜性質：**observability prerequisite**，⛔ 不是 architecture acceptance
- R7（不存原文）**完全不動**。Stage 2 若真需要原文，另開正式 privacy decision。

## 一、Claim ceiling（先鎖，免得三天後統計被過度解讀）

```text
✅ 能回答：production routing machinery 的 nomination observability／failure distribution
❌ 不能回答：
   「沒有 nomination 的 query 有多少其實應該進 Face？」
   「candidate 是不是正確的 Face？」
   「production nomination recall 是多少？」
   「categories 的 responsibility coverage 好不好？」
   「instance query 有多少被漏掉？」
   「single/dialog 架構是不是正確？」
⇒ 看到「30% candidate=[]」只能說
   **「30% 沒產生 Face nomination」**，⛔ 不得說「漏掉 30%」——後者需要 ground truth。
```

## 二、欄位（**4 個，不是 3 個**）

實查後追加第 4 個：現有 `processing_path` **無法**分辨進場來源
（`conversational` 1,849 筆把「分類路由／trigger 直達／Step 0.5 圖片改道／既有 session」
全部混在一起），I8 因此不可能用既有欄位滿足。

```text
top1_knowledge_id            nomination 判斷**當下**所用的 top1 KB row id；無 top1 → null
top1_categories              同一 top1 row 在**當下**讀到的 categories，正規化陣列；無 → []
nomination_candidate_facet_keys
                             retrieval/category nomination 層實際提出的 Face candidates，
                             **尚未經 responsibility resolver**；無候選 → []
entry_source                 normal_classification｜trigger_direct｜vision_redirect｜
                             existing_session｜transaction_form
                             （I8 用；⛔ 不得由 processing_path 反推）
```

⛔ `nomination_candidate_facet_keys` **不得**偷寫成 resolver candidate 或 committed facet
——Stage 1 的全部意義就是把 `nomination → responsibility resolution → commit` 三段分開（裁定 001）。

## 三、寫入點（**鎖在決策發生的地方，不得事後反推**）

### A. retrieval fact

在「本次 nomination 使用哪個 top1」確定之後**立刻** capture。

⚠️ **不得**用以下之後的 row 回填——execution order 已踩過一次：
`_drop_empty_answer_rows`／`_top1_relevance_gate`／direct-answer reranking
（Face nomination 在 `_top1_relevance_gate` **之前**）。

### B. nomination fact ——⚠️ 需要一次**行為中性**的重構

現行 `_diagnosis_config_for_knowledge` 把提名與裁決**交錯**，且**第一個 commit 就短路返回**：

```python
for cat in _knowledge_category(best_knowledge):
    cfg = await config_for_category(db_pool, cat)      # ← 提名
    if cfg is not None:
        if _instance_hint_suppressed(decision, cfg): continue
        _resolved, _authority = await _resolve_pre_commit_candidate(...)  # ← 裁決
        if _resolved is not None: return _resolved, _authority            # ← 短路
```

⇒ 今天**觀察不到完整候選集**。實作須改成兩段：

```text
第一段  逐 category 取 config，收齊 candidate 清單 → capture nomination_candidate_facet_keys
第二段  依**原順序**跑 suppression ＋ resolver，first-commit-wins 語義**逐字不變**
```

⚠️ 這是行為中性重構，但**必須證明**：沿用刀 A 的做法——逐形狀等價測試 ＋ mutation，
⛔ 不得只靠「看起來一樣」。

即使 resolver 最終為 `stay`／`switch`／`technical_fail_open`／`guard`／`no commit`，
`nomination_candidate_facet_keys` **一律不得被覆寫**。

## 四、不變量（8 條）

```text
I1  nomination ≠ commit
    ⛔ **不得**寫成 `committed_facet ∈ nomination_candidate_facet_keys`——
    authoritative delegation（bill_diagnosis→billing_anomaly→contract_closeout）
    會使最終 committed Face 不等於最初 nomination。寫了就直接違反現行 responsibility chain。
I2  resolver 若被呼叫，其 seed candidate 必須能追到 nomination 或其他 explicit entry source
I3  空陣列有語義：`null` = telemetry unavailable／未 instrument；`[]` = 已 instrument 且零候選
    ⛔ 兩者混用會污染「無 nomination 比例」
I4  categories 與 top1 必須同一個 retrieval snapshot（⛔ 不得 A 的 id 配 B 的 categories）
I5  ⛔ 不存任何 query 派生文字（query_tokens／matched pattern／normalized utterance／
    identifier text）——那會偷偷跨進 R7／Stage 2 的隱私面
I6  telemetry 失敗 ≠ routing 失敗：serialization／DB insert／categories malformed
    一律不得改變 production answer path（沿用既有 fire-and-forget）
I7  unknown category 保真：top1 categories 內若有目前無 Face mapping 的 category，
    **保留原 category、candidate = []**，⛔ instrumentation 層不得自行 drop
    ——「category 存在但沒有 candidate」正是最想量的 failure shape
I8  entry source 必須能分群，統計時排除 existing_session／trigger_direct／
    vision_redirect／transaction_form；否則 `facet_key` 有值可能根本不是 nomination 造成的
```

## 五、第一批 report：deterministic funnel

```text
normal_classification requests
  → 有 retrieval top1？          否 → S1 no_top1
  → top1 有 categories？          否 → S2 top1_but_no_categories
  → categories 產生 candidate？   否 → S3 categories_but_no_nomination
  → candidate 進 resolver 後 authoritative commit？
                                  否 → S4 nomination_but_no_authoritative_commit
                                  是 → S5 authoritative_commit
```

以前「沒進 Face」全部混在一起；現在可分辨**卡在 retrieval／metadata／nomination mapping／responsibility**。

### 兩張交叉表

```text
① category → nomination
   category｜requests｜candidate=0｜candidate>0
   抓：production top1 明明帶某 category，mapping 卻從未產生 candidate
   ⚠️ 仍不能說這些 query「本來應該」進 Face
② nominated candidate → resolver result
   candidate｜model stay｜model switch｜technical_fail_open｜no commit
   ⚠️ 一律讀既有的 `decision_source` / `has_commit_authority`，
      ⛔ 不得重新用 `stay=true` 猜 authority（裁定 001 ④）
```

## 六、實作前的兩個 deterministic guard

```text
正對照  已知 query → 已知 top1／categories → 期望提名 bill_diagnosis
        assert telemetry 記到的**正是**那一組
突變    故意移除某 category→facet mapping
        → nomination_candidate_facet_keys 必須由 ["bill_diagnosis"] 變 []
⇒ 證明 instrumentation 真的在量 nomination，而**不是事後從 commit state 抄答案**。
（「沒有分歧」這類否定結論，量尺必須先證明咬得動——本 repo 已有此規約。）
```

## 七、Stage 1 能先回答的那個結構性問題

即使不能量正確性，它能驗一個**必要條件**：

> **retrieval + category 這套 mechanism，在真實 production traffic 上到底有沒有足夠 support。**

```text
若 top1_categories 非空 10,000 requests，其中 9,000 candidate=[]，
且大量 categories 根本沒有任何 Face mapping
⇒ 無需 user utterance 即可證明：現行 category→candidate architecture 的**可作用範圍極其有限**
  （structural fact，非 semantic correctness claim）
反之，若多數 relevant category 都有 candidate
⇒ Stage 2 才值得把問題收斂到「candidate 是否語義正確」
```

## 八、順序

```text
Stage 1 contract（本檔）
→ deterministic telemetry implementation（含兩段式重構的等價證明）
→ positive ＋ mutation controls
→ production accumulation
→ machine-side funnel analysis
→ **再決定** Stage 2 privacy 是否值得付出
```
