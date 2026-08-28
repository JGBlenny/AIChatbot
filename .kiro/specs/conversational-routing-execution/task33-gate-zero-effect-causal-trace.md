# 「block 11 筆卻抑制 0 筆」的機轉——讀取級 causal trace

- 日期：2026-08-28｜依據：裁定 002 步驟 2 後的追因指示
- 範圍：**只歸因，不改任何一層**（classifier／wiring／scope 皆未動）
- 資料：`routing-disambiguation/evidence/task-6-holdout-measurement.json` 的 50 筆
  ＋ **以今天的程式重算**

## 結論（先講）

> **第一個斷點在 consumer 的「抑制集合」`gate_applies_to = C ∧ D`，
> 不是 classifier，也不是 wiring defect。11 筆 block 從來沒有機會作用。**

## 四個必答問題

```text
1 block verdict 有沒有真的回到 chat.py 的 consumer？
  → **有**。`_instance_hint_suppressed` 讀 `decision.verdict`，非 block 直接 return False。
2 consumer 有沒有因此 suppress candidate？
  → **只在 gate_applies_to(cfg) 為真時**：
     C = grounding_scope.requires_instance_reference is True
     D = key ∈ LEVEL_A_INSTANCE_GATE_SCOPE
3 被 suppress 的 candidate，是否就是後面實際 commit 的那個？
  → **11 筆 block 一筆都沒被 suppress**（見下方逐筆）。
4 若被 suppress 卻仍進 Face，Face 從哪個第二入口重新提名？
  → **N/A**——沒有任何 candidate 被 suppress 過，第二入口問題不成立。
```

## 逐筆（11 筆 block 的實際路由）

```text
9 筆 route = single，facet = None      → 本來就不進 Face，**無 Hint 可抑制**
2 筆 route = dialog：
    n=11「已經發給房客的帳單還能改金額嗎」→ 物件操作引導
    n=30「押金退還也需要開一張帳單嗎」    → 退租收尾
  兩者**皆不在** LEVEL_A_INSTANCE_GATE_SCOPE，也**未宣告** requires_instance_reference
  → gate_applies_to = False → 未抑制
```

⚠️ **原 measurement 檔的敘述句與同檔 `all_rows` 對不上**：
它寫「8 筆本來就 single、3 筆落在 scope 外」，逐筆重數是 **9 筆 single、2 筆 scope 外**。
結論方向不變，但**該敘述的數字不可引用**。

## 抑制集合有多小（實測）

```text
LEVEL_A_INSTANCE_GATE_SCOPE = frozenset({"bill_diagnosis"})     ← D，只有一個
測試庫 16 個 Face 中宣告 requires_instance_reference=true 的：
  bill_diagnosis  → true
  其餘 15 個      → 未宣告
⇒ C ∧ D 恆等於 {bill_diagnosis}。gate 對其他任何 Face 都**無權作用**。
```

## 正對照組（證明 wiring 是好的，不是「沒觀察到反例」）

⚠️ 「接線沒問題」是否定結論，必須有一個已知必然被抑制的項目證明它咬得動：

```text
以 holdout n=1（verdict=block）配三種 Face：
  bill_diagnosis ＋ 宣告 C（C∧D 皆成立）  → gate_applies_to=True 、suppressed=**True**  ✅
  contract_closeout ＋ 宣告 C（D 不成立）  → gate_applies_to=False、suppressed=False
  bill_diagnosis 未宣告 C（C 不成立）      → suppressed=False
⇒ block 一旦落在納管 Face 上，consumer **確實**會抑制。
   0/50 不是因為訊號傳不到，而是因為**訊號從沒落在納管的 Face 上**。
```

## 今日重算：classifier 未漂移

```text
以今天的程式重跑 50 筆：block 11 / abstain 32 / allow 7
與 holdout 紀錄**逐筆一致，零不一致**
⇒ 現行 implementation 在行為上也確認就是被反證的那一版（不只 digest 相同）。
```

## 故障歸屬（對照原假設 A／B／C）

```text
B  wiring defect            → **排除**（正對照組證明會抑制）
A  classifier semantic 缺陷 → **尚未證實**：9/11 block 的 query 本來就該 single，
                              gate 的判定與既有行為**一致**，看不出判錯
C  scope / source coverage  → **成立**：block 落到的 2 個 Face 都在納管集合外
＋  abstain coverage        → **成立**：32/50 = 64% 正反證據皆空，
                              那 32 筆的 routing 恆等於 gate OFF
```

⇒ 0/50 的成因是 **coverage**，不是判錯，也不是沒接線。

## 兩個缺口都需要決定，**不是**我可以逕行修的 deterministic bug

```text
① scope coverage：要不要把 requires_instance_reference ／ LEVEL_A_INSTANCE_GATE_SCOPE
   擴到 billing_anomaly／contract_closeout／物件操作引導 等 Face？
   ⚠️ 這正是業主定義的「authority/source coverage defect —— 要定哪些 nomination
      sources 受 instance eligibility 約束」，屬 authority 決定。
   ⚠️ 現行 fail-closed by scope 是**刻意**的（「Level A 的隔離才是結構性的而非靠運氣」），
      擴張等於改變隔離契約。
② abstain coverage：64% 正反證據皆空 → lexical ruleset 對自然說法覆蓋不足。
   要處理就是改 classifier / abstention policy，屬業主指定「才要動 classifier」的那一支。
```

## 原 holdout 的身分（已鎖）

```text
這 50 筆已被看過結果、已用來定位缺陷、接下來還會用來設計修法
⇒ 可當 **diagnostic / regression corpus**
⛔ **不得**再充當修改後版本的最終 authorization holdout
新版流程：freeze implementation → freeze protocol → 取**新的未看過** matching holdout
         → 第一次執行 → 決定 authorized／rejected
⛔ 不得修到這 50 筆有效後，再拿同 50 筆宣布 gate 通過。
```
