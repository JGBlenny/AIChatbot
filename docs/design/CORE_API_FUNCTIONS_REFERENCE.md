# API 核心函數參考

**日期**: 2026-01-20
**版本**: 1.0
**目的**: 快速參考 API 處理系統中的核心函數

---

## 🎯 核心概念

### 統一處理函數

**重要**: 系統有一個統一的函數處理所有動態 API 的回傳數據

```
UniversalAPICallHandler._format_response()
```

**位置**: `services/universal_api_handler.py:352-383`

**作用**:
- ✅ 統一處理所有 `implementation_type='dynamic'` API 的回傳
- ✅ 將原始 JSON 數據轉換為用戶可讀文本
- ✅ 不需要為每個 API 寫格式化代碼

---

## 📦 核心函數列表

### 1. 統一 API 調用入口

```python
APICallHandler.execute_api_call(
    api_config: Dict[str, Any],
    session_data: Dict[str, Any],
    form_data: Optional[Dict[str, Any]] = None,
    user_input: Optional[Dict[str, Any]] = None,
    knowledge_answer: Optional[str] = None
) -> Dict[str, Any]
```

**位置**: `services/api_call_handler.py:53`

**作用**:
- 統一的 API 調用入口
- 根據 `implementation_type` 路由到不同處理器
- 返回統一格式的結果

**返回值**:
```python
{
    'success': bool,              # 調用是否成功
    'data': dict,                 # 原始 API 數據
    'formatted_response': str,    # 格式化後的文本（用戶看到的）
    'error': str                  # 錯誤訊息（如果失敗）
}
```

---

### 2. 動態 API 執行器

```python
UniversalAPICallHandler.execute_api_call(
    endpoint_id: str,
    session_data: Optional[Dict[str, Any]] = None,
    form_data: Optional[Dict[str, Any]] = None,
    user_input: Optional[Dict[str, Any]] = None,
    knowledge_answer: Optional[str] = None
) -> Dict[str, Any]
```

**位置**: `services/universal_api_handler.py:35`

**作用**:
- 處理 `implementation_type='dynamic'` 的 API
- 從數據庫載入配置
- 執行 HTTP 請求
- 調用格式化函數

**處理流程**:
```
載入配置 → 構建請求 → 執行 HTTP → 格式化響應 → 返回結果
```

---

### 3. 🎯 核心統一處理函數

```python
UniversalAPICallHandler._format_response(
    config: Dict[str, Any],
    api_result: Dict[str, Any],
    knowledge_answer: Optional[str] = None
) -> str
```

**位置**: `services/universal_api_handler.py:352-383`

**⭐ 這是統一處理所有動態 API 回傳的核心函數！**

**作用**:
1. ✅ 接收原始 API JSON 數據
2. ✅ 根據 `response_format_type` 選擇格式化方式
3. ✅ 應用 `response_template` 模板
4. ✅ 替換變量 `{name}`, `{email}`, `{company.name}` 等
5. ✅ 合併知識庫答案（如果配置）
6. ✅ 返回用戶可讀的格式化文本

**支持的格式類型**:
- `template`: 使用模板替換變量（最常用）✅
- `raw`: 直接返回 JSON 字符串
- `custom`: 自定義格式化（未實作）

**範圍**:
- ✅ **所有** `implementation_type='dynamic'` 的 API 都使用這個函數
- ✅ 不需要為每個 API 寫格式化代碼
- ✅ 通過數據庫配置控制輸出格式

**示例**:

**輸入**:
```python
config = {
    'response_format_type': 'template',
    'response_template': '📋 用戶資訊\n姓名: {name}\nEmail: {email}\n公司: {company.name}'
}

api_result = {
    'name': 'Chelsey Dietrich',
    'email': 'Lucio_Hettinger@annie.ca',
    'company': {'name': 'Keebler LLC'}
}

knowledge_answer = '以下是您的帳戶資訊：'
```

**處理過程**:
1. 應用模板
2. 替換 `{name}` → `"Chelsey Dietrich"`
3. 替換 `{email}` → `"Lucio_Hettinger@annie.ca"`
4. 替換 `{company.name}` → `"Keebler LLC"`
5. 合併知識答案

**輸出**:
```
以下是您的帳戶資訊：

---

📋 用戶資訊
姓名: Chelsey Dietrich
Email: Lucio_Hettinger@annie.ca
公司: Keebler LLC
```

---

### 4. 模板應用函數

```python
UniversalAPICallHandler._apply_template(
    template: str,
    data: Dict
) -> str
```

**位置**: `services/universal_api_handler.py:385-411`

**作用**:
- 將模板字符串中的變量替換為實際數據
- 支持嵌套字段訪問（如 `{company.name}`）
- 支持數組訪問（如 `{items.0.name}`）

**工作原理**:
1. 使用正則表達式匹配 `{xxx}` 格式的變量
2. 提取變量路徑（支持 `xxx.yyy.zzz`）
3. 從 data 中遞歸獲取值
4. 替換到模板中

**支持的變量格式**:
- `{name}` - 簡單字段
- `{company.name}` - 嵌套字段
- `{address.city}` - 多層嵌套
- `{items.0.title}` - 數組元素（如果需要）

---

### 5. 參數構建函數

```python
UniversalAPICallHandler._build_params(
    param_mappings: List[Dict],
    session_data: Dict,
    form_data: Optional[Dict],
    user_input: Optional[Dict]
) -> Dict[str, Any]
```

**位置**: `services/universal_api_handler.py:234-276`

**作用**:
- 根據 `param_mappings` 配置從不同來源提取參數
- 支持從 session, form, input, static 提取數據
- 處理必填參數和默認值

**參數來源**:
- `session`: 從 session_data 提取（如 user_id）
- `form`: 從 form_data 提取（如表單填寫的值）
- `input`: 從 user_input 提取（如用戶輸入的日期）
- `static`: 靜態值（配置中直接指定）

---

### 6. 變量替換函數

```python
UniversalAPICallHandler._replace_variables(
    template: str,
    session_data: Dict,
    form_data: Optional[Dict],
    user_input: Optional[Dict]
) -> str
```

**位置**: `services/universal_api_handler.py:278-321`

**作用**:
- 替換 URL 和請求體中的變量
- 支持 `{session.user_id}`, `{form.start_date}`, `{input.query}` 格式

**示例**:
```python
# URL 模板
"https://api.example.com/users/{session.user_id}/history"

# session_data
{'user_id': '5'}

# 結果
"https://api.example.com/users/5/history"
```

---

## 🔄 完整調用流程

```
用戶觸發
   ↓
知識檢索（RAG）
   ↓
APICallHandler.execute_api_call()           ← 入口函數
   ↓
判斷 implementation_type
   ├─ dynamic  → UniversalAPICallHandler    ← 動態處理器
   └─ custom   → 自定義函數 (api_registry)
   ↓
UniversalAPICallHandler.execute_api_call()  ← 執行動態 API
   ├─ 載入數據庫配置
   ├─ 構建參數 (_build_params)
   ├─ 替換變量 (_replace_variables)
   ├─ 執行 HTTP 請求
   └─ 格式化響應 (_format_response) ⭐⭐⭐  ← 統一處理函數
        ├─ 應用模板 (_apply_template)
        ├─ 替換變量 {name}, {email}, {company.name}
        └─ 合併知識答案
   ↓
返回 {'success': True, 'data': {...}, 'formatted_response': '...'}
   ↓
chat.py 提取 formatted_response
   ↓
用戶收到格式化後的回應
```

---

## 📊 統一處理的優勢

### 為什麼需要統一處理函數？

**問題**（改進前）:
- ❌ 每個 API 要寫一個格式化函數
- ❌ 大量重複代碼
- ❌ 維護困難
- ❌ 擴展性差

**解決方案**（改進後）:
- ✅ 一個函數處理所有動態 API
- ✅ 通過配置控制格式
- ✅ 零代碼新增 API
- ✅ 易於維護

### 實際效果

**改進前**（需要寫函數）:
```python
# 要新增 10 個 API，需要寫 10 個函數
async def get_rent_history(...): pass
async def get_contract_info(...): pass
async def get_payment_history(...): pass
# ... 7 個更多
```

**改進後**（只需配置）:
```sql
-- 在數據庫中新增配置，不需要寫代碼
INSERT INTO api_endpoints (
    endpoint_id,
    api_url,
    response_template,
    ...
) VALUES
('rent_history', 'https://...', '租金: {amount}', ...),
('contract_info', 'https://...', '合約: {contract_no}', ...),
-- ... 8 個更多，全部零代碼
```

**統計**:
- ✅ 90% 的 API 只需配置（使用統一處理函數）
- ⚙️ 10% 的 API 需要代碼（複雜業務邏輯）

---

## 🎨 配置示例

### 完整的動態 API 配置

```json
{
  "endpoint_id": "example_user_info",
  "endpoint_name": "用戶資訊查詢",
  "implementation_type": "dynamic",
  "api_url": "https://jsonplaceholder.typicode.com/users/{session.user_id}",
  "http_method": "GET",
  "request_headers": {
    "Content-Type": "application/json"
  },
  "param_mappings": [
    {
      "param_name": "user_id",
      "source": "session",
      "source_key": "user_id",
      "required": true,
      "default": "1"
    }
  ],
  "response_format_type": "template",
  "response_template": "📋 用戶資訊\n姓名: {name}\nEmail: {email}\n電話: {phone}\n公司: {company.name}"
}
```

**重點**:
- `response_template` 控制輸出格式
- 支持 `{name}`, `{email}` 等簡單變量
- 支持 `{company.name}` 等嵌套變量
- **不需要寫任何格式化代碼** ✅

---

## 📚 相關文檔

- [API 數據流程完整說明](./API_DATA_FLOW.md) - 詳細的 12 階段流程
- [動態 API 測試報告](../archive/design-reports/DYNAMIC_API_TESTING_REPORT.md) - 測試驗證
- [改進的 API 架構設計](./IMPROVED_API_ARCHITECTURE.md) - 架構設計思路

---

## 🔑 核心要點總結

1. **統一處理函數**: `UniversalAPICallHandler._format_response()`
   - 位置: `services/universal_api_handler.py:352-383`
   - 作用: 統一處理所有動態 API 的回傳數據

2. **數據流程**: API 原始數據 → 模板格式化 → 用戶可讀文本
   - 原始: `{'name': 'John', 'email': 'john@example.com'}`
   - 模板: `"姓名: {name}\nEmail: {email}"`
   - 結果: `"姓名: John\nEmail: john@example.com"`

3. **配置驅動**: 90% 的 API 只需配置，不需要寫代碼
   - 在數據庫中配置 `response_template`
   - 系統自動使用統一處理函數格式化
   - 零代碼新增 API ✅

---

**維護者**: Claude Code
**日期**: 2026-01-20
**版本**: 1.0
