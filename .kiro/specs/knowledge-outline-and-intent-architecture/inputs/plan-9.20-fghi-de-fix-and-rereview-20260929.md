# Plan 9.20：F～I、D／E 疑點修正＋重審（兩波），先刪 hold 2 條、重抽客戶名詞表

> **現況**（`endpoint_progress.py`，2026-09-29，commit `35b86d77`）：`已審細目 pm 369／535、prospect 80／121；頁面 pm 89／183、prospect 27／183`（A 52／63、B 70／79、C 56／81、D 51／104、E 86／96、F 12／33、G 20／26、H 4／5、I 18／48；prospect 各架未審：A 2、B 1、C 4、D 7、E 5、F 4、G 2、H 1、I 15）。
>
> **進度（2026-10-03）**：第一波收案——S0 `1286d00a`、S1 `46234eb0`、停點紀錄 `6a7362e1`、S3 `a9c377df` 已 commit。**現值 `已審細目 pm 420／533、prospect 98／120`**（已審 424 條；S3 後重跑）。業主 2026-10-03 開第二波（§3），S4 進行中。
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
- **已預跑**（2026-10-01，S1 commit `46234eb0` 後；repo 未動）：
  - `p920-w1/p920-s2-targets.json`：從正本取 F～I 未審細目，共 60 條。
  - `p920-w1/p920-s2-batches.json`：依正本順序、粗目不拆、每批 ≤35，聯集＝targets，重複 0：
    - S2B1 28 條：F 4 組＋G 3 組＋H 1 組；
    - S2B2 32 條：I 6 組。
  - `p920-w1/p920-s2-hold.json`＝`[]`（本波沒有 hold；S1 也沒有整條刪除的細目）。
  - `p920-w1/review_sheet.py` 變更值：`CANON_COMMIT="46234eb0"`、`SHELVES` 預設 `FGHI`、`PREFIX="p920-s2"`、標題「Plan 9.20 S2 F～I 修正後重新先審」。
    - 空結果預跑：`parse` ⇒ `parsed 0 ids`；`check` ⇒ `targets 60; judged 0; raw-parsed 0; sheet ids 60`、`mismatches: 0`。
    - 負對照：`P919_SHELVES=FGH` ⇒ `❌ 32 targets not found in canon shelves FGH`。
  - brief：`p920-w1/brief-prereview-S2B{1,2}.txt`，由 `templates/brief-prereview.txt` 機械產生：
    - 換成本計畫名稱、批次、條數與釘住匯出路徑；
    - 補上 README 列的三項：講法要答得到；現行程式走不到的情境判 doubt；同粗目比對涵蓋不在本批的細目（含已審）；
    - 附待裁清單路徑，並寫明「已依程式寫、未選邊，不算 doubt」。
    - 各批 sources 前綴（S2B1 code／help、S2B2 code）都在 brief 的來源清單內。
  - S1 附的 P3／P4 建議 8 項（修正紀錄「核對過程」）不預告給先審代理，以保持判定獨立；S2 結果出來後，在審核單之外另列「建議」交業主參考。
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
- **已預跑**（2026-10-03，業主核可越過停點後；repo 正本未動）：
  - 工作區：S2 scratch 整份複製到本 session `scratchpad/p920-w1/`，`diff -rq` 相同，6 個產物 sha256 前 16 碼與 `s2-findings-9.20-20261001.md` §4 逐一相同。工具 `approve_write.py` 讀同目錄的 `p920-s2-{results,targets,hold}.json`、PLAN 指本計畫、段落「### S3」。
  - 業主原文已逐字記入 §6「### S3」；決定檔 `p920-w1/p920-s3-decision.json`（rule＝safe，其餘三欄空）。
  - derive（`P918_WRITE_SHELVES=FGHI`、`P918_SHEET=<S2 審核單絕對路徑>`）⇒ `approved 51 (both sources equal) by shelf {'F': 19, 'G': 6, 'H': 1, 'I': 25}; expected endpoint increment pm +51, prospect +18`。核可集合內 doubt 0 條；未核可的 pass 只有 ⚠️ 組的 `jgb/I/homepage-latest-news-section`。
  - 對照：rule 改 all ⇒ 52（多出 ⚠️ 組那條，prospect +19）；reply 改成不在 §6 的字串 ⇒ `❌ decision reply is not verbatim inside plan §6 ### S3 record`。
  - scratch 正本 `p920-s3-pc/`（repo canon 複製，`diff -r` 相同）：write ⇒ `added 51`；容器重匯出（9.19 S3 步驟 5 指令，路徑換 `/scratch/p920-s3-pc/canon`）與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 373 -> current 424; added lines 51; approved 51`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；A～E、CATALOG 與備份 `cmp` 相同。
  - scratch 重生成保留檢查（`--expect-reviewed-kept 424 --expect-open-questions 54`，`--runs-out` 寫 scratch）⇒ `已審保留：424 條／丟棄：0 條`、57 粗目／539 細目，產出與 scratch 正本 `diff -r` 相同。
  - scratch 終點指標 `已審細目 pm 420／533、prospect 98／120；頁面 pm 109／183、prospect 40／183`。
  - 紅燈基準（repo 工作樹、寫入前，00:55:59～00:56:57）：`9 failed, 3931 passed, 3 skipped`，集合存 `scratchpad/p920-s3-red-baseline.txt`，與 §12-2 名單逐名相同。
  - 預測新紅燈：把 scratch 正本掛到容器 `/app/canon`（正對照：容器內 `grep -c reviewed /app/canon/jgb/F.md`＝31，repo 為 12）跑全套單元 ⇒ `9 failed, 3931 passed`，與基準差集＝∅（9.19 S3 的「測試綁正本資料」紅燈本次未出現）。
- **對 repo 執行的步驟**：備份 `rag-orchestrator/canon/` 至 `scratchpad/p920-s3-backup/` 並 `diff -r`；`git diff --stat 46234eb0 -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆須為空 ⇒ write ⇒ 容器重匯出（`/app/canon`）⇒ verify `--backup p920-s3-backup` ⇒ 終點指標、全套單元差集、scratch 重生成與 repo `diff -r`、`make audit` ⇒ fresh outcome verifier ⇒ commit。
  - commit 範圍：F／G／H／I `.md`、`jgb.json`、本計畫、HANDOFF（終點行與現況）；`git diff --cached --name-only` 範圍外 0。CATALOG 須與備份相同，不在範圍內。
  - 寫入後還原：用 `p920-s3-backup/` 整個還原 `rag-orchestrator/canon/`，`diff -r` 與 `git diff --stat 46234eb0 -- rag-orchestrator/canon` 為空後停下交業主（已審數回到 373，屬預先授權的還原）。

#### ⏸ 第一波停點

S3 commit 後停下，回報終點指標、成本與 §6 紀錄。第二波在業主明示後才開始（業主 2026-09-29 已裁）。

### 第二波：D／E

#### S4 — D／E 40 條 doubt 修正（+0）

- **允許集合**：`p920-w2/allowed.json`，共 40 條＝D／E 未審且 9.16 S3 先審為 doubt 的細目。兩來源推導：舊 scratchpad 的 `p916-s3-results.json`，以及 `review-sheet-9.16-S3-DE-20260927.md`。不等或條數≠40 ⇒ 停。
- **與 S1 的差異**：9.16 之後，9.18 S1（客戶名改寫、IoT／點退例外）與本計畫 S0 都動過 D／E 部分細目。每條先比對 doubt 理由在現行文字上是否仍成立；已被處理的記為「已由 9.18／9.20 S0 處理」，不再改。
  - **記錄格式**：已處理的細目**不進修正表**（修正表每列都必須對到一筆 drafts 差異，否則 drafts_diff (a) 判 `log rows with no diff` FAIL），改列在修正紀錄獨立一節 `## 已由前案處理`，每條一行 `- \`<id>\`：<哪一案處理、現行文字為何已不成立>`。
  - 預跑（drafts 未改的 scratch 副本 `p920-w2/pc0/`）：只有該節 ⇒ `(a) fix-log rows: 0; unlogged diffs: 0; log rows with no diff: 0`、PASS；負對照：同一細目改寫成無差異的表格列 ⇒ `log rows with no diff: 1`、FAIL。
  - **已由前案處理也要獨立核對**：`## 已由前案處理` 的每一條，連同 9.16 doubt 理由與現行文字，一併放進 D／E 修正核對的 fresh verifier 包，判「過／不過」；判「不過」的回到一般修正（D1）。主 session ⛔ 自行認定後不送核對。
  - **涵蓋檢查（S4 驗收新增一項）**：`p920-w2/coverage_check.py <allowed.json> <修正紀錄>`——修正表 id ∪ `## 已由前案處理` id ∪ `## 停下交業主` id ＝ `allowed.json` 40 條，兩兩不交、不得有允許集合外的 id；不符 exit 1。
    - 預跑：正對照（38 列修正表＋2 條已處理）⇒ `union 40`、PASS；負對照：漏 1 條 ⇒ `missing 1`、FAIL；同一 id 同時在修正表與已處理 ⇒ `in both table and handled`、FAIL。
- **終點指標（+0，S6 的前置）**：開工前與完成後都須為 `已審細目 pm 420／533、prospect 98／120`；**已審集合維持 424 條**（取代 S1 驗收中的「373」）。
- 其餘步驟、驗收、停止、擁有與 S1 相同，把架換成 D／E：
  - 修正紀錄 `inputs/fix-log-9.20-S4-DE-<日期>.md`；
  - verifier 分 2 包（D、E）；
  - 重生成 `--expect-reviewed-kept <373＋S3 核可數>`；
  - A～C、F～I 位元組不變；
  - scratch 目錄 `p920-w2/`。
- **預算**：約 0.65M；**中途停點：S4 單片實際超過 0.9M 即停下交業主**（業主 2026-10-03「a」）。
- **已預跑**（2026-10-03，S3 commit `a9c377df` 後；repo 未動）：
  - ⚠️ **舊 scratchpad 已清空**：9.16 的 `p916-s3-results.json`（b25be7ef）、S0／S1 的 `p920-s0/`、`p920-w1/`、jgb2 匯出（ea138b18）都不在。以下逐項重建，全部放本 session `scratchpad/p920-w2/`。
  - **允許集合第二來源重建**：用 `extract_verdict.py` 從 9.16 S3 五批先審代理的 transcript（`~/.claude/projects/<專案>/b25be7ef…/subagents/agent-{a53c7110…,a01b4e6e…,aea14d47…,a78b4aed…,aefbdc2a…}.jsonl`，09-27 19:10～19:57）機械重取 raw ⇒ `p916-recovered/p916-s3-raw-S3B{1..5}.txt`，共 138 條（26／29／29／30／24）。
    - 與 repo 審核單 `review-sheet-9.16-S3-DE-20260927.md` 比對：id 集合相同、138 條判定逐條相同；doubt 兩邊都是 40 條且集合相同。
    - 40 條都在現行正本、都未審；D／E 其餘未審 23 條在 9.16 全是 pass（＝⚠️ 組 pass），合計 63，與 S5 分母一致。
    - `allowed.json` 共 40 條（D 30／E 10）；允許集合 evidence 152 筆，越界 0。
  - **工具重建**：`review_pipeline/` 範本複製後，從 S0 session 的 transcript（`ea138b18….jsonl` 中 S0 的 Bash 指令原文）逐字重放兩段 patch（`edit_fine.py` 的逐架 INDENT／TRAIL＋`remove_fine`；`canon_check.py` 讀詞表＋hold 規則），並逐字還原 `customer-terms.json`（18 詞，`(?i)` 改區段旗標）與 `name_scan.py`。
    - TRAIL 重新實測（`tail -c1`）：B／D／I 為 `\n`，其餘 `}`，與 patch 值相同。
    - 九架 roundtrip 全 True；H 改 indent 1 的負對照 exit 1。
    - `name_scan`：自檢 18／18 正對照命中、負對照 0；repo 正本 539 條 0 命中、「系統上」6，exit 0；scratch 副本放回「Meta Capital」⇒ 命中 1、exit 1。
  - **jgb2 釘住匯出**重建於 `scratchpad/jgb2-b2ee2ac/`（210M）；正對照 `checkIotBill` 在 `app/Bill.php` 命中 11（與 S0 相同）。
  - **步驟 0**：備份 `p920-w2/backup/`（drafts 九架、canon、runs 的 `*-20261001-s1-920*`；01:11:25），`diff -r`／`cmp` 相同；git 對 canon 與 runs 為空。紅燈基準沿用 S3 寫入後同一工作樹的全套結果（9 條，與 §12-2 名單相同）。
  - 重生成預期：`--expect-reviewed-kept 424 --expect-open-questions 54`（424＝373＋S3 核可 51）。

#### S5 — D／E 63 條重新先審（+0）

- 同 S2：分母 63 條（`SHELVES=DE`、前綴 `p920-s5`），預計 2 批。
- 審核單 `inputs/review-sheet-9.20-S5-DE-<日期>.md`，`check` 須為 `targets 63; judged 63; …`、不符 0。
- **預算**：約 0.5M。
- **終點指標（+0，S6 的前置）**：開工前與完成後都須為 `已審細目 pm 420／533、prospect 98／120`（已審 424）；正本相對 S4 commit `589e0a14` 不得有任何變動。
- **已預跑**（2026-10-03，S4 commit `589e0a14` 後；repo 未動）：
  - 工作區 `scratchpad/p920-w5/`：`review_sheet.py`、`extract_verdict.py` 由 S2 版（`p920-w1/`）複製，變更值 `CANON_COMMIT="589e0a14"`、`SHELVES` 預設 `DE`、`PREFIX="p920-s5"`、標題「Plan 9.20 S5 D／E 修正後重新先審」。
  - `p920-s5-targets.json`：從現行正本取 D／E 未審細目共 **63** 條（D 53／E 10）＝S4 允許集合 40 條＋9.16 ⚠️ 組 pass 23 條。
  - `p920-s5-batches.json`（S2 同一格式 `{批次: [{"coarse", "ids"}]}`）：依正本順序、粗目不拆（粗目跨批重複 0，程式檢查）、每批 ≤35，聯集＝targets、重複 0：S5B1 34 條（3 組：D-contract-edit-general 6／D-contract-edit-social-housing 19／D-contract-sign-view 9）、S5B2 29 條（9 組：D 5 組＋E 4 組）。
  - **非空預跑**（`scratchpad/p920-w5-pc/` 副本，合成 raw：63 條中 1 條 doubt）：`parse` ⇒ `parsed 63 ids: pass 62 / doubt 1`；`sheet` ⇒ `groups 12, pass 62 / doubt 1 / pending 0`；`check` ⇒ `targets 63; judged 63; raw-parsed 63; sheet ids 63`、`mismatches: 0`。負對照：合成 raw 刪 1 條 ⇒ `❌ S5B2: missing ids ['jgb/D/move-out-bill-generation']`、exit 1。實際 `p920-w5/` 無合成 raw，`p920-s5-results.json`＝`{}`。
  - `p920-s5-hold.json`＝`[]`。
  - 空結果預跑：`parse` ⇒ `parsed 0 ids`；`sheet` ⇒ `groups 12 … pending 63`；`check` ⇒ `targets 63; judged 0; raw-parsed 0; sheet ids 63`、`mismatches: 0`。負對照：`P919_SHELVES=D` ⇒ `❌ 10 targets not found in canon shelves D`。
  - brief `p920-w5/brief-prereview-S5B{1,2}.txt`：S2 用的 brief 原文已不在 scratchpad，從 S2 先審代理 transcript（`ea138b18…/subagents/agent-a3c18351…jsonl` 的 Read 結果）逐字取回（`s2-brief-recovered.txt`，89 行），只機械替換批次名、條數、架、id 清單、待裁清單路徑（`open-questions-20261003-s4-920.md`）與 jgb2 匯出路徑；判準段（含講法要答得到、走不到的情境、同粗目含已審比對）逐字沿用。
  - S4 核對附的延後建議不預告給先審代理，以保持判定獨立；S5 結果出來後在審核單之外另列。
- **驗收**（同 S2）：兩批一次一位代理；raw 由 `extract_verdict.py` 機械取出；`check` ⇒ `targets 63; judged 63; raw-parsed 63; sheet ids 63`、`mismatches: 0`；正對照：審核單副本與 raw 副本各把一條 doubt 改成 pass，兩者都要報出不一致；正本相對 `589e0a14` 的 `git status` 為空。
- **停止與回滾**：交件失敗時同一代理重貼一次，仍失敗即停；中途停下時未跑批次在審核單列「未先審」；回滾只刪審核單與 `p920-s5` 檔。

#### S6 — 業主終審＋寫入已審（pm 最多 +63、prospect 最多 +12）

- 同 S3：`P918_WRITE_SHELVES=DE`，其他架位元組不變；commit D／E `.md`、jgb.json、S5 審核單、本計畫、HANDOFF 終點行。
- **預算**：約 0.2M。
- **已預跑**（2026-10-03，業主終審回覆後；repo 正本未動）：
  - 工具 `p920-w5/approve_write.py`：由 S3 版複製，results／targets／hold 改讀 `p920-s5-*`、段落 `### S6`。業主原文已逐字記入 §6「### S6」；決定檔 `p920-w5/p920-s6-decision.json`（rule＝safe）。
  - derive（`P918_WRITE_SHELVES=DE`、`P918_SHEET=<S5 審核單絕對路徑>`）⇒ `approved 37 (both sources equal) by shelf {'D': 33, 'E': 4}; expected endpoint increment pm +37, prospect +7`。對照：reply 改成不在 §6 的字串 ⇒ `❌ decision reply is not verbatim…`；rule 改 all ⇒ 50（pm +50、prospect +10）。
  - scratch 正本 `p920-s6-pc/`：write ⇒ `added 37`；容器重匯出與 `load_canon_or_die` 通過；verify ⇒ `reviewed backup 424 -> current 461; added lines 37; approved 37`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；A～C、F～I、CATALOG 與備份 `cmp` 相同。
  - scratch 重生成保留檢查（`--expect-reviewed-kept 461 --expect-open-questions 54`）⇒ `已審保留：461 條／丟棄：0 條`，產出與 scratch 正本 `diff -r` 相同。
  - scratch 終點指標 `已審細目 pm 457／533、prospect 105／120；頁面 pm 119／183、prospect 48／183`。
  - 紅燈基準沿用 S4 驗收時同一工作樹的全套結果（9 條，`p920-w2/red-baseline.txt`；S4 commit 後檔案內容未再變動）。預測新紅燈：scratch 正本掛到容器 `/app/canon`（正對照：容器內 D.md `reviewed` 84，repo 51）跑全套 ⇒ `9 failed, 3931 passed`，差集＝∅。
- **對 repo 執行的步驟**：備份 `rag-orchestrator/canon/` 至 `scratchpad/p920-s6-backup/` 並 `diff -r`；`git diff --stat 589e0a14 -- rag-orchestrator/canon` 與 `git status --short rag-orchestrator/canon` 皆須為空 ⇒ write ⇒ 容器重匯出 ⇒ verify `--backup p920-s6-backup` ⇒ repo 與 scratch 預跑 `diff -r` ⇒ 終點指標、全套單元差集、`make audit` ⇒ fresh outcome verifier ⇒ commit。
  - **outcome verifier 附加條件（業主 2026-10-03「好」）**：
    - **抽樣**：派工前由主 session 固定抽出，`random.Random(20261003).sample(sorted(p920-s6-approved.json), 12)`，結果存 `p920-w5/p920-s6-sample.json`，12 個 id 記入 §6「### S6」（verifier 可自行重算核對）。
    - **輸出**：verifier 對 12 條逐條列出標題與每一句，各判「成立／不成立」，附釘住匯出的檔案路徑與可 grep 字串。
    - **推翻的定義**：抽樣細目的標題或任一句，所述內容在釘住匯出 `jgb2-b2ee2ac`（及細目 sources 所列的幫助中心、帳本、裁決）中找不到支持、或有反證。只是措辭建議（P3／P4）、「沒寫到但不矛盾」不算推翻。
    - **任一條推翻** ⇒ 用 `p920-s6-backup/` 還原正本、`git diff --stat 589e0a14 -- rag-orchestrator/canon` 為空後停下交業主。
    - **驗收**：§6 記下 12 個 id 與逐條結果。
  - commit 範圍：D／E `.md`、`jgb.json`、S5 審核單、本計畫、HANDOFF（終點行與現況）；`git diff --cached --name-only` 範圍外 0。CATALOG 須與備份相同。
- **終點指標**：寫入後須為 `已審細目 pm 457／533、prospect 105／120`（pm +37、prospect +7）。

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
- **業主裁決（2026-10-03）**：「a」——對選項「(a) 上限提高到 4.2M（建議）；另設中途停點：S4 實際花費超過 0.9M 先停下交業主」。⇒ 開第二波（D／E，S4～S6）；**上限 3.5M→4.2M**；S4 單片超過 0.9M 即停。執行模式沿用 ASK。
- **業主裁決（2026-10-03，S4 中途停點）**：「a」——對選項「(a) 越過 S4 停點，跑完第二波，總上限提高到 4.5M（建議）；S5 開跑前再回報一次實際累計」。⇒ 越過 S4 中途停點 0.9M；**上限 4.2M→4.5M**；S5 開跑前回報累計。
- **業主裁決（2026-10-03，S5 開跑前回報後）**：「a」——對選項「(a) 開跑 S5，上限再放寬到 4.8M（建議）；S6 寫入前若累計超過 4.5M 再回報一次」。⇒ **上限 4.5M→4.8M**；S6 寫入前累計超過 4.5M 須先回報。

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
- **S2 第 1 輪（fresh plan-verifier）＝READY**（2026-10-01）⇒ 依業主核可開跑（ASK 模式）。
- **S3 第 1 輪（fresh plan-verifier）＝READY**（2026-10-03，審含「已預跑」與「對 repo 執行的步驟」）⇒ 依業主核可開跑。
- **S4 第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×2——(1) 計畫開頭現況仍寫「停在 S3 之前、369／533」，S4 沿用 S1 驗收的「已審 373」與自身 `--expect-reviewed-kept 424` 矛盾；(2) 「已由前案處理」沒有記錄格式，若寫成修正表列會讓 drafts_diff (a) FAIL。處置：兩項皆 **FIX**（開頭改為現值 420／98、S4 寫明不變基準 424；新增 `## 已由前案處理` 節格式並預跑正負對照）。送第 2 輪。
- **S4 第 2 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×1——「已由前案處理」由主 session 單方認定、不經核對，也沒有檢查 40 條是否全數有去處。⇒ **第二次自動 REVISE，停止重送、逐條處置**：**FIX**（已處理條目一併送 verifier 核對；新增 `coverage_check.py` 涵蓋檢查並預跑正負對照）。依規則開一次收尾審查（新的就緒期）；若再判 REVISE 就暫停交業主。
- **S4 收尾審查（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主核可開跑。
- **S5 第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×1——`p920-s5-batches.json` 為平面清單，與 `review_sheet.py` 讀的 S2 分組格式不符，第一份真 raw 就會讓 `parse` 崩潰；空結果預跑沒走到讀批次的程式路徑，所以沒擋下。處置：**FIX**（改成 S2 格式並加非空合成預跑與負對照）。送第 2 輪。
- **S5 第 2 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主核可開跑。
- **S6 第 1 輪（fresh plan-verifier）＝REVISE**（2026-10-03）：P2×1——業主附加的抽驗條件沒有寫明誰抽、怎麼抽、怎麼記，也沒定義「推翻」，CONFIRMED 無法對回業主條件。處置：**FIX**（固定種子抽樣並記入 §6、規定逐句輸出格式、定義推翻、加驗收行）。送第 2 輪。
- **S6 第 2 輪（fresh plan-verifier）＝READY**（2026-10-03）⇒ 依業主核可開跑。
- S5、S6 開工前各自再送就緒審查。

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
- **commit**：`1286d00a`（業主 2026-10-01「commit，進 S1」），範圍 13 檔，`git diff --cached --name-only` 範圍外 0。
- **成本**：S0 約 0.35M（含 jgb2 匯出與預跑、修正核對 verifier 約 0.06M、outcome verifier 約 0.2M——它重跑了全套單元與 audit）。

### S1（2026-10-01）

- **允許集合**：`p920-w1/allowed.json` 共 38 條（F 12／G 5／H 1／I 20）。
  - 兩個來源推導結果相同：舊 scratchpad 的 `p918-s2-results.json`／`p919-s2-results.json`（已複製並記 sha256 `9dab9e17…`／`d3873739…`），以及 repo 審核單 9.18 S2、9.19 S2。
  - F～I 未審 60 條全部有先審結論。
- **步驟 0**：
  - 備份 `p920-w1/backup/`（17:05:07，早於第一次 repo 編輯 17:17:36），與現況相同。
  - 紅燈基準沿用 S0 驗收時同一工作樹的結果（9 條；S0 commit 沒有改動檔案內容）。
  - 允許集合 evidence 131 筆，開工前越界 N＝0。
- **工具預跑**：
  - `edit_fine.py` 九架 roundtrip 都是 True；H 改 indent 1 的負對照 exit 1。
  - 詞表工具從 `p920-s0/` 複製；在 F 架放回「Meta Capital」的負對照 ⇒ 命中、exit 1；「系統上」6 處。
- **修正**：
  - 主 session 逐條以 grep 對釘住匯出確認 doubt 證據後改寫，ops 存 `p920-w1/ops.json`。
  - 新增 evidence 40 筆，逐字 grep 全部命中（D1 刪句時一併移除 1 筆，淨增 39 筆）；負對照為不存在的 `case 'repair_complete'` ⇒ 0。
  - 先套 scratch 副本、再套 repo，F～I 與試套逐位元組相同。
  - 修正紀錄 `inputs/fix-log-9.20-S1-FGHI-20261001.md`，共 93 列。
- **核對**：
  - fresh verifier F＋H **35／35 過**；G＋I **53／55 過**。
  - 不過的 2 項依 D1 修一次後複核：
    - `payment-icash-ctbc-setup` 句 0 過；
    - `control-panel-setting-shell` 句 1 仍不過（新寫的「可左右切換的選單列」不對）⇒ 依 D1 整句刪。這句是新增句，刪掉即回到只有句 0；標題同步拿掉「與側欄」，並移除只為該句加的 source。
  - P3／P4 建議 8 項延後到 S2 重審一併看（明細見修正紀錄「核對過程」）。
  - 核對原始結論摘要存 `p920-w1/verdict-{FH,GI,recheck}.txt`（G＋I 與複核兩份是收案後依 outcome verifier P4 補存的摘要，原文在代理 transcript）。
- **差異比對**（`ABCDEFGHI`）：(a)～(g) PASS，`(g) evidence remaps 27; new out-of-range: 0`；drafts-A～E 與備份 `cmp` 相同。
- **重生成**：
  - scratch 試跑後對 repo 跑（`--runs-out` 寫 scratch 再複製回 repo）：`已審保留：373 條／丟棄：0 條`、57 粗目／539 細目、open_questions 54 則（內文與前次相同）；repo 與試跑逐位元組相同。
  - DSP-068 刪除 26 行／30 字元：變動只在允許集合內的 3 條（repair-edit-tenant-memo 位移、pricing-free-trial-eligibility 與 pricing-free-trial-feature-scope 各新增 1 筆）。
  - `canon_check` ⇒ `blocks changed 38 (in allowed 38)`、`mismatches: 0`，客戶名 0、「系統上」6。
  - `name_scan` ⇒ 539 條、0 命中。
  - `load_canon_or_die` 通過（`canon_sha256 3f266ad6…`）。
- **終點指標 `已審細目 pm 369／533、prospect 80／120；頁面 pm 89／183、prospect 27／183`**（不變，符合 +0 預期）。
- **單元與 audit**：`9 failed, 3931 passed, 3 skipped`，紅燈集合減去基準＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（7 項全過；自行抽 20 句對釘住匯出全部成立，新增 evidence 39／39 逐字命中；自建正對照：注入「Meta Capital」「tongSang」都被抓到）。附記 P4×3（evidence 淨增數、G＋I 判定未存檔、建議條數）已更正。
- **成本**：S1 約 0.9M（主 session 查證與修正約 0.35M、verifier 核對 3 次約 0.3M、outcome verifier 約 0.25M）⇒ **9.20 累計約 1.25M**（不含立案 0.75M；第一波停點 1.8M）。

### S2（2026-10-01）

- 2 批 fresh verifier 依序跑完，一次一位，兩批都一次解析通過：
  - S2B1（F／G／H 28 條）pass 26／doubt 2；
  - S2B2（I 32 條）pass 26／doubt 6；
  - 合計 **pass 52／doubt 8**。
- raw 由 `extract_verdict.py` 從代理 transcript 機械取出，存 `p920-w1/p920-s2-raw-S2B{1,2}.txt`。
- 審核單：`inputs/review-sheet-9.20-S2-FGHI-20261001.md`，表頭 commit `46234eb0`，共 14 組，其中 ⚠️ 1 組（`I-marketing-home`：pass 1／doubt 1）。
  - `check` ⇒ `targets 60; judged 60; raw-parsed 60; sheet ids 60`、`mismatches: 0`。
  - 正對照（`jgb/I/notification-mail-settings`）：審核單副本與 raw 副本各把 doubt 改成 pass，兩者都報出不一致（`sheet<->results`、`raw<->results`）。
  - 正本與 runs 相對 `46234eb0` 的 `git status` 為空。
- **S1 修過的 38 條仍被抓出 6 條**（16%，與 9.19 的 18% 相近）：
  - `repair-apply-flow-and-entry`：入口漏了租客的「我的報修」；
  - `repair-edit-amount-visibility`：講法「怎麼填」答不到；
  - `pricing-free-trial-eligibility`：「取消不退款」是走不到的情境；
  - `control-panel-setting-shell`：S1 刪掉側欄句後，講法「控制台側邊欄」答不到；
  - `notification-mail-settings`：漏了會員側欄的「通知收件信箱」頁可以新增信箱；
  - `homepage-sections-overview`：「從特定搜尋入口」無源。
- **未修過但被抓出的 2 條**：`pricing-free-vs-experience-plan`（替待裁 #42／#43 選了 FAQ 那一邊）、`pricing-quota-full-block`（畫面上永遠不會顯示物件上限數字）。
- 修正列入下個計畫。先審附的建議另列：「另見」引用的標題已過時 3 處，另有租客例外、影片上傳等建議。
- 整理（2026-10-03）：8 條 doubt、11 條附帶建議與 S1 的 8 項 P3／P4 合併列於 `inputs/s2-findings-9.20-20261001.md`（從 raw 程式轉出，含 scratch 產物 sha256）。
- **成本**：2 批約 0.55M（S2B1 0.30M、S2B2 0.23M）；S2 就緒審查約 0.13M ⇒ **9.20 累計約 1.95M**。⚠️ **已超過第一波停點 1.8M**（業主核可「S3 完成前累計達 1.8M 也要先停」）⇒ **停下交業主**。

### S3（2026-10-03）

- **業主裁決原文**（2026-10-03，對「建議越過停點跑 S3、審核單回安全組過」的回覆）：「越過停點，跑 S3，審核單安全組過」——越過第一波停點 1.8M（上限 3.5M 內）；非 ⚠️ 13 組的 pass 標已審；⚠️ 1 組（`I-marketing-home`）全組本批不審；8 條 doubt 本批不審；無點名、無照原樣過、無排除。
- **寫入前準備**：
  - 就緒審查 READY（§5）。決定檔、derive 結果與對照見 §1 S3「已預跑」：`approved 51 (both sources equal) by shelf {'F': 19, 'G': 6, 'H': 1, 'I': 25}; expected endpoint increment pm +51, prospect +18`。
  - git 基準（`46234eb0`）與 status 皆為空；備份 `scratchpad/p920-s3-backup/`（01:00:03）以 `diff -r` 比對相同。
  - 紅燈基準 `scratchpad/p920-s3-red-baseline.txt` 共 9 條（00:55:59～00:56:57），與 §12-2 名單逐名相同。
- **寫入與驗證**：
  - `write` ⇒ `added 51`；容器重匯出與 `load_canon_or_die` 通過（539 條）。
  - verify ⇒ `reviewed backup 373 -> current 424; added lines 51; approved 51`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；`git status` 只有 F／G／H／I `.md` 與 `jgb.json` 變動，CATALOG 不變。
  - repo 正本與預跑的 scratch 正本、scratch 重生成產出（保留 424／丟棄 0）皆 `diff -r` 相同。
  - **終點指標 `已審細目 pm 420／533、prospect 98／120；頁面 pm 109／183、prospect 40／183`**（pm +51、prospect +18，與預期相同；第一波預估 pm +30～45、prospect +10～16，實際高於預估）。
  - 單元 `9 failed, 3931 passed, 3 skipped`，與基準差集＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（5 項＋正對照全過）：自行由審核單重算安全組 51 條，與 approved 差集為 ∅；`.md` diff 只有 51 行 reviewed、`jgb.json` 只有 102 個 reviewed 欄位與 `canon_sha256`（`3f266ad6…`→`b9691255…`）；終點指標與紅燈集合逐字相同。附記 P3：HANDOFF 現況先寫「S3 已 commit」，於本 commit 成立；P4：`make audit` 由主 session 實跑 PASS（verifier 依規不跑）。
- **成本**：S3 約 0.3M（主 session 預跑與執行約 0.15M、就緒審查約 0.07M、outcome verifier 約 0.1M）⇒ **9.20 累計約 2.25M**（上限 3.5M）。
- **⏸ 第一波停點**：S3 commit 後停下；第二波（D／E，S4～S6）須業主明示。

### S4（2026-10-03）

- **就緒審查**：第 1 輪 REVISE、第 2 輪 REVISE、收尾審查 READY（§5）。
- **允許集合與工具**：見 §1 S4「已預跑」。備份 `p920-w2/backup/`（01:11:25，早於第一次 repo 編輯 01:22:17）。
- **修正**：
  - 主 session 逐條對釘住匯出確認 doubt 證據後改寫，ops 存 `p920-w2/ops.json`（38 條）；新增 evidence 61 筆逐字命中，負對照 `case 'repair_complete'` ⇒ 0。
  - 先套 scratch 副本 `p920-w2/pc/`、再套 repo，D／E 與試套逐位元組相同；A～C、F～I 與備份 `cmp` 相同。
  - 修正紀錄 `inputs/fix-log-9.20-S4-DE-20261003.md`：修正表 96 列（改 90／新增句 4／刪句 2）、已由前案處理 2 條（`contract-payment-method`、`contract-rentbasic-latefee`）；`coverage_check` ⇒ `union 40`、PASS；drafts_diff (a) `log rows with no diff: 0`。
  - 內容反轉 1 條：`jgb/E/bill-tenant-unverified-draft-lock`——合約頁提示「租客未驗證時帳單停在草稿」，但現行送出路徑沒有任何驗證狀態檢查（`BillController.php` 的 `case 'send':` 只查擁有者、簽核與金額；曾經的驗證判斷只剩註解，見 `app/Services/BillService.php` 的 `email_verified_at` 兩行與 `ContractController.php` 的 `notify_tenant_status` 註解）⇒ 依業主裁決「以程式為準」改寫，並刪去以該限制為前提的句 2。畫面文案與程式不一致，屬 jgb2 缺陷候選。
- **核對**：
  - D 包 fresh verifier：69 項 **66 過／3 不過**（明細見修正紀錄「核對過程」）；已由前案處理 2 條皆過。
  - 不過 3 項依 D1 修一次（`ops-recheck-D.json`，新 evidence 4 筆逐字命中），待複核。
  - E 包（29 項）尚未核對。
- **⏸ 中途停點（業主 2026-10-03「S4 單片超過 0.9M 即停」）**：
  - S4 目前約 0.8M（估算）：代理實數——就緒審查 3 輪 0.07＋0.11＋0.06M、D 包核對 0.22M；主 session（重建工具、允許集合、40 條查證與改寫）約 0.35M。
  - 剩餘必要步驟：E 包核對約 0.1M、D 複核約 0.05M、重生成與驗收約 0.05M、outcome verifier 約 0.2M ⇒ S4 合計約 1.2M，**必然超過 0.9M** ⇒ 在送 E 包前停下交業主。
  - 現況：repo 的 drafts-D／E 已改（未 commit）；正本（canon）、runs 皆未動。回滾＝以 `p920-w2/backup/drafts/` 還原 drafts-D／E。
- **越過中途停點後（業主「a」）**：
  - E 包 fresh verifier：29 項 **CONFIRMED 29／29**（刪句 2 項確認剩下的句子成立）。
  - D 包複核（依 D1 修過一次的 3 條、4 項）：**CONFIRMED 4／4**。
  - 修正紀錄修正表 96 列全部「過」或「—」；附建議（不阻擋）列於「核對過程」，延後。
- **差異比對**（`ABCDEFGHI`）：(a)～(g) PASS（`(g) evidence remaps 33; new out-of-range: 0`）；drafts-A～C、F～I 與備份 `cmp` 相同；`coverage_check` ⇒ `union 40`、PASS。
- **重生成**：
  - scratch 試跑後對 repo 跑（`--runs-out` 寫 scratch 再複製回 repo）：`已審保留：424 條／丟棄：0 條`、57 粗目／539 細目、open_questions 54 則（扣表頭後內文與 S1 版相同）；DSP-068 刪除清單與 S1 版相同（26 行／30 字元）。repo 正本與試跑、3 個 runs 產出逐位元組相同。
  - `canon_check` ⇒ `blocks changed 38 (in allowed 38)`、`mismatches: 0`，客戶名 0、「系統上」6；A～C、F～I `.md` 與備份相同。
  - `name_scan` ⇒ 539 條、0 命中。`load_canon_or_die` 通過（`canon_sha256 fee40221…`）。
- **終點指標 `已審細目 pm 420／533、prospect 98／120；頁面 pm 109／183、prospect 40／183`**（不變，符合 +0；已審 424）。
- **單元與 audit**：`9 failed, 3931 passed, 3 skipped`，紅燈集合減去基準＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（6 項全過；自行重跑 coverage／drafts_diff／canon_check 與負對照，jgb.json 逐 id 比對已審 424 集合不變、只有 38 條允許集合內細目變動；65 筆新 evidence 逐字命中；自抽 10 句對釘住匯出全部成立；終點指標逐字相同）。附記：P4 本節「註解掉」未指明位置 ⇒ 已補上；P3 `bill-tenant-unverified-draft-lock` 只寫「合約頁」，同一提示也出現在帳單編輯頁、委託合約頁與租客名單頁 ⇒ 已列於修正紀錄延後建議，留待下一份計畫。
- **成本**：S4 約 1.3M（代理實數：就緒審查 3 輪 0.24M、修正核對 D 0.22M／E 0.16M／D 複核 0.13M、outcome verifier 約 0.15M；主 session 約 0.4M，估算）⇒ **9.20 累計約 3.55M**（上限 4.5M）。

### S5（2026-10-03）

- 2 批 fresh verifier 依序跑完，一次一位：
  - S5B1（D 34 條）：第一次交件只有 33 行、總數仍寫 34（漏 `contract-guarantor-add-after-signing`），`parse` 大聲失敗 ⇒ 依規則同一代理補審並重貼完整 34 行後收件（不完整版存 `p920-s5-raw-S5B1.first-incomplete.txt`）。結果 pass 29／doubt 5。
  - S5B2（D／E 29 條）：一次通過，pass 21／doubt 8。
  - 合計 **pass 50／doubt 13**。
- raw 由 `extract_verdict.py` 從代理 transcript 機械取出，存 `p920-w5/p920-s5-raw-S5B{1,2}.txt`。
- 審核單：`inputs/review-sheet-9.20-S5-DE-20261003.md`，表頭 commit `589e0a14`，共 12 組，其中 ⚠️ 6 組（`D-contract-edit-general` 4／2、`D-early-termination` 4／2、`D-notary` 2／1、`E-bill-list` 1／1、`E-bill-create-edit` 2／1、`E-virtual-account` 0／1；pass／doubt）。
  - `check` ⇒ `targets 63; judged 63; raw-parsed 63; sheet ids 63`、`mismatches: 0`。
  - 正對照（`jgb/D/contract-tax-invoice`）：審核單副本把 doubt 改 pass ⇒ `sheet<->results` 不一致 2；raw 副本改 pass ⇒ `raw<->results` 不一致 1。
  - 正本相對 `589e0a14` 的 `git status` 為空。
- **S4 修過的 38 條仍被抓出 8 條**（21%；9.19 18%、9.20 S2 16%）：`contract-tax-invoice`、`contract-show-panels`、`move-out-bill-generation`、`move-out-eligibility-conditions`、`contract-thinkcloud-signing-variants`、`bill-actions-received`、`bill-partial-month-proration`、`recharge-account-mismatch-and-duplicate`。其中多數是 S4 只修了 doubt 所指的句子，同一細目其他句子或講法另有問題（講法答不到 3 條）。
- **未修過但被抓出 5 條**：`contract-payment-method`（「加入常用帳號」看的是編輯團隊權限）、`social-housing-tenant-license`（所得百分位選項已被註解掉）、`contract-upload-existing-vs-electronic`（上傳上限 15MB 非 10MB）、`early-termination-reasons`（例句非逐字）、`early-termination-form-fields`（講法答不到）。
- 依「安全組過」：S6 可寫入 **37 條（pm +37、prospect +7）**；全部 pass 過則 50 條（pm +50、prospect +10）。
- **成本**：S5 約 0.86M（就緒審查 2 輪 0.18M、S5B1 0.27M、S5B2 0.31M、主 session 約 0.1M 估算）⇒ **9.20 累計約 4.4M**（上限 4.8M；S6 約 0.3M ⇒ 寫入前將超過 4.5M，依業主裁決須先回報）。

### S6（2026-10-03）

- **業主裁決原文**（2026-10-03，兩則連續回覆）：
  - 對「建議回『安全組過，跑 S6』」：「安全組過? 有派代理驗收過嗎」
  - 對「建議把抽驗 pass 併進 S6 的 outcome verifier（37 條隨機抽 12 條逐句對程式，任一條被推翻就不寫入、先交業主），累計約 4.75M 仍在上限內」：「好」
  - 解讀：非 ⚠️ 6 組的 pass 標已審（rule＝safe）；⚠️ 6 組全組本批不審；13 條 doubt 本批不審；無點名、無照原樣過、無排除。**附加條件**：S6 的 fresh outcome verifier 須自 37 條中隨機抽 12 條逐句對釘住匯出；任一條推翻 ⇒ 以備份還原正本並停下交業主（屬 §1 S3「寫入後驗收不符」的預先授權還原）。越過 4.5M 回報線，上限 4.8M 內。
- **抽樣（派工前固定）**：`random.Random(20261003).sample(sorted(p920-s6-approved.json), 12)` ⇒ `jgb/D/contract-guarantor-add-after-signing`、`jgb/D/contract-esign-no-extra-fee`、`jgb/D/social-housing-landlord-license-conditions`、`jgb/D/entrusted-contract-tabs-overview`、`jgb/D/social-housing-tenant-household`、`jgb/D/social-housing-dealer-basic`、`jgb/D/social-housing-building-detail`、`jgb/D/contract-locked-after-signing`、`jgb/D/social-housing-early-termination-difference`、`jgb/D/move-out-remains-in-active-list`、`jgb/D/social-housing-tenant-basic-status`、`jgb/E/balance-invoice-monthly-invoice-table`（重算一致）。
- **寫入前準備**：就緒審查第 1 輪 REVISE、第 2 輪 READY（§5）。git 基準（`589e0a14`）與 status 皆為空；備份 `scratchpad/p920-s6-backup/`（10:12:23）`diff -r` 相同；紅燈基準沿用 `p920-w2/red-baseline.txt`（9 條）。
- **寫入與驗證**：
  - `write` ⇒ `added 37`；容器重匯出與 `load_canon_or_die` 通過。
  - verify ⇒ `reviewed backup 424 -> current 461; added lines 37; approved 37`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`；`git status` 只有 D／E `.md` 與 `jgb.json`，CATALOG 不變。
  - repo 正本與 scratch 預跑、scratch 重生成產出（保留 461／丟棄 0）皆 `diff -r` 相同。
  - **終點指標 `已審細目 pm 457／533、prospect 105／120；頁面 pm 119／183、prospect 48／183`**（pm +37、prospect +7，與預期相同；D pm 51→84、E pm 86→90）。
  - 單元 `9 failed, 3931 passed, 3 skipped`，與基準差集＝∅；`make audit` OVERALL PASS。
- **fresh outcome verifier＝CONFIRMED**（5 項＋自建正對照全過）：
  - 自行由審核單重算安全組 37 條（D 33／E 4），與 approved 相同，與 13 條 doubt、⚠️ 組 13 條 pass 交集 0；`.md` 只多 37 行 reviewed、`jgb.json` 只動 37×2 個 reviewed 欄位與 `canon_sha256`（`fee40221…`→`7537689a…`）；終點指標逐字相同。
  - **業主抽驗條件：12／12 成立、推翻 0**（重算種子結果與 `p920-s6-sample.json` 相同）。逐條結果（標題與每句皆對釘住匯出或所列來源成立）：`social-housing-building-detail` 成立（標題＋4 句）；`social-housing-early-termination-difference` 成立（標題＋2 句）；`social-housing-landlord-license-conditions` 成立（標題＋2 句）；`social-housing-tenant-basic-status` 成立（標題＋2 句）；`social-housing-tenant-household` 成立（標題＋1 句）；`social-housing-dealer-basic` 成立（標題＋2 句）；`contract-esign-no-extra-fee` 成立（標題＋3 句）；`contract-locked-after-signing` 成立（標題＋4 句）；`contract-guarantor-add-after-signing` 成立（標題＋2 句）；`move-out-remains-in-active-list` 成立（標題＋2 句）；`entrusted-contract-tabs-overview` 成立（標題＋2 句）；`balance-invoice-monthly-invoice-table` 成立（標題＋4 句）。
  - 正對照：doubt `contract-tax-invoice`、`recharge-account-mismatch-and-duplicate` 與 ⚠️ 組 pass（`general-contract-notary-tab` 等 4 條）皆無 reviewed 行；同區核可的 `social-housing-notary` 有。
  - 附記：P3 HANDOFF「S0～S6 皆已 commit」於本 commit 成立；P4 HANDOFF 開工順序「最後一節是 S2」已改；P4 本節逐條結果已補。
- **成本**：S6 約 0.4M（就緒審查 2 輪 0.14M、outcome verifier 約 0.2M、主 session 約 0.06M，估算）⇒ **9.20 累計約 4.8M**（上限 4.8M）。

### 9.20 收案（2026-10-03）

- 終點指標：9.20 開工前 `pm 369／535、prospect 80／121` ⇒ 收案 **`pm 457／533、prospect 105／120`**（pm +88、prospect +25；分母因 S0 刪 hold 2 條各減）。
- 兩波：F～I 修 38／重審 60／核可 51；D／E 修 38（前案已處理 2）／重審 63／核可 37。
- 留給下一份計畫：S2 doubt 8 條＋S5 doubt 13 條（修後重審被抓回 6＋8 條，新抓出 2＋5 條）；⚠️ 組 pass（S2 1 條、S5 13 條）；A／B／C 9.19 留下 43 條；S2／S4／S5 附帶建議（`inputs/s2-findings-9.20-20261001.md`、`fix-log-9.20-S4-DE-20261003.md`「核對過程」）；jgb2 缺陷候選 `bill-tenant-unverified-draft-lock`（畫面提示與送出程式不一致）。
- 成本約 4.8M（不含立案 0.75M），計畫 3.5M；超出主因：S4 舊 scratchpad 清空須重建約 0.2M、修正核對與先審代理實數普遍比估算高 40～100%、就緒審查 REVISE 共 6 輪。
