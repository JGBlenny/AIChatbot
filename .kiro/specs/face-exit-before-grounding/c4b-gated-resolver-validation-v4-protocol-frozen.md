# `C4b-gated-resolver-validation` **v4**（output-contract repair）protocol（**FROZEN**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 前身：v1／v2（NOT_VALIDATED）與 v3（attribution：`missing` 3/3）——**皆不回填**
> ⚠️ 舊 C4b 歷史同樣不動。

## 0. 這輪改的是什麼（**不是再堆 prompt wording**）

v3 的直接證據：三次原始 JSON 的鍵集合為
`action／extracted_fields／next_question／scope／face`，
**與 persona 規則自身宣告的輸出形狀逐鍵吻合**，且不含附加在規則之後的 delegation instruction。

⇒ 該修的是 **schema declaration**，不是 wording：

```text
delegation field 從「附加 instruction」 → 升格為 evaluator 的**正式 output contract**
```

## 1. 修法（業主裁定 (a)）

把 `delegate_facet_key` 正式寫進規則宣告的每輪輸出形狀，並鎖住語義：

```text
每輪輸出 JSON：{…原有各欄…,"delegate_facet_key":"…（見下）"}
【delegate_facet_key 規則】
  scope="stay"                              → 必須為 ""
  scope="switch" 且符合已宣告的轉交對象      → 必須填該對象的鍵
  scope="switch" 但無法對應合法轉交對象      → ""
```

⚠️ **白名單驗證仍在程式端**（`delegate_specs` → 正規化只認 target）；
模型**沒有**因此獲得新的 authority。

## 2. 作用域限制（讓 causal claim 乾淨）

```text
✅ 只改**本 fixture 修改的兩個面向**（有宣告 delegates 者）的規則宣告
✅ 只改**測試庫**，測試結束**還原**（連 answer 原文一併還原）
❌ 不改 production persona 資料
❌ 不改其餘任何 Face——其 prompt／output shape 逐位元不變
❌ 不改 parser、resolver、ruler、categories、threshold；production gate 仍 false
```

⇒ 唯一變數：**delegation field 是否進入 evaluator 的正式 output contract**。

### 為何不是 (b)（API-level structured output）

同時會改變 provider call contract／schema enforcement／可能所有 Face／failure mode／
token 行為——屆時 v4 若綠，將無法區分是「delegation 成為正式 output contract」有效，
還是「API-level 強制結構化輸出改變了整體模型行為」。(a) 是最小 causal test。

### 為何不是 (c)（拆成兩次判定）

scope 與 delegation 本質是同一個 responsibility decision（「不是我的」＋「依契約該給誰」）；
拆兩次會多一次成本與延遲、兩次判斷可能互相不一致、且需重新提供 responsibility context。
目前沒有證據需要付這個代價。

## 3. 第一觀測點是 **raw output**，不是最終答案

```text
hop 1  raw delegate_facet_key == "billing_anomaly"    drop_reason == kept
hop 2  raw delegate_facet_key == "contract_closeout"  drop_reason == kept
hop 3  scope == stay                                   fail_open == false
再往下  only contract_closeout committed → grounding executed → final answer uses grounding
```

## 4. 裁決表（事前定死）

| 觀測 | 裁決 | 下一步 |
|---|---|---|
| 三跳 raw 皆 `kept` ＋ commit ＋ grounding ＋ grounded answer | **VALIDATED**（僅此 predeclared case） | 才談 migration／rollout |
| raw 仍 `missing` 3/3 | **(a) 被反證**——自然語言 persona schema 不足以構成可靠 output contract | 才有充分理由升級到 **(b)** |
| raw 有值但被丟棄（`not_allowed`／`wrong_key`／`not_string`） | 歸因到正規化或鍵名 | 依 v3 處置表對應修法 |
| 三次不同類 | **不穩定** → `INSUFFICIENT_EVIDENCE` | 不得挑最好看的那次修 |

## 5. 其餘參數（同前，未變更）

```text
query「幫我查點退帳單金額」／turn2「678」／3 runs／brain gpt-4o 0.4/400／
factual 合成 gpt-4o-mini 0.2/800／semantic 不 retry／target ≤30、all ≤60（委派前檢查）
gate 只在測試行程開；USE_MOCK_JGB_API=true
```

## 6. claim ceiling

```text
✅ 可說：在此 predeclared case 上，把 delegation 納入宣告形狀後，evaluator 會（不會）產生該欄位
❌ 不可說：diag-01 已修好／routing 已正確／可開 production gate／其他 Face 亦然／
          persona schema 是正確的長期方案（那要 (b) 的獨立研究）
```
