# Plan 9.27 驗收清單（凍結，2026-10-04）

> 計畫：`inputs/plan-9.27-goal-eval-freeze-and-guard-20261004.md`。依據規格：`goal-acceptance-spec-20261004.md` v6 §3 第 1 步。
> 業主原話（本計畫所服務）：「你要不要先定義 寫成驗收規格 在派代理驗」「修完直接進入填 §5」。規格 §3 第 1 步原文：「凍結：各門檻、抽查種子、H 題 id 與雜湊、判準版本、容忍帶公式；售前適用清單（業主逐項裁）；新增 H 全體 196 題的機械守護並過正對照；在定義檔 §0 第 1、4 項標『已由 2026-10-04 裁決取代，見本規格』。」
> 本計畫已審細目 +0（不動正本）。

| # | 服務的原文 | 驗收 | 觀測點 | 證據 |
|---|---|---|---|---|
| A1 | 「H 題 id 與雜湊」 | 凍結檔列 196 題，每題 `id`／`split`／`audience`／`form`／`q_sha256` 與 `inputs/ruler-9.13-index.json` 逐欄相同；不含 `ce2ce3372c6e`；計數 holdout 99、material 97、業者 193、售前 3；檔內無任何題目文字 | 指令重算（讀索引與凍結檔比對；對 `questions.json` 每題文字做 ≥8 字子字串掃凍結檔＝0 命中） | 指令輸出 |
| A2 | 「抽查種子」「判準版本」「容忍帶公式」 | 凍結檔含七個種子（值與計畫 §1 第 2 步相同），規格每一個隨機抽樣步驟（完整性種入 10、業主抽查 20 件、30 句、L1 (ii) 30、L2 30、L1 一致性 40、L3 判者 20）都對到一個種子，不需種子的步驟（H gold 雙判、L3 種入 20 則、N）列明理由；規格檔 sha256 與 commit 內規格檔實際 sha256 相同、容忍帶公式字串（基線 Wilson 95% 半寬）、`questions.json` sha256 `15333e1429575d1547ec929da26f525dc0bcbba627007648ee4a7e1701a1100f` | `shasum -a 256` 與 JSON 讀值 | 指令輸出 |
| A3 | 「各門檻」 | 規格 §5 已填門檻（覆蓋業者 ≥95%、售前 ≥90%；L1 ≥90%、L2 ≥80%、L3 ≥85%、端到端 ≥70%）原樣存在於 commit 內規格檔，並被凍結檔的規格 sha256 鎖住 | 讀規格 §5＋A2 雜湊 | 指令輸出 |
| A4 | 「新增 H 全體 196 題的機械守護並過正對照」——(a) | 對現行正本執行守護（不帶基準）恰重現 2 筆：`8cce4b057f46`×`jgb/D/contract-list-export-declaration`×body、`71c32e1c3d67`×`jgb/E/balance-invoice-refund-report-column`×title | 主機實跑守護 | 輸出（只含 id） |
| A5 | 同上——(b) | holdout 一題、material 一題各取 ≥8 字片段，分別種入**標題**副本與**內文**副本（scratch），四組守護皆 FAIL 且輸出指出該題 id 與該欄位 | 主機實跑守護於副本 | 輸出 |
| A6 | 同上——(c) | 一題整句種入**講法**副本，守護 FAIL 且輸出標示整句雜湊路徑 | 同上 | 輸出 |
| A7 | 同上——(d) | 兩筆依業主裁定處置後（放行者入基準檔），守護對現行正本 PASS；若有一筆被裁為洩題，本項改判「守護維持 FAIL、已記 §6、修正本另案」，本計畫照停止條件處理 | 主機實跑守護 | 輸出＋業主裁定原文 |
| A8 | 同上——大聲失敗 | 指向不存在或 sha256 不符的 `questions.json`、或 0 個正本檔時，守護非 0 退出並印原因 | 實跑 | 輸出 |
| A9 | 同上——不洩題 | 守護所有輸出（含 FAIL 與 self-test）不含任何題目原文或共同子字串：對 A4～A8 的全部輸出做 ≥8 字子字串掃 196 題＝0 命中 | 指令掃描 | 輸出 |
| A10 | 同上——自證 | `--self-test` 通過；單元測試全綠；兩個變異（停用子字串比對、停用基準扣除）各使對應測試紅，repo 檔不變 | pytest＋變異實跑 | 輸出 |
| A11 | 同上——接進 `make audit` | `check_invariants.sh` 含新守護區塊；區塊層兩組反證（scratch，repo 檔不變）：(1) 把該區塊抽出、守護路徑換成會對種入副本報 FAIL 的包裝後執行，結束時 `FAIL=1` 且 `CODE_REGRESSIONS` 含新不變量條目；(2) 換成 `--self-test` 必失敗的副本後執行，同樣 `FAIL=1` 且有條目；放回原狀後主機 `make audit` OVERALL PASS 且輸出可見新守護 PASS 行 | 區塊實跑＋`make audit` | 輸出 |
| A12 | 「售前適用清單（業主逐項裁）」 | `inputs/prospect-applicability-proposal-20261004.md` 57 個粗目每列都有業主裁定欄，與業主回覆原文一致；粗目集合＝`rag-orchestrator/canon/jgb.json` 的 57 個 `coarses[].id` | 指令比對 | 輸出＋業主原文 |
| A13 | 「在定義檔 §0 第 1、4 項標『已由 2026-10-04 裁決取代，見本規格』」 | 定義檔 §0「任務與驗收」第 1、4 項各恰多一句取代標註並指向規格；檔案其餘位元組不變（與備份 diff 只有這兩處） | `diff` | 輸出 |
| A14 | 不動正本（+0） | `rag-orchestrator/canon/`、drafts、CATALOG 與 HEAD 位元組相同；端點指標仍為 pm 537／537、prospect 121／121 | `git diff --stat`＋`endpoint_progress.py` | 輸出 |
| A15 | 不碰他線 | 他線未 commit 檔 sha256 指紋步驟 0 前後相同（正對照 `runtime.py` 在清單內） | `shasum` 比對 | 輸出 |
| A16 | 全套回歸 | 全套 unit 失敗集合與步驟 0 基準差集＝∅；收集清單含 `rag-orchestrator/tests/unit/audit/test_goal_eval_holdout_guard_req.py` | pytest（含 `--collect-only` 對照） | 輸出 |
| A17 | 規則 P：+0 需業主同意 | commit 內 plan-meta 的 `consent_zero` 與業主核可回覆原文逐字一致，且內容是對本計畫 +0 的同意；不符 ⇒ 不 commit | 對照業主訊息原文與 `git show HEAD:<計畫>` | 原文＋輸出 |
| A18 | 規格 §2.4「每次寫入正本前與主機上的 `make audit` 都跑」 | `review_pipeline/README.md` 與 `.agents/` 鏡像的「寫入前」步驟含守護指令與「非 0 ⇒ ⛔ 寫入」；兩份 diff 相同 | grep＋diff | 輸出 |
| A19 | 規格 §2.4「實作時在其註解補一句指向本規格」 | `canon_phrasing_frozen_disjoint.py` 與備份的差異只在 docstring 一句；不變量 34 self-test 與主檢查結果不變 | diff＋實跑 | 輸出 |

**不在範圍（非目標）**：存量補核 525 條、覆蓋表、效果量測、修正本——規格 §3 第 2～4 步，後續計畫。
