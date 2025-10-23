# 📋 SOP 整合實作總結

## 完成時間
2025-10-18

## 📊 實作內容

### ✅ 已完成的任務

1. **SOP 與金流模式對應關係分析**
   - 識別出 7 個金流敏感的 SOP 項目（租金支付、收據、遲付處理等）
   - 定義了「金流過我家」vs「金流不過我家」vs「混合型」的回答策略差異
   - 文檔：`docs/features/SOP_INTEGRATION_IMPLEMENTATION.md`（本文件）

2. **資料庫結構設計與建立**
   - Migration 檔案：`database/migrations/33-create-vendor-sop-tables.sql`
   - 新增表：
     - `vendor_sop_categories` - SOP 分類表
     - `vendor_sop_items` - SOP 項目表（支援金流模式與業種類型動態調整）
   - 擴充 `vendors` 表：
     - `business_type` - 業種類型（full_service, property_management）
     - `cashflow_model` - 金流模式（through_company, direct_to_landlord, mixed）
   - 建立檢視：`v_vendor_sop_full` - SOP 完整資訊檢視

3. **SOP 檢索服務實作**
   - 檔案：`rag-orchestrator/services/vendor_sop_retriever.py`
   - 功能：
     - 根據意圖檢索 SOP
     - 根據分類檢索 SOP
     - 根據金流模式動態調整內容
     - 根據業種類型動態調整語氣
   - 支援快取機制

4. **SOP 匯入腳本**
   - 檔案：`scripts/import_sop_from_excel.py`
   - 功能：
     - 解析 Excel 格式的 SOP 文件
     - 自動識別金流敏感項目
     - 生成不同金流模式的內容版本
     - 批量匯入到資料庫

---

## 🏗️ 架構設計

### 1. 回話邏輯架構（4 層結構）

```
Layer 1: 業種類型判斷
├── full_service (包租型) → 公司立場、主動確認
└── property_management (代管型) → 協助方立場、引導聯繫房東

Layer 2: 金流模式判斷
├── through_company (金流過我家) → 公司帳戶、主動催繳
├── direct_to_landlord (金流不過我家) → 房東帳戶、僅提醒
└── mixed (混合型) → 先詢問合約類型

Layer 3: SOP 流程對照
├── 租賃流程相關資訊 (16 項)
├── 租賃管理工具與平台 (6 項)
├── 維護與修繕服務 (6 項)
└── 租客權益與法律問題 (0 項)

Layer 4: 共用知識庫（RAG fallback）
└── 向量搜尋 + 意圖分類
```

### 2. 資料表關係

```sql
vendors (業者表)
├── business_type (業種類型)
├── cashflow_model (金流模式)
└── ... (其他業者資訊)

vendor_sop_categories (SOP 分類表)
├── vendor_id → vendors.id
├── category_name (分類名稱)
└── display_order (顯示順序)

vendor_sop_items (SOP 項目表)
├── category_id → vendor_sop_categories.id
├── vendor_id → vendors.id
├── content (基礎內容)
├── cashflow_through_company (金流過我家版本)
├── cashflow_direct_to_landlord (金流不過我家版本)
├── business_type_full_service (包租型語氣)
├── business_type_management (代管型語氣)
└── related_intent_id → intents.id
```

---

## 🔄 工作流程

### 用戶問問題時的處理流程

```python
1. 接收用戶問題
   ↓
2. 意圖分類（IntentClassifier）
   ↓
3. 檢查是否有對應的 SOP 項目
   ├─ 有 → 繼續 SOP 流程
   └─ 無 → Fallback 到 RAG 檢索
   ↓
4. 獲取業者資訊（VendorParameterResolver）
   ├─ business_type: full_service / property_management
   └─ cashflow_model: through_company / direct_to_landlord / mixed
   ↓
5. 檢索 SOP（VendorSOPRetriever）
   ├─ 根據 requires_cashflow_check 判斷是否需要金流模式調整
   ├─ 選擇對應的內容版本
   └─ 根據 requires_business_type_check 調整語氣
   ↓
6. LLM 答案優化（LLMAnswerOptimizer）
   ├─ 接收 SOP 項目內容
   ├─ 根據 business_type 調整系統提示詞
   └─ 生成最終答案
   ↓
7. 返回答案給用戶
```

---

## 📝 金流模式範例對比

### 範例 1：租金支付方式

| 金流模式 | 回答內容 |
|---------|---------|
| **金流過我家** | "登入JGB系統查看**公司收款帳號**，可通過銀行轉帳、信用卡支付或超商代碼繳款。" |
| **金流不過我家** | "請向**房東**索取收款帳號，建議使用銀行轉帳並留存交易記錄。" |
| **混合型** | "請問您的合約是哪種繳費方式？（公司代收/直接給房東）" |

### 範例 2：租金遲付處理

| 金流模式 | 回答內容 |
|---------|---------|
| **金流過我家** | "**JGB系統**會自動發送催繳通知並依約收取滯納金，請儘速完成繳款。" |
| **金流不過我家** | "**房東**會處理遲付事宜，JGB系統僅協助發送提醒通知。請您主動聯繫房東說明情況。" |

### 範例 3：押金退還

| 金流模式 | 回答內容 |
|---------|---------|
| **金流過我家** | "押金由**公司**收取並專戶保管，租約結束後會根據房屋狀況於7個工作天內退還。" |
| **金流不過我家** | "押金由**房東**收取，租約結束後請與房東確認退還時間與方式。" |

---

## ⚙️ 設定範例

### 設定業者類型與金流模式

```sql
-- 設定業者 1 為包租型（金流過我家）
UPDATE vendors
SET business_type = 'full_service',
    cashflow_model = 'through_company'
WHERE id = 1;

-- 設定業者 2 為代管型（金流不過我家）
UPDATE vendors
SET business_type = 'property_management',
    cashflow_model = 'direct_to_landlord'
WHERE id = 2;
```

---

## 🔧 待完成任務

### 高優先級（2週內）

1. ⏰ **修改 LLM 優化器整合 SOP**
   - 修改 `LLMAnswerOptimizer._create_system_prompt()` 支援業種類型與金流模式
   - 在 `chat.py` 中整合 `VendorSOPRetriever`

2. ⏰ **執行 SOP 匯入**
   - 將 `20250305 real_estate_rental_knowledge_base SOP.xlsx` 匯入資料庫
   - 驗證資料完整性

3. ⏰ **測試金流模式分支邏輯**
   - 測試「金流過我家」場景
   - 測試「金流不過我家」場景
   - 測試語氣差異

### 中優先級（1個月內）

4. 📅 **補充其他金流敏感項目的版本**
   - 完善 `cashflow_through_company` 和 `cashflow_direct_to_landlord` 內容
   - 新增 `cashflow_mixed` 版本的引導話術

5. 📅 **建立 SOP 管理介面**
   - 前端介面：新增/編輯/刪除 SOP
   - 支援批量匯入
   - 預覽不同金流模式的差異

6. 📅 **SOP 與意圖的自動關聯**
   - 根據 SOP 項目名稱自動匹配相關意圖
   - 支援手動調整關聯

### 低優先級（未來規劃）

7. 🔮 **多輪對話狀態管理（Phase 2）**
   - 參考 `docs/B2B_API_INTEGRATION_DESIGN.md`
   - 實作 SessionManager
   - 實作 FlowOrchestrator（狀態機控制）

8. 🔮 **SOP 流程可視化**
   - 流程圖編輯器
   - 流程執行追蹤
   - 流程分析報表

---

## 📊 系統影響評估

### 對現有系統的影響

| 模組 | 影響程度 | 說明 |
|------|---------|-----|
| **資料庫** | ✅ 低 | 新增 2 張表，擴充 1 張表（向後兼容） |
| **RAG Orchestrator** | ⚠️ 中 | 需整合 `VendorSOPRetriever`，但不影響現有 RAG fallback |
| **LLM Optimizer** | ⚠️ 中 | 需修改 `_create_system_prompt()`，支援 business_type |
| **Chat API** | ⚠️ 中 | 需在回答前先檢索 SOP，但保留原有邏輯 |
| **Knowledge Admin** | ✅ 低 | 可選：新增 SOP 管理介面 |

### 效能影響

- **額外查詢**：每次 Chat 請求新增 1-2 次資料庫查詢（可透過快取優化）
- **記憶體**：vendor_info 快取約 1KB/業者
- **回應時間**：預估增加 10-20ms（資料庫查詢時間）

---

## 🎯 預期效果

### 1. 回答準確性提升

- 金流相關問題的回答錯誤率預計降低 **80%**
- 不再出現「請匯款到公司帳戶」但實際是直接給房東的錯誤

### 2. 用戶體驗改善

- 包租型業者：用戶感受到**主動服務**
- 代管型業者：用戶理解**協助角色**，不會對 AI 產生過高期待

### 3. 系統擴展性增強

- 新增業者時，只需設定 `business_type` 和 `cashflow_model`
- SOP 更新透過資料庫，不需修改程式碼

---

## 📚 相關文件

- [B2B API 整合框架設計](./B2B_API_INTEGRATION_DESIGN.md) - Phase 2 多輪對話與狀態管理
- [Business Scope 重構](../architecture/BUSINESS_SCOPE_REFACTORING.md) - B2B/B2C 場景隔離
- [多業者實作](../planning/PHASE1_MULTI_VENDOR_IMPLEMENTATION.md) - Phase 1 架構設計

---

## 💡 未來優化方向

1. **AI 自動生成 SOP 版本**
   - 根據基礎內容，AI 自動生成「金流過我家」和「金流不過我家」版本
   - 減少人工撰寫成本

2. **SOP 版本控制**
   - 記錄 SOP 修改歷史
   - 支援 A/B 測試不同版本的效果

3. **智能 SOP 推薦**
   - 根據用戶問題，推薦應該新增的 SOP 項目
   - 分析常見問題與現有 SOP 的覆蓋率

4. **跨業者 SOP 共享**
   - 建立通用 SOP 模板庫
   - 業者可以選擇套用並微調

---

**建立時間**: 2025-10-18
**建立者**: Claude Code
**狀態**: ✅ 資料表建立完成 / ⏰ 等待整合測試
