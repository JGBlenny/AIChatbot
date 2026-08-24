# Round 1 members：contract freeze（**Step ④**）

> 2026-08-24｜語言 zh-TW｜前置：evaluation contract（`11cd12d`）、matching ruler（`326ce04`）
> ⚠️ **本檔 freeze 於 challenge cases 產生／揭露之前**（M2）。
> ⚠️ **本輪只驗 R1。不接 production seam。**

## 邊界（業主 2026-08-24 指定）

```text
member 做到：  query × fixed Face ＋ frozen provenance source → applicability evidence
               （applicable ／ not_applicable ／ undecidable）

本階段不做：   ❌ 接 handle_retrieval  ❌ 改 Face entry  ❌ early-return 前加 veto
               ❌ 改 production routing outcome  ❌ 動 enable flag／manifest
```

**因果順序**：`R1 有沒有新資訊？` → PASS 才值得問 `R2 接上 authority 能否真的改 routing？`
⚠️ 故 member disposition 本輪**只能**證 `satisfies／fails **R1** information contract`，
**不得**寫成 satisfies R2／routing authority contract。
META-RULE 於 seam 階段仍有效，**只是不是這一輪的驗收對象**。

## 共同控制（最小差異設計）

```text
same evaluator class ｜ same model ｜ same model config ｜ same output schema ｜ same execution protocol
唯一變數：authority-information source（provenance）
```

---

## D1-member-1

| 欄 | 內容 |
|---|---|
| **member_id / version** | `D1-member-1 / v1` |
| **family membership argument** | candidate-specific applicability adjudication：由**獨立 adjudicator** 對 `query × candidate entry` 取得 applicability evidence |
| **input contract** | `query` ＋ **routing-owned applicability specification**（按 entry class） |
| **output schema** | `{applicability: applicable\|not_applicable\|undecidable, reason, evidence_used}` |
| **information source** | `evidence/d1-routing-applicability-spec-v1.json`｜`spec_digest = ebb5f542f14d5c09` |
| **source owner** | **routing layer** |
| **source provenance** | 產品需求層語義（rule vs instance 的產品契約）；**Face-agnostic、按 entry class** |
| **independence from Face-owned contract** | 本 spec **不含任何 Face 的 handles／does_not_handle**；它描述 **query 對 entry 的需求（demand）**，D3 描述**某 Face 的供給（offer）**——owner、單位、敘述對象三者皆不同 |
| **evaluator rules digest** | `d1_rules_digest = 80a25631ffe293d9`（見下方 §rules） |
| **explicitly forbidden inputs** | similarity｜category（作為 applicability 答案）｜現行 production route｜challenge labels｜**另一 member 的輸出**｜**D3 的 Face-owned contract** |
| **known confounds** | evaluator 為 LLM → 非決定性；spec 由本 session 撰寫（**非隔離**）→ 記為 authorship confound |
| **falsifier** | 固定 `(similarity, category)` 後，其 evidence 無法隨 expected applicability 改變（＝R1 falsified） |
| **negative control（D1-NC）** | candidate 已被提出 ＋ metadata／Face identity 強烈暗示適用 ＋ 獨立 evidence 不支持 → **SHALL NOT** 自動判 applicable |

## D3-member-1

| 欄 | 內容 |
|---|---|
| **member_id / version** | `D3-member-1 / v1` |
| **family membership argument** | Face-owned applicability contract：把 responsibility 變成 Face 的 **executable semantic contract** |
| **input contract** | `query` ＋ **該 Face 的 responsibility contract** |
| **output schema** | 同 D1（相同 schema，最小差異設計） |
| **information source** | `evidence/d3-face-responsibility-contract-v1.json`｜`contract_digest = 9b1c12e154b0c85a` |
| **source owner** | **Face owner** |
| **source provenance** | 各 Face 的 seed RULES **自述範疇**逐句轉為 machine-consumable（Face 側撰寫） |
| **responsibility_contract_digest** | `9b1c12e154b0c85a` |
| **self-attestation prohibited** | ✅ 明訂：`face says applicable=true` **不得**作為答案；須 query 與 contract **可驗證匹配** |
| **carrier decision** | **design-side versioned artifact；NOT production Face config schema migration** |
| **evaluator rules digest** | `d3_rules_digest = cf5ee690dd4735d1`（見下方 §rules） |
| **explicitly forbidden inputs** | similarity｜category（作為答案）｜現行 route｜challenge labels｜**另一 member 的輸出**｜**D1 的 routing spec** |
| **known confounds** | evaluator 為 LLM → 非決定性；contract 由本 session 自 seed 轉寫（**非隔離**）→ authorship confound |
| **falsifier** | 同 R1；另加：contract 若退化為「另一組人工 categories／keywords 且無 executable semantics」→ R4 打掉 |
| **negative control（D3-NC）** | Face 宣告適用 ＋ query 不符 responsibility contract → **SHALL reject** |

### §rules（evaluator 判定規則，已凍結；digest 見上表）

兩份規則文本已凍結於 `evidence/`（`d1-evaluator-rules-v1.txt`／`d3-evaluator-rules-v1.txt`），
差異**僅在** provenance 來源與「不得索取」清單，其餘（輸出格式、undecidable 允許、
「候選被提出／面向自稱」不構成理由）**逐字相同**。

---

## ⚠️ 兩道 provenance 防線

### ① 若 D1 spec ≡ D3 contract，family attribution **降級**

```text
若最後發現 D1 spec == D3 contract（僅 owner／storage location 不同）
→ 本輪**不得**宣稱比較了 D1 vs D3
→ 最多只能證：「某一種 query×Face semantic specification 具資訊價值」
   （這仍是有效結果，但 family attribution 降級）
```

**目前的區別**：D1 為 **Face-agnostic 的 entry-class 需求模型**（2 個 entry class，無 Face 清單）；
D3 為 **per-Face 供給宣告**（6 個 Face，各有 handles／does_not_handle）。

### ② 反 circular validation

```text
Product ground truth ──→ query × Face applicability（blind labeler 依**產品責任／業務真實歸屬**判）
Face-owned contract  ──→ D3 evaluator prediction
兩條**必須可比較**
```

⚠️ **禁止**：contract 寫「這些算 applicable」→ labeler 照 contract 原文標 → evaluator 照 contract 判
→ 100% agreement。**那只是 circular validation。**
⚠️ 若產品 ground truth 的**唯一來源**就是同一份 Face contract，
**SHALL 明記 normative dependence，證據等級降一級。**

## 通過 A＋B 之後才問（**現在不決定**）

```text
這份 evidence 如何接到 R2 authority seam？
contract 最終應進 production Face config、獨立 registry，還是其他 authoritative store？
```
