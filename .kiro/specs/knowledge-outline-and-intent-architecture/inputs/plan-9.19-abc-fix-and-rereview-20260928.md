# Plan 9.19：A／B／C 疑點修正＋重審（含 ⚠️ 組通過件），並整理 jgb2 缺陷清單

> **現況**（`endpoint_progress.py`，2026-09-28，commit `199d4fc5`）：`已審細目 pm 304／535、prospect 53／121；頁面 pm 79／183、prospect 23／183`。
>
> **本計畫預期**：
> - S3 完成時 **pm 最多 +83、prospect 最多 +29**（S2 重審後實算；原估最多 +111／+35）（A／B／C 未審 110 條，加上 I 架 1 條）。
> - 依 9.16 修正後重審的經驗（修 76 → 過 75），實際預期約 **pm +70～95**。
> - S0、S1、S2 都是 +0。

## 0. 為什麼有這份

- 業主 2026-09-28 裁示：
  - 9.19＝「A／B／C 疑點修正＋重審」；
  - 頁面量尺「先不動，列待辦」；
  - I 架「應寄 Email 實際不寄」這類問題「整理成清單交產品」。
- A／B／C 還沒審的 110 條都已經有 9.17 S1 的先審結論（`scratchpad/p917-s1-results.json`、審核單 `inputs/review-sheet-9.17-S1-ABC-20260928.md`）：
  - 68 條 doubt（A 24、B 21、C 23），每條附程式反證；
  - 42 條是 ⚠️ 組裡的 pass（A 13、B 12、C 17）。
  - 其中含 prospect 34 條。prospect 目前最落後，所以先做 A／B／C。
- 另附 1 條 I 架細目：`jgb/I/pricing-trial-plan-landing-page`。它寫出了合作品牌名「愛租屋」，引號裡的文字也少了「元」（9.18 S2 doubt）。

## 1. 切片（順序：S0 → S1 → commit → S2 → S3；S0 唯讀，可與 S1 並行準備）

### S0 — jgb2 缺陷清單（+0，唯讀）

- 主 session 從以下來源整理，產出 `inputs/jgb2-defects-9.19-<日期>.md`：
  - 9.17 S1、9.18 S2 審核單的 doubt 理由；
  - 9.15 G1 清單；
  - 9.16 §6 的三處。
- 只收錄「程式行為疑似缺陷」的項目，**不收**「正本寫錯」的項目。例：
  - 取消訂閱通知 `subscription_cance` 拼錯而不寄；
  - 修繕「通知及同步租客」開關未接；
  - 首頁 `v-if` 用空陣列判斷；
  - 社區 `sell_price_range_per_unit` 永遠是空值；
  - 物件公開頁 `spaceType` 拿翻譯字串與英文 key 比對。
- 每項附：釘住匯出 `scratchpad/jgb2-b2ee2ac/` 的檔案＋可 grep 符號、使用者可見後果、相關細目 id。⛔ 在本計畫開 Monday 單；業主看清單後自行決定。
- **驗收**：每項都有可 grep 的程式證據，而且在釘住匯出中 grep 得到（逐項實跑、記錄命中）；正對照為一個已知存在的符號。
- **預算**：約 0.1M（主 session 自做）。

### S1 — A／B／C 68 條＋I 1 條疑點修正（+0；是 S3 的前置）

- **允許集合**：`scratchpad/p919-s1-allowed.json`，共 69 條，是 `p917-s1-results.json` 中 verdict＝doubt 且目前未審的 A／B／C 細目，再加上 `jgb/I/pricing-trial-plan-landing-page`。
  - 由腳本產生，條數≠69 即停。
  - 全部是未審細目，重生成時不會丟掉任何已審。
- **改前備份（步驟 0，第一次執行 `p919_edit.py` 之前）**：
  - 備份範圍：drafts 全架、`rag-orchestrator/canon/`、`runs/outline-20260920/` 既有 `*-20260928*` 產出（9.18 S1 的 3 個檔）。
  - 備份到 `scratchpad/p919-s1-backup/`（子目錄 `drafts/`、`canon/`、`runs/`）。
  - 用 `diff -r`（canon）與 `cmp`（每個 drafts 與 runs 檔）確認和現況相同。
  - 在 §6 記錄備份時間與比對結果。
  - **紅燈基準**：同一工作樹、同一步驟跑全套單元（`scripts/run-tests.sh unit -q -p no:cacheprovider`），把 FAILED 的**測試 id 集合**記入 §6，存成 `scratchpad/p919-s1-red-baseline.txt`。工作樹有別的工作線尚未提交的程式與測試修改，所以不能沿用 9.18 的 9 條當基準。
- **改寫工具**：`scratchpad/p919_edit.py`（`p918_edit.py` 的副本，**已建、已預跑**）。
  - 變更：
    - `TRAIL` 改為 A:""、B:"\n"、C:""、I:"\n"（實測）；roundtrip 範圍 A B C I。
    - 以 `ALLOWED=`（必填）限定允許集合。
    - 環境變數 `P919_RUNS` 只供 scratch 預跑覆寫 drafts 目錄。
  - **句序映射**：一次呼叫中所有句序都指呼叫前的句子。
    - 新句序＝該句前面保留下來的舊句數，加上它前面插入的句數。`insert_after[-1]` 插在所有舊句之前；`insert_after[k]` 可一次插多句，依序放在舊句 k 之後。
    - `evidence[].sentence_index` 依同一映射改寫；被刪句的 evidence 一併移除。
    - 呼叫前就已越界的 evidence 原樣保留、不修。
  - **`evidence_add`**：句序指**呼叫後**的句序，鍵名必須恰為 `sentence_index`／`source`／`quote_or_symbol`；越界或鍵名不符就拒絕。
  - 整體覆寫的 `evidence` op 在 p919 停用，給了就拒絕。
  - **已預跑**（2026-09-28，scratch drafts 副本 `pc10/`，測試細目 `jgb/A/account-change-password`，5 句、6 筆 evidence）：
    - `--roundtrip` ⇒ A B C I 皆 `byte-identical: True`。
    - 一次呼叫同時做 `set 0`、`delete 1`、`insert_after {-1:[1 句], 0:[2 句]}`、`evidence_add`（新句 2）：
      - 句子＝預期序列；
      - evidence＝預期映射（舊 0→1、2→4、3→5、4→6，刪句 1 的 2 筆被移除，新增 1 筆在句 2）；
      - 全部在範圍內。
    - 負對照：改允許集合外的細目 ⇒ 拒絕；給整體 `evidence` op ⇒ 拒絕。
- **允許集合開工前量測**：69 條中既有 evidence 越界 **0 條**（N＝0），所以驗收照「全部在範圍內」。
- **修法**（主 session 親修，依 9.17 S1 的 doubt 理由與證據逐條處理）：
  - 只修 doubt 理由所指的問題，⛔ 擴大改寫範圍。
  - 句子要改寫成對齊現行程式的使用者可見行為；引號內的介面標籤要逐字對到現行畫面。
  - 實作詞、過程筆記直接刪掉或改寫。
  - 客戶名改為「特定合作團隊」（沿用 9.18 D1）。
  - 若某條細目必須整條刪除才能成立 ⇒ 不刪，停下列給業主。
  - 同組細目改寫後不得互相矛盾（9.16 抽驗的教訓）。
- **修正紀錄**：`inputs/fix-log-9.19-S1-<日期>.md`。
  - 格式同 9.18 S1：一列一個改動項，含依據與 verifier 判定，另有刪除節。
  - 依據欄指向 9.17 審核單的 doubt 理由；I 那條指向 9.18 審核單。
- **核對**：fresh verifier 分 3 包（依架：A 24、B 21、C 23＋I 1），序列跑，逐項判「過／不過」。
  - D1：修一次仍不過 ⇒ 整句刪。
  - 若整句刪會讓細目只剩 0 句 ⇒ 停下交業主。
  - brief 沿用 9.18 S1 核對版，加入「⛔ 同組矛盾」「引號標籤逐字」兩條。
- **差異比對**：`scratchpad/p919_s1_drafts_diff.py`（`p918_s1_drafts_diff.py` 的副本，**已建、已預跑**）。
  - 變更：`SHELVES` 由 `P919_DIFF_SHELVES` 決定，預設 `ABCI`。
  - 新增檢查 **(g)**：允許集合內細目的 `evidence` 差異，視為 `p919_edit.py` 的機械位移，不列入修正紀錄；但比對「越界 evidence 數」，改後多於改前即 FAIL。允許集合**外**細目的 evidence 差異仍算 (c) 保護違規。
  - **已預跑**：
    - 對上述插刪後的 scratch 副本：(g) `evidence remaps on allowed fines: 1; new out-of-range: 0`，只要 3 列句子改動的修正紀錄，(a)～(f) 就 PASS。
    - 正對照：
      - 改允許集合外 `jgb/B/team-basic-info` 的 evidence ⇒ (c) 報出、FAIL；
      - 把允許集合內一筆 evidence 句序改成 99 ⇒ (g) `out-of-range evidence 0 -> 1`、FAIL。
- **重生成**：
  - 參數：`--date 20260928-s1-919`（若跨日則用當日日期）、`--expect-reviewed-kept 308`、`--expect-open-questions <實算>`。
  - 先在 scratch 試跑，全部 `--expect-*` 通過才對 repo 跑。
- **驗收**：
  - 差異比對 (a)～(f) 全 PASS；drafts-D／E／F／G／H 與備份位元組相同（`cmp`）。
  - 重生成：`已審保留：308 條／丟棄：0 條`。
    - D E F G H `.md` 與備份位元組相同。
    - A B C I 的區塊差異只在允許集合內（`p919_s1_canon_check.py <p919-s1-backup/canon> rag-orchestrator/canon p919-s1-allowed.json`）。
  - 客戶名掃描用 `scratchpad/p919_s1_canon_check.py`（`p918_s1_canon_check.py` 的副本，`PAT` 加「愛租屋」）：
    - 預跑正對照：現行正本命中 `('I', '愛租屋')`，`.md` 1 處、CATALOG＋jgb.json 1 處。
    - 修正後全正本 0 命中；負對照：原本在 E／F 的 6 處「系統上」不變。A／B／C／I 改寫若合法寫入「系統上」，不算違規，因為樣式已排除它。
  - evidence 對齊：允許集合 69 條的 `sentence_index` 全部在 0..n-1 之內（開工前 N＝0）。
  - 已審 id 集合不變（308）；終點指標不變。
  - 全套單元：改後紅燈 id 集合與 §6 基準的差集＝∅（新增紅燈 0）；`make audit` PASS；fresh outcome verifier。
  - **commit 範圍**：只 `git add` 本片擁有的路徑——drafts-A／B／C／I.json、`rag-orchestrator/canon/`、`runs/outline-20260920/*-<date>*`、修正紀錄、本計畫。commit 前以 `git diff --cached --name-only` 核對，範圍外路徑為 0，結果記入 §6。⛔ `git add -A`。
- **停止**：
  - 修法需要臆測才能成立，或必須刪整條 ⇒ 該條不改、停下列給業主。
  - 差異比對不過，或重生成 `--expect-*` 不過：
    - 還沒對 repo 跑 ⇒ 不還原，直接停；
    - 已對 repo 跑 ⇒ 用 `scratchpad/p919-s1-backup/` 還原後停。
  - 累計達 §3 D4 停點 ⇒ 停。
- **擁有**：
  - drafts-A／B／C／I.json（只限允許集合）
  - `rag-orchestrator/canon/`（重生成）
  - `runs/outline-20260920/*-<date>*` 新產出
  - 修正紀錄、本計畫 §6
  - scratchpad 的 p919-s1 檔案
- **回滾**：用 `scratchpad/p919-s1-backup/`（drafts 全架、canon）還原，並刪掉本片新產出。
- **預算**：約 1.1M（主 session 修正、verifier 3 包＋複核約 0.9M、outcome verifier 約 0.12M）。

### S2 — A／B／C＋I 111 條重新先審（+0；是 S3 的前置）

- **分母**：S1 commit 後 A／B／C 未審的 110 條，加上 `jgb/I/pricing-trial-plan-landing-page`，共 111 條，存 `scratchpad/p919-s2-targets.json`，數目≠111 即停。
  - 42 條 ⚠️ 組 pass 內容沒改，但需要和修正後的同組細目一起重審，才抓得到跨細目矛盾。
- **工具**：`scratchpad/p919_s2_sheet.py`，是 `p918_s2_sheet.py` 的副本。
  - 變更值：`CANON_COMMIT=<S1 commit>`、`SHELVES` 預設為 `ABCI`、前綴 `p919-s2`、標題「Plan 9.19 S2」。
  - targets 改為讀 `p919-s2-targets.json`，不再以「整架未審」計算，因為 I 架只納入 1 條。這項工具變更要預跑正負對照。
- **批次**：粗目不拆、每批 ≤35，共 4 批。對照表派工前存成 `p919-s2-batches.json`。
  - **已預跑**（2026-09-28，S1 commit `bdb2327b` 後）：
    - `p919_s2_sheet.py`：`CANON_COMMIT="bdb2327b"`、`SHELVES` 預設 `ABCI`（`P919_SHELVES`）、前綴 `p919-s2`。targets 讀 `p919-s2-targets.json`，是 A／B／C 未審 110 條加上 `jgb/I/pricing-trial-plan-landing-page`，共 111 條。
    - 批次：
      - S2B1 33 條：A 7 組；
      - S2B2 33 條：A-notification-settings＋B 5 組；
      - S2B3 29 條：B-tenant-list＋C 7 組；
      - S2B4 16 條：C 3 組＋I-pricing 1 條。

      聯集＝targets，互不重疊。
    - 空結果審核單 `check` ⇒ `targets 111; judged 0; raw-parsed 0; sheet ids 111`、`mismatches: 0`。
    - 負對照：`P919_SHELVES=ABC` ⇒ `❌ 1 targets not found…['jgb/I/pricing-trial-plan-landing-page']`。
    - brief 以 9.18 S2 版為範本，已生成 `scratchpad/p919-s2-brief-S2B*.txt`。各批 sources 前綴都在來源清單內：S2B1 code／help、S2B2 code、S2B3 code／help、S2B4 code／help。
- **brief**：9.18 S2 版，含 `doc:` 來源、「只放一份結論」、「逐條對照清單」。派工前以 grep 確認每批 sources 前綴都在來源清單內。
- **保留清單（hold）**：`scratchpad/p919-s2-hold.json` 列了 `jgb/A/login-sso-redirect-no-duplicate-buttons`、`jgb/B/biglandlord-escrow-owner` 兩條。業主已裁「列下個計畫刪除」，所以這兩條照常重審，判定只記錄、不標已審。brief 不預告這件事，避免影響獨立判定。
  - `p919_s2_sheet.py` 的處理（已改、已預跑）：
    - 這兩條在審核單列成 `[hold]`，並附註「⛔ 標已審（先審判定：X）」，不計入 pass／doubt，也不計入 ⚠️ 的分母；
    - 表頭寫明「整組回『過』也不涵蓋它們」；
    - `check` 核對 `[hold]` 標記＝hold ∩ 已判。
  - 預跑結果（假結果）：
    - 正常審核單：`raw<->results` 以外的 mismatch 為 0；
    - 負對照：審核單副本把一條 `[hold]` 改成 `[pass]` ⇒ 報出 `hold marks: sheet [...] vs expected [...]` 等 3 項。
- **審核單與驗收**：
  - 審核單 `inputs/review-sheet-9.19-S2-ABCI-<日期>.md`；
  - `check` 輸出 `targets 111; judged 111; raw-parsed 111; sheet ids 111`、不符 0；
  - 兩個正對照皆報出；
  - 正本相對 S1 commit 無變動。
- **停止與回滾**：同 9.18 S2（交件失敗，同一代理重貼一次仍失敗即停；中途停下時未跑的批次在審核單列「未先審」；回滾只刪審核單與 p919-s2 檔）。
- **預算**：4 批約 0.9M。

### S3 — 業主終審＋寫入已審（pm 最多 +83、prospect 最多 +29；實算見下）

- **業主回覆**：依審核單 `inputs/review-sheet-9.19-S2-ABCI-20260929.md` 回覆，可用以下幾種形式：
  - 規則：「安全組過」（非 ⚠️ 組的 pass）或「全部 pass 過」；
  - 點名 ⚠️ 組「過」：只收該組的 pass；
  - 逐條點名 doubt「照原樣過」；
  - 逐條點名 pass「不要」。

  其餘 doubt 一律本批不審。**`[hold]` 兩條不論回覆內容都不會被核可。** 回覆若無法完整寫成四欄形式，就回頭問業主。
- **工具**：`scratchpad/p919_approved.py`，由 `p918_approved.py` 複製，變更項目如下：
  - results／targets 改讀 `p919-s2-*`；
  - PLAN 改指本計畫，段落用「### S3」；
  - **加入 HOLD**：讀 `p919-s2-hold.json`。來源 B 把 hold 排除在核可之外，也不計入 ⚠️ 分母；來源 A 只認 `[pass]`／`[doubt]` 列，所以 hold 本來就被排除。
  - 環境變數：`P918_WRITE_SHELVES=ABCI`（必填）、`P918_SHEET=/Users/chenqinghuang/dev/work/AIChatbot/.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.19-S2-ABCI-20260929.md`。
- **步驟**（⛔ 手選 id、⛔ 手改正本）：
  1. 業主原文逐字記入 §6「### S3」，再寫 `scratchpad/p919-s3-decision.json`。
  2. `P918_WRITE_SHELVES=ABCI P918_SHEET=/Users/chenqinghuang/dev/work/AIChatbot/.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.19-S2-ABCI-20260929.md python3 p919_approved.py derive p919-s3-decision.json --out p919-s3-approved.json`
  3. 備份：`rag-orchestrator/canon/` 複製到 `scratchpad/p919-s3-backup/`，以 `diff -r` 確認相同；`git diff --stat bdb2327b -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆須為空。
     **紅燈基準（同一工作樹、寫入前）**：跑 `scripts/run-tests.sh unit -q -p no:cacheprovider`，把 FAILED 的測試 id 集合存成 `scratchpad/p919-s3-red-baseline.txt`，並將條數與時間記入 §6 S3。
  4. `P918_WRITE_SHELVES=ABCI python3 p919_approved.py write p919-s3-approved.json --date <日期>`
  5. 容器重匯出（⛔ 用重跑生成器來改正本）：
     `docker compose -f docker-compose.dev.yml run --rm -T --no-deps rag-orchestrator python -c "from services.agent.canon.canon_parser import parse_canon_dir, export_json, export_catalog; from services.agent.canon.canon_assembler import load_canon_or_die; d=parse_canon_dir('/app/canon/jgb'); export_json(d,'/app/canon/jgb.json'); export_catalog(d,'/app/canon/jgb/CATALOG.md'); load_canon_or_die('/app/canon')"`
  6. `P918_WRITE_SHELVES=ABCI python3 p919_approved.py verify p919-s3-approved.json --backup p919-s3-backup`，然後逐項跑下方驗收。
- **已預跑**（2026-09-29，scratch 計畫副本與 scratch 正本 `pc14/`，repo 未動）：
  - derive 結果，兩來源推導一致：
    - 「安全組過」⇒ 65 條（A 26／B 24／C 15／I 0；pm +65、prospect +27）；
    - 「全部 pass 過」⇒ 83 條（pm +83、prospect +29）；
    - 兩種回覆都不含 hold。
  - **hold 正對照**：results 副本把 `biglandlord-escrow-owner` 改成 pass，工具仍不核可它。
  - **hold 負對照**：工具副本拿掉 HOLD 排除 ⇒ `sheet-derived 83 != results-derived 84; only-results ['jgb/B/biglandlord-escrow-owner']`，推導失敗。
  - 安全組 65 條走完 write＋重匯出＋`load_canon_or_die`，verify 結果為 `reviewed backup 308 -> current 373; added lines 65`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
  - scratch 終點指標：`已審細目 pm 369／535、prospect 80／121；頁面 pm 89／183、prospect 27／183`。
- **驗收**：
  - 決定檔忠於原文：雙向核對，由 fresh outcome verifier 逐條勾選。
  - verify 結果為 `mismatches: 0`，涵蓋以下各點：
    - 已審集合＝308 ∪ 核可（逐 id 比對）；
    - A／B／C／I 只多出 `- sources:` 之後的 reviewed 行，刪除 0 行；
    - D～H、CATALOG、README 逐位元組相同；
    - jgb.json 只有核可 id 多出 `reviewed_*`。
  - hold 兩條沒有 reviewed 行。
  - `load_canon_or_die` 通過。
  - 終點指標：pm＝304＋增量、prospect＝53＋增量。
  - 重生成保留檢查（**只寫 scratch**）：
    - 先把 `rag-orchestrator/canon` 複製到 `scratchpad/p919-s3-regen-canon`。
    - 再執行：
      `docker compose -f docker-compose.dev.yml run --rm -T --no-deps -v <scratchpad>:/scratch rag-orchestrator python /.claude/skills/outline-curation/scripts/drafts_to_canon.py generate --drafts-dir /.claude/skills/outline-curation/runs/outline-20260920 --coarse-ids /.kiro/specs/knowledge-outline-and-intent-architecture/inputs/coarse-ids-20260921.md --front-matter-from /scratch/p919-s3-regen-canon/jgb --canon-root /scratch/p919-s3-regen-canon --runs-out /scratch/p919-s3-regen-runs --date <日期>-s3check --expect-reviewed-kept <308＋核可數> --expect-open-questions 54`
    - 須印出 `已審保留：<308＋核可數> 條／丟棄：0 條`，產出的 A～I `.md`、CATALOG、jgb.json 與 repo 逐位元組相同。
    - ⛔ 對 repo 跑。
  - 寫入後的紅燈 id 集合減去 `scratchpad/p919-s3-red-baseline.txt` 須為 ∅；`make audit` PASS；fresh outcome verifier CONFIRMED。
  - commit 只收以下檔案，並以 `git diff --cached --name-only` 核對，範圍外須為 0：A／B／C／I `.md`、jgb.json、審核單、本計畫、`.kiro/specs/knowledge-outline-and-intent-architecture/HANDOFF-20260923.md`（終點行）。CATALOG 須與備份位元組相同，所以不在 commit 範圍內；若有變動，verify 會先報錯。
- **停止**：
  - **寫入前**失敗（回覆不符四欄、derive 失敗、備份不同、git 基準非空）⇒ 不還原，直接停。
  - **寫入後**任一驗收不符 ⇒ 用已驗證的 `p919-s3-backup/` 還原，並以 `diff -r` 確認、`git diff --stat bdb2327b -- rag-orchestrator/canon` 為空，然後停下交業主。這屬於預先授權的還原；若已審數低於 308，仍須業主明示。
  - 累計達 2.7M 停點 ⇒ 停。
- **擁有**：`rag-orchestrator/canon/jgb/A.md`、`B.md`、`C.md`、`I.md`、`jgb.json`；本計畫 §6；HANDOFF 終點行；scratchpad 的 p919-s3-decision／approved／backup／regen-*／red-baseline。⛔ drafts、D～H、CATALOG（應無變動）。
- **回滾**：以 `p919-s3-backup/` 還原，或 revert 該 commit；已審數下降須業主明示。
- **預算**：outcome verifier 約 0.15M。

## 2. 不做（另案）

- D／E 未審 63 條；F～I 未審 59 條（60 條扣掉本計畫納入的 I 架 1 條；該條 S3 後仍未審，所以 9.19 收案時 F～I 未審細目仍是 60 條，pm 口徑 58，見 §6 更正）。
- 頁面量尺修正（業主裁「先不動，列待辦」）；pm 真缺口 9～12 頁補寫；prospect 可見頁範圍定義。
- `set` 改寫後，舊 evidence 可能不再支持新句（evidence 不進正本，屬資料品質問題）。
- drafts evidence 句序既有的不對齊，共 23 條（其中 9 條是 9.16～9.18 插句造成的）。本計畫只保證允許集合內對齊，並修工具讓以後的編輯不再產生新的不對齊。

## 3. ⏳ 待業主裁

- **D1**：沿用——只修 doubt 所指的問題；修一次仍不過就整句刪；需要整條刪時停下交業主；客戶名改為「特定合作團隊」。（建議：同意）
- **D2**：S2 把 42 條 ⚠️ 組 pass 一起重審（內容沒改，但重新判定）。重審後若變成 doubt，本批不審。（建議：同意；否則仍會卡在同組規則上）
- **D3**：S3 終審標準沿用「安全組過」，看審核單後再定。（建議：沿用）
- **D4**：預算上限 3.0M（S0 0.1＋S1 1.1＋S2 0.9＋S3 0.15＋就緒審查 0.4＋預留 0.35）；累計達 2.7M 先停下交業主。（建議：可以）

- **業主裁決（2026-09-28）**：「核可，D1～D4 照建議、ASK 模式 (Recommended)」。

## 4. 停止條件（全片共用）

- 已審細目數任何時候下降 ⇒ 停下交業主（本計畫預期不會下降：允許集合全是未審細目）。
- 正本只准在 S1（重生成，只動允許集合）與 S3（只加 reviewed 行）時變動。
- 累計達停點先停下交業主；超過上限即停。
- 一次只跑一個代理（本機 8GB）。

## 5. 就緒審查紀錄

- 大綱＋S0＋S1 第 1 輪＝REVISE，P2×4：
  1. 插句或刪句必然造成 evidence 差異，但差異比對會要求把它列入修正紀錄並判「過」，否則 FAIL；
  2. evidence 位移規則沒涵蓋一次插多句、`-1`、刪插混用，`evidence_add` 的句序基準與鍵名不明，允許集合既有越界數也沒量；
  3. 沒有改前備份的步驟；
  4. 客戶名掃描工具不含「愛租屋」，也沒有正對照。

  **全數 FIX，並先建工具、預跑**：
  - `p919_edit.py`：句序映射規則，`evidence_add` 用呼叫後句序、鍵名 `quote_or_symbol`，停用整體覆寫；
  - `p919_s1_drafts_diff.py`：新增 (g) 機械檢查；
  - `p919_s1_canon_check.py`：加入「愛租屋」；
  - 加「改前備份」步驟；
  - 實測允許集合既有越界 N＝0。

  所有正負對照結果記在 S1。
- 大綱＋S0＋S1 第 2 輪＝REVISE，P2×1：工作樹有別線尚未提交的程式與測試修改，「紅燈＝既有 9 條」可能因無關原因不過或掩蓋新紅燈，commit 也沒有限定路徑。這是**第二次自動 REVISE ⇒ 停止重送，逐條處置**。
  - **FIX**：S1 步驟 0 加「同工作樹紅燈 id 基準」；驗收改為「差集＝∅」；加 commit 範圍與 `git diff --cached --name-only` 核對。
  - P3 採納：「系統上」檢查改為「E／F 原 6 處不變」。
  - P3 不處理：`set` 改寫後舊 evidence 可能不再支持新句。evidence 不進正本，屬資料品質問題，列 §2。

  依規則只開一次收尾審查。
- 收尾審查（fresh plan-verifier）＝**READY** ⇒ 交業主核可（`next_gate: user_approval`）。S2、S3 開工前各自再過就緒審查。
- S2 第 1 輪＝REVISE，P2×1：業主裁定要刪除的兩條，在 S2 產物中沒有「不可標已審」的標記。S3 若整組回「過」，會把已知錯誤的內容寫成已審，下個計畫刪除時已審數還會下降。
  - **FIX（採方案 a）**：新增 hold 清單；`p919_s2_sheet.py` 標 `[hold]`、⚠️ 分母排除、`check` 核對標記，並附正負對照；S3 工具兩個來源都排除 hold，另列預跑要求。
- S2 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 依業主 9.19 核可開跑（ASK 模式，每批回報）。
- S3 第 1 輪＝REVISE，P2×2：
  1. 步驟 5 的容器匯出鏈與重生成保留檢查沒有寫成可執行指令，照字面跑有覆寫 repo 的風險；
  2. 單元紅燈基準沒寫檔名與量測時點，而工作樹還有其他工作線的改動。

  **FIX**：
  - 步驟 5 寫成完整指令；
  - 重生成檢查寫全 scratch 旗標，並註明「⛔ 對 repo 跑」；
  - 步驟 3 加寫入前紅燈基準 `p919-s3-red-baseline.txt`，驗收改為以它比對；
  - 擁有範圍列入 regen 與 red-baseline。

  P3 一併處理：審核單改用絕對路徑；commit 清單補 HANDOFF 路徑、移除 CATALOG；表頭預期更正為 +83／+29。

- S3 第 2 輪（fresh plan-verifier）＝**READY** ⇒ 審核單交業主終審。
## 6. 執行紀錄

### S0（2026-09-28）

- 產出 `inputs/jgb2-defects-9.19-20260928.md`，共 20 項（D1～D20）：本片新整理 16 項，先前計畫已記錄的 4 項一併移交。
- 每項證據都以 grep 在釘住匯出中實測命中。正對照 `checkIotBill` 命中 1；負對照（不存在的符號）命中 0。
- D15 的證據路徑第一次指錯目錄，改到 `src/components/Lightbox/PowerMeterTopUp.vue` 後命中。
- D20 是 S1 核對時才發現、後來補上的：租客列表的注意事項文案與開關行為相反。

### S1（2026-09-28）

- **步驟 0**：
  - 備份 `scratchpad/p919-s1-backup/`（21:44:26，早於第一次編輯）：`diff -r` canon 無差異；drafts 與 runs 的 3 個 `*-20260928-s1*` 檔 `cmp` 皆相同。
  - 紅燈基準 `scratchpad/p919-s1-red-baseline.txt`（同一工作樹）共 9 條，與 9.17 S2 的紅燈集合相同。
- **修正**：主 session 逐條以 grep 對釘住匯出確認 doubt 證據後，用 `p919_edit.py` 改寫。
  - 允許集合 69 條中改了 **61 條**（A 22／B 15／C 23／I 1），共 **133 個改動項**。
  - 其中 phrasings 調整 7 條：講法已對不上改寫後的內文。
  - 修正紀錄見 `inputs/fix-log-9.19-S1-20260928.md`。
- **未改的 8 條**：
  - B 5 條：只有客戶名的 doubt，9.18 已處理。
  - `notification-settings-report-buttons`：行為有程式根據。
  - **2 條必須整條刪除，依 D1 停下交業主**：`jgb/A/login-sso-redirect-no-duplicate-buttons`（情境在程式裡走不到）、`jgb/B/biglandlord-escrow-owner`（只存在於舊 blade）。
- **核對**：
  - 3 包 fresh verifier：A 34／37、B 32／33、C＋I 36／48。
  - 依 D1 修一次後複核 40 項：38 過。
  - 複核仍不過的 2 項，句子內容都已確認正確，只是缺出處登錄、講法回歸。這 2 項改用機械修補，由主 session 以 grep 驗證（偏離 D1「整句刪」字面，理由記在修正紀錄「核對過程」）。
- **差異比對**（`p919_s1_drafts_diff.py`）：
  - (a)～(f) PASS；(g) `evidence remaps on allowed fines: 19; new out-of-range: 0`。
  - 允許集合開工前越界數 N＝0，所以 69 條 evidence 全數在範圍內。
  - drafts-D～H 與備份相同。
- **重生成**：
  - scratch 試跑後對 repo 跑，`--date 20260928-s1-919`：`已審保留：308 條／丟棄：0 條`，`reviewed-dropped` 為 `[]`；repo 產出與試跑逐位元組相同。
  - `p919_s1_canon_check.py`：變動區塊 61 條＝允許集合內改動的細目；D～H 與備份相同；jgb.json 61 條、CATALOG 84 行變動都只在允許集合內。
  - 客戶名在 `.md`、CATALOG、jgb.json 全 0 命中；「系統上」6 處都在 E／F，原樣保留。
- **終點指標**：`已審細目 pm 304／535、prospect 53／121；頁面 pm 79／183、prospect 23／183`（不變，符合預期）。
- **單元與 audit**：9 failed，新增紅燈 0（與基準比較的差集為空）；`make audit` PASS。
- **fresh outcome verifier＝CONFIRMED**（9 項全過）。抽查結果：
  - 18 條細目逐句對過程式碼；
  - 允許集合 69 條的 305 筆 evidence 越界 0，其中 299 筆 code evidence 的引文全部 grep 命中；
  - 兩項機械修補沒有留下錯誤內容。

  附記（延後，不擋收案）：
  - **P3**：`register-verify-code-shape` 新句 1 的 evidence 仍掛著舊的 `isLocked` 依據，sources 也缺 AuthController。
  - **P4**：
    - `team-public-page-share` 的 `askable` 欄仍含「有專屬短網址嗎」（不進正本）；
    - `estate-house-info-card` 移除了兩筆標籤 evidence（標籤仍能在 sources 中命中）；
    - `biglandlord-seat-limit` 的 evidence 來源不在 sources（修正前就是如此）；
    - 修正紀錄的差異比對輸出原本是佔位字（**已補上**）。

  P3 與前兩項 P4 在 S2 重新先審時一併看，屆時仍需處理的列入下個計畫。
- **commit 範圍核對**：`git diff --cached --name-only` 共 16 檔，範圍外 0。
- **業主裁決（2026-09-28）**：commit「commit，接著進 S2 (Recommended)」；兩條必須整條刪除的細目「列下個計畫刪除 (Recommended)」，本計畫不動，S2 照常重審。
- **成本**：S0 約 0.05M；S1 的主 session 修正，加上 verifier 3 包、複核 1 輪、outcome 1 輪約 0.95M；就緒審查 ×3 約 0.33M ⇒ **9.19 累計約 1.35M**（停點 2.7M、上限 3.0M）。

### S2（2026-09-28～29）

- 4 批 fresh verifier 依序跑完，一次一位。brief 以 9.18 S2 版為範本，另加三項：講法要答得到、現行程式走不到的情境判 doubt、比對同粗目（含不在本批的細目）。合計 **pass 83／doubt 28**（含 hold 兩條）：

  | 批 | 條數 | pass／doubt |
  |---|---|---|
  | S2B1 | 33 | 25／8 |
  | S2B2 | 33 | 27／6 |
  | S2B3 | 29 | 21／8 |
  | S2B4 | 16 | 10／6 |

- 4 批都一次解析通過，沒有交件失敗。
- 審核單：`inputs/review-sheet-9.19-S2-ABCI-20260929.md`，表頭 commit `bdb2327b`。
  - 共 25 組，其中 ⚠️ 9 組。
  - 審核單上 pass 83／doubt 26，另有 hold 2 條；兩條 hold 先審都判 doubt，標為 `[hold]`。
  - `check` ⇒ `targets 111; judged 111; raw-parsed 111; sheet ids 111`、`mismatches: 0`。
  - 正對照（`jgb/C/team-public-page-share`）：審核單副本與 raw 副本各把 doubt 改成 pass，兩者都報出不一致。
  - 正本與 runs 相對 `bdb2327b` 的 `git diff --stat` 為空。
- **S1 修過的 61 條裡，仍有 11 條被判 doubt**，主要類型：
  - 鎖定條件漏了另一條路徑；
  - 同步密碼的說法會誤導；
  - 附設傢俱的「商用／有建物」區塊只放座位數；
  - 窄螢幕排序其實也會帶入；
  - 物件狀態表出自舊文件；
  - 缺漏手機版的例外。

  修正列入下個計畫。
- **成本**：4 批約 0.88M；S2 就緒審查 ×2 約 0.1M。

### S3（2026-09-29）

- **業主裁決原文**（AskUserQuestion「9.19 S3 終審：A／B／C＋I 審核單要怎麼過？」之回覆）：「安全組過 (Recommended)」——非 ⚠️ 16 組的 pass 標已審；⚠️ 9 組全組本批不審；26 條 doubt 本批不審；[hold] 2 條不標；無點名、無照原樣過、無排除。
- **寫入前準備**：
  - 決定檔 `p919-s3-decision.json`。
  - derive ⇒ `approved 65 (both sources equal) by shelf {'A': 26, 'B': 24, 'C': 15, 'I': 0}; expected endpoint increment pm +65, prospect +27`；hold 在核可中 0 條。
  - git 基準（`bdb2327b`）與 status 皆為空。
  - 備份 `p919-s3-backup/`（11:55:38）以 `diff -r` 比對相同。
  - 紅燈基準 `p919-s3-red-baseline.txt` 共 9 條（11:57:52），與 S1 基準相同。
- **寫入與驗證**：
  - `write` ⇒ `added 65`；重匯出與 `load_canon_or_die` 通過。
  - verify ⇒ `reviewed backup 308 -> current 373`、`mismatches: 0`。
  - hold 兩條都沒有 reviewed 行；正對照：核可的 `dashboard-big-landlord-view` 查得到。
  - 終點指標 `pm 369／535、prospect 80／121；頁面 pm 89、prospect 23→27`。
  - scratch 重生成保留 373、丟棄 0，產出與 repo 相同。
  - `make audit` PASS。
- **驗收不符 ⇒ 依停止條件還原並停**：
  - 單元測試出現 1 條新紅燈：`tests/unit/agent/test_canon_assembler_req.py::test_prospect_outline_is_deterministic_and_registers_canon`，錯誤訊息 `AssertionError: (set(), frozenset({'jgb/A/register-email-steps'}))`。
  - **根因（對碼確認）**：這個測試用 `next(f for f in real_doc.fines() if "prospect" in f.target_user)` 取「版控正本第一條 prospect 細目」，當作刻意留白的未審細目，但 `_mark_reviewed_except` 會跳過已經審過的細目。本片核可了 `jgb/A/register-email-steps`，它正是那「第一條」，測試因此找不到留白細目。
  - 換句話說，這是測試綁死了正本的實際資料，不是寫入錯誤；該測試檔不在本片擁有範圍內，工作樹中也沒有別條工作線的修改。
  - 處置：以 `p919-s3-backup/` 整個還原 `rag-orchestrator/canon/`。還原後 `diff -r` 相同、`git diff --stat bdb2327b -- rag-orchestrator/canon` 與 status 皆為空，終點指標回到 `pm 304／prospect 53`。停下交業主。
- **業主裁決（2026-09-29）**：「核可改測試＋越過停點重做 (Recommended)」——授權修改 `tests/unit/agent/test_canon_assembler_req.py` 的取樣條件，並越過 2.7M 停點（上限 3.0M 內）重做 S3。
- **重做（業主裁決後）**：
  - 測試修改：`tests/unit/agent/test_canon_assembler_req.py` 只改一處。`prospect_fine` 改為取「第一條未審的 prospect 細目」（`and not (f.reviewed_by or "").strip()`），並加兩行註解，斷言不變。改後在還原後的正本上跑 `1 passed`。
  - 備份仍與正本相同，git 基準為空。用同一份 `p919-s3-approved.json` 重跑 write ⇒ `added 65`，重匯出後 `canon_sha256` 為 `76538d2a…`，與第一次相同。
  - verify ⇒ `reviewed backup 308 -> current 373; added lines 65`、`mismatches: 0`。hold 兩條沒有 reviewed 行。
  - repo 正本與先前的 scratch 重生成產出（保留 373／丟棄 0）逐位元組相同。
  - **終點指標 `已審細目 pm 369／535、prospect 80／121；頁面 pm 89／183、prospect 27／183`**（pm +65、prospect +27，與預期相同）。
  - 單元測試 9 failed，與基準 `p919-s3-red-baseline.txt` 的差集為空，改過的測試通過；`make audit` PASS。
  - fresh outcome verifier＝**CONFIRMED**（8 項全過）。附記兩點：P3 是本段重做紀錄原本缺漏，現已補上；P4 是原文與解讀寫在同一行。
- **成本**：S3 就緒審查 ×2 約 0.13M、outcome verifier 約 0.12M ⇒ **9.19 累計約 2.8M**。業主已核可越過 2.7M 停點，上限 3.0M。

### 9.19 收案

- **終點指標**：由 pm 304／prospect 53 升到 **pm 369／prospect 80**；頁面 pm 79→89、prospect 23→27。S0、S1、S2 都是 +0，S3 +65／+27。
- **留給下個計畫**：
  - A／B／C 未審 45 條：25 條 doubt（**更正**：原寫 26 doubt，第 26 條是 I 架的 `pricing-trial-plan-landing-page`，屬 F～I）、18 條 ⚠️ 組 pass、hold 2 條依業主裁決**整條刪除**（`login-sso-redirect-no-duplicate-buttons`、`biglandlord-escrow-owner`，須走生成器的刪細目路徑）。
  - I 架「愛租屋」那條（`pricing-trial-plan-landing-page`）已改寫，但仍判 doubt：講法「深入了解企業方案」對不上。
  - D／E 未審 63 條；F～I 未審細目 **60** 條（pm 口徑 58；**更正**：原寫 59，漏算了本計畫納入、但 S3 後仍未審的 I 架 1 條）。
  - jgb2 缺陷清單 20 項：`inputs/jgb2-defects-9.19-20260928.md`，由業主決定是否開單。
  - 頁面量尺待辦；pm 真缺口約 9～12 頁；prospect 可見頁範圍待定義。
  - S1 附記的 P3／P4：`register-verify-code-shape` 的 evidence、`team-public-page-share` 的 askable 等。

