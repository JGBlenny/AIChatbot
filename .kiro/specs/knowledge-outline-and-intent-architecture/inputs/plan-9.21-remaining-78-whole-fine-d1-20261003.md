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

### W1-S3 — 業主終審＋寫入（pm 最多 +43）
- 同 9.20 S3／S6；outcome verifier 沿用固定種子抽驗（核可數 ≥ 12 時抽 12 條，否則全抽）。
- 預算約 0.35M。

#### ⏸ 第一波停點
W1-S3 commit 後停下，回報終點指標、累計成本、D1 量測結果。第二波在業主明示後才開始。

### W2-S1／S2／S3 — D／E／F／I（21 條 doubt 修正、35 條重新先審、終審）
- 同第一波，架換 D／E／F／I（W2-S1 開工前另送就緒審查，屆時寫出全部常數：不變位元組為 A～C、G、H；`--expect-reviewed-kept` 以 W1-S3 後實值為準；D1 依停點裁決）；允許集合來源：S5 審核單（D／E）與 S2 審核單（F／I）＋各自 raw（`p920-w5/p920-s5-raw-*`、`p920-w1/p920-s2-raw-*`，不在則從 transcript 重取）。
- 預算約 0.6＋0.5＋0.3M。

## 2. 不做（另案）
- 新起草細目（頁面真缺口約 11～12 頁）、頁面量尺改造、prospect 可見頁範圍定義——皆待業主裁（HANDOFF §12-4）。
- 54 則待裁、jgb2 缺陷清單、6 條 `sources` 必填紅燈。
- 講法核可（`approved`）與回答品質量測。

## 3. 業主裁決與待裁
- **已裁（2026-10-03「D1 改整條、9.21 照建議」）**：見 §0。
- **業主裁決（2026-10-03）**：「核可」——核可大綱＋W1-S1；執行模式沿用 ASK（每片回報）。W1-S2 起各片開工前各自再送就緒審查。

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
