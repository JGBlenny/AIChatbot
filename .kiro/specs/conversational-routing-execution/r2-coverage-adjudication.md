# R2：A03 misaligned queries 的 coverage adjudication（2026-08-29）

- 對象：A03 burned corpus 的 **59 個 misaligned cases**（⛔ 不重算 A03 verdict）
- 判準：**在不新增產品能力、不補充 KB、也不靠「同主題」推論的前提下，
  frozen expected row 已有的責任／答案／能力，是否足以正確完成這句 query 的 intent？**
  ⛔ 不是問「這句應不應該被 retrieval 找到」。
- downstream 分類**機械推導**：COVERED→M-A／NOT_COVERED→M-B／AMBIGUOUS→UNKNOWN
  ⛔ 不人工再決定一次。
- 逐句 evidence 見 `scripts/analysis/r2_adjudication.json`（含 frozen 原文最小引用）。

## 量尺先驗（positive control）

```text
#42「押金不夠扣的話金額會怎麼呈現」
3519 原文：「正數則代表押金扣完還不夠，租客需要補繳差額。」
⇒ 判 **COVERED** ✅ —— 量尺可用
```

## 主表：primary bucket × coverage

```text
                            COVERED  NOT_COVERED  AMBIGUOUS
P1 EXPECTED_OUTSIDE_TOP10      **29**      11          6
P2 WRONG_TOP1_LEVEL_A            2         0          2
P3 WRONG_TOP1_NON_LEVEL_A        9         0          0
──────────────────────────────────────────────────────────
TOTAL                          **40**      11          8

downstream:  M-A **40**（68%）／ M-B 11（19%）／ UNKNOWN 8（14%）
```

## ⚠️ 這推翻了我先前的印象——照實更正

```text
我先前寫：「零召回問句（email／批次／權限／補印）都不是 3406 在講的內容」
⇒ **我是從 4 個最明顯出界的例子外推到整批**，錯了。

實際逐句裁定後：G2 的 17 個失敗中
  COVERED **11**／NOT_COVERED 4／AMBIGUOUS 2
落在 envelope 內卻**零召回**的包括：
  「收據下載的路徑麻煩告知一下」「系統有提供收據下載的功能嗎」
  「租客要繳費證明我要從哪裡調」「收據是 PDF 檔嗎還是只能截圖」
  「請問繳費證明跟收據是同一份東西嗎要怎麼拿」
⇒ 這些**正是 3406 原文在回答的東西**。
```

## 逐 stratum

```text
unit            n   COVERED  NOT_COV  AMBIG
G1             11      6        4       1
G2             17     11        4       2
G3             13      6        3       4
I2-explicit     7      7        0       0
I3-explicit     3      3        0       0
I4-explicit     2      1        0       1
I5-explicit     1      1        0       0
I6-explicit     5      5        0       0
```

⚠️ **所有 instance unit（I2／I3／I5／I6）的失敗 100% 是 COVERED**
⇒ oracle-too-broad 完全**不解釋** instance 側的失敗。
M-B 全數集中在 G1／G2／G3（11 筆），且都是明確的能力界線外
（前置設定、時間承諾、批次、email、權限、比例分攤、日期區間）。

## 結論

```text
① **M-A（confirmed retrieval misalignment on covered intents）＝ 40／59**
   其中 **COVERED × P1 ＝ 29**，是最乾淨的 recall failure evidence
   ⇒ **retrieval implementation defect：ESTABLISHED**
② **M-B（A03 stratum 超出 frozen KB coverage）＝ 11／59**
   ⇒ oracle-too-broad 假說 **成立但為次要**（19%），⛔ 不足以解釋 A03-SEMANTIC FAIL
③ AMBIGUOUS 8 筆維持 diagnostic unknown，⛔ 未硬塞進 M-A 或 M-B
④ COVERED × P3 ＝ 9：expected 在候選內、卻被**非-Level-A KB** 超車
   ⇒ 除 recall 之外另有 ranking／competition 成分
```

## ⚠️ 修正我對 80% 門檻的措辭（採業主更精確的表述）

```text
我先前寫：「同一個 80% 門檻假設 envelope 等寬」——**過度**。
80% 門檻本身**不必然**要求 envelope 等寬；它要求的是
**每個 synthetic stratum 的生成分布落在其對應 frozen row 的 semantic envelope 內**。
若 3498 的 envelope 很窄，只要 I6 author 也被約束在那個窄 envelope 內，
20 題照樣可以合理要求 80%。
⇒ R1 支持的精確命題是「**A03 部分 stratum 與 frozen row envelope 不匹配**」，
  ⛔ 不是「統一門檻因 envelope 不等寬而無效」。
  R2 已量出「不匹配」占 11/59。
```

## 狀態更新

```text
RETRIEVAL_SEMANTIC_MISALIGNMENT   CONFIRMED at A03 protocol level
retrieval implementation defect   **ESTABLISHED**（M-A 40，其中 COVERED×P1 29）
knowledge coverage defect         **不成立為主因**（M-B 11／19%）
A03 oracle-too-broad hypothesis   **成立但次要**
pair-competition hypothesis       REFUTED as primary mechanism
⛔ 未動任何 retrieval 參數、未動任何 KB、未重算 A03 verdict
```

## 下一步（R3，⛔ 僅在 M-A subset 上做）

```text
在 confirmed M-A 的 40 筆上純觀測，區分：
  R3a embedding／candidate generation 根本沒召回 expected
  R3b expected 有生成，但被 production threshold 切掉
  R3c expected 留下，但 ranker 排錯
⚠️ 重點是觀測 **pre-threshold candidate state**，
⛔ **不是**把 threshold 降低後重新宣告效果。
```
