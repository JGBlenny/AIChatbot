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

- **分母**：`rag-orchestrator/canon/jgb/A.md`／`B.md`／`C.md`（S3 完成後的 commit，以下記作 `<S3>`）中無 `- reviewed:` 行的細目，預期 223 條（A 63、B 79、C 81）；清單存 `scratchpad/p917-s1-targets.json`，數目≠223 即停。
- **做法**（沿用 9.16 S3，工具參數化為架 A／B／C）：依粗目分 8 批（A 2、B 3、C 3，每批 ≤35，粗目不拆），**派工前**存 id→批次對照 `scratchpad/p917-s1-batches.json`（聯集＝targets、不交）。每批一位 fresh verifier、序列、一次一位；brief＝9.16 S3 版（明列本批 id＋預期條數；逐句對源⛔抽樣；可答性；本線錯誤型態；**畫面標籤以現行畫面為準、⛔ 設定檔／程式註解標籤**；**現行 vs 舊路徑**），另加一條：**同組細目之間不得互相矛盾**（9.16 抽驗教訓）。每批最終訊息以 `p916_s3_extract.py` 從代理紀錄檔機械取出逐字存 `scratchpad/p917-s1-raw-<批>.txt`；results 只由腳本 `parse` 產生；缺 id／多 id／格式錯／doubt 缺證據 ⇒ 視同交不出件（同一代理重貼一次，再失敗即停）。
- **審核單**：`inputs/review-sheet-9.17-S1-ABC-<日期>.md`，腳本從 results＋正本標題產生（⛔ 手抄），表頭記 commit；依粗目分組；doubt 比例以該組 targets 為分母，>30% 標 ⚠️；⛔ 題目原文。
- **驗收**：
  - 已判 id 集合＝targets（223，每條恰一個判定）
  - 三段對帳 `check` 不符數＝0；正對照兩個（raw 副本 doubt→pass、審核單副本 doubt→pass）各報出該 id；輸出記入 §6
  - `git diff --stat <S3> -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 為空；終點指標不變
- **擁有**：審核單、本計畫 §6；scratchpad 的 targets／batches／raw／results／腳本。⛔ 改正本、drafts、帳本。
- **回滾**：只新增審核單，刪除即可。
- **預算**：8 批 × 約 0.27M ≈ 2.2M。
- **停止**：累計達停點（§3 D3）即停，未審批次在審核單列「未先審」、該組不可整組回過。

### S2 — 業主終審＋寫入已審（**預期終點 pm 最多 +223、prospect 最多 +53**）

- 業主依審核單逐組回「過」；doubt 只能「本批不審」或「照原樣過」。核可清單由腳本從審核單＋results 各算一次、兩者相同才寫（同 9.16 S4）。
- 寫入：A.md／B.md／C.md 核可細目 `- sources:` 之後加 `- reviewed: {by: owner, at: <日期>}`；`export_json`／`export_catalog` 重匯出；⛔ 重跑生成器；改前備份。
- **驗收**：新增行數＝核可數、刪除 0；已審 id 集合＝既有 136 ∪ 核可（逐 id）；doubt／未核可細目 0 條被標；D E F G H I 與 CATALOG 位元組不變；`load_canon_or_die` 通過；終點指標 pm／prospect 增量＝核可中對應 target_user 條數；單元紅燈＝既有 9 條；`make audit` PASS；重生成保留檢查（scratch）；fresh outcome verifier。
- **擁有**：`rag-orchestrator/canon/jgb/A.md`、`B.md`、`C.md`、`jgb.json`、`CATALOG.md`；HANDOFF 終點行。
- **回滾**：以備份還原（已審數下降 ⇒ 須業主明示）。
- **預算**：outcome verifier 約 0.15M。

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
- 大綱＋S3 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 交業主核可（`next_gate: user_approval`）。S1、S2 開工前各自再過就緒審查。
