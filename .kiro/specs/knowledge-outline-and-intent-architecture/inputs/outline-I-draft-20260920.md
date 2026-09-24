# I 架草稿（jgb2 master @ b2ee2ac382ce；粗目 6、細目 54、句 145）

讀法：每個粗目底下一條細目答一件事；句子後的〔〕是來源檔（程式或幫助中心頁）；「待查」是文件與程式衝突或程式裡查不到的，未選邊。

## 方案、價格與免費試用（11 條；頁：listings.pricing、listings.pricing.TrialPlan）

### JGB 有哪些方案？（免費試用、體驗方案、入門／熱門／專業四級距、企業方案）
- 講法：有哪些方案／方案分幾種／方案怎麼選／價格方案介紹／哪個方案適合我
- 給誰看：property_manager、prospect
- 方案頁把付費方案分成「體驗方案」「入門方案」「熱門方案」「專業方案」四個級距，其中入門方案涵蓋 50、100、150 個物件，熱門方案涵蓋 200 到 450 個物件並標示為最熱門，專業方案為 500 個物件。〔app/Http/Controllers/ApiController.php〕
- 除了頁面上列出的四個級距，另外還提供不綁信用卡的「免費試用」方案，以及只能透過聯繫窗口洽談的「企業方案」。〔src/pages/listings/pricing/parts/PlanAndDevice.vue〕
- 方案價格依物件數量分級計費，頁面上可切換「月費」或「年費」兩種計費週期查看價格。〔src/pages/listings/pricing/parts/PlanForm.vue〕
- 企業方案主打客製化專屬 LOGO 頁與客製化專屬網址頁，是提供給大型企業的解決方案，需點選「深入了解企業方案」導向預約 demo 頁面洽談，頁面上不會顯示企業方案的價格。〔src/pages/listings/pricing/parts/PlanAndDevice.vue〕
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "企業方案" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/Home.vue src/pages/listings/pricing/parts/PlanForm.vue', 'result': "0 hits — '企業方案' never appears as a priced tier cell in the plan-comparison table component", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "企業方案" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/parts/PlanAndDevice.vue src/pages/listings/pricing/parts/CalculatePrice.vue → 3 hits (PlanAndDevice.vue \'企業方案\' title, \'深入了解企業方案\' link; CalculatePrice.vue \'您需要我們的[s2]企業方案[s3]\')'}`

### 免費試用怎麼開始、能用多久？（新建立房東身分自動取得，一個週期後不自動續訂）
- 講法：免費試用能用多久／怎麼取得免費試用／免費方案會自動續訂嗎／試用期多長
- 給誰看：property_manager、prospect
- 免費試用是「不綁信用卡的 30 天試用方案」，點選「免費試用」後導向註冊頁完成註冊即可啟用。〔src/pages/listings/pricing/parts/PlanAndDevice.vue〕
- 系統在建立房東身分（個人房東、企業團隊或社宅房東）時，只要註冊過程沒有帶入優惠代碼，就會自動給予這個免費方案，效期為系統設定的一個週期（目前為一個月），到期後不會自動續訂。〔app/User.php〕
- 個人房東如果是透過優惠代碼連結完成註冊，取得的是優惠代碼指定的方案，而不是這個自動贈送的免費方案。〔app/User.php〕
- 免費方案贈送的方案價格固定為 0，即使使用者取消訂閱也不會產生退款。〔app/User.php〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "\\$role->plan_cycle = " b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/User.php', 'result': '0 — 建立房東身分那段程式（switch ($configRuleKey) 分支）裡找不到任何一行有幫免費方案寫入 plan_cycle 續訂欄位', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "// 不設定 plan_first_ymd 與 plan_cycle 使方案不會續訂" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/User.php → 2，確認兩個建立免費方案的分支都明講刻意不寫入續訂欄位'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "case Role::RULE_KEY_LANDLORD_INDIVIDUAL:" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/User.php', 'result': "1 hit — 個人房東的 case 緊接著檢查 session('promotion')，若沒有優惠代碼（promotion 為空）就沒有 break，直接落入下一個 case（企業團隊／社宅房東）共用的免費方案建立區塊", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "case Role::RULE_KEY_LANDLORD_CORPORATE:" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/User.php → 1，確認緊接在個人房東 case 之後、中間沒有 break 敘述，兩個 case 確實共用同一段免費方案賦值程式'}`
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c "\\$role->plan_price = [1-9]" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/User.php', 'result': '0 — 建立免費方案的兩個分支裡，plan_price 找不到任何一次被賦予非 0 的數字', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c "\\$role->plan_price = 0;" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/User.php → 2，確認同一組欄位確實兩處都寫死為 0（連同註解『以免使用者取消訂閱拿到退款』），對照組能命中'}`

### 免費試用不能用哪些功能？（最多 5 個物件，不支援團隊與門鎖電錶等進階功能）
- 講法：免費方案有什麼限制／免費試用不能用什麼功能／免費方案物件上限／免費試用支援哪些功能
- 給誰看：property_manager、prospect
- 免費試用最多可新增 5 個物件、支援批次物件上傳，並擁有智能合約（內政部最新標準範本）、支援既存合約、一般匯款、自動催繳通知、即時帳務報表、分店管理、租客管理等功能。〔src/pages/listings/template-parts/LightboxFreePlan.vue〕
- 免費試用不支援 720° VR、團隊成員管理、大房東管理、編輯權限設定、智能門鎖、智能電錶等功能。〔src/pages/listings/template-parts/LightboxFreePlan.vue〕
- 免費試用彈窗裡把自動對帳列在不支援的功能，並註記「無法申請國泰、永豐，可申請藍新、中信」，代表這個限制其實只擋國泰與永豐兩家金流。〔src/pages/listings/template-parts/LightboxFreePlan.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "\'720° VR\', null" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/template-parts/LightboxFreePlan.vue', 'result': '1 hit，落在 state.unsupportedList 陣列（開頭在自動對帳等項目之前）第一項，確認 720° VR 是被列在不支援清單，不是支援清單', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nP "(?<!un)supportedList" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/template-parts/LightboxFreePlan.vue → 2 hits（陣列宣告＋.map渲染呼叫，用負向後顧排除 unsupportedList 的子字串誤命中），證明同一個元件真的會渲染一份平行的『支援功能』清單'}`
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/template-parts/LightboxFreePlan.vue | sed -n \'/supportedList: \\[/,/unsupportedList: \\[/p\' | grep -c "自動對帳"', 'result': '0 — supportedList 陣列裡完全沒有出現自動對帳', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/template-parts/LightboxFreePlan.vue | sed -n \'/unsupportedList: \\[/,/^        })$/p\' | grep -c "自動對帳" → 1，確認自動對帳確實落在緊接著的 unsupportedList 陣列裡'}`
- ⚠️ 待查：src/pages/listings/pricing/parts/FAQ.vue 的『免費方案和體驗方案的差別？』問答明講免費方案『擁有智能合約及自動對帳功能』，但實際彈出的免費試用清單（LightboxFreePlan.vue）把自動對帳列在不支援清單裡（只是加註可申請藍新、中信）；兩份畫面文案互相矛盾，未能判斷哪一份是最新版本，交由業主裁決。

### 個人房東與企業團隊方案差在哪？（人員管理四項功能、自動對帳與分店管理起始級距不同）
- 講法：個人房東跟團隊方案差別／團隊方案多什麼功能／企業團隊方案內容／個人跟公司方案不一樣嗎
- 給誰看：property_manager、prospect
- 方案頁目前只會顯示企業團隊身分適用的方案內容與功能比較表，頁面上沒有讓使用者切換成個人房東身分查看內容的入口。〔src/pages/listings/pricing/Home.vue〕
- 系統另外定義了一份個人房東專用的方案比較表：人員管理相關的「團隊成員管理」「編輯權限設定」「團隊資訊」「進階設定」四項功能，個人房東的入門、熱門、專業、體驗方案全部都不提供；企業團隊則除了體驗方案外，入門、熱門、專業方案都提供這四項功能。〔app/Http/Controllers/ApiController.php〕
- 自動對帳在個人房東的比較表裡，入門、熱門、專業、體驗方案顯示的都是文字說明「無法申請國泰、永豐可申請藍新、中信」；企業團隊的比較表裡，入門、熱門、專業方案顯示為打勾支援，只有體驗方案不支援。〔app/Http/Controllers/ApiController.php〕
- 分店管理在個人房東的比較表裡，體驗、入門、熱門、專業方案全部支援；企業團隊的比較表裡則是體驗方案不支援，入門、熱門、專業方案才支援。〔app/Http/Controllers/ApiController.php〕
- 大房東管理在兩份比較表裡的支援情形完全相同：體驗方案不支援，入門、熱門、專業方案都支援。〔app/Http/Controllers/ApiController.php〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "planRole" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/Home.vue src/pages/listings/pricing/parts/PlanForm.vue src/pages/listings/pricing/parts/PlanSlider.vue', 'result': '6 hits total across the three files — Home.vue 只有第 31 行『state.planRole = landlord_corporate』這一處賦值，其餘 5 個命中全部落在 PlanForm.vue／PlanSlider.vue 對 state.groups[state.planRole] 的唯讀取用，找不到任何一處把 planRole 改成 landlord_individual 或提供切換按鈕', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "state.displayTable = e.value" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/parts/PlanForm.vue → 1，確認同一個檔案裡『月費／年費』這個真的有切換開關的狀態，寫法上跟 planRole（只有唯讀取用、無賦值點）明顯不同'}`
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/ApiController.php | sed -n "/\'landlord_individual\' => \\[/,/\'landlord_corporate\' => \\[/p" | grep -A20 "\'label\' => \'團隊成員管理\'," | grep -c "\'tick\' => 1,"', 'result': '0 — 個人房東表裡團隊成員管理／編輯權限設定／團隊資訊／進階設定四個欄位的四個級距全部是 tick=0', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/ApiController.php | sed -n "/\'landlord_corporate\' => \\[/,\\$p" | grep -A20 "\'label\' => \'團隊成員管理\'," | grep -c "\'tick\' => 1," → 3，企業團隊表同一欄位的入門／熱門／專業三個級距是 tick=1'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/ApiController.php | sed -n "/\'landlord_individual\' => \\[/,/\'landlord_corporate\' => \\[/p" | grep -A20 "\'label\' => \'自動對帳\'," | grep -c "\'cellType\' => \'tick\'"', 'result': "0 — 個人房東表自動對帳的四個級距全部是 cellType='text'（文字說明），沒有任何一格是 tick 型態", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/ApiController.php | sed -n "/\'landlord_corporate\' => \\[/,\\$p" | grep -A20 "\'label\' => \'自動對帳\'," | grep -c "\'cellType\' => \'tick\'" → 4，企業團隊表同一欄位四個級距全部是 tick 型態'}`

### 免費方案與體驗方案差在哪？（前者系統贈送 5 個物件，後者每月付費可續訂 10 個物件）
- 講法：免費方案跟體驗方案差在哪／免費方案跟體驗方案哪裡不同／體驗方案是免費的嗎／免費方案可以續訂嗎
- 給誰看：property_manager、prospect
- 免費方案是提供給每一個新創身份的測試方案，在一個月的測試期間內可以創建 5 個物件，並擁有智能合約及自動對帳功能。〔src/pages/listings/pricing/parts/FAQ.vue〕
- 體驗方案是提供給想要數位轉型的短期試用方案，在方案期限內可以創建 10 個物件，同樣擁有智能合約與自動對帳功能，而且可以自行續訂來延長試用期限。〔src/pages/listings/pricing/parts/FAQ.vue〕
- 體驗方案跟其他付費方案一樣，可以在頁面上切換查看「月費」或「年費」兩種計費週期的價格；不像免費方案是系統贈送、價格固定為 0。〔src/pages/listings/pricing/parts/PlanForm.vue〕
- ⚠️ 待查：本題的『免費方案』與 jgb/I/pricing-free-trial-eligibility 描述的自動贈送方案（app/User.php 建立房東身分時給的 plan_name='免費方案'）用的是同一個方案名稱，但 FAQ.vue 這則問答與 LightboxFreePlan.vue 彈窗的功能敘述在自動對帳等項目上互相矛盾（見 jgb/I/pricing-free-trial-feature-scope 的 open_questions），因此本題內容以 FAQ.vue 原文照實呈現，不代表已核實其功能清單。

### 怎麼用物件數量試算方案價格？（50～500 物件拉桿試算，超過 500 個要洽企業方案）
- 講法：怎麼算方案價格／物件數量怎麼換算價格／我有幾間房適合哪個方案／價格試算工具
- 給誰看：property_manager、prospect
- 方案頁提供「計算方案價格」拉桿工具，方案最少始於 50 個物件，拉桿範圍是 50 到 500 個物件、每格間距 50。〔src/pages/listings/pricing/parts/CalculatePrice.vue〕
- 拉桿的「物件」定義為管理的房源數，例如管理五間收租房源就算五個物件。〔src/pages/listings/pricing/parts/CalculatePrice.vue〕
- 拉桿拉到 500（拉桿上限）時，頁面會提示物件數量超過 500 個以上需要洽詢企業方案。〔src/pages/listings/pricing/parts/CalculatePrice.vue〕
- 試算出的價格是根據輸入的物件數量估算，不包含任何適用稅費與加購費用；年繳的折扣已經包含在顯示的年繳價格內。〔src/pages/listings/pricing/parts/CalculatePrice.vue〕
- 選定物件數量後按「選擇方案」，會直接帶著方案、計費週期（月費／年費）與物件數量一起跳轉到訂閱頁面。〔src/pages/listings/pricing/parts/CalculatePrice.vue〕

### 物件額度快滿了會怎樣？（剩 5 個以下觸發提醒，剛好剩 5 個另寄 Email）
- 講法：物件額度快滿了會通知嗎／物件數量快到上限怎麼辦／方案物件用完前有提醒嗎／額度不夠怎麼知道
- 給誰看：property_manager
- 新增物件時，若訂閱中的身分剩餘可新增物件數量在 5 個以下，系統會發送站內通知中心訊息與 Email 提醒即將額滿。〔app/Estate.php〕
- 當剩餘物件數量剛好只剩 5 個時，除了前述提醒，系統會再另外寄送一封 Email 通知使用者接近訂閱方案的物件數量上限。〔app/Estate.php〕
- 這個提醒只在身分目前有生效中的訂閱時才會觸發，沒有生效中的訂閱不會收到這個提醒。〔app/Estate.php〕
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "if (\\$ownerRole->isSubscriptionActive() && \\$remainEstatesCounts <= 5) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Estate.php', 'result': '1 hit — the notice block is nested inside this single if-condition, so isSubscriptionActive()===false skips the whole block and no notice fires', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "Notification::notice(\'will_full_remind_to_subscription\'" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Estate.php → 1 hit, confirming the notice call itself exists inside that guarded block'}`

### 企業方案提供什麼？（客製化 LOGO 頁與網址頁，需另外聯繫洽談）
- 講法：企業方案內容／企業方案怎麼申請／大型企業方案／客製化方案怎麼談
- 給誰看：property_manager、prospect
- 企業方案標榜「客製化專屬 LOGO 頁」與「客製化專屬網址頁」兩項功能，定位為適合大型企業的企業級解決方案。〔src/pages/listings/pricing/parts/PlanAndDevice.vue〕
- 企業方案沒有在頁面上列出價格，要點選「深入了解企業方案」連結導向預約 demo 頁面另外洽談。〔src/pages/listings/pricing/parts/PlanAndDevice.vue〕
- 物件數量超過 500 個（試算拉桿上限）時，系統會提示改為聯繫企業方案。〔src/pages/listings/pricing/parts/CalculatePrice.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/pricing/parts/PlanAndDevice.vue | sed -n "/{ t(\'企業方案\', null, store.state.listingsI18n) }/,/{ t(\'體驗方案\', null, store.state.listingsI18n) }/p" | grep -c "dollarSign\\|trialPlanPrice"', 'result': '0 — 企業方案欄位的內容只有客製化 LOGO 頁／客製化網址頁兩個賣點與『深入了解企業方案』連結，完全沒有出現幣別符號或價格變數', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/pricing/parts/PlanAndDevice.vue | sed -n "/{ t(\'體驗方案\', null, store.state.listingsI18n) }/,/{ t(\'查看體驗方案\', null, store.state.listingsI18n) }/p" | grep -c "dollarSign\\|trialPlanPrice" → 1，證明同一檔案裡緊接著的『體驗方案』欄位確實有用 dollarSign／trialPlanPrice 顯示價格數字，對照之下企業方案欄位沒有這些'}`

### 體驗方案介紹頁講什麼？（每月費用試算、體驗方案資格需求、客戶見證、免費試用／免費諮詢按鈕）
- 講法：體驗方案介紹頁／體驗方案要多少錢／體驗方案資格需求／深入了解企業方案後看到什麼
- 給誰看：property_manager、prospect
- 體驗方案介紹頁的標題文案是「小成本輕鬆管房非夢事」，副標會即時換算並顯示「每月只需 [金額]，JGB Smart Property 就提供您管理房源所需的一切」，金額是用台幣 100 元即時換算成使用者當地幣別。〔src/pages/listings/pricing/TrialPlan.vue〕
- 頁面用三段搭配截圖的功能介紹依序說明物件及廣告管理、線上合約管理、自動金流管理。〔src/pages/listings/pricing/TrialPlan.vue〕
- 頁面中段放了一則客戶見證（愛租屋 執行長），並附一支介紹影片連結。〔src/pages/listings/pricing/TrialPlan.vue〕
- 頁面下段「體驗方案資格需求」列出兩項條件：管理房源時間不到兩年的「新創時期」，以及過去沒有使用過 JGB 平台的「全新客戶」。〔src/pages/listings/pricing/TrialPlan.vue〕
- 頁面上下各有一組「免費試用」與「免費諮詢」按鈕，「免費試用」會開啟免費方案彈窗，「免費諮詢」會另開分頁導向預約 demo 表單。〔src/pages/listings/pricing/TrialPlan.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "getExchangeCurrency(\'TWD\', store.state.siteOptions.dollarSign, 100)" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/TrialPlan.vue', 'result': '1 hit — state.trialPlanPrice 是拿固定台幣 100 元即時換算出來的結果，不是拉桿或方案級距算出來的價格', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "trialPlanPrice: \'-\'," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/TrialPlan.vue → 1，確認這個欄位初始值是佔位符，要等 API 回傳幣別資料後才會被換算覆蓋，證明畫面上看到的金額真的是即時算出來的，不是寫死的字串'}`
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "過去並沒有使用過 JGB 平台" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/TrialPlan.vue', 'result': '1 hit — 這句描述掛在 state.targets 陣列裡『全新客戶』這個項目的 description 欄位', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "管理房源時間不到兩年" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/pricing/TrialPlan.vue → 1，確認同一個陣列裡『新創時期』項目也有對應的 description，兩個資格條件確實都在同一份清單裡'}`

### 方案價格怎麼算、年繳有折扣嗎？（體驗方案月費固定台幣 100 元；一般方案年繳等於 10 個月的月費）
- 講法：方案價格數字／年繳折扣多少／體驗方案多少錢／方案價格從哪裡算出來
- 給誰看：property_manager、prospect
- 體驗方案的月費固定是台幣 100 元，換算成其他幣別後顯示。〔app/Http/Controllers/UserController.php〕
- 入門、熱門、專業等依物件數量分級的方案，實際單價與級距價格是從系統的方案物件價格表讀出來的，不是固定寫死的數字，因此這裡無法列出各級距的金額。〔app/Helper.php〕
- 一般依物件數量分級方案的年繳費用，計算方式是月費乘以 10（等於少收 2 個月的費用）；體驗方案的年繳費用則是月費乘以 12，沒有這個折扣。〔app/Helper.php〕
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Helper.php | sed -n "/if (\\$planEstatePrice\\[\'number_min\'\\] == 10) {/,/basic_price\'\\]\\*12 : 0;/p" | grep -c \'\\*10\'', 'result': '0 — number_min==10（體驗方案）這個分支裡，basic_price 只乘以 12，完全沒有出現 *10 這個乘數', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Helper.php | sed -n "/basic_price\'\\]\\*12 : 0;/,/basic_price\'\\]\\*10 : 0;/p" | grep -c \'\\*10\' → 1，確認緊接著的 else 分支（其他依物件數量分級方案）確實用 *10 計算年繳費用'}`
- 否定查證：`{'sentence_index': 1, 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "basic_price\\|unit_price" b2ee2ac382ce -- app src config', 'result': '只命中 app/Helper.php 的計算式與 UserIdentityMonthlyStat.php 註解，程式內無任何級距金額常數', 'expected_zero': False, 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c "exchange_currency(\'TWD\'" b2ee2ac382ce -- app/Http/Controllers/UserController.php', 'control_result': '1（體驗方案 100 元那行）'}`
- ⚠️ 待查：app/Helper.php 的 get_plan_price() 只定義計算邏輯，實際的入門／熱門／專業／企業方案單價與基本費金額存放在資料庫 plan_estate_prices 表（透過 Redis 快取），不在程式碼裡，因此每個級距具體收費多少無法從程式碼直接列出，需要查詢當時資料庫內容才能確認。

### 物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案）
- 講法：物件額度用滿了／額度滿了不能新增物件／訂閱失效還能新增物件嗎／方案額度用完提示
- 給誰看：property_manager
- 物件列表新增物件、批次匯入物件、社區底下新增物件等多個入口，在送出前都會先檢查目前身分的訂閱是否還在生效中、以及剩餘可新增物件數量是否還夠。〔app/Http/Controllers/EstateController.php〕
- 只要訂閱已經失效，或是剩餘可新增物件數量不足，這些入口都會擋下操作並改成提示使用者方案額度已滿，導向升級方案，而不是真的建立物件。〔app/Http/Middleware/SubscriptionCheck.php〕
- 彈出視窗的標題一律是「已達到數量上限！」，但內文依目前身分是否為有效訂閱中而不同：已訂閱中時內文是「您的 [方案名稱] 最多可上傳 [物件上限] 組物件，目前已到達上限，要升級方案嗎？」，按鈕文字是「前往升級」；沒有有效訂閱時內文是「您尚未訂閱服務最多可上傳 [物件上限] 組物件，目前已到達上限，請先前往訂閱服務，即可享受所有您需要的功能！」，按鈕文字是「我要訂閱」。〔resources/views/layouts/lightbox/general.blade.php〕
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "if (!empty(\\$role) && \\$role->isSubscriptionActive()) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- resources/views/layouts/lightbox/general.blade.php', 'result': '1 hit — 這個判斷式之後才會把 subscribedPlanIsFull 的標題／內文／按鈕文字改成已訂閱版本，証明兩種文案是同一個 lightbox key 依訂閱狀態切換出來的，不是兩個獨立燈箱', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "\\$lightbox[\'subscribedPlanIsFull\'][\'action_link\'][\'text\'] = ___(\'前往升級\');" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- resources/views/layouts/lightbox/general.blade.php → 1，確認已訂閱分支把按鈕文字改成『前往升級』（未訂閱時預設是『我要訂閱』），兩種文案確實不同'}`

## 訂閱、付款與訂單（20 條；頁：users.subscription、users.subscription.chose、users.subscription.unsubscribe、users.orders、users.payment.index、users.payment.add、users.payment.detail）

### 訂閱頁怎麼選方案？（體驗方案、依物件數量拉桿的基本方案、企業方案洽談三選一）
- 講法：訂閱頁怎麼選方案／怎麼變更訂閱方案／選方案時可以選幾種／方案物件數量怎麼拉
- 給誰看：property_manager
- 選擇方案頁提供三種方案：「體驗方案」、依物件數量計價的「基本方案」（涵蓋原本的入門／熱門／專業級距）、以及需另外洽談的「企業方案」（點擊後導向預約 demo 表單）。〔src/pages/users/subscription/Chose.vue〕
- 選基本方案時用拉桿選擇物件數量，範圍是 50 到 500，每格間距 50，價格與方案名稱會隨拉桿即時更新。〔src/pages/users/subscription/Chose.vue〕
- 拉桿不能拖拉到低於目前已上傳的物件數量，如果目前物件數量超過拉桿最小值，拉桿會自動跳到能容納目前物件數的最小級距，並顯示「無法選擇比已上傳物件數量小的方案」的提示。〔src/pages/users/subscription/Chose.vue〕
- 只有目前方案為空、體驗方案或免費方案時，體驗方案選項才能點選；已經是基本方案或更高方案的使用者，體驗方案選項會顯示為灰階樣式且無法點擊。〔src/pages/users/subscription/Chose.vue〕
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "plan.name == \'trial\' && !state.allowTrial" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue', 'result': "1 hit — this expression sets the 'disabled' class on the trial planItem exactly when allowTrial is false", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "allowTrial: computed" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue → 1 hit, confirming allowTrial is a live computed property feeding that class binding'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "state.quantitySlider.error = t(\'無法選擇比已上傳物件數量小的方案\')" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue', 'result': '1 hit — 這段錯誤訊息就掛在監測『拖拉數值 < 已擁有物件數』的 watch 邏輯裡', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "state.quantitySlider.value = Math.ceil(state.userPlan.ownedEstatesQty / 50) * 50" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue → 1，確認同一段 watch 裡真的有把拉桿數值往上修正到能容納目前物件數的最小級距'}`

### 訂閱怎麼扣款？（先試刷 TWD 1 驗證信用卡、藍新金流走 SSL／PCI-DSS）
- 講法：訂閱怎麼付款／訂閱扣款安全嗎／信用卡驗證怎麼跑／確認扣款會怎樣
- 給誰看：property_manager、prospect
- 還沒完成信用卡授權前，付款按鈕顯示「前往授權」；授權完成後之後每次調整方案，按鈕會改成「前往付款」，點擊後彈出「扣款提醒」再次確認才會送出。〔src/pages/users/subscription/Chose.vue〕
- 第一次授權信用卡時，系統會試刷 TWD 1 元確認信用卡有效，約定成功後隨即取消這筆 TWD 1 的扣款，不會真的收這 1 元。〔src/pages/users/subscription/Chose.vue〕
- 付款流程由合作服務商藍新金流提供線上刷卡支付服務，其系統架構採用 SSL 256bit 加密機制，並符合 PCI-DSS 國際安全認證。〔src/pages/users/subscription/Chose.vue〕
- 按下「確認扣款」後會直接更新訂閱方案並執行扣款，頁面會提醒使用者在送出前再次確認方案與金額細節。〔src/pages/users/subscription/Chose.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "系統將試刷TWD 1以確認信用卡有效，成功約定後，會隨即取消TWD 1扣款" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue', 'result': '1 hit — 這段提醒文字只在 state.checkCreditAgreed == false（尚未授權）時顯示', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "state.checkCreditAgreed == false" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue → 1，確認這段『會取消 1 元扣款』的提醒確實綁定在尚未完成信用卡授權的條件下'}`

### 訂閱時發票資訊要填什麼？（二聯式／三聯式、統一編號僅三聯式必填；地址欄目前沒有掛必填檢查）
- 講法：訂閱發票怎麼填／二聯式三聯式差在哪／統一編號要填嗎／訂閱要留Email跟電話嗎
- 給誰看：property_manager
- 訂閱付款頁的發票類型可切換「二聯式」或「三聯式」，兩者共用同一組表單只是欄位開關不同。〔src/pages/users/subscription/Chose.vue〕
- 「買受人」在兩種發票類型下都要填；「統一編號」只有選三聯式時才會顯示且為必填欄位。〔src/pages/users/subscription/Chose.vue〕
- 地址分成國家、縣市、鄉鎮區、詳細地址四欄；畫面上「地址」標題沒有標示必填記號，畫面上的必填檢查與錯誤提示邏輯目前沒有啟用，等於這四個欄位目前實際上沒有被強制要求填寫。〔src/pages/users/subscription/Chose.vue〕
- Email 在二聯式發票時標示為必填，三聯式則非必填；聯絡電話則兩種類型都不是必填欄位。〔src/pages/users/subscription/Chose.vue〕
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -B1 -nF "{{ t(\'聯絡電話\') }}" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue | grep -c after-required', 'result': '0 — 聯絡電話標題 div 上一行沒有 after-required class，確認聯絡電話不是必填欄位', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -B1 -nF "{{ t(\'買受人\') }}" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue | grep -c after-required → 1，確認同一份表單裡『買受人』標題上一行確實帶 after-required class（一律必填），證明抓法能正確命中'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A5 -nF "<AddressComponent2" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Chose.vue | grep -c ":required\\|:errors"', 'result': '0 — Chose.vue 呼叫 AddressComponent2 時沒有傳入 :required 或 :errors 這兩個 prop', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "default: false," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/components/AddressComponent2.vue → 命中多處，其中一處緊接在 required 這個 prop 定義之後，確認沒有外部傳入時 required 預設值就是 false（不顯示必填標記）'}`

### 訂閱優惠碼怎麼用？（輸入後即時驗證，續訂優惠次數沒有設定上限時顯示「終生」）
- 講法：訂閱優惠碼怎麼輸入／優惠碼兌換／續訂優惠次數／續訂優惠可以用多久
- 給誰看：property_manager
- 選擇方案頁可以輸入優惠碼並按「兌換」，系統會即時回覆這組優惠碼是否合法及對應訊息，已套用的優惠碼會列在下方，可以個別移除。〔src/pages/users/subscription/Chose.vue〕
- 訂閱完成後，「我的方案」頁會顯示目前方案的「續訂優惠」折扣金額與「剩餘續訂優惠次數」。〔src/pages/users/subscription/MyPlan.vue〕
- 剩餘續訂優惠次數如果沒有設定，畫面會顯示為「終生」，代表這個優惠沒有次數上限；有設定次數時才會顯示實際剩餘次數。〔src/pages/users/subscription/MyPlan.vue〕
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "coupon_remaining_recurrence_count == null" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue', 'result': '1 hit — 顯示「終生」文字的 v-else-if 條件就是這個欄位沒有值時', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "coupon_remaining_recurrence_count > 0" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue → 1，確認同一個欄位在有設定次數（大於 0）時走的是顯示實際次數的另一個分支，兩個分支互斥'}`

### 我的方案頁看什麼？（方案卡片、付款方式綁定狀態、溢繳費用）
- 講法：我的方案頁面內容／怎麼看目前訂閱方案／溢繳費用是什麼／付款方式在哪裡看
- 給誰看：property_manager
- 「我的方案」頁左側卡片顯示方案名稱、物件數量級距、額外戶數（如果有加購）與方案價格；右側顯示付款方式與溢繳費用。〔src/pages/users/subscription/MyPlan.vue〕
- 若已綁定信用卡會顯示卡別圖示、卡號與到期日；未綁定時顯示「尚未綁定」。〔src/pages/users/subscription/MyPlan.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "{{ t(\'尚未綁定\') }}" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue', 'result': '1 hit — 「尚未綁定」文字掛在 v-if="!(...payment_method?.card_info?.number)" 條件下', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "card_info?.number" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue → 命中多處，確認同一個欄位在有卡號時走的是顯示卡別／卡號／到期日的另一個分支'}`
- ⚠️ 待查：右側『溢繳費用』欄位顯示的金額是使用者累積的訂閱溢繳金餘額，實際的計算與使用時機見 jgb/I/subscription-plan-change-billing。

### 怎麼換綁信用卡？（更新要重新授權並試刷 1 元，變更方案按鈕需要對應權限）
- 講法：怎麼換綁信用卡／更換信用卡要重新授權嗎／沒有權限可以變更方案嗎／變更按鈕按不下去
- 給誰看：property_manager
- 要更換綁定的信用卡，點「更新」會先跳出提醒視窗，說明更換需要重新授權，屆時會試刷一塊錢，按「前往更換」才會繼續流程。〔src/pages/users/subscription/MyPlan.vue〕
- 頁面上的「變更」按鈕只有在使用者具備變更訂閱方案的權限時才可以點擊，沒有這個權限的人看到的是無法點擊的灰階樣式。〔src/pages/users/subscription/MyPlan.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "hasEditRoleSubscriptionPermission ? \'\' : \'disabled\'" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue', 'result': '1 hit — 「變更」按鈕的 class 綁定在沒有權限時會加上灰階樣式，命中該行', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "hasEditRoleSubscriptionPermission = computed" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue → 1，確認這個權限旗標是真的有被計算出來、不是死碼'}`

### 換方案時舊方案沒用完的錢會退嗎？（按剩餘天數比例換算成溢繳金，直接折抵新方案費用）
- 講法：升級方案舊方案的錢退嗎／降級方案會退費嗎／溢繳金怎麼算／換方案生效時間
- 給誰看：property_manager
- 在選擇方案頁重新提交訂閱時，系統會立即生效這次的方案變更，不是等到原方案到期才切換。〔app/Http/Controllers/UserController.php〕
- 系統會依照目前方案「剩餘天數 ÷ 方案總天數」的比例，把原方案未使用完的費用換算成溢繳金，直接折抵這次要繳的金額，折抵不完的部分才會列為應付金額。〔app/Http/Controllers/UserController.php〕

### 取消訂閱會怎樣？（立即停止自動續訂與已授權信用卡，但用到目前效期結束才失效）
- 講法：取消訂閱馬上失效嗎／取消訂閱要選原因嗎／取消訂閱後還能用多久／怎麼取消訂閱
- 給誰看：property_manager
- 取消訂閱前系統會告知：目前訂閱的方案資格會持續到方案到期日當天，到期後才不會自動續訂，屆時也無法再繼續使用 JGB 的所有服務——也就是取消動作立即生效的是「停止自動續訂」，不是立刻停用目前方案。〔app/Http/Controllers/UserController.php〕
- 取消時必須從「我不再需要使用相關服務」「無法解決我遇上的問題」「費用昂貴」「其他」四個原因中選一個才能送出；選「其他」的話還要填寫說明文字，否則「確定」按鈕維持無法點擊的樣式。〔app/Http/Controllers/UserController.php〕
- 送出取消後，系統會清除該身分的自動續約資料與已授權的信用卡約定資料，並寄送 Email 通知使用者。〔app/Http/Controllers/UserController.php〕
- 取消動作能不能送出，看的是目前身分是否已經沒有「自動續約資料」——即使目前仍是有效訂閱中的免費方案（沒有自動續約資料），一樣會被這個檢查擋下、直接跳出系統忙碌的錯誤訊息，不會進入原因選擇畫面；這跟目前方案是否還在生效中無關。〔app/Http/Controllers/UserController.php〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "!state.allowSubmit ?\'disabled\' :\'\'" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Unsubscribe.vue', 'result': '1 hit — 「確定」按鈕的 class 綁定在 allowSubmit 為 false 時會套用灰階不可點的樣式', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "allowSubmit: computed" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/Unsubscribe.vue → 1，確認 allowSubmit 是真的有邏輯在計算（勾選其他時要求說明文字非空），不是寫死的值'}`
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "如果取消訂閱，您目前的方案資格會持續到 [s3] 日，之後將不再自動續訂，屆時您也無法再繼續使用 JGB 的所有服務。" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php', 'result': '1 hit — 這段說明文字只在 isSubscriptionActive() 為真（is_subscribed 非空或有 plan_id）時組出來給前台顯示', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "您目前無訂閱方案" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php → 1，確認同一個函式裡若 isSubscriptionActive() 為否，走的是完全不同、不含『持續到期日』說法的另一段文字'}`
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "// 原本就已經取消訂閱了就不給進來" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php', 'result': '1 hit — 這段註解掛在函式最前面 empty($this->role->plan_extend_ymd) 判斷式上，判斷為真就直接回傳系統忙碌訊息，跟是否為有效訂閱中（isSubscriptionActive）是兩回事', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "empty(\\$this->role->plan_extend_ymd)" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php → 1，確認這個判斷式真的是函式進入點的第一道檢查，且判斷欄位是 plan_extend_ymd 不是訂閱有效狀態'}`
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "public function isSubscriptionActive()" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Role.php', 'result': '1 hit — isSubscriptionActive() 只判斷 is_subscribed 是否非空或是否有 plan_id，完全不檢查 plan_extend_ymd', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "if (!empty(\\$this->is_subscribed) || (isset(\\$this->plan_id))) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Role.php → 1，確認免費方案只要 is_subscribed 非空就會被判定為有效訂閱中，即使沒有 plan_extend_ymd（不會自動續訂）也一樣'}`

### 自動續訂扣款失敗會怎樣？（方案資料整個清空、限額歸零、所有物件立即下架，沒有寬限期）
- 講法：續訂扣款失敗怎麼辦／自動續約失敗會下架物件嗎／沒有信用卡授權會怎樣／續訂失敗有寬限期嗎
- 給誰看：property_manager
- 排程續訂時，如果目前身分已經沒有信用卡扣款授權，或是不符合可續訂的條件（例如沒有首次訂閱日或方案週期資料），系統會直接視同不續訂，把訂閱方案資料整個清空、所有方案限額歸零，並且把目前已上架的物件全部下架；同一支排程如果進行到實際刷卡續訂但扣款失敗，也是走一樣的清空與下架流程。〔app/Console/Commands/AutoRenewSubscription.php〕
- 訂閱方案資料被清空後，方案物件數量、合約數量、團隊成員數量、大房東數量等限額全部歸零，首次訂閱日、方案開始日、結束日、續約日等日期欄位也都被清空，等於整個回到沒有訂閱方案的狀態。〔app/Role.php〕
- 物件下架的範圍是目前所有「刊登中」或「買賣廣告」的物件，會被直接改成非刊登、非上架狀態。〔app/Role.php〕
- 這整個流程沒有任何寬限期或重試機制——系統沒有多留幾天再檢查一次或延後下架的邏輯，扣款失敗或條件不符當次排程就會立即清空並下架。〔app/Console/Commands/AutoRenewSubscription.php〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "if (!\\$role->checkCreditAgreed() || !\\$role->isSubscriptionRenewable()) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Console/Commands/AutoRenewSubscription.php', 'result': '1 hit — 條件不符時緊接著呼叫 clearSubscription() 與 pullOffAllEstate() 後 continue，跳過該身分本次排程剩下的續訂流程', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "如果扣款失敗 則清空訂閱方案資料與下架物件" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Console/Commands/AutoRenewSubscription.php → 1，確認實際刷卡但扣款失敗的分支也是呼叫同一組 clearSubscription／pullOffAllEstate'}`
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -inE "grace|寬限|緩衝|retry|重試" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Console/Commands/AutoRenewSubscription.php', 'result': '0 — 整支排程指令檔裡找不到任何寬限期、緩衝天數或重試相關的字樣或邏輯分支', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "public function handle()" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Console/Commands/AutoRenewSubscription.php → 1，確認這是真的有主邏輯的排程指令檔（不是空檔案漏抓），對照組能命中'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "public function pullOffAllEstate()" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Role.php', 'result': '1 hit — 函式內把符合 is_open!=0 或 sell_is_open!=0 條件的物件全部改成 false', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "\\$estate->is_open = false;" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Role.php → 1，確認真的有把物件狀態改掉的賦值敘述，不是只查詢不動作'}`

### 付款紀錄頁看什麼？（扣款日、訂單編號、付款內容、金額、收據）
- 講法：付款紀錄在哪裡看／訂單紀錄怎麼查／收據在哪裡下載／扣款紀錄列表
- 給誰看：property_manager
- 付款紀錄頁以清單方式列出每一筆已完成扣款：扣款日、訂單編號、「付款內容」、金額、以及「收據」連結；付款內容欄列的是這筆扣款買了什麼——已購買的方案／加購項目名稱（例如熱門方案的加購次數、續訂折扣說明等），加上這筆訂單本身附帶的補充說明文字，沒有任何項目時顯示「無」。〔routes/web.php〕
- 如果目前身分完全沒有付款紀錄，頁面會顯示「目前尚未有任何付款紀錄」。〔src/pages/users/orders/Index.vue〕
- 頁面提示「如果紀錄有疑慮，請聯繫JGB客服」。〔src/pages/users/orders/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "const dataFetcher = reactive(" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/orders/Index.vue', 'result': '1 hit — 緊接著下一行呼叫 /api3/users/orders/list，這條路由對應的是 UserController@getPaymentLogLists，不是 UserController@subscription', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "Route::match([\'get\'], \'/list\', \'UserController@getPaymentLogLists\');" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- routes/web.php → 1，且緊接在 Route::prefix(\'orders\') 群組內，確認付款紀錄頁走的是這支方法'}`
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "state.datas" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue', 'result': '0 hits — 訂閱方案頁（MyPlan.vue）的畫面完全沒有讀取 state.datas 這個欄位，宣告了但沒有任何模板或邏輯引用它', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "datas: []," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/subscription/MyPlan.vue → 1，確認這個欄位真的有被宣告（不是打錯字），只是宣告後從未被讀取，證明 UserController@subscription 回傳的電控門鎖／攝影機／智慧電錶陣列是沒有消費端的假資料'}`
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "// TODO: 2404 後端回傳資料需要修改其他欄位，另外再新增 訂閱方案(subscription_plan) 及 硬體設備(deviceList) 兩個欄位" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php', 'result': "1 hit — 緊接著的 $datas 陣列是寫死的假資料（日期 2022/06/28、bill_id 'HM20220704' 等），跟著這行 TODO 註解一起出現", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "\'date\' => \'2022/06/28\'," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php → 1，確認確實有一筆寫死日期的假資料列在陣列裡'}`

### 收款設置支援哪些金流商？（藍新／國泰世華／永豐／中信／icash Pay／現金收款帳戶，各家設定費與手續費不同）
- 講法：收款設置支援哪些金流／線上收款要收多少費用／金流申請要錢嗎／手續費可以轉嫁給租客嗎
- 給誰看：property_manager
- 收款設置頁面可以新增的線上金流商包括藍新、國泰世華、永豐、中信、icash Pay，此外也可以另外新增「現金收款帳戶」讓租客用現金或匯款方式繳費。〔src/pages/users/payment/_parts/CashBanks.vue〕
- 國泰世華與永豐銀行要自行向銀行申請，首次設定費都是 5,000 元；中國信託與藍新則是直接在 JGB 系統線上申請，設定費全免。〔doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html〕
- 各家手續費不同：國泰世華虛擬 ATM 免費、超商條碼每筆 10 至 20 元；永豐虛擬 ATM 每筆 3 元、信用卡每筆 1.85%；中國信託虛擬 ATM 免費；藍新虛擬 ATM 實體繳納每筆 15 元、網路繳納每筆 20 元、信用卡國內每筆 2.4%、國外每筆 3%、超商代碼每筆 28 元。〔doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html〕
- 藍新的手續費規定一律由收款方（房東）自行吸收，不能轉嫁給租客；國泰世華的超商條碼手續費則可以自行設定要由租客或房東負擔；選擇中國信託則要注意租客必須自己有中信帳戶並用中信 App 才能繳費。〔doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html〕
- 藍新的超商代碼繳費方式另外還有租金金額限制：只能用來繳交 30 元以上、20,000 元以下的款項，超過這個範圍就不能選超商代碼繳費。〔doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html〕
- 以上金流商不是每個身分或方案都能開通：個人房東不能開通藍新、國泰世華、永豐；免費方案與體驗方案不能開通國泰世華、永豐。〔app/Http/Controllers/UserController.php〕
- 否定查證：`{'sentence_index': 4, 'cmd': 'sed -n \'/藍新金流有何限制？/,/信用卡付款/p\' \'/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html\' | grep -c "30 元以上、20,000 以下"', 'result': '1 — 該段落明確列出藍新超商代碼付款的租金金額限制', 'positive_control': 'sed -n \'/藍新金流有何限制？/,/信用卡付款/p\' \'/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html\' | grep -c "電商付款" → 1，確認這段真的是『藍新金流有何限制』這一整節的內容，不是抓錯區塊'}`
- 否定查證：`{'sentence_index': 5, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A2 -nF "if (\\$this->role->config_rule_key === Role::RULE_KEY_LANDLORD_INDIVIDUAL) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php | grep -c PAYMENT_NEWEBPAY', 'result': '1 — 個人房東分支確實會鎖藍新（PAYMENT_NEWEBPAY），限制真的存在，細節另立 jgb/I/payment-vendor-eligibility-by-role-and-plan', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "\'disabled\' => false," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php → 1，確認每個金流商預設是 disabled=false（可開通），要進到條件分支才會被鎖，證明鎖是額外附加的限制不是預設狀態'}`
- ⚠️ 待查：本題手續費／設定費數字來自幫助中心文章 qa27（https://www.jgbsmart.com/help/post/qa27，編輯日期 2026/06/30），未在 jgb2 程式碼中找到對應常數可交叉核對，僅能確認文件本身存在且描述具體，未能查證這些費率在系統上線時是否已經調整過。
- ⚠️ 待查：適用範圍的細節（哪個身分／方案不能開哪個金流商）另立一條 jgb/I/payment-vendor-eligibility-by-role-and-plan，本題只點出有此限制存在，不重複展開。

### 哪些身分或方案不能開通某些金流商？（個人房東不能開藍新／國泰世華／永豐，免費方案／體驗方案不能開國泰世華／永豐）
- 講法：個人房東能開藍新嗎／免費方案能開國泰世華嗎／金流商為什麼不能選／收款方式被鎖住怎麼辦
- 給誰看：property_manager
- 系統回傳可開通金流商列表時，若目前身分是「個人房東」，藍新、國泰世華、永豐三家都會被標成不可開通；若不是個人房東、但目前方案是「免費方案」或「體驗方案」，則只有國泰世華、永豐會被標成不可開通，藍新不受此限制。〔app/Http/Controllers/UserController.php〕
- 被標成不可開通的金流商在選單上仍以正常顏色顯示，點選後畫面不會出現該金流商的申請表單，改以紅字顯示「您無法開通此收款方式，若有問題請洽詢JGB客服」；選單上金流商變成灰階是另一件事，代表這家金流已經開通滿三組帳號。〔src/pages/users/payment/routerView/Add.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A2 -nF "elseif (in_array(\\$planName, [\'免費方案\', \'體驗方案\'])) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php | grep -c PAYMENT_NEWEBPAY', 'result': '0 — 免費方案／體驗方案這個分支只鎖 PAYMENT_CATHAYBK 與 PAYMENT_SINOPAC，不含 PAYMENT_NEWEBPAY，確認藍新不受這條規則限制', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A2 -nF "if (\\$this->role->config_rule_key === Role::RULE_KEY_LANDLORD_INDIVIDUAL) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php | grep -c PAYMENT_NEWEBPAY → 1，確認個人房東那個分支確實含 PAYMENT_NEWEBPAY，兩個分支鎖的金流商清單不同'}`
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "((state.bankSelected.key && !state.bankSelected.disabled))" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/routerView/Add.vue', 'result': '1 hit — 『綁定資訊』申請表單區塊的整段內容是被包在『已選金流商且未被 disabled』這個判斷式裡才會渲染', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "state.bankSelected.disabled ? \'block\' : \'hidden\'" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/routerView/Add.vue → 1，確認紅字提示訊息區塊的顯示／隱藏條件正好跟表單相反，disabled 為真時紅字顯示、表單不顯示'}`

### 藍新金流申請要注意什麼？（個人房東無法申請；手機與 Email 送出後不能改，每個金流最多開三組帳號，需審核）
- 講法：藍新金流怎麼申請／藍新申請資料能改嗎／金流最多能開幾組帳號／藍新審核要多久
- 給誰看：property_manager
- 申請藍新科技前要先確認目前身分能不能開通：個人房東完全不能開通藍新（點選藍新後不會出現申請表單，改以紅字提示改洽 JGB 客服），以下申請細節只適用於能開通藍新的身分。〔src/pages/users/payment/routerView/Add.vue〕
- 申請藍新科技時填寫的手機號碼與 Email，送出申請後就不能再修改，因為它們會分別成為藍新的管理者帳號與通知信箱。〔src/pages/users/payment/_parts/Newebpay.vue〕
- 藍新申請時填寫的商店名稱，系統會自動加上固定字首後才送出；用於提領入帳款項的銀行帳戶，規定必須是帳號申請人本人所有。〔src/pages/users/payment/_parts/Newebpay.vue〕
- 同一個帳號每個金流最多可以開通三組帳號。〔src/pages/users/payment/routerView/Add.vue〕
- 只要有勾選開通信用卡（含國外信用卡）付款方式，藍新就需要三個工作天以上的審核時間，實際天數依藍新官方審核進度調整。〔doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "此號碼將成為您未來藍新科技/NewebPay的管理者帳號，送出申請後無法修改，請確認無誤。" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Newebpay.vue', 'result': '1 hit — 手機號碼欄位下方直接印出這段提醒', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "此信箱將成為藍新科技/NewebPay 寄送通知信的信箱，送出申請後無法修改，請確認無誤。" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Newebpay.vue → 1，確認 Email 欄位下方也有同一句型的提醒，兩個欄位都明講送出後不能改'}`
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A2 -nF "if (\\$this->role->config_rule_key === Role::RULE_KEY_LANDLORD_INDIVIDUAL) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php | grep -c PAYMENT_NEWEBPAY', 'result': '1 — 個人房東分支確實含 PAYMENT_NEWEBPAY（藍新），確認個人房東不能開通藍新', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A2 -nF "elseif (in_array(\\$planName, [\'免費方案\', \'體驗方案\'])) {" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/UserController.php | grep -c PAYMENT_NEWEBPAY → 0，確認免費／體驗方案那個分支不含藍新，兩個分支鎖的名單不同，抓法能分辨'}`
- ⚠️ 待查：『三個工作天以上』的審核時間只在幫助中心文章 qa27 找到，jgb2 程式碼裡沒有找到對應的常數或後端排程可交叉核對，只能確認文件本身這樣寫。

### 金流綁定後還能改嗎？（除了國泰世華，其他金流商明細頁都是唯讀不能重送）
- 講法：收款方式可以改嗎／金流明細可以編輯嗎／綁定後想改資料怎麼辦／哪個金流可以重新送審
- 給誰看：property_manager
- 綁定成功後點進明細頁查看，除了國泰世華以外的金流商表單都是唯讀不能再編輯重送；只有國泰世華的明細頁可以重新填寫並再次送出。〔src/pages/users/payment/routerView/Detail.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "isDisabled={true}" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/routerView/Detail.vue', 'result': '5 hits — every one of Newebpay／Cathaybk／Ctbc／Sinopac／IcashPay renders with isDisabled={true} on the Detail page', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "onSubmit={()=>{" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/routerView/Detail.vue → 1 hit, and it is on the Cathaybk block only, confirming only that vendor\'s form actually wires a submit handler despite also carrying isDisabled={true}'}`
- ⚠️ 待查：Cathaybk（國泰）明細頁同時帶 isDisabled={true} 又帶 onSubmit／onChange，兩者如何配合放行編輯（例如是否有另一個欄位或狀態解鎖輸入框）未在讀到的檔案範圍內看到，僅能確認它是唯一被接上重新送出邏輯的金流商。

### icash Pay／中信收款帳戶申請要多久？（智付通約 2-5 個工作天，中信 ACH 驗證約 5 個工作天）
- 講法：icash Pay申請多久／中信收款帳戶審核多久／智付通開通要多久／ACH驗證是什麼
- 給誰看：property_manager
- 選擇 icash Pay 時頁面會提醒：智付通將存取申請資料以完成開通程序，需要至少 2 到 5 個工作天。〔src/pages/users/payment/routerView/Add.vue〕
- 選擇中國信託時，頁面說明送審後會由 JGB 進行 ACH 驗證並撥款 1 元到收款帳號，審核時間需要 5 個工作天（不含例假日）。〔src/pages/users/payment/_parts/Ctbc.vue〕

### 收據範本有哪些？（財政部包租業租金收據範本只有法人／社宅團隊才看得到）
- 講法：收據範本有哪些／財政部範本怎麼設定／一般收據怎麼選／收據要不要開通
- 給誰看：property_manager
- 一般個人房東的收據類型只有兩種可選：「超商繳費單、JGB系統收據」與「超商繳費單、不檢附收據」；只有當下身分是法人或社宅團隊時，選單才會多出另外三種含「財政部包租業租金收據」或「JGB系統繳費單」的組合，總共五種可選。〔src/utils/constants/paymentSetting.ts〕
- 選擇含「財政部包租業租金收據」的組合時，必須先在團隊資訊內填寫公司登記證日期、公司登記證縣市、公司登記證號，否則範本內容會缺資料。〔src/pages/users/payment/_parts/Receipt.vue〕
- 收據可以上傳一張用印圖片作為正式收款依據，限定 JPG、PNG 檔，最多 1 張，檔案大小上限 10MB；這個上傳欄位不受收據類型限制、一律顯示，只有沒有「編輯收款設置」權限時才會整區塊變灰無法操作，跟收據類型選了哪一種、目前身分是不是團隊都無關。〔src/pages/users/payment/_parts/Receipt.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "const isTeam = [3, 4].includes(store.state?.userData?.role?.config_rule_key)" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue', 'result': '1 hit — availableReceiptOptions 這個 computed 屬性只有在 isTeam 為真時才回傳全部 5 個選項（both、tw_zh_mof、general、jgb_system、no）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "return labelKeyToLabel([general, no])" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue → 1，確認非團隊身分走的是另一個分支，只回傳 general（超商繳費單、JGB系統收據）與 no（超商繳費單、不檢附收據）兩個選項，選單裡沒有名叫『一般收據』的選項'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -B20 -nF "AjaxUploader" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue | grep -c \'v-if="state.showTransactionInputs"\'', 'result': '0 — 用印圖片上傳所在的容器（含 AjaxUploader）往上追溯 20 行內完全沒有出現 showTransactionInputs 這個判斷式，證明它不在被收據類型控制顯示的那個 grid 容器裡', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "v-if=\\"state.showTransactionInputs\\"" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue → 1，確認 showTransactionInputs 這個判斷式真的存在於同一個檔案、只是包住的是另一個容器（帳單收款人設定），不是抓錯字串'}`

### 押金收據能自訂摘要跟蓋章嗎？（摘要與三顆收款章都只有特定合作團隊才看得到）
- 講法：押金收據摘要怎麼改／收據可以蓋章嗎／押金收據印章設定／押金收據字數上限
- 給誰看：property_manager
- 押金收據的「摘要」欄開頭文字可以自訂、最多 20 個字（留空沿用團隊名稱），以及設定三顆收款章（主辦出納、主辦會計、機構首長）蓋印於押金收據對應的用印格——這一整塊設定只有特定的合作團隊身分才會顯示，一般房東完全看不到這個區塊。〔src/pages/users/payment/_parts/Receipt.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "return groups.includes(\'depositReceiptZiyu\') || groups.includes(\'depositReceiptZilian\')" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue', 'result': '1 hit — isDepositReceiptStampTeam 這個 computed 屬性只在角色所屬的特殊分組包含這兩個團隊代號時才成立', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "v-if=\\"isDepositReceiptStampTeam\\"" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue → 1，確認整個 <template> 區塊（含摘要欄與三顆收款章）都是用同一個旗標包起來，不屬於這兩個團隊的人完全看不到摘要自訂欄，不只是看不到收款章'}`
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -B2 -nF "押金收據摘要標題（留空沿用團隊名稱）" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue | grep -c "isDepositReceiptStampTeam"', 'result': '1 — 摘要標題欄前面兩行就是 <template v-if="isDepositReceiptStampTeam">，證明摘要欄本身也在這個判斷式內，不是只有收款章被限制', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "RECEIPT_SUMMARY_TITLE_MAX" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue → 命中多處（含 :maxlength 綁定），確認摘要欄真的存在於程式裡、只是被 isDepositReceiptStampTeam 整段包住'}`

### 帳單怎麼開電子發票？（要先聯繫 JGB 業務開通加值服務，開通後才會出現稅與發票分頁）
- 講法：帳單怎麼開發票／電子發票怎麼啟用／合約怎麼設定要不要開發票／發票功能怎麼申請
- 給誰看：property_manager、prospect
- 帳單開立發票功能預設不是啟用狀態，要先開通電子發票加值服務，再聯繫 JGB 業務才能啟用。〔src/pages/users/payment/_parts/Invoice.vue〕
- 功能啟用完成後，「編輯合約」畫面才會多出「稅與發票」分頁，用來設定這份合約未來收款時的帳單是否要開立發票。〔src/pages/users/payment/_parts/Invoice.vue〕
- 發票的開立模式可以設定「預先開立發票時機」，並可再指定要提前的天數。〔src/pages/users/payment/_parts/Invoice.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "如要啟用此功能，請先開通電子發票加值服務後，聯繫您的 JGB 業務。" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Invoice.vue', 'result': '1 hit — 這段說明文字掛在功能尚未啟用的畫面區塊裡', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "{{ t(\'功能已啟用\') }}" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Invoice.vue → 1，確認同一個檔案裡有另一個『功能已啟用』狀態的分支，證明目前是兩態切換而非恆常關閉'}`

### 沒有查看權限會怎樣？（收款設置與訂閱方案選單整個不會出現）
- 講法：沒有權限看不到收款設置／訂閱方案選單不見了／為什麼找不到訂閱方案／編輯團隊權限的作用
- 給誰看：property_manager
- 團隊成員如果沒有被開啟對應的查看權限，介面上【收款設置】與【訂閱方案】這兩個選單會整個不出現（不是變成灰色不能點，而是完全看不到），而且這位成員的帳號資訊會以個人房東的形式呈現。〔doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa23_zh-Hant.html〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'sed -n \'/為什麼權限勾了卻沒有作用？/,/有兩組權限沒開/p\' \'/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa23_zh-Hant.html\' | grep -c "整個選單不會出現"', 'result': '0 — 『必須一起開啟才會生效』的一般規則段落（新增物件／編輯物件／新增合約這一類），沒有出現『整個選單不會出現』的說法，代表這只是提醒查看＋編輯要一起開，不是選單消失', 'positive_control': 'sed -n \'/有兩組權限沒開，選單會整個看不見/,/因此同事若回報/p\' \'/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa23_zh-Hant.html\' | grep -c "整個選單不會出現" → 1，確認緊接著描述『編輯團隊』『查看人員／編輯人員』這兩組特殊權限的段落，明確用『整個選單不會出現』這個說法，兩種行為在文件裡是分開描述的'}`
- 否定查證：`{'sentence_index': None, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "edit_role\\", // 編輯團隊" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Character.php', 'result': '1 hit — 權限清單裡確實有一個名字就叫『編輯團隊』的獨立權限鍵 edit_role', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "edit_role_payment\\", // 編輯收款設置" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Character.php → 1，確認同一份清單裡『編輯收款設置』『編輯訂閱方案』是另外兩個獨立權限鍵，跟 edit_role、跟側邊欄用的 show_role_payment／show_role_subscription 都不是同一個鍵'}`
- ⚠️ 待查：文件與程式對這個行為的歸因不一致，未選邊：qa23 把【收款設置】【訂閱方案】選單消失歸因於沒有開啟「編輯團隊」權限；但程式裡側邊欄選單（app/Role.php）這兩個項目各自對應獨立的查看權限旗標 show_role_payment（『查看收款設置』）與 show_role_subscription（『查看訂閱方案』），而且權限清單（app/Character.php）裡「編輯團隊」（edit_role）、「編輯收款設置」（edit_role_payment）、「編輯訂閱方案」（edit_role_subscription）是三個各自獨立的權限鍵，跟 show_role_payment／show_role_subscription 這兩個查看權限鍵又是不同層級。是否 qa23 所指的『編輯團隊』實際上涵蓋或連動這兩個查看權限，還是文件用詞不精確，需要業主或熟悉權限矩陣的人確認。

### 帳單可以自動排程發送、指定收款人嗎？（提前 0～20 天自動發送，收款人可選原簽約者／主要經理人／自訂）
- 講法：帳單自動發送設定／帳單提前幾天發送／帳單收款人怎麼設定／收款人可以改成別人嗎
- 給誰看：property_manager
- 「帳單自動排定發送」可以設定「幾天前」，選項是不啟用、當天、或提前 1 到 20 天；系統會依照設定的天數，把已經填寫完成（或不需填水電瓦斯等生活費用細節）的帳單，在繳費截止日前自動排入待發送帳單列表，例如截止日 05/05、設定提前 5 天，系統會在 04/30 早上 7 點把該筆帳單排入列表。〔src/pages/users/payment/_parts/OtherSetting.vue〕
- 這個自動發送排程設定只有在目前身分是有效訂閱中才會顯示。〔src/pages/users/payment/_parts/OtherSetting.vue〕
- 「帳單收款人」可以選「原簽約者」「主要經理人」或「自訂」；選「自訂」時要額外填寫收款人、聯絡人、聯絡人電話、Email 四個欄位，選其他兩個選項則不需要，會直接送出設定；這整組帳單收款人設定只在收據類型選「1. 超商繳費單、財政部包租業租金收據、JGB系統收據」「3. 超商繳費單、JGB系統收據」「4. JGB系統繳費單、JGB系統收據」時才會顯示，選「2. 超商繳費單、財政部包租業租金收據」或「5. 超商繳費單、不檢附收據」時整組不顯示。〔src/pages/users/payment/_parts/Receipt.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "transactionInputLabelKeys.billAutoSend" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/OtherSetting.vue', 'result': '2 hits — 標題與送出成功提示都用同一個 labelKey，緊接著的下拉選單 options 是 state.dayOptions（不啟用／當天／1~20）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "billAutoSend: \'帳單自動排定發送\'," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/utils/constants/paymentSetting.ts → 1，確認這個 labelKey 對應的顯示文字就是『帳單自動排定發送』'}`
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "store.state?.userData?.role?.isSubscriptionActive && <div className=\\"mb-6\\">" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/OtherSetting.vue', 'result': '1 hit — 整個帳單自動發送設定區塊都包在這個判斷式裡', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "其他設置" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/OtherSetting.vue → 1，確認這個檔案本身就是『其他設置』分頁的內容，不是別的頁面'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -B1 -nF "resetCustomReceiverInfos()" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue | grep -c "CUSTOM"', 'result': '1 — 選『自訂』以外的選項時會呼叫 resetCustomReceiverInfos() 並直接送出設定，不用等額外欄位填完', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "receiptReceiverType === ReceiptReceiverType.CUSTOM" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue → 1，確認選『自訂』時才會渲染出收款人／聯絡人／電話／Email 四個額外欄位的區塊'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A10 -nF \'v-if="state.showTransactionInputs"\' b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue | grep -c billReceiver', 'result': '1 — 開頭 v-if="state.showTransactionInputs" 這個容器往下 10 行內就出現帳單收款人（billReceiver）的下拉選單，確認帳單收款人設定被包在這個判斷式裡', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "paymentMetaState?.form?.receipt_type === ReceiptOptionType.BOTH" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/users/payment/_parts/Receipt.vue → 1，確認 showTransactionInputs 為真的條件（收據類型為 BOTH／GENERAL／JGB_SYSTEM）真的存在，不是空判斷'}`

## 預約 demo（4 條；頁：listings.demoForm）

### 預約 demo 表單要填什麼？（公司、職稱、聯絡方式、物件所在地、感興趣功能與諮詢內容）
- 講法：預約demo要填什麼／怎麼申請demo／聯繫我們表單欄位／demo表單怎麼填
- 給誰看：property_manager、prospect
- 預約 demo 表單（頁面標題「聯繫我們」）要填公司名稱、職稱、姓名、電話、Email、物件所在地（國家/城市）、物件數量、團隊人數、最有興趣的功能（可複選）與諮詢內容，並勾選同意 JGB 隱私權政策。〔src/pages/listings/DemoForm.vue〕
- 頁面下方標示「所有資訊皆必填」，「送出」按鈕的顏色會依畫面上是否已填妥公司名稱、職稱、姓名、電話、Email、物件所在地、感興趣功能、物件數量、團隊人數、諮詢內容這 10 個欄位並勾選隱私權政策，在灰色與可點擊的主色之間切換，但按鈕本身一律可以點擊；實際擋下送出的是每個欄位上的瀏覽器對必填欄位的內建檢查，未填妥必填欄位時是瀏覽器原生驗證跳出提示、擋下表單送出，不是這個顏色判斷式在擋。〔src/pages/listings/DemoForm.vue〕
- 「最有興趣的功能」選項是複選核取方塊，畫面會要求至少勾選一項；其餘欄位都是單選下拉選單或文字輸入框。〔src/pages/listings/DemoForm.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -B5 -nF "demoform-submit-button" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/DemoForm.vue | grep -c \':disabled\'', 'result': '0 — 送出按鈕的宣告附近沒有 :disabled 綁定，只有 :class 與 :style 依 allowSubmit 切換顏色，按鈕元素本身一直是可點擊的', 'positive_control': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/DemoForm.vue | grep -c 'required' → 11，確認表單欄位上真的掛了原生 required 屬性（8 個固定必填欄位、1 個感興趣功能的條件式 required、1 個一般 required、1 個隱私權 checkbox），跟畫面顯示要求一致"}`

### demo 表單的下拉選項有哪些？（物件數量 7 級距、團隊人數 6 級距、感興趣功能 6 項）
- 講法：物件數量選項有哪些／團隊人數怎麼選／感興趣功能有哪些選項／demo表單職稱選單
- 給誰看：property_manager、prospect
- 「物件數量」分成 1-10、11-30、31-50、50-100、100-200、200-300、300戶以上 共 7 個級距可選。〔config/demoform.php〕
- 「團隊人數」分成 1-15、16-30、31-50、51-100、101-500、501-1000 共 6 個級距可選。〔config/demoform.php〕
- 「最有興趣的功能」可複選的項目是房源管理、租約管理、帳務管理、團隊管理、智慧門鎖、智慧電錶共 6 項。〔config/demoform.php〕
- 「職稱」下拉選單提供公司負責人、公司主要管理者、行銷主管、業務主管、營運主管、財務主管、技術主管、行銷窗口、業務窗口、營運窗口、財務窗口、技術窗口、其他共 13 個選項。〔config/demoform.php〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'estates_amount\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'"', 'result': '7 — config/demoform.php 裡 estates_amount（物件數量）陣列剛好有 7 個選項，跟句子列的級距／選項數一致', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'status\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'" → 3，用同一套抓法對 status 這組不相干的陣列算出的是 3 不是句子裡的數字，證明抓法真的照各陣列自己的邊界分別計數，不是整份檔案混算'}`
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'team_member_amount\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'"', 'result': '6 — config/demoform.php 裡 team_member_amount（團隊人數）陣列剛好有 6 個選項，跟句子列的級距／選項數一致', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'status\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'" → 3，用同一套抓法對 status 這組不相干的陣列算出的是 3 不是句子裡的數字，證明抓法真的照各陣列自己的邊界分別計數，不是整份檔案混算'}`
- 否定查證：`{'sentence_index': 2, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'function_table\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'"', 'result': '6 — config/demoform.php 裡 function_table（最有興趣的功能）陣列剛好有 6 個選項，跟句子列的級距／選項數一致', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'status\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'" → 3，用同一套抓法對 status 這組不相干的陣列算出的是 3 不是句子裡的數字，證明抓法真的照各陣列自己的邊界分別計數，不是整份檔案混算'}`
- 否定查證：`{'sentence_index': 3, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'job_title\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'"', 'result': '13 — config/demoform.php 裡 job_title（職稱）陣列剛好有 13 個選項，跟句子列的級距／選項數一致', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:config/demoform.php | sed -n "/\'status\' => \\[/,/^    \\],\\$/p" | grep -cE "^        \'" → 3，用同一套抓法對 status 這組不相干的陣列算出的是 3 不是句子裡的數字，證明抓法真的照各陣列自己的邊界分別計數，不是整份檔案混算'}`

### demo 表單送出後多久有人聯繫？（顯示感謝頁，2-3 個工作天內專人聯繫）
- 講法：demo表單送出後多久聯繫／預約demo後會怎樣／填完表單多久有人回覆／demo表單送出成功畫面
- 給誰看：property_manager、prospect
- 表單送出成功後會切換成感謝畫面，寫著「謝謝您完成預約表單！」，並提示「感謝您完成填寫表單，將會有專人於 2-3 天工作天聯繫您」，畫面上有按鈕可以回到官網首頁。〔src/pages/listings/DemoForm.vue〕

### demo 表單哪些欄位真的會被系統擋下？（系統實際只驗公司、姓名、電話、Email 四項）
- 講法：demo表單哪些欄位真的必填／實際驗證跟畫面要求一樣嗎／demo表單漏填會怎樣／demo表單驗證規則
- 給誰看：property_manager
- 表單頁面要求全部 10 個欄位與隱私權同意都填妥、按鈕才會從灰色變可點擊，但系統實際送出時只會檢查公司名稱、姓名、電話、Email 這四個欄位是否為空、以及 Email 格式是否正確，只要這四項合格就能送出成功。〔app/Http/Controllers/IndexController.php〕
- 否定查證：`{'sentence_index': 0, 'cmd': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/IndexController.php | sed -n '/public function demoForm/,/public function trialForm/p' | sed -n '/\\$rule = \\[/,/\\];/p' | grep -c '=>'", 'result': '4 — demoForm() 函式裡 $rule 陣列只有 4 個 key（company_name／name／tel／email），跟畫面上要求的 10 個欄位不一致', 'positive_control': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Http/Controllers/IndexController.php | sed -n '/public function demoForm/,/public function trialForm/p' | sed -n '/\\$rule = \\[/,/\\];/p' | grep -c 'job_title\\|interests\\|estates_amount' → 0，確認職稱／感興趣功能／物件數量這些畫面上必填的欄位完全沒有出現在後端驗證規則裡"}`

## 控制台（設定、通知信範本、自動化任務）（9 條；頁：controlPanel.index、controlPanel.setting、notificationMail、taskManagement、taskManagement.create、taskManagement.edit）

### 控制台首頁目前能用什麼？（目前只有「任務管理器」一個項目可以點擊進入）
- 講法：控制台有什麼功能／控制台首頁能做什麼／控制台目前可以用哪些設定
- 給誰看：property_manager
- 控制台首頁的說明是「管理您的 JGB 系統」，目前畫面上實際可以點擊進入的項目只有「任務管理器」一項。〔src/pages/control-panel/Index.vue〕
- 任務管理器的卡片說明是「設定您的排程機器人，在滿足設定的條件後，可以觸發自動操作。」，點擊後會進入任務管理器頁面。〔src/pages/control-panel/Index.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/control-panel/Index.vue | sed -n "/TODO: 其他控制台功能之後待補完/,/<\\/div> \\*\\/}/p" | grep -c "label={"', 'result': '12 — 廣告頁資訊／簽約資訊／收款金流與發票／物件設定／合約設定／帳務設定／(重複的)任務管理器／簽核管理／裝置設定／通知設定／全球偏好設定／訂閱與付款紀錄 這 12 個卡片全部落在同一段 JSX 註解裡，不會被渲染出來', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/control-panel/Index.vue | sed -n "1,/TODO: 其他控制台功能之後待補完/p" | grep -c "label={" → 1，確認註解區塊之外只有「任務管理器」這一張卡片是真的會渲染'}`

### 進入控制台設定後看到什麼？（本身只是麵包屑與側欄外殼，內容是任務管理器頁面）
- 講法：控制台設定頁內容／任務管理器上一層是什麼／控制台麵包屑／控制台側邊欄
- 給誰看：property_manager
- 點進控制台的設定範圍後，畫面上方會顯示「Dashboard／控制台／任務管理設定」的麵包屑，本身不含其他獨立內容，實際顯示的內容是底下的任務管理器（或新增／編輯任務）頁面。〔src/pages/control-panel/setting/Index.jsx〕
- 否定查證：`{'sentence_index': 0, 'cmd': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/control-panel/setting/Index.jsx | grep -oE '<[A-Za-z][A-Za-z0-9]*' | sort -u | wc -l", 'result': '7 — 整個檔案裡出現過的 JSX 標籤只有 LayoutGeneral／Breadcrumbs／div／OrderAside／RouterView／Component／KeepAlive 七種，沒有任何獨立的內容型元件（表單、清單、卡片…），確認本身只是外殼＋側欄＋子路由', 'positive_control': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/control-panel/taskManagement/Index.vue | grep -oE '<[A-Za-z][A-Za-z0-9]*' | sort -u | wc -l → 11，確認底下真正有內容的任務管理器頁面標籤種類明顯較多，證明抓法能分辨『空殼』與『有內容』的頁面"}`

### 任務管理器是做什麼用的？（設定週期性任務或預定通知，系統會提前自動開單並寄信）
- 講法：任務管理器是什麼／自動化任務怎麼運作／排程機器人是什麼／任務管理器用途
- 給誰看：property_manager
- 任務管理器頁面的說明是：設定週期性的任務、或是預定通知，設定完成後，系統會自動在指定週期前完成單據的開立，並寄信通知。〔src/pages/control-panel/taskManagement/Index.vue〕
- 任務列表可以用「社區」「任務類型」篩選，也可以用任務名稱關鍵字搜尋；沒有符合篩選條件時顯示「沒有符合的結果」，完全沒有建立過任務時顯示「目前尚無任務資料」。〔src/pages/control-panel/taskManagement/Index.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "沒有符合的結果😢" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/control-panel/taskManagement/Index.vue', 'result': '1 hit', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "目前尚無任務資料" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/control-panel/taskManagement/Index.vue → 1，確認『篩選無結果』與『完全沒有任務資料』是同一個列表元件裡兩種不同條件各自對應的空狀態文字'}`
- ⚠️ 待查：任務列表頁（taskManagement/Index.vue）的說明文字寫「指定週期的前三十天完成單據的開立」，但新增／編輯任務頁（taskManagement/edit/Index.jsx）寫的是「觸發時間前 45 天完成單據的開立，系統後續會在觸發時間的 30 天前、15 天前寄送通知信」——兩個頁面對『提前幾天開單』給的具體天數不一致（30 天 vs 45 天），未能判斷哪一份是最新版本，交由業主裁決，因此標題不寫出具體天數。

### 新增任務能選哪些類型？（目前只開放「通知」類型，行為是信件通知或站內通知）
- 講法：任務類型有哪些／任務行為可以選什麼／可以設定修繕單自動開單嗎／通知任務怎麼設定
- 給誰看：property_manager
- 新增任務時，任務類型目前只有「通知」一種可以選，對應的任務行為是「信件通知」或「站內通知」兩種。〔app/Services/TaskService.php〕
- 任務管理器列表頁的說明文字雖然舉例提到「週期修繕單」，但目前新增任務時可以選的任務類型只有「通知」，「修繕管理」目前沒有這個選項。〔app/Services/TaskService.php〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Services/TaskService.php | grep -n "\'repair\'"', 'result': "2 hits — getTypeOptions() 內一處是帶 // 前綴的註解行「//     'value' => 'repair',」（不是真正回傳給前端的陣列項）；另一處在 translateData() 是沒有 // 前綴的既有資料轉譯對照表「'repair' => '修繕管理',」，用來把資料庫裡舊資料的 type 值轉成中文顯示，不是新增任務時可選的選項來源", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Services/TaskService.php | grep -n "\'notification\'," → 命中 getTypeOptions() 裡沒有 // 前綴的「\'value\' => \'notification\',」那一行，證明同一個函式裡『通知』這個選項確實是未被註解、會被回傳的'}`

### 任務週期怎麼設定？（單位分年／月，方式可選僅一次、持續不停、特定日期結束、重複特定次數）
- 講法：任務週期怎麼設定／任務可以只跑一次嗎／任務可以設定結束日期嗎／任務重複次數怎麼設定
- 給誰看：property_manager
- 任務的週期單位可以選「年」或「月」。〔app/Services/TaskService.php〕
- 任務的重複方式有四種：「僅一次」、「持續不停」、「特定日期結束」、「重複特定次數」。〔app/Services/TaskService.php〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Services/TaskService.php | sed -n "/\'method\' => \\[/,/^            \\]\\$/p" | grep -c "\'label\' =>"', 'result': '4 — cycle 選項裡的 method 陣列剛好只有 4 個 label（僅一次／持續不停／特定日期結束／重複特定次數），沒有第五種', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:app/Services/TaskService.php | sed -n "/\'unit\' => \\[/,/^            \\],\\$/p" | grep -c "\'label\' =>" → 2，確認同一個函式裡 unit 陣列（年／月）用同樣的抓法算出的是 2 不是 4，證明抓法真的照陣列邊界分別計數，不是整支檔案亂算'}`

### 新增任務表單有哪些欄位？（任務名稱、任務類型、關聯物件、任務行為、任務時間、重複間隔、結束時間、通知對象、通知內容）
- 講法：新增任務要填哪些欄位／任務表單內容／關聯物件怎麼選／通知對象怎麼設定
- 給誰看：property_manager
- 新增／編輯任務的表單依序是：「任務名稱」「任務類型」「關聯物件」（可全選或挑選特定物件）「任務行為」「任務時間」「重複間隔」「結束時間」（可再設定於某天結束或重複特定次數）「通知對象」（輸入 Email 或選擇團隊成員）與「通知內容」。〔src/pages/control-panel/taskManagement/edit/Index.jsx〕
- 編輯已存在的週期性任務時，會多一個「編輯範圍」欄位，用來選擇這次修改只套用在這一項任務、還是套用在這項任務和後續任務。〔src/pages/control-panel/taskManagement/edit/Index.jsx〕

### 已建立的任務怎麼編輯／刪除？（每筆任務可編輯、複製、刪除，編輯週期任務可選只改這次或連後續一起改）
- 講法：任務可以刪除嗎／任務可以複製嗎／編輯週期任務會影響後續任務嗎／任務列表可以做什麼操作
- 給誰看：property_manager
- 任務列表每一列右側的齒輪選單提供三個動作：「編輯任務」「複製現有任務」「刪除任務」。〔src/use/config/useTaskManagementTypes.js〕
- 編輯週期性任務時，可以選擇修改範圍是「這項任務」（只改這一次）或「這項任務和後續任務」（連同之後每次排程一起改）。〔app/Services/TaskService.php〕

### 通知信副本信箱怎麼設定？（預設收件為團隊擁有者信箱，每個通知信最多再加 3 組副本）
- 講法：通知信副本信箱怎麼加／通知信可以加幾個收件人／通知信預設寄給誰／通知信設定在哪裡
- 給誰看：property_manager
- 通知信設定頁面說明：通知信預設接收信箱是團隊擁有者的註冊信箱，每個通知信最多可以再新增 3 組副本信箱。〔src/pages/control-panel/notificationMail/Index.jsx〕
- 否定查證：`{'sentence_index': None, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c "TaskItem" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/control-panel/notificationMail/Index.jsx', 'result': '1 — TaskItem 只在檔案開頭被 import／宣告一次，JSX 模板裡完全沒有第二次出現（沒有被實際渲染）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c "mappingState" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/control-panel/notificationMail/Index.jsx → 2，確認同一個檔案裡確實有符號是 import 後又在邏輯裡被呼叫第二次（真的被使用），跟 TaskItem／TableHead 只出現一次（僅宣告、從未使用）的情況不同'}`
- 否定查證：`{'sentence_index': None, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "const typeOptionsFetcher = reactive(" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/control-panel/notificationMail/Index.jsx', 'result': '1 hit — 抓回的 state.typeOptions 資料只在 useQuery 的 onSuccess 裡被 mappingState 賦值', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "class=\\"relative grow\\"" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/control-panel/notificationMail/Index.jsx → 1，確認畫面上緊接著開一個 class=\\"relative grow\\" 的容器，但這個容器內沒有任何讀取 state.typeOptions 的渲染邏輯（開始標籤後直接關閉）'}`
- 否定查證：`{'sentence_index': None, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/control-panel/Index.vue | sed -n "/TODO: 其他控制台功能之後待補完/,/routerName={\'notificationMail\'}/p" | grep -c "{/\\*"', 'result': "2 — 這個連到通知信設定頁面的卡片，落在從 {/* //TODO... */} 開始、到 routerName={'notificationMail'} 為止的範圍內，範圍裡出現了 2 個 {/* 開頭的 JSX 註解標記，代表這張卡片是包在註解區塊裡的，不會被渲染", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "routerName={\'taskManagement\'}" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/control-panel/Index.vue → 1，確認同一個檔案裡『任務管理器』那張卡片的 routerName 沒有被註解包住，是真的會渲染出來的連結'}`
- ⚠️ 待查：通知信設定頁面（notificationMail/Index.jsx）除了上述說明文字外，實際列出各通知類型並讓使用者新增副本信箱的清單區塊（state.typeOptions 抓回資料後應該渲染的地方）目前是空的 <div>，也 import 了 TaskItem／TableHead 元件卻沒有在畫面上使用，無法確認副本信箱的新增介面在目前版本是否已完整實作；另外，目前找不到任何現行（未被註解）的選單或連結會導向這個頁面，只能透過直接輸入網址進入。

### 誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定」子路徑才會擋）
- 講法：誰可以用控制台／租客可以設定任務管理嗎／控制台權限限制／為什麼進不去控制台
- 給誰看：property_manager
- 進入「設定」子路徑（任務管理、通知信設定）之前，系統會先檢查目前角色屬於哪個特定合作團隊角色分組，如果不屬於系統認可的分組，會直接被導回一般使用者頁面，無法進入。〔src/routes/controlPanel.js〕
- 這個角色分組檢查只掛在「設定」頁面上，控制台首頁本身沒有這道檢查，任何登入的身分都能開啟控制台首頁，只是首頁目前只有「任務管理器」一張卡片可以點擊進入。〔src/routes/controlPanel.js〕
- 新增任務、編輯任務與通知信設定這三個頁面都額外標記租客角色不允許使用。〔src/routes/controlPanel.js〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "if (![\'controlPanel\', \'tongSang\'].includes(specialRoleGroup.key)){" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/routes/controlPanel.js', 'result': "1 hit — 判斷式為真（不屬於這兩個分組）時直接 window.location.href = '/users'", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "window.location.href = \'/users\'" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/routes/controlPanel.js → 1，確認判斷式為真時真的有導頁動作，不是空判斷'}`
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A3 -nF "name: \'controlPanel.index\'," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/routes/controlPanel.js | grep -c "beforeEnter"', 'result': '0 — controlPanel.index 這個路由物件（/controlPanel）沒有 beforeEnter 屬性，不會執行任何角色分組檢查', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -A3 -nF "name: \'controlPanel.setting\'," b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/routes/controlPanel.js | grep -c "beforeEnter" → 1，確認緊接著的 controlPanel.setting 路由物件真的有掛 beforeEnter，兩者寫法不同'}`

## 官網首頁（7 條；頁：web:indexs）

### 官網首頁有哪些區塊？（橫幅、熱門物件、優質租管業者推薦、特色介紹、企業夥伴、最新消息）
- 講法：首頁有什麼內容／官網首頁架構／首頁看得到什麼／JGB官網首頁介紹
- 給誰看：prospect
- 首頁最上方是橫幅區塊，接著依序是「熱門物件」輪播、「誠心推薦·優質租管業者」輪播、平台特色說明區塊、東南亞城市數與試用／諮詢按鈕、「最新消息」，最後是「企業夥伴」。〔src/pages/listings/Home.vue〕
- 「熱門物件」區塊只有在有回傳物件資料時才會顯示，用輪播呈現每筆物件的縮圖、標題與地址等資訊；「查看更多物件」這個連結到找房搜尋頁的按鈕，只有從特定搜尋入口進入首頁時才會顯示，一般直接造訪首頁不會看到這個按鈕。〔src/pages/listings/Home.vue〕
- 「誠心推薦·優質租管業者」區塊同樣只在有資料時顯示，用輪播呈現使用 JGB 的租管業者推薦內容。〔src/pages/listings/Home.vue〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "v-if=\\"\\$route.query?.allowSearch\\"" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/Home.vue', 'result': '1 hit — 「查看更多物件」這個連結整段包在這個條件判斷式裡，一般沒有帶這個標記進站的訪客不會渲染出這個按鈕', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "誠心推薦·優質租管業者" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/Home.vue → 1，確認同一份檔案裡緊接著的另一個輪播區塊沒有用同一種進站來源條件包起來，只受限於是否有資料'}`

### 首頁「JGB平台十大特色」實際列出幾項？（標題寫十大，目前輪播只設定 3 項：管理儀表板、線上合約管理、即時帳務報表）
- 講法：JGB平台十大特色有哪些／首頁特色介紹內容／十大特色是哪些功能
- 給誰看：prospect
- 首頁「JGB平台十大特色」區塊底下的輪播資料目前只設定了 3 項：「管理儀表板」（手機、電腦各種介面輕鬆管理，招租、收支情況一目了然）、「線上合約管理」（獨家租賃智能合約，合法線上電子簽約）、「即時帳務報表」（完整資金報表，精準掌控現金流以及各項費用明細查詢），標題文字寫「十大」但資料筆數不是十筆。〔src/pages/listings/Home.vue〕
- 這個區塊底下有「查看所有功能」與「了解價格方案」兩個按鈕，分別連到產品特色頁與價格方案頁。〔src/pages/listings/Home.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/Home.vue | sed -n "/showRoom: \\[/,/showRoomFocus: 0,/p" | grep -c "^[[:space:]]*titleKey:"', 'result': '3 — 「JGB平台十大特色」標題下方對應的 state.showRoom 陣列只定義了 3 個以 titleKey 開頭的項目（用行首錨定排除同樣含有 titleKey 字樣的 subtitleKey 欄位）', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/Home.vue | sed -n "/advantages: \\[/,/advantagesFocus: 0,/p" | grep -c "^[[:space:]]*titleKey:" → 3，同一個檔案裡緊接著的 state.advantages 陣列（對應「JGB平台擁有三大優勢」）也剛好是 3 項，證明「標題數字與陣列筆數相符」在同一個檔案裡是做得到的，只是十大特色這一段沒有做到'}`

### 首頁說 JGB 在東南亞幾個城市使用？（超過 8 個城市，旁邊有免費試用／免費諮詢按鈕）
- 講法：JGB服務幾個城市／首頁城市數字／JGB東南亞據點／首頁免費試用按鈕在哪
- 給誰看：prospect
- 首頁有一個區塊寫著「東南亞超過 8 個城市都在使用 JGB Smart Property」，旁邊並排「免費試用」與「免費諮詢」兩個按鈕。〔src/pages/listings/Home.vue〕

### 首頁的線上諮詢小幫手正式站看得到嗎？（目前設定為正式環境不顯示，只在非正式環境出現）
- 講法：首頁有線上客服小幫手嗎／官網有聊天機器人嗎／為什麼官網看不到諮詢小幫手
- 給誰看：property_manager
- 首頁雖然掛載了售前諮詢小幫手，但目前的顯示條件只在「非正式環境」才會出現，正式環境（也就是一般訪客看到的正式官網）目前不會顯示這個小幫手。〔src/pages/listings/Home.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "window.APP_ENV !== \'production\'" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- src/pages/listings/Home.vue', 'result': '1 hit — 售前諮詢小幫手元件的掛載條件正是這一句', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/Home.vue | grep -c "Assistant" → 2，確認這個元件確實有被 import 並在模板中掛載，不是完全沒接線的死碼，只是掛載條件排除了正式環境'}`
- ⚠️ 待查：只讀了 listings/Home.vue 這一個檔案，不能排除同一個小幫手元件是否在其他官網頁面（例如價格頁、產品特色頁）用不同條件掛載並在正式環境顯示；此處只確認首頁這一支檔案目前的掛載條件是排除正式環境。

### 首頁「JGB平台擁有三大優勢」是哪三項？（提高出租效率、自動化管房流程、提升租客服務品質）
- 講法：JGB三大優勢是什麼／首頁三大優勢介紹／JGB平台優勢
- 給誰看：prospect
- 首頁「JGB平台擁有三大優勢」區塊依序是：「快速提高房源出租管理效率」（提供房東專屬物件刊登頁並轉發社群媒體）、「自動化管房流程」（支援手機介面 24 小時檢視數據報告）、「提升租客服務品質」（即時簽約及帳單通知，支援線上報修）。〔src/pages/listings/Home.vue〕

### 首頁「最新消息」顯示什麼？（沒有消息資料時整區塊不會出現，點擊會開啟幫助中心文章）
- 講法：首頁最新消息在哪／最新消息點進去是什麼／首頁消息輪播
- 給誰看：prospect
- 「最新消息」區塊只有在有取得消息資料時才會顯示，用輪播呈現每則消息的縮圖、分類標籤、標題與發布時間。〔src/pages/listings/Home.vue〕
- 點擊消息縮圖或標題，會另開分頁導向幫助中心的對應文章頁面。〔src/pages/listings/Home.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/Home.vue | sed -n \'/v-if="news"/,/<\\/Slick>/p\' | grep -v \'<!--\' | grep -c \'item.description\'', 'result': '0 — 最新消息輪播卡片裡沒有渲染 item.description 這個欄位（同一份程式碼裡有一行印 item.description 的 div，但整行被 <!-- --> 註解掉），確認實際顯示的只有縮圖、分類標籤、標題、發布時間四項', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/Home.vue | sed -n \'/v-if="news"/,/<\\/Slick>/p\' | grep -v \'<!--\' | grep -c \'item.created_at\' → 1，確認同一個範圍內『發布時間』（item.created_at）確實有未被註解掉、會渲染的一行，證明抓法能正確分辨有渲染跟被註解掉的差別'}`

### 首頁「企業夥伴」放了什麼？（10 個合作夥伴 logo 排成靜態方格，不是輪播）
- 講法：企業夥伴是誰／首頁合作夥伴logo／企業夥伴區塊內容
- 給誰看：prospect
- 首頁「企業夥伴」區塊目前用 10 個合作夥伴 logo 圖檔排成靜態方格呈現（桌機每列 5 個、手機每列 2 個），不是輪播，也不附文字說明每個 logo 對應的公司名稱。〔src/pages/listings/Home.vue〕
- 否定查證：`{'sentence_index': 0, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/Home.vue | sed -n "/企業夥伴/,/IWBI.png/p" | grep -c Slick', 'result': '0 — 企業夥伴區塊（從標題到下一個 IWBI 圖片區塊之間）完全沒有用到 Slick 元件', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:src/pages/listings/Home.vue | sed -n "/最新消息/,/企業夥伴/p" | grep -c Slick → 2，確認緊接在前面的『最新消息』區塊確實有用 Slick 元件，證明 grep 抓得到 Slick、不是工具本身失效'}`

## 中華電信雲市集訂單頁（3 條；頁：web:customers.tcloud）

### 雲市集訂單頁顯示什麼？（訂單編號、時間、採購方案、價格、點數折抵、付款狀態）
- 講法：雲市集訂單頁面內容／台灣雲市集訂單資訊／雲市集訂單狀態怎麼看／雲市集訂單點數
- 給誰看：property_manager、prospect
- 頁面標題是「臺灣雲市集訂單資訊」，列出雲市集訂單編號、訂單時間、採購方案、方案價格（TWD）、使用雲市集點數（點）。〔resources/views/customer/tcloud.blade.php〕
- 訂單狀態只有「已付款」或「待付款」兩種；已付款且系統有記錄付款資料時，還會多顯示匯款帳戶末 5 碼。〔resources/views/customer/tcloud.blade.php〕
- 頁面下方另外列出客戶資訊（公司統編、公司名稱）與付款資訊（匯款銀行、匯款帳號、匯款金額／自付額）。〔resources/views/customer/tcloud.blade.php〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/customer/tcloud.blade.php | grep -oE "訂單狀態：\\{\\{ ___\\(\'[^\']+\'\\) \\}\\}" | sort -u | wc -l', 'result': '2 — 整份頁面裡『訂單狀態：』後面接的文案只有兩種不重複的值（已付款、待付款），沒有第三種狀態字樣', 'positive_control': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show b2ee2ac382ce06763798a7238e4fd5c9411fcfaa:resources/views/customer/tcloud.blade.php | grep -c '訂單狀態：' → 3，確認『訂單狀態：』這個標籤真的在 if／elseif／else 三個分支各出現一次，抓法沒有漏看任何分支"}`

### 雲市集訂單怎麼付款？（國泰世華一次性虛擬帳號限 WebATM，2 個工作天內付款，付款後 2 天開發票、7 天內開通）
- 講法：雲市集訂單怎麼繳費／雲市集付款期限／雲市集開通要多久／雲市集虛擬帳號怎麼轉帳
- 給誰看：property_manager、prospect
- 匯款銀行固定是國泰世華銀行（代碼 013），匯款帳號是系統配發給這筆訂單的一次性虛擬帳號，注意事項寫明「請透過 WebATM 進行轉帳，避免付款失敗」。〔resources/views/customer/tcloud.blade.php〕
- 注意事項要求收到匯款資訊後 2 個工作天內完成付款。〔resources/views/customer/tcloud.blade.php〕
- 款項確認後，會在 2 個工作天內開立電子發票，7 個工作天內開通服務。〔resources/views/customer/tcloud.blade.php〕

### 雲市集訂單連結為什麼會失效？（連結簽章驗證不過，或訂單編號查無資料，都會導回官網首頁）
- 講法：雲市集連結失效／雲市集訂單頁打不開／雲市集付款連結驗證失敗／雲市集訂單查無資料
- 給誰看：property_manager、prospect
- 進入這個訂單頁面前，系統會先驗證連結上的簽章，驗證不通過時會導回官網首頁，並提示「驗證失敗，如有任何問題，請聯繫JGB客服。」〔app/Http/Controllers/CustomerController.php〕
- 如果連結裡的訂單編號在系統裡查不到對應資料，一樣會導回官網首頁，提示「此付款連結已失效，如有任何問題，請聯繫JGB客服。」〔app/Http/Controllers/CustomerController.php〕
- 否定查證：`{'sentence_index': 1, 'cmd': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "此付款連結已失效，如有任何問題，請聯繫JGB客服。" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/CustomerController.php', 'result': "1 hit — 掛在 empty(\\$customerTCloud = DB::table('customer_tclouds')->where('id', \\$id)->first()) 判斷為真的分支", 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -nF "return view(\'customer.tcloud\', compact(\'customerTCloud\'));" b2ee2ac382ce06763798a7238e4fd5c9411fcfaa -- app/Http/Controllers/CustomerController.php → 1，確認查得到資料時走的是正常顯示頁面的另一條路徑，兩者互斥'}`
- ⚠️ 待查：程式裡的註解寫「1. 找不到對應id 2. 該訂單已被付款」暗示已付款的訂單也會被導回首頁，但實際判斷式只檢查資料是否存在（empty($customerTCloud)），並沒有另外針對「已付款」的狀態做導回處理——已付款的訂單目前仍會正常顯示頁面並標示「已付款」，這條註解與實際判斷式所寫的邏輯不一致，未能查到近期改動紀錄能解釋這個落差。
