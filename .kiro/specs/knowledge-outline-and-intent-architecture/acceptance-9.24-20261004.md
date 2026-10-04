# Plan 9.24 驗收清單（2026-10-04 凍結；與計畫一起送就緒審查，核可後 ⛔ 修改）

業主原話：「開」——對提案「開 Plan 9.24，把剩下 6 條修完、審完，預期 pm 527→533、prospect 118→120。這樣現有細目就全部審完。」

判定：A1～A5 全部 PASS ⇒ 任務完成；任一 FAIL ⇒ 未完成（依計畫 §1「commit 後驗收任一項 FAIL」處置：⛔ 改寫歷史、⛔ 自行撤回，回報業主裁決）。觀察點一律是 **commit 之後的 HEAD 與乾淨工作樹**，⛔ 以工作樹未 commit 狀態算完成。

6 條：`jgb/A/account-basic-info`、`jgb/A/account-contact-info`、`jgb/A/account-change-password`、`jgb/D/contract-thinkcloud-signing-variants`、`jgb/I/pricing-free-trial-eligibility`、`jgb/I/pricing-free-vs-experience-plan`。

## A1「把剩下 6 條修完」——4 條錯句已修、修正只動這 4 條
- 觀察：HEAD 的 `drafts-{A,D,I}.json` 與 `rag-orchestrator/canon/jgb/{A,D,I}.md`，對照本計畫 §1 的修正後原文。
- 通過：4 條依 §1「修正後原文」處置——句子只有整句刪（句數 `pricing-free-trial-eligibility` 2、`pricing-free-vs-experience-plan` 4、`contract-thinkcloud-signing-variants` 2、`account-change-password` 4，其餘句與開工前逐字相同），兩條定價細目標題逐字等於 §1 且為原文子序列（只刪字）；HEAD 正本（`jgb/*.md` 含 CATALOG）中已不含下列字串：`沒有帶入優惠代碼時，才自動取得`、`取得的是優惠代碼指定的方案`、`帶優惠代碼註冊時取得的是優惠方案`、`也會跳出同樣的訊息`、`需同時包含英文與數字`、`未帶優惠代碼時自動取得`、`建立房東身分時自動贈送`、`企業團隊與社宅房東建立身分時自動取得`。
- 範圍：相對 9.24 開工前 commit，drafts 與正本的內容變動只出現在這 4 條（另 2 條只多 `- reviewed:` 行）；其他 533 條逐欄不變。
- 負對照：上述 8 個字串在開工前 commit 的正本中各命中 ≥1（證明搜尋有效）。

## A2「審完」——6 條已審且已進版控
- 觀察：`git show HEAD:rag-orchestrator/canon/jgb.json`。
- 通過：6／6 為 `reviewed_by=owner`、`reviewed_at` 為 2026-10-04；HEAD 上未審細目數＝0；`git status --short rag-orchestrator/canon .claude/skills/outline-curation/runs` 為空。

## A3 每句都核對成立（寫入驗收＝全數逐句核對）
- 觀察：HEAD 樹內 `.kiro/specs/knowledge-outline-and-intent-architecture/verification/20261004-p924-write.json`。
- 通過：`kind=write`、`verdict=CONFIRMED`、`base`＝9.24 開工前 HEAD；`fines` 恰 6 條＝A2 的 6 個 id；每條 `title=成立`、`sentences` 句數＝HEAD 正本該條 `content_units` 數且全為 `成立`；`content_sha256`／`title_text`＝HEAD 正本的值；HEAD 版 `outline_plan_discipline.py` PASS；commit 訊息有 `Verified-by:` 指向此檔。
- 判準含：標題與句子不得以列舉或概括造成排他或過度概括；同粗目細目對同一事實的說法不得互相矛盾（違反即不成立）。
- 人工：6 條每條都讀 notes（⛔ 抽樣），確認每句引用的是**該細目宣告的來源**（jgb2 釘住匯出路徑／符號，或 sources 所列幫助中心頁），不是空泛描述。

## A4 終點指標「pm 527→533、prospect 118→120」
- 觀察：commit 後重跑 `endpoint_progress.py`（HANDOFF 開頭指令）。
- 通過：第一行以 `已審細目 pm 533／533、prospect 120／120；` 開頭（其後為頁面段）。負對照：對開工前 commit 正本跑，第一行以 `已審細目 pm 527／533、prospect 118／120；` 開頭 ⇒ 不符。

## A5 沒有打壞別的東西
- 全套單元：紅燈集合與 9 條基準（HANDOFF §12-2）雙向差集＝∅。
- `test_library_view_req.py` 的修正：相對開工前 commit 只新增 `_all_unreviewed_canon_copy` 與改寫 `test_real_views_fit_the_budget` 的 mutation 段；在 HEAD 正本（全審）上該檔全綠；反向 mutation 有咬合力（把撤審複本換成原正本 ⇒ 該測試變紅）；產品程式 0 改動。
- `make audit`：commit 前（計畫步驟 8）與 commit 後最終工作樹皆 OVERALL PASS。
- 其他工作線未 commit 檔：sha256 與開工前指紋全同（計畫步驟 8，commit 前）。
- commit 檔案集合＝計畫 §1 列的 16 檔（`git show --name-only HEAD`）。

## 不在本次範圍（業主原話未包含，明列以免誤認為完成）
- **線上 AI 客服答得到這 6 條**：需部署；部署與線上正本版本現況未查證（HANDOFF §12-4）。
- 頁面缺口（pm 頁面 140／183）、新起草細目、54 則待裁、jgb2 缺陷提報。
- 本次整句刪掉的 4 項正確資訊（個人房東怎麼取得免費方案、免費方案 5 個物件、送簽時 PDF 解析失敗則簽署不會開始、新密碼至少 6 字元且需與確認欄位一致）：不補寫（計畫 §2，下份計畫起草）。
