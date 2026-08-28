# Architecture premise audit｜立案（2026-08-29 業主裁定）

> **暫停 3.4 與 instance-gate authorization。** D1→D3 已提供足夠訊號要求上游檢驗；
> 繼續替 gate 找授權，是在**精密地驗證一個可能錯的前提**。

## 觸發這個裁定的兩件事

```text
① D1→D3 一直在驗「gate 能不能正確阻止 candidate」，
   但 D3 顯示：許多理論上需要 instance handling 的 query
   **根本沒有 candidate 可以讓 gate 管**。
   ⇒ 若 nomination layer 的 coverage 本身不成立，gate 授權只是局部問題。
② 這幾天的討論一路把架構前提當成公理在用。
```

## ⚠️ 兩個必須先更正的前提錯誤（否則又拿驗證證明自己的預設）

```text
更正一：D3 的 60 句是**合成**，不是真實 instance 問句
  strata A = 真實 rule 40｜strata B = **合成** instance 60
  「36/60 沒有 nomination」只能推出：
    **在這批合成且被盲標為 instance 的問句裡**，現行 nomination 對 36 句未產生 Face candidate。
  ⛔ 不得推出「真實使用者的 instance 問句有六成進不了面向」。
  ⇒ 足以要求往上游查，**不足以估 production coverage**。

更正二：架構前提不是「top1 categories 決定該由哪個面向負責」
  裁定 001 已定：category = **nomination evidence only**；
                commit authority = responsibility resolver。
  ⇒ 待驗的是：**retrieval + category 這套 nomination mechanism，
     能否產生足夠且正確的 responsibility candidates。**
```

## 為什麼不能直接追那 36 句

```text
它們是 synthetic，且標註框架本身就預設「instance → 應進 dialog / Face」。
拿「盲標者認為應進 Face」當 oracle，再問「為什麼系統沒進 Face」，
**仍然是用架構本身驗架構**。
⛔ 36/60 不得成為新的產品 KPI。
```

## 要驗架構，標籤必須往上一層

標註**完全不提**：`Face`／`single`／`dialog`／`bill_diagnosis`／`contract_closeout`／
`category`／`0.75`／`instance gate`／`resolver`。

改問與現有 implementation 無關的產品命題：

```text
A 是否需要使用者／物件／合約／帳單的**個別資料**？
B 現有問句是否已提供足夠識別資訊？
C 是否必須讀取系統狀態／API 才能正確回答？
D 是否可以只靠通用知識一次回答完整？
E 若資訊不足，需要追問**什麼類型**的資訊？
F 使用者真正要完成的是：理解規則／查實際狀態／執行操作／排除異常
```

## 兩層分析

```text
Layer 0  User need / capability truth
         這個需求到底需要：通用知識？個別資料？API grounding？追問？操作？
Layer 1  Current architecture mapping
         retrieval → nomination → eligibility → responsibility → execution
         是否真的把 Layer 0 的需求接住？
```

要回答的是：

> **現行「retrieval → nomination → responsibility → Face」架構，
> 能不能把需要個別資料處理的需求，送到具有該能力的處理路徑？**

而**不是**「有沒有符合我們事先規定好的 Face label」。

## 待驗假設（取代先前那份「六個假設」）

```text
H1 「通用說明」與「需要個別狀態／資料」是有產品價值的區分嗎？
H2 retrieval knowledge 的 metadata／categories 是否足以作為 Face candidate nomination evidence？
H3 目前 Face capability／responsibility 的劃分，是否涵蓋真實使用者需要完成的工作？
H4 similarity ≥ 0.75 作為 nomination eligibility，是否會合理保留所需 candidates？
H5 一輪只選一條 responsibility path，是否足以處理實際 query？
H6 需要個別資料的 query 在資訊不足時，是否**真的**應進多輪追問；
   還是有些可以直接 grounding／tool call 後單輪回答？
```

### H6 為何特別重要

```text
「instance」不必然等於「多輪」。
  使用者：「合約 89557 現在狀態？」
  識別碼已經給了 ⇒ 最好的 UX 可能是**直接 grounding 後回答**，
  而不是進 Face 再問一次合約編號。
⇒ `instance = dialog` 本身就該被驗，**不得當公理**。
```

## ⚠️ 立即的執行障礙：真實對話語料同樣稀缺

本 audit 要求**真實** conversation corpus，但已知來源都有問題：

```text
assistant-reports 37 份   30 份做過知識工程（KB 已對其調整）、37 份全量重播
                          ⇒ 對「nomination layer」而言**已污染**
                          （KB 被它們調過，量 nomination 等於量自己調過的東西）
pages released 1571 句    真實，但源自幫助中心 ⇒ 結構性偏 rule-side；
                          且已釋出供知識工程使用，用了就會再被 KB 調整
production 流量           usage-metering 明訂**不存原文**，事後撈不回來
```

⇒ **這個障礙必須在設計 audit 取樣之前解決，不能做到一半才發現**——
D2／D3 連續兩輪的教訓就是「coverage 不足本身是發現，不是重抽的理由」。

## 本裁定的狀態

```text
3.4                     ⏸️ PAUSED（非取消）
instance-gate 授權       ⏸️ PAUSED
D3 的 A 層量測結果       保留為 evidence（rule-side 43.3%／instance-side 21.7%／abstain 57%）
                        ⚠️ 但那是「在現行架構前提下」的量測，不因暫停而變成架構結論
下一步                   先解語料來源，再設計 Layer 0 標註協定
```
