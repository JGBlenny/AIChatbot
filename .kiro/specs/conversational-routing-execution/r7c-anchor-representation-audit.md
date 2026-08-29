# R7-C：empty-answer anchor 的 retrieval representation 稽核（2026-08-29）

- 對象：R6-B 的 **4656（3 筆）／4657（1 筆）**
- ⛔ 純靜態 audit：未改 summary、未改 KB、未跑語料、未改任何參數

## ① 兩列的完整 retrieval-visible 內容

```text
4656  question_summary「查帳單 帳單編號查詢」
      answer 長度 **0**｜categories 條件診斷：帳單｜keywords 帳單／查詢／編號
      action_type direct_answer｜form_id 無

4657  question_summary「合約的點退帳單金額 查點退金額」
      answer 長度 **0**｜categories 條件診斷：帳單｜keywords 合約／點退／金額
      action_type direct_answer｜form_id 無
```

## ② downstream capability 的精確承諾

```text
categories 條件診斷：帳單 → Face **bill_diagnosis**
  requires_instance_reference = true（P1e-2 已宣告）
  grounding_scope: select=api、endpoint=**jgb_bills**、required_slots=[**bill_ref**]
  → `diagnose_bill` 分支：B01 發不出去／B02 取消不了／B03 逾期費／
                          B04 手動到帳／B05 收據／P04 虛擬帳號
                          其餘落 `_format_bill_status`（通用現況）
instance_applicability = instance（reviewed_product_declaration）
⇒ 承諾＝**取得使用者指定的那一筆帳單並回報其實值／現況**
```

## ③ 是否還有其他 metadata 進入 scoring surface —— **查證後：沒有**

```text
【reranker surface】（R5 已證）
  text = question_summary（answer 僅在 summary 為空時 fallback）

【embedding surface】（本輪新查，`knowledge-admin/backend/app.py`）
  :329  text_for_embedding = f"{question_summary}. 關鍵字: {keywords}"（有 keywords 時）
  :457  text_for_embedding = question_summary
  :635  base_text = question_summary if question_summary else answer[:200]
        text_for_embedding = f"{base_text}. 關鍵字: {keywords}"
  ⇒ **`answer` 從不進入 embedding**；summary 非空時亦不會 fallback

【keyword surface】keywords 進 embedding 文字（部分路徑）＋ keyword_boost
【categories】只用於 **nomination**，⛔ 不進 scoring
```

⇒ **兩個 scoring surface（vector 與 rerank）都只看 question_summary(＋keywords)。**

## ④ summary 是否完整表達該 responsibility —— **否**

```text
4656 summary「查帳單 帳單編號查詢」
  ⇒ 表達了「查帳單」與「用編號查」
  ⛔ **未**表達：狀態／已繳未繳／發送狀態／草稿／到期／金額……
     而 capability 承諾的是**該筆帳單的完整現況**（`_format_bill_status`）
  ⚠️ A03 中失敗的 I2 query 正是這類：
     「那筆帳單到底繳了沒」「請問這張帳單現在是已寄出還是草稿」
     ——語義落在 capability 內，⛔ 卻不在 summary 的詞面內

4657 summary「合約的點退帳單金額 查點退金額」
  ⇒ 表達得相對貼合（點退＋金額）
  ⚠️ 但 `diagnose_bill` **沒有點退專用分支** ⇒ 實際落 `_format_bill_status`
     ⇒ capability 與 summary 的落差在此列較小，但**承諾本身也較模糊**
```

## ⑤ 判定

```text
**CAPABILITY_NOT_REPRESENTED_IN_RETRIEVAL_SURFACE ＝ CONFIRMED（架構事實）**

anchor 的 coverage truth 由 **downstream capability** 定義，
但它在 retrieval 中的**唯一** representation 是一串窄關鍵詞 summary，
而 answer（本可承載語義）**為空且從不進入任何 surface**。
⇒ 這不是「被藏起來的語義」（3406 至少還有 answer 可證），
  而是**能力語義從未被放進 retrieval representation**——更極端的一類。
```

⚠️ **claim ceiling**：

```text
✅ 已證明：**架構上**該能力未被表示在任何 scoring surface
⛔ **未證明**：這就是那 4 筆失敗的 causal mechanism
   —— 無法用 R6 的 counterfactual 檢驗（沒有 answer 可替換），
      且⛔ 不得人工補一段 capability description 再去測（那是設計新 document）
⇒ R6-B 的 root cause 仍 **OPEN**
```

## ⑥ 一個歷史設計結論需要降級

```text
`api_server.py` 註解：「拿掉 answer 後差距提升 99%，正確率不變（見 knowledge.md §5）」
⇒ 現只能視為**當時那個 evaluation corpus 上的歷史結果**。
A03／R6 已找到合法 counterexample family：對 3406，summary-only 會使
confirmed-covered queries 被壓到門檻下。
⛔ 不得再把該舊實驗當成全域設計真理。
```

## 狀態

```text
summary-only reranking architecture      CONFIRMED
summary-only globally defective          REFUTED / not supported
3406 scoring-surface mismatch            CONFIRMED causal
3498 scoring-surface contribution        PARTIAL
empty-anchor representation hypothesis   **CONFIRMED as architecture fact**，causal 仍 OPEN
remaining R3b cases                      OPEN（R7-A 近門檻 3496/3519；R7-B 雙 surface 皆弱）
⛔ 未改 summary／KB／threshold／任何參數
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
