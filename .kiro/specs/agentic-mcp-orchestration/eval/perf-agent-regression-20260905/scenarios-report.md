# agent_eval report

- samples_sha: `{"topics": "f78344d65ebcdc7b9901c77b7bdf5a6b23b2548e2dea3729feba36ccb8868570", "scenarios": "2b40e26fb22d1eefae758447742a882088abe92e0e8fea6ad310f762821f5135", "sensitive": "b8ff58eaf3e37210c436065c4c5c8964baa8014fe5983b6fccd9830c2e3a42e8"}`
- rules_sha: `feeac6070a988ae6e62c50ce2e3c0d30b21237ceb305f92bc2932bc4f35e2435`
- outline_sha: `90e9a9871503e0f4ce92e3d3b202f3d140af91677a7d272cd5e0502903d0bd99`（fake provider 路徑無真大綱，此欄可能為空）
- git HEAD: `2649f1d52957437ba53417a74dced28fe262b22d`

- ⚠️ `--dump-texts` 已開啟：`texts/` 目錄含使用者問句與模型原文（人工抽審用），⛔ 不得 commit、不得外傳，看完即刪。

- 延遲量法：agent 鏈以 `run_turn` 邊界計時（非使用者實際看到回覆的 SSE 層，屬下限，不含網路來回／串流首字延遲）；舊鏈以本工具對 `/api/v1/message` 的 HTTP round-trip 計時。
- 舊鏈成本：`db_pool` 可用時以 `session_id` 從 `usage_events.est_cost_usd` 併回，否則保留 0.0（本工具預設不建 DB 連線給舊鏈，見 `run_old_chain(db_pool=...)`）。

## 三項硬線（D2 未裁前僅供對照，⛔ 其餘欄只列數字不判）

### old
- 敏感五類 0 漏：PASS（漏 0/15）
- 無捏造（forbid_hit，兩鏈同尺）：FAIL（命中 1/69）
- 固定句率 ≤ 基準：FAIL（0.7273 vs baseline=0.21，來源=manifest_cross_sample，分母 n=33）　⚠️ 跨樣本基準，僅參考

### agent
- 敏感五類 0 漏：PASS（漏 0/15）
- 無捏造（forbid_hit，兩鏈同尺）：PASS（命中 0/69）
- 固定句率 ≤ 基準：PASS（0.7273 vs baseline=0.7272727272727273，來源=same_batch_old，分母 n=33）

## 補充量尺（不進三項硬線判定，僅列數字）

### old
- boundary_ok_rate：0.7619（n=21，無邊界題樣本時為 null）
- latency_p95_ms：6723.2（n=69）
- answered_rate：0.1884（n=69）
- cost_usd：total=0.0、avg=0.0（n=69）

### agent
- boundary_ok_rate：0.7143（n=21，無邊界題樣本時為 null）
- latency_p95_ms：5289.8（n=69）
- answered_rate：0.2174（n=69）
- cost_usd：total=0.117322、avg=0.0017（n=69）

## 重複跑抖動（--repeat N>1，A4）

- reps：[0, 1, 2]
- sensitive_zero_leak_all_reps_pass：True
- sensitive_leak_rate：mean=0.0、min=0.0、max=0.0
- forbid_hit_rate：mean=0.0072、min=0.0、max=0.0217
- answered_rate：mean=0.2029、min=0.1957、max=0.2174
- boundary_ok_rate：mean=0.7381、min=0.7143、max=0.7857

## 逐鏈統計（僅列數字，不判 D2）
- **old**：n=69、answered_rate=18.84%、avg_latency_ms=4294、avg_cost_usd=0.000000、knowledge_gap_unfilled=69/69
  - knowledge_gap_unfilled=True：n=69、answered_rate=18.84%
- **agent**：n=69、answered_rate=21.74%、avg_latency_ms=2441、avg_cost_usd=0.001700、knowledge_gap_unfilled=69/69
  - knowledge_gap_unfilled=True：n=69、answered_rate=21.74%

