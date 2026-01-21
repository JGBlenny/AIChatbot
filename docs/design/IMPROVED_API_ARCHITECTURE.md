# 改進的 API 架構設計

**日期**: 2026-01-18
**問題**: 當前每個 API 都要寫一個函數，擴展性差
**解決方案**: 動態配置 + 通用調用器

---

## 🎯 核心理念

**不要為每個 API 寫一個函數，而是用通用的調用器 + 配置來處理！**

---

## 🏗️ 改進後的架構

### 層次 1: 數據庫配置（完整的 API 信息）

```sql
CREATE TABLE api_endpoints (
    id SERIAL PRIMARY KEY,
    endpoint_id VARCHAR(100) UNIQUE NOT NULL,
    endpoint_name VARCHAR(200) NOT NULL,
    endpoint_icon VARCHAR(10) DEFAULT '🔌',
    description TEXT,

    -- ⭐ 新增：實際的 API 配置
    api_url VARCHAR(500),                    -- 例如: https://api.rental.com/v1/rent-history
    http_method VARCHAR(10) DEFAULT 'GET',   -- GET, POST, PUT, DELETE
    request_headers JSONB DEFAULT '{}',      -- {"Authorization": "Bearer {api_key}"}
    request_timeout INTEGER DEFAULT 30,      -- 超時時間（秒）

    -- ⭐ 新增：參數映射配置
    param_mappings JSONB DEFAULT '[]',       -- 參數如何從 session/form/input 取得

    -- ⭐ 新增：響應處理配置
    response_format_type VARCHAR(50),        -- 'template', 'custom', 'raw'
    response_template TEXT,                  -- 響應格式化模板

    -- ⭐ 新增：實作類型
    implementation_type VARCHAR(20) DEFAULT 'dynamic',  -- 'dynamic' 或 'custom'
    custom_handler_name VARCHAR(100),        -- 如果是 custom，指定函數名

    -- 原有欄位
    available_in_knowledge BOOLEAN DEFAULT TRUE,
    available_in_form BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    vendor_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 層次 2: 通用 API 調用器

```python
class UniversalAPICallHandler:
    """通用的 API 調用處理器"""

    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.http_client = httpx.AsyncClient()

        # ⭐ 只註冊需要特殊處理的 API
        self.custom_handlers = {
            'complex_billing_calculation': self._handle_complex_billing,
            'multi_step_verification': self._handle_multi_step_verification,
        }

    async def execute_api_call(
        self,
        endpoint_id: str,
        session_data: Dict[str, Any],
        form_data: Optional[Dict[str, Any]] = None,
        user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        執行 API 調用（動態）
        """
        # 1. 從數據庫載入 API 配置
        endpoint_config = await self._load_endpoint_config(endpoint_id)

        if not endpoint_config:
            return {'success': False, 'error': f'未找到 API: {endpoint_id}'}

        # 2. 判斷實作類型
        if endpoint_config['implementation_type'] == 'custom':
            # 使用自定義處理器
            return await self._execute_custom_handler(endpoint_config, session_data, form_data, user_input)
        else:
            # 使用動態調用
            return await self._execute_dynamic_api(endpoint_config, session_data, form_data, user_input)

    async def _execute_dynamic_api(
        self,
        config: Dict[str, Any],
        session_data: Dict[str, Any],
        form_data: Optional[Dict[str, Any]],
        user_input: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        ⭐ 核心：動態執行 API 調用
        """
        try:
            # 1. 準備 URL
            url = config['api_url']
            url = self._replace_variables(url, session_data, form_data, user_input)

            # 2. 準備參數
            params = self._build_params(
                config['param_mappings'],
                session_data,
                form_data,
                user_input
            )

            # 3. 準備請求頭
            headers = config.get('request_headers', {})
            headers = {
                k: self._replace_variables(v, session_data, form_data, user_input)
                for k, v in headers.items()
            }

            # 4. 執行 HTTP 請求
            method = config['http_method'].upper()
            timeout = config.get('request_timeout', 30)

            logger.info(f"🔌 調用 API: {method} {url}")

            if method == 'GET':
                response = await self.http_client.get(url, params=params, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = await self.http_client.post(url, json=params, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = await self.http_client.put(url, json=params, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = await self.http_client.delete(url, params=params, headers=headers, timeout=timeout)
            else:
                return {'success': False, 'error': f'不支持的 HTTP 方法: {method}'}

            # 5. 處理響應
            response.raise_for_status()
            result = response.json()

            # 6. 格式化響應
            formatted = self._format_response(config, result)

            return {
                'success': True,
                'data': result,
                'formatted_response': formatted
            }

        except Exception as e:
            logger.error(f"❌ API 調用失敗: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _build_params(
        self,
        param_mappings: List[Dict],
        session_data: Dict,
        form_data: Optional[Dict],
        user_input: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        根據配置構建參數

        param_mappings 示例:
        [
            {
                "param_name": "user_id",
                "source": "session",
                "source_key": "user_id",
                "required": true
            },
            {
                "param_name": "start_date",
                "source": "form",
                "source_key": "start_date",
                "default": "2025-01-01"
            }
        ]
        """
        params = {}

        for mapping in param_mappings:
            param_name = mapping['param_name']
            source = mapping['source']  # 'session', 'form', 'input', 'static'

            if source == 'session':
                value = session_data.get(mapping['source_key'])
            elif source == 'form':
                value = form_data.get(mapping['source_key']) if form_data else None
            elif source == 'input':
                value = user_input.get(mapping['source_key']) if user_input else None
            elif source == 'static':
                value = mapping.get('static_value')
            else:
                value = None

            if value is None:
                if mapping.get('required'):
                    raise ValueError(f"缺少必要參數: {param_name}")
                value = mapping.get('default')

            if value is not None:
                params[param_name] = value

        return params

    def _format_response(self, config: Dict, api_result: Dict) -> str:
        """
        根據配置格式化響應
        """
        format_type = config.get('response_format_type', 'template')

        if format_type == 'raw':
            # 直接返回 JSON
            return json.dumps(api_result, ensure_ascii=False, indent=2)

        elif format_type == 'template':
            # 使用模板格式化
            template = config.get('response_template', '')
            return self._apply_template(template, api_result)

        elif format_type == 'custom':
            # 調用自定義格式化函數
            handler_name = config.get('custom_formatter')
            if handler_name in self.custom_formatters:
                return self.custom_formatters[handler_name](api_result)

        return str(api_result)

    def _apply_template(self, template: str, data: Dict) -> str:
        """
        應用模板

        模板示例:
        "您在 {data.month} 的租金為 ${data.amount}，狀態：{data.status}"
        """
        # 簡單的模板替換（可以使用 Jinja2 等更強大的引擎）
        result = template

        def replace_nested(key_path: str, data: Dict) -> str:
            keys = key_path.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, '')
                elif isinstance(value, list) and key.isdigit():
                    value = value[int(key)] if int(key) < len(value) else ''
                else:
                    return ''
            return str(value)

        # 替換 {data.xxx} 格式的變量
        import re
        pattern = r'\{([^}]+)\}'

        def replacer(match):
            key_path = match.group(1)
            return replace_nested(key_path, data)

        result = re.sub(pattern, replacer, result)
        return result

    async def _execute_custom_handler(
        self,
        config: Dict,
        session_data: Dict,
        form_data: Optional[Dict],
        user_input: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        執行自定義處理器（用於複雜業務邏輯）
        """
        handler_name = config.get('custom_handler_name')

        if handler_name not in self.custom_handlers:
            return {
                'success': False,
                'error': f'未找到自定義處理器: {handler_name}'
            }

        handler = self.custom_handlers[handler_name]
        return await handler(session_data, form_data, user_input)
```

---

## 📝 配置示例

### 示例 1: 簡單的查詢 API（完全動態）

```json
{
  "endpoint_id": "rent_history",
  "endpoint_name": "查詢租金紀錄",
  "endpoint_icon": "💰",
  "api_url": "https://api.rental.com/v1/tenants/{session.user_id}/rent-history",
  "http_method": "GET",
  "request_headers": {
    "Authorization": "Bearer {api_key}",
    "Content-Type": "application/json"
  },
  "param_mappings": [
    {
      "param_name": "start_date",
      "source": "form",
      "source_key": "start_date",
      "default": "2025-01-01"
    },
    {
      "param_name": "end_date",
      "source": "form",
      "source_key": "end_date",
      "default": "2025-12-31"
    }
  ],
  "response_format_type": "template",
  "response_template": "📋 您的租金繳納記錄\n\n{records}",
  "implementation_type": "dynamic"
}
```

**完全不需要寫函數！** ✅

### 示例 2: 需要特殊處理的 API（自定義）

```json
{
  "endpoint_id": "complex_billing_calculation",
  "endpoint_name": "複雜帳單計算",
  "implementation_type": "custom",
  "custom_handler_name": "handle_complex_billing"
}
```

**只有這種複雜的才需要寫函數** ⭕

---

## 🎨 管理頁面需要擴展的欄位

```vue
<!-- ApiEndpointsView.vue -->

<div class="form-group">
  <label>實作類型</label>
  <select v-model="formData.implementation_type">
    <option value="dynamic">🔄 動態調用（推薦）</option>
    <option value="custom">⚙️ 自定義處理</option>
  </select>
</div>

<!-- 如果選擇 dynamic -->
<div v-if="formData.implementation_type === 'dynamic'">
  <div class="form-group">
    <label>API URL</label>
    <input v-model="formData.api_url" placeholder="https://api.example.com/v1/..." />
    <small>支持變量: {session.user_id}, {form.xxx}</small>
  </div>

  <div class="form-group">
    <label>HTTP 方法</label>
    <select v-model="formData.http_method">
      <option value="GET">GET</option>
      <option value="POST">POST</option>
      <option value="PUT">PUT</option>
      <option value="DELETE">DELETE</option>
    </select>
  </div>

  <div class="form-group">
    <label>請求頭（JSON）</label>
    <textarea v-model="formData.request_headers" rows="3"></textarea>
  </div>

  <div class="form-group">
    <label>參數映射</label>
    <button @click="addParamMapping">+ 新增參數</button>
    <div v-for="(param, index) in formData.param_mappings" :key="index">
      <input v-model="param.param_name" placeholder="參數名" />
      <select v-model="param.source">
        <option value="session">Session</option>
        <option value="form">Form</option>
        <option value="input">User Input</option>
        <option value="static">靜態值</option>
      </select>
      <input v-model="param.source_key" placeholder="來源鍵" />
      <button @click="removeParamMapping(index)">刪除</button>
    </div>
  </div>

  <div class="form-group">
    <label>響應模板</label>
    <textarea v-model="formData.response_template" rows="5"></textarea>
    <small>
      使用 {data.field} 格式引用響應字段<br>
      例如: 您的餘額為 ${data.balance}
    </small>
  </div>
</div>

<!-- 如果選擇 custom -->
<div v-if="formData.implementation_type === 'custom'">
  <div class="form-group">
    <label>自定義處理器名稱</label>
    <input v-model="formData.custom_handler_name" placeholder="handle_xxx" />
    <small class="warning">⚠️ 需要在後端代碼中實作此函數</small>
  </div>
</div>
```

---

## 📊 對比：改進前 vs 改進後

### 改進前（❌ 每個 API 要寫函數）

```python
# 要新增 10 個 API
async def get_rent_history(...): pass
async def get_contract_info(...): pass
async def get_payment_history(...): pass
async def get_tenant_profile(...): pass
async def get_maintenance_records(...): pass
async def get_invoice_details(...): pass
async def get_lease_terms(...): pass
async def get_property_info(...): pass
async def get_parking_info(...): pass
async def get_amenity_booking(...): pass

# 還要註冊
self.api_registry = {
    'rent_history': self.get_rent_history,
    'contract_info': self.get_contract_info,
    # ... 10 個映射
}
```

**問題**: 寫了 10 個函數，大部分邏輯都重複！

### 改進後（✅ 只需配置）

```sql
-- 在管理頁面新增 10 筆配置
INSERT INTO api_endpoints (endpoint_id, api_url, http_method, ...) VALUES
('rent_history', 'https://api.com/rent-history', 'GET', ...),
('contract_info', 'https://api.com/contract', 'GET', ...),
('payment_history', 'https://api.com/payments', 'GET', ...),
-- ... 只需配置，不需要寫代碼
```

**優勢**:
- ✅ 通過管理頁面配置
- ✅ 不需要寫代碼
- ✅ 不需要重啟服務
- ✅ 非技術人員也能配置

---

## 🎯 總結

### 核心思想
**不要為每個 API 寫函數，而是：**

1. **90% 的 API**: 動態配置（URL + 參數映射 + 響應模板）
2. **10% 的 API**: 自定義函數（複雜業務邏輯）

### 優勢
- ✅ **擴展性極強**: 新增 API 只需配置
- ✅ **維護成本低**: 不需要改代碼
- ✅ **靈活性高**: 支持自定義處理
- ✅ **易於管理**: 通過 UI 配置

### 下一步
1. 擴展 `api_endpoints` 表結構
2. 實作 `UniversalAPICallHandler`
3. 升級管理頁面 UI
4. 遷移現有 API 到新架構

---

**維護者**: Claude Code
**日期**: 2026-01-18
**版本**: 2.0 (改進版)
