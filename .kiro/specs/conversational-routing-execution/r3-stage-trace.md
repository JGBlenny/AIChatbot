# R3：confirmed M-A 的逐 stage 純觀測 trace（2026-08-29）

- 對象：R2 判定的 **M-A 40 筆**（COVERED × misaligned）
- ⛔ 未改 threshold、未改 top_k、未改 embedding、未改 KB
- 完整性：trace rows 40／unique 40／exceptions 0；`PRODUCER_EXIT=0`（⛔ 非 pipeline exit code）

## ⚠️ 第一版量尺是錯的——正對照當場否決

```text
第一版用 raw `vector_similarity` 對 0.65 判 threshold
正對照 #61/#62/#63（I1-explicit，A03 判 CORRECT）
  vector_similarity 僅 0.52–0.56 < 0.65 ⇒ 依該量尺「應被門檻砍掉」
  但實際 **final_rank = 1**
⇒ 對碼確認：Step 6 `_finalize_scores`（rerank_score ＋ keyword_boost ＋ vector_similarity）
  之後，Step 7 才用 **final `similarity`** 過門檻
⇒ 第一版的 R3b 歸類**無效，未採用**
```

⚠️ 若當初只跑 40 筆 M-A、不放正對照，那張錯表會長得非常合理
（R3b 62.5%、且「全部被 0.65 砍掉」），很可能就直接報出去了。

## 修正後的 stage 模型

```text
S1 RAW         `_vector_search` 輸出                  ＝ candidate generation universe
S2 UNFILTERED  `retrieve(return_unfiltered=True)`     ＝ **已算 final similarity、未過門檻**
S3 FINAL       過 similarity_threshold ＋ top_k       ＝ production 回傳
```

⚠️ `return_unfiltered` 是 production 自己的 debug 旁路：跳過 Step 7 過濾但保留 Step 6 計分
⇒ 正是所需的 post-finalize／pre-threshold 狀態，⛔ 不需要也沒有降門檻重跑。

## 量尺先驗（positive control，⛔ 不進 M-A 母體）

```text
#61 final_sim 0.8375 ✅  #62 0.9295 ✅  #63 0.7280 ✅
#188 0.8982 ✅  #189 0.9473 ✅  #190 0.9658 ✅
六筆皆 S1 present → S2 present → pass threshold → final_rank 1
⇒ harness 在正常案例上看得見完整鏈路
```

## 主表（互斥，n=40）

```text
R3a GENERATION_MISS    **6**  (15%)   expected 不在 candidate universe
R3b THRESHOLD_DROP    **23**  (58%)   有生成、有計分，但 final similarity < 0.65
R3c RANKING_LOSS      **11**  (28%)   過門檻但非 top1
```

## ⚠️ 這推翻了先前「candidate generation 是主導機制」的推測

```text
R2 的分類學顯示 P1（expected 未進 top10）＝ 最大宗，
我當時把它讀成 candidate generation／recall 問題。
R3 的 stage trace 證明：**那多半不是「沒生成」，而是「生成了、算分了、被門檻擋掉」。**
GENERATION_MISS 只有 6 筆（15%）。
```

## 逐 stratum

```text
unit            n   R3a  R3b  R3c
G1              6    0    1    5
G2             11    1    9    1
G3              6    2    2    2
I2-explicit     7    2    3    2
I3-explicit     3    1    1    1
I4-explicit     1    0    1    0
I5-explicit     1    0    1    0
I6-explicit     5    0    5    0
```

⚠️ 形狀分歧明顯：**G1 以 R3c 為主（5/6）**，**G2／I6 以 R3b 為主**
⇒ ⛔ 不得用單一機制概括十個 unit。

## gap 觀測（⛔ 未據此改任何參數）

```text
gap_threshold = final_similarity − 0.65
  n=34  min **−0.6335**  median **−0.0366**  max +0.2915
R3b 中「貼線」者（gap > −0.05）：**9／23**
```

⚠️ 中位數只差 0.037，但**分佈很長**（最低 −0.63）
⇒ ⛔ 不得推論「門檻降一點就好」——那是 candidate experiment，不是本輪的觀測範圍。

## R3c 的 winner 類型

```text
winner ∈ Level-A：**2／11**
⇒ ranking loss 多數是被**非-Level-A 的 KB** 超車，⛔ 不是 Level-A 內部互搶
（與 pair-competition 已被反證一致）
```

## 可以下的 claim

```text
✅ confirmed retrieval failures 中，**主要機制是 threshold policy**（58%）
✅ candidate generation miss **確實存在但次要**（15%）
✅ ranking loss 佔 28%，且多為非-Level-A KB 超車
⛔ 不得說「降門檻即可修好」——未做該實驗，且分佈長尾
⛔ 不得說 candidate generation 沒問題——6 筆是真的
```

## 狀態更新

```text
retrieval implementation defect   ESTABLISHED
threshold-policy defect           **ESTABLISHED as primary mechanism**（23／40）
candidate-generation defect       **ESTABLISHED as secondary**（6／40）
ranking defect                    **ESTABLISHED as secondary**（11／40）
knowledge coverage defect         確有 11 筆 mismatch（R2），⛔ 非主因
pair-competition hypothesis       REFUTED
⛔ 本檔不提修法（業主指示）
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
