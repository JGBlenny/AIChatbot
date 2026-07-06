-- ============================================================
-- quota-management：團隊月額度設定（spec quota-management 任務 1）
-- opt-in：無列/停用＝不管制（R1.2）。加值＝UPDATE quota。冪等。
-- ============================================================
CREATE TABLE IF NOT EXISTS vendor_quotas (
    vendor_id             INTEGER PRIMARY KEY,
    monthly_message_quota INTEGER NOT NULL CHECK (monthly_message_quota > 0),
    warn_threshold_pct    SMALLINT NOT NULL DEFAULT 80 CHECK (warn_threshold_pct BETWEEN 1 AND 99),
    block_on_exceed       BOOLEAN NOT NULL DEFAULT TRUE,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by            VARCHAR(50)
);
DO $$
BEGIN
    RAISE NOTICE '✅ vendor_quotas 就緒（opt-in：未設定團隊不受限）';
END $$;
