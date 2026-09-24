---
coarse: I
title: 方案與導入
scope: 方案比較與試用、功能矩陣、導入與資料遷移、批次匯入流程、競品（deliberate_no）；⛔ 找真人走 handoff
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
---
## 方案與導入 {#I}
### 跟 Bananas、屋我也差在哪 {#jgb/I/competitor-comparison}
- phrasings:
  - {text: "Bananas", source: "question_summary:3607", status: approved}
  - {text: "屋我也", source: "question_summary:3607", status: approved}
  - {text: "租賃管理系統", source: "question_summary:3607", status: approved}
- sources: [kb:3607]
- reviewed: {by: owner, at: 2026-09-07}
- policy: deliberate_no
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
同類的租賃管理系統還有 Bananas、屋我也，三者都做物件、合約、帳務，差異主要在合約類型廣度、金流、IoT 整合與適用場景。
以公開官網可查的事實來說：金箍棒的合約類型較完整（涵蓋一般租賃、社會住宅、委託），金流支援多元（藍新／永豐／中信／國泰／愛金卡），並有智慧門鎖／電錶整合（硬體細節由專人說明）與大房東報表，適合社宅委託、需多元收款、要對業主交報表的代管團隊。
對方官網未明確提及的功能，我們無法替他們確認，建議您直接向對方詢問。
若想實際比較，歡迎預約 demo。

### 會評論競爭對手嗎 {#jgb/I/competitor-neutrality}
- phrasings:
  - {text: "你們會評論競爭對手嗎", source: "question_summary:3609", status: approved}
  - {text: "怎麼看同業", source: "question_summary:3609", status: approved}
  - {text: "會說對手壞話嗎", source: "question_summary:3609", status: approved}
- sources: [kb:3609, kb:3798]
- policy: deliberate_no
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
我們不會評論同業的好壞或內部狀況，只就公開可查的事實、以及金箍棒實際適合的情境提供中立資訊；對方未明確提供的功能，建議您直接向對方確認，我們不會替他們斷言有或沒有。
若想實際比較，最準的方式是預約 demo 或直接開免費試用體驗。
5b. 競品處理協定（硬護欄）
不主動點名競品;使用者主動提到才回應
競品事實只能用本次提供的 E1 知識;E1 沒給就不講競品細節
對手未列明的功能說「不確定他們是否提供,建議直接向對方確認」
絕不斷言對方「沒有/不支援」,不貶低、不評對方內部狀況
不討論競品價格、不傳未經證實的負面訊息
比較後收束回 JGB 適用情境與優勢（E2）→ 導試用/demo
6. CTA 出口慣例
| 情境 | 出口 |
|---|---|
| 想試用 | trial_form |
| 想看 demo / 企業客 | demo_form |
| 問價格 | [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資 |
| 問 IoT 硬體 | 專人（點下方『找真人』） |
7. 功能對照索引（情境 → 推薦功能）
| 情境/痛點 | 推薦功能（點名用） |
|---|---|
| 退租結算、押金扣抵複雜 | 差額發票、押金設算息 |
| 收租對帳亂、催繳費 | 自動帳單、金流代收、儲值金 |
| 合約多、社宅/委託 | 電子簽章、社宅/委託合約 |
| 人多協作、對業主交代 | 團隊權限、大房東報表 |
| 現場抄表/換鎖 | 智慧電錶/門鎖（細節由專人）|
| 報修追蹤慢 | 線上報修、進度追蹤 |
| 物件分散難管 | 房源集中、社區歸戶、批次上傳 |
| 找房客、空屋招租 | 物件公開頁、VR 看屋 |
| 逾期未繳、要催繳 | 自動逾期提醒、滯納金 |
| 點交點退、續約解約 | 線上點交點退、續約解約 |
| 發票開錯要作廢 | 電子發票作廢 |
| 大量租客建檔 | 租客批次匯入 |
| 外籍/海外租客 | 多語系介面 |
| 想評估費用 | 導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資／點下方『找真人』 |

### 首頁儀表板顯示哪些數據 {#jgb/I/dashboard-overview}
- phrasings:
  - {text: "對外首頁會顯示哪些物件", source: "koyu:slug90#3", status: approved}
- sources: [draft:batch#8, helpcenter:Landlordonboarding00]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
登入後的首頁儀表板有三塊：收支情況（圖表化呈現，可自訂時間區間看營運趨勢）、帳務情況（近期的逾期待收款帳單與待繳費帳單，可點「更多」看明細）、修繕情況（租客目前申請中的修繕單）。
想看實際畫面可預約 demo。

### 舊系統資料能否匯入（可匯入範圍、不支援項目與批次匯入做法） {#jgb/I/data-migration}
- phrasings:
  - {text: "哪些能匯", source: "question_summary:5379", status: approved}
  - {text: "房東租客合約帳單", source: "question_summary:5379", status: approved}
  - {text: "批次匯入", source: "question_summary:5379", status: approved}
  - {text: "搬資料", source: "question_summary:5379", status: approved}
  - {text: "舊系統資料可以匯進來嗎", source: "question_summary:5379", status: approved}
  - {text: "合約能不能匯", source: "question_summary:5379", status: approved}
- sources: [kb:5379, docs:knowledge/jgb-product-facts.md#batch-import-scope, helpcenter:onboarding6, helpcenter:qa05, helpcenter:qa06, kb:3476]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
換系統最怕重建資料。
金箍棒可以用 Excel 範本批次匯入：物件（一般與社會住宅）、租客、社區、大房東聯絡簿；團隊（法人房東）帳號還能用「匯出草稿帳單→填寫→匯回」的方式批次更新帳單；合約與舊系統已繳完的歷史帳單不支援匯入。
搬遷細節可預約 demo，由專人依您的資料量評估。
要特別說明的是：合約目前不支援批次匯入，需要逐筆建立（線上電子簽新約，或上傳既有紙本合約 PDF 存檔）；舊系統已繳完的歷史帳單也沒有搬移功能。
大量新增租客可使用 Excel 批次匯入功能：1. 在租客管理頁面下載匯入範本（Excel 格式）；2. 依範本格式填寫租客資料（姓名、聯絡方式等）；3. 上傳填寫完成的 Excel 檔案；4. 系統自動驗證資料格式並匯入。
匯入過程中若有格式錯誤或重複資料，系統會提示需要修正的項目。
批次匯入適合一次性建檔大量租客，省去逐一手動輸入的時間。

### 可以免費試用嗎 {#jgb/I/free-trial}
- phrasings:
  - {text: "可以免費試用嗎", source: "question_summary:3611", status: approved}
  - {text: "試用多久", source: "question_summary:3611", status: approved}
  - {text: "多久可以提款", source: "koyu:advanced12#3", status: approved}
  - {text: "驗證碼多久可以重發", source: "koyu:tenantintro.register#3", status: approved}
- sources: [kb:3611]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
可以，新帳號享有免費試用一個月，註冊即可開始，先實際用過再決定。
需要協助開通可以留個聯絡方式，或直接預約 demo 由專人帶您看。

### 個人房東（約 10～30 戶）適配與建議做法 {#jgb/I/individual-landlord-scale-fit}
- phrasings:
  - {text: "個人房東", source: "question_summary:3596", status: approved}
  - {text: "免費試用", source: "question_summary:3596", status: approved}
  - {text: "多元金流", source: "question_summary:3597", status: approved}
  - {text: "帳務自動化", source: "question_summary:3597", status: approved}
  - {text: "物件合約帳務", source: "question_summary:3596", status: approved}
  - {text: "約10戶", source: "question_summary:3596", status: approved}
  - {text: "約20戶", source: "question_summary:3597", status: approved}
  - {text: "約30戶", source: "question_summary:3598", status: approved}
  - {text: "規模化", source: "question_summary:3598", status: approved}
  - {text: "銜接團隊大房東報表", source: "question_summary:3598", status: approved}
- sources: [kb:3596, kb:3597, kb:3598]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
管 10 間左右的個人房東，最花時間的通常是收租對帳和合約來回。
金箍棒把物件、合約、帳務集中在一個系統：線上電子簽章簽約、自動產帳單與金流代收、收租對帳一條龍，取代 Excel 與 LINE 的零散作業，也能發租客通知、處理報修。
建議先用免費試用一個月實際跑跑看；正式方案級距與費用調整中，可於定價頁(https://www.jgbsmart.com/pricing)查看或由專人為您說明，這裡不報數字。
管到 20 間左右，帳單與對帳的量明顯變大、人工容易出錯。
金箍棒的帳務模組（自動帳單、多元金流代收、電子發票、儲值金）能把收租對帳自動化，搭配物件管理、電子簽章合約、租客通知與修繕，讓一個人也管得動這個規模。
可先免費試用一個月感受效率差異；方案級距與費用請見定價頁(https://www.jgbsmart.com/pricing)或由專人提供，這裡不報過時數字。
管到 30 間左右，已接近個人經營的規模上限，物件與帳務都相當可觀；未來若開始多人協作或要對業主交報表，會很快需要團隊管理與大房東報表。
金箍棒在這階段能用物件、合約、帳務的完整自動化撐住現有規模，並可平順銜接到團隊方案。
建議先免費試用一個月；正式級距與費用調整中，請見定價頁(https://www.jgbsmart.com/pricing)或由專人為您盤點，這裡不直接報價。

### 怎麼收費與方案分級差異 {#jgb/I/pricing-plans}
- phrasings:
  - {text: "多少錢", source: "question_summary:3610", status: approved}
  - {text: "怎麼收費", source: "question_summary:3610", status: approved}
  - {text: "公司方案多少錢", source: "koyu:Landlordonboarding02#20", status: approved}
- sources: [kb:3610, kb:5376, kb:3453]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
金箍棒採訂閱制，方案依管理規模（物件數）以及是否需要團隊、大房東報表、IoT 等功能分級。
目前方案與價格正在調整，為避免提供過時數字，實際級距與費用請參考線上定價頁(https://www.jgbsmart.com/pricing)，或留下聯絡方式由專人為您報價。
也歡迎先用免費試用一個月實際體驗。
金箍棒採訂閱制，方案依管理規模（物件數）以及是否需要團隊、大房東報表、IoT 等功能分級。
目前方案與價格正在調整，為避免提供過時數字，實際級距與費用請參考線上定價頁(https://www.jgbsmart.com/pricing)，或留下聯絡方式由專人為您報價。
也歡迎先用免費試用一個月實際體驗。
JGB 提供不同等級的訂閱方案，主要差異在於：（1）可管理的物件數量上限；（2）可設定的大房東數量上限；（3）可使用的進階功能（如 IoT 整合、差額發票等）。
免費方案可管理有限數量的物件，付費方案依等級提供更多物件額度和進階功能。
各方案詳細內容和價格可在「訂閱方案」頁面查看。
若目前方案的物件數量不夠用，可升級方案或加購額外物件額度。

### 系統總覽、能解決什麼問題與適不適合我 {#jgb/I/product-overview}
- phrasings:
  - {text: "你們系統介紹", source: "question_summary:3585", status: approved}
  - {text: "合不合用", source: "question_summary:3585", status: approved}
  - {text: "怎麼用", source: "question_summary:3585", status: approved}
  - {text: "想了解金箍棒", source: "question_summary:3585", status: approved}
  - {text: "想看看你們", source: "question_summary:3585", status: approved}
  - {text: "物業管理", source: "question_summary:3585", status: approved}
  - {text: "適不適合我用", source: "question_summary:3585", status: approved}
  - {text: "你們能解決什麼問題", source: "question_summary:3606", status: approved}
  - {text: "管理困擾", source: "question_summary:3606", status: approved}
- sources: [kb:3585, kb:3606, draft:batch#1, kb:3798]
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
金箍棒智慧物管能把物件、合約、收租對帳到智慧設備集中在一個系統管理。
想知道適不適合您，先讓我了解一下您的狀況。
管理租賃常見的收租對帳、合約、人多協作、報修等問題，金箍棒都有對應的模組。
想知道我們怎麼解決您的狀況，先選一個您最想改善的：
5b. 競品處理協定（硬護欄）
不主動點名競品;使用者主動提到才回應
競品事實只能用本次提供的 E1 知識;E1 沒給就不講競品細節
對手未列明的功能說「不確定他們是否提供,建議直接向對方確認」
絕不斷言對方「沒有/不支援」,不貶低、不評對方內部狀況
不討論競品價格、不傳未經證實的負面訊息
比較後收束回 JGB 適用情境與優勢（E2）→ 導試用/demo
6. CTA 出口慣例
| 情境 | 出口 |
|---|---|
| 想試用 | trial_form |
| 想看 demo / 企業客 | demo_form |
| 問價格 | [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資 |
| 問 IoT 硬體 | 專人（點下方『找真人』） |
7. 功能對照索引（情境 → 推薦功能）
| 情境/痛點 | 推薦功能（點名用） |
|---|---|
| 退租結算、押金扣抵複雜 | 差額發票、押金設算息 |
| 收租對帳亂、催繳費 | 自動帳單、金流代收、儲值金 |
| 合約多、社宅/委託 | 電子簽章、社宅/委託合約 |
| 人多協作、對業主交代 | 團隊權限、大房東報表 |
| 現場抄表/換鎖 | 智慧電錶/門鎖（細節由專人）|
| 報修追蹤慢 | 線上報修、進度追蹤 |
| 物件分散難管 | 房源集中、社區歸戶、批次上傳 |
| 找房客、空屋招租 | 物件公開頁、VR 看屋 |
| 逾期未繳、要催繳 | 自動逾期提醒、滯納金 |
| 點交點退、續約解約 | 線上點交點退、續約解約 |
| 發票開錯要作廢 | 電子發票作廢 |
| 大量租客建檔 | 租客批次匯入 |
| 外籍/海外租客 | 多語系介面 |
| 想評估費用 | 導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資／點下方『找真人』 |

### 方案物件額度上限與用滿怎麼辦 {#jgb/I/property-quota-limit}
- phrasings:
  - {text: "凶宅怎麼辦", source: "koyu:rentallaw.pt2#18", status: approved}
  - {text: "免費方案可以建幾個物件", source: "gapmap:C07", status: approved}
- sources: [draft:batch#3, docs:knowledge/jgb-product-facts.md#free-plan-quota]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
金箍棒的方案是依可管理的物件數分級，物件額度用滿就無法再新增，可以升級方案、加購額度，或把不再使用的物件下架釋放額度；目前用量在「訂閱方案」頁看得到。
各方案的物件數級距請以線上定價頁為準 [查看方案與費用](https://www.jgbsmart.com/pricing)。
免費方案預設可建 5 個物件（免費試用一個月就是免費方案），實際額度以帳號內「訂閱方案」頁顯示為準。
新帳號享有免費試用一個月，可先實際體驗再選方案。

### 升級、變更、續約與取消訂閱（含付款紀錄） {#jgb/I/subscription-change-renewal}
- phrasings:
  - {text: "升級更換", source: "question_summary:3454", status: proposed}
  - {text: "取消訂閱", source: "question_summary:3455", status: proposed}
  - {text: "自動續訂", source: "question_summary:3457", status: proposed}
  - {text: "訂閱付款紀錄", source: "question_summary:3457", status: proposed}
  - {text: "退訂流程", source: "question_summary:3455", status: proposed}
- sources: [draft:batch#4, helpcenter:Landlordonboarding02, kb:3454, kb:3356, kb:3455, kb:3457]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
方案的變更在「團隊管理」的「訂閱方案」頁：點「變更」、選物件數量對應的年／月方案、完成付款即生效，支出可在「付款紀錄」查看。
訂閱到期會自動續約扣款；若扣款失敗，方案會失效、物件會被系統自動下架，補完付款後再重新上架即可。
要取消訂閱，在方案頁下方的服務條款連結點「取消訂閱」。
升級或更換訂閱方案：進入帳號設定中的「訂閱方案」頁面，查看目前方案資訊後選擇「更換方案」，挑選新方案並完成付款即可。
升級後新方案立即生效，物件額度即時更新。
方案費用依選擇的付費週期（月繳/年繳等）不同。
系統支援信用卡付款，付款成功後會收到訂閱回條通知。
取消訂閱的操作步驟：
1. 點選左側選單「其他設定」>「訂閱方案」
2. 點選「變更」
3. 在價格方案下方找到服務條款連結，點選藍字「取消訂閱」即可完成
取消訂閱流程：進入帳號設定的「訂閱方案」頁面，選擇「取消訂閱」並確認。
取消後方案會在目前付費週期結束時失效，期間仍可正常使用所有功能。
取消後物件刊登數若超過免費方案上限，超出的物件會自動下架。
已建立的合約和帳單資料不受影響，但部分進階功能將無法使用。
若要重新訂閱，可隨時再次選購方案。
訂閱付款紀錄可在帳號設定的「付款紀錄」頁面查看，包含每次扣款的金額、日期和付款狀態。
系統預設自動續訂：在方案到期前 5 天會發送續訂提醒通知，到期時自動以原付款方式扣款續訂。
若自動扣款失敗（如信用卡過期、額度不足），系統會通知並給予補繳期限。
未在期限內完成付款，方案將降為免費版。

### 訂閱扣款失敗：方案失效、物件下架與恢復 {#jgb/I/subscription-payment-failure}
- sources: [kb:3509, kb:3457]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
訂閱扣款失敗時，系統會清除方案並將物件全部自動下架，多數功能會暫時無法使用。
處理方式：到「訂閱方案」頁確認方案狀態與付款方式（更換有效的信用卡或付款管道），完成續約付款後方案恢復，再將物件重新上架即可。
若付款方式正常仍扣款失敗，請聯繫客服協助。
訂閱付款紀錄可在帳號設定的「付款紀錄」頁面查看，包含每次扣款的金額、日期和付款狀態。
系統預設自動續訂：在方案到期前 5 天會發送續訂提醒通知，到期時自動以原付款方式扣款續訂。
若自動扣款失敗（如信用卡過期、額度不足），系統會通知並給予補繳期限。
未在期限內完成付款，方案將降為免費版。

### 公司或包租代管團隊適合嗎 {#jgb/I/team-company-fit}
- phrasings:
  - {text: "全模組", source: "question_summary:3584", status: approved}
  - {text: "公司團隊方案", source: "question_summary:3584", status: approved}
  - {text: "包租代管物管", source: "question_summary:3584", status: approved}
  - {text: "團隊權限", source: "question_summary:3584", status: approved}
- sources: [kb:3584]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
公司或團隊（包租代管、物管）通常要多人分工，還得對業主交報表，需求比個人房東複雜。
金箍棒的全模組方案正好對應這種規模——除了物件、合約、帳務，還有團隊權限管理讓成員分工，以及大房東報表，把代收代付與營運狀況整理好、對業主交代清楚；若有現場抄電表或換門鎖的需求，智慧電錶／門鎖也能依需求整合（細節由專人說明）。
實際適合的模組組合與費用會依團隊規模而不同，建議直接預約 demo，由專人陪您盤點需求並提供報價。

### 為什麼選金箍棒 {#jgb/I/why-choose-jgb}
- phrasings:
  - {text: "差異化", source: "question_summary:3608", status: approved}
  - {text: "為什麼選金箍棒", source: "question_summary:3608", status: approved}
  - {text: "有多語系介面嗎", source: "gapmap:C46", status: approved}
  - {text: "外籍租客能用嗎", source: "gapmap:C46", status: approved}
- sources: [kb:3608]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
選金箍棒的主要理由在「合約類型廣 + 多元金流 + IoT 整合 + 規模化團隊管理」：合約涵蓋一般／社會住宅／委託（社宅與委託代管尤其完整）、金流支援藍新／永豐／中信／國泰／愛金卡、可串接智慧門鎖／電錶（細節由專人說明）、多人權限搭配大房東報表方便對業主交代，另有押金設算息、VR 看屋、6 國語系等加值，且新帳號享免費試用一個月。
想實際體驗可直接開試用或預約 demo。

### 房東新手教學總覽（從哪開始、各篇教學有哪些） {#jgb/I/onboarding-tutorial-index}
- sources: [helpcenter:Landlordonboarding]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
