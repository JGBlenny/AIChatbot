# A03 protocol —— **已凍結**（2026-08-29，凍結於 corpus 生成之前）

⛔ 凍結後不得修改任何判準、不得補題、不得合併評估單位、不得擴 oracle。

## 0. 為什麼要有 A03

A02 把兩件事混成一個 truth：

```text
「這句話**表面上**能否判出 instance／general」
        ≠
「系統在 retrieval 選定某個 Knowledge 之後，gate 是否照契約正確執行」
```

⇒ A03 **分開授權**，⛔ 不硬塞成單一 PASS。

## 1. raw label space —— **四類**

```text
INSTANCE           必須讀該使用者自己的資料才能正確完成
GENERAL            不需要任何該使用者自己的資料
CONTEXT_DEPENDENT  **語言事實**：句子本身不足以唯一決定 intent，
                   須知對話脈絡或使用者當下 referent 才能判
UNDECIDABLE        **標註失敗**：標註品質不足／標註者無法判斷
```

⚠️ `CONTEXT_DEPENDENT` ≠ `UNDECIDABLE`，⛔ 不得混同。
⚠️ `LABEL_DISAGREEMENT` 是兩位標註者比較後的 **derived state**，
⛔ **不是第五個 raw label**。

## 2. Layer Q — derived states

```text
兩位皆 INSTANCE 或皆 GENERAL                        → SEMANTICALLY_JUDGEABLE
任一方判 CONTEXT_DEPENDENT，且**不存在** G↔I 實質衝突 → CONTEXT_DEPENDENT
真正的 G vs I 衝突                                   → LABEL_DISAGREEMENT
其餘（含 UNDECIDABLE）                               → UNDECIDABLE
```

## 3. Corpus（事前固定，⛔ 不補題）

```text
10 strata × 20 = 200
  G1–G3（general）      每組 20，不分子配額
  I1–I7（instance）     每組 **10 explicit ＋ 10 elliptical**（預先登記子配額）
     explicit    帶明示指涉：「我的／這張／編號 X」
     elliptical  自然省略：「帳單寄不出去是什麼原因」
```

⛔ **不採「全部加『我的／這張』」**——那只能建立 explicit-reference subset
authorization，claim ceiling 太窄，且等於為了讓 oracle 一致而改題目。

### ⚠️ `CONTEXT_DEPENDENT` **刻意不設下限**

```text
⛔ 不要求 elliptical 必須有多少比例被判成 context-dependent。
理由：那會從「不要為了 denominator 強迫自然語言變 instance」
      變成「為了證明 ambiguity 強迫 elliptical 一定要被標成 context-dependent」
      ——**一樣是讓測試資料迎合預期**。
⇒ elliptical 的四類分布**完整報告**，但不設門檻。
⚠️ 若 70 題 elliptical 全被一致判成 instance，表示這批 synthetic 沒有重現 A02 的歧義現象；
   claim 就**不得延伸到 context-dependent language**，⛔ 但不得因此偽造一個 failure。
```

## 4. `allowed_top1_ids`（沿用已凍結的一對一 oracle）

```text
G1 → 3402   G2 → 3406   G3 → 3519
I1 → 4640   I2 → 4656   I3 → 4657
I4 → 3495   I5 → 3496   I6 → 3498   I7 → 3499
```

## 5. 三個 verdict（⛔ 不合成單一 PASS）

```text
A03-LABELS      PASS ／ INCONCLUSIVE
A03-SEMANTIC    PASS ／ FAIL ／ INCONCLUSIVE
A03-AUTHORITY   PASS ／ FAIL ／ INCONCLUSIVE
```

## 6. 固定流程與判準（⛔ 順序不可調換）

```text
【1】integrity
     200/200、序號齊全、無重複、工具隔離（各恰一次 Read 自己的語料檔）

【2】label quality —— 直接在**四類 raw labels** 上計算
     L1 exact agreement >= 90%｜Cohen's κ >= 0.70
     ⛔ 禁止把 INSTANCE vs CONTEXT_DEPENDENT、或 CONTEXT_DEPENDENT vs UNDECIDABLE
        事後合併成 agreement
     L1 < 90% ／ κ < 0.70 ／ κ 因零變異 undefined → **A03-LABELS = INCONCLUSIVE**（整輪停）

【3】semantic corpus sufficiency（**implementation 執行前**）
     G1／G2／G3            各自 SEMANTICALLY_JUDGEABLE >= **15/20**
     I1–I7 **explicit**    各自 SEMANTICALLY_JUDGEABLE >= **8/10**
     ⛔ 不得 pooled 補足（三個 general 不得互補；七個 explicit 不得互補）
     任一不足 → **A03-SEMANTIC = INCONCLUSIVE ／ SEMANTIC_CORPUS_INSUFFICIENT**
     ⚠️ CONTEXT_DEPENDENT 不算 judgeable，**但它不是 label failure**；UNDECIDABLE 才是

【4】frozen implementation 首次執行（**BURN 點**）

【5】Layer A — retrieval semantic alignment
     評估單位＝**10 個 semantic evaluation units**：
       G1、G2、G3、I1-explicit … I7-explicit
     ⚠️ ⛔ **不是**「每個 stratum」——instance stratum 混了 elliptical，
        而 elliptical 明確不接受 semantic correctness 判定
     alignment = (top1 ∈ allowed_top1_ids[unit]) ÷ semantically_judgeable queries
     每一個 unit >= **80%**
     任一 < 80% → **A03-SEMANTIC = FAIL ／ RETRIEVAL_SEMANTIC_MISALIGNMENT**
     ⚠️ 用 **FAIL 不是 INCONCLUSIVE**：第【3】關已保證該 unit 有足夠可判資料，
        資料足夠仍低於預登記門檻，就是**被測 semantic retrieval 沒達標**

【6】ELLIPTICAL_AUTHORITY_EXERCISE_PRECONDITION（**implementation 執行後**才量）
     I1–I7 **elliptical** 各自：top1 ∈ frozen Level-A 10 rows >= **8/10**
     ⚠️ 它只代表「有足夠 ambiguous／elliptical queries 實際進入 P1f authority policy 的作用域」，
        ⛔ **不代表 retrieval 正確**
     任一不足 → **A03-AUTHORITY = INCONCLUSIVE ／
                  ELLIPTICAL_AUTHORITY_NOT_SUFFICIENTLY_EXERCISED**
     ⛔ **不得**寫成 RETRIEVAL_INSUFFICIENT——context-dependent query
        本來就沒有唯一的 retrieval semantic oracle

【7】Layer B — authority contract execution
     母體＝**所有** top1 ∈ frozen Level-A 的案例（含 general／explicit instance／
     context-dependent elliptical）
     expected：row declaration × frozen Face requirement
       row=instance + Face=REQUIRED → ELIGIBLE／retain
       row=general  + Face=REQUIRED → INELIGIBLE／suppress
     observed：實際 consumer routing action
     accuracy = **100%**；任一筆不一致 → **A03-AUTHORITY = FAIL ／ AUTHORITY_POLICY_FAIL**

     ⚠️⚠️ **evaluator 必須從 frozen truth 獨立推導 expected value，
     ⛔ 不得呼叫 production 的 `instance_applicability_decision()` 來產生 expected**
     ——那等於**拿函式驗自己**（tautology），量到的只會是恆真。
```

## 7. claim ceiling

```text
A03-AUTHORITY 的 claim 必須寫成 **conditional on the retrieval interpretation**，
⛔ **不得**寫成「系統理解了使用者真正的意圖」。

允許出現：A03-AUTHORITY = PASS 而 A03-SEMANTIC = PARTIAL／INCONCLUSIVE
⇒ 這**完全合理**：gate consumer 接線正確，但對缺 referent 的句子，
  「系統選 instance 還是 general」那一步本身沒有 query-only ground truth
  ——那屬 retrieval／conversational context interpretation，⛔ 不屬 applicability gate。

⛔ 不得宣稱：production frequency／recall／traffic distribution；
   其他 15 個 REQUIRED Faces 已授權；可以擴 PREENTRY_ROUTABILITY_FACETS。
```

## 8. 語料來源

```text
新的 isolated synthetic author（⛔ 0 tool calls）
⛔ A02 corpus 不得重用作 A03 holdout（已因 protocol outcome 被看過）
✅ A02 可留作 diagnostic corpus
```

## 9. 未變動

```text
⏸ gate enable｜⏸ 3.4｜⏸ 擴 scope｜⏸ release
Level-A population digest 57413ee8a4068f73bc4e0c2c0512967e
implementation SHA f89861250d9cd01f4585fc9624a629b75bbcc7d5
```

## 10. A03 完成後會浮出的**下一個獨立命題**（⛔ 不在本協議範圍）

> **對缺乏明示 referent 的診斷型 utterance，
> retrieval 是否有足夠 authority 決定它應被解讀成 instance intent？**

⚠️ 那是下一層要裁的問題，⛔ **不是**再去修改 applicability contract。
