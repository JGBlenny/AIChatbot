# agent_eval report

- samples_sha: `{"topics": "f78344d65ebcdc7b9901c77b7bdf5a6b23b2548e2dea3729feba36ccb8868570", "scenarios": "2b40e26fb22d1eefae758447742a882088abe92e0e8fea6ad310f762821f5135", "sensitive": "b8ff58eaf3e37210c436065c4c5c8964baa8014fe5983b6fccd9830c2e3a42e8"}`
- rules_sha: `3077f05f718314175ceaa093abf75a1d8cabe6ecdcfaad14c844459868dabafd`
- outline_sha: `90e9a9871503e0f4ce92e3d3b202f3d140af91677a7d272cd5e0502903d0bd99`（fake provider 路徑無真大綱，此欄可能為空）
- git HEAD: `b010bfec5583c30f7f5fc07f8023e85ee4aa4219`

- ⚠️ `--dump-texts` 已開啟：`texts/` 目錄含使用者問句與模型原文（人工抽審用），⛔ 不得 commit、不得外傳，看完即刪。

- 延遲量法：agent 鏈以 `run_turn` 邊界計時（非使用者實際看到回覆的 SSE 層，屬下限，不含網路來回／串流首字延遲）；舊鏈以本工具對 `/api/v1/message` 的 HTTP round-trip 計時。
- 舊鏈成本：`db_pool` 可用時以 `session_id` 從 `usage_events.est_cost_usd` 併回，否則保留 0.0（本工具預設不建 DB 連線給舊鏈，見 `run_old_chain(db_pool=...)`）。

## 三項硬線（D2 未裁前僅供對照，⛔ 其餘欄只列數字不判）

### old
- 敏感五類 0 漏：PASS（漏 0/0）
- 無捏造（forbid_hit，兩鏈同尺）：FAIL（命中 3/162）
- 固定句率 ≤ 基準：FAIL（0.3623 vs baseline=0.21，來源=manifest_cross_sample，分母 n=138）　⚠️ 跨樣本基準，僅參考

### agent
- 敏感五類 0 漏：PASS（漏 0/0）
- 無捏造（forbid_hit，兩鏈同尺）：FAIL（命中 1/162）
- 固定句率 ≤ 基準：FAIL（0.7899 vs baseline=0.36231884057971014，來源=same_batch_old，分母 n=138）

## 補充量尺（不進三項硬線判定，僅列數字）

### old
- boundary_ok_rate：0.75（n=24，無邊界題樣本時為 null）
- latency_p95_ms：9822.45（n=162）
- answered_rate：0.5802（n=162）
- cost_usd：total=0.0、avg=0.0（n=162）

### agent
- boundary_ok_rate：0.9167（n=24，無邊界題樣本時為 null）
- latency_p95_ms：4341.35（n=162）
- answered_rate：0.1914（n=162）
- cost_usd：total=0.478509、avg=0.002954（n=162）

## DSP-028 監控欄（逐句契約改版後新增）

- budget_exhausted：59/162（agent 鏈；DSP-028 驗收尺①＝重寫預算耗盡走固定句的回合數）
- verifier_reasons 分佈：SCHEMA:source_not_found=72、SCHEMA:cite_out_of_range=47、QUOTE_NOT_COVERING=15、POLARITY_MISMATCH=6、UNCITED_ASSERTION=1
- source_not_found：72/162（DSP-029 驗收①子成因，上限 5/162）
- POLARITY_MISMATCH：6/162（DSP-029 驗收① F-C 單列；R4 基準 9/162）
- known_open 通過數：3/3（known_open.json；⛔ 全部仍被放行＝尚未擋住，DSP-030 處理）
- 整筆免 cite 的 question／greeting 比例：**待接**（r11 安全審 F-2 的 OPEN 項監控欄）。　⚠️ `TurnResult`／`TurnTrace` 目前都不回 `sentences`，這個比例算不出來；在它接上之前，單句修辭問句整筆免引用的風險只能從上面的 `verifier_reasons` 分佈間接觀察（`UNCITED_ASSERTION` 少不代表沒有漏，⛔ 不得當成該風險已關閉）。

## 重複跑抖動（--repeat N>1，A4）

- reps：[0, 1, 2]
- sensitive_zero_leak_all_reps_pass：True
- sensitive_leak_rate：mean=None、min=None、max=None
- forbid_hit_rate：mean=0.0123、min=0.0093、max=0.0185
- answered_rate：mean=0.3858、min=0.3148、max=0.4722
- boundary_ok_rate：mean=0.8333、min=0.75、max=0.9375

## 逐鏈統計（僅列數字，不判 D2）
- **old**：n=162、answered_rate=58.02%、avg_latency_ms=2177、avg_cost_usd=0.000000、knowledge_gap_unfilled=162/162
  - knowledge_gap_unfilled=True：n=162、answered_rate=58.02%
- **agent**：n=162、answered_rate=19.14%、avg_latency_ms=3165、avg_cost_usd=0.002954、knowledge_gap_unfilled=162/162
  - knowledge_gap_unfilled=True：n=162、answered_rate=19.14%

