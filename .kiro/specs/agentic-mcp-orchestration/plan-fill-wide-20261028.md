# 「填欄擴及首句、卡後、多欄回合」片計畫（r2，2026-10-28 業主核可）

規則與驗收清單：`acceptance-fill-wide-20261028.md`（規則 FW-R1～FW-R14、清單 FW0～FW13、## 廣度、非目標）。原則 P1、P4、P5。上線最低範圍內（錯筆卡不得後補，DSP-115 第 3 點），和第 4 步切換正式機同時進行（FW-R10）。以下 `~/jgb-archive/arch-step3-20261018/` 簡寫為 `arch/`。

## 0. 先答三題、終點指標、斷路器

**廣度**（全域「驗收廣度」第 7 條）：
1. 每項幾組資料 × 幾種輸入 × 重複幾次：FW1 首句 5 組表單 × 每組 ≥11 輸入（11 類各 ≥1）× 1；FW2 卡後 5 × ≥7（7 類）× 1；FW3 多欄 5 × ≥7（7 類）× 1；FW0 X4 同批 5 組 221 場 × 1；FW4 X8 5 組 106 場 × 1；FW5 X9 3 組 × 10 種輸入（17 場，重複只算穩定性）；FW6 F3″ 1 組 × 40、F8 1 組 × 20；FW7 E 片 195 場 × 1；FW8 M0 29 題 56 場 × 1。
2. 輸入誰寫：FW1～FW3 由不讀程式的 fresh 代理依配額撰寫、標出資料與非資料部分、跑前凍結 sha256，⛔ 與上一片 X0、X8 輸入重複；FW0、FW4～FW8 為既有題組（fresh 代理或 verifier 所寫）；FW9 為實作方所寫，只證不退步。
3. 跟改前比：FW1～FW3、FW6 F3″ 在改前（現行常駐）與改後同輸入各跑一次；FW0、FW4、FW5、FW6 F8、FW7、FW8、FW9 的改前值已在現行受測物上量過（見下表來源），不重跑。

**終點指標**（目標文件＝目標正本 `architecture-target-20261018.md` §1「每片怎樣算完成」的全部量法，加 DSP-115 第 3 點的收案門檻「錯筆卡」）。受測物＝常駐 `aichatbot-rag-orchestrator`，`runtime.py` md5 `6dc04e030c886e5379e31f6afa9cd143`、`write_forms.py` md5 `41ffac4b7766c0aca5452f669465491a`（容器與工作樹相同，2026-10-28 查），HEAD `720f0bf7`＋未提交改動（`arch/fill2/baseline/wt-before-plan.txt`，`git diff -- rag-orchestrator` md5 `d510a5c5…`）。X4 after6、X8 on6 的 `header.json` 記的 md5 與此相同。「前兩片」＝計畫點名目標正本為目標文件的最近兩片：E 片（`plan-closing-handoff-e-20261026.md`）與填欄只填答覆片（`plan-fill-answer-only-20261027.md` §0）。

| 量法 | 門檻 | 現值（來源，皆量於現行受測物） | 本片預期 | 前兩片實際變化（來源） |
|---|---|---|---|---|
| M0 判分場解決數（harness 現在）W／K／A／全部 | 每列改後 ≥ 改前 | 18/20、19/20、12/12、49/52（`arch/fill/m0fa_score.json` 的 `harness\|現在`） | 每列 0（§8 Q4）。M0 的寫入場（W、W-D）首句與卡後回合都經過本片，資料段標錯會變成重問或拒收，有退步風險，由 FW8 量 | E（程式前判，`arch/e/report-e-close.md` 終點表）：W 20→20、K 18→20、A 12→12、全部 50→52；填欄片（`arch/fill/report-fill-close.md` 終點表）：W 14→18、K 20→19、A 12→12、全部 46→49 |
| M0（T4 現在）W／K／A／全部 | 每列改後 ≥ 改前 | 19/20、19/20、12/12、50/52（同檔 `T4\|現在`） | 每列 0（§8 Q4） | E：無 T4 列；填欄片：W 16→19、K 20→19、A 12→12、全部 48→50 |
| M0 盲判嚴格 A／K／W／W-D／全部 | 每列改後 ≥ 改前 | 12/12、14/20、10/10、10/10、46/52（`arch/fill/blind/result.txt` 的 `after`） | 每列 0（§8 Q4） | E（`arch/e/report-e-close.md`「M0 改後與盲判」節）：A 12→12、K 12→14、W 10→10、W-D 10→10、全部 44→46；填欄片：A 12→12、K 14→14、W 10→10、W-D 9→10、全部 45→46 |
| 鎖定缺陷「道謝後轉真人」（M0 場數） | 0 | 0（同上） | 0（維持；§8 Q4） | E：2 → 0（`arch/e/report-e-close.md`）；填欄片：0 → 0 |
| **錯筆卡：首句、卡後、多欄回合**（本片鎖定） | 0（FW-R3） | X4 7 筆（首句 FA1b 4、卡後 FA1c 3，含 FA1c-bill-02 覆寫已填欄；`arch/fill/x4-after6/judge.json`）；X8 1 筆（首句 FA1b-est-02；`arch/fill/x8-on6/judge.json`）；FW1～FW3 新輸入（X1 改前，2026-10-28 10:36～10:48 於現行受測物，凍結輸入 sha256 `444bd57d…`，`arch/fill2/x1-before/judge.txt`）：錯筆卡 FW1 1/55、FW2 2/46、FW3 5/40（合計 8/141）；卡住 FW1 19、FW2 7、FW3 7；欄位錯置 0；FW2 更正有套用 34/39、部分更正未套用 1 場（FW2-con-06，回話有點名） | X4 7 → 0～1、X8 1 → 0（殘留預期只剩「名稱緊貼英數道謝、AI 連道謝一起標成資料」，§3 G6，是否接受交業主 §8 Q2；首句意圖回 `action: "none"`＋空陣列時照現行收值的回合另報，§8 Q1）；FW1～FW3 新輸入另計改前改後 | E：無此列；填欄片：X4 同批 22 → 7（−15，其中單欄追問 15 → 0）、X9 17 場 11 → 0 |
| 錯筆卡：單欄追問回合（不退步） | 0 | X9 同批 0/17（`arch/fill/x4b6/judge.txt`）；X4 單欄追問 0 | 0（維持；§8 Q4） | E：無此列；填欄片 11/17 → 0/17（`arch/fill/report-fill-close.md`） |
| 卡住：首句、卡後（FW-R5） | 改後 ≤ 改前 | X4 FA1b 10、FA1c 3；X8 FA1b 2、FA1c 3（同上兩檔） | 0 或減少 | 填欄片 X4 全部 27 → 24 |
| 既有回歸題組 E2a 六組 | 每組 ≥ 改前 | R、D、C、T、RS 2/2，DS 1/2（`arch/fill/x6_6/`） | 0（§8 Q4） | E：DS −1（`arch/e/report-e-close.md`）；填欄片：0（`arch/fill/report-fill-close.md`） |
| 既有回歸題組 E 片（FW7）E1／E2／E3 原卡／E4 程式轉人／E14 | 每組 ≥ 改前 | 48/48、64/64、5/5、0/48、15/15（`arch/fill/x5_6/`；`arch/fill/report-fill-close.md` FA4 列） | 0（§8 Q4） | E：本片建立；填欄片：47→48、63→64、4→5、0→0、15→15 |
| 既有回歸題組 F12（FW6）F3″ (2)／F8 錯筆卡 | F3″ ≥ 改前；F8 0 | F3″ 37/40（X1 改前，2026-10-28 於現行受測物 runtime `6dc04e03…` 重跑，`arch/fill2/x5b/f3pp_score_before.txt`、檔首指令與版本 `arch/fill2/x5b/run_before.header`；上一片第 4 輪 35/40）；F8 錯筆卡 0（`arch/fill/x5b/f8_judge_after6.txt`） | 0（§8 Q4） | E：未量；填欄片：F3″ 34→35、F8 錯筆卡 1→0（`arch/fill/report-fill-close.md` FA4b 列） |
| 單元測試 | 全過 | 9 failed、6842 passed（`arch/fill/unit-after-fix6.txt`）——**未達字面** | 0（9 筆不變；新測試全過；§8 Q4） | E：0；填欄片：0 |
| `make audit` | PASS | PASS（`arch/fill/invariants-after-rebuild7.txt`） | 0（§8 Q4） | E：PASS；填欄片：PASS |

**斷路器**：前兩片實際變化 E M0 +2、填欄片 M0 +3／錯筆卡 −15，不全為 0 ⇒ **不觸發**。

## 1. 目標

客人在首句開口、確認卡出現後打字、一次回答程式追問的多個欄位時，卡上只出現他講的資料；道謝、寒暄、應答字不會被填進任何欄位，也不會被拆成數字填進別欄（FW-R2、FW-R3）。同時不能讓客人講過的資料被丟掉、要再講一次（FW-R5），上一片修好的單欄追問回合不退步（FW-R6）。

實際事件（現行受測物；X4＝`arch/fill/x4-after6/`，每場回話與卡面在 `records.jsonl`，判定在 `judge.json`）：

| 場 | 回合 | 卡上的錯值 | 值從哪來 |
|---|---|---|---|
| FA1b-rep-06 | 首句（`write_draft_program_first_wait_timeout`） | 問題描述「燈不亮，已經壞了3天3q」 | 意圖等待逾時，值來自主模型提議 |
| FA1b-bill-09 | 首句（同上逾時） | 說明「3Q」（客人「開脹單」錯字，被讀成報修） | 同上 |
| FA1b-est-05 | 首句 | 物件名稱「松仁晴空3Q」 | 寫入意圖 |
| FA1b-ext-06 | 首句 | 「您先前說 3 元」（`said_amount` 3 來自「3q」） | 寫入意圖 |
| FA1c-rep-04 | 卡後 | 問題描述「冷氣只能吹到28度3q」 | 寫入意圖 |
| FA1c-rep-06 | 卡後 | 問題描述「遙控器也沒反應，謝啦」 | 寫入意圖 |
| FA1c-bill-02 | 卡後 | 帳單項目「清潔費」被換成「退租清潔」（客人說「說明幫我加：退租清潔 thx」） | 寫入意圖選錯欄；非道謝衍生 |
| X8 FA1b-est-02 | 首句 | 物件名稱「悅揚閣多謝」 | 寫入意圖 |

8 筆都算錯筆卡（X4 7、X8 1）。FA1c-bill-02 不是道謝衍生，而是已填的帳單項目被客人要加進說明的資料覆寫成錯值；改前（`arch/fill/x2-before/`）這一場是「填入」，上一片才變錯筆卡（`arch/fill/x4-after6/judge.txt` 翻轉清單「FA1c-bill-02 填入 錯筆卡」）。它與上一片第 13 點第 2 題（說明欄**重複**帳單項目、「改前就有，改後沒有變多」）不同，算不算錯筆卡交業主 §8 Q3；裁定前照原判分算錯筆卡（FW-R2）。

## 2. 目標形態（業界原頁渲染檔；逐字）

原頁沿用上一片 2026-10-27 以 web-drive（jgbui）渲染的 `arch/fill/sources/*.txt`（每檔首兩行是網址與最終網址；`_index.json` 列字數），與 2026-10-18 渲染的 Google 對話設計 `~/jgb-archive/devflow-20261018/sources-repair/gcd-help.txt`（首行網址 `https://developers.google.com/assistant/conversation-design/confirmations`）。本節引句皆以 `python3` 在原檔 `find()` 命中後逐字摘錄。

### 2.1 首句講多件事：每一件各填各的欄，值照客人原話

- Rasa CALM 指令產生器（`rasa-calm-command-generator.txt`，`https://rasa.com/docs/reference/config/components/llm-command-generators/`）提示詞：「**Slot extraction:** For every slot value the user mentions (name, amount, type, date, etc.), output exactly one `set slot slot_name value` command. Do not skip any.」——首句裡講到的每一個值都要抽，不是只抽一個。
- 同檔：「Extract text slot values exactly as provided by the user. Avoid assumptions, format changes, or partial extractions.」——值照原話。
- Microsoft Copilot Studio（`copilot-slot-filling.txt`，`https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-entities-slot-filling`）：「You can also use proactive slot filling, which allows the user to specify multiple pieces of information that map to different entities, at once. The agent understands what information belongs to which entity. In cases where it's unsure of the intended mapping, it prompts the user to be more specific by providing choices.」——一句多欄可以；不確定就問，不硬填。這同時是多欄回合（程式一次追問多欄、客人一句答多欄）的目標形態。

### 2.2 確認之後客人會更正；更正要能改掉已填的值

- Google 對話設計（`gcd-help.txt`）：「Expect users to make corrections, after explicit and implicit confirmations, when there’s been a misunderstanding or misinterpretation of their input. Give users the opportunity to make changes, even when there weren’t mistakes.」「Allow one-step corrections.」
- Rasa CALM 提示詞：「`set slot slot_name slot_value`: Set a slot for the active flow. For example, `set slot transfer_money_recipient Freddy`. Can be used to correct and change previously set values.」
- ⇒ 卡後打字的回合不能比照上一片「追問回合不覆寫已填欄」（B5）；更正要一步就改得掉（FW2「更正有套用的場數改後 ≥ 改前」）。

### 2.3 AI 抽值、系統驗；驗不過就再問

- Rasa CALM 提示詞：「Do not validate slot values. If a user provides a value that seems incorrect or informal (e.g., a name instead of an ID, or a relative date), extract it anyway. The system will handle validation errors later.」——理解（抽值）歸模型，驗證歸系統。
- Rasa forms（`rasa-forms.txt`）驗證範例註解：「validation failed, set this slot to None so that the user will be asked for the slot again」——驗不過的是**那一個值**，該欄清空、再問該欄；不是整句作廢。

### 2.4 道謝、寒暄不是資料

- 道謝、寒暄字被填進欄位或衍生成別欄值：**查無業界專節**（上一片 §2.3、§2.4 同此結論；Rasa forms 的 `ignored_intents` 是整句是閒聊時不填，不涵蓋「資料＋道謝」同句）。第一原理：欄位值是客人給的資料；同句的道謝不是任何欄位的值（r9「只填答覆部分」）。

### 2.5 本線的分工（DSP-091）

「哪部分是資料」是理解，歸 AI；「這個值收不收、要不要再問」是寫入流程，歸程式（2.3 的分法同此）。⛔ 程式用道謝詞表判斷（FW-R8）。

## 3. 差距（對碼；可重跑）

讀碼指令在 repo 根執行。

| # | 目標形態 | 現況 | 查證 |
|---|---|---|---|
| G1 | 2.1～2.3 三種回合有「AI 標資料段、系統驗值」 | 上一片的做法只在單欄追問回合啟用：`_fill_begin_intent_call` 在 `len(wd.asked) != 1`、或回合開始沒有草稿時回 `{}`、不設 `fill_active`；三種回合的系統句、schema、值閘與開關 off 逐字相同 | `grep -n "def _fill_begin_intent_call" -A 24 rag-orchestrator/services/agent/runtime.py` |
| G2 | 2.3 系統驗值時分得出資料與道謝 | 三種回合的值只過現行值閘 (i)：值須是客人原話（`wd.user_texts`）子字串、數字 token 須出現在原話——「燈不亮，已經壞了3天3q」是原話子字串、「3q」裡的 `3` 是原話數字，都會過。`_write_draft_turn_gate` 在 `not wd.fill_active` 時直接回 (i) 的結果 | `grep -n "if not wd.fill_active:" -B 3 -A 2 rag-orchestrator/services/agent/runtime.py`（命中 `_write_draft_turn_gate` 內一處） |
| G3 | FW-R4 能否沿用上一片的「AI 標資料段」 | **可以沿用，而且光加規則句就修掉大半**。探針（2026-10-28，`arch/fill2/probe/probe_intent.py`、`probe_intent2.py`，在常駐容器內以 `WF.write_intent_system_prompt(enum_labels=True, data_text=True)` 直打寫入意圖，只呼叫模型、不碰 JGB；輸出 `out1.jsonl` 16 行、`out2.jsonl` 24 行）：X4 那 7 句加上資料段規則後，AI 自己回的欄位值大多已不含道謝——卡後「冷氣只能吹到28度3q」description 3/3＝「冷氣只能吹到28度」、「遙控器也沒反應，謝啦」3/3＝「遙控器也沒反應」、「說明幫我加：退租清潔 thx」3/3 進 `sub_title`（不再換掉帳單項目）、「基隆溫馨一人宅套房2027年1月那期延後2天3q」3/3 只回 `days` 2、沒有 `said_amount`；首句「幫我報修 饒河夜市好房…3天3q」3/3 description 不含 3q。反向風險：首句「浴室的燈不亮，已經壞了3天3q，物件是學生獨立套房可租補」2/2 回 `action: "none"`、`fields: []`（`out1.jsonl`；沒有對照 off 的探針），首句的值可能因此改由主模型提議或程式追問取得，由 FW1、FW0 的重問與卡住量。探針是簡化對話（不含真實草稿狀態），只算中間證據，成效以 FW0～FW4 為準 | `python3 -c "import json;[print(json.loads(l)['msg'],json.loads(l)['k']) for l in open('$HOME/jgb-archive/arch-step3-20261018/fill2/probe/out2.jsonl')]"` |
| G4 | FW-R4、FW-R5 哪幾條不能沿用 | **上一片 fail-closed 的那幾條不能沿用**。上一片第 2 輪（嚴格資料段套到所有寫入回合）X8：卡住 on 16、off 8（`arch/fill/x8_compare.md`），主形狀兩種：①卡後更正被 (iii) 擋下（「租金改成17000感謝您」「押金改 20000 ty」「繳費期限改到 2026/12/20，辛苦你了」「改延後5天多謝」）；②多欄回合前句已講的值被擋。業主第 10 點因此收窄。探針：卡後「租金改成17000感謝您」`fields` 3/3 都是 rent=17000（正確），但 `data_texts` 1/3 回 `[]`（`out2.jsonl`）——上一片 C1 (a)「空陣列一律不併」照搬，這句更正就會被擋；卡後「繳費期限改到 2026/12/20，辛苦你了」2/2 意圖 `fields`、`data_texts` 都空（`out1.jsonl`），值只能來自主模型提議，空陣列一律擋就會卡住 | `grep -n "租金改成17000感謝您" /Users/chenqinghuang/jgb-archive/arch-step3-20261018/fill/x8_compare.md` |
| G5 | 2.3 意圖等待逾時時仍要驗 | 首句程式優先只等 `WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S`（1.0 秒），逾時 ⇒ 記 `write_draft_program_first_wait_timeout`、意圖不取用；主模型的提議（`_write_proposal_handle` → `_write_proposal_merge`）比意圖合併先到，此時資料段還沒讀到。X4 的 FA1b-rep-06、FA1b-bill-09 都是這條路 | `grep -n "WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S = \|V_PROGRAM_FIRST_WAIT_TIMEOUT)" rag-orchestrator/services/agent/runtime.py`；`grep -n "if not await self._write_proposal_merge" rag-orchestrator/services/agent/runtime.py` |
| G6 | 2.4 | **程式端修不到的殘留**：首句「我要新增一個物件叫松仁晴空3Q…」「新增物件 松仁晴空3Q，…」各 2～3 次，AI 都把「松仁晴空3Q」同時放進 title 與 `data_texts`（`out1.jsonl`、`out2.jsonl`）；現行系統句已接 `DATA_TEXTS_NAME_NOTE`。資料段裡就有「3Q」⇒ (iii) 擋不到；要擋就得列詞表（FW-R8 ⛔）。與上一片第 13 點第 1 題（「車位費ty」）同類 | `grep -n "^DATA_TEXTS_NAME_NOTE" -A 2 rag-orchestrator/services/agent/write_forms.py` |
| G7 | — | 動作選錯：「幫我開脹單，…管裡費 1000 元，3Q」探針 2/3 被讀成 `repair_create`（`out2.jsonl`）；這是 FA1b-bill-09 的起點，不是道謝衍生（非目標） | 同 G3 指令 |
| G8 | — | 卡後回話：三種回合 `fill_active` 為 `False` ⇒ `_fill_value_not_applied` 恆 `False`；本片若在卡後拒收某值卻不設旗標，狀態句會照現行（讀到同值 ⇒ `CARD_READ_SAME_LEAD`；沒讀到值 ⇒ `CARD_NO_CHANGE_TEXT`），客人要改的值沒套用卻被叫去按確認 | `grep -n "def _fill_value_not_applied" -A 5 rag-orchestrator/services/agent/runtime.py`；`grep -n "CARD_UNCHANGED_TEXT\b" rag-orchestrator/services/agent/runtime.py` |

正對照：G2 的 grep 若 0 處＝指令壞了（`_write_draft_turn_gate` 必然存在）；G5 第二條命中 1 處即正常。

**FW-R4 結論**：沿用「AI 標資料段（A）」與「每個值再比一次資料段（iii）」；換掉「資料段未知或空陣列就整回合不併」（fail-closed）、「追問回合不覆寫已填欄」（B5）、「只填答覆段」（B4、`answer_text`）三條——前者是卡住變多的主因（G4），後兩條只對單欄追問有意義且與 2.2 相反。另補一條上一片沒有的：意圖逾時時等意圖結果再驗主模型提議（G5）。

## 4. 路徑

每個範圍項目標出它服務的目標正本原則（P 號，`architecture-target-20261018.md` §2.8 原則表）與對應的差距或實際事件（§1 表、§3 G 號）。

### 4.1 適用範圍（P1；§1 三種回合 8 筆事件、G1）

「寬回合」＝本回合送出寫入意圖呼叫（現行 `_start_write_intent_call` 條件）、非凍結，且屬下列之一（回合開始、送出意圖呼叫之前依程式已知狀態判一次，存回合內狀態）：
- (a) 首句：`wd.had_draft` 為 `False`；
- (b) 卡後：`wd.had_draft` 為 `True`、`wd.asked` 空，且下列之一成立：草稿綁定的那張卡還活著（`_write_draft_bound_card` 找得到、未兌現〔無 `receipt`〕、未作廢〔`invalidated` 非 `True`〕），或寫入候選清單還在等使用者選（候選回合）；兩者皆無（例：插問知識題後 `asked` 被清空、還沒出過卡也沒列候選）⇒ 不算寬回合，照現行（§11 r1c）；
- (c) 多欄：`wd.had_draft` 為 `True`、`len(wd.asked) >= 2`。

單欄追問回合（`len(wd.asked) == 1`）照上一片（`fill_active`）不變；文件回合、`pick:` 按鈕回合、凍結回合照現行。寬回合與單欄追問回合互斥（同一回合只會是一種）。回合中草稿被換成另一動作時，寬回合的做法照樣套在新草稿上（寬回合本來就不依「目前草稿＝回合開始那份」）。

### 4.2 A. AI 標資料段（沿用上一片；P4；G1、G3，§1 X4 7 筆與 X8 1 筆中來自寫入意圖的 6 筆）

寬回合的寫入意圖呼叫一律帶 `data_text=True`、不帶 `asked_labels`：系統句接 `DATA_TEXTS_RULE`＋`DATA_TEXTS_NAME_NOTE`（候選回合再接 `DATA_TEXTS_PICK_NOTE`），`WRITE_INTENT_NONE_RULE` 後接 `WRITE_INTENT_PARTIAL_NOTE`；schema 根層加必填 `data_texts`；不加 `answer_text`。三個建構點（`write_intent_system_prompt(` 的 3 處呼叫）一律經同一個參數入口（現行 `_fill_begin_intent_call` 擴充，⛔ 各點各寫）。⛔ 改任何規則句字面（字面會改變抽取率）。資料段讀取沿用 `_fill_read_data`（逐段在最新一句、起訖不切斷數字或英數；前面回合抄來的段略過記 `fill_segment_not_in_message`）。

### 4.3 B. 程式驗值（換掉 fail-closed）

全部收在現行 `_write_draft_turn_gate`（6 個值閘呼叫點已一律經它，見上一片 `plan-fill-answer-only-20261027.md` §3 G6），寬回合依序：
1. **(i) 現行值閘**照舊比 `wd.user_texts`；不過 ⇒ 照現行拒收。（P1；不變項，FW-R6）
2. **(ii) 同值重述**：(i) 結果等於草稿該欄現值 ⇒ 照現行同值重併。（P1；不變項）
3. **資料段未知 ⇒ 照現行**（P1；G4，上一片 X8 卡住 8 → 16）（只過 (i)），記新標記 `fill_wide_data_unknown`（固定字串）。「未知」＝意圖呼叫逾時、例外、無法解析、ambiguous、值域外、鍵缺、`null`、型別不對、或某段出現在最新一句卻每處都切斷數字或英數（`_fill_read_data` 不存）。理由：上一片 fail-closed 在這三種回合讓卡住翻倍（G4）、業主第 10 點收窄；本片換成「讀不到資料段就退回現行」，最壞結果＝與現行相同。
4. **主模型提議比意圖先到（G5）⇒ 先等意圖結果再驗**（P4；G5，§1 FA1b-rep-06、FA1b-bill-09）：提議要過閘時，若意圖呼叫尚未取用，先以 `asyncio.wait`（⛔ 取消）等它完成，上限＝`min(WRITE_INTENT_WAIT_MAX_S, 剩餘期限 − WRITE_DRAFT_PROGRAM_MIN_REMAINING_S)`（與 `_await_write_intent` 同一條上限），完成就由**同一個結果物件**讀資料段（⛔ 另發呼叫、⛔ 直接解析 task 原始回應以外的來源）再過 (iii)；仍未完成 ⇒ 資料段未知（第 3 點）。意圖的合併照現行時點（`_write_draft_decide`），本點只讀資料段。實作約束（security-reviewer F2）：
   - 寬回合用自己的旗標；⛔ 設或讀單欄追問的 `fill_proposal_first`（它一設，`_fill_read_data`、`_fill_data_unknown` 就一律不用資料段，第 4 點會失效）。
   - 每回合只等一次（放在 `_write_proposal_merge` 進逐值迴圈之前），結果鎖住，⛔ 逐值重等。
   - 判讀意圖結果抽成一支**無副作用**、與 `_await_write_intent` 共用的函式（同一檢查順序：`call.settled`／`label_only` → `task.cancelled()` → `task.exception()` → `_RetriedIntentResponse.failed` → `parse_write_intent_content` → `WriteIntent.model_validate`（接 `ValidationError`）→ `_fill_intent_in_domain`），或把解析結果暫存在本回合 accumulator、`_await_write_intent` 沿用；⛔ 在本點 append violation、寫 `modifies_submitted`／`intent_pick_id`／`intent_parsed`／`intent_target`／`record_rechoice`、或設 `intent_consumed`（重複標記會讓 FW0 的 `write_intent_call_failed` 等計數失真；設 `intent_consumed` 會讓 `_write_draft_decide` 不合併意圖）。
   - 上限寫 `max(0.0, min(WRITE_INTENT_WAIT_MAX_S, 剩餘期限 − WRITE_DRAFT_PROGRAM_MIN_REMAINING_S))`（與 `_await_write_intent` 同式）。
   - 只讀本回合 `acc.write_intent_call`，⛔ 讀 `self._write_intent_calls` registry。
5. **空陣列**（P5；G4 探針「租金改成17000感謝您」1/3、「繳費期限改到 2026/12/20，辛苦你了」2/2）（`data_texts` 為 `[]`，或全部段被略過）⇒ 當資料段未知（第 3 點，照現行收值），記 `fill_wide_data_unknown`。**這條偏離上一片 C1 (a)「空陣列一律不併」，交業主 §8 Q1**（本計畫照建議案 (c) 寫；業主選 (a) 或 (b) 時改本點與 FW11 (e)(f)）。理由：現行 7 筆錯筆卡的資料段都非空（G3 探針），空陣列擋不到它們；空陣列一律擋反而會擋下 G4 那兩種正確更正。純道謝回合另有保護：追問回合（含多欄）由 E 片標籤（`_dialog_act_not_field_answer`）不併；卡後與首句沒有這層保護，由 FW2「卡後純道謝或寒暄」類量。
6. **(iii) 資料段非空 ⇒ 逐值比**（P4；G2，§1 FA1b-est-05、FA1b-ext-06、FA1c-rep-04、FA1c-rep-06、X8 FA1b-est-02）：同一值閘只拿 `data_texts` 逐段比（⛔ 串接）；不過 ⇒ **只拒收這一個值**（其餘值照收），記 `fill_value_outside_data`。enum／category 的值閘不比原話，(iii) 不起作用（同上一片）。
7. 不套 B4（只填答覆段）、B5（不覆寫已填欄）、B6（追問欄重問）（P5；§2.2、G4 卡後更正被擋）：首句缺的欄照現行由程式追問；卡後更正照現行覆寫（2.2）；多欄回合沒填到的欄照現行缺欄追問。
8. **卡後回話（P2；G8，FW-R7）**：寬回合 (b) 有值被第 6 點拒收 ⇒ 設「本回合有值沒套用」旗標，綁定卡仍有效時狀態句用 `CARD_UNCHANGED_TEXT`（「這次的修改沒有套用…」），⛔ `CARD_STILL_VALID_TEXT`、⛔ `CARD_READ_SAME_LEAD`。**部分套用、卡重出**（同句另有值收下，走 `CARD_DIFFERS_TEXT` 或重出卡分支；security-reviewer F3：現行 `_fill_value_not_applied(` 只在 `_write_draft_card_still_valid_exit` 與 `_write_reply_state` 的卡未變分支被讀）⇒ 回話加一句程式固定句，點名沒套用的欄位**標籤**（⛔ 帶值），讓客人知道那一欄還是舊值。資料段未知（第 3、5 點）不設（值照現行併）。
9. 候選集綁定欄：沿用 `_fill_bound_field_exempt`（只過 (i)），條件不變。（P5；不變項，A-2a／F12 已選定的紀錄不被 (iii) 擋）
10. 資料段只活在本回合（同上一片 B7；P3，給模型的資料與給人看的、存下來的分開；security-reviewer 第 4 題：新欄位加 `field(repr=False)`、新判讀路徑接住 `ValidationError` 等例外且 ⛔ 記 `str(exc)`）：⛔ 進 `agent_state`、草稿、trace、決策快照、日誌；新標記固定字串、⛔ 帶值。

### 4.4 開關（P1；回復路徑，§8 回復）

`AGENT_FILL_DATA_TEXT_WIDE`，照 `write_draft_enabled_from_env` 樣式讀（on／off、未設＝on、其他值 `ValueError`、啟動失敗）。只在 `AGENT_FILL_DATA_TEXT` 也 on 時生效；off ⇒ 三種回合與現行逐字相同（FW11 (a)）。程式內直接讀屬性（比照 `_fill_data_text_on`，⛔ 預設 off 的 `getattr`）。

**開關要傳得進常駐容器**（security-reviewer F1，主會話已重查：`grep -n "AGENT_FILL_DATA_TEXT" docker-compose.prod.yml docker-compose.bedrock-local.yml ~/jgb-archive/arch-step3-20261018/overall/compose-writelog.yml` 0 處；正對照同指令以 `AGENT_WRITE_DRAFT` 命中 `docker-compose.prod.yml`）：`docker-compose.prod.yml` 的 `rag-orchestrator.environment` 只傳明列的鍵、沒有 `env_file`，未宣告的開關在 `.env` 設 off 會被靜默忽略、程式當 on。本片在 `docker-compose.prod.yml` 宣告 `AGENT_FILL_DATA_TEXT_WIDE: ${AGENT_FILL_DATA_TEXT_WIDE:-}`，並補宣告既有的 `AGENT_FILL_DATA_TEXT: ${AGENT_FILL_DATA_TEXT:-}`（上一片缺口，同一行為；空＝on，與現行相同）。A+ 前提：寬回合的保護以 `AGENT_WRITE_PROPOSAL` 等 A+ 三開關 on 為前提（`_write_draft_merge_model_confirm` 舊出卡路徑當回合的卡不經 (iii)，同上一片）。

### 4.5 單元測試（FW11，新檔 `rag-orchestrator/tests/unit/agent/test_fill_wide_req.py`）

(a) `AGENT_FILL_DATA_TEXT_WIDE=off`、或 `AGENT_FILL_DATA_TEXT=off` ⇒ 三種回合的系統句、schema（3 個建構點）、值閘、狀態句與現行逐字相同；開關值不合 ⇒ 啟動失敗。(b) 單欄追問回合與現行逐字相同（上一片 `test_fill_data_text_req.py` 全過）。(c) 首句「我要新增一個物件叫和平小屋 3q，在台北市…」、資料段兩段 ⇒ 名稱不含「3q」或由程式追問，其餘欄照填。(d) 卡後「租金改成17000感謝您」、資料段 `["17000"]` 或 `["租金改成17000"]` ⇒ rent 改成 17000。(e) 卡後同句、資料段 `[]`、`fields` 有 rent ⇒ 當未知、rent 改成 17000、記 `fill_wide_data_unknown`。(f) 卡後「繳費期限改到 2026/12/20，辛苦你了」、資料段 `[]`、`fields` 空、主模型提議 `date_expire` ⇒ 當未知、照現行併。(g) 多欄「台北市大安區復興南路100號 住宅 3q」⇒ 各欄照填、無值含「3q」。(h) 一句兩值、一個在資料段內一個不在 ⇒ 只拒收那一個。(i) 意圖逾時、主模型提議 description 含「3q」、意圖之後完成且資料段不含「3q」⇒ 提議值被拒收；意圖到上限仍未完成 ⇒ 照現行併、記 `fill_wide_data_unknown`。(j) 意圖例外、無法解析、ambiguous、值域外、鍵缺、`null`、型別不對 ⇒ 各一條，皆照現行併。(k) 卡後更正被 (iii) 拒收 ⇒ 回話 ⛔ 是「卡片還在，請按確認。」。(l) 候選綁定欄只過 (i)。(m) 資料段字串不出現在 `agent_state`、草稿、trace、決策快照、日誌（caplog）與 violation 字串，`repr` 回合狀態也不出現。(n) 回合中草稿換成另一動作 ⇒ 寬回合做法照樣套用、不觸發單欄追問的 B4／B5。(o) 提議先到、等意圖：`write_intent_call_failed` 等標記每回合各只一次；意圖照常由 `_write_draft_decide` 合併；剩餘期限已不足時上限為 0、不丟例外；意圖 task 例外或重送失敗（`failed`）⇒ 資料段未知。(p) 卡後「租金改成17000、押金改 20000 ty」、資料段只含租金段 ⇒ 租金改、卡重出，回話含點名「押金」的固定句、⛔ 含值。

### 4.6 改動檔（預估）

- `rag-orchestrator/services/agent/write_forms.py`：開關常數與讀取、`fill_wide_data_unknown` 標記常數；規則句與 schema 函式**不改**（沿用 `data_text=True`、`asked_labels=None`）。
- `rag-orchestrator/services/agent/runtime.py`：`_fill_begin_intent_call` 擴充寬回合判定與參數；`_WriteDraftTurn` 加寬回合旗標；`_write_draft_turn_gate` 寬回合分支（4.3 第 3～8 點）；提議先到時等意圖讀資料段（4.3 第 4 點）；卡後狀態句旗標（4.3 第 8 點）；開關讀取。
- 新測試檔（4.5）。
- `docker-compose.prod.yml`：`rag-orchestrator.environment` 宣告 `AGENT_FILL_DATA_TEXT_WIDE`、`AGENT_FILL_DATA_TEXT`（4.4）。
- 文件：`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`、目標正本 §3 P1 列與 §4、HANDOFF、`.claude/DECISIONS.md` 新 DSP、`.claude/MAP.md`。⛔ 另一個視窗的 4 份檔。

### 4.7 偏離目標形態的取捨

| 偏離 | 理由 |
|---|---|
| 資料段讀不到時照現行收值，不照 Rasa forms「驗不過就再問」 | 「讀不到資料段」不是「值驗不過」，是驗證工具本身沒結果；上一片照 fail-closed 做，三種回合卡住 8 → 16（G4），業主第 10 點收窄。代價：意圖逾時且等不到、或 AI 輸出壞掉的回合，道謝仍可能上卡（與現行相同），由 FW0～FW4 的 `fill_wide_data_unknown` 回合數與錯筆卡一起報 |
| 空陣列時照現行收值（偏離 C1 (a)） | 2.2 更正要一步就改得掉；G4 兩種正確更正都出現空陣列。代價：卡後或首句的純道謝回合，主模型若把道謝提議成欄位值會照現行上卡；X4 現行 7 筆錯筆卡沒有這一種。交業主 §8 Q1 |
| 名稱緊貼英數道謝、AI 連道謝一起標成資料時不擋 | 要擋就得列詞表（DSP-091 ⛔）；卡上看得到，客人可按「我要修改」，按確認前不會寫入。交業主 §8 Q2 |
| 首句意圖呼叫多輸出 `data_texts`，可能更常超過程式優先的 1.0 秒等待 | 不加長等待（W1c §9.11-3：無草稿回合多是知識題，加長會拖慢每個知識回合）；超過時改走第 4 點「提議先到先等意圖」。由 FW0、FW1 的 `write_draft_program_first_wait_timeout` 回合數改前改後並列報 |
| 提議先到時多等意圖（最多到 `WRITE_INTENT_WAIT_MAX_S`） | 2.3 系統驗值要有驗證依據；意圖呼叫回合開始就送，主模型出提議時多半已完成，額外等待多為 0。代價：意圖慢的回合延遲變長，由 FW0、FW1 的回合時間改前改後並列報 |

## 5. 驗收判法

FW1～FW3 每場由程式依撰寫者標註判，沿用 `arch/fill/drive/judge_fill.py` 的四類，改兩處：
1. 「已填欄被換值」依 FW-R2：新值含非資料字或由非資料字衍生 ⇒ **錯筆卡**；新值是客人那句裡標為資料的字、覆寫掉已填欄的正確值（FA1c-bill-02 型）⇒ 業主 §8 Q3 裁定前照原判分算**錯筆卡**；新值是客人資料、重複填進原本空著的欄 ⇒ **欄位錯置**（照實報、改前改後並列、記後補）。
2. 卡後場另判「更正有套用」：撰寫者列了新值、卡上換成新值 ⇒ 計數（FW2）。
判不出（標註、卡面與追問句都對不上）的場交 fresh 盲判代理（同上一片 §5）。FW0、FW4 用同一支改過的判分程式**重判改前**（`x4-after6`、`x8-on6` 的 `records.jsonl` 不重跑），改前改後同一把尺。

## 6. 業主裁示

2026-10-28，對話：業主問「建議是 ?」，主會話建議另開本片（原文見規則檔一節）；業主回「同意」。

2026-10-28 核可（AskUserQuestion 選項原文）：Q1「當讀不到、照現行收值 (Recommended)」⇒ §4.3 第 5 點照 (c)；Q2「列已知偏離 (Recommended)」⇒ 名稱緊貼英數道謝列已知偏離（FW-R3 例外）；Q3「算錯筆卡，本片要修 (Recommended)」⇒ FA1c-bill-02 型算錯筆卡（FW-R2）；Q4、Q5 與核可「同意，核可計畫 r2 (Recommended)」⇒ 防退步各列預期 0、以「改後 ≥ 改前」收案；FW3、F3″ 現值在 X1（核可後、改程式前）量。規則與清單凍結 sha256 `7a25829b…`（`arch/fill2/acceptance-frozen.sha256`）。

## 7. 執行與測試選擇（全域「測試選擇」）

每回合時間與費用依上一片實測：X4 221 場 634 回合 15.5 分（約 1.47 秒／回合，`arch/fill/x4-after6/records.jsonl` 起訖）；Bedrock 12,423 回合 US$10.4706（約 US$0.00084／回合，`arch/fill/report-fill-close.md` 用量節）。

| 執行 | 回答的決定 | 會改變下一步的結果 | 規模與理由 | 跑前成本 |
|---|---|---|---|---|
| X0 寫輸入（fresh 代理） | FW1～FW3 輸入凍結 | 配額不滿或與舊輸入重複 ⇒ 退回補寫 | 1 位；5 表單 × (11＋7＋7)＝125 句起（首句 55、卡後 35、多欄 35） | 上一片 X0 126,906 token、X8 撰寫 117,354 token；估 12～15 萬 |
| X1 FW1～FW3、F3″ 改前（核可後、改程式前；量測時點見 §8 Q5） | 三種回合現值；FW-R5 卡住基準；F3″ 現值（上一片第 5、6 輪未重跑） | FW1～FW3 改前錯筆卡 0 ⇒ 輸入沒打到缺陷，退回 X0 | 125 場 × 約 3.5 回合≈438 回合＋F3″ 約 120 回合 | 約 558 回合 × 1.47 秒≈14 分、約 US$0.47 |
| X2 單元測試、audit、canon-accept | 能否進入使用者層量測 | 新失敗 ⇒ 修到全過才跑 X3 | 全套（便宜且決定性） | 約 3 分（`arch/fill/unit-after-fix6.txt`） |
| X3 FW1～FW3 改後 | 錯筆卡是否 0；卡住是否沒增加；卡後更正是否照套用 | 錯筆卡 ≥1 且不屬 §8 Q2 已接受類型 ⇒ 停、查根因；卡住增加的場帶本片標記 ≥1 ⇒ 停 | 同 X1 輸入（實際凍結 141 場；X0 撰寫者超出 125 句下限，`arch/fill2/inputs/inputs.json`） | 約 10.7 分、約 US$0.37 |
| X4 FW0 X4 同批 221 場改後 | 7 筆錯筆卡是否修好（終點表收案值） | 同 X3 | 全 221 場（終點量測：§0 終點表「錯筆卡：首句、卡後、多欄回合」「錯筆卡：單欄追問回合」兩列的收案重量，「測試選擇」第 2 條第一種時機） | 15.5 分、約 US$0.53 |
| X5 FW4 X8 106 場改後 | 新說法上錯筆卡與卡住 | 同 X3 | 全 106 場（判不出影響範圍，「測試選擇」第 2 條第二種時機：改的是首句、卡後、多欄回合的值閘，鋪陳回合也經過；同一句鋪陳在 15 個場景中有 3 個跑出單欄或多欄兩種追問集合，改後受測回合走哪條路無法由改前紀錄判定；改前紀錄中單欄追問 65 場已有 16 場的受測回合本身是寬回合，分類見 `~/.claude/governance/test-selection-dedupe-20261028/evidence/classify-out.txt`） | 7.6 分（`arch/fill/x8-on6.log`）、約 US$0.27 |
| X6 FW5 X9 17 場、FW6 F3″／F8、FW7 E 片、FW9 E2a 改後 | 單欄追問與其他類別是否退步 | 任一 < 改前 ⇒ 停、查（DS 依前例補跑 1 次） | 全部場都有首句或卡後回合（改動碰到）；改前值見清單 | X9 1.1 分＋F3″ 約 3 分＋F8 約 2 分＋E 571 回合約 14 分＋E2a 約 1 分 ⇒ 約 21 分、約 US$0.70 |
| X7 FW8 M0 改後 | 終點變化 | 任一列 < 改前 ⇒ 停、交業主 | 全 56 場（終點量測，「測試選擇」第 2 條第一種時機）；改前用 `arch/fill/run/m0fa`（現行受測物），不重量 | 上一片 M0 改後約 1 小時 43 分；模擬客人 6 位 358,514 token＋盲判 5 批 268,470 token；Bedrock 約 340 回合 ≈ US$0.29 |
| X8 收案 verifier | 宣稱是否成立 | REFUTED ⇒ 依發現處置 | 1 位 fresh verifier，另寫 ≥10 句新輸入、換表單換說法，三種回合都要有 | 上一片 X8b 101,928 token；實跑約 70 回合、約 2 分 |

不跑：開關 off 對照批（off 與現行逐字相同，由 FW11 (a) 保證）；M0 改前重量（現值已在現行受測物上量過）。

**分工與獨佔**：核可後，程式改動（`write_forms.py`、`runtime.py`、新測試檔、`docker-compose.prod.yml` 兩行宣告）交一位 security-executor 獨佔（值閘屬寫入前驗證，依全域安全路由 ⛔ 一般 executor；上一片同），brief 帶 §4 全文、FW11 與 Hard rules（⛔ stash、⛔ 寫 canon、⛔ 整包 dump 憑證、⛔ 憑證進 argv；臨時容器 label 指令）；主會話獨佔文件、常駐重建、X0～X7 量測與判讀；X0 撰寫代理、X8 verifier 只讀不寫 repo。

**用量報告**：收案報告列子代理 token 加總（任務通知 `<subagent_tokens>`，逐位列）與 Bedrock 費用（`usage_events.est_cost_usd`，起訖時間與查證 SQL），格式比照上一片。

## 8. 停點、回復、待業主

**核可時業主已裁**（§6）：

- **Q1 空陣列（偏離 C1 (a)）**：寬回合 AI 回 `data_texts` 空陣列時，要 (a) 照上一片一律不併（「租金改成17000感謝您」探針 1/3、「繳費期限改到 2026/12/20，辛苦你了」2/2 的更正會被擋，回「這次的修改沒有套用」）；(b) 只在意圖 `fields` 也空時不併（後一句仍會被擋）；還是 (c) 一律當資料段未知、照現行收值（建議；代價是卡後或首句純道謝時，主模型把道謝提議成欄位值仍會上卡，X4 現行 7 筆沒有這一種，由 FW2 量）？上一片 C1 (a) 的選項說明寫「最壞結果是多問一次」；在卡後回合，最壞結果是更正改不掉。(c) 另一個代價：首句意圖回 `action: "none"`、`data_texts` 空（G3 探針「浴室的燈不亮，已經壞了3天3q，…」2/2）時，主模型若把「…3天3q」提議成問題描述，會照現行上卡（等同 FA1b-rep-06 現況）；FW1 依回合類型另報 `fill_wide_data_unknown` 回合中的錯筆卡數，供裁定後回看。
- **Q3 FA1c-bill-02 型（客人資料覆寫已填欄）算不算錯筆卡**：卡後「說明幫我加：退租清潔 thx」，帳單項目「清潔費」被換成「退租清潔」。改前（`arch/fill/x2-before/`）這場是「填入」，上一片改後才變錯筆卡；與上一片第 13 點第 2 題（說明欄**重複**帳單項目、改前就有）不同。要 (a) 算錯筆卡（建議；已填的正確值被換掉，按確認就寫錯資料，屬 DSP-115 第 3 點不得後補），還是 (b) 比照第 13 點第 2 題算欄位錯置、列後補？本計畫照 (a) 寫，X4 現值 7 筆含這一筆。
- **Q4 預期變化為 0 的列**：終點表 M0 各列、道謝後轉真人、單欄追問錯筆卡、E2a、E 片、F12、單元測試、audit 本片預期都是 0（本片只修三種回合的錯筆卡，這些列只防退步）。同意這些列預期 0、以「改後 ≥ 改前」收案嗎？（全域「終點指標」第 4 條：本片鎖定列「首句、卡後、多欄錯筆卡」預期不為 0，斷路器不因這些列觸發。）
- **Q5 現值未量的兩列**：FW3 多欄回合帶非資料的輸入，既有題組沒有，要等 X0 寫完新輸入才量得到；F3″ 上一片第 5、6 輪未重跑。兩者都排在 X1：核可後、改程式前量（改程式前量到的就是現行受測物的現值，結果寫進計畫終點表再開工）。同意這樣排（建議），還是要核可前先量（多一輪 X0＋X1 約 14 分、12～15 萬 token，且 X0 得在核可前派）？
- **Q2 名稱緊貼英數道謝的殘留**：首句「松仁晴空3Q」這類，AI 連道謝一起標成資料，程式端不列詞表就擋不到。要比照上一片第 13 點第 1 題列已知偏離（建議），還是另想做法（要列詞表就違反 DSP-091，需先改 DSP-091）？

**主會話讀法（我先這樣做了，要改請說）**：
- 「確認卡後」只算打字，不含按鈕（FW-R1）。

**停點**：X1 改前 FW1～FW3 錯筆卡 0；X2 新失敗；X3～X5 錯筆卡 ≥1（不屬 Q2 已接受類型）或卡住增加的場帶本片標記 ≥1；X6、X7 任一退步；verifier REFUTED 且屬 DSP-115 第 3 點。

**回復**：`AGENT_FILL_DATA_TEXT_WIDE=off` 重建常駐即回到現行（單欄追問回合不受影響；前提是 4.4 的 compose 宣告）。收案前實證一次：以 off 重建後 `docker exec -w /app aichatbot-rag-orchestrator python -c "import os;print(os.environ.get('AGENT_FILL_DATA_TEXT_WIDE'))"` 印 `off`，再打 FW11 (c) 那句首句、卡面與現行相同，然後回 on 重建；程式回復以 `arch/fill2/baseline/`（改程式前備份改動檔）＋`git diff` 還原。

## 9. 後補清單（DSP-115）

（審查與量測中產生，收案時一起處理。）

- 道謝被 AI 標成資料（§11 RC-W4，業主列已知偏離）：規則句兩版都沒收斂；結構性解法（不列詞表）另行定題。
- 鋪陳多欄回合有值沒套上、也沒有標記（FA1a-con-01 改前改後皆然、FA3-bill-03 改後）：§11 RC-W1 只讓下一回合補得回來，當回合為何沒套上未查。
- `test_f12_name_lenient_req.py::test_f1_typo_contract_ref_lists_contract_candidates` 偶發失敗：隨機 nonce（例 `22dfa10937330805`）含 `09\d{8}` 會被當手機號碼抓到（`arch/fill2/unit-after-r1-run2-flake.txt`；單獨重跑 134 筆全過）。與本片無關。
- 首句等待逾時後主模型輸出截斷 ⇒ 轉人（M0 改後 W-D1_k2、S-1_k1；改前 K8_k2 同型）：重放 18 次 0 重現（§11 X7），業主裁「判偶發，列後補」。截斷的成因未查。
- 首句程式先判等待逾時偏高：重放 15/18、M0 改前 17/56 改後 15/56（`WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S`＝1.0 秒）；改前改後同水準，逾時後走主模型提議，結果正確。
- 卡後回合有草稿、本回合沒出卡 ⇒ `WRITE_NOT_ISSUED_TEXT`（M0 改後 C-R_k2 第 4 句「對，是捷仕堂 溫馨雅房可租補」）：下一句重說即出卡。

## 10. 審查紀錄

**r1 plan-verifier（fresh，2026-10-28，136,642 token）：REVISE**。處置：
- F1（P2）FA1c-bill-02 讀成「欄位錯置」不算錯筆卡，但它改前是填入、上一片才翻成錯筆卡，且與上一片第 13 點第 2 題的「重複」不同：**FIX**——裁定前照原判分算錯筆卡（§1、§5 第 1 點、FW-R2），交業主 §8 Q3；§0、§1、FW0 的 X4 現值統一為 7。
- F2（P2）值閘屬寫入前驗證，核可前沒有唯讀 security-reviewer：**FIX**——送下一位 plan-verifier 前，先由唯讀 security-reviewer 審 §4.3 第 3～6 點（含第 4 點等意圖結果、讀同一個結果物件），發現與處置寫在下方。
- F3（措辭）終點表缺 M0 分組列、FW6／FW7 列、E 片來源：**FIX**（§0 表）。
- F4 預期 0 的列沒有業主同意：**FIX**——§8 Q4。
- F5 FW3 多欄、F3″ 現值未量：**FIX**——§8 Q5（核可後、改程式前量，或核可前量）。
- F6（措辭）§4 各項沒標 P 號：**FIX**（§4 各項）。
- F7（P3）FW13 只比 diff 與 porcelain、X0／X1 成本按舊句數：**FIX**——FW13 加未追蹤檔內容 md5（`arch/fill2/baseline/wt-before-plan.txt` 已補 13 檔）；X0 125 句、X1 約 14 分 US$0.47、X3 約 10.7 分 US$0.37。
- 待查：首句意圖回 `action: "none"`＋空陣列時 (c) 會讓「…3q」照現行上卡：併入 §8 Q1 的代價說明，FW1 依回合類型另報 `fill_wide_data_unknown` 回合中的錯筆卡。

**security-reviewer（唯讀，§4.3 第 3～6 點、第 8、10 點、§4.4；2026-10-28，203,826 token）**：第 1 題（會不會放寬）、第 3 題（模型輸出或注入能否放寬）、第 4 題（資料段外流）無發現——所有放行出口回的都是 (i) 的輸出，(iii) 只加一道「且」；`data_texts` 存的是原句 `message[s:e]`。處置：
- F1（P2）回復開關傳不進常駐（compose 只傳明列鍵、無 `env_file`）：**FIX**——主會話重查屬實（§4.4 指令與正對照）；4.4、4.6 加 compose 宣告，§8 回復加 off 實證步驟。待查（上一片 X8 off 對照當時怎麼注入）不影響本片，不追。
- F2（P3）等意圖的實作約束不足（`fill_proposal_first` 會讓第 4 點失效、重用 `_await_write_intent` 會重複副作用、上限少 `max(0.0, …)`）：**FIX**——寫進 §4.3 第 4 點實作約束與 FW11 (o)。依 DSP-115 第 2 點本可後補，但不修第 4 點直接失效（G5 兩筆修不到），屬「會改變下一步」。
- F3（P3）卡後部分更正被拒收、卡重出時回話不提：**FIX**——§4.3 第 8 點、FW11 (p)、FW2 期望。客人按確認會寫進他已說要改掉的舊值，近 DSP-115 第 3 點（寫錯資料），不後補。
- 觀察：新欄位 `field(repr=False)`、新判讀路徑 ⛔ 記 `str(exc)`：寫進第 10 點與 FW11 (m)。A+ 前提：寫進 4.4。

**r2 plan-verifier（fresh closing review，2026-10-28）**：**READY**。下一關：業主核可（附 §8 Q1～Q5）。

## 11. 修復輪 1（2026-10-28，業主核可）

**觸發**：X3（141 場）錯筆卡 8 → 3，停點觸發；X4 7 → 2；X5 1 → 1（FA1b-est-02 修好、FA1c-con-03 新增）；卡住 X4 24 → 31、X5 10 → 16，增加的場帶本片標記（`fill_value_outside_data`＋`fill_segment_not_in_message`）。紀錄：`arch/fill2/x3-after/`、`x4-after/`、`x8-after/`（各含 `records.jsonl`、`judge.txt`）。

**根因（對碼，可重跑）**：
- RC-W1 寬回合擋掉前一句已講過的值（FA1a-con-01、FA3-bill-03）：鋪陳的多欄回合有值沒套上（FA1a-con-01 改前同一回合 `write_draft_keys` 也是空），下一回合 AI 再提議，改前照 (i) 補上；本片 (iii) 只拿最新一句的資料段比 ⇒ 拒收。屬 §4.3 第 6 點沒預見的後果（沿用上一片 RC2「前面回合的值照舊擋在 (iii)」，`grep -n "只縮不擴" rag-orchestrator/services/agent/runtime.py`），不是實作偏離。
- RC-W2 AI 把表單沒有的欄位改填別欄（FA1c-bill-02，§8 Q3 算錯筆卡）：卡後「說明幫我加：退租清潔 thx」⇒ 帳單項目「清潔費」換成「退租清潔」；`manual_bill_create` 沒有說明欄。
- RC-W3 AI 把另建一筆當成改卡（FA1c-con-03）：卡後要另建一份別的物件的合約 ⇒ 卡上物件被換掉。
- RC-W4 道謝被 AI 標成資料（FW1-est-01「空間類型：ty」、FW3-est-02「行政區：中和區 感恩」、FW3-est-04「地址：…66號tks」）：探針 `arch/fill2/probe/probe_note.py`、`out_note.jsonl`（9 句 × 現行／候選 × 8 次）：候選說明句 F2 7/8 → 1/8、F1 0/8 → 6/8、F3 8/8 → 7/8，對照 C1～C3 0/8 → 0/8 ⇒ 整體不比現行好，不採。

**業主裁示**（AskUserQuestion 2026-10-28，選項原文）：
- 道謝錯筆：「不採這句，列已知偏離 (Recommended)」⇒ RC-W4 比照 §8 Q2 列已知偏離，範圍擴到文字值（地址、行政區、空間類型等），道謝緊貼或隔空白、逗號皆同；這類錯筆卡 ⛔ 算停點，照實報數。
- 修復輪：「三項都修，照排程重跑 (Recommended)」。

**改動**：
1. RC-W1（`runtime.py` `_write_draft_turn_gate` 寬回合分支）：在 (ii)、資料段未知之後、(iii) 之前，非 enum／category 欄先以同一值閘只比最新一句（`[wd.user_message]`）；不過（值只出現在前面回合的使用者訊息）⇒ 照 (i) 收、記新標記 `fill_wide_carry_over`（固定字串）、清該欄拒收紀錄；過 ⇒ 照第 6 點 (iii)。只限寬回合；單欄追問回合（上一片 RC2）不變。放行出口仍是 (i) 的輸出，等於改前行為，⛔ 比改前寬。
2. RC-W2（`write_forms.py`）：加一句共用常數，接在 `data_text=True` 附加的規則句之後：使用者講的欄位不在這個動作可填的鍵裡 ⇒ 那個值 ⛔ 改填到別的鍵。
3. RC-W3（同上）：加一句共用常數：使用者要另外再建一筆，是新請求，⛔ 拿來改這筆的欄位。
4. 第 2、3 點的例句 ⛔ 用 X3～X5 輸入原句；`data_text=False`（開關 off）時系統句逐字不變。
5. 單元測試（`test_fill_wide_req.py` 追加）：RC-W1 卡後與多欄各一（前句的值補上照收並記 `fill_wide_carry_over`；最新一句裡的道謝值仍被 (iii) 擋）；RC-W2、RC-W3 系統句含新句、`data_text=False` 逐字不變。

**重跑**（全域「測試選擇」；第 2、3 點改的是共用提示詞 ⇒ 判不出影響範圍）：X2 全套；X3 141 場（約 10.7 分、約 US$0.37）；X4 221 場（終點量測，約 15.5 分、約 US$0.53）；X5 106 場（約 7.6 分、約 US$0.27）；X6（約 21 分、約 US$0.70）；X7 M0 56 場（終點量測，約 1 小時 43 分、模擬客人加盲判約 63 萬 token、約 US$0.29）；X8 收案 verifier。停點同 §8，RC-W4 型除外。

**追加 r1b（主會話依第 1 點原意「這句才補上」收窄）**：X4 改後 FA1c-rep-06 卡後回合，AI 把前句物件名稱改寫成截短版重新提議，第 1 點新段照 (i) 收、覆寫了已填欄。改為：只在草稿該欄目前為空時走 carry-over；已有值 ⇒ 照第 6 點 (iii)。單元測試 R1-W1b；`unit-after-r1b.txt` 失敗集合＝基準 9 筆。定向重跑（「測試選擇」第 2 條：改動碰到的＝r1 紀錄中帶 `fill_wide_carry_over` 的 5 場；先前沒過的＝F3″ F3PP-05、-23、-37 與 E4 U4-1、-2、-4、-5、-8，依前例補跑 1 次）：腳本 `arch/fill2/run_r1b_targeted.sh`，結果 `arch/fill2/r1b/`。

**r1b 結果**（`arch/fill2/r1b/`）：carry-over 5 場 FW1-con-04 填入、FW3-con-01 重問後填入、FA1c-rep-06 錯筆卡 → 填入、FA1b-con-02 填入、FA2-con-02 重問後填入；F3″ 36/40；E4 補跑 5 題 × 6 情境 程式轉人 0/30、任何轉人 2/30（`e/analyze_e.py arch/fill2/r1b`）；單元失敗集合＝基準；invariants OVERALL PASS。

**追加 r1c（業主核可 2026-10-28「收窄卡後定義，定向重跑 (Recommended)」）**：
- 觸發：r1 E2a T 組 0/2（改片前 2/2）。T3「學生獨立套房可租補」在插問知識題（T2）之後，系統改走 estate_create、問縣市／行政區／地址／用途，沒有問修繕單的問題描述。
- 根因（對碼）：`_write_draft_turn_begin` 一進回合就把草稿的 `asked` 清空（`grep -n 'draft\["asked"\] = \[\]' rag-orchestrator/services/agent/runtime.py`）。T2 是問句 ⇒ 凍結；到 T3 草稿還在、`asked` 空 ⇒ `_fill_wide_begin` 判成卡後寬回合、送 `data_text=True`，但其實還沒出過卡。
- 探針：`arch/fill2/probe/probe_t3.py`、`probe_t3_only.py`，同一段對話送同一句：
  - 現行 estate_create 5/6；
  - 去掉 RC-W2/W3 兩句 estate_create 3/6；
  - 去掉 RC-W3 句 estate_create 5/5；
  - `data_text=False`（改片前這種回合送的） estate_create 1/8、none 7/8（`out_t3.jsonl`、`out_t3_off.jsonl`）。
- 改動：§4.1 (b) 收窄為「草稿綁定的卡還活著」。沒有活卡 ⇒ `_fill_wide_begin` 回 `{}`，系統句與值閘都照現行（改片前行為）。單元測試補兩種：無活卡的卡後回合不設 `fill_wide`；有活卡照舊設。
- 重跑（「測試選擇」第 2 條，改動碰到的）：
  - E2a 全部 6 組（44 場，r1 實測約 3 分）。
  - X3／X4／X8 r1 紀錄中「先前出過追問或卡、上一回合既不是卡也不是追問」的場：X3 8、X4 19、X8 14，共 41 場。這是近似選法：紀錄沒有回合種類，用回覆含「還需要」與 `card` 欄判；r1 平均每場約 4.5 秒。
  - 另跑單元測試與 invariants。
  - 腳本 `arch/fill2/run_r1c_targeted.sh`，結果放 `arch/fill2/r1c/`。
- r1c 範圍補正（業主核可 2026-10-28，選項原文「活卡或候選清單都算 (Recommended)」）。第一版只認活卡，單元測試 `test_fw11_l_bound_candidate_field_only_passes_i` 失敗，因為候選回合（列出候選、還沒出卡）也被排出寬回合了，和 §4.2「候選回合再接 `DATA_TEXTS_PICK_NOTE`」相牴。E2a T 組的 T2、T3 沒有寫入候選，只有知識條目 `candidate_ids`，所以這次補正不影響 T 組的修法。§4.1 (b) 已照此改寫。
- r1c 讀法（主會話採保守預設）：「還在等使用者選」的判法和附 `DATA_TEXTS_PICK_NOTE` 的條件相同，即 `_write_candidates_pick_open` 有值且 `picked is None`；已撤回的候選集算在內，已選定的不算。已選定、沒有卡、`asked` 空的回合（例：選定之後插問）因此不算寬回合，照現行處理，這和改片前一致。符號：`_WriteDraftTurn.bound_card_live`、`_WriteDraftTurn.pick_list_open`、`_fill_wide_begin`。runtime md5 `7764d1e6…`，test_fill_wide_req md5 `88b455d4…`。

**r1c 結果**（受測物 runtime `7764d1e6…`、write_forms `4047bbcc…`，結果在 `arch/fill2/r1c/`）：
- 單元：失敗集合＝基準 9 筆（`unit-after-r1c2.txt`）。
- invariants：OVERALL PASS（`invariants-after-r1c.txt`）。
- E2a：R、D、C、T、RS、DS 各 2/2，T 組 0/2 → 2/2，T3 動作 repair_create（`analyze_e13.py arch/fill2/r1c/e2a`）。
- 定向 41 場：錯筆卡 0；和 r1 同場比，X3 8 場分布相同，X8 14 場分布相同，X4 19 場填入 11 → 10、卡住 7 → 8。翻轉的場沒有本片標記，資料段未知與值不在資料段的標記都是 0。

**X7 M0 結果**（改後 `m0w`＝runtime `7764d1e6…`，改前 `m0fa`；56 場、6 位模擬客人；判分 `arch/fill2/m0w_score.json`、盲判 `arch/fill2/blind/result.txt`，誘餌 30/30 判對）：

| 列 | harness 改前 → 改後 | 盲判 改前 → 改後 |
|---|---|---|
| A | 12/12 → 12/12 | 12/12 → 12/12 |
| K | 19/20 → 20/20 | 14/20 → 15/20 |
| W | 18/20 → 19/20（W＋W-D） | 10/10 → 10/10 |
| W-D | （併入上列） | 10/10 → **9/10** |
| 全部 | 49/52 → 51/52 | 46/52 → 46/52 |

- 停點觸發：盲判 W-D 少 1（W-D1_k2）。該場與 S-1_k1（紀錄場、不計分）首句都是「首句等待逾時 → 主模型輸出截斷 → 轉人」，約 18.5 秒；改前同類截斷轉人是 K8_k2。
- 查證：同三句（兩場改後講法＋改前講法）各重放 6 次＝18 次，轉人 0、全部正確出卡或列候選；等待逾時 15/18、截斷 0（`arch/fill2/probe/firstturn/rows.json`，快照 18/18）。M0 首句等待逾時改前 17/56、改後 15/56，截斷 1 → 2。
- 盲判翻轉另有 K1_k1 通過 → 不通過（知識作答漏一句必含事項）、K6_k2 與 K8_k2 不通過 → 通過；知識回合不經本片判定。
- C-R_k2 第 4 句回 `WRITE_NOT_ISSUED_TEXT`（有草稿、本回合沒出卡），下一句重說即出卡、送出正確；該場兩把尺皆通過，錯筆卡 0。
- 業主裁定（2026-10-28）：「判偶發，列後補，進驗證員」——首句截斷轉人列 §9 後補，進 X8。

**X8 前查證 FW6 F3″**（主會話，2026-10-28）：
- F3″ (2) 改前 37/40（`arch/fill2/x5b/f3pp_score_before.json`）；r1 34/40；r1b 補跑 F3PP-05、-23、-37 後 36/40（`f3pp_score_r1b.json`），沒找到的是 F3PP-08、-15、-38（改前同樣沒找到）和 **F3PP-23**。照 FW6「改後 ≥ 改前」字面，少 1 句。
- F3PP-23「單身貴族那個雅房 我想報」→「報修 熱水器沒熱水」：第 1 句兩邊都沒建草稿，所以第 2 句是首句寬回合。改前 AI 把第 1 句的物件名一起帶進草稿（`write_draft_keys:description,estate_name`），之後列出候選；r1 只帶了問題描述（`write_draft_keys:description`），沒有 `fill_value_outside_data`，也沒有 `fill_wide_carry_over`。r1b 第 1 句讀成 estate_create，屬非目標「AI 選錯動作」。
- 探針 `arch/fill2/probe/probe_f3pp23.py`，輸出 `out_f3pp23.jsonl`，同一段對話送寫入意圖呼叫、每版 8 次：AI 帶出前句物件名，data_text 開 4/8、關 2/8。正對照（物件名和問題講在同一句）開 8/8、關 6/8。開了不比關差。主會話判讀：偶發、不是本片造成，待驗證員核、業主裁。

**X8 收案 verifier（fresh，2026-10-28，127,080 token）：REFUTED**。報告的證據在 scratchpad `x8w/`（重跑紀錄另存 `arch/fill2/x8-verifier/`）。主會話處置：
- F1（P1）卡後覆寫已填欄（Q3 型）：最終碼 FA1c-bill-02「說明幫我加：退租清潔 thx」跑 5 次，錯筆卡 2 次，帳單項目「清潔費」被換成「退租清潔」，沒有本片標記。主會話重讀紀錄屬實（`re-bill03-1`、`-3`）。r1 單次抽樣剛好填對。依 DSP-115 第 3 點不得後補 ⇒ **暫停，交業主裁修法**。
- F2（P2，本片引入）多欄或首句回合答物件名，被讀成 estate_create：改前 0/154，最終碼定向 5/39，M0 改後 2 場。主會話計數屬實。與 r1c 前 T 組、F3PP-23 r1b 第 1 句同機制（T 組探針：`data_text=False` estate_create 1/8，開啟 5/6）。非目標「AI 選錯動作」不涵蓋本片引入的情況 ⇒ 交業主裁要修還是後補。
- F3（P2）FW12 文件未改：**FIX**，主會話在程式定案後改正文。
- F4（P2）RC-W2、RC-W3 兩句也接到單欄追問回合的系統句上 ⇒ FW-R1「單欄追問照現行」、FW11 (b)、§8「WIDE=off 即回現行」字面不成立。X9 0/17 沒退步 ⇒ 交業主裁收窄或接受。
- F5（P2）X4 卡住 24 → 29、F3″ 37 → 36：**FIX**。修完後在最終碼上重量 X4 全量（終點量測）與 F3″。
- F6、F7（待查／P4）：新輸入卡住都不帶本片標記；知識插問被凍結是既有行為 ⇒ **DEFER**，進 §9。

## 12. 修復輪 2（草稿 2026-10-28；不採用，由 §13 取代）

**先答三題**：每個使用者層項目沿用 §7 的資料組與輸入（X3 5 表單 141 場、X4 5 表單 221 場、X5 5 表單 106 場；輸入由 fresh 撰寫代理寫、已凍結，非實作者）；定向重複只算穩定性（「a 組 × b 輸入 × c 次」照寫）；改前對照用 §11 r1c 最終碼紀錄（`arch/fill2/r1c/`、`x4-after/`、`x8-verifier/`）與改片前紀錄（`arch/fill/x4-after6/`、`x8-on6/`、`arch/fill2/x1-before/`）。終點指標同 §0；本輪預期變化：錯筆卡（首句、卡後、多欄）在最終碼為 FA1c-bill-02 2/5 → 0；多欄回合誤換新增物件單 4/27（`x8-verifier/est-x8c-*`）→ 0；其餘列預期 0（防退步）。前兩片實際變化見 §0 終點表。

### 12.1 業主原話與規則（AskUserQuestion 2026-10-28，選項原文）

| ID | 業主原話 | 可檢查的條件 | 主會話讀法 |
|---|---|---|---|
| R2-1 | F1「AI 標出沒有的欄，程式擋 (Recommended)」 | 寬回合的意圖呼叫回一組「講到表單沒有的欄位」的原話段；程式拒收與這些段重疊的任何欄位值（含覆寫已填欄），回覆照程式固定句說明沒加上；FA1c-bill-02 錯筆卡 0 | 回覆固定句 ⛔ 帶使用者原話（沿用 §4.3 第 8 點「⛔ 帶值」） |
| R2-2 | F2「同一輪一起修 (Recommended)」 | 本片引入的「多欄、卡後回合答物件名被讀成另一支寫入動作」修好；客人明講改辦另一件事仍照現行換單 | 首句那一類經開關對照判定**非本片引入**（12.2），不在本輪修法內，照非目標「AI 選錯動作」照實報數 |
| R2-3 | F4「收窄到三種回合 (Recommended)」 | RC-W2、RC-W3 兩句與本輪新句只接在寬回合；單欄追問回合的系統句、schema 與上一片逐字相同 | — |
| R2-4 | （§11 處置 F3、F5，主會話 FIX） | FW12 文件改正文；最終碼重量 X4 全量與 F3″ | — |

凍結規則與清單（`acceptance-fill-wide-20261028.md`，sha256 `7a25829b…`）不改；R2-3 是讓實作回到 FW-R1、FW11 (b) 的字面。

### 12.2 根因（對碼與探針，可重跑）

**F1**（FA1c-bill-02「說明幫我加：退租清潔 thx」，`manual_bill_create` 沒有說明欄）：RC-W2 那句只是提醒，AI 仍會把值改填到別欄；值在資料段內，(iii) 照收 ⇒ 覆寫「清潔費」。探針 `arch/fill2/probe/probe_f1.py`、`out_f1.jsonl`（卡後同一段對話、每版 12 次）：
- 現行：帳單項目被改成「退租清潔」5/12。
- 加 `not_in_form_texts`（schema 欄＋規則句）：帳單項目被改 0/12；AI 標出「退租清潔」11/12（其中 3 次連「thx」一起標）。
- 混合句「金額改 1500，備註寫押金扣抵」：金額套用 5/12 → 9/12；「押金扣抵」標出 11/12。
- 正常改欄「帳單項目改成退租清潔」：套用 8/12 → 5/12，誤標 1/12（那次沒填值，卡不會錯）⇒ **代價**：正常改欄可能較常沒套上，進停點（12.5）。

**F2 多欄、卡後**：寬回合送的 `data_text=True` 系統句沒有「目前在辦哪張單、剛追問哪幾欄」（單欄追問回合有 `ANSWER_TEXT_RULE_TEMPLATE`「正在追問的欄位」，寬回合 ⛔ `asked_labels`，§4.2），AI 只靠前文推斷；客人只回物件名 ⇒ AI 回 `estate_create`＋`title` ⇒ `_write_draft_decide` 的 `other_action` 帶值 ⇒ 換新草稿（`grep -n "other_action = " rag-orchestrator/services/agent/runtime.py`、`_write_draft_target`）。探針 `probe_f2d.py`、`out_f2d.jsonl`（多欄追問「物件、問題描述」後答「學生獨立套房可租補」，每版 16 次）：

| 版本 | 讀成 estate_create | 明講改辦（正對照「報修先不用了，我要新增一間物件…」）換單 |
|---|---|---|
| 現行 | 11/16 | 16/16 |
| 拿掉 RC-W3 句 | 6/16 | 16/16 |
| RC-W3 例句去掉「另一間」 | 9/16 | 16/16 |
| `data_text=False`（改片前） | 0/16 | 16/16 |
| 現行＋「目前狀態」句 | **0/16** | **16/16** |

RC-W3「下個月的也先開一張」對照：各版都回 `manual_bill_create`、⛔ 改本筆欄位（現行 16/16）。

**F2 首句（FW1-rep-05「幫我開單 學生獨立套房可租補 謝啦，電燈會閃爍」）不是本片引入**：同一受測物（runtime `7764d1e6`）`AGENT_FILL_DATA_TEXT_WIDE` off／on 各 8 場（`arch/fill2/probe/run_fw1r5_onoff.sh`，結果 `probe/fw1r5/`）：estate_create off 5/8、on 6/8；意圖呼叫單獨送（`out_f2d.jsonl`）off 11/16、現行 13/16。首句沒有進行中的單，「目前狀態」句不適用。

**FA1a-rep-13 首句漏問題描述**：只出現在 r1（`x4-r1`）；最終碼 `x4-after` 與 verifier 重跑 3 次（`x8-verifier/est-a13-*`）首句都收下問題描述、最後出對的修繕卡 ⇒ 不另修。

### 12.3 目標形態（業界原頁；沿用 §2 渲染檔，逐字）

- Rasa CALM 指令產生器把「目前狀態」結構化給模型（`arch/fill/sources/rasa-calm-command-generator.txt`）：「Active flow and slot - Active elements within the conversation that require the model’s attention.」模板：「{"active_flow":"{{ current_flow }}","current_step":{"requested_slot":"{{ current_slot }}",…」。⇒ F2：理解客人這句時，進行中的單與正在要的欄由程式給 AI。
- 同檔：「Only start a flow if the user's message is clear and fully addressed by that flow's description and purpose.」「Do not cancel any flow unless the user explicitly requests it.」⇒ 只有明講才換單。
- 同檔：「Extract text slot values exactly as provided by the user. Avoid assumptions, format changes, or partial extractions.」；Copilot Studio（`copilot-slot-filling.txt`）：「The agent understands what information belongs to which entity. In cases where it's unsure of the intended mapping, it prompts the user to be more specific by providing choices.」⇒ F1：值對不到欄位時不硬塞到別欄。
- 「表單根本沒有客人講的那一欄」怎麼回：**查無業界專節**。第一原理：沒有的欄不能借別欄存（存了就寫錯資料）；客人要知道那段沒加上，才不會以為已記下。
- 分工（DSP-091）：AI 標「哪段講的是表單沒有的欄」「這句是不是在回答進行中的單」；擋不擋、換不換單、回什麼由程式。

### 12.4 改動（核可後交 security-executor 獨佔；值閘屬寫入前驗證）

1. **F4 收窄**（`write_forms.py`）：`write_intent_system_prompt`、`write_intent_call_schema`／`write_intent_response_format` 加參數 `wide: bool = False`；`FIELD_NOT_IN_FORM_NOTE`＋`ANOTHER_RECORD_NOTE`、本輪新句與新 schema 欄只在 `wide=True` 接。`_fill_wide_begin` 回 `{"data_text": True, "wide": True, …}`；單欄追問回合（`_fill_begin_intent_call` 末段）照舊 `{"data_text": True, "asked_labels": …}` ⇒ 系統句與 schema 和上一片逐字相同（上一片版本以 `arch/fill2/baseline/write_forms.py` 為準）。
2. **F2「目前狀態」句**（`write_forms.py` 新常數、`runtime.py` `_fill_wide_begin`）：卡後與多欄寬回合（有進行中的草稿），在系統句最末接程式組的一句：多欄＝「目前狀態：進行中的單＝{表單中文名}（{動作鍵}）；剛才追問的欄位＝{欄位標籤、以頓號接}。客人這句在回答追問時，action 回進行中這張、照它的欄位填；只有客人明講要改辦另一件事，才回另一個 action。」（探針逐字）；卡後＝同句，前半改為「進行中的單＝{表單中文名}（{動作鍵}），已出確認卡、等客人確認或修改」、「回答追問」改為「改這張卡」。`{}` 只放程式持有的 `title_zh`、動作鍵、`Field.label`（⛔ 使用者原話）。首句不接。程式端換單規則不改（`other_action` 照現行）。
3. **F1 表單沒有的欄**：
   - (a) schema（只在 `wide=True`）加 `not_in_form_texts`（字串陣列）與規則句（探針逐字：「not_in_form_texts：使用者最新一句裡，講到這個動作沒有的欄位（例如這個動作沒有「說明」欄，使用者說「說明寫退租清潔」）時，那一欄的值逐字照抄列在這裡；這些值 ⛔ 填進 fields 的任何鍵。沒有 ⇒ 空陣列。」；例句 ⛔ 用 X3～X5 輸入原句，正式例句由 executor 換成不同字的同型句，換後重跑 12.5 F1 探針）。
   - (b) 程式讀法同 `_fill_wide_read_data`：由驗過的原始物件讀，逐段以 `_fill_data_spans` 驗是最新一句原字；鍵缺、`null`、型別錯、段不在原句 ⇒ 當沒有（照現行收值，Q1 同理）。⛔ 讀模型字串本身。
   - (c) 值閘（寬回合 (iii) 之前，`_fill_wide_precheck` 同層）：text／period 欄的候選值與任一段重疊（去空白後互為子字串）⇒ 只拒收這一個值、記新標記 `fill_wide_not_in_form`（固定字串）；enum／category 不比；候選集綁定欄豁免與 (iii) 相同。來源含意圖 `fields`、主模型提議、整句填入三條（與 (iii) 同一入口）。
   - (d) 回覆：本回合有值因 (c) 被拒 ⇒ 回覆加程式固定句「您提到的部分內容，這張單沒有對應的欄位，沒有加上。」（新常數；與 `fill_wide_not_applied_text` 同一出口、排在其後；⛔ 帶使用者原話）。卡後照現行重出卡；首句、多欄照現行缺欄追問。
4. **單元測試**（`test_fill_wide_req.py` 追加）：F4 單欄追問系統句與 schema 逐字等於 baseline 版、寬回合含新句；F2 卡後與多欄系統句含狀態句、首句不含、`{}` 只來自表單定義；F1 (b) 段不在原句當沒有、(c) 重疊拒收記標記且不覆寫已填欄、enum 不受影響、off 不送新欄、(d) 固定句不含原話。既有 13 支 WIDE off 測試不改。
5. **開關**：沿用 `AGENT_FILL_DATA_TEXT_WIDE`（off ⇒ 三種回合、單欄追問皆回改片前）；不新增開關。

### 12.5 執行與測試選擇（全域「測試選擇」；每回合約 1.47 秒、US$0.00084，§7）

| 執行 | 回答的決定 | 會改變下一步的結果 | 規模與理由 | 跑前成本 |
|---|---|---|---|---|
| Y0 單元、audit、canon-accept、invariants | 能否進使用者層 | 新失敗（基準 9 筆以外）⇒ 修到過 | 全套（便宜、決定性） | 約 3 分 |
| Y1 F1 探針重跑（換正式例句後） | 正式字面是否保住探針效果 | 帳單項目被改 ≥1/12 或正常改欄套用 < 5/12 ⇒ 停、交業主 | `probe_f1.py` 3 句 × 12 次（意圖呼叫） | 36 呼叫、約 2 分、< US$0.05 |
| Y2 FA1c-bill-02 定向 | F1 錯筆卡是否 0 | ≥1 ⇒ 停 | 1 輸入 × 8 次（穩定性；最終碼 2/5 才出現，少於 8 次看不出） | 約 40 回合、1 分 |
| Y3 X5 FA1c-rep-01～09 定向追加 2 次 | F2 是否 0 | 讀成另一動作 ≥1 ⇒ 停 | 9 輸入 × 2 次（加 Y5 的 1 次共 3 次，同 verifier 量法 4/27） | 約 60 回合、1.5 分 |
| Y4 X4 全 221 場 | 終點量測；F5 卡住 24→29 是否回落；FA1c 卡後正常更正有沒有變少 | 錯筆卡 ≥1（Q2 型除外）⇒ 停；卡住增加的場帶本片標記 ≥1 ⇒ 停；FW2 更正有套用 < r1c 值 ⇒ 停、交業主 | 全量（「測試選擇」第 2 條第一種：終點量測） | 15.5 分、約 US$0.53 |
| Y5 X3 141 場、X5 106 場 | 新說法錯筆卡與卡住 | 同 Y4 | 全量（第二種：改的是寬回合共用系統句與 schema，碰到哪些場判不出） | 18.3 分、約 US$0.64 |
| Y6 F3″ 40 句、E2a 44 場 | F5 的 F3″ 37→36、T 組是否保住 | F3″ < 37/40 ⇒ 交業主（§11 待裁）；E2a 任一組 < 2/2 ⇒ 停 | 全量（F3″ 為 F5 處置；E2a 是多欄、卡後誤換單的既有回歸） | 約 4 分、約 US$0.13 |
| Y7 X9 17 場 | 不跑：F4 讓單欄追問逐字回上一片，由 Y0 逐字測試保證 | — | — | — |
| Y8 M0 全 56 場 | 終點量測 | 任一列 < 改前（`m0fa`）⇒ 停、交業主 | 全量（第一種；K 列 20 場中 4 場也進寫入流程，`arch/fill/run/m0w/convs/`，⇒ 不能只跑寫入列） | 約 1 小時 43 分；模擬客人＋盲判約 63 萬 token；約 US$0.29 |
| Y9 收案 verifier（fresh） | 宣稱是否成立 | REFUTED ⇒ 依發現處置 | 1 位；另寫 ≥10 句新輸入，三種回合、≥3 表單 | 約 13 萬 token |

不跑：E 片全量、F8、X6 其餘（本輪不碰轉人、收尾、單欄追問；Y0 逐字測試保證單欄追問）。合計 Bedrock 約 US$1.7、模擬客人與審查代理約 80 萬 token（估計，非上限）。

### 12.6 停點與回復

停點：Y0～Y9 表內各列；另 X4／X3／X5 任一場出現 `fill_wide_not_in_form` 且該場判卡住或欄位沒套上 ⇒ 列出交業主（正常改欄被擋的代價，12.2 F1）。回復：`AGENT_FILL_DATA_TEXT_WIDE=off` 重建；程式以 `arch/fill2/baseline-r1c/`（已備份，md5 runtime `7764d1e6`、write_forms `4047bbcc`、test `88b455d4`）還原。

### 12.7 後補（DSP-115）

- 首句「幫我開單 ＋物件名＋問題」被讀成新增物件單（FW1-rep-05；開關 off 5/8、on 6/8）：既有 AI 選錯動作，非本片引入；照實報數。

## 13. 前提重查與更正（2026-10-28 晚；§1～§12 是當時紀錄，不改寫，以本節為準）

業主：「要重查 你以靜錯過太多次」「我目前不信任你的成果」「我理解的是你把那些補丁 結構化的處理 在對其 流程 和 結構」。兩位唯讀 fresh 代理逐句重查（只讀檔、不呼叫模型）：§0～§8 100 條（成立 76〔其中單次抽樣 7〕、部分 11、不成立 7、單次抽樣且因果不成立 2、查不到 3）；§9～§12 84 條（成立 40、部分 25、不成立 9、單次抽樣 5、查不到 5）。全表：`~/jgb-archive/arch-step3-20261018/fill2/premise/audit-s0-s8.md`、`audit-s9-s12.md`。

改變結論的更正（細節與查證指令見上列兩檔的條目編號）：

1. **「manual_bill_create 沒有說明欄」不成立**（s9 #19、#20、#60、#77）：`grep -n '"sub_title", "說明"' rag-orchestrator/services/agent/confirm_card.py` 命中。FA1c-bill-02 的毛病是 AI 把說明填進既有的「帳單項目」欄。§11 RC-W2 定性、§12 F1 根因與修法、業主對 F1 的裁定都以此為前提 ⇒ F1 須重裁。
2. **FA1c-bill-02 不是本片引入**（s0 #40／#97、s9 #48、#8）：同一份最終碼 `fill2/probe/bill02/` 各 8 次，開關 off 覆寫 6/8、on 覆寫 4/8。「改前是填入、上一片才變錯筆卡」只靠改前 2 次執行。Q3 裁定（算錯筆卡）不變，敘述改正。
3. **FA1b-rep-06、FA1b-bill-09 的值來自寫入意圖，不是主模型提議**（s0 #33、#60、#70、#96）：兩場無 `write_proposal` 標記、來源 `program_draft`。§3 G5、§4.3 第 4 點、§4.7 在本批 7 筆錯筆卡中沒有對應事件。FA1b-bill-09 實際讀成手動帳單、說明收進「3Q」（s0 #34、#62）。
4. **F2 修法候選「目前狀態句」未證實**（s9 #69、#70、#75）：`fill2/probe/out_f2d.jsonl` multi 題（正解 `repair_create`）16 次：cur estate_create 11；state estate_create 0，但 repair_create 只有 2、none 14；off repair_create 4、none 12。RC-W3「下個月的也先開一張」對照沒有跑狀態句版（`probe_f2d.py` `if st and not has_draft: continue`）；卡後版狀態句沒有探針。
5. **§12 改前對照基準錯**（s9 #57、#79）：`fill2/x4-after/` 是 runtime `523f3c4d`（修復輪 1 前），最終碼 `7764d1e6` 沒有 X4 全量紀錄。
6. **待業主裁**（s9 #14）：FA1b-bill-09 改後卡是修繕單「問題描述：管裡費 1000 元」，判分記為欄位錯置、未算錯筆卡；同口徑下 X4 錯筆卡可能是 3 而不是 2（DSP-115 第 3 點）。

處置：§12 不採用；本片不再逐案加規則句與閘門。下一步依 `HANDOFF-20261018.md` §0.5、§2.3 第一列：現行程式整組重跑 OV 口語題組與 M0 → 依斷點分布與四層盤點（AI 輸入狀態／AI 輸出格式／程式每回合驗值／程式決定下一步）寫結構化修法新計畫 → 審查 → 業主核可。
