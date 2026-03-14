-- ============================================================================
-- 修復 API Endpoint 知識庫同步 Trigger
-- ============================================================================
-- 目的：擴展 Trigger 以支援兩種知識庫引用方式：
--   1. 通過 form_id → form_schemas.api_config->>'endpoint'（方式 A）
--   2. 直接在 knowledge_base.api_config->>'endpoint'（方式 B）
--
-- 日期：2026-03-13
-- ============================================================================

-- 刪除舊的 Trigger 和 Function
DROP TRIGGER IF EXISTS trigger_sync_api_endpoint_kb_ids ON knowledge_base;
DROP FUNCTION IF EXISTS sync_api_endpoint_kb_ids();

-- 創建改進的 Trigger Function
CREATE OR REPLACE FUNCTION sync_api_endpoint_kb_ids()
RETURNS TRIGGER AS $$
DECLARE
  affected_endpoint_ids TEXT[];
  old_endpoint_ids TEXT[];
  new_endpoint_ids TEXT[];
BEGIN
  -- ========================================
  -- 處理 DELETE 操作
  -- ========================================
  IF (TG_OP = 'DELETE') THEN
    -- 方式 A：通過 form_id 引用的 endpoints
    IF OLD.form_id IS NOT NULL THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO old_endpoint_ids
      FROM form_schemas
      WHERE form_id = OLD.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    -- 方式 B：直接在 api_config 引用的 endpoint
    IF OLD.api_config IS NOT NULL AND OLD.api_config->>'endpoint' IS NOT NULL THEN
      old_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(old_endpoint_ids, '{}') || ARRAY[OLD.api_config->>'endpoint']
        )
      );
    END IF;

    affected_endpoint_ids := old_endpoint_ids;

  -- ========================================
  -- 處理 UPDATE 操作
  -- ========================================
  ELSIF (TG_OP = 'UPDATE') THEN
    -- 方式 A：form_id 改變時，需要更新舊的和新的 endpoints
    IF OLD.form_id IS NOT NULL AND OLD.form_id != COALESCE(NEW.form_id, '') THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO old_endpoint_ids
      FROM form_schemas
      WHERE form_id = OLD.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    IF NEW.form_id IS NOT NULL THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO new_endpoint_ids
      FROM form_schemas
      WHERE form_id = NEW.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    -- 方式 B：api_config 中的 endpoint 改變時
    IF OLD.api_config IS NOT NULL AND OLD.api_config->>'endpoint' IS NOT NULL THEN
      old_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(old_endpoint_ids, '{}') || ARRAY[OLD.api_config->>'endpoint']
        )
      );
    END IF;

    IF NEW.api_config IS NOT NULL AND NEW.api_config->>'endpoint' IS NOT NULL THEN
      new_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(new_endpoint_ids, '{}') || ARRAY[NEW.api_config->>'endpoint']
        )
      );
    END IF;

    -- 合併所有受影響的 endpoints
    affected_endpoint_ids := ARRAY(
      SELECT DISTINCT unnest(COALESCE(old_endpoint_ids, '{}') || COALESCE(new_endpoint_ids, '{}'))
    );

  -- ========================================
  -- 處理 INSERT 操作
  -- ========================================
  ELSE
    -- 方式 A：通過 form_id 引用的 endpoints
    IF NEW.form_id IS NOT NULL THEN
      SELECT ARRAY_AGG(DISTINCT api_config->>'endpoint')
      INTO new_endpoint_ids
      FROM form_schemas
      WHERE form_id = NEW.form_id
        AND api_config->>'endpoint' IS NOT NULL;
    END IF;

    -- 方式 B：直接在 api_config 引用的 endpoint
    IF NEW.api_config IS NOT NULL AND NEW.api_config->>'endpoint' IS NOT NULL THEN
      new_endpoint_ids := ARRAY(
        SELECT DISTINCT unnest(
          COALESCE(new_endpoint_ids, '{}') || ARRAY[NEW.api_config->>'endpoint']
        )
      );
    END IF;

    affected_endpoint_ids := new_endpoint_ids;
  END IF;

  -- ========================================
  -- 更新所有受影響的 API endpoints
  -- ========================================
  IF affected_endpoint_ids IS NOT NULL AND array_length(affected_endpoint_ids, 1) > 0 THEN
    FOR i IN 1..array_length(affected_endpoint_ids, 1) LOOP
      UPDATE api_endpoints
      SET related_kb_ids = (
        SELECT ARRAY_AGG(DISTINCT kb.id ORDER BY kb.id)
        FROM knowledge_base kb
        LEFT JOIN form_schemas fs ON kb.form_id = fs.form_id
        WHERE (
          -- 方式 A：通過 form_id 關聯
          (fs.api_config->>'endpoint' = affected_endpoint_ids[i])
          OR
          -- 方式 B：直接在 api_config 關聯
          (kb.api_config->>'endpoint' = affected_endpoint_ids[i])
        )
      )
      WHERE endpoint_id = affected_endpoint_ids[i];
    END LOOP;
  END IF;

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 重新創建 Trigger
CREATE TRIGGER trigger_sync_api_endpoint_kb_ids
AFTER INSERT OR UPDATE OR DELETE ON knowledge_base
FOR EACH ROW
EXECUTE FUNCTION sync_api_endpoint_kb_ids();

-- ============================================================================
-- 數據清理：重新計算所有 API endpoints 的 related_kb_ids
-- ============================================================================
UPDATE api_endpoints
SET related_kb_ids = (
  SELECT ARRAY_AGG(DISTINCT kb.id ORDER BY kb.id)
  FROM knowledge_base kb
  LEFT JOIN form_schemas fs ON kb.form_id = fs.form_id
  WHERE (
    -- 方式 A：通過 form_id 關聯
    (fs.api_config->>'endpoint' = api_endpoints.endpoint_id)
    OR
    -- 方式 B：直接在 api_config 關聯
    (kb.api_config->>'endpoint' = api_endpoints.endpoint_id)
  )
)
WHERE endpoint_id LIKE 'lookup%';

-- ============================================================================
-- 驗證結果
-- ============================================================================
SELECT
  ae.endpoint_id,
  ae.endpoint_name,
  ae.related_kb_ids,
  array_length(ae.related_kb_ids, 1) as kb_count
FROM api_endpoints ae
WHERE ae.endpoint_id LIKE 'lookup%'
ORDER BY ae.endpoint_id;
