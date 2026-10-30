# AIChatbot 文檔總覽

本目錄收錄 AIChatbot 系統的所有技術文檔。

> **找特定主題？** 請先看 [INDEX.md](./INDEX.md) — 任務導向的快速查找索引（架構、API、指南、回測、測試等）。

---

## 文檔分類

| 目錄 | 內容 |
|------|------|
| [architecture/](./architecture/) | **目標架構**（`TARGET_ARCHITECTURE.md`，架構唯一正本）與**現況正本**：系統全景、對話線架構、Facet、Retriever Pipeline、資料庫 Schema |
| [api/](./api/) | API 規格與外部系統對接（JGB、conversational API 等） |
| [guides/](./guides/) | 操作指南（快速開始、功能使用、知識匯入匯出等） |
| [user-guides/](./user-guides/) | 非技術人員操作指南 |
| [features/](./features/) | 功能說明（⚠️ SOP 與表單只剩後台維護面，對話路徑不讀） |
| [design/](./design/) | 設計文件（知識動作、表單對話、權限、Lookup 等） |
| [deployment/](./deployment/) | 部署指南與檢查清單 |
| [backtest/](./backtest/) | ⚠️ 回測框架與知識完善迴圈的**執行面已拆除**；現行改善輪走 `.claude/skills/retrieval-improvement-loop/` |
| [testing/](./testing/) | 測試規範與整合測試指南 |
| [changelog/](./changelog/) | 歷史變更記錄 |
| [maintenance/](./maintenance/) | 系統審計與維護記錄 |
| [archive/](./archive/) | 歷史歸檔文件（依日期，如 `2026-06/`） |

---

## 常用入口

⛔ **先讀這份**（系統應該長什麼樣，設計以它為準）：

1. [`architecture/TARGET_ARCHITECTURE.md`](./architecture/TARGET_ARCHITECTURE.md) ⭐ —— 目標架構、分工、原則、與現況的差距

**現況看這三份**（2026-09-12 對碼）：

2. [`architecture/SYSTEM_ARCHITECTURE.md`](./architecture/SYSTEM_ARCHITECTURE.md) ⭐ —— 系統現在怎麼跑
3. [`architecture/AGENTIC_MCP_ARCHITECTURE.md`](./architecture/AGENTIC_MCP_ARCHITECTURE.md) ⭐ —— 一回合的完整流程（§2b）、為什麼被轉人（§4b）
4. [`api/mcp-facade.md`](./api/mcp-facade.md) —— 現行 `/mcp` 串接契約

其他：

- **統一部署**：[deployment-runbook.md](./deployment-runbook.md) ⭐（部署唯一依據）
- **jgb2 串接規格**：[jgb2-chat-integration.md](./jgb2-chat-integration.md)（⚠️ 檔頭有 2026-09-12 補正，**`tenant` 在新線不存在**）
- **參數台帳**：[retrieval-parameters.md](./retrieval-parameters.md)（含「不要動」的已裁決禁令）
- 上手：[快速開始](./guides/getting-started/QUICKSTART.md)

🔴 **2026-09-11，31 個舊 REST 對話鏈模組整批刪除**（DSP-046）：意圖分類、SOP 編排、
表單狀態機、答案優化、信心度評估全部不存在。`architecture-overview.md` 已改成指路檔；
`architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md` 只剩四節，⛔ 都不要當現況入口。

完整索引請見 [INDEX.md](./INDEX.md)。
