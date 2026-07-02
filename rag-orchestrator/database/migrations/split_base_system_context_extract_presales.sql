-- =====================================================
-- domain-conversational-facets（後續修正）：把「售前系統脈絡」從通用 base 拆出
--
-- 背景：疊加載入（get_system_context）假設 category='系統脈絡' 且 target_user IS NULL 的列（id 3622）
--   是「共用產品底座」。實查其內容為**售前導向**（§5b 競品協定 / §6 CTA 出口 / §7 功能推薦索引），
--   導致合約等診斷領域疊加後仍吃到售前銷售脈絡（本 spec 要解的缺口 2 只被半解）。
--
-- 修正：把該列**在「## 5b」邊界切兩段**（內容保全，分隔恰為 \n\n）：
--   - base（target_user IS NULL）留「真通用」段（§1 定位 / §2 客群 / §3 模組 / §4 語氣 / §5 合規鐵則）。
--   - 售前 append（target_user=['prospect']）承接售前段（§5b/§6/§7）。
--   疊加後：售前 = base + 售前 append = **原文一字不差（不回歸）**；合約 = base + 合約 append（不含售前）。
--
-- 搭配程式：`routers/chat.py` 三處售前合成呼叫改傳領域鍵 'prospect'（拿回售前 append）。
--
-- 套用（部署作業）：
--   psql "$DATABASE_URL" -f database/migrations/split_base_system_context_extract_presales.sql
--   套用後清快取（重啟服務，或後台 /conversational-config 任一儲存）。
-- 冪等：base 已不含「## 5b」（已拆過）→ 自動略過。內容保全自檢：切分無法還原原文則中止（不動資料）。
-- =====================================================

DO $$
DECLARE
    orig text;
    base_part text;
    presales_part text;
    pos int;
BEGIN
    SELECT answer INTO orig FROM knowledge_base
    WHERE category = '系統脈絡' AND target_user IS NULL AND is_active = TRUE
    ORDER BY id DESC LIMIT 1;

    IF orig IS NULL THEN
        RAISE NOTICE '⏭️ 無通用 base 系統脈絡，略過';
        RETURN;
    END IF;

    pos := position('## 5b' IN orig);
    IF pos = 0 THEN
        RAISE NOTICE '⏭️ base 不含「## 5b」（已拆分或格式不符），略過（冪等）';
        RETURN;
    END IF;

    base_part := rtrim(substr(orig, 1, pos - 1), E' \n\r\t');  -- 去尾端空白/換行（含 \n；純 rtrim 只去空白）
    presales_part := substr(orig, pos);

    -- 內容保全自檢：base ＋ \n\n ＋ 售前 必須還原原文，否則中止（避免售前回歸）
    IF base_part || E'\n\n' || presales_part <> orig THEN
        RAISE EXCEPTION '❌ 拆分無法還原原文（分隔非 \n\n），中止以免售前回歸';
    END IF;

    -- 售前 append（target_user=prospect），冪等
    IF NOT EXISTS (
        SELECT 1 FROM knowledge_base
        WHERE category = '系統脈絡' AND target_user @> ARRAY['prospect']::text[] AND is_active = TRUE
    ) THEN
        INSERT INTO knowledge_base (question_summary, answer, category, target_user, is_active)
        VALUES ('售前系統脈絡 append（競品協定/CTA/功能索引）', presales_part, '系統脈絡',
                ARRAY['prospect']::text[], TRUE);
    END IF;

    -- base 縮為真通用（去售前段）
    UPDATE knowledge_base SET answer = base_part
    WHERE category = '系統脈絡' AND target_user IS NULL AND is_active = TRUE;

    RAISE NOTICE '✅ 已拆分：真通用 base % 字 + 售前 append % 字（售前疊加＝原文，不回歸）',
        length(base_part), length(presales_part);
END $$;

-- 驗證
DO $$
DECLARE
    base_len int;
    presales_len int;
BEGIN
    SELECT length(answer) INTO base_len FROM knowledge_base
    WHERE category = '系統脈絡' AND target_user IS NULL AND is_active = TRUE ORDER BY id DESC LIMIT 1;
    SELECT length(answer) INTO presales_len FROM knowledge_base
    WHERE category = '系統脈絡' AND target_user @> ARRAY['prospect']::text[] AND is_active = TRUE ORDER BY id DESC LIMIT 1;
    RAISE NOTICE '📊 base(真通用)=% 字；售前 append=% 字（套用後請清快取）', base_len, COALESCE(presales_len, 0);
END $$;
