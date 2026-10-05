<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「核可，同意本計畫 +0 (Recommended)」
-->
# Plan 9.29：目標驗收規格 §2.2 後半——依 D1 處置 9.28 的 111 項不成立（+0）

> **現況**（2026-10-04，HEAD `f13b0cb5`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`。
>
> **本計畫的進度單位**：規格第 2 項（內容）的「不成立句已處置並重驗」——**已處置 0／111 → 111／111**（每項的去向：改寫、整句刪、標題刪字、業主裁定保留、業主裁定延後整條刪）。已審細目數 **+0**：被修改的細目在寫入前暫時失去已審，每組 commit 後回到 537／121；本計畫不刪細目。`consent_zero` 目前為佔位（含「待」，`CONSENT_BAD` 會擋 commit）；業主核可時須明示同意，逐字原文替換此欄；沒有 ⇒ ⛔ commit。
>
> **為什麼值得做這份 +0**（連續第四份 +0）：這 111 項是已審、會被 AI 客服引用的錯誤內容（數字錯、按鈕文字錯、漏例外、描述已失效的流程）。不處置，正本就繼續把錯的答案交給業者；規格第 2 項的達成條件也明寫「不成立句已處置並重驗」。
>
> **驗收清單（凍結）**：`.kiro/specs/knowledge-outline-and-intent-architecture/acceptance-9.29-20261004.md`。

## 0. 依據

- 規格 `../goal-acceptance-spec-20261004.md` §2.2：「不成立句依 D1（修一次或整句刪）並重審」；達成：「補核全數成立或不成立句已處置並重驗；抽查 30／30」。
- 業主 2026-10-04 對「下一步：依 D1 處置這 111 項……要開始的話我先寫計畫、送就緒審查」回覆「開始」。
- D1（HANDOFF §12-2，業主 2026-10-03）：修時同步檢查同條細目的標題、所有句子與講法；⛔ 改別條；修一次仍不過就整句刪；需要整條刪、或須替待裁選邊的，停下交業主。
- 待處置清單 `inputs/fix-list-9.29-20261004.json`（由 9.28 彙整機械產生）：111 項、81 條細目（標題 29、句 81、抽查推翻 1），每項附 9.28 批次代理的不成立理由。整條每句都不成立的 9 條列為**整條刪候選**；另 9.28 B07 指出「物件綁定社區」導引（`forcebinding-*` 5 條，其中 4 條在待處置清單；`forcebinding-select-estates-irreversible` 9.28 判全條成立、不在清單）現行已觸發不了。

## 1. 流程（五組 G1～G5，依架分；同一流程）

| 組 | 架 | 細目 | 整條句數 |
|---|---|---|---|
| G1 | A、B | 19 | 53 |
| G2 | C | 11 | 31 |
| G3 | D | 19 | 84 |
| G4 | E | 18 | 52 |
| G5 | F、G、H、I | 14 | 46 |

### 核可前已預跑（scratch，repo 未動）
- drafts 重生成基準：`drafts_to_canon.py generate`（`--front-matter-from` 現行正本、`--expect-reviewed-kept 543`）在 scratch 產出與 repo 正本 `diff -r` 相同（已審保留 543、丟棄 0、DSP-068 刪除 36 行、open_questions 54）。
- `edit_fine.py` 的檔尾換行表只列 A、B、C、I；實測 drafts 檔尾：A、C、E、F、G 無換行，B、D、I 有換行，H 與 `json.dumps(indent=1)` 不相等（H 無待處置細目，不會被編輯）。⇒ 執行時把 D、E、F、G 補進 `TRAIL`，並以 `--roundtrip` 對九架（H 除外）證明位元組不變。

### 步驟（核可後）
1. **步驟 0 基準**：HEAD 全碼；`make audit`；他線 41 檔指紋（正對照 `runtime.py`）；全套 unit 紅燈基準；`edit_fine.py` 補 D、E、F、G 的 `TRAIL` 並 `--roundtrip` 九架（H 除外）位元組不變（`.agents` 鏡像同步）；HANDOFF 備份 `scratchpad/p929-backup/HANDOFF.md` 並 `cmp`。
2. **起草（每組一位 executor，依序）**：輸入＝該組待處置項（含 9.28 理由與證據檔路徑）＋各細目全文與 sources＋jgb2 釘住匯出。規則：
   - 每項只改一次：句子改寫成合法來源實際的行為（附逐字引文與檔案路徑）；無法從合法來源確立 ⇒ 整句刪；標題只刪字到每個斷言都有句子支撐。
   - 整條檢查（D1）：同條其他句、標題與講法若因修正而矛盾，一併修，修正紀錄標「整條 #m」；⛔ 改別條細目。
   - 整條刪候選 9 條照樣逐句「修一次」；只有改寫後仍無一句能成立時才標「交業主」。`forcebinding-*` 4 條依業主核可時的裁定處理（見 §3 (b)）。其他需要替產品或待裁選邊的項目標「交業主」，⛔ 動手。
   - 00c 起草規則：證據逐字、否定句附 `not_supported_greps` 與正對照、⛔ 實作詞；客戶名一律寫「特定合作團隊」；⛔ 新增修正以外的事實。
   - 輸出 `edit_fine.py` 的 ops JSON（每條細目一份）＋修正紀錄表；主 session 以 `P919_RUNS=<scratch drafts>`、`ALLOWED=<該組細目>` 套用到 scratch drafts，`drafts_diff.py` 須 PASS（允許集合外 0 改動）。`edit_fine.py` 拒絕「句子全刪」⇒ 該細目標「交業主」（本計畫不做整條刪除，見 §2）。
3. **先審（每組一位 fresh verifier，依序）**：逐句核對每條被修改細目的**全部**句子與標題，判準同 9.28 brief 並加「排他列舉、過度概括、同粗目矛盾即不成立」；每組混 1 條誘餌（9.28 誘餌機制）當正對照，誘餌漏抓 ⇒ 該組先審作廢、換人一次。處置：已改寫句被判不成立 ⇒ 整句刪（⛔ 二次改寫）；未改動但被判不成立的句（新發現）⇒ 整句刪或標「交業主」；標題 ⇒ 刪字；刪後會讓細目無句 ⇒ 標「交業主」。
3b. **刪後整條複查（全部組完成後一次）**：凡先審後又刪句或刪字的細目，派一位 fresh verifier 做 D1 整條檢查——標題每個斷言仍有句子支撐、剩下的句子沒有排他或過度概括、與同粗目其他細目不矛盾；只做判定。不符 ⇒ 只能再刪字或刪句，或標「交業主」（⛔ 改寫）。輸出 `verification/<日期>-p929-postdelete.json`；終審單標出這些細目。
4. **業主終審**（一次，全部 81 條）：`inputs/review-sheet-9.29-20261004.md` 逐條列修正前後原文、處置類別、先審結論、是否「先審後刪除」；另列「交業主」項，每項附建議。業主回覆核可範圍（可整批或逐條標出例外）。**未核可的細目**：該細目的 ops 不套、正本保留原文與已審，A1 去向記「業主裁定保留」。**「交業主」項**的去向只有兩種：業主裁定保留（同上），或業主裁定整條刪除——延後到下份計畫（需另建整條刪除工具），本計畫不動，A1 去向記「業主裁定延後整條刪」。
5. **寫入（每組一個 commit，依序 W1～W5）**：
   1. **組基準快照**：以當時 HEAD 為準，把 `rag-orchestrator/canon`、`runs/outline-20260920` 複製到 `scratchpad/p929/W<k>-base/`，`diff -r` 與 repo 相同（組內停下的還原來源與比對基準）。
   2. 把該組**業主核可**細目的 ops 套到 repo drafts；`drafts_diff.py` PASS；先在 scratch 試跑生成器確認，再對 repo 生成（`--expect-reviewed-kept` ＝ 生成前正本已審條數 − 本組實際改動內容的細目數）；`canon_check.py` 區塊差異只在本組已改動集合。
   3. **加已審前快照**：把生成後的 `rag-orchestrator/canon` 複製到 `scratchpad/p929/W<k>-pre-approve/`，`diff -r` 相同。
   4. `approve_write.py write` 對本組已改動且業主核可的細目加已審 → 容器重匯出、`load_canon_or_die` → `approve_write.py verify --backup scratchpad/p929/W<k>-pre-approve/`（須 `mismatches: 0`、只多 `- reviewed:` 行）。
   5. 全套 unit 差集 ∅；終點指標回到 pm 537／537、prospect 121／121。
   6. **寫入核對**：一位 fresh verifier 逐句核對本組全部已改動細目（`kind: write`，每句「成立」、帶 `content_sha256`／`title_text`）→ `--extract` → `make audit` OVERALL PASS → commit（`Verified-by` 指向本組寫入證據）。
6. **文件**：最後一組 commit 一併更新 HANDOFF（開頭現況、§12-1 加 9.29 列、9.28 的「110 項」改為 111）。
- **commit 範圍（每組）**：本組 drafts、runs 產出（`open-questions-*`、`reviewed-dropped-*` 等生成器輸出）、`rag-orchestrator/canon/jgb/<架>.md`、`CATALOG.md`、`jgb.json`、本組寫入證據；第一組另含本計畫、驗收清單、待處置清單、終審單、先審與複查證據、`edit_fine.py`（含 `.agents` 鏡像）；最後一組另含 HANDOFF。⛔ `git add -A`、⛔ `--amend`；push 由業主自跑。
- **還原**：第 k 組在步驟 5.2 之後、commit 之前任何停下 ⇒ 以 `scratchpad/p929/W<k>-base/` 還原 `rag-orchestrator/canon` 與 `runs/outline-20260920`，`git diff HEAD -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 須為空（前面已 commit 的組留在 HEAD，不受影響）、`load_canon_or_die` 通過 ⇒ 記 §6 ⇒ 停下交業主。寫入核對推翻任一句 ⇒ 同上還原、停下交業主（⛔ 本計畫內再改寫）。commit 後驗收 FAIL ⇒ ⛔ 改寫歷史，回報業主。

## 2. 不做（後續計畫）

- 業主抽查 30 句（規格 §2.2，種子 `20261006`）：本計畫全部寫入後再抽。
- **整條刪除**：review_pipeline 沒有整條刪除工具（`edit_fine.py` 對句子全刪會拒絕並要求另走刪除路徑；`drafts_diff.py` (d) 要求修正紀錄「## 刪除」節），本計畫不做；業主裁定要整條刪的細目延後到下份計畫，先建工具與機械檢查。
- 整句刪掉的正確資訊重新起草（同 9.24 做法，下份計畫）。
- 事實帳本 `docs/knowledge/jgb-product-facts.md` 與幫助中心內與程式衝突的段落（9.28 各批 findings 已列）：本計畫只改正本；帳本與幫助中心另案。
- 9.28 驗證提的 P4：9.28 計畫 §0 過時字句、B14 停擺時間描述——屬已 commit 的歷史紀錄，不改。

## 3. 業主裁決與待裁

- **已裁**：規格 v6；業主「開始」。
- **待裁（核可時回覆）**：(a) 本計畫，並明示同意 +0（被修改的細目在寫入前暫時失去已審，每組 commit 後回到 537／121）；(b) `forcebinding-*` 4 條（導引現行已觸發不了）二選一：改寫成「舊版遷移流程、現行不再觸發」的描述（本計畫 G2 起草），或退役整條刪（延後下份計畫，本計畫不動；選此項時 4 條在 A1 記「業主裁定延後整條刪」）。第 5 條 `forcebinding-select-estates-irreversible` 不在本計畫範圍，兩案皆不動，留下份計畫一併處理。
- **待裁（步驟 4 終審時另交）**：81 條修正結果；起草或先審中標「交業主」的項目（保留或延後整條刪）。

## 4. 停止條件與額度

- 允許集合外的 drafts 或正本有任何改動 ⇒ 停。
- 某組先審的誘餌連續兩次漏抓 ⇒ 該組暫停，其餘組照跑，收尾回報。
- 寫入核對推翻任一句 ⇒ 該組還原、停下交業主。
- 已審細目數在每組 commit 後須回到 pm 537、prospect 121（本計畫不刪細目；未核可者保留原文與已審）；不符 ⇒ 停。
- **額度**：起草 5×約 0.5M、先審 5×約 0.35M、刪後複查約 0.3M、寫入核對 5×約 0.3M、就緒審查約 0.4M，估約 6.8M（含重做預留 1M）；規格 §5 總上限 30M，前面計畫已用約 7.5M。累計超過 9M ⇒ 停下回報。
- 執行模式沿用本線的 ASK：核可範圍內連續執行；業主終審是固定停點；停止條件觸發或完成時回報。

## 5. 就緒審查紀錄

- **預跑**：見 §1「核可前已預跑」；待處置清單 111 項／81 條，各組細目與句數見 §1 表。

- **第 1 輪**（fresh plan-verifier）：REVISE，P2×5，全數 FIX——(1) 還原只有步驟 0 的備份，會把已 commit 的組倒回 ⇒ 每組開工前建「組基準快照」並改用它還原、以 `git diff HEAD` 為空驗證；(2) `approve_write.py verify --backup` 未指定 ⇒ 加「加已審前快照」並明定；(3) 業主未核可細目的去向未定義 ⇒ ops 不套、保留原文與已審（A1「業主裁定保留」），§4 與 A7 公式改為恆回 537／121；(4) 整條刪除寫成「DSP-068（同 9.24）」錯誤且無工具 ⇒ 本計畫不做整條刪，列 §2 非目標、交業主項只有「保留」或「延後」兩種去向，`forcebinding-*` 改在核可時裁定；(5) 先審後刪句缺 D1 整條複查 ⇒ 新增步驟 3b（fresh verifier 判定，只能再刪或交業主），終審單標「先審後刪除」。

- **第 2 輪（收尾審查）**（fresh plan-verifier）：READY。

## 6. 執行紀錄

- **業主核可**（2026-10-04，AskUserQuestion 逐字）：(a)「核可，同意本計畫 +0 (Recommended)」（已填入 consent_zero）；(b) forcebinding 4 條：「改寫成舊版流程 (Recommended)」⇒ G2 起草改寫成「舊版遷移流程、現行不再觸發」。

- **步驟 0**（HEAD `f13b0cb5`）：`make audit` OVERALL PASS；unit 紅燈 9 項，與 9.28 收尾相同；他線 41 檔指紋與 9.28 相同（含正對照 `runtime.py`）；`edit_fine.py` 補 D～G 的 `TRAIL`，九架（H 除外）`--roundtrip` 位元組不變，H 架當負對照仍不相等；兩份鏡像 `cmp` 相同；HANDOFF 備份 `scratchpad/p929-backup/`。
- **起草（executor，五組）**：工作清單由 `scratchpad/p929/gen_worklist.py` 機械產生（9.28 句號是正本序，以去標點子字串對回 drafts 句序；D 架 `contract-invite-and-review-period` 的 drafts [3] 對應正本句 4、5）。產出以 `check_exec.py` 驗：每項恰一去向、標題子序列、引文逐字命中匯出、識別字／客戶名掃描（正負對照）、套到 scratch 後 `drafts_diff` PASS。五組結果：G1 改寫 18／標題刪字 9／講法刪除 1；G2 改寫 14／標題刪字 4（forcebinding 4 條依業主裁定改寫為舊版流程）；G3 改寫 16／標題刪字 6／整句刪 3／講法刪除 1；G4 改寫 20／標題刪字 5／交業主 2；G5 改寫 12／標題刪字 6／整句刪 1／講法刪除 1。引文 918 筆，未命中 0。
  - 檢查腳本兩處修正：依據路徑前綴 `help:`／`code:` 未剝除（誤報 1 筆，引文本身命中）；門鎖品牌名 `SkyWatch` 列白名單（已審正本 G 架已用 2 次）。
- **先審（verifier，五組各一位，各混 1 條誘餌）**：五組皆有效（`check_batch` 錯誤 0）、誘餌皆抓到並引用來源。不成立：G1 10、G2 1、G3 2、G4 6、G5 5。處置：改寫句仍不成立 ⇒ 整句刪（5 句）；原句新發現不成立 ⇒ 整句刪（10 句）；標題刪字 10 處（含刪句連動 3 處）；刪後無句 ⇒ 交業主 2 條（`jgb/E/bill-actions-progress`、`jgb/E/recharge-account-vs-single-use-atm`）。逐項見 `scratchpad/p929/G*/postreview-disp.json`。
- **事故（主 session，已救回）**：在 zsh 迴圈以未加引號的變數呼叫 `regen.sh`，`"G1 524"` 被當成一個參數，bash 內 `rm -rf $SP/p929/$G/regen` 拆字後刪除了 scratch `p929/G1`～`G5` 整個目錄，並在 repo 根目錄建出 `524/`、`526/`、`529/`、`532/`（內容僅為正本副本，`diff -r` 與正本相同；已刪除）。repo 正本、drafts、git 皆未受影響。救回：工作清單重產；起草產出由代理 transcript 中原寫檔指令依序重放；以先審證據重收驗證——五組 `check_batch` 錯誤 0（即每條 `content_sha256`／`title_text` 與先審當時逐字相同），重產 brief 字數與原版相同；先審後處置依原內容重套（句數變化與原次相同）。`regen.sh` 加參數檢查（恰 2 個、組名與數字格式、`allowed.json` 存在、路徑加引號），負對照：傳入合併參數 ⇒ 拒絕。
- **步驟 3b 刪後整條複查**（fresh verifier，15 條＋誘餌 1）：有效（`check_batch` 錯誤 0）、誘餌抓到。11 條成立；4 條不成立且只刪字刪句救不回 ⇒ 交業主：`jgb/A/signer-individual-fields`（標題答不到、「另需」承接已刪句）、`jgb/B/biglandlord-list-overview`（欄位列舉不完整）、`jgb/B/biglandlord-sheet-overview`（標題問句已無句子回答）、`jgb/G/power-meter-single-edit-tabs`（基本資料漏列一欄，與同粗目矛盾）。
- **終審單**：`inputs/review-sheet-9.29-20261004.md`（81 條；交業主 7 條；附帶觀察 32 項），客戶名掃描 0。
- **用量**：代理合計約 3.24M（就緒第 2 輪 0.08M、起草 5 組 1.26M、先審 5 組 1.54M、3b 0.36M），另有就緒第 1 輪（compaction 前，未計）。
- **業主終審**（2026-10-05，AskUserQuestion 逐字）：74 條修正「核可全部 74 條 (Recommended)」；`jgb/E/bill-actions-expense-paid`「保留原文，撤銷 9.28 判定 (Recommended)」；其餘 6 條（`jgb/E/bill-actions-progress`、`jgb/E/recharge-account-vs-single-use-atm`、`jgb/A/signer-individual-fields`、`jgb/B/biglandlord-list-overview`、`jgb/B/biglandlord-sheet-overview`、`jgb/G/power-meter-single-edit-tabs`）「全部延後整條刪 (Recommended)」。⇒ 寫入集合＝74 條；7 條不套 ops、原文與已審照舊。
- **W1（G1，寫入 16 條）**：5.1～5.5 全過——組基準快照 diff 相同；drafts 與 scratch 最終版逐條相同；repo 正本與 scratch 試跑 diff 相同；`canon_check` 區塊差異 16／允許 16、客戶名 0；`approve_write verify` mismatches 0；終點指標 pm 537／537、prospect 121／121；H 守護 PASS；unit 紅燈與基準差集 ∅。**寫入核對 verifier＝REFUTED**：14 條全條成立，2 條不成立——`jgb/A/dashboard-overview-lists`（標題與句 1 漏大房東例外：`Landlord.vue` 大房東分支不渲染帳單／合約列表與 Email 紀錄）、`jgb/B/advance-late-fee` 句 3（延遲金開關是建立合約時從團隊複製到合約，`Bill::canGenerateLateFeeBill` 判斷合約層 `enable_late_fee`；開啟前的既有合約不會產生）。對照細目（誘餌）抓到並引用來源。主 session 對碼確認兩條：非大房東分支才有 `<BillContractRepair />`；`UserController` 團隊延遲金設定段沒有任何合約更新（同段正對照 `role->` 命中 12）。⇒ 依 §4 停止條件：以 `W1-base` 還原 canon 與 runs，`git diff HEAD` 為空、`load_canon_or_die` 通過、他線 41 檔指紋不變；證據存 `scratchpad/p929/G1/write-W1.json`；停下交業主。
- **業主裁定**（2026-10-05，AskUserQuestion 逐字）：上述 2 條「比照其餘 6 條延後整條刪 (Recommended)」；之後規則「被推翻的細目自動視同延後整條刪 (Recommended)」——寫入核對推翻某細目 ⇒ 該組以組基準快照還原、把被推翻的細目移出寫入集合（A1 去向「業主裁定延後整條刪」）、其餘重新寫入，並由一位 fresh verifier 對剩下的細目重新核對；全條成立才 commit，再被推翻 ⇒ 停下交業主（取代 §4「寫入核對推翻任一句 ⇒ 該組還原、停下交業主」）。延後整條刪累計 8 條。
- **W1 重寫（14 條）**：5.1～5.5 全過（`approve_write verify` mismatches 0；終點指標 pm 537／537、prospect 121／121；H 守護 PASS；unit 3946 通過、紅燈 9 與基準差集 ∅）。**fresh 寫入核對＝REFUTED**：13 條全條成立；`jgb/A/forget-password-flow` 句 5（原句，未改動）不成立——失敗彈窗是 `'密碼設定失敗：' + (result.message || '請檢查輸入格式')`，而 `AuthController` `updatePassword` 的失敗回傳都不設 `message`（只在成功路徑設，同段正對照命中 2），彈窗永遠顯示固定字「請檢查輸入格式」，不是「失敗原因」。對照細目（誘餌）抓到。主 session 對碼確認。⇒ 依業主規則「再被推翻 ⇒ 停下交業主」：以 `W1-base` 還原，`git status` 對 canon／runs 為空、`load_canon_or_die` 通過、他線 41 檔指紋不變；證據存 `scratchpad/p929/G1/write-W1b.json`。代理用量累計約 3.78M。
- **業主裁定**（2026-10-05，AskUserQuestion 逐字）：「被推翻就延後，其餘用同一位核對的結論 (Recommended)」——`jgb/A/forget-password-flow` 延後整條刪（累計 9 條）；之後每組：寫入核對推翻的細目移出寫入集合（延後整條刪）、其餘重新寫入，證據由同一位寫入核對代理重貼它已判全條成立的那些細目（`content_sha256`／`title_text` 由不變量 43 W 規則逐條比對本 commit 正本），不再另派新代理。
- **W1 第三次寫入（13 條）**：5.1～5.5 全過（區塊差異 13／允許 13；`approve_write verify` mismatches 0；終點指標 pm 537／537、prospect 121／121；H 守護 PASS；unit 3946 通過、紅燈與基準差集 ∅）。同一位寫入核對代理重貼它已判全條成立的 13 條（不重新查證）⇒ `verification/20261005-p929-W1-write.json`：CONFIRMED、13 條＝寫入集合、每條 `content_sha256`／`title_text` 與本次正本相同、客戶名 0。
- **W2（G2，C 架 11 條）**：5.1～5.5 全過；寫入核對推翻 1 條——`jgb/C/estate-rent-open-permission-and-validation` 句 1 引號內「刊登物件」不是現行介面文字（現行預覽頁按鈕為「刊登」；「刊登物件」只在註解與已註解的舊路由選單），主 session 對碼確認 ⇒ 依業主規則延後整條刪（累計 10 條），以 `W2-base` 還原後重寫 10 條：5.1～5.5 全過（區塊差異 10／允許 10；`approve_write verify` mismatches 0；終點指標 pm 537／537、prospect 121／121；H 守護 PASS；unit 紅燈與基準差集 ∅）；同一位核對代理重貼 10 條 ⇒ `verification/20261005-p929-W2-write.json` CONFIRMED（逐條 sha／標題與正本相同、客戶名 0）。核對代理另提「待查」：招租店舖資訊儲存路徑疑似缺少「是否屬於被編輯的團隊／房東」的授權檢查（讀碼推論、未實跑；與 9.28 B09 交業主同一處），交業主另案。
- **W3（G3，D 架 19 條）**：5.1～5.5 全過（區塊差異 19／允許 19；`approve_write verify` mismatches 0；終點指標 pm 537／537、prospect 121／121；H 守護 PASS；unit 紅燈與基準差集 ∅）；寫入核對一次全條成立（對照細目抓到）。初版證據 notes 含一個特定合作團隊名稱的程式識別字（客戶名掃描命中 1）⇒ 請同一位代理只改寫該處、判定逐字不動後重貼 ⇒ `verification/20261005-p929-W3-write.json` CONFIRMED（19 條＝寫入集合、逐條 sha／標題相同、客戶名 0）。核對代理附記：審閱天數「團隊可調整」實為內部後台按團隊設定、業者端無設定畫面（措辭待業主另裁）；幫助中心紙本上傳 10MB 與程式 15MB 不一致。
- **W4（G4，E 架 15 條；交業主 2 條不套）**：5.1～5.5 全過（區塊差異 15／允許 15；`approve_write verify` mismatches 0；終點指標 pm 537／537、prospect 121／121；H 守護 PASS；unit 紅燈與基準差集 ∅）；寫入核對一次全條成立（對照細目抓到）⇒ `verification/20261005-p929-W4-write.json` CONFIRMED（15 條＝寫入集合、逐條 sha／標題相同、客戶名 0）。核對代理附記：同粗目 `jgb/E/balance-invoice-unsigned-contract` 句 2 未排除社會住宅與押金設算息帳單不寄信的情形（下次補核）。
- **W5（G5，F／G／I 架 14 條；交業主 1 條不套）**：第一次寫 13 條，寫入核對推翻 2 條——`jgb/I/demo-form-actual-validation-scope` 句 1、`jgb/I/demo-form-fields` 句 2（列「設了必填」的欄位漏了職稱、物件數量、團隊人數三個同樣標 `required` 的下拉選單；主 session 對碼確認，正對照「公司名稱」同樣有 `required`）⇒ 依業主規則延後整條刪；以 `W5-base` 還原後重寫 11 條：5.1～5.5 全過（區塊差異 11／允許 11；`approve_write verify` mismatches 0；終點指標 pm 537／537、prospect 121／121；H 守護 PASS；unit 紅燈與基準差集 ∅）；同一位核對代理重貼 11 條 ⇒ `verification/20261005-p929-W5-write.json` CONFIRMED（逐條 sha／標題相同、客戶名 0）。
- **收尾（A1 對帳）**：`inputs/dispositions-9.29-20261005.json`（由 `scratchpad/p929/gen_ledger.py` 機械產生）——111 項每項恰一個去向：改寫 64、標題刪字 25、整句刪 6（其中 2 項為改寫後先審仍不成立）、業主裁定延後整條刪 14、業主裁定保留 2。寫入 68 條（W1 13、W2 10、W3 19、W4 15、W5 11）；不套修正 13 條＝保留原文 1 條（`jgb/E/bill-actions-expense-paid`，9.28 判定撤銷）＋延後整條刪 12 條（`jgb/E/bill-actions-progress`、`jgb/E/recharge-account-vs-single-use-atm`、`jgb/A/signer-individual-fields`、`jgb/B/biglandlord-list-overview`、`jgb/B/biglandlord-sheet-overview`、`jgb/G/power-meter-single-edit-tabs`、`jgb/A/dashboard-overview-lists`、`jgb/B/advance-late-fee`、`jgb/A/forget-password-flow`、`jgb/C/estate-rent-open-permission-and-validation`、`jgb/I/demo-form-actual-validation-scope`、`jgb/I/demo-form-fields`），留在正本、原文與已審照舊，下份計畫先建整條刪除工具再刪除並重新起草。
- **教訓**：fresh 代理每一輪都會再抓到前一輪沒抓到的錯（先審後 3b 又推翻 4 條、寫入核對又推翻 6 條，多為排他列舉與漏例外）。業主裁定「被推翻就延後、其餘用同一位核對的結論」避免無限循環。
- **用量**：代理合計約 5.0M（不含就緒第 1 輪）；規格 §5 總上限 30M。
- **收尾結果驗證**（fresh verifier，BRIEF-CONTRACT v1，對凍結清單 A1～A12；HEAD `c6e7ac3d`）：REFUTED，P2×1——A8「起草與先審證據掃描結果記 §6」未做到，且以不分大小寫的擴充詞表另有命中未逐筆說明；其餘 A1～A7、A9、A10、A12 獨立重算全過，抽查 8 句（W1～W5 各至少 1 句）全部成立；A11 的 `--roundtrip` 被代理端權限分類器擋下未重跑。處置：**FIX**（本計畫引入、在 A8 範圍內、以 A8 允許的「逐筆說明」補齊），並由主 session 重跑 `edit_fine.py --roundtrip`：九架（H 除外）位元組不變。
- **A8 掃描結果（補記）**：詞表＝`canon_check.py` 的 `PAT`；正對照（合成客戶名）命中、負對照（「系統上」）不中。
  - 分大小寫（原詞表）：起草產出（`check_exec.py` 步驟 4）0；先審證據 G1～G5 與 3b 證據 0；寫入證據 W1～W5 0（W3 初版命中 1，已請代理改寫後重貼）；終審單 0；去向對帳檔 0；正本 `jgb.json`、`jgb/*.md`、`CATALOG.md` 0。
  - 不分大小寫（擴充）：本計畫 16 個檔共命中 1——`verification/20261004-p929-prereview-G4.json` notes 內引用的一個程式識別字（某特定合作團隊的群組旗標變數名，該句同時註明「部分特定合作團隊沒有」）。drafts 改動細目比 base 多 1——`jgb/E/bill-power-reading-draft-defaults` 的 evidence 逐字引文（同一個變數名；00c 規定 evidence 必須逐字引程式，識別字只准出現在 evidence）。**說明**：此識別字是 jgb2 原始碼裡的變數名，不是客戶名稱的文字敘述；base `f13b0cb5` 已有 6 個已 commit 檔含同一識別字、19 個檔含其字根（不分大小寫），本計畫沒有新增可對外理解的客戶資訊；正本（對話時會被引用的部分）不分大小寫 0 命中。⇒ 依 A8「命中須為 0 或逐筆說明」記錄於此，不改寫已 commit 的證據檔。
