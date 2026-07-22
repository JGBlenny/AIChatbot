-- =====================================================
-- Migration: 建立金流追問選單範例表單 payment_gateway_followup
-- =====================================================
-- 日期: 2026-06-20
-- 功能: form-chaining（表單串接機制）任務 5.1
-- 目的: 提供一張可運作的「制式追問選單」後續表單，供 payment_gateway_select
--       完成後自動串接。單一 select 欄位 + branch_answer mapping，
--       每個選項以既有知識條目回覆，全程不經向量檢索（100% 決定性）。
-- 需求: 4.1, 4.2
-- 對應知識: 手續費誰負擔→3551；能不能綁多家→3554；怎麼換金流商→3554
--
-- 冪等：ON CONFLICT (form_id) 更新，可安全重跑。
-- =====================================================

BEGIN;

INSERT INTO form_schemas (
    form_id,
    form_name,
    vendor_id,
    is_active,
    skip_review,
    on_complete_action,
    description,
    fields,
    api_config
) VALUES (
    'payment_gateway_followup',
    '金流追問選單',
    NULL,            -- 平台通用（與 payment_gateway_select 一致）
    true,
    true,            -- call_api 型表單，跳過人工審核
    'call_api',
    '金流設定說明後的制式追問選單，依選項以 branch_answer 回覆對應知識',
    '[
        {
            "field_name": "followup_topic",
            "field_label": "追問主題",
            "field_type": "select",
            "required": true,
            "prompt": "還想了解什麼？\n1. 手續費誰負擔\n2. 能不能綁多家\n3. 怎麼換金流商",
            "options": [
                {"label": "手續費誰負擔", "value": "fee"},
                {"label": "能不能綁多家", "value": "multi"},
                {"label": "怎麼換金流商", "value": "switch"}
            ]
        }
    ]'::jsonb,
    '{
        "endpoint": "branch_answer",
        "combine_with_knowledge": false,
        "params": {
            "choice": "{form.followup_topic}",
            "mapping": {
                "fee": 3551,
                "multi": 3554,
                "switch": 3554
            },
            "fallback": "這個問題請聯繫 JGB 客服協助確認。"
        }
    }'::jsonb
)
ON CONFLICT (form_id) DO UPDATE SET
    form_name          = EXCLUDED.form_name,
    vendor_id          = EXCLUDED.vendor_id,
    is_active          = EXCLUDED.is_active,
    skip_review        = EXCLUDED.skip_review,
    on_complete_action = EXCLUDED.on_complete_action,
    description        = EXCLUDED.description,
    fields             = EXCLUDED.fields,
    api_config         = EXCLUDED.api_config,
    updated_at         = NOW();

COMMIT;

-- 驗證
DO $$
DECLARE
    cfg JSONB;
BEGIN
    SELECT api_config INTO cfg FROM form_schemas WHERE form_id = 'payment_gateway_followup';
    IF cfg IS NOT NULL
       AND cfg->>'endpoint' = 'branch_answer'
       AND (cfg->'params'->'mapping'->>'fee') = '3551'
       AND (cfg->'params'->'mapping'->>'switch') = '3554' THEN
        RAISE NOTICE '✅ payment_gateway_followup 範例表單建立成功';
    ELSE
        RAISE EXCEPTION '❌ payment_gateway_followup 建立失敗';
    END IF;
END $$;

-- =====================================================
-- 套用:
--   docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
--     database/migrations/create_payment_gateway_followup_form.sql
-- 回滾:
--   DELETE FROM form_schemas WHERE form_id = 'payment_gateway_followup';
-- =====================================================
