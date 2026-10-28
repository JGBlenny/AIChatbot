# 「選對紀錄」片計畫：寫入時選對紀錄（同名物件／合約、帳單延期）（2026-10-21，r5 已核可）

> 狀態：r5，業主 2026-10-21「核可」（security-reviewer r1 §11、plan-verifier r1／r2 §12／§13、收尾審查 §14；Q1～Q4 與量尺題業主已裁；收尾審查的 1 條依業主裁示修正、未再送審）。實作中。核可前不動程式。
> 規則與驗收清單：同目錄 `acceptance-pick-right-record-20261021.md`（業主原話、規則 PR-0～PR-11、廣度表、清單 V0～V12；核可時一併凍結）。
> 決策：DSP-107（本片範圍、順序：A-2a 之後、W2 之前；上線範圍含本片）、DSP-106、DSP-103、DSP-091。服務原則：P5（已選定的那筆紀錄）、P1（寫入全程）。

**廣度先答（全域「驗收廣度」第 7 條）**：使用者層 V3／V4 各項 4～9 組資料（同名組全用）× 12 題 × 每題 2 次 × 改前改後兩版；輸入由不讀程式的 fresh 代理依說法類別與描述欄位類別寫好並凍結；改前改後在同一批題上比（改前＝`d1ddc084`）。另重跑 OV 出錯筆的 6 題與 V10 型二 4 句、M0 題組 56 場、OV 48 題 × 2、E2a 6 組 × 2；verifier 另寫 ≥10 個新輸入在兩版實跑。

## 1. 目標

客人要改的是哪一筆，卡上就是那一筆；系統分不出時列候選或追問，⛔ 替客人挑。依據：OV 現在版本錯筆出卡 11/96 場、其中 6 場已寫入（DSP-106）；V10 新輸入型二 3 例（`~/jgb-archive/arch-step3-20261018/overall/report-ov.md` V4、`p8_v10.md`）。規則見規則檔第三節。

**終點指標（現值 → 預期）**：
- OV 題組錯筆出卡：現在版本 11/96 場、其中已寫入 6（`report-ov.md` V4）→ 0（V7 判）。
- V3／V4「選對並出卡」：改前現值由同批凍結題在 `pick-before`（`d1ddc084`）實跑取得（V3／V4 改前欄）→ 逐題配對差 95% 下限 > 0。
- M0 鎖定類別「系統換成別張帳單」（W-D4_k2、W-D5_k2）：改前 `d1ddc084` 已 2/2 解決（`overall/p5_v5_table.md` 第 9 列）→ 預期變化 0，只證不退步。理由：M0 題組要求名稱一字不差（`report-ov.md` 第一段「36/56 場要求名稱一字不差」），測不到本片的缺陷；本片缺陷由 OV 新題組發現，所以本片的正向終點指標用上面兩條，不用 M0。

## 2. 目標形態（業界與第一原理；不看自家現況）

業界原文渲染於 `~/jgb-archive/arch-step3-20261018/pick-right/sources/`（索引 `INDEX.md`，2026-10-21 web-drive 渲染；`a2a/sources/` 為 A-2a 時所渲染）。以下逐句照原文，宣稱只寫原文直接支持的。

**G1 依描述縮小候選：有兩種做法並存，⛔ 業界統一做法。**
- 程式依屬性取回：Apple App Intents `EntityPropertyQuery`："The AppIntents runtime will invoke query comparator mapping closures for each comparator included in the user request … It is then up to you to retrieve entities matching those comparators, using whichever backend … suits your application."（`pick/apple-appintents-entitypropertyquery.txt`；該頁沒寫誰把使用者的話轉成比較子）
- LLM 從回傳清單挑一筆：只有 Salesforce workshop "Agents have the ability to select records out of the response … Can you summarize the first case for me?"（`a2a/salesforce-workshop-standard-actions.txt`），例子是依序位（「第一筆」）挑。Intercom Fin "Fin will read the full contents of the items list and respond with: ..."（`a2a/fin-data-connectors-in-procedures.txt`）是讀清單內容作答，⛔ 是挑選，不作 LLM 挑選的依據。
- **LLM 依屬性描述在同名紀錄中挑一筆：查無業界對應**。Q1 的建議（甲′）屬第一原理推導：描述對到哪一筆是理解問題（DSP-091 理解歸 AI），程式只收候選集內編號並出卡（選定與出卡歸程式）。
- 查無一家寫出「依樓層、金額等描述先篩 → 0 筆或仍多筆各怎麼辦」的完整流程（INDEX R1「查無直接對應」）。

**G2 仍多筆不替使用者假設**：Alexa "Don’t: Make an assumption and select for them when there’s more than one plausible match for what the customer said"（`a2a/alexa-patterns-lists.txt`）；Apple SiriKit Needs disambiguation "when you identify two or more possible results and cannot choose one definitively"（`a2a/apple-sirikit-resolve.txt`）。反例：Apple 同頁 Success "even if it means making an educated guess"。

**G3 候選要能分辨、長清單要有取得方式**：Alexa "Avoid naming list items with similar and shared terms."；"Paginate long lists."；"Don’t: Be tempted to include all possible options in one list."（`a2a/alexa-patterns-lists.txt`）。上限各家不同：Lex 按鈕 "Maximum number of 5 items"（`a2a/lex-api-imageresponsecard.txt`）、Zendesk "displays up to 10 options"（`a2a/zendesk-carousels-ai-agents.txt`）。**同名時要顯示哪些欄位：查無業界規則**，只有例子（Zendesk "date ordered, order number"）。

**G4 單筆推定沒把握要確認、值要驗**：Apple SiriKit Needs confirmation "you can choose a single value, but are not completely confident that it is the correct value"；Rasa "The custom action can accept or reject the new slot value."（`pick/rasa-validating-slot-values.txt`）。查無一家寫「單筆結果先比對使用者先前講過的屬性」（INDEX R3）——本片 PR-4 的「比對客人講的金額」屬第一原理推導：客人已給的值與系統選的列矛盾，即是 G4「not completely confident」的可程式判定特例。

**G5 確認卡要讓人看得出選錯**：NN/g "A confirmation dialog must restate the user’s request … with specific information that allows users to understand the effects of their action. Without identifying details it’s useless to ask users to confirm a request"；"make it likely that the user would recognize a mistake"（`pick/nng-confirmation-dialog.txt`）；Alexa `Dialog.ConfirmIntent` "Be sure to repeat back all the values the user needs to confirm in the prompt."（`pick/alexa-dialog-management.txt`）；UiPath "shows the user the input parameters it plans to use"（`pick/uipath-agent-tool-confirmation.txt`）。帳單／租約卡該印哪些欄位：查無業界原文，依 G5 第一原理取「能讓客人看出換錯筆的欄位」。

## 3. 差距（自家現況；讀碼於 2026-10-21，盤查 `agentic-mcp` 38/38）

| # | 現況（可 grep 的符號） | 對應目標 |
|---|---|---|
| D1 | 寫入候選列在 `write_candidates.py` `minimize_row` 裁成：合約 `id,title,date_end,estate_id,is_history`、物件 `id,title,status`；給 AI 的資料段與給人的清單都走 `jgb2.py` `_ROW_PROJECTORS`（合約只印編號、名稱、到期日；物件只印編號、名稱、狀態）。fixture 同名組 26007／40303 只差「40303 已有合約」，67651／68007 差縣市與樓層，35214／39931 差狀態與租金——這些欄位 AI 與客人都看不到 | G1、G3（PR-1、PR-2） |
| D2 | 打字描述只有三條出路：AI `pick_id`、整句純數字、重列（`runtime.py` `_write_candidates_typed`）；程式端無依描述比對 | G1（PR-1） |
| D3 | 畫面列 `CANDIDATES_SHOWN_MAX`＝5 筆，其餘只附「還有其他筆，不在其中請講編號」；「基隆好房」同名合約 6 份 | G3（PR-3） |
| D4 | 延期 `tools/confirm.py` `_resolve_bill_by_period` → `_bills_of_estate`：`get_bills(keyword=物件名)`，比對帳單 title；只取第一頁；不解析物件、不看 `estate_id`。fixture 帳單 64 張中 4 張標題不含物件名（705879、990001～990003），查不到；標題含該字串的別物件帳單會混入 | PR-6 |
| D5 | `_filter_bills` 只依月份（`_row_in_month`）與未繳篩；剩一張即 `_fill_bill_fields` 出卡；`BILL_DUE_EXTEND_FORM` 無金額欄，客人講的金額無處存放；「M/D 到 M/D」計費期間 `bill_period.py` 解析不了 | G4（PR-4） |
| D6 | 延期卡 `confirm_card.py` `_render_bill_due_extend` 只印帳單編號、原到期日、起算日、延後天數、新到期日——無金額、標題、計費期間、物件 | G5（PR-5） |
| D7 | 候選選定後 `_apply_bill_pick` 不再對照客人先前講的金額或期間；AI 選 769253 而非 769252 時，資料段沒有計費期間（`_project_bill_row` 只印到期日與金額） | G4、G5（PR-4） |
| D8 | 物件記憶 `runtime.py` `_apply_estate_carry_to_confirm_args` 補 `estate_name` 時延期卡不印物件，客人看不出沿用 | G5（PR-5） |
| D9 | `get_bills`（`jgb_system_api.py`）不能依 `estate_id` 或金額篩；可依 `contract_ids`。物件的合約可由 `_viewer_contract_rows`（`/contracts/status-overview`，限有效且最新）取得 | PR-6（做法限制） |

## 4. 路徑（設計）

開關 `AGENT_PICK_RIGHT`（預設 on；off＝A-2a 行為逐位相同，供回退與 off-run 等價測試）。只動寫入路徑；唯讀查詢的 `_ROW_PROJECTORS` 輸出 ⛔ 改（G 片範圍、B 片測試釘住）。

### 4.1 型二：帳單先解析物件、再依物件取帳單（D4、D9 → PR-6）

0. **身分前置（S-F1）**：新路徑三支呼叫（物件、合約、帳單）之前，比照 `_bills_of_estate`：`role_id` 與 `user_id` 皆非空且過 `jgb2._identity_gate_ok`；缺任一 ⇒ 0 次出向、回空（走現行缺欄出口）。每支呼叫一律帶 `viewer_user_id=user_id`。
1. 延期缺 `bill_id` 時，先以既有 `_resolve_estate_rows`（帶 viewer）把 `estate_name` 解成物件；同名多筆走 A-2a 物件候選（客人先選物件）：封閉表 `CANDIDATE_TYPES[(bill_due_extend, "estate_name")]` 加 `TYPE_ESTATE`，新增延期的物件選定處理——以 `_estate_by_id`（帶 viewer）重驗後才取該物件帳單，帳單階段的候選一律來自已選物件（S-F8）。解不到走現行缺欄出口。
2. 該物件的帳單＝（a）`_viewer_contract_rows` 中 `estate_id` 相符的合約，**逐合約各查一次** `get_bills(contract_ids=<單一編號>, viewer_user_id=…)`（`/bills` 只吃單一 `contract_id`，S-F7）；`get_bills` 需先能轉送 `page`（現由 `**kwargs` 吞掉），逐頁取，迴圈上限以次數計（每合約 ≤3 頁、總計 ≤`WRITE_CANDIDATES_MAX` 20 張），⛔ 只看 `has_more`；（b）現行 `keyword` 查詢結果中 `estate_id` 相符者。兩者以帳單編號聯集。每列斷言 `contract_id` 在所查集合內（a）且 `estate_id` 等於解出的物件，不符一律丟掉（修正別物件混入）。
   - ⚠️ 真 JGB `/bills` 沒有 `keyword` 篩選（DSP-109 爭議：jgb2 `BillApiController@index` 各分支 0 命中，替身有）。真機上（b）等於「該成員看得到的帳單第一頁」再以 `estate_id` 篩，所以本片在真機的主路徑是（a）；（b）只是補漏，⛔ 拿替身上（b）的成效代表真機。
3. 帳單或**合約**清單有下一頁卻達上限時，視同「可能還有」，不做「唯一一張」判定（改列候選）；合約清單 `has_more` 為真時，物件列的「有無有效合約」顯示「—」，⛔ 顯示「無」（S-F3）。

### 4.2 型二：比對客人講的金額與計費期間（D5、D7 → PR-4）

1. `BILL_DUE_EXTEND_FORM` 加欄 `said_amount`（整數，使用者原話；過既有 `_number_in_texts` 值閘：原話沒有這個數字就丟）與 `said_range`（封閉語法「M/D 到 M/D」或「M月D日到M月D日」，由程式比照 `_period_gate_value` 從使用者原話解析後與模型值比對，只存程式解析出的值；`bill_period.py` 新增解析；解析不到回 `None`，⛔ 猜）。鍵名刻意與卡上顯示的系統值不同（S-F2）。物件或期別在草稿中變動時清掉 `said_amount`／`said_range`（S-F4）。
   - 已知限制（S-F4）：同句有多個數字時，模型可能把錯的數字填進 `said_amount` 且過值閘，使「≥2 張」縮成「1 張」而出錯筆卡。防線是卡上印**帳單本身**的金額與計費期間供客人核對（4.5），並在 V4 放同句 ≥3 個數字的題目量它。
2. 期別篩完後：有 `said_amount` 就再篩 `_bill_amount(row) == said_amount`；有 `said_range` 就再篩 `date_start`、`date_end` 的月日相符。
3. 出口：剩 1 張且（客人有講的值都相符）→ 出卡；≥2 張 → `pick:bill` 候選；0 張而客人有講金額或期間 → 說明「這個物件該期沒有 N 元的帳單」並列該物件該期（無期別則全部）帳單為候選（業主裁 Q3）。
4. 候選選定後（`_apply_bill_pick`、AI `pick_id`）：客人先前講的 `said_amount`／`said_range` 與選中那張不符時——打字選定（AI 回編號）不符則不出卡、重列候選；按鈕選定不符時照客人按的出卡，卡上加一句「您先前說 N 元，這張是 M 元」（期間同理）並印帳單本身的值供核對——PR-4 的例外，業主裁 Q4。

### 4.3 型一：讓比對描述的一方看得到可分辨欄位（D1、D2 → PR-1、PR-2）——業主裁 Q1＝甲′

- **建議（甲′，延續 DSP-103 的甲）**：AI 看候選清單回「指哪一筆的編號」，程式只收候選集內編號（現行）；改的是 AI 與客人看得到的欄位。新增寫入候選專用投影（`write_candidates.py`），`minimize_row` 多留：物件 `district`／`city`、`floor`、`rent`、`status`、是否有有效合約（由同一次 `_viewer_contract_rows` 推得）；合約 `date_start`、`date_end`、`rent`、`status`；帳單 `title`、`date_start`、`date_end`、`date_expire`、金額、狀態。⛔ 帶 `to_user_*`、承租人姓名。
- **替代（乙，DSP-107 字面）**：AI 從客人的話抽出條件（縣市區、樓層、租金、狀態、有無合約、日期），程式依條件在候選集篩；0 筆或仍多筆列候選。代價：條件種類要逐一定義型別與比對規則，開放描述（「沒過期那份」「靠海大那間」）要再加型別；DSP-103 已否決過此路（理由同上）。
- 兩案共同：程式只接受候選集內的那一筆（PR-10）；AI 回 `none` 或條件篩後仍多筆 → 重列並在前言說出「依您說的○○仍有 N 筆」（G3 Alexa preamble）。

### 4.4 同名全部看得到（D3 → PR-3）——業主裁 Q2＝10 筆

- 建議：畫面上限 5 → 10（Zendesk 10；JGB 面板按鈕數上限未查，實作前查 jgb2 `ConfirmCard.vue`／候選元件），候選集仍 ≤20；超過 10 筆時保留固定句，並因 4.3 的欄位已在資料段，客人可用描述選到第 11 筆以後。

### 4.5 確認卡印可分辨欄位（D6、D8 → PR-2、PR-5）

- 延期卡加（PR-5）：物件（名稱＋編號）、帳單標題、金額、計費期間。
- **顯示值一律由程式從系統列導出（S-F2）**：卡上要印的鍵全部宣告為系統欄位（加進預檢 `derived_keys`），由 `_fill_bill_fields`／預檢在**所有路徑**上覆寫——含模型自帶 `bill_id`、寫入生命週期開關 off、自呼路徑；進來時先無條件丟掉模型帶的同名鍵（比照 `payload.pop("estate_id", None)`）。物件行由帳單列的 `estate_id` 經 viewer 反查得出，與草稿物件名不一致 ⇒ 不出卡。卡上金額＝帳單本身金額，⛔ 印客人講的 `said_amount`。
- **自由文字欄位把關（S-F5）**：卡上新增的 JGB 自由文字（帳單標題、物件名）比照 `confirm_card._closed_value`：`sanitize_data_piece(v) != v` 或超長 ⇒ 印「—」；寫入候選新投影保留逐列 `sanitize_data_piece` 與 `wrap_tool_data` nonce 包裝。
- 型一的卡（PR-2 要求，非選配）：修繕卡物件行加縣市區＋樓層；建合約卡「物件」行加縣市區＋樓層；補開帳單卡「合約」行加起訖日。皆由 `confirm_card.render` 從程式查得的列產生（測試 `test_c5_card_answer_is_the_formatter_text` 約束），⛔ 由模型或 hint 補。

### 4.6 標記、文件

- 新標記：`pick_right:amount_mismatch`、`pick_right:range_mismatch`、`pick_right:estate_first`（進 `TurnTrace.violations`，供量測分組）。標記與 log 只記型別或碼，⛔ 記金額、名稱、期間（S-F11，同 `_resolve_bill_by_period` 現行紀律）。golden 情境開關固定 off（同 A-2a 做法），逐位不變。
- 文件：`docs/api/jgb2-web-assistant-integration.md`「寫入時的候選選擇」節、`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` 延期段、目標正本 §4 狀態欄、HANDOFF。

## 5. 偏離目標形態的取捨（照實寫）

1. **候選與卡的欄位由第一原理選**：業界無規則（G3、G5 查無），取 fixture 同名組實際彼此不同的欄位；風險是真 JGB 物件列欄位與 fixture 不同——fixture 註記為團隊 20151 真實擷取（遮罩），但 `get_estate_status` 回傳欄位在真 JGB 未逐欄驗：V0 讀 jgb2 `git show origin/master:app/Http/Controllers/External/EstateApiController.php` 的 `formatEstate` 逐欄對（⛔ 連正式機）；缺欄時印「—」，不壞。
2. **帳單改由合約查、不要求 JGB 加 `estate_id` 參數**：現況比較好做、且不擋上線；代價是歷史合約上的帳單查不到（N4）。另提 JGB 需求為後續。
3. **型二的金額比對是第一原理推導**（G4 查無業界對應）。
4. **畫面上限取 10、不分頁**：Alexa 建議分頁、Siemens 建議 2～3 個；分頁要新增入向值與狀態，10 筆內配合描述可選，先不做。停點：V3 若出現「目標在第 11 筆以後且描述選不到」。
5. **按鈕選定與先前描述不符時照按鈕出卡並明說不符（4.2-4，業主裁 Q4）**：客人看過印有金額的清單後明示選了這張（G2「不替使用者假設」的前提是使用者沒明示）；屬 PR-4 的例外。

## 6. 交業主裁的題目

2026-10-21 業主已裁（規則檔原話 7）：Q1 甲′、Q2 10 筆、Q3 說明並列候選、Q4 照按的出卡並明說不符；另收尾審查量尺題裁「改前用新規則重跑」（§14）。各題原文如下。

- **Q1 型一由誰比對描述**：建議（甲′）AI 看帶可分辨欄位的清單回編號、程式只收候選集內編號；替代（乙）AI 抽條件、程式篩。⚠️ 主會話更正：DSP-107 決定欄寫「依 AI 理解出的描述由程式篩」是主會話先前建議的字句，與 DSP-103 否決的「AI 抽條件由程式篩」相衝，當時未指出。DSP-107 另寫「範圍與做法由該片計畫定」；選甲′ 則於收案決策列寫明取代 DSP-107 該句。
- **Q2 畫面筆數**：建議 10 筆＋候選集 ≤20；替代：維持 5 筆加「看更多」分頁按鈕；全部 ≤20 筆列出。
- **Q3 金額或期間對不上時**：建議說明對不上並列該物件該期帳單為候選；替代：只追問「您說的是哪一張」不列。
- **Q4 客人按鈕選了與先前所說金額或期間不符的帳單**：建議照按的出卡、卡上加「您先前說 N 元，這張是 M 元」（PR-4 的例外，核可後於 PR-4 旁註記）；替代：同打字選定，不出卡、重列候選（PR-4 字面）。
## 7. 執行切片與驗收順序

1. security-reviewer（唯讀）→ 處置寫入本計畫 → plan-verifier → 業主核可。
2. 實作（`executor`，單一寫者）：4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6；每步單元測試（V1）。
3. 題組（V2）：fresh 代理產題並凍結（與實作平行，代理不讀 `rag-orchestrator/services`）。
4. 建改前容器 `pick-before`（`d1ddc084` 工作樹，埠 18105）；改後重建常駐；V0。
5. V3、V4（兩版）→ V5 → V6、V7（兩版，皆 DSP-108 規則；改前在 `pick-before` 重跑 M0 56 場與 OV 48 題 × 2）→ V8 → V9、V10 → 報告 → V11 fresh verifier。

## 8. 停點（只用結果條件）

- 改後任一場錯筆寫入（PR-7）⇒ 停，查根因後才續跑。
- 呼叫 JGB 前 mock 檢查不是 `True` ⇒ 不跑。
- security-reviewer 或 verifier 提出 P0／P1 ⇒ 依全域規則暫停該片。
- V6／V7 判定退步 ⇒ 不收案，交業主。
- 實作要動 DSP-091 程式環節以外的分工（例如讓模型決定出卡）⇒ 停，交業主。
- 新路徑任一出向呼叫沒帶 `viewer_user_id`，或缺 `user_id` 仍送出 ⇒ 停（S-F1）。
- V10 白名單等值斷言的正對照沒抓到 ⇒ 測試無效，停（S-F6）。
- 收案報告與上線說明必寫：真 JGB `/bills` 的篩選語義（keyword 無、`user_id` 為承租人篩選、`contract_id` 搭 viewer）只對到 jgb2 原始碼、未在真機實測（DSP-109、S-Q-b）；⛔ 拿替身成效宣稱真機。

## 9. 回退

`AGENT_PICK_RIGHT=off` 回到 A-2a 行為（off-run 等價測試保證）；程式回退＝git revert 本片 commit。

## 10. 用量回報

收案時回報子代理 token 加總與模型呼叫費用（不設上限，停點只用結果條件）。

## 11. security-reviewer r1 處置（2026-10-21；報告為子代理回報，主會話已複核下列標「已核」者）

結論：無 P0／P1；P2 兩條、P3 七條、P4 兩條、待查五條。

| 編號 | 級 | 摘要 | 主會話複核 | 處置 |
|---|---|---|---|---|
| S-F1 | P2 | 物件→合約→帳單新鏈，`get_bills` 帶 `role_id`＋`contract_ids` 即放行、`viewer_user_id` 非空才送；計畫未寫身分前置 | 已核：`jgb_system_api.get_bills` 入口條件與 `if viewer_user_id:`；`confirm._bills_of_estate` 有 `if not role_id or not user_id` | FIX：§4.1-0、§8；V10 加缺 `user_id` ⇒ 三支 0 次出向的負向測試 |
| S-F2 | P2 | 卡上新欄位若取 payload，模型可預塞；延期 payload 非封閉鍵 | 已核：`runtime._apply_estate_carry_to_confirm_args` docstring「保留鍵只有 `today`」 | FIX：§4.5 顯示值由系統列覆寫、丟模型同名鍵、客人講的值改鍵名 `said_*`；V1 加模型自帶顯示鍵的測試 |
| S-F3 | P3 | 合約清單只看第一頁，唯一判定與「有無合約」可能錯 | 未另核（`_only_valid_contract_of_estate` 註解為報告引文） | FIX：§4.1-3 |
| S-F4 | P3 | 金額值閘只證數字在原話；計費期間值閘未寫 | 已核：`_number_in_texts` 僅比完整數字 token（摘要時已讀） | FIX：§4.2-1 程式解析 `said_range`、變動即清、已知限制寫明；V4 加同句 ≥3 數字題 |
| S-F5 | P3 | 卡上新增自由文字不加包裝進 dialog | 未另核 | FIX：§4.5 sanitize 等值＋限長；V1 加測試 |
| S-F6 | P3 | V10 只列禁止鍵，分辨力不夠 | 未另核 | FIX：V10 改白名單等值＋正對照 |
| S-F7 | P3 | `get_bills` 只吃單一合約、不轉送 `page` | 已核：`params["contract_id"] = contract_ids` 與其上註解 | FIX：§4.1-2 |
| S-F8 | P3 | 延期加「先選物件」層未寫選定通道與重驗 | 未另核 | FIX：§4.1-1 |
| S-F9 | P3 | §5.1 說列入 V0、V0 沒有 | 已核：清單 V0 只有 md5 與 mock | FIX：§5.1、V0 |
| S-F10 | P4 | 純數字整句可能撞候選編號 | — | DEFER：機率低（需恰好等於候選集內編號）；後續片 |
| S-F11 | P4 | 新顯示值落地 `pending_confirm` 與 dialog；標記與 log 勿記值 | — | FIX：§4.6 標記與 log 只記型別或碼；落地 `pending_confirm` 屬現行確認卡同一機制，不另處置 |
| S-Q-a | 待查 | 真 JGB `/bills` 有無 keyword | 已核：jgb2 origin/master、origin/preview（2026-10-15）、master、assistant_agent_demo 的 `BillApiController.php` 皆 0 命中 `keyword`；正對照 `ContractApiController`、`EstateApiController` 命中 | 轉事實：記 DSP-109 爭議；§4.1-2 註記真機主路徑為（a）；§8 收案必寫未實測 |
| S-Q-b | 待查 | 新路徑要不要傳 `user_id`（真機為承租人篩選） | — | 實作時與 `viewer_bill_row` 傳參一致，V1 斷言兩處同形；真機語義列 §8 未實測 |
| S-Q-c | 待查 | fixture 有無「合約看得到、帳單看不到」的列 | — | V10 前置：實作者查 `fixture_data/*vendor4.json` 的 `bill_visibility`；沒有就補一列測試用 fixture 或報告寫明此負向測試分不出對錯 |
| S-Q-d | 待查 | 真 JGB 帳單 `title` 會不會含承租人姓名 | — | 上線前經 `jgb-prod-readonly` 遮罩抽樣（業主核可後）；本片 ⛔ 以 fixture 代表真機，收案寫明未查 |
| S-Q-e | 待查 | `confirm.request` 回傳的完整帳單列是否寫進 trace | — | V10 前置：實作者 grep trace 組裝（`turn_context` `tool_call_records`）；若完整列進 trace，候選路徑改存縮減列 |

## 12. plan-verifier r1 處置（2026-10-21，REVISE 4 條）

| 編號 | 級 | 摘要 | 主會話複核 | 處置 |
|---|---|---|---|---|
| PV-1 | P2 | Q4 把「只做延期卡」稱 DSP-107 字面，實則違反 PR-2 | 已核：`.claude/decisions/DSP-107.md` 型一「候選與確認卡印可分辨欄位」 | FIX：§4.5 型一卡改為 PR-2 要求；r1 Q4 撤回 |
| PV-2 | P2 | 按鈕選定不符照出卡，與 PR-4 衝突且未列業主題 | 已核：§4.2-4 與 PR-4 條件 | FIX：改列 Q4 交業主；PR-4 讀法欄註記待裁 |
| PV-3 | P2 | PR-2／PR-3／PR-6 後半在使用者層無觀察項；編號可讓 PR-2 預設通過 | 已核：V3、V4 判定式 | FIX：PR-2 註明編號不算；V3 加清單與卡的可分辨欄位、同名全部可達；V4 加別物件帳單 0 混入 |
| PV-4 | P2（wording-only） | G1 拿 Fin 當 LLM 挑選依據，原文是讀清單作答 | 已核：`fin-data-connectors-in-procedures.txt` 原句 | FIX：§2 G1 改寫，並寫「依屬性描述挑：查無業界對應」 |
| PV-待查 | — | 標題不含物件名的 4 張帳單的合約是否在 `status-overview` 回傳內 | 已查：`assistant_demo_vendor4.json` 中 705879／990001／990002／990003 的合約皆 `active=1`、`is_newest=1`（替身 `status-overview` 只篩這兩欄）；另見 709743 的合約 84981 不在 fixture 合約表，路徑（a）找不到、只靠（b）keyword——真機（b）無效（DSP-109） | V2 前置：產題前以 viewer 實查這 5 張帳單能否經（a）或（b）取得，取不到的不出「可被選到」題並寫明 |
| PV-P3 | P3 | V6 寫 26 題，OV 報告寫 M0 29 題 56 場 | 已核：`m/sessions.json` 56 列（W 20、K 20、A 12、其他 4） | FIX：廣度表 V6 改為 29 題、56 場原樣 |

## 13. plan-verifier r2 處置（2026-10-21，REVISE 6 條；第二次自動 REVISE，處置後送一次收尾審查）

| 編號 | 級 | 摘要 | 主會話複核 | 處置 |
|---|---|---|---|---|
| PV2-1 | P2 | 未寫終點指標現值與預期；M0 鎖定類別改前已 2/2 | 已核：`overall/p5_v5_table.md` 第 9 列「延期_換錯帳單 … 2/2」 | FIX：§1 加終點指標三行；M0 預期 0 變化附理由，正向指標改用 OV 錯筆出卡與 V3／V4 配對差 |
| PV2-2 | P2 | M0 場次寫錯（應 W-D4_k2、W-D5_k2） | 已核：`m/report-m0.md`「系統換成別張帳單 \| 2（W-D4_k2 … W-D5_k2 …）」 | FIX：V6 與上位驗收方式註記改兩場逐場判 |
| PV2-3 | P2 | V1 把「測試全過」放寬成基準 9 筆 | 已核：目標正本 §1「測試全過」 | FIX：V1 照字面，有既有失敗照實報「未達字面」並附集合比對（同 OV P5b） |
| PV2-4 | P2 | PR-0 多個條件無清單項觀察 | 已核：PR-0 列與 V0 原條件；`runtime.py` `DEFAULT_MAX_COMPLETION_TOKENS = 2000` | FIX：V0 加他窗 4 份 sha256 前後同、`origin/main` 前後同、輸出上限 grep、核可前程式 0 改動 |
| PV2-5 | P2（wording-only） | PR-5 旁註指向不存在的待裁題 | 已核 | FIX：旁註改為擴充理由，不宣稱待裁 |
| PV2-6 | P2 | PR-5 物件行無驗收項 | 已核：V4 原條件 | FIX：V4 加延期卡物件名稱與編號＝帳單列 `estate_id` 反查 |
| PV2-P3 | P3 | S-Q-d 無清單項；PR-7 出處為提問句 | — | DEFER：S-Q-d 需正式站唯讀抽樣，須業主另核，收案報告寫明未查；PR-7 已有原話 2 支撐，不改 |

## 14. 收尾審查（plan-verifier r3，2026-10-21）：REVISE 1 條，交業主

| 編號 | 級 | 摘要 | 主會話複核 | 處置 |
|---|---|---|---|---|
| CR-1 | P2（substantive） | 改後量測依 DSP-108 只計打字句，V7 改前基準 OV「現在」96 場與 V6 基準 51/52 是舊規則（按鈕計入）量的，比較兩邊量尺不同 | 已核：`report-ov.md` 第 35 行「8 句用完或未送結束標記 21（其中 7 場…確認卡待按、4 場最後一步是按鈕…）」；DSP-108「自下一次量測起適用」 | 業主裁「改前用新規則重跑」：V6、V7 改前基準改為 `pick-before` 以 DSP-108 規則重跑 M0 56 場與 OV 48 題 × 2；規則檔廣度表下加回合上限規則行。依業主裁示修正，未再送審 |
| CR-待查 | — | V4（iii）在 fixture 有無「標題含該物件名、屬別物件」的帳單 | 已查：`assistant_demo_vendor4.json` 有 16 張（例：760897 屬 68007、標題含 67651 的名稱——即 M0 W-D4_k2 寫錯的那張）；正對照：自家物件名命中 60/64 | 結案：V4（iii）分辨得出對錯 |

