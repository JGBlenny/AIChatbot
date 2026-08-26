-- 回滾 seed_responsibility_delegates_v1（兩段各自可獨立回退；冪等）
BEGIN;

UPDATE knowledge_base
SET generation_metadata = generation_metadata #- '{conversational_config,responsibility}'
WHERE category = '對話規則'
  AND generation_metadata->'conversational_config'->>'key' IN ('bill_diagnosis', 'billing_anomaly');

UPDATE knowledge_base
SET answer = regexp_replace(
        regexp_replace(answer, ',"delegate_facet_key":"…（見下）"', '', 'g'),
        chr(10) || '【delegate_facet_key 規則】[^\n]*', '', 'g')
WHERE category = '對話規則'
  AND generation_metadata->'conversational_config'->>'key' IN ('bill_diagnosis', 'billing_anomaly')
  AND answer LIKE '%delegate_facet_key%';

COMMIT;

-- DELETE FROM schema_migrations WHERE migration_name = 'seed_responsibility_delegates_v1';
