---
coarse: B
title: 團隊、人員與大房東
scope: 團隊建立與成員邀請、角色權限、人員管理、大房東記錄與代管關係；⛔ 帳號本身歸 A
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊） {#B-team-profile}
### 團隊資訊頁面可以設定什麼？（公司 Logo、團隊名稱、團隊介紹） {#jgb/B/team-basic-info}
- phrasings:
  - {text: "團隊資訊在哪裡設定", source: "draft:outline-20260920", status: approved}
  - {text: "團隊名稱怎麼改", source: "draft:outline-20260920", status: approved}
  - {text: "團隊介紹要寫什麼", source: "draft:outline-20260920", status: approved}
  - {text: "團隊首頁的介紹文字在哪改", source: "draft:outline-20260920", status: approved}
  - {text: "公司 Logo 怎麼上傳", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/role.blade.php, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
團隊管理的「團隊資訊」頁面「基本資訊」區塊，可以上傳公司 Logo、設定團隊名稱，並撰寫團隊介紹。
團隊介紹是要讓未來租客認識這個團隊的自我介紹文字，填寫後會顯示在團隊首頁上。
沒有編輯團隊資訊權限的帳號，這個頁面的欄位只能檢視、不能修改。
### 廣告頁聯絡資訊要填什麼？（Line ID、Facebook、WhatsApp 選填，公司電話與公司 Email 必填） {#jgb/B/team-ad-contact}
- phrasings:
  - {text: "廣告頁聯絡資訊要填什麼", source: "draft:outline-20260920", status: approved}
  - {text: "公司電話一定要填嗎", source: "draft:outline-20260920", status: approved}
  - {text: "WhatsApp 怎麼填", source: "draft:outline-20260920", status: approved}
  - {text: "廣告聯絡方式在哪設定", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/role.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
團隊資訊頁的「廣告頁聯絡資訊」會呈現在物件廣告上，讓租客可以透過更多管道與房東聯繫，提升簽約成功率。
這個區塊可以填寫 Line ID、Facebook 個人首頁連結；填寫 WhatsApp 時要包含國碼與電話號碼，國碼前面不需要打「+」。
公司電話與公司 Email 是這個區塊裡的必填欄位。
### 怎麼刪除團隊？（需先解除訂閱方案、輸入團隊名稱確認、刪除後資料無法恢復） {#jgb/B/team-delete}
- phrasings:
  - {text: "怎麼刪除團隊", source: "draft:outline-20260920", status: approved}
  - {text: "刪除團隊會怎樣", source: "draft:outline-20260920", status: approved}
  - {text: "刪除團隊的條件", source: "draft:outline-20260920", status: approved}
  - {text: "團隊解散流程", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/role.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有帳號本身擁有的團隊，團隊資訊頁才會顯示「刪除團隊」的入口。
如果團隊目前的訂閱方案尚未結束，系統會先提示要到「團隊管理」的「訂閱方案」解除現有訂閱，才能繼續刪除。
可以刪除時，畫面會列出這個團隊目前持有的物件數與合約數，並要求輸入團隊名稱才能按下刪除。
刪除團隊會同時清除這個團隊底下所有的物件、合約與帳務等資料，且無法恢復。
### 簽約資訊卡「個人資訊」區塊要填什麼？（只有租客與個人房東身分才有；姓氏、名稱、身分證字號、Email、手機、戶籍地址、通訊地址必填；身分證正反面與其他附件選填） {#jgb/B/team-signer-personal-info}
- phrasings:
  - {text: "簽約資訊個人欄位有哪些", source: "draft:outline-20260920", status: approved}
  - {text: "身分證正反面要傳嗎", source: "draft:outline-20260920", status: approved}
  - {text: "良民證要上傳嗎", source: "draft:outline-20260920", status: approved}
  - {text: "戶籍地址跟通訊地址一樣可以嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue, code:app/Role.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約資訊卡的「個人資訊」區塊只有租客與個人房東身分會顯示，法人房東與社宅團隊顯示的是「公司資訊」等區塊，不會有這個區塊；可以填寫刊登物件廣告與簽立合約時所需提供的資料：姓氏、名稱、身分證字號、Email、手機號碼都是必填。
戶籍地址與通訊地址也要填寫，通訊地址可以點「同戶籍地址」直接帶入。
身分證正反面照片是選填，另外還有一個「其他附件(選填)」區塊，可以選填上傳工作名片/學生證、良民證、小章這三項附件。
### 簽約資訊卡的「公司資訊」要填什麼？（公司登記名稱上限 20 字、公司統編皆為必填；公司負責人只有社宅團隊必填；社宅團隊還要填必填的社宅業者編號與公司登記證號） {#jgb/B/team-signer-company-info}
- phrasings:
  - {text: "公司登記名稱字數上限", source: "draft:outline-20260920", status: approved}
  - {text: "社宅業者編號在哪填", source: "draft:outline-20260920", status: approved}
  - {text: "公司登記證號要填嗎", source: "draft:outline-20260920", status: approved}
  - {text: "公司統編格式錯誤怎麼辦", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約資訊卡的「公司資訊」要填公司登記名稱（最多 20 字）與公司統編，這兩項不分一般團隊或社宅團隊都是必填。
「公司統編」欄位下方可以選擇統編類型是「公司統編(檢核)」還是「其他統編(不檢核)」，選「公司統編(檢核)」時會檢查統一編號格式，格式不對會顯示「公司統編格式錯誤」。
「公司負責人」只有社宅團隊是必填欄位，一般團隊則是選填。
「社宅業者編號」只有社宅團隊看得到，且是必填欄位；一般團隊沒有這一欄。
「公司登記證號」對社宅團隊是必填，一般團隊則是選填；「公司登記證日期」「公司登記證縣市」則是選填。
不過團隊要選用「財政部包租業租金收據範本」時，系統要求這三項都要先填寫完成。
### 簽約資訊卡的「經紀人資訊」要填什麼？（經紀人／經紀業名稱與證號，名稱上限 15 字；社宅團隊多了經紀人聯絡電話與 Email，且都是必填） {#jgb/B/team-signer-agent-info}
- phrasings:
  - {text: "經紀人名稱字數上限", source: "draft:outline-20260920", status: approved}
  - {text: "經紀業名稱可以不填嗎", source: "draft:outline-20260920", status: approved}
  - {text: "經紀人聯絡電話什麼時候要填", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約資訊卡有獨立的「經紀人資訊」區塊，可以填經紀人與經紀業各自的名稱、證號。
「經紀人名稱」與「經紀業名稱」都有 15 字的上限，超過會顯示已達上限的錯誤提示；一般團隊的經紀人名稱、證號、經紀業名稱、證號全部都是選填。
社宅團隊的經紀人名稱、經紀人證號會變成必填，還會多出「經紀人聯絡電話」「經紀人 Email」這兩個欄位、同樣必填；一般團隊看不到這兩個聯絡電話與 Email 欄位。
### 簽約資訊卡的「租賃住宅管理人員資訊」要填什麼？（姓名與證號；社宅團隊多了聯絡電話欄位，且姓名／證號／電話都是必填；沒有 Email 欄位） {#jgb/B/team-signer-manager-info}
- phrasings:
  - {text: "租賃管理人員要填哪些資料", source: "draft:outline-20260920", status: approved}
  - {text: "租賃管理人員聯絡電話要填嗎", source: "draft:outline-20260920", status: approved}
  - {text: "租賃住宅管理人員證號在哪填", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約資訊卡有獨立的「租賃住宅管理人員資訊」區塊，可以填租賃管理人員的名稱與證號，一般團隊這兩項都是選填。
社宅團隊的租賃管理人員名稱、證號都變成必填，還會多出「租賃管理人員聯絡電話」欄位、同樣必填；這個區塊沒有 Email 欄位。
### 簽約資訊卡可以上傳哪幾種圖章？（法人或社宅團隊的簽約資訊卡才看得到「附件」與「電子簽約圖章」兩個區塊；「附件」有公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章五種，「電子簽約圖章」另外只有一個「圖章」欄位） {#jgb/B/team-signer-stamps}
- phrasings:
  - {text: "圖章要上傳哪幾種", source: "draft:outline-20260920", status: approved}
  - {text: "電子簽約圖章是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "公司大章小章差在哪", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「附件」與「電子簽約圖章」這兩個區塊，只有簽約資訊卡屬於法人團隊或社宅團隊時才會出現；個人團隊的簽約資訊卡看不到這兩個區塊。
簽約資訊卡的「附件」區塊可以分別上傳公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章共五種圖章。
「電子簽約圖章」是另一個獨立區塊，只有一個「圖章」上傳欄位，跟「附件」區塊的五種圖章是不同的檔案；圖章上傳並儲存後，可以開啟「預設使用圖章取代親手簽名」，簽約時就會直接套用這個圖章。
### 一個團隊可以管理多組公司資訊嗎？（可以在「團隊資訊管理」視窗新增與刪除，但清單第一筆不能刪除） {#jgb/B/team-multi-company-info}
- phrasings:
  - {text: "可以設定多組公司資訊嗎", source: "draft:outline-20260920", status: approved}
  - {text: "公司資訊怎麼新增", source: "draft:outline-20260920", status: approved}
  - {text: "主要那組公司資訊可以刪除嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue, code:src/components/Lightbox/SignerInfosEdit.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約資訊卡片旁的「管理」按鈕會開啟「團隊資訊管理」視窗，會列出這個團隊目前所有的公司資訊，可以點「新增」加入一組新的公司資訊。
清單上每組公司資訊旁都有一個可以點擊刪除的圖示，但清單的第一筆沒有這個刪除圖示，不能被刪除。
### 沒有查看團隊資訊的權限，打開團隊資訊頁會怎樣？（提示「您目前登入的帳號無法查看團隊資訊功能」） {#jgb/B/team-info-no-view-permission}
- phrasings:
  - {text: "沒有權限看團隊資訊會怎樣", source: "draft:outline-20260920", status: approved}
  - {text: "團隊資訊頁打不開", source: "draft:outline-20260920", status: approved}
  - {text: "無法查看團隊資訊功能是什麼意思", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果目前登入的帳號沒有查看團隊資訊的權限，系統會提示「您目前登入的帳號無法查看團隊資訊功能」。
### 簽約資訊卡上有哪些地址欄位群？（個人的戶籍地址／通訊地址、公司的登記地址／通訊地址；社宅團隊另有經紀人與租賃管理人員各自的通訊地址） {#jgb/B/team-signer-address-groups}
- phrasings:
  - {text: "簽約資訊有哪些地址欄位", source: "draft:outline-20260920", status: approved}
  - {text: "通訊地址可以跟戶籍地址一樣嗎", source: "draft:outline-20260920", status: approved}
  - {text: "公司通訊地址在哪填", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
個人資訊區塊有「戶籍地址」與「通訊地址」兩組地址欄位，通訊地址可以點「同戶籍地址」直接帶入戶籍地址的內容。
公司資訊區塊有「公司登記地址」與「公司通訊地址」兩組地址欄位，公司通訊地址可以點「同公司登記地址」直接帶入。
社宅團隊還會多出「經紀人通訊地址」與「租賃管理人員通訊地址」這兩組獨立的地址欄位，一般團隊看不到這兩組。
### 怎麼在多組簽約資訊之間切換？（頁面上方有可切換的分頁列，超過 5 組時另外多出「所有團隊」下拉選單） {#jgb/B/team-signer-profile-switch}
- phrasings:
  - {text: "怎麼切換不同的簽約資訊", source: "draft:outline-20260920", status: approved}
  - {text: "簽約資訊太多組要怎麼選", source: "draft:outline-20260920", status: approved}
  - {text: "所有團隊下拉選單是什麼", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
團隊資訊管理裡新增的每一組公司資訊，都會在簽約資訊卡片上方變成一個可以點擊切換的分頁項目。
當公司資訊超過 5 組時，畫面會多出一個「所有團隊」的下拉選單；這個下拉選單列出的是全部組數（不是只有超過 5 組後多出來的部分），點選其中一項一樣可以切換過去。
## 成員列表（邀請、角色、成員名下資料） {#B-member-list}
### 成員列表可以看到什麼資訊？（加入時間、Email、手機號碼、目前的角色） {#jgb/B/member-list-overview}
- phrasings:
  - {text: "成員列表看得到什麼", source: "draft:outline-20260920", status: approved}
  - {text: "成員清單有哪些欄位", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼看成員的角色", source: "draft:outline-20260920", status: approved}
  - {text: "成員名下有沒有物件怎麼看", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/team/index.blade.php, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
成員列表標題旁會顯示成員人數，這個人數是下方一般成員列的筆數再加 1；以團隊擁有者身分登入時，剛好等於含團隊擁有者本人的總人數。
清單上每位成員都會顯示 Email、手機號碼，以及目前套用的角色名稱；加入時間只有一般成員那幾列有，團隊擁有者那一列和自己那一列的加入時間是空白。
### 怎麼邀請新成員加入團隊？（用 Email 或手機號碼搜尋，對方要先是 JGB 會員） {#jgb/B/member-invite}
- phrasings:
  - {text: "怎麼邀請成員", source: "draft:outline-20260920", status: approved}
  - {text: "新增成員流程", source: "draft:outline-20260920", status: approved}
  - {text: "邀請成員要對方先註冊嗎", source: "draft:outline-20260920", status: approved}
  - {text: "成員邀請用 email 還是手機", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/team/index.blade.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點擊成員列表的「邀請」按鈕會開啟「新增成員」視窗，可以選擇用 Email 或手機號碼搜尋要邀請的對象。
受邀請的對象如果不是 JGB 會員，將無法新增為團隊成員；輸入的 Email 或手機號碼查不到帳號時，會顯示「您輸入的帳號不存在」。
可以一次搜尋加入多位對象到「即將新增成員」清單，確認後一次送出邀請。
### 成員的「角色」權限決定什麼？（決定看得到與能編輯的物件、合約、帳務、修繕等範圍） {#jgb/B/member-role-concept}
- phrasings:
  - {text: "角色權限是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "角色能設定哪些權限", source: "draft:outline-20260920", status: approved}
  - {text: "團隊擁有者的權限跟一般成員一樣嗎", source: "draft:outline-20260920", status: approved}
  - {text: "成員權限範圍怎麼分", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/UserController.php, code:resources/views/layouts/lightbox/character-capability-edit.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
每位成員會被指派一個「角色」，角色的權限設定決定這位成員能不能查看、新增、編輯、刪除物件、合約、帳務、修繕等資料，以及看的是自己名下的還是整個團隊的。
除了物件、合約、帳務、修繕之外，角色權限也能授予查看團隊權限、查看或編輯團隊資訊、查看成員列表、查看大房東列表、查看租客列表等團隊管理相關功能。
團隊擁有者是創建這個團隊的人，權限固定，不能被編輯或刪除。
### 怎麼管理團隊的角色範本？（可新增、編輯、刪除，也能套用 JGB 內建的快速設定範本） {#jgb/B/member-role-manage}
- phrasings:
  - {text: "角色管理在哪", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼新增角色", source: "draft:outline-20260920", status: approved}
  - {text: "角色範本有哪些", source: "draft:outline-20260920", status: approved}
  - {text: "刪除角色會怎樣", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/layouts/lightbox/character-capability-edit.blade.php, code:config/character.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點擊成員列表的「角色管理」，可以看到團隊內所有角色，點「編輯」可以調整角色名稱與權限細節。
新增角色時可以直接點「快速設定」套用 JGB 提供的權限參考範本，例如店長、會計等內建範本，再自行微調。
角色刪除後無法恢復。
### 怎麼移除成員？（列表右側的紅色 × 圖示開啟確認視窗，按「移除」才會真的刪除；名下還有物件或合約會被擋下） {#jgb/B/member-remove}
- phrasings:
  - {text: "怎麼移除成員", source: "draft:outline-20260920", status: approved}
  - {text: "成員名下有物件不能刪怎麼辦", source: "draft:outline-20260920", status: approved}
  - {text: "移除成員後果", source: "draft:outline-20260920", status: approved}
  - {text: "成員擁有的物件怎麼轉移給別人", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/team/index.blade.php, code:src/pages/users/team/memberOwned/Index.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點成員列表這一列右側的紅色 × 圖示，會跳出「移除成員」確認視窗，按「移除」才會真的刪除這位成員。
如果這位成員名下還有綁定中的物件或合約，系統會先擋下移除，改跳出提示，要先指派其他經理人後才能進行移除動作。
這時候可以點進「〔成員姓名〕擁有的物件」或「擁有的合約」頁面，把每一筆物件或合約的授權移除，再回來移除這位成員。
成員移除後，對方將無法再存取這個團隊內的任何資訊。
### 邀請成員有名額上限嗎？（依訂閱方案而定；已訂閱達上限要升級方案，未訂閱要先訂閱） {#jgb/B/member-seat-limit}
- phrasings:
  - {text: "成員邀請有上限嗎", source: "draft:outline-20260920", status: approved}
  - {text: "團隊成員人數上限", source: "draft:outline-20260920", status: approved}
  - {text: "邀請額滿怎麼辦", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/layouts/lightbox/general.blade.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
團隊可以邀請的成員人數上限，是由目前的訂閱方案決定的。
達到上限後，點「邀請」不會開啟邀請視窗，而是提示已達到數量上限：已訂閱的團隊會導引前往升級方案；還沒訂閱服務的團隊則會提示請先前往訂閱服務，按鈕是「我要訂閱」。
### 怎麼指派物件或合約給成員？（點成員旁的鉛筆圖示選「編輯綁定物件」或「編輯綁定合約」） {#jgb/B/member-assign-owned}
- phrasings:
  - {text: "怎麼指派物件給成員", source: "draft:outline-20260920", status: approved}
  - {text: "編輯綁定合約在哪", source: "draft:outline-20260920", status: approved}
  - {text: "成員名下物件怎麼調整", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/team/index.blade.php, code:src/pages/users/team/memberOwned/Index.jsx]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
有編輯權限時，成員列表中一般成員那幾列右側有鉛筆圖示，點開可以選「編輯綁定物件」或「編輯綁定合約」，會跳到這位成員擁有的物件／合約頁面；團隊擁有者那一列和自己那一列沒有鉛筆圖示。
在「〔成員姓名〕擁有的物件」或「擁有的合約」頁面，可以點「授權更多物件／合約」加入新的授權，或點「移除所有授權」一次撤銷這位成員的所有物件／合約授權。
### 怎麼查看每個角色能做什麼？（點「角色權限說明」的「這裡」開啟角色權限列表，每一列是一項權限、每一欄是一個角色，用勾號／叉號表示有沒有這項權限） {#jgb/B/member-role-permission-list}
- phrasings:
  - {text: "角色權限列表在哪看", source: "draft:outline-20260920", status: approved}
  - {text: "角色權限說明在哪", source: "draft:outline-20260920", status: approved}
  - {text: "目前團隊還沒有角色怎麼辦", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/team/index.blade.php, code:resources/views/layouts/lightbox/character-capability-edit.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
成員列表頁面點「角色權限說明請點擊這裡」，會開啟「角色權限列表」視窗，用表格列出團隊內每個角色目前擁有的權限：每一列是一項權限（部分權限旁邊有說明文字），每一欄對應一個角色，用綠色勾號或灰色叉號表示這個角色有沒有這項權限。
如果團隊目前還沒有建立任何角色，角色權限列表會顯示「目前團隊還沒有任何角色，您可以選擇：」，並提供「新增角色」的按鈕。
### 成員列表可以直接改成員的角色嗎？（一般成員那一列可以用角色下拉選單直接切換；擁有者與自己那一列、或沒有編輯權限時選單會鎖住） {#jgb/B/member-list-role-inline-change}
- phrasings:
  - {text: "列表上怎麼改成員角色", source: "draft:outline-20260920", status: approved}
  - {text: "角色下拉選單怎麼用", source: "draft:outline-20260920", status: approved}
  - {text: "新增角色的入口在哪裡", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/team/index.blade.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
成員列表中一般成員那一列有角色下拉選單，選擇要指派的角色後就會直接送出變更，不用另外打開編輯視窗；團隊擁有者那一列和自己那一列的選單是鎖住的，沒有編輯權限時整個選單也會鎖住。
可以切換的角色下拉選單最下面有一個「+ 新增角色」選項，點選後會直接開啟「新增角色」視窗，不用先離開成員列表。
### 編輯角色時的「開啟條件」是什麼？（要先勾選列出的其他權限，這個權限選項的勾選框才能點；沒先勾好之前，勾選框會維持鎖住） {#jgb/B/member-role-edit-open-condition}
- phrasings:
  - {text: "為什麼有些權限打不開", source: "draft:outline-20260920", status: approved}
  - {text: "開啟條件是什麼意思", source: "draft:outline-20260920", status: approved}
  - {text: "角色編輯畫面權限勾不起來", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/layouts/lightbox/character-capability-edit.blade.php, code:src/store/modules/team/capabilityEdit.js]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「編輯角色」視窗裡，部分權限選項旁邊會顯示「開啟條件」文字，列出必須先勾選的其他權限。
在還沒勾選完開啟條件列出的權限之前，這個選項的勾選框會維持鎖住、無法點選；全部勾好開啟條件之後，這個選項才能勾選。
### 編輯角色時的「重設條件」按鈕是做什麼的？（把所有權限勾選全部清空） {#jgb/B/member-role-edit-reset}
- phrasings:
  - {text: "重設條件按鈕做什麼", source: "draft:outline-20260920", status: approved}
  - {text: "角色編輯畫面的重設是什麼意思", source: "draft:outline-20260920", status: approved}
  - {text: "重設條件會清掉哪些勾選", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/layouts/lightbox/character-capability-edit.blade.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
編輯角色或新增角色的視窗下方有「重設條件」按鈕，點下去會把所有權限勾選全部清空，包含編輯既有角色時原本已載入的勾選。
### 成員列表可以怎麼排序？（姓名、加入時間、手機號碼、Email、角色名稱各有正反兩種排序） {#jgb/B/member-list-sort}
- phrasings:
  - {text: "成員列表怎麼排序", source: "draft:outline-20260920", status: approved}
  - {text: "可以依加入時間排序嗎", source: "draft:outline-20260920", status: approved}
  - {text: "成員排序有哪些選項", source: "draft:outline-20260920", status: approved}
- sources: [code:src/entry/team.js]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
成員列表可以依姓名（A-Z／Z-A）、加入時間（早／晚）、手機號碼（小／大）、Email（A-Z／Z-A）、角色名稱（A-Z／Z-A）排序，一共 10 種排序方式可以選。
### 為什麼「團隊擁有者」和自己那一列的角色下拉不能改？（這兩列是固定顯示在列表最上面、角色下拉是鎖住的，跟其他成員分開處理） {#jgb/B/member-list-role-select-disabled}
- phrasings:
  - {text: "團隊擁有者角色不能改嗎", source: "draft:outline-20260920", status: approved}
  - {text: "自己的角色下拉是灰的", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼有一列選不了角色", source: "draft:outline-20260920", status: approved}
- sources: [code:resources/views/users/team/index.blade.php, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
成員列表最上面會固定顯示「團隊擁有者」與「自己（登入帳號本人）」各一列，如果登入帳號本人就是團隊擁有者則只顯示一列；這兩列各自的角色下拉選單是鎖住的、不能點選變更。
「團隊擁有者」是系統內建的固定角色，不會出現在成員的角色下拉選單裡。
## 大房東列表與授權物件 {#B-biglandlord-list}
### 大房東列表有哪些欄位？（ID、姓名、會員註冊、Email、手機號碼、身分證字號、地址、帳戶名稱、帳戶資訊、合作方式、合作起迄、所屬物件、生日、主要聯絡方式，其中生日與主要聯絡方式目前每筆都顯示「-」） {#jgb/B/biglandlord-list-overview}
- phrasings:
  - {text: "大房東列表有哪些欄位", source: "draft:outline-20260920", status: approved}
  - {text: "大房東資料看得到什麼", source: "draft:outline-20260920", status: approved}
  - {text: "大房東的合作起迄怎麼看", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/list/_parts/ListTable.vue, code:app/Services/BigLandlordService.php, code:src/utils/surelyVue/bigLandlord.ts, code:src/components/SurelyVue/BigLandlord/IsRegisteredCell.vue, code:src/components/SurelyVue/BigLandlord/RelatedEstateCell.vue, code:src/components/SurelyVue/BigLandlord/NameCell.vue, code:src/components/SurelyVue/Common/TextBlockCell.vue, code:src/routes/bigLandlords.js, code:src/pages/bigLandlords/list/_parts/owned.jsx]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大房東列表由左至右的欄位是：ID、姓名、會員註冊、Email、手機號碼、身分證字號、地址、帳戶名稱、帳戶資訊、合作方式、合作起迄、所屬物件、生日、主要聯絡方式，最右邊另有每一列的操作欄。
「會員註冊」欄是一個圓點：綠色代表這位大房東已完成註冊或驗證，灰色代表還沒有。
「所屬物件」欄顯示授權給這位大房東的物件數量（括號裡的數字），點下去會進到這位大房東的授權物件頁。
點擊「姓名」欄的名字會開啟這位大房東的聯絡資訊卡。
「生日」「主要聯絡方式」兩欄目前每一筆都只顯示「-」，不會顯示內容。
### 怎麼新增大房東？（已註冊會員填 Email 即可，未註冊只要填姓氏與名稱，Email 選填） {#jgb/B/biglandlord-add}
- phrasings:
  - {text: "怎麼新增大房東", source: "draft:outline-20260920", status: approved}
  - {text: "大房東還沒註冊怎麼辦", source: "draft:outline-20260920", status: approved}
  - {text: "新增大房東要填什麼", source: "draft:outline-20260920", status: approved}
- sources: [code:src/components/Lightbox/MemberInvite.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點擊大房東列表的「新增大房東」，系統會先問這位大房東是否已經註冊 JGB 帳號。
如果已經註冊，只要輸入對方的 Email 按「新增」就可以加入。
如果還沒註冊，姓氏與名稱是必填，Email 則是選填。
### 大房東的「授權物件」怎麼設定？（逐筆物件勾選瀏覽廣告／合約／帳務／修繕；合約要先勾廣告，帳務要先勾廣告＋合約，修繕沒有前提） {#jgb/B/biglandlord-authorize-estates}
- phrasings:
  - {text: "大房東能看到哪些資料", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼授權物件給大房東", source: "draft:outline-20260920", status: approved}
  - {text: "大房東權限怎麼設定", source: "draft:outline-20260920", status: approved}
  - {text: "移除大房東的物件授權", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/list/_parts/owned.jsx, code:app/Http/Controllers/UserController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點進「〔大房東姓名〕擁有的物件」頁面，可以看到目前授權給這位大房東的物件清單，並針對每一筆物件個別勾選「瀏覽物件廣告」「瀏覽物件所屬合約」「瀏覽物件所屬帳務」「瀏覽物件所屬修繕」這幾項權限。
「瀏覽物件所屬合約」要先勾選「瀏覽物件廣告」才能勾；「瀏覽物件所屬帳務」要先勾選「瀏覽物件廣告」與「瀏覽物件所屬合約」才能勾；「瀏覽物件所屬修繕」則沒有前提，可以直接勾選。
這個頁面也可以填寫這筆物件的「合作方式」與「合作起迄」日期備註。
點「授權更多物件」可以挑選其他物件加入授權；點「移除所有授權」會一次撤銷這位大房東的所有物件授權。
### 大房東名單可以批次匯入或匯出嗎？（可以，Excel 匯入新增、Excel 匯出下載） {#jgb/B/biglandlord-import-export}
- phrasings:
  - {text: "大房東可以批次匯入嗎", source: "draft:outline-20260920", status: approved}
  - {text: "大房東資料怎麼匯出", source: "draft:outline-20260920", status: approved}
  - {text: "大房東 excel 匯入匯出在哪", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/list/_parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
大房東列表的「新增大房東」按鈕旁有下拉選單，可以選擇「匯入大房東」開啟批次匯入視窗。
清單有資料時，同一個下拉選單也可以選「匯出大房東」，下載 Excel 格式的大房東資料。
### 大房東列表每一列的操作選單有哪些功能？（編輯所屬物件、編輯大房東、刪除大房東） {#jgb/B/biglandlord-actions-menu}
- phrasings:
  - {text: "怎麼刪除大房東", source: "draft:outline-20260920", status: approved}
  - {text: "移除大房東流程", source: "draft:outline-20260920", status: approved}
  - {text: "大房東資料怎麼編輯", source: "draft:outline-20260920", status: approved}
- sources: [code:src/use/config/useBigLandlordsTypes.ts]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
每一筆大房東資料旁的操作選單，可以選「編輯所屬物件」跳到授權物件頁面、「編輯大房東」修改資料，或「刪除大房東」移除這位大房東。
### 授權物件頁移除物件後，為什麼要按「套用」才會生效？（按紅色 X 移除只是待處理狀態，按套用才真的移除，按恢復可以取消這次變更） {#jgb/B/biglandlord-authorize-apply-step}
- phrasings:
  - {text: "授權物件移除後沒反應", source: "draft:outline-20260920", status: approved}
  - {text: "套用按鈕是做什麼的", source: "draft:outline-20260920", status: approved}
  - {text: "移除物件可以復原嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/list/_parts/owned.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在授權物件頁按某筆物件的紅色 X 移除後，畫面只會先在這筆物件上標示「「套用」後將移除此物件」，並不會立刻生效。
要按下頁面下方的「套用」按鈕，這次的變更才會真正送出；在按下套用之前，也可以點「恢復」把這次的移除還原。
### 刪除大房東會發生什麼？（先跳出確認視窗，確認後這位大房東就無法再存取這個團隊的任何資訊） {#jgb/B/biglandlord-delete-confirm}
- phrasings:
  - {text: "刪除大房東會怎樣", source: "draft:outline-20260920", status: approved}
  - {text: "大房東刪除確認視窗", source: "draft:outline-20260920", status: approved}
  - {text: "刪除大房東後對方還能登入嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/components/Lightbox/MemberDelete.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點操作選單的「刪除大房東」會先跳出「移除大房東」確認視窗，詢問是否確定要刪除。
確認刪除後，這位大房東就無法再存取這個團隊內的任何資訊。
### 大房東名額有上限嗎？（目前大房東列表頁的「新增大房東」沒有名額檢查） {#jgb/B/biglandlord-seat-limit}
- phrasings:
  - {text: "大房東可以新增幾位", source: "draft:outline-20260920", status: approved}
  - {text: "大房東名額上限", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Services/BigLandlordService.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
大房東列表頁上「新增大房東」按鈕背後的新增流程，沒有名額上限的檢查邏輯，目前可以持續新增。
### 大房東列表沒有資料時會顯示什麼？（一開始沒有任何大房東顯示「尚無大房東」；用關鍵字搜尋卻沒有符合結果則顯示「沒有符合的結果😢」） {#jgb/B/biglandlord-list-empty}
- phrasings:
  - {text: "大房東列表是空的", source: "draft:outline-20260920", status: approved}
  - {text: "還沒有大房東畫面長怎樣", source: "draft:outline-20260920", status: approved}
  - {text: "搜尋不到大房東會顯示什麼", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/list/_parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大房東列表目前一筆資料都沒有、而且沒有輸入搜尋關鍵字時，表格會顯示「尚無大房東」。
如果是用關鍵字搜尋、但搜尋不到符合的大房東，表格則會顯示「沒有符合的結果😢」。
### 批次匯入大房東的 Excel 範本要填哪些欄位？（姓氏、名稱必填，其餘含 Email、手機、身分證字號、地址、帳戶資訊、合作方式與合作起迄都是選填） {#jgb/B/biglandlord-batch-template-fields}
- phrasings:
  - {text: "大房東匯入範本欄位", source: "draft:outline-20260920", status: approved}
  - {text: "批次新增大房東要填什麼", source: "draft:outline-20260920", status: approved}
  - {text: "大房東匯入哪些欄位必填", source: "draft:outline-20260920", status: approved}
- sources: [code:src/components/ImportPreview/configs/bigLandlord.ts]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「匯入大房東」的批次匯入範本裡，只有姓氏與名稱是必填欄位。
其餘 Email、手機號碼、身分證字號、國家／縣市／區域／地址、帳戶名稱、帳戶資訊、合作方式、合作起始與終止時間都是選填欄位。
### 大房東列表可以用什麼排序？（姓名、手機號碼、Email、身分證字號，各有正序與反序共 8 種排序方式） {#jgb/B/biglandlord-list-sort}
- phrasings:
  - {text: "大房東列表怎麼排序", source: "draft:outline-20260920", status: approved}
  - {text: "可以用身分證字號排序嗎", source: "draft:outline-20260920", status: approved}
  - {text: "大房東列表排序選項有哪些", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/BiglandlordController.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大房東列表可以依姓名、手機號碼、Email、身分證字號這四個欄位排序，每個欄位都有正序（A-Z／小到大）與反序（Z-A／大到小）兩種方向，總共 8 種排序方式。
## 大房東報表 {#B-biglandlord-report}
### 大房東報表可以看到什麼？（依大房東列出所屬物件、出租中物件與執行中合約租金總額） {#jgb/B/biglandlord-report-overview}
- phrasings:
  - {text: "大房東報表看得到什麼", source: "draft:outline-20260920", status: approved}
  - {text: "大房東報表怎麼看", source: "draft:outline-20260920", status: approved}
  - {text: "大房東的物件租金總額在哪查", source: "draft:outline-20260920", status: approved}
  - {text: "大房東報表可以下載嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/report/_parts/ListTable.vue, code:src/pages/bigLandlords/report/_parts/BigLandlordItemDetail.jsx, code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大房東報表清單會依大房東列出姓名、所屬物件數、出租中物件數，以及目前執行中合約的租金總額。
點開單一大房東的細節，可以進一步看到底下每個社區、每筆物件的租客、租期與租金明細，並能個別下載報表。
報表會用團隊在「進階設定」設定的結算幣別，把不同幣別的合約金額換算成同一種幣別做加總。
### 誰看得到大房東報表？（法人房東與社宅團隊身分，且角色要有「查看大房東報表」權限） {#jgb/B/biglandlord-report-permission}
- phrasings:
  - {text: "大房東報表誰能看", source: "draft:outline-20260920", status: approved}
  - {text: "查看大房東報表權限", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼看不到大房東報表", source: "draft:outline-20260920", status: approved}
- sources: [code:app/Http/Controllers/UserController.php, code:app/Role.php, code:resources/views/layouts/lightbox/character-capability-edit.blade.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
側邊選單「大房東管理」底下的「大房東報表」項目，只有法人房東與社宅團隊身分才會出現。
團隊成員所屬的角色要有「查看大房東報表」的權限，這個選單項目才會出現。
角色權限設定裡，「查看大房東報表」的開啟條件是先有「查看大房東列表」。
### 大房東報表可以依社區細看嗎？（報表清單有「社區」欄） {#jgb/B/biglandlord-report-community-rate}
- phrasings:
  - {text: "大房東報表有社區欄嗎", source: "draft:outline-20260920", status: approved}
  - {text: "大房東報表匯率在哪看", source: "draft:outline-20260920", status: approved}
  - {text: "報表可以下載社區層級嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/report/_parts/ListTable.vue, code:src/pages/bigLandlords/report/_parts/BigLandlordItemDetail.jsx]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大房東報表清單有一欄「社區」，顯示這位大房東名下的社區數量，點擊數字會開啟社區清單。
## 大房東對帳表 {#B-biglandlord-sheet}
### 大房東對帳表在算什麼？（依年度列出屋主的收入與支出，年度表每月一欄；一般團隊是屋主租金收入與支出，特定合作團隊的資金版報表另有押金、屋主提領、屋主直收等區塊） {#jgb/B/biglandlord-sheet-overview}
- phrasings:
  - {text: "大房東對帳表看什麼", source: "draft:outline-20260920", status: approved}
  - {text: "對帳表怎麼看押金收支", source: "draft:outline-20260920", status: approved}
  - {text: "對帳表在算什麼", source: "draft:outline-20260920", status: approved}
  - {text: "對帳表的總結餘怎麼算", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/sheet/_parts/Sheet.vue, code:src/pages/bigLandlords/sheet/index.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/Index.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/TableInfo.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/EstateList.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/ReconciliationTerm.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/DepositList.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/EZoneCashflow.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/PropertyManagingReconciliation.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/OwnerWithdrawalCashflow.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/OwnerDirectReceiveCashflow.vue, code:src/pages/bigLandlords/sheet/_parts/monthlyReport/RemarkOfOwner.vue]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
大房東對帳表是針對一位大房東、依年度整理的屋主收支報表：年度表每個月一欄（1月到12月），各區塊列出每個月的金額；單月對帳單則列出該月的明細，抬頭是「屋主租金對帳單」（採資金版報表的特定合作團隊是「屋主資金對帳單」）。
年度表的區塊依團隊類型而不同：一般團隊是「屋主租金收入」「屋主租金支出」兩個區塊；採資金版報表的特定合作團隊是「押金收入」「押金支出」「屋主資金收入」「屋主資金支出」「屋主提領」「屋主直收收入」「屋主直收支出」七個區塊；部分團隊的用語會改顯示為「租金收入」「本期支出」。
單月對帳單最上方有屋主名稱與製表人，往下所有團隊都有「物件清單」「記帳期間」「押金」三個區塊；一般團隊接著是「屋主租金」區塊，採資金版報表的特定合作團隊則接著是「屋主資金」「屋主提領」「屋主直收」三個區塊與備註。
「記帳期間」區塊列出該月的記帳起訖日，以及本期屋主租金收入、本期屋主租金支出、本期屋主租金總結餘、上期屋主租金結餘、流水帳結餘與可調動租金（採資金版報表的特定合作團隊，用語是「屋主資金」「可調動資金」）；部分團隊的用語會改成「租金收入」「本期支出」，並隱藏上期結餘、總結餘與可調動租金。
有顯示總結餘的一般團隊，總結餘的算法是上期結餘加屋主租金收入、減屋主租金支出（報表上寫成「總結餘（上期結餘 + 屋主租金收入 - 屋主租金支出）」）。
### 對帳表顯示「尚未被指派物件」是什麼意思？（這位大房東還沒被授權任何物件） {#jgb/B/biglandlord-sheet-empty}
- phrasings:
  - {text: "對帳表沒資料怎麼辦", source: "draft:outline-20260920", status: approved}
  - {text: "大房東報表空白原因", source: "draft:outline-20260920", status: approved}
  - {text: "大房東還沒授權物件會怎樣", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/sheet/index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果這位大房東目前還沒有被授權任何物件，對帳表會提示這位大房東尚未被指派物件，需要先到「大房東管理」指派物件，才會有資料。
### 對帳表出現「本月含多幣別帳單」提示是什麼意思？（該月的帳單有不同幣別，已用結算幣別加總） {#jgb/B/biglandlord-sheet-multi-currency}
- phrasings:
  - {text: "對帳表多幣別提示是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼金額有換算過的字樣", source: "draft:outline-20260920", status: approved}
  - {text: "多幣別合計怎麼算", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/sheet/_parts/SheetTemplate.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果某個月份的帳單含有不同幣別，對帳表會在該區塊顯示「本月含多幣別帳單（〔幣別列表〕），以〔結算幣別〕結算合計」的提示，代表這個小計已經把不同幣別換算成同一種幣別加總。
### 對帳表可以隱藏沒有金額的項目嗎？（可以開關「隱藏空值項目」） {#jgb/B/biglandlord-sheet-hide-empty-rows}
- phrasings:
  - {text: "對帳表可以只看有金額的項目嗎", source: "draft:outline-20260920", status: approved}
  - {text: "隱藏空值項目是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "對帳表列太多怎麼精簡", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/sheet/_parts/SelectBar.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
對帳表上方可以開關「隱藏空值項目」，開啟後金額為零的類別列不會顯示在表格上。
### 對帳表怎麼從年表切到單一月份的月報？（點表頭的月份會進入該月月報，點「取消」回到年表） {#jgb/B/biglandlord-sheet-month-drilldown}
- phrasings:
  - {text: "對帳表年表怎麼看單月明細", source: "draft:outline-20260920", status: approved}
  - {text: "月報怎麼回到年表", source: "draft:outline-20260920", status: approved}
  - {text: "點月份沒反應", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/sheet/_parts/Sheet.vue, code:src/pages/bigLandlords/sheet/index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
年度對帳表的表頭可以點某個月份，進入這個月的月報明細畫面。
在月報畫面下方點「取消」，會離開這個月份的明細，回到原本的年度對帳表。
### 對帳表載入或下載失敗會怎樣？（載入失敗會顯示錯誤並提供「重試」，下載失敗只顯示錯誤訊息） {#jgb/B/biglandlord-sheet-load-download-fail}
- phrasings:
  - {text: "對帳表載入失敗怎麼辦", source: "draft:outline-20260920", status: approved}
  - {text: "報表下載失敗怎麼辦", source: "draft:outline-20260920", status: approved}
  - {text: "對帳表重試按鈕在哪", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/sheet/index.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
對帳表載入失敗時，畫面會顯示「報表載入失敗，請稍後再試」（或畫面顯示的錯誤訊息），並提供「重試」按鈕重新載入。
下載月報失敗時，畫面會顯示「報表下載失敗，請稍後再試」，但這個提示不提供重試按鈕，需要再次點擊「下載」。
### 大房東對帳表頁面的側邊選單和載入畫面長怎樣？（左側有社區／物件選單，看單一物件報表時會顯示上次匯入時間，報表產生中會顯示載入百分比進度條） {#jgb/B/biglandlord-sheet-aside-and-loading}
- phrasings:
  - {text: "對帳表左邊選單是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "上次匯入時間在哪看", source: "draft:outline-20260920", status: approved}
  - {text: "對帳表載入畫面在跑什麼", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/bigLandlords/sheet/index.vue, code:src/pages/bigLandlords/sheet/_parts/SelectBar.jsx]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
對帳表頁面左側有一個側邊選單，可以選擇要看整個社區還是特定物件的對帳資料。
切換到看單一物件的報表時，畫面上會顯示這個物件資料「最後導入時間」；看社區整體報表時不會顯示這個時間。
報表資料在產生中的時候，畫面中間會顯示一個百分比進度條，數字會隨著報表產生進度往上跳動。
## 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」） {#B-advanced-settings}
### 「帳單自訂費用項目」怎麼設定？（分收入類／支出類，必填性質與自定義名稱，會科品項代號選填） {#jgb/B/advance-fee-items}
- phrasings:
  - {text: "費用項目怎麼設定", source: "draft:outline-20260920", status: approved}
  - {text: "自訂費用分收入支出類嗎", source: "draft:outline-20260920", status: approved}
  - {text: "帳單費用項目性質怎麼選", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/_part/FeesItemManagement.vue, code:src/pages/users/advance/_part/FeePanel.vue, code:src/pages/users/advance/_part/BillsManagement.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階設定的「帳務管理」區塊可以設定帳單「自訂費用」的收付項目，分成「收入類」與「支出類」。
新增每個項目時要選擇「性質」（例如租金、押金、水費、電費、管理費、清潔費、網路費、滯納金、違約金、賠償金、押金設算息、其他），並填寫「自定義名稱」，這兩項畫面上都標示為必填。
「會科品項代號」是選填欄位，用來提供給 ERP／會計系統拋轉使用。
自訂項目可以拖曳調整順序，點旁邊的編輯圖示可以修改，編輯時也可以刪除；預設項目只顯示，不能編輯。
### 進階設定的「優惠項目」是給誰用的？（只有部分特定合作團隊才看得到，可設定折扣套用在租金費用上） {#jgb/B/advance-discount-items}
- phrasings:
  - {text: "進階設定有租金折扣嗎", source: "draft:outline-20260920", status: approved}
  - {text: "優惠項目怎麼設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定「合約管理」區塊的「優惠項目」只會顯示給部分特定合作團隊，一般團隊的進階設定沒有這個設定。
有這個設定的團隊最多可以建立 10 組優惠項目（其中一個特定合作團隊的上限是 30 組），在計算租金費用時套用折扣。
### 進階設定的「延遲金設置」是什麼、延遲金怎麼算？（只有特定合作團隊看得到；合約建立時帶入團隊設定，租金帳單逾期付款後才產生延遲金帳單，金額＝租金 ×（逾期天數 − 緩衝天數）× 延遲金百分比） {#jgb/B/advance-late-fee}
- phrasings:
  - {text: "進階設定有滯納金設定嗎", source: "draft:outline-20260920", status: approved}
  - {text: "延遲金怎麼算", source: "draft:outline-20260920", status: approved}
  - {text: "逾期繳費會產生什麼費用", source: "draft:outline-20260920", status: approved}
  - {text: "延遲金設置在哪", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx, code:app/Bill.php, code:app/Http/Controllers/UserController.php, code:app/Contract.php]
- reviewed: {by: owner, at: 2026-10-05}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定裡的「延遲金設置」區塊只會出現在特定合作團隊，一般團隊沒有這個設定。
有這個區塊的團隊可以用「啟用」開關開啟或關閉延遲金，區塊裡會顯示「緩衝天數」與「延遲金」百分比，啟用後可按「編輯延遲金設置」修改；送出變更時，團隊若有設定簽核流程就送簽核，沒有則直接更新。
延遲金是在租金帳單逾期付款之後才產生：這張租金帳單所屬合約已啟用延遲金、帳單已到帳，而且付款日比繳費期限晚、超過緩衝天數時，系統會自動為同一位租客再產生一張延遲金帳單，並直接送到應到帳；這張延遲金帳單的繳費期限是產生當天。
只有型態是一般租金的帳單會觸發延遲金，點退帳單、手動新增的帳單、罰款帳單、儲值帳單與押金設算息帳單都不會。
延遲金金額的算法是：這張租金帳單的租金項目金額 ×（逾期天數 - 緩衝天數）× 延遲金百分比，逾期天數是付款日比繳費期限晚的天數。
是否產生延遲金、緩衝天數與延遲金百分比，看的是合約上的設定：合約建立時才從團隊目前的設定複製一份到合約，團隊之後再開啟或修改設定，已建立的合約不會跟著改變，所以團隊開啟延遲金之前就建立的合約不會產生延遲金帳單。
### 「預設補充條款」怎麼設定？（最多可以設 3 組，編輯合約時直接選用） {#jgb/B/advance-additional-terms}
- phrasings:
  - {text: "補充條款範本怎麼設定", source: "draft:outline-20260920", status: approved}
  - {text: "合約補充條款可以存幾組", source: "draft:outline-20260920", status: approved}
  - {text: "預設條款在哪編輯", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定的「合約管理」區塊可以設定至多三組常用的「預設補充條款」，編輯合約時可以直接選用，不用每次重新輸入。
每一組條款都可以新增、編輯、預覽（會轉成 PDF 預覽），也可以刪除。
### 「標籤設定」是做什麼用的？（幫物件加自訂標籤，單個標籤輸入框最多收 9 個字元） {#jgb/B/advance-custom-label}
- phrasings:
  - {text: "自訂標籤怎麼設定", source: "draft:outline-20260920", status: approved}
  - {text: "標籤字數上限是多少", source: "draft:outline-20260920", status: approved}
  - {text: "物件標籤在哪加", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx, code:src/components/LabelPanel.vue, code:src/pages/estates/list/_parts/ListTable.vue, code:src/pages/estates/list/Index.vue]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定的「物件管理」區塊有一個「標籤設定」，可以先在這裡建立自訂標籤。
設定好標籤後，可以到物件管理的物件總表，幫不同的物件加上這些自訂標籤。
單一個標籤最多只能輸入 9 個字元，中文或英文都一樣，超過的字會被截掉。
畫面上的說明文字寫的是「單個標籤上限為18字元(9個字)」，但實際輸入不分中英文都只收 9 個字元。
### 怎麼綁定智能裝置廠商？（輸入裝置廠商帳號密碼完成綁定，之後可在 JGB 平台管理裝置） {#jgb/B/advance-device-binding}
- phrasings:
  - {text: "智能裝置怎麼綁定", source: "draft:outline-20260920", status: approved}
  - {text: "裝置管理在哪設定", source: "draft:outline-20260920", status: approved}
  - {text: "裝置廠商綁定流程", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階設定的「裝置管理」區塊可以「綁定設備廠商」，綁定後就能在 JGB 平台內管理你的智能裝置。
點「開始綁定」後，要選擇裝置廠商並輸入該廠商的帳號密碼登入，才能完成綁定。
綁定完成的廠商會列在下方，每一筆都可以按「更新資料」重新取得裝置資料。
### 自訂費用項目可以合併嗎？（可以把多個品項併入其中一個既有品項，合併後無法回復） {#jgb/B/advance-fee-items-merge}
- phrasings:
  - {text: "怎麼合併費用項目", source: "draft:outline-20260920", status: approved}
  - {text: "合併品項後可以回復嗎", source: "draft:outline-20260920", status: approved}
  - {text: "自訂費用項目合併操作", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/_part/FeesItemManagement.vue, code:src/components/Lightbox/CustomFeeItemMerge.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在「帳單自訂費用項目」可以點「合併項目」，勾選要合併的收入類或支出類品項，再從「欲合併品項」選擇要併入的既有品項，勾選的品項就會併入這個品項；系統預設的品項不能勾選合併。
品項合併後無法回復，操作前系統會提醒要謹慎操作。
### 進階設定的「繳費週期優惠」是給誰用的？（只有特定合作團隊才看得到，選比月繳更長的繳費週期就有折扣） {#jgb/B/advance-payment-cycle-discount}
- phrasings:
  - {text: "選季繳有折扣嗎", source: "draft:outline-20260920", status: approved}
  - {text: "誰看得到繳費週期優惠設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定「合約管理」區塊的「繳費週期優惠」只會顯示給特定合作團隊，其他團隊的進階設定都沒有這個設定。
有這個設定的團隊，編輯合約時選擇比月繳更長的繳費週期，就能獲得租金折扣。
### 「Email 通知語系」在哪設定、誰看得到？（只有法人房東或社宅團隊看得到，決定代發通知信的預設語系） {#jgb/B/advance-notification-locale}
- phrasings:
  - {text: "Email 通知語系怎麼設定", source: "draft:outline-20260920", status: approved}
  - {text: "個人房東有語系設定嗎", source: "draft:outline-20260920", status: approved}
  - {text: "租客收到的通知信語言怎麼決定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定的「全域設定」區塊只會顯示給法人房東或社宅團隊的身分，個人房東的進階設定看不到這個區塊，也就沒有「Email 通知語系」可以設定。
「Email 通知語系」可以設定系統代發給租客的通知信預設語系。
### 「時區設定」會影響哪些通知？（只有法人房東或社宅團隊看得到，改變排程通知的發送時間） {#jgb/B/advance-timezone}
- phrasings:
  - {text: "個人房東有時區設定嗎", source: "draft:outline-20260920", status: approved}
  - {text: "改時區會影響什麼通知", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「時區設定」跟「Email 通知語系」一樣在「全域設定」區塊，只有法人房東或社宅團隊看得到。
選擇非台灣時區後，像每日過期帳單通知、合約 30 天內到期提醒通知這類排程通知的發送時間，會改用所選的時區計算。
### 「結算幣別」是做什麼用的？（只有法人房東或社宅團隊看得到，把大房東報表的多幣別合約統一結算成一種幣別） {#jgb/B/advance-settlement-currency}
- phrasings:
  - {text: "結算幣別是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "多幣別報表怎麼算", source: "draft:outline-20260920", status: approved}
  - {text: "結算幣別在哪設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「結算幣別」也在「全域設定」區塊，只有法人房東或社宅團隊看得到。
這個設定用來把大房東報表裡多種幣別的合約資訊，統一結算成一種幣別。
### 為什麼進階設定看不到「裝置管理」區塊？（訂閱方案要生效中，且不能是免費方案） {#jgb/B/advance-device-binding-visibility}
- phrasings:
  - {text: "裝置管理不見了", source: "draft:outline-20260920", status: approved}
  - {text: "免費方案可以綁裝置嗎", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼進階設定沒有裝置管理", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階設定的「裝置管理」區塊只有在訂閱方案生效中、且方案不是免費方案時才會顯示；訂閱未生效或使用免費方案的團隊看不到這個區塊。
### 「房東專屬帳號」是做什麼用的？（只有法人房東或社宅團隊看得到；顯示在團隊首頁，且第一次儲存後不能自行修改，要洽 JGB 客服） {#jgb/B/advance-dedicated-account}
- phrasings:
  - {text: "房東專屬帳號是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "房東專屬帳號可以改嗎", source: "draft:outline-20260920", status: approved}
  - {text: "房東專屬帳號在哪設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「房東專屬帳號」欄位在「全域設定」區塊裡，這個區塊只有法人房東或社宅團隊的進階設定看得到，個人房東團隊沒有這個區塊。
進階設定「全域設定」區塊的「房東專屬帳號」會應用在這個團隊的「團隊首頁」上。
「房東專屬帳號」第一次儲存後就不能自行修改，要修改需要洽 JGB 客服人員處理。
### 招租廣告可以自動刊登或自動下架嗎？（部分特定合作團隊可以：合約到期日前 N 天自動刊登，簽約後自動下架） {#jgb/B/advance-auto-publish-unpublish}
- phrasings:
  - {text: "招租廣告會自動上架嗎", source: "draft:outline-20260920", status: approved}
  - {text: "簽約後廣告會自動下架嗎", source: "draft:outline-20260920", status: approved}
  - {text: "自動刊登天數怎麼設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定「物件管理」區塊的「招租廣告自動刊登」與「招租廣告自動下架」只有部分特定合作團隊看得到，其他團隊沒有這兩個設定；「招租廣告自動刊登」啟用後，可以設定天數，物件的合約到期日在這個天數內時，系統會自動將這個物件的招租廣告刊登出去。
「招租廣告自動下架」啟用後，物件簽訂合約、進入執行中合約狀態時，系統會自動把這個物件的招租廣告下架。
### 「合約管理」的標籤設定跟物件的標籤設定是同一個嗎？（不是，這是合約專用的另一組標籤） {#jgb/B/advance-contract-label}
- phrasings:
  - {text: "合約可以加標籤嗎", source: "draft:outline-20260920", status: approved}
  - {text: "合約標籤在哪設定", source: "draft:outline-20260920", status: approved}
  - {text: "合約標籤跟物件標籤一樣嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階設定「合約管理」區塊也有自己的「標籤設定」，用來建立合約專用的標籤，跟「物件管理」區塊那組給物件用的標籤設定是分開管理的兩組標籤。
### 「銷貨單品項代號對應」是做什麼用的？（只有特定團隊才有，設定匯出「M 化銷貨單」時每個品項要帶的產品代號） {#jgb/B/advance-sales-item-code}
- phrasings:
  - {text: "銷貨單品項代號對應是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "匯出銷貨單產品代號空白", source: "draft:outline-20260920", status: approved}
  - {text: "哪些團隊有銷貨單品項代號設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/_part/BillsManagement.vue, code:src/pages/users/advance/_part/WenzhongItemCodeManagement.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階設定「帳務管理」區塊的「銷貨單品項代號對應」只有特定團隊的進階設定才會出現，是一項團隊層級的設定，不是每個團隊都有。
這個設定用來指定匯出「M 化銷貨單」時，每個費用品項要帶入的產品代號；留空的品項會沿用系統預設代號，只有系統預設也沒有代號的品項，匯出檔案裡的產品代號才會是空白，也可以指定哪些品項不要匯入銷貨單。
### 「社區管理」的城市／區域／位置設定是做什麼？（只有特定合作團隊看得到，用來建立社區可選用的城市、區域、位置標籤） {#jgb/B/advance-community-labels}
- phrasings:
  - {text: "城市設定在哪", source: "draft:outline-20260920", status: approved}
  - {text: "區域設定是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "位置設定跟標籤設定差在哪", source: "draft:outline-20260920", status: approved}
  - {text: "誰看得到社區管理設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進階設定的「社區管理」區塊只會顯示給特定合作團隊，一般團隊看不到這個區塊。
這個區塊有「城市設定」「區域設定」「位置設定」三組獨立的自訂標籤，設定好之後，可以在社區編輯頁的基本資料為社區選用對應的城市、區域、位置標籤。
### 進階設定的「短租期核可流程」是做什麼的？（只有特定合作團隊看得到；租期少於設定天數時，合約要先簽核通過才會發出邀請給租客） {#jgb/B/advance-short-lease-approval}
- phrasings:
  - {text: "短租期核可流程是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "短租期簽核怎麼設定", source: "draft:outline-20260920", status: approved}
  - {text: "租期太短要簽核嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/advance/Index.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
進階設定「合約管理」區塊的「短租期核可流程」只會顯示給特定合作團隊，一般團隊的進階設定沒有這個設定。
啟用後，如果合約的租期少於設定的天數（短租期定義），這份合約在簽約前需要先進行簽核；簽核通過後，合約邀請才會發出給租客。
## 租客列表（當前租客／封存、準時繳租率、信用評價） {#B-tenant-list}
### 租客列表有哪兩個分頁？（當前租客／封存，封存代表這位租客已被移出列表且目前沒有進行中的合約） {#jgb/B/lessee-tabs}
- phrasings:
  - {text: "租客列表分幾種", source: "draft:outline-20260920", status: approved}
  - {text: "準時繳租率怎麼算", source: "draft:outline-20260920", status: approved}
  - {text: "封存的租客是什麼", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/ListTable.vue, code:src/pages/users/lesseeList/parts/PageTop.vue, code:app/Services/LesseeService.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客列表分成「當前租客」與「封存」兩個分頁，涵蓋簽約成功的租客，以及房東自行管理、還沒正式簽約的潛在租客。
把一位租客「封存」等於把他從當前租客列表移除；如果這位租客目前還有進行中的合約，系統會擋下這個動作、不能封存。
### 租客列表的「信用評價」欄位為什麼有些人看不到？（需要有查看租客信用評價的權限才會顯示這一欄） {#jgb/B/lessee-credit-rating-visibility}
- phrasings:
  - {text: "信用評價欄位不見了", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼看不到信用評價", source: "draft:outline-20260920", status: approved}
  - {text: "租客信用評價需要什麼權限", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客列表可以顯示「信用評價」欄位，但只有擁有「查看租客信用評價」權限的成員，畫面上才會出現這一欄；沒有這個權限的人，整欄完全不會出現，也不會佔用表格版面。
### 租客列表可以新增、匯入、匯出租客嗎？（個人房東與法人房東可以手動新增、Excel 匯入與匯出；社宅團隊只能匯出） {#jgb/B/lessee-crud}
- phrasings:
  - {text: "租客列表可以新增租客嗎", source: "draft:outline-20260920", status: approved}
  - {text: "租客資料怎麼匯入匯出", source: "draft:outline-20260920", status: approved}
  - {text: "已簽約的租客可以改名字嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
個人房東與法人房東的租客列表可以「新增租客」手動加入一筆租客資料，也可以用「匯入租客」批次匯入，或「匯出租客」下載成 Excel；社宅團隊的租客列表只有匯出功能，不能新增或匯入。
已經有合約的租客，沒辦法在這裡編輯姓名，也不能被刪除。
### 租客列表裡 Email／手機號碼顯示藍色、橘色、灰色代表什麼？（驗證狀態：已驗證／等待驗證／未驗證） {#jgb/B/lessee-notification-status-color}
- phrasings:
  - {text: "租客通知顏色代表什麼", source: "draft:outline-20260920", status: approved}
  - {text: "Email 顯示灰色是什麼意思", source: "draft:outline-20260920", status: approved}
  - {text: "手機號碼橘色代表什麼", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
藍色的 Email 或手機號碼代表這個聯絡方式已經被租客驗證過，可以接收合約與帳單通知；橘色代表正在等待租客驗證；灰色代表還沒驗證，沒驗證的 Email 或手機號碼收不到通知。
### 租客的 Email／手機驗證連結多久過期？（72 小時） {#jgb/B/lessee-verification-link-expiry}
- phrasings:
  - {text: "驗證連結多久過期", source: "draft:outline-20260920", status: approved}
  - {text: "驗證信有效期限", source: "draft:outline-20260920", status: approved}
  - {text: "簡訊驗證連結會過期嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
驗證通知寄出後，信件或簡訊裡連結的有效時間是 72 小時。
### 租客的通知開關關閉後會怎樣？（Email 與手機的開關分開，關掉哪一個就停哪一種通知） {#jgb/B/lessee-notification-toggle-effect}
- phrasings:
  - {text: "租客通知關閉會怎樣", source: "draft:outline-20260920", status: approved}
  - {text: "關掉通知還收得到帳單信嗎", source: "draft:outline-20260920", status: approved}
  - {text: "通知開關在哪裡設定", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/PageTop.vue, code:src/pages/users/lesseeList/parts/ContactInfoBlock.jsx]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客列表的 Email 與手機通知開關是分開的：關閉 Email 開關就不會再收到 Email 通知，關閉手機開關就不會再收到簡訊通知，另一種管道不受影響；已註冊的租客，開關無法在這裡操作。
### 租客的「準時繳租率」怎麼算？（已到帳未逾期帳單數 ÷ 全部應計入帳單數） {#jgb/B/lessee-on-time-pay-rate}
- phrasings:
  - {text: "準時繳租率公式", source: "draft:outline-20260920", status: approved}
  - {text: "繳租率是看哪些帳單", source: "draft:outline-20260920", status: approved}
  - {text: "準時繳租率算式", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客列表會顯示每位租客的「準時繳租率」，計算方式是：已到帳未逾期帳單數 ÷（應到帳逾期帳單數 ＋ 已到帳未逾期帳單數 ＋ 已到帳逾期帳單數）。
### 租客列表可以看到哪些欄位？（ID、姓名、會員註冊、Email - 通知、手機號碼 - 通知、註冊合約、免註冊合約、所屬修繕、準時繳租率、帳戶名稱、帳號資訊、操作） {#jgb/B/lessee-list-columns}
- phrasings:
  - {text: "租客列表有哪些欄位", source: "draft:outline-20260920", status: approved}
  - {text: "免註冊合約是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "所屬修繕欄位是什麼", source: "draft:outline-20260920", status: approved}
  - {text: "帳號資訊欄位是什麼", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客列表預設會顯示 ID、姓名、會員註冊、Email - 通知、手機號碼 - 通知、註冊合約、免註冊合約、所屬修繕、準時繳租率、帳戶名稱、帳號資訊、操作這些欄位。
「註冊合約」是這位租客名下、對方已註冊 JGB 帳號的合約數量；「免註冊合約」是不用租客先註冊帳號、建檔時就標記為免註冊的合約數量。
### 社宅團隊的租客列表欄位有什麼不一樣？（沒有「會員註冊」「免註冊合約」與操作選單，「註冊合約」欄改叫「所屬總合約」） {#jgb/B/lessee-list-columns-by-role}
- phrasings:
  - {text: "社宅租客列表欄位差在哪", source: "draft:outline-20260920", status: approved}
  - {text: "租客列表沒有操作欄", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/ListTable.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅團隊的租客列表看不到「會員註冊」「免註冊合約」兩欄與最右側的操作選單，「註冊合約」欄也會改叫「所屬總合約」。
### 租客的 Email 或手機還在等待驗證時，帳單會怎樣？（帳單會停留在草稿分頁，等驗證完成或連結過期才能發送，也可以手動移動） {#jgb/B/lessee-pending-verification-bill-draft}
- phrasings:
  - {text: "帳單卡在草稿分頁怎麼辦", source: "draft:outline-20260920", status: approved}
  - {text: "帳單一直沒發送原因", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
為避免租客無法收到帳單通知，若 Email 或手機號碼尚在等待租客驗證，管理者建立帳單時，系統會把帳單停留在草稿帳單分頁中，等租客完成驗證或驗證連結過期後，才能發送帳單。
管理者仍然可以手動把這張帳單從草稿移到應到帳或已到帳分頁。
### 租客列表勾選多筆租客後可以做什麼？（特定合作團隊可以批次發送通知，其他團隊沒有這個批次操作） {#jgb/B/lessee-bulk-notify}
- phrasings:
  - {text: "租客列表勾選後能做什麼", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼批次通知租客", source: "draft:outline-20260920", status: approved}
  - {text: "租客批次操作在哪", source: "draft:outline-20260920", status: approved}
- sources: [code:src/use/config/useLesseeTypes.ts, code:src/pages/users/lesseeList/parts/ListTable.vue, code:src/components/ListBulkAction.vue, code:src/components/Lightbox/EditUsersMessage.jsx]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有特定合作團隊的租客列表有勾選框；勾選一筆以上租客後，固定在列表上方的批次操作列會顯示已選數量，並提供「發送通知」。
其他團隊的租客列表沒有勾選框，也沒有批次操作。
按「發送通知」會開啟視窗，填寫「通知標題」與「通知內容」後按「發送」，這則通知會發給所有已勾選的租客，並在租客登入時顯示。
### 匯出租客的入口在哪？（一般房東用「新增租客」下拉選單裡的「匯出租客」；社宅團隊只有一顆「匯出」按鈕，沒有新增或匯入） {#jgb/B/lessee-export-entry-by-role}
- phrasings:
  - {text: "匯出租客在哪", source: "draft:outline-20260920", status: approved}
  - {text: "社宅團隊怎麼匯出租客", source: "draft:outline-20260920", status: approved}
  - {text: "為什麼看不到新增租客按鈕", source: "draft:outline-20260920", status: approved}
- sources: [code:src/pages/users/lesseeList/parts/PageTop.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般房東（含法人房東）在租客列表可以點「新增租客」按鈕旁的下拉選單，選「匯入租客」或「匯出租客」。
社宅團隊的租客列表沒有「新增租客」與「匯入租客」，只有一顆「匯出」按鈕，功能等同於一般房東的「匯出租客」。
### 租客列表可以怎麼搜尋篩選、每頁看幾筆？（可依姓名／Email／手機號碼／租客 ID 搜尋，用會員註冊與通知狀態篩選，每頁可選 30／60／90 筆） {#jgb/B/lessee-list-search-and-pagination}
- phrasings:
  - {text: "租客列表怎麼搜尋", source: "draft:outline-20260920", status: approved}
  - {text: "可以用租客 ID 搜尋嗎", source: "draft:outline-20260920", status: approved}
  - {text: "每頁可以看幾筆租客", source: "draft:outline-20260920", status: approved}
  - {text: "租客列表可以篩選通知狀態嗎", source: "draft:outline-20260920", status: approved}
- sources: [code:src/utils/constants/lessee.js, code:src/pages/users/lesseeList/parts/PageNav.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客列表的搜尋框可以選擇用姓名、Email、手機號碼、租客 ID 其中一種類型當關鍵字搜尋。
另外還可以用「會員註冊」（未註冊／已註冊）與「通知狀態」篩選租客；「通知狀態」的選項分成手機與 Email 兩組，各有「接受通知」「不接受通知」「驗證中」「未填寫聯繫方式」四種狀態，共八個選項。
列表下方可以選擇每頁顯示 30 項、60 項或 90 項。
### 租客列表每一列的操作選單有哪些功能？（建立電子合約、上傳紙本合約、編輯租客、封存租客；封存分頁裡則改成刪除租客） {#jgb/B/lessee-action-menu}
- phrasings:
  - {text: "租客列表操作選單在哪", source: "draft:outline-20260920", status: approved}
  - {text: "怎麼幫租客建立電子合約", source: "draft:outline-20260920", status: approved}
  - {text: "封存分頁的租客要怎麼刪除", source: "draft:outline-20260920", status: approved}
- sources: [code:src/components/SurelyVue/Lessee/ActionCell.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客列表每一列右側的操作選單裡，可以選「建立電子合約」「上傳紙本合約」「編輯租客」。
在「當前租客」分頁看到的操作選單最後一項是「封存租客」；切到「封存」分頁後，同一個位置的選項會改成「刪除租客」。
