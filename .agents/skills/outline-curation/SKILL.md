---
name: outline-curation
description: 完善大綱（正本粗目／細目／講法）的七步決定性流程——intake→structure→phrasing→answerability→reweigh→diff→import。每步輸出 StepEnvelope 化 JSON，只產待審清單，⛔ 不自動合併、⛔ 不自動入庫。用於新建或重切某受眾的知識正本大綱。
version: "0.1.0"
budgets:
  feature_surface:
    agents: 4
  structure:
    agents: 6
  answerability:
    agents: 180
  total:
    agents: 240
---

# 完善大綱 skill

⛔ **本檔只承載流程全圖、七步表、四閘門索引與成本表。紀律本身住在 hook
（`.claude/hooks/outline_gate.py`）與 `../retrieval-improvement-loop/rules/`——這裡只指連結，不複製。**

## 流程全圖

```text
0 page-surface   腳本→子代理 基準＝JGB 頁面樹（DSP-065）；功能全表當粒度對照；子代理逐格判 covered／partial／missing；橋 surface_to_cells.py 轉成步 4／5 的格 → steps/00-feature-surface.md
   ↓
0c topic-first   子代理     DSP-067：骨架（架→粗目＝產品功能）業主核可後，每架 executor 起草細目（一件可問的事、每句對釘住 commit／幫助中心）＋fresh verifier 逐句對源；render_drafts.py 人讀版、outline_summary.py 總表與待裁 → steps/00c-topic-first-drafting.md
   ↓
1 intake        腳本      讀輸入、凍結 sha、產「受測物定義清單」骨架
   ↓
2 structure     腳本→子代理 3 角度提議（產品功能面／內容邊界／受眾層級）各一子代理 → 第 4 個子代理合成
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

重切模式（任務 9.3⑤，從既有正本重切；9.6 S4／DSP-058 起正本為圖書館形態——`rag-orchestrator/canon/jgb/`
一目錄＋九架，⛔ 不再有 `prospect.md`／`property_manager.md` 兩份單檔）：步 1 `--canon rag-orchestrator/canon/jgb`
＋`--exclude <排除清單.json>`（`structure_propose.py prepare` 與 `intake.py` 皆同支援，與 `--kb-rows`／`--kb-json`
二擇一；`--canon` 也接單檔，供讀取已退役的封存正本）→ 步 2 照常（子代理提議＋合成；產出前可先跑
`structure_review_sheet.py` 出歸屬審核單交業主）→ `apply_proposal.py --canon rag-orchestrator/canon/jgb --out <目錄>`
（依 `id_map` 逐條決定屬性去留，見該檔 `render_remap` docstring；產出恆為九架＋`CATALOG.md`＋`jgb.json`；
`--version`／`--scopes`／`--out-idmap`／`--out-pending-dir` 皆有預設，最小可只給 `--canon`／`--proposal`／`--out`）→
步 3 **先消化 `pending-phrasings.json`**（拆分來源的講法沒有自動歸位）。

## 七步

| 步 | 檔案 | 輸入 | 輸出 schema | 形態 |
|---|---|---|---|---|
| 0 | [`steps/00-feature-surface.md`](steps/00-feature-surface.md) | jgb2 分支（頁面樹＋功能全表）／幫助中心／既有正本 | `schemas/page-surface.json`（0a 基準）＋`schemas/feature-surface.json`（0a 對照）＋`schemas/feature-coverage.json`（0b）＋`surface_to_cells.py` 產 `cells.json`／`map.json`（步 4／5 輸入） | 腳本（0a）＋唯讀子代理（0b）；業主 2026-09-18「應該是 skill 的一個環節」 |
| 0c | [`steps/00c-topic-first-drafting.md`](steps/00c-topic-first-drafting.md) | 骨架（粗目＋頁） | `runs/outline-<日期>/drafts-<架>.json` | 每架一 executor 起草＋一 verifier 逐句對源（DSP-067） |
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
- **hook `check_phrasing_unique`（任務 9.1c）**：同一句講法文字（NFKC）不得掛兩個細目；`apply_proposal.py --canon`
  重切套用時已自行先擋一次（exit 2），hook 是進版控前的第二道防線
- **parser `target_user` 值域＋`see_also` 存在性（任務 9.1a）**：`canon_parser.parse_canon_text` 對兩者皆
  fail-loud；`apply_proposal.py --canon` 產出後一律回讀（`parse_canon_text`），值域／存在性錯誤在此擋下
- **成本帳範圍**（2026-09-07 業主裁 (a)：**預算按每次 run**——`cost_ledger.py --run-id <id>`／`--run-prefix <pfx>` 只計該次 run 的 journal；不帶參數＝整案累進，只作歷史總覽）：`cost_ledger.py` 只讀 `journal/` 頂層 `*.json`。`agentsUsed`＝代理數（組數×2＋第 3 判者），⛔ 不是 verdict 條數。
- **Stop 閘**：`.claude/hooks/outline_gate.py`——`object_under_test` 未核可、材料 sha 未凍結、或 `cost.json` 任一層超支 ⇒ 擋；步 5 有 not_available／owner_decision 格、已產 diff_report 而 `source_audit` 未核對 ⇒ 擋（步 5b）
  ⚠️ **`object_under_test`／`materials_frozen` 檢查目前為休眠閘門**：只在狀態檔 `evals_ran` 非空時才啟動；
  七步腳本目前沒有任何一支寫入 `evals_ran`，要到 `agent_eval` 整合（任務 6.4／4.3）才會有腳本寫這個鍵。

## 代理數上限（每次 run；主機記憶體的並行限制，⛔ 不是模型能力限制。上限值源自 8 GB 主機時期；2026-10-15 主機已升 24 GB，待實測後再調）

| 層 | 上限 |
|---|---|
| 步 2 structure | ≤ 6 代理 |
| 步 4 answerability | ≤ 180 代理（格數×2 判者＋不一致第 3 判者；格數＝步 0 橋產出的 cells） |
| 整案 total | ≤ 240 代理 |

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
  steps/00-feature-surface.md 01-intake.md … 07-import.md
  schemas/*.json
  scripts/_envelope.py page_surface.py page_coverage_batches.py page_coverage_report.py outline_gap_map.py render_drafts.py outline_summary.py feature_surface.py feature_coverage_check.py surface_to_cells.py intake.py structure_propose.py apply_proposal.py phrasing_map.py similar_items.py
          attach_phrasings.py answerability_args.py answerability_agents.py save_verdict.py finalize_answerability.py
          merge_answerability_batches.py reweigh.py source_audit.py diff_report.py cost_ledger.py
          raw_purge.py canon_source_check.py remap_ids.py canon_items.py structure_review_sheet.py
  journal/            （gitignored；各步成本 journal（cost_ledger 讀）；步 2／4 原始輸出在 raw/落點）
  raw/                （gitignored；講法出處原文，去識別前）
```

## 擴充模式（一架一輪，brief-9.7，2026-09-16）

補內容不重切：既有架內細目原樣 keep，新材料（kb 列＋幫助中心頁）提成新細目，其餘八架逐位元不動。

```bash
S=.claude/skills/outline-curation; R=$S/runs/<架>-<日期>
# 材料：kb 列 {"rows":[{kb_id,question_summary,answer}]}；幫助中心頁 [{id:"help:<slug>",summary,text}]
python3 $S/scripts/intake.py            --canon rag-orchestrator/canon/jgb --kb-json $R/kb-rows.json --drafts $R/help-pages.json --shelf A --out $R/intake.json --frozen-at <ISO>
python3 $S/scripts/structure_propose.py prepare --canon rag-orchestrator/canon/jgb --kb-rows $R/kb-rows.json --drafts $R/help-pages.json --shelf A --coarses $S/schemas/coarses-jgb.json --out-dir $R/structure
#   → 三角度子代理＋合成（同步 2）；提議每細目必填 target_user、op（keep／merge／split／new）；材料屬他架 ⇒ out_of_shelf
python3 $S/scripts/apply_proposal.py    --shelf A --canon rag-orchestrator/canon/jgb --kb-rows $R/kb-rows.json --drafts $R/help-pages.json --proposal $R/structure-proposal.json --out /tmp/jgb-A
#   → 九架＋CATALOG＋jgb.json＋id_map＋pending/（pending-content.json＝幫助中心頁提成的細目，標題有、內容空，等人／代理撰寫）
```

規則：`op=new` 且來源全是 `tmp:kb:*` ⇒ 內容＝各列 answer 切句依序串接、`sources: [kb:<id>…]`、無 `reviewed`（補審前不可見）；來源含 `tmp:draft:*` ⇒ 零內容＋進 `pending-content.json`；**既有細目吸收新材料**（`op=merge`，`merge_of` 含 `tmp:canon:` 與 `tmp:kb:`／`tmp:draft:`）⇒ 既有內容與講法保留、kb 句接在後面、sources 追加、`reviewed` 丟棄（內容變即待審）、含草稿另記 pending-content；新 id 與任何架既有 id 撞、缺 `target_user`、`coarse_id≠--shelf`、來源不在材料 ⇒ exit 2 且**不落任何輸出檔**（先渲染到暫存、`parse_canon_dir` 回讀過才搬到 `--out`，`--out` 須為空）。

## 受眾＝細目屬性，不換檔

9.6 S4／DSP-058 後正本是**一份圖書館**（`rag-orchestrator/canon/jgb/`，一目錄＋九架），`prospect`／
`property_manager` 不再各自一份檔案——受眾差異落在每個細目自己的 `target_user`（陣列，值域僅這兩者，
兩者共用的細目明列兩者）。⛔ 沒有「換受眾」這個動作：重切／新增知識一律對同一份 `canon/jgb/` 操作，
差別只在某細目的 `target_user` 填什麼。步 2 `structure_propose.py` 的粗目輸入固定是
`schemas/coarses-jgb.json`（九碼，兩受眾共用同一份，⛔ 不分檔）。

- **`phrasing_map.py --koyu` 是售前限定材料**（F12）：問法正本只有 prospect 的版本；`--koyu` 已改為選填，
  沒有 prospect 講法時省略此參數即可，該來源自動跳過（`payload.counts.candidates_koyu==0`），⛔ 不報錯。
- **`source_audit.py worklist --authority` 可覆寫預設權威來源**（F12）：`DEFAULT_AUTHORITY` 是 prospect 現行值
  （jgb2 master 程式／docs、幫助中心、事實帳本），若某細目的權威來源不同，用可重複的 `--authority` 選項逐一指定，
  不給則沿用現行預設值（行為不變）。

## 隱私掃描範圍

PII 掃描覆蓋 `canon/`（正本，進版控）與 `runs/`（各步 StepEnvelope 輸出，進版控）；
`raw/` 與 `journal/` 都在 `.gitignore`，**不在掃描範圍**（不進版控就不會被 CI 的 PII 掃描檢查）。
`raw_purge.py` 依檔名日期處理 `raw/` 的 90 天保存期限。

