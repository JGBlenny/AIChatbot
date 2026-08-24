# `bill_diagnosis` observation-contract audit rule（**凍結於查核之前**）

> 2026-08-24｜語言 zh-TW｜業主裁定：`c4a-diag-01` 走 **(β) measurement-instrument amendment**
> 前置：`c4a-required-facts-draft.md`（DRAFT，`08f79a2`）｜案例四案 FROZEN（`451c0d2`）
> **狀態：FROZEN**

## 這次查核回答的唯一問題

> **在 `bill_diagnosis` 現有 production grounding representation 中，
> 有哪些明確、machine-observable 的 semantic facts 尚未被 current adapter canonicalize？**

⚠️ **不是**「怎麼讓 `c4a-diag-01` 變綠」。差別在因果：

```text
case 先 FROZEN → 5.2 依 production semantics 判出必要 fact = 應收金額
              → 才發現既有 observer 觀測不到它
```

`4.6`／`5.3`／`5.4` **均未執行**，故這是**量測儀器覆蓋不足**，
不是「看到結果不如預期才改尺」。

## ⚠️ Prior-exposure declaration（本輪不能宣稱 blind）

```text
執行 4.4／5.1 期間，我已見過 build_bill_diagnosis_facts 的實際輸出，
包含其開頭區塊以「• 狀態／• 金額／• 繳費期限」條列呈現。
```

**防護**：該印象**不得**直接作為 admission 依據；
`amount_due` 是否可加入，一律以下方 O-1～O-6 逐條查證後決定。

---

## O-1～O-6：新增 canonical fact 的 admission rule（**查核前鎖死**）

```text
O-1  production grounding **現在真的有明確表示它**
O-2  能以 **deterministic semantic label** 觀測，**不靠自由文字猜測**
O-3  observer 只回答「fact 是否送達」，**不含 sufficiency policy**（B-1 延續）
O-4  **不新增／不修改 production formatter**
O-5  **不查看** 5.3／5.4 的 pass／fail（該二者尚未執行）
O-6  amendment 完成後**重新 freeze observation contract**，再回到 5.2
```

### 失敗即轉 γ（**事前寫定**）

```text
若 O-1 或 O-2 不成立 → **β FAIL**
→ 結論改為：case 可 ground，但目前 execution output **沒有可稽核方式**
   證明 amount fact 被送達 → C4a instrumentation／design 須重新處理（γ）
⚠️ **不得**為了保住 case 而寫自然語言 keyword parser。
```

## Canonical key 命名（業主裁定）

```text
amount_due     ← 本案所需的**應收**事實（production semantics：`_bill_amount_due()` → `total`）
amount_stored  ← anomaly observer 既有 key（`帳單金額 …（系統存值）` 的呈現語義）
```

⚠️ **不得**因兩者都涉及金額就合併——除非 production 明確契約證明兩者同一語義。
canonical key 表達的是**產品語義**，不是底層 API 欄位名。

## 本次查核**不做**

```text
❌ 不動已 FROZEN 的四案
❌ 不動 production formatter
❌ 不動 4.4 fixture
❌ 不 freeze 5.2（維持 DRAFT，待 observer 重新 freeze 後才回去完成）
❌ 不擴充 anomaly observer（本輪只審 bill_diagnosis）
```
