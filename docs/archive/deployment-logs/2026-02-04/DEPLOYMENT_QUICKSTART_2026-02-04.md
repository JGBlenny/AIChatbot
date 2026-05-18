# 電費寄送區間查詢系統 - 快速部署指南

**部署日期**: 2026-02-04
**預估時間**: 15-20 分鐘

---

## 🚀 一鍵部署（推薦）

```bash
cd /Users/lenny/jgb/AIChatbot
./scripts/deploy_billing_interval.sh
```

腳本會自動執行：
1. ✅ 前置檢查
2. ✅ 資料庫備份
3. ✅ 配置部署
4. ✅ 資料複製
5. ✅ 服務重啟
6. ✅ 功能測試

---

## ⚡ 手動部署（三步驟）

### 步驟 1: 部署配置與資料

```bash
# 1. 備份
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 匯入配置
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/exports/billing_interval_complete_data.sql

# 3. 複製業者 2 資料
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
  SELECT 2, category, category_name, lookup_key, lookup_value, metadata, is_active, NOW()
  FROM lookup_tables WHERE category = 'billing_interval' AND vendor_id = 1 AND is_active = TRUE
  ON CONFLICT DO NOTHING;
"

# 4. 複製 Embedding
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base SET embedding = (SELECT embedding FROM knowledge_base WHERE id = 1296)
  WHERE id = 1297 AND embedding IS NULL;
"
```

### 步驟 2: 重啟服務

```bash
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
sleep 10
```

### 步驟 3: 驗證

```bash
# 測試業者 1
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{"message":"我想查詢電費寄送區間","vendor_id":1,"user_role":"customer","user_id":"test","session_id":"test1"}'

# 測試業者 2
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{"message":"我想查詢電費寄送區間","vendor_id":2,"user_role":"customer","user_id":"test","session_id":"test2"}'
```

預期結果：兩個測試都應返回 `"form_triggered": true`

---

## 📋 驗收檢查清單

部署完成後，確認以下項目：

```bash
# 執行驗證
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin << 'EOF'
-- 檢查資料筆數
SELECT vendor_id, COUNT(*) FROM lookup_tables
WHERE category = 'billing_interval'
GROUP BY vendor_id;
-- 預期: vendor 1 和 2 各 247 筆

-- 檢查 Embedding
SELECT id, embedding IS NULL FROM knowledge_base WHERE id IN (1296, 1297);
-- 預期: 兩個都是 f (false)

-- 檢查 Scope
SELECT id, vendor_id, scope FROM knowledge_base WHERE id IN (1296, 1297);
-- 預期: 兩個都是 'customized'
EOF
```

### ✅ 必須全部通過

- [ ] 業者 1 資料 = 247 筆
- [ ] 業者 2 資料 = 247 筆
- [ ] ID 1296 有 embedding
- [ ] ID 1297 有 embedding
- [ ] 兩個都是 scope = 'customized'
- [ ] 業者 1 表單觸發成功
- [ ] 業者 2 表單觸發成功

---

## 🔄 快速回滾

如果出現問題：

```bash
# 恢復備份（替換時間戳）
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup_YYYYMMDD_HHMMSS.sql

# 重啟服務
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
```

---

## 📚 詳細文檔

- 完整部署指南: [DEPLOYMENT_2026-02-04_BILLING_INTERVAL.md](./DEPLOYMENT_2026-02-04_BILLING_INTERVAL.md)
- 配置總結: [BILLING_INTERVAL_SETUP_SUMMARY.md](BILLING_INTERVAL_SETUP_SUMMARY.md)
- 檔案索引: [BILLING_INTERVAL_FILES_INDEX.md](BILLING_INTERVAL_FILES_INDEX.md)

---

## 🆘 故障排除

### 問題 1: 業者 2 表單未觸發

**症狀**: `form_triggered: false`

**解決方案**:
```bash
# 檢查 scope 配置
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT id, vendor_id, scope, business_types FROM knowledge_base WHERE id = 1297;
"

# 如果 scope != 'customized'，執行修正
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base
  SET scope = 'customized',
      business_types = ARRAY['property_management', 'full_service']::text[]
  WHERE id = 1297;
"

# 重啟服務
docker-compose -f docker-compose.prod.yml restart rag-orchestrator
```

### 問題 2: 業者 2 無資料

**症狀**: 查詢返回「未找到資訊」

**解決方案**:
```bash
# 重新複製資料
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  DELETE FROM lookup_tables WHERE vendor_id = 2 AND category = 'billing_interval';

  INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
  SELECT 2, category, category_name, lookup_key, lookup_value, metadata, is_active, NOW()
  FROM lookup_tables WHERE category = 'billing_interval' AND vendor_id = 1 AND is_active = TRUE;
"
```

### 問題 3: Embedding 缺失

**症狀**: 知識庫檢索返回 0 筆

**解決方案**:
```bash
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  UPDATE knowledge_base
  SET embedding = (SELECT embedding FROM knowledge_base WHERE id = 1296)
  WHERE id = 1297;
"
```

---

**最後更新**: 2026-02-04
