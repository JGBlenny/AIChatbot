# Plan 9.26 驗收清單（2026-10-04 凍結；與計畫一起送就緒審查，核可後 ⛔ 修改）

業主原話：「同意」——對建議「下一份做『改量尺』：讓頁面指標把同一頁目錄底下子元件的引用也算進去。這不動正本，是 +0 計畫，需要您明示同意，也等於推翻您先前『量尺先不動』的裁示」（理由：量尺把內容已寫、只引用子元件的頁算成缺口；改量尺比補引用便宜且不動已審內容；改完才看得出真缺口）。

判定：A1～A4 全部 PASS ⇒ 任務完成；任一 FAIL ⇒ 未完成（commit 前＝依計畫還原並停；commit 後＝⛔ 改寫歷史、⛔ 自行撤回，回報業主）。觀察點一律是 **commit 之後的 HEAD 與乾淨工作樹**。

## 實作差異（以業主核可計畫 §3 待裁 (b) 為前提；不核可則本清單 A1 須重寫、⛔ 沿用）
- 原話「同一頁目錄底下子元件」⇒ 實作改為「頁面入口檔的 import 閉包＋子路由（只收 `src/pages/` 底下的檔）」，⛔ 以目錄比對。理由：同目錄的兄弟頁會互相點亮（`users/auth/` 下的 `Forget.vue`／`Login.vue`／`Verify.vue` 是不同頁）；子路由渲染的檔不一定在同目錄（`users.forget` 的畫面在 `parts/forget/*.vue`）。

## A1「讓頁面指標把同一頁目錄底下子元件的引用也算進去」——量尺改了、而且量得對（依上節實作差異）
- 觀察：HEAD 的 `endpoint_progress.py --closure …/page-import-closure.json` 對 HEAD 正本重跑。
- 通過：第一行以 `已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183` 開頭；附件 `inputs/page-coverage-closure-9.26-20261004.md` 列的 35 頁在 HEAD 量尺下皆命中；每列的「細目 → 命中檔」：**SPA 頁**＝命中檔在 HEAD 閉包 JSON 該頁清單內、且在該細目 `sources`（`code:src/pages/<檔>`）內；**blade 頁**（本次只有 `page:web:notifications.index`）＝命中檔是該細目 `sources` 去掉 `#方法` 後的 controller 檔，不查閉包 JSON（閉包只對 SPA 頁）。
- 正對照：`users.forget` 由引用 `parts/forget/*.vue` 的已審細目命中（舊量尺不命中）。
- 負對照：不給 `--closure` 時第一行頁面段為 `頁面 pm 143／183`（只比入口檔＋`#方法` 去除）；兄弟頁不互相點亮——`users/auth/Login.vue` 的閉包不含 `users/auth/Forget.vue`。

## A2「這不動正本」——+0
- 通過：相對 `60cc55df`，`rag-orchestrator/canon/` 與 `runs/outline-20260920/drafts-*.json` 位元組不變；已審細目數不變（pm 537、prospect 121）。

## A3 閉包可重現、可信
- 通過：HEAD 的 `page_import_closure.py` 對釘住匯出（`b2ee2ac382ce`；匯出以 `.claude/skills/outline-curation/scripts/review_pipeline/README.md` 的 `git -C …/jgb2/dev1 archive b2ee2ac382ce | tar -x` 指令重建，⛔ 讀 jgb2 工作樹）重跑，產出與 HEAD 的 `page-import-closure.json` 逐位元組相同；閉包只含 `src/pages/` 底下的檔（全檔掃描 `src/components` 0 筆）；`.claude/` 與 `.agents/` 兩份腳本 `cmp` 相同。
- 測試：新增測試全綠；變異檢查有咬合力（在 scratch 副本上改、以掛載覆蓋執行，repo 檔 `cmp` 不變：`page_hit` 改回只比入口檔 ⇒ 閉包測試紅；停用子路由解析 ⇒ 子路由測試紅）；給了 `--closure` 但某 SPA 頁不在閉包內 ⇒ 大聲失敗（⛔ 靜默退回舊量法）。

## A4 沒有打壞別的東西
- 全套單元：紅燈集合與 9 條基準雙向差集＝∅（新增測試不在紅燈內）。
- `make audit`：commit 前與 commit 後皆 OVERALL PASS。
- 其他工作線未 commit 檔：sha256 與開工前指紋（計畫 §1 步驟 0 的 `scratchpad/p926/foreign-fp.txt`）全同。
- HANDOFF 開頭的終點指標跑法含 `--closure`，現值與 A1 重跑結果一致。

## 不在本次範圍（業主原話未包含，明列以免誤認為完成）
- 新量尺下剩餘 pm 6 頁（`indexs`、`/help` 的 blade→SPA 對應；`bills.sheet` G3；社宅 3 分頁需改已審細目來源）。
- 閉包是代理指標：跨功能共用子元件會點亮頁、外框父路由會被任一子孫路由的引用點亮（例：`users.index` 命中 63 條、`bills.index` 25 條；附件供抽查）；不代表每頁「每件可問的事」都有細目。
- prospect 可見頁範圍；已審存量補核；線上部署。
