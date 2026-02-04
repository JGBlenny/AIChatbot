-- =====================================================
-- 業者 2 電費寄送區間資料 (247 筆)
-- 不依賴業者 1，獨立部署
-- 從本地資料庫匯出: 2026-02-04
-- =====================================================

BEGIN;

INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路3段158號一樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05120026123"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁義街269號', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05293047010"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民族西路338號5樓之7', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00207994502"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市蘆洲區中央路20巷11號', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "05210366160"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市蘆洲區中央路20巷11號1樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "05210366104"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區景平路666號2樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "01441125209"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區雙連街1巷15號四樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00177770404"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區遼寧街160號', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00367702108"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區遼寧街160號之2', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00367703109"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區武成街80巷29號', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00704700204"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區信義西路25號', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "05040755104"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區大明街25巷2弄22號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01185908407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488124"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路2段5.7號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00017664305"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區民生路三段200號一樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01024875101"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區忠孝路48巷4弄8號一樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01190293108"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區忠孝路48巷4弄8號二.三.四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01190293200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區忠孝路132巷8號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01207430102"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區忠孝路132巷8號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01207430204"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區民生路三段200號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01024875203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區民生路三段200號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01024875305"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區民生路三段200號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01024875407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區館前西路213巷6號', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "01122743018"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區館前西路213巷6號1.2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01122743109"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區館前西路213巷6號3.4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01122743303"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區館前西路213巷6號5樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01122743508"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區裕民街55號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01093430200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區長江路1段156巷9弄19號之1二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01092565201"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區大明街25巷2弄22.24號公設', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01185907008"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區和平街186號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01462156109"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區中和街60巷13號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05400942400"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '桃園市龜山區龍華街3巷12號4+5樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05468905408"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路3段158號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05120026225"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路3段158號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05120026327"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路3段158號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05120026429"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路一段109號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05098260302"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路一段109號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05098260404"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路一段111號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05098261303"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重陽路一段111號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05098261405"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁義街167巷45之1號四樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05241048421"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區長元西街1號二樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05040835202"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487123"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487145"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號5樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487167"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號6樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487189"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號7樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號8樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487225"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號9樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487247"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號10樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487269"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號11樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487281"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號13樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487327"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號14樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487349"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路500號15樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545487361"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號5樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488168"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號6樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488180"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號7樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488204"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號8樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488226"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號9樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488248"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號10樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488260"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號11樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488282"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號13樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488328"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號14樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488340"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號15樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488362"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁義街269號二樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05293047203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁義街269號三樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05293047305"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁義街269號四樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05293047407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁義街269號五樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05293047500"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷17號一樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254679104"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷17號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254679206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷17號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254679308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷17號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254679400"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷17號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254679503"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷19號一樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254680107"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷19號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254680209"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷19號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254680301"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷19號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254680403"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區仁政街86巷19號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05254680506"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區重新路四段23號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05097906300"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區信義西路25號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05040755206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區自強路2段21巷13號一樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05121559108"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區自強路2段21巷13號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05121559200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區自強路2段21巷13號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05121559302"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區自強路2段21巷13號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05121559404"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路143號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05010007229"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路143號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05010007309"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓之15', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05050217283"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓之16', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05050217261"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓之18', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05050217227"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓之22', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05050217147"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓之23', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05050217125"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓之24', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05050217103"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "05050218217"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區六張街126巷23弄33號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05055780403"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號公設', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923009"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號B1', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923087"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923305"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號5樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923500"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號6樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923602"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集勇街96號7樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05297923704"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集美街2號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05080603308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區五谷王北街20巷15弄13號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05323715105"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區中山路二段312巷7號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01418652200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市蘆洲區中正路140號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05212192507"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市蘆洲區中央路20巷11號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05210366206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市蘆洲區中央路20巷11號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05210366308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市蘆洲區中央路20巷11號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05210366400"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區仁愛路141巷30弄20號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01312491507"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區中正路274號公設', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01380165004"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區中正路274號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01380165106"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區中正路274號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01380165300"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區中正路274號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01380165402"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區中正路274.276號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01380163206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區中正路276號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01380163308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市永和區中正路276號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01380163400"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區員山路294巷1號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01422356403"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區泰和街38巷27號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01440854404"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區景平路666號地下一樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01441125027"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區景平路666號2樓-1', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01441133209"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區景平路666號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01441125301"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區景平路666號3樓-1', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "01441133301"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市文山區木新路3段345號2樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "01675034206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市文山區木新路3段345號3樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "01675034308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市松山區民生東路五段138巷3號2樓之7', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00302282205"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市松山區民生東路五段138巷3號4樓之7', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00302282409"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市松山區饒河街181號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00491162209"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市松山區饒河街181號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00491162301"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市松山區饒河街181號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00491162403"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區昆明街28巷8號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00145636209"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西園路二段283號一樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00694600108"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西園路二段283號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00694600211"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西園路二段283號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00694600302"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西園路二段283號四樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00694600404"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西昌街202號之1', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00663691205"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西昌街202號之2', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00663691307"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區雙園街28.30號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00683355200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區雙園街55號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00682673407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區武成街5號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00706940209"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區武成街80巷31號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00704696106"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區汀洲路一段140巷44號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00590164100"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區汀洲路一段140巷44號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00590164202"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區三元街184號二樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00762550205"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區三元街184號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00762550307"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區三元街184號四樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00762550409"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區漢口街1段42號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00060642308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區漢口街1段42號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00060642400"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區漢口街1段42號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00060642503"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區漢口街1段42號六樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00060642605"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區中華路二段45號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076102207"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區中華路二段45號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076102309"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區中華路二段45號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076102401"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區中華路二段45號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076102504"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中華路二段５３號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076106201"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中華路二段５３號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076106303"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中華路二段５３號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076106405"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中華路二段５３號五樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00076106508"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中正區中華路二段75巷6號5樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00076300504"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區萬全街40巷12號二樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00177967207"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區寧夏路23號之1', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00017214117"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區平陽街46號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00017227203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區長安西路78巷4弄6號之4三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00021061304"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民生西路326號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00131227204"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民生西路326號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00131227306"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民生西路326號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00131227408"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民生西路326號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00131227501"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民生西路45巷7弄16號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00122865208"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區延平北路四段282巷11號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00219397207"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區延平北路258號2-10樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00164304218"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區延平北路2段210巷5號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00164768208"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區延平北路2段210巷5號', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00164768106"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路3段137巷25號公設', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00242091002"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路3段137巷25號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00242091206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路3段137巷25號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00242091308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路3段137巷25號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00242091400"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路3段137巷25號五樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00242091503"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區南京西路340號二樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00138590200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區南京西路340號三樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00138590302"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區南京西路340號四樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00138590404"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路2段5.7號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00017667400"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路2段5號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00017667308"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路2段5號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00017667206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路2段7號四樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00017664407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區興城街51號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00176717202"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區興城街51號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00176717304"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區興城街51號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00176717406"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區士東路43號5樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16030248500"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區福國路71號3樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16052300306"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區福國路71號4樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16052300408"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區忠誠路2段140巷15弄17號', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16031880100"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區建國北路2段22號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00421683202"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區中山北路一段135巷37號之1二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00484143200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區中山北路一段135巷37號之1三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00484143302"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區中山北路一段105巷23號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00484392202"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區中山北路六段768號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16030591200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區中山北路六段768巷三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16030591302"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區中山北路六段768巷四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16030591404"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區天玉街15號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16041009309"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區天玉街15號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16041009401"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區天玉街15號五樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16041009504"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區天玉街15號六七樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16041009606"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市士林區天玉街15號公設', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16041009003"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區民生東路一段29號11樓11樓之1', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00296709945"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區民生東路一段29號12樓12樓之1', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00296709967"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區遼寧街160號二樓部分', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00367702222"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區遼寧街160號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00367702200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區遼寧街160號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00367702302"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區民權東路二段117號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00344616206"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區吉林路488號2樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00038780208"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市北投區自強街37號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16066884200"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市北投區中和街273號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "16725177203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市泰順街54巷21號之7四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817548402"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區師大路86巷1號4樓', '單月', '{"note": "您的電費帳單將於每【單月】寄送。", "electric_number": "00817261407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區樂利路45巷5號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00894942207"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區泰順街54巷25號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817543203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區泰順街54巷23號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817545307"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區泰順街54巷25號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817543305"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區泰順街54巷23號三樓之1', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817545329"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區泰順街54巷23號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817545409"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市板橋區民生路三段319號24樓之2', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "01098423202"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區新北大道七段312號10樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "05463958640"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市新莊區富貴路502號1樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05545488102"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區正義北路6號之1九樓之17', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05050217249"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區長元街98巷33號之1一樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "05045668109"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市三重區集美街4號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "05080602307"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '新北市中和區景平路666號1樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "01441125107"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西昌街202號之3', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00663691409"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區環河南路一段71號10樓之26', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00092236928"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民生西路326號一樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00131227102"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區重慶北路2段5.7號二樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00017664203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民族西路338號4樓之7', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00207994409"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民族西路338號4樓之8', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00207996401"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民族西路338號5樓之8', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00207996504"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大同區民族西路338號13樓之6', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00207992986"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區建國北路2段22號三樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00421683304"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市松山區復興南路一段47巷9弄9號', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00541436105"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區西園路二段372巷23弄10號2樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00688605203"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市萬華區和平西路3段298巷5號2樓之5', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00675825202"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市北投區溫泉路71號7樓之18', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "16707103707(租客自繳)"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市北投區溫泉路71號7樓之20', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "16707104708(租客自繳)"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市北投區自強街37號', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "16066884108(租客自繳)"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市信義區忠孝東路4段553巷48號五樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00441307505"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區泰順街54巷25號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817543407"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區泰順街54巷23號四樓之1', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00817545421"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市大安區敦化南路二段81巷53號四樓', '雙月', '{"note": "您的電費帳單將於每【雙月】寄送。", "electric_number": "00890743446"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區遼寧街160號一樓', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00367700106"}', true, NOW())
ON CONFLICT DO NOTHING;
INSERT INTO lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active, created_at)
VALUES (2, 'billing_interval', '電費寄送區間', '台北市中山區遼寧街201巷2號', '自繳', '{"note": "此物件採用自行繳費方式，請直接向台電繳納電費。", "electric_number": "00425762207"}', true, NOW())
ON CONFLICT DO NOTHING;

COMMIT;

-- 總計: 247 筆資料（業者 2 - 信義包租代管）
