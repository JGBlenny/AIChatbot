# 步 4：answerability

**輸入**：`phrasing-map.json`。
**輸出 schema**：`../schemas/answerability.json`。
**形態**（業主 2026-09-06 裁：skill 流程用 Claude Code 子代理；模型 API 只在真實對話使用，⛔ 不留 API 判者）：`../scripts/answerability_agents.py prepare` 把格分組（預設 5 格一組，共用 rubric＋候選 prompt）→ 每組 2 個 slot 的 prompt 逐位元相同 → 主 session 每次最多 4 個子代理並行（8 GB 機器 ≥10 並行會整機重開）→ 回傳 JSON 存 `verdicts/<組>-s<slot>.json`（用 `../scripts/save_verdict.py <組>-s<slot> <子代理 transcript.jsonl> --out-dir <prepare 的 --out-dir>`：取最後一則 assistant 文字、容忍圍欄與散文、無文字 exit 2）→ `collect`：事後驗證、不一致格產第 3 判者 prompt（`third.prompt.md`）、齊了就 Reconcile（與 1.4 定義等價、門檻 0.80）→ result JSON → `finalize_answerability.py`。`deterministic=false`；原始 prompt／回傳留 `../raw/answerability-<日期>/`。Workflow 版（`../../../workflows/outline-curation.js`，1.4）留參考。
**出口條件**：`needs_rubric_revision=false`（為 `true` 時 Stop hook 擋）；成本落在步 4 上限（≤180 代理／$3）內。

## 實作對應（1.4）

- **rubric 正本**：[`../schemas/answerability-rubric.md`](../schemas/answerability-rubric.md)（四值定義，⛔ 不寫例子；跑前凍結 sha、業主核可後才進 readiness）。
- **args 組裝**：`../scripts/answerability_args.py --slim`——讀缺口地圖（55 格；`.kiro/specs/presales-grounding-gate/coverage-map/map-v2.json`）＋rubric＋候選來源 → args JSON。候選來源二擇一：**`--canon <正本或草稿 .md>`（2.4b 起的正式用法：候選＝細目，id＝細目 id、content＝內容句；講法／sources 不進候選）**，或 `--kb-rows`＋`--drafts`（M-a 試作的臨時集合 `tmp:kb:<id>`／`tmp:draft:<n>`）。白名單投影，⛔ 不含分數／排序／系統判定欄位；支援 `--cell-ids` 子集。
- **重產 2.4b 材料（repo 根）**：`python3 .claude/skills/outline-curation/scripts/answerability_args.py --cells .kiro/specs/presales-grounding-gate/coverage-map/map-v2.json --canon <草稿.md> --rubric .claude/skills/outline-curation/schemas/answerability-rubric.md --frozen-at <ISO> --slim --out .claude/skills/outline-curation/raw/answerability-<日期>/args-canon.json` → `python3 .claude/skills/outline-curation/scripts/answerability_agents.py prepare --args <同上> --out-dir .claude/skills/outline-curation/raw/answerability-<日期> --cells-per-agent 5`。
- **判者（現行）**：`../scripts/answerability_agents.py prepare --args <slim args> --out-dir <raw dir> [--cells-per-agent 5]` → 派子代理 → `collect --args … --out-dir … --out <result>`（exit 3＝還缺判者檔、exit 4＝已產第 3 判者 prompt、0＝Reconcile 完成）。同組的格共用 prompt，判者可見同組其他格問句；同一格的判者之間互不可見。
- **Workflow（參考）**：[`../../../workflows/outline-curation.js`](../../../workflows/outline-curation.js)（`step:'answerability'`）——`pipeline(cells, judge1, judge2, 不一致才 judge3)`；args >20 KB 要用 wrapper `workflow({scriptPath}, ARGS)` 委派；同 schema、同 Reconcile。
- **收尾**：`../scripts/finalize_answerability.py`——把判者結果（`answerability_agents.py collect` 輸出或合併後結果）包成 StepEnvelope（過 `../schemas/answerability.json`）、寫 journal 檔、更新狀態檔 `answerability` 鍵；`needs_rubric_revision=true` 時仍寫檔但 exit 2。
