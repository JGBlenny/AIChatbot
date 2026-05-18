# 如何新增一個完整的 API Endpoint

> ⚠️ **此文檔部分過時** (2026-01-20)
>
> 本文檔描述的是舊架構下的 API 添加流程（需要寫函數）。
>
> **新架構下的推薦流程**:
> - **90% 的簡單 API**: 只需在數據庫中配置，不需要寫代碼 ✅
>   - 配置 `api_url`, `response_template` 等欄位
>   - 系統自動使用統一處理函數
>   - 參考: [API 核心函數參考](./design/CORE_API_FUNCTIONS_REFERENCE.md)
>
> - **10% 的複雜 API**: 仍然使用本文檔描述的流程
>   - 需要複雜業務邏輯的情況
>   - 按本文檔步驟實作自定義函數
>
> 更多資訊請參考:
> - [改進的 API 架構設計](./design/IMPROVED_API_ARCHITECTURE.md)
> - [API 數據流程完整說明](./design/API_DATA_FLOW.md)
> - [動態 API 測試報告](../../archive/design-reports/DYNAMIC_API_TESTING_REPORT.md)

**日期**: 2026-01-18
**目的**: 從頭到尾新增一個可工作的 API endpoint（自定義函數方式）

---

## 📋 完整流程概覽

新增一個 API endpoint 需要 **3 個步驟**：

```
1️⃣ 前端管理（元數據）
   ↓ 在管理頁面新增 API endpoint 選項

2️⃣ 後端實作（邏輯）
   ↓ 實作實際的 API 調用邏輯

3️⃣ 註冊與測試
   ↓ 註冊到 api_registry 並測試
```

---

## 🎯 範例：新增「查詢租金紀錄」API

假設我們要新增一個 `rent_history` API，用於查詢租客的歷史租金繳納記錄。

---

### Step 1: 前端管理（元數據）

#### 1.1 訪問管理頁面
```
http://localhost:8087/api-endpoints
```

#### 1.2 新增 API Endpoint
點擊「新增 API Endpoint」，填寫：

| 欄位 | 值 | 說明 |
|------|-----|------|
| **Endpoint ID** | `rent_history` | 唯一識別碼（程式中使用） |
| **顯示名稱** | `查詢租金紀錄` | 顯示給用戶看的名稱 |
| **圖示** | `💰` | Emoji 圖示 |
| **描述** | `查詢歷史租金繳納紀錄` | API 功能描述 |
| **處理函數** | `handle_rent_history` | 後端函數名稱（提示用） |
| **知識庫可用** | ✅ 勾選 | 在知識庫管理中可選 |
| **表單可用** | ✅ 勾選 | 在表單管理中可選 |
| **啟用** | ✅ 勾選 | 啟用此 API |

#### 1.3 保存
點擊「儲存」，前端選單中就會出現這個選項。

**但這時候還不能真正使用！**需要繼續後端實作。

---

### Step 2: 後端實作（API 邏輯）

#### 2.1 在 BillingAPIService 中實作 API 方法

**文件**: `rag-orchestrator/services/billing_api.py`

```python
async def get_rent_history(
    self,
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    查詢租金繳納歷史

    Args:
        user_id: 用戶 ID
        start_date: 開始日期（可選，格式 YYYY-MM-DD）
        end_date: 結束日期（可選，格式 YYYY-MM-DD）

    Returns:
        {
            'user_id': '...',
            'records': [
                {
                    'month': '2025-01',
                    'amount': 15000,
                    'paid': True,
                    'paid_date': '2025-01-05',
                    'method': 'bank_transfer'
                },
                ...
            ],
            'total_paid': 180000,
            'total_pending': 0
        }
    """
    try:
        logger.info(f"📋 查詢租金歷史: user_id={user_id}")

        # 構建查詢參數
        params = {'user_id': user_id}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        # 調用實際的 API（示例）
        # 這裡可能是調用你的租賃管理系統 API
        api_url = f"{self.base_url}/rent-history"

        response = await self._make_request('GET', api_url, params=params)

        if response.get('success'):
            return {
                'success': True,
                'data': response.get('data', {}),
                'message': '成功獲取租金歷史'
            }
        else:
            return {
                'success': False,
                'error': response.get('error', '查詢失敗')
            }

    except Exception as e:
        logger.error(f"❌ 查詢租金歷史失敗: {str(e)}")
        return {
            'success': False,
            'error': f'系統錯誤：{str(e)}'
        }
```

#### 2.2 註冊到 APICallHandler

**文件**: `rag-orchestrator/services/api_call_handler.py`

找到 `__init__` 方法中的 `api_registry`，新增映射：

```python
def __init__(self):
    """初始化 API 服務"""
    self.billing_api = BillingAPIService()

    # API endpoint 映射到具體服務
    self.api_registry = {
        'billing_inquiry': self.billing_api.get_invoice_status,
        'verify_tenant_identity': self.billing_api.verify_tenant_identity,
        'resend_invoice': self.billing_api.resend_invoice,
        'maintenance_request': self.billing_api.submit_maintenance_request,
        'rent_history': self.billing_api.get_rent_history,  # ⭐ 新增
    }
```

#### 2.3 配置回傳格式化（可選）

如果需要特殊的格式化邏輯，可以在 `_format_response` 方法中添加：

```python
def _format_response(
    self,
    api_config: Dict[str, Any],
    api_result: Dict[str, Any],
    knowledge_answer: Optional[str] = None
) -> str:
    """格式化 API 響應"""

    endpoint = api_config.get('endpoint')

    # ⭐ 為 rent_history 添加特殊格式化
    if endpoint == 'rent_history':
        return self._format_rent_history_response(api_result, knowledge_answer)

    # 其他 endpoint 的格式化...

def _format_rent_history_response(
    self,
    api_result: Dict[str, Any],
    knowledge_answer: Optional[str] = None
) -> str:
    """格式化租金歷史響應"""

    if not api_result.get('success'):
        return f"❌ 查詢失敗：{api_result.get('error', '未知錯誤')}"

    data = api_result.get('data', {})
    records = data.get('records', [])

    if not records:
        response = "📋 目前沒有租金繳納記錄。"
    else:
        response = "📋 **您的租金繳納記錄**\n\n"
        for record in records:
            status = "✅ 已繳" if record['paid'] else "⏳ 待繳"
            response += f"• {record['month']}: ${record['amount']:,} {status}\n"
            if record['paid']:
                response += f"  繳款日期: {record['paid_date']}\n"

        response += f"\n💰 總已繳金額: ${data.get('total_paid', 0):,}"
        if data.get('total_pending', 0) > 0:
            response += f"\n⏳ 待繳金額: ${data['total_pending']:,}"

    # 如果需要合併知識答案
    if api_config.get('combine_with_knowledge') and knowledge_answer:
        response = f"{knowledge_answer}\n\n---\n\n{response}"

    return response
```

---

### Step 3: 重啟服務

#### 3.1 重啟 rag-orchestrator
```bash
docker restart aichatbot-rag-orchestrator
```

#### 3.2 驗證 API 註冊
```bash
# 檢查日誌中是否有錯誤
docker logs aichatbot-rag-orchestrator --tail 50
```

---

## ✅ 測試流程

### 1. 在知識庫中使用

1. 訪問知識庫管理頁面
2. 新增或編輯一個知識
3. 動作類型選擇：「API 調用 + 知識答案」
4. API Endpoint 下拉選單中選擇：「💰 查詢租金紀錄」
5. 配置參數：
   ```json
   {
     "user_id": "{session.user_id}",
     "start_date": "{user_input.start_date}",
     "end_date": "{user_input.end_date}"
   }
   ```
6. 保存知識

### 2. 在聊天測試

1. 訪問 Chat 測試頁面
2. 輸入觸發該知識的問題
3. 系統會：
   - 檢索到該知識
   - 調用 `rent_history` API
   - 格式化並返回結果

---

## 🎨 API 配置範例

### 簡單配置（只需要 user_id）
```json
{
  "endpoint": "rent_history",
  "params": {
    "user_id": "{session.user_id}"
  },
  "combine_with_knowledge": true
}
```

### 複雜配置（多個參數）
```json
{
  "endpoint": "rent_history",
  "params": {
    "user_id": "{session.user_id}",
    "start_date": "{form.start_date}",
    "end_date": "{form.end_date}",
    "include_details": "true"
  },
  "combine_with_knowledge": true,
  "verify_identity_first": true
}
```

---

## 📊 完整的文件修改清單

| 步驟 | 文件 | 修改內容 | 必須？ |
|------|------|----------|--------|
| 1 | 管理頁面 | 新增 API endpoint 元數據 | ✅ 必須 |
| 2 | `billing_api.py` | 實作 API 調用方法 | ✅ 必須 |
| 3 | `api_call_handler.py` | 註冊到 `api_registry` | ✅ 必須 |
| 4 | `api_call_handler.py` | 自定義格式化（可選） | ⭕ 可選 |
| 5 | 測試 | 在聊天測試頁面驗證 | ✅ 必須 |

---

## 🚨 常見錯誤

### 錯誤 1: "不支援的 API endpoint"
**原因**: 在管理頁面新增了 endpoint，但沒有註冊到 `api_registry`

**解決**:
```python
# 確保在 api_call_handler.py 中註冊
self.api_registry = {
    # ...
    'your_endpoint': self.billing_api.your_method,  # 添加這行
}
```

### 錯誤 2: API 調用失敗
**原因**: 後端方法實作有問題或外部 API 不可用

**解決**:
1. 檢查 `billing_api.py` 中的實作
2. 確認外部 API URL 和參數正確
3. 查看日誌: `docker logs aichatbot-rag-orchestrator`

### 錯誤 3: 參數替換不正確
**原因**: `{session.user_id}` 等動態參數沒有正確替換

**解決**:
- 確保 `_prepare_params` 方法正確處理
- 檢查傳入的 session_data, form_data 是否完整

---

## 🔮 進階：動態配置（未來擴展）

如果希望更靈活，可以在數據庫中存儲更多配置：

### 擴展 api_endpoints 表
```sql
ALTER TABLE api_endpoints ADD COLUMN api_url VARCHAR(500);
ALTER TABLE api_endpoints ADD COLUMN request_method VARCHAR(10) DEFAULT 'GET';
ALTER TABLE api_endpoints ADD COLUMN request_headers JSONB DEFAULT '{}';
ALTER TABLE api_endpoints ADD COLUMN response_format_template TEXT;
```

### 示例配置
```json
{
  "endpoint_id": "rent_history",
  "api_url": "https://api.example.com/v1/rent-history",
  "request_method": "GET",
  "request_headers": {
    "Authorization": "Bearer {api_key}",
    "Content-Type": "application/json"
  },
  "response_format_template": "您在 {month} 的租金為 ${amount}，狀態：{status}"
}
```

這樣就可以在管理頁面直接配置 API URL 和格式，不需要修改代碼！

---

## 📚 相關文檔

- [API Endpoints 管理系統實作](./API_ENDPOINTS_MANAGEMENT_IMPLEMENTATION.md)
- [知識動作系統設計](./design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [API Call Handler 實作](./design/API_CALL_HANDLER_IMPLEMENTATION.md)

---

**維護者**: Claude Code
**日期**: 2026-01-18
**版本**: 1.0
