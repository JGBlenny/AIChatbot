# 實作任務：routing-disambiguation

> 建立 2026-08-23｜語言 zh-TW
> 來源：[requirements.md](./requirements.md)（9 需求／35 子需求）、[design.md](./design.md) **v1.2**
>（v1.1 ＋ [erratum 01](./design-erratum-01-block-scope.md)：membership 改 Face 層語義契約、與 rollout scope 正交）、
> [gap-analysis.md](./gap-analysis.md)、[research.md](./research.md)、
> [robustness-protocol.json](./robustness-protocol.json)（v1，digest `4690a258f502d98d`）
> ⚠️ `.kiro/settings/rules/tasks-generation.md`、`tasks-parallel-analysis.md`、
> `templates/specs/tasks.md` 均不存在，沿用前案已建立的格式與註記慣例。

## 註記圖例

| 註記 | 意義 |
|---|---|
| **⚡F** | 可交 Fable 執行：全機械、brief 可一次寫完、無設計判斷 |
| **🧠主** | 須主 session 親自做：判型、裁決、跨元件整合、產品判定 |
| **🔍V** | 完成後須獨立代理驗證 |
| **(P)** | 可與同層其他 (P) 並行（無共享檔案、無順序依賴）|

---

## ⚠️ 完成的定義（本 spec 與一般實作任務不同）

```text
Candidate implementation complete   ≠   Design validated
```

**真正的完成條件**：

```text
protocol v1 PASS
＋ protocol v2 structural invariants PASS      ← 2026-08-23 業主裁示新增
＋ unseen holdout PASS
＋ matching ruleset／protocol／dataset digests
＋ Level A regression／blast-radius PASS
```

⚠️ **v2 不取代 v1、不改 v1 的尺**；但 **N4 是 design correctness contract，
最終必須綠**——不得因為「v1 已凍結」就把 v2 當旁觀者。
⚠️ **N4 的定性**：deterministic contract／future-proof invariant，
**不是 production incident reproduction**（語料現無天然 multi-face KB），
故**不受 Req.9.3 的 ≥30 可判定案例限制**——那條約束的是 holdout 的統計效力，
與結構不變量無關。

⚠️ **holdout 不是「最後補一個測試任務」，它是本方案是否成立的裁決點。**
若 holdout 失敗，正確結果是 **candidate REFUTED**，
**不是**回頭改 regex 直到 holdout 轉綠——
**一旦看過 holdout 再調 ruleset，那批資料就不再是 holdout，必須另建新的未見集合**（Req.9.2）。

## ⚠️ 明確不生成 implementation task（contingency／future work）

| 項目 | 現況 | 為何不做 |
|---|---|---|
| `FACET_SCOPE_SALVAGE` | 前案已設計、未實作 | gap 判 L4-b `INSUFFICIENT_EVIDENCE`；**非選定方案**，僅 design candidate |
| L3 intent taxonomy 增維 | 未選定 | `api_required` 0/54 未供裝、與 taxonomy 正交；重啟 Step 3 為獨立成本決策 |
| L5 clarification | 未選定 | 無可靠 ambiguity detector；重啟條件為 abstain 率過高（design 決策 3）|
| L6 144 筆 data hygiene | 後續獨立工作 | 本案只約束 exposure surface 的**使用方式**，不消除結構共居 |

---

## 執行順序（因果，非元件編號）

```text
1. 先建立會失敗的契約與 negative controls   ← 最先；且必須先確認它們是紅的
   ↓
2. InstanceEvidence／extractor
   ↓
3. InstanceReferenceGate
   ↓
4. production seam 整合（旗標預設 OFF）
   ↓
5. protocol v1 驗收
   ↓
6. unseen holdout ← **裁決點**
   ↓
7. Level A 範圍宣告與啟用
```

⚠️ **順序 1 不可後移**：契約若在實作之後才寫，就會被寫成「剛好符合已完成的實作」。

---

## 1. 先建立會失敗的契約與 negative controls

**目標**：在任何實作之前，先讓「什麼算失敗」成為可執行的斷言。
⚠️ 本任務完成時這些測試**應該全部是紅的**——那是它們有效的證明（Req.6.5）。

- [x] 1.1 **🧠主** 建立**啟用守門**的 negative control：四路皆須拒絕啟用——
  `status="not_run"`／`status="failed"`／`passed` 但 ruleset digest 不符／
  `passed` 但 protocol digest 不符；僅三者相符才允許。
  ⚠️ 特別鎖 `failed` 那一路——原設計的 `result != None` 只防 missing、不防 failed。
  _Requirements: 3.5, 9.2_

- [x] 1.2 **⚡F** (P) 建立**wrong facet ≠ success**的斷言：instance 問句進入
  「條件診斷：帳單」以外的任何 dialog SHALL 判為失敗。
  ⚠️ 前案兩度因只驗 `route == "dialog"` 而把跑錯面向算成成功。
  _Requirements: 1.4_

- [x] 1.3 **🧠主** 建立 **multi-category negative control** 並納入 **protocol v2**
  （**不得改 v1**）：一個 rule 問句，其 top-1 KB 掛兩個以上分類且其中兩個皆為
  instance-requiring Face，斷言最終仍為 `single`。
  ⚠️ 沿用 `continue` 下一分類無法保證 Req.1.2；凍結案例集三筆恰為單一相關分類，
  會出現「案例綠但契約未成立」。
  _Requirements: 1.2, 1.3_

- [x] 1.4 **⚡F** (P) 建立 **Level A scope isolation** 斷言：旗標開啟時，
  **白名單以外的 Face 行為完全不變**（取數個非帳單域面向的代表問句對照）。
  ⚠️ 防「帳單 8/8 但偷偷改了 21 Faces」。
  _Requirements: 2.5, 5.2_

- [x] 1.5 **🧠主** 逐 **test ID** 檢視 1.1–1.4 的 semantic failure reason，
  確認每一條的紅是**斷言本身**造成的，而非只是缺少實作；綠的各條逐一說明其定性
  （preservation／rollout-safety／量尺自我守門），並記錄各自的失敗訊息。
  ⚠️ 這是 negative control 的 negative control——**守門若一開始就是綠的，它守不到任何東西**。
  ⚠️ **看測試名稱＋失敗原因，不看 failed 總數**；1.3／1.4 刻意不是全紅。
  _Requirements: 6.5_

- [x] 1.6 **🧠主** **Design Erratum：裁定 `block` 的作用域**
  （1.5 之後、**任何 candidate implementation 之前**；業主裁示 2026-08-23）。

  ⚠️ **SHALL NOT 直接在 (a) 擴白名單／(b) query-scoped 抑制之間二選一**——
  那是「如何表示」，不是「要表示什麼」。**先回答責任集合**：

  > **rule 判定成立後，哪些 Routing Hints 屬於同一個「應被抑制的
  > instance-routing responsibility」？其 membership 依據是什麼？**

  作用域的單位 SHALL 明確：**Face／routing family／整筆 KB 的 hints** 擇一並說明理由。
  兩條硬約束：

  ```text
  不得靠「所有 required_slots 非空」  → Must 1 已否決該全域等價（22 Face 中 13 個非空）
  不得靠「任何 dialog 都封掉」        → 會越過 Level A，變成另一種全域 heuristic
  ```

  ⚠️ **`billing_anomaly` 另有 Req.4 的產品歸屬未決案例**——
  SHALL NOT 因為 N4 技術上需要它就宣告它屬於 scope
  （「技術上需要它 → 所以產品上它屬於 scope」是本案明令禁止的推論形態）。

  **三條不可違反的裁定原則（業主 2026-08-23）**：

  ```text
  ① membership SHALL NOT = bool(required_slots)
  ② membership SHALL NOT 因「有 bill_ref」就自動成立
     —— 共用 execution slot ≠ 共用 routing responsibility
  ③ 未決 Face 不得因 N4 技術需要，自動被升格為產品上應納管的 Face
  ```

  任何方案若**必須先假定**「`billing_anomaly` 與 `bill_diagnosis` 本來就是同一
  responsibility」才能成立，一律標 **BLOCKED BY PRODUCT DECISION**，
  不得自行補上假設。

  **選項分析已產出（2026-08-23）**：
  [design-erratum-01-block-scope.md](./design-erratum-01-block-scope.md)
  ——五個選項（A 明列 key／B bill-ref family／C Face 層語義宣告／
  D query-scoped（**正交，非並列**）／E 整筆 KB（**預期 loser，具名以便禁止**）），
  每個固定產出六項：membership predicate／blast radius／N4 行為／Level A isolation／
  **Req.4 coupling（硬欄位）**／falsifier。**狀態：RULING PENDING。**
  _Requirements: 1.2, 2.5, 4.2_

---

## 2. `InstanceEvidence` 與決定性抽取器

- [x] 2.0 **🧠主** ⚠️ **本輪第一件事：跑 erratum 01 的 falsifier**——
  對「我的收據在哪」「我這筆點退的錢怎麼怪怪的」跑 extractor：
  判 `allow`／`abstain` → 1.6 裁定維持；判 **`block`** → **1.6 裁定立即失效**，
  停止 Task 2、重開 erratum，**不准靠修改測試繼續**。
  _Requirements: 4.2, 1.3_

- [x] 2.1 **🧠主** 定義 `InstanceEvidence` 值物件：正向證據、反向證據、`spans`。
  ⚠️ `spans` 用 **immutable tuple**——`@dataclass(frozen=True)` 只凍結欄位綁定，
  dict 內容仍可 mutate，型別契約會名不副實。
  _Requirements: 2.1, 3.1_

- [x] 2.2 **⚡F** (P) 實作正向特徵抽取：`identifier`／`possessive`／`lookup_verb`／`problem_report`，
  複用 `conversational_engine.py` 既有 id-like／ordinal 抽取慣例，不新造。
  _Requirements: 2.1_

- [x] 2.3 **⚡F** (P) 實作反向特徵抽取：`explanation_request`。
  ⚠️ research 實測顯示它比任一正向特徵更強（8/9 vs 最高 5/11）——
  **只找正向特徵會漏掉「規則問句」這一半**。
  _Requirements: 2.1_

- [x] 2.4 **⚡F** 實作 `extract(None)`／`extract("")` → 回空 evidence。
  ⚠️ **不得靠 exception → fail-open 間接達成**：靠例外的行為不會被型別或測試鎖住。
  _Requirements: 3.1_

- [x] 2.5 **🧠主 🔍V** 建立抽取器的**不變量測試**：零 LLM 呼叫、零 IO、
  **不讀取任何相似度分數**。
  **🔍V 理由**：與相似度正交是本元件存在的唯一理由（Req.3.1）；
  若它偷讀分數，整個方案退化為「換個地方做相似度競爭」（Req.2.3）。
  _Requirements: 2.3, 3.1, 3.4_

- [x] 2.6 **🧠主** 建立 `RulesetManifest`：規則集內容雜湊、版本、`HoldoutRecord`。
  規則集為**版本化資產**，變更即須重跑並保留前版結果。
  _Requirements: 3.5, 7.2_

---

## 3. `InstanceReferenceGate`

- [x] 3.1 **🧠主** 實作三值判定 `allow`／`block`／`abstain`，並回傳可稽核的 `reason`
  （命中哪些正／反向證據）。
  _Requirements: 1.1, 1.2, 3.1_

- [x] 3.2 **🧠主** 實作 `block` 的**雙條件**：需同時「無正向證據」且「有反向證據」。
  ⚠️ 反向標記**不得採 veto**——實測有一筆 instance 案例同時命中 possessive 與
  explanation_request，veto 會誤殺，正是 3.4 那類「修一邊傷另一邊」。
  _Requirements: 1.3_

- [x] 3.3 **🧠主**（⚠️ **改排入 Task 4**：本條要求的是 **seam-level suppression semantics**，
  gate 純函式階段做不到，也不該偷做——業主 2026-08-23 裁示）
  實作 `block` 的**作用域**：抑制該問句對**白名單內所有 instance-requiring Face**
  的 Hint，**不是** `continue` 下一個分類。非白名單 Face 不受影響。
  _Requirements: 1.2, 2.5_

- [x] 3.4 **⚡F** 補測試鎖住 **`abstain` 不得被摺疊**成 `allow` 或 `block`。
  ⚠️ 訊號不足時假裝有結論，正是本案要消滅的失敗形態。
  _Requirements: 1.3_

---

## 4. production seam 整合

- [x] 4.1 **🧠主** 實作**兩層**判定（erratum 01 改判；**取代原白名單版本**）：

  ```text
  is_instance_requiring_face(cfg)  ← C：讀 Face 自身的 requires_instance_reference 宣告
  AND in_gate_rollout_scope(cfg)   ← D：本次 release 的啟用邊界（明列 key）
      ↓ 兩層同時成立
  gate_applies_to(cfg)
  ```

  ⚠️ **不得**用 `bool(cfg.grounding_scope.required_slots)`：其語義為「執行需要哪些欄位」，
  未來 Face 可能 required `date`／`reason`／`amount`，皆非 entity reference
  （實查：22 Face 中 13 個非空）。
  ⚠️ **不得把兩層摺疊成一層**——摺疊後 Level B 擴張就得改 membership 定義，
  語義契約會退化成 rollout 清單。
  ⚠️ **Face 宣告逐一裁定，禁止批次推導**：現況僅 `bill_diagnosis` 為 `true`；
  `billing_anomaly` 待逐 Face 裁定；`billing_invoice`／`billing_flow` 不得自動跟進。
  _Requirements: 2.5, 5.2, 8_

- [x] 4.2 **🧠主** 於 `_diagnosis_config_for_knowledge` 串接：
  `config_for_category` 命中之後、`_preentry_routable` 之前。
  旗標 `INSTANCE_REFERENCE_GATE` **預設 `false`**。
  _Requirements: 1.1, 1.2, 7.1_

- [x] 4.3 **🧠主 🔍V** 驗證 `facet_entry_eligible` 的**等價契約未被破壞**——
  `decision_layer` 檔頭明訂該函式對任意輸入須與搬移前 inline 邏輯嚴格同輸出。
  新 gate SHALL 為獨立函式，不改動既有門檻判定。
  **🔍V 理由**：破壞等價契約會使前案建立的 171 條整合護欄失去對照意義。
  _Requirements: 8_

- [x] 4.4 **⚡F** 實作 fail-open：抽取或判定例外 → `abstain` → 不阻擋
  （沿 `_preentry_routable` 慣例）。
  _Requirements: 1.3_

---

## 5. protocol v1 驗收（**不得改尺**）

- [x] 5.1 **🧠主** 以凍結案例集驅動 **production seam**（Req.6.1，不得在測試內重演 routing 語義）：
  `RULE 4 → single`／`INSTANCE 4 → dialog:條件診斷：帳單`／`CONTROL 5` 不變。
  門檻 `bilateral_pass = 8/8`（雙邊缺一不可）。
  _Requirements: 1.1, 1.2, 1.3, 6.1_

- [x] 5.2 **🧠主** 執行擾動 P1 `corpus_add_sibling`×3／P2 `semantic_model_rebuild`×1／
  P3 `phrasing_variant`×1，量 `flip_rate ≤ 1/8` 且**不得有任一筆反覆翻面**。
  _Requirements: 3.2, 3.3_

- [x] 5.3 **🧠主** 記錄 `decision_margin`（**只記錄、不設門檻**）——
  用於證明判別**不靠邊際**，而非把邊際拉大就算過。
  _Requirements: 3.1, 3.4_

- [ ] 5.4 **🧠主 🔍V** blast radius：先依 Req.5.2 逐筆判定 20260731 同批七筆的
  **intended behavior**（產品裁示或既有規格），僅有產品依據支持者入 assertion；
  七筆**全數實測記錄**（不論是否入 assertion）。
  **🔍V 理由**：此處最容易把「現行行為」直接當成「應維持的行為」（Req.7.3）。
  _Requirements: 5.2, 7.3_

---

## 6. unseen holdout ⭐ **裁決點**

⚠️ **順序不可對調**——五步做完才跑 extractor。

- [ ] 6.1 **🧠主** 自 exposure KB／domains 抽樣，記錄抽樣方法與 seed。
  _Requirements: 9.3_

- [ ] 6.2 **🧠主** 取得**未參與 ruleset 建構**的 user utterances
  （優先取真實回報／既有語料；生成者須與規則作者隔離）。
  ⚠️ **不得**「抽 30 個 KB → 照其 wording 改寫 query」——那與 source text 高度同源，
  是換個形式的 overfit。
  _Requirements: 9.3, 9.2_

- [ ] 6.3 **🧠主** **盲標**：在不知道 extractor 判定結果的情況下做產品標註，
  完成即**凍結 labels** 並計入 `dataset_digest`。
  ⚠️ rule 與 instance **兩側都必須有案例**——只驗一側會重演前案的單邊假綠。
  _Requirements: 9.3, 1.3_

- [ ] 6.4 **🧠主** 最後才跑 extractor，產出 `HoldoutRecord`
  （status／ruleset digest／protocol digest／dataset id＋digest）。
  _Requirements: 3.5_

- [ ] 6.5 **🧠主 🔍V** **裁決**：

  | 結果 | 處置 |
  |---|---|
  | PASS ＋ 三重 digest 相符 | 進任務 7 |
  | FAIL | **candidate REFUTED**——記錄反證，**不得回頭改 regex 直到轉綠** |

  ⚠️ 一旦看過 holdout 再調 ruleset，**那批資料就不再是 holdout**，須另建新的未見集合。
  **🔍V 理由**：這是本方案唯一的裁決點，且最容易被「再調一下就過了」侵蝕。
  _Requirements: 9.2, 9.3, 3.5_

---

## 7. Level A 範圍宣告與啟用

- [ ] 7.1 **🧠主** 依實測宣告 Req.2.5 的**適用範圍**：
  Level A（帳單域驗證）或 Level B（跨 exposure surface，需 ≥30 跨域可判定案例）。
  ⚠️ 僅在帳單域驗證者 SHALL 明確標示範圍，**SHALL NOT 表述為通用解**。
  _Requirements: 2.5, 9.1, 9.4_

- [ ] 7.2 **🧠主 🔍V** 啟用 `INSTANCE_REFERENCE_GATE`：須先通過
  `assert_gate_enablable()` 的三條檢查。
  **🔍V 理由**：外部行為變更；且啟用守門本身是本設計的核心防線。
  _Requirements: 3.5, 7.1_

- [ ] 7.3 **🧠主** 驗證四筆 routing known-red 轉綠，且雙向 suite 兩側同時成立。
  _Requirements: 5.3, 1.3_

- [ ] 7.4 **🧠主** 依 Req.4.2 判定 `BILLING_INSTANCE_FACET_UNDECIDED` 兩筆的產品歸屬
  （產品裁示或既有規格；**現行 route／embedding 分數／migration provenance 三者
  皆不得單獨作為依據**），判定後始得入正向斷言。
  _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 7.5 **🧠主** 結論分級：僅通過現有基準者 SHALL 僅聲稱「技術可行／regression-safe」；
  「routing 品質確實提升」SHALL 僅在通過 production holdout 後聲稱。
  _Requirements: 9.1, 9.2_

---

## 需求覆蓋對照

| 需求 | 任務 |
|---|---|
| 1.1 | 3.1, 4.2, 5.1 |
| 1.2 | 1.3, 3.1, 3.3, 4.2, 5.1 |
| 1.3 | 1.3, 3.2, 3.4, 4.4, 5.1, 6.3, 7.3 |
| 1.4 | 1.2 |
| 1.5 | 7.1 |
| 2.1 | 2.1, 2.2, 2.3 |
| 2.2 | gap-analysis 已完成（六層評估，含 loser 證據）|
| 2.3 | 2.5 |
| 2.4 | gap-analysis 已完成（no winner 為合法結論）|
| 2.5 | 1.4, 3.3, 4.1, 7.1 |
| 2.6 | gap-analysis 已完成（六層 disposition ＋ falsifier）|
| 3.1 | 2.1, 2.4, 2.5, 3.1, 5.3 |
| 3.2 | 5.2 |
| 3.3 | 5.2 |
| 3.4 | 2.5, 5.3 |
| 3.5 | 1.1, 2.6, 6.4, 6.5, 7.2 |
| 4.1 | 7.4 |
| 4.2 | 7.4 |
| 4.3 | 7.4 |
| 4.4 | 7.4 |
| 5.1 | 5.4 |
| 5.2 | 1.4, 4.1, 5.4 |
| 5.3 | 7.3 |
| 6.1 | 5.1 |
| 6.2 | 5.1, 5.2 |
| 6.3 | 5.1 |
| 6.4 | 5.1 |
| 6.5 | 1.5 |
| 7.1 | 4.2, 7.2 |
| 7.2 | 2.6 |
| 7.3 | 5.4 |
| 8 | 4.1, 4.3；並見文首「明確不生成 implementation task」表 |
| 9.1 | 7.1, 7.5 |
| 9.2 | 1.1, 6.2, 6.5, 7.5 |
| 9.3 | 6.1, 6.2, 6.3, 6.5 |
| 9.4 | 7.1 |

⚠️ Req.2.2／2.4／2.6 已於 **gap 階段完成**（六層評估、逐層 disposition、no winner），
故不生成新的 implementation task——**重做會使已凍結的 disposition 失去意義**。

## 註記統計

| 註記 | 數量 |
|---|---|
| **⚡F** | 7（1.2, 1.4, 2.2, 2.3, 2.4, 3.4, 4.4）|
| **🧠主** | 20 |
| **🔍V** | 7（1.1 隱含於 1.5、2.5, 4.3, 5.4, 6.5, 7.2；含 1.5）|
| **(P)** | 2 組（1.2／1.4、2.2／2.3）|

**🔍V 集中於四類風險**：守門本身是否有效（1.5、7.2）、與相似度正交的驗證（2.5）、
等價契約不被破壞（4.3）、現行行為被當成應維持行為（5.4）、**裁決點被侵蝕**（6.5）。


---

## 實作進度

### ✅ 1.1（2026-08-23）

`rag-orchestrator/tests/unit/decision/test_instance_gate_enable_invariant_req.py`
——6 筆測試，**全紅**（預期）：

```text
passed=0  failed=6
ImportError: cannot import name 'instance_reference_gate' from 'services'
```

四條拒絕路徑（`not_run`／`failed`／ruleset digest 不符／protocol digest 不符）
＋ 一條允許路徑 ＋ 一條「不得降級為 warning」。
import 置於各測試函式內，使四條路徑**各自**變紅——整檔於收集階段 error
會只看到一個錯誤，看不出各條是否都有被斷言。

`ACTIVE_PROTOCOL_DIGEST` 釘死 protocol v1 的 `4690a258f502d98d`。

> ⚠️ **1.1 的紅尚不足以證明斷言有效**：六筆紅在**同一個 ImportError**，
> 一個寫錯的斷言（例如 `pytest.raises` 包錯範圍）此刻同樣顯示為紅。
> 逐條確認「紅的原因是斷言本身而非缺少實作」**留待任務 1.5**。

### ✅ 1.2（2026-08-23）

`rag-orchestrator/tests/unit/decision/test_protocol_facet_verdict_req.py`
——12 筆測試，**全紅**（預期）：

```text
passed=0  failed=12
ModuleNotFoundError: No module named 'scripts.routing'
```

被測對象是**量尺**而非 production routing：餵它一筆已知為錯的觀測結果
（instance 問句進入非「條件診斷：帳單」的 dialog），證明它確實判 `fail`。
integration 既有的正向斷言只能證明「對的時候會綠」，**不能證明「錯的時候會紅」**。

涵蓋：五個錯面向（含 **3936「帳單異常」——前案真正跑錯、卻被記為通過的那一個**）／
正確面向須綠（防恆紅）／`facet=None` 不得判 pass（前案判定式的形狀）／
instance 落回單發＝fail／**彙總層**：RULE 全 single ＋ INSTANCE 全進錯面向
不得報 `bilateral_pass`／期望值取自凍結檔且 digest 釘死 v1／`UNDECIDED` 判
`unscored` 而非 pass。

**量尺落點決策**（design 未指定，主 session 裁定）：
`scripts/routing/protocol_v1.py`，沿 `scripts/backtest/decision_replay.py`
（量尺為版本化資產、另立 unit 測試）的既有慣例。契約面僅兩支函式
`score_case()`／`bilateral_pass()` 加 `expected_for()`／`PROTOCOL_DIGEST`，
刻意壓到最小——先寫的契約若把 API 攤開，實作就會被寫成「剛好符合契約」。

> ⚠️ **證據等級（業主裁示 2026-08-23）**：
>
> ```text
> 1.2 COMPLETE
>   = contract scaffold exists
>   = 12/12 pre-implementation red
>   ≠ semantic effectiveness proven
> ```
>
> 12 筆紅在**同一個 ModuleNotFoundError**，此時「正確的斷言」與「寫反的斷言」
> **一樣紅**，恆綠／恆紅量尺尚無法區分。把它升格為「有效守門」的是**任務 1.5**：
> 實作最小必要 module 後，逐條看到它們因**預期的 semantic reason** 紅／綠。
> 引用本筆證據時 SHALL NOT 用 `12 failed` 支撐超過上述等級的主張。
> 已先驗證凍結檔在容器內可讀（`/.kiro/...`，digest `4690a258f502d98d`，
> RULE 4／INSTANCE 4），確保 1.5 檢視時不會混入第二個失敗來源。

**未動既有紅綠**：unit `1021 passed` 前後一致；新增前 19 failed，新增後 31 failed，
差額恰為本檔 12 筆。

⚠️ **`_meta` 13 筆的定性（業主裁示 2026-08-23）**：
`tests/unit/_meta/test_env_parity_req.py`（6）與 `test_runner_layer_contract_req.py`（7）
讀取 repo root 的 `docker-compose.prod.yml`／`scripts/run-tests.sh`／`.github/workflows/tests.yml`，
而測試容器只掛 `/app`(=rag-orchestrator)、`/docs`、`/.kiro`。
故：**這 13 筆在目前 container mount topology 下不可判定，屬 execution-environment
mismatch；不得計入 product/unit regression delta。**

比較方式 SHALL 為：

```text
targeted task tests   → 必須精確判紅綠（看測試名稱＋失敗原因）
container unit delta  → 排除**已指名的 13 個 test ID**，而非只把數字減 13
_meta contracts       → 於具 repo-root artifacts 的環境另外執行
```

⚠️ **不得寫成「日後先扣掉 13 筆」**——固定扣數字會讓第 14 筆同類的**真** regression
被心理上一併忽略。尤其任務 1.5 SHALL 看測試名稱與失敗原因，**不看 failed 總數**。

### ✅ 1.3（2026-08-23）

`.kiro/specs/routing-disambiguation/robustness-protocol-v2.json`（digest `26a6199116f738ec`；
建立時為 `791e84c38ae813fd`，補 metadata 後 **superseded_before_use**，見下方 1.4 後的補記）
＋ `rag-orchestrator/tests/integration/conversational/test_multi_category_gate_scope_req.py`
——6 筆，**2 紅 4 綠**（見下方紅綠定性）：

```text
passed=4  failed=2
AssertionError: rule 問句在 categories=['條件診斷：帳單','帳單異常'] 下進了「bill_diagnosis」
AssertionError: rule 問句在 categories=['帳單異常','條件診斷：帳單'] 下進了「billing_anomaly」
```

**v1 未動**：`robustness-protocol.json` 未出現在本次 diff；測試內逐次重算並回證
`4690a258f502d98d`。新增案例一律進 v2，provenance＝design v1.1 業主審查 **Must ④**
（`block` 改抑制同型 Hint、非 `continue` 下一分類）。凍結時間因果「先凍量尺 → 再看方案」
因此維持完整。

**鎖的是產品效果，不是迴圈實作**，且雙邊：

| 斷言 | 現況 | 定性 |
|---|---|---|
| rule ＋ multi-category → `single`（兩種 categories 順序） | 🔴 ×2 | 契約逼出的未決設計問題 |
| instance ＋ **相同** shape → `bill_diagnosis` | 🟢 | **preservation**：擋「整列 categories 全封掉」的省事修法 |
| 旗標關閉 → 行為與今日一致 | 🟢 | **rollout-safety**：斷言「關閉時不變」，**非**「今日 route 是對的」 |
| 兩個分類確實各解析到一個 bill_ref 型 Face | 🟢 | 守門本身沒悄悄失效（退化成單分類情境仍會全綠）|
| 案例取自凍結 v2 ＋ v1 digest 回證 | 🟢 | 防「事後把量尺改成剛好符合實作」|

⚠️ **本檔刻意不是全紅**，四筆綠各有理由並逐條標於 docstring；
它們是 preservation／rollout-safety／量尺自我守門，**不是「已經修好」的證據**。

**⚠️ 逼出的未決設計問題（進 v2 `open_conflict_for_task_4_1`，本檔不預選解法）**：
任務 4.1 的 Level A 白名單（`face key == bill_diagnosis` 且 `bill_ref ∈ required_slots`）
只涵蓋**一個** Face，但 N4 rule_side 要求 final 為 single，需要「帳單異常」
（`billing_anomaly`，`required_slots=['bill_ref']`）也被抑制——**兩者目前不相容**。
任務 3.3／4.1 須擇一裁定：(a) 白名單擴為 bill_ref 型帳務 Face 集合
（`bill_diagnosis`／`billing_anomaly`／`billing_invoice`／`billing_flow`）；
或 (b) 維持單一 Face 並改以 query-scoped 抑制表述。**裁定前這兩筆必然為紅。**

**⚠️ 語料實況（實查 `aichatbot_test`，corpus digest `918b69ce70fbb8f1660819c3774eb24b`）**：
**categories 解析後掛到兩個以上 Face 的 KB 為 0 筆。**
74 筆 `categories≥2` 中 58 筆碰到帳務分類，但配對者多為主題分類（帳單管理／付款金流／
合約管理／發票開立），皆非 Face；3497／3500／3501／3502（`['條件診斷：付款','繳費金流排障']`）
與 3503／3504（`['條件診斷：發票','發票']`）**看似 multi-face，實則
「條件診斷：付款」「條件診斷：發票」沒有 Face 設定**，`config_for_category` 回 None。
故本控制以**合成 KB row** 驅動 production seam（決策全走 production，僅 KB row 為輸入）；
新增語料會變更 corpus digest、破壞 v1 凍結，故不走種資料。
L6 共居 hygiene 為 future work，語料隨時可能長出天然案例——**契約先於資料存在**即其價值。

**未動既有紅綠**：integration 由 `177 passed + 4 known-red` → `181 passed + 6 failed`，
差額恰為本檔 4 綠 2 紅；原 4 筆 known-red 仍為原本那四筆（rule 側），未被本檔影響。

### ✅ 1.4（2026-08-23）

`rag-orchestrator/tests/integration/conversational/test_level_a_scope_isolation_req.py`
——6 筆，**2 紅 4 綠**：

```text
passed=4  failed=2
ModuleNotFoundError: No module named 'services.instance_reference_gate'   ×2
```

| 區塊 | 斷言 | 現況 | 定性 |
|---|---|---|---|
| A | `is_instance_requiring_face()` 判準 ≠ `bool(required_slots)` | 🔴 ×2 | scaffold（實作不存在）|
| B | 旗標 ON／OFF 下非 Level A Face 的 (route, facet) 完全相同 | 🟢 | preservation |
| C | **過寬** stub gate（開旗標即封所有 Face）SHALL 被判出漂移 | 🟢 | 證明 B 咬得動 |
| C | **正確** stub gate（只封 Level A）SHALL **不**被判出漂移 | 🟢 | 證明 B 有鑑別力 |
| — | 待裁定 Face 僅實測記錄、不入任一側斷言 | 🟢 | 不預選 erratum 解法 |

**判準證據（實查 22 個 Face）**：**13 個 required_slots 非空**——
`contract_ref`×6（contract_diag／contract_change／contract_sign／contract_closeout／
contract_renew／account_login）、`bill_ref`×4、`estate_ref`、`meter_ref`、`member_ref`、
以及 repair_create 的五槽。`bool(required_slots)` 會**一次納管 13 個 Face**，
這就是 Must 1 否決該等價的具體代價。

**C 的成對設計**：只有「過寬會紅」不夠——只會喊漂移的檢查同樣沒有鑑別力，
會把正確實作一起擋掉。故另加「正確 stub 不得被判越界」，並**先斷言該 stub 真的改了東西**
（Level A 代表問句 OFF 落 `bill_diagnosis`、ON 落 `single`），
否則「什麼都沒變當然沒漂移」會是空跑的假綠。

**判定式的關鍵細節**：一題是否在隔離宣稱範圍內，以 **OFF 側**的落點決定。
用 ON 側決定的話，「gate 把某題踢出 Level A」會讓那題自動退出宣稱——**漂移永遠測不到**。

**待 erratum 裁定者僅記錄不斷言**：`billing_anomaly`／`billing_invoice`／`billing_flow`／
`billing_late_fee` 四者既不入正向斷言、也不入隔離宣稱。實測記錄：
「滯納金怎麼收這麼多」→ `billing_late_fee`。

**未動既有紅綠**：integration 由 `181 passed + 6 failed` → `185 passed + 8 failed`，
差額恰為本檔 4 綠 2 紅。

### 📌 v2 自描述 metadata 補全並重新 freeze（2026-08-23，業主裁示）

```text
791e84c38ae813fd  →  superseded_before_use
26a6199116f738ec  →  現行 v2
```

**為什麼改**：不是內容缺失，而是 **provenance 分裂**——v2 本體只定義 N4 案例與量尺，
它的**制度地位**（additive／不取代 v1／最終收案必要條件）卻只寫在 tasks.md。
未來只拿到 evidence ＋ protocol artifact 的人，**無法從 v2 自身判讀它是什麼**。

**為什麼現在改不構成事後改尺**：修改時**尚無任何 candidate implementation，
亦未以 v2 量測過任何方案**（`supersedes.measurements_taken_against_it = "none"`）。
**僅補 metadata**：未動任何案例、expected route、metric 或 threshold（改檔腳本內逐塊回證
`additions`／`measurement_note`／`relation_to_v1` 逐字不變）。
⚠️ **一旦以 v2 量測過任何方案，再要變更 SHALL 另立 v3 並保留 v2 結果。**

補入欄位：`parent_protocol_digest`／`replaces_v1: false`／
`acceptance_role: required_additive_contract`／
`final_acceptance{protocol_v1_must_pass, protocol_v2_must_pass}`／
`provenance{id: design_v1_1_must_4, created_before_candidate_implementation: true}`／
`supersedes{...}`。這些**已成為可執行斷言**（1.3 測試逐條核對），不再只是散文。

**時間線（到此仍無 candidate implementation／candidate measurement）**：

```text
v1 freeze → gap／design → 發現 Must ④ → v2 建立 → 1.3／1.4 contract scaffold
→ v2 acceptance role 補全並重新 freeze
──────────────────────────────────────────── ↑ 到此為止
→ 1.5 → design erratum（1.6）→ Task 2 implementation
```

### ✅ 1.5（2026-08-23）

完整報告：[evidence/task-1-5-negative-control-audit.md](./evidence/task-1-5-negative-control-audit.md)

```text
母體 30 個 test ID（1.1 六＋1.2 十二＋1.3 六＋1.4 六）

A  semantic effectiveness proven   22 / 30
B  scaffold（待 candidate 模組）      8 / 30
C  契約本身有問題                     0 / 30
```

⚠️ **母體是 30 不是 26**——先前口頭說 26 是加錯；分母錯會讓覆蓋率看起來比實際好。

**方法：突變測試 13 個，全數被殺、0 survived。** 綠色不會自動等於有效，
故對每一條綠都問「什麼樣的錯誤會讓它變紅」，答不出來就不是 A。
成對突變是重點：**M10（恆紅）／M11（恆綠）** 與 **M8（恆稱無漂移）／M9（恆稱有漂移）**
——只證明「恆綠會被抓」不夠，恆紅的量尺同樣測不出東西，還會擋掉正確實作。

**業主指定的五項量尺結案條件，逐項以突變反證成立**：

```text
錯 facet            → 因 wrong facet 而 FAIL   ✓ M1／M11
single on instance  → 因 wrong route 而 FAIL   ✓ M11
UNDECIDED           → unscored（非 pass）       ✓ M2
正確 facet          → PASS                     ✓ M10（恆紅會被抓）
bilateral 假綠      → 被拒絕                    ✓ M3（單邊會被抓）
```

**方法論邊界（重要）**：本輪實作了**量尺** `rag-orchestrator/scripts/routing/protocol_v1.py`
——protocol v1 凍結在前、量尺照著實作，屬 measurement infrastructure。
**candidate（`InstanceEvidence`／gate／seam 整合）完全未動。**
故 1.1 六條與 1.4 兩條成員資格斷言**必然維持 B**：它們守的正是 1.6 裁定前不得開始的模組。
**這是順序紀律的必然結果，不是稽核缺口。**

**C ＝ 0**：無非預期紅綠，**無契約需先修**。
**尚不能宣稱** candidate 的 semantic effectiveness；
**可以宣稱**量尺與作用域判定式確實會咬到它們聲稱要咬的錯誤，且不會把正確實作誤判為越界。

**下一步 SHALL 為 1.6 design erratum，不是 Task 2。**

### ✅ 1.6（2026-08-23，業主裁定）

裁定全文：[design-erratum-01-block-scope.md](./design-erratum-01-block-scope.md)
（**分析原文不回頭改寫**，裁定另立於文末——才看得出裁定依據了什麼）。

```text
A 明列 key      REJECTED as membership source（第二 truth source）→ 改列為 D 的 rollout list
B family        REJECTED / INSUFFICIENT_JUSTIFICATION（無獨立 family 語義）
C Face 語義契約  SELECTED
D rollout scope SELECTED，與 C 正交
E 整筆 KB       REJECTED（安全性靠 corpus 偶然形狀）→ 保留為 explicitly rejected alternative
```

**本次 erratum 的核心不是「白名單放幾個 Face」，而是把兩個曾被混在一起的命題拆開**：

```text
Face 語義上屬不屬於 instance-routing responsibility   →  C
這次 release 有沒有資格對它啟用                        →  D
```

兩側契約因此對稱：`InstanceEvidence`（問句側）× `requires_instance_reference`（Face 側）
→ `InstanceReferenceGate`。**execution slot 被偷當成 routing semantics 的推論正式消滅。**

**design v1.2**：決策 6 改判、決策 2 精確修訂（保留「不新增 KB-row metadata」，
只撤回「`required_slots` 足以表示 instance requirement」，新增 Face 層語義契約）。

**Req.4 正式結論**：1.6 **不裁定**兩筆 undecided utterance 的 facet；
只要 extractor 對它們產生 positive instance evidence 就不進 block path，
故 **Face membership 與 utterance facet ownership 可分離**。
⚠️ **falsifier 已排為任務 2.0**：若實測判 `block`，本裁定立即失效並重開。

⚠️ **N4 rule 側在 `billing_anomaly` 完成逐 Face 裁定前仍為紅**——
裁定尚未做完，不是實作缺失，**不得靠改斷言轉綠**。

**契約同步（1.4 新增 2 條，皆 B／scaffold）**：兩層不得被摺疊、
Level A Face 須兩層皆成立。宣告載體取 `grounding_scope`
（與 `required_slots`／`enabled_gate` 同處，沿面向配置鍵契約慣例）——
**此為主 session 的實作載體選定**，erratum 只裁「Face 自身第一級宣告」。
1.5 稽核母體因此 **30 → 32**（A 22／B 10／C 0；A 絕對數未變，分母變動已明記）。

### ✅ 2.1／2.2／2.3 ＋ 2.0 falsifier（2026-08-23）

`rag-orchestrator/services/instance_evidence.py`（ruleset `ie-v1`）——
規則集**逐條取自 research.md 主題 1 的實測特徵表**，
**未針對 falsifier 兩句特調**（特調會讓 2.0 自我實現：為那兩句補到會 positive → PASS → 什麼也沒證明）。

**2.0 結果：PASS（extractor 層）**

```text
我的收據在哪            pos=['possessive']                       ctr=[]
我這筆點退的錢怎麼怪怪的  pos=['possessive', 'problem_report']     ctr=[]
```

⚠️ **PASS 之所以有意義，在於它不是「什麼都 positive」**——同一份規則集在凍結案例集上：

```text
RULE     4/4  pos=∅ ＋ ctr=explanation_request   → 雙條件成立，會被 block
INSTANCE 4/4  pos≠∅                              → allow
CONTROL  5/5  pos=∅（其中 2 筆 ctr 亦空 → abstain，行為不變）
BLAST    7/7  pos≠∅
```

若 RULE 側也全 positive，2.0 就是空跑的假綠。**兩側同看才構成證據。**

⚠️ **2.0 PASS 不決定 facet 歸屬**：SHALL NOT 據此宣稱 `billing_anomaly` 或
`bill_diagnosis` 正確；**Req.4 continues undecided**。

**gate 層的鎖已自動上膛**：`test_undecided_utterances_are_never_blocked` 以
`importorskip` 寫成——gate 尚未實作時自動略過（`[env]` 2 筆），
**任務 3.1 落地後自動生效**。寫成註解或待辦會被忘記，寫成自動上膛的斷言不會。

**已記錄、未修的 ruleset 缺口**（**不得為求好看而現在補 pattern**，留給 holdout 判真）：
`押金設算息怎麼計算`／`怎麼用 Excel 批次匯入帳單` 兩筆 CONTROL 的反向證據為空
——`怎麼計算` 不含 `怎麼算`。兩筆本就應為 single，gate 判 abstain 不改變行為，故不影響本輪。

**實作邊界**：`identifier` 的 id-like 樣式**逐字複製** `conversational_engine._ID_TOKEN_RE`
（含「與日期分隔符或數字相鄰者不算識別」這道 e2e 逼出的守門），
**不 import**——本模組須維持零相依零 IO（R3.1）。⚠️ **兩處不得漂移**，
同步守門列為任務 2.5 的不變量測試項。

### ✅ 2.4（2026-08-23）

`tests/unit/decision/test_instance_evidence_empty_input_req.py`——7 筆全綠。

```text
None ／ "" ／ "   " ／ "\n\t " ／ 全形空白  → empty evidence（Task 3 對應：abstain）
```

**同時鎖了反向**：抽取器**不得**有 blanket try/except——餵入結構上不合法的輸入
SHALL 拋出而非靜默回空。否則這兩件事在型別上不可區分：

```text
「沒有訊號」             ← 應回空 evidence
「extractor 壞掉後被吃掉」 ← 應向上拋，由 seam 依 4.4 判 abstain
```

fail-open 的正確位置在 production seam（任務 4.4），**不在抽取器內部**。

### ✅ 2.5（2026-08-23）

`tests/unit/decision/test_instance_evidence_invariants_req.py`——25 筆全綠。

鎖六件事：**零 LLM／零 IO／不讀相似度／決定性／真 immutable／spans 只保存命中片段**。

| 不變量 | 鎖法 |
|---|---|
| 零相依 | AST 走訪全部 import（含函式內延後 import），須 ⊆ `{re, dataclasses, typing}` |
| 零 IO | monkeypatch `builtins.open`／`socket.socket` 成拋出，抽取器仍須正常運作 |
| 不讀相似度 | AST 識別字中不得出現 similarity／score／rerank／embedding／llm；**且 `extract` 的參數只有 `question`——多一個參數就是分數的入口** |
| 決定性 | 同輸入跨 20 次、跨實例完全同輸出 |
| immutable | `FrozenInstanceError` ＋ `spans` 為 tuple（`frozen=True` 只凍欄位綁定，容器本身也須不可變）|
| spans | 每個 span 皆須出現在原文，且其標的須在證據集合內 |

**identifier 同步守門以 behavioral equivalence 鎖定，不比 regex 字串**：
15 筆 token 矩陣（整句純數字上下限／句中 token／日期斜線與連字號／四位數金額／
中英混合／小數／三位數／無數字／空字串／None）同時餵
`instance_evidence` 與 `conversational_engine._extract_identifier`，要求**逐筆同判**。
字串相等只證明兩行字一樣，證明不了 flags／邊界／日期排除／整句上下限在兩邊同樣生效。

**突變驗證 M14**：把 `_ID_TOKEN_RE` 的 `\d{4,15}` 改成 `\d{2,15}` →
矩陣中「三位數且非整句」立即轉紅。**守門會咬。**

⚠️ 寫本檔時抓到一筆**自己的測試 bug**（大小寫比對寫錯，恆真的 `import` 檢查）——
已刪除該冗餘檢查（AST 那條本就涵蓋任意位置的 import）。屬 1.5 分類的 **C**，
發現當下即修，未進 commit。

### ✅ 2.6（2026-08-23）—— Task 2 收束

`services/instance_reference_gate.py`（manifest ＋ 啟用守門；**不含 gate 判定，那是 3.1**）
＋ `tests/unit/decision/test_ruleset_manifest_req.py`（6 筆）。

**硬邊界已成為可執行契約**：

```text
ruleset digest   ✓
protocol digest  ✓
dataset digest   ✓
holdout not_run  ✗   → 仍不得啟用
```

`current_manifest().holdout.status` **恆為 `not_run`**，直到任務 6 的 unseen holdout 裁決。
⚠️ **測得出「PASS 時會放行」≠ production manifest 現在可以寫 PASS**——
第四種路徑用 synthetic manifest 測邏輯，不代表真實候選已通過 holdout。

其餘鎖定：規則集內容雜湊（正向／反向／版本任一改動 → digest 變 → 舊 PASS 失效）、
manifest digest 由**當前實際生效**的規則集算出（非寫死字串）、
pattern 表以 `MappingProxyType` 保**副本**（改來源 dict 不動既有 manifest）。

**1.1 六條 B → A 升格**：再跑 5 個突變（M15 退回 `result != None`／M16 拿掉 ruleset 綁定／
M17 拿掉 protocol 綁定／M18 降級為 warning／**M19 恆拒**），**全數被殺、0 survived**，
六條各自至少被一個殺掉。1.x 契約母體 32：**A 28／B 4／C 0**，
剩下 4 條 B 全部指向任務 4.1。

**2.0 的上膛條件已修正**：原本靠「模組存在」上膛，但 2.6 正好建立了同一個模組
（manifest 用），會讓它變成 `AttributeError` 紅、看起來像 falsifier 失敗。
改為以**判定函式存在**上膛（`hasattr(gate, "instance_reference_gate")`）。

---

## ✅ Task 2 收束判定

> **問句側 signal 是否已成為 deterministic、版本化、可稽核，
> 但尚未獲准影響 production routing 的 candidate asset？**

**是。** 四項逐一有據：

| 主張 | 依據 |
|---|---|
| deterministic | 2.5：零 LLM／零 IO／不讀相似度／同輸入跨 20 次跨實例同輸出 |
| 版本化 | 2.6：規則集內容雜湊，任一 pattern 或版本變動即改 digest |
| 可稽核 | 2.1／2.5：`spans` 保存命中片段且必在原文中；manifest 綁定三重 digest |
| **尚未獲准影響 routing** | 2.6：`holdout=not_run` → `assert_gate_enablable` 拒絕；**seam 尚未串接**（任務 4.2）|

**下一步進 Task 3**——那是這個 signal **第一次**取得 routing decision semantics。

### ✅ 3.1／3.2／3.4（2026-08-23）—— gate 判定，仍不碰 seam

`services/instance_reference_gate.py` ＋ `tests/unit/decision/test_instance_reference_gate_req.py`
（14 筆全綠）。判定表照 design v1.2 逐列實作，**未加任何產品 heuristic**。

**2.0 armed falsifier：gate 模組一存在即自動上膛，第一時間跑，PASS**
（4 passed／0 skipped，不再是 armed scaffold）：

```text
我的收據在哪            → allow    suppress=False
我這筆點退的錢怎麼怪怪的  → allow    suppress=False
```

1.6「membership 與 facet ownership 可分離」因此取得 **gate-level 第二層證據**
（第一層為 2.0 的 extractor 層）。⚠️ **仍不決定 Req.4 的 facet ownership。**

**凍結案例集的 gate 實測**（`face_requires_instance=True`）：

```text
RULE      4/4  block    suppress=True    ← no-positive + counter，雙條件成立
INSTANCE  3/4  allow    suppress=False
          1/4  abstain  suppress=False   ← 正反同時命中，**未被 veto 誤殺**
UNDECIDED 2/2  allow    suppress=False
CONTROL   3/5  block（本就應單發，不受影響）／2/5 abstain（no-signal）
```

**突變驗證（5 個，全數被殺）**：

| ID | 突變 | 被殺數 |
|---|---|---|
| M20 | 反向標記採 veto（`if counter: block`）| 6 |
| M21 | abstain → block（第三態塌向 block）| 5 |
| M22 | **abstain → allow**（最容易被忽略的方向）| 4 |
| M23 | no-signal → allow（無訊號假裝有結論）| 2 |
| M24 | rollout action 併回 verdict（abstain 也抑制）| 1 |

⚠️ **verdict 與 rollout action 分屬兩欄**：`suppresses_hint()` 只認 `block`。
`abstain` 的政策效果像 allow，**語義不是 allow**——稽核、holdout 的 abstain 率、
未來 L5 clarification 都要讀得到它。M24 就是把兩者併回一欄的突變，已被鎖住。

### ✅ 3.3（業主編號）＝ 任務 4.1 的兩層判定（2026-08-23）

⚠️ **編號對照**：業主的「3.3 membership／rollout scope 合取」＝ tasks 原編號 **4.1**；
tasks 原編號 **3.3（`block` 作用域）** 因屬 seam-level，**改排入 Task 4**。
兩者不是同一件事，此處記在 4.1 名下並於 3.3 加註。

```text
is_instance_requiring_face(face)   ← C：只讀 grounding_scope.requires_instance_reference
in_gate_rollout_scope(face)        ← D：LEVEL_A_INSTANCE_GATE_SCOPE = {bill_diagnosis}
gate_applies_to(face)              ← C ∧ D，**只有一行，沒有第三條隱藏推論**
```

**C 不得 fallback**：`bool(required_slots)`／`bill_ref ∈ required_slots`／`key == bill_diagnosis`
一律不得作為推導來源；**缺欄位 → `False`**（fail-closed by scope）——
舊 Face 未補宣告時不得被意外納管，Level A 的隔離才是結構性的而非靠運氣。

**Face 宣告落地**：`database/migrations/20260823_bill_diagnosis_requires_instance_reference.sql`
——**只改 `bill_diagnosis` 一個 Face**（逐 Face 裁定，禁止批次推導）。
已套 `aichatbot_test` 並回證冪等（第二次 `UPDATE 0`）。
⚠️ **production 未套**：屬線上操作，由業主自行執行
`bash rag-orchestrator/database/migrate.sh --apply`（帳本感知）；套用後須清設定快取。
⚠️ 宣告 ≠ 啟用：實際納管仍需 rollout scope 同時成立，且旗標預設 false、holdout 未過前不得啟用。

**1.4 四條 B → A 升格，並先過突變**：

| ID | 突變 | 被殺的 test ID |
|---|---|---|
| M25 | membership 退回 `bool(required_slots)` | membership_is_not_bool_required_slots／in_scope_but_undeclared |
| M26 | `gate_applies_to` 只看 C（丟掉 rollout scope）| membership_and_rollout_scope_are_two_separate_layers |
| M27 | `gate_applies_to` 只看 D（丟掉語義 membership）| **in_scope_but_undeclared**（見下）|
| M28 | membership 以 face key 推導 | in_scope_but_undeclared／two_separate_layers |
| M29 | 缺欄位預設 `True`（fail-open by scope）| 三條 |

⚠️ **突變當場抓到契約缺口**：原本只測「已宣告但不在 rollout scope」，
**M27（只看 D、丟掉語義 membership）不會被抓到**。
補上另一半「在 rollout scope 內但未宣告 → 不得納管」後，M27 才被殺。
兩層契約要**兩個方向都測**才成立——這正是 1.5 突變紀律要防的形態。

```text
1.x 契約母體 33（1.4 新增 1 條）

A semantic effectiveness proven   33 / 33
B scaffold                         0 / 33
C contract defect                  0 / 33
```

### ✅ Task 4（2026-08-24）—— GateDecision 第一次取得 production authority

`routers/chat.py`（**+55 行，全為新增**）＋ `services/instance_reference_gate.py`
（啟用狀態）＋ `tests/integration/conversational/test_instance_gate_seam_req.py`（15 筆全綠）
＋ `tests/unit/decision/test_instance_gate_activation_req.py`（12 筆全綠）。

**啟用是兩層，不是一個旗標**（業主 2026-08-23 裁示）：

```text
requested  = 旗標打開（運維意圖）
authorized = 規則集通過 matching holdout（證據授權）
active     = requested AND authorized
```

⚠️ **現階段把 env 設成 `INSTANCE_REFERENCE_GATE=true` 也不會生效**——
production manifest 仍 `not_run`。凍結案例集在「OFF」與「ON 但未授權」兩種狀態下
routing **逐筆完全相同**。

⚠️ **分母表述更正（業主 2026-08-24）**：該次比對共 **22 筆 utterance observations**
＝ **20 筆有驗收角色**（RULE 4＋INSTANCE 4＋CONTROL 5＋BLAST 7）
＋ **2 筆只觀察不計分**（UNDECIDED）。
先前寫成「全體 20 筆」是把 UNDECIDED 混進了計分集合。
**UNDECIDED SHALL NOT 進入 bilateral／pass 分母。**

**seam 位置照 design 不重排**：`config_for_category` 之後、`_preentry_routable` 之前。
之前不行（gate 需要 Face 的語義契約）；之後也不行（LLM 的機率判定會先對 query 下手，
deterministic 契約反而後到，責任順序顛倒）。**判定每個 query 只做一次**。

**抑制語義（原任務 3.3，改排於此）**：`block` 時抑制**所有 `gate_applies_to` 為真**的 Face
Hint，**不是** `continue` 下一分類；抑制集合**只由 C ∧ D 決定**，
未擴成「所有 categories／所有 bill_ref Face／所有 dialog Face／所有 required_slots Face」。

**4.3 等價契約未被破壞**：`services/decision_layer.py` **本輪零改動**（git diff 可證），
`facet_entry_eligible` 逐字未動；既有等價 suite（`test_decision_layer_equivalence_req.py`／
`test_facet_entry_equivalence_config_req.py`）全綠。新 gate 是**多一道 Routing Hint
authorization**，不是門檻或 eligibility 的替代品：

```text
原 eligibility：這筆 KB 有資格提出某個 Face Hint
新 gate      ：這個 query 是否允許此類 Hint 生效
```

**4.4 兩種 fail-open 的原因不得摺疊**：

```text
證據不足     → verdict="abstain" → 維持既有 routing（有 verdict 可稽核）
抽取/判定例外 → 回 None ＋ 印「fail-open…（非 abstain）」→ 維持既有 routing
```

exception boundary 放在 **seam**（不是抽取器——2.4 已刻意讓抽取器不吞例外）；
**SHALL NOT 在例外時偽造空 evidence 再送進 gate**，那會讓「壞掉」偽裝成「沒有訊號」。

**突變驗證（4 個，全數被殺）**：

| ID | 突變 | 被殺的 test |
|---|---|---|
| M30 | 抑制擴成「所有 Face」（溢出 C∧D）| suppression_does_not_leak_to_unmanaged_faces |
| M31 | 只跳過當前分類（沿用 `continue` 語義）| category_order 兩序 ＋ 4 筆 rule 抑制 |
| M32 | active 只看 requested（丟掉授權）| flag_off_and_requested_but_unauthorized_are_both_inert |
| M33 | 例外偽造成 abstain | exception_fails_open_and_is_not_disguised_as_abstain |

**N4 拆成兩層，機制與產品裁定分離**（業主裁示）：

| 契約 | 第二個 Face | 現況 |
|---|---|---|
| **機制**：category 順序不得繞過抑制 | **合成** Face（明示 `requires_instance_reference=true` ＋ D scope=true）| 🟢 兩序皆綠 |
| **production membership** | 真實 `billing_anomaly` | **strict xfail**：待逐 Face 裁定 ＋ 授權 |

⚠️ `strict=True` 是刻意的：若哪天它**意外轉綠**，代表有人在裁定完成前動了 membership
或授權——**那必須當場被看見，而不是安靜地變綠**。

**另有一條會隨裁定改判的斷言**（已於測試內註明）：
`suppression_does_not_leak_to_unmanaged_faces` 目前斷言「帳單異常仍可接手」，
因為它未宣告 C。`billing_anomaly` 完成裁定並宣告後，該條應改判為 `single`。

**2.0 falsifier 的第三次確認（seam 層）**：兩筆未決問句在 gate 真正生效時仍**未被抑制**。
Req.4 **仍未被 Task 4 裁定**。

**紅綠現況**：integration `205 passed／4 failed／2 xfailed`——
4 failed 即原本那 4 筆 known-red REGRESSION，**旗標 OFF 時本就應維持紅**；
它們要到任務 6 授權、任務 7 啟用後才會轉綠。unit `1107 passed`（13 failed 全為具名 `_meta` 環境錯配）。

### ✅ 5.1／5.3、🟡 5.2（2026-08-24）

**synthetic authorization 的邊界（報告用語不得混用）**：

```text
Candidate technical acceptance under synthetic authorization
≠ Candidate authorized for release
```

只注入 matching-PASS manifest 讓 **production authorization check** 通過，
其餘 extractor → gate → seam **全走 production code path**；
未 mock verdict／未 mock suppression／未改 `current_manifest()` 的真實 `not_run`／
未把 synthetic PASS 寫回正式 manifest。

**5.1 baseline（evidence/protocol-v1-baseline.json）**

```text
bilateral_pass  8/8   ✅   RULE 4/4 single、INSTANCE 4/4 條件診斷：帳單
CONTROL         5/5   ✅   不變
BLAST           7/7        全進條件診斷：帳單（intended behavior 待 5.4 判定）
UNDECIDED       2          只記錄，**不進 bilateral／pass 分母**
negative control      ✅   ruleset digest 差一位 → gate_active=False，
                           且 RULE 四筆 routing 與未授權時完全相同
                           （證明本 harness 真的過 production authorization seam，
                             不是 fixture 直接把 gate 打開）
```

**5.3 decision_margin（只記錄、不設門檻）**：RULE 最小 0.0119、INSTANCE 最小 0.0114。
邊際依然薄，但判別不由它決定——這正是記錄它的用途（R3.4）。

### 5.2 擾動（IN PROGRESS）

```text
P1 corpus_add_sibling   3 輪 × 8 = 24    flips 0/24   PASS
P3 phrasing_variant     1 輪 × 8 =  8    flips 4/8    ADVERSE FINDING CONFIRMED
P2 semantic_model_rebuild                              BLOCKED — requires host execution
formal aggregate verdict                               PENDING（分母固定 40）
```

**P1 選樣的 measurement parity 說明（非錯誤）**：
production inventory snapshot 曾記錄 **144**；本輪 test corpus 依**同一 frozen predicate**
（`is_active` ＋ `answer` 非空 ＋ 掛面向分類）實查為 **145**。
P1 以本輪**完整 eligible population** 為母體、固定 seed 抽樣，
**不事後排除樣本**——看到樣本再修母體就是另一種改尺。
其中一筆為 `系統脈絡：帳號領域-登入排障(子面向)`，符合 frozen predicate 故保留。

**P3 adverse finding（獨立保留，不得被 aggregate 沖淡）**：

```text
4/8 base cases changed route under meaning-preserving paraphrase
  6 個變體失敗可歸因於 extractor/gate 的 lexical coverage
  1 個可歸因於既有 retrieval/facet drift（gate 判 allow）
```

病灶不是 similarity margin，是**字面反向片語**：

```text
「怎麼算」→ counter 命中        「計算方式是什麼」→ 不命中
「在哪裡」→ counter 命中        「要去哪裡」      → 不命中
```

⚠️ **不得補這些 pattern**：P3 已把變體曝光，補了就是拿 acceptance data 訓練 candidate，
再拿同一批 data 宣稱通過——那批變體從此失去驗證意義。

**風險定位已改變（重要）**：P1 的 0/24 降低了「corpus 一動就翻」這個特定擔憂
——candidate **不是**重演上一版 anchor 的 0.003 margin 形態；
主要風險改為 **deterministic lexical contract 對保義改寫的 coverage 不足**。
Task 6 holdout 正是判「這是可接受的 coverage 缺口，還是整個 deterministic candidate 不成立」。

**最終算式（frozen，不得改）**：分母 40（P1 24＋P2 8＋P3 8），門檻 ≤ 5/40 ＝ 12.5%。
目前已固定 4 flips：P2 0 flip → 4/40 PASS；1 flip → 5/40 PASS；≥2 → ≥15% FAIL。
⚠️ 若最終形式 PASS，報告 SHALL **並列**兩條結論，不得只寫 PASS：

```text
Formal protocol-v1 robustness : PASS（依 frozen aggregate 分母）
P3 adverse finding            : 4/8（保義改寫下改變 route）
```

**P2 待執行（host 端，本 session 權限被拒——碰 `docker-compose.prod.yml`）**：

```bash
docker inspect aichatbot-semantic-model --format 'container={{.Id}}\nimage={{.Image}}'
docker compose -f docker-compose.prod.yml up -d --force-recreate semantic-model
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8002/        # 預期 200
docker inspect aichatbot-semantic-model --format 'container={{.Id}}\nimage={{.Image}}'
```

重建前身分（已存證）：`container=369e57723b30…`／`image=sha256:fceedf9c18f0…`。
判定分兩欄：`container_before != container_after` → **protocol validity VALID**；
`image_before == image_after` → **perturbation strength LIMITED**。
**支持**「robust to service recreation」；**不支持**「robust to a different semantic model version」。
⚠️ 即使 image 相同也**不得**事後宣布 P2 無效而從分母刪掉——那是改凍結規則。

### ✅ 5.2 結算（2026-08-24）——**兩條結論並列，不得只寫 PASS**

```text
Formal protocol-v1 robustness : PASS
  P1 corpus_add_sibling   3×8 = 24   flips 0
  P2 semantic_model_rebuild 1×8 = 8  flips 0
  P3 phrasing_variant     1×8 =  8   flips 4
  ────────────────────────────────────────
  合計 4 / 40 = 10.0%   門檻 ≤12.5%   → PASS
  「不得有任一筆反覆翻面」→ 成立（四筆各只在 P3 翻面，於 P1×3 與 P2 皆穩定）

P3 adverse finding : 4/8
  保義改寫下改變 route；6 個變體失敗歸因於 extractor/gate 的 lexical coverage，
  1 個歸因於既有 retrieval/facet drift（gate 判 allow）
```

⚠️ **這個 PASS 只能宣稱「符合預先凍結的 aggregate robustness threshold」**，
SHALL NOT 表述為 phrasing robust／generalized／routing quality improved。

**P2 的兩欄判定（host 端由業主執行 force-recreate）**：

```text
container_before 369e57723b30…  ≠  container_after 0916e5657394…   → protocol validity  VALID
image_before     sha256:fceedf9c18f0…  ==  image_after 同值          → perturbation strength LIMITED
service HTTP 200                                                     → service restored

支持的主張  ：robust to service recreation
不支持的主張：robust to a different semantic model version/model rebuild
```

⚠️ image 相同**不構成**把 P2 從分母刪除的理由——那會改凍結規則。
但也**不得**把它說成測過 model-version drift；同 image ＋ stateless reranker，
這一輪擾動在效果上可能近乎 no-op。

證據：`evidence/protocol-v1-p1-corpus-sibling.json`／`-p2-model-rebuild.json`／`-p3-phrasing.json`。
