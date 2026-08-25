# `C4b-gated-resolver-validation` protocol（**FROZEN，執行前凍結**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 身分：**新 implementation 的 acceptance evidence**——**不是**重跑舊 C4b
> ⚠️ 舊 C4b 的歷史**不動、不回填**：`C4a CONFIRMED／C4b NOT PASSED／gate CLOSED` 維持原樣。
> 即使本輪全綠，也**不得**把舊 C4b 改寫成 PASS。

## 0. 這一輪要證什麼

四個 slice 證的是「新 control flow **可以**成立」；本輪要證：

> **真 brain 在新 contract 下會穩定走完 delegation chain，
> 並且答案真的用到最後那個面向的 execution grounding。**

## 1. 隔離邊界（**不碰 production**）

```text
delegates 資料   只寫**測試庫**（aichatbot_test）的兩列，測試結束**還原原值**
                 bill_diagnosis  → billing_anomaly
                 billing_anomaly → contract_closeout
                 ⚠️ 這兩條**不是新發明的 ownership**——是先前 authoritative persona contract
                    與 runtime delegation 已實測暴露的 edge（research.md §F-2／§11.4）
gate            `PREENTRY_ROUTABILITY_GATE` **只在測試行程內**設為 true；
                `.env`／兩份 compose **一律不動**（production 仍 false）
jgb2            `USE_MOCK_JGB_API=true`；contract_closeout 的 grounding 走 `jgb_contracts`
                （**未遷移端點**，仍由方法級 mock 提供決定性資料）
掃描            **不得**把所有 Face 的自然語言規則批次轉成 DB delegates——那是 migration，範圍另計
```

## 2. 凍結參數

```text
model／temp／max_tokens   沿 production：brain gpt-4o／0.4／400／json_object；
                         factual 合成 gpt-4o-mini／0.2／800
query（逐字）             幫我查點退帳單金額
turn 2（逐字）            678   ← 方法級 mock 的合約 id（決定性）
repetitions              3（每次全新 session）
retry                    僅事前列舉的 infra 類 ≤2；semantic 結果**不 retry**
上限                     target_scope_calls ≤ 30 ／ all_provider_calls ≤ 60（皆委派前檢查）
```

⚠️ 名目每 run 約 5 次目標呼叫（resolver 3 ＋ 進場後 brain 1 ＋ 合成 1）。

## 3. 必須同時成立的五項（**只看最終答案不算過**）

```text
① chain     bill_diagnosis  → switch ＋ delegate=billing_anomaly
            billing_anomaly → switch ＋ delegate=contract_closeout
            contract_closeout → stay
② session   只 commit contract_closeout；form_sessions 該 session 僅此一列
③ grounding contract_closeout 的 execution 真的跑到（jgb_contracts）
④ answer    最終回答使用該 execution 的 grounding（沿用 C4b v2 尺：值字面／別筆字面／泛用標記）
⑤ verdict   **每一跳的 reason 都必須是 `responsibility_contract`**
```

### ⚠️ ⑤ 是本輪最重要的防假綠

resolver 對「規則取不到／brain 失敗／例外」一律 fail-open(stay)——那是為了維持
production 相容，但**fail-open 不得算新路徑通過**：

```text
stay_source = model_verdict   → 可計入 PASS
stay_source = fail_open       → 該 run **NOT PASS**（根本沒驗到新 authority path）
```

evidence **MUST** 逐跳記錄 `reason`。

## 4. 事前鎖死的裁決表

| 結果 | 裁決 |
|---|---|
| 3/3 五項全成立 | `GATED_RESOLVER_VALIDATED`——**僅表示這條 vertical slice 在此 predeclared case 上成立** |
| 部分成立 | 逐項記錄哪一項斷在哪；**NOT VALIDATED**，不得回填舊 C4b |
| 任一跳 `fail_open` | 該 run NOT PASS（見 §3⑤） |
| infra 失敗耗盡 retry | 該 run INCONCLUSIVE |

## 5. claim ceiling

```text
✅ 可說：在此 predeclared case 上，真 brain 依契約走完 chain，且答案用到最後面向的 grounding
❌ 不可說：diag-01 已修好／routing 已正確／可以開 production gate／
          舊 C4b 可以改判／其他 Face 也會如此
```

## 6. 通過之後**才**談的下一階段（本輪不做）

```text
1 delegates production migration 設計   2 source-by-source audit
3 gate rollout strategy                4 cost／latency measurement
5 production enablement
```

⚠️ **不得**從「diag-01 修好了」直接跳到「全域開 gate」——
一開就是 normal classification path 每候選多一次 brain evaluation，
成本、延遲、fail-open 比例都要先有數。
