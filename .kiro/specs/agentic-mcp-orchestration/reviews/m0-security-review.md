# M0 security review（1.9，security-reviewer 唯讀，2026-09-04）— REVISE → 1.10 處置

[P1] `jgb2.query.bills`／`contracts` 缺 `user_id` 時仍發無 viewer 圈定查詢，回整個 role 資料（tenant 會話 role_id 有、user_id 空）；與 `docs/api/mcp-facade.md` §4.2「雙證缺一即拒」衝突 — 處置 1.10：非 property_manager 強制雙證；pm 維持 role 單證；文件同步。
[P2] 不變量 27 只掃 `registry.py` ⇒ 空跑綠燈 — 1.10：掃 `services/agent/**`＋0 spec 即紅。
[P2] 不變量 29 WHERE 片段抽取可被非 WHERE 字串常數繞過 — M1 備註。
[P2] `registry.call()` 未剝身分鍵、只靠 spec 的 additionalProperties — 1.10：register 預設 false＋call 剝除記 violations。
[P2] 候選列整包回模型（最小化不足） — M1 備註（併 text_for_model 契約）。
[P2] `verify_api_key` 欄位偵測降級把「不限」當預設且永久快取 False — 1.10：TTL 重試＋health 紅旗 `api_keys_agent_scope_ready`。
[P3] DNS-rebinding 關閉殘餘風險＝應用層不驗 Host；Host 白名單留 nginx；⛔ 別把後台網域填進 `MCP_ALLOWED_ORIGINS`（/rag-api 代理會注入 X-API-Key）；`X-JGB-Identity` 必填是承重牆。
[P3] `/mcp` 額度在 middleware 攔時 0 列 usage_events；`quota_check` 例外 fail-open 為既有 — M1 備註。
[P3] `facade_only` 對 `/mcp`（for_model=False）形同無效 — M1 決定 /mcp 面向語義。
[P3] `_ToolListFilter` 取 header 路徑與 `_invoke` 不同，需真裝 SDK 跑一次 tools/list — 已由 1.7b ⑦ 覆蓋（list_tools 回八工具）。
[P3] `help.read` 無 audience／citable 過濾 — help-center-source 子 spec 前置。
[P3] 文件仍寫 SDK 未裝 — 1.10 同步。
已正確處理：隔離同源三消費點、kwargs 到謂詞、kb.get 兩分支、身分 fail-closed、錯誤語彙封閉、額度唯一寫入者、速率桶、middleware 順序無繞過、anyio 4 例外不外洩、資料面 CHECK 語義。

# M0 verifier（fresh，2026-09-04）— CONFIRMED（1.10 前）
A–F 全證實：audit PASS（含 3、27–31）；make test 只剩已知紅；integration agent 84 過 0 skip；equiv 53＋unit 54；容器 200／401／401、fastapi 0.115.14；兩道牆探針符合；D-002 突變 21 紅→還原 54 綠。風險：P2 admin DB 未套 api_keys migration（key 作用域降級為不限，403 結論不可外推 runtime，套後重跑 `test_key_vendor_scope_mismatch_is_403_over_http`）；P3 不變量 27 空跑；P4 舊鏈三處手抄條件未搬。

# 1.10 定向 recheck（fresh verifier，2026-09-05）— CONFIRMED
tenant 缺 user_id 五格（bills 無 ref／ref／keyword、contracts 無 ref／keyword）全 NO_MATCH 且零出向；正對照帶 user_id 走原路且 `viewer_user_id` 轉發；pm（mode=b2b／target_user=pm）單證放行；`resolved_audience()` 拋例外／無 audience／空字串 user_id 皆 fail-closed。突變 `return bool(role_id)` ⇒ unit 5 紅＋integration 1 紅，還原後綠、md5 一致、git status 不變。unit 241／integration 85 皆 0 skip；不變量 27 掃到 4 spec；`registry.call` 剝六鍵記 violations。
P3（既有、非本次引入）：bills 帶 ref 時 `get_bills` 的 ref adapter 前兩通（`GET /bills` 只 role_id、`/contracts?contract_ids=` 無 viewer）以整 role 視角解析 ref，Layer 2 只落第三通 — M1 追蹤 adapter 層圈定。

# M1 收案（2026-09-05）
- M1 fresh verifier：**REFUTED**（P2：`shadow._trace_to_dict` 讀已刪 `args_hash` ⇒ 有工具呼叫即整輪靜默丟棄；unit 盲點 `tool_calls=[]`）＋P3 測試庫孤兒 token、P3 本機 admin DB 缺 `outline_approved_by`（業主 migration 未跑）。其餘 A–G 全證實；主 session 三處直改（`mutates_session`、`budget_from_env`、lifespan 裝飾器）判可接受。
- 修正 `672baf6` → 定向 recheck **CONFIRMED**：新 unit 帶工具呼叫可序列化；原情境攔截 `logger.exception=0`、`set_decision=1`；突變回 `args_hash` ⇒ unit 紅＋情境丟棄重現；殘留 0；unit agent 498、integration agent 127 綠。advisory：guard 用 `tc\.args_hash` 而非裸字串。
- 本機 image 重建：health 200、`/mcp` 無 key 401、agent fail-soft（migration 未跑）、`make audit` PASS。
