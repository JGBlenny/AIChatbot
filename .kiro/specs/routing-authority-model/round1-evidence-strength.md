# Round 1：D1／D3 證據強度限定（**凍結於 labels 產生之前**）

> 2026-08-24｜語言 zh-TW｜cohort 已凍結（`0f359f6`，digest `543d3e97b0a6afe6`）
> ⚠️ 本檔 commit 時：**labels 尚未產生、members 尚未執行**。

## Ground truth source：採**第 2 級**（業主裁定）

```text
1. 獨立既有 product／business specification   ← **實查不存在**（帳務領域無獨立於 seed 之外的 applicability 規格）
2. Face seed 中 D3 轉譯前的 authoritative source   ← **本輪採用**
3. product owner adjudication                  ← 不採（業主已看過 D3 設計與整段研究，
                                                  只會把 dependence 從「共同來源」換成「candidate-aware adjudicator」）
4. D3 responsibility artifact 本身              ← 不採
```

## D3 的限定（比「降一級」更精確）

> **D3 的 normative independence 不成立；execution independence 仍成立。**

```text
Ground truth labeler → 讀**原始 authoritative seed**
D3 member           → 讀**事前凍結**、由**同一 seed** 轉譯出的 executable contract
Challenge utterances → 由 **member-blind 隔離作者**生成
```

**D3 通過 A／B 可證**：

> 一個**事前凍結**的 Face-owned executable contract，能否把**既有 authoritative Face semantics**
> 穩定施加到**未見 wording** 上，並產生 R1 所需的 applicability discrimination。

**不可證**：

> Face seed 所定義的 responsibility boundary 本身是**獨立驗證過、完整且正確**的產品 routing ontology。

（落在已凍結的 claim ceiling 之內。）

## 兩者的證據強度**分開記，不得都寫成同一個 `SUPPORTED`**

```text
D1:  label authority = Face seed
     information source = routing-owned demand model
     normative_source_overlap = **false**        ← 本 cohort 對 D1 無同源問題

D3:  label authority = Face seed
     contract source  = **same Face seed**
     normative_source_overlap        = **true**
     execution_artifact_independence = true      （contract 事前凍結）
     challenge_independence          = true      （作者 member-blind）
```

**若 D3 通過，disposition SHALL 表達為**：

```text
D3-member-1:  SUPPORTED for R1 execution／discrimination
              **with PARTIAL NORMATIVE DEPENDENCE**
D3 family:    SUPPORTED by existence proof **within authoritative-seed semantics**
NOT established: independent correctness／completeness of Face responsibility semantics
```

⚠️ 仍符合 M1——**不是無效實驗，只是 SUPPORT 的射程有明確上限。**

## Step ⑥ labeling protocol（四項鎖定）

**labeler 只看**：

```text
pair-hidden、randomized 單句 ｜ fixed candidate Face
該 Face 的**原始 seed authoritative text** ｜ applicability label schema
```

**不給**：

```text
D3 executable artifact ｜ D1 demand spec ｜ D1／D3 member 身份 ｜ member prompt／rules
similarity／category ｜ current route ｜ **pair mapping** ｜ 作者原本想做的正反方向
```

**且 labeler 不需知道「這輪在測 R1」**——只需知道其產品任務：
依 authoritative seed 判斷該句是否屬於該 Face 的處理責任。
（再少一層研究目的對標註的影響。）

**允許並保護 `UNDECIDABLE`**：

```text
seed 依據不足 → UNDECIDABLE
⚠️ **不得**為維持作者「30 組一正一反」的設計而強迫拆成 opposite labels
```

**labels freeze 後才恢復 pair mapping**。若出現

```text
作者 intended contrast pair → blind labels 卻同側
```

那是 **challenge-generation yield 的真實結果**——**不修、不重標**。
