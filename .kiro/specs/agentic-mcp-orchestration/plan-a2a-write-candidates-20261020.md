# A-2a 片計畫：寫入時名稱對到多筆，由程式列候選、使用者選定後回原流程（2026-10-20，草稿 r2）

- 規則與凍結清單（同一檔）：`acceptance-a2a-write-candidates-20261020.md`（A2-R0～A2-R13、非目標 N1～N2、V0～V17 含 V2b）。
- 依據：DSP-091（分工）、DSP-101（範圍與順序）、DSP-100（B 的已知代價）；目標正本 §4 A-2a 列。
- 證據目錄：`~/jgb-archive/arch-step3-20261018/a2a/`（repo 外；業界原文在 `sources/`，索引 `sources/INDEX.md`）。
- 狀態：業主 2026-10-20 核可（DSP-103；Q1 全部含帳單、Q2 甲、Q3 新增 pick:），施工中。審查歷程——r1 經 security-reviewer（P1 1、P2 3、P3 6、P4 2，處置見 §11）；r2 經 plan-verifier REVISE（P2 5，處置見 §12）；r3 經第二位 plan-verifier REVISE（P2 5，處置見 §13；兩次自動 REVISE 已到上限，主持人逐條處置後開一次收尾審查）；r4 收尾審查 REVISE（P2 1，substantive，見 §14），r5 已修、未再審，暫停交業主；業主未核可。核可前 repo 內程式與測試 0 改動。

## 1. 目標（業主原話整理成的規則見規則檔第三節）

使用者在寫入流程中講了一個名稱，系統裡對到兩筆以上時，畫面上要看得到這幾筆、能點選或用說的選一筆，選完直接繼續原本的建立或變更（出確認卡），不必再講一次其他欄位。清單與選定都由程式掌握（DSP-091），B 擋住的假狀態句維持 0。

| 指標 | 現值（出處） | 本片預期 | 清單 |
|---|---|---|---|
| 終點指標：E2b 程式前判 | 29/32（B 收案，DSP-100） | ≥30/32，C-B 兩場皆解決 | V12 |
| 合約同名候選清單可見 | 13/20（B 同題對照 post，DSP-100；B 前 20/20 為模型自寫） | ≥19/20，且由程式產生 | V8 |
| 無依據狀態句 | 0/220（B post） | 維持 0/220 | V11 |

## 2. 目標形態（業界與第一原理；不看自家現況）

業界原文逐字見 `sources/INDEX.md`；下表只寫原文直接支持的，未查完的照寫。

| # | 目標形態 | 原文依據（檔名） | 不能推的部分 |
|---|---|---|---|
| T1 | 候選由程式從使用者自己的資料產生，以按鈕／清單呈現 | Rasa："use a custom action to get the list of cards associated with the user"（rasa-responses.txt）；Zendesk："retrieve the list of recent orders"（zendesk-answer-step-types.txt）；Apple："Needs disambiguation — Specify this resolution when you identify two or more possible results and cannot choose one definitively."（apple-sirikit-resolve.txt） | Intercom Fin："Fin will read the full contents of the items list and respond"（LLM 呈現）；Salesforce workshop 由推理引擎挑紀錄。⇒ ⛔ 寫「業界都由程式產生」。本片選程式產生的理由是 DSP-091（已選定的那筆紀錄歸程式）＋B 前 4/220 假狀態句教訓，不是「業界都」。 |
| T2 | 按鈕直接帶值、跳過語意理解 | Rasa："buttons provide the advantage of skipping the NLU pipeline … set slot commands defined in the payload"（rasa-responses.txt）；Lex："the response from the user is constrained to the text associated with a button"（lex-api-imageresponsecard.txt） | — |
| T3 | 按鈕與打字並存，打字可用序數、自然語言、部分標題 | Copilot Studio："each choice appears as a button, but users can also type their answer"（copilot-ask-a-question.txt）；Alexa："Allow customers to select options using ordinals" "Allow customers to select options using natural language, including synonyms and partial titles"（alexa-patterns-lists.txt）；Rasa 打字由 Command Generator（LLM）產生 `set slot`（rasa-command-generator.txt） | 序數怎麼解析：Rasa、Copilot、DFCX、Lex 未查完。 |
| T4 | 比對不到就重問，有上限後轉其他出口；仍模稜兩可要再追問 | Rasa："The assistant will repeatedly ask for the slot until the value is not rejected"（rasa-flow-steps.txt）；Copilot："Repeat up to 2 times is the default." "You can escalate to a human agent or provide a default value."（copilot-ask-a-question.txt）；Alexa："Follow up to disambiguate if the customer makes a selection that could indicate more than one of the options"（alexa-patterns-lists.txt） | — |
| T5 | 選定後回到原流程，已填的值保留 | Rasa："Once the child flow is complete, the execution continues with the parent flow." "Slots of the parent flow will not be reset when the child flow is activated."（rasa-flow-steps.txt）；Copilot："it resumes in the originating topic by default"（copilot-topic-management.txt）；DFCX END_FLOW（dfcx-handler.txt）；Apple customIdentifier 再解析（apple-sirikit-resolve.txt） | Fin 未查完。 |
| T6 | 候選數有上限（5～10），長清單不要一次列全 | Lex 按鈕 "Maximum number of 5 items"（lex-api-imageresponsecard.txt）；Zendesk "up to 10 options"（zendesk-carousels-ai-agents.txt）；Alexa "Paginate long lists" "Don't: Be tempted to include all possible options in one list."（alexa-patterns-lists.txt） | 超過上限怎麼辦只有 Alexa 寫（分頁）。 |
| T7 | 多筆可能時不替使用者選；寫入前確認 | Alexa："Don't: Make an assumption and select for them when there's more than one plausible match"（alexa-patterns-lists.txt）；Copilot："Makers can require user confirmation before executing tools that modify data."（copilot-faqs-generative-orchestration.txt）；Lex confirmation prompt（lex-intent-confirm.txt） | Apple 允許 educated guess（"Use this resolution even if it means making an educated guess"）＋確認——與 Alexa 不同。本片選「不猜」：寫入有後果（帳單掛錯合約），且已有確認卡兜底；理由見 §5 偏離 3。 |

第一原理補充（查無業界對應，自行推導）：候選集要存在伺服端、按鈕只帶編號且伺服端驗證屬於候選集——否則按鈕值等於一條任意編號輸入通道（JGB 前端把 `quick_replies` 值原樣送回，使用者或呼叫端可自造值）。業界頁面沒寫到這層驗證（未查完），本片依安全規則加。

## 3. 差距（自家現況，此時才讀程式）

查證指令（repo 根目錄）：

| # | 現況 | 查證 | 對應目標 |
|---|---|---|---|
| G1 | 合約名稱多筆：`_resolve_unique_contract` 回 `"many"` ⇒ `_missing_fields_result(["合約"])`，只回「還需要：合約」、不列候選；物件名稱多筆、物件多份有效合約同此 | `grep -n 'if status == "many":' -A1 rag-orchestrator/services/agent/tools/confirm.py`；`grep -n "_only_valid_contract_of_estate" rag-orchestrator/services/agent/tools/confirm.py` | T1 |
| G2 | B 片狀態回話依同一支解析回「還需要：合約」（DSP-100 已知代價：清單可見 20/20 → 13/20）；B 前的清單是模型自己寫的（未經程式） | `grep -n "def closed_action_missing_labels" rag-orchestrator/services/agent/tools/confirm.py`；證據 `~/jgb-archive/arch-step3-20261018/b/ab/AB-result.md` | T1、A2-R8 |
| G3 | 帳單候選已有程式清單＋`select:bill:<id>` 按鈕，但點下去走 LIFF 點選段：清草稿、寫 `SELECT_SCOPE_KEY`、回帳單 facts，下一步交模型（KD-1） | `grep -n "CONFIRM_CANDIDATES_TEXT =" rag-orchestrator/services/agent/runtime.py`；`grep -n "clear_write_draft()" rag-orchestrator/services/agent/runtime.py`（`_run_select_segment` 內） | T5 |
| G4 | 打字選定無程式路徑：E2b C-B_k1 使用者說「應該是到期日2027/04/30那筆」仍回「還需要：合約」，直到打出編號 `80304`（數字走 `contract_ids` 精確查）才出卡 | `~/jgb-archive/arch-step3-20261018/b/e2b3/convs/C-B_k1/turns.jsonl` 第 6～7 回合；`grep -n "if ref.isdigit():" rag-orchestrator/services/agent/tools/confirm.py` | T3、T4 |
| G5 | `repair_create` 物件名稱多筆：出卡端 `open_repairs` 回 `None` ⇒ 卡照出，按確認後兌現端 `_resolve_estate` 判不出唯一 ⇒ 失敗 | `grep -n "有列但判不出唯一一列（多筆）⇒ 回 None" rag-orchestrator/services/agent/mcp_facade.py` | T1、T7 |
| G6 | 意圖判斷呼叫（`WriteIntent`）只抽「使用者原話裡的值」，看不到候選清單，無法回「指哪一筆」 | `grep -n "def write_intent_system_prompt" rag-orchestrator/services/agent/write_forms.py` | T3 |
| G7 | 候選上限現值 5（`CONFIRM_CANDIDATES_MAX`、`JGB2_CANDIDATE_CAP` 預設）；多於 5 筆時現況只截前 5 | `grep -n "CONFIRM_CANDIDATES_MAX =\|_DEFAULT_CANDIDATE_CAP =" rag-orchestrator/services/agent/runtime.py rag-orchestrator/services/agent/tools/jgb2.py` | T6 |
| G8 | jgb2 preview `AgentTurnClient::normalize` 對 `quick_replies` 只限筆數與長度、不檢查值前綴（後端透傳已查）；前端 Vue 送回值的行為未逐行查（推定與 `confirm_submit:`／`select:` 同一機制，**未查完**） | `git -C ~/dev/work/jgb2/dev2 show origin/preview:app/Services/Assistant/AgentTurnClient.php \| grep -n "MAX_QUICK_REPLIES"` | A2-R3 |
| G9 | mock 資料可驗：同名合約 6 組（含「台北中正-小南門單身貴族分租套房D」2 筆）、同名物件 4 組（含「台北文山-離塵一房(國泰)」2 筆） | `python3` 讀 `rag-orchestrator/services/jgb/fixture_data/assistant_demo_vendor4.json` 依 `title` 計數 | V8～V10 |

## 4. 路徑（設計）

### 4.1 候選產生（G1、G2、G5 → A2-R1、A2-R2、A2-R8）

- `confirm.py` 解析多筆的各出口（合約 many、物件 many、物件多份有效合約、`repair_create` 物件 many）改回**候選形狀**：沿用帳單已有的 `_bill_candidates_result` 同型（`data["candidates"]`＋`action`／`payload`＋新增 `field`），列由同一支帶 viewer 查詢取得（合約：`_viewer_contract_rows`；物件：`_viewer_estate_rows`；物件多份有效合約：該物件的有效合約列）。⛔ 新增揭露面更大的查法。
- **雙證條件**（§11 P2-3）：候選列只在 `_identity_pair` 的 `role_id` 與 `user_id` 都有值時產生；缺任一 ⇒ 不列清單，維持現行出口（封閉三動作現行即 `NO_MATCH`；`repair_create` 維持現行）。⛔ 沿用 `mcp_facade` `_open_repairs` 閉包的查詢結果列清單（缺 `user_id` 時那是全團隊範圍）。
- `repair_create` 物件多筆：出卡前先判（與兌現端 `_resolve_estate` 同一判準），多筆 ⇒ 候選；查無與上游失敗維持現行。
- **候選集只在程式依草稿發出的 `confirm.request`（`wd_program`／提議轉成的程式呼叫）時寫**（§11 P3-4）；文件回合、文件暫存回合、點選範圍回合、模型自呼路徑收到候選形狀 ⇒ 維持現行缺欄出口（「還需要：…」），⛔ 寫候選集。
- Runtime 收候選形狀的那一段（現 `_CONFIRM_CANDIDATE_DOMAIN` 只有 `bill_due_extend`）擴成封閉表：動作 × 欄位 ⇒（投影 domain、pick 型別、固定句）。固定句分合約／物件／帳單三句，⛔ 插值使用者值，只插筆數。dialog 只寫程式摘要（比照 `CONFIRM_CANDIDATES_DIALOG_SUMMARY`）。
- B 片 `_write_reply_state` 分支 (3)：缺欄原因是名稱多筆時，狀態回話＝候選清單＋按鈕（A2-R8）；乙′ 狀態行同此。**清單與候選集由同一支函式、同一次查詢產生**（§11 P3-6），⛔ 清單與候選集分兩次查；`_write_reply_state` 與 `closed_action_missing_labels` 的 docstring 由「唯讀」改為「⛔ 出卡、⛔ 建 token、只寫候選集」。

### 4.2 候選集與按鈕選定（G3 → A2-R3、A2-R6、A2-R9）

- 候選集存在 `agent_state["write_candidates"]`：`{action, field, type, ids:[str…], name_fp, creator, picked}`。
  - `ids` 一律 `str(id).strip()`，≤20（同一次查詢第一頁的全部列，程式截 20；畫面只列前 5 筆，見 §4.4）；`has_more`＝上游還有下一頁或多於 20；`type` ∈ {contract, estate, bill}；`creator`＝`_pending_creator(identity)`（§11 P2-2）。
  - `name_fp`＝列出候選時**該欄位的名稱值**指紋（不含其他欄位；§11 P4-2）：使用者在同一或後續回合改其他欄位（金額、項目）不使候選集失效；該欄位被改成別的名稱 ⇒ 失效。
  - `picked`＝選定的編號（未選定為 `None`）；**選定編號只存在這裡**，⛔ 寫進草稿（草稿 `DRAFT_KEYS` 封閉、不收系統解析的編號，§11 P2-1）。模型、意圖呼叫、提議路徑都 ⛔ 寫 `picked`。`picked` 進卡的唯一通道見 §4.5「程式專用選定通道」，⛔ 經 `args.payload`。
  - ⛔ 存名稱或列內容。
- **生命週期**（§11 P3-2）：註冊進 `agent_session.KEY_SPECS`，壽命 `UNTIL_SCOPE_EXIT`（`assert len(KEY_SPECS)` 改 14）；`AgentSession.clear_write_draft()` 內一併清候選集（單一清除點，涵蓋取消、送出、換動作、閒置、換身分、`select:` 釘住範圍）；新清單覆蓋舊的；**出確認卡時清**（出卡後舊候選按鈕一律失效句；要換一筆請使用者再講）。讀回由新增的 `load_write_candidates` 驗形狀（封閉鍵、ids ≤20、型別值域、creator 存在），不合 ⇒ 丟棄並記標記，比照 `load_draft`。
- 入向機器值 `pick:<contract|estate|bill>:<id>`（`[A-Za-z0-9_-]{1,32}`、`fullmatch`、⛔ NFKC、⛔ strip）。**處理點在 `_write_draft_begin` 之後**（草稿已過 `load_draft`、建立者比對、`SELECT_SCOPE_KEY` 清草稿；§11 P2-2），並另檢：entry＝mcp、非影子回合、非文件回合與文件暫存回合、`_write_draft_visible`、開關 on。
- 判定成立的條件（全部成立；§11 P3-3）：候選集存在且形狀合法、`creator` ＝本回合身分、`(type, 候選集 field, str(id).strip())` 與候選集吻合（型別不符即不成立）、草稿存在且動作＝候選集 `action`。不成立 ⇒ 失效固定句、0 次 JGB 查詢、草稿與 token 不變。成立 ⇒ 寫 `picked`，走 §4.5。
- 帳單候選按鈕由 `select:bill:<id>` 改為 `pick:bill:<id>`（Q1 含帳單時）。LIFF 清單的 `select:` 路徑不變。

### 4.3 打字選定（G4、G6 → A2-R4）

候選集有效的回合，意圖判斷呼叫多帶一段「候選清單」資料段（每列只放投影欄、先過 `sanitize_data_piece`，nonce 包住；§11 P3-1），schema 加欄位 `pick_id`，strict schema 以**動態 enum**（候選集編號＋`none`）限制。程式仍再驗 `pick_id` ∈ 候選集（同 §4.2 判定條件）：成立 ⇒ 等同按鈕選定；`none` 但該欄位有新名稱 ⇒ 依新名稱重新解析（使用者改講別的名稱）；其餘 ⇒ 重列同一份候選＋標記。這打破 `write_intent_system_prompt`「⛔ 含任何資料段」的現行不變量，該函式註解同步改寫（只在候選集有效回合附此段）。主模型輸出 schema 不變。這是 Q2 建議案（甲）；乙案見 §6。

殘餘風險（照實寫）：同團隊成員能替紀錄命名，惡意標題可能把打字選定導向**候選集內**的另一筆；跨業者不受影響（標題只來自 viewer 可見列）；兜底是確認卡（卡上印選中紀錄的編號與名稱）。V9 加惡意標題案例量測。

### 4.4 筆數上限（G7 → A2-R7）

畫面列前 5 筆（每筆一顆按鈕）＋「還有其他筆…」固定句；**候選集保存同一次查詢的全部列（≤20）**，畫面外的列只是沒顯示、仍屬候選集（plan-verifier r3 P2-1）。

- 打字描述（編號、序數、到期日、狀態）：意圖判斷呼叫的候選資料段放候選集**全部** ≤20 列的投影（`_project_contract_row`：編號、名稱、到期日），`pick_id` 動態 enum 同為全部 ≤20 個編號＋`none`。AI 只理解「指哪一筆」，程式依 §4.2 判定條件收下。所以「到期日 2027/04/30 那份」即使是第 6 筆，也在 enum 內。
- 編號不在候選集（例如超過 20 筆或 `has_more` 時的其他列）：使用者講的是純數字 ⇒ 程式以 `_viewer_contract_rows(contract_ids=…)`／`_visible_estate_by_id` 精確查（現行 `_resolve_unique_contract` 的 `ref.isdigit()` 分支同一支），查到且名稱與候選集欄位名稱相同 ⇒ 成立；否則重列＋標記。非編號描述指到候選集外 ⇒ 重列同一份候選＋固定句「還有其他筆，不在其中請講編號」（⛔ 程式自己解析日期詞）。畫面上「還有其他筆」那一句也用同一句。
- 到期日誤入其他欄位的風險：描述選定用的日期可能被意圖呼叫抽進 `manual_bill_create` 的 `date_expire`。意圖提示寫明「描述哪一筆用的值不是欄位值」，V9、V16 量「卡上 `date_expire`＝描述用的到期日」次數，門檻 0。
- ⛔ 做分頁按鈕（業界只有 Alexa 寫分頁；按鈕面板筆數有限，jgb2 `MAX_QUICK_REPLIES` 為 10）。

### 4.5 回原流程（A2-R5）

選定 ⇒ 程式依草稿發出 `confirm.request`（`_write_draft_decide` 的觸發條件同一支），經**程式專用選定通道**帶入 `picked`，出卡前以帶 viewer 的精確編號查詢重新確認可見。

**程式專用選定通道**（plan-verifier r2 P2-a）：

- 形狀：`program_pick = {"action", "field", "type", "id"}`，由 runtime 從候選集 `picked` 組出。
- 傳遞：`ToolRegistry.call` 新增具名參數 `program_pick`（預設 `None`）→ 只轉給 `confirm.request`（`confirm_request(..., program_pick=...)`，形狀比照既有具名注入 `open_repairs`）→ `_prepare_closed_action`／`repair_create` 出卡前解析。**⛔ 經 `args`／`args.payload`**：模型 tool call、MCP client 直呼 `confirm.request`、提議路徑都只能碰 `args`，碰不到這個參數。
- 設定點唯一：runtime 只在 `wd_program` 為真（程式依草稿發出）且候選集判定成立（§4.2）時傳；其他呼叫一律 `None`。比照 A+ AP-4 `draft_payload` 只由程式呼叫端設的做法。
- 兌現端：卡上的 payload（含程式解析出的系統編號）照現行由 confirm token 帶到 `jgb.action.*`，兌現端仍以帶 viewer 的精確編號查詢重驗。

**模型自帶系統編號照丟（每條路徑）**：`_prepare_closed_action` 既有的 `payload.pop("estate_id")`（`contract_create`）、`payload.pop("contract_id")`（`manual_bill_create`）**保留在最前面、無條件執行**；`repair_create` 新增同型 `payload.pop("estate_id")`（§11 P1-1）。丟完之後：有 `program_pick` 且動作、欄位相符 ⇒ 依編號解析；否則 ⇒ 依名稱解析（現行）。

`bill_due_extend` 例外照實寫：模型帶 `bill_id` 是現行支援的路徑（`_resolve_bill_by_period` 註解「有編號 ⇒ 完全不走這一段」；兌現端 `action` 以 `viewer_bill_row` 重驗），本片 ⛔ 改它（改了會動到點選範圍與 LIFF 既有流程，不在 A-2a 範圍；KD-1 歸 A-2）。本片只加：有 `program_pick`（型別 bill）時，以 `program_pick` 的編號**覆蓋** payload 的 `bill_id`，並在出卡前以 `viewer_bill_row` 重驗。

各動作依編號解析：

- 合約（`manual_bill_create`）：`_viewer_contract_rows(contract_ids=…)`＋編號比對（與 `_resolve_unique_contract` 的 `ref.isdigit()` 分支同一支查詢）；兌現端既有 `_visible_contract_by_id`。
- 物件（`manual_bill_create`、`contract_create`）：`_visible_estate_by_id`；兌現端既有 `_visible_estate_by_id`。
- 帳單（`bill_due_extend`）：`viewer_bill_row`＋`_fill_bill_fields`（**不依賴** `AGENT_WRITE_LIFECYCLE` 的 `_run_form_precheck`；§11 P3-5）；兌現端既有 `viewer_bill_row`。
- **`repair_create` 物件（§11 P1-1）**：(i) 出卡前丟模型自帶 `estate_id`（上段）；(ii) 依 `program_pick` 以 `_visible_estate_by_id` 解析並寫入卡 payload 的 `estate_id`；(iii) 卡上印物件編號（`_render_repair_create` 加一行，S2 1d「卡上編號＝寫入編號」）；(iv) 兌現端 `action.repair_create` 在卡 payload 有 `estate_id` 時改用 `_visible_estate_by_id`（看不到 ⇒ `NO_MATCH`），無 `estate_id` 時維持現行名稱解析。
- 看不到 ⇒ 查無固定句。欄位齊 ⇒ 出卡（並清候選集）；仍缺 ⇒ B 片缺欄追問。按鈕回合不呼叫主模型與意圖判斷呼叫。

改動的函式：`ToolRegistry.call`、`confirm_request`、`_prepare_closed_action`、`repair_create` 出卡前解析（`confirm.py`）、`_render_repair_create`、`action.repair_create`、runtime 的 `wd_program` 呼叫點。

### 4.6 開關、標記、文件

- 開關 `AGENT_WRITE_CANDIDATES`（未設／空＝on）；off ⇒ B 行為。只在 A+ 出卡開關與 `AGENT_WRITE_DRAFT` 皆 on 時生效（候選集只由程式依草稿出卡時寫）。
- trace 標記（只記型別與筆數）：`write_candidates_shown:<型別>:<n>`、`write_candidate_pick:button|typed`、`write_candidate_pick_invalid`、`write_candidate_reask`。
- 文件同步：`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`（終止點表、候選段）、`docs/api/mcp-facade.md`（新機器值）、目標正本 §3.1 KD-8 與 §4 A-2a 列、HANDOFF、MAP、新 DSP（機器值契約與選定方式）。

## 5. 偏離目標形態的取捨（照實寫）

1. **⛔ 分頁、上限取 5 不取 10**（T6 Alexa 分頁；面板上限 10）：改為畫面列 5 筆＋固定句「還有其他筆，不在其中請講編號」；候選集保存全部 ≤20 列，畫面外的列可用文字描述選定（§4.4）。事實：mock 有 6 份同名合約「基隆好房」（G9），多於 5 筆的情境確實存在，由 V16 實打量測。對使用者的理由：同名紀錄的按鈕只靠編號與到期日區分，筆數越多越難一眼找到要的那筆；第 6～20 筆不必翻頁，直接講「到期日 X 那份」或編號即可選定；超過 20 筆時只能講編號（代價照實寫）。上限 5 與 Lex 按鈕卡上限、現行帳單候選 `CONFIRM_CANDIDATES_MAX` 一致。現況比較好做（沿用既有上限、不做分頁狀態）也是理由之一，照實寫。V16 若顯示使用者找不到第 6 筆以後的那筆，⇒ 停，交業主改上限或做分頁。
2. **打字選定的理解交 AI、選定由程式驗證**（T3 Rasa 由 LLM 產生 `set slot`）：程式只收候選集內編號。⛔ 用詞表或正規式解析「第二個」「到期日…」（專案規則：開放語義換層不補詞表）。
3. **不猜**（T7 Alexa；Apple 允許 educated guess＋確認）：選 Alexa 一側。理由：寫入有後果；猜錯靠確認卡攔的前提是使用者會細看卡上編號，B 片資料沒有證據支持這個前提。
4. **候選集存伺服端並驗證**：業界頁面未查到同層描述（未查完），依安全規則加；代價是候選集過期後舊按鈕失效。

相關但不在本次範圍：唯讀查詢的候選清單打字挑選（KD-8 其餘，歸 A-2）；點選範圍回合模型自呼出卡（KD-1，歸 A-2）；文件回合（KD-2）；結構化 `card`（C 片）。

## 6. 交業主裁的題目

- **Q1 範圍**（事實先講：接真 JGB 時 `contract_create`、`manual_bill_create` 屬 `WRITE_NOT_SUPPORTED_ACTIONS`，出卡前即以「尚未開放」收尾；所以上線當下只有 `repair_create` 物件同名與 `bill_due_extend` 帳單候選會實際用到本片，合約同名要等 JGB 前置（DSP-101）開放這兩個動作後才生效；mock 量測照做）：建議「寫入五動作中會發生名稱多筆的全部」＝合約同名（`manual_bill_create`）、物件同名（`manual_bill_create`／`contract_create`／`repair_create`）、物件多份有效合約、帳單候選改為選定後回原流程。替代：(i) 不含帳單（帳單維持 `select:bill`，KD-1 情境不變）；(ii) 只做合約同名（最小，物件同名 `repair_create` 仍「卡照出、按確認才失敗」）。
- **Q2 打字選定方式**：建議（甲）意圖判斷呼叫看候選清單、回「指哪一筆的編號」，程式只收候選集內編號（理解交 AI，可處理「沒過期那份」這類說法）。替代（乙）AI 只抽條件（編號／序數／日期），程式依條件在候選集篩：更決定性，但條件種類要逐一定義、「沒過期那份」這類需要再加條件型別。
- **Q3 新入向機器值 `pick:<型別>:<編號>`**：對外契約新增（JGB 面板後端已確認透傳任意值；前端未查完，§3 G8）。建議採用並記新 DSP；替代：沿用 `select:<型別>:<id>` 但在候選集有效時改走選定（同一個值兩種語義，LIFF 清單點選與寫入選定難分，不建議）。

## 7. 執行切片與驗收順序

單片施工（耦合在同一條寫入路徑，⛔ 拆給多個寫手）：主 session 直做或一位 `executor`（依全域派工規則）；security 相關部分（機器值攔截、候選集驗證）由 `security-executor`。順序：單元 V2～V7 → `make audit`／契約 V13 → 重建容器、mock 檢查 True → 實打 V8～V11、V15～V17、V2b → E2b V12（先依 DSP-102 改前判並附正對照）→ fresh verifier V14 → 報告與文件同步。

## 8. 停點（只用結果條件）

- V8、V9、V15 或 V16 未達門檻 ⇒ 停，寫原因交業主（⛔ 自行調門檻或改題）。
- V11 任一項比 B 差 ⇒ 停。
- V12 <30/32 或 C-B 未解決 ⇒ 停，逐場原因交業主。
- 實作需要讓模型決定 DSP-091 程式列環節的下一步才能過 ⇒ 停（A2-R10）。
- security-reviewer／plan-verifier 的 P0／P1 未解 ⇒ 不交核可。

## 9. 回退

開關 `AGENT_WRITE_CANDIDATES=off` ⇒ B 行為；程式回退＝revert 本片 commit。候選集鍵 `write_candidates` 在 off 時不讀不寫，殘留值無作用。

## 10. 用量回報

片收尾回報子代理 token 加總（任務通知 `subagent_tokens` 加總）與本機 Bedrock 呼叫費用估算；⛔ token 上限當停點。計畫期至今：業界原文代理 191,803、security-reviewer 199,275。

## 11. security-reviewer r1 處置（2026-10-20）

主持人已抽查決策所依的三項證據：`action.repair_create` 以 `keyword=estate_name`＋`_resolve_estate` 兌現（`grep -n "estate = _resolve_estate(" rag-orchestrator/services/agent/tools/action.py`）；`DRAFT_KEYS` 封閉五鍵（`grep -n "^DRAFT_KEYS" -A1 rag-orchestrator/services/agent/write_forms.py`）；`run_program_segments(` 早於 `self._write_draft_begin(acc`（`grep -n "run_program_segments(\|self._write_draft_begin(acc" rag-orchestrator/services/agent/runtime.py`）。

| 編號 | 等級 | 摘要 | 處置 | 落點 |
|---|---|---|---|---|
| P1-1 | P1 | `repair_create` 選定後兌現仍依名稱解析；模型可帶 `estate_id` | FIX | §4.5 `repair_create` 三件；A2-R5；V10 |
| P2-1 | P2 | 選定編號存草稿與 `DRAFT_KEYS` 封閉衝突 | FIX（採 (a)：只存候選集 `picked`，程式注入） | §4.2；A2-R6 |
| P2-2 | P2 | pick 段早於草稿驗證與建立者比對；候選集無 creator | FIX | §4.2 處理點與判定條件；V3 |
| P2-3 | P2 | 缺 `user_id` 時物件列是全團隊範圍 | FIX | §4.1 雙證條件；A2-R2；V2 |
| P3-1 | P3 | 候選標題進意圖呼叫的注入風險 | FIX（sanitize、動態 enum、量測） | §4.3；V9 |
| P3-2 | P3 | 候選集生命週期實作點 | FIX（`KEY_SPECS`、單一清除點、讀回驗證、出卡即清） | §4.2；A2-R6 |
| P3-3 | P3 | 型別與欄位一起比、編號字串化 | FIX | §4.2 判定條件；V3 |
| P3-4 | P3 | 模型自呼路徑收到候選形狀 | FIX（只在程式依草稿發出時寫候選集） | §4.1 |
| P3-5 | P3 | 帳單選定依賴 `AGENT_WRITE_LIFECYCLE` | FIX（pick 路徑直接 `viewer_bill_row`＋`_fill_bill_fields`） | §4.5 |
| P3-6 | P3 | 清單與候選集需同一次查詢；唯讀契約改寫 | FIX | §4.1 |
| P4-1 | P4 | `pick:` 原值進 dialog 被當使用者原話 | FIX（dialog 只寫程式摘要） | §4.1 |
| P4-2 | P4 | `draft_fp` 與保留其他欄位衝突 | FIX（改 `name_fp`） | §4.2 |

待查（不評等級，帶入施工）：真 JGB `get_estate_status(keyword=<編號>)` 能否以編號查到物件（`_visible_estate_by_id` 依此；施工前以 preview 唯讀查詢確認或標為未驗）；JGB 前端是否原樣送回 `quick_replies` 值（G8）；`session_id` 實務上是否跨身分共用（P2-2 嚴重度；已以 creator 比對防住，不影響設計）。

## 12. plan-verifier r2 處置（2026-10-20）

主持人已抽查：`_prepare_closed_action` 內 `payload.pop("estate_id", None)`、`payload.pop("contract_id", None)` 存在（`grep -n 'payload.pop("estate_id"\|payload.pop("contract_id"' rag-orchestrator/services/agent/tools/confirm.py`）；`ToolRegistry.call` 只以 `fn(identity, args)` 呼叫工具（`grep -n "return await asyncio.wait_for(fn(identity, args)" rag-orchestrator/services/agent/tools/registry.py`）；mock 同名合約「基隆好房」6 份。

| 編號 | 等級 | 摘要 | 處置 | 落點 |
|---|---|---|---|---|
| P2-a | P2 | `picked` 注入與既有「模型自帶編號一律丟」衝突、通道未定 | FIX（程式專用選定通道 `program_pick`，⛔ 經 `args`；pop 保留且無條件；`bill_id` 現行路徑不改列非目標 N2） | §4.2、§4.5；A2-R5；V5；N2 |
| P2-b | P2 | 偏離 1 理由與 mock 事實矛盾（基隆好房 6 份） | FIX（更正事實、改以使用者效果陳述理由、V16 量測並設停點） | §5 偏離 1；V16 |
| P2-c | P2 | A2-R2／R3／R6／R7 只有單元層證據 | FIX（V15 實打偽造／型別不符／過期按鈕；V16 實打 6 筆；A2-R2 實打入口探針 V2b） | V2b、V15、V16 |
| P2-d | P2 | 終點指標未寫現值與預期變化 | FIX | §1 指標表 |
| P2-e | P2 | 原話 2「排在 W2 之前並加進上線範圍」未對應規則或非目標 | FIX（非目標 N1） | 規則檔「非目標」節 |

## 13. plan-verifier r3 處置（2026-10-20；第二次自動 REVISE，主持人逐條處置）

主持人已抽查：`_viewer_contract_rows` 只收 `contract_ids`、`keyword` 兩個篩選（`grep -n "async def _viewer_contract_rows" -A3 rag-orchestrator/services/agent/tools/action.py`）；`WRITE_NOT_SUPPORTED_ACTIONS = frozenset({"estate_create", "contract_create", "manual_bill_create"})`（`tools/confirm.py`）；`confirm_source:program_draft` 標記存在（`grep -n '_csrc = "program_draft"' rag-orchestrator/services/agent/runtime.py`）。

| 編號 | 等級 | 摘要 | 處置 | 落點 |
|---|---|---|---|---|
| P2-1 | P2 | 到期日描述指到清單外那筆時沒有程式路徑 | FIX（候選集存同一次查詢全部 ≤20 列、畫面列 5；意圖資料段與 enum 涵蓋全部；候選集外只收編號精確查；`date_expire` 誤填量測） | §4.2、§4.4；A2-R7；V6、V9、V16 |
| P2-2 | P2 | V11、V12 沒有對應規則 | FIX（新增 A2-R13） | A2-R13；V11、V12 |
| P2-3 | P2 | A2-R10、A2-R12 只有中間證據 | FIX（V8 加出卡來源標記判定；新增 V17 開關 off 實打） | V8、V17 |
| P2-4 | P2 | V8 未列 A2-R8 | FIX | V8 |
| P2-5 | P2 | 按鈕選定是放寬、未標 | FIX（A2-R1 讀法欄標放寬與依據，A2-R3、A2-R9 引用） | A2-R1、A2-R3、A2-R9 |

待查 r3 所列「接真 JGB 時兩個動作尚未開放」：查證屬實，寫進 §6 Q1 前言，交業主裁範圍時一併看。

## 14. 收尾審查 r4 處置（2026-10-20；收尾審查不重開迴圈）

| 編號 | 等級 | 摘要 | 處置 | 落點 |
|---|---|---|---|---|
| C-1 | P2（substantive） | r3 P2-1 的修正只進 §4.4 與 V6、未進 A2-R7；A2-R7 與 §5 偏離 1 仍寫「依描述／更多條件重新查詢」，與 `_viewer_contract_rows` 只收編號與關鍵字矛盾 | FIX（A2-R7 改寫成 (a)～(d)，讀法欄標收窄「候選集外只能以編號選定」；固定句三處統一為「還有其他筆，不在其中請講編號」；偏離 1 理由改寫；V16 文字組改「選定後出卡」） | A2-R7；§4.4；§5 偏離 1；V6；V16 |

驗證（主持人）：`grep -n "以描述重新查詢\|更多條件\|程式重新查"` 兩檔 0 命中；正對照 `grep -c "還有其他筆，不在其中請講編號"` 計畫 2、規則檔 ≥1 命中。本處置**未經再審**（收尾審查不重開迴圈；審查員標 substantive，不適用「已修、未再審」例外），交業主決定核可或再審一次。
