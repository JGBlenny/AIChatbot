# Plan 9.28 驗收清單（凍結，2026-10-04）

> 計畫：`inputs/plan-9.28-stock-reverify-525-20261004.md`。依據：`goal-acceptance-spec-20261004.md` §2.2。
> 規格原文：「9.15～9.21 寫入的 525 條，全數逐句由 fresh verifier 對合法來源核對（jgb2 釘住匯出、幫助中心、事實帳本條目、業主審核單裁決——裁決句以該裁決文字判，⛔ 超出裁決）；證據同 9.23 §1 `kind: write` 形狀；不成立句依 D1（修一次或整句刪）並重審。」業主 2026-10-04：「好」。
> **縮小範圍（非目標）**：「不成立句依 D1 處置並重審」與業主抽查 30 句移到下一份計畫——處置對象要等本計畫結果才知道，且需業主逐條終審。本計畫已審細目 +0。

| # | 服務的原文 | 驗收 | 觀測點 | 證據 |
|---|---|---|---|---|
| A1 | 「9.15～9.21 寫入的 525 條」 | 24 批細目聯集恰＝現行已審 543 條扣除 p923／p924／p925 write 證據的 18 條，共 525 條、互斥；18 條證據的 `content_sha256` 與正本相同；每個粗目只出現在一批 | 指令重算（讀 `jgb.json`、三份證據、`decoy-manifest`） | 輸出 |
| A2 | 「全數逐句」 | 24 份批次證據（`verification/*-p928-B01.json`～`B24`）每條真細目的 `sentences` 長度＝正本 `content_units` 數，`content_sha256`、`title_text` 與正本相同；元素只有 "成立"／"不成立"；合計 525 條、1,442 句、525 個標題全數有判定 | 重跑 `aggregate.py`＋獨立腳本逐條比對 | 輸出 |
| A3 | 「由 fresh verifier」 | 每份批次證據由 `--extract` 從該批代理 transcript 取出（`source_transcript` 欄位存在）、代理自寫的 `base`＝派出時 HEAD；各 base 到 commit 的父之間 `rag-orchestrator/canon` 與 drafts 無變動 | `git diff <base> <父> -- …` | 輸出 |
| A4 | 「對合法來源核對」——放水偵測（正對照） | 24 批每批的誘餌改動句判「不成立」且該句 note 引用合法來源檔（非正本／證據路徑）；誘餌清單存於 `inputs/stock-reverify-9.28-decoys-20261004.json`，每項的原片段在來源細目該句恰出現一次、改後即與已核對事實矛盾；誘餌 id 與標題都不與正本既有細目相同；全部批次證據的 notes／findings 不引用禁讀位置 | `aggregate.py` 誘餌欄＋人讀誘餌清單 | 輸出 |
| A5 | 同上——抽查重核 | 抽查證據（`verification/*-p928-spotcheck.json`，獨立 fresh verifier）的 20 句＝`aggregate.py` 以種子 `20261012` 重算的抽樣；被推翻句數 ≤ 2（≥3 依計畫 §4 停），且只出現在彙整的 `spotcheck_overturned` 欄 | 重跑彙整＋比對 | 輸出 |
| A6 | 「證據同 9.23 §1 `kind: write` 形狀」 | 每份批次證據 `kind`＝"write"，`verdict` 與逐條判定一致，含 `base`、`claim`、`fines`（id／title／sentences／content_sha256／title_text／notes）；每條有「標題：」note、每句有「句 n：」note 且含來源檔名（或「同上」「無法判定」），每條至少一個合法來源檔 | JSON 結構檢查（`aggregate.py` 每批有效性＝本項） | 輸出 |
| A7 | 「不成立句依 D1 …」的前置——清單完整 | `inputs/stock-reverify-9.28-summary-20261004.json` 的批次標題不成立與句不成立清單，與 24 份證據逐條重算完全相同；抽查推翻另列 `spotcheck_overturned`；人讀版 `.md` 兩類分節列出，每項附細目 id、句序、正本原句、notes 理由，筆數與 JSON 相同 | 重算比對 | 輸出 |
| A8 | 作廢與暫停批如實揭露 | 彙整的每批 `valid`／`errors`／重做次數與 §6 紀錄一致；若有暫停批，該批細目列為「未補核」，進度數字只算有效批 | 對照 §6 與彙整 | 輸出 |
| A9 | 不動正本（+0） | `rag-orchestrator/canon/`、drafts 與 HEAD 位元組相同；端點指標仍為 pm 537／537、prospect 121／121 | `git diff`＋`endpoint_progress.py` | 輸出 |
| A10 | repo 公開——不洩客戶名 | 本計畫 commit 範圍內全部代理產物——24 份批次證據、抽查證據、change 證據、加了抽查欄後的兩份彙整——以 `scan_names.py`（詞表＝`canon_check.py` `PAT`）掃描 0 命中，內建正負對照通過；掃描發生在抽查之後（9b）與 change 證據取出之後（10） | 指令（outcome verifier 驗 change 以外各檔；change 證據由主 session 取出後掃描、結果寫入 commit 訊息） | 輸出 |
| A11 | 規則 P：+0 需業主同意 | commit 內 plan-meta 的 `consent_zero` 與業主核可回覆原文逐字一致且為對 +0 的同意 | 對照原文與 `git show HEAD:<計畫>` | 原文＋輸出 |
| A12 | 不碰他線、無回歸 | 他線 41 檔指紋前後相同；全套 unit 紅燈與基準差集＝∅；`make audit` OVERALL PASS | 指令 | 輸出 |
| A13 | 可重現 | `review_pipeline/stock_reverify/` 八檔與 `.agents/` 鏡像相同；以這些檔在 scratch 重新產生的批次、brief 清單（id 集合）與抽查 20 句與本次相同 | `cmp`＋重跑 | 輸出 |
