# r3 plan-verifier（收尾審查）— design 1.2（2026-09-04）

REVISE

[P1] `build_visibility_predicate` 條件表第 4 條把 `target_user` 寫成等值比對且漏掉 `IS NULL` 放行；照表實作會讓 `kb.target_user IS NULL` 的通用知識整批消失，差分矩陣無 `kb.target_user` 維抓不到 — 證據：`vendor_knowledge_retriever_v2.py` `target_user_filter_sql = "AND (kb.target_user IS NULL OR kb.target_user && %s::text[])"`（兩處相同，b2c 另加 `'all_users'`；`_effective_target_user` 只作用於參數側）。
[P1] 域映射表要求 mock `_bills_index` 接受 `viewer_user_id`，等於拆掉刻意的大聲失敗防護（註解「不假裝答得出可見性」），M0 會在圈定語義未模擬下判綠 — 修法：保留 raise，出向參數斷言鉤子只驗轉發；是否放寬 mock 交業主。

不擋（P2）：①不變量 20 AST 會被 SELECT 投影誤判；②`/mcp` 計量雙落點（middleware＋門面）可能一呼叫兩列；③`KB_GET_CAP`／`KB_GET_SESSION_CAP` 不一致；④`AGENT_STAGE` 未列 env；⑤R5.5 目錄 8K 無落點；⑥`mode` 缺漏未定；⑦`verify_api_key` 只回 `{id,name}`；⑧R10.2 trace_id 未串 SSE。

## r2 P1 處置核對
部分：viewer_user_id（mock 改法）、`/mcp` 額度落點（雙落點）、謂詞條件（第 4 條錯）。已處置：額度 key 綁 API key、X-API-Key 無條件、前提偵測、疑問句夾斷言、header fail-closed（僅 mode 未定）。
