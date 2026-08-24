# B′ protocol（**FROZEN，執行前凍結**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 身分：**production-equivalent diagnostic variant**——不是「把 B 再跑一次」
> 前身：R1 Goal B（`research.md` §8.2／§8.3，evidence `r1-first-execution.json`）
> ⚠️ **原 B 的紀錄不動、不回填、不重新解釋**：其歷史永久為
> `switch／stay／switch ＝ rejection reproduced, stability not established,
> confounded by non-in-session system context`。

## 0. B′ 要消掉的 confounder

實測（§8.3）顯示 `_preentry_routable` 對 `billing_anomaly` 取到的是 **base** system context
（digest `d1f88c90…`，與 `bill_diagnosis` 相同），而 in-session 會取到「帳單異常」的
領域脈絡（digest `2158ebdc…`）。B 的 2/3 因此同時混了 LLM 不穩定性**與**錯的 evaluation context。

B′ 只回答一句反事實：

> **`billing_anomaly` 在它自己真正的 in-session responsibility context 下，
> 到底會不會接受這句 query？**

## 1. 執行方式：**全程 production path**，不人工餵 context

```text
❌ 不得   人工把 context key 改成「帳單異常」再呼叫 _preentry_routable
          （那只會造出另一個測試專用語境）
✅ 必須   讓 billing_anomaly **自己建立 session**，由 production 組裝 in-session context：
          POST /api/v1/message  message=<query>  trigger_facet_key=billing_anomaly  stream=false
          → _seed_repair_facet → _conversational_respond → engine.prepare
          → get_system_context(db, _domain_key(config)) ＝「帳單異常」
          → production conversational_step
```

⚠️ **routing 怎麼進去不是本輪要驗的**：用已知的 direct entry 把它放進 `billing_anomaly` 即可；
但**進去之後**的 context 組裝與 scope 判定必須全部是真 production path。

⚠️ **PREENTRY_ROUTABILITY_GATE 維持 false**（B′ 不經該 seam）。

## 2. 凍結參數（與 R1 同源，未變更）

```text
model gpt-4o ／ temperature 0.4 ／ max_tokens 400 ／ response_format json_object
query（逐字）幫我查點退帳單金額        query sha1(16) c0d220cc3f1d47cb
Face          billing_anomaly（persona pm_billing_anomaly）
repetitions   3（每次全新 session）
retry         僅事前列舉的 infra 類 ≤2；semantic 結果不 retry
上限          target_scope_calls ≤ 8 ／ all_provider_calls ≤ 20（皆在委派前檢查）
```

⚠️ **只採計 `billing_anomaly` 的那次 brain 呼叫**：若 B′ 判 switch，引擎會關會話、落回檢索，
分類路由可能改進 `bill_diagnosis`（§8.1 已知），該次呼叫**不計入 B′ 結果**，
以 rules digest 區分（`aefa054899cdd7e6` ＝ billing_anomaly）。

## 3. 逐次記錄七欄（同 R1）

```text
face_identity ／ rules_digest ／ system_context_digest（含實際 key）／
state ／ query ／ history ／ scope_result（**正規化前**的原始值）
```

**成立條件**：三次的 `system_context_digest` 必須為 in-session 的 `2158ebdc2d8fe7e6`；
若仍是 base（`d1f88c90…`），代表 confounder 未被消掉，B′ **無效**，須先查明原因再談結果。

## 4. 事前鎖死的裁決表（**四格填滿，不留空格**）

| B′ 三次結果 | 裁決 |
|---|---|
| 3 switch | **stable in-session rejection** |
| 2 switch／1 stay | rejection reproduced, unstable → `INSUFFICIENT_EVIDENCE` |
| 1 switch／2 stay | acceptance reproduced, unstable → `INSUFFICIENT_EVIDENCE` |
| 0 switch／3 stay | **stable in-session acceptance** → `RESPONSIBILITY_GAP` hypothesis **refuted** |

只有**第一格**，搭配已成立的：

```text
bill_diagnosis            6/6 switch（stable）
reroute residue           FALSIFIED
context truncation        FALSIFIED
identity／state mismatch   FALSIFIED
producer／consumer mismatch FALSIFIED
```

才足以正式套用：

> **RESPONSIBILITY_GAP_CONFIRMED** → 立即 **STOP** → **不選 owner**
> → 升級至 Responsibility Governance Decision Record（新 artifact，不改對方狀態）

任何混合結果一律維持 **`INSUFFICIENT_EVIDENCE`**。

## 5. claim ceiling

```text
✅ 可說：在這一句 predeclared query 上，billing_anomaly 的 in-session scope 判定為 X（穩定度見上表）
❌ 不可說：它對「這類問題」都會 X／誰應該接手／pre-entry gate 該不該開／root cause 已定
```
