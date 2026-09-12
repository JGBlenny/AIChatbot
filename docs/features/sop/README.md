# 📚 SOP 系統文檔索引

**最後對碼**: 2026-09-12

🔴 **SOP 的「影響對話」那一半已經沒有了。**

| 這裡的文檔教的 | 現況 |
|---|---|
| 建立／編輯／複製 SOP 範本與項目、批次匯入、embedding 重算 | ✅ 仍可用（`routers/platform_sop.py` 15 條路由、`routers/vendors.py` 10 支 `/sop/*`、`sop_embedding_generator.py`） |
| 觸發模式（none／manual／immediate／auto）、後續動作（form_fill／api_call／form_then_api）、關鍵詞觸發、SOP↔知識仲裁 | ⛔ **對話路徑零讀取**。`sop_orchestrator.py`／`sop_trigger_handler.py`／`form_manager.py` 已於 2026-09-11 刪除（DSP-046）。查證：`grep -rli "sop" rag-orchestrator/services/agent/` 為 0（正對照：同目錄 `kb` 13 檔、`verifier` 20 檔） |

**結論：改 SOP 不會改變機器人的任何回答。** 以下各份文檔請套用上表閱讀——
欄位存得進 DB，但沒有任何程式會在對話時查它們。
現行對話走 `/mcp` 的 `agent.turn`，見
[`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md`](../../architecture/AGENTIC_MCP_ARCHITECTURE.md)。

⚠️ 下方「目錄結構」的檔數（design 4／implementation 6／testing 3／optimization 2）
是 2026-02 的快照；**實際現況**：`design/` 不存在、`implementation/` 3 份、
`testing/` 1 份、`optimization/` 1 份。
---

## 🗂️ 目錄結構

```
sop/
├── README.md                           # 本文件
├── SOP_TRIGGER_MODE_UPDATE_INDEX.md    # 2026-02-03 的 UI 更新紀錄（歷史）
├── implementation/                     # 3 份
├── testing/                            # 1 份
└── optimization/                       # 1 份
```

---

## ⭐ 快速開始

**想了解 SOP 系統？** 從這裡開始：

| 文檔 | 用途 | 閱讀時間 |
|------|------|---------|
| [SOP_GUIDE.md](../../guides/features/SOP_GUIDE.md) | SOP 後台操作指南（⚠️ 觸發／後續動作那幾節對話路徑不讀） | 30 分鐘 |
| [`docs/user-guides/VENDOR_SOP_USER_GUIDE.md`](../../user-guides/VENDOR_SOP_USER_GUIDE.md) | 業者端操作（檔頭有對碼表） | — |

---

## 🎨 設計文檔

**適合**: 了解 SOP 系統設計思路、架構決策

| 文檔 | 說明 | 日期 |
|------|------|------|
| [SOP_TYPES_ANALYSIS_2026-01-22.md](../../archive/2026-06/sop/SOP_TYPES_ANALYSIS_2026-01-22.md) | SOP 類型分析 | 2026-01-22 |
| [SOP_UI_DESIGN_2026-01-22.md](../../archive/2026-06/sop/SOP_UI_DESIGN_2026-01-22.md) | SOP UI 設計規劃 | 2026-01-22 |
| [SOP_NEXT_ACTION_DESIGN_2026-01-22.md](../../archive/2026-06/sop/SOP_NEXT_ACTION_DESIGN_2026-01-22.md) | SOP Next Action 設計 | 2026-01-22 |
| [SOP_CONVERSATION_FLOW_2026-01-22.md](../../archive/2026-06/sop/SOP_CONVERSATION_FLOW_2026-01-22.md) | SOP 對話流程設計 | 2026-01-22 |

---

## 💻 實作文檔

**適合**: 開發人員、需要了解實作細節

| 文檔 | 說明 | 日期 |
|------|------|------|
| [SOP_NEXT_ACTION_IMPLEMENTATION.md](./implementation/SOP_NEXT_ACTION_IMPLEMENTATION.md) | SOP Next Action 實作 | - |
| [SOP_NEXT_ACTION_IMPLEMENTATION_SUMMARY.md](../../archive/2026-06/sop/SOP_NEXT_ACTION_IMPLEMENTATION_SUMMARY.md) | SOP Next Action 實作總結 | - |
| [SOP_TRIGGER_MODE_UI_UPDATE_2026-02-03.md](../../archive/2026-06/sop/SOP_TRIGGER_MODE_UI_UPDATE_2026-02-03.md) | SOP 觸發模式 UI 更新 | 2026-02-03 |
| [SOP_FLOW_STRICT_VALIDATION_2026-01-26.md](./implementation/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md) | SOP Flow 嚴格驗證 | 2026-01-26 |
| [VENDOR_SOP_FLOW_CONFIGURATION.md](./implementation/VENDOR_SOP_FLOW_CONFIGURATION.md) | 廠商 SOP 流程配置 | - |
| VENDOR_SOP_RETRIEVAL_IMPROVEMENT.md | 廠商 SOP 檢索改進 | - |

---

## 🧪 測試文檔

**適合**: QA、測試人員、驗證功能

| 文檔 | 說明 | 日期 |
|------|------|------|
| [SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE.md](./testing/SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE.md) | SOP 觸發模式測試執行指南 | - |
| [TEST_SOP_VERIFICATION_REPORT.md](../../archive/2026-06/sop/TEST_SOP_VERIFICATION_REPORT.md) | SOP 驗證測試報告 | 2026-01-26 |
| [sop_coverage_report.md](../../archive/2026-06/sop/sop_coverage_report.md) | SOP 覆蓋率報告 | 2026-01-26 |

---

## ⚡ 優化文檔

**適合**: 性能優化、系統改進

| 文檔 | 說明 | 日期 |
|------|------|------|
| [SOP_KEYWORDS_COMPARISON.md](./optimization/SOP_KEYWORDS_COMPARISON.md) | SOP Keywords 方案對比 | - |
| [SOP_KEYWORDS_IMPLEMENTATION_2026-02-11.md](../../archive/2026-06/sop/SOP_KEYWORDS_IMPLEMENTATION_2026-02-11.md) | SOP Keywords 實作說明 | 2026-02-11 |

---

## 🎯 常見任務導航

### 任務 1: 我要了解 SOP 系統的基本概念
1. 閱讀 [SOP_GUIDE.md](../../guides/features/SOP_GUIDE.md)
2. 查看 [SOP_TYPES_ANALYSIS](../../archive/2026-06/sop/SOP_TYPES_ANALYSIS_2026-01-22.md)

### 任務 2: 我要配置 SOP 觸發模式
1. 閱讀 [SOP_TRIGGER_MODE_UPDATE_INDEX.md](./SOP_TRIGGER_MODE_UPDATE_INDEX.md)
2. 參考 [SOP_TRIGGER_MODE_UI_UPDATE](../../archive/2026-06/sop/SOP_TRIGGER_MODE_UI_UPDATE_2026-02-03.md)

### 任務 3: 我要測試 SOP 功能
1. 使用 [SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE](./testing/SOP_TRIGGER_MODE_TEST_EXECUTION_GUIDE.md)
2. 參考 [TEST_SOP_VERIFICATION_REPORT](../../archive/2026-06/sop/TEST_SOP_VERIFICATION_REPORT.md)

### 任務 4: 我要優化 SOP 檢索效果
1. 了解 [SOP_KEYWORDS_COMPARISON](./optimization/SOP_KEYWORDS_COMPARISON.md)
2. 實作 [SOP_KEYWORDS_IMPLEMENTATION](../../archive/2026-06/sop/SOP_KEYWORDS_IMPLEMENTATION_2026-02-11.md)

### 任務 5: 我要改進 SOP 對話流程
1. 查看 [SOP_CONVERSATION_FLOW](../../archive/2026-06/sop/SOP_CONVERSATION_FLOW_2026-01-22.md)
2. 參考 [SOP_FLOW_STRICT_VALIDATION](./implementation/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md)

### 任務 6: 我要配置廠商專屬 SOP
1. 閱讀 [VENDOR_SOP_FLOW_CONFIGURATION](./implementation/VENDOR_SOP_FLOW_CONFIGURATION.md)
2. 參考 VENDOR_SOP_RETRIEVAL_IMPROVEMENT

---

## 📊 SOP 系統演進時間線

```
2026-02-11  ─  SOP Keywords 優化實作
2026-02-03  ─  SOP 觸發模式 UI 優化
2026-01-26  ─  SOP Flow 嚴格驗證 + 測試報告
2026-01-22  ─  SOP 系統設計文檔系列（類型分析、UI設計、Next Action、對話流程）
更早期     ─  SOP 基礎實作、檢索改進
```

---

## 🔗 相關資源

### 主要文檔
- **SOP 使用指南**: [docs/guides/features/SOP_GUIDE.md](../../guides/features/SOP_GUIDE.md)
- **SOP 快速參考**: [docs/guides/reference/SOP_QUICK_REFERENCE.md](../../guides/reference/SOP_QUICK_REFERENCE.md)
- **SOP Excel 匯入**: [docs/guides/features/SOP_EXCEL_IMPORT_GUIDE.md](../../guides/features/SOP_EXCEL_IMPORT_GUIDE.md)

### 其他相關
- **主文檔索引**: [docs/INDEX.md](../../INDEX.md)
- **技術更新**: [docs/README.md](../../README.md)
- **功能文檔**: [docs/features/](../)

---

## 📝 文檔維護

### 新增 SOP 文檔時

請按照以下分類放置：
- **設計文檔** → `design/`
- **實作文檔** → `implementation/`
- **測試文檔** → `testing/`
- **優化文檔** → `optimization/`

並更新本 README.md 索引。

### 文檔命名規範

```
設計: SOP_{FEATURE}_DESIGN_{DATE}.md
實作: SOP_{FEATURE}_IMPLEMENTATION_{DATE}.md
測試: SOP_{FEATURE}_TEST_{DATE}.md
優化: SOP_{FEATURE}_OPTIMIZATION_{DATE}.md
```

---

**維護者**: AIChatbot Team
**最後更新**: 2026-02-14
**整合日期**: 2026-02-14 (P1 文檔整理)
**文件總數**: 16 個 (1 個索引 + 4 個設計 + 6 個實作 + 3 個測試 + 2 個優化)
