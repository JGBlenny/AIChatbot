# 站內幫手對話架構——目標正本（業主 2026-10-18 定方向：混合式，DSP-091）

> **本檔回答「對話線應該長什麼樣」**：架構、目標、驗收方式、路徑。「現在怎麼跑」看 `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`；工作進度與下一步看 `HANDOFF-20261018.md`。
> 業界原文皆以 web-drive 渲染存檔於 `~/jgb-archive/devflow-20261018/`（`sources-repair/`、`sources-card/`、`sources-arch/`，每檔首行為網址與擷取時間）；下文引文皆可在該檔 grep 到原字串。
> 現況事實（§3）附可 grep 的符號，⛔ 不寫行號當事實。

## 核心架構：混合式——理解交給 AI，有規則、有後果的環節由程式掌握

**AI 負責聽懂使用者，並在知識作答與一般對話中自己決定怎麼查、怎麼答；凡是有業務規則、說錯或做錯會造成後果的環節，下一步由程式依宣告與狀態決定。**

| 環節 | 誰決定下一步 | 說明 |
|---|---|---|
| 理解使用者這句話要什麼（意圖、欄位值、要更正、要取消、要真人、已解決） | AI | 以標籤輸出，⛔ 讓 AI 填代碼 |
| 寫入全程：缺哪欄、出不出卡、能不能送出、送出後回什麼 | 程式 | DSP-085 已實作第一片 |
| 已選定的那筆紀錄（候選列出、使用者選了哪一筆、後續都用這筆） | 程式 | 換錯帳單的根因層 |
| 帶狀態的句子（請確認、已完成、已取消、已轉人）與確認卡、按鈕 | 程式 | AI 只組不帶狀態的話 |
| 轉人規則（含收尾）：何時轉、先問還是直接轉、道謝即收尾 | 程式（規則） | 收尾屬轉人規則（DSP-091）；AI 只提供「使用者要真人／已解決」的理解 |
| 知識完全查無時的出口（「處理不了」） | 程式 | AI 組話 |
| 知識作答：要不要查、查哪段、怎麼組答案；只答得出一部分時說明缺什麼、部分回答、追問 | AI | 只依核可知識（DSP-066）；答案有沒有依據由 Verifier（程式）把關（DSP-091） |
| 一般對話、追問的措辭 | AI | |
| 唯讀查詢（帳單、合約等）：依 AI 理解出的查詢條件，由程式查詢並篩選（如依期別篩帳單） | 程式 | AI 理解使用者要查什麼；AI 自呼工具只在程式接不住時用——該類查詢程式尚未宣告，或程式讀不出查詢條件；程式已宣告的查詢類型 AI ⛔ 繞過（DSP-091） |

**業界依據**：Rasa、Google 原文明說由 LLM 理解使用者，Intercom 原文寫由其 AI 代理 Fin 依客人說的話判斷（Salesforce、Zendesk 存檔中查無逐字對應的句子，查到的是 LLM 處理對話、AI 執行程序；原文見 §2.1）。有規則、有後果的步驟交給誰，各家不同：Rasa CALM 全交程式；Salesforce、Intercom 提供並建議把這類步驟交給程式決定性執行，其餘由 AI；Google 可任選全生成、部分生成或決定性流程；Zendesk 生成式程序由 AI 依程序執行條件判斷與外部動作（原文見 §2.1）。本線選 Salesforce／Intercom 型的混合式，理由是 M0 三類主缺陷（說「請確認」卻沒出卡、道謝後轉真人、換錯帳單）都出在模型決定有後果的步驟；不採全系統流程化，因為知識題與閒聊做成流程會變僵（Intercom 原文見 §2.4 末條）。

**依據的決策**：DSP-091（決策沿革見 `.claude/decisions/DSP-091.md`）、DSP-085。§2.8 原則 P1～P8 是本節在各層的展開；任何計畫若讓 AI 決定上表「程式」列的下一步，即違反本節。

## 0. 業主原話與規則（判定一律依規則）

業主原話：
- 「整個架構要不要先整理文件 避免之後歪掉」「整理清楚 後 紀錄 我要重開後執行」（2026-10-18）
- 「A 並更新相關文件 並免後續開發的 誤導」「清除錯誤 過時文件 不需要的封存 避免被誤讀 避免備注 很容易讓錯誤資訊被誤讀」「也確保 架構 任務目標 驗收成果 方向等 明確」「相關的目錄 索引 也要做好」（2026-10-18）
- 「像整體邏輯應該 有一個整體脈絡 而不是一個一個調整吧」「需通用方式修改 而非 特規補丁」（第 3 步計畫 §1）
- 「像是確認卡 應該是此系統出格式 接的系統呈現吧」（第 3 步計畫 §1）
- 「目前要該是要把本地替換 oss 並確保 回應品質都能符合 有效的回應 並把某些部分邏輯參考業界做法去調整」（HANDOFF 前版 §1.1）

| 規則 | 可檢查內容 | 出處 |
|---|---|---|
| AR1 一份涵蓋整體 | 本檔涵蓋對話線全部層次（理解、流程、修補、知識、轉人、回話、呈現）；M0 每一類缺陷都對得到一條原則（§3 末段） | 「整個架構」「整體脈絡」 |
| AR2 業界先於現況 | 依序：目標（§1）→ 目標形態（§2，每句業界宣稱附渲染原文）→ 差距（§3）→ 路徑（§4）；查無業界對應者寫明第一原理推導 | 全域「設計方法」 |
| AR3 防歪 | 本檔登進 `.claude/MAP.md` `#agentic-mcp`；每份計畫寫出所服務的原則編號與本檔章節（§5） | 「避免之後歪掉」「避免後續開發的誤導」 |
| AR4 可交接執行 | 本檔與 HANDOFF 都在 repo；HANDOFF 指向本檔；新視窗只靠兩檔即可開工 | 「我要重開後執行」 |
| AR5 通用不特規 | 原則不以動作名、欄位名、題目用字分支；動作差異只放在動作宣告（資料） | 「需通用方式修改 而非 特規補丁」 |
| AR6 卡由本系統出結構 | P8＝本系統出結構化內容、接入方呈現、附文字備援 | 「確認卡 應該是此系統出格式」 |
| AR7 方向與驗收明確 | 檔首寫明誰決定哪個環節；§1 寫明目標、基線數字與每片的驗收方式；§4 每片寫明服務的原則與狀態 | 「確保 架構 任務目標 驗收成果 方向等 明確」 |
| AR8 不留錯誤資訊 | 相關文件與本檔不留與 DSP-091 相反的現行陳述；錯的直接改正文、過時無用的刪除，⛔ 以附註或刪除線保留錯誤原文。讀法：「不需要的封存」＝已封存且無紀錄價值的檔，git 有追蹤者刪除、引用改 `git show` 指標 | 「清除錯誤 過時文件 不需要的封存…避免備注」 |
| AR9 索引 | `.claude/MAP.md` `#agentic-mcp` 登記本檔與 HANDOFF、DECISIONS 指標行含 DSP-091；刪除或改名的檔在 MAP 與本線文件中無失效引用 | 「相關的目錄 索引 也要做好」 |
| AR10 分工照 A | 檔首分工表的「程式」列與 DSP-091 選項 A 原文及業主追加裁示（收尾屬轉人規則；知識「不足」歸 AI、程式只管完全查無）逐項相同；A 未涵蓋且未裁的環節列待裁，⛔ 寫成已定 | 「A」；業主 2026-10-18 追加裁示（記於 DSP-091） |

## 1. 目標與驗收

**使用者成功的樣子**（業者、租客，多輪對話）：
1. 問知識題得到只依核可知識的答案；不足時被告知缺什麼、被追問，而不是被捏造或直接丟給真人。
2. 辦事（報修、延期、建物件／合約／帳單）時，說過的不被重問；說錯可以改、可以取消、中途插問別的再回來；按確認後真的完成，沒完成時被誠實告知。
3. 系統說出口的「請確認」「已完成」「已轉真人」永遠等於實際狀態。
4. 問完說謝謝就收尾，不被轉真人；真的需要真人時被清楚轉過去。
5. 接入方（JGB 網頁等）拿到結構化內容自行呈現，不必解析文字。

**怎麼量**（DSP-087）：模擬客人代理多輪對話＋程式前判＋盲判代理，算 Intercom 式解決率（最後一次回答後不再要求真人、不回頭再問）與嚴格解決率。

**基線（M0，2026-10-18，gpt-oss-120b，報告 `~/jgb-archive/arch-step3-20261018/m/report-m0.md`）**：

| 題組 | Intercom 式 | 嚴格 |
|---|---|---|
| 寫入 W 合計（修繕 W-R 10＋延期 W-D 10） | 4/20 | 4/20 |
| 其中延期 W-D | 0/10 | 0/10 |
| 更正專題 A | 4/12 | 4/12 |
| 知識 K | 16/20 | 11/20 |
| 全部 | 24/52（46.2%） | 19/52（36.5%） |

**每片怎樣算完成**：
- 該片在計畫裡凍結驗收清單（規則→觀察點→證據→通過條件），通過條件寫在使用者入口層（`/mcp` 實打、模擬客人對話），單元測試只是中間證據。
- 該片鎖定的 M0 缺陷類別，在同一題組、同一量尺重測中逐場轉成解決或附根因。
- 其他類別不退步：既有回歸題組不低於前一基線、測試全過、`make audit` PASS。
- 全線門檻（解決率要到多少才切正式機）尚未設定：DSP-087 定為「先跑出數字再定」，由業主依各片數字決定。

## 2. 目標形態：業界的分層架構

**一句話**：語言模型負責理解使用者要什麼；有業務規則的流程由預先宣告的步驟決定性執行；偏離正常路徑的情況由一組固定的「對話修補模式」處理；知識題走「只依核可知識、不足就說」的檢索作答；轉真人有明確規則；回覆層可選擇是否用模型組話；呈現交給接入方。

```
使用者訊息
 └─ L1 理解層（LLM）：程式掌握的環節輸出結構化指令（寫入意圖／更正／取消／選擇／要真人／已解決）；知識與一般對話在工具迴圈內作答
     └─ L2 流程層（程式，決定性）：每個業務動作一份宣告（欄位、驗證、預檢、確認、執行、收據）
         ├─ L3 對話修補模式：更正、取消、中斷後回原流程、澄清、完成收尾、處理不了、轉人、內部錯誤
         └─ L4 知識作答：只依核可知識；不足 ⇒ 說明＋部分回答＋追問；查無 ⇒「處理不了」模式
     └─ L5 轉人規則：何時轉（規則＋偵測）與轉去哪（流程）分開
 └─ L6 回話層：帶狀態的句子由程式依狀態產生；模型只組不帶狀態的話
 └─ L7 呈現層：本系統出結構化內容＋文字備援；接入方決定外觀
```

### 2.1 理解交給 LLM；有規則的步驟交給誰各家不同（L1、L2）→ 原則 P0、P4、P1

- Rasa CALM（`sources-repair/rasa-business-logic.txt`）：「CALM uses LLM to understand user input in the context of the conversation.」「Separation of concerns: In CALM assistants, LLMs keep the conversation fluent but don’t guess your business logic.」「Deterministic execution: Follows structured workflows for reliable, debuggable interactions.」
- Rasa 指令產生器（`sources-repair/rasa-llm-cmdgen.txt`）：「It outputs a sequence of commands that represent how the user wants to progress the conversation.」例：「the command output might be [SetSlot(slot_name, True), StartFlow("check_balance")].」
- Google Dialogflow CX（`sources-arch/google-generative-vs-deterministic.txt`）：「Dialogflow CX agents always use language models for understanding end-user intention, but you can decide whether and how language models are used for agent responses.」「once intention is established, you have complete control over the conversation flow and agent responses.」
- Intercom Fin Procedures（`sources-arch/intercom-fin-procedures.txt`）：「Use code for precision - Add code when you need Fin to follow strict rules when executing certain steps—such as ensuring accuracy for eligibility checks, date calculations, or record updates.」「Procedures are primarily triggered by customer intent — Fin decides whether to start a Procedure based on what the customer says.」
- Salesforce Agent Script（`sources-arch/salesforce-agent-script-lang.txt`）：「Logic instructions (->) run deterministically every time. Use them for business rules, running actions, setting variables, and conditional branching.」「Prompt instructions (|) are natural language sent to the LLM.」

- 有規則、有後果的步驟交給誰，各家不同：
  - Rasa CALM 全交程式（`sources-repair/rasa-dialogue-mgmt.txt`）：「The dialogue manager is the part of Rasa that decides how to take the best next step」。
  - Google 三種任選（`sources-arch/google-generative-vs-deterministic.txt`）：「You can choose from fully generative, partly generative, and deterministic features」；決定性 flows 是「a good option for agents that require explicit control」。
  - Intercom 程序內由 AI 決定下一步，需要嚴格規則的步驟用程式（`sources-arch/intercom-fin-procedures.txt`）：「Fin reasons about what to do next and adjusts seamlessly」「Use code for precision - Add code when you need Fin to follow strict rules when executing certain steps」；分岔條件可用自然語言或 Python：「Use Conditions for major forks in logic, such as eligibility checks or plan-based routing, using natural language or Python for predictable outcomes.」
  - Salesforce 混合（`sources-arch/salesforce-agent-script-lang.txt`）：「predictable execution where you need it, while preserving the LLM’s ability to handle nuanced conversations」。
  - Zendesk 生成式程序由 AI 執行規則步驟（`sources-arch/zendesk-generative-procedures.txt`）：「An alternative to scripted dialogues」「The AI agent checks a condition and then continues down the matching path.」

### 2.2 對話修補是一級機制（L3）→ 原則 P5

- 不重問已給過的資料：Zendesk generative procedures（`sources-arch/zendesk-generative-procedures.txt`）：「If a required detail is already available in the conversation, the AI agent may continue without asking again.」（Zendesk 由 AI agent 判斷；本線依 P1 由程式草稿持有欄位）
- Rasa（`sources-repair/rasa-patterns.txt`）：「Patterns implement Conversation Repair」；預設模式：「pattern_continue_interrupted for interruptions.」「pattern_correction for corrections.」「pattern_cancel_flow for cancellations.」「pattern_clarification for clarification.」「pattern_completed for completion.」「pattern_internal_error for internal errors.」；另有 `pattern_cannot_handle`、`pattern_human_handoff`。
- Google 對話設計（`sources-repair/gcd-help.txt`，舊版指南）：「Expect users to make corrections, after explicit and implicit confirmations」「Don’t cancel and force users to start the dialog over」。
- Amazon Lex（`sources-repair/lex-reelicit.txt`）：「you may want to re-elicit a slot after your customer declines a confirmation」。
- Microsoft Copilot Studio（`sources-repair/ms-topic-switch.txt`）：「it resumes in the originating topic by default」。
- Intercom（`sources-arch/intercom-procedures-vs-tasks-vs-workflows.txt`）：「Fin can jump sections, revisit steps, switch Procedures, and adapt when customers change direction mid-conversation.」
- 候選由程式從資料取出讓使用者挑：Rasa（`sources-repair/rasa-flow-steps.txt`）「want to display available values for the slot fetched from a database as buttons」；以打字指稱某一筆項目**查無業界專節**（第 3 步計畫 §2.4），以第一原理推導：候選清單是程式剛給出的有限集合，可對屬性做決定性比對。

### 2.3 不可逆動作前確認、綁參數、送出前驗證（L2）→ 原則 P1

- Google（`sources-repair/gcd-help.txt`）：「Double-check with the user prior to performing an action that would be difficult to undo」。
- OpenAI Agents SDK（`sources-repair/openai-hitl.txt`）：「Per-call approvals are scoped to the specific call ID」。
- Lex（`sources-repair/lex-confirmation.txt`）：「You can define a Lambda code hook to validate the intent before you send it for fulfillment.」

### 2.4 知識作答（L4）→ 原則 P6

- Intercom Fin（`sources-arch/intercom-fin-faqs.txt`）：「It only provides answers based on your support content or data.」「When it does not know the answer, it will say that it didn’t find an answer, and it can then hand over to a human.」知識不足時的回應「Give context of sources that were found.」「Express uncertainty.」「Attempt to answer if possible.」「Request clarification from the user.」（該檔逐條列出）。
- Intercom Fin AI Engine（`sources-arch/intercom-fin-ai-engine.txt`）：「Determine if the generated response is grounded in the knowledge of your knowledge resources and support content as a source of truth.」「If the output from the model doesn’t meet the Fin AI Engine™ parameters for certainty, then a response is generated to ask the customer to clarify their query.」
- Rasa Enterprise Search（`sources-arch/rasa-enterprise-search-policy.txt`）：「Rasa directs all knowledge based questions to the default flow pattern_search.」「If no relevant documents are retrieved then Pattern Cannot Handle is triggered.」；（`sources-arch/rasa-enterprise-search-pro.txt`）「it is important for the assistant to abstain from responding to the user.」
- Rasa 生成式檢索提示（`sources-arch/rasa-generative-search.txt`）：「If you are unable to find an answer in the given relevant documents, do not cite sources from elsewhere in the conversation context.」
- Zendesk（`sources-arch/zendesk-knowledge-reply.txt`）：「If no relevant knowledge is found, the AI agent informs the customer that it can’t answer their question.」
- 知識題不做成流程：Intercom（`sources-arch/intercom-fin-procedures.txt`）「Building a Procedure for a single-question FAQ (like "What are your business hours?") creates a rigid experience.」

### 2.5 轉人與收尾（L5）→ 原則 P7

- Intercom（`sources-arch/intercom-fin-escalation.txt`）：「Escalation Rules and Guidance decide when escalation happens. Workflows decide what happens next.」「In some cases, Fin sends a message offering escalation instead of escalating immediately.」「However, Fin will never offer escalation twice in a row.」
- Intercom（`sources-arch/intercom-conversational-fin.txt`）：「If the customer clearly requests human support, Fin escalates directly.」「If the customer is stuck in a loop, Fin will offer to escalate.」使用者表示已解決的方式：「Indicate that Fin has answered their question by responding positively (e.g., “That helped,” “Yes,” or “OK, thanks”).」
- Rasa（`sources-repair/rasa-patterns.txt`）：`pattern_completed`「Flow that asks if the user needs more help after completing their initiated use cases」；轉人的預設是告知無法協助：「Currently, the default behaviour for a human handoff is to inform the user that the assistant cannot help with the request.」文件另給覆寫 `pattern_human_handoff` 的範例，先以 `collect: confirm_human_handoff` 確認再轉。
- Intercom Procedures（`sources-arch/intercom-fin-procedures.txt`）：「Fin will escalate the conversation if it detects the conversation is not making progress, is in a loop, or if the customer explicitly asks for a human agent.」
- Zendesk（`sources-arch/zendesk-generative-procedures.txt`）：流程走不下去時「the AI agent clearly indicates that the procedure has ended so the customer isn’t left waiting.」

### 2.6 回話層（L6）→ 原則 P2、P3

- Google（`sources-arch/google-generative-vs-deterministic.txt`）：「you can decide whether and how language models are used for agent responses」——回覆是否由模型產生是可選的設計點。
- **第一原理（查無業界逐字對應）**：使用者看到的「請確認」「已完成」「已轉真人」若與系統狀態不符，使用者會依錯誤狀態行動（不按鈕、以為已辦好）。由 2.1 Rasa「don’t guess your business logic」推導：**帶狀態的句子只由程式依狀態產生**（P2）；**給模型的資料與給人看的呈現分開**（P3，推導自 2.7 內容與呈現分離）。

### 2.7 呈現層（L7）→ 原則 P8

- MCP 規格（`sources-card/mcp-tools-latest.txt`）：「Structured content is returned as a JSON value in the structuredContent field of a result.」「For backwards compatibility, a tool that returns structured content SHOULD also return the serialized JSON in a TextContent block.」
- Adaptive Cards（`sources-card/ms-adaptive-cards-overview.txt`）：「Card Authors own the content, Host App owns the look and feel」；fallbackText（`sources-card/adaptive-cards-schema-AdaptiveCard.txt`）「The text that should be displayed if the client is not able to render the card.」
- Rasa（`sources-card/rasa-responses.txt`）：「it is up to the implementation of the output channel how to display the defined buttons」。

### 2.8 原則總表（每份計畫引用這裡的編號）

| 原則 | 內容 | 層 | 業界依據 |
|---|---|---|---|
| **P0** | **混合式：理解交給 AI；有規則、有後果的環節由程式掌握**（環節分工見檔首表）；P1～P8 為其展開 | 全部 | 2.1 |
| P1 | 寫入全程（建立→確認→更正→送出／取消→收據）由程式持有；動作差異只在動作宣告 | L2 | 2.1、2.3 |
| P2 | 說出口的狀態（請確認、已完成、已取消、已轉人）只由程式依實際狀態產生 | L6 | 2.6 第一原理 |
| P3 | 給模型的資料與給人看的呈現分開 | L6 | 2.6 第一原理、2.7 |
| P4 | 在程式掌握的環節，理解層輸出結構化指令（寫入意圖、更正、取消、選擇、要真人、已解決），下一步由程式決定；知識作答與一般對話不經指令層 | L1 | 2.1 |
| P5 | 對話修補（更正、取消、中斷回原流程、澄清、候選選擇、處理不了）是共用模式，所有程式掌握的流程共享 | L3 | 2.2 |
| P6 | 知識題只依核可知識作答；不足時說明＋部分回答＋追問；查無走「處理不了」 | L4 | 2.4 |
| P7 | 轉人與收尾由規則決定：明確要求直接轉、卡住先詢問且不連發、道謝即收尾 | L5 | 2.5 |
| P8 | 本系統出結構化內容（卡、按鈕、狀態）＋文字備援；外觀由接入方決定 | L7 | 2.7 |

## 3. 差距（現況，2026-10-18 對碼；可重跑）

查證指令皆在 repo 根目錄執行。

| 原則 | 現況 | 查證 | M0 量到的後果（`~/jgb-archive/arch-step3-20261018/m/report-m0.md`） |
|---|---|---|---|
| P4 | **沒有指令層**：模型在 `_run_model_loop` 自由選工具、自由寫句子、自填 `kind`／`ask_target`／`handoff_reason`；寫入另有一支意圖呼叫 `_start_write_intent_call`（輸出 `write_intent`，DSP-085）——是寫入專用的指令雛形，知識、查詢、轉人沒有 | `grep -n "def _run_model_loop\|def _start_write_intent_call" rag-orchestrator/services/agent/runtime.py` | 同句首已給物件仍被追問（W-R4 k2，根因待 A0） |
| P1 | 草稿出卡即清（G1）；「修改」與取消同一路（G2）；無卡後更正（G3）；enum 由模型填代碼（G4）；送出前預檢缺（G6）；同 session 可並存多張可兌現卡（`PENDING_CONFIRM_MAX = 20`）；一般寫入回合的模型自呼 `confirm.request` 只當提議、出卡由程式依草稿觸發（A+，`AGENT_WRITE_PROPOSAL` 等三開關皆 on），**文件回合、文件暫存回合、點選範圍回合仍以模型參數出卡**（點選範圍由 A-2、文件回合由「文件回合」片接手；§3.1 KD-1、KD-2） | 第 3 步計畫 §3 G1～G6；`grep -n "PENDING_CONFIRM_MAX =" rag-orchestrator/services/agent/runtime.py rag-orchestrator/services/agent/agent_session.py`；`grep -n "def _write_proposal_handle\|SELECT_SCOPE_KEY) is None" rag-orchestrator/services/agent/runtime.py` | 延期 0/10；只列 5 張帳單 13 場；急迫程度相反 6 場；反覆「還需要」11 場 |
| P5 | 更正：只有草稿內同欄覆寫（`_write_draft_merge_intent`）。取消：有（`CANCELLED_TEXT`）。**中斷回原流程：無**——單一草稿，換動作由 `_write_draft_target` 新建、舊的丟棄，無流程堆疊。澄清：有固定句 `ASK_TARGET_TEXT`。候選：只有按鈕 `select:` fullmatch（G5），打字挑選無程式路徑（純 4～9 位數字走 `_pre_lookup_trigger`） | `grep -n "def _write_draft_target\|def _pre_lookup_trigger\|_SELECT_VALUE_RE = re.compile" rag-orchestrator/services/agent/runtime.py` | 換錯帳單 2 場（W-D4 k2 已寫入 760897）；I-1 插問未答 |
| P2 | 寫入情境回合（草稿存活或 session 有綁定卡）的回話由程式依狀態產生（`_write_reply_state`：卡仍有效、卡未變、卡不同、缺欄追問、未送出、無待確認），只重出既有卡、⛔ 出新卡；提議未發、程式呼叫非終結由程式結束回合（`_write_reply_kd3_exit`）；問句回合模型的 `answer` 可送、程式接狀態行（`_write_reply_model_plus_status`），`ask`／`recommend` 一律換成程式回話；以上依賴 A+ 出卡開關。每則模型撰寫的回覆在一般出口前經帶狀態句判讀閘（`_state_claim_gate`：LLM 判讀等待確認／已完成／已取消／已轉人四類，對不到程式狀態事件即換程式句；判讀失敗時可出卡的回合 fail-closed）；`prose_confirm_suspect` 結構條件直接視為未對到。開關 `AGENT_WRITE_REPLY_PROGRAM`、`AGENT_STATE_CLAIM_GATE`（未設＝on）。Verifier 本身仍不比對狀態（G7）；確認卡與收據是程式文字（DSP-038） | `grep -n "def _write_reply_state\|def _write_reply_kd3_exit\|def _write_reply_model_plus_status\|def _state_claim_gate" rag-orchestrator/services/agent/runtime.py`；`grep -n "def judge_state_claims" rag-orchestrator/services/agent/state_claim.py` | 文字說請確認卻未出卡 ≥4；按確認但無按鈕 7；假收據 1（C-C k1） |
| P3 | 候選清單分給模型與給人兩份：給模型的 `_candidates_text` 含提示句（`CANDIDATES_MODEL_HINT_HEADER`／`FOOTER`），給人的 `candidates_text_for_user` 只列程式解析出的列值；資料段注入 10 處（`TurnAccumulator.inject`，註解仍寫「九段」） | `grep -n "def _candidates_text\|def candidates_text_for_user" rag-orchestrator/services/agent/tools/jgb2.py`；`grep -n "acc.inject(" rag-orchestrator/services/agent/runtime.py` | 給人的回覆夾內部提示（第 2 步報告） |
| P6 | 知識只來自正本目錄＋細目，`reviewed` 為唯一門（DSP-066）；Verifier 引用類只觀察不擋（DSP-040，`grounding_observe`）；部分回答＋說缺什麼已做政策文（`a6df614c`）；查無多走轉人固定句；**Verifier 步⑦ 的轉人字眼 `HANDOFF_WORDS` 含「沒有資料」且屬安全類（照擋）**——AI 說明缺什麼而本回合未轉人會被拒 | `grep -n "_OBSERVED_CLASSES_BY_MODE" rag-orchestrator/services/agent/verifier.py`；`grep -n "^HANDOFF_WORDS" rag-orchestrator/services/presales_gate.py`；`grep -n '"HANDOFF_WORD_NO_HANDOFF": "safety"' rag-orchestrator/services/agent/verifier.py`；AGENTIC_MCP §4b | 知識嚴格解決 11/20；缺必要事實 5 場；第 2 步捏造 10/36 |
| P7 | 轉人有五個來源（模型自報、預算耗盡、範圍退出、程式降級、工具查無）；**無「先詢問再轉」、無收尾模式**——查 `還有什麼\|還有其他\|還需要其他` 於本目錄只命中 `runtime.py` 一行註解（正對照：查法有效），程式無收尾句；有連續固定句計數 `fixed_streak`（用途未查） | `grep -rn "還有什麼\|還有其他\|還需要其他" rag-orchestrator/services/agent/`；AGENTIC_MCP §4b | 道謝後轉真人 3 場 |
| P8 | `/mcp` 回七鍵 `AgentTurnOutput`（`structured_output=True`），卡只以文字放 `answer`，門面不轉發 `card`；按鈕為 `quick_replies {label, value}` | `grep -n "class AgentTurnOutput\|structured_output=True" rag-orchestrator/services/agent/mcp_facade.py` | 接入方只能顯示文字卡（第 3 步計畫 G9） |

M0 缺陷 → 原則對照（AR1）：延期列 5 張→P1（A0 根因）；換錯帳單→P5；急迫程度相反→P1；反覆還需要→P1／P4；無按鈕、文字請確認、假收據→P2；物件名截短→P4（A0 根因）；道謝轉人→P7；知識缺事實→P6；無結構卡→P8。九類全有對應。

### 3.1 仍由模型主導（已知偏離）

檔首分工表「程式」列中，下列環節目前仍可能由模型決定下一步。每筆登記在 `rag-orchestrator/tests/unit/agent/dsp091_known_deviations.py`，各有一支現況探針（`test_dsp091_division_contract_req.py`）；偏離被修掉時探針失敗，接手片須把該筆移出本表與登記、改成必過契約。本表與登記不一致時 `make audit` 不變量 45 判 FAIL。

| ID | 偏離 | 分工表列 | 接手片 |
|---|---|---|---|
| KD-1 | 點選範圍、唯讀檢視回合：模型自呼 `confirm.request` 的參數照舊執行出卡 | 寫入全程、已選定的那筆紀錄 | A-2 |
| KD-2 | 文件回合、文件暫存有效回合：模型參數出卡；文件程式發卡的非終結結果交回模型 | 寫入全程 | 文件回合 |
| KD-5 | 轉人由模型輸出決定，出口閘只在模型選了轉人後介入；無收尾規則 | 轉人規則（含收尾） | E |
| KD-6 | 知識完全查無沒有程式先發的出口 | 知識完全查無的出口 | D |
| KD-7 | 唯讀查詢的參數由模型自呼工具決定 | 唯讀查詢的查詢與篩選 | G |
| KD-8 | 打字挑選候選無程式路徑 | 已選定的那筆紀錄 | A-2 |

## 4. 路徑（分片；每片寫出服務的原則）

**方向**：目標形態是 §2 的完整分層；路徑採漸進——每片把一條原則推到位，每片前後用同一量尺量，⛔ 一次重寫成流程引擎（DSP-091）。理由：現有寫入鏈的安全性質（雙雜湊、token 單次、範圍閘，DSP-038／042）已驗證，整換要全部重驗；一次換無法把解決率變化歸因到單一改動。指令層（P4）排後面，是因為 P1／P2 的缺陷造成 M0 最大損失（延期 0/10），P4 的效果要等流程層就位才量得到——依使用者效果排序。

| 片 | 做什麼 | 原則 | 鎖定的 M0 缺陷 | 狀態（詳 HANDOFF） |
|---|---|---|---|---|
| M | 量尺修正＋M0 基線 | （量尺） | — | 完成 |
| A | 寫入全程由程式持有：A0 根因、A1 草稿生命週期、A2 卡後更正、A3 修改鍵、A4 enum 由程式轉碼、A6 宣告式預檢、A7 唯一有效卡、A8 單一動作登錄 | P1、P5（更正） | 延期列 5 張、急迫程度相反、反覆還需要、卡後改欄位、按修改 | 已收案：計畫 `plan-conversation-architecture-step3-20261018.md`、驗收 `acceptance-conversation-architecture-step3-20261018.md`；報告 `~/jgb-archive/arch-step3-20261018/ra/report-ra.md` |
| A+ | 出卡只由程式依草稿觸發：收掉模型自己呼叫 `confirm.request` 出卡的路徑，模型改為提出寫入意圖 | P1、P4 | 反覆還需要（模型自呼路徑） | 計畫 `plan-card-program-only-aplus-20261019.md`、凍結驗收 `acceptance-card-program-only-aplus-20261019.md`（2026-10-19 業主核可；2026-10-20 已收案，fresh verifier CONFIRMED）；報告 `~/jgb-archive/arch-step3-20261018/aplus/report-aplus.md` |
| DG | 分工防偏離：DSP-091 分工契約測試＋已知偏離登記（§3.1）＋`make audit` 不變量 45（確認卡與缺欄追問的來源） | P0 | —（防止已接手環節退回模型） | 計畫 `plan-division-guard-20261020.md`、凍結驗收 `acceptance-division-guard-20261020.md`（2026-10-20 業主核可） |
| A-2a | 寫入時名稱對到多筆紀錄（例：合約同名兩筆）由程式列出候選，使用者選定後回原流程；範圍與選定方式由該片計畫定（DSP-101） | P5、P1 | 反覆還需要（合約同名）；B 後合約同名候選清單可見 20/20 → 13/20 | 待出片（B 之後、W2 之前） |
| A-2 | 候選選擇的其餘部分（A-2a 以外的打字挑選、挑完回原流程） | P5 | 換錯帳單 | 待 A 後出片，先送 security-reviewer |
| 文件回合 | 文件回合、文件暫存有效回合的出卡改由程式依草稿觸發；文件程式發卡的非終結結果不交回模型（§3.1 KD-2；須相容 DSP-076 文件值暫存規則） | P1 | —（KD-2） | 待出片 |
| B | 寫入進行中回話全由程式樣板；工具結果分給模型／給人兩份 | P2、P3 | 文字請確認、無按鈕、假收據、回覆夾內部提示 | 計畫 `plan-b-write-replies-program-20261020.md`、凍結驗收 `acceptance-b-write-replies-program-20261020.md`（2026-10-20 業主核可；同日收窄宣稱收案，fresh verifier CONFIRMED，DSP-100）；報告 `~/jgb-archive/arch-step3-20261018/b/report-b.md` |
| E | 收尾與轉人規則：道謝即收尾、卡住先詢問且不連發、明確要求直接轉 | P7 | 道謝轉人 | 待 B 後出片 |
| D | 知識不捏造／完整：不足時由 AI 說明缺什麼、部分回答、追問（Verifier 把關依據；步⑦ 不再把「說明缺什麼」當轉人字眼擋）；完全查無走程式的「處理不了」出口 | P6 | 知識缺事實、捏造 | 另起計畫 |
| C | `agent.turn` 加結構化 `card`，`answer` 留文字備援；JGB 端需求稿 | P8 | 無結構卡 | 待出片（跨元件） |
| G | 唯讀查詢由程式執行：AI 理解出查詢條件，程式查詢並篩選（依期別篩帳單等日期計算），AI 自呼工具只在程式接不住時用（進入條件寫進計畫）；起點為 W3 草稿 `plan-query-program-led-w3-20261017.md` | P0、P4 | 換錯帳單 | 待出片 |
| F | 程式掌握環節的指令化：把 `write_intent` 推廣為更正、取消、選擇、要真人、已解決等指令；含中斷回原流程（流程堆疊） | P4、P5 | 插問未答、物件名截短 | A／B 驗收後評估 |
| W2 | 主模型輸出失控（灌空白至輸出上限）處置：system 明示只輸出 JSON＋串流早停後走現行重寫；整回合逾時切斷進行中的呼叫；備援模型後議 | （執行層韌性，不屬分層原則） | A 後 20 場失敗中 6 場主因 | 計畫 `plan-truncation-w2-20261017.md`、驗收 `acceptance-truncation-w2-20261017.md`（DSP-094、DSP-095） |
| 期別 | 期別年份解析：「YYYY年M月」年份被丟、推成最近的過去月份 | P1 | A 後 20 場失敗中 8 場主因 | 計畫 `plan-period-parse-20261019.md`、驗收 `acceptance-period-parse-20261019.md`；含期別值閘改比對解析值（DSP-094） |

順序：A → 期別 → A+ → DG → B → A-2a → W2 → E → D → C → G → A-2 → 文件回合 → F（DSP-101）。上線最低範圍：A、期別、A+、B、A-2a、E、W2（DSP-101）。

不在範圍：業者端敏感題程式防線（另案）。

## 5. 防歪機制（AR3）

1. **本檔是目標唯一正本**：登在 `.claude/MAP.md` `#agentic-mcp`；`AGENTIC_MCP_ARCHITECTURE.md` 開頭一行指向本檔。
2. **每份計畫必引原則**：計畫 §1 寫「服務原則：P?」與本檔章節；路徑每項標原則；plan-verifier brief 固定加必查項「每個範圍項目對得到本檔一條原則，對不到即缺項」。
3. **改原則先改本檔**：新增、刪除或改寫原則，先改 §2.8 與檔首分工表交業主核可，並記一條 DECISION；⛔ 在單片計畫裡另立原則。
4. **差距表隨片更新**：每片收尾時改 §3 該原則那一列的「現況」（附新查證）；進度只寫 HANDOFF。
5. **改正文、不留錯誤原文**（AR8）：決策或事實改變時直接改正文；過時且無用的文件刪除；⛔ 以附註、刪除線或「已失效」標記保留錯誤內容。
6. **既有決策優先**：與 §6 決策衝突的做法，先列待裁，⛔ 自行繞過。
7. **過渡修正**：程式接手某環節之前，只修現有模型主導路徑上的錯、不新增 AI 決定權，不算違反分工；計畫須寫明「過渡修正、不新增 AI 決定權」並指向將接手的那一片（如 A+、G）（DSP-091）。
8. **自動檢查**：檔首分工表「程式」列由 `rag-orchestrator/tests/unit/agent/test_dsp091_division_contract_req.py` 檢查——已接手的列是必過契約，尚未接手的列登記在 `dsp091_known_deviations.py`（＝§3.1）並各有現況探針；`make audit` 不變量 45 核對 §3.1 與登記一致，並在一般寫入回合出現來源不明的模型出卡（`confirm_source:model:unregistered`）時 FAIL。每片收尾時，把它接手的 KD 移出 §3.1 與登記、改成必過契約、改程式註解。

## 6. 與既有決策的相容（`.claude/DECISIONS.md`）

| 決策 | 對本檔的約束 | 本檔處置 |
|---|---|---|
| DSP-091 | 混合式分工 | 檔首分工表、P0 |
| DSP-085 | 寫入程式掌握流程；⛔ 只加提示詞 | P1；F 片把 `write_intent` 推廣時須記新 DECISION |
| DSP-038 | 確認卡由程式 formatter 逐字成為 `answer`，⛔ 經模型／Verifier；雜湊綁卡 | P1、P2 保留；P8 的結構化卡由同一 formatter 另出資料形狀，文字照舊 |
| DSP-042 | `select:` 在模型前攔截；⛔ 讓模型抽 id | P5 打字挑選由程式比對，⛔ 經模型 |
| DSP-043 | `outcome` 由程式設 | P2 把同原則延伸到答案文字 |
| DSP-011、074、D-002 | 授權在上游；b2b ⛔ 補 `IS NULL` | 本檔不動授權與隔離 |
| DSP-009 | 敏感五類固定句轉人、⛔ 補知識 | P7 規則保留此項為「直接轉」 |
| DSP-040 | 引用類只觀察、機敏類照擋 | P6 的依據檢查是否改成擋，由 D 片依觀察紀錄提案，⛔ 本檔逕改 |
| DSP-066 | 只有 `reviewed` 細目進模型 | P6「只依核可知識」即此門 |
| DSP-087 | 先代理量測、Intercom 式解決率 | §1 量法 |
| R4.2 | `confirm_edit` 語意未定義 | A3 定義，須記一條 DECISION |

## 7. 待業主裁

目前無。

## 8. 本檔驗收清單

| # | 規則 | 宣稱 | 觀察點 | 證據 | 通過條件 |
|---|---|---|---|---|---|
| 1 | AR1 | 涵蓋七層、M0 九類缺陷皆有原則 | 本檔 §2、§3 末段 | 逐類對照 | 九類全對到 P1～P8 |
| 2 | AR2 | 四步順序；業界宣稱附原文 | 本檔 §1～§4 | 對每句引文在所列檔 `grep -F` | 全部命中；查無業界者標「第一原理」 |
| 3 | AR3 | MAP 登記、現況文件指向本檔、計畫必引原則 | `.claude/MAP.md`、`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`、§5 | grep 本檔檔名 | 兩處各命中；§5 有必查項 |
| 4 | AR4 | HANDOFF 指向本檔 | `HANDOFF-20261018.md` | grep 本檔檔名 | 命中 |
| 5 | AR5 | 原則無動作名分支 | §2.8 | 讀表 | 無動作名、欄位名條件 |
| 6 | AR6 | P8 寫明結構化＋文字備援＋接入方呈現 | §2.7、§2.8 | 讀表 | 三要素皆在 |
| 7 | AR7 | 分工、目標、基線、每片驗收、每片原則與狀態都寫明 | 檔首、§1、§4 | 讀檔 | 五項皆在 |
| 8 | AR8 | 相關文件無與 DSP-091 相反的現行陳述；設計提案 v2、HANDOFF-20261017 已刪且無失效引用 | `grep -rnE "決策搬進模型|自選工具|決策在模型|由模型做|模型自己決定|程式替它決定|agentic-tool-selection-design|HANDOFF-20261017" .kiro/specs/agentic-mcp-orchestration/*.md .kiro/specs/agentic-mcp-orchestration/spec.json .claude/MAP.md docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`（正對照：同目錄 grep `DSP-091` 應命中本檔） | 輸出逐條判讀 | 剩下的命中只出現在敘述歷史、已凍結紀錄或 `git show` 指標 |
| 9 | AR9 | MAP 登記與指標 | `.claude/MAP.md` | grep 本檔、`HANDOFF-20261018.md`、`DSP-091` | 三者皆命中 |
| 10 | AR10 | 分工表照 A | 檔首表、`.claude/decisions/DSP-091.md` 業主原話與追加裁示 | 逐項對照 | 相同（含追加裁示） |
| 10b | AR8 | 轉人、查無出口與出卡的現行規範不交給模型決定 | requirements.md、design.md 全檔逐句讀（grep 只當補充：`grep -n "handoff\|轉人\|confirm.request\|出卡" .kiro/specs/agentic-mcp-orchestration/requirements.md .kiro/specs/agentic-mcp-orchestration/design.md`，正對照：requirements.md 必命中 R7.1） | 逐句判讀 | 每處是工具定義、已完成任務紀錄、處置紀錄，或寫明「模型提出、程式依規則決定」；現況與目標不同處指向 §3 |
| 11 | AR1～AR10 | 獨立審查 | fresh plan-verifier（設計方法必查項） | 報告 | READY，或依規則處置後交業主 |
