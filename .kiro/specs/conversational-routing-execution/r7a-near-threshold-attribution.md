# R7-A：3496／3519 的 near-threshold boundary attribution（2026-08-29）

- 對象：R3b residual 的 **3 筆**（3496×1、3519×2）
- 對照：**同一 expected row** 的**全部** P0_CORRECT 案例（3496 n=8、3519 n=5）
  ⛔ 非 unit 取樣，⛔ 兩列不 pooled（M1）
- ⛔ 未改 0.65、⛔ 未做降門檻實驗、⛔ 未跑新 corpus、⛔ 未碰 KB

## 判準（**看數字之前**已定義）

```text
A1 BOUNDARY_ONLY_CANDIDATE   failure 與同-row controls 的組件高度同型，
                             主要差異只剩 final 恰落在 0.65 兩側
A2 UPSTREAM_SCORE_DIFFERENCE failure 的某組件相較同-row controls **明顯偏弱**
                             ⇒ threshold 只是最後執行 loss 的 seam，⛔ 非 root cause
A3 INSUFFICIENT_TO_SEPARATE  controls 分布太寬、無清楚分群 ⇒ 維持 UNKNOWN
```

## row 3496（threshold 0.65）

```text
          final      gap   rerank  vector  boost  query
FAIL    0.6448  −0.0052   0.6360  0.7237   1.30  這張帳單取消時跳錯誤是什麼意思
ctrl    0.7116  +0.0616   0.7122  0.7060   1.30  那張帳單我想取消但按鈕是灰的
ctrl    0.8355  +0.1855   0.8617  0.5989   1.30  …
ctrl    0.9209 … 0.9830（其餘 6 筆）
controls n=8：final min **0.7116**／med 0.9494／max 0.9830
              rerank min **0.7122**／med 0.9815
              低於 0.75 者 1／8；低於 0.70 者 **0／8**
```

⇒ FAIL 的 rerank **0.636 低於 controls 的最小值 0.712**，
且 ⚠️ 它的 **vector 0.7237 反而是全體最高之一**（controls median 0.684）
⇒ **A2 UPSTREAM_SCORE_DIFFERENCE**

## row 3519（threshold 0.65）

```text
          final      gap   rerank  vector  boost  query
FAIL    0.3308  −0.3192   0.2958  0.6463   1.30  押金不夠扣的話金額會怎麼呈現
FAIL    0.6349  −0.0151   0.6486  0.5115   1.20  結算金額包含哪些項目
ctrl    0.7714  +0.1214   0.7934  0.5732   1.20  損壞賠償會算進點退帳單嗎
ctrl    0.8571 … 0.9784（其餘 4 筆）
controls n=5：final min **0.7714**／med 0.9572／max 0.9784
              rerank min **0.7934**／med 0.9769
              低於 0.75 者 **0／5**
```

⇒ 兩筆 FAIL 的 rerank（0.296／0.649）**皆低於 controls 的最小值 0.793**
⇒ **A2 UPSTREAM_SCORE_DIFFERENCE**

## ⚠️ 「就差 0.001」是假象——業主預警命中

```text
#50「結算金額包含哪些項目」final 0.6349、gap 僅 −0.015
直覺會讀成「門檻明顯太高」。
但同-row controls **最低就是 0.7714**、⛔ 沒有任何一筆落在 0.65–0.77 之間
⇒ 這批 query 的 scoring **已經明顯異常**，只是碰巧卡在 cutoff 附近
⇒ ⛔ 不是「boundary 把同質族群從中間切開」
```

## 逐 row 裁定（⛔ 不 pooled）

```text
3496  threshold contribution = **NOT_SUPPORTED**（A2）
3519  threshold contribution = **NOT_SUPPORTED**（A2）
```

⚠️ **樣本限制**：3496 僅 1 筆、3519 僅 2 筆。
分離之所以成立，是因為**對照分布很緊且完全在上方**（min 0.71／0.77，無重疊），
⛔ 不是因為樣本量足夠 ⇒ 本裁定限於**這 3 個 case**，
⛔ 不得外推成「該 row 的所有近門檻案例皆非 boundary 問題」。

## 狀態

```text
threshold-stage loss        ESTABLISHED（seam）
threshold-policy defect     **NOT ESTABLISHED**——且本輪在 3 個最像 boundary 的
                            案例上取得 **NOT_SUPPORTED** 的正面證據
score/scoring locus         ESTABLISHED（3 筆的 rerank 皆低於同-row controls 下限）
3496／3519 residual         **已解釋為 upstream scoring difference**，
                            ⇒ 併入 R7-B 的「雙 surface 皆弱」家族處理
remaining OPEN              R7-B（3495／3498 residual／3406 residual）＋ R6-B anchors 4 筆
⛔ 未改任何參數
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
