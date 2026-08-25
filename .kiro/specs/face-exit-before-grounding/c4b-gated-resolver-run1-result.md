# `C4b-gated-resolver-validation` 第一次執行：**NOT_VALIDATED**

> 2026-08-25｜協議 `c4b-gated-resolver-validation-protocol-frozen.md`（`4508286`，先於執行 commit）
> evidence：`evidence/c4b-gated-resolver-run1.json` ＋ `…-stdout.log`
> 預算：`target_scope_calls = 3`（上限 30）／`all_provider_calls = 15`（上限 60）／retry 0
> ⚠️ 舊 C4b 歷史**未回填**：`C4a CONFIRMED／C4b NOT PASSED／gate CLOSED` 原樣。

## 0. 結果

```text
verdict = NOT_VALIDATED
3/3 runs 都停在**第一跳**：
  bill_diagnosis → verdict=switch、**delegate_to=None** → stop_reason=switch_without_delegate
  → 不 commit 任何面向 → 落回既有 fallback（通用兜底文案）
  → session rows = **0**（新流程確實沒建立 transient session，②的副作用面成立）
```

## 1. 五項逐項

```text
① chain      ✗ 只有一跳（預期三跳）
② session    ✓ 沒有 transient session；✗ 但也沒有 commit contract_closeout
③ grounding  ✗ 未執行（沒有面向被 commit）
④ answer     ✗ value_not_used（回的是兜底文案）
⑤ verdict    ✓ **reason = responsibility_contract**——是**真的模型判定**，不是 fail-open
```

⚠️ ⑤ 成立很重要：這次紅**不是**因為新機制故障後 fail-open 混過去，
而是真的問到了模型、模型也真的判了 switch——**只是沒說要轉交給誰**。

## 2. 根因（零成本診斷，未再花錢）

逐項排除：

```text
✓ fixture 有寫進去          比對到 knowledge_base id 4252
✓ 契約有被解析              allowed_delegates == ('billing_anomaly',)
✓ prompt 有帶白名單          system message 確含「【轉交對象 delegate_facet_key…】…billing_anomaly」
✗ 模型沒有填 delegate_facet_key
```

**原因：契約給的是英文面向鍵，規則講的是中文分類名，兩者之間沒有對應。**

```text
規則（authoritative wording）  「帳單金額組成/看不到帳單（**帳單異常**）… → scope="switch"」
白名單（contract）             billing_anomaly
```

模型要自行把「帳單異常」對到 `billing_anomaly` 才填得出來；
而 prompt 又明寫「無法判定就省略此欄」——它就省略了。

⇒ **這是 delegation contract 的表達缺口，不是 resolver control flow 的缺陷。**
resolver 的三個分支（stay／delegate／無 delegate 落回 fallback）都照設計運作。

## 3. 提請裁示的修法（**未實作、未再執行**）

在 slice 2 已宣告的 delegate 結構內補一個欄位（業主原草案的
`# responsibility wording / condition` 正是此欄），並在 prompt 內一併渲染：

```yaml
responsibility:
  delegates:
    - target: billing_anomaly
      when: 帳單金額組成／看不到帳單
```

渲染後：`本領域責任契約允許轉交的對象：billing_anomaly（帳單金額組成／看不到帳單）`

```text
影響面   只動 prompt 渲染與白名單解析；resolver control flow 不變
成本     零（未帶 delegates 時 prompt 仍逐字不變的回歸鎖維持）
風險     若仍不填，代表問題不在詞彙對應，而在模型不願指名——那是另一種發現
```

⚠️ 依協議「semantic 結果不 retry」，**本輪到此為止**；
修法與再跑一次都需要業主授權（再跑一次約 target 15 次呼叫）。

## 4. 這次已經確定的事（不必再驗）

```text
✅ gate 在測試行程內確實生效（resolver 被呼叫、chain 被記錄）
✅ delegates fixture 的寫入・解析・還原三段都可用
✅ 「不 commit 就不建 session」的副作用面成立（0 列）
✅ 判定來源可區分（reason 欄位讓 fail-open 無法冒充通過）
```
