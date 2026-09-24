# 9.6 S4 執行契約（executor）— 2026-09-15

前置：S1／S2／S3 皆 fresh verifier CONFIRMED（2026-09-15）。母計畫 `plan-9.6-library-canon-20260915.md` v4 §2「skill」「文件」列＋§3 S4。⛔ 本片不改任何 `rag-orchestrator/services/**`、`app.py`、`scripts/audit/**`、hook——那些在 S3 已收。

## 結果（一句）
skill（outline-curation）與文件改成描述圖書館正本；skill 對 `canon/jgb/` 能跑重切（`--canon` 目錄）；全 repo 無舊 id 前綴殘留。

## ⛔ 邊界
⛔ `.env`／git stash／commit／push；⛔ 碰 `.agents/`／`.codex/`（主 session 同步）；⛔ 手改 `canon/jgb/*`；⛔ 動 `docs/archive/**`（封存物）；⛔ 補知識內容；⛔ 動 `rag-orchestrator/services/**`／`app.py`／`scripts/audit/**`／`.claude/hooks/**`。看舊版 `git show HEAD:<path>`。測試在容器 `scripts/run-tests.sh unit <args>`；skill 腳本在容器內掛 `-v "$PWD/.claude:/repo/.claude:ro"`（寫輸出到 `/tmp`）。

## 範圍
1. `.claude/skills/outline-curation/scripts/apply_proposal.py`：`--canon` 接目錄（`parse_canon_dir`）或單檔（封存檔）；`render`／`render_remap` 產出改為**依粗目切九架**寫到 `--out <dir>`（front matter 六鍵，`scope` 沿用輸入正本的 `scopes`／或 `--scopes`），每細目寫明 `target_user`＋`business_types`，id 規則 `jgb/<粗目碼>/<slug>`；同時呼叫 `export_catalog`／`export_json` 產 `CATALOG.md`／`jgb.json`；`--audience` 參數改為 `--canon-name`（預設 `jgb`）。既有 prospect 單檔渲染路徑可刪（DSP-058 後無用），但 `--canon` 讀單檔仍要能讀封存檔（`canon_items.py` 沿用 `parse_canon`／`parse_canon_dir` 二擇一）。
2. `.claude/skills/outline-curation/scripts/structure_propose.py`：`coarses_block`／`output_spec_block` 改 `jgb/<粗目碼>/<slug>`，粗目來源 `schemas/coarses-jgb.json`（新；由 `coarses-prospect.json` 與 `coarses-property_manager.json` 合成，兩檔內容相同的 9 條，⛔ 不新增粗目；舊兩檔刪除）；提示詞的 output spec 加「每細目必填 `target_user`（值域 prospect／property_manager，共用明列兩者）」定義句（提示詞只寫定義不寫例子）。
3. `.claude/skills/outline-curation/schemas/structure-proposal.json`：fine 物件加必填 `target_user`（陣列、enum）；`apply_proposal` 驗證缺＝exit 2。
4. `.claude/skills/outline-curation/scripts/{canon_items,structure_review_sheet,diff_report,intake,canon_source_check,answerability_args}.py`：凡 `parse_canon(<path>)` 改為「路徑是目錄 ⇒ `parse_canon_dir`，否則 `parse_canon`」（共用一個小 helper 放 `canon_items.py`）。
5. `.claude/skills/outline-curation/SKILL.md`、`steps/02-structure.md`、`steps/06-diff.md`、`steps/07-import.md`：受眾檔敘述改圖書館形態（正本＝`canon/jgb/`；重切輸入 `--canon rag-orchestrator/canon/jgb`；「換受眾前置」一節改為「受眾＝細目屬性，不換檔」）。
6. 測試 `rag-orchestrator/tests/unit/skills/outline_curation/*`：對上列改動補／改案；既有 `coarses-*` 引用改 `coarses-jgb.json`。
7. 文件：`docs/architecture/SYSTEM_ARCHITECTURE.md` §2 路 A A-9（大綱組裝：`parse_canon_dir`→受眾視圖→`_STATIC_TOC_IDENTITY`→`build_outline` 先過軸→K=5）與 registry 敘述；`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` 提到 `canon/<audience>.md`／`load_canon_or_die(…, audience)`／「兩份正本」之處；`docs/knowledge/jgb-domain-map.md` §4「我們現在的東西對上去」加一句現況指向 `canon/jgb/`。⛔ 只改與正本形態相關的句子，⛔ 不重寫章節；每句改動要能被 `make audit` 的不變量 36／41 接受（反引號識別字須 grep 得到）。
8. 殘留掃描：全 repo（排除 `docs/archive/`、`.claude/skills/outline-curation/runs/*-20260915/`、`raw/`、`journal/`、`.git`）grep `prospect/[A-Z]/[a-z0-9-]+|property_manager/[A-Z]/[a-z0-9-]+` 應為 0 命中（正對照：對 `docs/archive/` 同一 grep 必命中）；有命中逐一改成 `jgb/…`（用 `runs/library-20260915/id_map.json`）或說明為何保留。

## 驗收（全部要跑、貼數字）
① `scripts/run-tests.sh unit` 全套 0 failed（含 skill 測試新數字）。
② `apply_proposal.py --canon rag-orchestrator/canon/jgb --proposal <合成提案> --out /tmp/x`：合成提案＝對現行 `canon/jgb` 三條細目 `op=keep`（含 `target_user`）的最小 structure-proposal（⛔ 不用 `runs/*-20260915/structure-proposal.json`，那是舊 id 前綴的重切材料）；能產九架＋CATALOG＋jgb.json，且 `parse_canon_dir(/tmp/x)` 成功、三條細目內容逐字同源；正對照：同提案拿掉一條的 `target_user` ⇒ exit 2。
③ `structure_propose.py prepare --canon rag-orchestrator/canon/jgb`（或其現行子命令）能產 intake／prompt，prompt 內粗目 9 條且 id 規則為 `jgb/`（貼片段）。
④ 殘留掃描 0 命中＋正對照命中數。
⑤ `make audit`：不變量 36／40／41 不比改前差（改前：36 PASS、40 PASS、41 FAIL 20 條）；貼三條的狀態。
⑥ `git status --porcelain` 改動檔 ⊆ 本 brief 範圍（貼清單）。

## 交件格式
改／新增／刪除檔清單；①～⑥ 指令＋輸出摘要；取捨與已知債；`.agents/` 需同步的檔清單（給主 session）。
