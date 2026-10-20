# A+ 片計畫：出卡只由程式依草稿觸發（2026-10-19，草稿）

- 狀態：r3 草稿。r2 業主 2026-10-19 核可（Q1／Q2／Q3 裁示見 §8），AUTO，已實作；實測觸發 §7 停點（V7），業主裁「修 A+ 提議路徑」⇒ 新增 AP-7（§9）。r3 審查：security-reviewer 無 P0／P1（§9.4）；plan-verifier REVISE → 問業主（§9.6）→ 收尾審查剩 1 條 wording-only，已修、未再審；業主 2026-10-19 核可 r3（「核可 (Recommended)」，AUTO 沿用），AP-R10、V13 凍結。r2 審查：security-reviewer 無 P0／P1（§5）；plan-verifier 第 1 輪 REVISE（B1 V2 口徑、B2 草稿已清前提）→ 已修 → 第 2 輪 READY。
- 決策：DSP-091（分工）、DSP-094（上線範圍含 A+）、DSP-096（順序 A → 期別 → A+ → B …）。
- 規則與驗收清單：`acceptance-card-program-only-aplus-20261019.md`（規則 AP-R1～AP-R9、清單 V0～V12），核可時凍結。
- 服務原則（目標正本 `architecture-target-20261018.md` §2.8）：P1 寫入全程由程式持有、P4 程式掌握的環節由理解層輸出結構化指令、下一步由程式決定。
- 風險類別：寫入確認路徑（security-sensitive）⇒ 核可前 `security-reviewer`，再 `plan-verifier`；實作交 `security-executor`；完成後 fresh `verifier`。
- 盤查證據：`~/jgb-archive/arch-step3-20261018/aplus/`（`base_q.py`、`overlap.py`、`other.py`、`doc_q.py`、`sel_q.py`，輸出 `baseline-20261019.txt`）。

## 1. 目標

**使用者要的結果**：辦事時，說過的不被重問；卡片還在時不被要求重給資料；卡上的值都經過程式的值閘才進卡。依據規則 AP-R1～AP-R4。

值閘範圍（安全審查 1-4，既有行為、本片不改）：文字、數字、日期、Email、電話、期別欄位比對使用者原話；選項（`enum`）只查表單值域、修繕分類（`category`）只查分類樹，**不比對原話**——模型或意圖給的選項值只要在值域內就進草稿。本片讓模型參數不再繞過值閘直接進卡（現況是直接進卡），是收窄；選項與分類值比原話列為非目標（驗收檔第四節）。

**現況與目標的差距（量到的）**：A 片容器（2026-10-19 14:54 起，640 回合）中，模型自己呼叫 `confirm.request` 17 次，**17 次全部以模型參數算缺欄、回「還需要：…」**，0 次出卡；其中 13 次落在 A 後 E2b 重測的 10 場（W-R1_k1、W-R2_k1 ×3、W-R2_k2、W-R3_k1 ×2、W-R5_k1、W-D4_k2、W-D5_k1、C-B_k1、C-M_k2、C-R_k1），1 次在 `hits/R3`，1 次是期別片 verifier 那場（`01fd226a…`），2 次未對到場次。17 次的前因：

| 前因 | 次數 | 說明 |
|---|---|---|
| 程式優先等意圖逾時（`write_draft_program_first_wait_timeout`） | 9 | 意圖沒在等待時限內回來（無草稿 `WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S`＝1 秒、有草稿 `WRITE_DRAFT_PROGRAM_FIRST_WAIT_S`＝3 秒；9 次的 `write_draft_keys` 皆空，即 1 秒那一級） ⇒ 主模型自呼 ⇒ 以模型參數算缺欄；意圖的結果本回合沒被取用 |
| 綁定卡在、值相同（`write_draft_reissue_skipped_same_values`） | 5 | 業主原話 2 指的情形：程式不重出卡 ⇒ 交回模型 ⇒ 模型自呼少帶欄位 ⇒「還需要」 |
| 其他 | 3 | 無逾時標記、程式也沒觸發出卡（原因未逐筆查），模型自呼 |

**終點指標**：E2b 寫入＋更正題組 Intercom 解決數。基線 28/32，由兩次量測組成：W-R 7/10（A 後重測，report-ra §2）、W-D 9/10 與 C-D 2/2（期別片重跑，report-period §5.1）、C-B／C-C／C-E／C-M／C-R 10/10（A 後重測）。

| 量 | 基線 | 預期 | 理由 |
|---|---|---|---|
| E2b W＋C Intercom | 28/32 | 28～30/32 | 未解決 4 場：W-R2_k1（分類值閘，A-2）、W-R3_k1／k2（物件名截短 RC3，A-2）、W-D3_k2（W2 截斷）。主因都不在本片，本片只拿掉其中的模型路徑誤問；多數場次本來就解決，誤問只讓客人多講一次 |
| 模型路徑「還需要」 | 11 次／8 場（與終點指標同組成：A 後 W-R、C-B／C／E／M／R 共 11 次；期別片重跑 W-D、C-D 0 次） | 0 | AP-R1 |
| 「卡片還在」情形交回模型 | 5 次（A 片容器） | 0 | AP-R3 |

本片對終點指標的預期增量小（0～2 場），主要效果在機制層：模型參數不再進卡也不再產生誤問，B 片之後可以假設「出卡與缺欄追問一律是程式產出」。

**業主原話對照**

| 原話 | 對應 |
|---|---|
| 原話 1「A 片若要修模型主導路徑，須標「過渡修正」並指向 A+／G。」 | AP-R5 |
| 原話 2「卡片有效、值又相同時，改由程式回「卡片還在，請按確認」，不再交回模型。」 | AP-R3（放寬：重出同卡；Q2 待裁） |
| 原話 3「開始」（含「reissue gate 放 A+」照建議） | 本計畫；AP-R4 |
| 片定義「出卡只由程式依草稿觸發…模型改為提出寫入意圖」 | AP-R1、AP-R2（Q1 待裁） |

## 2. 目標形態（業界做法；原文存於 `~/jgb-archive/devflow-20261018/`，2026-10-18 渲染擷取）

- **理解層只產生指令，由對話管理照流程執行。**
  - Rasa 指令產生器（`sources-repair/rasa-llm-cmdgen.txt`）：「It outputs a sequence of commands that represent how the user wants to progress the conversation.」
  - Rasa 對話理解（`sources-repair/rasa-dialogue-understanding.txt`）：「These next steps are communicated as a set of “commands” for the dialogue manager to follow」「Each command issued by the dialogue understanding module can only leverage existing flows and knowledge bases. That means the system cannot create new workflows or generate responses beyond what has already been designed.」
- **確認由流程在欄位填齊後發出，不是由模型決定何時出。**
  - Amazon Lex（`sources-repair/lex-confirmation.txt`）：「After the conversation with the user is complete and the slot values for the intent are filled, you can configure a confirmation prompt to ask the user if the slot values are correct.」
  - Rasa（`sources-repair/rasa-flow-steps.txt`）以 collect 步收確認：「- collect: final_confirmation # slot name」「ask_before_filling: true」。
- **模型發出的工具呼叫先過執行端的規則，再決定是否執行。**
  - OpenAI Agents SDK（`sources-repair/openai-hitl.txt`）：「When the model emits a tool call, the runner evaluates its approval rule (needs_approval, require_approval, or the hosted MCP equivalent).」「If the approval rule requires approval and no decision for that tool call is stored, execution pauses」。
- **已填的欄位不重問。**
  - Rasa（`sources-repair/rasa-flow-steps.txt`）：「By default, a collect step is skipped if the corresponding slot is already filled.」
  - Zendesk（`sources-arch/zendesk-generative-procedures.txt`，目標正本 §2.2 已引）：「If a required detail is already available in the conversation, the AI agent may continue without asking again.」
- **卡片還在時重出同一張卡**：查無業界專節。第一原理推導：使用者重述與卡上相同的值，表示要的就是這張卡；JGB 面板只有最後一則訊息可互動（`jgb-spec-structured-card-draft-20261019.md` §3），所以要讓使用者能按，必須在最後一則重出同一張卡與按鈕。
- **限制**：以上只查 Rasa、Lex、OpenAI Agents SDK、Zendesk；不代表全業界。Intercom、Salesforce 由 AI 決定程序內下一步（目標正本 §2.1），本線依 DSP-091 採程式決定。

## 3. 差距（現況，附可 grep 的符號；查證指令在 repo 根目錄執行）

1. **模型自呼仍以自身參數執行**：`rag-orchestrator/services/agent/runtime.py` `_run_model_loop` 內，`name == CONFIRM_TOOL_NAME and not wd_program` 時先 `_write_draft_merge_model_confirm`（只合併進草稿），接著仍以模型的 `raw_args` 呼叫 `self.registry.call`；結果走 `missing_fields_ask_text`（缺欄追問）或 `_begin_pending_confirm`（出卡）。`_write_draft_merge_model_confirm` 的 docstring 寫明「這一次呼叫本身 ⛔ 改」。
2. **模型自呼成功會擋掉程式觸發**：`_WriteDraftTurn.model_confirm_ok`（`grep -n "model_confirm_ok" rag-orchestrator/services/agent/runtime.py`）。
3. **值相同時交回模型**：`_write_draft_reissue_gate` 值相同 ⇒ 記 `write_draft_reissue_skipped_same_values`、回 `False` ⇒ `_write_draft_decide` 回 `None` ⇒ 主模型接手。
4. **值相同以字串比對 `confirm.request` 改寫後的 payload**：`_write_draft_reissue_gate` 的 `str(new_payload[k]) != str(old_payload.get(k))`，`old_payload` 取自 `pending_confirm[pid]["payload"]`（`_begin_pending_confirm` 存的是 `confirm.request` 回傳的 payload）。
5. **綁定卡有效性只看 session 狀態**：`_write_draft_bound_card` 只看 `pending_confirm` 的動作與建立者；token 是否過期（`CONFIRM_TOKEN_TTL_S`，600 秒）、是否已兌現只在兌現時（`_REDEEM_PENDING_SQL`）才知道。`tools/confirm.py` 沒有唯讀查 token 狀態的函式（`grep -n "^async def \|^def " rag-orchestrator/services/agent/tools/confirm.py`）。
6. **逾時後意圖結果被丟掉**：程式優先等意圖逾時後，若模型自呼得缺欄，回合在 `confirm_missing_fields_ask` 出口結束，`_write_draft_decide` 沒被呼叫，意圖結果只在 trace 收尾時計 token（`_WriteIntentCall.settle`），不合併。
7. **文件回合與點選範圍回合**：`_write_draft_decide` 對兩者都不觸發（`document is not None`、`SELECT_SCOPE_KEY`），由模型自呼出卡。使用量：2026-09-01 起 `document_*` 1 次；2026-10-18 起點選範圍回合 1 次（`aplus/baseline-20261019.txt`）。
8. **golden 與開關**：`tests/unit/agent/test_pipeline_golden_req.py` 設 `AGENT_WRITE_DRAFT=off`；開關讀法見 `write_forms.write_draft_enabled_from_env`、`write_lifecycle_enabled_from_env`（未設＝on）。

## 4. 路徑（單片）

### 4.1 改動

| 項目 | 改什麼 | 服務規則 |
|---|---|---|
| AP-0 | 新開關 `AGENT_WRITE_PROPOSAL`（讀法比照 `AGENT_WRITE_DRAFT`：未設或空字串＝on、`off`＝現行）。本片所有行為只在三個開關都 on 時生效。 | AP-R7（回退） |
| AP-1 | **模型自呼 → 提議**：`_run_model_loop` 遇到模型自己的 `confirm.request`（非 `wd_program`、非文件回合、無文件暫存、非點選範圍、非影子回合 `readonly_view`——影子回合維持現行，9i 不動 token 表與 `agent_state`）時：(1) 合併進草稿，**觸發語義與意圖合併相同**（安全審查 1-8）：值閘不變（`from_intent=False`）；新建草稿算 `created`；通過值閘的鍵加入 `touched` 並設 `merged`；物件名稱前置查詢命中值優先、與物件名重疊的文字值丟棄（比照 `_write_draft_merge_intent` 的 W1c 規則）；之後 `_write_draft_decide` 取用的意圖結果後合併，同欄以意圖為準。(2) **⛔ 以模型參數呼叫 `registry.call`**。(3) 呼叫 `_write_draft_decide`（取用意圖結果、合併、整句填入、跑 reissue gate）；得到程式訊息 ⇒ 以**模型這次 tool call 的 id** 執行程式的 `confirm.request`（args 整份取代 `raw_args`，含 `summary`＝`WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY`；照片、物件記憶等既有前處理照舊），結果走現行出口（出卡、缺欄追問、查無、範圍閘）；**非終結結果**（無缺欄清單的 `INVALID_INPUT`、無查無標記的 `NO_MATCH`、`DATE_BEFORE_TODAY` 等）比照 `wd_program` 區塊：記 `V_PROGRAM_NONTERMINAL`，先過 `_write_draft_reissue_not_issued_exit`（綁定卡已燒、這次沒出成新卡 ⇒ 固定句結束回合；安全審查 1-1），不成立才回填結果、交回模型。(4) 沒得到程式訊息 ⇒ 先檢查 AP-2、既有 `_write_draft_reissue_exit`／`_write_draft_submitted_exit`；都不成立 ⇒ 回模型封閉工具結果。提議的動作不在 `FORMS` 或看不到 ⇒ 封閉結果 `NO_MATCH`，不觸發。開關 on、非排除回合但 `acc.write_draft is None` ⇒ 一律封閉結果，⛔ 退回以模型參數執行（1-7）。`model_confirm_ok` 在開關 on 時不再被設。新增 violation 標記 `write_proposal`（每次提議）、`write_proposal_not_issued`（封閉結果）。<br>**實作約束**（1-2、1-6）：用本次 tool call 專屬的區域旗標標記「這是提議轉成的程式呼叫」，⛔ 設或重用 `wd_program`（它是整則 message 共用變數，設了會讓同則後續 tool_calls 跳過預算檢查與計數）；⛔ 以 `tc.id` 或其前綴判斷呼叫來源（nonce 對模型可見，`wdprog-`／`docprog-` id 模型造得出來）。模型的這次呼叫照現行計入 `tool_calls` 預算、照跑 `reserved_ids` 撞名檢查。封閉結果比照 `doc_write_face` 分支直接組 tool message `{"ok": false, "error": "HANDLED_BY_PROGRAM"}`（常數、不含草稿值），⛔ 建 `ToolResult(error="HANDLED_BY_PROGRAM")`（`ToolError` 是封閉 Literal）。 | AP-R1、AP-R2 |
| AP-2 | **卡片還在**：`_write_draft_reissue_gate` 值相同的分支，先確認綁定卡有效，四項全成立才算有效：(i) AP-3 唯讀查詢回 `live`；(ii) 以 `pending["payload"]` 重新排版 `confirm_card.render(action, payload, today=bills._today())`（**必帶 `today`**，與出卡時同一時鐘；安全審查 2-1）的雜湊＝`card_sha256`，且等於 DB 該列 `summary_sha256`（2-2）；(iii) `fields_before_today(action, payload, bills._today())` 為空（卡上日期未早於今天，否則兌現閘二必擋；2-3）；(iv) 排版拋 `ConfirmCardError`（逾期帳單延期卡跨日等）⇒ 不成立，⛔ 讓例外離開回合。有效 ⇒ 設旗標、記 violation 標記 `write_draft_card_still_valid`（V2 以它計入程式路徑），回合由新出口 `_write_draft_card_still_valid_exit` 結束：answer＝`CARD_STILL_VALID_TEXT`（「卡片還在，請按確認。」）＋換行＋卡文字；本回合意圖合併或整句填入有值被值閘丟掉時，句子改用 `CARD_UNCHANGED_TEXT`（「這次的修改沒有套用，卡片內容沒變；要送出請按確認，要改請按「我要修改」」；Q2，回合內新旗標記錄「使用者句子的值被丟」，模型提議被丟不算）；`outcome=confirm_pending`、`pending_id`＝原 pid、`quick_replies=confirm_quick_replies(原 pid)`、dialog 寫卡文字；不建 token；出卡當時的卡外提示行（未結單、`BILL_MATCH_HINT`）不重出（理由 §4.3；2-4）。(ii)～(iv) 任一不成立 ⇒ 依 AP-3 (d) 處置。檢查點與既有 `_write_draft_reissue_exit` 相同的三處（程式優先之後、模型輸出之後、AP-1 提議之後）。**Q3**：`_write_draft_reissue_gate` 的進入條件由 `had_draft and not created` 放寬為「草稿動作與綁定卡相同」；草稿是本回合新建（回合開始無草稿）時只走值相同那一支（全相同 ⇒ 本出口），有不同 ⇒ 照現行觸發（不燒、交 A7），⛔ 從卡回填草稿。 | AP-R3 |
| AP-3 | **綁定卡狀態與無效時的處置**：`tools/confirm.py` 新增唯讀查詢 `pending_token_state(db_pool, session_id, pending_id)`。**查詢約束**（安全審查 3-1、3-2）：先過 `_PENDING_ID_RE`；純 `SELECT`，以 `pending_id` **且** `session_id` 過濾；選取欄位只有 `redeemed`、剩餘秒數（`expires_at - now()`，**以 DB `now()` 判定**）、`summary_sha256`、`payload_sha256`，⛔ 選 `token`；判定順序 **`redeemed` 優先於過期**：`redeemed=true` ⇒ `redeemed`；剩餘 < 60 秒（含已過期）⇒ `expired`；否則 `live`；查無列、`_PENDING_ID_RE` 不合、`db_pool is None`、42703 與其他 DB 例外 ⇒ 一律 `missing`（fail-closed，⛔ 判 `live`）。回傳只含狀態與雜湊比對結果。**處置**：值相同但 (a) `expired`，或 (d) AP-2 (ii)～(iv) 不成立 ⇒ 比照 A2：先 `redeem_pending` 燒掉綁定卡（剩餘 < 60 秒但仍 live 的卡在這裡燒掉），燒成功 ⇒ 標 `invalidated`、設 `reissue_burned`（3-3），照常觸發程式出新卡（A7 在同一交易燒掉本 session 其他 token）；新卡沒出成 ⇒ #9b 固定句。燒不到 ⇒ 再查一次 `pending_token_state`：仍是 `expired`（`redeemed=false` 且已過期，不可能再兌現）⇒ 同「燒成功」處置；其他（含期間被兌現而變 `redeemed`）⇒ 比照 A2 的 `reissue_blocked`（3-1：已兌現優先）。(b) `redeemed`／`missing` ⇒ 沿用現行 S3「燒不到 ⇒ ⛔ 重出卡」：`reissue_blocked` 固定句。有收據、已作廢照現行。 | AP-R3、AP-R7 |
| AP-4 | **值相同改比正規化值**：`_begin_pending_confirm` 在開關 on 且**這次呼叫是程式依草稿發出（`wd_program` 或 AP-1 的區域旗標）**時，於待確認筆加存 `draft_payload`＝**這次呼叫送出的 payload** 中屬於 `to_payload(草稿)` 的鍵（⛔ 在 `_begin_pending_confirm` 讀「當下草稿」——文件暫存或模型自呼出的卡會帶上不對應的值；安全審查 4-1 (ii)）。舊筆、或讀出時形狀不合（不是 dict、值不是 `str`／`int`／`float`／`None`）⇒ 視同沒有這個鍵、沿用現行比對（比照 `WF.load_draft`「一律視為不可信」；4-1 (i)）。reissue gate 比對本回合 `touched` 鍵：`to_payload(草稿)[k] == entry["draft_payload"].get(k)`（⛔ `str()`）。`draft_payload` 只在 reissue gate 讀，⛔ 進草稿、卡或 `confirm.request`（4-1 (iii)，V8 靜態檢查）。 | AP-R4 |
| AP-5 | **過渡標記**：AP-1 (4) 封閉結果之後由模型寫回覆，屬模型主導路徑 ⇒ 註解「過渡修正、不新增 AI 決定權；寫入進行中回話由 B 片接手」。文件回合與點選範圍回合不改，註解標明「A+ 非目標；點選範圍由 A-2 接手」。 | AP-R5 |
| AP-6 | 單元測試：V1、V4、V5、V8 新增條目；既有測試中以「模型自呼出卡」為預期的，改成開關 off 的正對照或改斷言新行為，逐一列出原意圖。 | AP-R1～AP-R4、AP-R7 |
| AP-7 | **提議沒有值進草稿時由程式接住**（r3，§9）：(1) 巢狀提議解一層；(2) 提議沒有任何值進草稿時，程式以固定句（卡仍有效時為中性句＋同卡，§9.6）結束回合，⛔ 交回模型。細節見 §9.2。 | AP-R10 |

### 4.2 不做

見驗收檔第四節：文件回合與點選範圍回合、意圖抽取品質與整句填入規則、程式優先等待時限（1 秒／3 秒兩級）、模型自寫的追問或「請確認」、修繕分類值比對、對外 MCP 的 `confirm.request`。

### 4.3 偏離目標形態的取捨

- **沿用 `confirm.request` 當提議管道，不另開工具**（Q1 待裁，以下是建議理由）：使用者看到的結果只取決於「誰決定下一步」，工具名不影響使用者；改名要同時改模型提示與工具清單，會讓本片量測多一個變因、無法歸因。把模型的整套指令（寫入、更正、取消、選擇…）重新設計是 F 片的範圍（目標正本 §4 F 列）。業界 Rasa 是模型只出指令、沒有「出卡工具」；本片在語義上達到同樣的分工（模型的呼叫只是提議），名稱上沒有。
- **文件回合、點選範圍回合不收**：理由見驗收檔第四節。兩者使用量近零，且各有既有的程式先發與授權規則；這是範圍判斷，不是業界依據。
- **「卡片還在」重出同一張卡**：業主原話只說回一句話；重出卡與按鈕是第一原理推導（§2 末條），列為 AP-R3 的放寬。
- **重出時不帶出卡當時的卡外提示行**（未結單、`BILL_MATCH_HINT`；安全審查 2-4）：提示行在前一則已出示過，且不進 `card_sha256`；要重出得在待確認筆多存一份提示文字，增加一個要驗形狀的鍵。使用者看到的卡本體（兌現依據）完整。這是「現況比較好做」的取捨，照實寫。
- **模型提議的觸發語義比照意圖合併**（安全審查 1-8）：模型的呼叫既然只是提議，提議裡通過值閘的值就和意圖結果一樣算本回合的變更（`merged`、`touched`）；否則意圖沒抓到新值時提議永遠落到封閉結果，AP-4 也看不到模型改的值而誤判「卡片還在」。同欄以意圖結果為準，與程式優先路徑一致。
- **「卡片還在」的有效門檻多一個 60 秒下限**（安全審查 2-3）：剩不到 60 秒的卡，使用者按下時很可能已過期而得到「請重新確認」；改出新卡。60 秒是第一原理取的值（約一次讀卡加點擊的時間），查無業界對應。

### 4.4 文件同步（AP-R9）

| 文件 | 改什麼 |
|---|---|
| `architecture-target-20261018.md` §3 P1 列 | 「模型仍可自己呼叫 `confirm.request` 出卡」改成 A+ 後現況（模型自呼為提議；文件與點選範圍回合例外）；`PENDING_CONFIRM_MAX` 描述對碼後更新 |
| 同檔 §4 A+ 列 | 狀態改為計畫／驗收路徑；「鎖定的 M0 缺陷」改為「反覆還需要（模型自呼路徑）」——現寫「文字說請確認卻未出卡」是模型**沒有**呼叫 `confirm.request` 時自寫的文字，屬 B 片（同表 B 列已列），A+ 拿不掉 |
| `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` | `confirm.request` 流程圖、情境、假設中「模型呼叫即出卡」的敘述 |
| `.kiro/specs/agentic-mcp-orchestration/requirements.md` R4.2 | 「現行模型仍可自己呼叫 `confirm.request` 出卡」改成 A+ 後現況 |
| `.kiro/specs/agentic-mcp-orchestration/design.md` | 對碼；描述模型呼叫即出卡的現行句改正文 |
| `docs/api/mcp-facade.md` 工具表 | 對外 MCP 行為不變；描述「站內幫手模型呼叫即出卡」的正文句（若有）改正文 |
| `jgb-spec-structured-card-draft-20261019.md` §5.3 | 「等第 3 步 A 片收斂後補上」改成「C 片計畫時補上」（A 片已收案） |
| `HANDOFF-20261018.md` | §2 A+ 現況、新檔路徑 |

實作前先 grep 確認每份文件實際寫了什麼，沒寫到模型出卡的就不改。

## 5. 安全審查結論

`security-reviewer` 2026-10-19 唯讀審查（報告原文 `~/jgb-archive/arch-step3-20261018/aplus/security-review-20261019.md`）：**無 P0／P1**；3 條引入 P2，全部是計畫規格或驗收缺口，已補進本計畫與驗收檔。主會話已對碼核實三條 P2 的程式事實（`_run_model_loop` 的 `if wd_program:` 區塊、`confirm_card._render_bill_due_extend` 的 `base = max(before, today) if today else before`、`run_turn` 的 `except BaseException` 再拋、`_write_draft_merge_model_confirm` 不設 `merged`／`touched`）。

| # | 級 | 發現 | 處置 | 落點 |
|---|---|---|---|---|
| 1-1 | P2 引入 | AP-1 的非終結結果不經 `if wd_program:` 區塊 ⇒ 綁定卡已燒、新卡沒出成時交回模型（#9b 形狀） | FIX | AP-1 (3)；V8 新增 AP-1 版 9b |
| 2-1 | P2 引入 | 重排版沒帶 `today`，逾期帳單延期卡與跨日會拋 `ConfirmCardError`，整回合失敗 | FIX | AP-2 (ii)(iv)；V4 (g)(h) |
| 3-1 | P2 引入 | 「已兌現」須優先於「已過期」並以 DB `now()` 判定；F9 遺失收據時先判過期會對已寫入的卡出新卡 | FIX | AP-3 查詢約束與燒不到再查；V4 (f) |
| 1-2 | P3 引入 | id 偽造／預算：計畫寫法不開洞，但缺明文約束（⛔ 重用 `wd_program`、⛔ 以 `tc.id` 判） | FIX | AP-1 實作約束；V1 (e)(f) |
| 1-4 | P3 既有 | `enum`／`category` 值閘不比原話；§1 原寫「卡上每個值都來自使用者說過的話」不成立 | FIX（收窄宣稱） | §1 值閘範圍；V1 依欄位型別參數化；驗收檔第四節 |
| 1-8 | P3 引入 | 模型提議合併不設 `merged`／`touched` ⇒ 少觸發、AP-4 看不到模型改的值 | FIX | AP-1 (1)；§4.3；V6 歸因 |
| 2-2 | P3 加固 | 「卡片還在」宜同時比 DB `summary_sha256` | FIX | AP-2 (ii)、AP-3 查詢欄位 |
| 2-3 | P3 引入 | 判 live 到按下之間可能過期；卡上日期早於今天時兌現閘二必擋 | FIX | AP-2 (iii)、AP-3 60 秒下限；V4 (i) |
| 3-2 | P3 引入 | 查詢須雙鍵過濾、過 `_PENDING_ID_RE`、fail-closed、⛔ 選 `token` | FIX | AP-3 查詢約束；V8 9q 型與靜態檢查 |
| 3-3 | P3 引入 | (d) 只標作廢不燒、(a)(d) 未設 `reissue_burned` | FIX | AP-3 處置；V8 9aa 型 |
| 4-1 | P3 引入 | `draft_payload` 讀取驗形狀、只由程式呼叫的 payload 寫入、只在 gate 讀 | FIX | AP-4；V8 靜態檢查 |
| 1-3 | — | 每回合程式觸發上限 1 次未被繞過 | 無需處置 | V1 (d) 保留 |
| 1-5 | P4 引入 | V1(c) 斷言點未扣照片／物件記憶鍵、未驗 `summary` 常數 | FIX | V1 (c) |
| 1-6 | P4 引入 | `ToolError` 是封閉 Literal，不含 `HANDLED_BY_PROGRAM` | FIX | AP-1 實作約束 |
| 1-7 | P4 引入 | `write_draft is None` 時退路未寫 | FIX | AP-1 |
| 2-4 | P4 引入 | 重出時卡外提示行不見 | FIX（明寫不保留＋理由） | AP-2、§4.3 |
| 4-2 | P4 | 舊筆相容無問題 | 無需處置 | — |

**待查（審查員列出，不評級）**

- 單一 message 多個 tool_calls 是否在 Bedrock gpt-oss 實際發生：AP-1 約束已要求逐一計入預算、⛔ 用整則共用變數，不論是否發生都成立；V1 (f) 以假模型驗。
- S3 的原文理由只查到第 3 步計畫 §7「Q1 A2 與舊卡送出併發｜採 S3」一行：3-1 依此行與程式推得「防兩次寫入」；本計畫對過期卡的處置（燒不到再查、只在確認 `redeemed=false` 且過期時出新卡）不依賴 S3 有沒有其他目的。
- `assert_redeemed` 是以 token 查的純 SELECT、語義不同，只供實作參照寫法，不推翻 §3 差距 #5。

## 6. 執行與驗收

0. **前置與基準點**：A 片、期別片的改動仍未提交（HEAD `4bb48114`）。開工前主會話把本片會動到的檔整份複製到 `~/jgb-archive/arch-step3-20261018/aplus/baseline/`（保留相對路徑），存 `git diff HEAD -- <這些檔>` 為 `baseline.patch`、各檔 sha256；單元失敗基準＝`~/jgb-archive/arch-step3-20261018/period/c5_full_failed.txt`（30 筆）。
1. 實作交 `security-executor`，範圍限 AP-0～AP-6。
2. 主會話重建常駐容器（業主已授權本線本機容器）：`docker compose -f docker-compose.prod.yml -f docker-compose.bedrock-local.yml up -d --build rag-orchestrator`；記重建時間（V2 起點）。
3. 每次會呼叫 JGB 前跑 mock 檢查，必須印 `True`（V0）。
4. 依序：V1、V4、V5、V8、V9 的單元與靜態部分 → V3 實打 → V6 重放 → V9 E2a → V7 E2b 32 場 → V2 統計 → V10、V11。
5. 文件同步（§4.4），再 fresh `verifier`（V12）。

## 7. 回復、停點、用量

- **回復**：先設 `AGENT_WRITE_PROPOSAL=off` 重建（行為回到改前）；要撤掉程式時用 `aplus/baseline/` 蓋回並核對 sha256，本片新增的測試檔直接刪除，再重建。⛔ `git checkout HEAD`（會抹掉 A 片、期別片未提交的改動）。
- **停點**：安全審查或 verifier 回報 P0／P1；V3 任一案未通過且原因在本片；V7 Intercom 低於 28/32 且有場次的未解決原因在本片改動。發生時暫停回報業主。
- **用量**：收尾回報子代理 token 加總與模型 API 呼叫次數。

## 8. 業主裁示（2026-10-19）

業主答覆：核可＝「核可 (Recommended)」；Q1＝「沿用 confirm.request (Recommended)」；Q2＝「改說沒套用 (Recommended)」；Q3＝「也回卡片還在 (Recommended)」。即下列三題皆採 (a)；規則檔 AP-R2、AP-R3 已寫入裁示，V4 (l)(m) 為對應驗收。核可同時同意目標正本 §4 A+ 缺陷欄改為「反覆還需要（模型自呼路徑）」。

原題：

- **Q1（AP-R2 讀法）**「模型改為提出寫入意圖」：(a) 沿用 `confirm.request`，語義改為提議（建議，理由 §4.3）；(b) 另開一支提議工具、把 `confirm.request` 對模型隱藏（要改模型提示與工具清單，量測多一個變因）。
- **Q2（AP-R3 讀法）**本回合使用者給了新值、但被值閘丟掉（例：W-R2_k1 的分類「設備類」對不到分類樹），草稿值因此與卡相同：(a) 改回「這次的修改沒有套用，卡片內容沒變；要送出請按確認，要改請按「我要修改」」＋同一張卡（建議：照原話回「卡片還在」會讓使用者以為改成功了）；(b) 照原話回「卡片還在，請按確認」。分類對不到本身仍歸 A-2。
- **Q3（AP-R3 前提）**原話「卡片有效、值又相同時」沒有限定草稿還在。草稿閒置兩回合會被清掉，但卡仍在 600 秒效期內；這時使用者只重述部分同值，現行會由程式追問「還需要…」（與原話 2 的問題同形）。(a) 草稿已清、本回合新建草稿時，也比對綁定卡的 `draft_payload`：本回合寫進的值全相同 ⇒ 回「卡片還在」＋同一張卡（建議，依使用者效果：不再出現原話 2 的誤問）；限制：⛔ 從卡回填草稿（安全審查 4-1 (iii)、第 3 步 9e），之後若再改值，草稿只有本回合給的欄位，會依草稿追問缺欄。(b) 只在草稿還在時適用，草稿已清照現行（工作較少；查無這種情形的發生次數）。選 (a) 時 V4 加一案：草稿已清＋部分同值 ⇒ 「卡片還在」、無新 token；選 (b) 時此情形列入驗收檔第四節非目標。

## 9. r3：提議沒有值進草稿時由程式接住（AP-7）

### 9.1 停點與量到的機制

r2 實作後（容器 2026-10-19 22:23:57 重建），E2b 32 場模擬客人自報解決 27/32（未盲判），低於基線 28/32，其中 C-M_k1、C-M_k2 的未解決原因含本片改動 ⇒ §7 停點成立，暫停回報業主。歸因原文：`~/jgb-archive/arch-step3-20261018/aplus/e2b/e2b_attribution_prelim.md`。

C-M 情境：出卡 → 按「修改」→ 使用者說「問題描述改成：X」。重放（`aplus/e2b/diag/drive_cm*.py`；意圖與主呼叫原始輸出取自診斷容器 `w2-diag` 的 shim 紀錄 `w2/run2/calls.jsonl`，依時間窗對）：

| 程式 | 意圖有抽出描述 | 意圖回 `action:none` 時 |
|---|---|---|
| r2 前（`w2-diag` 基準三檔，10 次） | 6/6 出卡 | 4 次：模型自呼 `confirm.request` 3 次 ⇒ 以模型參數算缺欄「還需要：問題描述」（誤問，但客人再講一次可接回）；模型自寫文字 1 次 |
| r2（`w2-diag` 暫換 A+ 三檔，8 次） | 4/4 出卡 | 4 次：模型自呼 1 次 ⇒ 提議 0 鍵合併 ⇒ 封閉結果 ⇒ 模型轉人；模型未呼叫工具、自寫「請確認」假卡文字 3 次 |

- 模型提議的 payload 是巢狀形狀（trace `794875d1`）：`{"action":"repair_create","payload":{"estate_name":"就是豪宅啦","description":"臥室冷氣滴水"}}`。`_write_proposal_merge` 只讀頂層鍵（`action`、`payload` 都不是表單欄位）⇒ 0 鍵合併 ⇒ `created`／`merged` 皆不成立 ⇒ `_write_draft_decide` 回 `None` ⇒ 封閉結果 `HANDLED_BY_PROGRAM` ⇒ 模型自寫回覆。
- E2b 的 C-M_k1（trace `b3eaa1b2`）、C-M_k2（`3cfb38dc`）標記序列與 `794875d1` 相同（`write_proposal` → `write_draft_action` → `write_draft_keys` → `write_proposal_not_issued`），模型隨後寫「請在確認卡上點擊送出」但沒有卡。常駐容器不記模型參數，這兩場是否同為巢狀形狀屬**推論**（標記序列相同），未取得原文。
- 根因在意圖層（理解層，非本片目標）；本片的影響是把 r2 前可接回的誤問變成死路。

### 9.2 改動（AP-7）

只在 A+ 生效（三個開關皆 on）且屬 AP-1 提議分支的回合；開關 off、`confirm.request` 工具本身、對外 MCP、`_payload_of` 的其他呼叫點都不變。

1. **巢狀提議解一層**：`_write_proposal_merge` 取得的 payload `P`，若除 `action` 外沒有任何 `form.keys` 內的鍵（含系統來源鍵；外層帶任何表單鍵就不解），且 `P["payload"]` 是 dict、或是能解析成 dict 的 JSON 字串 ⇒ 以該內層 dict 的表單鍵合併；內層**有 `action` 鍵**（不論值）且值不等於 `P["action"]`（含 `None`、`""`、非字串）⇒ 視同動作不合（封閉結果 `NO_MATCH`、不觸發）。只解一層（內層再有 `payload` 不再解）。合併規則（值閘、W1c 名稱規則、`touched`／`merged`、Q2 不設 `user_value_dropped`）與 AP-1 (1) 相同。新增 violation 標記 `write_proposal_unwrapped`。**實作約束**（安全審查 r3 F1、F3、F5-8）：解開與內層動作比對都在 `wd.activity = True` 與 `_write_draft_target` **之前**完成（動作不合 ⇒ 草稿、`created` 都不變）；內層 JSON 字串解析接 `TypeError`、`ValueError`、`RecursionError`，失敗 ⇒ 視同不解開；解開邏輯只在 `_write_proposal_merge` 內，⛔ 改 `_payload_of`。
2. **提議沒有值進草稿 ⇒ 程式結束回合**：`_write_proposal_handle` 在 `_write_draft_decide` 回 `None`、既有三個出口（綁定卡燒不到、卡片還在、修改已送出）都不成立之後，若同時成立：草稿存在且動作＝提議動作；本回合 `created`、`merged`、`caught`、`filled` 皆不成立；非凍結回合（`frozen`）；本回合程式尚未觸發（`triggered`）⇒ 不回模型封閉結果，改由程式結束回合：
   - (a) 有同動作綁定卡、未作廢、無收據，`to_payload(草稿)` 與該卡 `draft_payload` 全部鍵相等（安全審查 r3 F7：草稿已改成新值而卡仍是舊值時不走 (a)），且 AP-2 的有效四項成立（AP-3 唯讀查詢帶 `card_sha256`、`payload_sha256` 判 `live`＋重排版雜湊相符＋卡上日期未早於今天＋排版不拋例外）⇒ 新固定句 `PROPOSAL_NO_VALUE_CARD_TEXT`「這句沒有讀到要修改的內容，卡片內容沒變；要送出請按確認，要改請按「我要修改」或直接說要改哪一項、改成什麼。」（業主 2026-10-19 裁示，§9.6；⛔ 用 `CARD_UNCHANGED_TEXT`／`CARD_STILL_VALID_TEXT`）＋換行＋同一張卡、同一個 `pending_id` 的三顆鍵、`confirm_pending`、⛔ 新 token。標記 `write_proposal_no_value_card`，並同記 `write_draft_card_still_valid`（V2 以它計入程式重出同卡；安全審查 r3 F4，凍結的 V2 不改）。**實作約束**（r3 F2）：(a)(b) 只用唯讀的 `pending_token_state` 與 `_write_draft_bound_card_text`；⛔ 呼叫 `_write_draft_same_values`、`redeem_pending`；⛔ 改待確認筆（含 `invalidated`）；⛔ 設 `reissue_blocked`、`reissue_burned`、`card_still_valid`；出口另寫，⛔ 重用 `_write_draft_card_still_valid_exit` 的開頭句判斷。
   - (b) 其他 ⇒ 新固定句 `PROPOSAL_NO_VALUE_TEXT`：「這句我沒有讀到要填寫或修改的內容，目前沒有更新。可以填寫或修改的有：{labels}。請直接說哪一項、內容是什麼，我再幫您整理成確認卡。」`{labels}` 依 `edit_ask_text` 的同一規則取自表單宣告（草稿 `to_payload` 有值的 `user_words` 欄位；都沒有 ⇒ 該表單全部 `user_words` 欄位；⛔ 放使用者值；無標籤 ⇒ 去掉中間那句的固定句）。`outcome=clarifying`、`expects=text`、`action`＝草稿動作；⛔ 出卡、⛔ 建或燒 token、⛔ 呼叫模型寫回覆。新增標記 `write_proposal_no_value`。
   - 其餘封閉結果情形（期限不足、看不到、點選範圍、`reissue_held`、同回合第二次提議等）照 AP-1 (4) 不變。
3. **測試**：見驗收檔 V13；r2 已有的 V1 (d)（同回合第二次提議 ⇒ 封閉結果）、(g)（`write_draft is None` ⇒ 封閉結果）維持。

### 9.3 取捨

- **(1) 是容忍模型輸出格式的修補，不是根本解**：根本解是讓模型的工具參數照 schema 產生（工具參數嚴格化或改由意圖層出指令），屬 F 片（目標正本 §4 F 列）。本片只解一層、內層一樣過值閘，模型送巢狀不會多拿到任何寫入能力；不解的話，每次模型送巢狀，提議都會白白落空。依據：第一原理，查無業界對應。
- **(2) 只接住「模型有呼叫 `confirm.request`」的情形**：模型沒呼叫工具、自己寫「請確認」文字的情形（r2 重放 3/8）屬 B 片（驗收檔第四節），本片拿不掉。
- **(2)(b) 不重出舊卡**：C-M 情境的舊卡已因「修改」作廢；重出舊值的卡會讓使用者以為改成功。卡還有效時走 (a)，句子依業主裁示（§9.6）用中性句：不宣稱有修改嘗試（「再出一次確認卡」的使用者沒要改），也不說「卡片還在」（想改卻沒被讀到的使用者會以為改好而送出舊值，W-R3 實測出現過）；附同一張卡是因為 JGB 只有最後一則可互動。
- **預期**：C-M 的意圖 `none` 回合中，模型有呼叫工具的那部分改為出卡（巢狀可解）或程式固定句（可接回）；模型自寫文字的那部分不變。E2b 預期 27～30/32，不保證回到 28。

### 9.4 r3 安全審查（2026-10-19，`security-reviewer` 唯讀）

無 P0／P1；報告存 `~/jgb-archive/arch-step3-20261018/aplus/security-review-r3-20261019.md`。主會話已對碼核實 F1（`_write_proposal_merge` 在逐鍵合併前即呼叫 `_write_draft_target`）、F2（`_write_draft_same_values` 會燒卡與設旗標）、F4（V2 只認兩個標記）。

| # | 級 | 發現 | 處置 | 落點 |
|---|---|---|---|---|
| F1 | P3 引入 | 內層動作不合須在任何草稿變動前判定，否則換掉舊草稿並在模型輸出後觸發 | FIX | §9.2 (1) 實作約束；V13 (c) |
| F2 | P3 引入 | (a)(b) 若重用 `_write_draft_same_values`／`_write_draft_card_still_valid_exit` 會燒卡或說錯句 | FIX | §9.2 (2) 實作約束；V13 (i)(h) |
| F4 | P3 引入 | V2 會把 (a) 的回合算成模型路徑出卡 | FIX（(a) 同記 `write_draft_card_still_valid`，凍結 V2 不改） | §9.2 (2)(a) |
| F3 | P4 既有＋1 處 | 深層巢狀 `json.loads` 拋 `RecursionError` 未被接住 | FIX（新解析點接住；既有兩處不改，列待辦） | §9.2 (1)；V13 (l) |
| F5 | P4 引入 | V13 缺條目 | FIX | V13 (c)(h)(i)(l)～(o) |
| F6 | P4 引入 | 「屬於該表單的鍵」兩種讀法 | FIX（`form.keys`） | §9.2 (1) |
| F7 | P4 既有 | (a) 不檢查草稿＝卡 | FIX | §9.2 (2)(a) |

**待查**（審查員列出，不評級）：模型在非寫入回合送不帶值的提議時，AP-7 會以固定句結束回合、使用者的問題沒人答。查證（`aplus/q_notissued.py`，唯讀，重建後至今）：帶 `write_proposal` 的回合 22 次，其中 `write_proposal_not_issued` 7 次，7 次的使用者句子都在寫入流程內（C-M 改描述、「再出一次確認卡」「把確認卡內容再貼給我」）；0 次是非寫入問題。樣本只涵蓋本片 E2a／E2b／重放，V7 重跑後再查一次，若出現非寫入句即回報業主。

### 9.6 業主裁示（2026-10-19，r3 plan-verifier REVISE 後）

plan-verifier 第 1 輪 REVISE：(2)(a) 原寫 `CARD_UNCHANGED_TEXT`＋同卡，是計畫自選的讀法（Q2 只裁「使用者給了新值但被值閘丟掉」），且 §9.4 待查的實際句子「再出一次確認卡」並非要修改。改為問業主。題目：「模型送了提議、但沒有任何值寫進草稿，而且確認卡還有效（草稿和卡一樣）時，程式要回什麼？」業主選「中性句＋同一張卡 (Recommended)」（選項說明：回「這句沒有讀到要修改的內容，卡片內容沒變；要送出請按確認，要改請按「我要修改」或直接說要改哪一項、改成什麼。」，下面附同一張卡和三顆按鈕，不建新 token）。其他選項：照原話只問要改成什麼（不附卡）、「卡片還在」＋同卡、「沒套用」＋同卡。

收尾審查（新的 plan-verifier）：上輪 blocker 已解；剩 1 條 `Kind: wording-only`——AP-R10 對凍結回合、已觸發回合的排除沒標「收窄」與理由。已在 AP-R10 讀法欄與驗收檔第四節補上（條件與 V13 (j) 不變）。**已修，未再審**。另記 P3 建議：(2)(a) 只有 V13 (A) 單元測試能強制走到，/mcp 層要靠模型送無值提議才會出現；V7 重跑後依 §9.4 再查一次。

### 9.5 執行（r3 核可後）

1. 交 `security-executor`，範圍限 AP-7（含 V13 單元條目）。
2. 單元與靜態：V13，連同 V1、V4、V5、V8 全部重跑；agent 單元測試與基線 30 筆比對。
3. 重建常駐容器、mock 檢查 → V13 重放 → V3 實打 → V9 E2a → V7 E2b 32 場重跑（盲判）→ V2 → V10、V11 → fresh `verifier`（V12）。
4. `w2-diag` 只用來取模型原始輸出；換檔診斷後一律還原基準三檔並核對 sha256。
