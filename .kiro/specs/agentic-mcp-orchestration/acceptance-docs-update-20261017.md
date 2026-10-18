# 驗收清單：文件更新與錯誤資訊清除（2026-10-17）

業主原話：「更新相關文件 補足 相關紀錄 並 清除錯誤 誤導的資訊」

| # | 對應業主字句 | 宣稱 | 觀察點 | 通過條件 |
|---|---|---|---|---|
| 1 | 清除錯誤 | `docs/api/mcp-facade.md` §7.1 的 `agent.turn` 參數描述與 `mcp_facade.AGENT_TURN_SPEC` 一致（五個參數、required 只有 message） | 文件 vs 程式 | 一致 |
| 2 | 清除錯誤 | `docs/api/mcp-facade.md` 逾時段：逾時回 `TOOL_TIMEOUT`、被取消不回結果、兩者都不存檔 | 文件 vs `_agent_turn`（只接 `asyncio.TimeoutError`，`store.save_row` 在 `wait_for` 之後） | 一致 |
| 3 | 清除錯誤 | `docs/architecture/SYSTEM_ARCHITECTURE.md`：`build_registry` 無條件 21 支（7＋6＋3＋5），`agent.turn` 第 22 支受 `AGENT_TURN_ENABLED` 管 | 文件 vs `build_registry`、`len(ACTION_SPECS)`、`len(STATS_SPECS)` | 一致 |
| 4 | 清除錯誤 | 兩份架構文：MCP client 只在兩支整合測試與 `scripts/smoke/mcp_smoke.py` | `grep -rln "mcp\.client\|ClientSession"` | 一致 |
| 5 | 清除錯誤 | `AGENTIC_MCP_ARCHITECTURE.md`：無 `pop("outline")`、`mcp_facade.py` 2,812 行、成本 `operation` 含 `document_extraction` | 程式 | 一致 |
| 6 | 清除錯誤 | `docs/api/jgb2-web-assistant-integration.md` 第 10 行不再觸發不變量 40 | `python3 scripts/audit/checks/doc_system_boundary.py` | PASS |
| 7 | 補足紀錄 | `.claude/DECISIONS.md` DSP-077～079 改為業主裁示的「文件依程式更正」、DSP-080 記錄 Bedrock 開源方向（原話、暫定、正式機未切）；`.claude/decisions/DSP-080.md` 的數字與 `~/jgb-archive/bedrock-eval-20261017/` 的 RESULT 檔一致 | 帳本 vs 證據檔 | 一致；`decisions.py unresolved` 不含 077～080 |
| 8 | 更新相關文件 | `HANDOFF-20261017.md` §1.2／§1.3／§2／§3.3／§3.5／§5 與現況一致（正式機 `19c38d14`、IAM 只開 gpt-oss、第一片狀態、評估數字、更正清單） | HANDOFF vs 程式／證據檔／`plan-oss-slice1-20261017.md` | 無與證據矛盾的陳述 |
