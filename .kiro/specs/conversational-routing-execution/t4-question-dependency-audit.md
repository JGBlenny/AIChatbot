# T4：bill-domain builders 的 question dependency static audit（2026-08-29）

```text
問題（凍結）  late_fee 是否為 bill-domain deterministic builders 中
              **唯一**缺少 question-sensitive fact branching 的結構性例外？
⛔ 不跑語料、⛔ 不改碼
判準          `user_question`（**含 alias**）是否實際改變 deterministic fact
              selection／branching；⛔「變數出現過」不算，log／顯示不算
```

## 結果

| builder | sig | body 讀取 | if-test 分流 | 傳給下游 | 判定 |
|---|---|---|---|---|---|
| `build_payment_flow_facts` | ✅ | 1 | ✅ | — | QUESTION_SENSITIVE |
| `build_bill_anomaly_facts` | ✅ | **0** | — | — | **NOT_QUESTION_SENSITIVE** |
| `build_invoice_facts` | ✅ | 1 | — | `diagnose_invoice_logs` | QUESTION_SENSITIVE（下游） |
| `build_bill_diagnosis_facts` | ✅ | 1 | ✅ | `is_late_fee_intent`／`diagnose_bill` | QUESTION_SENSITIVE |
| `build_late_fee_facts` | ✅ | **0** | — | — | **NOT_QUESTION_SENSITIVE** |

## Verdict：**S3 — MIXED**

```text
不具 question sensitivity 的 builder：帳單異常、滯納金（**兩個**）
⇒ late_fee **不是**唯一例外
⛔ 不能用「唯一 outlier」講故事，⛔ 不能宣稱它缺了別人普遍具有的能力層
```

### ⚠️ 量尺第三次踩同一個坑（已修）

```text
第一版把 `build_bill_diagnosis_facts` 誤判成「讀取但未分流」——
因為它寫的是 `q = user_question or ""` 再 `if ... in q`，是**一層 alias**。
補上 alias 傳遞後才正確判為 QUESTION_SENSITIVE。
⚠️ 本專案已第三次被 alias／子字串類的量尺缺陷騙到
（前兩次：embedding surface 掃描漏 alias；formatter 比對被罐頭句打中）。
```

## 上游檢查：late_fee 路徑在 builder 之前**也沒有** sub-intent 分流

```text
face_bill_response(endpoint, data, user_question, face)
  → BILL_FACE_BUILDERS[face]        # 只依 face 名稱選 builder
  → build_late_fee_facts(row, q)    # q 未被使用
⇒ 整條 deterministic late_fee execution path 從進 Face 到 facts
  **都沒有** sub-intent distinction
```

## ⚠️ 但另有一個**支持 KEEP_BOTH** 的結構性發現

`帳單異常` face 與 late_fee 是同一形狀，而且更明顯：

```text
帳單異常（builder 同樣 NOT_QUESTION_SENSITIVE）底下有 **三個** empty-answer anchor：
  3934 帳單金額怪怪的 跟預期不一樣
  3935 這期帳單怎麼還沒出來
  3936 租客說看不到帳單 找不到
⇒ 三者的**產品 intent 明顯不同**（金額異常／未產生／可見性），
  但它們共用同一個 question-insensitive builder，各自只負責**進場辨識**。
```

⇒ 「**多個 entry anchor 共用一份 question-insensitive facts**」是本 codebase 的
**既有設計**，⛔ 不是 late_fee 的異常。facts 相同 ⇒ ⛔ **不足以**推出責任相同。

⚠️ 反向證據也要記：A04 的兩位獨立 labeler 把
`(3934,3935,3936)` 判為 MULTI_OWNER ×9、`(3939,3940)` ×3 ——
連人在只看責任規格時也難以分離。⇒ 兩邊都有證據，⛔ 不宜單向下結論。

## ⇒ 對 3939／3940 的裁定輸入

```text
✅ S3 成立：⛔ 不得用「late_fee 是唯一 outlier」支持讀法 B
✅ 但「多 anchor 共用一份 facts」是既有設計 ⇒ ⛔ 也不得用
   「facts 相同」直接支持讀法 A（CONSOLIDATE_ONE）
⇒ 目前狀態維持：
   DUPLICATE_UNDER_CURRENT_CAPABILITY
   product distinction = **OPEN**
```

⚠️ 下一個能真正分辨的證據，只剩 **3939／3940 的原始設計來源或責任文件**
（它們為何被拆成兩列），⛔ 不是再多的程式靜態分析。
