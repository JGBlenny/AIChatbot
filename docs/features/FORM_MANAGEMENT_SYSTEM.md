# 📋 動態表單收集系統

> 📦 已於 2026-09-11 部分歸檔至 [`docs/archive/2026-09/FORM_MANAGEMENT_SYSTEM.md`](../archive/2026-09/FORM_MANAGEMENT_SYSTEM.md)。
>
> ⚠️ **只有「對話式填單引擎」退役，表單管理後台仍活**，請勿誤讀為整套表單系統已下線：
>
> | 部分 | 狀態 | 說明 |
> |---|---|---|
> | 對話填單引擎（`services/form_manager.py`；歸檔文件「🔧 核心功能實作」節） | ⛔ 已退役 | 隨舊 REST 對話鏈於 2026-09-11 一併刪除，見 `.claude/DECISIONS.md` DSP-046 |
> | 表單管理 CRUD 後台（`routers/forms.py`；歸檔文件「📊 API 端點」節） | ✅ 仍活 | `GET/POST/PUT/DELETE /rag-api/v1/forms`、`/rag-api/v1/forms/{id}`、`/rag-api/v1/form-submissions` 等，容器 OpenAPI 可查證 |
> | 資料庫設計（歸檔文件「🗄️ 資料庫設計」節：`form_schemas`／`form_sessions`／`form_submissions`） | ✅ 仍活 | 表結構未隨舊鏈刪除，`form_sessions` 現由 `/mcp` 新線（`services/agent/session_persistence.py`）共用 |
>
> 換句話說：歸檔文件裡「業務需求」「系統架構」「核心功能實作」（觸發、欄位收集、離題、知識整合、Chat API 整合）等描述的是**已死的對話式填單流程**；
> 「資料庫設計」與「API 端點」兩節記的是**仍可參考的現況**。查證指令：
> `grep -n "@router\." rag-orchestrator/routers/forms.py`。
