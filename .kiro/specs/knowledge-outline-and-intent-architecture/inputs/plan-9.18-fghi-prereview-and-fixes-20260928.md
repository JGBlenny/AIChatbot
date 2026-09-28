# Plan 9.18：F／G／H／I 四架先審＋業主終審，並修客戶名與 IoT 例外、盤出頁面缺口

> **現況**（`endpoint_progress.py`，2026-09-28，commit `2d4260d2`）：`已審細目 pm 250／535、prospect 37／121；頁面 pm 70／183、prospect 18／183`。
>
> **本計畫預期**：
> - S1 淨 +0：IoT 那 1 條已審細目內容要改，會先掉已審（pm 250→249），業主重審通過後回到 250；客戶名 7 條原本就未審，不影響已審數。
> - S3 pm 最多 +112、prospect 最多 +38（F～I 全部）。依 9.17 先審約七成通過、安全組規則，實際預期約 **pm +55～75**。
> - S2、S4 都是 +0。
>
> 參考上限（正本副本假設全審實測）：F～I 全審 ⇒ 頁面 pm 101、prospect 36。

## 0. 為什麼有這份

- 業主 2026-09-28 裁示「照建議」。建議內容：9.18 先做 F G H I 先審，順帶修客戶名與 IoT 例外，並盤出頁面缺口；A～E 剩下的 173 條（先修疑點再重審）放 9.19。
- 選 F～I 的理由（實測，見 §6 附錄）：每條細目換到的頁面比 A～E 多約五成（F～I 118 條換 +31 頁；A～E 173 條換 +36 頁），prospect 頁面也多（+18 對 +14）。
- 頁面指標（M2）是**代理指標**：頁面算不算覆蓋，看有沒有細目的 `code:` 來源對到該頁的元件路徑。九架全審也只到 pm 135／183，差的 48 頁可能是真的沒寫，也可能是細目引用的路徑不同。S4 把這兩種分開。

## 1. 切片（順序：S1 → commit → S2 → S3；S4 可排在 S2 之前或之後，唯讀、不動正本）

### S1 — 客戶名改寫＋`bill-scheduled-send-rule` 補 IoT 例外（淨 +0；途中已審 −1 再 +1）

- **客戶名掃描**（2026-09-28 現樹）：
  - 樣式：`(?<!系)統上|新北住都|樓宇|資育|資聯|泰萬通|Beyond360|beyond360|安歌|喬立|joeRich|nthurc|tongSang|21228`。「統上」前面排除「系」，因為「系統上」不是客戶名；正本裡「系統上」共 6 處。
  - 命中 7 條，全部未審：
    - `jgb/A/notification-settings-report-buttons`（樓宇）
    - `jgb/B/advance-discount-items`、`jgb/B/advance-late-fee`、`jgb/B/advance-payment-cycle-discount`、`jgb/B/advance-short-lease-approval`、`jgb/B/lessee-bulk-notify`（統上／新北住都）
    - `jgb/D/contract-rentbasic-latefee`（新北住都）
  - 正對照：「只給統上合作團隊」命中。負對照：「匯出筆數超過系統上限」不命中。
  - 初版計畫用「統上」子字串掃出 12 條，其中 E 3 條、F 2 條是「系統上」誤中，已由就緒審查第 1 輪抓出並更正。
- **允許集合**：`scratchpad/p918-s1-allowed.json`＝上述 7 條＋**已審** `jgb/E/bill-scheduled-send-rule`，共 8 條，已寫好。
- **做法**：
  1. **改前備份**：drafts-A／B／D／E、`rag-orchestrator/canon/`、`runs/outline-20260920/` 既有 `*-20260928*` 產出，備份到 `scratchpad/p918-s1-backup/`。
  2. **改寫工具**：`scratchpad/p918_edit.py`，是 `p916_edit.py` 的 p918 副本。
     - 變更值：`TRAIL` 依架判斷檔尾換行。已實測 load＋dump 位元組相同：A、E 無換行，B、D 有換行。
     - roundtrip 檢查範圍改為 A B D E。
     - 以 `ALLOWED=p918-s1-allowed.json` 限制可改的細目。必填，未給即失敗。
     - **已預跑**：`--roundtrip` ⇒ A B D E 皆 `byte-identical: True`；負對照改允許集合外的 `jgb/B/advance-fee-items` ⇒ 拒絕（exit 1）。
  3. **客戶名改寫**：
     - 標題、句子、講法裡的客戶名一律改成「特定合作團隊」。
     - 若同一條要區分兩個不同團隊的行為，寫成「部分特定合作團隊」＋差異本身，⛔ 寫名稱（§3 D1）。
     - 只改名稱，⛔ 順手修該條的其他疑點；那些留給 9.19。
  4. **IoT 例外**：依 `inputs/evidence-9.17-S3b-scheduled-send-meter-20260927.md` 的 E3～E5，句 2 補上例外：唯一未填的是電費、物件綁定 IoT 電錶、而且讀得到讀數時，仍可排入；度數在排入與發送時自動補上，補不到或 0 度則不送出。
     - 來源：釘住匯出 `app/Bill.php` `checkIotBill`、`app/Console/Commands/BillBatchSend.php` `prepareIotMeterForSend`。
     - 標題若斷言「只有度數填完才能排」，一併改成和內文一致。
  5. **修正紀錄**：`inputs/fix-log-9.18-S1-<日期>.md`，格式同 9.17 S3。fresh verifier 逐項核（D1：修一次仍不過就整句刪），並核對 7 條客戶名細目已無客戶名殘留、句意沒變。
- **差異比對工具**：`scratchpad/p918_s1_drafts_diff.py`，是 `p916_s2_drafts_diff.py` 的 p918 副本。
  - 變更值：`SHELVES` 由環境變數 `P918_DIFF_SHELVES` 決定，預設 `ABDE`；輸出訊息列出架名。
  - **已預跑**（2026-09-28）：
    - 現行 drafts 對自身比 ⇒ `fines in base (shelves ABDE): 342; doubt set: 8 (not found in base: 0)`，(b)(c)(f) 皆 0，`RESULT: PASS`。
    - 正對照：scratch 副本各改 B `advance-fee-items`、E `bill-list-export` 一句 ⇒ (b) 2、(c) 2，逐條報出，`RESULT: FAIL`。
- **重生成**：
  - S1 生成器、在容器裡跑，參數 `--date 20260928-s1`、`--expect-reviewed-kept 249`（250 − IoT 1 條）、`--expect-open-questions <實算>`。
  - 先在 scratchpad 試跑；全部 `--expect-*` 通過，才對 repo 跑。
- **重審寫入**：
  1. 修正後的 `bill-scheduled-send-rule` 交業主重審。業主回覆原文逐字記入 §6「### S1」。
  2. 業主回「過」⇒ 寫 `scratchpad/p918-s1-rereview.json`＝`["jgb/E/bill-scheduled-send-rule"]`；不過 ⇒ 不寫、維持未審。
  3. 寫入前把 `rag-orchestrator/canon/` 備份到 `scratchpad/p918-s1-rereview-backup/`，並用 `diff -r` 確認相同。
  4. 工具 `scratchpad/p918_approved.py`（`p917_s2_approved.py` 的通用副本；必填環境變數 `P918_WRITE_SHELVES`，verify 的「不得變動架」自動取其補集）：
     - `P918_WRITE_SHELVES=E python3 p918_approved.py write p918-s1-rereview.json --date <日期>`
     - 容器重匯出＋`load_canon_or_die`
     - `P918_WRITE_SHELVES=E python3 p918_approved.py verify p918-s1-rereview.json --backup scratchpad/p918-s1-rereview-backup`
  5. **已預跑**（scratch 正本副本，先拿掉該條 reviewed 行來模擬重生成後的狀態）：
     - write ⇒ `added 1 reviewed lines`；重匯出＋`load_canon_or_die` 通過。
     - verify ⇒ `reviewed backup 249 -> current 250; added lines 1`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
     - 正對照：D.md 多一行 reviewed ⇒ `D.md differs from backup`。
     - 未給 `P918_WRITE_SHELVES` ⇒ 直接失敗。
- **驗收**：
  - 差異比對（`p918_s1_drafts_diff.py`，`--doubt p918-s1-allowed.json`、`--fix-log` 本片修正紀錄、基準＝`p918-s1-backup` 的 drafts）：(a)～(f) 全 PASS。
  - drafts-C／F／G／H／I 與備份逐位元組相同（`cmp`）。
  - 重生成：
    - 印出 `已審保留：249 條／丟棄：1 條`，且 `reviewed-dropped-20260928-s1.json` 只含 `jgb/E/bill-scheduled-send-rule`。
    - C F G H I `.md` 與備份逐位元組相同。
    - A B D E 的區塊差異只在允許集合內；`jgb.json`／`CATALOG.md` 的差異只在允許集合 id（＋sha）。
  - 客戶名：
    - 修正後用上述樣式掃全正本 ⇒ 0 命中。
    - 「系統上」出現次數仍是 6。
    - 正對照：scratch 副本插入「統上」⇒ 命中。
  - 重審寫入後：
    - verify `mismatches: 0`；E.md 新增行數＝業主通過數、刪除 0。
    - 已審 id 集合＝寫入前集合 ∪ 通過 id（逐 id 比對）。
    - `load_canon_or_die` 通過；除 E.md 外其他架、CATALOG、README 與重審備份逐位元組相同；`jgb.json` 只在通過 id 多 `reviewed_*`。
  - 終點指標：pm＝249＋（過則 1）、prospect＝37＋（過且該條 target_user 含 prospect 則 1）。
  - 全套單元紅燈＝既有 9 條；`make audit` PASS；fresh outcome verifier（在 S1 commit 前，逐條核上述各項）。
- **停止**：
  - 客戶名改寫必須靠臆測才能保住句意 ⇒ 不改該條、停下交業主。
  - 差異比對不過、重生成丟棄的不是那 1 條、或 `--expect-*` 失敗：
    - 還沒對 repo 跑 ⇒ 不還原，直接停；
    - 已對 repo 跑 ⇒ 用 `p918-s1-backup/` 還原 drafts、正本與產出後再停。
  - 重審寫入後 verify 或驗收不符 ⇒ 用已驗證的 `p918-s1-rereview-backup/` 還原正本，停下交業主。
  - 業主重審不過 ⇒ 該條維持未審，已審數 249，照實記入 §6；業主的重審裁決本身就是明示。
- **擁有**：
  - drafts-A／B／D／E.json（只限允許集合）
  - `rag-orchestrator/canon/`（重生成＋重審 reviewed 行）
  - `runs/outline-20260920/*-20260928-s1*`
  - 修正紀錄、本計畫 §6、HANDOFF 終點行
  - scratchpad 的 p918-s1 檔與工具
- **回滾**：用 `p918-s1-backup/` 還原 drafts、正本與產出，並刪除 `*-20260928-s1*`。
- **預算**：約 0.35M（修正 verifier 最多 2 輪、outcome verifier）。

### S2 — F／G／H／I 代理先審（+0；是 S3 的前置）

- **分母**：S1 commit 後，F／G／H／I 中沒有 `- reviewed:` 行的細目。預期 118 條（F 33、G 26、H 5、I 54），清單存 `scratchpad/p918-s2-targets.json`；數目≠118 即停。
- **工具**：`p917_s1_sheet.py` 的 p918 副本 `scratchpad/p918_s2_sheet.py`。變更值：
  - `SHELVES="FGHI"`
  - `CANON_COMMIT=<S1 commit>`
  - 前綴 `p918-s2-*`
  - 審核單標題「Plan 9.18 S2 F／G／H／I」與回覆說明「S3」

  覆蓋守門沿用。
  - **已預跑**（2026-09-28，S1 commit `af8a86df` 後）：
    - `CANON_COMMIT="af8a86df"`，`SHELVES` 預設為 `FGHI`（環境變數 `P918_SHELVES`），前綴 `p918-s2`，標題與回覆說明已改。
    - targets 118（F 33／G 26／H 5／I 54）；批次 S2B1～S2B4＝33／31／31／23，聯集＝targets、不交。
    - 空結果審核單 `check` ⇒ `targets 118; judged 0; raw-parsed 0; sheet ids 118`、`mismatches: 0`。
    - 負對照：`P918_SHELVES=FGH` ⇒ `❌ 54 targets not found…`；審核單副本刪掉一組 ⇒ `sheet coverage: sheet ids 108 vs targets 118` 與組缺失。
- **批次**（粗目不拆，每批 ≤35）：

  | 批 | 條數 | 粗目 |
  |---|---|---|
  | S2B1 | 33 | F 全架（repair-list／apply／edit／share） |
  | S2B2 | 31 | G 全架（power-meter／device-page／remote-unlock）＋H-help-center |
  | S2B3 | 31 | I-pricing＋I-subscription-payment |
  | S2B4 | 23 | I-demo-booking／control-panel／marketing-home／hicloud-order |

  對照表派工前存成 `scratchpad/p918-s2-batches.json`（聯集＝targets、不交）。
- **做法**（同 9.17 S1）：
  - 每批一位 fresh verifier，序列跑，一次一位。
  - brief＝9.17 S1 第 2 批起的版本，含「最後一則只放一份結論」，路徑改指本批所屬架。
  - 最終訊息用 `p916_s3_extract.py` 機械取出；results 只由 `parse` 產生。缺 id、多 id、格式錯 ⇒ 同一代理重貼一次，再失敗就停。
- **審核單**：`inputs/review-sheet-9.18-S2-FGHI-<日期>.md`，由腳本產生；⚠️＝doubt 超過該組待審的 30%。
- **驗收**：
  - `check` 輸出含 `targets 118; judged 118; raw-parsed 118; sheet ids 118`，`mismatches: 0`。
  - 正對照兩個（審核單副本、raw 副本各把一條 doubt 改成 pass）都報出。
  - 正本與 drafts 相對 S1 commit 的 `git diff --stat` 為空。
- **brief 的來源清單**：以 9.17 S1 第 2 批起的版本為基礎，另加一項 `doc:<絕對路徑>` ⇒ 直接讀該路徑（與 `help:` 同目錄的幫助中心文件）。
  - F／G／H／I 的 `sources` 實測只有三種前綴：`code:`（F 61、G 52、H 9、I 80）、`help:`（F 4）、`doc:`（I 3，即 `payment-vendor-options-overview`、`payment-newebpay-setup-details`、`payment-permission-menu-visibility`）。細目數 118，與 targets 相符。
  - **衝突規則**：畫面、權限與流程行為以現行程式為準，文件與程式衝突 ⇒ doubt；費率、金額等程式裡沒有的事實，以該文件為唯一來源逐句對。
  - 派工前以 grep 確認：本批細目 `sources` 的每一種前綴都出現在 brief 的來源清單裡。
- **擁有**：審核單、本計畫 §6、scratchpad 的 p918-s2 檔。⛔ 改正本。
- **停止**：
  - targets≠118 ⇒ 不派工。
  - 某批交件失敗（重貼一次仍失敗）或累計達 D4 停點 2.0M ⇒ 停止派下一批。已完成的批次保留 raw／results；可產生部分審核單，未跑的批次在審核單列「未先審」，該組不可整組回「過」。交業主決定追加或縮小範圍。
- **回滾**：只新增審核單與 scratchpad 的 `p918-s2-*` 檔。刪除審核單與 `p918-s2-raw-*`／`p918-s2-results.json` 即可；正本與 drafts 不動。
- **預算**：4 批 × 約 0.19M ≈ 0.8M。

### S3 — 業主終審＋寫入已審（pm 最多 +76、prospect 最多 +24；實算見下）

- **業主回覆**依審核單 `inputs/review-sheet-9.18-S2-FGHI-20260928.md`，可以這樣回：
  - 規則二選一：「安全組過」＝非 ⚠️ 組的 pass；或「全部 pass 過」。
  - 點名某個 ⚠️ 組「過」：只收該組的 pass。
  - 逐條點名某條 doubt「照原樣過」。
  - 逐條點名某條 pass「不要」（排除）。

  沒被點名的 doubt 一律本批不審。回覆若無法完整寫成 rule／warn_groups／doubt_as_is／exclude 四欄（附條件、語意不明、點到不存在的組或 id），就不做 derive，回問業主。
- **工具**：`scratchpad/p918_approved.py`（`p917_s2_approved.py` 的通用副本，子命令 derive／write／verify）。
  - 環境變數：`P918_WRITE_SHELVES=FGHI`（必填）；`P918_SHEET` 填審核單絕對路徑（derive 必填）。
  - `P918_PLAN_SECTION` 用預設的「### S3」。derive 會檢查 `reply` 是否逐字出現在本計畫 §6「### S3」段內。
  - results／targets 固定讀 `scratchpad/p918-s2-results.json`、`p918-s2-targets.json`。
  - verify 的「不得變動架」自動取 A～E。
- **步驟**（⛔ 手選 id、⛔ 手改正本）：
  1. **記錄裁決**：業主回覆原文先逐字記入 §6「### S3」。再依原文寫 `scratchpad/p918-s3-decision.json`，格式為 `{"reply": 原文, "rule": "safe"|"all"|"none", "warn_groups": [...], "doubt_as_is": [...], "exclude": [...]}`。
  2. **推導核可清單**：
     ```
     P918_WRITE_SHELVES=FGHI P918_SHEET=/Users/chenqinghuang/dev/work/AIChatbot/.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.18-S2-FGHI-20260928.md python3 p918_approved.py derive p918-s3-decision.json --out p918-s3-approved.json
     ```
     推導規則：核可＝（依規則選中的組 ∪ 點名的 ⚠️ 組）的 pass id，扣掉 exclude，再加上點名照原樣過的 doubt id。
     - 來源 A 是審核單的列與 ⚠️ 標記。
     - 來源 B 是 results＋targets＋正本分組，⚠️ 以 doubt／待審 >30% 重算。
     - 兩個來源算出的集合相同才寫檔。
  3. **備份**：把 `rag-orchestrator/canon/` 整個複製到 `scratchpad/p918-s3-backup/`，用 `diff -r` 確認相同。另外 `git diff --stat af8a86df -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 都要為空（2026-09-28 實測皆空）。
  4. **寫入**：
     ```
     P918_WRITE_SHELVES=FGHI python3 p918_approved.py write p918-s3-approved.json --date <日期>
     ```
     只在 F～I 核可細目的 `- sources:` 行之後加 `- reviewed: {by: owner, at: <日期>}`。
  5. **重匯出**：容器內 `parse_canon_dir('/app/canon/jgb')` → `export_json`／`export_catalog` → `load_canon_or_die('/app/canon')`。⛔ 重跑生成器改正本。
  6. **驗證**：
     ```
     P918_WRITE_SHELVES=FGHI python3 p918_approved.py verify p918-s3-approved.json --backup p918-s3-backup
     ```
     接著跑下面「驗收」各項。
- **已預跑**（2026-09-28；用 scratch 計畫副本，§6 內放測試原文；用 scratch 正本副本 `pc8/`；repo 未動）：
  - **derive 四種回覆**，兩來源推導結果都相同：

    | 回覆 | 核可 | 分架 | 已審細目增量 |
    |---|---|---|---|
    | 「安全組過」 | 58 | F 12／G 20／H 4／I 22 | pm +54、prospect +16 |
    | 「全部 pass 過」 | 80 | | pm +76、prospect +24 |
    | 「安全組過，I-pricing 也過，tcloud-payment-instructions 照原樣過」 | 64 | | |
    | 「安全組過，但 repair-list-columns 不要」 | 57 | | |

  - **derive 負對照**，以下全部失敗：
    - 點名非 ⚠️ 組 `G-power-meter`；
    - 把 pass id 當成 doubt 照原樣過；
    - exclude 一個不在選中組裡的 id；
    - 決定檔沒有原文；
    - 原文不在 §6 S3 段內；
    - 未知欄位 `except`；
    - 真計畫尚無 §6「### S3」。
  - **寫入流程**：write 58 條＋容器重匯出＋`load_canon_or_die` 通過。
    - verify ⇒ `reviewed backup 250 -> current 308; added lines 58`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
    - 同一份清單重跑 write ⇒ 拒絕。
  - **verify 正對照**：
    - A.md 加一個換行 ⇒ `A.md differs`；
    - README 加一字元＋多一個檔 ⇒ `README.md differs`、`canon file set differs`；
    - 改 `jgb.json` 的粗目標題 ⇒ `coarse-level fields changed`；
    - 寫入後未重匯出 ⇒ 58 項不符。
  - **終點指標**（scratch）：`已審細目 pm 304／535、prospect 53／121；頁面 pm 79／183、prospect 23／183`。
- **驗收**：
  - **決定檔忠於原文**：`reply` 與 §6 S3 原文逐字相同；四欄每個值都能在原文找到依據，原文每一句核可或排除也都有對應的欄位值（雙向）。由 fresh outcome verifier 逐條勾選。
  - verify 結果為 `mismatches: 0`，具體是：
    - 已審 id 集合＝備份的 250 ∪ 核可（逐 id 比對）。
    - F～I 相對備份只多了 `- sources:` 後的 reviewed 行，只出現在核可 id 上，行數＝核可數，刪除 0 行。
    - A～E `.md`、`jgb/CATALOG.md`、`README.md` 與備份逐位元組相同，檔案集合也相同。
    - `jgb.json` 只在核可細目多出 `reviewed_*`，頂層只有 `canon_sha256` 變；粗目層欄位與其他細目欄位都沒變。
  - **未經業主核可的細目 0 條被標**：由「已審 id 集合＝250 ∪ 核可」加上「決定檔忠於原文」推得。
  - `load_canon_or_die` 通過。
  - **終點指標** `endpoint_progress.py`：pm＝250＋derive 印出的 pm 增量；prospect＝37＋derive 印出的 prospect 增量。
  - **重生成保留檢查**：只在 scratch 跑。先複製正本到 `scratchpad/p918-s3-regen-canon`，再以 `--front-matter-from /scratch/p918-s3-regen-canon/jgb --canon-root /scratch/p918-s3-regen-canon --runs-out /scratch/p918-s3-regen-runs --date 20260928-s3check --expect-reviewed-kept <250＋核可數> --expect-open-questions 54` 試跑（54 是 S1 重生成實算值，S2 沒動 drafts）。
    - 要求印出 `已審保留：<250＋核可數> 條／丟棄：0 條`。
    - scratch 產出的 `.md`、CATALOG、jgb.json 與 repo 正本逐位元組相同。
    - ⛔ 對 repo 跑。
  - 全套單元紅燈＝既有 9 條；`make audit` PASS；fresh outcome verifier（在 S3 commit 前）。
- **停止**：
  - **寫入前**（步驟 1～3）失敗：回覆不符四欄形式、derive 失敗、備份 `diff -r` 不同、`git diff --stat af8a86df -- rag-orchestrator/canon` 非空。處置：**不還原**，直接停下交業主。
  - **寫入後**（步驟 4 起）失敗：write 失敗、重匯出或 `load_canon_or_die` 失敗、verify 任一不符、終點指標≠預期、重生成保留數≠250＋核可數、單元紅燈≠既有 9 條、`make audit` 非 PASS、outcome verifier 非 CONFIRMED。處置依序是：
    1. 用步驟 3 已通過 `diff -r` 的 `scratchpad/p918-s3-backup/`，整個還原 `rag-orchestrator/canon/`；
    2. 用 `diff -r` 確認與備份相同，並確認 `git diff --stat af8a86df -- rag-orchestrator/canon` 為空；
    3. 停下交業主。

    這種「驗收失敗、還原回 250」屬本片預先授權的還原，不算 §4 的已審下降；但若已審數低於 250，仍須業主明示。
- **擁有**：
  - `rag-orchestrator/canon/jgb/F.md`、`G.md`、`H.md`、`I.md`、`jgb.json`、`jgb/CATALOG.md`
  - 本計畫 §6、HANDOFF 終點行
  - scratchpad 的 `p918-s3-decision.json`、`p918-s3-approved.json`、`p918-s3-backup/`、`p918-s3-regen-*`
  - ⛔ drafts、A～E、其他工作線檔。
- **回滾**（已 commit 後）：以 `scratchpad/p918-s3-backup/` 還原，或 revert 該 commit；已審數會下降，須業主明示。
- **預算**：寫入由主 session 做；outcome verifier 約 0.15M。

### S4 — 頁面缺口清單（+0，唯讀）

- 主 session 寫 `scratchpad/p918_page_gap.py`，用和 `endpoint_progress.py` 同一套 `page_hit` 規則，列出 page-surface `in_baseline` 裡**不分已審、pm 身分**都沒有細目指到的頁。預期 48 頁（＝183−135，以 `--ignore-review` 的正對照交叉核）。
- 每頁再分三類：
  1. **近似命中**：同一元件目錄或同一 controller 有細目引用，只是路徑不逐字相等 ⇒ 多半是引用寫法不同，不是沒寫。
  2. **完全無細目**。
  3. **不該算**：例如純跳轉頁或錯誤頁，只列出，不裁決。
- prospect 身分另列一張表。
- 產出 `inputs/page-gap-9.18-<日期>.md`：每頁附 component／controller 與分類依據。⛔ 在本片補寫細目。
- **驗收**：
  - 缺口頁數＝183 − 現樹 `--ignore-review` 的 pm 頁數。
  - 正對照：一個已覆蓋的頁在清單中不出現；把 scratch 副本中某條細目的 sources 刪掉後，該頁會出現。
- **預算**：約 0.1M（主 session 自做；分類有疑義的頁由一位 scout 抽查）。

## 2. 不做（另案）

- A～E 未審 173 條（A／B／C 110 條、D／E 63 條）的疑點修正與重審 ⇒ 9.19。
- 缺口頁的細目補寫 ⇒ 依 S4 清單另開計畫。
- drafts `evidence` 欄內的客戶名：不是對外文字，不在本計畫範圍。
- jgb2 缺陷與文件不一致交產品。

## 3. ⏳ 待業主裁

- **D1**：客戶名改寫規則為「特定合作團隊」；需要區分兩個團隊時寫「部分特定合作團隊」＋差異，⛔ 名稱。另沿用 9.16：修一次仍不過就整句刪，內容一改就重審。（建議：同意）
- **D2**：S1 會讓已審的 `bill-scheduled-send-rule` 暫時掉審（pm 250→249），業主重審後回補。事先同意這個暫時下降嗎？（建議：同意；這是 9.17 S3b 業主已裁「B 不完整，下個計畫補例外」的執行）
- **D3**：S3 終審標準沿用「安全組過、⚠️組不審」？（建議：沿用，看審核單後再定）
- **D4**：預算上限 2.2M（S1 0.35＋S2 0.8＋S3 0.15＋S4 0.1＋就緒審查 0.3＋預留 0.5）；累計達 2.0M 先停下交業主。（建議：可以）

- **業主裁決（2026-09-28）**：「核可，D1～D4 照建議、ASK 模式 (Recommended)」。

## 4. 停止條件（全片共用）

- 已審細目數在 S1 以外任何時候下降 ⇒ 停下交業主。S1 的 −1 已由 D2 事先授權，而且只准是 `jgb/E/bill-scheduled-send-rule`。
- 正本只准在 S1（重生成＋重審 reviewed 行）與 S3（只加 reviewed）變動。
- 累計達停點先停下交業主；超過上限即停。
- 一次只跑一個代理（本機 8GB）。

## 5. 就緒審查紀錄

- 大綱＋S1 第 1 輪＝REVISE（P1×1、P2×2）：
  1. 【P1】客戶名掃描用「統上」子字串，把「系統上」誤判成客戶名。E 的 3 條已審與 F 的 2 條被誤列；已審暫降數、`--expect-reviewed-kept` 與 D2 都跟著錯；「全文 0 命中」的驗收也算不出來。
  2. 【P2】差異比對工具寫死 D／E，蓋不到 A／B 的改動，而且會因為 id 不在基準裡而固定失敗。
  3. 【P2】重審寫入沒有可執行的工具，也沒有精確驗收。

  **全數 FIX**：
  - 樣式改成 `(?<!系)統上`，加正負對照；允許集合 13 → 8，已審暫降 4 → 1；表頭、D2、§4 同步更正；S1 擁有範圍移除 drafts-F。
  - 新增 `p918_s1_drafts_diff.py`（ABDE）並預跑正對照；新增 `p918_approved.py`（`P918_WRITE_SHELVES`）並預跑重審寫入與正負對照；驗收寫明逐項判定。
  - P3 採納：IoT 標題一併對齊；未動的架與 drafts 以 `cmp` 驗證。
- 大綱＋S1 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 交業主核可（`next_gate: user_approval`）。S2、S3 開工前各自再過就緒審查。
- S2 第 1 輪＝REVISE，P2×2：
  1. brief 來源清單漏了 I 架 3 條細目使用的 `doc:`，衝突規則也沒寫；
  2. 缺「回滾」與「停止」（中途停下時的處置）。

  **FIX**：加入 `doc:` 位置與衝突規則，並實測 F～I 前綴只有三種（附條數）；補「停止」與「回滾」兩欄。
- S2 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 依業主 9.18 核可開跑（ASK 模式，每批回報）。各批 brief 已生成（`scratchpad/p918-s2-brief-S2B*.txt`），且逐批以 grep 確認 sources 前綴都在來源清單內：S2B1 code／help、S2B2 code、S2B3 code／doc、S2B4 code。
- S3 第 1 輪＝REVISE，P2×2：
  1. 工具名寫成不存在的 `p918_s3_approved.py`，也沒寫出 derive／write／verify 的完整指令與必填環境變數；
  2. 「逐條同 9.17 S2」照搬了 9.17 寫死的擁有範圍（⛔ D～I）、git 基準 `f03be3b0`、`--expect-open-questions 54` 等值，彼此衝突，照字面執行會誤停。

  **FIX**：S3 改寫成完整獨立的一片：
  - 工具改指 `p918_approved.py`，三條指令附完整環境變數；
  - 決定檔、核可清單、備份檔名寫明；
  - 擁有範圍改為 F～I；
  - git 基準改為 `af8a86df`（實測為空）；
  - 重生成檢查寫明 `--expect-reviewed-kept <250＋核可數> --expect-open-questions 54`（S1 實算）。

  P3 一併處理：補跑並記錄其餘負對照與 verify 正對照。
- S3 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 審核單交業主終審。

## 6. 執行紀錄

### S1（2026-09-28）

- **業主重審裁決原文**（`jgb/E/bill-scheduled-send-rule` 修正後全文）：「過 (Recommended)」。
- **備份**：`scratchpad/p918-s1-backup/`（drafts 全架、canon；runs 當時無 `*-20260928*` 產出）。
- **修正**：用 `p918_edit.py` 改 8 條、共 18 個改動項。修正紀錄見 `inputs/fix-log-9.18-S1-20260928.md`。
  - 客戶名 7 條第一次核即全過。
  - IoT 新句與標題第一次核不過：寫了「唯一例外」，但 `checkIotBill` 對點退帳單（`BILL_TYPE_MOVEOUT`）也直接放行。依 D1 修一次，改寫為「例外有兩種」，複核通過。
  - 差異比對 (a)～(f) PASS；drafts-C／F／G／H／I 與備份相同。
- **重生成**：scratch 試跑後對 repo 跑。
  - 結果：`已審保留：249 條／丟棄：1 條`（`jgb/E/bill-scheduled-send-rule`，content_changed），repo 產出與試跑逐位元組相同。
  - `p918_s1_canon_check.py`：
    - 變動區塊 8 條＝允許集合；C F G H I 與 README 相同；jgb.json 與 CATALOG 只在允許集合變動。
    - 客戶名在 `.md`／CATALOG／jgb.json 全部 0 命中，「系統上」仍 6 處。
    - 正對照：備份正本命中 17＋24；改允許集合外一條 ⇒ 報出。
- **重審寫入**：
  - 重審備份 `scratchpad/p918-s1-rereview-backup/` 以 `diff -r` 確認相同。
  - `p918_approved.py write` ⇒ `added 1`；重匯出＋`load_canon_or_die` 通過。
  - verify ⇒ `reviewed backup 249 -> current 250; added lines 1`、`mismatches: 0`。
  - 已審 id 集合與 S1 前逐 id 相同（250）。
- **終點指標**：`已審細目 pm 250／535、prospect 37／121；頁面 pm 70／183、prospect 18／183`，淨 +0，符合預期。
- **其他檢查**：單元紅燈與 9.17 S2 相同，為既有 9 條；`make audit` PASS。
- **fresh outcome verifier＝CONFIRMED**（8 項全過）。附記：
  - **P3（本片引入，延後 9.19）**：`drafts-E.json` 該條插句後，`evidence[].sentence_index` 沒有跟著位移，新句也沒有配上證據。影響只在 `render_drafts.py` 產生的審閱稿〔來源〕標註，正本與 jgb.json 不帶 evidence。
    - 根因：`p916_edit.py`／`p918_edit.py` 的 `insert_after` 不會位移 evidence 句序。9.16 S2 的插句可能也有同樣情形，9.19 一併盤查。
  - **P4**：「讀數是 0 度」較精確的說法是用電量 0；負用量也會被跳過。留 9.19。
- **成本**：就緒審查 ×2 約 0.13M、修正 verifier ×2 約 0.17M、outcome verifier 約 0.12M ⇒ 9.18 累計約 0.45M。

### S2（2026-09-28）

- 4 批 fresh verifier 序列跑完（一次一位），F／G／H／I 合計 **pass 80／doubt 38**：

  | 批 | 範圍 | 條數 | pass／doubt |
  |---|---|---|---|
  | S2B1 | F | 33 | 21／12 |
  | S2B2 | G＋H | 31 | 25／6 |
  | S2B3 | I-pricing＋I-subscription-payment | 31 | 19／12 |
  | S2B4 | I 其餘 | 23 | 15／8 |

- **交件失敗 1 次**：S2B2 漏交 `jgb/G/device-lock-type-and-binding-limit`，但尾行照寫「總 31」。`parse` 以 `missing ids` 大聲失敗，依規則由同一代理重貼一次，重貼後 31 條解析通過。之後的 brief 加上「逐條對照清單」。
- **審核單**：`inputs/review-sheet-9.18-S2-FGHI-20260928.md`，由腳本產生，表頭 commit `af8a86df`。
  - 共 14 組，其中 ⚠️ 6 組：F-repair-apply、F-repair-edit、G-remote-unlock、I-pricing、I-control-panel、I-hicloud-order。
  - `check` ⇒ `targets 118; judged 118; raw-parsed 118; sheet ids 118`、`mismatches: 0`。
  - 正對照（`jgb/I/tcloud-payment-instructions`）：審核單副本、raw 副本各把 doubt 改成 pass，兩處都有報出。
  - 正本與 runs 相對 `af8a86df` 的 `git diff --stat` 為空。
- **值得業主知道的疑點型態**：
  - F 架報修的通知與可見性照幫助中心寫，但現行程式不同：網頁上的「通知及同步租客」開關沒有接上，房東建的單租客看不到；結單只寄 Email。
  - I 架有好幾處「應寄 Email 實際不寄」：取消訂閱的通知名稱拼錯、即將額滿只發站內通知。
  - 首頁「沒資料就不顯示」的判斷用空陣列，永遠成立。
  - **S1 漏掃一個客戶名**：`jgb/I/pricing-trial-plan-landing-page` 寫出「愛租屋」，全正本只有 I.md 1 處。S1 的用詞清單沒有收這個詞，這條已判 doubt、不會被標，改寫併入 9.19。
- **成本**：4 批約 0.90M（含重貼）、S2 就緒審查 ×2 約 0.11M ⇒ 9.18 累計約 1.45M（停點 2.0M）。

### S3（2026-09-28）

- **業主裁決原文**（AskUserQuestion「9.18 S3 終審：F／G／H／I 審核單要怎麼過？」之回覆）：「安全組過 (Recommended)」——非 ⚠️ 8 組的 pass 標已審；⚠️ 6 組全組本批不審；38 條 doubt 全數本批不審；無點名、無照原樣過、無排除。
- **決定檔**：`scratchpad/p918-s3-decision.json`＝`{"reply":"安全組過 (Recommended)","rule":"safe",…皆空}`。
- **derive** ⇒ `approved 58 (both sources equal) by shelf {'F': 12, 'G': 20, 'H': 4, 'I': 22}; expected endpoint increment pm +54, prospect +16`。
- **寫入前確認**：`git diff --stat af8a86df -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆空；備份 `scratchpad/p918-s3-backup/` 以 `diff -r` 比對相同。
- **寫入與匯出**：`write` ⇒ `added 58`；容器重匯出（`canon_sha256` `1df129d7…`）＋`load_canon_or_die` 通過。
- **verify** ⇒ `reviewed backup 250 -> current 308; added lines 58`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
- **終點指標 `已審細目 pm 304／535、prospect 53／121；頁面 pm 79／183、prospect 23／183`**（pm +54、prospect +16，與預期相同；頁面 pm +9、prospect +5）。
- **重生成保留**（scratch，`--expect-reviewed-kept 308 --expect-open-questions 54`）⇒ `已審保留：308 條／丟棄：0 條`，產出與 repo 正本逐位元組相同。
- **單元與 audit**：單元紅燈＝既有 9 條；`make audit` PASS。
- **fresh outcome verifier＝CONFIRMED**（7 項全過，僅一條 P4：可改在空目錄重生成以取得更嚴格的逐位元組證據）。
- **成本**：S3 就緒審查 ×2 約 0.13M、outcome verifier 約 0.12M ⇒ **9.18 累計約 1.7M**（停點 2.0M、上限 2.2M）。

### 附錄：路線選擇實測（2026-09-28，scratch 正本副本 `scratchpad/whatif/`，把未審細目全部加上 reviewed 行後跑 `endpoint_progress.py`）

| 假設 | 已審細目 | 頁面 |
|---|---|---|
| A～E 全審 | pm 423、prospect 83 | pm 106、prospect 32 |
| F～I 全審 | pm 362、prospect 75 | pm 101、prospect 36 |
| 九架全審 | pm 535、prospect 121 | pm 135、prospect 48 |
