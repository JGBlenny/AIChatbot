-- =====================================================
-- iot-conversational-facets 任務 2.2：IoT 系統脈絡——母薄層＋2 子面向（資料，非 schema）
-- 內容依 research.md 主題 1/2 jgb2 ground truth 撰寫（未給電四分支、每小時同步、
-- DAE 帳號失效整批停同步、儲值 webhook 對帳、離線快照語義）。機制數字寫死、LLM 不得自創。
-- 母層自律：僅名詞對照，分支細節一律下沉子層。
-- 前置：add_iot_facet_categories.sql。套用後清快取。
-- 冪等：以 (category='系統脈絡', question_summary) 識別，已存在不重插。
-- =====================================================

-- 母『智慧設備』：名詞對照（薄層）
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：IoT領域-智慧設備(母共用)',
    $CTX$## 智慧設備名詞對照
電表分兩類：雲端電表（台科電＝系統內代號 DAE、鳴周＝Miezo，數據自動同步）與手動抄表。台科電電表支援「儲值模式」＝預付制，餘額隨用電扣抵。設備的線上/供電/度數等狀態由系統定時向廠商同步，非即時值。門鎖等其他設備屬廠商功能面，問題多需聯繫對應廠商處理。$CTX$,
    '系統脈絡', ARRAY['智慧設備']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：IoT領域-智慧設備(母共用)');

-- 子『電表排障』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：IoT領域-電表排障(子面向)',
    $CTX$## 電表問題怎麼判
系統會查這顆電表的現值並決定性判因，照系統判定作答，不臆測原因。
- 判定順序：先看是否離線——離線時所有數值都是「截至最後同步」的快照，不下供電結論；再看供電與儲值餘額。
- 儲值模式下餘額耗盡，電表端會自動斷電；**儲值入帳後電表端會自動復電**，不需另外操作。
- 供電被關閉但非餘額問題：系統沒有斷電原因紀錄，不猜是誰關的；處理路徑是「裝置管理→智慧電錶」編輯該電表切換模式。
- 數據同步為**每小時一次**：度數與廠商端有 1 小時內落差屬正常。度數長期不動的高頻真因：台科電雲端帳號的密碼變更或未開 API 服務，會讓該帳號下所有電表整批停止同步——到「團隊管理→進階設定→綁定設備廠商」重新驗證帳號密碼。
- 儲值後電還沒來：儲值帳單付款後偶有廠商回報延遲，系統每小時自動對帳補認；超過一小時仍未復電請聯繫客服。
- 排除以上仍異常（含硬體、室內迴路、跳電）→ 聯繫台科電或對應廠商，附電表名稱與物件資訊。$CTX$,
    '系統脈絡', ARRAY['電表排障']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：IoT領域-電表排障(子面向)');

-- 子『IoT設定引導』
INSERT INTO knowledge_base (question_summary, answer, category, categories, is_active)
SELECT '系統脈絡：IoT領域-IoT設定引導(子面向)',
    $CTX$## IoT 設定怎麼引導
先分流是哪類設定，再給對的路徑；涉及特定設備現況的問題轉電表排障處理。
- 電表串接啟用：到「團隊管理→進階設定→綁定設備廠商」綁定台科電（或其他廠商）帳號，驗證通過後系統會自動同步該帳號下的裝置清單，可在「裝置管理→智慧電錶」看到同步進來的電表；同一廠商帳號只能綁一個團隊，被占用需聯繫客服換綁。剛同步的電表不會自動關聯物件，要在智慧電錶列表編輯逐顆綁定物件；合約電費選「依儲值電錶設定」後，租客儲值的付款管道沿用該合約的收款方式（線下/線上）。
- 儲值單價與餘額：單價（每度金額）是在台科電端設定的，JGB 顯示的是同步後的鏡像值——要調整單價請到台科電端操作或聯繫廠商。
- 租客儲值流程：租客於前台對電表儲值會產生儲值帳單，付款入帳後自動入值；儲值帳單有效期為 4 天，逾期自動失效需重新發起。儲值的「錢入帳了沒」屬帳務範疇。
- 門鎖預設密碼規則、IoT 連結起始日：於 IoT 設定中調整，規則生效範圍以設定頁說明為準。$CTX$,
    '系統脈絡', ARRAY['IoT設定引導']::text[], TRUE
WHERE NOT EXISTS (SELECT 1 FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary='系統脈絡：IoT領域-IoT設定引導(子面向)');

DO $$
DECLARE n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge_base
    WHERE category='系統脈絡' AND question_summary LIKE '系統脈絡：IoT領域-%' AND is_active;
    RAISE NOTICE '✅ IoT 領域系統脈絡：% / 3（母1＋子2）', n;
END $$;
