# 計畫：寫入流程由程式掌握（2026-10-17，r5）

> 業主原話（2026-10-17）：「修繕 不能延續處理了嗎」「像是品質是不參考 要寫規則 這會不會也是類似問題」「但是需要通用處理 不能局部補丁」；方向選擇：「程式掌握流程」。
> 驗收清單（凍結）：`.kiro/specs/agentic-mcp-orchestration/acceptance-write-flow-20261017.md`
> r2：依 plan-verifier r1（REVISE，9 條）與 security-reviewer 修訂；r3：依 plan-verifier r2（REVISE，7 條）處置並簡化；r4／r5：依業主「修完再審一輪」處置 r3（6 條）、r4（2 條）；r5 後：處置 r5（2 條，皆驗收題目與計畫自洽問題）。處置表見 §6。

## 0. 根因（皆已對碼，可重跑）

| 事實 | 查證 |
|---|---|
| 架構文件自承「**寫入面出卡與否綁模型**：無程式面下限保證出卡一定成功」 | `grep -n "寫入面出卡與否綁模型" docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` |
| 程式追問、物件記憶、補缺值都通用，但全部掛在「模型已呼叫 `confirm.request`」之後 | `grep -n "missing_fields_ask_text(tool_result)" rag-orchestrator/services/agent/runtime.py`（條件 `name == CONFIRM_TOOL_NAME`） |
| 5 支寫入動作只有 3 支有共用欄位表；修繕另一套；延期繳費缺欄時走 `render()` 失敗、回不帶 `missing_fields` 的 `INVALID_INPUT`，程式不追問 | `grep -n "^CLOSED_ACTION_FIELDS" rag-orchestrator/services/agent/confirm_card.py`；`grep -n "REPAIR_MISSING_LABELS\|async def _resolve_bill_by_period" rag-orchestrator/services/agent/tools/confirm.py` |
| runtime 寫死修繕欄位字面 | `grep -n '"物件" in _missing' rag-orchestrator/services/agent/runtime.py` |
| 程式自己發一次 `confirm.request` 走同一條工具迴圈的機制已存在（謄本回合專用） | `grep -n "class _ProgramMessage\|DOCUMENT_PROGRAM_CONFIRM_SUMMARY" rag-orchestrator/services/agent/runtime.py` |
| 對話歷史每回合有送進模型，gpt-oss 仍不把前面講過的物件帶進流程 | `grep -n "def _append_dialog" rag-orchestrator/services/agent/turn_context.py`；`~/jgb-archive/bedrock-eval-20261017/s1/s1_B.json`（`set=="R"`） |

結論：缺的是「**程式面下限**」。修法是由程式掌握「要不要進寫入流程、還缺什麼、何時出卡」，模型只負責「抽出使用者話裡的欄位值」與「講話」。業界同型做法：Rasa CALM「business logic … implemented as a set of flows」「Flow Policy is a state machine that deterministically executes the business logic」（2026-10-17 渲染官方文件）。

## 1. 計畫範圍（program envelope）與終點指標

目標：**任何寫入動作**的多輪收欄位到出確認卡，不依賴模型主動呼叫工具；換模型不影響流程。

**終點指標**（來源 `~/jgb-archive/bedrock-eval-20261017/s1/s1_A.json`、`s1_B.json`；第二支動作現值於執行第 0 步量）：

| 指標 | 現值 | 預期 |
|---|---|---|
| gpt-oss 報修三步出卡率 | 0/3 | 3/3 |
| gpt-oss 延期繳費三步出卡率 | 執行第 0 步量 | 3/3 |
| gpt-6-luna 報修三步出卡率 | 3/3 | 3/3（不退步） |

本計畫只有一片可執行（W1）；查詢工具（`jgb2.query.*`）同類問題列為後續（§5）。

## 2. 第一片 W1：寫入草稿由程式掌握

### 2.0 前置（未滿足不開工）

1. **OSS 第一片先 commit**（業主核可本計畫時一併授權；只含 `rag-orchestrator/services/agent/runtime.py`、`docker-compose.prod.yml`、`rag-orchestrator/tests/unit/agent/test_output_cap_and_ask_target_desc_req.py`、`plan-oss-slice1-20261017.md`、`acceptance-oss-slice1-20261017.md`）。W1 的基準＝該 commit；執行紀錄寫明 hash。
2. 執行第 0 步：在**改動前**以評估容器量延期繳費腳本（驗收 #2 的逐句輸入）A、B 各 ×3，得現值；並以 `jgb2.query.bills` 確認「基隆溫馨一人宅套房」2026 年 11 月帳單（fixture id 709744，status 1）可查到。查不到 ⇒ 改用驗收 #2 的 `contract_create` 備案腳本，執行紀錄寫明理由。
3. 基線紅燈：全量單元測試已知 9 條失敗（`HANDOFF-20261017.md` §1.3）；執行第 0 步存名單於 `~/jgb-archive/bedrock-eval-20261017/w1/baseline_red.txt`。

### 2.1 做什麼

**(1) 一張表宣告 5 支寫入動作的表單**（新檔 `rag-orchestrator/services/agent/write_forms.py`）

- 欄位屬性：鍵、中文標籤、型別（`text`／`int`／`number`／`date`／`email`／`phone`／`enum`／`sys_id`／`category`）、來源（`user_words`＝使用者口述；`system`＝系統解析或程式導出）、追問對象 `ask_target`。
- 必填以**替代組**表達：`required_any_of = [[鍵…], [鍵…]]`（任一組全給即滿足），並指定**追問用的那一組**（`ask_group`）。單一必填＝只有一組。例：`bill_due_extend` 必填＝`days` 且（`[bill_id]` 或 `[estate_name]`）——照現行程式（`_resolve_bill_by_period` 只檢查 `estate_name`；`_filter_bills` 在沒講期別時不篩，唯一帳單直接出卡、多張出候選）；追問組＝`[estate_name, period]`（缺物件時一併請使用者講期別；依 `BILL_DUE_EXTEND_SPEC`「⛔ 不為了取得帳單編號反問使用者」）。期別**不是**必填（`BILL_DUE_EXTEND_SPEC` 文字寫期別代替必填，與程式不一致，已記 `dispute.py` 待業主裁；本片照程式）。
- 3 支封閉動作**由 `CLOSED_ACTION_FIELDS`／`CLOSED_ACTION_ANY_OF`／`_REF_ALTERNATIVES` 導出**（⛔ 另抄一份）；`repair_create`、`bill_due_extend` 在本檔新宣告，**必填判準照現行程式行為**（⛔ 改行為）：修繕「問題描述」去空白後為空＝缺（沿用 A9，`confirm.py` 現行 `not payload.get(key).strip()`）。⚠️ 這與 `REPAIR_CREATE_SPEC` 文字「允許是空字串」不一致，已記 `dispute.py` 待業主裁；本片不改 SPEC 文字、也不改程式語義。
- **5 支動作的缺欄計算一律走同一個函式** `missing_labels(action, payload)`：`confirm.request` 在 `render()` 之前呼叫它，缺 ⇒ 回 `INVALID_INPUT`＋`data.missing_fields`（中文標籤）。封閉動作的既有 `missing_required_labels` 改為呼叫它（輸出逐字不變，測試鎖住）；**呼叫點不動**——封閉動作仍在 `_prepare_closed_action` 的受眾檢查與 `check_closed_keys` 之後才算缺欄（非業者照舊先得 `NO_MATCH`）。刪除 `REPAIR_MISSING_LABELS` 與 confirm.py 的 `if action == "repair_create":` 缺欄區塊。
- `_MISSING_LABEL_VOCAB` 與 runtime 缺欄追問的 `ask_target` 對映都由表導出；刪除 runtime 的 `"物件" in _missing` 字面。`ask_target` 推導規則**與現行結果逐位相同**（由表驅動）：缺欄中有宣告 `ask_target=estate` 的欄位 ⇒ `estate`；否則恰缺一欄且該欄有宣告 `ask_target` ⇒ 該值；其餘 ⇒ `None`。表內宣告：物件名稱欄位（`estate_name`）＝`estate`、修繕問題描述＝`description`，其他欄位皆 `None`——對修繕與封閉三動作即重現現行「`"物件" in _missing` ⇒ estate／只缺問題描述 ⇒ description／其餘 None」。
- **行為變更（明列）**：缺欄統一後，`bill_due_extend` 缺 `days` 時，不論草稿或模型自己呼叫，都改回 `missing_fields`、由程式追問（現行為不帶 `missing_fields` 的 `INVALID_INPUT`、交回模型）。這是本片刻意改到模型自呼路徑之處；表驅動的直接結果還有一處：`bill_due_extend` 同時缺 `bill_id` 與 `estate_name` 時也改回 `missing_fields`（驗收 #3 要求，執行時由 security-executor 指出補記）。gpt-6-luna 在腳本 D 的表現由驗收 #4 量測。
- 表內 `ask_target` 只能取**既有** `ASK_TARGETS` 或 `None`（⛔ 新增值域，保住 off 時 schema 逐位相同）；沒有合適值的欄位（例：延後天數、期別）填 `None`——與現行 `_finish_confirm_turn(ask_target=None)` 對非修繕缺欄的行為相同。
- **草稿值 → payload 值的正規化**（5 支共用函式 `to_payload(action, fields)`）：`int`／`number` 轉數值（`days` 等轉 int）、`date` 轉 `confirm_card._parse_date` 收的 `YYYYMMDD`、`enum` 依表內各欄位宣告的 **payload 型別**轉（`emergency_status` ⇒ int 1／2，對 `confirm_card._EMERGENCY_ZH` 的整數鍵；封閉三動作的 enum 仍為字串，照 `_closed_value`）、其餘照原字串；轉換失敗的欄位視為缺（進缺欄追問）。
- 啟動斷言：表單動作集合＝`CONFIRM_ACTIONS`＝`ACTION_SPECS` 的動作名（少一支即大聲失敗）。

**(2) 模型輸出新增 `write_intent` 欄位**

- `AgentOutput.write_intent: Optional[WriteIntent] = None`（pydantic 預設 None ⇒ 既有假輸出不帶此欄仍能解析）。
- 形狀：`null` 或 `{action: <5 支動作名 enum>, fields: [{key: <表內 source=user_words 與 enum/category 型別欄位鍵 enum>, value: string}]}`。**`system` 來源的鍵（`estate_id`、`contract_id`、`bill_id`⁽¹⁾、`date_expire_before/after` 等）不在 enum 內**，模型無法經此填。
  - ⁽¹⁾ `bill_id`：使用者口述編號屬 user_words；表內標 `int` 型、依 (3) 的數字閘驗。
- 說明文字：使用者這句是要建立／變更系統資料，或在回答「進行中的建立」時填；`value` 只填使用者原話裡出現的值，⛔ 推測、⛔ 代寫；改談別的事時填 `null`。**說明文字內列出動作名與各動作可填的鍵（由表單產生）**——比照 `ask_target` 說明列值域的作法（`_agent_output_response_format` 註解：gpt-oss 不讀 enum）。
- **pydantic 端 `WriteIntent.action`／`fields[].key`／`value` 一律開放字串**（理由同 `AgentOutput.ask_target` 刻意 `Optional[str]`）：值域外的動作或鍵由程式丟棄並記 violation `write_intent_out_of_domain`，⛔ 讓整份 `AgentOutput` 被拒（避免 SCHEMA 重寫吃光預算、波及知識題）。
- `AGENT_WRITE_DRAFT=on` 時 `_agent_output_response_format` 才把 `write_intent` 放進 strict schema；`off` 時 schema 與現行逐位相同（驗收 #6 鎖住）。

**(3) 會話草稿 `write_draft`**（`state["agent"]` 新鍵，經 `AgentSession` 讀寫）

- 內容：`{action, fields: {key: value}, idle_turns, created_by_role}`；⛔ 存 token、⛔ 存系統解析的**編號類**值（`estate_id`／`contract_id`／`bill_id` 解析結果）；唯一例外是 (4) 由前置查詢唯一命中寫入的物件**名稱**。
- **值的閘（寫入草稿前一律過；模型自己呼叫 `confirm.request` 的 payload 合併進草稿時也過同一道閘）**：

  | 型別 | 規則 | 不過 |
  |---|---|---|
  | `text` | 正規化（去空白）後為本會話使用者訊息（`dialog` 的 user 端＋本句）之子字串；並過 `sanitize_data_piece` 不變 | 丟棄＋violation `write_intent_value_not_in_user_words` |
  | `int`／`number` | 字串轉數值後，沿用既有 `runtime._number_in_texts`（完整數字 token 出現在使用者原話；國字數字不收 ⇒ 改由程式追問，偏保守） | 同上 |
  | `date` | 使用者訊息中可解析出同一日期：`YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY年M月D日／號`（有年份時用使用者講的年份）、`M月D日／號`（無年份時取今年或明年中第一個不早於今天者）；有年份的寫法先比對，避免被 `M月D日` 截斷 | 同上 |
  | `email` | 兩邊都只去空白（⛔ 去連字號）後，模型值為使用者訊息子字串；草稿存模型給的原值 | 同上 |
  | `phone` | 兩邊都去空白與連字號後比對；草稿存模型給的原值 | 同上 |
  | `enum`（例：`emergency_status`） | `value` 須在表內封閉值域（`emergency_status` ∈ {"1","2"}，照 `REPAIR_CREATE_SPEC`）；⛔ 加語意詞表比對（業主「⛔ 補詞表」原則）；**值域內的捏造值（使用者沒說緊急卻填 "2"）本閘擋不到**，由卡面印出急迫程度＋使用者按確認承擔（列 §4 已知風險；與模型自己呼叫 `confirm.request` 的現況同一等級） | 值域外 ⇒ 丟棄＋violation |
  | `category`（`category_name`） | 寫進草稿前即呼叫既有分類樹閘 `_is_valid_repair_category`（封閉詞彙，⛔ 要求原話子字串：口述「冷氣」對上分類「空調」屬既有契約） | 丟棄＋violation `write_intent_category_invalid` |

  ⚠️ 模型自己呼叫 `confirm.request` 的那一次呼叫本身**不改**（非目標：不改 gpt-6-luna 現行出卡路徑）；閘只決定哪些值能留在草稿供之後的回合使用。
  ⚠️ 從模型自己的 `confirm.request` 合併時，**只取模型原始參數**（`json.loads(tc.function.arguments)`，在任何 `_apply_*_to_confirm_args`／`_apply_document_to_payload` 與 `_prepare_closed_action` 就地改寫之前）——照片辨識描述、物件記憶補值、系統解析 id／名稱 ⛔ 進草稿（`IMAGE_SUGGESTION_KEY` 註解「只進修繕單描述，不進模型資料段」）。文件回合（`document is not None`）與 `document_carry` 有效時不合併。
- **可見性閘**：只有在 `registry.specs_for(identity, stage, for_model=False)` 看得到 `jgb2.action.<action>`、且非 `readonly_view` 時，才建草稿、才觸發（比照 `_prepare_closed_action` 的「別的受眾 ⛔ 出一張永遠兌現不了的卡」）；看不到 ⇒ `write_intent` 忽略、記 violation `write_intent_action_not_visible`。
- 合併：同鍵新值覆蓋；丟掉不屬於該動作表單的鍵；`write_intent.action` 與草稿不同 ⇒ 換新草稿。
- **生命週期登記**：`agent_session.KEY_SPECS` 新增 `write_draft`，生命週期 `UNTIL_SCOPE_EXIT`（沿用既有六種之一，⛔ 新增第七種；`scope_exit()` 自動清），封閉表斷言改為 12；其餘清除條件（出卡、閒置、身分、兌現／取消、not_supported）在各自寫點明確呼叫清除。
- **讀回驗形狀**：從 `form_sessions.collected_data` 讀回一律視為不可信——action 須在 `CONFIRM_ACTIONS`、鍵須在該動作表單、值須為字串且截上限（文字欄位沿用表內 `max_len`，`description` 上限 500 字），不合 ⇒ 整份丟棄並記 violation；表單斷言不含 `IDENTITY_OWNERSHIP_KEYS` 任一鍵。
- **釘住範圍**：`SELECT_SCOPE_KEY` 有值時不注入、不觸發（比照 `_estate_carry_of`）。
- 清除：出卡成功（`confirm_pending`）、範圍出口（`scope_exit()`）、`select:` 釘住範圍、身分（`identity.resolved_audience()`／role）與 `created_by_role` 不同、連續 2 回合 `write_intent` 為 null（使用者改談別的）、使用者兌現或取消確認卡、`AGENT_WRITE_DRAFT=off`。
- 注入：下一回合在資料段加一行程式產出的「進行中的建立：<動作中文名>；已有：<標籤>；還缺：<標籤>」——**只放標籤、⛔ 放使用者值**（值已在對話歷史裡，⛔ 再複製一份進 prompt）。經 `TurnAccumulator.inject` 以 **`citable=False`**（會話記憶類，⛔ 可當引用依據）、id 取 `ReservedCallIds` 新增的保留 id（例 `wd-{head}`，回合開頭由 nonce 無條件派生，模型偽造同 id 照既有規則拒收）、文字過 `sanitize_data_piece`；排在 DSP-022 當句使用者訊息之前（既有測試 `test_current_user_message_is_last_message_sent_to_model` 鎖住）。
- **⛔ 不進 trace**：`decision_snapshot`／`usage_events` 只記 `write_draft_action` 與欄位**鍵名**清單，⛔ 記值。

**(4) 追問接回（不靠模型）**

上回合是程式缺欄追問（`LAST_ASK_TARGET_KEY` 對到草稿動作的表內欄位 F），本回合：
- F 為**物件名稱欄位**（表內 `ask_target=estate` 的 `estate_name`；實際走得到的動作＝`repair_create`、`contract_create`、`bill_due_extend`。`manual_bill_create` 缺合約時標籤是「合約」、`ask_target` 為 None，依與現行逐位相同的規則不會追問物件，故不在此路徑），上回合 `LAST_ASK_TARGET_KEY`＝`estate`（屬既有 `_PRE_LOOKUP_NAME_ASK_TARGETS`），且既有前置查詢 `_pre_lookup_trigger(after_name_ask=...)` 對到**唯一**物件 ⇒ 程式把該物件名稱寫進草稿 `estate_name`（拿得到列上 `title` 時用 `title`；單筆命中只拿得到查詢關鍵字時用該關鍵字——見 §4；⛔ 用模型輸出）。⛔ 寫進 `contract_ref`：前置查詢只查物件，合約名稱一律由模型 `write_intent` 提供、過 text 閘。
- F 為 `text` 型且模型 `write_intent` 為同一動作但沒給 F ⇒ 以使用者本句原文填 F。
- 其餘（模型 `write_intent` 為 null 且前置查詢未唯一命中）⇒ 視為改談別的，不填、`idle_turns+1`。

**(5) 程式觸發 `confirm.request`**

- **插入點**：`_run_model_loop` 中「無 tool_calls ⇒ 模型嘗試給最終答案」分支，`AgentOutput.model_validate` 成功之後、`handoff_dict` 組裝與 T2（`HANDOFF_DATA_REWRITE_HINT`）／V2（`RECENT_REFS_REWRITE_HINT`）改寫分支與 `self.verifier.verify` **之前**。
- **條件（全部成立才觸發）**：`AGENT_WRITE_DRAFT=on`；草稿**本回合新建（即使尚無任何欄位，例：「能幫我新增一張修繕單嗎」）**、或本回合有新值、或剛由 (4) 接回——新建無欄位時 `confirm.request` 回缺欄清單 ⇒ 程式追問句，下一回合即符合 (4) 的前提；本回合尚未觸發過；本回合模型未成功呼叫 `confirm.request`；**不是**敏感轉人（`out.kind=="handoff"` 且 `fact_class` 屬敏感五類或 `handoff_reason=="sensitive_no_grounding"` ⇒ 不觸發，轉人優先）；非文件回合（`document is None` 且 `document_writable_action(document)` 為 None——`doc_action` 是工具迴圈內的區域變數，插入點須另算；文件回合維持既有路徑）；`document_carry` 有效且動作不同時不觸發；通過可見性閘；`SELECT_SCOPE_KEY` 無值；**剩餘期限足夠**（`deadline_s − 已用` ≥ 6 秒，涵蓋非終結時多一次模型呼叫；否則不觸發、保留模型原輸出）。
- **呼叫**：組 `_ProgramMessage`（tool_call id 前綴 `wdprog-`＋nonce，不在 `ReservedCallIds` 內；`summary`＝常數 `WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY = "依對話中使用者提供的欄位建立。"`；payload＝`{action, **草稿欄位}`），設為下一輪 `message` 後 `continue`，走**同一條**工具迴圈（範圍閘、`WRITE_NOT_SUPPORTED_ACTIONS`、照片覆寫、物件記憶補值、保留 id 檢查全部照舊）。
- **工具預算**：程式觸發**不計入**、也不受 `tool_call_exhausted` 限制（每回合上限 1 次，故有界）；實作以程式呼叫旗標跳過**所有**該檢查點（迴圈前段與 TOOL_TIMEOUT 重試處兩處），記 violation `write_draft_program_confirm`。
- **結果收尾**：
  - 缺欄（帶 `missing_fields`）⇒ 既有程式追問句結束回合（`ask_target` 由表導出）。
  - 成功出卡 ⇒ 既有 `_begin_pending_confirm` 結束回合；清草稿。
  - 範圍閘不過 ⇒ 既有 `SCOPE_EXIT_TEXT` 出口；清草稿。
  - `WRITE_NOT_SUPPORTED` ⇒ 既有固定句出口；清草稿。
  - 既有迴圈中**本來就是終結的出口一律照舊**：帶查無標記的 `NO_MATCH` ⇒ `jgb2_not_found_exit` 固定句；統計未開放 ⇒ 既有固定句。
  - 其他非終結結果（無 `missing_fields` 的 `INVALID_INPUT`、帳單多筆候選、未帶查無標記的 `NO_MATCH`）⇒ **⛔ 撤回任何東西**：工具結果照常回填、`tool_call_records`／`tool_results_by_id`／照片建議消耗都依既有規則（與模型自己呼叫時逐位同一段程式），迴圈再叫一次模型，模型的下一個輸出走 T2／V2／Verifier／出口閘的正常路徑——即既有 `_document_program_message` 的同一行為。本回合不再觸發。記 violation `write_draft_program_confirm_nonterminal`。多出的那一次模型呼叫有界（每回合最多 1 次），期限由上方 ≥6 秒條件與迴圈頂端既有 `deadline_s` 檢查共同保護。
  - 期限（`deadline_s`）到 ⇒ 既有 `budget_exhausted` 固定句。
- 模型當回合的原始文字在觸發時丟棄（卡與追問句皆為程式產出）。

**(6) 開關**：env `AGENT_WRITE_DRAFT`（`on`／`off`；**未設或空字串＝`on`**——比照 `AGENT_MAX_COMPLETION_TOKENS` 的 `.strip() or 預設` 讀法；其他非空值啟動失敗並印原因）。`docker-compose.prod.yml` 加 `AGENT_WRITE_DRAFT: ${AGENT_WRITE_DRAFT:-}`；dev compose 依約定不宣告 AGENT_*。

### 2.2 不做（non-goals，附理由）

| 不做 | 理由 |
|---|---|
| 確認卡文字、雜湊綁卡、兌現流程（DSP-038） | 已是程式產出，與本題無關 |
| 模型自己呼叫 `confirm.request` 那一次的處理（唯一例外：`bill_due_extend` 缺 `days` 改程式追問，見 §2.1(1)） | 保住 gpt-6-luna 現行 3/3 路徑；閘只管進草稿的值 |
| 謄本／收據文件回合 | 已有自己的程式路徑（`_document_program_message`），本片不合併 |
| 查詢工具 `jgb2.query.*` 改程式觸發 | 同類問題，範圍與驗收不同，列 §5 |
| 補充鐵則進 repo、截斷後處置 | 既有待決項，與寫入流程獨立 |
| Bedrock 正式接線、金鑰、正式機部署 | 需安全審查與業主操作 |
| 網頁按鈕入口 `action:<name>` | 業主選「程式掌握流程」（未選含 UI 入口方案） |
| 修繕分類、照片辨識、帳單期別解析邏輯 | 只把「必填／標籤／追問對象」移進表單，解析與渲染不動 |

### 2.3 負責人與執行

- 主會話：前置、第 0 步量測、整合、驗收判讀。
- 實作：一位 `security-executor`（依安全審查結論；單一寫手、同一 checkout）。擁有檔案：`rag-orchestrator/services/agent/write_forms.py`（新）、`output_schema.py`、`runtime.py`、`turn_context.py`、`session_persistence.py`、`tools/confirm.py`、`confirm_card.py`（只限缺欄函式改呼叫）、`agent_session.py`（`KEY_SPECS` 加鍵、斷言改 12、讀寫方法）、`docker-compose.prod.yml`、`rag-orchestrator/tests/unit/agent/test_agent_session_req.py`（鍵數與鍵集合斷言）、`rag-orchestrator/tests/unit/agent/` 下新測試檔與須改寫的 golden 情境。W1 差異只可動到本清單內的檔案。
- 驗證：fresh `verifier`（資料結構／序列化變更＋跨元件驗收＋安全相關）。

### 2.4 驗收

見凍結清單 `acceptance-write-flow-20261017.md`（8 項）。

### 2.5 回退

- W1 commit 前：`git diff <OSS 第一片 commit>` 只含 W1 差異；回退＝`git checkout <OSS 第一片 commit> -- <W1 擁有檔案>`（只撤 W1，第一片不受影響），新檔直接刪除需業主同意。
- W1 commit 後：`git revert <W1 commit>`。
- 上線後：`AGENT_WRITE_DRAFT=off` 重啟容器 ⇒ 撤回 `write_intent` schema、草稿、程式觸發（驗收 #6）；缺欄統一（含 `bill_due_extend` 缺 `days` 改程式追問）不隨開關回退，`ask_target` 推導與現行逐位相同。完整回退＝`git revert <W1 commit>`。

### 2.6 預算與停點

- token：實作＋測試＋實測＋verifier 合計上限 2.5M（固定開銷約 0.4M）。
- 模型費用：實測約 2 模型 × 約 70 回合，Bedrock gpt-oss 每千回合約 US$3.18（DSP-080），合計 < US$1。
- 停點：(a) 驗收 #1 或 #2 實作後首輪實測失敗 ⇒ 停，回報根因再決定；(b) 需改 `ASK_TARGETS` 以外的對外契約（`agent.turn` 回傳鍵）⇒ 停，交業主；(c) 預算用到 2.0M 仍未過驗收 ⇒ 停；(d) 前置 1 未獲授權 ⇒ 不開工。

### 2.7 帳本

核可後新增決策 DSP-085（編號因同日四筆爭議順延；業主原話、方向「寫入流程由程式掌握，模型只抽欄位與組話」、否決：只加提示詞、含 UI 入口方案暫不做）；實測通過後把 `AGENTIC_MCP_ARCHITECTURE.md` 的「寫入面出卡與否綁模型」改寫為現況。

## 3. 安全審查

security-reviewer（2026-10-17）：無 P0／P1；P2 四條、P3 六條、P4 一條，逐條處置見 §6.2。結論：雜湊綁卡、兌現比對建立者、範圍閘、文件寫入禁令、WRITE_NOT_SUPPORTED、封閉動作限業者、分類樹驗證都在 `confirm_request`／`_run_model_loop` 共用路上，程式觸發經 `_ProgramMessage` 進同一迴圈即不被繞過。執行者依此用 `security-executor`。

## 4. 已知風險

- 模型把非寫入的句子誤填 `write_intent` ⇒ 程式追問或出卡；仍須使用者按確認才寫入。驗收 #4 量誤觸發、#8 量改談別的。
- 輸出 schema 變大 ⇒ 每回合輸出 token 增加；驗收 #5 量延遲。
- 數字／日期閘的正規化有涵蓋不到的口語（例：「下禮拜一」、國字數字）⇒ 值被丟、程式再追問一次（偏保守，不出錯值）。
- enum 欄位值域內的捏造（例：使用者沒說緊急，模型填 `emergency_status`="2"）值閘擋不到；卡上印出急迫程度、須使用者按確認，與模型自己呼叫 `confirm.request` 的現況同一等級。
- §2.5 的 `git diff <OSS 第一片 commit>` 會含其他窗口未提交的檔案；回退指令只 checkout W1 擁有檔案，不受影響。
- 問句側敏感樣式會命中部分寫入語句（例「合約期間…」「月費」「屋頂有漏洞」），這些回合不走程式優先、退回 W1b 輸出後觸發（security-reviewer W1c F4）。
- 既有物件記憶 `estate_carry` 在前置查詢唯一命中時寫入，之後缺物件的 `confirm.request`（模型自呼或程式觸發）會被它補上；若使用者在追問描述時答了恰好唯一命中某物件的短詞（例「頂樓」），卡上可能印出該物件，須使用者按確認（W1 前即存在；§7.3 DEFER）。
- 物件名稱補值在單筆命中只拿得到查詢關鍵字時，補進草稿與卡上的是使用者打的關鍵字（例：「學生獨立套房」而非完整名稱）；物件解析仍以同身分可見範圍唯一命中，卡上名稱較短但指向同一物件（§7.2 已觀察；security-reviewer W1b 2a）。

## 5. 後續（本計畫不做，列入 HANDOFF 待決）

- 查詢工具同類問題：一般查詢 `jgb2.query.*` 仍由模型決定要不要查（前置查詢只涵蓋編號／短名詞，`_pre_lookup_id_result`／`_pre_lookup_keyword_result`）。W1 成立後評估同一做法。

## 6. 審查處置

### 6.1 plan-verifier r1（REVISE）

| # | 級 | 摘要 | 處置 |
|---|---|---|---|
| 1 | P1 | `git restore` 回退會清掉 OSS 第一片未 commit 改動；compose 未列擁有權 | FIX：§2.0-1 前置 commit、§2.5 只撤 W1、§2.3 列 compose |
| 2 | P2 | `bill_due_extend` 無表單驅動缺欄；替代必填表達不了 | FIX：§2.1(1) 替代組＋追問組、5 支同一 `missing_labels`、驗收 #3 各缺一欄 |
| 3 | P2 | 觸發插入點、handoff、預算、非終結結果、summary 未定義 | FIX：§2.1(5) 逐項寫明 |
| 4 | P2 | 名稱型追問答覆不進草稿 | FIX：§2.1(4) 前置查詢唯一命中寫入草稿；單元測試 |
| 5 | P2 | off 逐位相同與 strict schema 矛盾 | FIX：§2.1(2) off 時 schema 不含欄位、pydantic 預設 None；驗收 #6 |
| 6 | P2 | 防捏造閘只涵蓋文字欄位 | FIX：§2.1(3) 型別×規則表、system 鍵排除、模型 payload 合併同閘 |
| 7 | P2 | 缺安全審查 | FIX：§3／§6.2；執行者改 `security-executor` |
| 8 | P2 | 驗收備案無腳本、#4 無基準、grep 缺 `-r` | FIX：驗收清單 r2 |
| 9 | P2 wording | 未寫終點指標 | FIX：§1 終點指標表 |

### 6.2 security-reviewer

| # | 級 | 摘要 | 處置 |
|---|---|---|---|
| F1 | P2 | 程式觸發未檢查受眾看不看得到寫入工具（售前會拿到兌現不了的卡、草稿存個資） | FIX：§2.1(3) 可見性閘、§2.1(5) 條件；單元測試（prospect＋`write_intent` ⇒ 不寫 token、不建草稿） |
| F2 | P2 | 觸發吃工具預算／期限；非終結結果多叫一次模型 | 前半 FIX：§2.1(5) 不計工具預算、期限 ≥6 秒才觸發；單元測試（工具用滿再作答 ⇒ 不變 `budget_exhausted`）。後半 REJECT（見表下說明） |
| F3 | P2 | 模型 payload 合併若取補值後版本，照片描述與系統值漏進草稿 | FIX：§2.1(3) 只取模型原始參數、文件回合不合併；單元測試（照片回合照片描述不進草稿與下一回合 messages） |
| F4 | P2 | 注入段 citable 與保留 id 未定 | FIX：§2.1(3) `citable=False`、`ReservedCallIds` 新 id、sanitize、排序；單元測試（偽造同 id 記 `tool_call_id_collides_with_reserved`） |
| F5 | P3 | 非文字欄位無來源閘；系統值鍵不可進值域 | FIX：§2.1(2)(3) system 鍵排除、數字用 `_number_in_texts`、email／phone 子字串、`emergency_status` 只收封閉值 |
| F6 | P3 | 生命週期須進 `KEY_SPECS`；釘住範圍要擋 | FIX：§2.1(3) 登記 `UNTIL_SCOPE_EXIT`、斷言 12、釘住不注入不觸發 |
| F7 | P3 | 讀回驗形狀、上限、鍵按動作過濾 | FIX：§2.1(3) 讀回驗形狀與上限、合併丟非本動作鍵、斷言無身分鍵 |
| F8 | P3 | WRITE_NOT_SUPPORTED 時 Email／電話留在草稿 | FIX：§2.1(5) not_supported 清草稿 |
| F9 | P3 | 整句接回會錯置岔題 | FIX：§2.1(4) 文字欄位只在模型 `write_intent` 為同一動作時接回；驗收 #8 腳本 T |
| F10 | P3 | 文件回合觸發浪費且清文件暫存 | FIX：§2.1(5) 文件回合與 `document_carry` 動作不同時不觸發 |
| F11 | P4 | trace 紀律 | FIX：§2.1(3) 只記鍵名、violation 固定字串 |
| Q1 | 待查 | 正式機 `AGENT_AUDIENCES`／`AGENT_STAGE` | 不影響：F1 的可見性閘不論設定都生效 |
| Q2 | 待查 | `form_sessions` 完成列有無保留期限 | DEFER：草稿與 `dialog`／`pending_confirm` 同敏感等級且清除更嚴；保留期限另列 HANDOFF 待決 |
| Q3 | 待查 | REST 橋 `handle_agent_entry` 無 owner 比對 | DEFER：非本片路徑，註解標已掛不起來；列 HANDOFF |
| Q4 | 待查 | strict schema 是否收 `maxLength` | 不依賴：上限一律程式端（F7） |
| Q5 | 待查 | 觸發點位置、被拒嘗試的 `write_intent` 是否合併 | FIX：§2.1(5) 插入點在 T2／V2／Verifier 之前；只採觸發判斷當次的 `out.write_intent`，被 schema 拒的嘗試不合併 |

F2 後半（非終結不再叫模型）於 r3 改判 **REJECT**：plan-verifier r2 #6 證實「撤回」會與既有迴圈的查無出口、照片建議消耗、`tool_call_records` 互相衝突，留下不一致狀態；改為沿用既有 `_document_program_message` 的行為（多一次模型呼叫，每回合上限 1 次，期限門檻提高到 6 秒）。

### 6.3 plan-verifier r2（REVISE，連續第二次；主會話逐條處置後送一次收尾審查）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | 新增 `days`／`period` ask_target 使 off 時 schema 改變 | FIX（簡化）：不新增值域，無合適值填 `None`（§2.1(1)） |
| 2 | 草稿字串未轉型，`days` 字串不出卡 | FIX：共用 `to_payload` 正規化（§2.1(1)）；單元測試 |
| 3 | 只表態意圖的第一句不觸發，接回前提不成立 | FIX：草稿新建即觸發（§2.1(5)）；驗收 #1 第一句須為程式追問 |
| 4 | 修繕問題描述空字串語義兩源不一致 | FIX：照現行程式（空白算缺），記 dispute 待業主裁；單元測試 |
| 5 | 分類不合法留在草稿造成永久非終結 | FIX：寫入草稿前即驗分類樹（§2.1(3)） |
| 6 | 非終結「撤回」與既有出口與副作用衝突 | FIX（簡化）：不撤回，沿用既有程式驅動行為（§2.1(5)）；F2 後半改判 REJECT |
| 7 | 擁有檔案缺 `agent_session.py` 與其測試 | FIX：§2.3 補列 |
| 待查 | #4 未量正確率、#5 延遲無基準 | FIX：驗收 #4 加正確率門檻、#5 引基準 |

### 6.4 plan-verifier r3 收尾審查（REVISE；業主 2026-10-17 選「修完再審一輪」）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | `emergency_status` 字串未轉 int，出卡永遠失敗 | FIX：`to_payload` 依表內 payload 型別轉（§2.1(1)）；單元測試 |
| 2 | 驗收 #8 的 enum 捏造宣稱與設計不一致 | FIX（a）：驗收改為值域外的值；值域內捏造列 §4 已知風險 |
| 3 | 日期缺 `YYYY年M月D日`、email 去連字號對不上 | FIX：§2.1(3) 補寫法與比對規則；單元測試用腳本 C 第三句 |
| 4 | `bill_due_extend` 期別列為必填改變現行行為 | FIX：必填改 `[bill_id]` 或 `[estate_name]`，期別只在追問組；單元測試鎖模型自呼路徑逐位不變 |
| 5 | `write_intent` enum 不受 gpt-oss 遵守、pydantic 型別未定 | FIX：§2.1(2) 說明文字列值域、pydantic 開放字串、值域外丟棄記 violation |
| 6 | 開關空字串會讓正式容器起不來 | FIX：§2.1(6) 未設／空字串＝on |
| P3 | 系統解析值字面衝突、`doc_action` 區域變數、TOOL_TIMEOUT 重試處預算檢查、`git diff` 含他窗檔案 | FIX：§2.1(3)(5)、§4 |

### 6.5 plan-verifier r4（REVISE 2 條；業主 2026-10-17 再選「修完再審一輪」）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | off 不等於回到現行：缺欄統一與 `ask_target` 推導未掛開關 | FIX（b）：`ask_target` 改為與現行逐位相同的表驅動規則；`bill_due_extend` 缺 `days` 改程式追問明列為行為變更；§2.5／§2.2 收窄；驗收 #3 鎖各缺欄組合的 `ask_target` |
| 2 | `contract_ref` 經物件前置查詢接回語義錯 | FIX：名稱接回只寫 `estate_name`；`contract_ref` 改由模型提供（§2.1(4)）；單元測試 |
| P3 | 版本標示；驗收 #2 卡面只印帳單編號；收窄漏列 `contract_create`；期別必填文件與程式不一致 | FIX：標 r5；驗收 #2 以帳單編號 709744 判；收窄補列；dispute 已記 |

### 6.6 plan-verifier r5（REVISE 2 條；已修、未再審）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | 驗收 #3「缺 bill_id 且缺 period」與「不帶期別逐位相同」互相矛盾 | FIX：改為「缺 bill_id 且缺 estate_name ⇒ 程式追問、標籤含物件與期別、`ask_target=estate`」 |
| 2 | `manual_bill_create` 名稱接回在現行 ask_target 規則下走不到 | FIX：§2.1(4) 移除 `manual_bill_create`；驗收 #3 改用 `contract_create` 從真的缺欄追問回合開始 |
| 待查 | 封閉動作缺欄呼叫點相對受眾檢查與 `check_closed_keys` 的順序 | FIX：§2.1(1) 寫明呼叫點不動 |

## 7. 執行紀錄

### 7.0 前置（2026-10-17）

- 業主核可 r5（「核可＋授權 commit 第一片」）。OSS 第一片 commit `81f42ea3`（5 檔：runtime.py、docker-compose.prod.yml、test_output_cap_and_ask_target_desc_req.py、plan/acceptance-oss-slice1）。W1 基準＝`81f42ea3`。
- 決策 DSP-085 已記（DSP-081～084 為同日爭議列；`dispute.py` 曾把兩筆誤併進 DSP-032／DSP-082，已還原計數並改記 DSP-083／084）。
- 第 0 步現值（`~/jgb-archive/bedrock-eval-20261017/w1/`）：
  - `D_A_before.json`：gpt-6-luna 腳本 D 2/3 `confirm_pending`，但兩張卡皆為帳單 750528（2027/12）、其中一張延後 1 天——模型以物件關鍵字查帳單（候選上限 5 張、只回 2027 年帳單）後自選；每回合 6.9～28.5 秒。
  - `D_B_before.json`：gpt-oss 腳本 D 0/3；每回合 2.4～18.7 秒。
  - 前置查證：`jgb2.query.bills` ref=709744 查得（2026/11/01、待發送）；`confirm.request` 帶 `{bill_due_extend, estate_name:基隆溫馨一人宅套房, period:11月那期, days:7}` ⇒ 出卡帳單 709744、2026/11/01→2026/11/08 ⇒ 驗收 #2 預期成立，不需改用備案 C。
  - ⚠️ 驗收 #5（最大 ≤20 秒）在 gpt-6-luna 腳本 D 的改動前現值已超標（28.5 秒）；門檻凍結不改，結果照實回報。
  - 基線紅燈：`scripts/run-tests.sh unit` ⇒ 9 failed／4454 passed（`w1/baseline_red.txt`，與 HANDOFF §1.3 一致）。

### 7.1 實作（security-executor，2026-10-17）

- 擁有檔案內完成；新檔 `services/agent/write_forms.py`、`tests/unit/agent/test_write_draft_flow_req.py`（64 條）。全量單元 9 failed／4519 passed，失敗清單與基線逐條相同（`w1/pytest.txt`）。grep 目標零命中、正對照命中（主會話重跑確認）。
- 執行者回報的偏離與主會話處置（皆 ACCEPT，未擴大範圍）：
  1. `_agent_output_response_format()` 預設為 off 形狀，runtime 明確傳開關——保住清單外既有測試（屬性恰五個）；驗收 #6 仍成立。
  2. 鍵名稽核記在 violations（`write_draft_action:<動作>`、`write_draft_keys:<鍵>`），不加 TurnTrace 欄位——避免改清單外 golden fixture；符合「只記鍵名」。
  3. `write_intent` 含任一域外鍵（含 system 鍵、身分鍵）整份丟棄——較保守。
  4. 整句填入只用於文字欄位（實際只有修繕問題描述）；物件名稱只靠前置查詢唯一命中或模型抽取——與 §2.1(4) 一致且較保守。
  5. 模型自呼 `confirm.request` 合併的值不算本回合新值（該次呼叫已執行），值保留供後續回合。
  6. `created_by_role` 存「受眾|role_id|user_id」——比計畫更嚴。
  7. 閒置計數只在模型迴圈出口累加。
  8. `select:` 釘住範圍回合整個草稿機制不跑並清草稿——比計畫（不注入、不觸發）多清一步，較保守。
  9. 帳單多筆候選在既有迴圈本為終結出口（按鈕 ask），依 §2.1(5)「本來就是終結的出口一律照舊」處理。
  10. `bill_due_extend` 同缺 `bill_id`／`estate_name` 也改回 `missing_fields`——FIX：§2.1(1) 已補記。
  11. 新增 violation 固定字串：`write_intent_value_out_of_domain`、`write_intent_value_too_long`、`write_draft_shape_invalid`、`write_draft_cleared_idle`、`write_draft_name_caught`、`write_draft_answer_filled`。

### 7.2 首輪實測（2026-10-17）——觸發停點 (a)

證據 `~/jgb-archive/bedrock-eval-20261017/w1/`（`R_A/B.json`、`D_A/B.json`、`T_A/B.json`、`P_A/B.json`、`run_all.log`）。

| | 報修 R | 延期繳費 D | 改談別的 T |
|---|---|---|---|
| gpt-6-luna | 3/3 出卡（2 張卡上物件印「學生獨立套房」＝模型抽出的較短名稱；fixture 只有一個符合物件） | 3/3 出卡，全為帳單 709744、7 天（改動前 2/3 且皆選錯帳單）；最慢 4.1 秒（改動前 28.5） | 第三句未接回：T2 後草稿被閒置清除、T3 名稱未接回 |
| gpt-oss | 0/3 | 0/3 | 程式未介入 |

**根因（R_B_diag.shim.jsonl 原始輸出）**：gpt-oss 每回合輸出 `"write_intent": null`，連「能幫我新增一張修繕單嗎」也是（推理原文「User wants to create repair」）。strict schema 只保證欄位存在，不保證非 null——計畫「模型無法略過」的假設不成立。次因：(4) 接回只認程式追問，模型自寫的追問之後不接回；T 情境的名稱接回要求上回合 `LAST_ASK_TARGET_KEY=estate`。

**診斷探測**（`w1/probe/`，專用「意圖＋欄位」呼叫、action 值域含 `none`；gpt-oss low；原始輸出全存）：
- probe1（無草稿資料段）：起手句 R1／D1／T1 9/9；D2／D3 續答含欄位 6/6；T2 改談別的判 none 3/3；知識題 36 次誤判 0；但只回物件名或只回描述的續答（R2／R3／T3）0/9。中位 0.5 秒。⚠️ 首次計分 25 筆「解析失敗」是量尺錯（Bedrock 回傳前綴殘缺 `{\n  "{...`），由原始輸出以逐位置 `raw_decode` 重算。
- probe2（加草稿資料段＋`answers_pending` 布林）：「是否在回答追問」判斷約半數正確、知識題誤判 2/36、5 筆無法解析 ⇒ 續答判斷不可交給 gpt-oss。

**結論**：起手意圖可由專用呼叫可靠取得；續答（短答）必須由程式依「上一句程式追問的欄位」接收，不能問模型。W1 需修訂設計，交業主決定。

## 8. W1 修訂（W1b，2026-10-17）

> 業主裁示（停點 (a) 後）：修法 1、2 照提議（專用意圖判斷呼叫；程式追問後的下一句由程式依追問欄位接收、草稿缺物件時唯一命中即補），岔題辨認選「問句不當答覆」（選項原文：「句尾是問號或『嗎／呢』的問句 ⇒ 不填進草稿、交主模型正常回答，草稿保留。結構規則（句型），不是語意詞表；『冷氣不冷嗎』這類會被誤判成岔題、再追問一次。」）。驗收清單不收窄，只在 #3／#6／#8 增列單元測試（見清單 r6）。

### 8.1 改什麼（在 W1 已實作的程式上增量修改；其餘 §2.1 規格不變）

1. **意圖來源改為專用呼叫，主輸出不再帶 `write_intent`**
   - 每回合（開關 on、非文件回合、非 `select:` 回合、通過可見性閘、且非 `readonly_view`）由 runtime 另發一次 **意圖判斷呼叫**：同一個模型、同一個 client，strict schema `{action: <5 支動作名＋"none">, fields: [{key, value}]}`，說明文字列出動作與鍵（由表單產生，`write_forms.write_intent_description()`），輸入＝系統句＋本會話對話（`dialog`）＋當句；`max_completion_tokens` 400。
   - 與主模型迴圈**並行**啟動（`asyncio` 同時發出），在 §2.1(5) 的觸發判斷點 await；逾時（3 秒）或失敗 ⇒ 視為 `none`、記 violation `write_intent_call_failed`，⛔ 影響主回合。
   - 解析：剝 `<reasoning>…</reasoning>` 後逐位置 `json.JSONDecoder().raw_decode`，取第一個含 `action` 的物件（Bedrock 回傳前綴殘缺，見 §7.2）；全不成 ⇒ `none`＋violation `write_intent_unparsed`。
   - pydantic／值域外處理、值閘、可見性閘照 §2.1(2)(3)。
   - 主輸出 `AgentOutput` 移除 `write_intent` 欄位（on 與 off 的 `response_format` 皆與改動前逐位相同——驗收 #6 由「off 逐位相同」擴為「on／off 皆逐位相同」）。
   - 計量：意圖呼叫的 token 計入同回合 `prompt_tokens`／`completion_tokens`，`llm_calls` 另記 `write_intent_calls`（violations 固定字串 `write_intent_call`）。
2. **續答由程式接收（不問模型）**
   - 條件：草稿存在、上回合是**程式缺欄追問**（`confirm_missing_fields_ask`）、當句**不是問句**。
   - 問句判準（結構規則）：去尾端空白與句末標點（。！!～~、）後，以「？」「?」結尾，或最後一字為「嗎」「呢」⇒ 問句。問句 ⇒ 不填、草稿保留、閒置計數不加。
   - 接收：上回合追問的缺欄清單中，第一個 `source=user_words` 的**文字型**欄位（例：問題描述）⇒ 當句原文（過 `sanitize_data_piece`、長度上限）；名稱型欄位依下條。
3. **物件名稱補值（不限上回合追問）**：草稿缺 `estate_name` 時，當句跑既有前置查詢（`_pre_lookup_trigger` 以 `after_name_ask=True` 呼叫），**唯一**命中 ⇒ 寫入系統查得的物件名稱。
4. 觸發條件（§2.1(5)）的「本回合有新值或剛建立」改為：意圖呼叫建立／合併了草稿，或 8.1-2／8.1-3 接收了值。
5. **不變**：值閘、可見性閘、清除條件、注入段、預算豁免、非終結處理、開關語義、`to_payload`、表單與缺欄統一。

### 8.2 不做

- 不讓模型判斷「是否在回答追問」（probe2 約半數正確）。
- 不加語意詞表；問句判準只看句末字元。

### 8.3 回退

同 §2.5；另 W1b 為 W1 之上的增量，未 commit 前可整體以 `git checkout 81f42ea3 -- <W1 擁有檔案>` 撤回（新檔刪除需業主同意）。

### 8.4 預算與停點

- 追加上限 1.0M token（W1 已用約 0.9M）。
- 停點：W1b 實測 #1 或 #2 仍失敗 ⇒ 停，回報根因。

### 8.5 W1b r2（依 plan-verifier W1b r1 REVISE 6 條修訂；以下覆寫 §8.1 對應段）

1. **程式追問標記的持久位置**（覆寫 8.1-2 前提）：草稿新增第 5 鍵 `asked`＝上回合**程式缺欄追問**所問欄位鍵的清單（依表單欄位鍵，非中文標籤）。`DRAFT_KEYS` 改為 5 鍵，`load_draft` 驗：`asked` 為 list、元素皆為該動作表單的欄位鍵、長度 ≤ 表單欄位數，不合整份丟棄。
   - **寫點唯一**：`confirm_missing_fields_ask` 出口（不論程式觸發或模型自呼 `confirm.request` 得缺欄——兩者的追問句都是程式產出）在草稿存在時寫入；草稿不存在時（模型自呼且無草稿）先建草稿再寫。**模型自寫的追問（`kind=ask` 經 Verifier 的輸出）⛔ 寫**。
   - **清點**：每回合開始讀出後即清為 `[]`（只對緊接的下一回合有效）；草稿其他清除條件照舊。
2. **整句填入的判準**（覆寫 8.1-2 接收段）：只在 `asked` **恰好一個**欄位、且該欄位為 `source=user_words`、型別 `text`、**非名稱欄位**（非 `estate_name`／`contract_ref`）時，以當句原文填入（過 `sanitize_data_piece`、長度上限）。`asked` 含名稱欄位或多於一個欄位 ⇒ 不整句填入，當句只交 8.1-3 物件補值與意圖呼叫。**同欄優先序**：意圖呼叫抽出的值若通過值閘 ⇒ 用它；否則用整句值。
3. **問句回合整段凍結**（覆寫 8.1-1／8.1-3／8.1-4 在此情形的行為）：`asked` 非空（上回合是程式缺欄追問）且當句為問句 ⇒ 本回合**不合併**意圖呼叫結果（含不同動作的換草稿）、**不跑** 8.1-3、**不觸發**；草稿除 `asked` 清空外原樣保留；回答完全交主模型。對應業主原文「不填進草稿、交主模型正常回答，草稿保留」。
4. **意圖呼叫 task 的收尾與計量**（補 8.1-1）：task 於回合開始建立；`_run_turn_body` 最外層以 `try/finally` 在組 trace 前一律收尾——已完成 ⇒ 經 `usage_metering.add_llm_usage` 計量並把 token 加入 `prompt_tokens`／`completion_tokens`、記 `write_intent_call`；未完成 ⇒ `cancel()` 並記 `write_intent_call_cancelled`（未完成者無 token 可計）。觸發判斷點 await 的逾時改為 `min(8 秒, 剩餘期限 − 6 秒)`（probe2 有 4/63 筆 5.5～7.3 秒）；`max_completion_tokens` 改為 800（與探測一致）。
5. **驗收觀察點**：#6「schema description 含動作名與鍵名」與 #8「值域外 action／key」改以**意圖呼叫的 schema 與回應解析**為觀察點（清單 r7）。
6. **安全審查**：security-reviewer 審 W1b（F9 改變、前置查詢擴大觸發、意圖呼叫輸入面），結論與處置見 §8.6。

### 8.6 security-reviewer（W1b）結論與處置

**優先序**：§8 內衝突時 **§8.6 覆寫 §8.5，§8.5 覆寫 §8.1～8.4**。依此：task 建立點＝8.6-3a；收尾位置＝8.6-3b（取代 8.5-4 的「最外層 try/finally」）；取消時的計量＝8.6-3b 估算計入（取代 8.5-4「未完成者無 token 可計」）；8.1-3 的執行條件＝8.6-2b／2d 收窄後的版本。

結論：無 P0／P1；未新增授權面（寫入仍經確認卡＋雜湊＋使用者按確認；物件解析以 `role_id＋viewer_user_id` 限範圍；意圖呼叫同 provider／client、輸入為主呼叫子集；`asked` 由程式出口寫）。以下處置皆為**實作規格**（與 §8.5 同效力）。

| # | 級 | 摘要 | 處置 |
|---|---|---|---|
| 1a | P3 | 非問句岔題被整句填成描述 | FIX：意圖呼叫回傳**另一支寫入動作**時不整句填入；同一句已整句填入某欄 ⇒ 不再跑 8.1-3 |
| 1b | P3 | `asked` 未綁動作，換草稿跨動作錯置（dev） | FIX：換草稿時一併清 `asked` |
| 1c | P3 | 「每回合開頭清空」若只清副本會殘留 | FIX：`_write_draft_begin` 讀出後**立刻經 `AgentSession` 寫回** `asked=[]`；單元測試「程式追問→問句（凍結）→陳述」第三句不被整句填入 |
| 1d | P3 | 文件回合不應寫 `asked`／建草稿 | FIX：`document is not None`、`doc_action` 非 None、`_document_carry_of` 有效三者皆排除 |
| 2a | P3 | 單筆命中時補進的是使用者關鍵字、非列上名稱 | FIX：8.1-3 拿得到列上 `title` 時用 `title`；只有關鍵字時照現行（用關鍵字），§2.1(4)「值來自系統查得的列」更正為此，並列 §4 已知風險 |
| 2b | P3 | 拿掉「上回合追問物件」前提後短答被誤補成物件 | FIX：8.1-3 只在 `asked` 為空或含 `estate_name` 時執行；同句已整句填入其他欄位不執行；單元測試「追問描述→答『頂樓』且替身唯一命中 ⇒ 不寫 `estate_name`」 |
| 2c | P4 | 多一次 estates 查詢 | ACCEPT（同身分可見範圍、查無不注入） |
| 2d | 待查→FIX | 8.1-3 時點 | 只對**回合開始即存在**的草稿生效（沿用 `_build_turn_context` 的既有前置查詢，不另開第二條查詢路徑）；本回合由意圖呼叫新建的草稿，物件靠意圖呼叫欄位 |
| 3a | P3 | task 不可早於 `run_program_segments` | FIX：task 在 `run_program_segments` 未結束回合、`_build_turn_context` 之後，且草稿機制可跑（開關 on、非文件、非 `select:`、非 `readonly_view`、看得到任一 `jgb2.action.*`）時才建立 |
| 3b | P3 | 外層 finally 收尾進不了 trace；`wait_for` 會自動取消 | FIX：收尾掛在**真正組 trace 的兩處**——`TurnAccumulator.build_trace`（`turn_context.py`，涵蓋一般出口與 `build_fixed`）與 `_finish_confirm_turn` 組 `TurnTrace(` 之前（`runtime.py`）；⛔ 動 `exit_gates.py`、`turn_segments.py`（不在 §2.3 擁有清單；`turn_segments` 出口早於 task 建立，不需收尾）；等待用 `asyncio.wait({task}, timeout=…)`（不自動取消）；未完成才 `cancel()`，記 `write_intent_call_cancelled` 並以輸入字元數 ÷1.1 估算 prompt token 計入 |
| 3c | P4 | 偽造 JSON 搶先被解析 | FIX：只解析 `</reasoning>` 之後的最終段；同一回應出現多個帶 `action` 且內容不同的物件 ⇒ 視為 `none` |
| 4a | P4 | 模型自呼出口建草稿未過可見性閘 | FIX：一律經可見性閘 |
| 4b | P4 | `asked` 讀回驗形狀可再嚴 | FIX：不得重複、只收 `source=user_words` 鍵、與 `action` 一併驗 |
| 5a | P3 | 問句凍結須涵蓋 ≤6 字補名稱路徑 | FIX：凍結判斷包住 `_write_draft_catch_name` 呼叫本身；單元測試「追問後答『A棟呢』且替身唯一命中 ⇒ 草稿不變」 |
| 5b | P4 | 問句判準漏網（零寬、全形變體、ASCII 句點） | FIX：先過 `sanitize_data_piece`＋NFKC，句末去除集合加 `.`、`…`，問號集合含 `？`、`?`、`﹖` |
| Q-a | 待查 | jgb2 estates keyword 比對語義 | DEFER（2b 已縮小觸發範圍） |
| Q-b | 待查 | Bedrock 取消請求是否仍計費 | DEFER（3b 以估算 token 計入） |
| Q-c | 待查→FIX | 整句超長截斷或拒收 | 拒收（不整句填入），交意圖呼叫 |

### 8.7 plan-verifier W1b r2 收尾審查（REVISE 2 條；已修、未再審）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | 8.6-3b 收尾 hook 位置放不進去且超出擁有範圍（`exit_gates.finalize` 收到時 trace 已組好） | FIX：改為 `TurnAccumulator.build_trace` 與 `_finish_confirm_turn` 組 `TurnTrace(` 前；移除 `exit_gates.finalize`／`turn_segments` |
| 2 | §8.6／8.5／8.1 衝突無優先序；8.6-2a 更正未落正文（wording-only） | FIX：§8.6 開頭明列優先序；§2.1(4) 改寫、§4 補風險 |

### 7.3 W1b 實作（security-executor，2026-10-17）

- 擁有檔案內完成；`exit_gates.py`／`turn_segments.py` 未動。`test_write_draft_flow_req.py` 144 條；全量 9 failed／4599 passed，失敗清單＝基線（主會話重跑比對確認）。grep 目標零命中、正對照命中。
- 偏離與主會話處置：
  1. 「合併了草稿」解讀為「意圖呼叫至少一值通過值閘」（同值重講也觸發）——ACCEPT（觸發結果為程式追問或出卡，仍須按確認）。
  2. 意圖說明改「action 填 none、fields 空陣列」；schema 根層加 description——ACCEPT（主輸出已無此欄；與 probe 系統句一致）。
  3. `_run_turn_body` 例外離開時 `abort()` 意圖 task——ACCEPT（防孤兒計費呼叫；不取代 8.6-3b 收尾點）。
  4. `_write_intent_calls[trace_id]` 登記——ACCEPT。
  5. 問句凍結回合仍建立意圖 task（不等待、收尾時計量或取消）——ACCEPT，記為後續可省成本項。
  6. `asked` 動作名改從 payload 取（封閉動作缺欄結果不帶 action）——ACCEPT。
- 安全疑點（執行者提出）：8.6-2b 防「頂樓」誤補只擋到草稿；既有「物件記憶」`estate_carry`（第六批 #10）在前置查詢唯一命中時仍會寫入，程式觸發 `confirm.request` 缺物件時由 `_apply_estate_carry_to_confirm_args` 補上 ⇒ 卡上可能印出誤命中的物件，須使用者按確認。處置：DEFER＋列 §4 已知風險——此為既有機制在模型自呼路徑同樣存在的行為（W1 前即如此），非 W1b 引入；收窄 `estate_carry` 寫點屬既有功能變更，另案交業主。

### 7.4 W1b 實測（2026-10-17）——觸發停點 §8.4

證據 `~/jgb-archive/bedrock-eval-20261017/w1/`（`R_*.json`、`D_*.json`、`T_*.json`、`P_*.json`、`shim_B.jsonl`、`run_all.log`；首輪移至 `w1/r1/`）。

| | 報修 R | 延期繳費 D | 知識題誤觸發 | 知識題延遲 中位／最大 |
|---|---|---|---|---|
| gpt-6-luna | 3/3 | 2/3（第 3 輪 D3：模型先自查帳單撞查無固定句） | 1/30（P14「合約本文歸檔資料」被意圖呼叫判成建合約 ⇒ 程式追問欄位） | 3.6／8.9 秒 |
| gpt-oss | 1/3 | 0/3 | 0/30 | 2.6／20.5 秒 |

已改善（W1b 生效）：起手句 6/6 由程式追問（R1、D1）；物件名稱接回 R2 3/3（`write_draft_name_caught`）；D2 物件＋期別進草稿 2/3；R3 整句接回並出卡 1 次（`write_draft_answer_filled`）。

**根因（結構）**：程式路徑排在主模型之後——觸發點在「主模型最終輸出解析成功」之後。gpt-oss 主模型在續答回合常失控截斷（`llm_output_truncated`，14～32 秒）或 `ask_target_invalid` 被擋轉人，程式觸發點不是沒走到、就是剩餘期限 <6 秒不觸發；另一種是主模型先自呼 `confirm.request`（不帶草稿值）或先自查撞出口，程式的續答值沒套上。例：R 第 0 輪 R3 模型自呼 `confirm.request` 缺描述 ⇒ 程式追問，未套用「冷氣不冷」；D 三輪 D3 皆在程式觸發前轉人／截斷。
**次要**：意圖呼叫用的是主模型本身；gpt-6-luna 在 P14 誤判建合約（gpt-oss 0/30）。

⇒ 驗收 #1、#2（gpt-oss）、#4（luna D 3/3、誤觸發 0）未過。預算：W1 2.5M＋W1b 1.0M 已用盡（停點 (c) 同時成立）。交業主決定。

## 9. W1c 程式優先（2026-10-17）

> 業主裁示（W1b 停點後）：「寫 W1c 程式優先」（選項原文：「寫入回合先由程式處理、不等主模型；意圖說明加『名詞片語／查詢 ⇒ none』。追加預算 1.5M；照流程寫計畫→審查→交你核可。」）。驗收清單 8 項不改（凍結），只在 #3／#8 增列單元測試（清單 r9）。

### 9.1 改什麼（在 W1＋W1b 之上；§8 其餘不變）

1. **程式優先入口**：`_run_model_loop` 進入 `while` 之前、謄本 `_document_program_message` 判斷之後（僅當 `program_message is None`），新增 `_write_draft_program_first(...)`：
   - await 意圖呼叫（等待上限 `WRITE_DRAFT_PROGRAM_FIRST_WAIT_S = 3` 秒，`asyncio.wait` 不自動取消；逾時 ⇒ 不走程式優先，task 保留給既有的輸出後觸發點與收尾）。
   - 依 §8.5／§8.6 規則做：問句凍結判斷、意圖合併（含 1a 另一動作不整句填入）、整句填入、可見性閘、`select:`／文件回合／`document_carry` 排除、期限 ≥6 秒——**與 `_write_draft_after_output` 共用同一段程式**（抽出共用函式，⛔ 複製兩份）。
   - 條件成立 ⇒ 回傳 `_write_draft_program_message(...)`，設為迴圈第一輪的 `program_message`、`program_kind="wd"`；之後走既有工具迴圈：缺欄 ⇒ 程式追問、出卡、範圍閘、not_supported、查無固定句等**終結出口直接結束回合，主模型本回合不被呼叫**；非終結結果 ⇒ 依既有行為回填並呼叫主模型（每回合程式觸發仍上限 1 次）。
   - 條件不成立（入口條件見 §9.7 F2；意圖等待未完成見 §9.7 F1）⇒ 照現行：主模型迴圈，輸出後觸發點（W1b）保留為後備。
2. **敏感題保護**：程式優先時尚無主模型輸出可判敏感轉人；使用者當句命中既有問句側敏感判準（`services/agent/question_sensitivity.py`，讀 `VerifierRules.question_sensitive_patterns`）時不走程式優先（⛔ 新增詞表）。
3. **意圖判斷說明補一句**（`WRITE_INTENT_SYSTEM_PROMPT`）：「使用者只說名詞或名詞片語、在問功能怎麼用、或在查資料 ⇒ none；只有使用者明確要系統替他建立或變更一筆資料，或正在回答進行中的建立所需的資料時，才填動作。」
4. **計量**：不變（意圖呼叫照 §8.6-3b 收尾）；主模型未被呼叫的回合 `llm_calls` 只含意圖呼叫以外的 0 次，trace 照實。

### 9.1a 終點指標（推進 §1 表；現值取自 §7.4 W1b 實測）

| 指標 | 現值（W1b） | W1c 預期 | 對應驗收 |
|---|---|---|---|
| gpt-oss 報修三步出卡率 | 1/3 | 3/3 | #1 |
| gpt-oss 延期繳費三步出卡率 | 0/3 | 3/3 | #2 |
| gpt-6-luna 報修三步出卡率 | 3/3 | 3/3（不退步） | #4 |
| gpt-6-luna 延期繳費三步出卡率 | 2/3 | 3/3 | #4 |
| 知識題誤觸發（A／B） | 1/30／0/30 | 0／0 | #4 |

### 9.1b 執行第 0 步（實作前，便宜探測）

以新的 `WRITE_INTENT_SYSTEM_PROMPT`（含 9.1-3 加句）用 `w1/probe/` 同型探測 gpt-oss：腳本 D2、D3、R1、D1 與 12 題知識題各 ×3，量抽取率（plan-verifier W1c Q-A：D2 是名詞片語，可能被新句推成 none）。D2 抽取率 <2/3 ⇒ 停、回報再議加句用字。

### 9.2 擁有檔案

`rag-orchestrator/services/agent/runtime.py`、`rag-orchestrator/services/agent/write_forms.py`、`rag-orchestrator/tests/unit/agent/test_write_draft_flow_req.py`（必要時 `turn_context.py`）。⛔ 動 `exit_gates.py`、`turn_segments.py`、`verifier.py`（敏感判準只讀用）。

### 9.3 不做

- 主模型與意圖呼叫的「先回先用、取消另一方」競速（複雜度高；先以 3 秒等待上限量延遲）。
- 物件記憶 `estate_carry` 收窄（§7.3 DEFER）。

### 9.4 驗收

清單 8 項原條件不變；增列單元測試（r9）：程式優先且程式路徑終結 ⇒ 主模型未被呼叫（假模型 script 未消耗）；意圖等待逾時 ⇒ 照常呼叫主模型、輸出後觸發點仍可用；程式優先遇非終結結果 ⇒ 主模型被呼叫一次並帶回填結果；使用者當句命中敏感樣式 ⇒ 不走程式優先；`_write_draft_program_first` 與 `_write_draft_after_output` 共用同一個判斷函式（以測試或程式結構證明）。實測重跑全部腳本（R、D、T、P）。

### 9.5 預算與停點

- 追加上限 1.5M token。
- 停點：W1c 實測 #1 或 #2 仍失敗 ⇒ 停、回報根因；知識題延遲中位數比 W1b 增加 >1.5 秒，或 `budget_exhausted` 比例／最大延遲較 W1b 上升 ⇒ 停、回報。

### 9.6 回退

同 §8.3；W1c 為 W1b 之上的增量（未 commit）。

### 9.7 security-reviewer（W1c）結論與處置（覆寫 §9.1 對應段）

結論：無 P0／P1／P2；未新增授權面（程式優先把輸出後觸發提前，走同一組終結出口；可見範圍使 prospect 走不到程式優先；輸出皆程式產出）。

| # | 級 | 摘要 | 處置 |
|---|---|---|---|
| F1 | P3 | 3 秒逾時若沿用共用段：回傳 None 與「意圖 none」無法區分，會略過 1a、設 `intent_consumed` 使後備失效 | FIX（覆寫 9.1-1）：程式優先以 `asyncio.wait` 判「task 是否完成」；**未完成 ⇒ 不設 `intent_consumed`、不記 `write_intent_call_failed`（另記固定字串 `write_draft_program_first_wait_timeout`）、不合併、不整句填入、不觸發**，全部留給輸出後觸發點；單元測試：意圖延遲 >3 秒、`asked=[description]`、非問句 ⇒ 主模型呼叫前無 `write_draft_answer_filled`，輸出後觸發點取得意圖並套用 1a |
| F2 | P3 | 「意圖 none ⇒ 照現行」與共用觸發條件衝突，續答回合（意圖本就回 none）會永遠不走程式優先 | FIX（覆寫 9.1-1）：入口條件＝與輸出後觸發點**同一條件**（`created`／`merged`／`caught`／`filled` 任一成立），刪除「意圖 none」字樣；單元測試：上回合 `asked=[description]`、意圖回 none、非問句 ⇒ 走程式優先且主模型 script 未消耗 |
| F3 | P4 | `question_sensitive` 規則缺時放行 | FIX：`getattr(self.verifier, "rules", None)` 為 None ⇒ 不走程式優先；單元測試 |
| F4 | P4 | 敏感樣式會命中部分寫入語句（「合約期間…」「月費」「漏洞」）⇒ 退回 W1b 行為 | ACCEPT，列 §4 已知限制（⛔ 改規則檔：業主「⛔ 補詞表」） |
| F5 | P4 | 非寫入回合序列等待最多 3 秒 | ACCEPT；§9.5 停點加記 `budget_exhausted` 比例與最大延遲 |
| Q1 | 待查 | gpt-6-luna 意圖呼叫延遲分布未量 | 實測時記錄意圖 task 完成時間（`run_w1.py` 由 trace 讀 `write_draft_program_first_wait_timeout` 次數） |
| Q2 | 待查 | 意圖呼叫輸入含助理回覆 | DEFER（W1b 已同；值閘只比對使用者原話） |

共用函式須保留文件回合排除（`document is not None or document_writable_action(document) is not None ⇒ None`）。

### 9.8 plan-verifier W1c（REVISE 1 條 wording-only；已修、未再審）

| # | 摘要 | 處置 |
|---|---|---|
| 1 | §9 未寫終點指標現值與預期（wording-only） | FIX：§9.1a |
| Q-A | 新加句可能使 D2 判 none | FIX：§9.1b 實作前探測，未達即停 |
| Q-B | 9.1-1 正文殘留「意圖 none」 | FIX：改指 §9.7 F1／F2 |
| Q-C | luna 意圖延遲未量 | 實測記錄（§9.7 Q1） |

### 9.9 W1c 執行紀錄

- 業主核可 W1c（「核可、開始」，2026-10-17；§9.8 為已修、未再審）。
- 第 0 步探測（`~/jgb-archive/bedrock-eval-20261017/w1/probe/probe3_w1c.py`、`probe3.json`，含原始輸出；gpt-oss low、新說明含 9.1-3 加句）：R1 3/3、D1 3/3、D2 2/3（第 1 輪判 none）、D3 3/3（days=7）；知識題 36 次誤判 0；最慢 1.0 秒 ⇒ D2 達門檻（≥2/3），照計畫進入實作。⚠️ D2 判 none 的回合須靠物件名稱補值或後備觸發點，風險由驗收 #2 量測。
- 實作（security-executor）：擁有檔案內完成（`runtime.py`、`write_forms.py`、測試檔；`turn_context.py` 與四個禁動檔未動）；`_write_draft_decide` 為兩條路共用判斷；測試檔 158 條全綠；全量 9 failed／4613 passed，失敗清單＝基線（主會話重跑比對確認）。
- 偏離與處置（皆 ACCEPT）：(1) 既有 144 條測試的替身 `FakeVerifier` 無 `rules` ⇒ 依 F3 走後備路徑，W1c 路徑以 `_RulesVerifier`（真規則檔）另測——正式 `Verifier` 必帶 `rules`；(2) 等待上限固定 3 秒（期限不足由共用函式的 ≥6 秒條件擋）；(3) 敏感轉人否決以 `allow_trigger` 傳入共用函式，順序同 W1b；(4) 未新增「程式優先觸發」專用 trace 字串（實測以 `llm_calls=0` 或觸發字串先於主模型判讀）。

### 9.10 W1c 實測（2026-10-18）——觸發停點 §9.5

證據 `~/jgb-archive/bedrock-eval-20261017/w1/`（W1b 一輪移至 `w1/r2/`）。

| | 報修 R | 延期繳費 D | 改談別的 T | 知識題誤觸發 | 知識題延遲 中位／最大（W1b） |
|---|---|---|---|---|---|
| gpt-oss | **3/3**（W1b 1/3） | 2/3（W1b 0/3） | 2/2 第三句追問問題描述 | 0/30 | 2.6／21.9 秒（2.6／20.5） |
| gpt-6-luna | 3/3（第 0 輪第二句提早出卡，描述錯為「可租補」） | 1/3（W1b 2/3） | 2/2 | 0/30 | **5.2**／13.9 秒（3.6／8.9） |

寫入回合多數 `llm_calls=0`（主模型未被呼叫）、0.6～2.5 秒。

**根因**：
1. **天數被值閘擋**（D3 失敗 3 次：A 2、B 1，`write_intent_value_not_in_user_words`）：意圖呼叫照抄原話回 `days="7 天"`（`shim_B.jsonl` 推理原文「days = "7 天"? … Keep original phrase」），`write_forms.parse_number` 要求整串為數字 ⇒ 解析失敗。
2. **一句拆成兩欄**（A R 第 0 輪）：gpt-6-luna 意圖呼叫把「學生獨立套房可租補」拆成物件「學生獨立套房」＋描述「可租補」，兩者皆為原話子字串、通過值閘；且意圖的物件值優先於前置查詢的系統名稱。
3. **D2 意圖 none**（B 第 2 輪）：意圖呼叫判 none、整句非純物件名、前置查詢未唯一命中 ⇒ 交主模型（12.8 秒），與 §9.1b 探測 2/3 一致。
4. **gpt-6-luna 知識題延遲 +1.6 秒**（超過停點 1.5 秒）：luna 的意圖呼叫有 5 次超過 3 秒等待（`write_draft_program_first_wait_timeout`），每個知識回合都先等意圖。

驗收：#1（gpt-oss 報修）達成；#2（2/3）、#4（luna D 1/3）、#5 未過。交業主決定。

### 9.11 W1c 修正（業主 2026-10-18「修完重測」；驗收中發現的缺陷修正，不另走計畫審查）

1. **數字欄位取值**：`int`／`number` 欄位的意圖值若含**恰好一個**數字 token（全形先 NFKC、千分位照現行）⇒ 取該數字（例「7 天」→7、「延 7 天」→7）；零個或多個 ⇒ 視為不合。取出的數字仍須通過 `_number_in_texts`（出現在使用者原話）。
2. **同一段原話不填兩欄、系統名稱優先**：本回合前置查詢唯一命中而寫入草稿的物件名稱（系統列 `title`，或單筆命中時的查詢關鍵字）**優先於**意圖呼叫的 `estate_name`；意圖呼叫的其他文字欄位值若為該命中**物件名稱或使用者當句中被判為物件名稱那一段**的子字串 ⇒ 丟棄並記 `write_intent_value_overlaps_name`。
3. **程式優先等待分級**：回合開始時**已有草稿** ⇒ 等待上限 3 秒（不變）；**無草稿** ⇒ 等待上限 1 秒；未完成一律依 §9.7 F1（不消耗、留給輸出後觸發點）。
- 單元測試：「7 天」「延 7 天」進草稿為 7、「7 到 10 天」不進；R2 情境意圖拆成物件＋描述「可租補」且前置查詢唯一命中 ⇒ 描述不進草稿、物件為系統名稱；無草稿回合等待 1 秒逾時 ⇒ 走主模型、輸出後觸發點仍可用；有草稿回合仍等 3 秒。

### 9.12 W1c 修正後實測（2026-10-18）

證據 `~/jgb-archive/bedrock-eval-20261017/w1/`（`R_*.json`、`D_*.json`、`T_*.json`、`P_*.json`、`shim_*.jsonl`、`run_all.log`、`judge/`、`pytest.txt`、`audit.txt`；W1c 修正前一輪在 `w1/r3/`）。

| 驗收 | 結果 |
|---|---|
| #1 gpt-oss 報修 | 3/3 出卡；卡上物件「學生獨立套房可租補」、問題描述「冷氣不冷」；第一句皆程式追問、第二句只追問問題描述 |
| #2 gpt-oss 延期繳費 | 3/3 出卡；帳單 709744、延後 7 天 |
| #3 程式／單元 | grep 目標零命中、正對照命中；單元測試 178 條通過（執行者回報、全量含之） |
| #4 gpt-6-luna／誤觸發／盲判 | luna R 3/3、D 3/3（709744、7 天）；知識題誤觸發 A 0/30、B 0/30；盲判（誘餌 6/6）A 正確 26／錯誤 0、B 正確 24／**錯誤 4** ⇒ B 錯誤數超過門檻 3（4 則皆為補資料段沒寫的細節：P05、P17、P29、P30） |
| #5 延遲 | R＋D 回合：A 中位 1.8／最大 7.8 秒；B 中位 0.85／最大 1.7 秒 |
| #6 開關 | 單元測試（執行者回報） |
| #7 | 全量 9 failed／4633 passed，失敗清單＝基線；本機容器重建後 `make audit` OVERALL: PASS |
| #8 改談別的 | A、B 各 2 輪：第三句皆程式追問問題描述、未出卡；⚠️ A 第 0 輪第二句主模型自寫「可以提供要新增修繕單的物件名稱和問題描述嗎？」（程式本回合凍結、草稿未動，屬主模型輸出）——是否構成「第二句出寫入追問」交 verifier 判 |
| 知識題延遲 | A 中位 3.2／最大 6.4 秒（W1b 3.6／8.9）；B 中位 2.45／最大 26.4 秒（W1b 2.6／20.5，最大值為截斷回合，屬 W2） |

### 9.13 verifier（W1c 修正後）REFUTED 與處置（2026-10-18）

verifier 判 REFUTED：#1、#2、#3、#5、#6、#7 複核通過；#4 B 盲判錯誤 4 > 3；#8 A 第 0 輪 T2 主模型自寫寫入追問。

| # | 級 | 摘要 | 處置 |
|---|---|---|---|
| F1 | P2（W1 引入） | 問句凍結回合仍注入「進行中的建立」行，推主模型回寫入追問 | FIX（主會話直改，一行）：`runtime.py` 注入條件加 `and not wd.frozen`；新增 `test_question_frozen_turn_does_not_inject_the_draft_line`（拿掉修正即轉紅，已實測）；測試檔 179 條通過。重跑腳本 T A、B 各 2 輪（`w1/T_*.json`；前一輪存 `w1/r4/`）：4 輪 T2 皆無寫入追問（A：轉人／回答自動扣款；B：一般反問），T3 皆程式追問問題描述 |
| F2 | P2（量尺錯，主會話造成） | 盲判誘餌 1／4／1 分批，第 1、3 批無法自證 | FIX：同一批 60 則答案重新分 3 批、**每批 6 則誘餌**（`judge/w1_rejudge_*`）重判；三批誘餌皆 6/6 ⇒ 採用。A 正確 26／錯誤 0；B 正確 25／錯誤 3（P05、P29、P30，皆補資料段沒寫的細節）⇒ #4 達門檻（B 錯誤 ≤3、正確 ≥24）。前一輪判分（`w1_judge_*`）作廢不引用 |
| F3 | P3 | luna 首句程式優先常逾時（無草稿等 1 秒） | DEFER：改動前同情境亦轉人，不影響清單條件；記為後續（意圖呼叫是否固定用較快模型另議） |
| F4 | P4 | D_B 第 2 輪 D2 主模型自寫追問 | ACCEPT（第三句仍正確出卡） |
| F5 | P4 | brief 的 pytest 路徑 | 已知（容器內路徑相對 `/app`） |
| F6 | P4 | repo 有他窗臨時檔 cc.py／claim4.py／probe.py | commit 時排除 |

### 9.14 最終驗證（2026-10-18）——CONFIRMED

fresh verifier（BRIEF-CONTRACT v1）判 **CONFIRMED**：清單 8 項逐條以證據檔重算皆 PASS；「R／D／P 實測可代表最終程式」前提以雜湊比對確認（實測時 `runtime.py` sha1＝最終版反套 F1 修正；R／D／P 96 回合無 `write_draft_question_frozen`，F1 不影響其行為）；通用性成立（無新增動作專屬分支、唯一字表為問句結構規則）；無 P0～P2。
P4（不擋、記錄）：gpt-oss 腳本 T 第二句被既有出口閘換成「想處理哪一件事？」未回答自動扣款（對話品質，非本片宣稱）；gpt-oss 盲判錯誤 3/30 剛好卡門檻（R1 補充鐵則處理）；F1 新測試的正對照斷言偏弱；他窗未追蹤檔 `rag-orchestrator/cc.py`／`claim4.py`／`probe.py` commit 時排除。
W1＋W1b＋W1c＋修正尚未 commit（待業主指示）。
