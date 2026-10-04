<!-- plan-meta
endpoint_from: pm 519/533, prospect 116/120
endpoint_to: pm 527/533, prospect 118/120
consent_zero:
-->
# Plan 9.23：10 條已全數核對細目交終審＋寫入

> **現況**（`endpoint_progress.py`，2026-10-04，HEAD `721a0cb6`）：`已審細目 pm 519／533、prospect 116／120；頁面 pm 133／183、prospect 52／183`；`jgb.json` 539 條、未審 14 條；`git diff --stat fd89adaa -- rag-orchestrator/canon` 為空（9.22 S2 先審以來正本未變）。
>
> **本計畫預期**：已審細目 **pm 519→529、prospect 116→120**（10 條全為 pm；其中 4 條同時開放 prospect，寫入後 prospect 全審）。頁面指標由預跑實測後記入 §6，不設目標。
> **S1b 縮減後（2026-10-04，§6 S1b）**：S1 推翻兩條定價細目 ⇒ 只寫入 8 條，預期改為 **pm 519→527、prospect 116→118**（plan-meta 同步）。

## 0. 為什麼有這份

- 業主 2026-10-04「1. (建議) 候選一：把 10 條已全數核對的細目交終審。預計 pm 519→529、prospect 116→120，約 0.4～0.5M。」
- 來源：Plan 9.22 §6「9.22 停止」——S2 安全組 pass 11 條在 S3 寫入後由 fresh outcome verifier **全數逐句核對**，10 條每句成立、1 條（`jgb/D/contract-thinkcloud-signing-variants` 句 3）被推翻；依計畫還原正本、停。10 條的先審判定與審核單沿用 `inputs/review-sheet-9.22-S2-ACDI-20261003.md`（表頭 commit `fd89adaa`），內容自該 commit 起未變。
- 10 條（審核單分組；⚠️ 組 `A-account-profile` 不在內）：
  - C 3：`jgb/C/estate-dashboard-attachments-vs-contract-attachments`、`jgb/C/estate-dashboard-runnings-vs-memos`、`jgb/C/team-public-page-recruitment`（＋prospect）
  - D 4：`jgb/D/contract-show-panels`、`jgb/D/contract-upload-existing-vs-electronic`（＋prospect）、`jgb/D/general-contract-notary-tab`、`jgb/D/contract-thinkcloud-esign-service`
  - I 3：`jgb/I/pricing-free-trial-eligibility`（＋prospect）、`jgb/I/pricing-free-vs-experience-plan`（＋prospect）、`jgb/I/pricing-quota-full-block`
- ⚠️ 9.22 的全數核對**不能直接當本次寫入證據**：不變量 43 W 要求同 commit 附 `base`＝HEAD 的 `kind: write` 證據，且每條帶本 commit 正本的 `content_sha256`／`title_text`。⇒ 本次仍須派一位 fresh outcome verifier 逐句重核 10 條。

## 1. 切片：只有 S1（終審＋寫入＋全數核對＋commit）

### S1 — 業主終審＋寫入（pm +10、prospect +4）

- **業主終審決定**：核可本計畫時一併回覆終審。建議回覆＝「安全組過，排除 contract-thinkcloud-signing-variants」⇒ 決定檔 `{"rule": "safe", "warn_groups": [], "doubt_as_is": [], "exclude": ["jgb/D/contract-thinkcloud-signing-variants"]}`。業主原文先逐字記入 §6「### S1」再 derive；原文與此不同則依原文 derive，並在 §6 記預期增量（不得超過 pm +13、prospect +4）。
- **工具**：`scratchpad/p923/`，由 9.22 的 `p922-s2/` 複製（已存本 session scratchpad `p922-s2-src/`）：`approve_write.py` 只改 `PLAN`＝本計畫、`P918_PLAN_SECTION="### S1"`；results／targets／hold 沿用 `p922-s2-*`（14 條、hold `[]`）；`P918_WRITE_SHELVES=CDI`；`P918_SHEET=<9.22 S2 審核單絕對路徑>`。jgb2 釘住匯出 `scratchpad/jgb2-b2ee2ac/`（`b2ee2ac382ce`；不在則依 `review_pipeline/README.md` 重建）。紅燈基準 `scratchpad/red-baseline.txt`（9 條，與 HANDOFF §12-2 逐名相同）。
- **預跑（核可前，scratch，repo 不動）**：
  1. derive：合成 §6 副本放入建議回覆 ⇒ 預期 `approved 10 (both sources equal) by shelf {'C': 3, 'D': 4, 'I': 3}`、`pm +10, prospect +4`。負對照：回覆不在 §6 ⇒ 大聲失敗；`exclude` 拿掉 ⇒ 11。
  2. scratch 正本 write ⇒ `added 10`；重匯出、`load_canon_or_die` 通過；verify ⇒ `reviewed backup 525 -> current 535`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；A／B／E／F／G／H 與 CATALOG 與備份相同。
  3. scratch 重生成保留（`--expect-reviewed-kept 535 --expect-open-questions 54`，`--runs-out` 指 scratch）⇒ 保留 535／丟棄 0，與 scratch 正本 `diff -r` 相同。
  4. scratch 終點指標＝`pm 529／533、prospect 120／120`；頁面值記下。
  5. scratch 正本掛容器跑全套單元 ⇒ 與紅燈基準差集＝∅（prospect 全審情境已由 9.22 `4f13a0b5` 的測試修正處理；若仍出現新紅 ⇒ 停、交業主，⛔ 自行改測試）。
- **已預跑**（2026-10-04，HEAD `721a0cb6`；repo 正本未動，`git status --short rag-orchestrator/canon` 為空）：
  - 工具 `scratchpad/p923/approve_write.py`：由 `p922-s2-src/` 複製，只改 `PLAN`＝本計畫、預設段落 `### S1`；results／targets／hold 為 `p922-s2-*` 原檔。
  - derive（合成計畫副本 `p923/plan-synth.md` 的 §6「### S1」放入建議回覆）⇒ `approved 10 (both sources equal) by shelf {'C': 3, 'D': 4, 'I': 3}; expected endpoint increment pm +10, prospect +4`。負對照：拿掉 `exclude` ⇒ `approved 11 … D: 5 … pm +11`；回覆不在 §6 ⇒ `❌ decision reply is not verbatim inside plan §6 ### S1 record`、exit 1。
  - scratch 正本 `p923-pc/canon`（repo 複製，`diff -r` 相同）：write ⇒ `added 10`；容器重匯出（9.19 S3 步驟 5 指令，路徑換 `/scratch/p923-pc/canon`）與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 525 -> current 535; added lines 10; approved 10`、`reviewed fines pm 529, prospect 120`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
  - scratch 重生成（`--expect-reviewed-kept 535 --expect-open-questions 54`，`--runs-out` scratch）⇒ `已審保留：535 條／丟棄：0 條`、57 粗目／539 細目、open_questions 54，產出與 scratch 正本 `diff -r` 相同。
  - scratch 終點指標 ⇒ `已審細目 pm 529／533、prospect 120／120；頁面 pm 140／183、prospect 53／183`（C pm 81／81、D 103／104、I 48／48）。
  - scratch 正本掛 `/app/canon` 跑全套 unit ⇒ `9 failed, 3931 passed, 3 skipped`，與紅燈基準雙向差集＝∅。掛載正對照：同掛載下容器讀 `/app/canon/jgb.json` 已審 535（repo 為 525）。
  - 工作樹跑 HEAD 版不變量 43 檢查器（含本計畫檔）⇒ PASS（plan-meta 有效）。
  - **`make audit` 基準**（HEAD `721a0cb6`＋現行工作樹、正本未動）⇒ `OVERALL: PASS（2026-10-04）`、`CODE_CONTRACT_REGRESSIONS: 0`、`PRODUCT / POPULATION BLOCKERS: 0`（log `scratchpad/p923-audit-baseline.log`）。
  - **W 證據路徑**（HEAD 版檢查器 `p923/opd_head.py` 的純函式，舊＝repo `jgb.json`、新＝scratch `p923-pc` 的 `jgb.json`）：`citable_change_ids` ⇒ 10 條、與 derive 核可集合相同。依下方「證據形狀」手寫合成證據：正對照 ⇒ `[]`（0 違規）；負對照三種皆違規——一句改 "不成立" ⇒ `有句子未判成立`；sentences 元素放物件 `{"n":1,"verdict":"成立","evidence":…}` ⇒ `有句子未判成立`；少一條 ⇒ `證據細目 ≠ 需核細目：少 [...]`。合成 transcript（SubagentHandback 形狀）`extract` ⇒ `wrote … verdict CONFIRMED, kind write, fines 10`，取出檔再跑 W ⇒ `[]`；指定錯的 base ⇒ `❌ 代理證據的 base … ≠ 指定`、rc 1。
- **對 repo 執行（核可後）**：
  0. **寫入前預算閘**：累計已花＋本片剩餘主 session 估算（0.1M）＋verifier 預留 0.3M > 0.65M ⇒ **不寫入**、停下回報業主（此時 repo 未動，無須還原）。過閘後到 commit 前不再有預算停點；verifier 實際用量超出預留不中斷交件，事後記帳回報。
  1. 備份 `scratchpad/p923-backup/`（`rag-orchestrator/canon` 全樹＋HANDOFF 存為 `HANDOFF.bak`，`diff -r`／`cmp` 相同）；git 前置限擁有路徑：`git diff --stat HEAD -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆空。其他工作線未 commit 檔建 sha256 指紋為基準（`git status --short` 列出的非本線路徑），本片 ⛔ 碰，commit 前重算須相同。
  2. write ⇒ 重匯出 ⇒ verify（同預跑 2 的期望值）⇒ repo 與 scratch 預跑 `diff -r` 相同 ⇒ 終點指標＝`pm 529／533、prospect 120／120` ⇒ 全套單元差集＝∅。
  3. 寫 §6「### S1」執行紀錄、更新 HANDOFF 開頭終點指標與一句話現況、§12-1 加 9.23 列、§12-4 未審細目段。
  4. `make audit`：基準為 OVERALL PASS（見「已預跑」）⇒ 此時預期**只有**不變量 43 的工作樹 W 項（工作樹已審變動尚無 `base`＝HEAD 的 write 證據）FAIL；其他任一項 FAIL ⇒ 依「通用還原」停。
  5. **fresh outcome verifier（全數逐句核對）**：見下。
  6. `--extract <verifier transcript> verification/20261004-p923-write.json --base <HEAD 全碼>` ⇒ `make audit` 須 OVERALL PASS ⇒ commit（trailer `Verified-by: .kiro/specs/knowledge-outline-and-intent-architecture/verification/20261004-p923-write.json CONFIRMED`）。
  - ⚠️ 驗證後 ⛔ 再改本計畫或 HANDOFF（改了就要重驗）：§6 只記到「派 verifier 前」的事實；verifier 結論以證據檔本身（同 commit）為紀錄，`make audit` 結果寫在 commit 訊息與回報。
- **outcome verifier brief 要點**：中文、findings 繁體中文；HANDOFF §12-2 必禁清單；給 HEAD 全碼並要求在最後一則訊息只放一份 ```json 結論（`kind: write`、`verdict`、`base`、`claim`、`fines`）。待驗宣稱＝要回報業主的宣稱，逐字相同：
  - (1) 10 條每條標題與每句（句數＝`content_units`）對 jgb2 釘住匯出成立，逐條逐句列「成立／不成立」並附匯出證據路徑；每條帶讀到的 `content_sha256` 與 `title_text`；
  - (2) `jgb.json` 已審集合＝525 條原集合 ∪ 這 10 條，其他細目內容不變；A.md 無 diff；
  - (3) 終點指標重跑＝`已審細目 pm 529／533、prospect 120／120`；
  - (4) 全套單元與紅燈基準雙向差集＝∅；
  - (5) 本計畫 §6 與 HANDOFF 改動處的數字與實況一致。
- **證據形狀（brief 逐字寫入）**：最後一則訊息只放一個 ```json 區塊，結構恰為
  `{"kind": "write", "verdict": "CONFIRMED|REFUTED", "base": "<HEAD 全碼>", "claim": "<上述待驗宣稱>", "fines": [{"id": "<細目 id>", "title": "成立", "sentences": ["成立", …], "content_sha256": "<jgb.json 讀到的值>", "title_text": "<jgb.json 讀到的標題>", "notes": ["句 n：<匯出證據路徑與理由>", …]}, …], "findings": [...]}`。
  `title` 與 `sentences` 每個元素**只能是字串** "成立" 或 "不成立"（句數＝該條 `content_units` 數）；證據路徑與理由一律放 `notes`，⛔ 放進 `sentences`。(2)～(5) 的結果放 `findings`。
- **通用還原（適用步驟 2 寫入之後到 commit 之前的任何停下，無例外：步驟 2～6 任一檢查不符、verifier 推翻或交件格式不合 W、`extract` 失敗、取出後 `make audit` 非 OVERALL PASS、commit hook 拒絕、§4 任一停止條件在此區間觸發）**：以 `p923-backup/` 還原 `rag-orchestrator/canon` ⇒ 確認 `git diff --stat HEAD -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆空、與備份 `diff -r` 相同、`load_canon_or_die` 通過 ⇒ HANDOFF 以備份 `p923-backup/HANDOFF.bak` 用 `cp` 還原並 `cmp` 相同（⛔ `git checkout`）⇒ 記 §6 ⇒ 停下交業主（⛔ 本計畫內修句、⛔ 重派第二位 verifier）。正本 ⛔ 在未附證據的狀態下留過本回合。
- **commit 範圍（7 檔）**：`rag-orchestrator/canon/jgb/C.md`、`D.md`、`I.md`、`rag-orchestrator/canon/jgb.json`、本計畫、HANDOFF、`verification/20261004-p923-write.json`。`git diff --cached --name-only` 恰為此 7 檔；⛔ `git add -A`；⛔ `--amend`；push 由業主自跑。

## 2. 不做（另案）

- `contract-thinkcloud-signing-variants` 句 3 修正與重審、`A-account-profile` 3 條（HANDOFF §12-4 候選二）。
- 已審存量補做寫入後全數核對（候選三）。
- 54 則待裁、jgb2 缺陷、頁面缺口、6 條 `sources` 紅燈、9.11 時期未 commit 檔歸屬。

## 3. 業主裁決與待裁

- **已裁（2026-10-04）**：見 §0。核可前不動正本。
- **待裁**：本計畫核可＋S1 終審回覆（§1 建議原文）。執行模式 ASK（S1 完成或停下即回報）。

## 4. 停止條件與預算

- **總上限 0.65M，不放寬**：就緒審查約 0.06～0.18M（最多 3 輪）＋outcome verifier 約 0.25～0.3M（9.22 S3 核 11 條＋測試檔為 0.27M）＋主 session 約 0.15M。⚠️ 比回報候選時的 0.4～0.5M 高，因為 9.22 的教訓是要預留驗證代理。
- **預算閘在寫入前**（§1 repo 執行步驟 0）：累計＋剩餘主 session 0.1M＋verifier 預留 0.3M > 0.65M ⇒ 不寫入、停下回報（9.22 S3 沒有預留驗證代理，派出時已超限）。寫入後的任何停下一律先走 §1「通用還原」再停。
- 已審細目數任何時候下降 ⇒ 停；正本只准在 S1 寫入時變動、且只加 `- reviewed:` 行。
- 預跑或 repo 執行出現紅燈基準以外的紅 ⇒ 停。
- 一次只跑一個代理（本機 8GB）；代理 brief 一律帶 HANDOFF §12-2 必禁清單。

## 5. 就緒審查紀錄

- **第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-04）：P2×2——(1) verifier 證據未規定 fines 欄位形狀，且錨點後首份 `kind: write` 證據無前例、預跑未測 W 證據路徑，代理若把證據路徑寫進 `sentences` 會被 W 判 FAIL，而預算無第二位 verifier；(2) repo 執行步驟 2、4、6 停下時無還原規定（10 條已審會無證據留在工作樹，使所有視窗 audit 紅），且無 `make audit` 基準。處置：兩項皆 **FIX**——§1 加「證據形狀」逐字 JSON 與 `notes` 欄位、預跑加合成證據正對照＋三負對照＋`extract` 往返與錯 base 負對照；§1 加「通用還原」涵蓋步驟 2、4、6 全部停下（含 HANDOFF 備份還原），預跑加 `make audit` 基準（OVERALL PASS）。送第 2 輪。
- **第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-04）：P2×1——預算停點排在寫入之後、派 verifier 之前，且不在「通用還原」適用範圍內，觸發時 10 條已審會無證據留在工作樹，與「正本 ⛔ 在未附證據的狀態下留過本回合」矛盾。第 1 輪 (1) 處置、證據形狀、base／trailer／commit 範圍、plan-meta、待驗宣稱經該輪核對無阻擋。⇒ **第二次自動 REVISE，停止重送、逐條處置**：**FIX**——預算閘移到寫入前（repo 執行步驟 0，含剩餘主 session 估算與 verifier 預留），寫入後不再有預算停點；「通用還原」改為涵蓋步驟 2 寫入後到 commit 前的任何停下、無例外（含 extract 失敗、hook 拒絕、§4 停止條件）；§4 同步改寫。依規則開一次收尾審查；再判 REVISE 就暫停交業主。
- **收尾審查（fresh plan-verifier）＝READY**（2026-10-04）⇒ 交業主核可（`next_gate: user_approval`）。就緒審查三輪合計約 0.17M（含主 session 預跑）。

## 6. 執行紀錄

### S1（2026-10-04）

- **業主裁決原文**（2026-10-04，對「請回覆：核可計畫＋終審原文」的回覆）：「安全組過，排除 contract-thinkcloud-signing-variants」——視為核可本計畫並終審：非 ⚠️ 組 pass 標已審（rule＝safe），排除 `jgb/D/contract-thinkcloud-signing-variants`；⚠️ 組 `A-account-profile` 與 doubt 本批不審。
- **寫入前預算閘**（步驟 0）：累計約 0.17M＋剩餘主 session 0.1M＋verifier 預留 0.3M＝0.57M ≤ 0.65M ⇒ 過閘。
- **derive**（真決定檔 `p923/p923-decision.json`、本計畫 §6）⇒ `approved 10 (both sources equal) by shelf {'C': 3, 'D': 4, 'I': 3}; expected endpoint increment pm +10, prospect +4`；核可清單與預跑 `synth-approved.json` `cmp` 相同。
- **備份與前置**：`scratchpad/p923-backup/`（canon 全樹＋`HANDOFF.bak`）與 repo `diff -r`／`cmp` 相同；`git diff --stat HEAD -- rag-orchestrator/canon` 與 status 皆空；其他工作線未 commit 檔 41 個（`git status --porcelain -z`，扣除本計畫檔）sha256 指紋存 `scratchpad/p923-foreign-fp.txt`，摘要 `7379139225332cc4`（正對照：`rag-orchestrator/services/agent/runtime.py` 在清單內）。
- **寫入與驗證**：`write` ⇒ `added 10`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 525 -> current 535; added lines 10; approved 10`、`reviewed fines pm 529, prospect 120`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；repo 正本與 scratch 預跑 `p923-pc/canon` `diff -r` 相同；`git status` 只有 C／D／I `.md` 與 `jgb.json`（A.md 無 diff）。
- **終點指標 `已審細目 pm 529／533、prospect 120／120；頁面 pm 140／183、prospect 53／183`**（pm +10、prospect +4，與預期相同）。
- **單元**：`scripts/run-tests.sh unit` ⇒ `passed=3931 failed=9`，紅燈集合與基準雙向差集＝∅（log `scratchpad/p923-unit-after.log`）。
- **HANDOFF**：開頭終點指標、一句話現況、開工順序第 2／5 步、§12-1 加 9.23 列、§12-4 未審細目段已更新。
- **`make audit`（派 verifier 前）**：與基準相比唯一差異＝不變量 43 `W 工作樹有 10 條細目新增已審或已審內容變動，卻沒有 base＝HEAD 的全數逐句核對證據`，其他各項同基準（log `scratchpad/p923-audit-prev.log`），符合步驟 4 預期。
- **成本（派 verifier 前）**：累計約 0.25M。以下由證據檔與 commit 訊息記錄（§1 步驟 6 註）。
- **fresh outcome verifier＝REFUTED**（10 個標題、55 句全數核對（`content_units` 合計：8 條 46＋兩條定價細目 9）；(2)～(5) 成立）：3 句不成立，皆為同一個範圍錯——
  - `jgb/I/pricing-free-trial-eligibility` 句 2「個人房東則是註冊過程沒有帶入優惠代碼時，才自動取得免費方案」、句 4「透過優惠代碼連結完成註冊，取得的是優惠代碼指定的方案」；
  - `jgb/I/pricing-free-vs-experience-plan` 句 1 括號「個人房東帶優惠代碼註冊時取得的是優惠方案」。
  - 實況：`app/User.php` Step4「給予房東初始方案」只在 `$promotion['type']=='registration_plan'` 時給優惠方案；後台優惠類型另有 `login_plan`（登入免費方案）、`plan_discount`（方案折扣）（`Admin/PromotionController.php`），帶這兩類代碼註冊的個人房東照樣拿到免費方案。主 session 對匯出確認 `User.php` 該條件與三種類型屬實。正式站是否有後兩類優惠屬資料面，未查。
  - 其餘 8 條（C 3、D 4、I `pricing-quota-full-block`）標題與每句皆成立。
- **依「通用還原」處置**：`rag-orchestrator/canon` 由 `p923-backup/canon` 還原、HANDOFF 由 `HANDOFF.bak` 還原；`diff -r`／`cmp` 相同，`git diff --stat HEAD` 與 status（canon＋HANDOFF）皆空，`load_canon_or_die` 539 條通過；終點指標回到 `已審細目 pm 519／533、prospect 116／120`；其他工作線 41 檔 `shasum -c` 全 OK。
- **驗收清單判定**（凍結檔 `scratchpad/p923-acceptance.md`，sha256 `717e5960…`）：A1 FAIL（未寫入）、A2 FAIL（證據 REFUTED）、A3 FAIL（指標 519／116）、A4 不適用 ⇒ **任務未完成**，停下交業主。
- **成本**：verifier 約 0.28M ⇒ 累計約 0.58M（上限 0.65M）。

### S1b（2026-10-04，8 條）

- **業主裁決原文**（2026-10-04，對「只寫入 8 條（建議）／先修兩條定價細目再一起寫入」與上限說明的回覆）：「別管上限 聚焦驗收成果」——採建議選項：只寫入 S1 已逐句成立的 8 條；上限 0.65M 不再作為停止條件（業主明示），停止條件只剩驗收結果。
- 決定檔：rule＝safe，排除 `jgb/D/contract-thinkcloud-signing-variants`、`jgb/I/pricing-free-trial-eligibility`、`jgb/I/pricing-free-vs-experience-plan`。預期 pm 519→527、prospect 116→118（plan-meta 已改）。兩條定價細目依 D1 修正與重審另案。
- 流程同 S1（備份 → write → 重匯出 → verify → 終點指標 → 單元 → HANDOFF → `make audit` 只剩 W → fresh outcome verifier 全數逐句核對 → extract → audit PASS → commit）；任一停下走「通用還原」。驗收清單另行凍結：`scratchpad/p923b-acceptance.md`。
- **derive**（`p923/p923b-decision.json`、`P918_PLAN_SECTION="### S1b"`）⇒ `approved 8 (both sources equal) by shelf {'C': 3, 'D': 4, 'I': 1}; expected endpoint increment pm +8, prospect +2`。
- **前置**：repo 正本與 HANDOFF 與 `p923-backup/` 仍 `diff -r`／`cmp` 相同（S1 還原後未動），canon status 空。
- **寫入與驗證**：`write` ⇒ `added 8`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 525 -> current 533; added lines 8; approved 8`、`reviewed fines pm 527, prospect 118`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`（排除的 3 條仍未審）；scratch 重生成 `已審保留：533 條／丟棄：0 條`，與 repo 正本 `diff -r` 相同；`git status` 只有 C／D／I `.md` 與 `jgb.json`。
- **終點指標 `已審細目 pm 527／533、prospect 118／120；頁面 pm 140／183、prospect 53／183`**（pm +8、prospect +2，與預期相同）。
- **單元**：`passed=3931 failed=9`，紅燈集合與基準雙向差集＝∅（`scratchpad/p923b-unit-after.log`）。
- **HANDOFF**：開頭終點指標、一句話現況、開工第 2／5 步、§12-1 加 9.23 列、§12-4 未審細目段。
- **`make audit`（派 verifier 前）**：與基準相比唯一差異＝不變量 43 `W 工作樹有 8 條細目新增已審或已審內容變動，卻沒有 base＝HEAD 的全數逐句核對證據`（`scratchpad/p923b-audit-prev.log`）。以下由證據檔與 commit 訊息記錄。
- **fresh outcome verifier（S1b 第 1 次）＝REFUTED**：8 條 8 個標題、46 句全數成立，(2)～(4) 成立；(5) 不成立 1 項——§6 S1 記「10 個標題、57 句」，正本 `content_units` 合計實為 55（P2，紀錄錯誤：主 session 照抄前一位 verifier 交件的句數、未對正本重算）；另 P3：開頭「本計畫預期」未反映 S1b 縮減。主 session 以 `jgb.json` 重算確認 55。
- **處置**：被推翻的是計畫紀錄、不是正本內容 ⇒ 正本不還原（內容與上次驗證時逐位元組相同）；改正 §6 S1 句數與開頭預期段，派新的 fresh outcome verifier 重驗全部宣稱（8 條逐句＋(2)～(5)）。
