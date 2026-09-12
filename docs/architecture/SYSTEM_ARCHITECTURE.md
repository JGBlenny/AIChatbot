# 系統架構（現況）

**最後對碼：2026-09-12**　**版本：4.0**

> 本檔回答一個問題：**這個系統現在是什麼。**
> ⛔ 它不記錄歷史、不記錄計畫。要判斷任何一份文件、一支程式、一張表還需不需要，
> 以本檔為基準——不在本檔的活路徑上，就要有別的理由才留。
>
> **v4.0 是整份重寫。** v3.0（2026-02-03）把 SOP 編排、表單填寫流程、意圖分類、
> 舊 chat 管線寫成現況，那些機制已於 2026-09-11 隨舊 REST 對話鏈刪除
> （31 個模組，commit `7c905408`／`10116570`，見 `.claude/DECISIONS.md` DSP-046）。
> 依 D-001 的先例——描述型文件描述錯了，處置是**以 runtime 為準逐行修正**，⛔ 不是加警語。
>
> 相關：對話線內部見 [`AGENTIC_MCP_ARCHITECTURE.md`](./AGENTIC_MCP_ARCHITECTURE.md)；
> 檢索分數欄位見 [`retriever-pipeline.md`](./retriever-pipeline.md)；
> 資料表 schema 見 [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md)。

---

## 0. 一句話

**這是一個包租代管業的 SaaS 多租戶知識平台。它有一個對話系統和一個管理後台，
但兩者目前只在「知識庫」這張表上相接——管理後台維護的其他東西，對話系統一個都不讀。**

---

## 1. 核心是 `AgentRuntime`，`/mcp` 只是它的一個門面

> ⛔ **外部串接不屬於本系統，⛔ 不進架構敘述。** jgb2 Web、LINE OA demo、回測工具
> 之類是**部署時接上來的消費者**。誰持 key、哪些停用、實際流量多少是**部署事實**，
> 要查去看 `api_keys` 與 `usage_events`，⛔ 不寫進本檔。
>
> 🔴 **2026-09-12 由程式重新推導，方向與前一版相反。** 前一版把 `/mcp` 畫成脊椎、
> 把 runtime 當成它裡面的東西——那是照抄 `AGENTIC_MCP_ARCHITECTURE.md` 第一張
> 「由外往內」的圖。**只要數一下誰呼叫 `run_turn`，方向立刻就反過來。**

### 核心（不知道任何門面的存在）

```
AgentRuntime.__init__(provider, registry, verifier, assembler, budget,
                      readonly_view, stage, clock, model, reasoning_effort,
                      tool_timeout_s, status_interval_s, attempt_sink,
                      candidate_selector, candidate_selectors, db_pool)
```

**這張依賴清單裡沒有 `/mcp`、沒有 REST、沒有任何協定。** 核心由
`services/agent/bootstrap.py::build_runtime` 組起來，`app.py` 在 lifespan 建兩份
（正式一份、`readonly_view=True` 的影子一份）。組成：

| 部件 | 是什麼 |
|---|---|
| `provider` | LLM 出口 |
| `registry` | `ToolRegistry`，16 支工具，四步閘（見 §2） |
| `assembler` | `PromptAssembler`（system 整回合只有一則） |
| `candidate_selector(s)` | 大綱候選選取，K=5（見 §2 路 A） |
| `verifier` | `OutputVerifier`，九步 |
| `budget` | 工具呼叫數／改寫數／deadline |

### 門面（接在核心外面，⛔ 核心不依賴它們）

非測試的 `run_turn` 呼叫端就是門面的完整清單：

| 門面 | 檔案 | 現況 |
|---|---|---|
| **MCP** | `services/agent/mcp_facade.py::_agent_turn`（`AGENT_TURN_SPEC`，`facade_only`） | ✅ **唯一掛著的** |
| **遷移橋**（⛔ 不是門面） | `routers/agent_entry.py::handle_agent_entry`／`_agent_sse` | **遷移橋（任務 2.2／R9）**，⛔ 不是端點：它站在舊鏈 `chat.py` 的請求路徑上分流（受眾在 `AGENT_AUDIENCES` ⇒ 走 runtime，否則回 `None` 讓舊鏈續跑）。⛔ **掛路由救不活**：上游的 `VendorChatRequest`／`VendorChatResponse`／`_conversational_to_response`／`sse_event`／`metered` 五樣全隨 `chat.py` 刪除，回退目標（舊鏈）也不在 |
| 回測 | `tools/agent_eval.py` | 離線 |
| 影子 | `services/agent/shadow.py`（`readonly_view=True`） | 隨 `app.py` 建 |

`run_turn` 的簽名在 `mcp_facade` 裡被註解為「**REST／影子／回測共用的介面**」
——共用，代表它不屬於任何一個門面。

🔴 **⛔ 「門面之一」⛔ 不等於「門面很薄」**（2026-09-12 對抗性演練：一位只讀文件的工程師
把「再加一個門面」估成 1 天，實際是重寫一整層邊界）。門面層自己帶著**順序即契約**的
13 個步驟——outline fail-closed **排在 `store.load` 之前**（判不過的回合不留半開的 session 列）、
配額**最壞值預扣排在抓檔之前**（超過一張都不抓）、過期**先 close 再 start**（顛倒會把新列一起關掉）、
**逾時不 save**（落不了半寫狀態）、bytes 不落地、命名空間身分……逐步見 §2b 階段 1。
另外還要處理三件門面層專屬的事：**額度計量要重寫**（`app.py::usage_metering_middleware`
只對 `/mcp` 動作、且刻意不 begin/finalize——不變量 31「門面是唯一寫入者」）、
**`GATED_PREFIXES` 要加前綴**（否則新端點沒有無條件金鑰閘）、
**`Identity.entry` 要決定**（`"rest"` ⇒ 寫入型工具看不到也叫不到）。


⚠️ **`/mcp` 是插座，不是對話架構**：它只做驗 key／驗身分／記帳三件事，**零對話邏輯**。
⚠️ **本系統只有 MCP server，沒有對外的 MCP client**：`mcp.client`／`ClientSession`
全 repo 只出現在兩支整合測試裡（拿 client 打自己的 server）；`runtime.py` **不 import `mcp`**，
模型呼叫工具走 `registry.call`，**in-process**，與 MCP 協定無關。

### MCP 門面收什麼（`mcp_facade.py` 常數）

| 項 | 值 |
|---|---|
| 掛載 | `Mount('/mcp', app=build_asgi_app(_mcp_server))`（`app.py` 唯一的 Mount） |
| 金鑰 | `x-api-key`（`_API_KEY_HEADER`）——無條件 401 |
| 身分 | `x-jgb-identity`（`_IDENTITY_HEADER`），**明文 JSON**，必帶 `vendor_id`＋`session_id` |
| 受眾值域 | `Audience = Literal['prospect','property_manager','tenant']`（封閉） |
| 入口模式 | `ENTRY_MODES = ('b2b','b2c')`，預設 `b2c`；`target_user=='prospect'` 一律改寫 `b2b` |

### 已不存在的門面

| | 現況 |
|---|---|
| `POST /api/v1/message` | **不存在**。`routers/chat.py` 已刪 |
| `POST /api/v1/chat/stream` | **不存在** |
| `routers/agent_entry.py` | ⛔ **它從來不是門面**——是遷移橋（見上）。唯一還有價值的是 `_agent_sse` 的事件序（`start`／`intent`／`: keepalive`／`answer_chunk`／`metadata`／`done`），**全 repo 唯一的 SSE 契約實作** |

⚠️ **這是門面的缺口，不是核心的缺口**：核心完好，缺的是一個 HTTP 面。
spec R3.6／R9.3 仍要求它。

### ⛔ 新增一個 `jgb2.query.<域>` 之前必讀（2026-09-12 對抗性演練逼出）

| # | 坑 | 為什麼 |
|---|---|---|
| 1 | **`_jgb2_spec` 的 stage 預設是 `{property_manager: M0, tenant: M0}`** | 照抄＝**租客也看得到**。既有六域的資料租客本來就有份，**新域不一定**——例如業者的訂閱方案／價格／用量，照抄就是洩漏，而且**沒有任何閘會擋**。⇒ 新域必須**顯式**決定 stage |
| 2 | **無物件維度的域 ⛔ 不得帶 `scope` 鍵** | `_ok_single(scoped=True)` 只給有 `estate_id` 的實體列。無物件維度卻帶 scope ⇒ L15 比對拿到 `None` 走 fail-closed，整域被判範圍外 |
| 3 | **`usage_metering.quota_check` 的數字在 `/mcp` 上可能是「安靜的錯」** | `_quota_fetch` 的 used 只數 `is_internal = FALSE` 的 `usage_events`；而 `/mcp` 的 `is_internal` **由 API key 紀錄決定**，demo key 就是 `is_internal=TRUE` ⇒ 拿它做「本月用了幾則」會誠實地回 0。`quota_check(is_internal=True)` 更是直接回 `state='none'` |

⚠️ **`test_mcp_facade_unit_req.py::test_build_registry_registers_expected_tools` 對工具名做
集合等值斷言**——加一支工具就會紅，必須同 PR 改。文件 §7 測試層沒提任何清單型斷言。

⚠️ **「額度」在本專案是兩個不同的東西**，兩者都叫額度但不同 DB、不同授權鏈：
jgb2 訂閱的 `estate_usage`（物件／合約數上限，由 jgb2 依 role 收口）vs
本系統的月訊息額度 `vendor_quotas`（**本 repo 自己的商業資料，DSP-011「授權由 JGB API
全權處理」涵蓋不到它**）。⛔ 要把後者放進對話前，先裁決。

### ⛔ 「調鬆一點」時不能動的東西（2026-09-12 對抗性演練逐條逼出）

一位工程師收到「答案太保守，調鬆一點」，只讀文件寫出的計畫裡有四項會出事：

| 想動 | 為什麼不能 |
|---|---|
| `KB_SIMILARITY_THRESHOLD` 下調 | **已裁決的禁令**：`decision_layer.py` docstring 逐字「⛔ 不得改回 0.55：失敗方向是門檻悄悄變鬆、回出相關性較低的知識，而且無聲」。2026-09-12 才剛**上調**對齊 |
| 擴充 `NON_SENSITIVE_HANDOFF_REASONS`（加 `budget_exhausted` 少轉人） | **封閉集合**＝`{no_grounding, llm_mentioned_handoff}`，由 `test_handoff_without_lookup_req.py` 釘死。T2／兩道降級閘**正是靠這個差別成立**，加值會讓出口邏輯整個錯位 |
| 在 `agent_rules` 加幾句「有資料段就先答」 | **反向惡化＋測試會紅**：`agent_rules.py` 檔頭記著「提示詞越長，模型越傾向先轉人」（DSP-028 回歸實測）；且 `test_ask_target_req.py` 斷言 `len(_POLICY_TEXT) <= 1584`（prospect 正本 5.1 凍結） |
| `AGENT_VERIFIER_MODE` 改 `observe_only` | 它**只在 `USE_MOCK_JGB_API=true` 時允許**，否則啟動 raise。為了讓它不 raise 而開 mock ⇒ **整站替身、寫入只落行程記憶體＝靜默假成功**。⛔ 不得為放寬 Verifier 而開 mock |

⚠️ `IMAGE_CONFIDENCE_MIN = 0.6` 是 **`runtime.py` 的程式常數，不是 env**，且
`test_image_entry_req.py` 斷言 `== 0.6`——⛔ 不是旋鈕。

⚠️ **真正能調鬆、但文件從沒並列過的旋鈕**：`CandidateSelector` 的 `K = 5`
（模型每回合只拿到 5 條可引用細目，直接決定「沒有可引用事實 ⇒ 轉人」）、
`kb.search(threshold=…)` 可**逐次覆寫**全域門檻、`AGENT_MODEL`（空＝退回 `OPENAI_MODEL`）、
`AGENT_STAGE`（預設 M0，決定工具可見性）。⚠️ `PRESALES_EXTRACTIVE` ⛔ 不在此列
（業主 2026-09-04 裁「補完知識前 ⛔ 不重提」）。

### ⚠️ 一處反向耦合（已知債）

`runtime.py` 有 `from services.agent.mcp_facade import current_stage`——**核心 import 了門面**。
只讀一個 stage 環境值，但方向是錯的。⛔ 不在本檔處置，記下避免下一輪走查誤判。

### 1a. 誰到得了（三道閘的交集）

| 閘 | 位置 | 效果 |
|---|---|---|
| `AGENT_TURN_SPEC["stage"]` | `mcp_facade.py` | 只有 `prospect`／`property_manager` 有鍵 ⇒ **tenant 永遠叫不到 `agent.turn`** |
| `_jgb2_spec` 的 `stage` | `mcp_facade.py` | 只有 `property_manager`／`tenant` 有鍵 ⇒ **prospect 看不到任何 `jgb2.*` 工具** |
| `AGENT_TURN_ENABLED` | env，預設 `false` | 只管 `agent.turn` 是否註冊 |

⇒ **能同時用到對話與 JGB 查詢的受眾只有 `property_manager` 一種。**

🔴 **`tenant` 在新線完全不存在**（⛔ 不只是「叫不到 `agent.turn`」）：

| 受眾 | canon 正本 | `AGENT_TURN_SPEC["stage"]` |
|---|---|---|
| `prospect` | ✅ `canon/prospect.md` | ✅ M1 |
| `property_manager` | ✅ `canon/property_manager.md` | ✅ M1 |
| **`tenant`** | ❌ **無 `canon/tenant.md`** | ❌ **缺鍵** |

`app.py::_AGENT_OUTLINE_AUDIENCES = ("prospect", "property_manager")`；
`build_audience_outline` 對 tenant 直接 `raise`；`build_toc`（讀 DB 的那條 tenant 路徑）
**零生產呼叫端**。⇒ **接 tenant 不是接線，是一整個知識正本工程。**

⚠️ `jgb2.query.*`／`jgb2.action.*` 是**無條件註冊**的（不受 `AGENT_TURN_ENABLED` 管）——
持 key 的 MCP client 即使在 `agent.turn` 關閉時仍可直接呼叫查詢工具。

### 1b. 一回合的形狀

**六條程式終止路徑**永遠先於模型（機器值不進模型，順序即契約）：文件回合禁寫 → 文件不可讀
→ 照片失敗/逾時/低信心 → 確認按鈕 → 清單點選 → 同題重問重播。之後才是模型迴圈
（工具呼叫 → Verifier 九步 → 四道出口閘 → 收尾）。🔴 前一版寫「三個程式段」是照抄舊圖，`turn_segments.py` 的 docstring 自己寫的是**六條**。
**完整流程（每一個分岔與終止點）見 `AGENTIC_MCP_ARCHITECTURE.md` §2b。**

---

## 2. 知識從哪裡來——兩條互不相通的路

### 路 A：每回合自動注入（主要供答來源，**不碰 `knowledge_base`**）

```
_build_turn_context → _select_outline
  → canon_assembler.get_canon(audience)        ← git 正本 rag-orchestrator/canon/*.md + .json
  → fine_index.FineIndex.visible_subset
  → candidate_selector.CandidateSelector.select（K=5，餘弦）
  → prompt_assembler.PromptAssembler（＋ agent_rules 政策文字）
```

**正本是 git 檔案，不是資料庫。** 啟動時由 `app._init_agent_runtime` → `outline.build_audience_outline` 載入。

### 路 B：模型主動呼叫工具

```
kb.search → VendorKnowledgeRetrieverV2.retrieve()（向量＋詞面＋reranker＋門檻）
            只回 id／question_summary／similarity，citable=False
kb.get    → build_visibility_predicate ＋ canon.review_state.content_reviewed_predicate
```

- `kb.search` 對 **prospect 永不可見**（`KB_SEARCH_SPEC["stage"]` 無 prospect 鍵）。
- 檢索的三軸隔離仍是現行行為：`vendor_ids`／`target_user`／`business_types`。
  🔴 **b2b 業態過濾是 `business_types && ARRAY['system_provider']`、無 `IS NULL` 放行**
  ——補上 `IS NULL` 會打穿刻意設計的跨業者隔離（D-002）。
- `kb.search` 明文排除 `系統脈絡` 與 `對話規則` 兩個分類 ⇒ 那些列在對話路徑上不可達。

⚠️ **`kb.get` 目前對每一列都回 `NO_MATCH`**：`content_reviewed_predicate()` 只放行
`^reviewed:\S+$`，而本機庫 926 筆 active 知識中該形狀為 **0 筆**。這是 D1 之前的
**預期行為**（`review_state.py` docstring 自述），⛔ 不是壞掉。

---

## 3. 面向（Face）：腦活著，骨架死了

新線**不是**「載入面向設定 → 進場判定 → 決定性算 facts」，而是
**「模型從一個封閉 enum 挑 `face` → 直呼對應 builder」**——enum 由 `_jgb2_spec(domain, sorted(builders.keys()))` 在註冊當下由註冊表現算。

🔴 **⛔ 「加一個 face 鍵」⛔ 不等於「加一個能力」**（2026-09-12 對抗性演練：一位只讀文件的
工程師照上面那句規劃新 face，做出來會是一個拿得到資料列、卻算不出答案的 builder）。
三件文件從來沒講、但決定你能不能做的事：

| # | 事實 | 後果 |
|---|---|---|
| 1 | **face 只選 builder，⛔ 不選資料源** | 資料源**寫死在 `query_<domain>` 函式本體**。實測 `query_estates` 只呼叫 `get_estate_status`＋`get_estate_detail`，**⛔ 不依 `face` 分流**。加鍵拿不到新資料 |
| 2 | **builder 簽名是單列** | `build_payment_flow_facts(bill, user_question)`、`build_estate_status_facts(estate, detail, user_question)`。多列一律走 `_ok_candidates` 變候選清單 ⇒ **跨列彙總（「這戶今年收了幾期」）在現行形狀下表達不出來** |
| 3 | **參數列是封閉的** | `_jgb2_spec` 的 `properties` 是 `face`（必填 enum）／`ref`／`keyword`，`additionalProperties: False`。🔴 **2026-09-12 更正**：前一版寫「釘住參數列為 `["ctx","face","ref","keyword"]`」——**兩處都錯**：沒有 `ctx`，且 `test_to_openai_tools_strict_req.py` 測的是**檔內自建的假 spec**（驗 strict schema 轉換形狀），⛔ 不是真 spec。真正對 `_jgb2_spec` 做斷言的是 `test_session_confirm_tools_req.py`（驗 `extra_properties` 預設不變、只有 repairs 多 `estate_id`）。只有 repairs 有 `JGB2_EXTRA_PROPERTIES` ⇒ 其餘域**傳不了額外參數** |

⇒ 真要加能力，動的是 `query_<domain>` 的資料源與回傳形狀，**那是架構改動，不是加一個鍵**。

### 🔴 六個域的隔離**不對稱**（安全相關，⛔ 挑域承載資料前必讀）

| 域 | 身分閘 | jgb2 端 `viewer_user_id` 圈定 | stage |
|---|---|---|---|
| `bills` | `_identity_gate_ok`（受眾感知：pm 單證／tenant 雙證） | ✅ **有** | pm・tenant |
| `contracts` | `_identity_gate_ok` | ✅ **有** | pm・tenant |
| `repairs` | `_identity_gate_ok` | ⛔ 無 | pm・tenant |
| `meters` | `_validate_identity`（一律雙證） | ⛔ 無 | pm・tenant |
| `accounts` | `_validate_identity` | ⛔ 無 | pm・tenant |
| `estates` | `_validate_identity` | ⛔ 無 | pm・tenant |

⚠️ **只有 `bills`／`contracts` 有 jgb2 端的 viewer 圈定。** 其餘四域的別戶隔離**全靠本地**
`_enforce_tool_scope` 的 `scope.estate_id`——而那個 scope **只在使用者點過清單（`select:`）之後才存在**。
一般對話（沒點清單）時，那四域**既無 viewer 圈定、也無 scope**。

⇒ **⛔ 不得把財務／個資等級的資料掛進沒有 viewer 圈定的域**（尤其 `estates`，
六個域的 `stage` 都含 `tenant`）。要承載那類資料，掛 `bills`／`contracts`。

六個域、15 個合法 `face`（＝六張 `*_FACE_BUILDERS` 註冊表的鍵；查證：以 `ast` 解析工作樹逐表取鍵——⛔ 不要用 `docker exec`，長駐容器落後工作樹，見下方 §6）：

| 域 | face |
|---|---|
| bills | 帳單異常、條件診斷：帳單、滯納金、發票、繳費金流排障 |
| contracts | 合約異動、簽署排障、續約、退租收尾 |
| accounts | 團隊成員權限、登入排障（⚠️ 在 enum 內但 `query_accounts` 頂端硬拒） |
| meters | 電表排障 |
| estates | 物件現況診斷 |
| repairs | 修繕分類、修繕進度 |

#### ⚠️ DB 的「對話規則」列與程式端 face **對不起來**（2026-09-12 實查，待裁決）

`knowledge_base` 有 23 列 `category='對話規則'`（全 `is_active`）＋27 列 `系統脈絡`，
但兩邊的面向名有雙向差集：

| 方向 | 數量 | 名單 |
|---|---|---|
| **DB 有、程式沒有** | 11 | 售前顧問、合約診斷、註冊驗證排障、帳號綁定異動、IoT設定引導、物件操作引導、帳單設定引導、建約引導、帳單診斷、修繕報修、訂閱診斷 |
| **程式有、DB 沒有** | 3 | 修繕分類、修繕進度、條件診斷：帳單 |

**這 50 列目前沒有任何消費者**：讀 `系統脈絡` 的 `system_context.py` 已刪、
`outline.build_toc` 真實呼叫 0 處（AST 驗，⛔ grep 命中會把 docstring 算進去）；
讀 `對話規則` 的 `conversational_rules.load_rules` 已刪，
`prompt_assembler` 的 DB 路徑未接線（任務 2.1）。
兩個分類也都被 `build_visibility_predicate` 的 `IS DISTINCT FROM` 排除在檢索外。

**2026-09-12 盤查結果（⛔ 不是「待裁決」，是查得到答案的）**：把這 11 個名字逐一
拿去比對「非 archive 的 spec」，**10 個有對應的 spec，且那些 spec 都停在
`tasks-generated`（任務寫了、沒實作）**：

| 列 | 對應 spec | spec phase |
|---|---|---|
| 註冊驗證排障／帳號綁定異動 | `account-conversational-facets` | tasks-generated |
| 帳單設定引導／建約引導 | `billing-conversational-facets` | tasks-generated |
| 合約診斷 | `contract-conversational-facets` | tasks-generated |
| 物件操作引導 | `estate-conversational-facets` | tasks-generated |
| IoT設定引導 | `iot-conversational-facets` | tasks-generated |
| 售前顧問／帳單診斷 | `agentic-mcp-orchestration` | tasks-approved |
| 修繕報修 | `conversational-repair` | implementation-completed |
| **訂閱診斷** | **無任何 spec** | — |

⇒ **這 11 列絕大多數是「規劃了沒做完」，⛔ 不是舊鏈殘留。** 真正該問的不是要不要刪，
而是：**那五份 `tasks-generated` 的面向 spec，寫的是舊的「資料驅動面向」做法
（一筆 `category='對話規則'` ＝一個面向），而新線的 face 是程式驅動（`*_FACE_BUILDERS`）
——這些 spec 要整份改寫成新做法，還是撤案？** 只有「訂閱診斷」無主，可單獨處置。
⛔ 本輪不動 DB（業主「資料先不碰」）。
查證：`SELECT question_summary FROM knowledge_base WHERE is_active AND category='對話規則' ORDER BY id;`
以及 `grep -rln "<面向名>" .kiro/specs --include="*.md" | grep -v /archive/`。

#### ⚠️ 19 張表在執行期程式零引用（2026-09-12 實查，待裁決）

`public` 有 63 張表，其中 **19 張在 `.py`／`.ts`／`.js`／`.vue`（排除 tests）完全查不到**
——只有 migration 與文件提過。⛔ 本輪不動 DB（業主「資料先不碰」）。

| 類別 | 表 | 估列數 |
|---|---|---|
| **舊鏈殘留**（主體已刪） | `digression_config`（離題偵測配置）、`suggested_intents`、`chat_history`、`vendor_sop_overrides` | 10／1,561／—／— |
| **迴圈執行面殘留** | `knowledge_gap_analysis`、`knowledge_import_jobs`、`knowledge_review_queue`、`loop_rollback_history`、`backtest_logic_changes`、`backtest_manual_reviews`、`test_collections`、`test_scenario_collections` | 2,662／33／—／… |
| **備份／快照**（命名即自述） | `_category_phase2_snapshot`、`kb_rent_backup_20260419`、`knowledge_base_backup_dedup`、`knowledge_base_deleted_phase2` | 668／—／—／55 |
| **非程式消費**（不是死的） | `schema_migrations`（97 列，runbook／shell 用）、`business_types_config`、`business_scope_config` | — |

**2026-09-12 盤查結果**：這 19 張的處置**比對話規則列清楚得多**——
① 它們服務的 8 個主體（`digression_detector.py`／`intent_suggestion_engine.py`／
`chat.py`／`sop_orchestrator.py`／`gap_analyzer.py`／`coordinator.py`／
`backtest_client.py` 等）**逐一 `find` 確認全部不存在**；
② 拿表名去比對非 archive 的 spec，**沒有任何一張被列為待建**——只有三張被
「當成盤查證據」提到（`knowledge_review_queue` 在 `routing-authority-model` 的
盤點裡被記為「唯一具 approver 身分的機器化審批痕跡」，那是**稽核軌跡**的價值，
⛔ 不是待建；`chat_history`／`test_scenario_collections` 被記為「本機為空／清單」）。

⇒ **19 張全是殘留**，其中只有 `knowledge_review_queue` 有「保留當審批痕跡」的理由。

⚠️ **「零引用」≠「該刪」**：`schema_migrations` 是 migration 帳本、由 shell 與 runbook 使用；
判死之前要先問「消費者是不是在**執行期程式以外**」（同 `return_unfiltered` 的教訓）。
⛔ 我先前只掃 `.py` 得到「22 張零引用」——擴到 `.sh`／`.sql`／`.md` 後全 repo 是 **0/63**，
那個數字是假警報。上表用的是**執行期程式**這個較嚴的定義。
查證：`SELECT tablename FROM pg_tables WHERE schemaname='public';` 再對程式做逐表 grep。

**回合路徑上不讀的**（🔴 2026-09-12 逐條重驗——前一版寫「**全部零消費者**」是錯的，
九條**全都還有非測試消費者**，只是不在對話回合路徑上。這種「把活的說成死的」比反方向
更難發現，因為五把尺全都只找「把死的說成活的」）：

| 符號 | 還在嗎 | 誰在用 | 回合路徑 |
|---|---|---|---|
| `config_for_category` | ✅ `conversational_config.py:273` | `tools/audit_config.py`（設定契約稽核）、`tools/seed_repair_facet_knowledge.py` | ⛔ 不呼叫 |
| `build_toc` | ✅ `outline.py:426` | **無**——AST 數 `ast.Call` 真實呼叫 **0 處**（⛔ grep 會把 docstring 算進來）。活的是 canon 版 `build_canon_toc`（3 處） | ⛔ 不呼叫 |
| `grounding_scope`／`persona_role`／`topic_scope`／`answer_rules`／`cta_rules` | ✅ 定義在 `conversational_config.py` | `tools/audit_config.py` 逐條稽核；`instance_applicability.py` 讀 `grounding_scope` | ⛔ 不讀這幾個鍵 |
| `category_config` | — | **僅註解提及**（`services/jgb/estates.py:94`、`repairs.py:87` 各一行） | ⛔ 無程式讀取 |
| `FORM_TRIGGER_THRESHOLD` | ✅ `decision_layer.py:77` 讀 env | ⚠️ 讀進來了但**欄位 `.form_trigger_threshold` 零讀取** | ⛔ 不讀 |

⚠️ **`conversational_config.py` 本身在回合路徑上**（`runtime.py`／`turn_context.py`／
`tools/handoff.py`／`shadow.py` 都 import 它，用 `effective_handoff_message`／
`config_for_target_user` 等）——⛔ 別把「這幾個鍵不讀」讀成「整個模組沒人用」。

---

## 4. 不在對話路徑上的東西（後台維護面）

這些**人還在用、系統還在存，但對話系統一個字都不讀**：

| 子系統 | 後台面 | 對話路徑 |
|---|---|---|
| **SOP** | `routers/platform_sop.py`（15 路由）、`routers/vendors.py` 的 SOP 段、`sop_utils.py`、`sop_embedding_generator.py`、前端 3 個元件 | **零路徑**。`services/agent/**` 查無任何 sop 引用 |
| **意圖** | `intents` 表被匯入／匯出／platform_sop／vendors 共 6 支程式讀 | **零路徑**。分類器與它的端點已刪 |
| **表單** | `form_schemas` CRUD、`routers/forms.py` | 只有 `form_sessions` 這張表被借用來存對話狀態（`form_id='conversational'`） |
| **測試情境／回測** | `test_scenarios`、`backtest_runs`、`backtest_results` 與後台查詢頁 | **零執行器**。執行機制已刪 |
| **知識完善迴圈** | `routers/loops.py`（5 條查詢）、`routers/loop_knowledge.py`（審核） | **零執行器**。`services/knowledge_completion_loop/` 只剩 `embedding_client.py` |
| **未釐清問題** | `routers/unclear_questions.py`（7 條 CRUD） | **不再有新資料**——寫入點隨 `chat.py` 刪除 |

⚠️ **SOP 特別注意**：後台每次存 SOP 仍會呼叫 `generate_sop_embeddings_async` 真的去算向量
（`routers/vendors.py` 有 7 個呼叫點），寫進 DB 之後沒有任何程式會查它們。
業者維護 SOP 的成本是真的，效果是零——而畫面不會告訴他這件事。

---

## 5. 已知缺陷（對碼確認，尚未處置）

| # | 缺陷 | 後果 |
|---|---|---|
| 1 | `_finish_generic`／`query_accounts`／`query_estates` 一律 `builder(row, "")`，**問句永遠是空字串** | `_diagnose_atm_expired`（虛擬帳號過期）與 invoice_logs 診斷**不可達**；`build_team_permission_facts` 的可見性種類**恆為「帳單」** |
| 2 | `secondary_call` 機制**有宣告、有降級分支、無執行者** | 8 筆 DB config 空轉；G3 個人化封存、G5 權限擋分流、T2 帳單可見性**永遠走未附掛路徑** |
| 3 | `point_refund_selection`（點退帳單選單契約，業主 2026-08-29 授權）**唯一實作在零呼叫端的 `face_bill_response` 內** | `query_bills` 直接取 `rows[0]`——正是該契約要防的「多筆情境答錯筆」 |

---

## 6. 服務與資料（規模）

| 面 | 數量 |
|---|---|
| rag-orchestrator 端點 | 136（全部掛載） |
| knowledge-admin 端點 | 66 |
| 前端 `.vue`／`.js` | 52 |
| `services/agent/` 模組 | 42（不含 `__init__.py`） |
| prod compose env 鍵 | 90（去重；含重複出現則 104） |
| DB 資料表 | 63 |
| 單元測試 | 3,629 |

🔴 **驗證前必讀——本機有兩個 rag-orchestrator，跑的是不同的程式碼**（2026-09-12 實測）：

| | 起自 | Mounts | 跑的是 |
|---|---|---|---|
| 長駐 `aichatbot-rag-orchestrator` | `docker-compose.prod.yml` | **空** | **image 內的程式碼，落後工作樹** |
| 測試容器（`./scripts/run-tests.sh` 的 `compose run --rm`） | `docker-compose.dev.yml` | `./rag-orchestrator:/app` | **工作樹** |

⇒ `docker exec aichatbot-rag-orchestrator …` 的結果 **⛔ 不得當作工作樹的事實**。
實例：本輪 `routers/` 在 image 內 21 支、工作樹 22 支（差 `agent_entry.py`）。
要驗工作樹請走測試容器，或 `docker run --rm -v "$PWD:/w" -w /w python:3.11-slim …`。

**服務**：`rag-orchestrator`(8100)、`knowledge-admin-api`(127.0.0.1:8000)、
`knowledge-admin-web`(nginx)、`embedding-api`(5001)、`semantic-model`(8002)、
`postgres`(5432, pgvector)、`redis`(6381)。

**認證**：rag 側 `X-API-Key`（`api_keys` 表存 SHA-256，開關 `RAG_API_AUTH_ENFORCE`）；
後台側 JWT（`routes_auth.get_current_user`）；nginx 對 `/rag-api/` 與 `/rag-api/mcp`
掛 `auth_request`，對 `/api/` **不掛**（後台自己的 `Depends` 是唯一防線）。

---

## 7. 怎麼用本檔判斷「還需不需要」

對任何一支程式、一份文件、一張表，問同一個問題——**它在上面哪一節？**

| 落在 | 判定 |
|---|---|
| §1–§3（對話路徑、知識來源、face builder） | **新架構在用**，⛔ 不得刪 |
| §4（後台維護面） | **人要用、對話不讀**——刪不刪是**產品決策**，⛔ 不是清理決策 |
| §5（已知缺陷） | **修或撤，二選一**，⛔ 不是刪掉了事 |
| 三節都不在 | **舊架構殘骸**，依 D-005 處置（前提全滅且無唯一資訊→刪；記錄決策→歸檔；局部錯而其餘是唯一正本→修正） |

⚠️ **⛔ 不得用「有沒有人 import」當判準**。這一輪已三次因此誤判：
`routers/platform_sop.py`（因檔名含 sop 被當舊線入口）、
`tools/contracts/visibility.py`（無 importer 但 skill 指定它是正本）、
`routers/agent_entry.py`（失去呼叫者被當成失去用途）。
非 import 的消費者至少有四類：`Dockerfile` 建置期匯入、`check_invariants.sh` 的
`docker exec` 字串匯入、skill／MAP 的正本指定、spec 的需求條文。
