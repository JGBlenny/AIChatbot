# 審核單：Plan 9.18 S2 F／G／H／I 未審細目代理先審（118 條）

> 審閱的正本版本：commit `af8a86df`。本單由 `scratchpad/p918_s2_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 80／doubt 38／未先審 0。
> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審。⛔ 標示「有未先審細目」的組不可整組回「過」。

## 修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存） `F-repair-list`（待審 11 條：pass 9／doubt 2／未先審 0）

- [pass] `jgb/F/repair-list-search-filter` 修繕單總表可以怎麼搜尋或篩選？（案名／地址／經理人／租客關鍵字，加上單一組「修繕單時間段」下拉：報修時間起訖／最後更新時間起訖／7 日內申請報修三選一，還有分類／項目／是否緊急）
- [pass] `jgb/F/repair-list-columns` 修繕單總表的表格欄位顯示什麼？（物件地址、分類＆項目、報修日期、最後更新、結算金額、房東/管理者、租客）
- [pass] `jgb/F/repair-list-sort-and-pagination` 修繕單總表怎麼排序、一頁看幾筆？（每頁 30／60／90 筆可選；排序選項裡的「結算金額」只有房東方帳號才看得到）
- [pass] `jgb/F/repair-create-button-visibility` 「新增修繕單」按鈕誰看得到？（租客一定有；房東方要有「新增&編輯&刪除所屬」或「新增&編輯&刪除所有」修繕資料其中一項權限）
- [pass] `jgb/F/repair-total-visibility` 「結算總金額」是什麼？（只有房東方帳號登入時才會顯示；這個數字只加總目前這一頁看得到的修繕單，換頁或換每頁筆數就會不一樣）
- [pass] `jgb/F/repair-export-visibility` 誰能匯出修繕單？（要另外有匯出修繕資料的權限；而且這顆按鈕只有在「新增修繕單」按鈕會出現的身分底下才會一起出現，單獨有匯出權限而沒有編輯權限的房東方帳號看不到它）
- [pass] `jgb/F/repair-move-status-from-list` 修繕單總表怎麼切換狀態？（每列右邊的齒輪選單有「移至」各個狀態的選項，封存後仍然可以再移回其他狀態）
- [pass] `jgb/F/repair-list-filter-category-item-urgent` 修繕單總表可以用分類、項目、是否緊急篩選嗎？（可以；先選分類才能選項目，換分類會把已選的項目清空；「是否緊急」是一個勾選框，勾了才會加上這個條件）
- [pass] `jgb/F/repair-list-contact-card` 修繕單總表點「房東/管理者」或「租客」欄位會怎樣？（會彈出這個人的聯絡資訊卡）
- [doubt] `jgb/F/repair-status-tabs` 修繕單總表有哪些狀態分頁？（申請修繕、安排修繕、完成修繕、結單、封存，各代表什麼階段） —— 句序 2：這句說明各狀態代表什麼（「安排修繕代表房東方正在確認或已經指派廠商」「完成修繕代表…房東方在做結算與備註」等），但列出的來源全是程式，程式裡只有狀態名稱和註解，查不到這些說法，屬於無源句
- [doubt] `jgb/F/repair-view-only-roles` 哪些身分會看到「查看」而不是「編輯＆查看」的齒輪按鈕文字？（大房東角色，以及只有「顯示所屬」沒有「顯示所有」修繕資料權限的經理人帳號；這個文字只反映顯示修繕資料的權限，能不能移動狀態、能不能在細節頁編輯是另一組「編輯修繕」權限決定的，兩者互相獨立） —— 句序 2：團隊成員若是這張修繕單的經理人（agent_user_id 等於本人），逐物件權限判斷對所有修繕權限都回 true，所以只有「顯示所屬」權限的經理人看自己負責的修繕單時，齒輪文字是「編輯＆查看」而且有移動選項；把「查看」寫成經理人的常態（句 2、句 5 與標題）與程式相反

回覆：

## 報修申請流程 `F-repair-apply`（待審 8 條：pass 4／doubt 4／未先審 0） ⚠️

- [pass] `jgb/F/repair-apply-category-item-other` 報修分類項目怎麼選？（分類與項目都是系統設定的清單，選好之後在報修細節可以按「編輯」回上一步重選；有一個特定分類會多出讓使用者自己輸入名稱的欄位）
- [pass] `jgb/F/repair-apply-detail-fields` 報修細節要填什麼？（項目分類、問題必填；預約時段依身分決定是否必填；緊急修繕、佐證照片、備註選填；「通知及同步租客」是房東代租客申請時會看到的一個開關，但目前沒有實際作用）
- [pass] `jgb/F/repair-apply-reservation-slots` 預約時段規則是什麼？（畫面上標示為必填，但實際上只有租客身分申請時系統才會擋下沒填的情況；房東申請時就算不填也能送出）
- [pass] `jgb/F/repair-apply-photo-limit` 報修可以附照片或影片嗎？（照片最多 10 張；影片最長 30 秒或 100MB；支援 jpeg／jpg／png 圖片與 mov／mp4／webm 影片）
- [doubt] `jgb/F/repair-apply-flow-and-entry` 怎麼申請修繕單？（【修繕管理】>【修繕單總表】右上角「新增修繕單」進入，選物件→選分類項目→填報修細節→送出，按「上一步」「下一步」在步驟間切換） —— 句序 3：租客的修繕單總表只列 is_notice_tenant=1 的單；網頁上「通知及同步租客」開關沒有接上，房東建的單一律存成 is_notice_tenant=false，租客看不到，所以「不管誰發起，雙方登入系統都看得到」與程式衝突（文件與程式衝突，以程式為準）
- [doubt] `jgb/F/repair-apply-without-contract` 沒有租約在跑的物件也能申請修繕嗎？（可以，房東方只要建好物件就能申請，不用先有合約） —— 句序 1：含實作與過程筆記：「系統裡原本用合約找修繕對象的那段邏輯已經標註不再使用」，句 3「流程裡原本預留的合約欄位目前維持空白」也是；事實本身（房東方有物件就能申請）成立
- [doubt] `jgb/F/repair-apply-notifications` 新增修繕單後誰會收到通知？（租客本人、團隊擁有者會收到 Email，租客如果有綁定 LINE 也會收到 LINE 通知） —— 句序 1：程式裡 repair_create 的實際行為：租客發起只通知房東（LINE、通知中心、Email），不通知租客；房東發起時，租客通知受 is_notice_tenant 控制，而網頁建單一律是 false，所以只寄 Email 給房東。沒有「租客收到 Email／LINE」的路徑；句子只依幫助中心，與程式衝突
- [doubt] `jgb/F/repair-notifications-by-stage` 安排廠商、完成修繕、結單時還會發哪些通知？（依幫助中心教學：填寫廠商資訊後、完成修繕儲存後、移到結單狀態時，租客或團隊都會再收到一次通知） —— 句序 3：結單通知 repair_finish 只寄 Email（房東一律寄，租客要 is_notice_tenant 為 true 才寄），沒有 LINE 也沒有通知中心；句 1、句 2 的租客通知同樣受 is_notice_tenant 控制，網頁上房東建的單不會通知租客。只依幫助中心，與程式衝突

回覆：

## 修繕單編輯 `F-repair-edit`（待審 10 條：pass 5／doubt 5／未先審 0） ⚠️

- [pass] `jgb/F/repair-edit-print` 修繕單細節頁怎麼列印？（右上角有「列印」按鈕，會叫出瀏覽器內建的列印視窗，可以印出來或存成 PDF）
- [pass] `jgb/F/repair-edit-switch-status` 修繕單細節頁怎麼切換狀態？（下拉選單直接選要換到哪個階段，按「變更」儲存）
- [pass] `jgb/F/repair-edit-application-detail-readonly` 修繕單細節頁顯示哪些報修時填的資料？（「細節補充」區塊底下：申請日期、是否緊急、照片、聯絡電話或 Email、物件區域與時區、分類項目、問題、備註、預約時段；房東方才看得到「細節補充」這個標題與說明文字）
- [pass] `jgb/F/repair-edit-vendor-assign` 怎麼安排修繕廠商？（填寫修繕時間、廠商名稱、維修人員、聯絡電話，儲存後會留下歷史紀錄可以展開查看）
- [pass] `jgb/F/repair-edit-landlord-complete-memo` 「房東備註」要填什麼？（完成時間、備註文字最多 300 字、可以附照片，最多 10 張、單檔最大 10MB、支援 JPG／PNG／PDF；只有有編輯權限的房東方帳號能編輯）
- [doubt] `jgb/F/repair-edit-progress-timeline` 修繕單細節頁的進度時間軸顯示什麼？（申請修繕、安排修繕、完成修繕、結單、封存五個階段各自的日期，還沒到的階段不顯示日期） —— 句序 1：時間軸上的日期不是「到了這個階段的日期」：安排修繕取第一筆廠商紀錄的修繕時間，完成修繕取房東備註的完成時間；結單、封存時間在列表「移至」往回移時不會清掉。所以「還沒到的階段不顯示日期」這個絕對說法有程式反例（例如還在安排修繕，房東先填了完成時間）
- [doubt] `jgb/F/repair-edit-cannot-edit-roles` 誰不能編輯修繕單細節頁？（租客帳號、大房東角色都只能看，不能切換狀態、不能改廠商資訊、不能寫房東備註） —— 句序 1：「租客帳號…都只能看內容」與同組的 repair-edit-tenant-memo 句 3 矛盾：租客在細節頁可以編輯「房客備註」。標題「都只能看」也一樣
- [doubt] `jgb/F/repair-edit-amount-visibility` 修繕結算金額誰看得到？（「結算金額」欄位只有身分是房東的帳號才會顯示，租客看不到；這筆金額目前只是修繕單自己的紀錄文字，沒有找到跟帳單模組串接的路徑） —— 句序 標題：標題含過程筆記與實作詞：「沒有找到跟帳單模組串接的路徑」。內文「不會自動產生帳單」本身成立
- [doubt] `jgb/F/repair-edit-tenant-memo` 「房客備註」是什麼？（右邊那一欄，只有這張修繕單有填過預約時段才會出現，沒有的話會顯示「此修繕單為房東發起，無房客備註」） —— 句序 2：房東在網頁申請時一定會送出至少一列預約時段，因為第一列刪不掉，沒填的話就是空值；後端仍把它存進 pre_assign_data，細節頁的 tenant_order_times 變成 ["  - "]，不是空的。結果房東發起、沒填時段的單也會顯示房客備註區，不會出現「此修繕單為房東發起，無房客備註」
- [doubt] `jgb/F/repair-edit-share-to-vendor` 怎麼把修繕單分享出去給廠商？（在修繕單細節頁點「分享」，可以複製連結，也可以直接用 LINE 分享出去；廠商點開連結不需要登入 JGB 帳號） —— 句序 1：絕對句漏了裝置例外：行動裝置上瀏覽器支援 navigator.share 時，點「分享」直接叫出系統分享選單，不會開「分享修繕申請單」視窗，句 2 的「兩種方式」也就不成立

回覆：

## 修繕單分享頁 `F-repair-share`（待審 4 條：pass 3／doubt 1／未先審 0）

- [pass] `jgb/F/repair-share-public-link` 修繕單分享頁需要先登入嗎？（不需要，這個連結是公開的，系統特別把它排除在登入檢查之外，任何拿到網址的人都可以直接打開）
- [pass] `jgb/F/repair-share-visibility-summary` 分享連結誰看得到？（拿到網址的任何人都能看到這張修繕單房東方的手機／Email、物件所在區域、照片、廠商聯絡電話；金額只有在瀏覽者本人目前登入身分是房東時才會顯示，且不會核對是不是這張修繕單相關的房東或租客）
- [pass] `jgb/F/repair-share-content` 修繕單分享頁看得到什麼？（修繕申請單標題與是否緊急、照片、報修細節、安排的廠商資訊、房東備註與房客備註，全部都是唯讀；不會顯示物件廣告連結、縮圖，也沒有房東／承租方資訊側欄）
- [doubt] `jgb/F/repair-share-no-expiry` 分享連結會過期嗎？（目前不會，系統一度寫過 30 天過期的檢查，但已經停用，現在沒有天數限制） —— 句序 2：含實作歷史筆記：「系統背後曾經寫過『如果超過 30 天就不給查看』的檢查，但這段檢查已經被停用」，標題「系統一度寫過 30 天過期的檢查」也是；對使用者來說只要「目前不會過期」即可

回覆：

## 電表列表與單一電表 `G-power-meter`（待審 17 條：pass 15／doubt 2／未先審 0）

- [pass] `jgb/G/power-meter-list-category-tabs` 電錶清單怎麼切換分類？（所有電錶、一般型、儲值型三個分類，切換後會換一批列表）
- [pass] `jgb/G/power-meter-list-status-tags` 電錶清單的狀態標籤是什麼意思？（全部／供電中／斷電中／未連線，夾在分類跟清單之間；未連線含未啟用）
- [pass] `jgb/G/power-meter-list-search` 電錶清單怎麼用關鍵字搜尋？（可選描述、序號、設備名稱、所屬物件名稱其中一種）
- [pass] `jgb/G/power-meter-list-sort` 電錶清單怎麼排序？（可依設備描述、目前電度、預計可用電度排序；門鎖、攝影機、小白盒清單沒有排序選單）
- [pass] `jgb/G/power-meter-manufacturer-maintenance` 電錶清單出現「原廠系統維護中」是什麼意思？（維護期間度數不更新、無法儲值）
- [pass] `jgb/G/power-meter-service-expiry` 電錶顯示「服務到期」或「快到期」怎麼辦？（30 天內到期會提醒續訂；只有業者看得到，只出現在清單頁）
- [pass] `jgb/G/power-meter-list-row-fields` 電錶清單每一列顯示什麼？（型號序號、目前電度、狀態、所屬物件；儲值型才有預計可用電度與低電度警報）
- [pass] `jgb/G/power-meter-usage-chart-export` 電錶清單列展開後能看什麼？（用電量走勢圖可選 1/7/30/90 天；CSV 只能下載前 90 天）
- [pass] `jgb/G/power-meter-single-edit-tabs` 電錶編輯頁能改什麼？（儲值型有基本設定／電錶資料／開立發票三個頁籤，一般型只有基本設定）
- [pass] `jgb/G/power-meter-single-estate-single-bind` 一支電錶只能綁一個物件？（選擇物件的挑選頁是單選，選了一個之後其他物件會被鎖住不能再選）
- [pass] `jgb/G/power-meter-mode-switch` 怎麼切換電錶的供電狀態？（一般型：供電／斷電；儲值型：儲值／強開／斷電，切換中鎖按鈕只有儲值型有）
- [pass] `jgb/G/power-meter-basic-info-fields` 電錶資料頁的餘額、費率、預計可用電度怎麼看？（只有儲值型電錶才有這個頁籤；費率由雲端儲值系統設定，可用電度＝餘額÷費率）
- [pass] `jgb/G/power-meter-topup-flow` 電錶怎麼儲值？（「儲值」按鈕就在清單列上，不用展開；金額固定四個選項，維護中或連不上廠商時按鈕會變灰）
- [pass] `jgb/G/power-meter-invoice-tab-fields` 開立發票頁籤裡面能填什麼？（目前只有帳單是否開立發票一個選項）
- [pass] `jgb/G/power-meter-list-empty-state` 電錶清單沒有資料時畫面顯示什麼？（分類內沒有設備寫「此分類尚無設備」；完全沒綁定寫「目前尚無綁定設備」，租客看不到綁定引導連結）
- [doubt] `jgb/G/power-meter-vendor-unreachable` 電錶顯示「目前連不上廠商」怎麼辦？（度數不會更新、儲值送不出去；業者跟租客都看得到） —— 句序 1：「如果目前連不上某個廠商，清單頁與單一電錶頁…都會出現」是絕對句，但只適用全站共用連線的那家廠商；另一家以帳號巡檢回報連不上時，提示只給業者看、只出現在清單頁，而且會寫帳號並叫人查帳號密碼，和句序 2、3 的敘述相反
- [doubt] `jgb/G/iot-entry-requirements` 電錶／門鎖／攝影機／小白盒頁面需要什麼條件才能進入？（需訂閱方案、且未超過物件數量上限） —— 句序 1：第二道檢查不是物件數量上限，而是方案有沒有開 IoT 功能；兩道檢查也都不擋租客。另外「路由」「掛了檢查」是實作詞

回覆：

## 裝置頁（門鎖、攝影機、小白盒） `G-device-page`（待審 7 條：pass 5／doubt 2／未先審 0）

- [pass] `jgb/G/device-page-shared-list` 門鎖／攝影機／小白盒清單長什麼樣？（型號序號、描述、狀態、所屬物件四欄，可依關鍵字搜尋，沒有排序選單）
- [pass] `jgb/G/device-page-lock-open-close` 門鎖清單怎麼直接開門／鎖門？（開門一定有、鎖門只有特定廠商支援；離線時按鈕不會顯示）
- [pass] `jgb/G/device-lock-type-and-binding-limit` 私人門鎖跟共用門鎖差在哪？（私人只能綁一個物件，共用可以綁多個）
- [pass] `jgb/G/device-lock-open-log` 門鎖的開門記錄怎麼看？（可依日期查詢操作時間與動作，沒有記錄時會顯示尚無記錄）
- [pass] `jgb/G/device-gateway-not-counted` 小白盒綁定物件跟門鎖不同在哪？（小白盒不會讓物件被標記為「IoT裝置」，也不會擋刪除）
- [doubt] `jgb/G/device-edit-tabs-by-type` 裝置編輯頁的頁籤，門鎖跟攝影機／小白盒不一樣？（門鎖多出密碼設定、開門記錄兩個頁籤） —— 句序 4：「編輯按鈕在分類群組被標記成不可編輯時會鎖住…目前程式把這個群組一律標記為可編輯」是程式實作筆記，講的是使用者看不到的失效機制，不是畫面行為
- [doubt] `jgb/G/device-lock-passwords-three-types` 門鎖密碼有哪三種？（房東個人密碼、租客個人密碼、租客共用密碼，權限各不同） —— 句序 3：加引號的「編輯密碼」在現行畫面上不會出現（被設成隱藏），不能當介面標籤引用；「畫面上雖然定義了…被設定成永遠不會顯示」是實作詞。使用者看得到的事實（沒有編輯入口，只能刪掉重新新增）應直接寫

回覆：

## 遠端解鎖（輸入解鎖密碼開門） `G-remote-unlock`（待審 2 條：pass 1／doubt 1／未先審 0） ⚠️

- [pass] `jgb/G/remote-unlock-no-login` 遠端解鎖連結需要登入嗎？（不用登入，只要有連結跟密碼就能開）
- [doubt] `jgb/G/remote-unlock-page` 遠端解鎖連結怎麼用？（輸入共用密碼按開門，密碼錯誤或連結失效會提示原因；找不到產生這個連結的入口） —— 句序 5：「找不到任何按鈕或畫面會產生…」是盤查過程筆記，「連結碼是用這台門鎖的建立時間算出來的固定值」是實作細節（實際是門鎖 id 加建立時間算出的雜湊）。標題「找不到產生這個連結的入口」也帶著同樣的過程筆記語氣

回覆：

## 幫助中心（分類、文章、搜尋） `H-help-center`（待審 5 條：pass 4／doubt 1／未先審 0）

- [pass] `jgb/H/help-center-home-groups` 幫助中心首頁長什麼樣？（分類卡片顯示圖示、篇數、更新日期）
- [pass] `jgb/H/help-center-group-structure` 幫助中心分類頁怎麼排文章？（分類底下先分次分類，各次分類再列出文章卡片）
- [pass] `jgb/H/help-center-post-detail` 幫助中心文章內頁有什麼？（麵包屑、分享到 Facebook／LINE、上下篇導覽、相關文章）
- [pass] `jgb/H/help-center-trial-form` 幫助中心的「立即免費試用」視窗是什麼時候跳出來的？（首頁停留 60 秒自動彈出，四個欄位都要填）
- [doubt] `jgb/H/help-center-search` 幫助中心搜尋怎麼運作？（比對標題與內文、多個關鍵字要同時出現、可加選分類） —— 句序 3：「沒有輸入任何關鍵字就送出搜尋，會直接被導回幫助中心首頁」與畫面行為不符：關鍵字空白時，搜尋框的送出根本不會跳頁，人會停在原頁。導回首頁只發生在直接打開沒帶關鍵字的搜尋網址時

回覆：

## 方案、價格與免費試用 `I-pricing`（待審 11 條：pass 5／doubt 6／未先審 0） ⚠️

- [pass] `jgb/I/pricing-plan-tiers-overview` JGB 有哪些方案？（免費試用、體驗方案、入門／熱門／專業四級距、企業方案）
- [pass] `jgb/I/pricing-free-vs-experience-plan` 免費方案與體驗方案差在哪？（前者系統贈送 5 個物件，後者每月付費可續訂 10 個物件）
- [pass] `jgb/I/pricing-calc-by-estate-count` 怎麼用物件數量試算方案價格？（50～500 物件拉桿試算，超過 500 個要洽企業方案）
- [pass] `jgb/I/pricing-enterprise-plan-offer` 企業方案提供什麼？（客製化 LOGO 頁與網址頁，需另外聯繫洽談）
- [pass] `jgb/I/pricing-quota-full-block` 物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案）
- [doubt] `jgb/I/pricing-free-trial-eligibility` 免費試用怎麼開始、能用多久？（新建立房東身分自動取得，一個週期後不自動續訂） —— 句序 1：引號裡的介面文案跟現行畫面不一致：畫面上是「不綁信用卡的30天的試用方案，歡迎體驗！」，正本寫成「不綁信用卡的 30 天試用方案」
- [doubt] `jgb/I/pricing-free-trial-feature-scope` 免費試用不能用哪些功能？（最多 5 個物件，不支援團隊與門鎖電錶等進階功能） —— 句序 3：兩個問題：(1) 引號文字多了一個逗號，現行是「無法申請國泰、永豐可申請藍新、中信」；(2)「這個限制其實只擋國泰與永豐」是絕對句，漏了個人房東的例外。個人房東連藍新也不能開，跟同組 payment-vendor-eligibility-by-role-and-plan 矛盾
- [doubt] `jgb/I/pricing-individual-vs-corporate-team` 個人房東與企業團隊方案差在哪？（人員管理四項功能、自動對帳與分店管理起始級距不同） —— 句序 2：標題和句 2 都說這四項屬於「人員管理」，但比較表裡「團隊資訊」「進階設定」其實在「團隊管理 / 其他設定」群組
- [doubt] `jgb/I/pricing-quota-near-full-notice` 物件額度快滿了會怎樣？（剩 5 個以下觸發提醒，剛好剩 5 個另寄 Email） —— 句序 1：剩 5 個以下時系統只寫通知中心、不寄 Email；只有剛好剩 5 個那次才寄一封 Email，所以句 1 的「與 Email」沒有來源，句 2「再另外寄送一封」也跟著錯
- [doubt] `jgb/I/pricing-trial-plan-landing-page` 體驗方案介紹頁講什麼？（每月費用試算、體驗方案資格需求、客戶見證、免費試用／免費諮詢按鈕） —— 句序 3：寫出了客戶名稱「愛租屋」，應改寫或不具名。另外句 1 的引號漏了「元」，現行是「每月只需 [s1] 元，…」
- [doubt] `jgb/I/pricing-plan-price-basis` 方案價格怎麼算、年繳有折扣嗎？（體驗方案月費固定台幣 100 元；一般方案年繳等於 10 個月的月費） —— 句序 1：100 元只是說明文字裡寫死的數字。實際扣款和方案頁顯示的價格，都是 get_plan_price(10,…) 從 plan_estate_prices 表讀出來的，所以「體驗方案固定 100 元」跟句 2「其他方案不是寫死」的對比不成立

回覆：

## 訂閱、付款與訂單 `I-subscription-payment`（待審 20 條：pass 14／doubt 6／未先審 0）

- [pass] `jgb/I/subscription-choose-plan-flow` 訂閱頁怎麼選方案？（體驗方案、依物件數量拉桿的基本方案、企業方案洽談三選一）
- [pass] `jgb/I/subscription-payment-authorization-flow` 訂閱怎麼扣款？（先試刷 TWD 1 驗證信用卡、藍新金流走 SSL／PCI-DSS）
- [pass] `jgb/I/subscription-invoice-fields` 訂閱時發票資訊要填什麼？（二聯式／三聯式、統一編號僅三聯式必填；地址欄目前沒有掛必填檢查）
- [pass] `jgb/I/subscription-coupon-and-renewal-discount` 訂閱優惠碼怎麼用？（輸入後即時驗證，續訂優惠次數沒有設定上限時顯示「終生」）
- [pass] `jgb/I/subscription-my-plan-page` 我的方案頁看什麼？（方案卡片、付款方式綁定狀態、溢繳費用）
- [pass] `jgb/I/subscription-change-card-flow` 怎麼換綁信用卡？（更新要重新授權並試刷 1 元，變更方案按鈕需要對應權限）
- [pass] `jgb/I/subscription-plan-change-billing` 換方案時舊方案沒用完的錢會退嗎？（按剩餘天數比例換算成溢繳金，直接折抵新方案費用）
- [pass] `jgb/I/subscription-renewal-charge-failure` 自動續訂扣款失敗會怎樣？（方案資料整個清空、限額歸零、所有物件立即下架，沒有寬限期）
- [pass] `jgb/I/payment-vendor-options-overview` 收款設置支援哪些金流商？（藍新／國泰世華／永豐／中信／icash Pay／現金收款帳戶，各家設定費與手續費不同）
- [pass] `jgb/I/payment-vendor-eligibility-by-role-and-plan` 哪些身分或方案不能開通某些金流商？（個人房東不能開藍新／國泰世華／永豐，免費方案／體驗方案不能開國泰世華／永豐）
- [pass] `jgb/I/payment-newebpay-setup-details` 藍新金流申請要注意什麼？（個人房東無法申請；手機與 Email 送出後不能改，每個金流最多開三組帳號，需審核）
- [pass] `jgb/I/payment-receipt-template-options` 收據範本有哪些？（財政部包租業租金收據範本只有法人／社宅團隊才看得到）
- [pass] `jgb/I/payment-receipt-deposit-team-extras` 押金收據能自訂摘要跟蓋章嗎？（摘要與三顆收款章都只有特定合作團隊才看得到）
- [pass] `jgb/I/payment-bill-autosend-and-recipient` 帳單可以自動排程發送、指定收款人嗎？（提前 0～20 天自動發送，收款人可選原簽約者／主要經理人／自訂）
- [doubt] `jgb/I/subscription-cancel-effect` 取消訂閱會怎樣？（立即停止自動續訂與已授權信用卡，但用到目前效期結束才失效） —— 句序 3：「寄送 Email 通知使用者」實際不會發生。controller 呼叫的是 'subscription_cancel'，但 Notification::notice 裡只有拼錯的 case 'subscription_cance'，比對不到就不寄；就算拼對了，那個 case 也只在訂閱仍有效時才寄。對照組：同一個 switch 裡的 case 'will_full_remind_to_subscription' 有抓到
- [doubt] `jgb/I/orders-payment-history` 付款紀錄頁看什麼？（扣款日、訂單編號、付款內容、金額、收據） —— 句序 1：括號裡舉的例子「熱門方案的加購次數、續訂折扣說明」沒有來源。付款內容實際是「訂閱方案：[方案名] - 共 [n] 個物件 * 1」這類品項，再加上訂單的 contents
- [doubt] `jgb/I/payment-vendor-edit-after-binding` 金流綁定後還能改嗎？（除了國泰世華，其他金流商明細頁都是唯讀不能重送） —— 句序 1：國泰世華明細頁的主要綁定欄位（加密因子、ATM 前綴）一樣是唯讀；只有超商條碼欄位還沒填齊時，才能補填那一段再送出，不是整張表都能重填
- [doubt] `jgb/I/payment-icash-ctbc-setup` icash Pay／中信收款帳戶申請要多久？（智付通約 2-5 個工作天，中信 ACH 驗證約 5 個工作天） —— 句序 1：「智付通…需至少 2 - 5 個工作天」這段提醒是在選藍新（newebpay）時才顯示，不是 icash Pay；標題跟著錯
- [doubt] `jgb/I/payment-bill-e-invoice-setup` 帳單怎麼開電子發票？（要先聯繫 JGB 業務開通加值服務，開通後才會出現稅與發票分頁） —— 句序 3：「預先開立發票」模式只有特定合作團隊（preBillingInvoice 群組）才有，一般帳號只能選「帳單已到帳後開立」；而且開立時機還有「繳費期限後」，不只是「提前」
- [doubt] `jgb/I/payment-permission-menu-visibility` 沒有查看權限會怎樣？（收款設置與訂閱方案選單整個不會出現） —— 句序 1：唯一的文件來源 qa23 說是少了「編輯團隊」權限；程式則是兩個選單各自看 show_role_payment／show_role_subscription（查看收款設置／查看訂閱方案）。文件和程式本身就衝突，正本又把兩邊混在一起，還把文件裡綁「編輯團隊」的「帳號資訊以個人房東形式呈現」接到查看權限上

回覆：

## 預約 demo `I-demo-booking`（待審 4 條：pass 3／doubt 1／未先審 0）

- [pass] `jgb/I/demo-form-fields` 預約 demo 表單要填什麼？（公司、職稱、聯絡方式、物件所在地、感興趣功能與諮詢內容）
- [pass] `jgb/I/demo-form-option-lists` demo 表單的下拉選項有哪些？（物件數量 7 級距、團隊人數 6 級距、感興趣功能 6 項）
- [pass] `jgb/I/demo-form-submit-result` demo 表單送出後多久有人聯繫？（顯示感謝頁，2-3 個工作天內專人聯繫）
- [doubt] `jgb/I/demo-form-actual-validation-scope` demo 表單哪些欄位真的會被系統擋下？（系統實際只驗公司、姓名、電話、Email 四項） —— 句序 1：送出按鈕不是填完才「變可點擊」，它一直都能點；前端 10 個欄位都有瀏覽器原生 required，會先擋下送出，所以「只要四項合格就能送出成功」只有直接打 API 才成立。這和同組 demo-form-fields 說的「按鈕本身一律可以點擊，擋送出的是瀏覽器驗證」互相矛盾

回覆：

## 控制台（設定、通知信範本、自動化任務） `I-control-panel`（待審 9 條：pass 5／doubt 4／未先審 0） ⚠️

- [pass] `jgb/I/task-manager-type-behavior-scope` 新增任務能選哪些類型？（目前只開放「通知」類型，行為是信件通知或站內通知）
- [pass] `jgb/I/task-manager-cycle-options` 任務週期怎麼設定？（單位分年／月，方式可選僅一次、持續不停、特定日期結束、重複特定次數）
- [pass] `jgb/I/task-manager-form-fields` 新增任務表單有哪些欄位？（任務名稱、任務類型、關聯物件、任務行為、任務時間、重複間隔、結束時間、通知對象、通知內容）
- [pass] `jgb/I/task-manager-edit-delete-copy` 已建立的任務怎麼編輯／刪除？（每筆任務可編輯、複製、刪除，編輯週期任務可選只改這次或連後續一起改）
- [pass] `jgb/I/control-panel-access-restriction` 誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定」子路徑才會擋）
- [doubt] `jgb/I/control-panel-entry-scope` 控制台首頁目前能用什麼？（目前只有「任務管理器」一個項目可以點擊進入） —— 句序 2：「點擊後會進入任務管理器頁面」是絕對句，漏了權限例外：角色不在 controlPanel 或 tongSang 分組的人，點了會被導回 /users
- [doubt] `jgb/I/control-panel-setting-shell` 進入控制台設定後看到什麼？（本身只是麵包屑與側欄外殼，內容是任務管理器頁面） —— 句序 1：「本身不含其他獨立內容」和程式不符：外殼在非新增／編輯頁會顯示 OrderAside 側欄（標題寫了側欄，內文沒寫）。子路由也不只有任務管理器與新增／編輯，還有 notificationMail
- [doubt] `jgb/I/task-manager-purpose` 任務管理器是做什麼用的？（設定週期性任務或預定通知，系統會提前自動開單並寄信） —— 句序 標題：標題把「系統會提前自動開單並寄信」寫成系統事實，但目前任務類型只有「通知」，修繕開單已經被註解掉，和同組 task-manager-type-behavior-scope 矛盾。內文只是轉述頁面說明，而頁面說明本身兩處也對不上：列表頁寫前三十天，新增頁寫前 45 天
- [doubt] `jgb/I/notification-mail-settings` 通知信副本信箱怎麼設定？（預設收件為團隊擁有者信箱，每個通知信最多再加 3 組副本） —— 句序 1：標題問「怎麼設定」，但這一頁只有說明文字，沒有任何可以新增副本信箱的表單或控制項；首頁卡片和側欄的入口也都被註解掉了，所以回答不了標題，還會把人引到一個不能用的頁面

回覆：

## 官網首頁 `I-marketing-home`（待審 7 條：pass 5／doubt 2／未先審 0）

- [pass] `jgb/I/homepage-ten-features-actual-count` 首頁「JGB平台十大特色」實際列出幾項？（標題寫十大，目前輪播只設定 3 項：管理儀表板、線上合約管理、即時帳務報表）
- [pass] `jgb/I/homepage-city-count-cta` 首頁說 JGB 在東南亞幾個城市使用？（超過 8 個城市，旁邊有免費試用／免費諮詢按鈕）
- [pass] `jgb/I/homepage-presales-assistant-visibility` 首頁的線上諮詢小幫手正式站看得到嗎？（目前設定為正式環境不顯示，只在非正式環境出現）
- [pass] `jgb/I/homepage-three-advantages` 首頁「JGB平台擁有三大優勢」是哪三項？（提高出租效率、自動化管房流程、提升租客服務品質）
- [pass] `jgb/I/homepage-enterprise-partners-section` 首頁「企業夥伴」放了什麼？（10 個合作夥伴 logo 排成靜態方格，不是輪播）
- [doubt] `jgb/I/homepage-sections-overview` 官網首頁有哪些區塊？（橫幅、熱門物件、優質租管業者推薦、特色介紹、企業夥伴、最新消息） —— 句序 2：`v-if="hotListings"` 和 `v-if="landlordFeedback"` 檢查的是陣列：前端預設值與後端回傳都是 []，而 [] 在 JS 裡是 truthy，所以沒資料時區塊標題照樣會顯示，「只有在有回傳資料時才會顯示」不成立（句序 3 同理）。另外句序 1 說「最後是企業夥伴」，但企業夥伴後面還有一張 IWBI 圖片
- [doubt] `jgb/I/homepage-latest-news-section` 首頁「最新消息」顯示什麼？（沒有消息資料時整區塊不會出現，點擊會開啟幫助中心文章） —— 句序 1：`v-if="news"` 檢查的是陣列：後端回傳的是 array_slice 產生的陣列，前端預設值也是 []，[] 是 truthy，所以沒有消息時「最新消息」標題與空輪播照樣會出現，「整區塊不會出現」（標題也這樣寫）不成立

回覆：

## 中華電信雲市集訂單頁 `I-hicloud-order`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/I/tcloud-order-info-fields` 雲市集訂單頁顯示什麼？（訂單編號、時間、採購方案、價格、點數折抵、付款狀態）
- [pass] `jgb/I/tcloud-link-invalid-cases` 雲市集訂單連結為什麼會失效？（連結簽章驗證不過，或訂單編號查無資料，都會導回官網首頁）
- [doubt] `jgb/I/tcloud-payment-instructions` 雲市集訂單怎麼付款？（國泰世華一次性虛擬帳號限 WebATM，2 個工作天內付款，付款後 2 天開發票、7 天內開通） —— 句序 標題：標題「付款後 2 天開發票、7 天內開通」把來源的「工作天」拿掉了，數字單位對不上；「限 WebATM」也比來源的「請透過WebATM進行轉帳，避免付款失敗」說得更死（內文三句本身正確）

回覆：
