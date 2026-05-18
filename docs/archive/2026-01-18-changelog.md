# 文件更新規格 - Knowledge Action System (方式 2：自動格式化)

**日期**: 2026-01-18
**版本**: v1.1.0
**變更類型**: 功能增強 - 採用 API 原始數據自動格式化方式

---

## 📋 變更摘要

本次更新將 API 回應處理方式從「方式 1（API 自帶格式化訊息）」調整為「方式 2（系統自動格式化原始數據）」，提升系統的統一性和維護性。

### 核心變更
1. ✅ API 層只需返回原始數據，不需要自己格式化
2. ✅ 增強 `api_call_handler.py` 的自動格式化能力
3. ✅ 支援中文欄位映射
4. ✅ 支援特殊格式化（金額千分位等）
5. ✅ 分離成功和錯誤數據的格式化邏輯

---

## 📂 文件變更清單

### 一、修改的文件（Modified）

#### 1. `rag-orchestrator/routers/chat.py`
**變更行數**: +191 / -30
**變更類型**: 功能增強

**主要變更**：
- 在 `_build_knowledge_response()` 中新增 `action_type` 路由邏輯（第 905-972 行）
- 新增 `_handle_api_call()` 函數處理 API 調用場景（第 1151-1253 行）
- 支援 4 種 action_type：
  - `direct_answer`: 純知識問答
  - `form_fill`: 表單 + 知識答案
  - `api_call`: 直接調用 API
  - `form_then_api`: 表單完成後調用 API

**影響範圍**:
- 所有知識庫查詢流程
- API 調用場景

---

#### 2. `rag-orchestrator/services/form_manager.py`
**變更行數**: +113 / -10
**變更類型**: 功能增強

**主要變更**：
- 在 `_complete_form()` 中新增表單完成後 API 調用支援（第 717-750 行）
- 新增 `_execute_form_api()` 函數執行表單完成後的 API（第 740-786 行）
- 新增 `_format_completion_message()` 格式化完成訊息（第 788-828 行）
- 支援 3 種 `on_complete_action`：
  - `show_knowledge`: 只顯示知識答案
  - `call_api`: 只調用 API
  - `both`: 兩者都執行

**影響範圍**:
- 所有表單完成流程
- 表單 + API 組合場景

---

#### 3. `rag-orchestrator/services/vendor_knowledge_retriever.py`
**變更行數**: +4
**變更類型**: 資料庫查詢擴充

**主要變更**：
- SQL 查詢中新增 `kb.action_type` 欄位（第 94 行）
- SQL 查詢中新增 `kb.api_config` 欄位（第 95 行）

**影響範圍**:
- 所有知識庫檢索操作

---

#### 4. `rag-orchestrator/services/api_call_handler.py` ⭐ **本次重點修改**
**變更行數**: +85
**變更類型**: 功能增強（方式 2 實作）

**主要變更**：
- 修改 `_format_api_data()` 支援自動格式化（第 258-285 行）
- **新增** `_format_success_data()` 格式化成功數據（第 287-320 行）
  - 中文欄位映射（第 292-302 行）
  - 特殊格式化邏輯（金額千分位等）（第 313-316 行）
- **新增** `_format_error_data()` 格式化錯誤數據（第 322-338 行）
  - 錯誤類型提示
  - 建議訊息
  - 錯誤代碼

**影響範圍**:
- 所有 API 調用的回應格式化
- 錯誤訊息顯示

**欄位映射表**（第 292-302 行）：
```python
field_mapping = {
    'invoice_id': '帳單編號',
    'month': '帳單月份',
    'amount': '金額',
    'status': '狀態',
    'sent_date': '發送日期',
    'due_date': '到期日',
    'email': '發送郵箱',
    'ticket_id': '工單編號',
    'order_id': '訂單編號',
}
```

---

#### 5. `rag-orchestrator/services/billing_api.py` ⭐ **本次重點修改**
**變更行數**: 修改 50 行
**變更類型**: API 回應格式調整（方式 1 → 方式 2）

**主要變更**：
- 修改 `_mock_get_invoice_status()` 只返回原始數據（第 163-210 行）
- **移除** 所有 `message` 欄位的手動格式化
- **保留** 原始數據欄位：
  - 成功場景：`invoice_id`, `month`, `amount`, `status`, `sent_date`, `due_date`, `email`
  - 錯誤場景：`error_type`, `suggestion`, `next_send_date`

**修改前**（方式 1）：
```python
return {
    'success': True,
    'invoice_id': 'INV-123',
    'amount': 15000,
    'message': '✅ **帳單查詢成功**\n\n📅 月份: ...'  # 自己格式化
}
```

**修改後**（方式 2）：
```python
return {
    'success': True,
    'invoice_id': 'INV-test_user-2026-01',
    'month': '2026-01',
    'amount': 15000,
    'status': 'sent',
    'sent_date': '2026-01-01',
    'due_date': '2026-01-15',
    'email': 'test_user@example.com'
    # 沒有 message，由系統自動格式化
}
```

**影響範圍**:
- 所有帳單 API 的模擬實作
- 未來真實 API 實作的參考範本

---

### 二、新增的文件（New Files）

#### 核心服務模組

##### 1. `rag-orchestrator/services/api_call_handler.py`
**行數**: 322 行
**功能**: 統一 API 調用處理器

**核心功能**：
- ✅ 解析 `api_config` 配置
- ✅ 動態參數替換（`{session.xxx}`, `{form.xxx}`, `{user_input.xxx}`）
- ✅ 調用具體的 API 服務
- ✅ 錯誤處理和降級策略
- ✅ **自動格式化 API 響應**（方式 2 核心）

**API 註冊表**（第 33-38 行）：
```python
self.api_registry = {
    'billing_inquiry': self.billing_api.get_invoice_status,
    'verify_tenant_identity': self.billing_api.verify_tenant_identity,
    'resend_invoice': self.billing_api.resend_invoice,
    'maintenance_request': self.billing_api.submit_maintenance_request,
}
```

---

##### 2. `rag-orchestrator/services/billing_api.py`
**行數**: 328 行
**功能**: 帳單 API 服務實作

**核心 API**：
- `get_invoice_status()`: 查詢帳單狀態
- `verify_tenant_identity()`: 驗證租客身份
- `resend_invoice()`: 重新發送帳單
- `submit_maintenance_request()`: 提交報修申請

**模擬模式**：
- 環境變數：`USE_MOCK_BILLING_API=true`
- 測試用戶：
  - `test_user`: 正常用戶（身分證後4碼: 1234）
  - `test_no_data`: 無帳單資料
  - `test_not_sent`: 帳單尚未發送

---

#### 資料庫遷移腳本

##### 3. `database/migrations/add_action_type_and_api_config.sql`
**行數**: 164 行
**功能**: 新增知識庫動作系統欄位

**變更內容**：
1. `knowledge_base` 表新增：
   - `action_type` (VARCHAR): 動作類型
   - `api_config` (JSONB): API 配置
   - 約束：`CHECK (action_type IN ('direct_answer', 'form_fill', 'api_call', 'form_then_api'))`

2. `form_schemas` 表新增：
   - `on_complete_action` (VARCHAR): 完成後動作
   - `api_config` (JSONB): API 配置
   - 約束：`CHECK (on_complete_action IN ('show_knowledge', 'call_api', 'both'))`

3. 數據遷移：
   - 將現有的 `form_id IS NOT NULL` 知識設為 `action_type = 'form_fill'`

4. 驗證腳本：
   - 自動檢查欄位是否成功添加
   - 顯示統計資訊

---

##### 4. `database/migrations/configure_billing_inquiry_examples.sql`
**行數**: 381 行
**功能**: 插入帳單查詢系統範例配置

**涵蓋場景**：
- **場景 A**: 純知識問答（租金繳納方式）- `action_type = 'direct_answer'`
- **場景 B**: 表單填寫（租屋詢問）- `action_type = 'form_fill'`
- **場景 C**: API 查詢（已登入）- `action_type = 'api_call'`
- **場景 D**: 表單 + API（訪客查帳單）- `action_type = 'form_then_api'`
- **場景 E**: 表單 + API（報修申請）- `action_type = 'form_then_api'`

**測試建議**：
- 使用模擬 API (`USE_MOCK_BILLING_API=true`)
- 測試用戶：`test_user` (身分證後4碼: 1234)
- 特殊測試用戶：`test_no_data`, `test_not_sent`

---

#### 設計文檔

##### 5. `docs/design/API_CONFIGURATION_GUIDE.md`
**行數**: ~800 行
**功能**: API 配置完全指南

**內容**：
- 核心概念說明
- 完整配置結構
- 參數映射語法
- 回應格式化選項
- 10+ 實際範例
- 如何添加新 API
- 常見問題

**注意**: 需要更新以反映方式 2 的變更 ⚠️

---

##### 6-12. 其他設計文檔
- `KNOWLEDGE_ACTION_SYSTEM_DESIGN.md`: 系統設計
- `KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md`: 實作指南
- `KNOWLEDGE_ACTION_QUICK_REFERENCE.md`: 快速參考
- `KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md`: 實作範例
- `KNOWLEDGE_ACTION_IMPLEMENTATION_SUMMARY.md`: 實作總結
- `DEPLOYMENT_RESULTS.md`: 部署結果
- `FINAL_IMPLEMENTATION_REPORT.md`: 最終實作報告
- `SYSTEM_VERIFICATION_REPORT.md`: 系統驗證報告

---

### 三、未變更的文件（Unchanged）

以下文件無需修改，但會受到新功能影響：

1. `rag-orchestrator/main.py` - 服務入口
2. `rag-orchestrator/services/db_utils.py` - 資料庫工具
3. `rag-orchestrator/services/cache_service.py` - 緩存服務
4. `.env` - 環境配置（已包含新增的環境變數）

---

## 🔄 API 變更規格

### API 回應格式變更

#### 修改前（方式 1）：API 自帶格式化訊息

```python
# billing_api.py
async def get_invoice_status(user_id, month):
    return {
        'success': True,
        'invoice_id': 'INV-123',
        'amount': 15000,
        'message': '✅ **帳單查詢成功**\n\n📅 月份: 2026-01\n💰 金額: NT$ 15,000\n...'
    }
```

**優點**：API 完全控制訊息格式
**缺點**：每個 API 都要自己格式化，不統一

---

#### 修改後（方式 2）：系統自動格式化 ⭐

```python
# billing_api.py
async def get_invoice_status(user_id, month):
    return {
        'success': True,
        'invoice_id': 'INV-test_user-2026-01',
        'month': '2026-01',
        'amount': 15000,
        'status': 'sent',
        'sent_date': '2026-01-01',
        'due_date': '2026-01-15',
        'email': 'test_user@example.com'
        # 沒有 message，由 api_call_handler.py 自動格式化
    }
```

**優點**：
- ✅ API 只需返回原始數據，簡單清晰
- ✅ 格式化邏輯統一在 `api_call_handler.py`
- ✅ 易於維護和擴展
- ✅ 支援中文欄位映射
- ✅ 支援特殊格式化（金額、日期等）

**缺點**：
- ⚠️ 需要在 `field_mapping` 中預先定義欄位映射
- ⚠️ 複雜的個性化訊息需要修改格式化邏輯

---

### 自動格式化輸出範例

#### 成功場景

**API 原始返回**：
```json
{
  "success": true,
  "invoice_id": "INV-test_user-2026-01",
  "month": "2026-01",
  "amount": 15000,
  "status": "sent",
  "sent_date": "2026-01-01",
  "due_date": "2026-01-15",
  "email": "test_user@example.com"
}
```

**系統自動格式化為**：
```
✅ **查詢成功**

📌 **帳單編號**: INV-test_user-2026-01
📌 **帳單月份**: 2026-01
📌 **金額**: NT$ 15,000
📌 **狀態**: sent
📌 **發送日期**: 2026-01-01
📌 **到期日**: 2026-01-15
📌 **發送郵箱**: test_user@example.com
```

---

#### 錯誤場景

**API 原始返回**：
```json
{
  "success": false,
  "error": "no_invoice_found",
  "error_type": "查無帳單資料",
  "suggestion": "您查詢的期間目前尚無帳單記錄"
}
```

**系統自動格式化為**：
```
⚠️ **查無帳單資料**

💡 您查詢的期間目前尚無帳單記錄

錯誤代碼：no_invoice_found
```

---

## 💾 資料庫變更規格

### Schema 變更

#### 1. `knowledge_base` 表

```sql
-- 新增欄位
ALTER TABLE knowledge_base
ADD COLUMN action_type VARCHAR(50) DEFAULT 'direct_answer',
ADD COLUMN api_config JSONB;

-- 新增約束
ALTER TABLE knowledge_base
ADD CONSTRAINT check_action_type
CHECK (action_type IN ('direct_answer', 'form_fill', 'api_call', 'form_then_api'));

-- 新增索引
CREATE INDEX idx_kb_action_type ON knowledge_base(action_type);
```

**欄位說明**：
- `action_type`: 動作類型，決定系統行為
- `api_config`: API 配置（JSONB），包含 endpoint, params, combine_with_knowledge 等

---

#### 2. `form_schemas` 表

```sql
-- 新增欄位
ALTER TABLE form_schemas
ADD COLUMN on_complete_action VARCHAR(50) DEFAULT 'show_knowledge',
ADD COLUMN api_config JSONB;

-- 新增約束
ALTER TABLE form_schemas
ADD CONSTRAINT check_on_complete_action
CHECK (on_complete_action IN ('show_knowledge', 'call_api', 'both'));

-- 新增索引
CREATE INDEX idx_form_schemas_on_complete_action ON form_schemas(on_complete_action);
```

**欄位說明**：
- `on_complete_action`: 表單完成後動作
- `api_config`: 表單完成後的 API 調用配置

---

### 數據遷移

```sql
-- 將現有的表單觸發知識更新為 form_fill
UPDATE knowledge_base
SET action_type = 'form_fill'
WHERE form_id IS NOT NULL
  AND action_type = 'direct_answer';
```

---

## ⚙️ 配置變更規格

### 環境變數（.env）

#### 新增配置

```bash
# ==================== 帳單 API 配置 ====================
# 帳單 API 基礎 URL
BILLING_API_BASE_URL=http://localhost:8000

# 帳單 API 金鑰
BILLING_API_KEY=

# 帳單 API 超時時間（秒）
BILLING_API_TIMEOUT=10.0

# 使用模擬 API（開發/測試環境設為 true，生產環境設為 false）
USE_MOCK_BILLING_API=true
```

#### 已存在配置（無需修改）

```bash
# OpenAI API Key
OPENAI_API_KEY=...

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 📦 依賴變更

### Python 依賴

#### 新增依賴

```txt
httpx>=0.24.0  # 用於 API 調用
```

#### 驗證安裝

```bash
cd /Users/lenny/jgb/AIChatbot/rag-orchestrator
pip install httpx
python -c "import httpx; print(f'httpx version: {httpx.__version__}')"
```

---

## 🧪 測試規格

### 單元測試需求

#### 1. `api_call_handler.py` 測試

**測試項目**：
- ✅ `_format_success_data()` 正確格式化成功數據
- ✅ `_format_error_data()` 正確格式化錯誤數據
- ✅ `_format_api_data()` 正確路由到對應格式化函數
- ✅ 欄位映射正確轉換為中文
- ✅ 金額正確添加千分位
- ✅ 跳過內部標誌（success, verified, error）

**測試用例**：
```python
# 測試成功數據格式化
def test_format_success_data():
    api_result = {
        'success': True,
        'invoice_id': 'INV-123',
        'amount': 15000,
        'month': '2026-01'
    }
    formatted = handler._format_success_data(api_result)
    assert '✅ **查詢成功**' in formatted
    assert '**帳單編號**: INV-123' in formatted
    assert '**金額**: NT$ 15,000' in formatted  # 千分位

# 測試錯誤數據格式化
def test_format_error_data():
    api_result = {
        'success': False,
        'error': 'no_data',
        'error_type': '查無資料',
        'suggestion': '請檢查輸入'
    }
    formatted = handler._format_error_data(api_result)
    assert '⚠️ **查無資料**' in formatted
    assert '💡 請檢查輸入' in formatted
```

---

#### 2. `billing_api.py` 測試

**測試項目**：
- ✅ `_mock_get_invoice_status()` 返回正確的原始數據格式
- ✅ 不包含 `message` 欄位
- ✅ 包含所有必要欄位（invoice_id, month, amount 等）
- ✅ 錯誤場景返回正確的錯誤數據

**測試用例**：
```python
def test_mock_invoice_status_format():
    result = billing_api._mock_get_invoice_status('test_user')

    # 驗證原始數據格式
    assert 'message' not in result  # 不應該有 message
    assert 'invoice_id' in result
    assert 'amount' in result
    assert result['success'] == True

def test_mock_invoice_error_format():
    result = billing_api._mock_get_invoice_status('test_no_data')

    assert result['success'] == False
    assert 'error_type' in result
    assert 'suggestion' in result
```

---

### 集成測試需求

#### 場景測試清單

| 場景 | action_type | 測試內容 | 預期結果 |
|------|------------|---------|---------|
| A | `direct_answer` | 純知識問答 | 返回知識答案 |
| B | `form_fill` | 表單填寫 | 觸發表單收集資料 |
| C | `api_call` | 已登入用戶查帳單 | 調用 API + 知識答案（自動格式化） |
| D | `form_then_api` | 訪客查帳單 | 表單 → API（自動格式化） |
| E | `form_then_api` | 報修申請 | 表單 → API（只返回 API 結果） |

#### 測試腳本範例

```bash
# 場景 C: API 查詢（已登入）
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的帳單",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_session_001"
  }'

# 預期輸出包含：
# - ✅ **查詢成功**
# - 📌 **帳單編號**: ...
# - 📌 **金額**: NT$ 15,000
# - ---
# - 📌 溫馨提醒
```

---

## 🚀 部署檢查清單

### 部署前準備

- [ ] 確認 Docker 服務運行
- [ ] 確認資料庫連接正常
- [ ] 確認 Redis 服務運行
- [ ] 確認環境變數已配置

### 部署步驟

#### 1. 執行資料庫遷移

```bash
docker exec -it aichatbot-postgres psql \
  -U aichatbot \
  -d aichatbot_admin \
  -f /path/to/database/migrations/add_action_type_and_api_config.sql
```

**驗證**：
```bash
docker exec -it aichatbot-postgres psql \
  -U aichatbot \
  -d aichatbot_admin \
  -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'knowledge_base' AND column_name IN ('action_type', 'api_config');"
```

---

#### 2. 執行範例配置腳本

```bash
docker exec -it aichatbot-postgres psql \
  -U aichatbot \
  -d aichatbot_admin \
  -f /path/to/database/migrations/configure_billing_inquiry_examples.sql
```

**驗證**：
```bash
docker exec -it aichatbot-postgres psql \
  -U aichatbot \
  -d aichatbot_admin \
  -c "SELECT action_type, COUNT(*) FROM knowledge_base WHERE is_active = true GROUP BY action_type;"
```

---

#### 3. 重啟服務

```bash
docker-compose restart rag-orchestrator

# 或者單獨重啟
docker restart aichatbot-rag-orchestrator
```

**驗證**：
```bash
# 檢查服務健康狀態
curl http://localhost:8100/health

# 檢查日誌
docker-compose logs -f rag-orchestrator | grep -E "🔧|🎯|📝|🔌|📞"
```

---

#### 4. 執行測試

```bash
# 測試場景 A: 純知識問答
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "租金怎麼繳", "vendor_id": 1, "user_role": "customer"}'

# 測試場景 C: API 查詢
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "我的帳單", "vendor_id": 1, "user_role": "customer", "user_id": "test_user", "session_id": "test_001"}'
```

---

### 部署後驗證

- [ ] 所有場景測試通過
- [ ] 日誌無錯誤
- [ ] API 回應格式正確（含中文標籤、千分位等）
- [ ] 錯誤處理正常（降級訊息、fallback）
- [ ] 對話歷史正常保存

---

## 📊 影響評估

### 向後兼容性

#### ✅ 完全兼容
- 現有的 `direct_answer` 知識無需修改
- 現有的 `form_fill` 表單功能無影響
- 現有的資料庫記錄自動遷移

#### ⚠️ 需要注意
- 如果已有自訂的 API 服務，需要調整返回格式為原始數據
- 如果已有自訂的格式化邏輯，需要整合到 `api_call_handler.py`

---

### 性能影響

| 項目 | 影響 | 說明 |
|------|------|------|
| API 調用延遲 | 無影響 | 格式化邏輯非常輕量 |
| 記憶體使用 | 微增 | 欄位映射字典常駐記憶體（< 1KB） |
| 資料庫查詢 | 無影響 | 只是多讀取 2 個欄位 |
| 整體效能 | ✅ 無明顯影響 | |

---

### 維護成本

#### 降低
- ✅ API 開發更簡單（不需要自己格式化）
- ✅ 格式化邏輯統一管理
- ✅ 中文標籤統一維護

#### 增加
- ⚠️ 需要維護 `field_mapping` 欄位映射表
- ⚠️ 新增欄位需要更新映射

---

## 🔮 未來擴展建議

### 1. 支援自訂格式化規則

```python
# 允許在 api_config 中定義格式化規則
{
  "endpoint": "billing_inquiry",
  "formatting_rules": {
    "amount": "currency",      # 金額格式
    "sent_date": "date_long",  # 日期長格式
    "status": "badge"          # 徽章樣式
  }
}
```

---

### 2. 支援多語言

```python
field_mapping = {
    'zh-TW': {'invoice_id': '帳單編號'},
    'en-US': {'invoice_id': 'Invoice ID'},
    'ja-JP': {'invoice_id': '請求書番号'},
}
```

---

### 3. 支援模板引擎

```python
# 使用 Jinja2 等模板引擎
response_template = """
✅ {{ title }}

{% for field in fields %}
📌 **{{ field.label }}**: {{ field.value }}
{% endfor %}
"""
```

---

## 📚 相關文檔

- [API 配置完全指南](../design/API_CONFIGURATION_GUIDE.md) ⚠️ 需更新
- [系統設計文檔](../design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [實作指南](../design/KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md)
- [快速參考](../design/KNOWLEDGE_ACTION_QUICK_REFERENCE.md)

---

## 🐛 已知問題

目前無已知問題。

---

## ✅ 變更確認

- [x] 所有代碼修改已完成
- [x] 文檔已創建
- [ ] 資料庫遷移腳本已測試
- [ ] 單元測試已編寫
- [ ] 集成測試已執行
- [ ] 性能測試已通過
- [ ] 部署指南已編寫

---

**最後更新**: 2026-01-18
**更新者**: Claude Code
**版本**: v1.1.0
