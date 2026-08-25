# `C4b-gated-resolver-validation` **v2** protocol（**FROZEN，執行前凍結**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 前身：v1（`c4b-gated-resolver-validation-protocol-frozen.md`）＋其結果
> `c4b-gated-resolver-run1-result.md` — **NOT_VALIDATED，永久保留、不回填**
> ⚠️ 舊 C4b 歷史同樣不動：`C4a CONFIRMED／C4b NOT PASSED／gate CLOSED`。

## 0. 為何 v2 不是「為了變綠改尺」

v1 把 failure 定位得很窄，且 omission 與 contract 表達之間有直接缺口：

```text
resolver control flow   正常          fixture／parsing   正常
allowed delegate        正常          prompt whitelist   正常
model scope decision    switch 3/3    missing piece      delegate_facet_key 3/3 omitted

responsibility rule 講的是   「帳單異常」
machine target 給的是        billing_anomaly
prompt 只說 billing_anomaly 是合法 target，**沒說什麼語義情況對應它**
```

⇒ v2 修的是 **contract representation**，不是量尺，也不是 resolver。

## 1. 修法與其三條界線

```yaml
delegates:
  - target: billing_anomaly
    when: 帳單金額組成/看不到帳單
```

```text
界線一  `when` 的身分＝**responsibility delegation semantics**，供 evaluator 判斷
        何時可選該白名單 target；**不是** resolver 自己做 keyword routing 的條件。
        程式不得出現 `if "帳單金額" in query: delegate_to(...)`——authority 仍在 evaluator。
界線二  白名單約束不鬆：模型輸出的 delegate_facet_key 必須存在於
        `responsibility.delegates[].target`，否則丟棄。`when` 只增加理解，
        **不讓模型獲得自創 destination 的能力**（具名 unit 鎖住：拿 when 當 key 會被丟棄）。
界線三  先凍結再重跑；v1 的 NOT_VALIDATED **永久保留**，本輪另存為 v2。
```

## 2. 兩條 edge 一次補齊（**避免第一跳修好、第二跳同因再紅**）

`when` **逐字取自現有 authoritative persona responsibility wording**，不自行發明 ownership：

```yaml
bill_diagnosis:
  delegates:
    - target: billing_anomaly
      when: 帳單金額組成/看不到帳單        # 規則原文：「帳單金額組成/看不到帳單（帳單異常）… → switch」

billing_anomaly:
  delegates:
    - target: contract_closeout
      when: 封存/點退帳單處理              # 規則原文：「封存/點退帳單處理、其他領域完整新問題 → switch」
```

⇒ 本輪測的是「**structured representation 能否忠實承載既有 responsibility contract**」，
**不是**重新分配責任。

## 3. 隔離與參數（同 v1，未變更）

```text
delegates 只寫測試庫兩列，結束**還原**；PREENTRY_ROUTABILITY_GATE 只在測試行程內開
USE_MOCK_JGB_API=true；brain gpt-4o/0.4/400；factual 合成 gpt-4o-mini/0.2/800
query「幫我查點退帳單金額」／turn2「678」／3 runs／semantic 不 retry
上限 target ≤30、all_provider ≤60（委派前檢查）
```

## 4. evidence 必須逐跳保留

```text
hop N: candidate ／ scope ／ delegate ／ reason_source ／ **fail_open: true|false**
commit: 只有 contract_closeout 建立 session
grounding: executed
final answer: uses grounding
```

⚠️ **任一跳 `fail_open=true` → 不得算 vertical slice validated。**

## 5. 結果解讀（**事前定死**）

| 觀測 | 裁決 |
|---|---|
| 3/3 完整走完 chain → stay → grounding → grounded answer | **structured responsibility delegation vertical slice = VALIDATED** |
| 第一跳好了、第二跳不 delegate | contract representation 仍不足，**繼續定位；不改 resolver** |
| 仍停在第一跳 `switch + no delegate` | `when` 已排除「key↔語義對應不足」→ 問題升級為 **evaluator／output-contract 問題** |
| 結果不穩定 | 記為 **instability**，**不得**以多數決宣稱 validated |

⚠️ VALIDATED **不等於**：整個 routing architecture 已驗證／production gate 可以打開。

## 6. 通過之後才談（本輪不做）

```text
delegates production migration 設計 ／ source-by-source audit ／ gate rollout strategy ／
cost・latency measurement ／ production enablement
```
