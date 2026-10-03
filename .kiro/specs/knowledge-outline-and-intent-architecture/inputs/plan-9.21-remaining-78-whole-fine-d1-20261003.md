# Plan 9.21：剩餘 78 條未審細目推進（兩波），D1 改「修整條」

> **現況**（`endpoint_progress.py`，2026-10-03，HEAD `ee35c1ea`）：`已審細目 pm 457／533、prospect 105／120；頁面 pm 119／183、prospect 48／183`（A 52／62、B 70／78、C 56／81、D 84／104、E 90／96、F 31／33、G 26／26、H 5／5、I 43／48）。
>
> **本計畫預期**：
> - 第一波（A／B／C，W1-S1～S3）：pm +20～28、prospect +2～4。
> - 第二波（D／E／F／I，W2-S1～S3）：pm +18～25、prospect +3～6。
> - 合計 pm +38～53（9.20 實際核可率：第一波 51／60＝85%、第二波 37／63＝59%；本批多為第二、三輪難件，取下緣）。修正片與重審片都是 +0，為終審片的前置。
> - 頁面量尺上限（現有細目全審）pm 136、prospect 51 ⇒ 本計畫頁面最多 pm +17、prospect +3（`endpoint_progress.py --ignore-review` 正對照：`頁面 不分身分 136／183；pm 136、prospect 51`）。

## 0. 為什麼有這份

- 業主 2026-10-03「D1 改整條、9.21 照建議」，建議內容：
  - **D1 改「修整條」**：修 doubt 時同步檢查同一條細目的標題、所有句子與講法；⛔ 不准改別條細目；超出 doubt 所指的改動一律逐列進修正紀錄、交核對代理判。
  - **D1 改法的驗收**：9.21 重審後被抓回的比例（修過的細目在重新先審被判 doubt 的比例）**< 10%**；未達則下一份計畫改回原 D1。
  - **範圍與分波**：剩下未審全做，依架分兩波——A／B／C 一波、D／E／F／I 一波。
  - **預算**：上限 4.0M；第一波結束（約 2.0M）停下回報。
  - 終審沿用「安全組過」。
- 為什麼改 D1：9.20 修過的細目重審被抓回 16～21%（第一波 6／38、第二波 8／38），多數是只修 doubt 所指的那句、同條其他句子或講法另有問題（講法答不到 3 條）。每被抓回一次就重付一輪「修正→核對→先審」（9.20 平均每條已審約 0.055M）。
- 未審細目 78 條（pm 76），以各自最近一次先審結論分組（審核單 9.19 S2、9.20 S2、9.20 S5）：

  | 組 | doubt | ⚠️ 組 pass | 先審出處 |
  |---|---|---|---|
  | A／B／C | 25（A 8、B 5、C 12） | 18（A 2、B 3、C 13） | 9.19 S2 |
  | D／E | 13（D 10、E 3） | 13（D 10、E 3） | 9.20 S5 |
  | F／I | 8（F 2、I 6） | 1（I） | 9.20 S2 |

  - A／B／C 25 條 doubt 中有 11 條是 9.19 修過後仍被判 doubt 的第三輪件。
  - 54 則待裁（`runs/outline-20260920/open-questions-20261003-s4-920.md`）未裁；doubt 若需要替待裁選邊才能修，記入修正紀錄「停下交業主」節，⛔ 不選邊。

## 1. 切片（順序：W1-S1 → commit → W1-S2 → W1-S3 → commit → ⏸ 第一波停點 → W2-S1 → commit → W2-S2 → W2-S3 → commit）

（各片步驟、驗收、停止、擁有與 9.20 對應片相同；以下只寫差異。工具沿用 9.20 重建版：`scratchpad/p920-w2/`（edit_fine、drafts_diff、canon_check、name_scan、customer-terms、coverage_check）、`scratchpad/p920-w5/`（review_sheet、approve_write、extract_verdict、S2 brief 原文）、`scratchpad/jgb2-b2ee2ac/`；開工前確認仍在，不在就依 HANDOFF §12-3 從 transcript 重建。）

### 新 D1（本計畫起適用）

- doubt 所指的句子照舊修；**同時**逐句檢查同條細目的標題、其餘句子與講法，凡與釘住匯出不符、講法答不到、或與同粗目細目矛盾者一併修。
- ⛔ 只限同一條細目；⛔ 不改其他細目（含同粗目）；同粗目其他細目若有問題，記入修正紀錄「另見」節，留下一份計畫。
- 其餘沿用：修一次仍不過就整句刪；需要整條刪的、或 **doubt 本身**的修正需要替待裁（54 則）選邊的，整條記入「停下交業主」節、本片不改（修正表 0 列）。
- **整條檢查發現、但修它需要替待裁選邊的項目**（doubt 以外的句子、標題或講法）：doubt 照修；該項記入新節「## 整條待裁」（每條 `- \`<細目 id>\`：<哪一項>：<涉及哪則待裁>`），本片不改、⛔ 不選邊。`coverage_check` 不計此節（同一 id 可同時在修正表與整條待裁）；⛔ 同一 id 不得同時在修正表與停下交業主。
  - 已預跑（合成）：一條細目有 `依據 #n` 修正列＋整條待裁一項 ⇒ `coverage_check` PASS、`scope_check` PASS；負對照：同一 id 又記入停下交業主 ⇒ `in both table and stopped`、FAIL。
- **範圍標記（機器可讀）**：不加欄（`drafts_diff._ROW` 固定 6 欄）；範圍寫在修正表「依據」欄，三種固定格式擇一：`依據 #n`（doubt 所指）／`整條 #m`（同條檢查新增）／`依據 #n＋整條 #m`（同一改動項同時因 doubt 與整條檢查而改：**只寫一列**，兩個依據並列）。
  - `依據 #n` 列在「## 依據」節（原 doubt 理由，同 9.20）；`整條 #m` 列在新節「## 整條依據」，每條 `m. \`<細目 id>\`：<問題>：<釘住匯出路徑 code:／help:／docs:> \`<可 grep 字串>\``，由主 session 對匯出 grep 命中後才寫。
  - 機械檢查 `p921-w1/scope_check.py <修正紀錄>`：依據欄格式、`#n`／`#m` 存在、`整條 #m` 的細目 id 與該列一致、每條整條依據附路徑＋grep 字串；印出 doubt／整條／兩者 列數與觸及整條列的 verifier 判定分布；違反即 exit 1。
  - 已預跑（2026-10-03，合成修正紀錄）：正對照（doubt 1 列、整條 1 列、兩者 1 列）⇒ PASS；負對照三條皆 FAIL／exit 1：整條編號不存在、整條依據缺證據、依據欄格式錯（`依據 1`）。

### W1-S1 — A／B／C 25 條 doubt 依新 D1 修正（+0）

- **底片＝9.20 S4**（含已由前案處理、`coverage_check`、修正核對→D1 修一次→複核）；以下常數全部改寫，⛔ 不沿用 9.20 的值：
  - scratch 目錄 `p921-w1/`；修正紀錄 `inputs/fix-log-9.21-W1-S1-ABC-<日期>.md`；ops 存 `p921-w1/ops.json`。
  - 允許集合 `p921-w1/allowed.json` 25 條＝A／B／C 未審且 9.19 S2 判 doubt 者。兩來源：repo 審核單 `review-sheet-9.19-S2-ABCI-20260929.md`，以及以 `extract_verdict.py` 從 9.19 S2 先審代理 transcript 重取的 raw；不等或條數≠25 ⇒ 停。
    - 已查（2026-10-03）：transcript 在 `~/.claude/projects/<專案>/b25be7ef…/subagents/`（S2B1 兩份 `agent-a21416978ec9459e2`／`agent-ac6754e5974d55854`，S2B2 `agent-aa8fc94066faf51ca`、S2B3 `agent-a1e53ca01dcc8bade`、S2B4 `agent-a13617ccf24f7f90c`）。S2B1 兩份須對照 9.19 §6 S2 紀錄判定被採用的交件，⛔ 不得兩份合併。
  - **不變位元組**：drafts-D～I 與 `canon/jgb/D.md`～`I.md` 與備份 `cmp` 相同；CATALOG 只允許允許集合內細目的行變動（`canon_check`）。
  - **終點指標（+0，W1-S3 的前置）**：開工前與完成後都須為 `已審細目 pm 457／533、prospect 105／120`；已審集合維持 **461** 條。
  - 重生成 `--expect-reviewed-kept 461 --expect-open-questions 54`（`--runs-out` 寫 scratch 再複製回 repo，日期標 `<日期>-w1s1-921`）。
  - **修正核對 verifier 分包**：A、B 合一包，C 一包（粗目不拆）；brief 由 `templates/brief-fix-verify.txt` 衍生，**改三處**：
    1. 判準第 5 條「只修 doubt 所指的地方；如果看到超出 doubt 範圍的改動，請指出」**刪除**，改為「改動只限同一條細目（任何欄位）；改到別條細目即判不過」。
    2. 新增：`整條 #m` 列的依據是「## 整條依據」該條（主 session 對釘住匯出的證據），判準＝「改後成立、依據成立、未引入新錯誤」；⛔ 不以「超出 doubt 範圍」判不過。
    3. 新增：範圍標錯也要報（例：標 `依據 #n` 但改動與該 doubt 理由無關、或該標 `整條` 卻標 doubt）。
    - 驗收：brief 全文 grep「只修 doubt 所指」0 命中（正對照：模板原文命中 1）。
  - **整條列的逐列核對（機械）**：`scope_check` PASS；`整條`＋`兩者` 列數＝修正紀錄中觸及整條的列數，且每列都有 fresh verifier 判定（過／不過，⛔ 空白）。§6 記整條列數與過／不過分布。
  - commit 範圍：drafts-A／B／C、`canon/jgb/A.md`～`C.md`、CATALOG、`jgb.json`、runs `*-<日期>-w1s1-921*` 三檔、修正紀錄、本計畫；`git diff --cached --name-only` 範圍外 0。
- 驗收另加：`coverage_check` 25 條全數有去處（修正表＋已由前案處理＋停下交業主）。
- 預算約 0.7M。

### W1-S2 — A／B／C 43 條重新先審（+0）
- 分母＝25 條允許集合＋18 條 ⚠️ 組 pass（以現行正本 A／B／C 未審細目機械推出，條數≠43 ⇒ 停）；brief 用 9.20 S2 原文（`p920-w5/s2-brief-recovered.txt`），機械替換批次、架、id 清單與待裁路徑；工具、批次格式同 9.20 S5（含非空合成預跑＋負對照）。
- **D1 改法量測（業主的成效判準）**：
  - 分母＝W1-S1 修正表中出現、且在 W1-S2 重審 targets 內的細目（排除「已由前案處理」「停下交業主」的 id；**有「整條待裁」項的細目仍計入分母**——它有修正、也會重審，重審若因那一項判 doubt 照計，並在 §6 另列件數）；分子＝其中在 W1-S2 raw（`extract_verdict.py` 取出）判 doubt 者；比例＝分子／分母。§6 記分子、分母、被排除的 id 與理由；可由 `p921-s2-results.json` 與 `p921-w1/allowed.json`、修正紀錄機械重算。
  - **怎麼用**：W1 值在 ⏸ 第一波停點回報；**W1 ≥ 10% ⇒ 由業主在停點決定 W2 用新 D1 或改回舊 D1**；「下一份計畫是否改回舊 D1」以 W1＋W2 合併值判（合併分母＝兩波分母相加）。
- 預算約 0.6M。
- **終點指標（+0，W1-S3 的前置）**：開工前與完成後都須為 `已審細目 pm 457／533、prospect 105／120`（已審 461）；正本相對 W1-S1 commit `ca8b3a08` 不得變動。
- **已預跑**（2026-10-03，`ca8b3a08` 後；repo 未動）：
  - 工作區 `scratchpad/p921-s2/`：`review_sheet.py`、`extract_verdict.py` 由 9.20 S5 版（`p920-w5/`）複製，變更值 `CANON_COMMIT="ca8b3a08"`、`SHELVES` 預設 `ABC`、`PREFIX="p921-s2"`、標題「Plan 9.21 W1-S2 A／B／C 修正後重新先審」。
  - `p921-s2-targets.json`：現行正本 A／B／C 未審 **43** 條（＝W1-S1 允許集合 25＋⚠️ 組 pass 18）。
  - `p921-s2-batches.json`（S2 格式 `{批次: [{coarse, ids}]}`）：正本順序、粗目不拆、每批 ≤35：W1S2B1 33 條（A 5 組＋B 4 組＋C 2 組）、W1S2B2 10 條（C 3 組）；聯集＝targets、重複 0。hold＝`[]`。
  - brief `brief-prereview-W1S2B{1,2}.txt`：由 9.20 S2 原文（`s2-brief-recovered.txt`）機械替換批次、條數、架、id 清單、待裁路徑（`open-questions-20261003-w1s1-921.md`）與匯出路徑；判準段逐字沿用。W1-S1 的修正紀錄與核對建議⛔ 不給先審代理（保持獨立）。
  - 非空合成預跑（`scratchpad/p921-s2-pc/` 副本，43 條中 1 條 doubt）：`parse` ⇒ `parsed 43 ids: pass 42 / doubt 1`；`sheet` ⇒ `groups 14 … pending 0`；`check` ⇒ `targets 43; judged 43; raw-parsed 43; sheet ids 43`、`mismatches: 0`；負對照刪 1 行 ⇒ `❌ W1S2B2: missing ids […]`、exit 1。實際工作區無合成 raw。
  - **D1 量測工具** `p921-s2/d1_measure.py <修正紀錄> <targets> <results>`：分母／分子依本節定義機械計算、印比例與被排除 id；空分母或缺判定 ⇒ exit 2。預跑：合成 results ⇒ `denominator 25 … ratio 1/25 = 4.0%`；真 results 尚空 ⇒ `fines without a re-review verdict`、exit 2。
- **驗收**：兩批一次一位代理、raw 機械取出；`check` ⇒ `targets 43; judged 43; raw-parsed 43; sheet ids 43`、`mismatches: 0`；審核單 `inputs/review-sheet-9.21-W1-S2-ABC-<日期>.md`；正對照（審核單副本／raw 副本各改一條 doubt 為 pass ⇒ 兩者都報不一致）；`d1_measure` 結果記入 §6；正本 `git status` 為空。
- **停止與回滾**：交件失敗同一代理重貼一次，仍失敗即停；回滾只刪審核單與 `p921-s2` 檔。

### W1-S3 — 業主終審＋寫入（pm 最多 +43）
- 同 9.20 S3／S6；outcome verifier 沿用固定種子抽驗（核可數 ≥ 12 時抽 12 條，否則全抽）。
- 預算約 0.35M。
- **已預跑**（2026-10-03，業主終審回覆後；repo 正本未動）：
  - 工具 `p921-s2/approve_write.py`：由 9.20 S6 版複製，results／targets／hold 改讀 `p921-s2-*`、PLAN 改指本計畫、段落 `### W1-S3`。業主原文已逐字記入 §6「### W1-S3」；決定檔 `p921-s2/p921-s3-decision.json`（rule＝safe）。
  - derive（`P918_WRITE_SHELVES=ABC`、`P918_SHEET=<W1-S2 審核單絕對路徑>`）⇒ `approved 37 (both sources equal) by shelf {'A': 7, 'B': 8, 'C': 22}; expected endpoint increment pm +37, prospect +5`。對照：reply 改成不在 §6 的字串 ⇒ `❌ decision reply is not verbatim…`；rule 改 all ⇒ 40。
  - scratch 正本 `p921-s3-pc/`：write ⇒ `added 37`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 461 -> current 498; added lines 37; approved 37`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；D～I、CATALOG 與備份 `cmp` 相同。
  - scratch 重生成保留檢查（`--expect-reviewed-kept 498 --expect-open-questions 54`）⇒ `已審保留：498 條／丟棄：0 條`，與 scratch 正本 `diff -r` 相同。
  - scratch 終點指標 `已審細目 pm 494／533、prospect 110／120；頁面 pm 125／183、prospect 50／183`。
  - 紅燈基準沿用 `p920-w2/red-baseline.txt`（9 條；W1-S1 commit 後同一工作樹已驗 9 failed 同名）；預測新紅燈：scratch 正本掛到容器 `/app/canon`（正對照：容器內 C.md `reviewed` 78、repo 56）跑全套 ⇒ `9 failed, 3931 passed`，差集＝∅。
- **對 repo 執行的步驟**：備份 `rag-orchestrator/canon/` 至 `scratchpad/p921-s3-backup/` 並 `diff -r`；`git diff --stat ca8b3a08 -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆須為空 ⇒ write ⇒ 容器重匯出 ⇒ verify `--backup p921-s3-backup` ⇒ repo 與 scratch 預跑 `diff -r` ⇒ 終點指標、全套單元差集、`make audit` ⇒ fresh outcome verifier（含抽驗）⇒ commit。
  - **抽驗（沿用 9.20 S6）**：派工前固定 `random.Random(20261003).sample(sorted(p921-s3-approved.json), 12)`，存 `p921-s2/p921-s3-sample.json`，12 個 id 記入 §6；verifier 逐條列標題與每句成立／不成立並附匯出證據；**推翻**＝抽樣細目的標題或任一句在釘住匯出（及細目所列來源）找不到支持或有反證（P3／P4 措辭建議不算）；任一推翻 ⇒ 用 `p921-s3-backup/` 還原、`git diff --stat ca8b3a08 -- rag-orchestrator/canon` 為空後停下交業主；§6 記 12 個 id 與逐條結果。
  - commit 範圍：A／B／C `.md`、`jgb.json`、W1-S2 審核單、本計畫、HANDOFF（終點行與現況）；`git diff --cached --name-only` 範圍外 0。
- **終點指標**：寫入後須為 `已審細目 pm 494／533、prospect 110／120`（pm +37、prospect +5）。

#### ⏸ 第一波停點
W1-S3 commit 後停下，回報終點指標、累計成本、D1 量測結果。第二波在業主明示後才開始。

### W2-S1 — D／E／F／I 21 條 doubt 依新 D1 修正（+0）

- **底片＝W1-S1**（同步驟、同新 D1、同 executor 起草→主 session 審閱與機械驗證→套用→核對→D1 修一次→複核→重生成→outcome verifier）；以下常數全部改寫，⛔ 不沿用 W1-S1 的值：
  - scratch 目錄 `p921-w2/`；修正紀錄 `inputs/fix-log-9.21-W2-S1-DEFI-<日期>.md`；ops 存 `p921-w2/ops.json`；工具自 `p921-w1/` 複製（edit_fine、drafts_diff、canon_check、name_scan、customer-terms、coverage_check、scope_check、apply_ops、templates），值不改。
  - **允許集合** `p921-w2/allowed.json` **21 條（D 10／E 3／F 2／I 6）**＝D／E／F／I 未審且最近一次先審判 doubt 者。兩來源：
    - D／E：repo 審核單 `review-sheet-9.20-S5-DE-20261003.md`（正本 `589e0a14`）＋ `scratchpad/p920-w5/p920-s5-raw-*`；
    - F／I：`review-sheet-9.20-S2-FGHI-20261001.md`（正本 `46234eb0`）＋ `scratchpad/p920-w1/p920-s2-raw-*`。
    - 已查（2026-10-03，`d7c805d9`）：審核單與 raw 逐 id 判定相同（S5 63／63、S2 60／60）；D～I 未審 35＝doubt 21＋pass 14（全為 ⚠️ 組 pass）；不等或條數≠21 ⇒ 停。
    - 判定後內容未變：`git diff --stat <該正本> -- drafts-D／E（589e0a14）、drafts-F／I（46234eb0）` 皆空；`.md` 自該正本起只新增 `- reviewed:` 行（非 reviewed 新增行 0；正對照：reviewed 行有命中）。
  - **備份** `p921-w2/backup/`（drafts、runs 整個目錄、canon；13:16:02，與 repo `diff -r` 相同）；九架 roundtrip 全 True；客戶名掃描 `fines scanned: 539`、hits 0、「系統上」6。
  - **不變位元組**：drafts-A／B／C／G／H 與 `canon/jgb/A.md`～`C.md`、`G.md`、`H.md` 與備份 `cmp` 相同；CATALOG 只允許允許集合內細目的行變動（`canon_check`）。
  - **終點指標（+0，W2-S3 的前置）**：開工前（已量）與完成後都須為 `已審細目 pm 494／533、prospect 110／120`；已審集合維持 **498** 條。
  - 重生成 `--expect-reviewed-kept 498 --expect-open-questions 54`（`--runs-out` 寫 scratch 再複製回 repo，日期標 `<日期>-w2s1-921`）。
  - **起草**：executor，brief `p921-w2/brief-executor-fix.md`＝W1 版（`p921-w1/brief-executor-fix.md`）機械替換：目錄 `p921-w2`、條數 21、`drafts-{D,E,F,I}.json`、工作清單 `p921-w2/worklist.txt`（已產生，21 條，含 doubt 理由、現行內容、同粗目標題）、待裁路徑 `open-questions-20261003-w1s1-921.md`（54 則）；新 D1 與 Hard rules 段逐字沿用。套到 scratch 副本、`drafts_diff --list` 產出改動項後，同一 executor 續做 `scope-map.json`（每項 doubt／whole／both）與 `whole-basis.md`（同 W1-S1）；主 session 對匯出逐字 grep 後才寫入修正紀錄。
  - **修正核對 verifier 分包**：D＋E 一包（13 條）、F＋I 一包（8 條）；brief 由 W1-S1 已改版 `p921-w1/brief-fix-AB.txt` 機械替換，**替換表（逐項）**：
    1. 首行片名與包名「Plan 9.21 W1-S1」「A＋B 架」⇒「Plan 9.21 W2-S1」「D＋E 架」／「F＋I 架」；改動項數、細目數（首行與末行 `總 N`）⇒ 該包 `drafts_diff --list` 實數；
    2. 「## 改動項」清單 ⇒ 該包的改動項（`drafts_diff --list` 機械篩架）；
    3. 修正紀錄路徑 ⇒ `inputs/fix-log-9.21-W2-S1-DEFI-<日期>.md`；依據來源「9.19 S2 先審的 doubt 理由」⇒「D／E＝9.20 S5 先審、F／I＝9.20 S2 先審的 doubt 理由」；
    4. 改後檔名 `drafts-A.json、drafts-B.json` ⇒ 該包兩架；改前備份 `p921-w1/backup/drafts/` ⇒ `p921-w2/backup/drafts/`；
    5. 待裁路徑 `open-questions-20261003-s4-920.md` ⇒ `open-questions-20261003-w1s1-921.md`。
    - 判準段（含 W1-S1 已改的三處）逐字沿用。
    - **驗收（機械 grep，兩份 W2 brief 各自）**：`W1-S1`、`9.19`、`ABC`、`A＋B`、`s4-920`、`p921-w1`、`drafts-A`、`drafts-B`、「只修 doubt 所指」皆 0 命中；`fix-log-9.21-W2-S1-DEFI-` 恰 1 命中；末行 `總 N` 與「## 改動項」行數相等。正對照：`p921-w1/brief-fix-AB.txt` 對前 8 個字串各至少命中 1、`templates/brief-fix-verify.txt` 對「只修 doubt 所指」命中 1。任一不符 ⇒ 不派工、修 brief。
  - `drafts_diff` 以 `P919_DIFF_SHELVES=ABCDEFGHI` 執行（(a)～(g) PASS，A／B／C／G／H 無改動項）；`scope_check` PASS；`coverage_check` 21 條全數有去處；整條列逐列有 fresh verifier 判定，§6 記整條列數與過／不過分布。
  - commit 範圍：drafts-D／E／F／I、`canon/jgb/D.md`～`F.md`、`I.md`、CATALOG、`jgb.json`、runs `*-<日期>-w2s1-921*` 三檔、修正紀錄、本計畫；`git diff --cached --name-only` 範圍外 0。
- **預算約 1.3M**（W1-S1 實績 1.6M／25 條按 21 條折算）。9.21 累計估 2.55＋1.3≈3.85M；**W2-S1 commit 後累計 > 3.9M ⇒ 停下回報業主**（上限 4.8M；W2-S2 估 0.6M、W2-S3 估 0.35M）。

### W2-S2 — D／E／F／I 35 條重新先審（+0）
- **底片＝W1-S2**（同步驟、同 brief 判準、同驗收與停止回滾）；以下常數全部改寫：
  - 工作區 `scratchpad/p921-w2s2/`：`review_sheet.py`、`extract_verdict.py`、`d1_measure.py` 由 `p921-s2/` 複製，變更值 `CANON_COMMIT="59a43bce"`、`SHELVES` 預設 `DEFI`、`PREFIX="p921-w2s2"`、標題「Plan 9.21 W2-S2 D／E／F／I 修正後重新先審」。
  - `p921-w2s2-targets.json`：現行正本 D／E／F／I 未審 **35** 條（＝W2-S1 允許集合 21＋⚠️ 組 pass 14；條數≠35 ⇒ 停）。
  - `p921-w2s2-batches.json`（S2 格式）：正本順序、粗目不拆、**按架分兩批**（減輕單一代理負載）：W2S2B1 20 條（D 6 組）、W2S2B2 15 條（E 3 組＋F 2 組＋I 3 組）；聯集＝targets、重複 0。hold＝`[]`。
  - brief `brief-prereview-W2S2B{1,2}.txt`：由 9.20 S2 原文機械替換批次、條數、架、id 清單、待裁路徑（`open-questions-20261003-w2s1-921.md`）與匯出路徑；判準段逐字沿用；grep `W1-S2`／`W1S2`／`s4-920`／`w1s1-921`／`p921-s2/`／`fix-log` 皆 0 命中。W2-S1 修正紀錄與核對建議⛔ 不給先審代理。
- **已預跑**（2026-10-03，`59a43bce` 後；repo 未動）：非空合成預跑（`scratchpad/p921-w2s2-pc/` 副本，35 條中 1 條 doubt）：`parse` ⇒ `parsed 35 ids: pass 34 / doubt 1`；`sheet` ⇒ `groups 14 … pending 0`；`check` ⇒ `targets 35; judged 35; raw-parsed 35; sheet ids 35`、`mismatches: 0`；負對照刪 1 行 ⇒ `❌ W2S2B2: missing ids […]`、exit 1。實際工作區無合成 raw（`parse` ⇒ 0）。
- **D1 量測**：`d1_measure.py <W2-S1 修正紀錄> <targets> <results>`；預跑：合成 doubt 落在允許集合內 1 條 ⇒ `denominator 21 … ratio 1/21 = 4.8%`；真 results 尚空 ⇒ `fines without a re-review verdict`、exit 2。§6 記 W2 值與 **W1＋W2 合併值**（分子相加／分母 25＋21＝46），合併值供「下一份計畫是否改回舊 D1」判斷（§1 W1-S2 定義）。
- **驗收**：兩批一次一位代理、raw 機械取出；`check` ⇒ `targets 35; judged 35; raw-parsed 35; sheet ids 35`、`mismatches: 0`；審核單 `inputs/review-sheet-9.21-W2-S2-DEFI-<日期>.md`；正對照（審核單副本／raw 副本各改一條 doubt 為 pass ⇒ 兩者都報不一致；若全 pass 則改一條 pass 為 doubt）；`d1_measure` 結果記入 §6；正本相對 `59a43bce` 的 `git status`／`git diff --stat` 為空。
- **終點指標（+0，W2-S3 的前置）**：開工前與完成後都須為 `已審細目 pm 494／533、prospect 110／120`（已審 498）。
- **停止與回滾**：交件失敗同一代理重貼一次，仍失敗即停；回滾只刪審核單與 `p921-w2s2` 檔。
- **預算約 0.5M**；9.21 累計估 4.1＋0.5≈4.6M（上限 5.1M；W2-S3 估 0.35M）。

### W2-S3 — 業主終審＋寫入（pm 最多 +32）
- **底片＝W1-S3**（安全組規則、寫入→容器重匯出→verify、固定種子抽驗 12 條、任一推翻以備份還原並停）；以下常數全部改寫：
  - 工具 `p921-w2s2/approve_write.py`：由 `p921-s2/` 版複製，results／targets／hold 改讀 `p921-w2s2-*`、段落 `### W2-S3`；PLAN 同本計畫。業主原文已逐字記入 §6「### W2-S3」；決定檔 `p921-w2s2/p921-w2s3-decision.json`（rule＝safe）。
  - 寫入架 `P918_WRITE_SHELVES=DEFI`；審核單 `P918_SHEET=<inputs/review-sheet-9.21-W2-S2-DEFI-20261003.md 絕對路徑>`。
- **已預跑**（2026-10-03，業主終審回覆後；repo 正本未動）：
  - derive ⇒ `approved 27 (both sources equal) by shelf {'D': 15, 'E': 6, 'F': 2, 'I': 4}; expected endpoint increment pm +25, prospect +6`。對照：reply 改成不在 §6 的字串 ⇒ `❌ decision reply is not verbatim inside plan §6 ### W2-S3 record`；rule 改 all ⇒ 32（pm +30、prospect +7）。
  - scratch 正本 `p921-w2s3-pc/`：write ⇒ `added 27`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 498 -> current 525; added lines 27; approved 27`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；A／B／C／G／H、CATALOG 與備份 `cmp` 相同。
  - scratch 重生成保留檢查（`--expect-reviewed-kept 525 --expect-open-questions 54`）⇒ `已審保留：525 條／丟棄：0 條`，與 scratch 正本 `diff -r` 相同。
  - scratch 終點指標 `已審細目 pm 519／533、prospect 116／120；頁面 pm 133／183、prospect 52／183`。
  - 紅燈基準沿用 `p920-w2/red-baseline.txt`（9 條）；scratch 正本掛到容器 `/app/canon` 跑全套（正對照：容器內 D.md `reviewed` 99、repo 84）⇒ `9 failed, 3931 passed`，差集＝∅。
- **對 repo 執行的步驟**：備份 `rag-orchestrator/canon/` 至 `scratchpad/p921-w2s3-backup/` 並 `diff -r`；`git diff --stat 59a43bce -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆須為空 ⇒ write ⇒ 容器重匯出 ⇒ verify `--backup p921-w2s3-backup` ⇒ repo 與 scratch 預跑 `diff -r` ⇒ 終點指標、全套單元差集、`make audit` ⇒ fresh outcome verifier（含抽驗）⇒ commit。
  - **抽驗**：派工前固定 `random.Random(20261003).sample(sorted(p921-w2s3-approved.json), 12)`，存 `p921-w2s2/p921-w2s3-sample.json`，12 個 id 記入 §6；推翻定義與處置同 W1-S3（還原用 `p921-w2s3-backup/`、基準 `59a43bce`）。
  - commit 範圍：D／E／F／I `.md`、`jgb.json`、W2-S2 審核單、本計畫、HANDOFF（終點行與現況）；`git diff --cached --name-only` 範圍外 0。
- **終點指標**：寫入後須為 `已審細目 pm 519／533、prospect 116／120`（pm +25、prospect +6）。
- **預算約 0.35M**；9.21 累計估 4.83＋0.35≈5.18M（上限 5.3M）。

## 2. 不做（另案）
- 新起草細目（頁面真缺口約 11～12 頁）、頁面量尺改造、prospect 可見頁範圍定義——皆待業主裁（HANDOFF §12-4）。
- 54 則待裁、jgb2 缺陷清單、6 條 `sources` 必填紅燈。
- 講法核可（`approved`）與回答品質量測。

## 3. 業主裁決與待裁
- **已裁（2026-10-03「D1 改整條、9.21 照建議」）**：見 §0。
- **業主裁決（2026-10-03）**：「核可」——核可大綱＋W1-S1；執行模式沿用 ASK（每片回報）。W1-S2 起各片開工前各自再送就緒審查。
- **業主裁決（2026-10-03，W1-S1 後成本回報）**：「a」——對選項「(a) 繼續 W1-S2 和 W1-S3，第一波停點放寬到 2.6M（建議）；W1-S2 開工前照例先送就緒審查」。⇒ **第一波停點 2.0M→2.6M**；總上限 4.0M 不變，第二波範圍與 D1 於第一波停點依 D1 量測結果再裁。
- **業主裁決（2026-10-03，第一波停點）**：「a」——對選項「(a) 第二波繼續用新 D1，上限放寬到 4.8M（建議）」。⇒ 第二波 D／E／F／I 35 條沿用新 D1；**總上限 4.0M→4.8M**。
- **業主裁決（2026-10-03，W2-S1 後成本停點）**：「a」——對選項「(a) 上限放寬到約 5.1M，跑 W2-S2 和 W2-S3（建議）」。⇒ **總上限 4.8M→5.1M**；W2-S2、W2-S3 開工前各自送就緒審查。
- **業主裁決（2026-10-03，W2-S2 後成本回報）**：「a」——對選項「(a) 放寬到約 5.3M，跑 W2-S3 寫入（建議）」。⇒ **總上限 5.1M→5.3M**；終審回覆另計（見 §6 W2-S3）。

## 4. 停止條件（全片共用）
- 已審細目數任何時候下降 ⇒ 停。
- 正本只准在修正片的重生成（只動允許集合）與終審片的寫入（只加 reviewed 行）時變動。
- 累計達停點先停；超過上限即停。
- 一次只跑一個代理（本機 8GB）。
- 代理 brief 一律帶 HANDOFF §12-2 必禁清單。

## 5. 就緒審查紀錄

- **第 1 輪（fresh plan-verifier，大綱＋W1-S1）＝REVISE**（2026-10-03）：P2×4——(1) 新增「範圍」欄會讓 `drafts_diff._ROW`（固定 6 欄）解析失敗；(2) 沿用的核對 brief 第 5 條「只修 doubt 所指」與新 D1 矛盾，整條列沒有依據也沒有判準；(3) D1 成效判準的分母、用哪一波、停點時怎麼用都沒定義；(4) W1-S1 沿用 9.20 的常數（不變位元組、已審 373、分包 F＋H／G＋I）不適用。處置：四項皆 **FIX**——範圍改寫在依據欄固定格式＋新 `scope_check.py`（已預跑正負對照）；brief 改三處並以 grep 驗收；量測分母／分子／用法寫死；W1-S1 改以 9.20 S4 為底片並逐項寫出常數。送第 2 輪。
- **第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×1——新 D1 下，一條細目可能 doubt 已修、但整條檢查發現另一項須替待裁選邊；計畫沒說它歸哪節，若同時記修正表與停下交業主，`coverage_check` 必然失敗，量測分母也不明。⇒ **第二次自動 REVISE，停止重送、逐條處置**：**FIX**（選 (a)：doubt 照修，該項記入新節「整條待裁」、不計入 coverage、細目仍計入量測分母；合成預跑正負對照）。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **收尾審查（fresh plan-verifier）＝READY**（2026-10-03）⇒ 大綱＋W1-S1 交業主核可（`next_gate: user_approval`）。W1-S2、W1-S3、W2 各片開工前各自再送就緒審查。
- **W1-S2 第 1 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主核可開跑。
- **W1-S3 第 1 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主核可開跑。
- **W2-S1 第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×1——verifier brief 由 W1 版衍生，替換清單漏了修正紀錄路徑（仍指 W1-S1 A／B／C）與依據來源（9.19 S2），而 grep 驗收只查「只修 doubt 所指」與 `p921-w1`，攔不到。處置：**FIX**——改為逐項替換表（片名／包名／件數、改動項、修正紀錄與依據來源、改後與改前路徑、待裁路徑），grep 驗收擴為 9 個殘留字串 0 命中＋W2 修正紀錄恰 1 命中＋件數一致，附正對照（實測 W1 brief 含首行、末行、修正紀錄、改後、改前、待裁 6 處 W1 常數）。送第 2 輪。
- **W2-S1 第 2 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主「a」（第二波新 D1、上限 4.8M）開跑。
- **W2-S2 第 1 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主「a」（上限 5.1M）開跑。
- **W2-S3 第 1 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主「安全組過」與「a」（上限 5.3M）開跑。

## 6. 執行紀錄

### 立案前盤查（2026-10-03）

- `/canon-audit outline-drafting` 應讀 10 份：9 份文件由主 session 整檔讀過；`runs/outline-20260920/` 33 檔由 scout 分批整檔讀過（drafts-I、page-surface 首讀有缺段，經 Stop 閘門點名後以固定 400 行分段補讀），7 個 reviewed-dropped 與 8 個 dsp-068 檔由主 session 讀過。完成以 Stop 閘門通過為準（`audit.py status` 的 session 推測曾誤報 0/10，⛔ 不當證據）。
- 盤查成本另計，不計入本計畫上限（同 9.20）：scout 4 位約 0.6M、主 session 約 0.2M。

### W1-S1（2026-10-03）

- **允許集合**：`p921-w1/allowed.json` 25 條（A 8／B 5／C 12）。第二來源以 `extract_verdict.py` 從 9.19 S2 四批 transcript 重取（`p921-w1/p919-recovered/`）：S2B1 兩份中 `agent-a21416978ec9459e2` 無結論（中途放棄），採 `agent-ac6754e5974d55854`（25／8／33，與 9.19 §6 S2 相符）。與 repo 審核單 111 條判定逐條相同；A／B／C 未審 43＝doubt 25＋⚠️ pass 18。
- **工具與備份**：工具自 `p920-w2/` 複製＋新 `scope_check.py`；備份 `p921-w1/backup/`（10:58:32，早於第一次 repo 編輯 11:37:05）；九架 roundtrip 全 True、客戶名 0 命中。
- **起草（分工與計畫不同，記錄）**：為控制主 session 成本，修正起草交 **executor**（brief `p921-w1/brief-executor-fix.md`，只准寫 scratch），產出 `ops-draft.json`＋逐句筆記 `fix-notes.md`；主 session 審閱筆記、機械驗證後才套用。另由同一 executor 產出範圍對照 `scope-map.json`（doubt 57／whole 49／both 7）與整條依據 22 條。
  - 機械驗證：25 個 id＝允許集合、停下 0；新 evidence 287 筆＋整條依據證據全部對釘住匯出逐字命中；先套 scratch 再套 repo，A～C 與試套逐位元組相同、D～I 與備份相同。
- **修正紀錄** `inputs/fix-log-9.21-W1-S1-ABC-20261003.md`：修正表 113 列、整條依據 22 條、整條待裁 2 條、另見 10 條；`scope_check` PASS、`coverage_check` PASS、drafts_diff (a)～(g) PASS。
- **核對**：A＋B 58／59、C 53／54；不過 2 項依 D1 修一次，複核 7／7 CONFIRMED（明細見修正紀錄「核對過程」）。整條列 56 列全數過；**整條列數 56（doubt＋整條並列 7、純整條 49），過 56／不過 0**。
- **生成時調整**：`forget-account-flow` 句 3 標籤中間含終止符，生成器大聲失敗 ⇒ 依 DSP-068 拆兩段引號後通過（記於修正紀錄）。
- **重生成**：scratch 試跑後對 repo 跑（`--runs-out` 寫 scratch 再複製回 repo）：`已審保留：461 條／丟棄：0 條`、57 粗目／539 細目、open_questions 54 則；DSP-068 刪除 31 行／34 字元。repo 與試跑、3 個 runs 產出逐位元組相同。`canon_check` ⇒ `blocks changed 25 (in allowed 25)`、`mismatches: 0`，客戶名 0、「系統上」6；D～I `.md` 與備份相同。`load_canon_or_die` 通過。
- **終點指標 `已審細目 pm 457／533、prospect 105／120；頁面 pm 119／183、prospect 48／183`**（不變，符合 +0；已審 461）。
- **單元與 audit**：`9 failed, 3931 passed, 3 skipped`，與基準差集＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（6 項全過；自行重跑三支檢查、逐 id 比對 jgb.json 已審 461 集合不變、25 條變動全在允許集合；自抽 12 條細目對釘住匯出（含 7 條有整條列者與 DSP-068 拆段句）全部成立；整條依據 10 筆證據逐字命中；負對照 3 筆皆 0）。附記 P4×2（「最下方」用詞、核對過程 REFUTED 字樣易誤讀），延後。
- **成本**：W1-S1 約 1.6M（executor 起草 0.61M、核對 A＋B 0.22M、C 0.22M、複核 0.13M、outcome verifier 約 0.2M、主 session 約 0.2M 估算）。⚠️ 超出本片預算 0.7M 一倍多；9.21 累計約 1.6M，第一波停點 2.0M 會被 W1-S2（估 0.6～0.8M）越過 ⇒ **W1-S1 commit 後停下回報業主**。

### W1-S2（2026-10-03）

- 2 批 fresh verifier 依序跑完，一次一位，兩批都一次解析通過：W1S2B1（33 條）pass 32／doubt 1；W1S2B2（10 條）pass 8／doubt 2；合計 **pass 40／doubt 3**。raw 由 `extract_verdict.py` 機械取出，存 `p921-s2/p921-s2-raw-W1S2B{1,2}.txt`。
- 審核單 `inputs/review-sheet-9.21-W1-S2-ABC-20261003.md`，表頭 commit `ca8b3a08`，共 14 組，⚠️ 2 組（`A-account-profile` pass 2／doubt 1、`C-estate-dashboard` pass 1／doubt 1）。
  - `check` ⇒ `targets 43; judged 43; raw-parsed 43; sheet ids 43`、`mismatches: 0`。
  - 正對照（`jgb/C/team-public-page-recruitment`）：審核單副本改 pass ⇒ 不一致 2；raw 副本改 pass ⇒ 不一致 1。
  - 正本相對 `ca8b3a08` 的 `git status` 為空。
- **D1 改法量測（業主成效判準）**：`d1_measure.py` ⇒ `denominator 25 (table 25, in targets 25, excluded [])`、`numerator 1: ['jgb/C/estate-dashboard-attachments-vs-contract-attachments']`、**`ratio 1/25 = 4.0%`（判準 < 10% ⇒ 達成）**；對照舊 D1：9.19 18%（11／61）、9.20 第一波 16%（6／38）、第二波 21%（8／38）。
  - 被抓回的 1 條：下載附件需物件編輯權限（大房東下載會收到「權限不足！」），句子與標題寫「下載不限身分」——是 W1-S1 沿用的舊句、整條檢查漏看。
- 其餘 2 條 doubt 皆為未修過的 ⚠️ 組 pass：`account-contact-info`（「第二組聯絡號碼限填純數字」程式未強制）、`team-public-page-recruitment`（標題把一般店舖也有的轉址列為差異；講法「網址不一樣嗎」答不到）。
- 依「安全組過」：W1-S3 可寫入 **37 條（pm +37、prospect +5）**；全部 pass 過則 40 條（pm +40、prospect +5）。
- **成本**：W1-S2 約 0.6M（就緒審查 0.07M、W1S2B1 0.28M、W1S2B2 0.19M、主 session 約 0.05M）⇒ **9.21 累計約 2.2M**（第一波停點 2.6M）。

### W1-S3（2026-10-03）

- **業主裁決原文**（2026-10-03，對「建議照之前的做法回『安全組過』；抽驗沿用 9.20 S6 固定種子抽 12 條」的回覆）：「安全組過」——非 ⚠️ 12 組的 pass 標已審（rule＝safe）；⚠️ 2 組全組本批不審；3 條 doubt 本批不審；無點名、無照原樣過、無排除。抽驗沿用 9.20 S6：outcome verifier 自核可集合以固定種子抽 12 條逐句對釘住匯出，任一推翻 ⇒ 以備份還原並停。
- **抽樣（派工前固定）**：`random.Random(20261003).sample(sorted(p921-s3-approved.json), 12)` ⇒ `jgb/A/notification-mark-read-navigate`、`jgb/A/forget-account-flow`、`jgb/C/estate-edit-building-transcript-general`、`jgb/B/biglandlord-report-community-rate`、`jgb/C/estate-list-sort-remembers-last`、`jgb/C/community-estates-overview-card`、`jgb/C/community-estates-category-switch`、`jgb/A/notification-settings-report-buttons`、`jgb/C/community-estates-pagination`、`jgb/B/lessee-bulk-notify`、`jgb/C/estate-list-pagination`、`jgb/C/team-public-page-edit-and-banner`（重算一致）。
- **寫入前準備**：就緒審查 READY（§5）。git 基準（`ca8b3a08`）與 status 皆為空；備份 `scratchpad/p921-s3-backup/`（12:56:25）`diff -r` 相同；紅燈基準沿用 `p920-w2/red-baseline.txt`（9 條）。
- **寫入與驗證**：`write` ⇒ `added 37`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 461 -> current 498; added lines 37; approved 37`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；`git status` 只有 A／B／C `.md` 與 `jgb.json`，CATALOG 不變；repo 與 scratch 預跑、scratch 重生成產出（保留 498／丟棄 0）皆 `diff -r` 相同。
- **終點指標 `已審細目 pm 494／533、prospect 110／120；頁面 pm 125／183、prospect 50／183`**（pm +37、prospect +5，與預期相同；A pm 52→59、B 70→78（全審）、C 56→78）。
- 單元 `9 failed, 3931 passed, 3 skipped`，差集＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（5 項＋正對照全過）：自行由審核單重算安全組 37 條（A 7／B 8／C 22），與 approved 相同；`.md` diff 只有 37 行 reviewed、`jgb.json` 只動 37×2 個 reviewed 欄位與 `canon_sha256`；終點指標逐字相同。
  - **抽驗：12／12 成立、推翻 0**（重算種子結果與 `p921-s3-sample.json` 相同）：`notification-mark-read-navigate`（標題＋3 句）、`forget-account-flow`（標題＋5 句）、`estate-edit-building-transcript-general`（標題＋2 句）、`biglandlord-report-community-rate`（標題＋2 句）、`estate-list-sort-remembers-last`（標題＋4 句）、`community-estates-overview-card`（標題＋5 句）、`community-estates-category-switch`（2 句）、`notification-settings-report-buttons`（標題＋6 句）、`community-estates-pagination`（1 句）、`lessee-bulk-notify`（標題＋3 句）、`estate-list-pagination`（1 句）、`team-public-page-edit-and-banner`（標題＋6 句）皆成立。其中 6 條為 W1-S1 依新 D1 修過者。
  - 附記 P4×2（個人「自我介紹」列的程式鍵拼錯可能無標籤、手機與電腦版刪除社區呼叫不同動作），皆程式面、不影響細目，延後。
- **成本**：W1-S3 約 0.35M（就緒審查 0.07M、outcome verifier 約 0.2M、主 session 約 0.08M）⇒ **9.21 第一波累計約 2.55M**（停點 2.6M）。

### ⏸ 第一波停點（2026-10-03）

- 終點指標：`已審細目 pm 457→494／533、prospect 105→110／120；頁面 pm 119→125、prospect 48→50`。
- D1 成效：修過 25 條重審抓回 1／25＝4.0%（判準 < 10% 達成）；終審核可 37／43＝86%（9.20 第二波 59%）。
- 成本：第一波約 2.55M（W1-S1 1.6M、W1-S2 0.6M、W1-S3 0.35M）；上限 4.0M 剩約 1.45M。
- 第二波（D／E／F／I：doubt 21＋⚠️ pass 14＝35 條）的範圍與 D1 待業主裁。

### W2-S1（2026-10-03）

- **允許集合**：`p921-w2/allowed.json` 21 條（D 10／E 3／F 2／I 6），兩來源逐 id 相同（見 W2-S1 節）；就緒審查 2 輪（§5）。
- **工具與備份**：工具自 `p921-w1/` 複製；備份 `p921-w2/backup/`（13:16:02，早於第一次 repo 編輯 13:55:14）；九架 roundtrip 全 True、客戶名 0 命中。
- **起草**：executor（`p921-w2/brief-executor-fix.md`）產出 `ops-draft.json`＋`fix-notes.md`（21 條全修、停下 0；整條修正 46 項；整條待裁 2 項），續做 `scope-map.json`（doubt 37／whole 37／both 13）與 `whole-basis.md`（20 條）。主 session 審閱筆記並機械驗證：21 id＝允許集合；新 evidence 191 筆＋整條依據證據 31 筆逐字命中；先套 scratch 再套 repo，九架與試套逐位元組相同、A／B／C／G／H 與備份相同。
  - 整條待裁 2 項的去處：`pricing-free-vs-experience-plan`（自動對帳，涉及待裁 #42／#43，刪該語不選邊）記入「整條待裁」；`pricing-quota-full-block`（未訂閱版彈窗數字位置程式判斷式疑寫反，**非 54 則待裁**）記入「另見」為 jgb2 缺陷候選，本條避開不寫數字。
  - `bill-actions-received`：起草者判 doubt 理由於現行內容已不成立，改動全為整條（權限例外、「一律」、押金設算息不通知），核對 verifier 判過。
- **修正紀錄** `inputs/fix-log-9.21-W2-S1-DEFI-20261003.md`：修正表 87 列、整條依據 20 條、整條待裁 1 條、另見 21 條；`scope_check` PASS、`coverage_check` PASS、drafts_diff (a)～(g) PASS。
- **核對**：verifier brief 依替換表機械產生，grep 驗收 9 字串 0 命中、W2 修正紀錄恰 1 命中、件數一致（D＋E 57、F＋I 30）。D＋E **56／57**、F＋I **30／30**；不過 1 項（`move-out-bill-generation` 新增句寫歷史合約同意後「不是點退完成」，程式與同組細目皆反證，P2 本片引入）依 D1 修一次，複核 **7／7 CONFIRMED**。**整條列數 50（兩者並列 13、純整條 37），過 50／不過 0**。附建議 5 則延後。
- **重生成**：scratch 試跑後對 repo 跑：`已審保留：498 條／丟棄：0 條`、57 粗目／539 細目、open_questions 54 則；DSP-068 刪除 33 行／34 字元。repo 與試跑、3 個 runs 產出逐位元組相同。`canon_check` ⇒ `blocks changed 21 (in allowed 21)`、`mismatches: 0`，客戶名 0、「系統上」5（`repair-apply-flow-and-entry` 改為「JGB 網頁介面沒有」）；A／B／C／G／H `.md` 與備份相同。`load_canon_or_die` 通過。
- **終點指標 `已審細目 pm 494／533、prospect 110／120；頁面 pm 125／183、prospect 50／183`**（不變，符合 +0；已審 498）。
- **單元與 audit**：`9 failed, 3931 passed, 3 skipped`，與基準差集＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（5 項＋終點指標重跑全過，無 P0～P2）：自行重跑三支檢查；jgb.json 已審 498 集合逐 id 相同、變動恰為 21 條允許集合且皆未審；自抽 18 句（含 13 句整條、複核句、`bill-actions-received` 2 句）對釘住匯出全部成立；整條依據 3＋3 筆證據逐字命中；`pricing-free-vs-experience-plan` 正本與 jgb.json 中「對帳」0 次（不選邊）；兩份核對 brief 9 字串 0 命中；客戶名 0；負對照（舊「加入常用帳號看收款設置權限」說法）被程式反證。附記 P4×3（「頁面上方」用詞、一筆證據引註解但下方判斷式相符、drafts／open-questions 的客戶名命中與備份及前版相同、非本片引入），延後。
- **成本**：W2-S1 約 1.55M（就緒審查 2 輪 0.13M、executor 起草＋範圍對照 0.52M、核對 D＋E 0.26M、F＋I 0.16M、複核 0.11M、outcome verifier 約 0.2M、主 session 約 0.17M 估算）。⚠️ 超出本片預算 1.3M；**9.21 累計約 4.1M，越過本片停點 3.9M ⇒ W2-S1 commit 後停下回報業主**（W2-S2 估 0.6M＋W2-S3 估 0.35M 會使總額約 5.05M，超過上限 4.8M）。

### W2-S2（2026-10-03）

- 2 批 fresh verifier 依序跑完，一次一位，皆一次解析通過：W2S2B1（D 20 條）pass 18／doubt 2；W2S2B2（E／F／I 15 條）pass 14／doubt 1；合計 **pass 32／doubt 3**。raw 由 `extract_verdict.py` 機械取出，存 `p921-w2s2/p921-w2s2-raw-W2S2B{1,2}.txt`。
- 審核單 `inputs/review-sheet-9.21-W2-S2-DEFI-20261003.md`，表頭 commit `59a43bce`，共 14 組，⚠️ 3 組（`D-contract-sign-view` pass 1／doubt 1、`D-notary` pass 2／doubt 1、`I-pricing` pass 2／doubt 1）。
  - `check` ⇒ `targets 35; judged 35; raw-parsed 35; sheet ids 35`、`mismatches: 0`。
  - 正對照（`jgb/I/pricing-free-vs-experience-plan`）：審核單副本改 pass ⇒ 報 `sheet<->results` 不一致；raw 副本改 pass ⇒ 報 `raw<->results` 不一致。
  - 正本相對 `59a43bce` 的 `git status` 與 `git diff --stat` 皆空。
- **D1 量測**：`d1_measure.py` ⇒ `denominator 21 (table 21, in targets 21, excluded [])`、`numerator 2`、**`ratio 2/21 = 9.5%`（< 10%）**；其中 1 條（`pricing-free-vs-experience-plan`）另有整條待裁項，但被抓的是標題「每月付費」與內文「月費／年費」不符，與該待裁（自動對帳）無關。**W1＋W2 合併 3／46＝6.5%**（舊 D1 16～21%）⇒ 下一份計畫沿用新 D1 的判準成立。
  - 被抓回 2 條：`contract-upload-existing-vs-electronic`（句 2 沿用畫面過時說明「最新 109 年內政部公版合約」，現行範本為 114／113 年）、`pricing-free-vs-experience-plan`（標題「每月付費」，程式可年繳）——兩者都是 W2-S1 整條檢查漏看的舊文字。
  - 另 1 條 doubt 為未修過的 ⚠️ 組 pass：`general-contract-notary-tab`（「英文版合約不支援公證」漏英文版包租業範本有公證的例外）。
- 依「安全組過」：W2-S3 可寫入 **27 條**（受眾：pm 21、pm＋prospect 4、prospect 2；確切終點增量以 W2-S3 derive 為準）；全部 pass 過則 32 條。
- **成本**：W2-S2 約 0.73M（就緒審查 0.07M、W2S2B1 0.31M、W2S2B2 0.30M、主 session 約 0.05M）⇒ **9.21 累計約 4.83M**（上限 5.1M）。⚠️ W2-S3 估 0.35M（W1-S3 實績）會使總額約 5.18M，**超過上限約 0.08M ⇒ 停下回報業主**。

### W2-S3（2026-10-03）

- **業主裁決原文**（2026-10-03，對問題「W2-S2 審核單的終審要怎麼回？」的選擇）：「安全組過」——非 ⚠️ 11 組的 pass 標已審（rule＝safe）；⚠️ 3 組全組本批不審；3 條 doubt 本批不審；無點名、無照原樣過、無排除。抽驗沿用 W1-S3：outcome verifier 自核可集合以固定種子抽 12 條逐句對釘住匯出，任一推翻 ⇒ 以備份還原並停。
- **抽樣（派工前固定）**：`random.Random(20261003).sample(sorted(p921-w2s3-approved.json), 12)` ⇒ `jgb/D/contract-edit-tabs-overview`、`jgb/E/bill-tenant-unverified-draft-lock`、`jgb/I/notification-mail-settings`、`jgb/D/early-termination-reasons`、`jgb/D/contract-rentbasic-template-and-dates`、`jgb/E/bill-actions-received`、`jgb/D/early-termination-form-fields`、`jgb/E/bill-internal-note-visibility`、`jgb/D/contract-rentbasic-latefee`、`jgb/D/move-out-bill-generation`、`jgb/I/homepage-sections-overview`、`jgb/E/recharge-account-mismatch-and-duplicate`（重算一致）。
- **寫入前準備**：就緒審查 READY（§5）。git 基準（`59a43bce`）與 status 皆為空；備份 `scratchpad/p921-w2s3-backup/`（16:43:56）`diff -r` 相同；紅燈基準沿用 `p920-w2/red-baseline.txt`（9 條）。
- **寫入與驗證**：`write` ⇒ `added 27`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 498 -> current 525; added lines 27; approved 27`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；`git status` 只有 D／E／F／I `.md` 與 `jgb.json`，CATALOG 不變；repo 與 scratch 預跑、scratch 重生成產出（保留 525／丟棄 0）皆 `diff -r` 相同。
- **終點指標 `已審細目 pm 519／533、prospect 116／120；頁面 pm 133／183、prospect 52／183`**（pm +25、prospect +6，與預期相同；D pm 84→99、E 90→96（全審）、F 31→33（全審）、I 43→45）。
- 單元 `9 failed, 3931 passed, 3 skipped`，與基準差集＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（5 項＋負對照全過）：自行由審核單重算安全組 27 條（D 15／E 6／F 2／I 4），與 approved 相同；`.md` diff 只有 27 行 reviewed、`jgb.json` 只動 27×2 個 reviewed 欄位與 `canon_sha256`；終點指標逐字相同；負對照：⚠️ 組 5 條 pass 與 3 條 doubt 仍未審。
  - **抽驗：12／12 成立、推翻 0**（重算種子結果與 `p921-w2s3-sample.json` 相同）：`contract-edit-tabs-overview`（標題＋7 句）、`bill-tenant-unverified-draft-lock`（標題＋2 句）、`notification-mail-settings`（標題＋4 句）、`early-termination-reasons`（標題＋3 句）、`contract-rentbasic-template-and-dates`（標題＋9 句）、`bill-actions-received`（標題＋10 句）、`early-termination-form-fields`（標題＋4 句）、`bill-internal-note-visibility`（標題＋2 句）、`contract-rentbasic-latefee`（標題＋2 句）、`move-out-bill-generation`（標題＋6 句，含 W2-S1 複核過的歷史合約句）、`homepage-sections-overview`（標題＋4 句）、`recharge-account-mismatch-and-duplicate`（標題＋3 句）皆成立。其中 7 條為 W2-S1 依新 D1 修過者。
  - 附記 P4×4（「會員側欄」實為「團隊管理」側欄群組、特定合作團隊匯入式批次編輯可改內部備註、「多數團隊看不到」未量化、`canon_sha256` 未重算），皆措辭或驗證範圍，延後。
- **成本**：W2-S3 約 0.37M（就緒審查 0.07M、outcome verifier 約 0.2M、主 session 約 0.1M）⇒ **9.21 累計約 5.2M**（上限 5.3M）。

### 9.21 收案（2026-10-03）

- **終點指標**：`已審細目 pm 457→519／533、prospect 105→116／120；頁面 pm 119→133、prospect 48→52`（pm +62、prospect +11）。剩餘未審：pm 14、prospect 4（W1 ⚠️／doubt 6 條＋W2 ⚠️／doubt 8 條）。
- **新 D1「修整條」成效**：重審抓回 W1 1／25、W2 2／21，**合併 3／46＝6.5%**（舊 D1 16～21%）；終審核可 W1 37／43、W2 27／35。代價：修正片成本 W1 1.6M、W2 1.55M，約為舊 D1 的兩倍。⇒ 下一份計畫沿用新 D1。
- **成本**：約 5.2M（第一波 2.55M、W2-S1 1.55M、W2-S2 0.73M、W2-S3 0.37M），上限經業主三次放寬（4.0→4.8→5.1→5.3M）；主因是新 D1 修正片與先審代理單批成本皆高於預估。
- **留給下一份計畫**：
  - 未審 14 條：W1 ⚠️ 組 3 條 pass＋3 條 doubt（見 W1-S2 審核單）；W2 ⚠️ 組 5 條 pass＋3 條 doubt（`contract-upload-existing-vs-electronic`「最新 109 年」、`general-contract-notary-tab` 英文版包租業有公證、`pricing-free-vs-experience-plan` 標題「每月付費」）。
  - 整條待裁：W1 2 條、W2 1 條（#42／#43 自動對帳）；另見：W1 10 條、W2 21 條（含 jgb2 缺陷候選：未訂閱版額度彈窗數字位置）。
  - 各片延後建議與 P4 附記（明細見各修正紀錄「核對過程」與 §6 各片）。
