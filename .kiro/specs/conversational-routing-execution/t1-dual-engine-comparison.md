# T1：滯納金雙引擎決定性能力比對（2026-08-29）

```text
scope   `_diagnose_late_fee`（A，條件診斷：帳單 face／3498）
        `build_late_fee_facts`（B，滯納金 face／3939・3940）
⛔ 無語料 ⛔ 無檢索 ⛔ 無 LLM ⛔ 未改任何 KB／applicability／routing
方法    同一組固定 fixture 分別送兩個引擎，只記決定性事實類別
```

## Verdict：**E3 — ONE_SIDE_PARTIAL**（A 為殘缺的一方）

```text
共有事實類別 26｜A-only 5｜B-only 13
⇒ ⛔ 不是 E1（兩者不等價，B 明顯較完整）
⇒ ⛔ 不是 E2（A 沒有一塊 B 拿不到的**責任領域**，只有一個 B 沒印的**欄位**）
```

## A-only 的 5 項，逐項看**其實只有 1 項是真能力**

| case | A-only 項目 | 實質 |
|---|---|---|
| 3 已付款 | 含繳費／到帳時間 | ✅ **真能力**：A 印 `pay_at`／`complete_at`，B 完全不印 |
| 4 合約列 | 含帳單識別 | ❌ **缺陷**：A 把**合約**列叫成「帳單「忠孝東路 3F 租約」」 |
| 4 合約列 | 指出資料缺失 | ❌ 同上，是誤判情境後的罐頭句 |
| 5 滯納金帳單列 | 指出資料缺失 | ❌ **缺陷**：A 認不出這是滯納金帳單，答「此帳單尚未繳費。若超過繳費期限仍未付款，系統會依合約設定計算逾期費」——**把滯納金帳單當成會被加收滯納金的帳單** |
| 6 資料不全 | 含繳費期限 | ❌ fixture 無 `date_expire`，A 仍印標題行 ⇒ 量尺誤判，非能力 |

⇒ **A 真正獨有的只有 `pay_at`／`complete_at` 兩個欄位。**

## B-only 的 13 項：整段責任面

```text
每個 case  帳單狀態、實際金額（`_bill_head`；A **完全沒有**）
case 4     讀出**合約實值**「費率 5%、緩衝 3 天」＋兩種結算機制說明
case 5     讀出**實際結算備註**「租金 25000 × 遲繳 10 天 × 0.5% = 1,250」
           並認得這是滯納金帳單（`type==4` 或標題含延遲金／滯納）
case 6     大聲降級
```

## ⚠️ 量尺自身的修正（第一版誤判，已改並重跑）

```text
第一版把 A 在 case 3 的「緩衝天數、百分比」算成「解釋怎麼算」與「含合約設定值」
—— 那只是**背誦欄位名**，⛔ 沒有任何實值。
收緊為必須出現實際數值（`費率 \d+%`／`緩衝 \d+ 天`／`×`／結算備註）後，
A-only 由 7 降為 5。
```

## 三軸歸屬（依實測，⛔ 非依 row 文字或 face 名稱）

```text
general mechanism    B 有（case 4 的兩種機制說明、case 5 的不累加規則）；A **無**
instance diagnosis   B 有（識別＋狀態＋金額＋設定實值）；A 只有期限與付款時間
amount calculation   B 有（實際結算備註逐字）；A **無**（只有罐頭句）
```

## ⇒ 對產品裁定 ② 的輸入

```text
⛔ 不建議設 precedence 長期維持兩套引擎——A 不是「另一個責任領域」，
   而是同一責任的**較弱實作**，且在 case 4／5 會產生**語義錯誤**的輸出。
✅ 若收斂為單一 owner，B 是唯一能承接三軸的一方；
   ⚠️ 但收斂前必須把 A 獨有的 `pay_at`／`complete_at` 補進 B，否則會**丟能力**。
⚠️ 這兩個欄位是「已付款卻仍被收滯納金」情境的關鍵事實。
```

## ⛔ 本輪未做

```text
⛔ 未改任何引擎、未改 KB、未改 applicability、未改 routing precedence
⛔ 未裁 3498 的 row identity（依業主順序：先裁 ownership capability）
```

---

# Step 1：`pay_at`／`complete_at` 搬進 B（業主授權 2026-08-29）

```text
LATE_FEE_INSTANCE_OWNERSHIP
  B / late_fee face                        → AUTHORITATIVE OWNER CANDIDATE
  A / bill_diagnosis._diagnose_late_fee    → SUPERSEDED_PARTIAL_IMPLEMENTATION
  precedence between A/B                   → **REJECTED**
```
⚠️ 理由：在 T1 的證據下設 precedence，等於刻意保留一條**已知會答錯**的 owner，
只是在前面再加規則避免走到它——沒有產品價值，還擴大 routing state space。

## 射程（⛔ 只搬 T1 判定為 genuine 的那一項）

```text
✅ pay_at／complete_at，存在才輸出
⛔ 不臆測、⛔ 不補值
⛔ 不搬 A 的罐頭逾期說明、⛔ 不搬 A 的 due-date 推論、
⛔ 不搬 A 的欄位名背誦、⛔ 不搬 A 的任何既有文案
```
落點：`_payment_time_lines()`，掛在 B 的**兩個帳單列分支**（一般帳單／滯納金帳單）。
⚠️ 合約列分支 ⛔ 不掛——合約沒有付款時間語義。

## 5 組 guard ＋ mutation（8 條全過）

```text
1 已付款且有 pay_at/complete_at → 必須保留，且 B 原有 狀態／金額 不得丟
2 未付款 → ⛔ 不得偽造付款時間；只有 complete_at 時 ⛔ 不得生出繳費時間
3 滯納金帳單 → 結算備註與「不累加」規則不變，
  且 ⛔ 不得繼承 A 的錯誤語義「若超過繳費期限仍未付款…」
4 合約設定 → 費率／緩衝／兩種機制不變；⛔ 合約列不得出現付款時間
5 mutation：拿掉 `_payment_time_lines` 投影 ⇒ guard 1 必須紅
```

## Capability closure：`B_after` vs `A_before ∪ B_before`

```text
B_after 未覆蓋的 A_before 有效 facts：無 ✅
B_after 繼承的 A 錯誤 facts：          無 ✅
⇒ **B_CAPABILITY_SUPERSET = CONFIRMED**
```

### ⚠️ 量尺第二次收緊（又一次誤判，已修正並重跑）

```text
case 6 的 fixture **沒有** date_expire，A 卻被判成「有繳費期限 fact」——
因為純子字串比對打中了 A 的罐頭句「若超過**繳費期限**仍未付款」。
改為必須是**帶值的標籤** `繳費期限：<數字>` 後，該假缺口消失。
⚠️ 這是本案第二次「量尺打中罐頭文案」；第一次是 case 3 的「緩衝天數、百分比」。
⇒ 教訓：比對 formatter 時，**子字串命中 ≠ 該 fact 存在**，罐頭句會製造兩種假象
  （假能力／假缺口），必須要求帶值。
```

## ⛔ 本 commit **未**做（業主要求分刀）

```text
⛔ 未取消 bill_diagnosis 對 late-fee instance intent 的 ownership
⛔ 未動 `diagnose_bill` 的「逾期／延遲金／滯納金／late fee」關鍵字
   —— 需先確認它們現在究竟是 nomination keyword、`_diagnose_late_fee` dispatch、
     還是一般帳單狀態查詢的其他用途；只移除 **owner conflict 的那條 dispatch
     authority**，⛔ 不得誤傷普通帳單狀態查詢
⛔ 未裁 3498 的 Knowledge identity
```

⚠️ 業主已定案的分界：**「不再是 instance owner」已成立；「應該成為 general row」尚未成立。**
⛔ 不得因 instance owner 搬走，就機械地把 `instance` 翻成 `general`。

---

# Step 2：late-fee instance ownership 收斂（業主授權 2026-08-29）

⚠️ 業主指出的關鍵：**只刪 dispatch 不足以證明「A 不再擁有這個 intent」**——
它會改落 `bill_diagnosis` 的 generic path，那只是「A 不再專門診斷滯納金」。

## 兩件事一起做

```text
A execution  移除 `diagnose_bill → _diagnose_late_fee` dispatch
B authority  late-fee intent 若仍因 legacy nomination 抵達 bill_diagnosis，
             bill_diagnosis **不得 commit** ⇒ 決定性排除並明示轉交唯一 owner
```
實作：`is_late_fee_intent()` ＋ `late_fee_exclusion_facts()`。
⚠️ 排除點放在 `build_bill_diagnosis_facts` 的**最前面**——`_DIAG_KEYWORDS` 仍含
逾期／延遲金／滯納金，少了這道排除，query 會被帶進 `diagnose_bill` 再落 generic path，
**正是業主指出的錯誤綠燈**。
`_diagnose_late_fee` 保留但標記 `SUPERSEDED / NO AUTHORITY`，⛔ 不得再被任何 dispatch 呼叫。

## `_DIAG_KEYWORDS` ⛔ 未動

```text
它是「這句有沒有診斷症狀」的 generic discriminator
⛔ 不是 late-fee ownership declaration
動它會誤傷發送／取消／手動到帳三種診斷
```
判定詞 `LATE_FEE_INTENT_KEYWORDS` **逐字沿用**原 dispatch 那組
（`逾期／延遲金／滯納金／late fee`）——換一組就是偷偷改 ownership 邊界，有測試鎖住。

## Guard 1–6 ＋ M1／M2（20 條全過）

```text
1–3 三種 late-fee 提法 → 一律 exclusion，⛔ 不落 generic path、⛔ 無 A 的罐頭句
4–6 發不出去／取消不了／手動到帳 → 仍由 bill_diagnosis 承接，⛔ 未被吸走
＋   任何 late-fee 提法 ⛔ 不得抵達 `_diagnose_late_fee`（以 spy 驗呼叫次數＝0）
M1  關掉 intent 判定（等同恢復舊 dispatch）⇒ ownership guard 必須紅
M2  拿掉 exclusion（authority transfer）⇒ query 被 A 收斂回答，必須紅
```

## 不變量 14（三組正對照）

```text
① late-fee intent ⛔ 不得由 bill_diagnosis 收斂作答（含 generic path）
② `_DIAG_KEYWORDS` 必須不變
正對照：關掉判定必紅／誤傷其他診斷必紅／動 `_DIAG_KEYWORDS` 必紅
```

### ⚠️ 不變量 14 一度**害不變量 7 變紅**（已修）

```text
本檢查器是唯一從 host 直接 import `services.jgb.bills` 的稽核項，
產生的 `__pycache__/bills.cpython-*.pyc` 內含原始字串
⇒ 被**不變量 7**（金額欄位語義層）的原始碼掃描當成違規。
⇒ 修法：檢查器在 import 前設 `sys.dont_write_bytecode = True`，並清掉殘留 .pyc。
⚠️ **一條不變量不得因為另一條不變量的副產物而變紅**；
⛔ 我沒有改不變量 7 的判準來遷就它。
```

## 狀態

```text
B_CAPABILITY_SUPERSET          CONFIRMED ✅
late_fee instance owner        **B ONLY** ✅
A._diagnose_late_fee           SUPERSEDED / no authority ✅
_DIAG_KEYWORDS                 UNCHANGED ✅
other bill diagnosis           REGRESSION-GUARDED ✅
```

⚠️ **仍未成立**：「3498 應改 general」。Step 2 只證明
`3498 不再有資格代表 bill_diagnosis 的 late-fee instance ownership`。
下一刀單獨裁 3498 的 Knowledge identity（純 general／被 3531-3532 吸收後停用／
另有窄責任），⛔ 不得機械地把 `instance` 翻成 `general`。
