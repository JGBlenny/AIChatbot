# AIChatbot 文檔索引

> 本文檔提供任務導向的快速查找。技術演進與深度內容請查看 [README.md](./README.md)。

**最後更新**: 2026-07-06

---

## 現況入口（2026-07-06 新增，優先讀）

| 文檔 | 用途 |
|------|------|
| [系統架構總覽](./architecture-overview.md) ⭐ | 現況單一入口：使用者×路由×面向×資料體系×計量額度×品質×已知債 |
| [統一部署 Runbook](./deployment-runbook.md) ⭐ | 33 migrations→匯入→重建→煙囪→稽核（部署唯一依據） |
| [jgb2 串接規格（正式版）](./jgb2-chat-integration.md) | 三形狀身分契約 b2b/b2c/prospect（給 jgb2 工程，含 b2b 待補齊項） |
| 盤查報告與批次 | `scripts/audit/reports/`（知識/業者SOP盤查證據鏈與可重放批次） |
| [Ground-truth Research](./research/README.md) | jgb2 原始碼盤查定案結論（各域真相依據） |
| 知識批次 | `scripts/knowledge-batches/`（部署重放依賴） |

## 架構文件（Source of Truth）

| 文檔 | 用途 |
|------|------|
| [完整對話架構](./architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md) ⭐ | 對話流程、意圖分類、SOP/KB 決策、表單狀態機、答案優化 |
| [Retriever Pipeline](./architecture/retriever-pipeline.md) ⭐ | 分數欄位定義、pipeline stage、閾值對應表 |
| [系統架構](./architecture/SYSTEM_ARCHITECTURE.md) | 全系統架構、微服務、部署 |
| [資料庫 Schema](./architecture/DATABASE_SCHEMA.md) | DB 結構、表關聯 |

## API 文件

| 文檔 | 用途 |
|------|------|
| [API 端點完整清單](./API_ENDPOINTS_COMPLETE_INVENTORY.md) | 所有端點一覽 |
| [API 文檔索引](./api/README.md) | API 規格詳細說明 |
| [JGB 外部 API 規格](./api/jgb_external_api_spec.md) | JGB 系統對接規格 |
| [JGB 合約 API 規格](./api/jgb-contracts-api-spec.md) | JGB 合約查詢規格 |
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
| [修繕表單指南](./user-guides/MAINTENANCE_FORM_USER_GUIDE.md) | 修繕報修操作 |
| [SOP 使用指南](./user-guides/VENDOR_SOP_USER_GUIDE.md) | SOP 流程操作 |
| [知識完善迴圈](./user-guides/knowledge_completion_loop.md) | 知識迴圈操作 |
| [快速開始](./user-guides/quick_start.md) | 快速上手 |

## 設計文件

| 文檔 | 用途 |
|------|------|
| [API 配置指南](./design/API_CONFIGURATION_GUIDE.md) | API 配置方式 |
| [知識動作系統設計](./design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md) | 知識庫動作架構 |
| [表單對話設計](./design/FORM_FILLING_DIALOG_DESIGN.md) | 表單填寫流程 |
| [權限系統設計](./design/PERMISSION_SYSTEM_DESIGN.md) | 權限架構 |
| [Lookup 表系統設計](./design/LOOKUP_TABLE_SYSTEM_DESIGN.md) | Lookup 系統架構 |

## 功能文件

| 文檔 | 用途 |
|------|------|
| [功能文件索引](./features/README.md) | 所有功能總覽 |
| [對話式回答＋售前顧問](./features/conversational-presales.md) | conversational 模式（多輪問答→收斂）、資料驅動設定、串流、部署 |
| [表單管理系統](./features/FORM_MANAGEMENT_SYSTEM.md) | 表單系統說明 |
| [Reranker 功能](./features/RERANKER_FEATURE.md) | 語義重排序 |
| [認證系統](./features/AUTH_SYSTEM_README.md) | 認證機制 |
| [SOP 功能](./features/sop/README.md) | SOP 系統完整說明 |

## 回測系統

| 文檔 | 用途 |
|------|------|
| [回測快速開始](./backtest/GETTING_STARTED.md) | 回測入門 |
| [知識完善迴圈](./backtest/KNOWLEDGE_COMPLETION_LOOP_GUIDE.md) | 迴圈完整指南 |
| [回測速查](./backtest/QUICK_REFERENCE.md) | 快速參考 |

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
