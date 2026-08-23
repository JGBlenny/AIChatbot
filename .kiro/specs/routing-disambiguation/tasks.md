# 實作任務：routing-disambiguation

> 建立 2026-08-23｜語言 zh-TW
> 來源：[requirements.md](./requirements.md)（9 需求／35 子需求）、[design.md](./design.md) v1.1、
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
＋ unseen holdout PASS
＋ matching ruleset／protocol／dataset digests
＋ Level A regression／blast-radius PASS
```

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

- [ ] 1.2 **⚡F** (P) 建立**wrong facet ≠ success**的斷言：instance 問句進入
  「條件診斷：帳單」以外的任何 dialog SHALL 判為失敗。
  ⚠️ 前案兩度因只驗 `route == "dialog"` 而把跑錯面向算成成功。
  _Requirements: 1.4_

- [ ] 1.3 **🧠主** 建立 **multi-category negative control** 並納入 **protocol v2**
  （**不得改 v1**）：一個 rule 問句，其 top-1 KB 掛兩個以上分類且其中兩個皆為
  instance-requiring Face，斷言最終仍為 `single`。
  ⚠️ 沿用 `continue` 下一分類無法保證 Req.1.2；凍結案例集三筆恰為單一相關分類，
  會出現「案例綠但契約未成立」。
  _Requirements: 1.2, 1.3_

- [ ] 1.4 **⚡F** (P) 建立 **Level A scope isolation** 斷言：旗標開啟時，
  **白名單以外的 Face 行為完全不變**（取數個非帳單域面向的代表問句對照）。
  ⚠️ 防「帳單 8/8 但偷偷改了 21 Faces」。
  _Requirements: 2.5, 5.2_

- [ ] 1.5 **🧠主** 確認 1.1–1.4 在**尚未實作**的狀態下全部為紅，並記錄各自的失敗訊息。
  ⚠️ 這是 negative control 的 negative control——**守門若一開始就是綠的，它守不到任何東西**。
  _Requirements: 6.5_

---

## 2. `InstanceEvidence` 與決定性抽取器

- [ ] 2.1 **🧠主** 定義 `InstanceEvidence` 值物件：正向證據、反向證據、`spans`。
  ⚠️ `spans` 用 **immutable tuple**——`@dataclass(frozen=True)` 只凍結欄位綁定，
  dict 內容仍可 mutate，型別契約會名不副實。
  _Requirements: 2.1, 3.1_

- [ ] 2.2 **⚡F** (P) 實作正向特徵抽取：`identifier`／`possessive`／`lookup_verb`／`problem_report`，
  複用 `conversational_engine.py` 既有 id-like／ordinal 抽取慣例，不新造。
  _Requirements: 2.1_

- [ ] 2.3 **⚡F** (P) 實作反向特徵抽取：`explanation_request`。
  ⚠️ research 實測顯示它比任一正向特徵更強（8/9 vs 最高 5/11）——
  **只找正向特徵會漏掉「規則問句」這一半**。
  _Requirements: 2.1_

- [ ] 2.4 **⚡F** 實作 `extract(None)`／`extract("")` → 回空 evidence。
  ⚠️ **不得靠 exception → fail-open 間接達成**：靠例外的行為不會被型別或測試鎖住。
  _Requirements: 3.1_

- [ ] 2.5 **🧠主 🔍V** 建立抽取器的**不變量測試**：零 LLM 呼叫、零 IO、
  **不讀取任何相似度分數**。
  **🔍V 理由**：與相似度正交是本元件存在的唯一理由（Req.3.1）；
  若它偷讀分數，整個方案退化為「換個地方做相似度競爭」（Req.2.3）。
  _Requirements: 2.3, 3.1, 3.4_

- [ ] 2.6 **🧠主** 建立 `RulesetManifest`：規則集內容雜湊、版本、`HoldoutRecord`。
  規則集為**版本化資產**，變更即須重跑並保留前版結果。
  _Requirements: 3.5, 7.2_

---

## 3. `InstanceReferenceGate`

- [ ] 3.1 **🧠主** 實作三值判定 `allow`／`block`／`abstain`，並回傳可稽核的 `reason`
  （命中哪些正／反向證據）。
  _Requirements: 1.1, 1.2, 3.1_

- [ ] 3.2 **🧠主** 實作 `block` 的**雙條件**：需同時「無正向證據」且「有反向證據」。
  ⚠️ 反向標記**不得採 veto**——實測有一筆 instance 案例同時命中 possessive 與
  explanation_request，veto 會誤殺，正是 3.4 那類「修一邊傷另一邊」。
  _Requirements: 1.3_

- [ ] 3.3 **🧠主** 實作 `block` 的**作用域**：抑制該問句對**白名單內所有 instance-requiring Face**
  的 Hint，**不是** `continue` 下一個分類。非白名單 Face 不受影響。
  _Requirements: 1.2, 2.5_

- [ ] 3.4 **⚡F** 補測試鎖住 **`abstain` 不得被摺疊**成 `allow` 或 `block`。
  ⚠️ 訊號不足時假裝有結論，正是本案要消滅的失敗形態。
  _Requirements: 1.3_

---

## 4. production seam 整合

- [ ] 4.1 **🧠主** 實作 `is_instance_requiring_face(cfg)`：**Level A 白名單**——
  face key == `bill_diagnosis` 且 `"bill_ref" ∈ required_slots`。
  ⚠️ **不得**用 `bool(cfg.grounding_scope.required_slots)`：其語義為「執行需要哪些欄位」，
  未來 Face 可能 required `date`／`reason`／`amount`，皆非 entity reference。
  _Requirements: 2.5, 5.2, 8_

- [ ] 4.2 **🧠主** 於 `_diagnosis_config_for_knowledge` 串接：
  `config_for_category` 命中之後、`_preentry_routable` 之前。
  旗標 `INSTANCE_REFERENCE_GATE` **預設 `false`**。
  _Requirements: 1.1, 1.2, 7.1_

- [ ] 4.3 **🧠主 🔍V** 驗證 `facet_entry_eligible` 的**等價契約未被破壞**——
  `decision_layer` 檔頭明訂該函式對任意輸入須與搬移前 inline 邏輯嚴格同輸出。
  新 gate SHALL 為獨立函式，不改動既有門檻判定。
  **🔍V 理由**：破壞等價契約會使前案建立的 171 條整合護欄失去對照意義。
  _Requirements: 8_

- [ ] 4.4 **⚡F** 實作 fail-open：抽取或判定例外 → `abstain` → 不阻擋
  （沿 `_preentry_routable` 慣例）。
  _Requirements: 1.3_

---

## 5. protocol v1 驗收（**不得改尺**）

- [ ] 5.1 **🧠主** 以凍結案例集驅動 **production seam**（Req.6.1，不得在測試內重演 routing 語義）：
  `RULE 4 → single`／`INSTANCE 4 → dialog:條件診斷：帳單`／`CONTROL 5` 不變。
  門檻 `bilateral_pass = 8/8`（雙邊缺一不可）。
  _Requirements: 1.1, 1.2, 1.3, 6.1_

- [ ] 5.2 **🧠主** 執行擾動 P1 `corpus_add_sibling`×3／P2 `semantic_model_rebuild`×1／
  P3 `phrasing_variant`×1，量 `flip_rate ≤ 1/8` 且**不得有任一筆反覆翻面**。
  _Requirements: 3.2, 3.3_

- [ ] 5.3 **🧠主** 記錄 `decision_margin`（**只記錄、不設門檻**）——
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
