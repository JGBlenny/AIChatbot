# B″ protocol（**FROZEN，執行前凍結**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 身分：**runtime-delegated candidate expansion**
> ⚠️ B／B′ 的紀錄**不動、不回填、不重新解釋**。

## 0. 為何新增這個候選

B′ 在 authoritative in-session evaluation 中**明確**把本 query delegate 至
`contract_closeout`（「點退帳單屬**合約退租收尾**範疇…轉由合約領域接手」，
`evidence/r1b-prime-execution.json` rep1／rep3）。
故依 §1 的 closure 規則納入該 Face 為候選——**不是**研究者手選。

⚠️ 若事後把候選集截斷在前兩個 Face，`RESPONSIBILITY_GAP_CONFIRMED` 會變成
**由測試邊界製造**，而不是 production responsibility graph 的事實。

## 1. candidate set 的定義（**事前定死，避免第三次臨場裁範圍**）

> **對本 query 的 candidate set，不以研究者手選 Face 為界；
> 以 runtime authoritative scope evaluation 明確產生的 Face delegation closure 為界。**

```text
初始已觀測候選   bill_diagnosis
runtime 明確 delegate → billing_anomaly → contract_closeout
                     → 若又明確指名另一 enabled Face，繼續納入

終止條件（任一）
A. 某 Face **stable stay**（接受責任）
B. delegation 回到已測 Face → responsibility delegation **cycle**
C. Face switch 但**沒有可辨識的新 owner**
D. 指向不存在／disabled／非 Face 的 destination
```

⚠️ 這是 **descriptive discovery rule**，**不是**替 governance 決定誰「應該」負責。

## 2. 受測 Face 的凍結事實（執行前實查，2026-08-25）

```text
key            contract_closeout（enabled=True）
persona        pm_contract_closeout
topic_scope    退租收尾
grounding      select=api／endpoint=jgb_contracts；**未宣告** enabled_gate／prefill_api
               → 直達進場等價性成立（同 bill_diagnosis／billing_anomaly）
rules digest   363ed0d0da3ca23c（919 字）
scope 條款     「是退租/解約/收尾相關、或在回答你剛問的問題 → stay。
                 明顯是另一領域的完整新問題 → switch。不確定 → stay 並澄清。」
in-session ctx key=退租收尾  digest=16b107f0aaf4eb5f（1569 字）
```

## 3. 凍結參數

```text
model gpt-4o ／ temperature 0.4 ／ max_tokens 400 ／ response_format json_object
query（逐字）幫我查點退帳單金額        query sha1(16) c0d220cc3f1d47cb
candidate     contract_closeout
state         全新 session（每次 repetition 一條，production 自建）
repetitions   3
retry         僅事前列舉的 infra 類 ≤2；semantic 結果不 retry
上限          target_scope_calls ≤ 8 ／ all_provider_calls ≤ 20（皆委派前檢查）
```

**執行方式**：全程 production path——`trigger_facet_key=contract_closeout` 直達建 session，
context 組裝與 scope 判定皆真 production；**不人工餵 context**；
`PREENTRY_ROUTABILITY_GATE` 維持 false。

**成立條件**：三次的 system message 皆須含 in-session（退租收尾）脈絡；
否則 B″ 無效，須先查明原因。

⚠️ switch 後落回分類路由的呼叫（預期為 `bill_diagnosis`）以 rules digest 判為 **uncounted**。

## 4. 事前鎖死的裁決表

| B″ 三次結果 | 裁決 |
|---|---|
| 3 stay | **responsibility owner exists** → `RESPONSIBILITY_GAP_CONFIRMED` **不成立**（見 §5） |
| 3 switch | 依其 runtime 輸出再分流（見 §6），**不得**直接宣告 gap |
| 混合（2/1 或 1/2） | `INSUFFICIENT_EVIDENCE` |

## 5. 若 3 stay：得到的是**另一個形狀**，不得硬塞既有分類

```text
responsibility owner exists:   contract_closeout accepts query
observed routing path:         retrieval／classification → bill_diagnosis
                               → scope rejects → reroute → bill_diagnosis again
⇒ 問題轉為：**responsibility owner exists but is unreachable /
   not proposed by current entry-routing authority**
```

⚠️ 這**不是** responsibility gap，也**不得**硬塞 `IMPLEMENTATION_DEFECT`。
先形成新的 evidence-backed mechanism，再看 R5 是否需要另一分類。

## 6. 若 3 switch：仍**不能**立刻宣告 gap，依 runtime 輸出續分流

```text
明確指向第四個 enabled Face    → 依 §1 closure 繼續納入並續測
回指 bill_diagnosis／billing_anomaly → responsibility delegation **cycle**
拒絕但**不指名**任何可承接 Face  → 才接近 **no-owner terminal**
輸出混合／無法辨識              → INSUFFICIENT_EVIDENCE
```

## 7. R5 第五類的**操作化**定義（取代原較模糊的措辭）

> `RESPONSIBILITY_GAP_CONFIRMED`
>
> 在本 query 的 **runtime delegation closure 已被追至終點**，
> 且所有被 authoritative responsibility evaluation **實際提出為候選 owner** 的 Face，
> 在其 **production-equivalent in-session context** 下均不接受責任，
> 並且**不存在尚未檢驗的新 delegation target**。

⚠️ 這不是改結論救測試，而是在第一次發現 candidate set **不是封閉兩元素集合**時，
把原本模糊的「任何候選 Face」操作化。原三條護欄不變。

## 8. 目前狀態（B″ 執行前）

```text
bill_diagnosis            stable reject（6/6）
billing_anomaly           stable reject（3/3，in-session）
execution alternatives    falsified（四項）
reroute residue           falsified
runtime delegation closure **not exhausted** → contract_closeout 未測
outcome                   **INSUFFICIENT_EVIDENCE**
```
