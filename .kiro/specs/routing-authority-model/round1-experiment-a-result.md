# Experiment A 結果：D1-member-1 ／ D3-member-1（首次執行）

> 2026-08-24｜語言 zh-TW
> frozen inputs：cohort `543d3e97b0a6afe6`｜labels `a3cf08354f180960`
> ｜D1 spec `ebb5f542f14d5c09`｜D3 contract `9b1c12e154b0c85a`
> 因果鏈完整：ruler → member freeze → cohort freeze → blind labels freeze → **本次首曝**

## 結果

```text
scored pairs = 29（29 opposite pairs；含 undecidable 的 bf-03 排除）

D1-member-1                paired discrimination 12/29 ｜ item agreement 41/58
D3-member-1                paired discrimination 12/29 ｜ item agreement 41/58
NEGATIVE_CONTROL impostor  paired discrimination  0/29 ｜ item agreement 29/58
```

⚠️ **impostor 0/29 證明本指標會咬**：一個只看 category（不看語義）的常數訊號，
paired discrimination **必為 0**，而它的 item agreement 仍有 29/58——
**這正是「只看 item accuracy 會被騙」的實證**。

## 失敗形態：**兩個 member 都是單向過度拒絕，不是隨機錯**

```text
labels   applicable 29 ｜ not_applicable 30 ｜ undecidable 1
D1       applicable 12 ｜ not_applicable 48
D3       applicable 13 ｜ not_applicable 47

D1  過度拒絕（label=applicable → 判 not_applicable）17 ｜ 過度放行 **0**
D3  過度拒絕 17 ｜ 過度放行 **0**
```

**兩者都把 applicable 側壓縮掉了**：29 個應為 applicable 的句子中，17 個被判 not_applicable。
17/29 組因此兩側同判 → paired discrimination 只剩 12/29。

典型未區別組（label 相反、member 兩側皆 `not_applicable`）：

```text
bd-02  「一般來說帳單發出去之後還能改金額嗎，流程是怎樣」 vs「8月那張水電費現在還改得動嗎」
bd-07  「帳單刪掉以後單號會被重複用到嗎」               vs「為什麼這張帳單沒辦法刪」
bd-06  「重發帳單的話租客通常會收到兩次通知嗎」          vs「9/15 那張我想再重發一次，可以喔？」
ba-06  「帳單期間可以跨月嗎」                        vs「這筆的期間寫 7/1-7/31，但明明應該是八月份的」
```

⚠️ 右側全部明確指涉某一筆（`8月那張`／`這張`／`9/15 那張`／`這筆`），
**member 仍判 not_applicable**——這不是「軸線太細」，是**執行層面沒有把軸線施加上去**。

## ⚠️ 一個必須攤開的發現：兩個 member 的判定 **85% 相同**

```text
D1 與 D3 逐句判定相同：51/60 = 85%
分數完全相同：paired 12/29、item 41/58（純屬巧合的機率低）
9 筆差異中，**7 筆**是「一方判 applicable、另一方 not」，方向不一致
```

依 **member freeze 的 provenance 防線①**：

> 若 D1 spec 與 D3 contract 在行為上不可區分，**本輪不得宣稱比較了 D1 vs D3**。

**判定**：本輪**不得**作 D1 vs D3 的比較性結論。
兩者**同一 evaluator class／model／config**，僅換 provenance 文本，
而行為 85% 重合——**無法區分是 architecture family 差異還是 classifier 行為主導**。
⚠️ 這正是最小差異設計要暴露的東西：**它暴露了 evaluator 主導、provenance 影響有限。**

## Disposition（依 M1 兩級）

```text
member 層
  D1-member-1  **REJECTED for R1**（paired discrimination 12/29；單向過度拒絕 17/29）
  D3-member-1  **REJECTED for R1**（同上）

family 層
  D1 family  **INSUFFICIENT_EVIDENCE**（一個 member 失敗，不得外推）
  D3 family  **INSUFFICIENT_EVIDENCE**（同上）
```

⚠️ **明令禁止的推論**：「D1／D3 都失敗 → candidate-specific adjudication 或
Face-owned contract 這兩條路都不可行」。**M1 不允許。**

## 未進 Experiment B

依既定規則：**只有 A 的存活者才進 B**。兩個 member 皆未存活 → **B 不執行**。
⚠️ 故 matching ruler（tolerance `0.058928`）本輪**未被使用**，仍為凍結狀態，可供下一輪沿用。

## 本輪確實學到的（可帶進下一輪）

```text
① paired discrimination 這把尺有鑑別力（impostor 0/29 vs member 12/29）
   且它抓到了 item agreement 抓不到的東西（impostor item agreement 仍 29/58）
② 失敗是**單向的**：過度拒絕 17、過度放行 0 —— 與 v1 lexical candidate、
   與 Q2 的 relevance gate **同一形態**（precision-first collapse）
③ 兩份不同 provenance 文本經同一 evaluator 後行為 85% 重合
   → 下一輪若仍用「文本 ＋ 通用 evaluator」的形態，須先解釋為何不會再被 evaluator 主導
```

⚠️ ③ 是本輪最有價值的負面資訊，但它**不是** claim ceiling 之外的結論：
它只說明**這種 member 形態**的行為由 evaluator 主導，
**未證明** provenance 分離在其他形態下無效。
