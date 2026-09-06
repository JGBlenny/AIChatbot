# 步 2：structure

**輸入**：`intake.json`。
**輸出 schema**：`../schemas/structure-proposal.json`。
**形態**（業主 2026-09-06 裁：⛔ 本步不打模型 API、用 Claude Code 子代理）：`../scripts/structure_propose.py prepare` 產 3 份角度 prompt（使用者提問路徑／內容邊界／受眾層級，逐位元穩定、只寫定義）→ 主 session 派 3 個子代理各拿一份（互不可見）回 JSON → `validate` 逐份驗（schema＋id_map 覆蓋每一輸入項目＋細目 id 合規＋粗目不可改）→ `synth-prompt` → 第 4 個子代理合成（含 rejected_alternatives）→ `package` 成 StepEnvelope（合成不得引入三份都沒有的細目）。原始輸出留 `../raw/structure-<日期>/`（gitignored）；`deterministic=false`。粗目由 `../schemas/coarses-<audience>.json` 固定。
**套用**：`../scripts/apply_proposal.py --proposal <envelope> --kb-rows … --drafts … --version …` 決定性產正本草稿 Markdown＋id 對應表（缺對應表 exit 2；產出回讀過 `canon_parser`）。Workflow 版（`../../../workflows/outline-curation.js` Structure phase，未實作）留參考。
**出口條件**：三角度提案齊全、人審合成後的 `synthesis` 欄非空；成本落在步 2 上限（≤6 代理／$0.5）內，否則 `cost_ledger.py` 擋。
