# F12 名稱講不準時找得到：計畫 r5（2026-10-22 業主核可，清單原話 12；依原話 11；r5-1 不做、r5-2～r5-4 照做、r5-5 只做名稱；r4 於同日核可（原話 9），r3 裁定見原話 6 與清單第五節）

規則與驗收清單：r5 `acceptance-name-lenient-f12-r5-20261022.md`（同目錄；業主核可後凍結，判定一律依該檔）；r4 凍結清單 `acceptance-name-lenient-f12-20261022.md`（紀錄）。決策：DSP-110（本片排在 W2 前）、DSP-091（分工）。服務原則：P5（對話修補：處理不了、候選選擇）。

r2 依據：r1 plan-verifier REVISE（B1～B7）；業主 2026-10-22「照建議，先做實驗」→ 實驗報告 `~/jgb-archive/arch-step3-20261018/f12/exp/report-exp.md`；業主「照建議，定 AI 從清單挑」；量體依業主「有點太大」「小一些」「不要在放大了 目前的量體就好」「後續的測試也注意量體」。r3 依據：r2 plan-verifier REVISE（資安審查、F2 挑題與基準分開、開發集重疊、查不到出口兩句都計、規則 ID、OV 其餘題去向、審查 brief 附原話），處置見 §10。r4 依據：r3 實作後 F3 兩輪實打未達 85%（第 1 輪改後 26/50；R1 實作偏離 §4.2 修正後第 2 輪 41/50，改前 4/50；紀錄 `~/jgb-archive/arch-step3-20261018/f12/run/f3f4-r1-record.md`），剩餘未中根因 R3（名稱沒進草稿）、R4（前一回合講的名稱以草稿值比對落空）；業主 2026-10-22 選「擴範圍修 R3＋R4」（清單原話 7）。r4 改動：§1（第 2 點限 (甲)、宣稱依據改 F3′）、§2.3 第 5、6 點、§4.2（(甲)(乙) 觸發、閘門、整句來源）、§4.3 (乙) 前言、§4.4、§4.5、§4.7、§4.8 r4 表、§5 量測量體、§6 r4-1～r4-3、§7、§8 結果停點、§10 r4 表。

r5 依據：r4 實作後 F3′ 改後 27/50（54%）、改前 2/50，依 §8 停；業主准許拿 F3′ 診斷（清單原話 10）。診斷（§2.3 第 7 點）：23 句未中有 16 句名稱已進草稿，但缺欄檢查排在名稱解析之前，其他欄位收不進來 ⇒ 名稱從沒被查。業主裁「照這個方向寫 r5」（原話 11）：名稱一講就先查，不等其他欄位收齊。r5 改動：§1 第 3 點與宣稱依據改 F3″、§2.1 r5 表、§2.3 第 7 點、目標形態、§3 G-6、§4.2 (丙)、§4.5、§4.7、§4.8 r5 列（待審）、§5、§6 r5-1～r5-5、§7、§8、§10 r5 表。

r6（2026-10-24 業主核可，r6 清單原話 16）：選定後可改選，自成一節見 §11；§1～§10 不改。

## 1. 目標（設計方法第 1 步）

- 使用者用簡稱、漏字、錯字（含同音字）、全半形不同、名稱前後帶描述詞講物件或合約名稱時，系統列出含那一筆的候選讓使用者選；⛔ 回「系統裡查不到這個編號或名稱」就結束。
- 真的找不到時（(甲)：使用者講的名稱已進草稿、現行與寬鬆都查無），程式以固定句說明找不到這個名稱並請使用者重講名稱（不回顯原話，§4.8 S-9）；⛔ 使用者補其他欄位時一再回同一句「查不到」。(乙)（名稱沒進草稿）寬鬆也落空時照現行追問名稱欄、不出「找不到」說明——程式分不出使用者是沒講名稱還是講了但 AI 沒抽到，出「找不到」會對沒講名稱的人說錯話；此情形與現行行為相同（不變差），列 §6 r4-3。
- 使用者在寫入流程中講出物件或合約名稱、其他必填欄位還沒給齊時，系統**當回合**就依名稱查：查無或多筆 ⇒ 當回合列候選（查無且寬鬆也落空 ⇒ 第 2 點的找不到說明）；唯一 ⇒ 照現行追問其他欄位（r5，原話 11）。⛔ 等其他欄位全收齊才查名稱，而讓收不進來的欄位擋住名稱查找（F3′ 23 句未中有 16 句是這個形狀，§2.3 第 7 點）。
- 終點指標（現值＝選對紀錄片改後量測，程式＝本片改前；挑題與基準分開：以每題第 1 次紀錄挑「出現查不到出口」的題，第 2 次紀錄當基準；`python3 ~/jgb-archive/arch-step3-20261018/f12/ov_baseline.py` 末段重算）：

| 指標 | 題組 | 現值（第 2 次紀錄） | 預期（改後每題 1 次，同分母比例） |
|---|---|---|---|
| 出現查不到出口的場次比例 | OV 28 題（開發集外） | 21/28（75%） | ≤ 38%（減半以上） |
| 其中未解決（OV 程式前判） | OV 28 題（開發集外） | 10/28（36%） | ≤ 18% |
| 出現查不到出口的場次比例 | V3/V4 13 題（開發集內，含 V3E 5 題） | 12/13（92%） | 只報，不作宣稱依據 |

  預期值的依據：開發集 190 句中 161 句（85%）有名稱片段；方案在開發集抓到 90～97%（§2.3）；同一場可能出現多次查不到、也有不含名稱片段的講法（只講位置、只補欄位），所以預期取「減半」而不是 76%。開發集取自 V3/V4 對話（`f12/exp/build_dataset.py` 只收 `v34_pick.json` 場次），所以 V3/V4 題的結果不撐宣稱；宣稱只靠開發集外的 OV 題與 F3″ 新輸入（原 F3 輸入已用於 r3 診斷、F3′ 已用於 r4 診斷，都只報）。

## 2. 目標形態（第 2 步；業界原文 `~/jgb-archive/arch-step3-20261018/f12/industry.md`，渲染頁 `f12/sources/`）

### 2.1 業界原文

各家講的是槽位／實體值清單，沒有一家直接講「名稱對到資料庫某一筆紀錄」；以下套到紀錄屬推論。

| 面向 | 業界原文（逐字） | 出處檔 |
|---|---|---|
| 依「這位使用者的」清單解析 | Lex runtime hints：「generate a list of account nicknames for a specific user」；不在清單時「the original user input will be used for the slot」 | `lexv2-runtime-hints.txt` |
| 由 app 自己查自己的資料 | Apple `EntityStringQuery`：`entities(matching: String)`（不規定演算法，由 app 實作） | `apple-entitystringquery.txt` |
| 容錯 | Copilot Studio smart matching：「autocorrect misspellings and expand semantically」——原文只寫在 Closed list 小節，文件未說是否適用 open list（`industry.md` 已註） | `copilotstudio-entities.txt` |
| 多筆或不確定時讓使用者選 | Apple `requestDisambiguation(among:dialog:)`；Copilot Studio 依 `ConfidenceScore`「accept, disambiguate, or reprompt」 | `apple-requestdisambiguation.txt`、`copilotstudio-entities.txt` |
| 多筆說得通時不替使用者選 | Alexa：「Don't: Make an assumption and select for them when there's more than one plausible match for what the customer said」 | `pick-right/sources/INDEX.md` |
| 動態清單上限 | Copilot Studio open list、Alexa dynamic entities 約 100 筆 | `industry.md` 對照表 |

各家不同：Rasa 詞表是正規表示式＋同義詞，五頁查無 fuzzy；Dialogflow CX 的 fuzzy 只寫詞序無關；Lex 預設 Expand 模式解析相似值。⛔ 寫成「業界都」。

r5 驗證時機（渲染頁 `~/jgb-archive/arch-step3-20261018/f12/sources/r5/`，抽取腳本同目錄 `ind.py`；只查這三家，Intercom、Copilot Studio 未查）：

| 面向 | 業界原文（逐字） | 出處檔 |
|---|---|---|
| 收集步驟當下驗證、沒過當場重問 | Rasa：「You can define slot validation rules directly in your flow yaml file by adding a rejections property to any collect step.」「When validation fails, your assistant will automatically try to collect the information again. The assistant will repeatedly ask for the slot until the value is not rejected.」 | `rasa_flowsteps.txt` |
| 每收到一欄就能交程式檢查；意圖辨識後的第一個回應也能呼叫程式（原文未寫此時拿得到首句的欄位值） | Lex V2：「You can use Lambda functions at the following points in a conversation with a user:」「In the initial response after the intent is recognized.」「After eliciting a slot value from the user.」「When confirming an intent.」 | `lex_dialoghook.txt` |
| 抓出本回合剛填的欄位、交後端驗證 | Dialogflow CX：「To check whether a particular form parameter was filled in the last turn, use the following condition: $page.params.parameter-id.status = "UPDATED"」；webhook「validate collected data」 | `cx_parameter.txt`、`cx_webhook.txt` |
| 欄位順序由設計者排 | Rasa：「Your assistant will not proceed to the next step in the flow until the slot account_type has been filled.」（步驟依 flow 定義的順序） | `rasa_flowsteps.txt` |

三家都提供「欄位收到的當回合就驗」的時點；現行「全收齊、出卡前才查名稱」對應 Lex 的「When confirming an intent」那一個時點。三家文件都**沒有**規定名稱要排在其他欄位之前，也沒有寫「名稱模糊時列候選」——名稱先查是本片依 §2.3 第 7 點實測選的順序（第一原理：名稱錯了，其他欄位填得再完整也是寫到錯的那筆；名稱不先定，收不進來的欄位會把名稱查找一起擋掉），候選清單沿用 A-2a。

### 2.2 第一原理（查無業界對應的部分）

- 錯字多是同音字（量測實例：號宅／豪宅、像山／象山、側／測、男／南、路／錄），程式要在**讀音**層比對才抓得到。
- **只有 1 筆寬鬆命中也列候選**：這是第一原理，偏離 Copilot Studio 信心高時「accept」。理由：寬鬆命中可能錯，而確認卡確認的是整筆寫入，不是「你指的是這筆嗎」；多一步換不寫錯。
- 前篩用**整句**不用抽出的片段：實驗中讓 AI 先抽片段，抽成描述（「6/1 到期的那張帳單」「基隆那間」）就對不上（§2.3 第 1 點）。

### 2.3 實驗證據（`report-exp.md`；1 組資料 × 190 句 × 2 次，句子為選對紀錄片量測中回查不到的使用者句，盲判分類）

1. 程式讀音比對靠抽出的片段：名稱句 69%（τ0.5）；給它正確片段則 160/161——瓶頸在抽片段，不在比對。
2. AI 看使用者的清單直接挑：83／29 筆清單 95%（程式同名展開後 97%）；100 筆 94%；200 筆掉到 73%。
3. 程式整句前篩前 50 筆 → AI 挑：100 筆 92%、200 筆 89%，每次 prompt 約 1,100 token（看整份 200 筆的四分之一）。
4. AI 只列一筆相近名稱而漏目標（200 筆漏抓 87 次中 57 次）：程式再補「前篩分數不低於 AI 所挑最低分」的紀錄、同名展開、上限 5，離線重算 200 筆 84%→90%、100 筆 89%→93%、83／29 筆 95%→97%（`f12/exp/augment.py`、`augment.txt`；不呼叫模型）。
5. 無指稱句（只補欄位）誤列候選 3～6/38 次 ⇒ 觸發要限縮：「現行查找查無」，或「寫入流程該填名稱卻沒有名稱」的那一回合（r4，見第 6 點；誤列率由清單 F5 量）。
6. 實打（r3 實作，F3 凍結 50 句；`f12/run/f3f4-r1-record.md`）：使用者第 1 句講名稱、表單補齊那回合才查名稱，是常見形狀（只講一半、分多句、一句多件事）。修正整句來源後仍有兩型落空——(R3) AI 意圖呼叫沒把名稱放進草稿（`write_intent_value_not_in_user_words` 或草稿鍵不含名稱欄），系統從頭沒查名稱，只一再追問「還需要：合約／物件」；(R4) 名稱在前一回合講、以草稿名稱欄值當整句，寬鬆回空。原因「抽到的值是片段、對不上」是推論、未證實：草稿值查無後已被清掉、沒有取到（紀錄同段）；與第 1 點的實驗觀察同形，r4 改用使用者原話當整句即繞過此點，不論推論是否成立。
7. 實打（r4 實作，F3′ 凍結 50 句，改後 27/50；診斷 `f12/run/f3p-miss-diagnosis.txt`，腳本 `f12/run/f3p_miss_cls.py` 逐回合查 trace `usage_events.decision_snapshot->'agent'->'violations'`）：23 句未中——
   - 16 句（F3P-06、07、16、17、19、20、23、28、30、32、34、41、44、45、47、49）：名稱已進草稿（`write_draft_keys` 含 `estate_name` 或 `contract_ref`），但 `_prepare_closed_action` 與 `confirm_request` 先以 `missing_required_labels`／`missing_labels` 回缺欄、排在名稱解析之前；其他欄位一直收不進來 ⇒ 3 回合內名稱從沒被查。收不進來的原因（同句可多項）：日期值被值閘丟掉（`write_intent_value_not_in_user_words`，如「這張期限11/30」）10 句、程式先行等待逾時（`write_draft_program_first_wait_timeout`，R2）10 句、延期講目標日不換算天數（「延到11月25日」一直追問「延後天數」）3 句。
   - 4 句（F3P-26、29、39、50）：首句被答成問答或轉人，未進寫入流程。
   - 3 句觸發了寬鬆比對但沒中：F3P-04「國泰那間」——目標正名「台北文山-離塵一房(國泰)」，「國泰」在括號內，被名稱核心規則（§4.1 去括號內文字）拿掉；F3P-10、F3P-40——首句沒進寫入流程（trace 無寫入標記），第 2 句 (乙) 只拿本句比對：F3P-40 回空（第 3 句名稱才進草稿，又被缺欄擋住），F3P-10 本句「承租人是林先生，一個月兩萬八」不含名稱卻列出 5 筆不相干候選。
   - 分類合計 16＋4＋3＝23（F3P-40 只計在本項；診斷檔 `f3p-miss-diagnosis.txt` 逐句列出）。
   - 舊 F3（補句是實作者照系統吃得下的格式寫）同版 46/50：差距主要來自欄位收集，不是名稱比對。

**目標形態**：先照現行精確／子字串查；查無時，程式取這位使用者看得到的物件或合約清單，以整句讀音前篩前 50 筆，交 AI 回傳清單內編號（enum 限定），程式驗證、補相近分數與同名、上限 5，一律列候選（沿用 A-2a／選對紀錄的候選清單與按鈕），使用者選定後回原流程；全部落空，程式以固定句說明找不到這個名稱並請重講（不回顯原話）。r4 另在寫入流程缺名稱時以整句跑同一套比對，落空則照現行追問（§1 第 2 點）。r5：名稱在本回合講出、其他欄位仍缺時，當回合先跑名稱查找（現行精確查找＋寬鬆），結果同出卡時：唯一 ⇒ 繼續追問其他欄位；多筆或寬鬆有候選 ⇒ 當回合列候選；選定後回原流程追問其餘欄位（§2.1 r5 表的「收到就驗」時點）。

## 3. 差距（第 3 步；查證指令在 repo 根目錄執行）

- G-0 盤點：`python3 ~/jgb-archive/arch-step3-20261018/f12/g0_count.py`（2026-10-22：577 檔、2,880 回合中 175 場、475 回合、406 種句）；改前基準 `python3 ~/jgb-archive/arch-step3-20261018/f12/ov_baseline.py`（OV 52/96 場、18 未解決；V3/V4 32/72 場、23 未選對出卡；M0 0/56 場）。
- G-1 物件查找是客戶端 token 子字串、只取第一頁 200 筆：`grep -n "def get_estate_status" -A60 rag-orchestrator/services/jgb_system_api.py | grep -n "per_page\|all(t in joined"`。
- G-2 合約查找交給 JGB 伺服器 `title LIKE %keyword%`：`grep -n "_viewer_contract_rows(api, role_id, user_id, keyword=ref)" rag-orchestrator/services/agent/tools/confirm.py`；寬鬆比對須由本端不帶 keyword 取清單（`MAX_PER_PAGE = 200`）。
- G-3 唯一性判準只認正名完全相同或整份恰好一列：`grep -n "def _resolve_estate(" -A15 rag-orchestrator/services/agent/tools/action.py`。
- G-4 查無即程式固定句結束、不說哪個名稱、不重問：`grep -n "PRE_LOOKUP_NOT_FOUND_TEXT =" rag-orchestrator/services/agent/runtime.py`；出口條件在違規標籤 `jgb2_not_found_exit` 附近（`grep -n '"jgb2_not_found_exit"' rag-orchestrator/services/agent/runtime.py`；那是標籤字串，不是函式）。
- G-6（r5）缺欄檢查排在名稱解析之前：封閉三動作 `grep -n "missing = missing_required_labels(action, payload)" rag-orchestrator/services/agent/tools/confirm.py`（在 `_prepare_closed_action` 內、`_resolve_estate_rows`／`_resolve_contract_rows` 之前）；修繕與延期 `grep -n "missing = missing_labels(action, payload)" rag-orchestrator/services/agent/tools/confirm.py`（在 `confirm_request` 內、`_prepare_repair_estate` 與帳單解析之前）。
- G-5 讀音工具已在依賴內：`grep -n "pypinyin\|jieba" rag-orchestrator/requirements.txt`。

## 4. 路徑與範圍（第 4 步；每項括號＝服務的目標或事件）

### 4.1 前篩與 AI 挑選（目標 1；§2.3 第 2～4 點；資安 S-3、S-4、S-7）

- 新模組 `rag-orchestrator/services/agent/name_match.py`：
  - `prefilter(sentence, rows, k=NAME_LENIENT_PRE_K)`：純函式。正規化（NFKC、小寫、去空白與標點與符號），中文字以 `pypinyin` 逐字轉無聲調拼音，**比對單位＝一個中文字的整個音節**（非字母），其他字元一字一單位（同實驗 `f12/exp/run_exp.py` `units`）；名稱核心＝正名去【…】［…］與括號內文字；分數＝名稱核心與整句的最長共同子序列長度（單位數）；≥2 才入選；依分數、覆蓋率排序取前 `NAME_LENIENT_PRE_K`＝50。
  - `ai_pick(...)`：一次模型呼叫，輸入＝整句＋前篩後清單。送模型的每列只有 `id`、`title` 兩鍵（白名單等值斷言），名稱逐列過 `sanitize_data_piece` 並以 `wrap_tool_data` 加 nonce 包住（比照 `write_candidates.data_piece_text`）。輸出 JSON schema 的 `ids` 陣列，enum＝清單內編號＋`none`——enum 只當提示，程式自己驗：
    - 解析一律用 `llm_output.final_segment`＋`iter_json_objects`，⛔ 沿用實驗的 `parse_json`；推理段未收尾 ⇒ 空。
    - 只認恰好一個、只有 `ids` 鍵的物件；多個不同物件 ⇒ 空。
    - `ids` 每項須為字串且精確等於送出清單內的編號；清單外、型別不對、重複者丟棄；`none` 與編號混用 ⇒ 空。
    - 解析失敗、逾時、例外 ⇒ 空（走 §4.4），不重試迴圈、⛔ fail-open。
  - `augment(picks, rows, scores)`：純函式。AI 所挑＋同名紀錄＋前篩分數不低於 AI 所挑最低分者，去重、上限 `NAME_LENIENT_CAP`＝5；AI 回空 ⇒ 空。
  - 常數 `NAME_LENIENT_PRE_K`、`NAME_LENIENT_CAP` 與提示詞全文在開發集定案（清單 F7），⛔ 用 F2～F4 量測輸入調。
- ⛔ 詞表、⛔ 依 fixture 名稱或題目分支。

### 4.2 接入查找（目標 1；G-1～G-4；資安 S-1、S-2、S-5、S-6、S-7、S-8）

- **生效條件**（呼叫當下讀）：`AGENT_NAME_LENIENT` 為 on **且** `write_candidates_effective_from_env()` 為真；不生效 ⇒ 0 次模型呼叫、0 次額外查詢，行為與現行逐字相同。
- **身分閘**：寬鬆入口自己檢查 `role_id`、`user_id` 皆非空、`resolved_audience()=="property_manager"`、過 `jgb2._identity_gate_ok`；缺任一 ⇒ 不發任何出向呼叫、不呼叫模型，走現行出口。每支出向呼叫都帶 `role_id` 與 `viewer_user_id=user_id`。
- 觸發點（三種，皆限**寫入流程**；現行查到 ≥1 筆的行為逐字不變；`candidates=False` 的路徑（`closed_action_missing_labels`）永遠不觸發）：
  - **(甲) 查無**：物件／合約名稱解析查無（帶查無標記）。
  - **(乙) 的閘門與 (甲) 同一組**（S-13、S-14）：(乙) 入口放在 `confirm.py`，與 `_name_lenient_result` 共用 `name_lenient_effective_from_env`、`_wc.allowed`、`_name_lenient_identity_ok` 與同一個 `wd.name_lenient`（`run_once`），⛔ 在 runtime 另寫出向呼叫；回合累積器的名稱指紋固定用 `name_fp("")`。接真 JGB 時 `WRITE_NOT_SUPPORTED_ACTIONS` 的動作一律不觸發 (乙)（同 `write_name_candidates`），不發清單查詢、不呼叫模型。
  - **(乙) 缺名稱**（r4，R3）：本回合合併完畢後，草稿動作的名稱欄（`WF.NAME_KEYS` 中該動作用的那一欄）仍空、程式即將追問且追問欄位含該名稱欄；本回合使用者是打字（非按鈕、非 `pick:`、非確認／修改／取消記號）；整句＝本回合使用者原話。有候選 ⇒ 照 §4.3 列候選（選定後回原流程，再追問其餘欄位）；回空 ⇒ **照現行追問、逐字不變**（使用者可能根本還沒講名稱，⛔ 回查不到固定句、⛔ 標已追問、⛔ 清任何欄位）。
  - **(丙) 名稱先查**（r5，原話 11；G-6）：適用修繕、建合約、手開帳單、延期繳費（延期只先定物件，帳單仍在欄位收齊後依期別解析；建物件不適用——它的名稱是新物件的名字）。條件全成立才做：本回合合併完畢後草稿名稱欄有值；該值是**本回合講的**（同 R1 判定：正規化後出現在本回合使用者原話；意圖或提議合併重寫同名不算）；本回合為打字（同 (乙) 的 `typed`）；沒有有效的程式選定（`valid_program_pick` 為空、候選集未選定）；缺欄清單非空（缺欄為空 ⇒ 照現行出卡路徑，本來就會解析名稱）；**只解析出卡時會用到的那一欄**（S-18）：延期限 `bill_id` 缺值時才先定物件（有 `bill_id` 出卡時不走物件解析）；手開帳單有 `contract_ref` 只解析 `contract_ref`，沒有才解析 `estate_name`。位置：封閉三動作在 `_prepare_closed_action` 的受眾檢查與 `check_closed_keys` **之後**、回缺欄之前；修繕與延期在 `confirm_request` 回缺欄之前，先過 `_name_lenient_identity_ok`（受眾、身分閘）才發任何查詢。動作：以出卡時同一組解析函式（`_resolve_estate_rows`／`_resolve_contract_rows`，帶 role 與 viewer；手開帳單講物件名稱照 §3f 1b 取該物件有效合約）只解析名稱那一段：
    - 唯一（含物件恰有一份有效合約）⇒ 回現行缺欄清單，回覆逐字同改前；⛔ 把編號寫進 payload、⛔ 存解析結果，出卡時照現行再解析一次；
    - 多筆 ⇒ 當回合回 A-2a 候選形狀（同出卡時多筆的候選：前言、按鈕、上限不變）；
    - 查無 ⇒ 走 (甲)（寬鬆比對；候選或 §4.4 找不到說明）；
    - 沒查成（API 錯誤）、手開帳單的物件無有效合約或有多份 ⇒ 回現行缺欄清單（照舊在出卡時處理；⛔ 當查無）。
    選定後沿用候選集 `picked`＋`program_pick` 與寬鬆的 `name_lenient_picked_title`，下一回合起程式追問其餘欄位；出卡時依選定編號精確查（A-2a 現行）。
    第二個接入點（主會話依資安審查附帶觀察納入）：runtime 的 B2 `_write_reply_state` 缺欄分支（程式先行沒發 `confirm.request` 的回合，如 `wd.model_confirm_ok`、剩餘時間低於 `WRITE_DRAFT_PROGRAM_MIN_REMAINING_S`、reissue gate 擋下）——現只試 `missing_name_lenient`；r5 在同一處先試 (丙)，入口放 `confirm.py`、沿用同一組閘門與每回合計數器，⛔ 在 runtime 另寫出向呼叫，`closed_action_missing_labels`（`candidates=False`）仍永遠不觸發。F3′ 中有缺欄回合走這條（如 F3P-41 第 3 回合 `write_reply_state:missing_fields`、無 `confirm.request`）。
- (甲)(乙)(丙) 共用閘門（`name_lenient_effective_from_env`、`_wc.allowed`、`_name_lenient_identity_ok`、`run_once`）；開關 off 或 A-2a 關 ⇒ 不做 (丙)，行為與現行逐字相同；接真 JGB 時 `WRITE_NOT_SUPPORTED_ACTIONS` 照舊在前面擋下，(丙) 不發查詢。
- (甲)(乙)(丙) 共用每回合最多 1 次寬鬆與 1 次模型呼叫的上限；(丙) 另限每回合 `_resolve_estate_rows`、`_resolve_contract_rows` 各最多 1 次（計數器放在每回合一份的 `NameLenientTurnCtx`；同回合多次 `confirm.request` 不重查，第二次起沿用第一次的結果型別），有效合約與 `_annotate_valid_contract` 的查詢另計、收案照實報次數（S-21）。
- 每回合寬鬆最多 1 次：結果暫存在回合累積器（鍵＝action、欄位、名稱指紋），畫面清單與候選集 `ids` 取自同一份；同步更新 `confirm.write_name_candidates`、`closed_action_missing_labels` 中「⛔ 呼叫任何 LLM」的 docstring。
- 寬鬆結果只能變成候選形狀；⛔ 寫進 payload 的 `estate_id`／`contract_id`、⛔ 回 `status="one"`。
- 物件清單：`get_estate_status` 查無時只回 sentinel、拿不到整頁，所以另發一次 `keyword=None`、帶 role 與 viewer 的呼叫（專用 helper，過身分閘），取第一頁最多 200 筆；共用 adapter 回傳形狀不變（回歸測試斷言 `jgb2.query.estates`、`repair_create` 輸出不變）。
- 合約清單：以 viewer 不帶 keyword 取第一頁；`get_contracts` 現不轉送 `per_page`、JGB 預設 50（`ContractApiController::DEFAULT_PER_PAGE`），本片為 `get_contracts` 加選用參數 `per_page`（預設不帶＝逐位不變），寬鬆 helper 傳 200。真 JGB 上建合約、手動帳單現在被 `WRITE_NOT_SUPPORTED_ACTIONS` 在解析前擋下，合約寬鬆路徑目前只在替身上跑得到。
- 總數超過 200 時候選前言加「只比對了前 200 筆」。
- **範圍的真機限制**：真 JGB 的 `GET /estates` 不吃 `viewer_user_id`，物件清單在真機上是**團隊範圍**，成員範圍要等 jgb2-req#24（`jgb2-api-requests.md`）；合約由 JGB 依 viewer 圈定。替身上的 viewer 測試結果 ⛔ 拿來宣稱真機的成員邊界（同現行精確查找，非本片引入）。
- 整句來源（(甲)）：草稿名稱欄值（正規化：NFKC、casefold、去空白與標點）出現在本回合使用者原話 ⇒ 本回合原話；否則（名稱在前一回合講）⇒ 本會話既有的使用者訊息（`_write_draft_user_texts`：`dialog` 的 user 端＋本句，值閘本來就用的來源）中**最近一則**含該名稱欄值者（r4，R4）；都沒有 ⇒ 草稿名稱欄值。意圖或提議合併把同一個名稱再寫進草稿（加進 `touched`）不算本回合講過（R1 修正）。⛔ 為此新存原句（S-15）：選出的整句只出現在 `ai_pick` 送模型的 messages；候選結果的 `query` 仍傳名稱欄值、(乙) 傳空字串；⛔ 寫進 `wd`、草稿、session、provenance、log 或 trace（清單 FR-10）。實作限制：`name_match.py` 凍結（F7 md5），`NameLenientTurn.sentence_for` 只回 `user_message` 或名稱值；R4 由 runtime／confirm 層把選出的舊句當該次比對的 `user_message` 傳入（只活在該次呼叫），不改 `name_match.py`；其 docstring 因此與 r4 用法不完全一致，收案 DSP 記明。做不到而必須改 `name_match.py` ⇒ 停（§8）。
- 候選列沿用 `write_candidates.minimize_row` 白名單，⛔ 新增欄位。

### 4.3 命中後（目標 1；Alexa、§2.2 第 2 點、DSP-091；資安 S-9）

- 有候選 ⇒ 一律列候選（含只有 1 筆），前言程式固定句「找不到完全相同的名稱，你是不是指下面這幾筆？」＋原有候選清單與 `pick:` 按鈕；選定後回原流程。AI 打字選定照 DSP-110（甲′）。
- (乙) 命中時使用者沒講過名稱，「找不到完全相同的名稱」語意不對，前言改用程式固定句「你要處理的是下面哪一筆？」（主會話選的字句，核可時一併確認）；其餘同上。
- 固定句 ⛔ 回顯使用者原話（沿用 `write_candidates` 固定句「只插筆數」不變式；「重列前言是否回顯原話」業主仍待裁，裁定前取最保守作法）。

### 4.4 真的找不到（目標 2；G-4）

- 候選為空 ⇒ 程式固定句「找不到這個名稱的物件／合約，請再確認名稱，或直接給編號。」（常數 `NAME_NOT_FOUND_TEXT`，⛔ 回顯原話），該欄標為已追問，清掉草稿裡查不到的名稱。
- 使用者下一句只補其他欄位 ⇒ 程式只重問名稱，⛔ 再回查不到固定句。
- 以上只適用 (甲)；(乙) 回空照現行追問（§4.2）。(乙) 在名稱已被標「查不到」後的重問回合仍可觸發（使用者重講名稱的那句）；回空照現行重問名稱。

### 4.5 開關、用量、紀錄（資安 S-7、S-10、S-12）

- `AGENT_NAME_LENIENT`：未設＝on；`off`＝與現行逐字相同（單元 off-run）；其他值啟動即 `ValueError`（同 `write_candidates_enabled_from_env`）。回退＝設 off 重建容器。Q-6 若裁不納入上線，正式機須設 off（寫進交接檔與部署說明；`docs/deployment-runbook.md` 是他窗未提交檔，本片不動，交業主轉達）。
- 用量：(甲) 查無的回合、(乙) 寫入流程缺名稱的回合（使用者只補欄位、名稱仍缺的每一回合都會觸發），各多 1 次清單查詢與至多 1 次模型呼叫（前篩為空則不呼叫模型；同回合 (甲)(乙) 合計 ≤1），每次約 1,100 prompt＋140 completion token（實驗值）；以東京 gpt-oss-120b US$0.18／0.73 每百萬 token 約 US$0.0003／次。不另設上限（S-17：每回合 ≤1、單則訊息 ≤2000 字），收案分 (甲)／(乙) 報次數。
- log 與 trace 只記型別與筆數（例：`name_lenient:shown:estate:3`、`name_lenient:none`），並記觸發型別 `name_lenient:trigger:notfound`／`name_lenient:trigger:missing`；r5 另記 (丙) 結果 `name_early:one`／`name_early:many`／`name_early:none`／`name_early:error`（只有結果型別）；⛔ 記句子、名稱、編號或模型原始輸出。
- r5 用量：(丙) 在「本回合講名稱且其他欄位仍缺」的回合多 1 次精確查找（與出卡時那次重複，唯一時不存結果）；查無才接 (甲) 的寬鬆（同上，每回合 ≤1 次模型呼叫）。收案分 (甲)／(乙)／(丙) 報次數。

### 4.6 文件與決策

- 收案時更新 `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` 名稱查找段、目標正本 §3 P5 與 §4、交接檔，記一條 DSP（含定案常數、宣稱範圍、上線範圍是否納入）。

### 4.7 相關但不在本次範圍

- 只用位置或特徵指稱、不含名稱片段（Q-1）；唯讀查詢（Q-2）；第 2 頁以後的紀錄（Q-3）；F7、F8（DSP-110 待裁）。
- 語意（embedding）比對：查無業界對應，且實驗方案已達 90% 以上；不做。
- R2「程式先行等待逾時」（`write_draft_program_first_wait_timeout` 後模型自呼 `jgb2.query.*` 查無 ⇒ 舊查不到出口，或模型直接回話）：F3 第 2 輪 1 並行仍出現（F3-28、44），屬既有時序問題、非名稱比對；列後續片（業主原話 7）。
- r5 診斷出的其他欄位問題（§2.3 第 7 點），皆非名稱比對、列後續片交業主排：(i) 日期值被值閘丟掉（`write_intent_value_not_in_user_words`：模型把「11/30」等轉成標準日期後對不回原話）；(ii) 延期講目標日不換算天數；(iii) 首句被答成問答或轉人、未進寫入流程（F3P-26、29、39、50；F3P-10、40 的首句）。這三項不修，使用者在自然講法下仍常寫不完；F12 只負責名稱找得到（§5 F3″ 量法）。
- (乙) 只拿本回合原話比對（F3P-10 本句無名稱卻列 5 筆、F3P-40 名稱在未進寫入流程的首句）：本片不改（改成看前幾句會增加誤列，且首句未進寫入流程屬 (iii)）；誤列由 F5 把關，F3P-10 型列為已知限制。

### 4.8 資安審查處置（security-reviewer 2026-10-22，唯讀；P0／P1 0 條）

| # | 發現 | 嚴重度 | 處置 | 落點 |
|---|---|---|---|---|
| S-1 | 真 JGB `GET /estates` 不吃 viewer，物件清單在真機是團隊範圍；viewer 宣稱只在替身成立 | P2 | FIX：計畫與規則改寫真機限制；F1、F4 的 viewer 證據標「僅替身」；報告與上線說明必寫 | §4.2；清單 FR-4、F1、F4 |
| S-2 | `role_id` 空時 `/estates` 不帶團隊過濾 | P2 | FIX：寬鬆入口自帶身分閘；出向必帶 role 與 viewer；負向測試；停點 | §4.2、§8；清單 F1 |
| S-3 | gpt-oss strict json_schema 不可靠；實驗解析器不可沿用 | P3 | FIX：`final_segment`＋`iter_json_objects`、只認單一 `ids` 物件、精確比對清單、失敗即空 | §4.1；清單 F1 |
| S-4 | 業者自填名稱的提示注入；名稱經 jgb2 markdown 呈現 | P3 | FIX（送模型部分）：sanitize＋nonce 包裝、F7 加注入名稱；DEFER（候選清單顯示名稱的 markdown）：A-2a 起既有、同團隊成員才改得到名稱、仍須使用者按選與確認，列為已知限制交業主 | §4.1；清單 F7 |
| S-5 | 實作可能把單筆寬鬆命中當唯一直接出卡 | P3 | FIX：生效條件綁 A-2a；結果只能是候選形狀；F1 測 A-2a 關時逐字相同 | §4.2；清單 F1 |
| S-6 | 放進現有解析函式會違反「不呼叫 LLM」契約、一回合多次呼叫、清單與候選集不一致 | P3 | FIX：每回合最多 1 次、同一份結果、`candidates=False` 不觸發、改 docstring | §4.2；清單 F1 |
| S-7 | 合約列含承租人電話與 Email；log 紀律；原句新落地；`per_page` 寫法不符 | P3 | FIX：送模型只 `id`、`title` 等值斷言＋正對照；log 只記型別與筆數；不新存原句；`get_contracts` 加選用 `per_page` | §4.1、§4.2、§4.5；清單 F1 |
| S-8 | `get_estate_status` 查無只回 sentinel，拿不到整頁 | P3 | FIX：另發 `keyword=None` 專用呼叫，共用 adapter 不變＋回歸測試 | §4.2；清單 F1 |
| S-9 | 回顯 `<講法>` 違反固定句只插筆數的不變式 | P3 | FIX（最保守）：不回顯；「重列前言是否回顯」業主待裁項沿用 | §4.3、§4.4；清單 FR-3 |
| S-10 | 開關預設 on | P3 | FIX：非法值 `ValueError`；Q-6 不納入則正式機設 off | §4.5；清單 F1 |
| S-11 | 「viewer 外從不出現」性質測試分辨力不足 | P3 | FIX：假 API 依 (role, viewer) 回列並記出向參數、假模型回他人編號；正對照 | 清單 F1 |
| S-12 | 成本放大 | P4 | 不另處置，收案回報用量 | §9 |

r4（security-reviewer 2026-10-22，唯讀；審計畫與驗收，(乙)／R4 尚未實作；P0／P1 0 條）：

| # | 發現 | 嚴重度 | 處置 | 落點 |
|---|---|---|---|---|
| S-13 | (乙) 是新入口（現行 `_name_lenient_result` 遇空名稱回 `None`）；身分閘、開關、A-2a 關、性質測試未延伸 | P2 | FIX：(乙) 與 (甲) 同一組閘門與 `run_once`；F1 補 (乙) 身分負向、off／A-2a 關 0 次、性質測試涵蓋 (乙) | §4.2；清單 F1 |
| S-14 | (乙) 未寫明遵守真 JGB `WRITE_NOT_SUPPORTED_ACTIONS` | P3 | FIX：真 JGB 上該三動作不觸發；F1 補 `use_mock=False` 0 次 | §4.2；清單 F1 |
| S-15 | R4「不新存」無驗收方法；整句可能流進 `query`／provenance／草稿 | P3 | FIX：整句只進 `ai_pick` messages、`query` 傳名稱值或空字串；F1 補 on／off 狀態比對與 log grep＋正對照 | §4.2；清單 F1 |
| S-16 | S-1 團隊範圍同樣適用 (乙)，且更常出現 | P4 | FIX（文字）：FR-4 讀法與 F5 viewer 證據標「僅替身」 | 清單 FR-4、F5 |
| S-17 | (乙) 成本放大；§4.5 舊句只寫查無 | P4 | 上限 DEFER（每回合 ≤1、訊息 ≤2000 字）；文字 FIX；用量分 (甲)／(乙) 報、加觸發型別標記 | §4.5、§9 |

審查查無發現（附反證）：回空的存在性洩漏、R4 跨 session／跨使用者混入、舊句送模型、R1 子字串判定被構造輸入左右（最壞只降低找得到率）。非資安順提：(乙) 前言語意 ⇒ §4.3 改用 (乙) 專用固定句。

r5（security-reviewer 2026-10-22，唯讀；審 (丙) 計畫與清單；P0／P1／P2 0 條）：

| # | 發現 | 嚴重度 | 處置 | 落點 |
|---|---|---|---|---|
| S-18 | (丙) 解析的名稱欄可能與出卡時用的不同（延期已有 `bill_id`、手開帳單已有 `contract_ref` 又講物件），使用者的選定被靜默忽略；卡片仍顯示實際那筆、須按確認 | P3 | FIX：只解析出卡時會用到的那一欄；F1 補兩個負向案例 | §4.2 (丙)；清單 F1 |
| S-19 | F1「不落地」只比鍵，偵測不到既有鍵的值被改寫；「payload 無編號」觀察點不明 | P3 | FIX：唯一案例 `agent_state`（含 `estate_carry`、`write_candidates`、`write_draft`）與 `form_sessions.collected_data` 序列化與 off-run 逐位相同；正對照加「系統正名寫回草稿名稱欄」 | 清單 F1 |
| S-20 | log 正對照寫「或」，(丙) 標記壞了也能通過 | P4 | FIX：(丙) 案例必須搜得到 `name_early:*`（唯一、多筆、錯誤各 ≥1） | 清單 F1 |
| S-21 | 「每回合名稱查找 ≤1」未定義；`run_once` 只管寬鬆；同回合多次 `confirm.request` 會重查 | P4 | FIX：定義為兩支解析函式各 ≤1、計數器在 `NameLenientTurnCtx`；有效合約與 annotate 查詢另計照實報 | §4.2、§4.5；清單 F1 |

審查查無發現（附查證）：身分閘——`_name_lenient_identity_ok` 比出卡時的 `_prepare_repair_estate`（只看身分非空）與 `_pr_resolve_bill` 都嚴；欄位不全時解析函式只吃名稱字串、不讀模型自帶編號；`WRITE_NOT_SUPPORTED_ACTIONS` 的 return 排在缺欄檢查與 `_prepare_closed_action` 之前；多筆候選與出卡時同一支帶 role、viewer 的查詢，`program_pick` 唯一設定點在 runtime；揭露句：量測腳本 `settled()` 遇 `confirm_pending` 即停、從不送 `confirm_submit:`，走不到寫入。

待查（不評嚴重度）：Q-e 候選集提早出現後，只補欄位的回合 AI 打字選定被諮詢的次數變多，可能在使用者沒選時成立選定（卡片仍顯示、要按確認）——確認方法：F3″、F5 改後逐回合統計 `write_candidate_pick:typed`，挑該回合原話未指稱任何候選者，>0 即成立（清單 F3″、F5 加此報告項）。Q-f 真 JGB 上 (丙) 多筆候選屬團隊範圍（S-1 既有限制、出現次數變多）——收案報告上線說明寫到 (丙)。

非資安附帶觀察：B2 `_write_reply_state` 缺欄分支不經 `confirm_request`，(丙) 覆蓋有缺口 ⇒ 主會話納入第二個接入點（§4.2 (丙)）。

待查（不評嚴重度）：Q-a jgb2 站內幫手實際用的呈現元件與 master／preview 設定；Q-b master／preview 的 `EstateApiController@index` 是否已支援 viewer；Q-d 真機合約 `title` 是否含承租人姓名（抽樣需另核可）。Q-c（前篩單位）已在 §4.1 寫明＝音節。

## 5. 偏離與取捨

- 前篩演算法、`PRE_K`、`CAP`、補齊規則是第一原理與實驗定案，查無業界演算法規定（Apple 明言交給 app）。
- 只比對第一頁 200 筆：現行查物件本來就只取第一頁；200 筆以上的團隊是否存在未知（Q-3）；實驗只量到 200 筆（業主裁示量體）。
- 量測量體：F2 每題改後 1 次（改前用既有紀錄，第 1 次挑題、第 2 次當基準，不另跑改前），F3′／F5 每句＝首句＋該句專屬補句 1～2 句（補句與首句由同一位 fresh 代理寫、跑前一起凍結；腳本照序送出，首句已出候選、卡、查不到句或非 clarifying 即停），不加模擬客人自由對話；F4 沿用 r3 凍結首句、補句改由同一 fresh 代理逐句撰寫並凍結；原 F3 沿用 r3 的 4 句固定補句（實作者寫，只當中間證據、不撐任何宣稱），M0 與 OV 其餘 20 題依 Q-4 處理——依業主「後續的測試也注意量體」；穩定度另由 F7 開發集重跑量。
- 量測條件限制：改後模擬客人用 `pick-right/run/make_briefs.py` 產 ova 同一版派工句、同一預設模型 Sonnet；改前紀錄 ova 有 A0／A1 兩位中途換成 Opus 5.5（`pick-right/report-pick.md` 量測效度節，業主當時裁「不變」），哪幾場不可考，列為限制。
- 現況比較好做的部分照實寫：沿用 A-2a 候選清單與按鈕，是因為已有且符合「讓使用者選」，不是因為業界如此。
- r5 量測（F3″）：新 fresh 代理寫新輸入（目標不與 F3、F3′ 的 20 筆重複；有效合約共 10 份、未用 4 份，合約目標 ≥3 可行），送法同 F3′。凍結補句送完仍未出候選、卡或找不到句時，兩容器都再送 1 句**揭露句**：實作者寫的固定句，依動作給齊其餘必填欄位（系統吃得下的格式）、⛔ 含任何名稱，只用來讓流程走到確認卡、看出系統定的是哪一筆——(丙) 唯一命中時回覆仍是追問其他欄位，不走到卡就無法判它定的是不是目標；而其他欄位收不進來是 §4.7 的後續片問題。判分分兩欄：「未經揭露句找到」（使用者在自然講法下的實際體驗，只報）與「含揭露句找到」（名稱找得到，F12 宣稱、85% 門檻）。揭露句只當觀察手段，⛔ 撐 R4 形狀、FR-9 或 FR-11 的使用者層宣稱。FR-11（名稱先查）另以「講名稱那回合就看到候選」判：分母取改前容器在講名稱那回合回的是缺欄追問的句子（由 `f12-before` 紀錄定，與 r5 機制無關），剔除改後 (丙) 判唯一者（回覆與改前相同，使用者看不出差別）與改後在講名稱那回合前已停者，逐句列出；分子＝改後容器同一回合列出含目標的候選。揭露句只在講名稱那回合之後才送，r4 程式在缺欄回合不查名稱，這一欄分得出 (丙) 有沒有效（plan-verifier 第 1 次 B-1、第 2 次 Blocker 1）。(丙) 判唯一的句子另報為機制項（其後確認卡是否為目標，可經揭露句）。
- r5 量體：改後容器跑 F3″（約 40 句）、F3′（50 句，已用於診斷，只報，用來看診斷出的機制有沒有修到）、F5（12 句）、F4（12 句）；改前容器只跑 F3″（改前程式未變，F3′／F5／F4 沿用 r4 改前紀錄）。原 F3 不再重跑（只報性質，錯筆卡防護由 F3″、F3′ 涵蓋）。
- 資料組只有 1 組：`assistant_demo_vendor4.json`；另一份 `demo_vendor4.json` 是同團隊同 83 筆物件（物件編號交集 83），不是獨立資料組；F4 他團隊組用 role 30999。

## 6. 待業主裁（核可時一併裁）

- **B1**：原話 1「但你是把測試文題寫得很正 那口語化的實際問題要怎麼抽」的「抽」是哪個意思？(a) 系統怎麼從口語抽出名稱（本計畫採此讀法，業主裁定前暫採）；(b) 測試輸入要從實際使用者的問題抽樣。選 (b)：F3 輸入來源改成正式站真實對話抽樣（經 `jgb-prod-readonly`、依其遮蔽規則，需另核可），先查有多少可用句再定；兩者都要也可以。
- Q-1：只用位置或特徵、不含名稱片段的講法是否納入？建議不含（開發集 10/190 句），列下一片。
- Q-2：唯讀查詢要不要一起用？建議本片只做寫入，唯讀查詢下一片接同一模組。
- Q-3：是否核可以 `jgb-prod-readonly` 查正式站各團隊物件數、合約數分布（只取筆數彙總）？用來決定要不要處理第 2 頁以後。不核可則照 §5。
- Q-4：上位驗收要求既有回歸題組不退步。M0 題組 56 場在改前量測中 0 場出現查不到（`ov_baseline.py`，正對照：同指令在 OV 找到 52 場）；OV 48 題中第 1 次紀錄沒出現查不到的 20 題，本片觸發條件同樣多半不會發生。建議本片不重跑 M0 與 OV 其餘 20 題（省 56＋20 場以上），以單元 off-run（現行查找有結果時逐字不變）＋F2 涵蓋觸發場次；或照上位方式重跑（M0 56 場、OV 48 題）。
- Q-5：分工讀法確認——AI 把使用者講法對到清單內編號（產生候選）屬「理解」，何時呼叫、驗證、補齊、列候選、選定、出卡皆由程式；這是否符合 DSP-091？（同型先例：DSP-110 甲′。）
- Q-6：F12 收案後是否納入上線範圍（DSP-107 清單）？建議納入。
- r4-1：「沒講名稱不亂列」（FR-9）量化為 F5「改後列出候選的句數 − 改前列出候選的句數 ≤ ⌈0.2 × F5 句數⌉」（10 句時 ≤2）——主會話選的讀法；可改為 0 增加（較嚴，可能逼 (乙) 收窄）或不設門檻只報。建議照此。
- r4-4：原話 7「F3/F4 重跑」照做，另放寬為：宣稱依據移到新輸入 F3′（原 F3 已用於 r3 診斷）、新增 F5（FR-9 防護）、F4 補句改由 fresh 代理撰寫；量體兩容器合計約多 100 段對話（清單 FR-8 讀法）。替代：只重跑 F3／F4、以原 F3 當依據（已被診斷污染，收案宣稱力弱）。建議照放寬。
- r4-3：(乙) 寬鬆也落空時（含使用者講了名稱但 AI 沒抽進草稿），照現行追問名稱欄、不出「找不到這個名稱」說明（§1 第 2 點、§4.4）。替代：出一句不指控的提示（如「沒對到你說的物件，請給名稱或編號」），但對沒講名稱的人會語意不對。建議照現行追問（不變差）。
- r4-2：(乙) 命中前言「你要處理的是下面哪一筆？」（§4.3）——主會話選的字句。建議照此。
- r5-1：括號內文字要不要納入比對（F3P-04「國泰那間」對「台北文山-離塵一房(國泰)」）？要改 `name_match.py` 的名稱核心規則 ⇒ F7 md5 變、F7 開發集要重做（190 句 × 1 次，模型費約 US$0.06），依 §8 交業主。fixture 83 筆物件中 23 筆名稱有括號，括號內多是租客型態或狀態（「個人租客」「法人租客」「空房」），納入後「空房那間」這類講法會列出不相干候選。**建議本片不做**，列下一片另設計（例如只納入人名或公司名型的括號內容）並量誤列；替代：本片就做並重做 F7。
- r5-2：F3″ 的揭露句（§5）——實作者寫、兩容器同送、不含名稱，宣稱 85% 判在「含揭露句找到」，「未經揭露句找到」只報。建議照此；替代：只用凍結補句、不送揭露句（唯一命中的句子判不出是否為目標，會被算成沒找到或要另判）。
- r5-3：(丙) 多筆時把 A-2a 候選提前到講名稱的回合，列出的候選與選定結果不變、時點改變（清單 FR-4 放寬）。原話 11 回應的主會話說法已含「名稱查無或有多筆時當回合列候選」，此項請一併確認。建議照此。
- r5-4：§4.7 後續片（日期值閘、延期天數換算、首句未進寫入流程）在 F12 收案後另開，建議先做日期與天數兩項（F3′ 中 13 句以上被擋）；本片不動。
- r5-5：原話 11 回應的「每一欄收到就驗」，本片是否只做名稱？等到出卡才對系統資料查的欄位有兩個：物件／合約名稱（本片 (丙)），以及延期繳費的期別到帳單的對應（`_period_gate_value` 只比年月，帳單在欄位收齊後才依期別解析）。**建議本片只做名稱，期別到帳單留後續片**：F3′ 23 句未中沒有一句卡在期別對不到帳單（延期未中都卡在「延後天數」，§2.3 第 7 點），且帳單解析要物件先定，(丙) 做完後再做較單純。替代：本片一併做——物件已定（唯一或已選定）且期別已收到、其他欄位仍缺時，先依期別解析帳單，對不到或多筆當回合處理（範圍、資安審查、F1 與量測都要再擴）。裁定前清單 FR-11 標「暫採」。

## 7. 執行順序

security-reviewer（唯讀，處置寫入 §4.8）→ 收尾 plan-verifier → 業主核可（含 B1、Q-1～Q-6）→ security-executor 實作（模組、接入、開關、單元）→ F7 開發集定案並凍結常數與 md5 → F3／F4 輸入由 fresh 代理產生並凍結 → 主會話重建常駐容器、`make audit`、mock 檢查 → 量測 F2～F6 → 報告 → fresh verifier（F8）。改前容器：以現行常駐映像打標籤起 `f12-before`（18106）。

r4：security-reviewer（唯讀，處置寫入 §4.8 r4 列）→ plan-verifier → 業主核可 → security-executor 實作 (乙) 與 R4 整句來源＋單元（`name_match.py` ⛔ 動，F7 定案不變）→ 新輸入 F3′／F5 由 fresh 代理產生並凍結 → 重建常駐容器、`make audit`、mock 檢查 → F3′、F3（原凍結輸入，只報）、F4、F5 兩容器實打 → F2、F6 → 報告 → fresh verifier（F8）。

r5：security-reviewer（唯讀，處置寫入 §4.8 r5 表）→ plan-verifier → 業主核可（含 r5-1～r5-5）→ security-executor 實作 (丙)＋單元（r5-1 不做則 `name_match.py` ⛔ 動）→ 新輸入 F3″ 由 fresh 代理產生並凍結（揭露句由主會話寫、同時凍結）→ 重建常駐容器、`make audit`、mock 檢查 → 改後 F3″、F3′（只報）、F5、F4；改前 F3″ → F2、F6、F0 → 報告 → fresh verifier（F8）。

## 8. 停點

- 任一量測出現錯筆寫入（寫進使用者沒選的那筆）⇒ 停，交業主。
- 現行查找有結果時的行為有任何改變（off-run 或回歸）⇒ 停，修到逐字相同再繼續。r5 例外：(丙) 多筆時候選提前到講名稱的回合出現不算改變（清單 FR-4 r5 讀法、§6 r5-3）；候選集合、前言、按鈕與選定結果仍須與出卡時多筆的候選逐字相同。
- F7 開發集未達門檻 ⇒ 停，交業主（⛔ 拿量測輸入調）。
- 任何寬鬆路徑的出向呼叫沒帶 `role_id` 或 `viewer_user_id` ⇒ 停（比照選對紀錄片 S-F1）。
- r4：實作 R4 或 (乙) 必須改 `name_match.py`（F7 md5 會變）⇒ 停，交業主（重做 F7 或改設計）。
- r4：清單任一項（F0～F7，含 F3′ 未達 85%、F3′／F3 錯筆卡或寬鬆直接出卡、F5 超過門檻、F4 任一組未過、F2 未達預期、F6 回歸、F1 新測試失敗、F0 受測物不符）通過條件未達 ⇒ 停，照實交業主（附逐句結果與 trace 型別標記彙總）。⛔ 先拿該批輸入逐句診斷再改程式；要診斷須業主同意，且一經用於診斷，該批輸入即不得再撐宣稱，須另由 fresh 代理寫新輸入並凍結（同 §10 R5）。
- r5：上一條一體適用於 F3″（兩個通過條件：FR-11「講名稱那回合就有結果」≥85%、「含揭露句找到」≥85%，任一未達即停）；(丙) 唯一命中時回覆與改前有任何不同（單元 off-run 對照）⇒ 停，修到逐字相同；(丙) 的任何查詢沒帶 `role_id` 或 `viewer_user_id`、或在身分閘前發出 ⇒ 停。

## 9. 用量

收案時回報子代理 token 加總與模型費用；⛔ token 上限當停點。

## 10. 審查處置

r2 plan-verifier（第 2 次 REVISE，依全域規則不再自動重送，主會話逐條處置後開一次收尾審查）：

| # | 審查意見 | 處置 | 落點 |
|---|---|---|---|
| R2-1 | 資安敏感（合約改不帶 keyword 取整頁、業者自填名稱送模型、候選由模型輸出決定、viewer 範圍是授權邊界），未經 security-reviewer，實作者寫一般 executor | FIX | §4.8、§7（security-executor） |
| R2-2 | F2 挑題與基準用同一批紀錄、分母不同、模擬客人條件未規定 | FIX：第 1 次挑題、第 2 次當基準；一律同分母比例；派工句與模型寫明，Opus 換場列限制 | §1、§5；清單 F2 |
| R2-3 | 開發集與 F2 的 V3/V4 題重疊 | FIX：V3/V4 列開發集內、只報；宣稱只靠 OV 題與 F3 | §1；清單 F2 |
| R2-4 | `ov_baseline.py` 只認舊句 | FIX：重算兩句都計，點名判分工具 | 清單 F2 |
| R2-5 | F6、F9 未引規則 ID | FIX | 清單 F6、F9 |
| R2-6 | OV 其餘題去向未交裁 | FIX：併入 Q-4 | §6 |
| R2-7 | 審查 brief 缺原話 2、3 | FIX：收尾審查 brief 附逐字原話與上下文 | 收尾審查 brief |

r3 收尾 plan-verifier（REVISE，2 條 P2、審查員標 substantive；依全域規則不再自動送審，修正後交業主裁，**已修、未再審**）：

| # | 審查意見 | 處置 | 落點 |
|---|---|---|---|
| C-1 | F4 要求回覆「含使用者講法」，與 FR-3／§4.4 不回顯（S-9）矛盾；§1、§2.3 也是回顯寫法 | FIX：F4 改為含 `NAME_NOT_FOUND_TEXT` 且不含原話；§1、§2.3 改不回顯 | 清單 F4；§1、§2.3 |
| C-2 | S-10 非法值 `ValueError` 無驗收點 | FIX：F1 加開關值斷言 | 清單 F1；§4.8 S-10 |

r4 量測後處置（主會話以 trace、`form_sessions` 草稿、容器內隔離重現查證；`f12/run/f3f4-r1-record.md`）：

| # | 實打發現 | 處置 | 落點 |
|---|---|---|---|
| R1 | 意圖合併把前一回合的名稱再寫進 `touched` ⇒ 整句誤用本回合補句（14/24 句） | FIX（核可範圍內，實作偏離 §4.2）：名稱值出現在本句才算本回合講；已實作、單元 98/98、第 2 輪 10/14 轉為找到 | §4.2 |
| R2 | 程式先行等待逾時 ⇒ 模型自查舊出口 | DEFER：既有時序、非名稱比對；後續片 | §4.7 |
| R3 | 名稱沒進草稿 ⇒ 從未查名稱 | FIX（業主原話 7 擴範圍）：(乙) 缺名稱觸發 | §4.2、§4.4；清單 F1、F3′、F5 |
| R4 | 前一回合講的名稱以草稿值比對落空 | FIX（業主原話 7）：整句取最近一則含名稱值的既有使用者訊息 | §4.2；清單 F1、F3′ |
| R5 | F3 凍結輸入已被主會話用於診斷 | FIX：宣稱依據改為新輸入 F3′（fresh 代理、跑前凍結）；原 F3 改只報 | 清單廣度表、F3、F3′ |

r4 plan-verifier（第 1 次）REVISE 處置：

| # | 問題 | 處置 | 落點 |
|---|---|---|---|
| B-1 | (乙) 回空不出查不到句，與 FR-3、§1 第 2 點衝突；F4 未依 r4 分組 | FIX：FR-3 與 §1 限 (甲)，收窄寫在 FR-3 旁並列 §6 r4-3；F4 三組各給通過條件，定義「只重問名稱」＝程式追問的欄位只有名稱欄 | §1、§6；清單 FR-3、F4 |
| B-2 | F3′／F5 多輪部分用實作者寫的 4 句固定補句 | FIX：每句專屬補句由同一 fresh 代理撰寫、跑前凍結；廣度表分列首句與補句；原 F3／F4 的固定補句只當中間證據、⛔ 撐 R4 或 FR-9 | §5；清單廣度表、F3′、F4、F5 |
| B-3 | 驗收未過無停點，輸入可能再被診斷污染 | FIX：§8 加結果停點與輸入使用規則 | §8 |
| B-4 | R4 根因寫成定論 | FIX：§2.3 第 6 點改標推論、未證實 | §2.3 |
| B-5 | §1 宣稱依據仍寫 F3；r4 改動清單不全 | FIX | §1、開頭 r4 依據段 |
| B-6 | F5 門檻超過 10 句無法判 | FIX：改為 ⌈0.2 × 句數⌉ | §6 r4-1；清單 F5 |

r4 plan-verifier（第 2 次，fresh）REVISE 處置——已達兩次自動 REVISE，主會話逐條處置後記 **r4 就緒 epoch 2**，只開一次收尾 fresh 審查：

| # | 問題 | 處置 | 落點 |
|---|---|---|---|
| B-1 | 原話 7「（不新存）」沒有規則 | FIX：新增 FR-10，F1 的 S-15 項改引 FR-10 | 清單 FR-10、F1 |
| B-2 | 「F3/F4 重跑」被放寬（F3′、F5、F3 降只報）未標明、未交業主 | FIX：FR-8 讀法註明放寬與量體；§6 r4-4 | 清單 FR-8；§6 |
| B-3 | F4「只重問名稱」靠實作者寫的固定補句 | FIX：F4 補句改由 F3′ 代理逐句撰寫、跑前凍結 | §5；清單廣度表 F4、F4 |
| B-4 | F5 未列說法類別 | FIX：口語、一句多件事、只講一半、分多句、順序對調各 ≥1；簡稱、錯字不適用並附理由 | 清單廣度表 F5 |
| 待查 | `name_match.py` 凍結下 R4 能否實作 | FIX：§4.2 寫明由 runtime／confirm 傳入舊句當 `user_message`；做不到即停 | §4.2、§8 |

r4 收尾 plan-verifier（epoch 2）REVISE（4 條 substantive）⇒ 依規則暫停交業主；業主就 B-1 裁「當前有效合約 哪個物件就哪個吧」（清單原話 8），主會話處置如下，**未再審**：

| # | 問題 | 處置 | 落點 |
|---|---|---|---|
| B-1 | 合約目標「經所屬物件」算找到，放寬 FR-1 未標、可左右 85% | FIX（業主裁）：只在該合約是所屬物件目前的有效合約時算找到（與程式 §3f 1b 一致）；F3′ 合約目標限有效合約。依此重算第 2 輪：F3-38、F3-40 目標 81821 為歷史合約（fixture `is_history=1`）、物件 34886 無有效合約 ⇒ 不算；F3-45（85516，物件 67603 的有效合約）仍算 ⇒ 39/50（78%） | 清單原話 8、FR-1、廣度表 F3′、F3′ |
| B-2 | 結果停點未涵蓋全部清單項 | FIX：§8 改為任一清單項（F0～F7）未達即停，輸入使用規則一體適用 | §8 |
| B-3 | log／trace 不含檢查無正對照 | FIX：同一捕捉內必須搜得到 `name_lenient:trigger:*` 標記；加「故意記進 log」正對照 | 清單 F1 |
| B-4 | F4 (乙) 回空要求跨容器逐字相同，判不了且與 §4.4 衝突 | FIX：改依改後容器自己的回覆與 trace 判；(甲) 之後照「只重問名稱」 | 清單 F4 |

r4 量測後處置（F3′ 改後 27/50 依 §8 停；業主原話 10 准許診斷；`f12/run/f3p-miss-diagnosis.txt`）：

| # | 實打發現 | 處置 | 落點 |
|---|---|---|---|
| R6 | 缺欄檢查排在名稱解析前，其他欄位收不進來 ⇒ 名稱從沒被查（16/23） | FIX（業主原話 11）：(丙) 名稱先查 | §1、§2.1 r5 表、§4.2 (丙)；清單 FR-11、F1、F3″ |
| R7 | 日期值閘丟值、延期天數不換算、首句未進寫入流程（含 4 句問答／轉人） | DEFER：非名稱比對，後續片交業主排 | §4.7；§6 r5-4 |
| R8 | 括號內文字被名稱核心拿掉（F3P-04） | 交業主：要改 `name_match.py`、重做 F7 | §6 r5-1 |
| R9 | (乙) 只看本句，本句無名稱仍列 5 筆（F3P-10） | DEFER：已知限制，F5 把關 | §4.7 |
| R10 | F3′ 已用於診斷 | FIX：宣稱依據改 F3″（fresh 代理、跑前凍結）；F3′ 只報 | §1、§5；清單廣度表、F3″ |

r5 plan-verifier（第 1 次）REVISE 處置：

| # | 問題 | 處置 | 落點 |
|---|---|---|---|
| B-1 | 85% 判在含揭露句，r4 程式配揭露句也能過，分不出 (丙) 有沒有效 | FIX：F3″ 加 FR-11 通過條件「講名稱那回合就有結果」，分母由改前紀錄定 | §5；清單 F3″、廣度表 |
| B-2 | 「每一欄收到就驗」收窄成只做名稱未標明 | FIX：附程式證據——其他欄位在併入草稿時已過值閘（`runtime.py` 的 `_write_draft_gate_value`、`_period_gate_value`，不過記 `write_intent_value_not_in_user_words`／`write_intent_value_out_of_domain`），名稱是唯一要等出卡才查的欄位；值閘過嚴（日期）屬 §6 r5-4；讀法寫在 FR-11 旁 | 清單 FR-11 |
| B-3 | §8 停點與 FR-4 放寬衝突 | FIX：§8 加 r5 例外 | §8 |
| B-4 | F3″ 85% 沒寫分母 | FIX：分母＝有名稱片段的講法，判分腳本與剔除方式寫明 | 清單 F3″ |
| B-5 | Lex 列後半句原文不支持 | FIX：改寫並標明原文未寫 | §2.1 r5 表 |
| 待查 | 診斷計數 17＋4＋3＝24 | FIX：F3P-40 只計在寬鬆未中項，改 16 句、逐句列號 | §1、§2.3 第 7 點、R6 |
| 待查 | Q-f 未落到報告項 | FIX：清單 F9 加上線說明寫到 (丙) 團隊範圍 | 清單 F9 |

r5 plan-verifier（第 2 次，fresh）REVISE 處置——已達兩次自動 REVISE，主會話逐條處置後記 **r5 就緒 epoch 2**，只開一次收尾 fresh 審查：

| # | 問題 | 處置 | 落點 |
|---|---|---|---|
| Blocker 1 | FR-11 分子含「(丙) 判唯一」——回覆與改前相同、使用者看不出；靠揭露句後的卡又與 §5 衝突；改後在 `name_turn` 前已停無判法 | FIX：分子只算同一回合列出含目標的候選；(丙) 判唯一與 `name_turn` 前已停者自分母剔除並逐句列出，唯一者另報為機制項；§5 改成一致說法 | §5；清單 F3″ |
| Blocker 2 | 「名稱是唯一等到出卡才查的欄位」不實（期別到帳單也是）；「每一欄收到就驗」讀法未交業主 | FIX：改正事實；§6 新增 r5-5，FR-11 標暫採；清單第五節列入 | §6 r5-5；清單 FR-11、第五節 |

r5 收尾 fresh plan-verifier（epoch 2）：**READY**（2026-10-22）。next_gate: user_approval（含 §6 r5-1～r5-5 業主裁示）。

## 11. r6：選定後可改選（2026-10-24 業主核可，r6 清單原話 16；r6-1～r6-7 全照建議，見清單第五節；資安審查與 5 次 plan-verifier 已做，第 5 次修法未再審）

r6 依據：r5 實作後 F8 fresh verifier 三次 REFUTED（`~/jgb-archive/arch-step3-20261018/f12/r5/report-r5.md`「F8 第 1 次」「第 2 次」「第 3 次 REFUTED」三節）。第 1 次 P2-1（選定後補欄位那回合又列一次候選）⇒ 修正 v1 `_name_lenient_keep_picked`；第 2 次 P2-A（v1 讓選定後另一回合改口無效）⇒ 修正 v2 `_name_said_before_pick_only`；第 3 次 P2-甲（v1、v2 共有：選定 A 後另一回合以編號改口，補欄位那回合模型填回舊講法、被擋下 ⇒ 卡是已撤回的 A；情境 C03 2/2、C14 1/1）、P2-乙（打字選定沒有按鈕標記 ⇒ 補欄位回合重跑寬鬆比對，候選可能不含已選那筆；C10b 2/2）。三輪都錯在同一處：程式以「名稱有沒有出現在某段原話」推測客人是不是改口。業主 2026-10-24 裁「選定後仍可改選」（r6 清單原話 15）。復原輪數已用 3／5（全域「Recovery and authority」）。

規則與驗收清單：r6 `acceptance-name-lenient-f12-r6-20261024.md`（同目錄；業主核可後凍結）。r5 清單為紀錄，FR-1～FR-11 與 F0～F9 由 r6 清單引用沿用。服務原則：P5（候選選擇、更正）、P0（DSP-091：「已選定的那筆紀錄」由程式決定，理解由 AI）。

終點指標：§1 的「查不到出口比例」（OV 28 題現值 21/28、預期 ≤38%）r6 預期變化＝0——r6 只改選定之後到出卡前，不動名稱查找與列候選。r6 是本片收案的前提：F8 需 CONFIRMED，第 3 位 verifier 以 P2-甲、P2-乙 推翻。r6 自己的指標＝選定後改口時「卡上是已撤回那筆」的場數，現值來自第 3 位 verifier 紀錄（`f12/r5/f8c/runs`）：C03 2/2、C14 1/1；打字選定後補欄位重列 C10b 2/2；預期都是 0（F10 量）。

### 11.1 目標（第 1 步）

1. 使用者選定候選（按鈕或打字）之後、確認卡出來之前改口要另一筆（講編號、第幾個、特徵、簡短代稱），系統改成那一筆，之後的卡就是那一筆；⛔ 卡是已撤回的那筆（原話 15「改口＝撤回選定」；P2-甲、P3-丁）。
2. 改口講的是候選清單以外的名稱 ⇒ 依新講法重查（現行精確查找→寬鬆），舊選定不帶過去（原話 15「講到候選集外的名稱就依新講法重查」；情境 C16）。
3. 沒改口、只補其他欄位 ⇒ 不再列候選，卡用原選定那筆；按鈕選定與打字選定一樣（原話 15「打字選定也記標記」；P2-1、P2-乙）。
4. 程式不再以「原話出現位置」推測客人有沒有改口（原話 15「拿掉靠猜的 keep_picked」）。

### 11.2 目標形態（第 2 步；渲染頁 `~/jgb-archive/arch-step3-20261018/f12/sources/r6/`，各檔首行為網址）

| 面向 | 業界原文（逐字） | 出處檔 |
|---|---|---|
| 理解層每回合都可輸出「改值」指令，含已填過的欄位 | Rasa LLM 指令產生器提示詞：「`set slot slot_name slot_value`: Set a slot for the active flow. For example, `set slot transfer_money_recipient Freddy`. Can be used to correct and change previously set values.」 | `rasa-command-generators.txt` |
| 「改值」是理解層的一種輸出 | Rasa 對話理解指令表：「correct slot」「The user has provided an updated value for a slot」 | `rasa-dialogue-understanding.txt` |
| 更正交給對話修補模式；預設直接改並告知 | Rasa：「pattern_correction for corrections.」；預設設定（「Reference: Default Pattern Configuration」節）`pattern_correction` 的步驟為 `action: action_correct_flow_slot` 後接 `action: utter_corrected_previous_input`，其回應「Ok, I am updating {{ context.corrected_slots.keys()|join(', ') }} to {{ context.new_slot_values | join(', ') }} respectively.」 | `rasa-patterns.txt` |
| 可改成先確認再改 | Rasa：「You can change the default implementation for a correction and require a confirmation from the user before a slot is updated」；範例「Oh wait!! I meant to say to John, not Joe!」→「Do you want to update the recipient to John? (Yes/No)」 | `rasa-patterns.txt` |

本輪只查 Rasa 一家（Lex、Dialogflow CX、Copilot Studio 未查）；⛔ 寫成「業界都」。Rasa 原文講槽位值，套到「候選清單的哪一筆」屬推論：選定那一筆＝把「紀錄」這一欄設成某個編號，改口＝對同一欄再下一次 set slot。

**目標形態**：選定之後、出卡之前，每個打字回合的意圖呼叫照樣回「使用者這句指的是清單哪一筆」（`pick_id`，enum＝候選集內編號＋`none`），等同 Rasa 的 set slot／correct slot；程式只收候選集內編號——與現選定不同 ⇒ 改選；相同或 `none` ⇒ 選定不動。本回合講出候選集外的名稱（`pick_id` 為 `none`、名稱值出自本回合原話）⇒ 依新名稱重查。改選後不先問「要改成 X 嗎？」，直接改（同 Rasa 預設）；確認卡本身就是送出前的確認步，卡上顯示新那筆、仍須按確認（第一原理：多問一次等於同一件事確認兩次）。改選回合沒有出卡時要不要另告知，見 §11.6 r6-3。

### 11.3 差距（第 3 步；查證指令在 repo 根目錄執行）

- G6-1 選定後不提供 `pick_id`：`grep -n 'def _write_candidates_pick_open' -A16 rag-orchestrator/services/agent/runtime.py | grep 'picked'`（`cands.get("picked") is not None` ⇒ None）；意圖呼叫因此不附 enum 與 `PICK_ID_RULE`，客人改口沒有理解管道。
- G6-2 打字選定已選定即不動：`grep -n 'def _write_candidates_typed' -A25 rag-orchestrator/services/agent/runtime.py | grep 'picked'`（早退；整句只打編號的路徑也只在未選定時走）。
- G6-3 推測式防護：`_name_lenient_keep_picked` 只看 `_name_lenient_active()`、不看候選集是否來自寬鬆比對（`grep -n 'def _name_lenient_keep_picked' -A22 rag-orchestrator/services/agent/runtime.py | grep 'active\|is_lenient'` 只命中 active）⇒ A-2a 精確同名的候選集也被擋（C14）；`_name_said_before_pick_only` 讀 `CANDIDATE_PICK_DIALOG_USER`，該標記只有按鈕回合寫進 dialog（`grep -n 'CANDIDATE_PICK_DIALOG_USER' rag-orchestrator/services/agent/runtime.py`），打字選定沒有 ⇒ P2-乙。呼叫點：`_write_draft_merge_intent`、`_write_proposal_merge`（`grep -n '_name_lenient_keep_picked(' rag-orchestrator/services/agent/runtime.py`；本節指令描述 r6 實作前的程式，r6 刪除後此指令回 0，即 F1 (i)；改前命中見 `~/jgb-archive/arch-step3-20261018/f12/r6/pre-impl/agent/runtime.py`）。
- G6-4 寬鬆候選第一次選定改寫名稱後即拿掉寬鬆標記：`grep -n 'k != _wc.LENIENT_KEY' rag-orchestrator/services/agent/runtime.py`（`_name_lenient_pick_rewrite`；r6 改為保留寬鬆鍵後此指令回 0，改前命中見同一備份）⇒ 改選另一筆時 `is_lenient` 為假、名稱不再改寫，草稿名稱仍是第一筆的正名。
- G6-5 綁定比名稱指紋：`grep -n 'def _write_candidates_bound' -A12 rag-orchestrator/services/agent/runtime.py | grep 'name_fp'`；名稱欄任何改變 ⇒ 解綁、出卡時依名稱重查（新名稱重查的機制已在，r6 只要讓「本回合講的新名稱」走得到、讓模型從上下文填回的舊講法走不到）。
- G6-6 出卡前按舊按鈕改選現行已可行（`_write_candidate_pick_begin` 不擋已選定：`grep -n 'def _write_candidate_pick_begin' -A30 rag-orchestrator/services/agent/runtime.py | grep -c 'picked'` 的命中只在寫入處），但選定後畫面不再列按鈕；出卡即清候選集（`_begin_pending_confirm`，A2-R6 (a)），出卡後改選照 DSP-104（`record_rechoice`），不在 r6。
- G6-7 現行程式註解與測試的「已選定 ⇒ 不動」：`_write_candidates_typed` docstring；測試 `rag-orchestrator/tests/unit/agent/test_f12_name_lenient_req.py` 的 `-k "p21 or p2a"` 各支（含 `test_f1_p2a_said_before_pick_only_boundaries`）。
- 分工防護不受影響：不變量 45 只在 `confirm_source:model:unregistered` 時 FAIL（`grep -n 'model:unregistered' scripts/audit/checks/division_guard.py`）；改選走意圖呼叫＋程式驗證、出卡仍由程式依草稿（`program_pick`），不新增模型自呼出卡路徑。

### 11.4 路徑（第 4 步；括號＝服務的 §11.1 目標）

1. **選定後仍提供 `pick_id`**（目標 1）：`_write_candidates_pick_open` 在候選集有效、已綁定、出卡前時，選定與否都回候選集；enum、資料段、`PICK_ID_RULE` 與未選定時相同（同一份候選集 `ids`，同一支帶 role 與 viewer 的查詢組資料段）。取列來源（§11.10 待查 1）：候選集帶寬鬆鍵且已改寫名稱（選定中或已撤回，第 2 點）⇒ 一律以 `name_lenient_rows_for_ids` 依 `ids` 取列（前面照現行保留 `self._name_lenient_active()` 判斷；取不到列 ⇒ `None`、不附 `pick_id`）——草稿名稱已改寫成選定那筆的正名，若照現行先以名稱重查（`write_name_candidates`），回來的列可能只剩同正名者，`offered` 少於 `ids`、改選不到其他筆；A-2a 精確同名與選對紀錄的候選集名稱未改寫，照現行。按鈕回合照舊不建意圖呼叫。
2. **選定後的打字回合由程式依 `pick_id` 決定**（目標 1、3）：`_write_candidates_typed` 不再於已選定時早退——
   - `pick_id` ∈ `pick_offered` ∩ `ids` 且 ≠ 現選定 ⇒ 改選（寫回候選集 `picked`），記新標記 `write_candidate_repick:typed`（常數放 `write_candidates.py`）；
   - 整句只打編號且在 `ids` 內、≠ 現選定 ⇒ 改選（同上標記）；已選定時 ⛔ 走 `pick_matches_name` 分支（整句打候選集外編號 ⇒ 選定不動；§11.8 R6-S1）；
   - `pick_id` 等於現選定、`none`、缺漏、型別或值不合 ⇒ 選定不動；
   - 選對紀錄片的分不出（`pr_indistinct_ids`）與金額期間不符（`_pick_right_typed_mismatch`）照未選定時同一套規則套在改選目標上；改選目標被退回 ⇒ 清掉 `picked`（候選集保留、重問），⛔ 留著舊選定讓程式出舊那筆的卡（§11.8 N-2）。**清掉選定後的「已撤回」狀態**（§11.8 補審 R6-N3、§11.11、§11.12；業主 2026-10-24 選「簡化後再審一次」）：清掉 `picked`（`retract` 或改選被退回）時 ⛔ 動草稿名稱、⛔ 重新解析名稱；候選集保留原 `ids`、`LENIENT_KEY`、已改寫鍵，另記 `withdrawn: True`。草稿名稱與 `name_fp` 不變 ⇒ 綁定照舊成立（`_write_candidates_bound`）。已撤回期間：
     - 意圖呼叫照第 1 點附同一份 `ids` 的 `pick_id`；`pick_id` ∈ `ids` ⇒ 重新選定（拿掉 `withdrawn`，寬鬆來源依第 3 點改寫名稱）；`retract`／`none` ⇒ 不動；
     - 名稱合併（§11.13 V7-1）：第 4 點的分類與第 2 點「判定順序」的暫存不併，在已撤回且仍綁定時同樣適用（模型提議與意圖兩處）——候選集內講法丟棄、不是本回合講的丟棄，只有候選集外且本回合講的才解綁重查；「`pick_id` 等於現選定」一條不適用；
     - **出卡入口的關口**（§11.13 V7-2）：程式依草稿發 `confirm.request` 的兩個入口——`wd_program`（`_write_draft_decide` 的 created／merged／picked／reask）與 `proposal_program`（模型提議經 `_write_proposal_handle` 轉成的程式呼叫）——在候選集有效且綁定時經同一個關口：已選定 ⇒ 兩入口都帶 `program_pick`（現行只有 `wd_program` 帶）；已撤回 ⇒ 在發出 `confirm.request` 之前整次改成**重列同一份 `ids`**（列候選回合的按鈕與固定句），`confirm.request` 不執行，選對紀錄的 `scope_pick` 帳單解析也不做；B2 `_write_reply_state` 缺欄分支在已撤回時同樣不重新解析名稱（照已選定處理）；
     - 重列取列（§11.13 V7-3）：與第 1 點 `pick_id` 資料段同一套——寬鬆且已改寫 ⇒ `name_lenient_rows_for_ids`；其餘先 `write_name_candidates`，回 None（例：(丙) 列出的精確同名候選集在其他欄位仍缺時）⇒ `name_lenient_rows_for_ids` 依 `ids` 取列（estate／contract 型別）；只留 `ids` 內、本人查得到的列；
     - 依上列取列仍為空（全都看不到了）⇒ 清掉候選集與草稿名稱欄，照現行追問名稱，⛔ 出卡；
     - 本回合講出候選集外的名稱（第 4 點）⇒ 照現行解綁、候選集清掉、依新名稱重查。
   四種來源（(甲)、(乙) 寬鬆、A-2a 精確同名、選對紀錄）都走同一條路，不重新解析名稱，所以不會唯一命中舊那筆而出它的卡（§11.12 B-1、B-2 與兩條待查都不再適用）。第 7a 點的 `retract` 同一條規則。
   - **判定順序**（§11.8 N-1）：已選定且綁定時，同一回合先算出程式驗證過的 `pick_id`（∈ `pick_offered` ∩ `ids`），再做名稱欄合併（第 4 點）；模型提議合併（`_write_proposal_merge`，早於意圖呼叫）在此狀態下把名稱欄值暫存不併，留到 `_write_draft_decide` 拿到 `pick_id` 後依第 4 點處理；意圖結果合併（`_write_draft_merge_intent`）同樣以驗證過的 `pick_id` 為準，⛔ 名稱合併先解綁、使改選失效。
3. **寬鬆候選改選時名稱跟著改寫**（目標 1）：保留「候選集來自寬鬆比對」的標記到出卡（不再於第一次改寫時拿掉 `LENIENT_KEY`；改以新鍵記「已改寫」；`load_write_candidates` 形狀要求（§11.8 R6-S4）：新鍵另列封閉鍵集合（寬鬆＋已改寫），值須 `is True`、只能與 `LENIENT_KEY` 同時出現、型別限 estate／contract、`picked` 非 None 或 `withdrawn` 為 True；`withdrawn` 值須 `is True`、只能在 `picked` 為 None 時出現；另加 `picked ∈ ids`；第 4 點新增的 `origin_fp` 與原講法正規化字串另列入封閉鍵集合、型別固定為字串、長度上限同名稱欄、兩者須對應（`origin_fp`＝該字串的指紋）；候選編號等於保留字 `none`、`retract` ⇒ 組候選集時拒收、讀回判形狀不合（§11.8 補審 R6-S7）；不合 ⇒ `write_candidates_shape_invalid`、候選集清掉），改選後把草稿名稱改寫成新那筆的系統正名、名稱指紋同步更新。A-2a 精確同名候選集名稱本來相同，不改寫。
4. **選定後名稱欄的合併規則**（目標 2、3、4）：候選集已選定、仍綁定時，意圖呼叫或模型提議帶來的名稱欄值——
   - 本回合已改選（第 2 點）⇒ 丟棄該值（名稱由第 3 點改寫或本來相同）；
   - `pick_id` 等於現選定 ⇒ 丟棄（指的就是選定那筆）；
   - 值是**候選集內講法** ⇒ 丟棄（改不改選只看 `pick_id`）。候選集內講法的定義：正規化後等於或被包含於這份候選集的**原講法**（列候選時草稿的名稱值；候選集新存其指紋 `origin_fp` 與正規化字串（只供本點比對，⛔ 寫回草稿），與 `name_fp` 同源（`_write_candidates_field_value`），⛔ 取 R4 整句、送模型的 messages 或 provenance（FR-10）；(乙) 缺名稱觸發時存空字串，跳過「被包含於原講法」這一條；寬鬆改寫名稱時不動），或被包含於候選集任一筆的系統正名（正名只取本回合帶身分取得的列——`name_lenient_rows_for_ids` 或 `write_name_candidates` 的列，不分開關一律保留本回合的列供比對；⛔ 取模型或使用者的值；取不到列 ⇒ 只套原講法那一條，再依本回合原話判定；§11.8 補審 R6-S8、R6-S9）；⛔ 把「包含原講法」的較長名稱算進來——那可能是候選集外的新名稱（例：原講法「幸福」、改口「幸福五館」），要重查（§11.10 B-a）。這是對有限集合的決定性比對（目標正本 §2.2），用意是讓客人補欄位時重講原本的模糊講法不會被當成新名稱（§11.9 B1；r5 F8 第 1 次已知限制）；
   - 其餘情形：值出自本回合原話（正規化後為本回合使用者原話的子字串，同 r4 R1 與 (丙) 的「本回合講的」判定，`_name_said_in_message`）⇒ 視為新名稱（**候選集外**），照現行合併 ⇒ 解綁 ⇒ 依新名稱重查（現行精確→寬鬆，(甲)(丙) 同一組閘門）；不是出自本回合原話 ⇒ 丟棄（模型從上下文填回的舊講法）。
   記標記 `write_candidate_name_kept`（丟棄時）／`write_candidate_name_new`（改用新名稱時），只記型別。
5. **移除推測式防護**（目標 4）：刪 `_name_lenient_keep_picked`、`_name_said_before_pick_only` 與標記常數 `V_NAME_LENIENT_KEEP_PICKED`，兩個呼叫點改接第 4 點的規則；`CANDIDATE_PICK_DIALOG_USER` 不再被任何決策讀取（按鈕回合照舊寫進 dialog，供既有用途）。
6. **範圍**：依 §11.6 r6-1 裁定——建議第 1～5 點套用所有寫入候選集（A-2a 精確同名、選對紀錄、F12 寬鬆）；若裁只限寬鬆候選集，第 1、2、4 點加 `is_lenient` 條件，A-2a 候選集維持現行。
7. **改選回合的告知**（目標 1：讓客人知道改口有被收下）：依 §11.6 r6-3 裁定。
7a. **只撤回、沒指定新的一筆**（目標 1；例「剛剛選錯了」「不是這間」）：依 §11.6 r6-7 裁定。建議 (a)：`pick_id` enum 加一個值 `retract`，`PICK_ID_RULE` 加一句「使用者說選錯了／不是這筆、但沒說要哪一筆 ⇒ retract」；程式收到 `retract` 且已選定 ⇒ 清掉 `picked`、進入第 2 點「已撤回」狀態，重列同一份 `ids`（同列候選回合的按鈕與固定句），記 `write_candidate_retract:typed`；未選定時收到 `retract` ⇒ 當 `none`。
8. **測試**：改寫 `test_f12_name_lenient_req.py` 的 p21／p2a 各支為 r6 契約（見清單 F1 r6 項）；A-2a 測試中斷言「已選定後打字不動」的情形依 r6-1 更新並逐支列入收案報告；新增測試檔 `test_f12_repick_r6_req.py`。
9. **文件**：收案時改 `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` 寫入候選段（選定後可改選）、目標正本 §3 P5 現況、交接檔；記一條 DSP（含 r6-1～r6-7 裁定）；若 r6-1 選全部，交接檔 §2.4 A-2a 殘留「出卡前已選定又改選仍沿用舊選定」同步刪除。

10. **開關與回退**（§11.9 B6）：r6 第 1～5、7、7a 點掛在 A-2a 生效（`AGENT_WRITE_CANDIDATES` on 且 A+ 三開關 on）之下，不另加開關。r6-1 裁 (a) 時套用所有候選集，`AGENT_NAME_LENIENT` off 只關寬鬆候選，A-2a 精確同名與選對紀錄的候選集仍照 r6；r6-1 裁 (b) 時加 `is_lenient` 條件，`AGENT_NAME_LENIENT` off ⇒ r6 全部不生效、選定後行為與 r5 逐字相同。A-2a off ⇒ 沒有候選集，與現行逐字相同。回退：核可時把受改動檔原樣複製到 `~/jgb-archive/arch-step3-20261018/f12/r6/pre-impl/`（md5 記於 `f12/r6/pre-impl-md5.txt`；工作樹未提交，所以 git 沒有可回的版本）；要回退就把這些檔複製回工作樹、比對 md5 後重建容器。只關開關無法回退 r6-1 (a) 對 A-2a 候選集的改動。

相關但不在本次範圍：出卡後改選（DSP-104 `record_rechoice`，現行）；「編號22492」這類前綴加編號被當名稱走寬鬆（P3-丙，r3／r4 既有，第 3 位 verifier 判不在 FR-1 範圍）——第 2 點只收整句只打編號與 AI 回的 `pick_id`，前綴句由 AI 理解；選定後重新顯示候選按鈕（現行畫面只在列候選那回合有按鈕，改選走打字）。

### 11.5 偏離與取捨

- 第 4 點保留「名稱值是否出自本回合原話」的判定：它判的是**抽出來的值從哪來**（同值閘 `write_intent_value_not_in_user_words`、r4 R1、(丙) 已用的判定），不是推測客人有沒有改口；改不改選只由 AI 的 `pick_id`（程式驗證）與本回合講的新名稱決定。這個讀法交業主確認（§11.6 r6-2）。
- 改選不先問確認（偏離 Rasa 可選的確認變體，同 Rasa 預設）：理由見 §11.2。
- 候選集內講法只收「等於或被包含」：客人重述時加了字（例「幸福一館那間」，若 AI 抽出的名稱值連「那間」一起）就不算候選集內講法，會依該值重查、可能再列一次候選；取決於 AI 抽出的值，由 F10 不改口情境量，照實報。
- 候選集外的新名稱若剛好被包含於某筆候選正名（例：候選「幸福五館A棟」，客人改講候選集外的「幸福五館」），會被當候選集內講法丟棄、卡仍是原選定（不會選到候選集外紀錄；卡須按確認）；fixture 有此名稱族則 F10 放 1 場照實報（§11.8 補審 Q-r4）。
- AI 理解失敗（改口卻回 `none`、又沒講新名稱）時選定不動，卡會是舊那筆——取決於模型理解，由 F10 量；卡仍須按確認。
- 現況比較好做的部分照實寫：沿用 A-2a 的 `pick_id` enum 與驗證，是因為它已存在且就是 set slot 的形狀，不是因為業界如此。

### 11.6 待業主裁（核可時一併裁）

- **r6-1 範圍**：第 1～5 點套用到哪些候選集？(a) 全部寫入候選集（建議）——依據：C14 是 A-2a 精確同名候選集，在 v2 同樣出了已撤回那筆的卡（G6-3：防護不分寬鬆與否）；交接檔 §2.4 已記 A-2a 殘留「出卡前已選定又改選仍沿用舊選定」，是同一機制；只修寬鬆會是特例修法。代價：A-2a 既有行為「選定後打字不動」改變，相關測試要改。(b) 只限 F12 寬鬆候選集：A-2a 維持現行，C14 形狀不修。
- **r6-2「講到候選集外的名稱」怎麼判**（§11.5 第 1 點、§11.4 第 4 點）：(a) 照第 4 點（建議）——先排除候選集內講法（等於或被包含於原講法、或被包含於候選集內某筆正名；包含原講法的較長名稱不排除、會重查），剩下的名稱值又出自本回合原話，才算候選集外 ⇒ 重查；客人補欄位時重講原本的模糊講法，不重查、不重列；(b) 不排除候選集內講法、只看是否出自本回合——重講原講法會再列一次候選（r5 F8 第 1 次已知限制），與 FR-14 衝突；(c) 選定後一律丟棄名稱值、只認 `pick_id`——候選集外的新名稱就重查不到，與原話 15「講到候選集外的名稱就依新講法重查」衝突。
- **r6-7 只撤回、沒指定新的一筆**（原話 15「改口＝撤回選定」的讀法；§11.4 第 7a 點）：(a) 清掉選定、重列同一份候選（第 2 點「已撤回」狀態，客人重新選定前不出卡），由 AI 回 `retract` 觸發、程式驗證（建議）——依據：原話 15 把改口等同撤回；不處理的話，客人說「選錯了」之後卡仍是已撤回那筆，違反目標 1；(b) 維持選定、等客人講出要哪一筆——成本低，但「剛剛選錯了」之後若直接補欄位，卡會是已撤回那筆。
- **r6-3 改選回合的告知**：改選了但這回合還沒出卡（其他欄位仍缺）時，(a) 程式在追問前加一句固定句「已改成：<系統正名>（編號 <N>）。」（建議；Rasa 預設改值後告知，客人才知道改口有被收下；插入的是系統紀錄的正名與編號，不回顯客人原話）；(b) 不加，等卡出來才看得到。選 (a) 則 B 片固定句清單（`test_v16b_program_texts_are_fixed_constants`）加一句，且（§11.8 R6-S2）：名稱只取本身分清單上新那筆的系統列（`name_lenient_picked_title` 或同一份 `pick_rows` 的列，過 `sanitize_data_piece` 且等值），⛔ 取草稿、使用者或模型值；樣板常數只含 `{title}`、`{id}` 兩欄；寫進 dialog 的是不含名稱的程式摘要（同列候選時的 `dialog_summary` 做法），回覆才含名稱；`write_candidates.py` 固定句段不變式改寫為「只插筆數，或系統正名與編號」。
- **r6-4 量體**：F3″、F2 不重跑（建議）——F3″ 腳本列出候選即停、不經選定（第 1 位 verifier 已以程式閱讀確認）；F2 41 場模擬客人的宣稱已依原話 14 縮窄，r6 只動「選定後到出卡前」，由 F10 專題量；替代：F2 重跑 41 場（約多 100 萬 token 模擬客人用量）。
- **r6-6「打字選定也記標記」讀法**：(a) 讀為「打字選定與按鈕選定在後續回合效果相同」，不另寫標記（建議）——r6 的決策不讀任何原話位置標記（第 5 點），寫了也沒有決策會用；(b) 另把打字選定也寫進同一個 dialog 標記 `CANDIDATE_PICK_DIALOG_USER`——多一處 dialog 寫入、無決策讀它，日後若有程式讀它則兩種選定一致。
- **r6-5 改前對照容器**：以現行常駐映像（v2）打標籤 `aichatbot-rag-orchestrator:f12-v2`，起 `f12-v2`（18107，共用 DB、mock）當 F10 改前；刪除照舊需業主同意。替代：只用 `f12-before`（F12 前，沒有寬鬆候選，F10 寬鬆情境無法對照）。

### 11.7 執行順序與停點

security-reviewer（唯讀，處置寫入本節 §11.8）→ plan-verifier → 業主核可（含 r6-1～r6-7）→ security-executor 實作第 1～10 點（含 7a）＋單元 → F10 輸入由 fresh 代理產生並凍結（不讀程式、不看 `f12/r5/f8a`～`f8c` 與 `p21/` 的輸入）→ 起 `f12-v2`、重建常駐容器、F0（mock、md5、`make audit`）→ F10 兩容器實跑、第 3 位 verifier 場景重送（只報）→ 全量 unit → 報告 → 第 4 位 fresh verifier（F8，復原第 4 輪）。

停點：
- F10 任一場（判定範圍依清單 F10「適用情境」；標 Q-r4 形狀的場只報、不觸發停點）卡上那筆 ≠ 最後選擇，或標「撤回」的場卡上是已撤回那筆（r6-7 裁 (a) 時）⇒ 停，照實交業主（⛔ 先拿 F10 輸入診斷再改；要診斷須業主同意，用過的輸入不再撐宣稱）。
- 任何改選落到候選集外編號 ⇒ 停。
- 現行未選定時的行為（列候選、第一次選定、出卡）有任何改變（單元 off-run／回歸）⇒ 停，修到逐字相同。
- 第 4 位 verifier REFUTED ⇒ 第 5 輪為最後一輪；再不過即 `PAUSED_VERIFICATION`，交業主。

用量：收案回報子代理 token 加總與模型費用；⛔ token 上限當停點。

### 11.8 資安審查處置（security-reviewer 2026-10-24，唯讀；P0／P1 0 條）

審查原件的發現編號即為 R6-S1、R6-S2、R6-S4、R6-S5（原件沒有 R6-S3）。

主會話抽查：`_write_draft_decide` 內 `_write_draft_merge_intent(` 排在 `_write_candidates_typed(` 之前、`_write_proposal_handle` 先呼 `_write_proposal_merge(` 再 `_write_draft_decide(`（N-1 成立）；`_write_candidates_typed` 內有 `elif await pick_matches_name(` 分支（R6-S1 成立）。指令：`grep -n "_write_draft_merge_intent(\|_write_candidates_typed(\|pick_matches_name(\|_write_proposal_merge(" rag-orchestrator/services/agent/runtime.py`。

| ID | 嚴重度 | 內容 | 處置 | 落點 |
|---|---|---|---|---|
| R6-S1 | P3 | 已選定時整句打候選集外編號會走 `pick_matches_name`，可能把選定設到候選集外的同名紀錄 | FIX | §11.4 第 2 點；清單 F1 (b) |
| R6-S2 | P3 | r6-3 (a) 告知句未鎖名稱來源與 dialog 寫法，可能繞過 S-4 包裝、違反 S-9 | FIX（若裁 (a)） | §11.6 r6-3；清單 F1 (j) |
| R6-S4 | P4 | `load_write_candidates` 不驗 `picked ∈ ids`；新鍵形狀未定（縱深防禦，狀態存伺服端、出卡再以身分查） | FIX | §11.4 第 3 點；清單 F1 (k) |
| R6-S5 | P4 | 選定後每個打字回合多出候選資料段查詢、改選多一次取名稱查詢（不屬 S-21 的兩支） | DEFER（不設上限，照實報） | 清單 F10 報告項 |
| N-1 | 功能（非資安） | 名稱合併早於改選判定 ⇒ 新名稱先解綁、改選失效 | FIX | §11.4 第 2 點「判定順序」 |
| N-2 | 功能（非資安） | 改選目標被退回時舊 `picked` 仍在 ⇒ 出舊那筆的卡（P2-甲 形狀） | FIX | §11.4 第 2 點；清單 F1 (b) |
| P-1 | 待查 | 改選後改寫名稱失敗 ⇒ `picked`＝B、名稱＝A | 加單元確認（反證：出卡依編號精確查並覆寫名稱） | 清單 F1 (c) |
| P-2 | 待查 | 資料段注入面擴大到選定後回合（只限候選集內） | DEFER：影響限本人候選集、卡須按確認；以 F10 不改口情境 `write_candidate_repick:typed`＝0 量 | 清單 F10 |
| P-3 | 待查 | F1 (g) 缺綁定正對照、只測換使用者 | FIX | 清單 F1 (g)、(h) |

**補審（2026-10-24，同一位審查員，針對 `retract`、`origin_fp`、依 `ids` 取列、候選集內講法；P0～P2 資安 0 條）**：R1 `retract` 只清選定、重列列出自帶身分查詢，無新授權或外洩面；R2 原講法字串是已落地的草稿名稱值，不違反 FR-10、S-7、S-15；R3 依 `ids` 取列仍經 `_name_lenient_identity_ok`、成員範圍不變；R4 候選集內講法只丟名稱值、不設選定。

| ID | 嚴重度 | 內容 | 處置 | 落點 |
|---|---|---|---|---|
| R6-N3 | 功能 P2 | 寬鬆且已改寫的候選集清掉 `picked`（`retract` 或 N-2）後，現行重列「程式依草稿重發」會以舊那筆正名解析 ⇒ 唯一命中、出已撤回那筆的卡。主會話對碼：`runtime.py` `_write_candidates_typed` docstring「重列同一份候選（`reask`，程式依草稿重發）」 | FIX | §11.4 第 1、2 點；清單 F1 (b)(n)、F10 |
| R6-S7 | P4 | 保留值 `none`／`retract` 與候選編號同字形空間 | FIX | §11.4 第 3 點；清單 F1 (k) |
| R6-S8 | P4 | 原講法來源未釘死（可能誤取 R4 整句）、(乙) 情形未寫、指紋與字串對應未定 | FIX | §11.4 第 3、4 點；清單 F1 (k) |
| R6-S9 | P4 | 候選正名來源與取不到時的退路未寫 | FIX | §11.4 第 4 點；清單 F1 (m) |
| Q-r1 | 待查 | 注入讓模型連回 `retract` 造成重列 | DEFER：按鈕回合不建意圖呼叫可脫離；F10 不改口場報 `write_candidate_retract:typed` 次數（目標 0） | 清單 F10 |
| Q-r4 | 待查 | 候選集外新名稱被包含於某候選正名 ⇒ 被丟棄 | DEFER：不會選到候選集外紀錄、卡須確認；fixture 有此名稱族則 F10 放 1 場照實報；記入 §11.5 | §11.5；清單 F10 |
| Q-r2 | 待查 | 原講法字串保留到候選集清除 | 收案報告寫一句（session 30 分鐘閒置過期 `SESSION_IDLE_TTL_S`） | 收案報告 |

r5 資安處置：S-4（範圍擴大，R6-S2 處置後成立）、S-9（R6-S2 處置後成立）、S-19（實作後重跑 off-run 逐位相同）、S-21（成立，新增查詢另計）；S-1、S-2、S-5、S-6、S-15、S-18、S-20 不受影響（審查附依據）。

### 11.9 plan-verifier 第 1 次處置（2026-10-24，REVISE，B1～B7 皆 P2）

| ID | 內容 | 處置 | 落點 |
|---|---|---|---|
| B1 | 補欄位時重講原本的模糊講法會被當新名稱 ⇒ 解綁重查 ⇒ 重列，與 FR-14 衝突 | FIX：候選集內講法排除（存原講法指紋）；讀法交業主 | §11.4 第 4 點；§11.6 r6-2；清單 FR-13 讀法、F1 (m) |
| B2 | 「改口＝撤回選定」被收窄成「改選另一筆」，只撤回不指定時卡是已撤回那筆 | FIX：新增待裁題與建議做法 | §11.4 第 7a 點；§11.6 r6-7；清單 FR-12 讀法、F1 (n)、F10 |
| B3 | §11 沒寫終點指標 | FIX | §11 開頭「終點指標」 |
| B4 | F10 缺「順序對調」「只講一半」 | FIX：各 ≥1 | 清單廣度表 F10 |
| B5 | F10 (2) 未出卡與新名稱情境判不出 | FIX：(2) 分子只算出卡且卡＝最後選擇；新名稱情境只依 (4) 判、不計入 (2) | 清單 F10 |
| B6 | 回退方式與開關範圍未定 | FIX | §11.4 第 10 點；清單 FR-4 調整、F1 (f) |
| B7 | r6-6 裁 (b) 時無驗收項 | FIX | 清單 FR-14、F1 (l) |

待查三條：R6-S3 不存在（原件即無）；第 7 點補上服務的目標；揭露句由主會話寫（反證成立：情境句由 fresh 代理寫，揭露句不含名稱與指稱，維持）。

### 11.10 plan-verifier 第 2 次處置（2026-10-24，REVISE；依全域規則不再自動送審，主會話逐條處置後開一次收尾審查）

| ID | 內容 | 處置 | 落點 |
|---|---|---|---|
| B-a（P2） | 「包含原講法」會把候選集外新名稱當候選集內講法丟掉 | FIX：拿掉該方向 | §11.4 第 4 點；§11.5；§11.6 r6-2；清單名詞、F1 (m) |
| B-b（P2） | F10 在 r6-1 (b) 與只撤回情境下判不出、條件互斥 | FIX：清單 F10 加「適用情境」與「撤回」標法，四種裁法逐一寫明 | 清單 F10；§11.7 停點 |
| B-c（P2，wording-only） | 原話 15 流程片語（核可後實作、上限 5 輪）沒進規則表 | FIX：加 FR-16，F8 引用 | 清單規則表、F8 |
| B-d（P2，wording-only） | 業主裁定節漏 r6-7 | FIX | 清單第五節 |
| F8 缺廣度列（P3） | — | FIX（成本小） | 清單廣度表 |
| 待查 1 | 寬鬆選定改寫名稱後依名稱重查，`offered` 可能少於 `ids` | 主會話對碼成立：`_write_candidates_intent_kwargs` 先呼 `write_name_candidates(identity, cands["action"], payload)`，`payload` 來自 `_write_candidates_pick_open` 的草稿（`WF.to_payload(wd.draft["action"], …)`），只有結果為 None 才改用 `name_lenient_rows_for_ids`。FIX：已選定的寬鬆候選集一律依 `ids` 取列 | §11.4 第 1 點；清單 F1 (a) |
| 待查 2 | `retract`、`origin_fp` 未經資安審查 | 送原資安審查員補看，結果記於下方 | §11.8 補記 |
| 待查 3 | 重述加語尾可能被當新名稱 | 記為已知取捨，F10 量 | §11.5 |

### 11.11 收尾 plan-verifier（2026-10-24，REVISE；依全域規則暫停交業主）

收尾審查判 REVISE，C-1～C-3 皆 P2、Kind: substantive；依全域規則不再自行送審，交業主裁。業主 2026-10-24 選「修完再審一次 (建議)」⇒ 下列修法已套用到 §11.4 第 1、2、7a 點、§11.6 r6-7、§11.7 停點與清單 F1 (a)(b)(n)、F10，另開一次 fresh plan-verifier。C-1、C-2 的修法（還原名稱）被 §11.12 取代。

| ID | 內容 | 主會話提案修法 |
|---|---|---|
| C-1 | 第 3 點規定已改寫鍵只能在 `picked` 非 None 時出現，與第 1、2 點「清掉 `picked` 後仍依 `ids` 重列」互相矛盾：保留該鍵 ⇒ 讀回時形狀不合、候選集被清；拿掉該鍵 ⇒ 退回依舊正名重查 | 與 C-2 一併處理：清掉 `picked` 時把候選集**還原成剛列出時的狀態**——草稿名稱還原為原講法、`name_fp` 重算、拿掉已改寫鍵、保留 `LENIENT_KEY`。這就是 r5 已有的「寬鬆候選、未選定」狀態，形狀合法；取列走現行 `write_name_candidates` 查無 ⇒ `name_lenient_rows_for_ids` 依 `ids`（第 1 點「不論是否選定」改回「已選定時」） |
| C-2 | 撤回或改選被退回之後，下一回合只補欄位時，草稿名稱仍是舊那筆的正名 ⇒ 程式依名稱唯一命中 ⇒ 出已撤回那筆的卡 | 同上：草稿名稱已還原為原講法，出卡時依原講法解析 ⇒ 精確查無 ⇒ (甲) 寬鬆路徑列候選（FR-2 寬鬆路徑不直接出卡）⇒ 不會出舊那筆的卡。F1 補「撤回 → 下回合補欄位」「改選被退回 → 下回合補欄位」各一支，斷言卡 ≠ 舊選定，附正對照。代價：寬鬆路徑重跑，列出的候選可能與原 `ids` 不同（AI 挑選），屬 FR-2 範圍內 |
| C-3 | 只報的那一場（Q-r4，候選集外名稱剛好被包含於某筆候選正名）沒有從 F10 判定與停點中排除 | F10「適用情境」與 §11.7 停點加一句：標 Q-r4 形狀的場只報，不計入 (1)～(6)、不觸發停點 |

### 11.12 業主指示再審（2026-10-24，REVISE；交業主）

B-1（P2）還原用的是正規化字串，不是原值。原講法「幸福 一館」還原成「幸福一館」後，精確查找會唯一命中舊那筆，於是出舊那筆的卡（`_name_said_key` 會去空白與標點；`name_fp` 只做 strip；`_prepare_repair_estate` 唯一命中即出卡）。B-2（P2）(乙) 來源的寬鬆候選，原講法是空字串。撤回後依本句「剛剛選錯了」重跑寬鬆比對，可能回空並追問名稱，和 F1 (n)、F10 (6) 要求的「重列候選」互相矛盾。待查：選對紀錄帳單候選集撤回後，會不會依金額或期間唯一命中原選定；還原時沒有同步 `wd.pr_anchor`（估 P3）。

業主 2026-10-24 選「簡化後再審一次 (建議)」⇒ 已套用到 §11.4 第 1、2、3、4、7a 點、§11.6 r6-7 與清單 F1 (a2)(k)(n)、F10 (6)。

主會話判斷：第 3、4 輪的阻擋都來自 §11.4 第 2 點「清掉選定時還原名稱」。還原等於讓系統重新解析一次名稱，每一種來源（(甲)、(乙)、精確同名、選對紀錄）各有不同的解析路徑，所以會一直冒出邊角情況。提案的簡化做法是：**撤回後不還原、不重新解析**。候選集保留原 `ids`，並記「已撤回」；這段期間程式依草稿出卡時，名稱欄一律改為重列同一份 `ids`（寬鬆來源用 `name_lenient_rows_for_ids`，精確同名與選對紀錄用候選集本身），直到客人重新選定。這樣四種來源只走同一條路。B-1 不再發生（不還原），B-2 也不再發生（重列的是原清單），待查 1、2 也不再發生（不重新解析）。代價是要多一個「已撤回」狀態，並寫明它的形狀與綁定規則。

### 11.13 第 5 位 plan-verifier（簡化版，2026-10-24，REVISE；交業主）

業主 2026-10-24 選「修過未再審，交我核可 (建議)」⇒ 下表修法已套用、未再審，標 `next_gate: user_approval (fixed, not re-reviewed)` 交業主核可；本次修法的正確性改由清單 F1 (a2) 正對照、F10 停點與第 4 位 verifier 把關。

| ID | 內容 | 處置 | 落點 |
|---|---|---|---|
| V7-1（P2） | 已撤回時名稱合併無規則 ⇒ 模型填回舊講法 ⇒ 解綁 ⇒ 依該講法唯一命中已撤回那筆 ⇒ 出卡（P2-甲 形狀） | FIX：第 4 點分類與判定順序在已撤回時同樣適用 | §11.4 第 2 點；清單 F1 (a2) |
| V7-2（P2） | 出卡有 `wd_program`、`proposal_program` 兩入口，`program_pick` 只在前者；選對紀錄的 `scope_pick` 帳單解析不經名稱解析 | FIX：兩入口同一關口；已選定兩入口都帶 `program_pick`，已撤回整次改重列 | §11.4 第 2 點；清單 F1 (a2) |
| V7-3（P2） | (丙) 精確同名候選集在其他欄位仍缺時，`write_name_candidates` 回 None ⇒ 被當成全看不到、清名稱 | FIX：取列與第 1 點同一套，回 None 時依 `ids` 取列 | §11.4 第 2 點；清單 F1 (a2) |
| P3 | B2 `_write_reply_state` 已撤回時會重新解析名稱 | FIX（成本小）：照已選定處理 | §11.4 第 2 點 |
| P3 | 清單 F1 (k) 竄改列表字面與 (a2) 衝突 | FIX：補「且未帶 `withdrawn`」 | 清單 F1 (k) |
| 待查 | A-2a 精確同名已選定時，`proposal_program` 不帶 `program_pick`，可能重列並蓋掉選定 | 併入 V7-2 處置（已選定兩入口都帶）；F1 加一支 | 清單 F1 (a2) |

### 11.14 r6 復原第 4 輪：F10 停點後的根因與修法（2026-10-24 業主裁，清單原話 17、18）

F10（第 1 批輸入）依 §11.7 停點停：S11 卡是舊選定；S05、S32、S28、S19 未過 (2)(3)(6)。業主准拿 F10 輸入診斷（原話 17），根因與探針證據見 `~/jgb-archive/arch-step3-20261018/f12/r6/diag/diagnosis-r6.md`（容器內同 provider／模型／系統句／schema 重送失敗回合，各 5 次；正對照 S02、S03、S08、S14）。第 1 批輸入此後只報、不撐宣稱。

根因（摘要）：(i) S05：客人句中講出編號，AI 正確回該編號，「分不出」規則只收整句純編號而退回；(ii) S32、S28：按鈕選定後 dialog 只寫 `CANDIDATE_PICK_DIALOG_USER`、不含編號，AI 不知道現選定哪筆，`pick_id` 隨手填（推理段未判斷選哪筆）；(iii) S19：選定後附候選段時 AI 把「剛剛選錯了」判成另一支動作（實跑 S06、S09、S19，v2 為 0），換新草稿、候選集解綁；(iv) S11：新名稱很少被填進名稱欄。只改規則文字（探針 v1）S32 更差，否決；告知目前動作（swpa）動作誤判未改善，否決。

業界對照（`f12/sources/r6/rasa-command-generators.txt`，r6 已渲染）：Rasa command generator 提示的「Current State」帶 `active_flow`、`requested_slot` 與各 slot 現值；`cancel flow`「Cancel the current flow if the user requests it」。下列第 2 點把「目前選定的是哪一筆」交給理解層，同此形狀；本輪只查 Rasa 一家。

修法（業主原話 18 兩題皆照建議）：

1. **客人講出的編號不算 AI 猜測**（程式；根因 (i)）：使用者這句（NFKC）以非數字為界的數字段中，恰有一段屬於候選集 `ids` 且等於 AI 回的 `pick_id` ⇒ 該 `pick_id` 視為客人講出，選對紀錄「分不出」退回不套用（未選定時 PR-2／PR-7 與選定後同一條）；金額期間不符照舊套用。數字段只作佐證，⛔ 單憑句中數字改選（金額、電話可能撞號）。
2. **已選定回合先回「要不要改選」**（理解層輸入與輸出格式；根因 (ii)(iv)；原話 18 第 1 題）：候選集已選定（`picked` 有值）、出卡前的打字回合，意圖 schema 加必填封閉欄位 `rechoice`（`keep`／`switch`／`retract`，排在 `pick_id` 之前），`pick_id` enum 回到候選集 `ids`＋`none`（⛔ `retract` 值）；系統句與欄位說明附固定規則句，句中帶現選定編號（程式值，`candidate_id` 驗過形狀）。規則句逐字為探針 swp 所用：「rechoice：使用者先前已從清單選了一筆（編號 {picked}）。最新一句要不要改用清單裡的另一筆——只是補資料、確認、或重講原本的名稱或講法 ⇒ keep；明講要換成清單裡的另一筆（講編號、第幾個、或那筆的特徵）⇒ switch，pick_id 填那一筆；說剛才選錯了、不是這一筆，但沒講要換哪一筆 ⇒ retract；改講一個清單以外的名稱 ⇒ retract，並把新名稱照原話填進名稱欄位。rechoice 不是 switch 時 pick_id 填 none。」程式：
   - `switch` 且 `pick_id` 屬於本回合附上的編號 ∩ `ids`、≠ 現選定 ⇒ 依 §11.4 第 2 點改選（含分不出、金額期間退回 ⇒ 已撤回）；
   - `retract` ⇒ 清掉選定、進入已撤回、重列（取代 §11.4 第 7a 點以 `pick_id`＝`retract` 觸發；r6-7 (a) 語意不變）；
   - `keep`、缺漏、值不合 ⇒ 選定不動；且本回合候選集那一欄的名稱值一律丟棄（記 `write_candidate_name_kept`）——AI 判沒改選，名稱是重講；
   - 整句只打 `ids` 內另一編號 ⇒ 改選（不看 `rechoice`，同 §11.4 第 2 點）；
   - 名稱合併其餘照 §11.4 第 4 點（`retract`＋候選集外、本回合講的名稱 ⇒ 解綁重查）。
   已撤回（`picked` 為 None）與未選定的回合 ⛔ 附 `rechoice`，系統句與 schema 與未選定時逐字相同。
3. **選定後誤換動作的防護**（程式；根因 (iii)；原話 18 第 2 題）：候選集已選定或已撤回且綁定本草稿時，意圖回另一支寫入動作、但沒有任何非空欄位值 ⇒ 不換草稿、不合併、不整句填入，記 `write_candidate_action_kept`；帶了值 ⇒ 照現行換動作。代價：客人只講「改報修」不帶內容時不換，要多講一句。

驗收：F10 依 r6 清單同一套條件（含原話 17 的 S34 讀法），以**新一批**輸入重跑——新的 fresh 代理撰寫、指定涵蓋根因 (i)～(iv) 的形狀（句中講編號改選、補欄位順帶確認、補欄位時重講模糊講法、只說選錯了、選錯了＋新名稱、選定後換動作帶與不帶值），跑前凍結；換動作的場只報、不計入 (1)～(6)；改前 `f12-v2`、改後常駐容器；F10r 照舊只報；之後第 4 位 verifier（F8）。本輪為復原第 4 輪（共 5 輪），F8 REFUTED ⇒ 第 5 輪為最後一輪。F1 另加：第 1 點（句中講編號 ⇒ 改選；正對照：拿掉 ⇒ 退回）、第 2 點（已選定才有 `rechoice`；`keep` 且 `pick_id`≠選定 ⇒ 不改選；`keep` ⇒ 名稱值丟棄；`switch` ⇒ 改選；`retract` ⇒ 已撤回；系統句含現選定編號；已撤回與未選定時 schema 與系統句逐字同未選定；正對照各一）、第 3 點（不帶值換動作 ⇒ 草稿不變；帶值 ⇒ 照換；無候選集時照現行；正對照：拿掉防護 ⇒ 失敗）。改動前檔案備份：`~/jgb-archive/arch-step3-20261018/f12/r6/round4/pre-impl/`（md5 `round4/pre-impl-md5.txt`）。

已知、不在本輪：問題描述欄被整句填入改口句（例 S11 卡上問題描述＝「啊講錯了，是瑞光好房1…」，r6 前即如此，`_write_draft_fill_answer`）——照實報，交業主決定是否另開。

### 11.15 r6 復原第 5 輪（最後一輪）：第 2 批 F10 停點後的根因與修法（2026-10-24 業主裁，清單原話 19、20、21）

第 4 輪（§11.14）F10 第 2 批依 §11.7 停：錯筆卡 5 場（S09、S10、S16、S20、S21），(2) 12/18，(4) 6 場只過 S15（報告 `~/jgb-archive/arch-step3-20261018/f12/r6/report-r6.md`「復原第 4 輪」節）。業主准拿第 2 批診斷（原話 19），根因與探針證據見 `~/jgb-archive/arch-step3-20261018/f12/r6/round4/diag/diagnosis-r6b.md`（常駐容器內、線上同一 provider／模型／推理強度，系統句與 schema 由現行程式產生，失敗回合各重送 5～10 次）。第 2 批輸入此後只報、不撐宣稱。

#### 11.15.1 本輪規則（業主原話 → 可檢查條件）

| 規則 | 可檢查條件 | 出處 | 讀法 |
|---|---|---|---|
| R19-1 | 第 3 批 F10 輸入由 fresh 撰寫者寫、跑前凍結；第 1、2 批只報；本輪為復原第 5 輪（最後一輪） | 原話 19「准許，修完跑第 5 輪」 | — |
| R19-2 | 選定後的回合 ⛔ 把當句整句填進追問的欄位 | 原話 19「納入第 5 輪」；原話 21 Q15-1「包含已撤回」、Q15-2「所有文字欄」 | 「選定後」：回合開始時候選集已選定或已撤回、仍綁定本草稿（Q15-1）；適用欄位：`_write_draft_fill_answer` 會整句填入的所有文字欄（問題描述、帳單項目、說明、合約名稱等；Q15-2，比原話 19 所問的問題描述放寬，業主裁定）；未選定、無候選集的回合照現行整句填入 |
| R19-3 | 改口當回合即出卡、後續改口未送出的場（S20、S21 型）照錯筆卡算，⛔ 移出 (1)(2) | 原話 19「不移，照錯筆卡算」 | — |
| R20-1 | （本輪不做）選定後的回合並行呼叫兩次意圖判斷；兩次都指同一筆才改選；不一致 ⇒ 重列請客人再點 | 原話 20「選定後回合呼叫兩次」；原話 25「再不過就拿掉第6點」 | 非目標：第 8 位審查再判 REVISE（§11.15.13），依原話 25 本輪拿掉；選定後回合只送一次意圖呼叫（第 5 點的截斷重試除外） |
| R20-2 | 選定後 AI 回另一支寫入動作、欄位只有物件或合約名稱（`NAME_KEYS`）⇒ 不換動作；該名稱是候選集外、本回合講的 ⇒ 當成改講新名稱、依新名稱重查 | 原話 20「只有名稱不算帶值」（選項原文「只講名稱不換動作，名稱當成改講新名稱、依新名稱重新查找」）；原話 21 | 已選定與已撤回同一條；名稱是候選集內講法或不是本回合講的 ⇒ 丟棄（§11.4 第 4 點同一套分類，r6 已核可） |

**Q15-1（業主裁，原話 21：包含已撤回）**：R19-2（不整句填入）的「選定後」含已撤回（R20-1 依原話 25 本輪不做）。依據：已撤回期間重新選定那一回合，同一句話照現行會被整句填進追問欄位並在同回合出卡，與 S21 同形狀（程式路徑推導；第 2 批沒有觀察到實例）。代價：已撤回回合的欄位值只收 AI 抽出的。

**Q15-2（業主裁，原話 21：所有文字欄）**：`_write_draft_fill_answer` 對「來源為使用者原話、`text` 型、非 `NAME_KEYS`」的欄位都會整句填入（修繕問題描述、手開帳單「帳單項目」「說明」、建立合約「合約名稱」等，`confirm_card.py` `_ClosedField`）；選定後這些欄位一律不整句填入。依據：同一個機制、同一種錯（改口句被當答覆、當回合出卡）；探針（`round4/diag/diagnosis-r6b.md`「補充探針」）選定後只追問帳單項目時，AI 抽出「清潔費」9/9、「網路費」9/10，「欸等一下」0/9 誤填。第 2 批實跑中被整句填成改口句的只觀察到問題描述（10 場），帳單、合約文字欄沒有觀察到實例。代價：AI 沒抽到時要多問一次。

#### 11.15.2 目標形態與差距（摘要；依據 §11.14 已引的 Rasa 原文）

Rasa command generator 的提示帶 `requested_slot` 與各 slot 現值，由 LLM 發 `set slot`（「Can be used to correct and change previously set values」，`f12/sources/r6/rasa-command-generators.txt`）；slot 預設由 LLM 產生的值填（`from_llm`：「This is the default slot mapping type if the mappings are not explicitly defined in the domain file」，`f12/sources/rasa-slots.txt`）。自家差距：(a) 選定後追問欄位由程式整句填入，不經理解層判斷這句是不是答覆；(b) 改講新名稱沒有專屬輸出位置。本輪只查 Rasa 一家。

截斷重試（第 5 點）的業界原文（渲染頁 `~/jgb-archive/arch-step3-20261018/f12/sources/r6/round5/`，各檔首行為網址）：
- Instructor（`instructor-retrying.txt`）：「With integer max_retries, Instructor retries supported parsing and validation errors.」；「client.create(max_retries=2, ...) configures Instructor validation retries after the first extraction attempt: at most three SDK calls.」——支持「解析失敗由程式重送、次數有上限」。
- Instructor（`instructor-reask.txt`）：「you can use the max_retries parameter to set the number of times you can reask the model to correct the output.」——它的重送是把驗證錯誤附回去請模型改正。
- OpenAI 官方文件 Structured Outputs 頁的「JSON mode」節（`openai-finish-reason.txt`；本系統意圖呼叫用的是 strict `json_schema`，即 Structured Outputs，不是 JSON mode；該頁 Structured Outputs 節「Step 3: Handle edge cases」的內文沒有抽到）：「Your application must detect and handle the edge cases that can result in the model output not being a complete JSON object」；「you should use a validation library and potentially retries to ensure that the output matches your desired schema.」——支持「輸出不是完整 JSON 時由應用程式偵測並處理（可重試）」，原文寫在 JSON mode 的注意事項下，套到 strict schema 是推論。
- 偏離：第 5 點重送**同一份輸入**、不附錯誤訊息。理由：這裡的失敗是推理段失控、800 token 用完（`finish_reason=length`），不是輸出內容可被指正的錯；同一份輸入多數次正常完成（附段 S22b 6/10、不附段 0/75 截斷）。附錯誤訊息的 reask 變體沒有實測。上限只重送 1 次（Instructor 範例用 `max_retries=2`），理由是 8 秒等待內最多容得下一次（第 5 點耗時）。

雙次呼叫（R20-1）本輪不做（原話 25）。

#### 11.15.3 修法

1. **選定後不整句填入**（程式；R19-2；根因 S20、S21，及 S10、S16 出卡回合）：回合開始時候選集已選定或已撤回（Q15-1）、仍綁定本草稿 ⇒ `_write_draft_fill_answer` 不跑（Q15-2：所有文字欄）；追問欄位只收意圖呼叫抽出、過值閘的值。探針：選定後回合 13 句問題描述，AI 抽出 59/65（未抽出 6：截斷 5、漏 1），60/60 解析成功者回 keep。沒抽到 ⇒ 程式照現行追問（可回復）。
2. **改講新名稱的專屬欄位**（理解層輸出格式＋程式；根因 S12、S13、S14、S17、S15）：已選定的回合（附 `rechoice` 的回合），schema 加必填字串欄 `new_name`，排在 `rechoice` 之前；`rechoice` 規則句「改講一個清單以外的名稱 ⇒ retract，並把新名稱照原話填進名稱欄位」改為「…並把新名稱照原話填進 new_name」，系統句與欄位說明另接：「new_name：使用者最新一句若講了一個清單以外的物件或合約名稱（要改用的那一個），照原話填那個名稱（只填名稱本身，不含「改成」「那間」等字）；沒有講清單以外的名稱 ⇒ 空字串。」（兩句逐字＝探針變體 `nn`，`round4/diag/probe_variants_r6b.json`）。程式：`new_name` 去頭尾空白後非空、`sanitize_data_piece` 等值、出自本回合原話（`_name_said_in_message`）、且依 §11.4 第 4 點不是候選集內講法（原講法、本回合列的系統正名）⇒ 同一次沒有成立的改選（`rechoice` 為 `keep`、`retract`、缺漏，或 `switch` 但沒有驗過且未被退回的目標）時，視同 `retract`＋候選集外新名稱（同一次另有驗過且未被退回的改選目標——`switch` 驗過的 X 或第 3 點——⇒ 第 6 點矛盾，不走這裡）：寫進候選集那一欄（過既有值閘）、解綁、依新名稱重查（§11.4 第 4 點的 `"new"` 路徑，記 `write_candidate_name_new`）。不合任一條 ⇒ 忽略 `new_name`。已撤回、未選定的回合 ⛔ 附 `new_name`（系統句與 schema 照第 4 輪）。探針：S12 9/10、S13 10/10、S14 10/10、S17 9/10、S15 9/9 填出；對照 7 場 70 次 0 次誤填。風險：AI 常把「那間」一起填進（S15 6/9），新名稱解析吃不吃得下要實跑看，不另加詞表。
3. **句中講出的編號採為改選**（程式；根因 S19）：已選定的回合，`rechoice` 不是 `switch`，但 `pick_id` 屬於本回合附上的編號 ∩ `ids`、≠ 現選定，且 `_said_id_is_pick_id`（§11.14 第 1 點同一條：句中恰一段數字屬於 `ids` 且等於 `pick_id`）⇒ 視同 `switch`。只有句中數字、沒有 `pick_id` 相符 ⇒ ⛔ 改選。探針：S19 `pick_id` 10/10 等於句中編號、`rechoice` 10/10 回 keep。
4. **名稱不算新動作的值**（程式；R20-2；根因 S15）：§11.14 第 3 點「有沒有非空欄位值」改為不計 `NAME_KEYS` 的欄位；只有名稱 ⇒ 不換動作、記 `write_candidate_action_kept`。被擋下的那支動作帶的名稱欄值去向：
   - 已選定與已撤回同一條（R20-2）：依 §11.4 第 4 點分類——候選集外且本回合講的 ⇒ 算「改講新名稱」（不論 `rechoice` 是 `keep`、`retract`、缺漏，或 `switch` 但沒有驗過且未被退回的目標——原話 20「名稱當成改講新名稱、依新名稱重新查找」；同一次另有驗過且未被退回的改選目標——已選定：`switch` 驗過的 X 或第 3 點；已撤回：`pick_id` ∈ `ids` 驗過的 X——⇒ 第 6 點矛盾）：寫進候選集那一欄、解綁、依新名稱重查（記 `write_candidate_name_new`）；名稱取法同第 6 點（`new_name` 合條件就用它，否則用這個名稱欄值）；候選集內講法或不是本回合講的 ⇒ 丟棄；
   - 草稿其餘欄位照 §11.14 第 3 點不合併（被擋下那支動作的欄位只取名稱欄做上列分類）。
   無候選集、或候選集未綁定本草稿時照現行（§11.14 第 3 點不適用）。
5. **附候選段的意圖呼叫截斷時重試一次**（程式；根因 S22）：附候選段的呼叫回 `finish_reason=length` 或解析不出 ⇒ 同一份輸入重送一次；仍失敗 ⇒ 照現行（`None`）。未附候選段的呼叫 ⛔ 重試（與現行逐字相同）。`WRITE_INTENT_MAX_COMPLETION_TOKENS` 不改（探針：上限 1600 仍 3/20 跑滿，加大無效）。等待上限 `WRITE_INTENT_WAIT_MAX_S`（8 秒）不改，重試算在同一個等待內；超過 ⇒ 照現行逾時處理。探針耗時：截斷的呼叫 3.2～7.2 秒（6 次）、正常 0.7～2.6 秒（`probe_meta.txt`）⇒ 第一次截斷超過約 5 秒時重試來不及，照實量、照實報。
6. **同一次改選與改講新名稱**（程式，單次意圖呼叫；取代原第 6 點「選定後回合呼叫兩次」，依原話 25 拿掉；R20-2；根因 S12～S17 的同形狀邊界）：回合開始時候選集已選定或已撤回、仍綁定本草稿的回合：
   - **驗過且未被退回的改選目標 X**：已選定：`switch` 驗過的 X 或第 3 點；已撤回：`pick_id` ∈ `ids` 驗過的 X。「退回」＝現行 `_write_candidates_typed_post_pick` 的分不出、金額期間不符。程式在決定名稱值去向**之前**先算出是否退回——現行 `_write_candidates_name_rule` 用退回前算的 `repick_target`（`_write_candidates_repick_target`），本點改動；§11.4 第 4 點「本回合已改選（第 2 點）⇒ 丟棄該值」同改為「本回合有驗過且未被退回的改選目標」（已選定、已撤回皆同）。
   - **改講新名稱成立**（任一）：第 2 點 `new_name` 合條件；`rechoice=retract` 且名稱欄值為候選集外、本回合講的（§11.14 第 2 點保留的路）；第 4 點被擋下的另一動作帶候選集外、本回合講的名稱；已撤回時名稱欄值為候選集外、本回合講的（§11.4 第 4 點）。名稱 N 取法：`new_name` 合條件優先，否則名稱欄值。
   - **決定**（單次，依序取第一個成立的）：
     1. 另一動作帶非名稱欄值 ⇒ 照 §11.14 第 3 點換動作（現行，不受本點影響）；
     2. 有 X、且改講新名稱成立 ⇒ **矛盾**：視同 `rechoice=retract`（已選定 ⇒ 清掉選定、進入已撤回；重列同一份 `ids`）；本回合所有名稱值（意圖結果的名稱欄、`new_name`、被擋下動作的名稱、主模型提議暫存的 `deferred_names`）丟棄、不解綁；非名稱欄位照 `retract` 回合的現行合併；記 `write_candidate_name_conflict`；
     3. 改講新名稱成立（含 X 被退回）⇒ 寫進候選集那一欄（過既有值閘）、解綁、依 N 重查（記 `write_candidate_name_new`）；
     4. 有 X ⇒ 改選到 X（現行；名稱值是候選集內講法或不是本回合講的 ⇒ 丟棄）；
     5. 其餘照現行（`retract` 或 X 被退回 ⇒ 重列；`keep` ⇒ 不動）。
   - 意圖解析失敗（含第 5 點重試後仍失敗）⇒ 照現行（含 `_write_candidates_deferred_names`）。
   - 整句只打 `ids` 內編號 ⇒ 照 §11.4 第 2 點改選（現行）。
   - 未選定、無候選集的回合與現行逐字相同。

#### 11.15.4 驗收（依 r6 清單同一套條件；原話 17、19 的讀法）

- **F10**：第 3 批輸入，由第 3 位 fresh 撰寫者照 `round4/inputs/writer_brief_r6b.md` 同一份配額與限制（路徑改到 `round5/inputs/`，另禁讀 `f12/r6/round4/`）撰寫，配額不低於第 2 批，另指定涵蓋本輪根因的形狀：選定後被追問問題描述時改口（含先講「等一下」再改、改了又改回）、句中講出候選編號改選、撤回＋新名稱（含「那間」等尾綴）、否定句＋兩筆名稱只差一字、選定後換動作（帶內容與不帶內容）；另加配額：報修（有問題描述欄）場中選定後改口 ≥4、手開帳單場先給金額與期限、選定後再改口（讓系統只剩帳單項目要問）≥2、選定後只講一個候選清單外的新名稱（不講要做什麼、例「啊講錯了，是○○那間」）≥4，其中手開帳單或延期繳費 ≥2；每場另填 `change_steps`（撰寫者標的改口、撤回、換動作那幾則的 steps 索引，從 0 起算；不改口的場為空陣列）；跑前凍結（`round5/inputs/FROZEN_F10_r6c.txt`）。廣度同清單「## 廣度」：1 組資料（可用只有 `assistant_demo_vendor4.json`，理由見清單）× ≥45 場 × 每容器 1 次；輸入由不讀程式的撰寫者寫；改前 `f12-v2`（18107）、改後常駐容器（重建），同一批並列。判定沿用 r6 清單 F10 (1)～(6)；S34 型（按鈕那回合即出卡、改口句未送出）移出 (1)(2)（原話 17；S07、S42、S43 延伸讀法業主未表異議）；S20、S21 型照錯筆卡算（R19-3）。本輪另加兩條判定（§11.15.6 B1），與 (1)～(6) 同樣逐場列改前、改後：
  - **(7) 卡上文字欄不是改口句**（R19-2）：出卡的場，卡上「・問題描述：」「・帳單項目：」「・說明：」「・合約名稱：」各行的值（NFKC、去頭尾空白）⛔ 等於或包含該場 `change_steps` 任一則的原句（同樣正規化）。適用：出卡且 `change_steps` 非空、卡上有上列任一行的場。
  - **(8) 沒說要換動作就不換動作**（R20-2）：kind 不含「換動作」的場（客人沒明說要改做另一種寫入），第一次選定之後不出現另一支動作的草稿（trace `write_draft_action:<動作>` 只有該場 `action`）。名稱是候選集外的新名稱時，另照 (4) 判依新名稱重查。kind 含「換動作」的場照 §11.14 只報、不計入 (1)～(8)。適用範圍含不改口的場，比原話 21 紀錄的「擴到所有改口場」寬；依據：業主核可照建議修的 §11.15.8 C3 建議原文「擴到所有 kind 不含「換動作」的場」；理由：R20-2 適用於選定後的每一回合。
  F10 過＝(1)～(8) 全過；停點仍依 §11.7（錯筆卡）與 §11.15.5。判分腳本 (4) 改看「改口那回合」（第 4 輪更正），(7)(8) 一併寫進判分腳本；跑前以第 2 批 after 結果驗判分腳本：(4) 須判 S12、S13、S14、S16、S17 不過、S15 過；(7) 須判 S20（卡上「欸等一下」）、S21 不過（第 2 批沒有 `change_steps`，驗判分用的值由主會話依各場 kind 與 steps 標出、先存檔再跑），並以第 2 批卡上問題描述是正常描述的報修場（判分前列出場號）為過的正對照；(8) 須判 S15 不過（kind「撤回＋新名稱」，改口那則之後草稿換成 `repair_create`；不需暫標），S06（選定後改口、全程手開帳單）過；kind 含「換動作」的 S39～S41 不判。量尺自證：`f12-v2` 錯筆卡 ≥1。
- **F1 另加**（每點各列正對照：暫改程式的哪一處 ⇒ 哪一支測試失敗 ⇒ 還原）：
  - 第 1 點：選定後、追問問題描述、AI 沒抽到 ⇒ 不填、不出卡；AI 抽到 ⇒ 填 AI 值、出卡；已撤回後重新選定那回合 ⇒ 不整句填入（Q15-1）；選定後只追問帳單項目、AI 沒抽到 ⇒ 不填（Q15-2）；未選定時整句填入照舊。正對照：拿掉「選定後不跑 `_write_draft_fill_answer`」⇒「AI 沒抽到 ⇒ 不填」失敗。
  - 第 2 點：只有已選定的回合有 `new_name`、且排在 `rechoice` 前；`keep`／`retract`＋合條件 ⇒ 解綁重查、記 `write_candidate_name_new`；不出自本句、或是候選集內講法 ⇒ 忽略；已撤回與未選定的 schema、系統句與第 4 輪逐字相同。正對照：(i) 程式不讀 `new_name` ⇒「合條件 ⇒ 解綁重查」失敗；(ii) schema 拿掉 `new_name` ⇒ schema 測試失敗。
  - 第 3 點：keep＋`pick_id`≠選定＋句中講出該編號 ⇒ 改選；同樣但句中沒講 ⇒ 不改選；句中講的編號 ≠ `pick_id` ⇒ 不改選。正對照：拿掉第 3 點分支 ⇒ 第一支失敗。
  - 第 4 點：已選定＋另一動作＋只有名稱欄值且為候選集外、本回合講的 ⇒ 不換動作、記 `write_candidate_action_kept`、解綁依該名稱重查、記 `write_candidate_name_new`——`rechoice` 為 `keep`、`retract`、缺漏三支各一（含 `new_name` 空與 `new_name` 合條件兩種；後者用 `new_name`）；已選定＋另一動作＋只有名稱＋同一次驗過的 `switch` ⇒ 矛盾、重列；已撤回＋另一動作＋只有候選集外、本回合講的名稱 ⇒ 不換動作、解綁重查；另一動作＋只有候選集內講法（已選定、已撤回各一）⇒ 不換、名稱丟棄、選定不動；另一動作＋非名稱欄值 ⇒ 照換；無候選集時照現行。正對照：(i)「有值」判定改回計入 `NAME_KEYS` ⇒ 第一支失敗；(ii) 擋下後丟掉名稱欄值 ⇒「不換動作、解綁重查」那幾支失敗。
  - 第 5 點：附段呼叫第一次截斷 ⇒ 重送一次、用重送結果；第一次解析不出 ⇒ 同；兩次都截斷 ⇒ `None`；未附段的呼叫 ⇒ 只送一次；重試超過等待上限 ⇒ 照現行逾時。正對照：拿掉重試 ⇒ 第一支失敗。
  - 第 6 點（逐條對應 §11.15.3 第 6 點）：已選定——`switch` 驗過 X＋`new_name` 合條件 ⇒ 矛盾、重列、名稱不套用、不解綁、記 `write_candidate_name_conflict`；第 3 點句中編號＋`new_name`（例「22492 那間，不對，是幸福五館」）⇒ 同；`retract`＋名稱欄候選集外本回合講的（`new_name` 空）⇒ 改講新名稱；`switch` X 被退回（分不出）＋`new_name` 合條件 ⇒ 改講新名稱、解綁重查；`switch` X 被退回、無新名稱 ⇒ 重列；`switch` 驗過 X＋另一動作帶非名稱值 ⇒ 換動作（現行）。已撤回——`pick_id` X 驗過＋名稱欄候選集外本回合講的 ⇒ 矛盾、重列；`pick_id` X 被退回（分不出）＋名稱欄候選集外本回合講的 ⇒ 改講新名稱、解綁重查；`pick_id` X 驗過＋名稱欄是候選集內講法 ⇒ 改選 X、名稱丟棄（現行）。主模型提議暫存候選集外名稱＋同一次矛盾 ⇒ 暫存名稱丟棄、不解綁。選定後的回合只送一次意圖呼叫（第 5 點重試除外）。正對照：(i) 名稱去向改回用退回前的 `repick_target` ⇒「已撤回 X 被退回＋候選集外名稱 ⇒ 改講新名稱」失敗；(ii) 拿掉矛盾判定 ⇒「22492 那間，不對，是幸福五館 ⇒ 重列」失敗；(iii) 矛盾時不丟暫存名稱 ⇒ 暫存那支失敗。
  - 既有 F1 全數照過；`DEFAULT_MAX_COMPLETION_TOKENS = 2000` 與 `name_match.py` md5 不變。
- **F10r** 照舊只報；**F8**：fresh verifier（BRIEF-CONTRACT v1，未看過 r6 任何輸入與結果），自寫 ≥10 個新輸入（換說法、含本輪六點的形狀）。
- 核可後，本節 F1 另加項與 F10 第 3 批讀法追加進清單第五節，記新 sha256（`f12/r6/ACCEPTANCE_FROZEN_r6.txt`）。
- 改動前檔案備份：`~/jgb-archive/arch-step3-20261018/f12/r6/round5/pre-impl/`。

#### 11.15.5 停點、回復、用量

- F10 任一適用場錯筆卡 ⇒ 停（§11.7）；本輪是最後一輪 ⇒ r6 照實收案交業主，⛔ 再開第 6 輪。F8 REFUTED 同。
- 回復：工作樹未 commit；`round5/pre-impl/` 備份可整檔還原；常駐容器可依還原後工作樹重建。
- 已知、不在本輪（探針 T4，`diagnosis-r6b.md`「補充探針」）：選定後改口「第二筆才對啦」AI 10/10 把動作標成修繕；1/10 同時捏造問題描述＝改口句，這時有非名稱欄值，§11.14 第 3 點與本節第 4 點都擋不到，會換成修繕草稿。照實報，交業主決定是否另開。
- 預期（照實寫）：不做兩次呼叫 ⇒ 殘留 AI 誤讀沒有第二道擋（S09 型單次錯選約 3/10、S10／S16 型約 1/10；`diagnosis-r6b.md`「程式改不動的殘留」）⇒ F10 改口約 18 場仍可能 1～3 場錯筆卡，(1)「錯筆卡＝0」很可能不過、r6 照實收案；本輪能驗的是第 1～6 點修掉的形狀（S12～S22 型）有沒有消失。
- 用量：收尾回報子代理 token 加總與模型呼叫。

#### 11.15.6 plan-verifier 第 1 次處置（2026-10-24，REVISE，B1～B6 皆 P2）

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| B1 | R19-2、R20-2 的使用者層效果在 F10 沒有判定條件 | FIX：加 (7) 卡上問題描述不是改口句、(8) 換動作只帶名稱；撰寫者加 `change_steps` 與配額；判分腳本以第 2 批驗 | §11.15.4 F10 |
| B2 | 已撤回時被擋下的另一動作所帶名稱沒有去處 | FIX：已撤回照 §11.4 第 4 點名稱合併；已選定丟棄、只認 `new_name` | §11.15.3 第 4 點；F1 第 4 點 |
| B3 | 第 2 點「不論 rechoice」與第 6 點「矛盾 ⇒ 重列」衝突 | FIX：驗過的 `switch`＋合條件 `new_name` 一律依第 6 點矛盾重列 | §11.15.3 第 2 點；F1 第 6 點 |
| B4 | F1 正對照未逐點指名、第 4／6 點分支不全 | FIX：逐點寫正對照，補齊分支 | §11.15.4 F1 |
| B5 | 截斷重試未查業界 | FIX：渲染 Instructor 兩頁、OpenAI Structured Outputs，逐句引用並寫偏離（同輸入重送、不附錯誤訊息、上限 1 次） | §11.15.2 |
| B6 | 「選定後」含已撤回是業主未裁的讀法 | FIX：改列待裁題 Q15-1（建議含） | §11.15.1 |
| 待查 | 「不一致」是否只限編號不同 | 不處置：原話 20「不一致就重列」字面涵蓋（審查員同判反證強） | — |

#### 11.15.7 plan-verifier 第 2 次處置（2026-10-24，REVISE；依全域規則不再自動送審，主會話逐條處置後開一次收尾審查）

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| V1（P2） | 第 1 點讓所有整句填入的文字欄選定後都不填，超出原話 19 所問的問題描述，未標放寬 | FIX：列待裁題 Q15-2（建議放寬）；補探針 T1～T4；F1、F10 (7)、撰寫者配額涵蓋帳單項目 | §11.15.1；§11.15.3 第 1 點；§11.15.4 |
| V2（P2） | F10 (8) 沒有判分自證 | FIX：(8) 須判 S15 不過、S06 過 | §11.15.4 F10 |
| V3（P2） | 已選定時 `retract`＋名稱欄候選集外值（`new_name` 空）的決定未定 | FIX：算改講新名稱（保留 §11.14 第 2 點那條路），名稱取 `new_name` 優先；F1 第 6 點補兩支 | §11.15.3 第 6 點；§11.15.4 F1 |
| V4（P2，審查員標 wording-only） | OpenAI 引文標錯節、「預設 2 次」不符原文 | FIX：改標 JSON mode 節並註明推論；改為「範例用 max_retries=2」 | §11.15.2 |

新的準備度時期（epoch 2）：上表改動後送一次收尾 fresh plan-verifier；它再判 REVISE ⇒ 暫停交業主（除非它把剩下每條都標 wording-only）。

#### 11.15.8 收尾 plan-verifier 處置（2026-10-24，REVISE，3 條 P2；依規則暫停交業主，業主裁「修完再送一次審」，清單原話 21）

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| C1（P2） | 第 4、6 點對「已選定＋另一動作＋只有候選集外名稱＋`retract`＋`new_name` 空」結果相反 | FIX：統一為改講新名稱、依名稱重查（與 C2 同一處改） | §11.15.3 第 4、6 點；F1 第 4 點 |
| C2（P2） | 已選定時丟棄被擋下動作的名稱，是對原話 20「依新名稱重新查找」的收窄、未標 | FIX：照原話 20，已選定與已撤回同一條依 §11.4 第 4 點分類重查；R20-2 改寫 | §11.15.1 R20-2；§11.15.3 第 4 點 |
| C3（P2） | (8) 只判撰寫者標的 kind，S15 型（客人只改講名稱、AI 自標另一動作）量不到；「換動作只帶名稱」場未定義 | FIX：(8) 擴到所有 kind 不含「換動作」的場；撰寫者配額改成「只講清單外新名稱」；S15 不需暫標 | §11.15.4 F10 |

Q15-1、Q15-2 業主已裁（原話 21），正文改寫為定案。新的準備度時期（epoch 3）：送一位 fresh plan-verifier（業主指示的續審，原話 21）。

#### 11.15.9 續審 plan-verifier 處置（2026-10-24，REVISE：1 條 substantive、1 條 wording-only；依規則暫停交業主）

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| D1（P2） | 已撤回時同一次「重新選定 X」＋候選集外本回合講的名稱，無唯一結果 | FIX：比照已選定記為矛盾、重列；第 4 點寫明已撤回的驗過目標；F1 第 6 點補兩支與正對照 | §11.15.3 第 4、6 點；F1 第 6 點 |
| D2（審查員標 wording-only） | (8) 範圍比原話 21 紀錄寬、未標 | FIX：(8) 旁寫明放寬、依據與理由 | §11.15.4 F10 (8) |

業主裁「再審一次」（清單原話 22）：新的準備度時期（epoch 4），送一位 fresh plan-verifier。

#### 11.15.10 第 5 位 plan-verifier 處置（2026-10-24，REVISE：1 條 P2 substantive；依規則暫停交業主）

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| E1（P2） | 兩次不一致判重列，但欄位合併取第一次的名稱欄值，經現行名稱規則可能解綁重查，同一輸入兩種結果 | FIX：第 6 點改成一張「合併後的決定 → 選定狀態／名稱值／其他欄位／標記」的唯一表，名稱值只經這張表處理；F1 第 6 點補三支與五種決定各一支、附正對照 | §11.15.3 第 6 點；F1 第 6 點 |

說明：第 2～5 位審查員的 P2 都落在第 6 點各分支之間的一致性；這次把第 6 點收成一張決定表，一次涵蓋所有分支，而不是再補單一分支。

業主裁「再審一次決定表」（清單原話 23）：新的準備度時期（epoch 5），送一位 fresh plan-verifier，範圍限第 6 點決定表與 F1 第 6 點，以及它與第 2、4 點的一致性。

#### 11.15.11 第 6 位 plan-verifier 處置（2026-10-24，範圍限第 6 點，REVISE：G1～G4 皆 P2；依規則暫停交業主）

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| G1 | 「只一次成功且非不動」表判重列、F1 兩支卻要求改講新名稱（主會話上一版自己寫出的矛盾） | FIX：只留重列（照 R20-1）；刪掉相反的兩支 | §11.15.3 第 6 點；F1 第 6 點 |
| G2 | 改選目標被退回時表沒有結果 | FIX：退回在單次結果內套用，歸「重列」 | 同上 |
| G3 | 某一次換動作帶非名稱值時，決定與欄位合併互斥 | FIX：新增「換動作 A」類別；不一致時重列且不合併（含動作） | 同上 |
| G4 | 第 3 點改選＋`new_name` 的矛盾沒寫進第 2 點、F1 沒鎖 | FIX：第 2 點括號含第 3 點；F1 補一支 | §11.15.3 第 2 點；F1 第 6 點 |

說明：上一版的決定表改成「每次各自走完單次回合的整套程式判定、只算不套用，再比兩個結果；一致照第一次整個套用，不一致重列且本回合什麼都不合併」。單次回合的判定已在第 1～4 輪實作並測過，兩次呼叫只多一層比較，不再另寫一套合併規則。

業主裁「再審一次第 6 點」（清單原話 24）：新的準備度時期（epoch 6），送一位 fresh plan-verifier，範圍同 §11.15.10 末段。

#### 11.15.12 第 7 位 plan-verifier 處置（2026-10-24，範圍限第 6 點，REVISE：H1～H4 皆 P2；依規則暫停交業主）

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| H1 | 同一次「換動作帶值」與改選／撤回／新名稱同時成立時六類不互斥 | FIX：歸類改為依最終效果、固定先後（換動作 > 矛盾 > 改講新名稱 > 改選 > 重列 > 不動） | §11.15.3 第 6 點；F1 第 6 點 |
| H2 | 被退回的目標算不算「驗過」，第 2、4、6 點不一 | FIX：一律「驗過且未被退回」；退回＋新名稱 ⇒ 改講新名稱 | 第 2、4、6 點；F1 第 6 點 |
| H3 | `switch` 無驗過目標＋另一動作只帶名稱未定義 | FIX：照原話 20 算改講新名稱 | 第 2、4 點；F1 第 4、6 點 |
| H4 | 主模型提議路徑的暫存名稱在重列時未處理 | FIX：重列時暫存名稱丟棄、不解綁；提議已合併的非名稱欄位保留；等待以兩次都結束為準 | 第 6 點；F1 第 6 點 |

說明：H1、H3 的組合在只呼叫一次時就存在（第 1～4 輪程式依程式順序處理：換動作先於改選；`switch` 無目標時名稱丟棄），兩次呼叫只是讓它浮上檯面；本次以「依最終效果、固定先後」一次定義。

業主裁（清單原話 25）：再審一次第 6 點；再判 REVISE ⇒ 第 5 輪拿掉第 6 點、只做第 1～5 點。

#### 11.15.13 第 8 位 plan-verifier 處置（2026-10-24，範圍限第 6 點，REVISE：J1、J2 皆 P2）與原話 25 落地

| ID | 問題 | 處置 | 改在 |
|---|---|---|---|
| J1 | 已撤回、`pick_id` X 被退回＋同一動作名稱欄候選集外：第 3 類與 §11.4 第 4 點（現行用退回前目標）兩種結果；F1 已撤回那支寫成 `new_name`（已撤回不附） | FIX：取 J1 修法 (a)——§11.4 第 4 點「本回合已改選」改為驗過且未被退回，寫明是對現行程式的改動；F1 已撤回那支改寫成名稱欄、附正對照 | §11.15.3 第 6 點；F1 第 6 點 |
| J2 | 兩次都失敗＋已撤回＋暫存名稱：「不合併」與「同現行」互斥 | 不再適用：依原話 25 拿掉兩次呼叫；單次意圖失敗照現行（含 `_write_candidates_deferred_names`） | §11.15.3 第 6 點 |

原話 25 落地：第 6 點「選定後回合呼叫兩次」拿掉，R20-1 列為非目標；原第 6 點裡單次就成立的規則（驗過且未被退回、改講新名稱的來源、矛盾 ⇒ 重列且名稱不套用）改寫成新第 6 點，矛盾不再依兩次比較、改為單次時視同 `retract`＋名稱丟棄。新第 6 點與 F1 第 6 點是主會話依審查結果改寫，**已修未再審**；原第 6 點全文見 `~/jgb-archive/arch-step3-20261018/f12/r6/round5/plan-history/plan-11-15-review8.md`。
