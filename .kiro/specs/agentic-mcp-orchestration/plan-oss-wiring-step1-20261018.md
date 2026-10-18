# 計畫：主線第 1 步「正式接線（本地替換 gpt-oss）」（2026-10-18 第 4 稿：併入 security-reviewer 發現、plan-verifier 第 1、2 輪 REVISE 處置）

> 業主原話：「我要調整成 Amazon Bedrock 的使用方式」「我有 ai-cs-bedrock-api-key.txt 所以是替換 並不是評估」「先暫定 gpt-oss 去處理問題」「目前要該是要把本地替換 oss 並確保 回應品質都能符合 有效的回應 並把某些部分邏輯參考業界做法去調整」「正式接線 是本地都處理好 才線上換吧」；本次指示「照 §2.4 開始寫主線第 1 步『正式接線（本地替換 gpt-oss）』的計畫：設計方法四步、接點盤查清單八項、第 0 步先探測 Bedrock 是否接受 reasoning: {exclude: true}；金鑰處置先過 security-reviewer，再送 plan-verifier，交我核可後才實作。任何會呼叫 JGB 的測試前，先照 §2.3 確認本機是 mock。」
> 依據：`HANDOFF-20261018.md` §1～§2、盤查報告 `audit-oss-replacement-20261018.md`（`/canon-audit agentic-mcp` 22/22 整檔讀過）。
> 驗收清單（凍結後以此為準）：`.kiro/specs/agentic-mcp-orchestration/acceptance-oss-wiring-step1-20261018.md`
> 業界原文：`~/jgb-archive/devflow-20261018/sources-oss/`（皆以 web-drive 渲染後抽字）。

**終點指標**：gpt-oss 最終輸出不經評估 shim、能被正式程式解析的比例——現值 **0／15**（已存 Bedrock 原始輸出中 AgentOutput 最終輸出 15 則，`json.loads` 原文 15 則全敗；2026-10-18 主會話以 `~/jgb-archive/eval-harness/runs/*/shim_raw.jsonl`＋`bedrock-eval-20261017/**/shim_raw*.jsonl` 統計）→ 預期 **≥12／15**（＝shim 處理後可解析數，等價測試）；本機常駐服務對話模型：gpt-4o-mini／OpenAI → `openai.gpt-oss-120b-1:0`／Bedrock、不經 shim。

## 0. 現況（已對碼；行號只作定位，以符號為準）

| 事實 | 查證 |
|---|---|
| 對話模型連線：`app.py` 以 `get_llm_provider()` 取 provider 交 `_agent_bootstrap.build_runtime`；同一個 provider 也交 `ShadowRunner` | `grep -n "_get_llm_provider\|build_runtime(" rag-orchestrator/app.py` |
| `OpenAIProvider.__init__(self, api_key=None)` 建 `OpenAI(api_key=...)` 與 `AsyncOpenAI(api_key=..., timeout=OPENAI_TIMEOUT_S)`，**沒有 base_url 參數**；`get_llm_provider` 以 `_provider_cache` 依 provider 類型共用一個實例 | `grep -n "class OpenAIProvider\|AsyncOpenAI(\|_provider_cache" rag-orchestrator/services/llm_provider.py` |
| 站內幫手只有兩個呼叫點用這個 provider：主呼叫 `AgentRuntime._next_model_message`、寫入意圖呼叫 `_start_write_intent_call` | `grep -n "self.provider.async_client" rag-orchestrator/services/agent/runtime.py`（2 處） |
| 照片、文件、健康檢查各自 `AsyncOpenAI(api_key=OPENAI_API_KEY)`，都不帶 base_url ⇒ 若照評估容器做法設全域 `OPENAI_BASE_URL`，三者會一起被導向 Bedrock（gpt-oss 不收圖片；健康檢查會拿 OpenAI 金鑰去打 Bedrock） | `grep -n "AsyncOpenAI(" rag-orchestrator/services/image_recognition_service.py rag-orchestrator/services/agent/document_extract.py rag-orchestrator/services/pipeline_health_service.py` |
| 唯一解析點：`_run_model_loop` 無 tool_calls 分支 `json.loads(content)` → `AgentOutput.model_validate`；失敗 ⇒ `rewrites += 1`，用完 ⇒ `build_fixed("budget_exhausted")`；未用完 ⇒ 原文 `{"role":"assistant","content":content}` append 進 messages＋`rewrite_feedback("SCHEMA", ...)` | `grep -n "json.loads(content)\|rewrite_feedback(\"SCHEMA\"" rag-orchestrator/services/agent/runtime.py` |
| 原文 content 另在 HANDOFF_DATA、RECENT_REFS、VERIFIER_REJECT 三條改寫 append；工具呼叫訊息 `_assistant_tool_call_message` 帶原 content | `grep -n "\"role\": \"assistant\", \"content\": content\|def _assistant_tool_call_message" rag-orchestrator/services/agent/runtime.py` |
| 寫入意圖解析已能處理推理段：`write_forms.parse_write_intent_content` 取最後一個 `</reasoning>` 之後、逐個 `{` 試 `raw_decode` | `grep -n "def parse_write_intent_content\|_REASONING_CLOSE\|raw_decode" rag-orchestrator/services/agent/write_forms.py` |
| 主迴圈沒有任何推理段處理（`<reasoning`、`raw_decode` 在 runtime.py 0 命中；正對照 `json.loads(content)` 有命中） | `grep -c "<reasoning\|raw_decode" rag-orchestrator/services/agent/runtime.py`；正對照 `grep -c "json.loads(content)" ...` |
| 價目：`usage_metering.DEFAULT_PRICING`（USD／百萬 token）沒有 gpt-oss，`_compute_cost` 精確比對模型名，缺價 ⇒ `est_cost_usd=None`；可由 `LLM_PRICING_PATH` JSON 增補 | `grep -n "DEFAULT_PRICING\|def _pricing\|LLM_PRICING_PATH" rag-orchestrator/services/usage_metering.py` |
| 健康檢查 `_check_llm` 以 `OPENAI_API_KEY` 呼 `models.list()`、`is_core=True`；沒有檢查對話模型端點 | `grep -n "async def _check_llm\|models.list" rag-orchestrator/services/pipeline_health_service.py` |
| `docker-compose.prod.yml` 的 rag-orchestrator 用明列 `environment:`（無 env_file）；不傳 `OPENAI_BASE_URL`；全檔無 `secrets:` | `grep -n "OPENAI_BASE_URL\|^secrets:\|  secrets:" docker-compose.prod.yml`（0 命中）；正對照 `grep -n "AGENT_MODEL" docker-compose.prod.yml` |
| 已存 Bedrock 原始回應（eval-harness `runs/*/shim_raw.jsonl`、bedrock-eval-20261017，11 檔）：gpt-oss 訊息 30/30 在 content 夾 `<reasoning>`（含 1 則工具呼叫訊息），message 只有 content／role／tool_calls 三鍵，無獨立 reasoning 欄位；AgentOutput 最終輸出 12 則去標籤後可解析、2 則去標籤後為空（只有推理、`stop`）、1 則灌空白至 `length` | 2026-10-18 主會話統計（⚠️ 看到的是 SDK `model_dump` 後的物件，原始 HTTP 未看 ⇒ 第 0 步 Q2 補） |
| 評估 shim 做的事：所有字串 content（含工具呼叫訊息）以 `<reasoning>.*?</reasoning>` 剝除；json_schema 且無 tool_calls 時截第一個 `{` 到最後一個 `}`；W1、R3 的 gpt-oss 結果皆在此條件下測得 | `~/jgb-archive/eval-harness/shim/bedrock_shim.py` `_create` |
| 本機常駐服務 mock：2026-10-18 業主以覆寫重建後 `_use_mock_jgb_api()` 回 `True`；`.env` 未改，不帶覆寫重建會回 `False` | HANDOFF §2.3 指令 |

## 1. 設計方法四步

### 1.1 目標（業主原話）

- G1「我要調整成 Amazon Bedrock 的使用方式」「所以是替換 並不是評估」——本機常駐服務的客服對話真的走 Bedrock gpt-oss，不經評估 shim。
- G2「確保 回應品質都能符合 有效的回應」——本步只負責「接線不讓品質變差」：推理原文不外洩、最終輸出能被解析、不因接線多轉人；品質達標由第 2 步量測、第 3 步修（HANDOFF §1.4）。
- G3「正式接線 是本地都處理好 才線上換吧」——本步只動本機；正式機在開關關閉時行為逐位不變（現行 gpt-6-luna）。
- G4 業主本次指示：金鑰處置過安全審查；呼叫 JGB 的測試前確認 mock。

### 1.2 目標形態（業界做法，照原文；渲染檔在 `~/jgb-archive/devflow-20261018/sources-oss/`）

**A. 推理原文的處理**

| # | 業界原文 | 出處檔 | 推出的目標形態 |
|---|---|---|---|
| A1 | 「You therefore should not show raw CoT to end users.」 | `openai-cookbook-handle-raw-cot.txt` | 推理原文不得出現在客人看到的答案與留存的對話 |
| A2 | 「After a message to the final channel in a subsequent sampling turn all analysis messages should be dropped. Function calls to the commentary channel can remain」 | 同上 | 模型給出最終輸出後，下一次取樣不再帶前面的推理 |
| A3 | 「If the last message by the assistant was a tool call of any type, the analysis messages until the previous final message should be preserved on subsequent sampling until a final message gets issued」；推理對「the performance of tool calling」很重要 | 同上 | 同一回合的工具迴圈中，推理**應保留**給下一次取樣，直到最終輸出 |
| A4 | 「Raw CoT will be returned as part of the response unless reasoning: { exclude: true } is specified as part of the request.」「The raw CoT is exposed as a reasoning property on the message in the output」「When in doubt, please follow the convention / behavior of the OpenRouter implementation.」 | 同上 | 推理應走獨立 `reasoning` 欄位，不夾在 content；可用 `exclude` 不回傳 |
| A5 | 「Reasoning tokens will appear in the reasoning field of each message, unless you decide to exclude them.」「"exclude": true - The model will still use reasoning, but it won't be returned in the response. The tokens are still billed and count against max_tokens.」「Preserving reasoning blocks is useful specifically for tool calling」 | `openrouter-reasoning-tokens.txt` | `exclude` 不省費用、不省輸出上限；工具迴圈保留推理有益 |
| A6 | 「If you use InvokeModel, the model reasoning, surrounded by <reasoning> tags, precedes the text content of the response.」；Chat Completions 回應「conforms to the chat completion object」 | `aws-model-parameters-openai.txt` | Bedrock 至少在 InvokeModel 把推理以標籤夾進 content；Chat Completions 是否同樣，原文未明說 ⇒ 第 0 步 Q2 實測（已存樣本 30/30 夾在 content） |
| A7 | 「Reasoning: Supported, on by default (effort configurable: low, medium, high)」 | `aws-model-card-gpt-oss-120b.txt` | 推理不能關，最低 `low`（與 2026-10-17 實測 `none` 回 400 一致） |

**B. 金鑰處置**

| # | 業界原文 | 出處檔 | 推出的目標形態 |
|---|---|---|---|
| B1 | 「Short-term – Lasts up to 12 hours … Recommended for production use.」「Long-term keys are for exploration only. For production, use short-term keys.」；自動更新用 `aws_bedrock_token_generator.provide_token()` | `aws-api-keys.txt` | 長期金鑰只限探索用途——本機接線視為探索、非正式；正式機應改短期金鑰＋自動更新 |
| B2 | 「If you’re injecting passwords and API keys as environment variables, you risk unintentional information exposure.」「Environment variables are often available to all processes … can also be printed in logs」「Secrets are mounted as a file in /run/secrets/<secret_name>」；`_FILE` 環境變數慣例 | `docker-compose-secrets.txt` | 金鑰以 Compose secret 掛成檔案，程式讀 `*_FILE` 指的路徑；不放環境變數 |

**C. 查無業界對應、依第一原理推導的部分（照實標註）**

- C1 **依能力分端點**：對話走 Bedrock、照片與文件仍走 OpenAI 視覺模型。推導：gpt-oss 只收文字（AWS 模型卡；2026-10-17 實測），視覺模型 IAM 未開（HANDOFF §1.3）⇒ 兩種能力必須各有端點與金鑰；金鑰與端點必須成對，否則一方的金鑰會被送到另一方（洩漏）。查無業界對應。
- C2 **嚴格結構化輸出的容錯解析**：strict `json_schema` 理應保證整段是 JSON，但已存樣本見推理標籤（15／15）、2026-10-17 東京實測 strict json_schema 回傳 2／2 前面多了「以下」（記憶 `reference_llm_model_pricing_20261008.md`；HANDOFF §3「修正 strict JSON 前綴」）⇒ 解析前去標籤並以 `raw_decode` 取第一個完整 JSON 物件（與專案已有 `parse_write_intent_content` 同法）。查無業界對應（OpenAI／AWS 原文都假設 strict 輸出乾淨）。
- C3 **每次模型呼叫記成本**：沿用專案既有計量契約（`usage_metering`），價格須取官方來源。查無業界對應（屬自家契約）。

### 1.3 差距

| 目標形態 | 現況 | 差距 |
|---|---|---|
| A1 推理不外洩 | 主迴圈不處理推理；最終答案只在 JSON 解析成功時才產生，推理段讓解析失敗 ⇒ 多半走 SCHEMA 改寫至 `budget_exhausted` 轉人（不外洩但答不出） | 解析前清理 |
| A2 最終後丟推理 | 原文含推理被 append 進 messages（四條改寫路徑） | append 用清理後內容 |
| A3／A4 工具迴圈保留推理、走獨立欄位 | 推理夾在 content（已存樣本）；工具呼叫訊息原 content 回送 | 第 0 步 Q2／Q3 判定 Bedrock 能否收發 `reasoning` 欄位，再定 |
| B1／B2 金鑰為檔案、長期金鑰只限本機 | 只有 `OPENAI_API_KEY` 環境變數；Bedrock 金鑰在 `~/Downloads`，評估腳本以 `$(cat …)` 匯出成環境變數 | 新增對話端點專用的檔案金鑰 |
| C1 依能力分端點 | provider 只有一組，且以類型快取共用 | 對話 provider 另建、不進快取 |
| C2 容錯解析 | 只有寫入意圖路徑有 | 主迴圈補上（共用同一解析函式） |
| C3 成本 | gpt-oss 無價 ⇒ 成本留空 | 依官方價補價 |
| 健康檢查 | 只檢查 OpenAI 金鑰 | 對話端點設定時加檢 |
| 量測工具 | eval-harness 只打評估容器 18101（含 shim） | 能打常駐服務 8100（不含 shim） |

### 1.4 路徑（每項對回 1.1 目標或實際事件；偏離目標形態的取捨照實寫）

| 片 | 做什麼 | 服務 |
|---|---|---|
| S0 | 第 0 步探測（§2） | G1；業主指示「第 0 步先探測」；事件：W1 未探測就實作多兩輪（steering「先探測」） |
| S1 | 對話端點與金鑰（§3.1） | G1、G4；C1；事件：設全域 `OPENAI_BASE_URL` 會把照片導向不收圖片的 gpt-oss（§0 第 4 列） |
| S2 | 主迴圈推理清理（§3.2） | G2；A1、A2（A3 依 Q3）；事件：已存樣本 30/30 夾推理、W1 輸出後觸發依賴解析成功（盤查 C1） |
| S3 | 價目與健康檢查（§3.3） | G1（看得到它真的在用、花多少）；C3；事件：盤查 B6 成本記不到 |
| S4 | 測試：單元、黃金、等價（§3.4） | G2、G3；事件：盤查 C5 黃金測試是回歸網；HANDOFF §3「接線時照搬同一邏輯並以存下的模型原文做等價測試」 |
| S5 | 本機組態覆寫檔＋文件（§3.5） | G1、G3、G4；事件：§2.3 不帶覆寫重建會回到非 mock |
| S6 | eval-harness 能打常駐服務（§3.6） | G2（第 2 步量測的前提）；事件：盤查 C7 |
| S7 | 業主重建、實打、稽核、fresh verifier（§3.7） | G1～G4 |

偏離與取捨：
- **A3（工具迴圈保留推理）有條件照做**：Q3 證明 Bedrock 收 `reasoning` 欄位且真的進了 prompt ⇒ 照做；否則工具呼叫訊息也剝除（＝shim 行為，W1／R3 即在此條件下測得）。理由：把推理以標籤留在 content 回送，伺服端會把它當成最終文字而非 analysis，與 A3 的本意不符，且未經量測。
- **`exclude: true` 預設不採用（偏離 HANDOFF §2.2「可行 ⇒ 從源頭關掉」）**，理由：(1) A5 原文「The tokens are still billed and count against max_tokens」——不省費用與上限；(2) 清理器仍必要（前綴「以下」等雜字與 exclude 無關）⇒ 不省程式；(3) R1 歸因曾靠推理原文判讀模型為何選 `no_grounding`（`plan-partial-answer-gap-r3-20261018.md` §0），exclude 後評估紀錄看不到；(4) 若 Q3 可行，exclude 會讓 A3 無從照做。Q1 結果仍完整記錄；業主核可時可改選「採用 exclude」。
- **清理以「對話端點開關」控制，不以模型名分岔**：只有設了對話端點（`build_agent_provider_from_env()` 非 `None`）時，runtime 才啟用推理剝除與 JSON 擷取；未設時連進入點都不碰（plan-verifier 第 1 輪 #1：否則正式機 luna 在「原本解析失敗但可擷取」與「可解析但字串含字面 `<reasoning>`」兩種輸入下會改變行為，違反 G3）。代價：日後正式機若改用其他端點但不經此開關，清理器不生效——正式機切換屬第 4 步，切換時一併設此開關。
- **長期金鑰只限本機**（B1 原文允許探索用途）；正式機短期金鑰＋自動更新另案（列 §4）。

## 2. 第 0 步：探測（核可後、實作前；做完即丟，結果寫入 §8 執行紀錄）

位置：`~/jgb-archive/oss-wiring-20261018/probe/`（repo 外）。直接以 httpx 打 Bedrock Chat Completions 原始 HTTP（看得到 SDK 會吞掉的未知欄位）。金鑰處置（§5 F1、F14）：腳本內以固定路徑常數開檔讀入記憶體，先過與正式程式相同的格式驗證（只一行、字元限 `[A-Za-z0-9+/=._~-]`；不合格 ⇒ 只印路徑與「格式不符」後非 0 退出），放 `Authorization` 標頭；⛔ 印出、⛔ 進 argv／環境變數、⛔ 存進紀錄。每次呼叫包 `except Exception as e`，只印 `type(e).__name__` 與 status code（⛔ 印 `str(e)`、traceback）。紀錄只存請求 body、回應 status 與 body，⛔ 序列化 `response.request` 或任何標頭；紀錄目錄 `chmod 700`、腳本 `umask 077`；⛔ 開 DEBUG logging、`OPENAI_LOG`。

| Q | 問題 | 做法 | 判定 | 決定規則 |
|---|---|---|---|---|
| Q0 | 錯誤回應會不會回帶 token？（§5 待查 1） | 以明顯假的 token 字串 `invalid-probe-token` 打 1 次 | 401／403 的 body 是否含送出的 token 字串 | 含 ⇒ 服務端 `APIStatusError` 訊息一律只記類別與 status（擴大 §3.1 錯誤處理範圍）；不含 ⇒ 照 §3.1 |
| Q1 | Bedrock 是否接受 `reasoning: {"exclude": true}`？ | 同一個小題（strict json_schema、無工具）各 3 次：不帶（正對照：預期 content 有 `<reasoning>`）／`extra_body` 帶 `{"reasoning":{"exclude":true}}` | 狀態碼；200 時 content 是否仍有標籤；`usage.completion_tokens` | 照實記錄；依 §1.4 預設不採用。正對照未見標籤 ⇒ 判定「探測條件壞了」，停 |
| Q2 | 預設時推理出現在哪裡？ | Q1 不帶組的原始 JSON：列出 `choices[0].message` 所有鍵；有無 `reasoning`／`reasoning_content` | 鍵清單 | 決定清理器是否還需處理 content 標籤（預期需要） |
| Q3 | 帶推理的 assistant 訊息能否被 Bedrock 收下並進 prompt？ | 一段「使用者→assistant 工具呼叫→工具結果→再取樣」對話，assistant 訊息分三種送：(a) 不帶推理 (b) `reasoning` 欄位帶一段已知長度的推理文 (c) `reasoning_content` 欄位同文；各 2 次 | 狀態碼；`usage.prompt_tokens` 差（b／c 相對 a） | 差值 ≥ 該推理文以 tiktoken o200k 估算 token 數的 50% ⇒ 「收下並進 prompt」⇒ 工具迴圈保留推理（A3 照做）；否則工具訊息也剝除 |
| Q4 | 金鑰能否 `GET /openai/v1/models`？ | 1 次 | 狀態碼 | 200 ⇒ 健康檢查用它；否則健康檢查只驗設定（檔案可讀、端點已設），⛔ 為健康檢查花對話 token |
| Q5 | 真實形狀下雜字的型態 | 從已存 `shim_raw.jsonl` 取 10 筆 AgentOutput 請求原樣重送（題目原文只在 repo 外） | 每筆 content：標籤、前綴、後綴、空白、截斷 | 形狀全部進 §3.4 單元測試的合成樣本（不存原文進 git） |
| Q6 | gpt-oss-120b 東京區官方單價 | AWS 官方 Price List（`pricing.us-east-1.amazonaws.com` 的 AmazonBedrock offer 檔，ap-northeast-1），或渲染 Bedrock 價格頁 | 找到的列原文存檔 | 找到 ⇒ 進 `DEFAULT_PRICING`；找不到 ⇒ 不填價（成本留空，照現行），回報「未查完」，清單 #6 收窄 |

約 25 次模型呼叫（Q1 6、Q3 6、Q5 10、其餘少量）；費用照實回報（token × Q6 單價，未查得單價則只報 token）。停點：**Q0 以外**任一呼叫回 401／403 ⇒ 停、交業主（⛔ 重試或換金鑰）；5xx 只重送一次。Q5 樣本足夠：已存檔中 gpt-oss AgentOutput 請求 16 筆（2026-10-18 主會話統計）。

## 3. 做什麼（核可後）

### 3.1 S1 對話端點與金鑰

- `OpenAIProvider.__init__` 加選用參數 `base_url=None`；為 `None` 時建構呼叫與現行逐字相同（`OPENAI_TIMEOUT_S` 照舊套用）。**有給 `base_url` 時必須明確給非空 `api_key`，⛔ 退回 `os.getenv("OPENAI_API_KEY")`**（§5 F6：建構子層再擋一次）。
- `services/llm_provider.py` 新增 `build_agent_provider_from_env()`：
  - 讀 `AGENT_LLM_BASE_URL` 與 `AGENT_LLM_API_KEY_FILE`。**兩者皆未設 ⇒ 回 `None`**，`app.py` 照舊用 `get_llm_provider()`（正式機路徑，逐位不變）。
  - **只設其一 ⇒ 啟動紅（raise）**：只有端點時 ⛔ 退回 `OPENAI_API_KEY`（會把 OpenAI 金鑰送到 AWS）；只有金鑰檔時 ⛔ 送往 OpenAI 預設端點。
  - 金鑰檔不存在、不可讀、去頭尾空白後為空、**多於一行或含 `[A-Za-z0-9+/=._~-]` 以外字元** ⇒ 啟動紅；錯誤訊息只含路徑與原因代碼，⛔ 含檔案內容（§5 F1：h11 驗標頭失敗的訊息 `Illegal header value {!r}` 會帶完整 `Bearer <金鑰>`，經 `shadow.py` 的 `logger.exception` 進 `docker logs`）。
  - **已設 `AGENT_LLM_BASE_URL` 時偵測到 `OPENAI_BASE_URL` ⇒ 啟動紅**（§5 F5：SDK 在 base_url 為 None 時讀它，照片、文件、健康檢查的 OpenAI 金鑰會被送到該處）。
  - 回傳一個**新的** `OpenAIProvider(api_key=<檔案內容>, base_url=...)`，⛔ 放進 `_provider_cache`（照片、文件、健康檢查與其他呼叫者照舊走 OpenAI）。
- `app.py` `_init_agent_runtime`：`provider = build_agent_provider_from_env() or _get_llm_provider()`，同一個 provider 交 `build_runtime` 與 `ShadowRunner`（現行即共用）。啟動訊息印「對話端點：Bedrock／預設」與模型名，⛔ 印金鑰或其長度。
- 金鑰來源（本機）：Compose secret（§3.5），容器內 `/run/secrets/agent_llm_api_key`。

### 3.2 S2 主迴圈推理清理

- 清理函式放 `write_forms` 旁的共用位置（`services/agent/llm_output.py`，新檔），`parse_write_intent_content` 的推理段與 `raw_decode` 邏輯抽到這裡共用（行為不變，既有寫入意圖測試照過）。
- **開關**：`AgentRuntime` 新增建構參數 `clean_llm_output: bool = False`，經 `bootstrap.build_runtime(**runtime_kwargs)` 傳入；`app.py` 只在 `build_agent_provider_from_env()` 非 `None` 時傳 `True`（`ShadowRunner` 的工廠同樣傳）。以下兩項**只在 `clean_llm_output=True` 時執行**；`False` 時程式路徑與現行逐位相同。
- `_next_model_message` 回傳前：content 為字串且含 `<reasoning>` ⇒ 剝除所有推理段（含未閉合的開頭段：取最後一個 `</reasoning>` 之後）；剝除後寫回 `message.content`，記 `llm_output_reasoning_stripped`（`acc.violations`，與 `LLM_OUTPUT_TRUNCATED` 同管道）。不含標籤 ⇒ 不動。
- `_run_model_loop` 無 tool_calls 分支：先照現行 `json.loads(content)`；**只有失敗時**才以 `raw_decode` 逐個 `{` 取第一個能通過 `AgentOutput.model_validate` 的頂層物件，成功 ⇒ 以該物件繼續、把 `content` 換成該物件的 JSON 字串（之後四條改寫 append 的都是它），記 `llm_output_json_extracted`；仍失敗 ⇒ 照現行 SCHEMA 改寫。⇒ content 原樣可解析時（luna、黃金 28 情境）路徑逐位不變。
- 工具呼叫訊息：依 Q3 —「收下並進 prompt」⇒ 剝下的推理放進該 assistant 訊息的 `reasoning` 欄位（只在本回合 `acc.messages` 內），最終輸出產生後的下一次取樣（改寫路徑）不再帶；否則只帶剝除後 content。
- ⛔ 動截斷處置（`finish_reason=="length"` 仍只記旗標，屬第 3 步）、出口閘、Verifier、改寫預算。

### 3.3 S3 價目與健康檢查

- Q6 查得官方單價 ⇒ `DEFAULT_PRICING["openai.gpt-oss-120b-1:0"] = (prompt, completion)`，註記來源與查得日；查不得 ⇒ 不加（成本留空），回報。
- `pipeline_health_service` 新增 `_check_agent_llm`（回傳 `"name": "Agent LLM Endpoint"`；**函式內接住所有例外**，否則 `check_all_components` 外層的 `str(raw)` 會繞過固定代碼）：只在 `AGENT_LLM_BASE_URL` 有設時列入；設定判斷與金鑰讀取**重用 `build_agent_provider_from_env()`**（⛔ 另寫一套配對邏輯）；Q4 可行 ⇒ 以對話端點金鑰呼 `models.list()`；不可行 ⇒ 只驗設定。`is_core=True`（對話主路徑依賴它，與 `_check_llm` 同級）。**`error` 欄只放固定代碼、例外類別名、status code，⛔ `str(e)`**（§5 F4：`/pipeline-health` 在 `RAG_API_AUTH_ENFORCE` 預設 false 時不需認證，8100 對所有網卡發布）。未設時檢查清單與現行逐位相同。

### 3.4 S4 測試

1. 新單元測試（`tests/unit/agent/test_oss_wiring_req.py`）：
   - provider：兩者未設 ⇒ `None`；只設其一 ⇒ raise；金鑰檔空／不存在／多行／含非法字元（含中間 CR、空白）⇒ raise 且訊息不含檔案內容；同時設 `OPENAI_BASE_URL` ⇒ raise；`OpenAIProvider(base_url=..., api_key=None 或 "")` ⇒ raise；設妥 ⇒ `base_url` 正確、不在 `_provider_cache`、`get_llm_provider()` 回傳的仍是原實例。
   - 清理器（合成樣本，形狀取自 Q5 與已存樣本，⛔ 原文）：推理段＋JSON、前綴「以下」、後綴雜字、多段推理、未閉合推理、去標籤後為空、灌空白、推理段內含 JSON 樣字串（不得被搶先解析）。
   - 開關關閉（`clean_llm_output=False`，正式機現況）：(i)「解析失敗但可擷取」的輸出（前綴「以下」＋合法 JSON）⇒ 仍走 SCHEMA 改寫，messages 與輸出和現行逐位相同；(ii)「可解析但字串欄位含字面 `<reasoning>`」⇒ 內容原樣不動；(iii) violations 不出現兩個新旗標。
   - 主迴圈（開關開啟；FakeProvider，照 DSP-022 斷言最後一則 user 訊息）：帶推理的最終輸出 ⇒ 一次通過、messages 不含 `<reasoning>`；第一次雜字無法解析 ⇒ 改寫時 append 的 assistant 內容不含推理；工具呼叫訊息依 Q3 結論斷言。
   - 健康檢查：未設時檢查清單不變；設妥時多一項；以會拋出含金鑰字串例外的假 client 測，`error` 欄只含固定代碼與類別名。
2. 黃金測試：`_final_noisy` 輔助＋新增 1 情境（推理段＋前綴包住的最終輸出；**該情境以 `clean_llm_output=True` 建 runtime**，既有 28 情境維持預設 `False`），`AGENT_GOLDEN_REGEN=1` 重產 fixture；**既有 28 情境的 fixture 內容逐位不變**（以 `git diff` 只見新增鍵證明）。
3. 等價測試（repo 外，`~/jgb-archive/eval-harness/tests/`）：對已存 Bedrock 原始輸出逐筆比對「shim 處理後再 `json.loads`」與「新清理器＋解析」——shim 成功者新路徑必須得到相同物件；shim 失敗者記錄新路徑結果（可多救回，不可少）。
4. 全量 `scripts/run-tests.sh`：失敗 ⊆ 第 0 步在 HEAD 重抓的基線。

### 3.5 S5 本機組態覆寫檔與文件

- 新檔 `docker-compose.bedrock-local.yml`（進 repo，不含任何金鑰值）：只覆寫 rag-orchestrator——`AGENT_MODEL=openai.gpt-oss-120b-1:0`、`AGENT_REASONING_EFFORT=low`、`AGENT_LLM_BASE_URL=https://bedrock-runtime.ap-northeast-1.amazonaws.com/openai/v1`、`AGENT_LLM_API_KEY_FILE=/run/secrets/agent_llm_api_key`、**`USE_MOCK_JGB_API="true"`（寫死，本機接 Bedrock 時一律 mock）**、`AGENT_ASSISTANT_KEY_IDS: ${AGENT_ASSISTANT_KEY_IDS:-}`（§5 F16：讓「站內幫手金鑰缺 user_id ⇒ 400」這道閘與正式機同樣可開；值由業主在 `.env` 填）；`secrets: agent_llm_api_key: file:` 以**絕對路徑**指向業主決定的金鑰檔位置（§6 決定 1；§5 F15、待查 3：`~` 是否展開未查，⛔ 用）。金鑰檔 ⛔ 放 repo 或 `./rag-orchestrator` build context（Dockerfile 為 `COPY . .`）。
- 撤銷／輪替程序（寫進 DECISIONS 與覆寫檔註解）：AWS console 對該金鑰 Deactivate ⇒ 換檔 ⇒ `up -d --force-recreate rag-orchestrator`（金鑰只在啟動時讀一次；§5 F15）。
- `docker-compose.prod.yml` **不改**（正式機與現行本機啟動方式逐位不變）。
- 本機啟動：`docker compose -f docker-compose.prod.yml -f docker-compose.bedrock-local.yml up -d --build rag-orchestrator`（業主手跑）。
- 文件（同一片更新）：`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` §6 環境變數表、`docs/guides/deployment/ENVIRONMENT_VARIABLES.md`、`.kiro/steering/tech.md`（「對話回合：`AGENT_MODEL`→`OPENAI_MODEL`」那行）、`.kiro/steering/answer-eval-and-probe.md` 收尾稽核重建指令（接 Bedrock 時加覆寫檔）。`docs/deployment-runbook.md` 有他窗未提交修改 ⇒ ⛔ 本片不改，列 §4。
- `.claude/DECISIONS.md` 新增一條：對話端點與金鑰分離（檔案金鑰、兩者成對、與 `OPENAI_BASE_URL` 互斥）；本機長期金鑰的條件（§5 F10）：到期 ≤90 天、IAM user 只開 gpt-oss-120b／ap-northeast-1、外洩即 Deactivate＋重建、檔案 `~/.config/aichatbot/`（目錄 700、檔 600）且刪除 Downloads 原檔、⛔ 用於正式機（正式機另議短期金鑰）。

### 3.6 S6 eval-harness 打常駐服務

- `harness/runner.py` 加 `--target resident`（預設 `eval` 行為逐位不變）。resident 模式的完整差異（plan-verifier 第 2 輪 #2）：
  1. **開頭先跑 §2.3 的 mock 檢查，非 `True` 即非 0 退出**（大聲失敗）。
  2. ⛔ 呼叫 `start(arm)`／`collect_and_stop`（不啟停容器、不收 shim；常駐服務由業主起）。
  3. 就緒檢查：改以 `/api/v1/system/pipeline-health` 回應中 `Agent LLM Endpoint` 為 `healthy`、且 `docker logs aichatbot-rag-orchestrator` 含「agent runtime 已初始化」為準（⛔ 讀 `bedrock-eval-svc`）。
  4. ⛔ 跑 `effective_config`（它讀 shim 紀錄）；模型證據改由 `aichatbot_admin` 的 `usage_events.model_breakdown` 依各回合 `trace_id`／時間窗查得，`meta["effective"]["models"]` 由此填入，同樣檢查須含 `openai.gpt-oss-120b-1:0`，不含即非 0 退出。
  5. 服務網址 `http://localhost:8100/mcp/`、`decision_snapshot` 查 `aichatbot_admin`。
  6. 金鑰：`mcp_client.KEY` 於 resident 模式改讀 `~/jgb-archive/eval-harness/secrets/resident-key`（`M.KEY = …`，`post` 於呼叫時才讀 `KEY`）。
  7. harness 單元測試新增：resident 模式（以假 `R.turn`、假 DB 查詢、假 mock 檢查）跑完後寫出 `records.jsonl` 與 `meta`、未呼叫 `start`／`collect_and_stop`；mock 檢查回 `False` 時非 0 退出且未送任何回合。
- 身分金鑰（§5 F2、F11、F12）：以一支 repo 外腳本在本機 `aichatbot_admin` 建一把測試金鑰——腳本內 `secrets.token_urlsafe(32)` 產生明文、直接寫進 `~/jgb-archive/eval-harness/secrets/resident-key`（umask 077、檔 600），同一個 `INSERT INTO api_keys` 帶 `name='eval-harness-local-oss-wiring'`、`key_hash`（`services/api_key_auth.hash_key` 同法）、`key_prefix=plain[:8]`、`is_internal=true`（量測中途不被額度擋、不混入 vendor 4 用量統計）、**`vendor_ids='{4}'`**（harness 身分固定 vendor 4；⛔ NULL＝不限業者）；明文 ⛔ 進 argv、stdout、對話；只回報 id。⛔ 走後台 `create_api_key`（需未授予的 admin 憑證、明文出現在 HTTP 回應、且設不了 `is_internal`／`vendor_ids`）。
- 撤銷：第 2 步量測結束時 `UPDATE api_keys SET is_active=false WHERE id=<id> AND name LIKE 'eval-harness-local-%'` 並刪金鑰檔（停用不刪除，保留 `last_used_at` 稽核；`api_keys` 無到期欄位）。
- 評估容器腳本 `~/jgb-archive/eval-harness/start_eval_svc.sh` 的 B 組（`export OPENAI_API_KEY="$(cat ~/Downloads/…)"`＋全域 `OPENAI_BASE_URL`）**停用**：改為印「已由常駐服務取代，見本計畫」後非 0 退出（§5 F8：金鑰進環境變數、照片等也會被導向 Bedrock；搬檔後 `export X="$(cat 不存在)"` 在 `set -e` 下仍回 0）。A 組不動。
- harness 單元測試照跑。

### 3.7 S7 收尾（依序）

1. 業主依 §6 決定放好金鑰檔，在提示列手跑 §3.5 的本機啟動指令。
2. `curl localhost:8100/api/v1/health` 回 200（steering 收尾稽核；該端點只做 DB `SELECT 1`）；另查 `curl localhost:8100/api/v1/system/pipeline-health`，回應 `components` 中 `name`＝`Agent LLM Endpoint` 那項的 `status`＝`healthy`。
3. mock 檢查回 `True`（§2.3 指令）——未回 `True` ⇒ 停，⛔ 跑任何對話。
4. 實打（`--target resident`，不加 shim）：清單 #1～#3 的題目；清單 #6 的容器內組態檢查。
5. `make audit` OVERALL: PASS（容器與工作樹一致後）。
6. fresh `verifier` 對照業主原話＋凍結清單＋本計畫宣稱。

## 4. 不做（理由）

- 正式機切換、正式機短期金鑰與自動更新（G3：本地都處理好才線上換；B1 已記目標形態，切換時另案）。
- 截斷處置、業者端敏感題防線、推論有無、`ask_target` 漏填（HANDOFF §1.4 第 3 步：依第 2 步量測結果才修）。
- 回應品質全量量測與門檻（第 2 步，DSP-087）。本步清單只驗「接線不讓品質變差」。
- 照片與文件換模型、後台三工具、embedding（HANDOFF §1.2）。
- **照片經 `/mcp` 的端到端實打**（plan-verifier 第 2 輪 #1）：`/mcp` 收照片只收 `image_urls`，須 https、主機在 `IMAGE_URL_ALLOWLIST`（預設只有 JGB 主機 `relay.jgbsmart.com`）且帶 `exp`，mock 只包 `JGBSystemAPI`（DSP-024）管不到這條；本機 jpg 送不進去。本步改以容器內組態檢查證明照片 client 未被導向 Bedrock（清單 #6）；端到端照片回合留第 2 步，以 S3-live 先例的程式內驅動（`~/jgb-archive/assistant-demo-20261014/s3_live_driver.py`，替換 `_image_fetch_one`）做。
- LLM API 錯誤（逾時以外）的攔截與轉人（盤查發現 `_agent_turn` 只處理 `asyncio.TimeoutError`；既有缺口、非本片引入，列待查）。
- Verifier 模式值域爭議（DSP-083）、DSP-080 切換條件改定（第 4 步）。
- `docs/deployment-runbook.md`（他窗未提交修改；本片收尾時在交接檔記一行待補）。

## 5. 安全審查（security-reviewer，唯讀，2026-10-18）

主會話抽查：`create_api_key` 的 INSERT 只有 name／key_hash／key_prefix／description（`grep -n "INSERT INTO api_keys" knowledge-admin/backend/app.py`）；`vendor_ids` NULL＝不限（`20260904_api_keys_agent_scope.sql` 註解）；`shadow.py` 有 `logger.exception`——三項皆對得上。

| # | 發現（摘要） | 嚴重度 | 處置 |
|---|---|---|---|
| F1 | 金鑰檔中間含非法字元時，h11 例外訊息帶完整 `Bearer <金鑰>`，經 traceback／`logger.exception` 外洩 | P2 | FIX：§3.1 載入驗證整檔格式；§2 探測同驗證、例外只印類別名 |
| F2 | 測試金鑰範圍未定；後台工具做不出 `is_internal`、`vendor_ids` NULL＝不限 | P2 | FIX：§3.6 明定 `is_internal=true`、`vendor_ids='{4}'` |
| F3 | 驗收 #8 正對照沒驗到金鑰樣式檔本身（空檔／尾 CR ⇒ 靜默 0） | P2 | FIX：清單 #8 加樣式檔前置檢查與同檔包夾正對照 |
| F4 | 健康檢查 `str(e)` 會回給不需認證的端點 | P3 | FIX：§3.3 只放固定代碼 |
| F5 | 有人設 `OPENAI_BASE_URL` 時 OpenAI 金鑰送往該處 | P3 | FIX：§3.1 互斥、啟動紅；清單 #8 加變數名稱檢查 |
| F6 | `OpenAIProvider.__init__` 會退回讀 `OPENAI_API_KEY` | P3 | FIX：§3.1 建構子層擋 |
| F7 | 清單 #8「環境變數名稱無承載金鑰者」照字面不成立 | P3 | FIX：清單 #8 改寫 |
| F8 | `start_eval_svc.sh` B 組做法較差、搬檔後匯出空金鑰 | P3 | FIX：§3.6 停用 B 組 |
| F9 | 內部金鑰免額度＋無價時成本 0 ⇒ 花費上限幾乎失效；8100、5432 對所有網卡發布（既有） | P3 | 部分 FIX：§3.6 量測結束停用金鑰、§6 決定 4 AWS Budgets 警示（業主做）；8100 綁 127.0.0.1 DEFER——既有暴露、非本片引入，且 compose `!override` 支援待查 |
| F10 | 長期金鑰本機可用，但要附條件 | P3 | FIX：§3.5 DECISIONS 條件；§6 決定 1 |
| F11 | `api_keys` 無到期欄位 | P3 | FIX：§3.6 撤銷時點與做法 |
| F12 | 建立途徑建議 SQL（後台需未授予憑證、明文進 HTTP 回應） | P3 | FIX：§3.6 |
| F13 | DB 傾印不落地；比對範圍漏探測紀錄、harness 輸出、attempt log | P3 | FIX：清單 #8 |
| F14 | 探測紀錄目錄權限、不序列化標頭、不開 DEBUG | P4 | FIX：§2 |
| F15 | Compose file secret 是 bind mount、uid／mode 被忽略；輪替須重建 | P4 | FIX：§3.5 絕對路徑、撤銷程序 |
| F16 | 覆寫檔沒設 `AGENT_ASSISTANT_KEY_IDS` | P4 | FIX：§3.5 |

待查（無證據、不評嚴重度）：(1) 401 body 是否回帶 token ⇒ 第 0 步 Q0；(2) 容器內 secret 檔擁有者與權限 ⇒ S7 只印 `stat -c '%a %U'`；(3) `secrets.file` 是否展開 `~` ⇒ 用絕對路徑迴避；(4) macOS grep 空樣式檔行為 ⇒ 清單 #8 前置檢查 `test -s` 已先擋；(5) MCP SDK 對工具例外是否寫 traceback ⇒ F1 的格式驗證已在源頭擋；(6) 金鑰實際到期日與 IAM policy ⇒ §6 決定 1（業主看 console）；(7) `turns_per_hour` 單位、`!override` 支援 ⇒ 隨 F9 DEFER。

## 6. 待業主決定（核可時一併回覆）

1. 金鑰檔放哪與長期金鑰條件：建議移到 `~/.config/aichatbot/bedrock-api-key`（目錄 700、檔 600），刪除 `~/Downloads` 原檔與垃圾桶；請在 AWS console 確認這把金鑰到期日 ≤90 天、IAM user 只開 gpt-oss（業主自己做；覆寫檔以絕對路徑指向）。
2. `exclude: true`：建議不採用（§1.4 理由）；或改選「採用」。
3. eval-harness 身分金鑰：建議依 §3.6 由腳本在本機 `aichatbot_admin` 建 `eval-harness-local-oss-wiring`（`is_internal=true`、`vendor_ids={4}`），第 2 步結束停用；或業主自行提供。
4. AWS Budgets 警示（§5 F9）：建議在 AWS 帳號為 Bedrock 設月預算警示（業主做；金額由業主定）。

## 7. 擁有檔案、執行分工、回退、用量

- **安全相關（security-executor）**：`services/llm_provider.py`、`app.py` 的 provider 選擇、`services/pipeline_health_service.py`、`docker-compose.bedrock-local.yml`、eval-harness 測試金鑰建立腳本與 `start_eval_svc.sh` B 組停用、第 0 步探測腳本的金鑰載入段。
- **主會話**：`services/agent/llm_output.py`（新）、`services/agent/runtime.py`、`services/agent/write_forms.py`（抽出共用，行為不變）、`services/usage_metering.py`、測試、黃金 fixture、文件、DECISIONS、eval-harness runner 參數化。
- 會改的既有測試：`tests/fixtures/agent/pipeline_golden.json`（只新增 1 鍵）；`test_pipeline_golden_req.py`（加 1 情境）。審查確認不需改：`test_output_cap_and_ask_target_desc_req.py`（截斷旗標不變）、`test_llm_provider_timeout_req.py`（`base_url=None` 時建構不變；若斷言建構參數逐字，則同步改並列執行紀錄）、寫入意圖相關測試（抽出共用後行為不變）。
- 回退：`git revert`；本機改回不帶覆寫檔重建。正式機不受影響（未設兩個新變數 ⇒ 路徑逐位不變）。
- 用量回報：收尾回報子代理 token（任務通知加總）＋ Bedrock 探測與實打費用（token × 官方單價，估算標明）。截至第 0 步完成：子代理 1,698,176 token（核可前 1,593,993＋探測 104,183）；Bedrock API 估 USD 0.0224。⛔ token 上限當停點。
- 停點（看結果）：Q0 以外任一探測呼叫回 401／403；清單任一項未過；mock 檢查非 `True`；fresh verifier 非 CONFIRMED ⇒ 停、交業主。

## 8. 審查處置與執行紀錄

### 8.1 plan-verifier 第 1 輪（第 2 稿，REVISE，3 條 substantive）

| # | 摘要 | 接點 | 處置 |
|---|---|---|---|
| 1 | 清理器與擷取未掛開關，正式機 luna 在兩種輸入下行為改變，G3「逐位不變」不成立 | #3 開關回退 | FIX（選 (a)）：§3.2 `clean_llm_output` 開關、§1.4 改寫、附錄 #3／#5、§3.4 加關閉時兩種輸入的測試 |
| 2 | 健康檢查觀察點錯：`/api/v1/health` 只做 `SELECT 1` | 非接點類 | FIX：§3.7 第 2 步、清單 #9 改看 `/api/v1/system/pipeline-health`（主會話已核：`grep -n "SELECT 1" rag-orchestrator/app.py`） |
| 3 | 缺終點指標 | 非接點類 | FIX：開頭加終點指標 0／15 → ≥12／15（主會話重新統計已存原文） |
| 待查 1 | Q0 故意取 401 與停點衝突 | — | FIX：停點改「Q0 以外」 |
| 待查 2 | 照片成本在 `openai_cost_tracking`、不在 `model_breakdown` | — | FIX：清單 #6 寫明兩張表 |
| 待查 3 | B1 用詞「開發」原文無 | — | FIX：改「探索用途」 |
| 待查 4 | C2「以下」無出處 | — | FIX：補記憶檔與 HANDOFF 出處 |
| 待查 5 | Q5 樣本是否 ≥10 | — | 已查：16 筆 |
| 待查 6 | 等價測試「相同物件」定義 | — | FIX：清單 #4 定義 |

接點類輪：是（#1 對到接點 #3）。

### 8.2 plan-verifier 第 2 輪（第 3 稿，REVISE，2 條 substantive；第二次自動 REVISE ⇒ 主會話逐條處置，記新的審查時點，只送一次收尾審查）

主會話核對：`runner.py` `run_turns` 確實呼叫 `start(arm)`、`wait_index_ready()`、`collect_and_stop`、`effective_config`，`CONTAINER = "bedrock-eval-svc"`；`mcp_client.py` `KEY` 於 import 時讀 `s1-test-key`、`post` 呼叫時用 `KEY`；`image_fetch.py` `DEFAULT_IMAGE_URL_ALLOWLIST` 只有 `relay.jgbsmart.com`——兩條皆成立。

| # | 摘要 | 接點 | 處置 |
|---|---|---|---|
| 1 | 清單 #6 照片回合照寫法跑不了（白名單只有 JGB 主機、mock 管不到；harness 無照片參數） | 非接點類 | 收窄：#6 改為容器內組態檢查（照片 client 的 base_url 為 OpenAI、`OPENAI_BASE_URL` 未設、對話 provider 為 Bedrock），收窄段與 §4 寫理由；端到端照片回合留第 2 步用 S3-live 程式內驅動 |
| 2 | `--target resident` 照 §3.6 範圍跑不完（綁評估容器、shim、`s1-test-key`） | 非接點類 | FIX：§3.6 列出 resident 模式 7 點完整差異與單元測試 |
| 待查 1 | #7「等於 token × 單價」在回合含其他模型時不成立 | — | FIX：清單 #7 改看 `model_breakdown` 中 gpt-oss 鍵，`est_cost_usd` 為空時須列缺價鍵 |
| 待查 2 | 黃金新情境須以開關開啟的 runtime 建 | — | FIX：§3.4 第 2 點寫明 |
| 待查 3 | `_check_agent_llm` 須內部接住所有例外 | — | FIX：§3.3 寫明 |

### 8.3 收尾審查（第 4 稿，fresh plan-verifier）：**READY**（2026-10-18）

### 8.4 業主核可（2026-10-18）

- 「核可、開始」；§6 決定 2＝「不採用，靠清理器」；決定 3＝「由腳本建前綴測試金鑰」。決定 1（金鑰檔位置與到期日）、決定 4（AWS Budgets）為業主自行操作，未回覆。
- 驗收清單第 4 稿自此凍結；之後收窄須再經業主核可。

### 8.5 第 0 步探測結果（2026-10-18；security-executor 執行，主會話抽查 q1／q3／q4 原始紀錄一致）

證據：`~/jgb-archive/oss-wiring-20261018/probe/`（`summary.json`、`q0`～`q5.jsonl`、`q6_price_raw.json`；目錄 700）。HEAD `369155df`；單元基線 9 失敗／4,642 通過（`~/jgb-archive/oss-wiring-20261018/baseline_unit_369155df.txt`）。

| Q | 結果 | 依決定規則 |
|---|---|---|
| Q0 | 假 token 回 401，body 不含送出的 token（`Invalid API Key format: Must start with pre-defined prefix`）——只驗到「前綴格式錯」這條；前綴正確但無效的金鑰未測 | 照 §3.1（不擴大）；未測部分列待查（既有行為：openai 例外照舊上拋，§4 已列 API 錯誤攔截不在本步） |
| Q1 | 帶 `reasoning: {"exclude": true}` 回 **200 但被忽略**：3／3 content 仍有 `<reasoning>`（正對照不帶組 3／3 有）；usage 無 `completion_tokens_details` | 業主「Bedrock 是否接受 exclude」的答案：**收下不報錯、但不生效**；與業主決定 2「不採用」一致 |
| Q2 | `message` 鍵只有 `content`／`refusal`／`role`，無 `reasoning`、`reasoning_content`；推理以標籤夾在 content | 清理器需處理 content 標籤 |
| Q3 | (b) `reasoning`、(c) `reasoning_content` 欄位的 prompt_tokens 與 (a) 相同（195），Δ＝0；對照 (d) Δ＝389 ⇒ 比值 0.0 | **未進 prompt ⇒ 工具呼叫訊息也剝除**（＝shim 行為；A3 無法照做，理由：Bedrock Chat Completions 不收推理欄位） |
| Q4 | `GET /models` 回 404 `<UnknownOperationException/>` | 健康檢查只驗設定（端點已設、金鑰檔格式合格），⛔ 呼叫模型 |
| Q5 | 10 筆真實 AgentOutput 重送：10／10 恰一對推理標籤；`</reasoning>` 到 `{` 的前綴 10／10 為空（本次未見「以下」）；stop 9 筆去標籤後 `json.loads` 全成功；length 1 筆為灌空白（JSON 中段起 14,486 字元空白）無法擷取 | 單元測試合成樣本含上列形狀＋「以下」前綴（2026-10-17 實測曾出現）；灌空白截斷屬第 3 步 |
| Q6 | AWS Price List `AmazonBedrock` offer（版本 `20261016210806`）ap-northeast-1：on-demand 標準 輸入 `0.00018`、輸出 `0.00073` USD／1K tokens（SKU `DFN5T4HYJPM5CGU9`、`FCYZ5PQ2VKGXJ3DH`）；正對照同檔 claude／nova 118 列 | `DEFAULT_PRICING["openai.gpt-oss-120b-1:0"] = (0.18, 0.73)`（USD／百萬）；另有同價的 `mantle-*-standard` 列，計入哪組未判定（同價，不影響） |

偏離：Q3 判定改用對照組 (d) 量 token（本機無 tiktoken，計畫原寫 o200k 估算）；探測改用標準庫 `urllib`（本機 python3 無 httpx）。
用量：Bedrock 26 次呼叫，prompt 106,353＋completion 4,440 token，估 USD 0.0224（標準層單價）；子代理 security-executor 104,183 token。

### 8.6 S1～S7 執行紀錄（2026-10-18；AUTO 模式，未 commit）

證據目錄：`~/jgb-archive/oss-wiring-20261018/`（700；題目與回答原文不進 git）。

| 片 | 結果 | 證據 |
|---|---|---|
| S1 | security-executor 依凍結契約完成 `llm_provider.py`（`build_agent_provider_from_env` 等）、`app.py` `_init_agent_runtime`、`pipeline_health_service._check_agent_llm`、覆寫檔、測試金鑰腳本（`api_keys.id=107`，`is_internal=true`、`vendor_ids={4}`）、`start_eval_svc.sh` B 組停用；主會話抽查 diff 與契約一致 | `git diff -- rag-orchestrator/services/llm_provider.py rag-orchestrator/app.py rag-orchestrator/services/pipeline_health_service.py` |
| S2 | `services/agent/llm_output.py`（新）＋`runtime.py` `clean_llm_output` 開關＋`write_forms.py` 改用共用函式 | 同上 |
| S3 | `DEFAULT_PRICING["openai.gpt-oss-120b-1:0"] = (0.18, 0.73)`（§8.5 Q6）；健康檢查只驗設定 | `grep -n "gpt-oss-120b" rag-orchestrator/services/usage_metering.py` |
| S4 | `tests/unit/agent/test_oss_wiring_req.py` 33 條全過；黃金新增 `oss_reasoning_cleaned`，既有 28 鍵逐位不變；全量單元 4,676 通過／9 失敗，9 條皆在第 0 步基線內 | `unit_after_s1s2.txt`、`baseline_unit_369155df.txt` |
| 等價（清單 #4） | 已存 Bedrock 原文 AgentOutput 15 則：舊路徑 12／15、新路徑 12／15、救回 0、不一致 0；WriteIntent 14 則新舊差異 0 | `equivalence_20261018.txt` |
| S5 | 覆寫檔與四份文件、DECISIONS DSP-090 | `docker-compose.bedrock-local.yml` |
| S6 | harness `--target resident`＋`TestResident` 4 條（harness 測試共 20 條 OK） | `~/jgb-archive/eval-harness/harness/runner.py` |
| S7 實打 | 37 回合（P 30、R 3、D 3、S1 1），error 0：#1 `model_breakdown` 鍵 37／37 皆 `openai.gpt-oss-120b-1:0`、容器只掛 `/run/secrets/agent_llm_api_key`；#2 answer 與 `usage_events` 列 `<reasoning`／`</reasoning>` 0（正對照：`llm_output_reasoning_stripped` 同法命中 31 列、各回合首字 37／37）；#3 P `budget_exhausted` 0／30、`llm_output_reasoning_stripped` 32 次；#7 37 列 `est_cost_usd` 全非空，合計 USD 0.076289、gpt-oss token 391,542 | `resident2/analysis.txt` |
| S7 #6 | 照片、文件 client 主機 `api.openai.com`；對話 provider 主機 Bedrock；環境變數名稱無 `OPENAI_BASE_URL` | `s7_item6_hosts.txt`、`s7_env_names_after.txt` |
| S7 #8 | 前置與同檔正對照通過；`docker inspect` 0、`docker logs`（2,434 行）0、`pg_dump aichatbot_admin` 串流 0（正對照同法 `llm_output_reasoning_stripped` 31）、證據目錄檔 0（正對照 15 檔）；`AGENT_ATTEMPT_LOG_PATH` 未設；環境變數名稱無 `AGENT_LLM_API_KEY`、`AWS_BEARER_TOKEN_BEDROCK`；金鑰檔容器內 `600 root` | 指令輸出只含計數 |

**偏離 §3.5（業主核可）**：重建後首輪 36 回合全回「Unknown tool: agent.turn」——`docker-compose.prod.yml` 預設 `AGENT_TURN_ENABLED=false`，計畫隱含「常駐服務 agent.turn 已開」的前提不成立。覆寫檔補 9 鍵照正式機值（`AGENT_STAGE` M1、`AGENT_TURN_ENABLED`、`AGENT_WRITE_TOOLS_ENABLED`、`AGENT_VERIFIER_MODE=grounding_observe`、`AGENT_BUDGET_TOOL_CALLS=3`、`AGENT_BUDGET_DEADLINE_S=20`、`AGENT_TURN_TIMEOUT_S=90`、`UVICORN_WORKERS=1`、`JGB_MOCK_FIXTURE` vendor 4 示範資料）；業主「照建議改 允許修改」後重建。失敗首輪紀錄留在 `resident/`。

**清單外觀察（不阻擋、未處置）**：`pipeline-health` 的「Agent」元件為 unhealthy，紅旗 `enforce_off_with_mcp_traffic`——本機未設 `RAG_API_AUTH_ENFORCE`（`docker-compose.prod.yml` 預設 `false`），該旗只供遙測、`/mcp` 服務層閘無條件生效（`services/agent/mcp_facade.py` `_enforce_flag_is_on`）；本次 diff 未觸及。

**延後**：`AGENT_LLM_BASE_URL` 未強制 https（設定者即業主、覆寫檔寫死 https；後續加固）；§8.5 Q0「前綴正確但無效的金鑰」回應未測（待查）；測試金鑰 id 107 於第 2 步量測結束時停用並刪檔（§3.6）。

**用量**：子代理 token 合計 1,890,651（本工作線至 S1 executor 收件止，不含收尾 verifier）；Bedrock 探測 USD 0.0224＋實打 USD 0.076289（`usage_events.est_cost_usd` 合計，標準層單價）。

## 附錄：接點盤查清單八項（`.kiro/steering/plan-touchpoint-checklist.md`）

| # | 接點 | 證據（可 grep 的符號＋路徑） | 不適用理由 |
|---|---|---|---|
| 1 | 插入點 | 推理剝除：`AgentRuntime._next_model_message` 回傳 `choice.message` 之前、`LLM_OUTPUT_TRUNCATED` 記錄之後；JSON 擷取：`_run_model_loop` 無 tool_calls 分支 `json.loads(content)` 失敗的 except 內、`acc.counters.rewrites += 1` 之前（`rag-orchestrator/services/agent/runtime.py`）；provider 選擇：`app.py` `_init_agent_runtime` 的 `provider = _get_llm_provider()` 處。順序契約：W1 插入點註解「`model_validate` 成功之後、`handoff_dict`／T2／V2／Verifier 之前」不變，擷取成功的物件同樣走這條 | — |
| 2 | 狀態生命週期 | 工具迴圈保留的推理只存在本回合 `acc.messages`（`TurnAccumulator`，回合結束即丟，不持久）；不新增會話狀態 ⇒ 不登記 `KEY_SPECS`（`grep -n "KEY_SPECS" rag-orchestrator/services/agent/agent_session.py`） | 無新會話狀態 |
| 3 | 開關回退 | `AGENT_LLM_BASE_URL`／`AGENT_LLM_API_KEY_FILE` 未設 ⇒ `build_agent_provider_from_env()` 回 `None`、走 `get_llm_provider()`，且 `AgentRuntime(clean_llm_output=False)` ⇒ 推理剝除與 JSON 擷取都不執行（新單元測試覆蓋「解析失敗但可擷取」「可解析且含字面 `<reasoning>`」兩種輸入逐位同現行）； 黃金 28 情境 fixture 逐位不變（`tests/unit/agent/test_pipeline_golden_req.py` `test_golden_matches_fixture`）；strict schema `_agent_output_response_format()` 不改 | — |
| 4 | 計量與觀察紀錄 | `usage_metering.add_llm_usage(self._model, ...)` 照記，模型名為 `openai.gpt-oss-120b-1:0`、依 `DEFAULT_PRICING` 算價；新旗標 `llm_output_reasoning_stripped`、`llm_output_json_extracted` 走 `acc.violations`→`trace.violations`（同 `LLM_OUTPUT_TRUNCATED`）；`_emit_attempt` 只記 `raw_len`，推理不進 attempt log；推理不進 trace、`decision_snapshot`、對話紀錄（清單 #2 驗） | — |
| 5 | 出口路徑 | 擷取成功 ⇒ 照常走 T2／V2／Verifier／出口閘；擷取失敗 ⇒ 照現行 SCHEMA 改寫→`build_fixed("budget_exhausted")`；`EXIT_GATES` 順序不變（`tests/unit/agent/test_pipeline_order_req.py`）；截斷仍只記旗標。⚠️ 開關開啟時行為改變只在「原本解析失敗」的路徑：原本走改寫或固定轉人，現在可能直接作答（這正是目標）；開關關閉時無任何改變 | — |
| 6 | 鎖住原句的既有測試 | `tests/fixtures/agent/pipeline_golden.json`、`test_pipeline_golden_req.py`（新增情境）；`test_llm_provider_timeout_req.py`（建構參數）；寫入意圖解析測試（`grep -rln "parse_write_intent_content" rag-orchestrator/tests`）；`test_output_cap_and_ask_target_desc_req.py`（截斷旗標） | — |
| 7 | 既有紀律與決議 | DSP-022（FakeProvider 測試須斷言最後一則 user 訊息）；DSP-024（mock 只在 `JGBSystemAPI` 邊界、compose 預設 true「部署必查」——覆寫檔寫死 true 與之相容）；DSP-075（正式機 luna，未設新變數不變）；DSP-080（方向 gpt-oss，切換條件不在本片）；DSP-085（寫入由程式掌握——意圖呼叫共用同一 provider，不另開）；DSP-086（只量 gpt-oss）；`requirements.md` Requirement 11 第 2 條「不在日誌、計量、回答中出現金鑰或 env 內容」 | — |
| 8 | 受影響文件 | `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` §6（`grep -n "AGENT_MODEL" docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`）、`docs/guides/deployment/ENVIRONMENT_VARIABLES.md`、`.kiro/steering/tech.md`、`.kiro/steering/answer-eval-and-probe.md`；`docs/deployment-runbook.md` 他窗佔用 ⇒ 延後（§4） | — |
