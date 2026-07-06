-- ============================================================
-- 盤查 2026-07-06 資料修正（jgb-knowledge-audit-20260706）
-- ①錯誤知識修正 5 筆（週期單位錯／重試3次杜撰）——embedding 基於 question_summary，answer 修正不動向量
-- ②3367 表單錨點死路 → 直答排查指引
-- ③發票時點知識退出 per-bill API 面向分類
-- ④重複列停用
-- ⑤金標改判（手動到帳 4 題 form_fill→conversational）
-- 冪等；新知識 INSERT 另由 import 工具處理（scripts/audit/reports/*-import.json，需 embedding）
-- ============================================================

-- 3399: 週期單位錯誤：實際為 6 種月計選項，非 7 種週計
UPDATE knowledge_base SET answer='週期帳單在建立合約時設定，系統依合約期間自動產生各期帳單。繳費週期共 6 種選項：每月、每 2 個月、每 3 個月、每 4 個月、每 6 個月、每年；並可設定每期的約定繳費日（每月 1～31 日擇一）。帳單到期日依合約的週期與約定日自動計算，系統每日排程檢查並產生新一期帳單。另外，為避免租客首筆帳單一建立就逾期，超過繳費期限的「首月帳單」系統會自動增加 5 天繳費寬限期。', updated_at=NOW() WHERE id=3399;

-- 3391: 刪除查無依據的「最多重試 3 次」；改為實際行為（失敗即通知）
UPDATE knowledge_base SET answer='信用卡自動扣款功能讓系統在帳單到期時自動從租客的信用卡扣款，無需手動操作。設定方式：在合約設定中開啟信用卡自動扣款功能，租客需完成首次信用卡授權。授權完成後，系統在帳單產生後按設定時間自動扣款。若扣款失敗（如卡片過期、額度不足），系統會立即通知租客，租客需進入帳單頁面改用其他付款方式完成繳費，或更新信用卡授權後等待下期自動扣款。信用卡授權即將到期時系統也會提前通知。', updated_at=NOW() WHERE id=3391;

-- 3409: 刪除「最多允許重試 3 次」句
UPDATE knowledge_base SET answer='信用卡繳費流程：租客在帳單頁面選擇信用卡付款後，系統導向金流商的安全付款頁面，輸入卡號完成交易。付款成功後系統即時收到通知，帳單狀態更新為「待對帳」，金流商確認後變為「已到帳」。信用卡付款的優點是即時確認，無需等待入帳。若付款失敗，租客可重新發起付款或改用其他已啟用的付款方式。', updated_at=NOW() WHERE id=3409;

-- 3412: 刪除「最多允許重試 3 次」句
UPDATE knowledge_base SET answer='付款共有 4 種主要狀態：（1）付款中：已建立付款訂單，等待租客完成付款操作；（2）付款成功：金流商確認款項已收到，帳單自動更新；（3）付款失敗：交易未完成，可能原因包含卡片額度不足、帳號錯誤等，租客可重新發起付款或改用其他付款方式；（4）取消付款：付款訂單已被取消。付款顯示「處理中」通常表示金流商正在確認入帳。', updated_at=NOW() WHERE id=3412;

-- 3415: 刪除「最多重試 3 次」句；對齊實際失敗處理
UPDATE knowledge_base SET answer='信用卡自動扣款失敗的常見原因：（1）信用卡過期或已掛失；（2）信用卡額度不足；（3）發卡銀行拒絕交易；（4）卡號或安全碼資訊有誤。系統在自動扣款失敗後會立即通知租客。處理方式：租客需進入帳單頁面手動選擇其他付款方式完成繳費，或更新信用卡授權資訊後等待下期自動扣款。信用卡授權即將到期時，系統也會提前發送通知提醒更新。', updated_at=NOW() WHERE id=3415;

-- ②3367 → 直答排查
UPDATE knowledge_base SET
  answer='租客反應沒收到通知時，依序排查：（1）帳號綁定：系統通知（通知中心、Email）需要租客已註冊並綁定帳號——租客尚未綁定時多數通知收不到，可用「租客資訊查詢」確認該租客的註冊與綁定狀態；（2）Email 正確性：確認合約上的租客 Email 填寫正確，並請租客檢查垃圾郵件匣；（3）請租客登入系統查看「通知中心」，站內通知不受信箱影響；（4）簡訊並非一般通知管道（僅特定專案使用），沒收到簡訊屬正常。以上都正常仍收不到，請聯繫客服查通知發送紀錄。',
  form_id=NULL, action_type='direct_answer', categories=ARRAY['通知系統']
WHERE id=3367 AND form_id IS NOT NULL;

-- ③發票時點通則不進 per-bill API 面向
UPDATE knowledge_base SET categories=ARRAY['發票開立']
WHERE question_summary='發票自動開立時點 何時開發票 開立時間' AND '發票' = ANY(categories);

-- ④重複列停用（與 3367 改版同義）
UPDATE knowledge_base SET is_active=FALSE
WHERE question_summary='租客沒收到通知 通知排查 Email 綁定';

-- ⑤金標改判
UPDATE test_scenarios SET expected_action_type='conversational', expected_form_id=NULL
WHERE expected_form_id='jgb_bill_diagnosis';
