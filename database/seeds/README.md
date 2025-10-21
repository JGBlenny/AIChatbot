# Database Seeds

此目錄包含資料庫種子數據和測試 SQL 文件。

## 文件說明

### SOP 相關
- `add_pet_policy_sop.sql` - 添加寵物政策 SOP
- `sop_templates.sql` - SOP 範本數據
- `test_sop_insert.sql` - SOP 插入測試

## 使用方式

```bash
# 執行種子文件
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin < database/seeds/sop_templates.sql

# 或使用 psql
psql -h localhost -U aichatbot -d aichatbot_admin -f database/seeds/add_pet_policy_sop.sql
```

## 注意事項

- 這些文件僅用於開發和測試環境
- 生產環境請使用 `/database/migrations/` 中的遷移文件
- 執行前請備份資料庫
