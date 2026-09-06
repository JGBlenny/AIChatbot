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

## 4c. 步 5b 權威來源核對（2026-09-07 業主裁「先盤查再給我真的不確認的」）

步 5 曾把 11 格 not_available／owner_decision 直接交業主；業主指正後派 4 個唯讀 scout 對 jgb2 master（2026-09-04，乾淨）＋docs（163）＋幫助中心（92）盤查，主 session 對決策關鍵事實親自對碼。結果：**11 格只有 0 格真的需要業主判事實**。

| 狀態 | 格 | 去處 |
|---|---|---|
| verified_fact 7 | C22 簽章不收費、C39 私人／共用門鎖、C07 免費 5 物件、C24 發票自動開、C25 差額發票、C29 儲值金、C54 載具 | 帳本 `docs/knowledge/jgb-product-facts.md` 各錨點；步 6 依帳本寫售前層級句 |
| verified_absent 1 | C52 沒有「系統管理」模組 | 可答邊界題＋掛講法 |
| owner_decided 3 | C53 先不管；C31 列不足「系統支援按合約分算，金額看合約」；C15 寫一句 | 帳本已記 |

⚠️ 一個 scout 的否定結論（「程式只有電錶沒門鎖」）被主 session 對碼推翻——它只掃了 Admin 控制器。否定結論必帶正對照，已寫進 `source_audit.py check` 的硬規則（verified_absent 缺 positive_control ⇒ exit 2）。

**機制化**：skill 新增步 5b（`steps/05b-source-audit.md`、`scripts/source_audit.py worklist／check`、`schemas/source-audit.json`）；`reweigh.py` 寫 `needs_source_audit`；Stop hook：有待核對格、已產 diff_report 而 `source_audit.unaudited` 缺或 >0 ⇒ 擋。**對碼標記**：細目 `sources` 含 `docs:knowledge/jgb-product-facts.md#` ⇒ 已對碼；coverage-map `_meta.fines_verified_against_code／fines_unverified`，`status.py` 印「已對碼 x／37」（現況 0／37，步 6 回填後更新）。紀錄：`inputs/source-audit-20260907.json`、工作單 `inputs/source-audit-worklist-20260907.json`。

**verifier CONFIRMED（步 5b）附帶已知債（P3，不擋）**：`source_audit.py check` 的證據只驗形狀（`path:symbol`）不解析路徑是否存在；`owner_decided` 只需 `owner_decision` 字串、不需證據——閘門證明「有紀錄」不證明「查過」，查過與否靠主 session 親自對碼的紀律；`diff_report` 用真值判斷（空 dict 會繞過，實務不會空）。

## 4d. 步 6 diff：售前草稿 v3（2026-09-07；fresh verifier CONFIRMED）

- 草稿：`inputs/prospect.draft.v3-20260907.md`（38 細目；**11 個帶對碼標記** `docs:knowledge/jgb-product-facts.md#…`；PII 掃描 0 命中、正對照命中）。⛔ 未放 `rag-orchestrator/canon/`、未入庫——交業主審後步 7 才放。
- 改了什麼：10 個細目回填事實（C22 簽章不收費、C03 包租 vs 代管、C24／C54 發票自動開與載具、C29 儲值金、C25 差額發票、C39 兩型門鎖、C52 沒有「系統管理」＋掛講法、C15 標籤、C07 免費 5 物件、C43 匯入範圍改正）＋新增 `G/utility-split-advice`（C31 業主一句）。verifier 抓兩句越過帳本邊界（「屬方案內容的一部分」「不用人工對帳」）已收緊。
- diff-report：`runs/2026-09-06T00-00-00Z/diff-report.json`——新增 1 細目、無刪無改名；`replacements[]` 43（content 35＝keep 29＋split 5＋new 1、merged_into 8）；id_map `inputs/id-map-20260907.json` 由步 2 `prospect.idmap2.json` 決定性轉換（42＋1）。
- ⚠️ 判者裁定綁的是 v2 sha（`da786d73…`）；v3 內容變了，**改動的 11 細目對應的格要重跑步 4 才能更新 coverage-map 的對碼標記**（reweigh 的 sha fail-loud 會擋 v3，這是對的）。
- **成本帳擋收案**：`cost_ledger` 彙總 journal 全部檔案，M-a 試作 $15.84（步預算 $3、整案 $6）⇒ `cost.over_budget=true`、Stop hook 擋。design E4「預算初值待 M-a 後核」未做。待業主：(a) M-a 3 份 journal 移 `journal/m-a-archive/`＋修 P3 agents 計數（建議）／(b) 重設 SKILL 預算／(c) 維持。
- **業主裁（2026-09-07）**：成本帳選 (a)——M-a 三份 journal 封存 `journal/m-a-archive/`，P3 計數已修（journal agents 113→23、cost agents 27／usd 0、over_budget=false）；**C46 算可答**（「6 國語系」句），已在 v3 掛講法「有多語系介面嗎」「外籍租客能用嗎」。
- hook 補防死結：Stop 同一組條件連擋 3 次未變 ⇒ 第 4 次交還給人（`_stop_block`），回歸鎖 `test_gate5_stop_unchanged_blocks_pause_after_three`。

## 4e. v3 重跑步 4＋reweigh（2026-09-07，業主：直接重跑）

| | v2（審查版） | v3（回填後） |
|---|---|---|
| 一致率 | 52／55＝0.945（3 格第 3 判者） | **55／55＝1.000**（無第 3 判者；22 判者，$0） |
| 去向 | fine 39／deliberate_no 5／not_available 5／owner_decision 6 | **fine 49／deliberate_no 5／not_available 1**（C53，業主裁不管） |
| 補法 | add_knowledge 14／add_phrasing 13／cross_audience 4／list_not_available 5／null 19 | add_knowledge 15／add_phrasing 17／list_not_available 1／null 22 |
| 缺口類 | retrieval_gap 15／content_gap 2 | retrieval_gap 21／content_gap 3（map-v2 對 kb 的舊量測，待正本索引後重跑） |
| 對碼標記 | 0／37 | **11／38** |

13 格翻正：C03、C43（partial→answerable）；C07、C15、C22、C24、C25、C39、C52、C54（no_source→answerable）；C29、C31（no_source→partial）；**C46 answerable→partial**（兩判者一致；業主裁「算」——去向仍 fine，補法標 add_knowledge，留給業主審正本時決定是否把多語系獨立成句）。
產物：`runs/2026-09-06T00-00-00Z/answerability-canon-v3.json`、`coverage-reweigh-v3.json`；`inputs/coverage-map-v3-20260907.json`、`source-audit-worklist-v3-20260907.json`、`source-audit-v3-20260907.json`（C53 owner_decided）；raw `raw/answerability-v3-20260907/`（gitignored）。cost：agents 49／usd 0、over_budget=false。

## 5. 下一步

步 6 `diff_report.py`（`replacements[]` old kb id → fine id；用本檔 `fines_referenced` 與 kb 來源對照）→ `rag-orchestrator/canon/prospect.md` 草稿＋`export_json` → 交業主（⛔ 不 commit 正本、⛔ 不入庫）。業主已裁（2026-09-07）：C53 不管、C31 一句說法、C15 寫、C46 算可答；v3 已回填並重判（§4e）。下一步＝業主審 v3 全文 → 步 7（放 canon/prospect.md＋export_json，⛔ 需業主授權 D1）。

## 6. 查證指令

```
SPEC=.kiro/specs/knowledge-outline-and-intent-architecture
python3 .claude/skills/outline-curation/scripts/reweigh.py --canon $SPEC/inputs/prospect.draft.review-20260907.md \
  --demand .kiro/specs/presales-grounding-gate/coverage-map/demand-v2.json --map .kiro/specs/presales-grounding-gate/coverage-map/map-v2.json \
  --answerability .claude/skills/outline-curation/runs/2026-09-06T00-00-00Z/answerability-canon.json \
  --coverage-out /tmp/cm.json --out /tmp/env.json && diff <(python3 -c "import json;print(json.dumps(json.load(open('/tmp/cm.json'))['cells'],sort_keys=True))") <(python3 -c "import json;print(json.dumps(json.load(open('$SPEC/inputs/coverage-map-20260907.json'))['cells'],sort_keys=True))") && echo 決定性一致
scripts/run-tests.sh unit tests/unit/skills/outline_curation/test_outline_curation_reweigh_req.py tests/unit/_meta/test_outline_gate_req.py
```
