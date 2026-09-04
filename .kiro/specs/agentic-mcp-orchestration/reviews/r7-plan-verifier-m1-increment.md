# r7 plan-verifier（M1 前增量：facade_only／Origin／2.7／2.1a／R3.7／5.2）— 2026-09-05
REVISE（6 P1）
1 agent.turn 自呼無程式擋（call() for_model 預設 False）→ 2.1 Runtime 一律 for_model=True＋2.6 測試。
2 2.1a loopback 與門面唯一計量疊加 ⇒ 1＋N 列 → 內部呼叫標頭不計量；驗收比列數與額度。
3 M1 後前提偵測第一旗恆真 → 改「未登錄／非 is_internal key 才紅」（2.8）。
4 2.7 trace 端點無業者範圍、派 mech → key vendor_ids 過濾 404、security-executor、先過 security-reviewer。
5 2.7 (P) 未列 2.5 前置、驗收空跑 → 前置 2.5＋真跑一回合整合案。
6 2.6 無回切開關 → AGENT_TURN_ENABLED；5.1 回切加格。
P2：1.8 Origin 措辭；docs 明寫外部 MCP client 即模型；ToolCallRecord.args_summary 回寫 design；不變量 30 白名單＋0 呼叫即紅；2.7 無條件 key 措辭；3.2 help 不可引用；候選投影／ref adapter 掛 2.x 追蹤。
七題：facade_only 規則不足（修）；Origin 一致；args_summary 相容但授權缺；loopback 重複計額（修）；R3.7 與 2.6 一致缺開關（修）；5.2 相容；不變量 30／前提旗升子任務。
