# Level-A 10 rows 的 `retrieval_representation` —— **PROPOSAL（待 review，⛔ 未寫入）**

> ⚠️ **本檔已被 review 部分覆寫**：3402／3499／4657 的最終裁定見
> `r9-review-status.md`，以該檔為準。其餘 7 筆仍為 `NOT_REVIEWED_BY_OWNER`。

- 依 **D3**：legacy summary／keywords／answer **只能作 proposal evidence**，
  ⛔ 不得自動生成 authoritative representation
- 本檔狀態 `RETRIEVAL_REPRESENTATION_PROPOSAL`，⛔ **不得被 production 消費**
- 每筆列出 **evidence**（frozen 原文／capability），供 reviewer 對照

## 撰寫原則（依 R9 simulation）

```text
✅ 比 question_summary 完整（要寫出 capability 承接的語義）
✅ 比 answer 精煉（⛔ 不含欄位清單、舉例、附帶導引）
⛔ 不是 answer 的複製、⛔ 不是 summary 的長版、⛔ 不是 keywords 串接
```

---

## general 三列

### 3402 ✅ `APPROVE_WITH_NARROWING`（見 r9-review-status.md）
```text
定稿：點退完成後系統何時／在什麼條件下自動產生點退帳單，
     以及該帳單如何進入費用結算。
⛔ 刪除一般帳單繳費期限／到期日規則——那不是本 row 承接的 intent。

原 proposal（已被收窄取代）：
proposal：點退完成後系統是否自動產生點退帳單、產生的時機，
         以及帳單包含哪些結算項目與如何與押金互抵。
evidence：answer「點退完成後系統自動產生…水電等未結費用／設施損壞賠償／其他費用…
         帳單金額會與押金互抵，多退少補」
⛔ 未寫入 answer 的「到期日依合約設定或點退當天計算」細節？—— 已含於「產生的時機」外，
   ⚠️ reviewer 請裁：到期日規則要不要進 representation
```

### 3406
```text
proposal：如何取得帳單收據／繳費證明：下載的位置與方式、
         收據可作為繳費證明、未繳費的帳單無法產生收據，
         以及收據與統一發票的區別。
evidence：answer「帳單繳費完成後可下載收據 PDF…在帳單詳情頁面點選『下載收據』…
         收據可供租客留存作為繳費證明。尚未繳費的帳單無法產生收據。
         若需要正式的統一發票，請參考發票開立功能另行處理」
⚠️ ⛔ 刻意未含 answer 的欄位清單（帳單編號／繳費日期／金額明細／付款方式）
   —— 那是 grounding 內容，非 semantic intent
```

### 3519
```text
proposal：點退帳單金額如何計算：加總哪些結算項目、如何扣抵押金，
         以及金額為正負時分別代表退款或需補繳差額。
evidence：answer「…水電費等結算費用，加上設備損壞賠償和違約金，再扣掉應退還的押金。
         帳單總額是負數就代表要退錢給租客，是正數則代表押金扣完還不夠，需要補繳差額」
⛔ 刻意未含 answer 的數字舉例（押金 20,000／水電 700…）
```

---

## deterministic instance 四列（⚠️ envelope 主要來自 capability）

### 3495
```text
proposal：診斷某一筆帳單為什麼無法發送給租客，
         包含發送失敗、寄不出、按發送無反應等情形。
evidence：answer「常見原因：狀態不對、金額未填、度數未填」（28 字）
         ＋ capability：bill_diagnosis → `_diagnose_cannot_send`（B01）對該筆判狀態與必填欄位
⚠️ answer 只列三個原因，**capability 涵蓋較寬** ⇒ representation 依 capability 撰寫
```

### 3496
```text
proposal：診斷某一筆帳單為什麼無法取消或作廢，包含取消按鈕不可用、
         取消時失敗等情形，以及可取消所需的帳單狀態條件。
evidence：answer「帳單取消需狀態為『應到帳』或『排定發送』。其他狀態不支援取消」
         ＋ capability：`_diagnose_cannot_cancel`（B02）
```

### 3498
```text
proposal：診斷某一筆帳單為什麼被收取逾期費／延遲金／滯納金，
         包含計費起算的日期認定與緩衝天數，以及金額如何得出。
evidence：answer「逾期費計算公式：租金 × 遲繳天數 × 費率%；遲繳天數 = 付款日 − 到期日 − 緩衝天數」
         ＋ capability：`_diagnose_late_fee`（B03）以該筆實值判定
⚠️ **刻意納入「滯納金」一詞** —— R7-B 的 #166 因該同義詞落空（B1）
   ⛔ 但這**不表示** representation 能解 B1 全家族（見 claim ceiling）
```

### 3499 ✅ `APPROVE`（responsibility-level）＋另列 answer defect
```text
定稿：查詢／診斷特定帳單手動到帳失敗、無法完成手動入帳的原因。
⛔ 不得寫成「常見原因包括 A／B／C」——除非 A/B/C 已由 capability 證明。

原 proposal：
proposal：診斷某一筆帳單手動到帳／標記已收款為什麼失敗，
         包含操作時出現的錯誤情形與可能原因。
evidence：answer「手動到帳失敗時前端會顯示錯誤訊息，常見三種」（22 字，⚠️ **未列出三種**）
         ＋ capability：`_diagnose_manual_complete`（B04）
⚠️ ⛔ 本列 answer 本身不完整（R1 已記）；representation 依 capability 撰寫，
   ⚠️ reviewer 請裁：是否同時補正該列 answer（**另案**，⛔ 不在本輪 scope）
```

---

## empty-answer anchors 三列（⚠️ envelope **全部**來自 capability）

### 4640
```text
proposal：查詢某一張收據的實際金額，例如某筆帳單的收據實收多少錢。
evidence：answer **空**；capability：bill_diagnosis → jgb_bills → B05 `_diagnose_receipt`
⚠️ 佐證：A03 的 I1-explicit **10/10 全對** ⇒ 現行 summary 已足夠，
   本 proposal 為**明示化**既有語義，⛔ 非擴張
```

### 4656   ← ⚠️ R8 判 MISSING 的那一列
```text
proposal：找出並查詢某一筆帳單目前的狀態，包括是否已繳費、
         是否已寄出或仍為草稿、到期情形，以及該筆帳單的現況。
evidence：answer **空**；capability：bill_diagnosis → jgb_bills → `_format_bill_status`
         （通用現況輸出）；required_slots=[bill_ref]
⚠️ 佐證：A03 的 I2-explicit **僅 3/10**，失敗 query 正是
   「那筆帳單到底繳了沒」「已寄出還是草稿」
⇒ 這正是 R8 指出「一個字都沒出現」的語義，⛔ 現行任何欄位皆未表示
```

### 4657 ⛔ `HOLD / REVIEW_BLOCKED_CAPABILITY_AMBIGUOUS`
```text
⚠️ blocker 是**選取步驟**不是金額：face_bill_response 對多列取 data[0]，
   _format_bill_status ⛔ 不讀 type ⇒ 「該合約的**點退**帳單」無法被辨識。
   金額本身**可證**（_bill_amount_due → bill["total"] → 「• 金額」）。
   完整證據與正對照見 r9-review-status.md。

原 proposal（⛔ 不批准）：
proposal：查詢某一份合約的點退結算帳單實際金額，例如退租結算最後要收或退多少錢。
evidence：answer **空**；capability：bill_diagnosis 查該筆點退帳單
⚠️ `diagnose_bill` **無點退專用分支** ⇒ 落 `_format_bill_status`
   ⚠️ reviewer 請裁：representation 是否應反映此限制
```

---

## ⚠️ Claim ceiling（本輪定案時必須一併記）

```text
✅ 本 population 修的是 **representation contract 缺口**
⛔ **不**宣稱會解掉 B1 ×5（匯出≈下載／滯納金／跳錯誤／缺錨詞——模型泛化問題）
⛔ **不**宣稱會解掉 B3 ×2（clean reranker discrimination candidates）
⛔ **不**因此取得 gate authorization
⇒ 正確表述：**完成 representation-contract defect 的候選修復；
  其餘 model／generalization defects 仍須獨立驗證。**
```

## 三個 reviewer 待裁點

```text
① 3402：到期日規則要不要進 representation
② 3499：是否同時補正該列不完整的 answer（**另案**）
③ 4657：representation 是否應反映「無點退專用分支」的限制
```
