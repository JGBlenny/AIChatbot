# Plan 9.22：剩餘 14 條未審細目收尾（新 D1）

> **現況**（`endpoint_progress.py`，2026-10-03，HEAD `7aac4142`）：`已審細目 pm 519／533、prospect 116／120；頁面 pm 133／183、prospect 52／183`（A 59／62、B 78／78、C 78／81、D 99／104、E 96／96、F 33／33、G 26／26、H 5／5、I 45／48）；`jgb.json` 已審 525／539。
>
> **本計畫預期**：
> - 細目：14 條全審為上限（pm +14、prospect +4 ⇒ pm 533／533、prospect 120／120）；依 9.21 終審核可率（W1 37／43＝86%、W2 27／35＝77%）與「安全組過」規則，預期 pm +10～13、prospect +2～4。修正片與重審片都是 +0。
> - 頁面：現有細目全審時的上限 pm 138、prospect 53（`endpoint_progress.py --ignore-review` 正對照：`頁面 不分身分 138／183；pm 138、prospect 53`）⇒ 本計畫頁面最多 pm +5、prospect +1。之後的頁面缺口須新起草細目，不在本計畫（§2）。

## 0. 為什麼有這份

- 業主 2026-10-03「a」——對選項「(a) 開 Plan 9.22 收尾 14 條（建議）：我先寫計畫、送就緒審查，再交您核可，照例設上限與停點」。
- 9.21 收案後未審 14 條（pm 14、prospect 4），以各自最近一次先審結論分組：

  | 組 | doubt | ⚠️ 組 pass | 先審出處（審核單＋raw） |
  |---|---|---|---|
  | A／C | 3（A 1、C 2） | 3（A 2、C 1） | `review-sheet-9.21-W1-S2-ABC-20261003.md`＋`scratchpad/p921-s2/p921-s2-raw-*` |
  | D／I | 3（D 2、I 1） | 5（D 3、I 2） | `review-sheet-9.21-W2-S2-DEFI-20261003.md`＋`scratchpad/p921-w2s2/p921-w2s2-raw-*` |

  - doubt 6 條：`jgb/A/account-contact-info`、`jgb/C/estate-dashboard-attachments-vs-contract-attachments`、`jgb/C/team-public-page-recruitment`、`jgb/D/contract-upload-existing-vs-electronic`、`jgb/D/general-contract-notary-tab`、`jgb/I/pricing-free-vs-experience-plan`。
  - ⚠️ 組 pass 8 條：`jgb/A/account-basic-info`、`jgb/A/account-change-password`、`jgb/C/estate-dashboard-runnings-vs-memos`、`jgb/D/contract-show-panels`、`jgb/D/contract-thinkcloud-esign-service`、`jgb/D/contract-thinkcloud-signing-variants`、`jgb/I/pricing-free-trial-eligibility`、`jgb/I/pricing-quota-full-block`。
  - 已查（2026-10-03，`7aac4142`）：14 條＝正本未審全集；審核單與 raw 逐 id 判定相同；判定後內容未變（`git diff --stat ca8b3a08 -- drafts-A／C`、`git diff --stat 59a43bce -- drafts-D／I` 皆空；`.md` 自該正本起只新增 `- reviewed:` 行，非 reviewed 新增行 0，正對照 A.md reviewed 新增 7）。
- D1 沿用 9.21「修整條」（§1 引用 9.21 §1「新 D1」全文規則）：9.21 兩波重審抓回合併 3／46＝6.5%（舊 D1 16～21%）。

## 1. 切片（順序：S1 → commit → S2 → S3 → commit）

各片步驟、驗收、停止、擁有與 9.21 對應片相同（**S1 底片＝9.21 W2-S1、S2 底片＝9.21 W2-S2、S3 底片＝9.21 W2-S3**）；以下只寫差異，所有常數逐項改寫，⛔ 沿用 9.21 的值。D1 規則、範圍標記（`依據 #n`／`整條 #m`／兩者）、「整條待裁」「停下交業主」「另見」各節定義＝9.21 §1「新 D1」。工具來源：`scratchpad/p921-w2/`（修正片）、`scratchpad/p921-w2s2/`（重審與寫入）、`scratchpad/jgb2-b2ee2ac/`；開工前確認仍在，不在就依 HANDOFF §12-3 從 transcript 重建。

### S1 — A／C／D／I 6 條 doubt 依新 D1 修正（+0）

- scratch 目錄 `p922-s1/`；修正紀錄 `inputs/fix-log-9.22-S1-ACDI-<日期>.md`；ops 存 `p922-s1/ops.json`；工具自 `p921-w2/` 複製（edit_fine、drafts_diff、canon_check、name_scan、customer-terms、coverage_check、scope_check、apply_ops、templates），值不改。
- **允許集合** `p922-s1/allowed.json` **6 條**（§0 doubt 清單）；兩來源（審核單、raw）不等或條數≠6 ⇒ 停。
- **疑點理由來源（唯一）與檢查（已預跑，2026-10-03）**：工作清單 DOUBT 行與修正紀錄「## 依據」只取 `p922-s1/doubt-raw.json`，它由 `p921-s2/p921-s2-raw-W1S2B*.txt`（A／C）與 `p921-w2s2/p921-w2s2-raw-W2S2B*.txt`（D／I）逐字取出（每 id 恰一行、皆 doubt）；⛔ 讀 `p920-*`、`p919-recovered` 等舊 raw（其中 `contract-upload-existing-vs-electronic`、`pricing-free-vs-experience-plan` 有已修過的舊理由）。
  - 工作清單 `p922-s1/worklist.txt`（6 條）已產生；修正紀錄由 `p922-s1/build_fixlog.py` 產生：標題「# Plan 9.22 S1 修正紀錄（A／C／D／I 疑點 6 條，新 D1「修整條」）」、依據標籤「（9.21 W1-S2 doubt）」（A／C）／「（9.21 W2-S2 doubt）」（D／I）、輸出 `inputs/fix-log-9.22-S1-ACDI-<日期>.md`。
  - 機械檢查 `p922-s1/doubt_source_check.py worklist|fixlog <檔>`：6 條的句序與理由與 raw 逐字相同；殘留字串 `9.19 S2`、`9.20 S`、`p919-recovered`、`p920-`、`W1-S1`、`W2-S1`、`10MB` 在 DOUBT 行（工作清單）／表頭＋依據節（修正紀錄）0 命中；不符即 exit 1。**派 executor 前跑 worklist、派核對 verifier 前跑 fixlog，FAIL 不派工。**
  - 預跑：worklist ⇒ `matched 6; residual 0`、PASS；`build_fixlog.py --basis-only` ⇒ fixlog PASS，`contract-upload-existing-vs-electronic` 依據含「最新 109 年」、不含「10MB」。負對照：把該條 DOUBT 換成 9.20 S5 舊理由 ⇒ `worklist DOUBT != raw`＋`10MB` 殘留、FAIL；對 9.21 W2 修正紀錄跑 fixlog ⇒ 3 條 `依據 != raw`＋`9.20 S`／`p920-`／`W2-S1`／`10MB` 殘留、FAIL。正對照：9.21 W2 修正紀錄含 `9.20 S` 22、`10MB` 2；`p921-w2/w1-builder.txt` 含 `p919-recovered` 2。
- **備份** `p922-s1/backup/`（drafts、runs 整個目錄、canon），須早於第一次 repo 編輯；九架 roundtrip 全 True；客戶名掃描 hits 0。
- **不變位元組**：drafts-B／E／F／G／H 與 `canon/jgb/B.md`、`E.md`～`H.md` 與備份 `cmp` 相同；A／C／D／I 只允許允許集合內細目變動、CATALOG 只允許允許集合內細目的行變動（`canon_check`）。
- **終點指標（+0）**：開工前與完成後都須為 `已審細目 pm 519／533、prospect 116／120`；已審集合維持 **525** 條。
- 重生成 `--expect-reviewed-kept 525 --expect-open-questions 54`（`--runs-out` 寫 scratch 再複製回 repo，日期標 `<日期>-s1-922`）。
- **起草**：executor，brief `p922-s1/brief-executor-fix.md`＝`p921-w2/brief-executor-fix.md` 機械替換，**替換表（8 處，已預跑）**：片名「Plan 9.21 W2-S1 — D／E／F／I 21 條」⇒「Plan 9.22 S1 — A／C／D／I 6 條」；目錄 `p921-w2` ⇒ `p922-s1`（含工作清單 `p922-s1/worklist.txt`，含 doubt 理由、現行內容、同粗目標題）；`drafts-{D,E,F,I}.json` ⇒ `drafts-{A,C,D,I}.json`；待裁 `open-questions-20261003-w1s1-921.md` ⇒ `open-questions-20261003-w2s1-921.md`（54 則，現行最新）；條數 21 ⇒ 6（工作清單、只改範圍、自檢、最後一則摘要四處）。新 D1 與 Hard rules 其餘逐字沿用。
  - **驗收（已預跑，2026-10-03）**：
    - 殘留字串 0 命中：`p921`、`W2-S1`、`D／E／F／I`、`D,E,F,I`、`w1s1-921`、`21 條`、`21 個`、`9.21`（正對照：W2 版依序 2／1／1／1／1／4／2／1）；
    - 新值恰在：`w2s1-921` 1、`drafts-{A,C,D,I}` 1；
    - 與 W2 版 `diff` 只有替換表的 8 行不同（其餘逐字相同）。
  - 套到 scratch 副本、`drafts_diff --list` 產出改動項後，同一 executor 續做 `scope-map.json` 與 `whole-basis.md`；主 session 對匯出逐字 grep 後才寫入修正紀錄。
- **修正核對 verifier**：一包（6 條）；brief 由 `p921-w2/brief-fix-DE.txt` 機械替換，**替換表**：
  1. 首行「Plan 9.21 W2-S1」「D＋E 架」⇒「Plan 9.22 S1」「A＋C＋D＋I 架」；改動項數、細目數（首行「N 個改動項（涉及 M 條細目）」與末行 `總 N`）⇒ `drafts_diff --list` 實數；
  2. 「## 改動項」清單 ⇒ 本片改動項；
  3. 修正紀錄路徑 ⇒ `inputs/fix-log-9.22-S1-ACDI-<日期>.md`；依據來源「D／E＝9.20 S5 先審、F／I＝9.20 S2 先審的 doubt 理由」⇒「A／C＝9.21 W1-S2 先審、D／I＝9.21 W2-S2 先審的 doubt 理由」；
  4. 改後檔名 `drafts-D.json、drafts-E.json` ⇒ `drafts-A.json、drafts-C.json、drafts-D.json、drafts-I.json`；改前備份 `p921-w2/backup/drafts/` ⇒ `p922-s1/backup/drafts/`；
  5. 待裁路徑 `open-questions-20261003-w1s1-921.md` ⇒ `open-questions-20261003-w2s1-921.md`。
  - 判準段（「## 每一項判什麼」以下）逐字沿用。
  - **驗收（機械，派工前）**：
    - 殘留字串 0 命中：`W2-S1`、`fix-log-9.21`、`p921-w2/`、`D＋E`、`drafts-E`、`9.20 S`、`w1s1-921`、`13 條`、「只修 doubt 所指」（正對照：`brief-fix-DE.txt` 依序 2／1／1／1／1／1／1／1，`templates/brief-fix-verify.txt` 對「只修 doubt 所指」1）；
    - `fix-log-9.22-S1-ACDI-` 恰 1 命中、`w2s1-921` 恰 1 命中；
    - 首行改動項數＝末行 `總 N`＝「## 改動項」行數，首行細目數＝該清單相異 id 數；
    - 「## 每一項判什麼」以下與 `brief-fix-DE.txt` 逐字相同。
    - 任一不符 ⇒ 不派工、修 brief。
  - **複核 brief**（D1 修一次後）：由 `p921-w2/brief-recheck.txt` 以同一替換表（片名、包名改「（A／C／D／I 架）」、件數、改動項、上一輪不過理由段、改前／ops 路徑改 `p922-s1/`、修正紀錄、依據來源、改後檔名、改前備份、待裁路徑）產生，派工前過**同一組**殘留字串、新值與判準段相同檢查（正對照：`brief-recheck.txt` 含 `W2-S1`、`fix-log-9.21`、`9.20 S`、`w1s1-921`、`p921-w2/`）。
- `drafts_diff` 以 `P919_DIFF_SHELVES=ABCDEFGHI` 執行（(a)～(g) PASS）；`scope_check` PASS；`coverage_check` 6 條全數有去處；整條列逐列有 fresh verifier 判定。不過項依 D1 修一次＋複核；片末 fresh outcome verifier。
- commit 範圍：drafts-A／C／D／I、`canon/jgb/A.md`、`C.md`、`D.md`、`I.md`、CATALOG、`jgb.json`、runs `*-<日期>-s1-922*` 三檔、修正紀錄、本計畫；`git diff --cached --name-only` 範圍外 0。
- 預算約 0.5M（9.21 W2-S1 實績 1.55M／21 條按 6 條折算＋固定開銷）。

### S2 — 14 條重新先審（+0）

- 工作區 `scratchpad/p922-s2/`：`review_sheet.py`、`extract_verdict.py`、`d1_measure.py` 由 `p921-w2s2/` 複製，變更值 `CANON_COMMIT="<S1 commit>"`、`SHELVES` 預設 `ACDI`、`PREFIX="p922-s2"`、標題「Plan 9.22 S2 A／C／D／I 修正後重新先審」。
- `p922-s2-targets.json`：現行正本未審 **14** 條（＝S1 允許集合 6＋⚠️ 組 pass 8；條數≠14 ⇒ 停）。批次：一批 `S2B1` 14 條（正本順序、粗目不拆）；hold＝`[]`。
- brief `brief-prereview-S2B1.txt`：由 9.20 S2 原文（`p921-w2s2/s2-brief-recovered.txt`）機械替換批次、條數、架、id 清單、待裁路徑（S1 重生成的 `open-questions-<日期>-s1-922.md`）與匯出路徑；判準段逐字沿用；grep `W2-S2`、`W2S2`、`w2s1-921` 皆 0 命中（正對照：`p921-w2s2/brief-prereview-W2S2B1.txt` 各命中 ≥1）。S1 修正紀錄⛔ 不給先審代理。
- 預跑（開工前）：非空合成輸入（14 條中 1 條 doubt）⇒ `parse`／`sheet`／`check` 對帳 0 不一致；負對照刪 1 行 ⇒ `missing ids`、exit 1；`d1_measure` 合成 doubt 落在允許集合 ⇒ 比例可算、真 results 空 ⇒ exit 2。
- **D1 量測**：分母＝S1 修正表中且在 targets 內的細目（排除「已由前案處理」「停下交業主」）；§6 記本計畫值與 **9.21＋9.22 合併值**（分子相加／分母 46＋本計畫分母）。
- **驗收**：raw 機械取出；`check` ⇒ `targets 14; judged 14; raw-parsed 14; sheet ids 14`、`mismatches: 0`；審核單 `inputs/review-sheet-9.22-S2-ACDI-<日期>.md`；正對照（審核單副本／raw 副本各改一條 ⇒ 兩者都報不一致）；正本相對 S1 commit 的 `git status`／`git diff --stat` 為空。
- **終點指標（+0）**：開工前與完成後都須為 `已審細目 pm 519／533、prospect 116／120`（已審 525）。
- **停止與回滾**：交件失敗同一代理重貼一次，仍失敗即停；回滾只刪審核單與 `p922-s2` 檔。
- 預算約 0.3M。

### S3 — 業主終審＋寫入（pm 最多 +14）

- 工具 `p922-s2/approve_write.py`：由 `p921-w2s2/` 版複製，results／targets／hold 改讀 `p922-s2-*`、PLAN 改指本計畫、段落 `### S3`；寫入架 `P918_WRITE_SHELVES=ACDI`；`P918_SHEET=<S2 審核單絕對路徑>`。業主原文先逐字記入 §6「### S3」再 derive。
- 預跑同 9.21 W2-S3：derive（兩來源相等）、reply 不在 §6 ⇒ 大聲失敗；scratch 正本 write／重匯出／verify（`reviewed backup 525 -> current 525+N`、`fines changed beyond reviewed_*: 0`）；scratch 重生成保留檢查（`--expect-reviewed-kept 525+N`）；scratch 終點指標；scratch 正本掛容器跑全套單元差集。
- **對 repo 執行**：備份 `scratchpad/p922-s3-backup/`；git 基準（S1 commit）與 status 皆空 ⇒ write ⇒ 重匯出 ⇒ verify ⇒ repo 與預跑 `diff -r` ⇒ 終點指標、單元差集、`make audit` ⇒ fresh outcome verifier（含抽驗）⇒ commit。
- **抽驗**：核可數 ≥ 12 時以 `random.Random(20261003).sample(sorted(approved), 12)`，否則全抽；派工前固定並記入 §6；推翻定義與處置同 9.21 W1-S3（還原用 `p922-s3-backup/`）。
- commit 範圍：A／C／D／I `.md`、`jgb.json`、S2 審核單、本計畫、HANDOFF（終點行與現況）；`git diff --cached --name-only` 範圍外 0。
- 預算約 0.35M。

## 2. 不做（另案）

- 新起草細目（pm 真缺口約 11～12 頁，`inputs/page-gap-9.18-20260928.md` §0）、頁面量尺改造、prospect 可見頁範圍定義——待業主裁（HANDOFF §12-4）。
- 54 則待裁、jgb2 缺陷清單（含 9.21 W2-S1 新發現的未訂閱版額度彈窗）、6 條 `sources` 必填紅燈。
- 講法核可（`approved`）與回答品質量測。
- 9.21 各片延後的措辭建議與 P4 附記。

## 3. 業主裁決與待裁

- **已裁（2026-10-03「a」）**：見 §0。核可前不動正本。
- **業主裁決（2026-10-03）**：「核可」——核可大綱＋S1；執行模式沿用 ASK（每片回報）；S2、S3 開工前各自再送就緒審查。

## 4. 停止條件（全片共用）

- 已審細目數任何時候下降 ⇒ 停。
- 正本只准在 S1 重生成（只動允許集合）與 S3 寫入（只加 reviewed 行）時變動。
- **總上限 1.3M；S1 commit 後累計 > 0.7M ⇒ 停下回報業主**；超過上限即停。
- 一次只跑一個代理（本機 8GB）。
- 代理 brief 一律帶 HANDOFF §12-2 必禁清單。

## 5. 就緒審查紀錄

- **第 1 輪（fresh plan-verifier，大綱＋S1）＝REVISE**（2026-10-03）：P2×2——(1) executor brief 的 grep 驗收漏了 `drafts-{D,E,F,I}`、待裁路徑 `w1s1-921`、自檢「21 個」三個 9.21 值；(2) verifier brief 替換表第 5 項寫「待裁路徑不變」但底稿實為 `w1s1-921`，grep 也漏 `D＋E`、`drafts-E`、`9.20 S`、`13 條`，複核 brief 無替換與檢查規則。處置：兩項皆 **FIX**——executor brief 已預跑產生，替換表寫成 8 處逐項、殘留 8 字串 0 命中（附正對照實測值）、與底稿 `diff` 只差替換的 8 行；verifier brief 改正第 5 項、殘留檢查擴為 9 字串＋新值恰 1＋件數一致＋判準段逐字相同；複核 brief 納入同一替換表與檢查。送第 2 輪。
- **第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×1——工作清單的 doubt 理由與修正紀錄「依據」節沒寫來源與檢查；照 9.21 的產生器複製會讀到 9.20 舊 raw，`contract-upload-existing-vs-electronic` 與 `pricing-free-vs-experience-plan` 會拿到已修過的舊理由，S1 的現有檢查都攔不到。⇒ **第二次自動 REVISE，停止重送、逐條處置**：**FIX**——疑點來源限定兩份 9.21 重審 raw、工作清單與修正紀錄產生器已寫出並預跑、新增 `doubt_source_check.py`（逐字比對＋殘留字串，附正負對照），派工前必過。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **收尾審查（fresh plan-verifier）＝READY**（2026-10-03）⇒ 大綱＋S1 交業主核可（`next_gate: user_approval`）。S2、S3 開工前各自再送就緒審查。

## 6. 執行紀錄

### S1（2026-10-03）

- **允許集合**：`p922-s1/allowed.json` 6 條，兩來源逐 id 相同（§0）。工具自 `p921-w2/` 複製；備份 `p922-s1/backup/`（19:52:52，早於第一次 repo 編輯 20:10:29）；九架 roundtrip 全 True；客戶名 0；開工前終點指標 `pm 519／533、prospect 116／120`。
- **派工前檢查**：`doubt_source_check.py worklist` PASS（6／6 與 9.21 重審 raw 逐字相同、殘留 0）；executor brief 殘留 8 字串 0、與底稿只差替換的 8 行。
- **起草**：executor 產出 `ops-draft.json`＋`fix-notes.md`（6 條全修、停下 0；整條修正 17 項；整條待裁 1 項），續做 `scope-map.json`（doubt 15／whole 20／both 0）與 `whole-basis.md`（6 條）。主 session 審閱筆記並機械驗證：6 id＝允許集合；新 evidence 107 筆＋整條依據 11 筆逐字命中；新文字客戶名 0；先套 scratch 再套 repo，九架與試套逐位元組相同、B／E／F／G／H 與備份相同。
  - executor 回報「`edit_fine.py` 的 TRAIL 缺 D」不成立：`p922-s1/edit_fine.py` 已含 `"D": "\n"`，D 架 roundtrip True、套用成功（其所指為另一份檔，未採用）。
  - 修正紀錄產生器未解析本次筆記的 (d)／(e) 小節格式 ⇒ 「整條待裁」1 條、「另見」5 條由主 session 依筆記手寫（含 jgb2 缺陷候選：招募頁「買賣中物件」切換會把網址弄壞）。
- **修正紀錄** `inputs/fix-log-9.22-S1-ACDI-20261003.md`：修正表 35 列、整條依據 6 條、整條待裁 1 條、另見 5 條；`scope_check`／`coverage_check`／`doubt_source_check fixlog` PASS、drafts_diff (a)～(g) PASS。
- **核對**：verifier brief 派工前檢查 PASS（殘留 9 字串 0、修正紀錄路徑恰 1、件數 35／6 一致、判準段逐字相同）。**34／35**；不過 1 項（`general-contract-notary-tab` 句 6 漏「車位合約與部分特定合作團隊專用範本沒有公證分頁」例外，P2 本片引入）依 D1 修一次，複核 **7／7 CONFIRMED**。**整條列 20，過 20／不過 0**。附建議 1 則延後。
- **重生成**：scratch 試跑後對 repo 跑：`已審保留：525 條／丟棄：0 條`、57 粗目／539 細目、open_questions 54 則（內文與 `w2s1-921` 版相同）；DSP-068 刪除 36 行／37 字元。repo 與試跑、3 個 runs 產出逐位元組相同。`canon_check` ⇒ `blocks changed 6 (in allowed 6)`、`mismatches: 0`，客戶名 0；B／E／F／G／H `.md` 與備份相同。`load_canon_or_die` 通過。
- **終點指標 `已審細目 pm 519／533、prospect 116／120；頁面 pm 133／183、prospect 52／183`**（不變，符合 +0；已審 525）。
- **單元與 audit**：`9 failed, 3931 passed, 3 skipped`，與基準差集＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（5 項＋終點指標重跑全過，無 P0～P2）：自行重跑四支檢查；6 條「依據」與 9.21 重審 raw 理由逐字相同；jgb.json 已審 525 集合不變、變動恰為 6 條允許集合；6 條標題＋共 40 句逐句對釘住匯出全部成立，原 doubt 皆不再成立（「109 年」「下載不限」「每月付費」0 命中、公證分頁補上無分頁例外）；整條待裁項不選邊；客戶名 0；負對照 2 筆皆 0。附記 P4×4（依據 #6 句序格式「句序 標題」、上傳合約 S5「帳單設定」對部分特定合作團隊不成立宜加限定、scratch 複核 brief 含一個範本代碼、社宅句沿用社宅看不到的選單標籤），延後。
- **成本**：S1 約 0.85M（executor 起草＋範圍對照 0.30M、核對 0.17M、複核 0.11M、outcome verifier 約 0.17M、主 session 約 0.1M 估算）。⚠️ 超出本片預算 0.5M；**累計約 0.85M，越過 S1 停點 0.7M ⇒ S1 commit 後停下回報業主**（S2 估 0.3M＋S3 估 0.35M ⇒ 總額約 1.5M，超過上限 1.3M）。
