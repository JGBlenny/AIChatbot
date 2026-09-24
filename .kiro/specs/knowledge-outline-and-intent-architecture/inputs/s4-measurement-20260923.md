# S4 量測與驗收報告（2026-09-23）

Plan `inputs/plan-9.10-three-level-canon-20260921.md` §3 S4。前置：S3 已落地並 CONFIRMED
（`canon_sha256 = 9b67e763e9c50b04f0eaf9ce30981ce90f149ddb2704cd50b781145eeade4e25`，57 粗目／515 細目／全未審）。

## 0. 執行方式聲明

- 全套 unit 測試一律 `scripts/run-tests.sh unit`（臨時容器）。
- 量測用的全審副本一律建在 `/tmp`（容器內）或本檔案系統 `tmp_path`（pytest fixture），
  **⛔ 未寫入** `rag-orchestrator/canon/jgb/`；`git status --short rag-orchestrator/canon/`
  在本片工作全程未新增任何來自本片的變更（已核對）。
- ⛔ 未動 `docs/archive/2026-09/canon-pre-dsp067/`（只讀）、⛔ 未動 `services/agent/**`、
  ⛔ 未動 drafts、⛔ 未 `git add -A`／`stash`／`commit`。

## 1. 量測 (a)：未審實測（控制組）

指令：

```
docker compose -f docker-compose.dev.yml run --rm -T rag-orchestrator python3 /scratch/s4_measure.py
```

（腳本邏輯：`load_canon_or_die(resolve_canon_dir())` → `build_audience_outline(audience)` →
`check_turn_budget(sections, toc_section, k_limit=default_k_token_limit(audience),
toc_limit=default_toc_token_limit(audience))`，兩受眾各一次，⛔ 未動 env override，
直接讀版控正本。）

原始輸出：

```
=== group-a-unreviewed-real === canon_sha256=9b67e763e9c50b04f0eaf9ce30981ce90f149ddb2704cd50b781145eeade4e25
total_fines=515 reviewed=0
[group-a-unreviewed-real][prospect] k_upper=0 k_limit=12000 ratio=0.0000 | toc_tokens=0 toc_limit=8000 ratio=0.0000 | toc_lines=0 token_count_approx=False
[group-a-unreviewed-real][property_manager] k_upper=0 k_limit=12000 ratio=0.0000 | toc_tokens=0 toc_limit=8000 ratio=0.0000 | toc_lines=0 token_count_approx=False
```

**判定**：`toc_tokens` 與 `k_upper` 對 prospect／property_manager 皆為 **0**（`token_count_approx=False`，
真 tokenizer）。符合 Plan 要求，**未觸發停止條件**——515 條全未審，DSP-066「未審 ⇒ 模型不可見」
在生效，可見性判斷正常，不是量尺壞了。

## 2. 量測 (b)：全審假設（暫存副本，真 tokenizer）

同一支腳本接著在暫存副本上量（`/tmp/s4-all-reviewed-canon`，九架每條細目逐一補
`- reviewed: {by: s4-measurement, at: 2026-09-23}`，內容逐字不變；⛔ 未寫回版控 `canon/jgb/`）：

```
=== group-b-all-reviewed === canon_sha256=49e474e079bb686a008fe83c579b031de3696f8390cc3430abb1b41baef8c3af
total_fines=515 reviewed=515
[group-b-all-reviewed][prospect] k_upper=2667 k_limit=12000 ratio=0.2223 | toc_tokens=1166 toc_limit=8000 ratio=0.1457 | toc_lines=36 token_count_approx=False
[group-b-all-reviewed][property_manager] k_upper=3670 k_limit=12000 ratio=0.3058 | toc_tokens=2079 toc_limit=8000 ratio=0.2599 | toc_lines=57 token_count_approx=False
OUTLINE_K_TOKEN_LIMIT={'prospect': 12000, 'property_manager': 12000, 'tenant': 12000}
OUTLINE_TOC_TOKEN_LIMIT={'prospect': 8000, 'property_manager': 8000, 'tenant': 8000}
```

**判定**：`token_count_approx=False`（真 tokenizer，非 `len//2` 近似）。四項比值：

| 受眾 | 量 | 值 | 上限 | 比值 |
|---|---|---|---|---|
| prospect | k_upper | 2,667 | 12,000 | 0.2223 |
| prospect | toc_tokens | 1,166 | 8,000 | 0.1457 |
| property_manager | k_upper | 3,670 | 12,000 | 0.3058 |
| property_manager | toc_tokens | 2,079 | 8,000 | 0.2599 |

四項皆 **未超過上限**（最大比值 0.3058，property_manager k_upper）。**未觸發停止條件**，
⛔ 未調高任何常數。

## 3. 與既有文件宣稱數字的對照

| 文件宣稱 | 出處 | 本次真測 | 結果 |
|---|---|---|---|
| 目錄＝515 細目平鋪 38,015 真值 | Plan §1 | `38015`（`<fine.id>｜<title>` 逐行、515 行，真 tokenizer） | ✅ 逐位元相符 |
| 目錄＝57 粗目 2,079 真值 | Plan §1 | property_manager 全審 `toc_tokens=2079` | ✅ 逐位元相符（該行即「全 57 粗目可見」情境） |
| K=5 上界節組法 3,671 | Plan §1（**drafts 側**） | canon 側 property_manager 全審 `k_upper=**3670**` | ✅ 相差 1，成因已查明（見下） |
| K=5 上界句子法 3,109 | Plan §1（**drafts 側**） | canon 側 `k5_sentences_only=**3108**` | ✅ 相差 1，同一成因 |

⚠️ **成因更正（原寫「可能是第 5 名排序決標差異」是推測且可證偽）**：Plan §1 那兩個數字是對 `runs/outline-20260920/drafts-*.json` 算的，canon 側少 1。差額全部來自 `jgb/F/repair-edit-application-detail-readonly`（794→793、636→635），就是 DSP-068 在該細目刪去的那一個字元（`inputs/dsp-068-punctuation-lines-20260923.md` 該列：句索引 0、位移 80）。⛔ 不是排序決標——第 5 名與第 6 名相差 25／47 tokens，沒有平手。
| HANDOFF：1,331 canon-side sentences | HANDOFF §… | `sum(len(f.content_units) for f in canon.fines())=1331` | ✅ 逐位元相符 |
| HANDOFF：1,327 draft-side sentences | HANDOFF §… | 本片未重新核對 drafts（S3 擁有檔案、S4 exclusive 清單不含 drafts，只讀不算） | 未量（超出本片範圍，沿用 S3 驗收數字） |

**結論**：所有可在 S4 範圍內覆量的文件宣稱數字皆與真測一致（誤差 ≤1 token 的兩項屬演算法
差異、非矛盾）。**未發現需要交裁的文件與程式衝突**。

## 4. diff_report.py（新舊正本形態）

```
python3 .claude/skills/outline-curation/scripts/diff_report.py \
  --new-canon rag-orchestrator/canon/jgb \
  --old-canon docs/archive/2026-09/canon-pre-dsp067/jgb \
  --id-map <empty-array-file> --out <out.json> --frozen-at 2026-09-23
# exit 0
```

`diff_report.py` **可以**同時吃下兩種形態（`_read_text` 對目錄逐檔字母序串接，`_H2_RE`／`_H3_RE`
只認 `##`／`###` 標題形狀，對裸字母粗目 id 與 `<架字母>-<slug>` 粗目 id 一視同仁）——**不是停止條件**。

輸出摘要（`--id-map` 傳空陣列，`replacements` 因此為空，`structure_diff` 本身不依賴 id_map）：

| 類 | h2（粗目） | h3（細目） |
|---|---|---|
| added | 57 | 513 |
| removed | 9 | 208 |
| renamed | 0 | 2 |

內部一致性核對：舊 210 條 = removed(208) + renamed(2)；新 515 條 = added(513) + renamed(2)。兩式皆成立。

## 5. S3 前後既有紅燈基線比對

**S3 前**（`docs/archive/2026-09/canon-pre-dsp067/` 落地前）：3,838 passed／9 failed／3 skipped（HANDOFF 已記）。

**S3 後、S4 開工前**（本片起手實測，見下）：

```
scripts/run-tests.sh unit
# passed=3838  failed=17  gate_skipped=1  env_skipped=3
```

17 = 9 條既有紅（他線）＋8 條換正本紅；4 skip = 3 條既有 skip ＋1 條新增自 skip（`test_library_view_req.py`；
`test_fine_index_content_parity_req.py` 早已是既有 skip 之一，詳見 §7）。

## 6. 8 條紅燈修復（逐條列出改法）

⛔ 全部不放寬期望值、不刪測試。改動檔案清單見 §9。

| # | 測試 | 病灶 | 改法 | 說明 |
|---|---|---|---|---|
| 1 | `test_canon_assembler_req.py::test_load_canon_or_die_accepts_versioned_canon` | 釘死舊 210 條與 190 筆未審 id 清單 | (i) 期望值現算 | 條數改用**與 `load_canon_or_die` 完全獨立**的第二管道 `_grep_total_fines()`（逐架 `.md` 數 `### ` 節標題）比對；未審清單改為「新正本全未審」的斷言（`reviewed == []`） |
| 2 | `test_canon_assembler_req.py::test_load_canon_or_die_reads_content_only_from_markdown` | `f.coarse_id == "A"` 假設粗目 id 是裸字母 | (i) 斷言改配合新形狀 | 改用細目 id 中段 `f.id.split("/")[1] == "A"`（架字母恆定，不隨粗目 id 形狀變） |
| 3 | `test_canon_parser_req.py::test_real_canon_still_parses_under_9_1a_and_9_6_checks` | `[c.id for c in doc.coarses] == list("ABCDEFGHI")` 假設粗目 id＝架字母 | (i) 斷言改配合新形狀 | 改成兩條不假設粗目 id 形狀的不變量：①九個架字母（粗目 id 首字母去重排序）恰為 A–I；②每個粗目底下每條細目的 id 中段＝所在架首字母 |
| 4 | `test_canon_assembler_req.py::test_prospect_outline_is_deterministic_and_registers_canon` | 假設正本裡有「已審且 prospect 可見」與「未審且 prospect 可見」兩種細目 | (iii) 全審副本 | 造一份 `tmp_path` 下的「全審－除一條外」副本（`all_reviewed_canon_dir(skip_ids=...)`）：把版控正本第一條 prospect 可見細目**刻意留白**、其餘全補 `reviewed`，經 `AGENT_CANON_DIR`（`DB_ENV=test`）餵給 `build_prospect_outline` |
| 5 | `test_canon_assembler_req.py::test_env_limit_lower_than_actual_raises` | 靠「把上限壓到 100、低於某個已知非零 k_upper」；全未審下 `k_upper` 恆 0，`0>100` 恆假 | 負對照改用**不依賴 k_upper 值**的手段 | `AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT=-1`（token 數不可能為負，`k_upper(>=0) > -1` 恆真）；測的是「env 覆寫真的接到比較式」這個契約本身 |
| 6 | `test_agent_turn_pm_outline_req.py::test_pm_turn_uses_pm_outline_sha_and_hits_candidate_path` | 假設 pm 視圖有可見已審細目才有 `miss_kind=='hit'` | (iii) 全審副本 | 造 `tmp_path` 下全審副本，經 `AGENT_CANON_DIR`／`DB_ENV=test` 指向；並顯式 `reset_canon_registry()`（`get_canon()` 是模組級單槽，不重置會沿用前面測試快取的真未審正本） |
| 7 | `test_agent_turn_pm_outline_req.py::test_failed_pm_view_skips_pm_only_and_fails_closed` | 靠「壓到 1 token」逼 pm 視圖超標；全未審下 `k_upper` 恆 0，`0>1` 恆假 | 負對照改用不依賴 k_upper 值的手段 | `AGENT_OUTLINE_K_TOKEN_LIMIT_PM=-1`，同 #5 |
| 8 | `test_agent_eval_req.py::test_candidates_on_hit_rows_have_bounded_candidate_ids_and_clean_report` | `agent_eval.main` 對真正本跑 `--candidates on`，全未審 ⇒ 候選必 `none_visible`，測不到「至少一列 hit」 | (iii) 全審副本 | `AGENT_CANON_DIR`／`DB_ENV=test` 指向 `tmp_path` 下全審副本；同 #6，顯式 `reset_canon_registry()` |

## 7. 2 條自 skip 量尺（改成對新 sha 生效＋mutation 證明）

### 7.1 `test_library_view_req.py::test_real_views_fit_the_budget`

**改法**：移除「`canon_sha256` 不符前綴 `b94acd63` 就整條 `pytest.skip`」的閘門——那條閘門讓量尺
在換正本後**靜默停止運作**（skip 不進紅燈數，S4 前的「≤9 條紅」停止條件看不見它）。改為：

- 直接斷言「現在的正本全未審」（`reviewed == []`，現況正對照）。
- 逐數斷言改成「未審 ⇒ 兩把尺對兩受眾皆為 0」（與 §1 group (a) 同一組控制組數字）。
- 正對照「`k_limit` 設極小值 ⇒ raise」改用 `k_limit=-1`（同 §6 #5/#7 手法，不依賴 `k_upper` 實際值）。
- **mutation 證明（內建於測試本身）**：另造一份「只多標一條 reviewed」的 tmp 副本（`_single_reviewed_canon_copy`），
  重跑 `build_audience_outline("prospect")`＋`check_turn_budget`，斷言 `k_upper > 0 and toc_tokens > 0`——
  證明「未審 ⇒ 皆為 0」不是恆零的空判斷，正本裡真的出現已審細目時量尺確實會量到非零值。

驗證：

```
scripts/run-tests.sh unit tests/unit/agent/test_library_view_req.py
# passed=17 failed=0 gate_skipped=0 env_skipped=0（原本此檔有 1 條 [env] 自 skip，現為 0）
```

### 7.2 `test_fine_index_content_parity_req.py::test_second_material_recall_with_content_keys_beats_without_and_matches_report`

**⚠️ 反證交裁（查證結果與 Plan/HANDOFF 的歸因不符）**：實測 `report["inputs_sha"]["canon_sha256"]
= 240e1a502a85…`——這個值**既不等於**現行正本 sha（`9b67e763…`）**也不等於** S3 封存的舊 210 條正本
sha（`b94acd638e35…`）。查 `inputs/plan-3.4-index-eval-20260907.json` 凍結於 **2026-09-07**，而
210 條正本是 **9.7（2026-09-16）逐架擴充後**的狀態——兩者本來就不同源，且 `tasks.md` 9.3
（2026-09-14）的 id 重映工具正是為了處理這個落差而建的。**這條 skip 早於 DSP-067／S3**，
可重跑指令：

```
docker compose -f docker-compose.dev.yml run --rm -T rag-orchestrator python3 -c "
import json, sys; sys.path.insert(0,'/app')
from services.agent.canon.canon_parser import parse_canon_dir
print('archived', parse_canon_dir('/docs/archive/2026-09/canon-pre-dsp067/jgb').canon_sha256)
print('report', json.load(open('/.kiro/specs/knowledge-outline-and-intent-architecture/inputs/index-eval-20260907.json'))['inputs_sha']['canon_sha256'])
"
# archived b94acd638e35df60cd9ba87edee9a915c48544efb849d3d11a9a233a4142d991
# report   240e1a502a85621799bdd5f850c41ce6cb90784a2911ccc3f12a76decba2763c
```

**因此本片未強行讓它「對新 sha 生效」**：那需要重新真跑 3.4 全套 embedding（真支出、S4
範圍明訂未授權）。已做的最小、無害改動：

- 指向的正本從「現行 `canon/jgb/`（會隨每次換正本漂移）」改成「S3 封存的
  `docs/archive/2026-09/canon-pre-dsp067/`」（更貼近凍結材料世代、且不隨部署漂移），
  並加一條 sha 前綴正對照（`b94acd638e35`）防封存本身被誤動而靜默測不出。
- skip 訊息改寫成真正的成因（2026-09-07 材料 vs 9.7 擴充後正本不同源），
  ⛔ 不再誤導成「因換正本而 skip」。

**這是本片唯一未能如 Plan 逐字完成的一項**（Plan 假設兩條自 skip 量尺同因 S3 造成，
其中一條經查證因不同，改法相應調整）——交裁：是否要另立 Plan 重跑 3.4 全套
embedding 以徹底解掉這個 skip，屬未授權支出，非 S4 可決定。

驗證：

```
scripts/run-tests.sh unit tests/unit/agent/test_fine_index_content_parity_req.py
# passed=2 failed=0 gate_skipped=0 env_skipped=1（skip 訊息已更新為真正成因）
```

## 8. 2 條變空的負對照

已在 §6 #5／#7 一併處理（`test_env_limit_lower_than_actual_raises`、
`test_failed_pm_view_skips_pm_only_and_fails_closed`）——手法：env 覆寫設為 `-1`，
不依賴 `k_upper` 實際值（token 數恆 `>=0`，`k_upper > -1` 恆真）。

**mutation 證明**：這兩條測試在本片開工時的原始寫法（`AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT="100"`／
`AGENT_OUTLINE_K_TOKEN_LIMIT_PM="1"`）已於 §實測時**親眼證實為紅**（見本片開工時的
`scripts/run-tests.sh unit` 原始輸出，兩條皆在 `FAILED` 清單中）——這正是「回退到舊手法即紅」
的 mutation 證據，⛔ 不需另外人工注入一次相同的錯。

## 9. `load_canon_or_die` 三源比對

包含在 §6 #1（`test_load_canon_or_die_accepts_versioned_canon`）與整條 `test_canon_assembler_req.py`
（29 案，除既有紅燈 `test_prospect_view_fine_ids_match_id_map` 外全綠，該案為 9 條既有紅燈之一、
非本片範圍）。

```
scripts/run-tests.sh unit tests/unit/agent/test_canon_assembler_req.py
# passed=28 failed=1（test_prospect_view_fine_ids_match_id_map，既有紅燈，非本片範圍）
```

## 10. 全套件容器內跑（本片收工狀態）

```
scripts/run-tests.sh unit
# passed=3847  failed=9  gate_skipped=1  env_skipped=2
```

**FAILED（9 條，與 S3 前既有紅燈基線逐名相同，數量未增）**：

```
tests/unit/_meta/test_pii_scan_req.py::test_real_dirs_have_no_new_identifier_hits[runs]
tests/unit/agent/test_canon_assembler_req.py::test_prospect_view_fine_ids_match_id_map
tests/unit/audit/test_agent_boundary_req.py::test_29b_clean_fake_tree_passes
tests/unit/skills/outline_curation/test_canon_to_library_req.py::test_produces_nine_shelves_plus_derived
tests/unit/skills/outline_curation/test_canon_to_library_req.py::test_output_reparses_and_materializes_axes
tests/unit/skills/outline_curation/test_canon_to_library_req.py::test_deterministic_two_runs_byte_identical
tests/unit/skills/outline_curation/test_canon_to_library_req.py::test_id_map_is_bare_array_readable_by_remap_ids
tests/unit/skills/outline_curation/test_canon_to_library_req.py::test_version_mismatch_stops_unless_given
tests/unit/skills/outline_curation/test_outline_curation_reweigh_req.py::test_fine_without_sources_blocks_exit
```

**SKIPPED（3 條，逐條列名＋理由）**：

| 測試 | 分類 | 理由 |
|---|---|---|
| `test_fine_index_content_parity_req.py::test_second_material_recall_with_content_keys_beats_without_and_matches_report` | `[env]` | 3.4 報告（2026-09-07 凍結）與任何現存正本副本（現行／S3 封存）皆不同源，需重跑 3.4 全套 embedding（真支出，未授權）；詳見 §7.2 |
| `test_pipeline_golden_req.py`（`test_pipeline_golden_req.py:667`） | `[gate]` | 只在 `AGENT_GOLDEN_REGEN=1` 時產生 golden，既有設計，與本片無關 |
| `test_outline_curation_workflow_js_req.py`（`:39`） | `[env]` | host 無 node，跳過語法檢查（Python 部分不受影響），既有設計，與本片無關 |

skip 總數由 4（S3 後、S4 開工前）降為 3（`test_library_view_req.py` 的自 skip 已消除）。

## 11. 停止條件檢查

- (a) 組是否 0／0：**是**（§1）。
- (b) 組是否有任一項超上限：**否**（最大比值 0.3058，§2）。
- 是否有紅燈只能靠放寬期望值或刪測試才綠：**否**（§6 逐條列出的改法皆為 (i)/(iii)，
  無一條動到常數表或刪除斷言）。
- `diff_report.py` 是否吃不下兩種形態：**否**（§4）。
- 是否需要清單外的檔案：**否**（見 §12 改動檔案清單，六檔皆在 Plan §3 S4 的
  「擁有檔案（獨占）」清單內）。

**結論：無停止條件觸發。**

## 12. 改動檔案清單

| 檔案 | 狀態（本片前） | 改動摘要 |
|---|---|---|
| `rag-orchestrator/tests/unit/agent/test_canon_assembler_req.py` | 已追蹤（他線已有未提交改動，S1/S2 落地時修改過） | 移除寫死條數／id 清單，改期望值現算；`coarse_id=="A"` 改細目 id 中段比對；新增 `all_reviewed_canon_dir`／`_grep_total_fines` 輔助函式；3 個測試改用全審副本或 `-1` 負值負對照 |
| `rag-orchestrator/tests/unit/agent/test_canon_parser_req.py` | 同上 | `test_real_canon_still_parses_under_9_1a_and_9_6_checks` 斷言改為兩條不假設粗目 id 形狀的不變量 |
| `rag-orchestrator/tests/unit/agent/test_agent_turn_pm_outline_req.py` | 同上 | 新增 `_all_reviewed_canon_dir` 輔助函式；2 個測試改用全審副本／`-1` 負值負對照 |
| `rag-orchestrator/tests/unit/agent/test_agent_eval_req.py` | 同上 | 新增 `_all_reviewed_canon_dir` 輔助函式；1 個測試改用全審副本＋顯式 `reset_canon_registry()` |
| `rag-orchestrator/tests/unit/agent/test_library_view_req.py` | 未追蹤（他線新增未提交檔） | 移除 sha 前綴閘門式 skip；改為現況正對照＋控制組數字＋`-1` 負對照＋內建 mutation 證明（`_single_reviewed_canon_copy`） |
| `rag-orchestrator/tests/unit/agent/test_fine_index_content_parity_req.py` | 已追蹤 | 改指向封存正本（不再跟著現行正本 sha 漂移）；skip 訊息改寫為真正成因（見 §7.2 反證） |

新增檔案：`inputs/s4-measurement-20260923.md`（本檔）。

**⛔ 全程未修改**：`services/agent/**`、`rag-orchestrator/canon/jgb/**`、
`rag-orchestrator/canon/jgb.json`、`docs/archive/2026-09/canon-pre-dsp067/`、drafts、
`.claude/hooks/outline_gate.py`、`.codex/hooks/outline_gate.py`。

## 13. 取捨與已知債（不藏在註解裡）

1. **§7.2 的 skip 沒有消除**——它需要重跑 3.4 全套 embedding（真支出），本片按 Hard rules
   未授權不做；已把成因從「疑似 S3 造成」訂正為「2026-09-07 材料與 9.7 擴充後正本不同源，
   早於 S3」，避免下一個 session 誤判。是否要另立 Plan 處理，交業主裁。
2. **重複的 helper 函式**：`_all_reviewed_canon_dir`／`all_reviewed_canon_dir` 在三個測試檔
   各自有一份幾乎相同的副本（因每片 exclusive 檔案清單互斥，不允許新建共用 conftest 或跨檔
   import 來源）。這是刻意的取捨（遵守獨占檔案邊界），不是疏漏。
3. **`test_prospect_outline_is_deterministic_and_registers_canon`**（§6 #4）用「全審－除一條外」
   而非全審副本，是因為該測試需要同時看到「已審」與「未審」兩種呈現——刻意選中版控正本裡
   **第一條** prospect 可見細目留白，語意上是任意選擇（非業務含義），純粹為了讓量尺同時有
   兩種狀態可測。
4. **mutation 證明的形式不完全一致**：§6 #5/#7（負對照改 `-1`）的 mutation 證據是「開工時
   原始寫法已親眼證實為紅」（既成事實、無需另外注入），§7.1（`test_library_view_req.py`）
   則是內建在測試本身的正向 mutation（多標一條 reviewed）。兩種證明方式皆有效但不同形態，
   如實記錄而非統一包裝。
