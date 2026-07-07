# AIChatbot 文檔總覽

本目錄收錄 AIChatbot 系統的所有技術文檔。

> **找特定主題？** 請先看 [INDEX.md](./INDEX.md) — 任務導向的快速查找索引（架構、API、指南、回測、測試等）。

---

## 文檔分類

| 目錄 | 內容 |
|------|------|
| [architecture/](./architecture/) | 系統架構、完整對話架構、Retriever Pipeline、資料庫 Schema（Source of Truth） |
| [api/](./api/) | API 規格與外部系統對接（JGB、conversational API 等） |
| [guides/](./guides/) | 操作指南（快速開始、功能使用、知識匯入匯出等） |
| [user-guides/](./user-guides/) | 非技術人員操作指南 |
| [features/](./features/) | 功能說明（SOP、表單、Reranker、認證等） |
| [design/](./design/) | 設計文件（知識動作、表單對話、權限、Lookup 等） |
| [deployment/](./deployment/) | 部署指南與檢查清單 |
| [backtest/](./backtest/) | 回測系統與知識完善迴圈 |
| [testing/](./testing/) | 測試規範與整合測試指南 |
| [changelog/](./changelog/) | 歷史變更記錄 |
| [maintenance/](./maintenance/) | 系統審計與維護記錄 |
| [archive/](./archive/) | 歷史歸檔文件（依日期，如 `2026-06/`） |

---

## 常用入口

- **系統現況總覽（2026-07-06 起單一入口）**：[architecture-overview.md](./architecture-overview.md) ⭐ —— 三類使用者/路由順位/21+面向登記/資料體系分工/計量額度/品質三層/已知債
- **統一部署**：[deployment-runbook.md](./deployment-runbook.md) ⭐（部署聖經，取代舊 deployment/ 指南）
- **jgb2 串接規格（b2b/b2c/售前）**：[jgb2-chat-integration.md](./jgb2-chat-integration.md)
- 架構真相來源：[完整對話架構](./architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md)、[Retriever Pipeline](./architecture/retriever-pipeline.md)
- API 一覽：[API 端點完整清單](./API_ENDPOINTS_COMPLETE_INVENTORY.md)
- 上手：[快速開始](./guides/getting-started/QUICKSTART.md)
- 部署：[部署指南](./deployment/DEPLOY_GUIDE.md)
- 回測 / 知識完善迴圈：[回測快速開始](./backtest/GETTING_STARTED.md)

完整索引請見 [INDEX.md](./INDEX.md)。
