# 📦 資料庫 Migration 文件

**最後更新**: 2026-04-16
**Migration 總數**: 63 個（含 test/fix/sync 類）
**追蹤機制**: `schema_migrations` 表 + 自動執行腳本

---

## 📋 目錄

- [概述](#概述)
- [快速開始](#快速開始)
- [Migration 清單](#migration-清單)
- [自動執行腳本](#自動執行腳本)
- [手動執行](#手動執行)
- [回滾策略](#回滾策略)
- [常見問題](#常見問題)

---

## 概述

本目錄包含所有資料庫 schema 變更的 migration 檔案。系統使用 `schema_migrations` 表追蹤執行歷史，確保每次推版不會漏掉欄位。

### 核心特性

✅ **自動追蹤**: 每個 migration 執行後記錄到 `schema_migrations` 表
✅ **冪等性**: 已執行的 migration 自動跳過，可重複執行
✅ **執行順序**: 按檔案名稱字母順序自動排序執行
✅ **錯誤處理**: 失敗的 migration 會記錄錯誤訊息

### 命名規範

```
<功能描述>.sql           # 一般功能
<功能描述>_YYYY-MM-DD.sql  # 帶日期的重大變更

範例:
- add_intent_embedding.sql
- create_form_tables.sql
- remove_form_intro_2026-01-13.sql
```

---

## 🚀 快速開始

### 方法 1: 使用自動執行腳本（推薦）

```bash
# 在生產環境執行所有待執行的 migration
./database/run_migrations.sh docker-compose.prod.yml

# 在開發環境執行
./database/run_migrations.sh docker-compose.yml
```

### 方法 2: 查看執行狀態

```bash
# 查看已執行的 migration
docker-compose -f docker-compose.prod.yml exec postgres psql -U aichatbot -d aichatbot_admin -c "
  SELECT migration_name, executed_at, success
  FROM schema_migrations
  ORDER BY executed_at DESC
  LIMIT 20;
"

# 查看資料庫表結構
docker-compose -f docker-compose.prod.yml exec postgres psql -U aichatbot -d aichatbot_admin -c "\dt"
```

---

## Migration 清單

### 0. 000_create_schema_migrations.sql ⭐ 系統核心
**建立日期**: 2026-01-22
**功能**: 建立 migration 追蹤系統
**影響表**: `schema_migrations` (新建)

```sql
CREATE TABLE schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);
```

---

### 1. add_intent_embedding.sql
**建立日期**: 2025-10
**功能**: 為 intents 表新增 embedding 欄位
**影響表**: `intents`

---

### 2. add_admins_table.sql
**建立日期**: 2025-10
**功能**: 建立管理員認證系統基礎表
**影響表**: `admins` (新建)

---

### 3. add_permission_system.sql
**建立日期**: 2025-10
**功能**: 建立完整的 RBAC 權限系統
**影響表**: `roles`, `permissions`, `admin_roles`, `role_permissions` (新建)

---

### 4. create_form_tables.sql
**建立日期**: 2025-11
**功能**: 建立表單管理系統
**影響表**: `form_schemas`, `form_sessions`, `form_submissions` (新建)

---

### 5. verify_form_tables.sql
**建立日期**: 2025-11
**功能**: 驗證表單表結構完整性
**類型**: 驗證腳本

---

### 6. add_form_submission_status.sql
**建立日期**: 2025-11
**功能**: 為 form_submissions 表新增狀態欄位
**影響表**: `form_submissions`

---

### 7. add_form_schema_description_fields.sql
**建立日期**: 2025-12
**功能**: 為表單 schema 新增描述性欄位
**影響表**: `form_schemas`

---

### 8. add_form_sessions_trigger_fields.sql
**建立日期**: 2025-12
**功能**: 為 form_sessions 新增觸發欄位
**影響表**: `form_sessions`

---

### 9. add_knowledge_base_missing_columns.sql
**建立日期**: 2025-12
**功能**: 為 knowledge_base 補充缺少的業務欄位
**影響表**: `knowledge_base`

---

### 10. rename_chat_history_user_role_to_target_user.sql
**建立日期**: 2026-01
**功能**: 重新命名欄位以符合新的命名規範
**影響表**: `chat_history`

---

### 11. add_action_type_and_api_config.sql
**建立日期**: 2026-01-16
**功能**: 為 knowledge_base 新增 action_type 和 api_config 欄位，支援 API 調用功能
**影響表**: `knowledge_base`

```sql
-- 新增 action_type 欄位
ALTER TABLE knowledge_base
ADD COLUMN action_type VARCHAR(50) DEFAULT 'direct_answer';

-- 新增 api_config 欄位
ALTER TABLE knowledge_base
ADD COLUMN api_config JSONB;

-- 新增約束
ALTER TABLE knowledge_base
ADD CONSTRAINT check_action_type
CHECK (action_type IN ('direct_answer', 'form_fill', 'api_call', 'form_then_api'));
```

---

### 12. create_api_endpoints_table.sql
**建立日期**: 2026-01-18
**功能**: 建立 API endpoints 管理表，動態管理系統可用的 API
**影響表**: `api_endpoints` (新建)

---

### 13. upgrade_api_endpoints_dynamic.sql
**建立日期**: 2026-01-20
**功能**: 升級 api_endpoints 表以支持動態配置
**影響表**: `api_endpoints`

新增欄位:
- `implementation_type`: 實作類型 (dynamic/custom)
- `api_url`: API URL
- `http_method`: HTTP 方法
- `param_mappings`: 參數映射
- `response_template`: 響應模板

---

### 14. configure_billing_inquiry_examples.sql
**建立日期**: 2026-01-16
**功能**: 配置帳單查詢相關的知識範例
**影響表**: `knowledge_base`, `intents`

---

### 15. remove_form_intro_2026-01-13.sql ⭐ 刪除欄位
**建立日期**: 2026-01-13
**功能**: 移除 knowledge_base.form_intro 欄位，統一使用 form_schemas.default_intro
**影響表**: `knowledge_base`

```sql
-- 資料遷移（如有需要）
UPDATE knowledge_base
SET form_id = form_id
WHERE form_intro IS NOT NULL;

-- 刪除欄位
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS form_intro;
```

**相關 Commits**:
- `781a7c0`: feat: 移除 form_intro 欄位
- `2a509a9`: fix: 移除 knowledge-admin 後端對 form_intro 的引用
- `5501929`: fix: 移除 rag-orchestrator 所有對 form_intro 的引用

---

### 16. remove_handler_function_column.sql ⭐ 刪除欄位
**建立日期**: 2026-01-21
**功能**: 移除 api_endpoints.handler_function 欄位，改用 custom_handler_name
**影響表**: `api_endpoints`

```sql
-- 刪除欄位
ALTER TABLE api_endpoints DROP COLUMN IF EXISTS handler_function;
```

**原因**: `handler_function` 是舊版欄位，新版使用 `custom_handler_name` (配合 `implementation_type`)

---

### 17. fix_backtest_runs_test_type_constraint.sql
**建立日期**: 2026-04-15
**功能**: 補齊 `backtest_runs.test_type` CHECK constraint，新增 `batch` 和 `continuous_batch`
**影響表**: `backtest_runs`

```sql
ALTER TABLE backtest_runs DROP CONSTRAINT backtest_runs_test_type_check;
ALTER TABLE backtest_runs ADD CONSTRAINT backtest_runs_test_type_check
  CHECK (test_type IN ('smoke', 'full', 'custom', 'batch', 'continuous_batch'));
```

**原因**: 線上 constraint 只允許 smoke/full/custom，知識完善迴圈寫入 `batch` 時 CheckViolation，導致回測失敗。

---

### 18. fix_knowledge_base_loop_fk_on_delete_set_null.sql
**建立日期**: 2026-04-15
**功能**: `knowledge_base` 的 loop 相關 FK 改為 `ON DELETE SET NULL`，並放寬 `check_loop_source`
**影響表**: `knowledge_base`

```sql
-- FK 改為 ON DELETE SET NULL
ALTER TABLE knowledge_base ADD CONSTRAINT knowledge_base_source_loop_id_fkey
  FOREIGN KEY (source_loop_id) REFERENCES knowledge_completion_loops(id) ON DELETE SET NULL;

-- CHECK 放寬，允許 source='loop' 時引用為 NULL
ALTER TABLE knowledge_base ADD CONSTRAINT check_loop_source
  CHECK (
    ((source)::text <> 'loop'::text AND source_loop_id IS NULL AND source_loop_knowledge_id IS NULL)
    OR ((source)::text = 'loop'::text)
  );
```

**原因**: 清除迴圈資料時知識應保留，FK 不應阻擋刪除。

---

### 19. sync_prod_api_forms_knowledge.sql（線上專用）
**建立日期**: 2026-04-15
**功能**: 同步線上 `api_endpoints` / `form_schemas` / `knowledge_base` / `knowledge_intent_mapping` 資料（以本地為準）
**影響表**: `api_endpoints`, `form_schemas`, `knowledge_base`, `knowledge_intent_mapping`, `form_sessions`

**內容**: 刪除死資料 → 更新既有記錄 → 新增缺失記錄（含 lookup endpoints、v2 查詢表單、對應知識與 intent 關聯）。

---

### 20. sync_prod_sop_data.sql（線上專用）
**建立日期**: 2026-04-15
**功能**: 補齊線上 vendor_id=2 缺少的 SOP categories / groups / items
**影響表**: `vendor_sop_categories`, `vendor_sop_groups`, `vendor_sop_items`

**內容**: 只補缺的 3 個 category、1 個 group 和 9 筆 SOP items。Embedding 由 `POST /api/v1/vendors/{id}/sop/regenerate-embeddings` 另外觸發生成。

---

## 🤖 自動執行腳本

### database/run_migrations.sh

這是解決"每次推版都會漏掉欄位"問題的核心腳本。

**功能特性**:
- ✅ 自動掃描所有 migration 文件
- ✅ 檢查 `schema_migrations` 表，跳過已執行的
- ✅ 按字母順序執行未執行的 migration
- ✅ 記錄執行時間和結果
- ✅ 彩色輸出，清晰易讀
- ✅ 失敗時返回非零退出碼

**使用方法**:

```bash
# 基本用法
./database/run_migrations.sh docker-compose.prod.yml

# 查看幫助
./database/run_migrations.sh --help
```

**輸出範例**:

```
========================================
Migration 自動執行腳本
========================================

✓ 資料庫服務運行中
✓ schema_migrations 表已就緒
✓ 找到 17 個 migration 文件

開始執行 migration...

  ⊘ add_admins_table (已執行，跳過)
  ⊘ add_permission_system (已執行，跳過)
  ▶ 執行: new_migration_2026-01-22
  ✓ new_migration_2026-01-22 (成功，耗時 45ms)

========================================
Migration 執行完成
========================================

總計: 17 個 migration
✓ 成功執行: 1
⊘ 已跳過: 16
```

### 整合到部署流程

**推薦做法**: 在每次部署時自動執行

```bash
# 在部署腳本中加入
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 5  # 等待資料庫啟動
./database/run_migrations.sh docker-compose.prod.yml

# 如果 migration 失敗，停止部署
if [ $? -ne 0 ]; then
    echo "Migration 失敗，停止部署"
    exit 1
fi

# 繼續部署其他服務
docker-compose -f docker-compose.prod.yml up -d
```

---

## 手動執行

### 執行單個 Migration

```bash
# 方法 1: 使用 cat | psql
cat database/migrations/your_migration.sql | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin

# 方法 2: 複製到容器內執行
docker cp database/migrations/your_migration.sql aichatbot-postgres:/tmp/
docker exec -it aichatbot-postgres \
  psql -U aichatbot -d aichatbot_admin -f /tmp/your_migration.sql

# 記錄到追蹤表
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c "
    INSERT INTO schema_migrations (migration_name, success)
    VALUES ('your_migration', true);
  "
```

### 查看執行歷史

```bash
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c "
    SELECT
      migration_name,
      executed_at,
      CASE WHEN success THEN '✓' ELSE '✗' END as status,
      execution_time_ms
    FROM schema_migrations
    ORDER BY executed_at DESC;
  "
```

---

## 回滾策略

### 方法一：使用備份恢復

```bash
# 備份當前資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_before_migration.sql

# 執行 migration
./database/run_migrations.sh docker-compose.prod.yml

# 如需回滾，恢復備份
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup_before_migration.sql
```

### 方法二：執行反向 SQL

每個 migration 應包含回滾指令（註解形式）：

```sql
-- Migration: Add new column
ALTER TABLE my_table ADD COLUMN new_column VARCHAR(50);

-- Rollback (uncomment to rollback):
-- ALTER TABLE my_table DROP COLUMN new_column;
```

### 方法三：從 schema_migrations 移除記錄

```bash
# 如果需要重新執行某個 migration
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c "
    DELETE FROM schema_migrations
    WHERE migration_name = 'migration_to_rerun';
  "
```

---

## 常見問題

### Q: 為什麼每次推版都會漏掉欄位？

**A**: 之前沒有 migration 追蹤機制，新的 migration 不會自動執行。現在有了：
1. `schema_migrations` 表追蹤執行歷史
2. `run_migrations.sh` 自動執行腳本
3. 整合到部署流程中

**解決方案**: 每次部署時執行 `./database/run_migrations.sh`

---

### Q: Migration 執行失敗怎麼辦？

**A**:
1. 查看錯誤訊息：腳本會顯示詳細錯誤
2. 查看 Docker 日誌: `docker-compose logs postgres`
3. 檢查 `schema_migrations` 表:
   ```sql
   SELECT * FROM schema_migrations WHERE success = false;
   ```
4. 修正問題後，從 `schema_migrations` 刪除失敗記錄，重新執行

---

### Q: 如何跳過特定 Migration？

**A**: 不建議跳過。如果必須：
```bash
# 手動標記為已執行（不實際執行）
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c "
    INSERT INTO schema_migrations (migration_name, success, created_by)
    VALUES ('migration_to_skip', true, 'manual_skip');
  "
```

---

### Q: 多個開發者同時新增 Migration 怎麼辦？

**A**: 使用日期時間命名，例如:
- `add_feature_a_2026-01-13-10-30.sql`
- `add_feature_b_2026-01-13-11-45.sql`

系統會按字母順序執行，確保順序一致。

---

### Q: 如何在本地測試 Migration？

**A**:
```bash
# 1. 備份本地資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_local.sql

# 2. 執行 migration
./database/run_migrations.sh docker-compose.yml

# 3. 驗證結果
docker-compose exec postgres psql -U aichatbot -d aichatbot_admin -c "\d your_table"

# 4. 如有問題，恢復備份
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup_local.sql
```

---

### Q: 刪除欄位的 Migration 安全嗎？

**A**: 刪除欄位前，請確認：
1. ✅ 程式碼中已移除所有對該欄位的引用
2. ✅ 備份資料庫（以防萬一）
3. ✅ 在測試環境先驗證
4. ✅ 確認該欄位沒有重要資料

範例：
- `remove_form_intro_2026-01-13.sql` - 已確認無資料使用
- `remove_handler_function_column.sql` - 資料已遷移到 `custom_handler_name`

---

## 新增 Migration 流程

### 1. 建立新檔案

```bash
# 帶日期的重大變更
touch database/migrations/add_new_feature_$(date +%Y-%m-%d).sql

# 一般功能
touch database/migrations/add_new_feature.sql
```

### 2. 編寫 SQL

```sql
-- Migration: Add new feature
-- 日期: 2026-01-22
-- 功能: 新增某某功能
-- 影響表: your_table

-- 檢查表是否存在
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='your_table'
                   AND column_name='new_column') THEN
        ALTER TABLE your_table ADD COLUMN new_column VARCHAR(50);
    END IF;
END $$;

-- Rollback:
-- ALTER TABLE your_table DROP COLUMN new_column;
```

### 3. 本地測試

```bash
# 測試語法
cat database/migrations/add_new_feature.sql | \
  docker-compose exec -T postgres psql -U aichatbot -d aichatbot_admin

# 使用自動腳本測試
./database/run_migrations.sh docker-compose.yml
```

### 4. 更新文檔

- 更新本 README.md
- 更新 `docs/database/DATABASE_SCHEMA.md`（如有需要）
- 提交 Git commit

### 5. 部署到生產環境

```bash
# 推送到 Git
git add database/migrations/add_new_feature.sql
git commit -m "feat: add new feature migration"
git push

# 在生產環境執行
./database/run_migrations.sh docker-compose.prod.yml
```

---

## 相關文件

- [資料庫架構文件](../../docs/database/DATABASE_SCHEMA.md)
- [系統架構文件](../../docs/architecture/SYSTEM_ARCHITECTURE.md)
- [部署指南](../../docs/guides/QUICKSTART.md)
- [資料庫 Init 腳本說明](../MIGRATIONS_INFO.md)

---

**維護者**: Claude Code
**最後更新**: 2026-01-22
**下次檢查**: 每次新增 migration 時更新
