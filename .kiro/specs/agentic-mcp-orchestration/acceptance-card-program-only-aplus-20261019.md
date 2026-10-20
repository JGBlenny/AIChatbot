# A+ 片：規則與驗收清單（2026-10-19，業主核可、已凍結；r3 的 AP-R10、V13 同日核可）

計畫：`plan-card-program-only-aplus-20261019.md`。決策：DSP-091（分工）、DSP-094（上線範圍含 A+）、DSP-096（順序）。業主 2026-10-19 核可（「核可」，Q1／Q2／Q3 皆選建議），AP-R1～AP-R9 與 V0～V12 自此凍結；之後若要收窄，須重新核可。AP-R10、V13 是 r3 新增（計畫 §9），業主 2026-10-19 核可（「核可 (Recommended)」）後一併凍結。2026-10-20 業主重新核可兩項修訂（原話 7），V8 第 (8) 點與 V9 依第五節判定。

## 一、業主原話

- 原話 1（2026-10-19，第 3 步 A 片開工指示）：「A 片若要修模型主導路徑，須標「過渡修正」並指向 A+／G。」
- 原話 2（2026-10-19，期別片核可時，問題「verifier 新發現：卡片還有效時，使用者重述同樣的值，系統卻回「還需要…」（A 片之前就有這個問題，A2 又多開了一條會走到這裡的路）。要排在哪一片修？」所選選項）：「排進 A+」——「在 A+ 明列成一項：卡片有效、值又相同時，改由程式回「卡片還在，請按確認」，不再交回模型。」
- 原話 3（2026-10-19）：「開始」。回應主視窗的提議：「我現在就開始做 A+ 計畫。流程是盤查、查業界做法、寫計畫、送審，審查通過後交你核可，核可前不動程式。」同一則提議另寫：「其中「reissue gate 放 A+」我會在 A+ 計畫裡照建議先寫進去，要改請說。」
- 原話 4（2026-10-19）：「繼續」（恢復 A+ 計畫工作）。
- 原話 5（2026-10-19，停點回報時，問題「A+ 在 C-M 情境把「可接回的誤問」變成死路。要怎麼處理？」所選選項）：「修 A+ 提議路徑 (Recommended)」——選項說明：「計畫改 r3：(1) 提議的 payload 若是巢狀 {action, payload:{…}} 就先解開一層再合併；(2) 提議合併不到任何欄位、草稿又還在時，改由程式回固定句問「要改成什麼」，不再交回模型（符合 DSP-091 寫入流程歸程式）。送 plan-verifier 審 → 你核可 → 實作 → 重放 C-M → 重跑 E2b 32 場。」
- 原話 6（2026-10-19，問題「模型送了提議、但沒有任何值寫進草稿，而且確認卡還有效（草稿和卡一樣）時，程式要回什麼？（例：使用者說「再出一次確認卡」，或想改但沒被讀到）」所選選項）：「中性句＋同一張卡 (Recommended)」——選項說明：「回「這句沒有讀到要修改的內容，卡片內容沒變；要送出請按確認，要改請按「我要修改」或直接說要改哪一項、改成什麼。」，下面附同一張卡和三顆按鈕，不建新 token。想重看卡的人有卡可按；想改卻沒被讀到的人，也知道「沒改到」。」
- 原話 7（2026-10-20，fresh verifier V12 判 REFUTED（V9 未達）後的停點回報，四題所選選項）：
  - 問題「V9 有兩項沒達成（RS 1/2、make audit FAIL），都不是 A+ 造成的。A+ 要怎麼收？」：「收窄 V9 後收案 (Recommended)」——選項說明：「V9 改成「A+ 不讓 E2a 和 audit 變差」，對照 A+ 前的基準：RS 掉字 A+ 前就有，audit 失敗來自 W2 計畫。RS 掉字另列待查。改完再派一位 fresh verifier 核對，接著進 B 片。」
  - 問題「make audit 失敗的原因是 W2 計畫 r4 第 57 行的路徑少了 rag-orchestrator/。…要修嗎？」：「准修，只改路徑 (Recommended)」——「只把 services/agent/... 改成 rag-orchestrator/services/agent/...，其他字一個不動，改完重跑 make audit 確認通過。」
  - 問題「凍結清單 V8(8) 寫「draft_payload 只在 reissue gate 讀」。…V8(8) 要怎麼處理？」：「改字面 (Recommended)」——「改成「只在 reissue gate 與 AP-7 (a) 比對時讀」，和已核可的 r3 一致。」
  - 問題「E2b 的 W-R3：使用者說「物件不對，是豪宅」，抽出來的值卻跟卡上的一樣，結果程式回了「卡片還在，請按確認」。…」：「交給 B 片處理 (Recommended)」；同題附註「內層 JSON 不設長度上限、卡片有效判定維持較嚴格的寫法」照建議。
- 已核可的片定義（不是業主逐字原話）：目標正本 `architecture-target-20261018.md` §4 A+ 列「出卡只由程式依草稿觸發：收掉模型自己呼叫 `confirm.request` 出卡的路徑，模型改為提出寫入意圖」，服務原則 P1、P4（DSP-091）。

## 二、規則

| ID | 可檢查條件 | 出處 | 讀法、收窄或放寬 |
|---|---|---|---|
| AP-R1 | 開關 on 時（`AGENT_WRITE_DRAFT`、`AGENT_WRITE_LIFECYCLE`、本片新開關三者皆 on），非文件回合、非點選範圍回合中，每一張確認卡（`outcome.state=confirm_pending`）都是程式依草稿發出的 `confirm.request`（payload＝`{action, **to_payload(草稿)}`）產生；模型自己呼叫 `confirm.request` 的參數**不直接**送進 `confirm.request` 執行，因此既不以它出卡，也不以它算缺欄追問。 | 片定義「出卡只由程式依草稿觸發：收掉模型自己呼叫 `confirm.request` 出卡的路徑」 | **收窄**：文件回合、文件暫存有效回合、點選範圍（`SELECT_SCOPE_KEY`）回合、開關 off 時維持現行（理由見計畫 §4.3）。**放寬**：「出卡」之外，模型參數產生的缺欄追問也一併收掉（同一條路徑的另一個出口；A 後 13 次誤問都出自這裡，計畫 §3）。 |
| AP-R2 | 模型呼叫 `confirm.request` 時，參數只當提議：經現行值閘（`_write_draft_gate_value`）合併進草稿，下一步由程式依草稿決定——出卡、缺欄追問、重出同卡（AP-R3）、或既有固定句出口；程式這次不發時，回模型一個封閉的工具結果，⛔ 以模型參數執行。 | 片定義「模型改為提出寫入意圖」 | **讀法（業主 2026-10-19 裁 Q1：「沿用 confirm.request」）**：「提出寫入意圖」＝沿用 `confirm.request` 這個名字當提議管道、語義改為提議；⛔ 另開提議工具或對模型隱藏 `confirm.request`。 |
| AP-R3 | 本回合草稿的動作與綁定卡相同（回合開始已有草稿且沒換動作，或草稿已清而本回合新建同動作草稿），且（a）綁定卡有效：同動作同建立者、未作廢、無收據、DB token（以 `pending_id`＋`session_id` 查）未兌現且剩餘 ≥ 60 秒（以 DB `now()` 判）、以存下的 payload 帶當日重新排版的卡文字雜湊＝`card_sha256`＝DB `summary_sha256`、卡上日期未早於今天；（b）本回合寫進草稿的欄位，正規化後的值與綁定卡相同 ⇒ 程式結束回合：回「卡片還在，請按確認」（本回合使用者句子帶出的值被值閘丟掉時改回 `CARD_UNCHANGED_TEXT`「這次的修改沒有套用，卡片內容沒變；要送出請按確認，要改請按「我要修改」」）＋同一張卡文字、`outcome.state=confirm_pending`、同一個 `pending_id` 的三顆鍵；模型這回合不被呼叫或其輸出丟棄；不新增 token。 | 原話 2 | **放寬**：「回」之外加上重出同一張卡與按鈕——JGB 面板只有最後一則訊息可互動（`jgb-spec-structured-card-draft-20261019.md` §3「只有最後一則訊息可互動」），只回一句話使用者無鍵可按。**讀法**：「卡片有效」讀成上列 (a) 全部成立；不成立時不適用本規則（改走計畫 §4.1 AP-3 的處置）。**前提（業主 2026-10-19 裁 Q3：「也回卡片還在」）**：草稿依 `WF.DRAFT_IDLE_LIMIT`（2）被清掉、卡仍有效時，重述同值同樣適用；⛔ 從卡回填草稿（安全審查 4-1 (iii)、第 3 步 9e），之後再改值時依草稿追問缺欄。換動作的情形沒有同動作綁定卡，不適用。**值被丟掉（業主 2026-10-19 裁 Q2：「改說沒套用」）**：「本回合使用者句子帶出的值」限意圖合併與整句填入（模型提議被丟的值不算——模型參數常夾帶原話沒有的值，算進來會對沒改值的使用者說「修改沒有套用」）；有值被丟、且寫進草稿的值都與卡相同 ⇒ 改回上述句子，其餘行為同「卡片還在」。 |
| AP-R4 | AP-R3 的「值相同」以正規化值比對：比對草稿 `to_payload` 後的值與綁定卡出卡當時的草稿 `to_payload` 值（逐鍵相等，⛔ `str()` 字串比對、⛔ 拿 `confirm.request` 改寫後的 payload 比）。 | 原話 3「reissue gate 放 A+」 | 「reissue gate」指期別片報告 §6 第 5 點：`_write_draft_reissue_gate` 以字串比對草稿與卡片 payload，同期換說法可能被判為有變更。 |
| AP-R5 | 本片改到、但仍由模型主導的路徑，程式碼註解與計畫都寫「過渡修正、不新增 AI 決定權」並指向接手的那一片；本片 ⛔ 新增任何由模型決定程式環節下一步的路徑。 | 原話 1；目標正本 §5 第 7 條 | 原話 1 針對 A 片，本片同樣適用（§5 第 7 條對每一片成立）。 |
| AP-R6 | 每次會呼叫 JGB 的測試（實打、E2a、E2b、整合）前，HANDOFF §2.3 mock 檢查輸出 `True`；不是 `True` 就不跑。 | 業主開工指示「任何會呼叫 JGB 的測試前，先跑 §2.3 的 mock 檢查，必須印 True。」 | 無。 |
| AP-R7 | 不弱化寫入授權：確認 token 綁定（`pending_id`＋`session_id`＋未兌現＋未過期）、範圍閘、可見性檢查、A7 唯一有效卡、DSP-092 advisory lock 都不放寬；同 session 可兌現卡 ≤ 1；開關 off 時行為與改前相同。 | 非業主原話：沿用第 3 步驗收 R8（業主 2026-10-18 核可「納入」） | 無。 |
| AP-R8 | 以同一量尺在本機常駐服務實測（模擬客人多輪＋程式前判＋盲判），E2b 寫入與更正題組不低於基線；既有回歸不退步。 | 目標正本 §1「每片怎樣算完成」 | 無門檻（DSP-087）；不退步＝不低於計畫 §1 基線。 |
| AP-R9 | 本片改動造成過時的現行文件同回合改正；新檔登索引。 | 全域「文件衛生」；目標正本 AR8、AR9 | 清單見計畫 §4.4。 |
| AP-R10 | 開關 on、AP-1 提議分支：(1) 提議 payload 除 `action` 外沒有表單鍵、且 `payload` 鍵是 dict 或可解析成 dict 的 JSON 字串 ⇒ 內層的表單鍵照 AP-R2 合併（內層 `action` 與外層不同 ⇒ 不合併、不觸發；只解一層）；(2) 提議後本回合沒有任何值寫進草稿（`created`／`merged`／`caught`／`filled` 皆不成立）、草稿存在且動作相同、非凍結、本回合程式未觸發、既有出口都不成立 ⇒ 程式結束回合，模型 ⛔ 寫回覆：綁定卡有效且草稿值與卡相同 ⇒ `PROPOSAL_NO_VALUE_CARD_TEXT`「這句沒有讀到要修改的內容，卡片內容沒變；要送出請按確認，要改請按「我要修改」或直接說要改哪一項、改成什麼。」＋同卡、無新 token；否則 ⇒ `PROPOSAL_NO_VALUE_TEXT`（只列表單宣告的欄位標籤）、不出卡、token 表不變。 | 原話 5、原話 6 | **讀法**：(1)「解開一層」＝只解 `{action, payload:{…}}` 這一種形狀、一層；(2)「合併不到任何欄位」讀成本回合沒有任何值進草稿（意圖、整句填入、名稱補值也都沒有）；「回固定句問要改成什麼」：卡仍有效時依原話 6 改回中性句＋同卡（JGB 只有最後一則可互動，只回一句會讓仍有效的卡無鍵可按）——這是**放寬**，業主已裁。**收窄**：凍結回合（收集中、使用者當句是問句）與本回合程式已觸發後的同回合第二次提議，仍回模型封閉結果——前者依 DSP-091 回答使用者的提問屬 AI（也涵蓋計畫 §9.4 待查「問題沒人答」），後者是業主 r2 核可的 AP-1 (4) 行為。**收窄**：模型沒呼叫工具、自寫文字的情形不在本規則（B 片）。 |

## 三、驗收清單

觀察點：本機常駐 `aichatbot-rag-orchestrator`（8100，本片程式、重建後），mock JGB，eval-harness 打真實 `/mcp` `agent.turn`；DB 查詢一律唯讀；原文放 repo 外 `~/jgb-archive/arch-step3-20261018/aplus/`。

| # | 服務規則 | 觀察點（業主使用的那一層） | 證據型態 | 通過條件 |
|---|---|---|---|---|
| V0 | AP-R6 | 每批實打、E2a、E2b、整合測試前跑 mock 檢查 | 指令輸出 | 每批 `True` |
| V1 | AP-R1、AP-R2 | 單元測試，對 `write_forms.FORMS` 每一支動作參數化（⛔ 以動作名分支），並依欄位型別參數化（安全審查 1-4）：假模型呼叫 `confirm.request`，參數含一個不合值閘的值——文字／數字／日期／Email／電話／期別欄位用「不在使用者原話」的值，選項欄位用「值域外」的值，分類欄位用「分類樹查無」的值 ⇒ (a) 出卡時卡上 payload＝`to_payload(草稿)`，該值不在卡上；(b) 欄位不齊時追問句＝依草稿缺欄算出的 `missing_fields_ask_text`；(c) `registry.call` 收到的 payload 扣除照片與物件記憶前處理寫入的鍵後，逐鍵等於 `to_payload(草稿)`，且 `summary`＝`WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY`（模型參數本身 ⛔ 被執行）；(d) 同回合第二次提議 ⇒ 封閉工具結果、無新 token；(e) 模型送的 tool call id 為 `wdprog-<nonce[:8]>`、`docprog-…`、或本回合保留 id ⇒ 仍走提議分支、計入 `tool_calls` 預算，保留 id 記 `tool_call_id_collides_with_reserved`；(f) 一則 message 帶 N 個 `confirm.request` tool_calls ⇒ 預算逐一計 N 次、同則後續呼叫照跑預算檢查；(g) 開關 on、非排除回合、`write_draft` 為 None ⇒ 封閉結果、無 `registry.call`；(h) 選項欄位帶值域內但原話沒說的值 ⇒ 照現行進卡（既有行為的正對照，見第四節）。正對照：開關 off 時同一測試照舊以模型參數出卡。 | pytest 輸出 | 全過 |
| V2 | AP-R1 | 本片 E2b、E2a、實打期間的 `usage_events`（唯讀查詢 `aplus/base_q.py` 同口徑，起點＝重建時間）：出卡回合（`pending_id` 非空且 `final_kind=ask`，排除 `confirm_edit_ask`）分三類計數：帶 `write_draft_program_confirm` ⇒ 程式出新卡；帶 `write_draft_card_still_valid` ⇒ 程式重出同卡（「卡片還在」，另列次數）；兩者皆無 ⇒ 模型路徑出卡。`confirm_missing_fields_ask` 回合全部帶 `write_draft_program_confirm`。查詢腳本以 `base_q.py` 為底、加上第二個標記，存為 `aplus/v2_q.py`。正對照：同一查詢在 A 後時段（2026-10-19 14:54 起）得出模型路徑缺欄追問 17 次；V3 任一案的 trace 套此判定式歸入「程式重出同卡」。 | 查詢與輸出 | 模型路徑出卡 0、模型路徑缺欄追問 0；「卡片還在」次數另列；文件回合與點選範圍回合另列 |
| V3 | AP-R3 | `/mcp` 實打，修繕與延期各 1 案：出卡 → 使用者重述同樣的值 ⇒ 回覆以「卡片還在，請按確認」開頭、含同一張卡文字、`outcome.state=confirm_pending`、`quick_replies` 三顆鍵帶同一個 `pending_id`；DB 無新 token 列；接著按 `confirm_submit:<該 pid>` ⇒ 寫入成功、mock 寫入 1 次。 | 對話紀錄、trace、DB 查詢、mock 計數 | 兩案皆符合 |
| V4 | AP-R3、AP-R7 | 單元＋DB：綁定卡 (a) token 已過期 (b) 已兌現 (c) 已作廢 (d) 重排版雜湊不符（含與 DB `summary_sha256` 不符） (e) 有收據 (f) **`redeemed=true` 且已過期、待確認筆沒有收據**（模擬 F9 收據遺失）⇒ 回 S3 固定句、不出新卡、mock 寫入總數 1 (g) **逾期帳單的延期卡**（出卡時 base＝今天）重述同值 ⇒ 回合不拋例外，當天回「卡片還在」 (h) 同 (g) 但時鐘跨過午夜 ⇒ 回合不拋例外、依 AP-3 (d) 處置 (i) 剩餘 < 60 秒、或卡上日期已早於今天 ⇒ 不回「卡片還在」、依 AP-3 處置 (j) (a)(d) 燒卡後程式呼叫早退（非終結）⇒ #9b 固定句、舊 pid 兌現失敗、寫入 0 (k) 查詢遇 DB 例外、42703、`db_pool is None`、`pending_id` 不合 `_PENDING_ID_RE` ⇒ 判 `missing`、不回「卡片還在」 ⇒ (a)～(k) 都 ⛔ 回「卡片還在」（(g) 當天除外）；依計畫 §4.1 AP-3 處置。(l) **Q3**：出卡後兩句無關話使草稿被清、卡仍有效，使用者只重述部分同值 ⇒ 回「卡片還在」＋同卡、無新 token、無「還需要」；草稿只含本回合欄位（⛔ 從卡回填）。(m) **Q2**：卡後使用者給的分類值對不到分類樹（意圖合併被丟）、其餘值同卡 ⇒ 回 `CARD_UNCHANGED_TEXT`＋同卡、無新 token；對照：只有模型提議的值被丟 ⇒ 回「卡片還在」。正對照：全部成立時回「卡片還在」。 | pytest 輸出、DB 查詢 | 全過 |
| V5 | AP-R4 | 單元：延期卡由「11月那期」出卡（草稿存 `2026/11`，經真實 `confirm_request` 的 payload 形狀）；使用者再說「11月那期」或「2026年11月」⇒ 判為相同（AP-R3 成立、不重出卡）。正對照：改天數 ⇒ 重出新卡、舊 pid 兌現失敗。 | pytest 輸出 | 全過 |
| V6 | AP-R2 | 重放三個已知形狀，各跑 3 次：(a) period 驗證員那場第 1 句（trace `01fd226ac54941158481bb3435290a45`，`period/verifier/chat_2710/`）；(b) W-D2 第 2 句只回物件名（`period/report-period.md` §5.4）；(c) `ra/hits/R3` 首句（trace `13bcf003…`）。 | 對話紀錄、trace | 每次出卡；未出卡的每一次寫到機制層原因（需要意圖原始輸出時，用診斷容器 `w2-diag` 取得），並寫明是否屬本片 |
| V7 | AP-R8 | E2b W＋C 共 32 場（W-R 10、W-D 10、C-* 12），劇本、模擬客人、程式前判、盲判同 A 後重測。 | 報告、逐場 trace | (a) Intercom 解決數 ≥ 計畫 §1 基線 28/32；(b) 每場未解決寫到機制層原因並歸屬；(c) 模型路徑「還需要」次數與基線（11 次／8 場，組成見計畫 §1）並列 |
| V8 | AP-R7 | 第 3 步驗收 9a～9aa 中涉及出卡的條目（9a、9b、9c、9d、9e、9m、9n、9p、9r、9s、9t）在本片程式上重跑；另加（安全審查第 5 節）：(1) **AP-1 路徑版 9b**：綁定卡已被 A2 或 AP-3 燒掉、提議轉成的程式呼叫早退 ⇒ 固定句、舊 pid 兌現失敗、寫入 0；(2) **9q 型**：另一 session 有相同 `pending_id` 的 live 列 ⇒ 本 session `pending_token_state` 判 `missing`、該列不變；(3) **9aa 型**：AP-3 (d) 作廢後模擬他回合以舊狀態存檔 ⇒ 舊 pid 仍兌現失敗；(4) **9g 型**：AP-1 路徑上「修改已送出」⇒ `_write_draft_submitted_exit`；(5) **9i 型**：`readonly_view=True` 下 AP-1／AP-2／AP-3 不動 token 表與 `agent_state`；(6) **9l 型**：`AGENT_WRITE_PROPOSAL=off` 時 9a 仍通過；(7) 提議未發卡的回合 token 表不變；(8) 靜態檢查：`pending_token_state` 只含 `SELECT`、選取欄位不含 `token`、`WHERE` 同時有 `pending_id` 與 `session_id`；`draft_payload` 只在 reissue gate 讀（grep 讀取點），不出現在草稿寫入、`confirm.request` args 與卡排版；`INSERT INTO agent_confirmation_tokens` 仍只在 `tools/confirm.py`（正對照同檔 `UPDATE agent_confirmation_tokens` 命中）。 | pytest 輸出、DB、grep | 全過 |
| V9 | AP-R7、AP-R8 | 回歸：E2a R／D／C／T／RS／DS 各 2/2（基線：A 後 R、C、T、RS 2/2，期別片後 D、DS 2/2）；agent 單元測試與基線 `~/jgb-archive/arch-step3-20261018/period/c5_full_failed.txt`（30 筆）相比無新增失敗；本片改寫的既有測試逐一列出原意圖與改法；golden 通過；`make audit` PASS；開關 off 跑 V1 正對照與 golden。 | 輸出 | 全過 |
| V10 | AP-R5 | grep 本片 diff：每個仍由模型主導、本片有改到的分支都有「過渡修正、不新增 AI 決定權」註解並指向接手片；diff 中沒有新的「模型決定程式環節下一步」分支。 | grep 輸出、diff | 符合 |
| V11 | AP-R9 | 計畫 §4.4 每份文件：grep 與新現況相反的陳述（例：「模型仍可自己呼叫 `confirm.request` 出卡」「model_confirm_ok」作為現行行為），附正對照（同指令命中新陳述）；新檔在 HANDOFF 與目標正本 §4 有登錄。 | grep 輸出 | 無殘留 |
| V12 | 全部 | fresh `verifier` 對照本檔與業主原話 | verifier 報告 | CONFIRMED |
| V13 | AP-R10 | (A) 單元，對 `FORMS` 每支動作參數化：(a) 巢狀提議（內層 dict、內層 JSON 字串兩種）⇒ 內層值經值閘進草稿、程式出卡或依草稿追問，卡上 payload＝`to_payload(草稿)`、記 `write_proposal_unwrapped`；(b) 內層含不合值閘的值 ⇒ 不進卡（同 V1 依欄位型別）；(c) 內層 `action` 與外層不同（另一支看得到的合法動作、`None`、`""`、非字串）⇒ 封閉 `NO_MATCH`；草稿前後完全相同、`created` 為 False、整個回合（含模型輸出之後）無 `write_draft_program_confirm`；(d) 兩層巢狀 ⇒ 只解一層；(e) 頂層已有任何 `form.keys` 鍵（含系統來源鍵）⇒ 不解內層；(f) 提議無值、草稿在、無綁定卡 ⇒ `PROPOSAL_NO_VALUE_TEXT`、`clarifying`、無模型回覆呼叫、token 表不變；草稿帶特殊值時回覆不含任何草稿值或原話片段，只有標籤；無標籤 ⇒ 去掉中間那句的固定句；(g) 同 (f) 但綁定卡已作廢（按過「修改」）⇒ 同 (f)；(h) 提議無值、綁定卡有效且 `to_payload(草稿)`＝卡 `draft_payload` ⇒ 回覆以 `PROPOSAL_NO_VALUE_CARD_TEXT` 開頭（`user_value_dropped` 為 True 或 False 都是；⛔ `CARD_UNCHANGED_TEXT`、`CARD_STILL_VALID_TEXT`）＋同卡、同 pid、無新 token、同記 `write_draft_card_still_valid`；使用者句子「再出一次確認卡」與「物件不對，改成 X」（意圖未抽出）兩種各一案；草稿與卡不同 ⇒ 走 (f)；(i) 綁定卡 `expired`／`redeemed`／`missing`／DB `summary_sha256` 或 `payload_sha256` 不符／live 但剩不到 60 秒／卡上日期早於今天／排版拋 `ConfirmCardError`（跨午夜）⇒ 走 (f)，且無副作用：待確認筆未被改（含 `invalidated`）、`redeem_pending` 呼叫 0 次、`reissue_blocked`／`reissue_burned` 皆 False；(j) 凍結回合、同回合第二次提議、`write_draft is None` ⇒ 照 AP-1 (4) 封閉結果；(k) 開關 off ⇒ 現行行為（正對照）；(l) 內層為深層巢狀（觸發 `RecursionError`）或超大字串 ⇒ 回合不拋例外、視同不解開；(m) 內層夾帶系統來源鍵（`date_expire_before`、`estate_id`、`contract_id`）、照片鍵、`role_id`、原話沒有的 `bill_id` ⇒ 不進草稿也不進卡；(n) 影子回合（`readonly_view`）、文件暫存、點選範圍回合遇到巢狀或無值提議 ⇒ 維持現行、token 表與 `agent_state` 不變；(o) 靜態：解開邏輯只在 `_write_proposal_merge` 內，`_payload_of` 與 r2 相同（diff 為空）。(B) 重放：C-M 形狀（出卡→按「修改」→「問題描述改成：臥室冷氣滴水」）在常駐容器跑 8 次，另在 `w2-diag` 換入本片程式跑 8 次取意圖與主呼叫原文，跑完還原基準並核對 sha256。 | pytest 輸出；對話紀錄、trace、shim 原文 | (A) 全過；(B) 0 次「模型寫回覆時畫面無卡卻說請確認」出自提議分支（`write_proposal_not_issued` 後由模型寫回覆）；每次未出卡寫到機制並歸屬 |

## 四、非目標（相對規則收窄的部分與理由）

- **文件回合、文件暫存有效回合、點選範圍回合**：維持模型自呼路徑。2026-09-01 起 `document_*` 標記只出現 1 次、2026-10-18 起點選範圍回合 1 次（`aplus/baseline-20261019.txt`）；文件回合另有程式先發的 `_document_program_message` 與 DSP-076 的覆寫規則，改動要另審。點選範圍接回原流程屬 A-2。
- **意圖判斷的抽取品質、整句填入只在追問恰好一欄時才填**：屬理解層（F 片／意圖提示）；本片只量 V6 並歸因。
- **程式優先的等待時限不改**（`WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S` 1 秒、`WRITE_DRAFT_PROGRAM_FIRST_WAIT_S` 3 秒）：report-ra §6 第 3 項仍待業主裁；本片讓逾時後模型的提議改由程式依草稿決定，不改等待時間。
- **模型自己寫的追問或「請確認」文字**（未呼叫 `confirm.request`）：屬 B 片（寫入進行中回話全由程式樣板）。
- **修繕分類值比對**（W-R2 k1 的分類對不到）：屬 A-2。
- **選項（`enum`）與修繕分類（`category`）值比對使用者原話**（安全審查 1-4，既有行為）：值閘只查值域與分類樹；本片讓模型參數改經值閘（現況直接進卡），已是收窄，再加原話比對要另定比對規則（選項標籤與口語說法不同形），不在本片。
- **重出卡時的卡外提示行**（未結單、`BILL_MATCH_HINT`）：不重出，理由見計畫 §4.3。
- **對外 MCP 直接呼叫 `confirm.request`** 的行為與工具描述不變。
- **AP-R10 不接凍結回合與已觸發回合**：凍結回合（`asked` 非空且當句是問句）的提議照 AP-1 (4) 回模型封閉結果，因為依 DSP-091 回答使用者的提問屬 AI；本回合程式已觸發後的同回合第二次提議同樣回封閉結果（r2 已核可的 AP-1 (4)）。驗收 V13 (j)。

## 五、修訂（2026-10-20 業主核可，原話 7）

本節取代 V8 第 (8) 點中 `draft_payload` 那一句與 V9 的「E2a 各 2/2」判定；V8、V9 其餘文字照第三節。

| 修訂 | 取代 | 新文字 | 判定 |
|---|---|---|---|
| M1 | V8 (8)「`draft_payload` 只在 reissue gate 讀（grep 讀取點）」 | `draft_payload` 只在 reissue gate 與 AP-7 (a) 比對（`_write_proposal_card_unchanged`）時讀（grep 讀取點）；兩處都只讀不寫，不出現在草稿寫入、`confirm.request` args 與卡排版。 | 全過 |
| M2 | V9「E2a R／D／C／T／RS／DS 各 2/2」 | A+ 不讓 E2a 變差（對照 A+ 前基準）：每組 2/2；未達的場次要同時滿足 (i) 失敗回合沒有 A+ 標記（`write_proposal*`、`write_proposal_no_value*`），(ii) 同一現象在 A+ 前程式的對話紀錄已出現（附路徑），(iii) 列為待查並寫明要什麼證據才能定位。三項都成立 ⇒ 不算 A+ 未達；任一不成立 ⇒ 未達。`make audit` PASS 不收窄（W2 計畫 r4 第 57 行路徑已依原話 7 修正）。 | 全過 |

非目標（相對第三節收窄）：E2a RS 物件名缺「補」的層級定位不在 A+（待查）；W-R3「使用者說不對、抽出值與卡相同仍回卡片還在」交 B 片；內層 JSON 字串不設長度上限；卡片有效判定維持「待確認筆有收據即無效」的較嚴格寫法。
