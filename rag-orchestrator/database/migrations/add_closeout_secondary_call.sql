-- =====================================================
-- contract-conversational-facets 任務 7.3：退租收尾 config 加 secondary_call（G3 上線後）
--
-- 為既有環境的『對話規則：退租收尾』grounding_scope 補 secondary_call 宣告：
-- 單筆收斂後查該合約帳單（{row.id} 插值）、attach 為 bills → formatter 個人化未封存清單。
-- 新裝環境由 seed_contract_facet_configs.sql（已含此宣告）建立，本檔僅補既有列。
--
-- 前置：jgb2 bills 端點已露出 is_archived/archive_ymd（G3）。
-- 套用：psql "$DATABASE_URL" -f database/migrations/add_closeout_secondary_call.sql
-- 套用後清快取（重啟或後台 /conversational-config 任一儲存）。
-- 冪等：已含 secondary_call 則不覆寫。
-- =====================================================

UPDATE knowledge_base
SET generation_metadata = jsonb_set(
        generation_metadata,
        '{conversational_config,grounding_scope,secondary_call}',
        '{"endpoint": "jgb_bills",
          "params": {"role_id": "{session.role_id}", "contract_ids": "{row.id}"},
          "list_path": "data",
          "attach_as": "bills"}'::jsonb),
    updated_at = now()
WHERE category = '對話規則'
  AND question_summary = '對話規則：退租收尾'
  AND is_active
  AND NOT (generation_metadata #> '{conversational_config,grounding_scope}' ? 'secondary_call');

DO $$
DECLARE ok BOOLEAN;
BEGIN
    SELECT generation_metadata #> '{conversational_config,grounding_scope}' ? 'secondary_call' INTO ok
    FROM knowledge_base WHERE category='對話規則' AND question_summary='對話規則：退租收尾' AND is_active
    ORDER BY id DESC LIMIT 1;
    RAISE NOTICE '✅ 退租收尾 secondary_call 宣告：%（套用後請清快取）', COALESCE(ok, FALSE);
END $$;
