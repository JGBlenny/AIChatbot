## A 帳號與身分 {#A}
scope: 註冊、登入、找回帳號、身分（房東／租客／法人／社宅）與個人資料、聯絡方式變更；⛔ 團隊成員權限歸 B
### A-registration 註冊帳號（Email／SSO、驗證碼、手機綁定） {#A-registration}
jgb/A/register-email-steps｜如何註冊 JGB 帳號？（Email、驗證碼、帳號設定三步驟）｜target_user=property_manager,prospect｜怎麼註冊帳號／註冊流程是什麼／第一次用要怎麼開帳號／註冊要填什麼／怎麼申請 JGB 帳號
jgb/A/register-tenant-contract-invitation｜租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「立即註冊」接續完成）｜target_user=property_manager,prospect｜租客電子合約邀請註冊／房東邀請租客簽約怎麼註冊／收到合約邀請信怎麼辦／租客可以不註冊嗎
jgb/A/register-sso｜可以用 Facebook、Google、LINE 註冊嗎？（SSO 仍需完成 Email 綁定）｜target_user=property_manager,prospect｜可以用臉書登入註冊嗎／可以用 Google 帳號註冊嗎／LINE 可以註冊嗎／第三方帳號註冊／SSO 註冊
jgb/A/register-captcha-expired｜註冊卡在機器人驗證過期怎麼辦？（重新勾選「我不是機器人」；寄驗證信時沒通過會退回第一步）｜target_user=property_manager｜機器人驗證過期／我不是機器人卡住／註冊一直失敗
jgb/A/register-email-verify-resend｜沒收到 Email 驗證碼怎麼辦？（可重發，發送次數過多會出現等待秒數）｜target_user=property_manager｜沒收到驗證信／驗證碼重發／驗證信在等待／Email 驗證碼過期
jgb/A/register-password-rule｜註冊密碼格式要求是什麼？（至少 6 碼、須同時包含英文與數字）｜target_user=property_manager,prospect｜密碼規則／密碼要幾碼／密碼格式／設定密碼限制
jgb/A/register-email-already-registered｜註冊時 Email 已被註冊過怎麼辦？（已完成註冊的 Email 會直接被擋下；只有還沒完成 Email 註冊的舊帳號才會進行帳號合併）｜target_user=property_manager｜Email 已經註冊過／帳號合併／重複註冊／曾經用 SSO 註冊過還能再用 Email 註冊嗎
jgb/A/register-phone-bind｜註冊要綁定手機號碼嗎？（可選填、簡訊驗證、可「下次再驗證」略過）｜target_user=property_manager,prospect｜註冊要綁手機嗎／手機驗證怎麼做／可以跳過手機驗證嗎／手機驗證碼收不到
jgb/A/register-phone-already-bound｜註冊時發現手機已綁定過怎麼辦？（直接顯示已綁定、按繼續完成流程）｜target_user=property_manager｜手機已經綁定過／重複綁定手機
jgb/A/register-role-select｜註冊完之後要選身分嗎？（一般會在房東/管理者、租客中二選一，可同時擁有兩種身分）｜target_user=property_manager,prospect｜註冊完要選身分嗎／房東身分和租客身分／怎麼切換房東和租客／我是房東還是租客
jgb/A/register-verify-code-shape｜驗證碼輸入畫面長什麼樣子？（識別碼加 4 碼數字；輸入錯誤太多次驗證碼會失效，需重新發送）｜target_user=property_manager｜驗證碼長什麼樣子／驗證碼輸入錯誤被鎖／驗證碼幾碼
jgb/A/register-email-link-resume｜從信箱 App 點註冊連結、去收驗證碼再回來，會從頭開始註冊嗎？（同一瀏覽器會記住 Email 回到驗證碼步驟；機器人驗證失效時退回第一步）｜target_user=property_manager｜註冊到一半去收信再回來會重來嗎／收信後點回註冊頁／從信箱 App 開註冊連結會重來嗎
### A-login 登入 {#A-login}
jgb/A/login-methods｜JGB 有哪些登入方式？（Email、手機號碼、Facebook／Google／LINE）｜target_user=property_manager,prospect｜怎麼登入／登入方式有哪些／可以用手機登入嗎／SSO 登入
jgb/A/login-role-select-before｜登入前要先選擇身分？｜target_user=property_manager,prospect｜登入頁面在哪／為什麼要選身分才能登入
jgb/A/login-phone-country-code｜用手機號碼登入時，國碼與號碼格式有什麼規則？（號碼長度上限與格式依所選國家而定）｜target_user=property_manager,prospect｜手機登入國碼／手機號碼格式限制／手機登入長度限制
jgb/A/login-remember-me｜「記住我」是做什麼？（只延長登入效期，跟記住登入方式無關）｜target_user=property_manager,prospect｜記住我是什麼
jgb/A/login-role-redirect｜登入時身分選錯了怎麼辦？（會依選擇的身分決定進入哪個角色的登入表單）｜target_user=property_manager｜登入身分選錯／怎麼切換登入身分／房東登入還是租客登入
jgb/A/login-error｜登入帳號或密碼錯誤時會顯示什麼？｜target_user=property_manager｜登入失敗／帳號密碼錯誤／登不進去
jgb/A/login-forget-password-link｜登入頁的「忘記密碼？」連結在哪裡？（在登入表單下方，點擊前往忘記密碼流程）｜target_user=property_manager｜忘記密碼在哪／忘記密碼連結
jgb/A/login-forget-account-link｜登入頁的「忘記帳號？」連結在哪裡？（在登入表單下方，點擊前往忘記帳號流程）｜target_user=property_manager｜忘記帳號在哪／忘記帳號連結
jgb/A/login-no-account-register-link｜登入頁有連到註冊頁的連結嗎？（登入表單上方的「還沒有帳號嗎？立即註冊」）｜target_user=property_manager,prospect｜登入頁怎麼去註冊／還沒帳號怎麼註冊
jgb/A/login-identity-switch｜同一帳號同時有房東與租客身分時怎麼切換？（登入時重新選擇身分，或在帳號資訊設定預設身分）｜target_user=property_manager｜房東租客身分切換／怎麼換身分登入／登入預設身分
### A-account-recovery 忘記帳號、忘記密碼 {#A-account-recovery}
jgb/A/forget-account-flow｜忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示）｜target_user=property_manager｜忘記帳號怎麼辦／忘記 email 帳號／找回帳號
jgb/A/forget-account-no-phone｜沒綁手機號碼還能用「忘記帳號」找回嗎？（不行，只能靠手機簡訊驗證）｜target_user=property_manager｜沒綁手機忘記帳號／沒有手機號碼怎麼找回帳號
jgb/A/forget-password-flow｜忘記密碼怎麼重設？（Email 或手機號碼擇一驗證帳號、輸入驗證碼後設定新密碼，設定完成一般會直接登入）｜target_user=property_manager｜忘記密碼怎麼辦／重設密碼／密碼忘記了／重設密碼後要重新登入嗎
jgb/A/forget-password-setpwd-invite｜「請設定密碼」畫面是什麼情境？（受邀請帳號的初次設定密碼流程）｜target_user=property_manager｜請設定密碼是什麼／被邀請要設密碼／被邀請設定密碼的頁面
### A-member-home 會員中心首頁 {#A-member-home}
jgb/A/dashboard-overview-blocks｜會員中心首頁有哪些統計區塊？（即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單）｜target_user=property_manager｜首頁看得到什麼／會員中心首頁／會員中心首頁有什麼統計資料／登入後的首頁
jgb/A/dashboard-overview-charts｜首頁的圖表看得到什麼？（招租／買賣廣告刊登率圓環圖、收支情況圖）｜target_user=property_manager｜首頁圖表／刊登率圓環圖／收支情況圖表
jgb/A/dashboard-overview-lists｜房東首頁下方還有哪些列表？（帳單與合約整合列表，具查看所有通知權限者另有系統代發送 E-mail 區塊；大房東首頁沒有）｜target_user=property_manager｜首頁下方列表／首頁帳單合約列表／首頁系統代發送E-mail區塊
jgb/A/dashboard-big-landlord-view｜大房東的首頁畫面和一般房東不一樣嗎？（沒有捷徑與四個統計方塊）｜target_user=property_manager｜大房東首頁／大房東看到的畫面／大房東首頁跟一般房東有什麼不同
jgb/A/dashboard-team-switch｜怎麼在會員中心首頁切換團隊？（左上角下拉選單選擇被加入的團隊）｜target_user=property_manager｜怎麼切換團隊／被加入多個團隊／團隊下拉選單在哪
jgb/A/dashboard-occupancy-tab｜首頁的「滿租率(beta)」頁簽是什麼？（限定開放的社區收入統計，非所有團隊都看得到）｜target_user=property_manager｜滿租率 beta／首頁頁簽／社區收入統計
jgb/A/dashboard-shortcuts-list｜首頁「捷徑」區塊有哪些功能？（新增物件、新增合約、新增帳單、新增修繕、查看統計報表、查看大房東列表）｜target_user=property_manager｜捷徑區塊有哪些功能／首頁捷徑按鈕
### A-account-profile 帳號資訊 {#A-account-profile}
jgb/A/account-basic-info｜帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂）｜target_user=property_manager｜帳號基本資訊怎麼改／改姓名／改大頭照／帳號資訊頁面
jgb/A/account-phone-bind-status｜帳號資訊頁怎麼看手機的綁定狀態？（已綁定／未綁定，未綁定才有「前往綁定」按鈕）｜target_user=property_manager｜手機有沒有綁定／手機綁定狀態／前往綁定按鈕
jgb/A/account-email-verify-status｜帳號資訊頁的 Email 驗證狀態怎麼看？（Email 無法自行更改，需聯繫客服）｜target_user=property_manager｜email 驗證狀態／怎麼換 email／更換綁定信箱
jgb/A/account-phone-no-change-entry｜手機已經綁定後可以自己更換嗎？（沒有更換入口，只顯示已綁定狀態）｜target_user=property_manager｜換手機號碼／更換綁定手機／手機已綁定還能改嗎
jgb/A/account-sso-status｜帳號資訊頁怎麼看 SSO 綁定狀態？（Facebook／Google／LINE 各自顯示已綁定或未綁定）｜target_user=property_manager｜sso 綁定狀態／有沒有連 facebook／帳號有沒有連 google
jgb/A/account-change-password｜登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼、新密碼與確認新密碼）｜target_user=property_manager｜登入後怎麼改密碼／帳號資訊改密碼／修改密碼要輸入原密碼嗎
jgb/A/account-contact-info｜帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話）｜target_user=property_manager｜聯絡資訊怎麼填／WhatsApp 要填什麼／line id 要填嗎／第二組電話欄位有什麼限制
jgb/A/account-preference｜帳號資訊頁的偏好設定能設定什麼？（登入預設房東身份、時區、Email 通知語系）｜target_user=property_manager｜登入預設身份怎麼設／時區設定在哪／Email 通知語言
jgb/A/account-progress-unlock｜帳號資訊頁有「資訊完整度」進度條嗎？（目前頁面上不會顯示這個區塊）｜target_user=property_manager,prospect｜資訊完整度是什麼／為什麼不能刊登廣告／為什麼不能簽約
jgb/A/account-save-integrity-check｜帳號資訊頁儲存失敗會提示什麼？（頁面沒有完整載入時會提醒重新整理再儲存）｜target_user=property_manager｜儲存失敗提示／帳號資訊存不進去
jgb/A/account-change-password-rules｜在帳號資訊頁改密碼，新密碼有什麼規則？（至少 6 個字元、需與確認新密碼一致；英數混合在這裡只是提示）｜target_user=property_manager｜改密碼有什麼限制／改密碼一定要英文加數字嗎／帳號資訊頁新密碼規則
### A-signer-info 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章） {#A-signer-info}
jgb/A/signer-individual-fields｜個人房東的簽約資訊要填哪些欄位？（姓氏、名稱、身分證字號、Email、手機號碼、戶籍地址、通訊地址標示必填，身分證正反面照片與其他附件為選填）｜target_user=property_manager,prospect｜個人房東簽約資訊／簽約要填身分證嗎／簽約資訊個人欄位
jgb/A/signer-corp-fields｜公司身分的簽約資訊要填什麼？（公司名稱、統編、負責人、公司電話/Email、登記證資料）｜target_user=property_manager,prospect｜公司簽約資訊／統編怎麼填／公司負責人要填嗎
jgb/A/signer-corp-seals｜公司身分可以上傳哪些印章與證件附件？（公司大章、小章、經紀人章、經紀業章、租賃管理員章，皆為選填）｜target_user=property_manager,prospect｜公司大小章上傳／經紀人章要傳嗎／簽約印章附件
jgb/A/signer-broker-manager-fields｜有不動產經紀人／租賃管理人員資格要多填什麼？（經紀人證號、租賃管理人員證號等）｜target_user=property_manager,prospect｜經紀人證號要填嗎／租賃管理人員資訊／經紀業名稱
jgb/A/signer-edit-permission｜簽約資訊誰能編輯？（沒有編輯權限的欄位會顯示為停用樣式）｜target_user=property_manager｜誰能改簽約資訊／沒有編輯權限會怎樣／簽約資訊唯讀
jgb/A/signer-address-fields｜簽約資訊的地址欄位怎麼填？（戶籍/通訊地址、公司登記/通訊地址皆為必填，可一鍵「同戶籍地址」「同公司登記地址」）｜target_user=property_manager,prospect｜戶籍地址要填嗎／通訊地址可以跟戶籍一樣嗎／公司登記地址
jgb/A/signer-multi-entry-switch｜公司名下有多筆簽約對象時要怎麼切換？（表單上方出現切換列，超過 5 筆再加「所有團隊」下拉選單）｜target_user=property_manager｜公司多筆簽約對象切換／多個公司要怎麼切換
jgb/A/signer-manage-save-buttons｜簽約資訊頁的「管理」「儲存」按鈕做什麼？（管理開啟簽約對象視窗可新增或刪除，儲存只在個人身分頁面出現）｜target_user=property_manager｜簽約資訊管理按鈕／簽約資訊儲存按鈕
### A-notification-center 通知中心 {#A-notification-center}
jgb/A/notification-center-type-filter｜通知中心怎麼依類型篩選通知？（依合約/帳務/修繕/裝置/其他分類）｜target_user=property_manager｜通知中心怎麼篩選／通知中心的通知類型有哪些／怎麼看合約類通知
jgb/A/notification-center-unread-dot｜通知中心的通知怎麼標示未讀？（列表項目左側的紅點，沒有「只顯示未讀」的篩選功能）｜target_user=property_manager｜只看未讀通知／通知未讀紅點
jgb/A/notification-center-per-page｜通知中心每頁顯示筆數可以怎麼調整？（30/60/90 筆，預設 30 筆）｜target_user=property_manager｜通知每頁幾筆／通知中心分頁
jgb/A/notification-center-permission｜為什麼通知中心是空的？（房東側需要查看通知的權限才看得到通知內容）｜target_user=property_manager｜通知中心是空的／為什麼看不到通知／通知權限
jgb/A/notification-mark-read-navigate｜點擊通知列表項目會發生什麼？（前往原連結；訊息類通知不換頁）｜target_user=property_manager｜點通知會怎樣／通知會標記已讀嗎／通知連結
jgb/A/notification-mark-read-out-of-range｜篩選後頁碼超出範圍會自動跳回第一頁嗎？（不會，只會顯示空的通知清單）｜target_user=property_manager｜通知頁碼超出範圍／篩選後跳到空白頁
jgb/A/notification-navbar-bell｜導覽列的通知鈴鐺會顯示什麼？（最近 5 筆通知與未點擊數量，大房東不會顯示）｜target_user=property_manager｜導覽列通知鈴鐺／鈴鐺數字是什麼／紅點跟鈴鐺數字差別
### A-notification-settings 通知收件設定與發送報表（通知收件信箱最多再加 3 組） {#A-notification-settings}
jgb/A/notification-settings-extra-emails｜通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱）｜target_user=property_manager｜通知收件信箱最多幾組／怎麼加通知信箱／額外通知信箱
jgb/A/notification-settings-categories｜通知收件設定有哪些分類？（合約、帳務、修繕、訂閱、房東管理，另有限定開放的加盟分潤報表）｜target_user=property_manager｜通知收件設定的分類有哪些／帳務通知包含什麼／訂閱通知是什麼
jgb/A/notification-settings-report-buttons｜「發送報表」「多團隊合併報表」按鈕是做什麼的？（選起始日與終止日，把加盟分潤報表寄到自訂通知信箱；僅限加盟分潤報表分類，多團隊合併僅限特定團隊）｜target_user=property_manager｜發送報表按鈕／多團隊合併報表／分潤報表怎麼看
jgb/A/notification-settings-save｜通知收件設定改完怎麼儲存？｜target_user=property_manager｜通知設定怎麼存／儲存按鈕按不下去／沒填信箱能存嗎

## B 團隊、人員與大房東 {#B}
scope: 團隊建立與成員邀請、角色權限、人員管理、大房東記錄與代管關係；⛔ 帳號本身歸 A
### B-team-profile 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊） {#B-team-profile}
jgb/B/team-basic-info｜團隊資訊頁面可以設定什麼？（公司 Logo、團隊名稱、團隊介紹）｜target_user=property_manager,prospect｜團隊資訊在哪裡設定／團隊名稱怎麼改／團隊介紹要寫什麼／團隊首頁的介紹文字在哪改／公司 Logo 怎麼上傳
jgb/B/team-ad-contact｜廣告頁聯絡資訊要填什麼？（Line ID、Facebook、WhatsApp 選填，公司電話與公司 Email 必填）｜target_user=property_manager,prospect｜廣告頁聯絡資訊要填什麼／公司電話一定要填嗎／WhatsApp 怎麼填／廣告聯絡方式在哪設定
jgb/B/team-delete｜怎麼刪除團隊？（需先解除訂閱方案、輸入團隊名稱確認、刪除後資料無法恢復）｜target_user=property_manager｜怎麼刪除團隊／刪除團隊會怎樣／刪除團隊的條件／團隊解散流程
jgb/B/team-signer-personal-info｜簽約資訊卡「個人資訊」區塊要填什麼？（只有租客與個人房東身分才有；姓氏、名稱、身分證字號、Email、手機、戶籍地址、通訊地址必填；身分證正反面與其他附件選填）｜target_user=property_manager｜簽約資訊個人欄位有哪些／身分證正反面要傳嗎／良民證要上傳嗎／戶籍地址跟通訊地址一樣可以嗎
jgb/B/team-signer-company-info｜簽約資訊卡的「公司資訊」要填什麼？（公司登記名稱上限 20 字、公司統編皆為必填；公司負責人只有社宅團隊必填；社宅團隊還要填必填的社宅業者編號與公司登記證號）｜target_user=property_manager｜公司登記名稱字數上限／社宅業者編號在哪填／公司登記證號要填嗎／公司統編格式錯誤怎麼辦
jgb/B/team-signer-agent-info｜簽約資訊卡的「經紀人資訊」要填什麼？（經紀人／經紀業名稱與證號，名稱上限 15 字；社宅團隊多了經紀人聯絡電話與 Email，且都是必填）｜target_user=property_manager｜經紀人名稱字數上限／經紀業名稱可以不填嗎／經紀人聯絡電話什麼時候要填
jgb/B/team-signer-manager-info｜簽約資訊卡的「租賃住宅管理人員資訊」要填什麼？（姓名與證號；社宅團隊多了聯絡電話欄位，且姓名／證號／電話都是必填；沒有 Email 欄位）｜target_user=property_manager｜租賃管理人員要填哪些資料／租賃管理人員聯絡電話要填嗎／租賃住宅管理人員證號在哪填
jgb/B/team-signer-stamps｜簽約資訊卡可以上傳哪幾種圖章？（法人或社宅團隊的簽約資訊卡才看得到「附件」與「電子簽約圖章」兩個區塊；「附件」有公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章五種，「電子簽約圖章」另外只有一個「圖章」欄位）｜target_user=property_manager｜圖章要上傳哪幾種／電子簽約圖章是什麼／公司大章小章差在哪
jgb/B/team-multi-company-info｜一個團隊可以管理多組公司資訊嗎？（可以在「團隊資訊管理」視窗新增與刪除，但清單第一筆不能刪除）｜target_user=property_manager｜可以設定多組公司資訊嗎／公司資訊怎麼新增／主要那組公司資訊可以刪除嗎
jgb/B/team-info-no-view-permission｜沒有查看團隊資訊的權限，打開團隊資訊頁會怎樣？（提示「您目前登入的帳號無法查看團隊資訊功能」）｜target_user=property_manager｜沒有權限看團隊資訊會怎樣／團隊資訊頁打不開／無法查看團隊資訊功能是什麼意思
jgb/B/team-signer-address-groups｜簽約資訊卡上有哪些地址欄位群？（個人的戶籍地址／通訊地址、公司的登記地址／通訊地址；社宅團隊另有經紀人與租賃管理人員各自的通訊地址）｜target_user=property_manager｜簽約資訊有哪些地址欄位／通訊地址可以跟戶籍地址一樣嗎／公司通訊地址在哪填
jgb/B/team-signer-profile-switch｜怎麼在多組簽約資訊之間切換？（頁面上方有可切換的分頁列，超過 5 組時另外多出「所有團隊」下拉選單）｜target_user=property_manager｜怎麼切換不同的簽約資訊／簽約資訊太多組要怎麼選／所有團隊下拉選單是什麼
### B-member-list 成員列表（邀請、角色、成員名下資料） {#B-member-list}
jgb/B/member-list-overview｜成員列表可以看到什麼資訊？（加入時間、Email、手機號碼、目前的角色）｜target_user=property_manager｜成員列表看得到什麼／成員清單有哪些欄位／怎麼看成員的角色／成員名下有沒有物件怎麼看
jgb/B/member-invite｜怎麼邀請新成員加入團隊？（用 Email 或手機號碼搜尋，對方要先是 JGB 會員）｜target_user=property_manager｜怎麼邀請成員／新增成員流程／邀請成員要對方先註冊嗎／成員邀請用 email 還是手機
jgb/B/member-role-concept｜成員的「角色」權限決定什麼？（決定看得到與能編輯的物件、合約、帳務、修繕等範圍）｜target_user=property_manager,prospect｜角色權限是什麼／角色能設定哪些權限／團隊擁有者的權限跟一般成員一樣嗎／成員權限範圍怎麼分
jgb/B/member-role-manage｜怎麼管理團隊的角色範本？（可新增、編輯、刪除，也能套用 JGB 內建的快速設定範本）｜target_user=property_manager｜角色管理在哪／怎麼新增角色／角色範本有哪些／刪除角色會怎樣
jgb/B/member-remove｜怎麼移除成員？（列表右側的紅色 × 圖示開啟確認視窗，按「移除」才會真的刪除；名下還有物件或合約會被擋下）｜target_user=property_manager｜怎麼移除成員／成員名下有物件不能刪怎麼辦／移除成員後果／成員擁有的物件怎麼轉移給別人
jgb/B/member-seat-limit｜邀請成員有名額上限嗎？（依訂閱方案而定；已訂閱達上限要升級方案，未訂閱要先訂閱）｜target_user=property_manager,prospect｜成員邀請有上限嗎／團隊成員人數上限／邀請額滿怎麼辦
jgb/B/member-assign-owned｜怎麼指派物件或合約給成員？（點成員旁的鉛筆圖示選「編輯綁定物件」或「編輯綁定合約」）｜target_user=property_manager｜怎麼指派物件給成員／編輯綁定合約在哪／成員名下物件怎麼調整
jgb/B/member-role-permission-list｜怎麼查看每個角色能做什麼？（點「角色權限說明」的「這裡」開啟角色權限列表，每一列是一項權限、每一欄是一個角色，用勾號／叉號表示有沒有這項權限）｜target_user=property_manager｜角色權限列表在哪看／角色權限說明在哪／目前團隊還沒有角色怎麼辦
jgb/B/member-list-role-inline-change｜成員列表可以直接改成員的角色嗎？（一般成員那一列可以用角色下拉選單直接切換；擁有者與自己那一列、或沒有編輯權限時選單會鎖住）｜target_user=property_manager｜列表上怎麼改成員角色／角色下拉選單怎麼用／新增角色的入口在哪裡
jgb/B/member-role-edit-open-condition｜編輯角色時的「開啟條件」是什麼？（要先勾選列出的其他權限，這個權限選項的勾選框才能點；沒先勾好之前，勾選框會維持鎖住）｜target_user=property_manager｜為什麼有些權限打不開／開啟條件是什麼意思／角色編輯畫面權限勾不起來
jgb/B/member-role-edit-reset｜編輯角色時的「重設條件」按鈕是做什麼的？（把所有權限勾選全部清空）｜target_user=property_manager｜重設條件按鈕做什麼／角色編輯畫面的重設是什麼意思／重設條件會清掉哪些勾選
jgb/B/member-list-sort｜成員列表可以怎麼排序？（姓名、加入時間、手機號碼、Email、角色名稱各有正反兩種排序）｜target_user=property_manager｜成員列表怎麼排序／可以依加入時間排序嗎／成員排序有哪些選項
jgb/B/member-list-role-select-disabled｜為什麼「團隊擁有者」和自己那一列的角色下拉不能改？（這兩列是固定顯示在列表最上面、角色下拉是鎖住的，跟其他成員分開處理）｜target_user=property_manager｜團隊擁有者角色不能改嗎／自己的角色下拉是灰的／為什麼有一列選不了角色
### B-biglandlord-list 大房東列表與授權物件 {#B-biglandlord-list}
jgb/B/biglandlord-list-overview｜大房東列表有哪些欄位？（ID、姓名、會員註冊、Email、手機號碼、身分證字號、地址、帳戶名稱、帳戶資訊、合作方式、合作起迄、所屬物件、生日、主要聯絡方式，其中生日與主要聯絡方式目前每筆都顯示「-」）｜target_user=property_manager｜大房東列表有哪些欄位／大房東資料看得到什麼／大房東的合作起迄怎麼看
jgb/B/biglandlord-add｜怎麼新增大房東？（已註冊會員填 Email 即可，未註冊只要填姓氏與名稱，Email 選填）｜target_user=property_manager｜怎麼新增大房東／大房東還沒註冊怎麼辦／新增大房東要填什麼
jgb/B/biglandlord-authorize-estates｜大房東的「授權物件」怎麼設定？（逐筆物件勾選瀏覽廣告／合約／帳務／修繕；合約要先勾廣告，帳務要先勾廣告＋合約，修繕沒有前提）｜target_user=property_manager｜大房東能看到哪些資料／怎麼授權物件給大房東／大房東權限怎麼設定／移除大房東的物件授權
jgb/B/biglandlord-import-export｜大房東名單可以批次匯入或匯出嗎？（可以，Excel 匯入新增、Excel 匯出下載）｜target_user=property_manager,prospect｜大房東可以批次匯入嗎／大房東資料怎麼匯出／大房東 excel 匯入匯出在哪
jgb/B/biglandlord-actions-menu｜大房東列表每一列的操作選單有哪些功能？（編輯所屬物件、編輯大房東、刪除大房東）｜target_user=property_manager｜怎麼刪除大房東／移除大房東流程／大房東資料怎麼編輯
jgb/B/biglandlord-authorize-apply-step｜授權物件頁移除物件後，為什麼要按「套用」才會生效？（按紅色 X 移除只是待處理狀態，按套用才真的移除，按恢復可以取消這次變更）｜target_user=property_manager｜授權物件移除後沒反應／套用按鈕是做什麼的／移除物件可以復原嗎
jgb/B/biglandlord-delete-confirm｜刪除大房東會發生什麼？（先跳出確認視窗，確認後這位大房東就無法再存取這個團隊的任何資訊）｜target_user=property_manager｜刪除大房東會怎樣／大房東刪除確認視窗／刪除大房東後對方還能登入嗎
jgb/B/biglandlord-seat-limit｜大房東名額有上限嗎？（目前大房東列表頁的「新增大房東」沒有名額檢查）｜target_user=property_manager,prospect｜大房東可以新增幾位／大房東名額上限
jgb/B/biglandlord-list-empty｜大房東列表沒有資料時會顯示什麼？（一開始沒有任何大房東顯示「尚無大房東」；用關鍵字搜尋卻沒有符合結果則顯示「沒有符合的結果😢」）｜target_user=property_manager｜大房東列表是空的／還沒有大房東畫面長怎樣／搜尋不到大房東會顯示什麼
jgb/B/biglandlord-batch-template-fields｜批次匯入大房東的 Excel 範本要填哪些欄位？（姓氏、名稱必填，其餘含 Email、手機、身分證字號、地址、帳戶資訊、合作方式與合作起迄都是選填）｜target_user=property_manager｜大房東匯入範本欄位／批次新增大房東要填什麼／大房東匯入哪些欄位必填
jgb/B/biglandlord-list-sort｜大房東列表可以用什麼排序？（姓名、手機號碼、Email、身分證字號，各有正序與反序共 8 種排序方式）｜target_user=property_manager｜大房東列表怎麼排序／可以用身分證字號排序嗎／大房東列表排序選項有哪些
### B-biglandlord-report 大房東報表 {#B-biglandlord-report}
jgb/B/biglandlord-report-overview｜大房東報表可以看到什麼？（依大房東列出所屬物件、出租中物件與執行中合約租金總額）｜target_user=property_manager｜大房東報表看得到什麼／大房東報表怎麼看／大房東的物件租金總額在哪查／大房東報表可以下載嗎
jgb/B/biglandlord-report-permission｜誰看得到大房東報表？（法人房東與社宅團隊身分，且角色要有「查看大房東報表」權限）｜target_user=property_manager｜大房東報表誰能看／查看大房東報表權限／為什麼看不到大房東報表
jgb/B/biglandlord-report-community-rate｜大房東報表可以依社區細看嗎？（報表清單有「社區」欄）｜target_user=property_manager｜大房東報表有社區欄嗎／大房東報表匯率在哪看／報表可以下載社區層級嗎
### B-biglandlord-sheet 大房東對帳表 {#B-biglandlord-sheet}
jgb/B/biglandlord-sheet-overview｜大房東對帳表在算什麼？（依年度列出屋主的收入與支出，年度表每月一欄；一般團隊是屋主租金收入與支出，特定合作團隊的資金版報表另有押金、屋主提領、屋主直收等區塊）｜target_user=property_manager｜大房東對帳表看什麼／對帳表怎麼看押金收支／對帳表在算什麼／對帳表的總結餘怎麼算
jgb/B/biglandlord-sheet-empty｜對帳表顯示「尚未被指派物件」是什麼意思？（這位大房東還沒被授權任何物件）｜target_user=property_manager｜對帳表沒資料怎麼辦／大房東報表空白原因／大房東還沒授權物件會怎樣
jgb/B/biglandlord-sheet-multi-currency｜對帳表出現「本月含多幣別帳單」提示是什麼意思？（該月的帳單有不同幣別，已用結算幣別加總）｜target_user=property_manager｜對帳表多幣別提示是什麼／為什麼金額有換算過的字樣／多幣別合計怎麼算
jgb/B/biglandlord-sheet-hide-empty-rows｜對帳表可以隱藏沒有金額的項目嗎？（可以開關「隱藏空值項目」）｜target_user=property_manager｜對帳表可以只看有金額的項目嗎／隱藏空值項目是什麼／對帳表列太多怎麼精簡
jgb/B/biglandlord-sheet-month-drilldown｜對帳表怎麼從年表切到單一月份的月報？（點表頭的月份會進入該月月報，點「取消」回到年表）｜target_user=property_manager｜對帳表年表怎麼看單月明細／月報怎麼回到年表／點月份沒反應
jgb/B/biglandlord-sheet-load-download-fail｜對帳表載入或下載失敗會怎樣？（載入失敗會顯示錯誤並提供「重試」，下載失敗只顯示錯誤訊息）｜target_user=property_manager｜對帳表載入失敗怎麼辦／報表下載失敗怎麼辦／對帳表重試按鈕在哪
jgb/B/biglandlord-sheet-aside-and-loading｜大房東對帳表頁面的側邊選單和載入畫面長怎樣？（左側有社區／物件選單，看單一物件報表時會顯示上次匯入時間，報表產生中會顯示載入百分比進度條）｜target_user=property_manager｜對帳表左邊選單是什麼／上次匯入時間在哪看／對帳表載入畫面在跑什麼
### B-advanced-settings 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」） {#B-advanced-settings}
jgb/B/advance-fee-items｜「帳單自訂費用項目」怎麼設定？（分收入類／支出類，必填性質與自定義名稱，會科品項代號選填）｜target_user=property_manager｜費用項目怎麼設定／自訂費用分收入支出類嗎／帳單費用項目性質怎麼選
jgb/B/advance-discount-items｜進階設定的「優惠項目」是給誰用的？（只有部分特定合作團隊才看得到，可設定折扣套用在租金費用上）｜target_user=property_manager,prospect｜進階設定有租金折扣嗎／優惠項目怎麼設定
jgb/B/advance-late-fee｜進階設定的「延遲金設置」是什麼、延遲金怎麼算？（只有特定合作團隊看得到；合約建立時帶入團隊設定，租金帳單逾期付款後才產生延遲金帳單，金額＝租金 ×（逾期天數 − 緩衝天數）× 延遲金百分比）｜target_user=property_manager,prospect｜進階設定有滯納金設定嗎／延遲金怎麼算／逾期繳費會產生什麼費用／延遲金設置在哪
jgb/B/advance-additional-terms｜「預設補充條款」怎麼設定？（最多可以設 3 組，編輯合約時直接選用）｜target_user=property_manager,prospect｜補充條款範本怎麼設定／合約補充條款可以存幾組／預設條款在哪編輯
jgb/B/advance-custom-label｜「標籤設定」是做什麼用的？（幫物件加自訂標籤，單個標籤輸入框最多收 9 個字元）｜target_user=property_manager,prospect｜自訂標籤怎麼設定／標籤字數上限是多少／物件標籤在哪加
jgb/B/advance-device-binding｜怎麼綁定智能裝置廠商？（輸入裝置廠商帳號密碼完成綁定，之後可在 JGB 平台管理裝置）｜target_user=property_manager｜智能裝置怎麼綁定／裝置管理在哪設定／裝置廠商綁定流程
jgb/B/advance-fee-items-merge｜自訂費用項目可以合併嗎？（可以把多個品項併入其中一個既有品項，合併後無法回復）｜target_user=property_manager｜怎麼合併費用項目／合併品項後可以回復嗎／自訂費用項目合併操作
jgb/B/advance-payment-cycle-discount｜進階設定的「繳費週期優惠」是給誰用的？（只有特定合作團隊才看得到，選比月繳更長的繳費週期就有折扣）｜target_user=property_manager,prospect｜選季繳有折扣嗎／誰看得到繳費週期優惠設定
jgb/B/advance-notification-locale｜「Email 通知語系」在哪設定、誰看得到？（只有法人房東或社宅團隊看得到，決定代發通知信的預設語系）｜target_user=property_manager,prospect｜Email 通知語系怎麼設定／個人房東有語系設定嗎／租客收到的通知信語言怎麼決定
jgb/B/advance-timezone｜「時區設定」會影響哪些通知？（只有法人房東或社宅團隊看得到，改變排程通知的發送時間）｜target_user=property_manager,prospect｜個人房東有時區設定嗎／改時區會影響什麼通知
jgb/B/advance-settlement-currency｜「結算幣別」是做什麼用的？（只有法人房東或社宅團隊看得到，把大房東報表的多幣別合約統一結算成一種幣別）｜target_user=property_manager,prospect｜結算幣別是什麼／多幣別報表怎麼算／結算幣別在哪設定
jgb/B/advance-device-binding-visibility｜為什麼進階設定看不到「裝置管理」區塊？（訂閱方案要生效中，且不能是免費方案）｜target_user=property_manager｜裝置管理不見了／免費方案可以綁裝置嗎／為什麼進階設定沒有裝置管理
jgb/B/advance-dedicated-account｜「房東專屬帳號」是做什麼用的？（只有法人房東或社宅團隊看得到；顯示在團隊首頁，且第一次儲存後不能自行修改，要洽 JGB 客服）｜target_user=property_manager,prospect｜房東專屬帳號是什麼／房東專屬帳號可以改嗎／房東專屬帳號在哪設定
jgb/B/advance-auto-publish-unpublish｜招租廣告可以自動刊登或自動下架嗎？（部分特定合作團隊可以：合約到期日前 N 天自動刊登，簽約後自動下架）｜target_user=property_manager,prospect｜招租廣告會自動上架嗎／簽約後廣告會自動下架嗎／自動刊登天數怎麼設定
jgb/B/advance-contract-label｜「合約管理」的標籤設定跟物件的標籤設定是同一個嗎？（不是，這是合約專用的另一組標籤）｜target_user=property_manager｜合約可以加標籤嗎／合約標籤在哪設定／合約標籤跟物件標籤一樣嗎
jgb/B/advance-sales-item-code｜「銷貨單品項代號對應」是做什麼用的？（只有特定團隊才有，設定匯出「M 化銷貨單」時每個品項要帶的產品代號）｜target_user=property_manager｜銷貨單品項代號對應是什麼／匯出銷貨單產品代號空白／哪些團隊有銷貨單品項代號設定
jgb/B/advance-community-labels｜「社區管理」的城市／區域／位置設定是做什麼？（只有特定合作團隊看得到，用來建立社區可選用的城市、區域、位置標籤）｜target_user=property_manager｜城市設定在哪／區域設定是什麼／位置設定跟標籤設定差在哪／誰看得到社區管理設定
jgb/B/advance-short-lease-approval｜進階設定的「短租期核可流程」是做什麼的？（只有特定合作團隊看得到；租期少於設定天數時，合約要先簽核通過才會發出邀請給租客）｜target_user=property_manager,prospect｜短租期核可流程是什麼／短租期簽核怎麼設定／租期太短要簽核嗎
### B-tenant-list 租客列表（當前租客／封存、準時繳租率、信用評價） {#B-tenant-list}
jgb/B/lessee-tabs｜租客列表有哪兩個分頁？（當前租客／封存，封存代表這位租客已被移出列表且目前沒有進行中的合約）｜target_user=property_manager,prospect｜租客列表分幾種／準時繳租率怎麼算／封存的租客是什麼
jgb/B/lessee-credit-rating-visibility｜租客列表的「信用評價」欄位為什麼有些人看不到？（需要有查看租客信用評價的權限才會顯示這一欄）｜target_user=property_manager｜信用評價欄位不見了／為什麼看不到信用評價／租客信用評價需要什麼權限
jgb/B/lessee-crud｜租客列表可以新增、匯入、匯出租客嗎？（個人房東與法人房東可以手動新增、Excel 匯入與匯出；社宅團隊只能匯出）｜target_user=property_manager,prospect｜租客列表可以新增租客嗎／租客資料怎麼匯入匯出／已簽約的租客可以改名字嗎
jgb/B/lessee-notification-status-color｜租客列表裡 Email／手機號碼顯示藍色、橘色、灰色代表什麼？（驗證狀態：已驗證／等待驗證／未驗證）｜target_user=property_manager｜租客通知顏色代表什麼／Email 顯示灰色是什麼意思／手機號碼橘色代表什麼
jgb/B/lessee-verification-link-expiry｜租客的 Email／手機驗證連結多久過期？（72 小時）｜target_user=property_manager｜驗證連結多久過期／驗證信有效期限／簡訊驗證連結會過期嗎
jgb/B/lessee-notification-toggle-effect｜租客的通知開關關閉後會怎樣？（Email 與手機的開關分開，關掉哪一個就停哪一種通知）｜target_user=property_manager｜租客通知關閉會怎樣／關掉通知還收得到帳單信嗎／通知開關在哪裡設定
jgb/B/lessee-on-time-pay-rate｜租客的「準時繳租率」怎麼算？（已到帳未逾期帳單數 ÷ 全部應計入帳單數）｜target_user=property_manager｜準時繳租率公式／繳租率是看哪些帳單／準時繳租率算式
jgb/B/lessee-list-columns｜租客列表可以看到哪些欄位？（ID、姓名、會員註冊、Email - 通知、手機號碼 - 通知、註冊合約、免註冊合約、所屬修繕、準時繳租率、帳戶名稱、帳號資訊、操作）｜target_user=property_manager｜租客列表有哪些欄位／免註冊合約是什麼／所屬修繕欄位是什麼／帳號資訊欄位是什麼
jgb/B/lessee-list-columns-by-role｜社宅團隊的租客列表欄位有什麼不一樣？（沒有「會員註冊」「免註冊合約」與操作選單，「註冊合約」欄改叫「所屬總合約」）｜target_user=property_manager｜社宅租客列表欄位差在哪／租客列表沒有操作欄
jgb/B/lessee-pending-verification-bill-draft｜租客的 Email 或手機還在等待驗證時，帳單會怎樣？（帳單會停留在草稿分頁，等驗證完成或連結過期才能發送，也可以手動移動）｜target_user=property_manager｜帳單卡在草稿分頁怎麼辦／帳單一直沒發送原因
jgb/B/lessee-bulk-notify｜租客列表勾選多筆租客後可以做什麼？（特定合作團隊可以批次發送通知，其他團隊沒有這個批次操作）｜target_user=property_manager｜租客列表勾選後能做什麼／怎麼批次通知租客／租客批次操作在哪
jgb/B/lessee-export-entry-by-role｜匯出租客的入口在哪？（一般房東用「新增租客」下拉選單裡的「匯出租客」；社宅團隊只有一顆「匯出」按鈕，沒有新增或匯入）｜target_user=property_manager｜匯出租客在哪／社宅團隊怎麼匯出租客／為什麼看不到新增租客按鈕
jgb/B/lessee-list-search-and-pagination｜租客列表可以怎麼搜尋篩選、每頁看幾筆？（可依姓名／Email／手機號碼／租客 ID 搜尋，用會員註冊與通知狀態篩選，每頁可選 30／60／90 筆）｜target_user=property_manager｜租客列表怎麼搜尋／可以用租客 ID 搜尋嗎／每頁可以看幾筆租客／租客列表可以篩選通知狀態嗎
jgb/B/lessee-action-menu｜租客列表每一列的操作選單有哪些功能？（建立電子合約、上傳紙本合約、編輯租客、封存租客；封存分頁裡則改成刪除租客）｜target_user=property_manager｜租客列表操作選單在哪／怎麼幫租客建立電子合約／封存分頁的租客要怎麼刪除

## C 社區與物件 {#C}
scope: 社區建檔、物件新增與批次匯入、刊登與銷售、物件狀態與欄位；⛔ 物件上的租約歸 D、抄表歸 E
### C-community-list 社區列表與建立 {#C-community-list}
jgb/C/community-list-overview-stats｜社區總表顯示什麼資訊？（物件總數、招租／買賣廣告數、空置數量、本月應收與已收）｜target_user=property_manager｜社區總表看得到什麼／社區列表顯示哪些數字／空置數量怎麼算／每個社區的招租買賣數量在哪看
jgb/C/community-add-single-and-limit｜如何新增社區？（訂閱方案有可建立社區數量上限）｜target_user=property_manager｜怎麼新增社區／社區數量有上限嗎／新增社區按鈕在哪
jgb/C/community-batch-add-and-copy｜怎麼批次新增社區、或複製現有社區建立新社區？｜target_user=property_manager｜批次新增社區怎麼做／社區可以用 Excel 匯入嗎／複製現有社區／有沒有現成社區範本可以複製
jgb/C/community-list-filter-sort｜社區總表怎麼搜尋與排序？（案名／地址關鍵字、縣市行政區、建物類型、捷運站）｜target_user=property_manager｜社區怎麼搜尋／社區列表篩選條件有哪些／怎麼依地區找社區／社區排序方式
jgb/C/community-delete-requires-empty｜社區可以刪除嗎？（社區底下不能有任何物件才能刪除，且刪除後無法復原）｜target_user=property_manager｜社區怎麼刪除／社區可以刪除嗎／刪不掉社區怎麼辦／刪除社區的限制
jgb/C/community-export-list｜社區總表可以匯出嗎？（需要匯出物件權限，會依目前篩選條件匯出）｜target_user=property_manager｜社區怎麼匯出／社區清單匯出功能／匯出社區要什麼權限
jgb/C/community-list-pagination｜社區總表每頁筆數可以調整嗎？（30／60／90項）｜target_user=property_manager｜社區總表每頁顯示幾筆／社區列表分頁筆數／怎麼調整每頁顯示社區數
jgb/C/community-list-add-permission｜誰看得到新增社區的入口？（總表右上角需要編輯物件權限；空狀態的批次新增／新增社區入口需要新增物件權限）｜target_user=property_manager｜新增社區按鈕不見了／誰可以新增社區／沒有編輯物件的權限看不到新增社區
jgb/C/community-pick-next-step｜社區選擇畫面選好社區之後會發生什麼？（複製社區直接建立副本並進入編輯；新增物件直接建立物件並進入編輯；複製物件接著挑選物件）｜target_user=property_manager｜選完社區之後會怎樣／複製社區之後會跳到哪裡／社區選擇畫面怎麼用
### C-community-edit 社區資料編輯（基本資料、照片與描述、介紹與交通） {#C-community-edit}
jgb/C/community-edit-tabs｜社區編輯有哪些分頁？（基本資料、介紹與交通、照片與描述）｜target_user=property_manager｜社區編輯有哪些分頁／社區資料要編輯哪些項目／編輯社區從哪裡進去
jgb/C/community-edit-basic-fields｜社區基本資料要填什麼？（社區名稱、詳細地址與對外顯示地址、建築類型、總樓層、屋齡）｜target_user=property_manager｜社區基本資料要填什麼／社區名稱字數限制／對外顯示地址跟詳細地址差在哪
jgb/C/community-edit-gallery-photo-limit｜社區照片與描述可以上傳幾張圖片？（限1張，JPG/PNG，檔案大小最大10MB）｜target_user=property_manager｜社區照片上限幾張／社區封面圖怎麼傳／社區圖片格式限制
jgb/C/community-edit-gallery-save-notice｜社區照片與描述什麼時候會跳出「已更新」提示？（存檔成功後才出現，不是上傳當下）｜target_user=property_manager｜社區照片上傳成功提示在哪／社區資料存檔提示／上傳照片後畫面沒反應正常嗎
jgb/C/community-edit-intros-and-transit｜社區介紹與交通怎麼填？（社區簡介、鄰近交通說明、可加多個鄰近捷運站）｜target_user=property_manager｜社區介紹要寫什麼／怎麼加捷運站／社區交通資訊在哪填
jgb/C/community-edit-basic-required-field｜社區基本資料哪個欄位是必填？（只有社區名稱是必填）｜target_user=property_manager｜社區哪些欄位一定要填／社區名稱一定要填嗎／社區地址是必填嗎
### C-community-estates 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） {#C-community-estates}
jgb/C/community-estates-overview-card｜社區底下物件頁最上方顯示什麼？（招租廣告、買賣廣告、目前空置數量、類型、屋齡、本月應收與已收金額）｜target_user=property_manager｜社區物件頁上面的卡片是什麼／社區概要顯示哪些數字／社區物件總覽在哪看
jgb/C/community-estates-category-switch｜社區底下的物件清單怎麼切換總覽／招租／買賣？（欄位標題會跟著切換內容改變）｜target_user=property_manager｜社區物件怎麼切換招租買賣／總覽招租買賣分類在哪／社區物件清單分類切換
jgb/C/community-estates-add-batch-copy｜怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制）｜target_user=property_manager｜社區物件怎麼新增／社區物件批次新增／複製現有物件／物件數量上限
jgb/C/community-estates-extra-tabs｜社區底下有差額發票、投報率頁籤嗎？（差額發票看該社區是否開通；投入成本與投報率由團隊的投報率功能開關一起控制，租客、大房東與沒有「查看所有帳單」權限的成員看不到）｜target_user=property_manager｜社區差額發票頁籤／社區投報率在哪看／社區物件頁籤有哪些
jgb/C/community-estates-pagination｜社區物件清單每頁筆數可以調整嗎？（30／60／90項）｜target_user=property_manager｜社區物件每頁顯示幾筆／物件清單分頁筆數／怎麼調整每頁項目數
### C-community-public-page 社區公開頁（社區詳情、社區總表） {#C-community-public-page}
jgb/C/community-show-content｜社區公開頁（社區廣告）顯示什麼？（基本資訊、鄰近捷運、社區介紹、刊登中物件）｜target_user=property_manager,prospect｜社區詳情頁有什麼／社區公開頁看得到什麼／社區廣告頁內容
jgb/C/community-show-price-range｜社區公開頁最上方顯示什麼價格區間？（租賃金額區間、售價金額區間）｜target_user=property_manager,prospect｜社區價格區間在哪看／社區租金區間
jgb/C/community-show-share｜社區公開頁怎麼分享？（分享燈箱或手機分享選單、查看所有物件連結）｜target_user=property_manager｜社區頁面怎麼分享／社區查看所有物件連結／社區分享燈箱
jgb/C/community-show-editor-nav｜在社區廣告頁可以直接跳到編輯社區、社區詳情或社區總表嗎？（只有具備編輯物件權限的使用者看得到這個選單）｜target_user=property_manager｜社區詳情頁怎麼編輯社區／社區公開頁回總表／社區詳情頁返回Dashboard
### C-community-force-binding 物件綁定社區的導引（2022/05 社區功能上線時的強制綁定流程，限團隊擁有者） {#C-community-force-binding}
jgb/C/forcebinding-why-and-who｜為什麼「物件需綁定社區」的導引？（2022/05/12 社區功能上線，只有團隊擁有者能操作）｜target_user=property_manager｜為什麼要綁定社區／物件為什麼要綁社區／誰可以做物件綁定社區
jgb/C/forcebinding-welcome-progress｜物件綁定社區的導引起始畫面顯示什麼？（需同意服務條款）｜target_user=property_manager｜綁定社區進度在哪看／還有幾個物件沒綁社區／綁定物件前要同意什麼
jgb/C/forcebinding-two-steps｜物件綁定社區導引有哪兩個步驟？（填寫社區資料、選擇欲綁定社區內的物件）｜target_user=property_manager｜綁定社區流程有幾步／先建社區還是先綁物件／沒綁完社區會怎樣
jgb/C/forcebinding-select-estates-irreversible｜怎麼挑選要綁定的物件？（可關鍵字搜尋、每頁30/60/90項，確認綁定後無法修改）｜target_user=property_manager｜怎麼選要綁定的物件／綁定物件可以改嗎／綁定物件怎麼搜尋
jgb/C/forcebinding-completion-states｜綁定完成後會看到什麼？（全部綁完顯示恭喜，還有剩則提示繼續綁定）｜target_user=property_manager｜綁定完成畫面／還有物件沒綁完怎麼辦／綁定物件成功提示
### C-estate-list 物件列表與篩選 {#C-estate-list}
jgb/C/estate-list-add-must-pick-community｜物件總表怎麼新增物件？（新增與複製現有物件都要先經過社區選擇畫面，目前沒有批次新增入口）｜target_user=property_manager｜物件總表怎麼新增物件／新增物件要選社區嗎／物件總表可以批次新增嗎／複製現有物件在物件總表
jgb/C/estate-list-counter-and-limit｜物件總表標題下方顯示什麼？（目前物件總數、尚可新增數量）｜target_user=property_manager｜物件總表顯示物件總數／還可以新增幾個物件／尚可新增物件數量在哪看
jgb/C/estate-list-filters｜物件總表有哪些進階篩選條件？（縣市行政區、經理人、大房東、社區、捷運、格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金與面積(坪)範圍、標籤）｜target_user=property_manager｜物件總表篩選條件有哪些／怎麼依經理人篩選物件／物件怎麼依社區篩選／租金範圍怎麼篩／格局怎麼篩選物件
jgb/C/estate-list-keyword-search｜物件總表關鍵字搜尋可以查什麼？（案名、地址、租客、物件ID、手機、信箱）｜target_user=property_manager｜物件怎麼用租客手機搜尋／物件關鍵字搜尋範圍／用物件ID找物件
jgb/C/estate-list-batch-actions｜物件總表可以批次操作嗎？（個人房東、大房東、租客身分不能；法人房東與社宅團隊成員可：匯出物件、新增批次帳單、批次刊登／取消刊登招租廣告、刪除；批次取消刊登失敗時不會顯示任何提示）｜target_user=property_manager｜物件怎麼批次下架／怎麼一次刊登多筆物件／物件總表可以匯出嗎
jgb/C/estate-status-affects-actions｜物件狀態會影響哪些功能？（招租廣告狀態未刊登／刊登中，與合約狀態洽談中／租約中，是各自獨立的；刪除物件要求未刊登、沒有合約、沒有 IoT 綁定）｜target_user=property_manager,prospect｜物件狀態影響什麼／洽談中是什麼意思／物件狀態怎麼判斷／刊登中的物件可以刪除嗎
jgb/C/estate-list-pagination｜物件總表每頁筆數可以調整嗎？（30／60／90項）｜target_user=property_manager｜物件總表每頁顯示幾筆／物件列表分頁筆數／調整每頁顯示物件數
jgb/C/estate-list-filters-space-type-and-others｜物件總表篩選還有哪些條件？（空間類型多選、「更多」：VR、有電梯、可開伙、可養寵物）｜target_user=property_manager｜物件怎麼篩VR／物件篩選可養寵物／物件篩選有電梯
jgb/C/estate-list-category-switch｜物件總表怎麼切換總覽／招租／買賣？（三種分類切換）｜target_user=property_manager｜物件總表怎麼切換招租買賣／物件總覽招租買賣分類／物件列表分類切換
jgb/C/estate-list-sort-remembers-last｜物件總表怎麼排序？（排序選項由系統提供，寬度 576px 以上切換的排序會被記住）｜target_user=property_manager｜物件總表怎麼排序／上次選的排序方式還在嗎／物件排序選項有哪些
### C-estate-edit 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） {#C-estate-edit}
jgb/C/estate-edit-basic-space-type｜物件基本資料的空間類型、用途、格局要怎麼填？｜target_user=property_manager｜物件用途怎麼選／物件格局怎麼填／虛擬辦公室是什麼意思
jgb/C/estate-edit-basic-address｜物件的詳細地址與對外顯示地址有什麼差別？｜target_user=property_manager｜物件地址怎麼填／對外顯示地址是什麼／物件廣告地址跟實際地址不同
jgb/C/estate-edit-basic-floor-room-number｜物件的樓層與房號要怎麼填？（頂加輸入+1、地下室輸入-1）｜target_user=property_manager｜頂加怎麼填樓層／地下室樓層怎麼寫／物件之幾房之幾床是什麼
jgb/C/estate-edit-basic-community-name-hide｜物件廣告頁可以隱藏群組/大樓名稱嗎？｜target_user=property_manager｜物件可以不顯示社區名稱嗎／廣告頁隱藏大樓名稱／群組名稱怎麼隱藏
jgb/C/estate-edit-building-transcript-social｜社宅物件建物謄本要填什麼？（申請謄本日期、段小段、謄本面積公式，不會顯示在廣告頁）｜target_user=property_manager｜社宅建物謄本要填什麼／社宅謄本面積怎麼算／社宅建物謄本會公開嗎
jgb/C/estate-edit-building-transcript-general｜一般物件建物謄本可以填什麼？（土地標的清冊、坐落基地、稅籍編號、專有部分、主建物、附屬建物，皆非必填）｜target_user=property_manager｜一般物件建物謄本要填什麼／土地標的清冊怎麼填／稅籍編號在哪填
jgb/C/estate-edit-facilities｜物件附設傢俱怎麼設定？（依用途與格局分區加入家電、傢俱、自訂項目，數量0不顯示在廣告頁）｜target_user=property_manager｜附設傢俱怎麼填／家電傢俱怎麼加／物件設備要怎麼設定
jgb/C/estate-edit-gallery-title-photos｜物件標題與照片有什麼限制？（標題最長60字、照片最多15張15MB、平面圖最多5張含PDF）｜target_user=property_manager｜物件標題字數限制／物件照片可以傳幾張／物件平面圖怎麼上傳／第一張照片是封面嗎
jgb/C/estate-edit-intro-transit｜物件介紹要填什麼？（房源簡介、鄰近交通，可加多筆鄰近捷運站）｜target_user=property_manager｜物件介紹要寫什麼／房源簡介怎麼寫／物件怎麼加捷運站
jgb/C/estate-edit-vr-720｜物件的720 VR全景照怎麼拍？（需先安裝 VR Maker App 掃 QR Code 拍攝，可設定是否用於廣告）｜target_user=property_manager｜720VR怎麼拍／VR全景照要用什麼app／VR全景照可以用電腦編輯嗎
jgb/C/estate-edit-cannot-change-community｜物件可以換綁到別的社區嗎？（畫面上目前沒有這個操作入口）｜target_user=property_manager｜物件換社區／物件重新綁定社區／物件搬到別的社區
jgb/C/estate-edit-basic-orientation｜物件基本資料可以填朝向嗎？｜target_user=property_manager｜物件朝向怎麼填／物件座向欄位
jgb/C/estate-edit-tabs-overview｜物件編輯有哪些分頁？（「物件資訊」與「廣告資訊」兩個群組；社宅與一般物件的建物謄本分頁互斥）｜target_user=property_manager｜物件編輯有哪些分頁／物件資訊跟廣告資訊差在哪／社宅物件編輯分頁跟一般物件不一樣
### C-rent-listing 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實） {#C-rent-listing}
jgb/C/estate-rent-detail-deposit-cap｜招租押金有法定上限嗎？（一般租賃契約押金最高不得超過兩個月租金）｜target_user=property_manager,prospect｜押金上限幾個月／押金可以收多少／押金計算方式
jgb/C/estate-rent-detail-move-in-lease-terms｜招租詳情的最短租期、最快入住日、最快點交日怎麼填？｜target_user=property_manager｜最短租期選項有哪些／最快入住日怎麼填／最快點交日設定
jgb/C/estate-rent-detail-tenant-conditions｜招租條件要求可以設定什麼？（身份限制複選、養寵物可否、開伙可否、生活公約）｜target_user=property_manager｜招租可以限制什麼身份／可以養寵物嗎怎麼設定／招租能不能開伙
jgb/C/estate-rent-contact-agency-info｜刊登主資訊的團隊資訊要在哪裡修改？（法人／社宅房東顯示公司資訊、到團隊資訊修改；個人房東顯示經理人資訊、到帳號資訊修改）｜target_user=property_manager｜經紀人證號在哪改／登記證號怎麼設定／刊登主資訊看不到經紀人資料
jgb/C/estate-rent-contact-manager-and-hide｜招租廣告可以隱藏經理人／房東的名稱、電話、Email嗎？（勾選框在「經理人資訊」或「刊登主資訊」的經理人卡片上，每種身分只有一組）｜target_user=property_manager,prospect｜招租廣告可以不顯示電話嗎／怎麼隱藏經理人名稱／廣告上隱藏Email
jgb/C/estate-rent-verify-legal｜招租的核實訊息是什麼？（依租賃住宅市場發展條例核實產權登記與違建面積）｜target_user=property_manager,prospect｜核實訊息要填什麼／產權登記已辦理未辦理是什麼意思／違建面積要填嗎
jgb/C/estate-rent-open-permission-and-validation｜為什麼物件的招租廣告刊登不出去？（沒有刊登權限、團隊沒有生效中的訂閱方案、或物件資料檢查沒通過）｜target_user=property_manager｜物件刊登不出去／刊登物件失敗原因／刊登物件需要什麼權限／招租廣告刊登失敗
jgb/C/estate-rent-detail-price-and-tax｜招租詳情要填哪些金額相關欄位？（面積、幣別、每月租金；特定合作團隊另有營業稅：應稅／零稅率／免稅）｜target_user=property_manager｜招租租金要填幣別嗎／營業稅怎麼選／招租面積怎麼填
### C-estate-dashboard 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） {#C-estate-dashboard}
jgb/C/estate-dashboard-entry-and-groups｜物件儀表板進去預設是哪個分頁？（一般預設招租表現，大房東直接進合約歷程；大房東看不到「限管理者查看」分頁群組）｜target_user=property_manager｜物件儀表板預設看哪頁／大房東能看物件儀表板哪些分頁／物件Dashboard入口
jgb/C/estate-dashboard-rent-performance｜招租表現分頁顯示什麼？（空置天數、廣告瀏覽次數、帳務表現、合約歷程與修繕紀錄摘要）｜target_user=property_manager｜招租表現看什麼／物件空置天數在哪看／廣告瀏覽次數在哪查
jgb/C/estate-dashboard-contracts-history｜物件儀表板的合約歷程顯示哪些欄位？（一般房東：狀態／簽約類型／物件／承租人／租期／是否通知；社宅房東：合約名稱／承租人／租期）｜target_user=property_manager｜合約歷程有哪些欄位／物件歷史合約在哪看／合約歷程每頁筆數
jgb/C/estate-dashboard-bills-tabs｜物件儀表板的帳務收支有哪些子頁籤？（總收支、統計報表）｜target_user=property_manager｜帳務收支子頁籤／物件統計報表在哪看／物件總收支怎麼看
jgb/C/estate-dashboard-repair-status-flow｜物件儀表板修繕紀錄怎麼呈現？（申請修繕→安排修繕→完成修繕→結單四狀態）｜target_user=property_manager｜修繕紀錄狀態有哪些／修繕紀錄欄位／物件修繕在哪看結算金額
jgb/C/estate-dashboard-attachments-vs-contract-attachments｜「附件清單」跟「合約附件」差在哪？（附件清單可上傳 JPG／PNG／PDF、每個物件最多 5 個檔案、單檔 10MB，上傳與下載需要物件編輯權限，刪除操作只有代理人且有新增物件權限才看得到；合約附件是固定的附件項目清單，可上傳附件補充以避免日後爭議）｜target_user=property_manager｜合約附件要傳什麼文件／附件清單空間不夠怎麼辦／物件附件跟合約附件差別
jgb/C/estate-dashboard-runnings-vs-memos｜「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入或支出與金額，記事本沒有金額欄位；兩者都能附檔）｜target_user=property_manager｜流水帳怎麼記／物件記事本可以記什麼／流水帳跟記事本差別
jgb/C/estate-dashboard-monthly-report-upload｜每月報表／每月對帳單怎麼上傳？（PDF、10MB上限，可批次指定多個物件，同月重傳會覆蓋舊檔）｜target_user=property_manager｜每月報表怎麼上傳／每月對帳單格式限制／同一個月上傳兩次報表會怎樣／怎麼批次上傳報表
jgb/C/estate-dashboard-top-cards｜物件儀表板最上方顯示哪三張卡？（物件資訊、招租廣告、買賣廣告；編輯捷徑需要新增物件權限）｜target_user=property_manager｜物件儀表板上面卡片是什麼／儀表板編輯捷徑不見了／儀表板可以直接編輯招租廣告嗎
### C-estate-public-page 單一物件廣告頁（招租） {#C-estate-public-page}
jgb/C/estate-house-preview-unpublished｜物件還沒刊登（未開放）時，廣告頁會怎麼顯示？（屋主看到的是預覽頁提示）｜target_user=property_manager,prospect｜物件沒刊登廣告頁還看得到嗎／物件廣告預覽頁／還沒刊登的物件連結有效嗎
jgb/C/estate-house-invite-countdown｜簽約邀請連結會失效嗎？（連結會顯示倒數，過期後失效）｜target_user=property_manager,prospect｜簽約邀請連結會過期嗎／合約邀請連結有時效嗎／邀請連結多久失效
jgb/C/estate-house-content-blocks｜物件廣告頁顯示哪些內容？（照片／VR全景切換、設備與設施、交通與環境設施、溫馨提醒）｜target_user=property_manager,prospect｜物件廣告頁有哪些內容／物件廣告頁看不看得到VR／物件廣告頁會顯示鄰近捷運站嗎
jgb/C/estate-house-contact-landlord｜物件廣告頁「聯絡房東」區塊顯示什麼？（房東電話／Email依隱藏設定決定是否顯示；公司廣告電話／Email不受隱藏設定影響）｜target_user=property_manager,prospect｜物件廣告頁聯絡房東怎麼看／隱藏電話設定有效嗎／廣告頁可以加房東Line嗎
jgb/C/estate-house-vs-show-url｜物件廣告頁的網址會自動轉換嗎？（刊登中時，內部編號網址會自動轉址到 JGB 編號公開網址）｜target_user=property_manager｜物件廣告頁網址是什麼／物件連結會自動跳轉嗎／物件廣告頁網址為什麼變了
jgb/C/estate-house-fees-table｜物件廣告頁有費用明細表嗎？（車位物件不顯示，其餘物件顯示生活費用表）｜target_user=property_manager,prospect｜物件廣告頁費用怎麼看／物件廣告頁有清潔費水電費嗎／車位物件有費用表嗎
jgb/C/estate-house-appointment-cta｜物件廣告頁有預約入住的按鈕嗎？（一般訪客看到「立即預約入住」，受邀簽約者看到「查看合約」）｜target_user=property_manager,prospect｜物件廣告頁怎麼預約看房／立即預約入住按鈕在哪／受邀簽約的人看到什麼按鈕
jgb/C/estate-house-info-card｜物件廣告頁的資料卡片顯示什麼？（地址／社區名稱、租金元/月與含哪些費用、建築類型與樓層或格局、商用類的空間類型與座位數、面積、物件平面圖）｜target_user=property_manager,prospect｜物件廣告頁資料卡片有什麼／物件廣告頁看不看得到含哪些費用／物件廣告頁格局在哪看
### C-team-storefront 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） {#C-team-storefront}
jgb/C/team-public-page-purpose｜房東對外首頁（招租店舖）是什麼？（公開展示聯絡資訊、簡介與所有刊登中物件，供分享給潛在租客）｜target_user=property_manager,prospect｜招租店舖是什麼／房東對外首頁怎麼用／怎麼進去我的招租店舖
jgb/C/team-public-page-edit-and-banner｜招租店舖上可以直接編輯哪些內容？（橫幅照片、頭像、自我介紹；團隊身分另可改團隊名稱等欄位，需要「編輯團隊權限」）｜target_user=property_manager｜招租店舖封面照片怎麼換／改自我介紹會同步嗎／招租店舖大頭照怎麼設
jgb/C/team-public-page-filter-and-view｜招租店舖怎麼篩選物件？（篩選條件加關鍵字搜尋，手機版多數條件收在「更多」；可切換小圖示／大圖示／條列式；每頁筆數 30／60／90，預設 30）｜target_user=property_manager｜招租店舖怎麼篩選物件／招租店舖顯示模式／招租店舖每頁顯示幾筆
jgb/C/team-public-page-share｜招租店舖怎麼分享？（電腦上開分享視窗可複製連結或分享到 FB、Line、LinkedIn；手機上會叫出系統分享選單；分享的是目前頁面的網址）｜target_user=property_manager,prospect｜招租店舖怎麼分享／怎麼分享招租店舖到Line
jgb/C/team-public-page-recruitment｜多團隊招募頁和一般招租店舖有什麼不同？（網址格式不同、物件列表只有招租、沒有社區篩選、每頁預設 10 筆）｜target_user=property_manager,prospect｜招募頁每頁顯示幾筆／招募頁跟一般店舖的網址不一樣嗎／招募頁跟招租店舖差在哪

## D 租約（含委託約子題） {#D}
scope: 合約建立、簽署、狀態與階段、續約、退租、違約金、租客邀請簽約；委託約（僅法人房東）；⛔ 帳單與押金金流歸 E
### D-contract-list 合約列表與搜尋 {#D-contract-list}
jgb/D/contract-list-status-tabs｜合約列表有哪些狀態頁籤？｜target_user=property_manager｜合約列表有哪些狀態／待租客簽回是什麼意思／合約總表分頁／合約狀態頁籤
jgb/D/contract-search-keyword-scope｜合約列表怎麼搜尋合約？（案名／地址／租客／ID／手機／信箱六種關鍵字，另有進階搜尋）｜target_user=property_manager｜合約怎麼搜尋／合約列表關鍵字搜尋範圍／進階搜尋合約
jgb/D/contract-create-entry｜怎麼建立一份新合約？（合約總表右上角「建立合約」，或物件總表小齒輪選建立合約）｜target_user=property_manager｜怎麼建立合約／合約要去哪裡建立／一個物件可以簽幾份合約／新增合約入口
jgb/D/contract-create-estate-completeness-requirement｜物件要先刊登廣告才能建立合約嗎？（現行規則是必填欄位要填齊，不是看刊登狀態）｜target_user=property_manager｜物件要刊登才能建約嗎／沒有上架的物件可以簽約嗎／建立合約的物件條件
jgb/D/contract-list-row-gear-actions｜合約總表列的小齒輪可以做什麼操作？（不論狀態都有「查看帳單」；其餘依合約狀態、身分、權限等條件增減）｜target_user=property_manager｜合約列表小齒輪可以做什麼／合約列表的齒輪按鈕能做什麼
jgb/D/contract-list-row-sort-options｜合約總表可以怎麼排序？（依名稱、更新時間、合約起始日、終止日、成立日，共 5 種依據）｜target_user=property_manager｜合約列表怎麼排序／合約排序選單
jgb/D/contract-list-columns｜合約總表有哪些欄位？（含團隊自訂的「標籤」欄）｜target_user=property_manager｜合約列表標籤欄／合約總表欄位
jgb/D/contract-list-deposit-alert｜合約總表的待退押金提示燈號是什麼意思？（合約到期前 30 天才能點退）｜target_user=property_manager｜待退押金提示是什麼／合約列表押金提示燈號
jgb/D/contract-list-bill-currency-column｜合約總表什麼時候會多出「帳單幣別」欄？（只有在批次建立帳單、挑選合約的頁面才會出現，一般檢視沒有這一欄）｜target_user=property_manager｜合約列表帳單幣別欄／帳單幣別什麼時候出現
jgb/D/contract-list-export-declaration｜合約總表可以匯出實價登錄資料嗎？（只有在「執行中合約」頁籤、中文站台、團隊開通此功能且帳號有建立合約權限時才會出現按鈕）｜target_user=property_manager｜匯出實價登錄資料／合約列表怎麼匯出實價登錄
jgb/D/contract-list-export-excel｜合約總表可以匯出 Excel 嗎？（勾選後按「匯出合約」，需要匯出合約權限，內容含租期、每期租金、合約押金等欄位）｜target_user=property_manager｜合約匯出excel／合約總表下載／匯出合約權限
### D-contract-edit-general 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） {#D-contract-edit-general}
jgb/D/contract-edit-tabs-overview｜建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁）｜target_user=property_manager｜建約有哪些步驟／合約編輯分幾頁／建立合約流程／合約分頁順序
jgb/D/contract-tenant-basic-info｜承租方基本資料怎麼填？（個人／法人租客、租客註冊或免註冊、緊急聯絡人）｜target_user=property_manager｜承租方基本資料怎麼填／租客要註冊帳號才能簽約嗎／法人租客怎麼填／緊急聯絡人
jgb/D/contract-rentbasic-template-and-dates｜「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期）｜target_user=property_manager｜合約範本怎麼選／合約起迄日期怎麼設定／租賃訂約日期是什麼
jgb/D/contract-rentbasic-billing-cycle｜「基本條件」分頁的繳費週期與帳單週期制度怎麼設定？（繳費週期／繳費截止日、當月分算或跨月計算、分算日）｜target_user=property_manager｜繳費週期怎麼設定／繳費截止日是什麼／跨月計算跟當月分算差在哪／帳單週期分算日
jgb/D/contract-rentbasic-latefee｜「基本條件」分頁的遲繳滯納金怎麼計算？（僅特定合作團隊可見，兩段比例＋拖欠天數門檻，欄位唯讀）｜target_user=property_manager｜滯納金怎麼設定／遲繳滯納金計算方式／滯納金比例跟拖欠天數
jgb/D/contract-rentbasic-tenant-language｜「基本條件」分頁的租客慣用語系是什麼？（決定系統產生給租客的合約文件語系）｜target_user=property_manager｜租客慣用語系是什麼／合約文件語系怎麼選
jgb/D/contract-rentbasic-early-termination｜合約的「可否提前解約」與違約金怎麼設定？（每月租金／固定金額／詳參補充條款／其他四種算法）｜target_user=property_manager｜提前解約違約金怎麼算／合約可否提前解約設定／違約金計算方式／解約通知天數
jgb/D/contract-rent-fees｜租金費用分頁要設定什麼？（租金、押金、自訂收入／支出費用、租金優惠、繳費週期優惠）｜target_user=property_manager｜租金費用怎麼設定／押金上限／自訂費用收入支出／繳費週期優惠／租金優惠跟繳費週期優惠差在哪
jgb/D/contract-rent-deposit-two-modes｜押金有哪幾種設定方式？（每月租金倍數／固定金額兩種計算基準）｜target_user=property_manager｜押金怎麼算／押金計算基準
jgb/D/contract-rent-adjustment｜租金調幅設定分頁在做什麼？（依繳費期數設定固定金額或百分比調漲／調降）｜target_user=property_manager｜租金調幅怎麼設定／租金逐年調漲／分期調整租金／租金調幅方式
jgb/D/contract-tax-invoice｜稅與發票分頁怎麼設定？（是否開立發票、出租方統一編號、各品項是否應稅）｜target_user=property_manager｜合約發票怎麼設定／租金以外可以開發票嗎／應稅品項設定／統一編號要不要打
jgb/D/contract-bill-setting｜帳單設定分頁在做什麼？（預先編輯未來帳單的標題、金額、週期與自動執行動作）｜target_user=property_manager｜帳單設定分頁怎麼用／可以先編輯未來帳單嗎／帳單期間跟租期不一樣／帳單自動執行動作
jgb/D/contract-payment-method｜合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種）｜target_user=property_manager｜收款方式有哪些／怎麼設定收租金方式／固定虛擬帳號收租／現金收款帳戶
jgb/D/contract-facilities-tab｜附設傢俱分頁在做什麼？（設定家具責任歸屬，簽約後會帶入點交清單）｜target_user=property_manager｜家具修繕責任歸屬／點交清單怎麼來的
jgb/D/contract-situation-tab｜現況補充分頁要寫什麼？（車位、屋況、漏水處等現況細節）｜target_user=property_manager｜現況補充要寫什麼／非自然死亡揭露
jgb/D/contract-landlord-dealer-basic｜出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、法人房東可用電子簽名圖章）｜target_user=property_manager｜出租方基本資料怎麼填／經理人資訊怎麼設定／電子簽名圖章／團隊資料自動帶入
jgb/D/contract-building-transcript-optional｜建物謄本分頁是選填的嗎？（選填，僅供合約內容完備使用，不會顯示在廣告頁）｜target_user=property_manager｜建物謄本要填嗎／謄本資訊會公開嗎／建物謄本是選填的嗎
jgb/D/contract-attachments-optional｜合約附件分頁能上傳什麼？（各類文件圖片或 PDF，最大 10MB）｜target_user=property_manager｜合約附件可以放什麼／附件檔案大小限制／合約附件格式
jgb/D/contract-additional-convention｜補充條款有字數限制嗎？（可套用範本與複製其他合約）｜target_user=property_manager｜補充條款字數限制／補充條款最多幾行／合約條款寫不下怎麼辦／補充條款範本
jgb/D/contract-edit-tabs-conditional-rules｜合約編輯分頁會依什麼條件增減？（紙本／客製化契約書、車位、特定合作團隊範本、稅務發票資格皆會影響）｜target_user=property_manager｜合約分頁為什麼變少／紙本合約有哪些分頁／車位合約分頁
jgb/D/contract-edit-building-transcript-visibility｜「建物謄本」分頁什麼時候不會顯示？（只有選中／未選合約範本時才顯示，選到英越文或泰文版就會被拿掉）｜target_user=property_manager｜建物謄本分頁不見了／什麼時候沒有建物謄本
jgb/D/contract-lease-scope-by-space-type｜合約的租賃範圍怎麼決定？（物件空間型態，不用使用者勾選）｜target_user=property_manager｜租賃範圍怎麼決定／合約全部還是部分怎麼判斷／租賃範圍會自動判斷嗎
jgb/D/contract-tenant-code-change｜承租人編碼要異動怎麼辦？（此操作需由 JGB 客服協助）｜target_user=property_manager｜承租人編碼異動／租客編碼改不了／承租人代號怎麼改
### D-contract-edit-social-housing 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） {#D-contract-edit-social-housing}
jgb/D/social-housing-building-detail｜社宅合約「建物標的」分組有哪些分頁？（建物細節、現況補充、現況照片、附設傢俱四個分頁）｜target_user=property_manager｜社宅合約建物標的怎麼填／建物細節填錯怎麼改
jgb/D/social-housing-photos-tab｜社宅合約「現況照片」分頁一定要上傳嗎？（部分照片為必填，用來證明社宅內部現況設備存在）｜target_user=property_manager｜現況照片一定要上傳嗎／社宅照片認證
jgb/D/social-housing-facilities-tab｜社宅合約「附設傢俱」分頁要填什麼？（設備、隔間、家電與傢俱的數量與型號）｜target_user=property_manager｜社宅附設傢俱／社宅傢俱數量怎麼填／社宅家電型號怎麼填
jgb/D/social-housing-rent-basic-conditions｜社宅合約「基本條件」要填什麼？（合約範本、委託期間、住宅現況、物件返還狀態、代收定金、爭議處理）｜target_user=property_manager｜社宅合約基本條件／委託租賃期間是什麼／物件返還狀態怎麼設定／代收定金幾日內轉交
jgb/D/social-housing-early-termination-difference｜社宅合約的提前解約怎麼設定？跟一般合約一樣嗎？（只設定雙方是否可以提前解約，沒有違約金計算方式）｜target_user=property_manager｜社宅合約提前解約說明／社宅違約金跟一般合約一樣嗎
jgb/D/social-housing-rent-fees-tab｜社宅合約「租金費用」分頁要填什麼？（代租金額或包租金額、租金與押金、生活費用）｜target_user=property_manager｜社宅租金費用怎麼填／社宅代租金額怎麼設定
jgb/D/social-housing-payment-method-tab｜社宅合約「收款方式」怎麼設定？（轉帳、票據、現金三種；代租代管範本還要選收款人是原房東或業者）｜target_user=property_manager｜社宅收款方式／收款人是誰
jgb/D/social-housing-notary｜社宅合約一定要公證嗎？（預設應辦理公證，可填理由不辦但視同放棄公證費補助；辦理公證後需下載文件紙本簽署再上傳歸檔）｜target_user=property_manager｜社宅合約一定要公證嗎／公證費由誰負擔／社宅簽約流程／公證後怎麼上傳
jgb/D/social-housing-attachments-tab｜社宅合約「合約附件」要準備什麼？（合約附件只收其他文件如附註條款、稅籍證明；測量成果圖等在出租方附件分頁，轉租範本除外）｜target_user=property_manager｜社宅合約附件要準備什麼／出租方承租方附件上傳
jgb/D/social-housing-subsidy-terms-tab｜社宅合約「補助申請」分頁在做什麼？（配合社宅包租代管 333 補貼政策，出租方三種稅費減免）｜target_user=property_manager｜社宅333補貼政策／社宅補助申請怎麼填
jgb/D/social-housing-landlord-tabs-overview｜社宅合約「出租方」分組有哪些分頁？（基本資料、授權、附件三個分頁）｜target_user=property_manager｜社宅出租方分頁有哪些／社宅出租方基本資料授權附件
jgb/D/social-housing-landlord-license-conditions｜社宅合約「授權」分頁要確認什麼？（合法建物條件、住宅使用、同意提供住宅的方式等授權事項）｜target_user=property_manager｜合法建物條件／出租方授權項目
jgb/D/social-housing-tenant-tabs-overview｜社宅合約「承租方」分組有哪些分頁？（基本資料、家庭＆財產、授權、附件）｜target_user=property_manager｜社宅承租方分頁有哪些／社宅承租方基本資料家庭授權附件
jgb/D/social-housing-tenant-basic-status｜社宅合約「基本資料」怎麼審核租客資格？（承租人資格、住宅政策補貼戶、代理人；包租包管改填公司資料）｜target_user=property_manager｜低收入戶申請社宅／社宅租客資格怎麼審核
jgb/D/social-housing-tenant-household｜社宅合約「家庭＆財產」分頁要登記什麼？（家庭成員、不動產與動產總額、最近年所得）｜target_user=property_manager｜社宅家庭財產申報／社宅不動產動產總額申報
jgb/D/social-housing-tenant-license｜社宅合約承租方的「授權」分頁要同意什麼？（承租資格變動通知、無自有住宅、所得低於最低生活費標準 3.5 倍、財稅所得總檢核）｜target_user=property_manager｜承租方授權項目／財稅所得總檢核授權
jgb/D/social-housing-dealer-basic｜社宅合約「業者」分頁在做什麼？（確認團隊資料與經理人資訊，有誤要回團隊資訊或帳號資訊修改）｜target_user=property_manager｜社宅業者分頁／業者資料錯誤要去哪改
jgb/D/social-housing-move-in-terms｜社宅合約「點交證明文件」分頁在約定什麼？（點交狀態與修繕責任的預先約定，不是簽約後實際執行的點交）｜target_user=property_manager｜社宅點交證明文件是什麼／合約裡的點交跟實際點交一樣嗎
jgb/D/social-housing-charter-sublet-tab-hiding｜社宅合約選「包租包管」或「轉租」範本，分頁會不同嗎？（包租包管不顯示承租方的家庭＆財產、授權、附件，轉租不顯示出租方的授權、附件）｜target_user=property_manager｜社宅包租包管範本分頁／社宅轉租範本分頁差異
### D-contract-sign-view 簽約與合約檢視 {#D-contract-sign-view}
jgb/D/contract-invite-and-review-period｜合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效；天數由 JGB 依團隊設定）｜target_user=property_manager,prospect｜合約審閱期多久／合約邀請多久會過期／租客沒簽約連結失效／審閱期天數
jgb/D/contract-sign-flow-steps｜租客簽約要經過哪些步驟？（填承租方簽約資料與上傳文件、預覽合約、自動扣款先授權信用卡、部分範本另有條款勾選、雲想科技畫面簽名）｜target_user=property_manager｜租客怎麼簽約／簽約要填什麼／簽約要傳哪些印章／簽名過程有紀錄嗎
jgb/D/contract-esign-no-extra-fee｜電子簽章簽約要另外收費嗎？（系統內沒有簽章計費機制，簽約流程無付費／加購畫面）｜target_user=property_manager,prospect｜電子簽章要收費嗎／簽約要加購嗎／電子簽章計費
jgb/D/contract-locked-after-signing｜合約簽約後可以修改嗎？（送出前可編輯、雙方簽名完成前可取消邀請重編，簽署完成即無法更改，需重新簽一份新合約）｜target_user=property_manager,prospect｜合約簽名後可以改嗎／合約內容填錯怎麼辦／取消簽名重新編輯／取消邀請重新編輯／簽約後修改合約
jgb/D/contract-show-panels｜社宅合約的檢視頁面看得到什麼？（承租方、業者、經理人資訊，以及點交點退進行中的提示）｜target_user=property_manager｜社宅合約檢視頁面看得到什麼／社宅合約詳細資料有哪些區塊／合約點交中提示
jgb/D/contract-show-paper-upload-archive｜合約檢視頁的「歸檔資料」是什麼？有什麼檔案限制？（租客免註冊的合約簽署後上傳合約、續約、終止合約的歸檔 PDF，最大 10MB）｜target_user=property_manager｜免註冊合約歸檔上傳限制／合約本文歸檔資料
jgb/D/contract-show-creditcard-auth-prompt｜簽約時會提示信用卡自動扣款授權嗎？（收款設定需要信用卡自動扣款時，租客在簽約頁點「下一步」會提示前往授權；特定合作團隊專屬範本除外）｜target_user=property_manager｜信用卡自動扣款授權／前往授權是什麼
jgb/D/contract-upload-existing-vs-electronic｜上傳既有合約跟建立電子合約差在哪？（上傳＝「紙本簽約」，用於已簽訂或已公證完成的合約；自製合約模板是電子合約的「客製化契約書」）｜target_user=property_manager,prospect｜上傳既有合約適用情境／上傳合約檔案太大怎麼辦／既存合約跟電子合約差別
jgb/D/contract-guarantor-add-after-signing｜簽約後可以補加保證人嗎？（租客簽約流程本身就能加連帶保證人；簽約完成後要補加，業者端沒有自助功能，需洽 JGB 客服協助）｜target_user=property_manager｜簽約後加保證人／補簽保證人／簽約完成後能加連帶保證人嗎
### D-move-in 點交 {#D-move-in}
jgb/D/move-in-checklist-and-responsibility｜點交清單怎麼確認？（依合約約定的傢俱項目逐一上傳照片、標註出租方或承租方負責）｜target_user=property_manager｜點交清單怎麼確認／點交要上傳照片嗎／點交責任歸屬／點交備註字數限制
jgb/D/move-in-meter-readings｜點交要填另計費用起始度數嗎？（依合約設定另計的費用項目要輸入起始度數，會直接帶入日後帳單計算）｜target_user=property_manager｜點交要填電表度數嗎／點交起始度數／點交後帳單怎麼算電費
jgb/D/move-in-page-general-vs-social-housing｜點交頁面一般合約跟社宅合約用的是同一個嗎？（不是，一般住宅合約用一般合約的點交頁面，社宅合約會被導向社宅合約的點交頁面）｜target_user=property_manager｜社宅點交頁面跟一般合約一樣嗎／點交頁面差異
jgb/D/move-in-blocked-states｜點交送出後還能再送一次嗎？（已完成點交無法再次送出；已送出、等待租客確認中的清單要先取消邀請才能改）｜target_user=property_manager｜點交已送出可以改嗎／點交完成能重新點交嗎／取消點交邀請
jgb/D/move-in-cancel-invite｜點交邀請送出後可以取消嗎？（可以，系統會記錄「取消點交邀請」這個動作）｜target_user=property_manager｜點交邀請可以取消嗎／已送出的點交怎麼收回
jgb/D/move-in-result-pdf｜點交結果能下載 PDF 嗎？（有專屬頁面可以檢視或下載點交 PDF）｜target_user=property_manager｜點交結果PDF／點交可以下載嗎
jgb/D/move-in-optional-and-timing｜點交是必要流程嗎？（點交是選擇性操作，未點交也能發帳單；簽約完成後即可在執行中合約選取物件點交）｜target_user=property_manager,prospect｜點交一定要做嗎／什麼時候可以點交／不點交可以發帳單嗎
### D-move-out 點退 {#D-move-out}
jgb/D/move-out-checklist-and-damage｜點退時怎麼處理設備損壞？（系統點退可逐項填入賠償金額與理由、可儲存草稿；上傳點退文件則只顯示文件）｜target_user=property_manager｜點退設備損壞怎麼處理／點退可以先存草稿嗎／點退賠償金額
jgb/D/move-out-bill-generation｜點退會產生什麼帳單？（房東在「點退找補費用」確認費用後送出點退；註冊租客按同意後帳單成立、合約轉為點退完成，不看有沒有繳款；免註冊租客送出即成立）｜target_user=property_manager｜點退帳單包含什麼／點退完成的條件／租客同意點退後會怎樣／免註冊租客點退帳單
jgb/D/move-out-eligibility-conditions｜什麼合約可以點退？（合約狀態須為合約成立／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外）｜target_user=property_manager｜什麼合約可以點退／沒有註冊的租客可以點退嗎／點退合約狀態限制
jgb/D/move-out-timing-window｜點退的時間限制是什麼？（合約到期前 30 天起可以點退，過了到期日之後目前沒有再設上限）｜target_user=property_manager｜點退時間限制／點退要在到期前幾天辦理／合約到期後還能點退嗎
jgb/D/move-out-remains-in-active-list｜點退完成的合約為什麼還在「執行中合約」？（只要還沒到合約到期日就會留在執行中，到期後才轉入歷史合約）｜target_user=property_manager,prospect｜已點退為什麼還在執行中合約／歷史合約是什麼／點退狀態分類
jgb/D/move-out-fee-adjustment-step｜點退第二步「點退找補費用」頁面要填什麼？（系統帶入的點退費用項目，含提前解約時自動帶入的違約金、傢俱賠償，另可填備註、期限、附件）｜target_user=property_manager｜點退找補費用要填什麼／點退第二步流程／點退傢俱賠償
jgb/D/move-out-tenant-no-response-cancel｜租客不確認點退時要怎麼辦？（系統不會逾期自動放行，只能由房東取消點退邀請後重新發送）｜target_user=property_manager｜租客不確認點退／點退會自動過期放行嗎／點退邀請可以取消重發嗎
### D-renew 續約 {#D-renew}
jgb/D/renew-batch-entry-and-selection｜怎麼一次幫多筆合約續約？（合約總表「建立合約」旁選批次續約，異動中的合約不能選）｜target_user=property_manager｜批次續約怎麼操作／續約可以選哪些合約／哪些合約不能續約
jgb/D/renew-date-setting-modes｜續約日期怎麼設定？（多份合約可用快速日期設定一次加 N 個月，或個別指定每份合約的續約日）｜target_user=property_manager｜續約日期怎麼設定／續約可以一次設定嗎／租客收不到續約通知
jgb/D/renew-upload-paper-signed｜續約可以上傳紙本已簽合約嗎？（只選一份紙本簽約的合約續約時可以，提供雙方已完成簽約的紙本合約掃描檔）｜target_user=property_manager｜續約可以上傳紙本合約嗎／續約用電子簽名圖章
jgb/D/renew-preview-bill-generation｜續約可以預先編輯帳單嗎？（續約預覽頁可先編輯續約期間帳單，實際帳單於完成續約後才產生）｜target_user=property_manager｜續約可以先看帳單嗎／續約帳單什麼時候產生／確認續約帳單頁面
jgb/D/renew-signing-flow｜續約邀請發出後流程是什麼？（房東確認無誤後立即簽名完成續約）｜target_user=property_manager｜續約簽約流程／租客簽回續約後要做什麼／續約怎麼完成
jgb/D/renew-invite-review-days｜續約邀請效期是幾天？（預設 3 天，團隊可覆蓋設定）｜target_user=property_manager｜續約邀請幾天內要簽／續約審閱天數
jgb/D/renew-data-carryover-rules｜續約時資料怎麼沿用？（新合約由舊合約複製，並更新出租方/承租方最新資料；週期設定有調整就用新的、沒調整就沿用）｜target_user=property_manager｜續約會沿用舊合約資料嗎／續約聯絡資料會更新嗎
jgb/D/renew-deposit-difference-handling｜續約押金差額怎麼處理？（一般續約第一張帳單不列押金；只有特定合作團隊的延長續約會用原押金算差額；新合約無法直接沿用舊合約押金，一律列全額押金）｜target_user=property_manager｜續約押金差額／押金可以轉到新合約嗎／續約要不要重收押金
### D-early-termination 提前解約 {#D-early-termination}
jgb/D/early-termination-reasons｜房東申請提前解約要選什麼理由？（新版中文合約有 10 項理由可選，其餘合約只能選「其他」）｜target_user=property_manager｜提前解約理由有哪些／解約要選什麼原因／非中文合約解約理由
jgb/D/early-termination-form-fields｜申請提前解約要填什麼？（預計提前解約日須早於原合約到期日、違約金支付方與金額、佐證資料）｜target_user=property_manager｜提前解約要填什麼／解約違約金由誰付／提前解約日期限制／提前解約佐證資料怎麼傳
jgb/D/early-termination-tenant-cancel｜誰可以取消已送出的提前解約申請？（房東透過小齒輪取消；租客只能取消自己發起、還在申請中的提前解約）｜target_user=property_manager｜房東怎麼取消提前終止合約／租客可以取消提前解約嗎／取消提前解約條件
jgb/D/early-termination-eligibility｜什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起）｜target_user=property_manager｜什麼合約可以提前解約／可否提前解約設定對房東有效嗎／續約中可以提前解約嗎
jgb/D/early-termination-effect-move-out｜提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金）｜target_user=property_manager,prospect｜提前解約後多久可以點退／提前解約影響
jgb/D/early-termination-billing-after｜提前解約後還會出新帳單嗎？（解約日之後系統不會再自動產生新租金帳單；已產生、落在解約日後的帳單要業者自行封存）｜target_user=property_manager｜提前解約後帳單／解約後還會出帳單嗎／解約後帳單要自己處理嗎
### D-notary 租約公證（公證分頁與公證服務） {#D-notary}
jgb/D/general-contract-notary-tab｜一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項；只有部分合約範本有此選項）｜target_user=property_manager｜一般合約公證怎麼設定／公證強制執行事項／英文合約可以公證嗎
jgb/D/contract-thinkcloud-esign-service｜簽約時進入的雲想科技頁面是什麼？（系統導向 Thinkcloud 雲想科技的電子簽署網頁，簽完再導回 JGB；一般合約、委託合約皆會用到）｜target_user=property_manager｜簽約跳出的雲想科技頁面是什麼／雲想科技畫面是誰在用
jgb/D/contract-thinkcloud-signing-variants｜簽署畫面與客製化契約書 PDF 要注意什麼？（公會中文版合約加補充條款會多一組簽名位置；上傳的 PDF 底稿無法解析時合約建立不了，要重新輸出再上傳）｜target_user=property_manager｜客製化合約 PDF 無法解析／公會版合約補充條款簽名位置／補充條款為什麼多一組簽名
jgb/D/contract-thinkcloud-diy-pdf-sign-blocked｜客製化契約書送簽時 PDF 底稿解析失敗會怎樣？（簽署不會開始）｜target_user=property_manager｜客製化契約書送簽失敗／送簽時 PDF 底稿解析不出來
### D-entrust-contract 委託合約（列表、建立編輯、檢視） {#D-entrust-contract}
jgb/D/entrusted-contract-what-is-it｜委託合約是什麼？（房東委託業者包租代管的合約，跟業者與租客之間的租賃合約是不同份文件）｜target_user=property_manager,prospect｜委託合約是什麼／委託合約跟租賃合約差在哪／委託合約狀態頁籤
jgb/D/entrusted-contract-lease-type｜委託合約「包租」跟「代管」有什麼不同？（代管必填服務費計算模式、幣別與金額或比例；計算制度、週期、約定日期兩者都要填）｜target_user=property_manager,prospect｜包租跟代管差在哪／委託合約類型／代管合約要填什麼
jgb/D/entrusted-contract-tabs-overview｜委託合約編輯畫面有哪些分頁？（房東資訊、委託條件三頁、管理方資訊共 3 組 5 頁）｜target_user=property_manager｜委託合約分頁有哪些／委託合約編輯步驟
jgb/D/entrusted-contract-preview-to-show｜委託合約編輯完成後怎麼進入簽署？（點右上角「預覽合約」先儲存資料，再進入檢視頁面）｜target_user=property_manager｜委託合約怎麼進入簽署／委託合約預覽合約按鈕
jgb/D/entrusted-contract-upload-file-size-limit｜委託合約上傳既有檔案限制多大？（畫面寫最大 6MB，上傳元件實際上限是 10MB）｜target_user=property_manager｜委託合約上傳檔案大小限制／委託合約檔案6MB
jgb/D/entrusted-contract-fees｜委託合約的收費分頁要設定什麼？（服務費或包租金額的計算模式與週期，押金提示不得超過兩個月租金）｜target_user=property_manager｜委託合約收費怎麼算／委託合約押金上限／跨月計算與當月分算
jgb/D/entrusted-contract-landlord-info｜委託合約的房東資訊怎麼填？（房東註冊或房東免註冊；免註冊時要選個人房東或法人房東身份）｜target_user=property_manager｜委託合約房東資訊怎麼填／房東一定要註冊帳號嗎／房東免註冊是什麼
jgb/D/entrusted-contract-manager-info｜委託合約的經理人資訊分頁要填什麼？（選簽約公司並帶出公司、經紀人與租賃住宅管理人員資訊、指定經理人、電子簽名圖章）｜target_user=property_manager｜委託合約經理人資訊怎麼填／租賃住宅管理人員證號／委託合約電子簽名圖章
jgb/D/entrusted-contract-payment｜委託合約收付款資訊怎麼設定？（沒有選擇器，固定顯示「出租方帳戶」與「管理方帳戶」兩個現金收付區塊，後者必填）｜target_user=property_manager｜委託合約收付款怎麼設定／收款是給房東還是業者／委託合約可以選一種收款方式嗎
jgb/D/entrusted-contract-show-and-upload｜委託合約檢視頁面能做什麼？（查看歸檔資料、上傳既有委託合約檔案、尚未寄出邀請前可返回編輯）｜target_user=property_manager｜委託合約檢視頁面看得到什麼／委託合約上傳檔案／委託合約還沒簽名可以改嗎
jgb/D/entrusted-contract-create-entry｜委託合約怎麼建立？（委託合約列表頁「建立委託約」按鈕，需有建立合約權限，可選客製化契約書或紙本簽約）｜target_user=property_manager｜委託合約怎麼建立／委託合約建立入口

## E 帳務（含發票、收款金流、抄表） {#E}
scope: 帳單產生與週期、催繳、滯納金、收款方式與金流商、發票、抄表與水電費；⛔ 修繕流程歸 F
### E-bill-list 帳單列表與帳單狀態 {#E-bill-list}
jgb/E/bill-list-tabs｜帳單列表分成哪些分頁？（帳單總表／草稿帳單／收款帳單／支出帳單／總收支）｜target_user=property_manager,prospect｜帳單分頁／帳單列表怎麼分類／帳單總表跟草稿帳單差在哪／帳單有哪些分頁
jgb/E/bill-status-tabs-landlord｜「草稿帳單」「收款帳單」「支出帳單」分頁底下各分哪些狀態？｜target_user=property_manager｜帳單狀態有哪些／草稿排定發送封存差在哪／應到帳待對帳已到帳／應支出已支出已失效
jgb/E/bill-status-tabs-tenant｜租客的帳單列表跟房東的有什麼不同？（只有收款帳單／支出帳單兩個分頁）｜target_user=property_manager,prospect｜租客帳單列表／租客看得到草稿帳單嗎／租客帳單分頁／租客帳單狀態
jgb/E/bill-actions-draft｜「草稿」狀態的帳單可以做哪些動作？（編輯／發送／移至已到帳／封存）｜target_user=property_manager｜草稿帳單能做什麼／草稿帳單怎麼發送／草稿帳單齒輪選單／合併帳單
jgb/E/bill-actions-scheduled｜「排定發送」狀態的帳單可以做哪些動作？（只有「取消排定發送」）｜target_user=property_manager｜排定發送可以取消嗎／取消排定發送
jgb/E/bill-actions-archived｜「封存」狀態的帳單可以做哪些動作？（沒有任何動作，齒輪選單是空的）｜target_user=property_manager｜封存的帳單能做什麼／封存後還能操作嗎
jgb/E/bill-actions-unreceived｜「應到帳」狀態的收款帳單可以做哪些動作？（匯款資訊／移至已到帳／開立發票／取消帳單）｜target_user=property_manager｜應到帳可以做什麼／匯款資訊在哪看／應到帳可以取消嗎
jgb/E/bill-actions-progress｜「待對帳」狀態的收款帳單可以做哪些動作？（單張可退至應到帳、移至已到帳、開立發票，沒有取消帳單；批次沒有退至應到帳）｜target_user=property_manager｜待對帳可以做什麼／退至應到帳／待對帳能取消嗎
jgb/E/bill-actions-received｜「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單）｜target_user=property_manager｜已到帳能做什麼／重開發票／作廢發票／收款備註怎麼改／退款對帳單
jgb/E/bill-actions-expense-unpaid｜「應支出」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：付款）｜target_user=property_manager｜應支出可以做什麼／租客怎麼付款
jgb/E/bill-actions-expense-unconfirmed｜「待對帳」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：沒有齒輪動作）｜target_user=property_manager｜待對帳支出帳單
jgb/E/bill-actions-expense-paid｜「已支出」狀態的支出帳單，房東跟租客各能做什麼？（房東一律有編輯收款備註／封存；反轉帳單才多出收據／退款對帳單）｜target_user=property_manager｜已支出的收據／退款對帳單怎麼看／已支出可以封存嗎
jgb/E/bill-expired-status｜帳單狀態顯示「已失效」是什麼意思？（限電錶儲值帳單，4 天繳費期限）｜target_user=property_manager,prospect｜已失效是什麼意思／儲值帳單過期／帳單已失效要補繳嗎／電錶儲值帳單失效
jgb/E/bill-list-keyword-search｜帳單列表怎麼用關鍵字搜尋？（可指定用案名／地址／租客／ID／手機／信箱／帳單名稱／虛擬帳號／合約帳單共 9 種比對）｜target_user=property_manager｜帳單怎麼搜尋／帳單關鍵字搜尋／用虛擬帳號查帳單／用租客名字找帳單
jgb/E/bill-list-export｜帳單總表怎麼匯出？（要先勾選帳單才會出現匯出選項）｜target_user=property_manager｜帳單怎麼匯出／匯出帳單上限／匯出帳單要先勾選嗎／全選匯出跟勾選匯出差在哪
jgb/E/bill-list-bulk-action-intersection｜帳單總表勾選多筆不同狀態的帳單時，批次操作列會出現哪些動作？（只列出每一筆帳單都能做的共同動作）｜target_user=property_manager｜勾選不同狀態的帳單能做什麼／帳單總表批次操作交集／混合狀態帳單批次動作
jgb/E/bill-list-export-other-tabs｜「草稿帳單」「支出帳單」「總收支」分頁的匯出按鈕，跟帳單總表不是同一套（不需要先勾選，走另一個較舊的匯出流程）｜target_user=property_manager｜支出帳單怎麼匯出／總收支怎麼匯出／草稿帳單怎麼匯出
jgb/E/bill-list-income-export-social-housing｜「收款帳單」分頁固定的匯出按鈕，什麼時候會多出「匯出租客繳費證明」子選項？（只有身分類別為社會住宅的帳號才有）｜target_user=property_manager｜收款帳單怎麼匯出／匯出租客繳費證明／社會住宅匯出證明
jgb/E/bill-list-special-team-cvs-buttons｜「應到帳」「已到帳」狀態，特定合作團隊的帳號會多出哪些按鈕？（應到帳：匯入發票；已到帳：匯出收據／匯入收據／批次匯出收據）｜target_user=property_manager｜匯入發票在哪／匯出收據／批次匯出收據
jgb/E/bill-balance-tab-export-submenu｜「總收支」分頁的匯出按鈕，特定合作團隊的帳號會多出什麼子選項？（匯出收支明細表）｜target_user=property_manager｜匯出收支明細表／總收支匯出子選項
jgb/E/bill-list-batch-shortcuts｜「草稿帳單」分頁右上角有哪些批次建立帳單的快捷按鈕？（新增週期帳單／新增批次帳單／排定發送帳單／批次編輯帳單，Excel新增帳單僅限特定合作團隊；帳單總表沒有這些按鈕）｜target_user=property_manager｜批次建立帳單／一次建立多張帳單／Excel新增帳單／批次編輯帳單／批次編輯帳單特定團隊視窗不一樣
jgb/E/bill-scheduled-send-rule｜「排定發送帳單」有什麼限制？（一般要度數填完才能排，點退帳單與綁定智慧電錶的電費例外；每天中午 12 點統一發送）｜target_user=property_manager｜排定發送帳單怎麼用／排定發送限制／水電度數沒填能排定發送嗎／帳單幾點統一發送
jgb/E/bill-single-notification-deeplink｜帳單通知信裡的連結點進去會看到什麼？（帳單列表只先列出通知裡的那幾張帳單，自己改篩選後回到一般列表）｜target_user=property_manager｜帳單連結點進去／通知信帳單連結／通知連結只列出那張帳單
jgb/E/bill-balance-tab｜「總收支」分頁的用途是什麼？（「全部」混列已到帳與已支出的帳單，另有已到帳、已支出、應到帳、應支出各自的頁籤）｜target_user=property_manager｜總收支分頁／收支總覽在哪看／總收支跟帳單總表差在哪
jgb/E/bill-notify-channels｜帳單通知走哪些管道？通知對象是誰？（免註冊租客可分別開關 Email／簡訊，已註冊租客固定收 Email 與站內通知、已綁定 LINE／FB 另收推播；只發給帳單本身的那位承租人）｜target_user=property_manager,prospect｜帳單通知怎麼關／簡訊通知在哪關掉／帳單通知會發給誰／關閉租客所有通知
jgb/E/bill-invoice-void-limitation｜發票可以線上作廢嗎？（可在帳單詳細頁作廢，但只支援 ezPay；其他金流商的發票作廢不了，已開折讓的發票也不能再作廢）｜target_user=property_manager,prospect｜發票怎麼作廢／作廢發票支援哪些金流商／折讓後還能作廢嗎／ezPay作廢發票
jgb/E/bill-notify-remittance-visibility｜「通知已匯款」按鈕什麼時候才會出現？（租客付款資訊視窗只在非線上金流收款的帳單才有；應支出帳單的齒輪選單則沒有這個限制）｜target_user=property_manager,prospect｜通知已匯款在哪／通知已匯款不見了／線上收款還要通知已匯款嗎
jgb/E/bill-archive-precondition｜帳單要什麼狀態才可以直接封存？（「待發送」跟「已到帳」都可以直接封存，不用先轉成已到帳；可勾選多筆一次封存）｜target_user=property_manager｜草稿可以直接封存嗎／封存要先變已到帳嗎／批次封存帳單／封存順序怎麼安排
jgb/E/bill-deposit-receipt-no｜押金收據號碼是系統自動產生的嗎？（特定合作團隊的客製功能，號碼透過 Excel 匯出／匯入手動填寫，系統不會自動編流水號）｜target_user=property_manager,prospect｜押金收據號碼怎麼填／押金收據號碼會自動產生嗎／押金收據匯入匯出
jgb/E/bill-scheduled-contract-ended-guard｜合約已結束、但底下還留著未來計費期間的租金帳單，系統排定發送時會怎麼處理？（系統自動排定發送／自動寄出都會跳過不寄，但不會刪除帳單；業者手動排定發送則不受這條規則限制；批次寄出依帳單 id 由小到大處理，沒有可指定的發送順序）｜target_user=property_manager｜合約結束後帳單還會自動寄嗎／解約後草稿帳單會怎樣／排定發送帳單順序／合約到期未來帳單擋不擋
jgb/E/bill-remind-resend-by-support｜業者可以請 JGB 客服代發催繳通知嗎？（此操作需由 JGB 客服協助；業者端沒有自助重發催繳的介面）｜target_user=property_manager,prospect｜催繳通知可以重發嗎／客服可以幫忙催繳嗎／重新寄催繳通知
jgb/E/bill-cvs-barcode-overdue-payment｜超商代碼繳費逾期後才繳，帳單還會入帳嗎？（系統不檢查代碼期限，代碼逾期後是否還能繳費屬外部規定，系統不判斷）｜target_user=property_manager,prospect｜超商代碼過期還能繳嗎／超商代碼逾期入帳／超商繳費逾期
jgb/E/bill-receipt-feature-roadmap｜收據功能還會不會有新的開發？（現行已到帳帳單的齒輪選單一律看得到收據，目前沒有公開的後續開發時程）｜target_user=property_manager,prospect｜收據功能會不會更新／收據還有新功能嗎／收據開發時程
### E-bill-create-edit 建立與編輯帳單（單筆、批次、週期批次） {#E-bill-create-edit}
jgb/E/bill-create-modes｜新增帳單有哪幾種頁面？（新增帳單／新增批次帳單／新增週期帳單／編輯帳單）｜target_user=property_manager,prospect｜新增帳單有幾種／批次帳單跟週期帳單差在哪／怎麼新增帳單／編輯帳單在哪
jgb/E/bill-create-target｜新增帳單時「對象」可以選哪些？（租客／大房東／物件／其他）｜target_user=property_manager｜帳單對象怎麼選／帳單可以開給大房東嗎／帳單對象是誰／帳單開給物件
jgb/E/bill-batch-vs-cycle｜「新增批次帳單」跟「新增週期帳單」有什麼不同？（批次是每個對象各一張，週期是一次產出各期帳單；兩者都可在租客與物件之間切換）｜target_user=property_manager,prospect｜批次帳單跟週期帳單差別／新增批次帳單怎麼選對象／新增週期帳單怎麼選物件
jgb/E/bill-cycle-schedule-fields｜新增週期帳單的「繳費週期」設定要填哪些欄位？（繳費週期／繳費截止日／截止日設定／帳單週期制度）｜target_user=property_manager｜週期帳單怎麼設定／繳費週期選項／當月分算跟跨月計算差在哪／提前截止同月截止
jgb/E/bill-cycle-amortization｜「總額（自動分攤）」欄位什麼時候才會出現？（只有新增週期帳單、且團隊開通社區投報率時）｜target_user=property_manager｜總額自動分攤在哪／週期帳單金額怎麼分攤／自動分攤欄位不見了
jgb/E/bill-fee-item-rules｜帳單費用細目填寫有什麼規則？（度數欄位最多小數點後 2 位、電水瓦斯金額欄位限制小數點後 2 位、當期度數不可小於上期度數）｜target_user=property_manager｜費用細目怎麼填／水電費當期度數錯誤／金額小數點限制／度數輸入錯誤提示
jgb/E/bill-title-field｜「帳單標題」最多可以輸入幾個字？（45 個字）｜target_user=property_manager｜帳單標題字數上限／帳單標題最多幾個字
jgb/E/bill-remark-field｜「帳單備註」最多可以輸入幾個字？（150 個字）｜target_user=property_manager｜帳單備註字數上限／帳單備註最多幾個字
jgb/E/bill-internal-note-field｜「內部備註」最多可以輸入幾個字？誰看得到？（100 個字，僅供業者團隊成員查看／編輯，租客看不到）｜target_user=property_manager｜內部備註字數上限／內部備註誰看得到
jgb/E/bill-internal-note-visibility｜「內部備註」在哪些地方會出現？（只給業者團隊成員看：新增帳單單筆、編輯帳單與帳單列表欄位可填，帳單明細可看；批次／週期帳單頁面不顯示）｜target_user=property_manager｜內部備註在批次帳單有嗎／內部備註在週期帳單有嗎
jgb/E/bill-payment-method-account-pair｜新增帳單時付款方式跟收款帳戶一定要一起填嗎？（兩者要嘛都空、要嘛都填；固定虛擬帳號例外）｜target_user=property_manager｜付款方式沒填會怎樣／收款帳戶沒選會怎樣／固定虛擬帳號付款方式
jgb/E/bill-tenant-unverified-draft-lock｜租客還沒完成驗證時，帳單會被擋在草稿嗎？（合約頁的提示這樣寫，但目前送出帳單時系統不會因為驗證狀態擋下）｜target_user=property_manager,prospect｜租客沒驗證帳單發不出去／帳單卡在草稿／租客驗證連結過期帳單／帳單一直是草稿狀態
jgb/E/bill-submit-button-behavior｜新增帳單頁面下方送出按鈕的文字跟行為會依情境改變（送出／發送簽核／簽核中／預覽帳單）｜target_user=property_manager｜送出按鈕文字不一樣／發送簽核是什麼／簽核中按鈕／週期帳單預覽按鈕
jgb/E/bill-contract-payment-prefill｜新增帳單選租客當對象時，付款方式會自動帶入合約的收款設定嗎？（會，但帳戶已停用/不可取號等情況不會亂猜）｜target_user=property_manager｜帳單付款方式自動帶入／新增帳單付款方式跟合約一樣／合約收款方式帶入帳單
jgb/E/bill-partial-month-proration｜不足一個月的租金怎麼算？（依天數比例；一般團隊以剩餘天數 ÷ 該月曆天數，逐月產帳以實際天數 ÷ 該期帳單天數，不是固定除以 30）｜target_user=property_manager,prospect｜不足月租金怎麼算／入住天數比例分攤／不足一個月租金按天數怎麼折算
jgb/E/bill-power-reading-draft-defaults｜草稿帳單的電費度數要自己填嗎？（物件有綁定智慧電錶時，可在編輯頁按「取得即時電錶度數」先帶入）｜target_user=property_manager｜電費度數怎麼帶入／電表度數會重抓嗎／草稿帳單度數空白
### E-bill-stats 帳單統計與報表 {#E-bill-stats}
jgb/E/bill-stat-overview｜「統計報表」的「當前表現」分頁顯示什麼？（收款情況／支出情況卡片）｜target_user=property_manager,prospect｜統計報表看什麼／收款情況怎麼算／支出情況怎麼算／預計總收款是什麼
jgb/E/bill-stat-monthly-tabs｜統計報表除了「當前表現」，還有「每月報表」「每月對帳單」分頁，但只有特定合作團隊看得到｜target_user=property_manager｜每月報表在哪／每月對帳單在哪／統計報表分頁不見了
jgb/E/bill-monthly-report-upload｜「每月報表」跟「每月對帳單」分頁在做什麼？（依社區/物件上傳與下載每月的物件報表、對帳單檔案）｜target_user=property_manager｜物件報表怎麼新增／物件對帳單怎麼新增／報表還沒上傳／每月報表社區物件篩選
### E-social-housing-report 社宅報表 {#E-social-housing-report}
jgb/E/social-housing-sheet-list｜社宅報表的「清冊列表」在列什麼？（每個媒合編號底下的表單勾選與修繕費、申請期數）｜target_user=property_manager｜社宅報表清冊列表／媒合編號在哪看／社宅表單修繕費／申請期數上限是12嗎／社宅表單哪個沒有額外欄位／社宅表單全選
jgb/E/social-housing-sheet-contract-version｜社宅報表上方的合約版本切換列是做什麼用的？（切換不同版本的社宅合約，每次查詢都會帶著這個版本一起送出）｜target_user=property_manager｜社宅報表合約版本／社宅報表版本切換／社宅合約版本網址
jgb/E/social-housing-sheet-make-form｜社宅報表怎麼製作表單？（填撥款日、勾選表單後按「製作表單」，會記錄成清冊紀錄）｜target_user=property_manager｜社宅報表怎麼做表單／撥款日在哪填／製作表單按鈕／社宅表單團隊紀錄
jgb/E/social-housing-sheet-export-history｜社宅報表的「匯出歷史」會記錄幾筆匯出動作？（系統至多記錄近 30 筆）｜target_user=property_manager｜社宅報表匯出歷史／社宅表單匯出紀錄上限／匯出歷史看多少筆
jgb/E/social-housing-sheet-archive｜社宅報表的「歸檔」是什麼意思？（操作按鈕是「確定歸檔」；綠色「歸檔」標籤只在已歸檔後才出現）｜target_user=property_manager｜社宅報表歸檔／歸檔後能修改嗎／確定歸檔按鈕／舊紀錄表單能下載嗎
jgb/E/social-housing-sheet-program-scope｜社宅報表的「社會住宅」身份可以對應到哪個地方政府的社宅方案？（系統只定義身份類別，不判斷方案適配）｜target_user=property_manager｜社宅報表適用哪個社宅方案／社會住宅身份限制／社宅報表限台灣嗎
### E-balance-invoice 差額發票（群組、底租、社區層開關） {#E-balance-invoice}
jgb/E/balance-invoice-community-switch｜差額發票要在哪裡設定？（團隊開通後在「差額發票管理」建立差額群組；社區編輯頁的差額發票開關只對部分特定合作團隊顯示）｜target_user=property_manager,prospect｜怎麼開差額發票／社區差額發票開關／差額發票怎麼計算／底租總額怎麼設定
jgb/E/balance-invoice-group-statuses｜差額發票群組總表有哪些狀態？（尚未生效／進行中／歷史／封存）｜target_user=property_manager｜差額發票群組狀態／差額發票群組總表／差額發票尚未生效／差額發票封存
jgb/E/balance-invoice-list-columns｜差額發票群組總表列表裡看得到哪些欄位？（ID／出租物件數／本月發票狀態／累積成本／累積收入／累積發票金額）｜target_user=property_manager｜差額發票列表欄位／差額發票累積成本／差額發票累積收入／差額發票本月發票狀態
jgb/E/balance-invoice-group-basic-info｜建立差額發票群組要填哪些基本資料？（群組名稱／底租／租期／前期餘額／房屋座落地址／房屋稅籍編號）｜target_user=property_manager｜差額發票群組怎麼建立／群組名稱必填嗎／前期餘額怎麼填／房屋稅籍編號填在哪
jgb/E/balance-invoice-pick-and-individual-rent｜差額發票群組怎麼加入物件？每個物件的底租可以自訂嗎？（群組可開「自訂個別底租」，把群組底租總額分配給各物件）｜target_user=property_manager｜差額發票怎麼加物件／自訂個別底租／可分配租金是什麼／群組底租怎麼分配到每個物件
jgb/E/balance-invoice-group-detail-tabs｜差額發票群組詳細頁面看得到什麼？（招租數量／本月應收金額／本月已收金額，以及三個分頁）｜target_user=property_manager｜差額發票群組詳細頁／招租數量是什麼／本月應收金額／差額總表在哪看
jgb/E/balance-invoice-monthly-invoice-table｜「差額總表」裡每個月的差額怎麼看、怎麼開發票？（累積成本、累積收入、差額、是否開發票、發票金額、發票字軌）｜target_user=property_manager｜差額總表欄位／差額發票開立日期／差額發票字軌／差額怎麼算
jgb/E/balance-invoice-timing｜差額發票什麼時候自動產生？（一般業者每月 1 日 03:00 開立上月發票；特定團隊另有自己的時程）｜target_user=property_manager｜差額發票何時開立／差額發票排程／差額發票狀態多久更新一次／差額發票每2小時
jgb/E/balance-invoice-group-action-menu｜差額發票群組的動作選單有哪些選項？什麼時候不能用？（編輯群組／開立發票／封存群組／刪除群組；列表頁不能用時反灰，詳細頁直接不顯示；另有查看歷程圖示）｜target_user=property_manager｜差額發票群組怎麼刪除／差額發票群組動作選單／開立發票按鈕為什麼灰色／封存群組按鈕為什麼不能按
jgb/E/balance-invoice-refund-report-column｜差額發票收支表的租金退款／減免怎麼呈現？（列在「租金增(減)(B)」欄，以負數表示）｜target_user=property_manager｜差額發票收支表退款／差額發票租金增減欄／差額發票減免怎麼記
jgb/E/balance-invoice-rent-item-rule｜差額發票收支表怎麼判斷一個帳單品項算不算「租金」收入？（系統預設品項看名稱是不是「租金」「退租金」；自訂品項看品項性質）｜target_user=property_manager｜差額發票租金品項判定／退租帳單科目重複計入／差額收支表怎麼認租金
jgb/E/balance-invoice-entity-type-change｜身分從法人改成自然人後，差額發票群組要怎麼重新設定？（系統沒有專用的身分切換規則）｜target_user=property_manager｜差額發票法人改自然人／差額群組身分切換／差額發票身分變更
jgb/E/balance-invoice-unsigned-contract｜合約還沒簽回時能不能開發票或收據？（發票看合約的開票設定、押金收據看帳單是否到帳，簽署狀態是否連動要看個案）｜target_user=property_manager｜合約未簽回能開發票嗎／合約未簽回押金收據／簽約中可以開發票嗎
jgb/E/balance-invoice-anomaly-list｜帳單不在任何差額發票群組內時，JGB 怎麼處理？｜target_user=property_manager｜帳單沒有差額群組怎麼辦／發票異常盤查名單／帳單不在差額群組
### E-virtual-account 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） {#E-virtual-account}
jgb/E/recharge-account-list-columns｜「固定虛擬帳號管理」列表看得到哪些資訊？（虛擬帳號、餘額、歷程一律都有；租客或物件欄位看團隊的固定虛擬帳號模式；有編輯權限時另有操作欄）｜target_user=property_manager｜固定虛擬帳號管理在哪／虛擬帳號列表欄位／虛擬帳號餘額能改嗎／虛擬帳號歷程
jgb/E/recharge-account-delete｜固定虛擬帳號要怎麼刪除？（列表操作選單選「刪除」，跳出確認視窗後才會真的刪掉）｜target_user=property_manager｜虛擬帳號刪除流程／刪除虛擬帳號要確認嗎／刪除虛擬帳號失敗
jgb/E/recharge-account-history-content｜點開「歷程」看得到哪些內容？（最近 50 筆金額變動的時間／類型／金額／前後餘額／操作人員，有連結帳單可以點開查看）｜target_user=property_manager｜歷程看得到什麼／金額變動歷程內容／歷程能看帳單嗎
jgb/E/recharge-account-bank-support｜固定虛擬帳號可以選哪些銀行？（聯邦、中國信託有專屬的建號流程，其餘從系統銀行清單選）｜target_user=property_manager｜虛擬帳號支援哪家銀行／聯邦虛擬帳號／中信虛擬帳號／虛擬帳號銀行清單
jgb/E/recharge-account-ubot-flow｜聯邦（803）虛擬帳號怎麼建立？有什麼限制？（金額鎖在帳號裡，租客月租變動要重新建一組）｜target_user=property_manager｜聯邦虛擬帳號怎麼建／聯邦虛擬帳號綁定金額／聯邦虛擬帳號金額改了怎麼辦／聯邦虛擬帳號匯錯金額
jgb/E/recharge-account-ctbc-flow｜中國信託（822）虛擬帳號怎麼算出帳號？（填企業識別碼 5 碼與繳款人識別碼 8 碼由系統計算）｜target_user=property_manager｜中信虛擬帳號怎麼算／企業識別碼幾碼／繳款人識別碼幾碼／中信虛擬帳號計算機
jgb/E/recharge-account-immutable｜虛擬帳號建立後，銀行跟帳號可以改嗎？（不行，銀行跟帳號建立後不能改；可以改餘額，以及依團隊模式改租客資料或綁定物件）｜target_user=property_manager｜虛擬帳號可以改銀行嗎／虛擬帳號可以改帳號嗎／編輯虛擬帳號能改什麼／虛擬帳號要換銀行怎麼辦
jgb/E/recharge-account-estate-binding-validation｜虛擬帳號綁定物件時，輸入物件 ID 有什麼驗證？｜target_user=property_manager｜虛擬帳號綁定物件ID／物件ID驗證失敗／物件不屬於這個團隊／虛擬帳號選擇物件按鈕
jgb/E/recharge-account-export｜「固定虛擬帳號管理」的「報表匯出」匯出什麼？（指定日期區間內租客匯入的入帳明細 Excel）｜target_user=property_manager｜虛擬帳號怎麼匯出／虛擬帳號匯出明細／虛擬帳號匯出日期區間
jgb/E/recharge-account-daily-settlement｜固定虛擬帳號的入帳是怎麼自動比對到帳單的？（入金當下即時銷帳，另有每日凌晨 03:00 排程再比對；限特定合作團隊；餘額不夠不會變成已到帳）｜target_user=property_manager｜固定虛擬帳號自動到帳／虛擬帳號入帳幾點處理／虛擬帳號沖銷排程
jgb/E/recharge-account-refund-excluded｜退押金這類要付給租客的帳單，也走固定虛擬帳號嗎？（不會，顯示的是租客本人的收款帳戶）｜target_user=property_manager｜退押金走虛擬帳號嗎／支出帳單收款帳戶／退款方向虛擬帳號
jgb/E/recharge-account-vs-single-use-atm｜「固定虛擬帳號管理」跟租客線上繳費取得的 ATM 虛擬帳號是同一種嗎？（不是，線上繳費的 ATM 帳號是依單張帳單單筆取號，藍新取號的效期為 180 天）｜target_user=property_manager｜ATM虛擬帳號跟固定虛擬帳號差在哪／線上繳費ATM虛擬帳號效期／固定虛擬帳號跟單筆ATM帳號一樣嗎
jgb/E/recharge-account-mismatch-and-duplicate｜租客重複匯款時系統怎麼處理？（國泰世華單筆帳單 ATM 帳號已付款後重複匯入會略過；固定虛擬帳號多匯的部分留在儲值餘額）｜target_user=property_manager｜虛擬帳號重複匯款／虛擬帳號多匯的錢去哪／重複匯款會重複入帳嗎
jgb/E/recharge-account-regenerate-expired｜逾期的虛擬帳號能不能重新產生？（此操作需由 JGB 客服協助，業者端沒有自助入口）｜target_user=property_manager｜逾期虛擬帳號重新產生／虛擬帳號過期怎麼辦／虛擬帳號重發
### E-payment-onboarding 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」） {#E-payment-onboarding}
jgb/E/payment-gateway-options｜JGB 支援哪些收款金流？身分限制是什麼？（國泰世華／永豐銀行／中國信託／藍新／愛金卡；個人房東不能開通藍新、國泰世華、永豐銀行）｜target_user=property_manager,prospect｜支援哪些收款金流／個人房東可以用哪個金流／國泰世華可以申請嗎／永豐銀行金流申請
jgb/E/payment-gateway-fees｜各家收款金流的申請費用跟入帳帳戶限制是什麼？（國泰世華／永豐銀行首次設定費 5,000 元且限本行帳戶；中國信託／藍新線上申請不收申請費、可指定任一實體帳戶）｜target_user=property_manager,prospect｜金流申請要收費嗎／首次設定費多少／入帳帳戶有限制嗎／國泰世華入帳帳戶
jgb/E/newebpay-precondition｜開通藍新智付通前要準備什麼？（申請表要自填 09 開頭的台灣手機號碼）｜target_user=property_manager｜藍新開通前提條件／藍新智付通手機號碼
jgb/E/newebpay-required-fields｜開通藍新智付通前，團隊要先填完哪些資料？（個人房東不能開通藍新）｜target_user=property_manager｜藍新開通要先填什麼資料／個人房東可以開藍新嗎／公司統編沒填能開藍新嗎
jgb/E/newebpay-payment-methods｜藍新開通時有哪些付款方式？（信用卡／Google Pay／Samsung Pay／ATM／超商代碼送出時都會開啟；國外卡要另外申請）｜target_user=property_manager,prospect｜藍新支援哪些付款方式／超商代碼繳費金額限制／國外卡要另外申請嗎／藍新付款方式預設開哪些
jgb/E/ctbc-apply-flow｜中國信託收款怎麼申請？（中信轉帳 Pay 填資料送審，ACH 驗證約 5 個工作天；中信虛擬帳號填 5 碼企業代碼即可，個人房東不能開通）｜target_user=property_manager｜中信轉帳Pay怎麼申請／中信金流審核多久／中信收款帳號開通流程
jgb/E/ctbc-form-validation｜中國信託申請表單各欄位有什麼格式限制？（聯絡電話 10 碼、銀行代碼 3 碼）｜target_user=property_manager｜中信申請表單欄位限制／聯絡電話要幾碼／銀行帳號要幾碼／銀行代碼幾碼
jgb/E/payment-gateway-withdrawal｜各家金流的款項要怎麼提領？（藍新要自己登入後台辦理，前 5 次免費之後每次 10 元）｜target_user=property_manager,prospect｜藍新款項怎麼提領／藍新提款手續費／收到的錢在哪裡領
jgb/E/payment-onboarding-tax-risk｜線上金流收款會不會有稅務申報風險？（屬稅捐機關與業者自身規劃，系統不判斷）｜target_user=property_manager,prospect｜金流收款稅務風險／線上收款要報稅嗎／資金流向申報
jgb/E/cash-payment-account-management｜「現金收款帳戶」怎麼管理？（可以新增、編輯、移除；需要收款設置編輯權限）｜target_user=property_manager｜現金收款帳戶怎麼設定／現金收款帳戶可以刪除嗎／常用收款帳戶管理

## F 修繕 {#F}
scope: 報修、派工、進度與狀態、修繕通知；⛔ 費用入帳歸 E
### F-repair-list 修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存） {#F-repair-list}
jgb/F/repair-status-tabs｜修繕單總表有哪些狀態分頁？（申請修繕、安排修繕、完成修繕、結單、封存）｜target_user=property_manager,prospect｜修繕單有幾個狀態／修繕單分頁有哪些／修繕進度分幾個階段／修繕總表怎麼分類
jgb/F/repair-list-search-filter｜修繕單總表可以怎麼搜尋或篩選？（案名／地址／經理人／租客關鍵字，加上單一組「修繕單時間段」下拉：報修時間起訖／最後更新時間起訖／7 日內申請報修三選一，還有分類／項目／是否緊急）｜target_user=property_manager｜修繕單怎麼搜尋／修繕單列表篩選條件／怎麼找特定物件的修繕單／修繕單可以用日期篩選嗎／修繕單篩選條件怎麼重設
jgb/F/repair-list-columns｜修繕單總表的表格欄位顯示什麼？（物件地址、分類＆項目、報修日期、最後更新、結算金額、房東/管理者、租客）｜target_user=property_manager｜修繕單列表欄位說明／修繕單表格看得到什麼／修繕單總表欄位
jgb/F/repair-list-sort-and-pagination｜修繕單總表怎麼排序、一頁看幾筆？（每頁 30／60／90 筆可選；排序選項裡的「結算金額」只有房東方帳號才看得到）｜target_user=property_manager｜修繕單一頁顯示幾筆／修繕單可以怎麼排序／租客可以用金額排序修繕單嗎
jgb/F/repair-create-button-visibility｜「新增修繕單」按鈕誰看得到？（租客一定有；房東方要有「新增&編輯&刪除所屬」或「新增&編輯&刪除所有」修繕資料其中一項權限）｜target_user=property_manager｜新增修繕單按鈕在哪／誰可以新增修繕單／為什麼看不到新增修繕單按鈕
jgb/F/repair-total-visibility｜「結算總金額」是什麼？（只有房東方帳號登入時才會顯示；這個數字只加總目前這一頁看得到的修繕單，換頁或換每頁筆數就會不一樣）｜target_user=property_manager｜修繕單結算總金額／誰看得到修繕總金額／結算總金額是全部加起來的嗎
jgb/F/repair-export-visibility｜誰能匯出修繕單？（要另外有匯出修繕資料的權限；而且這顆按鈕只有在「新增修繕單」按鈕會出現的身分底下才會一起出現，單獨有匯出權限而沒有編輯權限的房東方帳號看不到它）｜target_user=property_manager｜怎麼匯出修繕單／修繕單可以匯出嗎／有匯出權限但看不到匯出按鈕
jgb/F/repair-move-status-from-list｜修繕單總表怎麼切換狀態？（每列右邊的齒輪選單有「移至」各個狀態的選項，封存後仍然可以再移回其他狀態）｜target_user=property_manager｜修繕單怎麼換分頁／怎麼把修繕單移到結單／修繕單狀態怎麼改／封存的修繕單可以移回來嗎
jgb/F/repair-view-only-roles｜哪些身分會看到「查看」而不是「編輯＆查看」的齒輪按鈕文字？（大房東角色，以及對這張單只有「顯示所屬」、沒有「顯示所有」修繕資料權限的團隊成員；但這張單的經理人本人看到的仍是「編輯＆查看」）｜target_user=property_manager｜大房東可以改修繕單嗎／誰只能看修繕單／查看跟編輯有什麼差別／為什麼列表裡少了幾張修繕單
jgb/F/repair-list-filter-category-item-urgent｜修繕單總表可以用分類、項目、是否緊急篩選嗎？（可以；先選分類才能選項目，換分類會把已選的項目清空；「是否緊急」是一個勾選框，勾了才會加上這個條件）｜target_user=property_manager｜修繕單怎麼用分類篩選／修繕單搜尋可以選項目嗎／怎麼只看緊急修繕單／分類項目篩選怎麼用
jgb/F/repair-list-contact-card｜修繕單總表點「房東/管理者」或「租客」欄位會怎樣？（會彈出這個人的聯絡資訊卡）｜target_user=property_manager｜點房東管理者欄位會怎樣／修繕單列表點租客會出現什麼／怎麼看修繕單相關人的聯絡方式
### F-repair-apply 報修申請流程 {#F-repair-apply}
jgb/F/repair-apply-flow-and-entry｜怎麼申請修繕單？（房東方從【修繕管理】>【修繕單總表】、租客從【我的報修】>【修繕單總表】右上角「新增修繕單」進入，選物件→選分類項目→填報修細節→送出，按「上一步」「下一步」在步驟間切換）｜target_user=property_manager｜怎麼新增修繕單／怎麼報修／申請修繕流程／修繕單申請入口在哪
jgb/F/repair-apply-without-contract｜沒有租約在跑的物件也能申請修繕嗎？（可以，房東方只要建好物件就能申請，不用先有合約）｜target_user=property_manager,prospect｜空屋可以報修嗎／沒租客的房子能修繕嗎／申請修繕要先有合約嗎
jgb/F/repair-apply-category-item-other｜報修分類項目怎麼選？（分類與項目都是系統設定的清單，選好之後在報修細節可以按「編輯」回上一步重選；有一個特定分類會多出讓使用者自己輸入名稱的欄位）｜target_user=property_manager｜修繕項目沒有我要的怎麼辦／報修分類怎麼選／自訂修繕項目名稱
jgb/F/repair-apply-detail-fields｜報修細節要填什麼？（項目分類、問題必填；預約時段依身分決定是否必填；緊急修繕、佐證照片、備註選填；「通知及同步租客」是房東代租客申請時會看到的一個開關，但目前沒有實際作用）｜target_user=property_manager｜修繕單要填哪些資料／報修細節必填欄位／申請修繕表單欄位
jgb/F/repair-apply-reservation-slots｜預約時段規則是什麼？（畫面上標示為必填，但實際上只有租客身分申請時系統才會擋下沒填的情況；房東申請時就算不填也能送出）｜target_user=property_manager｜修繕預約時段怎麼填／租客要選維修時間嗎／可以約幾個修繕時段
jgb/F/repair-apply-photo-limit｜報修可以附照片或影片嗎？（照片最多 10 張；影片最長 30 秒或 100MB；支援 jpeg／jpg／png 圖片與 mov／mp4／webm 影片）｜target_user=property_manager,prospect｜報修可以傳照片嗎／修繕單附件限制／報修影片大小限制／修繕照片幾張
jgb/F/repair-apply-notifications｜新增修繕單後誰會收到通知？（租客送出時通知房東方；房東方在網頁上建立時只寄 Email 給房東方，租客不會收到通知）｜target_user=property_manager,prospect｜申請修繕會通知誰／報修後誰會知道／修繕單送出通知
jgb/F/repair-notifications-by-stage｜安排廠商、完成修繕、結單時還會發哪些通知？（租客只有在這張修繕單會通知租客時才收得到；結單只寄 Email）｜target_user=property_manager｜安排修繕會通知租客嗎／完成修繕後誰會知道／修繕單結單會通知誰
### F-repair-edit 修繕單編輯 {#F-repair-edit}
jgb/F/repair-edit-progress-timeline｜修繕單細節頁的進度時間軸顯示什麼？（申請修繕、安排修繕、完成修繕、結單、封存五個階段，以及各階段對應的日期）｜target_user=property_manager｜修繕單進度怎麼看／修繕單細節頁面／修繕單時間軸
jgb/F/repair-edit-print｜修繕單細節頁怎麼列印？（右上角有「列印」按鈕，會叫出瀏覽器內建的列印視窗，可以印出來或存成 PDF）｜target_user=property_manager｜修繕單怎麼列印／修繕單可以存成 PDF 嗎
jgb/F/repair-edit-switch-status｜修繕單細節頁怎麼切換狀態？（下拉選單直接選要換到哪個階段，按「變更」儲存）｜target_user=property_manager｜修繕單細節頁怎麼改狀態／怎麼在修繕單裡面切換階段／細節頁的狀態下拉選單怎麼用／選了狀態沒按變更會生效嗎
jgb/F/repair-edit-cannot-edit-roles｜誰不能編輯修繕單細節頁？（租客帳號、大房東角色不能切換狀態、不能改廠商資訊、不能寫房東備註；租客只能編輯自己的房客備註）｜target_user=property_manager｜租客可以改修繕單嗎／大房東可以編輯修繕單嗎／誰能改修繕單內容
jgb/F/repair-edit-application-detail-readonly｜修繕單細節頁顯示哪些報修時填的資料？（「細節補充」區塊底下：申請日期、是否緊急、照片、聯絡電話或 Email、物件區域與時區、分類項目、問題、備註、預約時段；房東方才看得到「細節補充」這個標題與說明文字）｜target_user=property_manager｜修繕單細節頁看得到什麼／修繕單申請內容在哪看／細節補充是什麼／報修資料能不能在細節頁改
jgb/F/repair-edit-vendor-assign｜怎麼安排修繕廠商？（填寫修繕時間、廠商名稱、維修人員、聯絡電話，儲存後會留下歷史紀錄可以展開查看）｜target_user=property_manager｜怎麼填廠商資訊／修繕單怎麼指派維修人員／廠商聯絡資料怎麼填
jgb/F/repair-edit-landlord-complete-memo｜「房東備註」要填什麼？（完成時間、備註文字最多 300 字、可以附照片，最多 10 張、單檔最大 10MB、支援 JPG／PNG／PDF；只有有編輯權限的房東方帳號能編輯）｜target_user=property_manager｜房東備註在哪填／房東備註可以放照片嗎／備註字數限制多少
jgb/F/repair-edit-amount-visibility｜修繕結算金額在哪裡填、誰看得到？（在「完成修繕」的「房東備註」編輯模式填；「結算金額」欄位只有身分是房東的帳號才會顯示，租客看不到；填了金額不會自動產生帳單）｜target_user=property_manager｜修繕結算金額怎麼填／完成修繕怎麼登記費用／修繕金額會變成帳單嗎／修繕結算金額誰看得到
jgb/F/repair-edit-tenant-memo｜「房客備註」是什麼？（右邊那一欄，放租客的備註文字與照片，只有租客自己能編輯；從網頁建立的修繕單都會顯示這一欄）｜target_user=property_manager｜房客備註在哪／修繕單為什麼沒有房客備註／租客可以留言嗎
jgb/F/repair-edit-share-to-vendor｜怎麼把修繕單分享出去給廠商？（在修繕單細節頁點「分享」，電腦上可以複製連結或用 LINE 分享，手機上會直接叫出手機的分享選單；廠商點開連結不需要登入 JGB 帳號）｜target_user=property_manager｜修繕單怎麼分享給廠商／怎麼把修繕單傳給水電行／修繕單連結怎麼複製
### F-repair-share 修繕單分享頁 {#F-repair-share}
jgb/F/repair-share-public-link｜修繕單分享頁需要先登入嗎？（不需要，這個連結是公開的，系統特別把它排除在登入檢查之外，任何拿到網址的人都可以直接打開）｜target_user=property_manager,prospect｜修繕分享連結要登入嗎／修繕單連結廠商打得開嗎／分享頁需要帳號嗎／修繕分享連結是公開的嗎
jgb/F/repair-share-visibility-summary｜分享連結誰看得到？（金額只有在瀏覽者本人目前登入身分是房東時才會顯示，且不會核對是不是這張修繕單相關的房東或租客）｜target_user=property_manager,prospect｜分享連結誰都能看嗎／修繕分享頁會外流個資嗎／分享頁看得到金額嗎
jgb/F/repair-share-no-expiry｜分享連結會過期嗎？（目前不會，沒有天數限制）｜target_user=property_manager｜修繕分享連結會過期嗎／修繕單連結多久失效／分享連結有效期限
jgb/F/repair-share-content｜修繕單分享頁看得到什麼？（修繕申請單標題與是否緊急、照片、報修細節、安排的廠商資訊、房東備註與房客備註，全部都是唯讀；不會顯示物件廣告連結、縮圖，也沒有房東／承租方資訊側欄）｜target_user=property_manager｜分享頁看得到什麼／修繕單連結打開會看到什麼／廠商點連結能看到哪些資訊

## G 裝置（IoT） {#G}
scope: IoT 門鎖、密碼、裝置廠商與狀態；⛔ 抄表歸 E
### G-power-meter 電表列表與單一電表 {#G-power-meter}
jgb/G/power-meter-list-category-tabs｜電錶清單怎麼切換分類？（所有電錶、一般型、儲值型三個分類，切換後會換一批列表）｜target_user=property_manager｜電錶清單怎麼切換分類／一般型跟儲值型電錶差在哪裡看／怎麼只看儲值型電錶／電錶分類標籤有哪些
jgb/G/power-meter-list-status-tags｜電錶清單的狀態標籤是什麼意思？（全部／供電中／斷電中／未連線，夾在分類跟清單之間；未連線含未啟用）｜target_user=property_manager｜電錶未連線標籤是什麼意思／未啟用跟未連線一樣嗎／供電中斷電中是什麼標籤／狀態標籤在畫面哪個位置
jgb/G/power-meter-list-search｜電錶清單怎麼用關鍵字搜尋？（可選描述、序號、設備名稱、所屬物件名稱其中一種）｜target_user=property_manager｜電錶清單怎麼搜尋／怎麼找特定的電錶／電錶搜尋範圍有哪些
jgb/G/power-meter-list-sort｜電錶清單怎麼排序？（可依設備描述、目前電度、預計可用電度排序）｜target_user=property_manager｜電錶清單可以排序嗎／電錶列表的排序選單／門鎖清單能排序嗎
jgb/G/power-meter-manufacturer-maintenance｜電錶清單出現「原廠系統維護中」是什麼意思？（維護期間度數不更新、無法儲值）｜target_user=property_manager｜電錶維護中是什麼意思／電錶顯示原廠系統維護中怎麼辦／維護期間可以儲值嗎／電錶度數為什麼不會動
jgb/G/power-meter-vendor-unreachable｜電錶顯示目前連不上廠商怎麼辦？（度數不會更新、儲值送不出去；全站共用連線的廠商業者跟租客都看得到，以團隊帳號連線的廠商只有業者在清單頁看得到）｜target_user=property_manager,tenant｜電錶連不上廠商是什麼意思／為什麼電錶儲值不了／租客看得到連不上廠商的提示嗎／電錶度數為什麼不會更新
jgb/G/power-meter-service-expiry｜電錶顯示「服務到期」怎麼辦？（30 天內到期會提醒續訂；只有業者看得到，只出現在清單頁）｜target_user=property_manager｜電錶服務快到期怎麼辦／電錶帳號到期會怎樣／為什麼有些電錶帳號沒有顯示到期提示／電錶到期提示租客看得到嗎
jgb/G/power-meter-list-row-fields｜電錶清單每一列顯示什麼？（型號序號、目前電度、狀態、所屬物件；儲值型才有預計可用電度與低電度警報）｜target_user=property_manager｜電錶清單有哪些欄位／電錶列表顯示什麼資訊／儲值型電錶跟一般型差在哪／最後連線成功時間是什麼
jgb/G/power-meter-usage-chart-export｜電錶清單列展開後能看什麼？（用電量走勢圖可選 1/7/30/90 天；CSV 只能下載前 90 天）｜target_user=property_manager｜電錶用電量走勢圖去哪看／電錶清單怎麼匯出CSV／用電量圖表可以選幾天／CSV可以下載多久的資料
jgb/G/power-meter-single-edit-tabs｜電錶編輯頁能改什麼？（描述、綁定物件、供電狀態；儲值型另有電錶資料頁籤，帳號開通自動開立發票時還有開立發票頁籤；租客只能看不能改）｜target_user=property_manager｜電錶編輯頁可以改什麼／電錶設定有哪些頁籤／電錶怎麼改描述／電錶發票設定在哪／一般型電錶編輯頁有電錶資料頁籤嗎
jgb/G/power-meter-single-estate-single-bind｜一支電錶只能綁一個物件？（選擇物件的挑選頁是單選，選了一個之後其他物件會被鎖住不能再選）｜target_user=property_manager｜電錶可以綁幾個物件／電錶能不能綁多個物件／電錶綁定物件的規則／選擇物件是單選還是可以多選
jgb/G/power-meter-mode-switch｜怎麼切換電錶的供電狀態？（一般型：供電／斷電；儲值型：儲值／強開／斷電，切換中鎖按鈕只有儲值型有）｜target_user=property_manager｜電錶怎麼斷電／怎麼切換電錶模式／強開模式是什麼／電錶切換中不能點是為什麼
jgb/G/power-meter-basic-info-fields｜電錶資料頁的餘額、費率、預計可用電度怎麼看？（只有儲值型電錶才有這個頁籤；費率由雲端儲值系統設定，可用電度＝餘額÷費率）｜target_user=property_manager｜電錶餘額怎麼看／電錶費率是誰設定的／預計可用電度怎麼算／電號在哪裡查
jgb/G/power-meter-topup-flow｜電錶怎麼儲值？（「儲值」按鈕就在清單列上，不用展開；金額固定四個選項，維護中或連不上廠商時按鈕會變灰）｜target_user=property_manager｜電錶怎麼儲值／儲值金額可以自己輸入嗎／儲值後帳單在哪裡看／儲值歷程在哪裡查
jgb/G/iot-entry-requirements｜電錶／門鎖／攝影機／小白盒頁面需要什麼條件才能進入？（房東方要有生效中的訂閱，而且方案有開放智能裝置功能；租客不受限制）｜target_user=property_manager,prospect｜電錶頁面打不開／門鎖頁面顯示需要訂閱／IoT 功能需要訂閱方案嗎／方案沒有智能裝置功能會怎樣
jgb/G/power-meter-invoice-tab-fields｜開立發票頁籤裡面能填什麼？（目前只有帳單是否開立發票一個選項）｜target_user=property_manager｜開立發票頁籤能填什麼／電錶發票要怎麼設定統編／帳單開立發票是哪個選項
jgb/G/power-meter-list-empty-state｜電錶清單沒有資料時畫面顯示什麼？（分類內沒有設備寫「此分類尚無設備」；完全沒綁定寫「目前尚無綁定設備」，租客看不到綁定引導連結）｜target_user=property_manager｜電錶清單沒有資料會顯示什麼／此分類尚無設備是什麼意思／目前尚無綁定設備怎麼處理
### G-device-page 裝置頁（門鎖、攝影機、小白盒） {#G-device-page}
jgb/G/device-page-shared-list｜門鎖／攝影機／小白盒清單長什麼樣？（型號序號、描述、狀態、所屬物件四欄，可依關鍵字搜尋）｜target_user=property_manager,prospect｜門鎖清單長怎樣／攝影機列表有哪些欄位／小白盒怎麼看清單／裝置清單怎麼搜尋
jgb/G/device-page-lock-open-close｜門鎖清單怎麼直接開門／鎖門？（開門一定有、鎖門只有特定廠商支援；離線時按鈕不會顯示）｜target_user=property_manager｜門鎖怎麼直接開門／怎麼在清單上鎖門／為什麼我的門鎖沒有鎖門按鈕／門鎖離線還能操作嗎
jgb/G/device-edit-tabs-by-type｜裝置編輯頁的頁籤，門鎖跟攝影機／小白盒不一樣？（門鎖多出密碼設定、開門記錄兩個頁籤）｜target_user=property_manager｜攝影機編輯頁有哪些頁籤／門鎖設定頁籤有哪些／小白盒可以改密碼嗎／裝置編輯頁功能
jgb/G/device-lock-type-and-binding-limit｜私人門鎖跟共用門鎖差在哪？（私人只能綁一個物件，共用可以綁多個）｜target_user=property_manager,prospect｜私人門鎖跟共用門鎖差別／門鎖可以綁幾間房／共用門鎖是什麼／門鎖類型怎麼選
jgb/G/device-lock-passwords-three-types｜門鎖密碼有哪三種？（房東個人密碼、租客個人密碼、租客共用密碼，權限各不同）｜target_user=property_manager｜門鎖密碼有幾種／租客密碼房東能改嗎／共用密碼是什麼／門鎖密碼設定規則
jgb/G/device-lock-open-log｜門鎖的開門記錄怎麼看？（可依日期查詢操作時間與動作，沒有記錄時會顯示尚無記錄）｜target_user=property_manager｜門鎖開門記錄在哪裡看／怎麼查門鎖歷史紀錄／開門記錄有哪些欄位
jgb/G/device-gateway-not-counted｜小白盒綁定物件跟門鎖不同在哪？（小白盒不會讓物件被標記為「IoT裝置」，也不會擋刪除）｜target_user=property_manager｜小白盒是什麼／小白盒綁物件有差嗎／物件為什麼沒顯示IoT裝置標籤／物件刪不掉是不是因為有綁裝置
### G-remote-unlock 遠端解鎖（輸入解鎖密碼開門） {#G-remote-unlock}
jgb/G/remote-unlock-page｜遠端解鎖連結怎麼用？（輸入共用密碼按開門，密碼錯誤或連結失效會提示原因）｜target_user=property_manager｜遠端解鎖連結怎麼用／收到開門連結要怎麼開門／解鎖密碼輸入錯誤會怎樣／這個開門連結為什麼失效／遠端解鎖連結怎麼產生
jgb/G/remote-unlock-no-login｜遠端解鎖連結需要登入嗎？（不用登入，只要有連結跟密碼就能開）｜target_user=property_manager,prospect｜遠端解鎖要登入嗎／開門連結免登入嗎／沒有帳號可以開門嗎

## H 幫助中心 {#H}
scope: 幫助中心入口與使用方式、教學文件位置；⛔ 各功能怎麼用歸該功能所在架（目前空架，存廢另裁）
### H-help-center 幫助中心（分類、文章、搜尋） {#H-help-center}
jgb/H/help-center-home-groups｜幫助中心首頁長什麼樣？（分類卡片顯示圖示、篇數、更新日期）｜target_user=property_manager,prospect｜幫助中心首頁有什麼／幫助中心分類怎麼看／幫助中心怎麼進去／幫助中心有哪些分類
jgb/H/help-center-group-structure｜幫助中心分類頁怎麼排文章？（分類底下先分次分類，各次分類再列出文章卡片）｜target_user=property_manager,prospect｜幫助中心分類頁長怎樣／幫助中心文章怎麼分組／幫助中心次分類是什麼
jgb/H/help-center-post-detail｜幫助中心文章內頁有什麼？（麵包屑、分享到 Facebook／LINE、上下篇導覽、相關文章）｜target_user=property_manager,prospect｜幫助中心文章怎麼分享／文章頁有上一篇下一篇嗎／文章內頁長什麼樣／怎麼回到分類列表
jgb/H/help-center-search｜幫助中心搜尋怎麼運作？（比對標題與內文、多個關鍵字要同時出現、可加選分類）｜target_user=property_manager,prospect｜幫助中心搜尋規則／幫助中心搜不到文章怎麼辦／幫助中心可以打多個關鍵字嗎／幫助中心搜尋能限定分類嗎
jgb/H/help-center-trial-form｜幫助中心的「立即免費試用」視窗是什麼時候跳出來的？（首頁停留 60 秒自動彈出，四個欄位都要填）｜target_user=property_manager,prospect｜幫助中心會跳出試用視窗嗎／免費試用視窗要填什麼／怎麼關掉試用彈窗／免費試用天數

## I 方案與導入 {#I}
scope: 方案比較與試用、功能矩陣、導入與資料遷移、批次匯入流程、競品（deliberate_no）；⛔ 找真人走 handoff
### I-pricing 方案、價格與免費試用 {#I-pricing}
jgb/I/pricing-plan-tiers-overview｜JGB 有哪些方案？（免費試用、體驗方案、入門／熱門／專業四級距、企業方案）｜target_user=property_manager,prospect｜有哪些方案／方案分幾種／方案怎麼選／價格方案介紹／哪個方案適合我
jgb/I/pricing-free-trial-eligibility｜免費試用怎麼開始、能用多久？（一個週期後不自動續訂）｜target_user=property_manager,prospect｜免費試用能用多久／怎麼取得免費試用／免費方案會自動續訂嗎／試用期多長
jgb/I/pricing-free-trial-feature-scope｜免費試用不能用哪些功能？（最多 5 個物件，不支援團隊與門鎖電錶等進階功能）｜target_user=property_manager,prospect｜免費方案有什麼限制／免費試用不能用什麼功能／免費方案物件上限／免費試用支援哪些功能
jgb/I/pricing-individual-vs-corporate-team｜個人房東與企業團隊方案差在哪？（團隊成員管理等四項功能、自動對帳與分店管理起始級距不同）｜target_user=property_manager,prospect｜個人房東跟團隊方案差別／團隊方案多什麼功能／企業團隊方案內容／個人跟公司方案不一樣嗎
jgb/I/pricing-free-vs-experience-plan｜免費方案與體驗方案差在哪？（前者系統贈送，後者付費訂閱、可選月繳或年繳，可建 10 個物件並自行續訂）｜target_user=property_manager,prospect｜免費方案跟體驗方案差在哪／免費方案跟體驗方案哪裡不同／體驗方案是免費的嗎／免費方案可以續訂嗎
jgb/I/pricing-calc-by-estate-count｜怎麼用物件數量試算方案價格？（50～500 物件拉桿試算，超過 500 個要洽企業方案）｜target_user=property_manager,prospect｜怎麼算方案價格／物件數量怎麼換算價格／我有幾間房適合哪個方案／價格試算工具
jgb/I/pricing-quota-near-full-notice｜物件額度快滿了會怎樣？（剩 5 個以下觸發提醒，剛好剩 5 個另寄 Email）｜target_user=property_manager｜物件額度快滿了會通知嗎／物件數量快到上限怎麼辦／方案物件用完前有提醒嗎／額度不夠怎麼知道
jgb/I/pricing-enterprise-plan-offer｜企業方案提供什麼？（客製化 LOGO 頁與網址頁，需另外聯繫洽談）｜target_user=property_manager,prospect｜企業方案內容／企業方案怎麼申請／大型企業方案／客製化方案怎麼談
jgb/I/pricing-trial-plan-landing-page｜體驗方案介紹頁講什麼？（每月費用試算、體驗方案資格需求、客戶見證、免費試用／免費諮詢按鈕）｜target_user=property_manager,prospect｜體驗方案介紹頁／體驗方案要多少錢／體驗方案資格需求／查看體驗方案會看到什麼
jgb/I/pricing-plan-price-basis｜方案價格怎麼算？（各方案單價從系統價格表讀取）｜target_user=property_manager,prospect｜方案價格數字／體驗方案價格怎麼算／方案價格從哪裡算出來
jgb/I/pricing-quota-full-block｜物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案）｜target_user=property_manager｜物件額度用滿了／額度滿了不能新增物件／訂閱失效還能新增物件嗎／方案額度用完提示
jgb/I/pricing-landlord-initial-plan｜建立房東身分時會拿到什麼方案？（企業團隊與社宅房東自動取得免費方案；個人房東一般也是，透過特定優惠或行銷活動連結註冊時則取得活動指定的方案）｜target_user=property_manager,prospect｜註冊後會拿到什麼方案／新帳號有送方案嗎／用優惠連結註冊會拿到什麼方案
### I-subscription-payment 訂閱、付款與訂單 {#I-subscription-payment}
jgb/I/subscription-choose-plan-flow｜訂閱頁怎麼選方案？（體驗方案、依物件數量拉桿的基本方案、企業方案洽談三選一）｜target_user=property_manager｜訂閱頁怎麼選方案／怎麼變更訂閱方案／選方案時可以選幾種／方案物件數量怎麼拉
jgb/I/subscription-payment-authorization-flow｜訂閱怎麼扣款？（先試刷 TWD 1 驗證信用卡、藍新金流走 SSL／PCI-DSS）｜target_user=property_manager,prospect｜訂閱怎麼付款／訂閱扣款安全嗎／信用卡驗證怎麼跑／確認扣款會怎樣
jgb/I/subscription-invoice-fields｜訂閱時發票資訊要填什麼？（二聯式／三聯式、統一編號僅三聯式必填；地址欄目前沒有掛必填檢查）｜target_user=property_manager｜訂閱發票怎麼填／二聯式三聯式差在哪／統一編號要填嗎／訂閱要留Email跟電話嗎
jgb/I/subscription-coupon-and-renewal-discount｜訂閱優惠碼怎麼用？（輸入後即時驗證，續訂優惠次數沒有設定上限時顯示「終生」）｜target_user=property_manager｜訂閱優惠碼怎麼輸入／優惠碼兌換／續訂優惠次數／續訂優惠可以用多久
jgb/I/subscription-my-plan-page｜我的方案頁看什麼？（方案卡片、付款方式綁定狀態、溢繳費用）｜target_user=property_manager｜我的方案頁面內容／怎麼看目前訂閱方案／溢繳費用是什麼／付款方式在哪裡看
jgb/I/subscription-change-card-flow｜怎麼換綁信用卡？（更新要重新授權並試刷 1 元，變更方案按鈕需要對應權限）｜target_user=property_manager｜怎麼換綁信用卡／更換信用卡要重新授權嗎／沒有權限可以變更方案嗎／變更按鈕按不下去
jgb/I/subscription-plan-change-billing｜換方案時舊方案沒用完的錢會退嗎？（按剩餘天數比例換算成溢繳金，直接折抵新方案費用）｜target_user=property_manager｜升級方案舊方案的錢退嗎／降級方案會退費嗎／溢繳金怎麼算／換方案生效時間
jgb/I/subscription-cancel-effect｜取消訂閱會怎樣？（立即停止自動續訂與已授權信用卡，但用到目前效期結束才失效）｜target_user=property_manager｜取消訂閱馬上失效嗎／取消訂閱要選原因嗎／取消訂閱後還能用多久／怎麼取消訂閱
jgb/I/subscription-renewal-charge-failure｜自動續訂扣款失敗會怎樣？（方案資料整個清空、限額歸零、所有物件立即下架，沒有寬限期）｜target_user=property_manager｜續訂扣款失敗怎麼辦／自動續約失敗會下架物件嗎／沒有信用卡授權會怎樣／續訂失敗有寬限期嗎
jgb/I/orders-payment-history｜付款紀錄頁看什麼？（扣款日、訂單編號、付款內容、金額、收據）｜target_user=property_manager｜付款紀錄在哪裡看／訂單紀錄怎麼查／收據在哪裡下載／扣款紀錄列表
jgb/I/payment-vendor-options-overview｜收款設置支援哪些金流商？（藍新／國泰世華／永豐／中信／icash Pay／現金收款帳戶，各家設定費與手續費不同）｜target_user=property_manager｜收款設置支援哪些金流／線上收款要收多少費用／金流申請要錢嗎／手續費可以轉嫁給租客嗎
jgb/I/payment-vendor-eligibility-by-role-and-plan｜哪些身分或方案不能開通某些金流商？（個人房東不能開藍新／國泰世華／永豐，免費方案／體驗方案不能開國泰世華／永豐）｜target_user=property_manager｜個人房東能開藍新嗎／免費方案能開國泰世華嗎／金流商為什麼不能選／收款方式被鎖住怎麼辦
jgb/I/payment-newebpay-setup-details｜藍新金流申請要注意什麼？（個人房東無法申請；手機與 Email 送出後不能改，每個金流最多開三組帳號，需審核）｜target_user=property_manager｜藍新金流怎麼申請／藍新申請資料能改嗎／金流最多能開幾組帳號／藍新審核要多久
jgb/I/payment-vendor-edit-after-binding｜金流綁定後還能改嗎？（綁定資料都是唯讀；國泰世華只能補填還沒填齊的超商條碼欄位）｜target_user=property_manager｜收款方式可以改嗎／金流明細可以編輯嗎／綁定後想改資料怎麼辦／哪個金流可以重新送審
jgb/I/payment-icash-ctbc-setup｜藍新／中信收款帳戶申請要多久？（藍新：智付通至少 2-5 個工作天；中信 ACH 驗證約 5 個工作天）｜target_user=property_manager｜藍新申請要多久／中信收款帳戶審核多久／智付通開通要多久／ACH驗證是什麼
jgb/I/payment-receipt-template-options｜收據範本有哪些？（財政部包租業租金收據範本只有法人／社宅團隊才看得到）｜target_user=property_manager｜收據範本有哪些／財政部範本怎麼設定／一般收據怎麼選／收據要不要開通
jgb/I/payment-receipt-deposit-team-extras｜押金收據能自訂摘要跟蓋章嗎？（摘要與三顆收款章都只有特定合作團隊才看得到）｜target_user=property_manager｜押金收據摘要怎麼改／收據可以蓋章嗎／押金收據印章設定／押金收據字數上限
jgb/I/payment-bill-e-invoice-setup｜帳單怎麼開電子發票？（要先聯繫 JGB 業務開通加值服務，開通後才會出現稅與發票分頁）｜target_user=property_manager,prospect｜帳單怎麼開發票／電子發票怎麼啟用／合約怎麼設定要不要開發票／發票功能怎麼申請
jgb/I/payment-permission-menu-visibility｜沒有查看權限會怎樣？（收款設置與訂閱方案選單整個不會出現）｜target_user=property_manager｜沒有權限看不到收款設置／訂閱方案選單不見了／為什麼找不到訂閱方案／查看訂閱方案權限的作用
jgb/I/payment-bill-autosend-and-recipient｜帳單可以自動排程發送、指定收款人嗎？（提前 0～20 天自動發送，收款人可選原簽約者／主要經理人／自訂）｜target_user=property_manager｜帳單自動發送設定／帳單提前幾天發送／帳單收款人怎麼設定／收款人可以改成別人嗎
### I-demo-booking 預約 demo {#I-demo-booking}
jgb/I/demo-form-fields｜預約 demo 表單要填什麼？（公司名稱、職稱、姓名、電話、Email、物件所在地、物件數量、團隊人數、最有興趣的功能、諮詢內容，並勾選同意隱私權政策）｜target_user=property_manager,prospect｜預約demo要填什麼／怎麼申請demo／聯繫我們表單欄位／demo表單怎麼填
jgb/I/demo-form-option-lists｜demo 表單的下拉選項有哪些？（物件數量 7 級距、團隊人數 6 級距、感興趣功能 6 項）｜target_user=property_manager,prospect｜物件數量選項有哪些／團隊人數怎麼選／感興趣功能有哪些選項／demo表單職稱選單
jgb/I/demo-form-submit-result｜demo 表單送出後多久有人聯繫？（顯示感謝頁，2-3 個工作天內專人聯繫）｜target_user=property_manager,prospect｜demo表單送出後多久聯繫／預約demo後會怎樣／填完表單多久有人回覆／demo表單送出成功畫面
jgb/I/demo-form-actual-validation-scope｜demo 表單漏填欄位時，系統端會擋下哪些？（送出後系統端只檢查公司名稱、姓名、電話、Email 四項，其餘欄位空白不會被系統端退回）｜target_user=property_manager｜demo表單哪些欄位真的必填／實際驗證跟畫面要求一樣嗎／demo表單漏填會怎樣／demo表單驗證規則
### I-control-panel 控制台（設定、通知信範本、自動化任務） {#I-control-panel}
jgb/I/control-panel-entry-scope｜控制台首頁目前能用什麼？（目前只有「任務管理器」一個項目可以點擊進入，而且只開放給特定合作團隊）｜target_user=property_manager｜控制台有什麼功能／控制台首頁能做什麼／控制台目前可以用哪些設定
jgb/I/control-panel-setting-shell｜進入控制台設定後看到什麼？（上方三層麵包屑與左側「控制台」側邊欄，內容是任務管理器、新增／編輯任務或通知信設定頁）｜target_user=property_manager｜控制台設定頁內容／任務管理器上一層是什麼／控制台麵包屑／控制台側邊欄
jgb/I/task-manager-purpose｜任務管理器是做什麼用的？（設定週期性任務或預定通知的排程功能）｜target_user=property_manager｜任務管理器是什麼／自動化任務怎麼運作／排程機器人是什麼／任務管理器用途
jgb/I/task-manager-type-behavior-scope｜新增任務能選哪些類型？（目前只開放「通知」類型，行為是信件通知或站內通知）｜target_user=property_manager｜任務類型有哪些／任務行為可以選什麼／可以設定修繕單自動開單嗎／通知任務怎麼設定
jgb/I/task-manager-cycle-options｜任務週期怎麼設定？（單位分年／月，方式可選僅一次、持續不停、特定日期結束、重複特定次數）｜target_user=property_manager｜任務週期怎麼設定／任務可以只跑一次嗎／任務可以設定結束日期嗎／任務重複次數怎麼設定
jgb/I/task-manager-form-fields｜新增任務表單有哪些欄位？（任務名稱、任務類型、關聯物件、任務行為、任務時間、重複間隔、結束時間、通知對象、通知內容）｜target_user=property_manager｜新增任務要填哪些欄位／任務表單內容／關聯物件怎麼選／通知對象怎麼設定
jgb/I/task-manager-edit-delete-copy｜已建立的任務怎麼編輯／刪除？（每筆任務可編輯、複製、刪除，編輯週期任務可選只改這次或連後續一起改）｜target_user=property_manager｜任務可以刪除嗎／任務可以複製嗎／編輯週期任務會影響後續任務嗎／任務列表可以做什麼操作
jgb/I/notification-mail-settings｜通知信副本信箱可以設定嗎？（可以：會員側欄「通知收件信箱」頁每個通知類別最多再加 3 組；控制台裡的「通知信設定」頁只有說明、沒有新增欄位，也沒有入口）｜target_user=property_manager｜通知信副本信箱怎麼加／通知信可以加幾個收件人／通知信預設寄給誰／通知信設定在哪裡／通知收件信箱在哪裡
jgb/I/control-panel-access-restriction｜誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定」子路徑才會擋）｜target_user=property_manager｜誰可以用控制台／租客可以設定任務管理嗎／控制台權限限制／為什麼進不去控制台
### I-marketing-home 官網首頁 {#I-marketing-home}
jgb/I/homepage-sections-overview｜官網首頁有哪些區塊？（橫幅、熱門物件、優質租管業者推薦、特色介紹、企業夥伴、最新消息）｜target_user=prospect｜首頁有什麼內容／官網首頁架構／JGB官網首頁介紹
jgb/I/homepage-ten-features-actual-count｜首頁「JGB平台十大特色」實際列出幾項？（標題寫十大，目前輪播只設定 3 項：管理儀表板、線上合約管理、即時帳務報表）｜target_user=prospect｜JGB平台十大特色有哪些／首頁特色介紹內容／十大特色是哪些功能
jgb/I/homepage-city-count-cta｜首頁說 JGB 在東南亞幾個城市使用？（超過 8 個城市，旁邊有免費試用／免費諮詢按鈕）｜target_user=prospect｜JGB服務幾個城市／首頁城市數字／JGB東南亞據點／首頁免費試用按鈕在哪
jgb/I/homepage-presales-assistant-visibility｜首頁的線上諮詢小幫手正式站看得到嗎？（目前設定為正式環境不顯示，只在非正式環境出現）｜target_user=property_manager｜首頁有線上客服小幫手嗎／官網有聊天機器人嗎／為什麼官網看不到諮詢小幫手
jgb/I/homepage-three-advantages｜首頁「JGB平台擁有三大優勢」是哪三項？（提高出租效率、自動化管房流程、提升租客服務品質）｜target_user=prospect｜JGB三大優勢是什麼／首頁三大優勢介紹／JGB平台優勢
jgb/I/homepage-latest-news-section｜首頁「最新消息」顯示什麼？（用輪播呈現消息，點擊會開啟幫助中心文章）｜target_user=prospect｜首頁最新消息在哪／最新消息點進去是什麼／首頁消息輪播
jgb/I/homepage-enterprise-partners-section｜首頁「企業夥伴」放了什麼？（10 個合作夥伴 logo 排成靜態方格，不是輪播）｜target_user=prospect｜企業夥伴是誰／首頁合作夥伴logo／企業夥伴區塊內容
### I-hicloud-order 中華電信雲市集訂單頁 {#I-hicloud-order}
jgb/I/tcloud-order-info-fields｜雲市集訂單頁顯示什麼？（訂單編號、時間、採購方案、價格、點數折抵、付款狀態）｜target_user=property_manager,prospect｜雲市集訂單頁面內容／台灣雲市集訂單資訊／雲市集訂單狀態怎麼看／雲市集訂單點數
jgb/I/tcloud-payment-instructions｜雲市集訂單怎麼付款？（國泰世華一次性虛擬帳號，注意事項請用 WebATM 轉帳；收到匯款資訊後 2 個工作天內付款，款項確認後 2 個工作天內開發票、7 個工作天內開通）｜target_user=property_manager,prospect｜雲市集訂單怎麼繳費／雲市集付款期限／雲市集開通要多久／雲市集虛擬帳號怎麼轉帳
jgb/I/tcloud-link-invalid-cases｜雲市集訂單連結為什麼會失效？（連結簽章驗證不過，或訂單編號查無資料，都會導回官網首頁）｜target_user=property_manager,prospect｜雲市集連結失效／雲市集訂單頁打不開／雲市集付款連結驗證失敗／雲市集訂單查無資料
