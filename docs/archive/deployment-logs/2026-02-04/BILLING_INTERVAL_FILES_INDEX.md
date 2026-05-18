# 電費寄送區間查詢系統 - 檔案索引

**建立日期**: 2026-02-04
**系統版本**: v1.0
**適用業者**: 業者 1 (甲山林) & 業者 2 (信義包租代管)

---

## 📁 檔案清單

### 1. SQL 配置腳本

#### 業者 1 配置
**檔案**: `database/seeds/billing_interval_system_data.sql`
**內容**:
- ✅ API 端點配置 (`lookup_billing_interval`)
- ✅ 表單配置 (`billing_address_form`)
- ✅ 知識庫項目 (ID: 1296)

**用途**: 快速建立業者 1 的完整系統配置

**執行**:
```bash
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/seeds/billing_interval_system_data.sql
```

---

#### 業者 2 配置
**檔案**: `database/seeds/billing_interval_system_vendor2.sql`
**內容**:
- ✅ 表單配置 (`billing_address_form_v2`)
- ✅ 知識庫項目 (ID: 1297)

**用途**: 建立業者 2 的專用配置（API 端點與業者 1 共用）

**執行**:
```bash
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/seeds/billing_interval_system_vendor2.sql
```

---

#### 完整資料匯出
**檔案**: `database/exports/billing_interval_complete_data.sql`
**內容**:
- ✅ API 端點配置（完整欄位）
- ✅ 表單配置（業者 1 & 2）
- ✅ 知識庫項目（業者 1 & 2）
- ✅ Lookup Tables 資料複製指令
- ✅ Embedding 複製指令
- ✅ 驗證查詢

**用途**:
- 生產環境完整部署
- 災難恢復
- 系統遷移

**特點**:
- 包含所有配置的完整欄位定義
- 包含詳細註解說明
- 包含 ON CONFLICT 處理（支持重複執行）

---

### 2. 資料檔案

#### Lookup Tables 資料 (CSV)
**檔案**: `database/exports/lookup_tables_vendor1.csv`
**內容**: 業者 1 的 247 筆電費寄送區間資料

**格式**:
```csv
vendor_id,category,category_name,lookup_key,lookup_value,metadata,is_active
1,billing_interval,電費寄送區間,台北市中山區民生東路...,單月,"{""note"": ""...""}",t
```

**欄位說明**:
- `vendor_id`: 業者 ID (1 = 甲山林, 2 = 信義包租代管)
- `category`: 類別 (billing_interval)
- `category_name`: 類別中文名稱 (電費寄送區間)
- `lookup_key`: 地址（查詢鍵）
- `lookup_value`: 寄送區間（單月/雙月/自繳）
- `metadata`: JSON 格式的額外資訊（note, electric_number）
- `is_active`: 是否啟用

**統計**:
- 總筆數: 247
- 單月: 29 筆
- 雙月: 191 筆
- 自繳: 27 筆

---

### 3. Migration 腳本

#### 已執行的 Migration
1. **`database/migrations/create_lookup_tables.sql`**
   - 創建 lookup_tables 表
   - 建立索引

2. **`database/migrations/add_lookup_api_endpoint.sql`**
   - 新增 lookup_billing_interval API 端點

3. **`database/migrations/create_billing_address_form.sql`**
   - 創建業者 1 的表單配置

4. **`database/migrations/create_billing_knowledge.sql`**
   - 創建業者 1 的知識庫項目

**狀態**: ✅ 已執行（不需重複執行）

---

### 4. 文檔

#### 系統文檔
1. **`docs/LOOKUP_SYSTEM_REFERENCE.md`**
   - Lookup 系統快速參考
   - 包含 API 端點、錯誤類型、故障排除

2. **`docs/CHANGELOG_2026-02-04_lookup_improvements.md`**
   - 詳細的系統更新日誌
   - 包含技術細節、修改檔案清單

3. **`docs/UPDATES_SUMMARY.md`**
   - 系統更新摘要
   - 快速了解核心改進

4. **`docs/BILLING_INTERVAL_SETUP_SUMMARY.md`**
   - 業者 1 & 2 的完整配置總結
   - 包含驗證測試、故障排除

5. **`docs/BILLING_INTERVAL_FILES_INDEX.md`** (本檔案)
   - 所有檔案的索引和使用說明

#### 部署文檔
6. **`docs/deployment/DEPLOYMENT_2026-02-04.md`**
   - 完整的部署指南
   - 包含部署步驟、驗證測試、回滾計畫

#### 設計與實作文檔
7. **`docs/design/LOOKUP_TABLE_SYSTEM_DESIGN.md`**
   - 系統設計文檔

8. **`docs/implementation/LOOKUP_TABLE_IMPLEMENTATION_SUMMARY.md`**
   - 實作摘要

9. **`docs/testing/LOOKUP_SYSTEM_TEST_GUIDE.md`**
   - 測試指南

10. **`docs/guides/LOOKUP_TABLE_QUICK_REFERENCE.md`**
    - 快速參考指南

---

### 5. 資料導入工具

**檔案**: `scripts/data_import/import_billing_intervals.py`
**用途**: 從 Excel 匯入電費寄送區間資料

**使用方式**:
```bash
python3 scripts/data_import/import_billing_intervals.py \
  --file data/billing_intervals.xlsx \
  --vendor-id 1
```

**功能**:
- ✅ 讀取 Excel 檔案
- ✅ 驗證資料格式
- ✅ 清理地址格式
- ✅ 批量插入資料庫
- ✅ 錯誤處理和報告

---

## 🚀 完整部署流程

### 新環境部署（從零開始）

```bash
# 1. 執行 Migration（如果未執行）
./database/run_migrations.sh docker-compose.yml

# 2. 匯入完整配置
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/exports/billing_interval_complete_data.sql

# 3. 匯入業者 1 資料
python3 scripts/data_import/import_billing_intervals.py \
  --file data/billing_intervals.xlsx \
  --vendor-id 1

# 4. 複製資料給業者 2
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
  SELECT 2, category, category_name, lookup_key, lookup_value, metadata, is_active, NOW()
  FROM lookup_tables
  WHERE category = 'billing_interval' AND vendor_id = 1 AND is_active = TRUE;
"

# 5. 複製 embedding
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base
  SET embedding = (SELECT embedding FROM knowledge_base WHERE id = 1296)
  WHERE id = 1297 AND embedding IS NULL;
"

# 6. 重啟服務
docker-compose -f docker-compose.prod.yml restart rag-orchestrator

# 7. 驗證
docker-compose -f docker-compose.prod.yml logs --tail=20 rag-orchestrator
```

---

### 僅更新配置（資料已存在）

```bash
# 更新配置
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/exports/billing_interval_complete_data.sql

# 重啟服務
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
```

---

## 📊 資料庫表結構

### api_endpoints
```sql
endpoint_id            | lookup_billing_interval
endpoint_name          | 電費寄送區間查詢
implementation_type    | dynamic
api_url                | http://localhost:8100/api/lookup
http_method            | GET
param_mappings         | [見完整 SQL 檔案]
response_template      | ✅ 查詢成功\n\n{fuzzy_warning}...
```

### form_schemas
```sql
-- 業者 1
form_id                | billing_address_form
vendor_id              | 1
skip_review            | TRUE
on_complete_action     | call_api
api_config             | {"endpoint": "lookup_billing_interval", ...}

-- 業者 2
form_id                | billing_address_form_v2
vendor_id              | 2
skip_review            | TRUE
on_complete_action     | call_api
api_config             | {"endpoint": "lookup_billing_interval", ...}
```

### knowledge_base
```sql
-- 業者 1
id                     | 1296
vendor_id              | 1
form_id                | billing_address_form
trigger_mode           | auto
action_type            | form_fill
priority               | 100

-- 業者 2
id                     | 1297
vendor_id              | 2
form_id                | billing_address_form_v2
trigger_mode           | auto
action_type            | form_fill
priority               | 100
```

### lookup_tables
```sql
vendor_id              | 1 或 2
category               | billing_interval
category_name          | 電費寄送區間
lookup_key             | 完整地址
lookup_value           | 單月/雙月/自繳
metadata               | {"note": "...", "electric_number": "..."}
is_active              | TRUE
```

---

## ✅ 驗證檢查清單

### 配置驗證
- [ ] API 端點存在且啟用
- [ ] 表單配置正確（業者 1 & 2）
- [ ] 知識庫項目存在（ID 1296 & 1297）
- [ ] 知識庫項目有 embedding

### 資料驗證
- [ ] 業者 1 有 247 筆資料
- [ ] 業者 2 有 247 筆資料
- [ ] 資料統計正確（單月 29、雙月 191、自繳 27）

### 功能驗證
- [ ] 業者 1 可觸發表單
- [ ] 業者 2 可觸發表單
- [ ] 精確匹配正常
- [ ] 模糊匹配正常
- [ ] 多選項檢測正常
- [ ] 表單重試機制正常

---

## 🔗 相關資源

### 內部文檔
- [Lookup 系統快速參考](./LOOKUP_SYSTEM_REFERENCE.md)
- [部署指南](../DEPLOYMENT_2026-02-04.md)
- [配置總結](./BILLING_INTERVAL_SETUP_SUMMARY.md)

### 資料庫
- `api_endpoints` - API 端點配置表
- `form_schemas` - 表單配置表
- `knowledge_base` - 知識庫表
- `lookup_tables` - Lookup 資料表

### 檔案位置
- SQL 腳本: `database/seeds/` 和 `database/exports/`
- Migration: `database/migrations/`
- 文檔: `docs/`
- 資料導入工具: `scripts/data_import/`

---

**最後更新**: 2026-02-04
**維護者**: DevOps Team
**版本**: 1.0
