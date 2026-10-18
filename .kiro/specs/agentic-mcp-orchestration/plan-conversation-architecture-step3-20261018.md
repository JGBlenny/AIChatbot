# 計畫：對話整體架構——寫入全程由程式持有、回話與狀態一致、確認卡結構化（主線第 3 步，2026-10-18 r1 草稿）

> 狀態：**業主 2026-10-18 核可（r5，fixed, not re-reviewed）**，規則與驗收清單凍結；執行模式 AUTO（沿用本工作線）。r5 修正（A8、R1 檢查句、#2）未經獨立審查，由實作後 verifier 實跑 #2 涵蓋。
> 驗收清單（草稿，核可時凍結）：`acceptance-conversation-architecture-step3-20261018.md`
> 依據量測：`report-two-layer-eval-step2-20261018.md`（第 2 步報告）。

## 1. 目標（業主原話）

- 「需通用方式修改 而非 特規補丁」「像整體邏輯應該 有一個整體脈絡 而不是一個一個調整吧」（本 session）。
- 「像是確認卡 應該是此系統出格式 接的系統呈現吧」「要調整吧 ?」（本 session）。
- 「目前要該是要把本地替換 oss 並確保 回應品質都能符合 有效的回應 並把某些部分邏輯參考業界做法去調整」（HANDOFF-20261018 §1.1）。
- 承接 DSP-085（業主 2026-10-17：「修繕 不能延續處理了嗎」「但是需要通用處理 不能局部補丁」，選「程式掌握流程」）：W1／W1b／W1c 已讓「收欄位 → 出卡」由程式掌握（commit `f117be32`）；本計畫把同一原則延伸到**出卡之後**（改、挑、送出、取消、收據）與**回話層**。

### 1.1 規則（由上列原話整理；原話只當出處，判定一律依本節，業主核可時一併凍結）

| 規則 | 內容（可檢查） | 出處 |
|---|---|---|
| R1 不分動作寫死 | 修法只放在全部寫入動作共用的流程層（草稿、確認、更正、候選、回話）；⛔ 以動作名、欄位名、題目用字、詞表做條件分支。檢查：新增一個假動作，只加動作專屬登錄——`write_forms.FORMS` 一項（含 A6 預檢宣告時，宣告在 `WriteForm` 上）、`confirm_card.CONFIRM_ACTIONS` 一項、`confirm_card._RENDERERS` 一項、所需的 `confirm_card.CONFIRM_FIELD_ATTRS`、測試自建的工具登錄表上註冊一支假的 `jgb2.action.<假動作>`（假執行器）——由測試自身註冊或 patch 加入；⛔ patch 或修改流程程式（`runtime.py`、`tools/confirm.py`、`confirm_card.render()` 的共用部分）；流程層一律在呼叫當下讀 `confirm_card.CONFIRM_ACTIONS` 這一份（A8），因此上列登錄即足以走完「收欄位→出卡（`confirm_request`→`_begin_pending_confirm`）→更正→送出（`_run_confirm_segment`→`registry.call`）／取消」。**讀法註記（業主 2026-10-18 裁定）**：動作專屬登錄（表單、卡片排版、送出規格）屬動作資料，不算流程程式 | 「需通用方式修改 而非 特規補丁」、DSP-085「不能局部補丁」 |
| R2 不只改提示詞 | 每項修法必須是程式行為改變；只改提示詞或樣板措辭不算修好 | DSP-085（⛔ 只加提示詞）、「而非 特規補丁」 |
| R3 一個脈絡 | 每項修法必須掛在三條原則之一：P1 寫入全程（建立到送出／取消）由程式持有；P2 說出口的狀態（確認、完成、請按確認）只由程式依實際狀態產生；P3 給模型的資料與給人看的呈現分開。掛不上的不做。**讀法註記（放大）**：「三條原則即整體脈絡」與「掛不上的不做」是本計畫的推導，依據第 2 步報告 §4 缺陷表的歸類與 §2.1、§2.7；原話只說應有一個整體脈絡 | 「像整體邏輯應該 有一個整體脈絡 而不是一個一個調整吧」 |
| R4 卡由本系統出結構、接入方呈現 | 本系統回傳確認卡的結構化資料（欄位、動作）；外觀由接入方決定；文字版只當備援。**讀法註記**：把問句「要調整吧 ?」讀成「要做」（本片只列 C 概要、不實作）；「文字版只當備援」是放大，依據 §2.6（MCP「SHOULD also return the serialized JSON in a TextContent block」、Adaptive Cards fallbackText） | 「像是確認卡 應該是此系統出格式 接的系統呈現吧」「要調整吧 ?」 |
| R5 有效回應以實測判 | 以第 2 步同一量尺（模擬客人多輪＋程式前判＋盲判）在本機常駐服務量；不以單元測試或人工看幾句代替 | HANDOFF §1.1「確保 回應品質都能符合 有效的回應」 |
| R6 先確認 mock | 每次會呼叫 JGB 的測試（實打、E2a、E2b、整合）執行前，HANDOFF §2.3 mock 檢查輸出 `True`；不是 `True` 就不跑 | 原始要求「任何會呼叫 JGB 的測試前，先照 §2.3 確認本機是 mock」 |
| R7 參考業界做法 | A 片每項做法標出所依的 §2 目標形態段落；查無業界對應者寫明第一原理推導與「查無業界對應」。**讀法註記**：「某些部分」讀為本計畫改動的部分 | HANDOFF §1.1「並把某些部分邏輯參考業界做法去調整」 |
| R8 不弱化寫入授權 | 任何改動後，確認 token 綁定（`pending_id`＋`session_id`＋未兌現＋未過期）、範圍閘、可見性檢查不得放寬；同 session 可兌現卡 ≤ 1；開關關閉時安全強化仍在。**出處註記**：非本次業主原話，是本計畫加的約束，來自全域安全路由（寫入授權屬 security-sensitive）與 §7 security-reviewer F1～F9、安全複核；業主核可時一併確認 | 非業主原話（見出處註記） |

原話對照（每句原話對到規則或非目標）：「需通用方式修改 而非 特規補丁」→ R1、R2；「像整體邏輯應該 有一個整體脈絡…」→ R3；「像是確認卡…」「要調整吧 ?」→ R4（本片非目標：C）；「確保 回應品質都能符合 有效的回應」→ R5（不設門檻為非目標，DSP-087）；「任何會呼叫 JGB 的測試前…」→ R6；「並把某些部分邏輯參考業界做法去調整」→ R7；「把本地替換 oss」→ 非目標：已於第 1 步 commit `2892a183` 完成，本片在同一 gpt-oss 接線上量測、不改模型接線；DSP-085「不能局部補丁」「程式掌握流程」→ R1、R2；原始要求「照 §2.4 開始寫主線第 1 步…的計畫」→ 非目標：第 1 步已完成（`2892a183`），本計畫為主線第 3 步；「交我核可後才實作」→ 核可閘：本計畫狀態行「核可前 ⛔ 動程式」，A 片程式改動只在業主核可後開始。

業主裁定（2026-10-18 核可時）：R3 讀法「對，照這樣」；R4 讀法「對，要做且留文字備援」；R8「納入」；R1 讀法見 R1 註記。以上規則自此凍結，後續驗收、verifier、挑戰者一律依本節判定。

成功＝客人在多輪對話中更正、挑選、反悔都不必重來，系統說出口的確認／完成與實際狀態一致，確認卡由接入方以結構化資料呈現。A 片只負責其中「更正、卡與寫入一致」（報告 §4「改欄位」「卡與寫入不一致」）；「候選選擇」歸 A-2；「確認／完成話術」「內部提示外露」歸 B；結構化卡歸 C；「知識不捏造／完整」歸 D；「首句資訊」「物件名」根因未查，由 A0 一併查明後再指派（見 A0）。

## 2. 目標形態（業界做法，先於現況）

原文皆以 web-drive 渲染存檔（`~/jgb-archive/devflow-20261018/sources-repair/`、`sources-card/`，每檔首行為網址與擷取時間 2026-10-18），以下逐字引用、檔名可 grep。

### 2.1 理解與執行分離：模型把話轉成指令，流程由程式決定性執行

- Rasa（`rasa-dialogue-understanding.txt`，https://rasa.com/docs/learn/concepts/dialogue-understanding/）：「the dialogue understanding component interprets the input and generates a list of commands that represent how the user wants to progress the conversation.」指令表含「The user has provided an updated value for a slot」（correct slot）、「The user does not want to continue with the current flow」（cancel flow）。
- Rasa CALM（`rasa-business-logic.txt`，https://rasa.com/docs/learn/concepts/calm/）：「Deterministic execution: Follows structured workflows for reliable, debuggable interactions.」「ensuring the assistant follows predefined logic without guessing or inventing the next steps on the fly」。

### 2.2 更正是一級機制，含確認之後

- Google 對話設計（`gcd-help.txt`，https://developers.google.com/assistant/conversation-design/confirmations；頁面標示 Conversational Actions 已於 2023-06-13 停用，屬舊版設計指南）：「Expect users to make corrections, after explicit and implicit confirmations」「Disambiguate what users want to correct and ask for the new information.」反例：「Don’t cancel and force users to start the dialog over」。
- Amazon Lex V2（`lex-reelicit.txt`，https://docs.aws.amazon.com/lexv2/latest/dg/reelicit-slots.html）：「you may want to re-elicit a slot after your customer declines a confirmation」。
- Rasa（`rasa-patterns.txt`，https://rasa.com/docs/reference/primitives/patterns/）：「Patterns implement Conversation Repair」；預設 `pattern_correction` 走 `action_correct_flow_slot`；可改為「require a confirmation from the user before a slot is updated」。

### 2.3 不可逆動作前確認；確認綁定那一次的參數；送出前驗證

- Google（`gcd-help.txt`）：「Double-check with the user prior to performing an action that would be difficult to undo」。
- OpenAI Agents SDK（`openai-hitl.txt`，https://openai.github.io/openai-agents-python/human_in_the_loop/）：「Per-call approvals are scoped to the specific call ID」。
- Lex（`lex-confirmation.txt`，https://docs.aws.amazon.com/lexv2/latest/dg/intent-confirm.html）：「You can define a Lambda code hook to validate the intent before you send it for fulfillment.」
- Rasa（`rasa-flow-steps.txt`，https://rasa.com/docs/reference/primitives/flow-steps/）：「When validation fails, your assistant will automatically try to collect the information again.」

### 2.4 候選值由程式從資料取出、讓使用者挑

- Rasa（`rasa-flow-steps.txt`）：`action_ask_{slot_name}`「useful if you … want to display available values for the slot fetched from a database as buttons」（原句以 `want to display available values for the slot fetched from a database as buttons` 可 grep）。
- Microsoft Copilot Studio（`ms-entities-slot.txt`，https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-entities-slot-filling）：「prompts the user to be more specific by providing choices」。
- **查無業界對應**：「以金額／期別／編號打字挑選某一筆項目、再回原流程」——上列各家只到「選哪個流程／意圖」層級，項目層級查無專節（渲染代理已查 Rasa、Dialogflow CX、Lex、Copilot Studio，見 `sources-repair` 報告 F 節）。本計畫此項以第一原理推導：候選清單是程式剛給出的有限集合，使用者的指稱可對集合屬性做決定性比對，唯一命中即等同按鈕。

### 2.5 中斷與回到原流程

- Microsoft（`ms-topic-switch.txt`，https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-topic-management）：「it resumes in the originating topic by default」。

### 2.6 確認卡：系統給結構化內容，接入方呈現，附文字備援

- MCP 規格（`mcp-tools-latest.txt`，https://modelcontextprotocol.io/specification/latest/server/tools）：「Structured content is returned as a JSON value in the structuredContent field of a result.」「For backwards compatibility, a tool that returns structured content SHOULD also return the serialized JSON in a TextContent block.」
- Microsoft Adaptive Cards（`ms-adaptive-cards-overview.txt`，https://learn.microsoft.com/en-us/adaptive-cards/）：「Card Authors own the content, Host App owns the look and feel」；`adaptive-cards-schema-AdaptiveCard.txt`：fallbackText「The text that should be displayed if the client is not able to render the card.」
- Rasa（`rasa-responses.txt`）：「it is up to the implementation of the output channel how to display the defined buttons」。
- Zendesk（`zendesk-structured-messages-real.txt`）：「Zendesk has built in fallback behaviours that attempt to communicate the intent of the action in the best way possible.」
- Slack（`slack-chat-postMessage.txt`）：`text`「this is used as a fallback string to display in notifications」。
- 查無：Intercom、Botpress 的「不支援時降級成文字」原句（未查完）。

### 2.7 第一原理（查無業界逐字對應）

- **說出口的狀態必須等於程式狀態**：「已確認」「已完成」「請按確認」只能由程式依狀態產生。查無逐字原文；由 2.1「business logic 不由模型猜」推導；Lex 以 `confirmationState` 狀態欄位表達確認（`lex-lambda-common.txt`），文件未寫明誰設定。
- **給模型的資料與給人看的文字分開**：查無逐字原文；推導自 2.6「內容（資料）與呈現分離」。

## 3. 差距（現況，已對碼；可重跑）

| # | 目標形態 | 現況 | 查證 |
|---|---|---|---|
| G1 | 草稿保留到送出／取消（2.2） | 出卡成功即清草稿 | `grep -n "W1（§2.1(3) 清除條件）：出卡成功" rag-orchestrator/services/agent/runtime.py`（下一行 `session.clear_write_draft()`） |
| G2 | 卡後可更正（2.2） | 「修改」按鈕與取消同一路：非 submit 一律燒 token 回 `CANCELLED_TEXT` | `grep -n "submit = verb == CONFIRM_QUICK_REPLY_VALUES\[0\]" rag-orchestrator/services/agent/runtime.py`；註解「修改／取消：**一律先燒 token**」 |
| G3 | 更正指令（2.1 correct slot） | 無「改欄位」指令；卡後更正的句子沒有草稿可改，進一般模型回合，常退回「還需要：問題描述」（`MISSING_FIELDS_ASK_TEMPLATE`） | `grep -rn "MISSING_FIELDS_ASK_TEMPLATE" rag-orchestrator/services/agent/tools/confirm.py`；正對照：草稿內覆寫路徑 `_write_draft_merge_intent` 存在 |
| G4 | 值的語意清楚 | 意圖說明對 enum 只列代碼「只能填 1／2」，不列 1＝非緊急、2＝緊急 | `grep -n "只能填" rag-orchestrator/services/agent/write_forms.py`（`write_intent_description`）；值域 `_EMERGENCY_ZH` |
| G5 | 程式給候選、使用者可挑（2.4） | 只有按鈕機器值 `select:<type>:<id>` fullmatch；打字指稱（金額、期別、編號）無程式路徑 | `grep -n "_SELECT_VALUE_RE = re.compile\|def _parse_select_value" rag-orchestrator/services/agent/runtime.py` |
| G6 | 送出前驗證（2.3） | 延期卡以 `max(before, today)+days` 起算；W-D1 卡上新到期日 2026/10/21，按確認兩次回 `ACTION_FAILED_TEXT`；同為過期帳單 W-D3 成功——**根因未查** | `grep -n "max(before, today)" rag-orchestrator/services/agent/tools/confirm.py rag-orchestrator/services/agent/confirm_card.py`（工具與卡兩處同式）；`grep -n "ACTION_FAILED_TEXT: Final" rag-orchestrator/services/agent/confirm_card.py` |
| G7 | 狀態話術只由程式產生（2.7） | 出口閘與 Verifier 無「answer 宣稱完成／像卡但 state 不符」檢查；模型可自寫假卡（W-R4 k2 `state=answered`） | `grep -c "confirm_pending" rag-orchestrator/services/agent/exit_gates.py rag-orchestrator/services/agent/verifier.py rag-orchestrator/services/agent/runtime.py`＝0／0／2（主會話 2026-10-18 實跑；runtime 為正對照） |
| G8 | 給模型與給人分開（2.7） | 候選清單把給模型的提示（`⛔ 不是使用者指定編號的資料`、`請以 ref 指定該編號再查一次`）直接接進使用者回答 | `grep -n "不是使用者指定編號的資料\|請以 ref 指定該編號再查一次" rag-orchestrator/services/agent/tools/jgb2.py`；`grep -n "CONFIRM_CANDIDATES_TEXT + " rag-orchestrator/services/agent/runtime.py` |
| G9 | 結構化卡＋文字備援（2.6） | `/mcp` 回傳七鍵（answer、kind、handoff、quick_replies、trace_id、session_expired、outcome），卡只以排好的文字放 `answer`；JGB preview `AgentTurnClient.php` 白名單只轉六鍵、`ConfirmCard.vue` 以 `pre-line` 呈現 `answer` | `grep -n "class AgentTurnOutput" rag-orchestrator/services/agent/mcp_facade.py`；JGB：`git -C ~/dev/work/jgb2/dev1 show origin/preview:app/Services/Assistant/AgentTurnClient.php` |

既有決議相容性（`.claude/DECISIONS.md` 全檔已由 scout 讀過；無決議以字面否決「改欄位指令」「結構化卡」「狀態機」）：
- DSP-038（卡文字由程式 formatter 決定性產出、逐字成為 answer、⛔ 經模型／Verifier）——本計畫保留；結構化卡＝同一 formatter 另出資料形狀，文字仍逐字為 answer（備援）。
- DSP-042（`select:` 服務端 fullmatch 攔截；⛔ `select:` 進模型抽 id）——G5 打字挑選不改按鈕路徑，新增路徑由程式比對、不讓模型抽 id。
- DSP-043（`outcome` 由 Runtime 程式設、不由模型判）——G7 延伸同一原則到答案文字。
- DSP-085（程式掌握流程；⛔ 只加提示詞）——本計畫延伸。
- R4.2（`confirm_edit` 只見機器值名稱，語意未定義）——G2 定義語意，需記一條 DECISION。

## 4. 路徑（分片；每項對回 §1 目標或實際事件）

程式（envelope）：A 寫入全程由程式持有 → B 回話與狀態一致 → C 結構化確認卡（跨元件）→ D 知識不捏造（目標形態未渲染，本計畫不展開）。M 量尺修正先行（repo 外）。
本計畫只有 **M＋A** 可執行；B、C 待 A 驗收後各自出片計畫；D 另起計畫。

### M（量尺修正，repo 外 eval-harness；先於 A 的重測）

終點指標預期變化：**0**（M 不改受測系統），是 A 片（預期變化為正）的前置：量尺修正後先在**現行容器（commit `2892a183`，不需重建）**重跑一次第 2 步第二層，得到「M 後基線」，A 的改善才可歸因。

| 項 | 對應事件 |
|---|---|
| M1 修繕真值加「急迫程度」；角色指令改為核對卡上全部欄位 | 第 2 步報告 §3 缺陷 1、W-R2 k1 任務規格錯誤 |
| M2 判分對話稿印出 `no_button` | 報告 §3 缺陷 4 |
| M3 每場前重置 mock 記憶體狀態（或每場改用未被寫過的帳單）；查重置方式時 ⛔ 重啟容器（重啟歸業主） | 報告 §3 缺陷 2 |
| M4 延期題 W-D1、W-D2、W-D3、W-D5（真值帳單皆早於量測日）改用未過期帳單；W-D4 不動；另設「過期帳單」專題（期望：出卡前就說明做不到或給可行日） | 報告 §3 缺陷 3、W-D1／W-D2／W-D5 |
| M5 新增更正專題，分組：**歸 A**——卡後改欄位（每個寫入動作至少一題，A2）、按「修改」（A3）；**歸 A-2**——打字挑候選（金額／期別／編號），A 後只記錄現況；**只記錄現況**——中途問別的再回來（2.5；A1 保留草稿是必要不充分條件，回原流程的引導未列入 A，A 後只記錄） | §4 缺陷表「改欄位」「候選選擇」；2.2、2.4、2.5 |

### A（第一片：寫入全程由程式持有；DSP-085 延伸）

| 項 | 做什麼（通用，不分動作） | 對應事件／原則（§1.1） |
|---|---|---|
| A0 | 執行第 0 步：查 G6 W-D1 送出失敗根因（線索：兌現端 `bill_due_extend` 以 `get_bills(viewer_user_id=…)` 讀可見清單、mock 有分頁 `per_page`／`DEFAULT_PER_PAGE`，帳單不在第一頁即 `_no_match`——待證），先報告再定 A6；另查「首句資訊」（W-R4 k2：首句已給物件仍追問）與「物件名」（W-R3「就是豪宅啦」被截成「豪宅」）根因——根因落在 A1～A7 同一層才併入，否則回報後另出片（不列入 A 驗收） | W-D1 k1／k2；W-R4 k2；W-R3 k1／k2 |
| A1 | 草稿生命週期改為「建立 → 出卡（保留）→ 送出／取消／逾時才清」；pending 與草稿綁同一 action；任何 receipt 寫入即清草稿；確認待決期間，使用者每個不屬寫入相關意圖的文字回合 `idle_turns` 照常累加，達 `DRAFT_IDLE_LIMIT` 即清草稿（草稿含個資，⛔ 留到 session 關閉）；按鈕回合不計 idle（送出、取消即清；「修改」把 `idle_turns` 歸 0）；idle 清草稿只清草稿，綁定的卡依既有到期規則（不新增行為），之後的更正句因無草稿照現行走一般回合 | G1；W-R2／R3／R4 退回追問；P1 |
| A2 | 確認待決時，使用者句子照既有意圖判斷呼叫（`write_intent`）抽到**同動作**欄位值，且與綁定那張卡的值**不同** ⇒ 程式經 `_write_draft_gate_value` 更新草稿，再由 `to_payload(草稿)` 經 `confirm_request` 重出新卡（舊卡由 A7 作廢）；值相同 ⇒ 不重出卡。⛔ 把 `pending["payload"]` 複製進草稿、⛔ 直接改 pending 內容；綁定的卡已有 receipt ⇒ 不重出卡 | G3；2.1 correct slot、2.2；P1 |
| A3 | 「修改」按鈕語意改為：token 照現行立即燒掉、保留草稿（實作注意：`_run_confirm_segment` 現對所有按鈕先 `clear_write_draft()`，A1／A3 須改此處）、程式問「要修改哪一項」（列卡上欄位）；若新增 receipt 標記，`_answer_for_receipt` 須明確處理（⛔ 落入預設成功收據）；「取消」維持現行 | G2；2.2「Disambiguate what users want to correct」；P1 |
| A4 | enum 欄位改由**程式**決定代碼：意圖判斷呼叫的 schema 對 enum 欄位只收**標籤**（取自表單，例「非緊急」「緊急」），程式依表單把標籤轉成代碼；不在標籤集合 ⇒ 視為缺值、照表單追問（⛔ 讓模型直接填代碼）；適用全部 enum 欄位 | G4；W-R2 k1「不急」成「緊急」（候選根因：說明只列代碼 1／2，待 A 後重測確認）；P1（值的意義由程式依表單決定） |
| A6 | 依 A0 結果：出卡前預檢。**通用做法（R1）**：預檢與系統值重算由表單宣告、共用流程執行——`WriteForm` 新增選填宣告（哪個欄位是既有資料的編號、用哪個帶 viewer 的唯讀查詢、從讀到的列算出哪些 `SOURCE_SYSTEM` 欄位）；共用出卡流程對「表單有宣告且編號欄有值」者一律執行，流程程式 ⛔ 出現動作名（宣告定在 `WriteForm`／`FORMS` 上，⛔ 另設名稱查表；流程層無動作名分支）；`bill_due_extend` 的宣告重用既有 `_fill_bill_fields`（F8）。既有 `_resolve_bill_by_period` 的動作名分支是現況（第六批 A，依物件＋期別對帳單），屬候選選擇路徑，本片不改、交 A-2 檢討。其餘約束：只用帶 viewer 的讀取（⛔ 寫入端點、⛔ token）；看不到與不存在回同一句；不可行原因只用封閉樣板、且只在可見性確認後說；預檢只在 `render()` 與雜湊之前改 payload；兌現端既有檢查全保留；有編號的延期卡以 viewer 讀到的列重算原到期日（§7 F8） | G6；W-D1 k1／k2；2.3；P1 |
| A7 | **唯一有效卡**（作廢以 DB 為準）：(1) 模型自呼與程式觸發出卡：在 `tools/confirm.py` `confirm_request` 寫 token 處改為 `async with db_pool.acquire() as conn: async with conn.transaction():` 包住「燒本 session 所有未兌現 token」＋`_INSERT_TOKEN_SQL`；INSERT 前任何例外 ⇒ 整筆回滾、舊卡仍有效、無新 pending；`confirm_request` 在 INSERT 之前就早退（缺欄、候選、render 失敗、NO_MATCH、日期早於今天）⇒ 不燒。(2) A2 重出卡：先以既有 `redeem_pending()`（綁 `pending_id`＋`session_id`＋`redeemed=false`＋`expires_at>now()`）燒綁定卡並提交、丟掉回傳 token；回 None ⇒ 不重出卡、回程式固定句；之後 `confirm_request` 任何早退或例外，舊卡都已失效。(3) 清單點選（`_run_select_segment`）作廢舊卡時，同步以 DB 燒（不再只改 `invalidated` 旗標）。(4) 宣稱口徑：「同 session 可兌現的 pid ≤ 1」（pending 唯一寫點 `_begin_pending_confirm`＋回合結束整包存檔），不宣稱 DB 只剩一列；燒卡沿用 `redeemed=true`（既有取消／修改／作廢慣例）。(5) 範圍閘擋下時：舊卡已燒、新 token 無 pending ⇒ `_run_confirm_segment` 回 `confirm_unknown_pending_id`、不可兌現 | 安全審查 F1、F2、Q1；plan-verifier r1 B1；安全複核 A7-1～A7-6；P1 |
| A8 | **單一動作登錄**：`runtime.py`、`tools/confirm.py`、`write_forms.py` 不再各自 import `CONFIRM_ACTIONS` 副本，改在呼叫當下讀 `confirm_card.CONFIRM_ACTIONS`（模組參照）；行為不變（現有 5 個動作逐字同結果）。既有動作名字面（`_resolve_bill_by_period`、`DOCUMENT_PROGRAM_CONFIRM_ACTIONS`、`FORMS` 建表分支）是現況，本片不改 | 業主 2026-10-18 裁定「流程改讀單一登錄」；再審 r5 阻擋；R1；P1 |

### A-2（下一片，候選選擇；A 驗收後出片計畫，先送 security-reviewer）

原 A5 移出 A 片。理由：安全複核（§7）指出「挑完回原流程」要放寬三道既有閘（`_write_draft_begin`、`_write_draft_decide` 在 `SELECT_SCOPE_KEY` 有值時停用草稿；`_start_write_intent_call` 要求草稿存在），且選取段跑在草稿驗證之前、填 `bill_id` 後缺原到期日會交回模型（重開 F8）；這些是範圍邊界的設計，獨立成片審查比塞進 A 安全。原 A5 內容與安全約束保留如下，A-2 計畫以此為起點：

| A5（移至 A-2） | 候選清單成為會話狀態：只從工具結構化結果 `data["candidates"]` 記錄（⛔ 從回答文字解析），只存 id 與比對屬性（編號、金額、到期日、期別標籤；⛔ 名稱、email、電話），只對緊接的下一回合有效；使用者打字指稱時，數字整段相等比對，唯一命中 ⇒ 組成 `select:<type>:<id>` 再經 `_parse_select_value` 驗；0 或多筆 ⇒ 再列並說明。挑完回原流程（定案，送 security-reviewer 複核）：`select_scope` 照現行寫入、範圍閘照舊 fail-closed；若當下有寫入草稿，且被挑的類型等於草稿動作表單中某欄位宣告的候選類型（表單 `FormField` 新增屬性 `select_type`，現有唯一一例：`bill_due_extend.bill_id` → `bill`；`_SELECT_TYPE_TO_TOOL` 現只有 bill／contract／repair），則**不清草稿**，由程式把選中列的 id 填進該欄位，來源記為新值 `program_select`（只限宣告了 `select_type` 的欄位、值只取自程式記住的候選列或按鈕 `select:` 已驗證的 id，⛔ 經模型）；其他情形照現行清草稿。出卡時範圍閘仍比對卡上物件＝`select_scope` 物件，兌現端仍以 viewer 讀可見清單 | G5；W-D2 k1、W-D3、W-D5 k1；P1 |

A-2 必須先解決的安全複核發現：A5-1 只做最窄放寬（只在表單 `select_type`＝`select_scope.type` 且該欄由程式選取填入時保留草稿；範圍內物件名補值、物件記憶維持關閉）；A5-2 選取段自跑 `load_draft`／建立者比對／可見性／開關四道；A5-3 F8 重算原到期日為硬前置；A5-4 填 `bill_id` 時移除 payload 中舊 `estate_name`／`period`；A5-5 值取自查詢回傳已驗證列並過型別解析；`program_select` 不得做成 `FormField.source` 新值（`load_draft`／`to_payload` 會丟），改以封閉驗證的草稿來源欄；打字 `select:bill:<id>` 不受候選清單限制須明寫（與使用者直接說編號同信任等級）。驗收候選：9j、9o(2)′、9u～9z。

A 不做（附理由）：
- B、C、D 各項：分片，A 驗收後再出計畫（業主可改順序）。
- 不新增動作專屬分支、不加詞表、不只改提示詞（§1.1 R1、R2）。
- 不改 DSP-038 卡文字、雜湊、兌現核心；不改 `select:` 按鈕路徑（DSP-042）。
- 正式機、preview：⛔ 碰。

### B（第二片，概要；A 驗收後出計畫）

- B1 寫入流程進行中（草稿存在或確認待決）的回合，使用者看到的文字一律由程式樣板產生（追問、卡、收據、取消、做不到）；模型自由文字不在這些回合出現。對應 G7、W-R4 k2 假卡、W-D2 k1「請點擊確認」無卡、W-D5 k1 宣稱已延後。
- B2 工具結果分「給模型」與「給人看」兩份；給人看的只由使用者端 formatter 產生。對應 G8、W-D1 k1、W-D2 k1／k2、W-D3 k1／k2、W-D5 k1／k2。

### C（第三片，概要；跨元件）

- C1 `agent.turn` 回傳加選填鍵 `card`（標題、欄位清單 {label, value}、動作清單 {label, value}），由同一 formatter 產出；`answer` 保留卡文字當備援（MCP「SHOULD also return the serialized JSON in a TextContent block」同型）。
- C2 JGB 需求稿：`AgentTurnClient.php` 白名單加 `card`、`ConfirmCard.vue` 依結構渲染、無 `card` 時沿用 `answer`。JGB 端由業主轉交，本系統 ⛔ 改 jgb2。

### D（另起計畫）

- 第 2 步 N 抽 40 fabricated 10/36、K1／K6／K7 少一項必須包含事實。目標形態（業界 grounding／faithfulness 做法）**尚未渲染**，本計畫不宣稱；另起計畫照四步走。

### 相關但不在本次範圍

- 查詢工具 `jgb2.query.*` 改程式觸發（DSP-085 §5 後續）：與寫入生命週期不同題。
- 截斷（W2）、敏感題業者端防線：HANDOFF §1.4 第 3 步候選，另排。

## 5. 驗收（A 片；細項見清單檔）

- 主觀察點＝第 2 步同一量尺（M 修正後）：本機常駐服務 `/mcp` 實打，模擬客人多輪＋程式前判＋盲判。
- 終點指標：第 2 步寫入任務 Intercom 解決（補真值後）W 10/20（W-R 6/10、W-D 4/10）。M 後在現行容器重跑得「M 後基線」（M4 改寫 W-D1、W-D2、W-D3、W-D5；M1 改修繕真值與角色指令；M5 新增專題）——與第 2 步不再同題組，故 **A 預期以 M 後基線為準**：同一題組上，W-R2 k1（A4）、W-R3 k1、W-R4 k1（A2／A3）三型在 M 後基線未解決者，A 後至少 +3 場轉成解決（若 M 後基線已有其中幾場解決，照實列出、預期相應減少）；W-D 依 A0／A6 結論；W-D2 型（候選選擇）歸 A-2；W-R4 k2（假卡、首句）歸 B／A0。M5「歸 A」組每題預期在 A 後解決；其餘組只記錄。
- 回歸：E2a R、D、C、T、RS、DS 逐輪通過不退步；知識 K 20/20 不退步；unit 與 golden 測試全過；`make audit` PASS。
- 依 DSP-087 不設新門檻；數字交業主。

## 6. 擁有、執行、回退、用量、停點

- 擁有：A 片程式 `rag-orchestrator/services/agent/{runtime.py,write_forms.py,tools/confirm.py,tools/action.py,confirm_card.py,agent_session.py}` 與對應測試；M 片 `~/jgb-archive/eval-harness/`。
- 執行：A 涉及確認 token 作廢／重發（寫入授權）⇒ security-executor；M ⇒ 主會話或 mech-executor。
- 回退：A1～A6 加開關（比照 `AGENT_WRITE_DRAFT`），關閉即回現行行為；A7 唯一有效卡屬安全強化，**不隨開關關閉**（回退＝git revert），並記一條 DECISION（「多張卡並存」從未裁決過；內容含 §7 A7-5 誤傷情形與 `handle_agent_entry` 註記）——我先這樣定，要改請說；commit 由業主指示。
- 實作前置：查既有測試是否要求同一 session 兩張卡都能兌現（`tests/` 搜 `PENDING_CONFIRM_MAX`），有則列出、交業主裁；測試替身（`FakePool`、`_Pool`）是否支援 `acquire()`／`transaction()`；外部 `/mcp` 身分能否直接呼叫 `confirm.request`。
- 用量：收尾回報子代理 token 加總＋Bedrock 費用（不設 token 上限）。
- 停點（結果條件）：A0 根因指向 mock 本身（非本系統）⇒ 先回報、A6 改為只修量尺；A2 重出卡造成任何「舊 token 仍可兌現」⇒ 停（P0）；回歸任一項退步 ⇒ 停。

## 7. 審查處置

### security-reviewer（2026-10-18，唯讀；主會話已對碼 F1 關鍵事實：`invalidated` 只在 select 段設、`PENDING_CONFIRM_MAX = 20`、rag-orchestrator 內 `asyncio.Lock|pg_advisory|FOR UPDATE` 0 筆、正對照 `asyncio.wait_for(` 有命中）

| 發現 | 嚴重度 | 處置 |
|---|---|---|
| F1 作廢只放 A2 分支，模型自呼出卡路徑與意圖判斷失敗時舊卡仍可兌現 | P1 | FIX：新增 A7，作廢放唯一出卡收斂點 |
| F2 只改狀態旗標會被併發存檔蓋掉 | P2 | FIX：A7 以 DB 為準、先燒後發 |
| F3 新 receipt 標記會落入預設成功收據 | P2 | FIX：A3 寫明 |
| F4 草稿保留後重複原值會自動重出卡 | P2 | FIX：A2 只在值不同時重出卡 |
| F5 拿 pending payload 填草稿會繞過「值出自使用者原話」閘 | P2 | FIX：A2 寫明只走 `to_payload`→`confirm_request` |
| F6 候選來源、存活期、守門未寫；`select_scope` 會清草稿 | P2 | FIX：A5 寫明；`select_scope` 與草稿互動已定案（A5），送 security-reviewer 複核 |
| F7 預檢可能洩露、有副作用、成第二套規則 | P2 | FIX：A6 寫明 |
| F8 有編號的延期卡原到期日由模型填、未比對（既有） | P3 | FIX（併入 A6，屬同一預檢） |
| F9 併發存檔可能蓋掉 receipt（既有） | P3 | DEFER：不重複寫入（token 已燒）；另記待辦 |
| Q1 A2 與舊卡送出併發 | 待查 | 採 S3（A7 燒不到就不出新卡） |
| Q2 既有測試是否要求兩張卡並存 | 待查 | 列為實作前置（§6） |
| Q3 A0 根因線索 | 待查 | 併入 A0 |
| Q4 確認待決期間 idle 累加 | 待查 | 併入 A1 |

建議驗收條目 S1～S12 已併入驗收清單 #9（逐條列）。

### 業主指示的第二次再審 plan-verifier（REVISE，1 substantive）

| 阻擋 | 處置 |
|---|---|
| R1／#2 所列登錄不足：`CONFIRM_ACTIONS` 在 runtime／tools.confirm／write_forms 各有 import 副本；送出走的工具登錄表啟動時由 `ACTION_SPECS` 建好；A6 名稱查表不在 #2 清單 | 業主裁定「流程改讀單一登錄」：新增 A8；A6 宣告定在 `WriteForm`；R1 檢查句與 #2 列明全部登錄點（主會話已 grep 全部 `CONFIRM_ACTIONS`／`ACTION_SPECS`／`FORMS`／`specs_for` 引用）；業主指示改完直接交核可、標未再審 |
| 待查：`_scope_gate_confirm_request` 對未知動作回 None，假動作測不到範圍閘 | #2 註明；範圍閘由 9m、9r 涵蓋 |

### 業主指示的再審 plan-verifier（REVISE，1 substantive＋1 wording-only）

| 阻擋 | 處置 |
|---|---|
| R1／#2 假動作檢查無法執行（`CONFIRM_ACTIONS`、`_RENDERERS`、`ACTION_SPECS` 為逐動作登錄，計畫未界定算不算流程程式） | 業主裁定「動作專屬登錄不算流程」；R1 檢查句列明可加的登錄與不得改的檔，加讀法註記；#2 通過條件同步 |
| 原話對照漏「照 §2.4…的計畫」「交我核可後才實作」（wording-only） | FIX：兩檔原話對照補上 |
| 待查：9q 整合測試是否呼叫 JGB | 實作時定；若呼叫則受 R6 約束（#0 不只限 `run.py` 批次） |

### 收尾 plan-verifier（REVISE，3 substantive＋1 wording-only；依 GOV-1 新條款審，逐條規則忠實性：R1、R2、R5 忠實，R3、R4 放大未註記）

業主 2026-10-18 選「照改後再審一次」（業主指示的延續，非自動第三輪）。

| 阻擋 | 處置 |
|---|---|
| A6 F8 重算屬單一動作，與 R1／驗收 #2 不能同時成立 | FIX：A6 改為表單宣告預檢、共用流程執行；#2 通過條件改寫為可判宣告式設定 |
| 原話→規則→驗收對應不完整 | FIX：新增 R6（mock）、R7（業界做法）、R8（不弱化寫入授權，標明非業主原話）；「把本地替換 oss」列非目標；§1.1 加原話對照；驗收每列標規則 ID |
| A1 草稿生命週期無驗收 | FIX：A1 寫明 idle 規則與按鈕回合；驗收新增 #5 |
| R3、R4 放大與讀法未註記（wording-only） | FIX：兩處同步加讀法註記 |
| 待查：§2.4 Copilot Studio 句支持力偏弱 | 只用於 A-2，A-2 計畫重查；本片不依賴 |

### plan-verifier r2（REVISE，3 substantive＋1 wording-only，全部 FIX；第二次自動 REVISE ⇒ 新準備期，只開一次收尾審查）

| 阻擋 | 處置 |
|---|---|
| M5 專題依賴 A5 與 A 外工作 | M5 分組：歸 A（改欄位、修改）／歸 A-2（打字挑候選）／只記錄（中途插話）；驗收 #7 同步 |
| M1～M4 無驗收 | 驗收加 #M1～#M4，列為 M 後基線重跑前置 |
| 同題組口徑與 M4 改寫範圍矛盾 | M4 明列 W-D1／D2／D3／D5；預期改以 M 後基線為準 |
| #9 範圍字樣 9a～9l、#2 A1～A6 未更新（wording-only） | 改「9a～9aa（9j、9o 移至 A-2）」「A0～A4、A6、A7」 |

### security-reviewer 複核（2026-10-18，A7 改版與 A5 定案）

| 發現 | 嚴重度 | 處置 |
|---|---|---|
| A7-1 驗收 9b 與 9n 互斥（同交易回滾後舊卡仍有效） | P2 | FIX：A7 分路徑寫；9b 改為 9b′ |
| A7-2 A2 燒綁定卡 SQL 未綁 session | P3 | FIX：重用 `redeem_pending()` |
| A7-3 同交易保證不了 DB 只剩一列未兌現 | P3 | FIX：宣稱改「可兌現 pid ≤ 1」，驗收 9p；不加 advisory lock（最壞為兩張皆燒、fail-closed） |
| A7-4 `redeemed=true` 兼作燒卡 | P4 | DEFER：沿用既有取消／修改／作廢慣例；`assert_redeemed` 無外流路徑（複核已查） |
| A7-5 誤傷情形（範圍閘擋下、模型自發呼叫、文件第三道網、外部直呼）屬可用性損失 | P4 | FIX：寫進 §6 待記 DECISION；外部直呼可見性列實作前置待查 |
| A7-6 清單點選作廢仍只改旗標 | P3 | FIX：A7 (3) |
| A5-1～A5-5 | P2／P3 | 拆片：A5 移至 A-2，發現全數帶入 A-2 起點 |
| `routers/agent_entry.py` `handle_agent_entry` 無呼叫者、用裸 session_id | P4 | DEFER：記入 DECISION 註記（重新掛上前須改命名空間鍵） |

### plan-verifier r1（REVISE，6 條）

| 阻擋 | 處置 |
|---|---|
| B1 P1：A7 放 `_begin_pending_confirm` 做不到（INSERT 在 `confirm_request`、該函式同步、範圍閘早退不經過） | FIX：A7 移到 `confirm_request` 內、INSERT 前同交易；A2 綁定卡另以單一 UPDATE 燒、0 列不重出；範圍閘情形寫明；驗收加 9m、9n（主會話已對碼：`_INSERT_TOKEN_SQL` 只在 `tools/confirm.py`、`def _begin_pending_confirm` 非 async） |
| B2 P2：A、M 未寫預期變化 | FIX：§4 M 寫「0，前置於 A」；§5 寫現值 W 10/20 → 同題組 ≥ 15/20（安全複核後 A5 拆至 A-2，現為 ≥ 13/20；r2 再改為「M 後基線上三型 +3」，以 §5 為準），逐場列依據（precheck：W-D1 k1／k2、W-D2 k1／k2、W-D5 k1／k2、W-R3 k1、W-R4 k1／k2 未解決，W-R2 k1 補真值後未解決） |
| B3 P2：首句資訊、物件名無歸屬 | FIX：兩類併入 A0 查根因、不列入 A 驗收；§1 成功句改寫各類歸屬 |
| B4 P2：A4 只改提示詞，違 R2 | FIX：A4 改為程式依表單把標籤轉代碼、非標籤視為缺值；掛 P1；驗收 #6 改寫 |
| B5 P2：`select_scope` 定案留到核可後 | FIX：A5 定案並送 security-reviewer 複核；驗收加 9o |
| B6 wording-only：A6 少對應欄 | FIX |
