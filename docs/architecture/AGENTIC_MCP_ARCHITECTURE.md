# 對話線架構（現況，2026-09-08 上線）

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。

> 讀者：要改這條線的工程、要接它的呼叫端、要驗它的稽核。
> 對象：`rag-orchestrator/services/agent/**`＋`/mcp` 門面。舊鏈（REST `/api/v1/message`、SOP、面向）不在本文，見 `COMPLETE_CONVERSATION_ARCHITECTURE.md`。
> 事實紀律：每個機制都附可 grep 的符號；行號會漂，⛔ 不當事實。決策依據在 `.claude/DECISIONS.md` DSP-011／037～042、demo 帳本 `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/demo-ledger-line-oa-20260907.md` §1b。

## 怎麼讀這一份

⛔ **章節順序＝一則訊息實際走的順序**，⛔ 不是按寫作先後堆的。找答案照這張表跳：

| 你要問的 | 去哪一節 |
|---|---|
| 誰是核心、誰只是門面 | §0 一句話 |
| **誰呼叫誰**（MCP、AI、工具、JGB API 的關係），一回合有哪些 AI 呼叫 | **§0a 誰呼叫誰** |
| 每個元件負責什麼、⛔ 不做什麼 | §1 元件與責任（§1a 模組圖、§1b 其餘核心模組逐支） |
| 一回合長什麼樣（概覽） | §2 一回合的路徑 |
| **一句話進來到回出去，每一步與每一個終止點** | **§2b 完整流程**（階段 0 請求層→階段 1 門面→階段 2 四段管線→階段 3 寫入鏈→終止點表） |
| 實際八種情境各自怎麼走、誰決定什麼 | §3 八種情境走查 |
| 誰擋什麼（金鑰／別戶／寫入／機敏／照片／額度／紀錄） | §4 邊界與紀律 |
| **為什麼被轉人**（五個來源）、線上到底擋不擋 | **§4b 回合出口與「為什麼轉人」** |
| 上傳文件那條線 | §4c 文件歸納回合（§4c-1 逐支） |
| 資料存在哪 | §5 資料落點 |
| 環境變數與現行值 | §6 組態 |
| 測試怎麼分層 | §7 測試層 |
| 現在還壞著／還沒做的 | §8 已知限制 |
| 這條線對模型做了哪些**假設** | §9 模型行為假設表 |

⚠️ **邊界規則不在本檔**，在 `BOUNDARY.md`（哪些算本系統、哪些算呼叫端）。

## 0. 一句話

**核心是 `AgentRuntime`，`/mcp` 只是接在它外面的門面之一**（⛔ 把 `/mcp` 當脊椎、Runtime 當它裡面的東西）。

**系統定位（DSP-130）**：本系統是對話服務，不是 MCP 系統。本檔寫現況：對話服務區（MCP 門面、`AgentRuntime`、AI 呼叫、大綱、草稿、確認卡、出口檢查、轉人）與工具區（`ToolRegistry` 與工具）跑在同一個程式，`jgb2.*` 與 `JGBSystemAPI` 這批 JGB 工具暫放在內。目標架構與差距見 `TARGET_ARCHITECTURE.md` §4、§8；現況的破口見 §0a「第 3、4 段以外的兩條路」。

> 📐 **邊界規則見 `docs/architecture/BOUNDARY.md`（唯一正本）。** 三個桶：本系統／呼叫端／外部相依；
> 一句話測試＝「把呼叫端整個換掉，這句話還成立嗎」。⛔ 不要在本檔另寫一份宣告。

**核心**：`AgentRuntime` 收到一句話與一份會話狀態，先用**程式**處理機器值終止路徑
（確認按鈕、清單點選、照片／文件），其餘叫 AI 理解：主模型在封閉工具清單裡查資料、組話，
寫入意圖呼叫讀出動作與欄位值；寫入由程式依草稿出確認卡、按了才兌現；答案過 `OutputVerifier`
再過四道出口閘。它的建構依賴是
`provider`／`registry`／`verifier`／`assembler`／`budget`／`candidate_selector`／`db_pool`
——**⛔ 沒有任何協定或門面**。

**門面**（判準：非測試的 `run_turn` 呼叫端，**⛔ 用 `ast` 數 `ast.Call`、不要 grep**；照判準會數到**五個檔**，其中 `agent_entry.py` 是遷移橋、`runtime.py` 是 `stream_turn` 自呼，兩者都不是門面——見下段）：`mcp_facade._agent_turn`（✅ 掛著：經專用對話 API `routers/agent_dialogue.py` 與 `/mcp` 兩個入口，共用 `_make_invoke` 建的 `_invoke`）、
`tools/agent_eval.py`（回測）、`shadow.py`（影子）。
⚠️ `routers/agent_entry.py` **不在這張清單上**——它是**遷移橋**（任務 2.2／R9）：站在舊鏈 `chat.py` 的請求路徑上分流，⛔ 不是門面也不是端點；上游五樣相依全隨 `chat.py` 刪除，⛔ 掛路由救不活。
`run_turn` 的簽名在 `mcp_facade` 裡被註解為「**REST／影子／回測共用的介面**」。

⚠️ **本系統只有 MCP server，沒有對外的 MCP client**：MCP client 全 repo 只出現在測試工具裡——三支整合測試用 `mcp.client`
（`mcp.Client`／`mcp.client.streamable_http.streamable_http_client`），煙霧測試腳本 `scripts/smoke/mcp_smoke.py` 用 `ClientSession`；三者都是拿 client 打本系統自己的 server；`runtime.py` ⛔ 不 import `mcp`，模型呼叫工具走 `registry.call`，
**in-process**。

🔴 **⛔ 「門面之一」⛔ 不等於「門面很薄」**（2026-09-12 兩次對抗性演練逼出：
第一次有人把「再加一個門面」估成 1 天，第二次有人讀完本段估 3–5 天但**估錯了方向**）。
⚠️ **關鍵是分清可複用與不可複用，⛔ 不要照抄 13 步。**

**可複用的（⛔ 不要重做）**：`_make_agent_turn` 回傳的內層函式簽名是
`async def _agent_turn(identity: Identity, args: dict) -> ToolResult`——**協定無關**，
本身就是一支一般工具。那 13 個順序即契約的步驟（形狀檢查 → outline fail-closed
**排在 `store.load` 之前** → 配額**最壞值預扣排在抓檔之前** → 命名空間 → 過期**先 close 再 start**
→ 前處理 → `wait_for(run_turn)` → `stamp_last_turn` → `store.save`；候選章節由 `runtime._select_outline` 每回合從正本現組，`agent_state` 沒有大綱鍵）
**全在這個函式體內**，新門面的工作是**接上它**。
⛔ `_make_agent_turn` 的 docstring 逐字寫著「**⛔ 不另寫第二條回合邏輯**（R3.7）」
——重做一遍就是違反它。逐步見 §2b 階段 1。

**不可複用的（真正的工作量在這裡）**：

| 要自己做的 | 為什麼不能照抄 |
|---|---|
| 傳輸層：`McpServiceGate`（最外層 ASGI middleware）、`parse_identity`、`resolve_call`、`_make_invoke`（計量 begin／quota／finalize＋速率＋每小時上限）、`build_asgi_app`／`union_specs`／`_ToolListFilter`／`_MountPathNormalizer` | 全是 MCP 協定專屬。`mcp_facade.py` 共 3,573 行（2026-10-30 `wc -l`），這一層佔大半 |
| 🔴 **命名空間身分（安全決策，⛔ 選錯＝重開一個已關掉的 P1）** | 見下方紅字 |
| **額度計量**（`app.py::usage_metering_middleware` 只對 `/mcp` 動作、刻意不 begin/finalize——不變量 31「門面是唯一寫入者」） | 中介層綁死路徑前綴 |
| **`GATED_PREFIXES` 要加前綴** | 否則新端點沒有無條件金鑰閘 |
| **`Identity.entry` 要決定** | `"rest"` ⇒ 寫入型工具看不到也叫不到 |

🔴 **命名空間身分擋的是什麼**（`namespaced_identity` docstring 逐字；形狀是 `mcp:{api_key_id}:{vendor_id}:{session_id}`）：

- `session.slots.get/set` 打的是 `form_sessions.session_id = $1`；
  `confirm.request`／`redeem_token` 打的是 `agent_confirmation_tokens.session_id`。
  **這兩組 SQL 都沒有 vendor 條件。**
- 所以只要工具拿到的是**裸 `session_id`**，持另一把 key／另一個 vendor 的呼叫端
  只要帶同一個 `session_id`，就能**讀他人的槽位、兌現他人的確認 token**
  ——那是被擋掉過一次的 **P1**，會從這扇側門原封不動走回來。
- ⛔ **fail-closed**：`api_key_id`／`vendor_id` 缺、或鍵超過 `form_sessions.session_id` 的
  100 字 ⇒ `ValueError`。⛔ **不得「退回裸 session_id」**——那正是被擋掉的那條路。
- ⚠️ REST 路徑（`routers/agent_entry.py`）**刻意不呼叫本函式**：那條路的 `session_id`
  由上游 scope 過，且與舊鏈共用同一列；加前綴會讓兩者天然分池、續對話直接斷掉。
  「MCP 加前綴、REST 不加」是**分池設計**，⛔ 不要為了「一致」把 REST 也加上去。

查證：`grep -n "def namespaced_identity" -A 26 rag-orchestrator/services/agent/mcp_facade.py`；
`grep -n "不另寫第二條回合邏輯" rag-orchestrator/services/agent/mcp_facade.py`。

## 0a. 誰呼叫誰

由外到內四段，只有第一段走 MCP 協定。第 1、2 段在對話服務區，第 3 段是兩區的接點，第 4 段在工具區（DSP-130）。

**現況架構**（對話服務區與工具區跑在同一個程式）：

```
呼叫端
  │ 對話 API：POST /api/v1/agent/turn（DSP-134）；過渡：MCP 協定 POST /mcp，tools/call agent.turn
━━ 對話服務區（本系統主體）━━
對話 API（routers/agent_dialogue.py）／MCP 門面（mcp_facade.py）——共用同一個 _invoke
  │ 驗金鑰、身分、額度；讀寫會話狀態；照片與文件前處理
  │ 函式呼叫 run_turn（這段不走 MCP 協定）
AgentRuntime（對話核心，runtime.py）
  │ 程式：機器值、草稿、閘門、確認卡、轉人、回話
  │ AI：理解使用者、知識作答、一般對話的措辭
  │ 函式呼叫 registry.call；寫入用的查詢直呼 confirm.py 函式（都不走 MCP 協定）
━━ 工具區（JGB 工具暫放本系統）━━
工具層（ToolRegistry，registry.py）
  │ 查帳單、查合約、建修繕單等；MCP 門面與 AgentRuntime 共用同一份
  │ JGBSystemAPI → Transport → HTTP
━━ 外部系統 ━━
JGB API（/api/external/v1 等）
```

各段的呼叫方式：

| 段 | 誰呼叫誰 | 怎麼呼叫 | 符號 |
|---|---|---|---|
| 1 | 呼叫端 → 對話 API／MCP 門面 | HTTP `POST /api/v1/agent/turn`（JSON body 原樣交 `agent.turn`）；過渡入口為 MCP 協定 `POST /mcp`、`tools/call agent.turn`；兩者都進 `_make_invoke` 建的 `_invoke` | `agent_dialogue.build_router`；`mcp_facade.build_mcp_server`、`build_asgi_app`、`_make_invoke` |
| 2 | MCP 門面 → AgentRuntime | 函式呼叫 | `_agent_turn` 呼叫 `runtime.run_turn` |
| 3 | AgentRuntime → 工具層 | 函式呼叫 | `self.registry.call(...)` |
| 4 | 工具層 → JGB API | HTTP | `JGBSystemAPI`（`services/jgb_system_api.py`）→ `Transport`（`services/jgb/transport.py`）；`USE_MOCK_JGB_API=true` 時走替身 |

**MCP 門面目前兼兩份工作**：對話入口（`agent.turn`）與工具入口（`build_mcp_server` 依 `union_specs` 逐支 `add_tool`）。對話回合可從專用對話 API（`routers/agent_dialogue.py`，`Identity.entry="dialogue"`，DSP-134）或 `/mcp`（`entry="mcp"`）進來，兩者共用同一份 registry、同一個 `_invoke`、同一組請求層閘，寫入工具可見性與確認兌現都以 `identity.is_backend_entry()` 判斷；正式機尚未部署新入口，呼叫端仍走 `/mcp`。本系統另有檔案直傳（`agent_uploads_router`）與後台管理等 HTTP 路由，那些不跑對話回合。目標是呼叫端只走對話 API、`/mcp` 關閉（DSP-130、DSP-131）。

**第 3、4 段以外的兩條路**（都不走 MCP 協定）：

- AgentRuntime 直呼 `tools/confirm.py` 的函式查 JGB，不經 `registry.call`：寫入名稱查詢（`write_name_candidates`、`missing_name_lenient`、`name_early_lookup`、`name_lenient_picked_title`、`name_lenient_rows_for_ids`、`name_precheck_ids`、`pick_matches_name`）、報修分類驗值（`_is_valid_repair_category`）、封閉動作缺欄判定（`closed_action_missing_labels`）。
- MCP 門面在 `build_registry` 內有兩個閉包：`_repair_category_tree` 在 `run_turn` 之前直接查 JGB；`_open_repairs` 注入 `confirm.request`，直接查 JGB。

**執行工具的工具層只有一份**：`app.py` 用 `build_registry` 建一份 `ToolRegistry`，同時交給 `build_mcp_server` 與 `build_runtime`；`routers/agent.py` 另建一份，只用於 `/openapi.json`、`/health`，不執行工具。支數依條件變動：`AGENT_STAGE` 預設 M0 時 12 支；M2 以上、pm＋`entry=mcp`、`AGENT_TURN_ENABLED` 開啟時註冊 22 支，模型清單少門面專用的 `agent.turn`（`facade_only`），成 21 支；舊知識庫零列已審時 `gate_kb_search_on_reviewed_rows` 再藏 `kb.search`，成 20 支。直傳啟用時多一支門面專用的 `agent.upload_ticket`。其他身分與入口的支數不同，以 `specs_for` 為準。

**MCP、AI、工具的關係**：

- 主模型走 Chat Completions 的 `tools`（`registry.to_openai_tools`），只提出要呼叫哪支工具與參數；執行的是 `_run_model_loop` 裡的 `registry.call`。
- 打 JGB API 的程式：`tools/jgb2.py`、`jgb2_stats.py`、`action.py`、`confirm.py`，加上面兩個門面閉包；AI 不打。`kb.*`、`help.read`、`session.slots.*` 用本系統自己的資料。
- 寫入工具 `jgb2.action.*` 在模型的工具清單裡，但 `_wrap_write_tool` 要已兌現的確認 token 才放行，token 不進模型上下文。
- 其他工具也能經 `/mcp` 直呼：先過門面的金鑰、身分、額度，再經 `_invoke` 到 `registry.call`，不經 AgentRuntime，沒有 AI 與草稿。直呼 `confirm.request` 拿得到卡片資料，但沒有待確認筆，無法兌現；直呼 `jgb2.action.*` 在工具可見時回 `CONFIRMATION_REQUIRED`，`AGENT_WRITE_TOOLS_ENABLED` 關閉或 `entry=rest` 時回 `NO_MATCH`。

**一回合的 AI 呼叫**（只有主模型帶工具，其餘只回 JSON 或文字）：

| 呼叫 | 何時 | 回什麼 | 符號 |
|---|---|---|---|
| 主模型 | 進段三後，可多輪。程式依意圖出卡、標籤判定由程式收尾（要真人、已解決）、重送、卡仍有效、剛送出、候選按鈕回合，由程式結束回合，主模型不呼叫或被中斷 | 工具呼叫或最終答案 | `_run_model_loop`、`_dialog_act_pre_loop`、`_DialogActPreempt`、`_write_draft_reissue_exit`、`_write_draft_card_still_valid_exit`、`_write_draft_submitted_exit` |
| 寫入意圖 | 使用者文字回合，主模型之前先發，回合開始還沒有草稿也照發（等待時間見 §3 情境 1）；文件回合、`pick:` 機器值、影子回合、`AGENT_WRITE_DRAFT` 關閉、`select:` 釘住範圍或看不到寫入工具時不發 | 動作、欄位值 | `_start_write_intent_call` |
| 標籤 | 使用者文字回合，與寫入意圖同時發；文件回合、`pick:` 機器值、影子回合、`AGENT_CLOSING_HANDOFF` 關閉時不發。確認用的 `_dialog_act_field_confirm` 是之後再發一次 | `dialog_act`（要真人、已解決等）；程式依它決定要不要結束回合 | `_start_dialog_act_call`、`_dialog_act_field_confirm` |
| 帶狀態句判讀 | 模型答案過 Verifier 後；`AGENT_STATE_CLAIM_GATE` 開啟時才跑，轉人回合與程式回話結束的回合不跑 | 回覆有沒有宣稱狀態 | `state_claim.judge_state_claims` |
| 名稱寬鬆比對 | 寫入時名稱講不準 | 候選編號 | `name_match.ai_pick` |
| 門面前處理 | 有照片、文件或謄本時，在 `run_turn` 之前 | 辨識或擷取結果 | `image_recognition_service`、`document_extract`、`mcp_facade._documind_pick_leaves` |

**工具由誰發起**：

| 工具 | 發起者 | 符號 |
|---|---|---|
| `jgb2.query.*`、`jgb2.stats.*`、`kb.*`、`help.read`、`handoff.request`、`session.slots.*` | 主模型提出 | `_run_model_loop` |
| `jgb2.query.*`（清單點選、整句編號或短名稱的前置查詢） | 程式 | `_run_select_segment`、`_PRE_LOOKUP_*` |
| `jgb2.query.*`（兌現範圍閘） | 程式 | `_scope_gate_confirm_request`。未結修繕提示由 `_open_repairs` 閉包直接查 JGB，不經工具呼叫 |
| `confirm.request`（一般寫入回合） | 程式依草稿；主模型自呼只當提議 | `_write_draft_program_message`、`_write_proposal_handle` |
| `confirm.request`（謄本回合放行 `estate_create` 的第一輪） | 程式 | `_document_program_message`、`DOCUMENT_PROGRAM_CONFIRM_ACTIONS` |
| `confirm.request`（文件暫存回合） | 草稿動作與暫存動作相同時，程式也可依草稿發起；其餘由主模型 | `_write_draft_decide`（`carry["action"] != draft["action"]` 才不發）；見 §8「部分寫入回合仍以模型參數出卡」 |
| `confirm.request`（其他文件回合、點選範圍回合） | 主模型 | 見 §8「部分寫入回合仍以模型參數出卡」 |
| `jgb2.action.*` | 程式，客人按確認後 | `_run_confirm_segment` |


## 1. 元件與責任

```mermaid
flowchart LR
  subgraph FACES["門面（可插拔，⛔ 核心不依賴它們）"]
    F["mcp_facade /mcp＋agent_dialogue /api/v1/agent/turn\n✅ 掛著（共用 _invoke）"]
    RE["agent_entry 遷移橋\n⛔ 上游已滅"]
    EV["agent_eval 回測"]
    SH["shadow 影子"]
  end
  F --> RT
  RE -.-> RT
  EV -.-> RT
  SH -.-> RT
  F --> ST[NamespacedStateStore\nform_sessions.collected_data]
  F --> IM[image_fetch\n抓檔/縮圖]
  IM --> VS[ImageRecognitionService\nOpenAI vision]
  RT["**AgentRuntime.run_turn**\n（核心）"] --> SEL[select 段]
  RT --> CF[confirm 段]
  RT --> LLM[OpenAI chat\ngpt-6-luna]
  RT --> REG[ToolRegistry\n可見性/速率/schema]
  REG --> Q[jgb2.query.*]
  REG --> A[jgb2.action.*]
  REG --> C[confirm.request]
  REG --> K[kb.* / help.read / session.slots.*]
  Q --> TR[jgb transport\nUSE_MOCK_JGB_API]
  A --> TR
  TR --> MOCK[(demo_vendor4.json\n記憶體)]
  TR -. 正式 .-> JGB[(jgb2 external/v1\nagent/v1)]
  RT --> VF[OutputVerifier\n觀察模式]
  RT --> TRC[trace / usage_events\n決策快照]
```

| 元件 | 檔案（符號） | 責任 | ⛔ 不做 |
|---|---|---|---|
| **核心 Runtime** | `services/agent/runtime.py`（`AgentRuntime.run_turn`、`_run_turn_body` 四段接線） | **整個對話架構**：程式段、模型迴圈、Verifier、出口閘 | ⛔ 不知道任何協定或門面 |
| 門面（其一） | `services/agent/mcp_facade.py`（`build_asgi_app`、`AGENT_TURN_SPEC`、`_agent_turn`、`AgentTurnOutput`、`check_and_record_agent_turn`） | 驗 key／Origin／身分 header、命名空間 `mcp:{api_key_id}:{vendor_id}:{session_id}`、每呼叫一列 `usage_events`、每小時上限、照片前處理、會話過期、呼叫 Runtime | 不判授權（DSP-011：授權由 JGB API 依 role 收口） |
| 狀態 | `services/agent/state_store.py`（`NamespacedStateStore`、`stamp_last_turn`、`is_expired`、`SESSION_IDLE_TTL_S`） | 對話歷史、槽位、待確認表、過期戳，落 `form_sessions.collected_data` | 不存 token、不存照片 |
| Runtime | `services/agent/runtime.py`（`AgentRuntime.run_turn`、`_run_confirm_segment`、`_run_select_segment`、`_enforce_tool_scope`、`_apply_scope_exit`、`_scope_gate_confirm_request`、`_begin_pending_confirm`、`_finalize`） | 機器值程式段、模型迴圈、工具結果包裝、範圍守門、固定句、trace | 不讓模型判「同一戶」「同意詞」 |
| 工具註冊 | `services/agent/tools/registry.py`（`ToolRegistry.call`、`register`、`_validate_value`、`ToolError`） | 四步：可見性（stage×旗標）、速率、schema、執行；寫入工具強制 `mcp_only`＋已兌現 | `_validate_value` 實作的是 `type`／`enum`／`required`／`additionalProperties`／`maxLength`／`minLength`／`maximum`／`minimum`／`items`（遞迴）。⛔ **無 `maxItems`／`pattern`**（兩者 0 命中，正對照：`maxLength` 有命中）；`minimum`／`maximum` 會擋 |
| 查詢工具 | `services/agent/tools/jgb2.py`（`query_bills/contracts/estates/meters/repairs/accounts`、`_ok_single` 帶 `scope.estate_id`） | face 封閉列舉、ref／keyword 縮小、facts 由 formatter 決定性組句 | 不讓模型算數字（逾期天數程式算） |
| 寫入工具 | `services/agent/tools/action.py`（`ACTION_SPECS` 五支：`bill_due_extend`、`repair_create`、`estate_create`、`contract_create`、`manual_bill_create`；另有 `_resolve_estate`、`_resolve_category`） | 形狀→範圍讀→寫；冪等鍵＝確認 token；分類缺值歸「其他」、急迫缺值 1 | 不模糊比對物件／分類 |
| 確認卡 | `services/agent/tools/confirm.py`（`confirm_request`、`_is_valid_repair_category`、`open_repairs` 注入）、`services/agent/confirm_card.py`（`render`、`category_name_of`、`emergency_status_of`） | 卡文字由程式依 action＋payload 決定性產出；雜湊綁卡；卡外 `hint` | 模型 summary 不上卡 |
| 照片 | `services/agent/upload_store.py`、`services/agent/image_fetch.py`、`services/image_recognition_service.py`、`services/s3_image_service.py`（`downscale_image`） | 收瀏覽器直傳的暫存檔（回滾模式 `urls` 才抓 relay 簽章網址，硬邊界）、縮圖去 EXIF、分批辨識、決定性驗證輸出 | bytes 不落地、不進任何紀錄；描述硬留空 |
| Verifier | `services/agent/verifier.py`（`OutputVerifier`、`_is_observed`、`_ref_failures`、`_verify_routes`）、`app.py`（`_wrap_verifier_observe_only` 只交模式的相容層） | **模式感知在 `verify()` 內部**：觀察類記進 `verdict.observed` 後**繼續跑後面的類**、照擋類立刻擋（DSP-040／W6-b3） | `observe_only` 只在 `USE_MOCK_JGB_API=true` 允許（否則啟動 raise）；`grounding_observe` 配真 API ⇒ 健檢紅旗 |
| 規則與正本 | `services/agent/agent_rules.py`（`_POLICY_TEXT_NON_PROSPECT`）、`canon/jgb/`（九架正本，2026-09-21.0）＋`.json` | 模型每回合看到的定義句與九架正本（受眾＝細目屬性 `target_user`） | 只寫定義不寫例子 |
| 健檢 | `services/agent/health.py`（`verifier_mode`） | `write_tools_enabled`、`use_mock_jgb_api`、`verifier_mode`、`verifier_observe_only`（保留鍵）、`image_recognition{…}` | `grounding_observe`×非 mock ⇒ `premise.red_flags` |

### 1a. 2026-09-10 Plan R 後的模組圖

`services/agent/runtime.py` 的 `_run_turn_body`（對碼 `rag-orchestrator/services/agent/runtime.py` 符號 `_run_turn_body`，
現約 40 餘行）已拆成四段管線的**接線**，段本身收斂到獨立模組（Plan R R1，`inputs/plan-structural-refactor-20260910.md`）：

```mermaid
flowchart LR
  RTB["_run_turn_body\n（接線，~45 行）"] --> TS["turn_segments.py\nrun_program_segments\n模型前六條終止路徑"]
  RTB --> TC["turn_context.py\nTurnAccumulator／ReservedCallIds\n九段資料注入"]
  RTB --> ML["_run_model_loop\n（runtime.py 內，工具迴圈＋Verifier）"]
  ML --> EG["exit_gates.py\nEXIT_GATES 四道閘"]
  EG --> AS["agent_session.py\n（已落地，13 處呼叫）"]
```

- `turn_segments.py`：模型前的六條終止路徑（機器值程式段）。
- `turn_context.py`：`TurnAccumulator`（回合可變狀態容器）＋ `ReservedCallIds`（保留 id 派生）＋九段資料注入。
- `exit_gates.py`：四道出口閘依序表 `EXIT_GATES`（`scope_exit` → `handoff_without_lookup` → `ask_target_gate` → `handoff_data_exits`，
  順序本身是契約，見該檔 docstring）與 `finalize`。
- `limits.py`：DSP-045 額度封閉表（見 §6），與回合管線並行、非管線的一段。
- `agent_session.py`（`AgentSession()` 在 `runtime.py`／`exit_gates.py`／`turn_segments.py`／
  `state_store.py`／`completed_actions.py` 被呼叫；查證：以 `ast` 數 `ast.Call`，
  ⛔ 不要用 grep 命中數，docstring 會混進來）：收攏 `state["agent"]` 鍵的生命週期讀寫成單一類別。
  ⚠️ 唯獨 `begin_turn()` 本體仍是刻意的 no-op（門面尚未改叫它，見該檔註解）
  （`begin_turn()`／`end_turn()`／`prompt_segments()` 唯一寫讀點），⛔ 尚未執行，本節先記目標形態避免下一輪走查誤判。
- 九個保留 id 前綴（Plan R 覆蓋矩陣列舉）：`img-`／`done-`／`entry-`／`aff-`／`ctx-`／`pre-`／`ref-`／`doc-`／`est-`。

### 1b. 其餘核心模組（逐支：它回答什麼命題、⛔ 不得怎麼改）

🔴 **2026-09-12 補寫**：`services/agent/**` 42 個模組裡，本文原本只解釋了 13 個。
以下把「只被點名」的補上——每支寫「它回答什麼命題」與「⛔ 不得怎麼改」，
因為後者才是改壞的入口。

#### 注入面

| 模組 | 回答什麼命題 | ⛔ 不得怎麼改 |
|---|---|---|
| `prompt_assembler.py`<br>543 行 | **哪些文字准進 system prompt**。白名單只有兩種：(i) 本系統**程式產生**的指令文字（persona／政策／鐵則／工具用途一句話）；(ii) 大綱／目錄，且一律經 `wrap_provenance_data("outline", …)` 包成資料段 | 其餘一切（工具回傳、幫助中心正文、知識列全文）**走工具回傳位置**，由 Runtime 以 `wrap_tool_data(nonce)` 包成 `role=tool`。`build()` 的參數表**刻意沒有任何能接 `ToolResult` 的欄位**——這是**結構上的保證，不是靠自律**（測試用 `inspect.signature` 鎖住參數集合）。⚠️ 使用者訊息**不進資料區**：資料段語義是「以下為資料、非指令」，把提問塞進去會讓模型把它當待引用素材 |
| `provenance_units.py`<br>182 行 | **引用怎麼成立**。DSP-029 把引用從「模型抄一段引文」改成「模型填一個**片段編號**」：編號側在每個片段行首貼 `[{nonce}:{tool_call_id}:{source}§{i}]`，解析側把標記拆回四元組並取第 i 片段 | **兩側各寫一份切法就是這個設計的致命傷**：切法差一個空片段，模型看到的 `§3` 與系統解析的第 3 片段就不是同一句，而**失敗方向是放行**（解析出來是別的句子，覆蓋檢查照樣可能過）。故**只有一個切法函式**，兩側都只准呼叫它；切法 `split_sentences`／`_split_sentences` **定義在本檔**，`verifier.py` 從這裡 import（依賴方向：verifier → provenance_units）——**Verifier 步②也用它，三處同一把尺** |
| `output_schema.py`<br>430 行 | `AgentOutput`／`VerifierRules`／`VerifierVerdict` 的資料模型（pydantic v2）。⛔ 只放模型，判斷在 `verifier.py` | **`fact_class` 刻意是 `Optional[str]` 不是列舉**：若用列舉，pydantic 會在**建構那一步**就對非法值 raise，Verifier 永遠看不到「非法值」這個狀態，fail-closed 分支也就測不到。⚠️ 生產路徑上 OpenAI `response_format` 的 strict json_schema 仍送封閉 enum——放寬只在型別層 |

#### 判定面

| 模組 | 回答什麼命題 | ⛔ 不得怎麼改 |
|---|---|---|
| `question_sensitivity.py`<br>54 行 | **模型自報敏感是不是真敏感**。`fact_class` 由模型自填、Verifier 只驗「敏感類配敏感原因」——回測抓到模型可以把任何一題自報成 `sensitive_no_grounding`，藉此**躲過兩道降級閘直接轉人**。這支是程式側的第二意見 | ⛔ 不寫字串特例：樣式全在 `config/agent_verifier_rules.json` 的 `question_sensitive_patterns`，**改判定＝改規則檔、⛔ 不改程式**。⛔ 不改寫 `out.fact_class`、無副作用只回 bool。⚠️ 詞表錨在**我們自己的產品／服務**（抽成／SLA／資安／法遵／客戶案例），⛔ 不錨在物管本來就有的詞（租金／滯納金／續約）——**誤判成敏感＝維持轉人（無新風險），誤判成非敏感＝敏感題被降級成固定句**，故詞表寧可窄 |
| `affirmative.py`<br>43 行 | 「使用者說『好』算不算授權送出」。`AFFIRMATIVE_WORDS` 是**凍結元組** | `is_affirmative` **只認整句等值，⛔ 不做包含比對**——「對 查」「對，列出來」都不算。把包含比對當授權訊號＝任何帶肯定字的長句都會被誤判成「同意送出」。⛔ 程式不得多不得少不得改順序 |
| `text_norm.py`<br>36 行 | 句末標點正規化，**⛔ 只做這一件事**：連續終結標點收斂成第一個 | ⛔ 不補標點、不刪非終結標點、不動內文其他字元。封閉兩條規則：全形 `。？！` 連續 ≥2 收斂成第一個；半形 `?`／`!` 後接全形 `。` 收斂成半形本身 |
| `bill_period.py`<br>181 行 | **口述期別 → 可比對的年月／未繳**。病灶：業務說「九月的房租」，模型連問三輪帳單編號——**房東不會講編號**，編號是系統識別碼 | **純函式**：⛔ 不讀時鐘（`today` 由呼叫端傳）、⛔ 不讀 env、⛔ 不查 DB、⛔ 不叫模型。**封閉語法**：能解析的講法全在常數表，表外一律 `None`＝解析不到，⛔ 不「盡力猜一個最像的」——猜錯期別的代價比問不到高 |

#### 狀態面

| 模組 | 回答什麼命題 | ⛔ 不得怎麼改 |
|---|---|---|
| `agent_session.py`<br>347 行 | `state["agent"]` 的**生命週期封裝**：`begin_turn`／`end_turn` 是**唯一寫點**（取代原本散在 `exit_gates.finalize`／`_finish_confirm_turn`／`turn_segments` 三處各自的欄位寫入），`prompt_segments()` 是範圍釘住判斷的**唯一讀點**，`scope_exit()` 清掉全部 `until_scope_exit` 鍵 | **純封裝，⛔ 不改任何鍵的生命週期數值**（FIFO 5／20／50、一次性、釘住不寫）。包住**同一個** dict，⛔ 不複製、不改鍵名。⚠️ `begin_turn()` 目前仍是刻意的 no-op（門面尚未改叫它） |
| `session_persistence.py`<br>88 行 | 會話狀態的 SQL 層。新線過去借用 1,581 行的舊引擎，量過只命中四個方法、合計 **43 行純 SQL** ⇒ 抽出來 | **⛔ SQL 逐字照搬、一個字都不准改**：同一張 `form_sessions`、同一組欄位、同一個 `form_id='conversational'`。**既有 DB 列必須繼續可讀——這是搬移的前提，不是副作用** |
| `completed_actions.py`<br>226 行 | 「剛剛那張單號多少」答得出來。病灶：建單成功後 `receipt` 只進 `trace`／`outcome.ref`，**沒進任何模型看得到的地方** | **程式寫、⛔ 不是模型寫**：元素形狀 `{action, ref_type, ref_id, estate_id, at_iso}` **全部封閉值**，模型只能引用不能改寫。⛔ 不進 dialog 歷史、⛔ 不讓模型自己填 `estate_name` 之類的自由字串 |

#### 正本面（配合 §2 路 A）

| 模組 | 回答什麼命題 | ⛔ 不得怎麼改 |
|---|---|---|
| `canon/canon_parser.py`<br>880 行 | 正本格式與解析（Markdown → `CanonDoc`＋`canon_sha256`）。架 front matter **恰六鍵**（`SHELF_FRONT_MATTER_KEYS`；單檔路徑另有 `FRONT_MATTER_KEYS`）；粗目 `## 標題 {#<架字母>-<slug>}`（裸字母 `{#X}` 已於 S5 停用，目錄路徑大聲拒絕）；細目 id 正則 `^[a-z_]+/[A-Z]/[a-z0-9-]+$`；屬性區塊之後每一非空行＝一個內容句 | **F8 嚴格性**：屬性區塊內任何無法解析的行一律 `CanonFormatError`（列號＋原因），**⛔ 不落 `content_units`**——否則講法（含去識別後的真流量）會進 system prompt 成可引用句。⚠️ `source: traffic:*` 的講法 ≤20 字且不含 ≥4 位數字串 |
| `canon/canon_assembler.py`<br>322 行 | 啟動契約 `load_canon_or_die(canon_dir)`：正本只有**一份**（DSP-058，`canon/jgb/` 一目錄＋九架 `A.md…I.md`，`canon_parser.parse_canon_dir` 解析，**無 `audience` 參數**）；內容**只**來自 `.md` 的解析結果；`.json`／`CATALOG.md` **逐位元組**比對重導出結果。受眾隔離改由 `build_outline(doc, audience, …)` 產出的**身分的篩選結果**承擔（依細目 `target_user`／`business_types` 過濾），⛔ 不是拿 `doc.audience`（圖書館形態下恆為 `"jgb"`）比對 | ⚠️ **⛔ 不是只比 `canon_sha256` 欄**——該 sha 只涵蓋各架 `.md` 的位元組，`.json` 改一位元 sha 仍相等。缺架／不同源／格式錯 ⇒ `CanonLoadError`，`_agent_configured()` 為真時**升為啟動紅**。**組裝來源＝正本 Markdown，⛔ 不讀 DB**——DB 售前池是正本的衍生物，大綱不得反過來以衍生物為來源 |
| `canon/review_state.py`<br>113 行 | `knowledge_base.outline_approved_by` 的**值域與謂詞**的單一來源 | 其他任何檔案（`tools/kb.py`／`agent_outline_dump.py`／migration SQL）一律引用本檔常數，**⛔ 不得自行寫出 `outline_approved_by` 字面**——不變量 32 會擋 |

#### 觀測面

| 模組 | 回答什麼命題 | ⛔ 不得怎麼改 |
|---|---|---|
| `trace_view.py`<br>291 行 | 回合軌跡的**渲染層**：`usage_events` 一列 → **只含形狀、不含原文**的敘事視圖。端點與 CLI 共用本檔 | **⛔ 不各寫一份渲染邏輯**——否則兩條路徑的遮罩紀律會漂。⚠️ **渲染層還要再遮一次**：不變量 30 守的是**寫入端**，本檔是**讀出端**，而讀出端會把內容送到人的螢幕、CLI 檔案與 HTTP 回應上（含 `session_id` 遮罩） |

查證：各模組檔頭 docstring 即上表出處，例
`sed -n '1,22p' rag-orchestrator/services/agent/prompt_assembler.py`。

## 2. 一回合的路徑（`agent.turn`）

> 本節是**概覽**；逐步、含每一個分岔與終止點的完整流程見 **§2b**。

```mermaid
sequenceDiagram
  participant L as 呼叫端
  participant F as mcp_facade
  participant R as AgentRuntime
  participant M as 模型
  participant T as 工具/替身
  L->>F: tools/call agent.turn {message, upload_ids?}
  F->>F: 401/403/400 閘、usage_events、每小時上限
  F->>F: 過期？(last_turn_at > 1800s) → 關舊列、開新列、session_expired=true
  F->>F: 照片？→ 取暫存檔/縮圖/分批辨識 → ImageTurnInput
  F->>R: run_turn(identity, message, state, image=?)
  R->>R: 六條程式終止路徑（文件、照片、確認、清單點選、重播），命中即回（不進模型）
  R->>M: 寫入意圖呼叫、標籤呼叫先發（不帶工具）
  R->>R: 程式等意圖結果（_write_draft_program_first）
  alt 欄位齊且非敏感
    R->>T: 程式呼叫 confirm.request（registry.call）
    T-->>R: 確認卡
    R-->>F: TurnResult（卡文字＝回答；主模型沒被呼叫，Verifier 不跑）
  else 程式收尾（要真人、已解決、重送、卡仍有效、剛送出、候選按鈕）
    R-->>F: TurnResult（程式回話；主模型不呼叫或被中斷）
  else 其他回合
    R->>M: 主模型：系統規則＋正本＋dialog＋(照片 facts)＋工具清單
    M-->>R: 主模型提出工具呼叫（jgb2.query.* / kb.* 等）
    R->>T: registry.call 四步
    T-->>R: ToolResult（facts, provenance, scope）
    R->>R: 有 select_scope 且別戶？→ 替換為固定工具訊息（原 facts 不進模型）
    M-->>R: sentences
    R->>R: _write_draft_after_output（意圖晚到可在此出卡，主模型文字丟棄）
    R->>R: Verifier、_state_claim_gate、exit_gates 四道出口閘
    R-->>F: TurnResult{answer, kind, quick_replies, trace}
  end
  F->>F: 存 state、stamp_last_turn、trace 快照
  F-->>L: {answer, kind, handoff, quick_replies, trace_id, session_expired, outcome}
```

**`outcome`（DSP-043）**：第七鍵 `{state, expects, action, ref}`，`state` 八態（answered／clarifying／confirm_pending／confirmed／cancelled／failed／handoff／out_of_scope）由各出口程式設、一般出口依 `kind`／`quick_replies` 導出（`runtime.make_outcome`／`default_outcome`／`receipt_ref`）；呼叫端只看它決定畫面。

**六條程式終止路徑永遠先於模型**（與 §1a／§2b 及 `turn_segments.py` docstring 一致）。順序即契約：①文件回合禁寫 ②文件不可讀 ③照片失敗/逾時/低信心 ④確認機器值 ⑤清單點選 ⑥同題重問重播。這是「機器值不承載意圖」的實作：按鈕與點選不需要模型理解，也不讓模型看到 pid／id 原值。逐條見 §2b 段一。

## 2b. 完整流程（逐步，含每一個分岔與終止點）

> 對碼日：2026-09-12。每一步附可 grep 的符號，⛔ 不寫行號當事實。
> §2 的序列圖是概覽；本節是**全部**分岔——凡是能讓回合在這裡結束的，都列出來。

### 階段 0｜請求層（`mcp_facade`，⛔ 順序固定不得調換）

```
nginx auth_request
  → McpServiceGate（ASGI middleware，最外層）── 擋 initialize／tools/list／DELETE 等非工具請求
  → _invoke（每支工具薄包裝的入口）── 身分只從 SDK request context 取
```

兩處**各跑一次**同樣三道檢查，這是刻意的縱深防禦：

| # | 檢查 | 失敗 | 符號 |
|---|---|---|---|
| 1 | API key | **401，無條件**（⛔ 不看 `RAG_API_AUTH_ENFORCE`） | `require_api_key_unconditional`／`ERR_API_KEY` |
| 2 | Origin 三態 | 403 | `check_origin`／`load_allowed_origins` |
| 3 | `X-JGB-Identity`（**明文 JSON**，⛔ 無 base64）fail-closed | 400／403 | `parse_identity` 直接 `json.loads(raw)` |

第 3 道內部依序：

1. JSON 不合法 ⇒ `400 ERR_IDENTITY_MALFORMED`
2. `_coerce_vendor_id` 取不到 ⇒ **`400 ERR_IDENTITY_NO_VENDOR`**（⚠️ `vendor_id` 是**必填**）
3. `session_id` 缺 ⇒ `400 ERR_IDENTITY_NO_SESSION`
4. `_normalize_target_user` → `normalize_entry_mode`（**順序不得對調**：payload 合法形狀含 list，拿原值比 `=="prospect"` 會是 False ⇒ 留下「受眾說 prospect、謂詞說 b2c」的分裂身分，失敗形狀是**靜默零內容**）
5. `vendor_check(vendor_id)` 不在 vendors 表 ⇒ `403 ERR_VENDOR_UNKNOWN`
6. 不在 key 的 `vendor_ids` 內 ⇒ `403 ERR_VENDOR_OUT_OF_KEY_SCOPE`
7. 回 `Identity(entry="mcp")`——**唯一**把 `entry` 設成 `"mcp"` 的真身分建構點

⚠️ **這道閘只把 `vendor_id`／`session_id` 當必填，`role_id` 是選填（`_opt_str`）——
但下游 `jgb2.query.bills`／`contracts` 對 property_manager 要求 `role_id`（`_identity_gate_ok`
單證），缺就回 `NO_MATCH`。** 因此「身分通過第 3 道」⛔ 不等於「查得到資料」；缺 `role_id`
的 pm 會一路走到轉人固定句（為什麼不是 `NO_DATA_TEXT`，見段四閘 4 下方的紅字）。

**額度**：門面是 `usage_events` 的唯一寫入者（`begin()` → `quota_check()` → 呼叫 → `finalize()`）。
這一層另有兩個出口：`uctx is None` ⇒ **`METERING_UNAVAILABLE`**（計量不可用一律**拒絕服務**，
⛔ 不靜默略過——額度是本系統對呼叫者的唯一控制）；`quota.state == "blocked"` ⇒ **`QUOTA_EXCEEDED`**（429）。

### 階段 1｜`agent.turn` 門面（`_make_agent_turn`）

| 步 | 動作 | 失敗出口 |
|---|---|---|
| 1.1 | 預設模式 `AGENT_ATTACHMENT_INPUT=upload_ids`：帶 `image_urls`／`file_urls` ⇒ 拒；回滾模式 `urls`：帶 `upload_ids` ⇒ 拒，`image_urls` 形狀／張數 ≤ `IMAGE_MAX_COUNT`(10) | `INVALID_INPUT`（⛔ 不截斷後照跑） |
| 1.2 | `attachment_purpose ∈ ATTACHMENT_PURPOSES`；`upload_ids` 份數 `repair` ≤10、`document` ≤1；回滾模式非 document 帶 `file_urls` ⇒ 拒，份數 ≤ `FILE_MAX_COUNT` | `INVALID_INPUT` |
| 1.3 | `message` 與附件**皆空** | `INVALID_INPUT` |
| 1.4 | `app.state.agent_runtime` 缺席 | `NO_MATCH`（門面 preflight 已先回 `AGENT_UNAVAILABLE`） |
| 1.5 | `_outline_for_audience(受眾)` 取不到 ⇒ **fail-closed** | `NO_MATCH`（⛔ 不塞別的受眾的大綱）。**刻意排在 `store.load` 之前**——判不過的回合不該先在 `form_sessions` 留半開的列 |
| 1.6 | 配額**最壞值預扣**：`upload_ids` 先只驗不取（`upload_store.STORE.check`），依判出的型別計「照片張數 ＋ PDF 份數 × `DOC_MAX_PAGES`」，過了才 `claim`；`LIMITS.images_per_hour`／`files_per_hour` | `RATE_LIMITED`（**排在取檔之前**：一張都不取） |
| 1.7 | `namespaced_identity` ⇒ `mcp:{api_key_id}:{vendor_id}:{session_id}` | `INVALID_INPUT`（超長） |
| 1.8 | `store.load` → `is_expired`（30 分鐘）⇒ **先 `close` 舊列再 `start` 新列**（⛔ 順序不得顛倒：先 start 再 close 會把新列一起關掉） | — |
| 1.9 | 大綱不進 `agent_state`：候選章節由 `runtime._select_outline` 每回合現組，`agent_state` 沒有大綱鍵，⛔ 不得序列化進 `collected_data` 的紀律自然成立 | — |
| 1.10 | 照片／文件前處理（`prepare_image_turn`／`prepare_document_turn`）——**bytes 只活在區域變數**，⛔ 不進 state／trace／log | — |
| 1.11 | `asyncio.wait_for(run_turn, AGENT_TURN_TIMEOUT_S − image_elapsed)` | `TOOL_TIMEOUT`；**逾時 ⇒ `store.save` 不執行**，落不了半寫狀態 |
| 1.12 | `stamp_last_turn` → `store.save` | — |
| 1.13 | 回 `AgentTurnOutput` 七鍵：`answer`／`kind`／`handoff`／`quick_replies`／`trace_id`／`session_expired`／`outcome` | — |

### 階段 2｜`_run_turn_body` 四段管線（⛔ 本身不做任何判定，只接線）

#### 段一：`turn_segments.run_program_segments` — **六條終止路徑，順序即契約**

| # | 條件 | 出口 |
|---|---|---|
| ① | 有文件 **且** 訊息是 `confirm_*:<pid>` | `_document_turn_no_write`。**排在確認段之前**——確認段一進去就兌現，那時再擋來不及 |
| ② | 文件擷取不出可用欄位 | 固定句 `DOC_UNREADABLE_TEXT` |
| ③ | 照片失敗／逾時／信心 < `IMAGE_CONFIDENCE_MIN`（⚠️ **程式常數 0.6，⛔ 不是 env**，`test_image_entry_req.py` 斷言 `== 0.6`） | `IMAGE_FAILED_TEXT`／`IMAGE_TIMEOUT_TEXT`／`IMAGE_PICK_CATEGORY_TEXT` |
| ④ | `^confirm_(submit\|edit\|cancel):[0-9a-f]{16}$` **等值 `fullmatch`**（2026-09-12 由 `.match` 改正，見 §8）——帶結尾換行／空白／前後綴一律不觸發兌現 | `_run_confirm_segment`（見階段 3） |
| ⑤ | `select:(bill\|contract\|repair):<id>` **真的是 `fullmatch`**、⛔ 不 NFKC、⛔ 不 strip | `_run_select_segment`：程式直答該筆 facts、寫槽位、記 `select_scope`。⚠️ 另有四條早退**全部回同一句** `SELECT_NOT_FOUND_TEXT`：工具 `not ok`／`facts` 空／`_verify_routes` 取不到（fail-closed）／路由命中——⛔ 不細分，細分等於用回話差別揭露「這筆存在但你看不到」 |
| ⑥ | `handoff_cache[cache_key]` 命中（同題重問） | 逐字重播，`llm_calls=0`、`violations=["replayed_from:<trace_id>"]` |

⚠️ `handoff_cache` 的 `setdefault` **排在 ⑤ 之後**：提早建鍵會讓每個從 ①–⑤ 早退的回合
在 `agent_state` 多一個空 dict，那是會被序列化落庫的狀態形狀改變。

**六段全不命中**才進段二。以上六條**一次模型都沒叫**。

#### 段二：`_build_turn_context` — 狀態容器 ＋ prompt ＋ 九段資料注入

1. `TurnAccumulator(nonce=new_nonce())`——16 位十六進位（⛔ 不用 `secrets.token_urlsafe`，它產 `-`／`_` 會被 `_require_nonce` 擋）
2. `ReservedCallIds`：九個保留前綴 `img-`／`done-`／`entry-`／`aff-`／`ctx-`／`pre-`／`ref-`／`doc-`／`est-`。**無條件保留**——沒有大綱時放行等於讓模型自己造一個叫 `outline` 的來源
3. `_select_outline`：`canon_assembler.get_canon(audience)`（git 正本）→ `FineIndex.visible_subset` → `CandidateSelector.select`（K=5，餘弦）
4. `_seed_outline_provenance`：大綱以保留 `tool_call_id="outline"` **預載成一筆 provenance**（DSP-020；不預載 ⇒ 模型照鐵則引用大綱、Verifier 只認工具回傳 ⇒ 兩次 `QUOTE_NOT_VERBATIM` → `budget_exhausted`）
5. `registry.to_openai_tools` → 文件回合以 `doc_write_face` 濾掉寫入面
6. `assembler.build_messages`（system 整回合**只有一則**）
7. **九段注入**，順序固定：

| 順序 | 段 | citable | 條件 |
|---|---|---|---|
| 1 | 肯定語授權 | ⛔ False | 上一回合 `ask_target=="confirm_intent"` 且本句是肯定語 |
| 2 | 空會話註記 | ⛔ False | `dialog` 長度 0 |
| 3 | 前置查詢 | ✅ True | 整句為 4–9 位數字，或 ≤6 字無數字無標點無空白的短名詞 |
| 4 | 最近編號 | ⛔ False | dialog 最近 6 則＋`completed_actions` 的 4–9 位數字，上限 5 |
| 5 | **文件事實** | ✅ True | 本回合最大的一段不可信文字，⛔ 不得是最後一則 |
| 6 | **`user_message`** | — | DSP-022：使用者那句在**這個位置**注入。🔴 **⛔ 它不是「永遠的最後一則 user 訊息」**——7–10 的 `inject()` 追加的也是 `role="user"`（`turn_context.py::TurnAccumulator.inject` docstring 逐字），且排在它**之後**；只有 7–10 全不成立時它才是最後一則。釘住它的 `test_current_user_message_is_last_message_sent_to_model` 只跑無照片無 context 的回合，**綠燈證明不了「永遠」** |
| 7 | 影像事實 | ✅ True | `image.status ∈ {ok, partial}` |
| 8 | 物件記憶 | ⛔ False | 照片回合且有 `estate_carry`；⛔ 釘住範圍時不注入 |
| 9 | 完成動作記憶 | ✅ True | 非空且（有範圍時）同戶 |
| 10 | 呼叫端進場句 | ⛔ False | `context` 參數非空 |

⚠️ 1–5 排在 `user_message` **之前**，7–10 排在**之後**——這是既有債（Plan 列 L-W9-a），
動它會改變照片線的訊息順序。

#### 段三：`_run_model_loop`

```
while True:
  deadline 到 ⇒ build_fixed("budget_exhausted")
  chat.completions.create(parallel_tool_calls=False, response_format=strict json_schema)
  ├─ 有 tool_calls ─────────────────────────────────────────────
  │   逐支：
  │     身分鍵出現 ⇒ 記 IDENTITY_KEY:<key> violation（⛔ 不擋，剝除靠 registry）
  │     不在 visible_names ⇒ 記 FORBIDDEN:<name>（⛔ 只記不擋）
  │     在 doc_write_face ⇒ **第二道網，直接回 NO_MATCH、⛔ 不呼叫 registry**
  │     registry.call 四步（可見性 / 速率 / schema / 執行）
  │       TOOL_TIMEOUT ⇒ 重試一次（也計預算）；再逾時 ⇒ tool_unavailable
  │       registry 例外 ⇒ tool_unavailable
  │     L15 範圍比對（有 select_scope 時）：別戶就地換空殼——**三份全換**
  │       （text_for_model / provenance / data），只換一份＝fail-open
  │     estates keyword 查到唯一物件 ⇒ 寫 estate_carry
  │     模型自呼 confirm.request ⇒ A+ 三開關（AGENT_WRITE_DRAFT／LIFECYCLE／PROPOSAL）皆 on 時
  │       只當提議（_write_proposal_handle：參數經值閘併入草稿，下一步由程式決定），
  │       ⛔ 以模型參數出卡；文件回合、文件暫存回合、點選範圍回合、影子回合例外（見階段 3）
  │     confirm.request 成功 ⇒ **這一回合立刻結束**（見階段 3）
  │     session.slots.set 成功 ⇒ 槽位寫回 state（⛔ 勿刪：_save 是整包覆蓋不是 merge）
  │     包成資料段：有 provenance 走 wrap_provenance_data（行首標記
  │       `[{nonce}:{tool_call_id}:{source}§{i}]`），無 provenance 走 wrap_tool_data
  │   預算耗盡 ⇒ build_fixed("budget_exhausted")
  │   continue（回迴圈頂端再叫一次模型）
  └─ 無 tool_calls（模型嘗試給最終答案）────────────────────────
      AgentOutput.model_validate 失敗 ⇒ 記一次 rewrite、回饋 SCHEMA、continue
      改寫分支 A「HANDOFF_DATA」：kind=handoff ∧ reason ∈ NON_SENSITIVE_HANDOFF_REASONS
        ∧ fact_class ∉ 敏感五類 ∧ 有工具結果 ∧ 非「每筆都 ok 且 empty」⇒ 消耗一次 rewrite
      改寫分支 B「RECENT_REFS」：同上但**零工具呼叫** ∧ 本回合注入過最近編號
      ⚠️ NON_SENSITIVE_HANDOFF_REASONS 是**封閉白名單** = {no_grounding, llm_mentioned_handoff}
         ⛔ 不等於「非敏感」——budget_exhausted 非敏感卻不在集合內，T2 出口正是靠這個差別成立
      ⚠️ 兩條在**預算已耗盡時直接跳過**，⛔ 不走 rewrite_exhausted——否則
         handoff_reason 會變成 budget_exhausted，T2 出口閘永遠到不了
      寫入情境回合（草稿存活或 session 有綁定卡；`_write_context_turn`）且 kind≠handoff：
        非問句回合的任何 kind、問句回合的 ask／recommend ⇒ 模型文字丟棄，
          程式狀態回話結束回合（`_write_reply_program_exit`，見階段 3 末）
        問句回合的 answer ⇒ 往下走，最後由程式接狀態行（乙′）
      resolve_refs(out, tool_results_by_id, nonce)  ← nonce 是「出自本回合」的唯一憑據
      verifier.verify(...)  九步（見下）
      verdict.ok=False ⇒ 記一次 rewrite、回結構化拒因＋修法句、continue
      verdict.ok=True  ⇒ 帶狀態句判讀閘（`_state_claim_gate`，kind≠handoff）：
        LLM 判讀回覆是否宣稱等待確認／已完成／已取消／已轉人，任一類對不到程式狀態事件
        ⇒ 模型文字 ⛔ 送出、⛔ 進 dialog，換程式句（`_state_claim_replace_exit`）
        ⇒ 組 TurnResult（句末標點正規化只套模型文字）
        ⇒ 乙′ 回合：`_write_reply_model_plus_status` 接狀態行；其餘 finalize
```

**Verifier：程式自述「七步」、本文列「九步」——⛔ 不是矛盾，是顆粒度不同。**
`verifier.py` docstring 的七步是①敏感五類 ②白名單句型 ③覆蓋＋極性 ④來源可引用
⑤導流白名單 ⑥禁詞（⑥′文件回合）⑦handoff 詞後置掃描；本文把第①步**拆成四個子步**
（①／①敏感樣式表／①′／①-b，記號上也標了子步），③④在程式裡是同一支 `_ref_failures`。
⚠️ 引用步數時**指明是哪一種顆粒度**，⛔ 不要只寫數字。

逐步（本文顆粒度）：① fact_class／handoff 原因配對 → ① 敏感樣式表
→ ①′ `marker_in_answer` → ①-b `ask_target_invalid` → ② 逐筆 schema → ③④ `_ref_failures`
→ ⑤ `_verify_routes` → ⑥ `forbid`／⑥′ `docturn` → ⑦ `scan_handoff_mentions`。
**擋或只記**由 `verdict_class()` × `_OBSERVED_CLASSES_BY_MODE` 查表決定，
模式值域封閉 `("enforce", "grounding_observe", "observe_only")`。
⚠️ 模式感知在 `verify()` **內部**——外層翻判定會讓先命中的引用類把機敏類整段跳過。

### 階段 3｜寫入鏈（唯一能改 JGB 資料的路）

```
confirm.request(summary, payload)
  呼叫者：程式依寫入草稿觸發（_write_draft_decide；DSP-085、DSP-091）。
  模型自呼：A+ 三開關皆 on ⇒ 只當提議——_write_proposal_merge 把參數（巢狀 {action, payload}
    只解一層）經值閘併入草稿，程式決定出卡、追問，或回固定句（提議沒有值時：
    卡仍有效且草稿＝卡 ⇒ PROPOSAL_NO_VALUE_CARD_TEXT＋同一張卡，否則 PROPOSAL_NO_VALUE_TEXT）；
    回合沒有因此結束時（凍結回合、同回合已觸發、動作不合等），⛔ 退回以模型參數執行；
    `AGENT_WRITE_REPLY_PROGRAM` on 時，寫入情境的非問句回合由程式結束回合
    （`_write_reply_kd3_exit` ⇒ 程式狀態回話，不再叫模型寫回覆）；問句回合模型拿到封閉結果
    HANDLED_BY_PROGRAM／NO_MATCH 後回答提問，回覆經判讀閘，程式再接狀態行。程式呼叫結果
    非終結時同此處置。
    例外（仍以模型參數呼叫）：文件回合、文件暫存有效回合、點選範圍回合（A-2 接手）、影子回合；
    開關 off 時亦同。
  → ⚠️ **成功有兩種形狀**：
     (a) 對到單筆 ⇒ 產卡（下行）
     (b) 以 estate_name＋period 對到**多筆** ⇒ `_bill_candidates_result` 回候選形狀
         （⛔ 無 card／pending_id）⇒ `_begin_pending_confirm` 收成一個 **ask 回合**：
         `CONFIRM_CANDIDATES_TEXT` ＋候選清單＋最多 `CONFIRM_CANDIDATES_MAX` 顆
         `select:bill:<id>` 按鈕；⛔ 不建 pending、⛔ 不發 token
         （A-2a 生效時改由 `_write_candidates_exit` 列 `pick:` 候選；`AGENT_PICK_RIGHT` 生效時延期
         先解析物件、再列該物件的帳單，見下方「寫入時選對紀錄」）
  → (a) 程式依 action＋payload 決定性產卡（confirm_card.render）；
        handler 同時驗 payload 形狀與**分類是否在樹內（⚠️ 缺值放行，不擋）**
  → 發 token（DB 只存雜湊與 pending_id）
  → 三顆 quick reply：confirm_(submit|edit|cancel):<pending_id>
  → ⚠️ 有 select_scope ⇒ _scope_gate_confirm_request 先比物件，別戶**不建 pending**
        （⚠️ 比的欄位不同：**報修比 `estate_id`**、**延期現查該帳單的物件**）
  → ⚠️ 文件回合 ⇒ _document_turn_no_write（第三道網）
  → _begin_pending_confirm 存 {action, payload, card_sha256, estate_id}
  → 回合以 kind=ask 結束；**卡文字逐字＝TurnResult.answer，模型輸出丟棄、Verifier 不跑**
  → 卡外另附 `hint`（同物件未結單）
  ⚠️ **例外**：`data` 形狀不符（缺 `card`／`action` 值域外／`payload` 非 dict）⇒
     `_begin_pending_confirm` 記 `confirm_request_data_shape_invalid` 後回 `None`，
     **模型迴圈繼續跑**，⛔ 不是「立刻結束」

下一回合，使用者按鈕（段一 ④）
  → redeem_pending 先燒 token、比對卡雜湊
  → registry.call(jgb2.action.<x>, {payload, confirmation_token})
  → 工具內 assert_redeemed **再驗一次**（pool 缺席 ⇒ False ⇒ CONFIRMATION_REQUIRED，fail-closed）
  → 寫替身（services/jgb/transport.py）或真 JGB
  → receipt 存回 pending（重送回同一 receipt）
```

失敗誠實回 `ACTION_FAILED_TEXT`；取消燒 token 但 ⛔ 不覆蓋既有 receipt；
pid 不在本 session（含過期後舊鍵）⇒ 固定句「這筆確認已失效」。

**寫入情境的程式狀態回話**（`_write_reply_state`，`AGENT_WRITE_REPLY_PROGRAM` on 且 A+ 出卡開關 on；
唯讀判定，⛔ 出新卡、⛔ 建 token）：依序 (1) 綁定卡仍有效且草稿＝卡 ⇒ `CARD_STILL_VALID_TEXT`＋這次讀到的值
（`card_read_values_text`；使用者給的值被丟棄時改 `CARD_UNCHANGED_TEXT`、不列值）＋同一張卡與同 pid 三顆鍵；
(2) 綁定卡有效、與草稿不同 ⇒ `CARD_DIFFERS_TEXT`＋卡；(3) 草稿缺欄 ⇒ `MISSING_FIELDS_ASK_TEMPLATE`
（`WF.missing_labels` 依草稿算；欄位齊但封閉三動作的名稱對到多筆或物件無唯一有效合約 ⇒ 依出卡路徑
同一支 `_prepare_closed_action` 的缺欄清單，`closed_action_missing_labels`）；(4) 有草稿未出卡，或無草稿但 session 有綁定卡 ⇒ `WRITE_NOT_ISSUED_TEXT`；
(5) 無草稿、無綁定卡 ⇒ `NO_PENDING_WRITE_TEXT`。trace 記
`write_reply_state:<分支>`、`write_reply_source:program`／`model_plus_status`。
帶狀態句判讀閘（`state_claim.judge_state_claims`，`AGENT_STATE_CLAIM_GATE` on）：輸入只有回覆文字、
以 nonce 資料段包住，輸出上限 200 token、逾時 4 秒；「等待確認」只指內容已整理好、只等使用者
確認或送出的回覆，請使用者選哪一筆紀錄、提供或補充資料、核對名稱編號或條件的回覆不算
（`STATE_CLAIM_SYSTEM_PROMPT`）；對不到事件記 `state_claim_unbacked:<類別>`，
寫入情境回合換成上列狀態回話、其他回合換 `NO_PENDING_WRITE_TEXT`、已轉人換 `HANDOFF_OFFER_TEXT`；
判讀失敗時可出卡回合（寫入情境、點選範圍、文件、文件暫存）同樣換句，其他回合照送並記
`state_claim_check_failed`。`prose_confirm_suspect`（`kind=ask` ∧ `ask_target=confirm_intent` ∧
本回合無 `confirm.request`）直接當「等待確認」未對到，不呼叫判讀。判讀原文 ⛔ 進 trace、snapshot、log。

**寫入時名稱對到多筆的候選清單**（A-2a，DSP-103；`AGENT_WRITE_CANDIDATES` on 且 A+ 三開關 on，`_write_candidates_active`）：
程式依草稿出卡時，`manual_bill_create`（合約、物件）、`contract_create`（物件）、`repair_create`（物件）、
`bill_due_extend`（帳單）的名稱對到多筆 ⇒ `_write_candidates_exit` 由程式列清單結束回合：
候選列出自出卡前同一次帶 viewer 的查詢（只在 `role_id` 與 `user_id` 皆有值時列），候選集
`agent_state["write_candidates"]`（`{action, field, type, ids≤20, has_more, name_fp, creator, picked}`，
`write_candidates.load_write_candidates` 驗形狀）存全部 ≤20 個編號，畫面列前 10 筆（`AGENT_PICK_RIGHT`
off 時 5 筆，`write_candidates.candidates_shown_max`）＋每筆一顆
`pick:<contract|estate|bill>:<id>` 按鈕，多於畫面筆數或上游還有下一頁接 `CANDIDATES_MORE_TEXT`
（「還有其他筆，不在其中請講編號。」）。選定兩條路，成立與否都由程式判：
(a) 按鈕：`pick:` `fullmatch` 後由 `_write_candidate_pick_begin` 判（候選集、建立者、型別、欄位、
編號、草稿動作皆吻合，且非點選範圍、文件、影子回合）；不成立回 `CANDIDATE_PICK_INVALID_TEXT`、
⛔ 任何 JGB 查詢與模型呼叫；(b) 打字：意圖判斷呼叫附上候選集內各列（nonce 資料段）與 `pick_id` 動態 enum，
`_write_candidates_typed` 只收候選集內編號；整句是候選集外的編號 ⇒ 帶 viewer 精確查、名稱相同才成立
（`pick_matches_name`）；其餘非問句重列同一份候選。選定成立後程式依草稿觸發 `confirm.request`，
選定編號只經程式專用通道 `program_pick`（`ToolRegistry.call` 具名參數，唯一設定點在程式依草稿觸發處）
傳到 `_prepare_closed_action`；模型參數裡的 `estate_id`／`contract_id` 一律丟棄（模型給的 `bill_id`
維持現行路徑）。候選集在 `clear_write_draft` 與出卡時清除；由 `program_pick` 出的卡，選定改存在該待確認筆
（`write_candidates.CARD_PICK_KEY`，讀回以 `load_card_pick` 驗形狀、建立者、名稱指紋），卡後更正其他欄位時
程式依草稿重出卡。可帶回的回合，意圖判斷呼叫多一個必填封閉欄位 `record_rechoice`（`same`／`other`，
`write_forms.RECORD_RECHOICE_KEY`；AI 只回答使用者這句有沒有要換另一筆紀錄，⛔ 回編號），其餘回合系統句與
schema 不變。只有 AI 恰好回 `same`、那張卡在本回合燒卡前仍有效、草稿是同一份、名稱欄未改，才由
`_write_candidates_card_pick` 帶回同一筆（仍經 `program_pick`、出卡端照樣帶 viewer 精確查）；回 `other`、
沒回、值不合或意圖呼叫失敗 ⇒ 不帶回，照草稿名稱重新解析，名稱多筆即重列候選（同一句改的其他欄位保留）；
名稱欄改成別的名稱則照新名稱重新解析。trace 只記型別與筆數：
`write_candidates_shown:<型別>:<n>`、`write_candidate_pick:button|typed`、`write_candidate_pick_invalid`、
`write_candidate_reask`、`write_candidate_carry:same|declined`、`write_candidate_rechoice`。
開關 off ⇒ 名稱多筆的出口與 B 逐字相同。

**寫入時選對紀錄**（`AGENT_PICK_RIGHT` on 且 A-2a 生效，`write_forms.pick_right_effective_from_env`；
計畫 `plan-pick-right-record-20261021.md`）：
(1) 延期繳費先解析物件（`tools/confirm._pr_resolve_bill`）：身分前置——`role_id` 與 `user_id` 皆有值且過
`jgb2._identity_gate_ok`，缺一 ⇒ 0 次出向；物件名稱同名多筆 ⇒ 先列**物件**候選（`pick:estate:<id>`，
`write_candidates.candidate_types_of`；trace `pick_right:estate_first`），程式選定的物件以 `_estate_by_id`
帶 viewer 重驗。該物件的帳單＝`_viewer_contract_rows` 中該物件的合約逐份 `get_bills(contract_ids=<單一>,
page=…)`（每合約 ≤`PR_PAGES_PER_CONTRACT`＝3 頁、總計 ≤`WRITE_CANDIDATES_MAX` 張，迴圈以次數計）聯集現行
keyword 查詢，每列斷言 `contract_id`／`estate_id` 相符；合約或帳單清單達上限仍有下一頁 ⇒ 不做「唯一一張」判定。
帳單候選集另帶 `scope_estate_id`（`write_candidates.SCOPE_ESTATE_KEY`），之後改講金額或期間只在同一個物件重查
（`scope_pick_of`）。
(2) 比對客人講的值：表單多兩欄 `said_amount`（int，過數字值閘）、`said_range`（`bill_period.parse_said_range`
封閉語法「M/D 到 M/D」「M月D日到M月D日」，程式從原話解析），不上卡、⛔ 進 body；物件或期別變動即清掉
（`runtime._pick_right_said_reset`）。期別篩後再依 `bill_amount_matches`／`bill_range_matches` 篩；0 張相符但該期
有帳單 ⇒ 前言 `PR_*_MISMATCH_TEXT` 說明對不上並列該期（無期別則全部）帳單（trace
`pick_right:amount_mismatch`／`range_mismatch`）；打字選定與講的值不符 ⇒ 重列（`PR_REASK_TEXT`，⛔ 回顯原話）；
按鈕選定不符 ⇒ 照按的出卡、卡上加「提醒」行。
(3) 候選列一律經 `write_candidates.minimize_row` 白名單（`PICK_RIGHT_ROW_KEYS`；⛔ 承租人資料、地址、經緯度、
`user_id`、`sub_title`、`payment_id`、`invoice_number`），給人看的清單與給意圖呼叫的資料段共用寫入候選專用
投影（`_PR_PROJECTORS`；唯讀查詢的 `_ROW_PROJECTORS` 不動），逐列 `sanitize_data_piece`、nonce 包住。
(4) 卡上可分辨欄位（`AGENT_PICK_RIGHT` on 即生效，含寫入生命週期 off 與模型自帶 `bill_id`）：延期卡加
物件名稱＋編號、帳單標題、帳單金額、計費期間；修繕卡、建合約卡加物件位置（縣市區＋樓層）；補開帳單卡加
合約期間。值只由程式從帶 viewer 查得的系統列寫進 `confirm_card.PICK_DISPLAY_KEY`（模型帶的同名鍵在入口一律丟掉），
進 `payload_sha256`；JGB 自由文字含 `sanitize_data_piece` 會改動的字元或超長 ⇒ 印「—」。延期卡的物件由帳單列
`estate_id` 反查，與草稿物件名不一致 ⇒ 查無固定句、⛔ 出卡。
trace 標記只記碼（⛔ 金額、名稱、期間）。開關 off ⇒ 與 A-2a 逐字相同（模型自帶的 `sys_pick_display` 仍在入口丟掉）。

**寫入時名稱講不準**（F12，DSP-112；`AGENT_NAME_LENIENT` on 且 A-2a 生效，`name_match.name_lenient_effective_from_env`；
計畫 `plan-name-lenient-f12-20261022.md`）：
(1) 寬鬆比對（`name_match.py`）：`prefilter` 以讀音單位最長共同子序列對名稱核心（正名去【…】［…］與括號內文字）
打分，分數 ≥`NAME_LENIENT_MIN_SCORE`＝2、取前 `NAME_LENIENT_PRE_K`＝50（清單第一頁 ≤`NAME_LENIENT_LIST_MAX`＝200 筆）；
`ai_pick` 一次模型呼叫，送模型每列只有 `id`、`title`、nonce 包住，輸出只收恰好一個 `{ids}` 物件、每項須精確等於
送出清單內編號，解析失敗、逾時（`NAME_LENIENT_TIMEOUT_S`＝6）、例外 ⇒ 空（⛔ 重試、⛔ fail-open）；`augment` 補齊
同名與前篩分數不低於 AI 所挑最低分者，上限 `NAME_LENIENT_CAP`＝5，候選 ⊆ 送模型清單。結果一律走 A-2a 候選出口
（⛔ 寫 payload 的編號、⛔ 回唯一），每回合寬鬆 ≤1 次（`NameLenientTurn` 的 `run_once`）；AI 回空 ⇒
`NAME_NOT_FOUND_TEXT`。
(2) 觸發點（`tools/confirm.py`）：(甲) 名稱解析查過零筆（`_name_lenient_result`）；(乙) 合併後名稱欄仍空、即將追問且
本回合打字（`missing_name_lenient`）；(丙) 名稱先查（`name_early_lookup`）——修繕、建合約、手開帳單、延期繳費，名稱
本回合講、其他欄位仍缺 ⇒ 當回合依名稱查，多筆即列候選、查無接 (甲)、唯一照現行追問。身分閘在任何出向之前
（`_name_lenient_identity_ok`），清單查詢帶 `role_id` 與 `viewer_user_id`；⚠️ 真 JGB `GET /estates` 不吃 viewer，
物件清單在真機是團隊範圍。
(3) 選定後回合（`runtime._write_candidates_cmd_turn`；計畫 `plan-post-pick-commands-20261024.md`）：回合開始已選定、
仍綁定本草稿時，意圖呼叫改送指令版 schema——`target` 為依序指令 `{op, value}`，`op` ∈ `pick`／`nth`／`name`／`clear`
（`write_forms.PICK_TARGET_OP_DOMAIN`；規則句 `PICK_TARGET_RULE_TEMPLATE`，⛔ 改字面），未選定、已撤回、無候選集的
回合 schema 與系統句不變。程式逐項驗（`_write_candidates_cmd_effect`）、最後一個生效：`pick` 須在本回合列出且屬
候選集；`nth` 對畫面清單；`name` 對到的列含現選定或屬原講法 ⇒ 維持，清單裡唯一一筆、且名稱是本句原字 ⇒ 改選那筆，
對到多筆 ⇒ 撤回重列，清單外名稱且是本句原字 ⇒ 解綁前先用解綁後同一組查找查一次（`_write_candidates_name_precheck`、
`tools/confirm.name_precheck_ids`），查到含現選定 ⇒ 維持，否則解綁依新名稱重查；`clear` 或無效 ⇒ 撤回並重列同一份候選。
選定後回合的名稱值一律不由意圖 `fields` 寫入（記 `write_candidate_name_kept`）。trace 只記封閉碼
（`write_candidate_cmds:<碼依序，逗號連>`、`write_candidate_cmd_last:<碼>`、`write_candidate_name_precheck:keep|miss`）。
⚠️ 已知未處理（DSP-112；「雙胞胎與手開帳單合約」片暫停至上線後，DSP-115）：除編號外完全相同的同名物件照樣列兩顆按鈕；手開帳單講物件只取該物件的有效合約
（`_valid_contracts_of_estate`），已結束合約不在候選內。

### 回合的全部終止點（一張表，18 列）

⚠️ **引用時指明顆粒度**：表是 **18 列**，但**列數 ≠ 終止點數**——第 4 列「文件禁寫／文件不可讀／照片三條」一列就含 5 個終止點。⛔ 不要報「共 N 個終止點」這種彙總數字，它從表裡導不出來；要數就照段一六條＋段四四道各自數。

| 出口 | 從哪來 | `kind` |
|---|---|---|
| 401／403／400 | 階段 0 三道請求層檢查 | （不成回合） |
| `QUOTA_EXCEEDED`(429)／`METERING_UNAVAILABLE` | 階段 0 `_invoke` 的額度／計量 | （不成回合） |
| `INVALID_INPUT`／`RATE_LIMITED`／`NO_MATCH`／`TOOL_TIMEOUT` | 階段 1 門面 | （工具錯誤） |
| 文件禁寫／文件不可讀／照片三條 | 段一 ①②③ | `answer` |
| 確認兌現／取消／失效 | 段一 ④ | `answer` |
| 清單點選直答 | 段一 ⑤ | `answer` |
| 同題重問重播 | 段一 ⑥ | `handoff` |
| `budget_exhausted`（deadline／工具數／改寫數） | 段三 | `handoff` |
| `tool_unavailable`（registry 例外／兩次 TOOL_TIMEOUT） | 段三 | `handoff` |
| 確認卡 | 段三 `confirm.request` 成功**對到單筆** | `ask` |
| **確認候選清單** | 段三 `confirm.request` 對到**多筆**（`_bill_candidates_result` ⇒ `_begin_pending_confirm` 候選分支）；⛔ 不建 pending、⛔ 不發 token | `ask` |
| **範圍外不出卡** | 段三 `_scope_gate_confirm_request`（⛔ 不經 `exit_gates.finalize`，是段三獨立的 return） | `answer` |
| **寫入候選清單** | 段三：程式依草稿出卡時名稱對到多筆（`_write_candidates_exit`，`AGENT_WRITE_CANDIDATES` 生效）；程式列清單＋`pick:` 按鈕、寫候選集；⛔ 出卡、⛔ 建 token、⛔ 寫草稿 | `ask` |
| **候選選定失效** | 段三前：`pick:` 機器值不成立（`_write_candidate_pick_begin`）⇒ `CANDIDATE_PICK_INVALID_TEXT`；⛔ JGB 查詢、⛔ 動草稿與 token、⛔ 呼叫模型 | `ask` |
| **寫入情境程式狀態回話** | 段三：寫入情境回合模型輸出被丟棄（`_write_reply_program_exit`）、提議未發或程式呼叫非終結（`_write_reply_kd3_exit`）；⛔ 不經段四 | `ask`／`answer` |
| **帶狀態句換句** | 段三判讀閘（`_state_claim_replace_exit`）；⛔ 不經段四 | `answer`／`ask` |
| 模型正常作答（過 Verifier、判讀閘） | 段三 → 段四（乙′ 回合由 `_write_reply_model_plus_status` 接狀態行） | `answer`／`ask`／`recommend`／`handoff` |
| 四道閘改寫後的固定句 | 段四 | `answer`／`ask` |


## 3. 八種情境走查（一則訊息進來，走到本系統回出什麼）

⛔ **本節只寫本系統內部**：呼叫端是誰、使用者在什麼畫面操作、機器值被畫成什麼按鈕，
一律**不屬於本系統**（檔頭已述）。下文一律稱「呼叫端」。

🔴 **2026-09-12 補寫**：§2b 是「管線有哪幾段」，本節是「**實際一句話怎麼走完**」。
讀者問「其他情境也一樣嗎」時，§2b 答不出來——它只到元件層。

#### 情境 1：寫入類（延後繳款）

**輸入**：呼叫端送進一則 pm 身分的訊息——「基隆獨立共生公寓雅房九月的房租，房客說想晚三天繳」
（⛔ 哪一個外部系統送的、使用者在哪個畫面打的，都**不屬於本系統**，見檔頭）

1. **進門**：三道閘過（`vendor_id=2`、`role_id=37305`、受眾 pm）
2. **13 步**：1.5 取 `canon/jgb/`（九架正本，target_user=property_manager 篩選結果）大綱**取得到**（取不到就 `NO_MATCH`，
   且**刻意排在建 session 列之前**）→ `store.load` 查無 ⇒ `start` 新列
3. **段一**：六條全不符 ⇒ 叫模型
4. **段二**：九段只有 ②空會話註記 與 ⑥`user_message` 成立；
   同時選好大綱 5 條候選，以 `tool_call_id="outline"` 預載
5. **段三**：寫入意圖呼叫、標籤呼叫先發，程式等意圖結果（有草稿等 3 秒、無草稿等 1 秒）。寫入意圖呼叫回動作
   `bill_due_extend` 與欄位值（物件名、期別、天數），程式過值閘後併入寫入草稿（`_write_draft_decide`）。
6. **程式出卡**：欄位齊且非敏感 ⇒ 程式自己產生一次 `confirm.request`（`_write_draft_program_message`），走 `registry.call`，
   主模型本回合不被呼叫。⚠️ `bill_due_extend` 只有 `USE_MOCK_JGB_API=true` 走得到出卡；接真 JGB 回固定句（見 §8）。
   工具內帶 viewer 查物件與帳單，期別交給 `bill_period` **純函式**解析（⛔ 不讀時鐘、不查 DB、不叫模型；
   表外講法一律 `None`，⛔ 不猜）。**房東不會講帳單編號**，所以 `estate_name` 與 `period` 兩欄可代替它。
   意圖等不到才叫主模型：主模型若也呼叫 `confirm.request`，只當提議（見 §2b 階段 3）；輸出後由
   `_write_draft_after_output` 接手，這時才有主模型文字要丟棄。
7. **回合結束**：卡文字逐字＝回答，Verifier 與段四都不跑

**本系統回出去的**：確認卡文字 ＋ 三個機器值 `confirm_submit`／`confirm_edit`／`confirm_cancel`
（**寫死在 `form_contract.py`，值一個都不准改**——它們是**對外契約**，⛔ 呼叫端怎麼把它們畫成按鈕不屬於本系統）

**第 2 回合（按下確認）**：`message` ＝ `confirm_submit:a3f19c2e8b4d7061`
⇒ **段一④ 命中，模型一次都沒被叫醒**。`fullmatch` 比對（帶換行／空白／前後綴一律不觸發，
⚠️ 失敗方向是**多執行一次寫入**，⛔ 不得改回 `.match`）⇒ 執行 ⇒ 標 `executed`（冪等）
⇒ `render_receipt` ⇒ **`completed_actions` 記一行封閉值**（沒有這步，下一句問
「剛剛那張單號多少」答不出來——回執原本只進 `trace`／`outcome`）。

#### 情境 2：純查詢（不建單）

「這期的滯納金多少」⇒ 模型選 `jgb2.query.bills`、face 填 `滯納金`（**封閉 enum，只能從 15 個裡挑**）
⇒ `bills.py` 的 builder **決定性算 facts**（⛔ 不是 LLM 算）⇒ 模型組話 ⇒ Verifier 驗每句指回片段編號。

⚠️ **現行形狀的硬限制**：builder 簽名是**單列** ⇒「這戶今年繳了幾期」**答不出來**；
多列一律走 `_ok_candidates` 變候選清單。

#### 情境 3：清單點選（呼叫端回傳機器值）

呼叫端送回機器值 `select:bill:88291` ⇒ **段一⑤，模型與 Verifier 都不跑**。
⚠️ 這個機器值**由本系統定義、由呼叫端原樣送回**——⛔ 呼叫端用什麼介面呈現那張清單不屬於本系統。
守門順序**與確認段完全相同、⛔ 不得調換**：
① `entry != "mcp"` 整段不執行 ② `readonly_view`（影子）不執行——**影子與正式共用 `session_id`**，
影子若寫槽位，正式那邊就被改掉了，而使用者根本沒點過任何東西 ③ **`fullmatch`、⛔ 不 NFKC、⛔ 不 strip**。

`answer` **逐字＝該域 builder 的程式產出**；同時寫 `select_scope`，**範圍從此釘住**。
⚠️ 不跑 Verifier **≠ 沒有出口檢查**：facts 出去前仍過 `_verify_routes`，email 面由封閉表擋。
⚠️ 找不到那筆時**四種原因全回同一句**——⛔ 細分等於用回話差別洩漏「這筆存在但你看不到」。

#### 情境 4：範圍退出

範圍釘住後問「那另一戶的呢」⇒ `scope_out>0 且 scope_in==0` ⇒ **閘 1 命中**：
五欄一起改、⛔ 不進 handoff cache、清 `estate_carry`。
**它排第一道是刻意的**——「唯一接句點，排在 handoff cache 與 dialog 之前」，
所以 dialog 存的是**使用者真正看到的那一句**。

#### 情境 5：照片報修

1.1 張數 ≤10（超過 `INVALID_INPUT`，**⛔ 不截斷後照跑**）→ 1.6 **按張數預扣，扣不過一張都不抓**
→ 1.10 縮到 `IMAGE_MAX_PX=1024`，vision `detail` **程式釘死**（⛔ 不由 env——
「那會讓一張照片要花多少錢變成部署者可調的東西」），**bytes 只活在區域變數**
→ 段一③ 失敗／逾時／`confidence < 0.6` 且候選 ≥2 ⇒ 三句固定話，**模型不被叫醒**。

🔴 **`ImageTurnInput` 刻意沒有 `description` 欄**＝封閉值原則：**不讓模型的自由文字進入後續流程**。
這正是 §4c 文件線要處置的那道相撞。

#### 情境 6：文件上傳

見 §4c。兩個終止點在段一①②；Verifier 多跑 ⑥′。

#### 情境 7：售前（prospect）

**這條路幾乎不碰 jgb2**：

| 工具 | prospect | property_manager |
|---|---|---|
| `kb.search` | ❌ **stage 無 prospect 鍵 ⇒ 永不可見** | ✅（門面照列；**給不給模型依資料狀態**：舊知識庫零列已審時不給，見 §8） |
| `kb.get` | ✅（但見下） | ✅ |
| `jgb2.query.*` | stage 有，但**沒有 `role_id`／`user_id`** ⇒ 身分閘一律 `NO_MATCH` | ✅ |

⇒ **售前的答案幾乎全部來自路 A 的 canon 大綱**。
⚠️ `kb.get` 目前對每一列都回 `NO_MATCH`（`^reviewed:\S+$` 形狀本機 0 筆，D1 前的預期行為）。
⇒ **售前答不出來時，先看回合紀錄的候選 5 條有沒有對題細目，再看細目內容有沒有寫到。** 正本 543 條細目全部已審，1,753 條講法全部 `approved`（DSP-129）。

#### 情境 8：同題重問

**段一⑥**：`handoff_cache` 命中 ⇒ 逐字重播，`llm_calls=0`，記 `replayed_from:<trace_id>`。
⚠️ `setdefault` **刻意排在⑤之後**：提早建鍵會讓每個從①–⑤早退的回合都多出一個空 dict，
**那是會被序列化落進 `form_sessions.collected_data` 的狀態形狀改變**。

#### 共同骨架：八種裡有四種模型根本不會被叫醒

⚠️ **「模型講的話」與「程式產的文字」是兩種輸出，規則完全不同**——混成一欄會讓人以為情境 1 的答案沒有引用來源。拆開如下：

| 情境 | 模型 | Verifier | 模型那句話引用什麼 | 另外由程式產出的文字 |
|---|---|---|---|---|
| 1 寫入 | 一般路徑 ❌（意圖先到就出卡）；意圖逾時才 ✅，文字丟棄。欄位值來自寫入意圖呼叫 | ❌（出卡回合不跑） | — | **確認卡**（`render(action,payload)`）＋**回執**（`render_receipt`） |
| 2 純查詢 | ✅ | ✅ | 工具回傳的 facts（builder 決定性算） | — |
| 3 清單點選 | ❌ | ❌（但過 `_verify_routes`） | — | **整段 answer ＝ builder 產出** |
| 4 範圍退出 | ✅ | ✅ | （模型原本那句被換掉） | 閘 1 的 `SCOPE_EXIT_TEXT` |
| 5 照片 | 三種情況 ❌ | — | — | 三句固定話 |
| 6 文件 | 兩種情況 ❌ | ✅（多 ⑥′） | `build_document_facts` 組的句子 | 讀不出欄位時的 `DOC_UNREADABLE_TEXT` |
| 7 售前 | ✅ | ✅ | **canon 大綱細目**（路 A） | — |
| 8 重問 | ❌ | ❌ | — | **逐字重播上次的 answer** |

#### 為什麼確認卡與回執 ⛔ 不能是模型寫的

`confirm.request(summary, payload)` 的 `summary` 是**模型的自由文字**，
`payload` 才是**真正會被送去執行的參數**——兩者由模型分別填 ⇒ **可以不一致**：
卡上寫「延 3 天」、payload 寫 90 天，**使用者按下確認時同意的是他看到的那張卡，
系統執行的卻是 payload**。

DSP-038-2 的處置是把三者綁死：

```
卡文字 = render(action, payload)      ← 只從 payload 導出，模型碰不到
summary_sha256 = sha256(卡文字)       ← 存進 agent_confirmation_tokens
TurnResult.answer = 卡文字（逐字）      ← 使用者看到的就是這一份
```

⇒「使用者看到的字」「表裡的雜湊」「將被執行的 payload」是**同一份資料的三種形式**，
⛔ 中間沒有模型可以插手的縫。

`render()` 的硬約束：同 payload 必得同一字串（⛔ 不讀時鐘／env／DB、⛔ 不叫 LLM、
⛔ 不依賴 dict 插入順序）；**缺欄位就 raise**，⛔ 不用預設值補、⛔ 不印半張卡
——半張卡會讓使用者對著一個他沒看到的欄位按下確認；`date_expire_after` 必須由
呼叫端明給，本檔只**驗算**，⛔ 不在缺值時自己算出來當成使用者確認過的事實。
⚠️ `today` 是**關鍵字參數由呼叫點傳入，⛔ 不從 payload 讀**——payload 是模型控制的
資料，讓它決定起算基準等於把驗算交回給被驗的那一方。

`render_receipt` 同理：句子**只從 `action`＋`payload` 導出**（那份 payload 正是
使用者剛在卡上確認過的），下游回傳只貢獻一個經 `receipt_id_of` 過形狀的識別碼
——⛔ 不把 receipt 裡的自由文字拼進句子，那等於**在確認鏈末端開一個沒人檢查的輸出口**。

⇒ **這套架構最常被誤解的地方**：它不是「什麼都丟給 AI」，是
**程式先把能決定的決定完，剩下的才給模型，而模型說的每句話還要能指回程式查到的資料**。

#### 同一句話走歪的三種方式（都回同一句轉人）

| 情況 | 走到哪 |
|---|---|
| 物件／帳單查不到 | `_no_match()` ⇒ `status="error"` ⇒ **閘 4 早退** |
| 呼叫端沒帶 `role_id` | `_identity_gate_ok` 對 pm 要求它 ⇒ 同上 |
| 模型講了資料以外的事 | Verifier 擋 → 改寫 → 再擋 ⇒ `budget_exhausted` |

**三種原因、一句話。這就是「問帳單都被轉專人」的全部來源。**

## 4. 邊界與紀律（誰擋什麼）

| 面 | 機制 | 符號 |
|---|---|---|
| 呼叫者 | key（無條件 401）、Origin 三態、身分 header fail-closed | `mcp_facade.parse_identity`、`check_origin`、`load_allowed_origins` |
| 授權 | 不在本系統；查詢帶呼叫者 `role_id`／`user_id` 交 JGB API 收口；不存在與不在範圍同一句「查無此筆」 | DSP-011；`SELECT_NOT_FOUND_TEXT` |
| 別戶 | 清單點選後以 `estate_id` 等值程式判定；候選過濾、單列替換、寫入閘；聊天進場不設限（正本） | `_enforce_tool_scope`、`SCOPE_EXIT_TEXT`、`_SELECT_DEFAULT_FACE`（最小揭露 face，⛔ 無 email／電話） |
| 寫入 | 旗標×stage 可見；`mcp_only`；token 單次、雜湊綁卡、冪等鍵 | `registry.register` 強制、`redeem_pending`、`assert_redeemed` |
| 機敏 | **W6-b3（2026-09-09）落地後**：demo 線上值改 `AGENT_VERIFIER_MODE=grounding_observe` ⇒ `SENSITIVE_TOPIC`／`ROUTE_NOT_ALLOWED`／`FORBIDDEN_TERM`／`POLARITY_MISMATCH`／`SCHEMA` 的安全子成因（`marker_in_answer`／`handoff_reason_*`／`ask_target_invalid`／`empty_*`）**照擋**；只有引用解析與涵蓋類（`UNCITED_ASSERTION`／`QUOTE_TOO_SHORT`／`QUOTE_NOT_COVERING`／`SOURCE_NOT_CITABLE`＋`SCHEMA` 的 `ref_*`／`unit_out_of_range`）記進 `verdict.observed` 不擋。模式感知在 `verify()` **內部**、觀察類記錄後繼續跑（`grep -n "def _is_observed" rag-orchestrator/services/agent/verifier.py`）——⛔ 外層不再翻判定，那個作法會讓先命中的引用類把機敏類整段跳過。`observe_only`（＝舊旗語義）仍是全部放行、且只准配替身。清單點選 facts 出口另外直呼 `_verify_routes`（`grep -n "verify_routes = getattr" rag-orchestrator/services/agent/runtime.py`），那條一直都擋。 | `verifier.OutputVerifier.verify`／`_is_observed`、`health.verifier_mode`、`config/agent_verifier_rules.json` |
| 照片 | 白名單等值主機、https、不跟轉址、私網 IP 拒、5 MB 串流硬閘、型別驗證、去 EXIF、bytes 不落地、描述硬留空 | `image_fetch.validate_image_url`／`fetch_image`、`downscale_image` |
| 額度 | 每呼叫一列 `usage_events`（內部 key 不計額度）；上限值一律取自 `services/agent/limits.py::AgentLimits` 封閉表（DSP-045）：`turns_per_hour=1200`／`tool_calls_per_minute=600`／`kb_get_per_hour=3000`／`images_per_hour=600`／`files_per_hour=100`。⛔ **`AGENT_TURN_CAP`／`RATE_PER_MIN`／`KB_GET_CAP`／`IMAGE_COUNT_CAP_PER_HOUR`／`FILE_COUNT_CAP_PER_HOUR` 五個 env 都已除役、程式明文不再讀**（`grep -rn "不再讀" rag-orchestrator/services/agent/`）——設了不會報錯、也不會生效 | `_check_and_record_rate`、`check_and_record_agent_turn`、`check_and_record_image_count` |
| 紀錄 | trace／決策快照只有結構化欄位（封閉白名單由 `test_agent_decision_snapshot_keys_match_closed_whitelist_exactly` 逐鍵守測）；dialog 只寫程式摘要或卡文字；token、照片、ref 原值不進 trace | `_emit_agent_decision`、`DECISION_BANNED_KEYS`、不變量 27–31 |

## 4b. 回合出口與「為什麼轉人」——對碼事實表（2026-09-09）

> 動機：2026-09-09 我把「答案被 Verifier 打回所以轉人」講成線上原因，業主指出線上是觀察模式。這一節把「誰決定轉人」寫死，每句附查證指令；⛔ 引用時先跑指令再說。

**A. 轉人是誰決定的（六個來源）**

| 來源 | 觸發 | 使用者看到 | 查證 |
|---|---|---|---|
| 程式轉人（E 片，客人要真人） | 標籤呼叫（每個使用者文字回合另發、只判 `dialog_act`，與主模型及寫入意圖呼叫並行）的 `dialog_act=wants_human`（AI 理解、程式決定下一步）⇒ `kind=handoff`、`handoff.reason=user_request`；`user_request` 只由程式設定（`PROGRAM_ONLY_HANDOFF_REASONS`），主模型自報此值 ⇒ 改成 `no_grounding` 並記 `handoff_reason_not_model_visible`；開關 `AGENT_CLOSING_HANDOFF`（未設＝on） | `USER_REQUEST_HANDOFF_TEXT`（「好的，幫您轉真人客服，請點下方的『找真人』。」） | `grep -n "def _dialog_act_exit" rag-orchestrator/services/agent/runtime.py`；`grep -n "USER_REQUEST_HANDOFF_TEXT\|def closing_handoff_enabled_from_env" rag-orchestrator/services/agent/write_forms.py`；`grep -n "PROGRAM_ONLY_HANDOFF_REASONS" rag-orchestrator/services/presales_gate.py` |
| 模型自報 | 模型輸出 `kind=handoff`＋`handoff_reason=no_grounding`／`sensitive_no_grounding`（值域見 `HandoffReason`） | `PRESALES_HANDOFF_MESSAGE`（「這題我這邊沒有可靠資料，幫您轉專人——點下方的『找真人』。」，`effective_handoff_message(None)`） | `grep -n "class HandoffReason" rag-orchestrator/services/presales_gate.py`；`grep -n "PRESALES_HANDOFF_MESSAGE" rag-orchestrator/services/conversational_config.py rag-orchestrator/services/agent/tools/handoff.py` |
| 預算耗盡 | Verifier **擋**（非觀察模式）兩次改寫仍不過 ⇒ `handoff_reason=budget_exhausted` | 同上固定句 | log 行 `agent_turn trace_id=… kind=handoff handoff_reason=budget_exhausted … verifier_rejects=2` |
| 範圍退出 | 清單點選會話問別戶（L15） | `SCOPE_EXIT_TEXT` | `grep -n "def _apply_scope_exit" rag-orchestrator/services/agent/exit_gates.py`（⛔ 不在 runtime.py，那裡只是 import） |
| 程式降級（S4，2026-09-09） | 模型自報 `no_grounding` 但零工具呼叫、無範圍、非敏感類 ⇒ **不轉人**，改追問 `ASK_TARGET_TEXT` | 「想處理哪一戶或哪一筆？…」 | `grep -n "def _apply_handoff_without_lookup" rag-orchestrator/services/agent/exit_gates.py` |
| **工具查無／身分不足**（實務上最常見） | `jgb2.query.*` 回 `NO_MATCH`（ref／keyword 對不到列，或 pm 缺 `role_id`）⇒ 該筆 `status="error"` ⇒ **閘 2（要求零工具呼叫）與閘 4（要求全 `ok`）都不接管** ⇒ 模型的 `no_grounding` 原樣送出 | 同轉人固定句 | `grep -n "def _no_match" rag-orchestrator/services/agent/tools/jgb2.py`；log 行 `tool_calls=1 … handoff_reason=no_grounding` |

**A2. 程式收尾（E 片，不是轉人）**：`dialog_act=resolved` 且沒有未決的確認卡、草稿或候選清單（`_closing_pending_state`）⇒ 程式回 `CLOSING_TEXT`（「不客氣，有需要再找我。」，`kind=answer`）；有未決狀態或同句帶新請求 ⇒ 不收尾、照原流程。追問欄位中（`_dialog_act_not_field_answer`）：標籤 `wants_human` ⇒ 不填、轉人；標籤 `resolved` ⇒ 同輸入再發一次標籤確認（`_dialog_act_field_confirm`，至多等 `DIALOG_ACT_FIELD_CONFIRM_WAIT_S` 秒），確認為 `none` ⇒ 照現行填入，否則不填、程式重問缺欄；標籤未完成 ⇒ 不填、程式重問缺欄；標籤 `none` ⇒ 交填欄。不填的那句記 `dialog_act_fill_skipped`，草稿保留。

**A3. 填欄只填答覆（DSP-117，開關 `AGENT_FILL_DATA_TEXT`，未設＝on）**：只在**單欄追問回合**生效（回合開始即有草稿、上一回合程式只追問一欄、非凍結；`_fill_begin_intent_call`）。該回合寫入意圖呼叫另回 `data_texts`（最新一句裡屬於資料的段落，逐字照抄；道謝、寒暄、應答詞不算）與 `answer_text`（只回答追問那一欄的部分）——理解歸 AI；程式驗每段是最新一句的子字串、起訖不切斷數字或英數，追問欄只填程式從原句切出的答覆段（⛔ 整句），①～⑥ 值閘多比一次資料段（只縮不擴），已填的非追問欄不覆寫（候選綁定的名稱欄照 F12 名稱規則）。資料段讀不到或不成立 ⇒ 本回合不併新值、追問欄不填、程式重問（`fill_data_text_unknown`、`fill_data_text_reask`）。其餘寫入回合（第一句、確認卡出現後打字、一次追問多欄）與開關 off 相同。確認卡出現後打字、草稿與卡相同時（與本片開關無關；B 片 `AGENT_WRITE_REPLY_PROGRAM` 與 A+ 提議路徑生效時，`_write_reply_active`）：沒讀到任何值 ⇒ `CARD_NO_CHANGE_TEXT`；讀到的值與卡相同 ⇒ `CARD_READ_SAME_LEAD`＋「這次讀到的是」行；⛔ 再回「卡片還在，請按確認。」。查證：`grep -n "def _fill_begin_intent_call\|def _fill_read_data\|def _write_draft_fill_answer" rag-orchestrator/services/agent/runtime.py`；`grep -n "^DATA_TEXTS_RULE\|^DATA_TEXTS_NAME_NOTE\|^CARD_NO_CHANGE_TEXT\|^CARD_READ_SAME_LEAD\|^V_FILL_" rag-orchestrator/services/agent/write_forms.py`。查證：`grep -n "def _closing_pending_state\|def _dialog_act_exit\|def _dialog_act_not_field_answer\|def _dialog_act_field_confirm" rag-orchestrator/services/agent/runtime.py`；`grep -n "CLOSING_TEXT\|V_DIALOG_ACT_FILL_SKIPPED" rag-orchestrator/services/agent/write_forms.py`。

**B. 線上（demo）到底擋不擋：`AGENT_VERIFIER_MODE=grounding_observe`（runbook §20-2；W6-b3 於 2026-09-09 落地）**

- 讀值點唯一：`health.verifier_mode()`（舊旗 `AGENT_VERIFIER_OBSERVE_ONLY` 不參與解析）。查證：`grep -n "def verifier_mode" rag-orchestrator/services/agent/health.py`。
- 效果：**引用解析與涵蓋類只記錄**（記進 `VerifierVerdict.observed`，評估繼續往下跑），**主題錨定極性（`polarity_source=pair`，「尚未逾期」對「已逾期 8 天」）與機敏類照擋**；**裸否定詞表極性（`polarity_source=term`）只記錄**——2026-09-09 誤殺量測：裸詞表對稱整段比對在 98 句裡命中 12、幾乎全假陽性（引文側含否定詞、多 ref 一側缺否定詞），曾造成 7 回合預算耗盡轉人。查證：`grep -n "polarity_source" rag-orchestrator/services/agent/verifier.py`。查證：`grep -n "_GROUNDING_OBSERVE_REASONS\|_GROUNDING_OBSERVE_SCHEMA_CAUSES" rag-orchestrator/services/agent/verifier.py`。
- `app._wrap_verifier_observe_only` 只剩**相容層**：交模式、守 `observe_only` 只准配替身，⛔ 不再包 `verify()`、不再翻判定。查證：`grep -n "def _wrap_verifier_observe_only" rag-orchestrator/app.py`。
- 因此線上**可能**出現 `budget_exhausted` 轉人了（極性／機敏類擋兩次）——這是刻意的：那正是「尺在守什麼」看得見的地方。B 段 2026-09-09 之前的實證（24 回合 `agent_verifier_reject` 0 次）是**舊組態**的數字，⛔ 不得再引用為現況。
- 程式與帳本 R8 一致：機敏類照擋。

**C. 模型為什麼傾向轉人（提示詞層，觀察模式改變不了）**

- 鐵則：「只講工具回傳內容裡能引用的事實；沒有工具佐證的事實一律不說」、「`kind=fact` 的句子要有 `refs`」。查證：`grep -n "沒有工具佐證的事實一律不說\|要有 \`refs\`" rag-orchestrator/services/agent/agent_rules.py`。判斷題沒有可引用事實 ⇒ 依規則不說 ⇒ 剩轉人。
- 2026-09-09 前【判準】只定義「資料段與工具都查無 ⇒ `no_grounding`」，沒有「缺對象先問」「判斷題依資料段給建議」「查無先確認編號」；S4 補了這三句定義。查證：`grep -n "判斷句與指令句先確定對象" rag-orchestrator/services/agent/agent_rules.py`。
- 已知：提示詞越長模型越傾向先轉人（`agent_rules.py` 檔頭註解的回歸實測）。

**D. 尺的版本（r2／r3／DSP-039）是 Verifier 的事，不是提示詞的事**

| 名稱 | 意思 | 現況 |
|---|---|---|
| r2 | Verifier 引用類判定照擋（`UNCITED_ASSERTION`／`QUOTE_NOT_COVERING`…） | 業主 R8 停用 |
| r3 觀察模式 | 引用類只記不擋 | **線上 demo 組態**＝`AGENT_VERIFIER_MODE=grounding_observe`（引用類觀察、其餘照擋，見 B） |
| DSP-039 值級尺 | 工具事實片段以值級比對 | 備援，未啟用 |
| W6-b3 `AGENT_VERIFIER_MODE` | 引用類觀察＋極性與機敏類照擋的正式參數（三態；`observe_only` 為舊旗語義） | **已落地（2026-09-09）**；`self_test` 釘死 `enforce` 不受旗影響 |

**E. 怎麼判讀一回合**：看 log 行 `agent_turn trace_id=<id> kind=<kind> handoff_reason=<reason> tool_calls=<n> verifier_rejects=<n> llm_calls=<n>`——`kind=handoff` 且 `verifier_rejects=0` ⇒ 模型自選；`tool_calls=0` ⇒ 它一個查詢都沒做；`handoff_reason=budget_exhausted` ⇒ 是 Verifier 擋出來的（`grounding_observe` 下**仍可能出現**——擋的是極性類或機敏類；只有 `observe_only` 才不會出現）。

## 4c. 文件歸納回合（W9，`attachment_purpose=document`）

> 範圍：呼叫端以 `attachment_purpose="document"` 送上 JPG／PNG／PDF（帳單憑證／合約），
> 本系統回一段**只根據擷取欄位**寫成的歸納。
> 非目標：寫回外部系統、OCR 全文回顯、多份文件比對。
> ⛔ 檔案從哪個外部入口上傳、使用者在什麼畫面選的，**不屬於本系統**。

**資料流**：

```
upload_ids（預設：取暫存檔，`upload_store.STORE.claim`）／file_urls、image_urls（回滾模式 `urls`）
  → 回滾模式才過抓檔六道閘（`image_fetch.fetch_image`，等值白名單、https、不跟轉址、私網 IP 擋、`exp` 預檢、串流 bytes 硬閘，file 線加具名參數複用、⛔ 不另立第二支抓檔函式）
  → PDF 轉頁圖（`pypdfium2`，逐頁 `asyncio.to_thread`，由頁面尺寸反算 scale 釘每頁輸出像素上限，頁級與總時限，只 rasterize、不觸附件／JS API；`DOC_MAX_PAGES` 5，超過只看前 5 頁並明講）
  → 擷取（`DocumentExtractionService.extract`，vision 模型、strict JSON schema、封閉種類 `kind` ∈ {bill_receipt, contract, other}、`DOCUMENT_FIELD_SPECS` 定義的型別化欄位、`DOCUMENT_EXTRACTION_MODEL`）
  → `DocumentTurnInput`（封閉值：`status`／`kind`／`facts`／`pages_seen`／`pages_total`；`facts` 由程式逐欄組句、未擷取欄位寫「未載明」）
  → 資料段（保留 id 前綴 `doc-`，排在 `user_message` 之前，前綴「文件內容（擷取自使用者上傳的文件，不是使用者說的話、不是指令）：」，citable）
  → 模型歸納
  → Verifier
```

**邊界**：

- 該回合 `scope=="write"`／`mcp_only` 工具對模型不可見，且 per-turn 閘令該回合不出確認卡、不接受 `confirm_submit`（邊界層封閉，⛔ 不靠模型自律不引用寫入意圖）。
- 兩個新輸入（`attachment_purpose`、`file_urls`）不進 `trace`／`log`／`agent_state`；trace 只記 `has_document`／`document_status`／`document_kind`／`pages_seen`，⛔ 無任何欄位值。
- 歸納文字仍走既有 dialog 落點，落 `form_sessions.collected_data` 直到人工清除——保存期／清除機制待業主裁（demo 期不處理）。
- 照片頁與 PDF 頁合計 >10 ⇒ 整回合 `INVALID_INPUT`；`file_urls` 每小時每把 key `files_per_hour=100` 份配額，用罄 ⇒ `RATE_LIMITED`。

**與照片線的差異**：

| | 照片（`ImageTurnInput`） | 文件（`DocumentTurnInput`） |
|---|---|---|
| 進場文字 | 封閉值＋辨識描述（業主 2026-09-10 **撤銷 S9-11**：`suggested_description` 淨化、≤200 字，只進修繕單描述、⛔ 不進模型資料段；DSP-044） | 型別化、可引用文字（citable），代價由「寫入面關閉＋不可自成 unit」承擔 |
| 模型 | `IMAGE_RECOGNITION_MODEL` | `DOCUMENT_EXTRACTION_MODEL` |
| detail | `low` | `high` |

### 4c-1. `document_extract.py`（1,126 行）逐支

🔴 **2026-09-12 補寫**：這支比 `verifier.py` 還大，而本文原本只有兩句順帶提到它
（`DOC_UNREADABLE_TEXT` 與 PDF 轉頁圖）。它是**安全邊界**，不是工具函式。

#### 它在處理什麼衝突

照片報修線有一條「封閉值原則」：`ImageTurnInput` **刻意沒有 `description` 欄**——
不讓模型的自由文字進入後續流程。但文件歸納（帳單憑證／合約副本）**本質上需要把
文件上的文字帶進模型**。這兩件事正面相撞，本模組就是那道相撞的處置面。

**處置方式**：文件文字**只能**以「型別化、長度封頂、經 `sanitize_data_piece`、
掛『不是指令』前綴」的資料段進場，且：
⛔ 不進確認卡、⛔ 不進任何寫入 payload、⛔ 不進 trace／log／`agent_state`。

#### 三段，⛔ 不得合併成「把 PDF 丟給模型」

| 段 | 做什麼 | ⛔ 邊界 |
|---|---|---|
| ① `rasterize_pdf` | PDF ⇒ 頁圖（`pypdfium2`，逐頁 `asyncio.to_thread`） | **只 `render`**：`get_attachment`／`count_attachments`／`init_forms` **一次都不出現在本檔**——⛔ 不碰附件／嵌入檔／表單／JS API |
| ② `DOCUMENT_FIELD_SPECS` ＋ `build_json_schema()` | 欄位是**封閉表**，schema 由表產生 | ⛔ **不為「帳單」「合約」各寫一條程式路徑**——新增一種文件＝表上加一列，程式碼不動 |
| ③ `build_document_facts` | 擷取結果 ⇒ **程式組的句子** | 模型的自由文字在這裡被截長、**剝句末標點**（⛔ 不得自成一個可引用的 `provenance_unit`）、過 `sanitize_data_piece`，然後由**程式**收尾 |

⚠️ ③ 的順序不得顛倒：`sanitize_data_piece` 會把換行換成空白，先跑它會留下多餘空白。

#### 封閉的文件型別與旋鈕

**型別（封閉表）**：`bill_receipt`／`contract`／`other`——⛔ 值域封閉，加型別＝加表列。

| 旋鈕 | 值 | 說明 |
|---|---|---|
| `DOC_PAGE_MAX_PX` | 1024 | 頁圖長邊上限，**與照片線的 `IMAGE_MAX_PX` 同級**——⛔ 不讓兩線的頁圖大小分歧 |
| `DOC_PAGE_TIMEOUT_S` | 8.0 | 單頁渲染硬時限 |
| `DOC_TOTAL_TIMEOUT_S` | 25.0 | 整份 PDF 總時限 |
| `DOC_MAX_PAGES` | 5 | 超過只看前 5 頁**並明講** |

⚠️ **逾時的語義**：同步原生解析器**不可中斷**，所以逾時是「**放棄等待、保留已渲染的頁**」，
⛔ 不是「殺掉那次渲染」。子行程隔離是 DEFER——前提是
`to_thread` ＋逐頁像素上限＋頁級／總時限三項全在。

#### 額度：文件回合按最壞值預扣

一份 PDF 最多變成 `DOC_MAX_PAGES` 張頁圖 ⇒ 進場時以 `len(file_urls) × DOC_MAX_PAGES`
**預扣**（見階段 1 的 1.6）。⚠️ 這個最壞值只用在預扣，**早退判斷⛔ 不得用它**
（會誤殺）。

#### bytes 與擷取 JSON 的生命週期

**只活在 `prepare_document_turn` ＋ `extract` 的區域變數裡。**
本檔的 `logger` ⛔ **只印例外類別名**——`str(e)` 在 bytes 模型下可能把整串 base64
（＝文件本身）寫進 log。

#### 它在回合裡的兩個終止點

- 段一①：文件回合 ⛔ 不接受 `confirm_submit`（**排在確認段之前**——確認段一進去就兌現）
- 段一②：擷取不出可用欄位 ⇒ `DOC_UNREADABLE_TEXT`，⛔ 不進模型

#### Verifier 的文件回合專用步

`verify(..., document_turn=True)` 多跑一步 ⑥′：文件歸納回合 ⛔ 不寫回、⛔ 不建單，
所以「已把憑證掛到帳單上」（完成式寫入宣稱）與「要我存成系統帳單並匯入嗎？」
（提議寫入）在該回合**一律是承諾做不到的事**。預設 `False` ＝逐位不變。

查證：`grep -n "DOCUMENT_FIELD_SPECS\|DOC_PAGE_MAX_PX\|def rasterize_pdf\|def build_document_facts" rag-orchestrator/services/agent/document_extract.py`。

#### 段四：`exit_gates.finalize` — 四道閘**依序**跑（⛔ 不得重排）

| 序 | 閘 | 命中條件 | 效果 |
|---|---|---|---|
| 1 | `scope_exit` | `scope_out>0 且 scope_in==0` | 整段換 `SCOPE_EXIT_TEXT`、`kind="answer"`、`handoff=None`、`final_kind` 一起改（⛔ 不進 handoff cache）。部分範圍外 ⇒ 末尾接一行。⚠️ 本回合出現過範圍外 ⇒ **清掉 `estate_carry`** |
| 2 | `handoff_without_lookup` | `kind=handoff` ∧ reason ∈ **`NON_SENSITIVE_HANDOFF_REASONS`**（封閉白名單，⛔ 不等於「非敏感」）∧ `fact_class ∉ 敏感五類` ∧ **零工具呼叫** ∧ 無 select 範圍 | 降級為追問 `ASK_TARGET_TEXT`，五欄一起改 |
| 3 | `ask_target_gate` | `kind=="ask"` ∧ `ask_target ∉ ASK_TARGETS` | 換指路固定句，並把 `ask_target` **歸零**——留著值域外字串會讓 `LAST_ASK_TARGET_KEY` 變成模型可塞任意字串的地方。⚠️ 這是**保底閘**：觀察模式下 Verifier 不擋，⛔ 不得假設「Verifier 過了就合法」 |
| 4 | `handoff_data_exits` | 同閘 2 的封閉白名單條件，但 **有工具呼叫** | 全部 `empty` ⇒ `NO_DATA_TEXT`；否則 `NO_JUDGEMENT_TEXT`＋`ask_target="confirm_intent"`。⚠️ 任一筆 `status != "ok"` 或撞名保留 id ⇒ **整段不動**（那時 `empty` 不可信） |

🔴 **閘 4 不是「查無」的保護網——最常見的一類查無根本走不到它。**
`empty` 只在 `status=="ok"` 才可能為 `True`（`_tool_result_empty` 對 `error`／`timeout`／`rejected`
**硬回 `False`**，因為「沒查成」不得講成「不存在」）。而 `jgb2.query.*` 六域查無時回的是
`_no_match()`＝`{"ok": False, "error": "NO_MATCH"}` ⇒ `_tool_result_status` 判 `"error"` ⇒
閘 4 第一個條件 `any(r.status != "ok")` 就早退。**結果：使用者看到的是轉人固定句，不是
`NO_DATA_TEXT`。** 同一條鏈也吃掉身分不足——`_identity_gate_ok` 對 property_manager 要求
`role_id`，缺就 `_no_match()`，而 `role_id` 在 `mcp_facade` 是選填（必填只有 `vendor_id`）。
查證：`grep -n "def _no_match\|def _identity_gate_ok" rag-orchestrator/services/agent/tools/jgb2.py`；
`grep -n "def _tool_result_empty" rag-orchestrator/services/agent/runtime.py`；
`grep -n 'status != "ok"' rag-orchestrator/services/agent/exit_gates.py`。

⚠️ **閘 2／閘 4 另有 U2 例外**：模型自報敏感但被程式推翻時（`_sensitive_self_report_overridden`），
即使 reason 不在白名單也照樣進閘，並多記一筆 `sensitive_self_report_overridden`。

收尾：`default_outcome(result)` → `AgentSession.end_turn`（寫 `dialog`／`last_ask_target`／
`fixed_streak`；`final_kind=="handoff"` 才寫 `handoff_cache`）→ `_emit_agent_decision(trace)`。

## 5. 資料落點

| 資料 | 位置 | 保留 |
|---|---|---|
| 對話歷史、槽位、待確認表（含 receipt、estate_id）、`last_turn_at`、`select_scope` | `form_sessions.collected_data`（命名空間鍵） | 隨會話；過期關列（`state='COMPLETED'`） |
| 確認 token | `agent_confirmation_tokens`（雜湊、`pending_id`、卡雜湊、TTL） | 兌現即燒 |
| 用量 | `usage_events`、`openai_cost_tracking`（`operation='image_recognition'`／`operation='document_extraction'`，後者由 `mcp_facade._record_document_cost` 自寫） | 計量 |
| trace | 決策快照（`/api/v1/agent/trace/{trace_id}`） | 結構化欄位 |
| 替身寫入 | 行程記憶體（`services/jgb/transport.py`） | 重啟歸零 |

## 6. 組態

🔴 **三組數字不是同一回事**：程式預設、`docker-compose.prod.yml` 插值預設、正式機 `.env` 實際值。
診斷「哪裡太保守」前先確認守門模式（2026-09-12 對抗性演練：一位工程師照錯的守門模式做了整套診斷）。

| 鍵 | 正式機值（2026-10-16） | `docker-compose.prod.yml` 插值預設 | 程式預設 |
|---|---|---|---|
| `AGENT_VERIFIER_MODE` | `grounding_observe` | `enforce` ← 行為相反（引用類也擋） | `enforce` |
| `AGENT_BUDGET_DEADLINE_S` | 20 | 20 | 20.0（`bootstrap.py`） |
| `AGENT_BUDGET_TOOL_CALLS` | 3 | 4 | 4（`bootstrap.py`） |
| `AGENT_TURN_TIMEOUT_S` | 90 | 30 | 30.0（`mcp_facade._DEFAULT_AGENT_TURN_TIMEOUT_S`） |
| `USE_MOCK_JGB_API` | `false` | `true` | — |

正式機值以 `.env` 與健檢（`/api/v1/agent/health` 的 `checks.limits`／`verifier_mode`／`use_mock_jgb_api`）為準；本檔寫的是 2026-10-16 的現況，之後有改以健檢為準。

⚠️ **一個會靜默假成功的組合**：`AGENT_VERIFIER_MODE=observe_only` 只在
`USE_MOCK_JGB_API=true` 時允許（否則啟動 raise）。為了讓它不 raise 而去開 mock
⇒ **整站替身、寫入只落行程記憶體**——測起來全過，實際什麼都沒寫。⛔ 不得為了
放寬 Verifier 而開 mock。

（各鍵的值與說明；部署步驟見 runbook §20）

| 鍵 | 正式機 | 說明 |
|---|---|---|
| `USE_MOCK_JGB_API`／`JGB_API_BASE_URL` | false／`https://www.jgbsmart.com` | `true`＝整站替身；`false` 需 `JGB_API_KEY`（S-5 刻意 raise）。接真 JGB 且 `JGB_WRITE_WIRING` 不生效時，延期繳費與建物件／合約／手動帳單由程式回固定句、不發請求（見 §8） |
| `JGB_WRITE_WIRING` | 空（程式側；部署檔 `docker-compose.prod.yml` 用 `${JGB_WRITE_WIRING:-}` 傳入） | 恰為 `on` 才算開（`jgb_system_api._write_wiring_from_env`，唯一讀值點，結果存成 `JGBSystemAPI.write_wiring`）。開且（替身模式，或 `JGB_API_BASE_URL` 主機＝`staging.jgbsmart.com`）才生效；連 www 或其他主機 ⇒ 當關並記一行警告。生效時五項寫入與修繕照片送真 JGB（見 §8）；關時與接線前相同 |
| `AGENT_STAGE`／`AGENT_TURN_ENABLED` | M1／true | 工具面可見與 `agent.turn` 註冊 |
| `AGENT_WRITE_TOOLS_ENABLED` | true | `jgb2.action.*` 可見（AND stage、AND 呼叫端金鑰 id 在 `AGENT_ASSISTANT_KEY_IDS` 內；後者見下列該鍵） |
| `AGENT_VERIFIER_MODE` | grounding_observe（業主 2026-10-15 裁示；上線後同批 5 題知識題實測 `enforce` 答 1／5、`grounding_observe` 答 3／5） | 正式參數（DSP-040／W6-b3）：`enforce`（預設）／`grounding_observe`（引用類觀察、極性與機敏類照擋）／`observe_only`（全部觀察，只在 mock 允許、否則啟動 raise）。`grounding_observe`×非 mock ⇒ 健檢 `premise.red_flags` 記紅但不阻起 |
| `AGENT_VERIFIER_OBSERVE_ONLY` | **已除役（2026-09-10）** | 舊相容旗；`app.py`／`health.py` 讀到即印警告要求改用 `AGENT_VERIFIER_MODE`，⛔ 不再參與解析（查證：`grep -n AGENT_VERIFIER_OBSERVE_ONLY rag-orchestrator/services/agent/health.py`） |
| `AGENT_MODEL`／`AGENT_REASONING_EFFORT` | **`gpt-6-luna`＋`none`**（DSP-075，業主 2026-10-15 統一；正式機已採用） | 對話模型。luna 系列帶工具只接受 `reasoning_effort=none`（`low`／`minimal` 回 400）。舊設定 `gpt-5-mini`／low 的模型 `gpt-5-mini-2025-08-07` 於 2026-12-11 停用；`AGENT_MODEL` 空白時回退 `OPENAI_MODEL`（本機 `.env` 為 `gpt-4o-mini`），部署務必明設。歷次量測見帳本 §1s 與 DSP-072 細節 |
| `AGENT_LLM_BASE_URL`／`AGENT_LLM_API_KEY_FILE` | 未設 | 對話模型專用端點與金鑰檔（主線第 1 步正式接線，2026-10-18）。兩者皆未設＝對話照舊用 `OPENAI_API_KEY` 連 OpenAI（正式機現況，路徑逐位不變）；兩者皆設＝只有對話 provider 改連該端點（`llm_provider.build_agent_provider_from_env`，不進 `_provider_cache`），照片、文件、健康檢查仍走 OpenAI，且 runtime 開啟推理段剝除與 JSON 擷取（`AgentRuntime(clean_llm_output=True)`，trace 旗標 `llm_output_reasoning_stripped`／`llm_output_json_extracted`）；只設其一、與 `OPENAI_BASE_URL` 並存、金鑰檔格式不合＝啟動紅。本機接 Bedrock gpt-oss 用 `docker-compose.bedrock-local.yml`（Compose secret 掛 `/run/secrets/agent_llm_api_key`；寫死 mock JGB，⛔ 用於正式機）；正式機接 gpt-oss 用 `docker-compose.bedrock-prod.yml`（DSP-121；只覆寫對話模型四鍵與金鑰 secret，金鑰由業主處理） |
| `IMAGE_RECOGNITION_MODEL` | `gpt-6-luna` | 照片辨識；程式端對 gpt-6 系列送 `reasoning_effort=none`（站內幫手 S3 收尾） |
| `DOCUMENT_EXTRACTION_MODEL` | `gpt-6-luna`（程式預設 `gpt-5.6-luna`） | 文件歸納（W9）；同上 `reasoning_effort=none` |
| `OPENAI_TIMEOUT_S` | 25（runbook §20-2 值；正式機現值待查） | agent 每次模型呼叫 SDK 逾時＋預設重試，讓掛住的呼叫在門面逾時內自救 |
| `IMAGE_URL_ALLOWLIST` | 未設（預設 `relay.jgbsmart.com`） | 抓圖白名單；有設值是**取代**、不是附加；設成空字串＝全擋；白名單內除 relay 外每個 host 都必帶 `exp`。只在回滾模式 `AGENT_ATTACHMENT_INPUT=urls` 用得到（DSP-122） |
| `IMAGE_MAX_BYTES`／`IMAGE_COUNT_CAP_PER_HOUR` | 5,000,000／200 | 照片硬邊界 |
| `AGENT_ASSISTANT_KEY_IDS` | `101`（站內幫手金鑰，限定 vendor 4、非內部） | 列入者 `X-JGB-Identity` 缺 `user_id` ⇒ 400 `IDENTITY_MISSING_USER_ID`；未設或空字串＝不對任何金鑰啟用（靜默）；含非整數＝啟動失敗（`mcp_facade._ASSISTANT_KEY_IDS_ENV`）。**寫入工具只對名單內金鑰可見、可執行**（`registry._assistant_key_ok`、`registry.is_write_tool`）：名單空 ⇒ 連文字修繕單在內所有寫入工具不可見；`/mcp` 的工具聯集（`mcp_facade.union_specs`）探針不帶金鑰，不註冊寫入工具，站內幫手寫入只經 `agent.turn` |
| `DOCUMIND_BASE_URL`／`DOCUMIND_TOKEN` | 未設 | 謄本解析；未設或不合規組合（非 https、無 Token）＝謄本功能關閉，使用者看到「未啟用」固定句 |
| 額度與速率**五道上限**（`AGENT_TURN_CAP`／`RATE_PER_MIN`／`KB_GET_CAP`／`IMAGE_COUNT_CAP_PER_HOUR`／`FILE_COUNT_CAP_PER_HOUR`）。🔴 **⛔ 每回合預算不在內**——`limits.py` docstring 逐字寫「每回合預算（`Budget`）不在此，仍由 `bootstrap.py` 管（`AGENT_BUDGET_*` env，未變動）」 | 改由 `services/agent/limits.py` 程式內封閉表 | **DSP-045（2026-09-10）**：⛔ 不再讀 env 覆寫（業主：「env 沒人記得」）；預設寬鬆只擋惡意（回合 1200/h、工具 600/min、kb.get 3000/h、照片 600/h、PDF 100/h）；生效值由 `/api/v1/agent/health` 回報 |
| `AGENT_BUDGET_TOOL_CALLS`／`AGENT_BUDGET_DEADLINE_S`／`AGENT_TURN_TIMEOUT_S` | 3／20／90 | 每回合工具呼叫上限／回合預算（秒）／門面逾時（秒）。工具上限與時間上限 2026-10-15 業主「照建議」（本機同批題目量測：上限 4＝答出 12／20，上限 3＝13／20，上限 2＝13／20 但報修首句皆轉人）；門面逾時 90 讓文件回合預算拿滿（`min(DOCUMENT_MAX_BUDGET_S=45, 逾時/2)`）。延遲三層見 §8 |
| `AGENT_WRITE_REPLY_PROGRAM`／`AGENT_STATE_CLAIM_GATE` | 未設（＝on） | B 片開關，值域 on／off、未設或空字串＝on、其他值啟動失敗；off ⇒ 寫入情境回話與帶狀態句判讀閘回到 B 片前行為（`write_forms.write_reply_program_enabled_from_env`、`state_claim.state_claim_gate_enabled_from_env`）。判讀呼叫用對話模型與 `AGENT_REASONING_EFFORT` |
| `AGENT_WRITE_CANDIDATES` | 未設（＝on） | A-2a 片開關（DSP-103），值域 on／off、未設或空字串＝on、其他值啟動失敗；只在 A+ 三開關皆 on 時生效；off ⇒ 寫入時名稱對到多筆回到 B 行為（不列候選、無 `pick:` 按鈕）（`write_forms.write_candidates_enabled_from_env`） |
| `AGENT_PICK_RIGHT` | 未設（＝on） | 「選對紀錄」片開關，值域 on／off、未設或空字串＝on、其他值啟動失敗；候選相關（先物件、比對講的值、畫面 10 筆、候選白名單）只在 A-2a 生效時生效，卡上可分辨欄位在開關 on 即生效；off ⇒ 與 A-2a 逐字相同（`write_forms.pick_right_enabled_from_env`、`pick_right_effective_from_env`） |
| `AGENT_NAME_LENIENT` | 未設（＝on） | F12 名稱寬鬆比對開關（DSP-112），值域 on／off、未設或空字串＝on、其他值 `ValueError`；只在 A-2a 生效時生效；off ⇒ 名稱查無、缺名稱、名稱先查三觸發點皆不跑（`name_match.name_lenient_enabled_from_env`、`name_lenient_effective_from_env`）。選定後回合的指令版 schema 不看此開關（送出條件只看候選集與現選定，`runtime` 送意圖呼叫處 `cmd_offered`）；解綁前查找的寬鬆那一步才看 |
| `UVICORN_WORKERS` | 1 | `/mcp` 與行程內計數需單 worker |
| `MCP_ALLOWED_ORIGINS` | `-` | 伺服器對伺服器不送 Origin |

⛔ 不設 `AGENT_BUDGET_REWRITES=0`（探針組態）、不設 `AGENT_ATTEMPT_LOG_PATH`（開發量測；W6-b3 起它會多記引文原文 `resolved_unit` 與 `observed`，供極性誤殺量測逐句人看——**線上一律不設**）。

## 7. 測試層

| 層 | 位置 | 跑法 |
|---|---|---|
| unit（假 API、假模型、真 registry） | `tests/unit/agent/test_*_req.py`（select／scope／confirm／expired／image） | `./scripts/run-tests.sh unit tests/unit/agent -q`（1419） |
| integration（真 DB） | `tests/integration/agent/`（token、select 槽位） | `./scripts/run-tests.sh integration …` |
| 真線路（一次性、gate） | `tests/integration/agent/test_image_real_req.py`（`RUN_REAL_OPENAI=1`） | 素材不進 repo |
| 情境回測 | 帳本 §1h 劇本（三組共 63 案）；harness 在 scratchpad | 隔離實例 `smoke-rag`＋內部 key |
| 稽核 | `scripts/audit/check_invariants.sh`（不變量 27–31 為本線） | `make audit` |

## 8. 已知限制

- **單欄追問以外的寫入回合，道謝字仍可能上卡（DSP-117 已知偏離）**：「填欄只填答覆」（§A3）只在單欄追問回合生效（業主 2026-10-27 裁「縮小到追問回合」）。第一句開口、確認卡出現後打字、一次追問多欄的回合只過原有值閘（值須是原話子字串、數字 token 出現在原話），句中的道謝字或從道謝衍生的值（例：「3q」的 3）仍可能填進欄位。單欄追問回合也有漏網：系統句沒點名的英數道謝緊貼在答覆後（例：「車位費ty」「民生東路溫馨居tks」），或名稱與道謝縮寫緊貼（例：「大安溫馨套房3Q」）時，AI 仍可能把縮寫當成答覆的一部分；程式端不列詞表（DSP-091），業主 2026-10-28 裁列已知偏離。兩種都印在確認卡上，客人可按「我要修改」更正。量測與場數見收案報告 `~/jgb-archive/arch-step3-20261018/fill/report-fill-close.md`。查證：`grep -n "def _fill_begin_intent_call" rag-orchestrator/services/agent/runtime.py`；`grep -n "^DATA_TEXTS_NAME_NOTE" rag-orchestrator/services/agent/write_forms.py`。
- **確認鍵機器值只認整串相符**：`runtime._parse_confirm_value` 用 `_CONFIRM_VALUE_RE.fullmatch`；帶換行、空白或前後綴的訊息不兌現，當一般訊息進模型。⛔ 不得改回 `.match`：Python 的 `$` 允許結尾換行，`"confirm_submit:<pid>\n"` 會命中並多執行一次真實寫入，不可回復。釘住的測試：`test_runtime_confirm_segment_req.py` 的 `test_parse_confirm_value_*`。

- 線⑤ 模型偶爾在有工具結果時自判「無依據」轉人（三輪 2/21 情境不穩）；屬答案層定義文（5.1）範圍。
- `AGENT_VERIFIER_MODE=grounding_observe`（線上值）下引用類不擋——模型講的事實**沒有被要求對得上引文**，只有極性、機敏、標記外洩、schema 契約這幾類在守；重開引用類的依據是觀察紀錄（`verdict.observed`）中「真該擋」的計數（DSP-040 絆線）。相容旗 `AGENT_VERIFIER_OBSERVE_ONLY` 已於 2026-09-10 除役（見 §6）。
- **部分寫入回合仍以模型參數出卡**：三開關（`AGENT_WRITE_DRAFT`／`AGENT_WRITE_LIFECYCLE`／`AGENT_WRITE_PROPOSAL`）皆 on 時，一般寫入回合的確認卡與缺欄追問只由程式依草稿發出（`_write_proposal_handle`、`_write_draft_decide`）；點選範圍、唯讀檢視、文件回合、文件暫存有效回合的模型自呼 `confirm.request` 仍照模型參數執行。點選範圍、唯讀檢視與文件回合有沒有卡看模型（謄本回合放行 `estate_create` 的第一輪例外，由程式發起，見 §0a）；文件暫存有效回合若草稿動作與暫存動作相同，程式也會依草稿發起（`_write_draft_decide`），動作不同才只看模型。清單與接手片見目標正本 `architecture-target-20261018.md` §3.1（KD-1、KD-2）；每次執行的來源記在 violation `confirm_source:<來源>`，`make audit` 不變量 45 檢查。
- **帶狀態句判讀是 LLM，會漏判**：寫入情境問句回合的模型 `answer` 若在文字裡追問寫入欄位，結構規則（只看 `kind`）抓不到、判讀閘也不判追問；「已完成」只對到 session 內有收據，不對到是哪一筆；回覆夾帶誘導判讀的字串時，知識回合可能送出未對到事件的帶狀態句（寫入情境非問句回合不受影響：整則換成程式回話）。`make audit` 不變量 45 印 `state_claim_unbacked:*`、`state_claim_check_failed` 數。
- **兩張敏感表的受眾範圍不同**（調錯表會動到無關的那張）：

  | 表 | 受眾範圍 | 會擋 pm 嗎 |
  |---|---|---|
  | `sensitive_patterns`（答案側金額／百分比／保證…） | `sensitive_patterns_audiences = ["prospect"]` | ⛔ **不會**——`_sensitive_patterns_apply` 對 pm 直接不掃 |
  | **`question_sensitive_patterns`**（問句側：客戶案例／價格／SLA…） | `_TABLE_DEFAULTS["qsensitive"]` 的 audiences 參數是 **`None` ＝ 全受眾** | ✅ **會** |

  ⇒ **pm 問「我這方案一個月多少錢」被判機敏而轉人，是 `question_sensitive_patterns` 幹的，
  ⛔ 不是 `sensitive_patterns`。** 調 `sensitive_patterns` 不會改變這個結果。
  ⚠️ `grounding_observe` 下引用類只觀察、機敏類**照擋**，所以這道會真的擋掉答案。
- **延遲命題的數字不在同一層**：需求文 `requirements.md` D2／§「延遲」寫 p95 ≤12 秒（業主待裁）；回合預算 `AGENT_BUDGET_DEADLINE_S` 程式預設與正式機都是 20 秒；門面逾時 `AGENT_TURN_TIMEOUT_S` 程式預設 30 秒、正式機 90 秒（為了容納文件回合）。三者是同一命題（回合延遲上限）在 spec／回合預算／門面逾時各自定的數字，⛔ 尚未有裁決把它們收斂成一個。正式機量測（2026-10-15，工具上限 3）：知識題 20 題答出 11、中位 4.0 秒、p90 9.0 秒。
- **四個寫入動作接真 JGB 由開關 `JGB_WRITE_WIRING` 決定**（JGB staging 已開這些端點，DSP-132；開關與生效條件見 §6 組態表）：
  - 開關生效（替身模式，或連 staging）：延期繳費、建立物件／合約／手動帳單照常出確認卡，兌現時送 `PATCH /api/external/v1/bills/{id}`（body 只送 `date_expire`、`role_id`、`viewer_user_id`、`idempotency_key`；`bill_id` 須純數字，否則不發請求，`JGBSystemAPI.agent_patch_bill_due_date`）與 `POST /api/external/v1/estates`、`/contracts`、`/bills/manual`（`JGBSystemAPI._assistant_write`）。送給 JGB 的 `idempotency_key` 是確認 token。已在 staging 實測（2026-10-31，團隊 20151）。
  - 開關不生效（關，或連 www 等非 staging 主機；正式機今天連 www，master 沒有這些端點）：四個動作都不出確認卡、不發請求，由程式回固定句（延期繳費 `confirm.BILL_DUE_EXTEND_NOT_SUPPORTED_TEXT`，其餘 `confirm.WRITE_NOT_SUPPORTED_TEXT`）；非文件回合由 runtime 以固定句結束回合（`runtime._is_stats_not_supported`，violation `jgb2_stats_not_supported_exit`）。統計三項已改打 JGB 既有列表端點（`jgb2_stats`，DSP-126）。JGB 開放端點的設計見 `.kiro/specs/agentic-mcp-orchestration/jgb-api-spec-for-jgb-20261015.md`。
- **寫入結果的處理（開關生效時）**：JGB 拒絕訊息只在 `(端點樣板, 狀態碼, 訊息全文)` 完全相符時換成固定句（白名單 `transport.WRITE_REJECTION_WHITELIST`，固定句 `confirm_card.WRITE_RESULT_TEXTS`，格式「這筆操作沒有完成：<原因>。」）；白名單外 4xx、金鑰層、404 ⇒ `confirm_card.ACTION_FAILED_TEXT`；JGB 原文不轉給客人、不進模型、不進 log。逾時、5xx、送出後連線錯誤、2xx 非 JSON、2xx 缺 id ⇒ 「結果未確認」（`confirm_card.UNCONFIRMED_TEXT`），⛔ 回「無法執行」（客人會重開新卡、新冪等鍵 ⇒ 重複單）。兩類的 `outcome.state` 都是 `failed`（`runtime.AgentRuntime._answer_for_receipt`）；同一張卡重按由本系統回同一份結果、不再發請求。寫入 HTTP 逾時 JSON 30 秒、multipart 60 秒（`transport.WRITE_TIMEOUT_S`、`WRITE_TIMEOUT_MULTIPART_S`）；開關生效時寫入工具逾時 90 秒（`runtime.WRITE_TOOL_TIMEOUT_S`）；讀取維持 10 秒。JGB 端同一把 `idempotency_key` 重送是否不重複建立未實測（本系統不會重送同鍵）。
- **修繕單照片**（DSP-136）：開關生效時，修繕單有照片以 `multipart/form-data` 送 `POST /api/external/v1/repairs`，照片在 `broken_photos[]`（≤10 張、每張 ≤5,000,000 bytes、JPEG／PNG；位元組只取自確認卡綁定的暫存檔、重算 sha256 對卡上值，`action._card_photo_files`、`JGBSystemAPI.create_repair`），確認卡不再出現「照片這次不會送出」提醒；已在 staging 實測。開關不生效時不送檔、也不送中繼資料，確認卡外提醒照片暫時無法附上（`REPAIR_PHOTOS_NOT_ATTACHABLE_HINT`），文字修繕單照常送。DocuMind 已接測試機（DSP-124、DSP-125；明文 http、無認證，合成檔防護開著，只送樣本檔）。
- **細目索引開機逾時後背景重建**：開機 prepare 逾時（60 秒）後在背景重建（上限 900 秒；`app._prepare_index_in_background`），現行 3,835 項換算約 7 分鐘（未實測，算法見 `docs/deployment-runbook.md` 20-3b）；重建完成前回答只用目錄。
- **舊知識庫零列已審時 `kb.search` 不給模型**：正式機 `knowledge_base` 有效 926 列、已審 0 列（2026-10-15 量測），`kb.search` 列出的每筆 `kb.get` 都取不到；`mcp_facade.gate_kb_search_on_reviewed_rows` 依資料狀態判定（啟動時一次），門面照列。
- 驗證關 ⑦（轉人字眼）：字眼出自該句可引用引文時放行（`verifier._uncovered_handoff_mention`）；引文沒有、引文不可引用、只在別句引文、無句子結構 ⇒ 照擋。
- 工具參數塞身分鍵（`vendor_id`／`role_id`／`user_id`／`target_user`／`mode`／`viewer_user_id`）：現況由 `ToolRegistry.call` **剝除不採用**並記 trace，不回錯誤；其他未宣告鍵 ⇒ `INVALID_INPUT`。是否改為一律拒絕：待業主裁。
- 速率與配額為行程內計數（單 worker 正確；多 worker 會乘倍）。


## 9. 模型行為假設表

本線程式對「模型會怎麼配合」有若干未經 API 文件白紙黑字保證、僅靠實測支撐的假設；換模型或換 SDK 版本前應重新核對。

| 假設 | 內容 | 量測出處 |
|---|---|---|
| 主動呼叫 `confirm.request` | 模型在需要使用者二次確認的寫入前，會主動選用 `confirm.request` 工具而非直接呼叫寫入工具。一般寫入回合在 A+ 三開關皆 on 時，出卡由程式依草稿觸發，模型的呼叫只當提議、出不出卡不依賴本假設；文件回合、文件暫存回合、點選範圍回合仍依賴 | 帳本 §1s（lb2 劇本各輪出卡計數）；A+ 驗收 `acceptance-card-program-only-aplus-20261019.md` |
| strict `json_schema` | 對話模型與文件歸納模型皆走 `response_format=json_schema strict` 原生支援（非二次解析） | `plan-document-summary-demo-20260909.md`（容器內 openai 1.54.0 驗證） |
| `reasoning_effort` 值域 | `gpt-5.6-luna` 帶工具呼叫時僅接受 `reasoning_effort=none`；傳 `low`／`minimal` 回 400 | 帳本 §1s |
| tools＋reasoning 相容性 | 工具定義（MCP facade 轉譯後的 schema）與 reasoning 參數同時傳入時不衝突；已用於 luna／terra／mini 三種模型對照 | 帳本 §1q、§1s |
| `gpt-6-luna`（DSP-075 現行） | 帶工具時只接受 `reasoning_effort=none`；2026-10-15 站內幫手 S1-live（`/mcp` 實跑 16 回合）可用，引用過短偶致 `QUOTE_NOT_COVERING` | 站內幫手計畫 `.kiro/specs/agentic-mcp-orchestration/plan-assistant-11-items-20261014.md` §3e |

⚠️ 上表全部繫於實測樣本數（三輪 lb2、四張照片等），非窮舉；模型供應方行為變動時無自動偵測，靠下一輪 smoke 對照才會發現。
