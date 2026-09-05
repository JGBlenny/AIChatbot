# 研究記錄：agentic-mcp-orchestration

> 建立時間：2026-09-04T17:51:48+0800
> 目的：記錄 design 前的技術調查、架構決策、相依性分析。發現流程：full（外部 API／服務、新技術棧、複雜狀態、資料遷移、效能、安全六項複雜度指標中有 5 個「是」）。

## 摘要

### 調查範圍
MCP Python SDK（server／client／ASGI 掛載／授權／結構化輸出／錯誤）、OpenAI Chat Completions 工具呼叫契約與 Responses API 的內建 MCP 工具、既有程式的整合點（validation_gap.md 三個 scout）、token 計數依賴、容器執行環境。

### 關鍵發現
- `mcp` 2.1.1（PyPI）可用，Python ≥3.10；容器為 3.11.16。`MCPServer`＋`@mcp.tool()`，`streamable_http_app()` 可 `Mount` 進既有 FastAPI，但**主 app lifespan 必須進 `mcp.session_manager.run()`**，否則首請求 `RuntimeError: Task group is not initialized`。
- 工具回傳型別註解自動成 `output_schema`（BaseModel／TypedDict／dataclass 不包裝；scalar 包 `{"result": …}`），回傳前**驗證**；`ToolError` 訊息會到模型端，未捕捉例外訊息被遮罩為 `Error executing tool <name>`（內部細節不外洩）；輸入依 schema 先驗、不合即 `is_error=True`。
- 授權：`TokenVerifier.verify_token(token) -> AccessToken | None`＋`AuthSettings(required_scopes=[…])` 成對傳給 `MCPServer(...)`；handler 內 `get_access_token()` 取 `client_id／scopes／subject／claims`。
- OpenAI Chat Completions：`tools[].function{name, parameters, strict}`、`tool_choice ∈ {"none","auto","required", {"type":"function","function":{"name"}}}`、`parallel_tool_calls: bool`、assistant `tool_calls[].{id, function.name, function.arguments}`、`role:"tool"` 訊息帶 `tool_call_id`；`response_format={"type":"json_schema","json_schema":{"schema","strict":true}}`。Responses API 有內建 `"type":"mcp"` 工具（需 `server_url` 對 OpenAI 可達或 Secure MCP Tunnel，每請求帶 `authorization`），線上在 bastion 後 ⇒ 不當生產路徑。
- 既有可沿用資產與 13 項缺口見 validation_gap.md；`tiktoken` 0.14.0 可裝、容器未裝。

## 研究主題

### 主題 1：MCP server 掛進 FastAPI 與身分注入
**調查問題**：工具伺服器要不要獨立程序？身分怎麼進工具而不經模型？
**研究方法**：官方文件（run/asgi、run/authorization、handlers/context）、現有程式（`app.py` lifespan、`chat.py` 入口）。
**發現**：`app.py` 已有 `@asynccontextmanager lifespan` 建 `db_pool` 與各 service，加一行 `async with mcp.session_manager.run()` 即可同 app 掛載；`Context` 只給請求層資料（headers／session／progress），身分要從 `get_access_token()` 的 claims 或由呼叫端明碼傳入。
**結論**：工具以純函式 registry 實作，接受 `Identity` 物件；in-process 門面（Runtime）直接傳 Identity；HTTP 門面由 `TokenVerifier` 把 bearer 轉成 `AccessToken.claims` 再組 Identity。兩個門面共用同一 registry，隔離謂詞經 `retrieve()` 同源。

### 主題 2：模型迴圈用哪個 API
**調查問題**：Chat Completions 自 dispatch vs Responses 內建 MCP。
**發現**：現行 `llm_provider.OpenAIProvider` 已有 `AsyncOpenAI`；`llm_answer_optimizer` 有單次 tool-call 回填雛形；Responses 內建 MCP 需公網可達。
**結論**：Chat Completions 迴圈＋`parallel_tool_calls=false`＋strict 工具 schema＋最終回答用 `response_format json_schema strict`（引用契約）；provider 抽象保留換 Claude 的路（D1）。

### 主題 3：引用契約可驗性
**調查問題**：逐字子串比對在中文與模型改寫下是否可行。
**發現**：主題 pilot 六欄實測，模型會改標點／全半形；rubric 用「必含群」可過但太鬆；forbid 詞可抓張冠李戴。
**結論**：正規化（NFKC、去空白、統一標點）後子串比對；最小引用長度 6 字；每句 ≥1 cite；斷言封閉詞集含否定式（「無法／不需要／不支援／不會」）；尺自證＝五輪 e2e 抓到的捏造句必拒。

### 主題 4：大綱 token 預算
**發現**：prospect 池 5,533 字 ≈ 3.5K token；系統脈絡 27 列 10,022 字 ≈ 6K；`tiktoken` 未裝（容器）；provider 回 usage 可校準。
**結論**：組裝時用 `tiktoken`（加依賴，鎖 cl100k_base／o200k_base 依模型），啟動時檢查預算大聲失敗；上限 R5.5。

### 主題 5：影子模式不阻塞
**發現**：`_metered_stream` 在串流結束 finalize 計量；`usage_metering.set_decision` 寫 `decision_snapshot`；不變量 5 要求內部流量標 `is_internal`。
**結論**：影子以 `asyncio.create_task` 在回應送出後執行，獨立 `UsageContext` 標 `is_internal=True`，結果寫 `decision_snapshot.agent_shadow`（不與主事件混）。

## 技術選型

### 選型 1：工具伺服器部署形態
| 方案 | 優點 | 缺點 | 適用場景 |
|---|---|---|---|
| A in-process＋MCP 對外掛載 | 零延遲、一份程式、謂詞同源 | 內外耦合同一部署單元 | 起步 |
| B 獨立 mcp-tools 服務 | 邊界乾淨、獨立擴縮 | +50–200 ms／呼叫、跨容器共享隔離程式碼 | 多消費者、獨立審計 |
| C 混合（registry＋兩門面） | A 的效能＋B 的路可留 | registry 介面要設計 | **選用** |
**最終選擇**：C。理由：M0–M3 只動 prospect，熱路徑不該多一跳；外部 agent（Claude Code、回測）走 MCP 掛載；日後拆服務只換門面。

### 選型 2：模型呼叫 API
**最終選擇**：Chat Completions 迴圈（現行 SDK 1.54）。理由：無公網可達需求、與現有 provider／計量鉤一致、Claude 可換 provider。

## 相依性分析
### 外部 API 與服務
| 服務 | 版本 | 用途 | 文件 | 注意 |
|---|---|---|---|---|
| OpenAI Chat Completions | openai 1.54.0 | 模型迴圈 | developers.openai.com/api/docs/api-reference/chat/create | `parallel_tool_calls=false`；strict schema 需 `additionalProperties:false`＋全 required |
| OpenAI Responses（內建 mcp） | — | 外部實驗用 | developers.openai.com/api/docs/guides/tools-connectors-mcp | 需公網可達／tunnel；⛔ 非生產路徑 |
| JGB API | 現行 | `jgb2.query/action` | `jgb_system_api.py` | role_id＋user_id 雙證由 server 帶 |

### 函式庫與套件
| 套件 | 版本 | 用途 | 授權 | 風險 |
|---|---|---|---|---|
| mcp | 2.1.1 | MCPServer／streamable_http_app／TokenVerifier | MIT | v2 API 與 v1 不相容，鎖版 |
| tiktoken | 0.14.0 | 大綱 token 預算 | MIT | 編碼要對應模型 |
| openai | 1.54.0（既有） | 迴圈 | Apache-2.0 | — |

## 現有程式碼分析
**整合點**：`app.py:lifespan`（Mount＋session_manager）、`routers/chat.py:handle_conversational_entry／CONVERSATIONAL_ENABLED_ROLES`（per-audience 開關）、`_conversational_sse／_metered_stream`（串流與計量）、`conversational_engine`（form_sessions 狀態、確認機器值、`_execute_endpoint`）、`vendor_knowledge_retriever_v2.retrieve`（謂詞同源）、`system_context.get_system_context`（目錄）、`services/jgb/*build_*_facts`（facts）、`presales_gate／conversational_config`（常數）、`usage_metering.set_decision`（落點）、`pipeline_health_service`（健檢）。
**技術債**：reranker 靜默停用（售前路徑不用即迴避；pm／tenant 待重評）；`FACE_BUILDERS` 中央 registry 查無（各模組 builder，設計以 domain→builder 映射表補）。

## 效能考量
| 指標 | 目標 | 測法 |
|---|---|---|
| prospect 回合 p95 | ≤ 12 s（D2） | usage_events 延遲欄＋影子評估 |
| 工具單次 | ≤ 3 s | 工具日誌 |
| 首字 | ≤ 4 s | SSE 事件時間戳 |
| 每回合成本 | ≤ 現行 ×3 | usage_events.est_cost_usd |
**瓶頸**：模型呼叫 2–4 次；工具內 DB 查詢；影子模式雙倍模型費用（月上限自動關）。

## 安全性考量（STRIDE）
- Spoofing：模型或外部 client 冒用身分 ⇒ 工具 schema 無身分欄、bearer claims 由 server 驗。
- Tampering：工具回傳被當指令 ⇒ 固定包裝、system prompt 明示、Verifier 不看回傳文字以外的東西。
- Repudiation：每回合 trace_id 串 SSE／工具日誌／計量。
- Information Disclosure：`ToolError` 只給業務訊息，未捕捉例外遮罩；工具回傳封閉欄位；日誌不含個資與金鑰。
- DoS：預算（4 呼叫／2 重寫／20 s）、影子月上限、MCP `max_request_body_size`。
- Elevation：寫入工具需 token；白名單依身分與階段。

## 風險登記
| 風險 | 類型 | 影響 | 機率 | 緩解 | 狀態 |
|---|---|---|---|---|---|
| Verifier 過嚴 ⇒ 轉人率上升 | 技術 | 高 | 中 | 影子評估對照；斷言詞集版本化；可調 | 開放 |
| 模型不叫工具直接答 | 技術 | 高 | 中 | 無 cite 即拒；首步可 `tool_choice="required"`（大綱在上下文時不需要） | 開放 |
| 大綱過長稀釋注意力 | 技術 | 中 | 中 | token 預算；主題頁結構化標題 | 開放 |
| 幫助中心資料源與版本 | 商業 | 中 | 高 | D3 裁前 citable=false | 開放 |
| 影子成本 | 商業 | 中 | 中 | 月上限自動關 | 已緩解（設計） |
| mcp v2 API 變動 | 技術 | 中 | 低 | 鎖版；門面隔離 | 已緩解 |

## 開放問題
1. D1 模型與 SDK（預設 OpenAI Chat Completions）。2. D2 收案線。3. D3 幫助中心引用。4. D4 預算值。5. D5 影子告知。6. `FACE_BUILDERS` 映射（實作時對碼）。

## 時間軸
| 日期 | 活動 | 結果 |
|---|---|---|
| 2026-09-04 | 三 scout 落差分析＋外部文件查證 | validation_gap.md、本檔 |

## 參考資源
- https://py.sdk.modelcontextprotocol.io/run/asgi/ ；/run/authorization/ ；/handlers/context/ ；/servers/structured-output/ ；/servers/handling-errors/
- https://developers.openai.com/api/docs/api-reference/chat/create ；/guides/function-calling ；/guides/tools-connectors-mcp
- https://github.com/modelcontextprotocol/python-sdk

## 主題 6（1.1 追加）：授權邊界與 jgb2 事實來源
- **業主裁決 DSP-011（2026-09-04）**：「權限的部分由 API 全權處理；此系統只管額度。」⇒ 本系統不建授權層，`role_id`／`user_id` 為上游信任輸入（沿用 `F-C25`）；本系統對呼叫者的閘只有 `services/api_key_auth.py:api_key_guard`（服務層）與 `services/usage_metering.py:quota_check`（額度）。MCP 門面因此定為非公開認證面，⛔ 不用 SDK 的 `TokenVerifier`／`AuthSettings`。
- **jgb2 兩層權限**（`jgb2-source-index.md` §3.5）：Layer 1 `external_api_key_permissions`／whitelists；Layer 2 `viewer_user_id`→`VisibleScope::resolve()`，僅 `bills`／`contracts/status-overview`／`payments`／`invoices` 四端點生效。本 repo `services/jgb_system_api.py` 已有 `viewer_user_id` 用法（grep `viewer_user_id`）。
- **L1 自同步**：9 支 External controller 回應自帶 `mapping`；`services/jgb_response_formatter.py` 已讀 `mapping`，而 `services/jgb/bills.py:STATUS_LABELS` 是重複硬表（缺口 7）⇒ agent 路徑只讀 `mapping`。
- **security-reviewer 查證**（2026-09-04）：全 repo 無入站 bearer 驗證（正對照 `verify_api_key` 存在）；`_grounding_by_ids` SQL 無業者過濾；隔離謂詞 4 份手抄各不相同 ⇒ `build_visibility_predicate` 列 M0 首項。
- **待裁**：jgb2-source-index §10.1 MCP 工具面掛 `external/v1`（現況）或加掛 `agent/v1`（ed25519＋IP 白名單）。

## 主題 7（5.8 追加，2026-09-05）：NLI 接地檢查——模型現況與業界對照

來源存取日期皆 2026-09-05；由具 WebSearch 的唯讀代理調研，數字可回指網址；⛔ 皆未實跑。

### 候選模型（CPU 可跑、有中文分數）

| 模型 | 參數 | 授權 | 中文分數 | 大小 | 備註 |
|---|---|---|---|---|---|
| `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | 0.3B | MIT | XNLI zh acc 0.803（[模型卡](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7)） | 558 MB，含 ONNX | 訓練含 ANLI／WANLI 對抗樣本；機翻資料自述會降品質；不支援 FP16 |
| `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` | 0.3B | MIT | XNLI zh 0.8116（[模型卡](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli)） | 558 MB | 資料多樣性較低 |
| `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli` | 0.1B | MIT | XNLI zh 0.721（[模型卡](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli)） | 查無 | 約 3 倍快、掉 8 點 |
| `IDEA-CCNL/Erlangshen-Roberta-110M-NLI` | 110M | Apache-2.0 | CMNLI 80.83／OCNLI 78.56（[模型卡](https://huggingface.co/IDEA-CCNL/Erlangshen-Roberta-110M-NLI)） | 409 MB（無 safetensors） | 簡中原生 NLI；label `0=CONTRADICTION,1=NEUTRAL,2=ENTAILMENT` |
| `IDEA-CCNL/Erlangshen-Roberta-330M-NLI` | 330M | Apache-2.0 | CMNLI 82.25／OCNLI 79.82 | 1.3 GB | 同上 |
| `joeddav/xlm-roberta-large-xnli` | 0.6B | MIT | 模型卡查無；XNLI test 已進訓練 ⇒ ⛔ 不可用 XNLI test 評它 | 2.24 GB | CPU 延遲預期最高 |
| `vectara/hallucination_evaluation_model`（HHEM-2.1-Open） | 0.1B | Apache-2.0 | **繁中不適用**（模型卡 `language: en`；商用 2.3 才有簡中） | 439 MB | 需 `trust_remote_code` |

### 業界做法（皆不支援繁中）

| 產品 | 模型型態 | 粒度 | 輸出 | 來源 |
|---|---|---|---|---|
| Google Vertex Check grounding | 未揭露 | 一句＝一 claim | support score 0–1、claim 級分數、引用 chunk；延遲 <500 ms；語言查無 | [docs](https://docs.cloud.google.com/generative-ai-app-builder/docs/check-grounding) |
| Azure Groundedness detection | 未揭露＋（reasoning 用 GPT-4o） | 整段 vs sources，標 ungrounded 片段 offset | 布林＋比例；**僅英文** | [docs](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/groundedness) |
| Bedrock Contextual grounding | 未揭露 | 整份 response；明言不支援 chatbot QA | grounding／relevance 0–1，門檻 BLOCK；en/fr/es | [docs](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html) |
| Vectara HHEM | NLI 式分類器 | 句對／段落對 | 0–1 | [模型卡](https://huggingface.co/vectara/hallucination_evaluation_model) |
| RAGAS faithfulness | LLM 判官（拆 claim→逐 claim）；HHEM 變體 | 原子 claim vs context | 支持 claim 比例 | [docs](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/) |

### 陷阱（對 5.8 設計的直接影響）

1. XNLI zh 是翻譯句、未標簡繁（[XNLI](https://ar5iv.labs.arxiv.org/html/1809.05053)）；OCNLI 指翻譯資料有 translationese（[OCNLI](https://ar5iv.labs.arxiv.org/html/2010.05444)）⇒ 0.80 不能當繁中口語期望值。
2. 繁中 NLI 公開基準查無（正對照 OCNLI 有中）⇒ 必須自建 zh-TW holdout，先凍結判準。
3. 預訓練含 zh-Hant（CC-100 5.3G）但微調全簡中 ⇒ 繁中原文與 OpenCC 轉簡兩種輸入都要量。
4. 長前提退化：NLI 是句層級，SummaC／AlignScore 都切段取 max 聚合（[SummaC](https://aclanthology.org/2022.tacl-1.10/)、[AlignScore](https://github.com/yuh-zha/AlignScore)）⇒ 前提用 DSP-029 解析出的**單句**正好對齊。
5. 中文分句弱點（逗號句界 F1 約 70%）⇒ 假設句用 Verifier 同一把 `split_sentences`，與線上一致。
6. label 順序各模型不同 ⇒ 讀 `id2label`，⛔ 不硬編。
7. CPU 每句對延遲公開數字幾乎查無（HHEM：2k token <1.5 s）⇒ 目標機器實測。
8. 授權：候選皆 MIT／Apache-2.0 可商用；`symanto/*` 未標授權不列。

### 建議：先試 `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`，配 `Erlangshen-Roberta-110M-NLI` 當第二把尺；兩把尺都要先在自建 holdout 上證明「看得見已知的接地錯誤」（R4 三捏造句），才能拿來量系統輸出。
