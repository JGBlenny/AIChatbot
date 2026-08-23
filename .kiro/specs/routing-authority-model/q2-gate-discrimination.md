# Q2（第二輪）：`_top1_relevance_gate` 的鑑別力 — offline replay 結果

> 2026-08-24｜語言 zh-TW｜pairs `9f4929b586d29cbc`／labels `95fae69d07f090ca`
> 因果鏈：**pairs freeze → blind labels freeze → 首次 gate 執行**（順序未顛倒，gate 執行前未抽樣試看）

## 結果

```text
分母 31（33 判定 − 2 UNDECIDABLE，未併入）

TP  9   人判適用、gate 放行
TN 15   人判不適用、gate 擋下
FP  0   ← **放行錯位：一筆都沒有**
FN  7   ← **誤殺：人判適用卻被擋**

agreement  24/31 = 77%
precision  9/9  = 100%
recall     9/16 = 56%
```

## 兩個方向的解讀，都要留

**正面：訊號有資訊價值，而且不靠分數。**
15 筆人判不適用者**全數被擋**（TN 15/15、FP 0），而這些 pair 的
similarity 多在 0.73–0.93——**分數切不開的東西，`query × KB` 的語義判定切得開**。
這是 P7（similarity-based representation 不構成新 authority）的**反面佐證**：
存在一種不靠 similarity 的判別來源。

**負面：它以 44% 的誤殺換取零放行。**
16 筆真正適用的知識中**擋掉 7 筆**。誤殺樣本：

```text
4-1  刷卡繳的話手續費是誰要吸收 × 信用卡ATM收款手續費 房東負擔   ← 人判 high confidence
10-2 滯納金到底是用什麼方式在計算的？ × 滯納金客製版本
11-1 已經發給房客的帳單還能改金額嗎 × 物件刊登租金調整 帳單金額不變
20-1 逾期要幾天以後才開始算滯那金 × 滯納金帳單產生 付款後結算規則
26-1 這張的滯納金怎麼比我自己算的還多 × 滯納金客製版本
30-2 押金退還也需要開一張帳單嗎 × 提前終止後帳單仍產生 需封存
47-2 房客一直反應沒收到帳單通知…… × 租客看不到帳單 三條件與信箱情境
```

⚠️ **這不必然是缺陷**：precision-first 是**已定案的產品取捨**
（「接受查無比例上升，b2b 錯誤指引的成本高於一次查無」）。
在答題路徑上，誤殺的代價是**一次誠實查無**。
⚠️ 但 4-1 是**人判 high confidence** 的明確對應題卻被擋，
顯示誤殺**不只發生在邊緣案例**。

## 對「能否成為 routing authority」的意涵（**未回答，僅列出必須先答的問題**）

```text
同一道 veto，代價結構在兩條路徑上不同：
  答題路徑：誤殺 → 一次誠實查無（已被產品接受）
  routing 路徑：誤殺 → 該進的面向沒進（使用者拿到通則說明而非自己那筆的資料）
∴ 沿用同一套 precision-first 校準到 routing，**其誤殺代價尚未被產品裁定過**
```

**INSUFFICIENT EVIDENCE**：本輪**不能**回答「它應否成為 routing authority」。
還缺：①routing 側誤殺代價的產品裁示；②它只判 `query × KB`，
**不知道 Face**，無法回答「該不該進場、該進哪一個」；
③它覆蓋不了 `trigger_facet_key`／vision／session 三種 entry。

## 證據限制（逐字保留）

> **Normative independence is not claimed.** human ground truth 與 gate prompt
> 共享同一產品 applicability criterion；本實驗評估的是 gate 對既定 criterion 的
> **execution discrimination**，**不是**獨立驗證 criterion 本身是否正確。

補充限制：

```text
- replay 為**逐 pair 獨立判定**；production gate 是**序列迴圈**（top1 判 YES 即停）
  → 本結果量的是**分類器**，非迴圈行為
- 模型 parity 為**設計推定**（env_file 同源），未實查 production 環境變數
- **不可推出 production frequency**：線上多少 request 走到這道 gate、
  多少被更早的 Face early-return 截走，仍是 runtime 問題
- 樣本 31 筆、單一領域（帳務）、單一 target_user（property_manager）
```

## 本輪對三個假說的增量

- **H2（缺 first-class query semantics）**：**增強**。存在一種
  「不靠 similarity、由 query × 內容語義判定」的訊號，且對不適用者 15/15 全中。
- **H1**：**無增量**。本輪未測「把 Hint 搬離 answer row 是否產生新 authority」。
- **H3**：**無增量**，且再次凸顯限制——這道 veto **不知道 Face**，
  無法承擔「該進哪一個面向」的判定。
