# 📦 資料庫 Migration 文件

**最後更新**: 2026-01-14
**Migration 總數**: 11 個

---

## 📋 目錄

- [概述](#概述)
- [Migration 清單](#migration-清單)
- [執行順序](#執行順序)
- [使用說明](#使用說明)
- [回滾策略](#回滾策略)

---

## 概述

本目錄包含所有資料庫 schema 變更的 migration 檔案。Migration 檔案會在 Docker 容器啟動時自動執行。

### 命名規範

```
<功能描述>.sql

範例:
- add_intent_embedding.sql
- create_form_tables.sql
- remove_form_intro_2026-01-13.sql
```

### 執行機制

- Docker 容器啟動時自動執行
- 按照檔案名稱排序執行
- 執行記錄儲存在 `schema_migrations` 表

---

## Migration 清單

### 1. add_intent_embedding.sql
**建立日期**: 2025-10
**功能**: 為 intents 表新增 embedding 欄位
**影響表**: `intents`

```sql
-- 新增欄位
ALTER TABLE intents ADD COLUMN embedding vector(1536);

-- 建立向量索引
CREATE INDEX idx_intents_embedding ON intents
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

---

### 2. add_admins_table.sql
**建立日期**: 2025-10
**功能**: 建立管理員認證系統基礎表
**影響表**: `admins`

```sql
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 3. add_permission_system.sql
**建立日期**: 2025-10
**功能**: 建立完整的 RBAC 權限系統
**影響表**: `roles`, `permissions`, `admin_roles`, `role_permissions`

建立表:
- `roles`: 角色定義
- `permissions`: 權限定義
- `admin_roles`: 管理員角色關聯 (多對多)
- `role_permissions`: 角色權限關聯 (多對多)

---

### 4. create_form_tables.sql
**建立日期**: 2025-11
**功能**: 建立表單管理系統
**影響表**: `forms`, `form_sessions`, `form_submissions`

建立表:
- `forms`: 表單定義
- `form_sessions`: 表單填寫會話
- `form_submissions`: 表單提交記錄

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

```sql
ALTER TABLE form_submissions
ADD COLUMN status VARCHAR(20) DEFAULT 'pending';

-- 可選值: pending, approved, rejected
```

---

### 7. add_form_schema_description_fields.sql
**建立日期**: 2025-12
**功能**: 為表單 schema 新增描述性欄位
**影響表**: `forms`

```sql
ALTER TABLE forms
ADD COLUMN field_descriptions JSONB;
```

---

### 8. add_form_sessions_trigger_fields.sql
**建立日期**: 2025-12
**功能**: 為 form_sessions 新增觸發欄位
**影響表**: `form_sessions`

```sql
ALTER TABLE form_sessions
ADD COLUMN triggered_by VARCHAR(50),
ADD COLUMN trigger_context JSONB;
```

---

### 9. add_knowledge_base_missing_columns.sql
**建立日期**: 2025-12
**功能**: 為 knowledge_base 補充缺少的業務欄位
**影響表**: `knowledge_base`

新增欄位:
- `business_scope`: 業務範圍 (external/internal/both)
- `video_url`: 影片連結
- `category`: 知識分類

---

### 10. rename_chat_history_user_role_to_target_user.sql
**建立日期**: 2026-01
**功能**: 重新命名欄位以符合新的命名規範
**影響表**: `chat_history`

```sql
ALTER TABLE chat_history
RENAME COLUMN user_role TO target_user;
```

---

### 11. remove_form_intro_2026-01-13.sql ⭐ 最新
**建立日期**: 2026-01-13
**功能**: 移除 forms 表的 form_intro 欄位，統一使用 default_intro
**影響表**: `forms`

```sql
-- 資料遷移
UPDATE forms
SET default_intro = COALESCE(form_intro, default_intro)
WHERE form_intro IS NOT NULL;

-- 移除欄位
ALTER TABLE forms DROP COLUMN IF EXISTS form_intro;
```

**相關 Commits**:
- `781a7c0`: feat: 移除 form_intro 欄位，統一使用表單 default_intro
- `2a509a9`: fix: 移除 knowledge-admin 後端對 form_intro 的引用
- `5501929`: fix: 移除 rag-orchestrator 所有對 form_intro 的引用

---

## 執行順序

Migration 按照檔案名稱字母順序自動執行：

```
1. add_admins_table.sql
2. add_form_schema_description_fields.sql
3. add_form_sessions_trigger_fields.sql
4. add_form_submission_status.sql
5. add_intent_embedding.sql
6. add_knowledge_base_missing_columns.sql
7. add_permission_system.sql
8. create_form_tables.sql
9. remove_form_intro_2026-01-13.sql
10. rename_chat_history_user_role_to_target_user.sql
11. verify_form_tables.sql
```

---

## 使用說明

### 查看已執行的 Migration

```bash
# 連線到 PostgreSQL
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin

# 查詢已執行的 migration
SELECT * FROM schema_migrations ORDER BY id;
```

### 手動執行 Migration

如果需要手動執行特定 migration:

```bash
# 複製 SQL 檔案到容器
docker cp database/migrations/your_migration.sql aichatbot-postgres:/tmp/

# 執行 migration
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin -f /tmp/your_migration.sql
```

### 新增 Migration

1. **建立新檔案**:
   ```bash
   touch database/migrations/your_new_migration_$(date +%Y-%m-%d).sql
   ```

2. **編寫 SQL**:
   - 使用 `IF NOT EXISTS` 避免重複建立
   - 包含回滾指令（註解）
   - 新增註釋說明變更目的

3. **測試**:
   ```bash
   # 在開發環境測試
   docker-compose down
   docker-compose up -d
   ```

4. **記錄**:
   - 更新本 README
   - 更新 `docs/database/DATABASE_SCHEMA.md`

---

## 回滾策略

### 方法一：使用備份恢復

```bash
# 備份當前資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_before_migration.sql

# 執行 migration
docker-compose restart postgres

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

---

## 常見問題

### Q: Migration 執行失敗怎麼辦？

**A**:
1. 查看 Docker 日誌: `docker-compose logs postgres`
2. 檢查語法錯誤
3. 確認表/欄位不存在
4. 使用備份回滾

### Q: 如何跳過特定 Migration？

**A**:
不建議跳過 migration。如果必須，可以：
1. 暫時移除該檔案
2. 手動在 `schema_migrations` 表中標記為已執行

### Q: 多個開發者同時新增 Migration 怎麼辦？

**A**:
使用日期時間命名，例如:
- `add_feature_a_2026-01-13-10-30.sql`
- `add_feature_b_2026-01-13-11-45.sql`

---

## 相關文件

- [資料庫架構文件](../../docs/database/DATABASE_SCHEMA.md)
- [系統架構文件](../../docs/architecture/SYSTEM_ARCHITECTURE.md)
- [部署指南](../../docs/guides/QUICKSTART.md)

---

**維護者**: Claude Code
**最後更新**: 2026-01-14
**下次檢查**: 每次新增 migration 時更新
