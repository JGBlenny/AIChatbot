# 架構文件「誰呼叫誰」驗收（2026-10-30）

業主原話：「先更新相關的架構文件 我發現你根本不清楚」「很容易做歪」「我跟問了架構 你一直不清楚 我很擔心」「我怕做錯」。

## 規則

| ID | 條件 | 來源 |
|---|---|---|
| AR-1 | 架構文件寫的呼叫路徑與程式一致：哪段走 MCP 協定、哪段是函式呼叫、誰打 JGB API | 「先更新相關的架構文件」 |
| AR-2 | 工具由 AI 提出或由程式發起，文件與程式一致 | 「很容易做歪」 |
| AR-3 | 一回合的 AI 呼叫，順序與條件都與程式一致 | 「很容易做歪」 |
| AR-4 | 現況與目標分開寫，讀者不會把目標讀成現況 | 「我怕做錯」 |

收窄：本片只核對「誰呼叫誰」相關段落，不重驗文件全文。

## 驗收清單

| 項目 | 規則 | 觀察點 | 證據 |
|---|---|---|---|
| C1 | AR-1 | `AGENTIC_MCP_ARCHITECTURE.md` §0、§0a；目標正本「實體架構」節；`CLAUDE.md`「誰呼叫誰」 | 符號對照 `mcp_facade.py`、`runtime.py`、`tools/confirm.py`、`tools/registry.py` |
| C2 | AR-1 | §0a 工具支數條件 | 容器唯讀計算 `to_openai_tools`，對照 `gate_kb_search_on_reviewed_rows` |
| C3 | AR-2 | §0a「工具由誰發起」表 | 全掃 `.call(` |
| C4 | AR-3 | §0a AI 呼叫表、§2 序列圖、§3 情境 1、共同骨架第 1 列 | 依 `run_program_segments`、`_start_write_intent_call`、`_write_draft_program_first`、`_write_draft_after_output`、`verifier.verify`、`_state_claim_gate` 的實際順序 |
| C5 | AR-1 | §6、§8、`docs/api/jgb2-web-assistant-integration.md` 接真 JGB 的未開放清單 | `WRITE_NOT_SUPPORTED_ACTIONS`、`jgb2_stats` |
| C6 | AR-4 | 目標正本四條路表與其下一段 | 對照檔首分工表、§3.1 KD、RD 列 |

## 廣度

| 項目 | 類型 | 資料組（用／可用） | 不同輸入數 | 重複次數 | 輸入撰寫者 | 改前對照 |
|---|---|---|---|---|---|---|
| C1～C6 | 機制項 | — | — | — | — | — |

上位驗收方式：無
