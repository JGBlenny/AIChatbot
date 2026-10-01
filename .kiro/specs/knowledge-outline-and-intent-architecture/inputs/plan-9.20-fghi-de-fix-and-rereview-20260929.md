# Plan 9.20：F～I、D／E 疑點修正＋重審（兩波），先刪 hold 2 條、重抽客戶名詞表

> **現況**（`endpoint_progress.py`，2026-09-29，commit `35b86d77`）：`已審細目 pm 369／535、prospect 80／121；頁面 pm 89／183、prospect 27／183`（A 52／63、B 70／79、C 56／81、D 51／104、E 86／96、F 12／33、G 20／26、H 4／5、I 18／48；prospect 各架未審：A 2、B 1、C 4、D 7、E 5、F 4、G 2、H 1、I 15）。
>
> **本計畫預期**：
> - S0 已審數 +0。hold 2 條刪除後，分母 pm 535→533、prospect 121→120（兩條皆未審：`login-sso-redirect-no-duplicate-buttons` 掛 pm＋prospect，`biglandlord-escrow-owner` 只掛 pm）。
> - 第一波（F～I，S1～S3）：pm +30～45、prospect +10～16。
> - 第二波（D／E，S4～S6）：pm +30～45、prospect +5～9。
> - 依據：9.19 修正加重審 111 條、核可 65 條（59%）。S1／S2／S4／S5 都是 +0。

## 0. 為什麼有這份

- 業主 2026-09-29 對 9.20 範圍建議回「照建議」，內容是：
  - 兩波，先 F～I、再 D／E；A／B／C 剩下的 43 條留到 9.21；
  - 上限 3.5M，第一波收案時（約 1.8M）先停下交業主；
  - S0 刪除 hold 2 條，從程式重新抽客戶名詞表，並改寫「Meta Capital」；
  - 重抽後若在**已審**細目中掃到客戶名，就停下逐條交業主裁，不自動改寫；
  - 終審沿用 D1＋「安全組過」。
- 未審細目共 168 條。2026-09-29 逐條對上最近一次先審的結論，168 條都有結論：

  | 組 | doubt | ⚠️ 組 pass | 先審出處 |
  |---|---|---|---|
  | A／B／C | 27（其中 hold 2） | 18 | 9.19 S2 |
  | D／E | 40 | 23 | 9.16 S3 |
  | F～I | 38（9.18 S2 37 條＋9.19 S2 1 條 `jgb/I/pricing-trial-plan-landing-page`） | 22 | 9.18 S2／9.19 S2 |

  查證方式：以 `rag-orchestrator/canon/jgb.json` 中 `reviewed_by` 為空的細目，對照舊 session scratchpad（`b25be7ef…/scratchpad/`）的 `p916-s3-results.json`、`p918-s2-results.json`、`p919-s2-results.json`，取最近一次判定。S0 會以 repo 內已 commit 的審核單再推一次，作為第二來源。
- 為什麼選 F～I 與 D／E：這兩組每條都只修過零次，修了收穫最多；A／B／C 剩下 25 條 doubt 裡，有 11 條是 9.19 修過後仍被判 doubt 的第三輪件。prospect 未審 41 條中有 22 條在 F～I，所以 F～I 排第一波。

## 1. 切片（順序：S0 → commit → S1 → commit → S2 → S3 → commit → ⏸ 停點 → S4 → commit → S5 → S6 → commit）

所有工具都從 `.claude/skills/outline-curation/scripts/review_pipeline/` 複製到本 session scratchpad 使用：S0 放 `p920-s0/`，第一波放 `p920-w1/`，第二波放 `p920-w2/`。檔頭的變更值依各片改寫，開工前預跑正負對照（README 規定）。jgb2 證據一律讀釘住匯出 `scratchpad/jgb2-b2ee2ac/`，用 README 的 `git -C …/jgb2/dev1 archive b2ee2ac382ce` 建立。

**各片共用的工具設定**（就緒審查 R1 #1、#3）：
- `edit_fine.py` 的 `dump()` 寫死 `indent=1`，`TRAIL` 範本只實測了 A／B／C／I。每一片的副本都要**逐架設定完整序列化參數**，把寫死的 `indent=1` 改成逐架查表：
  - 縮排：H＝2，其餘八架＝1；
  - 檔尾換行 `TRAIL`：逐架實測。
  - 2026-09-29 實測：九架以「逐架縮排＋原檔尾換行」重新序列化，全部與原檔位元組相同；H 若用 indent 1 則不相同。
  - `--roundtrip` 改成跑九架。預跑時九架都要 `byte-identical: True`。
  - 負對照：scratch 副本把 H 強制改回 indent 1 ⇒ 印出 `H roundtrip byte-identical: False` 並 exit 1。
  - **任一架 roundtrip 不是 True ⇒ 在任何編輯之前停下。**
  - 理由：`drafts_diff` 比的是解析後的 JSON，抓不到整檔被重新排版。
- `drafts_diff.py` 一律用 `P919_DIFF_SHELVES=ABCDEFGHI` 跑，讓允許集合外、任何一架的改動都會被 (b)／(c)／(f) 抓到。預跑輸出必須印出 `fines in base (shelves ABCDEFGHI)`。
- 客戶名掃描一律用 S0 產出的 `p920-s0/customer-terms.json` 組 `PAT`。S1／S4 複製的是 `p920-s0/canon_check.py` 與 `p920-s0/name_scan.py`，**⛔ 用範本的舊詞表**；開工前重跑正對照（見 S1）。

### S0 — 前置：hold 刪除、客戶名詞表重抽、Meta Capital 改寫（+0）

- **步驟 0（備份與基準）**：
  - 備份 drafts 全架、`rag-orchestrator/canon/`，以及 `runs/outline-20260920/` 既有的 `*-20260928-s1-919*` 產出，到 `scratchpad/p920-s0/backup/`；以 `diff -r`／`cmp` 確認與現況相同。
  - **紅燈基準**：同一工作樹跑 `scripts/run-tests.sh unit -q -p no:cacheprovider`，把 FAILED 測試 id 集合存成 `scratchpad/p920-s0/red-baseline.txt`。工作樹有 15 檔歸屬待裁的改動，所以不沿用 9.19 的基準。
- **客戶名詞表重抽（依記憶 `feedback_knowledge_authoring_style` 第 9 點）**：
  - 來源一：從釘住匯出系統性抽取特殊團隊定義（`SpecialRole` 常數、`Role.php` 規則鍵、i18n 字串中的團隊／品牌名）。
  - 來源二：歷次先審的 doubt 理由中提到的名稱（9.16～9.19 審核單）。
  - 產出 `scratchpad/p920-s0/customer-terms.json`，每個詞附一個正對照（必中句）與一個負對照（必不中的常用詞，例如「系統上限」）。
  - 更新 `p920-s0/canon_check.py` 的 `PAT`。預跑時，現行正本必須命中 `('D', 'Meta Capital')`（正對照），且「系統上」仍是 6 處。
  - **只掃客戶／合作團隊名，不掃金流或電子簽章廠商**（藍新、中信、國泰、Thinkcloud／雲想科技等）。這些廠商名是產品事實，出現在介面上，不在改寫範圍。
- **全正本掃描與處置**：
  - 新工具 `p920-s0/name_scan.py`：用同一份 `PAT` 逐細目掃 `rag-orchestrator/canon/jgb/*.md`，輸出「細目 id｜命中字串｜是否已審」。`canon_check.py` 只回報架層命中，不分已審與否，所以另寫這支。預跑正對照：必須列出 `jgb/D/contract-payment-method｜Meta Capital｜未審`。
  - 命中在**未審**細目 ⇒ 列入 S0 允許集合，改寫為「特定合作團隊」（沿用 §12-2）。
  - 命中在**已審**細目 ⇒ 不改，停下逐條交業主裁（業主 2026-09-29 已裁）。
  - 已知必中：`jgb/D/contract-payment-method` 的「Meta Capital」（未審）。
- **hold 2 條整條刪除**（業主 2026-09-28 已裁）：`jgb/A/login-sso-redirect-no-duplicate-buttons`、`jgb/B/biglandlord-escrow-owner`。
  - 在 `p920-s0/edit_fine.py` 加 `remove_fine` op：只准刪除 `ALLOWED` 內、且列在 `p920-s0/hold.json` 的細目，其他一律拒絕。
  - `drafts_diff.py` 已支援整條刪除（`item_diff` 產生 `(id, "fine", "", "刪細目")` 項；(b) 限允許集合；(d) 要求刪除集合＝修正紀錄「## 刪除」節；`structural_diff` 排除已刪細目），**不另加檢查**。
- **S0 修正紀錄** `inputs/fix-log-9.20-S0-<日期>.md`，格式同 9.19 S1（依就緒審查 R1 #2 寫死）：
  - 每條 hold 刪除**兩處都要有**：表格列 `` | `<id>` | fine |  | 刪細目 | 業主 2026-09-28 裁定整條刪除 | — | ``（(a) 要求每個差異項都有對應表格列），加上「## 刪除」節的 `` - `<id>` ``（(d) 要求兩邊相等）。
  - 客戶名改寫列的判定欄（「過／不過」）由 **fresh verifier** 填：用 `templates/brief-fix-verify.txt`，只核這幾列。主 session ⛔ 自填「過」。
- **預跑**（scratch drafts 副本，`P919_DIFF_SHELVES=ABCDEFGHI`）：
  - 正對照：刪 hold 1 條＋改寫 1 句客戶名，修正紀錄照上面格式寫，改寫列判定欄暫填「過」（只限預跑）⇒ 印出 `(a) … unlogged diffs: 0`、`(d) … equal: True`、`(e) rows not passed and not a deletion: 0`，(b)(c)(f)(g) PASS。
  - 負對照：
    - `edit_fine` 刪非 hold 細目 ⇒ 拒絕；
    - 在副本 JSON 直接刪一條允許集合內、但不在「## 刪除」節的細目 ⇒ (d) FAIL；
    - 刪允許集合外的細目 ⇒ (b) FAIL；
    - 改動 E 架（S0 不動的架）任一細目 ⇒ (b)／(c) FAIL；
    - 改寫列判定欄改成「不過」⇒ (e) FAIL。
  - 兩條都沒有 open_questions（已對 `open-questions-20260928-s1-919.md` 54 則核對），所以 open_questions 仍是 54。
  - 已知破壞：`ruler-9.12-questions.json` 有 2 題的 gold 指向 `login-sso-redirect-no-duplicate-buttons`，與 9.15 的 3 題同類，記入 §6。9.20 期間不跑 9.12 量尺。
- **重生成**：
  - 先在 scratch 試跑，參數 `--date 20260929-s0-920 --expect-reviewed-kept 373 --expect-open-questions 54`，全部通過才對 repo 跑。
  - `reviewed-dropped` 必須為 `[]`。
- **驗收**：
  - drafts_diff（`P919_DIFF_SHELVES=ABCDEFGHI`）(a)～(g) 全 PASS，改寫列的判定欄全部來自 fresh verifier。
  - 沒有任何允許集合或 hold 細目的架，其 drafts 檔與備份 `cmp` 相同。這份架清單在詞表掃描後寫入 §6；以已知命中推算，至少包括 drafts-C、E、F、G、H、I。
  - `canon_check`：區塊差異只在允許集合內（改寫的細目，加上兩條 hold 的區塊消失）。現行 `canon_check.py` 遇到細目減少會報「fine order/membership differs」，所以 `p920-s0/canon_check.py` 改為：舊順序去掉 hold 兩條後，必須與新順序相同；其餘不變。預跑負對照：scratch 正本多刪一條非 hold 細目 ⇒ 報錯。另外，客戶名在 `.md`、CATALOG、jgb.json 全 0 命中；「系統上」仍 6 處。
  - DSP-068 刪除清單：新的 `dsp-068-deletions-20260929-s0-920.json` 與前一份相比，只有允許集合內的細目可以不同。
  - 終點指標：已審 pm 369、prospect 80 不變；分母 pm 533、prospect 120。
  - 紅燈 id 集合減去 `p920-s0/red-baseline.txt` ＝∅；`make audit` PASS；fresh outcome verifier CONFIRMED。
  - **commit 範圍**：drafts-A／B／D（以及詞表掃出的其他未審命中所在架）、`rag-orchestrator/canon/`、`runs/outline-20260920/*-20260929-s0-920*`、S0 修正紀錄、本計畫；以 `git diff --cached --name-only` 核對範圍外為 0。⛔ `git add -A`。
- **停止**：
  - 已審細目命中客戶名 ⇒ 停，交業主。
  - 任一 `--expect-*` 不過：尚未對 repo 跑 ⇒ 直接停；已對 repo 跑 ⇒ 以 `p920-s0/backup/` 還原後停。
- **擁有**：drafts（只限 S0 允許集合＋hold）、`rag-orchestrator/canon/`（重生成）、`runs/outline-20260920/*-20260929-s0-920*`、本計畫 §6、`scratchpad/p920-s0/`。
- **回滾**：以 `p920-s0/backup/` 還原 drafts 與 canon，刪除本片新產出。
- **預算**：約 0.2M（主 session 自做約 0.05M，改寫列核對 verifier 約 0.05M，outcome verifier 約 0.1M）。

### 第一波：F～I

#### S1 — F～I 38 條 doubt 修正（+0）

- **允許集合**：`p920-w1/allowed.json`，共 38 條＝F～I 未審且最近一次先審為 doubt 的細目。
  - 由腳本以兩個來源各推一次：(1) 舊 scratchpad 的 `p918-s2-results.json`／`p919-s2-results.json`（先複製到 `p920-w1/` 並記 sha256）；(2) repo 內的審核單 `review-sheet-9.18-S2-FGHI-20260928.md`、`review-sheet-9.19-S2-ABCI-20260929.md`。兩者不等或條數≠38 ⇒ 停。
  - 全部是未審細目，重生成時不會丟掉任何已審。
- **步驟 0**：同 S0 的備份與紅燈基準，存到 `p920-w1/backup/`、`p920-w1/red-baseline.txt`。另外量允許集合開工前 evidence 越界數 N，記入 §6。
- **客戶名掃描預跑**（就緒審查 R1 #3）：`p920-w1/canon_check.py` 與 `name_scan.py` 從 `p920-s0/` 複製。預跑時在 scratch 正本放回一句含「Meta Capital」（或任一 S0 抽出的詞）⇒ 必須命中且 exit 1；「系統上」仍是 6 處。
- **修法**（主 session 親修，沿 9.19 S1）：
  - 只修 doubt 理由所指的問題，每條先以 `grepcheck.py` 對釘住匯出確認 doubt 的程式證據，再改寫。
  - doubt 理由若落在 54 則待裁（F 14、G 6、H 1、I 13）所記的文件與程式衝突上 ⇒ 只寫程式可證的畫面行為，或整句刪；⛔ 替業主選邊。
  - 客戶名改寫為「特定合作團隊」；實作詞刪除或改寫；引號內的介面標籤要逐字對到畫面。
  - 必須整條刪除才能成立 ⇒ 不刪，停下列給業主，並加入 hold 清單。
  - 同粗目改寫後不得互相矛盾。
- **修正紀錄**：`inputs/fix-log-9.20-S1-FGHI-<日期>.md`，格式同 9.19 S1，依據欄指向 9.18（或 9.19）審核單的 doubt 理由。
- **核對**：fresh verifier 分 2 包（F＋H、G＋I，依粗目不拆），序列跑。brief 用 `templates/brief-fix-verify.txt`。D1：修一次仍不過 ⇒ 整句刪；整句刪後剩 0 句 ⇒ 停下交業主。
- **差異比對與重生成**：drafts_diff (a)～(g) 全 PASS（`P919_DIFF_SHELVES=ABCDEFGHI`）；先在 scratch 試跑，參數 `--date <日期>-s1-920 --expect-reviewed-kept 373 --expect-open-questions 54`，通過才對 repo 跑。
- **驗收**：
  - A～E 的 drafts 與 `.md` 跟備份位元組相同。
  - F～I 的區塊差異只在允許集合內（`canon_check`）；客戶名 0 命中；DSP-068 刪除清單只有允許集合內的細目可以變動。
  - 允許集合的 evidence 越界數不超過開工前的 N。
  - 已審集合不變（373）；終點指標不變。
  - 紅燈差集＝∅；`make audit` PASS；fresh outcome verifier CONFIRMED。
  - commit 範圍：drafts-F／G／H／I、`rag-orchestrator/canon/`、`runs/outline-20260920/*-<日期>-s1-920*`、修正紀錄、本計畫。
- **停止**：同 9.19 S1（需要臆測才能成立或必須整條刪 ⇒ 停；比對或重生成不過 ⇒ 依是否已對 repo 跑決定直接停或還原後停；累計達 §3 停點 ⇒ 停）。
- **擁有**：drafts-F／G／H／I（只限允許集合）、`rag-orchestrator/canon/`、`runs/outline-20260920/*-<日期>-s1-920*`、修正紀錄、本計畫 §6、`scratchpad/p920-w1/`。
- **預算**：約 0.6M（主 session 修正約 0.3M、verifier 2 包加複核約 0.2M、outcome verifier 約 0.1M）。

#### S2 — F～I 60 條重新先審（+0）

- **分母**：S1 commit 後 F～I 未審的全部細目，共 60 條，存 `p920-w1/s2-targets.json`，數目≠60 ⇒ 停。其中 22 條 ⚠️ 組 pass 內容沒改，要和修正後的同組細目一起重審，才抓得到跨細目矛盾。
- **工具**：`p920-w1/review_sheet.py`，變更值 `CANON_COMMIT=<S1 commit>`、`SHELVES=FGHI`、前綴 `p920-s2`、標題「Plan 9.20 S2」。hold 清單沿用 S1 新增的（若有）。
- **批次**：粗目不拆、每批 ≤35，預計 2 批；派工前把對照表存成 `p920-w1/s2-batches.json`，聯集須＝targets 且互不重疊。
- **brief**：`templates/brief-prereview.txt`（9.19 S2 版）。派工前以 grep 確認每批 sources 前綴都在來源清單內。
- **審核單與驗收**：
  - 審核單 `inputs/review-sheet-9.20-S2-FGHI-<日期>.md`；
  - `check` 輸出 `targets 60; judged 60; raw-parsed 60; sheet ids 60`、不符 0；
  - 正對照：審核單副本與 raw 副本各把一條 doubt 改成 pass，兩者都要報出不一致；
  - 正本相對 S1 commit 無變動。
- **停止與回滾**：交件失敗時，同一代理重貼一次，仍失敗即停；中途停下時，未跑的批次在審核單列「未先審」；回滾只刪審核單與 `p920-s2` 檔。
- **預算**：2 批約 0.45M。

#### S3 — 業主終審＋寫入已審（pm 最多 +58、prospect 最多 +22；實際依「安全組過」）

- 流程同 9.19 S3：
  1. 業主原文逐字記入 §6；
  2. `approve_write.py derive`（兩來源推導相同才寫，排除 hold）；
  3. 備份 canon 並以 `diff -r` 核對；量寫入前紅燈基準；
  4. `write`；
  5. 容器重匯出（9.19 S3 步驟 5 的完整指令）；
  6. `verify --backup`。
  - 環境變數：`P918_WRITE_SHELVES=FGHI`、`P918_SHEET=<S2 審核單絕對路徑>`。
- **驗收**：
  - verify `mismatches: 0`；A～E、CATALOG 位元組不變；
  - scratch 重生成保留檢查逐位元組相同（⛔ 對 repo 跑）；
  - 終點指標＝369＋增量／80＋增量；
  - 紅燈差集＝∅（出現新紅燈時，先查是否為測試取樣綁了正本資料，§12-3）；
  - `make audit` PASS；fresh outcome verifier CONFIRMED。
  - commit：F～I `.md`、jgb.json、S2 審核單、本計畫、HANDOFF 終點行。
- **停止**：寫入前失敗 ⇒ 直接停；寫入後驗收不符 ⇒ 以備份還原並停，交業主。
- **預算**：約 0.2M。

#### ⏸ 第一波停點

S3 commit 後停下，回報終點指標、成本與 §6 紀錄。第二波在業主明示後才開始（業主 2026-09-29 已裁）。

### 第二波：D／E

#### S4 — D／E 40 條 doubt 修正（+0）

- **允許集合**：`p920-w2/allowed.json`，共 40 條＝D／E 未審且 9.16 S3 先審為 doubt 的細目。兩來源推導：舊 scratchpad 的 `p916-s3-results.json`，以及 `review-sheet-9.16-S3-DE-20260927.md`。不等或條數≠40 ⇒ 停。
- **與 S1 的差異**：9.16 之後，9.18 S1（客戶名改寫、IoT／點退例外）與本計畫 S0 都動過 D／E 部分細目。每條先比對 doubt 理由在現行文字上是否仍成立；已被處理的記為「已由 9.18／9.20 S0 處理」，不再改。
- 其餘步驟、驗收、停止、擁有與 S1 相同，把架換成 D／E：
  - 修正紀錄 `inputs/fix-log-9.20-S4-DE-<日期>.md`；
  - verifier 分 2 包（D、E）；
  - 重生成 `--expect-reviewed-kept <373＋S3 核可數>`；
  - A～C、F～I 位元組不變；
  - scratch 目錄 `p920-w2/`。
- **預算**：約 0.65M。

#### S5 — D／E 63 條重新先審（+0）

- 同 S2：分母 63 條（`SHELVES=DE`、前綴 `p920-s5`），預計 2 批。
- 審核單 `inputs/review-sheet-9.20-S5-DE-<日期>.md`，`check` 須為 `targets 63; judged 63; …`、不符 0。
- **預算**：約 0.5M。

#### S6 — 業主終審＋寫入已審（pm 最多 +63、prospect 最多 +12）

- 同 S3：`P918_WRITE_SHELVES=DE`，其他架位元組不變；commit D／E `.md`、jgb.json、S5 審核單、本計畫、HANDOFF 終點行。
- **預算**：約 0.2M。

## 2. 不做（另案）

- A／B／C 剩下的 43 條（25 doubt 中 11 條是第三輪件、18 條 ⚠️ 組 pass），留到 9.21。
- 頁面量尺（業主已裁「先不動、列待辦」）；pm 真缺口補寫；prospect 可見頁範圍定義。
- 54 則待裁的裁決、jgb2 缺陷清單 20 項要不要開單。
- 6 條 `sources` 必填紅燈、售前與業者政策文字的長度問題。
- 工作樹中 15 檔的歸屬（業主裁決前，本線不動、不 revert；commit 只 add 本線檔）。
- drafts 既有的 evidence 句序錯位 23 條（本計畫只保證允許集合內不增加越界）。
- 9.19 S1 附記的 P3／P4（`register-verify-code-shape` 的 evidence 等，屬 A／B／C）。

## 3. 業主裁決與待裁

- **已裁（2026-09-29「照建議」）**：
  - 範圍與順序：兩波，F～I → D／E。
  - 預算：上限 3.5M；第一波收案（S3 完成）時停下交業主。若在 S3 完成前累計就達到 1.8M，也要先停。
  - 已審細目命中客戶名：停下逐條交業主裁。
  - 終審：D1＋「安全組過」。
- **業主裁決（2026-10-01）**：「核可，ASK」——核可大綱＋S0＋S1；執行模式 ASK（每片回報）。S2～S6 開工前各自再送就緒審查。

## 4. 停止條件（全片共用）

- 已審細目數任何時候下降 ⇒ 停下交業主（本計畫預期不會下降：允許集合全是未審細目，hold 兩條也未審）。
- 正本只准在 S0／S1／S4 的重生成（只動允許集合與 hold），以及 S3／S6 的寫入（只加 reviewed 行）時變動。
- 累計達停點先停；超過上限即停。
- 一次只跑一個代理（本機 8GB）。
- 代理 brief 一律帶 §12-2 的必禁清單，外加「⛔ 直接讀 `/Users/chenqinghuang/dev/work/jgb2/`」。

## 5. 就緒審查紀錄

- **大綱＋S0＋S1 第 1 輪（R1）＝REVISE，P2×3**，三條都在工具程式中重現，全數 FIX：
  1. S0 沒指定 `P919_DIFF_SHELVES`（範本預設 `ABCI`，漏掉 D）；`edit_fine.py` 的 `TRAIL`／`--roundtrip` 只涵蓋 A／B／C／I。
     ⇒ 各片一律 `ABCDEFGHI`、九架實測序列化參數並跑九架 roundtrip（縮排部分於 R2 補上）；列出必須 `cmp` 相同的架。
  2. 修正紀錄格式與 (a)／(e) 不符：刪細目也需要表格列；改寫列的「過」沒有指定由誰判。
     ⇒ 寫死兩處格式；改寫列交 fresh verifier 判；補正負對照。
  3. S1 會沿用範本的舊客戶名詞表。
     ⇒ S1／S4 改用 `p920-s0/` 的詞表工具，並補放回「Meta Capital」的正對照。
- **第 2 輪（R2）＝REVISE，P2×1**：R1 #1 只處理了檔尾換行，但 drafts-H 是 2 格縮排，`edit_fine.py` `dump()` 卻寫死 `indent=1`，所以 H 的 roundtrip 必然失敗；若照樣編輯 H，整檔會被重新排版，而 drafts_diff 抓不到。已實測重現。
  - 這是**第二次自動 REVISE ⇒ 停止重送，逐條處置**：**FIX**。「各片共用的工具設定」改為逐架設定縮排（H＝2）與 `TRAIL`，加入 H 的負對照，並規定任一架 roundtrip 不是 True 就在編輯前停下。
  - 依規則開一次收尾審查（新的就緒期）；若再判 REVISE，就暫停交業主，不再重送。
- **收尾審查（fresh plan-verifier）＝READY** ⇒ 大綱＋S0＋S1 交業主核可（`next_gate: user_approval`）。
- S2、S3、S4、S5、S6 開工前各自再送就緒審查。

## 6. 執行紀錄

### 立案前盤查（2026-09-29）

- `/canon-audit outline-drafting` 應讀 10 份，`audit.py status` 結果為 `10/10 已完整讀過`。9 份文件由主 session 整檔讀過；`runs/outline-20260920/` 目錄（24 檔、1.6 MB）由 3 位 scout 加上主 session 補讀完成。
- ⚠️ **scout 自稱「整檔讀完」不可信**：讀取收據（`~/.claude/canon/state/receipts/<session>.json`）顯示——
  - 讀 D 架的 scout 只讀了第 1～2000 行與 5500 行以後，卻回報了細目總數與最後一條 id；
  - 另一位 scout 越界讀了派工範圍外的 7 個檔；
  - E 架（缺最後 1 行）、F 架、I 架（缺第 2875～3179 行）也都不完整。
  - 缺的行段由主 session 補讀。因此 scout 回報的客戶名命中清單**不作為證據**；S0 的詞表與掃描一律由程式產出。
- 盤查成本另計，不計入本計畫上限。

### S0（2026-10-01）

- **步驟 0**：
  - 備份 `scratchpad/p920-s0/backup/`（16:17:11，早於第一次編輯 16:20:09）：canon `diff -r` 相同，drafts 九架 `cmp` 相同，runs 的 `*-20260928-s1-919*` 也已備份。
  - 紅燈基準 `p920-s0/red-baseline.txt`：9 條，與 §12-2 名單逐名相同。全套結果 `9 failed, 3931 passed, 3 skipped`。
  - jgb2 釘住匯出重建於 `scratchpad/jgb2-b2ee2ac/`（210M）；正對照 `checkIotBill` 在 `app/Bill.php` 命中 11。
- **客戶名詞表**：`p920-s0/customer-terms.json` 共 18 詞。
  - 來源：
    - 程式：`config/app.php` 的特殊團隊 role id 設定與其註解（新北住都、大瀚商務、ANGO、富喬、資育、資聯、南軟／高軟育成部、`tone_sang`、`joerich`、`nthurc`、`gtb`）；`config/contract.php` 的範本名稱（新北住都中心、大瀚商務、Meta Capital、半伴）；`src/use/config/useSpecialRoles.js`。
    - 歷次 doubt 理由：統上、新北住都、樓宇／21228、愛租屋、Meta Capital。
  - 每詞附正負對照，`name_scan.py` 先自檢：18／18 正對照命中、負對照 0 命中。
  - 原本的全域旗標 `(?i)` 全部改成區段旗標，合併成一個正則後不再有 DeprecationWarning。
  - **掃描結果**：541 條中只命中 `jgb/D/contract-payment-method｜Meta Capital｜未審`；已審命中 0 ⇒ 不需交業主。「系統上」6 處。
- **工具**：
  - `edit_fine.py`：逐架 `INDENT`（H＝2）與九架 `TRAIL`（實測 `tail -c1`：B／D／I 為 `\n`）；新增 `remove_fine` op，只限 `hold.json`。
    - 九架 roundtrip 全部 `True`。
    - 負對照：H 改成 indent 1 ⇒ `H … False`、exit 1。
  - `canon_check.py`：`PAT` 改讀 `customer-terms.json`；細目集合比對改為「舊集合去掉 hold 後須等於新集合」，另外檢查不得出現新細目。
- **預跑**（scratch `p920-s0/pc/`，`P919_DIFF_SHELVES=ABCDEFGHI`）：
  - 正對照：刪 hold 1 條＋改寫 1 句 ⇒ `(a) unlogged diffs: 0`、`(d) equal: True`、`(e) 0`、PASS。
  - 負對照全數如預期：
    - `edit_fine` 刪非 hold 細目 ⇒ 拒絕；
    - 刪允許集合內、但不在「## 刪除」節的細目 ⇒ (a)(d) FAIL；
    - 刪允許集合外的細目 ⇒ (b) FAIL；
    - 改動 E 架 ⇒ (b)(c) FAIL；
    - 判定欄改成「不過」⇒ (e) FAIL。
  - canon_check 負對照：多刪一條非 hold 細目 ⇒ `C: fine order/membership differs`、exit 1。
  - name_scan 負對照：放回「Meta Capital」⇒ 命中、exit 1。
- **修正**：允許集合 3 條（`p920-s0/allowed.json`）：
  - hold 2 條用 `remove_fine` 刪除；
  - `contract-payment-method` 句 1 改寫為「特定合作團隊的專用範本」。
  - 修正紀錄 `inputs/fix-log-9.20-S0-20261001.md`。
  - fresh verifier＝**CONFIRMED**（1／1 過）。附 P4：本條可以寫得更精確，例如「某特定合作團隊的兩份專用範本」；延到 S4 處理。
- **差異比對**：(a)～(g) PASS（`ABCDEFGHI`）；drafts-C／E／F／G／H／I 與備份 `cmp` 相同。
- **重生成**：
  - scratch 試跑 `已審保留：373 條／丟棄：0 條`、`57 粗目／539 細目`、DSP-068 刪除 24 行／28 字元，與前次清單集合相同；open_questions 54 則，內文與前次相同。
  - 第一次對 repo 跑失敗：容器把 `/.claude` 掛成唯讀，寫 `reviewed-dropped` 時拋 `OSError`。事後確認 repo 正本與備份 `diff -r` 相同，**沒有寫到一半**。
  - 改為 `--runs-out` 指向 `/scratch/p920-s0/repo-runs` 後重跑成功，再把 3 個 runs 產出複製進 repo。
  - repo 正本與 scratch 試跑逐位元組相同（`diff -r`）；3 個 runs 產出也 `cmp` 相同。
  - ⚠️ S1／S4 的「對 repo 跑」一律照這個方式：`--runs-out` 寫 scratch，再複製回 repo。
- **驗收**：
  - `canon_check` ⇒ `blocks changed 1 (in allowed 1)`、`mismatches: 0`，客戶名 0、「系統上」6。
  - `name_scan` ⇒ 539 條、0 命中。
  - `load_canon_or_die` 通過：539 條，`canon_sha256 a80f1142…`。
  - **終點指標 `已審細目 pm 369／533、prospect 80／120；頁面 pm 89／183、prospect 27／183`**：已審數不變，分母 pm 535→533、prospect 121→120，與預期相同。
  - 全套單元 `9 failed, 3931 passed, 3 skipped`；紅燈集合減去基準＝∅。
  - `make audit` OVERALL PASS。
- **已知破壞**：`ruler-9.12-questions.json` 有 **2 題**（`…#0`、`…#1`）的 gold 指向已刪除的 `login-sso-redirect-no-duplicate-buttons`（outcome verifier 更正，原寫 1 題）。與 9.15 的 3 題同類，9.20 期間不跑 9.12 量尺。
- **fresh outcome verifier＝CONFIRMED**（7 項全過；自建正對照：在 scratch 正本注入 3 個詞 ⇒ 3 命中）。附記 P3：已知破壞題數 1→2，已更正。
- **成本**：S0 約 0.35M（含 jgb2 匯出與預跑、修正核對 verifier 約 0.06M、outcome verifier 約 0.2M——它重跑了全套單元與 audit）。
