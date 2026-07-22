-- =====================================================
-- migration 執行帳本(2026-07-22 兩套體系收斂,runbook §17)
--
-- 背景:conversational 系列(本目錄)自始走 runbook 手動、無執行紀錄,
--   「prod 套了沒」只能查 DB 現況回答(pending_question/search_kb_status 皆踩過)。
--   收斂裁定:沿用既有 schema_migrations 表當帳本(編號系列遺產,表結構不動),
--   目錄與執行慣例維持本目錄+runbook 逐節;編號系列(database/migrations-legacy/)
--   與 run_migrations.sh 同日除役。
-- 規則:今後 runbook 每支 migration 執行後補一行 INSERT(見 §17 範式);
--   本檔回填「7/7 全庫搬遷批」36 支(效果經 dump 進入 prod,created_by 標 backfill)。
-- 冪等:ON CONFLICT DO NOTHING。
-- =====================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_by VARCHAR(100) DEFAULT 'system'
);

INSERT INTO schema_migrations (migration_name, created_by)
VALUES
    ('split_base_system_context_extract_presales', 'backfill-20260707'),
    ('backfill_contract_knowledge_diagnosis_category', 'backfill-20260707'),
    ('seed_conversational_diagnosis_contract_rule', 'backfill-20260707'),
    ('seed_domain_contract_system_context', 'backfill-20260707'),
    ('add_contract_facet_categories', 'backfill-20260707'),
    ('backfill_presales_synth_rules', 'backfill-20260707'),
    ('seed_contract_entry_anchor_colloquial', 'backfill-20260707'),
    ('add_contract_facet_categories_v2', 'backfill-20260707'),
    ('seed_contract_facet_system_context', 'backfill-20260707'),
    ('seed_contract_facet_configs', 'backfill-20260707'),
    ('add_closeout_secondary_call', 'backfill-20260707'),
    ('update_closeout_archive_answer_rule', 'backfill-20260707'),
    ('backfill_contract_knowledge_facet_categories', 'backfill-20260707'),
    ('add_billing_facet_categories', 'backfill-20260707'),
    ('seed_billing_facet_system_context', 'backfill-20260707'),
    ('seed_billing_facet_configs', 'backfill-20260707'),
    ('backfill_billing_knowledge_facet_categories', 'backfill-20260707'),
    ('add_account_facet_categories', 'backfill-20260707'),
    ('seed_account_facet_system_context', 'backfill-20260707'),
    ('seed_account_facet_configs', 'backfill-20260707'),
    ('backfill_account_knowledge_facet_categories', 'backfill-20260707'),
    ('add_iot_facet_categories', 'backfill-20260707'),
    ('seed_iot_facet_system_context', 'backfill-20260707'),
    ('seed_iot_facet_configs', 'backfill-20260707'),
    ('backfill_iot_knowledge_facet_categories', 'backfill-20260707'),
    ('add_estate_facet_categories', 'backfill-20260707'),
    ('seed_estate_facet_system_context', 'backfill-20260707'),
    ('seed_estate_facet_configs', 'backfill-20260707'),
    ('backfill_estate_knowledge_facet_categories', 'backfill-20260707'),
    ('add_test_scenario_audience', 'backfill-20260707'),
    ('backfill_test_scenario_audience', 'backfill-20260707'),
    ('add_test_scenario_gold_checks', 'backfill-20260707'),
    ('seed_bill_diagnosis_facet', 'backfill-20260707'),
    ('audit_20260706_knowledge_fixes', 'backfill-20260707'),
    ('add_usage_events', 'backfill-20260707'),
    ('add_vendor_quotas', 'backfill-20260707'),
    ('20260722_schema_migrations_ledger', 'runbook')
ON CONFLICT (migration_name) DO NOTHING;

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM schema_migrations;
    RAISE NOTICE '✅ migration 帳本就緒:共 % 筆紀錄', n;
END $$;
