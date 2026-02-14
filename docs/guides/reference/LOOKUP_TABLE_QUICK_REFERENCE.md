# 🚀 Lookup Table System - 快速參考指南

**版本**: v1.0 | **更新**: 2026-02-04 | **狀態**: 📝 規劃中

---

## 📖 概述

Lookup Table System 是一個通用的鍵值對查詢系統，支持：
- ✅ 精確匹配和模糊匹配
- ✅ 多租戶隔離
- ✅ 與知識庫/表單系統無縫整合
- ✅ 易於擴展新的查詢類別

**典型應用**: 電費寄送區間查詢、物業管理員查詢、停車位查詢等

---

## ⚡ 快速開始

### 1. 部署系統（5 分鐘）

```bash
# 1. 創建數據庫表
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin \
  < database/migrations/create_lookup_tables.sql

# 2. 配置 API endpoint
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin \
  < database/migrations/add_lookup_api_endpoint.sql

# 3. 導入數據
python3 scripts/data_import/import_billing_intervals.py

# 4. 創建表單和知識庫
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin \
  < database/test_data/insert_address_form.sql
docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin \
  < database/test_data/insert_billing_knowledge.sql

# 5. 重啟服務
docker-compose restart rag-orchestrator

# 6. 驗證
curl "http://localhost:8100/api/lookup?category=billing_interval&key=測試地址&vendor_id=1"
```

### 2. 測試對話流程（1 分鐘）

```bash
# 訪問前端
open http://localhost:8087/#/knowledge

# 測試對話
用戶: 電費怎麼繳
系統: [顯示地址收集表單]
用戶: 新北市板橋區忠孝路48巷4弄8號二樓
系統: ✅ 查詢成功 - 您的電費帳單於【雙月】寄送
```

---

## 🗄️ 數據庫表結構

### lookup_tables

```sql
CREATE TABLE lookup_tables (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    category VARCHAR(100) NOT NULL,      -- 類別 ID
    lookup_key TEXT NOT NULL,            -- 查詢鍵
    lookup_value TEXT NOT NULL,          -- 查詢值
    metadata JSONB DEFAULT '{}',         -- 額外數據
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(vendor_id, category, lookup_key)
);
```

**索引**:
- `idx_lookup_category`: 類別查詢優化
- `idx_lookup_key_gin`: 模糊匹配優化（GIN 索引）

---

## 🔌 API 使用

### Lookup API

```http
GET /api/lookup?category={category}&key={key}&vendor_id={vendor_id}
```

**參數**:
| 參數 | 必填 | 說明 | 示例 |
|-----|------|-----|------|
| `category` | ✅ | 查詢類別 | `billing_interval` |
| `key` | ✅ | 查詢鍵 | `新北市板橋區...` |
| `vendor_id` | ✅ | 業者 ID | `1` |
| `fuzzy` | ❌ | 模糊匹配 (默認 true) | `true` |
| `threshold` | ❌ | 匹配閾值 (默認 0.6) | `0.8` |

**響應示例**:

```json
{
  "success": true,
  "match_type": "exact",
  "value": "雙月",
  "metadata": {
    "electric_number": "12345678"
  }
}
```

### 列出所有類別

```http
GET /api/lookup/categories?vendor_id=1
```

---

## 📝 如何新增查詢類別

### 步驟 1: 插入數據

```sql
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata) VALUES
(1, 'property_manager', '物業管理員', '社區A', '張三 / 0912-345-678', '{}'),
(1, 'property_manager', '物業管理員', '社區B', '李四 / 0922-111-222', '{}');
```

### 步驟 2: 配置 API endpoint

```sql
INSERT INTO api_endpoints (
    endpoint_id, endpoint_name, implementation_type, api_url, http_method,
    param_mappings, response_template, is_active
) VALUES (
    'lookup_property_manager',
    '物業管理員查詢',
    'dynamic',
    'http://localhost:8100/api/lookup',
    'GET',
    '[
        {"param_name": "category", "source": "static", "static_value": "property_manager", "required": true},
        {"param_name": "key", "source": "form", "source_key": "community_name", "required": true},
        {"param_name": "vendor_id", "source": "session", "source_key": "vendor_id", "required": true}
    ]'::jsonb,
    '✅ 查詢成功\n\n👤 **管理員**: {value}',
    true
);
```

### 步驟 3: 創建表單

```sql
INSERT INTO form_schemas (vendor_id, form_name, fields, submit_behavior) VALUES (
    1,
    '社區名稱收集表單',
    '[{
        "name": "community_name",
        "label": "社區名稱",
        "type": "text",
        "required": true,
        "placeholder": "例如：社區A"
    }]'::jsonb,
    'api_call'
);
```

### 步驟 4: 創建知識庫

```sql
INSERT INTO vendor_knowledge_base (
    vendor_id, question, answer, action_type, form_schema_id, api_config, trigger_mode
) VALUES (
    1,
    '誰是我的物業管理員',
    '請告訴我您的社區名稱，我幫您查詢管理員資訊。',
    'form_then_api',
    (SELECT id FROM form_schemas WHERE form_name = '社區名稱收集表單'),
    '{"endpoint": "lookup_property_manager", "combine_with_knowledge": true}'::jsonb,
    'manual'
);
```

---

## 🧪 常用測試命令

### 測試 Lookup API

```bash
# 精確匹配
curl "http://localhost:8100/api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號二樓&vendor_id=1" | jq

# 模糊匹配
curl "http://localhost:8100/api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號2樓&vendor_id=1" | jq

# 列出類別
curl "http://localhost:8100/api/lookup/categories?vendor_id=1" | jq
```

### 測試完整對話

```bash
# 使用測試腳本
bash tests/test_billing_chat_flow.sh

# 或手動測試
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "電費怎麼繳",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_001"
  }' | jq
```

---

## 🔍 查詢數據庫

### 查看所有類別

```sql
SELECT DISTINCT category, category_name, COUNT(*) as count
FROM lookup_tables
WHERE vendor_id = 1 AND is_active = true
GROUP BY category, category_name;
```

### 查看特定類別數據

```sql
SELECT lookup_key, lookup_value, metadata
FROM lookup_tables
WHERE vendor_id = 1
  AND category = 'billing_interval'
  AND is_active = true
LIMIT 10;
```

### 搜索數據

```sql
-- 精確匹配
SELECT * FROM lookup_tables
WHERE vendor_id = 1
  AND category = 'billing_interval'
  AND lookup_key = '新北市板橋區忠孝路48巷4弄8號二樓';

-- 模糊匹配（使用 LIKE）
SELECT lookup_key, lookup_value, similarity(lookup_key, '新北市板橋區') as sim
FROM lookup_tables
WHERE vendor_id = 1
  AND category = 'billing_interval'
  AND lookup_key ILIKE '%新北市板橋區%'
ORDER BY sim DESC
LIMIT 5;
```

---

## 📊 數據管理

### 批量更新數據

```bash
# 使用導入腳本（UPSERT 模式）
python3 scripts/data_import/import_billing_intervals.py
```

### 手動更新單筆數據

```sql
UPDATE lookup_tables
SET lookup_value = '單月',
    metadata = '{"electric_number": "99999999"}'::jsonb,
    updated_at = CURRENT_TIMESTAMP
WHERE vendor_id = 1
  AND category = 'billing_interval'
  AND lookup_key = '新北市板橋區忠孝路48巷4弄8號二樓';
```

### 刪除數據

```sql
-- 軟刪除（推薦）
UPDATE lookup_tables SET is_active = false
WHERE vendor_id = 1 AND category = 'billing_interval';

-- 硬刪除
DELETE FROM lookup_tables
WHERE vendor_id = 1 AND category = 'billing_interval';
```

---

## 🐛 故障排除

### 問題 1: 查詢無結果

**檢查**:
```sql
-- 確認數據存在
SELECT COUNT(*) FROM lookup_tables
WHERE vendor_id = 1 AND category = 'billing_interval' AND is_active = true;

-- 確認 key 是否完全匹配
SELECT lookup_key FROM lookup_tables
WHERE vendor_id = 1 AND category = 'billing_interval'
ORDER BY lookup_key;
```

**解決**: 調低模糊匹配閾值
```http
GET /api/lookup?...&threshold=0.5
```

### 問題 2: 模糊匹配太慢

**檢查索引**:
```sql
-- 確認 GIN 索引存在
\d lookup_tables

-- 如果缺失，創建索引
CREATE INDEX idx_lookup_key_gin
ON lookup_tables USING gin(lookup_key gin_trgm_ops);
```

### 問題 3: API 調用失敗

**檢查日誌**:
```bash
docker-compose logs -f rag-orchestrator | grep -i "lookup"
```

**驗證配置**:
```sql
SELECT * FROM api_endpoints WHERE endpoint_id = 'lookup_billing_interval';
```

### 問題 4: 表單未觸發

**檢查知識庫配置**:
```sql
SELECT question, action_type, form_schema_id, api_config
FROM vendor_knowledge_base
WHERE question LIKE '%電費%';
```

---

## 📁 文件結構

```
AIChatbot/
├── data/
│   └── 全案場電錶.xlsx                    # 原始數據
├── database/
│   ├── migrations/
│   │   ├── create_lookup_tables.sql       # 創建表
│   │   └── add_lookup_api_endpoint.sql    # 配置 endpoint
│   └── test_data/
│       ├── insert_address_form.sql        # 表單配置
│       └── insert_billing_knowledge.sql   # 知識庫配置
├── rag-orchestrator/
│   ├── routers/
│   │   └── lookup.py                      # Lookup API 實現
│   └── services/
│       ├── api_call_handler.py            # API 調用處理器
│       └── universal_api_handler.py       # 通用 API 處理器
├── scripts/
│   └── data_import/
│       └── import_billing_intervals.py    # 數據導入腳本
├── tests/
│   ├── test_lookup_api.sh                 # API 測試
│   └── test_billing_chat_flow.sh          # 對話流程測試
└── docs/
    ├── design/
    │   └── LOOKUP_TABLE_SYSTEM_DESIGN.md  # 詳細設計文檔
    └── guides/
        └── LOOKUP_TABLE_QUICK_REFERENCE.md # 本文檔
```

---

## 🔗 相關文檔

- [📘 Lookup Table System 詳細設計](../design/LOOKUP_TABLE_SYSTEM_DESIGN.md)
- [📘 Knowledge Action System Design](../design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [📘 API Configuration Guide](../design/API_CONFIGURATION_GUIDE.md)
- [📘 SOP 系統指南](./SOP_GUIDE.md)

---

## 📞 常見問題

### Q: 如何提高模糊匹配準確度？

**A**: 調整 `threshold` 參數：
- `0.8-1.0`: 非常嚴格（推薦用於精確查詢）
- `0.6-0.8`: 中等（默認，適合大多數場景）
- `0.4-0.6`: 寬鬆（用於拼寫錯誤容忍）

### Q: 支持多語言嗎？

**A**: 當前僅支持繁體中文。可在 `metadata` 中存儲多語言：
```json
{
    "value_zh_TW": "雙月",
    "value_en_US": "Bi-monthly"
}
```

### Q: 如何處理大量數據？

**A**:
- 確保 GIN 索引已創建
- 考慮使用 PostgreSQL 分區表（> 100萬筆）
- 使用 Redis 緩存熱門查詢

### Q: 可以整合外部 API 嗎？

**A**: 可以！修改 `lookup.py` 的查詢邏輯：
```python
# 先查本地數據庫
row = await conn.fetchrow(...)
if not row:
    # 調用外部 API
    external_result = await call_external_api(key)
    return external_result
```

---

## 🎯 實戰示例

### 示例 1: 停車位查詢

```sql
-- 1. 插入數據
INSERT INTO lookup_tables (vendor_id, category, lookup_key, lookup_value) VALUES
(1, 'parking_slot', 'ABC-1234', 'B2-015'),
(1, 'parking_slot', 'XYZ-5678', 'B1-032');

-- 2. 創建知識庫
INSERT INTO vendor_knowledge_base (vendor_id, question, answer, action_type, form_schema_id, api_config) VALUES
(1, '我的停車位在哪', '請提供您的車牌號碼。', 'form_then_api', ...);
```

**對話**:
```
用戶: 我的停車位在哪
系統: 請提供您的車牌號碼
用戶: ABC-1234
系統: ✅ 您的停車位在 B2-015
```

### 示例 2: 垃圾收集時間

```sql
INSERT INTO lookup_tables (vendor_id, category, lookup_key, lookup_value) VALUES
(1, 'garbage_schedule', '1樓', '週一、週四 18:00-20:00'),
(1, 'garbage_schedule', '2樓', '週二、週五 18:00-20:00');
```

---

## ✅ 檢查清單

### 部署前

- [ ] 數據庫表已創建
- [ ] API endpoint 已配置
- [ ] 數據已導入並驗證
- [ ] 表單和知識庫已配置
- [ ] 單元測試通過

### 部署後

- [ ] Lookup API 可訪問
- [ ] 精確匹配正常
- [ ] 模糊匹配正常
- [ ] 完整對話流程通過
- [ ] 錯誤日誌無異常

---

**版本**: v1.0 | **最後更新**: 2026-02-04

**快速鏈接**:
- [返回文檔首頁](../README.md)
- [查看詳細設計](../design/LOOKUP_TABLE_SYSTEM_DESIGN.md)
- [報告問題](../../.github/ISSUE_TEMPLATE.md)
