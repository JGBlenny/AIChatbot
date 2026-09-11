# 知識庫 API 配置完全指南
> 📦 **2026-09-11 歸檔（舊鏈退役）：原位置 `docs/design/API_CONFIGURATION_GUIDE.md`**——原因：所述動態 API 執行引擎（services/api_call_handler.py）已隨舊 REST 對話鏈於 2026-09-11 退役，見 .claude/DECISIONS.md DSP-046；API 端點管理後台（routers/api_endpoints.py）本身仍活著，不受影響。

> 如何設定知識觸發 API 調用以及控制回應格式

**日期**: 2026-01-18
**適用版本**: Knowledge Action System v1.0

---

## 📖 目錄

1. [核心概念](#核心概念)
2. [配置方式](#配置方式)
3. [API 配置結構](#api-配置結構)
4. [參數映射語法](#參數映射語法)
5. [回應格式化](#回應格式化)
6. [完整範例](#完整範例)
7. [常見場景](#常見場景)

---

## 核心概念

### action_type（動作類型）

知識庫的每一條知識都有一個 `action_type`，決定系統的行為：

| action_type | 說明 | 使用場景 |
|------------|------|---------|
| `direct_answer` | 純知識問答 | 一般問題回答（預設） |
| `form_fill` | 表單 + 知識答案 | 需要收集用戶資料 |
| `api_call` | API 調用 + 知識答案 | 需要即時查詢外部數據 |
| `form_then_api` | 表單 → API → 知識答案 | 先收集資料，再調用 API |

### api_config（API 配置）

當 `action_type` 為 `api_call` 或 `form_then_api` 時，需要配置 `api_config` 來指定：
- 調用哪個 API endpoint
- 需要哪些參數
- 參數從哪裡獲取（session、表單、用戶輸入等）
- 如何格式化回應
- 失敗時的降級策略

---

## 配置方式

### 方式 1: 通過資料庫直接配置

```sql
-- 插入一條 API 調用知識
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    api_config,
    keywords,
    scope,
    is_active
) VALUES (
    '帳單查詢（已登入用戶）',
    '如未收到帳單郵件，請檢查垃圾郵件夾。',  -- 知識答案
    'api_call',
    '{
        "endpoint": "billing_inquiry",
        "params": {
            "user_id": "{session.user_id}"
        },
        "combine_with_knowledge": true,
        "fallback_message": "⚠️ 目前無法查詢帳單，請稍後再試。"
    }'::jsonb,
    ARRAY['帳單', '查詢'],
    'global',
    true
);
```

### 方式 2: 通過管理後台配置（推薦）

未來將提供視覺化介面，可以：
1. 選擇 action_type
2. 選擇 API endpoint（從下拉選單）
3. 配置參數映射（拖拽式）
4. 預覽回應格式
5. 測試 API 調用

---

## API 配置結構

### 完整的 api_config JSON 結構

```json
{
  "endpoint": "billing_inquiry",              // 必填：API 端點名稱

  // 參數配置（兩種方式擇一）
  "params": {                                 // 方式1：固定參數
    "user_id": "{session.user_id}",          // 從 session 獲取
    "month": "{user_input.month}"            // 從用戶輸入獲取
  },

  "params_from_form": {                       // 方式2：從表單映射
    "user_id": "tenant_id",                  // API 參數名: 表單欄位名
    "month": "inquiry_month"
  },

  // 身份驗證（可選）
  "verify_identity_first": true,             // 是否先驗證身份
  "verification_params": {                   // 驗證參數映射
    "tenant_id": "tenant_id",
    "id_last_4": "id_last_4"
  },

  // 回應配置
  "combine_with_knowledge": true,            // 是否合併知識答案
  "response_template": "查詢結果：{api_response}\n\n{knowledge_answer}",

  // 錯誤處理
  "fallback_message": "⚠️ 查詢失敗，請稍後再試。\n\n{knowledge_answer}"
}
```

### 欄位說明

#### 1. endpoint（必填）

API 端點名稱，必須在 `api_call_handler.py` 的 `api_registry` 中註冊。

**已支援的端點**：
- `billing_inquiry`: 帳單查詢
- `verify_tenant_identity`: 租客身份驗證
- `resend_invoice`: 重新發送帳單
- `maintenance_request`: 報修申請

#### 2. params 與 params_from_form

**params**: 用於固定參數或簡單映射
```json
{
  "params": {
    "user_id": "{session.user_id}",     // 從會話獲取
    "status": "active"                  // 固定值
  }
}
```

**params_from_form**: 用於表單場景（`form_then_api`）
```json
{
  "params_from_form": {
    "api_user_id": "form_tenant_id",    // API參數名: 表單欄位名
    "api_month": "form_month"
  }
}
```

#### 3. verify_identity_first（可選）

是否在調用主 API 前先驗證身份。

```json
{
  "verify_identity_first": true,
  "verification_params": {
    "tenant_id": "tenant_id",          // 租客編號（從表單）
    "id_last_4": "id_last_4"           // 身分證後4碼（從表單）
  }
}
```

驗證失敗時會中止 API 調用，返回驗證失敗訊息。

#### 4. combine_with_knowledge（可選，預設 true）

是否將 API 結果與知識答案合併。

- `true`: 回應格式為「API結果 + 知識答案」
- `false`: 只返回 API 結果

#### 5. response_template（可選）

自訂回應格式模板。

**可用變數**：
- `{api_response}`: API 返回的格式化結果
- `{knowledge_answer}`: 知識庫答案

**範例**：
```json
{
  "response_template": "✅ 查詢成功\n\n{api_response}\n\n---\n\n💡 溫馨提示\n{knowledge_answer}"
}
```

#### 6. fallback_message（可選）

API 調用失敗時的降級訊息。

```json
{
  "fallback_message": "⚠️ 系統維護中，請稍後再試。\n\n{knowledge_answer}"
}
```

---

## 參數映射語法

### 支援的參數來源

#### 1. 從 session 獲取

```json
{
  "params": {
    "user_id": "{session.user_id}",        // 用戶 ID
    "vendor_id": "{session.vendor_id}",    // 業者 ID
    "session_id": "{session.session_id}"   // 會話 ID
  }
}
```

#### 2. 從表單獲取

```json
{
  "params_from_form": {
    "tenant_id": "tenant_id",              // 表單欄位：tenant_id
    "contact_phone": "phone"               // 表單欄位：phone
  }
}
```

#### 3. 從用戶輸入獲取（未來支援）

```json
{
  "params": {
    "query": "{user_input.query}"
  }
}
```

#### 4. 固定值

```json
{
  "params": {
    "api_version": "v1",
    "source": "chatbot"
  }
}
```

#### 5. 混合使用

```json
{
  "params": {
    "user_id": "{session.user_id}",       // 來自 session
    "status": "pending",                  // 固定值
    "priority": "high"                    // 固定值
  },
  "params_from_form": {
    "location": "repair_location",        // 來自表單
    "description": "issue_desc"           // 來自表單
  }
}
```

---

## 回應格式化

### 格式 1: API 結果 + 知識答案（預設）

```json
{
  "combine_with_knowledge": true
}
```

**輸出範例**：
```
✅ 帳單查詢成功

📅 帳單月份: 2026-01
💰 金額: NT$ 15,000
📧 發送日期: 2026-01-01
⏰ 到期日: 2026-01-15

---

📌 溫馨提醒
如果您未收到帳單郵件，請檢查垃圾郵件夾。
```

### 格式 2: 只返回 API 結果

```json
{
  "combine_with_knowledge": false
}
```

**輸出範例**：
```
✅ 報修申請已送出

報修單號：MNT-123456

我們會盡快安排維修人員處理，請保持電話暢通。
```

### 格式 3: 自訂模板

```json
{
  "combine_with_knowledge": true,
  "response_template": "🔍 查詢結果\n\n{api_response}\n\n━━━━━━━━━━━━━━━━\n\n💡 小提示\n{knowledge_answer}"
}
```

**輸出範例**：
```
🔍 查詢結果

帳單月份: 2026-01
金額: NT$ 15,000

━━━━━━━━━━━━━━━━

💡 小提示
如果您未收到帳單郵件，請檢查垃圾郵件夾。
```

---

## 完整範例

### 範例 1: 已登入用戶查詢帳單

**需求**：
- 用戶問：「我的帳單」
- 系統直接調用 API 查詢（使用 user_id）
- 返回：API 結果 + 溫馨提示

**配置**：

```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    api_config,
    keywords,
    scope,
    is_active
) VALUES (
    '帳單查詢（已登入用戶）',
    E'📌 **溫馨提醒**\n\n如果您未收到帳單郵件，請檢查：\n1. 垃圾郵件夾\n2. 郵箱地址是否正確',
    'api_call',
    '{
        "endpoint": "billing_inquiry",
        "params": {
            "user_id": "{session.user_id}"
        },
        "combine_with_knowledge": true,
        "fallback_message": "⚠️ 目前無法查詢帳單，請稍後再試。\n\n{knowledge_answer}"
    }'::jsonb,
    ARRAY['帳單', '查詢', '繳費通知'],
    'global',
    true
);
```

### 範例 2: 訪客查詢帳單（需驗證身份）

**需求**：
- 訪客問：「查詢帳單」
- 先填表單收集：租客編號、身分證後4碼
- 驗證身份後調用 API
- 返回：API 結果 + 溫馨提示

**步驟 1：創建表單**

```sql
INSERT INTO form_schemas (
    form_id,
    form_name,
    fields,
    on_complete_action,
    api_config,
    is_active
) VALUES (
    'billing_inquiry_guest',
    '帳單查詢表（訪客）',
    '[
        {
            "field_name": "tenant_id",
            "field_label": "租客編號",
            "field_type": "text",
            "prompt": "請提供您的租客編號（格式：T12345）",
            "required": true
        },
        {
            "field_name": "id_last_4",
            "field_label": "身分證後4碼",
            "field_type": "text",
            "prompt": "請提供您身分證後 4 碼（用於身份驗證）",
            "required": true,
            "max_length": 4
        }
    ]'::jsonb,
    'call_api',
    '{
        "endpoint": "billing_inquiry",
        "verify_identity_first": true,
        "verification_params": {
            "tenant_id": "tenant_id",
            "id_last_4": "id_last_4"
        },
        "params_from_form": {
            "user_id": "tenant_id"
        },
        "combine_with_knowledge": true,
        "fallback_message": "⚠️ 目前無法查詢帳單，請稍後再試或聯繫客服。"
    }'::jsonb,
    true
);
```

**步驟 2：創建知識**

```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    keywords,
    scope,
    is_active
) VALUES (
    '帳單查詢（訪客）',
    E'📌 **溫馨提醒**\n\n如果您未收到帳單郵件，請檢查垃圾郵件夾。',
    'form_then_api',
    'billing_inquiry_guest',
    ARRAY['帳單', '查詢', '訪客'],
    'global',
    true
);
```

### 範例 3: 報修申請（只返回 API 結果）

**需求**：
- 用戶問：「我要報修」
- 填寫報修表單
- 調用 API 提交報修
- 只返回報修單號（不含知識答案）

**步驟 1：創建表單**

```sql
INSERT INTO form_schemas (
    form_id,
    form_name,
    fields,
    on_complete_action,
    api_config,
    is_active
) VALUES (
    'maintenance_request',
    '報修申請表',
    '[
        {
            "field_name": "location",
            "field_label": "報修地點",
            "field_type": "text",
            "prompt": "請提供報修地點（例如：客廳、廚房、浴室）",
            "required": true
        },
        {
            "field_name": "issue_description",
            "field_label": "問題描述",
            "field_type": "text",
            "prompt": "請描述需要維修的問題",
            "required": true
        },
        {
            "field_name": "urgency",
            "field_label": "緊急程度",
            "field_type": "text",
            "prompt": "請選擇緊急程度：1-一般、2-緊急、3-非常緊急",
            "required": true
        }
    ]'::jsonb,
    'call_api',
    '{
        "endpoint": "maintenance_request",
        "params_from_form": {
            "user_id": "{session.user_id}",
            "location": "location",
            "description": "issue_description",
            "urgency": "urgency"
        },
        "combine_with_knowledge": false,
        "response_template": "✅ **報修申請已送出**\n\n報修單號：{api_response}\n\n我們會盡快安排維修人員處理，請保持電話暢通。"
    }'::jsonb,
    true
);
```

**步驟 2：創建知識**

```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    form_id,
    keywords,
    scope,
    is_active
) VALUES (
    '報修申請',
    '',  -- 不需要知識答案
    'form_then_api',
    'maintenance_request',
    ARRAY['報修', '維修', '故障'],
    'global',
    true
);
```

---

## 常見場景

### 場景 1: 查詢個人資料

```json
{
  "endpoint": "get_user_profile",
  "params": {
    "user_id": "{session.user_id}"
  },
  "combine_with_knowledge": true
}
```

### 場景 2: 提交訂單

```json
{
  "endpoint": "create_order",
  "params_from_form": {
    "user_id": "{session.user_id}",
    "product_id": "product_id",
    "quantity": "quantity",
    "address": "shipping_address"
  },
  "combine_with_knowledge": false,
  "response_template": "✅ 訂單已成功送出！\n\n訂單編號：{api_response}\n\n預計 3-5 個工作天送達。"
}
```

### 場景 3: 查詢訂單狀態

```json
{
  "endpoint": "get_order_status",
  "params": {
    "user_id": "{session.user_id}",
    "order_id": "{user_input.order_id}"
  },
  "combine_with_knowledge": true,
  "fallback_message": "⚠️ 訂單查詢失敗，請檢查訂單編號是否正確。"
}
```

### 場景 4: 預約服務（需驗證）

```json
{
  "endpoint": "book_service",
  "verify_identity_first": true,
  "verification_params": {
    "user_id": "{session.user_id}",
    "verification_code": "verification_code"
  },
  "params_from_form": {
    "service_type": "service_type",
    "preferred_date": "date",
    "preferred_time": "time"
  },
  "combine_with_knowledge": false,
  "response_template": "✅ 預約成功！\n\n預約編號：{api_response}\n\n我們會在預約時間前一天提醒您。"
}
```

---

## 如何添加新的 API Endpoint

### 步驟 1: 在 billing_api.py 中實作 API 方法

```python
# rag-orchestrator/services/billing_api.py

async def get_order_status(
    self,
    user_id: str,
    order_id: str
) -> Dict[str, Any]:
    """查詢訂單狀態"""
    if self.use_mock:
        return self._mock_get_order_status(user_id, order_id)

    try:
        async with httpx.AsyncClient(timeout=self.api_timeout) as client:
            response = await client.get(
                f"{self.api_base_url}/api/orders/{order_id}",
                params={'user_id': user_id},
                headers={'X-API-Key': self.api_key}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"❌ 訂單查詢失敗: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': '⚠️ 訂單查詢失敗，請稍後再試。'
        }

def _mock_get_order_status(self, user_id: str, order_id: str) -> Dict[str, Any]:
    """模擬訂單查詢"""
    return {
        'success': True,
        'order_id': order_id,
        'status': '配送中',
        'estimated_delivery': '2026-01-20',
        'message': f'訂單 {order_id} 目前狀態：配送中，預計 2026-01-20 送達。'
    }
```

### 步驟 2: 在 api_call_handler.py 註冊

```python
# rag-orchestrator/services/api_call_handler.py

class APICallHandler:
    def __init__(self):
        self.billing_api = BillingAPIService()

        self.api_registry = {
            'billing_inquiry': self.billing_api.get_invoice_status,
            'verify_tenant_identity': self.billing_api.verify_tenant_identity,
            'resend_invoice': self.billing_api.resend_invoice,
            'maintenance_request': self.billing_api.submit_maintenance_request,
            'get_order_status': self.billing_api.get_order_status,  # ✅ 新增
        }
```

### 步驟 3: 配置知識庫

```sql
INSERT INTO knowledge_base (
    question_summary,
    answer,
    action_type,
    api_config,
    keywords,
    scope,
    is_active
) VALUES (
    '訂單查詢',
    '您可以隨時查詢訂單狀態。',
    'api_call',
    '{
        "endpoint": "get_order_status",
        "params": {
            "user_id": "{session.user_id}",
            "order_id": "{user_input.order_id}"
        },
        "combine_with_knowledge": true
    }'::jsonb,
    ARRAY['訂單', '查詢', '物流'],
    'global',
    true
);
```

---

## 測試配置

### 使用 curl 測試

```bash
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的帳單",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_session_001"
  }'
```

### 檢查日誌

```bash
# Docker 環境
docker-compose logs -f rag-orchestrator | grep -E "🔌|📞|🧪"

# 關鍵日誌標記：
# 🔌 - API 調用開始
# 📞 - 表單完成後 API 調用
# 🧪 - 模擬 API 調用
# ✅ - API 調用成功
# ❌ - API 調用失敗
```

---

## 常見問題

### Q1: 如何判斷該用 `api_call` 還是 `form_then_api`？

**A**:
- 如果用戶已登入且系統有足夠資訊直接調用 API → 用 `api_call`
- 如果需要先收集用戶資訊（如身份驗證） → 用 `form_then_api`

### Q2: 可以同時使用 `params` 和 `params_from_form` 嗎？

**A**: 可以！系統會合併兩者的參數：
```json
{
  "params": {
    "user_id": "{session.user_id}",
    "api_version": "v1"
  },
  "params_from_form": {
    "query_month": "month"
  }
}
```

### Q3: API 調用失敗會怎麼樣？

**A**: 系統會：
1. 記錄錯誤日誌
2. 返回 `fallback_message`（如果有配置）
3. 如果 `combine_with_knowledge=true`，仍會顯示知識答案

### Q4: 如何測試 API 配置？

**A**: 設置環境變數 `USE_MOCK_BILLING_API=true` 使用模擬 API，無需真實外部服務。

---

## 相關文檔

- [系統設計](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [實作指南](./KNOWLEDGE_ACTION_IMPLEMENTATION_GUIDE.md)
- [快速參考](./KNOWLEDGE_ACTION_QUICK_REFERENCE.md)

---

**最後更新**: 2026-01-18
