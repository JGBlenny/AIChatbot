<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「Approved, agree this plan is +0 (Recommended)」
-->
# Plan 9.27：目標驗收規格執行第一步——凍結、留出題守護、售前適用清單（+0）

> **現況**（2026-10-04，HEAD `9618129c`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`（`--closure`）。
>
> **本計畫預期**：已審細目 **+0**（不動正本）。產出＝執行目標驗收規格（`../goal-acceptance-spec-20261004.md` v6）所需的前置：凍結檔、H 196 題機械守護、售前適用清單（業主裁定）、定義檔標註。`consent_zero` 目前為佔位（含「待」，`outline_plan_discipline.py::CONSENT_BAD` 會擋 commit）；**業主核可本計畫時須明示同意 +0**，其逐字原文替換此欄；核可回覆沒有對 +0 的明示同意 ⇒ ⛔ commit、停下交業主（驗收 A17）。
>
> **為什麼值得做這份 +0**（9.26 亦為 +0，本份是連續第二份）：規格 §3 第 2～4 步（補核、覆蓋、補缺口、效果量測）全都依賴本計畫的產物——補缺口會寫正本，規格 §2.4 要求守護在**每次寫入正本前**就位，否則補內容時無法機械證明沒有把 H 題寫進正本；種子與 H 題雜湊不在量測前凍結，之後任何量測都可被質疑看結果再挑。本計畫不做，下一份 +N 計畫無法合規開工。
>
> **驗收清單（凍結）**：`.kiro/specs/knowledge-outline-and-intent-architecture/acceptance-9.27-20261004.md`。

## 0. 為什麼有這份

- 規格 §3 第 1 步：「凍結：各門檻、抽查種子、H 題 id 與雜湊、判準版本、容忍帶公式；售前適用清單（業主逐項裁）；新增 H 全體 196 題的機械守護並過正對照；在定義檔 §0 第 1、4 項標『已由 2026-10-04 裁決取代，見本規格』。」
- 業主 2026-10-04「修完直接進入填 §5」並已填 §5（門檻、額度 30M token／L3 US$5、抽查業主本人）；問「所以是? 等我確認？」——主 session 答：直接寫本計畫，下一個業主關卡是核可。

## 1. 切片：只有 S1（一次 commit）

1. **步驟 0 基準**：HEAD 全碼；`make audit` 基準；他線未 commit 檔 sha256 指紋 `scratchpad/p927/foreign-fp.txt`（正對照 `runtime.py`）；備份執行中會改到的既有檔到 `scratchpad/p927-backup/` 並逐一 `cmp`：定義檔、HANDOFF、`inputs/prospect-applicability-proposal-20261004.md`（未追蹤）、`.claude/skills/outline-curation/scripts/review_pipeline/README.md` 與 `.agents/` 鏡像、`scripts/audit/checks/canon_phrasing_frozen_disjoint.py`。
2. **凍結檔** `inputs/goal-eval-freeze-20261004.json`（repo 內只放 id、雜湊、計數，⛔ 題目文字）：H 196 題的 `id`／`split`／`audience`／`form`／`q_sha256`（來自 `inputs/ruler-9.13-index.json`，排除 `ce2ce3372c6e`）；規格檔 sha256（判準版本＝該雜湊）；六個抽樣種子固定為：完整性種入 10 件 `20261004`、業主抽查 20 件 `20261005`、業主抽查 30 句 `20261006`、L1 正對照 (ii) 30 條 `20261007`、L2 正對照 30 條 `20261008`、L1 一致性 40 題 `20261009`、L3 判者另 20 題雙判 `20261010`（Python `random.Random(seed)`）；凍結檔另列規格中**不需種子**的步驟與理由：H gold 雙判（H 全體）、L3 種入 10＋10 則（人工構造、非抽樣）、N（全體 184）；容忍帶公式（基線 Wilson 95% 半寬）；`questions.json` sha256（`15333e14…100f`）。
3. **H 留出題守護** `scripts/audit/checks/goal_eval_holdout_guard.py`（新檔；不在 `.claude/settings.json` 鎖定清單內）：
   - 讀凍結檔的 196 個 `q_sha256` 與 repo 外 `~/jgb-archive/ruler-9.13/questions.json`（sha256 不符或讀不到 ⇒ FAIL 並印原因）；對正本 `rag-orchestrator/canon/*.json`（現為 `jgb.json` 一檔；掃到 0 檔 ⇒ FAIL）每條細目的 `title`、`phrasings[].text`、`content_units[]` 做 (i) `hash_norm` 整句比對（同不變量 34）＋ (ii) NFKC、去空白後 ≥8 字最長共同子字串（同 Plan 9.14）；扣除基準檔 `inputs/goal-eval-guard-baseline-20261004.json` 的（題 id, 細目 id, 欄位）後有命中 ⇒ FAIL。
   - 輸出只印題 id、細目 id、欄位、共同長度（⛔ 題目或子字串）。
   - `--self-test`：合成資料驗整句、片段×標題、片段×內文三路都能抓、基準扣除生效、缺原文時 FAIL。
   - 參數 `--questions`／`--canon`／`--freeze`／`--baseline` 可覆寫（供測試與副本正對照）。
4. **單元測試** `rag-orchestrator/tests/unit/audit/test_goal_eval_holdout_guard_req.py`（與既有 `test_canon_invariants_req.py` 同目錄，會被全套 unit 收集；只用合成資料、⛔ 讀 `~/jgb-archive`——規格「⛔ 註冊進容器內 pytest」限制的是守護本身對真題的掃描，不是合成資料單元測試）（合成資料，不讀 `~/jgb-archive`）＋變異（停用子字串比對 ⇒ 片段測試紅；停用基準扣除 ⇒ 基準測試紅；scratch 副本掛載，repo 檔不變）。
5. **首跑與正對照**（規格 §2.4 守護驗收）：
   - (a) 對現行正本首跑須重現 `8cce4b057f46`／內文、`71c32e1c3d67`／標題，少一筆 ⇒ 守護不可用、停。
   - (b) holdout 一題、material 一題各取 ≥8 字片段，分別種入標題副本與內文副本（scratch），四組皆須 FAIL；(c) 整句種入講法副本須 FAIL。
   - 兩筆首跑命中**交業主逐筆裁**（產品用語放行 ⇒ 寫入基準檔；洩題 ⇒ 另案修正本、本計畫不動正本，守護在修好前維持 FAIL 並記 §6）。
   - (d) 裁定後對現行正本 PASS。
6. **接進 `make audit`**：須在 `scripts/audit/check_invariants.sh` 加一個不變量區塊（比照不變量 34 的寫法，只在主機執行）。該檔受 `.claude/settings.json` 權限規則保護（Edit 拒絕）⇒ **業主二擇一**：暫時解除該規則讓主 session 加區塊後再上鎖，或由主 session 提供補丁、業主親手套用。未接上前本計畫不收案。區塊寫法比照不變量 34：self-test 失敗 ⇒ `FAIL=1`＋`CODE_REGRESSIONS+=`；守護非 0 ⇒ `FAIL=1`＋`CODE_REGRESSIONS+=`。
6b. **寫入前程序**：在 `review_pipeline/README.md`（含 `.agents/` 鏡像）「寫入前」步驟加一句：跑 `python3 scripts/audit/checks/goal_eval_holdout_guard.py`，非 0 ⇒ ⛔ 寫入。
6c. **不變量 34 註解**：在 `canon_phrasing_frozen_disjoint.py` 模組 docstring 補一句「H 的 material 97 題另由 `goal_eval_holdout_guard.py` 守（目標驗收規格 2026-10-04 裁決 8），本檢查語義不變」；只動註解。
7. **售前適用清單**：`inputs/prospect-applicability-proposal-20261004.md`（57 粗目：提議適用 53、不適用 4 並附理由）**交業主逐項裁**，裁定後在檔內標註並凍結（檔名不變）。
8. **定義檔標註**：`inputs/definitions-outline-baseline-20260919.md` §0 第 1、4 項各加一句「⚠️ 已由 2026-10-04 業主裁決取代，見 `../goal-acceptance-spec-20261004.md` §0」。
9. **文件**：HANDOFF 開頭一句話現況與開工第 2 步指向規格與本計畫；§12-1 加 9.27 列。
10. **驗證與 commit**：全套 unit 差集 ∅；`make audit` OVERALL PASS（含新不變量）；fresh outcome verifier（`kind: change`，BRIEF-CONTRACT v1，含驗收清單）；`--extract` ⇒ commit（`Verified-by`）。
- **commit 範圍**：規格 `goal-acceptance-spec-20261004.md`、本計畫、驗收清單、`inputs/goal-eval-freeze-20261004.json`、`inputs/goal-eval-guard-baseline-20261004.json`、售前適用清單、`scripts/audit/checks/goal_eval_holdout_guard.py`、`rag-orchestrator/tests/unit/audit/test_goal_eval_holdout_guard_req.py`、`check_invariants.sh`（業主套用或解鎖後）、`canon_phrasing_frozen_disjoint.py`（只註解）、`review_pipeline/README.md` 兩份、定義檔、HANDOFF、證據檔。
- **還原**：commit 前任何停下 ⇒ (1) 從 `p927-backup/` 還原步驟 0 備份清單內的檔並 `cmp`；(2) 只刪除**本計畫執行時才建立**的檔：凍結檔、基準檔、守護腳本、測試檔、證據檔（`verification/20261004-p927-change.json`）；⛔ 刪除執行前已存在的未追蹤檔（規格、本計畫、驗收清單、售前提議）；兩份清單互斥、合起來涵蓋所有會碰到的檔；(3) `check_invariants.sh` 若已改，由業主還原或解鎖後還原 ⇒ 停、交業主。commit 後驗收 FAIL ⇒ ⛔ 改寫歷史、回報業主。

## 2. 不做（後續計畫）

- 存量補核 525 條（規格 §2.2，下一份計畫，約 13M token）。
- 覆蓋表、可問的事清單、I 架「不支援」細目（規格 §2.1）。
- 效果量測 L1～L3（規格 §2.4）。
- 修正本（若首跑命中被裁為洩題，另案）。

## 3. 業主裁決與待裁

- **已裁**：規格 v6 §0（12 項）與 §5。
- **待裁（核可時一併回覆）**：(a) 本計畫，並明示同意 +0；(b) `check_invariants.sh` 二擇一（暫時解鎖／業主親手套用補丁）；(c) 售前適用清單逐項（可整批「照提議」或標出改判）；(d) 首跑 2 筆命中逐筆裁定在步驟 5 執行時另交。

## 4. 停止條件

- 正本、drafts 任何變動 ⇒ 停。
- 業主核可回覆沒有對本計畫 +0 的明示同意 ⇒ ⛔ commit、停下交業主。
- 首跑未重現 2 筆已知命中、任一正對照未 FAIL、單元差集非 ∅、`make audit` 非 PASS ⇒ 依 §1 還原並停。
- 額度：本計畫代理用量計入規格 §5 的 30M 總上限；本計畫估約 1M（就緒審查＋outcome verifier）。

## 5. 就緒審查紀錄

- **預跑**（2026-10-04，scratch `p927/preflight_guard.py`，只印 id）：H＝196（holdout 99＋material 97，排除 `ce2ce3372c6e`；業者 193、售前 3），196 題原文 `hash_norm` 全數對上索引 `q_sha256`；掃 3,817 個欄位，命中恰 2 筆＝`71c32e1c3d67`／`jgb/E/balance-invoice-refund-report-column`／title／8、`8cce4b057f46`／`jgb/D/contract-list-export-declaration`／body／8，整句雜湊命中 0。

- **第 1 輪**（fresh plan-verifier）：REVISE，P2×6，全數 FIX——(1) consent_zero 用非 +0 同意的原話佔位 ⇒ 改「待…」佔位（CONSENT_BAD 會擋）＋A17＋停止條件＋說明為何值得做 +0；(2) A11 推翻不了區塊接線 ⇒ A11 改兩組區塊層反證；(3) 漏寫入前程序與不變量 34 註解 ⇒ 新增 6b、6c 與 A18、A19；(4) 漏 L3 判者 20 題種子 ⇒ 第 7 個種子＋不需種子清單；(5) 測試路徑錯（`scripts/audit/checks/test_*` 0 筆，正對照 `rag-orchestrator/tests/unit/audit/test_canon_invariants_req.py` 存在）⇒ 改正；(6) 還原未備份售前提議、刪除範圍未界定 ⇒ 備份清單與刪除清單逐一列名、互斥。
- **第 2 輪（收尾）**（fresh plan-verifier）：**READY**。

## 6. 執行紀錄

- **業主核可**（2026-10-04，AskUserQuestion 逐字）：核可「Approved, agree this plan is +0 (Recommended)」；權限鎖「I'll apply the patch myself (Recommended)」（業主親手套用補丁）；售前清單「As proposed, but A-account-profile applies (Recommended)」（適用 54、不適用 3）；2 筆命中於步驟 5 另交。
- **步驟 0**：HEAD `9618129c49d7b2fea744dd35b8a7ac70b6cd2a6e`；`make audit` 基準唯一紅燈＝不變量 43「P 預期 +0 卻沒有有效的業主原文 consent_zero」（佔位被擋，正對照符合預期），填入業主原文後重跑見下；他線未 commit 檔 41 個指紋 `scratchpad/p927/foreign-fp.txt`（正對照含 `runtime.py`，路徑集合與 9.26 相同）；備份 `scratchpad/p927-backup/` 七檔逐一 `cmp` 相同。填入業主原文後 `make audit` OVERALL PASS（`scratchpad/p927/audit-baseline2.log`）；全套 unit 基準 9 紅，與 9.26 紅燈集合相同（`scratchpad/p927/red-base.txt`）。
- **凍結檔**：`inputs/goal-eval-freeze-20261004.json`——196 題（holdout 99、material 97；業者 193、售前 3；verbatim 59、summary 137），七個種子、三項不需種子的理由、容忍帶公式、規格／索引／題目原文 sha256。
- **守護**：`scripts/audit/checks/goal_eval_holdout_guard.py`，`--self-test` 11/11；單元 `rag-orchestrator/tests/unit/audit/test_goal_eval_holdout_guard_req.py` 7 passed；變異（scratch 副本掛載覆蓋 `/scripts/…`，repo 檔 sha256 不變）：停用子字串比對 ⇒ 5 紅（含執行期正對照擋下）、停用基準扣除 ⇒ 2 紅（`test_baseline_allows_only_exact_triple`、`test_self_test_passes`）。
- **步驟 5**：(a) 不帶基準首跑恰 2 筆＝`71c32e1c3d67`×`jgb/E/balance-invoice-refund-report-column`×title×8、`8cce4b057f46`×`jgb/D/contract-list-export-declaration`×body×8；(b) holdout `01e5118a1410`、material `040a7e9fdbc0` 片段種入標題副本／內文副本四組皆 rc=1 且指出該題與欄位；(c) material 整句種入講法副本 rc=1、含 `× phrasing × hash`；全部輸出洩題 8 字片段 0（`scratchpad/p927/plant.log`）。業主裁定（AskUserQuestion 逐字）：命中 1「產品用語，放行 (Recommended)」、命中 2「產品用語，放行 (Recommended)」⇒ 寫入 `inputs/goal-eval-guard-baseline-20261004.json`；(d) 對現行正本 PASS（基準放行 2、新命中 0）。
- **步驟 6**：補丁 `scratchpad/p927/inv44.patch`（不變量 44 區塊，插在不變量 43 區塊之後、不動 43 的釘住內容；`git apply --check` 通過）。區塊層反證（scratch 抽出區塊執行）：守護換成指向種入副本的包裝 ⇒ `FAIL=1`、`CODE_REGRESSIONS` 1 筆（不變量 44 條目）；換成 self-test 必失敗的副本 ⇒ `FAIL=1`、1 筆（自我測試未過條目）。待業主親手套用。
- **6b／6c／8**：`review_pipeline/README.md` 兩份「寫入前」加守護一句（兩份相同）；`canon_phrasing_frozen_disjoint.py` 只在 docstring 補 2 行，不變量 34 self-test 與主檢查結果不變；定義檔 §0 第 1、4 項各加一句取代標註。
- **7**：售前清單加「業主裁定」欄，`A-account-profile` 改判適用 ⇒ 適用 54、不適用 3。
