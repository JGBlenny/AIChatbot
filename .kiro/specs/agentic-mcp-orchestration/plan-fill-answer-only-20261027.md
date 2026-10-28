# 「填欄只填答覆」片計畫（r4，2026-10-27 業主核可）

規則與驗收清單：`acceptance-fill-answer-only-20261027.md`（規則 FA-R1～FA-R12、清單 FA0～FA11、## 廣度、非目標）。原則 P1、P4、P5。上線最低範圍內，排在第 4 步切換正式機之前（DSP-117）。以下 `~/jgb-archive/arch-step3-20261018/` 簡寫為 `arch/`。

## 0. 先答三題、終點指標、斷路器

**廣度**（全域「驗收廣度」第 7 條）：
1. 每項幾組資料 × 幾種輸入 × 重複幾次：FA0 X9 同一批 3 組表單 × 10 種輸入 × 1～5 次（共 17 場；重複只算穩定性，不算覆蓋）；FA1a（追問回合）5 組表單 × 每組 ≥13 輸入 × 1；FA1b（第一句就帶非資料）5 × ≥8 × 1；FA1c（確認卡出現後打字補充）5 × ≥5 × 1；FA2 5 × ≥7（另加答覆＋道謝 4 句）× 1；FA3 5 × ≥5 × 1；FA4 E 片 E1～E4、E14 全部場重跑（195 場）× 1；FA4b F12 名稱題組 F3″ 1 組 × 40 種首句 × 1、選定後指令式 F8 1 組 × 20 個輸入 × 1；FA5 M0 29 題 56 場 × 1；FA6 E2a 6 組 × 2 輪。
2. 輸入誰寫：FA1～FA3 由不讀程式的 fresh 代理依配額撰寫，並逐句標出答覆部分、非資料部分、預期各欄值，跑前凍結 sha256；FA0、FA4～FA6 為既有題組（FA6 為實作方所寫，只證不退步）。
3. 跟改前比：FA1～FA6、FA4b 全部在改前程式（現行常駐，修正 9 受測物）與改後程式同輸入各跑一次並列；FA0 改前值已有（X9）；FA6 改前用 `arch/e/e2a/after9/`（同一受測物）。

**終點指標**（目標文件＝目標正本 `architecture-target-20261018.md` §1「每片怎樣算完成」的全部量法，加 DSP-115 第 3 點的收案門檻「錯筆卡」）。受測物＝常駐 `aichatbot-rag-orchestrator`，`runtime.py` md5 `456860bacd1cfeb116344030b77b4bff`（容器與工作樹相同，2026-10-27 查），HEAD `720f0bf7`＋未提交改動（`arch/fill/baseline/wt-before-plan.txt`，diff md5 `7c289d4a…`）。「前兩片」＝計畫點名目標正本為目標文件的最近兩片：選對紀錄片（`plan-pick-right-record-20261021.md`，在 OV 之後，引 `report-ov.md` V4）與 E 片（`plan-closing-handoff-e-20261026.md` §0 點名目標正本 §1）；F12、選定後指令式片、W2 不計入（依 E 計畫 §0 的查證）。

| 量法 | 門檻 | 現值（來源） | 本片預期 | 前兩片實際變化（來源） |
|---|---|---|---|---|
| M0 判分場解決數，各列 W、W-D、A、K、全部（Intercom 式／嚴格） | 改後 ≥ 改前 | **現值未量**：E 收案的 M0 量的是修正 7（`arch/e/report-e-close.md`「M0 的三列量的是修正 7，沒有在修正 9 上重量」），⛔ 當現值。業主 2026-10-27 裁：核可後、改程式前量（§6 第 4 點），同批即改前對照 | 0（每列 ±0，業主 §6 第 4 點同意）。本片改到每個送出寫入意圖呼叫的回合（§4.1 適用範圍），M0 的寫入場（W、W-D）都經過；資料段標錯或未知會變成重問，有退步風險，由 FA5 量 | 選對紀錄片：判分場 45/52 → 44/52（−1，`arch/pick-right/report-pick.md`「判分場 44 < 45」）；E：判分場 50/52 → 52/52、嚴格 44/52 → 46/52（+2，`arch/e/report-e-close.md` 終點表，量於修正 7） |
| 鎖定缺陷「道謝後轉真人」（M0 場數） | 0 | 未量（同上）；最近一次 0（E，修正 7） | 0（維持） | 選對紀錄片：報告無此列、計 0；E：2 → 0（−2，變好） |
| 既有回歸題組 E2a 六組 | 每組改後 ≥ 改前 | R、D、C、T、RS 2/2，DS 1/2（`arch/e/report-e-close.md` E13，修正 9 受測物 `e/e2a/after9/`）——DS 未達字面，根因判在 F12 既有 | 0 | 選對紀錄片：R、C、T 2/2，RS 1/2，DS 補跑 2/2（`arch/pick-right/report-pick.md` V8，判非本片退步）；E：DS −1 |
| 單元測試全過 | 全過 | 9 failed、6652 passed（`arch/e/unit-after-revert10.txt`，2026-10-27 06:10，runtime md5 `456860ba…`；文件整理後 `arch/docs-cleanup/code-comments/unit.out` 同數）——**未達字面** | 0（9 筆不變；新測試全過） | 選對紀錄片：照字面報（該計畫 PV2-3），計 0；E：0 |
| `make audit`（`check_invariants.sh`） | PASS | PASS（`arch/e/invariants-revert10.txt`「OVERALL: PASS（2026-10-27）」） | 0 | 選對紀錄片：PASS（`report-pick.md` V8）；E：PASS |
| 錯筆卡（DSP-115 第 3 點；本片鎖定的題型） | 0 | **11/17**（X9 verifier 在修正 9 受測物實跑，`arch/e/x9-verifier/run_r8/records.jsonl` 6 場＋`rep/run_r8/records.jsonl` 11 場；彙整 `arch/e/x9-verifier/REPORT-x9.txt` F1）；第一句帶道謝另有探針 2 種輸入 3 場中 2 場錯卡（`arch/fill/probe-first-turn/`） | 11/17 → 0/17；收案值取自 §7 X4b（同一批 17 場在改後程式重跑，FA0）。FA1a、FA1b 新輸入另計改前改後 | 選對紀錄片、E 都沒有這一列（計 0） |

**斷路器**：前兩片實際變化選對紀錄片 M0 −1、E +2，不全為 0 ⇒ **不觸發**。

## 1. 目標

客人在寫入流程裡講話（第一句開口、回答追問、補充資料），卡上只出現他講的資料；道謝、寒暄、應答詞不會被填進任何欄位，也不會被拆成數字填進別欄、蓋掉已填的值（規則 FA-R1～FA-R5）。

實際事件：
- 追問回合（X9，修正 9 受測物，`arch/e/x9-verifier/REPORT-x9.txt` F1）：
  - 帳單追問「帳單項目」時回「水電費 3q」⇒ 卡上「金額：3 元」（setup 已填 1200），寫入意圖抽出 `total`。
  - 「水電費 3q」×3、「網路費 3Q」×2 ⇒ 卡上「帳單項目：水電費 3q／網路費 3Q」（`write_draft_answer_filled`，整句填入）。
  - 建物件「叫 和平小屋 3q」×2 ⇒「面積：3」「空間類型：3q」。
  - 修繕「門鎖壞了 3q」×2、「馬桶堵住了，感謝🙏」⇒ 問題描述含道謝。
  - 合計 11/17 錯筆卡。改前程式同一機制：`arch/e/before/E14` 帳單組「帳單項目：3Q」。
- 第一句就帶道謝（2026-10-27 探針，同一受測物，`arch/fill/probe-first-turn/records.jsonl`、`records2.jsonl`、`probe_first*.py`）：
  - 「我要新增一個物件叫和平小屋 3q，在台北市大安區復興南路一段100號，住宅用，月租 16000 元」⇒ 卡上「物件名稱：和平小屋 3q」。
  - 「幫我開一張帳單，合約是台北信義-市政府寵物友善單人房(永豐信用卡)，項目水電費 3q」＋「繳費期限 2026/12/15」⇒ 2 次中 1 次卡上「金額：3 元」。

## 2. 目標形態（業界原頁渲染檔；逐字）

原頁 2026-10-27 以 web-drive（jgbui）渲染，存 `arch/fill/sources/*.txt`（每檔首三行是網址、最終網址、渲染註記；`_index.json` 列字數）。Dialogflow CX `concept/form` 回 404（`dialogflow-cx-form.txt`），改用同站 `concept/parameter` 的 Form parameters 節；Lex `using-slots-values` 轉址到 `what-is`（`lex-slot-values.txt`），未用。

### 2.1 只把資料部分填進去；追問時只填回答那一欄的部分；同句的其他話另外處理

- Rasa CALM 指令產生器（`rasa-calm-command-generator.txt`）：「If you asked the user a yes/no question (using a collect step) and they say “yes.”, the correct command output is SetSlot(slot_name, True).」「If the user answers the question but also requests something new, like “yes. Oh what’s my balance?”, the command output might be [SetSlot(slot_name, True), StartFlow("check_balance")].」——同一句裡，答覆進欄位，其餘部分另成指令，不進欄位。
- 同檔提示詞：「Extract text slot values exactly as provided by the user. Avoid assumptions, format changes, or partial extractions.」——值逐字取自原話（本線現行值閘「值須是原話子字串」同此）；這條不分是不是追問回合。
- Microsoft Copilot Studio（`copilot-slot-filling.txt`）：「when a user answers "It costs 1000 dollars" to a question from a Question node configured to collect this entity, the agent recognizes that "1000 dollars" corresponds to the money type of information. When the agent extracts this information and saves it to a variable, it saves "1000" as a number even though the surrounding information was text.」——存的是答覆部分，不是整句。
- 不同做法：Amazon Lex `AMAZON.FreeFormInput`（`lex-freeform.txt`）：「It recognizes strings that consist of words or characters. The resolved value is the entire input utterance.」「AMAZON.FreeFormInput is only recognized when elicited for.」——追問時整句當值，就是本線現行 `_write_draft_fill_answer` 的做法；業主 r9 已裁「只填答覆部分」，本片不採。

### 2.2 追問某一欄時，不貪心地把同一句的值塞進別欄

- Rasa CALM slots（`rasa-calm-slots.txt`）：「We recommend setting ask_before_filling: true at the collect flow steps for slots that can be filled by the same entity in the same flow. This prevents the assistant from greedily filling all the slots with the same entity at the same time, when only one of the slots was requested.」
- Dialogflow CX（`dialogflow-cx-parameter.txt`）：「If the end-user provides multiple parameter values in a single conversation turn during form filling, usually only one form parameter is set. However, if the same parameters are defined as intent parameters in an intent referenced in the same flow, Dialogflow CX may set multiple form parameters in a single conversation turn. This behavior is an optimization of NLU which may or may not occur during a conversation, so this behavior shouldn't be relied on.」——預設只設一欄；多欄是不保證的最佳化。
- 不同做法：Copilot Studio（`copilot-slot-filling.txt`）「proactive slot filling, which allows the user to specify multiple pieces of information that map to different entities, at once」「In cases where it's unsure of the intended mapping, it prompts the user to be more specific by providing choices.」——一句多欄可以，但不確定就問。

### 2.3 非答覆的話不填欄位；沒填到就再問

- Rasa forms（`rasa-forms.txt`）：「if you do not want any of the required slots of a form to be filled when the intent is chitchat, then you would need to define the following (after the form name and under the ignored_intents keyword)」；「While a form is active, if a user's input does not fill the requested slot, the execution of the form action will be rejected」。
- Rasa forms 驗證：「validation failed, set this slot to None so that the user will be asked for the slot again」。
- Dialogflow CX：「If a required parameter value is not provided by the end-user after an agent prompt, the initial prompt will be repeated unless a different behavior is defined in the reprompt handlers.」

### 2.4 已填的欄：客人明說要改才改

- Rasa CALM 提示詞（`rasa-calm-command-generator.txt`）：「`set slot slot_name slot_value`: Set a slot for the active flow. For example, `set slot transfer_money_recipient Freddy`. Can be used to correct and change previously set values.」——已填的值可以被客人的更正改掉。
- Rasa CALM flow steps（`rasa-calm-flow-steps.txt`）：「By default, a collect step is skipped if the corresponding slot is already filled.」
- 「道謝字被當成新值蓋掉已填欄」：**查無業界專節**。第一原理：已填值是客人先前給的資料；新值要蓋掉它，新值本身必須是資料（2.1、2.3）。
- 本片取的是比 Rasa 更嚴的做法（追問回合不覆寫已填別欄，業主 §6 第 2 點裁 B），偏離理由見 §4.3。

### 2.5 本線的分工（DSP-091）

「哪部分是資料、哪部分是答覆、哪部分是道謝」是理解，歸 AI；「填不填、填什麼、要不要重問」是寫入流程，歸程式。⛔ 用道謝詞表判斷（AR5；記憶「修法只修根層不特例」）。

## 3. 差距（對碼；可重跑）

讀碼指令在 repo 根執行。

| # | 目標形態 | 現況 | 查證 |
|---|---|---|---|
| G1 | 2.1 只填答覆部分 | 追問單一 text 欄、意圖沒給該欄時，**整句**填入：`wd.draft["fields"][key] = sanitize_data_piece(user_message).strip()`，記 `write_draft_answer_filled` | `grep -n "async def _write_draft_fill_answer" -A 40 rag-orchestrator/services/agent/runtime.py` |
| G2 | 2.1、2.3 非資料不進欄、不衍生別欄 | 意圖值併入草稿只過值閘；值閘只驗「值是原話子字串」「數字 token 出現在原話」：`re.findall(r"\d+", normalized)`——「3q」裡的 `3` 會過；「和平小屋 3q」是原話子字串也會過。不分是不是追問回合 | `grep -n "def _number_in_texts" -A 12 rag-orchestrator/services/agent/runtime.py`；`grep -n "if kind == \"text\":" -A 7 rag-orchestrator/services/agent/runtime.py` |
| G3 | 2.4 已填欄只被資料改 | 值過閘即覆寫，不看該欄是否已填：`draft["fields"][f.key] = value` 共 4 行，分屬 `_write_draft_merge_intent`、`_write_draft_merge_model_confirm`、`_write_proposal_merge`、`_write_candidates_deferred_names`；候選集名稱另由 `_write_candidates_apply_name`、`_write_candidates_replay_names` 寫名稱欄 | `grep -n 'draft\["fields"\]\[f.key\] = value' rag-orchestrator/services/agent/runtime.py`（4 行） |
| G4 | 2.5 理解歸 AI | 寫入意圖呼叫不知道程式正在追問哪一欄（系統句沒有追問欄位）；也沒有輸出「哪部分是資料」 | `grep -n "def write_intent_system_prompt" -A 35 rag-orchestrator/services/agent/write_forms.py`（參數只有 enum_labels、modifies_flag、pick_rule、rechoice_type、target_picked、dialog_act） |
| G5 | 2.3 | E 片 `_dialog_act_not_field_answer`：標籤 `none` ⇒ `return False`，照現行填（G1、G2 路徑）；這是 X9 F1 的出口 | `grep -n "def _dialog_act_not_field_answer" -A 40 rag-orchestrator/services/agent/runtime.py` |
| G6 | — | 整句填入有 3 個呼叫點（候選集兩處、一般一處），都在 `_write_draft_merge_intent` 之後。值閘 `_write_draft_gate_value` 以 `wd.user_texts` 比對的呼叫點有 6 個，全部處理**本回合**的值：①`_write_draft_merge_intent`（意圖值）②`_write_draft_merge_model_confirm`（模型自呼 `confirm.request` 參數，供之後回合用）③`_write_proposal_merge`（模型自呼提議）④`_write_candidates_deferred_names`（③暫存的名稱值）⑤`_write_candidates_apply_name`（本回合「改講新名稱」）⑥`_write_candidates_replay_names`（本回合收集的名稱值）。意圖等待逾時時，提議比意圖合併先到（`_write_proposal_handle` 內註解「程式優先入口沒成立（意圖等待逾時）時，提議比意圖合併先到」）⇒ 此時資料段未知 | `grep -n "_write_draft_fill_answer(acc" rag-orchestrator/services/agent/runtime.py`（3 處）；`grep -n "_write_draft_gate_value(" rag-orchestrator/services/agent/runtime.py`（定義 1＋呼叫 6） |
| G7 | — | 寫入意圖呼叫在每個使用者文字回合都送（`_start_write_intent_call`：`acc.write_draft` 非 `None`、非文件回合、看得到任一 `jgb2.action.*`；`pick:` 回合不送），第一句開口也送；建構點 3 處（`write_intent_system_prompt(` 的呼叫點） | `grep -n "def _start_write_intent_call" -A 20 rag-orchestrator/services/agent/runtime.py`；`grep -n "write_intent_system_prompt(" rag-orchestrator/services/agent/runtime.py`（3 處） |

正對照：G2 的 grep 同時命中 `def _number_in_texts`（必然存在）；G6 兩條 grep 命中 3 處與 7 處、G7 第二條命中 3 處即正常，0 處＝指令壞了。

## 4. 路徑

### 4.1 做法（一個改動，所有寫入回合共用）

**適用範圍**（業主 §6 第 1 點）：「寫入回合」＝本回合送出了寫入意圖呼叫（G7 的條件）。其中「追問回合」＝回合開始、送出意圖呼叫之前，依程式已知狀態判一次並存進回合內狀態：`wd.had_draft`、`wd.asked` 非空、非凍結。追問回合只有一種情況排除：意圖呼叫回了**一個驗證過、且與草稿不同的 `FORMS` 動作**（即現行 `other_action`）⇒ `_write_draft_target` 換新草稿，該回合改依「非追問的寫入回合」處理（資料段照用，見 B）。本回合草稿因任何原因（意圖、主模型提議 ③、模型自呼 `confirm.request` ②、缺欄追問寫點 `_write_draft_record_asked`）換成另一動作的草稿 ⇒ 該回合對新草稿一律依非追問寫入回合處理：B4 不填、B5 不套、`answer_text` 不用；B4、B5、`answer_text` 只在「目前草稿＝回合開始那份草稿（動作相同）」時生效。寫入意圖呼叫沒送的回合（文件回合、`pick:` 回合、開關 off）與改前逐字相同。本片的保證以 A+ 三個開關皆 on 為前提（`_confirm_model_reason` 回 `flag_off` 的那支，模型自呼 `confirm.request` 照模型參數執行，不經 ①～⑥）；單獨關掉 A+ 時本片保證不成立。

**A. AI 標出資料段（理解）**：寫入回合，寫入意圖呼叫多帶：
1. 系統句末尾接一段規則與定義：
   - `data_texts`：最新一句裡屬於資料的部分，逐字照抄，**依原句順序拆成若干段**（道謝、寒暄夾在中間時從那裡斷開）；道謝、寒暄、應答詞、閒聊、要真人、與這筆資料無關的新請求都不算；沒有資料回空陣列。
   - 追問回合另加程式持有的「正在追問的欄位」（表單欄位標籤，⛔ 帶使用者原話）與 `answer_text`：`data_texts` 裡**只回答正在追問那一欄**的部分，逐字照抄，不含引導語與別欄資料；沒有填空字串。
2. schema 根層加必填 `data_texts`（字串陣列）；追問回合另加必填 `answer_text`（字串）。
3. 建意圖呼叫有 3 處（G7：`_start_write_intent_call`，以及候選段 kwargs 帶 `target_picked=picked_id`、`pick_rule=True` 的兩支），三處一律接同一段規則與 schema；FA8、FA9 (k) 逐處各一條測試。

**B. 程式用資料段閘門（決定）**——寫入回合，全部收在一個新的「本回合閘門原話」helper，6 個值閘呼叫點（§3 G6 ①～⑥）一律改用它，⛔ 各點各寫：
1. **驗資料段**：`data_texts` 的每一段，去空白後須是最新一句去空白後的子字串，**且它在最新一句原句（未去空白）裡對應那一段的起訖不切斷數字或英數連續字串**（起點前一字與第一字、終點最後一字與後一字，不得同為數字或同為 ASCII 英數；空白本身算邊界，所以「1500 3q」的「1500」成立；「15000」切成「1500」、「2026/11/15」切成「2026/11/1」⇒ 不成立；原句出現多次時任一處兩條都成立即可）。`answer_text` 須是某一段資料段的子字串，同樣兩條。邊界檢查只用來把「AI 切錯」導向 fail-closed，不是安全邊界——切斷數字由 (i) 的整數 token 比對（`_number_in_texts`）與日期正規式 `(?<!\d)…(?!\d)` 本來就擋。空字串段、全空白段略過（不帶任何值，也不算不成立）；(iii) 一律以陣列**逐段**比對，⛔ 先串接——值橫跨兩段即拒收。任一段不成立、鍵缺、值為 null 或型別不對（`data_texts` 非字串陣列、`answer_text` 非字串）、意圖回 `None`（逾時、例外、無法解析、ambiguous、值域外）、或模型提議比意圖結果先到 ⇒ 本回合「資料段未知」。資料段的唯一來源是 `_await_write_intent` 驗過的那個物件（同一個 helper 取用）；③ 處理時意圖結果尚未取用 ⇒ 資料段未知，⛔ 直接解析 task 原始回應。`action=none` ⇒ 兩鍵由原始物件讀（比照 `pick_id` 的讀法），有效就用、無效就當資料段未知。主模型提議的動作 ⛔ 拿來判定資料段或脫離追問回合。
2. **資料段未知（fail-closed）**：本回合 ①～⑥ **一律不併任何值**（值與草稿現值相同者例外，見 B3），記 `fill_data_text_unknown`、⛔ 記「使用者的值被丟」統計（`user_value_dropped` 的計數用途），追問欄不填，走 B6 重問。**狀態句另用回合內旗標「本回合有值沒套用」**：資料段未知、或 (iii) 拒收任一值 ⇒ 設旗標；綁定卡仍有效的回合，旗標成立 ⇒ 狀態句用 `CARD_UNCHANGED_TEXT`（「這次的修改沒有套用…」），⛔ 出 `CARD_STILL_VALID_TEXT`（「卡片還在，請按確認。」）——現行 `_write_draft_card_still_valid_exit` 只看 `user_value_dropped`，客人要改的值被擋下時會被叫去按確認、送出舊值。第一句的動作仍照現行建立草稿（動作不是欄位值），欄位留空、由程式追問缺欄。比照 r6「逾時後備改成重問缺欄」。
3. **兩道都要過（G2；只縮不擴）**：資料段為空陣列 ⇒ ①～⑥ 一律不併新值，enum／category 也一樣（業主 10-27 裁 C1 (a)；最壞結果是重問）。資料段已知且非空時，①～⑥ 的每個值依序：(i) 現行值閘照舊比 `wd.user_texts`（⛔ 改），不過 ⇒ 照現行拒收；(ii) 過了且 (i) 的正規化結果等於草稿該欄現值 ⇒ 草稿不變、不記值被丟（重述已併的值；比的是正規化值，「1,200」「11/1」重述不會被誤擋）；(iii) 否則再以同一值閘、只拿 `data_texts` 當原話比一次，不過 ⇒ 拒收、記 `fill_value_outside_data`。所以「和平小屋 3q」不是任何一段資料段（「我要新增一個物件叫和平小屋」「在台北市大安區…」）的子字串 ⇒ 拒收、名稱欄由程式追問；先前回合有「3 月份」也擋得住「水電費 3q」的 `3`；(i) 擋得住的值 (iii) 不會放行。存進草稿的一律是 (i) 的輸出（例：`period` 的「未繳」後綴依 `wd.user_texts` 判），(iii) 只判過或不過。(ii) 的副作用與現行「同值重併」相同（`provided`、`touched`、`merged` 照現行設），不另加也不另減；FA9 (l) 測。text 型值閘是子字串比對，資料段「租金 15000」裡的 text 值「1500」仍過得了 (i)、(iii)——這是現行就有的，本片不擴也不修（int／number 由整數 token 比對擋）。enum／category 兩型的值閘不比對原話（`_write_draft_gate_value` 的 `enum`、`category` 分支），所以資料段非空時 (iii) 對它們不起作用，保護靠 B5；資料段非空時，空的 enum／category 欄仍可能由 AI 推測，由 FA1 `repair_create` 組量；確認卡出現後打字補充的回合不套 B5，句中有資料段時，已填的 enum／category 欄可被 AI 推出的標籤覆寫，程式不擋——由 FA1c `repair_create` 組「已填 enum／category＋補充＋道謝」輸入量，錯卡 ≥1 即停（§8）。純道謝、寒暄（資料段空陣列）不會改到任何型別的欄。
4. **只填答覆（G1）**：追問回合的整句填入改填答覆段——由程式從最新一句原句切出 B1 對到的那一段原字（⛔ 直接用模型回的 `answer_text` 字串，避免模型插入的 U+3000、U+00A0 等空白進卡），再過 `sanitize_data_piece`、照現行 `WF.value_max_len(f)` 做長度拒收；答覆段為空 ⇒ 不填；同時追問多欄時照現行只在恰好追問一欄時填（`answer_text` 在多欄時不用）。「水電費，1500」⇒ 帳單項目填「水電費」，`1500` 只能經意圖值進 `total`。
5. **已填欄（G3，FA-R4，業主 §6 第 2 點裁 B）**：追問回合裡，已填的**非追問欄**一律不覆寫，記 violation，客人要改在卡上更正。適用欄位集合：**候選集綁定的那一欄**（`wd.candidates["field"]`）在 ①～⑥ 全部 6 處一律照 W1c／F12 既有名稱規則（`_write_candidates_name_rule` 的 drop／same／new／collect；改選、改講新名稱是那套規則的明示操作），⛔ 套本條，只套 B3；其餘已填非追問欄在 G3 的 4 處賦值點套本條。非追問的寫入回合（第一句、確認卡出現後的補充）覆寫規則照現行，只加 B3。
6. **沒填到就重問（2.3）**：追問的欄位本回合仍缺 ⇒ 照現行缺欄追問句重問；第一句缺的欄照現行缺欄追問。
7. **資料段只活在本回合**：`data_texts`、答覆段只存在 `_WriteDraftTurn` 的回合內欄位（比照 `user_message` 的「只活在本回合」），⛔ 進 `agent_state`、草稿、trace、決策快照、日誌；新 violation 一律固定字串、⛔ 帶值。

②（模型自呼 `confirm.request` 參數）在寫入回合同樣套 B2、B3：它的值留給之後的回合用，不改變本回合那次呼叫（現行非目標不變）。

E 片的標籤呼叫不改：`wants_human`、`resolved`（含確認呼叫）各分支照舊；標籤 `none` 時也改走上面的 B，不再整句填。

**開關**：`AGENT_FILL_DATA_TEXT`，照 `write_draft_enabled_from_env` 樣式讀（on／off、未設＝on、其他值 `ValueError`、啟動失敗），屬性讀取 ⛔ 用預設 off 的 `getattr`；off ⇒ 與改前逐字相同，由 FA8 的 off 測試保證（只供回復，不跑 off 對照批，§7）。

### 4.2 改動檔（預估）

- `rag-orchestrator/services/agent/write_forms.py`：`write_intent_system_prompt`、`write_intent_call_schema`、`write_intent_response_format` 加資料段規則與 `asked_labels` 參數；新規則常數；新 violation 常數。
- `rag-orchestrator/services/agent/runtime.py`：建意圖呼叫的 3 處接規則與追問欄位；回合開始判追問回合；資料段存回合內欄位；新 helper「本回合閘門原話」；§3 G6 ①～⑥ 六個值閘呼叫點改用 helper；`_write_draft_fill_answer` 改填答覆段；G3 四處賦值點加追問回合不覆寫判斷；開關讀取。
- 新單元測試 `rag-orchestrator/tests/unit/agent/test_fill_data_text_req.py`（FA8、FA9 (a)～(t)、B1～B7 逐條；①～⑥ 每個呼叫點至少一條；3 個意圖呼叫建構點各一條）。
- 文件：`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`（A2 段、§8 已知限制）、目標正本 §4 片狀態、HANDOFF、`.claude/DECISIONS.md` 新 DSP、`.claude/MAP.md`。

### 4.3 偏離目標形態的取捨

| 偏離 | 理由 |
|---|---|
| 不照 Rasa `ask_before_filling`／Dialogflow「只設一欄」把追問回合鎖成只收追問欄 | 目標正本 §1 使用者成功第 2 點「說過的不被重問」；同句另給的資料（「水電費，1500」）照收，比照 Copilot proactive slot filling。代價：資料段若被 AI 標錯，空的別欄仍可能進錯值——由 FA1、FA3 量 |
| 追問回合不覆寫已填別欄，比 Rasa「Can be used to correct and change previously set values」嚴 | 業主 §6 第 2 點裁 B：錯筆不得後補（DSP-115 第 3 點），只靠 AI 標對不夠；代價是追問中順口講的更正要到卡上再改一次 |
| 資料段由 AI 標，不由程式比對道謝詞 | DSP-091 理解歸 AI；AR5 不靠詞表。代價：AI 標錯時會漏。B1、B2 fail-closed；B3 是「現行值閘 ∩ 資料段值閘」，所以只縮不擴；資料段空陣列時任何型別都不併（含 enum／category，C1 (a)），最壞結果是重問；資料段非空時，text／int／number 最壞結果是重問，enum／category 不比原話、另靠 B5 與 FA1、FA1c 量——除非 AI 把道謝字標進資料段或答覆段（含資料段＝整句，結果與現行相同，程式端不攔，由 FA0、FA1 量）。同 repo 有反證：E 片在標籤呼叫系統句附上追問欄位時，AI 把「OK 3q」讀成名稱而出錯筆卡（`runtime.py` `_start_dialog_act_call` 的註解「⚠️ 系統句勿附「正在追問哪一欄」」）；本片追問回合同樣附追問欄位，所以 FA1a 加「追問名稱欄＋純／近純非資料」輸入，X4 錯卡 ≥1 即停 |
| 寫入回合的值閘不再只比先前回合原話 | 堵「先前回合有同一個數字」的漏洞（FA9 (d)）。代價：模型在本回合才補併先前回合講過、但當時沒併進的值，會被擋下改由程式重問——B3 的「與現值相同不經閘」讓已併的值不受影響 |
| 意圖呼叫逾時、提議先到時，第一句的欄位也不併 | fail-closed（2.3「沒填到就再問」）；代價是逾時回合客人要再講一次，由 FA2、FA5 量重問與解決數 |

### 4.4 修正 10 重新比較（FA-R7）

| | 修正 10（E 片 r7，已退回） | 本片 |
|---|---|---|
| 改哪裡 | 標籤呼叫系統句附上「正在追問哪些欄」，讓「答覆＋道謝」不被標 `resolved` | 寫入意圖呼叫標資料段與答覆段，填欄只用答覆段、值閘只用資料段 |
| 解決什麼 | 「答覆＋道謝」被跳過不填（X8 發現 1，14/15） | 「答覆＋道謝」填進道謝字、衍生別欄（X9 F1，11/17）；第一句帶道謝出錯卡（探針） |
| 實測 | 兩版實跑都出錯筆卡（`arch/e/report-e-close.md` 第 11、12 點）——因為標成 `none` 之後仍走整句填入 | 待量（FA1、FA2） |
| 關係 | 修正 10 只決定「要不要填」；錯卡出在「填什麼」。本片修好「填什麼」之後，修正 10 的錯卡理由不再成立 | — |

建議：本片**不恢復**修正 10。修正 9 的現況是「答覆＋道謝」被標 `resolved` 時，再由確認呼叫判斷；確認呼叫判 `none` 才照填，否則重問——多問一次，但不錯卡。FA2 另列「答覆＋道謝被重問」的場數：改後 0 ⇒ 結案；>0 ⇒ 收案報告交業主裁「是否恢復修正 10（改填資料段後）」，⛔ 主會話自行恢復。

## 5. 驗收

見規則檔三節（FA0～FA11）與 ## 廣度。判法：FA1～FA3 每場由程式依撰寫者標註判，結果分四類——
1. **填入**：卡上各欄值包含標註的資料、不含標註的非資料部分（追問場看追問欄是否含標註的答覆）；
2. **重問後填入**：程式重問某欄 ⇒ 驅動程式只再回一次撰寫者標註的該欄資料（純答覆），之後同 1 判；重問不算錯卡，另計「重問」場數（FA-R7、FA-R9 用）；
3. **重問後仍未填**：驅動程式回過一次後仍重問 ⇒ 記「卡住」，不算錯卡，列出交主會話查根因（FA2 以此計退步）；
4. **錯筆卡**：任一時點卡上欄位含標註的非資料字，或別欄值不等於 setup 值或撰寫者列出的預期值。
判不出（標註、卡面與追問句都對不上）的場列出，交 fresh 盲判代理判；盲判輸入含輸入句、標註、每回合系統回話與卡面（沒出卡的場只有回話）。

## 6. 業主裁示

2026-10-27，AskUserQuestion（計畫 r3 收尾審查後）：
1. Q5 範圍：選「擴到所有寫入回合 (Recommended)」。選項說明原文：「同一套「AI 標資料段、程式只用資料段填欄與過值閘」套到每個寫入回合，不只追問中。要改計畫 §4.1 與清單（加第一句帶道謝的輸入），再送一次審查才交核可。代價：非追問回合不再逐字不變，回歸面變大（M0、E2a 都要看）。錯卡＝0 是上線擋點，一次修完不用再開一片。」
2. Q1「不蓋掉已填的欄」：選「B 一律不覆寫 (Recommended)」。選項說明原文：「追問回合裡已填的別欄一律不覆寫，客人要改到確認卡上更正。保證不會被道謝蓋掉，代價是順口講的更正要多改一次。候選綁定的名稱欄照既有 F12 規則。」
3. FA-R1：選「擴及寒暄應答 (Recommended)」。選項說明原文：「「好 冷氣不冷」只填「冷氣不冷」，「OK 3q」不填任何欄。FA1 的寒暄應答類輸入算錯卡判準。」
4. M0：選「同意兩者 (Recommended)」。選項說明原文：「照 E 片前例：改前量的 M0 同時當現值與改前對照；預期 0 的列只看不退步。」（題目：核可後、改程式前先量 M0（約 57 分），並同意本片在 M0 各列、道謝後轉真人、E2a、單元測試、audit 的預期變化都是 0。）

2026-10-27，AskUserQuestion（計畫 r4 收尾審查 C1 後）：
5. C1 空資料段：選「(a) 空陣列一律不併 (Recommended)」。選項說明原文：「資料段為空陣列時，①～⑥ 六個合併點都不寫入新值，enum／category 也一樣，與 FA9 (q)「不併任何新值」一致。順手改計畫 §4.3 第 3 列、B3 尾段、FA1c 差距說明，FA9 (q) 加一個 enum 案例（emergency_status）。最壞結果是多問一次。」
6. 下一步：選「修完直接交你核可 (Recommended)」。選項說明原文：「收尾審查不再重開循環。改完標「已修、未再審」，連同 4 條可後補一起交你核可。你核可前不動程式。」

2026-10-27 業主核可本計畫 r4（對話原文「核可計畫 r4」；核可時 C1 為「已修、未再審」）。

2026-10-27，AskUserQuestion（X4／X4b 錯筆卡 ≥1 停點後；根因探針：AI 把「3q／3Q」「麻煩囉」標進資料段，程式照設計放行）：
7. 修法：選「規則句加說明＋舉例 (Recommended)」。選項說明原文：「在 data_texts 規則句寫「道謝也包括網路縮寫與口語」並舉 2～3 例，例子刻意避開凍結輸入用過的詞，免得量測放水。改完重跑 X4、X4b、X5、X6，X8 另寫新說法。代價：等於在 AI 端補一小段詞表；沒舉到的縮寫仍會漏（探針裡 ty 3/3 錯），錯筆卡未必能到 0。」題目原文：「錯筆卡的根因是 AI 不認得「3q」是道謝。修法要走哪條？（三條都會同時查 X5／X6 的退步）」
8. 第 7 點的前提被探針推翻（舉例避開凍結輸入用過的詞 ⇒ 「水電費 3q」等 6 句仍 3/3 標錯；只有點名「3q」才修好）後重問：選「規則句直接點名常見道謝 (Recommended)」。選項說明原文：「在 data_texts 規則句點名 3q／3Q、thx、麻煩囉這類常見網路與口語道謝。探針：點名的 3/3 全對，未點名的 tks、感恩啦、辛苦了、謝囉也對，ty 3/3 錯。代價：X4／X4b 含這些詞，改善幅度只算中間證據，成效以 X8 新說法為準；未點名的縮寫仍可能漏，錯筆卡未必為 0。」題目原文：「「避開測試詞的舉例」實測修不好 3q。「3q」要怎麼處理？」
   同輪另修本片引入的退步（主會話處置，未另問；派工單 `arch/fill/brief-fix1.md`、`brief-fix1c.md`、`brief-fix1d.md`）：
   - RC2：AI 把前面回合的資料抄進 `data_texts` ⇒ 不在最新一句的段略過（記 `fill_segment_not_in_message`），其餘 B1 規則不變。
   - RC4 形狀 A：追問兩欄以上時 `answer_text` 不成立 ⇒ 只當沒有答覆段，資料段照存（單欄追問仍整回合未知）。
   - RC4 形狀 B：未選定候選回合 AI 常把 `data_texts` 回成 `[]`（探針 7/8）⇒ 該回合系統句在 `DATA_TEXTS_RULE` 後接 `DATA_TEXTS_PICK_NOTE`（探針 16/16 切對；只給 AI 讀、不點名任何詞）。
   - E2 收尾 63/64 → 58/64 不是 B6 搶 E 片出口：那 6 場是鋪陳失敗（setup_ok=false，成因即 RC2、RC4），E 片出口程式未改。

2026-10-27，對話（第 2 輪改後量測 X4 錯筆卡 22→3、卡住 27→57 後，業主問「建議是 ?」）：
9. 業主回「好，照你建議做」。建議原文要點：再修一輪，只修卡住的前兩大成因（首句請求裡的資料被丟、後續回合的值被擋），逾時的 5 場不動；一輪後就停，成效以 X8 新說法為準；X8 的卡住仍明顯高於改前 ⇒ 建議縮小範圍（嚴格資料段只留追問回合），數字並列交業主裁（等於部分收回第 1 點 Q5）。
   這一輪的處置（主會話處置，未另問；派工單 `arch/fill/brief-fix2.md`、`brief-fix3.md`）：
   - P3-2「後續回合的值被擋」主形狀：候選清單已列、客人沒點、下一句 AI 把前句名稱再寫進候選綁定那一欄 ⇒ (iii) 擋下 ⇒ 名稱永遠缺。修法：候選集未選定、仍綁定本草稿時，綁定那一欄只過 (i)（記 `fill_bound_field_exempt`）。已知副作用：綁定欄的值可能帶本句的道謝字（例「基隆溫心一人宅 3q」），與 off 相同；這個值只用來查物件，物件卡印的是系統查到的名稱 ⇒ 接受，記後補。
   - P3-1「首句請求裡的資料被丟」：原先推測是 AI 不把請求句裡的欄位內容當資料，探針推翻（`scratchpad/probe3q/probe12.py`：5 句各 5 次，現行規則句 24/25 有列資料段）。逐場重放（診斷版只加 print、常駐重建時換回）：這幾場在修完 P3-2 的版本重放 4/4 首句值都有進草稿，第 2 輪那幾場是 AI 單次變異加逾時，不另修。
   - 重放中找到的另一形狀：追問中客人一次補多欄但還沒補齊（合約第 3 句），AI 常回 `action: "none"`、`fields: []`（推理原文「Not complete yet. So action none.」；探針 13：off 5/8、on 6/8）。off 靠後一句 AI 把前面的值全列一次補回，on 的 (iii) 照設計擋前句值 ⇒ 卡住。修法：開關 on 時系統句在 `WRITE_INTENT_NONE_RULE` 後接一段「只補了一部分也照進行中的動作填 action、列 fields」（探針 13：6/8 ⇒ 1/8；反向對照探針 14：追問中講非資料的 5 句，現行與加這段都是 0/20 列出欄位）。只給 AI 讀，程式不比對任何詞。
10. 第 9 點那輪修完後量 X8 新說法（fresh 撰寫代理 106 句、5 表單，同一受測物 on 對 off；`arch/fill/x8_compare.md`）：卡住 on 16、off 8；錯筆卡 on 3、off 4。AskUserQuestion 題目原文：「X8 新說法上，改後卡住 16 場、改前 8 場；錯筆卡改後 3、改前 4。下一步要走哪條？（兩條都會一併修「卡後更正沒套用卻說卡片還在」這個改前就有的錯筆卡）」業主選「縮小到追問回合 (Recommended)」。選項說明原文：「照你上次同意的備案：嚴格資料段只留在「程式追問某欄、客人回答」的回合；第一句、卡後打字、一句補多欄的回合改回現行值閘。預期卡住回到接近改前；代價是第一句帶道謝的保護變弱（X4 第一句錯筆卡改後 0，改前 4），等於部分收回 Q5「擴到所有寫入回合」。改完重跑 X4、X4b、X8，再進 M0 與驗證員。」
   主會話讀法（我先這樣做了，要改請說）：「程式追問某欄」＝上一回合程式追問的欄位只有一欄（多欄追問已依 RC4-A 不用答覆段，歸「一句補多欄」）；其餘寫入回合與開關 off 完全相同。FA-R1、FA-R3、FA-R4、FA-R5 的「錯筆卡＝0」範圍跟著收窄到單欄追問回合；第一句、卡後打字、多欄回合的錯筆卡照實報、與改前比，不擋收案——但「卡後更正沒套用、程式卻回「卡片還在，請按確認。」」這一形狀照 FA1c 判準仍須 0（兩版都有，屬寫錯資料，DSP-115 第 3 點）。
   這一輪的處置（第 10 點範圍內，主會話處置，未另問；派工單 `arch/fill/brief-fix4.md`、`brief-fix5.md`）：
   - 修復輪 3：`_fill_begin_intent_call` 只在單欄追問回合啟用；卡後回合沒讀到任何值 ⇒ `CARD_NO_CHANGE_TEXT`「卡片內容沒有變更；要送出請按確認，要改請按「我要修改」。」（兩個卡後出口、on／off 皆生效）。
   - 修復輪 4：第 4 輪 X4 `FA1c-rep-06`（卡後「問題描述再加一句：遙控器也沒反應，謝啦」，意圖只回與卡相同的物件名、描述沒讀到）仍回「卡片還在，請按確認。／這次讀到的是：物件…」。程式從狀態分不出「客人沒要改」與「AI 漏讀了要改的欄」（要分辨得看詞，DSP-091 ⛔）⇒ B 片生效時，卡後讀到同值的前導句改 `CARD_READ_SAME_LEAD`「卡片內容沒有變更；要送出請按確認。」＋讀到行；B 片關照舊。主模型提議被值閘丟掉仍不算值被丟（A+ AP-2 Q2 照舊）。
11. 第 5 輪（修復輪 4 後）X4 單欄追問名稱回合錯筆卡 2 筆（`FA3-est-04`「復興100號3q」、`FA3-est-05`「3Q 晴空小舍」；改前同 2 筆錯，第 4 輪 2 筆皆對）。探針 17（`scratchpad/probe3q/probe17.py`，每句 8 次）：名稱與 3Q 緊貼或 3Q 在前 ⇒ AI 把 3Q 標進資料段與答覆段 3/8～7/8；有空白、中文道謝 0/8。探針 18（規則句後接名稱說明）：「復興100號3q」3/8→0/8、「3Q 晴空小舍」6/8→1/8、「大安溫馨套房3Q」6/8→6/8；反向對照「復興100號」「3Q公寓」「Q3 小屋」0/8 被切。AskUserQuestion 題目原文：「單欄追問名稱時，「大安溫馨套房3Q」「3Q 晴空小舍」這種名稱和 3Q 黏在一起（或 3Q 在前）的句子，AI 會把 3Q 當成名稱的一部分，卡上印出「物件名稱：…3Q」。第 5 輪 X4 有 2 筆（FA3-est-04／05，改前也是這 2 筆錯；第 4 輪 2 筆都對），X8 新說法單欄追問 0 筆、X4b 0/17。規則句已經點名 3q 並寫「緊貼也要斷開」，仍會漏。程式端要辨認 3Q 就得列詞表，違反 DSP-091。要怎麼處理？」業主選「補一句說明再收 (Recommended)」。選項說明原文：「規則句後補「名稱也一樣：緊貼在名稱前後的道謝縮寫不是名稱的一部分」。每句 8 次的探針結果：「復興100號3q」3/8→0/8、「3Q 晴空小舍」6/8→1/8、「大安溫馨套房3Q」6/8→6/8；本身含數字或英文的名稱（復興100號、3Q公寓、Q3 小屋）照原樣保留，0/8 被切。要多一輪改程式、重建、重跑 X4／X4b／X8，約 1 小時。剩下的漏網列為已知偏離：卡上看得到名稱，客人可以按「我要修改」。」
12. X7 M0 改後（`arch/fill/run/m0fa`，受測物 runtime `6dc04e03…`、write_forms `41ffac4b…`）K 列 20/20 → 19/20，碰 §7 X7 停點。AskUserQuestion 題目原文：「M0 改後的 K 列從 20/20 降到 19/20，碰到計畫停點「任一列 < 改前 ⇒ 停、交業主」。掉的那場是 K8_k2：同一句「報修單能附照片跟影片嗎 有啥限制」，改前正常作答；改後主模型輸出被截斷（llm_output_truncated），走預算耗盡轉真人。那回合沒有任何本片標記，改後全部 182 回合裡只有 1 回合用到本片。其他列：W 14→18（T4 16→19）、全部 46→49，盲判 45→46、K 14→14，道謝後轉真人 0→0。下一步怎麼走？」業主選「判非本片，派驗證員 (Recommended)」。選項說明原文：「K8_k2 列為已知偏離（主模型輸出截斷，屬既有行為），寫進收案報告與後補清單；接著派收案驗證員，請它一併核對這個根因判讀。約 1 小時。」
13. 收案 verifier X8b 判 REFUTED（`arch/fill/report-fill-close.md`「收案驗證」節）後，AskUserQuestion 三題：
   - 題目原文：「收案驗證員判 REFUTED：單欄追問回合「車位費ty」4/4 卡上印「帳單項目：車位費ty」，「民生東路溫馨居tks」也上卡。你第 8 點選的選項說明原文寫「探針：…ty 3/3 錯。代價：…未點名的縮寫仍可能漏，錯筆卡未必為 0」，第 11 點寫「剩下的漏網列為已知偏離」；但凍結規則 FA-R5 是錯筆卡＝0，DSP-115 第 3 點錯筆卡不得後補。這兩筆要怎麼處理？」業主選「依第 8、11 點列已知偏離 (Recommended)」。選項說明原文：「讀成你在第 8、11 點已接受「沒點名的縮寫可能漏」，ty、tks 列已知偏離，本片照實收案（驗證員 REFUTED、沒有 CONFIRMED，宣稱寫明這個漏網）。理由：程式端要認 ty 就得列詞表（違反 DSP-091），規則句每點名一個就會有下一個沒點到的；卡上看得到，客人可按「我要修改」，按確認前不會寫入。改前同一類句子整句填入，同樣會錯。」
   - 題目原文：「凍結清單 FA1a 寫「出現撰寫者沒列的別欄值，即錯」，判分程式沒做這條。實際出現的是：帳單項目「清潔費」，同時被帶進「說明：清潔費」。這是客人自己講的資料，不是從道謝衍生的。數量：X4 改後 3 張、改前 5 張；X8 開 2 張、關 1 張。這算錯筆卡嗎？」業主選「不算錯筆卡，列後補 (Recommended)」。選項說明原文：「你的原話是「卡上出現道謝字，或出現從道謝衍生的別欄值」。說明欄的值來自客人的資料，改前就有，改後沒有變多。」
   - 題目原文：「客人回「簡稱北投宅就好啦 感恩」，卡上的物件名稱是「簡稱北投宅就好啦」（「感恩」有去掉）。撰寫代理把「簡稱…就好啦」標成答覆的一部分，所以判成填入；關掉新功能時會重問，最後得到「北投宅」。這算填入還是錯筆卡？」業主選「算填入，列後補 (Recommended)」。選項說明原文：「卡上沒有道謝字，也不是從道謝衍生的值，依 FA-R1／R3 不算錯筆卡。名稱帶了口語，記後補。」

## 7. 執行與測試選擇（全域「測試選擇」）

每場時間依 E 片腳本實測：`arch/e/after9/E1/records.jsonl` 118 回合 2.3 分（約 1.2 秒／回合）；費用依 E 報告 `usage_events.est_cost_usd` 3,783 回合 US$3.9712（約 US$0.00105／回合）。

| 執行 | 回答的決定 | 會改變下一步的結果 | 規模與理由 | 跑前成本 |
|---|---|---|---|---|
| X0 寫輸入（fresh 代理） | FA1～FA3 的輸入凍結 | 配額不滿 ⇒ 退回補寫 | 1 位代理；5 表單 × (13＋8＋5＋7＋4)＋5 × 5 ≈ 210 句 | E 片同類撰寫代理約 5～6 萬 token（`arch/e/report-e-close.md` 子代理 token 段：盲判／撰寫代理 3.3～5.6 萬），本次句數較多，估 6～8 萬 |
| X1 M0 改前（核可後、改程式前） | 終點現值；FA5 改前對照 | 數字即現值；改後 < 改前 ⇒ 不收、查根因 | M0 全 56 場（終點量測，「測試選擇」第 2 條第一種時機） | 57 分（`arch/e/run/m0after/convs` 20:49:46～21:46:48）；模擬客人 6 位 326,830 token＋盲判 6 位 298,450 token（E 報告）；Bedrock 約 340 回合 ≈ US$0.36 |
| X2 FA1～FA3 改前 | 錯筆卡改前值（新輸入）；FA2 被重問基準 | 改前 FA1a、FA1b 錯卡皆 0 ⇒ 輸入沒打到缺陷，退回 X0 重寫 | 約 210 場 × 約 3 回合 | 約 13 分、約 US$0.66 |
| X3 單元測試、audit、canon-accept | 改後能否進入使用者層量測 | 新失敗 ⇒ 修到全過才跑 X4 | 全套（便宜且決定性） | 約 3 分（`unit.out` 180.96s） |
| X4 FA1～FA3 改後 | 錯筆卡是否 0；純答覆是否退步；修正 10 要不要交裁 | 錯卡 ≥1 ⇒ 停、查根因、修；FA2 被重問 >0 ⇒ 列業主待裁；`write_intent_unparsed` 與重送標記數改後明顯多於改前（輸出變長致截斷）⇒ 查根因再判 FA2 | 同 X2 輸入 | 同 X2 |
| X4b FA0 X9 同批 17 場改後 | 鎖定缺陷是否修好（終點表「錯筆卡」列的收案值） | 錯卡 ≥1 ⇒ 停、查根因、修 | 改動會碰到的同一批（「測試選擇」第 2 條；17 場全是追問回合，其中 11 場先前沒過）：`arch/e/x9-verifier/drive_x9.py`＋`inputs_x9.json`（6 場）、`rep/drive_x9.py`＋`rep/inputs_x9.json`（11 場）；改前值已有（X9 在修正 9 受測物實跑），不另跑 | 1.1 分（`run_r8` 6 場 18 回合 0.5 分＋`rep/run_r8` 11 場 32 回合 0.6 分，`records.jsonl` 的 t0／t1）；50 回合 ≈ US$0.05 |
| X5 FA4 E 片題組改後 | E 行為是否退步 | 任一組 < after9 ⇒ 停、查 | E1～E4、E14 全部場：每個使用者文字回合都送寫入意圖呼叫（G7），全部碰到（「測試選擇」第 2 條「改動會碰到的」）；改前用 `arch/e/after9/`（同一受測物） | `arch/e/after9/{E1,E2,E3,E4,E14}/records.jsonl` 計 195 場 571 回合 ⇒ 約 11.4 分、約 US$0.60 |
| X5b FA4b F12 名稱與選定後指令式題組改前改後 | 候選、選定、改講名稱是否因資料段閘退步（安全差異審查待查 3） | F3″ (2) 改後 < 改前、或 F8 錯筆卡 ≥1 ⇒ 停、查 | F3″ 40 種首句（`arch/f12/r5/inputs_r5.json` 的 `f3pp`，全是第一句帶名稱的寫入回合）、F8 20 個輸入（`arch/f12/cmd/f8/verifier-r1p4/`，選定後回合）：全部碰到；F12 收案值量於 F12 程式、不是現行受測物，所以改前同日重跑。驅動：跑前找出 F12 收案時的既有驅動並列路徑，找不到依輸入檔重寫並在報告寫明 | 依每回合約 1.2 秒、US$0.00105：F3″ 約 120 回合、F8 約 80 回合 ⇒ 每次約 4 分、US$0.21；改前改後共約 8 分、US$0.42 |
| X6 FA6 E2a 改後 | 寫入回歸 | 任一組 < 改前 ⇒ 停、查（DS 依前例補跑 1 次） | 六組 × 2 輪（改動碰到）；改前用 `arch/e/e2a/after9/`（同一受測物，X9 核過 AST 相同），不另跑 | 每次約 44 回合、約 1 分、US$0.05 |
| X7 M0 改後 | 終點變化 | 任一列 < X1 ⇒ 停、交業主 | 全 56 場（終點量測） | 同 X1 |
| X8 收案 verifier | 宣稱是否成立 | REFUTED ⇒ 依發現處置 | 1 位 fresh verifier，另寫 ≥10 句新輸入、換表單換說法、含第一句與追問回合 | E 片 X9 247,784 token |

不跑：開關 off 對照批（回答不了任何決定：off 與改前逐字相同，由 FA8 的 off 單元測試保證）。

**分工與獨佔**：核可後，程式改動（`write_forms.py`、`runtime.py`、新測試檔）交一位 security-executor 獨佔（值閘屬寫入前驗證，依全域安全路由 ⛔ 用一般 executor），brief 帶 §4.1 全文、FA8／FA9 與 Hard rules；主會話獨佔文件、常駐重建、X0～X7 量測與結果判讀；X0 撰寫代理、X8 verifier 只讀不寫 repo。

**用量報告**：收案報告列子代理 token 加總（依任務通知 `<subagent_tokens>`，逐位列）與 Bedrock 費用（`usage_events.est_cost_usd`，起訖時間與查證 SQL），格式比照 E 報告。

## 8. 停點、回復、待業主

**核可時要業主裁**：本計畫的核可（§6 四題已裁）。

**停點**：X2 改前 FA1a、FA1b 錯卡皆 0（輸入沒打到）；X3 新失敗；X4、X4b 錯卡 ≥1；X5、X5b、X6、X7 任一退步；verifier REFUTED 且屬 DSP-115 第 3 點。

**回復**：開關 `AGENT_FILL_DATA_TEXT=off` 重建常駐即回到改前行為（A+ 三個開關維持 on，本片保證以其為前提）；程式回復以 `arch/fill/baseline/` 備份（改程式前備份改動檔）＋`git diff` 還原。

## 9. 後補清單（DSP-115）

r4 收尾審查的可後補項（DSP-115 第 2 點，收案時一起處理；r3 收尾審查的 5 條已在 r4 改掉）：
1. FA0 只用 3／5 組，另兩組（`bill_due_extend`、`contract_create`）未逐組寫理由（同題重測只限 X9 原批，其他組由 FA1a～FA3 覆蓋）。
2. §7 X8 只寫 token 成本，未寫場數 × 每場時間。
3. FA1b 未列錯字、簡稱類；FA3 說法類別未含口語、錯字、簡稱——X0 撰寫配額補上。
4. §0 E2a 列選對紀錄片漏了 D（`report-pick.md` V8 原文「R、D、C、T 2/2」）。

修復輪中記下的後補項（不改變下一步；收案時一起處理）：
5. 候選綁定欄的值可能帶本句道謝字（例「基隆溫心一人宅 3q」），與 off 相同；只用來查物件，卡上印系統查到的名稱（§6 第 9 點 P3-2）。
6. 單欄追問回合中草稿被換成另一動作（主模型提議另一動作、缺欄寫點換草稿）時，`fill_active` 仍為 True，資料段閘套在新草稿上（B4、B5 已由 `_fill_followup_now` 排除；修復輪 3 前即如此）。
7. 卡仍有效、客人問問題而沒讀到值（例「送出後多久會處理？」）時，前導句也改成 `CARD_NO_CHANGE_TEXT`（修復輪 3 兩個出口都改）；措辭在問句回合是否合適待收案時看。
8. 卡後打字時寫入意圖 AI 偶爾回另一支動作（X8 診斷重放 `FA1c-bill-03`：帳單卡上「繳費期限改到 2026/12/20」回 `bill_due_extend`、無欄位 ⇒ 程式改追問延後繳的欄位）；與本片無關，改前同樣可能。
9. X5 E4 程式轉人：第 3 輪 2/48（after9 0），來自 E 片標籤 `dialog_act_exit`（「上次真人客服說退租的話要…」「還是只能在後台問…」）；第 4 輪（修復輪 3 後）0/48（`fill/x5_4/E4`），不再出現。
10. X5 E3 確認卡組 `U3a-5`：卡出現後客人打「3Q」，主模型走知識查無出口轉人（「這題我這邊沒有可靠資料，幫您轉專人…」），第 4 輪 1/20（after9 0/20、第 3 輪 0/20）。修復輪 3 後卡後回合的寫入意圖與 off 相同，該回合 violations 只有 `dialog_act_call`；卡未被改、之後按確認照常建立。不寫錯資料，列後補。

## 10. 審查紀錄

**r1（fresh plan-verifier，2026-10-27）：REVISE**，阻擋 6、可後補 5、待查 3。處置：

| 發現 | 處置 | r2 改了什麼 |
|---|---|---|
| B1 錯筆卡列沒有改後重跑 X9 同批 | FIX | §7 加 X4b、清單加 FA0，終點列收案值指向 X4b |
| B2 `data_text` 含別欄資料卻整段填進追問欄 | FIX | §4.1 A 加 `answer_text`，B4 只填答覆段；FA9 (c) |
| B3 資料段未知時提議值仍以整句過閘 | FIX | §4.1 B1、B2：未知 ⇒ 本回合一律不併；FA9 (b) |
| B4 值閘呼叫點只點名 2 處，實有 6 處 | FIX | §3 G3、G6 列全 6 處與 4 處賦值點；B 收進同一 helper；FA9 (e) |
| B5 FA1 缺「順序對調」 | FIX | 規則檔廣度 FA1 加順序對調；FA2 加只講一半 |
| B6 brief 沒附業主原話 | FIX（流程） | r2 brief 直接貼原話 |
| D1 Q3 只涵蓋 M0 | FIX | Q3 擴及全部預期 0 的列 |
| D2 缺用量報告、獨佔 | FIX | §7 末兩段 |
| D3 三句原話沒承接 | FIX | 規則檔加 FA-R11、FA-R12 與 E 收案一句 |
| D4 FA5／FA6 類型 | FIX | 改標 |
| D5 G3 命中數 | FIX（隨 B4） | — |
| 待查 1 先前回合同一個數字 | FIX | B3：值閘只比資料段；FA9 (d) |
| 待查 2 security-reviewer | 不跑（r2 時判斷） | r2 審查改判應跑，見 r2 B2 |
| 待查 3 Dialogflow 只引前半 | FIX | §2.2 補全句與註解 |

**r2（第二位 fresh plan-verifier，2026-10-27）：REVISE**，阻擋 4、可後補 2、待查 1。已達兩次自動 REVISE，不再自動重送；r3 為新的審查輪次，先跑唯讀 security-reviewer，再由一位 fresh plan-verifier 做收尾審查。

| 發現 | 處置 | r3 改了什麼 |
|---|---|---|
| B1 只比資料段會放進「切斷數字」的值（「15000」切成「1500」） | FIX | §4.1 B1 加邊界檢查；B3 改為「現行值閘 ∩ 資料段值閘」；FA9 (h) |
| B2 值閘是對不可信模型輸出的驗證，應過安全審查 | FIX | r3 送 plan-verifier 前先跑唯讀 security-reviewer，發現與處置記在本節 |
| B3 FA1／FA3 沒定義「重問」場怎麼判 | FIX | §5 判法改四類；規則檔 FA1、FA3 通過條件同步 |
| B4 Q1 (B) 對候選集名稱欄在 6 處處理矛盾 | FIX | §4.1 B5 寫明欄位集合：候選集綁定欄 6 處都照 F12 名稱規則；FA9 (g) |
| D1 追問中改辦另一動作會被 B3 全擋 | FIX | §4.1「適用範圍」 |
| D2 X4b 措辭 | FIX | 改成「改動會碰到」 |
| 待查 比的是正規化值還是原值 | FIX | B3 (ii) 寫明比 (i) 的正規化結果 |

**r3 安全審查（唯讀 security-reviewer，2026-10-27）**：P1 1、P2 1、P3 7、P4 1、待查 4；無跨業者綁定問題。主會話對碼：S1 依據 `_await_write_intent`（`action=none` 與失敗皆回 `None`）與 `_write_draft_decide`（`if not other_action:` 後整句填入）成立；S9 依據 `_start_dialog_act_call` 註解成立。

| 發現 | 處置 | r3 改了什麼 |
|---|---|---|
| S1 P1 意圖沒結果的回合不算追問回合 ⇒ 退回整句填入 | FIX | §4.1 適用範圍改為回合開始依已知狀態判、只有意圖確認的另一動作排除；`None`／`action=none`／提議帶另一動作的處理；FA9 (j) |
| S2 P2 enum／category 的 B3 不起作用，Q1 說明不實 | FIX | B3 末句、B5、Q1 說明改寫；FA3 補 `repair_create` |
| S3 P3 邊界在哪個字串上算未寫 | FIX | B1：原句上算、空白算邊界、多次出現任一成立、只是塑形；FA9 (m) |
| S4 P3 存哪個值、(ii) 副作用未寫 | FIX | B3：存 (i) 輸出、(ii) 副作用同現行同值重併；FA9 (l) |
| S5 P3 兩段存在哪裡未限定 | FIX | B7；FA9 (n) |
| S6 P3 填模型字串、無長度上限 | FIX | B4：程式切原句原字、sanitize、長度拒收 |
| S7 P3 off 無測試、讀法未寫 | FIX | 開關段；FA8 加 off 測試 |
| S8 P3 3 個建構點只寫一處、缺鍵未定 | FIX | A.3；B1 缺鍵／null／非字串 ⇒ 未知；FA9 (k) |
| S9 P3 附追問欄位的同 repo 反證 | FIX | §4.3 引用；FA1 加輸入類別 |
| S10 P4 text 型資料段內切值 | FIX（照實描述） | B3 末句寫明是現行行為、本片不擴不修 |
| 待查 1 資料段未知時 `pick_id`／`target`／`record_rechoice` 照常 | 不改 | 限同身分候選編號內、無越權證據；收案 verifier 另查 |
| 待查 2 `_write_draft_catch_name`、`_name_lenient_pick_rewrite` 的關鍵字會不會帶「3q」 | 執行時查 | FA9 (e) 擴及單筆命中補名稱路徑；FA1 使用者層量 |
| 待查 3 不記 `user_value_dropped` 對仍有效卡狀態句的影響 | 執行時查 | security-executor 對碼後加單元測試，狀態句與改前同一回合比對；不同即停回報 |
| 待查 4 X9 F1 整句填入場的意圖是 none 還是逾時 | 部分查 | `run_r8`、`rep/run_r8` 的 `records.jsonl` 各 1 筆 `write_draft_program_first_wait_timeout`、0 筆 `write_intent_call_failed`；S1 的修法兩種都涵蓋 |

**r3 收尾審查（fresh plan-verifier，2026-10-27）：REVISE**，阻擋 2 條，審查員皆標 `Kind: wording-only`（P2）：C1「前兩片」應為選對紀錄片與 E（非 OV）；C2 FA0 是 10 種輸入、重複 1～5 次，不是 17 個案例。兩條已在 §0 與規則檔廣度改字。可後補 5 條：FA9 (e) 未含單筆命中補名稱、§0 M0 列無來源陳述、FA1 口語錯字簡稱併類與 FA3 無說法類別、X6 改前可用 after9、FA9 未列長度拒收與日誌——r4 全部改掉。待查 2 條：(1) 非追問回合有沒有道謝衍生值——主會話當場探針證實有（§1），屬 DSP-115 第 3 點錯筆、不得後補，範圍交業主，業主裁擴到所有寫入回合（§6 第 1 點）；(2) 空的 enum／category 欄會不會被衍生值——結構上不擋，寫進 B3 末句，由 FA1 `repair_create` 組量。

**r4（業主裁擴大範圍後重寫）**：§4.1 適用範圍改為所有寫入回合；資料段改為依原句順序的多段 `data_texts`（第一句道謝常夾在中間）；`answer_text` 只在追問回合；B5 只管追問回合；§1 加探針事件；§3 加 G7；§7 X5 改跑 E1～E4、E14 全部，X6 改前用 after9；清單加 FA1b 與 FA9 (o)～(q)。r4 為業主改範圍後的新輪次：先唯讀 security-reviewer 審 §4.1 的改動，再一位 fresh plan-verifier 收尾審查。

**r4 安全差異審查（唯讀 security-reviewer，2026-10-27）**：P2 2、P3 2、P4 3、待查 5；多段陣列未破壞「只縮不擴」，無綁錯物件路徑。主會話對碼：R4-1 依據 `_write_draft_card_still_valid_exit` 的 `lead = WF.CARD_UNCHANGED_TEXT if wd.user_value_dropped else WF.CARD_STILL_VALID_TEXT` 與 `write_forms.py` 的 `CARD_STILL_VALID_TEXT`「卡片還在，請按確認。」成立。

| 發現 | 處置 | 改了什麼 |
|---|---|---|
| R4-1 P2 資料段未知時狀態句叫客人按確認、送出舊值 | FIX | B2：狀態句改用回合內旗標「本回合有值沒套用」；FA9 (r) |
| R4-2 P2 卡後打字補充回合在範圍內卻沒驗收 | FIX | 清單加 FA1c（5 組 × ≥5）；FA9 (r) |
| R4-3 P3 卡後回合已填 enum／category 不受保護 | FIX（照實寫＋量） | B3 末句寫明缺口；FA1c `repair_create` 組加該類輸入、錯卡即停 |
| R4-4 P3 草稿被意圖以外路徑換掉時追問狀態歸屬未定 | FIX | 適用範圍：B4、B5、`answer_text` 只對回合開始那份草稿；FA9 (s) |
| R4-5 P4 空段、串接、多追問欄未定 | FIX | B1 空段略過、逐段比對 ⛔ 串接；B4 多欄不用 `answer_text`；FA9 (t) |
| R4-6 P4 保證以 A+ 三開關 on 為前提未寫 | FIX | 適用範圍末句、§8 回復 |
| R4-7 P4「提議先到」判準未寫 | FIX | B1：唯一來源為 `_await_write_intent` 驗過的物件 |
| 待查 1 輸出變長致截斷增加 | 量 | §7 X4 加 `write_intent_unparsed` 與重送標記數改前改後並列 |
| 待查 2 `_write_draft_catch_name` 以查詢關鍵字當名稱 | 量（同 r3 待查 2） | FA9 (e) |
| 待查 3 F12、選定後指令式題組未在量測內 | FIX | §7 加 X5b、清單加 FA4b（改前改後同日） |
| 待查 4 第一句「提議先到」頻率 | 量 | X4 的 FA1b 記錄列 `fill_data_text_unknown` 與 `write_proposal` 同場數 |
| 待查 5 `_write_proposal_merge` 不檢查 `triggered`（既有行為） | 不改 | 非本片引入；記收案報告已知限制 |

**r4 收尾審查（fresh plan-verifier，2026-10-27）：REVISE**，阻擋 1 條，審查員標 `Kind: substantive`（P2）：C1 `data_texts` 為空陣列時，B3「資料段已知時（含空陣列）」加上 enum／category 值閘不比對原話（`_write_draft_gate_value` 的 `if kind == "enum":` 分支只做 `WF.enum_code_for_label`），意圖給的 enum／category 標籤照樣能進草稿；清單 FA9 (q) 卻要求「不併任何新值」，兩邊矛盾；§4.3「最壞結果是重問」對這兩型也不成立。主會話對碼成立。收尾審查不再重啟循環、非 wording-only ⇒ 本片暫停，交業主裁 (a) 空陣列 ⇒ 一律不併（含 enum／category）或 (b) 保留 B3、FA9 (q) 只涵蓋比對原話的型別。可後補 4 條記 §9。業主 10-27 裁 (a)，並裁「修完直接交核可」；B3、§4.3、清單 FA1c、FA3、FA9 (q) 已照 (a) 改，**已修、未再審**。

