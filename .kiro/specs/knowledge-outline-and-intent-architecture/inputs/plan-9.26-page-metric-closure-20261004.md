<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「同意」
-->
# Plan 9.26：改量尺——頁面覆蓋改認「入口檔＋其子元件／子路由閉包」（+0）

> **現況**（`endpoint_progress.py`，2026-10-04，HEAD `60cc55df`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 142／183、prospect 53／183`。
>
> **本計畫預期**：已審細目 **+0**（不動正本；`consent_zero` 為業主原文「同意」）。**頁面指標改量法後 pm 142→177、prospect 53→82**（預跑實測，§6）。剩 pm 6 頁未覆蓋（§0）。
>
> **驗收清單（凍結）**：`.kiro/specs/knowledge-outline-and-intent-architecture/acceptance-9.26-20261004.md`。

## 0. 為什麼有這份

- 業主 2026-10-04「同意」——對建議「下一份做『改量尺』：讓頁面指標把同一頁目錄底下子元件的引用也算進去。這不動正本，是 +0 計畫，需要您明示同意，也等於推翻您先前『量尺先不動』的裁示」；理由三點：量尺把「內容已寫、只引用子元件」的頁算成缺口，9.25 為此多跑兩輪審查；改量尺比替約 10 條已審細目補引用便宜且不動已審內容；改完才看得出真缺口。
- **與建議用語的差異（請業主核可）**：建議原話是「同一頁**目錄**底下子元件」，實作改為「入口檔的 **import 閉包＋子路由**（只收 `src/pages/` 底下的檔）」。理由：照目錄比會讓同目錄的兄弟頁互相點亮（`users/auth/` 下的 `Forget.vue`／`Login.vue`／`Verify.vue` 是不同頁），而入口檔實際渲染的子元件不一定在同目錄（`users.forget` 的畫面在 `parts/forget/*.vue`，由子路由經 router-view 渲染）。閉包只算「這頁真的會載入」的檔，比目錄準。
- 量尺現況（`endpoint_progress.py` `page_hit`）：SPA 頁只認細目 `sources` 逐字等於 `code:src/pages/<入口檔>`；blade 頁以 controller 檔比對，但 `NotificationController.php#index` 這類 `#方法` 後綴比不到。

## 1. 切片：只有 S1（程式＋測試＋閉包產物＋文件，一次 commit）

- **步驟 0（第一次改 repo 檔之前；結果記 §6）**：記下 HEAD 全碼；`make audit` 基準（預期 OVERALL PASS）；他線未 commit 檔（`git status --porcelain -z --untracked-files=all`，扣除本計畫、驗收清單、附件）的 sha256 指紋寫入 `scratchpad/p926/foreign-fp.txt`，正對照 `rag-orchestrator/services/agent/runtime.py` 須在清單內；備份 `scratchpad/p926-backup/`：`.claude/` 與 `.agents/` 兩份 `endpoint_progress.py`、`rag-orchestrator/tests/unit/skills/outline_curation/test_endpoint_progress_req.py`、HANDOFF，逐檔 `cmp` 與 repo 相同。

- **新腳本** `.claude/skills/outline-curation/scripts/page_import_closure.py`（＋`.agents/` 鏡像，`cmp` 相同）：從 jgb2 **釘住 commit 的匯出**（`b2ee2ac382ce`）對每個 in_baseline SPA 頁入口檔做靜態閉包——`import … from '…'`／`import('…')`（解析 `@src/` 與相對路徑、副檔名與 `index`／`Index`）＋ `src/routes/*.js` 的子路由（以大括號與 `children:` 追蹤巢狀，同檔 `const X = [ … ]` 的 `...X` 展開就地內嵌；⛔ 以路由名稱前綴猜）；**只收 `src/pages/` 底下的檔**（⛔ `src/components` 等共用元件）。前置拿不到（匯出無 `src/pages`、入口檔不存在、SPA 頁 0）⇒ 非 0。原型在 `scratchpad/p926/page_import_closure.py`（已預跑）。
- **閉包產物** `.claude/skills/outline-curation/runs/outline-20260920/page-import-closure.json`（`{"sha": "b2ee2ac382ce", "pages": {…}}`，141 個 SPA 入口）。
- **改 `endpoint_progress.py`**（＋鏡像）：
  - `code_paths` 去掉 `#…` 後綴；
  - `page_hit(unit, paths, closure=None)`：SPA 頁命中＝閉包內任一檔被引用（不給閉包時只比入口檔，即舊量尺；**給了閉包但該頁不在閉包內 ⇒ 大聲失敗**，⛔ 靜默退回）；
  - 新參數 `--closure <json>`（不存在或 `pages` 空 ⇒ 大聲失敗）；headline 格式不變。
- **測試**：
  - `tests/unit/skills/outline_curation/test_endpoint_progress_req.py` 加：閉包命中子元件、無閉包時子元件不命中（舊行為）、`#方法` 去除後 blade 命中、`--closure` 檔不存在／空 ⇒ SystemExit；既有 5 條不改。
  - 新檔 `tests/unit/skills/outline_curation/test_page_import_closure_req.py`：合成匯出（import 鏈、`@src` 與相對路徑、子路由 children、`...X` 展開、`src/components` 不收、兄弟頁不互入、入口檔不存在 ⇒ SystemExit）。
  - 變異檢查（在 scratch 副本上改、掛載覆蓋執行，repo 檔 `cmp` 不變）：把 `page_hit` 的閉包分支改回只比入口檔 ⇒ 新測試變紅；把 `route_children` 停用 ⇒ 子路由測試變紅。
- **文件**：HANDOFF 開頭終點指標跑法加 `--closure …/page-import-closure.json` 並改現值；§12-4「頁面量尺待辦」改寫為新量尺下剩餘 6 頁；附件 `inputs/page-coverage-closure-9.26-20261004.md`（新增覆蓋 35 頁逐頁列命中細目與檔，供業主抽查）。
- **驗證與 commit**：全套 unit 與 9 條基準差集 ∅（新增測試全綠）；`make audit` OVERALL PASS；他線指紋 `shasum -a 256 -c scratchpad/p926/foreign-fp.txt` 全 OK；fresh outcome verifier（`kind: change`，brief 中文、BRIEF-CONTRACT v1，含驗收清單 A1～A4）；`--extract` ⇒ `verification/20261004-p926-change.json` ⇒ commit（`Verified-by`）。
- **commit 範圍**：上述 2 支腳本＋2 個鏡像、閉包 JSON、2 個測試檔、HANDOFF、本計畫、驗收清單、附件、證據檔（`git diff --cached --name-only` 核對；⛔ `git add -A`）。
- **還原**：commit 前任何停下 ⇒ 由 `scratchpad/p926-backup/`（⛔ `git checkout`）還原被改的既有檔（`endpoint_progress.py` 兩份、測試檔、HANDOFF）並刪除新增檔，`git status` 對上述路徑為空 ⇒ 停、交業主。commit 後驗收 FAIL ⇒ ⛔ 改寫歷史、回報業主。

## 2. 不做（另案）

- **新量尺下剩餘 pm 6 頁**：`indexs` 與 `/help`（blade 外殼，內容在 SPA，閉包只對 SPA 頁算）；`bills.sheet`（業主 G3 排除，仍在分母）；社宅 `landlordBasic`／`photos`／`subsidyTerms`（對應細目沒有引用這些分頁的程式檔：`social-housing-photos-tab`、`social-housing-subsidy-terms-tab` 無 `code:` 來源，`social-housing-landlord-tabs-overview` 只引 `useEditStore.js`）——要覆蓋須改已審細目來源並重驗，待業主裁。
- prospect 可見頁範圍（新量尺下 prospect 82／183，業主「另議」）。
- 已審存量補做寫入後全數核對（業主「先不排」）。

## 3. 業主裁決與待裁

- **已裁**：§0「同意」（+0、推翻「量尺先不動」）。
- **待裁（核可時一併回覆）**：(a) 本計畫；(b) 「目錄」改「import 閉包＋子路由」的實作差異；(c) 閉包是代理指標——跨功能共用子元件會點亮頁（例：差額發票編輯頁經物件搜尋區塊命中），外框父路由會被任一子孫路由的引用點亮（例：`users.index` 63 條、`bills.index` 25 條），附件 35 頁請抽查是否接受。

## 4. 停止條件

- 正本、drafts 任何變動 ⇒ 停（本計畫 ⛔ 動正本）。
- 新增測試未綠、變異檢查未咬、單元差集非 ∅、`make audit` 非 PASS ⇒ 依 §1 還原並停。
- 一次只跑一個代理；代理 brief 帶 HANDOFF §12-2 必禁清單。

## 5. 就緒審查紀錄

- **第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-04）：P2×1——§1 沒有開工前基準步驟（HEAD、`make audit` 基準、他線指紋、`p926-backup/` 備份），驗收 A4 的「開工前指紋」無比對對象、還原路徑無來源。處置：**FIX**——§1 新增步驟 0（第一次改檔前執行、結果記 §6），驗證與 commit 段加指紋 `shasum -c`。送第 2 輪。
- **第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-04）：P2×1——凍結驗收 A1 未逐字引業主原話（拿掉「同一頁目錄底下」），清單內也沒記「目錄→import 閉包＋子路由」的差異與前提，verifier 拿原話對照實作會判不過。附 P3×4：給了閉包但頁不在閉包內時靜默退回舊量法、A3 未寫匯出重建方式、變異檢查未寫在哪改與怎麼還原、§3(c) 漏「父路由被子孫點亮」。⇒ **第二次自動 REVISE，停止重送、逐條處置**：P2 **FIX**——A1 改逐字引用，清單新增「實作差異」節（含理由與「以業主核可 §3(b) 為前提、不核可則 A1 重寫」）；P3×4 皆 **FIX**（頁不在閉包 ⇒ 大聲失敗、A3 寫明以 `review_pipeline/README.md` 的 `git -C …/jgb2/dev1 archive b2ee2ac382ce | tar -x` 重建匯出、變異在 scratch 副本上做且 repo 檔 `cmp` 不變、§3(c) 補父路由）。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **收尾審查（fresh plan-verifier）＝REVISE**（2026-10-04）：第 2 輪處置與 P3×4 皆確認到位；剩 P2×1——驗收 A1 要求附件每列命中檔都在閉包 JSON 內，但 blade 列 `notifications.index` 的命中檔是 `NotificationController.php`，依設計不在閉包內 ⇒ 必判不過。處置：**FIX**（主 session 已改）——A1 分寫 SPA 列（查閉包 JSON＋`sources`）與 blade 列（查去 `#方法` 的 `sources`，不查閉包），附件說明同步。**依審查上限暫停，交業主裁**：核可（含此修正、不再自動審）或要求再審一次。

## 6. 執行紀錄

### 立案前預跑（2026-10-04，HEAD `60cc55df`；repo 未動）

- 閉包原型 `scratchpad/p926/page_import_closure.py` 對釘住匯出 ⇒ `spa components 141; files per page min 1 median 4 max 67`。樣本：`users/auth/Forget.vue` 5 檔（含 `parts/forget/Account.vue`、`Password.vue`、`parts/VerifyPanel.vue`）；`contracts/edit/Index.vue` 55 檔（含各分頁；原先未展開 `...contractRoutes__edit` 時只有 3 檔，已修）。
- 量尺原型 `scratchpad/p926/scripts/endpoint_progress.py`（掛容器 `/p`）：無 `--closure` ⇒ `已審細目 pm 537／537、prospect 121／121；頁面 pm 143／183、prospect 53／183`（＋1＝`notifications.index`，`#方法` 去除）；有 `--closure` ⇒ `頁面 pm 177／183、prospect 82／183`；`--ignore-review --closure` ⇒ `頁面 不分身分 177／183；pm 177、prospect 82`。
- 新增覆蓋 35 頁與命中細目／檔：附件 `inputs/page-coverage-closure-9.26-20261004.md`；未覆蓋 6 頁見 §2。

### S1（2026-10-04）

- **業主裁決原文**（2026-10-04，對「Plan 9.26 收尾審查只剩 1 個驗收措辭問題（已修），依上限不再自動重審。怎麼進行？」）：「核可（含此修正） (Recommended)」——核可本計畫、§3 (b)「目錄→import 閉包＋子路由」差異、(c) 附件 35 頁，以及收尾審查後的 A1 分寫修正；不再自動重審。
- **步驟 0**：HEAD `60cc55df326dd91bcdbb78241877aa04c37e2c9d`；`make audit` 基準 `OVERALL: PASS（2026-10-04）`；他線未 commit 檔 41 個 sha256 指紋 `scratchpad/p926/foreign-fp.txt`（正對照含 `rag-orchestrator/services/agent/runtime.py`）；備份 `scratchpad/p926-backup/`（`claude/`、`agents/` 兩份 `endpoint_progress.py`、`test_endpoint_progress_req.py`、`HANDOFF.bak`）逐檔 `cmp` 相同。
- **實作**：
  - `page_import_closure.py`（`.claude/` 與 `.agents/` 兩份 `cmp` 相同）：自原型整理（移除未用變數），對釘住匯出產出與原型 `scratchpad/p926/closure.json` 的 `pages` 完全相同 ⇒ `[closure] spa components 141; files per page min 1 median 4 max 67`；寫入 `runs/outline-20260920/page-import-closure.json`（`sha` `b2ee2ac382ce`）。
  - `endpoint_progress.py`（兩份 `cmp` 相同；`git diff --stat` 33 增／12 刪）：`code_paths` 去 `#…`；`page_hit` 給閉包時比閉包、頁不在閉包內大聲失敗、不給時只比入口檔；`load_closure`／`--closure`；docstring 更新。
  - 實跑：有 `--closure` ⇒ `已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`；不給 ⇒ `頁面 pm 143／183、prospect 53／183`。
- **測試**：`test_endpoint_progress_req.py` 加 4 條、新檔 `test_page_import_closure_req.py` 4 條 ⇒ 兩檔 `13 passed`。變異（scratch 副本掛載覆蓋，repo 檔不變）：`page_hit` 閉包分支改只比入口檔 ⇒ `test_closure_counts_subcomponent_citation` 紅；`build` 停用子路由（`kids = {}`）⇒ `test_children_spread_and_imports_are_followed` 紅。全套 `scripts/run-tests.sh unit` ⇒ `passed=3939 failed=9`，紅燈與基準雙向差集＝∅（`scratchpad/p926/unit-after.log`）。
- **文件**：HANDOFF 開頭終點指標（跑法加 `--closure`、現值）、一句話現況、開工第 2／5 步、§12-1 加 9.26 列、§12-4 頁面待辦改寫為剩餘 6 頁。
