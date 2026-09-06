---
name: outline-curation
description: 完善大綱（正本粗目／細目／講法）的七步決定性流程——intake→structure→phrasing→answerability→reweigh→diff→import。每步輸出 StepEnvelope 化 JSON，只產待審清單，⛔ 不自動合併、⛔ 不自動入庫。用於新建或重切某受眾的知識正本大綱。
version: "0.1.0"
budgets:
  structure:
    agents: 6
    usd: 0.5
  answerability:
    agents: 180
    usd: 3
  total:
    agents: 240
    usd: 6
---

# 完善大綱 skill

⛔ **本檔只承載流程全圖、七步表、四閘門索引與成本表。紀律本身住在 hook
（`.claude/hooks/outline_gate.py`）與 `../retrieval-improvement-loop/rules/`——這裡只指連結，不複製。**

## 流程全圖

```text
1 intake        腳本      讀輸入、凍結 sha、產「受測物定義清單」骨架
   ↓
2 structure     腳本→子代理 3 角度提議（提問路徑／內容邊界／受眾層級）各一子代理 → 第 4 個子代理合成
   ↓                      → steps/02-structure.md（2.3 實作；Workflow 版留參考）
3 phrasing      腳本+人審 講法／缺口格掛回細目；相似細目待審清單
   ↓
4 answerability 腳本→子代理 每組 5 格 × 2 判者（互不可見）、不一致加第 3；事後驗證、raw 留檔
   ↓                      → steps/04-answerability.md（answerability_agents.py：分組子代理；Workflow 版留參考）
5 reweigh       腳本      呼叫 tools/gapmap/coverage_map.py 重量
   ↓
5b source-audit 腳本+scout not_available／owner_decision 的格先對權威來源（jgb2 程式／docs／幫助中心）盤查，
   ↓                      事實回填 docs/knowledge/jgb-product-facts.md；只有 owner_needed 才交業主 → steps/05b-source-audit.md
6 diff          腳本      結構差異＋id 對應表＋取代對應表＋成本（G4 獨立驗證）
   ↓
7 import        腳本      業主核可後：正本 commit → export_batch → import_facet_knowledge
                          ⚠️ `export_batch.py` 與 `import_facet_knowledge.py` 的擴充**尚未實作**（任務 7.1／7.2）
                          ⛔ 需業主授權（D1）
```

## 七步

| 步 | 檔案 | 輸入 | 輸出 schema | 形態 |
|---|---|---|---|---|
| 1 | [`steps/01-intake.md`](steps/01-intake.md) | kb 列／草稿／缺口地圖／既有正本 | `schemas/intake.json` | 腳本 |
| 2 | [`steps/02-structure.md`](steps/02-structure.md) | intake.json | `schemas/structure-proposal.json` | 腳本＋Claude Code 子代理（2.3；決策 7 修訂） |
| 3 | [`steps/03-phrasing.md`](steps/03-phrasing.md) | structure-proposal.json | `schemas/phrasing-map.json` | 腳本＋人審 |
| 4 | [`steps/04-answerability.md`](steps/04-answerability.md) | phrasing-map.json | `schemas/answerability.json` | 腳本＋Claude Code 子代理（`answerability_agents.py`；業主 2026-09-06：API 只在真實對話） |
| 5 | [`steps/05-reweigh.md`](steps/05-reweigh.md) | answerability.json | `schemas/coverage-reweigh.json` | 腳本 |
| 5b | [`steps/05b-source-audit.md`](steps/05b-source-audit.md) | coverage-map.json | `schemas/source-audit.json` | 腳本＋唯讀 scout；⛔ 未核對不得交業主（2026-09-07 業主裁） |
| 6 | [`steps/06-diff.md`](steps/06-diff.md) | 新舊正本＋id_map | `schemas/diff-report.json`＋`schemas/cost.json` | 腳本 |
| 7 | [`steps/07-import.md`](steps/07-import.md) | 已核可正本 | rollback SQL | 腳本；⚠️ `export_batch.py`／`import_facet_knowledge.py` 擴充尚未實作（任務 7.1／7.2）；⛔ 需業主授權（D1） |

## 四閘門

⛔ 紀律本身在 hook 與既有 skill，這裡只指路：

- **G0 前提／權威來源核對**：見 [`../retrieval-improvement-loop/SKILL.md`](../retrieval-improvement-loop/SKILL.md)、
  [`rules/已否決的路.md`](../retrieval-improvement-loop/rules/已否決的路.md)、
  [`rules/該不該問業主.md`](../retrieval-improvement-loop/rules/該不該問業主.md)（步 1 intake 對齊）
- **G2 量測管線自證**：見 [`rules/量測管線自證.md`](../retrieval-improvement-loop/rules/量測管線自證.md)（步 5 reweigh 對齊）
- **G4 獨立驗證**：宣稱療效／數字／尺一律派 fresh verifier（步 6 diff／cost_ledger 對齊）
- **成本帳範圍**（2026-09-07 業主裁 (a)）：`cost_ledger.py` 只讀 `journal/` 頂層 `*.json`；M-a 試作帳（usd 15.84，業主 2026-09-06 已接受超支）封存在 `journal/m-a-archive/`（gitignored），⛔ 不要移回頂層——會讓每次收案的 Stop 以 over_budget 擋。`agentsUsed`＝代理數（組數×2＋第 3 判者），⛔ 不是 verdict 條數。
- **Stop 閘**：`.claude/hooks/outline_gate.py`——`object_under_test` 未核可、材料 sha 未凍結、或 `cost.json` 任一層超支 ⇒ 擋；步 5 有 not_available／owner_decision 格、已產 diff_report 而 `source_audit` 未核對 ⇒ 擋（步 5b）
  ⚠️ **`object_under_test`／`materials_frozen` 檢查目前為休眠閘門**：只在狀態檔 `evals_ran` 非空時才啟動；
  七步腳本目前沒有任何一支寫入 `evals_ran`，要到 `agent_eval` 整合（任務 6.4／4.3）才會有腳本寫這個鍵。

## 成本表（初值，M-a 試作後由業主核定）

| 層 | 上限 |
|---|---|
| 步 2 structure | ≤ 6 代理／$0.5 |
| 步 4 answerability | ≤ 180 代理／$3（55 格×2＋不一致第 3 判者 ≤ 55） |
| 整案 total | ≤ 240 代理／$6 |

`scripts/cost_ledger.py` 讀本檔 front matter 的 `budgets`，任一層超支 exit 2。

## StepEnvelope 契約

每步輸出共同外殼（`scripts/_envelope.py::make_envelope`）：

```python
class StepEnvelope(TypedDict):
    step: Literal["intake","structure","phrasing","answerability","reweigh","diff","import"]
    skill_version: str
    inputs_sha: dict[str, str]
    deterministic: bool
    raw_outputs_path: str | None
    cost: StepCost
    payload: dict
```

決定性步（1／3／5／6／7）：`inputs_sha`＋`skill_version` 相同 ⇒ 輸出逐位元相同。
非決定性步（2／4）：`deterministic=false`，原始輸出留 `raw/`／journal（`raw_outputs_path`；步 2 子代理、步 4 子代理判者）。

## 目錄

```text
.claude/skills/outline-curation/
  SKILL.md
  steps/01-intake.md … 07-import.md
  schemas/*.json
  scripts/_envelope.py intake.py structure_propose.py apply_proposal.py phrasing_map.py similar_items.py
          attach_phrasings.py answerability_args.py answerability_agents.py finalize_answerability.py
          merge_answerability_batches.py reweigh.py source_audit.py diff_report.py cost_ledger.py
          raw_purge.py canon_source_check.py
  journal/            （gitignored；各步成本 journal（cost_ledger 讀）；步 2／4 原始輸出在 raw/落點）
  raw/                （gitignored；講法出處原文，去識別前）
```

## 換受眾前置

換受眾（`prospect`→`property_manager`／`tenant`）前，確認：

- **`coarses-<audience>.json` 必須存在**（步 2 `structure_propose.py` 的粗目輸入；沒有就先建）。
- **`phrasing_map.py --koyu` 是售前限定材料**（F12）：問法正本只有 prospect 的版本；`--koyu` 已改為選填，
  沒有該受眾的問法正本時省略此參數即可，該來源自動跳過（`payload.counts.candidates_koyu==0`），⛔ 不報錯。
- **`source_audit.py worklist --authority` 可覆寫預設權威來源**（F12）：`DEFAULT_AUTHORITY` 是 prospect 現行值
  （jgb2 master 程式／docs、幫助中心、事實帳本），換受眾若權威來源不同，用可重複的 `--authority` 選項逐一指定，
  不給則沿用現行預設值（行為不變）。

## 隱私掃描範圍

PII 掃描覆蓋 `canon/`（正本，進版控）與 `runs/`（各步 StepEnvelope 輸出，進版控）；
`raw/` 與 `journal/` 都在 `.gitignore`，**不在掃描範圍**（不進版控就不會被 CI 的 PII 掃描檢查）。
`raw_purge.py` 依檔名日期處理 `raw/` 的 90 天保存期限。

⚠️ **`journal/*.json` 並非完全只有 counts／usd**：`journal/structure-20260906.json` 有一個 `note`
自由文字欄位（`"子代理（Agent 工具）執行；token／usd 由 harness 計、此處不估"`，查證：
`python3 -c "import json;print(json.load(open('journal/structure-20260906.json'))['note'])"`）——
是機制備註不是使用者資料，但確實不是「只有 counts／usd」；`answerability-canon*.json` 兩份確實只有
`agents[]`（`prompt_tokens`／`completion_tokens`／`usd`）＋`run_id`／`step`／`wall_s`，無文字欄位。
