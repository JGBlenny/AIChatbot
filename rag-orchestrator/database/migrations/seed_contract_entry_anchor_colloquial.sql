-- 合約診斷「進場錨點」口語補強（domain-conversational-facets 後續：召回補強）
--
-- 背景：進診斷靠第一句與「狀態判斷」知識的向量相似度（≥0.65）。原錨點只有書面語
--   （「合約狀態查詢 目前狀態」），含「合約」二字的口語（「這份合約怎麼還沒生效」0.585、
--   「我的合約卡在哪」0.523）進不了場。
-- 教訓（實測）：把多種口語塞進同一筆 keywords 會**稀釋向量**（回歸句 0.785→0.684、
--   口語也沒救起來）→ 正解＝**一種講法一筆錨點**（各自專屬向量）。
-- 驗收（2026-07-02，含 reranker 全鏈路）：
--   正向：這份合約怎麼還沒生效 0.831／幫我看85100這份合約怎麼還沒生效 0.684／
--         我的合約卡在哪 0.685／合約簽了怎麼都沒動靜 0.738 → 全進診斷
--   回歸：我想查合約狀態 0.785 不變
--   反向：無「合約」模糊句 0.585 仍擋；發票/帳單/招租句不誤入
-- 冪等：以 question_summary 識別，已存在不重插。
-- ⚠️ embedding 欄位本檔不填——套用後需重算向量才會生效：
--    到知識管理後台把這兩筆各重存一次（存檔自動算），或跑既有重嵌工具。

INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '合約怎麼還沒生效 生效了沒', '', ARRAY['狀態判斷']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['合約','生效','還沒生效']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '合約怎麼還沒生效 生效了沒');

INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '合約卡在哪 卡住了 簽了沒動靜', '', ARRAY['狀態判斷']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['合約','卡住','沒動靜']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '合約卡在哪 卡住了 簽了沒動靜');

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE question_summary IN ('合約怎麼還沒生效 生效了沒','合約卡在哪 卡住了 簽了沒動靜') AND is_active;
    RAISE NOTICE '✅ 合約進場口語錨點：% 筆（記得重算這兩筆的 embedding 才會生效）', n;
END $$;
