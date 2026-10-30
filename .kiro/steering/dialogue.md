# Dialogue Steering

> 🎯 **本檔寫現況，不是設計依據。目標：本系統是對話服務，不是 MCP 系統；呼叫端走專用對話 API，`/mcp` 不是最終入口；JGB 工具要搬出本系統，由 JGB 維護。** 分工與完整架構見 `docs/architecture/TARGET_ARCHITECTURE.md`。

> **完整文件**：[docs/architecture/AGENTIC_MCP_ARCHITECTURE.md](../../docs/architecture/AGENTIC_MCP_ARCHITECTURE.md)（§2b 流程、§4b 轉人來源）
>
> **相關文件**：
> - Retriever Pipeline：[docs/architecture/retriever-pipeline.md](../../docs/architecture/retriever-pipeline.md)
> - 知識資料結構：[knowledge.md](./knowledge.md)

本文件為 AI 引導用摘要，詳細邏輯與圖表請查閱完整文件。

---

## 對話處理核心流程（agentic-MCP，唯一活線）

```
/mcp 的 agent.turn（唯一掛著的門面，13 步進場契約）
    ↓
AgentRuntime.run_turn —— 核心，建構依賴裡⛔ 沒有任何協定或門面
    ↓
段一 turn_segments.run_program_segments  （六條終止路徑，程式直接結束回合）
    ↓
段二 _build_turn_context                 （九段注入，user_message 永遠最後）
    ↓
段三 _run_model_loop                     （模型選工具 → registry.call in-process
                                          → Verifier 逐句驗引用 → 最多兩次改寫）
    ↓
段四 exit_gates.finalize                 （四道閘依序，⛔ 順序即契約）
```

**回合可以在哪裡結束**（每個數字都指得回程式，⛔ 不要引用沒有來源的總數）：
段一 **六條**程式終止路徑（`turn_segments.py` docstring 自述「六個程式終止路徑」）、
段四 **四道**出口閘（`exit_gates.py::EXIT_GATES`）、
門面階段 0 的驗證失敗（401／403／400／`INVALID_INPUT`／`RATE_LIMITED`／`TOOL_TIMEOUT`）。
逐步流程與每個分岔見
[`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](../../docs/architecture/AGENTIC_MCP_ARCHITECTURE.md) §2b。

🔴 **⛔ 以下機制全部不存在**（2026-09-11 隨舊 REST 對話鏈刪除，DSP-046）：
意圖分類與意圖加成、SOP／知識並行檢索與六 case 仲裁、SOP 觸發模式、表單狀態機、
離題偵測、信心度評估、答案優化五策略、業者參數注入。
⛔ 不要用它們解釋任何現行行為，也不要照它們設計新東西。

## 四道出口閘（順序不得重排）

| 序 | 閘 | 效果 |
|---|---|---|
| 1 | `scope_exit` | 清單點選會話問別戶 ⇒ 換 `SCOPE_EXIT_TEXT` |
| 2 | `handoff_without_lookup` | 零工具呼叫的 `no_grounding` ⇒ 降級成追問 `ASK_TARGET_TEXT` |
| 3 | `ask_target_gate` | `ask_target` 值域外 ⇒ 換指路句並歸零（保底閘） |
| 4 | `handoff_data_exits` | 有工具呼叫且**全部 `ok`** 時才接管 |

🔴 **閘 4 不是「查無」的保護網**：`jgb2.query.*` 查無回 `_no_match()`＝`ok:False`
⇒ `status="error"` ⇒ 閘 4 第一個條件就早退 ⇒ 使用者看到**轉人固定句**而不是 `NO_DATA_TEXT`。
pm 缺 `role_id` 走同一條鏈。轉人的五個來源見 `AGENTIC_MCP_ARCHITECTURE.md` §4b。

## 關鍵閾值（現行唯一一顆）

| 閾值 | 值 | 讀值點 |
|------|-----|---------|
| `KB_SIMILARITY_THRESHOLD` | 0.65 | `services/decision_layer.py::DecisionConfig` → `services/agent/tools/kb.py` |

⛔ 舊鏈的 SOP 0.55／KB 0.6／差距 0.15／完美匹配 0.90／合成 0.80／快速路徑 0.75／
信心度 0.85／0.70 **全部沒有程式讀者**。⛔ 不得改回 0.55（`decision_layer.py` docstring 明寫）。

## 面向（face）速查

**六域 16 個 face**（bills 5、contracts 5、accounts 2、repairs 2、iot 1、estates 1；各域 `*_FACE_BUILDERS`，合約域名為 `FACE_BUILDERS`，位於 `services/jgb/<域>.py`），註冊時由 `_jgb2_spec(domain, sorted(builders.keys()))` **現算**——
⛔ 不是資料驅動、加一個 key 不等於加一個能力（face 只選 builder，資料源硬編在 `query_<域>`）。
builder 簽名是單列 ⇒ **跨列彙總表達不出來**。擴充判準見
[`docs/architecture/facet-architecture.md`](../../docs/architecture/facet-architecture.md)。

- **寫入類走確認卡**：收齊欄位 ≠ 送出。`services/agent/confirm_card.py::render` 程式決定性產卡文字；
  三鈕機器值 `confirm_submit`／`confirm_edit`／`confirm_cancel` 在 `services/form_contract.py`，⛔ 值一個都不准改。
- **冪等**：execute 成功後標 `executed`；失敗誠實告知可重試、不設旗標。
- **可見性**：`AGENT_WRITE_TOOLS_ENABLED` AND `ToolSpec.stage`（DSP-038-1）。

## 候選分流速查（仍然有效）

API grounding 回 N 筆時：`N ≤ candidate_cap` → 直接列候選供選序號；
`N > cap` → 預設先請使用者補更明確的識別，補不動才截斷列前 cap 筆。

- **`result_mapping.skip_refine`（預設關）**：同母體多期資料（如同一合約的 26 期帳單）
  用關鍵字縮不了，補識別是**問使用者答不出來的問題** → 設 true 直接列候選，少一輪。
- ⚠️ **跳過的是「補識別輪」，不是「重查」**：使用者選定候選後仍會填回 `required_slots[0]`
  並**重查 API**。誤讀成跳過重查 → 有人會拿候選列欄位當 grounding，底稿就失去 API 權威來源。
- 旗標住在 `result_mapping`，管的卻是對話政策；⛔ 不改鍵名（改名＝改既有 DB 配置列）。
  查證：`grep -rn "skip_refine" rag-orchestrator/services/agent/`。

## 受眾只有兩種

對話層的受眾是 `prospect` 與 `property_manager`。知識正本只有一份「圖書館」：`rag-orchestrator/canon/jgb/A.md … I.md`（九架）＋衍生物 `CATALOG.md`（`ls rag-orchestrator/canon/jgb/`；說明見 `rag-orchestrator/canon/README.md`）；受眾不再各有一份正本，隔離改由 `canon_assembler.build_outline` 依細目的 `target_user`＋`business_types` 篩選。
**`tenant` 在對話層不存在**：`AGENT_TURN_SPEC["stage"]` 無 tenant 鍵 ⇒ `agent.turn` 永不可見。
⚠️ 但 `kb.search`／`help.read`／六域 `jgb2.query.*` 的 `stage` **含 tenant**——
資料存取層已開、缺的是對話層。⚠️ `audience_of` 把「其餘全部（含 `target_user=None`）」
映射到 tenant ⇒ **開 tenant 等於打開預設分支**。

## 系統角色對應

⚠️ 本檔每個 session 都被當專案記憶載入（`CLAUDE.md`：Load entire `.kiro/steering/`），
⛔ 過時一行的傷害大於一整份文件。以下每一支 2026-09-12 逐一確認存在。

| 組件 | 檔案 |
|------|------|
| 核心 | `services/agent/runtime.py::AgentRuntime` |
| 唯一掛著的門面 | `services/agent/mcp_facade.py`（`/mcp` 的 `agent.turn`） |
| 回合四段 | `turn_segments.py`／`turn_context.py`／`runtime.py`／`exit_gates.py` |
| 工具註冊表 | `services/agent/tools/registry.py`（in-process，⛔ 沒有 MCP client） |
| 六域查詢 | `services/agent/tools/jgb2.py` → `services/jgb/*` |
| 知識（路 B） | `services/agent/tools/kb.py` → `vendor_knowledge_retriever_v2.py`／`base_retriever.py` |
| 知識（路 A） | `services/agent/canon/`（git canon → FineIndex → CandidateSelector K=5） |
| 會話狀態 | `services/agent/session_persistence.py`（借用 `form_sessions` 表） |
| 表單／確認卡常數 | `services/form_contract.py` |
| 輸出驗證 | `services/agent/verifier.py` |
| 快取 | `services/cache_service.py`（⚠️ **不在對話回合路徑上**） |

⛔ **已不存在**：`intent_classifier.py`、`confidence_evaluator.py`、`sop_orchestrator.py`、
`sop_trigger_handler.py`、`form_manager.py`、`digression_detector.py`、`llm_answer_optimizer.py`、
`conversational_engine.py`、`api_call_handler.py`、`system_context.py`、`routers/chat.py`。

## 現行入口

唯一**掛著的門面**是 `/mcp` 的 `agent.turn`（`services/agent/mcp_facade.py`）。
⚠️ **它不是核心**——核心是 `AgentRuntime`，`/mcp` 只是接在它外面的門面之一
（見 `docs/architecture/SYSTEM_ARCHITECTURE.md` §1）。
⛔ **實際上沒有分流、沒有回退、沒有影子在運作**——但原因不是程式被刪：
`routers/agent_entry.py`（REST 分流，實作 R9.3 對外契約）與 `services/agent/shadow.py`
（影子，實作 R8）**都還在**，它們失去的是另一端——舊 REST 鏈。
`routers/agent_entry.py` 是**新架構為 strangler 遷移寫的橋**（spec 任務 2.2／R9）：站在舊鏈 `chat.py` 的請求路徑上分流，**⛔ 它不是端點、本來就沒有 `APIRouter`**。⛔ **掛路由救不活它**——上游需要的 `VendorChatRequest`／`VendorChatResponse`／`_conversational_to_response`／`sse_event`／`metered` **五樣全隨 `chat.py` 刪除**，回退目標（舊鏈）也不在。
影子沒有第二條線可以比對。⚠️ R8／R9 仍在 spec 內未撤案。

🔴 **2026-09-12 更正**：前一版寫「`AGENT_AUDIENCES` 已連同它管的入口一併移除」——**那是錯的**
（我先刪後還原，忘了把這句改回來）。實況：`agent_entry.py::agent_audiences()` 仍讀它、
`mcp_facade._AGENT_CONFIGURED_ENV_KEYS` 仍含它、**兩份 compose 都仍宣告**。
它只是**沒有生效對象**（要它分流的入口不存在），⛔ 不是被移除。
`agent_configured()` 的判準是三把鍵任一有值：`AGENT_AUDIENCES`／`AGENT_SHADOW_AUDIENCES`／`AGENT_TURN_ENABLED`
（查證：`services/agent/mcp_facade.py:_AGENT_CONFIGURED_ENV_KEYS`）。
⛔ 不要以「清空某個旗標就能回切」做決策——沒有可回切的對象，只能回滾版本。
