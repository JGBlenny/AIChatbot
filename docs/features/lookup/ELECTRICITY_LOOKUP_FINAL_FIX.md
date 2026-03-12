# 電費資訊查詢 - 最終修復完成

## 📅 完成日期
2026-03-12

## 🎯 問題回顧

用戶反映電費資訊查詢功能無法正常顯示完整資料，只顯示「寄送區間: 雙月」而非完整的電費資訊。

**用戶期望:**
```
✅ 查詢成功
- 電號：01190293110
- 寄送區間：雙月
- 計費方式：固定費率
- 固定費率(元/度)：5.5
- 抄表日：每月15日
- 繳費日：每月5日前
```

**實際顯示:**
```
✅ 查詢成功
📊 查詢結果: 雙月
您的電費帳單將於每【雙月】寄送。
```

---

## 🔍 根本原因分析

### 問題 1: API URL 路徑錯誤 ❌
**文件:** 資料庫 `api_endpoints` 表

**問題:** Lookup 路由器的 prefix 從 `/api` 修正為 `/api/v1`，但資料庫中的 API URL 配置沒有同步更新。

**舊配置:**
```
http://localhost:8100/api/lookup
```

**新配置:**
```
http://localhost:8100/api/v1/lookup
```

### 問題 2: 查詢類別錯誤 ❌
**文件:** 資料庫 `form_schemas` 表

**問題:** 表單配置仍在查詢舊的分散格式 `billing_interval`，而非新的整合格式 `utility_electricity`。

**舊配置:**
```json
{
  "endpoint": "lookup_generic",
  "static_params": {"category": "billing_interval"},
  "params_from_form": {"address": "address"}
}
```

**新配置:**
```json
{
  "endpoint": "lookup_generic",
  "static_params": {"category": "utility_electricity"},
  "params_from_form": {"address": "address"}
}
```

### 問題 3: 缺少整合格式資料 ❌
**文件:** 資料庫 `lookup_tables` 表

**問題:** 資料庫中沒有 `utility_electricity` 類別的記錄，只有舊的分散記錄（billing_interval, billing_method 等）。

### 問題 4: JSON 格式化邏輯缺失 ❌
**文件:** `rag-orchestrator/services/universal_api_handler.py`

**問題:** 回應模板中使用 `{formatted_value}` 佔位符，但程式碼中沒有特殊處理邏輯來格式化 JSON 物件為清單顯示。

---

## ✅ 修復方案

### 修復 1: 更新 API URL 路徑
**執行的 SQL:**
```sql
UPDATE api_endpoints
SET api_url = REPLACE(api_url, 'http://localhost:8100/api/lookup', 'http://localhost:8100/api/v1/lookup')
WHERE api_url LIKE 'http://localhost:8100/api/lookup%';
```

**結果:** 更新了 8 個端點

### 修復 2: 更新表單查詢類別
**執行的 SQL:**
```sql
UPDATE form_schemas
SET api_config = '{
  "endpoint": "lookup_generic",
  "static_params": {"category": "utility_electricity"},
  "params_from_form": {"address": "address"}
}'::jsonb
WHERE form_id = 'billing_address_form_v2';
```

### 修復 3: 建立整合格式測試資料
**執行的 SQL:**
```sql
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active)
SELECT
    2 as vendor_id,
    'utility_electricity' as category,
    '電費資訊' as category_name,
    '台北市大安區信義路三段125號5樓之3' as lookup_key,
    json_build_object(
        '寄送區間', '雙月',
        '電號', '01190293110',
        '計費方式', '固定費率',
        '固定費率(元/度)', '5.5',
        '抄表日', '每月15日',
        '繳費日', '每月5日前',
        '台電優惠', '',
        '分攤方式', '',
        '備註', ''
    )::text as lookup_value,
    json_build_object(
        'electric_number', '01190293110',
        'note', '您的電費資訊如下：'
    )::jsonb as metadata,
    true as is_active;
```

### 修復 4: 實現 JSON 格式化邏輯
**檔案:** `rag-orchestrator/services/universal_api_handler.py`
**位置:** Lines 418-461, `_apply_template()` 方法

**新增邏輯:**
```python
def _apply_template(self, template: str, data: Dict) -> str:
    """
    應用響應模板

    特殊處理:
    - {formatted_value}: 如果 value 是 dict/JSON，格式化顯示為清單
    """
    def replacer(match):
        key_path = match.group(1)

        # 特殊處理 formatted_value
        if key_path == 'formatted_value':
            value = data.get('value')
            if isinstance(value, dict):
                # 格式化為清單顯示
                lines = []
                for k, v in value.items():
                    if v and str(v).strip():  # 只顯示非空值
                        lines.append(f"- **{k}**：{v}")
                return '\n'.join(lines) if lines else str(value)
            else:
                return str(value) if value is not None else ''

        # ... 其他處理邏輯
```

**部署步驟:**
```bash
# 1. 停止並移除容器
docker stop aichatbot-rag-orchestrator
docker rm aichatbot-rag-orchestrator

# 2. 重新編譯 (--no-cache 確保使用最新代碼)
docker compose -f docker-compose.prod.yml build --no-cache rag-orchestrator

# 3. 啟動服務
docker compose -f docker-compose.prod.yml up -d rag-orchestrator
```

### 修復 5: 更新回應模板
**執行的 SQL:**
```sql
UPDATE api_endpoints
SET response_template =
'✅ 查詢成功

📊 **電費資訊**：
{formatted_value}

{note}
{fuzzy_warning}'
WHERE endpoint_id = 'lookup_generic';
```

---

## 🧪 測試驗證

### 測試 1: 直接 API 測試 ✅
**命令:**
```bash
curl -s -G "http://localhost:8100/api/v1/lookup" \
  --data-urlencode "category=utility_electricity" \
  --data-urlencode "key=台北市大安區信義路三段125號5樓之3" \
  --data-urlencode "vendor_id=2" \
  --data-urlencode "fuzzy=true"
```

**結果:**
```json
{
  "success": true,
  "match_type": "exact",
  "category": "utility_electricity",
  "key": "台北市大安區信義路三段125號5樓之3",
  "value": {
    "寄送區間": "雙月",
    "電號": "01190293110",
    "計費方式": "固定費率",
    "固定費率(元/度)": "5.5",
    "抄表日": "每月15日",
    "繳費日": "每月5日前"
  }
}
```

**狀態:** ✅ 通過

### 測試 2: Universal API Handler 測試 ✅
**測試檔案:** `test_form_flow.py`

**執行:**
```bash
python3 test_form_flow.py
```

**結果:**
```
測試: 透過 Universal API Handler 查詢電費資訊
地址: 台北市大安區信義路三段125號5樓之3
Vendor ID: 2

API 調用結果:
Success: True

格式化回應 (formatted_response):
✅ 查詢成功

📊 **電費資訊**：
- **寄送區間**：雙月
- **電號**：01190293110
- **計費方式**：固定費率
- **固定費率(元/度)**：5.5
- **抄表日**：每月15日
- **繳費日**：每月5日前

您的電費資訊如下：

欄位檢查:
  ✅ 電號
  ✅ 寄送區間
  ✅ 計費方式
  ✅ 固定費率
  ✅ 抄表日
  ✅ 繳費日
```

**狀態:** ✅ 通過 - 所有 6 個預期欄位都正確顯示

### 測試 3: 聊天介面測試 🔄
**操作步驟:**
1. 在聊天介面輸入：「電費資訊查詢」
2. 系統返回表單要求輸入地址
3. 輸入地址：「台北市大安區信義路三段125號5樓之3」
4. 系統查詢並返回完整電費資訊

**預期結果:**
```
✅ 查詢成功

📊 **電費資訊**：
- **寄送區間**：雙月
- **電號**：01190293110
- **計費方式**：固定費率
- **固定費率(元/度)**：5.5
- **抄表日**：每月15日
- **繳費日**：每月5日前

您的電費資訊如下：
```

**狀態:** 🔄 待用戶在聊天介面測試確認

---

## 📊 修改文件清單

### 資料庫變更
1. ✅ `api_endpoints` - 更新 8 個端點的 API URL
2. ✅ `api_endpoints` - 更新 lookup_generic 的 response_template
3. ✅ `form_schemas` - 更新 billing_address_form_v2 的 api_config
4. ✅ `lookup_tables` - 新增 utility_electricity 測試記錄

### 程式碼變更
1. ✅ `rag-orchestrator/services/universal_api_handler.py:418-461`
   - 新增 `{formatted_value}` 特殊處理邏輯
   - 格式化 JSON 物件為清單顯示

2. ✅ Docker 容器重建
   - 完全移除舊容器
   - --no-cache 重新編譯
   - 驗證程式碼已更新

### 測試檔案
1. ✅ `test_electricity_lookup.sh` - 直接 API 測試腳本
2. ✅ `test_form_flow.py` - Universal API Handler 測試程式

### 文檔
1. ✅ `docs/features/lookup/API_URL_FIX.md` - API URL 修正記錄
2. ✅ `docs/features/lookup/FRONTEND_DISPLAY_FIX.md` - 前端顯示修復
3. ✅ `docs/features/lookup/ELECTRICITY_LOOKUP_FINAL_FIX.md` - 本文檔

---

## 🎯 核心技術點

### 1. 模板變數替換系統
`universal_api_handler.py` 使用正則表達式替換模板中的佔位符：

```python
pattern = r'\{([^}]+)\}'
result = re.sub(pattern, replacer, template)
```

支援兩種佔位符：
- **一般佔位符:** `{key}`, `{nested.key}` - 從 API 回應中取值
- **特殊佔位符:** `{formatted_value}` - 觸發自定義格式化邏輯

### 2. JSON 物件格式化
當遇到 `{formatted_value}` 且 `value` 是 dict 時：

```python
if isinstance(value, dict):
    lines = []
    for k, v in value.items():
        if v and str(v).strip():  # 只顯示非空值
            lines.append(f"- **{k}**：{v}")
    return '\n'.join(lines)
```

輸出格式:
```
- **寄送區間**：雙月
- **電號**：01190293110
- **計費方式**：固定費率
```

### 3. 參數映射機制
`api_endpoints.param_mappings` 定義如何從不同來源提取參數：

```json
[
  {
    "param_name": "category",
    "source": "form",
    "source_key": "category",
    "required": true
  },
  {
    "param_name": "key",
    "source": "form",
    "source_key": "address",
    "required": true
  },
  {
    "param_name": "vendor_id",
    "source": "session",
    "source_key": "vendor_id",
    "required": true
  }
]
```

**來源類型:**
- `form` - 從表單資料提取
- `session` - 從會話資料提取
- `static` - 使用靜態值

### 4. 表單靜態參數合併
`form_manager.py` 在調用 API 前合併 static_params：

```python
# Line 943
merged_form_data = {**form_data, **api_config.get('static_params', {})}
```

這讓表單可以預設某些參數值（如 category），用戶不需要手動輸入。

---

## 📝 後續工作

### 1. 批量匯入完整資料 🔄
目前只有一筆測試地址的 `utility_electricity` 記錄，需要：

1. **準備 Excel 匯入檔案**
   - 使用新的整合格式範本
   - 包含所有地址的完整電費資訊

2. **透過管理介面匯入**
   - URL: http://localhost:8087
   - 功能：💾 Lookup 數據管理 → 📥 匯入 Excel

3. **驗證匯入結果**
   - 檢查所有地址都有 utility_electricity 記錄
   - 確認資料完整性

### 2. 清理舊資料 🔄
確認新資料正常運作後，刪除舊的分散記錄：

```sql
DELETE FROM lookup_tables
WHERE vendor_id = 2
AND category IN (
  'billing_interval',
  'billing_method',
  'meter_reading_day',
  'payment_day'
);
```

### 3. 擴展到水費和瓦斯費 🔄
套用相同模式到其他公用事業費用：

- `utility_water` - 水費資訊
- `utility_gas` - 瓦斯費資訊

需要：
1. 建立對應的表單
2. 配置 API 端點
3. 匯入資料
4. 測試驗證

---

## ✅ 修復確認清單

- [x] API URL 路徑修正 (/api → /api/v1)
- [x] 表單查詢類別更新 (billing_interval → utility_electricity)
- [x] 建立整合格式測試資料
- [x] 實現 JSON 格式化邏輯
- [x] 更新回應模板使用 {formatted_value}
- [x] Docker 容器重建部署
- [x] 直接 API 測試通過
- [x] Universal API Handler 測試通過
- [ ] 聊天介面端到端測試（待用戶確認）
- [ ] 批量匯入完整資料
- [ ] 清理舊格式資料

---

## 🎉 總結

經過以下修復：
1. ✅ API URL 路徑統一為 `/api/v1`
2. ✅ 資料結構從分散格式遷移到整合格式
3. ✅ 實現 JSON 物件自動格式化為清單顯示
4. ✅ 確保 Docker 容器使用最新程式碼

**電費資訊查詢功能現在能夠正確顯示所有 6 個欄位：**
- 寄送區間
- 電號
- 計費方式
- 固定費率(元/度)
- 抄表日
- 繳費日

系統已準備好供用戶在聊天介面中測試完整流程。

---

**文檔版本：** 1.0
**最後更新：** 2026-03-12
**負責人：** AI Assistant
**狀態：** ✅ 技術修復完成，待用戶聊天介面測試確認
