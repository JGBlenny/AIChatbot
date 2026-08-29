# R4：23 筆 threshold-stage loss 的分數組件拆解（2026-08-29）

- 母體：R3b 的 **23 筆**（confirmed COVERED × threshold drop）
- 對照：**同 stratum** 的 P0_CORRECT_TOP1 共 24 筆（⛔ 不進母體）
- ⛔ 未改 threshold、未改 scoring 權重、未改 KB、未做降門檻實驗
- `PRODUCER_EXIT=0`；23/23 的 expected 皆出現在 unfiltered 候選中（⇒ 全部有被計分）

## 分類界線由 `_finalize_scores` 契約導出（⛔ 未發明新門檻）

```text
1. rerank_score 存在 → similarity = 0.1×vector + **0.9×rerank**   src="rerank"
2. keyword_score 存在 → similarity = min(1, max(vector,keyword)×boost) src="keyword"
3. 否則              → similarity = min(1, vector×boost)              src="vector"
```

## ① 一個機制當場被排除

```text
cases    score_source = rerank **23/23**
controls score_source = rerank **24/24**
⇒ 「reranker 根本沒對這一列計分」（被 0.3 下限或 20 筆上限排除）＝ **0 筆**
⛔ 該機制 **RULED OUT**
```

## ② binding component：**rerank_score**，且與 vector 明確分離

```text
unit          組別  n   rerank(min/med/max)        vector(med)   final(med)
G1            FAIL  1   0.643/0.643/0.643          0.467         0.626
              CTRL  3   0.943/0.966/0.992          0.635         0.933
G2            FAIL  9   **0.018/0.166/0.629**      0.449         0.194
              CTRL  3   0.864/0.970/0.987          0.569         0.930
G3            FAIL  2   0.296/0.649/0.649          0.646         0.635
              CTRL  3   0.793/0.876/0.977          0.685         0.857
I2-explicit   FAIL  3   0.257/0.302/0.640          0.588         0.331
              CTRL  3   0.725/0.882/0.984          0.661         0.852
I3-explicit   FAIL  1   0.515                      0.588         0.523
              CTRL  3   0.962/0.988/0.999          0.767         0.966
I4-explicit   FAIL  1   0.377                      0.626         0.401
              CTRL  3   0.936/0.936/0.968          0.663         0.915
I5-explicit   FAIL  1   0.636                      **0.724**     0.645
              CTRL  3   0.862/0.987/0.999          **0.614**     0.949
I6-explicit   FAIL  5   0.220/0.550/0.607          0.647         0.564
              CTRL  3   0.881/0.918/0.995          0.730         0.894
```

### ⚠️ I5-explicit 是最乾淨的分離證據

```text
FAIL 的 vector **0.724** ＞ CTRL 的 vector **0.614**
但 FAIL 的 rerank 0.636 ≪ CTRL 的 rerank 0.987
⇒ **vector 訊號不但沒缺，還更強；壓低 final 的是 reranker。**
```

## ③ keyword 也不是缺口

```text
cases     有 keyword_matches 22/23｜boost median **1.3**
controls  有 keyword_matches 21/24｜boost median **1.2**
⇒ 失敗案例的 keyword 訊號**不比對照組差**（boost 甚至更高）
⛔ keyword contribution 不足 ⇒ **不成立**
```

## ④ 對 T1／T2 的判別

```text
T1 CUTOFF_POLICY_PROBLEM   final similarity 合理，只是 0.65 過嚴
T2 SCORE_CALIBRATION       Step 6 把本該高分的 expected row 算太低

證據指向 **T2**：
  G2 的 rerank median 為 **0.166**（對照組 0.970）——⛔ 這不是「差一點點」
  9/23 貼線（gap > −0.05）只是分佈的一端；另一端 rerank 低到 **0.018**
⇒ 「把 0.65 調低」無法解釋 rerank 0.018 的案例
```

⚠️ 但仍**不得**直接宣告「reranker 壞了」——見下方未解問題。

## ⑤ winner 一律也是 rerank 來源

```text
所有 winner 的 score_source 皆為 rerank
⚠️ G2 有 **2 筆 winner 就是 3406 本身**（＝ expected）
   ⇒ 那兩筆是「expected 在 unfiltered 中排第一，但 final similarity < 0.65」
     ⇒ 整批被門檻清空 ⇒ 表現為零召回
```

## ⚠️ 尚未解答的關鍵問題（R5 候選，⛔ 本輪不做）

```text
reranker 對這些 paraphrase 給極低分——它到底拿 query 去比對**哪一段文字**？
  ・question_summary（如「帳單收據 繳費證明 PDF 下載」）？
  ・answer 全文？
  ・兩者串接？
⚠️ R2 判 COVERED 用的是 **answer 內容**；若 reranker 只看 question_summary，
   則「答案涵蓋、但摘要不像」會系統性地被壓低——那是**可檢查的機制**，⛔ 不是猜測。
```

## 狀態更新

```text
threshold-stage loss             ESTABLISHED as primary（23／40）
threshold-policy defect（T1）     **證據不支持為主因**
score/calibration defect（T2）    **ESTABLISHED as the locus**——binding component ＝ rerank_score
  ・「reranker 未計分」機制        **RULED OUT**（0／23）
  ・vector 不足                    **RULED OUT**（I5 反證）
  ・keyword 不足                   **RULED OUT**（訊號不比對照差）
reranker input-text hypothesis   **OPEN**（R5）
candidate-generation defect      ESTABLISHED secondary（6／40）
ranking defect                   ESTABLISHED secondary（11／40）
⛔ 本檔不提修法；⛔ 未碰 R3c 的 11 筆
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
