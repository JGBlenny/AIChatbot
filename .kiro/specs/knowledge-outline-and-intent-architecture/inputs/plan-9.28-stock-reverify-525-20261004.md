<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「核可，同意本計畫 +0 (Recommended)」
-->
# Plan 9.28：目標驗收規格第 2 步——存量 525 條逐句補核（+0）

> **現況**（2026-10-04，HEAD `77464446`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`。
>
> **本計畫的進度單位**：規格第 2 項（內容）的「存量補核」——**已補核細目 0／525 → 525／525**，並列出全部不成立句。已審細目數 **+0**（本計畫不動正本）。`consent_zero` 目前為佔位（含「待」，`outline_plan_discipline.py::CONSENT_BAD` 會擋 commit）；業主核可時須明示同意 +0，其逐字原文替換此欄；沒有 ⇒ ⛔ commit、停下交業主。
>
> **為什麼值得做這份 +0**（連續第三份 +0）：規格第 2 項的達成條件是「補核全數成立或不成立句已處置並重驗」；9.15～9.21 寫入的 525 條寫入後只抽驗，9.22 的全數核對證明抽驗會放過錯句（11 條抓到 1 句）。不先補核，就不知道已審內容裡有多少錯句，後續覆蓋與效果量測都建立在未驗證的內容上。
>
> **驗收清單（凍結）**：`.kiro/specs/knowledge-outline-and-intent-architecture/acceptance-9.28-20261004.md`。

## 0. 依據

- 規格 `../goal-acceptance-spec-20261004.md` §2.2：「9.15～9.21 寫入的 525 條，全數逐句由 fresh verifier 對合法來源核對（jgb2 釘住匯出、幫助中心、事實帳本條目、業主審核單裁決——裁決句以該裁決文字判，⛔ 超出裁決）；證據同 9.23 §1 `kind: write` 形狀；不成立句依 D1（修一次或整句刪）並重審。」
- 業主 2026-10-04 對「下一步是存量 525 條補核，要開始的話先寫計畫、送就緒審查、再交您核可」回覆「好」。
- 525 條＝現行已審 543 條扣除已有寫入後全數核對證據的 18 條（`verification/20261004-p923-write.json` 8、`-p924-write.json` 6、`-p925-write.json` 4；三檔記錄的 `content_sha256` 與現行正本全數相同，預跑已核）。共 1,442 句＋525 個標題。

## 1. 切片：只有 S1（一次 commit）

1. **步驟 0 基準**：HEAD 全碼；`make audit` 基準；他線未 commit 檔 41 個 sha256 指紋（正對照 `runtime.py`）；全套 unit 紅燈基準（9 條）；備份 HANDOFF；`rag-orchestrator/canon/` 備份並 `diff -r` 相同；jgb2 釘住匯出 `scratchpad/jgb2-b2ee2ac` 存在（缺則依 `review_pipeline/README.md` 重建）。
2. **批次**（`stock_reverify/make_batches.py`，機械產生）：依正本順序以粗目為單位不拆，每批累計 ≤70 句（單一粗目超過即自成一批）⇒ 24 批（B01～B24；4～33 條、36～100 句）；聯集＝525 條、互斥。
3. **誘餌（正對照）**：每批混入 1 條誘餌——取已全數核對的 18 條之一，恰改一句的關鍵事實（數字、引號標籤、行為），清單 `stock_reverify/decoys.py`（24 項）。誘餌 id 與標題逐項手寫，`gen_briefs.py` 斷言兩者都不與正本既有細目相同；排序讓誘餌的架儘量與該批相同（A→B01～B05、C→B06～B09、D→B10～B14）；插入位置以種子 `20261011+批號` 決定。誘餌只存在於 brief，不進正本。
4. **brief**（`stock_reverify/gen_briefs.py` 由 `jgb.json` 機械產生，模板 `stock_reverify/brief-template.txt`）：逐字列出每條的標題、句子、sources、`content_sha256`；合法來源位置與判定規則沿用 9.19 先審 brief（現行 vs 舊路徑、加引號介面文字逐字、絕對句漏例外、來源衝突以程式為準、裁決句不得超出裁決、無法判定 ⇒ 不成立）；輸出＝單一 ```json 區塊、`kind: write` 形狀（同 9.23 §1：`title`／`sentences` 只能是 "成立"／"不成立"，證據寫 `notes`）；notes 標題一則、每句一則並寫來源檔名（同檔可寫「同上」，每條至少一個檔名）；notes 與 findings 中的客戶或團隊名一律寫「特定合作團隊」；**只准讀合法來源**——⛔ 讀 `rag-orchestrator/`（含正本）、`.claude/`、`.agents/`、`.kiro/`（sources 明列的審核單除外）、`docs/` 中事實帳本以外的檔、`/private/tmp/` 中 jgb2 匯出以外的檔；HANDOFF §12-2 必禁清單。內容一律以 brief 逐字列出者為準。
5. **執行**：一次一位 fresh verifier（本機 8GB），依序 B01→B24。每批交件後 `outline_plan_discipline.py --extract <transcript> verification/<日期>-p928-<批號>.json --base <派出時 HEAD>`，再跑 `stock_reverify/aggregate.py` 判該批有效性：
   - 有效（逐項涵蓋驗收 A6）＝`kind`＝"write"；`verdict` 與逐條判定一致（任一不成立 ⇒ REFUTED）；細目集合恰為該批＋誘餌；每條真細目句數與 `content_sha256`／`title_text` 與正本相同；元素皆為 "成立"／"不成立" 字串；每條有「標題：」note、每句有「句 n：」note 且含來源檔名（或「同上」「無法判定」），每條至少引用一個合法來源檔；全部 notes／findings 不得引用禁讀位置（正本、drafts、`verification/`、brief、誘餌清單）；**誘餌改動句判「不成立」且 note 引用合法來源檔**。
   - 交件格式不合（上列任一結構項）⇒ SendMessage 請該代理重貼一次；仍不合 ⇒ 換一位 fresh verifier 重做該批一次；再不合 ⇒ 該批標「暫停」。引用禁讀位置 ⇒ 不重貼，直接換人重做一次。
   - 誘餌漏抓或判不成立卻沒引來源 ⇒ 該批作廢，換一位 fresh verifier（同 brief）重做一次；再失敗 ⇒ 該批標「暫停」，其餘批照跑，收尾回報業主。
6. **彙整**：`aggregate.py` 產出 `inputs/stock-reverify-9.28-summary-20261004.json`（每批有效性、base、誘餌結果；逐條結果；標題不成立與句不成立清單附 notes）與人讀版 `inputs/stock-reverify-9.28-summary-20261004.md`（不成立清單逐條附正本原句與理由，供下一份計畫依 D1 處置）。誘餌清單存 `inputs/stock-reverify-9.28-decoys-20261004.json`。
7. （客戶名掃描移到第 9 步之後，見第 9b、10 步。）
8. **文件**：HANDOFF 一句話現況、開工第 2 步、§12-1 加 9.28 列。
9. **抽查（偵測放水，不取代全數核對）**：`aggregate.py --sample-out` 以種子 `20261012` 從有效批判「成立」的句子抽 20 句 ⇒ 派一位 fresh「抽查 verifier」（`stock_reverify/gen_spot.py`＋`spot-template.txt` 產生 brief：逐字列出 20 句與所屬細目標題、sources，⛔ 告知批次判定；合法來源、判定規則、禁讀與 Hard rules 與批次 brief 逐字相同；note／findings 的客戶或團隊名一律寫「特定合作團隊」）⇒ 交 ```json（`kind: change`、`verdict`、`base`、`claim`、`sample`: [{id, n, verdict, note}]）⇒ `--extract` 存 `verification/<日期>-p928-spotcheck.json` ⇒ `aggregate.py --spotcheck` 把推翻句放進彙整的**獨立欄** `spotcheck_overturned`（批次不成立清單不變）。推翻 ≥3 句 ⇒ 依 §4 停；抽查證據結構不合 ⇒ 重貼一次、再不合換人一次。
9b. **客戶名掃描（一）**：`stock_reverify/scan_names.py`（詞表逐字取自 `canon_check.py` 的 `PAT`，內建正負對照，對照失敗退出 2）掃 24 份批次證據、抽查證據、加了抽查欄後的兩份彙整；命中 ⇒ 證據是代理原文、⛔ 主 session 改寫 ⇒ 停下交業主。
10. **驗證與 commit**：全套 unit 差集 ∅；`make audit` OVERALL PASS；fresh outcome verifier（`kind: change`，BRIEF-CONTRACT v1，含驗收清單）驗**最終位元組**：重跑彙整（含抽查欄）、核對每份證據的 base 與正本未變、核對 A1～A13；brief 同樣要求 notes／findings 的客戶或團隊名一律寫「特定合作團隊」。待驗宣稱寫明「抽查推翻 x 句（≤2）且只列在 `spotcheck_overturned`」，推翻 1～2 句不影響其判 CONFIRMED；判 REFUTED ⇒ 不 commit、依還原停下交業主。`--extract` 存 `verification/<日期>-p928-change.json` ⇒ **客戶名掃描（二）**：`scan_names.py` 掃 `git diff --cached --name-only` 內全部 `verification/*-p928-*.json` 與兩份彙整（含 change 證據），命中 ⇒ 停下交業主 ⇒ commit（`Verified-by` 指向此檔）。
- **commit 範圍**：本計畫、驗收清單、HANDOFF、24 份批次證據、抽查證據、outcome 證據、四份 `inputs/stock-reverify-9.28-*`（彙整 JSON／md、誘餌清單、重做清單，後者為 outcome 驗證 A8 後由業主核可補上）、`.claude/skills/outline-curation/scripts/review_pipeline/stock_reverify/` 八檔（`make_batches.py`、`decoys.py`、`gen_briefs.py`、`brief-template.txt`、`aggregate.py`、`gen_spot.py`、`spot-template.txt`、`scan_names.py`）與 `.agents/` 鏡像。`git diff --cached --name-only` 須恰為此清單。
- **還原**：本計畫不寫正本；commit 前停下 ⇒ HANDOFF 以備份 `cp` 還原並 `cmp`，已取出的證據與彙整留在工作樹（未追蹤、不影響 `make audit`），記 §6、停下交業主。

## 2. 不做（後續計畫）

- **不成立句的處置**（D1 修一次或整句刪 → 重審 → 業主終審 → 寫入＋`kind: write` 證據）：規格 §2.2 的後半。理由：數量與內容要等本計畫結果才知道，且需業主逐條終審，另立計畫（9.24 範本）。
- 業主抽查 30 句（規格 §2.2，種子 `20261006`）：處置完再抽，否則會抽到待修的句子。
- 覆蓋表、效果量測（規格 §2.1、§2.4）。

## 3. 業主裁決與待裁

- **已裁**：規格 v6 §0、§5；業主「好」（開始存量補核）。
- **待裁（核可時回覆）**：本計畫，並明示同意 +0。

## 4. 停止條件與額度

- 正本、drafts 在執行期間任何變動 ⇒ 停（每批派出前與彙整前 `git diff --stat <步驟 0 HEAD> -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 須空，工作樹亦然）。
- 作廢或暫停批數 > 6（25%）⇒ 停，交業主（驗證方式本身不可靠）。
- 抽查 20 句中有 ≥ 3 句被推翻（批次判成立、抽查判不成立）⇒ 停，交業主；1～2 句 ⇒ 只列在彙整的 `spotcheck_overturned` 獨立欄（下一份計畫一併處置），照常收尾。
- **額度**：規格 §5 代理合計上限 30M token。本計畫估約 15M（每批約 0.5～0.7M×24＋重做預留 1.5M＋outcome verifier 0.5M）。前 6 批平均 ×24 推估超過 18M ⇒ 停下回報。
- 執行模式沿用本線已選的 ASK：在核可範圍內連續跑完，停止條件觸發或完成時回報。

## 5. 就緒審查紀錄

- **預跑**（2026-10-04，scratch `p928/`）：
  - 18 條既有證據的 `content_sha256` 與正本全數相同；待補核 525 條、1,442 句；來源類型 code 886、docs 56、help 45、doc 2。
  - 分批 24 批、聯集 525 條；誘餌 24 項全部「原片段在該句恰出現一次」、誘餌 id 不與正本撞名（第一版後綴撞到既有 `jgb/A/account-change-password-rules`，斷言擋下後改為依序取不撞名後綴）。
  - 24 份 brief 產生成功，最大 34,965 字元。
  - `aggregate.py --self-test` 8/8：正確（含 1 句不成立）有效且清單正確；誘餌漏抓、誘餌判不成立但沒引來源、少一條、句數不符、sha 不符、元素不是字串、缺證據檔皆判作廢。

- **第 1 輪**（fresh plan-verifier）：REVISE，P2×4，全數 FIX——(1) 誘餌可不對來源就抓到（引用判定接受正本／證據路徑、brief 未禁讀正本、誘餌 id／標題可被看穿）⇒ brief 加禁讀清單並刪「可比對正本」措辭；`aggregate.py` 的來源判定改為合法來源檔名、引用禁讀位置整批作廢；誘餌 id 與標題改手寫並斷言不撞名、按架排序；(2) 每批有效性比 A6 寬 ⇒ 納入 `kind`、`verdict` 一致、每句 note、每條至少一個來源檔、禁讀位置；(3) 抽查推翻與 A7 矛盾、outcome verifier 可能 REFUTED ⇒ 抽查改由獨立 verifier 在 outcome 之前做，推翻句只進獨立欄，outcome 驗最終位元組；(4) brief 缺客戶名改寫指示 ⇒ 補上並重產 24 份。
- **第 1 輪後預跑**：`aggregate.py --self-test` 21/21（新增負對照：誘餌只引 `jgb.json`、只引 `verification/`、真細目引用禁讀位置、一句 note 沒有檔名、note 全是「同上」、缺「句 n」、`kind: change`、`verdict` 矛盾；抽查四例：推翻 1 句只進獨立欄且批次清單不變、集合不符、引用正本、verdict 矛盾）。來源檔名判定以 9.23～9.25 真實證據 78 則句 note 當正對照：只認完整相對路徑時僅 42 則命中（會誤殺），改為接受程式檔名或「同上」後全數可判有效；禁讀樣式對 `canon/jgb/A.md`、`verification/…json`、`drafts-A.json`、`CATALOG.md` 皆命中。端到端：合成 24 份證據經 `--extract` 往返後彙整 24／24 有效、525 條、1,442 句，抽樣 20 句；24 份 brief 皆含客戶名改寫規則。
- **第 2 輪**（fresh plan-verifier）：REVISE，P2×1——客戶名防洩只涵蓋批次 brief 與批次證據，抽查 brief 無改寫指示、抽查證據與 change 證據不在掃描範圍、掃描排在抽查寫入彙整之前。⇒ 第二次自動 REVISE，停止重送、逐條處置：**FIX**——新增 `gen_spot.py`＋`spot-template.txt`（合法來源、判定規則、禁讀、Hard rules 逐字取自批次模板，並含客戶名改寫指示；預跑產生 7,992 字元 brief，含兩條規則）；新增 `scan_names.py`（詞表逐字取自 `canon_check.py` `PAT`、內建正負對照）；掃描改為第 9b 步（抽查之後）＋第 10 步取出 change 證據後再掃一次、命中即停；outcome brief 加改寫指示；A10 範圍同步。預跑：`scan_names.py` 對端到端合成證據 24 份＋彙整 25 檔 0 命中、正負對照 ✅。依規則開一次收尾審查；再判 REVISE 即暫停交業主（除非審查者標全部 wording-only）。
- **第 3 輪（收尾）**（fresh plan-verifier）：**READY**。

## 6. 執行紀錄

- **業主核可**（2026-10-04，AskUserQuestion 逐字）：「核可，同意本計畫 +0 (Recommended)」（已填入 consent_zero）。
- **步驟 0**：HEAD `77464446d4de61b6412b1d9af9eb425be6cd3c0c`；`make audit` OVERALL PASS（`scratchpad/p928/audit-baseline.log`）；他線 41 檔指紋同 9.27（`scratchpad/p928/foreign-fp.txt`，正對照含 `runtime.py`）；正本備份 `scratchpad/p928-backup/canon` 與 HANDOFF 備份，`diff -r`／`cmp` 相同；jgb2 匯出存在；unit 紅燈基準沿用 9.27 同樹結果（9 條，`scratchpad/p928/red-base.txt`）。
- **brief**：24 份由 `gen_briefs.py` 以步驟 0 HEAD 產生，誘餌清單與預跑相同；派工時代理只讀自己的 brief 檔（放在與誘餌清單分開的目錄）。B01 交件後發現模板「同上」規則措辭不夠明確（代理寫「同一檔」），B02 起模板改為明示「必須寫『同上』兩字或檔名」，誘餌與批次內容不變。B15 起派工訊息另提醒 JSON 引號跳脫；B17 重做起另提醒唯讀不得建暫存檔。
- **24 批結果**：全數有效（`aggregate.py` 每批檢查 kind、verdict 一致、細目集合、句數、sha、title_text、notes 格式與合法來源、禁讀路徑、誘餌），24 個誘餌全數判不成立並引用合法來源。合計 525 條、1,442 句：全條成立 445 條；標題不成立 29、句不成立 81。
- **重做與揭露**（全數記錄）：
  - B01 首交格式不合（4 則 note 寫「同一檔」未寫「同上」）⇒ SendMessage 重貼一次 ⇒ 有效；判定未變
  - B14 首派代理停擺（stream watchdog 600s 無進度，failed，未交件）⇒ 換一位 fresh verifier 重做一次
  - B14 重貼（客戶簡稱改寫）一次 ⇒ 有效；判定未變
  - B15 代理自行揭露：一次 grep 參數展開為空、於 repo 根目錄遞迴執行，輸出僅見 semantic_model 檔、未引用；主 session 判定不重做（誘餌已抓且引 jgb2 來源、notes 無禁讀路徑——彙整 FORBID 檢查通過）
  - B15 首交 JSON 引號未跳脫（解析失敗）⇒ SendMessage 重貼一次 ⇒ 有效；判定未變
  - B17 首派代理自行揭露在 scratch/b/ 建立又刪除暫存腳本（違反 brief 唯讀 Hard rule）⇒ 依 brief「違反即作廢」該批作廢，未收件；換一位 fresh verifier 重做一次
  - B24 代理自行揭露：一次 grep 參數展開為空、於 jgb2 匯出根目錄遞迴，輸出帶出匯出內 dotenv 類範例檔數行註解，未用於判定；主 session 判定不作廢（匯出為 brief 允許的來源；匯出內唯一 dotenv 類檔為 jgb2 版控的 .env.custom，代理稱只見註解行；證據 grep APP_KEY／PASSWORD／SECRET／_KEY= 0 筆）
- **抽查**：種子 `20261012` 抽 20 句，fresh verifier 獨立重核，推翻 1 句（`jgb/G/device-page-lock-open-close` 句 3：只寫 SkyWatch 會顯示開／關門，漏「須在線上」條件），≤2 ⇒ 只列入彙整獨立欄 `spotcheck_overturned`；抽查證據 `verification/20261004-p928-spotcheck.json`。
- **客戶名掃描（一）**：`scan_names.py` 掃 24 份批次證據＋抽查證據＋兩份彙整＋誘餌清單，0 命中，正負對照通過。另見 §6 末「交業主事項」關於詞表大小寫落差。
- **正本未動**：`git diff --stat <步驟0 HEAD> -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 與工作樹皆空；終點指標重跑 `已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`。
- **代理用量**：26 次派工合計 6,678,771 token（含作廢的 B17 首派；B14 首派停擺未回報用量、不計），原估 15M。
- **交業主事項**（不阻擋本計畫）：
  1. 客戶名掃描詞表（`canon_check.py` 的 `PAT`）區分大小寫，抓不到 `isTongSang`、`isNthurc`、`meta_capital` 等程式識別字；這些詞早已出現在 repo 已追蹤檔（含 9.23 證據）。證據 notes 是否另行清除，待業主裁。
  2. B09 代理推論 jgb2 招租店舖可能讓非該店舖成員、但有編輯團隊權限的登入者編輯個人房東店舖（未實跑），屬 jgb2 端疑似授權缺口。
  3. jgb2 版控內有 `.env.custom`（主 session 未讀內容），若含真實設定值屬 jgb2 端風險。
  4. 多條帳本（`docs/knowledge/jgb-product-facts.md`）與幫助中心段落經批次代理指出與程式衝突，清單見各批 findings，處置併入下一份計畫。
- **最終 outcome verifier：REFUTED**（2026-10-04）——A1～A7、A9～A13 成立；**A8 不成立（P2）**：驗收清單要求彙整列出每批「重做次數」並與 §6 一致，但 `aggregate.py` 的彙整沒有重做欄位，重做紀錄只在本節。另有 P3（不分大小寫重掃，證據有 4 筆程式識別字，已列交業主事項 1）、P4×2（`source_transcript` 只存檔名，session 結束後無法重新取出；B24 意外 grep 帶出 `.env.custom` 行，證據 secret 樣式掃描 0 筆）。
- **依 §1 第 10 步停下**：不 commit；HANDOFF 以備份 `cp` 還原並 `cmp` 相同（含 9.28 內容的版本留在 `scratchpad/p928/HANDOFF-with-9.28.md`）；證據、彙整、工具留在工作樹（未追蹤）；`make audit` 不受影響。交業主裁定。
- **業主裁定**（2026-10-04，AskUserQuestion 逐字）：「補上重做欄位再驗一次 (Recommended)」。
- **A8 修正**：新增 `inputs/stock-reverify-9.28-redo-20261004.json`（每批 resend／replace／voided／note／disclosure，取自本節重做紀錄）；`aggregate.py` 加 `--redo`（批號集合須恰等於彙整，否則大聲失敗）與人讀版「〇、各批有效性與重做次數」表，self-test 23/23（新增：重做帶入、批號不符失敗）；重產兩份彙整（重貼 3、換人 2、作廢 1，與本節一致；其餘數字不變）；`.agents` 鏡像同步；客戶名重掃 29 檔 0 命中；HANDOFF 改回含 9.28 內容的版本。之後派一位 fresh outcome verifier 驗最終位元組。

