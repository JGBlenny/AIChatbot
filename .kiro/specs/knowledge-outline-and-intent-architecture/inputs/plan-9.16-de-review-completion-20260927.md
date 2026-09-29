# Plan 9.16：D／E 兩架已審收尾（生成器保留已審＋修正疑慮細目＋第二批交審）

> 狀態：**S1～S4 完成（2026-09-27）**；終點 pm 62→137、prospect 10→18，收案後抽驗撤 1 條 ⇒ **最終 pm 136、prospect 17**。業主核可：D1 沿用「修一次仍不過就整句刪」；D2 內容一改就重審；D3 上限 4M、3.2M 先停（S4 時約 2.99M，含收案後抽驗約 3.13M）。ASK 模式。commit：S1＋S2 `3642733c`、S3＋S4 `496369d2`、抽驗撤回 `5d188b37`。
> **終點指標（本計畫起點，`endpoint_progress.py` 2026-09-27）**：`已審細目 pm 62／535、prospect 10／121；頁面 pm 24／183、prospect 7／183`（D pm 20／104、prospect 1／9；E pm 42／96、prospect 9／21）。
> **本計畫預期**：S4 完成時 D／E **pm 最多 +138、prospect 最多 +20**（＝D／E 尚未已審的全部；以業主審過為準）；S1～S3 為 +0，皆為 S4 的前置。
> 上游：Plan 9.15 §6（S4 先審結果、doubt 61 條、⚠️ 8 組、B7 未跑）；記憶 `feedback_endpoint_metric_first`、`project_ledger_p914_scope_errors`。

## 0. 為什麼有這份

Plan 9.15 只讓 D／E 200 條中的 62 條通過（目標最多 200）。剩下 138 條卡在三處：
- **61 條 doubt**：先審抓到的範圍錯，多數是 9.10 原稿（既存 vs 電子範本、社宅各範本、註冊 vs 免註冊、特定合作團隊、權限、舊元件或幫助中心舊標籤）。
- **8 個 ⚠️ 組的 53 條 pass**：同組錯誤率 >30%，業主裁「本批不審」。
- **B7 的 24 條**（`E-virtual-account`、`E-payment-onboarding`）：預算用盡未先審。

而且 **現在不能動正本內容**：`drafts_to_canon.py` 每次重跑會整架重寫、抹掉已審標記（grep `reviewed` 0 命中），已審的 62 條會歸零。所以第一片必須先讓生成器保留已審。

## 1. 切片

### S1 — 生成器保留已審＋已審數不下降守門（預期終點 +0；是 S2～S4〔pm 最多 +138〕的前置）

- **做**：`drafts_to_canon.py generate` 新增保留邏輯：
  1. 生成前讀 `--front-matter-from` 目錄（現行正本）裡每條細目的 `reviewed`（`{by, at}`）與**內容指紋**（標題＋句子＋`sources`＋`target_user`＋`business_types`＋`instance_applicability` 的 sha256）。
  2. 生成新正本時，細目 id 相同且內容指紋相同 ⇒ 在 `- sources:` 之後寫回原 `reviewed` 行；指紋不同 ⇒ **不寫回**（內容改了就要重審），並列入 `reviewed-dropped-<日期>.json`。
  3. 新旗標 `--expect-reviewed-kept N`：保留數 ≠ N 即大聲失敗；未給時只印保留數與丟棄清單。**保留／丟棄的計算與這個比對，都在記憶體中建好九架全文之後、寫入 `--canon-root` 或 `--runs-out` 任何檔案之前完成**（現行 `generate` 是先寫九架再核其他數字——本檢查不得照那個順序，否則比對失敗時已審標記早已被覆寫）。`reviewed-dropped-<日期>.json` 也在比對通過後才寫。
- **守門測試**（`rag-orchestrator/tests/unit/skills/outline_curation/test_outline_curation_drafts_to_canon_req.py` 新增）：
  - 合成正本 2 條已審（1 條內容不變、1 條改了一句）＋1 條未審 ⇒ 生成後恰保留 1 條、丟棄 1 條且列入清單、未審者不會變成已審。
  - 變異：拿掉寫回 ⇒ 測試紅。
  - `--expect-reviewed-kept` 不符 ⇒ 非 0 結束，**且沒有留下任何輸出**：canon-root 的 `jgb/` 不存在；若測試先放了舊正本，則與測試前逐位元組相同（沿用既有測試的 `assert not (canon_root / "jgb").exists()` 寫法）。
- **擁有（只准改這些）**：`.claude/skills/outline-curation/scripts/drafts_to_canon.py`、`.agents/skills/outline-curation/scripts/drafts_to_canon.py`（鏡像）、`rag-orchestrator/tests/unit/skills/outline_curation/test_outline_curation_drafts_to_canon_req.py`。⛔ 動 `rag-orchestrator/canon/`、`runs/outline-20260920/` 既有檔、其他工作線的未提交檔。
- **驗收**：
  - 現樹實跑（**只寫到 scratchpad**）：`--canon-root <scratchpad>/p916-s1-canon`（先複製現行 `rag-orchestrator/canon/` 進去當 `--front-matter-from` 與輸出根）、`--runs-out <scratchpad>/p916-s1-runs`、`--date 20260927`、`--expect-reviewed-kept 62`、`--expect-open-questions 54` ⇒ 保留 62、丟棄 0；scratchpad 產出的 `jgb/*.md`、`jgb.json`、`CATALOG.md` 與 `rag-orchestrator/canon/` 逐位元組相同（`cmp`），`open-questions-20260927.md` 與 repo 內同名檔相同
  - 同一實跑改 `--expect-reviewed-kept 61` ⇒ 非 0 結束，且 scratchpad 輸出根與執行前逐位元組相同
  - 全套單元紅燈＝既有 9 條；`make audit` PASS
  - `.agents/` 鏡像同步（`cmp`）
- **不做**：改 `canon_parser`、改已審標記格式。
- **回滾**：改前備份 `drafts_to_canon.py`（兩份鏡像）與該測試檔到 scratchpad，以備份還原。
- **預算**：主 session 直接做＋fresh verifier 1 位（約 0.2M）。
- **停止**：現樹重生成後保留數 ≠ 62，或正本任何位元組變動。

### S2 — 修正 61 條 doubt 與 B7 先審（預期終點 +0；是 S4 的前置）

- **輸入**：
  - 61 條 doubt＝`scratchpad/p915-s4-results.json` 的 `B1`～`B6` 各自 `doubt`（細目 id → 一句疑點）；審核單 `review-sheet-9.15-S4-DE-20260927.md` 同內容。疑點只有一句話、⛔ 不是逐句證據 ⇒ 主 session 修之前要自己回 jgb2 釘版匯出 `scratchpad/jgb2-b2ee2ac`（⛔ 直讀 `/Users/chenqinghuang/dev/work/jgb2/`）對碼。
  - B7＝粗目 `E-virtual-account`、`E-payment-onboarding` 共 24 條（9.15 未先審）。
  - ⛔ 不動：已審 62 條（清單 `scratchpad/p915-s4-approved.json`）、⚠️ 組原本 pass 的 53 條（留給 S3 重審）。
- **做法（沿用 9.15 S3 最後有效的方式）**：
  1. **B7 先審**：fresh verifier 對 24 條做 9.15 S4 式先審（pass／doubt＋一句理由），結果存 `scratchpad/p916-s2-b7-results.json`。
  2. **主 session 親修**：對 61＋B7 doubt 逐條對碼後改寫 `drafts-D.json`／`drafts-E.json`（⛔ 派 executor 起草——9.15 三批 executor 初稿全被退回）；細目 id 不改；`sources` 須能對回每句。**只准改 doubt 集合（61 條＋`p916-s2-b7-results.json` 的 doubt）內的細目**，其餘 D／E 細目（含已審 62、⚠️ 組 pass、B7 pass）任何欄位（含講法）⛔ 改。每一處改動寫進修正紀錄 `inputs/fix-log-9.16-S2-DE-<日期>.md` 的表格，一列一項：`細目 id｜欄位（title／sentences／phrasings／sources／target_user／business_types／instance_applicability／open_questions）｜句序（sentences 才填）｜動作（改／新增句／刪句／刪細目）｜依據（檔案路徑＋可 grep 符號）｜verifier 判定`。
  3. **fresh verifier 逐項核**（依粗目分 3～4 批、序列，每批一位新 verifier）：核修正紀錄的**每一列**（不只句子與標題），判過／不過＋證據；不過的主 session 再修一次，**仍不過就整句刪**（D1）。某細目句子全刪 ⇒ 整條細目刪除，列入修正紀錄「刪除」節並在回報中點名（終點分母會減少）。
  4. **機械差異比對**（主 session 寫 `scratchpad/p916_s2_drafts_diff.py`，可重跑）：以 `scratchpad/p916-s2-backup/` 的 drafts 為基準，逐細目 id、逐欄位列出改動與刪除；sentences 以序列對齊（`difflib.SequenceMatcher`）報出改／新增／刪除，句序一律用**備份側**的句序（新增句用插入位置），避免刪一句後後面全部誤報為改動；再與修正紀錄表格比對。另做**結構比對**：細目 id 集合（除修正紀錄「刪除」節外不得增減）、粗目清單／粗目標題（`coarse` 鍵）與順序、每條細目所屬粗目與粗目內順序、各檔頂層鍵，須與備份完全相同——S2 ⛔ 新增細目、⛔ 搬移細目、⛔ 動粗目。
  5. drafts JSON 維持原格式（`drafts-D.json` indent 1＋結尾換行；`drafts-E.json` indent 1、無結尾換行）。
- **生成**：S1 的新生成器、容器內跑（主機缺 psycopg2）；`.claude/` 在容器內唯讀，runs 目錄另掛可寫：`docker compose -f docker-compose.dev.yml run --rm -T --no-deps -v $PWD/.claude/skills/outline-curation/runs/outline-20260920:/runs-rw rag-orchestrator python /.claude/skills/outline-curation/scripts/drafts_to_canon.py generate --drafts-dir /runs-rw --coarse-ids /.kiro/specs/knowledge-outline-and-intent-architecture/inputs/coarse-ids-20260921.md --front-matter-from /app/canon/jgb --canon-root /app/canon --runs-out /runs-rw --date <日期> --expect-reviewed-kept 62 --expect-open-questions <N>`（N＝生成前從九架 drafts 實算的 `open_questions` 數，寫進修正紀錄）。先在 scratchpad 試跑一次（照 S1：複製 `rag-orchestrator/canon` 到 `scratchpad/p916-s2-trial-canon`，加 `-v <scratchpad>:/scratch`，`--front-matter-from /scratch/p916-s2-trial-canon/jgb --canon-root /scratch/p916-s2-trial-canon --runs-out /scratch/p916-s2-trial-runs`），全部 `--expect-*` 通過才對 repo 跑（`--expect-open-questions` 是先寫後核，試跑就是為了擋這條）。
- **驗收**：
  - 生成器印出 `已審保留：62 條／丟棄：0 條`；`load_canon_or_die` 通過（generate 內建）
  - A B C F G H I 七架 `.md` 與改前備份逐位元組相同（`cmp`）
  - 差異比對（最終位元組上跑）：(a) 改動／刪除項集合＝修正紀錄表格的列集合，不多不少；(b) 改動細目 id ⊆ doubt 集合；(c) doubt 集合以外的每條 D／E 細目（含已審 62、⚠️ 組 pass、B7 pass）所有欄位含講法 0 改動；(d) 刪除的細目 id＝修正紀錄「刪除」節；(e) 每列 verifier 判定為「過」或動作為刪句／刪細目；(f) 結構差異數＝0。正對照：基準對自己比 ⇒ 0 項；scratch 副本故意改一條已審細目的講法 ⇒ (c) 報出；scratch 副本把一條細目搬到另一粗目、另加一條新 id ⇒ (f) 報出並點名兩者。最終與正對照的輸出都存進修正紀錄
  - 洩漏掃描 `~/jgb-archive/ruler-9.13/scripts/leak_scan.py` 對新正本：新增命中只准是規則一已放行的產品用語（見 9.15 紀錄），否則修掉
  - 全套單元紅燈＝HANDOFF §4 既有 9 條；`make audit` PASS
  - 終點指標：M1 已審 pm 62／prospect 10 不變（S2 為 +0）
- **擁有**：`runs/outline-20260920/drafts-D.json`、`drafts-E.json`、生成器寫出的 `open-questions-<日期>.md`／`dsp-068-deletions-<日期>.json`／`reviewed-dropped-<日期>.json`；`rag-orchestrator/canon/`（只透過重生成）；`inputs/fix-log-9.16-S2-DE-<日期>.md`；`docs/knowledge/jgb-product-facts.md`（只在修正涉及帳本條目時，改法同 9.15 的 ⚠️ 更正註記）。⛔ 其他工作線的未提交檔。
- **回滾**：改前備份 `drafts-D.json`、`drafts-E.json`、`rag-orchestrator/canon/`、`jgb-product-facts.md`，以及 `runs/outline-20260920/` 現有的 `open-questions-*.md`／`dsp-068-deletions-*.json` 到 `scratchpad/p916-s2-backup/`，以備份還原；本片新產生的 `runs/outline-20260920/reviewed-dropped-<日期>.json`（及任何備份中沒有的新日期產出檔）一併刪除。
- **預算**：約 1.8M（親修由主 session 做，成本主要在 B7 先審＋3～4 批 verifier）；一次一位代理。
- **停止**：已審保留數 ≠ 62；七架任一位元組變動；某粗目修完仍有 >30% 句子不過（停下交業主，不硬修）；累計達 3.2M。

### S3 — 第二批代理先審（預期終點 +0；是 S4 的前置）

- **對象（分母）**：D／E 所有**尚未已審**的細目＝以 `rag-orchestrator/canon/jgb/D.md`／`E.md`（commit `3642733c` 後）實算「無 `- reviewed:` 行的細目」，預期 138 條（200 − 62；S2 未刪細目）。清單先存 `scratchpad/p916-s3-targets.json`，數目≠138 即停查原因。
- **做法**：沿用 9.15 S4 先審 brief（逐句對源⛔抽樣、可答性、本線反覆出錯類型、判 doubt 門檻；原文存 `scratchpad/p915-s4-last-brief.txt`），改兩處：①範圍不再寫「粗目底下全部細目」，改為**明列本批細目 id 清單＋「預期 N 條」**（取自 targets，已審細目不在內）；②加「現行 vs 舊路徑」提醒（S2 發現的 `addMerchant`／舊 blade／`bills.one` 類型），並點名 §6 留給 S3 的兩點（`newebpay-precondition` 句 0 只適用 `getPaymentVendor`；藍新開通勾選框未綁 enabled）。依粗目分 5 批、每批 ≤35 條，**派工前先把 id→批次對照存 `scratchpad/p916-s3-batches.json`**（批次聯集＝targets、兩兩不交），每批一位 fresh verifier、序列、一次一位；每條輸出 `pass` 或 `doubt｜句序｜理由｜證據`。每批被採用的 verifier 最終訊息**逐字存檔** `scratchpad/p916-s3-raw-<批次>.txt`（⛔ 摘要或改寫）；`scratchpad/p916-s3-results.json` **只由 `p916_s3_sheet.py parse` 從 raw 檔解析產生**（⛔ 手填）。解析時某批缺 id、多 id、行格式不符、或 doubt 缺證據 ⇒ 視同交不出件（重派一次，再失敗即停）。
- **審核單**：`inputs/review-sheet-9.16-S3-DE-<日期>.md`，**由腳本 `scratchpad/p916_s3_sheet.py` 從 results＋正本標題機械產生**（⛔ 手抄），依粗目分組（格式同 9.15 S4 審核單）：表頭記正本 commit `3642733c`；每組列 pass 細目（id＋標題）、doubt 清單（id＋一句理由）；doubt 比例以**該組 targets 條數**為分母，>30% 的組標 ⚠️ 並建議「本批不審」。⛔ 寫入題目原文。
- **驗收**：
  - 已判細目 id 集合＝`p916-s3-targets.json`，不多不少，每條恰一個判定；pass＋doubt＝138
  - **三段對帳**（同一腳本的 `check` 模式，可重跑）：①重新解析全部 raw 檔，與 results 逐 id 比對標籤 ⇒ 不符數＝0；②把最終審核單解析成各組 pass／doubt／未先審 id 清單，須與 results 依 `3642733c` 正本粗目歸組的結果逐條相同（標籤一致、組別一致、⚠️ 旗標符合 >30% 規則、無 targets 以外 id；未判的 targets 只能出現在「未先審」）⇒ 不符數＝0。正對照兩個：scratch raw 副本把一條 doubt 行改成 pass ⇒ ①報出該 id；scratch 審核單副本把一條 doubt 搬到 pass ⇒ ②報出該 id。三次輸出記入 §6
  - **部分審核單**（3.2M 停點觸發時）：未先審的細目列在所屬粗目的「未先審」小節；含未先審細目的粗目，組標題標「⛔ 本組有未先審細目，不可整組回『過』」，S4 對這些組只能逐條處理 pass 細目
  - `rag-orchestrator/canon/`、drafts 與七架本片 0 變動（`git diff --stat 3642733c -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 為空）
  - 終點指標不變（M1 pm 62、prospect 10）；審核單依粗目的條數加總＝138
- **擁有**：`inputs/review-sheet-9.16-S3-DE-<日期>.md`、本計畫 §6；scratchpad 的 raw 檔、results、批次對照與 `p916_s3_sheet.py`。⛔ 改正本、drafts、帳本。
- **回滾**：只新增審核單，刪除即可。
- **預算**：約 1.0～1.2M（5 批 × 約 0.2M）；累計預期約 2.6M，低於 3.2M 停點。
- **停止**：累計達 3.2M 即停交業主（未審完的批次列入審核單「未先審」）；某批 verifier 交不出件（依記憶 `feedback_verifier_agent_delivery`）重派一次，再失敗即停。

### S4 — 業主終審＋寫入已審（**預期終點 pm 最多 +138、prospect 最多 +20**）

- 業主依粗目回「過」；doubt 只能「本批不審」或「照原樣過」。
- **業主裁決（2026-09-27）**：「安全組過、⚠️組不審」＝非 ⚠️ 的 11 組 pass 細目標已審（預期 75 條）；⚠️ 5 組（D-contract-edit-social-housing、D-contract-sign-view、D-move-out、D-early-termination、D-notary）全組本批不審；40 條 doubt 全數本批不審。
- **核可清單（機械產生）**：由 `p916_s3_sheet.py` 從審核單＋results 取「非 ⚠️ 組的 pass id」存 `scratchpad/p916-s4-approved.json`（⛔ 手選），清單須＝results 中 verdict=pass 且所屬組未標 ⚠️ 的 id 集合，條數＝75。
- 寫入方式同 9.15 S4：只在 `rag-orchestrator/canon/jgb/D.md`／`E.md` 核可細目的 `- sources:` 行之後加一行 `- reviewed: {by: owner, at: 2026-09-27}`（與既有 62 條同格式、同位置，使日後重跑生成器可保留）；以 `export_json`／`export_catalog` 重匯出 `jgb.json`／`CATALOG.md`；⛔ 重跑生成器；改前備份 `canon/` 到 `scratchpad/p916-s4-backup/`。
- **驗收**：
  - `git diff` 的 D.md／E.md 只有新增 `- reviewed:` 行（刪除行 0），新增行數＝75；A B C F G H I 與 `CATALOG.md` 位元組不變（CATALOG 若含已審欄位則只准該欄變）
  - 正本中帶 `- reviewed:` 的細目 id 集合＝既有 62 條 ∪ `p916-s4-approved.json`（逐 id 比對，⛔ 只比條數）；⚠️ 組與 doubt 細目 0 條被標
  - `load_canon_or_die` 通過；終點指標 `endpoint_progress.py` pm＝62＋本批 pm 對象條數、prospect＝10＋本批 prospect 對象條數
  - 全套單元紅燈＝既有 9 條；`make audit` PASS；fresh outcome verifier（對上述逐條）
- **擁有**：`rag-orchestrator/canon/jgb/D.md`、`E.md`、`jgb.json`、`CATALOG.md`；本計畫 §6；HANDOFF 開頭終點指標行。⛔ drafts、七架、其他工作線檔。
- **回滾**：以 `scratchpad/p916-s4-backup/` 還原（已審數下降 ⇒ 須業主明示）。
- **預算**：寫入由主 session 做；outcome verifier 約 0.15M ⇒ 累計約 3.0M（3.2M 停點內）。
- **停止**：新增行數≠75、任何刪除行、id 集合不符 ⇒ 還原備份並停。

## 2. 不做（另案）

- 其餘七架（A B C F G H I）。
- `ruler-9.12` 3 題 gold 被刪的重映支援（9.15 已記為已知破壞）。
- jgb2 缺陷交產品（`inputs/doc-fix-list-9.15-G1-20260927.md` 已有，另加兩條：提前解約中兩個「點交物件」、Email 認領以明文比對密文）——另開單。
- 9.11 的 commit。

## 3. ⏳ 待業主裁

- **D1**：S2 沿用 9.15 的「修一次仍不過就整句刪」嗎？（建議：沿用）
- **D2**：S1 的保留規則——內容一改就丟掉已審、要重審（建議），還是只要 id 相同就保留？前者安全、後者省審核工時但會讓改過的內容帶著舊的已審標記進模型。
- **D3**：預算上限 4M（S1 0.2＋S2 1.8＋S3 1.2＋verifier 預留 0.8）；累計達 3.2M 先停交業主看剩餘量。

## 4. 停止條件（全片共用）

- 已審細目數（M1）任何時候下降 ⇒ 停下交業主。
- 正本 sha 只准在 S2（重生成）與 S4（只加 `reviewed`）變動；其他片變動 ⇒ 停。
- 累計 `subagent_tokens` 達 3.2M 先停交業主；超過 4M ⇒ 停。
- 一次只跑一個代理（本機 8GB）。

## 5. 就緒審查紀錄

- 大綱（fresh plan-verifier，2026-09-27）＝**READY**。
- S1 第 1 輪＝REVISE P2×2，全 FIX：`--expect-reviewed-kept` 須在寫任何檔之前比對（現行 generate 先寫後核，照搬會在失敗時已抹掉已審）＋不符時無輸出的測試；S1 缺擁有清單 ⇒ 列三個擁有檔，驗收實跑改為只寫 scratchpad 再 `cmp`。
- S1 第 2 輪＝**READY** ⇒ 大綱＋第一個可執行片皆 READY，交業主核可（`next_gate: user_approval`）。S2～S4 開工前各自再過就緒審查。
- 業主 2026-09-27 核可：先做 S1；D1 沿用；D2 內容一改就重審；D3 4M／3.2M。（業主回覆原文未留存，此句為主 session 摘述。）
- S3 第 1 輪＝REVISE P2×1，FIX：審核單只對帳條數，doubt 誤列 pass 會在 S4 被業主一併標已審 ⇒ 審核單改由腳本從 results 機械產生，加逐條對帳（含正對照）。P3 一併採納：batch brief 明列 id 與預期條數（避免重判 59 條已審）、派工前固定 id→批次對照、輸出缺漏／格式錯視同交不出件、⚠️ 分母＝該組 targets、審核單表頭記 commit、brief 點名 §6 留給 S3 的兩點。
- S3 第 2 輪＝REVISE P2×1：審核單對帳的是 results，但 verifier 原始輸出→results 這一步沒有檔也沒有檢查，轉錄時 doubt 誤成 pass 照樣全綠。**兩輪自動 REVISE 已達上限，主 session 裁決：FIX**（raw 逐字存檔、results 只由腳本解析產生、check 加 raw↔results 對帳＋正對照）；P3（停點觸發時的部分審核單）FIX（未先審細目只能列「未先審」、含未先審的粗目不可整組回過）；P4（untracked 檔不在 diff --stat）接受風險（S3 不寫 runs）。⇒ 新就緒紀元，開**唯一一次**收尾審查；再 REVISE 即暫停交業主。
- S2 第 1 輪＝REVISE P2×2，全 FIX：①「改過的句子」只來自自報的修正紀錄、沒有獨立分母 ⇒ 加機械差異比對（drafts 對備份逐欄位），改動集合須＝修正紀錄；② doubt 以外的細目沒有 0 改動檢查，且講法不在指紋內，改已審細目的講法會帶著舊已審標記過關 ⇒ 只准改 doubt 集合，其餘細目所有欄位含講法 0 改動，附正對照。P3 附帶修正：試跑指令補掛載、回滾備份加 runs 產出檔、verifier 核修正紀錄每一列（不只句子）。
- S2 第 2 輪＝REVISE P2×1：差異比對只看既有細目的欄位，新增細目、搬移細目（指紋不含所屬粗目 ⇒ 已審細目搬家仍保留標記）、改粗目都漏網。**兩輪自動 REVISE 已達上限，主 session 裁決：FIX**（加 (f) 結構比對＋正對照；S2 明文禁新增／搬移細目與動粗目）；P3（回滾未刪新產出檔）FIX。⇒ 新就緒紀元，開**唯一一次**收尾審查；再 REVISE 即暫停交業主。
- S3 收尾審查（fresh plan-verifier）＝**READY** ⇒ 交業主核可（`next_gate: user_approval`）。
- S2 收尾審查（fresh plan-verifier）＝**READY** ⇒ 交業主核可（`next_gate: user_approval`）。成本：三輪 plan-verifier 約 0.16M，9.16 累計約 0.3M／4M。

## 6. 執行紀錄

### S1（2026-09-27，主 session 直做）

- 備份：`scratchpad/p916-s1-backup/`（兩份鏡像＋測試檔）。
- 實作：`drafts_to_canon.py` 新增 `fine_blocks`（內容指紋）、`carry_reviewed`（寫回／丟棄，純記憶體）；`generate` 在引號平衡守門之後、寫任何檔之前算保留／丟棄並比 `--expect-reviewed-kept`，通過後才寫 `reviewed-dropped-<日期>.json` 與九架。`.agents/` 鏡像 `cmp` 相同。
- 測試：新增 3 條（保留／丟棄、不符時無輸出、不符時既有正本逐位元組不變）；該檔 12／12 綠。突變（拿掉寫回那一行）⇒ `test_reviewed_kept_when_unchanged_and_dropped_when_changed` 紅，還原後 `cmp` 相同。
- 現樹實跑（容器、只寫 scratchpad `p916-s1-canon`／`p916-s1-runs`）：`已審保留：62 條／丟棄：0 條`；`jgb/*.md`、`CATALOG.md`、`jgb.json`、`README.md` 共 12 檔與 `rag-orchestrator/canon/` 逐位元組相同；`open-questions-20260927.md`、`dsp-068-deletions-20260927.json` 與 repo 相同。正對照：同一 `cmp` 對 9.15 S4 前備份的 `D.md` 報差異。
- `--expect-reviewed-kept 61` ⇒ exit 1、`❌ 已審保留 62 條，與預期 61 條不符（丟棄 0 條）；未寫任何檔`；輸出根 15 檔 shasum 與執行前相同。
- 全套單元：3931 過、紅 9＝HANDOFF §4 既有名單；`make audit` PASS；`rag-orchestrator/canon/`、`runs/outline-20260920/` 無變動。
- 設計註記：講法（phrasings）不在指紋內（照 S1 定義），只改講法不會丟掉已審。
- fresh verifier：首輪 INCONCLUSIVE（唯缺 `make audit`——brief 禁碰常駐容器）⇒ 主 session 在最終位元組上重跑並留完整 log `scratchpad/p916-s1-audit.log`（含三檔 shasum、HEAD）⇒ 同一 verifier 核 shasum 一致、判讀 PASS ⇒ **CONFIRMED**。已親跑：62／61 實跑、12／12、變異紅、全套紅 9＝既有、邊界探針（換架保留、刪除 `fine_removed`、標題／句子／屬性任一改 ⇒ `content_changed`、未審不變已審）。
- DEFER（P4）：`fine_blocks` 略過所有 `  - ` 開頭行與空行，比「只排講法子項」寬；現行 541 條無此類非講法行，只有未來正本新增巢狀清單欄位時才有影響 ⇒ 屆時改成只略過 `  - {`。
- 成本：verifier 約 0.1M（累計約 0.1M／4M）。**S1 完成（終點 +0，S4 前置）。**

### S2（2026-09-27 起，業主核可、ASK 模式）

- 備份 `scratchpad/p916-s2-backup/`（`runs/` drafts-D／E＋open-questions／dsp-068 兩個日期、`canon/`、`jgb-product-facts.md`）。
- 工具：`scratchpad/p916_s2_drafts_diff.py`（正對照：基準對自己 0 項 PASS；改已審細目講法 ⇒ (c) 報出；搬細目＋加新 id ⇒ (f) 點名兩者；修正紀錄漏列／多列／未過 ⇒ (a)(d)(e) 報出）；`scratchpad/p916_edit.py`（drafts 讀寫逐位元組往返相同、只准改 doubt 集合）。
- **B7 先審**（fresh verifier，0.21M）：**pass 9／doubt 15（62%）**，結果 `scratchpad/p916-s2-b7-results.json`。doubt 主因：金流開通段對到**已不被路由的舊路徑**（`addMerchant`／舊 blade），現行走 `getPaymentVendor`；個人房東停用藍新等三家、另有「愛金卡」；虛擬帳號段混了立即／排定銷帳、漏權限與「以人為主／以物件為主」模式、特定客戶註解。doubt 集合＝61＋15＝**76**（`scratchpad/p916-s2-doubt.json`）。
- 親修完成：76 條 doubt 全改（213 項、75 條細目有改動——此為當時計數；2026-09-29 補驗重算，最終修正紀錄為 219 列、76 條細目，講法淨 −3，以下方「收尾」與修正紀錄為準；`payment-gateway-options` 一度漏修，差異比對對 doubt 集合時抓出後補修），差異比對 (b)(c)(f) 全 0；依據逐條記在 `scratchpad/p916-s2-basis.json`，判定記在 `scratchpad/p916-s2-verdicts.json`，修正紀錄在全部核完後由差異比對產表。
- 驗證批次（fresh verifier，序列）：
  - D1（D #1–20）：過 58／不過 1（社宅附件漏轉租／包租範本例外）⇒ 修一次，併 4 項 verifier 建議改進，5 條整條重核。
  - D2（D #21–39＋D1 複核 5 條）：過 62／不過 4 ⇒ D1 複核 5 條全過；`contract-show-creditcard-auth-prompt`（漏特定合作團隊專屬範本不跳授權）與 `move-out-fee-adjustment-step`（誤刪自動帶入的「違約金」列）各修一次，送 E1 第二次複核（再不過即整句刪，D1）。
  - E1（E #1–19＋D 複核 2 條）：過 52／不過 0 ⇒ D 架 39 條全過。依建議修 `bill-power-reading-draft-defaults`（綁定在物件層）併入 E2 複核。
  - E2（E #20–37＋E1 複核 1 條）：過 67／不過 4 ⇒ `balance-invoice-group-action-menu`（只有手動開票才不可刪）、`newebpay-precondition`（權限名稱）、`ctbc-apply-flow`（個人房東不能開中信虛擬帳號）各修一次，另依建議微調 3 條，6 條整條複核。
  - E 複核：過 28／不過 2 ⇒ `newebpay-precondition` 權限句第二次不過（引用的提示是死碼）⇒ **依 D1 整句刪**、標題收窄；`balance-invoice-pick-and-individual-rent` 補後端來源。最終 3 項複核：過 2／不過 1 ⇒ 不過原因是原句 3（可分配租金語意與程式不符、無來源）⇒ **依 D1 整句刪**，同份報告確認句 0–2 有來源；並依建議移除失去支撐的講法 1 則。
- 收尾：219 列全數「過」或刪句（刪句 8 列、刪細目 0）；修正紀錄 `inputs/fix-log-9.16-S2-DE-20260927.md`（含差異比對最終輸出與正對照）；差異比對 (a)～(f) 全 PASS。
- 生成：scratchpad 試跑 ⇒ `已審保留：62 條／丟棄：0 條`、open_questions 54、DSP-068 24 行／28 字元（新句含「…客服。」」標籤，照規則刪句號）；A B C F G H I 與 repo 逐位元組相同。repo 重生成 ⇒ 12 檔與試跑逐位元組相同；七架與改前備份相同；`reviewed-dropped-20260927.json`＝`[]`。
- 驗收：洩漏掃描 substring 命中 6（2 句 × drafts／jgb.json／D.md），8-gram 皆為已放行的產品用語（「公會中文版 租賃契約書 包租業」「待租客簽回」）；寬掃描新增 15 皆在 S1 測試檔的日期／dict 字面（非個資）。全套單元 3931 過、紅 9＝既有名單（`test_pii_scan[runs]` 命中仍只有既有 `line_id` 各 drafts 檔）；`make audit` PASS（不變量 34：講法 1747、交集空）；終點指標 D pm 20／104、E pm 42／96（M1 不變）。**S2 完成（終點 +0，S4 前置）。**
- commit `3642733c`（S1＋S2，業主核可）。

### S3（2026-09-27，業主核可、ASK 模式）

- 分母：`scratchpad/p916-s3-targets.json`＝138（正本無 `- reviewed:` 行的 D／E 細目；reviewed 62）。批次對照 `scratchpad/p916-s3-batches.json`：S3B1 26／S3B2 29／S3B3 29／S3B4 30／S3B5 24（聯集＝targets、不交）。
- 流程：每批 fresh verifier（序列）⇒ `scratchpad/p916_s3_extract.py` 從代理紀錄檔機械取出最終訊息存 `p916-s3-raw-<批>.txt` ⇒ `p916_s3_sheet.py parse` 產 results ⇒ `sheet` 產審核單 ⇒ `check` 三段對帳。S3B2 首次交件漏 1 條（`social-housing-subsidy-terms-tab`），parse 大聲失敗 ⇒ 依計畫重來一次（同一代理補審並重貼完整 29 行）後收件。
- 結果：**pass 98／doubt 40**（S3B1 20／6、S3B2 14／15、S3B3 20／9、S3B4 24／6、S3B5 20／4）。審核單 `inputs/review-sheet-9.16-S3-DE-20260927.md`（16 組；⚠️ 5 組：D-contract-edit-social-housing、D-contract-sign-view、D-move-out、D-early-termination、D-notary）。非 ⚠️ 11 組的 pass＝75、⚠️ 組 pass＝23；pass 中 prospect 對象 13 條。
- 驗收：`check` ⇒ `targets 138; judged 138; raw-parsed 138; sheet ids 138`、`mismatches: 0`；正對照 A（raw 副本 `payment-onboarding-tax-risk` doubt→pass）⇒ `raw<->results …: raw=pass results=doubt`；正對照 B（審核單副本 doubt→pass）⇒ 報出該 id 兩筆。`git diff --stat 3642733c -- rag-orchestrator/canon .claude/skills/outline-curation/runs` 為空、工作樹無變動 ⇒ 終點指標不變。**S3 完成（+0，S4 前置）。**
- 誠實紀錄：S3 doubt 中有 S2 親修且已驗證通過的細目被抓出新問題，主要是**社宅範本名稱**——S2 依 `config/contract.php` 寫成「包租合約」「轉租合約」，畫面實際為「包租包管」「轉租」（6 條）；另有收據信「一律附收據」漏特定合作團隊、內部備註列表可直接編輯、差額發票漏每月自動開立、藍新開通勾選框未綁定、`payment-onboarding-tax-risk`「系統代為收款」無源且與資金流向不符。S2 verifier 沒抓到的原因是它只核改動項對源、S3 以整條＋跨細目一致性判。
- 成本：S3 plan-verifier ×3 約 0.15M、S3B1～B5 約 0.23＋0.29＋0.26＋0.27＋0.18；9.16 累計約 **2.84M／4M**。
### S4（2026-09-27，業主裁決「安全組過、⚠️組不審」）

- 就緒審查（fresh plan-verifier）＝READY。
- 核可清單 `scratchpad/p916-s4-approved.json`：從審核單（非 ⚠️ 組 `[pass]`）與 results（非 ⚠️ 組 pass）各算一次，兩者相同＝75 條。改前備份 `scratchpad/p916-s4-backup/`（與 HEAD 逐位元組相同）。
- 寫入：D.md／E.md 在核可細目 `- sources:` 之後各加 `- reviewed: {by: owner, at: 2026-09-27}`（D 31、E 44，刪除 0）；`export_json`／`export_catalog` 重匯出 ⇒ `jgb.json` 只變 75×`reviewed_by`／`reviewed_at`＋`canon_sha256`；`CATALOG.md` 與 A B C F G H I 位元組不變；`load_canon_or_die` 通過（reviewed 137）。
- 驗收：已審 id 集合＝既有 62 ∪ 核可 75（交集空）；doubt 與 ⚠️ 組 0 條被標；全套單元紅燈＝既有 9 條；`make audit` PASS（主 session 於同一位元組執行）；重生成保留檢查（scratch）`已審保留：137 條／丟棄：0 條`、輸出與 repo 正本逐位元組相同。fresh outcome verifier＝**CONFIRMED**（`make audit` 依 brief 不重跑、採主 session 證據）。
- **終點指標：`已審細目 pm 137／535、prospect 18／121；頁面 pm 48／183、prospect 13／183`**（pm +75、prospect +8；prospect +8＝核可中 target_user 含 prospect 的條數）。HANDOFF 開頭已更新。
- 成本：S4 plan-verifier 約 0.06M、outcome verifier 約 0.09M；**9.16 累計約 2.99M／4M**（未達 3.2M 停點）。
- commit：S3＋S4 `496369d2`。
- **9.16 收案**：D／E 200 條中已審 137（pm 對象全數 137；prospect 18／30）；未審 63 條＝⚠️ 5 組 23 條 pass＋40 條 doubt，另案處理（建議 Plan 9.17：先修 40 條 doubt——含 S2 自己寫錯的社宅範本名稱 6 條——再對 ⚠️ 組重審）。

### 收案後抽驗（2026-09-27，業主要求）

- 從 S4 核可 75 條分層固定種子抽 10（`scratchpad/p916-spot-sample.json`，seed 20260927）：S2 親修層（母體 46）抽 5、原稿層（母體 29）抽 5；fresh verifier 整條重核。
- 結果：**pass 9／fail 1**；親修層 5／5 過；原稿層 1 條 P2——`jgb/E/payment-gateway-fees` 標題寫「中國信託／藍新免費」，來源只證申請免費、無交易費率，且藍新提款前 5 次免費後每次 10 元。無 P1。
- 連帶發現待裁：`jgb/E/bill-power-reading-draft-defaults`（排定發送時空白度數系統自動補抓，依帳本 #p914-power-reading-draft 與 app/Bill.php `prepareIotMeterForSend`）與已審的 `jgb/E/bill-scheduled-send-rule`（「只有度數填完的帳單才能排定」）看似矛盾，未對碼、不自行選邊，列 9.17。
- 成本約 0.14M；9.16 含抽驗累計約 3.13M。
- **業主裁決「撤」（2026-09-27）**：刪除 `payment-gateway-fees` 的 `- reviewed:` 行（E.md 刪 1 行）、重匯出（`jgb.json` 只變該條 reviewed 欄位＋sha，CATALOG 不變）；`load_canon_or_die` 通過；終點指標 `已審細目 pm 136／535、prospect 17／121`；全套單元紅燈＝既有 9 條；`make audit` PASS。該條列 9.17 修正後重審（備份 `scratchpad/p916-unreview-backup/`）。commit `5d188b37`。

> ⚠️ 2026-09-29 補記：以下三行是 **S2 期間**的紀錄，誤置在檔尾；其中「累計約 1.45M」是 S2 當時的值（括號內各項加總為 1.42M），⛔ 當作 9.16 最終成本（最終約 3.13M，見上）。

- 另記（verifier 附帶、未改）：`newebpay-precondition` 句 0「系統不再檢查帳號綁定手機」只適用現行 `getPaymentVendor`，舊 `addMerchant` 仍檢查（舊路徑、現行頁面不呼叫）；藍新開通勾選框未綁 enabled，實際開通以後端預設為準。兩者留 S3 先審再看。
- 過程中發現、另案處理的 jgb2／文件不一致：委託合約檢視頁上傳區畫面寫 6MB、元件實際上限 10MB；幫助中心 `paymentapply` 寫個人房東可選藍新，程式對個人房東停用藍新／國泰／永豐；`bills.one` 舊路由仍在但通知連結已改走列表 `?id=`。
- 累計成本約 1.45M／4M（S1 verifier 0.1、plan-verifier ×3 0.16、B7 0.21、D1 0.17、D2 0.19、E1 0.19、E2 0.2、E 複核 0.12、最終 3 項 0.08）。
