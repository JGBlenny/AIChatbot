# B 片計畫：寫入進行中的回話由程式產生、帶狀態句只對得到實際狀態（2026-10-20，草稿）

- 狀態：r5 草稿（依 security-reviewer 處置改寫，§9.1；依 plan-verifier 第 1、2 輪處置改寫，§9.2、§9.3；收尾審查 REVISE 後依業主裁示改為依 `kind`、只放行 `answer`，§9.4），再審 wording-only 已修、未再審（§9.6）；**業主 2026-10-20 核可**，Q1 乙′、Q2 不潤飾、Q3 LLM 判讀、Q4 列出讀到的值、Q5 歸 A-2（逐字見驗收檔第一節原話 6），規則與清單已凍結；執行依 AUTO（不 commit、不 push）。
- 決策：DSP-091（分工）、DSP-094（上線範圍含 B）、DSP-098（順序 A → 期別 → A+ → DG → B → W2 …）。
- 規則與驗收清單：`acceptance-b-write-replies-program-20261020.md`（規則 B-R0～B-R15、清單 V0～V16（含 V0a），規則在前），核可時凍結。
- 服務原則（目標正本 `architecture-target-20261018.md` §2.8）：P2 帶狀態句只由程式依實際狀態產生；P3 給模型的資料與給人看的呈現分開。接手 §3.1 KD-3、KD-4。
- 終點指標：B 鎖定的四類 M0 缺陷（文字請確認卻未出卡 ≥4 場、確認無按鈕 7 場、假收據 1 場、內部提示外露 7 場）在使用者入口層轉為 0 或逐場附根因；E2b、E2a 不低於 A+ 收案基準。
- 風險類別：寫入確認路徑與使用者看到的狀態（security-sensitive：輸出驗證、狀態真實性）⇒ 核可前 `security-reviewer`，再 `plan-verifier`；實作交 `security-executor`；完成後 fresh `verifier`。
- 盤查：`/canon-audit agentic-mcp` 30/30（含先前殘留的 0/25 那筆，已重起並讀滿）。證據：`~/jgb-archive/arch-step3-20261018/b/`（`kd34_q.sh`→`kd34-20261020.out`、`hint_leak.py`→`hint_leak-20261020.out`）；業界原頁：`~/jgb-archive/arch-step3-20261018/next/sources-b/`（2026-10-20 渲染）與 `~/jgb-archive/devflow-20261018/`（2026-10-18／19 渲染，目標形態研究 `next/target-b.md`）。

## 1. 目標

**使用者要的結果**：辦事時，系統說「請確認」就一定有一張能按的卡；說「已完成／已送出／已取消／已轉真人」就一定真的發生了；看到的話不夾系統給模型的內部提示。依據規則 B-R2～B-R9。

**目前量到的差距**：

| 缺陷 | 量到 | 出處 |
|---|---|---|
| 文字說「請確認」卻未出卡 | M0 至少 4 場（W-R2_k2、W-R4_k2、W-D5_k1、C-C_k1；逐句核對，另 5 筆比對式誤抓已剔除）；A+ E2b C-M_k2；DG 實打 s 第 2 回合（點選範圍） | `~/jgb-archive/arch-step3-20261018/m/report-m0.md` §4；`aplus/report-aplus.md` §5 觀察 2；`~/jgb-archive/arch-guard-20261020/v6/V6-evidence.md` |
| 確認卻無按鈕 | M0 7 場（W-R2_k2、W-R3_k2、W-R4_k1、W-R4_k2、W-D5_k1、C-C_k1、S-1_k1） | `m/defect_cats.json`「按確認無按鈕」 |
| 假收據 | M0 C-C_k1「已為「學生獨立套房」建立合約」（`state=answered`、無寫入）；DG s 第 2 回合「我已為帳單…延後 3 天」 | 同上 |
| 內部提示外露 | 第 2 步 7 場；對話紀錄中含提示句的回合：第 2 步 E2b 16、M0 36、A 後 29，全部出自程式候選清單出口；A+ E2b 0（同目錄候選清單回合也是 0，未走到該路徑） | `b/hint_leak-20261020.out` |
| 寫入中由模型寫回話（KD-3） | 2026-10-19 起本機 18 回合：提議未發 7 回合（8 次標記）、程式呼叫非終結 10 回合、`prose_confirm_suspect` 1 回合；模型最後輸出 answer 8、handoff 7（非終結後 3、提議未發後 4）、ask 3 | `b/kd34-20261020.out`（正對照：同時段 `write_draft_program_confirm` 579） |
| W-R3 誤讀不可見 | A+ E2b W-R3 ×2：使用者「物件不對，是就是豪宅啦」，意圖抽成「豪宅」＝卡上值 ⇒ 回「卡片還在，請按確認」 | `aplus/report-aplus.md` §5 觀察 1 |

## 2. 目標形態（業界做法；逐字原文，檔案在 `~/jgb-archive/` 之下）

### 2.1 Rasa、Lex 把帶狀態、帶後果的回話做成依狀態挑選的預寫回應；其他家做法不同

- Rasa：「By default, your assistant sends templated messages to the user, however:」——`devflow-20261018/sources-repair/rasa-business-logic.txt`；依狀態挑選樣板：「Conditional response variations let you define several static message templates under the same response name but tailor them to different states of the conversation.」「These variations are not LLM-based—they are “what you see is what you get” messages, drawn from your domain or responses files.」「Strict control over the exact wording in specific contexts or channels (e.g., “VIP members get a special greeting”).」——`arch-step3-20261018/next/sources-b/rasa-contextual-rephraser.txt`；條件以對話狀態判定：「the constraints of each conditional response variation are checked against the current dialogue state.」——`next/sources-b/rasa-responses.txt`。
- Amazon Lex 確認的三種回應皆預寫：「Confirmation response – This response is sent to the user when the user confirms the intent.」「Decline response – This response is sent to the user when the user declines the intent.」「Failure response – This response is sent to the user when the confirmation prompt can't be processed.」——`devflow-20261018/sources-repair/lex-confirmation.txt`。
- Google Dialogflow CX flows：「Designing an agent with deterministic flows takes more design time, but it is a good option for agents that require explicit control over agent responses.」——`devflow-20261018/sources-arch/google-generative-vs-deterministic.txt`（原文講的是「對回應有明確控制」，未逐字寫「預寫」）。
- Zendesk 系統回覆：「system replies are designed to deliver specific types of messages at different points in a conversation with a customer」「What the AI agent should say when escalating a conversation to a human agent.」（該列設定方式為「Yes (Dialogue)」）——`devflow-20261018/sources-arch/zendesk-system-replies.txt`。同一張表也有 AI 生成的系統回覆：「When no relevant use case is detected, the AI agent replies with an AI-generated message.」（Generative replies reply）、「the AI agent searches available knowledge sources to generate an answer」（Knowledge reply）——系統回覆不全是預寫。
- 反例（做法不同，⛔ 寫成「業界都用樣板」）：Zendesk generative procedures「The AI agent sends information to the customer, such as a confirmation, status update, or explanation.」——`sources-arch/zendesk-generative-procedures.txt`；Salesforce「Send the prompt to the LLM and return the LLM’s response to the customer.」——`sources-arch/salesforce-ascript-flow.txt`；Intercom Fin 無按鈕「Fin AI Agent cannot display or control UI buttons. Fin can only offer to escalate through text.」——`sources-arch/intercom-conversational-fin.txt`。逐家有據的說法：Rasa（預設）與 Lex 的這類回應是預寫回應；Google CX flows 標榜對回應的明確控制；Zendesk 的轉真人回覆是可設定的系統回覆，但同表的 Generative／Knowledge reply 由 AI 生成；Zendesk 生成式程序、Salesforce、Intercom Fin 的最終回話由 LLM 產生。本線選樣板依 DSP-091 與 M0 缺陷，不是業界共通。

### 2.2 模型改寫是 opt-in，廠商自己警告會改意思（對應 RB-2）

- 「By default, rephrasing is only enabled for responses that specify rephrase: True in the response template’s metadata.」「Hallucination: When rephrasing, it is possible that the LLM changes your message in a way that the meaning is no longer exactly the same.」——`devflow-20261018/sources-arch/rasa-contextual-response-rephraser.txt`。
- 反例：Rasa 自家範例對一句狀態句開了改寫（「Ok, I understand you don't want to be connected to a human agent. Is there something else I can help you with?」，該回應 `metadata` 為 `rephrase: True`）——`sources-repair/rasa-patterns.txt`。

### 2.3 模型產出的回覆在送出前由輸出防護檢查，不合就由程式擋下、改回設定好的回應

- OpenAI Agents SDK：「Output guardrails run on the final agent output」「First, the guardrail receives the output produced by the agent.」「Finally, we check if .tripwire_triggered is true. If true, an OutputGuardrailTripwireTriggered exception is raised, so you can appropriately respond to the user or handle the exception.」；官方範例的防護本身是另一個帶結構化輸出的 LLM agent：「guardrail_agent = Agent(」「instructions="Check if the output includes any math.",」「output_type=MathOutput,」——`next/sources-b/openai-agents-guardrails.txt`。
- NVIDIA NeMo Guardrails：「Output rails inspect the generated response before it returns to the user. These rails can allow, edit, or block the response.」——`next/sources-b/nemo-output-rails.txt`；「The goal of the output self-checking rail is to determine if the output from the bot should be returned to the user. This rail will prompt the LLM using a custom prompt.」「The bot refuse to respond message is returned when the output should not be allowed.」「With the default parser, self_check_input and self_check_output treat empty output as unsafe and block.」「The performance of this rail is strongly dependent on the capability of the LLM to follow the instructions in the self_check_output prompt.」——`next/sources-b/nemo-self-check.txt`。
- OpenAI 同頁也寫明檢查不一定是 LLM：「A guardrail can call an external classifier directly; it does not need to run another agent」——`next/sources-b/openai-agents-guardrails.txt`。
- 對 B 的意義：兩家都把「模型回覆可不可以送出」放在送出前的一道檢查。OpenAI 的檢查可以是 LLM agent（範例）或外部分類器，觸發時拋例外、交開發者處置；NeMo 的 self-check 用 LLM 判讀，不允許時回設定好的拒答句，判讀輸出為空（達 max_tokens）時預設擋下。判讀**逾時與例外**時要不要擋，兩家原文都沒寫——本線的 fail-closed 是推導（§4.3），查無業界逐字對應。兩家範例檢查的是有害內容與主題（數學作業），**沒有**逐字針對「回覆宣稱的狀態與系統實際狀態不符」——這一項是第一原理（§2.5）。

### 2.4 給模型的資料與給人看的呈現分開（P3）

- MCP：「Tool results may contain structured or unstructured content.」——`devflow-20261018/sources-card/mcp-tools-latest.txt`；「Describes who the intended audience of this object or data is.」——`sources-arch/mcp-schema-annotations.txt`。
- Salesforce：「To hide output information from the agent, set the output parameter’s filter_from_agent property to True.」——`sources-arch/salesforce-ascript-ref-actions.txt`。
- Intercom：「the data bypasses Fin's collection or reasoning entirely and remains untouched.」——`sources-arch/intercom-procedures-data-connectors.txt`。
- 「給人看的那份由程式格式器組成」沒有查到哪一家逐字這樣寫；MCP 規格只提供欄位與讀者標記、未寫哪一份必須給使用者（`target-b.md` §5）。

### 2.5 第一原理（查無業界逐字對應）

- 帶狀態句是狀態的函式：「請確認」的真值＝此刻有一張有效的卡；「已完成」的真值＝已收到執行成功結果。真值由程式持有，所以帶狀態句由程式依狀態產生（§2.1）；模型寫的文字若宣稱了狀態，送出前要對照程式狀態，對不到就不送（§2.3 的形態，比對對象換成程式狀態）。
- 佐證廠商自承會發生：「Sometimes, the playbook AI Generator will hallucinate information in a response in lieu of a tool result.」——`devflow-20261018/sources-arch/google-playbook-best-practices.txt`；Google 建議的緩解是提示詞，本線 DSP-085 規定 ⛔ 只加提示詞。
- 為何判讀要用 LLM、不用詞表：帶狀態句的說法是開放的（「我已為帳單…延後」「已為…建立合約」「請確認以上變更」「請按送出」），M0 以「請確認」字樣比對時 9 場命中、逐句核對後只 4 場是真的（K3、O-1 的「請確認」是請客人自己核對資料）——詞表同時漏抓與誤抓。專案記憶「開放語義換層不補詞表」。

## 3. 差距（現況；查證指令在 repo 根目錄執行）

| # | 現況 | 查證（含正對照） |
|---|---|---|
| G1（KD-3） | 提議未轉成程式呼叫：封閉結果 `{"ok":False,"error":…}` 回模型，模型寫回話；程式呼叫非終結：`proposal_program` 與 `wd_program` 兩處回填結果後 `continue` 再叫模型。兩處註解寫「由 B 片接手」。 | `git show 73d94a07:rag-orchestrator/services/agent/runtime.py | grep -n "由 B 片接手"`（2 處）；`grep -n "V_WRITE_PROPOSAL_NOT_ISSUED\|V_PROGRAM_NONTERMINAL" rag-orchestrator/services/agent/runtime.py`；DB：`bash ~/jgb-archive/arch-step3-20261018/b/kd34_q.sh 2026-10-19`（18 列；正對照 579） |
| G2（KD-4） | 一般出口只在 `kind=ask ∧ ask_target=confirm_intent ∧ 無 confirm.request` 記 `prose_confirm_suspect`，只 append、不改寫；`kind=answer` 的假完成句（DG 3a40）不記任何標記。寫入情境中模型 `kind=ask` 的問句照送。 | `grep -n "prose_confirm_suspect" rag-orchestrator/services/agent/runtime.py`；探針 `test_kd4_probe_model_confirm_prose_is_only_counted`（`rag-orchestrator/tests/unit/agent/test_dsp091_division_contract_req.py`） |
| G3 | Verifier 不擋帶狀態句：`assertion_terms` 為「可以、支援、不支援、需要、會、不會、無法、能、不能、提供、支持、包含、內建、整合、自動」，不含完成類說法；DSP-040 `grounding_observe` 下引用類拒因只記錄不擋。 | `grep -n -A16 '"assertion_terms"' rag-orchestrator/config/agent_verifier_rules.json`；`grep -n "_GROUNDING_OBSERVE_REASONS" rag-orchestrator/services/agent/verifier.py`（正對照：同檔命中定義） |
| G4 | 模型文字只有一個送出組裝點（`normalize_terminal_punctuation(out.answer)`），判讀閘放這裡即涵蓋所有模型回覆；確認卡、固定句不經此點。 | `grep -c "normalize_terminal_punctuation(" rag-orchestrator/services/agent/runtime.py` ⇒ 1 |
| G5（P3） | 候選清單出口把給模型的清單文字（`_candidates_text`，含「⛔ 不是使用者指定編號的資料」「請以 ref 指定該編號再查一次」）直接接在 `CONFIRM_CANDIDATES_TEXT` 後當使用者回覆；`ToolResult` 只有 `text_for_model`，無給人看的版本。 | `grep -n "不是使用者指定編號的資料\|請以 ref 指定該編號再查一次" rag-orchestrator/services/agent/tools/jgb2.py`；`grep -n "CONFIRM_CANDIDATES_TEXT + " rag-orchestrator/services/agent/runtime.py`；`python3 ~/jgb-archive/arch-step3-20261018/b/hint_leak.py <目錄>` |
| G6 | 確認無按鈕：程式出卡一律帶三顆鍵（`_begin_pending_confirm`）；A+ 後一般寫入回合模型路徑出卡 0（A+ 報告 §6）。M0 的 7 場出自模型文字「請確認」而無卡——G2 的同一條路徑。 | A+ `aplus/v2_r3_all.out`；`grep -n "def _begin_pending_confirm" rag-orchestrator/services/agent/runtime.py` |
| G7 | W-R3：AP-2 依規則回 `CARD_STILL_VALID_TEXT`，句中不含讀到的值。 | `grep -n "CARD_STILL_VALID_TEXT" rag-orchestrator/services/agent/write_forms.py rag-orchestrator/services/agent/runtime.py` |
| G8 | 輸出上限：`DEFAULT_MAX_COMPLETION_TOKENS = 2000`；意圖呼叫另用 `WRITE_INTENT_MAX_COMPLETION_TOKENS`（800）。 | `grep -n "DEFAULT_MAX_COMPLETION_TOKENS = \|WRITE_INTENT_MAX_COMPLETION_TOKENS" rag-orchestrator/services/agent/runtime.py rag-orchestrator/services/agent/write_forms.py` |

## 4. 路徑（單片）

### 4.1 改動

| 項 | 改什麼 | 服務的目標／事件 |
|---|---|---|
| B1（KD-3） | 開關 on、寫入情境回合：提議未發（`write_proposal_not_issued`）與程式呼叫非終結（`write_draft_program_confirm_nonterminal`，兩處）⇒ 先過現行 #9b 出口，再由 B2 狀態回話結束回合，不再回填給模型。問句回合依 Q1：乙′ 下照現行回模型封閉結果，讓模型回答提問，其回覆經 B3，程式再接 B2 狀態行。 | G1；KD-3；18 回合（`kd34`） |
| B2 | 新增狀態回話函式（程式依狀態挑固定句，⛔ 以動作名分支；**只讀，⛔ 出新卡、⛔ 建 token**——出卡的唯一判斷仍是 `_write_draft_decide`，它在每個寫入情境回合已於程式優先、提議合併後、模型輸出後三處呼叫，B2 不再給第四次機會，安全審查 S2）。順序：(1) 同動作綁定卡有效且 `to_payload(草稿)` 與卡 `draft_payload` 全部鍵相等 ⇒ 重用 `_write_proposal_card_unchanged`（唯讀；含 `pending_token_state` live、重排版雜湊相符、卡上日期未早於今天）⇒ 前導句 `CARD_STILL_VALID_TEXT`（本回合使用者值被值閘丟掉 ⇒ `CARD_UNCHANGED_TEXT`；B5 加讀到的值）＋換行＋**整張卡文字**、同 pid、原三顆鍵、無新 token（同 `_write_draft_card_still_valid_exit`）；(2) 綁定卡 live 但草稿與卡不同（本回合沒重出卡）⇒ 新固定句 `CARD_DIFFERS_TEXT`「確認卡上的內容和你剛才說的不一樣，卡片沒有更新，這筆還沒有送出。要照卡上內容送出請按確認，要改請按「我要修改」。」＋換行＋整張卡文字、同 pid、原三顆鍵；(3) 草稿缺欄 ⇒ 以 `WF.missing_labels(動作, to_payload(草稿))` 經 `missing_label_vocab()` 檢查後套 `MISSING_FIELDS_ASK_TEMPLATE`，`ask_target`＝`WF.ask_target_for_missing(labels)`；標籤不在詞彙內 ⇒ 走 (4)；(4) 新固定句 `WRITE_NOT_ISSUED_TEXT`「這筆還沒有送出，這次沒辦法產生確認卡。請再說一次要辦的內容，或稍後再試。」；(5) 無草稿、本 session 無 live 綁定卡 ⇒ 新固定句 `NO_PENDING_WRITE_TEXT`「這次沒有替你送出或變更任何資料；要辦理的話，請直接告訴我要辦什麼。」（只說本回合，⛔ 宣稱整段對話沒有送出過，S4）。一律經 `_finish_confirm_turn` 結束回合（⛔ 經 `_finalize`，否則被 T1 改成 `ASK_TARGET_TEXT`，S7）；(1)(2) `kind=ask`、`outcome=confirm_pending`；(3) `kind=ask`；(4)(5) `kind=answer`、`ask_target=None`。**寫入情境回合裡，模型回覆的處置（逐格，只看封閉欄位 `kind`、`ask_target` 與結構規則 `_is_question`）**：

| 回合 | 模型 `kind` 與 `ask_target` | 處置 | `write_reply_source` |
|---|---|---|---|
| 非問句 | `answer`／`ask`／`recommend`（任何 `ask_target`） | 丟棄，回本函式結果 | `program` |
| 問句 | `ask`／`recommend`（不論 `ask_target`，含 `None` 與值域外） | 丟棄，回本函式結果（寫入欄位追問、選哪一筆與確認歸程式，DSP-091「寫入全程與確認」「已選定的那筆紀錄」） | `program` |
| 問句 | `answer` | 模型文字送出＋狀態行（乙′，依 Q1）；`ask_target` 強制 `None` | `model_plus_status` |
| 任一 | `handoff` | 現行 DSP-021 固定句（E 片） | 不記 |

**為何依 `kind` 判、不列 `ask_target` 值（業主 2026-10-20 裁「只放行 answer」，§9.4）**：以 `ask_target` 值界定「寫入追問」兩度失敗——表單宣告的追問對象（`WF.label_ask_targets()`）只有 `estate`、`description` 2 值，漏掉 `address`、`date`、`bill_id`、`urgency` 等（R4-1）；改列白名單只放行 `choice` 也不成立，因為程式自己在寫入流程請使用者選哪一筆時就標 `choice`（`runtime.py` `CONFIRM_CANDIDATES_TEXT` 分支的 `make_outcome("clarifying", expects="choice")`＋`select:` 按鈕），模型在寫入中問「要延後哪一張帳單」同樣可能標 `choice`。`ask_target` 由模型填，一個值可同時是知識追問與寫入追問，任何值表都切不乾淨；改依回覆種類：寫入情境的問句回合，模型只有 `answer` 能送出，`ask`／`recommend` 不論 `ask_target` 一律換成程式狀態回話。KD-4 後半句（寫入追問由模型自寫）在結構層消除。**收窄**：寫入進行中使用者插問時，模型不能反問使用者（DSP-091 知識作答的追問歸 AI，此處只保留 `answer`）；使用者可在寫入結束或取消後再問。**殘餘風險**：模型把寫入追問寫進 `kind=answer` 的文字（例：「好的，請問地址是？」）結構規則抓不到——要判讀內容；B3 判讀閘只判帶狀態句，不判追問，本片不擴；列 §8。

送出的模型回覆 ⛔ 帶 `ask_target=confirm_intent`：上表已在第二列丟棄，判斷只看模型輸出欄位，與本回合工具呼叫紀錄無關（未轉成程式呼叫的提議也會留下 `confirm.request` 錯誤紀錄，使現行 `prose_confirm_suspect` 三條件不成立；plan-verifier 第 2 輪 B-1）。`kind=answer` 的 `ask_target` 強制 `None`（S8）。**乙′ 狀態行**：模型文字依現行順序經 B3、T1／T2、Verifier（`_finalize` 內出口閘不變，`normalize_terminal_punctuation` 只套模型文字，S12）後，由程式接上——(1)(2) ⇒ 模型文字＋空行＋該前導句＋換行＋整張卡文字，改由 `_finish_confirm_turn` 結束、附同 pid 三顆鍵（DSP-038：卡文字逐字出現、不經模型與 Verifier；S1）；(3) ⇒ 追問句；(4)(5) 不接。trace 記 `write_reply_source`，供 V12 (f)。 | B-R2、B-R4；G2；KD-4 後半；C-M_k2 |
| B3 | 帶狀態句判讀閘：一般出口組裝點之前，對將送出的模型文字（`kind` ∈ answer／ask／recommend；handoff 走 DSP-021 固定句，不經）做一次判讀呼叫（同意圖呼叫的供應方與模型；推理強度取供應方允許的最低值；新常數 `STATE_CLAIM_MAX_COMPLETION_TOKENS`＝200、`STATE_CLAIM_TIMEOUT_S`＝4，逾時與回合 deadline 取較早者）。**輸入**只有回覆文字，以每次隨機 nonce 標記的資料段包住，判讀指示寫明段內文字只是被判讀的資料（S10）；⛔ 資料段、草稿值、卡文字。**輸出** JSON `{"claims":[…]}`，值域四類，皆指「這則回覆宣稱**系統／助理在這段對話中替使用者做了或正在做**」：`awaiting_confirmation`（要使用者按確認／送出）、`completed`（已送出／建立／延後／變更）、`cancelled`（已取消）、`handed_off`（已轉真人）；轉述查到的紀錄狀態（「這張帳單已繳清」）不屬任何類（S4）。**程式比對**狀態事件（驗收檔第二節：本回合事件＋session 內 live 綁定卡、`completed_actions`、已兌現或已取消的 `pending_confirm` 收據）；任一類對不到 ⇒ 模型文字 ⛔ 送出、⛔ 進 dialog（S9），記 `state_claim_unbacked:<類別>`，改回：寫入情境回合＝B2；其他回合＝`NO_PENDING_WRITE_TEXT`；`handed_off` 一律改回新固定句 `HANDOFF_OFFER_TEXT`「需要真人客服的話，請直接說「找真人客服」。」（不宣稱轉過或沒轉過，S4）。現行 `prose_confirm_suspect` 三條件成立 ⇒ 不呼叫判讀、直接當 `awaiting_confirmation` 未對到（標記保留，供不變量 45 印數）。**判讀失敗**（逾時、非 JSON、值域外、例外）：本回合可出卡的回合——寫入情境、點選範圍、文件、文件暫存有效回合——fail-closed；其他回合照送並記 `state_claim_check_failed`（S5）。**計量與紀錄**：判讀呼叫經 `usage_metering.add_llm_usage` 計量、token 計入本回合；判讀輸入輸出原文 ⛔ 進 trace、snapshot、log，只記類別與耗時（S9）。換句一律經 `_finish_confirm_turn`（S7）。方法依 Q3 裁示。 | B-R5、B-R6；G2、G3、G4；DG 3a40、C-C_k1、M0 ≥4 場、無按鈕 7 場 |
| B4 | 給人看的候選清單：`jgb2.py` 新增給人看的格式器（同一列投影，⛔ 兩句給模型的提示，⛔ 回顯模型 payload 的查詢字串——只列程式解析出的列值，S11），候選清單出口改用它；`dialog_answer` 改用程式摘要（比照 `SELECT_DIALOG_SUMMARY`，S11）；給模型的 `_candidates_text` 不變。兩句提示改為具名常數（單元測試以常數比對）。 | B-R7；G5；內部提示外露 7 場 |
| B5（待 Q4） | W-R3：B2 (1) 且本回合使用者句子帶出的值都與卡相同 ⇒ 前導句後加一行「這次讀到的是：{標籤}「{卡上值}」，和卡上相同；要改請按「我要修改」。」（值取卡 formatter 的顯示值，⛔ 放使用者原句）。 | B-R9；G7；A+ W-R3 ×2 |
| B6 | 開關：`AGENT_WRITE_REPLY_PROGRAM`（B1、B2、B5）、`AGENT_STATE_CLAIM_GATE`（B3）；值域 on／off、未設＝on；off ⇒ 與改前逐字相同。B4 無開關（純顯示修正）。 | B-R13 |
| B7 | KD-3、KD-4：開工前存三支「改前行為探針」（KD-3 既有行為探針；KD-4 新增 (i) 模型自寫「請確認」照送、(ii) 寫入欄位追問由模型自寫照送，見驗收檔 B-R4 讀法），在改前程式通過、在新程式失敗（**順序**：先在新程式上照原樣跑三支改前探針並存輸出，之後才從登記移除 KD-3、KD-4——探針開頭的 `_anchor_present` 讀 `KD_BY_ID`，先刪登記會讓失敗原因變成 KeyError 而不是行為斷言；收尾審查待查項；移除登記時，`tests/unit/agent/dsp091_known_deviations.py` 規則表中引用 KD-3、KD-4 的 `"kds"` 元組要同步刪，否則 `test_dsp091_division_contract_req.py` 的 `assert kd in KD_BY_ID` 會失敗；KD-4 行為探針 (ii) 的假模型輸出要帶 `ASK_TARGETS` 內的值（例 `address`），帶 `None` 會被改前程式的 T1（`exit_gates.py` 的 `ask_target in ASK_TARGETS` 判斷）改成 `ASK_TARGET_TEXT`，探針在改前程式就不通過——r5 再審提醒），再改寫成必過契約；既有 KD-4 靜態探針（字串在、有 `append`、下一行無 `answer =`）在本設計下預期仍通過（標記保留），不當證據，隨 KD-4 移除一併刪；從 `dsp091_known_deviations.py` 與目標正本 §3.1 移除；兩處「由 B 片接手」註解改成現況；`division_guard.py` 第 ③ 段另印 `state_claim_unbacked:*`、`state_claim_check_failed` 次數（只印數，DSP-087）。 | B-R3、B-R4；目標正本 §5 第 8 條 |

### 4.2 不做

- 結構化 `card`／`structuredContent` 進 `/mcp`（C 片）；點選範圍、文件回合的出卡改程式（A-2、文件回合）；意圖抽取品質（F 片）；轉人規則與收尾（E 片）；中斷回原流程、說「算了」取消（F 片）；C-B 合約同名（建議 A-2，Q5）。
- ⛔ 加提示詞叫模型不要說「已完成」（DSP-085）；⛔ 以詞表判帶狀態句（§2.5）；⛔ 讓模型潤飾固定句（待 Q2，建議不潤飾）。

### 4.3 偏離目標形態的取捨

- **判讀用 LLM（AI 理解）**：DSP-091「理解由 AI、下一步由程式」——判讀只回「這段話宣稱了哪類狀態」，送不送、送什麼由程式依狀態決定，不是 AI 決定程式環節的下一步（B-R1）。代價：每則模型回覆多一次呼叫；V12 (e) 量延遲與次數並列，不設門檻。若業主選詞表或混合（Q3），§2.5 的漏抓誤抓風險照實保留。
- **判讀失敗的處置分兩種**：本回合可出卡的回合（寫入情境、點選範圍、文件、文件暫存有效）fail-closed（推導：NeMo 只寫判讀輸出為空時預設擋，逾時與例外兩家都沒寫）——這些回合說錯狀態的後果是客人以為已送出；其他回合照送，因為知識回答在判讀服務故障時整批被換成固定句，傷害比少見的漏判大。照實寫：這是依使用者效果的取捨，不是業界做法。
- **「已完成」以 session 內有收據為據，不比對是哪一筆**：模型在後面回合提起前面真的送出的那筆（「剛才已幫你延後」）是真話，只看本回合會誤擋（S4）；代價是 session 內有任何收據時，模型把 A 筆說成已完成、實際完成的是 B 筆，判讀閘攔不到。比對到哪一筆需要判讀抽出動作與對象，本片不做，殘留風險列 §8。
- **乙′ 重附卡時重出整張卡文字**：同一則回覆前面是模型文字、後面是逐字卡文字。DSP-038 要求確認卡由程式產生、逐字成為回覆且不經模型與 Verifier——卡文字在判讀閘與 Verifier 之後才接上，卡外前導句沿用 A+ AP-2 的作法（安全審查 S1）。
- **寫入情境回合的非問句一律回狀態回話**（KD-3 出口與模型任何非 handoff 的 `kind`，含 `answer`；問句回合依 B2 逐格表）：使用者在寫入中說了別的事（非問句，例「我先去看一下」）時，會得到「卡片還在…」或「還需要：…」而不是對那件事的回應。目標形態是理解層把「改做別的事」當指令（F 片）；本片先保證說出口的狀態為真。V12 逐場記錄是否發生。
- **寫入情境問句回合只送模型的 `answer`，追問不送**（業主 2026-10-20 裁，§9.4）：`ask_target` 由模型填、同一值可同時是知識追問與寫入追問（`choice` 即是），依值切不乾淨，故依 `kind` 判。代價：寫入進行中模型不能反問使用者；殘留風險：寫入追問寫進 `answer` 文字抓不到（§8）。
- **乙′ 讀法相對 §4 B 列字面收窄**（Q1）：DSP-091 規定知識作答與一般對話歸 AI；若選甲（插問也回固定句），會與 DSP-091 衝突，須先改 DSP-091。
- **B2 不出新卡**：模型說了「請確認」但程式沒出卡時，使用者得到「這筆還沒有送出…」而不是一張新卡。出卡判斷 `_write_draft_decide` 在同一回合已跑過三次、帶齊凍結回合、已送出修改、期限、重出擋關等條件；它沒出卡就是有擋下的理由，B2 再出一次等於繞過那些條件，或讓模型的措辭間接決定出卡（安全審查 S2；DSP-091 出卡歸程式）。代價：少數「本該有卡」的場次要使用者再說一次；V12 逐場記錄。
- **KD-3 出口後模型原本選轉人（7 回合：非終結後 3、提議未發後 4）改回狀態回話**：轉人歸 E 片；本片不擴大轉人來源。

### 4.4 文件同步（B-R15）

目標正本 §3.1（刪 KD-3、KD-4）、§3 P2／P3 現況列、§4 B 列狀態；HANDOFF §2.1／§2.2；`AGENTIC_MCP_ARCHITECTURE.md` 寫入確認與出口段（grep「prose_confirm_suspect」「只統計」）；`mcp-facade.md` §7.1（answer「已經過 Verifier」與確認卡、固定句、判讀閘的區別）；DECISIONS 新增 B 片決策列（核可後）；`.claude/MAP.md` 若登錄計畫檔則同步。

## 5. 安全

r1 已送 `security-reviewer`（唯讀）審，結論與處置見 §9；r2 依處置改寫後的安全不變量：
- B 的新出口 ⛔ 出新卡、⛔ 建 token；只以唯讀判定（`_write_proposal_card_unchanged`）重出同一張卡（同 pid、原三顆鍵）。可兌現卡數、A7、DSP-092 鎖不受影響。
- 附確認鍵的回覆一定含整張卡文字，卡文字在判讀閘與 Verifier 之後接上、逐字（DSP-038）。
- 判讀閘只讀模型文字；確認卡、固定句、收據文字不經判讀、不經模型。判讀輸入以 nonce 資料段包住；輸入輸出原文不落 trace、snapshot、log；被擋的模型文字不進 dialog。
- 換句後 `ask_target` ⛔ 設 `confirm_intent`（T3 肯定語不會被當授權）；寫入情境回合中模型的 `ask`／`recommend`（含帶 `ask_target=confirm_intent` 者）一律不送（只看模型輸出欄位，與工具呼叫紀錄無關），乙′ 送出的 `answer` 強制 `None`。
- 開關 off ⇒ 與改前逐字相同。

## 6. 執行與驗收

1. 開工前：他窗 4 份檔 sha256 存 `b/others-sha256-before.txt`；KD-3、KD-4 舊探針存 `b/probes-before/`；mock 檢查 `True`。
2. 實作（`security-executor`，一份完整 brief，帶 Hard rules）：B1～B7；單元 V3、V4、V5、V8 (a)、V9、V11；開關 off 正對照。
3. 重建常駐容器 → mock 檢查 → V1、V2、V10、V13；重放 V6（8×3）；判讀量測 V7；E2b＋E2a V12；V8 (b)；V14。
4. fresh `verifier`（V15）。
5. 報告 `~/jgb-archive/arch-step3-20261018/b/report-b.md`；commit 由業主指示；不 push。

## 7. 待業主裁

業主 2026-10-20 已裁（驗收檔原話 6）：Q1 乙′、Q2 不潤飾、Q3 (甲) LLM 判讀、Q4 (甲) 列出讀到的值、Q5 歸 A-2。以下保留裁示前的選項原文。

- **Q1（RB-1）寫入進行中回話全由程式樣板的範圍**：
  - 乙′（建議）：狀態回話（缺欄追問、確認卡、卡片狀態、未送出說明）與按鈕全由程式；使用者插問（問句回合）時，模型的回答（`answer`）可送出，但先過判讀閘，程式在後面接狀態行、卡有效時重出整張卡與同卡按鈕；模型的追問（`ask`／`recommend`，不論追問對象）一律換成程式狀態回話。非問句回合的模型回覆（含 `answer`）一律換成程式狀態回話。
  - 甲：寫入情境回合一律只送程式固定句（插問也不答）。須先改 DSP-091（知識作答歸 AI）。
  - 乙（target-b 原選項，「缺欄追問仍可由 AI 組」）不列：已登記為 KD-4 偏離、業主指示 B 接手，等於已排除。
- **Q2（RB-2）固定句填值後可否再讓 LLM 潤飾**：建議不潤飾（Rasa 自承改寫會改意思，§2.2；專案記憶記舊 REST 鏈答案優化階段 2 因刪掉參數而停用）。未見業主就本線的逐字裁示，故列待裁。
- **Q3 帶狀態句的判讀方式**：(甲) LLM 判讀、每則模型回覆（建議，§2.3、§2.5）；(乙) 詞表（漏抓誤抓，M0 9 命中 4 真）；(丙) 詞表初篩＋LLM 確認（省呼叫，初篩漏的就漏）。範圍（全部模型回覆、四類、三形狀必攔）已寫進 B-R5、B-R6，依業主指示由本計畫定，核可即凍結。
- **Q4 W-R3 的程式句**：(甲) 「卡片還在」句再列這次讀到的值（建議，B5）；(乙) 維持現句，W-R3 交 F 片修意圖抽取。
- **Q5 C-B 合約同名兩筆「還需要：合約」歸屬**：建議 A-2（正確的回應是列出兩筆讓人點選＝候選選擇）；B 不改。
- 不需裁、已確認：DSP-097（程式列是否含按鈕）不影響本片——按鈕現由程式組（`AgentOutput` 無按鈕欄位），本片只保證程式的「請確認」都帶按鈕。

## 8. 回復、停點、用量

- 回復：兩個開關設 off ⇒ 改前行為；B4 以 git 還原單一函式。
- 停點（看結果）：E2b < 30/32 且未解決場次的機制出自本片改動；V6 任一次未對到事件的帶狀態句送出；V11 任一條失敗；判讀閘讓確認卡或固定句被改字。觸發即停、回報業主。
- 殘留風險（不擋收案，照實回報）：「已完成」只對到 session 內有收據、不對到哪一筆（§4.3）；判讀是 LLM，漏判率由 V7 量、不設門檻；寫入情境問句回合的模型 `answer` 若在文字裡追問寫入欄位（例「好的，請問地址是？」），結構規則（只看 `kind`）抓不到、B3 也不判追問——V12 逐場記錄是否發生。
- 用量：收尾回報子代理 token 加總與 API 費用。計畫期至今：scout 3 次合計 247,025 tokens；security-reviewer 238,510 tokens；plan-verifier 第 1 輪 146,260 tokens、第 2 輪 117,018 tokens、收尾審查 91,274 tokens；再審 2 輪 100,099、95,851 tokens；合計 1,036,037。

## 9. 審查紀錄

### 9.1 security-reviewer（r1，2026-10-20）：無 P0，P1 1 條、P2 5 條、P3 5 條、P4 1 條

| # | 級 | 發現（摘要） | 處置 | 落點 |
|---|---|---|---|---|
| S1 | P1 | 乙′ 在模型文字旁附同卡確認鍵卻不重出卡文字，抵觸 DSP-038 | FIX：附鍵就接整張卡文字（同 `_write_draft_card_still_valid_exit` 的 `f"{lead}\n{card}"`），接在判讀閘與 Verifier 之後 | B2 乙′ 狀態行；§4.3；V4 |
| S2 | P2 | B2 (3) 在新出口呼叫出卡路徑，繞過 `_write_draft_decide` 各道擋關；從 B3 換句進入＝模型間接決定出卡 | FIX：刪除 B2 (3)；B 不出新卡、不建 token（查證：`grep -n "_write_draft_decide(" rag-orchestrator/services/agent/runtime.py` 定義外 3 處呼叫） | B2；B-R13；V11 (2) |
| S3 | P2 | B2 (1) 少「草稿＝卡 `draft_payload`」與唯讀約束 | FIX：重用 `_write_proposal_card_unchanged`；值被丟用 `CARD_UNCHANGED_TEXT`；草稿≠卡新增 (2) `CARD_DIFFERS_TEXT` | B2 (1)(2)；V3、V4 |
| S4 | P2 | 事件只算本回合，換回句本身可能說假話（前回合的卡、已送出、查到的已完成紀錄） | FIX：事件表加 session live 綁定卡、`completed_actions`、`pending_confirm` 收據；類別限定「助理替使用者做的」；換回句改成只說本回合或不宣稱狀態 | 驗收檔第二節；B3；B2 (5)；V5 (i)(j)(k) |
| S5 | P2 | fail-closed 範圍漏了文件、文件暫存回合 | FIX：改成「本回合可出卡的回合」 | B3；B-R5；V5 (e) |
| S6 | P2 | `kind=recommend` 未涵蓋 | FIX：判讀涵蓋所有非 handoff kind；寫入情境回合 recommend 比照 ask。量到的次數：10-01 起 `final_kind` ask 934、answer 729、handoff 61、recommend 0 | B2、B3；B-R4、B-R5；V4、V5 (c) |
| S7 | P3 | 換句走 `_finalize` 會被 T1 改成 `ASK_TARGET_TEXT` | FIX：一律 `_finish_confirm_turn`；缺欄用 `WF.ask_target_for_missing` | B2、B3 |
| S8 | P3 | 乙′ 回合可能觸發 T3 `AFFIRMATIVE_CARRY_TEXT` | FIX：乙′ 回合 `ask_target=None` | B2；V4 |
| S9 | P3 | 判讀呼叫計量；原文不落紀錄；被擋原文不進 dialog | FIX | B3；V5 (g) |
| S10 | P3 | 判讀輸入可被注入 | FIX：nonce 資料段包裹；V7 加注入題 | B3；V7 |
| S11 | P3 | 候選清單回顯 payload 查詢字串；`dialog_answer` 用全文 | FIX：只列程式解析出的列值；`dialog_answer` 用程式摘要 | B4；V8 (a) |
| S12 | P4 | B6／B5 筆誤；判讀在接狀態行前；標點正規化只套模型文字；`missing_fields_ask_text` 吃 ToolResult | FIX：全數改正（缺欄改以 `WF.missing_labels` 組句、不在詞彙退 (4)）；§5 r1「AP-3 (a)」誤植，改為 AP-2 的 `_write_proposal_card_unchanged` | B2、B3、B5 |

待查（審查員列出，未評級；處置）：
- JGB 面板是否只有最後一則訊息的按鈕可按 ⇒ 不影響 r2 設計（附鍵一律重出整張卡）；W2／C 片接 JGB 時確認。
- 過去回合「已完成」句的誤判率 ⇒ 由 V7 量（加入 session 有收據的後續回合句）。
- facts／receipt 是否有其他提示句外露 ⇒ 審查員已答：沒有其他出口把提示接進 answer（正對照：候選清單出口命中）；V8 (b) 掃描照做。
- 4 秒逾時與回合 deadline ⇒ 取較早者（B3）。
- recommend 出現次數 ⇒ 已量：10-01 起 0 次（同上 S6）。

### 9.2 plan-verifier 第 1 輪（r2，2026-10-20）：REVISE，P2 6 條、P3 1 條

主 session 逐條核對（kd34 輸出重數、`grep -rn "由 B 片接手"` 2 筆、讀 KD-4 探針原文、讀兩份業界原頁），全數成立，處置皆 FIX，改成 r3：

| # | 級／Kind | 發現 | 處置與落點 |
|---|---|---|---|
| B1 | P2／substantive | 原話 1 未逐字完整（缺「依據：」「計畫裡要先交我裁的題目：」）；流程、DSP-098、核可前不動程式、AUTO 沒有規則承接 | 驗收檔原話 1 改為逐字全文；新增 B-R0（流程與權限）與 V0a |
| B2 | P2／substantive | 問句回合中模型 `kind=ask` 的處置前後不一，丟棄會碰 DSP-091 知識追問 | B-R4 (a) 限非問句回合；問句回合依 Q1 乙′ 不丟、經 B3 後接狀態行；B2、§4.3、V4 四處一致 |
| B3 | P2／substantive | KD-4 靜態探針在本設計下大概率仍通過，「轉為失敗」不成立；KD-4 後半句無探針 | 改以開工前新增的兩支行為探針證明（前後半句各一）；V1 寫明失敗斷言；靜態探針隨 KD-4 移除刪除（B7、B-R3、B-R4） |
| B4 | P2／substantive | B-R2、B-R8 無驗收項 | V3、V4 引 B-R2；V12 (f) 以 trace `write_reply_source` 量使用者入口層；新增 V16（B-R8：靜態無 LLM 呼叫＋逐字等於常數） |
| B5 | P2／wording-only | §2.3「兩家都送預設回應」「檢查用 LLM」「拿不到結果預設擋」超出原文 | §2.3 改為 OpenAI 拋例外交開發者、可用分類器；NeMo 回拒答句、空輸出預設擋；逾時與例外的 fail-closed 標推導（§2.3、§4.3） |
| B6 | P2／wording-only | B-R13「卡文字逐字＝answer」與乙′／V4 字面矛盾 | B-R13 改為「逐字完整出現在 answer 中」，讀法欄註明與 A+ AP-2 一致 |
| P3 | P3／wording-only | 「由 B 片接手」實為 2 處；kd34 分布數字有誤 | §1、§3 G1、B7、§4.3、非目標依實際輸出改正 |

### 9.3 plan-verifier 第 2 輪（r3，2026-10-20）：REVISE，P2 4 條

第二次自動 REVISE ⇒ 依全域規則停止重送，主 session 逐條處置；處置為實質修正 ⇒ 記新的就緒時期（r4），只開一次收尾審查。主 session 已核對：未轉成程式呼叫的提議會留下 `confirm.request` 錯誤紀錄（`runtime.py` 中 `acc.violations.append(WF.V_WRITE_PROPOSAL_NOT_ISSUED)` 之前的 `ToolCallRecord(... status="error" ...)`）；`ASK_TARGETS`（`output_schema.py`）多數是寫入欄位；Zendesk 原頁同表有 Generative／Knowledge reply。

| # | 級／Kind | 發現 | 處置與落點 |
|---|---|---|---|
| B-1 | P2／substantive | 問句回合模型 `ask_target=confirm_intent` 可能照送（提議未發留下工具紀錄，結構條件不成立），下一回合「好」觸發 T3 | FIX：B2 逐格表——問句回合 `ask`／`recommend` 帶 `confirm_intent` 一律丟棄，只看模型輸出欄位；B-R4、B-R13、§5 同步；V4 (3) |
| B-2 | P2／substantive | 問句回合保留模型 `ask_target` ⇒ 寫入欄位追問仍由模型自寫，KD-4 後半句未消除 | FIX（審查員選項 (a)）：問句回合 `ask_target` 為表單宣告的寫入欄位對象（`WF.label_ask_targets()` 的值）⇒ 丟棄、回程式狀態回話；知識追問（其他合法值）才送；V4 (2)(4)；KD-4 整列移除、V2 仍為 6 筆 |
| B-3 | P2／substantive | 非問句回合模型 `kind=answer` 的處置未定，V12 (f) 無法判 | FIX：非問句回合任何非 handoff `kind` 都換成程式狀態回話；B-R2、B-R4、B2、§4.3、V4 (1)、V12 (f) 一致 |
| B-4 | P2／wording-only | §2.1 把 Zendesk 系統回覆、Google CX 寫成「預寫回應」超出原文 | FIX：Google 改為「對回應有明確控制」；Zendesk 補同表 AI 生成的系統回覆當反例；小標與總結句收窄 |
| 待查 | — | 乙′ 路徑的回合由哪個函式結束 | FIX：B2 寫明模型文字經現行 `_finalize` 出口閘後接狀態行，附卡時由 `_finish_confirm_turn` 結束 |

### 9.4 收尾審查（r4）

結論：REVISE，P2 2 條，皆 substantive ⇒ 依全域規則**暫停，交業主**（不再自動送審）。§9.3 的 B-1、B-3、B-4 已確認落地；B-2 未落地。主 session 已核對：`write_forms.py` `_ASK_TARGET_BY_KEY = {"estate_name": "estate", "description": "description"}`，`WF.label_ask_targets()` 的值只有 `estate`、`description`；`ASK_TARGETS` 共 19 值（`estate`、`community`、`address`、`bill_id`、`repair_id`、`contract_id`、`meter`、`date`、`description`、`urgency`、`confirm_intent`、`choice`、`photo`、`document`、`identity`、`scale`、`team`、`pain`、`interested`）。

| # | 級／Kind | 發現 | 建議處置（待業主選） |
|---|---|---|---|
| R4-1 | P2／substantive | 「寫入欄位對象」以 `WF.label_ask_targets()` 界定只涵蓋 2 值，`address`、`date`、`bill_id`、`urgency` 等寫入欄位追問會被當知識追問照送 ⇒ KD-4 後半句未消除；V4 (2) 例子與定義矛盾 | 反過來列白名單：寫入情境問句回合，模型 `ask`／`recommend` 只有 `ask_target == "choice"` 可送（加狀態行），其餘一律丟棄改程式狀態回話 |
| R4-2 | P2／substantive | 逐格表沒有 `ask_target` 為 `None` 或值域外的格 | 同上白名單一併涵蓋（非 `choice` 皆丟棄、記 `program`）；V4 加 `None` 案例 |

業主裁示（2026-10-20，AskUserQuestion 逐字）：「改白名單後再審一次 (Recommended)」（選項說明：寫入中的插問回合，模型的追問只有「choice」可以送出，其餘全部換成程式回話（含 ask_target 空值）；KD-4 整列可移除；改完再送一次 plan-verifier，READY 才交業主核可 Q1～Q5）。⇒ 改成 r5：B2 逐格表、B-R2、B-R4、V4、V12 (f)、§7 Q1 同步；待查項（探針與登記移除的順序）寫進 B7。

業主追問（2026-10-20 逐字）：「白名單 是 特規嗎？」主 session 答：白名單篩封閉值域、不算特規，但 `choice` 選錯——程式自己在寫入流程選哪一筆時標 `choice`（`runtime.py` `CONFIRM_CANDIDATES_TEXT` 分支），白名單會放行寫入追問；根層寫法是依 `kind` 不列值。業主裁示（AskUserQuestion 逐字）：「只放行 answer (Recommended)」（選項說明：看回覆種類，不列值：模型只有 answer 能送，ask／recommend 全部換成程式回話；KD-4 在結構層消除；缺點是寫入進行中模型不能反問使用者；殘餘風險：追問寫在 answer 文字裡抓不到，列進計畫）。⇒ r5 改依 `kind`：B2 逐格表、B-R2、B-R4、V4、V12 (f)、§7 Q1、§8 同步；`WRITE_CONTEXT_MODEL_ASK_TARGETS` 不新增。

### 9.5 業主指示再審（r5，2026-10-20）：REVISE，substantive 1 條（審查 brief 缺陷）、P3 wording-only 1 條

| ID | 級別 | 發現 | 處置 |
|---|---|---|---|
| R5-1 | substantive | brief 未附業主逐字原話，規則忠實性無法正式核對（暫看未見缺陷）；R4-1、R4-2 已確認消除，必查 2～6 皆無阻擋 | FIX（brief）：下一份審查 brief 直接貼業主原話 1 全文與兩次 AskUserQuestion 逐字選項，來源為對話紀錄 |
| R5-2 | P3／wording-only | 檔首狀態行仍寫「改白名單」 | FIX：改為「依 `kind`、只放行 `answer`」 |
| 提醒 | 不擋 | 移除登記要同刪規則表 `"kds"` 元組；KD-4 探針 (ii) 要帶 `ASK_TARGETS` 內的值 | 寫進 B7 |

用量：本輪 100,099 tokens；計畫期合計 940,186。

### 9.6 附原話再審（r5，2026-10-20）：REVISE，唯一 blocker 由審查員標 wording-only

| ID | 級別 | 發現 | 處置 |
|---|---|---|---|
| R6-1 | P2 以下／wording-only（審查員標） | V4 總述「寫入情境回合中…`kind=answer` ⇒ 模型文字在前、狀態句在後」未限問句回合，與同格 (1)、B2 首列、B-R2 矛盾 | FIX：改「寫入情境的問句回合中…（即下列 (5)）」——**已修，未再審** |
| 待查 (a) | 不評 | brief 稱原話 2 為點選範圍假完成句歸屬；驗收檔原話 2 實為 A+ 的 W-R3 答案 | 主 session 核對：驗收檔正確、brief 標錯；點選範圍「已裁交 B」在原話 1 內，B-R5／B-R6 承接；檔案不改 |
| 待查 (b) | 不評 | 原話 3～5 只在計畫 §9.4 | FIX：補進驗收檔第一節 |

規則忠實性（原話 1～5 逐句）、一致性、設計方法、分工、程式事實：審查員皆無阻擋。依全域規則（未經業主核可、收尾審查剩餘 blocker 皆由審查員標 wording-only）⇒ `next_gate: user_approval (fixed, not re-reviewed)`。

用量：本輪 95,851 tokens；計畫期合計 1,036,037。

用量：收尾審查 91,274 tokens；計畫期子代理合計 840,087 tokens。

待查（審查員列，不評級）：KD-3 探針呼叫 `_anchor_present("KD-3")` 讀 `KD_BY_ID`，執行時須先在新程式跑改前探針、再刪登記，否則失敗原因會是 KeyError——執行 brief 要寫明順序。
