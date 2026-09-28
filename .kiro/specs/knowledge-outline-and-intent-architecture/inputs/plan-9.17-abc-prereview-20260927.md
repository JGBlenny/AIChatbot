# Plan 9.17：A／B／C 三架先審＋業主終審，並收 9.16 兩件遺留

> 狀態：**業主 2026-09-27 核可**（先做 S3；D1～D4 全照建議）。ASK 模式。
> **終點指標（起點，`endpoint_progress.py` 2026-09-27，commit `5d188b37`）**：`已審細目 pm 136／535、prospect 17／121；頁面 pm 48／183、prospect 13／183`（A pm 0／63、prospect 0／18；B pm 0／79、prospect 0／19；C pm 0／81、prospect 0／16）。
> **本計畫預期**：S2 完成時 **pm 最多 +223、prospect 最多 +53**（＝A B C 全部；依 9.15／9.16 先審通過率約六到七成、安全組規則，實際預期約 pm +130～150）；S3a 預期 pm +1、prospect +1（`payment-gateway-fees` 重審通過時，無已審下降）；S3b 為 +0（只做證據表，業主同意見 D4）；S1 為 +0，是 S2 的前置。
> 上游：Plan 9.16 §6（S3 先審流程、收案抽驗）；記憶 `feedback_endpoint_metric_first`、`project_ledger_p914_scope_errors`。

## 0. 為什麼有這份

- 已審只在 D／E（pm 136）；A B C 三架 223 條 pm 細目全部未審，是終點指標最大的缺口。
- 9.16 已把「代理先審 → 腳本產審核單 → 三段對帳 → 業主終審 → 只加 reviewed 行 → 重生成可保留」整條跑通並驗證；本計畫沿用，不改機制。
- 9.16 收案抽驗留下兩件：`jgb/E/payment-gateway-fees`（標題寫中信／藍新免費無據，已撤回已審）要修正重審；`jgb/E/bill-power-reading-draft-defaults` 與已審的 `jgb/E/bill-scheduled-send-rule` 對「排定發送時空白度數」說法看似矛盾，要對碼交業主裁。

## 1. 切片

### S1 — A／B／C 代理先審（預期終點 +0；是 S2〔pm 最多 +223〕的前置）

- **分母**：`rag-orchestrator/canon/jgb/A.md`／`B.md`／`C.md`（S3 完成後的 commit `f03be3b0`（`41bb46f7` 之後只補文件、正本同））中無 `- reviewed:` 行的細目，預期 223 條（A 63、B 79、C 81）；清單存 `scratchpad/p917-s1-targets.json`，數目≠223 即停。
- **工具（p917 副本，⛔ 改 9.16 原檔，保留其可重跑）**：`scratchpad/p917_s1_sheet.py`（由 `p916_s3_sheet.py` 複製），變更值：架 `SHELVES="ABC"`、`CANON_COMMIT="f03be3b0"`、檔名前綴 `p917-s1-*`（targets／batches／raw／results）、審核單標題「Plan 9.17 S1 A／B／C」與回覆說明「S2」；另加兩道覆蓋守門：`group_view` 找不到任何 target 即大聲失敗（列出缺的 id）；`check` 比對審核單 id 集合＝targets（223、各一次），不符即計入 mismatches。`p916_s3_extract.py` 通用、沿用。**已預跑**（2026-09-27）：targets 223（A 63／B 79／C 81）、批次對照 8 批（34／29／25／22／32／28／31／22，聯集＝targets、不交）；空結果審核單 `check` ⇒ `targets 223; … sheet ids 223`、`mismatches: 0`；負對照 `P917_SHELVES=AB` ⇒ `❌ 81 targets not found…`；刪掉一組的審核單副本 ⇒ `sheet coverage: sheet ids 218 vs targets 223` 與組缺失。
- **做法**（沿用 9.16 S3）：依粗目分 8 批（A 2、B 3、C 3，每批 ≤35，粗目不拆），**派工前**存 id→批次對照 `scratchpad/p917-s1-batches.json`（聯集＝targets、不交）。每批一位 fresh verifier、序列、一次一位；brief＝9.16 S3 版，正本與 evidence 路徑改指**本批所屬架**的 `canon/jgb/<X>.md` 與 `runs/outline-20260920/drafts-<X>.json`（明列本批 id＋預期條數；逐句對源⛔抽樣；可答性；本線錯誤型態；**畫面標籤以現行畫面為準、⛔ 設定檔／程式註解標籤**；**現行 vs 舊路徑**），另加一條：**同組細目之間不得互相矛盾**（9.16 抽驗教訓）。每批最終訊息以 `p916_s3_extract.py` 從代理紀錄檔機械取出逐字存 `scratchpad/p917-s1-raw-<批>.txt`；results 只由腳本 `parse` 產生；缺 id／多 id／格式錯／doubt 缺證據 ⇒ 視同交不出件（同一代理重貼一次，再失敗即停）。
- **審核單**：`inputs/review-sheet-9.17-S1-ABC-<日期>.md`，腳本從 results＋正本標題產生（⛔ 手抄），表頭記 commit；依粗目分組；doubt 比例以該組 targets 為分母，>30% 標 ⚠️；⛔ 題目原文。
- **驗收**：
  - 已判 id 集合＝targets（223，每條恰一個判定）；`check` 輸出須含 `targets 223; judged 223; raw-parsed 223; sheet ids 223`（部分完成時 judged＜223、其餘在「未先審」）；審核單表頭 commit＝`f03be3b0`
  - 三段對帳 `check` 不符數＝0；正對照兩個（raw 副本 doubt→pass、審核單副本 doubt→pass）各報出該 id；輸出記入 §6
  - `git diff --stat <S3> -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 為空；終點指標不變
- **擁有**：審核單、本計畫 §6；scratchpad 的 targets／batches／raw／results／腳本。⛔ 改正本、drafts、帳本。
- **回滾**：只新增審核單，刪除即可。
- **預算**：8 批 × 約 0.27M ≈ 2.2M；9.17 已用約 0.35M ⇒ 預估約 2.55M，**最後一批可能碰到 2.6M 停點**——屆時照停止條件停、未審批次標「未先審」、該組不可整組回過，交業主決定是否追加。
- **停止**：累計達停點（§3 D3）即停，未審批次在審核單列「未先審」、該組不可整組回過。

### S2 — 業主終審＋寫入已審（**預期終點 pm 最多 +223、prospect 最多 +53**）

- 業主依審核單 `inputs/review-sheet-9.17-S1-ABC-20260928.md` 回覆。可回的形式：
  - 規則：「安全組過」＝非 ⚠️ 組的 pass；或「全部 pass 過」。
  - 點名 ⚠️ 組「過」：只收該組的 pass。
  - 逐條點名 doubt「照原樣過」。
  - 逐條點名 pass「不要」（排除）。

  其餘 doubt 一律本批不審。**回覆無法完整寫成 rule／warn_groups／doubt_as_is／exclude 四欄（附條件、語意不明、點到不存在的組或 id）⇒ 不做 derive，回問業主。**
- **S1 後實算上限**（見 §6 S1）：
  - 安全組過 ⇒ pm +113、prospect +19；
  - 全部 pass 過 ⇒ pm +155、prospect +32；
  - ⚠️ 組 pass 共 42 條。
- **步驟**（工具 `scratchpad/p917_s2_approved.py`，子命令 derive／write／verify；⛔ 手選 id、⛔ 手改正本）：
  1. **記錄裁決**：業主回覆原文先逐字記入 §6「### S2」，再照原文寫 `scratchpad/p917-s2-decision.json`，內容為 `{"reply": 原文, "rule": "safe"|"all"|"none", "warn_groups": [點名過的 ⚠️ 組], "doubt_as_is": [點名照原樣過的 doubt id], "exclude": [點名不要的 pass id]}`。
  2. **推導核可清單**：`derive p917-s2-decision.json --out p917-s2-approved.json`。它由兩個獨立來源各算一次：
     - 來源 A＝審核單的 `[pass]`／`[doubt]` 列與 ⚠️ 標記；
     - 來源 B＝`p917-s1-results.json`＋targets＋正本分組，⚠️ 以 doubt／targets >30% 重算。

     推導規則：核可＝（依規則選中的組 ∪ 點名的 ⚠️ 組）的 pass id，減去 exclude，再加上點名的 doubt id。兩來源相同才寫檔，並印出核可條數、各架條數、預期 pm／prospect 增量。下列任一情形都大聲失敗、不寫檔：
     - `reply` 沒有逐字出現在計畫 §6「### S2」段內，或 §6 還沒有 S2 段；
     - 決定檔有未知欄位；
     - 點名的組不是 ⚠️；
     - 點名的 doubt id 其實是 pass；
     - exclude 的 id 不是選中組的 pass；
     - 決定檔沒有原文；
     - 審核單有「未先審」；
     - 核可 id 已經有 reviewed 行。
  3. **備份**：`rag-orchestrator/canon/` 整個目錄複製到 `scratchpad/p917-s2-backup/`，並以 `diff -r` 確認和工作樹逐位元組相同。
  4. **寫入**：`write p917-s2-approved.json --date <日期>`。只在 A.md／B.md／C.md 的核可細目 `- sources:` 行之後加一行 `- reviewed: {by: owner, at: <日期>}`。既有 reviewed 行、或同一細目有兩行 sources ⇒ 失敗；寫入條數≠核可條數 ⇒ 失敗。
  5. **重匯出**：在容器內 `parse_canon_dir('/app/canon/jgb')` → `export_json`／`export_catalog`，接著 `load_canon_or_die('/app/canon')`。⛔ 重跑生成器改正本。
  6. **驗證**：`verify p917-s2-approved.json --backup scratchpad/p917-s2-backup`，再跑以下「驗收」各項。
- **已預跑**（2026-09-28，scratch 正本副本與 scratch 計畫副本〔含 §6 S2 測試原文〕，repo 正本未動）：
  - derive 四種回覆各得唯一集合，兩來源相同：
    - 「安全組過」⇒ 113（A 26／B 46／C 41；pm +113、prospect +19）；
    - 「全部 pass 過」⇒ 155（pm +155、prospect +32）；
    - 「安全組過，A-registration 也過，team-public-page-share 照原樣過」⇒ 121（pm +121、prospect +24）；
    - 「安全組過，但 login-methods 不要」⇒ 112（pm +112、prospect +18）。
  - 負對照皆失敗：
    - 點名非 ⚠️ 組 `A-login`；
    - 把 pass id 當 doubt 照原樣過；
    - exclude 一個不在選中組的 pass；
    - 決定檔無原文；原文不在 §6 S2；真計畫尚無 §6 S2；
    - 未知欄位 `except`；
    - 審核單副本拿掉 `A-registration` 的 ⚠️ ⇒ `sheet-derived 120 != results-derived 113`。
  - 寫入＋容器重匯出＋`load_canon_or_die` 通過：
    - verify ⇒ `reviewed backup 137 -> current 250; added lines 113`、`jgb.json reviewed fines 250; fines changed beyond reviewed_*: 0`、`mismatches: 0`，已審 pm 250／prospect 37。
    - 同一 write 重跑 ⇒ 拒絕（已有 reviewed 行）。
  - verify 正對照：
    - 在 ⚠️ 組 pass `jgb/A/register-email-steps` 多加 reviewed 行 ⇒ `reviewed set: extra [...]`；
    - D.md 加一個換行 ⇒ `D.md differs from backup`；
    - README 加一字元＋jgb/ 多一個檔 ⇒ `README.md differs`、`canon file set differs`；
    - `jgb.json` 改粗目標題 ⇒ `coarse-level fields changed`；
    - 未重匯出 ⇒ 113 條 `missing reviewed_* after write`。
- **驗收**：
  - **決定檔忠於原文**：`decision.json.reply` 與 §6 S2 原文逐字相同（derive 已檢）；rule／warn_groups／doubt_as_is／exclude 每個值都能在原文找到對應字句，原文每一句核可或排除都有對應欄位（雙向）。由 fresh outcome verifier 逐條勾選。
  - verify `mismatches: 0`。其中包含：
    - 已審 id 集合＝備份 137 ∪ 核可（逐 id）；
    - A／B／C 相對備份只多 `- sources:` 後的 reviewed 行、只在核可 id、行數＝核可數、刪除 0；
    - D E F G H I `.md`、`jgb/CATALOG.md`、`README.md` 與備份逐位元組相同，檔案集合相同；
    - `jgb.json` 只在核可細目多 `reviewed_*`，另外頂層 `canon_sha256` 變動；粗目層欄位與其他細目欄位 0 變動。
  - **未經業主核可的細目 0 條被標**（未點名的 doubt、未核可的 ⚠️ 組 pass、被排除的 pass）：由已審 id 集合＝137 ∪ 核可、加上決定檔忠於原文推得。
  - `load_canon_or_die` 通過。
  - 終點指標 `endpoint_progress.py`：pm＝137＋derive 印出的 pm 增量、prospect＝18＋derive 印出的 prospect 增量。
  - 重生成保留檢查：生成器在 scratch 以 `--expect-reviewed-kept <137＋核可數>` 試跑並通過，⛔ 對 repo 跑。
  - 全套單元紅燈＝既有 9 條；`make audit` PASS。
  - fresh outcome verifier（在 S2 commit 前，對上述逐條）。
- **停止**（分兩種）：
  - **寫入前（步驟 1～3）的失敗**：回覆不符四欄形式、derive 失敗、備份 `diff -r` 不同 ⇒ **不還原**，直接停下交業主；以 `git diff --stat f03be3b0 -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆為空，確認正本未動。
  - **寫入後（步驟 4 起）的失敗**：write 失敗、重匯出或 `load_canon_or_die` 失敗、verify 任一不符、終點指標≠預期、重生成保留數≠137＋核可數、單元紅燈≠既有 9 條、`make audit` 非 PASS、outcome verifier 非 CONFIRMED ⇒ 以步驟 3 **已通過 `diff -r` 的** `scratchpad/p917-s2-backup/` 整個還原 `rag-orchestrator/canon/`，再以 `diff -r` 確認與備份相同、`git diff --stat f03be3b0 -- rag-orchestrator/canon` 為空，停下交業主。

  這種「驗收失敗還原回 137」屬本片預先授權的還原，不算 §4 的已審下降。但只要已審數低於 137，仍須業主明示。
- **擁有**：`rag-orchestrator/canon/jgb/A.md`、`B.md`、`C.md`、`jgb.json`、`jgb/CATALOG.md`；本計畫 §6；HANDOFF 終點行；scratchpad 的 decision／approved／backup。⛔ drafts、D～I、其他工作線檔。
- **回滾**（已完成、已 commit 後）：以 `scratchpad/p917-s2-backup/` 還原或 revert 該 commit。已審數會下降，須業主明示。
- **預算**：寫入由主 session 做；outcome verifier 約 0.15M。

### S3 — 收 9.16 兩件遺留（S3a 預期 pm +1、prospect +1；S3b +0，需業主同意，見 §3 D4）

**S3a `payment-gateway-fees` 修正＋重審**（該條目前未審 ⇒ 重生成不會丟任何已審）
- **允許集合**：`scratchpad/p917-s3-allowed.json`＝`["jgb/E/payment-gateway-fees"]`，改動前寫好；⛔ 改其他任何細目（含已審的 `payment-gateway-options`，一致性只用「句子內容對齊它」達成，不改它）。
- **做法**：改前備份 `drafts-E.json`、`rag-orchestrator/canon/`、`runs/outline-20260920/` 既有 `*-20260927*` 產出到 `scratchpad/p917-s3-backup/`。主 session 依來源（`help:paymentapply_zh-Hant.html`；程式以釘住匯出 `scratchpad/jgb2-b2ee2ac/` 為準）用 `p916_edit.py`（允許集合換成本檔）改寫該條標題與句子：申請費 vs 交易費率分開寫、藍新提款前 5 次免費後每次 10 元、個人房東限制與 `payment-gateway-options` 內容一致。每一處改動記入修正紀錄 `inputs/fix-log-9.17-S3-<日期>.md`（格式同 9.16：一列一項、依據、verifier 判定、刪除節）。fresh verifier 逐項核（D1：修一次仍不過即整句刪）。
- **重生成**：S1 生成器、容器、`--date 20260927-s3`（不與 9.16 的 20260927 產出撞名）、`--expect-reviewed-kept 136`、`--expect-open-questions <實算>`；先 scratchpad 試跑，全部 `--expect-*` 通過才對 repo 跑。
- **重審寫入**：業主對修正後的該條回「過」後，照 9.16 S4 方式只在該條 `- sources:` 後加 `- reviewed:` 行＋`export_json`／`export_catalog` 重匯出（改前再備份一次）；業主未過 ⇒ 不寫、該條維持未審。
- **驗收**：
  - 差異比對（`p916_s2_drafts_diff.py`，`--doubt p917-s3-allowed.json`、`--fix-log` 本片修正紀錄、基準＝`p917-s3-backup` 的 drafts-E）(a)～(f) 全 PASS；正對照：scratch 副本改 `payment-gateway-options` 一句 ⇒ (b)(c) 報出。輸出記入修正紀錄
  - 重生成：`已審保留：136 條／丟棄：0 條`；A B C D F G H I `.md` 與備份逐位元組相同（`cmp`）；E.md 區塊差異只在允許集合內；`jgb.json`／`CATALOG.md` 差異只在該 id 與 sha
  - 重審寫入（若業主過）：E.md 只新增 1 行、刪除 0；已審 id 集合＝既有 136 ∪ {該條}（逐 id）；`load_canon_or_die` 通過
  - 終點指標 `endpoint_progress.py`＝pm 136＋（過則 1）、prospect 17＋（過則 1，該條 target_user 含 prospect）
  - 全套單元紅燈＝既有 9 條；`make audit` PASS；fresh outcome verifier（在 S3 commit 前，對上述逐條）
- **擁有**：`drafts-E.json`（僅允許集合）、`rag-orchestrator/canon/`（重生成＋該條 reviewed 行）、`runs/outline-20260920/` 下 `*-20260927-s3*` 新產出、`inputs/fix-log-9.17-S3-<日期>.md`、本計畫 §6、HANDOFF 終點行。
- **回滾**：以 `p917-s3-backup/` 還原 drafts-E、正本與 20260927 產出，刪除 `*-20260927-s3*` 新檔。

**S3b 排定發送空白度數：只做證據表＋業主裁決，本計畫 ⛔ 改任何細目**
- 兩條相關細目 `jgb/E/bill-power-reading-draft-defaults` 與 `jgb/E/bill-scheduled-send-rule` **都已審**，任何內容改動都會讓已審下降 ⇒ 本計畫不改。
- 主 session 以釘住匯出對碼（排定發送的前置檢查、`prepareIotMeterForSend` 等）與帳本 `#p914-power-reading-draft`，先確認兩條現行正本句子是否真的矛盾（9.16 抽驗描述的前提要重驗），寫成證據表 `inputs/evidence-9.17-S3b-scheduled-send-meter-<日期>.md`，給業主四個選項：A 條錯／B 條錯／兩條都對（範圍不同）／無法判斷。
- 業主裁決原文記入證據表與 §6；依裁決的修正（含帳本是否更正）列入下一個計畫，⛔ 在本計畫動手。
- **驗收**：證據表每個命題附釘住匯出的檔案＋可 grep 符號；正本、drafts、帳本本片 0 變動。
- **預算**：S3a＋S3b 約 0.35M。
- **順序**：S3 在 S1 之前做完並 commit；S1 的正本基準改為 **S3 的 commit**。

## 2. 不做（另案）

- D／E 其餘 62 條未審（9.16 未審 63 條扣掉本計畫 S3a 的 `payment-gateway-fees`；含 40 doubt 與 ⚠️ 組 23 條 pass）的修正與重審；S3b 裁決後的修正。
- F G H I 四架。
- jgb2 缺陷與文件不一致交產品（9.15 G1 清單＋9.16 §6 三處）。

## 3. ⏳ 待業主裁

- **D1**：沿用 9.16 裁決——修一次仍不過就整句刪；內容一改就重審。（建議：沿用）
- **D2**：S2 終審標準沿用「安全組過、⚠️組不審」？（建議：沿用，看審核單後再定）
- **D3**：預算上限 3M（S3 0.35＋S1 2.2＋S2 0.15＋預留 0.3）；累計達 2.6M 先停交業主看剩餘量。（建議：可以）
- **D4**：S3b 只做證據表、終點 +0（不改已審細目，避免已審下降）——同意嗎？（建議：同意）

## 4. 停止條件（全片共用）

- 已審細目數（M1）任何時候下降 ⇒ 停下交業主（本計畫沒有預期的下降）。
- 正本只准在 S3a（重生成＋該條 reviewed 行）與 S2（只加 reviewed）變動。
- 累計達停點先停交業主；超過上限即停。
- 一次只跑一個代理（本機 8GB）。

## 5. 就緒審查紀錄

- 大綱＋S3 第 1 輪＝REVISE P2×5（S3 差異比對缺允許集合與修正紀錄；reviewed 寫回路徑與 §4 衝突、S3 預期未量；未驗非目標架位元組不變；生成器產出檔與 9.16 同日撞名、擁有／回滾不全；S3b 由主 session 二選一、未記業主裁決）。**處置：縮小＋FIX**——S3b 改為只做證據表＋業主裁決、本計畫不改（兩條相關細目都已審）；S3a 補允許集合、修正紀錄、差異比對＋正對照、重生成用新日期、八架 `cmp`、reviewed 寫回照 9.16 S4、終點指標實算、outcome verifier；§4 同步。P3：S1 基準改為 S3 commit、§2 條數改 62、D 編號統一、證據用釘住匯出路徑。
- S1 第 1 輪＝REVISE P2×1：工具由 D／E 改 A／B／C 的變更值未列、`check` 只比審核單對自己的分組而非對 targets ⇒ 架設錯時整架會無聲掉出審核單。FIX：p917 副本工具、列出全部變更值、加兩道覆蓋守門並預跑正負對照；P3 採納：brief 路徑改本批架、部分完成的預期寫明、工具不改 9.16 原檔。
- S1 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 交業主核可開跑。
- 大綱＋S3 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 交業主核可（`next_gate: user_approval`）。S1、S2 開工前各自再過就緒審查。
- S2 第 1 輪＝REVISE，P2×2：
  1. 核可清單沒綁住業主實際回覆（沒有原文紀錄、推導規則、清單檔、工具），而且「doubt 照原樣過」和驗收「doubt 0 條被標」互相矛盾；
  2. 沒有自己的停止項，備份路徑也沒寫，驗收失敗後的還原和 §4「下降即停」衝突。

  **FIX**：
  - 新工具 `p917_s2_approved.py`（derive／write／verify），附裁決紀錄、推導規則、兩來源推導、清單檔路徑；
  - 驗收改為「未經業主核可 0 條被標」；
  - 加備份路徑與停止項，寫明驗收失敗還原屬預先授權；
  - 三種回覆與正負對照都已預跑（見 S2「已預跑」）。
- S2 第 2 輪＝REVISE，P2×2。這是第二次自動 REVISE ⇒ 停止重送，逐條處置後只開一次收尾審查：
  1. 決定檔由原文手寫、工具不比原文、沒有「排除」形式 ⇒ **FIX**：derive 檢查 `reply` 逐字在 §6 S2；加 `exclude` 欄位與未知欄位檢查；回覆不符四欄形式即停、回問；outcome verifier 雙向勾選決定檔對原文。
  2. 還原規則涵蓋「尚未備份／備份壞」⇒ **FIX**：停止分寫入前（不還原、以 git diff 確認）與寫入後（以已驗證的備份還原）。

  P3 三項一併 FIX：verify 加 README 與檔案集合比對、`jgb.json` 粗目層欄位比對；停止清單加單元紅燈／audit／outcome verifier。
- S2 收尾審查（fresh plan-verifier）＝**READY** ⇒ 交業主終審（`next_gate: user_approval`）。

## 6. 執行紀錄

### S3（2026-09-27）

- **S3a**：允許集合 `scratchpad/p917-s3-allowed.json`；備份 `scratchpad/p917-s3-backup/`（drafts-D／E、canon、9.16 的 20260927 產出）。親修 `payment-gateway-fees`（標題「費率」→「申請費用」、「免費」→「不收申請費」；補藍新提款費與交易手續費條款原文），修正紀錄 `inputs/fix-log-9.17-S3-20260927.md`（4 列全過；新句 [3] 首核不過〔流程註記、洽客服無據〕依 D1 修一次後過）。差異比對 (a)～(f) PASS，正對照（改 `payment-gateway-options`）⇒ (b)(c) 報出。試跑＋repo 重生成（`--date 20260927-s3`）：`已審保留：136 條／丟棄：0 條`；A B C D F G H I 與備份相同；E.md／CATALOG／jgb.json 差異只在該條（＋sha）；9.16 產出未被覆寫。業主重審「過」⇒ 只加 1 行 reviewed、重匯出；已審 id＝136 ∪ {該條}；`load_canon_or_die` 通過；**終點指標 `已審細目 pm 137／535、prospect 18／121`（pm +1、prospect +1）**；單元紅燈＝既有 9 條；`make audit` PASS。fresh outcome verifier＝**CONFIRMED**（六項全過；附記 P4：drafts evidence 欄未補新句、釘住匯出無 .git 無法自證 sha）。
- **S3b**：證據表 `inputs/evidence-9.17-S3b-scheduled-send-meter-20260927.md`——A 現行內容已不談排定發送、兩條無直接矛盾；B 句 2 漏「唯一缺的是 IoT 綁定物件電費度數時仍可排入、排入與發送時自動補」例外（`checkIotBill`、`prepareIotMeterForSend`）。**業主裁決「B 不完整，下個計畫補例外」**；本計畫未改任何細目。
- commit `41bb46f7`（S3 本體；因更新腳本編碼錯誤，裁決原文／§6／HANDOFF 行以後續 commit 補上）。
- 成本：plan-verifier ×2 約 0.11M、S3a verifier 約 0.08M、outcome verifier 約 0.1M ⇒ 9.17 累計約 0.3M。

### S1（2026-09-27～28）

- 8 批 fresh verifier 序列跑完（一次一位），結果 A／B／C 合計 **pass 155／doubt 68**：

  | 批 | 架 | 條數 | pass／doubt |
  |---|---|---|---|
  | S1B1 | A | 34 | 23／11 |
  | S1B2 | A | 29 | 16／13 |
  | S1B3 | B | 25 | 20／5 |
  | S1B4 | B | 22 | 18／4 |
  | S1B5 | B | 32 | 20／12 |
  | S1B6 | C | 28 | 19／9 |
  | S1B7 | C | 31 | 23／8 |
  | S1B8 | C | 22 | 16／6 |

  各批原始回覆以 `p916_s3_extract.py` 機械取出、存成 `scratchpad/p917-s1-raw-S1B*.txt`；results 由 `p917_s1_sheet.py parse` 產生。
- **交件失敗一次**：S1B1 的最終訊息含一行非細目的夾註，並且先後貼了兩份結論（先寫一份、再「更正」重貼）。`parse` 以重複 id 大聲失敗。依規則請同一代理重貼一次，重貼後 34 條解析通過。第 2 批起 brief 加一條「最後一則只能放一份結論、⛔ 夾補充行」，之後 7 批一次解析通過。
- 審核單 `inputs/review-sheet-9.17-S1-ABC-20260928.md`（腳本產生，表頭 commit `f03be3b0`）：
  - 26 組，其中 ⚠️ 11 組、安全組 15 組。
  - `check` ⇒ `targets 223; judged 223; raw-parsed 223; sheet ids 223`、`mismatches: 0`。
  - 正對照（`jgb/C/team-public-page-share`）：
    - 審核單副本 doubt→pass ⇒ 報出 `sheet<->results C-team-storefront [pass]/[doubt]`；
    - raw 副本 doubt→pass ⇒ 報出 `raw<->results …: raw=pass results=doubt`。
- `git diff --stat f03be3b0 -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 為空。正對照：同指令對 `5d188b37` ⇒ `3 files changed`。正本未動，終點指標維持 pm 137／prospect 18。
- **S2 選項的上限**（腳本依審核單＋drafts `target_user` 計算）：
  - 安全組過、⚠️組不審 ⇒ pm +113、prospect +19；
  - 全部 pass 過 ⇒ pm +155、prospect +32；
  - ⚠️組裡被擋下的 pass 共 42 條。
- **值得業主知道的疑點型態**：
  - B 架有 5 條正本寫出客戶名「統上」「新北住都」：`advance-discount-items`、`advance-late-fee`、`advance-payment-cycle-discount`、`advance-short-lease-approval`、`lessee-bulk-notify`。這些已在 repo 內，不是本片新增。
  - 其餘疑點大宗是「絕對句漏了社宅／特定合作團隊／大房東例外」與「引號標籤非現行介面字樣」（例：「合約中」vs 現行「租約中」、「同上」vs「同戶籍地址」、「其他」vs「更多」）。
- 成本：8 批 verifier 約 1.51M（含 S1B1 重貼）、S1 就緒審查 ×2 約 0.08M ⇒ **9.17 累計約 1.89M**（停點 2.6M）。

### S2（2026-09-28）

- **業主裁決原文**（AskUserQuestion「9.17 S2 終審：A／B／C 審核單要怎麼過？」之回覆）：「安全組過 (Recommended)」——＝非 ⚠️ 15 組的 pass 標已審；⚠️ 11 組全組本批不審；68 條 doubt 全數本批不審；無點名 ⚠️ 組、無照原樣過、無排除。
- 決定檔 `scratchpad/p917-s2-decision.json`＝`{"reply":"安全組過 (Recommended)","rule":"safe","warn_groups":[],"doubt_as_is":[],"exclude":[]}`。`derive` ⇒ `approved 113 (both sources equal) by shelf {'A': 26, 'B': 46, 'C': 41}; expected endpoint increment pm +113, prospect +19`。
- 備份 `scratchpad/p917-s2-backup/`：`diff -r` 相同（寫入前 `git diff --stat f03be3b0 -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆空）。
- `write --date 2026-09-28` ⇒ `added 113 reviewed lines`。容器重匯出 `canon_sha256` `59ff90ec…`（與 scratch 預跑相同），`load_canon_or_die` 通過。
- `verify` ⇒ `reviewed backup 137 -> current 250; added lines 113`、`jgb.json reviewed fines 250; fines changed beyond reviewed_*: 0`、`mismatches: 0`。
- **終點指標 `已審細目 pm 250／535、prospect 37／121；頁面 pm 70／183、prospect 18／183`**（pm +113、prospect +19，＝預期）。
- 重生成保留檢查（scratch `p917-s2-regen-canon`，`--expect-reviewed-kept 250 --expect-open-questions 54`）⇒ `已審保留：250 條／丟棄：0 條`；A～I、CATALOG、jgb.json 與 repo 正本逐位元組相同。
- 單元紅燈＝既有 9 條（pii_scan[runs] 只含既有 `line_id` 命中）；`make audit` ⇒ `OVERALL: PASS（2026-09-28）`。
- fresh outcome verifier＝**CONFIRMED**（7 項全過）。附記 P4：
  - 重生成 stdout 未存 log，改以 cmp＋`reviewed-dropped` 為 `[]` 間接證明；
  - unit 檔中一條紅燈的 FAILED 摘要印兩行，去重後仍是 9 條；
  - 舊的 `gs_before_s2.txt` 不是本片快照。

  三項皆不影響結論，不處理。
- 成本：S2 就緒審查 3 輪約 0.16M、outcome verifier 約 0.1M ⇒ **9.17 累計約 2.15M**（停點 2.6M、上限 3M）。

### 9.17 收案

- 終點指標由 pm 136／prospect 17（9.16 抽驗撤回後）升到 **pm 250／prospect 37**：S3a +1／+1，S2 +113／+19。
- 留給下個計畫：
  - `bill-scheduled-send-rule` 補 IoT 電費例外（S3b 業主裁決）；
  - D／E 未審 **63** 條（正本實數：D 53、E 10。§2 寫的 62 是算錯：9.16 S4 後未審 63 條，本來就不含 `payment-gateway-fees`；它被撤回後又在 S3a 重審，一撤一審抵銷，所以仍是 63）；
  - A／B／C 未審 110 條：68 條 doubt，以及 ⚠️ 11 組內 42 條 pass。其中 B 架 5 條寫出客戶名「統上」「新北住都」，需改寫為「特定合作團隊」；
  - F G H I 四架；
  - jgb2／文件不一致清單。

