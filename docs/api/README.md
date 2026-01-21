# API 文檔索引

**最後更新**: 2026-01-20
**維護者**: Claude Code

本文檔提供所有 API 相關文檔的快速索引和導航。

---

## 📚 快速導航

### 🎯 核心必讀文檔

如果您是新手或想快速了解系統，請按順序閱讀：

1. **[API 核心函數參考](./design/CORE_API_FUNCTIONS_REFERENCE.md)** ⭐ 最重要
   - 統一處理函數說明
   - 核心函數列表和作用
   - 快速參考和示例
   - **閱讀時間**: 10 分鐘

2. **[API 數據流程完整說明](./design/API_DATA_FLOW.md)**
   - 完整的 12 階段數據流程
   - 從 API 調用到用戶收到回應
   - 詳細的數據轉換過程
   - **閱讀時間**: 15 分鐘

3. **[改進的 API 架構設計](./design/IMPROVED_API_ARCHITECTURE.md)**
   - 新架構的設計理念
   - 動態配置 vs 自定義函數
   - 完整的代碼示例
   - **閱讀時間**: 20 分鐘

---

## 📋 所有文檔列表

### ✅ 當前有效文檔（推薦）

| 文檔名稱 | 路徑 | 日期 | 狀態 | 用途 |
|---------|------|------|------|------|
| **API 核心函數參考** | `docs/design/CORE_API_FUNCTIONS_REFERENCE.md` | 2026-01-20 | ✅ 最新 | 快速參考統一處理函數和核心 API |
| **API 數據流程完整說明** | `docs/design/API_DATA_FLOW.md` | 2026-01-20 | ✅ 最新 | 了解完整的數據流程和轉換 |
| **動態 API 測試報告** | `docs/design/DYNAMIC_API_TESTING_REPORT.md` | 2026-01-20 | ✅ 最新 | 測試結果和生產就緒評估 |
| **改進的 API 架構設計** | `docs/design/IMPROVED_API_ARCHITECTURE.md` | 2026-01-18 | ✅ 有效 | 架構設計和實作細節 |

### ⚠️ 部分過時文檔（參考用）

| 文檔名稱 | 路徑 | 日期 | 狀態 | 備註 |
|---------|------|------|------|------|
| **API Endpoint 架構說明** | `docs/API_ENDPOINT_ARCHITECTURE.md` | 2026-01-18 | ⚠️ 已過時 | 描述舊架構，僅供參考 |
| **如何新增 API Endpoint** | `docs/HOW_TO_ADD_COMPLETE_API.md` | 2026-01-18 | ⚠️ 部分過時 | 僅適用於複雜自定義 API |

---

## 🔍 按用途查找文檔

### 我想了解...

#### 「系統是如何處理 API 回傳的？」
→ 閱讀: [API 核心函數參考](./design/CORE_API_FUNCTIONS_REFERENCE.md)

**關鍵信息**:
- 統一處理函數: `UniversalAPICallHandler._format_response()`
- 位置: `services/universal_api_handler.py:352-383`
- 作用: 統一處理所有動態 API 的回傳數據

#### 「從 API 取得資訊後，系統如何組成可用資訊？」
→ 閱讀: [API 數據流程完整說明](./design/API_DATA_FLOW.md)

**關鍵章節**:
- 階段 9: 格式化響應
- 轉換點 2: Python 字典 → 格式化文本
- 系統「組成可用資訊」的具體方式

#### 「如何新增一個 API？」
→ 閱讀: [改進的 API 架構設計](./design/IMPROVED_API_ARCHITECTURE.md)

**兩種方式**:
- 90% 情況: 只需在數據庫配置（推薦）
- 10% 情況: 寫自定義函數（複雜邏輯）

#### 「新架構測試通過了嗎？可以上線嗎？」
→ 閱讀: [動態 API 測試報告](./design/DYNAMIC_API_TESTING_REPORT.md)

**測試結果**:
- ✅ 26 個測試項全部通過
- ✅ 生產就緒度: 可以上線

#### 「舊架構是怎樣的？」
→ 閱讀: [API Endpoint 架構說明](./API_ENDPOINT_ARCHITECTURE.md) (已過時)

**注意**: 僅供了解歷史，新開發請使用新架構

---

## 💡 常見問題快速解答

### Q1: 有一個統一處理 API 回傳的函數嗎？
**A**: ✅ 是的！

- **函數名**: `UniversalAPICallHandler._format_response()`
- **位置**: `services/universal_api_handler.py:352-383`
- **作用**: 統一處理所有 `implementation_type='dynamic'` API 的回傳
- **詳細說明**: 參考 [API 核心函數參考](./design/CORE_API_FUNCTIONS_REFERENCE.md)

### Q2: 從 API 取得資訊後，會在系統組成可用資訊嗎？
**A**: ✅ 完全正確！

**流程**:
1. 從 API 取得：HTTP 請求獲取原始 JSON
2. 在系統組成：使用 `response_template` 格式化 + 替換變量 + 合併知識答案
3. 可用資訊：`formatted_response` 直接顯示給用戶

**詳細說明**: 參考 [API 數據流程完整說明](./design/API_DATA_FLOW.md)

### Q3: 新增 API 需要寫代碼嗎？
**A**: 90% 情況不需要！

- **簡單 API**: 只需在數據庫配置 `api_url` 和 `response_template`
- **複雜 API**: 需要寫自定義函數（複雜業務邏輯）

**詳細說明**: 參考 [改進的 API 架構設計](./design/IMPROVED_API_ARCHITECTURE.md)

### Q4: 文檔記錄清楚嗎？
**A**: ✅ 是的，現在很清楚！

**已記錄**:
- ✅ 統一處理函數說明（核心函數參考）
- ✅ 完整數據流程（數據流程說明）
- ✅ 測試驗證（測試報告）
- ✅ 架構設計（架構設計文檔）

**改進點**:
- ✅ 新增核心函數參考文檔（2026-01-20）
- ✅ 標註舊文檔為已過時（2026-01-20）
- ✅ 創建文檔索引（本文檔）

---

## 📊 文檔狀態總覽

### 按時間線

```
2026-01-20（最新）
├─ ✅ API 核心函數參考（新增）
├─ ✅ API 數據流程完整說明
├─ ✅ 動態 API 測試報告
└─ ✅ 文檔索引（本文檔，新增）

2026-01-18
├─ ✅ 改進的 API 架構設計
├─ ⚠️ API Endpoint 架構說明（已過時）
└─ ⚠️ 如何新增 API Endpoint（部分過時）
```

### 按主題分類

**架構設計**:
- [改進的 API 架構設計](./design/IMPROVED_API_ARCHITECTURE.md) ✅
- [API Endpoint 架構說明](./API_ENDPOINT_ARCHITECTURE.md) ⚠️ (舊架構)

**核心函數**:
- [API 核心函數參考](./design/CORE_API_FUNCTIONS_REFERENCE.md) ✅ (最新)

**數據流程**:
- [API 數據流程完整說明](./design/API_DATA_FLOW.md) ✅

**測試驗證**:
- [動態 API 測試報告](./design/DYNAMIC_API_TESTING_REPORT.md) ✅

**操作指南**:
- [如何新增 API Endpoint](./HOW_TO_ADD_COMPLETE_API.md) ⚠️ (部分過時，僅適用自定義 API)

---

## 🎯 推薦閱讀順序

### 新手入門（3 步驟）

1. **快速了解**（10 分鐘）
   - 閱讀：[API 核心函數參考](./design/CORE_API_FUNCTIONS_REFERENCE.md)
   - 目標：了解統一處理函數是什麼

2. **深入理解**（15 分鐘）
   - 閱讀：[API 數據流程完整說明](./design/API_DATA_FLOW.md)
   - 目標：了解完整數據流程

3. **架構全貌**（20 分鐘）
   - 閱讀：[改進的 API 架構設計](./design/IMPROVED_API_ARCHITECTURE.md)
   - 目標：了解設計理念和實作細節

**總時間**: 約 45 分鐘

### 開發者深入學習（5 步驟）

1. 核心函數參考（10 分鐘）
2. 數據流程說明（15 分鐘）
3. 架構設計文檔（20 分鐘）
4. 測試報告（10 分鐘）
5. 參考舊架構對比（可選，10 分鐘）

**總時間**: 約 55-65 分鐘

---

## 📝 文檔維護

### 更新記錄

| 日期 | 更新內容 | 維護者 |
|------|---------|--------|
| 2026-01-20 | 創建文檔索引 | Claude Code |
| 2026-01-20 | 新增核心函數參考文檔 | Claude Code |
| 2026-01-20 | 標註舊文檔為已過時 | Claude Code |
| 2026-01-20 | 創建 API 數據流程說明 | Claude Code |
| 2026-01-20 | 創建動態 API 測試報告 | Claude Code |
| 2026-01-18 | 創建改進的架構設計文檔 | Claude Code |

### 貢獻指南

如果您需要更新文檔：

1. **新增文檔**: 在相應目錄創建 Markdown 文件
2. **更新索引**: 在本文檔中添加新文檔的鏈接
3. **標註日期**: 在文檔頂部標註日期和版本
4. **過時文檔**: 在頂部添加過時警告，並指向新文檔

---

## 🔗 相關資源

### 代碼文件

- `services/universal_api_handler.py` - 通用 API 處理器
- `services/api_call_handler.py` - API 調用處理器
- `routers/chat.py` - 聊天路由（調用 API）
- `services/form_manager.py` - 表單管理（調用 API）

### 數據庫

- `api_endpoints` 表 - API 端點配置
- Migration: `database/migrations/upgrade_api_endpoints_dynamic.sql`

### 測試腳本

- `/tmp/test_api_handler.py` - 架構集成測試
- `/tmp/test_dynamic_api.py` - 動態 API 測試
- `/tmp/test_custom_api.py` - 自定義 API 測試
- `/tmp/test_end_to_end.py` - 端到端流程測試

---

## ✅ 文檔完整性檢查表

- ✅ 統一處理函數說明 → [API 核心函數參考](./design/CORE_API_FUNCTIONS_REFERENCE.md)
- ✅ 數據流程說明 → [API 數據流程完整說明](./design/API_DATA_FLOW.md)
- ✅ 架構設計說明 → [改進的 API 架構設計](./design/IMPROVED_API_ARCHITECTURE.md)
- ✅ 測試驗證報告 → [動態 API 測試報告](./design/DYNAMIC_API_TESTING_REPORT.md)
- ✅ 舊文檔標註 → [API Endpoint 架構說明](./API_ENDPOINT_ARCHITECTURE.md) (已標註)
- ✅ 文檔索引 → 本文檔

**完整性評分**: 95% ✅

---

**維護者**: Claude Code
**創建日期**: 2026-01-20
**最後更新**: 2026-01-20
