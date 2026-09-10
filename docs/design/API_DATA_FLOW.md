# API 數據流程完整說明

> 📦 已於 2026-09-11 歸檔至 [`docs/archive/2026-09/API_DATA_FLOW.md`](../archive/2026-09/API_DATA_FLOW.md)（原因：全文描述的動態 API 執行流程〔`routers/chat.py` 路由 → `services/universal_api_handler.py` 執行〕已隨舊 REST 對話鏈於 2026-09-11 退役，見 `.claude/DECISIONS.md` DSP-046；查證 `grep -rn "action_type" rag-orchestrator/services/agent/` 命中 0，確認 agentic-MCP 新線無此機制的執行消費者。⚠️ 本檔與同批歸檔的 `CORE_API_FUNCTIONS_REFERENCE.md` 描述同一套機制，判斷依據相同）。
