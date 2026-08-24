# 5.5：C4a 執行與判型結果

> 2026-08-24｜語言 zh-TW｜依 `design.md` §「C4a 失敗判型」的 **frozen (a)/(b)/(c) 流程**判讀
> 凍結輸入：案例 `451c0d2`｜尺 `1dbf94c`｜執行證據 `e927769`（5.3）、`57269f4`（5.4）
> ⚠️ **本任務不修任何東西**（見文末「本輪未做」）。

## 判定

```text
四案皆抵達 frozen 流程圖的 **PASS 節點** → **C4a PASS**
(a) 鏈路未跑通        0/4
(b) mock 契約不保真   0/4
(c) grounding insufficiency  0/4
```

**⇒ 不觸發 Req.3.4 降級**（降級由 (a) 或 (c) 觸發；本輪兩者皆為 0）。

⚠️ **未新增第四種結果**：`PASS` 本來就是 frozen 流程圖的終點節點之一，
非為容納實測而新設；三種失敗型的定義亦一字未改。

---

## 判型依據＝**execution evidence**，不是測試總數

⚠️ `10 passed` 只是驗收摘要，**不是**判型依據。逐案的判型事實如下
（皆取自 5.3／5.4 的真 DB 執行，非從最終文字推得）：

| 案例 | ①API 呼叫且收斂單筆 | ②送達性 | ③充分性 | ④OB-3 fixture identity | ⑤secondary dispatch |
|---|---|---|---|---|---|
| `c4a-diag-01` | ✅ | ✅ `7,500` | ✅ `{amount_due}` | ✅ `{900003}` | **> 0**（期望 true） |
| `c4a-diag-02` | ✅ | ✅ `2026年8月租金` | ✅ `{cancel_determination}` | ✅ `{900001}` | **> 0**（期望 true） |
| `c4a-anom-01` | ✅ | ✅ **兩個來源值**（OB-1） | ✅ `{billing_period}` | ✅ `{900002}` | **= 0**（期望 false） |
| `c4a-anom-02` | ✅ | ✅ `待對帳` | ✅ `{bill_status}` | ✅ `{900003}` | **= 0**（期望 false） |

### 流程圖逐節點對照

```text
A「API 有被呼叫且收斂到單筆？」        → 是（四案的 transport 請求皆有紀錄且收斂單筆）
A「回傳形狀非預期？」（→(b)）          → 否（mock 依 4.5 契約回應，無形狀例外）
B「grounding_must_contain 全部命中？」 → 是（含 anom-01 的兩個來源值）
C「required_grounding_facts 全部存在？」→ 是（四案的 frozen required set 皆 ⊆ observed）
→ **PASS**
```

## 對照 invariant（本輪最重要的結構證據）

```text
diagnosis frozen cases   secondary dispatch > 0
anomaly   frozen cases   secondary dispatch = 0
```

⚠️ 該差異由 `execute_api_call` 的**派發次數**證明，**不是**由「`bill_detail` 有沒有被呼叫」推得——
後者在兩個面向**都成立**（anomaly 的 adapter 數字分支同樣會打一次 detail）。
> ⇒ 可據此宣稱：**chain closure 不依賴 `secondary_call` 才能成立。**

## 量尺會咬的反證（皆為 PASS 的必要背景）

```text
充分性反證   移除該案 required key → 紅（diagnosis 與 anomaly 各一）
OB-3 反證    期望綁到另一筆 fixture → 不相符（constant-record falsifier 有效）
OB-2 反證    抽掉 start／end 之一 → 紅；且**前置斷言證明** label 仍在、
             observer 仍觀測到 `billing_period` → 紅來自 **delivery**，非 observation 失效
```

⚠️ 若無這三組反證，「四案全綠」無法排除「尺根本不會紅」。

---

## ⚠️ 本次 PASS 的射程（**寫窄，不得升格**）

```text
✅ 只證明：4 個 protocol-frozen C4a cases
          × scope = numeric_bill_ref
          × execution_face ∈ {bill_diagnosis, billing_anomaly}
          的執行鏈閉環

❌ 非數字 bill_ref 分支已證（`get_contracts` 未遷移）
❌ 一般自然語言問法已穩健（本組為 protocol-frozen design/acceptance cohort，
   **非** blind／generalization evidence）
❌ routing ownership 正確（case inclusion 明令不得作此證據）
❌ 整個 adapter 已 closure
❌ 最終答案能力已證（C4a 只證 grounding 送達與充分；答案能力屬 C4b／6.3）
```

## 併同記錄的既有限制（非本輪引入）

```text
· detail 端點每次收斂被呼叫兩次（adapter 數字分支 ＋ 面向 secondary_call）——既有行為
· fixture 未建模 `details`／`pay_info`／`cvs_info`；`role_id` 不做 owner 圈定；
  `user_id` 過濾未實作（4.5 已列 known-unmodelled）
· 被 admission 排除的三筆維持 `NOT_ADMITTED_TO_CURRENT_C4A_COHORT`
  （兩筆屬 fixture 缺口、一筆屬 External 契約能力缺口）
```

## 本輪**未**做（5.5 不准修東西）

```text
❌ 未修改 4.6／formatter／fixture／case／required facts／harness semantics
❌ 未重新解釋 (a)/(b)/(c)，未新增第四種結果
❌ 未因判型結果調整任何斷言
❌ 未執行 6.x；4.6 仍為 **implemented ✅／verified ✅／released ❌**（6.3 人工放行前禁止上線）
```

## 待獨立驗證（🔍V）

```text
本任務標 🔍V：結論直接決定整個 spec 的優先序走向（是否觸發 R3.4 降級）。
→ fresh verifier 待派；其結果補記於此。
```
