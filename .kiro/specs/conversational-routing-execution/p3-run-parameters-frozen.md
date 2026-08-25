# P3 真 brain regression 執行參數（**FROZEN，執行前凍結**）

> 2026-08-26｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 業主 2026-08-26 授權付費執行，並附兩項前提：
> ① **用 mini**，不得再驗已準備淘汰的 gpt-4o 組態；
> ② 不得只重跑舊 v6——必須同時驗 A（pre-commit delegation）與 B（mid-session scope salvage）。

## 〇、與 C4b 舊參數的關係

`c4b-run-parameters-frozen.md`（brain=**gpt-4o**）記錄的是 **2026-08-25 當時**的量測條件，
**一字不改**。本檔是新組態下的新量測，兩者**不可逐案比較**；
舊 C4b v1–v5 evidence **一律不回填**（業主明令）。

## 一、目標組態（＝準備保留／上線的組態）

```text
brain（conversational_step）   PRESALES_SYNTH_MODEL = **gpt-4o-mini**  temp 0.4  max_tokens 400
第 2 輪 factual 合成           PRESALES_ANSWER_MODEL→OPENAI_MODEL = gpt-4o-mini  temp 0.2  max_tokens 800
prompt                        production 原樣，不得為測試改寫
工具                          brain 不掛 kb_search（診斷/交易面向未注入，推導事實非選項）
```

⚠️ 兩輪現在**同一個模型**——這與 C4b 時期（brain 4o／合成 mini）不同，
故 harness 的「target call」計數不得再以 model 名區分，改以 **max_tokens=400** 辨識 brain 輪。

## 二、A：pre-commit delegation regression

```text
鏈      bill_diagnosis --switch--> billing_anomaly --switch--> contract_closeout --stay-->
訊息    第 1 輪「幫我查點退帳單金額」／第 2 輪「678」
判準    ① 三跳 verdict 與 delegate 與 EXPECTED_CHAIN 逐位相符
        ② **唯一 commit**＝contract_closeout，且 resolver 期間不建立任何 session
        ③ 單筆 grounding（transport 依識別過濾至 678）
        ④ **v6 ruler 成立**（tests/support/v6_regression_ruler.py，已凍結、7 self-tests passed）
        ⑤ 所有 responsibility／scope 判定皆來自真模型，**fail_open = false**
           （出現 rules_unavailable／brain_unavailable／error_fail_open 任一即判紅）
```

## 三、B：mid-session scope salvage regression（**Task 8 新增的 production behavior**）

```text
情境    已在 Face session 中 → 送一句明顯不屬本面向職責的訊息 → brain 判 scope=switch
判準    ① raw payload 確實含 scope=switch（spy 直接取 provider 原始 JSON）
        ② 即使 action 越界，parsed StepResult.scope 仍為 'switch'
           ——若本輪真模型未自然產生越界 action，**如實記錄「未觀察到」**，
             不得以決定性注入冒充真模型證據（該分支已由 unit 16 條覆蓋）
        ③ FACET_SCOPE_SALVAGE=**on** 時 observable control flow 真的改變
           （payload=None 且 scope=switch 時仍退出／重路由，而非落「引擎降級」）
        ④ FACET_SCOPE_SALVAGE=**off** 時維持舊行為（同一輸入不改變控制流）
```

## 四、預算與重試

```text
重複次數     A：3 次；B：off/on 各 1 次
呼叫上限     brain 輪（max_tokens=400）≤ 30；全部 provider 呼叫 ≤ 60；超過即 BudgetExceeded 中止
重試         **semantic／assertion 紅一律不重試**；只允許 infra 重試 ≤ 2
             （timeout／rate limit／429／5xx／connection）
成本量級     mini 費率下，30 次 × (輸入 2–4k／輸出 ≤400 token) ⇒ 個位數美分
```

## 五、不得為了綠燈做的事

```text
❌ 改 v6 尺、改案例、改 fixture 值
❌ 用 A 的結果回填 v5／C4b 任何一輪
❌ 以決定性注入冒充 B② 的真模型證據
❌ semantic 紅了重跑到綠（只有 infra 可重試）
❌ 把「未觀察到越界 action」寫成「越界分支已驗」
```
