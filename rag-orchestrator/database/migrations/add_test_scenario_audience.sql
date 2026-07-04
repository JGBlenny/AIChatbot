-- =====================================================
-- 回測架構升級（2026-07-05）：測試情境加受眾維度
-- 根因：題庫無角色/業態欄 → 跑批單一請求形狀 → 錯形狀假陰性
-- （run290 業者題以 tenant 形狀全滅、run292 租客題以 b2b 形狀錯位——實案）。
-- request_target_user：tenant / property_manager / prospect
-- request_mode：b2c / b2b（與 target_user 對應：tenant→b2c、pm/prospect→b2b）
-- NULL＝未分類，runner 落回 env 預設形狀（向下相容）。
-- =====================================================
ALTER TABLE test_scenarios ADD COLUMN IF NOT EXISTS request_target_user varchar(30);
ALTER TABLE test_scenarios ADD COLUMN IF NOT EXISTS request_mode varchar(10);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_audience ON test_scenarios(request_target_user);
