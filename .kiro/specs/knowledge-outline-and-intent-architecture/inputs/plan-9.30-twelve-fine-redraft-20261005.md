<!-- plan-meta
endpoint_from: pm 537/537, prospect 121/121
endpoint_to: pm 537/537, prospect 121/121
consent_zero: 「核可，同意本計畫 +0 (Recommended)」
-->
# Plan 9.30：9.29 延後的 12 條細目整條重寫（重複者整條刪）（2026-10-05）

> **現況**（2026-10-05，HEAD `ce658bcb`）：`已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`。
>
> **本計畫的進度單位**：Plan 9.29 業主裁定「延後整條刪」的 12 條細目——**已處置 0／12 → 12／12**。每條去向四選一：
> - 整條重寫寫入；
> - 業主裁定整條刪（僅限與他條重複）；
> - 業主裁定保留；
> - 寫入核對推翻後保留原文並轉下份計畫。
>
> **已審細目數 +0**：重寫的細目在寫入前暫時失去已審，寫入後回復；整條刪除會讓分子與分母同減，例如刪 1 條 pm 細目 ⇒ pm 536／536。`consent_zero` 已填入業主 2026-10-05 核可原文（見 §6）。

## 0. 依據

- 業主 2026-10-05，AskUserQuestion 逐字：
  - 下一份計畫：「A 整條刪除＋重寫 12 條 (Recommended)」；
  - 做法：「保留 id 整條重寫，重複的才刪 (Recommended)」。
- Plan 9.29 §6：12 條清單與各自被推翻的理由。
  - 9.28 判定：`inputs/fix-list-9.29-20261004.json`；
  - 9.29 先審、3b 與寫入核對證據：`verification/*-p929-*.json`。
- 唯讀盤查（2026-10-05，主 session）：
  - `drafts_to_canon.py` 已支援細目自 drafts 消失（`reviewed-dropped` 的 `reason: fine_removed`）。
  - `drafts_diff.py` 檢查 (d) 已要求修正紀錄的「## 刪除」節，必須等於實際刪除的細目。
  - `edit_fine.py` 對「句子全刪」會拒絕，且沒有移除細目的操作。
  - 不變量 43 的 W 規則只看寫入後仍存在的已審細目；刪除的細目不需要寫入證據，改由 (d) 與 A4 機械檢查。
  - 12 個 id 在正本、drafts、runs、`.kiro`、`.agents` 以外只出現在 2 個 brief 範本的舉例裡（正對照：`jgb/A/account-registration` 被引用 32 次）。
  - 正本 `see_also` 0 條。
  - 測試與稽核沒有寫死現行細目總數：以 `git grep -P` 搜尋，正對照 `\b10\b` 命中 112 檔。

| id | 粗目 | 身分 | 現句數 | 9.29 推翻理由（摘要） |
|---|---|---|---|---|
| `jgb/E/bill-actions-progress` | 帳單列表與帳單狀態 | pm | 2 | 漏帳單編輯權限例外 |
| `jgb/E/recharge-account-vs-single-use-atm` | 固定虛擬帳號管理 | pm | 1 | 租客入口名稱非現行選單 |
| `jgb/A/signer-individual-fields` | 簽約資訊 | pm＋prospect | 5 | 必填列舉不完整、切換列不切換 |
| `jgb/B/biglandlord-list-overview` | 大房東列表 | pm | 3 | 欄位列舉不完整 |
| `jgb/B/biglandlord-sheet-overview` | 大房東對帳表 | pm | 2 | 其他團隊也看得到押金 |
| `jgb/G/power-meter-single-edit-tabs` | 電表 | pm | 4 | 漏租客例外、漏基本資料欄 |
| `jgb/A/dashboard-overview-lists` | 會員中心首頁 | pm | 1 | 漏大房東例外 |
| `jgb/B/advance-late-fee` | 進階設定 | pm＋prospect | 3 | 開關在建立合約時複製 |
| `jgb/A/forget-password-flow` | 忘記帳號、忘記密碼 | pm | 5 | 失敗彈窗不顯示原因 |
| `jgb/C/estate-rent-open-permission-and-validation` | 招租刊登 | pm | 2 | 按鈕名稱非現行介面 |
| `jgb/I/demo-form-actual-validation-scope` | 預約 demo | pm | 1 | 必填列舉漏 3 項 |
| `jgb/I/demo-form-fields` | 預約 demo | pm＋prospect | 3 | 必填列舉漏 3 項 |

## 1. 流程（一個切片 S1，一次 commit）

### 步驟（核可後）

**1. 步驟 0 基準**
- 記錄 HEAD；跑 `make audit`；記錄他線未提交檔指紋，含正對照 `runtime.py`；記錄全套 unit 紅燈基準；備份 HANDOFF。

**2. 工具**（兩份鏡像 `.claude`／`.agents` 同步，`cmp` 相同）
- `edit_fine.py` 新增兩個操作：
  - `{"remove_fine": true}`：細目必須同時在 `ALLOWED` 與 `REMOVE` 清單（環境變數 `REMOVE=<json>`）內；有其他 ops 鍵同時出現就拒絕；從 drafts 移除該細目，所屬粗目保留。
  - `{"rewrite_fine": {...}}`：整條重寫用。以新值整組取代 `title`、`sentences`、`phrasings`、`sources`、`evidence`、`not_supported_greps`、`open_questions`（避免沿用舊句的 evidence、否定 grep 與待裁殘留）；`proposed_id`、`askable`、`unit_ids`、`target_user`、`business_types`、`instance_applicability` 不得出現在 `rewrite_fine` 內（要改 ⇒ 拒絕，交業主）；evidence 的 `sentence_index` 必須落在新句子範圍內；有其他 ops 鍵同時出現就拒絕。
- `canon_check.py`：細目「順序／成員」比對改為——新正本缺席的細目若在 `REMOVE` 清單內（以 `--remove <json>` 傳入）則放行，其餘缺席、多出、順序變動照舊判錯並 exit 1；未傳 `--remove` 時行為與現行完全相同。
- 預跑（scratch）：
  - `remove_fine` 正對照：移除一條允許的細目 ⇒ `drafts_diff --fix-log` 的 (d) 相等、(a) 未記 0／多記 0、(e) 0、RESULT PASS；生成器 `reviewed-dropped` 出現 `fine_removed`；`canon_check --remove` exit 0。
  - `remove_fine` 負對照：不在 `REMOVE` 的細目 ⇒ 拒絕；`remove_fine` 混其他 ops ⇒ 拒絕。
  - `canon_check` 負對照：正本缺席的細目不在 `--remove` 清單 ⇒ exit 1；不傳 `--remove` ⇒ 與現行同樣 exit 1。
  - `rewrite_fine` 正對照：整條取代後，該細目舊 evidence／`not_supported_greps`／`open_questions` 不再出現；`drafts_diff` (b)(c)(f) PASS。負對照：`rewrite_fine` 內含 `target_user` ⇒ 拒絕；evidence `sentence_index` 越界 ⇒ 拒絕；7 個欄位缺任一 ⇒ 拒絕（不得默默清空或沿用舊值；`not_supported_greps`／`open_questions` 沒有內容時須明給空陣列）。
  - 修正紀錄正對照：scratch 套用 12 條重寫 ops 中的 11 條（留 1 條不套），重新產生修正紀錄後 `drafts_diff --fix-log` 的 (a) 未記 0／多記 0、(d) 相等、RESULT PASS；負對照：沿用 12 條版紀錄對 11 條套用的 drafts ⇒ FAIL（證明重新產生是必要步驟）。
  - `--roundtrip`：八架（A～G、I；H 除外）位元組不變。

**3. 起草**
- 由一位 executor，依 00c 規約與 9.25 新起草流程，輸出 12 條的整條新版本（同 id、同粗目）。
- 必含：
  - 標題；
  - 句子；
  - 講法 2～5 條，與全庫 NFKC 不重複，可沿用舊講法；
  - sources；
  - 每句逐字 evidence；
  - 否定句的 `not_supported_greps`（含實跑結果與正對照）；
  - `target_user` 與現行相同。若要改，須附理由並交業主。
- 輸入：
  - 細目主題（現行標題與 askable）；
  - 9.28 與 9.29 各輪推翻理由（當作已知陷阱清單）；
  - 同粗目其他細目全文（避免重複與矛盾）；
  - jgb2 釘住匯出。
- **重複判定**：起草時判斷一條是否與同粗目或全庫他條內容重複，例如預約 demo 那兩條。若重複，就不起草，改出「建議整條刪」與兩邊對照證據，交業主終審裁定。
- **輸出**：每條一份 `rewrite_fine` ops（或「建議整條刪」＋對照證據），以及逐條起草紀錄（每句依據、否定句 grep）。
- **機械檢查**（主 session，沿用 9.29 的 `check_exec.py` 並擴充）：
  - 每條欄位齊全；
  - evidence 逐字命中匯出；
  - 識別字與 `/` 路徑掃描（正負對照）；
  - 客戶名掃描：分大小寫與不分大小寫兩種，命中逐筆說明；
  - 講法 NFKC 全庫不重複；
  - 講法不得撞量尺題句（`make audit` 的 `canon_phrasing_frozen_disjoint` 會檢查，含 `ruler-9.12`／`ruler-9.13`；先在 scratch 跑一次）；
  - 套到 scratch 後 `drafts_diff` PASS（允許集合外 0 改動）。
- **修正紀錄**：`inputs/fix-log-9.30-20261005.md`，由主 session 以 `drafts_diff.py --list` 的輸出機械產生（`--doubt` 傳 12 條 id 清單、`P919_DIFF_SHELVES=ABCDEFGI`），**產生時機**：(1) 先審與複查完成後，對套用全部重寫 ops 的 scratch drafts 產生一版，供終審單引用；(2) 步驟 6.2 對 repo 只套用業主核可細目後，**重新產生**一版（刪除節＝核可刪除集合）；(3) 步驟 6.8 移出細目時，先在 drafts 還原該條，再重新產生並重跑 6.2～6.5。commit 的是最後一版。——每個改動項一列（`｜細目｜欄位｜句序｜動作｜依據｜判定｜`，格式同 `_ROW`），依據欄填起草紀錄位置；判定欄：句子與標題列取先審（或複核、整條複查）最終結論，成立＝「過」；講法、sources、其他欄位列在機械檢查全過時填「過」；核可刪除的細目同時有 `刪細目` 列（判定欄不檢查）與「## 刪除」節一行。每一版產生後都要跑 `drafts_diff --fix-log` 須 PASS。

**4. 先審**
- 由一位 fresh verifier 逐句核對全部重寫細目，混 1 條誘餌。判準同 9.29 先審，含排他列舉、漏例外、同粗目矛盾。
- 處置：
  - 不成立的句子 ⇒ 依 9.25 規則修一次 ⇒ 複核；
  - 仍不成立 ⇒ 整句刪；
  - 刪到無句或標題答不到 ⇒ 交業主（保留原文並轉下份計畫）。
- 有刪句的細目再由一位 fresh verifier 做整條複查（同 9.29 步驟 3b）。

**5. 業主終審**（一次）
- 終審單 `inputs/review-sheet-9.30-20261005.md`：逐條列新舊全文、先審結論、建議整條刪的對照證據；建議刪除的細目另列它的 `unit_ids` 是否有他條覆蓋（刪除會不會讓頁面量尺下降）。
- 業主回覆核可範圍。
- 未核可的細目：不套用、保留原文與已審。
- 「建議整條刪」須業主逐條核可才刪。

**6. 寫入**（一個 commit）
1. 組基準快照與 HEAD `diff -r` 相同。
2. 對 repo drafts 只套用業主核可的 `rewrite_fine` 與 `remove_fine`；依實際套用結果重新產生修正紀錄；`drafts_diff --fix-log inputs/fix-log-9.30-20261005.md` PASS（(a) 未記 0／多記 0、(d) 刪除集合＝業主核可的刪除集合、(e) 0）。
3. 生成器先跑 scratch 試跑，再跑 repo，兩者 `diff -r` 相同；`canon_check.py --remove <核可刪除清單>` 區塊差異只在允許集合、exit 0。
4. 建立加已審前快照（生成並容器匯出之後）。
5. `approve_write write` → 容器重匯出 `jgb.json`／`CATALOG.md` → `load_canon_or_die` 通過 → `approve_write verify --backup <加已審前快照>`（`mismatches: 0`）。
6. 檢查終點指標，H 守護 PASS。
7. 全套 unit 與基準差集為 ∅。
8. **寫入核對**：一位 fresh verifier 逐句核對全部寫入細目，`kind: write`，誘餌放 `control` 欄。
   - 推翻 ⇒ 依業主 2026-10-05 規則：被推翻的細目移出寫入集合，保留原文並轉下份計畫；其餘重寫；證據由同一位核對代理重貼。
9. `--extract` ⇒ `make audit` OVERALL PASS ⇒ commit（`Verified-by` 指向寫入證據）。

**7. 收尾**
- 一位 fresh outcome verifier（BRIEF-CONTRACT v1）對照本計畫驗收清單逐條驗收。
- 更新 HANDOFF（開頭現況、§12-1 加 9.30 列）。

### 範圍與還原
- **commit 範圍**：
  - 本計畫、驗收清單、終審單；
  - 被改動架的 drafts、runs 產出；
  - 正本被改動架的 `.md`、`CATALOG.md`、`jgb.json`；
  - `edit_fine.py`、`canon_check.py` 兩份鏡像；
  - 修正紀錄 `inputs/fix-log-9.30-20261005.md`；
  - 先審、複查、寫入證據；
  - HANDOFF。
  - ⛔ `git add -A`、⛔ `--amend`；push 由業主自跑。
- **還原**：步驟 6 開始到 commit 前任何停下 ⇒ 以組基準快照還原 `rag-orchestrator/canon` 與 `runs/outline-20260920`；`git diff HEAD` 對這兩處為空、`load_canon_or_die` 通過 ⇒ 記 §6 ⇒ 停下交業主。commit 後驗收 FAIL ⇒ ⛔ 改寫歷史，回報業主。

## 2. 不做（後續計畫）

- **9.24 以來整句刪掉的正確資訊重新起草**：清單分散在各計畫 §6；需另行彙整範圍。
- **業主抽查 30 句**：規格 §2.2，種子 `20261006`。
- **9.29 終審單附帶觀察 32 項**：帳本、幫助中心、介面文案衝突，以及其他細目疑似漏例外。本計畫只處理這 12 條；若起草時發現同粗目他條有錯，只記入觀察，⛔ 改他條。
- **招租店舖授權疑點**：另案（安全審查線）。

## 3. 業主裁決與待裁

- **已裁**：做 A；保留 id 整條重寫，重複的才刪。
- **待裁（核可時回覆）**：本計畫，並明示同意 +0。+0 的意思是：重寫細目在寫入前暫時失去已審；業主核可整條刪除時，分子與分母同減。
- **待裁（終審時）**：
  - 12 條新版本；
  - 「建議整條刪」各條（預期至少檢視預約 demo 兩條是否重複）；
  - 先審後無法成立的項目。

## 4. 停止條件與額度

- 允許集合外的 drafts 或正本有任何改動 ⇒ 停、還原。
- 先審的誘餌漏抓 ⇒ 該次先審作廢、換人一次；再漏 ⇒ 停。
- 寫入後已審細目數 ≠ 公式值 ⇒ 停、還原。公式值＝pm 537−（核可刪除中屬 pm 的條數）、prospect 121−（核可刪除中屬 prospect 的條數），分母同減。
- **額度**：
  - 預估：起草約 0.5M、先審約 0.35M、複查約 0.2M、寫入核對約 0.3M、收尾驗證約 0.2M、就緒審查約 0.15M，共約 1.7M；
  - 累計超過 2.6M ⇒ 停下回報。
- **執行模式**：沿用本線 ASK。業主終審是固定停點；停止條件觸發或完成時回報。

## 5. 就緒審查紀錄

- **第 1 輪**（fresh plan-verifier，2026-10-05）：REVISE，P2×3，**已全數 FIX**（見下方各條修法，已寫入步驟 2、3、6.2～6.5 與 commit 範圍）；另把兩項「待查」一併處理：整條重寫改用新 `rewrite_fine` 操作（整組取代 evidence、否定 grep、待裁，避免殘留）；`ruler-9.12` 經查只供 `canon_phrasing_frozen_disjoint.py` 比對講法與題句、不引用細目 id（刪除不會懸空），改在機械檢查加先跑一次；刪除對頁面量尺的影響改在終審單逐條列出：
  - B1：`canon_check.py` 遇細目缺席就 `fine order/membership differs` 並 exit 1 ⇒ 整條刪除過不了步驟 6.3。修法：步驟 2 一併改 `canon_check.py`，只放行 REMOVE 清單內的缺席；預跑加正對照（清單內刪除 exit 0）與負對照（清單外缺席 exit 1），記入 A9；commit 範圍加入此檔。
  - B2：步驟 6.5 漏了 9.29 步驟 5.4 的「容器重匯出 jgb.json＋`load_canon_or_die`」——`approve_write write` 只改 `.md`，`verify` 要讀 `jgb.json` 的 `reviewed_*`。修法：寫成 write → 重匯出 → `load_canon_or_die` → `verify --backup <加已審前快照>`。
  - B3：沒有步驟產出 `drafts_diff --fix-log` 需要的修正紀錄（(a) 每個改動都要有列、(e) 非刪除列須「過」、(d) 刪除須同時有 `刪細目` 列與「## 刪除」節）。修法：步驟 3、6.2 指定修正紀錄路徑與產生方式（由 `drafts_diff --list` 機械產生列，判定取先審／複核結論），納入 commit 範圍。
  - 待查（未列阻擋）：`inputs/ruler-9.12-*.json` 引用 `jgb/I/demo-form-actual-validation-scope`（若量尺仍在用，刪除會留下懸空 id）；`edit_fine.py` 無操作可清 `not_supported_greps`／`open_questions`，整條重寫後舊值可能殘留；刪除重複細目可能使頁面量尺下降（需查 `unit_ids`）。

- **第 2 輪（收尾審查）**（fresh plan-verifier，2026-10-05）：REVISE，P2×1（substantive）——B3-r2：修正紀錄在步驟 3（先審前、12 條全套用的 scratch）產生，步驟 6.2 卻沿用到只套業主核可細目的 repo；部分核可或 6.8 移出細目時，紀錄多出無對應改動的列，`drafts_diff.py` 的 `extra = sorted(log_rows - items)` 與 `deleted != log_deleted` 會判 FAIL，A6 無法達成。修法：先審與複查後才產生；步驟 6.2 依實際套用的核可集合以 `drafts_diff --list` 重新產生；6.8 移出細目時先在 drafts 還原該條、重新產生、重跑 6.2～6.5；預跑加「一條不套用」情境須 PASS。B1、B2、兩項待查經審查確認已關閉。另待查（P3）：計畫未寫 `drafts_diff --doubt` 與 `P919_DIFF_SHELVES`（預設 ABCI，E、G 架要放寬；設錯會大聲失敗）；`rewrite_fine` 漏給欄位時是清空還是拒絕未定。⇒ 依規則：第二次 REVISE 且為 substantive ⇒ 暫停交業主。
- **業主裁定**（2026-10-05，AskUserQuestion 逐字）：「照修法改，直接交我核可 (Recommended)」⇒ B3-r2 依修法改入步驟 3（產生時機三點）、步驟 2（「一條不套用」正負對照）、步驟 6.2（只套核可＋重新產生）；兩項 P3 待查一併寫入（`--doubt`／`P919_DIFF_SHELVES=ABCDEFGI`；`rewrite_fine` 缺欄位 ⇒ 拒絕）。**狀態：已修、未再審**（fixed, not re-reviewed），交業主核可。

## 6. 執行紀錄

- **業主核可**（2026-10-05，AskUserQuestion 逐字）：「核可，同意本計畫 +0 (Recommended)」（已填入 consent_zero；核可時狀態為「已修、未再審」）。
- **開工盤查**：`/canon-audit outline-drafting` 應讀 14 份，主 session 整檔讀完 12 份；`runs/outline-20260920/`（64 檔、2.3MB）未整檔讀，本計畫需要的 12 條全文與同粗目細目改以程式抽出；`verification/`（49 檔）由唯讀代理整檔讀過，但閱讀收據未記到。盤查開著會讓每位代理在結束時被閘門擋 3 次，業主 2026-10-05 自行執行 `audit.py end` 結束盤查（主 session 建議）。
- **步驟 0**（HEAD `ce658bcb`）：`make audit` OVERALL PASS；他線 41 檔指紋與 9.29 相同（含正對照 `runtime.py`）；另有 4 個未追蹤目錄 `.agents/skills/{answer-acceptance-verify,config-governance-review,holdout-validation,retrieval-improvement-loop}/` 非本線、不碰，16 檔指紋另存 scratch `foreign-agents-fp.txt`；HANDOFF 備份 scratch `p930/backup/` 並 `cmp` 相同；全套 unit `9 failed, 3946 passed, 3 skipped`，紅燈 9 條與 9.29 基準逐名相同（scratch `p930/red-base.txt`）；drafts 重生成基準（`--expect-reviewed-kept 543 --expect-open-questions 54`）與 repo 正本 `diff -r` 相同。
- **步驟 2 工具**：`edit_fine.py` 加 `remove_fine`／`rewrite_fine`，`canon_check.py` 加 `--remove`；兩份鏡像 `cmp` 相同。預跑（scratch）：
  - `--roundtrip` 八架（A～G、I）位元組不變。
  - `remove_fine` 正對照（移除 `jgb/I/demo-form-actual-validation-scope`）：`drafts_diff --fix-log` (a) 1 列、未記 0、多記 0，(d) 相等，(e) 0，RESULT PASS；生成器 `已審保留 542`、`reviewed-dropped` 記 `reason: fine_removed`；`canon_check --remove` exit 0。負對照：不在 REMOVE 清單 ⇒ 拒絕；混其他 ops ⇒ 拒絕。
  - `canon_check` 負對照：缺席細目不在 `--remove` 清單 ⇒ exit 1（`I: fine order/membership differs`）；不傳 `--remove` ⇒ exit 1，與 HEAD 版 `canon_check.py` 對同一輸入的結果相同。
  - `rewrite_fine` 正對照：整條取代後舊 evidence 引文、舊否定 grep 不再出現，`target_user`／`unit_ids`／`askable` 不變，`drafts_diff` (b)(c)(f) PASS。負對照：含 `target_user` ⇒ 拒絕；evidence 句序越界 ⇒ 拒絕；7 個欄位逐一缺漏 ⇒ 7 次皆拒絕；混其他 ops ⇒ 拒絕；負對照後 drafts 與基準 `cmp` 相同。
  - 修正紀錄（合成 11 條重寫＋1 條刪除）：12 條全套 ⇒ 產生紀錄 23 列，PASS；只套 11 條 ⇒ 重新產生 21 列，(a) 未記 0／多記 0、(d) 相等、RESULT PASS；沿用 12 條版紀錄對 11 條套用的 drafts ⇒ 多記 2 列、RESULT FAIL。修正紀錄產生器 scratch `p930/gen_fixlog.py`、起草機械檢查 scratch `p930/check930.py`（合成輸入預跑：引文 53 筆全命中、正對照命中；另抓到現行 `jgb/B/biglandlord-sheet-overview` 有 evidence 來源未列入 sources，證明該檢查會紅）。
  - ⚠️ 兩支工具改動在收尾 outcome verifier 驗收前屬「未驗證」。
- **步驟 3 起草**（executor 一位，約 0.67M）：輸入＝工作清單 scratch `p930/draft/worklist.md`（12 條現行全文、`verification/*.json` 機械抽出的既往推翻理由 23 筆＋9.29 寫入核對已還原紀錄 6 筆、同粗目其他細目全文）、全庫講法清單、jgb2 釘住匯出（自 9.29 scratch 以 APFS clone 複製，檔數 5882 與 `git archive b2ee2ac382ce` 相同、抽查檔 sha 相同）。結果：12 條全數重寫、建議整條刪 0（預約 demo 兩條判為不重複：一條答要填什麼、一條答系統端檢查哪些；`signer-individual-fields` 的多筆切換句整句拿掉）；交業主 9 項、跨條觀察 1 則（見終審單）。代理自陳誤建一個空目錄 `/tmp/_x` 並立即刪除，主 session 查證不存在。
  - 機械檢查 `check930.py`：12 條形狀合法；evidence 419 筆逐字命中（正對照命中）；標題／句子／講法 113 段的識別字、路徑、客戶名（分與不分大小寫）皆 0；講法 44 條 NFKC 不撞全庫 1709 條、彼此不重複；套到 scratch drafts 後 `drafts_diff` (b)(c)(f) PASS（改動項 85、涉及 12 條）。
  - scratch 重生成：`已審保留 531`（543−12）、57 粗目／543 細目、open_questions 54→56（`advance-late-fee`、`forget-password-flow` 各新增 1 則說明文字與程式衝突的待裁；`biglandlord-sheet-overview` 原 2 則逐字保留）；`canon_check` 區塊差異 12／允許 12、客戶名 0；不變量 34（講法 ∩ 凍結題句，含 `ruler-9.12`／`ruler-9.13`）交集為空；H 留出題守護 PASS（新命中 0）。
- **步驟 4 先審**（fresh verifier 一位，約 0.35M）：brief 由 scratch `p930/gen_review.py` 自 scratch 重生成正本機械產生，混 1 條誘餌（9.28 誘餌表第 8 項「社區複製流程」，位置種子 20261030）。證據 `verification/20261005-p930-prereview.json`（`--extract`，base `ce658bcb`）：13 條＝12 條＋誘餌、每條 `content_sha256`／`title_text`／句數與 scratch 正本相同；**12 條標題與全部 60 句皆「成立」**；誘餌在第 2 句判「不成立」並引來源（verdict 因誘餌為 REFUTED，屬預期）；客戶名分／不分大小寫 0。無刪句 ⇒ 不需整條複查。findings 另記 `advance-late-fee` 說明文字與程式衝突（與新增待裁同一件）。
- **修正紀錄第 1 版** `inputs/fix-log-9.30-20261005.md`（`gen_fixlog.py` 由 `drafts_diff --list` 產生，85 列、12 條、刪除 0）：`drafts_diff --fix-log` (a) 未記 0／多記 0、(d) 相等、(e) 0、RESULT PASS。
- **終審單** `inputs/review-sheet-9.30-20261005.md`：12 條新舊全文、先審結論、新增待裁 2 則、附帶觀察（疑似 jgb2 缺陷 3 項等）；客戶名掃描 0。
- **用量**：盤查代理 2 位約 0.85M（不在計畫預估內）、起草 0.67M、先審 0.35M ⇒ 累計約 1.87M（停止線 2.6M；剩寫入核對約 0.3M、收尾約 0.2M）。
- **停點**：交業主終審。
- **業主終審**（2026-10-05，AskUserQuestion 逐字）：「核可全部 12 條 (Recommended)」⇒ 寫入集合＝12 條、刪除集合＝∅。
- **步驟 6.1～6.7**：
  - 6.1 組基準快照 scratch `p930/W-base/`（HEAD `ce658bcb`）與 repo `canon`、`runs/outline-20260920` `diff -r` 相同。
  - 6.2 對 repo drafts 套 12 條 `rewrite_fine`，結果與 scratch 套用版 `diff -r` 相同；修正紀錄依實際套用重新產生（85 列、刪除 0），`drafts_diff --fix-log` (a)～(g) 全過、RESULT PASS；八架 `--roundtrip` 仍位元組不變。
  - 6.3 生成器 scratch 試跑與 repo 執行（`--expect-reviewed-kept 531 --expect-open-questions 56`、日期標 `20261005-w-930`、runs 產出寫 scratch 再複製回 repo 並 `cmp`）：repo 正本與試跑 `diff -r` 相同、runs 三檔相同；`reviewed-dropped` 12 筆皆 `content_changed`、集合＝寫入集合；`canon_check --remove`（空清單）區塊差異 12／允許 12、mismatches 0、客戶名 0。
  - 6.4 加已審前快照 scratch `p930/W-pre-approve/` `diff -r` 相同。
  - 6.5 `approve_write write`（`P918_WRITE_SHELVES=ABCEGI`、2026-10-05）added 12 → 容器重匯出 `jgb.json`／`CATALOG.md` → `load_canon_or_die` 通過 → `verify --backup W-pre-approve`：`reviewed backup 531 -> current 543`、`fines changed beyond reviewed_*: 0`、`mismatches: 0`。
  - 6.6 終點指標 `已審細目 pm 537／537、prospect 121／121；頁面 pm 177／183、prospect 82／183`（＝公式值，刪除 0）；H 留出題守護 PASS。
  - 6.7 全套 unit `9 failed, 3946 passed, 3 skipped`，紅燈與基準差集＝∅（雙向）。
- **步驟 6.8 寫入核對**（fresh verifier，約 0.32M；對照細目＝9.28 誘餌表第 13 項，結果寫 `control`）：11 條全條成立；對照細目在誘餌句（句 1）判不成立並引來源 ⇒ 量尺有效。**`jgb/B/advance-late-fee` 句 3 判不成立**：理由是延遲金帳單以 `'status' => Bill::BILL_PREPARE`（待發送）建立，非「直接送到應到帳」。
  - 主持人對碼：**反證比推翻理由強**——同一函式 `generateLateFeeBill` 在建立後有 `// 直接發送帳單至應支出/應到帳`、`$newBill->setReady(0, 'JGB系統', 0, 'JGB系統');`、`$newBill->status = Bill::BILL_READY;` 再存檔，`const BILL_READY = 2; // 狀態 2：應到帳/待繳費`；代理只看了建立當下的屬性。依紀律「反證比支持強的不列為問題、交回裁」：未自行改證據，把反證交回**同一位核對代理**重判該句並整份重貼（其餘 11 條與 control 逐字不動）；它若仍維持不成立 ⇒ 依業主 2026-10-05 規則移出寫入集合、保留原文轉下份計畫。
  - **重判結果**：同一位代理自行讀該函式後段（並追 `formatTypeStatus` 對收款方 `BILL_READY` ＝ `'unreceived'` 應到帳）後改判句 3 成立，承認「上次只讀到建立段落」；其餘 11 條與 control 逐字未動。證據 `verification/20261005-p930-write.json`（`--extract` 取最後一份，base `ce658bcb`）：**CONFIRMED**、12 條＝寫入集合、每條 `content_sha256`／`title_text`／句數與工作樹正本相同、全條成立；control `jgb/D/notary-agree-option` 誘餌句判不成立；客戶名分／不分大小寫 0。`outline_plan_discipline.py`（不變量 43，含工作樹 W）PASS。代理 findings 另記：建立段落的行內註解「狀態 2」與當下常數值 1 不符，易誤導（jgb2 程式註解問題，不改）。
- **A1 去向對帳**：12 條＝整條重寫寫入 12、業主裁定整條刪 0、業主裁定保留 0、寫入核對推翻後保留原文 0。
- **A8 客戶名掃描**（詞表＝`canon_check.py` 的 `PAT`；正對照合成客戶名命中、負對照「系統上」不中）：
  - 分大小寫：計畫、驗收清單、終審單、修正紀錄、先審與寫入證據 0；正本 `jgb.json`、`jgb/*.md`、`CATALOG.md` 0；HANDOFF 2——與開工前備份逐字相同（既有內容，本計畫未新增）。
  - 不分大小寫：上述 `.kiro` 新檔 0；正本 0；**drafts 改動細目 12 筆**，全部位於 `evidence` 的逐字引文與 `not_supported_greps` 指令／結果（`advance-late-fee` 3 筆、`bill-actions-progress` 3 筆、`estate-rent-open-permission-and-validation` 6 筆），內容是 jgb2 原始碼裡特定合作團隊的權限方法名與欄位鍵（00c 規定 evidence 須逐字引程式、識別字只准出現在 evidence），標題／句子／講法 0。**說明**：base `ce658bcb` 的已 commit drafts 已含同兩個字根（不分大小寫）共 40 處（`git grep -ic`：一個字根 A 1／B 5／D 11，另一個 B 13／D 5／E 2／I 3），本計畫未新增可對外理解的客戶資訊；對話時會被引用的正本 0。
- **用量**：盤查代理 2 位約 0.85M、起草 0.67M、先審 0.35M、寫入核對 0.33M（含重判）⇒ 累計約 2.2M（停止線 2.6M；收尾驗證約 0.2M）。
