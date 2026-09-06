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
2 structure     腳本→API  3 角度提議（提問路徑／內容邊界／受眾層級）各一獨立請求 → 第 4 請求合成
   ↓                      → steps/02-structure.md（2.3 實作；Workflow 版留參考）
3 phrasing      腳本+人審 講法／缺口格掛回細目；相似細目待審清單
   ↓
4 answerability 腳本→API  每格 2 判者（獨立請求）、不一致加第 3；schema 強制、journal 續跑
   ↓                      → steps/04-answerability.md（1.6 answerability_judge.py；Workflow 版留參考）
5 reweigh       腳本      呼叫 tools/gapmap/coverage_map.py 重量
   ↓
6 diff          腳本      結構差異＋id 對應表＋取代對應表＋成本（G4 獨立驗證）
   ↓
7 import        腳本      業主核可後：正本 commit → export_batch → import_facet_knowledge
                          ⛔ 需業主授權（D1）
```

## 七步

| 步 | 檔案 | 輸入 | 輸出 schema | 形態 |
|---|---|---|---|---|
| 1 | [`steps/01-intake.md`](steps/01-intake.md) | kb 列／草稿／缺口地圖／既有正本 | `schemas/intake.json` | 腳本 |
| 2 | [`steps/02-structure.md`](steps/02-structure.md) | intake.json | `schemas/structure-proposal.json` | 腳本直打 API（2.3；決策 7 修訂） |
| 3 | [`steps/03-phrasing.md`](steps/03-phrasing.md) | structure-proposal.json | `schemas/phrasing-map.json` | 腳本＋人審 |
| 4 | [`steps/04-answerability.md`](steps/04-answerability.md) | phrasing-map.json | `schemas/answerability.json` | 腳本直打 API（1.6 `answerability_judge.py`） |
| 5 | [`steps/05-reweigh.md`](steps/05-reweigh.md) | answerability.json | `schemas/coverage-reweigh.json` | 腳本 |
| 6 | [`steps/06-diff.md`](steps/06-diff.md) | 新舊正本＋id_map | `schemas/diff-report.json`＋`schemas/cost.json` | 腳本 |
| 7 | [`steps/07-import.md`](steps/07-import.md) | 已核可正本 | rollback SQL | 腳本；⛔ 需業主授權（D1） |

## 四閘門

⛔ 紀律本身在 hook 與既有 skill，這裡只指路：

- **G0 前提／權威來源核對**：見 [`../retrieval-improvement-loop/rules/`](../retrieval-improvement-loop/README.md)（步 1 intake 對齊）
- **G2 量測管線自證**：見同上（步 5 reweigh 對齊）
- **G4 獨立驗證**：宣稱療效／數字／尺一律派 fresh verifier（步 6 diff／cost_ledger 對齊）
- **Stop 閘**：`.claude/hooks/outline_gate.py`——`object_under_test` 未核可、材料 sha 未凍結、或 `cost.json` 任一層超支 ⇒ 擋

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
非決定性步（2／4）：`deterministic=false`，原始輸出留 `raw/`／journal（`raw_outputs_path`；步 2 子代理、步 4 API 判者）。

## 目錄

```text
.claude/skills/outline-curation/
  SKILL.md
  steps/01-intake.md … 07-import.md
  schemas/*.json
  scripts/_envelope.py intake.py diff_report.py cost_ledger.py
  journal/            （gitignored；各步成本 journal（cost_ledger 讀）；步 2／4 原始輸出在 raw/落點）
  raw/                （gitignored；講法出處原文，去識別前）
```
