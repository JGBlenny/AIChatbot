# A03 protocol —— **草案（數量與門檻待裁；⛔ 未凍結、未生成 corpus）**

## 0. 為什麼要有 A03（A02 揭露的是命題錯誤，不是題目不夠）

A02 把兩件事混成一個 truth：

```text
「這句話**表面上**能否判出 instance／general」
        ≠
「系統在 retrieval 選定某個 Knowledge 之後，gate 是否照契約正確執行」
```

⇒ A03 把兩者**分開授權**，⛔ 不再硬塞成單一 PASS。

## 1. query oracle 改為**三態＋一個失敗態**

```text
INSTANCE           必須讀該使用者自己的資料才能正確完成
GENERAL            不需要任何該使用者自己的資料
CONTEXT_DEPENDENT  **句子本身確實不足以唯一決定 intent**——
                   必須知道對話脈絡或使用者當下的 referent 才能判
UNDECIDABLE        標註品質不足／標註者無法做出判斷
```

⚠️ **`CONTEXT_DEPENDENT` ≠ `UNDECIDABLE`**，⛔ 不得混為一談：
前者是**語言事實**（「帳單寄不出去是什麼原因」天生歧義），
後者是**標註失敗**。A02 把兩者混在一起，才會把語言事實記成 corpus 不足。

⛔ **不得**為了讓 denominator 足夠而強迫 CONTEXT_DEPENDENT 變成 instance。

## 2. Layer Q — query semantic recoverability

```text
兩位皆 INSTANCE 或兩位皆 GENERAL             → SEMANTICALLY_JUDGEABLE
任一方判 CONTEXT_DEPENDENT，且**不存在** G↔I 實質衝突 → CONTEXT_DEPENDENT
真正的 G vs I 衝突                            → LABEL_DISAGREEMENT
其餘（含 UNDECIDABLE）                        → UNDECIDABLE
```

## 3. Layer A — retrieval semantic alignment

```text
【對 SEMANTICALLY_JUDGEABLE】沿用強 oracle：
   top1 ∈ allowed_top1_ids[stratum]，逐 stratum >= 80%
   ⇒ 這才是真正的 end-to-end semantic support

【對 CONTEXT_DEPENDENT】⛔ **不判對錯**
   query 本身沒有提供這個 truth ⇒ 只記錄 `retrieval_interpretation`：
     top1 落在哪一個 frozen Knowledge intent／該 row 的宣告是 instance 還是 general
   ⚠️ 這是**觀察系統如何解讀歧義**，⛔ 不是 semantic accuracy
```

## 4. Layer B — authority contract execution（**不需要 query truth**）

```text
母體：**所有** top1 ∈ Level-A frozen 10 rows 的案例（**含 CONTEXT_DEPENDENT**）
判定：top1 宣告 × Face requirement → authority decision
      instance × REQUIRED → ELIGIBLE ／ general × REQUIRED → INELIGIBLE
門檻：accuracy = **100%**
```

⚠️ claim 必須寫成 **conditional on the retrieval interpretation**，
⛔ **不得**寫成「系統理解了使用者真正的意圖」。這個差別是本協議的核心。

## 5. 兩個獨立 verdict（⛔ 不合成單一 PASS）

```text
A03-SEMANTIC    query → retrieval 的語義對位；只在 SEMANTICALLY_JUDGEABLE 上評估
A03-AUTHORITY   retrieval top1 → Knowledge truth → Face requirement → gate action；
                在所有 Level-A top1 cases 上評估
```

⚠️ 允許出現：

```text
A03-AUTHORITY = PASS
A03-SEMANTIC  = PARTIAL／INCONCLUSIVE on context-dependent language
```

這**完全合理**，且比硬湊一個總 PASS 誠實得多。它會告訴我們：
gate consumer 接線正確；但對缺 referent 的句子，
「系統選 instance 還是 general」那一步**本身沒有 query-only ground truth**
——那屬 **retrieval／conversational context interpretation**，⛔ 不屬 applicability gate。

## 6. Corpus 設計（**待裁**）

⚠️ ⛔ **不採「全部加『我的／這張』」**：那只能建立
**explicit-reference subset authorization**，claim ceiling 太窄，
且等於為了讓 oracle 一致而改題目。

✅ 改為**刻意包含兩種語言形態**，並**預先登記子配額**：

```text
建議：維持 10 strata × 20 = 200
  3 個 general strata（G1–G3）  每組 20，不分子配額
  7 個 instance strata（I1–I7） 每組 **10 explicit ＋ 10 elliptical**（事前固定）
     explicit   帶明示指涉：「我的／這張／編號 X」
     elliptical 自然省略：「帳單寄不出去是什麼原因」
```

⚠️ 兩者的**評估 oracle 不同**（這才是拆開的理由，⛔ 不是為了讓測試過）：

```text
explicit   → semantic correctness 可判 → 進 Layer A 分母
elliptical → 預期多為 CONTEXT_DEPENDENT → ⛔ 不宣稱 user-intent correctness，
             只驗 Layer B 的 contract-conditioned behavior
```

## 7. 待裁門檻（⛔ 我只提建議）

| 項目 | 建議 | 理由 |
|---|---|---|
| general strata sufficiency | SEMANTICALLY_JUDGEABLE >= **15/20** | 沿用 A02 |
| instance-explicit 子配額 | SEMANTICALLY_JUDGEABLE >= **8/10** | 明示指涉應該可判；低於此表示 authoring 未忠於 explicit 形態 |
| instance-elliptical 子配額 | **top1 ∈ Level-A >= 8/10** | ⚠️ ⛔ **不能**要求它 judgeable（那正是它的本質）；改要求它能餵進 Layer B |
| Layer A（每 stratum） | >= **80%** | 沿用 A02，僅在 SEMANTICALLY_JUDGEABLE 上算 |
| Layer B | **100%** | 沿用 A02；deterministic policy 不給誤差額度 |
| label quality | L1 >= **90%**、κ >= **0.70** | ⚠️ κ 現在是四類；⛔ 若某標註者只用單一標籤仍 → LABELING_INCONCLUSIVE |

## 8. 語料來源

```text
新的 isolated synthetic author（⛔ 0 tool calls）
⛔ A02 corpus **不得**重用作 A03 holdout（已因 protocol outcome 被看過）
✅ A02 可留作 diagnostic corpus
```

## 9. 未變動

```text
⏸ gate enable｜⏸ 3.4｜⏸ 擴 scope｜⏸ release
Level-A population 與 implementation SHA 維持凍結
```

## 10. 若 A03 完成，會浮出的**下一個獨立命題**（⛔ 不在本協議範圍）

> **對缺乏明示 referent 的診斷型 utterance，
> retrieval 是否有足夠 authority 決定它應被解讀成 instance intent？**

⚠️ 那是下一層要裁的問題，⛔ **不是**再去修改 applicability contract。
