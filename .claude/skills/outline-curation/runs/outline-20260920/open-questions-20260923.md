# 待裁問題彙整（20260923，共 81 則；⛔ 不進正本）

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
20. `jgb/D/contract-list-status-tabs`：「登入後的首頁」對應的路由是 users.dashboard；這個路由依角色渲染不同元件（租客走 Tenant.vue，房東／社宅走 Landlord.vue），本細目描述的是租客被導轉後的畫面，但「首頁」這個標籤字串（t('首頁')）只在 Landlord.vue 的麵包屑找到證據，Tenant.vue 本身沒有對應的標題文字，交回裁決是否需要另外查證租客視角的頁面標題。
21. `jgb/D/contract-create-estate-completeness-requirement`：幫助中心 landlordonboarding04lease_zh-Hant.html FAQ 寫「未刊登的物件代表物件還在編輯中，並不會顯示在公開廣告也無法新增合約」，但 app/Http/Controllers/ContractController.php 顯示 2024/11/13 已將建約條件由『物件已刊登（is_open）』改成『物件必填欄位齊全（isCurrentDataCanCreateContract）』，舊的判斷條件已經停用不再生效。兩者是否等價（欄位填齊是否等同已刊登）未經查證，交回裁決。
22. `jgb/D/contract-list-row-gear-actions`：小齒輪動作（編輯合約／刪除合約／取消簽名／取消續約／取消提前解約／點交物件等）在 ContractController.php index() 內依合約狀態組成陣列，本細目只列出最常見的幾種，完整清單依合約狀態、身分、權限而異，未逐一列舉。
23. `jgb/D/contract-edit-tabs-overview`：「稅與發票」「帳單設定」等其他選填分頁是否也有類似的一般團隊預設不顯示的隱藏規則，本細目未逐一查證每個選填分頁，只確認了租金調幅設定這一項，交回裁決是否需要逐項查證。
24. `jgb/D/contract-rentbasic-template-and-dates`：幫助中心 landlordonboarding04lease_zh-Hant.html 說「內政部所規範的五種合約範本」（且列舉的是原房東中文版／包租業中文版／代租代管中文版／英文版／英越文版共 5 個名目），但程式（app/Http/Controllers/ContractController.php 的範本組裝邏輯＋config/contract.php 的範本標籤）顯示一般團隊實際可選 12 種、個人房東身分可選 4 種，兩者皆非 5 種；文件與程式衝突，交回裁決以何者為準。
25. `jgb/D/contract-building-transcript-optional`：「不會刊登在網頁廣告上」的原句出自社宅合約教學頁對物件建立步驟中的建物謄本欄位，用在一般合約「建立與編輯」分頁的建物謄本（buildingTranscript/General.vue）上屬同名同性質欄位的合理外推，未直接對到一般合約分頁的說明文字，列此供覆核。
26. `jgb/D/contract-additional-convention`：src/pages/contracts/edit/additionalConvention/Index.vue 另外還有一句提示「補充條款至多僅限 1 頁 A4 內容，請務必執行「預覽結果」以確認最終呈現。」，跟本細目已收錄的「最多 50 行、每行 50 字」是不同的限制描述（前者是排版後的頁數提示，後者是輸入框的字元數上限），兩者可能同時成立（字數在上限內仍可能因排版超過 1 頁），交回裁決是否要在正本中一併說明兩種限制描述的關係。
27. `jgb/D/social-housing-building-detail`：幫助中心只列出「現況補充」為建物標的分組下的一個分頁名稱，沒有針對這個分頁本身的欄位/規則另外撰寫說明文字，本細目暫未補上該分頁的細節內容，交回裁決是否需要另外查證。
28. `jgb/D/social-housing-notary`：幫助中心 Landlordonboarding09Socialhousing_zh-Hant.html 說「公證是必要的程序，故無法於線上即完成簽約」，但 src/pages/contracts/edit/publicNotary/SocialHousing.vue 有 t('不辦理公證理由') 欄位，文案也寫「租賃雙方因以下事由同意不辦理公證者，視同自願放棄公證費申請之權益」，顯示程式上其實存在『同意不辦理公證』的路徑（代價是放棄公證費補助），跟幫助中心『必要程序、無法線上完成』的說法不完全一致，交回裁決是否已過期或屬於例外選項。
29. `jgb/D/social-housing-charter-sublet-tab-hiding`：社宅合約範本其實有三個值：management（代租代管）、charter（包租包管）、sublet（轉租）；useEditStore.js 只對 charter／sublet 有額外拿掉分頁的規則，grep 不到 'management' 這個字串，研判選「代租代管」範本時看到的是完整分頁，未逐一查證交回裁決是否需要補一條說明。
30. `jgb/D/contract-invite-and-review-period`：app/Http/Controllers/Internal/ContractWriteController.php 另有一條寫死 72 小時（+72 HOUR）的路徑，數值恰好與預設值相同，但走的是內部/API 寫入流程而非本細目描述的主要送出邀請流程，本細目未收錄此路徑，交回裁決是否兩條路徑需要分開說明。
31. `jgb/D/contract-sign-flow-steps`：isGTBContract（src/entry/contract-sign.js computed）在 resources/views/contract/sign.blade.php 裡有 11 處消費端，會控制「下一步，前往簽名」按鈕、承租方身份證明文件影本必填星號、實際入住人／履約保證金退款整個區塊、電子簽約圖章區塊，不是未接線的死碼。GTB 這個範本代號本身，程式裡除了一則註解「// GTB 大翰」（src/pages/contracts/edit/_methods/getFormDataForStepDone.js）外，找不到把它翻譯成正式產品用語的地方，交回裁決 GTB 契約在商業上該怎麼向使用者稱呼或介紹。
32. `jgb/D/contract-esign-no-extra-fee`：這只證明系統內沒有簽章計費機制，不證明 JGB 方案價目表沒有把電子簽章列為方案內容——方案內容以 /pricing 頁為準，售前不應直接報價。
33. `jgb/D/move-out-timing-window`：幫助中心 landlordonboarding04lease_zh-Hant.html 只說「租約將於30天內到期或是已解約之歷史合約，可進行點退」，沒有明確講到期日之後是否有上限；程式 app/Contract.php canMoveOut() 的上界判斷式 `$now > INF` 恆為 false（即無上限），下界仍是到期日前 30 天，兩者不衝突，但幫助中心未提及『無上限』這件事，列此供覆核是否需要在對外說法補充。
34. `jgb/D/renew-data-carryover-rules`：本細目未查證續約流程是否允許直接修改租金金額（rent），只確認到繳費週期/帳單週期設定與出租承租方聯絡資料的更新規則，交回裁決是否需要另外查證「續約可否改租金」。
35. `jgb/D/contract-thinkcloud-esign-service`：此頁面（雲想科技簽署頁面）在骨架中被歸類於「租約公證」粗目，但依程式內容，它實際承載的是 Thinkcloud 電子簽署 iframe，功能上更接近『簽約與合約檢視』的簽署機制本身，跟公證（notary）是否辦理是兩件事；本細目依骨架既定分類撰寫內容真實描述其功能，未強行改寫成公證服務，是否要調整粗目歸屬交回裁決。
36. `jgb/E/bill-actions-progress`：本條講的是單張帳單齒輪選單（`genSingleActions`，約行 1578：[退至應到帳／移至已到帳／開立發票]）；帳單總表勾選『多筆待對帳帳單』時，批次操作列走的是另一段靜態設定（`bulkActions` computed，約行 1255），那裡待對帳狀態只組出 [移至已到帳／開立發票] 兩個動作，沒有「退至應到帳」，跟單張齒輪選單不完全一樣。
37. `jgb/E/bill-list-keyword-search`：「合約帳單」（contractChain）在程式裡的中文註解寫「僅供合約列表齒輪深連結顯示，不加入 values 下拉」，但它其實跟其他 8 個選項一樣被放進同一份 `keyword_for.values` 白名單陣列，畫面下拉選單實際上會出現這個選項；註解與行為不一致，本條以程式實際行為（9 個選項都在下拉）為準，不選邊採信註解。
38. `jgb/E/bill-fee-item-rules`：錯誤文案寫『當期度數必須大於上期度數』，但實際判斷式是嚴格小於（<）才報錯，等於上期度數（度數 0）不會報錯——文案與判準不一致，待業主確認何者才是正確設計。
39. `jgb/E/bill-sheet-report-title`：整個前端程式碼裡找不到任何連到 `bills.sheet` 路由（`/bills/sheet`）的連結或選單項目，只有路由定義本身跟頁面自己會出現這個路由名稱；目前不確定使用者實際上是從哪個入口進入這個頁面（幫助中心也查無相關頁面說明），記為待裁。
40. `jgb/E/bill-sheet-report-title`：頁面右上角「下載」只是文字、沒有綁任何動作；連同沒有入口，疑似整頁尚未接線，待裁是否列入大綱。
41. `jgb/E/bill-sheet-two-views`：頁面本身沒有任何按鈕或下拉選單可以切換 `rowType`：程式裡這個參數只被讀取（`route.query.rowType`），整份程式碼裡沒有任何地方對它賦值或用 `router.push` 帶這個參數導向；要看哪一種檢視必須靠外部帶的網址參數決定，畫面上沒有切換入口，且目前找不到任何連到這個頁面的入口（見 `bill-sheet-report-title` 的 open_question）。
42. `jgb/E/bill-sheet-download-button`：查遍 src/pages/bills/sheet/Index.vue，這個「下載」文字跟它旁邊的下載圖示所在的整個 <div> 都沒有找到任何 @click／onClick 綁定，無法確認按下去實際會做什麼（甚至可能目前沒有接線）。回答使用者「按下去會下載什麼格式」之前，需要業主或工程確認這顆按鈕是否已經上線可用。
43. `jgb/E/balance-invoice-monthly-invoice-table`：「物件」「租客」「空房」三個欄位在 InvoiceTable.vue 是被整段 Vue 註解（<!-- -->）包住的死碼，畫面實際不會顯示——已排除，不寫入句子。
44. `jgb/E/balance-invoice-timing`：差額發票的使用目的／是否排除租客端，程式與幫助中心都查無明文說明（幫助中心沒有差額發票頁面），只能從『這一整個功能群組的頁面都在房東側路由、沒有租客可進入的入口』推斷，未直接寫入句子。
45. `jgb/E/newebpay-precondition`：程式判斷條件只檢查『手機號碼欄位是否為空』(empty($this->role->user->phone))，但錯誤訊息文字寫的是『請先完成手機號碼驗證』——沒有另外檢查手機是否已通過驗證流程，訊息文字與實際判準不一致，待業主確認何者才是正確設計。
46. `jgb/E/newebpay-payment-methods`：「開通帳號」（addMerchant，UserController.php）給的付款方式清單只有 6 種，沒有「超商條碼」；但另一支給編輯畫面用的「取得金流廠商設定」（getPaymentVendor，UserController.php）付款方式清單有 7 種，多了「超商條碼」（PAYMENT_CVS_BARCODE_KEY）。兩份清單是否本來就該一致、或「超商條碼」本來就是開通後才會在編輯畫面出現的選項，程式與幫助中心都查無明文說明，記為待裁。
47. `jgb/E/payment-gateway-withdrawal`：國泰世華／永豐銀行／中國信託的提領方式與審核工作天，幫助中心原文標註「待業務提供後補寫」，目前查無資料，需業主/業務補齊後才能回答。
48. `jgb/F/repair-status-tabs`：「封存」這個狀態實際的使用情境（例如什麼樣的修繕單會被封存、跟其他狀態相比差異是什麼）程式與幫助中心都沒有進一步說明，需業主補充。
49. `jgb/F/repair-status-tabs`：程式裡另外定義了一個「進行中」狀態常數（Repair::PROCESS），但它不在總表這五個分頁對應的狀態清單裡，程式裡也沒有找到任何地方會真的把一張修繕單設成這個狀態——不確定這是還沒串接的功能、還是已經停用的舊狀態，需業主確認。
50. `jgb/F/repair-move-status-from-list`：「結單」跟「封存」兩個分頁在程式的權限判斷與移動選單邏輯上完全相同（見上面的移動邏輯），程式碼裡沒有找到任何額外規則差異；兩者在業務上除了名稱代表的意義（結單＝流程走完並與租客確認、封存＝收起來不常看）之外是否還有其他差別，需業主確認。
51. `jgb/F/repair-move-status-from-list`：齒輪按鈕的文案預設是「編輯＆查看」，只有在目前登入者被判定為大房東（isBigLandlord）或是房東方裡「只能看不能編」的經理人身分時才會變成「查看」；租客分支的程式碼並沒有另外針對租客身分把文案降級成「查看」，只沿用同一顆預設變數。程式裡沒有追到 isBigLandlord 這個判斷式對租客登入的回傳值，所以無法確認租客的齒輪文案是不是永遠固定顯示「編輯＆查看」、完全不會出現「查看」，需業主確認。
52. `jgb/F/repair-view-only-roles`：幫助中心的修繕教學不管實際權限是什麼，一律把這顆齒輪按鈕稱為「查看」（例如安排修繕、完成修繕教學都寫「選擇【查看】」），但程式預設的按鈕文字其實是「編輯＆查看」，只有大房東或只有顯示所屬權限的經理人才會看到「查看」兩個字；文件用語跟預設畫面不一致，需業主確認要不要更新教學文字。
53. `jgb/F/repair-apply-flow-and-entry`：幫助中心教學稱最後一步按鈕是「申請報修」，程式畫面上這顆按鈕的文字實際是「申請修繕」（見 repair.constant.ts），兩邊用語不一致，需業主確認何者為準、要不要統一。
54. `jgb/F/repair-apply-category-item-other`：畫面用一個固定的分類 id（enum Categories.OTHER = 11）判斷要不要顯示自訂名稱欄位，但程式碼裡找不到任何字串證據證明資料庫裡 id 11 這筆分類目前真的叫「其他」——這個對應只存在於前端寫死的數字，需業主查證資料庫內容或提供對應說明。
55. `jgb/F/repair-apply-detail-fields`：「通知及同步租客」開關跟「緊急修繕」勾選框都只用 :model 綁定（元件實際的 prop 叫 modelValue），沒有接 v-model 或任何 change 事件，畫面上看得到、點了卻沒有效果；這會導致房東方申請修繕時，該張單永遠不會同步進租客自己的修繕單總表（is_notice_tenant 卡在預設值），緊急修繕也永遠送出「非緊急」。這是程式錯誤（bug）而非設計行為，需要業主確認要不要排入修復。
56. `jgb/F/repair-apply-detail-fields`：後端常數 Repair::EMERGENCY_STATUS 定義的註解寫「非緊急」，但 RepairController／UserController／RepairService 等呼叫端全部把它當「緊急」使用（is_urgent = (status === EMERGENCY_STATUS)），External/RepairApiController 甚至直接把它的中文對應寫成「非緊急」，跟 RepairService 裡同一個常數對應「緊急」互相矛盾；命名/註解跟實際用法顛倒，需業主確認正確語意，避免之後改程式的人被常數名稱誤導。
57. `jgb/F/repair-apply-reservation-slots`：「預約時段」欄位在畫面上（RepairDetailItemBlock 的 isRequired）一律顯示紅字必填提示，但實際送出驗證只針對租客身分生效，房東方申請時看到的必填標示跟系統實際行為不一致，需業主確認是要改成非租客也不顯示必填提示，還是要補上驗證。
58. `jgb/F/repair-apply-photo-limit`：說明文字把「照片至多 10 張」跟「影片最長 30 秒或 100MB」寫在同一句，但程式裡找不到證據顯示這是同一個總額度、以先到的限制為準——比較像是照片、影片各自獨立的兩條限制。這句話該怎麼理解需業主確認。
59. `jgb/F/repair-edit-amount-visibility`：修繕單裡的「結算金額」目前看起來只是紀錄用的文字欄位，程式碼裡沒有找到它跟帳單模組之間的任何串接，也就是說填了金額不會自動產生一筆帳單給房東或租客；這是否符合預期（例如帳單是另外手動開立），需業主確認。
60. `jgb/F/repair-edit-share-to-vendor`：幫助中心把這個分享入口叫做「分享主頁」，但程式畫面上這個區塊的標題是「分享訊息」、按鈕是「分享」、彈窗標題是「分享修繕申請單」，三處都沒有「分享主頁」這個字串，用語對不上，需業主確認要不要統一。
61. `jgb/F/repair-share-public-link`：幫助中心的修繕教學裡完全沒有提到分享連結不需要登入、任何拿到網址的人都能看到報修者聯絡方式與廠商電話這件事，程式行為（完全公開、無身分核對）跟文件揭露的落差算不算需要補充提醒，需業主確認。
62. `jgb/G/power-meter-invoice-tab-fields`：這個細目原本的補件指示要求記錄「出租方統一編號」「稅別」「承租方統一編號」「買受人名稱」這幾個欄位為現有功能，但在釘住的 commit 上，這些欄位（含對應的 script 變數）全部被註解掉（ticket #14336：2024-09-04 PM 要求拿掉「出租方統編」相關欄位），畫面上完全不會渲染、也送不出資料；本細目已改為記錄程式現況（開立發票頁籤目前只剩「是否自動開立發票」一個選項），與原始指示的假設不符，需業主確認這批欄位是否之後有計畫復原、或原始指示依據的是舊版程式／文件。
63. `jgb/G/device-page-shared-list`：房東教學文件（Landlordonboarding08Device_zh-Hant.html）寫明版本更新後系統上僅可操作智慧電表，但程式仍保有完整的門鎖／攝影機／小白盒清單、編輯、開關鎖頁面與路由，兩者是否一致（例如僅隱藏行銷/教學曝光、實際功能仍在）需業主確認。
64. `jgb/G/device-edit-tabs-by-type`：deviceGroup.editable 目前在整理裝置清單資料時固定寫死成 1（程式旁註記「改為總是顯示」），畫面上依這個值鎖住編輯按鈕的機制形同虛設；需業主確認這是刻意讓編輯永遠開放、還是舊有依群組鎖編輯的功能已經廢止但畫面判斷式忘了拿掉。
65. `jgb/G/device-lock-passwords-three-types`：租客共用密碼區塊的畫面文字寫「@{{doorLockPasswords['3'].length}} / 50」暗示上限 50 組，但新增按鈕的 disabled 條件是 doorLockPasswords['3'].length == 10，實際功能上限是 10 組，兩處數字不一致，需業主確認何者才是正確上限。
66. `jgb/G/device-lock-passwords-three-types`：「編輯密碼」按鈕背後的點擊事件與編輯表單都還在（點下去會把整組欄位切成可編輯狀態），但外層 div 標了 :hidden="true"，恆為隱藏、不會渲染在畫面上，使用者沒有入口可以觸發；需業主確認這是刻意下架既有密碼的編輯功能（只留新增/刪除），還是應該拿掉這個隱藏旗標讓它重新可見。
67. `jgb/G/remote-unlock-page`：routes/web.php 在 /unlock/{iotId}/{batch} 這條路由上方標了「// QR code 開鎖」的註解，暗示這個連結原本設計是給 QR code 掃碼用；但門鎖管理的畫面（清單、編輯頁、密碼設定頁）裡都找不到任何產生或顯示 QR code／這個連結的入口，全域搜尋 QRCode／qrcode 也只在其他功能（LINE 預約、VR 拍攝）找到，沒有一處接到門鎖。ToolController::unlock() 的方法註解另外寫著「新北住都 - 現場業務查詢租客user密碼用」，連結碼是用門鎖 id 與建立時間算出來的固定值。這個連結／QR code 目前是由誰、透過什麼管道產生並交給使用者，需業主確認，否則無法在正本上寫「怎麼取得這個連結」。
68. `jgb/H/help-center-trial-form`：`if ('listings.helpCenter'.includes(route.name))` 這個判斷式是固定字串 'listings.helpCenter'.includes(變數)，只有 route.name 完全等於 'listings.helpCenter'（或是它的子字串）時才會成立；'listings.helpCenter.group'／'.post'／'.search' 這些子頁面的路由名稱反而不會命中。這看起來像是原本想寫成 route.name.includes('listings.helpCenter')（涵蓋所有幫助中心子頁）卻寫反了，還是刻意只在首頁觸發，需業主確認，關係到這句話要不要修正成『所有幫助中心頁面都會倒數』。
69. `jgb/I/pricing-free-trial-feature-scope`：src/pages/listings/pricing/parts/FAQ.vue 的『免費方案和體驗方案的差別？』問答明講免費方案『擁有智能合約及自動對帳功能』，但實際彈出的免費試用清單（LightboxFreePlan.vue）把自動對帳列在不支援清單裡（只是加註可申請藍新、中信）；兩份畫面文案互相矛盾，未能判斷哪一份是最新版本，交由業主裁決。
70. `jgb/I/pricing-free-vs-experience-plan`：本題的『免費方案』與 jgb/I/pricing-free-trial-eligibility 描述的自動贈送方案（app/User.php 建立房東身分時給的 plan_name='免費方案'）用的是同一個方案名稱，但 FAQ.vue 這則問答與 LightboxFreePlan.vue 彈窗的功能敘述在自動對帳等項目上互相矛盾（見 jgb/I/pricing-free-trial-feature-scope 的 open_questions），因此本題內容以 FAQ.vue 原文照實呈現，不代表已核實其功能清單。
71. `jgb/I/pricing-plan-price-basis`：app/Helper.php 的 get_plan_price() 只定義計算邏輯，實際的入門／熱門／專業／企業方案單價與基本費金額存放在資料庫 plan_estate_prices 表（透過 Redis 快取），不在程式碼裡，因此每個級距具體收費多少無法從程式碼直接列出，需要查詢當時資料庫內容才能確認。
72. `jgb/I/subscription-my-plan-page`：右側『溢繳費用』欄位顯示的金額是使用者累積的訂閱溢繳金餘額，實際的計算與使用時機見 jgb/I/subscription-plan-change-billing。
73. `jgb/I/payment-vendor-options-overview`：本題手續費／設定費數字來自幫助中心文章 qa27（https://www.jgbsmart.com/help/post/qa27，編輯日期 2026/06/30），未在 jgb2 程式碼中找到對應常數可交叉核對，僅能確認文件本身存在且描述具體，未能查證這些費率在系統上線時是否已經調整過。
74. `jgb/I/payment-vendor-options-overview`：適用範圍的細節（哪個身分／方案不能開哪個金流商）另立一條 jgb/I/payment-vendor-eligibility-by-role-and-plan，本題只點出有此限制存在，不重複展開。
75. `jgb/I/payment-newebpay-setup-details`：『三個工作天以上』的審核時間只在幫助中心文章 qa27 找到，jgb2 程式碼裡沒有找到對應的常數或後端排程可交叉核對，只能確認文件本身這樣寫。
76. `jgb/I/payment-vendor-edit-after-binding`：Cathaybk（國泰）明細頁同時帶 isDisabled={true} 又帶 onSubmit／onChange，兩者如何配合放行編輯（例如是否有另一個欄位或狀態解鎖輸入框）未在讀到的檔案範圍內看到，僅能確認它是唯一被接上重新送出邏輯的金流商。
77. `jgb/I/payment-permission-menu-visibility`：文件與程式對這個行為的歸因不一致，未選邊：qa23 把【收款設置】【訂閱方案】選單消失歸因於沒有開啟「編輯團隊」權限；但程式裡側邊欄選單（app/Role.php）這兩個項目各自對應獨立的查看權限旗標 show_role_payment（『查看收款設置』）與 show_role_subscription（『查看訂閱方案』），而且權限清單（app/Character.php）裡「編輯團隊」（edit_role）、「編輯收款設置」（edit_role_payment）、「編輯訂閱方案」（edit_role_subscription）是三個各自獨立的權限鍵，跟 show_role_payment／show_role_subscription 這兩個查看權限鍵又是不同層級。是否 qa23 所指的『編輯團隊』實際上涵蓋或連動這兩個查看權限，還是文件用詞不精確，需要業主或熟悉權限矩陣的人確認。
78. `jgb/I/task-manager-purpose`：任務列表頁（taskManagement/Index.vue）的說明文字寫「指定週期的前三十天完成單據的開立」，但新增／編輯任務頁（taskManagement/edit/Index.jsx）寫的是「觸發時間前 45 天完成單據的開立，系統後續會在觸發時間的 30 天前、15 天前寄送通知信」——兩個頁面對『提前幾天開單』給的具體天數不一致（30 天 vs 45 天），未能判斷哪一份是最新版本，交由業主裁決，因此標題不寫出具體天數。
79. `jgb/I/notification-mail-settings`：通知信設定頁面（notificationMail/Index.jsx）除了上述說明文字外，實際列出各通知類型並讓使用者新增副本信箱的清單區塊（state.typeOptions 抓回資料後應該渲染的地方）目前是空的 <div>，也 import 了 TaskItem／TableHead 元件卻沒有在畫面上使用，無法確認副本信箱的新增介面在目前版本是否已完整實作；另外，目前找不到任何現行（未被註解）的選單或連結會導向這個頁面，只能透過直接輸入網址進入。
80. `jgb/I/homepage-presales-assistant-visibility`：只讀了 listings/Home.vue 這一個檔案，不能排除同一個小幫手元件是否在其他官網頁面（例如價格頁、產品特色頁）用不同條件掛載並在正式環境顯示；此處只確認首頁這一支檔案目前的掛載條件是排除正式環境。
81. `jgb/I/tcloud-link-invalid-cases`：程式裡的註解寫「1. 找不到對應id 2. 該訂單已被付款」暗示已付款的訂單也會被導回首頁，但實際判斷式只檢查資料是否存在（empty($customerTCloud)），並沒有另外針對「已付款」的狀態做導回處理——已付款的訂單目前仍會正常顯示頁面並標示「已付款」，這條註解與實際判斷式所寫的邏輯不一致，未能查到近期改動紀錄能解釋這個落差。

## Plan 9.14 追加：真實客服問句對源後仍定不了的（82～132）

> 來源：Plan 9.14 S3 對 145 個真實問句缺口格的對源盤查（jgb2 釘住 commit `b2ee2ac382ce`）。只寫一般化主題與原因，⛔ 不含客戶原文；對應的 `cell_id` 在 repo 外 run 目錄。沒有細目的用粗目 id（`inputs/coarse-ids-20260921.md`），分批時查無粗目的標「未歸粗目」。82～132 是盤查窮盡後的剩餘。（曾列 133～137 的 5 格是證據未過或被推翻的格，不是業主題；已由主 session 重新對源解決，改記在帳本。）已對源成立的事實見 `docs/knowledge/jgb-product-facts.md#p914`。

82. `E-bill-list`：〔9.14 真實問句〕收據自動寄送的過去規則——程式只反映現行版本，過去某時點的寄送設定無法從釘住 commit 重建，要查當時設定或客服紀錄。
83. `G-device-page`：〔9.14 真實問句〕舊門鎖系統的密碼資料在遷移時是否保留——程式未見任何舊資料匯入腳本；屬一次性歷史遷移，要當時負責人確認。
84. `C-team-storefront`：〔9.14 真實問句〕業者自有網站該放哪些內容——屬業者自身行銷決策、非產品功能；要不要有客服標準說法待裁。
85. `D-contract-edit-general`：〔9.14 真實問句〕多人簽約功能的未來規劃——現行已可加其他租客（`p914-contract-additional-tenants`），未來是否調整屬產品路線圖。
86. `G-power-meter`：〔9.14 真實問句〕更換電表的申辦流程與前置條件——幫助中心只說電表綁定由 JGB 業務協助，程式未見虛擬帳號與電表申辦的前後置關聯；屬人工業務流程。
87. `E-balance-invoice`：〔9.14 真實問句〕收支表跨年度的前期結餘，以及整年預收租金的開票——「前期結餘」重算程式整段被註解、不在上線版本；開票問題屬稅務與開票政策。
88. `E-bill-list`：〔9.14 真實問句〕排定發送的帳單順序與解約後草稿——程式可證：超出合約期間的帳單只被擋下自動寄送、不刪除；批次寄送依 id 順序，無依起租日排序的選項。剩下「排定發送日該選哪個基準」屬操作建議。
89. `E-virtual-account`：〔9.14 真實問句〕簽約進行中才申請虛擬帳號的影響——虛擬帳號綁定角色是獨立步驟，結果取決於當下角色建立的時序，靜態程式判定不了。
90. `E-virtual-account`：〔9.14 真實問句〕虛擬帳號綁定異常的處理——查詢、停用、補救只在 JGB 內部客服後台，業者端沒有自助修復流程；對外說法（請洽客服）待裁。
91. `D-contract-edit-general`：〔9.14 真實問句〕簽約日晚於起租日時對主管機關的說明——屬主管機關認定與客服公版說法，程式無從回答。
92. `未歸粗目`：〔9.14 真實問句〕客服紙本資料異動申請書的填寫規定——程式與幫助中心皆無此表單；屬 JGB 內部作業規範。
93. `未歸粗目`：〔9.14 真實問句〕逾期的虛擬帳號能否重新產生——重新產生只在內部客服後台，業者端無自助入口；同題另兩個子問（逾期帳號是否仍可收款、年繳帳單可否拆年度）未追完。
94. `C-estate-edit`：〔9.14 真實問句〕租金補貼申請表的地址欄填法——屬補貼主管機關的申請規定，系統無對應的轉換邏輯。
95. `E-balance-invoice`：〔9.14 真實問句〕差額發票群組內帳單跨期異動的影響——結果取決於該帳號各帳單當下狀態與操作順序，要個案資料才判定得了。
96. `D-renew`：〔9.14 真實問句〕提前續約使用方案時的折抵金額——程式未見單一公式，取決於當下生效的方案設定，屬計費政策。
97. `E-balance-invoice`：〔9.14 真實問句〕差額群組裡的特殊記帳安排（為對外不存在的租客建約、不開發票）是否可行——程式沒有這類旗標，會不會影響收支表正確性要熟悉差額群組的人判斷。
98. `E-virtual-account`：〔9.14 真實問句〕租客銀行的匯款上限與虛擬帳號——系統對虛擬帳號沒有金額上限檢查，是否受限取決於租客往來銀行。
99. `D-contract-edit-general`：〔9.14 真實問句〕同一合約列多名租金補貼申請人的寫法——屬政府補助規定，系統沒有這條規則。
100. `D-contract-edit-general`：〔9.14 真實問句〕出租方身分能否為單一合約改成屋主——出租方資訊是團隊／帳號層級設定，不在單一合約切換；該用哪個帳號簽屬業者營運安排。
101. `D-contract-edit-general`：〔9.14 真實問句〕二房東該選哪一種合約類別——系統只有原房東／包租業／代租代管三個選項，沒有二房東的對應；屬業態的法律定性。
102. `E-payment-onboarding`：〔9.14 真實問句〕資金流向與稅務申報風險——屬稅務機關判斷，非產品行為。
103. `D-contract-sign-view`：〔9.14 真實問句〕簽名與登記姓名不一致的法律效力——屬法律諮詢，程式不判斷。
104. `E-social-housing-report`：〔9.14 真實問句〕系統是否適用某個地方政府的社宅方案——系統有社會住宅用途類別；對特定方案的適配屬產品政策判斷。
105. `G-power-meter`：〔9.14 真實問句〕電表線下儲值後多久恢復供電——系統以排程或即時工作向廠商對帳確認儲值，實際供電時間取決於電表硬體與通訊；對外可講的時間範圍待裁。
106. `C-estate-edit`：〔9.14 真實問句〕環景拍攝設備是否要每個物件各買一組——導購頁沒有規定，屬硬體採購政策。
107. `C-estate-edit`：〔9.14 真實問句〕物件多項欄位的填法與金流銀行審查（謄本、坪數可否留空等多個子題）——謄本是否影響銀行審查屬第三方政策；其餘子題彼此獨立，要拆題。
108. `I-pricing`：〔9.14 真實問句〕加購物件額度要找哪個窗口——程式與幫助中心都沒有導流說明，屬銷售流程。
109. `D-contract-edit-general`：〔9.14 真實問句〕一個物件多個房號的建檔方式與租期重疊——系統只提供欄位，建檔規範屬操作政策。
110. `E-bill-list`：〔9.14 真實問句〕收支狀態各分類筆數對不上——畫面只顯示後端算好的數字，要查該帳號當時的帳單資料。
111. `E-bill-list`：〔9.14 真實問句〕客服可否代業者重發催繳通知——程式沒有客服代發機制，是否受理屬內部支援政策。
112. `E-virtual-account`：〔9.14 真實問句〕轉帳限額，以及同一個虛擬帳號可否多人共用匯款——限額是銀行政策；共用規則在需求文件裡沒有定義。
113. `D-contract-sign-view`：〔9.14 真實問句〕租客帳號未顯示業者發出的合約邀請——取決於帳號與合約綁定的實際資料（可能是多個帳號），要查個案。
114. `E-bill-list`：〔9.14 真實問句〕超商代碼逾期後付款是否入帳——系統不檢查代碼期限，完全依金流商回傳的結果；要向金流商確認其政策。
115. `D-contract-list`：〔9.14 真實問句〕實價登錄新版的上線時程與教學安排——現行已有實價登錄匯出（`p914-real-price-registration`），新版時程屬產品路線圖。
116. `E-balance-invoice`：〔9.14 真實問句〕帳單不在差額發票群組內時 JGB 怎麼處理——系統會把它列進內部「發票異常」盤查名單，處理只在內部後台；對外說法待裁。
117. `E-bill-list`：〔9.14 真實問句〕收據功能的開發時程——屬產品路線圖。
118. `G-power-meter`：〔9.14 真實問句〕抄表資料的匯入時程——屬個案專案排程。
119. `A-notification-settings`：〔9.14 真實問句〕LINE 官方帳號的訊息額度會不會影響帳單通知——程式沒有配額邏輯，額度是 LINE 平台的計費政策。
120. `I-marketing-home`：〔9.14 真實問句〕未來會不會推出原生 APP——現行是瀏覽器使用（`p914-web-not-app`），未來規劃屬產品路線圖。
121. `E-balance-invoice`：〔9.14 真實問句〕合約還沒簽回時能否開發票或收據——發票看合約的開票設定、押金收據看帳單是否已到帳，但簽署狀態會不會連動擋下，找不到單一判斷點，要工程確認。
122. `D-contract-edit-general`：〔9.14 真實問句〕簽約後補加保證人——業者端只有租客簽約流程能加連帶保證人，簽約後補加只在內部客服後台；對外說法（請洽客服）待裁。
123. `未歸粗目`：〔9.14 真實問句〕承租人編碼異動的作業方式——業者端沒有自助改碼的功能，現行做法屬客服內部作業規範。
124. `E-bill-list`：〔9.14 真實問句〕合約異動後新舊帳單與已開發票的封存順序——系統只提供單張封存，正確做法屬會計與發票規則的建議。
125. `G-power-meter`：〔9.14 真實問句〕手動抄表改用第三方雲端電表能否接續歷史度數——系統只有手動輸入與 JGB 電表兩種來源，第三方電表的相容性屬導入政策。
126. `G-power-meter`：〔9.14 真實問句〕電表安裝的工班安排與費用——屬業務與外部工班的商業安排。
127. `G-power-meter`：〔9.14 真實問句〕換錶後新電表的度數起點——度數是廠商硬體的鏡像值、JGB 唯讀，起點取決於廠商安裝作業。
128. `G-device-page`：〔9.14 真實問句〕門鎖磁扣等硬體選配與費用——系統沒有這類欄位，屬設備供應商的商業條件。
129. `E-balance-invoice`：〔9.14 真實問句〕退租帳單的科目名稱如何避免和已計入的預繳租金重複計入收支表——系統依品項名稱是否為「租金」判定是否計入；個案的科目命名屬記帳判斷。
130. `E-balance-invoice`：〔9.14 真實問句〕法人改為自然人後差額發票群組怎麼設——系統沒有身分切換的專用規則，結果取決於個案資料。
131. `E-payment-onboarding`：〔9.14 真實問句〕租客信用卡額度不足時自動扣款怎麼處理——舊的自動扣款指令已停用、不在排程；額度不足時的授權結果取決於金流商。
132. `D-move-out`：〔9.14 真實問句〕退租結算單會不會重複開立發票——取決於該帳單各款項當下的狀態，要個案資料判定。
