# 實驗設計：R1 information-independence／discrimination（**設計稿，尚未產樣本**）

> 2026-08-24｜語言 zh-TW｜對象：design-discovery 的四個 family（D1–D4）
> ⚠️ **本檔只定規則。未產任何 case、未跑任何 candidate。**

## ⭐ 核心裁定：這**不是** v2 final holdout

```text
Design-discovery challenge set        Final unseen holdout
──────────────────────────────        ────────────────────────────
用來淘汰 D1／D2／D3／D4                design ＋ ruler frozen 後才產
**可以刻意做難、刻意配對**              isolated author／blind labels
實驗後 candidate 可以看到並研究          candidate 首次接觸即燒毀
**不可拿來證明泛化**                    用來證明或反證泛化
```

理由：本實驗的資料**天生是 curator-designed falsification set**
（刻意讓 `(similarity, category)` 等價而 expected applicability 相反），
**不得冒充自然分布的 unseen generalization evidence**。

⚠️ **重用規則**：某 family 若在看過本 challenge set 後被修改，
該修改**不得**再以同一批資料證明改善——需新的 challenge cases 或走 final holdout。

---

## Experiment A — causal independence test（對 R1.1／R1.2）

**介入形式**（受控 seam，不依賴自然檢索剛好撞出相同浮點數）：

```text
hold(similarity, category) constant
vary(semantic case)

Case A: query=Q1, expected=applicable,     similarity=S, category=C
Case B: query=Q2, expected=not_applicable, similarity=S, category=C
```

**要問每個 family 的唯一問題**：

> **它提出的新增 evidence，能不能隨 expected applicability 改變？**

- 不能 → **R1 falsified**，該 family 出局。
- **本層量的是 `information independence`，不是 production accuracy。**

**Negative control（必跑）**：

```text
fake_evidence = f(similarity, category)
```

⚠️ 即使它叫 `semantic_scope`、存在另一張表、由另一個 model 產生——
只要**固定 `(similarity, category)` 後無法獨立變動**，就 **SHALL FAIL**。

⚠️ **A 的效力限制（必須明記）**：受控 seam 會餵入 production 未必產生的輸入組合
（Q2 首版正是因此量錯——見 `q2-gate-pairs-frozen.json` 的 `fidelity_fix`）。
故 **A 通過者 SHALL 於 B 以 production-equivalent retrieval 複驗**；
**A 單獨通過不構成 R1 滿足**。

---

## Experiment B — production-shaped matched-pair discrimination

走**真實 production-equivalent retrieval**，尋找自然發生的難例對：

```text
same routing category
same relevant KB／Face responsibility context
abs(score_a − score_b) ≤ **frozen tolerance**
opposite ground-truth applicability
```

⚠️ **`tolerance` 現在不訂**。程序為：

```text
① 先研究既有 score distribution，導出**可重現的 matching protocol**
② freeze tolerance ＋ matching rule
③ **才**開始配對產資料
```

**本層回答**：在 production-shaped ambiguity 下，新 evidence source **是否真的帶來 discrimination**。

---

## 樣本來源（三類，**全部標為 discovery evidence**）

| | 來源 | 可用性 | 限制 |
|---|---|---|---|
| **S1** | v1 burned holdout | **可用**（已明定 permitted for failure analysis／diagnostic）| ⚠️ **不得單獨**作本實驗證據——否則四個 family 只會學會解 v1 的傷疤。`#11/#30`／`#8/#43`／`#4` 為高價值 seed |
| **S2** | product-spec-derived controlled pairs | 可用（**最適合 Experiment A**，目的即 causal control）| 同主題／同 category，一側應進 Face、一側應留 knowledge。⚠️ **不得沿用已看過的句子本身**，只沿用 pair 結構 |
| **S3** | isolated author 產新 challenge cases | 可用 | 作者**可以**知道需要 paired contrast（因為這不是 final holdout）。給：產品場景／需建立 semantic contrast pair／每組 expected distinction／不得抄現有 case。⚠️ **不得**給 candidate implementation——否則 challenge set 會退化為針對特定 regex／prompt 的 adversarial patch set |

---

## Label schema（**兩層，不得只標 rule／instance**）

```text
candidate_applicability:  applicable ｜ not_applicable ｜ undecidable      ← 主 label
intended_action:          enter_face_X ｜ remain_knowledge ｜ other        ← 必要時附
```

⚠️ 理由：D1／D3 的 evidence unit 可能是 `query × Face`，D2 可能是 query representation。
**且必須避免把「query 是 instance」等價成「Face X 一定適用」**——那正是 v1 的混淆。

---

## 各 family 的 evidence unit 與專屬 negative control

**共同 ruler 相同，evidence unit 可不同。**

### D1
```text
測：query × candidate Face → applicability evidence
要求：pair 兩側可穩定區別
```

### D2
```text
測：query → first-class semantic representation
⚠️ **不得只看最終答對沒**——SHALL 指出 representation 中**哪一個欄位**提供 R1 所需的新資訊
   （decomposition requirement；否則 opaque label 會變成 v1 lexical classifier 2.0）
```

### D3
```text
測：query × explicit Face responsibility contract → applicability
專屬 negative control（**自證防線**）：
   Face 宣告「我適用」，但 query evidence 與其責任 contract 不匹配
   → **SHALL NOT** 僅因 Face 自己宣告而通過
   （否則回到「`requires_instance_reference=true` 就自動取得 authority」）
```

### D4
```text
⚠️ **不參加**「是否有新資訊」的競賽（它本就不滿足 R1）
只測：上游 D1／D2／D3 提供**相同 evidence** 時，D4 是否增加**可驗證的 correctness property**
falsifier：  with D4 的 outcome correctness == without D4 → 即為 architectural elegance
```

---

## 「穩定」的定義（**維度現在宣告，門檻稍後凍結**）

⚠️ **現在不訂 90% 之類的數字**，但**現在就要聲明穩定性至少涵蓋哪些維度**：

```text
paired discrimination
phrasing perturbation
repeated execution（同輸入重跑）
candidate／Face order perturbation（若該 family 對順序敏感）
no dependence on similarity／category mutation
```

**凍結時點**：在 **candidate implementation 之前**，一次凍結

```text
denominator ｜ metric ｜ threshold ｜ perturbation protocol ｜ model／config versions
```

（與 v1 ruler discipline 一致：量尺若能在看到結果後才定，就可以先做方案再挑有利的擾動。）

---

## ⛔ 本實驗**不得**用來選「最高 accuracy 的 winner」

**第一步只問是非，不排名**：

```text
D1 satisfies R1?  yes/no
D2 satisfies R1?  yes/no
D3 satisfies R1?  yes/no
D4 provides independent correctness property?  yes/no
```

**通過 falsifier 者**才進入比較，且比較維度為：

```text
R2 authority 可接性 ｜ R3 responsibility clarity ｜ R4 executable enforcement
R5 scope assumptions ｜ false-reject exposure ｜ operational cost
```

⚠️ 否則 architecture selection 會被降級成 **benchmark 排名**——
「D1 82%、D3 86%，所以 D3 贏」是本檔明令禁止的推論形態。

## 執行順序（**不得對調**）

```text
① 本設計稿 approve
② 研究 score distribution → freeze matching protocol／tolerance
③ freeze 樣本來源規則、label schema、falsifier、negative controls、穩定性維度
④ **才**產生 cases（S1 抽取／S2 建構／S3 隔離作者）
⑤ 執行 Experiment A → 通過者執行 Experiment B
⑥ 逐 family 出具 disposition（允許全部出局）
```
