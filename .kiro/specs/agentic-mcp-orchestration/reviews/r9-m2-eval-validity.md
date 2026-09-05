# r9：M2 評估方法有效性審查（fresh-context plan-verifier，2026-09-05）

**問題**：只用樣本 A（`topics-v2.json` 54 句）＋樣本 B（`scenarios-v1.json`）兩條鏈對跑，能不能有效驗證 M2 並支撐 M3 放行？
**判定：REVISE。**

## 結論（審查者原文摘要）

三個層次的阻斷：①工具目前跑不了真 agent 鏈（`--provider openai` 直接 `SystemExit`、registry 空、`db_pool=None`、未傳 `outline_doc`）；②多輪是假的（每 turn 重建 `state={}`，DSP-022 的 dialog 歷史永遠為空），且舊鏈同 session 連跑、agent 鏈不連，兩鏈不可比；③身分寫死 `mode="b2c"`，售前池是 b2b 池，兩條鏈都在量錯的池。即使修好，A 是調校知識用的量尺本身（五輪 after 對照檔），非 holdout，且只有「建立合約」單一主題；C（真實流量）缺席代表全程沒有未見過的資料。M2 五條收案線裡只有「敏感 0 漏」有半個尺（n=5、僅涵蓋一類），rubric／答到率、邊界不硬答率、p95、成本在工具裡查無實作。

## 發現（16 項）

| # | 優先級 | 問題 | 證據（可 grep） | 影響 | 最小修法 |
|---|---|---|---|---|---|
| 1 | P0 | agent 鏈無法真跑 | `tools/agent_eval.py`：`provider=openai 未在任務 4.2 實作範圍內`、`build_fake_registry`、`build_runtime(db_pool=None` | 全部 | 接真 provider／真 registry／`build_prospect_outline` |
| 2 | P0 | 多輪不帶歷史 | `_run_turn_for` 的 `state: dict = {}`；`runtime.py:_append_dialog` | 全部 | scenario 層一個 state 逐 turn 傳 |
| 3 | P0 | 身分池錯 b2c | `"mode": "b2c"`、`mode="b2c"`；正對照 `outline.py` `⛔ 勿改回 b2c` | 全部 | 改 b2b／vendor 1，加回歸測試 |
| 4 | P0 | A 是調校尺本身、單主題 | `topics-v2.json` `_meta.scope`；`topics-v2-after…after5`；`topic-contract-pilot-20260904.md` | 答到率／rubric／固定句率樂觀偏誤 | 降級為回歸集，⛔ 不作放行證據 |
| 5 | P0 | C 缺席 | manifest `"traffic": {"available": false`；design `M2 … 三組樣本` | M2 done 定義 | 業主匯出 ≥60 句分層，先寫抽樣法再看結果 |
| 6 | P1 | 敏感 0 漏量不到 | `load_topics_scenarios` 的 `sensitive=False`；scenarios 僅 5 個敏感 turn、3 個同句、只涵蓋 customer_reference | 敏感 0 漏 | 每類 ≥5 句獨立問法 |
| 7 | P1 | 無捏造兩鏈兩把尺都不對 | `compute_hardlines` 的 `verifier_rejects > 0 and r.kind == "answer"` vs `forbid_hit` | 無捏造 | 統一 `forbid_hit`＋抽審；verifier_rejects 只當觀測 |
| 8 | P1 | 固定句率基準跨樣本且與敏感／邊界正解衝突 | manifest `4/19≈0.21`；`fixed = sum(... kind == "handoff")` | 固定句率 | 只算非敏感非邊界子集；基準用同批 old 實測 |
| 9 | P1 | rubric／邊界率／p95／成本查無實作 | grep `rubric`／`p95` 無命中；`cost_usd=0.0` | 邊界 ≥90%、p95、答到率、成本 | 報表補四尺 |
| 10 | P1 | 延遲不在使用者層量 | `_run_turn_for` 直呼 `run_turn` | p95 | 註明為下限；真入口量法另案 |
| 11 | P1 | 單跑、無重複、無溫度釘 | grep `repeat` 無命中；tasks 1.1 收案註記「連跑兩次失敗集合會變」 | 全部判定力 | `--repeat N`，0 漏取最嚴、比率報全距 |
| 12 | P2 | D2 未裁 ⇒ M2 不可宣告 | design `D2 未裁前 agent_eval 只出對照不判 PASS` | 放行判準 | 跑前業主一次裁定寫進 manifest |
| 13 | P2 | 舊鏈轉人用關鍵字啟發式 | `_boundary_ok`／`_sensitive_leak` 的 `沒有資料／專人／找真人` | 敏感／邊界（舊鏈側低估） | 讀結構化 handoff＋固定句比對 |
| 14 | P2 | B 非逐字腳本；manifest turns 24 實 23；5 套實 6 套 | `"verbatim": false` ×8；`"turns": 24` | 與舊輪可比性 | B 當新獨立樣本；修計數 |
| 15 | P2 | 知識缺口未補沒有排除規則 | `_gap_batches_imported` 未被 `compute_hardlines` 引用 | 答到率／rubric | 報表分層 |
| 16 | P3 | `outline_sha` 永遠空字串 | `main()` 的 `outline_sha = ""` | 可追溯性 | 由 `runtime.outline_sha` 填 |

## 可直接留用

sha256 凍結與拒跑（`verify_manifest`、退出碼 3／4）；`_NO_VERBATIM_KEYS` 無原文斷言；`backtest_session_` 前綴與金鑰只進 header；A 的 8 句邊界題當回歸集；B 的 `must_not_contain` 禁詞尺；`--chain both` 同批對跑骨架。

## 主 session 處置（2026-09-05）

- #1–#3、#6–#11、#13–#16：**FIX**，派 executor（worktree）一次修，完成後派 fresh verifier。
- #4：**接受**——A／B 降級為「已知病灶回歸集」，tasks 4.3 與 manifest 註明 ⛔ 不作 M3 放行證據。
- #5：**業主動作**——線上匯出 prospect 問句。**2026-09-05 更正**：`chat_history` 全 repo 無寫入端（線上 7/7 備份 0 列），原文只在 `form_sessions.collected_data.dialog[].u`（`config_key='presales'`，commit `0464ff02` 起才持久化）；匯出指令見 `eval/export-prospect-dialog.sql`。本機去識別後凍結；建議 ≥60 句、分層（主題×敏感×單/多輪）。
- #10：**部分 DEFER**——p95 先以 `run_turn` 邊界量並標為下限；使用者層（SSE）量法待 M3 切換演練時做。
- #12：**業主動作**——D2 五個數字跑前裁定。

## 補充（2026-09-05，業主提供外部情境）

line-bot-platform 的四份接入文件（`chatai-requests.md` 等）含 21 個消費方定義的驗收案例，但身分是代管業務、路徑是現有面向鏈（`trigger_facet_key`），與 M2 的 prospect 影子評估不同母體 ⇒ 不能補 r9 #5 的樣本 C；其價值在 M4／M5 子 spec（已掛進 roadmap）。樣本 C 仍需線上 prospect 問句匯出。

## 修正後獨立驗證（fresh verifier，2026-09-05，HEAD `4ae6c14`）：**CONFIRMED**

12 項（#1–#3、#6–#9、#11、#13–#16）逐項 CONFIRMED，含證據字串與測試名；反向檢查未發現重述型假綠；`--provider openai` 缺 key 於任何 import／建 pool 之前即 `SystemExit`（不觸網、不 traceback）。測試：工具 34 綠、agent 目錄 557 綠。真路徑 smoke（`--set scenarios --limit 1 --repeat 2`）：18 筆、`rep` 0/1 皆在、JSONL 無原文鍵、report 有 p95／boundary_ok_rate／cost／`outline_sha`。

**驗證者的核心判斷（採納）**：在「A／B 只當回歸集、C 未到」前提下，本工具**能可信量「敏感 0 漏」**（30 句五類各 6、跨 rep 取最嚴，但只證已知病灶不復發）；**量不到「無捏造」**——唯一的尺 `forbid_hit` 只認樣本預列的禁詞（sensitive-v1 0/30 有禁詞），「無捏造 PASS」是低召回空真值，需樣本 C＋原文抽審旁路才成立。

非阻斷建議（P3，全數列入 4.3c 前置）：A1 多輪測試補 assistant 斷言並以「最後一則 user」定位第 2 輪；A2 抽審需「不進版控的原文旁路」或改由 trace 端做；A3 `answered_rate` 不量對錯（rubric 仍無）；A4 repeat 全距未進 report.md；A5 sensitive 集無禁詞 ⇒ 無捏造欄在該集無鑑別力，報表應標示；A6 容器內 `git HEAD` 空（root 非 repo）；A7 temperature 未釘（P4）。
