# Plan 9.15：讓已審細目開始增加（終點指標上板＋D／E 兩架起草與交審）

> 狀態：**業主 2026-09-27 核可**（接受 S3b 修法、不再審大綱；先做 S1；D1＝逐架交審；S1 規則措辭照原文）。ASK 模式。
> **終點指標（本計畫起點，可重跑）**：已審細目 **0／515**（pm 0／509、prospect 0／112）；頁面樹 183 頁中有已審細目的 **0**。
> **本計畫預期**：S1＝0（工具，業主 2026-09-26「A，照建議」已明示同意）；S4 完成時 D＋E 兩架最多 **+174**（D 97＋E 77，以業主審過為準）。
> 上游：HANDOFF §1 終點；Plan 9.14 §10（64 條對源事實、37 格部分缺口、51 則業主題）；記憶 `feedback_endpoint_metric_first`。

## 0. 為什麼有這份

- 9.11～9.14 連四份是量測／診斷，已審細目始終 0；業主 2026-09-26：「所以都在幹嘛」「你很容易失焦」。
- 結構性原因（本次盤查才看到）：
  - 細目**沒有任何「已審」標記**：`reviewed_by` 在 `rag-orchestrator/canon/jgb/*.md` 0 處（正對照：同目錄 `- target_user` 515 處＝細目數）。`canon_visible` 以 `reviewed_by is not None` 為門 ⇒ **兩身分目前可引用的正本細目＝0**。
  - DSP-066 規定「補完基準缺口後**一次**交審」⇒ 照規則，終點指標在最後一刻之前永遠是 0，漂移看不見。

## 1. 終點指標的定義（S1 要落成腳本）

- **M1（主指標，決定性）**：`reviewed_by` 非空、且 `target_user` 含該身分的細目數／該身分細目數；逐架（A～I）列。
- **M2（覆蓋，代理指標）**：頁面樹 `inputs/page-surface-20260919.json` 中 `in_baseline` 的 183 頁，有幾頁至少被一條「已審且含該身分」的細目的 `sources`（`code:<path>`）指到該頁元件。
  - **比對規則**：SPA 頁（`kind=spa`）⇔ 細目 `sources` 含 `code:src/pages/<component>`（逐字相等）；blade 頁（`kind=blade`，`component`＝`Controller@method`）⇔ `sources` 含 `code:app/Http/Controllers/(<子目錄>/)*<Controller>.php`（控制器檔層級，不到方法）。
  - ⚠️ 這是路徑比對的近似，⛔ 不得當「覆蓋完成」的判準，只看趨勢。**正對照**：關掉「已審」過濾，現樹用上列規則須得 **132／183**（SPA 114、blade 18；2026-09-26 主 session 實跑）。舊稿寫的 116 是另一個臨時規則（子字串雙向比對）的結果，作廢。
- 輸出第一行固定：`已審細目 pm X／509、prospect Y／112；頁面 pm A／183、prospect B／183`。

## 2. 切片

### S1 — 終點指標上板＋plan-verifier 加「終點推進」檢查（預期終點 +0；業主已同意）

- **做**：
  1. 新腳本 `.claude/skills/outline-curation/scripts/endpoint_progress.py`（`.agents/` 鏡像同步、`cmp` 相同）：讀 `rag-orchestrator/canon/jgb/*.md`（用既有 `canon_items.parse_canon_auto`，⛔ 不另寫解析）與 page-surface，印 §1 格式；`--json` 輸出供 HANDOFF 貼用。
     - 前置條件拿不到（正本或 page-surface 不存在、細目數 0）⇒ 非 0 退出並印原因；自帶正對照（細目總數必須 >0，且等於 `^### .*{#jgb/` 標題數）。
     - 執行環境：`parse_canon_auto` 需容器依賴（主機缺 `psycopg2`）⇒ 以 `docker compose -f docker-compose.dev.yml run --rm -T --no-deps rag-orchestrator python3 /.claude/skills/outline-curation/scripts/endpoint_progress.py …` 跑（同 Plan 9.14 步 5）。2026-09-26 同法實測：細目 515、pm 509、prospect 112、`reviewed_by` 非空 0。
  2. 單元測試 `rag-orchestrator/tests/unit/skills/outline_curation/test_endpoint_progress_req.py`：合成正本（2 條已審／1 條未審、兩身分混合）⇒ M1 計數正確；正本空 ⇒ 非 0；`reviewed_by` 空字串視同未審；**M2**：一條已審細目的 `sources` 各命中一個 SPA 頁與一個 blade 頁 ⇒ 2，未審細目命中 ⇒ 不計。腳本提供 `--ignore-review`（關掉已審過濾，只供正對照）。
  3. 全域 `~/.claude/agents/plan-verifier.md` 加一條（業主 2026-09-26 選 A）：
     > Plan envelope/slice must state which program endpoint metric it advances and the expected change (with the metric's current value). An expected change of 0 is allowed only if (a) the unit is a stated prerequisite of a named slice in the same Plan whose expected change is positive, or (b) the Plan records a stated reason and explicit owner consent for the 0. Otherwise REVISE (P2).
     - 改前備份到 session scratchpad；只加這一段，其餘逐字不動
  4. HANDOFF 開頭「一句話現況」改成：第一行貼 `endpoint_progress.py` 輸出，再接現況。
- **不做**：改正本、改 `canon_visible`、改 DSP-066（見 §3 D1）。
- **驗收**：
  - 現樹實跑輸出 `已審細目 pm 0／509、prospect 0／112；頁面 pm 0／183、prospect 0／183`
  - 現樹 `--ignore-review` 實跑，不分身分的頁面數＝132／183（§1 正對照；另印兩身分各自數字供記錄）；不等 ⇒ 停
  - 新測試全綠；既有 outline_curation 測試不新增紅燈
  - 鏡像 `cmp` 相同
  - `plan-verifier.md` diff 只有新增的那一段（備份比對）
  - **正對照**（同一條規則文字下判）：S2 原文（+0，且寫明是 S4〔+最多 174〕的前置 ⇒ 合 (a)）送 fresh plan-verifier ⇒ 不因終點規則 REVISE；同一份 S2 刪掉標題的「預期終點」與前置說明後的副本 ⇒ 必須 REVISE 並指出缺終點指標
- **回滾**：刪新腳本與測試、鏡像同步；`plan-verifier.md` 以備份還原；HANDOFF 還原該段。
- **預算**：主 session 直接做（小、單一路徑）；plan-verifier 正對照 2 次（約 0.1M token）。
- **停止**：`parse_canon_auto` 讀出的細目數 ≠ 515；plan-verifier 正對照不 REVISE。

### S2 — D／E 相關的業主題裁決（預期終點 +0；是 S3 與 S4〔預期 +最多 174〕的前置）

- 來源：`.claude/skills/outline-curation/runs/outline-20260920/open-questions-20260923.md`（1～81 原待裁＋82～132 Plan 9.14 追加）。
- **選題規則（可重跑）**：每則開頭的 id 以 `jgb/D/`、`jgb/E/`、`D-`、`E-` 開頭者（`grep -E '^[0-9]+\. \`(jgb/)?[DE][-/]'`，2026-09-27＝61 則）＋「未歸粗目」中主題屬 D／E 者：93（虛擬帳號重發⇒E）、123（承租人編碼異動、封存重建合約⇒D）；92（客服紙本申請書，跨架內部作業）不收、理由記在審核單。合計 **63 則**。
- **產出（S2 獨佔，主 session 唯一寫者）**：`inputs/review-sheet-9.15-S2-DE-20260927.md`；業主以組裁決時，主 session 逐則展開寫進該檔「裁決紀錄」節（每則：編號、採用／改寫／不寫、日期）。S3 只從這一節讀裁決。
- **業主工作**：只裁 D／E 這批；其餘架不用等。
- 不做：不改正本、drafts、DECISIONS；只寫審核單。
- 驗收：裁決紀錄的編號集合＝選題規則產出的 63 個編號，每則恰一個裁決。
- 回滾：刪除審核單。
- 停止：選題有歸架爭議、或業主未裁的編號 ⇒ 列給業主，⛔ 不帶進 S3。

### S3 — D／E 起草＋一次重跑生成（預期終點 +0；是 S4〔預期 +最多 174〕的前置）

- 材料：帳本 `#p914` 中 D／E 的事實、Plan 9.14 桶② D／E 的部分缺口、S2 裁決。
- 同次修不變量 34（刪 `drafts-D.json` 那條講法），DSP-070 的封存步驟先改掉；重跑一次生成，換 `canon_sha256`、同步釘 sha 的測試。
- 驗收：`make audit` 綠；新細目每句可對源（00c 逐句對源）。

**S3 細部（2026-09-27，盤查 `outline-drafting` 10／10 已讀）**
- **現況（可重跑）**：`drafts-D.json` 10 粗目／97 細目／246 句、帶 `open_questions` 16 條；`drafts-E.json` 7／77／231、帶 11 條；不變量 34 的講法在 `jgb/D/contract-rentbasic-template-and-dates` `phrasings[3]`；帳本 `#p914` 的「合約」「帳單、收款與發票」兩節共 37 條。
- ⚠️ 盤查更正：
  - `drafts_to_canon.py` **已無封存步驟**（`grep -n "archive\|shutil\|move" drafts_to_canon.py` 0 命中；S5 已移除）⇒「DSP-070 封存步驟先改掉」一項作廢。
  - `generate` 會**覆寫** `runs/outline-20260920/open-questions-<日期>.md` ⇒ ⛔ 不得沿用 `--date 20260923`（會抹掉 9.14 追加的 82～132）；本片用 `--date 20260927`，新檔只含 drafts 內剩餘的 `open_questions`。
- **範圍收窄（交業主知悉）**：Plan 9.14 桶②（37 格部分缺口）的「缺什麼」只存在 repo 外判者輸出（可能夾客戶措辭）⇒ **不併入本片**，另案。
- **已知破壞（不做，擁有者＝Plan 9.16）**：凍結量尺 `ruler-9.12-questions.json`（sha 釘在 samples-manifest，⛔ 不改）有 3／337 題的 gold 是被刪的 `bill-sheet-*` 細目；`ruler_eval.py --remap` 只能「舊 id→新 id」、無法剔題 ⇒ S3 後對新正本跑 ruler-9.12 會以 `RulerError` 大聲失敗。修法（9.16）：`ruler_eval` 重映支援「剔除並列入報告」，或把這 3 題重映到存活細目並寫明理由。9.15 期間不跑 ruler-9.12。
- **步驟**：
  1. 主 session（機械）：刪不變量 34 那條講法；G3 裁「財務報表頁不列入大綱」⇒ 刪 `unit_ids` 含 `page:bills.sheet` 的**全部 4 條**細目：`jgb/E/bill-sheet-report-title`、`bill-sheet-two-views`、`bill-sheet-total-cards`、`bill-sheet-download-button`（E 77→73；S4 上限改為 D 97＋E 73＋本片新增數）。
  2. 起草（`executor`，**D 一位、完成後 E 一位，序列**；brief 附 00c 規約、S2 裁決紀錄、帳本 D／E 條目、jgb2 釘住匯出 `$J`）：
     - 依 S2 裁決改寫帶 `open_questions` 的 27 條細目，改完清空該細目 `open_questions`（G2 查不到者照實寫「未提供」並留一條 `open_questions`）
     - 帳本 37 條 D／E 事實：能併入既有細目者補句，否則新增細目（`proposed_id` 依 00c 形狀、歸入既有粗目，⛔ 新增粗目）
     - 9.14 業主題 G6～G9 屬 D／E 者：依裁決補句（客服協助／無公開時程／外部規定／只寫系統行為）
     - 每句附來源（`sources`：`code:`／`help:`／`docs:knowledge/jgb-product-facts.md#<anchor>`），⛔ 客戶措辭
     - **業主裁決句**（G5「請洽客服」、G6「此操作需由 JGB 客服協助」、G7「目前沒有公開時程」、G8「屬外部規定，系統不判斷」、32 的簽章費口徑）：來源寫 `docs:.kiro/specs/knowledge-outline-and-intent-architecture/inputs/review-sheet-9.15-S2-DE-20260927.md#<裁決編號>`；verifier 對這類句**以該編號的裁決文字判定**（句意須與裁決一致、⛔ 超出裁決），不對程式判定。審核單不改（S2 已定稿）。
     - executor 另交一張對照表：63 個裁決編號 → 落到哪些細目 id（或「不寫」＝G3／G4），以及 G2 查不到而保留 `open_questions` 的細目清單
     - 只准改 `drafts-D.json`／`drafts-E.json`
  3. 每架起草完 ⇒ fresh `verifier` 對**全部變動句與新增句**逐句對源（依 00c：⛔ 抽樣；無來源或矛盾 >10% 即 REFUTED）＋00c 形狀檢查；verifier 報告須列「已核句數」，須等於主 session 由 drafts 改前改後 diff 算出的變動＋新增句數；REFUTED ⇒ 同一 executor 修一次，仍 REFUTED ⇒ 停交業主
  4. 生成：`drafts_to_canon.py generate … --date 20260927 --expect-open-questions N`（容器；`--front-matter-from` 為現行 `canon/jgb`；N＝其餘七架 drafts 現有 `open_questions` 數＋executor 回報的 D／E 保留數）
  5. 同步釘 sha 的測試（`grep -rln canon_sha256 rag-orchestrator/tests`）與條數斷言
- **驗收**：
  - 其餘七架 `A B C F G H I.md` 與生成前**逐位元組相同**（`cmp`）
  - `grep -c 'page:bills.sheet\|bills/sheet/Index.vue' rag-orchestrator/canon/jgb/E.md`＝0（正對照：同檔 `bills/list/Index.jsx` ≥1）
  - 全部變動句＋新增句皆經 verifier 逐句判定，已核句數＝diff 算出之數
  - 不變量 34 綠、`make audit` 綠
  - 全套單元紅燈＝HANDOFF §4 既有 9 條，無名單外
  - `endpoint_progress.py` 重跑：已審仍 0（S3 不標審）；D／E 細目數＝97＋新增 D、73＋新增 E，與起草回報相符
  - **裁決落地**：對照表 63 列、編號集合＝審核單裁決紀錄；每列指到的細目 id 在生成後正本中存在（或為「不寫」）；主 session 抽 10 列對讀細目內容與裁決一致
  - `generate --expect-open-questions N` 通過；`open-questions-20260927.md` 中 D／E 項＝executor 回報的 G2 查無清單
  - 兩位架 verifier 皆 CONFIRMED
- **回滾**：改前把兩份 drafts、`rag-orchestrator/canon/`（含 `jgb.json`）與要改的測試備份到 session scratchpad `p915-s3-backup/`，以備份還原；刪新 `open-questions-20260927.md`（⛔ 不用 `git checkout`）
- **預算**：起草 2 位＋verifier 2 位，合計 ≤2M（§5 總 5M 之內）；一次一位
- **停止**：七架任一位元組變動；新增粗目；任何句無來源；verifier 二次 REFUTED

### S3b — 「注入已審標記」的測試輔助與量測工具改成可重入（預期終點 +0；是 S4〔預期 +最多 174〕的前置）

- 問題（大綱收尾審查指出、主 session 已重現）：多支測試輔助與 `tools/canon/ruler_eval.py` 會對**每個**細目標題無條件附加 `- reviewed: {by: …}`；S4 讓 D／E 帶真的 `reviewed` 後，這些地方會觸發 `canon_parser` 的 `屬性重複 'reviewed'`；`test_library_view_req.py::test_real_views_fit_the_budget` 另有「全未審 ⇒ 0」與 `== 1` 的前提。
- **擁有**（清單以 `grep -ln -- "- reviewed: {by:" rag-orchestrator/tests/unit/agent/*.py rag-orchestrator/tools/canon/ruler_eval.py` 為準，2026-09-26 命中 10 支測試＋`ruler_eval.py`）：各注入輔助改成「已有 `reviewed` 的細目跳過」；`test_real_views_fit_the_budget` 與 `_single_reviewed_canon_copy` 改成以「現樹已審集合」為基準，⛔ 寫死全未審。
- 驗收：在暫存的正本副本上**預先把一條 D 細目標成已審**，上列輔助與 `ruler_eval` 的已審副本全部載入不報錯；全套單元測試紅燈數不增加；此檢查記在本計畫 §6，且須在 S4 開始前成立。
- 回滾：還原上列檔案。

### S4 — D／E 代理先審＋業主終審 ⇒ 標 `reviewed_by`（**預期終點 +最多 174**）

- **前置**：§3 D1 業主核可，且主 session 已把 DSP-066 修訂寫進 `.claude/DECISIONS.md`（見 §3 D1 的執行步驟）；S3b 驗收成立；未滿足 ⇒ S4 不開。
- 代理先審（逐句對源＋可答性，DSP-066），產審核單；業主終審；審過的細目在 `D.md`／`E.md` 加一行 `- reviewed: {by: owner, at: YYYY-MM-DD}`（`canon_parser.py` 的 `reviewed` 屬性格式）。
- **本片擁有**（改動只限這些）：
  - `rag-orchestrator/canon/jgb/D.md`、`E.md`：只准新增 `reviewed` 屬性行（diff 檢查：新增行全符合 `^- reviewed: \{by: .+, at: \d{4}-\d{2}-\d{2}\}$`、刪除行 0）
  - `rag-orchestrator/canon/jgb.json`：只准以 `export_json` **整份重匯出**（`load_canon_or_die` 逐位元組比對，⛔ 手改單一欄位）；允許的 diff＝`canon_sha256`＋業主通過之 D／E 細目的 `reviewed_by`／`reviewed_at` 值，其餘任何變動 ⇒ 停；`CATALOG.md` ⛔ 變動
  - 釘該 sha 的測試（`grep -rln canon_sha256 rag-orchestrator/tests` 列出者）同步改新值
  - 兩條「全未審」現況斷言改成「已審集合＝業主通過集合」：`tests/unit/agent/test_library_view_req.py`、`tests/unit/agent/test_canon_assembler_req.py` 的 `assert reviewed == []`
- 驗收：`endpoint_progress.py` 的 D、E 兩架已審數＝業主通過數；`canon_visible` 對這些細目回真；上列測試全綠；`make audit` 綠。

## 3. ⏳ 待業主裁

- **D1（決定性）**：DSP-066「補完基準缺口後一次交審」改成「**逐架交審，D／E 先**」？
  - 建議改：不改的話 S4 要等九架全補完，終點指標會繼續 0 很久，失焦看不見。
  - 代價：已審的 D／E 細目先進模型，其他架仍 0；跨架引用（如 E 引 D）可能暫時缺一半。
  - **代價（重跑會抹掉已審標記）**：生成器 `drafts_to_canon.py` 每次整架以 `"w"` 重寫九架、全檔無 `reviewed` 處理（grep 0；同檔 `shelf` 35 ⇒ 搜尋有效）⇒ S4 之後任何一次重跑都會靜默清掉業主審過的標記。DSP-066「一次交審」原本正是靠「最後才審」避開這件事。
    - 處置：S4 之後的任何重跑，**前置**＝生成器能保留既有 `reviewed` 行（或只重寫沒有已審細目的架）；擁有者＝下一份計畫（9.16）的第一片，⛔ 未完成前不得重跑。本計畫內 S3 的重跑發生在 S4 之前，不受影響。
  - **執行步驟**：業主核可後，主 session 在 S2 開始前把 DSP-066 的「交審批次」改寫為逐架交審（標業主日期與原話），這是 S4 的前置。
  - **否決或未裁的分支**：S2、S3 照做（它們本來就是補缺口，交審方式不影響）；S4 不開；本計畫預期終點變化改為 **+0**，S3 完成後停下交業主。
- **D2**：S1 的全域 `plan-verifier` 規則措辭（上面那段英文）可否。

## 4. 不做

- 其他七架（下一份計畫）；題意不明 14 題；9.11 commit；部署。

## 5. 停止條件（全片共用）

- 任一片的實際終點變化與預期不符且無法解釋 ⇒ 停下交業主。
- 正本 sha 只准在 S3（重跑生成）與 S4（只新增 `reviewed` 行＋`jgb.json` 整份重匯出，diff 限 S4 所列）變動；其他片或超出允許 diff 的變動 ⇒ 停。
- **已審細目數（M1）任何時候下降 ⇒ 停下交業主**（防重跑抹掉標記）。
- **預算**：S2～S4 合計 `subagent_tokens` ≤ **5M**（S3 生成＋逐句對源約 2M、S4 代理先審 174 條約 2M、fresh verifier 預留 1M；估法：Plan 9.14 對源約 1.5 萬 token／格）；本機 8GB ⇒ **一次只跑一個代理、⛔ 多判者並行**。記在 `cost.json` 式帳本；累計達 4M 先停交業主看剩餘工作量，超過 5M ⇒ 停。
- D1 被否決或未裁 ⇒ 依 §3 D1 分支：S4 不開、S3 後停。

## 6. 就緒審查紀錄

- 大綱第 1 輪（fresh plan-verifier，2026-09-26）＝REVISE P2×3，全 FIX：
  - §5 的 sha 停止條件會擋掉唯一推進終點的 S4 ⇒ 允許 S4 只新增 `reviewed` 行，S4 擁有 sha 重釘與兩條「全未審」斷言
  - D1 無擁有者、無否決分支 ⇒ 寫明主 session 在 S2 前改 DSP-066、否決時 S4 不開且預期改 +0
  - 大綱無總預算 ⇒ S2～S4 ≤5M、單代理序列、4M 先停
- 大綱第 2 輪＝REVISE P2×3（主 session 皆已重現）；已達第 2 次 ⇒ 停止自動重送，主 session 逐條裁決**全 FIX**，開新就緒週期、只送一次收尾審查：
  - `jgb.json` 逐位元組比對、含每條 `reviewed_by`／`reviewed_at`（`grep -c reviewed` 1030＝515×2）⇒ S4 改為整份 `export_json` 重匯出、diff 限定、`CATALOG.md` 不動
  - 生成器不保留 `reviewed`（grep 0）⇒ D1 代價寫明；S4 後重跑的前置歸 9.16 第一片；§5 加「已審數下降 ⇒ 停」
  - 新規則會擋自己的 S2／S3 ⇒ 規則改為允許「同計畫內正推進片的前置」；S1 正對照改用 S2 合規原文 vs 刪終點行副本
- **大綱收尾審查＝REVISE P2×1**（S4 真的標已審後，10 支測試輔助＋`ruler_eval.py` 無條件注入 `reviewed` 會觸發 `屬性重複`；主 session 以 grep 重現）⇒ 主 session 處置 FIX：新增前置片 S3b。⚠️ 依規則收尾審查不再開下一輪 ⇒ **暫停，交業主決定**。
- **業主裁（2026-09-27）**：「核可，先做 S1」（接受 S3b、不再審大綱）；D1「改成逐架交審」⇒ 主 session 已改寫 `.claude/DECISIONS.md` DSP-066（S4 前置之一已滿足）；S1 規則措辭「可以」。
- **S1 完成（2026-09-27，終點 +0，業主已同意）**：
  - `endpoint_progress.py`（`.agents` 鏡像 `cmp` 相同）現樹實跑：`已審細目 pm 0／509、prospect 0／112；頁面 pm 0／183、prospect 0／183`；`--ignore-review` 不分身分 **132／183**（pm 132、prospect 43）＝§1 正對照 ✓
  - 新測試 5 條全綠；`tests/unit/skills/outline_curation/` 242 條中紅 6 條＝HANDOFF §4 既有名單（`test_canon_to_library_req` 五條＋`test_fine_without_sources_blocks_exit`），無名單外紅
  - `~/.claude/agents/plan-verifier.md`：diff 只有新增那一段（備份 `scratchpad/plan-verifier.md.bak`，原 sha `d3998a3e25c05c94`）
  - **規則正對照（同一條規則文字、兩位 fresh plan-verifier）**：S2 合規原文 ⇒ 審查者明寫「S2 states which endpoint metric…meets the endpoint rule」，未因終點規則退件；刪掉終點行的副本 ⇒ REVISE 第一條即「S2 doesn't say which endpoint metric…」並引 `plan-verifier.md:13` ✓。證實同一 session 新派的審查者已讀到新規則
  - 兩位審查者另指出 S2 本身缺來源路徑、選題規則、題數、產出檔與範圍／回滾／停止（皆 P2，含漏收的 93）⇒ FIX：S2 補齊（63 則）、審查單加 93／123 與「裁決紀錄」節
  - HANDOFF 開頭改為貼 `endpoint_progress.py` 輸出
  - **例外 (b) 正對照**（業主追問後補測）：S1 帶業主同意紀錄 ⇒ READY；刪掉所有同意紀錄的副本 ⇒ REVISE 第一條即「S1 expects 0…neither allowed exception holds」✓（第二條「基準已含規則」是副本刪了完成紀錄造成的假象，非缺陷）
  - **fresh verifier＝CONFIRMED**（業主追問「有派代理驗證嗎」後補派；主 session 原本漏派，S1 動全域設定屬風險片）：V1 鏡像、V2 數字（另寫不 import 的驗算得同值 515／509／112／132）、V3 測試（3 份故意改壞的副本皆被抓到）、V4 diff 只多一段、V5 HANDOFF
  - DEFER（P4）：計畫寫的「正本空 ⇒ 非 0」未有對應測試（實際由 parser `缺架 A.md` 報錯 exit 1，行為正確）；合成正本已審條數與計畫措辭不同（行為無缺口）
- **S2 完成（2026-09-27，終點 +0，S3／S4 前置）**：業主「全部照建議」；主 session 逐則展開寫入審核單「裁決紀錄」節 63 則（47 題業主未提供數字 ⇒ 改寫為「請洽客服」）；驗收：選題規則重跑的編號集合＝裁決紀錄編號集合（63）✓。
- **S3 第 1 輪＝REVISE P2×3**（皆重現、全 FIX）：G3 漏刪 `bill-sheet-total-cards`（同頁 4 條）⇒ 全刪、E 77→73＋grep 驗收；抽樣對源違反 00c「⛔ 抽樣」⇒ 改全數、核句數對 diff；刪細目使 ruler-9.12 3／337 題 gold 消失 ⇒ 記為已知破壞、擁有者 9.16、9.15 期間不跑 9.12。
- **S3 收尾審查＝READY（2026-09-27）⇒ 開工**：
  - 備份 `scratchpad/p915-s3-backup/`（drafts-D／E、`rag-orchestrator/canon/` 全份）
  - 步驟 1 完成：D `jgb/D/contract-rentbasic-template-and-dates` 刪講法「合約範本有哪幾種」（4→3 條）；E 刪 `page:bills.sheet` 4 條細目（77→73），並把粗目「帳單統計與報表」的 `unit_ids` 去掉 `page:bills.sheet`（計畫未明寫、屬同一裁決的一致性處理，記錄於此）；JSON 保原格式（indent 1；D 有結尾換行、E 無）
  - 步驟 2：D 架 executor 交件：97→104 細目（新增 7、改 32 條）、變動＋新增 58 句；裁決 28 則全對上存在的細目；保留 open_questions 1 條（31）。executor 被 `make audit`（不變量 34，要等步驟 4 重生成）的 Stop 閘門卡住 ⇒ 主 session 停掉（交件已完整）
  - 步驟 3：D 架 fresh verifier＝**REFUTED**（58 句：46 支持／9 矛盾／3 無源或非事實＝20.7%）。主 session 重現 F1（合約總表走 `webList` 不是 `index()`）、F2（GTB 範本有正式標籤）、F5（「新增代理人」只在社宅合約）⇒ 退回同一 executor 修一次
  - D 架 executor 修一次後：104 細目、60 句待核、open_questions 清空；**fresh verifier 第 2 次＝REFUTED**（51 支持／6 矛盾／3 無源＝15%）：齒輪選單 s4／s7／s8 仍有誤（租客提前解約先查未繳帳單再開視窗；提前解約中實際渲染兩個點交＝程式缺陷；刪續約合約權限不含大房東）、GTB 英文版實際被註解掉且 s3／s4 仍用「GTB」、出租人資訊代租代管其實可逐份設定（超出裁決 100）、「是否通知」不在合約總表；另 3 句缺源 ⇒ **依 S3 停止條件停下交業主**
  - **業主裁（2026-09-27）**：「主 session 親修＋再驗一次」（仍不過就整句刪）；E 架「分小批＋先驗再交」
  - 主 session 依第 2 次發現親修 9 句（改寫 6、刪 3，含 evidence 索引同步）⇒ **fresh verifier 第 3 次**：59 句中矛盾 3（5.1%，未超門檻）＋1 句含特定客戶名 ⇒ REFUTED（只因「⛔ 客戶名稱」）；依業主裁**整句刪 3 句**（齒輪選單 #4、#7，租金費用「第四台」句）；客戶名那句內容經驗證成立、且標題也含同名 ⇒ 依 00c「特定合作團隊」改寫名稱（未刪內容）
  - D 架定稿：104 細目、open_questions 0。⚠️ 另有 5 條**原有**細目（9.10 起草、不在本片變動範圍）含「新北住都」；它同時是使用者可見的合約範本名稱，是否算客戶名待業主於 S4 審核時裁
  - E1（前三粗目）executor 交件：73→85 細目、25 句；裁決 10 則全落地（110 判「不寫」合 G9）；fresh verifier **REFUTED**（5 矛盾＋1 違規：批次動作「開立發票」有功能旗標、催繳是固定排程非合約天數、電費度數排定／發送時會補空值、合約結束帳單停在待發送、封存順序否定句無 grep）⇒ 比照 D 架由主 session 親修＋再驗一次；**連帶更正帳本 `p914-power-reading-draft`**（同根因）
  - E1 主 session 親修後 **fresh verifier 第 2 次＝REFUTED**（3／25：發票時機兩句寫成絕對、電費度數「發送時補抓」過頭）⇒ 依業主裁**整句刪**；`jgb/E/bill-invoice-issue-timing` 兩句全刪、整條細目移除（E1 新增 12→11）；E 架 84 條、`coarses[3..6]` 未動。同根因再更正帳本 `p914-power-reading-draft`（限排定發送）與 `p914-invoice-per-bill`（預設＋三種例外）
  - E2（後四粗目）executor 交件：32→48 細目、27 句；裁決 18 則（87／89／95 判「不寫」）；fresh verifier **REFUTED**（8／27：身份標籤自取、群組成員設定其實各自不同、自訂品項看性質不看名稱、收據漏特定團隊例外、虛擬帳號有依人／依物件兩模式、分期是獨立開關、否定句範圍過寬、自動扣款指令其實 `exit`）⇒ 主 session 親修：改寫 5 句、刪 2 句、`balance-invoice-no-ghost-tenant-flag` 唯一句矛盾 ⇒ 整條刪、97 改「不寫」（G9）；E 架 99 條；送最後一次 verifier（24 句）
  - E2 **最後一次 verifier＝REFUTED**（5／24）⇒ 依業主裁整句刪：刪 2 句、3 條細目變空而移除（`recharge-account-anomaly-support`、`recharge-account-remittance-limit-and-sharing`、`credit-card-auto-deduct-status`；裁決 90／98／112／131 改「不寫」）；E 架定稿 96 條。連帶更正帳本 `p914-atm-amount-mismatch`（分銀行，藍新 ATM 不動帳）
  - E 架 43／44（G4「維持不寫」）的 open_questions 為已裁排除紀錄 ⇒ 清空；D／E 只剩 93 的 1 條
  - **步驟 4 生成**（容器，`--date 20260927 --expect-open-questions 54` 通過）：57 粗目／**541 細目**（515＋D 7＋E 19）；跨架重複 id／講法 0；DSP-068 刪除 23 行／27 字元（與先前相同）
  - 驗收：七架 `A B C F G H I.md` sha256 與生成前相同 ✓；E.md `page:bills.sheet|bills/sheet/Index.vue` 0（正對照 `bills/list/Index.jsx` 3）✓；`open-questions-20260927.md` 的 D／E 項＝`jgb/E/recharge-account-regenerate-expired` 1 條 ✓；**`make audit` OVERALL PASS**（不變量 34 綠、講法 1,750）✓
  - 全套單元：3,928 passed／**9 failed＝HANDOFF §4 既有名單逐名相同**／3 skipped（同基線）；PII 掃描 `runs` 命中清單無新檔（`open-questions-20260927.md` 未入列）；釘 sha 的測試無一變紅 ⇒ 不需改測試
  - `endpoint_progress.py`：`已審細目 pm 0／535、prospect 0／121`（D 104／9、E 96／21）
  - **裁決落地對照表** `scratchpad/p915-s3-ruling-map.json`：63 列＝審核單裁決編號集合；47 列指到的細目 id 全數存在於生成後正本；16 列「不寫」（含 96；82、124 原誤記為不寫，實為併入既有細目，已更正）。⚠️ **96 號主 session 分派 D 架題號時漏列**，收件對帳才發現 ⇒ 依 G9 預設判「不寫」（9.14 對源查無單一公式）並記錄
  - 收件抽 10 列對讀後再修 2 標題＋1 句（`bill-fee-item-rules` 標題改「不可小於」、`contract-tenant-code-change` 標題去掉無源否定、`balance-invoice-unsigned-contract` 去過程筆記）並重生成：541 細目、七架 sha 同、`make audit` PASS
  - **S3 整片 fresh outcome verifier＝CONFIRMED**（C1 三源一致＋獨立重生成逐位元組相同、C2 七架 `cmp`、C3、C4 `make audit`、C5 紅燈＝既有 9 條、C6、C7 裁決 63 列、C8 標題不斷言已刪內容、C9 更正的 5 條帳本對碼成立）⇒ **S3 完成**（終點 +0，S4 前置）
  - DEFER（P3／P4，依規則不動已 CONFIRMED 的候選，交 S4 審核時一併看）：`contract-list-row-gear-actions` 標題「不論狀態都有查看物件」漏權限條件；`p914-invoice-per-bill`「不合併」宜註明差額發票是另一機制；`bill-archive-precondition` 未列「已支出」也可封存；`recharge-account-mismatch-and-duplicate` 引號文字取自後台紀錄
  - S2～S4 累計 `subagent_tokens` 1,733,192（未含 4 位被停掉、未回報用量的 executor）／5M
  - **業主（2026-09-27）「先 commit S1～S3」⇒ `f5e3e48b`（未 push）；「帳本只核 D／E 有用到的」**
  - 帳本複核（fresh verifier，D／E 引用的 36 條扣掉本輪已核 8 條＝28 條）＝REFUTED：**6 條 P2 程式反證＋5 條 P3 收窄**（預覽帳單預設開啟 vs 關閉團隊、註冊 vs 免註冊租客、既存 vs 電子範本合約、事後註冊可經邀請連結認領、合約範本清單來源與英文版補充條款、續約簽署流程、押金收據為特定團隊客製等）；主 session 重現其中 3 項後更正 11 條帳本，並把引用它們的 D／E 11 句＋5 標題同步改寫、重生成（541 細目、七架同、`make audit` PASS）⇒ 送 fresh verifier
  - ⚠️ 本輪合計 16 條帳本要更正，已記入記憶 `project_ledger_p914_scope_errors`；S3b 執行者曾與複核並行、違反 §5「一次一位」⇒ 主 session 發現後停掉（未改任何檔），待複核完成再派
  - 更正驗證 fresh verifier＝REFUTED（主 session 自己引入 2 條 P2：「是否通知」隱藏角色寫反〔`config_rule_key 1`＝租客〕、事後註冊認領漏「同一瀏覽器、工作階段 120 分鐘內」條件）＋2 條 P3（LINE／FB 推播限已綁定、「位元」實作詞）⇒ 全修、重生成 ⇒ **targeted fresh verifier＝CONFIRMED**；另把 18 條過時的帳本 evidence 引文換成現行事實文字（正本逐位元組不變，evidence 不進正本）
  - 外洩掃描：規則一只命中業主已放行的產品用語（「待租客簽回」等、既有範本名）
  - G1 裁決的第二半「文件／文案待修清單」原本漏交（E1 verifier A3 指出）⇒ 主 session 補交 `inputs/doc-fix-list-9.15-G1-20260927.md`（9 條＋1 條 jgb2 程式缺陷）
  - **連帶更正已 commit 的帳本 2 條**（同根因，主 session 自己改、非 S3 擁有檔，屬本線先前引入的錯）：`p914-contract-gear-menu` 改依 `webList`（補查看帳單、兩個取消邀請、社宅／權限條件）；`p914-contract-agents` 限定社宅合約
- **S3 第 2 輪＝REVISE P2×3**；已達第 2 次 ⇒ 停止自動重送，主 session 逐條裁決**全 FIX**，開新就緒週期、只送一次收尾審查：業主裁決句無合法來源 ⇒ 定來源形式（審核單＃編號）與 verifier 判法；E 驗收數 74→73；裁決落地無驗收 ⇒ 加 63 列對照表與 `--expect-open-questions`。
- **S1 第 1 輪＝REVISE P2×2**：① M2 比對規則未定義、驗收抓不到壞掉的比對器 ⇒ FIX（§1 寫明 SPA／blade 規則、正對照 132／183、`--ignore-review`、合成 M2 測試）；② 大綱尚未 READY ⇒ 程序性，隨大綱裁決。
