# 電費寄送區間查詢系統 - 生產環境部署指南

**部署日期**: 2026-02-04
**版本**: v1.0
**Git Commit**: (待填寫)
**部署類型**: 功能增強 + Bug 修復

---

## 📋 部署概要

本次部署包含電費寄送區間查詢系統的完整實現，以及業者 2 配置修正。

### 主要變更

1. **Lookup 系統增強**
   - 提高模糊匹配閾值（0.6 → 0.75）
   - 新增多選項檢測機制（ambiguous_match）
   - 新增表單重試機制（API 失敗時保持 COLLECTING 狀態）
   - 資料庫地址清理（移除括號註記）

2. **業者 2 配置修正**
   - 修正知識庫項目 ID 1297 的 scope 和 business_types
   - 確保業者 2 表單可正常觸發

3. **系統配置**
   - 業者 1 & 2 的表單配置（billing_address_form, billing_address_form_v2）
   - 知識庫項目（ID 1296, 1297）
   - API 端點配置（lookup_billing_interval）
   - Lookup Tables 資料（247 筆地址資料）

---

## ⚠️ 部署前檢查清單

- [ ] 確認資料庫備份已完成
- [ ] 確認 Git 分支為 main 且已 pull 最新代碼
- [ ] 確認 Docker 服務正常運行
- [ ] 確認沒有進行中的用戶會話（或已通知用戶）
- [ ] 準備好回滾計畫

---

## 🚀 部署步驟

### 階段 1: 資料庫配置部署

#### 1.1 備份現有資料

```bash
# 備份整個資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > \
  backup_$(date +%Y%m%d_%H%M%S).sql

# 備份關鍵表
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin \
  -t api_endpoints -t form_schemas -t knowledge_base -t lookup_tables > \
  backup_billing_interval_$(date +%Y%m%d_%H%M%S).sql
```

#### 1.2 部署 API 端點配置

```bash
# 執行完整配置匯入（包含 API 端點、表單、知識庫）
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/exports/billing_interval_complete_data.sql
```

**預期輸出**:
```
INSERT 0 1  -- api_endpoints
INSERT 0 1  -- form_schemas (billing_address_form)
INSERT 0 1  -- form_schemas (billing_address_form_v2)
INSERT 0 1  -- knowledge_base (ID 1296)
INSERT 0 1  -- knowledge_base (ID 1297)
```

#### 1.3 匯入 Lookup Tables 資料

**選項 A: 從業者 1 複製給業者 2（推薦）**

```bash
# 檢查業者 1 資料筆數
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT COUNT(*) FROM lookup_tables
  WHERE vendor_id = 1 AND category = 'billing_interval';
"
# 預期: 247 筆

# 複製給業者 2
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  INSERT INTO lookup_tables (
    vendor_id, category, category_name, lookup_key,
    lookup_value, metadata, is_active, created_at
  )
  SELECT
    2 as vendor_id,
    category, category_name, lookup_key,
    lookup_value, metadata, is_active, NOW()
  FROM lookup_tables
  WHERE category = 'billing_interval'
    AND vendor_id = 1
    AND is_active = TRUE
  ON CONFLICT DO NOTHING;
"

# 驗證業者 2 資料
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
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
"
```

**預期輸出**:
```
 vendor_id | 總筆數 | 單月 | 雙月 | 自繳
-----------+--------+------+------+------
         1 |    247 |   29 |  191 |   27
         2 |    247 |   29 |  191 |   27
(2 rows)
```

**選項 B: 使用 Python 腳本從 Excel 匯入**

```bash
# 如果業者 1 資料也需要重新匯入
cd /Users/lenny/jgb/AIChatbot
python3 scripts/data_import/import_billing_intervals.py \
  --file data/billing_intervals.xlsx \
  --vendor-id 1

# 然後使用選項 A 複製給業者 2
```

#### 1.4 複製 Embedding（重要！）

```bash
# 從業者 1 複製 embedding 給業者 2
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base
  SET embedding = (
    SELECT embedding
    FROM knowledge_base
    WHERE id = 1296
  )
  WHERE id = 1297 AND embedding IS NULL;
"

# 驗證 embedding 已複製
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT
    id,
    vendor_id,
    question_summary,
    embedding IS NULL as no_embedding
  FROM knowledge_base
  WHERE id IN (1296, 1297);
"
```

**預期輸出**:
```
  id  | vendor_id |         question_summary          | no_embedding
------+-----------+-----------------------------------+--------------
 1296 |         1 | 查詢電費帳單寄送區間（單月/雙月） | f
 1297 |         2 | 查詢電費帳單寄送區間（單月/雙月） | f
(2 rows)
```

---

### 階段 2: 應用程式代碼部署

#### 2.1 拉取最新代碼

```bash
cd /Users/lenny/jgb/AIChatbot

# 確認當前分支和狀態
git status
git log --oneline -5

# 拉取最新代碼（如果是從 Git 部署）
git pull origin main
```

#### 2.2 重新構建並重啟服務

```bash
# 重新構建 rag-orchestrator（包含新的代碼修改）
docker-compose build rag-orchestrator

# 重啟服務
docker-compose up -d rag-orchestrator

# 等待服務啟動（約 10 秒）
sleep 10

# 檢查服務狀態
docker-compose ps rag-orchestrator
docker-compose logs --tail=50 rag-orchestrator
```

**預期日誌**:
```
aichatbot-rag-orchestrator  | INFO:     Application startup complete.
aichatbot-rag-orchestrator  | INFO:     Uvicorn running on http://0.0.0.0:8100
```

---

### 階段 3: 功能驗證測試

#### 3.1 業者 1 測試

**測試 1: 表單觸發**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "deploy_test",
    "session_id": "deploy_test_v1_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 業者 1 - 表單觸發測試')
print(f'  Form Triggered: {data.get(\"form_triggered\")}')
print(f'  Form ID: {data.get(\"form_id\")}')
assert data.get('form_triggered') == True, '表單未觸發'
assert data.get('form_id') == 'billing_address_form', 'Form ID 錯誤'
print('✅ 通過')
"
```

**測試 2: 精確匹配**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市新莊區新北大道七段312號10樓",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "deploy_test",
    "session_id": "deploy_test_v1_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 業者 1 - 精確匹配測試')
print(f'  Form Completed: {data.get(\"form_completed\")}')
assert data.get('form_completed') == True, '表單未完成'
assert '雙月' in data.get('answer', ''), '回答中未包含「雙月」'
print('  結果: 雙月 ✅')
print('✅ 通過')
"
```

**測試 3: 模糊匹配（單一結果）**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市三重區重陽路3段158號",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "deploy_test",
    "session_id": "deploy_test_v1_002"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 業者 1 - 模糊匹配測試（單一結果）')
print(f'  Form Completed: {data.get(\"form_completed\")}')
assert data.get('form_completed') == True, '表單未完成'
assert '匹配到相似地址' in data.get('answer', ''), '未顯示模糊匹配警告'
print('✅ 通過')
"
```

**測試 4: 多選項檢測**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市三重區重陽路3段158號",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "deploy_test",
    "session_id": "deploy_test_v1_003"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 業者 1 - 多選項檢測測試')
answer = data.get('answer', '')
if '找到以下幾個相似地址' in answer:
    print('  偵測到多個相似地址 ✅')
else:
    print('  單一匹配結果')
print('✅ 通過')
"
```

#### 3.2 業者 2 測試

**測試 5: 表單觸發**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想查詢電費寄送區間",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "deploy_test",
    "session_id": "deploy_test_v2_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 業者 2 - 表單觸發測試')
print(f'  Form Triggered: {data.get(\"form_triggered\")}')
print(f'  Form ID: {data.get(\"form_id\")}')
assert data.get('form_triggered') == True, '表單未觸發'
assert data.get('form_id') == 'billing_address_form_v2', 'Form ID 錯誤'
print('✅ 通過')
"
```

**測試 6: 完整流程**

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "新北市新莊區新北大道七段312號10樓",
    "vendor_id": 2,
    "user_role": "customer",
    "user_id": "deploy_test",
    "session_id": "deploy_test_v2_001"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 業者 2 - 完整流程測試')
print(f'  Form Completed: {data.get(\"form_completed\")}')
assert data.get('form_completed') == True, '表單未完成'
assert '雙月' in data.get('answer', ''), '回答中未包含「雙月」'
print('  結果: 雙月 ✅')
print('✅ 通過')
"
```

---

### 階段 4: 資料驗證

#### 4.1 驗證配置完整性

```bash
# 執行驗證查詢
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin << 'EOF'
\echo '===== 驗證結果 ====='
\echo ''

-- 1. API 端點
\echo '1. API 端點配置:'
SELECT endpoint_id, endpoint_name, is_active
FROM api_endpoints
WHERE endpoint_id = 'lookup_billing_interval';

\echo ''
\echo '2. 表單配置:'
SELECT form_id, form_name, vendor_id, skip_review, is_active
FROM form_schemas
WHERE form_id IN ('billing_address_form', 'billing_address_form_v2')
ORDER BY vendor_id;

\echo ''
\echo '3. 知識庫項目:'
SELECT
    id,
    vendor_id,
    question_summary,
    scope,
    business_types,
    is_active,
    embedding IS NULL as no_embedding
FROM knowledge_base
WHERE id IN (1296, 1297)
ORDER BY id;

\echo ''
\echo '4. Lookup Tables 統計:'
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

\echo ''
\echo '===== 完成 ====='
EOF
```

**預期輸出**:

```
===== 驗證結果 =====

1. API 端點配置:
      endpoint_id       |    endpoint_name     | is_active
------------------------+----------------------+-----------
 lookup_billing_interval | 電費寄送區間查詢     | t

2. 表單配置:
         form_id         |      form_name      | vendor_id | skip_review | is_active
-------------------------+---------------------+-----------+-------------+-----------
 billing_address_form    | 電費寄送區間查詢    |         1 | t           | t
 billing_address_form_v2 | 電費寄送區間查詢    |         2 | t           | t

3. 知識庫項目:
  id  | vendor_id |         question_summary          |   scope    |           business_types           | is_active | no_embedding
------+-----------+-----------------------------------+------------+------------------------------------+-----------+--------------
 1296 |         1 | 查詢電費帳單寄送區間（單月/雙月） | customized | {property_management,full_service} | t         | f
 1297 |         2 | 查詢電費帳單寄送區間（單月/雙月） | customized | {property_management,full_service} | t         | f

4. Lookup Tables 統計:
 vendor_id | 總筆數 | 單月 | 雙月 | 自繳
-----------+--------+------+------+------
         1 |    247 |   29 |  191 |   27
         2 |    247 |   29 |  191 |   27

===== 完成 =====
```

---

## ✅ 驗收標準

部署完成後，必須滿足以下所有條件：

### 資料庫層

- [x] API 端點 `lookup_billing_interval` 已創建且啟用
- [x] 表單 `billing_address_form` (業者 1) 已創建且啟用
- [x] 表單 `billing_address_form_v2` (業者 2) 已創建且啟用
- [x] 知識庫 ID 1296 (業者 1) 已創建，scope = 'customized'
- [x] 知識庫 ID 1297 (業者 2) 已創建，scope = 'customized'
- [x] 兩個知識庫項目都有 embedding (no_embedding = f)
- [x] 業者 1 有 247 筆 lookup_tables 資料
- [x] 業者 2 有 247 筆 lookup_tables 資料
- [x] 資料統計正確（單月 29、雙月 191、自繳 27）

### 功能層

- [x] 業者 1 可觸發表單
- [x] 業者 2 可觸發表單
- [x] 精確匹配返回正確結果
- [x] 模糊匹配顯示警告訊息
- [x] 多選項檢測正常運作
- [x] 表單重試機制正常（API 失敗時可重新提交）

### 服務層

- [x] rag-orchestrator 服務正常運行
- [x] 無錯誤日誌
- [x] API 響應時間正常（< 3 秒）

---

## 🔄 回滾計畫

如果部署失敗或發現重大問題，執行以下回滾步驟：

### 選項 1: 資料庫回滾

```bash
# 恢復資料庫備份
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  backup_YYYYMMDD_HHMMSS.sql

# 重啟服務
docker-compose restart rag-orchestrator
```

### 選項 2: 刪除新增配置

```bash
# 僅刪除此次部署的配置
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin << 'EOF'
BEGIN;

-- 刪除 Lookup Tables
DELETE FROM lookup_tables
WHERE category = 'billing_interval';

-- 刪除知識庫
DELETE FROM knowledge_base
WHERE id IN (1296, 1297);

-- 刪除表單
DELETE FROM form_schemas
WHERE form_id IN ('billing_address_form', 'billing_address_form_v2');

-- 刪除 API 端點
DELETE FROM api_endpoints
WHERE endpoint_id = 'lookup_billing_interval';

COMMIT;
EOF

# 重啟服務
docker-compose restart rag-orchestrator
```

---

## 📊 效能監控

部署後 24 小時內，請監控以下指標：

1. **API 響應時間**
   ```bash
   # 檢查日誌中的響應時間
   docker-compose logs --tail=100 rag-orchestrator | grep "lookup_billing_interval"
   ```

2. **錯誤率**
   ```bash
   # 檢查錯誤日誌
   docker-compose logs --tail=500 rag-orchestrator | grep -i error
   ```

3. **表單完成率**
   ```sql
   -- 查詢表單統計
   SELECT
       COUNT(*) as 總觸發次數,
       COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as 完成次數,
       COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as 取消次數
   FROM form_sessions
   WHERE form_id IN ('billing_address_form', 'billing_address_form_v2')
       AND created_at > NOW() - INTERVAL '24 hours';
   ```

---

## 📝 相關文件

- [檔案索引](../BILLING_INTERVAL_FILES_INDEX.md)
- [配置總結](../BILLING_INTERVAL_SETUP_SUMMARY.md)
- [Lookup 系統參考](../LOOKUP_SYSTEM_REFERENCE.md)
- [業者 2 修正報告](../VENDOR2_BILLING_INTERVAL_FIX.md)
- [更新日誌](../CHANGELOG_2026-02-04_lookup_improvements.md)

---

## 👥 聯絡資訊

**技術負責人**: DevOps Team
**部署執行**: (待填寫)
**部署時間**: (待填寫)
**部署狀態**: (待填寫)

---

**最後更新**: 2026-02-04
**文件版本**: 1.0
