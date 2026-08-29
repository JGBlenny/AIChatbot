# A02 synthetic semantic authorization —— **協議草案（門檻待業主裁定後才凍結）**

⚠️ 這是**新協議**，⛔ 不沿用 A01 的任何量尺。
A01 的 `30/10/10` 是「一般性自然來源」的 **coverage precondition**；
A02 是刻意 scope-matched、strata 平衡的 synthetic test，**目的不同**，
⛔ 不得因為兩者都叫 holdout 就複製門檻。

## 0. Claim ceiling（**先寫死**，業主原文）

> **A02 tests semantic correctness and routing behavior under an isolated
> synthetic, scope-matched corpus. It does not estimate production frequency,
> recall, or traffic distribution.**

⇒ 因此 corpus **可以刻意平衡** general／instance，⛔ 不需要、也不得宣稱代表真實分布。

## 1. 驗證目標

```text
frozen Level-A 10-row applicability gate 的**語義行為**
implementation SHA f89861250d9cd01f4585fc9624a629b75bbcc7d5（維持凍結）
Level-A population digest 57413ee8a4068f73bc4e0c2c0512967e（維持凍結）
```

## 2. Corpus 規格（**事前固定，⛔ 生成後不得依結果補題**）

```text
6 個 intent strata × 20 句 = **120**（general 60／instance 60）

GENERAL
  G1  點退帳單是否／何時自動產生、結算流程
  G2  收據或繳費證明 PDF 如何取得
  G3  點退帳單金額的計算規則

INSTANCE
  I1  查自己的某張收據實際金額
  I2  查自己的某筆帳單／帳單狀態
  I3  查自己某份合約的點退帳單實際金額
```

⚠️ 每組數量事前固定；⛔ 生成後**不得**因某組 retrieval 表現差而補該組。

## 3. 作者隔離

```text
✅ 作者**可以**知道：上述六個使用者任務（＝本次要驗的 semantic domain）
   ⚠️ 這不是洩題——它是驗證標的的定義

⛔ 作者**不得**看到：
   3402/3406/… 等 10 個 knowledge rows｜question_summary｜categories｜
   embedding／ranking｜Face 名稱｜gate｜instance/general metadata｜
   lexical extractor｜任何測試｜「哪些措辭容易命中」

要求：自然產生**多種表述**（口語、簡略、含錯字、不同角色語氣），
⛔ 不得對 KB 文案改寫。
```

## 4. 兩層分開判（⛔ 不得只看最終 routing）

```text
Layer A — retrieval support
  synthetic query 的 top1 是否落在 frozen 10 rows，且落在**預期的 truth 側**
    expected general task  → top1 為 general Level-A row
    expected instance task → top1 為 instance Level-A row
  ⚠️ 若 scope-matched 的 synthetic 仍大量 top1 跑出 Level-A
     ⇒ 那是 **nomination／retrieval coverage 問題**，⛔ 不得歸咎 applicability gate

Layer B — authority behavior（**只有 Layer-A match 才進**）
  general truth  → INELIGIBLE → suppress
  instance truth → ELIGIBLE   → retain
```

⇒ 即使最終不過，也能分辨死在 ①retrieval ②applicability truth ③consumer policy 哪一層。

## 5. 待裁門檻（⛔ **我只提建議，未凍結**）

| 項目 | 我的建議 | 理由 |
|---|---|---|
| 每 stratum 最低有效題數 | **≥ 15**／20 | 留 5 句給 undecidable 耗損；低於此該 stratum 不具代表性 |
| Layer A alignment（每側） | **≥ 80%** | corpus 是刻意 scope-matched，低於此表示 retrieval 支撐不足 → 判 `RETRIEVAL_INSUFFICIENT`（**與 gate 失敗分開**） |
| Layer B authority accuracy | **≥ 90%** | 給定宣告後判定是決定性的；殘餘誤差來自 query truth 與 row truth 的語義錯位 |
| undecidable 處理 | 不計入分母 | 同 A01：兩位標註者合議否則 undecidable，⛔ 無仲裁者 |
| labeler integrity | 同 A01 frozen isolation contract | 兩位隔離、各恰一次 Read、456→120 規模不變原則 |
| label-quality | L1 ≥ 90%、κ ≥ 0.70 | 沿用 A01 §3B（該判準與來源無關，⚠️ 這是唯一適合沿用的） |

⚠️ ⛔ 這張表未經裁定前**不得**開始生成 corpus。

## 6. Mutation／negative controls（建議，待裁）

```text
① mutation：把某一筆 Level-A row 的宣告翻轉（instance↔general）
   → 對應 stratum 的 routing 必須整組翻轉
   ⇒ 證明結果真的由 truth contract 驅動，非 retrieval 巧合
② negative control：用 **A01 已 burned 語料中 top1 不在 Level-A 的句子**
   → 必須維持不進 Level-A（burned corpus 僅可用於失敗分析，此用途合法）
```

## 7. 執行順序（⛔ 不可調換）

```text
1. 業主裁定 §5／§6 → **協議凍結**
2. isolated synthetic author 生成 120 句（作者只收 §2 任務規格）
3. corpus 固定 ＋ digest
4. 兩位隔離標註者做 query 層 truth（instance／general／undecidable）
5. integrity ＋ label-quality precondition
6. labels 凍結 ＋ digest
7. 才跑 frozen implementation
8. **先判 Layer A**，再判 Layer B
```

## 8. 未變動

```text
⏸ 3.4｜⏸ gate enable｜⏸ 擴 PREENTRY_ROUTABILITY_FACETS｜⏸ release
A01 = CLOSED／BURNED；⛔ 不得用 A02 去補救 A01
```
