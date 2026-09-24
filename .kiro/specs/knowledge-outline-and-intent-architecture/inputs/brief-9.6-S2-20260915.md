# 9.6 S2 執行契約（mech-executor）— 2026-09-15

前置：S1 verifier CONFIRMED（2026-09-15，fresh verifier 重跑 (a)～(f) 全過；advisory A1＝integration 8 既有紅、A2＝`scopes-jgb.json` 多 `_readme` 鍵，皆非阻斷）。母計畫 `plan-9.6-library-canon-20260915.md` v4 §3 S2。

## 結果（一句）
用 S1 出貨的 `canon_to_library.py` 把兩份現行正本落成 `rag-orchestrator/canon/jgb/`（九架＋CATALOG）＋`canon/jgb.json`＋`id_map.json`；**舊檔不動、不封存、舊 loader 照讀舊檔**（切換在 S3）。

## ⛔ 邊界
- 只寫：`rag-orchestrator/canon/jgb/`（新目錄）、`rag-orchestrator/canon/jgb.json`（新）、`.claude/skills/outline-curation/runs/library-20260915/id_map.json`（新）。
- ⛔ 不改任何 `.py`；⛔ 不動 `canon/prospect.*`／`canon/property_manager.*`／`canon/README.md`；⛔ 不動 tests；⛔ git stash／commit；⛔ 不讀 `.env`；⛔ 不碰 `.agents/`／`.codex/`。
- 產物一律由腳本寫出，⛔ 不手改任何一架或 CATALOG（hook 對它們有 diff_report 閘）。

## 步驟
1. 在容器內跑（用法比照 `scripts/run-tests.sh`，掛 `-v $PWD/.claude:/.claude:ro`）：
   `python3 /.claude/skills/outline-curation/scripts/canon_to_library.py --prospect /app/canon/prospect.md --pm /app/canon/property_manager.md --scopes /.claude/skills/outline-curation/schemas/scopes-jgb.json --out /app/canon/jgb --id-map-out /tmp/id_map.json`
   （`/app` 掛的是 `./rag-orchestrator`，寫 `/app/canon/jgb` 即落到工作樹）。
2. `mv rag-orchestrator/canon/jgb/jgb.json rag-orchestrator/canon/jgb.json`；把 `/tmp/id_map.json` 複製到 `.claude/skills/outline-curation/runs/library-20260915/id_map.json`（容器內 `/.claude` 是唯讀掛載 ⇒ 先寫到 `/app/canon/jgb/id_map.json` 再由 host 搬，搬完刪除目錄內副本）。
3. 再跑一次步驟 1 到 `/tmp/again` 並 `diff -r`（扣 `jgb.json` 位置差）以證決定性。

## 驗收（全部要跑、貼輸出）
① **全部 53 條逐欄對照**（母體必須＝53，<53 即失敗）：以 `parse_canon`（兩舊檔）與 `parse_canon_dir("canon/jgb")` 各自載入，對每條新 id ← id_map 的舊 id，比對 `title, target_user, business_types, reviewed_by, reviewed_at, content_sha256, phrasings（text/source/status 三元組集合）, policy, policy_ref, instance_applicability, categories`，以及 `see_also` 經 id_map 映射後相等。⛔ 只比可見子集不算。輸出：對照筆數 53、不符 0（列出任何不符）。
② 未審 15 條逐條列出 `新 id → target_user`，且每條的 `target_user` ＝ 其原檔受眾（prospect 12 條 `[prospect]`、pm 3 條 `[property_manager]`）。
③ `parse_canon_dir("canon/jgb")` 成功；`canon/jgb.json` 與 `export_json(parse_canon_dir(...))` 重導出逐位元相同；`canon/jgb/CATALOG.md` 與 `export_catalog` 重導出逐位元相同；CATALOG 行數＝71（9×2＋53）；H 架 0 條。
④ hook：對九架＋CATALOG 逐檔驅動 `.claude/hooks/outline_gate.py` 的 PostToolUse 檢查（結構／識別碼／講法唯一／撞凍結題）全綠（正對照：把任一架的一條講法複製到另一架後講法唯一必紅——在 `/tmp` 複本上做，⛔ 不動工作樹）。
⑤ 現行不受影響：`scripts/run-tests.sh unit tests/unit/agent tests/unit/_meta tests/unit/skills` failed=0；`scripts/run-tests.sh integration tests/integration/agent` failed 數與清單 **與 S1 交件相同（8，同清單）**——多一條即失敗。
⑥ `git status --porcelain` 只多出上列三個新路徑（`canon/jgb/`、`canon/jgb.json`、`runs/library-20260915/id_map.json`），無任何 `M`。

## 交件格式
改／新增檔清單；①～⑥ 每條指令＋輸出摘要（含數字）；取捨與已知債（含 S1 交件第 1 條「粗目標題去字母前綴」是否如實反映在架檔）。
