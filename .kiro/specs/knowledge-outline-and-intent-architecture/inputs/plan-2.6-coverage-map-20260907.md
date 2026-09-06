# Plan 切片 KOIA-2.6：`tools/gapmap/coverage_map.py` 初版＋skill 步 5 `reweigh.py`＋步 0 出口（2026-09-07）

> 狀態：**業主核准 (a)（2026-09-07）→ 實作中（主 session、TDD、容器內 unit）→ 完成後 fresh verifier**。前史：三輪 plan-verifier 皆 REVISE（各一批 P2，全部 FIX 進本文：①fine_id 與正本綁定＋judge_agreement 逐格；②`add_phrasing` 列＋優先序；③`g0.authority` 哨兵判準）。依規約收尾審查後不自動再開；業主可 (a) 直接核准本版、(b) 指示再開一輪 fresh review、(c) 停。核准前 ⛔ 不寫碼。對應 tasks.md 2.6、design 元件 9／元件 1 步 5／E6、需求 R3.1–R3.7。

## 0. 結論先講

把「55 格 → 去向」做成一支決定性、$0、不碰 DB 的工具：輸入四份已存在的凍結材料（正本審查版、`demand-v2.json`、`map-v2.json`、`answerability-canon.json`），輸出每格一筆 `CellRecord`；skill 步 5 腳本包成 envelope，Stop hook 多查兩條出口。**主 session 親做（TDD、容器內 unit），完成後派 fresh verifier。**

## 1. 結果（outcome）

1. `tools/gapmap/coverage_map.py`：`reweigh(canon, demand_path, map_path, answerability_path) -> list[CellRecord]`（design 元件 9 簽名無 `map_path`，新增屬偏離，見 §8.3）＋CLI `--canon --demand --map --answerability --out coverage-map.json`。
2. `.claude/skills/outline-curation/scripts/reweigh.py`：呼叫上者，寫 `runs/<ts>/coverage-reweigh.json`（schema `schemas/coverage-reweigh.json`，已存在）；讀到 `answerability.needs_rubric_revision=true` ⇒ **exit 2**（E6）；`update_state` 寫 `reweigh: {path, cells_without_disposition, fines_without_sources}`。
3. `.claude/hooks/outline_gate.py` `check_stop`：`reweigh.cells_without_disposition>0` 或 `reweigh.fines_without_sources>0` ⇒ 擋。
4. `scripts/status.py` 新增 `print_coverage()`：讀最新 `coverage-map.json`（無 DB），印去向／補法分佈。
5. 用真材料跑一次 → `inputs/coverage-map-20260907.json`＋一段摘要附進 `inputs/m-b-answerability-20260907.md` §7 或新報告節。

## 2. 輸入（全部已存在、sha 可凍結）

| 材料 | 路徑 | 用到的欄位 |
|---|---|---|
| 正本審查版 | `inputs/prospect.draft.review-20260907.md`（sha `da786d73407b…`；用 `services.agent.canon.canon_parser.parse_canon`） | `FineItem.id/title/sources/policy/policy_ref/see_also` |
| 需求格 | `.kiro/specs/presales-grounding-gate/coverage-map/demand-v2.json`（55 格） | `id/module/topic/questions/policy/policy_ref/rubric/g0.authority` |
| 量測層 | `.kiro/specs/presales-grounding-gate/coverage-map/map-v2.json`（55 格，2026-09-04 對 kb 實測） | `cause_state/entry_state/coverage`（沿 `_meta.states` 三態） |
| 判者裁定 | `.claude/skills/outline-curation/runs/2026-09-06T00-00-00Z/answerability-canon.json` | `payload.labels[].{cell_id,label,fine_id}`、`needs_rubric_revision` |

`audience`＝正本 front matter `audience`（prospect）；`topic`＝demand 的 `topic`。

**輸入一致性（fail-loud，⛔ 不填預設）**：
- `answerability.inputs_sha.canon` ≠ 本次實際解析正本的 sha256（Markdown 位元組）⇒ **exit 2**（判者裁定的是另一版正本）。
- 任一 `labels[].fine_id` 非 null 且 ∉ `{FineItem.id}` ⇒ **exit 2**（去向指向不存在細目）。
- 任一 demand 格在 answerability 或 map-v2 缺席、或 label 非四值 ⇒ **exit 2**。

## 3. 去向與補法的決定性規則（R3.1／R3.7；⛔ 不看被驗系統排序，裁定 10）

| 判者 label | 附加條件 | disposition | fine_id | fix_type | 說明 |
|---|---|---|---|---|---|
| answerable | `content_gap`（§4） | `fine` | 判者 fine_id | `add_knowledge` | 有答但內容未含必含 |
| answerable | 非 content_gap ∧ `retrieval_gap`（§4） | `fine` | 判者 fine_id | `add_phrasing` | 有知識但撈不到（實例：C08 判 answerable、map-v2 `V`）|
| answerable | 非 content_gap ∧ 非 retrieval_gap | `fine` | 判者 fine_id | `null`（無需補法） | 已覆蓋 |
| partial | — | `fine` | 判者 fine_id | `add_knowledge` | 有細目但只答一部分（內容缺優先於講法缺；若同時 retrieval_gap，`gap_classes` 仍兩者都列） |
| no_source | `cause_state == "V"`（對題列只在 prospect 池外） | `owner_decision` | null | `cross_audience_rewrite`＋`draft_path` 建議值 | R3.6：以 Y 的知識改寫成 X 層級成草稿，⛔ 不直接開放 |
| no_source | 非 V 且 `has_authority(g0.authority)` | `owner_decision` | null | `add_knowledge` | 有權威來源可寫（N_CAND；實例 C07、C24） |
| no_source | 非 V 且 ¬`has_authority` | `not_available` | null | `list_not_available` | 進 G「現有不足」一句對外說法（實例 C22、C31、C39、C52、C53） |
| deliberate_no | 正本或 demand 有 `policy_ref` | `deliberate_no` | null | `null` | 符合（刻意不補） |
| deliberate_no | 無 `policy_ref` | `owner_decision` | null | `owner_decision` | 刻意不補但沒依據 ⇒ 交裁 |
| 判者缺該格／label 非四值／fine_id ∉ 正本／canon sha 不符 | — | **exit 2**（fail loud，⛔ 不填預設） | | | 正對照 unit（§7.3） |

**`has_authority` 決定性謂詞**（demand-v2 的 `g0.authority` 是自由文字，55 格無一空值，「沒有」用哨兵）：`t = authority.strip()`；`t` 以 `kb:` 或 `help:` 開頭 ⇒ True；以 `none` 或 `n/a` 開頭 ⇒ False；**其他形狀在 no_source 列 ⇒ exit 2**（⛔ 不預設有來源；實查其他形狀只出現在 deliberate_no／CTA 格，不會走到這兩列）。

**`fix_type` 優先序**（單值，R3.7）：`add_knowledge`（content_gap 或 partial）＞ `add_phrasing`（retrieval_gap）＞ `null`；缺口分類另存 `gap_classes: list["content_gap"|"retrieval_gap"]`，可同時多值，兩欄一致性由 §7.6 檢查。

`fix_type` 允許 `null`，是對 design 元件 9 `Literal[…]` 的一處放寬：已覆蓋與刻意不補的格沒有補法可填，硬塞六值之一會把「不用修」寫成「要修」。**待業主核**（見 §8）。

`merge_similar`：本版只在 `see_also` 互指且兩細目同被不同格判為正解時提案（C02／C23／C30 的 billing-overview 叢集會命中），⛔ 不合併。

## 4. R3.5 兩類分報（用 map-v2 的量測層，⛔ 不重跑系統）

- `retrieval_gap`（有知識但撈不到）：`disposition==fine` ∧ (`cause_state ∈ {S, V, FALSE_HIT}` ∨ `cause_state.startswith("UNSTABLE")`)。map-v2 實值含 `UNSTABLE['S', 'S_OK']`、`UNCLASSIFIED(待G0)`、`CTA`、`ADVICE`，比對一律**精確字串或明寫前綴**；§3 的 `V` 用精確相等（實查含 V 字的值只有 `V` 與 `ADVICE`，無誤落）。
- `content_gap`（回答未含必含）：`disposition==fine` ∧ `coverage ∈ {未覆蓋(回答未含必含), 已覆蓋⚠️}`。
- `gap_classes` 兩者可並列；決定 `fix_type` 時 content_gap 先判（entry 已答但內容缺）。⚠️ map-v2 的 cause_state 是 2026-09-04 對 **kb** 量的，不是對正本索引；`add_phrasing` 的 `min_verification` 因此＝「正本索引建好後用 `demand.questions` 重跑檢索，預期 `expected_fine_id`」（元件 10 步 1），⛔ 不是憑 kb 舊量測補講法。
- `min_verification`＝`{"phrasings": demand.questions, "expected_fine_id": fine_id}`。
- `judge_agreement`（R3.4）**逐格**由 `answerability.payload.labels[].verdicts[]` 決定性計算：`＝ 與終判 label 相同的 verdict 數 ／ verdict 數`（實查：每格 2–3 筆、共 113 筆；三格分歧 C24／C30／C46 各為 2/3，其餘 1.0）；全域一致率＝`labels` 中 verdicts 兩兩 label 全同的格數／55（＝0.945，可重算）。全域值與 sha 寫在 `coverage-map.json` 的 `_meta`；envelope `payload` 只放 `cells`（`schemas/coverage-reweigh.json` 的 `payload` 為 `additionalProperties:false`）。

## 5. 出口（步 0／步 5；Stop hook 亦查）

- `cells_without_disposition == 0`（55 格皆有去向；缺任何一格 ⇒ 工具 exit 2）。
- `fines_without_sources == 0`（正本 37 細目 `sources` 皆非空；現況實查 0）。

## 6. 非目標

- 不回填 `entry_state`／`answered`（那是 `agent_eval` 實跑，元件 10）；不碰 DB；不建 LINE 受眾；不自動合併細目；不改 rubric；不動 `phrasing_map.py`、`answerability_*`。
- `cross_audience_rewrite` 的草稿內容不在本版產生，只產 `draft_path` 建議路徑。

## 7. 驗收（acceptance；容器內跑）

1. **同輸入兩次逐位元相等**（決定性）。
2. 規則表每列一案（answerable×{content_gap／retrieval_gap（cause_state="V"）／無}／partial／no_source×V／×authority／×無／deliberate_no±policy_ref），fixture 用最小正本 md＋3 格 demand／map／answerability。
3. **正對照**：故意拿掉一格的判者列 ⇒ exit 2；把一筆 `fine_id` 改成不存在的 id ⇒ exit 2；竄改 `inputs_sha.canon` 一位元 ⇒ exit 2；未竄改 ⇒ 綠；`needs_rubric_revision=true` ⇒ `reweigh.py` exit 2、`false` ⇒ 通過（tasks 2.6 明列）。
4. envelope 過 `schemas/coverage-reweigh.json` 校驗；`payload.cells` 每筆有 `disposition`。
5. hook：state `reweigh.cells_without_disposition=1` ⇒ `check_stop` 回非空；`=0` ⇒ 空（沿用 `test_outline_gate_req.py` 的 subprocess 驅動）。
6. 真材料跑一次：55／55 有去向；**`gap_classes` 含 `retrieval_gap` 且 `fix_type=null` 的格數＝0**；三格分歧的 `judge_agreement` 為 2/3、其餘 1.0，且由每格值重算的全域值＝0.945；分佈預期（由 §3 規則對現有 label＋map-v2＋demand 推）：`fine` 39（28 answerable＋11 partial）、`deliberate_no` 5、`not_available` **5**（C22／C31／C39／C52／C53）、`owner_decision` **6**（`cross_audience_rewrite` 4：C15／C25／C29／C54；`add_knowledge` 2：C07／C24）；C47（answerable、cause_state `CTA`、coverage 未覆蓋）`fix_type=null` 但報告要註明「量測層未覆蓋、無補法（CTA 由程式附加）」，⛔ 不得寫成已覆蓋；每個數字寫進報告，**跑出來不等於推算即停下查規則**。
7. `scripts/run-tests.sh unit tests/unit/skills/ tests/unit/_meta/` 全綠（只允許既有 node skip）；`make audit` 不受影響（不動不變量涵蓋的檔）。
8. fresh `verifier` 對主張「55 格皆有決定性去向且兩類缺口分報正確」做反證後才打勾。

## 8. 待業主核的四點

1. `fix_type` 允許 `null`（§3）。替代：加第七值 `none`（要改 design 元件 9）。建議 `null`。
2. `cross_audience_rewrite` 的判準用 map-v2 的 `cause_state=="V"`（2026-09-04 對 kb 量的），而非「另一受眾正本有細目」（現在只有 prospect 一份正本，後者無法判）。正本增加後改判準＝新 readiness epoch。
4. `gap_classes` 是 design 元件 9 `CellRecord` 沒有的新欄位（R3.5 兩類可並列），建議與第 3 點一併回寫 design。
3. 新增 `map-v2.json` 為第四份輸入（design 元件 9 簽名 `reweigh(canon, demand_path, answerability_path)` 與 tasks 2.6 皆無）：沒有它 R3.5 兩類分報無法決定性算，只能等元件 10 `agent_eval` 回填。建議接受並回寫 design 元件 9 簽名。

## 9. 回滾／預算／停損

- 回滾：刪 `tools/gapmap/coverage_map.py`、`scripts/reweigh.py`、新測試；還原 `outline_gate.py` `check_stop` 兩行與 `status.py` 一函式。
- 預算 $0（無 API）；主 session 實作預估 1 個工作段；兩次 verifier REFUTED 即停下回業主。
- 停損：若 map-v2 與 answerability 對同一格出現無法用 §3 規則解釋的矛盾（例：cause_state S_OK 但判者 no_source）≥5 格，停下列表交裁，⛔ 不加特例。
