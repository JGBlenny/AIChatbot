-- =====================================================
-- 路由調校 2026-07-22：進場路由 keywords 衛生＋categories 補標＋口語錨點 4 筆
--
-- 背景：進場路由（top1 similarity ≥0.75 → categories → facet config）發現 13 案誤路由。
--   根因＝關鍵字加成塌陷：keyword 匹配是 jieba 斷詞「交集」，裸泛詞（合約/帳單/租客/
--   點退/註冊/物件/儲值）掛在哪列，任何含該詞的問句都對該列加成 ×1.1–1.3 並 cap 於
--   1.0——多列同分 1.0 後排序由插入序亂決，教學列吸走面向句、面向列吸走教學句。
--   另有 7/4 批次補入的知識（4053 等）categories 空白，top1 命中卻無面向可路由。
--
-- 手法（與 embedding 完整性鐵則相容——不動既有列 question_summary/answer，僅
--   keywords/categories；keywords 不參與向量，既有列免重嵌）：
--   1) keywords 衛生：修剪裸泛詞，只留該列專屬語彙；
--   2) categories 補標：4053 儲值教學 → IoT設定引導（iot spec 教學收斂裁定）；
--   3) 口語錨點 4 筆（一種講法一筆，同 seed_contract_entry_anchor_colloquial 慣例）。
--
-- 驗收：test_facet_entry_routing_req.py 83 案全綠（dev 2026-07-22 實跑）。
-- 安全：冪等（id＋question_summary 雙重定位；錨點以 question_summary 判重）。
-- ⚠️ 新錨點 embedding 本檔不填——套用後必須重嵌這 4 筆才生效（知識後台各重存一次，
--    或跑 scripts/regenerate_all_embeddings.py 的缺嵌補算）；部署後 reranker 重建＋清快取
--    照 runbook 慣例。
-- =====================================================

-- ── 1) keywords 衛生（修剪裸泛詞）──
UPDATE knowledge_base SET keywords = '{簽約邀請,發送邀請,不能發送,邀請}', updated_at = now()
WHERE id = 3368 AND question_summary = '合約簽約邀請 發送邀請 為什麼不能發送';
UPDATE knowledge_base SET keywords = '{提前解約,解約,提前終止,可以解約}', updated_at = now()
WHERE id = 3370 AND question_summary = '合約提前解約 可以解約嗎 提前終止';
UPDATE knowledge_base SET keywords = '{續約,可以續約,延長}', updated_at = now()
WHERE id = 3371 AND question_summary = '合約續約 可以續約嗎 延長合約';
UPDATE knowledge_base SET keywords = '{合約狀態,狀態查詢}', updated_at = now()
WHERE id = 3372 AND question_summary = '合約狀態查詢 目前狀態';
UPDATE knowledge_base SET keywords = '{合約狀態,合約階段,狀態總覽,合約流程,"12 種狀態"}', updated_at = now()
WHERE id = 3373 AND question_summary = '合約狀態 12 階段總覽';
UPDATE knowledge_base SET keywords = '{已出租,刊登中,租約中,洽談中}', updated_at = now()
WHERE id = 3428 AND question_summary = '物件狀態 定義條件';
UPDATE knowledge_base SET keywords = '{建立帳號,新帳號,開戶,第一次使用,怎麼開始}', updated_at = now()
WHERE id = 3435 AND question_summary = '註冊帳號 建立流程';
UPDATE knowledge_base SET keywords = '{設備離線,電表,"IoT 問題",無法連線,設備異常,電表離線}', updated_at = now()
WHERE id = 3461 AND question_summary = 'IoT 設備無法連線 排查';
UPDATE knowledge_base SET keywords = '{名單,新增,編輯}', updated_at = now()
WHERE id = 3475 AND question_summary = '租客名單 新增編輯管理';
UPDATE knowledge_base SET keywords = '{發不出,無法發送,發送失敗,寄不出,金額不能為空}', updated_at = now()
WHERE id = 3495 AND question_summary = '帳單為什麼發不出去';
UPDATE knowledge_base SET keywords = '{不用簽名,續約簽名,未綁定續約,免簽名}', updated_at = now()
WHERE id = 3529 AND question_summary = '免註冊租客續約 不需電子簽名';
UPDATE knowledge_base SET keywords = '{生效,還沒生效,生效了沒}', updated_at = now()
WHERE id = 3814 AND question_summary = '合約怎麼還沒生效 生效了沒';
UPDATE knowledge_base SET keywords = '{卡住,沒動靜,卡在哪}', updated_at = now()
WHERE id = 3815 AND question_summary = '合約卡在哪 卡住了 簽了沒動靜';
UPDATE knowledge_base SET keywords = '{時間窗,到期前30天}', updated_at = now()
WHERE id = 3848 AND question_summary = '點退時間窗 到期前30天起';
UPDATE knowledge_base SET keywords = '{繳了,沒進來,入帳,儲值入帳}', updated_at = now()
WHERE id = 3931 AND question_summary = '租客說繳了 錢還沒進來';
UPDATE knowledge_base SET keywords = '{教學,操作步驟}', updated_at = now()
WHERE id = 4053 AND question_summary = '租客儲值教學 操作步驟';
UPDATE knowledge_base SET keywords = '{刪除物件,物件刪除}', updated_at = now()
WHERE id = 4144 AND question_summary = '物件刪除 條件 歷史合約會消失嗎';
UPDATE knowledge_base SET keywords = '{招租店舖,對外首頁,分享,怎麼進去,入口}', updated_at = now()
WHERE id = 4146 AND question_summary = '招租店舖 房東對外首頁 入口 分享';
UPDATE knowledge_base SET keywords = '{快速篩選,押金狀態}', updated_at = now()
WHERE id = 4149 AND question_summary = '點交 點退 押金狀態 物件快速篩選';
UPDATE knowledge_base SET keywords = '{退房,換租客,重開物件}', updated_at = now()
WHERE id = 4216 AND question_summary = '退房後換新租客 點退押金 物件要重開嗎';

-- ── 2) categories 補標（iot spec「教學收斂進設定引導」裁定）──
UPDATE knowledge_base SET categories = '{IoT設定引導}', updated_at = now()
WHERE id = 4053 AND question_summary = '租客儲值教學 操作步驟'
  AND NOT (COALESCE(categories, ARRAY[]::text[]) @> ARRAY['IoT設定引導']::text[]);

-- ── 3) 口語錨點 4 筆（冪等；⚠️ 套用後需重嵌）──
INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '註冊名字跟證件不符 要怎麼改資料', '', ARRAY['註冊驗證排障']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['證件不符','名字不一樣','改資料']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '註冊名字跟證件不符 要怎麼改資料');

INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '想改合約租期 租金要調整', '', ARRAY['合約異動']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['改租期','調租金','改合約']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '想改合約租期 租金要調整');

INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '合約狀態怪怪的 不太對勁', '', ARRAY['狀態判斷']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['怪怪的','不對勁']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '合約狀態怪怪的 不太對勁');

INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types,
                            keywords, is_active, source)
SELECT '租客儲值了電還是沒有來 沒復電', '', ARRAY['電表排障']::text[],
       ARRAY['property_manager','tenant']::text[], ARRAY['system_provider']::text[],
       ARRAY['沒復電','未復電']::text[], TRUE, 'manual'
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base WHERE question_summary = '租客儲值了電還是沒有來 沒復電');

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE question_summary IN ('註冊名字跟證件不符 要怎麼改資料','想改合約租期 租金要調整',
                               '合約狀態怪怪的 不太對勁','租客儲值了電還是沒有來 沒復電')
      AND is_active;
    RAISE NOTICE '✅ 路由調校錨點：% 筆（記得重嵌這 4 筆 embedding 才會生效）', n;
END $$;
