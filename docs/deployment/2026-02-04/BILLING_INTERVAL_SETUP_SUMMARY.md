# 電費寄送區間查詢系統 - 完整配置總結

**建立日期**: 2026-02-04
**適用業者**: 業者 1 (甲山林) & 業者 2 (信義包租代管)

---

## 📊 系統概覽

### 已完成的配置

| 項目 | 業者 1 | 業者 2 | 狀態 |
|------|--------|--------|------|
| **Lookup Tables 資料** | 247 筆 | 247 筆 | ✅ 完成 |
| **表單配置** | billing_address_form | billing_address_form_v2 | ✅ 完成 |
| **知識庫項目** | ID: 1296 | ID: 1297 | ✅ 完成 |
| **API 端點** | lookup_billing_interval (共用) | lookup_billing_interval (共用) | ✅ 完成 |
| **Embedding** | 已生成 | 已複製 | ✅ 完成 |

### 資料統計

```
業者 1 (vendor_id=1):
  - 總筆數: 247
  - 單月: 29 筆
  - 雙月: 191 筆
  - 自繳: 27 筆

業者 2 (vendor_id=2):
  - 總筆數: 247 (從業者 1 複製)
  - 單月: 29 筆
  - 雙月: 191 筆
  - 自繳: 27 筆
```

---

## 🗂️ 資料庫配置詳情

### 1. API 端點 (共用)

**表**: `api_endpoints`
**ID**: `lookup_billing_interval`

```sql
SELECT * FROM api_endpoints WHERE endpoint_id = 'lookup_billing_interval';
```

**特點**:
- 所有業者共用同一個 API 端點
- 根據 `vendor_id` 參數查詢對應業者的資料
- 支持精確匹配和模糊匹配（閾值 0.75）

---

### 2. 表單配置

#### 業者 1

**表**: `form_schemas`
**Form ID**: `billing_address_form`
**Vendor ID**: `1`

```sql
SELECT * FROM form_schemas WHERE form_id = 'billing_address_form';
```

**配置**:
- `skip_review`: TRUE (自動提交)
- `on_complete_action`: call_api
- `api_config`: 調用 `lookup_billing_interval`

#### 業者 2

**Form ID**: `billing_address_form_v2`
**Vendor ID**: `2`

```sql
SELECT * FROM form_schemas WHERE form_id = 'billing_address_form_v2';
```

**配置**:
- `skip_review`: TRUE (自動提交)
- `on_complete_action`: call_api
- `api_config`: 調用 `lookup_billing_interval`

**注意**: 由於 `form_id` 必須唯一，業者 2 使用 `_v2` 後綴。

---

### 3. 知識庫項目

#### 業者 1

**表**: `knowledge_base`
**ID**: `1296`

```sql
SELECT * FROM knowledge_base WHERE id = 1296;
```

**配置**:
- `question_summary`: 查詢電費帳單寄送區間（單月/雙月）
- `trigger_mode`: auto
- `form_id`: billing_address_form
- `action_type`: form_fill
- `trigger_keywords`: {電費, 寄送, 區間, 單月, 雙月, 帳單}

#### 業者 2

**ID**: `1297`

```sql
SELECT * FROM knowledge_base WHERE id = 1297;
```

**配置**:
- `question_summary`: 查詢電費帳單寄送區間（單月/雙月）
- `trigger_mode`: auto
- `form_id`: billing_address_form_v2
- `action_type`: form_fill
- `trigger_keywords`: {電費, 寄送, 區間, 單月, 雙月, 帳單}
- `embedding`: 從 ID 1296 複製

---

### 4. Lookup Tables 資料

**表**: `lookup_tables`
**Category**: `billing_interval`

```sql
-- 業者 1
SELECT COUNT(*), lookup_value
FROM lookup_tables
WHERE vendor_id = 1 AND category = 'billing_interval'
GROUP BY lookup_value;

-- 業者 2
SELECT COUNT(*), lookup_value
FROM lookup_tables
WHERE vendor_id = 2 AND category = 'billing_interval'
GROUP BY lookup_value;
```

**資料來源**:
- 業者 1: 原始匯入
- 業者 2: 從業者 1 複製

---

## 📁 已建立的檔案

### SQL 腳本

1. **`database/seeds/billing_interval_system_data.sql`**
   - 業者 1 的完整系統配置
   - 包含 API 端點、表單、知識庫項目
   - 用於快速部署或重建

2. **`database/seeds/billing_interval_system_vendor2.sql`**
   - 業者 2 的專用配置
   - 包含表單 (billing_address_form_v2) 和知識庫 (ID 1297)

### Migration 檔案

這些檔案已在之前的部署中執行：

1. `database/migrations/create_lookup_tables.sql` - 創建 lookup_tables 表
2. `database/migrations/add_lookup_api_endpoint.sql` - 新增 API 端點
3. `database/migrations/create_billing_address_form.sql` - 創建業者 1 表單
4. `database/migrations/create_billing_knowledge.sql` - 創建業者 1 知識庫

---

## 🚀 部署與使用

### 業者 1 (已完成)

```bash
# 1. 執行配置腳本
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/seeds/billing_interval_system_data.sql

# 2. 資料已匯入 (247 筆)
# 驗證：
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT COUNT(*) FROM lookup_tables WHERE vendor_id = 1;
"
```

### 業者 2 (已完成)

```bash
# 1. 執行配置腳本
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/seeds/billing_interval_system_vendor2.sql

# 2. 複製資料 (已執行)
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
  SELECT 2, category, category_name, lookup_key, lookup_value, metadata, is_active, NOW()
  FROM lookup_tables
  WHERE category = 'billing_interval' AND vendor_id = 1;
"

# 3. 複製 embedding (已執行)
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base
  SET embedding = (SELECT embedding FROM knowledge_base WHERE id = 1296)
  WHERE id = 1297;
"

# 4. 重啟服務 (已執行)
docker-compose restart rag-orchestrator
```

---

## ✅ 驗證測試

### 業者 1 測試

```bash
# 觸發表單
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_001"
  }'

# 預期結果：
# - form_triggered: true
# - form_id: "billing_address_form"
```

### 業者 2 測試

```bash
# 觸發表單
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_002"
  }'

# 預期結果：
# - form_triggered: true
# - form_id: "billing_address_form_v2"
```

### API 直接測試

```bash
# 業者 1
curl "http://localhost:8100/api/lookup?category=billing_interval&key=新北市三重區重陽路3段158號一樓&vendor_id=1&fuzzy=true&threshold=0.75"

# 業者 2
curl "http://localhost:8100/api/lookup?category=billing_interval&key=新北市三重區重陽路3段158號一樓&vendor_id=2&fuzzy=true&threshold=0.75"
```

---

## 🔧 故障排除

### 問題：業者 2 表單無法觸發

**可能原因**:
1. 知識庫 embedding 未正確複製
2. 服務未重啟
3. 知識庫項目未被正確檢索

**解決方案**:

```bash
# 1. 檢查 embedding
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT id, embedding IS NULL as no_embedding
  FROM knowledge_base
  WHERE id IN (1296, 1297);
"

# 2. 如果 ID 1297 沒有 embedding，重新複製
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base
  SET embedding = (SELECT embedding FROM knowledge_base WHERE id = 1296)
  WHERE id = 1297;
"

# 3. 重啟服務
docker-compose restart rag-orchestrator

# 4. 等待 10 秒後重新測試
sleep 10
```

### 問題：查詢返回「沒有找到資料」

**檢查步驟**:

```bash
# 1. 確認資料存在
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT COUNT(*) FROM lookup_tables
  WHERE vendor_id = 2 AND category = 'billing_interval';
"
# 應該返回: 247

# 2. 測試精確匹配
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT lookup_key, lookup_value
  FROM lookup_tables
  WHERE vendor_id = 2
    AND category = 'billing_interval'
    AND lookup_key = '新北市三重區重陽路3段158號一樓';
"

# 3. 測試模糊匹配邏輯
# (檢查地址格式是否一致)
```

---

## 📚 相關文檔

- [LOOKUP_SYSTEM_REFERENCE.md](./LOOKUP_SYSTEM_REFERENCE.md) - Lookup 系統快速參考
- [DEPLOYMENT_2026-02-04.md](./deployment/DEPLOYMENT_2026-02-04.md) - 完整部署指南
- [CHANGELOG_2026-02-04_lookup_improvements.md](./CHANGELOG_2026-02-04_lookup_improvements.md) - 詳細變更日誌

---

## 🎯 下一步

### 如果需要新增業者 3

1. 複製 `billing_interval_system_vendor2.sql`
2. 修改以下內容：
   - `vendor_id`: 改為 3
   - `form_id`: 改為 `billing_address_form_v3`
   - 知識庫項目的 `vendor_id`
3. 複製 lookup_tables 資料
4. 複製 embedding

### 如果需要修改資料

```bash
# 新增單筆資料
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active)
VALUES (2, 'billing_interval', '電費寄送區間', '新地址', '單月', '{"note": "..."}', TRUE);

# 更新資料
UPDATE lookup_tables
SET lookup_value = '雙月'
WHERE vendor_id = 2 AND lookup_key = '某地址';

# 刪除資料
DELETE FROM lookup_tables
WHERE vendor_id = 2 AND lookup_key = '某地址';
```

---

**最後更新**: 2026-02-04
**維護者**: DevOps Team
