-- Migration 追蹤系統
-- 日期: 2026-01-22
-- 用途: 追蹤已執行的 migration，避免重複執行

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_by VARCHAR(100) DEFAULT 'system'
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_schema_migrations_name ON schema_migrations(migration_name);
CREATE INDEX IF NOT EXISTS idx_schema_migrations_executed_at ON schema_migrations(executed_at);

-- 註釋
COMMENT ON TABLE schema_migrations IS 'Migration 執行歷史記錄表';
COMMENT ON COLUMN schema_migrations.migration_name IS 'Migration 檔案名稱（不含 .sql）';
COMMENT ON COLUMN schema_migrations.executed_at IS 'Migration 執行時間';
COMMENT ON COLUMN schema_migrations.execution_time_ms IS 'Migration 執行耗時（毫秒）';
COMMENT ON COLUMN schema_migrations.success IS 'Migration 是否執行成功';
COMMENT ON COLUMN schema_migrations.error_message IS '如果失敗，記錄錯誤訊息';
