# 6.2 執行參數（**FROZEN，執行前凍結**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**。
> 解除 `c4b-phase-inventory.md` §「執行前必須先凍結的四件事」的 ①②③④。
> 相依：`c4b-ruler-frozen.md`（尺）、`c4b-entry-path-equivalence-resolved.md`（進場與供裝）。

> **凍結的意義**：以下每一項若在**看到 6.2 結果之後**變更，該次 evidence 即作廢，
> 須以新參數重跑並在報告中標明「參數已變更」。**不得**「跑到綠為止」。

## ① model／temperature／max_tokens／prompt／工具

C4b 每個案例會發生**恰好兩次**外部呼叫，兩次的參數**不同**，故分開凍結：

| | 第 1 輪 brain（`conversational_step`） | 第 2 輪合成（`synthesize_presales_answer`） |
|---|---|---|
| 觸發 | 訊息無識別碼 → 走 brain 決策 | 訊息為 `fixture_bill_id` → **決定性填槽**，不經 brain |
| model | `PRESALES_SYNTH_MODEL` → **`gpt-4o`** | `PRESALES_ANSWER_MODEL`→`OPENAI_MODEL` → **`gpt-4o-mini`** |
| temperature | `ADVISOR_TEMP` → **`0.4`** | `cta_mode="factual"` → `LLM_ANSWER_SYNTH_TEMP` → **`0.2`** |
| max_tokens | **400** | `LLM_ANSWER_MAX_TOKENS` → **800** |
| response_format | `json_object` | 純文字 |
| 工具 | **無**（見下） | 不適用 |
| prompt | **production 原樣**，不得為測試改寫 | 同左 |

解析點：`services/llm_answer_optimizer.py:946-947`（brain）／`:1060-1070`（合成）。

⚠️ **runner 保真度修補（本次一併處理）**：`PRESALES_SYNTH_MODEL` 原本只宣告於
`docker-compose.prod.yml`，`.env` 與 `docker-compose.dev.yml` 皆無 → 測試容器的 brain 會落回
`gpt-4o-mini`，**不是** production 的 `gpt-4o`。已於 `docker-compose.dev.yml` 逐字鏡射該宣告。
（與 `KB_SIMILARITY_THRESHOLD` 同一類事故；本專案已三次因 runner 保真度不足而結論作廢。）

⚠️ **brain 不掛 `kb_search` 工具**：`conversational_engine.py:672-676` 僅對交易面向
（`grounding_scope.execute_endpoint`）注入，兩個診斷面向皆未宣告 → 工具不存在。
故 C4b **不會**發生檢索呼叫，`tool availability = none` 是**推導出的事實**，不是選項。

## ② 案例、重跑次數、外部呼叫上限

```text
cases                    4（沿用 C4a frozen 四案，見 c4b-ruler-frozen.md）
runs_per_case            3
判定                     **3 次全過才算該案通過**（不取多數決）
                         → 真 brain 若只是「有時會引用」，那本身就是 C4b 要抓的結論
nominal_external_calls   4 × 3 × 2 = **24**
hard_cap                 **30**（含下方 retry 配額）；超過即中止並記 PAUSED，不得續跑
```

⚠️ 不取多數決的理由：本尺問的是「有沒有用這筆的值」。
一個 grounded 的回答**每次**都該引用；抖動即缺陷，用多數決會把缺陷洗掉。

## ③ retry policy（事前寫死）

```text
可 retry     僅**基礎設施類**失敗：timeout／rate limit／5xx／連線中斷
retry 上限   每次呼叫至多 2 次，全域 retry 配額 6 次（含在 hard_cap 30 之內）
不可 retry   斷言失敗（任何一類）——**一次紅就是紅**，記錄後進 6.3 裁決
記錄義務     每次 retry 必須進報告（次數、原因、發生於哪一案哪一輪）
```

## ④ 失敗分類（五類，**不得混為一談**）

| 類別 | 判準 | 處置 |
|---|---|---|
| `infra` | OpenAI timeout／rate limit／5xx | 依 ③ retry；耗盡→該案記 **INCONCLUSIVE**（既非通過也非 C4b 失敗） |
| `grounding_absent` | grounding 未送達 answer stage | **C4a 回歸**——凍結 6.2，回頭查 5.x，不得當成 C4b 結論 |
| `not_used` | grounding 在，但回答未引用該筆值／出現泛用標記 | **這正是 C4b 要偵測的失敗**，進 6.3 報告 |
| `wrong_instance` | 回答引用到別筆 fixture 的字面 | 同上，且須另記是哪一筆 |
| `ruler_false_red` | 回答正確，但撞到列舉式反向字面（如「是待對帳，不是待繳費」） | **6.3 人工裁決**；**不得**當場改尺救綠 |

⚠️ `ruler_false_red` 事前就存在於清單裡，是為了讓「改尺」這個念頭在**看到紅之前**
就已經被封死——事後才新增這個分類，等於用結果反推標準。

## ⑤ 環境與 skip 語義（「沒跑」不得看起來像「綠」）

```text
入口          scripts/run-tests.sh e2e （注入 RUN_E2E=1 ＋ REQUESTED_TEST_LAYERS=e2e）
jgb2 替身     USE_MOCK_JGB_API=true → JGBMockTransport（**不得**打真 jgb2 preview）
DB            測試庫 aichatbot_test（DB_ENV=test 守門）
標記          @pytest.mark.e2e（預設略過、不擋 CI）
```

evidence **MUST** 記錄，且**不得**只貼 pytest summary：

```text
executed_cases = 4        skipped_cases = 0        runs_per_case = 3
external_calls = <實際數>  retries = <實際數>       failures_by_class = {...}
```

## ⑥ 預期成本量級（R7.2 的「標明」義務）

```text
上界（含 retry 配額用盡）  ≤ 30 次呼叫
  gpt-4o     ≤ 12+ 次 × (輸入約 2–4k token ／ 輸出 ≤400 token)
  gpt-4o-mini ≤ 12+ 次 × (輸入約 2–4k token ／ 輸出 ≤800 token)
```

以公開費率量級（gpt-4o 約 $2.5／$10 每百萬 token；mini 低一個數量級）換算，
整輪凍結執行的預期成本在 **US$1 以下**。
⚠️ 費率**以帳單為準**；本檔凍結的是**呼叫數與 token 上界**，那才是可被機器守住的部分。

## ⑦ 這份凍結**不**涵蓋

```text
❌ 未執行 6.2
❌ 未改 C4a 的案例／required facts／observation contract／fixture
❌ 未變更 production 的 prompt、模型或溫度（只補了測試容器的宣告缺口）
❌ 不構成放行——放行是 6.3，放行人為業主
```
