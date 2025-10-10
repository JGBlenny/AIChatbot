# Phase 1: 多業者支援實作文件

## 📋 目錄

- [概述](#概述)
- [架構設計](#架構設計)
- [資料庫設計](#資料庫設計)
- [後端服務](#後端服務)
- [API 端點](#api-端點)
- [前端頁面](#前端頁面)
- [使用指南](#使用指南)
- [測試指南](#測試指南)
- [疑難排解](#疑難排解)

---

## 概述

### 業務模型

本系統為 **SaaS 多租戶架構**，服務對象為：

```
平台提供商（您）
    ↓ 提供服務
包租代管業者 A、B、C（互為競爭對手）
    ↓ 服務
租客（終端使用者）
```

### Phase 1 目標

**B2C 路徑**：租客 → 包租代管業者

- ✅ 租客透過 LINE/社群平台或業者 App/Web 與 AI 對話
- ✅ 系統根據業者 ID 返回客製化答案
- ✅ 使用 **LLM 智能參數注入系統**處理業者差異化參數
- ✅ 純知識庫查詢，無需外部 API 呼叫
- ✅ 無需租客身份識別

**Phase 2 功能**（未來實作）：

- ⏳ B2B 路徑：業者客服 → 平台系統
- ⏳ 租客身份識別
- ⏳ 外部 API 整合

---

## 架構設計

### 核心概念

#### 1. LLM 智能參數注入系統

**核心理念：** 不使用傳統的 `{{template_variable}}` 系統，而是讓 LLM 根據業者參數智能調整知識內容。

**運作方式：**
1. 知識庫儲存通用數值的參考內容（如「5 號」、「300 元」）
2. 系統檢索知識時，將業者參數傳遞給 LLM
3. LLM 自動識別並調整內容中的數值，使其符合業者參數

**範例：**

```
知識庫原始內容：
「您的租金繳費日為每月 5 號，請務必在期限前完成繳費。如果超過繳費日 3 天仍未繳納，將加收 300 元的逾期手續費。」

業者 A 參數：payment_day=1, grace_period=5, late_fee=200
業者 A 實際回應：
「您的租金繳費日為每月 1 號，請務必在期限前完成繳費。如果超過繳費日 5 天仍未繳納，將加收 200 元的逾期手續費。」

業者 B 參數：payment_day=5, grace_period=3, late_fee=300
業者 B 實際回應：
「您的租金繳費日為每月 5 號，請務必在期限前完成繳費。如果超過繳費日 3 天仍未繳納，將加收 300 元的逾期手續費。」
```

**優勢：**
- ✅ 無需維護模板變數，知識內容更自然
- ✅ LLM 能理解上下文，調整更精準
- ✅ 減少模板解析錯誤（如遺漏變數）
- ✅ 支援複雜的參數替換邏輯

#### 2. 三層知識範圍

| 範圍 | 說明 | 優先級 | 用途 |
|------|------|--------|------|
| `global` | 全域知識 | 最低 | 適用所有業者的通用知識 |
| `vendor` | 業者專屬 | 中等 | 特定業者獨有的知識 |
| `customized` | 客製化 | 最高 | 覆蓋全域知識的業者特殊版本 |

#### 3. 參數分類

| 分類 | 用途 | 範例參數 |
|------|------|----------|
| `payment` | 帳務相關 | payment_day, late_fee, grace_period |
| `contract` | 合約相關 | min_lease_period, deposit_months |
| `service` | 服務相關 | service_hotline, service_hours |
| `contact` | 聯絡資訊 | office_address, line_id |

---

## 資料庫設計

### 新增/擴展的表格

#### 1. `vendors` - 業者表

```sql
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,           -- 業者代碼（API 使用）
    name VARCHAR(200) NOT NULL,                 -- 業者名稱
    short_name VARCHAR(100),                    -- 簡稱
    contact_phone VARCHAR(50),                  -- 聯絡電話
    contact_email VARCHAR(100),                 -- 聯絡郵箱
    address TEXT,                               -- 公司地址
    subscription_plan VARCHAR(50),              -- 訂閱方案
    subscription_status VARCHAR(20),            -- 訂閱狀態
    is_active BOOLEAN DEFAULT true,             -- 是否啟用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. `vendor_configs` - 業者配置參數表

```sql
CREATE TABLE vendor_configs (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    category VARCHAR(50) NOT NULL,              -- payment, contract, service, contact
    param_key VARCHAR(100) NOT NULL,            -- 參數鍵
    param_value TEXT NOT NULL,                  -- 參數值
    data_type VARCHAR(20) DEFAULT 'string',     -- string, number, date, boolean, json
    display_name VARCHAR(200),                  -- 顯示名稱
    description TEXT,                           -- 參數說明
    unit VARCHAR(20),                           -- 單位（元、天、%）
    is_active BOOLEAN DEFAULT true,
    UNIQUE(vendor_id, category, param_key)
);
```

#### 3. `knowledge_base` 擴展欄位

```sql
ALTER TABLE knowledge_base
    ADD COLUMN vendor_id INTEGER REFERENCES vendors(id),
    ADD COLUMN scope VARCHAR(20) DEFAULT 'global',
    ADD COLUMN priority INTEGER DEFAULT 0;

-- 注意：is_template 和 template_vars 欄位已棄用
-- Phase 1 改用 LLM 智能參數注入，無需模板變數
```

### 範例資料

系統已預先建立兩個測試業者：

- **業者 A**：甲山林包租代管（繳費日 1 號，逾期費 200 元）
- **業者 B**：信義包租代管（繳費日 5 號，逾期費 300 元）

---

## 後端服務

### 1. LLMAnswerOptimizer（核心服務）

**位置：** `rag-orchestrator/services/llm_answer_optimizer.py`

**功能：**
- 使用 GPT-4o-mini 優化 RAG 檢索結果
- **智能參數注入**：根據業者參數動態調整知識內容
- 生成自然、精準的答案
- 支援多業者參數差異化

**核心方法：**

```python
# 1. 優化答案（含參數注入）
result = optimizer.optimize_answer(
    question="每月繳費日期是什麼時候？",
    search_results=rag_results,
    confidence_level="high",
    intent_info=intent_data,
    vendor_params={"payment_day": 1, "late_fee": 200},  # 業者參數
    vendor_name="甲山林包租代管"
)

# 2. 智能參數注入（內部使用）
adjusted_content = optimizer.inject_vendor_params(
    content="您的租金繳費日為每月 5 號...",
    vendor_params={"payment_day": 1, "late_fee": 200},
    vendor_name="甲山林包租代管"
)
# LLM 自動調整為：「您的租金繳費日為每月 1 號...」
```

**參數注入運作流程：**
```
1. RAG 檢索知識（含通用數值）
2. 提取業者參數（從 vendor_configs）
3. LLM 分析內容並識別可調整的數值
4. LLM 根據業者參數智能替換
5. 返回調整後的自然語言答案
```

### 2. VendorParameterResolver

**位置：** `rag-orchestrator/services/vendor_parameter_resolver.py`

**功能：**
- 獲取業者參數（從 vendor_configs 表）
- 格式化參數值（添加單位、格式化數字）
- 參數快取機制

**核心方法：**

```python
# 獲取業者所有參數（字典格式）
params = resolver.get_vendor_parameters(vendor_id=1)
# 結果: {"payment_day": 1, "late_fee": 200, "grace_period": 5, ...}

# 獲取格式化參數（含單位）
formatted_params = resolver.get_formatted_parameters(vendor_id=1)
# 結果: {"payment_day": "1 號", "late_fee": "200 元", ...}
```

**注意：** 此服務不再處理模板變數解析，僅負責參數獲取與格式化。

### 3. VendorKnowledgeRetriever

**位置：** `rag-orchestrator/services/vendor_knowledge_retriever.py`

**功能：**
- 根據業者 ID 和意圖檢索知識
- 自動應用優先級排序（customized > vendor > global）
- 返回知識列表（由 LLMAnswerOptimizer 進行參數注入）

**核心方法：**

```python
# 檢索知識
knowledge_list = retriever.retrieve_knowledge(
    intent_id=1,
    vendor_id=1,
    top_k=3
)

# 獲取統計
stats = retriever.get_knowledge_stats(vendor_id=1)
```

---

## API 端點

### Chat API

#### `POST /chat/v1/message`

**多業者聊天端點**（Phase 1: B2C 模式）

**請求範例：**

```json
{
  "message": "每月繳費日期是什麼時候？",
  "vendor_id": 1,
  "mode": "tenant",
  "include_sources": true
}
```

**回應範例：**

```json
{
  "answer": "您的租金繳費日為每月 1 號，請務必在期限前完成繳費。如果超過繳費日 5 天仍未繳納，將加收 200 元的逾期手續費。",
  "intent_name": "帳務查詢",
  "intent_type": "knowledge",
  "confidence": 0.95,
  "sources": [
    {
      "id": 123,
      "question_summary": "每月繳費日期",
      "answer": "您的租金繳費日為每月 5 號...",  // 原始通用內容
      "scope": "global"
    }
  ],
  "source_count": 1,
  "vendor_id": 1,
  "mode": "tenant",
  "timestamp": "2024-01-01T12:00:00Z",
  "llm_optimization": {
    "optimization_applied": true,
    "tokens_used": 456,
    "processing_time_ms": 1234,
    "vendor_params_injected": true  // LLM 已進行參數注入
  }
}
```

**注意：**
- `answer` 欄位包含 LLM 優化並注入業者參數後的最終答案
- `sources[].answer` 保留原始知識庫內容（通用數值）
- LLM 自動將「5 號」調整為業者 A 的「1 號」，「300 元」調整為「200 元」

#### `GET /chat/v1/vendors/{vendor_id}/test`

測試業者配置是否正確設定

**回應範例：**

```json
{
  "vendor": {
    "id": 1,
    "code": "VENDOR_A",
    "name": "甲山林包租代管股份有限公司",
    "is_active": true
  },
  "param_count": 12,
  "parameters": {
    "payment_day": {
      "value": "1",
      "data_type": "number",
      "unit": "號"
    },
    "late_fee": {
      "value": "200",
      "data_type": "number",
      "unit": "元"
    }
  },
  "test_template": {
    "original": "繳費日為 {{payment_day}}，逾期費 {{late_fee}}。",
    "resolved": "繳費日為 1 號，逾期費 200 元。"
  }
}
```

### Vendors API

#### `GET /api/v1/vendors`

獲取業者列表

**查詢參數：**
- `is_active`: 過濾啟用/停用狀態
- `subscription_plan`: 過濾訂閱方案

#### `POST /api/v1/vendors`

建立新業者

**請求範例：**

```json
{
  "code": "VENDOR_C",
  "name": "永慶包租代管股份有限公司",
  "short_name": "永慶",
  "contact_phone": "02-1234-5678",
  "contact_email": "service@vendorc.com",
  "subscription_plan": "premium",
  "created_by": "admin"
}
```

#### `PUT /api/v1/vendors/{vendor_id}`

更新業者資訊

#### `DELETE /api/v1/vendors/{vendor_id}`

停用業者（軟刪除）

#### `GET /api/v1/vendors/{vendor_id}/configs`

獲取業者配置參數

**查詢參數：**
- `category`: 過濾分類（payment, contract, service, contact）

**回應範例：**

```json
{
  "payment": [
    {
      "id": 1,
      "category": "payment",
      "param_key": "payment_day",
      "param_value": "1",
      "data_type": "number",
      "display_name": "繳費日期",
      "unit": "號"
    }
  ],
  "service": [...]
}
```

#### `PUT /api/v1/vendors/{vendor_id}/configs`

批次更新業者配置

**請求範例：**

```json
{
  "configs": [
    {
      "category": "payment",
      "param_key": "payment_day",
      "param_value": "1",
      "data_type": "number",
      "display_name": "繳費日期",
      "unit": "號"
    },
    {
      "category": "payment",
      "param_key": "late_fee",
      "param_value": "200",
      "data_type": "number",
      "display_name": "逾期手續費",
      "unit": "元"
    }
  ]
}
```

#### `GET /api/v1/vendors/{vendor_id}/stats`

獲取業者統計資訊

---

## 前端頁面

### 1. Chat 測試頁面 (`/chat-test`)

**功能：**
- 選擇業者
- 查看業者資訊和參數
- 即時測試 Chat API
- 查看意圖分類和知識來源
- 快速測試問題按鈕

**使用流程：**
1. 選擇業者（如「甲山林」）
2. 輸入問題或點擊快速測試問題
3. 查看 AI 回應和知識來源
4. 切換業者測試不同參數效果

### 2. 業者管理頁面 (`/vendors`)

**功能：**
- 業者列表（CRUD）
- 過濾啟用/停用狀態
- 新增/編輯業者資訊
- 查看業者統計
- 跳轉到配置頁面

**操作：**
- ➕ 新增業者：填寫代碼、名稱、聯絡資訊
- ✏️ 編輯：修改業者資訊
- ⚙️ 配置：跳轉到參數配置頁面
- 📊 統計：查看配置數量、知識數量
- 🗑️ 停用：軟刪除業者

### 3. 業者配置頁面 (`/vendors/:id/configs`)

**功能：**
- 按分類管理參數（帳務、合約、服務、聯絡）
- 視覺化編輯參數
- 即時預覽模板效果
- 自訂參數
- 批次儲存

**分類標籤：**
- 💰 帳務設定：payment_day, late_fee, grace_period
- 📝 合約設定：min_lease_period, deposit_months
- 🛎️ 服務設定：service_hotline, service_hours
- 📞 聯絡資訊：office_address, line_id

**預覽功能：**
- 點擊「👁️ 預覽效果」查看參數實際顯示效果
- 即時查看模板變數替換結果
- 確保參數設定正確

---

## 使用指南

### 基本流程

#### 1. 建立新業者

```
業者管理 → ➕ 新增業者 → 填寫資訊 → 💾 儲存
```

必填欄位：
- 代碼（唯一，建立後不可修改）
- 名稱

#### 2. 配置業者參數

```
業者管理 → ⚙️ 配置 → 選擇分類 → 編輯參數 → 💾 儲存
```

建議配置順序：
1. 帳務設定（payment_day, late_fee 等）
2. 服務設定（service_hotline 等）
3. 合約設定
4. 聯絡資訊

#### 3. 建立/修改知識庫

在「知識庫」頁面新增知識時：

**使用全域知識（推薦）：**
- vendor_id: 留空
- scope: global
- 答案中使用**通用參考數值**（如「5 號」、「300 元」）

**範例：**
```
問題：每月繳費日期是什麼時候？

答案：您的租金繳費日為每月 5 號，請務必在期限前完成繳費。
如果超過繳費日 3 天仍未繳納，將加收 300 元的逾期手續費。

scope: global
```

**重要說明：**
- ✅ 使用自然語言撰寫，無需 `{{模板變數}}`
- ✅ 使用通用數值作為參考（如「5 號」、「300 元」、「3 天」）
- ✅ LLM 會自動根據業者參數調整這些數值
- ✅ 例如：業者 A（payment_day=1）會將「5 號」自動調整為「1 號」

**業者專屬知識：**
- vendor_id: 選擇特定業者
- scope: vendor
- 內容直接使用該業者的具體數值

**覆蓋全域知識：**
- vendor_id: 選擇特定業者
- scope: customized
- priority: 設定較高值（如 10）

#### 4. 測試 Chat API

```
Chat 測試 → 選擇業者 → 輸入問題 → 查看回應
```

測試要點：
- ✅ 不同業者得到不同答案（LLM 參數注入正確）
- ✅ 意圖分類正確
- ✅ 知識來源優先級正確（customized > vendor > global）
- ✅ 數值調整準確（如業者 A 的「1 號」vs 業者 B 的「5 號」）
- ✅ 答案語氣自然，無模板痕跡

---

## 測試指南

### 資料庫遷移測試

```bash
# 1. 執行遷移腳本
cd /Users/lenny/jgb/AIChatbot
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -f /docker-entrypoint-initdb.d/06-vendors-and-configs.sql
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -f /docker-entrypoint-initdb.d/07-extend-knowledge-base.sql

# 2. 驗證表格建立
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "\d vendors"
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "\d vendor_configs"

# 3. 驗證範例資料
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "SELECT * FROM vendors;"
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "SELECT COUNT(*) FROM vendor_configs;"
```

### API 測試（使用 Postman/curl）

#### 測試 1：業者 A 詢問繳費日

```bash
curl -X POST http://localhost:8100/chat/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "每月繳費日期是什麼時候？",
    "vendor_id": 1,
    "mode": "tenant",
    "include_sources": true
  }'
```

**預期結果：**
- 回答中包含「1 號」
- 逾期費「200 元」

#### 測試 2：業者 B 詢問繳費日

```bash
curl -X POST http://localhost:8100/chat/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "每月繳費日期是什麼時候？",
    "vendor_id": 2,
    "mode": "tenant",
    "include_sources": true
  }'
```

**預期結果：**
- 回答中包含「5 號」
- 逾期費「300 元」

#### 測試 3：獲取業者列表

```bash
curl http://localhost:8100/api/v1/vendors
```

#### 測試 4：測試業者配置

```bash
curl http://localhost:8100/chat/v1/vendors/1/test
```

### 前端測試

1. **導航測試：**
   - 確認頂部導航欄顯示「業者管理」和「Chat 測試」
   - 點擊各頁面，確認路由正常

2. **業者管理測試：**
   - 新增業者
   - 編輯業者資訊
   - 查看統計
   - 跳轉到配置頁面

3. **配置頁面測試：**
   - 切換分類標籤
   - 編輯參數值
   - 點擊「預覽效果」查看模板解析
   - 儲存配置

4. **Chat 測試頁面：**
   - 選擇業者 A，詢問「繳費日期」→ 回答應包含「1 號」
   - 切換到業者 B，詢問相同問題 → 回答應包含「5 號」
   - 查看知識來源和意圖分類

### 回歸測試檢查表

- [ ] 資料庫遷移成功，無錯誤
- [ ] 兩個測試業者已建立
- [ ] 業者配置參數已載入（每個業者至少 10 個參數）
- [ ] 全域知識已建立（使用通用數值）
- [ ] API 端點回應正確
- [ ] 業者 A 和業者 B 得到不同答案
- [ ] LLM 參數注入正確（業者 A 的「1 號」vs 業者 B 的「5 號」）
- [ ] 回應包含 `llm_optimization` 欄位且 `optimization_applied: true`
- [ ] 前端頁面載入正常
- [ ] 導航功能正常
- [ ] Chat 測試頁面可正常對話

---

## 疑難排解

### 問題 1：Chat API 返回 500 錯誤

**可能原因：**
- 意圖分類器未初始化
- 資料庫連線失敗
- 業者 ID 不存在

**解決方案：**
1. 檢查 RAG Orchestrator 日誌：
   ```bash
   docker-compose logs rag-orchestrator
   ```

2. 驗證業者存在：
   ```bash
   curl http://localhost:8100/api/v1/vendors
   ```

3. 測試業者配置：
   ```bash
   curl http://localhost:8100/chat/v1/vendors/1/test
   ```

### 問題 2：LLM 參數注入未生效

**症狀：** 不同業者得到相同的答案，或數值未調整

**可能原因：**
- 業者未配置參數（vendor_configs 為空）
- LLM 優化未啟用
- vendor_params 未正確傳遞給 LLMAnswerOptimizer
- OpenAI API 錯誤

**解決方案：**
1. 檢查業者配置：
   ```bash
   curl http://localhost:8100/api/v1/vendors/1/configs
   ```

2. 檢查 LLM 優化日誌：
   ```bash
   docker-compose logs rag-orchestrator | grep "LLM"
   ```

3. 驗證測試端點：
   ```bash
   curl http://localhost:8100/chat/v1/vendors/1/test
   ```

4. 檢查回應中的 `llm_optimization` 欄位，確認 `optimization_applied: true`

### 問題 3：知識優先級錯誤

**症狀：** 應該使用 customized 知識但使用了 global 知識

**可能原因：**
- scope 欄位設定錯誤
- priority 值設定不當
- vendor_id 未正確設定

**解決方案：**
1. 檢查知識庫 scope 和 priority：
   ```sql
   SELECT id, question_summary, vendor_id, scope, priority
   FROM knowledge_base
   WHERE intent_id = [意圖ID]
   ORDER BY
     CASE
       WHEN scope = 'customized' THEN 1000
       WHEN scope = 'vendor' THEN 500
       ELSE 100
     END DESC, priority DESC;
   ```

2. 確認 customized 知識的 priority >= 10

### 問題 4：前端頁面載入失敗

**解決方案：**
1. 檢查 Vue Router 是否正確引入元件
2. 檢查瀏覽器 Console 錯誤訊息
3. 重新建置前端：
   ```bash
   cd knowledge-admin/frontend
   npm run build
   ```

---

## 下一步：Phase 2 規劃

Phase 2 將實作：

1. **B2B 模式支援**
   - 客服人員界面
   - 租客身份識別（從自然語言提取）
   - 外部 API 整合

2. **資料表：**
   - `tenants` - 租客資料（用於身份識別）
   - `vendor_apis` - 外部 API 配置
   - `vendor_api_endpoints` - API 端點對應
   - `vendor_api_logs` - API 呼叫日誌

3. **服務：**
   - `TenantIdentifier` - 租客身份識別
   - `ExternalAPIClient` - 外部 API 客戶端
   - `CustomerServiceAssistant` - 客服助理整合服務

---

## 文件版本

- **版本：** 2.0
- **建立日期：** 2025-01-XX
- **最後更新：** 2025-10-10
- **作者：** Claude Code
- **適用系統版本：** Phase 1（LLM 智能參數注入）
- **變更紀錄：**
  - v2.0 (2025-10-10): 更新為 LLM 智能參數注入系統，移除模板變數相關內容
  - v1.0 (2025-01-XX): 初始版本（使用模板變數系統）
