# 計畫：第 3 步整體驗收 OV（2026-10-21 r4）

> 狀態：r5，**業主 2026-10-21 核可**（Q3＝(a)、Q4＝(a)），規則與清單凍結。r3 收尾審查 REVISE 經業主裁「兩層都查」「照全文」「改完再審一次」，r4 依此改；r4 收尾審查再退回 3 條，業主裁「修這 3 條後交你核可」，r5 已修、未再審（見 §6）。
> 規則與驗收清單：同目錄 `acceptance-overall-step3-20261021.md`（規則在前，核可時與清單一併凍結）。
> 依附：GOV-4（全域「驗收廣度」節，業主 2026-10-21 核可：Q2(a) 下限 ≥3 組、≥5 種輸入；Q3(a) verifier 自寫 ≥10 個新輸入；計畫 `~/jgb-archive/governance-20261021/plan-gov4-acceptance-breadth.md`）。
> 風險類別：量測片，不改程式；結論會回頭影響 B、A-2a 等已收案片的宣稱（業主裁）⇒ 核可前 `plan-verifier`、完成後 fresh `verifier`。

## 先答三題（全域「驗收廣度」第 7 條）

1. 每項幾組資料 × 幾種輸入 × 重複幾次：新題組 6 類 × 8 題＝48 題 × 每題 2 次 × 2 個版本；每類 8 組資料，同名組全用（物件同名 4／4、合約同名 6／6、多張帳單物件 6／6），其餘以固定種子抽（物件 79 組抽到 8、合約 17 組抽到 8、有帳單物件 9 個用 8；P1 盤點已實跑）；每類 8 題中 7 種說法各 ≥1 題、48 題合計每種 ≥3 題。M0 題組 29 題原樣、56 場，只在現在版本跑。回歸：E2a 6 個固定腳本各 1 筆資料 × 2 輪（實作方所寫，只證不退步，見規則檔 Q4）；單元、golden、`make audit` 為機制項。程式層：第 3 步服務程式新增行對 fixture 全部名稱與編號掃描（V9）。
2. 輸入誰寫：新題組由不讀程式的 fresh 代理依 fixture 資料目錄產生，主會話只做真值正確性檢查；每題的開場句（「分多句」類為兩句）由產題代理依指定說法寫好並凍結，兩版本逐字相同，之後的回合由模擬客人照目標自由講。M0 題組沿用第 2 步出題代理所寫（36/56 場要求名稱一字不差）。E2a 腳本為第 2 步主會話所寫。
3. 跟改前比了嗎：新題組在 `de7f4653`（第 3 步之前、M0 基線受測物）與 `d1ddc084`（現在）同題同次數各跑；M0 題組與 M0 報告（同一受測物 `de7f4653`）比；E2a 與 B 片報告（前一基線）比；單元失敗集合與 A-2a 收案基線比。

## 1. 目標

業主原話與讀法見規則檔（W1、W2、W5、W8、W9）。要回答的問題只有一個：第 3 步做完的各片合起來，使用者用不同資料、不同講法辦事時，是不是真的比之前好；沒變好的地方在哪、為什麼。

成功＝報告第一段能用同一套事先凍結的判準回答「有效／無效」，並逐類、逐資料組、逐說法類別列出改前改後；M0 缺陷場次每一場都有結論。

終點指標：新題組寫入情境 Intercom 解決率「現在 − 之前」的配對差與 95% 信賴區間（現值：無同題改前改後數字；M0 → A 的 24/52 → 34/52 是唯一一次同題重測，且只到 A 片）。預期變化：從「未量」變成一個量到的配對差與信賴區間；假設方向為正（現在較好），但不預設會過 Q3 判定式——結論只有整體「有效／未證明有效」兩種，依 Q3 判定式；分類、分資料組、分說法的數字只描述，不另下結論。

## 2. 目標形態（業界做法與第一原理）

原文在 `~/jgb-archive/governance-20261021/sources/`（web-drive 渲染；GOV-4 同一批）：

- OpenAI，Evaluation best practices（`openai-eval-best-practices.txt`）：反模式「Biased design: Creating eval datasets that don’t faithfully reproduce production traffic patterns.」→ 新題組不沿用要求「一字不差」的題目；「generate a diverse set of test data across various scenarios. Ensure your test data includes typical cases, edge cases, and adversarial cases.」→ 6 類 × 全部資料組；「Contextual complexity」桶「Multiple questions or intents in a single request」「Typos and misspellings」「Short requests with minimal context」→ 說法類別「一句多件事」「錯字」「只講一半」；「Run and compare evals」→ 改版前後都要跑評測並比較（原文未逐字要求「同一批題」，同題配對列第一原理，見下）。
- Anthropic，Define success criteria and build evaluations（`anthropic-develop-tests.txt`）：「Be task-specific: Design evals that mirror your real-world task distribution. Don't forget to factor in edge cases!」→ 題目以業者實際會辦的四種寫入加卡後更正、中途插問為類別。
- Hamel Husain，Your AI Product Needs Evals（`hamel-your-ai-product-needs-evals.txt`）：「break down the scope of your LLM into features and scenarios」「you must generate test cases or inputs that will trigger all scenarios you wish to test. I often utilize an LLM to generate these inputs synthetically」→ 類別 × 資料組展開、由代理產題。

第一原理（查無業界逐字對應）：
- 產題代理不讀程式（全域「驗收廣度」第 4 條）：實作者寫的題只測得到他想到的失敗。
- 逐題配對比較與 bootstrap 信賴區間：同一題在兩版本各跑，差異才歸得到程式；48 題規模下以題為單位重抽樣。查無業界逐字對應，屬統計常規推導。
- 說法類別「簡稱」「順序對調」「分多句」「口語」：由本線 M0／E2b 題組要求名稱「一字不差」的實例推導（GOV-4 計畫 §2）。

偏離：模擬客人與盲判沿用 DSP-087 量尺（目標正本 §1「怎麼量」），不改成自動字串比對；理由：寫入情境的成敗要看多輪對話是否辦成，盲判已在本線用過並有誘餌把關。

## 3. 差距（現況；可重跑）

| # | 目標形態 | 現況 | 查證 |
|---|---|---|---|
| G1 | 同題改前改後 | 只有 A 片重測 M0（24/52 → 34/52）；期別、A+、B、A-2a 皆無同題改前對照（B 的同題對照是 4 句固定腳本） | `grep -n 34/52 ~/jgb-archive/arch-step3-20261018/ra/report-ra.md`（repo 外檔）；GOV-4 計畫 §3 D6 |
| G2 | 寫入題組有說法廣度 | M0 題組 36/56 場、A+／B／A-2a 的 E2b 32/32 場要求名稱「一字不差」 | GOV-4 計畫 §3 D6 |
| G3 | 資料組全用 | A-2a V8／V10／V16 各只用 1 組同名資料；fixture 合約同名 6 組、物件同名 4 組 | `services/jgb/fixture_data/assistant_demo_vendor4.json`（P1 盤點重算） |
| G4 | 目標正本規定的 M0 逐場重測 | A-2a 計畫與驗收 0 處提到 M0 | `grep -c M0 .kiro/specs/agentic-mcp-orchestration/acceptance-a2a-write-candidates-20261020.md`（0；正對照 `acceptance-b-write-replies-program-20261020.md` 為 4） |
| G6 | 程式層沒有寫死測試資料 | 只掃過 A-2a 一個 commit（`d1ddc084~1..d1ddc084`）的 5 個手選字串；第 3 步其餘 6 個 commit 未掃 | `git log --oneline de7f4653..d1ddc084`（7 筆） |
| G5 | 改前版本可跑 | 無 `de7f4653` 容器；前例 `w2-diag`（18103）以換檔方式建 | `docker ps --format '{{.Names}} {{.Ports}}'` |

`de7f4653..HEAD` 之間 `rag-orchestrator/database`、`requirements.txt`、`services/jgb/fixture_data` 皆無改動（`git diff --stat de7f4653..HEAD -- <路徑>` 為空，2026-10-21 主會話實跑）⇒ 兩版本可共用同一 DB 與同一份 fixture。

## 4. 路徑（一片，OV）

| 步 | 內容 | 對應 |
|---|---|---|
| P0 受測物 | 以 `git worktree add` 取 `de7f4653` 到 `~/jgb-archive/arch-step3-20261018/overall/wt-m0`，建映像 `aichatbot-rag-orchestrator:m0-diag`，起容器 `m0-diag`（18104，與常駐共用 DB 與網路；compose 覆寫檔放 `overall/`，⛔ 讀 `.env` 或印容器 env）。常駐容器改回不帶 write-log override（快照所記）並確認＝`d1ddc084`（本線容器可自行重建）。兩邊 mock 檢查印 True、印模型名稱（非憑證）。煙霧與一致性測試：6 類 × 2 版本各 1 場（主會話寫的固定句，只算中間證據），比對兩版本對同一真值的卡標籤集合、紀錄編號格式（有無「（編號 N）」後綴）與動作名；任一類不同 ⇒ 停點。mock 寫入是否跨場保留：同一容器寫一次、新 session 讀回，結果寫進報告 | V0 |
| P1 盤點 | **已於 2026-10-21 實跑（唯讀）**：`~/jgb-archive/arch-step3-20261018/overall/p1_inventory.py`，輸出 `p1_inventory.out`。資料組＝客人可能用同一名稱指稱的紀錄集合。修繕、建合約：物件名組 79（同名 4）；補開帳單：合約名組 17（同名 6）；帳單延期：有帳單的物件 9（≥2 張 6）；出卡後更正、流程中插問：從上列四種動作各取 2 組，優先同名組。正對照合約同名 6、物件同名 4 皆中。各類用／可用與抽法見規則檔「廣度」表 | V1 |
| P2 產題 | fresh 代理只拿到 P1 產出的資料目錄（名稱、地址、房型、租金、帳單期別與金額等業者看得到的欄位）與類別×說法表，產 48 題：每題＝客人目標、客人知道的資訊（含區分同名的屬性）、指定說法類別、照該說法寫好的開場句（「分多句」類兩句，凍結後兩版本逐字送出，送出由程式比對）、真值（動作、應選紀錄編號、卡上應有值）。⛔ 給 repo 路徑或程式。6 類：修繕、帳單延期、補開帳單、建合約、出卡後更正、流程中插問 | V2 |
| P3 凍結 | 主會話以單一腳本 `overall/truth_map.py` 把代理寫的真值轉成量尺鍵（`action`、`card_expect`、`card_contains`，標籤與編號格式取 P0 一致性測試確認的寫法），兩版本共用同一份；程式檢查真值在 fixture 內且與目標一致、說法類別與資料組覆蓋；主會話只改真值錯誤（逐題記錄），⛔ 改題意；存 `overall/tasks.json` 與 sha256 | V2 |
| P4 跑新題組 | 每題 2 次 × 2 版本；同題兩版本交錯排程，降低時間漂移；每批 ≤4 位模擬客人並行；每批前兩容器重啟（若 P0 證實 mock 寫入跨場保留）；排批由 `overall/schedule.py` 依 `tasks.json` 產生並自查：同一容器同一批內任兩場不碰同一筆物件、合約或帳單，含上層（帳單→合約→物件、合約→物件），違反即不跑；正對照為一個故意違反的測試批須被抓出 | V3、V4 |
| P5 跑 M0 題組 | M0 題組 56 場原樣在現在版本跑；M0 與 A 後原紀錄依 DSP-102（W-R3 真值同時含「水龍頭」「滴水」）重算前判，三者同一套真值，重算後的數字才是比較基準；K 組依目標正本「不低於前一基線」須 ≥ M0（16/20，K 組不受 DSP-102 影響）。排批同 P4：`schedule.py` 依 `m/sessions.json` 真值自查同批不碰同一筆（含上層），P0 證實寫入跨場保留時每批前重啟常駐容器 | V5、V6 |
| P5b 回歸 | 常駐容器（`d1ddc084`）跑 E2a 六組 × 2 輪：另放 OV 版腳本 `overall/e2a/run_all.sh`（自 B 片版複製，`OUT=` 改為 `overall/e2a`），每組前 mock 檢查；B 片 `b/e2a/` 只讀，跑前跑後各檔 sha256 比對、不同即停；E2a 前若 P0 證實寫入跨場保留則重啟容器，與其他場次同批時納入 `schedule.py` 自查；與 B 片報告（R、D、C、T、RS、DS 皆 2/2）比；`make test-unit` 全量（含 golden），失敗集合對 `a2a/unit-final-failed.txt`（9 筆）；`make audit`。目標正本字面是「測試全過」——有失敗就照實報，⛔ 自行放寬 | V8 |
| P5c 程式層特規 | `overall/special_case_scan.py` 自 fixture 取全部物件、合約、修繕的名稱類欄位字串（≥3 字；印出取用的欄位名與字串數）與物件、合約、帳單、修繕編號（≥4 位數，詞邊界），掃 `git diff de7f4653 d1ddc084 -- rag-orchestrator/services` 新增行；正對照＝同腳本掃同範圍 `rag-orchestrator/tests` 新增行須 ≥1 命中；服務程式命中逐行判讀 | V9 |
| P6 盲判 | 依 DSP-087 盲判，每批含 judge-check 誘餌；盲判不知道版本 | V3、V5 |
| P7 分析與報告 | 配對 bootstrap（以題為單位，10,000 次，種子固定）；逐類、逐資料組（用過／沒用過兩欄）、逐說法類別表；錯筆出卡清單；M0 缺陷逐場表；回歸表；程式層掃描結果；各片宣稱對照表 | V3～V9 |
| P8 驗證 | fresh `verifier`（自寫 ≥10 個新輸入，換資料組也換說法） | V10 |

產物放 `~/jgb-archive/arch-step3-20261018/overall/`；題目文字與答案 ⛔ 進 git（專案規則）。repo 只放本計畫、規則與清單檔與之後的決策列。

V5 的歸屬判讀：HANDOFF §2.5 缺陷中，歸給已完成片（A 含 A0／A1／A2／A4／A7、期別、A+、B、A-2a）的場次，判「已解決」或附機制層根因；歸給未施工片（A-2、E、D）的場次只記現況，不算本次未達。

非目標與理由：
- 逐片拆成效：各片改同一條寫入路徑且彼此依賴，拆片要再建 4 個中間版本、量測量 ×3；缺陷類別層已有歸屬表可對。
- E、W2、D、C 等未施工片：還沒有東西可量；做完後沿用本題組再量（屆時另立計畫）。
- 真 JGB、preview：本線不碰（業主開工指令）。
- 改程式：本片是量測；發現缺陷只記錄、交業主決定另開片。
- 改寫過去報告、凍結清單、決策列：全域文件衛生第 3 條；結論交業主裁後另立新決策。

回退：刪 `m0-diag` 容器與映像、`git worktree remove`；本片不改 repo 程式，無需程式回退。

## 5. 驗證、用量與停點

- 會呼叫 JGB 的每一批前，兩個容器都跑 HANDOFF §3 mock 檢查，必須印 True（`m0-diag` 把容器名換掉）。
- 用量估計（參考 A-2a 實際：E2b 32 場模擬客人約 30.4 萬、盲判約 14.5 萬 token ⇒ 每場約 1.4 萬）：新題組 192 場約 270 萬＋M0 56 場約 78 萬＋產題約 15 萬＋驗證約 25 萬 ≈ 390 萬；E2a 12 場為固定腳本、不用模擬客人，主要成本是 Bedrock 實打。Bedrock 本機實打費用另計，收尾回報實際用量（子代理 token 加總）。不設 token 上限停點。
- 停點（看結果）：P0 煙霧測試在 `de7f4653` 上前判無法解析卡，或任一類兩版本卡標籤／編號格式／動作名不一致（量尺對兩版本不公平）⇒ 停，交業主；P3 真值錯誤超過 5 題 ⇒ 重產題一次，再超過 ⇒ 停；盲判誘餌失敗 ⇒ 該批重判一次，再失敗 ⇒ 停；`schedule.py` 正對照沒抓到故意違反的批，或 `special_case_scan.py` 正對照 0 命中（工具壞了）⇒ 停；mock 檢查非 True ⇒ 該批不跑；verifier REFUTED 兩次 ⇒ 停。

## 6. 審查紀錄與處置

| 次 | blocker | 處置 |
|---|---|---|
| 1（r1） | 資料組數字未填、「全部資料組」與每類 8 題矛盾 | FIX：P1 盤點先實跑；廣度表填用／可用與抽法（同名組全用＋固定種子抽） |
| 1（r1） | 真值如何轉成量尺鍵未定、兩版本卡格式一致未證 | FIX：P3 單一 `truth_map.py` 兩版本共用；P0 擴成 6 類 × 2 版本一致性測試，不一致即停 |
| 1（r1） | 知識題「無門檻」偏離目標正本「不低於前一基線」 | FIX：V6 改為 ≥ M0 16/20，照正本 |
| 1（r1） | W3、W4、W6、W7 未引用（wording-only） | FIX：原話補齊，各掛規則或非目標 |
| 1（r1） | 終點指標無預期變化（wording-only） | FIX：寫明預期變化與假設方向 |
| 1（r1） | V5 基準與重跑真值不同（wording-only） | FIX：M0 與 A 後依 DSP-102 重算為基準，舊口徑只當參考 |
| 1（r1） | 廣度表列號與清單不符（wording-only） | FIX：改為 V3～V6 並補 V6 列 |
| 1（r1） | OpenAI「Run and compare evals」引申為同題（wording-only） | FIX：收窄為「改版前後都要比」，同題列第一原理 |
| 2（r2） | Q1(b)、Q2(b) 無法落地 | FIX（簡化）：撤兩題；規模固定 192 場、知識不進新題組，理由寫在規則檔 |
| 2（r2） | 「部分類別有效」無凍結定義 | FIX：結論只依 Q3 整體判定，分組數字只描述 |
| 2（r2） | 說法類別只是標籤、兩版本客人措辭不同 | FIX：開場句凍結、兩版本逐字送出、程式比對，不符作廢重跑一次再剔除 |
| 2（r2） | W2「通用修法嗎? 還是有特規」無規則 | FIX：掛 OV-R2，行為層分「用過／沒用過的資料組」；程式層盤查列非目標並附 grep 結果 |
| 2（r2） | V5／V6 廣度列格式不符（wording-only） | FIX：填數字與實際出題者 |
| 3（r3 收尾） | OV-R3 只引正本第 3 點前半、回歸只取 K | 業主裁「照全文」⇒ FIX：OV-R3 與「上位驗收方式」引 §1「每片怎樣算完成」第 1～3 點全文；新增 V8（E2a 六組、單元、golden、`make audit`，對前一基線）、P5b；E2a 廣度低於下限列 Q4 交業主 |
| 3（r3 收尾） | W2「特規」讀法未問業主、程式層 grep 只掃 A-2a 一個 commit 的 5 個字串 | 業主裁「兩層都查」⇒ FIX：新增 V9／P5c，掃 `de7f4653..d1ddc084` 全部服務程式新增行、字串取自 fixture 全部名稱與編號、附正對照；舊 grep 結果自非目標移除 |
| 3（r3 收尾） | 「用過資料組」清單只列 2 組 | FIX：改依 `overall/used_groups.json`（六批產物 3,177 檔；物件 22/79、合約 13/17、帳單 37/64；正對照通過） |
| 4（r4 收尾，依業主「再退回就停」⇒ 停，交業主；業主裁「修這 3 條後交你核可」⇒ FIX，未再審） | (1) P5b 照用 `b/e2a/run_all.sh` 會覆寫 B 片基線目錄（`OUT=` 寫死）；(2) 隔離與重啟只套 P4，P5（M0）與 P5b（E2a）同容器無隔離；(3) 說法類別只有整體配額、未保證 V3 每類各說法 ≥1，V5、V6 的第 3、4 條偏離未列待裁 | 三條主會話皆已重現（`run_all.sh` 第 4 行、`transport.py` `_created_visible`／`_idempotency_cache`、規則檔「各 ≥3 題」）。FIX：(1) P5b 改用 `overall/e2a/run_all.sh`、`b/e2a/` 只讀＋雜湊比對；(2) 隔離自查與重啟延伸到 P5、P5b，V5、V6、V8 通過條件加自查違反 0；(3) V2 加「V3 每類 7 種說法各 ≥1」，V5、V6 偏離併入 Q4 |
| 3（r3 收尾） | mock 寫入隔離只管同一張帳單 | FIX：同容器同批任兩場不碰同一筆物件、合約、帳單（含上層），`schedule.py` 自查＋正對照 |
