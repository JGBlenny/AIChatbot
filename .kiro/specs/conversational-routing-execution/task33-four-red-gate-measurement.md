# 現行 4 筆紅在 deterministic gate 下的判定

- 日期：2026-08-28｜方法：**只跑 deterministic gate ＋ 檢索 ＋ config 查表**，不跑 resolver、無 LLM
- 目的：把 3.4 的阻塞分流到 scope／classifier／其他

## 結果：**四筆全部 `block`，且四筆的納管判定全部成立**

| 問句 | verdict | nomination cats | 落到的 Face | C | D | `gate_applies_to` |
|---|---|---|---|---|---|---|
| 收據 PDF 在哪裡下載 | **block** | 帳單管理／條件診斷：帳單 | `bill_diagnosis` | ✅ | ✅ | **True** |
| 點退做完後，帳單會自動出來嗎？ | **block** | 帳單管理／條件診斷：帳單 | `bill_diagnosis` | ✅ | ✅ | **True** |
| 系統怎麼算點退帳單的金額 | **block** | 合約管理／條件診斷：帳單 | `bill_diagnosis` | ✅ | ✅ | **True** |
| 點退帳單的金額是怎麼算的 | **block** | 合約管理／條件診斷：帳單 | `bill_diagnosis` | ✅ | ✅ | **True** |

四筆的 `reason` 皆為 `no-positive+counter=['explanation_request']`
——正是「這是規則說明、不是 instance 問法」的決定性證據。

## ⚠️ 這不落在原判讀矩陣的任何一列

原矩陣的「全部 block」那一列寫的是「classifier 已會判，**只是 consumer 沒納管對應 Face**」。
但實測 **consumer 有納管**（`gate_applies_to=True`）。

```text
⇒ 3.4 的阻塞既不是 scope coverage，也不是 classifier coverage。
   唯一擋著的是：**gate 未被授權啟用**。
```

## 模擬（把「會轉綠」從推論變成量測）

⚠️ 以真實 gate 判定取代 `_instance_gate_decision`（後者因未授權恆回 None），
其餘一律走 production seam。**這是 simulation，不代表 gate 已授權。**

```text
「收據 PDF 在哪裡下載」      gateOFF→帳單異常        gateON→single   期望=單發
「點退做完後，帳單會自動出來嗎？」 gateOFF→條件診斷：帳單   gateON→single   期望=單發
「系統怎麼算點退帳單的金額」    gateOFF→single         gateON→single   期望=單發
「點退帳單的金額是怎麼算的」    gateOFF→退租收尾        gateON→single   期望=單發
```

兩個附帶事實：

```text
① gate ON 時四筆**全部符合期望**。
② gate OFF 時四筆的去向彼此不一致（帳單異常／條件診斷：帳單／single／退租收尾）——
   因為此時是 resolver 的 LLM 在決定，這正是 integration 失敗數 5～7 擺動的來源。
   gate ON 時抑制發生在 resolver **之前**，四筆都不再進 resolver ⇒ 結果也就決定性了。
```

## 與 holdout「routing effect 0/50」的關係（**兩者不衝突**）

```text
holdout 的 11 筆 block：9 筆本來就 single、2 筆落在 bill_diagnosis 以外的 Face
                        → 沒有一筆落在納管 Face 上 → effect 0
本次 4 筆 block：**全部**落在 bill_diagnosis（納管 Face）→ effect 4/4
⇒ 舊反證測到的是「那 50 筆樣本上沒有效果」，
   不等於「這個機制是惰性的」。兩者是**取樣**差異，不是矛盾。
```

## ⛔ 這份量測**不能**用來宣布 gate 通過

```text
這 4 筆正是我們想修綠的回歸案例，屬**已看過**的資料。
拿它當授權依據＝「修到這批有效再宣布通過」，正是裁定 002 ② 禁止的反模式。
它只能回答一件事：3.4 的阻塞落在哪一層。
```

## 待裁定（結果推翻了裁定 002 ② 的前提，故必須回頭問）

裁定 002 ② 寫的是：

> 若同一 implementation 已被 holdout REFUTED → 先**修改 deterministic classifier**，
> 再用新的未看過 matching holdout 驗證。

但現在的證據是：**classifier 對這 4 筆判得正確，scope 也涵蓋到了。**
沒有任何證據指出 classifier 哪裡該修。

```text
Q3 在「找不到 classifier 缺陷」的情況下，是否仍要為了滿足規則而修改它？
   (a) 是——維持「同一 implementation 不得重驗」的紀律，先做實質改動再驗
   (b) 否——改判為「舊 holdout 的取樣未涵蓋 gate 的標的情境」，
       以**新的、未看過且刻意涵蓋 instance／rule 兩型**的 matching holdout 重驗現行版本
   ⚠️ 走 (b) 等於承認舊反證是**取樣不足**而非**實作缺陷**——
      這是對既有裁決的改判，只有你能做。
   ⚠️ 無論走哪一支，**新 holdout 必須未看過**；本檔 4 筆與原 50 筆都已燒毀。
```
