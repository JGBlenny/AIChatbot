# Level-A gate authorization protocol —— **凍結於抽樣與標註之前**（2026-08-29）

⚠️ 依 `holdout-validation` 鐵則①：順序不可逆。本檔在 corpus 固定、標註、執行**之前**寫定。
⛔ 執行後不得修改本檔的任何判準。

---

## ⚠️ 阻斷條件（**必須先解，否則本協議無法執行**）

你列的驗證鏈是：

```text
query → retrieval top1 → Knowledge applicability truth → category nomination
      → Face requirement → applicability cross-product → suppression/allow → final routing
```

但**凍結的 implementation（`c35b2e4`）還接不上這條鏈**：

```text
現行 gate：`_instance_gate_decision` → InstanceEvidenceExtractor().extract(user_message)
          → instance_reference_gate(evidence, face_requires_instance=True)
          ⇒ 讀的是 **query 的詞彙證據**，⛔ **不是** applicability cross-product

P1c 刻意「接契約，不接政策」，並留下斷言
  `test_no_consumer_reads_the_new_decision_yet`
  —— routing 尚未消費 `instance_applicability_decision`
```

⇒ **本協議所授權的實作，必須先完成 consumer wiring（P1f）。**
⛔ 在未接線前執行，量到的會是舊的 lexical gate，與本輪建立的 truth contract 無關
——那正是 D1–D3 失敗的同型錯誤（在授權輸入缺席的系統上評估授權機制）。

```text
本協議狀態：**FROZEN but BLOCKED**
解除條件：P1f 完成 ＋ 重新記錄 implementation SHA ＋ 重跑 equivalence／matrix 測試
```

---

## 1. Source（業主裁定）

```text
source population   sealed pool 的**剩餘 456 句**（576 − D2 80 − D3 40）
sample              **ALL 456**
sampling rule       no sampling／census of remaining sealed pool
```

⚠️ **為什麼不留一部分**（業主裁定原文的理由）：它已是唯一具資格的來源，
且同來源前幾輪已提示 matching support 可能偏低。若只抽 160/240 而不足，
下一輪再從同池補抽就有 **adaptive sampling 的嫌疑**。全量一次回答
「這個唯一剩餘來源究竟有沒有足夠 matching support」。

```text
⚠️ 代價：這 456 句跑完即**全部 burned**。
   但若連全量都供不出足夠 Level-A support，保留 200 句沒有未來價值——
   只是把來源不足的問題往後拖。
```

## 2. `n_match` 的定義（**先寫死**）

```text
n_match = query 可判定
          AND production retrieval **top1** ∈ frozen Level-A 10 rows
```

⛔ 事後**不得**改成：top3 命中也算／categories 含 bill_diagnosis 也算／
similarity 很接近也算／resolver 最後進 bill_diagnosis 也算。

⚠️ 理由：目前 gate 的 authority input 是 **top1 knowledge truth**，
coverage 必須對齊真正的 consumer。

## 3. Coverage precondition（**驗證結果的一部分，⛔ 不是選題工具**）

```text
C1  judgeable Level-A top1 matches   >= 30
C2  truth = instance 的 matches      >= 10
C3  truth = general  的 matches      >= 10

任一不成立 → authorization = **INCONCLUSIVE**
  ⛔ 不得計 PASS／FAIL
  ⛔ 不得追加 corpus
  ⛔ 不得改 sampling
  ⛔ 不得放寬 top1 → topK
  ⛔ 不得因某側不足回頭補題
```

⚠️ `10/10` **不是**用來報兩側準確率，而是 **branch coverage precondition**：
gate 同時有「允許 instance」與「抑制 general」兩個方向，
一側只有 1–2 筆時即使總 N=30 也不算完整 authorization。

⚠️ 456 裡有多少 `undecidable` **不另留比例**——全量本身就是最大的耗損預留。

## 4. Truth preparation

```text
truth 單位   **query 層**：正確完成這句話的意圖，是否必須依賴
             user-specific／instance-specific runtime data
標籤         instance／general／undecidable
標註者       兩位互相隔離；每位恰好一次 Read 自己的語料檔（同 P1e-1 修訂）
可見         僅 query 原文
⛔ 不給      Level-A 那 10 筆知識、applicability 宣告、Face requirement、
             gate 機制、retrieval 結果、本協議的門檻
合議         兩者皆 instance→instance；皆 general→general；
             其餘一律 **undecidable**（不計入 judgeable）
```

⚠️ **已知方法風險**（P1e-1 的教訓，此處先登記）：盲標從文字判斷曾把
已證實需要實值的 3509 判成 general。本輪風險較低的理由是
**判的是 query 的 referent（「我這張帳單…」vs「帳單什麼時候開」），
不是 KB 答案的通用程度**——但⛔ 不得因此假設不會再錯；
若合議 general 與凍結的知識宣告大量衝突，該衝突本身就是結果的一部分。

## 5. 執行順序（⛔ 不可調換）

```text
1. 本協議凍結                    ← 現在
2. 456 固定為本輪 corpus ＋ digest
3. blind truth labeling ＋ integrity check（幻覺 id／漏標／工具使用）
4. freeze labels ＋ digest
5. **才**第一次跑 frozen implementation（需先解阻斷條件）
6. 計算 Level-A matching support
7. **先判 coverage precondition**
8. coverage PASS **才**計 authorization PASS／FAIL
```

## 6. PASS／FAIL／INCONCLUSIVE

```text
INCONCLUSIVE   C1／C2／C3 任一不成立，或阻斷條件未解
PASS           coverage 成立，且系統在兩個方向的判定與 truth 一致率達預登記門檻
FAIL           coverage 成立，但一致率未達門檻
```

⚠️ 一致率門檻**留待 coverage 判定通過後、看結果之前**由業主裁定並補登，
⛔ 不得在看到一致率之後才訂。

## 7. Claim ceiling（預先登記）

```text
✅ 可說：在此 456 句 census 上，Level-A top1 matches 為 n；兩側各為 x／y
⛔ 不得說：任何 production 分布——來源是真實衍生語料，**不是流量抽樣**
⛔ 不得說：對其他 Face／其他 scope 的授權結論
⛔ 本輪用畢，456 句全部 BURNED，⛔ 不得再作任何 holdout
```
