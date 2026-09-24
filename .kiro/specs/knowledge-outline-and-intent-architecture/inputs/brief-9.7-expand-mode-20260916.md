# 9.7 skill 擴充模式（executor）— 2026-09-16

業主 2026-09-16「接下來?」＝進入逐架補內容；本片只補**工具能力**，⛔ 不產內容、不改正本。母脈絡：DSP-058 圖書館正本（`rag-orchestrator/canon/jgb/`），skill 現況見 `.claude/skills/outline-curation/SKILL.md`（S4 已改）。

## 結果（一句）
outline-curation 能對**一架**做擴充：既有架內細目原樣保留，新材料（kb 列＋幫助中心頁）由步 2 提成新細目，`apply_proposal` 直接寫回九架（其他架逐位元不動）。

## 現況缺口（對碼）
- `structure_propose.py prepare` 與 `apply_proposal.py`：`--kb-rows` 與 `--canon` **二擇一**（互斥），沒有「既有正本＋新材料」的擴充模式。
- `intake.py --drafts` 只收 `id`＋`summary`，沒有內容欄；幫助中心頁的正文沒有進 skill 的路。
- `apply_proposal.render_remap`（--canon 模式）內容只來自既有細目（`id_map`），`tmp:kb:*` 新來源不會被渲染。

## ⛔ 邊界
⛔ `.env`／git stash／commit；⛔ 碰 `.agents/`／`.codex/`（主 session 同步）；⛔ 動 `rag-orchestrator/services/**`／`app.py`／hook／`scripts/audit/**`；⛔ 寫 `rag-orchestrator/canon/jgb/`（本片只到 `/tmp`）；⛔ 派子代理；⛔ 呼叫任何 LLM／embedding。測試在容器 `scripts/run-tests.sh unit tests/unit/skills`；腳本在容器內掛 `-v "$PWD/.claude:/repo/.claude:ro"`，輸出 `/tmp`。

## 範圍（可改）
`.claude/skills/outline-curation/scripts/{structure_propose,apply_proposal,intake,canon_items}.py`、`schemas/structure-proposal.json`、`steps/02-structure.md`、`SKILL.md`（加一節「擴充模式」）、`rag-orchestrator/tests/unit/skills/outline_curation/`（新 `test_outline_curation_expand_req.py`＋既有調整）。

## 規格
1. **擴充模式**＝同時給 `--canon <jgb 目錄>`＋`--kb-rows <rows.json>`（可再加 `--drafts`）＋**`--shelf <X>`**（單一粗目碼）：
   - `prepare`：候選項目＝該架既有細目（`tmp:canon:<fine.id>` 形狀，沿用 `canon_items`）＋kb 列（`tmp:kb:<id>`）＋drafts（`tmp:draft:<n>`，drafts 物件加選填 `text` 欄，prompt 內附正文，⛔ 只給該架用）；其他架細目**不進 prompt**（只在 output spec 說明「其他架不得動」）；prompt 明寫：既有細目一律 `op=keep`（id 不變）除非提議者判為 `merge`／`split`；新細目 `op=new`、`merge_of` 列來源、`target_user` 必填；材料若明顯屬他架 ⇒ 列在 `out_of_shelf`（id＋建議架）而不提成細目。
   - `apply_proposal`：`--canon`＋`--kb-rows`＋`--shelf X`：輸出九架到 `--out`，**非 X 架逐位元＝輸入**；X 架＝既有細目依 `id_map`（keep/move/merge/split 規則沿用 `render_remap`）＋新細目：`op=new` 且 `merge_of` 全為 `tmp:kb:*` ⇒ 內容＝各列 `answer` 依 `provenance_units.split_sentences` 切句、依序串接（不去重）、`sources: [kb:<id>…]`、`business_types` 預設 `[system_provider]`（可由提議覆寫）、`target_user` 取提議、無 `reviewed`；`merge_of` 含 `tmp:draft:*` ⇒ 該細目**內容為空**（零 content_units 合法）、`sources: [helpcenter:<slug>…]`、並寫進 `<out>/pending-content.json`（id、標題、來源頁 id、頁文）供人／代理撰寫；`op=new` 的 id 必須 `jgb/X/<slug>` 且不與任何架既有 id 撞（撞 ⇒ exit 2）。同時重產 `CATALOG.md`／`jgb.json`；跨架講法唯一由 `parse_canon_dir` 回讀把關（重複 ⇒ exit 2 且不留半套）。
   - `intake.py`：`--canon`＋`--kb-json`＋`--drafts`＋`--shelf` 同時可給（擴充模式），`payload` 記 `mode: "expand"`、`shelf`。
2. schema：`structure-proposal.json` 的 fine 加選填 `op`（enum keep/move/merge/split/new）與 `out_of_shelf[]`（`{id, suggested_shelf, why}`）；擴充模式下 `op` 必填。
3. 決定性：同輸入兩次逐位元同輸出；任何 exit 2 不落任何輸出檔。
4. 文件：`steps/02-structure.md`＋`SKILL.md` 加「擴充模式（一架一輪）」流程與指令範例（指令用真路徑：`rag-orchestrator/canon/jgb`、`runs/<架>-<日期>/kb-rows.json`）。

## 驗收（貼數字）
① `scripts/run-tests.sh unit tests/unit/skills` 0 failed（新增 ≥8 案：擴充 prepare 候選集合＝該架既有＋rows＋drafts；他架不進 prompt；apply 非 X 架逐位元同；`op=new` kb 內容切句同源；draft 新細目零內容＋pending-content；id 撞 exit 2 不落檔；跨架講法重複 exit 2 不落檔；決定性）。
② 對真材料 dry：`prepare --canon rag-orchestrator/canon/jgb --kb-rows .claude/skills/outline-curation/runs/A-20260916/kb-rows.json --drafts runs/A-20260916/help-pages.json --shelf A --coarses schemas/coarses-jgb.json --out-dir /tmp/prep` ⇒ items＝1（既有）＋21（rows）＋10（drafts），prompt 內無他架細目（正對照：不帶 `--shelf` 的 `--canon` 模式 prompt 含 53 條）。
③ 合成提議（A 架：既有 1 條 keep＋2 條 `new` 來自 rows＋1 條 `new` 來自 draft）`apply` 到 `/tmp/x`：`parse_canon_dir` 成功、細目 53＋3、B～I 八架與 `canon/jgb` 逐位元同、`pending-content.json` 1 筆；負對照：把一條 `new` 的 id 改成既有 `jgb/B/team-management-overview` ⇒ exit 2 且 `/tmp/y` 不存在。
④ `scripts/run-tests.sh unit` 全套 0 failed。

## 交件格式
改檔清單；①～④ 指令＋數字；取捨；`.agents/` 需同步檔清單。
