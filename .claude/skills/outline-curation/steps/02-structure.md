# 步 2：structure

**輸入**：`intake.json`。
**輸出 schema**：`../schemas/structure-proposal.json`。
**形態**（業主 2026-09-06 裁：⛔ 本步不打模型 API、用 Claude Code 子代理）：`../scripts/structure_propose.py prepare` 產 3 份角度 prompt（產品功能面／內容邊界／受眾層級，逐位元穩定、只寫定義）→ 主 session 派 3 個子代理各拿一份（互不可見）回 JSON → `validate` 逐份驗（schema＋id_map 覆蓋每一輸入項目＋細目 id 合規＋粗目不可改＋每細目必填 `target_user`）→ `synth-prompt` → 第 4 個子代理合成（含 rejected_alternatives）→ `package` 成 StepEnvelope（合成不得引入三份都沒有的細目）。原始輸出留 `../raw/structure-<日期>/`（gitignored）；`deterministic=false`。粗目由 `../schemas/coarses-jgb.json` 固定（9.6 S4／DSP-058 起兩受眾共用同一份，⛔ 不再分 `coarses-prospect.json`／`coarses-property_manager.json`）。
**套用**：`../scripts/apply_proposal.py --proposal <envelope> --kb-rows … --drafts … --version …` 決定性產正本草稿 Markdown＋id 對應表（缺對應表 exit 2；產出回讀過 `canon_parser`）——⚠️ 此為 `--kb-rows` 單檔臨時彙整路徑，非圖書館正本輸出（見下方重切用法）。Workflow 版（`../../../workflows/outline-curation.js` Structure phase，未實作）留參考。

**重切用法**（任務 9.3⑤，從既有正本重切；9.6 S4 起輸出恆為圖書館九架，與上面「新建」用法互斥，`--kb-rows`／`--canon` 二擇一）：
正本＝`rag-orchestrator/canon/jgb/`（一目錄＋九架）。步 1／步 2／步 3 的 `--canon` 一律指這個目錄：
`intake.py --canon rag-orchestrator/canon/jgb --exclude <排除清單.json>`、
`structure_propose.py prepare --canon rag-orchestrator/canon/jgb --exclude <排除清單.json> --coarses ../schemas/coarses-jgb.json`
（`--exclude` 只在給 `--canon` 時有效；`--canon` 也接單檔封存正本，供讀取已退役的舊格式材料）。
人審合成提議後套用：
`../scripts/apply_proposal.py --proposal <envelope> --canon rag-orchestrator/canon/jgb --out <目錄>`——
`--version`／`--scopes`／`--out-idmap`／`--out-pending-dir` 皆有預設（依序沿用輸入正本 version／輸入正本自帶
scopes 或 `../schemas/scopes-jgb.json` 內建預設／`<out>/id_map.json`／`<out>/pending/`），故最小可只給這三個參數。
內容來源改成 `--canon` 的既有細目，依 `id_map` 每一（舊→新）邊決定屬性去留（規則見 `apply_proposal.py::render_remap` docstring：
唯一且未被拆分的來源＝原樣帶過；其餘＝合併模式，講法聯集去重、`reviewed` 丟棄、`policy` 需一致否則 exit 2；
`target_user` 一律由提議每細目必填驅動，⛔ 不沿用來源、缺即拒套）；產出＝九架 Markdown＋`CATALOG.md`＋`jgb.json`
（`export_catalog`／`export_json`）＋`<out>/pending/` 落三個待審 JSON（`pending-splits.json`／`pending-phrasings.json`／
`pending-see_also.json`），步 3 要先消化 `pending-phrasings.json`。
業主審結構提議時可先跑 `../scripts/structure_review_sheet.py --run-dir <run-dir> --out <sheet.md>` 產「歸屬審核單」
（A 舊→新、B split、C merge、D rejected_alternatives、E 粗目分佈、F 待審清單——⚠️ F 只列結構預測，
實際 `pending-*.json` 筆數要 `apply_proposal.py --canon` 真的套用後才知道）。
**出口條件**：三角度提案齊全、人審合成後的 `synthesis` 欄非空；成本落在步 2 上限（≤6 代理／$0.5）內，否則 `cost_ledger.py` 擋。

## 擴充模式（一架一輪；brief-9.7，2026-09-16）

- 觸發：`prepare … --shelf <X>`，且 `--canon <rag-orchestrator/canon/jgb>`＋`--kb-rows` 同給（選填 `--drafts`，幫助中心頁形狀 `[{id:"help:<slug>", summary, text}]`）；`--exclude` 不適用。
- 候選＝該架既有細目（`tmp:canon:<fine.id>`）＋kb 列（`tmp:kb:<id>`）＋草稿（`tmp:draft:<n>`）；**其他八架的細目不進 prompt**，output spec 只說「其他架不得動」。
- 提議者規則：既有細目預設 `op=keep`（id 不變），只有判為同題才 `merge`／`split`；新細目 `op=new`、`merge_of` 列來源、`target_user` 必填（prospect／property_manager，共用明列兩者）；材料明顯屬他架 ⇒ 列 `out_of_shelf[{id, suggested_shelf, why}]`，⛔ 不提成細目。
- 之後：`apply_proposal.py --shelf X --canon … --kb-rows … [--drafts …] --proposal … --out <空目錄>`（見 SKILL.md「擴充模式」）；`pending/pending-content.json` 是幫助中心頁提成的細目（有標題、零內容），交人／代理撰寫後再補審。
