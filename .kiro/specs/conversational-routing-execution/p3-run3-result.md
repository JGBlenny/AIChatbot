# P3 第 3 次付費執行：**A 通過（3/3）** — mini 適用於目前的 responsibility-routing 架構

> 2026-08-26｜brain＝**gpt-4o-mini**｜brain 輪 **24**／全部 **29**（上限 30／60）
> 證據：`evidence/p3-run3-strict-schema.json`＋`p3-run3-stdout.log`
> 變更：strict `json_schema`（僅 `conversational_step_result` 這一個 seam）

## 一、A：`GATED_RESOLVER_VALIDATED`，五項判準同時成立、3/3

```text
rep1／rep2／rep3 完全一致：
  bill_diagnosis  --switch--> billing_anomaly     delegate_source = model_delegate
  billing_anomaly --switch--> contract_closeout   delegate_source = model_delegate
  contract_closeout --stay-->                     reason = responsibility_contract
  committed = contract_closeout｜session rows = ['contract_closeout']（唯一一列）
  v6 ruler = PASS（逐句 matched span 見證據）
  ⑤ fail_open = **false**：三跳的 reason 全是 responsibility_contract
```

實際答句（rep1，節錄）：

> 合約「信義區套房A」目前狀態為「已點交（執行中）」。目前尚不可點退，因為合約不在可點退的階段；
> 合約到期日為 **2026/12/31**，需到期前 30 天（**2026/12/01**）起才可發送點退。

## 二、兩個卡點各自的結局

```text
A2  action=ask 卻沒有 next_question   前：**3/3 踩到**   後：**0/24 輪**（全部 24 次 brain 呼叫零拒絕）
    ⇒ strict schema 對症，且是**唯一**變數（本輪只改這一件事）
A1  billing_anomaly 判 stay           前：1/3           後：**0/3**
    ⇒ 上一輪的 1/3 很可能是 A2 汙染下的樣本，而非模型語義不穩。
    ⚠️ 但 3/3 仍是**小樣本**；不得就此宣稱「mini 的 responsibility 判定已穩定」。
```

## 三、必須誠實標註的三件事

```text
① **singleton delegation 本輪未被觸發**：三跳的 delegate 全由模型自己填（model_delegate）。
   它現在是**保險**不是主力——其正確性由 unit（9 條）保證，**不是**由本輪證明。
   ⚠️ 不得因為本輪沒用到就移除：strict schema 保證鍵存在，**不保證值非空**。
② **B 仍 INCONCLUSIVE**：本輪 24 輪**零拒絕**，salvage 適用情境（payload 被擋 ∧ scope=switch）
   依然未出現。`FACET_SCOPE_SALVAGE` 的真 brain 因果驗證**尚未建立**，
   該分支由 unit `test_step_contract_layers_req.py`（16 條）覆蓋。
   ⚠️ strict schema 上線後，這個情境在 production 只會更罕見——B 的取證應改用
      「捕捉真模型 payload 後決定性重放」，並標明為 replay。
③ 本輪未動 persona wording、未動 v6 尺、未動 fixture、未回填任何舊 evidence。
```

## 四、因此可以正式宣稱的一句話

> **mini 適用於目前的 responsibility-routing 架構：LLM 負責 applicability 語義，
> 輸出形狀由 API strict schema 強制，singleton delegation 由 machine-readable contract
> 決定性解析。** 三次執行、五項判準同時成立、零 fail-open。

射程限定：`bill_diagnosis → billing_anomaly → contract_closeout` 這一條 vertical slice、
b2b／property_manager、JGBMockTransport 的 fixture 資料。
**不含**：真 API、權限圈定、真實資料分佈、其他 18 個面向。
