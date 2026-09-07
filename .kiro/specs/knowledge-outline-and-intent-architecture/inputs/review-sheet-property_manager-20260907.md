# 審核單：property_manager 正本 v3（2026-09-07）

> **業主 2026-09-07 裁：全部 ✅，已補 reviewed（version 2026-09-07.2）。**
> 每列打 ✅（reviewed）／✂️（刪）／✏️（改，寫一句）。我依單子補 `reviewed: {by: owner, at: …}`、刪除、重導出。未打 ✅ 的細目對 agent 不可見。

| # | 細目 id | 標題 | 來源 | 講法 | 字數 | 第一句 | 裁 |
|---|---|---|---|---|---|---|---|
| 1 | `property_manager/A/repair-ticket-photo-flow` | 拍照開修繕單基本流程與確認機制 | draft:batch#1 | 4 | 91 | 業務在現場上傳損壞照片後，系統先辨識損壞類別與急迫程度，進場第一輪就出確認摘要與三顆按鈕（確認送出／我要修改／取消）；只 | ✅ |
| 2 | `property_manager/A/repair-ticket-reclassify` | 分類辨識結果錯誤時如何修改 | draft:batch#2 | 2 | 56 | 按「我要修改」後只重新確認被改的項目（例如把「天花板」改成「馬桶後面的水管」），物件與急迫性不重問、不重跑辨識。 | ✅ |
| 3 | `property_manager/A/repair-ticket-low-confidence-candidates` | 照片辨識信心不足時的候選類別流程 | draft:batch#3 | 2 | 60 | 辨識信心不足時給 2–3 個候選類別讓業務選，選一後再出確認摘要；不退回三層下拉選單，也不憑空生成一句聽起來專業的描述。 | ✅ |
| 4 | `property_manager/A/repair-ticket-unrecognizable-photo` | 照片看不出損壞時的留白規則 | draft:batch#4 | 2 | 69 | 看不出損壞就明講看不出來，並請業務說明哪裡壞了；此時損壞描述必須留空，不得編寫「疑似管線老化」之類的推測，因為描述會原樣 | ✅ |
| 5 | `property_manager/A/repair-ticket-photo-count-limit` | 修繕辨識與附件的照片張數限制 | draft:batch#5 | 0 | 59 | 辨識一次最多用 3 張照片，多的由呼叫端先截；修繕單附件應保存全部照片（由呼叫端另帶完整清單），辨識仍只看前 3 張。 | ✅ |
| 6 | `property_manager/A/repair-ticket-agent-identity-lease-lookup` | 業務代開修繕單時的租約查詢身分規則 | draft:batch#6 | 0 | 51 | 業務替租客開單時不以業務自己的身分查租約；查不到租約不是錯誤，合約欄位留空直接開單，開單人由系統帶入。 | ✅ |
| 7 | `property_manager/A/repair-ticket-urgency-judgment` | 修繕單急迫程度的判斷來源 | draft:batch#7 | 0 | 55 | 急迫與非急迫由辨識建議，缺值時不得預設為急迫；值域以 JGB 資料庫為準（待裁：程式註解與舊表單的值域相反）。 | ✅ |
| 8 | `property_manager/A/repair-ticket-submit-failure` | 建單失敗時的處理與重試規則 | draft:batch#8 | 1 | 45 | 建單 API 失敗時明講「尚未建立」，提供「再試一次」；重複按確認在同一會話只會建一張單。 | ✅ |
| 9 | `property_manager/A/repair-ticket-vacant-no-lease` | 空屋或無租約物件的開單規則 | draft:batch#9 | 1 | 33 | 可以；空屋或無租約的物件開單時合約欄位為空，不因查不到租約而中止。 | ✅ |
| 10 | `property_manager/A/repair-ticket-mid-flow-cancel` | 報修流程中途取消的規則 | draft:batch#10 | 1 | 60 | 任一階段說取消（取消／不報了／不用了／算了／結束）即結束報修，JGB 不會產生新單。 | ✅ |
| 11 | `property_manager/B/dunning-draft-generation` | 催繳草稿的生成規則（模板＋語氣分級） | draft:batch#11 | 1 | 111 | 催繳草稿是模板加語氣等級：系統依近一年逾期次數分三級語氣（第 1 次客氣、2–3 次提醒、4 次以上明確），回傳含佔位符 | ✅ |
| 12 | `property_manager/B/dunning-draft-not-auto-send` | 催繳草稿不可一鍵發送給租客 | draft:batch#12 | 0 | 43 | 不可以；草稿一律推給業務自己複製去傳，不設計一鍵發送，所有提醒都是給業務而不是給租客。 | ✅ |
| 13 | `property_manager/B/dunning-draft-late-fee-mention` | 催繳草稿是否提及滯納金的規則 | draft:batch#13 | 0 | 83 | 合約有滯納金條款時模板可提及依合約計算滯納金；合約沒寫則不提；語氣第 1 級不提滯納金。 | ✅ |
| 14 | `property_manager/C/overdue-bill-followup-scope` | 逾期帳單追問可答範圍 | draft:batch#14, kb:3909, kb:3913 | 4 | 164 | 針對業務點選的那一筆帳單，可回近一年逾期明細（哪幾期、逾期幾天、是否補繳），數字全部來自 JGB 帳單資料；滯納金若依合 | ✅ |
| 15 | `property_manager/C/followup-session-single-item-boundary` | 追問的單筆會話邊界（不跨戶回答） | draft:batch#15 | 2 | 48 | 每筆清單項目是獨立會話，只看被點選的那一筆；問到別戶時退出並提示回清單點該戶，不回答別戶的內容。 | ✅ |
| 16 | `property_manager/C/followup-missing-data-in-jgb` | 追問遇到 JGB 沒有的資料時怎麼回 | draft:batch#16 | 1 | 52 | JGB 帳單只有已繳／未繳，沒有入帳日期；問到沒有的欄位就明講答不出來，不用更新時間冒充入帳日、不推算。 | ✅ |
| 17 | `property_manager/C/lease-expiry-followup-scope` | 合約到期追問可答範圍（導向續約面向） | draft:batch#17, kb:3799, kb:3824 | 5 | 140 | 進續約面向（不是退租收尾）：可依合約條款回答預告期是否到了、距到期幾天；租客有無續約意願 JGB 沒有欄位，要業務自己問 | ✅ |
| 18 | `property_manager/C/urgent-repair-followup-scope` | 緊急修繕追問範圍（目前無獨立面向） | draft:batch#18 | 1 | 41 | 目前沒有修繕歷史／進度面向，只有開單面向；緊急修繕在清單上照列，但第一版不開追問。 | ✅ |
| 19 | `property_manager/C/meter-item-followup-scope` | 電錶項目追問（導向電表排障面向） | draft:batch#19, kb:4021, kb:4091 | 4 | 118 | 電錶餘額不足走電表排障面向；項目以 id 直接進槽位，不靠關鍵字檢索。 | ✅ |
| 20 | `property_manager/C/followup-session-end` | 追問結束與流程收尾 | draft:batch#20 | 2 | 87 | 業務說結束（結束鈕送「結束」）即關閉這筆項目的會話並回清單；30 分鐘沒動作會話過期，過期後同一會話再進來要回可辨識的過 | ✅ |
| 21 | `property_manager/D/reply-tone-principles` | 回覆語氣與介面原則 | draft:batch#21 | 0 | 71 | 對象是站在現場、單手用手機的代管業務或房東：回答短、先給結論、按鈕優先於自由輸入；AI 只碰分類、措辭與挑選，數字與金額 | ✅ |
| 22 | `property_manager/D/prohibited-statements` | 禁止項清單（不編造／不推算／不代決定） | draft:batch#22 | 0 | 90 | 不編損壞描述、不推算 JGB 沒有的數字、不用系統時間冒充業務事實、不替租客做決定、不回答別戶資料、不自動送出任何會寫入 | ✅ |
| 23 | `property_manager/E/number-data-provenance-rule` | 數字的來源規則（一律引用JGB，需推算須標明） | draft:batch#23 | 0 | 75 | 帳單金額、逾期天數、次數、合約日期一律來自 JGB 資料；需要推算的（如依條款算滯納金）必須標明是推算並註明實際以 JG | ✅ |
| 24 | `property_manager/E/when-to-decline` | 什麼情況要拒答或退出 | draft:batch#24 | 0 | 64 | 三種情況一律拒答或退出：問到 JGB 沒有的資料、問到目前會話範圍以外的物件或人、以及需要寫入 JGB 但使用者尚未確認 | ✅ |
| 25 | `property_manager/E/identity-and-scope-boundary` | 誰在跟系統對話與權限邊界 | draft:batch#25 | 0 | 64 | 呼叫方是代管業務（管數十到數百戶）或自管房東，不是租客；身分由 LINE 綁定推出，權限以角色為邊界、只能看到自己權限內 | ✅ |
| 26 | `property_manager/E/session-expiry-general-rule` | 會話多久過期（一般規則） | draft:batch#26 | 0 | 64 | 系統端會話 30 分鐘沒動作即清除；過期後不得把新訊息當成全新對話靜默處理，要回可辨識的過期訊號。 | ✅ |
| 27 | `property_manager/F/urgency-value-domain-pending` | 急迫程度值域與預設值衝突（待裁） | draft:batch#27 | 0 | 56 | 急迫程度的數值定義程式註解與舊表單相反，且缺值時預設為急迫；需以 JGB 資料庫為準裁定並改預設為非急迫或留空。 | ✅ |
| 28 | `property_manager/F/repair-history-facet-pending` | 修繕歷史／進度面向是否新建（待裁） | draft:batch#28 | 0 | 30 | 修繕歷史／進度追問沒有對應面向，是否新建屬待裁；第一版不開。 | ✅ |
| 29 | `property_manager/F/dunning-endpoint-form` | 催繳草稿端點形式（待裁） | draft:batch#29 | 0 | 47 | 催繳草稿要做成面向內動作或獨立同步端點，二選一待裁；不論哪種都回模板加語氣等級、不回自由文字。 | ✅ |
| 30 | `property_manager/F/followup-latency-budget` | 追問回覆延遲上限（待驗） | draft:batch#30 | 0 | 39 | 呼叫端逾時 30 秒、點開才看等不了；追問回覆的 p95 尚無實測數據，待量。 | ✅ |
| 31 | `property_manager/F/contract-other-facets-scope-pending` | 合約其他子面向與對話規則是否納入本受眾範圍，待裁 | kb:3800, kb:3822, kb:3823, kb:3825, kb:3826 | 10 | 126 | 本細目涵蓋的系統機制目錄：合約領域-狀態判斷(子面向)；合約領域-合約異動(子面向)；合約領域-退租收尾(子面向)；合約 | ✅ |
| 32 | `property_manager/F/billing-other-facets-scope-pending` | 帳務其他子面向與對話規則是否納入本受眾範圍，待裁 | kb:3910, kb:3911, kb:3912, kb:3914 | 8 | 113 | 本細目涵蓋的系統機制目錄：帳務領域-繳費金流排障(子面向)；帳務領域-帳單異常(子面向)；帳務領域-發票(子面向)；帳務 | ✅ |
| 33 | `property_manager/F/account-domain-scope-pending` | 帳號領域（註冊／登入／綁定異動／團隊權限）系統知識是否納入本受眾範圍，待裁 | kb:3952, kb:3953, kb:3954, kb:3955, kb:3956 | 6 | 132 | 本細目涵蓋的系統機制目錄：帳號領域-帳號中心(母共用)；帳號領域-註冊驗證排障(子面向)；帳號領域-登入排障(子面向)； | ✅ |
| 34 | `property_manager/F/iot-setup-scope-pending` | IoT 設定引導系統知識是否納入本受眾範圍，待裁 | kb:4088 | 1 | 70 | 本細目涵蓋的系統機制目錄：IoT領域-IoT設定引導(子面向) | ✅ |
| 35 | `property_manager/F/estate-domain-scope-pending` | 物件領域（物件管理／操作引導／現況診斷）系統知識是否納入本受眾範圍，待裁 | kb:4132, kb:4133, kb:4134 | 3 | 100 | 本細目涵蓋的系統機制目錄：物件領域-物件管理(母共用)；物件領域-物件操作引導(子面向)；物件領域-物件現況診斷(子面向 | ✅ |
| 36 | `property_manager/F/subscription-domain-scope-pending` | 訂閱領域系統知識是否納入本受眾範圍，待裁 | kb:5373 | 1 | 69 | 本細目涵蓋的系統機制目錄：訂閱領域-條件診斷：訂閱(子面向) | ✅ |
