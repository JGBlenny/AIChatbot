# Level-A 10 rows representation —— review status（業主裁定 2026-08-29）

⚠️ `NOT_REVIEWED_BY_OWNER` **不是** UNKNOWN semantic truth，只是 review workflow 未完成。
⛔ 不得寫成資料層的 UNKNOWN。

| row | status |
|---|---|
| 3402 | `APPROVE_WITH_NARROWING` |
| 3499 | `APPROVE`（responsibility-level）＋另列 `KNOWLEDGE_CONTENT_INCOMPLETE` |
| 4657 | `HOLD / REVIEW_BLOCKED_CAPABILITY_AMBIGUOUS` |
| 3406 3495 3496 3498 3519 4640 4656 | `NOT_REVIEWED_BY_OWNER` |

---

## 3402 —— 收窄後定稿

裁示：`retrieval_representation` 描述 **row 承接的 intent**，⛔ 不是把 answer 裡
所有相關知識濃縮進去；否則會從「representation 不足」擺到另一端＝**semantic
envelope 膨脹**。

```text
定稿：點退完成後系統何時／在什麼條件下自動產生點退帳單，
     以及該帳單如何進入費用結算。
⛔ 刪除：一般帳單繳費期限／到期日規則
```

## 3499 —— 責任層通過；⛔ 不得替 answer 發明內容

```text
定稿：查詢／診斷特定帳單手動到帳失敗、無法完成手動入帳的原因。
⛔ 不得寫成：手動到帳失敗常見原因包括 A／B／C
   （除非 A/B/C 已由 downstream capability 或其他 authoritative contract 證明）
```
⇒ 兩件事分開：
```text
3499 retrieval representation      可先獨立成立
3499 answer content completeness   另列 defect（KNOWLEDGE_CONTENT_INCOMPLETE）
```
「answer 不完整」⛔ 不能反過來阻止 retrieval 表達它真正負責的 semantic responsibility；
但 retrieval 也⛔不能替 knowledge content 發明答案。

---

## 4657 —— HOLD，且**理由與先前理解不同**

裁示：不批准它宣告「查實際點退金額」，除非先證明能力真能提供那個值。
以下為實查所得的 machine evidence。

### ✅ 可證的部分

```text
金額**有**暴露：_format_bill_status（services/jgb/bills.py）
  total = _bill_amount_due(bill) → bill["total"]
  輸出 "• 金額：NT$ …"，並逐項列出 details[].total_price
上游 payload **有** type 欄位：JgbMockTransport.MAPPING["type"] = {2: "點退", …}
  （鏡射 BillApiController:173-197）
合約入口**有**：對話規則明文「沒有編號時可用合約編號或物件名稱」
```
⇒ 「金額拿不到」**不成立**——先前把 4657 的病灶說成「無點退專用分支」，
   ⚠️ 那句話為真但**不是**binding constraint。

### ⛔ 不可證的部分（真正的 blocker：**選取**，不是金額）

```text
face_bill_response（bills.py）對多列的處理是 **row = data[0]**
  —— 註解寫明「list 正規化為第一列」
⇒ 給定合約時，系統 ground 的是**第一列**帳單，⛔ 不是「該合約的點退帳單」
⇒ _format_bill_status ⛔ **不讀 type** ⇒ 輸出從不說明「這是不是點退帳單」
⇒ 對話規則承諾的「系統會列該合約的帳單候選」，**在帳單 face 路徑上找不到實作**
```

**否定結論的三道防線**（依 2026-08-24 定案）：
```text
正對照   同一組搜尋在修繕域確實找到多候選機制
         （services/jgb/repair_prefill.py 的 candidates / _classification_candidates）
         ⇒ 搜尋形狀有效，不是工具壞了
目標搜尋 bills.py 的多列處理只有一處：`row = data[0]`
對照預期 若存在候選列表，應出現與 repair_prefill 同形狀的 candidates 結構——未出現
```

### ⇒ 4657 的處置

```text
❌ 「查詢自己某份合約的實際點退帳單金額」   → REVIEW_BLOCKED（選取步驟不可證）
❌ 「查詢特定合約相關的點退帳單及其狀態」   → 仍 over-claim（「點退」的辨識不可證）
✅ 可證的上限只到：「查詢某一筆帳單（含點退帳單）的金額與目前狀態」
   —— 但那與 4656 幾乎重合 ⇒ 4657 的 semantic envelope 本身需要重新裁定
```
⚠️ 業主原話成立：**這代表先前對 4657 semantic envelope 的理解需要一起修正，
   而不是讓新的 representation 把舊誤解固化。**

### 由此掉出的獨立 defect（⛔ 不在本輪修）

```text
FACET_PROMISE_UNIMPLEMENTED：
  bill_diagnosis 對話規則承諾「系統會列該合約的帳單候選」，
  帳單 face 路徑實際只取 data[0]。
  ⇒ 使用者給合約編號時，得到的可能是**任意一筆**帳單，且系統不會說明是哪一種。
```

---

## 執行順序（業主定案，⚠️ 第 5 步不可漏）

```text
1. 完成 10-row product review
2. 只有 approved representation 才寫 DB ＋ provenance
3. Level-A completeness invariant 必須通過
4. 重建 semantic-model
5. **只對 Level-A 10 rows 重生 embedding**
6. 驗：DB contract → retriever transport → vector representation → reranker representation
      全部實際使用同一份 reviewed text
7. 再做 candidate validation
```
⚠️ **4 與 5 是同一個 migration step**，⛔ 不得只做 4。
只重建容器而不重生既有 embedding ＝ 製造「形式上新 contract 已接線，
但 retrieval 前半段仍吃舊 semantic surface」的**假完成**。
