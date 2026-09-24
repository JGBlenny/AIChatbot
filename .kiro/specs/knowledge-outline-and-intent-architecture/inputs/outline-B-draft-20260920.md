# B 架草稿（jgb2 master @ b2ee2ac382ce；粗目 7、細目 79、句 169）

讀法：每個粗目底下一條細目答一件事；句子後的〔〕是來源檔（程式或幫助中心頁）；「待查」是文件與程式衝突或程式裡查不到的，未選邊。

## 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊）⇄ 由 A 移入（12 條；頁：web:users.role）

### 團隊資訊頁面可以設定什麼？（公司 Logo、團隊名稱、團隊介紹）
- 講法：團隊資訊在哪裡設定／團隊名稱怎麼改／團隊介紹要寫什麼／團隊首頁的介紹文字在哪改／公司 Logo 怎麼上傳
- 給誰看：property_manager、prospect
- 團隊管理的「團隊資訊」頁面「基本資訊」區塊，可以上傳公司 Logo、設定團隊名稱，並撰寫團隊介紹。〔resources/views/users/role.blade.php〕
- 團隊介紹是要讓未來租客認識這個團隊的自我介紹文字，填寫後會顯示在團隊首頁上。〔resources/views/users/role.blade.php〕
- 沒有編輯團隊資訊權限的帳號，這個頁面的欄位只能檢視、不能修改。〔app/Http/Controllers/UserController.php〕

### 廣告頁聯絡資訊要填什麼？（Line ID、Facebook、WhatsApp 選填，公司電話與公司 Email 必填）
- 講法：廣告頁聯絡資訊要填什麼／公司電話一定要填嗎／WhatsApp 怎麼填／廣告聯絡方式在哪設定
- 給誰看：property_manager、prospect
- 團隊資訊頁的「廣告頁聯絡資訊」會呈現在物件廣告上，讓租客可以透過更多管道與房東聯繫，提升簽約成功率。〔resources/views/users/role.blade.php〕
- 這個區塊可以填寫 Line ID、Facebook 個人首頁連結；填寫 WhatsApp 時要包含國碼與電話號碼，國碼前面不需要打「+」。〔resources/views/users/role.blade.php〕
- 公司電話與公司 Email 是這個區塊裡的必填欄位。〔resources/views/users/role.blade.php〕

### 怎麼刪除團隊？（需先解除訂閱方案、輸入團隊名稱確認、刪除後資料無法恢復）
- 講法：怎麼刪除團隊／刪除團隊會怎樣／刪除團隊的條件／團隊解散流程
- 給誰看：property_manager
- 只有帳號本身擁有的團隊，團隊資訊頁才會顯示「刪除團隊」的入口。〔resources/views/users/role.blade.php〕
- 如果團隊目前的訂閱方案尚未結束，系統會先提示要到「團隊管理」的「訂閱方案」解除現有訂閱，才能繼續刪除。〔resources/views/users/role.blade.php〕
- 可以刪除時，畫面會列出這個團隊目前持有的物件數與合約數，並要求輸入團隊名稱才能按下刪除。〔resources/views/users/role.blade.php〕
- 刪除團隊會同時清除這個團隊底下所有的物件、合約與帳務等資料，且無法恢復。〔resources/views/users/role.blade.php〕

### 簽約資訊卡「個人資訊」區塊只有個人團隊看得到，要填什麼？（姓氏、名稱、身分證字號、Email、手機必填；戶籍地址／通訊地址／身分證正反面／其他附件選填或另有條件）
- 講法：簽約資訊個人欄位有哪些／身分證正反面要傳嗎／良民證要上傳嗎／戶籍地址跟通訊地址一樣可以嗎
- 給誰看：property_manager
- 簽約資訊卡的「個人資訊」區塊只有個人團隊看得到，法人團隊與社宅團隊不會顯示這個區塊；可以填寫這個團隊在刊登物件廣告與簽立合約時所需提供的個人資訊：姓氏、名稱、身分證字號、Email、手機號碼都是必填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 戶籍地址與通訊地址也要填寫，通訊地址可以點「同戶籍地址」直接帶入。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 身分證正反面照片是選填，另外還有一個「其他附件(選填)」區塊，可以選填上傳工作名片/學生證、良民證、小章這三項附件。〔src/pages/users/team/_parts/SignerDetails.vue〕

### 簽約資訊卡的「公司資訊」要填什麼？（公司登記名稱上限 20 字、公司統編皆為必填；公司負責人只有社宅團隊必填；社宅團隊還要填必填的社宅業者編號與公司登記證號，公司登記證日期與縣市則不分團隊都是選填）
- 講法：公司登記名稱字數上限／社宅業者編號在哪填／公司登記證號要填嗎／公司統編格式錯誤怎麼辦
- 給誰看：property_manager
- 簽約資訊卡的「公司資訊」要填公司登記名稱（最多 20 字）與公司統編，這兩項不分一般團隊或社宅團隊都是必填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「公司統編」欄位下方可以選擇統編類型是「公司統編(檢核)」還是「其他統編(不檢核)」，選「公司統編(檢核)」時會檢查統一編號格式，格式不對會顯示「公司統編格式錯誤」。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「公司負責人」只有社宅團隊是必填欄位，一般團隊則是選填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「社宅業者編號」只有社宅團隊看得到，且是必填欄位；一般團隊沒有這一欄。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「公司登記證號」對社宅團隊是必填，一般團隊則是選填；「公司登記證日期」「公司登記證縣市」不論一般團隊或社宅團隊都是選填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '276p' | grep -c isSocialHousingTeam", 'result': '1 — 「公司負責人」欄位的 isRequired 被 state.isSocialHousingTeam 包住，一般團隊不是必填', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '226,230p' | grep -c '公司登記名稱' => 1（正對照組：同檔案永遠必填的「公司登記名稱」欄位定義確實命中，證明 grep 找得到這個檔案裡的東西）"}`

### 簽約資訊卡的「經紀人資訊」要填什麼？（經紀人／經紀業名稱與證號，名稱上限 15 字；社宅團隊多了經紀人聯絡電話與 Email，且都是必填）
- 講法：經紀人名稱字數上限／經紀業名稱可以不填嗎／經紀人聯絡電話什麼時候要填
- 給誰看：property_manager
- 簽約資訊卡有獨立的「經紀人資訊」區塊，可以填經紀人與經紀業各自的名稱、證號。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「經紀人名稱」與「經紀業名稱」都有 15 字的上限，超過會顯示已達上限的錯誤提示；一般團隊的經紀人名稱、證號、經紀業名稱、證號全部都是選填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 社宅團隊的經紀人名稱、經紀人證號會變成必填，還會多出「經紀人聯絡電話」「經紀人 Email」這兩個欄位、同樣必填；一般團隊看不到這兩個聯絡電話與 Email 欄位。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '405p' | grep -c isSocialHousingTeam", 'result': '1 — 「經紀人聯絡電話」欄位的 isFieldVisible 被 state.isSocialHousingTeam 包住，一般團隊不會渲染這個欄位（「經紀人 Email」在同一寫法的另一個欄位定義裡也一樣）', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '228p' | grep -c '公司登記名稱' => 1（正對照組：同檔案永遠顯示的「公司登記名稱」欄位定義確實命中，證明 grep 找得到這個檔案裡的東西）"}`

### 簽約資訊卡的「租賃住宅管理人員資訊」要填什麼？（姓名與證號；社宅團隊多了聯絡電話欄位，且姓名／證號／電話都是必填；沒有 Email 欄位）
- 講法：租賃管理人員要填哪些資料／租賃管理人員聯絡電話要填嗎／租賃住宅管理人員證號在哪填
- 給誰看：property_manager
- 簽約資訊卡有獨立的「租賃住宅管理人員資訊」區塊，可以填租賃管理人員的名稱與證號，一般團隊這兩項都是選填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 社宅團隊的租賃管理人員名稱、證號都變成必填，還會多出「租賃管理人員聯絡電話」欄位、同樣必填；這個區塊沒有 Email 欄位。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | grep -cF "fieldTitleLabelKey: \'租賃管理人員 Email\',"', 'result': '0 — 整個 SignerDetails.vue 沒有租賃管理人員 Email 欄位的定義', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | grep -cF "fieldTitleLabelKey: \'經紀人 Email\'," => 1（正對照組：同檔案裡確實存在的「經紀人 Email」欄位定義確實命中，證明 grep 找得到這個檔案裡的東西）'}`

### 簽約資訊卡可以上傳哪幾種圖章？（法人或社宅團隊的簽約資訊卡才看得到「附件」與「電子簽約圖章」兩個區塊；「附件」有公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章五種，「電子簽約圖章」另外只有一個「圖章」欄位）
- 講法：圖章要上傳哪幾種／電子簽約圖章是什麼／公司大章小章差在哪
- 給誰看：property_manager
- 「附件」與「電子簽約圖章」這兩個區塊，只有簽約資訊卡屬於法人團隊或社宅團隊時才會出現；個人團隊的簽約資訊卡看不到這兩個區塊。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 簽約資訊卡的「附件」區塊可以分別上傳公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章共五種圖章。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「電子簽約圖章」是另一個獨立區塊，只有一個「圖章」上傳欄位，跟「附件」區塊的五種圖章是不同的檔案；圖章上傳並儲存後，可以開啟「預設使用圖章取代親手簽名」，簽約時就會直接套用這個圖章。〔src/pages/users/team/_parts/SignerDetails.vue〕

### 一個團隊可以管理多組公司資訊嗎？（可以在「團隊資訊管理」視窗新增與刪除，但清單第一筆不能刪除）
- 講法：可以設定多組公司資訊嗎／公司資訊怎麼新增／主要那組公司資訊可以刪除嗎
- 給誰看：property_manager
- 簽約資訊卡片旁的「管理」按鈕會開啟「團隊資訊管理」視窗，會列出這個團隊目前所有的公司資訊，可以點「新增」加入一組新的公司資訊。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 清單上每組公司資訊旁都有一個可以點擊刪除的圖示，但清單的第一筆沒有這個刪除圖示，不能被刪除。〔src/components/Lightbox/SignerInfosEdit.vue〕

### 沒有查看團隊資訊的權限，打開團隊資訊頁會怎樣？（提示「您目前登入的帳號無法查看團隊資訊功能」）
- 講法：沒有權限看團隊資訊會怎樣／團隊資訊頁打不開／無法查看團隊資訊功能是什麼意思
- 給誰看：property_manager
- 如果目前登入的帳號沒有查看團隊資訊的權限，系統會提示「您目前登入的帳號無法查看團隊資訊功能」。〔app/Http/Controllers/UserController.php〕

### 簽約資訊卡上有哪些地址欄位群？（個人的戶籍地址／通訊地址、公司的登記地址／通訊地址，都有「同上」可以直接帶入；社宅團隊另有經紀人與租賃管理人員各自的通訊地址）
- 講法：簽約資訊有哪些地址欄位／通訊地址可以跟戶籍地址一樣嗎／公司通訊地址在哪填
- 給誰看：property_manager
- 個人資訊區塊有「戶籍地址」與「通訊地址」兩組地址欄位，通訊地址可以點「同戶籍地址」直接帶入戶籍地址的內容。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 公司資訊區塊有「公司登記地址」與「公司通訊地址」兩組地址欄位，公司通訊地址可以點「同公司登記地址」直接帶入。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 社宅團隊還會多出「經紀人通訊地址」與「租賃管理人員通訊地址」這兩組獨立的地址欄位，一般團隊看不到這兩組。〔src/pages/users/team/_parts/SignerDetails.vue〕

### 怎麼在多組簽約資訊之間切換？（頁面上方有分頁式選單，超過 5 組會收進「所有團隊」下拉選單）
- 講法：怎麼切換不同的簽約資訊／簽約資訊太多組要怎麼選／所有團隊下拉選單是什麼
- 給誰看：property_manager
- 團隊資訊管理裡新增的每一組公司資訊，都會在簽約資訊卡片上方變成一個可以點擊切換的分頁項目。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 當公司資訊超過 5 組時，畫面會多出一個「所有團隊」的下拉選單；這個下拉選單列出的是全部組數（不是只有超過 5 組後多出來的部分），點選其中一項一樣可以切換過去。〔src/pages/users/team/_parts/SignerDetails.vue〕

## 成員列表（邀請、角色、成員名下資料）（13 條；頁：web:users.team、users.team.member.owned）

### 成員列表可以看到什麼資訊？（成員總人數、加入時間、Email、手機號碼、目前的角色）
- 講法：成員列表看得到什麼／成員清單有哪些欄位／怎麼看成員的角色／成員名下有沒有物件怎麼看
- 給誰看：property_manager
- 成員列表頁面上方會顯示目前團隊的成員總人數（含團隊擁有者本人）。〔resources/views/users/team/index.blade.php〕
- 清單上每位成員會顯示加入時間、Email、手機號碼，以及目前套用的角色名稱。〔resources/views/users/team/index.blade.php〕

### 怎麼邀請新成員加入團隊？（用 Email 或手機號碼搜尋，對方要先是 JGB 會員）
- 講法：怎麼邀請成員／新增成員流程／邀請成員要對方先註冊嗎／成員邀請用 email 還是手機
- 給誰看：property_manager
- 點擊成員列表的「邀請」按鈕會開啟「新增成員」視窗，可以選擇用 Email 或手機號碼搜尋要邀請的對象。〔resources/views/users/team/index.blade.php〕
- 受邀請的對象如果還不是 JGB 會員，系統會提示這個帳號尚未成為 JGB 會員，不能把他新增為團隊成員。〔resources/views/users/team/index.blade.php〕
- 可以一次搜尋加入多位對象到「即將新增成員」清單，確認後一次送出邀請。〔resources/views/users/team/index.blade.php〕

### 成員的「角色」權限決定什麼？（決定看得到與能編輯的物件、合約、帳務、修繕等範圍）
- 講法：角色權限是什麼／角色能設定哪些權限／團隊擁有者的權限跟一般成員一樣嗎／成員權限範圍怎麼分
- 給誰看：property_manager、prospect
- 每位成員會被指派一個「角色」，角色的權限設定決定這位成員能不能查看、新增、編輯、刪除物件、合約、帳務、修繕等資料，以及看的是自己名下的還是整個團隊的。〔app/Http/Controllers/UserController.php〕
- 除了物件、合約、帳務、修繕之外，角色權限也能授予查看團隊權限、查看或編輯團隊資訊、查看成員列表、查看大房東列表、查看租客列表等團隊管理相關功能。〔app/Http/Controllers/UserController.php〕
- 團隊擁有者是創建這個團隊的人，權限固定，不能被編輯或刪除。〔resources/views/layouts/lightbox/character-capability-edit.blade.php〕

### 怎麼管理團隊的角色範本？（可新增、編輯、刪除，也能套用 JGB 內建的快速設定範本）
- 講法：角色管理在哪／怎麼新增角色／角色範本有哪些／刪除角色會怎樣
- 給誰看：property_manager
- 點擊成員列表的「角色管理」，可以看到團隊內所有角色，點「編輯」可以調整角色名稱與權限細節。〔resources/views/layouts/lightbox/character-capability-edit.blade.php〕
- 新增角色時可以直接點「快速設定」套用 JGB 提供的權限參考範本，例如店長、會計等內建範本，再自行微調。〔resources/views/layouts/lightbox/character-capability-edit.blade.php〕
- 角色刪除後無法恢復。〔resources/views/layouts/lightbox/character-capability-edit.blade.php〕

### 怎麼移除成員？（列表右側的紅色 × 圖示開啟確認視窗，按「移除」才會真的刪除；名下還有物件或合約會被擋下）
- 講法：怎麼移除成員／成員名下有物件不能刪怎麼辦／移除成員後果／成員擁有的物件怎麼轉移給別人
- 給誰看：property_manager
- 點成員列表這一列右側的紅色 × 圖示，會跳出「移除成員」確認視窗，按「移除」才會真的刪除這位成員。〔resources/views/users/team/index.blade.php〕
- 如果這位成員名下還有綁定中的物件或合約，系統會先擋下移除，改跳出提示，要先指派其他經理人後才能進行移除動作。〔resources/views/users/team/index.blade.php〕
- 這時候可以點進「〔成員姓名〕擁有的物件」或「擁有的合約」頁面，把每一筆物件或合約的授權移除，再回來移除這位成員。〔src/pages/users/team/memberOwned/Index.jsx〕
- 成員移除後，對方將無法再存取這個團隊內的任何資訊。〔resources/views/users/team/index.blade.php〕

### 邀請成員有名額上限嗎？（依訂閱方案而定，達上限要升級方案才能繼續邀請）
- 講法：成員邀請有上限嗎／團隊成員人數上限／邀請額滿怎麼辦
- 給誰看：property_manager、prospect
- 團隊可以邀請的成員人數上限，是由目前的訂閱方案決定的。〔resources/views/layouts/lightbox/general.blade.php〕
- 達到上限後，點「邀請」不會開啟邀請視窗，而是提示已達到數量上限，並導引前往升級訂閱方案。〔resources/views/layouts/lightbox/general.blade.php〕

### 怎麼指派物件或合約給成員？（點成員旁的鉛筆圖示選「編輯綁定物件」或「編輯綁定合約」）
- 講法：怎麼指派物件給成員／編輯綁定合約在哪／成員名下物件怎麼調整
- 給誰看：property_manager
- 成員列表每一列右側有鉛筆圖示，點開可以選「編輯綁定物件」或「編輯綁定合約」，會跳到這位成員擁有的物件／合約頁面。〔resources/views/users/team/index.blade.php〕
- 在「〔成員姓名〕擁有的物件」或「擁有的合約」頁面，可以點「授權更多物件／合約」加入新的授權，或點「移除所有授權」一次撤銷這位成員的所有物件／合約授權。〔src/pages/users/team/memberOwned/Index.jsx〕

### 怎麼查看每個角色能做什麼？（點「角色權限說明」的「這裡」開啟角色權限列表，每一列是一項權限、每一欄是一個角色，用勾號／叉號表示有沒有這項權限）
- 講法：角色權限列表在哪看／角色權限說明在哪／目前團隊還沒有角色怎麼辦
- 給誰看：property_manager
- 成員列表頁面點「角色權限說明請點擊這裡」，會開啟「角色權限列表」視窗，用表格列出團隊內每個角色目前擁有的權限：每一列是一項權限（部分權限旁邊有說明文字），每一欄對應一個角色，用綠色勾號或灰色叉號表示這個角色有沒有這項權限。〔resources/views/users/team/index.blade.php〕
- 如果團隊目前還沒有建立任何角色，角色權限列表會顯示「目前團隊還沒有任何角色，您可以選擇：」，並提供「新增角色」的按鈕。〔resources/views/layouts/lightbox/character-capability-edit.blade.php〕

### 成員列表可以直接改成員的角色嗎？（列表每一列都有角色下拉選單可以直接切換；選單裡也有「+ 新增角色」，可以直接開「編輯角色」視窗）
- 講法：列表上怎麼改成員角色／角色下拉選單怎麼用／新增角色的入口在哪裡
- 給誰看：property_manager
- 成員列表每一列都有一個角色下拉選單，選擇要指派的角色後就會直接送出變更，不用另外打開編輯視窗。〔resources/views/users/team/index.blade.php〕
- 這個下拉選單最下面有一個「+ 新增角色」選項，點選後會直接開啟「編輯角色」視窗，不用先離開成員列表。〔resources/views/users/team/index.blade.php〕

### 編輯角色時的「開啟條件」是什麼？（要先勾選列出的其他權限，這個權限選項的勾選框才能點；沒先勾好之前，勾選框會維持鎖住）
- 講法：為什麼有些權限打不開／開啟條件是什麼意思／角色編輯畫面權限勾不起來
- 給誰看：property_manager
- 「編輯角色」視窗裡，部分權限選項旁邊會顯示「開啟條件」文字，列出必須先勾選的其他權限。〔resources/views/layouts/lightbox/character-capability-edit.blade.php〕
- 在還沒勾選完開啟條件列出的權限之前，這個選項的勾選框會維持鎖住、無法點選；全部勾好開啟條件之後，這個選項才能勾選。〔resources/views/layouts/lightbox/character-capability-edit.blade.php〕

### 編輯角色時的「重設條件」按鈕是做什麼的？（把目前正在編輯、還沒儲存的勾選狀態還原）
- 講法：重設條件按鈕做什麼／角色編輯畫面的重設是什麼意思／角色勾選錯了怎麼還原
- 給誰看：property_manager
- 編輯角色或新增角色的視窗下方有「重設條件」按鈕，點下去會把所有權限勾選全部清空，包含編輯既有角色時原本已載入的勾選。〔src/store/modules/team/capabilityEdit.js〕

### 成員列表可以怎麼排序？（姓名、加入時間、手機號碼、Email、角色名稱各有正反兩種排序）
- 講法：成員列表怎麼排序／可以依加入時間排序嗎／成員排序有哪些選項
- 給誰看：property_manager
- 成員列表可以依姓名（A-Z／Z-A）、加入時間（早／晚）、手機號碼（小／大）、Email（A-Z／Z-A）、角色名稱（A-Z／Z-A）排序，一共 10 種排序方式可以選。〔src/entry/team.js〕

### 為什麼「團隊擁有者」和自己那一列的角色下拉不能改？（這兩列是固定顯示在列表最上面、角色下拉是鎖住的，跟其他成員分開處理）
- 講法：團隊擁有者角色不能改嗎／自己的角色下拉是灰的／為什麼有一列選不了角色
- 給誰看：property_manager
- 成員列表最上面會固定顯示「團隊擁有者」與「自己（登入帳號本人）」各一列，如果登入帳號本人就是團隊擁有者則只顯示一列；這兩列各自的角色下拉選單是鎖住的、不能點選變更。〔resources/views/users/team/index.blade.php〕
- 「團隊擁有者」是系統內建的固定角色，不會出現在成員的角色下拉選單裡。〔config/character.php〕

## 大房東列表與授權物件（12 條；頁：bigLandlords.index、bigLandlords.list、users.team.owned、web:users.team）

### 大房東列表可以看到哪些欄位？（ID、姓名、會員註冊、身分證字號、生日、主要聯絡方式、帳戶資訊、合作方式、合作起迄、所屬物件）
- 講法：大房東列表有哪些欄位／大房東資料看得到什麼／大房東的合作起迄怎麼看
- 給誰看：property_manager
- 大房東列表的每一筆資料會顯示 ID、姓名、會員註冊、Email、手機號碼、身分證字號、地址、帳戶名稱與帳戶資訊。〔src/pages/bigLandlords/list/_parts/ListTable.vue〕
- 另外還會顯示合作方式、合作起迄日期、這位大房東目前被授權的所屬物件數量，以及生日、主要聯絡方式。〔src/pages/bigLandlords/list/_parts/ListTable.vue〕
- 點擊姓名可以開啟這位大房東的聯絡資訊卡。〔src/pages/bigLandlords/list/_parts/ListTable.vue〕

### 怎麼新增大房東？（已註冊會員填 Email 即可，未註冊只要填姓氏與名稱，Email 選填）
- 講法：怎麼新增大房東／大房東還沒註冊怎麼辦／新增大房東要填什麼
- 給誰看：property_manager
- 點擊大房東列表的「新增大房東」，系統會先問這位大房東是否已經註冊 JGB 帳號。〔src/components/Lightbox/MemberInvite.vue〕
- 如果已經註冊，只要輸入對方的 Email 按「新增」就可以加入。〔src/components/Lightbox/MemberInvite.vue〕
- 如果還沒註冊，姓氏與名稱是必填，Email 則是選填。〔src/components/Lightbox/MemberInvite.vue〕
- ⚠️ 待查：team/index.blade.php 的 id="inviteMember" 燈箱（type=2）文案是「受邀請的對象如果不是 JGB 會員，將無法新增為大房東」，且只提供 Email／手機號碼搜尋既有會員，不像本細目引用的 MemberInvite.vue 有『未註冊』分支可直接填姓氏＋名稱建立非會員大房東；兩者是否對應同一個『新增大房東』入口、或分屬新舊兩套介面，待業主確認。

### 大房東的「授權物件」怎麼設定？（逐筆物件勾選瀏覽廣告／合約／帳務／修繕；合約要先勾廣告，帳務要先勾廣告＋合約，修繕沒有前提）
- 講法：大房東能看到哪些資料／怎麼授權物件給大房東／大房東權限怎麼設定／移除大房東的物件授權
- 給誰看：property_manager
- 點進「〔大房東姓名〕擁有的物件」頁面，可以看到目前授權給這位大房東的物件清單，並針對每一筆物件個別勾選「瀏覽物件廣告」「瀏覽物件所屬合約」「瀏覽物件所屬帳務」「瀏覽物件所屬修繕」這幾項權限。〔src/pages/bigLandlords/list/_parts/owned.jsx〕
- 「瀏覽物件所屬合約」要先勾選「瀏覽物件廣告」才能勾；「瀏覽物件所屬帳務」要先勾選「瀏覽物件廣告」與「瀏覽物件所屬合約」才能勾；「瀏覽物件所屬修繕」則沒有前提，可以直接勾選。〔app/Http/Controllers/UserController.php〕
- 這個頁面也可以填寫這筆物件的「合作方式」與「合作起迄」日期備註。〔src/pages/bigLandlords/list/_parts/owned.jsx〕
- 點「授權更多物件」可以挑選其他物件加入授權；點「移除所有授權」會一次撤銷這位大房東的所有物件授權。〔src/pages/bigLandlords/list/_parts/owned.jsx〕

### 大房東名單可以批次匯入或匯出嗎？（可以，Excel 匯入新增、Excel 匯出下載）
- 講法：大房東可以批次匯入嗎／大房東資料怎麼匯出／大房東 excel 匯入匯出在哪
- 給誰看：property_manager、prospect
- 大房東列表的「新增大房東」按鈕旁有下拉選單，可以選擇「匯入大房東」開啟批次匯入視窗。〔src/pages/bigLandlords/list/_parts/PageTop.vue〕
- 清單有資料時，同一個下拉選單也可以選「匯出大房東」，下載 Excel 格式的大房東資料。〔src/pages/bigLandlords/list/_parts/PageTop.vue〕

### 大房東列表每一列的操作選單有哪些功能？（編輯所屬物件、編輯大房東、刪除大房東）
- 講法：怎麼刪除大房東／移除大房東流程／大房東資料怎麼編輯
- 給誰看：property_manager
- 每一筆大房東資料旁的操作選單，可以選「編輯所屬物件」跳到授權物件頁面、「編輯大房東」修改資料，或「刪除大房東」移除這位大房東。〔src/use/config/useBigLandlordsTypes.ts〕

### 授權物件頁取消勾選後，為什麼要按「套用」才會生效？（取消勾選只是待處理狀態，按套用才真的移除，按恢復可以取消這次變更）
- 講法：授權物件取消勾選沒反應／套用按鈕是做什麼的／取消勾選可以復原嗎
- 給誰看：property_manager
- 在授權物件頁把某項權限取消勾選後，畫面只會先標示「「套用」後將移除此物件」，並不會立刻生效。〔src/pages/bigLandlords/list/_parts/owned.jsx〕
- 要按下頁面下方的「套用」按鈕，這次的變更才會真正送出；在按下套用之前，也可以點「恢復」把這次的取消勾選還原。〔src/pages/bigLandlords/list/_parts/owned.jsx〕

### 刪除大房東會發生什麼？（先跳出確認視窗，確認後這位大房東就無法再存取這個團隊的任何資訊）
- 講法：刪除大房東會怎樣／大房東刪除確認視窗／刪除大房東後對方還能登入嗎
- 給誰看：property_manager
- 點操作選單的「刪除大房東」會先跳出「移除大房東」確認視窗，詢問是否確定要刪除。〔src/components/Lightbox/MemberDelete.vue〕
- 確認刪除後，這位大房東就無法再存取這個團隊內的任何資訊。〔src/components/Lightbox/MemberDelete.vue〕

### 大房東列表上方的「所有權人／轉租人」是做什麼用的？（記錄代管物件的所有權人或轉租人資料，加快編輯合約速度）
- 講法：所有權人轉租人是什麼／怎麼新增所有權人／轉租人資料在哪管理
- 給誰看：property_manager
- 大房東列表上方有「所有權人／轉租人」區塊，可以紀錄代管物件的所有權人或轉租人資料，提升日後編輯合約的效率。〔resources/views/users/team/index.blade.php〕
- 可以點「新增」建立一筆，操作選單則有「編輯所有權人」與「刪除所有權人」；清單筆數多時可以點「載入更多」繼續往下載。〔resources/views/users/team/index.blade.php〕

### 大房東名額有上限嗎？（大房東列表頁的「新增大房東」目前沒有名額檢查；成員／大房東管理頁（團隊管理底下的大房東列表）的「邀請」按鈕才有，額滿時會提示升級方案）
- 講法：大房東可以新增幾位／大房東名額上限／大房東額滿怎麼辦
- 給誰看：property_manager、prospect
- 大房東列表頁上「新增大房東」按鈕背後的新增流程，沒有名額上限的檢查邏輯，目前可以持續新增。〔src/pages/bigLandlords/list/_parts/PageTop.vue〕
- 另外還有一個「成員／大房東管理」頁面（團隊管理底下的大房東列表），上面「邀請」按鈕在名額已滿時會換成提示「已達到數量上限！」並導引前往升級方案；這個名額檢查是綁在按邀請送出的當下，不是綁在大房東列表頁的新增大房東流程上。〔resources/views/users/team/index.blade.php〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:app/Http/Controllers/BiglandlordController.php | grep -ciE 'limit|上限'", 'result': '0 — BiglandlordController 全檔（22 個 public function，含新增大房東的 store()）沒有任何名額／上限檢查邏輯', 'control_term': "git -C jgb2/dev2 show master:app/Http/Controllers/BiglandlordController.php | grep -c 'public function' => 22（正對照組：同一檔案確實有 22 個 public function 被 grep 找到，證明檔案讀得到、不是查詢方式壞掉）"}`

### 大房東列表沒有資料時會顯示什麼？（一開始沒有任何大房東顯示「尚無大房東」；用關鍵字搜尋卻沒有符合結果則顯示「沒有符合的結果😢」）
- 講法：大房東列表是空的／還沒有大房東畫面長怎樣／搜尋不到大房東會顯示什麼
- 給誰看：property_manager
- 大房東列表目前一筆資料都沒有、而且沒有輸入搜尋關鍵字時，表格會顯示「尚無大房東」。〔src/pages/bigLandlords/list/_parts/ListTable.vue〕
- 如果是用關鍵字搜尋、但搜尋不到符合的大房東，表格則會顯示「沒有符合的結果😢」。〔src/pages/bigLandlords/list/_parts/ListTable.vue〕

### 批次匯入大房東的 Excel 範本要填哪些欄位？（姓氏、名稱必填，其餘含 Email、手機、身分證字號、地址、帳戶資訊、合作方式與合作起迄都是選填）
- 講法：大房東匯入範本欄位／批次新增大房東要填什麼／大房東匯入哪些欄位必填
- 給誰看：property_manager
- 「匯入大房東」的批次匯入範本裡，只有姓氏與名稱是必填欄位。〔src/components/ImportPreview/configs/bigLandlord.ts〕
- 其餘 Email、手機號碼、身分證字號、國家／縣市／區域／地址、帳戶名稱、帳戶資訊、合作方式、合作起始與終止時間都是選填欄位。〔src/components/ImportPreview/configs/bigLandlord.ts〕

### 大房東列表可以用什麼排序？（姓名、手機號碼、Email、身分證字號，各有正序與反序共 8 種排序方式）
- 講法：大房東列表怎麼排序／可以用身分證字號排序嗎／大房東列表排序選項有哪些
- 給誰看：property_manager
- 大房東列表可以依姓名、手機號碼、Email、身分證字號這四個欄位排序，每個欄位都有正序（A-Z／小到大）與反序（Z-A／大到小）兩種方向，總共 8 種排序方式。〔app/Http/Controllers/BiglandlordController.php〕

## 大房東報表（3 條；頁：bigLandlords.report）

### 大房東報表可以看到什麼？（依大房東列出所屬物件、出租中物件與執行中合約租金總額）
- 講法：大房東報表看得到什麼／大房東報表怎麼看／大房東的物件租金總額在哪查／大房東報表可以下載嗎
- 給誰看：property_manager
- 大房東報表清單會依大房東列出姓名、所屬物件數、出租中物件數，以及目前執行中合約的租金總額。〔src/pages/bigLandlords/report/_parts/ListTable.vue〕
- 點開單一大房東的細節，可以進一步看到底下每個社區、每筆物件的租客、租期與租金明細，並能個別下載報表。〔src/pages/bigLandlords/report/_parts/BigLandlordItemDetail.jsx〕
- 報表會用團隊在「進階設定」設定的結算幣別，把不同幣別的合約金額換算成同一種幣別做加總。〔src/pages/users/advance/Index.jsx〕

### 誰看得到大房東報表？（需要「查看大房東報表」的角色權限）
- 講法：大房東報表誰能看／查看大房東報表權限／為什麼看不到大房東報表
- 給誰看：property_manager
- 側邊選單裡的「大房東報表」項目，要這位成員的角色有查看大房東報表的功能權限，才不會在選單整理時被拿掉。〔app/Role.php〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:app/Role.php | grep -nF 'if ($isBigLandlord || $isCurrentUser || $showBigLandlordReport) {'", 'result': "1（4141 行）— 這段只決定「大房東報表」子項目要不要先被加進選單陣列，加進去以後還會在下面的 foreach ($item['sub'] ...) 迴圈裡，用 itemSub['permission']（'show_biglandlord_report'）再檢查一次 $currentPermission，沒有這個權限一樣會被 unset 拿掉；真正決定使用者看不看得到的是這個 foreach 迴圈，不是 addSubItem 那一段", 'control_term': 'git -C jgb2/dev2 show master:app/Role.php | grep -cF "\'大房東報表\'," => 1（正對照組：同一段 addSubItem 呼叫裡的選單文字「大房東報表」確實命中，證明 grep 找得到這段程式碼，不是查詢方式壞掉）'}`

### 大房東報表可以依社區細看嗎？（報表清單有「社區」欄，細節頁還會顯示匯率）
- 講法：大房東報表有社區欄嗎／大房東報表匯率在哪看／報表可以下載社區層級嗎
- 給誰看：property_manager
- 大房東報表清單有一欄「社區」，顯示這位大房東名下物件所屬的社區。〔src/pages/bigLandlords/report/_parts/ListTable.vue〕
- 點開大房東報表細節，畫面上會顯示「匯率」欄，並且「所有物件」「社區」「物件」三個層級各自都有獨立的「下載報表」按鈕，可以分別下載對應範圍的報表。〔src/pages/bigLandlords/report/_parts/BigLandlordItemDetail.jsx〕

## 大房東對帳表（7 條；頁：bigLandlords.sheet）

### 大房東對帳表在算什麼？（只有特定合作團隊看得到完整的押金、屋主資金、屋主提領、屋主直收等類別金額，其他團隊只看得到屋主租金收支；單月報表才有「上一月」「下一月」「下載」，整年度報表是「匯出報表」）
- 講法：大房東對帳表看什麼／對帳表怎麼看押金收支／對帳表可以下載嗎／對帳表怎麼切換月份
- 給誰看：property_manager
- 對帳表以月份為單位列出各類別金額；只有特定合作團隊看得到完整的押金收入／支出、屋主資金收入／支出、屋主提領、屋主直收收入／支出等類別，其他團隊只看得到「屋主租金收入」「屋主租金支出」（部分團隊的用語會改顯示為「租金收入」「本期支出」）。〔src/pages/bigLandlords/sheet/_parts/Sheet.vue〕
- 「上一月」「下一月」「下載」「取消」這幾個按鈕只出現在單月報表畫面（網址帶 1 到 12 月其中一個月份參數）；查看整年度對帳表時看到的不是這幾個按鈕，而是可以切換年份、匯出整年度資料的「匯出報表」按鈕。〔src/pages/bigLandlords/sheet/index.vue〕
- ⚠️ 待查：「年度累計」欄目前是刻意隱藏：SelectBar.jsx 的 `const SHOW_YEARLY_COLUMN = false`（註解「2026-04-30 Joanna 拍板暫時隱藏」）與 Sheet.vue 對應區塊的 `v-if="false"` 都關閉了這一欄，畫面上不會顯示年度累計金額。是否要在知識裡提到這個欄位存在但目前關閉，或完全不提，待業主確認。
- ⚠️ 待查：月報明細（monthlyReport/ReconciliationTerm.vue、EZoneCashflow.vue 等）裡「租金收入」「本期支出」這兩個標題，只在 isLabelAdjust（useBigLandlordLabelAdjust）為真的團隊才會顯示；不是這個條件的團隊看到的是「屋主租金收入」「屋主租金支出」（V2 角色則是「本期屋主資金收入」「本期屋主資金支出」）。這兩套標題語義是否要分開寫成兩條知識、或只取一種當作『對外說法』，待業主確認。

### 對帳表顯示「尚未被指派物件」是什麼意思？（這位大房東還沒被授權任何物件）
- 講法：對帳表沒資料怎麼辦／大房東報表空白原因／大房東還沒授權物件會怎樣
- 給誰看：property_manager
- 如果這位大房東目前還沒有被授權任何物件，對帳表會提示這位大房東尚未被指派物件，需要先到「大房東管理」指派物件，才會有資料。〔src/pages/bigLandlords/sheet/index.vue〕

### 對帳表出現「本月含多幣別帳單」提示是什麼意思？（該月的帳單有不同幣別，已用結算幣別加總）
- 講法：對帳表多幣別提示是什麼／為什麼金額有換算過的字樣／多幣別合計怎麼算
- 給誰看：property_manager
- 如果某個月份的帳單含有不同幣別，對帳表會在該區塊顯示「本月含多幣別帳單（〔幣別列表〕），以〔結算幣別〕結算合計」的提示，代表這個小計已經把不同幣別換算成同一種幣別加總。〔src/pages/bigLandlords/sheet/_parts/SheetTemplate.vue〕

### 對帳表可以隱藏沒有金額的項目嗎？（可以開關「隱藏空值項目」）
- 講法：對帳表可以只看有金額的項目嗎／隱藏空值項目是什麼／對帳表列太多怎麼精簡
- 給誰看：property_manager
- 對帳表上方可以開關「隱藏空值項目」，開啟後金額為零的類別列不會顯示在表格上。〔src/pages/bigLandlords/sheet/_parts/SelectBar.jsx〕

### 對帳表怎麼從年表切到單一月份的月報？（點表頭的月份會進入該月月報，點「取消」回到年表）
- 講法：對帳表年表怎麼看單月明細／月報怎麼回到年表／點月份沒反應
- 給誰看：property_manager
- 年度對帳表的表頭可以點某個月份，進入這個月的月報明細畫面。〔src/pages/bigLandlords/sheet/_parts/Sheet.vue〕
- 在月報畫面下方點「取消」，會離開這個月份的明細，回到原本的年度對帳表。〔src/pages/bigLandlords/sheet/index.vue〕

### 對帳表載入或下載失敗會怎樣？（載入失敗會顯示錯誤並提供「重試」，下載失敗只顯示錯誤訊息）
- 講法：對帳表載入失敗怎麼辦／報表下載失敗怎麼辦／對帳表重試按鈕在哪
- 給誰看：property_manager
- 對帳表載入失敗時，畫面會顯示「報表載入失敗，請稍後再試」（或畫面顯示的錯誤訊息），並提供「重試」按鈕重新載入。〔src/pages/bigLandlords/sheet/index.vue〕
- 下載月報失敗時，畫面會顯示「報表下載失敗，請稍後再試」，但這個提示不提供重試按鈕，需要再次點擊「下載」。〔src/pages/bigLandlords/sheet/index.vue〕

### 大房東對帳表頁面的側邊選單和載入畫面長怎樣？（左側有社區／物件選單，看單一物件報表時會顯示上次匯入時間，報表產生中會顯示載入百分比進度條）
- 講法：對帳表左邊選單是什麼／上次匯入時間在哪看／對帳表載入畫面在跑什麼
- 給誰看：property_manager
- 對帳表頁面左側有一個側邊選單，可以選擇要看整個社區還是特定物件的對帳資料。〔src/pages/bigLandlords/sheet/index.vue〕
- 切換到看單一物件的報表時，畫面上會顯示這個物件資料「最後導入時間」；看社區整體報表時不會顯示這個時間。〔src/pages/bigLandlords/sheet/index.vue〕
- 報表資料在產生中的時候，畫面中間會顯示一個百分比進度條，數字會隨著報表產生進度往上跳動。〔src/pages/bigLandlords/sheet/index.vue〕

## 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」）⇄ 由 A 移入（18 條；頁：users.advance）

### 帳單的「自訂費用項目」怎麼設定？（分收入類／支出類，必填性質與自定義名稱，會科品項代號選填）
- 講法：費用項目怎麼設定／自訂費用分收入支出類嗎／帳單費用項目性質怎麼選／費用項目可以合併嗎
- 給誰看：property_manager
- 進階設定的「帳務管理」區塊可以設定帳單「自訂費用」的收付項目，分成「收入類」與「支出類」。〔src/pages/users/advance/_part/FeesItemManagement.vue〕
- 新增每個項目時要選擇「性質」（例如租金、押金、水費、電費、管理費、清潔費、網路費、滯納金、違約金、賠償金、押金設算息、其他），並填寫「自定義名稱」，這兩項都是必填。〔src/pages/users/advance/_part/FeePanel.vue〕
- 「會科品項代號」是選填欄位，用來提供給 ERP／會計系統拋轉使用。〔src/pages/users/advance/_part/FeePanel.vue〕

### 進階設定的「優惠項目」是給誰用的？（只有統上或新北住都的合作團隊才看得到，可設定折扣套用在租金費用上）
- 講法：進階設定有租金折扣嗎／優惠項目怎麼設定
- 給誰看：property_manager、prospect
- 進階設定「合約管理」區塊的「優惠項目」只會顯示給統上或新北住都的合作團隊，一般團隊的進階設定沒有這個設定。〔src/pages/users/advance/Index.jsx〕
- 有這個設定的團隊最多可以建立 10 組優惠項目（新北住都合作團隊上限是 30 組），在計算租金費用時套用折扣。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '840,842p' | grep -c 'isTongSang\\|isNthurc'", 'result': '1 — 「優惠項目」FormBlock 整段被 (state.isTongSang || state.isNthurc) 包住，一般團隊不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'749,753p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：緊接在後的「物件管理」區塊標題確實命中，證明 grep 本身能在這個檔案裡找到東西，不是查詢方式壞掉）'}`

### 進階設定的「延遲金設置」怎麼計算？（只有統上合作團隊看得到，公式是租金 × (逾期天數 - 緩衝天數) × 延遲金%）
- 講法：進階設定有滯納金設定嗎／延遲金怎麼算／逾期繳費會產生什麼費用／延遲金設置在哪
- 給誰看：property_manager、prospect
- 「延遲金設置」只會出現在統上這個合作團隊的進階設定裡，一般團隊沒有這個設定。〔src/pages/users/advance/Index.jsx〕
- 有這個設定的團隊可以開啟或關閉延遲金功能，並設定緩衝天數與延遲金百分比。〔src/pages/users/advance/Index.jsx〕
- 開啟後，租客逾期繳租超過緩衝天數，系統會自動計算延遲金並產生一筆帳單，這筆帳單的繳費截止日就是合約的終止日；計算公式是：租金 ×（逾期天數 - 緩衝天數）× 延遲金百分比。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '933,935p' | grep -c isTongSang", 'result': '1 — 「延遲金設置」FormBlock 整段被 state.isTongSang 包住，一般團隊不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'749,753p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：緊接在後的「物件管理」區塊標題確實命中，證明 grep 本身能在這個檔案裡找到東西，不是查詢方式壞掉）'}`

### 「預設補充條款」怎麼設定？（最多可以設 3 組，編輯合約時直接選用）
- 講法：補充條款範本怎麼設定／合約補充條款可以存幾組／預設條款在哪編輯
- 給誰看：property_manager、prospect
- 進階設定的「合約管理」區塊可以設定至多三組常用的「預設補充條款」，編輯合約時可以直接選用，不用每次重新輸入。〔src/pages/users/advance/Index.jsx〕
- 每一組條款都可以新增、編輯、預覽（會轉成 PDF 預覽），也可以刪除。〔src/pages/users/advance/Index.jsx〕

### 「標籤設定」是做什麼用的？（幫物件加自訂標籤，單個標籤上限 18 字元）
- 講法：自訂標籤怎麼設定／標籤字數上限是多少／物件標籤在哪加
- 給誰看：property_manager、prospect
- 進階設定的「物件管理」區塊有一個「標籤設定」，可以先在這裡建立自訂標籤。〔src/pages/users/advance/Index.jsx〕
- 設定好標籤後，可以到物件管理的物件總表，幫不同的物件加上這些自訂標籤。〔src/pages/users/advance/Index.jsx〕
- 單一個標籤最多可以輸入 18 字元（約 9 個中文字）。〔src/pages/users/advance/Index.jsx〕

### 怎麼綁定智能裝置廠商？（輸入裝置廠商帳號密碼完成綁定，之後可在 JGB 平台管理裝置）
- 講法：智能裝置怎麼綁定／裝置管理在哪設定／裝置廠商綁定流程
- 給誰看：property_manager
- 進階設定的「裝置管理」區塊可以「綁定設備廠商」，綁定後就能在 JGB 平台內管理你的智能裝置。〔src/pages/users/advance/Index.jsx〕
- 點「開始綁定」後，要選擇裝置廠商並輸入該廠商的帳號密碼登入，才能完成綁定。〔src/pages/users/advance/Index.jsx〕
- 綁定完成的廠商會列在下方，每一筆都可以按「更新資料」重新取得裝置資料。〔src/pages/users/advance/Index.jsx〕

### 自訂費用項目可以合併嗎？（可以選多個已存在的品項合併成新品項，合併後無法回復）
- 講法：怎麼合併費用項目／合併品項後可以回復嗎／自訂費用項目合併操作
- 給誰看：property_manager
- 在「帳單自訂費用項目」可以點「合併項目」，選擇多個已存在的收入類或支出類品項，合併成一個新品項，合併後金額會一併統計。〔src/pages/users/advance/_part/FeesItemManagement.vue〕
- 品項合併後無法回復，操作前系統會提醒要謹慎操作。〔src/components/Lightbox/CustomFeeItemMerge.jsx〕

### 進階設定的「繳費週期優惠」是給誰用的？（只有統上團隊才看得到，選比月繳更長的繳費週期就有折扣）
- 講法：選季繳有折扣嗎／誰看得到繳費週期優惠設定
- 給誰看：property_manager、prospect
- 進階設定「合約管理」區塊的「繳費週期優惠」只會顯示給統上這個合作團隊，一般團隊（含新北住都）的進階設定沒有這個設定。〔src/pages/users/advance/Index.jsx〕
- 有這個設定的團隊，編輯合約時選擇比月繳更長的繳費週期，就能獲得租金折扣。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '886,888p' | grep -c isTongSang", 'result': '1 — 「繳費週期優惠」FormBlock 只被 state.isTongSang 包住（不含 isNthurc），新北住都團隊不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'749,753p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：緊接在後的「物件管理」區塊標題確實命中，證明 grep 本身能在這個檔案裡找到東西，不是查詢方式壞掉）'}`

### 「Email 通知語系」在哪設定、誰看得到？（只有法人房東或社宅團隊看得到，決定代發通知信的預設語系）
- 講法：Email 通知語系怎麼設定／個人房東有語系設定嗎／租客收到的通知信語言怎麼決定
- 給誰看：property_manager、prospect
- 進階設定的「全域設定」區塊只會顯示給法人房東或社宅團隊的身分，個人房東的進階設定看不到這個區塊，也就沒有「Email 通知語系」可以設定。〔src/pages/users/advance/Index.jsx〕
- 「Email 通知語系」可以設定系統代發給租客的通知信預設語系。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '548,551p' | grep -c '\\[3, 4\\].includes'", 'result': '1 — 「全域設定」整個區塊（含 Email 通知語系、時區設定、結算幣別）被 [3, 4].includes(role.config_rule_key) 包住，config_rule_key=2 的個人房東不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'749,753p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：緊接在後的「物件管理」區塊標題確實命中，證明 grep 本身能在這個檔案裡找到東西，不是查詢方式壞掉）'}`

### 「時區設定」會影響哪些通知？（只有法人房東或社宅團隊看得到，改變排程通知的發送時間）
- 講法：時區設定在哪／個人房東有時區設定嗎／改時區會影響什麼通知
- 給誰看：property_manager、prospect
- 「時區設定」跟「Email 通知語系」一樣在「全域設定」區塊，只有法人房東或社宅團隊看得到。〔src/pages/users/advance/Index.jsx〕
- 選擇非台灣時區後，像每日過期帳單通知、合約 30 天內到期提醒通知這類排程通知的發送時間，會改用所選的時區計算。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '548,551p' | grep -c '\\[3, 4\\].includes'", 'result': '1 — 「全域設定」整個區塊（含 Email 通知語系、時區設定、結算幣別）被 [3, 4].includes(role.config_rule_key) 包住，config_rule_key=2 的個人房東不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'749,753p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：緊接在後的「物件管理」區塊標題確實命中，證明 grep 本身能在這個檔案裡找到東西，不是查詢方式壞掉）'}`

### 「結算幣別」是做什麼用的？（只有法人房東或社宅團隊看得到，把大房東報表的多幣別合約統一結算成一種幣別）
- 講法：結算幣別是什麼／多幣別報表怎麼算／結算幣別在哪設定
- 給誰看：property_manager、prospect
- 「結算幣別」也在「全域設定」區塊，只有法人房東或社宅團隊看得到。〔src/pages/users/advance/Index.jsx〕
- 這個設定用來把大房東報表裡多種幣別的合約資訊，統一結算成一種幣別。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '548,551p' | grep -c '\\[3, 4\\].includes'", 'result': '1 — 「全域設定」整個區塊（含 Email 通知語系、時區設定、結算幣別）被 [3, 4].includes(role.config_rule_key) 包住，config_rule_key=2 的個人房東不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'749,753p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：緊接在後的「物件管理」區塊標題確實命中，證明 grep 本身能在這個檔案裡找到東西，不是查詢方式壞掉）'}`

### 為什麼進階設定看不到「裝置管理」區塊？（訂閱方案要生效中，且不能是免費方案）
- 講法：裝置管理不見了／免費方案可以綁裝置嗎／為什麼進階設定沒有裝置管理
- 給誰看：property_manager
- 進階設定的「裝置管理」區塊只有在訂閱方案生效中、且方案不是免費方案時才會顯示；訂閱未生效或使用免費方案的團隊看不到這個區塊。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '193,195p' | grep -c isSubscriptionActive", 'result': '1 — deviceState.isAllowUse 要求 role.isSubscriptionActive 且 plan_name 不是「免費方案」，兩個條件都要成立「裝置管理」區塊才會渲染', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'751p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：同檔案裡沒有身分條件包住、必定渲染的「物件管理」區塊標題確實命中，證明 grep 找得到這個檔案裡的東西；原本用來當正對照組的「房東專屬帳號」其實也被 config_rule_key in [3,4] 的條件包住，不能拿來當「必定顯示」的正對照）'}`

### 「房東專屬帳號」是做什麼用的？（只有法人房東或社宅團隊看得到；顯示在團隊首頁，且第一次儲存後不能自行修改，要洽 JGB 客服）
- 講法：房東專屬帳號是什麼／房東專屬帳號可以改嗎／房東專屬帳號在哪設定
- 給誰看：property_manager、prospect
- 「房東專屬帳號」欄位在「全域設定」區塊裡，這個區塊只有法人房東或社宅團隊的進階設定看得到，個人房東團隊沒有這個區塊。〔src/pages/users/advance/Index.jsx〕
- 進階設定「全域設定」區塊的「房東專屬帳號」會應用在這個團隊的「團隊首頁」上。〔src/pages/users/advance/Index.jsx〕
- 「房東專屬帳號」第一次儲存後就不能自行修改，要修改需要洽 JGB 客服人員處理。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '548,551p' | grep -c '\\[3, 4\\].includes'", 'result': '1 — 「全域設定」整個區塊（含房東專屬帳號）被 [3, 4].includes(role.config_rule_key) 包住，config_rule_key=2 的個人房東不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'751p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：同檔案裡沒有身分條件包住、必定渲染的「物件管理」區塊標題確實命中，證明 grep 找得到這個檔案裡的東西）'}`

### 招租廣告可以自動刊登或自動下架嗎？（可以，合約到期日前 N 天自動刊登，簽約後自動下架）
- 講法：招租廣告會自動上架嗎／簽約後廣告會自動下架嗎／自動刊登天數怎麼設定
- 給誰看：property_manager、prospect
- 進階設定「物件管理」區塊的「招租廣告自動刊登」啟用後，可以設定天數，物件的合約到期日在這個天數內時，系統會自動將這個物件的招租廣告刊登出去。〔src/pages/users/advance/Index.jsx〕
- 「招租廣告自動下架」啟用後，物件簽訂合約、進入執行中合約狀態時，系統會自動把這個物件的招租廣告下架。〔src/pages/users/advance/Index.jsx〕

### 「合約管理」的標籤設定跟物件的標籤設定是同一個嗎？（不是，這是合約專用的另一組標籤）
- 講法：合約可以加標籤嗎／合約標籤在哪設定／合約標籤跟物件標籤一樣嗎
- 給誰看：property_manager
- 進階設定「合約管理」區塊也有自己的「標籤設定」，用來建立合約專用的標籤，跟「物件管理」區塊那組給物件用的標籤設定是分開管理的兩組標籤。〔src/pages/users/advance/Index.jsx〕

### 「銷貨單品項代號對應」是做什麼用的？（只有特定團隊才有，設定匯出「M 化銷貨單」時每個品項要帶的產品代號）
- 講法：銷貨單品項代號對應是什麼／匯出銷貨單產品代號空白／哪些團隊有銷貨單品項代號設定
- 給誰看：property_manager
- 進階設定「帳務管理」區塊的「銷貨單品項代號對應」只有特定團隊的進階設定才會出現，是一項團隊層級的設定，不是每個團隊都有。〔src/pages/users/advance/_part/BillsManagement.vue〕
- 這個設定用來指定匯出「M 化銷貨單」時，每個費用品項要帶入的產品代號；沒有設定代號的品項，匯出檔案裡的產品代號會是空白，也可以指定哪些品項不要匯入銷貨單。〔src/pages/users/advance/_part/WenzhongItemCodeManagement.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/_part/BillsManagement.vue | sed -n '20,22p' | grep -c billExportPaymentDetail", 'result': '1 — showWenzhongItemCode 只有角色特殊群組包含 billExportPaymentDetail 才會是 true，「銷貨單品項代號對應」元件用 v-if="showWenzhongItemCode" 掛載，一般團隊不會渲染', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/advance/_part/BillsManagement.vue | sed -n '34p' | grep -c '帳務管理' => 1（正對照組：同檔案永遠顯示的「帳務管理」標題確實命中，證明 grep 找得到這個檔案裡的東西）"}`

### 「社區管理」的城市／區域／位置設定是做什麼？（只有特定合作團隊看得到，用來建立社區篩選用的自訂標籤）
- 講法：城市設定在哪／區域設定是什麼／位置設定跟標籤設定差在哪／誰看得到社區管理設定
- 給誰看：property_manager
- 進階設定的「社區管理」區塊只會顯示給特定合作團隊，一般團隊看不到這個區塊。〔src/pages/users/advance/Index.jsx〕
- 這個區塊有「城市設定」「區域設定」「位置設定」三組獨立的自訂標籤，設定好之後可以用來為物件加上對應的城市、區域、位置標籤。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '691,693p' | grep -c isBeyond360", 'result': '1 — 「社區管理」整個區塊被 state.isBeyond360 包住，一般團隊不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'749,753p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：緊接在後的「物件管理」區塊標題確實命中，證明 grep 本身能在這個檔案裡找到東西，不是查詢方式壞掉）'}`

### 進階設定的「短租期核可流程」是做什麼的？（只有統上合作團隊看得到；租期少於設定天數時，合約要先簽核通過才會發出邀請給租客）
- 講法：短租期核可流程是什麼／短租期簽核怎麼設定／租期太短要簽核嗎
- 給誰看：property_manager、prospect
- 進階設定「合約管理」區塊的「短租期核可流程」只會顯示給統上合作團隊，一般團隊的進階設定沒有這個設定。〔src/pages/users/advance/Index.jsx〕
- 啟用後，如果合約的租期少於設定的天數（短租期定義），這份合約在簽約前需要先進行簽核；簽核通過後，合約邀請才會發出給租客。〔src/pages/users/advance/Index.jsx〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n '985p' | grep -c isTongSang", 'result': '1 — 「短租期核可流程」FormBlock 整段被 state.isTongSang 包住，一般團隊不會渲染這個區塊', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/advance/Index.jsx | sed -n \'751p\' | grep -c "title={t(\'物件管理\')}" => 1（正對照組：同檔案裡沒有身分條件包住、必定渲染的「物件管理」區塊標題確實命中，證明 grep 找得到這個檔案裡的東西）'}`

## 租客列表（當前租客／封存、準時繳租率、信用評價）⇄ 由 A 移入（14 條；頁：users.lesseeList）

### 租客列表有哪兩個分頁？（當前租客／封存，封存代表這位租客已被移出列表且目前沒有進行中的合約）
- 講法：租客列表分幾種／準時繳租率怎麼算／封存的租客是什麼
- 給誰看：property_manager、prospect
- 租客列表分成「當前租客」與「封存」兩個分頁，涵蓋簽約成功的租客，以及房東自行管理、還沒正式簽約的潛在租客。〔src/pages/users/lesseeList/parts/ListTable.vue〕
- 把一位租客「封存」等於把他從當前租客列表移除；如果這位租客目前還有進行中的合約，系統會擋下這個動作、不能封存。〔app/Services/LesseeService.php〕

### 租客列表的「信用評價」欄位為什麼有些人看不到？（需要有查看租客信用評價的權限才會顯示這一欄）
- 講法：信用評價欄位不見了／為什麼看不到信用評價／租客信用評價需要什麼權限
- 給誰看：property_manager
- 租客列表可以顯示「信用評價」欄位，但只有擁有「查看租客信用評價」權限的成員，畫面上才會出現這一欄；沒有這個權限的人，整欄完全不會出現，也不會佔用表格版面。〔src/pages/users/lesseeList/parts/ListTable.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -c show_credit_rating master -- src/pages/users/lesseeList/parts/ListTable.vue', 'result': '1 — 「信用評價」欄位是唯一一個用 show_credit_rating 權限包住、沒有權限就整欄從陣列拿掉的欄位定義', 'control_term': 'git -C jgb2/dev2 grep -c "title: t(\'國籍\')" master -- src/pages/users/lesseeList/parts/ListTable.vue => 1（正對照組：同檔案「國籍」欄位定義確實命中，證明 grep 能在這個檔案找到東西；「國籍」欄位定義本身沒有任何權限判斷）'}`

### 租客列表可以新增、匯入、匯出租客嗎？（可以手動新增，也支援 Excel 匯入與匯出）
- 講法：租客列表可以新增租客嗎／租客資料怎麼匯入匯出／已簽約的租客可以改名字嗎
- 給誰看：property_manager、prospect
- 租客列表可以「新增租客」手動加入一筆租客資料，也可以用「匯入租客」批次匯入，或「匯出租客」下載成 Excel。〔src/pages/users/lesseeList/parts/PageTop.vue〕
- 已經有合約的租客，沒辦法在這裡編輯姓名，也不能被刪除。〔src/pages/users/lesseeList/parts/PageTop.vue〕

### 租客列表裡 Email／手機號碼顯示藍色、橘色、灰色代表什麼？（驗證狀態：已驗證／等待驗證／未驗證）
- 講法：租客通知顏色代表什麼／Email 顯示灰色是什麼意思／手機號碼橘色代表什麼
- 給誰看：property_manager
- 藍色的 Email 或手機號碼代表這個聯絡方式已經被租客驗證過，可以接收合約與帳單通知；橘色代表正在等待租客驗證；灰色代表還沒驗證，沒驗證的 Email 或手機號碼收不到通知。〔src/pages/users/lesseeList/parts/PageTop.vue〕

### 租客的 Email／手機驗證連結多久過期？（72 小時）
- 講法：驗證連結多久過期／驗證信有效期限／簡訊驗證連結會過期嗎
- 給誰看：property_manager
- 驗證通知寄出後，信件或簡訊裡連結的有效時間是 72 小時。〔src/pages/users/lesseeList/parts/PageTop.vue〕

### 租客的通知開關關閉後會怎樣？（收不到任何合約或帳單的通知信件或簡訊）
- 講法：租客通知關閉會怎樣／關掉通知還收得到帳單信嗎／通知開關在哪裡設定
- 給誰看：property_manager
- 如果租客的通知開關被關閉，就不會收到任何合約或帳單的通知信件或簡訊。〔src/pages/users/lesseeList/parts/PageTop.vue〕

### 租客的「準時繳租率」怎麼算？（已到帳未逾期帳單數 ÷ 全部應計入帳單數）
- 講法：準時繳租率公式／繳租率是看哪些帳單／準時繳租率算式
- 給誰看：property_manager
- 租客列表會顯示每位租客的「準時繳租率」，計算方式是：已到帳未逾期帳單數 ÷（應到帳逾期帳單數 ＋ 已到帳未逾期帳單數 ＋ 已到帳逾期帳單數）。〔src/pages/users/lesseeList/parts/ListTable.vue〕

### 租客列表可以看到哪些欄位？（ID、姓名、會員註冊、Email - 通知、手機號碼 - 通知、註冊合約、免註冊合約、所屬修繕、準時繳租率、帳戶名稱、帳號資訊、操作）
- 講法：租客列表有哪些欄位／免註冊合約是什麼／所屬修繕欄位是什麼／帳號資訊欄位是什麼
- 給誰看：property_manager
- 租客列表預設會顯示 ID、姓名、會員註冊、Email - 通知、手機號碼 - 通知、註冊合約、免註冊合約、所屬修繕、準時繳租率、帳戶名稱、帳號資訊、操作這些欄位。〔src/pages/users/lesseeList/parts/ListTable.vue〕
- 「註冊合約」是這位租客名下、對方已註冊 JGB 帳號的合約數量；「免註冊合約」是不用租客先註冊帳號、建檔時就標記為免註冊的合約數量。〔src/pages/users/lesseeList/parts/ListTable.vue〕

### 社宅團隊與特定合作團隊的租客列表欄位有什麼不一樣？（社宅團隊沒有「會員註冊」「免註冊合約」「操作」，「註冊合約」欄改叫「所屬總合約」；特定合作團隊多了國籍、生日、主要聯絡方式）
- 講法：社宅租客列表欄位差在哪／為什麼我看不到國籍欄位／租客列表沒有操作欄
- 給誰看：property_manager
- 社宅團隊的租客列表看不到「會員註冊」「免註冊合約」「操作」這三欄，「註冊合約」欄也會改叫「所屬總合約」。〔src/pages/users/lesseeList/parts/ListTable.vue〕
- 只有特定合作團隊的租客列表才會多出「國籍」「生日」「主要聯絡方式」這三欄，一般團隊與社宅團隊都沒有這幾欄。〔src/pages/users/lesseeList/parts/ListTable.vue〕

### 租客的 Email 或手機還在等待驗證時，帳單會怎樣？（帳單會停留在草稿分頁，等驗證完成或連結過期才能發送，也可以手動移動）
- 講法：帳單卡在草稿分頁怎麼辦／租客沒驗證帳單發不出去／帳單一直沒發送原因
- 給誰看：property_manager
- 為避免租客無法收到帳單通知，若 Email 或手機號碼尚在等待租客驗證，管理者建立帳單時，系統會把帳單停留在草稿帳單分頁中，等租客完成驗證或驗證連結過期後，才能發送帳單。〔src/pages/users/lesseeList/parts/PageTop.vue〕
- 管理者仍然可以手動把這張帳單從草稿移到應到帳或已到帳分頁。〔src/pages/users/lesseeList/parts/PageTop.vue〕

### 租客列表勾選多筆租客後可以做什麼？（統上團隊可以批次發送通知，其他團隊沒有這個批次操作）
- 講法：租客列表勾選後能做什麼／怎麼批次通知租客／租客批次操作在哪
- 給誰看：property_manager
- 只有統上這個合作團隊，在租客列表勾選一筆以上租客後，畫面下方才會出現批次操作列，可以選「發送通知」一次通知這些租客；其他團隊勾選租客後沒有這個批次操作列。〔src/use/config/useLesseeTypes.ts〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/use/config/useLesseeTypes.ts | grep -c 'SpecialRole.tongSang'", 'result': '1 — bulkActions 陣列只有一個条件分支，僅在角色屬於 SpecialRole.tongSang（統上）時才會塞入「發送通知」這個項目，其餘團隊該陣列為空', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/lesseeList/parts/ListTable.vue | grep -c "t(\'封存\')" => 1（正對照組：同檔案的「封存」分頁分頁籤所有團隊都會渲染，不受這個特殊角色判斷限制）'}`

### 匯出租客的入口在哪？（一般房東用「新增租客」下拉選單裡的「匯出租客」；社宅團隊只有一顆「匯出」按鈕，沒有新增或匯入）
- 講法：匯出租客在哪／社宅團隊怎麼匯出租客／為什麼看不到新增租客按鈕
- 給誰看：property_manager
- 一般房東（含法人房東）在租客列表可以點「新增租客」按鈕旁的下拉選單，選「匯入租客」或「匯出租客」。〔src/pages/users/lesseeList/parts/PageTop.vue〕
- 社宅團隊的租客列表沒有「新增租客」與「匯入租客」，只有一顆「匯出」按鈕，功能等同於一般房東的「匯出租客」。〔src/pages/users/lesseeList/parts/PageTop.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 show master:src/pages/users/lesseeList/parts/PageTop.vue | sed -n \'142,144p\' | grep -c "config_rule_key === 4"', 'result': '1 — config_rule_key===4（社宅團隊）的按鈕區塊只有一顆「匯出」按鈕；「新增租客」下拉選單則被包在另一個 (config_rule_key === 2 || config_rule_key === 3) 條件裡，兩段互斥渲染', 'control_term': 'git -C jgb2/dev2 show master:src/pages/users/lesseeList/parts/PageTop.vue | sed -n \'113,115p\' | grep -c "config_rule_key === 2" => 1（正對照組：同檔案「新增租客」按鈕的角色判斷確實命中，證明 grep 找得到這段程式碼）'}`

### 租客列表可以怎麼搜尋篩選、每頁看幾筆？（可依姓名／Email／手機號碼／租客 ID 搜尋，用會員註冊與通知狀態篩選，每頁可選 30／60／90 筆）
- 講法：租客列表怎麼搜尋／可以用租客 ID 搜尋嗎／每頁可以看幾筆租客／租客列表可以篩選通知狀態嗎
- 給誰看：property_manager
- 租客列表的搜尋框可以選擇用姓名、Email、手機號碼、租客 ID 其中一種類型當關鍵字搜尋。〔src/utils/constants/lessee.js〕
- 另外還可以用「會員註冊」（未註冊／已註冊）與「通知狀態」篩選租客；「通知狀態」的選項分成手機與 Email 兩組，各有「接受通知」「不接受通知」「驗證中」「未填寫聯繫方式」四種狀態，共八個選項。〔src/utils/constants/lessee.js〕
- 列表下方可以選擇每頁顯示 30 項、60 項或 90 項。〔src/pages/users/lesseeList/parts/PageNav.vue〕

### 租客列表每一列的操作選單有哪些功能？（建立電子合約、上傳紙本合約、編輯租客、封存租客；封存分頁裡則改成刪除租客）
- 講法：租客列表操作選單在哪／怎麼幫租客建立電子合約／封存分頁的租客要怎麼刪除
- 給誰看：property_manager
- 租客列表每一列右側的操作選單裡，可以選「建立電子合約」「上傳紙本合約」「編輯租客」。〔src/components/SurelyVue/Lessee/ActionCell.vue〕
- 在「當前租客」分頁看到的操作選單最後一項是「封存租客」；切到「封存」分頁後，同一個位置的選項會改成「刪除租客」。〔src/components/SurelyVue/Lessee/ActionCell.vue〕
