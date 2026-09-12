# AIChatbot 文檔索引

> 本文檔提供任務導向的快速查找。技術演進與深度內容請查看 [README.md](./README.md)。

**最後對碼**: 2026-09-12

---

## ⛔ 先讀這三份（現況唯一正本）

| 想知道 | 讀哪份 |
|---|---|
| **系統現在怎麼跑**（核心／門面／15 個 face／知識兩條路／六域隔離不對稱） | [`architecture/SYSTEM_ARCHITECTURE.md`](./architecture/SYSTEM_ARCHITECTURE.md) — v4.0，2026-09-12 |
| **一回合的完整流程**、**為什麼被轉人**、每個分岔與終止點 | [`architecture/AGENTIC_MCP_ARCHITECTURE.md`](./architecture/AGENTIC_MCP_ARCHITECTURE.md) — §2b 是四段 13 個終止點，§4b 是轉人的五個來源 |
| **`/mcp` 串接契約**（header、工具、錯誤碼、額度） | [`api/mcp-facade.md`](./api/mcp-facade.md) |

🔴 **2026-09-11，31 個舊 REST 對話鏈模組整批刪除**（DSP-046）：意圖分類器、SOP 編排器與
觸發器、表單狀態機、答案優化器、信心度評估器、並行檢索仲裁——**全部不存在**。
任何「為什麼這樣回答」「為什麼被轉人」的問題，⛔ 不要從這些子系統查起，
先讀上表第二列的 §4b。本檔以下各節若與上表衝突，以上表為準。

---

## 現況入口

| 文檔 | 用途 |
|------|------|
| [統一部署 Runbook](./deployment-runbook.md) ⭐ | migrations→匯入→重建→煙囪→稽核（部署唯一依據） |
| [jgb2 串接規格](./jgb2-chat-integration.md) | 給 jgb2 工程的身分契約；⚠️ 檔頭有 2026-09-11 重大更新，**`tenant` 在新線不存在** |
| [檢索與對話路由參數台帳](./retrieval-parameters.md) ⭐ | 每個可調參數的現值／動它會怎樣／有沒有實證；含「不要動」的已裁決禁令 |
| [Ground-truth Research](./research/README.md) | jgb2 原始碼盤查定案結論（各域真相依據） |
| 盤查報告與批次 | `scripts/audit/reports/`、`scripts/knowledge-batches/`（部署重放依賴） |

⚠️ **有日期的盤查報告是當時的快照**（`presales-assistant-quality-audit-20260902.md`、
`retrieval-recall-audit-20260822.md` 等）：它們量的是 2026-09-08 agentic-MCP 上線**之前**
的舊鏈行為，⛔ 不得當現況診斷依據。

## 架構文件

| 文檔 | 用途 |
|------|------|
| [系統架構](./architecture/SYSTEM_ARCHITECTURE.md) ⭐ | **現況全景正本** |
| [Agentic-MCP 對話架構](./architecture/AGENTIC_MCP_ARCHITECTURE.md) ⭐ | **對話線內部正本**（§2b 流程、§4b 轉人來源） |
| [Facet 架構](./architecture/facet-architecture.md) | 六域 15 face 的責任分層與擴充判準 |
| [Retriever Pipeline](./architecture/retriever-pipeline.md) | 分數欄位定義、pipeline stage |
| [資料庫 Schema](./architecture/DATABASE_SCHEMA.md) | DB 結構、表關聯 |
| [對話架構（殘卷）](./architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md) | ⚠️ 2026-09-12 刪至四節：三層責任分層、檢索過濾與加成、系統角色、參數速查。⛔ 其餘章節的主體已刪，不要拿它當現況入口 |

## API 文件

| 文檔 | 用途 |
|------|------|
| [API 端點完整清單（已歸檔，2026-02-17 快照）](./archive/2026-09/API_ENDPOINTS_COMPLETE_INVENTORY.md) | 歷史參考，現行端點以 routers/ 目錄為準 |
| [API 文檔索引](./api/README.md) | API 規格詳細說明 |
| [JGB 外部 API 規格](./api/jgb_external_api_spec.md) | JGB 系統對接規格 |
| [JGB 合約 API 規格](./api/jgb-contracts-api-spec.md) | JGB 合約查詢規格（部分段落已被下一項取代，見檔頭） |
| [G1–G4 API 欄位擴充契約](./api/g1-g4-api-contract.md) | 現行 `status-overview`／`bills` 端點欄位擴充，取代合約規格中查無實作的端點段落 |
| [對話式回答 API 串接](./api/conversational-api.md) | 售前 conversational 對話 API（外部專案串接） |

## 操作指南

| 文檔 | 用途 |
|------|------|
| [快速開始](./guides/getting-started/QUICKSTART.md) | 新手入門 |
| [部署指南](./deployment/DEPLOY_GUIDE.md) | 部署步驟 |
| [部署清單](./deployment/DEPLOY_CHECKLIST.md) | 部署前檢查 |
| [SOP 指南](./guides/features/SOP_GUIDE.md) | SOP 系統使用 |
| [知識匯入匯出](./guides/features/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md) | 知識庫管理 |
| [串流聊天指南](./guides/features/STREAMING_CHAT_GUIDE.md) | SSE 串流實作 |
| [快取系統](./guides/features/CACHE_SYSTEM_GUIDE.md) | Redis 快取管理 |
| [更多指南...](./guides/README.md) | 完整指南目錄 |

## 使用者指南（非技術人員）

| 文檔 | 用途 |
|------|------|
| [SOP 使用指南](./user-guides/VENDOR_SOP_USER_GUIDE.md) | SOP 後台操作（⚠️ 改 SOP 不影響機器人回答） |
| [知識完善迴圈現況](./user-guides/knowledge-loop-status.md) | 迴圈剩下什麼、想跑改善輪走哪裡 |
| [知識完善迴圈三層文件索引](./user-guides/README.md) | 入門／標準手冊／深度執行流程順序 |

## 設計文件

| 文檔 | 用途 |
|------|------|
| [權限系統設計](./design/PERMISSION_SYSTEM_DESIGN.md) | 權限架構 |
| [Lookup 表系統設計](./design/LOOKUP_TABLE_SYSTEM_DESIGN.md) | Lookup 系統架構 |

## 功能文件

| 文檔 | 用途 |
|------|------|
| [功能文件索引](./features/README.md) | 所有功能總覽 |
| [Reranker 功能](./features/RERANKER_FEATURE.md) | 語義重排序 |
| [認證系統](./features/AUTH_SYSTEM_README.md) | 認證機制 |
| [SOP 功能](./features/sop/README.md) | SOP 系統完整說明 |

## 回測系統

| 文檔 | 用途 |
|------|------|
| [客服回報案例登錄簿](./backtest/assistant-report-regression.md) | 線上「回報」案例來源、狀態追蹤、J 清單 |
| [客服回報修正 SOP](./backtest/assistant-report-workflow.md) | 回報案例修正七步流程 |

## 測試指南

| 文檔 | 用途 |
|------|------|
| [批次測試標準](./testing/BATCH_TEST_STANDARDS.md) | 測試規範 |
| [Lookup 系統測試](./testing/LOOKUP_SYSTEM_TEST_GUIDE.md) | Lookup 測試方式 |
| [API 整合測試](./testing/api-integration-testing-guide.md) | API 測試指南 |

## Issue 追蹤

| 文檔 | 用途 |
|------|------|
| [.kiro/issues/](../.kiro/issues/) | Bug / 調查記錄 |

## 其他

| 文檔 | 用途 |
|------|------|
| [前端文件](./frontend/) | 前端需求、TODO |
| [變更日誌](./changelog/) | 歷史變更記錄 |
| [維護記錄](./maintenance/) | 系統審計報告 |
| [歸檔文件](./archive/) | 歷史歸檔（依日期，如 `2026-06/`） |

---

## 文檔結構

```
docs/
├── INDEX.md                    # 本文件
├── README.md                   # 技術演進總覽
├── architecture/               # 系統架構（source of truth）
├── api/                        # API 規格
├── guides/                     # 操作指南（含子目錄）
├── user-guides/                # 非技術人員指南
├── features/                   # 功能說明
├── design/                     # 設計文件
├── backtest/                   # 回測系統
├── frontend/                   # 前端文件
├── deployment/                 # 部署指南
├── testing/                    # 測試指南
├── changelog/                  # 變更日誌
├── maintenance/                # 維護記錄
└── archive/                    # 歷史歸檔（依日期分批，如 2026-06/）
```

## Agentic MCP（2026-09-08 demo 上線）
- [Agentic MCP 對話線架構（demo 版）](architecture/AGENTIC_MCP_ARCHITECTURE.md) — `/mcp` `agent.turn`：門面→Runtime 三個程式段→工具註冊→替身；寫入鏈、別戶邊界、照片線、組態、已知限制（2026-09-08 上線）
- [LINE bot 串接資訊單](../.kiro/specs/knowledge-outline-and-intent-architecture/inputs/line-bot-integration-sheet-20260908.md) — 端點 `/rag-api/mcp`、header、機器值、select、照片、限制、自測
- [HANDOFF 2026-09-09（agentic-mcp 大改版收案）](../.kiro/specs/knowledge-outline-and-intent-architecture/HANDOFF-20260909.md)
