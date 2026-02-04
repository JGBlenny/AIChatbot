# 生產環境部署指南：從 822e194 到 9b07ced

**起始 Commit**: `822e194` - fix: 修正知識庫表單觸發邏輯，避免 SOP 處理完成錯誤
**目標 Commit**: `9b07ced` - feat: 電費寄送區間查詢系統完整實現與部署資源
**部署日期**: 2026-02-04

---

## 📋 變更總覽

本次部署包含 3 個主要 commits：

1. **3ae0f85** - feat: 實現知識庫表單觸發模式，統一知識庫與 SOP 觸發機制
2. **ae787ed** - feat: 實現 Lookup Table 系統與完整文檔整理
3. **9b07ced** - feat: 電費寄送區間查詢系統完整實現與部署資源

### 核心功能

- ✅ 知識庫表單觸發模式（auto/manual）
- ✅ Lookup Table 系統（地址查詢、模糊匹配）
- ✅ 電費寄送區間查詢（業者 1 & 2）
- ✅ 多選項檢測機制
- ✅ 表單重試機制

### 影響範圍

**後端代碼** (16 個檔案)：
- `rag-orchestrator/routers/chat.py` - 聊天流程增強
- `rag-orchestrator/routers/lookup.py` - 新增 Lookup API
- `rag-orchestrator/services/form_manager.py` - 表單重試機制
- `rag-orchestrator/services/universal_api_handler.py` - API 狀態傳播修正
- `rag-orchestrator/services/sop_orchestrator.py` - SOP 觸發優化

**前端代碼** (5 個檔案)：
- `management-frontend/src/views/KnowledgeView.vue` - 支援觸發模式選擇
- `management-frontend/src/views/FormEditorView.vue` - 表單編輯器增強
- `management-frontend/src/components/VendorSOPManager.vue` - SOP 管理器更新

**資料庫** (8 個 Migration + 3 個 Seed)：
- 新增 lookup_tables 表
- 新增 followup_prompt 欄位
- 新增 API 端點配置
- 新增表單配置
- 新增知識庫項目

---

## ⚠️ 部署前檢查

### 環境需求

- [ ] PostgreSQL 14+
- [ ] Docker & Docker Compose
- [ ] Python 3.9+
- [ ] Node.js 18+
- [ ] 足夠的磁碟空間（至少 2GB）

### 資料備份

```bash
# 完整資料庫備份
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > \
  backup_before_822e194_$(date +%Y%m%d_%H%M%S).sql

# 關鍵表備份
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin \
  -t knowledge_base -t form_schemas -t api_endpoints > \
  backup_critical_tables_$(date +%Y%m%d_%H%M%S).sql
```

### Git 狀態確認

```bash
# 確認當前 commit
git log --oneline -1
# 預期: 822e194 fix: 修正知識庫表單觸發邏輯

# 確認沒有未提交的變更
git status
# 預期: nothing to commit, working tree clean
```

---

## 🚀 部署步驟

### 階段 1: 代碼部署

#### 1.1 拉取最新代碼

```bash
cd /path/to/AIChatbot

# 拉取最新代碼
git fetch origin
git checkout main
git pull origin main

# 確認已更新到 9b07ced
git log --oneline -1
# 預期: 9b07ced feat: 電費寄送區間查詢系統完整實現與部署資源
```

#### 1.2 查看變更內容

```bash
# 查看 commits
git log --oneline 822e194..HEAD

# 預期輸出:
# 9b07ced feat: 電費寄送區間查詢系統完整實現與部署資源
# ae787ed feat: 實現 Lookup Table 系統與完整文檔整理
# 3ae0f85 feat: 實現知識庫表單觸發模式，統一知識庫與 SOP 觸發機制
```

---

### 階段 2: 資料庫 Migration

#### 2.1 執行 Migration（順序執行）

```bash
# Migration 1: 新增 followup_prompt 欄位
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/migrations/add_followup_prompt_to_knowledge_base.sql

# Migration 2: 創建 lookup_tables 表
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/migrations/create_lookup_tables.sql

# Migration 3: 新增 lookup API 端點
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/migrations/add_lookup_api_endpoint.sql

# Migration 4: 創建電費表單配置
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/migrations/create_billing_address_form.sql

# Migration 5: 創建知識庫項目
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/migrations/create_billing_knowledge.sql
```

**每個 Migration 執行後都應檢查輸出，確保沒有錯誤**。

#### 2.2 驗證 Migration

```bash
# 檢查表是否創建
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "\dt lookup_tables"

# 檢查欄位是否新增
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'knowledge_base' AND column_name = 'followup_prompt';
"

# 檢查 API 端點
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT endpoint_id, endpoint_name FROM api_endpoints
  WHERE endpoint_id = 'lookup_billing_interval';
"
```

---

### 階段 3: 業務資料匯入

#### 3.1 匯入業者 1 配置與資料

```bash
# 方式 1: 使用完整匯入腳本（推薦）
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/exports/billing_interval_complete_data.sql

# 方式 2: 分步執行
# 步驟 1: 系統配置
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/seeds/billing_interval_system_data.sql

# 步驟 2: 匯入地址資料（使用 Python 腳本）
python3 scripts/data_import/import_billing_intervals.py \
  --file data/billing_intervals.xlsx \
  --vendor-id 1
```

#### 3.2 匯入業者 2 配置與資料

```bash
# 匯入業者 2（自動複製業者 1 資料）
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/seeds/import_vendor2_only.sql
```

#### 3.3 驗證資料匯入

```bash
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin << 'EOF'
-- 1. 檢查 API 端點
SELECT endpoint_id, endpoint_name, is_active FROM api_endpoints
WHERE endpoint_id = 'lookup_billing_interval';

-- 2. 檢查表單配置
SELECT form_id, form_name, vendor_id, is_active FROM form_schemas
WHERE form_id IN ('billing_address_form', 'billing_address_form_v2')
ORDER BY vendor_id;

-- 3. 檢查知識庫
SELECT id, vendor_id, question_summary, trigger_mode, form_id,
       scope, business_types, embedding IS NULL as no_embedding
FROM knowledge_base
WHERE id IN (1296, 1297)
ORDER BY id;

-- 4. 檢查 Lookup Tables 資料
SELECT
    vendor_id,
    COUNT(*) as 總筆數,
    COUNT(CASE WHEN lookup_value = '單月' THEN 1 END) as 單月,
    COUNT(CASE WHEN lookup_value = '雙月' THEN 1 END) as 雙月,
    COUNT(CASE WHEN lookup_value = '自繳' THEN 1 END) as 自繳
FROM lookup_tables
WHERE category = 'billing_interval'
GROUP BY vendor_id
ORDER BY vendor_id;
EOF
```

**預期結果**:
```
-- API 端點
 endpoint_id             | endpoint_name    | is_active
-------------------------+------------------+-----------
 lookup_billing_interval | 電費寄送區間查詢 | t

-- 表單配置
 form_id                 | form_name        | vendor_id | is_active
-------------------------+------------------+-----------+-----------
 billing_address_form    | 電費寄送區間查詢 |         1 | t
 billing_address_form_v2 | 電費寄送區間查詢 |         2 | t

-- 知識庫
 id   | vendor_id | question_summary              | trigger_mode | form_id                 | scope      | business_types                          | no_embedding
------+-----------+-------------------------------+--------------+-------------------------+------------+-----------------------------------------+--------------
 1296 |         1 | 查詢電費帳單寄送區間（單月/雙月） | auto         | billing_address_form    | customized | {property_management,full_service}       | f
 1297 |         2 | 查詢電費帳單寄送區間（單月/雙月） | auto         | billing_address_form_v2 | customized | {property_management,full_service}       | f

-- Lookup Tables
 vendor_id | 總筆數 | 單月 | 雙月 | 自繳
-----------+--------+------+------+------
         1 |    247 |   29 |  191 |   27
         2 |    247 |   29 |  191 |   27
```

---

### 階段 4: 服務重啟

#### 4.1 後端服務

```bash
# 重新構建（如果有代碼變更）
docker-compose -f docker-compose.prod.yml build rag-orchestrator

# 重啟服務
docker-compose -f docker-compose.prod.yml up -d rag-orchestrator

# 等待服務啟動
sleep 15

# 檢查服務狀態
docker-compose -f docker-compose.prod.yml ps rag-orchestrator
docker-compose -f docker-compose.prod.yml logs --tail=50 rag-orchestrator | grep -i "application startup complete"
```

**預期日誌**:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8100
```

#### 4.2 前端服務（如有變更）

```bash
# 重新構建前端
cd management-frontend
npm run build

# 重啟 Nginx（如適用）
docker-compose -f docker-compose.prod.yml restart nginx
```

---

### 階段 5: 功能驗證測試

#### 5.1 健康檢查

```bash
# 檢查 API 健康狀態
curl http://localhost:8100/health

# 預期: {"status":"healthy"}
```

#### 5.2 業者 1 功能測試

**測試 1: 表單觸發**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "prod_test",
    "session_id": "prod_test_v1_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data.get('form_triggered') == True, '表單未觸發'
assert data.get('form_id') == 'billing_address_form', 'Form ID 錯誤'
print('✅ 業者 1 表單觸發測試通過')
"
```

**測試 2: 完整流程**

```bash
# 提交地址
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市新莊區新北大道七段312號10樓",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "prod_test",
    "session_id": "prod_test_v1_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data.get('form_completed') == True, '表單未完成'
assert '雙月' in data.get('answer', ''), '回答中未包含「雙月」'
print('✅ 業者 1 完整流程測試通過')
print(f'查詢結果: 雙月')
"
```

#### 5.3 業者 2 功能測試

**測試 3: 表單觸發**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "prod_test",
    "session_id": "prod_test_v2_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data.get('form_triggered') == True, '表單未觸發'
assert data.get('form_id') == 'billing_address_form_v2', 'Form ID 錯誤'
print('✅ 業者 2 表單觸發測試通過')
"
```

**測試 4: 完整流程**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市新莊區新北大道七段312號10樓",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "prod_test",
    "session_id": "prod_test_v2_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data.get('form_completed') == True, '表單未完成'
assert '雙月' in data.get('answer', ''), '回答中未包含「雙月」'
print('✅ 業者 2 完整流程測試通過')
print(f'查詢結果: 雙月')
"
```

#### 5.4 邊界測試

**測試 5: 模糊匹配**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市三重區重陽路3段158號",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "prod_test",
    "session_id": "prod_test_fuzzy_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
if '匹配到相似地址' in data.get('answer', ''):
    print('✅ 模糊匹配測試通過（顯示警告）')
else:
    print('⚠️  精確匹配（未觸發模糊匹配）')
"
```

---

## ✅ 驗收標準

部署完成後，**所有項目必須通過**：

### 資料庫層
- [ ] Migration 全部執行成功
- [ ] API 端點 lookup_billing_interval 已創建
- [ ] 表單 billing_address_form (業者 1) 已創建
- [ ] 表單 billing_address_form_v2 (業者 2) 已創建
- [ ] 知識庫 ID 1296 (業者 1) 已創建，有 embedding
- [ ] 知識庫 ID 1297 (業者 2) 已創建，有 embedding
- [ ] 業者 1 有 247 筆 lookup_tables 資料
- [ ] 業者 2 有 247 筆 lookup_tables 資料

### 功能層
- [ ] 業者 1 表單觸發測試通過
- [ ] 業者 2 表單觸發測試通過
- [ ] 業者 1 完整流程測試通過
- [ ] 業者 2 完整流程測試通過
- [ ] 模糊匹配正常運作

### 服務層
- [ ] rag-orchestrator 服務正常運行
- [ ] 無錯誤日誌
- [ ] API 響應時間 < 3 秒
- [ ] 前端服務正常（如有更新）

---

## 🔄 回滾計畫

### 情境 1: Migration 失敗

```bash
# 恢復完整備份
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  backup_before_822e194_YYYYMMDD_HHMMSS.sql

# 重啟服務
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
```

### 情境 2: 資料匯入失敗

```bash
# 僅刪除新增的資料
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin << 'EOF'
BEGIN;

-- 刪除 Lookup Tables
DELETE FROM lookup_tables WHERE category = 'billing_interval';

-- 刪除知識庫
DELETE FROM knowledge_base WHERE id IN (1296, 1297);

-- 刪除表單
DELETE FROM form_schemas
WHERE form_id IN ('billing_address_form', 'billing_address_form_v2');

-- 刪除 API 端點
DELETE FROM api_endpoints WHERE endpoint_id = 'lookup_billing_interval';

COMMIT;
EOF

# 重啟服務
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
```

### 情境 3: 服務異常

```bash
# 回滾代碼
git checkout 822e194

# 重新構建
docker-compose -f docker-compose.prod.yml build rag-orchestrator

# 重啟服務
docker-compose -f docker-compose.prod.yml up -d rag-orchestrator
```

---

## 📊 部署後監控（24小時）

### 1. 錯誤監控

```bash
# 監控錯誤日誌
docker-compose -f docker-compose.prod.yml logs -f rag-orchestrator | grep -i error

# 檢查最近 1 小時的錯誤
docker-compose -f docker-compose.prod.yml logs --since 1h rag-orchestrator | grep -i error | wc -l
```

### 2. 效能監控

```bash
# 檢查 API 響應時間
docker-compose -f docker-compose.prod.yml logs --tail=100 rag-orchestrator | grep "lookup_billing_interval"
```

### 3. 使用統計

```sql
-- 查詢表單使用統計
SELECT
    form_id,
    COUNT(*) as 觸發次數,
    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as 完成次數,
    COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as 取消次數,
    ROUND(100.0 * COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) / COUNT(*), 2) as 完成率
FROM form_sessions
WHERE form_id IN ('billing_address_form', 'billing_address_form_v2')
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY form_id;
```

---

## 📝 變更檔案清單

### 新增檔案 (16)

**資料庫配置**:
- `database/exports/billing_interval_complete_data.sql`
- `database/exports/lookup_tables_vendor1.csv`
- `database/seeds/billing_interval_system_data.sql`
- `database/seeds/billing_interval_system_vendor2.sql`
- `database/seeds/import_vendor2_only.sql`

**Migration**:
- `database/migrations/add_followup_prompt_to_knowledge_base.sql`
- `database/migrations/create_lookup_tables.sql`
- `database/migrations/add_lookup_api_endpoint.sql`
- `database/migrations/create_billing_address_form.sql`
- `database/migrations/create_billing_knowledge.sql`

**部署文檔**:
- `docs/deployment/2026-02-04/` (10 個檔案)
- `scripts/deploy_billing_interval.sh`

### 修改檔案 (主要)

**後端**:
- `rag-orchestrator/routers/chat.py`
- `rag-orchestrator/routers/lookup.py` (新增)
- `rag-orchestrator/services/form_manager.py`
- `rag-orchestrator/services/universal_api_handler.py`
- `rag-orchestrator/services/sop_orchestrator.py`

**前端**:
- `management-frontend/src/views/KnowledgeView.vue`
- `management-frontend/src/views/FormEditorView.vue`
- `management-frontend/src/components/VendorSOPManager.vue`

---

## 📞 支援資訊

**技術負責人**: DevOps Team
**部署執行**: (待填寫)
**部署時間**: (待填寫)
**部署環境**: 生產環境

### 問題回報

如遇到問題，請提供：
1. 錯誤日誌
2. 執行的步驟
3. 預期結果 vs 實際結果

---

**建立日期**: 2026-02-04
**Git 範圍**: 822e194..9b07ced
**文件版本**: 1.0
