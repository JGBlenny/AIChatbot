# M-b 2.6／步 5 reweigh 報告：55 格 → 去向（2026-09-07）

> **結論先講：55／55 有去向、無來源細目 0，步 0／步 5 出口達成；分佈與 Plan §7.6 推算逐項相符。** 工具 `rag-orchestrator/tools/gapmap/coverage_map.py`、步 5 `scripts/reweigh.py`、Stop hook 兩條出口、`status.py` 摘要皆落地；容器 unit 綠。Plan：`inputs/plan-2.6-coverage-map-20260907.md`（業主核准 (a)，三輪 plan-verifier 的 P2 全部 FIX）。

## 1. 數字（真材料一跑；`python3 scripts/status.py` 亦印）

| 項目 | 值 |
|---|---|
| 去向 | fine 39／deliberate_no 5／not_available 5／owner_decision 6 |
| 補法 | add_knowledge 14／add_phrasing 13／cross_audience_rewrite 4／list_not_available 5／null 19 |
| 缺口類（R3.5，可並列） | retrieval_gap 15（有知識但撈不到）／content_gap 2（回答未含必含：C43、C45） |
| 判者一致率（R3.4，逐格重算） | 0.945；C24／C30／C46 各 2/3，其餘 1.0 |
| 無去向格／無來源細目 | 0／0 |
| 合併提案（⛔ 不合併） | 1：`C/contract-esign-flow` ↔ `C/contract-templates`（see_also 互指且皆為正解） |
| 輸入 sha | canon `da786d73…`、demand／map／answerability 見 `coverage-map-20260907.json._meta.inputs_sha` |

## 2. 每桶是哪些格

- **not_available 5（列現有不足，進 G 一句對外說法）**：C22 簽約另外收費、C31 水電費怎麼分算、C39 私人門鎖 vs 共用門鎖、C52 系統管理模組有哪些功能、C53 單合約與雙合約。
- **owner_decision 6**：跨受眾改寫 4（C15 物件自訂標籤、C25 差額發票、C29 儲值金回充、C54 手機條碼載具；map-v2 `V`＝對題列只在 prospect 池外，只給草稿路徑 `canon/drafts/cross-audience/<cell>.md`，⛔ 不開放列）；有權威來源可寫 2（C07 免費方案物件數 `kb:5373 池外`、C24 電子發票自動開 `kb:3601`）。
- **add_phrasing 13**：判者可答但 9/4 對 kb 量測撈不到（C01、C02、C08、C12、C14、C17、C21、C27、C33、C34、C37、C41、C42、C44、C46 中不含 content_gap／partial 的 13 格）。⚠️ 這是對 **kb** 的舊量測，最小驗證＝正本索引建好後用 `demand.questions` 重跑檢索（元件 10 步 1），⛔ 不是憑舊量測補講法。
- **C47 聯絡業務／demo**：answerable、cause_state `CTA`、coverage 未覆蓋、`fix_type=null`——量測層未覆蓋但無補法（CTA 由程式附加，R4.5），⛔ 不得讀成已覆蓋。
- **P6 八格**：C22／C39／C52／C53 → not_available；C25／C29／C54 → cross_audience_rewrite；C46 → fine＋add_phrasing（判可答但撈不到）。

## 3. 與 design 的偏離（Plan §8，業主已核）

1. `fix_type` 允許 `null`（已覆蓋／刻意不補無補法）。
2. `cross_audience_rewrite` 判準＝map-v2 `cause_state=="V"`；第二份正本出現後改判準＝新 readiness epoch。
3. `map-v2.json` 為第四份輸入（design 元件 9 簽名無）；建議回寫 design。
4. `gap_classes` 新欄位（R3.5 兩類可並列）。

## 4. fail-loud（⛔ 不填預設）與測試

`CoverageMapError` → exit 2：判者裁定的正本 sha ≠ 本次正本；fine_id ∉ 正本；格缺席；label 非四值；`g0.authority` 形狀不在 `kb:`／`help:`／`none`／`n/a`。`needs_rubric_revision=true` ⇒ `reweigh.py` 不重量、exit 2（E6）。
測試：`tests/unit/skills/outline_curation/test_outline_curation_reweigh_req.py`（規則表 11 列各一案、決定性、judge_agreement、三條正對照、authority 未知形狀、envelope schema＋state、rubric 旗標雙向、無來源細目 exit 2）；`tests/unit/_meta/test_outline_gate_req.py::test_gate5_stop_reweigh_exits_block_and_zero_allows`。

## 4b. verifier CONFIRMED 附帶 P4（不擋，記錄）

- `schemas/coverage-reweigh.json` 的 `payload.cells.items` 只是 `{"type":"object"}`，假 disposition 只被工具自己的出口擋；待收緊 enum。
- C24（電子發票自動開）判者 no_source 但 map-v2 `cause_state=S_OK`：Plan §9 停損形狀，僅 1 格（<5）不停；已落 owner_decision／add_knowledge（`kb:3601`），業主審時順帶看。

## 5. 下一步

步 6 `diff_report.py`（`replacements[]` old kb id → fine id；用本檔 `fines_referenced` 與 kb 來源對照）→ `rag-orchestrator/canon/prospect.md` 草稿＋`export_json` → 交業主（⛔ 不 commit 正本、⛔ 不入庫）。業主待裁：not_available 5 格的 G 段一句說法；跨受眾 4 格是否改寫；C46 核句。

## 6. 查證指令

```
SPEC=.kiro/specs/knowledge-outline-and-intent-architecture
python3 .claude/skills/outline-curation/scripts/reweigh.py --canon $SPEC/inputs/prospect.draft.review-20260907.md \
  --demand .kiro/specs/presales-grounding-gate/coverage-map/demand-v2.json --map .kiro/specs/presales-grounding-gate/coverage-map/map-v2.json \
  --answerability .claude/skills/outline-curation/runs/2026-09-06T00-00-00Z/answerability-canon.json \
  --coverage-out /tmp/cm.json --out /tmp/env.json && diff <(python3 -c "import json;print(json.dumps(json.load(open('/tmp/cm.json'))['cells'],sort_keys=True))") <(python3 -c "import json;print(json.dumps(json.load(open('$SPEC/inputs/coverage-map-20260907.json'))['cells'],sort_keys=True))") && echo 決定性一致
scripts/run-tests.sh unit tests/unit/skills/outline_curation/test_outline_curation_reweigh_req.py tests/unit/_meta/test_outline_gate_req.py
```
