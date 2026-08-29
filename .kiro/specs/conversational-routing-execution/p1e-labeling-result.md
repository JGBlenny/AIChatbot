# P1e-1 盲標結果（2026-08-29）——⚠️ **正對照失敗，consensus general 不得直接寫入**

## 執行完整性

```text
兩位標註者各 839/839 筆｜幻覺 id 0｜漏標 0
工具使用：兩位皆**只** Read 自己的語料檔（2–3 次為分頁）
          ⛔ 無 grep、無 DB、無程式碼、無搜尋 —— 隔離未被破壞
正對照：34 筆 deterministic **未**誤入盲標語料（應為 0，實為 0）✅
逐筆一致：818/839 = **97.5%**
```

## 合議結果

```text
合議 instance   76
合議 general   742
保持 UNKNOWN    21   （分歧或含 undecidable）
＋ P1b deterministic instance 34
─────────────────────────────
instance 110｜general 742｜unknown 21   合計 873
```

表面上 coverage 從 3.9% 跳到 **97.6%**。⚠️ **但這個數字不可直接採用。**

## ⚠️ 正對照失敗：3509

```text
知識 3509「訂閱扣款失敗導致功能異常」
  盲標 A = general    盲標 B = general    ⇒ 合議 general
  但本輪 runtime smoke **已實證**它必須讀該帳號的 /roles/{role_id}/subscription
  （committed subscription_diag → _diagnose_subscription_payment，真 API 成功）
⇒ **合議把一筆已證實的 instance 判成 general。**
```

## 這不是單點失誤，分歧清單顯示是**系統性**的

```text
A=general／B=instance 的 10 筆，全是**診斷型**問句：
  3873「我想改合約 內容要修改」    3874「合約打錯了 填錯要改」
  3875「簽出去的合約還能改嗎」      3884「租客說沒收到合約 找不到約」
  3936「租客說看不到帳單 找不到」    4562「想改合約租期 租金要調整」
  3207「租金少繳不足補繳」          3257「管理費繳納」…
A=general／B=undecidable 另有 7 筆同型：
  3883「租客簽不了約 一直簽不成」    3933「租客繳不了費 一直失敗」
  3978「租客登入後什麼都看不到 畫面空空的」…
反向（A=instance／B=general）只有 **1** 筆 ⇒ A 明顯偏向 general。
```

## 方法層的結論（**比數字重要**）

> **從答案文字盲標，量到的是「目前的答案寫得多通用」，
> ⛔ 不是「正確完成這個問題需不需要個別資料」。**

3509 的答案寫成「到訂閱方案頁確認方案狀態與付款方式」——**讀起來就是通用指引**。
只有知道 `diagnose_subscription` 引擎存在，才知道它**可以**用該帳號的資料回答。
⇒ 標註者看不到那個事實（那正是 withheld 清單的一部分），所以判 general 是**合理的**——
  問題不在標註者，在**題目給的證據不足以回答被問的問題**。

## ⚠️ 兩種錯誤的代價**不對稱**

```text
誤判為 instance  → 多做一次查詢，答案仍正確，**降級優雅**
誤判為 general   → gate 會**靜默抑制**本該進場的 Face
                   ——正是本輪剛修好的 3505／3506 那個病灶
```

## 建議處置（⛔ 提案，未執行，零 DB 寫入）

```text
【可用】110 筆 instance（34 deterministic ＋ 76 consensus）
        誤判成本低且方向安全 ⇒ 可作為 population proposal
        ⚠️ provenance 分開記：source=deterministic／source=blind_label_consensus

【不可直接用】742 筆 consensus general
        正對照已證明此類存在 false general，且代價不對稱
        ⇒ 需要**換一個問法**的第二輪（例如：「這一題若能讀到使用者自己的資料，
          會不會答得更正確？」），或維持 UNKNOWN 直到有更強證據

【維持 UNKNOWN】21 筆分歧
```

## 預先登記的 claim ceiling（協議凍結時寫定，此處對帳）

```text
✅ 可說：兩位隔離標註者對 818/839 筆達成一致（97.5%）
⛔ 不得說：applicability 標註「正確率」——本批**沒有** ground truth
   ⚠️ 而我們唯一擁有 ground truth 的那一筆（3509），合議**判錯了**
⛔ 不得說：任何 production 分布
```

## 用途分家（協議已凍結，此處重申）

```text
本批 839 一旦用於回填 → 即成 training/configuration corpus
⛔ 之後不得從中抽樣宣稱「gate 對 unseen 的準確率」
未來 authorization holdout 必須是完全 unseen 的另一批，
且在 implementation ＋ population freeze **之後**才建立。
```
