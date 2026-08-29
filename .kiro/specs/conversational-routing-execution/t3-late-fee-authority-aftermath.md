# T3：late-fee ownership 收斂後的 authority 補齊（2026-08-29）

## ① 3531／3532 applicability —— **positive general declaration**

```text
3531 → general   承接規則／機制說明：付款後結算的延遲金機制、公式與適用條件。
                 即使完全不知道使用者是哪份合約、哪張帳單，仍能完整正確回答。
3532 → general   承接不同客製版本的計算機制差異（延遲金版／階梯式版／固定金額版）。
```
⚠️ 這是**正面宣告**，⛔ 不是「沒看到 instance 證據所以當 general」。
⛔ **未**因此把它們加進 `LEVEL_A_V2`——內容 successor ⛔ 不等於 routing-scope successor。

## ③ 3939／3940 applicability —— **instance**，補的是 ownership 收斂後的空窗

```text
3939 → instance   empty-answer entry anchor；責任由唯一 owner 的
3940 → instance   late_fee face／`build_late_fee_facts` 決定，該能力提供的是
                  某一筆的實際金額／實際狀態／合約設定實值／實際結算備註／
                  付款與到帳時間 —— 沒有特定 referent 就無法完成 intent。
```
⚠️ 不補這一刀就會留下：**instance owner 已收斂成 B，但 B 的主要 entry anchors
沒有 applicability authority 宣告**。

---

# ③-b Row-role audit：3939 vs 3940

## 決定性發現

```text
`build_late_fee_facts(row, user_question)` 的 **body 從未使用 `user_question`**
（AST 實測：出現次數 = 0）
⇒ 兩列題意在**任何**輸入下都產出**逐字相同**的 facts
```

四種輸入實測（滯納金帳單／已付款滯納金帳單／合約設定列／一般帳單列）：

```text
差異 0/4 —— 全部逐字相同
```

兩列的路由表面差異僅止於檢索用詞：

| row | question_summary | keywords | category | action_type |
|---|---|---|---|---|
| 3939 | 滯納金怎麼收這麼多 | 滯納金／收這麼多 | 滯納金 | direct_answer |
| 3940 | 這筆延遲金是怎麼算的 | 延遲金／怎麼算 | 滯納金 | direct_answer |

## Verdict：`DUPLICATE_UNDER_CURRENT_CAPABILITY`

⚠️ **這句話要精確**：已證明的是「**在現行 capability 下**兩列不可區分」，
⛔ **未**證明「兩者的產品 intent 相同」。存在兩種讀法，必須由業主裁：

```text
讀法 A — 真 duplicate
  「怎麼收這麼多」與「怎麼算的」在滯納金域本來就同一件事：
  拿出該筆的結算備註與存值即完整回答。
  ⇒ CONSOLIDATE_ONE：保留單一 entry row，另一列退役或降為別名。

讀法 B — capability 尚未落實既有區分
  3939 偏「金額**異常**判定」（是不是收錯了、是否照設定跑），
  3940 偏「計算過程**拆解**」。
  現行引擎兩者都只回傳同一份 facts ⇒ 是**能力缺口**，⛔ 不是知識重複。
  ⇒ KEEP_BOTH_AS_ENTRY_VARIANTS ＋ 立案補 capability 區分。
```

## ⇒ 本輪**不寫** representation（依業主裁示）

```text
⛔ 不為 population 硬寫兩份近義 contract ——
   那正是 3498 給的教訓：**row 存在 ≠ 必須保留獨立 semantic responsibility**，
   且兩份高度重疊的 scoring document 會直接製造 ranking competition
   （3498 的 mutation 已實證：重複列會回到 rank 1 與真 owner 搶排序）。
```

## 現況與界線

```text
✅ 3531／3532 general、3939／3940 instance —— applicability authority 已補齊
⛔ LEVEL_A_V2 仍是 **9 rows**，未變
⛔ 未寫 3939／3940 的 retrieval_representation
⛔ 未開 A05
⚠️ 要擴 scope 必須另立 `LEVEL_A_V3` 決策，⛔ 不得偷塞進 V2
```

## 待業主裁

```text
Q 3939 vs 3940 採讀法 A（CONSOLIDATE_ONE）還是讀法 B
  （KEEP_BOTH_AS_ENTRY_VARIANTS ＋ 補 capability 區分）？
⚠️ 在此之前 ⛔ 不寫這兩列的 representation。
```
