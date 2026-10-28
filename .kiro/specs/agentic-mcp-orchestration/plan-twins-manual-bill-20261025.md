# 「雙胞胎與手開帳單合約」片計畫：同名物件看得出差別、手開帳單列出全部可開帳合約（2026-10-25，r5 草稿）

> 狀態：r5 草稿（r1 經 security-reviewer 唯讀審查，處置見 §11；r2 經 plan-verifier 第 1 次 REVISE 6 條，處置見 §12；r3 經第 2 次 REVISE 7 條，處置見 §13；r4 經收尾審查 REVISE 2 條〔含 1 條 substantive〕，處置見 §14，**修了、未再審**），暫停交業主裁定（⛔ 標 READY）。**業主 2026-10-25 改以推進上線為主（DSP-115）：本片暫停至上線後**；恢復時從 §14 與 §6 Q-A、Q-B、Q-C 接續，並依 DSP-115 只修會改變下一步的發現。下文「核可後記 DSP-115」改為恢復核可時另記新決策編號。核可前不動程式（核可前逐檔 md5 `~/jgb-archive/arch-step3-20261018/twins/v0/pre-approval-md5.txt`，621 列）。
> 規則與驗收清單：同目錄 `acceptance-twins-manual-bill-20261025.md`（業主原話 1～6、規則 TM-0～TM-12、廣度表、清單 V0～V12；核可時一併凍結）。
> 決策：DSP-112（本片來源、範圍、順序：F12 之後、W2 之前）、DSP-110、DSP-108、DSP-091；核可後記 DSP-115（業主 2026-10-25 四題裁定；取代 `plan-assistant-11-items-20261014.md` §3f 1b「缺 `contract_ref` 時以 `estate_name` 解析該物件唯一一份有效合約」與 A-2a「該物件多份有效合約」的有效合約限制。F12 原話 8 是 F12 FR-1 的判分裁定〔合約目標經所屬物件只在該合約為有效合約時算找到〕，屬 F12 凍結紀錄、本片 ⛔ 改；r1 起草時主會話曾把它寫成手開帳單的產品規則並據此向業主出題，見 §12 R-0）。待裁爭議：DSP-113、DSP-114。服務原則：P5（已選定的那筆紀錄）、P1（寫入全程）。

**廣度先答（全域「驗收廣度」第 7 條）**：使用者層 V3 同名物件 4／4 組 × 14 題、V4 手開帳單 8／15 組（抽法見清單）× 12 題，皆每題 1 次 × 改前改後兩版（模擬客人自由對話）；V4b 更正合約 5／5 組 × 6 句 × 1 次 × 兩版（腳本送凍結句）。輸入由不讀程式的 fresh 代理依說法類別寫好並凍結；改前改後在同一批題上比（改前＝`twins-before`，即核可前程式）。終點重量（改後 1 次；改前＝現值，同程式已量）：F2 41 場、F3″ 40 句、F3′ 50 句、F5 12 句、F4 12 句、E2a 6 組 × 2 輪；M0 題組 56 場 × 2 版（改前現值未量，P0 量）。verifier 另寫 ≥10 個新輸入在兩版實跑。每一次執行的決定、規模理由與成本見 §7.1。

## 1. 目標與終點指標

**目標**：客人講的是同名物件中的哪一間、要開帳單的是哪一份合約，卡上就是那一筆；系統分不出時列候選或追問，⛔ 替客人挑（原話 2、3；DSP-112）。

**目標文件**（兩份，量法全列）：(1) 目標正本 `architecture-target-20261018.md` §1「每片怎樣算完成」（上位驗收方式：M0 同題組同量尺重測、既有回歸題組不低於前一基線、測試全過、`make audit` PASS）；(2) F12 r5 凍結清單 `acceptance-name-lenient-f12-r5-20261022.md` 中決定能否收案的使用者層門檻 F2、F3″、F3′（錯筆卡＝0）、F5、F4、F6（DSP-112：本片即處理 F12 剩下的錯筆；F12 斷路器報告 `f12/cmd/endpoint/breaker-report.md` 亦以這些量法為終點）。F2 的 V3/V4 13 場、F3′ 比例為目標文件標「只報」的列，不計終點、照列。

**終點指標**（全域「終點指標」第 1、2 條；受測物＝常駐 `aichatbot-rag-orchestrator`，映像 `sha256:1aa81f09…`，`runtime.py`、`write_candidates.py`、`tools/confirm.py`、`write_forms.py`、`name_match.py` 容器內 md5 等於工作樹（`f2e/header.txt`、`f12/cmd/endpoint/f6_rerun.out` 檔首），HEAD `720f0bf7`＋未提交的 F12 改動＝核可前工作樹，逐檔 md5 `twins/v0/pre-approval-md5.txt`）。「前兩片」＝同一目標（F12 終點）的 r6 片（終點未量，依規則計 0）與指令式片（r5 量測 → 指令式片收案量測）；以下路徑除另註外皆在 `~/jgb-archive/arch-step3-20261018/`：

| 量法 | 門檻 | 現值（來源） | 本片預期 | 前兩片實際變化（來源） |
|---|---|---|---|---|
| F2 41 場錯筆卡／錯筆寫入 | 0／0 | 4／3（`f12/cmd/endpoint/f2run/f2e/score/f2_summary.txt`，2026-10-25 16:46） | ≤1／≤1：contract-2、interject-2、V3C-2 轉 0；V3C-8 不在範圍（非目標 N1） | r6：未量計 0；指令式片：4／3 → 4／3＝0（`breaker-report.md`） |
| OV 28 場含查不到出口／其中未解決 | ≤38%／≤18% | 7/28／1/28（同上） | 不退步（過門檻） | r6：未量計 0；指令式片：6/28／0/28 → 7/28／1/28（判變異，同上報告） |
| F3″ (2) 含揭露句找到 | ≥85% | 33/40＝82.5%，**未過門檻**（`f12/cmd/endpoint/f3f4_score_ep.out`「含揭露句找到」，`run_ep.out` 2026-10-25 15:58，映像同上） | 不變（本片不針對；物件候選多一欄可能影響 AI 選號，以重量確認） | r6：未量計 0；指令式片：35/40 → 33/40（−2，同上報告「記變異」） |
| F3″ (1) 講名稱那回合列出含目標候選 | ≥85% | 27/34＝79.4%，**未過門檻**（同上「分子/分母」） | 不變 | r6：未量計 0；指令式片：30/35 → 27/34（同上報告） |
| F3″ 寬鬆路徑每句候選 ≤5／寬鬆直接出卡／錯筆卡／錯筆寫入 | 0 句超過／0／0／0 | 0／0／0／0（`f3f4_score_ep.out` after「候選>5」「寬鬆直接出卡」「錯筆卡」皆空；錯筆寫入：`f3f4_run_ep.py` 出卡（`confirm_pending`）即停、不送確認，F3″ 場次沒有寫入可發生，錯筆卡 0 即錯筆寫入 0） | 0／0／0／0 | r6：未量計 0；指令式片：0、0 → 0、0＝0（`f12/cmd/endpoint/stop-report-f11.md`「F3″ 錯筆卡、寬鬆直接出卡」列；r5 值見 `f12/r5/report-r5.md` F3″ 列） |
| F3′ 錯筆卡（F3′ 唯一通過條件） | 0 | 0（同上「F3′ 錯筆卡」空） | 0 | r6：未量計 0；指令式片：0 → 0（同上報告 F3′／F5／F4 變化 0） |
| F5 候選增量／查不到出口句數 ≤ 改前／錯筆卡／寬鬆直接出卡 | ≤⌈0.2×12⌉＝3／≤改前（＝1，`run/f3f4_r4/f12before`）／0／0 | +2（過）／**2，未過門檻**（`f3f4_score_ep.out` after「F5 查不到出口句數」2、f12before 同鍵 1；判分腳本的「F5 門檻」鍵只判候選差、不判查不到，F12 收案報告亦只報候選差）／0／0（「F5 錯筆卡」空、「F5 寬鬆直接出卡」0） | 候選差、錯筆卡、寬鬆直接出卡不變；查不到不針對、預期不變（2） | r6：未量計 0；指令式片：候選差 +3 → +2；查不到 1 → 2（r5 `f12/run/f3f4_score_r5.out` 改後同鍵 1），**退 1、本計畫 r4 收尾審查前無人報過**；錯筆卡、寬鬆直接出卡 0 → 0 |
| F4 三組共同：錯筆卡／寬鬆直接出卡／候選 ≤5 且全屬本 viewer／回覆不含使用者原話／同草稿連續兩回合查不到 | 0／0／是／0／0 | 0／0（「F4 每句回合分類」after 12 句皆單回合 `notfound` 或 `cands`、無出卡 ⇒ 推得）／候選 >5 無、他團隊候選 0（「F4 候選>5」空、「F4 他團隊候選>0」0；全屬本 viewer 為替身上判，同 r4 讀法）／0（「F4 回顯≥4字」空）／0（「F4 連續兩回合查不到」0） | 不變 | r6：未量計 0；指令式片：「同」（`breaker-report.md` F3′／F5／F4 列） |
| F4 他團隊組：他團隊紀錄出現在候選 | 0 | 0（「F4 他團隊候選>0」0） | 不變 | 同上 |
| F4 不存在名稱組：每句結果屬允許之一（列候選或 (甲) 查不到；(甲) 後只補欄位回合只重問名稱；(乙) 不列候選且追問名稱欄） | 每句皆屬 | 首回合皆屬：每句為 `cands` 或 `notfound`（同上分類鍵）；「(甲) 後只重問名稱」**未觸及**——腳本出查不到即停（`f3f4_run_ep.py` 停止條件含 `NOT_FOUND`），無後續回合可判 | 不變 | 同上 |
| F4 只講位置組 | 只套三組共同條件，候選句數另報 | 同三組共同列 | 不變 | 同上 |
| F6 E2a 照字面全 2/2 | 全 2/2 | R、C、T 2/2；DS、RS 2/2；D 1/2，**未過門檻**（R、D：`f12/cmd/endpoint/f6_rerun.out` 16:05～16:10，該次於 C 前重啟失敗停止；C、T、RS、DS：`f12/cmd/endpoint/diag_f3pp/run_full.out` 16:25～16:33；兩檔檔首 `runtime.py` md5 皆 `663515418c…`，與受測物同；`e2a_analyze.out` 是依這兩次的 `e2a/*.log` 算出的判分） | 不變（本片不針對 D 的延期天數路徑） | r6：未量計 0；指令式片：RS 0/2 → 2/2、D 2/2 → 1/2（同上報告「記變異」） |
| M0 題組判分場解決數、K 組（目標正本 §1） | 改後 ≥ 改前 | **現值未量**（最近一次 44/52 是選對紀錄片程式，⛔ 當現值）；量法：P0 在 `twins-before` 以 DSP-108 規則跑 56 場（`pick-right/run/` 同腳本、`p5_score.py` 同口徑） | 不退步 | r6、指令式片皆未量 M0 ⇒ 計 0（`report-f12-close.md` 無 M0 列） |
| 單元測試失敗集合（目標正本 §1） | ⊆ 基準 | 9 筆，與 OV 基準 `overall/ov-unit-failed.txt` 逐行相同（`twins/v0/unit-pre.txt` 檔首記指令、時間、HEAD；`unit-pre-failed.txt`） | 不增 | r6：未量計 0；指令式片：9 failed → 9 failed（`f12/cmd/p4/unit-full-fix1.log`「9 failed, 6581 passed」），變化 0 |
| `make audit`（目標正本 §1） | PASS | PASS（`twins/v0/audit-pre2.txt`，檔首記指令、時間、HEAD 與受測物 md5 比對結果） | PASS | r6：未量計 0；指令式片：PASS → PASS＝0（`f12/cmd/p4/make-audit5.log`「OVERALL: PASS（2026-10-25）」） |

F3″ (1)(2)、F6 D 與 F5 查不到出口句數（2 對改前 1）現值已低於 F12 門檻：本片不以它們為目標（DSP-112 的範圍是 F2 剩下的錯筆），預期不變；F5 查不到是 r4 收尾審查才發現的未過項，要不要併入本片由業主裁（§6 Q-C）；收案重量若仍低於門檻照實報，⛔ 當本片成敗，但計入斷路器（下段）。

**斷路器狀態**：同一目標（F2 錯筆）前兩片（r6、指令式片）實際變化皆 0，已觸發；業主對斷路器報告裁「改題」（F12 原話 56，規則檔原話 2），本片即依該裁定開立。本片若 F2 錯筆仍 4／3，即第三片 0，收案時交業主斷路器報告。

**核可時請業主明示**：M0 現值核可前未量，P0（動程式前）在改前容器量（全域第 3 條；§6 Q-A）。

## 2. 目標形態（業界與第一原理；不看自家現況）

業界原文 2026-10-25 以 web-drive 渲染於 `~/jgb-archive/arch-step3-20261018/twins/sources/`（索引 `INDEX.md`）；同名辨識沿用 `a2a/sources/`、`pick-right/sources/` 既有渲染檔。以下照原文，只寫原文直接支持的。

**G1 列給人選的選項要分得出來**：Alexa "Avoid naming list items with similar and shared terms. Names of items in a list should be verbally distinct."（`a2a/sources/alexa-patterns-lists.txt`）。Alexa 同頁 "Follow up to disambiguate if the customer makes a selection that could indicate more than one of the options"。**同名紀錄該補哪個欄位：查無業界規則**（選對紀錄片 G3 已查）；本片取「合約紀錄」屬第一原理：fixture 唯一的全同組 40303／26007 的真實差別就在合約（40303 有 2026-06 已結束合約、26007 從未有合約），F2 兩場客人也正是用「名下沒有任何合約的那筆」「沒有合約的」來描述（`f2e/convs/s9f983c06`、`s238c29a1`）。

**G2 真的分不出時問一個窄問題、不替人猜**：Google "To resolve ambiguity, ask the user a narrow-focus question."（`pick-right/sources/google-cd-questions.txt`）；Apple SiriKit "if you find two contacts with the same name during resolution, you might populate the customIdentifier property of each INPerson object with a unique string"（`a2a/sources/apple-sirikit-resolve.txt`：同名靠唯一識別碼）；Alexa "Don’t: Make an assumption and select for them when there’s more than one plausible match"（`a2a/sources/alexa-patterns-lists.txt`）。現行分不出句（請講編號或直接點選）即此形態（TM-2）。

**G3 租約結束後仍可對它開費用**：
- Rentec Direct："After the move-out date, your tenant will be removed from the property but will still appear on the tenant page as inactive. This will give you an opportunity to view their ledger and make any last changes for credits/charges before archiving that tenant ledger."（`twins/sources/rentec-moving-out-tenant.txt`）
- DoorLoop："Any rent charges that were missed during the expired lease period will need to be manually posted for the affected months"（`twins/sources/doorloop-when-lease-expires.txt`）；"Allow tenants to access their portal to pay overdue charges after their lease ends or they move out."（`twins/sources/doorloop-portal-after-lease-ends.txt`）
- 手開費用掛在租約／租客帳上：DoorLoop "For manual charges, use the Post Charge button on the lease Transactions tab."（`doorloop-lease-transactions-overview.txt`）；Revela "Charges can be added to tenant ledgers by navigating to the user’s profile and selecting Actions > Add Charge."（`revela-adding-charges.txt`）
- 未查完：DoorLoop「已結束租約仍可加交易」那篇（9031758、7170382）headless 開回不存在頁；「預設只列啟用、可切換顯示全部」（BMC、Infor）一頁逾時、一頁只渲染 4 字元——⛔ 引用（INDEX「未查完」）。
- 自家產品現況（⛔ 業界，作產品規則依據，業主已採，原話 3 Q1）：jgb2 master 網頁開帳單 `Estate::formatTenantData` 列該物件全部 `actualContracts()`（`is_newest=1`）中 `active=1` 者，無狀態過濾；`BillService::requestTargetToBillWithSave` 存檔只查 `active`；`BillTargetBlock.jsx` `isExpiredContract`（`date_end <= today`）讓已結束排後（讀碼 `~/dev/work/jgb2/dev5`，master、工作樹乾淨）。

**G4 更正與換題分開處理**：Rasa "pattern_continue_interrupted for interruptions. pattern_correction for corrections."（`a2a/sources/rasa-patterns.txt`）；"Correction (repair pattern): Update and correct previously stored conversational information."（`a2a/sources/rasa-conversation-patterns.txt`）。由誰判斷是更正還是換題：Rasa 指令產生器 "It outputs a sequence of commands that represent how the user wants to progress the conversation."（目標正本 §2.1 引 `sources-repair/rasa-llm-cmdgen.txt`）＝理解層（DSP-091 理解歸 AI）。

## 3. 差距（自家現況；讀碼於 2026-10-25，盤查 `agentic-mcp` 48/48）

| # | 現況（可 grep 的符號） | 對應 |
|---|---|---|
| D-1 | 物件候選的「有效合約」旗標只在延期路徑寫上：`tools/confirm.py` `name_early_lookup` 的 `annotate = action == BILL_DUE_EXTEND_ACTION`、`missing_name_lenient` 與 `name_lenient_rows_for_ids` 同條件；報修、建合約、手開帳單的物件候選沒有 `has_valid_contract` 鍵 ⇒ `write_candidates.py` `_pr_estate_row` 印「有效合約 —」。F2 contract-2、interject-2 兩列即全同（`f2e/convs/s9f983c06`、`s238c29a1`）。⚠️ 本計畫起草時主會話曾對業主說「—」是因合約清單有下一頁，讀碼後更正：fixture 合約 29 份、每頁 50，沒有下一頁；原因是上述只在延期才寫旗標 | G1（TM-1） |
| D-2 | 即使寫上，`_annotate_valid_contract` 只算 `not is_history` ⇒ 40303（只有已結束 84201）與 26007（無）同為「無」，仍全同 | G1（TM-1） |
| D-3 | 合約查詢 `tools/action.py` `_viewer_contract_rows` 不帶 `per_page`、不翻頁（jgb2 `ContractApiController` `DEFAULT_PER_PAGE = 50`、`MAX_PER_PAGE = 200`、吃 `page`；`jgb_system_api.py` `get_contracts` 有 `per_page`、沒有 `page`）；團隊合約 >50 份時第一頁取不全。`keyword` 只比合約 `title`，且合約標題格式不一（`get_contracts` 查無 fallback 註解「重慶北137-503」），⛔ 用物件名當 keyword 取該物件合約 | TM-4 |
| D-4 | 手開帳單講物件：`_valid_contracts_of_estate` 排除 `is_history`；≥2 份才列候選、恰 1 份帶入。V3C-2（`s11a1aa80`）：49871 的有效合約只有 80304 ⇒ 直接帶入，客人要的 6 月已結束 83231 無從選；sdc09781b：40303 只有已結束 84201 ⇒ 缺欄「合約」，客人最後放棄 | G3（TM-3） |
| D-5 | V3C-2 第 6 句「這份是一整年的，不對，我要的是6月那份已結束的合約，幫我換一份」（手開帳單確認卡待決）回「還需要：問題描述」：trace `2732c1aec0044fa9b68670e08bbbd4ed` 的 `usage_events.decision_snapshot` violations 含 `write_intent_call`、`write_draft_action:repair_create`、`write_draft_keys:`（空）、`estate_carry_applied:estate_name`、`confirm_missing_fields_ask` ⇒ 意圖判斷回了 `repair_create`、未抽到欄位，程式改建報修草稿並沿用物件、追問報修必填。意圖呼叫當下看不看得到待決的手開帳單卡：未查明（`cmd-diag2` 意圖記錄只存回覆不存輸入；2026-10-25 對 `cmd-diag2` 重送同 7 句，路徑在第 1 句即分岔、未出卡，未重現，`twins/diag-pd/`） | G4（TM-5） |
| D-6 | V3C-8（`s7c8f4035`）：兩份合約都有列；84908（status 64、bit_status 3151、`is_history_done=1`）只標「歷史完成（已歸檔）」，客人講「已發送點退那份」對不到，按了 85894（DSP-114）——非目標 N1 | — |

## 4. 路徑（設計）

開關 `AGENT_TWINS_CONTRACTS`（預設 on；off＝核可前行為逐位相同，供回退與 off-run 等價測試）。只動寫入路徑；唯讀查詢 `_ROW_PROJECTORS` ⛔ 改。

### 4.1 物件候選列印「合約紀錄」（D-1、D-2、D-3 → TM-1、TM-2、TM-4、TM-9）

1. 新增 `_estate_contract_rows(api, role_id, user_id)`（`tools/action.py`，與 `_viewer_contract_rows` 同檔）：`get_contracts(role_id, viewer_user_id=user_id, per_page=200, page=p)`，p＝1..5，`has_more` 為假即停；回 `(rows, complete)`。`jgb_system_api.get_contracts` 加選用 `page`（不帶＝params 與改動前逐位相同，同 `per_page` 先例）。身分前置比照 `_bills_of_estate`：`role_id`、`user_id` 皆非空且過 `jgb2._identity_gate_ok`，缺 ⇒ 0 次出向、合約紀錄「—」。翻頁語義（S-T7）：只有最後取到的那頁 `pagination` 是 dict 且 `has_more is False` 才算 `complete`；`pagination` 缺或形狀不對 ⇒ `complete` 為假；任一頁沒查成 ⇒ `jgb2.UpstreamFailure`（呼叫端照現行沒查成處理）；跨頁依 `id` 去重。每回合暫存（S-T5）：結果以 `(role_id, user_id)` 為鍵存在本回合暫存（比照 `tools/confirm.py` 寬鬆比對情境的 `early_lookups`：每回合一份、只活在本回合、⛔ 落地；該情境物件只在帶 `name_lenient` 時才有，故本片於 runtime 每回合另建一份傳入三個呼叫點），同一回合 ⛔ 重翻；呼叫端拿不到暫存 ⇒ 照查（每次仍 ≤5 頁），V3／V4 報實際次數。只留對得到物件的列（S-T1）：取回後立即只保留 `estate_id` 屬於本次物件候選（或手開帳單已定物件）的列，其餘當場丟棄，⛔ 進 log、⛔ 進暫存、⛔ 進回傳。`get_contracts` 加 `page` 時順手改正 docstring 中「mock `_contracts_index` 未對此參數設防」的過時說明（S-T8）。
2. `_annotate_valid_contract` 改為 `_annotate_contract_record`：同一次 `_estate_contract_rows` 推每列物件的 `{open: 未結束份數, ended: 已結束份數, last_end: 已結束中最晚 date_end}`；`complete` 為假或沒查成 ⇒ `None`。形狀封閉（S-T6）：`contract_record` 只能是 `None` 或恰好三鍵 `{open: int, ended: int, last_end: str|None}`，由程式組；形狀不合 ⇒ 當 `None`，⛔ 放任何合約列欄位。已結束＝`date_end` ≤ 今天（台北時區，同 jgb2 `BillTargetBlock.jsx` `isExpiredContract`，只看 `date_end`）。
3. 呼叫點擴到所有寫入動作的物件候選：上列三處的 `action == BILL_DUE_EXTEND_ACTION` 條件改為「物件候選」（`cand_type == TYPE_ESTATE`），`_name_candidates_result` 的物件候選與 `_pr_resolve_bill` 照用同一支。
4. `write_candidates.py`：`PICK_RIGHT_ROW_KEYS[TYPE_ESTATE]` 以 `contract_record` 取代 `has_valid_contract`（白名單等值測試同步改，V10）；`_pr_estate_row` 印 TM-1 的五種字樣；`PR_INDISTINCT_TEXT` 判定照舊比非編號欄位（含新欄），全同才印（TM-2）。
5. 給 AI 的候選資料段與給人的清單同一份投影（現行），AI 看得到合約紀錄 ⇒ 客人講「沒有合約那間」時 AI 回對的編號（TM-8：AI 只回候選集內編號）。

### 4.2 手開帳單列出全部可開帳合約（D-4 → TM-3、TM-4）

1. `_valid_contracts_of_estate` 改為 `_billable_contracts_of_estate`：來源改用 4.1 的 `_estate_contract_rows`，取 `estate_id` 相符者，⛔ 再排除 `is_history`（`/contracts/status-overview` 本已限 `active=1`、`is_newest=1`＝jgb2 網頁同一範圍）。
2. 排序：未結束在前、已結束在後，各自依 `date_start` 由晚到早（同 jgb2 網頁 `BillTargetBlock.jsx`「1."簽合約日期"越後排前面 2.狀態"合約中"排前面」；該處比較函式只回 `-1`、相同日期次序未定義，本片同日期再依合約編號由大到小，使結果固定）。
3. 出口：≥2 份 ⇒ 合約候選（現行 `_name_candidates_result`，`TYPE_CONTRACT`）；恰 1 份且 `complete` ⇒ 帶入（卡上照現行印合約期間）；0 份 ⇒ 現行缺欄「合約」；`complete` 為假 ⇒ 列已取到的並附現行「可能還有」句，⛔ 判恰 1 份。
4. `_only_valid_contract_of_estate` 的其他呼叫者（延期等）⛔ 改語義：保留原函式給它們用，手開帳單改呼新函式。
6. 給模型的工具說明同步（plan-verifier r2 B6）：`tools/action.py` 手開帳單 `estate_name` 欄說明現為「系統以該物件唯一一份有效合約為準（該物件有多份或沒有有效合約時會回報缺少合約，請向使用者問清楚是哪一份合約）」，與新行為相反；改為描述現行為（列出該物件全部可開帳合約供選、恰一份才帶入），⛔ 含任何物件或合約名稱。同檔其他進模型提示的字串一併 grep「有效合約」核對（executor 獨占 `tools/action.py`）。
5. 選定端同一判準（S-T2）：手開帳單的「列候選」「清單內選定」（`_prepare_closed_action` 中 `pick_estate[1] == _wc.TYPE_CONTRACT` 那段）「清單外打編號」（`pick_matches_name` 的合約分支）三處，對手開帳單動作共用同一支判準函式（可開帳＝這位成員看得到＋`_estate_of_contract` 成立）：只對手開帳單拿掉 `is_history` 這一條，`_estate_of_contract` 物件歸屬檢查保留；其他動作（延期等）照現行排除 `is_history`。兌現端 `manual_bill_create` 的 `_visible_contract_by_id` 不改（已結束合約仍 `active=1`、`is_newest=1`，照常通過；審查已查）。

### 4.3 手開帳單更正合約不轉成報修（D-5 → TM-5）

先查根因再修（單一未知缺陷，主會話照 `kiro-debug`）：
1. 重現：在診斷容器（`cmd-diag2` 同碼，另加意圖呼叫**輸入**記錄的診斷映像 `twins-diag`，⛔ 進正式程式）走到手開帳單確認卡待決（V4b 的前置），送**診斷句組**，記意圖呼叫輸入與回覆。診斷句組＝V3C-2 原第 6 句（`twins/diag-pd/conv1`）＋主會話寫的開發句 ≤6 句（存 `twins/diag/dev-sentences.json`，P2 開始前算 sha256 記入報告）；⛔ 用 V4b 凍結句診斷（plan-verifier r2 B5：拿來診斷的輸入不撐宣稱，F12 原話 10 同一規則）。P2 開始前比對兩組句子逐字無重疊。
2. 預列分支：
   - (a) 意圖呼叫輸入不含待決的卡（動作）⇒ 把現行「進行中的建立」行（`write_forms.draft_injection_text` 的輸出，只含標籤）也放進確認卡待決回合的意圖呼叫——理解層輸入，符合 G4「由理解層判斷更正或換題」與 DSP-091。⛔ 把合約標題、期間等業者自由輸入的值拼進系統句或 schema 說明（S-T4，維持 `write_intent_system_prompt` 現行「⛔ 含任何使用者值」約定）；若證據顯示意圖呼叫需要已選合約的內容，只能走 `write_candidates.data_piece_text`（nonce＋`sanitize_data_piece`）資料段。
   - (b) 輸入含待決的卡，但 schema 沒有「更正待決卡的合約」的出口（意圖只能回同動作欄位或別的動作）⇒ 在確認卡待決回合的意圖 schema 補「改合約」指令，沿用選定後指令式 `pick_target_rule` 的 `name`／`clear` 形狀，由程式驗證後重列 4.2 的合約候選。安全條件（S-T3）：只在手開帳單確認卡待決時附上；指令只收 `name`／`clear`，⛔ 收 AI 給的編號，`name` 須通過 `_name_said_in_message` 與 `sanitize_data_piece(name) == name`（同 `runtime.py` `_write_candidates_cmd_effect`）；重列候選**之前**走現行作廢路徑（`wd.rechoice` 那支的 `redeem_pending`、`entry["invalidated"] = True`），作廢失敗 ⇒ `reissue_blocked`、不重列。
   - 其他（例：輸入與 schema 皆具備而模型仍判換動作）⇒ 停（§8），交業主；⛔ 加詞表或「換一份」特例。
3. 修完以 V4b 量（fresh 代理寫、P1 凍結、未用於診斷；改前同批並列，量尺自證）。

### 4.4 文件與紀錄（收案回合）

- `docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` F12 節末「⚠️ 已知未處理（DSP-112，下一片）」改寫為本片現況正文（文件衛生第 2 條）；HANDOFF 整份重寫；DSP-115 記業主四題裁定（取代 11 項計畫 §3f 1b 與 A-2a 的有效合約限制，見標頭）；`.claude/MAP.md` 登錄本片計畫與清單。
- 改完驗：grep 舊句「只取該物件的有效合約」「唯一一份有效合約」「有效合約 —」「`_valid_contracts_of_estate`」在現行文件與 `rag-orchestrator/services/agent/` 給模型的字串 0 命中（正對照：同指令命中新句）；舊函式名在保留給延期等呼叫者的程式內出現者逐筆列出、確認不是手開帳單路徑。

## 5. 偏離目標形態與取捨

- D-1′ 同名時補的欄位只取「合約紀錄」，⛔ 動態挑欄：理由同 DSP-110（動態挑選補片撤回，無實際事件支撐）；本片的實際事件只有 40303／26007 一組，差別正是合約。
- D-2′ 全同時沿用「請講編號或直接點選」並保留按鈕（G2 Google 是問窄問題、⛔ 給按鈕）：業主原話 3 Q2 選此；拿掉按鈕的代價是客人不知道編號時卡住（選項說明）。
- D-3′ 翻頁上限 5 頁 × 200 份＝1,000 份：超過即「—」與不判恰 1 份，安全側；理由：有每回合暫存後，合約清單每回合 ≤5 次上游呼叫（整回合逾時 30 秒、每次 10 秒，`mcp_facade._DEFAULT_AGENT_TURN_TIMEOUT_S`、`JGBSystemAPI.timeout`）；真 JGB 團隊合約數未查（⛔ 連正式機），收案報告寫明此限制，V3／V4 報告列單回合上游呼叫數與延遲（只報）。
- D-6′ 真 JGB 團隊擁有者看到的合約範圍（S-T1，jgb2 端既有問題）：jgb2 `ContractApiController@index` 帶 viewer 時改走 `Contract::queryThisUser`，其 `roleType === 'owner'` 分支沒有任何 role 條件（`where('user_id'…)` 已註解）⇒ 擁有者查到全庫合約；網頁端各呼叫點先自加 `where role_id` 再呼叫（正對照 `ContractController.php` 中 `->where($searchRoleIndex,$roleId)` 後接 `Contract::queryThisUser`）。主會話 2026-10-25 讀碼確認：jgb2 本機 `master` `2c2420be` 與 `origin/master` `638e1edd`（2026-10-23）這三檔 diff 為空；正式機部署版未查（⛔ 連正式機）；未實跑重現。本片影響：擁有者身分下合約紀錄極可能恆為「—」（等於現況、⛔ 錯值），且每回合取回別團隊含個資的合約列進記憶體（§4.1 已限只留對得到物件的列、當場丟棄）。mock 以 `_foreign_team` 依 role 隔離，測不到 ⇒ TM-9 的真 JGB 部分收窄為「未驗」；上線前提交業主（§6 Q-B）。修正在 jgb2 端（`index` 不論有無 `user_data` 一律 `where('role_id', $roleId)`，`VisibleScope::contractIdsQuery` 同），不在本片。
- D-4′ 「已結束」只看 `date_end ≤ 今天`、組內依 `date_start` 由晚到早，皆同 jgb2 網頁（業主 Q1「跟 JGB 網頁一樣」）；唯一偏離是同日期時依合約編號固定次序（網頁未定義）。兩者都只影響排序與合約紀錄的字樣，⛔ 影響可否開帳。fixture 實況：29 份合約中 `is_history=1` 的 19 份 `date_end` 皆 ≤ 2026-10-25，另有 3 份 `is_history=0` 但 `date_end` 已過（84972、85894、89296）⇒ 依網頁算作已結束。
- D-5′ 真 JGB 手開帳單不開放（TM-7）：jgb2-req #21 未開通，與本片無關的外部前提（原話 3 Q4）。

## 6. 業主待裁（核可時一併回覆）

- Q-A：M0 現值核可前未量，P0（動程式前）在 `twins-before` 量——同意？（全域「終點指標」第 3 條要求明示；E2a 現值已在同程式量過〔R、D：`f12/cmd/endpoint/f6_rerun.out`；C、T、RS、DS：`f12/cmd/endpoint/diag_f3pp/run_full.out`〕，r2 寫「未量」有誤，已改）
- 核可時請確認兩處讀法（規則檔 TM-1、TM-3 讀法欄）：(1) 物件列合約紀錄的字樣與 Q2 說明不同——加了份數、「已結束合約（2026-06）」改為「已結束 N 份（最近到期 YYYY/MM/DD）」、「從未有合約」改為「無」（程式只看得到啟用中、最新版、這位成員看得到的合約，無法斷言「從未有過」）、另加查不全時的「—」；要照 Q2 原字樣請說。(2) 手開帳單只有 1 份可開帳合約時直接帶入、卡上印合約期間、由客人在確認卡確認或改（沿用現行；Q1「全部列出讓他選」的另一讀法是只有 1 份也列成候選讓客人按）；要改請說。
- Q-B（資安審查 S-T1 新事實，涉及原話 3 Q4 的上線範圍）：物件候選「合約紀錄」在真 JGB 上線，要不要以 jgb2 先修好擁有者合約範圍為前提？
  - 建議：以 jgb2 修正為前提（本片照做、mock 驗收；真 JGB 等 jgb2 修正後再開 `AGENT_TWINS_CONTRACTS`）。理由：擁有者身分下改了也多半印「—」（效果≈現況），卻要每回合把最多 1,000 份別團隊含電話、Email、地址的合約列拉進記憶體；最小權限優先。
  - 另一選項：照原 Q4 上線，接受擁有者看到「—」、別團隊列只在記憶體當場丟棄、不落地；非擁有者成員（經理人、大房東）照常生效。
- 範圍外、需業主知道（S-T1 待查 Q3）：同一根因也落在**已上線**的唯讀合約查詢（`tools/jgb2.py` `query_contracts` 的三支 `get_contracts(..., viewer_user_id=user_id)`；回傳列沒有 `role_id`，AIChatbot 端無從事後濾）：若正式機 jgb2 與 master 相同，團隊擁有者在站內幫手查合約可能看到別團隊合約。本片不改（N4／N7）；建議另開 jgb2 需求單（`jgb2-api-requests.md` 屬他窗檔，由業主決定誰寫）並以 jgb-prod-readonly 確認正式機版本。
- Q-C（r4 收尾審查新事實）：F12 終點 F5「查不到出口句數 ≤ 改前」現值 2 對改前 1，**未過**；r5 時 1 對 1，指令式片退 1，F12 收案報告與斷路器報告都只報候選差、沒判這項。本片要不要併入？
  - 建議：不併入，照 F3″、F6 D 同法處理——收案照實報未達、計入斷路器；另在下一片前先找出是哪一句、哪個機制（本片 P0 順手逐句定位，只讀紀錄、不改程式）。理由：本片範圍是同名物件與手開帳單的錯筆；F5 是「沒講名稱」路徑，與本片改動不同段，併入要另起目標形態與驗收。
  - 另一選項：併入本片，P2 一併查根因；計畫須補 F5 的目標、差距、修法與驗收，再送審。
- 已裁（原話 3）：Q1 可開帳範圍、Q2 同名做法、Q3 附帶範圍、Q4 上線範圍。

## 7. 執行順序

| 步 | 內容 | 驗收 | 停點 |
|---|---|---|---|
| P0 | 核可時重算 `rag-orchestrator/` 逐檔 md5，須等於 `pre-approval-md5.txt`；常駐映像打標籤 `aichatbot-rag-orchestrator:twins-before`、起 `twins-before`（18111，compose 複製 `f12/cmd/compose-r5c.yml` 改名與埠）；兩容器 mock 檢查；改動檔備份到 `twins/v0/pre-impl/`；在 `twins-before` 跑 M0 56 場（改前現值，§7.1 E-1）；本機 jgb2 開發庫若在跑，唯讀查 `contracts.role_id <> estates.role_id`（以 `estate_id` 相接）筆數記入報告（security-reviewer 待查 Q2），沒在跑照實寫「未查」、⛔ 為此起環境；業主 Q-C 若裁不併入：讀 `f12/cmd/endpoint/run/f3f4_r5_r4in/after/F5-*` 與 `run/f3f4_r4/f12before/F5-*` 紀錄，逐句定位哪幾句出現查不到出口、記入報告（只讀紀錄、不跑、不改程式；定位工具須先以判分檔的 2／1 當正對照） | V0 | md5 不同、mock 不印 True ⇒ 停 |
| P1 | fresh 產題代理（不讀 `rag-orchestrator/services`、`twins/diag-pd/`、`twins/diag/`、F2 對話）依規則檔說法類別寫 V3 14 題、V4 12 題、V4b 6 句（V4b 為單句更正，「分多句」不適用，其餘 6 類各 ≥1，一句可屬多類）；凍結 sha256 | V2 | 真值核對不過 ⇒ 退回重寫一次 |
| P2 | 4.3 根因重現（主會話，§7.1 E-9；用診斷句組，⛔ 用 V4b 凍結句） | — | 分支屬「其他」⇒ 停、交業主 |
| P3 | 實作 4.1、4.2（`executor`，一次寫清的 brief：本計畫 §4.1～4.2、規則檔 TM-1～TM-4、TM-8、TM-9、V1、V10；獨占 `tools/confirm.py`、`tools/action.py`、`write_candidates.py`、`jgb_system_api.py` 與新測試檔）；executor 端的暫存以選用參數接收（不傳＝照查）；收件後主會話依 P2 分支實作 4.3，並在 `runtime.py` 每回合建暫存傳入三個呼叫點（`runtime.py`／`write_forms.py`，與 executor 檔案不重疊） | V1、V10 | executor 兩次不過 ⇒ 主會話接手 |
| P4 | 單元測試、`make audit`、golden、off-run 等價測試、特規掃描 | V1、V8、V9 | 失敗集合變大 ⇒ 修或停 |
| P5 | 重建常駐容器、md5、mock；V3、V4、V4b 兩容器（E-2～E-4）；終點重量 V5、F3″／F3′／F5／F4、V6、V7 改後（E-5～E-8） | V3～V7 | V3／V4／V4b 改後錯筆卡 ≥1 ⇒ 停、查機制，一次修正後只重跑：先前沒過的場、修正碰到的場（依據＝改了哪個函式或提示詞、對到哪些場，逐場寫）、新加的；修正改到共用提示詞或意圖 schema 等判不出影響範圍者，寫明改了什麼、為何對不到場，才整項重跑；仍有錯筆 ⇒ 交業主 |
| P6 | fresh `verifier`（brief：業主原話、規則檔路徑、清單、本計畫、diff 路徑） | V11 | REFUTED ⇒ 依全域修復規則（≤5 輪） |
| P7 | 報告 `twins/report-twins.md`、§4.4 文件、DSP-115、HANDOFF | V12 | — |

### 7.1 每一次執行：回答的決定、規模、成本（全域「測試選擇」第 1～3 條）

成本來源：模擬客人每場時間＝F2 41 場 71 分（`f12/cmd/endpoint/f2run/f2e/batch_driver.log` 16:46:23 → 17:57:04，每場約 1.7 分）；模擬客人 token＝F2 41 場 666 千（`f12/report-f12-close.md` 用量節「F2 模擬客人 A 波 362,427＋B 波 303,405」，每場約 16 千）；M0 每版 598 千（`pick-right/usage_session_tokens.txt` 的 `sim before m0b2` A0～D1 八筆加總）；腳本跑法時間＝F3″ 40 句 67 秒、F3′／F5／F4 74 句 128 秒（`f12/cmd/endpoint/run_ep.out`）、E2a 6 組 × 2 輪 約 16 分（R、D：`f6_rerun.out` 16:05:46 → 16:10:39；C、T、RS、DS：`diag_f3pp/run_full.out` 16:22:12 → 16:33:24，皆含組間重啟）；腳本跑法回合數＝F3″ 53 回合、F3′／F5／F4 95 回合（終點那次 `f12/cmd/endpoint/run/f3f4_r5/after/*/turns.jsonl`、`run/f3f4_r5_r4in/after/*/turns.jsonl` 行數）、E2a 44 回合（`e2a_analyze.out`「turns 44」），每回合至少 1 次本機 Bedrock 主模型呼叫（模型呼叫以回合數估），每回合約 1.3 秒（F3″ 67 秒／53 回合）；腳本跑法只呼叫本機 Bedrock，⛔ 子代理 token；verifier＝239～271 千（F12 F8 verifier 238,780、選對紀錄片 V11 270,748）。以下皆跑前估計，不是上限、不當停點。

| 編號 | 執行 | 回答的決定（會改變下一步的結果） | 規模與理由 | 成本估計 |
|---|---|---|---|---|
| E-1 | M0 56 場 × `twins-before`（P0） | 終點列 M0 的改前現值（全域「終點指標」第 3 條）；沒有它 E-8 無從比 | 全題組 56 場——終點量測（目標正本 §1 第 2、3 點同題組同量尺）。全部重跑時機＝「終點量測：送審前現值」 | ≤95 分、約 598 千 token |
| E-2 | V3 14 題 × 兩版（模擬客人） | (1) 改後錯筆卡 ≥1 ⇒ 停、查機制（§8）；(2) 改前 40303／26007 組沒出現全同或錯筆 ⇒ 量尺看不到病灶，照實報、TM-1 宣稱降為「機制做對、成效未驗證」 | 同名組 4／4 全用（可用即 4）；40303／26007 是唯一改前全同組、也是 F2 兩場錯筆來源，給 5 題（涵蓋報修、建合約、手開帳單、延期四動作＋1 題「有沒有合約」描述）；其餘 3 組各 3 題（每組三種描述類別：合約、位置、樓層或租金），少於 3 題無法讓每組都碰到合約類描述與一種非合約描述；總數 ≥5 種不同輸入（廣度下限） | 28 場 × 1.7 分 ≈ 48 分；≈ 450 千 token |
| E-3 | V4 12 題 × 兩版（模擬客人） | (1) 同 E-2 (1)；(2) 改前目標為已結束合約的題沒出現「查無」或錯筆 ⇒ 量尺未重現，照實報 | 8 組（抽法見規則檔）；已結束 ≥5 題（V3C-2、sdc09781b 兩種來源各至少 2 題＋1 題兩者皆有）、未簽約 ≥2、恰 1 份帶入 ≥2、其餘 3 題為多份含未結束；少任一類就有一種出口沒被使用者層碰到 | 24 場 × 1.7 分 ≈ 41 分；≈ 385 千 token |
| E-4 | V4b 5 組 × 6 句 × 1 次 × 兩版（腳本：固定前置走到確認卡待決，再送凍結更正句） | 改後回覆含「問題描述」或改建別的動作 ≥1 ⇒ 停、查機制；改前 0 次 ⇒ 量尺未重現，照實報、TM-5 宣稱降為機制項 | 可用 5 組全用；6 句 × 5 組＝30 個案例。r2 的「每句 2 次」刪去：重複只量穩定性、不增案例（全域「驗收廣度」第 2 條），30 個不同案例已足以回答「改後是否 0 次」 | 60 場 × 每場約 4 回合；≈ 10 分（以 F3″ 40 句 67 秒、每場回合數較多估）；Bedrock 本機約 240 回合，⛔ 子代理 token |
| E-5 | F2 41 場 × 改後（模擬客人） | 終點列 F2／OV 的收案值；contract-2、interject-2、V3C-2 有任一錯筆 ⇒ 本片未達 TM-6；F2 錯筆仍 4／3 ⇒ 斷路器報告 | 全 41 場——終點量測（收案重量）；改前＝`f2e` 同程式紀錄，不重跑 | 71 分、≈ 666 千 token |
| E-6 | F3″ 40 句、F3′ 50 句、F5 12 句、F4 12 句 × 改後（腳本 `f12/cmd/endpoint/f3f4_run_ep.py` 同法、`f3f4_score_ep.py` 同口徑） | 終點列 F3″、F3′ 錯筆卡、F5、F4 的收案值；任一錯筆卡 ≥1 ⇒ 停、查機制；比例低於現值 ⇒ 附機制層原因 | 全量——終點量測（收案重量）；改前＝現值（同程式 `run_ep.out`），不重跑 | 114 句 ≈ 4 分（`run_ep.out` 67＋128 秒）；約 148 回合本機 Bedrock（上次同批），⛔ 子代理 token |
| E-7 | E2a 6 組 × 2 輪 × 改後（`f12/cmd/endpoint/e2a_run_all.sh`） | 終點列 F6 收案值；低於現值（R、C、T、DS、RS 2/2，D 1/2）⇒ 附機制層原因、交業主 | 全量——終點量測；改前＝現值，不重跑 | 12 場 ≈ 16 分（上次兩段合計，含組間重啟，見成本來源）；約 44 回合本機 Bedrock（`e2a_analyze.out`），⛔ 子代理 token |
| E-8 | M0 56 場 × 改後 | 終點列 M0；改後 < 改前 ⇒ 逐場附機制層根因交業主 | 同 E-1——終點量測（收案重量） | ≤95 分、約 598 千 token |
| E-9 | 診斷句組（P2，診斷容器 `twins-diag`） | 4.3 根因屬 (a)、(b) 或其他 ⇒ 決定修法或停 | V3C-2 原句 1＋開發句 ≤6，每句 1～2 次；中間證據、⛔ 撐宣稱 | ≤14 場 × 約 3 回合 ≈ 42 回合本機 Bedrock（計畫期 `twins/diag-pd/conv1/turns.jsonl` 一場 7 回合為上界參考）；42 回合 × 1.3 秒 ≈ 1 分，含容器重啟估 ≈ 5 分；⛔ 子代理 token |
| E-10 | V11 verifier 自寫 ≥10 輸入 × 兩版 | 全域「驗收廣度」第 8 條規定；打不過即發現，依修復規則處置 | ≥10（規定下限）、≥3 組 | ≈ 240～270 千 token，含其模擬時間約 30 分 |

只報項的讀者與用途：V3／V4「選對並出卡」改前改後並列——業主讀；改後比改前少 ≥3 題 ⇒ 收案前查機制（退步訊號），否則僅記錄。V3／V4「單回合合約清單上游呼叫數與回合延遲」——取自 E-2、E-3 的 trace，不另跑；讀者是業主的 Q-B 上線判斷；任一回合呼叫 >5 次 ⇒ 暫存沒接上，屬 V1(g) 失敗、修；回合延遲 >20 秒且主因為合約翻頁 ⇒ 寫進上線風險交業主。

合計（跑前估計）：模擬客人約 2,700 千 token（E-1 598＋E-2 450＋E-3 385＋E-5 666＋E-8 598），verifier 約 270 千；牆鐘約 7 小時（模擬客人 1 並行；各列分鐘加總約 405 分）。

## 8. 停點（只看結果）

- P0：md5 不等於核可前、mock 不印 `True`。
- P2：根因不屬 4.3 (a)、(b)。
- P5：V3、V4、V4b 改後任一場錯筆卡（一次修正後仍有）；V6、V7 改後低於改前且根因指向本片改動。
- 任一步需要 commit、push、連正式機、刪診斷容器 ⇒ 停、交業主（AUTO 不含）。
- F2 改後錯筆仍 4／3 ⇒ 收案時交斷路器報告（§1）。

## 9. 回退

開關 `AGENT_TWINS_CONTRACTS=off` 即回核可前行為（off-run 等價測試保證）；或改動檔從 `twins/v0/pre-impl/` 複製回去、重建常駐容器；`twins-before` 即核可前程式現成可用。全程不 commit、不 push。

## 10. 用量

- 至本計畫 r5 交業主前，子代理 token 1,859,156（canon 盤查分讀等 1,268,798＋security-reviewer 190,845＋plan-verifier r2 107,795＋plan-verifier r3 138,370＋收尾 plan-verifier r4 153,348，各 task notification 加總）；模型 API 費用未另統計（Bedrock 本機；計畫期診斷重送 7 句）。
- 收案報告列：審查、產題、executor、模擬客人、verifier 各自的 token 加總。

## 11. 資安審查處置（security-reviewer，r1，2026-10-25）

主會話對每條先讀碼複核再處置；依據欄寫可 grep 的符號。

| 編號 | 級 | 發現 | 主會話複核 | 處置 |
|---|---|---|---|---|
| S-T1 | P1 | 真 jgb2 擁有者帶 viewer 查合約不限 role（jgb2 端既有問題，本片放大取數） | 成立：jgb2 `app/Contract.php` `queryThisUser` 的 `roleType === 'owner'` 分支只有註解掉的 `where('user_id'…)`；`ContractApiController.php` `if ($userData) { Contract::queryThisUser(...) } else { $query->where('role_id', $roleId); }`；`UserData::getRoleTypeByRoleUser` 中 `$role->user_id == $user->id` ⇒ `owner`；本機 master 與 origin/master 三檔相同。未實跑、正式機版本未查 | FIX（本片範圍內）：§4.1 只留對得到物件的列、其餘當場丟棄不落地；TM-9 真 JGB 部分收窄為「未驗」（§5 D-6′）；上線前提改交業主（§6 Q-B）；V10 加 (5) 模擬「上游回別團隊列」。jgb2 端修正與已上線唯讀路徑（待查 Q3）DEFER 交業主（§6） |
| S-T2 | P2 | 列出已結束合約，但清單內選定與清單外打編號仍排除 `is_history` ⇒ 選了回「查無」 | 成立：`tools/confirm.py` `_prepare_closed_action` 的 `if c_status != "one" or row is None or row.get("is_history"):`；`pick_matches_name` 的 `if row.get("is_history"): return False` | FIX：§4.2 第 5 點；V1(d) 加題 |
| S-T3 | P3 | 4.3 (b)「改合約」未寫先作廢舊卡、未限只收名稱 | 成立（計畫原文缺） | FIX：§4.3 (b) 安全條件；V1(e) 加斷言 |
| S-T4 | P3 | 4.3 (a) 若把合約標題拼進系統句＝提示注入面 | 成立（`DRAFT_LINE_TEMPLATE` 只放標籤，計畫原文寫「已選合約」易誤讀） | FIX：§4.3 (a) 限只用 `draft_injection_text` 輸出 |
| S-T5 | P3 | 單回合上游呼叫數被低估（`write_name_candidates`、`closed_action_missing_labels`、`confirm_request` 各跑一次） | 成立（呼叫序列見審查證據；未實量） | FIX：§4.1 每回合暫存；§5 D-3′ 改寫；V3／V4 報單回合呼叫數與延遲（只報） |
| S-T6 | P3 | 巢狀 `contract_record` 可穿過頂層白名單 | 成立：`write_candidates.minimize_row` 以 `{k: row.get(k)}` 原樣複製 | FIX：§4.1 第 2 點封閉形狀；V10 (4) |
| S-T7 | P4 | 翻頁失敗語義未定 | 成立：`tools/action.py` `_viewer_contract_rows` 的 `has_more = bool(isinstance(pagination, dict) and pagination.get("has_more"))` | FIX（同處設計，成本低）：§4.1 第 1 點；V1(f) |
| S-T8 | P4 | `get_contracts` docstring 過時 | 未另查（本片本來就改此函式） | FIX：§4.1 第 1 點順手改 |
| 待查 Q1 | — | 正式機 jgb2 版本是否同 master | 未查（⛔ 連正式機） | 交業主（§6） |
| 待查 Q2 | — | 本團隊物件上掛別 role 合約 | 未查 | DEFER：只影響擁有者身分的計數，已隨 Q-B 一併交業主；P0 若本機 jgb2 開發庫在跑，唯讀查 `contracts.role_id <> estates.role_id` 筆數記入報告，沒在跑照實寫未查 |
| 待查 Q3 | — | 已上線唯讀合約查詢的擁有者可見性 | 讀碼：`tools/jgb2.py` `query_contracts` 三支皆帶 viewer、AIChatbot 端無事後濾；jgb2 `formatContract` 回傳不含 `role_id` | DEFER 交業主（範圍外，§6） |
| 待查 Q4 | — | #21 端點是否再驗合約歸屬 | 端點未開通 | DEFER（N3） |
| 待查 Q5 | — | 同名組清單外打編號可收下另一間同名物件的合約 | 既有 A-2a 行為，未重現 | DEFER；V4 照列發生數 |

## 12. plan-verifier 第 1 次（r2）處置（2026-10-25，REVISE 6 條，皆 substantive）

| 編號 | 發現 | 主會話複核 | 處置 |
|---|---|---|---|
| B1 | brief 未附業主原話，忠實度無從核 | 成立（r2 brief 只指向規則檔引文） | FIX：業主原話自 session transcript 原樣抽出存 `~/jgb-archive/arch-step3-20261018/twins/v0/owner-words-raw.txt`（開工訊息、AskUserQuestion 題目與全部選項、業主回覆）；下一位審查員 brief 逐字貼上。抽出時另發現 R-0、R-1（下兩列） |
| R-0 | （主會話自查）規則檔與 r1 計畫把 F12 原話 8 寫成「手開帳單的合約對象」，並在 AskUserQuestion Q1 題目寫「會改掉原話 8「當前有效合約」的限制」 | 成立：原話 8 是 F12 r4 收尾審查 B-1「合約目標的候選只列出所屬物件時算不算找到」的判分裁定（`plan-name-lenient-f12-20261022.md` r4 收尾處置表 B-1；`acceptance-name-lenient-f12-r5-20261022.md` 原話 8）；手開帳單只取有效合約的程式設計來自 `plan-assistant-11-items-20261014.md` §3f 1b | FIX：規則檔原話 4、TM-3 出處、本計畫標頭 DSP-115 改寫；業主所選 Q1 的內容（列出啟用中、最新版全部合約）不受此影響，交核可時向業主說明題目措辭有誤 |
| R-1 | （主會話自查）規則檔原話 3 的選項說明被截短（Q1 少「依據是 jgb2 的 formatTenantData，存檔也只檢查 active。」、Q2 少「依據是 Alexa 的「選項要講得出差別」。」、Q3 少「同一條流程，改動小。」） | 成立（對照 `owner-words-raw.txt`） | FIX：規則檔原話 3 改為逐字全文 |
| B2 | 終點表只列部分量法、前兩片欄有「—」、audit 存檔無版本 | 成立 | FIX：§1 改點名兩份目標文件並列全部收案門檻（F2、OV、F3″ (1)(2)、F3′ 錯筆卡、F5、F4、F6、M0、單元、audit），每列前兩片寫實際變化或「未量計 0」；`make audit` 重跑存 `twins/v0/audit-pre2.txt`（檔首記 HEAD 與受測物 md5 比對 SAME）。另更正 r2 的 E2a「現值未量」：同程式已量（`f6_rerun.out`），Q-A 只剩 M0 |
| B3 | 每次執行缺決定、規模理由、成本；全重跑未標時機；P5 修正後整項重跑；只報項沒寫讀者 | 成立（全域「測試選擇」2026-10-25 定案） | FIX：§7.1 E-1～E-10；P5 改為只重跑沒過＋碰到＋新加；只報項寫讀者與決定 |
| B4 | V4b 可用 5 組只用 3 組、無排除理由 | 成立 | FIX：5／5 全用；每句 2 次改 1 次（理由見 §7.1 E-4） |
| B5 | V4b 句子兼作診斷與宣稱 | 成立（F12 原話 10 前例） | FIX：§4.3 第 1 點改用診斷句組（V3C-2 原句＋開發句，sha256 記錄、與 V4b 逐字無重疊）；P1 產題代理不讀 `twins/diag/` |
| B6 | `tools/action.py` 手開帳單工具說明「系統以該物件唯一一份有效合約為準」與新行為相反、未排改 | 成立（grep 命中該句） | FIX：§4.2 第 6 點；§4.4 grep 範圍加 `rag-orchestrator/services/agent/`；V1 加說明文字斷言 |
| P3 附記 | 待查 Q2 只在 §11、沒進 P0 | 成立 | FIX：P0 加本機唯讀查詢（不在跑則寫未查） |
| P3 附記 | 「資料組」指 fixture 內物件組、fixture 只有一份 | 成立 | FIX：規則檔廣度表下加一行說明 |

## 13. plan-verifier 第 2 次（r3）處置（2026-10-25，REVISE 7 條：B1、B7 substantive，B2～B6 wording-only）

第二次自動 REVISE＝上限；以下逐條處置後成 r4，開一次收尾審查（全域 Orchestration「Two automatic REVISE」條）。

| 編號 | 發現 | 主會話複核 | 處置 |
|---|---|---|---|
| B1 | 終點表缺 F3″ 寬鬆候選 ≤5、寬鬆直接出卡、錯筆卡、錯筆寫入四門檻 | 成立（`acceptance-name-lenient-f12-r5-20261022.md` F3″ 列通過條件末段） | FIX：§1 加一列；現值取 `f3f4_score_ep.out`；錯筆寫入依 `f3f4_run_ep.py` 出卡即停的跑法推得 0，寫明推法；前兩片取 `stop-report-f11.md` |
| B2 | F6 現值來源只引 `f6_rerun.out`，C、T、RS、DS 實在 `diag_f3pp/run_full.out` | 成立（`f6_rerun.out` 末兩行「FATAL restart C」「F6 exit 1」） | FIX：§1 F6 列、§6 Q-A、§7.1 成本來源與 E-7、規則檔 V7 廣度列與清單列改引兩檔與實際時間；E2a 時間由 5 分更正為 16 分 |
| B3 | E-6、E-7、E-9 成本缺模型呼叫估計 | 成立 | FIX：以上次同批回合數估（`run/f3f4_r5/after`、`run/f3f4_r5_r4in/after` 的 `turns.jsonl` 行數 53＋95；`e2a_analyze.out`「turns 44」；`twins/diag-pd/conv1` 7 回合） |
| B4 | TM-1 字樣與 Q2 說明不同、未寫明 | 成立（`owner-words-raw.txt` Q2 description） | FIX：TM-1 讀法欄逐項寫差異與理由；§6 列為核可時確認項 |
| B5 | TM-3「恰 1 份 ⇒ 帶入」是讀法選擇、未寫明 | 成立 | FIX：TM-3 讀法欄寫明並附另一讀法；§6 列為核可時確認項 |
| B6 | TM-1 個資限制字面反義 | 成立 | FIX：改為「⛔ 印…等任何合約列欄位，只印由份數與最近到期日推得的字樣」 |
| B7 | TM-5 只管更正合約，比 Q3 說明窄 | 成立（Q3 說明講手開帳單草稿整體） | FIX（採審查員選項 (a)）：TM-5 改為手開帳單草稿任何回合；V4 通過條件加「回覆含問題描述或改建別的動作 0 次」，V3 手開帳單題同判，取自同批 trace、不另跑 |
| 待查 Q1 | 目標正本「測試全過」對終點表「⊆ 基準」 | 維持：V1 已寫既有失敗照實報「未達字面」（同選對紀錄片 PV2-3 處置）；收案報告照字面標未達 | 不改 |
| 待查 Q2 | M0 56 場是否有重複算案例 | 查證：`m/sessions.json` 56 場、29 題、41 種不同指示、同題至多 2 場 | FIX：V6 廣度列寫明同題第 2 場只算穩定性 |
| 待查 Q3 | V4b 6 句對 7 類說法 | 維持：一句可屬多類、「分多句」不適用單句更正腳本；P1 產題 brief 寫明 V4b 適用 6 類各 ≥1 | 不改規則，P1 brief 照寫 |
| 待查 Q4 | 「沿用 AUTO」無規則編號 | 維持：模式選擇、非驗收條件，見 §8 | 不改 |

## 14. 收尾 plan-verifier（r4）處置（2026-10-25，REVISE 2 條：C-1 substantive、C-2 wording-only）

收尾審查只有一次；C-1 是 substantive ⇒ 依全域 Orchestration 規則暫停交業主，⛔ 標 READY。以下修改成 r5，**修了、未再審**。

| 編號 | 發現 | 主會話複核 | 處置 |
|---|---|---|---|
| C-1 | F5「查不到 ≤ 改前」現值寫「過」，實為 2 對 1 未過；前兩片欄漏寫 1 → 2 | 成立（`f3f4_score_ep.out` after「F5 查不到出口句數」2、f12before 1；`f3f4_score_r5.out` 1／1；判分腳本「F5 門檻」只判候選差）。主會話另以自寫腳本逐句找查不到句，兩側都 0 句、與判分檔 2／1 不符 ⇒ 該腳本的比對鍵錯（正對照不過），結果作廢，不據以下結論 | FIX：§1 F5 列改為未過並寫來源與前兩片 1 → 2；低於門檻段加入；新增業主待裁 Q-C（建議不併入、照實報、計入斷路器，P0 只讀定位）；V5b、TM-10 寫明判法 |
| C-2 | F4 列只寫部分 r4 條件的現值 | 成立（r4 清單 F4 列「三組共同…」「不存在名稱…」） | FIX：§1 F4 拆成四列，逐條寫現值、來源鍵或推法；「(甲) 後只重問名稱」寫明未觸及（腳本出查不到即停） |
| 待查 1 | TM-3 組內排序與 JGB 網頁不同 | 成立（`jgb2/dev5` master `src/pages/bills/edit/_parts/BillTargetBlock.jsx`「1."簽合約日期"越後排前面」，比較 `contract_date_start`） | FIX：§4.2 第 2 點、TM-3 改為組內依 `date_start` 由晚到早（同網頁）；同日期依編號固定次序，寫成 D-4′ 偏離 |
| 待查 2 | 「已結束」兩處定義不一 | 成立；並查得 D-4′ 原理由「fixture 有 date_end 在未來卻 is_history=1 的列」不實（19 份 `is_history=1` 的 `date_end` 皆 ≤ 2026-10-25） | FIX：§4.1 第 2 點與 D-4′ 改為只看 `date_end`（同網頁、同規則檔名詞）；V4 抽法依此重算為 13 個已結束、聯集 15、取 8（原寫 12／14 有誤），名單不變 |
| 待查 3 | E-10「約 30 分」無每場時間來源 | 成立（量級與 1.7 分／場相符） | 未改，交業主時照列 |
| 待查 4 | 「沿用 AUTO」無規則編號 | 同 §13 待查 Q4 | 不改 |
