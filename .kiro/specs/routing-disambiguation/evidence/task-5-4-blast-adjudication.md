# 任務 5.4：BLAST 七筆 intended behavior 判定（**先判定、後實測**）

> 2026-08-24｜語言 zh-TW｜_Requirements: 5.2, 7.3_
> **freeze 狀態：待業主裁定**（本檔為依據盤點，尚未 freeze）
> ⚠️ 本輪**只盤依據**：未跑 candidate、未改任何 assertion。

## 依據分類（只有 A–C 有資格直接支撐 intended behavior）

```text
A 產品 owner／明確產品規格
B 已核准設計或既有業務規則
C 已定案 regression／acceptance contract
D migration／commit／provenance      ← 只能解釋「今天為何如此」
E current route／metadata／observed  ← 同上
```

**provenance ≠ justification**：D／E 不得單獨 freeze expectation。

## ⚠️ 誠實揭露：本判定**非盲標**

任務 5.1 的 baseline 已記錄 BLAST 七筆實際 route（全為 `dialog:條件診斷：帳單`）。
故本檔**無法宣稱盲標**。緩解方式：每一筆的依據**逐條指名出處**，
可獨立於實測結果查核；且**不因七筆現況相同就給七筆相同 expectation**。

## 兩個面向的自述範疇（B 類，逐字引自 seed）

```text
條件診斷：帳單（bill_diagnosis）
  「協助管理者查『這筆帳單為什麼發不出去／取消不了／被收逾期費／手動到帳失敗』
    這類**單筆操作問題**」
  ＋【追問識別】未給編號時**由面向追問** → 進場不以問句已含識別為前提

帳單異常（billing_anomaly）
  「協助管理者查『金額不對／帳單沒出現／租客看不到帳單』」
  ＋「『為什麼是這個數字』只用底稿列出的組成回答」
```

## 判定表

| # | 案例 | 可用依據 | 類型 | 強度 | 直接支持此問句 | 建議 intended route | 裁定 |
|---|---|---|---|---|---|---|---|
| 1 | 帳單為什麼發不出去 | bill_diagnosis 自述範疇逐字含「發不出去」；`test_facet_entry_routing_req.py:157` BILLING_DIALOG_CASES 成員＋「2026-07-06 帳單診斷面向立案後改判進對話（3495 錨點，原 form_fill 保留裁定過時）」 | **B＋C** | 強 | ✅ 逐字命中 | `dialog:條件診斷：帳單` | **ADJUDICATED** |
| 2 | 帳單為什麼取消不了 | bill_diagnosis 自述範疇逐字含「取消不了」；`test_bill_diagnosis_facet_req.py:90` 以該句驅動面向作答 | **B** | 強 | ✅ 逐字命中 | `dialog:條件診斷：帳單` | **ADJUDICATED** |
| 3 | 為什麼被收逾期費 | bill_diagnosis 自述範疇逐字含「被收逾期費」 | **B** | 強 | ✅ 逐字命中 | `dialog:條件診斷：帳單` | **ADJUDICATED** |
| 4 | 帳單手動到帳失敗 | bill_diagnosis 自述範疇逐字含「手動到帳失敗」；`test_bill_diagnosis_facet_req.py:45` 以該句驅動面向作答 | **B** | 強 | ✅ 逐字命中 | `dialog:條件診斷：帳單` | **ADJUDICATED** |
| 5 | 這張帳單的收據金額多少 | protocol v1 **INSTANCE** 案例集，`expected: dialog:條件診斷：帳單`（已凍結）；`test_facet_entry_routing_req.py:193` BILLING_INSTANCE_CASES 成員 | **C** | 強 | ✅ 同一問句 | `dialog:條件診斷：帳單` | **ADJUDICATED（附張力）** |
| 6 | 我要查帳單 編號 12345 | **查無 A／B／C**。兩個面向的自述範疇皆未涵蓋「純查詢」：bill_diagnosis 限四類**操作問題**，billing_anomaly 限金額不對／沒出現／看不到。僅有 E（現行 route） | **E** | 無 | ❌ | **不建議**（route 與 facet 皆未定） | **UNADJUDICATED** |
| 7 | 幫我查點退帳單金額 | protocol v1 **INSTANCE** 案例集，`expected: dialog:條件診斷：帳單`（已凍結）；`test_facet_entry_routing_req.py:192` BILLING_INSTANCE_CASES 成員 | **C** | 強 | ✅ 同一問句 | `dialog:條件診斷：帳單` | **ADJUDICATED** |

## 第 5 筆的張力（提請裁示，我不自行選一份）

```text
C（凍結 acceptance）：這張帳單的收據金額多少 → 條件診斷：帳單
B（面向自述 scope）：bill_diagnosis 明訂「帳單**金額組成**／看不到帳單（帳單異常）→ scope=switch」
                     billing_anomaly 明訂「『為什麼是這個數字』只用底稿組成回答」
```

**我的讀法**：「收據金額**多少**」是**取值查詢**（bill_diagnosis 的 API grounding
本就回傳帳單存值），與「金額**組成／為什麼是這個數字**」不同，故不構成直接矛盾，
判 **ADJUDICATED**＋記張力。
⚠️ 若業主讀為同一件事，本筆應改判 **CONFLICTING_EVIDENCE** 並退出 assertion。

## 第 6 筆為何不補理由

「我要查帳單 編號 12345」帶明確識別，**技術上**必然被 gate 判 `allow`（identifier 正向證據），
實測也確實進面向——但**那是 E 類**。
產品上「純查一筆帳單」該進哪個面向（或該不該進面向）**沒有任何 A／B／C 依據**。
依 Req.7.3：**不得讓「維持現況」自動升格為 non-regression contract**。
故本筆只記 blast observation，**不計 PASS／FAIL**。

## 裁定後的處置（待業主 freeze）

```text
ADJUDICATED 6 筆 → freeze expected → 進 Req.5.2 non-regression assertion
UNADJUDICATED 1 筆 → 只記 observation，不入 assertion
freeze 時間戳／commit → 於業主裁定後補記，防止看到實測再改 intended behavior
```
