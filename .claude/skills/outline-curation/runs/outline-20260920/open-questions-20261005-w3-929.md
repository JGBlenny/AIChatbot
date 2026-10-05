# 待裁問題彙整（20261005-w3-929，共 54 則；⛔ 不進正本）

1. `jgb/A/login-identity-switch`：本頁程式只證實同組帳號可有房東與租客兩種身分、以及登入時重選身分／偏好設定裡的預設房東身分；是否存在「已登入狀態下不重新登入即可切換身分」的入口，本次盤查未找到來源，待業主或後續盤查補充。
2. `jgb/A/forget-password-setpwd-invite`：被邀請設定密碼連結的實際發送情境（哪個功能觸發大房東子帳號設密碼）未在本頁程式中找到來源，僅能確認前端行為，待業主補充或於後續盤查（大房東相關粗目）核對
3. `jgb/A/dashboard-big-landlord-view`：幫助中心文件 Landlordonboarding00 描述大房東首頁有 7 個區塊，但目前程式碼（src/pages/users/dashboard/Landlord.vue 第 129-162 行）在大房東分支只渲染 EstateDetails 與 BalanceChart 兩個元件——文件與程式碼有落差，本細目依程式碼為準記錄事實，何者才是正確版本待業主裁決，不在此代為選邊。
4. `jgb/A/account-change-password`：驗證規則 'password' => 'min:6|...' 允許剛好 6 個字元，但對應的錯誤訊息文案寫「密碼必須超過6個字元」（字面上是要求超過 6 碼、也就是至少 7 碼）；規則與文案不一致，何者為準待業主裁決。
5. `jgb/A/account-progress-unlock`：UserController（account 方法）的顯示資料裡定義了『資訊完整度』兩階段：第一階段（1/2 基本資訊）標示解鎖「刊登廣告」，第二階段（2/2 身份資訊）標示解鎖「簽立合約」與「開通線上智能整合收款」；但對應的畫面卡片整段被 `@if (false && ...)` 關閉、不會顯示給使用者，本次盤查也沒有在別處找到真的依這兩個階段擋下刊登廣告／簽約／開通收款的判斷式。這兩階段目前是否仍是實際生效的規則（只是進度條沒顯示），或整個機制已經廢棄，待業主或後續盤查確認。
6. `jgb/A/signer-edit-permission`：「團隊資訊」頁（可能傳入 isAllowedToEdit 為 false 的呼叫端）不在本粗目頁面範圍內，本細目僅描述元件本身支援唯讀模式，實際哪些角色會被設為不可編輯需另外於團隊/人員相關粗目查證
7. `jgb/B/biglandlord-add`：team/index.blade.php 的 id="inviteMember" 燈箱（type=2）文案是「受邀請的對象如果不是 JGB 會員，將無法新增為大房東」，且只提供 Email／手機號碼搜尋既有會員，不像本細目引用的 MemberInvite.vue 有『未註冊』分支可直接填姓氏＋名稱建立非會員大房東；兩者是否對應同一個『新增大房東』入口、或分屬新舊兩套介面，待業主確認。
8. `jgb/B/biglandlord-sheet-overview`：「年度累計」欄目前是刻意隱藏：SelectBar.jsx 的 `const SHOW_YEARLY_COLUMN = false`（註解「2026-04-30 Joanna 拍板暫時隱藏」）與 Sheet.vue 對應區塊的 `v-if="false"` 都關閉了這一欄，畫面上不會顯示年度累計金額。是否要在知識裡提到這個欄位存在但目前關閉，或完全不提，待業主確認。
9. `jgb/B/biglandlord-sheet-overview`：月報明細（monthlyReport/ReconciliationTerm.vue、EZoneCashflow.vue 等）裡「租金收入」「本期支出」這兩個標題，只在 isLabelAdjust（useBigLandlordLabelAdjust）為真的團隊才會顯示；不是這個條件的團隊看到的是「屋主租金收入」「屋主租金支出」（V2 角色則是「本期屋主資金收入」「本期屋主資金支出」）。這兩套標題語義是否要分開寫成兩條知識、或只取一種當作『對外說法』，待業主確認。
10. `jgb/C/community-list-filter-sort`：進階搜尋下拉的縣市／行政區／建物類型／捷運站中文標籤來自後端 searchOptions API 回傳值，程式端看不到逐字標籤字串，僅能確認欄位存在（country/city/district/building/MRT）。
11. `jgb/C/community-edit-basic-fields`：「社區名稱」30字限制目前只在輸入框的 placeholder 文案看到，Basic.vue 裡查不到 maxlength 屬性或對應的驗證規則（如 yup schema），無法確認是否真的有強制驗證。
12. `jgb/C/community-estates-category-switch`：「總覽」分類的 label 在程式裡寫的是 `t('總覽-1')`（src/utils/constants/estate.js），repo 內查不到任何 zh-Hant 翻譯字典檔（find 全庫找不到 *zh-Hant* 的翻譯資料檔，只有無關的 vendor/giggsey locale 資料），無法確認這個翻譯 key 實際顯示出來的中文字串是「總覽」還是帶著「-1」字樣；本大綱一律以「總覽」書寫，但這是推測而非逐字驗證。
13. `jgb/C/estate-list-add-must-pick-community`：幫助中心文章 qa01（物件批次新增表格如何填寫？）描述『在物件管理的社區總表中，按下右上方新增物件旁的三角形，選擇「批次新增」』，但目前物件總表（src/pages/estates/list/_parts/PageTop.vue）的「批次新增」選項是被註解掉的死碼、畫面不會顯示；無法判斷是舊文件未更新、還是入口移到別處（例如社區底下的物件清單 communities.estates 仍保留批次新增）。
14. `jgb/C/estate-status-affects-actions`：這條主要依據幫助中心 slug39 文章；程式碼裡目前查得到的即時合約狀態篩選（src/use/search/modules/contractStatus.js）只有『無租約／洽談中／租約中』三態，且第三態的字面標籤是「租約中」而非文件的「合約中」，無法在程式端找到與文件完全一致、逐字對應的『未刊登／刊登中／洽談中／合約中』四態分類字串，兩者是否為同一機制的不同呈現無法判斷。
15. `jgb/C/estate-list-category-switch`：「總覽」分類的 label 在程式裡寫的是 `t('總覽-1')`（src/utils/constants/estate.js），repo 內查不到 zh-Hant 翻譯字典檔，無法確認實際顯示出來的中文字串是「總覽」還是帶著「-1」字樣；與 community-estates-category-switch 同一個已知落差，本大綱一律以「總覽」書寫。
16. `jgb/C/estate-edit-building-transcript-general`：一般物件建物謄本分頁（buildingTranscriptGeneral/Index.vue）是 General.vue 元件的 wrapper（傳入 showAllFields=true），社宅物件的建物謄本頁（building_transcript/Index.vue）是完全不同的獨立元件；兩條路由的 meta.label 都叫「建物謄本」，程式端看不到解釋為何欄位集合差異這麼大的說明文字，僅能確認兩者互斥（display_property_purpose_key 分別為 [1] 與 [2]）。
17. `jgb/C/estate-edit-building-transcript-general`：此處「一般物件」指 property_purpose_key=1（一般住宅），不是頁面內主建物／附屬建物自己的「用途」欄位（main_building_usage／sub_building_usage，如住家用、商業用）——兩者是不同概念，寫作時避免用「用途」一詞同時指涉兩者。
18. `jgb/C/estate-dashboard-repair-status-flow`：路由與分頁選單上的標籤是「修繕紀錄」（src/routes/estates.js: label: '修繕紀錄'），但頁面自己的大標題用的是「修繕記錄」（src/pages/estates/dashboard/repair/Index.vue: t('修繕記錄')），兩個字不一致，本大綱統一採用選單上的「修繕紀錄」，但無法判斷哪一個才是刻意的正式名稱。
19. `jgb/C/estate-house-vs-show-url`：程式裡該段的註解寫「則直接導向到簽名頁面」，但實際 redirect 目標是 route('contracts.show')（合約檢視頁），註解文字與程式行為不一致，本條依程式行為書寫。
20. `jgb/E/recharge-account-regenerate-expired`：同題另兩個子問（逾期虛擬帳號是否仍可收款、年繳帳單可否拆年度）未追完，待後續補查。
21. `jgb/F/repair-status-tabs`：「封存」這個狀態實際的使用情境（例如什麼樣的修繕單會被封存、跟其他狀態相比差異是什麼）程式與幫助中心都沒有進一步說明，需業主補充。
22. `jgb/F/repair-status-tabs`：程式裡另外定義了一個「進行中」狀態常數（Repair::PROCESS），但它不在總表這五個分頁對應的狀態清單裡，程式裡也沒有找到任何地方會真的把一張修繕單設成這個狀態——不確定這是還沒串接的功能、還是已經停用的舊狀態，需業主確認。
23. `jgb/F/repair-move-status-from-list`：「結單」跟「封存」兩個分頁在程式的權限判斷與移動選單邏輯上完全相同（見上面的移動邏輯），程式碼裡沒有找到任何額外規則差異；兩者在業務上除了名稱代表的意義（結單＝流程走完並與租客確認、封存＝收起來不常看）之外是否還有其他差別，需業主確認。
24. `jgb/F/repair-move-status-from-list`：齒輪按鈕的文案預設是「編輯＆查看」，只有在目前登入者被判定為大房東（isBigLandlord）或是房東方裡「只能看不能編」的經理人身分時才會變成「查看」；租客分支的程式碼並沒有另外針對租客身分把文案降級成「查看」，只沿用同一顆預設變數。程式裡沒有追到 isBigLandlord 這個判斷式對租客登入的回傳值，所以無法確認租客的齒輪文案是不是永遠固定顯示「編輯＆查看」、完全不會出現「查看」，需業主確認。
25. `jgb/F/repair-view-only-roles`：幫助中心的修繕教學不管實際權限是什麼，一律把這顆齒輪按鈕稱為「查看」（例如安排修繕、完成修繕教學都寫「選擇【查看】」），但程式預設的按鈕文字其實是「編輯＆查看」，只有大房東或只有顯示所屬權限的經理人才會看到「查看」兩個字；文件用語跟預設畫面不一致，需業主確認要不要更新教學文字。
26. `jgb/F/repair-apply-flow-and-entry`：幫助中心教學稱最後一步按鈕是「申請報修」，程式畫面上這顆按鈕的文字實際是「申請修繕」（見 repair.constant.ts），兩邊用語不一致，需業主確認何者為準、要不要統一。
27. `jgb/F/repair-apply-category-item-other`：畫面用一個固定的分類 id（enum Categories.OTHER = 11）判斷要不要顯示自訂名稱欄位，但程式碼裡找不到任何字串證據證明資料庫裡 id 11 這筆分類目前真的叫「其他」——這個對應只存在於前端寫死的數字，需業主查證資料庫內容或提供對應說明。
28. `jgb/F/repair-apply-detail-fields`：「通知及同步租客」開關跟「緊急修繕」勾選框都只用 :model 綁定（元件實際的 prop 叫 modelValue），沒有接 v-model 或任何 change 事件，畫面上看得到、點了卻沒有效果；這會導致房東方申請修繕時，該張單永遠不會同步進租客自己的修繕單總表（is_notice_tenant 卡在預設值），緊急修繕也永遠送出「非緊急」。這是程式錯誤（bug）而非設計行為，需要業主確認要不要排入修復。
29. `jgb/F/repair-apply-detail-fields`：後端常數 Repair::EMERGENCY_STATUS 定義的註解寫「非緊急」，但 RepairController／UserController／RepairService 等呼叫端全部把它當「緊急」使用（is_urgent = (status === EMERGENCY_STATUS)），External/RepairApiController 甚至直接把它的中文對應寫成「非緊急」，跟 RepairService 裡同一個常數對應「緊急」互相矛盾；命名/註解跟實際用法顛倒，需業主確認正確語意，避免之後改程式的人被常數名稱誤導。
30. `jgb/F/repair-apply-reservation-slots`：「預約時段」欄位在畫面上（RepairDetailItemBlock 的 isRequired）一律顯示紅字必填提示，但實際送出驗證只針對租客身分生效，房東方申請時看到的必填標示跟系統實際行為不一致，需業主確認是要改成非租客也不顯示必填提示，還是要補上驗證。
31. `jgb/F/repair-apply-photo-limit`：說明文字把「照片至多 10 張」跟「影片最長 30 秒或 100MB」寫在同一句，但程式裡找不到證據顯示這是同一個總額度、以先到的限制為準——比較像是照片、影片各自獨立的兩條限制。這句話該怎麼理解需業主確認。
32. `jgb/F/repair-edit-amount-visibility`：修繕單裡的「結算金額」目前看起來只是紀錄用的文字欄位，程式碼裡沒有找到它跟帳單模組之間的任何串接，也就是說填了金額不會自動產生一筆帳單給房東或租客；這是否符合預期（例如帳單是另外手動開立），需業主確認。
33. `jgb/F/repair-edit-share-to-vendor`：幫助中心把這個分享入口叫做「分享主頁」，但程式畫面上這個區塊的標題是「分享訊息」、按鈕是「分享」、彈窗標題是「分享修繕申請單」，三處都沒有「分享主頁」這個字串，用語對不上，需業主確認要不要統一。
34. `jgb/F/repair-share-public-link`：幫助中心的修繕教學裡完全沒有提到分享連結不需要登入、任何拿到網址的人都能看到報修者聯絡方式與廠商電話這件事，程式行為（完全公開、無身分核對）跟文件揭露的落差算不算需要補充提醒，需業主確認。
35. `jgb/G/power-meter-invoice-tab-fields`：這個細目原本的補件指示要求記錄「出租方統一編號」「稅別」「承租方統一編號」「買受人名稱」這幾個欄位為現有功能，但在釘住的 commit 上，這些欄位（含對應的 script 變數）全部被註解掉（ticket #14336：2024-09-04 PM 要求拿掉「出租方統編」相關欄位），畫面上完全不會渲染、也送不出資料；本細目已改為記錄程式現況（開立發票頁籤目前只剩「是否自動開立發票」一個選項），與原始指示的假設不符，需業主確認這批欄位是否之後有計畫復原、或原始指示依據的是舊版程式／文件。
36. `jgb/G/device-page-shared-list`：房東教學文件（Landlordonboarding08Device_zh-Hant.html）寫明版本更新後系統上僅可操作智慧電表，但程式仍保有完整的門鎖／攝影機／小白盒清單、編輯、開關鎖頁面與路由，兩者是否一致（例如僅隱藏行銷/教學曝光、實際功能仍在）需業主確認。
37. `jgb/G/device-edit-tabs-by-type`：deviceGroup.editable 目前在整理裝置清單資料時固定寫死成 1（程式旁註記「改為總是顯示」），畫面上依這個值鎖住編輯按鈕的機制形同虛設；需業主確認這是刻意讓編輯永遠開放、還是舊有依群組鎖編輯的功能已經廢止但畫面判斷式忘了拿掉。
38. `jgb/G/device-lock-passwords-three-types`：租客共用密碼區塊的畫面文字寫「@{{doorLockPasswords['3'].length}} / 50」暗示上限 50 組，但新增按鈕的 disabled 條件是 doorLockPasswords['3'].length == 10，實際功能上限是 10 組，兩處數字不一致，需業主確認何者才是正確上限。
39. `jgb/G/device-lock-passwords-three-types`：「編輯密碼」按鈕背後的點擊事件與編輯表單都還在（點下去會把整組欄位切成可編輯狀態），但外層 div 標了 :hidden="true"，恆為隱藏、不會渲染在畫面上，使用者沒有入口可以觸發；需業主確認這是刻意下架既有密碼的編輯功能（只留新增/刪除），還是應該拿掉這個隱藏旗標讓它重新可見。
40. `jgb/G/remote-unlock-page`：routes/web.php 在 /unlock/{iotId}/{batch} 這條路由上方標了「// QR code 開鎖」的註解，暗示這個連結原本設計是給 QR code 掃碼用；但門鎖管理的畫面（清單、編輯頁、密碼設定頁）裡都找不到任何產生或顯示 QR code／這個連結的入口，全域搜尋 QRCode／qrcode 也只在其他功能（LINE 預約、VR 拍攝）找到，沒有一處接到門鎖。ToolController::unlock() 的方法註解另外寫著「新北住都 - 現場業務查詢租客user密碼用」，連結碼是用門鎖 id 與建立時間算出來的固定值。這個連結／QR code 目前是由誰、透過什麼管道產生並交給使用者，需業主確認，否則無法在正本上寫「怎麼取得這個連結」。
41. `jgb/H/help-center-trial-form`：`if ('listings.helpCenter'.includes(route.name))` 這個判斷式是固定字串 'listings.helpCenter'.includes(變數)，只有 route.name 完全等於 'listings.helpCenter'（或是它的子字串）時才會成立；'listings.helpCenter.group'／'.post'／'.search' 這些子頁面的路由名稱反而不會命中。這看起來像是原本想寫成 route.name.includes('listings.helpCenter')（涵蓋所有幫助中心子頁）卻寫反了，還是刻意只在首頁觸發，需業主確認，關係到這句話要不要修正成『所有幫助中心頁面都會倒數』。
42. `jgb/I/pricing-free-trial-feature-scope`：src/pages/listings/pricing/parts/FAQ.vue 的『免費方案和體驗方案的差別？』問答明講免費方案『擁有智能合約及自動對帳功能』，但實際彈出的免費試用清單（LightboxFreePlan.vue）把自動對帳列在不支援清單裡（只是加註可申請藍新、中信）；兩份畫面文案互相矛盾，未能判斷哪一份是最新版本，交由業主裁決。
43. `jgb/I/pricing-free-vs-experience-plan`：本題的『免費方案』與 jgb/I/pricing-free-trial-eligibility 描述的自動贈送方案（app/User.php 建立房東身分時給的 plan_name='免費方案'）用的是同一個方案名稱，但 FAQ.vue 這則問答與 LightboxFreePlan.vue 彈窗的功能敘述在自動對帳等項目上互相矛盾（見 jgb/I/pricing-free-trial-feature-scope 的 open_questions），因此本題內容以 FAQ.vue 原文照實呈現，不代表已核實其功能清單。
44. `jgb/I/pricing-plan-price-basis`：app/Helper.php 的 get_plan_price() 只定義計算邏輯，實際的入門／熱門／專業／企業方案單價與基本費金額存放在資料庫 plan_estate_prices 表（透過 Redis 快取），不在程式碼裡，因此每個級距具體收費多少無法從程式碼直接列出，需要查詢當時資料庫內容才能確認。
45. `jgb/I/subscription-my-plan-page`：右側『溢繳費用』欄位顯示的金額是使用者累積的訂閱溢繳金餘額，實際的計算與使用時機見 jgb/I/subscription-plan-change-billing。
46. `jgb/I/payment-vendor-options-overview`：本題手續費／設定費數字來自幫助中心文章 qa27（https://www.jgbsmart.com/help/post/qa27，編輯日期 2026/06/30），未在 jgb2 程式碼中找到對應常數可交叉核對，僅能確認文件本身存在且描述具體，未能查證這些費率在系統上線時是否已經調整過。
47. `jgb/I/payment-vendor-options-overview`：適用範圍的細節（哪個身分／方案不能開哪個金流商）另立一條 jgb/I/payment-vendor-eligibility-by-role-and-plan，本題只點出有此限制存在，不重複展開。
48. `jgb/I/payment-newebpay-setup-details`：『三個工作天以上』的審核時間只在幫助中心文章 qa27 找到，jgb2 程式碼裡沒有找到對應的常數或後端排程可交叉核對，只能確認文件本身這樣寫。
49. `jgb/I/payment-vendor-edit-after-binding`：Cathaybk（國泰）明細頁同時帶 isDisabled={true} 又帶 onSubmit／onChange，兩者如何配合放行編輯（例如是否有另一個欄位或狀態解鎖輸入框）未在讀到的檔案範圍內看到，僅能確認它是唯一被接上重新送出邏輯的金流商。
50. `jgb/I/payment-permission-menu-visibility`：文件與程式對這個行為的歸因不一致，未選邊：qa23 把【收款設置】【訂閱方案】選單消失歸因於沒有開啟「編輯團隊」權限；但程式裡側邊欄選單（app/Role.php）這兩個項目各自對應獨立的查看權限旗標 show_role_payment（『查看收款設置』）與 show_role_subscription（『查看訂閱方案』），而且權限清單（app/Character.php）裡「編輯團隊」（edit_role）、「編輯收款設置」（edit_role_payment）、「編輯訂閱方案」（edit_role_subscription）是三個各自獨立的權限鍵，跟 show_role_payment／show_role_subscription 這兩個查看權限鍵又是不同層級。是否 qa23 所指的『編輯團隊』實際上涵蓋或連動這兩個查看權限，還是文件用詞不精確，需要業主或熟悉權限矩陣的人確認。
51. `jgb/I/task-manager-purpose`：任務列表頁（taskManagement/Index.vue）的說明文字寫「指定週期的前三十天完成單據的開立」，但新增／編輯任務頁（taskManagement/edit/Index.jsx）寫的是「觸發時間前 45 天完成單據的開立，系統後續會在觸發時間的 30 天前、15 天前寄送通知信」——兩個頁面對『提前幾天開單』給的具體天數不一致（30 天 vs 45 天），未能判斷哪一份是最新版本，交由業主裁決，因此標題不寫出具體天數。
52. `jgb/I/notification-mail-settings`：通知信設定頁面（notificationMail/Index.jsx）除了上述說明文字外，實際列出各通知類型並讓使用者新增副本信箱的清單區塊（state.typeOptions 抓回資料後應該渲染的地方）目前是空的 <div>，也 import 了 TaskItem／TableHead 元件卻沒有在畫面上使用，無法確認副本信箱的新增介面在目前版本是否已完整實作；另外，目前找不到任何現行（未被註解）的選單或連結會導向這個頁面，只能透過直接輸入網址進入。
53. `jgb/I/homepage-presales-assistant-visibility`：只讀了 listings/Home.vue 這一個檔案，不能排除同一個小幫手元件是否在其他官網頁面（例如價格頁、產品特色頁）用不同條件掛載並在正式環境顯示；此處只確認首頁這一支檔案目前的掛載條件是排除正式環境。
54. `jgb/I/tcloud-link-invalid-cases`：程式裡的註解寫「1. 找不到對應id 2. 該訂單已被付款」暗示已付款的訂單也會被導回首頁，但實際判斷式只檢查資料是否存在（empty($customerTCloud)），並沒有另外針對「已付款」的狀態做導回處理——已付款的訂單目前仍會正常顯示頁面並標示「已付款」，這條註解與實際判斷式所寫的邏輯不一致，未能查到近期改動紀錄能解釋這個落差。
