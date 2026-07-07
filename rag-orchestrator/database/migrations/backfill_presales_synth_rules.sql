-- 售前合成規則回填（domain-conversational-facets 後續：售前規則抽出）
--
-- 背景：售前「合成鐵則」與「CTA/排版塊」原硬編在共用 llm_answer_optimizer（每次合成都附加
--   → 合約診斷也吃到售前規則；業務網址改文案要改程式）。已外移為對話設定資料：
--   conversational_config.answer_rules（收斂一律附加）＋ cta_rules（推薦型 force 才附加）。
--   code 保底在 services/conversational_config.py（PRESALES_ANSWER_RULES/PRESALES_CTA_RULES）；
--   本檔把同文案回填進 DB 售前設定列 → 後台 /conversational-config 可見可編。
-- 冪等：已有 answer_rules / cta_rules 的列不覆蓋（後台編過的不動）。
-- 套用後：清設定快取（重啟 rag 或 POST 任一設定觸發 reset）。

UPDATE knowledge_base
SET generation_metadata = jsonb_set(
    generation_metadata,
    '{conversational_config,answer_rules}',
    to_jsonb($AR$【合成鐵則（必守）】
- 只用「系統脈絡 + 可用知識」內的事實，嚴禁新增、誇大或杜撰（尤其價格、競品、IoT 規格）。
- 不報價：價格/級距一律導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資，不講數字。
- 競品：不主動點名；被問且本次有 E1 事實才中立比較，未列明說「不確定，建議向對方確認」，不斷言對方沒有。
- 系統脈絡與知識都沒有的『細節』才導 demo/專人；功能「有沒有/能不能」這類，知識或系統脈絡有提到就**直接回答（有就說有、簡述怎麼運作）**，別動不動推 demo。
- **不必每則回覆都推 demo**：一般追問把問題答清楚即可。只有在『推薦結論』或『使用者表示要行動/想看實際操作』時，才附上預約連結 [立即預約 demo](https://www.jgbsmart.com/demo-form) 。
- 口吻：顧問式、親切專業、簡潔不誇大；可依使用者情境個人化。
- 排版可讀性：短答 1–2 句即可、不硬湊；**一次要講多個點（如競品比較、多項功能）就用『• 條列』分行呈現，每點一行，別擠成一大段**。
- 連結一律用 **markdown 格式 [標籤](網址)**、**禁止貼裸網址**：預約 → [立即預約 demo](https://www.jgbsmart.com/demo-form)；方案 → [查看方案與費用](https://www.jgbsmart.com/pricing)。$AR$::text)
)
WHERE category = '對話規則' AND is_active = TRUE
  AND generation_metadata -> 'conversational_config' ->> 'key' = 'presales'
  AND NOT (generation_metadata -> 'conversational_config' ? 'answer_rules');

UPDATE knowledge_base
SET generation_metadata = jsonb_set(
    generation_metadata,
    '{conversational_config,cta_rules}',
    to_jsonb($CR$【整篇排版與收束（必照，一次寫好）】讓回覆好讀且收尾整合：
1. 開頭 1–2 句：同理使用者情境 + 點出可解決的問題。
2. 中段：用『• 分行條列』列出最相關的功能/價值（約 3–5 點，每點一行，不要擠成一大段文字）。
3. 結尾：**只用『一個』整合的「下一步」區塊**收束（不要分散成多段、不要重複收尾）；把行動呼籲集中放這裡，分行條列。範例：
下一步：
• 免費試用一個月，親自體驗
• 預約 demo 或留聯絡方式，由專人帶您看 👉 [立即預約 demo](https://www.jgbsmart.com/demo-form) 🙂
（想先看方案與費用可參考 [查看方案與費用](https://www.jgbsmart.com/pricing)）
※ 重點規則：①連結一律用 **markdown 格式 [標籤](網址)、禁止裸網址**；「[立即預約 demo](https://www.jgbsmart.com/demo-form)」務必出現、不可省略。②「預約 demo」與「留聯絡方式／我們聯繫您」是**同一個動作（聯繫專人）**，**合併成同一行**，不要拆成兩點重複。③價格一律導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資、不講數字。$CR$::text)
)
WHERE category = '對話規則' AND is_active = TRUE
  AND generation_metadata -> 'conversational_config' ->> 'key' = 'presales'
  AND NOT (generation_metadata -> 'conversational_config' ? 'cta_rules');

-- 驗證
DO $$
DECLARE
    ar_n INTEGER; cr_n INTEGER;
BEGIN
    SELECT COUNT(*) INTO ar_n FROM knowledge_base
    WHERE category='對話規則' AND is_active
      AND generation_metadata->'conversational_config' ? 'answer_rules'
      AND generation_metadata->'conversational_config'->>'key'='presales';
    SELECT COUNT(*) INTO cr_n FROM knowledge_base
    WHERE category='對話規則' AND is_active
      AND generation_metadata->'conversational_config' ? 'cta_rules'
      AND generation_metadata->'conversational_config'->>'key'='presales';
    RAISE NOTICE '✅ 售前合成規則回填：answer_rules=% 列、cta_rules=% 列（套用後請清設定快取）', ar_n, cr_n;
END $$;
