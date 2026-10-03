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
- **已預跑**（2026-10-03，S1 commit `fd89adaa` 後；repo 未動）：
  - 工作區 `scratchpad/p922-s2/`：三支工具由 `p921-w2s2/` 複製，變更值 `CANON_COMMIT="fd89adaa"`、`SHELVES` 預設 `ACDI`、`PREFIX="p922-s2"`、標題「Plan 9.22 S2 A／C／D／I 修正後重新先審」。
  - `p922-s2-targets.json`：現行正本未審 **14** 條（允許集合 6 全在其中）；`p922-s2-batches.json`：一批 `S2B1` 14 條、6 組（A-account-profile 3、C-estate-dashboard 2、C-team-storefront 1、D-contract-sign-view 2、D-notary 3、I-pricing 3）；hold＝`[]`。
  - brief `brief-prereview-S2B1.txt`：待裁路徑改為 S1 重生成的 `open-questions-20261003-s1-922.md`（內文與前版相同，54 則）；殘留 `W2-S2`、`W2S2`、`w2s1-921` 皆 0（正對照 W2 版各 1）；id 行 14；判準段與 W2 版逐字相同。
  - 非空合成預跑（`scratchpad/p922-s2-pc/`，14 條中 1 條 doubt）：`parse` ⇒ `parsed 14 ids: pass 13 / doubt 1`；`sheet` ⇒ `groups 6 … pending 0`；`check` ⇒ `targets 14; judged 14; raw-parsed 14; sheet ids 14`、`mismatches: 0`；負對照刪 1 行 ⇒ `❌ S2B1: missing ids […]`、exit 1。實際工作區無合成 raw（`parse` ⇒ 0）。
  - `d1_measure`：合成 doubt 落在允許集合 1 條 ⇒ `ratio 1/6 = 16.7%`；真 results 空 ⇒ `fines without a re-review verdict`、exit 2。
  - 正本相對 `fd89adaa` 的 `git status`／`git diff --stat` 皆空。

### S3 — 業主終審＋寫入（pm 最多 +14）

- 工具 `p922-s2/approve_write.py`：由 `p921-w2s2/` 版複製，results／targets／hold 改讀 `p922-s2-*`、PLAN 改指本計畫、段落 `### S3`；寫入架 `P918_WRITE_SHELVES=ACDI`；`P918_SHEET=<S2 審核單絕對路徑>`。業主原文先逐字記入 §6「### S3」再 derive。
- 預跑同 9.21 W2-S3：derive（兩來源相等）、reply 不在 §6 ⇒ 大聲失敗；scratch 正本 write／重匯出／verify（`reviewed backup 525 -> current 525+N`、`fines changed beyond reviewed_*: 0`）；scratch 重生成保留檢查（`--expect-reviewed-kept 525+N`）；scratch 終點指標；scratch 正本掛容器跑全套單元差集。
- **對 repo 執行**：備份 `scratchpad/p922-s3-backup/`；git 前置（**限本片擁有路徑**）：`git diff --stat fd89adaa -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆空、`git status --short -- rag-orchestrator/tests/unit/agent/test_canon_assembler_req.py` 只有 ` M`（已核可的測試修正）；其他工作線的未 commit 檔（29 個路徑、41 個檔，清單與 sha256 指紋 `scratchpad/p922-s2/foreign-paths.txt`／`foreign-fingerprint.txt`，指紋摘要 `61712a4d4c4acce4`）是既有、非本線擁有的基準，本片 ⛔ 碰，commit 前重算指紋須相同。⇒ write ⇒ 重匯出 ⇒ verify ⇒ repo 與預跑 `diff -r` ⇒ 終點指標 ⇒ **該測試檔對 repo 正本單跑**（預期只剩基準內的 `test_prospect_view_fine_ids_match_id_map` 一條紅）⇒ 全套單元與 `p920-w2/red-baseline.txt` 差集＝∅ ⇒ `make audit` ⇒ fresh outcome verifier（**全數核對**＋測試檔核對）⇒ commit。
  - **單元測試跑的程式樹**：`scripts/run-tests.sh unit`（`docker-compose.dev.yml`，`./rag-orchestrator:/app` 掛載工作樹）＝目前工作樹，含上述其他工作線的未 commit 改動；`red-baseline.txt` 的 9 條即在同一工作樹（9.20 起逐片重跑皆 9 failed 同名，9.22 S1 後亦同）取得；指紋相同即程式樹相同。
- **全數核對**（業主 2026-10-03「我要確保成果品質」，取代抽 12 條）：outcome verifier 對 approved 的**每一條**逐條列標題與每句成立／不成立並附匯出證據；**另核測試檔**：`rag-orchestrator/tests/unit/agent/test_canon_assembler_req.py` 相對備份 `scratchpad/p922-s2/test_canon_assembler_req.py.bak` 的 diff 只動 `_mark_reviewed_except` 與 `test_prospect_outline_is_deterministic_and_registers_canon` 兩處、產品程式 0 改動（本片改動以擁有路徑判定：`git diff --stat fd89adaa -- rag-orchestrator` 相對 S3 開工前只多出 `rag-orchestrator/canon` 與該測試檔；其他工作線檔以指紋比對與開工前相同）、目標測試在 repo 正本通過、負對照（舊版測試在 prospect 全審正本會 `StopIteration`）成立；推翻定義與處置同 9.21 W1-S3（任一推翻 ⇒ 用 `p922-s3-backup/` 還原、`git diff --stat <S1 commit> -- rag-orchestrator/canon` 為空後停下交業主）；§6 記每條結果。
- **測試檔被推翻的處置**：outcome verifier 判測試改動不成立（超出兩處、動到產品程式、或目標測試未綠）⇒ 用 `.bak` 還原該檔（`cmp` 相同）、用 `p922-s3-backup/` 還原正本，`git diff --stat fd89adaa -- rag-orchestrator/canon rag-orchestrator/tests/unit/agent/test_canon_assembler_req.py` 為空後停下交業主。正本內容被推翻時同樣以此條件確認還原。
- commit 範圍（**8 檔**）：`canon/jgb/C.md`、`D.md`、`I.md`、`jgb.json`、S2 審核單、本計畫、HANDOFF（終點行與現況）、`rag-orchestrator/tests/unit/agent/test_canon_assembler_req.py`；A.md 本片核可 0 條、⛔ 應有 diff（`git diff --stat -- rag-orchestrator/canon/jgb/A.md` 為空）。`git diff --cached --name-only` 恰為此 8 檔、範圍外 0。
- 預算約 0.35M。
- **已預跑**（2026-10-03，業主終審回覆後；repo 正本未動）：
  - 工具 `p922-s2/approve_write.py`：由 `p921-w2s2/` 版複製，results／targets／hold 改讀 `p922-s2-*`、PLAN 改指本計畫、段落 `### S3`；決定檔 `p922-s2/p922-s3-decision.json`（rule＝safe）；業主原文已逐字記入 §6「### S3」。
  - derive（`P918_WRITE_SHELVES=ACDI`、`P918_SHEET=<S2 審核單>`）⇒ `approved 11 (both sources equal) by shelf {'A': 0, 'C': 3, 'D': 5, 'I': 3}; expected endpoint increment pm +11, prospect +4`。對照：reply 改成不在 §6 的字串 ⇒ `❌ decision reply is not verbatim inside plan §6 ### S3 record`；rule 改 all ⇒ 13。
  - scratch 正本 `p922-s3-pc/`：write ⇒ `added 11`；重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 525 -> current 536; added lines 11; approved 11`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；B／E／F／G／H、CATALOG 與備份相同。
  - scratch 重生成保留（`--expect-reviewed-kept 536 --expect-open-questions 54`）⇒ `已審保留：536 條／丟棄：0 條`，與 scratch 正本 `diff -r` 相同。
  - scratch 終點指標 `已審細目 pm 530／533、prospect 120／120；頁面 pm 140／183、prospect 53／183`。頁面上限因 S1 補了程式來源由 pm 138 升為 140（`--ignore-review` 重量：`pm 140、prospect 53`）。
  - **預跑發現新紅燈**：scratch 正本掛容器跑全套 ⇒ `10 failed, 3930 passed`，差集＝`test_canon_assembler_req.py::test_prospect_outline_is_deterministic_and_registers_canon`（`StopIteration`：取樣「第一條未審 prospect 細目」，prospect 全審後挑不到；HANDOFF §12-3「測試綁正本實際資料」同類）。⇒ 停下交業主，業主裁 (a)（§3）。
  - **測試修正（只改測試）**：`_mark_reviewed_except` 對 skip_ids 中原本已審者拿掉 reviewed 行；測試改取第一條 prospect 細目。驗：該測試檔在 scratch 正本（I.md reviewed 54）與現行正本（51）皆只剩基準內的 `test_prospect_view_fine_ids_match_id_map` 一條紅；負對照：還原舊測試於 scratch 正本 ⇒ 目標測試再紅。修正後 scratch 正本全套 ⇒ `9 failed, 3931 passed`，差集＝∅。
- **終點指標**：寫入後須為 `已審細目 pm 530／533、prospect 120／120`（pm +11、prospect +4）。

## 2. 不做（另案）

- 新起草細目（pm 真缺口約 11～12 頁，`inputs/page-gap-9.18-20260928.md` §0）、頁面量尺改造、prospect 可見頁範圍定義——待業主裁（HANDOFF §12-4）。
- 54 則待裁、jgb2 缺陷清單（含 9.21 W2-S1 新發現的未訂閱版額度彈窗）、6 條 `sources` 必填紅燈。
- 講法核可（`approved`）與回答品質量測。
- 9.21 各片延後的措辭建議與 P4 附記。

## 3. 業主裁決與待裁

- **已裁（2026-10-03「a」）**：見 §0。核可前不動正本。
- **業主裁決（2026-10-03）**：「核可」——核可大綱＋S1；執行模式沿用 ASK（每片回報）；S2、S3 開工前各自再送就緒審查。
- **業主裁決（2026-10-03，S1 停點）**：「a」——對選項「(a) 上限放寬到 1.6M，繼續 S2 和 S3（建議）」。⇒ **總上限 1.3M→1.6M**；S2、S3 開工前各自送就緒審查。
- **業主裁決（2026-10-03，S2 開工前）**：「可以放寬 但我要確保成果品質」——對「重估剩餘約 0.75M、總額約 1.6～1.65M，上限定 1.7M 不再放寬」的回覆。⇒ **總上限 1.6M→1.7M，此後不再放寬**（碰到即停在當片）；**品質閘門一律不為省成本刪減**（就緒審查、raw 機械取出與三方對帳、正對照、單元差集、`make audit`、fresh outcome verifier 全保留）；另依此裁決把 S3 抽驗改為**全數核可細目逐句核對**（核可 ≤14 條，取代固定種子抽 12 條）。
- **業主裁決（2026-10-03，S3 預跑發現新紅燈後）**：「a」——對選項「(a) 同意，在 S3 先修這條測試再寫入（建議）」。⇒ S3 範圍加入**只改測試**：`rag-orchestrator/tests/unit/agent/test_canon_assembler_req.py` 的 `_mark_reviewed_except`（skip_ids 若原本已審則拿掉其 reviewed 行）與 `test_prospect_outline_is_deterministic_and_registers_canon`（改取第一條 prospect 細目，不再要求原本未審）；⛔ 動產品程式。驗收：修前在預跑正本重現紅燈、修後預跑正本與現行正本皆綠、全套差集＝∅、outcome verifier 一併核此檔。commit 範圍加此一檔。
- **業主裁決（2026-10-03，停止後）**：「a」——對選項「(a) 補派驗證（建議）：這筆額外花費明確記帳，只驗最終狀態」。⇒ 超出上限 1.7M 另派一位 fresh verifier 驗停止後的最終狀態（HEAD `4f13a0b5`），不做其他事。

## 4. 停止條件（全片共用）

- 已審細目數任何時候下降 ⇒ 停。
- 正本只准在 S1 重生成（只動允許集合）與 S3 寫入（只加 reviewed 行）時變動。
- **總上限 1.3M；S1 commit 後累計 > 0.7M ⇒ 停下回報業主**；超過上限即停。（現行上限 1.7M，見 §3；不再放寬。）
- 一次只跑一個代理（本機 8GB）。
- 代理 brief 一律帶 HANDOFF §12-2 必禁清單。

## 5. 就緒審查紀錄

- **第 1 輪（fresh plan-verifier，大綱＋S1）＝REVISE**（2026-10-03）：P2×2——(1) executor brief 的 grep 驗收漏了 `drafts-{D,E,F,I}`、待裁路徑 `w1s1-921`、自檢「21 個」三個 9.21 值；(2) verifier brief 替換表第 5 項寫「待裁路徑不變」但底稿實為 `w1s1-921`，grep 也漏 `D＋E`、`drafts-E`、`9.20 S`、`13 條`，複核 brief 無替換與檢查規則。處置：兩項皆 **FIX**——executor brief 已預跑產生，替換表寫成 8 處逐項、殘留 8 字串 0 命中（附正對照實測值）、與底稿 `diff` 只差替換的 8 行；verifier brief 改正第 5 項、殘留檢查擴為 9 字串＋新值恰 1＋件數一致＋判準段逐字相同；複核 brief 納入同一替換表與檢查。送第 2 輪。
- **第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×1——工作清單的 doubt 理由與修正紀錄「依據」節沒寫來源與檢查；照 9.21 的產生器複製會讀到 9.20 舊 raw，`contract-upload-existing-vs-electronic` 與 `pricing-free-vs-experience-plan` 會拿到已修過的舊理由，S1 的現有檢查都攔不到。⇒ **第二次自動 REVISE，停止重送、逐條處置**：**FIX**——疑點來源限定兩份 9.21 重審 raw、工作清單與修正紀錄產生器已寫出並預跑、新增 `doubt_source_check.py`（逐字比對＋殘留字串，附正負對照），派工前必過。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **收尾審查（fresh plan-verifier）＝READY**（2026-10-03）⇒ 大綱＋S1 交業主核可（`next_gate: user_approval`）。S2、S3 開工前各自再送就緒審查。
- **S2 第 1 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主「a」與「可以放寬 但我要確保成果品質」（上限 1.7M）開跑。
- **S3 第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×2——(1) S3 commit 範圍漏了業主核可加入的測試檔，`git diff --cached` 範圍檢查必失敗，或漏 commit 使 HEAD 紅；(2) 執行步驟與全數核對未納入測試修正的 repo 端驗收（單跑、差集基準、outcome verifier 核此檔），測試被推翻無處置，且殘留「含抽驗」字樣。處置：兩項皆 **FIX**——commit 範圍加測試檔（恰 9 檔）；對 repo 執行加「測試檔單跑＋全套差集對 `red-baseline.txt`」；全數核對加測試檔 diff／範圍／負對照；新增測試被推翻的還原與停止；「含抽驗」改「全數核對」。送第 2 輪。
- **S3 第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×3（皆第 1 輪修正時引入）——(1) commit 範圍寫「恰 9 檔」含 A.md，但 A 架核可 0 條、A.md 不會有 diff，實際 8 檔；(2) git 前置與「產品程式 0 改動」未限路徑，工作樹另有其他工作線的未 commit 改動，必然誤判，且未寫明測試跑哪棵程式樹；(3) 測試被推翻的還原條件 `git diff --stat fd89adaa` 無路徑限定，永遠不會為空。⇒ **第二次自動 REVISE，停止重送、逐條處置**：三項皆 **FIX**——commit 範圍改 8 檔並註明 A.md 無 diff；所有 git 檢查加本片擁有路徑；其他工作線 29 路徑／41 檔建 sha256 指紋為既有基準、commit 前重比；寫明單元測試跑掛載的工作樹、與紅燈基準同一棵；還原條件加路徑並以 `cmp` 驗測試檔。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **S3 收尾審查（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主「安全組過」、測試修正「a」與上限 1.7M 開跑。

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

### S2（2026-10-03）

- 1 批 fresh verifier（S2B1，14 條）一次解析通過：**pass 13／doubt 1**。raw 由 `extract_verdict.py` 機械取出，存 `p922-s2/p922-s2-raw-S2B1.txt`。
- 審核單 `inputs/review-sheet-9.22-S2-ACDI-20261003.md`，表頭 commit `fd89adaa`，共 6 組，⚠️ 1 組（`A-account-profile` pass 2／doubt 1）。
  - `check` ⇒ `targets 14; judged 14; raw-parsed 14; sheet ids 14`、`mismatches: 0`。
  - 正對照（`jgb/A/account-change-password`）：審核單副本改 pass ⇒ 報 `sheet<->results` 不一致；raw 副本改 pass ⇒ 報 `raw<->results` 不一致。
  - 正本相對 `fd89adaa` 的 `git status` 與 `git diff --stat` 皆空。
- **D1 量測**：`d1_measure.py` ⇒ `denominator 6 (table 6, in targets 6, excluded [])`、`numerator 0`、**`ratio 0/6 = 0.0%`**；**9.21＋9.22 合併 3／52＝5.8%**（舊 D1 16～21%）。
- 唯一 doubt 是 S1 未修的 ⚠️ 組 pass：`account-change-password` 句 4「新密碼需同時包含英文與數字」——帳號資訊頁「儲存」未綁前端檢查結果、後端只驗 `min:6` 與確認一致，純數字密碼照樣存得進去；英數規則只是畫面提示（該句是 9.21 W1-S1 整條檢查依 `PasswordForm.vue` 補上，9.21 W1-S2 判 pass，本次被推翻）。
- pass 附建議 2 則（`team-public-page-recruitment` 招募頁另少「經理人」篩選、手機版社區區塊不看有無社區；`contract-upload-existing-vs-electronic` 「帳單設定」對部分特定合作團隊不成立），皆不構成反證，延後。
- 依「安全組過」：S3 可寫入 **11 條（pm +11、prospect +4）**；⚠️ 組 2 條 pass 也過則 13 條（pm +13、prospect +4）。
- **成本**：S2 約 0.39M（就緒審查 0.06M、S2B1 0.28M、主 session 約 0.05M）⇒ **9.22 累計約 1.24M**（上限 1.7M；S3 估 0.4M，含全數核對）。

### S3（2026-10-03）

- **業主裁決原文**（2026-10-03，對問題「S2 重新先審完成…終審要怎麼回？」的選擇）：「安全組過」——非 ⚠️ 5 組的 pass 標已審（rule＝safe）；⚠️ 組 `A-account-profile` 整組本批不審；1 條 doubt 本批不審；無點名、無照原樣過、無排除。驗收依 §3：outcome verifier 對核可細目**全數**逐句核對，任一推翻 ⇒ 以備份還原並停。
- **寫入前準備**：就緒審查 3 輪（REVISE×2 皆 FIX，收尾 READY，§5）。git 前置（限擁有路徑）：`git diff --stat fd89adaa -- rag-orchestrator/canon` 與 status 皆空、測試檔 ` M`；備份 `scratchpad/p922-s3-backup/`（21:22:14）`diff -r` 相同；其他工作線 29 路徑／41 檔指紋 `61712a4d4c4acce4` 已存。
- **寫入與驗證**：`write` ⇒ `added 11`；重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 525 -> current 536; added lines 11; approved 11`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；`git status` 只有 C／D／I `.md` 與 `jgb.json`，A.md 無 diff、CATALOG 不變；repo 與 scratch 預跑、scratch 重生成產出（保留 536／丟棄 0）皆 `diff -r` 相同。
- **終點指標 `已審細目 pm 530／533、prospect 120／120；頁面 pm 140／183、prospect 53／183`**（pm +11、prospect +4，與預期相同；C pm 78→81、D 99→104、I 45→48 全審；只剩 A 3 條未審）。
- **測試與 audit**：該測試檔對 repo 正本單跑 ⇒ `1 failed, 28 passed`，紅的只有基準內的 `test_prospect_view_fine_ids_match_id_map`；全套 `9 failed, 3931 passed, 3 skipped`，與基準差集＝∅；`make audit` OVERALL PASS；其他工作線 41 檔指紋重算與開工前相同。
- **fresh outcome verifier＝REFUTED**（檢查 1、2、3、5、6 過；4 全數核對 10／11 成立）：`jgb/D/contract-thinkcloud-signing-variants` 句 3「送去簽署時，如果客製化契約書的 PDF 底稿又解析不出來，也會跳出同樣的訊息，簽署不會開始。」——「跳出同樣的訊息」不成立：簽署由 `sign.blade.php` 的 `window.$('#signForm').submit()` 送出，`ContractController@sign` 以 redirect 導到 GET 路由 `contracts.thinkcloud`，`thinkcloud()` 的 `catch (DiyPdfUnparseableException $e)` 回傳陣列（`'success' => false, 'message' => …`），瀏覽器得到的是 JSON 頁面、沒有彈窗；「簽署不會開始」成立（P2）。主 session 對匯出確認該 catch 與路由屬實。該句是 9.21 W2-S1 整條檢查新增，W2-S1 核對、9.21 W2-S2 與本計畫 S2 先審皆判過，本次全數核對才抓出。
  - 測試檔核對過（只動兩處、守門 assert 保留、產品程式 0 改動、41 檔指紋相同、舊寫法在現行正本 0 條未審 prospect ⇒ `StopIteration`）。附記 P4×3（`add_attachment` 讀錯陣列層級致後端未擋 5 檔上限屬 jgb2 缺陷、`isset` 對空字串成立、「企業團隊」對應法人房東），延後。
- **依計畫還原**：正本由 `p922-s3-backup/` 還原；`git diff --stat fd89adaa -- rag-orchestrator/canon` 與 status 皆空、`diff -r` 相同、`load_canon_or_die` 通過；終點指標回到 `已審細目 pm 519／533、prospect 116／120；頁面 pm 133／183、prospect 52／183`。測試檔不在被推翻之列、保留（在 525 已審正本上該檔單跑亦只剩基準內 1 條紅）。
- **成本**：S3 約 0.56M（就緒審查 3 輪 0.17M、outcome verifier 0.27M、主 session 約 0.12M）⇒ **9.22 累計約 1.80M，超過上限 1.7M**（outcome verifier 派出時累計約 1.53M、未預留其 0.27M）。依 §3「此後不再放寬、碰到即停在當片」⇒ **S3 不寫入、9.22 停在此處**。

### 9.22 停止（2026-10-03）

- **終點指標**：`已審細目 pm 519／533、prospect 116／120`（本計畫 +0；S1 的 6 條修正保留在正本、未審）。
- **留給下一份計畫**：14 條仍未審。
  - `jgb/D/contract-thinkcloud-signing-variants` 句 3 須依 D1 修（刪「跳出同樣的訊息」或改寫為程式可證的畫面行為），修後該條須重新先審。
  - 其餘 10 條 S2 安全組 pass 已通過全數逐句核對（本次 outcome verifier 逐句成立），可直接作為下一份計畫終審的候選，但正本內容若有變動須重驗。
  - `A-account-profile` 組 3 條：`account-change-password` 句 4「需同時包含英文與數字」程式未強制（doubt），同組 2 條 pass。
- **D1 量測**：9.22 S2 抓回 0／6；9.21＋9.22 合併 3／52＝5.8%。另：全數核對抓到一條經三輪審查都判過的錯句 ⇒ 抽樣 12 條的驗收強度不足以保證每條成立。
- **停止後最終狀態驗證（fresh outcome verifier，業主「a」）＝CONFIRMED**（6 項全過）：(1) `rag-orchestrator/canon` 與 `fd89adaa`、備份 `p922-s3-backup/` 皆相同，reviewed 525，終點指標逐字相同（負對照：`7aac4142` 與 `fd89adaa` 的正本 diff 有差，證明檢查有效）；(2) 測試檔相對 `fd89adaa` 只有兩處改動、assert 全保留，在 525 已審正本上目標測試通過；(3) 全套 `9 failed, 3931 passed`，與基準雙向差集＝∅；(4) `4f13a0b5` 只含計畫、S2 審核單、HANDOFF、測試檔，其他工作線 41 檔指紋 `shasum -c` 全 OK；(5) HANDOFF 現況行、§12-1 列與本節數字與實況一致；(6) 推翻屬實（`#signForm` 原生 POST → redirect 到 GET `contracts.thinkcloud` → catch 回傳陣列，瀏覽器得 JSON、無彈窗）。
  - 代理自承違規：把單元輸出寫進 scratch 兩個新檔（只含 pytest 輸出），主 session 已刪除；repo 與既有證據未動。附記 P4×1（測試註解描述的是 prospect 全審情境，現行正本為 116／120，措辭問題），延後。
  - **成本**：此驗證約 0.15M（超出上限部分，業主核可）⇒ 9.22 合計約 1.95M。
