# API 數據流程完整說明

**日期**: 2026-01-20
**版本**: 1.0
**目的**: 詳細說明從 API 調用到用戶收到回應的完整數據流程

---

## 🎯 用戶理解驗證

**用戶的理解**:
> 「從 API 取得資訊後，會在系統組成可用資訊」

**驗證結果**: ✅ **完全正確**

---

## 📊 完整數據流程圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 1: 用戶觸發                                                       │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  用戶輸入: "查詢我的帳戶資訊"
   │  Session: { user_id: "5", vendor_id: 1 }
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 2: 知識檢索（RAG）                                                │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  檢索到知識:
   │  {
   │    "id": 123,
   │    "question": "如何查詢帳戶資訊",
   │    "answer": "以下是您的帳戶資訊：",
   │    "action_type": "api_call",              ← 關鍵：觸發 API 調用
   │    "api_config": {
   │      "endpoint": "example_user_info",
   │      "params": {},
   │      "combine_with_knowledge": true
   │    }
   │  }
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 3: 路由到 API Handler (chat.py:1207)                              │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  db_pool = req.app.state.db_pool
   │  api_handler = get_api_call_handler(db_pool)
   │
   │  api_result = await api_handler.execute_api_call(
   │      api_config=api_config,
   │      session_data=session_data,
   │      knowledge_answer=knowledge_answer   ← 傳入知識答案
   │  )
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 4: APICallHandler 判斷類型 (api_call_handler.py:85)              │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  config = await self._load_endpoint_config('example_user_info')
   │
   │  if config['implementation_type'] == 'dynamic':
   │      ✅ 使用 UniversalAPICallHandler
   │  else:
   │      使用自定義函數 (api_registry)
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 5: 從數據庫載入完整配置 (universal_api_handler.py:104)           │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  SELECT * FROM api_endpoints WHERE endpoint_id = 'example_user_info'
   │
   │  載入配置:
   │  {
   │    "api_url": "https://jsonplaceholder.typicode.com/users/{session.user_id}",
   │    "http_method": "GET",
   │    "param_mappings": [
   │      {
   │        "param_name": "user_id",
   │        "source": "session",
   │        "source_key": "user_id",
   │        "default": "1"
   │      }
   │    ],
   │    "response_format_type": "template",
   │    "response_template": "📋 用戶資訊\n姓名: {name}\nEmail: {email}\n電話: {phone}\n公司: {company.name}"
   │  }
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 6: 準備 HTTP 請求 (universal_api_handler.py:150)                 │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  ① 替換 URL 變量:
   │     "https://.../users/{session.user_id}"
   │     → "https://.../users/5"                ← user_id 從 session 取得
   │
   │  ② 構建參數:
   │     根據 param_mappings 從 session/form/input 提取參數
   │     params = {"user_id": "5"}
   │
   │  ③ 準備請求頭:
   │     headers = {"Content-Type": "application/json"}
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 7: 執行 HTTP 請求 (universal_api_handler.py:183)                 │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  response = await self.http_client.get(
   │      "https://jsonplaceholder.typicode.com/users/5?user_id=5",
   │      headers=headers,
   │      timeout=30
   │  )
   │
   │  ✅ HTTP 200 OK
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 8: 解析 API 響應 (universal_api_handler.py:218)                  │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  📦 原始 JSON 數據:
   │  {
   │    "id": 5,
   │    "name": "Chelsey Dietrich",
   │    "username": "Kamren",
   │    "email": "Lucio_Hettinger@annie.ca",
   │    "address": {
   │      "street": "Skiles Walks",
   │      "suite": "Suite 351",
   │      "city": "Roscoeview",
   │      "zipcode": "33263",
   │      "geo": { "lat": "-31.8129", "lng": "62.5342" }
   │    },
   │    "phone": "(254)954-1289",
   │    "website": "demarco.info",
   │    "company": {
   │      "name": "Keebler LLC",
   │      "catchPhrase": "User-centric fault-tolerant solution",
   │      "bs": "revolutionize end-to-end systems"
   │    }
   │  }
   │
   │  返回:
   │  {
   │    "success": true,
   │    "data": {...},         ← 完整的原始數據
   │    "status_code": 200
   │  }
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 9: 格式化響應 (universal_api_handler.py:352)                     │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  🎨 應用模板格式化:
   │
   │  模板: "📋 用戶資訊\n姓名: {name}\nEmail: {email}\n電話: {phone}\n公司: {company.name}"
   │
   │  ① _apply_template() 遍歷模板中的變量
   │
   │  ② 替換簡單字段:
   │     {name}  → data['name']  → "Chelsey Dietrich"
   │     {email} → data['email'] → "Lucio_Hettinger@annie.ca"
   │     {phone} → data['phone'] → "(254)954-1289"
   │
   │  ③ 替換嵌套字段:
   │     {company.name} → data['company']['name'] → "Keebler LLC"
   │
   │  ④ 格式化結果:
   │     "📋 用戶資訊
   │      姓名: Chelsey Dietrich
   │      Email: Lucio_Hettinger@annie.ca
   │      電話: (254)954-1289
   │      公司: Keebler LLC"
   │
   │  ⑤ 合併知識答案 (如果 combine_with_knowledge=true):
   │     formatted = f"{knowledge_answer}\n\n---\n\n{formatted}"
   │
   │  最終格式化結果:
   │     "以下是您的帳戶資訊：
   │
   │      ---
   │
   │      📋 用戶資訊
   │      姓名: Chelsey Dietrich
   │      Email: Lucio_Hettinger@annie.ca
   │      電話: (254)954-1289
   │      公司: Keebler LLC"
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 10: 返回最終結果 (universal_api_handler.py:96)                   │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  return {
   │    "success": true,
   │    "data": {...},                 ← 保留原始 API 數據（供調試）
   │    "formatted_response": "..."    ← 用戶看到的最終文本
   │  }
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 11: chat.py 提取並返回 (chat.py:1217)                            │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  formatted_response = api_result.get('formatted_response', '')
   │
   │  return VendorChatResponse(
   │      answer=formatted_response,     ← 直接作為答案返回
   │      intent_type='knowledge',
   │      ...
   │  )
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  階段 12: 用戶收到回應                                                  │
└─────────────────────────────────────────────────────────────────────────┘
   │
   │  💬 聊天界面顯示:
   │
   │  ┌─────────────────────────────────────────────────────┐
   │  │ 以下是您的帳戶資訊：                                │
   │  │                                                     │
   │  │ ---                                                 │
   │  │                                                     │
   │  │ 📋 用戶資訊                                         │
   │  │ 姓名: Chelsey Dietrich                              │
   │  │ Email: Lucio_Hettinger@annie.ca                     │
   │  │ 電話: (254)954-1289                                 │
   │  │ 公司: Keebler LLC                                   │
   │  └─────────────────────────────────────────────────────┘
   │
   └─ 用戶看到完整、格式化、可讀的資訊 ✅
```

---

## 🔑 關鍵數據轉換點

### 轉換點 1: API 原始數據 → Python 字典

**位置**: `universal_api_handler.py:219`

```python
result_data = response.json()  # HTTP 響應 → Python dict
```

**輸入**: HTTP 響應體（JSON 字符串）
```json
{"id":5,"name":"Chelsey Dietrich","email":"Lucio_Hettinger@annie.ca",...}
```

**輸出**: Python 字典
```python
{
    'id': 5,
    'name': 'Chelsey Dietrich',
    'email': 'Lucio_Hettinger@annie.ca',
    ...
}
```

---

### 轉換點 2: Python 字典 → 格式化文本

**位置**: `universal_api_handler.py:385-411`

```python
def _apply_template(self, template: str, data: Dict) -> str:
    # 使用正則表達式替換 {xxx} 變量
    pattern = r'\{([^}]+)\}'
    result = re.sub(pattern, replacer, template)
    return result
```

**輸入**:
- 模板: `"姓名: {name}\nEmail: {email}"`
- 數據: `{'name': 'Chelsey Dietrich', 'email': 'Lucio_Hettinger@annie.ca'}`

**處理**:
1. 正則匹配 `{name}` → 提取 `name`
2. 從 data 中獲取 `data['name']` → `"Chelsey Dietrich"`
3. 替換 `{name}` → `"Chelsey Dietrich"`
4. 重複以上步驟處理所有變量

**輸出**: 格式化字符串
```
姓名: Chelsey Dietrich
Email: Lucio_Hettinger@annie.ca
```

---

### 轉換點 3: API 結果 + 知識答案 → 最終回應

**位置**: `universal_api_handler.py:380-381`

```python
if knowledge_answer:
    formatted = f"{knowledge_answer}\n\n---\n\n{formatted}"
```

**輸入**:
- `knowledge_answer`: `"以下是您的帳戶資訊："`
- `formatted`: `"📋 用戶資訊\n姓名: Chelsey Dietrich\n..."`

**輸出**: 合併後的完整文本
```
以下是您的帳戶資訊：

---

📋 用戶資訊
姓名: Chelsey Dietrich
Email: Lucio_Hettinger@annie.ca
電話: (254)954-1289
公司: Keebler LLC
```

---

## 📦 數據結構說明

### API Handler 返回值

```python
{
    'success': bool,              # 調用是否成功
    'data': dict,                 # 原始 API 響應數據（完整 JSON）
    'formatted_response': str,    # 格式化後的文本（用戶看到的）
    'error': str                  # 錯誤訊息（如果失敗）
}
```

**示例**:
```python
{
    'success': True,
    'data': {
        'id': 5,
        'name': 'Chelsey Dietrich',
        'email': 'Lucio_Hettinger@annie.ca',
        'phone': '(254)954-1289',
        'company': {'name': 'Keebler LLC'},
        ...
    },
    'formatted_response': '以下是您的帳戶資訊：\n\n---\n\n📋 用戶資訊\n姓名: Chelsey Dietrich\n...'
}
```

---

## 🎯 系統「組成可用資訊」的具體方式

### 1. 參數提取與替換
從 session/form/input 中提取動態參數，替換到 URL 和請求體中

**示例**:
- 配置: `"api_url": "https://api.com/users/{session.user_id}"`
- Session: `{"user_id": "5"}`
- 結果: `"https://api.com/users/5"`

### 2. 模板格式化
使用配置的 `response_template` 將原始 JSON 轉換為易讀文本

**支持特性**:
- ✅ 簡單字段: `{name}`, `{email}`
- ✅ 嵌套字段: `{company.name}`, `{address.city}`
- ✅ 數組訪問: `{items.0.name}` （如果是數組）

### 3. 知識答案合併
將知識庫的文字說明與 API 數據結合，形成完整回應

**配置控制**:
- `combine_with_knowledge: true` → 合併
- `combine_with_knowledge: false` → 僅 API 結果

### 4. 錯誤處理
當 API 調用失敗時，返回清晰的錯誤訊息（可選擇是否包含知識答案作為降級方案）

---

## ✅ 驗證結論

**用戶的理解**: ✅ **100% 正確**

> 「從 API 取得資訊後，會在系統組成可用資訊」

**具體分解**:

1. ✅ **從 API 取得資訊**:
   - HTTP 請求 → 獲取原始 JSON 數據
   - 解析為 Python 字典
   - 保存在 `result['data']` 中

2. ✅ **在系統組成**:
   - 使用 `response_template` 模板化
   - 替換變量 `{name}`, `{email}` 等
   - 支持嵌套訪問 `{company.name}`
   - 合併知識庫答案（如果配置）

3. ✅ **可用資訊**:
   - 生成 `formatted_response`
   - 直接返回給用戶顯示
   - 易讀、結構化、符合用戶期望

---

## 📊 測試驗證

**測試腳本**: `/tmp/test_end_to_end.py`

**測試結果**: ✅ **所有步驟驗證通過**

- ✅ 原始數據正確獲取
- ✅ 模板變量正確替換
- ✅ 知識答案正確合併
- ✅ 最終用戶看到完整、格式化的資訊

---

## 📞 相關文檔

- [動態 API 測試報告](./DYNAMIC_API_TESTING_REPORT.md)
- [改進的 API 架構設計](./IMPROVED_API_ARCHITECTURE.md)
- [API Endpoint 架構說明](../API_ENDPOINT_ARCHITECTURE.md)

---

**維護者**: Claude Code
**日期**: 2026-01-20
**版本**: 1.0
