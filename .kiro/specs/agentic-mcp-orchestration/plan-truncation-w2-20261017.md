# 計畫：W2 主模型輸出失控（灌空白至上限）處置

> 版本 r4（2026-10-19）。第 0 步已完成，0-2、0-3 停點觸發，業主依第 0 步報告裁示四項（DSP-095），本版依裁示改寫第 1、2 步與驗收清單。審查：第一輪 REVISE 四條已修；收尾審查 REVISE 兩條（獨占範圍、1-0 重現門檻）已修，未再審；業主 2026-10-19 核可。決策：DSP-095（W2 處置方式）、DSP-094（上線範圍含 W2）、DSP-096（執行順序）、DSP-080（gpt-oss 方向）、DSP-086（只量 gpt-oss）。
> 規則與驗收清單：`acceptance-truncation-w2-20261017.md`（r4，已凍結）。
> 第 0 步報告：`~/jgb-archive/arch-step3-20261018/w2/STEP0.md`（repo 外）。業界原文存檔：`~/jgb-archive/arch-step3-20261018/industry-w2/`（repo 外，web-drive 渲染，2026-10-19）。

## 1. 目標

### 1.1 業主原話

- 2026-10-19（DSP-094）：「2. 把 W2 截斷處置加進上線範圍：修正 DSP-093，先做提早中止和乾淨重試，備援模型之後再看。道謝為什麼容易觸發，在 W2 第 0 步一起查。同意」
- 2026-10-19（DSP-095，回覆第 0 步停點的四題，業主所選選項與其說明原文）：
  - 重試方式「改用現行重寫」：「中止後把剝掉空白的半截輸出附回去，再加格式提示（就是現行的重寫路徑，只是不再等滿 2,000 token）。偏離原話「乾淨重試」，理由是實測 95% 對 55%。」
  - 誤殺判準「改看使用者結果」：「不管這次呼叫本來會不會完成，只要中止＋重寫後使用者拿到的答案沒有變差（沒轉人、沒變慢超過 20 秒）就不算誤殺。驗收 C5 要改寫並重新核可。」
  - 明示 JSON「併入 W2 先做」：「W2 擴大範圍：先加這句，在 K、延期、E2a、題庫全量量副作用，再做提早中止＋重寫兜底。」
  - 卡住呼叫「併入 W2 查根因」：「W2 第 1 步先查清楚為什麼逾時沒切斷，再修；這是第 1 步第 5 項「以逾時中斷進行中的呼叫」能不能成立的前提。」
W-R6（不調高輸出上限）不是業主原話：業主問「2,000 token 是不是要提高 ?」，主視窗建議不提高（截斷輸出 95～99% 是空白，調高只會延長暴走），記為 DSP-094 否決項；業主核可 r4 時連同規則表一併接受。

規則 W-R0～W-R9 見驗收檔第一節；判定一律依規則。

### 1.2 使用者要達成什麼

客人問完、道謝或回答追問時，不會因為模型這一次輸出暴走，就等 20 秒以上之後被轉給真人；整回合也不會卡住好幾分鐘。

### 1.3 終點指標（基準 → 預期）

| 指標 | 基準 | 預期 | 來源 |
|---|---|---|---|
| 道謝回合轉人或失敗（含門面 `TOOL_TIMEOUT`，不論歸因） | 上午診斷 10 題 ×2：首呼叫截斷 12/20、轉人 9/20、16.6～31.7 秒；第 0 步 run2 30 回合：首呼叫截斷 12/30、轉人 4/30、最長 25.8 秒 | 0/20；每回合 ≤ 20 秒 | `ra/report-ra.md` §8.1；`diag/`；STEP0 |
| 道謝首呼叫截斷率（明示 JSON 的效果） | run2 12/30 | ≤ 6/30（原樣的一半以下，0-4 判準） | STEP0 |
| E2b 知識組 K（20 場）Intercom 解決 | 14/20；其中 5 場主因截斷 | 主因截斷 0 場（含由截斷開頭、之後因期限不足或逾時而轉人的連鎖）；≥ 18/20 | report-ra §8 |
| E2b 延期組 W-D＋C-D（12 場）主因截斷 | 期別片後：1/12（W-D3_k2） | 0 場；≥ 11/12 | `period/report-period.md` §5 |
| 截斷呼叫耗時 | 上午診斷每次 10.4～24.3 秒；重放最長 632 秒 | 由回合期限切斷，整回合 ≤ 20 秒 | `w2/thanks-breakdown-20261019.md`；STEP0 |
| 卡住呼叫 | 一回合 607 秒才回 `TOOL_TIMEOUT`（本機整回合逾時設 90 秒） | 整回合不超過 `AGENT_TURN_TIMEOUT_S`＋5 秒（5 秒＝門面外層寬限 `_AGENT_TURN_OUTER_MARGIN_S`，見 W-R9） | STEP0 |

## 2. 目標形態（業界做法；原文見存檔）

只寫查得到原文的做法；各家不同處照實列出，⛔ 推成「業界都」。

1. **串流中途偵測退化並中止，交給重試。** LiteLLM 內建：「Sometimes a model might enter an infinite loop, and keep repeating the same chunks … `litellm.REPEATED_STREAMING_CHUNK_LIMIT = 100` … If it exceeds that limit, it will raise a litellm.InternalServerError, to allow retry logic to happen.」（`litellm-stream.txt`）。OpenAI Python SDK 的串流物件可中途關閉：「def close(self) -> None: """Close the response and release the connection."""」（`openai-python-streaming-src.txt`）。本片不採這一項，理由見 §5。
2. **串流中止後的重試要自己寫。** OpenAI SDK：「Stream consumption is not automatically retried, because replaying a request could duplicate output already delivered to your application.」（`openai-python-readme.txt`）。
3. **整體時間預算由外層期限把關；單次請求另設逾時。** Instructor：「It does not interrupt an in-flight SDK request, SDK backoff, parsing, or user validation.」，範例以 `asyncio.wait_for(...)` 包住（`instructor-retrying.txt`）。OpenAI SDK：「By default requests time out after 10 minutes. You can configure this with a timeout option」，並示範單次請求 `client.with_options(timeout=5.0).chat.completions.create(`（`openai-python-readme.txt`）。
4. **輸出未完成（觸及 token 上限）視為錯誤，不當成功輸出。** OpenAI 結構化輸出指南範例：`if response.status == "incomplete" and response.incomplete_details.reason == "max_output_tokens": raise Exception("Incomplete response")`（`openai-guide-structured-outputs-md.txt`）。
5. **重試附回失敗輸出與回饋。** LangChain `RetryOutputParser` 附回失敗輸出：「Prompt: {prompt} Completion: {completion} Above, the Completion did not satisfy the constraints given in the Prompt.」（`langchain-retry-src.txt`）。Instructor 把驗證錯誤整理成回饋加進 context：「Captures the validation error(s) / Formats them as feedback / Adds the feedback to the prompt context / Asks the LLM to try again」，頁面沒說是否附回失敗原文（`instructor-retry-mechanisms.txt`）。存檔所查的 LangChain、Instructor、Guardrails 都沒有專談 `finish_reason=length` 之後附不附回。我們的做法（附回剝空白後的半截輸出＋SCHEMA 回饋）與 LangChain 同型；選它的依據是第 0 步實測（合格 57/60 對乾淨重試 33/60）。
6. **明示「輸出 JSON」可避免灌空白。** OpenAI 指南：「If you don't include an explicit instruction to generate JSON, the model may generate an unending stream of whitespace and the request may run continually until it reaches the token limit.」（`openai-guide-structured-outputs.txt`）。vLLM #32791（gpt-oss-120b、多輪、`json_object`）：「results in message.content == null, invalid JSON, or whitespace/repetition loops — even for trivial prompts.」，根因在 vLLM 的 parser（`vllm-issue-32791.txt`）；Bedrock 的後端實作不明，不能類推。
7. **環境：Bedrock gpt-oss-120b 串流可用**：模型卡標 Response streaming [YES]（`bedrock-gpt-oss-120b-card-dom.txt`）；第 0 步 0-1 實測 runtime 端點帶 tools＋strict `response_format`＋`reasoning_effort` 的 `stream=true` 四項可用（STEP0）。中止後 Bedrock 是否停止生成與計費：未查完。

相關但不在本次範圍：備援模型（業主「之後再看」）；`frequency_penalty`／`presence_penalty`（Bedrock 是否接受未查完）；對話歷史改以 JSON 形式呈現（0-4「刪上一輪回覆」組也有效，但刪除會丟上下文；改呈現方式未量測，不服務本次規則）。

## 3. 差距（現況，2026-10-19 對碼）

| 現況 | 查證 | 與目標形態的差距 |
|---|---|---|
| system 提示沒有任何「只輸出 JSON」的明示 | `rag-orchestrator/services/agent/prompt_assembler.py` `build()` 組 `system_content`；`grep -n "JSON" rag-orchestrator/services/agent/prompt_assembler.py rag-orchestrator/services/agent/agent_rules.py` 只命中舊鏈說明 | 目標形態 6 |
| 模型呼叫為非串流，一次等完整回應 | `runtime.py` `_next_model_message`：`chat.completions.create(**create_kwargs)`，無 `stream` | 逾時切斷時拿不到已收到的內容，無法估算計量（目標形態 3） |
| 截斷只記旗標 `llm_output_truncated`，之後照 SCHEMA 解析失敗路徑：附回剝推理後的輸出＋`rewrite_feedback("SCHEMA", …)` | 同函式 `finish_reason == "length"`；`_run_model_loop` | 重寫路徑本身沿用（目標形態 5）；差在每次截斷要等滿 2,000 token |
| 重寫上限與時間預算：`max_rewrites=2`、`deadline_s=20.0`，期限只在迴圈頂端檢查 | `services/agent/budget.py` `Budget`；`_run_model_loop` 迴圈頂端 | 進行中的呼叫不受期限中斷（目標形態 3） |
| 主模型呼叫沒有單次逾時；client 逾時取 `OPENAI_TIMEOUT_S`，未設 ⇒ SDK 預設 600 秒（正式機 `docker-compose.prod.yml` 預設空）。最外層門面 `asyncio.wait_for(runtime.run_turn(...))`，上限 `AGENT_TURN_TIMEOUT_S`（prod 預設 30、本機 `docker-compose.bedrock-local.yml` 90） | `services/llm_provider.py` `OPENAI_TIMEOUT_S`；`mcp_facade.py` `agent_turn_timeout_s`、`TOOL_TIMEOUT` | 第 0 步實測一回合 607 秒才回 `TOOL_TIMEOUT`：外層逾時沒有及時切斷，原因未查明（目標形態 3） |
| 截斷呼叫最長 632 秒（Bedrock 極慢地吐空白） | STEP0「截斷呼叫可長達 10 分鐘」 | 同上 |
| 計量依賴回應的 `usage` | `_next_model_message`：`usage_metering.add_llm_usage(...)` | 被期限切斷的串流拿不到 usage（0-1 證實 `include_usage` 只在串流結束時給） |

## 4. 路徑

### 第 0 步：量測（已完成）

結果見 STEP0：0-1 四項可用；0-2 找不到 N（停點觸發）；0-3 乾淨重試不如現行重寫（兩條停點觸發）；0-4 候選機制為「沒有明示 JSON」與「歷史裡的純文字回覆」。業主裁示見 DSP-095。串流中途偵測空白即中止不採（DSP-116，見 §5）。

### 第 1 步：實作（業主核可本計畫後；依 DSP-096 順序排在 A+、B 之後，除非業主改序）

- 執行角色：1-0 卡住呼叫的根因由主會話查（單一未知缺陷，依全域規則主會話自查）；1-1～1-6 交 `executor`（有界判斷），主會話負責整合與驗收。
- 專屬改動檔：`rag-orchestrator/services/agent/runtime.py`、`rag-orchestrator/services/agent/budget.py`、`rag-orchestrator/services/agent/prompt_assembler.py`、新檔 `rag-orchestrator/tests/unit/agent/test_truncation_w2_req.py`；1-0 若查出根因在其他檔（例如 `mcp_facade.py`、`services/llm_provider.py`），先列出檔名與理由、經主會話判定在本片範圍才改。既有測試若因改動要調整，先列出檔名、經主會話同意才改。
- 獨占：開工條件是其他片對上列檔案沒有進行中的改動（A+、B 已收尾或尚未開工）。從快照到 W2 收尾，其他片不得改這些檔。之後加入快照的檔（見「回復」）同樣適用：加入前先確認其他片對該檔沒有進行中的改動，確認不了 ⇒ 停，回主會話；加入後到 W2 收尾由本片獨占。

1-0. **查卡住呼叫的根因**（W-R9）：在本機診斷容器重現「進行中的模型呼叫超過整回合逾時仍未被切斷」——以 repo 外的假 LLM 端點（收到請求後不回應或極慢吐字）當 `AGENT_LLM_BASE_URL`，量整回合實際耗時是否超過 `AGENT_TURN_TIMEOUT_S`＋5 秒（與 C9 同一門檻）。查到機制（哪段程式、為何取消沒生效）並附證據；修法在 1-5 一併實作。重現不出 ⇒ 停，回業主附做過的重現方式。
1-1. **明示 JSON**（W-R7）：`prompt_assembler.py` `build()` 的 `system_content` 末尾加第 0 步實測的原句「Always respond with a single valid JSON object that matches the schema; do not output any text before or after the JSON.」（`w2/shim/replay.py` `SYSJSON`）；⛔ 改寫措辭（措辭若要改，須重量 0-4）。
1-2. （W-R1）`_next_model_message` 改為串流：拼回 message（content、tool_calls、finish_reason、usage），行為與現行逐欄相同；灌空白 ⛔ 提早中止，串流讀到結束（DSP-116）。
1-3. 截斷（`finish_reason == "length"`）⇒ 走現行重寫路徑（W-R2）：附回的半截輸出一律剝推理段（若有）並去頭尾空白，再加 `rewrite_feedback("SCHEMA", …)`，與第 0 步 0-3(b) 實測附回的內容相同（現行只在 `clean_llm_output=True` 且有推理段時才剝與去空白；截斷的輸出不論有無推理段都去空白，否則會把整串空白附回）；占 `max_rewrites`，⛔ 新增另一種重試。
1-4. （串流化與 1-5 的配套；實際事件：`runtime.py` `_next_model_message` 註解記載的 2.6 前置 security review P2——每次模型呼叫都要計量）逾時被切斷的呼叫仍要計量，⛔ 讓計量退化：有 usage 用 usage；沒有就用已收到的 content 字元數估 completion token、prompt token 取本回合上一次同請求的值或以 0 記，並記 `llm_usage_estimated`。
1-5. **期限中斷進行中的呼叫**（W-R9、目標形態 3）：主模型呼叫（含串流消費）以回合剩餘期限（`deadline_s` 減已用時間）為上限中斷，並對該次請求設 SDK 單次逾時（`with_options(timeout=…)` 或 `timeout=` 參數），讓 1-0 查到的未切斷路徑也會結束；逾時 ⇒ 關閉串流、走現行 `budget_exhausted` 固定句。重寫前剩餘期限 < 正常主呼叫 p95（2.6 秒：run2 驅動中 `finish=stop` 的主呼叫 126 筆，p50 1.37、p95 2.63、最長 13.76 秒；STEP0「補充量測」）⇒ 不重寫，直接固定句。
1-6. 單元測試：拼回等價；灌空白不中止、空白後正常收尾照常採用；截斷後重寫附回內容與現行相同；剩餘期限不足不重寫；逾時中斷進行中的呼叫（含 1-0 重現的路徑）；明示 JSON 句在 `system_content` 末尾；計量估算。

### 第 2 步：驗收（凍結清單 C1～C9）

先只套 1-1 重建常駐服務，跑 C8（明示 JSON 的效果與副作用，五組全量）；C8 過了再疊 1-2～1-5 重建，跑 C2～C5、C9；C6 為單元測試；最後 C7。

### 停點（看結果的條件）

- 第 1 步：1-0 重現不出；單元測試或 `check_invariants.sh` 無法在核可範圍內修到通過 ⇒ 停，回業主。
- 第 2 步：C2～C6、C8、C9 任一項未達，或 C7 被判 REFUTED ⇒ 先查到機制層（哪段程式、哪種輸入，附 trace）。屬本片範圍、修法有界 ⇒ 依全域修復規則修並重驗；否則停，回業主並附機制。C8 任一組比基準差 ⇒ 停，回業主（明示 JSON 句的副作用由業主裁，不自行改措辭）。

### 回復

第 1 步開工前，把專屬改動檔存快照到 `~/jgb-archive/arch-step3-20261018/w2/baseline/`（含 sha256）；之後 W2 第一次動任何不在快照裡的檔（含 1-0 查出後加入的檔、經同意調整的既有測試）之前，先把該檔加進 `baseline/`（含 sha256），新建檔記為「快照時不存在」。收尾時產生 W2 自己的 diff（所有快照檔：快照 → 收尾工作樹），存成 `w2/w2.patch`；`w2.patch` 的檔案清單必須等於 W2 實際改動的檔案清單。回復時用 `patch -R` 反向套用 `w2.patch`，只撤回 W2 的改動。⛔ 整檔覆蓋回快照；⛔ `git checkout HEAD`（工作樹有 A 片與期別片未提交的改動）。

## 5. 偏離目標形態的取捨

- 不採目標形態 1「串流中途偵測退化並中止」（DSP-116）：本模型灌空白的呼叫多數最後仍 `finish=stop` 且輸出可用（對照重放 10 次退化中 7 次），中止會把它們變成失敗，而中止後重寫常再灌空白（C2 中止回合 9 個中 6 個）；改由目標形態 3 的回合期限切斷卡太久的呼叫，截斷才走重寫。LiteLLM 偵測的「相同 chunk」與空白是否等價查無對應，未試。
- 不採「調低輸出上限」當中止手段：正常完成的輸出 completion 最高 1,999 token（`w2/run2/` 重放資料中 `finish=stop` 且合格者），調低會截到正常答案。
- 偏離業主原話「乾淨重試」：業主依實測改裁「改用現行重寫」（DSP-095）。
- 明示 JSON 句用英文原句：這是第 0 步實測過的版本；system 提示其餘為中文，混用是取捨，換中文須重量。

## 6. 待業主決定

- 停點一旦觸發（見 §4「停點」），回業主決定。

業主裁示（2026-10-25，執行中觸發的停點）：

- 1-0 重現不出（`~/jgb-archive/arch-step3-20261018/w2/repro10/`：明文與 TLS 假端點、不回應與慢吐字、全鏈路與 SDK 層，皆準時切斷）⇒ 業主選「照做 1-5，C9 改判未驗」：1-2～1-5 照做；C9 的「修前重現成立」判未驗，修後仍以同一假端點量整回合 ≤ `AGENT_TURN_TIMEOUT_S`＋5 秒並回固定句或 `TOOL_TIMEOUT`，機制欄寫「未查明」並列出做過的重現方式。依據：第 0 步卡住回合 608 秒≈SDK 預設逾時 600 秒；C8 呼叫 `1_00245` 在 Bedrock 端 63.8 秒、20 秒期限未切斷（`w2/c8/report-c8.md` §4）。
- C8 E2a RS 1/2（A 後 2/2，失敗為讀回句未含單號）⇒ 業主選「視為共有變異，續做」（同 2026-10-23 F12 裁示）；C8 其餘各組皆達門檻（`w2/c8/report-c8.md` §1）。

業主裁示（2026-10-26，C3～C5 未達觸發的停點）：

- C3 道謝轉人 1/20、C4 K 17/20、C5 中止回合 9 個中 6 個「重寫又灌空白再中止」⇒ `budget_exhausted` 轉人（`~/jgb-archive/arch-step3-20261018/w2/c2/report-c2.md`）。串流 vs 非串流對照重放（判準跑前凍結，`w2/shim/ab/DECISION.md`）：240 次退化 非串流 6、串流 4 ⇒ 串流不是原因；10 次退化中 7 次最後 `finish=stop` 且輸出可用 ⇒ 500 空白中止把可用輸出變成失敗。業主選「撤 500 空白中止」：
  - W-R1 改為：灌空白時 ⛔ 提早中止，串流讀到結束；卡太久由 1-5 回合期限切斷。1-2 保留串流拼回，偵測器與 `llm_output_degenerate_aborted` 移除。
  - 1-3 只在模型真的回 `finish_reason == "length"` 時走（附回剝推理、去頭尾空白的半截輸出）；1-4 估算只用在逾時；1-5 不變。
  - C2 改判不適用；C5「觸發中止的回合」讀為「觸發截斷（`llm_output_truncated`）的回合」，正對照 0 次 ⇒ 未驗；C6「偵測器正負樣本」改為「灌空白不中止、空白後正常收尾照常採用」。C3、C4、C5 用同一批題重量，再跑 C6、C7。
- 重量（`~/jgb-archive/arch-step3-20261018/w2/r2/report-r2.md`）：K 20/20、延期 11/12 過；C3 道謝 1/20 轉人（真截斷 18.3 秒，期限內放不下重寫）、C5 截斷 3 次中同一次轉人、E2a T 1/2（W2 未改的寫入意圖判斷呼叫，同輸入不同輸出）⇒ 業主選「接受殘餘、往下收案」：這兩項列為已知殘餘、記後補清單，C3、C5 以此收窄判定；接著 C6、C7、`w2.patch`。

## 7. 用量回報

不設 token 上限；每片收尾回報子代理 token 加總與 Bedrock 費用；停點只用結果條件。第 0 步：Bedrock 918 次呼叫約 US$1.5，未派子代理（STEP0）。
