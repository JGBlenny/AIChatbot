# r5 plan-verifier（業主目標驗證：JGB 相關服務經 MCP 做對話／語音）— tasks 25 項＋design 1.3（2026-09-04）

REVISE

[P0] 照 tasks 做完，MCP client 只拿到工具，無整回合能力；`AgentRuntime`＋Verifier＋固定句只從 `routers/chat.py:handle_conversational_entry` REST／SSE 進 — 建議：新增 `agent.turn` MCP 工具，或明文定案「JGB 端自帶模型」並寫入代價（Verifier／固定句不生效）。
[P0] 對話實際由 REST 達成且硬限 prospect（`CONVERSATIONAL_ENABLED_ROLES={'prospect'}`）；LINE 租客與語音來電者屬 tenant，M4／M5 另案 — 建議：tasks 明列本 spec 可對話對象只有 prospect，子 spec `agent-tenant-audience` 給 ID／outcome／前置。
[P1] MCP 路徑無逐字串流契約（research 主題 1 只載 Context／progress） — 建議：查證定案；無法串流則語音走 REST SSE。
[P1] 串流與 Verifier 順序未定：逐字先送 ⇒ 被拒文字外洩；等判完 ⇒ 首字＝整段時間 — 建議：sentence-level gate 或明文接受首字＝整段完成。
[P1] `session_id` 由誰產生、對話歷史誰保存，tasks 全無；LINE 租客 `role_id=null` 的合法組合未給 — 建議：1.7 加契約文件。
[P2] 外部可信服務憑證簽發流程與 Origin 對 server-to-server 語義未定 — 建議：5.3 runbook 加簽發指令；design 明訂 `/mcp` 僅 server-to-server。
[P2] 語音預算差一量級、無 barge-in — 建議：子 spec `voice-turn-budget`。
[P3] 對照表大項 1 無「MCP client 完成一段對話」驗收格。

目標達成路徑：現行 25 項做完，JGB 端只有 (1) REST `/api/v1/message`＋SSE 拿完整回合（僅 prospect）(2) `/mcp` 拿工具自備模型（品質保證不隨工具過來）。要「連上 /mcp 就能對話」需補 `agent.turn`＋tenant audience；語音再加串流定案與語音預算子 spec。
待查：MCP 工具結果能否增量串流；`form_sessions` 對 LINE userId／通話 session 是否可用；LINE bot 側能否承接 `handoff{channel,message}`。
