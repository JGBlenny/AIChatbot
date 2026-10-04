# Plan 9.25 驗收清單（2026-10-04 凍結；與計畫一起送就緒審查，核可後 ⛔ 修改）

業主原話：「繼續這些?」——對清單「重新起草 9.24 為了整句刪除而拿掉的 4 項正確資訊…；補頁面缺口：pm 實際缺約 11～12 頁；prospect 頁面範圍要先請您定；已審的存量補做一次寫入後全數核對」；選擇「頁面缺口＋4項資訊合一份」「這份只做 pm，prospect 另議」「先不排」「ASK」；就緒審查後再選「只補真缺內容 (Recommended)」——對選項「新寫 communities.pick＋3 項資訊（約 4～6 條新細目），頁面 pm 約 140→141；其餘 10 頁記為量尺待辦」。

判定：A1～A5 全部 PASS ⇒ 任務完成；任一 FAIL ⇒ 未完成（commit 前＝依計畫還原並停；commit 後＝⛔ 改寫歷史、⛔ 自行撤回，回報業主）。觀察點一律是 **commit 之後的 HEAD 與乾淨工作樹**。

## A1「只補真缺內容：communities.pick」——頁面 pm 多 1 頁
- 觀察：commit 後 HEAD 正本，以 `endpoint_progress.page_hit` 對已審且含 `property_manager` 的細目判定。
- 通過：`page:communities.pick` 命中，且命中的細目 `evidence` 至少一筆引用 `src/pages/communities/pick/Index.vue`；該細目回答「選好社區之後會發生什麼」，與 `jgb/C/community-batch-add-and-copy`、`estate-list-add-must-pick-community`、`community-estates-add-batch-copy` 不同題。
- 負對照：同一判定對開工前 HEAD `6e4db63d` 跑 ⇒ 未命中。

## A2「重新起草拿掉的資訊」——3 項各有一條已審新細目
- 通過：HEAD 正本有新細目分別回答：(1) 建立房東身分時拿到什麼方案（企業團隊與社宅房東自動取得免費方案；個人房東一般也是，另有優惠連結與行銷活動邀請連結兩條例外入口；⛔ 排他寫法）；(2) 客製化契約書送簽時 PDF 底稿解析失敗則簽署不會開始；(3) 帳號資訊頁改密碼的規則（至少 6 個字元、需與確認欄位一致；英數提示在此不強制，且與 `jgb/A/register-password-rule` 不矛盾）；皆已審。第 4 項「免費方案最多 5 個物件」由既有已審 `jgb/I/pricing-free-trial-feature-scope` 涵蓋（HEAD 標題含「最多 5 個物件」）。
- 範圍：既有 539 條細目相對 `6e4db63d` 逐欄不變（`jgb.json` 比對）；本計畫只新增細目。

## A3 每句都核對成立
- 觀察：commit 樹內 `verification/*.json`（`kind: write`）。
- 通過：`verdict=CONFIRMED`、`base`＝父 commit；`fines`＝本次新增已審全集；每條 `title=成立`、`sentences` 句數＝HEAD 正本 `content_units` 數且全為 `成立`、`content_sha256`／`title_text`＝HEAD 正本；判準含同題、跨粗目矛盾、排他／過度概括即不成立；HEAD 版 `outline_plan_discipline.py` PASS；commit 訊息有 `Verified-by:`。
- 人工：每條都讀 notes（⛔ 抽樣），每句引用該細目宣告的來源。

## A4 終點指標
- 觀察：commit 後重跑 `endpoint_progress.py`。
- 通過：第一行以 `已審細目 pm X／X、prospect Y／Y；頁面 pm P／183` 開頭，X＝533＋新增 pm 細目數、Y＝120＋新增 prospect 細目數、**P ≥ 141**。負對照：開工前為 `已審細目 pm 533／533、prospect 120／120；頁面 pm 140／183`。

## A5 沒有打壞別的東西
- 全套單元：紅燈集合與 9 條基準（HANDOFF §12-2）雙向差集＝∅（若需改測試，須業主另行核可並附變異檢查）。
- `make audit`：commit 前與 commit 後皆 OVERALL PASS。
- 其他工作線未 commit 檔：sha256 與開工前指紋全同。
- 新細目標題／句子／講法：程式識別字與路徑 0、客戶名 0、講法與全庫 0 重複。
- commit 檔案集合＝計畫 §6 記錄的清單（`git show --name-only HEAD`）。

## 不在本次範圍（業主原話未包含，明列以免誤認為完成）
- 量尺待辦：10 頁內容已有但引用未對到入口檔、約 29 頁外殼頁、`notifications.index`、`/help` 外殼；`bills.sheet`（G3 排除）。
- prospect 可見頁範圍與 prospect 頁面數（業主「另議」）。
- 已審存量補做寫入後全數核對（業主「先不排」）。
- 線上 AI 客服答得到這些細目（需部署；現況未查證）。
