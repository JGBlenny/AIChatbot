---
coarse: I
title: 方案與導入
scope: 方案比較與試用、功能矩陣、導入與資料遷移、批次匯入流程、競品（deliberate_no）；⛔ 找真人走 handoff
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 方案、價格與免費試用 {#I-pricing}
### JGB 有哪些方案？（免費試用、體驗方案、入門／熱門／專業四級距、企業方案） {#jgb/I/pricing-plan-tiers-overview}
- phrasings:
  - {text: "有哪些方案", source: "draft:outline-20260920", status: proposed}
  - {text: "方案分幾種", source: "draft:outline-20260920", status: proposed}
  - {text: "方案怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "價格方案介紹", source: "draft:outline-20260920", status: proposed}
  - {text: "哪個方案適合我", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/pricing/Home.vue, code:src/pages/listings/pricing/parts/PlanForm.vue, code:app/Http/Controllers/ApiController.php, code:src/pages/listings/pricing/parts/PlanAndDevice.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
方案頁把付費方案分成「體驗方案」「入門方案」「熱門方案」「專業方案」四個級距，其中入門方案涵蓋 50、100、150 個物件，熱門方案涵蓋 200 到 450 個物件並標示為最熱門，專業方案為 500 個物件。
除了頁面上列出的四個級距，另外還提供不綁信用卡的「免費試用」方案，以及只能透過聯繫窗口洽談的「企業方案」。
方案價格依物件數量分級計費，頁面上可切換「月費」或「年費」兩種計費週期查看價格。
企業方案主打客製化專屬 LOGO 頁與客製化專屬網址頁，是提供給大型企業的解決方案，需點選「深入了解企業方案」導向預約 demo 頁面洽談，頁面上不會顯示企業方案的價格。
### 免費試用怎麼開始、能用多久？（企業團隊與社宅房東建立身分時自動取得，個人房東未帶優惠代碼時自動取得；一個週期後不自動續訂） {#jgb/I/pricing-free-trial-eligibility}
- phrasings:
  - {text: "免費試用能用多久", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼取得免費試用", source: "draft:outline-20260920", status: proposed}
  - {text: "免費方案會自動續訂嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "試用期多長", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/pricing/parts/PlanAndDevice.vue, code:app/User.php, code:config/defaultplan.php]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
價格頁的「免費試用方案」寫著「不綁信用卡的30天的試用方案，歡迎體驗」，點「免費註冊試用」會另開註冊頁。
企業團隊與社宅房東身分建立時，一律自動取得免費方案；個人房東則是註冊過程沒有帶入優惠代碼時，才自動取得免費方案。
免費方案的效期是系統設定的一個週期（目前為一個月），到期後不會自動續訂。
個人房東如果是透過優惠代碼連結完成註冊，取得的是優惠代碼指定的方案，而不是這個自動贈送的免費方案。
### 免費試用不能用哪些功能？（最多 5 個物件，不支援團隊與門鎖電錶等進階功能） {#jgb/I/pricing-free-trial-feature-scope}
- phrasings:
  - {text: "免費方案有什麼限制", source: "draft:outline-20260920", status: proposed}
  - {text: "免費試用不能用什麼功能", source: "draft:outline-20260920", status: proposed}
  - {text: "免費方案物件上限", source: "draft:outline-20260920", status: proposed}
  - {text: "免費試用支援哪些功能", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/template-parts/LightboxFreePlan.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
免費試用最多可新增 5 個物件、支援批次物件上傳，並擁有智能合約（內政部最新標準範本）、支援既存合約、一般匯款、自動催繳通知、即時帳務報表、分店管理、租客管理等功能。
免費試用不支援 720° VR、團隊成員管理、大房東管理、編輯權限設定、智能門鎖、智能電錶等功能。
免費試用彈窗裡把自動對帳列在不支援的功能，並註記「無法申請國泰、永豐可申請藍新、中信」；不過能不能開通某家金流還要看身分，例如個人房東連藍新也不能開通（另見「哪些身分或方案不能開通某些金流商」）。
### 個人房東與企業團隊方案差在哪？（團隊成員管理等四項功能、自動對帳與分店管理起始級距不同） {#jgb/I/pricing-individual-vs-corporate-team}
- phrasings:
  - {text: "個人房東跟團隊方案差別", source: "draft:outline-20260920", status: proposed}
  - {text: "團隊方案多什麼功能", source: "draft:outline-20260920", status: proposed}
  - {text: "企業團隊方案內容", source: "draft:outline-20260920", status: proposed}
  - {text: "個人跟公司方案不一樣嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/pricing/Home.vue, code:app/Http/Controllers/ApiController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
方案頁目前只會顯示企業團隊身分適用的方案內容與功能比較表，頁面上沒有讓使用者切換成個人房東身分查看內容的入口。
系統另外定義了一份個人房東專用的方案比較表：「團隊成員管理」「編輯權限設定」「團隊資訊」「進階設定」四項功能，個人房東的入門、熱門、專業、體驗方案全部都不提供；企業團隊則除了體驗方案外，入門、熱門、專業方案都提供這四項功能。
自動對帳在個人房東的比較表裡，入門、熱門、專業、體驗方案顯示的都是文字說明「無法申請國泰、永豐可申請藍新、中信」；企業團隊的比較表裡，入門、熱門、專業方案顯示為打勾支援，只有體驗方案不支援。
分店管理在個人房東的比較表裡，體驗、入門、熱門、專業方案全部支援；企業團隊的比較表裡則是體驗方案不支援，入門、熱門、專業方案才支援。
大房東管理在兩份比較表裡的支援情形完全相同：體驗方案不支援，入門、熱門、專業方案都支援。
### 免費方案與體驗方案差在哪？（前者系統贈送 5 個物件，後者每月付費可續訂 10 個物件） {#jgb/I/pricing-free-vs-experience-plan}
- phrasings:
  - {text: "免費方案跟體驗方案差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "免費方案跟體驗方案哪裡不同", source: "draft:outline-20260920", status: proposed}
  - {text: "體驗方案是免費的嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "免費方案可以續訂嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/pricing/parts/FAQ.vue, code:src/pages/listings/pricing/parts/PlanForm.vue, code:app/User.php, code:config/defaultplan.php, code:src/pages/listings/template-parts/LightboxFreePlan.vue]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
免費方案是系統在建立房東身分時自動贈送的測試方案（個人房東帶優惠代碼註冊時取得的是優惠方案），在一個月的測試期間內可以創建 5 個物件，並擁有智能合約功能。
體驗方案是提供給想要數位轉型的短期試用方案，在方案期限內可以創建 10 個物件，同樣擁有智能合約功能，而且可以自行續訂來延長試用期限。
體驗方案跟其他付費方案一樣，可以在頁面上切換查看「月費」或「年費」兩種計費週期的價格；不像免費方案是系統贈送、價格固定為 0。
### 怎麼用物件數量試算方案價格？（50～500 物件拉桿試算，超過 500 個要洽企業方案） {#jgb/I/pricing-calc-by-estate-count}
- phrasings:
  - {text: "怎麼算方案價格", source: "draft:outline-20260920", status: proposed}
  - {text: "物件數量怎麼換算價格", source: "draft:outline-20260920", status: proposed}
  - {text: "我有幾間房適合哪個方案", source: "draft:outline-20260920", status: proposed}
  - {text: "價格試算工具", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/pricing/parts/CalculatePrice.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
方案頁提供「計算方案價格」拉桿工具，方案最少始於 50 個物件，拉桿範圍是 50 到 500 個物件、每格間距 50。
拉桿的「物件」定義為管理的房源數，例如管理五間收租房源就算五個物件。
拉桿拉到 500（拉桿上限）時，頁面會提示物件數量超過 500 個以上需要洽詢企業方案。
試算出的價格是根據輸入的物件數量估算，不包含任何適用稅費與加購費用；年繳的折扣已經包含在顯示的年繳價格內。
選定物件數量後按「選擇方案」，會直接帶著方案、計費週期（月費／年費）與物件數量一起跳轉到訂閱頁面。
### 物件額度快滿了會怎樣？（剩 5 個以下觸發提醒，剛好剩 5 個另寄 Email） {#jgb/I/pricing-quota-near-full-notice}
- phrasings:
  - {text: "物件額度快滿了會通知嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "物件數量快到上限怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "方案物件用完前有提醒嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "額度不夠怎麼知道", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Estate.php, code:app/Notification.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增物件時，若訂閱中的身分剩餘可新增物件數量在 5 個以下，系統會發送站內通知中心訊息提醒即將額滿。
當剩餘物件數量剛好只剩 5 個時，系統會再另外寄一封 Email 通知使用者接近訂閱方案的物件數量上限。
這個提醒只在身分目前有生效中的訂閱時才會觸發，沒有生效中的訂閱不會收到這個提醒。
### 企業方案提供什麼？（客製化 LOGO 頁與網址頁，需另外聯繫洽談） {#jgb/I/pricing-enterprise-plan-offer}
- phrasings:
  - {text: "企業方案內容", source: "draft:outline-20260920", status: proposed}
  - {text: "企業方案怎麼申請", source: "draft:outline-20260920", status: proposed}
  - {text: "大型企業方案", source: "draft:outline-20260920", status: proposed}
  - {text: "客製化方案怎麼談", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/pricing/parts/PlanAndDevice.vue, code:src/pages/listings/pricing/parts/CalculatePrice.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
企業方案標榜「客製化專屬 LOGO 頁」與「客製化專屬網址頁」兩項功能，定位為適合大型企業的企業級解決方案。
企業方案沒有在頁面上列出價格，要點選「深入了解企業方案」連結導向預約 demo 頁面另外洽談。
物件數量超過 500 個（試算拉桿上限）時，系統會提示改為聯繫企業方案。
### 體驗方案介紹頁講什麼？（每月費用試算、體驗方案資格需求、客戶見證、免費試用／免費諮詢按鈕） {#jgb/I/pricing-trial-plan-landing-page}
- phrasings:
  - {text: "體驗方案介紹頁", source: "draft:outline-20260920", status: proposed}
  - {text: "體驗方案要多少錢", source: "draft:outline-20260920", status: proposed}
  - {text: "體驗方案資格需求", source: "draft:outline-20260920", status: proposed}
  - {text: "查看體驗方案會看到什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/pricing/TrialPlan.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
體驗方案介紹頁的標題文案是「小成本輕鬆管房非夢事」，副標會即時換算並顯示「每月只需 [金額] 元，JGB Smart Property 就提供您管理房源所需的一切」，金額是用台幣 100 元即時換算成使用者當地幣別。
頁面用三段搭配截圖的功能介紹依序說明物件及廣告管理、線上合約管理、自動金流管理。
頁面中段放了一則合作客戶的見證，並附一支介紹影片連結。
頁面下段「體驗方案資格需求」列出兩項條件：管理房源時間不到兩年的「新創時期」，以及過去沒有使用過 JGB 平台的「全新客戶」。
頁面上下各有一組「免費試用」與「免費諮詢」按鈕，「免費試用」會開啟免費方案彈窗，「免費諮詢」會另開分頁導向預約 demo 表單。
### 方案價格怎麼算、年繳有折扣嗎？（各方案單價從系統價格表讀取；一般方案年繳等於 10 個月的月費） {#jgb/I/pricing-plan-price-basis}
- phrasings:
  - {text: "方案價格數字", source: "draft:outline-20260920", status: proposed}
  - {text: "年繳折扣多少", source: "draft:outline-20260920", status: proposed}
  - {text: "體驗方案價格怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "方案價格從哪裡算出來", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, code:app/Helper.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
包含體驗方案在內，各方案的實際單價與級距價格都是從系統的方案物件價格表讀出來的，不是固定寫死的數字，因此這裡無法列出各級距的金額。
一般依物件數量分級方案的年繳費用，計算方式是月費乘以 10（等於少收 2 個月的費用）；體驗方案的年繳費用則是月費乘以 12，沒有這個折扣。
### 物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案） {#jgb/I/pricing-quota-full-block}
- phrasings:
  - {text: "物件額度用滿了", source: "draft:outline-20260920", status: proposed}
  - {text: "額度滿了不能新增物件", source: "draft:outline-20260920", status: proposed}
  - {text: "訂閱失效還能新增物件嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "方案額度用完提示", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/EstateController.php, code:app/Http/Middleware/SubscriptionCheck.php, code:app/Http/Middleware/PremisesLimitCheck.php, code:resources/views/layouts/lightbox/general.blade.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
物件列表新增物件、批次匯入物件、社區底下新增物件等多個入口，在送出前都會先檢查目前身分的訂閱是否還在生效中、以及剩餘可新增物件數量是否還夠。
只要訂閱已經失效，或是剩餘可新增物件數量不足，這些入口都會擋下操作並改成提示使用者方案額度已滿，導向升級方案，而不是真的建立物件。
彈出視窗的標題一律是「已達到數量上限」，內文與按鈕依目前身分是否為有效訂閱中而不同。
有效訂閱中時，內文會寫出方案名稱與物件上限，並問「要升級方案嗎」，按鈕文字是「前往升級」。
沒有有效訂閱時，內文是請使用者「請先前往訂閱服務，即可享受所有您需要的功能」，按鈕文字是「我要訂閱」。
訂閱已失效時，複製物件、編輯物件、刊登招租廣告這些入口，也會出現同一個彈窗。
## 訂閱、付款與訂單 {#I-subscription-payment}
### 訂閱頁怎麼選方案？（體驗方案、依物件數量拉桿的基本方案、企業方案洽談三選一） {#jgb/I/subscription-choose-plan-flow}
- phrasings:
  - {text: "訂閱頁怎麼選方案", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼變更訂閱方案", source: "draft:outline-20260920", status: proposed}
  - {text: "選方案時可以選幾種", source: "draft:outline-20260920", status: proposed}
  - {text: "方案物件數量怎麼拉", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/subscription/Chose.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
選擇方案頁提供三種方案：「體驗方案」、依物件數量計價的「基本方案」（涵蓋原本的入門／熱門／專業級距）、以及需另外洽談的「企業方案」（點擊後導向預約 demo 表單）。
選基本方案時用拉桿選擇物件數量，範圍是 50 到 500，每格間距 50，價格與方案名稱會隨拉桿即時更新。
拉桿不能拖拉到低於目前已上傳的物件數量，如果目前物件數量超過拉桿最小值，拉桿會自動跳到能容納目前物件數的最小級距，並顯示「無法選擇比已上傳物件數量小的方案」的提示。
只有目前方案為空、體驗方案或免費方案時，體驗方案選項才能點選；已經是基本方案或更高方案的使用者，體驗方案選項會顯示為灰階樣式且無法點擊。
### 訂閱怎麼扣款？（先試刷 TWD 1 驗證信用卡、藍新金流走 SSL／PCI-DSS） {#jgb/I/subscription-payment-authorization-flow}
- phrasings:
  - {text: "訂閱怎麼付款", source: "draft:outline-20260920", status: proposed}
  - {text: "訂閱扣款安全嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "信用卡驗證怎麼跑", source: "draft:outline-20260920", status: proposed}
  - {text: "確認扣款會怎樣", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/subscription/Chose.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
還沒完成信用卡授權前，付款按鈕顯示「前往授權」；授權完成後之後每次調整方案，按鈕會改成「前往付款」，點擊後彈出「扣款提醒」再次確認才會送出。
第一次授權信用卡時，系統會試刷 TWD 1 元確認信用卡有效，約定成功後隨即取消這筆 TWD 1 的扣款，不會真的收這 1 元。
付款流程由合作服務商藍新金流提供線上刷卡支付服務，其系統架構採用 SSL 256bit 加密機制，並符合 PCI-DSS 國際安全認證。
按下「確認扣款」後會直接更新訂閱方案並執行扣款，頁面會提醒使用者在送出前再次確認方案與金額細節。
### 訂閱時發票資訊要填什麼？（二聯式／三聯式、統一編號僅三聯式必填；地址欄目前沒有掛必填檢查） {#jgb/I/subscription-invoice-fields}
- phrasings:
  - {text: "訂閱發票怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "二聯式三聯式差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "統一編號要填嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "訂閱要留Email跟電話嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/subscription/Chose.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
訂閱付款頁的發票類型可切換「二聯式」或「三聯式」，兩者共用同一組表單只是欄位開關不同。
「買受人」在兩種發票類型下都要填；「統一編號」只有選三聯式時才會顯示且為必填欄位。
地址分成國家、縣市、鄉鎮區、詳細地址四欄；畫面上「地址」標題沒有標示必填記號，畫面上的必填檢查與錯誤提示邏輯目前沒有啟用，等於這四個欄位目前實際上沒有被強制要求填寫。
Email 在二聯式發票時標示為必填，三聯式則非必填；聯絡電話則兩種類型都不是必填欄位。
### 訂閱優惠碼怎麼用？（輸入後即時驗證，續訂優惠次數沒有設定上限時顯示「終生」） {#jgb/I/subscription-coupon-and-renewal-discount}
- phrasings:
  - {text: "訂閱優惠碼怎麼輸入", source: "draft:outline-20260920", status: proposed}
  - {text: "優惠碼兌換", source: "draft:outline-20260920", status: proposed}
  - {text: "續訂優惠次數", source: "draft:outline-20260920", status: proposed}
  - {text: "續訂優惠可以用多久", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/subscription/Chose.vue, code:src/pages/users/subscription/MyPlan.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
選擇方案頁可以輸入優惠碼並按「兌換」，系統會即時回覆這組優惠碼是否合法及對應訊息，已套用的優惠碼會列在下方，可以個別移除。
訂閱完成後，「我的方案」頁會顯示目前方案的「續訂優惠」折扣金額與「剩餘續訂優惠次數」。
剩餘續訂優惠次數如果沒有設定，畫面會顯示為「終生」，代表這個優惠沒有次數上限；有設定次數時才會顯示實際剩餘次數。
### 我的方案頁看什麼？（方案卡片、付款方式綁定狀態、溢繳費用） {#jgb/I/subscription-my-plan-page}
- phrasings:
  - {text: "我的方案頁面內容", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼看目前訂閱方案", source: "draft:outline-20260920", status: proposed}
  - {text: "溢繳費用是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "付款方式在哪裡看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/subscription/MyPlan.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「我的方案」頁左側卡片顯示方案名稱、物件數量級距、額外戶數（如果有加購）與方案價格；右側顯示付款方式與溢繳費用。
若已綁定信用卡會顯示卡別圖示、卡號與到期日；未綁定時顯示「尚未綁定」。
### 怎麼換綁信用卡？（更新要重新授權並試刷 1 元，變更方案按鈕需要對應權限） {#jgb/I/subscription-change-card-flow}
- phrasings:
  - {text: "怎麼換綁信用卡", source: "draft:outline-20260920", status: proposed}
  - {text: "更換信用卡要重新授權嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有權限可以變更方案嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "變更按鈕按不下去", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/subscription/MyPlan.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
要更換綁定的信用卡，點「更新」會先跳出提醒視窗，說明更換需要重新授權，屆時會試刷一塊錢，按「前往更換」才會繼續流程。
頁面上的「變更」按鈕只有在使用者具備變更訂閱方案的權限時才可以點擊，沒有這個權限的人看到的是無法點擊的灰階樣式。
### 換方案時舊方案沒用完的錢會退嗎？（按剩餘天數比例換算成溢繳金，直接折抵新方案費用） {#jgb/I/subscription-plan-change-billing}
- phrasings:
  - {text: "升級方案舊方案的錢退嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "降級方案會退費嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "溢繳金怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "換方案生效時間", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在選擇方案頁重新提交訂閱時，系統會立即生效這次的方案變更，不是等到原方案到期才切換。
系統會依照目前方案「剩餘天數 ÷ 方案總天數」的比例，把原方案未使用完的費用換算成溢繳金，直接折抵這次要繳的金額，折抵不完的部分才會列為應付金額。
### 取消訂閱會怎樣？（立即停止自動續訂與已授權信用卡，但用到目前效期結束才失效） {#jgb/I/subscription-cancel-effect}
- phrasings:
  - {text: "取消訂閱馬上失效嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "取消訂閱要選原因嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "取消訂閱後還能用多久", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼取消訂閱", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/subscription/Unsubscribe.vue, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
取消訂閱前系統會告知：目前訂閱的方案資格會持續到方案到期日當天，到期後才不會自動續訂，屆時也無法再繼續使用 JGB 的所有服務——也就是取消動作立即生效的是「停止自動續訂」，不是立刻停用目前方案。
取消時必須從「我不再需要使用相關服務」「無法解決我遇上的問題」「費用昂貴」「其他」四個原因中選一個才能送出；選「其他」的話還要填寫說明文字，否則「確定」按鈕維持無法點擊的樣式。
送出取消後，系統會清除該身分的自動續約資料與已授權的信用卡約定資料。
取消動作能不能送出，看的是目前身分是否已經沒有「自動續約資料」——即使目前仍是有效訂閱中的免費方案（沒有自動續約資料），一樣會被這個檢查擋下、直接跳出系統忙碌的錯誤訊息，不會進入原因選擇畫面；這跟目前方案是否還在生效中無關。
### 自動續訂扣款失敗會怎樣？（方案資料整個清空、限額歸零、所有物件立即下架，沒有寬限期） {#jgb/I/subscription-renewal-charge-failure}
- phrasings:
  - {text: "續訂扣款失敗怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "自動續約失敗會下架物件嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有信用卡授權會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "續訂失敗有寬限期嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Console/Commands/AutoRenewSubscription.php, code:app/Role.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
排程續訂時，如果目前身分已經沒有信用卡扣款授權，或是不符合可續訂的條件（例如沒有首次訂閱日或方案週期資料），系統會直接視同不續訂，把訂閱方案資料整個清空、所有方案限額歸零，並且把目前已上架的物件全部下架；同一支排程如果進行到實際刷卡續訂但扣款失敗，也是走一樣的清空與下架流程。
訂閱方案資料被清空後，方案物件數量、合約數量、團隊成員數量、大房東數量等限額全部歸零，首次訂閱日、方案開始日、結束日、續約日等日期欄位也都被清空，等於整個回到沒有訂閱方案的狀態。
物件下架的範圍是目前所有「刊登中」或「買賣廣告」的物件，會被直接改成非刊登、非上架狀態。
這整個流程沒有任何寬限期或重試機制——系統沒有多留幾天再檢查一次或延後下架的邏輯，扣款失敗或條件不符當次排程就會立即清空並下架。
### 付款紀錄頁看什麼？（扣款日、訂單編號、付款內容、金額、收據） {#jgb/I/orders-payment-history}
- phrasings:
  - {text: "付款紀錄在哪裡看", source: "draft:outline-20260920", status: proposed}
  - {text: "訂單紀錄怎麼查", source: "draft:outline-20260920", status: proposed}
  - {text: "收據在哪裡下載", source: "draft:outline-20260920", status: proposed}
  - {text: "扣款紀錄列表", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/orders/Index.vue, code:app/Http/Controllers/UserController.php, code:routes/web.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
付款紀錄頁以清單方式列出每一筆已完成扣款：扣款日、訂單編號、「付款內容」、金額、以及「收據」連結；付款內容欄列的是這筆扣款買的品項，例如訂閱的方案名稱與物件數（有數量時後面會標出乘以幾份），再加上這筆訂單本身附帶的說明文字，沒有任何項目時顯示「無」。
如果目前身分完全沒有付款紀錄，頁面會顯示「目前尚未有任何付款紀錄」。
頁面提示「如果紀錄有疑慮，請聯繫JGB客服」。
### 收款設置支援哪些金流商？（藍新／國泰世華／永豐／中信／icash Pay／現金收款帳戶，各家設定費與手續費不同） {#jgb/I/payment-vendor-options-overview}
- phrasings:
  - {text: "收款設置支援哪些金流", source: "draft:outline-20260920", status: proposed}
  - {text: "線上收款要收多少費用", source: "draft:outline-20260920", status: proposed}
  - {text: "金流申請要錢嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "手續費可以轉嫁給租客嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/routerView/Add.vue, code:src/pages/users/payment/_parts/CashBanks.vue, doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
收款設置頁面可以新增的線上金流商包括藍新、國泰世華、永豐、中信、icash Pay，此外也可以另外新增「現金收款帳戶」讓租客用現金或匯款方式繳費。
國泰世華與永豐銀行要自行向銀行申請，首次設定費都是 5,000 元；中國信託與藍新則是直接在 JGB 系統線上申請，設定費全免。
各家手續費不同：國泰世華虛擬 ATM 免費、超商條碼每筆 10 至 20 元；永豐虛擬 ATM 每筆 3 元、信用卡每筆 1.85%；中國信託虛擬 ATM 免費；藍新虛擬 ATM 實體繳納每筆 15 元、網路繳納每筆 20 元、信用卡國內每筆 2.4%、國外每筆 3%、超商代碼每筆 28 元。
藍新的手續費規定一律由收款方（房東）自行吸收，不能轉嫁給租客；國泰世華的超商條碼手續費則可以自行設定要由租客或房東負擔；選擇中國信託則要注意租客必須自己有中信帳戶並用中信 App 才能繳費。
藍新的超商代碼繳費方式另外還有租金金額限制：只能用來繳交 30 元以上、20,000 元以下的款項，超過這個範圍就不能選超商代碼繳費。
以上金流商不是每個身分或方案都能開通：個人房東不能開通藍新、國泰世華、永豐；免費方案與體驗方案不能開通國泰世華、永豐。
### 哪些身分或方案不能開通某些金流商？（個人房東不能開藍新／國泰世華／永豐，免費方案／體驗方案不能開國泰世華／永豐） {#jgb/I/payment-vendor-eligibility-by-role-and-plan}
- phrasings:
  - {text: "個人房東能開藍新嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "免費方案能開國泰世華嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "金流商為什麼不能選", source: "draft:outline-20260920", status: proposed}
  - {text: "收款方式被鎖住怎麼辦", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, code:src/pages/users/payment/routerView/Add.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
系統回傳可開通金流商列表時，若目前身分是「個人房東」，藍新、國泰世華、永豐三家都會被標成不可開通；若不是個人房東、但目前方案是「免費方案」或「體驗方案」，則只有國泰世華、永豐會被標成不可開通，藍新不受此限制。
被標成不可開通的金流商在選單上仍以正常顏色顯示，點選後畫面不會出現該金流商的申請表單，改以紅字顯示「您無法開通此收款方式，若有問題請洽詢JGB客服」；選單上金流商變成灰階是另一件事，代表這家金流已經開通滿三組帳號。
### 藍新金流申請要注意什麼？（個人房東無法申請；手機與 Email 送出後不能改，每個金流最多開三組帳號，需審核） {#jgb/I/payment-newebpay-setup-details}
- phrasings:
  - {text: "藍新金流怎麼申請", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新申請資料能改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "金流最多能開幾組帳號", source: "draft:outline-20260920", status: proposed}
  - {text: "藍新審核要多久", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/_parts/Newebpay.vue, code:src/pages/users/payment/routerView/Add.vue, doc:/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/qa27_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
申請藍新科技前要先確認目前身分能不能開通：個人房東完全不能開通藍新（點選藍新後不會出現申請表單，改以紅字提示改洽 JGB 客服），以下申請細節只適用於能開通藍新的身分。
申請藍新科技時填寫的手機號碼與 Email，送出申請後就不能再修改，因為它們會分別成為藍新的管理者帳號與通知信箱。
藍新申請時填寫的商店名稱，系統會自動加上固定字首後才送出；用於提領入帳款項的銀行帳戶，規定必須是帳號申請人本人所有。
同一個帳號每個金流最多可以開通三組帳號。
只要有勾選開通信用卡（含國外信用卡）付款方式，藍新就需要三個工作天以上的審核時間，實際天數依藍新官方審核進度調整。
### 金流綁定後還能改嗎？（綁定資料都是唯讀；國泰世華只能補填還沒填齊的超商條碼欄位） {#jgb/I/payment-vendor-edit-after-binding}
- phrasings:
  - {text: "收款方式可以改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "金流明細可以編輯嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "綁定後想改資料怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "哪個金流可以重新送審", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/routerView/Detail.vue, code:src/pages/users/payment/_parts/Cathaybk.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
綁定成功後點進明細頁查看，各家金流商的資料都是唯讀、不能再編輯重送；唯一的例外是國泰世華：如果當初超商條碼相關欄位還沒填齊，明細頁可以補填這一段再送出，其他已綁定的欄位仍然不能改。
### 藍新／中信收款帳戶申請要多久？（藍新：智付通至少 2-5 個工作天；中信 ACH 驗證約 5 個工作天） {#jgb/I/payment-icash-ctbc-setup}
- phrasings:
  - {text: "藍新申請要多久", source: "draft:outline-20260920", status: proposed}
  - {text: "中信收款帳戶審核多久", source: "draft:outline-20260920", status: proposed}
  - {text: "智付通開通要多久", source: "draft:outline-20260920", status: proposed}
  - {text: "ACH驗證是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/routerView/Add.vue, code:src/pages/users/payment/_parts/Ctbc.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
選擇藍新、而且目前身分可以開通藍新時，頁面會提醒：智付通將存取申請資料以完成開通程序，需要至少 2 到 5 個工作天；個人房東不能開通藍新，選了藍新只會看到無法開通的紅字提示，不會出現這段提醒。
選擇中國信託時，頁面說明送審後會由 JGB 進行 ACH 驗證並撥款 1 元到收款帳號，審核時間需要 5 個工作天（不含例假日）。
### 收據範本有哪些？（財政部包租業租金收據範本只有法人／社宅團隊才看得到） {#jgb/I/payment-receipt-template-options}
- phrasings:
  - {text: "收據範本有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "財政部範本怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "一般收據怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "收據要不要開通", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/_parts/Receipt.vue, code:src/utils/constants/paymentSetting.ts]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般個人房東的收據類型只有兩種可選：「超商繳費單、JGB系統收據」與「超商繳費單、不檢附收據」；只有當下身分是法人或社宅團隊時，選單才會多出另外三種含「財政部包租業租金收據」或「JGB系統繳費單」的組合，總共五種可選。
選擇含「財政部包租業租金收據」的組合時，必須先在團隊資訊內填寫公司登記證日期、公司登記證縣市、公司登記證號，否則範本內容會缺資料。
收據可以上傳一張用印圖片作為正式收款依據，限定 JPG、PNG 檔，最多 1 張，檔案大小上限 10MB；這個上傳欄位不受收據類型限制、一律顯示，只有沒有「編輯收款設置」權限時才會整區塊變灰無法操作，跟收據類型選了哪一種、目前身分是不是團隊都無關。
### 押金收據能自訂摘要跟蓋章嗎？（摘要與三顆收款章都只有特定合作團隊才看得到） {#jgb/I/payment-receipt-deposit-team-extras}
- phrasings:
  - {text: "押金收據摘要怎麼改", source: "draft:outline-20260920", status: proposed}
  - {text: "收據可以蓋章嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "押金收據印章設定", source: "draft:outline-20260920", status: proposed}
  - {text: "押金收據字數上限", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/_parts/Receipt.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
押金收據的「摘要」欄開頭文字可以自訂、最多 20 個字（留空沿用團隊名稱），以及設定三顆收款章（主辦出納、主辦會計、機構首長）蓋印於押金收據對應的用印格——這一整塊設定只有特定的合作團隊身分才會顯示，一般房東完全看不到這個區塊。
### 帳單怎麼開電子發票？（要先聯繫 JGB 業務開通加值服務，開通後才會出現稅與發票分頁） {#jgb/I/payment-bill-e-invoice-setup}
- phrasings:
  - {text: "帳單怎麼開發票", source: "draft:outline-20260920", status: proposed}
  - {text: "電子發票怎麼啟用", source: "draft:outline-20260920", status: proposed}
  - {text: "合約怎麼設定要不要開發票", source: "draft:outline-20260920", status: proposed}
  - {text: "發票功能怎麼申請", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/_parts/Invoice.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
帳單開立發票功能預設不是啟用狀態，要先開通電子發票加值服務，再聯繫 JGB 業務才能啟用。
功能啟用完成後，「編輯合約」畫面才會多出「稅與發票」分頁，用來設定這份合約未來收款時的帳單是否要開立發票。
發票的開立模式一般只有「帳單已到帳後開立」；部分特定合作團隊另外可以選「預先開立發票」，再設定「預先開立發票時機」為「發送帳單」「繳費期限前」或「繳費期限後」，選後兩者時還要指定天數。
### 沒有查看權限會怎樣？（收款設置與訂閱方案選單整個不會出現） {#jgb/I/payment-permission-menu-visibility}
- phrasings:
  - {text: "沒有權限看不到收款設置", source: "draft:outline-20260920", status: proposed}
  - {text: "訂閱方案選單不見了", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼找不到訂閱方案", source: "draft:outline-20260920", status: proposed}
  - {text: "查看訂閱方案權限的作用", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Role.php, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
側邊選單的【收款設置】與【訂閱方案】分別看團隊成員有沒有「查看收款設置」「查看訂閱方案」權限；沒有對應的權限時，該選單會整個不出現，而不是變成灰色不能點。
### 帳單可以自動排程發送、指定收款人嗎？（提前 0～20 天自動發送，收款人可選原簽約者／主要經理人／自訂） {#jgb/I/payment-bill-autosend-and-recipient}
- phrasings:
  - {text: "帳單自動發送設定", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單提前幾天發送", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單收款人怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "收款人可以改成別人嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/payment/_parts/OtherSetting.vue, code:src/pages/users/payment/_parts/Receipt.vue, code:src/utils/constants/paymentSetting.ts]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「帳單自動排定發送」可以設定「幾天前」，選項是不啟用、當天、或提前 1 到 20 天；系統會依照設定的天數，把已經填寫完成（或不需填水電瓦斯等生活費用細節）的帳單，在繳費截止日前自動排入待發送帳單列表，例如截止日 05/05、設定提前 5 天，系統會在 04/30 早上 7 點把該筆帳單排入列表。
這個自動發送排程設定只有在目前身分是有效訂閱中才會顯示。
「帳單收款人」可以選「原簽約者」「主要經理人」或「自訂」；選「自訂」時要額外填寫收款人、聯絡人、聯絡人電話、Email 四個欄位，選其他兩個選項則不需要，會直接送出設定；這整組帳單收款人設定只在收據類型選「1. 超商繳費單、財政部包租業租金收據、JGB系統收據」「3. 超商繳費單、JGB系統收據」「4. JGB系統繳費單、JGB系統收據」時才會顯示，選「2. 超商繳費單、財政部包租業租金收據」或「5. 超商繳費單、不檢附收據」時整組不顯示。
## 預約 demo {#I-demo-booking}
### 預約 demo 表單要填什麼？（公司、職稱、聯絡方式、物件所在地、感興趣功能與諮詢內容） {#jgb/I/demo-form-fields}
- phrasings:
  - {text: "預約demo要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼申請demo", source: "draft:outline-20260920", status: proposed}
  - {text: "聯繫我們表單欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "demo表單怎麼填", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/DemoForm.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
預約 demo 表單（頁面標題「聯繫我們」）要填公司名稱、職稱、姓名、電話、Email、物件所在地（國家/城市）、物件數量、團隊人數、最有興趣的功能（可複選）與諮詢內容，並勾選同意 JGB 隱私權政策。
頁面下方標示「所有資訊皆必填」，「送出」按鈕的顏色會依畫面上是否已填妥公司名稱、職稱、姓名、電話、Email、物件所在地、感興趣功能、物件數量、團隊人數、諮詢內容這 10 個欄位並勾選隱私權政策，在灰色與可點擊的主色之間切換，但按鈕本身一律可以點擊；實際擋下送出的是每個欄位上的瀏覽器對必填欄位的內建檢查，未填妥必填欄位時是瀏覽器原生驗證跳出提示、擋下表單送出，不是這個顏色判斷式在擋。
「最有興趣的功能」選項是複選核取方塊，畫面會要求至少勾選一項；其餘欄位都是單選下拉選單或文字輸入框。
### demo 表單的下拉選項有哪些？（物件數量 7 級距、團隊人數 6 級距、感興趣功能 6 項） {#jgb/I/demo-form-option-lists}
- phrasings:
  - {text: "物件數量選項有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "團隊人數怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "感興趣功能有哪些選項", source: "draft:outline-20260920", status: proposed}
  - {text: "demo表單職稱選單", source: "draft:outline-20260920", status: proposed}
- sources: [code:config/demoform.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「物件數量」分成 1-10、11-30、31-50、50-100、100-200、200-300、300戶以上 共 7 個級距可選。
「團隊人數」分成 1-15、16-30、31-50、51-100、101-500、501-1000 共 6 個級距可選。
「最有興趣的功能」可複選的項目是房源管理、租約管理、帳務管理、團隊管理、智慧門鎖、智慧電錶共 6 項。
「職稱」下拉選單提供公司負責人、公司主要管理者、行銷主管、業務主管、營運主管、財務主管、技術主管、行銷窗口、業務窗口、營運窗口、財務窗口、技術窗口、其他共 13 個選項。
### demo 表單送出後多久有人聯繫？（顯示感謝頁，2-3 個工作天內專人聯繫） {#jgb/I/demo-form-submit-result}
- phrasings:
  - {text: "demo表單送出後多久聯繫", source: "draft:outline-20260920", status: proposed}
  - {text: "預約demo後會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "填完表單多久有人回覆", source: "draft:outline-20260920", status: proposed}
  - {text: "demo表單送出成功畫面", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/DemoForm.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
表單送出成功後會切換成感謝畫面，寫著「謝謝您完成預約表單」，並提示「感謝您完成填寫表單，將會有專人於 2-3 天工作天聯繫您」，畫面上有按鈕可以回到官網首頁。
### demo 表單哪些欄位真的會被系統擋下？（畫面上全部欄位都要填才能送出；系統端只再檢查公司、姓名、電話、Email 四項） {#jgb/I/demo-form-actual-validation-scope}
- phrasings:
  - {text: "demo表單哪些欄位真的必填", source: "draft:outline-20260920", status: proposed}
  - {text: "實際驗證跟畫面要求一樣嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "demo表單漏填會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "demo表單驗證規則", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/IndexController.php, code:src/pages/listings/DemoForm.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
表單頁面上全部 10 個欄位與隱私權同意都設了必填，沒填完時瀏覽器會先擋下送出；系統收到資料後，只會再檢查公司名稱、姓名、電話、Email 這四個欄位是否為空、以及 Email 格式是否正確。
## 控制台（設定、通知信範本、自動化任務） {#I-control-panel}
### 控制台首頁目前能用什麼？（目前只有「任務管理器」一個項目可以點擊進入，而且只開放給特定合作團隊） {#jgb/I/control-panel-entry-scope}
- phrasings:
  - {text: "控制台有什麼功能", source: "draft:outline-20260920", status: proposed}
  - {text: "控制台首頁能做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "控制台目前可以用哪些設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/control-panel/Index.vue, code:src/routes/controlPanel.js]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
控制台首頁的說明是「管理您的 JGB 系統」，目前畫面上實際可以點擊進入的項目只有「任務管理器」一項。
任務管理器的卡片說明是「設定您的排程機器人，在滿足設定的條件後，可以觸發自動操作」；點擊後，只有開放控制台的特定合作團隊會進入任務管理器頁面，其他帳號會被導回會員中心首頁。
### 進入控制台設定後看到什麼？（上方三層麵包屑與左側「控制台」側邊欄，內容是任務管理器、新增／編輯任務或通知信設定頁） {#jgb/I/control-panel-setting-shell}
- phrasings:
  - {text: "控制台設定頁內容", source: "draft:outline-20260920", status: proposed}
  - {text: "任務管理器上一層是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "控制台麵包屑", source: "draft:outline-20260920", status: proposed}
  - {text: "控制台側邊欄", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/control-panel/setting/Index.jsx, code:src/routes/controlPanel.js, code:src/pages/control-panel/_parts/OrderAside.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點進控制台的設定範圍後，畫面上方會顯示「Dashboard」「控制台」「任務管理設定」三層麵包屑，內容區顯示的是任務管理器、新增／編輯任務，或通知信設定頁面。
在任務管理器與通知信設定頁，桌面版畫面左側會有「控制台」側邊欄，欄內目前只有「任務管理設定」一項；新增、編輯任務時不顯示側邊欄。
手機版沒有左側欄，改成頁面上方一條顯示目前項目名稱的選單列，點開可以選項目。
### 任務管理器是做什麼用的？（設定週期性任務或預定通知的排程功能） {#jgb/I/task-manager-purpose}
- phrasings:
  - {text: "任務管理器是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "自動化任務怎麼運作", source: "draft:outline-20260920", status: proposed}
  - {text: "排程機器人是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "任務管理器用途", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/control-panel/taskManagement/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
任務管理器頁面的說明是：設定週期性的任務、或是預定通知，設定完成後，系統會自動在指定週期前完成單據的開立，並寄信通知。
任務列表可以用「社區」「任務類型」篩選，也可以用任務名稱關鍵字搜尋；沒有符合篩選條件時顯示「沒有符合的結果」，完全沒有建立過任務時顯示「目前尚無任務資料」。
### 新增任務能選哪些類型？（目前只開放「通知」類型，行為是信件通知或站內通知） {#jgb/I/task-manager-type-behavior-scope}
- phrasings:
  - {text: "任務類型有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "任務行為可以選什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "可以設定修繕單自動開單嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "通知任務怎麼設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Services/TaskService.php, code:src/pages/control-panel/taskManagement/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增任務時，任務類型目前只有「通知」一種可以選，對應的任務行為是「信件通知」或「站內通知」兩種。
任務管理器列表頁的說明文字雖然舉例提到「週期修繕單」，但目前新增任務時可以選的任務類型只有「通知」，「修繕管理」目前沒有這個選項。
### 任務週期怎麼設定？（單位分年／月，方式可選僅一次、持續不停、特定日期結束、重複特定次數） {#jgb/I/task-manager-cycle-options}
- phrasings:
  - {text: "任務週期怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "任務可以只跑一次嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "任務可以設定結束日期嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "任務重複次數怎麼設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Services/TaskService.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
任務的週期單位可以選「年」或「月」。
任務的重複方式有四種：「僅一次」、「持續不停」、「特定日期結束」、「重複特定次數」。
### 新增任務表單有哪些欄位？（任務名稱、任務類型、關聯物件、任務行為、任務時間、重複間隔、結束時間、通知對象、通知內容） {#jgb/I/task-manager-form-fields}
- phrasings:
  - {text: "新增任務要填哪些欄位", source: "draft:outline-20260920", status: proposed}
  - {text: "任務表單內容", source: "draft:outline-20260920", status: proposed}
  - {text: "關聯物件怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "通知對象怎麼設定", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/control-panel/taskManagement/edit/Index.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增／編輯任務的表單依序是：「任務名稱」「任務類型」「關聯物件」（可全選或挑選特定物件）「任務行為」「任務時間」「重複間隔」「結束時間」（可再設定於某天結束或重複特定次數）「通知對象」（輸入 Email 或選擇團隊成員）與「通知內容」。
編輯已存在的週期性任務時，會多一個「編輯範圍」欄位，用來選擇這次修改只套用在這一項任務、還是套用在這項任務和後續任務。
### 已建立的任務怎麼編輯／刪除？（每筆任務可編輯、複製、刪除，編輯週期任務可選只改這次或連後續一起改） {#jgb/I/task-manager-edit-delete-copy}
- phrasings:
  - {text: "任務可以刪除嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "任務可以複製嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "編輯週期任務會影響後續任務嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "任務列表可以做什麼操作", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useTaskManagementTypes.js, code:app/Services/TaskService.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
任務列表每一列右側的齒輪選單提供三個動作：「編輯任務」「複製現有任務」「刪除任務」。
編輯週期性任務時，可以選擇修改範圍是「這項任務」（只改這一次）或「這項任務和後續任務」（連同之後每次排程一起改）。
### 通知信副本信箱可以設定嗎？（可以：會員側欄「通知收件信箱」頁每個通知類別最多再加 3 組；控制台裡的「通知信設定」頁只有說明、沒有新增欄位，也沒有入口） {#jgb/I/notification-mail-settings}
- phrasings:
  - {text: "通知信副本信箱怎麼加", source: "draft:outline-20260920", status: proposed}
  - {text: "通知信可以加幾個收件人", source: "draft:outline-20260920", status: proposed}
  - {text: "通知信預設寄給誰", source: "draft:outline-20260920", status: proposed}
  - {text: "通知信設定在哪裡", source: "draft:outline-20260920", status: proposed}
  - {text: "通知收件信箱在哪裡", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/control-panel/notificationMail/Index.jsx, code:src/pages/control-panel/Index.vue, code:src/pages/users/notification/Index.vue, code:src/use/config/useForwardNotificationEmails.ts, code:app/Role.php, code:app/Http/Controllers/UserController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
控制台裡有一個「通知信設定」頁面，頁面上的說明寫：通知信預設接收信箱是團隊擁有者的註冊信箱，每個通知信最多可以再新增 3 組副本信箱。
這個頁面目前只有這段說明文字，沒有可以新增副本信箱的欄位或按鈕；控制台首頁與側欄也沒有連到這個頁面的入口。
要新增通知信副本信箱，請到會員側欄的「通知收件信箱」頁：每個通知類別（例如合約管理類別、帳務管理類別、修繕管理類別）最多可以再新增 3 組信箱，按「新增信箱」填好後按「儲存」。
「通知收件信箱」頁只有企業團隊與社宅房東身分的側欄看得到，而且要有「查看所有通知」權限；有「編輯團隊通知」權限才能新增、刪除信箱並儲存，沒有的話只能看。
### 誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定」子路徑才會擋） {#jgb/I/control-panel-access-restriction}
- phrasings:
  - {text: "誰可以用控制台", source: "draft:outline-20260920", status: proposed}
  - {text: "租客可以設定任務管理嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "控制台權限限制", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼進不去控制台", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/controlPanel.js]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進入「設定」子路徑（任務管理、通知信設定）之前，系統會先檢查目前角色屬於哪個特定合作團隊角色分組，如果不屬於系統認可的分組，會直接被導回一般使用者頁面，無法進入。
這個角色分組檢查只掛在「設定」頁面上，控制台首頁本身沒有這道檢查，任何登入的身分都能開啟控制台首頁，只是首頁目前只有「任務管理器」一張卡片可以點擊進入。
新增任務、編輯任務與通知信設定這三個頁面都額外標記租客角色不允許使用。
## 官網首頁 {#I-marketing-home}
### 官網首頁有哪些區塊？（橫幅、熱門物件、優質租管業者推薦、特色介紹、企業夥伴、最新消息） {#jgb/I/homepage-sections-overview}
- phrasings:
  - {text: "首頁有什麼內容", source: "draft:outline-20260920", status: proposed}
  - {text: "官網首頁架構", source: "draft:outline-20260920", status: proposed}
  - {text: "JGB官網首頁介紹", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/Home.vue, code:src/pages/listings/template-parts/HomeTop.vue]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
首頁最上方是橫幅區塊，接著依序是「熱門物件」輪播、「誠心推薦·優質租管業者」輪播、「JGB平台十大特色」說明區塊、「JGB平台擁有三大優勢」、東南亞城市數與試用／諮詢按鈕、「最新消息」、「企業夥伴」，最下方還有一張圖片橫幅。
「熱門物件」區塊用輪播呈現每筆物件的縮圖、標題與地址等資訊；區塊底下連到找房搜尋頁的「查看更多物件」按鈕，只有首頁網址另外帶了特定搜尋參數時才會顯示，首頁上沒有任何連結會帶這個參數，一般直接造訪首頁看不到這個按鈕。
同樣是首頁網址帶了那個搜尋參數時，橫幅下方會多出找房搜尋面板，一般直接造訪首頁也不會顯示。
「誠心推薦·優質租管業者」區塊用輪播呈現使用 JGB 的租管業者推薦內容。
### 首頁「JGB平台十大特色」實際列出幾項？（標題寫十大，目前輪播只設定 3 項：管理儀表板、線上合約管理、即時帳務報表） {#jgb/I/homepage-ten-features-actual-count}
- phrasings:
  - {text: "JGB平台十大特色有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁特色介紹內容", source: "draft:outline-20260920", status: proposed}
  - {text: "十大特色是哪些功能", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/Home.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
首頁「JGB平台十大特色」區塊底下的輪播資料目前只設定了 3 項：「管理儀表板」（手機、電腦各種介面輕鬆管理，招租、收支情況一目了然）、「線上合約管理」（獨家租賃智能合約，合法線上電子簽約）、「即時帳務報表」（完整資金報表，精準掌控現金流以及各項費用明細查詢），標題文字寫「十大」但資料筆數不是十筆。
這個區塊底下有「查看所有功能」與「了解價格方案」兩個按鈕，分別連到產品特色頁與價格方案頁。
### 首頁說 JGB 在東南亞幾個城市使用？（超過 8 個城市，旁邊有免費試用／免費諮詢按鈕） {#jgb/I/homepage-city-count-cta}
- phrasings:
  - {text: "JGB服務幾個城市", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁城市數字", source: "draft:outline-20260920", status: proposed}
  - {text: "JGB東南亞據點", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁免費試用按鈕在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/Home.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
首頁有一個區塊寫著「東南亞超過 8 個城市都在使用 JGB Smart Property」，旁邊並排「免費試用」與「免費諮詢」兩個按鈕。
### 首頁的線上諮詢小幫手正式站看得到嗎？（目前設定為正式環境不顯示，只在非正式環境出現） {#jgb/I/homepage-presales-assistant-visibility}
- phrasings:
  - {text: "首頁有線上客服小幫手嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "官網有聊天機器人嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼官網看不到諮詢小幫手", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/Home.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
首頁雖然掛載了售前諮詢小幫手，但目前的顯示條件只在「非正式環境」才會出現，正式環境（也就是一般訪客看到的正式官網）目前不會顯示這個小幫手。
### 首頁「JGB平台擁有三大優勢」是哪三項？（提高出租效率、自動化管房流程、提升租客服務品質） {#jgb/I/homepage-three-advantages}
- phrasings:
  - {text: "JGB三大優勢是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁三大優勢介紹", source: "draft:outline-20260920", status: proposed}
  - {text: "JGB平台優勢", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/Home.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
首頁「JGB平台擁有三大優勢」區塊依序是：「快速提高房源出租管理效率」（提供房東專屬物件刊登頁並轉發社群媒體）、「自動化管房流程」（支援手機介面 24 小時檢視數據報告）、「提升租客服務品質」（即時簽約及帳單通知，支援線上報修）。
### 首頁「最新消息」顯示什麼？（用輪播呈現消息，點擊會開啟幫助中心文章） {#jgb/I/homepage-latest-news-section}
- phrasings:
  - {text: "首頁最新消息在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "最新消息點進去是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁消息輪播", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/Home.vue]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
「最新消息」區塊用輪播呈現每則消息的縮圖、分類標籤、標題與發布時間。
點擊消息縮圖或標題，會另開分頁導向幫助中心的對應文章頁面。
### 首頁「企業夥伴」放了什麼？（10 個合作夥伴 logo 排成靜態方格，不是輪播） {#jgb/I/homepage-enterprise-partners-section}
- phrasings:
  - {text: "企業夥伴是誰", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁合作夥伴logo", source: "draft:outline-20260920", status: proposed}
  - {text: "企業夥伴區塊內容", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/listings/Home.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
首頁「企業夥伴」區塊目前用 10 個合作夥伴 logo 圖檔排成靜態方格呈現（桌機每列 5 個、手機每列 2 個），不是輪播，也不附文字說明每個 logo 對應的公司名稱。
## 中華電信雲市集訂單頁 {#I-hicloud-order}
### 雲市集訂單頁顯示什麼？（訂單編號、時間、採購方案、價格、點數折抵、付款狀態） {#jgb/I/tcloud-order-info-fields}
- phrasings:
  - {text: "雲市集訂單頁面內容", source: "draft:outline-20260920", status: proposed}
  - {text: "台灣雲市集訂單資訊", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集訂單狀態怎麼看", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集訂單點數", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/customer/tcloud.blade.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
頁面標題是「臺灣雲市集訂單資訊」，列出雲市集訂單編號、訂單時間、採購方案、方案價格（TWD）、使用雲市集點數（點）。
訂單狀態只有「已付款」或「待付款」兩種；已付款且系統有記錄付款資料時，還會多顯示匯款帳戶末 5 碼。
頁面下方另外列出客戶資訊（公司統編、公司名稱）與付款資訊（匯款銀行、匯款帳號、匯款金額／自付額）。
### 雲市集訂單怎麼付款？（國泰世華一次性虛擬帳號，注意事項請用 WebATM 轉帳；收到匯款資訊後 2 個工作天內付款，款項確認後 2 個工作天內開發票、7 個工作天內開通） {#jgb/I/tcloud-payment-instructions}
- phrasings:
  - {text: "雲市集訂單怎麼繳費", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集付款期限", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集開通要多久", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集虛擬帳號怎麼轉帳", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/customer/tcloud.blade.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
匯款銀行固定是國泰世華銀行（代碼 013），匯款帳號是系統配發給這筆訂單的一次性虛擬帳號，注意事項寫明「請透過 WebATM 進行轉帳，避免付款失敗」。
注意事項要求收到匯款資訊後 2 個工作天內完成付款。
款項確認後，會在 2 個工作天內開立電子發票，7 個工作天內開通服務。
### 雲市集訂單連結為什麼會失效？（連結簽章驗證不過，或訂單編號查無資料，都會導回官網首頁） {#jgb/I/tcloud-link-invalid-cases}
- phrasings:
  - {text: "雲市集連結失效", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集訂單頁打不開", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集付款連結驗證失敗", source: "draft:outline-20260920", status: proposed}
  - {text: "雲市集訂單查無資料", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/CustomerController.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進入這個訂單頁面前，系統會先驗證連結上的簽章，驗證不通過時會導回官網首頁，並提示「驗證失敗，如有任何問題，請聯繫JGB客服」
如果連結裡的訂單編號在系統裡查不到對應資料，一樣會導回官網首頁，提示「此付款連結已失效，如有任何問題，請聯繫JGB客服」
