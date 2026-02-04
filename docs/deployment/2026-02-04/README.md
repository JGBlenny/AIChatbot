# 2026-02-04 電費寄送區間查詢系統 部署

**部署日期**: 2026-02-04
**功能**: 電費寄送區間查詢系統（業者 1 & 2）
**狀態**: ✅ 已測試通過（本地環境）

---

## 📁 文件說明

### 🚀 部署指南

| 文件 | 說明 | 用途 |
|------|------|------|
| **DEPLOYMENT_FROM_822e194.md** | 生產環境部署指南 | ⭐ **生產環境必讀** - 從 commit 822e194 的完整部署流程 |
| **DEPLOYMENT_QUICKSTART_2026-02-04.md** | 快速部署指南 | ⚡ **本地測試** - 包含一鍵部署命令 |
| **DEPLOYMENT_2026-02-04_BILLING_INTERVAL.md** | 完整部署指南 | 📚 詳細的 4 階段部署流程、驗證標準、回滾計畫 |

### 📚 技術文檔

| 文件 | 說明 |
|------|------|
| **BILLING_INTERVAL_FILES_INDEX.md** | 檔案索引 - 列出所有相關檔案位置 |
| **BILLING_INTERVAL_SETUP_SUMMARY.md** | 配置總結 - 業者 1 & 2 的完整配置 |
| **LOOKUP_SYSTEM_REFERENCE.md** | Lookup 系統快速參考 - API 文檔 |
| **CHANGELOG_2026-02-04_lookup_improvements.md** | 更新日誌 - 詳細技術變更 |
| **UPDATES_SUMMARY.md** | 更新摘要 - 核心改進總結 |
| **VENDOR2_BILLING_INTERVAL_FIX.md** | 業者 2 修正報告 - Bug 修正詳情 |

---

## ⚡ 快速開始

### 🏭 生產環境部署（從 822e194）

**完整部署指南**: [DEPLOYMENT_FROM_822e194.md](./DEPLOYMENT_FROM_822e194.md)

```bash
# 1. 備份資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > \
  backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 拉取代碼
git checkout main
git pull origin main

# 3. 執行 Migrations（按順序）
for migration in \
  add_followup_prompt_to_knowledge_base \
  create_lookup_tables \
  add_lookup_api_endpoint \
  create_billing_address_form \
  create_billing_knowledge
do
  docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
    database/migrations/${migration}.sql
done

# 4. 匯入業務資料
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/exports/billing_interval_complete_data.sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/seeds/import_vendor2_only.sql

# 5. 重啟服務
docker-compose build rag-orchestrator
docker-compose up -d rag-orchestrator
```

### 🖥️ 本地測試部署（一鍵）

```bash
cd /Users/lenny/jgb/AIChatbot
./scripts/deploy_billing_interval.sh
```

### 📋 手動部署（三步驟）

```bash
# 1. 備份與配置
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d_%H%M%S).sql
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < database/exports/billing_interval_complete_data.sql

# 2. 複製資料與 Embedding
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
  SELECT 2, category, category_name, lookup_key, lookup_value, metadata, is_active, NOW()
  FROM lookup_tables WHERE category = 'billing_interval' AND vendor_id = 1 AND is_active = TRUE
  ON CONFLICT DO NOTHING;

  UPDATE knowledge_base SET embedding = (SELECT embedding FROM knowledge_base WHERE id = 1296)
  WHERE id = 1297 AND embedding IS NULL;
"

# 3. 重啟服務
docker-compose restart rag-orchestrator
```

---

## 📋 部署內容

### 資料庫配置

- **API 端點**: `lookup_billing_interval`
- **表單配置**:
  - 業者 1: `billing_address_form`
  - 業者 2: `billing_address_form_v2`
- **知識庫項目**:
  - 業者 1: ID 1296
  - 業者 2: ID 1297
- **Lookup Tables**: 247 筆地址資料（業者 1 & 2 各一份）

### 功能增強

1. ✅ 提高模糊匹配閾值（0.6 → 0.75）
2. ✅ 新增多選項檢測機制（ambiguous_match）
3. ✅ 新增表單重試機制
4. ✅ 資料庫地址清理（移除括號註記）
5. ✅ 業者 2 配置修正（scope & business_types）

---

## ✅ 驗收標準

部署後必須全部通過：

- [ ] 業者 1 資料 = 247 筆
- [ ] 業者 2 資料 = 247 筆
- [ ] ID 1296 有 embedding, scope = 'customized'
- [ ] ID 1297 有 embedding, scope = 'customized'
- [ ] 業者 1 表單觸發成功
- [ ] 業者 2 表單觸發成功

### 快速驗證命令

```bash
docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
  SELECT vendor_id, COUNT(*) FROM lookup_tables
  WHERE category = 'billing_interval' GROUP BY vendor_id;
"
```

預期輸出：
```
 vendor_id | count
-----------+-------
         1 |   247
         2 |   247
```

---

## 🔗 相關資源

### 資料庫檔案

- 完整匯出: `database/exports/billing_interval_complete_data.sql`
- 業者 1 配置: `database/seeds/billing_interval_system_data.sql`
- 業者 2 配置: `database/seeds/import_vendor2_only.sql`
- CSV 資料: `database/exports/lookup_tables_vendor1.csv`

### 部署腳本

- 自動化部署: `scripts/deploy_billing_interval.sh`
- 資料匯入: `scripts/data_import/import_billing_intervals.py`

---

## 📞 聯絡資訊

**技術負責人**: DevOps Team
**部署狀態**: 待生產環境部署
**建立日期**: 2026-02-04

---

**最後更新**: 2026-02-04
