<!-- plan-meta
endpoint_from: pm 527/533, prospect 118/120
endpoint_to: pm 533/533, prospect 120/120
consent_zero:
-->
# Plan 9.24：剩餘 6 條修正＋終審（現有細目全審）

> **現況**（`endpoint_progress.py`，2026-10-04，HEAD `c14ca7ae`）：`已審細目 pm 527／533、prospect 118／120；頁面 pm 140／183、prospect 53／183`；`jgb.json` 539 條、未審 6 條。
>
> **本計畫預期**：已審細目 **pm 527→533、prospect 118→120**（6 條全為 pm；兩條定價細目同時開放 prospect）⇒ 現有 539 條全審。頁面指標預跑實測不變（pm 140、prospect 53；頁面缺口另案）。
>
> **驗收清單（凍結）**：`.kiro/specs/knowledge-outline-and-intent-architecture/acceptance-9.24-20261004.md`（A1～A5；觀察點＝commit 後 HEAD）。

## 0. 為什麼有這份

- 業主 2026-10-04「開」——對提案「開 Plan 9.24，把剩下 6 條修完、審完，預期 pm 527→533、prospect 118→120」。先前業主裁示「別管上限 聚焦驗收成果」⇒ 本計畫 **不設預算停點**，停止條件只看驗收結果。
- 6 條與各自的已知問題（皆有釘住匯出證據，主 session 已對匯出 grep 確認）：

  | 細目 | 問題 | 出處 |
  |---|---|---|
  | `jgb/I/pricing-free-trial-eligibility` | 標題、句 2、句 4：寫成「個人房東未帶優惠代碼才拿免費方案、帶優惠代碼就拿指定方案」；實際只有 session `promotion.type=='registration_plan'` 才給別的方案（`app/User.php` Step4，且只在 `RULE_KEY_LANDLORD_INDIVIDUAL` 分支），而設定它的入口不只優惠代碼（`PromotionController.php`），還有行銷邀請連結（`MarketingInviteController.php` `'type' => 'registration_plan'`，方案 `個人房東 - 知識衛星行銷專案`）；`login_plan`／`plan_discount` 類代碼註冊仍拿免費方案 | 9.23 §6 S1 verifier；9.24 就緒審查第 1 輪 |
  | `jgb/I/pricing-free-vs-experience-plan` | 句 1 括號同上 | 同上 |
  | `jgb/D/contract-thinkcloud-signing-variants` | 句 3「也會跳出同樣的訊息」不成立（簽署走原生 POST → redirect → `thinkcloud()` catch 回陣列，瀏覽器得 JSON 頁、無彈窗）；「簽署不會開始」成立 | 9.22 §6 S3 verifier |
  | `jgb/A/account-change-password` | 句 4「需同時包含英文與數字」：帳號資訊頁 `儲存` 按鈕（`account.blade.php` `<button form="form_account_setting" … type="submit"`）未綁 `password_allow_submit`（`safety.blade.php` 才有），後端只驗 `min:6|…|same:password_confirmation` ⇒ 英數未強制 | 9.22 §6 S2 先審 doubt |
  | `jgb/A/account-basic-info`、`jgb/A/account-contact-info` | 無已知問題（9.22 S2 先審 pass；⚠️ 組因同組 change-password 而延後） | 9.22 S2 |

## 1. 切片：只有 S1（修正＋終審＋寫入＋全數核對＋一次 commit）

### 流程設計（與 9.21／9.22 不同處，請業主一併核可）

1. **⛔ 另開「重新先審」片**：9.22／9.23 的經驗是先審（含重新先審）三輪都放過的錯句，只有寫入後的全數逐句核對抓得到；本計畫改以「寫入後 fresh outcome verifier 全數逐句核對 6 條」為唯一品質閘門（每句、帶 `content_sha256`），任一句不成立即整片還原。
2. **修正＝整句刪（嚴格遵守 D1「修一次仍不過就整句刪」）**：4 處錯句皆為 9.21 修過一次後又被推翻（定價兩條＝9.21 W2 整條 #18／#19、thinkcloud 句 3＝9.21 W2 整條 #4、change-password 英數規則＝9.21 W1 整條 #1）⇒ 整句刪除，⛔ 第二次改寫、⛔ 只刪子句（第 2 輪就緒審查指出：只刪子句會留下排他列舉或過度概括）。標題只做刪字，使標題每一點都有內文支撐。機械證明：標題修正後文字是原文子序列；句子只有 `delete` 運算。代價（刪掉的正確資訊，記 §2 由下份計畫重新起草）：個人房東怎麼取得免費方案、免費方案可建 5 個物件、客製化 PDF 送簽時解析失敗則簽署不會開始、新密碼至少 6 字元且需與確認欄位一致。
3. **修正由主 session 起草**（只刪、證據已在手）；D1「修整條」由主 session 逐條檢查標題、全部句子與講法；獨立性由寫入後的 fresh verifier 提供。
4. **業主終審在核可時一併給**：終審對象＝下表修正後原文＋2 條未改細目。
5. **測試修正（只改測試）**：全審後 `tests/unit/agent/test_library_view_req.py::test_real_views_fit_the_budget` 的正對照「在第一條未審細目注入 reviewed」已無未審可標 ⇒ 依設計大聲失敗（與 9.22 S3 同類：測試取樣綁正本資料）。修法：新增 `_all_unreviewed_canon_copy`，全審時改用反向 mutation「複本全部撤審 ⇒ 兩受眾兩把尺必為 0」；未全審時維持原做法。⛔ 產品程式 0 改動。

### 修正後原文（業主終審對象；整句刪＋標題刪字）

| 細目 | 位置 | 處置 | 修正後 |
|---|---|---|---|
| `pricing-free-trial-eligibility` | 標題 | 刪字 | 免費試用怎麼開始、能用多久？（一個週期後不自動續訂） |
| 同上 | 句 2、句 4 | 整句刪 | 剩 2 句：①價格頁「免費試用方案」30 天文案與「免費註冊試用」連結；②免費方案效期一個週期、不自動續訂 |
| `pricing-free-vs-experience-plan` | 標題 | 刪字（刪「 5 個物件」） | 免費方案與體驗方案差在哪？（前者系統贈送，後者付費訂閱、可選月繳或年繳，可建 10 個物件並自行續訂） |
| 同上 | 句 1 | 整句刪 | 剩 4 句（體驗方案 10 物件可續訂、月費／年費、免費方案價格 0、免費方案不自動續訂） |
| `contract-thinkcloud-signing-variants` | 句 3 | 整句刪 | 剩 2 句（公會中文版補充條款簽名位置、客製化 PDF 建立時解析失敗）；標題兩點皆有內文支撐 |
| `account-change-password` | 句 4 | 整句刪 | 剩 4 句；標題「需輸入目前密碼、新密碼與確認新密碼」由句 3 支撐 |

- ops 存 `scratchpad/p924/ops.json`（只有 `title` 刪字與 `delete`；無新增證據、sources 不變）；`ops-v1-rewrite.json`（第 1 輪推翻）、`ops-v2-clause.json`（第 2 輪推翻）已作廢。
- **整條檢查（D1）**：刪後 4 條逐句與標題——`pricing-free-trial-eligibility` 句 1（價格頁文案）、句 3（一個週期不續訂）與講法；`pricing-free-vs-experience-plan` 句 2～5；thinkcloud 句 1～2；change-password 句 1～3、句 5——與 9.22／9.23 驗證結論一致；兩條定價細目刪後不再對「誰會自動取得免費方案」下任何列舉或概括，互不矛盾。正本其他細目含「優惠碼」者只有 I 架訂閱優惠碼細目（訂閱時兌換，與註冊取得方案無關），無「另見」。

### 已預跑（2026-10-04，HEAD `c14ca7ae`；repo 未動；第 2 輪處置後全數重跑）

- scratch runs 副本 `p924/runs-pc`：九架 roundtrip 全 True；ops 套用 4 條（句數 4→2、5→4、3→2、5→4）；兩處標題修正皆通過子序列（只刪字）檢查。
- scratch 重生成（`--expect-reviewed-kept 533 --expect-open-questions 54`）⇒ 保留 533／丟棄 0、57 粗目／539 細目；`canon_check` ⇒ `blocks changed 4 (in allowed 4)`、`jgb.json fines changed 4`、`CATALOG lines changed 4`、客戶名 0、`mismatches: 0`；`name_scan` hits 0；終點指標 `已審細目 pm 527／533、prospect 118／120；頁面 pm 140／183、prospect 53／183`（+0）。
- 被推翻／排他／過度概括字串（`沒有帶入優惠代碼時，才自動取得`、`取得的是優惠代碼指定的方案`、`帶優惠代碼註冊時取得的是優惠方案`、`也會跳出同樣的訊息`、`需同時包含英文與數字`、`未帶優惠代碼時自動取得`、`建立房東身分時自動贈送`、`企業團隊與社宅房東建立身分時自動取得`）：現行正本 `.md`＋CATALOG 依序 1／1／1／1／1／2／1／2 命中、修正後皆 0。
- scratch 寫入 6 條（`approve_write.py write`，`P918_WRITE_SHELVES=ADI`）⇒ verify `reviewed backup 533 -> current 539`、`reviewed fines pm 533, prospect 120`、`mismatches: 0`；終點指標 `已審細目 pm 533／533、prospect 120／120；頁面 pm 140／183、prospect 53／183`。
- 全套 unit（scratch 全審正本、原測試檔，第 1 版預跑）⇒ **10 failed**，新增 `test_library_view_req.py::test_real_views_fit_the_budget`（`AssertionError: 沒有標到任何一條細目（可能全部細目皆已審）`）；同測試的真實兩視圖預算斷言本身通過。
- 測試修正（scratch 副本 `p924/test_library_view_req.py`，掛載覆蓋執行）：全審正本 ⇒ 該檔 17 passed；現行 533 正本 ⇒ 17 passed；原版在全審正本 ⇒ 1 failed；變異（撤審複本換回原正本，`p924/test_library_view_req.mut.py`）⇒ 1 failed；全套 unit（本版 ops 的全審正本＋修正測試，`p924/unit-pre4.log`）⇒ `passed=3931 failed=9`，與基準雙向差集＝∅。

### 對 repo 執行（核可後）

0. 業主原文逐字記入 §6「### S1」；`make audit` 基準（預期 OVERALL PASS）；其他工作線未 commit 檔 sha256 指紋（`git status --porcelain -z`，扣除本計畫與驗收清單）。
1. 備份 `scratchpad/p924-backup/`：`.claude/skills/outline-curation/runs/outline-20260920/` 整個目錄、`rag-orchestrator/canon/`、測試檔、HANDOFF；`diff -r`／`cmp` 相同。
2. ops 套用 repo drafts（`ALLOWED=p924/allowed.json` 4 條）⇒ 重生成（`--runs-out` scratch、`--date 20261004-s1-924`，再把 3 個 runs 產出複製回 repo 並 `cmp`）⇒ `canon_check`／`name_scan` ⇒ 與 scratch 預跑 `p924/canon-pc` `diff -r` 相同 ⇒ 終點指標 +0。
3. 寫入 6 條 reviewed ⇒ 容器重匯出 ⇒ `approve_write.py verify`（backup＝步驟 2 後正本）⇒ 與 `p924/canon-w` `diff -r` 相同 ⇒ 終點指標第一行以 `已審細目 pm 533／533、prospect 120／120；` 開頭。
4. 測試檔換成 `p924/test_library_view_req.py`（`cmp`）⇒ 全套 `scripts/run-tests.sh unit` 與基準差集＝∅。
5. 寫 §6 紀錄（所有數字由實跑輸出複製、⛔ 照抄代理數字）、更新 HANDOFF（開頭終點指標、一句話現況、開工第 2／5 步、§12-1 加 9.24 列、§12-4 未審細目段）。
6. `make audit` ⇒ 預期只有不變量 43 工作樹 W（6 條）FAIL。
7. **fresh outcome verifier**（brief 中文、findings 繁中、HANDOFF §12-2 必禁、HEAD 全碼、證據形狀同 9.23 §1）待驗宣稱＝驗收清單 A1、A2（工作樹）、A3 的逐句部分、A4（工作樹）、A5 的單元與測試修正，以及本計畫 §6 與 HANDOFF 改動處數字與實況一致；(5) 每個數字要求代理自行重算。**判準另加**：標題與句子不得以列舉或概括造成排他或過度概括（例：漏列個人房東預設取得、概括所有房東身分）；同粗目細目之間對同一事實的說法不得互相矛盾——違反即判「不成立」。
8. **commit 前收尾檢查（全部要過才 commit）**：`--extract` ⇒ `verification/20261004-p924-write.json` ⇒ `make audit` OVERALL PASS ⇒ 指紋 `shasum -c` 全同 ⇒ `git diff --cached --name-only` 恰為下列 16 檔 ⇒ commit（trailer `Verified-by: .kiro/specs/knowledge-outline-and-intent-architecture/verification/20261004-p924-write.json CONFIRMED`）。
9. **commit 後驗收**：照驗收清單 A1～A5 對 HEAD 逐條判定（commit 後重跑終點指標與 `make audit`；commit 內容與驗證時逐位元組相同，A5 其餘項在步驟 4、8 已於同一棵樹確認）。
- **commit 範圍（16 檔）**：`drafts-A.json`、`drafts-D.json`、`drafts-I.json`；runs `dsp-068-deletions-20261004-s1-924.json`、`open-questions-20261004-s1-924.md`、`reviewed-dropped-20261004-s1-924.json`；`rag-orchestrator/canon/jgb/A.md`、`D.md`、`I.md`、`CATALOG.md`、`jgb.json`；`rag-orchestrator/tests/unit/agent/test_library_view_req.py`；本計畫；驗收清單；HANDOFF；證據檔。⛔ `git add -A`、⛔ `--amend`；push 由業主自跑。
- **通用還原（步驟 2 起到 commit 前的任何停下，無例外）**：runs 目錄、canon、測試檔、HANDOFF 由 `p924-backup/` 還原（runs 新增的 3 檔一併刪除），`git status` 對上述路徑為空、`diff -r`／`cmp` 相同、`load_canon_or_die` 通過 ⇒ 記 §6 ⇒ 停下交業主。
- **verifier 推翻計畫紀錄（非正本內容）時**：如 9.23 S1b，正本與 drafts 不還原，改正紀錄後派新 verifier 重驗全部宣稱；推翻正本內容 ⇒ 通用還原。
- **commit 後驗收任一項 FAIL**：⛔ 改寫歷史（`--amend`／rebase／reset）、⛔ 自行撤回或另開修正 commit；在對話中回報業主（哪一項、實際輸出），由業主裁決撤回或修正方式（任何後續 commit 碰本線路徑皆須另附驗證證據）。

## 2. 不做（另案）

- **本計畫整句刪掉的正確資訊，下份計畫新起草**：個人房東怎麼取得免費方案（預設自動取得；`registration_plan` 類優惠代碼與行銷邀請連結兩條入口例外）、免費方案可建 5 個物件、客製化 PDF 送簽時解析失敗則簽署不會開始、新密碼至少 6 字元且需與確認欄位一致。
- 頁面缺口（新起草細目）、prospect 可見頁範圍、54 則待裁、jgb2 缺陷提報（含 9.23 verifier 附記的 `add_attachment` 後端上限讀錯陣列層）、線上部署查證。

## 3. 業主裁決與待裁

- **已裁**：§0。
- **待裁（核可時一併回覆）**：(a) 本計畫與 §1「流程設計」五點（含「整句刪」與其代價：4 項正確資訊暫時從正本消失，下份計畫補）；(b) 終審：6 條（4 條依上表修正後原文、2 條原文）全部標已審，條件是寫入後全數逐句核對成立。建議原文：「核可，6 條終審過」。

## 4. 停止條件

- 驗收結果：任一步驟檢查或驗收項不符 ⇒ 依 §1 處置（commit 前＝通用還原；commit 後＝回報業主）；不設預算停點（業主「別管上限 聚焦驗收成果」）。
- 已審細目數任何時候下降 ⇒ 停。
- 一次只跑一個代理（本機 8GB）；代理 brief 一律帶 HANDOFF §12-2 必禁清單。

## 5. 就緒審查紀錄

- **第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-04）：P2×4——(1) 定價細目改寫稿「只有透過『註冊免費方案』類型的優惠代碼…例外」是排他敘述，漏了行銷邀請連結 `MarketingInviteController`（同樣設 `registration_plan`）；(2) 4 處皆為「修一次仍不過」，D1 規定整句刪，計畫卻第二次改寫且未列為例外；(3) 驗收清單 A4「第一行逐字為」與 `headline()` 實際輸出（後接頁面段）不符，必 FAIL；(4) commit 後驗收 FAIL 無處置。主 session 對匯出確認 (1)（`MarketingInviteController.php` `'type' => 'registration_plan'`、Step4 只在個人房東分支）。處置：四項皆 **FIX**——(1)(2) 改為只刪不寫，5 處以子序列檢查證明只刪字元、刪後缺口記 §2；(3) A4 改「以…；開頭」；(4) 新增「commit 後驗收任一項 FAIL」處置並把可在 commit 前判定的項目移到步驟 8。預跑全數重跑（§1「已預跑」為新值）。送第 2 輪。
- **第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-04）：P2×1——只刪子句後兩條定價細目出現排他列舉（`pricing-free-trial-eligibility` 標題與句 2 只列企業團隊與社宅房東，漏個人房東預設取得）與過度概括（`pricing-free-vs-experience-plan` 句 1「建立房東身分時自動贈送」還原 9.21 #19 修過的概括），兩條互相矛盾；D1 原文是整句刪；逐句「成立」的閘門攔不到。其餘（只刪、A4、commit 後處置、16 檔、change-password 與 thinkcloud）無阻擋。⇒ **第二次自動 REVISE，停止重送、逐條處置**：**FIX**——四處一律整句刪（含 thinkcloud 句 3、change-password 句 4，與 D1 一致、不另設子句例外），定價兩條標題只刪字至每點有內文支撐；verifier brief 與 A3 加「排他／過度概括／同粗目矛盾即不成立」判準；刪掉的 4 項正確資訊記 §2；預跑全數重跑。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **收尾審查（fresh plan-verifier）＝READY**（2026-10-04）⇒ 交業主核可＋終審（`next_gate: user_approval`）。

## 6. 執行紀錄

### S1（2026-10-04）

- **業主裁決原文**（2026-10-04，對「請回覆核可與終審」）：「核可，6 條終審過」——核可本計畫（含 §1 流程設計五點與 §2 代價）；6 條（4 條依 §1 修正後、2 條原文）標已審，條件是寫入後全數逐句核對成立。
- **步驟 0**：`make audit` 基準 `OVERALL: PASS（2026-10-04）`；其他工作線未 commit 檔 41 個 sha256 指紋存 `scratchpad/p924/foreign-fp.txt`（正對照：含 `rag-orchestrator/services/agent/runtime.py`）；HEAD `c14ca7aefdef846c063b37f360a4cf3423aa4e9d`。
- **步驟 1**：備份 `scratchpad/p924-backup/`（runs 目錄、canon、測試檔、`HANDOFF.bak`）與 repo `diff -r`／`cmp` 相同。
- **步驟 2**：ops 套用 ⇒ `pricing-free-trial-eligibility: 4 -> 2`、`pricing-free-vs-experience-plan: 5 -> 4`、`contract-thinkcloud-signing-variants: 3 -> 2`、`account-change-password: 5 -> 4`；`drafts-{A,D,I}.json` 與預跑 `p924/runs-pc` `cmp` 相同，其餘六架與備份相同。重生成 ⇒ `已審保留：533 條／丟棄：0 條`、57 粗目／539 細目、open_questions 54；3 個 runs 產出與預跑 `cmp` 相同並複製回 repo；repo 正本與預跑 `p924/canon-pc` `diff -r` 相同；`canon_check` ⇒ `blocks changed 4 (in allowed 4)`、`CATALOG lines changed 4`、`mismatches: 0`；`name_scan` hits 0；終點指標 `已審細目 pm 527／533、prospect 118／120；頁面 pm 140／183、prospect 53／183`（+0）。
- **步驟 3**：`write` ⇒ `added 6`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 533 -> current 539; added lines 6; approved 6`、`reviewed fines pm 533, prospect 120`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；repo 正本與預跑 `p924/canon-w` `diff -r` 相同；**終點指標 `已審細目 pm 533／533、prospect 120／120；頁面 pm 140／183、prospect 53／183`**（各架 pm 全滿：A 62、B 78、C 81、D 104、E 96、F 33、G 26、H 5、I 48）。
- **步驟 4**：測試檔換成 `p924/test_library_view_req.py`（`cmp` 相同；`git diff --stat` 49 增／9 刪）；`scripts/run-tests.sh unit` ⇒ `passed=3931 failed=9`，紅燈集合與基準雙向差集＝∅（`scratchpad/p924/unit-after.log`）。
- **步驟 5**：HANDOFF 更新開頭終點指標、一句話現況、開工第 2／5 步、§12-1 加 9.24 列、§12-4 未審細目段。
- **步驟 6**：`make audit` 與基準相比唯一差異＝不變量 43 `W 工作樹有 6 條細目新增已審或已審內容變動，卻沒有 base＝HEAD 的全數逐句核對證據`（`scratchpad/p924/audit-prev.log`），符合預期。以下由證據檔與 commit 訊息記錄（驗證後 ⛔ 再改本計畫）。
