# Database Migrations 說明

## 狀態：已歸檔

所有 migrations 的最終結果已整合到 `database/init/` 腳本中。

## 首次部署

使用 init 腳本即可：

```bash
# 停止服務並清除舊數據
docker-compose down
docker volume rm aichatbot_postgres_data

# 啟動 postgres（會自動執行 init 腳本）
docker-compose up -d postgres
```

## Init 腳本執行順序

1. `01-enable-pgvector.sql` - 啟用 pgvector 擴展
2. `02-create-knowledge-base.sql` - 創建知識庫表（最終完整版本）
3. `03-create-rag-tables.sql` - 創建 RAG 相關表
4. `04-create-intent-management-tables.sql` - 創建意圖管理表 + 預設意圖
5. `05-create-knowledge-intent-mapping.sql` - 創建知識-意圖映射表
6. `06-vendors-and-configs.sql` - 創建業者和配置表
7. `07-extend-knowledge-base.sql` - 插入知識範例數據
8. `09-create-test-scenarios.sql` - 創建測試系統表
9. `10-create-configuration-tables.sql` - 創建配置管理表 + 預設配置
10. `11-create-sop-system.sql` - 創建 Platform SOP 系統
11. `12-create-ai-knowledge-system.sql` - 創建 AI 知識系統

## Migrations 歷史記錄

已移至：`docs/archive/migrations_history/`

這些 migrations 記錄了資料庫結構從初始版本到當前版本的演變過程（共 48 個 migration 文件）。

**重要**：這些文件僅供歷史參考，**不需要執行**。所有變更已整合到上述 init 腳本中。

## 未來資料庫結構變更

如果需要修改資料庫結構：

### 方案 A：修改 init 腳本（推薦用於新增表/欄位）

1. 直接修改對應的 `database/init/` 腳本
2. 在開發環境測試
3. 在生產環境手動執行相應的 SQL
4. 更新 init 腳本以便未來部署使用

### 方案 B：創建新的 SQL 腳本（用於複雜變更）

1. 創建 `database/fixes/` 或 `database/updates/` 目錄下的腳本
2. 在生產環境手動執行
3. 記錄執行日誌
4. 同步更新 init 腳本

## 版本記錄

| 日期 | 版本 | 說明 |
|------|------|------|
| 2025-11-03 | v1.0 | 初始部署版本 |
|  |  | - 整合所有 migrations (01-48) 的結果 |
|  |  | - 創建完整的 init 腳本集 |
|  |  | - 包含預設配置數據 |
|  |  | - 總計 25 張核心表 |

## 表結構概覽

### 核心業務表（7 張）
- knowledge_base - 知識庫主表
- knowledge_intent_mapping - 知識-意圖映射
- intents - 意圖配置
- vendors - 業者表
- vendor_configs - 業者配置參數
- conversation_logs - 對話日誌
- unclear_questions - 未釐清問題

### 配置管理表（5 張）
- business_types_config - 業態類型配置
- target_user_config - 目標用戶配置
- system_param_definitions - 系統參數定義
- business_scope_config - 業務範圍配置
- suggested_intents - 建議的意圖

### SOP 系統表（5 張）
- platform_sop_categories - Platform SOP 分類
- platform_sop_groups - Platform SOP 群組
- platform_sop_templates - Platform SOP 範本
- vendor_sop_overrides - 業者 SOP 覆寫
- platform_sop_template_intents - SOP-意圖映射

### 測試系統表（5 張）
- test_collections - 測試集合
- test_scenarios - 測試場景
- backtest_runs - 回測執行記錄
- backtest_results - 回測結果
- test_scenario_collections - 測試場景-集合關聯

### AI 與導入系統表（3 張）
- ai_generated_knowledge_candidates - AI 生成知識候選
- knowledge_import_jobs - 知識導入作業
- chat_history - 聊天歷史記錄

## 相關文檔

- [部署指南 - 方案 A](../docs/DEPLOYMENT_PLAN_A.md)
- [資料庫架構設計](../docs/DATABASE_SCHEMA.md)
- [Migrations 歷史記錄](../docs/archive/migrations_history/)

## 注意事項

1. **不要手動修改生產環境的資料庫結構**，除非經過充分測試
2. **所有結構變更都應該先更新 init 腳本**，確保未來部署的一致性
3. **重大變更前務必備份資料庫**
4. **記錄所有手動執行的 SQL**，以便追溯和回滾

---

**最後更新**：2025-11-03
**維護者**：開發團隊
