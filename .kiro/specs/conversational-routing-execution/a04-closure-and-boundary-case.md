# A04 收案 ＋ 3498↔3531 責任邊界立案（業主裁定 2026-08-29）

## 一、A04 正式狀態

```text
A04                        = INCONCLUSIVE / CORPUS_INSUFFICIENT
reason                     = P stratum 3498 僅 13/20 confirmed single-owner truth
labeling quality           = PASS（L1 97.0%、κ 0.9682、兩位 labeler tool_uses 各 3）
candidate / legacy harness = NOT EXERCISED
corpus                     = SEALED_UNBURNED
                             ✅ 可用於 diagnostic／responsibility-boundary 分析
                             ⛔ **不得**用於取得 A04 authorization
```

## ⚠️ 二、為什麼**不**採「排除 3498、改驗 9 rows」

A04 凍結時的 claim unit 是 **Level-A frozen 10 rows**，coverage precondition 是
每 stratum `single-owner truth == intended row ≥ 15/20`。3498 = 13/20 ⇒
**predeclared precondition 沒過**，⛔ 不是「labeler 品質差」。

```text
先看到：3498 沒過 precondition
再決定：那 3498 不算，本輪改驗 9 rows
＝ **根據 validation outcome 修改 scope**
```
即使完全沒看 candidate／legacy 輸出，**已經看過 ground-truth distribution** ⇒
scope 不再是 validation 前凍結的。它未必讓成績變好看，但會破壞這條 provenance：

```text
freeze scope → generate → label → system
```

⇒ 若仍要驗其餘 9 rows，必須另開 **A05-9**，用**新的 unseen holdout**：
新 scope、新 corpus、新 digest、新隔離標註、新 system run。
⛔ 不得從 A04 的 180 筆 P cases 抽出來續用——那些 label 已經被看過，
不再是新 protocol 的 unseen source。

## ⚠️ 三、N 層的 63 筆也**不得**挪用

```text
N-valid 58／N-neighbor-shift 5／N-LevelA-truth 3／UNRESOLVED 34
⇒ N2 可用 63
```
A04 在進 system 前就停了 ⇒ 這 63 筆現在是 **knowledge-boundary diagnostic
evidence**，⛔ **不是** candidate safety validation evidence。

---

# 四、`KNOWLEDGE_RESPONSIBILITY_OVERLAP` —— **CONFIRMED**（另立案）

## 雙向證據（⛔ 不是 generator 偶發跑偏，⛔ 不是 reranker 問題）

```text
P 向：intended 3498 的 20 句 →  3 筆 truth 落到 **3531**
                             →  2 筆 truth 落到 **4656**
                             →  2 筆兩位不一致（A 判 3498／B 判 MULTI{3495,3496}）
N 向：intended 3939／3940 →  **3 筆 truth 落回 3498**
叢集：MULTI_OWNER (3939,3940)×3 兩位高度一致
⇒ 同一條裂縫、**方向相反**的兩組證據。
```

## 實查到的結構事實（⛔ 未改任何內容）

| row | question_summary | categories | applicability | answer 長度 | 所屬 face／capability |
|---|---|---|---|---|---|
| 3498 | 為什麼被收逾期費（延遲金） | 條件診斷：帳單 | **instance** | 48 | bill_diagnosis → `_diagnose_late_fee` |
| 3531 | 滯納金帳單產生 付款後結算規則 | 帳單管理, 滯納金 | 未宣告 | 231 | 滯納金 → `build_late_fee_facts` |
| 3532 | 滯納金客製版本 固定金額階梯式 | 帳單管理, 滯納金 | 未宣告 | 233 | 滯納金 → `build_late_fee_facts` |
| 3939 | 滯納金怎麼收這麼多 | 滯納金 | 未宣告 | **0** | 滯納金 → `build_late_fee_facts` |
| 3940 | 這筆延遲金是怎麼算的 | 滯納金 | 未宣告 | **0** | 滯納金 → `build_late_fee_facts` |

### ⚠️ 比「3498 與 3531 重疊」更精確的兩件事

```text
① **兩個不同的 face 都在承接「這一筆的滯納金診斷」**
   3498      → 條件診斷：帳單 face，引擎 `_diagnose_late_fee`
   3939/3940 → 滯納金 face，引擎 `build_late_fee_facts`
   ⇒ 同一 instance intent、**兩套決定性引擎**、兩個 nomination 路徑
   （`diagnose_bill` 的關鍵字表確實含「逾期／延遲金／滯納金／late fee」）

② **3498 自身宣告與內容不一致**
   applicability = `instance`（P1e 逐筆裁定）
   但 answer 48 字寫的是**通則公式**「租金 × 遲繳天數 × 費率%…」
   ⇒ general 內容掛 instance 宣告
```

## 待釐清的三個 semantic axes（⛔ 先不改文案、⛔ 先不 merge rows）

```text
general mechanism     滯納金制度／兩種機制／客製版本 —— 目前 3531、3532
instance diagnosis    這一筆為什麼被收、狀態與實值 —— 目前 3498 **與** 3939/3940 都宣稱
amount calculation    金額如何得出 —— 3498 的 answer（通則公式）
                                    vs `build_late_fee_facts` 的存值引用
```

### 立案要回答的問題

```text
Q1 3498 到底負責：某筆為何被收？實際金額如何算？還是 instance diagnosis？
Q2 3531 到底負責：制度／機制的規則性說明？是否應為 general only？
Q3 3939／3940 各自負責什麼？與 3498 的邊界在哪？
Q4 若確為**合法 overlap**，應如何明示 multi-owner／precedence，
   ⛔ 而不是硬逼成互斥 taxonomy？
```

⚠️ **Track 1 完成後，3498 才有資格重新進入新的 validation。**

## 兩條 Track ⛔ 不互相綁死

```text
Track 1  3498/3531 responsibility-boundary audit（產品 truth）
Track 2  A05-9 或修正後的 A05-10——從頭 freeze，⛔ 不沿用 A04 語料
```
業主裁示：**先處理 3498/3531 邊界，再決定開 A05-9 或 A05-10。**
