# 9.6 S1 執行契約（security-executor）— 2026-09-15

業主 2026-09-15「開工」核可。母計畫：`plan-9.6-library-canon-20260915.md` v4（§2 表、§3 S1、附錄 A）。定案：`.claude/DECISIONS.md` DSP-058。

## 結果（一句）
新增「一目錄＋九架」正本的解析路徑、衍生物導出、遷移腳本與 hook 分流；**舊單檔路徑與現行正本、啟動、測試一律原封**。

## ⛔ 邊界（違反即停）
- 只改下列「範圍」檔案；⛔ 不動 `load_canon_or_die`／`_CANON_REGISTRY`／`build_outline`／`runtime.py`／`app.py`／`outline.py`（那是 S3）。
- ⛔ 不讀 `.env`、不印任何金鑰；⛔ `git stash`；⛔ commit／push；⛔ 不碰 `.agents/`／`.codex/` 鏡像（主 session 手動同步）；⛔ 不對 DB 做任何寫入；⛔ 不寫 `rag-orchestrator/canon/jgb/`（S1 ⑩ 只寫到暫存目錄）。
- 看舊版用 `git show HEAD:<path>`。
- 否定結論一律帶正對照；測試在容器跑：`scripts/run-tests.sh unit <pytest args>`（host 無 pytest／psycopg2）；skill 腳本需要 parser 時在容器跑並掛 `-v $PWD/.claude:/repo/.claude:ro`（見 `scripts/run-tests.sh` 用法）。

## 範圍（可改）
1. `rag-orchestrator/services/agent/canon/canon_parser.py`
2. `.claude/hooks/outline_gate.py`
3. `.claude/skills/outline-curation/scripts/canon_to_library.py`（新）
4. `.claude/skills/outline-curation/schemas/scopes-jgb.json`（新；內容＝計畫附錄 A 九條，鍵 `A`…`I`）
5. 測試：`rag-orchestrator/tests/unit/agent/test_canon_parser_req.py`（加，不刪既有）、`rag-orchestrator/tests/unit/_meta/test_outline_gate_req.py`（調整同值測試）、新 `rag-orchestrator/tests/unit/skills/outline_curation/test_canon_to_library_req.py`
6. fixture：`rag-orchestrator/tests/fixtures/canon_jgb/`（合成三架＋一空架）

## 規格

### A. parser（`canon_parser.py`）
- 常數 `CANON_NAME = "jgb"`、`SHELF_FRONT_MATTER_KEYS = ("coarse","title","scope","version","reviewers","language")`、`SHELF_FILES = tuple(f"{c}.md" for c in "ABCDEFGHI")`、`SHELF_DERIVED_OK = ("CATALOG.md","README.md")`。既有 `FRONT_MATTER_KEYS`／`AUDIENCES`／`parse_canon`／`parse_canon_text`／`export_json` **語義與輸出逐位元不變**。
- `CanonDoc` 加欄位 `name: str`（單檔路徑＝`audience` 值；目錄路徑＝`CANON_NAME`；`audience` 目錄路徑亦填 `CANON_NAME`）。⚠️ `to_dict`／`export_json` 對**單檔**輸入的輸出必須逐位元不變 ⇒ `name` 只在目錄路徑才進導出（或導出時對單檔省略）；以 `test_canon_export_sync_req` 現行綠為證。
- `parse_canon_dir(dir) -> CanonDoc`：
  - `base = Path(dir).resolve()`；只讀 `SHELF_FILES`（固定白名單、字母序，⛔ 不 glob）；缺任一架 ⇒ `CanonFormatError(0, "缺架 X.md")`。
  - 目錄內任何 `.md` 不在 `SHELF_FILES ∪ SHELF_DERIVED_OK` ⇒ raise（大聲失敗）；每架 `resolve()` 後 `parent != base` 或 `is_symlink()` ⇒ raise。
  - 每架：front matter 恰為 `SHELF_FRONT_MATTER_KEYS`（多鍵／缺鍵 raise）；`coarse` 須等於檔名字母；`scope` 缺或空白 ⇒ raise；主體恰一個 `## 標題 {#X}` 且 X＝`coarse`（零細目允許）。
  - 細目：id 首段須等於 `CANON_NAME`（否則 raise）；**`target_user` 與 `business_types` 必填非空**（缺 ⇒ raise，訊息含細目 id）；`target_user` 每值 ∈ `_target_user_universe()`（沿用 `_validate_target_user`，`all_users` 拒）；`business_types` 須含 `system_provider`。
  - `see_also` 目標跨架存在性；`canon_sha256 = sha256("\n".join(sha256(每架全文) 依序))`；`phrasing_set_sha256` 沿用既有算法。
  - `version`／`reviewers`／`language`：九架須一致（不一致 raise）；`budget_tokens` 不存在（`CanonDoc.budget_tokens` 目錄路徑填 `0`，S3 不再讀它）。
- `export_catalog(doc, path)`：決定性；格式每架 `## X 標題 {#X}` 後一行 `scope: …`，再每細目一行 `<id>｜<title>｜target_user=<a,b>｜<approved 講法以「／」串接>`；⛔ 不含 content_units。
- 實作方式：把單檔 body 解析抽成可重用的內部函式（`_parse_body(lines, ...)`）給兩條路徑共用，⛔ 不複製一份狀態機。

### B. hook（`.claude/hooks/outline_gate.py`）
- `CANON_RE` 改 `^rag-orchestrator/canon/.+\.md$`；`_is_canon_target` 扣 `README.md`（任何層）。
- 分流：路徑符合 `^rag-orchestrator/canon/jgb/[A-I]\.md$` ⇒ 架規則（六鍵、一檔一粗目、X＝檔名、id 首段 `jgb`、細目必填 `target_user`＋`business_types`）；`canon/jgb/CATALOG.md` ⇒ 只跑識別碼掃描（結構跳過）；其他 ⇒ 舊七鍵規則（原封）。
- 講法唯一／撞凍結題／識別碼掃描對所有命中檔照跑。
- 常數與 parser 同值（`SHELF_FRONT_MATTER_KEYS`、`FINE_ID_RE`、`CANON_NAME`），`test_outline_gate_req.py` 的同值測試補新常數。

### C. `canon_to_library.py`
- CLI：`--prospect <md> --pm <md> --scopes <json> --out <dir> [--id-map-out <json>]`。
- 讀兩份舊正本（`parse_canon`）；每細目：id `<aud>/X/slug` → `jgb/X/slug`；`target_user`／`business_types` 落成明列（來源＝該細目在舊檔的實際值，即檔級預設）；`see_also` 同步 remap；其餘屬性（phrasings 含 status、sources、reviewed、policy、policy_ref、categories、instance_applicability）與 content_units 逐字原樣。
- 產 `<out>/A.md…I.md`（H 空架亦產）、`<out>/CATALOG.md`（`export_catalog`）、`<out>/jgb.json`（`export_json`；S2 再由主 session 搬到 `canon/jgb.json`）；`version` 取 `--version`（預設兩檔一致值，否則 raise）。
- 決定性：同輸入兩次逐位元相同。`id_map.json`：`[{"old": …, "new": …, "op": "keep"}]`（`remap_ids.py` 可讀的裸陣列）。
- 停點：同架同 slug 碰撞 ⇒ exit 2 列出（主 session 已盤為 0，仍要有檢查）。

## 驗收（全部要跑、要貼輸出）
① fixture 目錄 `parse_canon_dir` ＝預期 JSON（3 架＋1 空架、6 細目、跨架 see_also、一條共用 `[prospect, property_manager]`）。
② 缺 `target_user`／空／含 `all_users`／缺 `business_types`／不含 `system_provider` 各 raise（正對照：同 fixture 合法細目通過）。
③ `coarse`≠檔名 raise；④ 一檔兩粗目 raise；⑤ 多 `Z.md` raise（正對照：多 `README.md` 不 raise）；⑥ 符號連結 raise；⑦ id 首段 `prospect/` raise；⑧ `export_catalog` 兩次逐位元相同；⑧b `scope` 缺／空 raise（正對照：有 scope 通過）。
⑨ 相容性：`parse_canon("canon/prospect.md")`／`property_manager.md` 成功且 `canon_sha256` 與改前相同（改前值先記下）；`scripts/run-tests.sh unit tests/unit/agent tests/unit/_meta tests/unit/skills` 0 failed；`scripts/run-tests.sh integration tests/integration/agent` 0 failed（跑不動要說原因，⛔ 不宣稱綠）。
⑩ `canon_to_library.py` 對兩份現行正本＋`scopes-jgb.json` 跑兩次到暫存目錄，逐位元相同；`parse_canon_dir(暫存)` 成功、細目數 53、H 架 0 條；⛔ 不落版控。
⑪ hook 自測全綠；`canon/jgb/A.md`、`canon/jgb/CATALOG.md`、`canon/foo.md`、`canon/prospect.md` 命中 `CANON_RE`，`canon/README.md`／`canon/jgb/README.md` 不命中；`canon/prospect.md` 仍走七鍵規則通過。

## 交件格式
- 改了哪些檔（路徑）；每條驗收的指令＋輸出摘要（含 failed 數）；取捨與已知債；⛔ 不要總結成「全綠」而沒有貼數字。
