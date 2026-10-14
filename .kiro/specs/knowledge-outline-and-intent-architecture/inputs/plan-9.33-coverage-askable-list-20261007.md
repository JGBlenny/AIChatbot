<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「核可，同意本計畫 +0 (Recommended)」
-->
# Plan 9.33：規格 §2.1 覆蓋盤點——57 粗目「可問的事」清單、覆蓋判定、凍結補內容清單（2026-10-07）

> **現況**（2026-10-07，HEAD `0eb281ef`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`；正本 543 條全審。規格四項：第 3 項（審核）達成；第 2 項（內容）9.31 抽查 26／30、4 句已由 9.32 修正；**第 1 項（覆蓋）未做**；第 4 項（效果）未做。
>
> **本計畫的進度單位**：規格 §2.1 的三個產物——①57 粗目「可問的事」清單（含完整性驗證）、②逐件覆蓋判定與兩身分覆蓋率、③凍結的補內容清單。**0／3 → 3／3**。
>
> **已審細目數 +0**：本計畫只盤點與判定，不改正本；補內容（含 I 架「目前不支援」細目）是下一份計畫。`consent_zero` 已填入業主 2026-10-07 核可原文（見 §5）。

## 0. 依據

- 業主 2026-10-06：「照這個順序走」——①修 4 句（9.32 已完成）→ **②第 1 項覆蓋盤點，產出還缺哪些知識的清單並凍結** → ③第一次真實題量測。2026-10-07：「開始」。
- 目標驗收規格 `goal-acceptance-spec-20261004.md` §2.1（可問的事清單、完整性正對照兩種、售前適用、判定值域、業主抽查 20 件、I 架不支援、達成門檻）、§2.4「紀律」（補內容範圍＝第 1 項覆蓋表的全部未覆蓋事項，**在第一次 H 量測前凍結**）、§3 第 3 步、§5（門檻業者 ≥ 95%、售前適用 ≥ 90%；額度 30M；20 件由業主本人抽查）。
- 已凍結的輸入：骨架 `inputs/outline-skeleton-20260920.md`（57 粗目→頁）；頁面樹 `.claude/skills/outline-curation/runs/outline-20260920/page-surface.json`（183 頁）；售前適用清單 `inputs/prospect-applicability-proposal-20261004.md`（適用 54、不適用 3，已凍結）；種子 `inputs/goal-eval-freeze-20261004.json`（完整性種入 10 件 `20261004`、業主抽查 20 件 `20261005`）。
- 外部對照（repo 外）：`~/jgb-archive/ruler-9.13/skill-run-20260925/source-audit-{property_manager,prospect}.json` 的 `status=verified_fact` 紀錄共 64 格（業者 62、售前 2）。主 session 2026-10-07 開工前盤查：64 格皆有 `ledger_anchor` 欄，指向 48 個不同的帳本錨點，48 個都在 `docs/knowledge/jgb-product-facts.md` 的 `{#p914-…}` 中存在（正對照：帳本共 50 個 p914 錨點）；事實句＝該錨點節的「事實」行。〔⚠️ 本計畫初稿曾誤寫「紀錄欄位沒有 `ledger_anchor`」——當時只看了第一筆紀錄，那筆屬 `owner_needed` 類、本來就沒有此欄；已更正。〕
- 額度：規格 §5 上限 30M；9.28～9.32 實際合計約 16.7M（各計畫 §6），剩約 13M。

## 1. 程式大綱（兩片，依序，各一個 commit）

| 片 | 產物 | 業主關卡 | commit |
|---|---|---|---|
| **S1 可問的事清單** | `inputs/askable-list-9.33-<日期>.json`＋完整性驗證紀錄 | S1 完成回報（不需核可，除非完整性未達門檻或有分歧交裁） | 清單、驗證紀錄、證據 |
| **S2 覆蓋判定與凍結** | 覆蓋表 `inputs/coverage-9.33-<日期>.json`、兩身分覆蓋率、業主抽查 20 件、凍結補內容清單 `inputs/gap-freeze-9.33-<日期>.json` | **業主抽查 20 件（業主本人）**、補內容清單逐件「補／不補」裁定 | 覆蓋表、抽查單、凍結清單、證據 |

- S2 開工前另送一次就緒審查（只審 S2 細節，⛔ 重開 S1 核可）。本次就緒審查審「大綱＋S1」。
- 並行代理上限依 HANDOFF §12-2（2026-10-14 起主機 24 GB；原寫「一次只跑一個代理（本機 8GB）」）；代理 brief 一律帶 HANDOFF §12-2 必禁清單與「⛔ 讀正本」條款。

## 2. S1：57 粗目「可問的事」清單（含完整性驗證）

**2.1 步驟 0**：記錄 HEAD；`make audit`；他線未提交檔指紋（scratch `p930/foreign-fp.txt` 比對，含正對照 `runtime.py`）；盤查外部對照 64 格的事實句解法（見 §0）；確認 jgb2 釘住匯出完整（檔數＝`git archive b2ee2ac382ce` 檔數）。

**2.2 列舉**（executor；6 批依序，每批一位：A＋B、C、D、E、F＋G＋H、I——依骨架架別，批內粗目不拆）
- **每批輸入（主 session 準備，寫成 scratch 檔 `p933/batch-<批>/input.json`，代理只讀這個檔＋下列許可來源）**：該批粗目的骨架列（粗目 id、粗目標題、對應頁）、各頁的頁面單位（由主 session 從 `page-surface.json` 只抽出單位 id、路由名、元件路徑等頁面欄位，**不帶** `canon_titles`、正本細目 id、`inputs_sha.canon` 等任何正本衍生欄位）、該批粗目的售前適用裁定（粗目 id＋適用／不適用）。檢查：`grep -c 'jgb/[A-I]/' input.json`＝0（正對照：對 `page-surface.json` 跑同一條指令 > 0）。
- **許可讀取的路徑（白名單，代理只准讀這些）**：該批 `input.json`；jgb2 釘住匯出 `<scratch>/jgb2-b2ee2ac/` 底下的 `app/`、`src/`、`routes/`、`resources/`、`config/`、`database/`；幫助中心 `/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/`。起草規約 00c ⛔ 進白名單（該檔內文含禁讀路徑且「來源」節要求讀事實帳本與 `git show`，與本計畫衝突）——其「粒度」「用語」兩節由主 session 逐字放進每批 `input.json` 的 `rules` 欄，放入後對該欄跑禁讀前綴與 `jgb/[A-I]/` 檢查須 0 命中。白名單外一律禁讀，特別包括：`rag-orchestrator/`（含正本、CATALOG、`jgb.json`）、`.claude/skills/outline-curation/runs/`（含 drafts 與 `page-surface.json` 原檔）、`docs/`（含事實帳本整份；規格只禁 #p914 節，本計畫為了能機械驗證而禁整份——列舉來源本來就只有程式與幫助中心）、`.kiro/`、`~/jgb-archive/`、jgb2 任何工作樹與匯出內 `.env*`。輸入清單與禁讀清單 ⛔ 有交集。
- **工具使用規定（寫進 brief）**：Read／Grep／Glob 每次都要給白名單內的明確 `path`；⛔ 不帶 path 的 Grep／Glob；Bash 只准 `grep -nF`／`sed -n`／`cat`／`wc` 搭配白名單內的明確檔案或目錄路徑，⛔ `cd`、⛔ 變數組路徑、⛔ `find`、⛔ 對白名單外或白名單上層目錄遞迴搜尋。
- 規則（00c「粒度」節，逐條照抄進 brief）：每個粗目先列「可問的事」清單；至少涵蓋欄位群的意義與必填、規則／上限／驗證、錯誤與邊界（被鎖、過期、沒權限、沒載入完）、動作後會發生什麼、入口在介面哪裡、跟相鄰功能的關係、對某些身分（大房東／社宅團隊／租客）不同的地方；一件事＝使用者會問的一個問題。
- 每件輸出：`{"thing_id": "<粗目 id>#<流水號>", "coarse_id", "question": "<使用者會怎麼問，一句>", "kind": "<上列類別之一>", "presales": true|false（屬『有沒有這功能、怎麼運作、限制』類）, "pages": [<頁面單位>], "basis": [{"source": "code:…|help:…", "quote": "<逐字一行>"}]}`；每件至少一筆逐字依據（`grep -nF` 實測）。
- 機械檢查（主 session）：形狀與值域；`thing_id` 全域唯一；`coarse_id` ∈ 57；依據逐字命中；每個粗目至少 1 件；骨架 183 頁每頁至少被 1 件引用或在清單註明「該頁沒有獨立可問的事」與理由（⛔ 留無主頁；`bills.sheet` 標「業主排除」）；**讀取稽核**（腳本 scratch `p933/read_audit.py`，對每位代理 transcript 機械判定）。**比對方式寫死**：路徑一律先正規化成絕對路徑，再用下列**禁讀前綴**比對（⛔ 用相對子字串，例如單獨的 `docs/`）：`/Users/chenqinghuang/dev/work/AIChatbot/rag-orchestrator/`、`/Users/chenqinghuang/dev/work/AIChatbot/docs/`、`/Users/chenqinghuang/dev/work/AIChatbot/.kiro/`、`/Users/chenqinghuang/dev/work/AIChatbot/.claude/skills/outline-curation/runs/`、`/Users/chenqinghuang/jgb-archive/`、`/Users/chenqinghuang/dev/work/jgb2/`，以及匯出根下 `.env` 開頭的檔。以下任一成立即「命中」：(a) Read／Grep／Glob／Bash 的路徑參數（正規化後）落在禁讀前綴下，或不在白名單前綴下；(b) Grep／Glob 沒給 path，或 path 是任一禁讀路徑的上層（repo 根、`rag-orchestrator/`、`.claude/`、`.claude/skills/outline-curation/` 等）；(c) Bash 指令含 `cd`、`find`、`-r`／`-R`／`**` 遞迴、或路徑解析不出來；(d) 任何工具**結果**（輸出）中出現上列禁讀前綴字串，或正本細目 id 形狀 `jgb/[A-I]/[a-z0-9-]+`。命中 ⇒ 該批作廢重派。自我測試（合成 transcript，7 筆）：**判命中 4 筆**——直接 Read 禁讀前綴下的檔、無 path 的 Grep、`grep -rn x rag-orchestrator/`、工具輸出含 `jgb/A/account-registration`；**判不命中 3 筆**——Read 白名單內的匯出程式檔、Grep 幫助中心目錄且輸出含 `/Users/chenqinghuang/dev/work/docs/幫助中心/…`、Read 匯出程式檔且輸出含程式註解 `docs/adr/…`。開工時另對釘住匯出的 `app/`、`src/` 以固定字串搜 `docs/`、`jgb/` 記錄實際命中數，作為 (d) 不誤判的現況證據。
- 售前標記複核：主 session 依 00c「售前只掛有沒有這功能、怎麼運作、限制；操作細節只掛業者」逐件複核 `presales`；售前不適用的 3 個粗目一律 `presales=false`；改判逐件記錄理由。

**2.3 完整性驗證**（每批一位、與列舉者不同的 fresh 代理；同一套白名單、工具使用規定與讀取稽核；白名單另加主 session 準備的 `p933/batch-<批>/list-for-check.json`＝該批列舉清單移除種入件後的版本，只含清單欄位、不含正本衍生欄位）
- **種入**：全部清單以 `random.Random(20261004).sample(全清單依 thing_id 排序, 10)` 抽 10 件，從各自所屬批次的清單中移除後，交給該批的完整性代理；代理對照同一批程式與幫助中心，補上漏列、刪掉列錯（列錯須附理由），**不知道有種入**。
- **判定補回（規則開工前寫死）**：被移除的種入件 X 視為「補回」，須代理新增項中有一件 Y 同時符合：(i) **同一依據**——Y 的某筆依據與 X 的某筆依據是同一個檔案，且兩者引用的行在該檔中相距 ≤ 30 行，或落在同一個函式／同一個元件區塊（Vue `<template>` 同一個父節點、blade 同一個 `@section`、PHP 同一個 method）；(ii) **同一個問題**——X 的問題所問的對象（同一個欄位、按鈕、規則常數、狀態或流程步驟）與 Y 相同，能用同一句回答回答兩者。主 session 逐對列出 (i)(ii) 的符合情形與證據，寫進驗證紀錄；S1 收尾的 fresh verifier 在**看不到主 session 判定欄**的版本上獨立重判這 10 對，與主 session 不一致者交業主裁。**補回 ≥ 8／10** 才算完整性驗證可用；未達 ⇒ 換代理重做一次（沿用同 10 件，不重抽），再未達 ⇒ 停下交業主。
- **外部對照 64 格**：主 session（第三方，不參與列舉）依 §0 的解法把 64 格解成事實句，逐格對到清單某件事；對不到者逐格判「漏列」或「不屬可問的事」並記理由。**漏列 > 3 格 ⇒ 停下交業主**（⛔ 把漏列格的事實或理由交給任何代理補列——那會讓外部對照繞回自己、失去正對照效力）；漏列 ≤ 3 格時，漏列的格記入驗證紀錄，交 S2 一併列入凍結補內容清單（以事實句所屬粗目歸位）。
- 分歧（完整性代理要刪、主 session 不同意等）⇒ 列入 S1 回報交業主裁。
- 最終清單＝列舉清單＋補列（含補回的種入件）−確認列錯；寫入 `inputs/askable-list-9.33-<日期>.json`（repo；內容是從程式與幫助中心整理的問題，不含客服原話），驗證紀錄 `inputs/askable-verify-9.33-<日期>.md`。

**2.4 S1 收尾與 commit**：一位 fresh outcome verifier（BRIEF-CONTRACT v1）對驗收清單 S1 項逐項驗收 ⇒ `--extract` ⇒ `make audit` ⇒ commit（`Verified-by` 指向該證據）。⛔ `git add -A`、⛔ `--amend`；push 由業主自跑。

## 3. S2：覆蓋判定與凍結補內容清單（大綱；開工前另送就緒審查）

- **判定**：fresh 判定代理（**可讀**正本與 CATALOG）對清單每件事判 `covered`（列細目 id）／`partial`（列細目 id＋缺什麼）／`none`；業者身分判全部事項，售前身分只判售前適用粗目中 `presales=true` 的事項。腳本驗：清單集合＝判定集合、值域、`covered`／`partial` 列的細目 id 存在、已審、`target_user` 含該身分。`partial` 與 `none` 都算未覆蓋。混誘餌（主 session 構造：正本確定沒有的事、正本確定有的事各若干，判者不知道）。
- **覆蓋率**：業者＝`covered` 件數／業者全部件數；售前＝`covered`／售前適用件數；對照門檻（業者 ≥ 95%、售前 ≥ 90%）。
- **業主抽查 20 件**（業主本人，§5 第 5 點；種子 `20261005`；分層：業者 10、售前適用 6、售前不適用粗目中的事 4——後者請業主判「售前確實不需要答這件事」是否同意）：不同意 ≥ 3 件 ⇒ 判定重做。
- **凍結補內容清單**：全部未覆蓋事項逐件列出，業主逐件（或整批）裁「補／不補」；裁定後寫入 `inputs/gap-freeze-9.33-<日期>.json` 並記 sha256；規格 §2.4：**第一次 H 量測後 ⛔ 新增補內容項目、⛔ 推翻「不補」**。
- 產品沒有的事（判定時判「產品沒有」者）與 9.14 `verified_absent` 16 項，列入凍結清單的「I 架不支援」類，由補內容計畫寫成 I 架細目。

## 4. 不做（後續計畫）

- 補缺口（寫新細目、改既有細目）與 I 架「目前不支援」細目——下一份計畫，依凍結清單。
- 規格 §2.4 第一次真實題量測（業主順序第 ③ 步）。
- 9.30／9.31／9.32 附帶觀察（疑似 jgb2 缺陷、帳本說得太滿等）。
- 規格 §2.2 的重新抽查。

## 5. 業主裁決與待裁

- **已裁**：「照這個順序走」；「開始」。
- **業主核可**（2026-10-07，AskUserQuestion 逐字）：「核可，同意本計畫 +0 (Recommended)」（已填入 consent_zero；選項說明為「標『已修、未再審』直接開工 S1」）。範圍：大綱＋S1；S2 細節開工前另送就緒審查。
- **待裁（S1 回報時，僅在需要時）**：完整性驗證未達門檻、或完整性代理與主 session 分歧的事項。
- **待裁（S2）**：S2 細節核可；業主抽查 20 件；補內容清單「補／不補」。

## 6. 停止條件與額度

- 本計畫期間正本或 drafts 有任何改動 ⇒ 停。
- 讀取稽核抓到禁讀路徑 ⇒ 該批作廢重派一次；再犯 ⇒ 停。
- 種入補回 < 8／10 兩次 ⇒ 停、交業主；外部對照漏列 > 3 格 ⇒ 停、交業主。
- 外部對照 64 格的事實句解不出來 ⇒ S1 開工前停下回報（2026-10-07 已盤查可解，見 §0）。
- **額度**：就緒審查約 0.3M；S1 列舉 6 批約 2.4M、完整性 6 批約 1.8M、收尾約 0.2M；S2 判定約 1.5M、收尾約 0.2M；合計約 6.4M。S1 累計超過 6M、或全計畫累計超過 9M ⇒ 停下回報（規格 §5 上限 30M，剩約 13M）。〔業主 2026-10-07 核可修訂：S1 停止線 8M、全計畫 11M，見 §8。〕
- **執行模式**：沿用本線 ASK；S1 完成、S2 業主抽查與補內容裁定是固定停點。

## 7. 就緒審查紀錄

- **第 1 輪**（fresh plan-verifier，2026-10-07，大綱＋S1）：REVISE，P2×4（皆 substantive），**全數 FIX**：
  - B1 `page-surface.json` 在禁讀目錄且含正本細目 id 與標題（`canon_titles`）⇒ 改由主 session 抽出不含正本欄位的頁面單位寫成每批 `input.json`，並以 `grep -c 'jgb/[A-I]/'`＝0 驗證；改為白名單制，輸入與禁讀 ⛔ 交集。
  - B2 讀取稽核只看路徑參數、抓不到無 path 搜尋與上層遞迴 ⇒ 稽核規則改為 (a)～(d) 四條（含工具輸出出現禁讀路徑或正本 id 形狀），brief 加工具使用規定，正對照擴為四筆命中＋一筆不命中。
  - B3 重列會把漏列格事實交給代理、使外部對照繞回自己 ⇒ 刪除重列，漏列 > 3 直接停下交業主；≤ 3 的漏列格進 S2 凍結清單。
  - B4 種入補回判定沒有可操作標準、只由主 session 判 ⇒ 寫死「同一依據（同檔 ≤ 30 行或同函式／元件區塊）＋同一個問題（同對象、同一句可答）」，逐對記錄；S1 收尾 verifier 盲重判 10 對，不一致交業主；重做時沿用同 10 件。
  - 另更正 §0：64 格皆有 `ledger_anchor`（初稿誤寫）。送收尾審查。
- **收尾審查（第 2 輪）**（fresh plan-verifier，2026-10-07）：REVISE，P2×2（皆 substantive；B1、B3、B4 確認關閉，B2 結構關閉但比對方式未定）：
  - C1 讀取稽核以相對字串比對禁讀路徑，白名單幫助中心路徑本身含 `docs/`、程式註解也可能含 `docs/…` ⇒ 會誤判作廢。**FIX**：寫死「正規化絕對路徑＋禁讀前綴」比對；自我測試改 7 筆（4 命中＋3 不命中，含幫助中心輸出與程式註解兩筆不命中）；開工時記錄匯出內 `docs/`、`jgb/` 實際命中數。
  - C2 起草規約 00c 整檔在白名單，但內文含禁讀路徑、「來源」節要求讀帳本與 `git show` ⇒ 讀一次必命中。**FIX**：00c 移出白名單，「粒度」「用語」兩節逐字放進每批 `input.json` 的 `rules` 欄並檢查 0 命中。
  - 依規則：第二次 REVISE 且為 substantive ⇒ 停止自動送審，交業主決定。業主 2026-10-07 選「核可，同意本計畫 +0」⇒ **C1、C2 已修、未再審（fixed, not re-reviewed）**；C1 修法由開工時 7 筆自我測試機械把關。

## 8. 執行紀錄

- **步驟 0**（2026-10-07，HEAD `0eb281ef`）：`make audit` OVERALL PASS；他線 41 檔指紋與 `p930/foreign-fp.txt` 相同（含正對照 `runtime.py`）；釘住匯出 5882 檔；外部對照 64 格解成事實句（業者 62、售前 2，48 錨點，scratch `p933/ext64.json`）；每批 `input.json` 的 `jgb/[A-I]/` 0 命中（正對照 `page-surface.json` 210）、`rules` 欄禁讀前綴與 `jgb/[A-I]/` 皆 0；白名單來源（匯出 6 子目錄＋幫助中心）含禁讀絕對前綴 0 檔、含正本 id 形狀 0 檔（正對照正本目錄 10 檔）；匯出 `app/`＋`src/` 含 `docs/` 14 行、`jgb/` 1 行（皆非絕對前綴，(d) 不判）。粗目→頁取自 drafts 粗目層 `unit_ids`（只抽結構欄位）：182 頁被引用＋`bills.sheet` 業主排除＝183。
- **讀取稽核修訂**（業主 2026-10-07 核可，AskUserQuestion 逐字：「改稽核判準，保留這批 (Recommended)」）：A＋B 批第 1 版稽核按字面命中 835 筆，主 session 逐筆查證 160 個工具呼叫——Read／Write 全在白名單內、Bash 指令無任何白名單外路徑；命中來自 (1) 代理以變數、迴圈、`sort`／`head` 組指令（路徑全在匯出內；本環境代理的 Grep 工具不可靠，目錄搜尋只能靠 Bash），(2) 讀不存在的檔時系統自動附加「Note: your current working directory is …」提示（含 `.kiro/` 絕對路徑，代理無法控制）。**第 2 版判準**：Bash 以 shlex 斷詞、變數與迴圈展開後，每個路徑參數須落在白名單前綴內（相對路徑、`../`、`~`、未定義變數、白名單外指令仍判命中）；允許白名單內的 `grep -r` 與接 `sort`／`uniq`／`head`／`tail`／`wc` 的管線；工具輸出掃描前先去掉系統自動附加的目前目錄提示，其餘禁讀前綴與正本 id 形狀照判。自我測試擴為 18 筆（原 7 筆＋新增 11 筆：判命中 7、判不命中 4），18／18 通過；第 1 版保留於 scratch `p933/read_audit_v1.py`。A＋B 批依第 2 版重判命中 0。
- **額度停止線修訂**（業主 2026-10-07 核可，AskUserQuestion 逐字：「S1 停止線調到 8M (Recommended)」）：A＋B 批實耗約 0.62M（原估每批 0.4M）；S1 停止線 6M→8M，全計畫停止線 9M→11M（規格 §5 上限 30M 內）。
- **A＋B 批**：216 件（15 粗目，每粗目 6～23 件）、引文 286 筆、無主頁 0；機械檢查 1 處引文抄錯一字（`A-registration#1`「改使用」→原檔「改用」），主 session 依原檔更正並記於 scratch `p933/corrections.json`，事實不變。
- **讀取稽核第 3 版**（業主 2026-10-07 核可，AskUserQuestion 逐字：「採第 3 版，保留 C 批 (Recommended)」）：C 批第 2 版命中 269 筆，主 session 逐筆查證 172 個工具呼叫，無白名單外內容被讀到——命中來自 awk／tr／cut／printf 與自訂 shell 函式（檔案皆在白名單內）、1 筆相對路徑 `Index.vue`（以 cwd 解析後檔案不存在，無輸出）、1 筆 `ls` 匯出根（只列檔名）。**第 3 版判準**在第 2 版上另放行：唯讀文字工具 awk／tr／cut／printf 與 shell 函式（檔案參數仍須在白名單內）；相對路徑解析後檔案不存在者記錄為 note、不判命中（存在者照判命中）；`ls` 匯出根不判命中；迴圈項只在形如系統絕對路徑時當路徑檢查。自我測試 18 筆＋第 3 版追加 8 筆（命中 4、不命中 4）全過；第 2 版保留於 scratch `p933/read_audit_v2.py`。A＋B 批、C 批依第 3 版重判皆 0 命中。
- **C 批**：411 件（11 粗目）、引文 756 筆、無主頁 0；機械檢查 1 處：`C-community-force-binding#7` 在售前不適用粗目標 `presales=true`，依 §2.2 規則改 false（記於 `corrections.json`）。
- **命中處置規則**（業主 2026-10-08 核可，AskUserQuestion 逐字：「逐筆查證定去留，不再問你 (Recommended)」）：D 批第 3 版命中 6 筆（1 筆 `cd /dev/null` 違反 brief 但執行失敗、cwd 不變；5 筆為稽核解析不了的 shell 寫法——函式內迴圈、`set --`、heredoc——讀的檔皆在白名單內）。自此本計畫各批（含完整性代理）稽核有命中時，主 session 逐筆對照指令與輸出：確認沒讀到白名單外內容即保留，任一筆真的讀到白名單外內容即作廢重派；逐筆判定記於 scratch `p933/hit-review.md`（S1 commit 時複製進驗證紀錄），S1 收尾 verifier 獨立重核全部判定。
- **D 批**：403 件（10 粗目）、引文 684 筆、無主頁 0、機械檢查 0 錯；命中 6 筆逐筆判定保留。
- **E 批**：194 件（7 粗目）、引文 327 筆、無主頁 0、機械檢查 0 錯；命中 6 筆逐筆判定保留——其中 1 筆邊界：代理對匯出內 `docs/` 列檔名並 `grep -l`，只得檔名、未讀內文、清單 0 筆依據來自該處（交收尾重核）。其後各批 brief 明文禁止匯出內 `docs/`、`tests/`、`ai/`。
- **F＋G＋H 批**：216 件（8 粗目）、引文 414 筆、無主頁 0、機械檢查 0 錯；命中 12 筆（4 個呼叫）逐筆判定保留——其中 1 筆邊界：無路徑 `find`（cwd＝repo 根），代理只見系統截斷預覽中的 repo 根第一層項目名稱、無內文、無後續讀取（交收尾重核）。
- **I 批**：202 件（6 粗目）、引文 320 筆、無主頁 0、機械檢查 0 錯；命中 6 筆逐筆判定保留——其中 1 筆**嚴重邊界**：代理以 `grep -r … <匯出>/.env*` 嘗試搜尋匯出根的 `.env.custom`（違反 brief 與 Hard rules），逐行查證該呼叫輸出無任何 `.env` 內容回到代理（主 session 依規未讀該檔內容）；交收尾重核並向業主揭露。代理另回報 3 處程式與幫助中心互相矛盾（個人房東可開通的金流、免費試用的自動對帳、任務開單時機），兩邊依據都已放進同一件，未選邊。
- **列舉合計**：1,642 件、57 粗目（A＋B 216、C 411、D 403、E 194、F＋G＋H 216、I 202），列舉代理實耗約 2.87M token。逐筆命中判定記於 scratch `p933/hit-review.md`。
- **種入**（§2.3，種子 `20261004`，`random.Random(20261004).sample(依 thing_id 排序的 1,642 件, 10)`）：`C-community-public-page#2`、`B-advanced-settings#17`、`I-subscription-payment#11`、`C-team-storefront#3`、`D-contract-edit-social-housing#57`、`C-rent-listing#16`、`E-bill-create-edit#22`、`C-estate-dashboard#32`、`I-pricing#30`、`I-control-panel#14`（各批移除數：A＋B 1、C 4、D 1、E 1、F＋G＋H 0、I 3）。為免完整性代理從斷號推知有移除，`list-for-check.json` 依粗目重新連續編號（對照表在批次目錄外的 scratch `p933/maps/`）；列舉代理原清單亦移出批次目錄。
- **完整性第一輪**（6 位 fresh executor，約 2.11M token）：新增 A＋B 54、C 8、D 14、E 97、F＋G＋H 78、I 50 件；列錯 A＋B 1、C 7、D 4、E 4、F＋G＋H 3、I 2 件；新增項機械檢查全過（引文逐字命中）。D 批起 brief 加「逐頁打開元件檔」與 `coverage` 欄。命中逐筆判定皆保留（`p933/hit-review.md`）。**種入補回 4／10**（#1 `B-advanced-settings#17`、#7 `E-bill-create-edit#22`、#8 `I-subscription-payment#11`、#10 `I-control-panel#14`；未補回 C 4 件、D 1 件、I 1 件，其中 `I-pricing#30` 為規則 (i) 邊界，交收尾盲判），逐對見 scratch `p933/seed-pairs.md`。未達 8／10。
- **完整性重做**（依 §2.3「換代理重做一次、沿用同 10 件」；業主 2026-10-08 選「重做 C、D、I 三批，加機械查核深度 (Recommended)」）：C、D、I 三批各換新代理整批重檢（不只看種入件所在粗目，避免偏誤）；第一輪的 `check.json` 移出批次目錄；brief 加逐頁 `verdict`／`evidence`（無漏列須舉清單中涵蓋本頁的編號），交件後以 scratch `p933/coverage_check.py` 機械比對「宣稱讀過的檔確實出現在工具呼叫」與「evidence 編號存在」，對不上整批作廢。A＋B、E、F＋G＋H 第一輪結果保留。補回判定＝A＋B、E、F＋G＋H 取第一輪，C、D、I 取重做結果（重做取代第一輪，不取兩輪聯集）；重做後仍未達 ⇒ 停下交業主。
- **完整性重做 C 批**（新代理，約 0.48M token；新增 65、列錯 7；`coverage_check.py` 通過：43／43 頁、宣稱讀過 108 檔皆有讀取紀錄）：種入補回 **0／4**（`C-rent-listing#16` 為規則 (ii) 邊界，保守不計）。依計分規則（A＋B、E 取第一輪 2 件，C 取重做 0 件），D、I 即使全補回最多 6／10，已不可能達 8／10。
- **停止重做**（業主 2026-10-08 選「停止重做，先做外部對照 64 格再裁 (Recommended)」）：D、I 不重做（保留第一輪結果）。
- **目前清單**（scratch `p933/current-list.json`）：列舉 1,642 件－完整性列錯 21 件＋完整性新增 358 件＝**1,979 件**（C 取重做、其餘取第一輪）。
- **外部對照 64 格**（主 session 第三方逐格比對，關鍵字查清單後人工判定，逐格記於 scratch `p933/ext64-verdicts.json`）：**對到 43 格、漏列 20 格、不屬可問的事 1 格**（48 錨點中對到 31、漏列 16、不屬 1）；售前 2 格皆對到。**漏列 20 格 > 3 ⇒ 依 §2.3 停下交業主**（⛔ 把漏列事實交給任何代理補列）。漏列 16 條的共同點：多為跨頁的後端規則或流程（重複匯款處理、ATM 帳號效期、信用卡分期、提前解約後是否出帳、發票是否合併、車位物件不能建約、租賃範圍判定等），不落在單一頁面的畫面元素上——本計畫的列舉以頁面為入口，結構上容易漏掉這一類。
- **S1 狀態：完整性驗證兩項皆未達（種入 4／10、外部漏列 20 格），清單完整性未經證實；S1 未收尾、未 commit，待業主裁定。** S1 代理實耗約 5.5M token（列舉 2.86M、完整性 2.59M）。

## 9. 修訂 S1b：後端規則列舉（2026-10-08 起草；就緒審查第 1 輪 REVISE 後改寫，待收尾審查與業主核可）

**緣由**：S1 兩項完整性驗證皆未達（種入補回 4／10、外部對照漏列 20 格，見 §8）。業主 2026-10-08 選「加一輪『後端規則』列舉再驗 (Recommended)」，選項原文的範圍是「以後端為入口（金流回呼、排程、帳單與發票規則、各 controller 的驗證與拒絕條件）補列『跨頁規則』類的事，再用同一份外部對照驗（漏列事實不給代理，對照仍有效）。預估約 2～3M，需把 S1 停止線從 8M 調到約 11M」。

**業主核可**（2026-10-08，AskUserQuestion 逐字）：「核可 S1b，同意上述三件事 (Recommended)」。所指三件事：① 種入 4／10 照實記為未達、改以外部對照為主要完整性證據（對規格「≧ 8／10」的放寬）；② S1b 約 4.0M、停止線 4.5M，S1 停止線 11M、全計畫 14M（高於選項說明的 2～3M）；③ 知悉規格 30M 上限下，第 4 項效果量測約缺 9.5M，之後另裁。收尾審查第 2 輪 E1～E3 依此核可記為**已修、未再審（fixed, not re-reviewed）**。

**9.1 分派（只看路徑，與外部對照結果無關）**
- **目錄集合**：釘住匯出 `app/` 底下全部 `.php`，加上 `routes/`、`config/` 底下全部 `.php`。**明列排除 3 項**：`app/Providers/`（框架服務註冊，8 檔）、`app/Exceptions/Handler.php`（框架例外處理，1 檔；同目錄其餘例外類別含帳單、發票的拒絕條件，**保留**在集合內）、`app/ConstAddress.php`（約 5 MB 的縣市區里地址常數表，純資料、無規則）。前端 `src/`、`resources/` 已由 S1 以頁面入口涵蓋，資料庫結構 `database/` 不是客人會問的規則，皆不在本輪。
- **切法**：集合內 813 檔依路徑字典序排序，按檔案位元組數切成 7 段大小相近的連續區塊（每段約 2.4～4.1 MB），一檔只屬一段、未歸批 0 檔（除上列排除項）。腳本 scratch `p933/s1b_partition.py`，分派結果 `p933/s1b-partition.json`；試算正對照：`app/Services/Payment/UbotVaNotifyService.php` 落在第 6 段、`app/Http/Controllers/Vendors/ICashPayController.php` 落在第 5 段、`app/Exceptions/AdjustmentBlockedException.php` 落在第 2 段。
- **範圍用語**只用業主原話（金流回呼、排程、帳單與發票規則、各 controller 的驗證與拒絕條件、跨頁規則），⛔ 加入任何與外部對照漏列事實同詞的描述。

**9.2 每批輸入與 brief**
- `input.json`：`files`（該段檔案清單）、`coarses`（57 粗目 id 與標題）、`existing`（目前清單 1,979 件的 `thing_id`＋`question`，供去重；這份是 S1 在外部對照之前就已產出的成品，凍結其 sha256 入紀錄）、`rules`（00c「粒度」「用語」兩節原文，同 S1）。檢查同 §2.2：`jgb/[A-I]/` 與禁讀前綴 0 命中。
- brief 範本定稿於 scratch `p933/brief-s1b-template.txt`（附於本計畫送審，見 §9.6）：從後端程式補列跨頁規則型的可問的事，`existing` 已有同一個問題就不列；輸出另附 `files_reviewed`。
- **防洩漏機械檢查**：主 session 從外部對照漏列 16 條抽出 33 個詞（scratch `p933/leak-terms.txt`，⛔ 給代理），以 `p933/leak_check.py` 對 brief 範本、每批定稿 brief，以及 `input.json` 中由主 session 撰寫的欄位（`rules` 與 brief 指示文字）逐詞固定字串比對，**必須 0 命中**；正對照＝同一詞表對 `ext64.json` 命中 33／33。`existing` 與 `coarses` 是外部對照前已凍結的既有成品，不受此檢查（其 sha256 入紀錄供核）。2026-10-08 試跑：範本 0 命中、正對照 33。
- 白名單、工具使用規定、讀取稽核（第 3 版）與命中逐筆查證規則沿用 §2.2、§8。

**9.3 輸出、機械檢查與去重**
- 每件形狀同 S1（`thing_id`＝`<coarse_id>#b<流水號>`，`pages` 可為空），必須歸到 57 粗目之一、至少一筆逐字依據；機械檢查同 §2.2（形狀、值域、依據逐字命中、粗目合法、客戶名掃描）。
- `files_reviewed` 與代理工具呼叫機械比對（`coverage_check.py` 同法：宣稱看過的檔必須出現在 Read 或 cat／sed／grep 指名該檔的呼叫中），對不上整批作廢重派一次。
- 與 `existing` 重複者，主 session 依「同一對象、同一句可答」判定剔除，逐件記錄。

**9.4 驗收（取代 §2.3 的種入門檻，需業主明示同意）**
- **外部對照「對到」標準（開工前寫死）**：某格事實「對到」清單某件 Y，須同時符合 (a) Y 所問的對象與該格事實的對象相同（同一個規則、流程步驟、欄位、狀態或功能）；(b) 該格事實能直接回答 Y（同一句可答）。只是同一功能區、或 Y 只問到該事實的入口而不涉及該規則者，不算對到。
- **重驗**：主 session 以同一份 64 格（scratch `p933/ext64.json`）對「目前清單＋S1b 新增（去重後）」逐格重判，**漏列 ≤ 3 格**才算清單可用；> 3 ⇒ 停下交業主，⛔ 再加輪次。
- **獨立重判（不抽查，64 格全數）**：S1b 收尾 fresh verifier 在**看不到主 session 判定**的版本上，依同一「對到」標準 (a)(b) 獨立重判 **64 格全數**（含 S1 原判「對到」的格——S1 當時未有寫死標準）。與主 session 判定不一致者全數列表交業主裁；以業主裁定後的結果計算漏列格數。
- **種入**：S1 的種入補回 4／10 照實記為「未達」，⛔ 再重測（§2.3 只允許重做一次，已用完）。最終清單的完整性證據改以外部對照為主，這是對規格 §2.1「補回 ≥ 8／10」的放寬，須業主明示同意並逐字記入本節。
- S1b 收尾另含：重核 `p933/hit-review.md` 全部命中判定、種入 10 對盲判（§2.3 原定）、重跑 `leak_check.py` 結果一致；全部通過才 commit S1＋S1b。

**9.5 額度與停止線（以 §8 實測單價計）**
- 實測：S1 列舉每位代理平均約 0.48M（6 位 2.86M）、完整性每位約 0.35M、C 批重做 0.48M。
- S1b：7 位 × 0.5M ≈ 3.5M＋就緒審查與收尾約 0.5M ≈ **4.0M**；**S1b 停止線 4.5M**（一次定實，不中途放寬）。
- 9.33 至今約 6.1M（S1 代理 5.5M＋審查約 0.6M）；加 S1b 4.0M、S2 約 1.7M ⇒ 9.33 合計約 11.8M。S1 停止線 8M→11M、全計畫 11M→14M。
- **與業主選項說明的差異（須業主核可時明示同意）**：業主所選選項說明估「約 2～3M」，本修訂改用 §8 實測單價（每位約 0.5M）且範圍改為全部後端檔案（813 檔、7 位代理），估約 4.0M、停止線 4.5M；全計畫停止線 11M→14M 也超出選項所述。
- **規格 §5 總上限 30M 的後果（業主核可時須一併知悉）**：9.28～9.32 約 16.7M＋9.33 約 11.8M ≈ **28.5M**，剩約 1.5M。規格 §5 第 3 點列的第 4 項（效果）預算約 11M（L1 判者約 8M、正負對照出題約 1M、L3 判者約 2M）也計在 30M 內 ⇒ **本修訂核可後，第 4 項在現有上限內做不完，缺口約 9.5M**，需業主另裁：調高 §5 上限，或縮小第 4 項範圍。

**9.6 brief 範本（定稿，送審用；`{{…}}` 由腳本代入批次路徑）**：見 scratch `p933/brief-s1b-template.txt` 全文。要點：從後端程式補列跨頁規則型的事；`existing` 已有同一問題不列；白名單與工具規定同 S1 第 3 版；輸出 `things`（`#b` 編號）與 `files_reviewed`；交件後機械比對讀取紀錄。

**9.7 不做**：⛔ 刪改 S1 已有的 1,979 件；⛔ 依外部對照漏列事實定題、下關鍵詞或切批；⛔ 第三輪列舉；⛔ 把外部對照事實或詞表交給任何代理。

**9.8 就緒審查紀錄**
- **第 1 輪**（fresh plan-verifier，2026-10-08）：REVISE，P2×4（皆 substantive），**全數 FIX**（D1～D4 如下）。
- **收尾審查（第 2 輪）**（fresh plan-verifier，2026-10-08）：REVISE，P2×3（2 substantive、1 wording-only），**全數 FIX**：E1 盲判範圍未含 S1 原判對到的格 ⇒ 改為 64 格全數盲判；E2 `app/Exceptions/` 排除理由不實（含帳單、發票拒絕條件）⇒ 只排除 `Handler.php`、其餘放回，重切 813 檔，新增正對照 `AdjustmentBlockedException.php`；E3（wording-only）未對照選項估算 2～3M ⇒ 緣由補原文、§9.5 加差異說明與須明示同意。依規則：收尾審查再 REVISE 且含 substantive ⇒ 停止自動送審，交業主決定（核可「已修、未再審」或再送審）。
- 第 1 輪處置明細：
  - D1 檔名關鍵詞看來依已知漏列挑選（`Newebpay`、`Ctbc` 0 檔，`EarlyTermination` 1 檔，查證屬實）⇒ 改為純路徑分派＋明列排除；範圍用語只留業主原話；brief 範本定稿入審並加防洩漏詞表 0 命中檢查（含正對照）。
  - D2 關鍵詞分派留下大量未歸批檔（金流回呼、其他 controller、`routes/`、`config/`）且重疊無規則 ⇒ 目錄集合寫死、明列 3 項排除與理由、未歸批 0、依路徑連續切段無重疊；正對照兩檔已落批。
  - D3 外部對照重驗由已知答案的主 session 判、無比對標準、verifier 只抽查 ⇒ 寫死「對到」標準 (a)(b)；收尾 verifier 盲判 S1 漏列 20 格＋S1b 帶來的對到格＋邊界 3 格，不一致交業主。
  - D4 額度單價偏低、未寫第 4 項缺口 ⇒ 改用實測單價、停止線 4.5M 一次定實，明寫 30M 下第 4 項缺口約 9.5M 待業主裁。

**9.9 S1b 第 1 批結果與業主裁示（2026-10-14）**
- **S1b-1**（2026-10-08）：交 42 件；該批 211 檔，代理只碰 25 檔（覆蓋淺），實耗約 0.22M。42 件未做機械檢查、未去重。
- **scratch 遺失與重建**：舊 scratch 於 2026-10-13 被系統清空。2026-10-14 從主 session 與代理 transcript 重放「最後一次 Write＋其後全部成功的 Edit」重建於 repo 外 `~/jgb-archive/p933-rebuild-20261014/`（方法與對帳見該目錄 README）。對帳全數吻合：列舉 1,642 件（六批件數與引文數同 §8）、種入 10 件同 §8、完整性新增 358／列錯 21 ⇒ 目前清單 1,979 件，`existing` sha256 `000fcbc3270a63b2024fddabcd18cfc89dbff6172226e417bf13e1d4aa12afc6` 逐位元相同；外部對照 64 格 43／20／1（錨點 31／16／1）。
- **業主裁示**（2026-10-14，AskUserQuestion 逐字）：
  - S1b 剩餘批次：「brief 加覆蓋率要求再跑，第 1 批重做 (Recommended)」⇒ S1b-1 的 42 件作廢，7 批全部依新 brief 重跑。
  - 執行模式：「ASK (Recommended)」。
  - 覆蓋率要求的定義：「先抽規則行，代理逐段看完 (Recommended)」。選項說明原文：「主 session 用不針對特定功能的通用樣式（驗證規則、throw／abort、錯誤訊息、排程），從 813 檔決定性地抽出帶前後文的片段；覆蓋率＝代理看完 100% 片段，可以機械檢查。抽出量先免費量一次，再送計畫修訂、就緒審查和你核可」。
- **緣由**：§9.1 目錄集合 813 檔共 21.1 MB（`git ls-tree -l b2ee2ac382ce -- app routes config`，排除項同 §9.1），整檔讀完約超過 S1b 停止線 4.5M；S1b-1 覆蓋淺即因單一代理讀不完約 3 MB 的一段。
- **下一步**：量抽出量 → 改寫 §9.1～§9.3（片段抽取規則、切批、覆蓋率機械檢查、防洩漏檢查對抽取樣式本身也要 0 命中）→ 就緒審查 → 業主核可 → 才重跑。修訂前 ⛔ 派任何 S1b 代理。

**9.10 修訂：片段抽取與片段全覆蓋（2026-10-14 起草，待就緒審查與業主核可；取代 §9.1「切法」、§9.2 `input.json` 的 `files` 欄、§9.3 的 `files_reviewed` 比對，其餘條文沿用）**
- **目錄集合不變**：§9.1 的 813 檔（含 3 項排除）。釘住匯出 2026-10-14 由業主親跑 `git -C …/jgb2/dev1 archive b2ee2ac382ce` 重建，共 5882 檔（＝§8 步驟 0），放在 `/Users/chenqinghuang/p933-work-20261014/jgb2-b2ee2ac/`。⚠️ 代理可讀的工作區（匯出與各批 part 檔）**不得**放在 `~/jgb-archive/` 下——那是 §2.2 的禁讀前綴（外部對照資料所在），放在其下會讓讀取稽核把白名單讀取全判命中；也 ⛔ 放 `/private/tmp`（2026-10-13 曾被系統清空）。主 session 的 scratch（含漏列詞表、外部對照）留在 `~/jgb-archive/p933-rebuild-20261014/`，代理不可讀。
- **片段抽取（主 session，決定性，開工前凍結）**：腳本 `s1b_extract.py`（scratch，sha256 前 16 碼 `aee3bd9ef593ce17`）逐行比對四類樣式，命中行取前後 3 行、重疊或相鄰視窗合併成一段，片段 id＝`<檔>:L<起>-L<迄>`。四類只用程式結構詞，⛔ 功能詞：
  - 驗證規則：`Validator::make`、`validate(`、`function rules(`、`Rule::`，以及引號或 `|` 後接常見驗證規則名（required、nullable、numeric、integer、date、email、in、max、min、between、unique、exists、regex、size、digits）；
  - throw／abort：`throw new`、`abort(`／`abort_if(`／`abort_unless(`；
  - 錯誤訊息：含中文的字串字面值，**且**同一行有錯誤或回應結構（error／Errors／withErrors／fail／Exception／message／msg／`->with(`／`response()`／`json(`／return／abort／throw）；
  - 排程：`protected $signature`／`protected $description`、`$schedule->`、`->cron(` 與 Laravel 排程頻率方法。
- **抽取結果（2026-10-14 實測）**：813 檔中 530 檔有片段，共 5,032 段、1.95 MB（`s1b-snippets-v3.json`，sha256 前 16 碼 `026b4e993275dc2e`）；命中行：驗證 2,581、throw／abort 544、錯誤訊息 5,300、排程 462。**283 檔無任何片段**（約 3.5 MB，多為 `app/Modules`、`app/Services`、`app/Http` 的輔助程式與 `app/Models`、`app/Exports`），本輪不交代理、⛔ 宣稱已覆蓋，清單附於 S1b 回報。正對照：`UbotVaNotifyService.php` 9 段、`ICashPayController.php` 5 段、`AdjustmentBlockedException.php` 1 段。
  - 收斂紀錄（照實）：第 1 版「錯誤訊息」取任何含中文的字串 ⇒ 7.21 MB（60,302 行，主要是純資料代碼表與介面標籤）；第 2 版加「同一行有錯誤／回應結構」⇒ 1.87 MB，但 `app/Console` 61 檔無片段；第 3 版排程類加 `$signature`／`$description` ⇒ 現值。三版皆只依量與結構調整，⛔ 參考外部對照事實；凍結後 ⛔ 再改樣式。
- **切批**：片段依（檔、起始行）排序，同一檔不跨批，按位元組切 7 段連續區塊（`s1b_batches.py`）：S1b-1 169 檔／757 段／285 KB、S1b-2 72／691／286、S1b-3 31／720／266、S1b-4 31／812／301、S1b-5 31／729／306、S1b-6 117／756／264、S1b-7 79／567／285；合計＝5,032 段（母段）、530 檔。
- **part 上限（就緒審查第 1 輪 B1 修正）**：每批拆成序列化後 ≤ 18 KB 的 `part-NN.json`（共 193 個，最大 18,636 位元組）。依據：BPE token 數 ≤ 位元組數 ⇒ 每個 part 一次 Read 必定低於 25,000 token 上限，不靠逐檔試讀。序列化後超過上限的單段，依行邊界拆成子段：子段 id＝`<檔>:L<起>-L<迄>`、另帶 `parent`＝母段 id，母段行範圍＝子段聯集（實測僅 `config/contract.php:L36079-L36101` 一段拆成 5 子段，行範圍逐行吻合；最長單行跳脫後 6,475 位元組，不需行內拆分）。每個 part 最後一個鍵是 `end_marker`（`END-<批>-part-NN`）。正對照：主 session 以預設 Read 實讀全中文密度最高的 `S1b-7/part-25.json` 與 `S1b-1/existing-01.json`，皆一次整檔讀完、結果含 `end_marker`、無截斷提示。
- **代理輸入**：該批 `part-*.json`＋`input.json`（`coarses`、`rules`＝00c「粒度」「用語」兩節原文、`end_marker`；9 KB）＋`existing-NN.json`（1,979 件 `thing_id`＋`question` 依同一 18 KB 上限切 14 個，各帶 `end_marker`；`existing` 整體 sha256 仍＝`000fcbc3…afc6`）。白名單、工具使用規定、讀取稽核（第 3 版）、命中逐筆查證沿用 §2.2／§8；釘住匯出仍在白名單內（代理可讀片段所在檔的上下文，但覆蓋率只以片段計）。
- **覆蓋率要求（取代 `files_reviewed`）**：
  - 每個 part 檔、`input.json` 與每個 `existing-NN.json` 都必須以一次不帶 offset／limit 的 Read 整檔讀過。**「未截斷」的機械判定（B1 修正）**：該次 Read 的 `file_path`＝該檔絕對路徑、無 offset／limit、結果非錯誤、結果文字含該檔的 `end_marker`（檔案最後一個鍵＝讀到檔尾）、且不含 Read 工具的截斷提示（`PARTIAL view` 或 `showing lines N-M of K total`）。任一檔不符 ⇒ 整批作廢重派一次。檢查器 `s1b_coverage_check.py` 自測 11／11（正 1、負 10，含「part 被截斷」「只讀到前段」「帶 offset 分段讀」「漏讀 existing 檔」等合成負對照）。
  - 交件 `snippets_reviewed` 必須逐一列出該批**全部**片段 id（集合相等，機械比對），每段標 `listed`（列出由它產生的 `#b` 件 id，id 須存在於本批 `things`）或 `no_askable`（一句理由）。
  - 每件 `#b` 至少一筆依據逐字命中釘住匯出（`grep -nF` 實測），同 §9.3。
- **防洩漏**：`leak_check.py` 對 `s1b_extract.py`、`s1b_batches.py`、brief 範本、每批定稿 brief、`input.json` 主 session 撰寫欄位一律 0 命中，正對照 `ext64.json` 33／33（2026-10-14 對兩支腳本已實測 0 命中、正對照 33）。片段內容取自程式原文，不受此檢查（同 `existing`）。
- **開工前置**（未完成不得派代理；2026-10-14 已全數完成，B2 修正後補齊 ④～⑥）：
  ① 依 transcript 重建讀取稽核第 3 版與自我測試：18／18＋v3 追加 8／8 通過（同 §8）。
  ② `s1b_coverage_check.py`（sha256 前 16 碼 `128e03d365bb6c3f`）自測 11／11。
  ③ `s1b_inputs_v2.py`（`9a963665481fdf23`）產生 7 批 `input.json`＋`existing-NN.json`：`jgb/[A-I]/` 與禁讀前綴皆 0（正對照 `page-surface.json` 含 `jgb/` 形狀）、`existing` sha256＝凍結值。
  ④ **新工作區**：各批 part、`input.json`、`existing-NN.json` 皆產生在 `/Users/chenqinghuang/p933-work-20261014/p933/batch-S1b-<i>/`（`s1b_batches.py` `1ec2e618c1c49fec`、`s1b-batches.json` `7be5d89e65fb8913`；舊 `~/jgb-archive/…/s1b/` 的 60 KB 版作廢、不交代理）。讀取稽核白名單本來就是 `<SP>/p933/batch-<批>`，`SP` 已改為新工作區，程式不需改。
  ⑤ **讀取稽核新位置正負對照** `ws_test.py`（`c041f751975e03b0`）7／7：讀本批 part、本批 input、新位置匯出檔判不命中；讀 `~/jgb-archive/…/part-01.json`、別批 part、主 session 工具目錄、匯出根 `.env.custom` 判命中。
  ⑥ **brief 範本改寫**（`580b2047a476f348`）：輸入改為 part／existing／input 三種檔，要求逐檔一次整檔讀並確認 `end_marker`、交件 `snippets_reviewed`（listed／no_askable）；`snippets_reviewed` 3 處命中、`files_reviewed` 0 處（舊版 3 處作正對照）；7 批定稿 brief、範本、`rules` 與上列腳本 `leak_check.py` 全 0 命中（正對照 33／33）。
- **驗收**：外部對照重驗、64 格盲判、種入不再重測、收尾重核，全部沿用 §9.4。S1b-1 舊 42 件作廢、不併入。
- **額度**：停止線維持 **4.5M**（已用 S1b-1 約 0.22M）。估算：7 位 × 約 0.5M ≈ 3.5M＋就緒審查與收尾約 0.5M ⇒ 合計約 4.2M。每位代理必讀量＝片段約 0.26～0.31 MB＋existing 約 0.23 MB＋input 9 KB ≈ 0.5～0.55 MB；參考值：2026-10-14 一位唯讀 scout 以 67 次 Read 整檔讀 59 個檔約 1.4 MB，實耗約 0.68M（約每 MB 0.49M），據此每位讀取約 0.25～0.27M，加上產出與推理估約 0.5M。⚠️ 此單價未經 S1b 實測（就緒審查第 1 輪待查），故加一道閘門：**S1b-1 交件後若實耗 > 0.6M，先停下以實測單價重估 7 批總額再交業主**，不待累計觸及 4.5M。任一時點累計超過 4.5M ⇒ 停下回報，⛔ 中途放寬。
- **不做**：⛔ 用外部對照事實或漏列詞表調整樣式、片段或切批；⛔ 把 283 個無片段檔說成已覆蓋；⛔ 第三輪列舉。
- **已知限制（審查員列為待查，照實揭露）**：機械檢查證明每個檔確實整檔讀進、片段 id 集合相等，但驗不了 `no_askable` 的理由是否成立，也驗不了 `listed` 件的依據是否確實出自該段（依據只要求逐字命中整份匯出）；這是業主所選「看完 100% 片段」定義本身的界線，最終成效仍由 §9.4 外部對照重驗與 64 格盲判把關。

**9.11 §9.10 就緒審查紀錄**
- **第 1 輪**（fresh plan-verifier，2026-10-14）：REVISE，P2×2（皆 substantive），**全數 FIX**：
  - B1 part 只以位元組 ≤ 60 KB 控制、未控制 Read token 上限，實測 `S1b-7/part-07.json`（單段 `config/contract.php:L36079-L36101`）一次 Read 為 37,448 token 被截斷；「未截斷」判定未寫死 ⇒ 改為序列化 ≤ 18 KB（token ≤ 位元組的上界證明）、超限單段依行拆子段並保留 `parent`、每檔尾端 `end_marker`、判定寫死（含 `end_marker` 且無截斷提示）、檢查器加截斷合成負對照；另發現同類問題 `input.json` 256 KB（含 `existing`）⇒ 一併改切 `existing-NN.json`。
  - B2 開工前置未涵蓋新工作區、稽核白名單位置驗證、brief 改寫 ⇒ 補 ④～⑥ 並完成。
  - 待查（非阻擋）：額度單價無依據 ⇒ 改附參考值並加 S1b-1 實耗 > 0.6M 閘門；`no_askable`／`listed` 依據無法機械驗 ⇒ 列入已知限制。
- **收尾審查**（fresh plan-verifier，2026-10-14）：**READY**。
- **業主核可**（2026-10-14，AskUserQuestion 逐字）：「核可，派 S1b-1 (Recommended)」（問題原文：「核可 Plan 9.33 S1b 修訂（§9.9～§9.11：片段抽取 7 批、停止線 4.5M、S1b-1 實耗 > 0.6M 先停），開始派 S1b-1 嗎？」）。ASK 模式：每批交件後停下回報。

**9.12 S1b 執行紀錄**
- **S1b-1**（2026-10-14，§9.10 版，executor，brief sha256 前 16 碼 `6d4913a1006758ff`）：交 25 件（13 粗目、引文 59 筆）、`snippets_reviewed` 757／757；實耗 **0.58M**（< 0.6M 閘門）、90 次工具呼叫、約 11 分鐘。
  - 覆蓋檢查 `s1b_coverage_check.py`：PASS（28 個 part、14 個 existing、input 皆有一次整檔且未截斷的讀取紀錄；片段集合相等）。
  - 機械檢查 `s1b_check_things.py`：0 錯（形狀、值域、`#b` id、粗目、presales、引文逐字命中匯出、客戶名詞表）。
  - 讀取稽核第 3 版：命中 1 筆（`cd /dev/null; wc -c <本批 part>`，`cd` 失敗、cwd 不變、輸出只有本批檔位元組數）⇒ 逐筆判定保留（同 D 批先例），記入 `hit-review.md`；代理交件時自行揭露此筆與另一筆 `2>/dev/null`（白名單內，稽核不命中）。
  - 去重（§9.3，主 session）：25 件與 `existing` 逐件比對，判同一問題 0 件、剔除 0；邊界 3 件照列：`E-balance-invoice#b1`（狀態是否自動切換）↔ `#5`（狀態意思）、`B-biglandlord-sheet#b1`（異動後多久更新）↔ `#9`（產生中要等多久）、`E-bill-list#b1`（到時沒寄出的原因）↔ `#24`（何時寄出）。
  - 舊 S1b-1（2026-10-08，42 件）依 §9.9 作廢、不併入。
- **額度推算（照實）**：S1b 已耗約 0.97M（舊 S1b-1 0.22＋本次兩輪就緒審查約 0.17＋S1b-1 0.58）。以 S1b-1 實測 0.58M／批推算剩 6 批約 3.5M ⇒ 列舉結束約 4.45M，再加收尾（64 格盲判、命中重核、種入盲判）約 0.3～0.5M ⇒ **約 4.8～4.9M，會在收尾前後越過 4.5M 停止線**。依 §9.10「任一時點累計超過 4.5M ⇒ 停下回報」，已於 S1b-1 交件時先回報業主。
- **業主裁示**（2026-10-14，AskUserQuestion 逐字）：「停止線調到 5.2M，跑完 7 批 (Recommended)」（選項說明：「照 S1b-1 實測單價留約 0.3M 餘裕；全計畫仍在 14M 停止線內（估約 13M）。每批仍停下給你看」）⇒ **S1b 停止線 4.5M→5.2M**，全計畫 14M 不變；ASK 每批停點不變。
- **S1b-2**（2026-10-14，同 brief 只換批次參數）：交 52 件（22 粗目、引文 77 筆）、`snippets_reviewed` 691／691；實耗 **0.54M**、72 次工具呼叫、約 13 分鐘。覆蓋檢查 PASS、機械檢查 0 錯、讀取稽核第 3 版 0 命中（53 筆相對路徑 note，全為不存在的檔、未讀到內容）。
  - 去重：與 `existing` 同一問題 0 件（邊界 1：`C-community-estates#b8` 經理人是否必填 ↔ `#7` 哪些欄位必填）；**與 S1b-1 跨批重複 5 件**（D-contract-list、D-move-out、E-balance-invoice、G-power-meter、I-subscription-payment 各 1，皆保留 S1b-1 版、剔除 S1b-2 版）。成因：`existing` 凍結為 1,979 件、不含前批新件。另：各批 `#b` 流水號都從 1 起，跨批 `thing_id` 會撞號（如兩批皆有 `D-contract-list#b1`）⇒ 合併時以批次重新編號，逐件記對照。
  - **流程缺陷與修正（照實）**：代理 cwd 繼承主 session 派工當下的目錄——S1b-1 為 repo 根、S1b-2 為 `~/jgb-archive/p933-rebuild-20261014/work/p933`（主 session 專用區，含漏列詞表與外部對照）。兩批的相對路徑皆解析到不存在的檔、未讀到任何內容（稽核 note 逐筆「不存在」，0 筆存在），對清單 0 影響；但屬未設防。**自 S1b-3 起派工前先把 cwd 切到該批 `batch-S1b-<i>/`**，使相對路徑只會落在白名單內。
  - 累計：S1b 約 1.51M（停止線 5.2M）。
- **獨立評估（strategy-chain-verifier，2026-10-14）與期中量測**：評估判對題但推論鏈三處斷裂（種入放寬非證據、片段只占目錄集合約 9.5% 行、漏列 >3 即停而計畫內無完成路徑），並指出 S1b 的目的指標拖到最後才量。主 session 查證：`ContractEndedRentBillGuard.php`、`BillVirtualAccountHistoryService.php`、`BillDraftPeriodChecker.php`、`SinopacVaNotifyController.php` 在集合內卻 0 段（正對照 `UbotVaNotifyService.php` 有段）。**期中量測**（主 session 第三方，依 §9.4 (a)(b)）：S1b-1＋S1b-2 的 72 件對到漏列 16 錨點中 **0 個**（20 格中 0 格）；另 2 錨點（無手機 APP、幫助中心租客註冊教學）不在後端程式，後端列舉上限 14 錨點。之前回報的「覆蓋檢查 PASS」只代表片段全讀，⛔ 等於後端規則全看過（措辭過強，已更正）。
- **業主裁示**（2026-10-14，AskUserQuestion 逐字）：「C 先試跑帳務金流 1～2 批」（選項說明：「約 0.6～1.1M，量補到幾格再決定」）⇒ 依路徑名含帳務金流字樣的片段占比挑既有批次（不重切、不改片段）：**S1b-3（54%）→ S1b-6（47%）**；每批交件後主 session 立即依 §9.4 (a)(b) 量「漏列 20 格補到幾格」，與覆蓋、機械、稽核、去重一併回報，再由業主決定續跑、改走 A 或其他。⚠️ 挑批依據來自業主依漏列主題所下的指示，屬業主裁量；記此以免日後誤為主 session 依漏列事實切批（§9.7）。
- **S1b-3**（2026-10-14，C 路線第 1 批，帳務金流路徑占比 54%）：交 45 件（15 粗目、引文 51 筆）、`snippets_reviewed` 720／720；實耗 **0.52M**、71 次工具呼叫、約 12 分鐘；代理 cwd＝repo 根。覆蓋檢查 PASS；讀取稽核 0 命中（0 筆存在的相對路徑）；機械檢查 1 錯（`D-entrust-contract#b1` 引文 121 字 >120）⇒ 截去結尾分號、截後仍逐字命中原檔，記於 scratch `s1b-corrections.json`，重檢 0 錯。去重：與既有清單及 S1b-1／2 同一問題 0 件。
  - **目的指標期中量測**（主 session 第三方，§9.4 (a)(b)）：S1b-3 對到漏列錨點 **1 個**＝`p914-deposit-receipt-no`（`E-bill-list#b9` 收據號碼可否重複、`E-bill-list#b11` 押金收據功能是否每個團隊都有），計 **1 格**。**累計 3 批：漏列 20 格補到 1 格**（剩 19 格；≤3 須再補 16 格，其中 2 錨點不在後端程式）。
  - 累計：S1b 約 2.03M（停止線 5.2M）。依業主 C 裁示，交件後停下回報，由業主決定續跑 S1b-6、改走 A 或其他。
- **業主裁示**（2026-10-15，AskUserQuestion 逐字）：「A 停 S1b，漏列格列入凍結清單、進 S2 (Recommended)」（選項說明：「改計畫後送審、你核可」）⇒ S1b 停在 3 批（S1b-4～7 不跑）；修訂見 §9.13。
- **cwd 修正的實際限制**：主 session 的 Bash 無法把工作目錄停在 `/Users/chenqinghuang/p933-work-20261014/`（不在本 session 允許目錄，切過去即被重設回 repo 根）⇒ 改為：派工時 cwd＝repo 根（非 jgb-archive），代理的相對路徑若落在 repo 內既有檔即被讀取稽核 (a) 判命中、整批作廢；brief 已禁相對路徑。

**9.13 修訂：停 S1b、S1 收尾、進 S2（業主 2026-10-15「A 停 S1b，漏列格列入凍結清單、進 S2」；待就緒審查與業主核可）**

- **S1b 收束**：只計 S1b-1／2／3（片段版）；S1b-4～7 不跑。新增 25＋52＋45＝122 件，剔除跨批重複 5 件（§9.12）⇒ **淨增 117 件**；`existing` 去重 0 件剔除。thing_id 跨批撞號 ⇒ 合併時改為 `<coarse_id>#b<批>-<n>`（例 `D-contract-list#b1-1`），新舊對照表存 scratch `s1b-idmap.json` 並複製進驗證紀錄。
- **最終清單**＝目前清單 1,979 件＋S1b 淨增 117 件＝**2,096 件**，寫入 `inputs/askable-list-9.33-<日期>.json`（repo；內容是從程式與幫助中心整理的問題，不含客服原話）；機械檢查同 §2.2／§9.3（形狀、值域、id 唯一、粗目合法、引文逐字命中釘住匯出、客戶名詞表 0）。
- **完整性結論照實**：種入補回 4／10（未達，§9.4 已放寬）；外部對照：S1 原判對到 43／漏列 20／不屬 1，S1b 期中量測補到 1 格（`p914-deposit-receipt-no`）⇒ 主 session 判漏列 **19 格**（未達 ≤3）。業主選 A＝接受清單完整性維持此程度，**收尾盲判經業主裁定後的全部漏列格（主 session 現判 19）的事實全數列入 S2 凍結補內容清單**（以事實句所屬粗目歸位，回到 §2.3 原設計的「漏列格交 S2」，只是格數超過 3）。
- **S1 收尾驗證**（fresh verifier，看不到主 session 判定欄；BRIEF-CONTRACT v1）：①64 格依 §9.4 (a)(b) 標準對「最終清單」全數盲判，與主 session 判定不一致者列表交業主裁；②種入 10 對盲判（§2.3）；③重核 `hit-review.md` 全部命中判定（含 E、F＋G＋H、I 三筆邊界與 S1b 各批）；④重跑 `leak_check.py` 一致；⑤最終清單機械檢查重跑一致。通過 ⇒ `outline_plan_discipline.py --extract` 取證據 ⇒ `make audit` ⇒ commit 清單、驗證紀錄、計畫與證據（push 由業主自跑）。
- **驗收清單更新**：E4、E5、E14、E16、E19 皆加 2026-10-15 註記（見驗收檔）；E7 改以 commit 範圍檢查（見下）。

**9.13a 就緒審查第 1 輪處置（plan-verifier 2026-10-15：REVISE P2×4，全數 FIX）**
- **業主同意的書面依據**：A 選項的代價，主 session 於 2026-10-14 回報中的原文為「代價是清單完整性的證明維持在現在的程度，這要你明確接受」；同議題先前選項說明原文「清單完整性證明維持現狀（要你接受）」。2026-10-15 業主所選選項只寫「改計畫後送審、你核可」。⇒ **業主核可本修訂＝明示同意 E5／E16 未達、清單完整性未經證實**；核可提問須逐字列出此點，業主回答逐字記於本節。
- **收尾 verifier 的宣稱與範圍**：claim＝「Plan 9.33 S1＋S1b 收尾：最終清單 2,096 件（1,979＋S1b 淨增 117）符合 E1、E2、E6、E8、E14（3 批）；E3、E18 讀取稽核命中逐筆重核成立；E4 種入 4／10 照實記未達並完成 10 對盲判；E5、E16 64 格依 §9.4 (a)(b) 全數盲判、與主 session 判定的分歧逐格列表；E15 `leak_check` 重跑一致；E17、E19 書面依據在計畫」（E7 移出，見下）。**64 格與種入 10 對的盲判由另一位 verifier 執行（見「盲判的機制保證」），本 verifier 只引用其落檔結果。**
  - **通過判準**：上列每項的機械檢查通過，且 64 格、種入 10 對的分歧**逐項列表**（分歧本身不算失敗）⇒ CONFIRMED。
  - **順序（只有一種讀法）**：verifier CONFIRMED → 主 session 把分歧表交業主逐項裁 → 業主裁定逐字寫入計畫 §8、漏列格最終集合寫入驗證紀錄 → `--extract`（證據 base＝當時 HEAD，claim 範圍不因裁定改變，⛔ 重驗）→ `make audit` → commit。
- **失敗去向**：
  - ① 64 格或 ② 種入盲判：verifier 無法完成判定（輸入缺漏、讀取稽核命中）⇒ 該次作廢、修正輸入後重派一次；再失敗 ⇒ 停、交業主。
  - ③ 命中重核發現某批**真的讀到白名單外內容**：A 之下不重派——**該批產出的件從最終清單剔除**（S1b 批整批剔；S1 列舉或完整性批若受影響 ⇒ 因占比大，停下交業主），清單件數重算、機械檢查重跑。
  - ④ `leak_check` 重跑結果與 §9.2 記錄不一致（任一受檢檔命中、或正對照 ≠ 33／33）⇒ 停、交業主。
  - ⑤ 最終清單機械檢查失敗：純形狀／引文抄錯（同 `corrections.json` 先例）⇒ 主 session 依原檔更正、逐件記錄、重跑；涉及事實或粗目歸屬 ⇒ 停、交業主。
- **盲判的機制保證**（收尾審查第 2 輪 B1 修正：拆成兩位 verifier）：**盲判 verifier** 只做 ① 64 格與 ② 種入 10 對、⛔ 讀計畫／驗收／HANDOFF；**收尾 verifier** 做其餘項目並引用盲判落檔。盲判輸入放獨立目錄 `~/jgb-archive/p933-blind-20261015/`，只含：64 格的 `cell_id`＋事實句（無任何判定欄）、最終清單（`thing_id`＋`question`＋`coarse_id`）、種入 10 件與各批完整性代理新增項（無主 session 配對結論）、判準 (a)(b) 與 §2.3 規則原文。**盲判 verifier 禁讀**：`~/jgb-archive/p933-rebuild-20261014/` 整個目錄（含 `ext64-verdicts.json`、`seed-pairs.md`、`leak-terms.txt`）＋**整個 spec 目錄** `/Users/chenqinghuang/dev/work/AIChatbot/.kiro/specs/knowledge-outline-and-intent-architecture/`（計畫 §8、§9.12 寫有主 session 的補回判定與對到 thing_id）。盲判結果落檔 `~/jgb-archive/p933-blind-20261015/verdicts.json` 後才交收尾 verifier。命中重核（③）不需盲，所需的 transcript 與 `hit-review.md` 另以副本放 `~/jgb-archive/p933-blind-20261015/hits/`。**稽核**：主 session 以路徑掃描稽核盲判 verifier transcript——工具參數或輸出出現 `p933-rebuild-20261014`、`knowledge-outline-and-intent-architecture` 或 `plan-9.33`、`acceptance-9.33` 即命中；正對照兩筆：合成「讀 `ext64-verdicts.json`」與「讀 plan-9.33 計畫檔」的紀錄皆須判命中；結果附驗證紀錄；命中 ⇒ 該次盲判作廢、換人重派一次。
- **E7 基準**（收尾審查第 2 輪 B2 修正）：原基準 `p930/foreign-fp.txt` 在 2026-10-13 清空的 scratch 內、未重建（磁碟查無）。改為**列名清單**：commit 時 staged 路徑必須 ⊆ {`inputs/askable-list-9.33-<日期>.json`、`inputs/askable-verify-9.33-<日期>.md`、`inputs/plan-9.33-coverage-askable-list-20261007.md`、`acceptance-9.33-20261007.md`、`verification/<本次證據>.json`}（皆本 spec 目錄下）。開工時已存在、不在清單內的未提交改動（例：本目錄 `design.md`、`requirements.md`、`HANDOFF-20260923.md`、`inputs/plan-9.23／9.24／9.28-*.md` 的 8GB 加註；站內幫手線的 `services/jgb/`、`docs/api/` 等）一律 ⛔ staged。E7 **移出收尾 verifier 的 claim**，由主 session 在 staging 之後機械檢查：`git diff --cached --name-only` 逐行比對清單，輸出存進 `askable-verify-9.33-<日期>.md`（隨 commit）；正對照＝對同一份清單比對 `design.md` 必判「不在清單」。不符 ⇒ 不 commit、修正 staging。
- **S2**：照 §3 原設計；開工前另送就緒審查（§1「S2 細節開工前另送就緒審查」）。
- **額度**：S1 收尾驗證約 0.4M；9.33 至今約 6.1M＋S1b 2.03M＋審查；S2 估約 1.7M；全計畫停止線 14M 不變。
- **不做**：S1b-4～7；第三輪列舉；把漏列事實交任何列舉代理。

- **§9.13 就緒審查紀錄**：第 1 輪（plan-verifier 2026-10-15）REVISE P2×4 ⇒ 全數 FIX（§9.13a）。收尾第 2 輪（plan-verifier 2026-10-15）：第 1 輪四條中三條關閉；新 REVISE P2×2（種入盲判因讀計畫而不盲、E7 判準過寬且無人驗）⇒ 依規則第二次 REVISE 停止自動送審、逐條處置：B1 **FIX**（盲判拆給獨立 verifier、禁讀整個 spec 目錄、稽核加樣式與兩筆正對照）、B2 **FIX**（E7 改列名清單、移出 verifier claim、由主 session staging 後機械檢查＋正對照）。新 readiness epoch ⇒ 送**一次**收尾審查；再 REVISE 即停下交業主。
- 收尾審查（新 epoch 唯一一次，plan-verifier 2026-10-15）：**READY**。待業主核可（核可提問須逐字列出「明示同意 E5／E16 未達、清單完整性未經證實」）。
- **業主核可**（2026-10-15，AskUserQuestion 逐字）：「核可，同意 E5／E16 未達、清單完整性未經證實 (Recommended)」（問題原文：「核可大綱線 Plan 9.33 §9.13（停 S1b、S1 收尾、進 S2）嗎？核可＝明示同意「E5／E16 未達、清單完整性未經證實」。」）⇒ 執行 S1 收尾。
- **S1 收尾盲判**（blind-judge，2026-10-15；輸入 `~/jgb-archive/p933-blind-20261015/`、24 個分檔皆整檔讀過、讀取稽核 `blind_audit.py` 0 命中〔自測 3／3〕）：64 格 對到 36／漏列 26／不屬 2；種入補回 4／10，與主 session 同 4 件（`B-advanced-settings#17`、`E-bill-create-edit#22`、`I-subscription-payment#11`、`I-control-panel#14`），**種入 0 分歧**。64 格與主 session（對到 44／漏列 19／不屬 1）分歧 12 格（10 條事實）：主對到→盲漏列 9、主對到→盲不屬 1、主漏列→盲對到 2；逐格表 scratch `divergence-64.json`。
- **業主裁定**（2026-10-15，AskUserQuestion 逐字）：「照建議：9 條採盲判，第 5 條維持對到 (Recommended)」（第 5 條＝`p914-contract-invite-account-match` 3 格，維持對到 `D-contract-sign-view#36`；其餘 9 條事實採盲判）⇒ **64 格最終：對到 39／漏列 23／不屬可問的事 2**；23 格漏列事實全數列入 S2 凍結補內容清單（scratch `ext64-final-20261015.json`）。
