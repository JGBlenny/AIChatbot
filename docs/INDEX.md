# AIChatbot 文檔索引

**最後更新**: 2026-01-21

---

## 📚 文檔導航

### 🚀 快速開始（新手必看）

| 文檔 | 用途 | 閱讀時間 |
|------|------|---------|
| [更新摘要](./archive/2026-01-18-update-summary.md) | 3 分鐘了解 2026-01-18 更新 | 3 分鐘 |
| [前端待辦清單](./frontend/todo.md) ⭐ | 前端開發任務（簡化版） | 10 分鐘 |
| [API 配置指南](./design/API_CONFIGURATION_GUIDE.md) | 學習如何配置 API | 20 分鐘 |
| [如何添加 API 端點](./guides/how-to-add-api-endpoints.md) | API 端點添加指南 | 15 分鐘 |

---

### 📖 詳細規格（開發者必讀）

| 文檔 | 用途 | 閱讀時間 |
|------|------|---------|
| [完整變更日誌](./archive/2026-01-18-changelog.md) | 2026-01-18 所有變更的詳細規格 | 30 分鐘 |
| [前端修改需求](./frontend/requirements.md) ⭐ | 前端詳細規格（完整版） | 40 分鐘 |
| [系統設計](./design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md) | 知識庫動作系統架構 | 30 分鐘 |
| [實作指南](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md) | 分步驟實作教學 | 40 分鐘 |

---

### 🔍 參考資料

| 文檔 | 用途 |
|------|------|
| [快速參考](./design/KNOWLEDGE_ACTION_QUICK_REFERENCE.md) | 常用配置速查表 |
| [實作範例](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md) | 程式碼範例 |
| [實作總結](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_SUMMARY.md) | 實作重點總結 |

---

### 📊 報告文檔

| 文檔 | 用途 |
|------|------|
| [部署結果](./design/DEPLOYMENT_RESULTS.md) | 部署記錄 |
| [最終報告](./design/FINAL_IMPLEMENTATION_REPORT.md) | 專案完成報告 |
| [系統驗證](./design/SYSTEM_VERIFICATION_REPORT.md) | 系統測試驗證 |

---

## 🗂️ 按主題查找

### 主題 1：API 配置

**我想...**
- ✅ 學習如何配置 API → [API 配置指南](./design/API_CONFIGURATION_GUIDE.md)
- ✅ 了解 API 如何返回數據 → [更新摘要 - 效果對比](./UPDATE_SUMMARY_2026-01-18.md#🎨-效果對比)
- ✅ 自訂欄位映射 → [更新摘要 - 如何自訂](./UPDATE_SUMMARY_2026-01-18.md#🔧-如何自訂格式化)
- ✅ 查看 API 配置範例 → [API 配置指南 - 完整範例](./design/API_CONFIGURATION_GUIDE.md#完整範例)

---

### 主題 2：資料庫

**我想...**
- ✅ 了解資料庫變更 → [完整變更日誌 - 資料庫變更規格](./archive/2026-01-18-changelog.md#💾-資料庫變更規格)
- ✅ 執行資料庫遷移 → [更新摘要 - 快速部署](./archive/2026-01-18-update-summary.md#🚀-快速部署5-步驟)
- ✅ 查看遷移腳本 → [add_action_type_and_api_config.sql](../database/migrations/add_action_type_and_api_config.sql)
- ✅ 查看範例配置 → [configure_billing_inquiry_examples.sql](../database/migrations/configure_billing_inquiry_examples.sql)

---

### 主題 3：部署

**我想...**
- ✅ 快速部署系統 → [更新摘要 - 快速部署](./archive/2026-01-18-update-summary.md#🚀-快速部署5-步驟)
- ✅ 詳細部署步驟 → [完整變更日誌 - 部署檢查清單](./archive/2026-01-18-changelog.md#🚀-部署檢查清單)

---

### 主題 4：測試

**我想...**
- ✅ 了解測試場景 → [更新摘要 - 測試場景](./archive/2026-01-18-update-summary.md#📊-測試場景)
- ✅ 查看測試規格 → [完整變更日誌 - 測試規格](./archive/2026-01-18-changelog.md#🧪-測試規格)
- ✅ 執行測試 → [實作指南 - 測試指南](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md#🧪-測試指南)

---

### 主題 5：前端開發

**我想...**
- ✅ 快速開始前端開發 → [前端待辦清單](./frontend/todo.md) ⭐
- ✅ 了解詳細的 UI 設計 → [前端修改需求](./frontend/requirements.md)
- ✅ 查看需要修改的頁面 → [前端修改需求 - 修改總覽](./frontend/requirements.md#📋-修改總覽)
- ✅ 了解 UI/UX 設計規範 → [前端修改需求 - UI/UX 設計規範](./frontend/requirements.md#🎨-uiux-設計規範)

---

### 主題 6：程式碼

**我想...**
- ✅ 了解核心修改 → [更新摘要 - 核心改動](./archive/2026-01-18-update-summary.md#🎯-核心改動3-分鐘速覽)
- ✅ 查看程式碼範例 → [實作範例](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md)
- ✅ 查看 API 參考 → [API 文檔索引](./api/README.md)

---

## 🎯 常見任務速查

### 任務 1：我要配置一個新的 API

1. 閱讀：[API 配置指南](./design/API_CONFIGURATION_GUIDE.md)
2. 參考：[範例配置](./design/API_CONFIGURATION_GUIDE.md#完整範例)
3. 修改：`rag-orchestrator/services/billing_api.py`
4. 註冊：`rag-orchestrator/services/api_call_handler.py:33-38`
5. 配置：在資料庫中插入知識或表單配置

---

### 任務 2：我要修改 API 回應格式

1. 查看當前格式化邏輯：`rag-orchestrator/services/api_call_handler.py:287-338`
2. 修改欄位映射：第 292-302 行
3. 修改特殊格式化：第 313-316 行
4. 測試：重啟服務並調用 API

---

### 任務 3：我要部署到生產環境

1. 閱讀：[更新摘要 - 快速部署](./archive/2026-01-18-update-summary.md#🚀-快速部署5-步驟)
2. 檢查：[部署檢查清單](./archive/2026-01-18-changelog.md#🚀-部署檢查清單)
3. 執行：資料庫遷移 → 重啟服務 → 測試

---

### 任務 4：我要測試系統

1. 設置：確保 `USE_MOCK_BILLING_API=true`
2. 測試場景：[測試場景表](./UPDATE_SUMMARY_2026-01-18.md#📊-測試場景)
3. 執行測試：使用 curl 或 Postman
4. 驗證結果：檢查格式化效果

---

### 任務 5：我要開發前端功能

1. 快速開始：[前端待辦清單](./frontend/todo.md)
2. 詳細規格：[前端修改需求](./frontend/requirements.md)
3. 參考範例：查看 [KnowledgeView.vue](../knowledge-admin/frontend/src/views/KnowledgeView.vue) 現有欄位
4. 測試：完成後使用 [測試檢查清單](./frontend/todo.md#🧪-測試檢查清單)

---

### 任務 6：我要了解系統架構

1. 系統設計：[KNOWLEDGE_ACTION_SYSTEM_DESIGN.md](./design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
2. 流程圖：[完整變更日誌 - 流程圖](./archive/2026-01-18-changelog.md#🔄-api-變更規格)
3. API 參考：[API 文檔索引](./api/README.md)

---

## 📂 文檔結構

```
docs/
├── INDEX.md                                    # 本文件：文檔索引
├── README.md                                   # 項目主索引
├── api/
│   └── README.md                               # API 文檔索引
├── frontend/
│   ├── requirements.md                         # 前端修改需求（詳細版）⭐
│   ├── todo.md                                 # 前端待辦清單（簡化版）⭐
│   ├── implementation-summary.md               # 前端實作總結
│   └── insertion-guide.md                      # 前端插入指南
├── guides/
│   ├── api-path-conventions.md                 # API 路徑規範
│   ├── how-to-add-api-endpoints.md             # 如何添加 API 端點
│   └── how-to-add-complete-api.md              # 如何添加完整 API
├── archive/
│   ├── 2026-01-18-changelog.md                 # 完整變更日誌
│   ├── 2026-01-18-update-summary.md            # 更新摘要（3分鐘速覽）
│   ├── 2026-01-21-archive-report.md            # 歸檔報告
│   └── [其他歷史文件]
├── fixes/                                      # 修復報告
├── testing/                                    # 測試報告
└── design/
    ├── API_CONFIGURATION_GUIDE.md              # API 配置指南 ⭐
    ├── KNOWLEDGE_ACTION_SYSTEM_DESIGN.md       # 系統設計
    ├── KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md # 實作指南
    ├── KNOWLEDGE_ACTION_QUICK_REFERENCE.md     # 快速參考
    ├── KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md # 實作範例
    ├── KNOWLEDGE_ACTION_IMPLEMENTATION_SUMMARY.md # 實作總結
    ├── DEPLOYMENT_RESULTS.md                   # 部署結果
    ├── FINAL_IMPLEMENTATION_REPORT.md          # 最終報告
    └── SYSTEM_VERIFICATION_REPORT.md           # 系統驗證

database/migrations/
├── add_action_type_and_api_config.sql          # 資料庫遷移
└── configure_billing_inquiry_examples.sql      # 範例配置

rag-orchestrator/services/
├── api_call_handler.py                         # API 調用處理器 ⭐
├── billing_api.py                              # 帳單 API 服務 ⭐
├── form_manager.py                             # 表單管理器
└── vendor_knowledge_retriever.py               # 知識檢索器
```

---

## 🔖 推薦閱讀順序

### 新手入門（1 小時）

1. [更新摘要](./archive/2026-01-18-update-summary.md) - 3 分鐘
2. [API 配置指南](./design/API_CONFIGURATION_GUIDE.md) - 20 分鐘
3. [如何添加 API 端點](./guides/how-to-add-api-endpoints.md) - 15 分鐘
4. [快速部署](./archive/2026-01-18-update-summary.md#🚀-快速部署5-步驟) - 10 分鐘
5. [測試場景](./archive/2026-01-18-update-summary.md#📊-測試場景) - 10 分鐘

### 進階開發（3 小時）

1. [完整變更日誌](./archive/2026-01-18-changelog.md) - 30 分鐘
2. [系統設計](./design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md) - 30 分鐘
3. [實作指南](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md) - 40 分鐘
4. [實作範例](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md) - 30 分鐘
5. [測試規格](./archive/2026-01-18-changelog.md#🧪-測試規格) - 30 分鐘

### 系統維護（持續）

1. [快速參考](./design/KNOWLEDGE_ACTION_QUICK_REFERENCE.md) - 隨時查閱
2. [文件檢查清單](./FILES_CHECKLIST.md) - 隨時查閱
3. [API 配置指南](./design/API_CONFIGURATION_GUIDE.md) - 隨時查閱

---

## 💡 提示

- 💬 **有問題？** 先查看 [API 配置指南 - 常見問題](./design/API_CONFIGURATION_GUIDE.md#常見問題)
- 🐛 **發現問題？** 參考 [實作指南 - 常見問題排查](./design/KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md#🐛-常見問題排查)
- 🚀 **要部署？** 使用 [更新摘要 - 快速部署](./archive/2026-01-18-update-summary.md#🚀-快速部署5-步驟)
- 📊 **要測試？** 參考 [測試場景表](./archive/2026-01-18-update-summary.md#📊-測試場景)
- 📁 **查看修復記錄？** 瀏覽 [修復報告索引](./fixes/README.md)

---

**維護者**: Claude Code
**最後更新**: 2026-01-21
