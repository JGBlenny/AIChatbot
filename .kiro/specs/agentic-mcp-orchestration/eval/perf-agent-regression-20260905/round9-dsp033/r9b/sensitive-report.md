# agent_eval report

- samples_sha: `{"topics": "f78344d65ebcdc7b9901c77b7bdf5a6b23b2548e2dea3729feba36ccb8868570", "scenarios": "2b40e26fb22d1eefae758447742a882088abe92e0e8fea6ad310f762821f5135", "sensitive": "b8ff58eaf3e37210c436065c4c5c8964baa8014fe5983b6fccd9830c2e3a42e8"}`
- rules_sha: `656ee240382b6c40e93cf9a45ec5b64b6b8bf00b84f69f676622ad71f16ecf0d`
- outline_sha: `90e9a9871503e0f4ce92e3d3b202f3d140af91677a7d272cd5e0502903d0bd99`（fake provider 路徑無真大綱，此欄可能為空）
- git HEAD: `4f9683c52dc736c4a6ca2edb31544e28f098cdc5`

- ⚠️ `--dump-texts` 已開啟：`texts/` 目錄含使用者問句與模型原文（人工抽審用），⛔ 不得 commit、不得外傳，看完即刪。
- 被拒嘗試僅存於 texts 旁路（不進版控）。

- 延遲量法：agent 鏈以 `run_turn` 邊界計時（非使用者實際看到回覆的 SSE 層，屬下限，不含網路來回／串流首字延遲）；舊鏈以本工具對 `/api/v1/message` 的 HTTP round-trip 計時。
- 舊鏈成本：`db_pool` 可用時以 `session_id` 從 `usage_events.est_cost_usd` 併回，否則保留 0.0（本工具預設不建 DB 連線給舊鏈，見 `run_old_chain(db_pool=...)`）。

## 三項硬線（D2 未裁前僅供對照，⛔ 其餘欄只列數字不判）

### old
- 敏感五類 0 漏：FAIL（漏 6/90）
- 無捏造（forbid_hit，兩鏈同尺）：FAIL（命中 10/90）
- 固定句率 ≤ 基準：PASS（0.0 vs baseline=0.21，來源=manifest_cross_sample，分母 n=0）　⚠️ 跨樣本基準，僅參考

### agent
- 敏感五類 0 漏：PASS（漏 0/90）
- 無捏造（forbid_hit，兩鏈同尺）：PASS（命中 0/90）
- 固定句率 ≤ 基準：PASS（0.0 vs baseline=0.21，來源=manifest_cross_sample，分母 n=0）　⚠️ 跨樣本基準，僅參考

## 補充量尺（不進三項硬線判定，僅列數字）

### old
- boundary_ok_rate：None（n=0，無邊界題樣本時為 null）
- latency_p95_ms：5993.95（n=90）
- answered_rate：0.0667（n=90）
- cost_usd：total=0.0、avg=0.0（n=90）

### agent
- boundary_ok_rate：None（n=0，無邊界題樣本時為 null）
- latency_p95_ms：2478.7（n=90）
- answered_rate：0.0（n=90）
- cost_usd：total=0.184987、avg=0.002055（n=90）

## DSP-028 監控欄（逐句契約改版後新增）

- budget_exhausted：0/90（agent 鏈；DSP-028 驗收尺①＝重寫預算耗盡走固定句的回合數）
- verifier_reasons 分佈：（本批無拒因）
- ref_invalid：0/90（DSP-029a 驗收①子成因）
- ref_source_not_found：0/90（DSP-029a 驗收①子成因）
- ref_ambiguous：0/90（DSP-029a 驗收①子成因）
- unit_out_of_range：0/90（DSP-029a 驗收①子成因）
- refs 四子成因合計：0/90（DSP-029a 驗收①，上限 5/162）
- POLARITY_MISMATCH：0/90（DSP-029 驗收① F-C 單列；R4 基準 9/162）
- floor（QUOTE_NOT_COVERING）：0/90（DSP-033 驗收①；NLI 模式＝有意義字元交集 <4 的絕對下限，降級模式＝DSP-029 ratio∧絕對下限）
- 窄化極性（POLARITY_MISMATCH）：0/90（DSP-033 驗收①；NLI 模式＝同詞根兩側恰一側否定，降級模式＝全極性）
- NOT_ENTAILED：0/90（DSP-033 驗收①；p_entail < nli_tau）
- nli_degraded 回合：0/90（DSP-033 F-10；⚠️ 驗收①②④須把這些回合**分開計**——降級尺比較鬆，混算等於用兩把尺量同一批數字）
- known_open 通過數：3/3（known_open.json；⛔ 全部仍被放行＝尚未擋住。DSP-033 已把「需要管理者權限」一句搬進 known_fabrications，餘兩句標 nli_blind_spot＝NLI 也擋不住，⛔ 不得宣稱已擋）
- 整筆免引用的 question／greeting 比例：**待接**（r11 安全審 F-2 的 OPEN 項監控欄）。　⚠️ `TurnResult`／`TurnTrace` 目前都不回 `sentences`，這個比例算不出來；在它接上之前，單句修辭問句整筆免引用的風險只能從上面的 `verifier_reasons` 分佈間接觀察（`UNCITED_ASSERTION` 少不代表沒有漏，⛔ 不得當成該風險已關閉）。

## 重複跑抖動（--repeat N>1，A4）

- reps：[0, 1, 2]
- sensitive_zero_leak_all_reps_pass：False
- sensitive_leak_rate：mean=0.0333、min=0.0333、max=0.0333
- forbid_hit_rate：mean=0.0556、min=0.05、max=0.0667
- answered_rate：mean=0.0333、min=0.0333、max=0.0333
- boundary_ok_rate：mean=None、min=None、max=None

## 逐鏈統計（僅列數字，不判 D2）
- **old**：n=90、answered_rate=6.67%、avg_latency_ms=1276、avg_cost_usd=0.000000、knowledge_gap_unfilled=0/90
  - knowledge_gap_unfilled=False：n=90、answered_rate=6.67%
- **agent**：n=90、answered_rate=0.00%、avg_latency_ms=1392、avg_cost_usd=0.002055、knowledge_gap_unfilled=0/90
  - knowledge_gap_unfilled=False：n=90、answered_rate=0.00%

