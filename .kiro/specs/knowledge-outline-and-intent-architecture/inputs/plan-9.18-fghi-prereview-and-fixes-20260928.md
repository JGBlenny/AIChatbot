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

  覆蓋守門沿用。開跑前預跑：空結果 `check` ⇒ `targets 118 … sheet ids 118`；負對照 `SHELVES=FGH` ⇒ 大聲失敗。
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
- **擁有**：審核單、本計畫 §6、scratchpad 的 p918-s2 檔。⛔ 改正本。
- **預算**：4 批 × 約 0.19M ≈ 0.8M。

### S3 — 業主終審＋寫入已審（pm 最多 +112、prospect 最多 +38）

- 完全照 9.17 S2，工具換成 `p917_s2_approved.py` 的 p918 副本 `scratchpad/p918_s3_approved.py`。變更值：
  - SHEET／RESULTS／TARGETS 指向 p918-s2
  - PLAN 指向本計畫、§6 段名「### S3」
  - `WRITE_SHELVES="FGHI"`
  - verify 的「不得變動架」改為 A～E
- 開工前預跑三種回覆與正負對照（同 9.17 S2「已預跑」）。
- 業主回覆的形式、四欄決定檔、兩來源推導、備份 `scratchpad/p918-s3-backup/`、寫入、重匯出、驗收、停止（寫入前的失敗不還原；寫入後的失敗用已驗證的備份還原）、回滾，**逐條同 9.17 S2**。既有已審的基準改為「S1 完成後的實數」。
- **預算**：outcome verifier 約 0.15M。

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

### 附錄：路線選擇實測（2026-09-28，scratch 正本副本 `scratchpad/whatif/`，把未審細目全部加上 reviewed 行後跑 `endpoint_progress.py`）

| 假設 | 已審細目 | 頁面 |
|---|---|---|
| A～E 全審 | pm 423、prospect 83 | pm 106、prospect 32 |
| F～I 全審 | pm 362、prospect 75 | pm 101、prospect 36 |
| 九架全審 | pm 535、prospect 121 | pm 135、prospect 48 |
