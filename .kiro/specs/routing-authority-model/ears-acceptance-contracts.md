# EARS 驗收契約：R1–R5 展開

> 2026-08-24｜語言 zh-TW｜requirements 已凍結（`e4c340a`）
> 每條固定六欄：**EARS statement／provenance／scope／falsifier／acceptance method／negative control**

## 展開時的兩條硬邊界（業主 2026-08-24）

```text
① R5 SHALL NOT 在展開過程中被升成 NECESSARY
② EARS SHALL NOT 藉「讓需求變可測」偷偷選定 L2/L3/L4/L6 或 H1/H2/H3
```

⚠️ **某條若因 design 未定而無法指定 component，就測「契約結果」，
不得先替它發明 component。** 本檔全部以**行為契約**表述，零元件指名。

## META-RULE 的可執行形式（適用每一條）

```text
不可驗收：  「系統 SHALL 呼叫 applicability checker」          ← component → executed
必須驗收：  同一 routing case，改變 authority 的判定，routing outcome 隨之改變
            authority = absent／disabled      → enter
            authority = applicable            → enter
            authority = not_applicable        → **不 enter**
```

> **存在性不能作為 authority effectiveness 的替代證明。**

---

## R1.1｜判別不得為 (similarity, category) 的函數

| 欄 | 內容 |
|---|---|
| **EARS** | **WHEN** Face entry 由 retrieval-derived Hint 造成，**THEN** applicability 判定 SHALL NOT 為 `(similarity, category)` 的函數——存在兩個 `(similarity, category)` **相同**而判定**不同**的實例 |
| **provenance** | **NECESSARY / N1** |
| **scope** | 僅 retrieval-derived Hint 造成的 entry；不涵蓋 session／caller assertion／vision |
| **falsifier** | 出現僅用 similarity＋category 即可穩定分離 rule／instance 的實測方案 |
| **acceptance** | 取 ≥1 對 `(similarity, category)` 受控相同、產品期望相反的實例，系統判定 SHALL 相異。⚠️ 資料來源 SHALL 為**新的未見樣本**——v1 那 50 句已 BURNED |
| **negative control** | 以「判定＝`(similarity, category)` 的純函數」的替身實作跑同一組，SHALL 失敗 |

## R1.2｜「新增資訊」的排除定義

| 欄 | 內容 |
|---|---|
| **EARS** | 宣稱為新增的 applicability information SHALL NOT 為 ① answer retrieval score 的重新包裝 ② category membership 的重新編碼 ③ 同一 evidence 的另一個 threshold |
| **provenance** | **NECESSARY / N1**（P7；3.4 anchor 已實測 REFUTED）|
| **scope** | 同 R1.1 |
| **falsifier** | 該資訊在語料樣本上與 `(similarity, category)` **函數相依**（給定後者即可決定前者）|
| **acceptance** | 於語料樣本上證明該資訊**可獨立變動**：固定 `(similarity, category)`，該資訊仍有 ≥2 種取值且對應不同判定 |
| **negative control** | 餵入一個**由 similarity 決定性導出**的偽訊號，SHALL 被本條判為不合格 |

## R2.1｜否決必須反事實地改變 routing outcome

| 欄 | 內容 |
|---|---|
| **EARS** | **WHEN** authorized applicability evidence 對候選 entry 判 `not_applicable`，**THEN** routing outcome SHALL 與同案在 `applicable` 時**不同** |
| **provenance** | **NECESSARY / N2**（反例：v1 holdout `#11`／`#30`）|
| **scope** | 僅**被 contract 認可為可作用**的 evidence；低可信度 observation signal 不因本條取得否決權 |
| **falsifier** | 出現「authorized evidence 判否決、無 consumer，但 routing 結果仍正確」的實測案例 |
| **acceptance** | 同一 case 三態對照：`absent／applicable → enter`；`not_applicable → 不 enter` |
| **negative control** | **consumer-only-logs 替身**（讀取、寫 log、仍 enter）SHALL 失敗；**authority-absent 替身**（v1 形態：判對 block 但 `gate_applies_to=False`）亦 SHALL 失敗 |

## R2.2｜否決須在 entry 成為 irreversible 之前生效

| 欄 | 內容 |
|---|---|
| **EARS** | **WHEN** 判定為 `not_applicable`，**THEN** SHALL **不產生任何 entry 副作用**（不得先進場再回滾）|
| **provenance** | **NECESSARY / N2** |
| **scope** | 同 R2.1 |
| **falsifier** | 出現「先進場後回滾」而使用者可觀察行為與未進場**完全等價**的實作 |
| **acceptance** | 否決案例執行後，SHALL 無 session／狀態／計量上的 entry 痕跡（外部可觀察面為準）|
| **negative control** | **post-entry rollback 替身** SHALL 失敗——其 session 建立痕跡可被觀察到 |

## R3.1｜先有責任模型

| 欄 | 內容 |
|---|---|
| **EARS** | routing authority contract SHALL 明確區分 **candidate proposal ／ applicability evidence ／ final enter-reject authority** 三種責任 |
| **provenance** | **SUPPORTED, NOT NECESSARY**（Q1 矩陣導出；⚠️ 展開不得升級）|
| **scope** | 契約層；不指定由哪個元件擔任哪個角色 |
| **falsifier** | 出現一個三責任**不可區分**卻仍能滿足 R1／R2 的架構 |
| **acceptance** | 對任一 routing decision，三種責任的**承擔者可被指名**且**彼此可區分** |
| **negative control** | **三欄 log 替身**（只多印三個欄位、但 final authority 與 proposer 不可區分）SHALL 失敗 |

## R3.2｜可追溯（**次於**責任模型）

| 欄 | 內容 |
|---|---|
| **EARS** | 對一次 routing decision，三者的**來源與最終決策關係** SHALL 可追溯 |
| **provenance** | **SUPPORTED, NOT NECESSARY** |
| **scope** | 同 R3.1；⚠️ **SHALL NOT** 被降級為 observability 需求 |
| **falsifier** | 可追溯完整、卻仍無法回答「誰有最終否決權」|
| **acceptance** | 由一筆 decision 紀錄即可回答：誰提出、依據什麼 evidence、誰做最終決定——**無須讀程式碼** |
| **negative control** | 紀錄齊全但**責任模型缺席**者 SHALL 失敗（R3.1 未過則本條不得單獨通過）|

## R4.1｜機器可判定的 invariant 須有 executable enforcement

| 欄 | 內容 |
|---|---|
| **EARS** | 凡 routing correctness invariant **可由機器判定者**，SHALL 存在一個**違反時會失敗**的可執行檢查 |
| **provenance** | **CONFIRMED institutional failure**（20260731：warning ＋ 人工規約 ＋ 無 enforcement → 3 筆 REGRESSION）|
| **scope** | 僅限**可機器判定**者；不涵蓋需人類產品判斷的 invariant |
| **falsifier** | 出現一個可機器判定的 routing invariant，**無** executable enforcement 卻能證明不會被違反 |
| **acceptance** | **以歷史動作重放**：對內容型 KB 補掛面向分類（＝20260731 的動作），該檢查 SHALL 失敗 |
| **negative control** | 移除該檢查後，同一動作 SHALL **靜默通過**——證明擋下它的是機制而非巧合 |

## R4.2｜人工規約不得為唯一 enforcement

| 欄 | 內容 |
|---|---|
| **EARS** | 人工維護規約 MAY 作補充，**MUST NOT** 作為**唯一** correctness enforcement |
| **provenance** | **CONFIRMED institutional failure** |
| **scope** | ⚠️ 不禁止人工 review／checklist；不主張「categories 不該存在」|
| **falsifier** | 出現一個僅靠人工規約即可長期維持的 routing correctness invariant（需歷史證據）|
| **acceptance** | 每條被宣告的 routing invariant SHALL 標明其 enforcement 形式；標為「人工」者 SHALL 附**為何不可機器判定**的理由 |
| **negative control** | 一條可機器判定卻標為「人工」的 invariant SHALL 被本條判為不合格 |

## R5.1｜不得假設 evidence semantics 同質

| 欄 | 內容 |
|---|---|
| **EARS** | authority model SHALL NOT 假設所有 entry source 共享同一種 evidence semantics，亦 SHALL NOT 假設 query text alone 普遍足夠 |
| **provenance** | **SUPPORTED, NOT NECESSARY**（⚠️ 展開**不得**升成 NECESSARY；升格條件：trigger／vision／session 任一出現**實測 misrouting**）|
| **scope** | 契約宣告層 |
| **falsifier** | 出現一個以單一 evidence semantics 即可正確治理全部五路的實測方案 |
| **acceptance** | 每個**納入治理範圍**的 entry source SHALL 具名其 authority evidence 來源；未納入者 SHALL **明示 scope-out ＋ 理由** |
| **negative control** | 把某路 scope-out 而**不附理由**者 SHALL 失敗——防止再現 Level-A 式**無證據白名單** |

## R5.2｜query-only classifier 不足以治理非 query 來源

| 欄 | 內容 |
|---|---|
| **EARS** | **query-only classifier** SHALL NOT 被當作 session state／caller assertion／vision 等**非 query evidence** 來源的充分 authority |
| **provenance** | **SUPPORTED, NOT NECESSARY** |
| **scope** | ⚠️ 僅針對 **query-only**；輸入已含 session／caller assertion／image／entry-source type 者**不在**本條射程 |
| **falsifier** | 出現 query-only 判定即能正確治理 trigger／vision／session 的實測結果 |
| **acceptance** | 若某非 query 來源的 entry 之 authority 僅由 query 判定構成，SHALL 判為不合格 |
| **negative control** | 提出「trigger_facet_key 僅由 query classifier 治理」的設計，SHALL 被本檢查擋下 |

---

## 展開後仍 unresolved（**未因可測化而被解掉**）

```text
L2／L3／L4／L6 主責任層           INSUFFICIENT EVIDENCE
H1／H2／H3 single winner          INSUFFICIENT EVIDENCE
routing false-reject 可接受代價    PRODUCT DECISION PENDING
   ⚠️ **僅當** design candidate 可能以「拒絕本來應進場的 Face」作為 trade-off 時才需先裁示；
      **不得**為尚未存在的 candidate 預訂 5%／10% 之類 threshold
```

⚠️ 本檔**零元件指名**：所有 acceptance 皆以**行為契約 ＋ 反事實對照**表述，
故不預設任何一層擔任主責。
