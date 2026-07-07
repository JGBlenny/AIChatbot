-- =====================================================
-- account-conversational-facets 任務 3.2：既有帳號知識補標主面向（資料，非 schema）
-- ⚠️ 套用前置條件：facet-backfill-review.md（account spec 目錄）人工確認完成；id 與清單一致。
-- 補標 7 筆：登入排障 1（3436）＋帳號綁定異動 1（3437）＋團隊成員權限 5（3439/3544-3547）。
-- 3435/3438/3440 維持單發不掛；answer 修正（3435-3439）在知識批次 updates（任務 3.3）。
-- 安全：冪等；不動 category 主欄位與 embedding；部署後 reranker 重建＋清快取。
-- =====================================================

-- 登入排障
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '登入排障'), updated_at = now()
WHERE id = 3436 AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['登入排障']::text[]);

-- 帳號綁定異動
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '帳號綁定異動'), updated_at = now()
WHERE id = 3437 AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['帳號綁定異動']::text[]);

-- 團隊成員權限
UPDATE knowledge_base SET categories = array_append(COALESCE(categories, ARRAY[]::text[]), '團隊成員權限'), updated_at = now()
WHERE id IN (3439, 3544, 3545, 3546, 3547) AND is_active
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['團隊成員權限']::text[]);

-- 驗證：計數＋新面向互斥
DO $$
DECLARE n INT; dup INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE is_active AND categories && ARRAY['註冊驗證排障','登入排障','帳號綁定異動','團隊成員權限']::text[]
      AND COALESCE(category,'') NOT IN ('對話規則','系統脈絡');
    SELECT COUNT(*) INTO dup FROM knowledge_base
    WHERE is_active AND (
        SELECT COUNT(*) FROM unnest(categories) c
        WHERE c IN ('註冊驗證排障','登入排障','帳號綁定異動','團隊成員權限')) > 1;
    RAISE NOTICE '✅ 帳號面向補標：% 筆（預期 7）；跨面向重複 % 筆（預期 0）', n, dup;
END $$;
