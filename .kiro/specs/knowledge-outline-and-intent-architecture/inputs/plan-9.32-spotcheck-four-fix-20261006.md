<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「核可，同意本計畫 +0 (Recommended)」
-->
# Plan 9.32：Plan 9.31 抽查不成立的 4 句依 D1 修正（2026-10-06）

> **現況**（2026-10-06，HEAD `fb9732cf`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`；正本 543 條全審。
>
> **本計畫的進度單位**：Plan 9.31 抽查判「不成立」的 4 句——**已處置 0／4 → 4／4**。每句去向四選一：改寫寫入／整句刪寫入／業主裁定保留原文／寫入核對推翻後保留原文並轉下份計畫。
>
> **已審細目數 +0**：4 條細目改內容後，寫入前暫時失去已審，寫入後回復。`consent_zero` 已填入業主 2026-10-06 核可原文（見 §6）。

## 0. 依據

- 業主 2026-10-06：「照這個順序走」——對主 session 建議的順序「1. 先修抽查不成立的 4 句；2. 第 1 項覆蓋盤點並凍結補內容清單；3. 第一次真實題量測」。本計畫＝第 1 步。
- Plan 9.31 §6 與抽查單 `inputs/spotcheck-30-9.31-20261006.md`：4 句由獨立代理判不成立、業主逐句裁定「不成立 (Recommended)」；判定證據 `verification/20261006-p931-spotcheck-judgment.json`。
- ⚠️ Plan 9.31 §6 把 #2 記成「句 4」、#5 記成「句 2」是錯的（9.31 核對代理 P3）。正確對應以下表為準：正本 `content_units` 句序與 drafts 句序，由主 session 以「正本句去標點後是哪一個 drafts 句的子字串」機械對出（4 句皆唯一對到）。

| 抽查單 # | 細目 | 正本句序（0 起） | drafts 句序（0 起） | 不成立理由（代理原文摘要，業主裁定） |
|---|---|---|---|---|
| 2 | `jgb/A/notification-settings-extra-emails` | 2 | 2 | 「每個分類卡片都可各自新增／移除」漏權限例外（`edit_notification`）；同條 drafts 句 3 已寫需編輯權限 ⇒ 同條自相矛盾 |
| 5 | `jgb/D/contract-list-row-gear-actions` | 0 | 0 | 「依狀態、身分、權限決定」屬排他列舉；程式另依社會住宅合約、租客是否註冊、可否續約、特定合作團隊簽核狀態增減或停用 |
| 14 | `jgb/E/recharge-account-history-content` | 0 | 0 | 「列出每一筆」不成立：畫面只取第一頁，後端預設每頁 50 筆、新到舊 ⇒ 最多顯示最近 50 筆；標題「每筆金額變動」同一問題 |
| 26 | `jgb/D/contract-invite-and-review-period` | 0 | 0 | 「給租客一段審閱期才能簽約」讀成須等滿才能簽；程式裡是邀請失效期限、期限內隨時可簽（同條 drafts 句 2 已寫逾期失效）；後半句（天數讀團隊設定、未設定 3 天）成立 |

## 1. 流程（一個切片，一次 commit）

**1. 步驟 0 基準**：記錄 HEAD；`make audit`；他線未提交檔指紋（含正對照 `runtime.py`）；全套 unit 紅燈基準；備份 HANDOFF。

**2. 起草**（主 session；4 句規模小，不另派 executor，獨立性由步驟 4 的 fresh 先審提供）
- 依 D1「修整條」（Plan 9.21 §1）：每個不成立句只修一次——改寫成程式實際行為（每個斷言附逐字引文＋檔案路徑），或確立不了就整句刪；同條其他句、標題、講法若因此矛盾，一併處置並在依據欄標「整條 #m」；⛔ 改別條細目。
- 00c 規則照舊：引文逐字命中 jgb2 釘住匯出 `b2ee2ac382ce`；否定句附實跑 grep 與正對照；標題、句子、講法 ⛔ 程式識別字與 `/` 路徑；客戶名寫「特定合作團隊」。
- 已知要一併檢查的：#14 標題「每筆金額變動」（同一個 50 筆問題）。
- **#26「團隊可調整」措辭**（出處：Plan 9.29 §6 W3 紀錄「審閱天數「團隊可調整」實為內部後台按團隊設定、業者端無設定畫面（措辭待業主另裁）」；另見 `verification/20261005-p929-W3-write.json` findings、`verification/20261004-p928-B13.json` notes。⚠️ 不在 HANDOFF 與 56 則正式待裁內）：涉及 #26 標題「天數為團隊可調整設定」與 drafts 句 1「這個審閱天數設定屬於團隊層級，不同團隊可以各自覆蓋預設值」。**處理：業主於核可本計畫時一併裁定這段措辭**，起草照裁定寫；業主若裁「保留原措辭」，這兩處不改、記入修正紀錄「## 整條待裁」節。
- **碰到其他待裁的通則**（D1 原規則，HANDOFF §12-2 D1 段、Plan 9.21 §1「整條待裁」）：起草或先審若發現某處修正必須替業主待裁事項選邊，⛔ 主 session 或任何代理自行改寫或刪除；該處記入修正紀錄「## 整條待裁」節，列入終審單交業主裁，去向記「業主裁定」。
- 輸出 `edit_fine.py` 既有 ops（`title`／`set`／`delete`／`phrasings`／`evidence_add`／`add_sources`）與逐項依據；允許集合＝上表 4 條。
- 機械檢查（沿用 9.30 scratch `check930.py` 的檢查項，改為吃既有 ops）：ops 細目 ⊆ 允許集合；evidence 逐字命中；識別字／路徑／客戶名（分與不分大小寫）掃描；講法 NFKC 不撞全庫；套到 scratch drafts 後 `drafts_diff`（`P919_DIFF_SHELVES=ABCDEFGI`）(b)(c)(f) PASS；scratch 重生成（`--expect-reviewed-kept 539 --expect-open-questions 56`）、`canon_check` 區塊差異只在允許集合、不變量 34 交集為空、H 留出題守護 PASS。

**3. 修正紀錄** `inputs/fix-log-9.32-20261006.md`：以 `drafts_diff.py --list` 機械產生（scratch `p930/gen_fixlog.py`）；判定欄取步驟 4（含複核、整條複查）最終結論。產生時機同 Plan 9.30：先審後對全部 ops 產生一版；步驟 6 只套業主核可者後重新產生；寫入核對推翻而移出某條時先在 drafts 還原該條再重新產生。每一版 `drafts_diff --fix-log` 須 PASS。修正紀錄另含「## 整條待裁」節（列出不改的待裁處、理由與出處；沒有就寫「無」），終審單有對應一節。

**4. 先審**：一位 fresh verifier 逐句核對 4 條細目的**全部**句子與標題（不只被修的句），混 1 條誘餌（9.28 誘餌表未用過的一項）；判準同 Plan 9.30 先審（排他列舉、漏例外、同粗目矛盾、引號內字須為現行畫面文字）。不成立的句子依 D1 修一次 ⇒ 複核；仍不成立 ⇒ 整句刪；刪到無句或標題答不到 ⇒ 交業主（保留原文轉下份計畫）。**例外**：先審判不成立的理由落在業主待裁事項（含業主核可時未裁或裁「保留」的 #26「團隊可調整」措辭）⇒ ⛔ 走 D1 修改，改為停下列入終審單交業主裁定，去向記「業主裁定」。有刪句的細目再由一位 fresh verifier 整條複查。誘餌漏抓 ⇒ 該次先審作廢、換人一次。

**5. 業主終審**（固定停點）：終審單 `inputs/review-sheet-9.32-20261006.md`（每條新舊全文、先審結論、依據）。未核可的細目不套用、保留原文與已審。

**6. 寫入**（一個 commit；步驟同 Plan 9.30 §1 步驟 6）
1. 組基準快照與 HEAD `diff -r` 相同。
2. 對 repo drafts 只套業主核可的 ops；重新產生修正紀錄；`drafts_diff --fix-log` PASS。
3. 生成器 scratch 試跑與 repo 執行 `diff -r` 相同；`canon_check` 區塊差異只在核可集合、exit 0。
4. 加已審前快照。
5. `approve_write write` → 容器重匯出 → `load_canon_or_die` → `approve_write verify --backup <加已審前快照>`（`mismatches: 0`）。
6. 終點指標回到 pm 537／537、prospect 121／121；H 守護 PASS。
7. 全套 unit 與基準差集為 ∅。
8. 寫入核對：一位 fresh verifier 逐句核對全部寫入細目，`kind: write`，誘餌放 `control`。推翻 ⇒ 主 session 先對碼找反證；反證不成立 ⇒ 依業主 2026-10-05 規則移出寫入集合、保留原文轉下份計畫，其餘重寫，證據由同一位核對代理重貼；反證成立 ⇒ 交回同一位代理重判（Plan 9.30 先例）。
9. `--extract` ⇒ `make audit` OVERALL PASS ⇒ commit（`Verified-by` 指向寫入證據）。

**7. 收尾**：一位 fresh outcome verifier（BRIEF-CONTRACT v1）對照驗收清單逐條驗收；更新 HANDOFF（開頭現況、§12-1 加 9.31、9.32 兩列）。

- **commit 範圍**：本計畫、驗收清單、修正紀錄、終審單、先審／複查／寫入證據、被改動架的 drafts 與 runs 產出、正本被改動架的 `.md`、`CATALOG.md`、`jgb.json`、HANDOFF。⛔ `git add -A`、⛔ `--amend`；push 由業主自跑。
- **還原**：步驟 6 開始到 commit 前任何停下 ⇒ 以組基準快照還原 `rag-orchestrator/canon` 與 `runs/outline-20260920`，`git diff HEAD` 對這兩處為空、`load_canon_or_die` 通過 ⇒ 記 §6 ⇒ 停下交業主。

## 2. 不做（後續計畫）

- 規格 §2.1 覆蓋盤點與凍結補內容清單（業主同意的順序第 2 步，下一份計畫）。
- 規格 §2.4 第一次真實題量測（第 3 步）。
- 9.24 以來整句刪掉的正確資訊重新起草；9.30 終審單 §3 附帶觀察；9.31 代理 findings 9 則（幫助中心過時等）。
- 4 條以外細目的任何修正（即使起草時發現同粗目他條有錯，只記觀察）。
- 重新抽查 30 句（規格 §2.2 的再驗方式待第 1、4 項後另定）。

## 3. 業主裁決與待裁

- **已裁**：「照這個順序走」。
- **待裁（核可時回覆）**：本計畫，並明示同意 +0；以及 #26「團隊可調整」措辭怎麼處理（見 §1 步驟 2）。
- **待裁（終審時）**：4 條新版本。

## 4. 停止條件與額度

- 允許集合外的 drafts 或正本有任何改動 ⇒ 停、還原。
- 先審誘餌漏抓 ⇒ 該次作廢、換人一次；再漏 ⇒ 停。
- 寫入後已審細目數 ≠ pm 537／537、prospect 121／121 ⇒ 停、還原。
- **額度**：就緒審查約 0.15M、先審約 0.25M、（如需）複查約 0.1M、寫入核對約 0.25M、收尾約 0.2M，共約 0.95M；累計超過 1.4M ⇒ 停下回報。
- **執行模式**：沿用本線 ASK；業主終審是固定停點。

## 5. 就緒審查紀錄

- **第 1 輪**（fresh plan-verifier，2026-10-06）：REVISE，P2×1（substantive）——#26「團隊可調整」措辭的出處寫成 HANDOFF 但查不到（實際在 Plan 9.29 §6 W3 紀錄），且未寫先審判該措辭不成立時的去向；照原文執行會在步驟 4 以 D1 改寫或刪除該措辭，與「⛔ 替待裁選邊」衝突。**FIX**：出處改為 Plan 9.29 §6 W3 並附兩份證據檔；改採審查建議 (b)——業主核可本計畫時一併裁定該措辭，並保留 (a) 作後備（未裁或裁保留 ⇒ 不改、記「整條待裁」）；步驟 2 加「碰到其他待裁的通則」、步驟 4 加例外去向「停下交業主」；修正紀錄與終審單加「整條待裁」節。送收尾審查。
- **收尾審查**（fresh plan-verifier，2026-10-06）：**READY** ⇒ 交業主核可（`next_gate: user_approval`）。執行時注意：修正紀錄的「## 整條待裁」節一律用條列（`- …`），⛔ 用表格列，以免被 `drafts_diff.py` 的 `_ROW` 當成改動列解析。

## 6. 執行紀錄

- **業主核可**（2026-10-06，AskUserQuestion 逐字）：「核可，同意本計畫 +0 (Recommended)」（已填入 consent_zero）。
- **業主裁定 #26 措辭**（同時回覆，逐字）：「改成「由 JGB 依團隊設定」 (Recommended)」——對選項說明「標題與內文改寫成：天數依團隊設定、由 JGB 設定，業者端沒有設定畫面；要調整請洽 JGB 客服的說法，需有程式或文件依據才寫」。
- **步驟 0**（HEAD `fb9732cf`）：`make audit` OVERALL PASS；他線 41 檔指紋不變（含正對照 `runtime.py`）；HANDOFF 備份 scratch `p932/backup/`；全套 unit `9 failed, 3946 passed, 3 skipped`，紅燈 9 條與 9.30 基準逐名相同（scratch `p932/red-base.txt`）。
- **步驟 2 起草**（主 session；ops 存 scratch `p932/draft/ops.json`）：
  - #2 `notification-settings-extra-emails` drafts 句 2 改寫：改成「有通知設定的編輯權限時，每個通知分類卡片內可以各自新增或移除…」，與同條句 3（需編輯權限）一致；引文 `state.hasPermissionToEdit` 的 v-if 與 `edit_notification` 權限來源。
  - #5 `contract-list-row-gear-actions` drafts 句 0 改寫為非排他：「要看多項條件，包括這份合約目前的狀態、登入身分、權限，以及是否為社會住宅合約等」；標題同步改為「依合約狀態、身分、權限等條件增減」（整條 #標題，同一排他問題）；引文 5 筆（`switch ($LVcontractDataPage->status)`、租客身分判斷、權限判斷、社宅判斷、`canMoveIn() ? '' : 'disabled'`）。
  - #14 `recharge-account-history-content` drafts 句 0 改寫為「由新到舊、最多顯示最近 50 筆」；標題同步改為「最近 50 筆金額變動…」（整條 #標題）；引文：後端 `per_page` 預設 50、`orderBy('id', 'desc')`，前端呼叫不帶參數的網址。
  - #26 `contract-invite-and-review-period` drafts 句 0 改寫為「租客要在審閱期限內完成簽約；期限天數依團隊設定，沒有設定時預設 3 天（72 小時）」；依業主裁定改 drafts 句 1 為「審閱天數是 JGB 在後台依團隊設定的值，沒有特別設定的團隊一律用預設的 3 天」、標題括號改為「天數由 JGB 依團隊設定」；引文：`contract_inviting_expire_at` 計算、後台功能配置路由（`Admin\FeatureConfigController@index`）、該功能配置 migration 說明、`getSettings(... 'review_days' ?? 3)`。⚠️ 業主裁定選項說明另提「業者端沒有設定畫面」：那是否定句，00c 要求附實跑 grep 於 `not_supported_greps`，而本計畫核可的 ops 集合不含可寫入否定 grep 的操作 ⇒ 未寫入此否定子句，改以「JGB 在後台依團隊設定」表達；終審單列出供業主決定是否另案補上。
  - 講法 4 條皆未改。
  - 機械檢查：新增引文 14 筆逐字命中 jgb2 釘住匯出；改動的標題 3、句子 5 識別字／路徑／客戶名（不分大小寫）掃描 0；套到 scratch drafts 後 `drafts_diff` (b)(c)(f) 0、RESULT PASS（改動項 8）；scratch 重生成 `已審保留 539`、open_questions 56；`canon_check` 區塊差異 4／允許 4、客戶名 0；不變量 34 交集為空；H 留出題守護 PASS（新命中 0）。
- **步驟 4 先審**（fresh verifier，約 0.19M；誘餌＝9.28 誘餌表第 0 項，位置種子 20261032）：證據 `verification/20261006-p932-prereview.json`（`--extract`，base `fb9732cf`）：5 條＝4 條＋誘餌、sha 與 scratch 正本相同；**誘餌在句 3 判不成立並引來源（`account.blade.php` 的 Facebook `maxlength="200"`）⇒ 有效**。4 條的標題全成立；#2、#14、#26 全部句子成立；**#5 `contract-list-row-gear-actions` 正本句 6（drafts 句 5，未改動的原句）判不成立**：列「執行中合約」各階段的選項時漏了「提前解約」（非社宅合約的租客一律看得到；非租客有 `edit_owner_contract` 或 `sign_contract` 權限時也看得到）。主 session 對碼確認：`ContractController.php` 該 case 末段兩個分支都 push `$LVreturnActionTemplate['terminate']`（文字 `___('提前解約')`），class_name 依 `canEarlyTermination()`。未找到反證。
  - **D1 修一次**：drafts 句 5 句尾補「另外，非社宅用途的合約在這些階段也會顯示「提前解約」：租客身分一律看得到，非租客身分要有合約編輯或簽約權限才看得到；能不能點選要看合約目前是否可以提前解約。」；新增引文 3 筆逐字命中；識別字掃描 0；重套 scratch 後 `drafts_diff` PASS（改動項 9）、重生成保留 539、`canon_check` 4／4、H 守護與不變量 34 PASS。
  - **複核**（fresh verifier，約 0.15M；整條複核 #5；誘餌＝第 1 項，位置種子 20261033）：證據 `verification/20261006-p932-recheck.json`：#5 標題與正本 9 句全成立、sha 與 scratch 正本相同；誘餌在句 3 判不成立並引來源（`目前密碼驗證錯誤`）⇒ 有效。無刪句 ⇒ 不需整條複查。
- **修正紀錄第 1 版** `inputs/fix-log-9.32-20261006.md`（`gen_fixlog.py`，9 列、4 條、刪除 0，另附「## 整條待裁」節＝無）：`drafts_diff --fix-log` (a) 未記 0／多記 0、(d) 相等、(e) 0、RESULT PASS。
- **終審單** `inputs/review-sheet-9.32-20261006.md`：4 條改動前後對照、#26 業主裁定的落實與未寫的否定子句（附查證：jgb2 `src/` 對 `contract_review_renew_period`／`review_days` 0 命中，`app/Http/Controllers/ContractController.php` 有命中）、附帶觀察 2 則。
- **用量**：就緒審查 2 輪約 0.17M、先審 0.19M、複核 0.15M ⇒ 累計約 0.51M（停止線 1.4M）。
- **停點**：交業主終審。
- **業主終審**（2026-10-06，AskUserQuestion 逐字）：「核可全部 4 條 (Recommended)」⇒ 寫入集合＝4 條。
- **步驟 6.1～6.6**：
  - 6.1 組基準快照 scratch `p932/W-base/`（HEAD `fb9732cf`）與 repo `diff -r` 相同。
  - 6.2 對 repo drafts 套 4 條核可 ops，結果與 scratch 套用版 `diff -r` 相同；修正紀錄依實際套用重新產生（9 列、刪除 0、整條待裁＝無），`drafts_diff --fix-log` (a)～(g) 全過；八架 `--roundtrip` 位元組不變。
  - 6.3 生成器（`--expect-reviewed-kept 539 --expect-open-questions 56`、日期標 `20261006-w-932`）scratch 試跑與 repo 執行 `diff -r` 相同，runs 三檔複製回 repo 並 `cmp`；`reviewed-dropped` 4 筆皆 `content_changed`、集合＝寫入集合；`canon_check --remove`（空清單）區塊差異 4／允許 4、mismatches 0、客戶名 0。⚠️ 事故（無影響）：第一次以 zsh 變數組指令，變數未拆字、生成器未執行，只對未改動正本跑了兩次重匯出；主 session 立刻以 `diff -r` 確認 repo 正本與組基準快照相同、`git status` 0 筆，改用 bash 腳本 scratch `p932/gen.sh` 重跑。
  - 6.4 加已審前快照 scratch `p932/W-pre-approve/` `diff -r` 相同。
  - 6.5 `approve_write write`（`P918_WRITE_SHELVES=ADE`、2026-10-06）added 4 → 容器重匯出 → `load_canon_or_die` 通過 → `verify --backup W-pre-approve`：`reviewed backup 539 -> current 543`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
  - 6.6 終點指標 `已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`；H 留出題守護 PASS。
  - 6.7 全套 unit `9 failed, 3946 passed, 3 skipped`，紅燈與基準差集＝∅（雙向）。
- **步驟 6.8 寫入核對**（fresh verifier，約 0.19M；對照細目＝9.28 誘餌表第 4 項，結果寫 `control`）：證據 `verification/20261006-p932-write.json`（`--extract`，base `fb9732cf`）：**CONFIRMED**、4 條＝寫入集合、每條 `content_sha256`／`title_text`／句數與工作樹正本相同、全條成立（23 句）；control `jgb/A/password-last-updated` 誘餌句（句 4）判不成立並引來源 ⇒ 量尺有效。`outline_plan_discipline.py`（不變量 43，含工作樹 W）PASS。代理 findings 3 則（事實帳本 `p914-contract-invite-account-match`「換裝置不會自動綁定」說得太滿——註冊時另有以 Email／手機認領；內部建約 API 固定 72 小時；「點退押金」能否點另需點退權限），皆不影響判定，列入後續觀察。
- **C1 去向對帳**：4 句＝改寫寫入 4（#2、#5、#14、#26）；另 #5 先審新抓到的句 6 依 D1 修一次寫入；整句刪 0、業主裁定保留 0、寫入核對推翻 0。
- **C7 客戶名掃描**（`canon_check.py` 的 `PAT`；正對照合成客戶名命中、負對照「系統上」不中）：分大小寫——正本 0（`canon_check` 輸出）；不分大小寫——本計畫新增或修改的 `.kiro` 檔（計畫、驗收清單、修正紀錄、終審單、先審／複核／寫入證據）0；drafts 改動 4 條整條（含 evidence）0；HANDOFF 2 處為開工前即有（與 9.30 收尾時相同）。
- **用量**：就緒審查 0.17M、先審 0.19M、複核 0.15M、寫入核對 0.19M ⇒ 累計約 0.70M（停止線 1.4M；收尾約 0.2M）。
- **步驟 6.9 commit**：`make audit` OVERALL PASS；他線 41 檔指紋不變；commit `b4d4d846`（19 檔，範圍外 0；commit hook 不變量 43 通過）。
- **步驟 7 收尾驗證第 1 次**（fresh outcome verifier，BRIEF-CONTRACT v1，約 0.18M）：**REFUTED**，P2×1——C2「同條其他句、標題、講法的連帶處置在修正紀錄標『整條 #m』」未做到：修正紀錄 9 列依據欄皆為同一句、無「整條 #m」與依據節，連帶處置只寫在 §6 散文（`grep -c "整條 #"`＝0）。C1、C3（含自行回源 4 條）、C4～C7、C8 unit、C9、C10 獨立通過；H 守護、`make audit`、他線逐檔指紋未重跑（權限）。另 P4：新增 runs `open-questions-20261006-w-932.md` 帶生成器沿用的既有客戶名 1 處（不在 C7 範圍）。證據 `verification/20261007-p932-closeout-refuted.json`。
  - **處置**：P2 為本計畫引入、在 C2 範圍內 ⇒ **FIX**——修正紀錄依 Plan 9.21 格式重寫依據欄（`依據 #n`／`整條 #m`／`先審 #m`／`業主裁定`）並補「## 依據」「## 整條依據」「## 先審新抓到」節；`drafts_diff --fix-log` 仍 RESULT PASS（9 列、(a)～(g) 全過）、`grep -c "整條 #"`＝5。主 session 在主機重跑 H 留出題守護 PASS。P4 **DEFER**（既有文字、另案）。修正屬 claim 相關 ⇒ 另派一位 fresh verifier 重驗後另開 commit。
- **收尾重驗**（fresh outcome verifier，BRIEF-CONTRACT v1，約 0.15M）：**CONFIRMED**——C2 修好（9 列依據逐列對上實際改動與證據檔、`grep -c "整條 #"`＝5、`drafts_diff --fix-log` RESULT PASS；負對照刪 1 列 ⇒ FAIL）；C1、C3（自行回源 #14 句 0）、C5、C7、C9、C10 親自重跑通過；工作樹相對 `b4d4d846` 的本線改動只有修正紀錄、計畫 §6 與證據檔。證據 `verification/20261007-p932-closeout-change.json`（base `b4d4d846`）。非阻擋 P4：H 守護與 `make audit` 未由代理重跑（權限）⇒ 主 session commit 前在最終工作樹重跑（見下行）；他線逐檔指紋代理缺基準 ⇒ 主 session 以步驟 0 指紋檔（scratch `p930/foreign-fp.txt`）重比；「整條 #m」的 m 定義與 9.21 不同但檔頭已說明（不改）。
- **用量合計**：約 1.03M（停止線 1.4M 內）。
- **計畫完成**：4／4 已處置（改寫寫入 4，另修先審新抓到 1 句）；終點指標 pm 537／537、prospect 121／121。
- **commit 前重跑**（最終工作樹）：`make audit` OVERALL PASS（含不變量 43、44）；H 留出題守護 PASS；他線 41 檔以 scratch `p930/foreign-fp.txt` 逐檔比對全部 OK。
