# 步 0：覆蓋基準（JGB 頁面樹；功能全表為粒度對照）

**為什麼**（2026-09-18 業主）：領域地圖（`docs/knowledge/jgb-domain-map.md`）只列到粗目、缺口地圖（步 5）只從問句反推，
細目層沒有「產品有哪些功能」的分母 ⇒ 缺口只在有人問到時才被發現。本步固定在每一輪 intake 之前跑：缺口一次全部出來，補齊後一次審。

**輸入**：jgb2 分支（`config/character.php`、`routes/web.php`、`routes/api.php`）、幫助中心 zh-Hant 頁、既有正本目錄。
**輸出**：0a `page-surface.json`（StepEnvelope，`../schemas/page-surface.json`，決定性；功能全表 `feature-surface.json` 只當粒度對照）＋ 0b `feature-coverage.json`
（`../schemas/feature-coverage.json`，代理判定）＋人讀 `.md` 副本。**0b 的 JSON 是步 1 `--gapmap` 的輸入**（`cells[]`）。
**形態**：0a 腳本 `../scripts/feature_surface.py`（只讀來源；缺來源／0 筆／路由未解析比例超門檻 ⇒ exit 2；記 `jgb2_sha`、`help_dir`、`canon` 三個 sha 進 `inputs_sha`）；
0b 唯讀子代理分批，**只填判定**，每格對兩個開放身分（D3：`prospect`／`property_manager`）各一個判定 `by_identity`；`../scripts/feature_coverage_check.py` 驗 0b（unit_id 集合＝0a `units[]`、每格恰兩身分、verdict 在值域、covered／partial 必列存在的 `fine_ids`、sha 一致，違反 exit 2），印每身分統計。
**出口條件**：0a `counts` 六欄皆 >0、路由未解析 ≤ 10%；0b 通過 `feature_coverage_check.py`；`missing`／`partial` 清單進步 2 的擴充材料；0b 成本寫 `journal/feature-surface-<日期>.json`。

## 分母是什麼（DSP-065，2026-09-19；定義見 `inputs/definitions-outline-baseline-20260919.md`）

agent 回合拿問句比對細目、不預測客戶會問什麼 ⇒ 大綱該有的細目由「產品有哪些可被問的事」決定。
**基準＝JGB 使用者可到達的頁面樹**（`scripts/page_surface.py`，一條具名路由一格）：
(a) SPA 具名路由 `src/routes/*.js`；(b) 後端直接渲染的非內部頁（`routes/web.php` 非 `vueIndex`、非 `Admin\*`／`Internal\*`／`Vendors\*`、controller 方法含 `return view(`）。
歸架依版控 `schemas/page-shelf-map.json`；租客側標未開（DSP-054）、`nthurc` 住都專屬不入基準（DSP-065）。
功能全表（`scripts/feature_surface.py`：權限 action＋幫助中心段＋路由）只當粒度對照與步 5b 對源材料，⛔ 不當基準。
「產品沒有但客戶會問」的事由 I 架「目前不支援的功能」承接，清單來自客群痛點表，⛔ 不另立分母。
第一次跑（jgb2 `master` @ b2ee2ac382ce）：格 228＝基準 183（A 14／B 10／C 43／D 57／E 22／F 10／G 4／H 5／I 18，歸架依 DSP-067 骨架、以 `route:` 覆寫）＋租客 0＋住都 10＋不計 35（無頁面元件 6＝父路由轉址／catch-all，DSP-065a；非功能 19＝結果頁／匯入匯出／404／官網行銷頁／`vite`／LIFF 測試頁／通用殼層路由，D4；DSP-067 排除 10＝`users.approval` 統上客製、出售 5 頁、找房 2 頁、IoT 商品頁、舊活動付款頁）；SPA 具名路由 200（`next({ name })`／`redirect` 的 name 不算；單行路由物件也算）、blade 頁 28（同名 blade／SPA 頁各一格，如 `contracts.show`）（web.php 去註解後 GET／match 536：vueIndex 55、內部 172、api 56、無 view 217、controller 缺 8）。租客 0＝此路由樹沒有 `/tenant` 入口頁（租客側在別的入口，DSP-054 未開，另列）。

## 0 → 4／5 的橋（`../scripts/surface_to_cells.py`）

步 4（`answerability_args.py --cells`）與步 5（`coverage_map.reweigh`）吃 demand-v2 形狀的 `cells[]`；本橋把基準格（`page_surface` 的 `in_baseline` 格；或功能全表 action＋help 當對照）轉成格：
`id=F###`、`topic`＝單位 label、`questions=[]`（問法在步 3 從真實問句掛）、`g0.authority`＝`help:<file>`／`code:config/character.php:<action>`、`module`＝0b 對到的細目所在架；另出量測層 stub map（`cause_state="NOT_MEASURED"`）。
兩身分共用同一份格；⛔ 不再手工維護 55 格的售前專屬 demand-v2（它保留為歷史材料）。

## 0a 單位規則（機械，⛔ 無裁量）

- 一個權限 action ＝ 1 單位（`action:<key>`）。
- 路由：預設 `--route-granularity controller`——同 controller 併 1 單位（`route:<controller>`，`members` 列路由名）；`--route-granularity route` 則一 (controller, route name 或 path) 一單位。兩者皆規則、無裁量；`Admin\*` 標 `internal`；路徑或名稱含 `tenant` 標租客側。
- 幫助中心每頁每個 `<h3>` 段 ＝ 1 單位（`help:<file>#<section>`），無段落的頁 1 單位；分類含「租客」標租客側。
- 合併只准來自版控中的 `units-merge.json`（`{"merged_id": ["unit_id", …]}`，`--units-merge` 傳入、進 `inputs_sha`）。
- **已知不涵蓋面**（⛔ 不得當「沒有功能」）：Route group 前綴不還原（路徑為 group 內相對路徑）；陣列 callable／closure／`Route::resource|apiResource` 只計入「未解析」；前端 SPA 專屬畫面；排程、通知等無路由功能。

## 0b 判定規約

- **工作量與預算**：controller 粒度下單位約 450（45 action＋約 115 controller＋298 幫助中心段），0b 分批、每批一個唯讀子代理，批數 ≤ SKILL.md front matter 的 `feature_surface.agents`（4）：controller 粒度每批 ≤ 250 單位（458 ⇒ 2 批）；route 粒度（約 1,175 單位，只在需要逐路由對碼時用）每批 ≤ 300 單位（⇒ 4 批）。每批各寫一份 `journal/feature-surface-<日期>-<批>.json`，內含 `"step": "feature_surface"`（底線，⛔ 不是連字號，否則該層預算不計）。

- 對 0a 的每個單位恰填一格，格內對每個開放身分各一個判定（D5「每格×每身分」）：`verdict` ∈ `covered`（有細目、其 `target_user` 含此身分、直接答這頁的事，列 `fine_ids`）／`partial`（有相近細目但沒答這頁、或細目的 `target_user` 不含此身分，列 ids＋缺什麼）／`missing`／
  `tenant_not_open`（租客側，DSP-054）／`internal`（`Admin\*`）／`out_of_scope`（DSP-060 排除客群）。判定材料＝`canon/jgb/CATALOG.md`（id、標題、`target_user`、講法）＋各架 `A–I.md` 細目內文；售前身分問的是「有沒有這功能、怎麼運作」，業者身分問的是「這頁怎麼操作、規則是什麼」。
- ⛔ 不得新增、刪除、合併單位；route 名不明 ⇒ `note` 寫「需對碼」並判 `partial`，⛔ 不猜。
- 租客側單位不計缺口，但正本仍可有租客視角細目（受眾是業者），⛔ 不得因此刪它們。
- 範圍依 `.claude/DECISIONS.md` DSP-054／DSP-060／DSP-060a。

## CLI

```bash
# 0a 基準（頁面樹）
python3 .claude/skills/outline-curation/scripts/page_surface.py --jgb2 /Users/chenqinghuang/dev/work/jgb2/dev2 --branch master \
  --map .claude/skills/outline-curation/schemas/page-shelf-map.json --canon rag-orchestrator/canon/jgb \
  --out-json <run>/page-surface.json --out-md <run>/page-surface.md
python3 .claude/skills/outline-curation/scripts/page_surface.py --self-test
# 0a 功能全表（粒度對照）
python3 .claude/skills/outline-curation/scripts/feature_surface.py \
  --jgb2 /Users/chenqinghuang/dev/work/jgb2/dev2 --branch master \
  --help-dir "/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818" \
  --canon rag-orchestrator/canon/jgb \
  --out-json <run>/feature-surface.json --out-md <run>/feature-surface.md
python3 .claude/skills/outline-curation/scripts/feature_surface.py --self-test
# 0b 分批（頁面樹基準：批 1 A/B/G/H/I、批 2 C/F、批 3 D/E，每批一個唯讀判定子代理寫 <run>/coverage-<批>.json）→ 合併（非基準格機械填）
python3 .claude/skills/outline-curation/scripts/page_coverage_batches.py worklist --surface <run>/page-surface.json --out-dir <run>
python3 .claude/skills/outline-curation/scripts/page_coverage_batches.py merge --surface <run>/page-surface.json --out-dir <run> --out <run>/feature-coverage.json
# 0b 驗收＋橋（--surface 給頁面樹 page-surface.json；功能全表粒度對照時才給 feature-surface.json）
python3 .claude/skills/outline-curation/scripts/feature_coverage_check.py --surface <run>/page-surface.json --coverage <run>/feature-coverage.json
python3 .claude/skills/outline-curation/scripts/surface_to_cells.py --surface <run>/page-surface.json --coverage <run>/feature-coverage.json --out-cells <run>/cells.json --out-map <run>/map.json
python3 .claude/skills/outline-curation/scripts/intake.py --gapmap <run>/feature-coverage.json …
```
