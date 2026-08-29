# Level-A scope（`bill_diagnosis`）最後 6 筆 truth 逐筆裁定表

- 日期：2026-08-29｜⛔ **本輪不做 blind labeling**——這是 authority truth contract 的逐筆裁定
- `proposed declaration` 與 `裁定理由` **留空待業主填**
- 判準（已定案，唯一）：**正確完成這個 intent，是否必須依賴 user-specific / instance-specific runtime data**

## 護欄（每一筆都要過）

```text
⛔ 不得因為答案現在寫成通用說明就判 general —— 3509 已證明這會錯
⛔ 不得因為有 API／form／diagnostic engine 就自動判 instance
✅ general 必須有**正面理由**：即使知道此人的帳號／帳單／合約狀態，
   也不需要讀取，光靠產品規則就能正確完成 intent
✅ instance 必須有**必要性理由**：不讀該使用者的 runtime state 就無法正確回答
✅ 判不出來留 UNKNOWN，⛔ 不為補滿 Level-A truth 而硬裁
⚠️ 來源桶只做 provenance，**不得影響裁定方向**——
   後三筆⛔ 不因「之前被盲標 general」而有預設立場
```

## ⚠️ 一個盲標者看不到的結構性證據

```text
KB 對同一主題**成對**存在兩列：
  「機制列」  有完整通用答案，解釋規則怎麼算
  「錨點列」  **answer 長度 = 0**，唯一作用是讓 top1 命中後進面向

  收據：3406「帳單收據 繳費證明 PDF 下載」(130 字) ／ 4640「帳單收據金額 收據多少錢」(0 字)
  點退：3519「點退帳單金額計算 押金結算」(190 字) ／ 4657「合約的點退帳單金額 查點退金額」(0 字)

而 `chat.py::_drop_empty_answer_rows` 明文：
  「answer 空且無任何動作的知識＝**面向進場錨點**，只供進場判定用；
    落回單發答題前必須濾除」
⇒ 錨點列在設計上**不可能**用通用文字回答——它存在的理由就是把問題交給面向。
```

## 逐筆表

### ① 3402 — 來源：general review queue（盲標 A=general, B=general）

```text
問題        點退帳單 自動產生 費用結算
categories  帳單管理／條件診斷：帳單
candidates  bill_diagnosis（REQUIRED）
answer      「點退完成後系統自動產生點退帳單，內容包含：（1）水電等未結費用…
             （2）設施損壞賠償…（3）其他費用…到期日依合約設定或點退當天計算。
             帳單金額會與押金互抵，多退少補。」（124 字，direct_answer）
deterministic evidence   無（P1b 判 UNKNOWN）
capability evidence      diagnose_bill 分支命中：**無**
proposed declaration     ______
裁定理由                 ______
```

### ② 3406 — 來源：general review queue（盲標 A=general, B=general）

```text
問題        帳單收據 繳費證明 PDF 下載
categories  帳單管理／條件診斷：帳單
candidates  bill_diagnosis（REQUIRED）
answer      「帳單繳費完成後可下載收據 PDF…在帳單詳情頁面點選「下載收據」…
             尚未繳費的帳單無法產生收據。」（130 字，direct_answer）
deterministic evidence   無
capability evidence      diagnose_bill 分支命中：**B05 收據查詢**
                         ⚠️ 且 KB 另有錨點列 4640「帳單收據金額 收據多少錢」（0 字）
proposed declaration     ______
裁定理由                 ______
```

### ③ 3519 — 來源：general review queue（盲標 A=general, B=general）

```text
問題        點退帳單金額計算 押金結算
categories  合約管理／條件診斷：帳單
candidates  bill_diagnosis（REQUIRED）
answer      「…金額算法是：水電費等結算費用，加上設備損壞賠償和違約金，再扣掉應退還的押金。
             帳單總額是負數就代表要退錢給租客…舉例：押金 20,000、水電 700、賠償 5,000
             ⇒ -14,300…」（190 字，含**通用算式與舉例**，direct_answer）
deterministic evidence   無
capability evidence      diagnose_bill 分支命中：**無**
                         ⚠️ 且 KB 另有錨點列 4657「合約的點退帳單金額 查點退金額」（0 字）
proposed declaration     ______
裁定理由                 ______
```

### ④ 4640 — 來源：INSTANCE_PROPOSAL（盲標 A=instance, B=instance）

```text
問題        帳單收據金額 收據多少錢
categories  條件診斷：帳單
candidates  bill_diagnosis（REQUIRED）
answer      **（空，0 字）** ⇒ 面向進場錨點
deterministic evidence   無（P1b 的 E1/E2/E3 皆未命中——它沒有表單也沒有引擎標題對應）
capability evidence      diagnose_bill 分支命中：**B05 收據查詢**
                         ⚠️ 對照：`_diagnose_receipt` 曾因直接讀 final_total 把已繳帳單
                         答成「收據金額 NT$ 0」（不變量 7 的源起）——該分支確實取實值
proposed declaration     ______
裁定理由                 ______
```

### ⑤ 4656 — 來源：INSTANCE_PROPOSAL（盲標 A=instance, B=instance）

```text
問題        查帳單 帳單編號查詢
categories  條件診斷：帳單
candidates  bill_diagnosis（REQUIRED）
answer      **（空，0 字）** ⇒ 面向進場錨點
deterministic evidence   無
capability evidence      diagnose_bill 分支命中：無（落 `_format_bill_status` 通用現況輸出）
                         ⚠️ bill_diagnosis 的 required_slots=[bill_ref] ⇒ 進場後必問是哪一筆
proposed declaration     ______
裁定理由                 ______
```

### ⑥ 4657 — 來源：INSTANCE_PROPOSAL（盲標 A=instance, B=instance）

```text
問題        合約的點退帳單金額 查點退金額
categories  條件診斷：帳單
candidates  bill_diagnosis（REQUIRED）
answer      **（空，0 字）** ⇒ 面向進場錨點
deterministic evidence   無
capability evidence      diagnose_bill 分支命中：無
                         ⚠️ 與 3519（通用算式）成對存在
proposed declaration     ______
裁定理由                 ______
```

## 裁完之後

```text
bill_diagnosis scope 的 10 筆將首次全部具備明示 truth
（現況：4 已宣告 instance ＋ 這 6 筆）
⇒ 才具備重新進入 gate authorization 的**資料前提**
⏸ 3.4 仍 PAUSED；⛔ 本輪不擴 scope、不碰 B 桶 18 筆、不碰 D 桶 55 筆
```
