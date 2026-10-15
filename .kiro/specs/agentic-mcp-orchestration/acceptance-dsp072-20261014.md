# 驗收清單：DSP-072 暫定 gpt-6-luna（凍結 2026-10-14）

## 業主原話
- 2026-10-14 對話：「先暫定 gpt-6-luna 並更新相關文件」
- 2026-10-14 對話：「派一個 verifier 驗 目前系統 預設 gpt-6-luna」

## 清單

| # | 服務的業主原話 | 觀察點（業主使用的層） | 證據型態 |
|---|---|---|---|
| A1 | 「目前系統 預設 gpt-6-luna」 | 對話主線實際會用的模型：`rag-orchestrator/services/agent/runtime.py` 中 `AgentRuntime` 的模型決定邏輯（`AGENT_MODEL`→`OPENAI_MODEL`→程式預設值） | 程式原文＋可重跑 grep 指令 |
| A2 | 「目前系統 預設 gpt-6-luna」 | 部署組態預設值：`docker-compose.prod.yml` 的 `rag-orchestrator` 服務中 `AGENT_MODEL`、`OPENAI_MODEL` 插值預設 | 檔案原文＋grep |
| A3 | 「目前系統 預設 gpt-6-luna」 | 本機執行中容器 `aichatbot-rag-orchestrator` 實際環境變數 `AGENT_MODEL`、`OPENAI_MODEL`（`docker exec … printenv`，只印這兩個鍵） | 實跑指令輸出 |
| A4 | 「目前系統 預設 gpt-6-luna」 | 部署手冊指示部署者設定的值：`docs/deployment-runbook.md` §20-2 env 區塊的 `AGENT_MODEL=` 行 | 檔案原文 |
| A5 | 「更新相關文件」 | `.claude/DECISIONS.md` DSP-072、`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` §6 模型列與 §9 假設表、`docs/deployment-runbook.md` §20-2 警示段，皆記載「暫定 gpt-6-luna」，且 ⛔ 不得宣稱已是系統預設或已上線（須與 A1–A4 實況一致） | 檔案原文對照 A1–A4 |

## 非目標（理由）
- 正式機 `.env` 實際值：本 session 無正式機存取權限，不在本次驗收範圍（由業主或管理員另查）。
- gpt-6-luna 的答題品質：未實測，DSP-072 已標明，不在本次驗收範圍。
