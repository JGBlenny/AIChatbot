## A 帳號與身分 {#A}
scope: 註冊、登入、找回帳號、身分（房東／租客／法人／社宅）與個人資料、聯絡方式變更；⛔ 團隊成員權限歸 B
### A-registration 註冊帳號（Email／SSO、驗證碼、手機綁定） {#A-registration}
jgb/A/register-email-steps｜如何註冊 JGB 帳號？（Email、驗證碼、帳號設定三步驟）｜target_user=property_manager,prospect｜
jgb/A/register-tenant-contract-invitation｜租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「註冊」接續完成）｜target_user=property_manager,prospect｜
jgb/A/register-sso｜可以用 Facebook、Google、LINE 註冊嗎？（SSO 仍需完成 Email 綁定）｜target_user=property_manager,prospect｜
jgb/A/register-captcha-expired｜註冊卡在機器人驗證過期怎麼辦？（會退回第一步重新勾選）｜target_user=property_manager｜
jgb/A/register-email-verify-resend｜沒收到 Email 驗證碼怎麼辦？（可重發，發送次數過多會出現等待秒數）｜target_user=property_manager｜
jgb/A/register-password-rule｜註冊密碼格式要求是什麼？（至少 6 碼、須同時包含英文與數字）｜target_user=property_manager,prospect｜
jgb/A/register-email-already-registered｜註冊時 Email 已被註冊過怎麼辦？（系統會將帳號合併）｜target_user=property_manager｜
jgb/A/register-phone-bind｜註冊要綁定手機號碼嗎？（可選填、簡訊驗證、可「下次再驗證」略過）｜target_user=property_manager,prospect｜
jgb/A/register-phone-already-bound｜註冊時發現手機已綁定過怎麼辦？（直接顯示已綁定、按繼續完成流程）｜target_user=property_manager｜
jgb/A/register-role-select｜註冊完之後要選身分嗎？（房東/管理者、租客二選一，可同時擁有兩種身分）｜target_user=property_manager,prospect｜
jgb/A/register-verify-code-shape｜驗證碼輸入畫面長什麼樣子？（識別碼加 4 碼數字，輸入錯誤太多次會被鎖住）｜target_user=property_manager｜
jgb/A/register-email-link-resume｜從驗證信連結折返時會從頭開始註冊嗎？（不會，系統會記住 Email 直接跳到輸入驗證碼畫面）｜target_user=property_manager｜
### A-login 登入 {#A-login}
jgb/A/login-methods｜JGB 有哪些登入方式？（Email、手機號碼、Facebook／Google／LINE）｜target_user=property_manager,prospect｜
jgb/A/login-role-select-before｜登入前為什麼要先選擇身分？（決定進入房東/管理者或租客的登入表單）｜target_user=property_manager,prospect｜
jgb/A/login-phone-country-code｜用手機號碼登入時，國碼與號碼格式有什麼規則？（號碼長度上限與格式依所選國家而定）｜target_user=property_manager,prospect｜
jgb/A/login-remember-me｜「記住我」是做什麼？（只延長登入效期，跟記住登入方式無關）｜target_user=property_manager,prospect｜
jgb/A/login-sso-redirect-no-duplicate-buttons｜從 Facebook／Google／LINE 導回登入頁時，第三方登入按鈕會重複出現嗎？（不會）｜target_user=property_manager,prospect｜
jgb/A/login-role-redirect｜登入時身分選錯了怎麼辦？（會依選擇的身分決定進入哪個角色的登入表單）｜target_user=property_manager｜
jgb/A/login-error｜登入帳號或密碼錯誤時會顯示什麼？｜target_user=property_manager｜
jgb/A/login-forget-password-link｜登入頁的「忘記密碼？」連結在哪裡？（在登入表單下方，點擊前往忘記密碼流程）｜target_user=property_manager｜
jgb/A/login-forget-account-link｜登入頁的「忘記帳號？」連結在哪裡？（在登入表單下方，點擊前往忘記帳號流程）｜target_user=property_manager｜
jgb/A/login-no-account-register-link｜登入頁下面有連到註冊頁的連結嗎？（「還沒有帳號嗎？立即註冊」）｜target_user=property_manager,prospect｜
jgb/A/login-identity-switch｜同一帳號同時有房東與租客身分時怎麼切換？（登入時重新選擇身分，或在帳號資訊設定預設身分）｜target_user=property_manager｜
### A-account-recovery 忘記帳號、忘記密碼 {#A-account-recovery}
jgb/A/forget-account-flow｜忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示）｜target_user=property_manager｜
jgb/A/forget-account-no-phone｜沒綁手機號碼還能用「忘記帳號」找回嗎？（不行，只能靠手機簡訊驗證）｜target_user=property_manager｜
jgb/A/forget-password-flow｜忘記密碼怎麼辦？（Email 或手機任一驗證後即可重設新密碼）｜target_user=property_manager｜
jgb/A/forget-password-setpwd-invite｜「請設定密碼」畫面是什麼情境？（受邀請帳號的初次設定密碼流程）｜target_user=property_manager｜
### A-member-home 會員中心首頁 {#A-member-home}
jgb/A/dashboard-overview-blocks｜會員中心首頁有哪些統計區塊？（即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單）｜target_user=property_manager｜
jgb/A/dashboard-overview-charts｜首頁的圖表看得到什麼？（招租／買賣廣告刊登率圓環圖、收支情況圖）｜target_user=property_manager｜
jgb/A/dashboard-overview-lists｜首頁下方還有哪些列表？（帳單、合約、修繕整合列表，具通知權限者另有 Email 通知紀錄）｜target_user=property_manager｜
jgb/A/dashboard-big-landlord-view｜大房東的首頁畫面和一般房東不一樣嗎？（只顯示物件/社區最新收支詳情與收支圖表，沒有捷徑與四個統計方塊）｜target_user=property_manager｜
jgb/A/dashboard-team-switch｜怎麼在會員中心首頁切換團隊？（左上角下拉選單選擇被加入的團隊）｜target_user=property_manager｜
jgb/A/dashboard-occupancy-tab｜首頁的「滿租率(beta)」頁簽是什麼？（限定開放的社區收入統計，非所有團隊都看得到）｜target_user=property_manager｜
jgb/A/dashboard-shortcuts-list｜首頁「捷徑」區塊有哪些功能？（新增物件、新增合約、新增帳單、新增修繕、查看統計報表、查看大房東列表）｜target_user=property_manager｜
### A-account-profile 帳號資訊 {#A-account-profile}
jgb/A/account-basic-info｜帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂）｜target_user=property_manager｜
jgb/A/account-phone-bind-status｜帳號資訊頁怎麼看手機的綁定狀態？（已綁定／未綁定，未綁定才有「前往綁定」按鈕）｜target_user=property_manager｜
jgb/A/account-email-verify-status｜帳號資訊頁的 Email 驗證狀態怎麼看？（Email 無法自行更改，需聯繫客服）｜target_user=property_manager｜
jgb/A/account-phone-no-change-entry｜手機已經綁定後可以自己更換嗎？（沒有更換入口，只顯示已綁定狀態）｜target_user=property_manager｜
jgb/A/account-sso-status｜帳號資訊頁怎麼看 SSO 綁定狀態？（Facebook／Google／LINE 各自顯示已綁定或未綁定）｜target_user=property_manager｜
jgb/A/account-change-password｜登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼，新密碼規則同註冊）｜target_user=property_manager｜
jgb/A/account-contact-info｜帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話）｜target_user=property_manager｜
jgb/A/account-preference｜帳號資訊頁的偏好設定能設定什麼？（登入預設房東身份、時區、Email 通知語系）｜target_user=property_manager｜
jgb/A/account-progress-unlock｜帳號資訊頁有「資訊完整度」進度條嗎？（目前頁面上不會顯示這個區塊）｜target_user=property_manager,prospect｜
jgb/A/account-save-integrity-check｜帳號資訊頁儲存失敗會提示什麼？（頁面沒有完整載入時會提醒重新整理再儲存）｜target_user=property_manager｜
### A-signer-info 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章） {#A-signer-info}
jgb/A/signer-individual-fields｜個人房東的簽約資訊要填什麼？（姓氏、名稱、身分證字號、Email、手機、身分證正反面）｜target_user=property_manager,prospect｜
jgb/A/signer-corp-fields｜公司身分的簽約資訊要填什麼？（公司名稱、統編、負責人、公司電話/Email、登記證資料）｜target_user=property_manager,prospect｜
jgb/A/signer-corp-seals｜公司身分要上傳哪些印章與證件附件？（公司大章、小章、經紀人章、經紀業章、租賃管理員章）｜target_user=property_manager,prospect｜
jgb/A/signer-broker-manager-fields｜有不動產經紀人／租賃管理人員資格要多填什麼？（經紀人證號、租賃管理人員證號等）｜target_user=property_manager,prospect｜
jgb/A/signer-edit-permission｜簽約資訊誰能編輯？（沒有編輯權限的欄位會顯示為停用樣式）｜target_user=property_manager｜
jgb/A/signer-address-fields｜簽約資訊的地址欄位怎麼填？（戶籍/通訊地址、公司登記/通訊地址皆為必填，可一鍵「同上」）｜target_user=property_manager,prospect｜
jgb/A/signer-multi-entry-switch｜公司名下有多筆簽約對象時要怎麼切換？（表單上方出現切換列，超過 5 筆再加「所有團隊」下拉選單）｜target_user=property_manager｜
jgb/A/signer-manage-save-buttons｜簽約資訊頁的「管理」「儲存」按鈕做什麼？（管理開啟簽約對象管理視窗，儲存只在個人身分頁面出現）｜target_user=property_manager｜
### A-notification-center 通知中心 {#A-notification-center}
jgb/A/notification-center-type-filter｜通知中心怎麼依類型篩選通知？（依合約/帳務/修繕/裝置/其他分類）｜target_user=property_manager｜
jgb/A/notification-center-unread-dot｜通知中心的通知怎麼標示未讀？（列表項目左側的紅點，沒有「只顯示未讀」的篩選功能）｜target_user=property_manager｜
jgb/A/notification-center-per-page｜通知中心每頁顯示筆數可以怎麼調整？（30/60/90 筆，預設 30 筆）｜target_user=property_manager｜
jgb/A/notification-center-permission｜為什麼通知中心是空的？（房東側需要查看通知的權限才看得到通知內容）｜target_user=property_manager｜
jgb/A/notification-mark-read-navigate｜點擊通知列表項目會發生什麼？（前往原連結，並帶上標記已讀的依據）｜target_user=property_manager｜
jgb/A/notification-mark-read-out-of-range｜篩選後頁碼超出範圍會自動跳回第一頁嗎？（寫了判斷式，但實際上永遠不會被觸發）｜target_user=property_manager｜
jgb/A/notification-navbar-bell｜導覽列的通知鈴鐺會顯示什麼？（最近 5 筆通知與未點擊數量，大房東不會顯示）｜target_user=property_manager｜
### A-notification-settings 通知收件設定與發送報表（通知收件信箱最多再加 3 組） {#A-notification-settings}
jgb/A/notification-settings-extra-emails｜通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱）｜target_user=property_manager｜
jgb/A/notification-settings-categories｜通知收件設定有哪些分類？（合約、帳務、修繕、訂閱、房東管理，另有限定開放的加盟分潤報表）｜target_user=property_manager｜
jgb/A/notification-settings-report-buttons｜「發送報表」「多團隊合併報表」按鈕是做什麼的？（限加盟分潤報表分類，多團隊合併僅限特定團隊）｜target_user=property_manager｜
jgb/A/notification-settings-save｜通知收件設定改完怎麼儲存？（至少要有一個分類填了自訂信箱，儲存鍵才會啟用）｜target_user=property_manager｜

## B 團隊、人員與大房東 {#B}
scope: 團隊建立與成員邀請、角色權限、人員管理、大房東記錄與代管關係；⛔ 帳號本身歸 A
### B-team-profile 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊） {#B-team-profile}
jgb/B/team-basic-info｜團隊資訊頁面可以設定什麼？（公司 Logo、團隊名稱、團隊介紹）｜target_user=property_manager,prospect｜
jgb/B/team-ad-contact｜廣告頁聯絡資訊要填什麼？（Line ID、Facebook、WhatsApp 選填，公司電話與公司 Email 必填）｜target_user=property_manager,prospect｜
jgb/B/team-delete｜怎麼刪除團隊？（需先解除訂閱方案、輸入團隊名稱確認、刪除後資料無法恢復）｜target_user=property_manager｜
jgb/B/team-signer-personal-info｜簽約資訊卡「個人資訊」區塊只有個人團隊看得到，要填什麼？（姓氏、名稱、身分證字號、Email、手機必填；戶籍地址／通訊地址／身分證正反面／其他附件選填或另有條件）｜target_user=property_manager｜
jgb/B/team-signer-company-info｜簽約資訊卡的「公司資訊」要填什麼？（公司登記名稱上限 20 字、公司統編皆為必填；公司負責人只有社宅團隊必填；社宅團隊還要填必填的社宅業者編號與公司登記證號，公司登記證日期與縣市則不分團隊都是選填）｜target_user=property_manager｜
jgb/B/team-signer-agent-info｜簽約資訊卡的「經紀人資訊」要填什麼？（經紀人／經紀業名稱與證號，名稱上限 15 字；社宅團隊多了經紀人聯絡電話與 Email，且都是必填）｜target_user=property_manager｜
jgb/B/team-signer-manager-info｜簽約資訊卡的「租賃住宅管理人員資訊」要填什麼？（姓名與證號；社宅團隊多了聯絡電話欄位，且姓名／證號／電話都是必填；沒有 Email 欄位）｜target_user=property_manager｜
jgb/B/team-signer-stamps｜簽約資訊卡可以上傳哪幾種圖章？（法人或社宅團隊的簽約資訊卡才看得到「附件」與「電子簽約圖章」兩個區塊；「附件」有公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章五種，「電子簽約圖章」另外只有一個「圖章」欄位）｜target_user=property_manager｜
jgb/B/team-multi-company-info｜一個團隊可以管理多組公司資訊嗎？（可以在「團隊資訊管理」視窗新增與刪除，但清單第一筆不能刪除）｜target_user=property_manager｜
jgb/B/team-info-no-view-permission｜沒有查看團隊資訊的權限，打開團隊資訊頁會怎樣？（提示「您目前登入的帳號無法查看團隊資訊功能」）｜target_user=property_manager｜
jgb/B/team-signer-address-groups｜簽約資訊卡上有哪些地址欄位群？（個人的戶籍地址／通訊地址、公司的登記地址／通訊地址，都有「同上」可以直接帶入；社宅團隊另有經紀人與租賃管理人員各自的通訊地址）｜target_user=property_manager｜
jgb/B/team-signer-profile-switch｜怎麼在多組簽約資訊之間切換？（頁面上方有分頁式選單，超過 5 組會收進「所有團隊」下拉選單）｜target_user=property_manager｜
### B-member-list 成員列表（邀請、角色、成員名下資料） {#B-member-list}
jgb/B/member-list-overview｜成員列表可以看到什麼資訊？（成員總人數、加入時間、Email、手機號碼、目前的角色）｜target_user=property_manager｜
jgb/B/member-invite｜怎麼邀請新成員加入團隊？（用 Email 或手機號碼搜尋，對方要先是 JGB 會員）｜target_user=property_manager｜
jgb/B/member-role-concept｜成員的「角色」權限決定什麼？（決定看得到與能編輯的物件、合約、帳務、修繕等範圍）｜target_user=property_manager,prospect｜
jgb/B/member-role-manage｜怎麼管理團隊的角色範本？（可新增、編輯、刪除，也能套用 JGB 內建的快速設定範本）｜target_user=property_manager｜
jgb/B/member-remove｜怎麼移除成員？（列表右側的紅色 × 圖示開啟確認視窗，按「移除」才會真的刪除；名下還有物件或合約會被擋下）｜target_user=property_manager｜
jgb/B/member-seat-limit｜邀請成員有名額上限嗎？（依訂閱方案而定，達上限要升級方案才能繼續邀請）｜target_user=property_manager,prospect｜
jgb/B/member-assign-owned｜怎麼指派物件或合約給成員？（點成員旁的鉛筆圖示選「編輯綁定物件」或「編輯綁定合約」）｜target_user=property_manager｜
jgb/B/member-role-permission-list｜怎麼查看每個角色能做什麼？（點「角色權限說明」的「這裡」開啟角色權限列表，每一列是一項權限、每一欄是一個角色，用勾號／叉號表示有沒有這項權限）｜target_user=property_manager｜
jgb/B/member-list-role-inline-change｜成員列表可以直接改成員的角色嗎？（列表每一列都有角色下拉選單可以直接切換；選單裡也有「+ 新增角色」，可以直接開「編輯角色」視窗）｜target_user=property_manager｜
jgb/B/member-role-edit-open-condition｜編輯角色時的「開啟條件」是什麼？（要先勾選列出的其他權限，這個權限選項的勾選框才能點；沒先勾好之前，勾選框會維持鎖住）｜target_user=property_manager｜
jgb/B/member-role-edit-reset｜編輯角色時的「重設條件」按鈕是做什麼的？（把目前正在編輯、還沒儲存的勾選狀態還原）｜target_user=property_manager｜
jgb/B/member-list-sort｜成員列表可以怎麼排序？（姓名、加入時間、手機號碼、Email、角色名稱各有正反兩種排序）｜target_user=property_manager｜
jgb/B/member-list-role-select-disabled｜為什麼「團隊擁有者」和自己那一列的角色下拉不能改？（這兩列是固定顯示在列表最上面、角色下拉是鎖住的，跟其他成員分開處理）｜target_user=property_manager｜
### B-biglandlord-list 大房東列表與授權物件 {#B-biglandlord-list}
jgb/B/biglandlord-list-overview｜大房東列表可以看到哪些欄位？（ID、姓名、會員註冊、身分證字號、生日、主要聯絡方式、帳戶資訊、合作方式、合作起迄、所屬物件）｜target_user=property_manager｜
jgb/B/biglandlord-add｜怎麼新增大房東？（已註冊會員填 Email 即可，未註冊只要填姓氏與名稱，Email 選填）｜target_user=property_manager｜
jgb/B/biglandlord-authorize-estates｜大房東的「授權物件」怎麼設定？（逐筆物件勾選瀏覽廣告／合約／帳務／修繕；合約要先勾廣告，帳務要先勾廣告＋合約，修繕沒有前提）｜target_user=property_manager｜
jgb/B/biglandlord-import-export｜大房東名單可以批次匯入或匯出嗎？（可以，Excel 匯入新增、Excel 匯出下載）｜target_user=property_manager,prospect｜
jgb/B/biglandlord-actions-menu｜大房東列表每一列的操作選單有哪些功能？（編輯所屬物件、編輯大房東、刪除大房東）｜target_user=property_manager｜
jgb/B/biglandlord-authorize-apply-step｜授權物件頁取消勾選後，為什麼要按「套用」才會生效？（取消勾選只是待處理狀態，按套用才真的移除，按恢復可以取消這次變更）｜target_user=property_manager｜
jgb/B/biglandlord-delete-confirm｜刪除大房東會發生什麼？（先跳出確認視窗，確認後這位大房東就無法再存取這個團隊的任何資訊）｜target_user=property_manager｜
jgb/B/biglandlord-escrow-owner｜大房東列表上方的「所有權人／轉租人」是做什麼用的？（記錄代管物件的所有權人或轉租人資料，加快編輯合約速度）｜target_user=property_manager｜
jgb/B/biglandlord-seat-limit｜大房東名額有上限嗎？（大房東列表頁的「新增大房東」目前沒有名額檢查；成員／大房東管理頁（團隊管理底下的大房東列表）的「邀請」按鈕才有，額滿時會提示升級方案）｜target_user=property_manager,prospect｜
jgb/B/biglandlord-list-empty｜大房東列表沒有資料時會顯示什麼？（一開始沒有任何大房東顯示「尚無大房東」；用關鍵字搜尋卻沒有符合結果則顯示「沒有符合的結果😢」）｜target_user=property_manager｜
jgb/B/biglandlord-batch-template-fields｜批次匯入大房東的 Excel 範本要填哪些欄位？（姓氏、名稱必填，其餘含 Email、手機、身分證字號、地址、帳戶資訊、合作方式與合作起迄都是選填）｜target_user=property_manager｜
jgb/B/biglandlord-list-sort｜大房東列表可以用什麼排序？（姓名、手機號碼、Email、身分證字號，各有正序與反序共 8 種排序方式）｜target_user=property_manager｜
### B-biglandlord-report 大房東報表 {#B-biglandlord-report}
jgb/B/biglandlord-report-overview｜大房東報表可以看到什麼？（依大房東列出所屬物件、出租中物件與執行中合約租金總額）｜target_user=property_manager｜
jgb/B/biglandlord-report-permission｜誰看得到大房東報表？（需要「查看大房東報表」的角色權限）｜target_user=property_manager｜
jgb/B/biglandlord-report-community-rate｜大房東報表可以依社區細看嗎？（報表清單有「社區」欄，細節頁還會顯示匯率）｜target_user=property_manager｜
### B-biglandlord-sheet 大房東對帳表 {#B-biglandlord-sheet}
jgb/B/biglandlord-sheet-overview｜大房東對帳表在算什麼？（只有特定合作團隊看得到完整的押金、屋主資金、屋主提領、屋主直收等類別金額，其他團隊只看得到屋主租金收支；單月報表才有「上一月」「下一月」「下載」，整年度報表是「匯出報表」）｜target_user=property_manager｜
jgb/B/biglandlord-sheet-empty｜對帳表顯示「尚未被指派物件」是什麼意思？（這位大房東還沒被授權任何物件）｜target_user=property_manager｜
jgb/B/biglandlord-sheet-multi-currency｜對帳表出現「本月含多幣別帳單」提示是什麼意思？（該月的帳單有不同幣別，已用結算幣別加總）｜target_user=property_manager｜
jgb/B/biglandlord-sheet-hide-empty-rows｜對帳表可以隱藏沒有金額的項目嗎？（可以開關「隱藏空值項目」）｜target_user=property_manager｜
jgb/B/biglandlord-sheet-month-drilldown｜對帳表怎麼從年表切到單一月份的月報？（點表頭的月份會進入該月月報，點「取消」回到年表）｜target_user=property_manager｜
jgb/B/biglandlord-sheet-load-download-fail｜對帳表載入或下載失敗會怎樣？（載入失敗會顯示錯誤並提供「重試」，下載失敗只顯示錯誤訊息）｜target_user=property_manager｜
jgb/B/biglandlord-sheet-aside-and-loading｜大房東對帳表頁面的側邊選單和載入畫面長怎樣？（左側有社區／物件選單，看單一物件報表時會顯示上次匯入時間，報表產生中會顯示載入百分比進度條）｜target_user=property_manager｜
### B-advanced-settings 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」） {#B-advanced-settings}
jgb/B/advance-fee-items｜帳單的「自訂費用項目」怎麼設定？（分收入類／支出類，必填性質與自定義名稱，會科品項代號選填）｜target_user=property_manager｜
jgb/B/advance-discount-items｜進階設定的「優惠項目」是給誰用的？（只有統上或新北住都的合作團隊才看得到，可設定折扣套用在租金費用上）｜target_user=property_manager,prospect｜
jgb/B/advance-late-fee｜進階設定的「延遲金設置」怎麼計算？（只有統上合作團隊看得到，公式是租金 × (逾期天數 - 緩衝天數) × 延遲金%）｜target_user=property_manager,prospect｜
jgb/B/advance-additional-terms｜「預設補充條款」怎麼設定？（最多可以設 3 組，編輯合約時直接選用）｜target_user=property_manager,prospect｜
jgb/B/advance-custom-label｜「標籤設定」是做什麼用的？（幫物件加自訂標籤，單個標籤上限 18 字元）｜target_user=property_manager,prospect｜
jgb/B/advance-device-binding｜怎麼綁定智能裝置廠商？（輸入裝置廠商帳號密碼完成綁定，之後可在 JGB 平台管理裝置）｜target_user=property_manager｜
jgb/B/advance-fee-items-merge｜自訂費用項目可以合併嗎？（可以選多個已存在的品項合併成新品項，合併後無法回復）｜target_user=property_manager｜
jgb/B/advance-payment-cycle-discount｜進階設定的「繳費週期優惠」是給誰用的？（只有統上團隊才看得到，選比月繳更長的繳費週期就有折扣）｜target_user=property_manager,prospect｜
jgb/B/advance-notification-locale｜「Email 通知語系」在哪設定、誰看得到？（只有法人房東或社宅團隊看得到，決定代發通知信的預設語系）｜target_user=property_manager,prospect｜
jgb/B/advance-timezone｜「時區設定」會影響哪些通知？（只有法人房東或社宅團隊看得到，改變排程通知的發送時間）｜target_user=property_manager,prospect｜
jgb/B/advance-settlement-currency｜「結算幣別」是做什麼用的？（只有法人房東或社宅團隊看得到，把大房東報表的多幣別合約統一結算成一種幣別）｜target_user=property_manager,prospect｜
jgb/B/advance-device-binding-visibility｜為什麼進階設定看不到「裝置管理」區塊？（訂閱方案要生效中，且不能是免費方案）｜target_user=property_manager｜
jgb/B/advance-dedicated-account｜「房東專屬帳號」是做什麼用的？（只有法人房東或社宅團隊看得到；顯示在團隊首頁，且第一次儲存後不能自行修改，要洽 JGB 客服）｜target_user=property_manager,prospect｜
jgb/B/advance-auto-publish-unpublish｜招租廣告可以自動刊登或自動下架嗎？（可以，合約到期日前 N 天自動刊登，簽約後自動下架）｜target_user=property_manager,prospect｜
jgb/B/advance-contract-label｜「合約管理」的標籤設定跟物件的標籤設定是同一個嗎？（不是，這是合約專用的另一組標籤）｜target_user=property_manager｜
jgb/B/advance-sales-item-code｜「銷貨單品項代號對應」是做什麼用的？（只有特定團隊才有，設定匯出「M 化銷貨單」時每個品項要帶的產品代號）｜target_user=property_manager｜
jgb/B/advance-community-labels｜「社區管理」的城市／區域／位置設定是做什麼？（只有特定合作團隊看得到，用來建立社區篩選用的自訂標籤）｜target_user=property_manager｜
jgb/B/advance-short-lease-approval｜進階設定的「短租期核可流程」是做什麼的？（只有統上合作團隊看得到；租期少於設定天數時，合約要先簽核通過才會發出邀請給租客）｜target_user=property_manager,prospect｜
### B-tenant-list 租客列表（當前租客／封存、準時繳租率、信用評價） {#B-tenant-list}
jgb/B/lessee-tabs｜租客列表有哪兩個分頁？（當前租客／封存，封存代表這位租客已被移出列表且目前沒有進行中的合約）｜target_user=property_manager,prospect｜
jgb/B/lessee-credit-rating-visibility｜租客列表的「信用評價」欄位為什麼有些人看不到？（需要有查看租客信用評價的權限才會顯示這一欄）｜target_user=property_manager｜
jgb/B/lessee-crud｜租客列表可以新增、匯入、匯出租客嗎？（可以手動新增，也支援 Excel 匯入與匯出）｜target_user=property_manager,prospect｜
jgb/B/lessee-notification-status-color｜租客列表裡 Email／手機號碼顯示藍色、橘色、灰色代表什麼？（驗證狀態：已驗證／等待驗證／未驗證）｜target_user=property_manager｜
jgb/B/lessee-verification-link-expiry｜租客的 Email／手機驗證連結多久過期？（72 小時）｜target_user=property_manager｜
jgb/B/lessee-notification-toggle-effect｜租客的通知開關關閉後會怎樣？（收不到任何合約或帳單的通知信件或簡訊）｜target_user=property_manager｜
jgb/B/lessee-on-time-pay-rate｜租客的「準時繳租率」怎麼算？（已到帳未逾期帳單數 ÷ 全部應計入帳單數）｜target_user=property_manager｜
jgb/B/lessee-list-columns｜租客列表可以看到哪些欄位？（ID、姓名、會員註冊、Email - 通知、手機號碼 - 通知、註冊合約、免註冊合約、所屬修繕、準時繳租率、帳戶名稱、帳號資訊、操作）｜target_user=property_manager｜
jgb/B/lessee-list-columns-by-role｜社宅團隊與特定合作團隊的租客列表欄位有什麼不一樣？（社宅團隊沒有「會員註冊」「免註冊合約」「操作」，「註冊合約」欄改叫「所屬總合約」；特定合作團隊多了國籍、生日、主要聯絡方式）｜target_user=property_manager｜
jgb/B/lessee-pending-verification-bill-draft｜租客的 Email 或手機還在等待驗證時，帳單會怎樣？（帳單會停留在草稿分頁，等驗證完成或連結過期才能發送，也可以手動移動）｜target_user=property_manager｜
jgb/B/lessee-bulk-notify｜租客列表勾選多筆租客後可以做什麼？（統上團隊可以批次發送通知，其他團隊沒有這個批次操作）｜target_user=property_manager｜
jgb/B/lessee-export-entry-by-role｜匯出租客的入口在哪？（一般房東用「新增租客」下拉選單裡的「匯出租客」；社宅團隊只有一顆「匯出」按鈕，沒有新增或匯入）｜target_user=property_manager｜
jgb/B/lessee-list-search-and-pagination｜租客列表可以怎麼搜尋篩選、每頁看幾筆？（可依姓名／Email／手機號碼／租客 ID 搜尋，用會員註冊與通知狀態篩選，每頁可選 30／60／90 筆）｜target_user=property_manager｜
jgb/B/lessee-action-menu｜租客列表每一列的操作選單有哪些功能？（建立電子合約、上傳紙本合約、編輯租客、封存租客；封存分頁裡則改成刪除租客）｜target_user=property_manager｜

## C 社區與物件 {#C}
scope: 社區建檔、物件新增與批次匯入、刊登與銷售、物件狀態與欄位；⛔ 物件上的租約歸 D、抄表歸 E
### C-community-list 社區列表與建立 {#C-community-list}
jgb/C/community-list-overview-stats｜社區總表顯示什麼資訊？（物件總數、招租／買賣廣告數、空置數量、本月應收與已收）｜target_user=property_manager｜
jgb/C/community-add-single-and-limit｜如何新增社區？（訂閱方案有可建立社區數量上限）｜target_user=property_manager｜
jgb/C/community-batch-add-and-copy｜怎麼批次新增社區、或複製現有社區建立新社區？｜target_user=property_manager｜
jgb/C/community-list-filter-sort｜社區總表怎麼搜尋與排序？（案名／地址關鍵字、縣市行政區、建物類型、捷運站）｜target_user=property_manager｜
jgb/C/community-delete-requires-empty｜社區可以刪除嗎？（社區底下不能有任何物件才能刪除，且刪除後無法復原）｜target_user=property_manager｜
jgb/C/community-export-list｜社區總表可以匯出嗎？（需要匯出物件權限，會依目前篩選條件匯出）｜target_user=property_manager｜
jgb/C/community-list-pagination｜社區總表每頁筆數可以調整嗎？（30／60／90項）｜target_user=property_manager｜
jgb/C/community-list-add-permission｜誰看得到新增社區的入口？（總表右上角需要編輯物件權限；空狀態的批次新增／新增社區入口需要新增物件權限）｜target_user=property_manager｜
### C-community-edit 社區資料編輯（基本資料、照片與描述、介紹與交通） {#C-community-edit}
jgb/C/community-edit-tabs｜社區編輯有哪些分頁？（基本資料、介紹與交通、照片與描述）｜target_user=property_manager｜
jgb/C/community-edit-basic-fields｜社區基本資料要填什麼？（社區名稱限30字、詳細地址與對外顯示地址、建築類型、總樓層、屋齡）｜target_user=property_manager｜
jgb/C/community-edit-gallery-photo-limit｜社區照片與描述可以上傳幾張圖片？（限1張，JPG/PNG，檔案大小最大10MB）｜target_user=property_manager｜
jgb/C/community-edit-gallery-save-notice｜社區照片與描述什麼時候會跳出「已更新」提示？（存檔成功後才出現，不是上傳當下）｜target_user=property_manager｜
jgb/C/community-edit-intros-and-transit｜社區介紹與交通怎麼填？（社區簡介、鄰近交通說明、可加多個鄰近捷運站）｜target_user=property_manager｜
jgb/C/community-edit-basic-required-field｜社區基本資料哪個欄位是必填？（只有社區名稱是必填）｜target_user=property_manager｜
### C-community-estates 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） {#C-community-estates}
jgb/C/community-estates-overview-card｜社區底下物件頁最上方顯示什麼？（招租廣告、買賣廣告、目前空置數量、類型、屋齡、本月應收與已收金額）｜target_user=property_manager｜
jgb/C/community-estates-category-switch｜社區底下的物件清單怎麼切換總覽／招租／買賣？（欄位標題會跟著切換內容改變）｜target_user=property_manager｜
jgb/C/community-estates-add-batch-copy｜怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制）｜target_user=property_manager｜
jgb/C/community-estates-extra-tabs｜社區底下有差額發票、投報率頁籤嗎？（依團隊是否開通該功能才會出現，投入成本與投報率兩個頁籤是同一個開關）｜target_user=property_manager｜
jgb/C/community-estates-pagination｜社區物件清單每頁筆數可以調整嗎？（30／60／90項）｜target_user=property_manager｜
### C-community-public-page 社區公開頁（社區詳情、社區總表） {#C-community-public-page}
jgb/C/community-show-content｜社區公開頁（社區廣告）顯示什麼？（基本資訊、鄰近捷運、社區介紹、刊登中物件）｜target_user=property_manager,prospect｜
jgb/C/community-show-price-range｜社區公開頁最上方顯示什麼價格區間？（租賃金額區間、售價金額區間、售價單價區間坪或平方公尺隨語系切換）｜target_user=property_manager,prospect｜
jgb/C/community-show-share｜社區公開頁怎麼分享？（分享燈箱、查看所有物件連結）｜target_user=property_manager｜
jgb/C/community-show-editor-nav｜在社區廣告頁可以直接跳到編輯社區、社區詳情或社區總表嗎？（只有管理員看得到這個選單）｜target_user=property_manager｜
### C-community-force-binding 物件綁定社區的導引（2022/05 社區功能上線時的強制綁定流程，限團隊擁有者） {#C-community-force-binding}
jgb/C/forcebinding-why-and-who｜為什麼會出現「物件需綁定社區」的導引？（2022/05/12 社區功能上線，只有團隊擁有者能操作）｜target_user=property_manager｜
jgb/C/forcebinding-welcome-progress｜物件綁定社區的導引起始畫面顯示什麼？（已綁定與尚未綁定的物件數量、需同意服務條款）｜target_user=property_manager｜
jgb/C/forcebinding-two-steps｜物件綁定社區導引有哪兩個步驟？（填寫社區資料、選擇欲綁定社區內的物件；未完成系統功能無法正常使用）｜target_user=property_manager｜
jgb/C/forcebinding-select-estates-irreversible｜怎麼挑選要綁定的物件？（可關鍵字搜尋、每頁30/60/90項，確認綁定後無法修改）｜target_user=property_manager｜
jgb/C/forcebinding-completion-states｜綁定完成後會看到什麼？（全部綁完顯示恭喜，還有剩則提示繼續綁定）｜target_user=property_manager｜
### C-estate-list 物件列表與篩選 {#C-estate-list}
jgb/C/estate-list-add-must-pick-community｜物件總表怎麼新增物件？（新增與複製現有物件都要先經過社區選擇畫面，目前沒有批次新增入口）｜target_user=property_manager｜
jgb/C/estate-list-counter-and-limit｜物件總表標題下方顯示什麼？（目前物件總數、尚可新增數量）｜target_user=property_manager｜
jgb/C/estate-list-filters｜物件總表有哪些進階篩選條件？（縣市行政區、經理人、大房東、社區、捷運、用途、格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金與面積(坪)範圍、標籤）｜target_user=property_manager｜
jgb/C/estate-list-keyword-search｜物件總表關鍵字搜尋可以查什麼？（案名、地址、租客、物件ID、手機、信箱）｜target_user=property_manager｜
jgb/C/estate-list-batch-actions｜物件總表可以批次操作嗎？（匯出物件、新增批次帳單、批次刊登／取消刊登招租廣告、刪除；批次取消刊登失敗時不會顯示任何提示）｜target_user=property_manager｜
jgb/C/estate-status-affects-actions｜物件狀態會影響哪些功能？（未刊登／刊登中／洽談中／合約中，各自能做的操作不同）｜target_user=property_manager,prospect｜
jgb/C/estate-list-pagination｜物件總表每頁筆數可以調整嗎？（30／60／90項）｜target_user=property_manager｜
jgb/C/estate-list-filters-space-type-and-others｜物件總表篩選還有哪些條件？（空間類型多選、其他群組：VR、有電梯、可開伙、可養寵物）｜target_user=property_manager｜
jgb/C/estate-list-category-switch｜物件總表怎麼切換總覽／招租／買賣？（三種分類切換）｜target_user=property_manager｜
jgb/C/estate-list-sort-remembers-last｜物件總表怎麼排序？（排序選項由系統提供，上次選的排序方式會被記住並自動帶入）｜target_user=property_manager｜
### C-estate-edit 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） {#C-estate-edit}
jgb/C/estate-edit-basic-space-type｜物件基本資料的空間類型、用途、格局要怎麼填？｜target_user=property_manager｜
jgb/C/estate-edit-basic-address｜物件的詳細地址與對外顯示地址有什麼差別？｜target_user=property_manager｜
jgb/C/estate-edit-basic-floor-room-number｜物件的樓層與房號要怎麼填？（頂加輸入+1、地下室輸入-1）｜target_user=property_manager｜
jgb/C/estate-edit-basic-community-name-hide｜物件廣告頁可以隱藏群組/大樓名稱嗎？｜target_user=property_manager｜
jgb/C/estate-edit-building-transcript-social｜社宅物件建物謄本要填什麼？（申請謄本日期、段小段、謄本面積公式，不會顯示在廣告頁）｜target_user=property_manager｜
jgb/C/estate-edit-building-transcript-general｜一般物件建物謄本要填什麼？（土地標的清冊、坐落基地、稅籍編號、專有部分、主建物、附屬建物）｜target_user=property_manager｜
jgb/C/estate-edit-facilities｜物件附設傢俱怎麼設定？（第一個區塊標題是格局(<空間類型>)，依空間分區加入家電、傢俱、自訂項目，數量0不顯示在廣告頁）｜target_user=property_manager｜
jgb/C/estate-edit-gallery-title-photos｜物件標題與照片有什麼限制？（標題最長60字、照片最多15張15MB、平面圖最多5張含PDF）｜target_user=property_manager｜
jgb/C/estate-edit-intro-transit｜物件介紹要填什麼？（房源簡介、鄰近交通，可加多筆鄰近捷運站）｜target_user=property_manager｜
jgb/C/estate-edit-vr-720｜物件的720 VR全景照怎麼拍？（需先安裝 VR Maker App 掃 QR Code 拍攝，可設定是否用於廣告）｜target_user=property_manager｜
jgb/C/estate-edit-cannot-change-community｜物件可以換綁到別的社區嗎？（畫面上目前沒有這個操作入口）｜target_user=property_manager｜
jgb/C/estate-edit-basic-orientation｜物件基本資料可以填朝向嗎？｜target_user=property_manager｜
jgb/C/estate-edit-tabs-overview｜物件編輯有哪些分頁？（「物件資訊」與「廣告資訊」兩個群組；社宅與一般物件的建物謄本分頁互斥）｜target_user=property_manager｜
### C-rent-listing 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實） {#C-rent-listing}
jgb/C/estate-rent-detail-deposit-cap｜招租押金有法定上限嗎？（一般租賃契約押金最高不得超過兩個月租金）｜target_user=property_manager,prospect｜
jgb/C/estate-rent-detail-move-in-lease-terms｜招租詳情的最短租期、最快入住日、最快點交日怎麼填？｜target_user=property_manager｜
jgb/C/estate-rent-detail-tenant-conditions｜招租條件要求可以設定什麼？（身份限制複選、養寵物可否、開伙可否、生活公約）｜target_user=property_manager｜
jgb/C/estate-rent-contact-agency-info｜刊登主資訊的團隊資訊要在哪裡修改？（法人／社宅房東顯示公司資訊、到團隊資訊修改；個人房東顯示經理人資訊、到帳號資訊修改）｜target_user=property_manager｜
jgb/C/estate-rent-contact-manager-and-hide｜招租廣告可以隱藏經理人／房東的名稱、電話、Email嗎？（勾選框在「經理人資訊」或「刊登主資訊」的經理人卡片上，每種身分只有一組）｜target_user=property_manager,prospect｜
jgb/C/estate-rent-verify-legal｜招租的核實訊息是什麼？（依租賃住宅市場發展條例核實產權登記與違建面積）｜target_user=property_manager,prospect｜
jgb/C/estate-rent-open-permission-and-validation｜為什麼物件刊登不出去？（需要刊登物件或新增物件的權限；必填欄位沒填完會退回編輯頁）｜target_user=property_manager｜
jgb/C/estate-rent-detail-price-and-tax｜招租詳情要填哪些金額相關欄位？（面積、幣別、每月租金、營業稅：應稅／零稅率／免稅）｜target_user=property_manager｜
### C-estate-dashboard 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） {#C-estate-dashboard}
jgb/C/estate-dashboard-entry-and-groups｜物件儀表板進去預設是哪個分頁？（預設招租表現；大房東看不到「限管理者查看」分頁群組）｜target_user=property_manager｜
jgb/C/estate-dashboard-rent-performance｜招租表現分頁顯示什麼？（空置天數、廣告瀏覽次數、帳務表現、合約歷程與修繕紀錄摘要）｜target_user=property_manager｜
jgb/C/estate-dashboard-contracts-history｜物件儀表板的合約歷程顯示哪些欄位？（一般房東：狀態／簽約類型／物件／承租人／租期／是否通知；社宅房東：合約名稱／承租人／租期）｜target_user=property_manager｜
jgb/C/estate-dashboard-bills-tabs｜物件儀表板的帳務收支有哪些子頁籤？（總收支、統計報表）｜target_user=property_manager｜
jgb/C/estate-dashboard-repair-status-flow｜物件儀表板修繕紀錄怎麼呈現？（申請修繕→安排修繕→完成修繕→結單四狀態）｜target_user=property_manager｜
jgb/C/estate-dashboard-attachments-vs-contract-attachments｜「附件清單」跟「合約附件」差在哪？（附件清單自由上傳、有儲存空間上限，下載不限身分但只有代理人且有新增物件權限才能刪除；合約附件是租賃法定文件的固定清單）｜target_user=property_manager｜
jgb/C/estate-dashboard-runnings-vs-memos｜「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入/支出金額，記事本只是純文字備註）｜target_user=property_manager｜
jgb/C/estate-dashboard-monthly-report-upload｜每月報表／每月對帳單怎麼上傳？（PDF、10MB上限，可批次指定多個物件，同月重傳會覆蓋舊檔）｜target_user=property_manager｜
jgb/C/estate-dashboard-top-cards｜物件儀表板最上方顯示哪三張卡？（物件資訊、招租廣告、買賣廣告；編輯捷徑需要新增物件權限）｜target_user=property_manager｜
### C-estate-public-page 單一物件廣告頁（招租） {#C-estate-public-page}
jgb/C/estate-house-preview-unpublished｜物件還沒刊登（未開放）時，廣告頁會怎麼顯示？（屋主看到的是預覽頁提示；其他人造訪會得到404）｜target_user=property_manager,prospect｜
jgb/C/estate-house-invite-countdown｜簽約邀請連結會失效嗎？（連結會顯示倒數，過期後失效）｜target_user=property_manager,prospect｜
jgb/C/estate-house-content-blocks｜物件廣告頁顯示哪些內容？（照片／VR全景切換、設備與設施、交通與環境設施、溫馨提醒）｜target_user=property_manager,prospect｜
jgb/C/estate-house-contact-landlord｜物件廣告頁「聯絡房東」區塊顯示什麼？（房東電話／Email依隱藏設定決定是否顯示；公司廣告電話／Email不受隱藏設定影響）｜target_user=property_manager,prospect｜
jgb/C/estate-house-vs-show-url｜物件廣告頁的網址會自動轉換嗎？（刊登中時，內部編號網址會自動轉址到 JGB 編號公開網址）｜target_user=property_manager｜
jgb/C/estate-house-fees-table｜物件廣告頁有費用明細表嗎？（車位物件不顯示，其餘物件顯示生活費用表）｜target_user=property_manager,prospect｜
jgb/C/estate-house-appointment-cta｜物件廣告頁有預約入住的按鈕嗎？（一般訪客看到「立即預約入住」，受邀簽約者看到「查看合約」）｜target_user=property_manager,prospect｜
jgb/C/estate-house-info-card｜物件廣告頁的資料卡片顯示什麼？（地址／社區名稱、租金元/月與含哪些費用、建築類型與樓層或格局、商用類的空間類型與座位數、面積、物件平面圖）｜target_user=property_manager,prospect｜
### C-team-storefront 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） {#C-team-storefront}
jgb/C/team-public-page-purpose｜房東對外首頁（招租店舖）是什麼？（公開展示聯絡資訊、簡介與所有刊登中物件，供分享給潛在租客）｜target_user=property_manager,prospect｜
jgb/C/team-public-page-edit-and-banner｜招租店舖上可以直接編輯哪些內容？（封面照片、大頭照、姓名、自我介紹，會連動帳號資訊）｜target_user=property_manager｜
jgb/C/team-public-page-filter-and-view｜招租店舖怎麼篩選物件？（鄉鎮區或捷運、類型與格局，可切換小圖示／大圖示／條列式；每頁筆數 30／60／90，預設 30）｜target_user=property_manager｜
jgb/C/team-public-page-share｜招租店舖怎麼分享？（可分享至FB、Line、LinkedIn，加入團隊且設定客製帳號可有專屬短網址）｜target_user=property_manager,prospect｜
jgb/C/team-public-page-recruitment｜多團隊招募頁是什麼？（沒有指定住宅或商用時自動轉址到住宅、強制只顯示招租、不顯示社區篩選、每頁預設10筆）｜target_user=property_manager,prospect｜

## D 租約（含委託約子題） {#D}
scope: 合約建立、簽署、狀態與階段、續約、退租、違約金、租客邀請簽約；委託約（僅法人房東）；⛔ 帳單與押金金流歸 E
### D-contract-list 合約列表與搜尋 {#D-contract-list}
jgb/D/contract-list-status-tabs｜合約列表有哪些狀態頁籤？（待發送合約／待租客簽回／待房東簽名／執行中合約／歷史合約）｜target_user=property_manager｜
jgb/D/contract-search-keyword-scope｜合約列表怎麼搜尋合約？（案名／地址／租客／ID／手機／信箱六種關鍵字，另有進階搜尋）｜target_user=property_manager｜
jgb/D/contract-create-entry｜怎麼建立一份新合約？（合約總表右上角「建立合約」，或物件總表小齒輪選建立合約）｜target_user=property_manager｜
jgb/D/contract-create-estate-completeness-requirement｜物件要先刊登廣告才能建立合約嗎？（現行規則是必填欄位要填齊，不是看刊登狀態）｜target_user=property_manager｜
jgb/D/contract-list-row-gear-actions｜合約總表列的小齒輪可以做什麼操作？（不論狀態都有「查看物件」「查看帳單」；其餘依合約狀態、身分與權限增減）｜target_user=property_manager｜
jgb/D/contract-list-row-sort-options｜合約總表可以怎麼排序？（依名稱、更新時間、合約起始日、終止日、成立日，各分新舊／早晚，共 5 種依據）｜target_user=property_manager｜
jgb/D/contract-list-columns｜合約總表有哪些欄位？（含團隊自訂的「標籤」欄）｜target_user=property_manager｜
jgb/D/contract-list-deposit-alert｜合約總表的待退押金提示燈號是什麼意思？（合約到期前 30 天才能點退）｜target_user=property_manager｜
jgb/D/contract-list-bill-currency-column｜合約總表什麼時候會多出「帳單幣別」欄？（只有在批次建立帳單、挑選合約的頁面才會出現，一般檢視沒有這一欄）｜target_user=property_manager｜
jgb/D/contract-list-export-declaration｜合約總表可以匯出實價登錄資料嗎？（只有在「執行中合約」頁籤、中文站台、團隊開通此功能且帳號有建立合約權限時才會出現按鈕）｜target_user=property_manager｜
jgb/D/contract-list-export-excel｜合約總表可以匯出 Excel 嗎？（勾選後按「匯出合約」，需要匯出合約權限，內容含租期、每期租金、合約押金等欄位）｜target_user=property_manager｜
### D-contract-edit-general 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） {#D-contract-edit-general}
jgb/D/contract-edit-tabs-overview｜建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁）｜target_user=property_manager｜
jgb/D/contract-tenant-basic-info｜承租方基本資料怎麼填？（個人／法人租客、租客註冊或免註冊、緊急聯絡人）｜target_user=property_manager｜
jgb/D/contract-rentbasic-template-and-dates｜「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期）｜target_user=property_manager｜
jgb/D/contract-rentbasic-billing-cycle｜「基本條件」分頁的繳費週期與帳單週期制度怎麼設定？（繳費週期／繳費截止日、當月分算或跨月計算、分算日）｜target_user=property_manager｜
jgb/D/contract-rentbasic-latefee｜「基本條件」分頁的遲繳滯納金怎麼計算？（僅新北住都角色群組可見，兩段比例＋拖欠天數門檻，欄位唯讀）｜target_user=property_manager｜
jgb/D/contract-rentbasic-tenant-language｜「基本條件」分頁的租客慣用語系是什麼？（決定系統產生給租客的合約文件語系）｜target_user=property_manager｜
jgb/D/contract-rentbasic-early-termination｜合約的「可否提前解約」與違約金怎麼設定？（每月租金／固定金額／詳參補充條款／其他四種算法）｜target_user=property_manager｜
jgb/D/contract-rent-fees｜租金費用分頁要設定什麼？（租金、押金、自訂收入／支出費用、租金優惠、繳費週期優惠）｜target_user=property_manager｜
jgb/D/contract-rent-deposit-two-modes｜押金有哪幾種設定方式？（每月租金倍數／固定金額兩種計算基準）｜target_user=property_manager｜
jgb/D/contract-rent-adjustment｜租金調幅設定分頁在做什麼？（依繳費期數設定固定金額或百分比調漲／調降）｜target_user=property_manager｜
jgb/D/contract-tax-invoice｜稅與發票分頁怎麼設定？（是否開立發票、應稅品項、目前只支援租金品項開發票）｜target_user=property_manager｜
jgb/D/contract-bill-setting｜帳單設定分頁在做什麼？（預先編輯未來帳單的標題、金額、週期與自動執行動作）｜target_user=property_manager｜
jgb/D/contract-payment-method｜合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種）｜target_user=property_manager｜
jgb/D/contract-facilities-tab｜附設傢俱分頁在做什麼？（設定家具責任歸屬，簽約後會帶入點交清單）｜target_user=property_manager｜
jgb/D/contract-situation-tab｜現況補充分頁要寫什麼？（車位、屋況、漏水處等內政部規範現況細節）｜target_user=property_manager｜
jgb/D/contract-landlord-dealer-basic｜出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、電子簽名圖章）｜target_user=property_manager｜
jgb/D/contract-building-transcript-optional｜建物謄本分頁是選填的嗎？（選填，僅供合約內容完備使用，不會顯示在廣告頁）｜target_user=property_manager｜
jgb/D/contract-attachments-optional｜合約附件分頁能上傳什麼？（各類文件圖片或 PDF，最大 10MB）｜target_user=property_manager｜
jgb/D/contract-additional-convention｜補充條款有字數限制嗎？（最多 50 行、每行 50 字，可套用範本與複製其他合約）｜target_user=property_manager｜
jgb/D/contract-edit-tabs-conditional-rules｜合約編輯分頁會依什麼條件增減？（紙本／客製化契約書、車位、特定合作團隊範本、稅務發票資格皆會影響）｜target_user=property_manager｜
jgb/D/contract-edit-building-transcript-visibility｜「建物謄本」分頁什麼時候不會顯示？（只有選中／未選合約範本時才顯示，選到英越文或泰文版就會被拿掉）｜target_user=property_manager｜
jgb/D/contract-lease-scope-by-space-type｜合約的租賃範圍怎麼決定？（物件空間型態為整戶時自動為「全部」，其餘一律「部分」，不用使用者勾選）｜target_user=property_manager｜
jgb/D/contract-tenant-code-change｜承租人編碼要異動怎麼辦？（此操作需由 JGB 客服協助）｜target_user=property_manager｜
### D-contract-edit-social-housing 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） {#D-contract-edit-social-housing}
jgb/D/social-housing-building-detail｜社宅合約「建物標的」分組有哪些分頁？（建物細節、現況補充、現況照片、附設傢俱四個分頁）｜target_user=property_manager｜
jgb/D/social-housing-photos-tab｜社宅合約「現況照片」分頁一定要上傳嗎？（部分照片為必填，用來證明社宅內部現況設備存在）｜target_user=property_manager｜
jgb/D/social-housing-facilities-tab｜社宅合約「附設傢俱」分頁要填什麼？（各格局家具與數量）｜target_user=property_manager｜
jgb/D/social-housing-rent-basic-conditions｜社宅合約「基本條件」要填什麼？（合約範本、委託期間、住宅現況、物件返還狀態、代收定金、爭議處理）｜target_user=property_manager｜
jgb/D/social-housing-early-termination-difference｜社宅合約的提前解約怎麼設定？跟一般合約一樣嗎？（只設定雙方是否可以提前解約，沒有違約金計算方式）｜target_user=property_manager｜
jgb/D/social-housing-rent-fees-tab｜社宅合約「租金費用」分頁要填什麼？（代租金額或包租金額、租金與押金、生活費用）｜target_user=property_manager｜
jgb/D/social-housing-payment-method-tab｜社宅合約「收款方式」怎麼設定？（轉帳、票據、現金三種；代租代管範本還要選收款人是原房東或業者）｜target_user=property_manager｜
jgb/D/social-housing-notary｜社宅合約一定要公證嗎？（預設應辦理公證，可填理由不辦但視同放棄公證費補助；辦理公證後需下載文件紙本簽署再上傳歸檔）｜target_user=property_manager｜
jgb/D/social-housing-attachments-tab｜社宅合約「合約附件」要準備什麼？（合約附件只收其他文件如附註條款、稅籍證明；測量成果圖等在出租方附件分頁，轉租合約除外）｜target_user=property_manager｜
jgb/D/social-housing-subsidy-terms-tab｜社宅合約「補助申請」分頁在做什麼？（配合社宅包租代管 333 補貼政策，出租方三種稅費減免）｜target_user=property_manager｜
jgb/D/social-housing-landlord-tabs-overview｜社宅合約「出租方」分組有哪些分頁？（基本資料、授權、附件三個分頁）｜target_user=property_manager｜
jgb/D/social-housing-landlord-license-conditions｜社宅合約「授權」分頁要確認什麼？（合法建物條件、同意提供住宅、同意轉租等授權事項）｜target_user=property_manager｜
jgb/D/social-housing-tenant-tabs-overview｜社宅合約「承租方」分組有哪些分頁？（基本資料、家庭＆財產、授權、附件）｜target_user=property_manager｜
jgb/D/social-housing-tenant-basic-status｜社宅合約「基本資料」怎麼審核租客資格？（承租人資格、住宅政策補貼戶、代理人；包租合約改填公司資料）｜target_user=property_manager｜
jgb/D/social-housing-tenant-household｜社宅合約「家庭＆財產」分頁要登記什麼？（家庭成員、不動產與動產總額、最近年所得）｜target_user=property_manager｜
jgb/D/social-housing-tenant-license｜社宅合約承租方的「授權」分頁要同意什麼？（財稅所得總檢核、家庭年所得百分位等資格條件）｜target_user=property_manager｜
jgb/D/social-housing-dealer-basic｜社宅合約「業者」分頁在做什麼？（確認團隊資料與經理人資訊，有誤要回團隊資訊或帳號資訊修改）｜target_user=property_manager｜
jgb/D/social-housing-move-in-terms｜社宅合約「點交證明文件」分頁在約定什麼？（點交狀態與修繕責任的預先約定，不是簽約後實際執行的點交）｜target_user=property_manager｜
jgb/D/social-housing-charter-sublet-tab-hiding｜社宅合約選「包租包管」或「轉租」範本，分頁會不同嗎？（包租包管隱藏承租方戶籍/證照/附件，轉租隱藏出租方證照/附件）｜target_user=property_manager｜
### D-contract-sign-view 簽約與合約檢視 {#D-contract-sign-view}
jgb/D/contract-invite-and-review-period｜合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效，天數為團隊可調整設定）｜target_user=property_manager,prospect｜
jgb/D/contract-sign-flow-steps｜租客簽約要經過哪些步驟？（填承租方簽約資料與上傳文件、預覽合約、自動扣款先授權信用卡、部分範本另有條款勾選、雲想科技畫面簽名）｜target_user=property_manager｜
jgb/D/contract-esign-no-extra-fee｜電子簽章簽約要另外收費嗎？（系統內沒有簽章計費機制，簽約流程無付費／加購畫面）｜target_user=property_manager,prospect｜
jgb/D/contract-locked-after-signing｜合約簽約後可以修改嗎？（送出前可編輯、簽名前可取消簽名重編，簽署完成即無法更改，需重新簽一份新合約）｜target_user=property_manager,prospect｜
jgb/D/contract-show-panels｜合約檢視頁面看得到什麼？（出／承租方資訊、業者、經理人資訊，以及點交點退進行中的提示）｜target_user=property_manager｜
jgb/D/contract-show-paper-upload-archive｜合約檢視頁的「歸檔資料」是什麼？有什麼檔案限制？（租客免註冊的合約簽署後上傳合約、續約、終止合約的歸檔 PDF，最大 10MB）｜target_user=property_manager｜
jgb/D/contract-show-creditcard-auth-prompt｜簽約時會提示信用卡自動扣款授權嗎？（收款設定需要信用卡自動扣款時，租客在簽約頁點「下一步」會提示前往授權；特定合作團隊專屬範本除外）｜target_user=property_manager｜
jgb/D/contract-upload-existing-vs-electronic｜上傳既有合約跟建立電子合約差在哪？（既存合約用於已簽好或有自己公版合約的情境，皆可續用系統帳務／修繕追蹤）｜target_user=property_manager,prospect｜
jgb/D/contract-guarantor-add-after-signing｜簽約後可以補加保證人嗎？（租客簽約流程本身就能加連帶保證人；簽約完成後要補加，業者端沒有自助功能，需洽 JGB 客服協助）｜target_user=property_manager｜
### D-move-in 點交 {#D-move-in}
jgb/D/move-in-checklist-and-responsibility｜點交清單怎麼確認？（依合約約定的傢俱項目逐一上傳照片、標註出租方或承租方負責）｜target_user=property_manager｜
jgb/D/move-in-meter-readings｜點交要填另計費用起始度數嗎？（依合約設定另計的費用項目要輸入起始度數，會直接帶入日後帳單計算）｜target_user=property_manager｜
jgb/D/move-in-page-general-vs-social-housing｜點交頁面一般合約跟社宅合約用的是同一個嗎？（不是，一般住宅合約用一般合約的點交頁面，社宅合約會被導向社宅合約的點交頁面）｜target_user=property_manager｜
jgb/D/move-in-blocked-states｜點交送出後還能再送一次嗎？（已完成點交無法再次送出；已送出、等待租客確認中的清單要先取消邀請才能改）｜target_user=property_manager｜
jgb/D/move-in-cancel-invite｜點交邀請送出後可以取消嗎？（可以，系統會記錄「取消點交邀請」這個動作）｜target_user=property_manager｜
jgb/D/move-in-result-pdf｜點交結果能下載 PDF 嗎？（有專屬頁面可以檢視或下載點交 PDF）｜target_user=property_manager｜
jgb/D/move-in-optional-and-timing｜點交是必要流程嗎？（點交是選擇性操作，未點交也能發帳單；簽約完成後即可在執行中合約選取物件點交）｜target_user=property_manager,prospect｜
### D-move-out 點退 {#D-move-out}
jgb/D/move-out-checklist-and-damage｜點退清單怎麼處理設備損壞？（可編輯填入賠償金額與理由，過程可儲存草稿）｜target_user=property_manager｜
jgb/D/move-out-bill-generation｜點退會產生什麼帳單？（含提前解約金、點退押金、賠償金，設定期限後發送，租客確認並繳款才算完成）｜target_user=property_manager｜
jgb/D/move-out-eligibility-conditions｜什麼合約可以點退？（合約狀態須為執行中／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外）｜target_user=property_manager｜
jgb/D/move-out-timing-window｜點退的時間限制是什麼？（合約到期前 30 天起可以點退，過了到期日之後目前沒有再設上限）｜target_user=property_manager｜
jgb/D/move-out-remains-in-active-list｜點退完成的合約為什麼還在「執行中合約」？（只要還沒到合約到期日就會留在執行中，到期後才轉入歷史合約）｜target_user=property_manager,prospect｜
jgb/D/move-out-fee-adjustment-step｜點退第二步「點退找補費用」頁面要填什麼？（系統帶入的點退費用項目，含提前解約時自動帶入的違約金、傢俱賠償，另可填備註、期限、附件）｜target_user=property_manager｜
jgb/D/move-out-tenant-no-response-cancel｜租客不確認點退時要怎麼辦？（系統不會逾期自動放行，只能由房東取消點退邀請後重新發送）｜target_user=property_manager｜
### D-renew 續約 {#D-renew}
jgb/D/renew-batch-entry-and-selection｜怎麼一次幫多筆合約續約？（合約總表「建立合約」旁選批次續約，異動中的合約不能選）｜target_user=property_manager｜
jgb/D/renew-date-setting-modes｜續約日期怎麼設定？（多份合約可用快速日期設定一次加 N 個月，或個別指定每份合約的續約日）｜target_user=property_manager｜
jgb/D/renew-upload-paper-signed｜續約可以上傳紙本已簽合約嗎？（只選一份紙本簽約的合約續約時可以，提供雙方已完成簽約的紙本合約掃描檔）｜target_user=property_manager｜
jgb/D/renew-preview-bill-generation｜續約可以預先編輯帳單嗎？（續約預覽頁可先編輯續約期間帳單，實際帳單於完成續約後才產生）｜target_user=property_manager｜
jgb/D/renew-signing-flow｜續約邀請發出後流程是什麼？（租客簽回後可在「待租客簽回」查找，房東確認無誤後立即簽名完成續約）｜target_user=property_manager｜
jgb/D/renew-invite-review-days｜續約邀請效期是幾天？（預設 3 天，團隊可覆蓋設定）｜target_user=property_manager｜
jgb/D/renew-data-carryover-rules｜續約時資料怎麼沿用？（新合約由舊合約複製，並更新出租方/承租方最新資料；週期設定有調整就用新的、沒調整就沿用）｜target_user=property_manager｜
jgb/D/renew-deposit-difference-handling｜續約押金差額怎麼處理？（一般續約第一張帳單不列押金；只有特定合作團隊的延長續約會用原押金算差額；新合約無法直接沿用舊合約押金，一律列全額押金）｜target_user=property_manager｜
### D-early-termination 提前解約 {#D-early-termination}
jgb/D/early-termination-reasons｜房東申請提前解約要選什麼理由？（新版中文合約有 10 項法定理由可選，其餘合約只能選「其他」）｜target_user=property_manager｜
jgb/D/early-termination-form-fields｜申請提前解約要填什麼？（預計提前解約日須早於原合約到期日、違約金支付方與金額、佐證資料）｜target_user=property_manager｜
jgb/D/early-termination-tenant-cancel｜誰可以取消已送出的提前解約申請？（房東透過小齒輪取消，租客只有在提前解約確認中狀態才能取消）｜target_user=property_manager｜
jgb/D/early-termination-eligibility｜什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起）｜target_user=property_manager｜
jgb/D/early-termination-effect-move-out｜提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金）｜target_user=property_manager,prospect｜
jgb/D/early-termination-billing-after｜提前解約後還會出新帳單嗎？（解約日之後系統不會再自動產生新租金帳單；已產生、落在解約日後的帳單要業者自行封存）｜target_user=property_manager｜
### D-notary 租約公證（公證分頁與公證服務） {#D-notary}
jgb/D/general-contract-notary-tab｜一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項；英文與英越文版合約不支援）｜target_user=property_manager｜
jgb/D/contract-thinkcloud-esign-service｜簽約時進入的雲想科技頁面是什麼？（系統導向 Thinkcloud 雲想科技的電子簽署網頁，簽完再導回 JGB；一般合約、委託合約皆會用到）｜target_user=property_manager｜
jgb/D/contract-thinkcloud-signing-variants｜雲想科技簽署畫面依合約類型有什麼差異？（公會版本合約加補充條款多一個協商條款簽名框；DIY 客製化合約解析失敗時會顯示提示訊息，不會直接出現系統錯誤畫面）｜target_user=property_manager｜
### D-entrust-contract 委託合約（列表、建立編輯、檢視） {#D-entrust-contract}
jgb/D/entrusted-contract-what-is-it｜委託合約是什麼？（房東委託業者包租代管的合約，跟業者與租客之間的租賃合約是不同份文件）｜target_user=property_manager,prospect｜
jgb/D/entrusted-contract-lease-type｜委託合約「包租」跟「代管」有什麼不同？（代管必填服務費計算模式、幣別與金額或比例；計算制度、週期、約定日期兩者都要填）｜target_user=property_manager,prospect｜
jgb/D/entrusted-contract-tabs-overview｜委託合約編輯畫面有哪些分頁？（房東資訊、委託條件三頁、管理方資訊共 3 組 5 頁）｜target_user=property_manager｜
jgb/D/entrusted-contract-preview-to-show｜委託合約編輯完成後怎麼進入簽署？（點右上角「預覽合約」先儲存資料，再進入檢視頁面）｜target_user=property_manager｜
jgb/D/entrusted-contract-upload-file-size-limit｜委託合約上傳既有檔案限制多大？（畫面寫最大 6MB，上傳元件實際上限是 10MB）｜target_user=property_manager｜
jgb/D/entrusted-contract-fees｜委託合約的收費分頁要設定什麼？（服務費或包租金額的計算模式與週期，押金提示不得超過兩個月租金）｜target_user=property_manager｜
jgb/D/entrusted-contract-landlord-info｜委託合約的房東資訊怎麼填？（房東註冊或房東免註冊；免註冊時要選個人房東或法人房東身份）｜target_user=property_manager｜
jgb/D/entrusted-contract-manager-info｜委託合約的經理人資訊分頁要填什麼？（選簽約公司並帶出公司、經紀人與租賃住宅管理人員資訊、指定經理人、電子簽名圖章）｜target_user=property_manager｜
jgb/D/entrusted-contract-payment｜委託合約收付款資訊怎麼設定？（沒有選擇器，固定顯示「出租方帳戶」與「管理方帳戶」兩個現金收付區塊，後者必填）｜target_user=property_manager｜
jgb/D/entrusted-contract-show-and-upload｜委託合約檢視頁面能做什麼？（查看歸檔資料、上傳既有委託合約檔案、尚未寄出邀請前可返回編輯）｜target_user=property_manager｜
jgb/D/entrusted-contract-create-entry｜委託合約怎麼建立？（委託合約列表頁「建立委託約」按鈕，需有建立合約權限，可選客製化契約書或紙本簽約）｜target_user=property_manager｜

## E 帳務（含發票、收款金流、抄表） {#E}
scope: 帳單產生與週期、催繳、滯納金、收款方式與金流商、發票、抄表與水電費；⛔ 修繕流程歸 F
### E-bill-list 帳單列表與帳單狀態 {#E-bill-list}
jgb/E/bill-list-tabs｜帳單列表分成哪些分頁？（帳單總表／草稿帳單／收款帳單／支出帳單／總收支）｜target_user=property_manager,prospect｜
jgb/E/bill-status-tabs-landlord｜「草稿帳單」「收款帳單」「支出帳單」分頁底下各分哪些狀態？｜target_user=property_manager｜
jgb/E/bill-status-tabs-tenant｜租客的帳單列表跟房東的有什麼不同？（只有收款帳單／支出帳單兩個分頁）｜target_user=property_manager,prospect｜
jgb/E/bill-actions-draft｜「草稿」狀態的帳單可以做哪些動作？（編輯／發送／移至已到帳／封存）｜target_user=property_manager｜
jgb/E/bill-actions-scheduled｜「排定發送」狀態的帳單可以做哪些動作？（只有「取消排定發送」）｜target_user=property_manager｜
jgb/E/bill-actions-archived｜「封存」狀態的帳單可以做哪些動作？（沒有任何動作，齒輪選單是空的）｜target_user=property_manager｜
jgb/E/bill-actions-unreceived｜「應到帳」狀態的收款帳單可以做哪些動作？（匯款資訊／移至已到帳／開立發票／取消帳單）｜target_user=property_manager｜
jgb/E/bill-actions-progress｜「待對帳」狀態的收款帳單可以做哪些動作？（退至應到帳／移至已到帳／開立發票，沒有取消帳單）｜target_user=property_manager｜
jgb/E/bill-actions-received｜「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單）｜target_user=property_manager｜
jgb/E/bill-actions-expense-unpaid｜「應支出」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：付款）｜target_user=property_manager｜
jgb/E/bill-actions-expense-unconfirmed｜「待對帳」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：沒有齒輪動作）｜target_user=property_manager｜
jgb/E/bill-actions-expense-paid｜「已支出」狀態的支出帳單，房東跟租客各能做什麼？（房東一律有編輯收款備註／封存；反轉帳單才多出收據／退款對帳單）｜target_user=property_manager｜
jgb/E/bill-expired-status｜帳單狀態顯示「已失效」是什麼意思？（限電錶儲值帳單，4 天繳費期限）｜target_user=property_manager,prospect｜
jgb/E/bill-list-keyword-search｜帳單列表怎麼用關鍵字搜尋？（可指定用案名／地址／租客／ID／手機／信箱／帳單名稱／虛擬帳號／合約帳單共 9 種比對）｜target_user=property_manager｜
jgb/E/bill-list-export｜帳單總表怎麼匯出？（要先勾選帳單才會出現匯出選項；全選走篩選條件、勾選部分筆數走ID清單；其他分頁另有一套匯出流程）｜target_user=property_manager｜
jgb/E/bill-list-bulk-action-intersection｜帳單總表勾選多筆不同狀態的帳單時，批次操作列會出現哪些動作？（只列出每一筆帳單都能做的共同動作）｜target_user=property_manager｜
jgb/E/bill-list-export-other-tabs｜「草稿帳單」「支出帳單」「總收支」分頁的匯出按鈕，跟帳單總表不是同一套（不需要先勾選，走另一個較舊的匯出流程）｜target_user=property_manager｜
jgb/E/bill-list-income-export-social-housing｜「收款帳單」分頁固定的匯出按鈕，什麼時候會多出「匯出租客繳費證明」子選項？（只有身分類別為社會住宅的帳號才有）｜target_user=property_manager｜
jgb/E/bill-list-special-team-cvs-buttons｜「應到帳」「已到帳」狀態，特定合作團隊的帳號會多出哪些按鈕？（應到帳：匯入發票；已到帳：匯出收據／匯入收據／批次匯出收據）｜target_user=property_manager｜
jgb/E/bill-balance-tab-export-submenu｜「總收支」分頁的匯出按鈕，特定合作團隊的帳號會多出什麼子選項？（匯出收支明細表）｜target_user=property_manager｜
jgb/E/bill-list-batch-shortcuts｜「草稿帳單」分頁右上角有哪些批次建立帳單的快捷按鈕？（新增週期帳單／新增批次帳單／排定發送帳單／批次編輯帳單，Excel新增帳單僅限特定合作團隊；帳單總表沒有這些按鈕）｜target_user=property_manager｜
jgb/E/bill-scheduled-send-rule｜「排定發送帳單」有什麼限制？（只有度數填完的帳單才能排，每天中午 12 點統一發送）｜target_user=property_manager｜
jgb/E/bill-single-notification-deeplink｜帳單通知信裡的連結點進去會看到什麼？（帳單列表只先列出通知裡的那幾張帳單，自己改篩選後回到一般列表）｜target_user=property_manager｜
jgb/E/bill-balance-tab｜「總收支」分頁的用途是什麼？（「全部」混列已到帳與已支出的帳單，另有已到帳、已支出、應到帳、應支出各自的頁籤）｜target_user=property_manager｜
jgb/E/bill-notify-channels｜帳單通知走哪些管道？通知對象是誰？（免註冊租客可分別開關 Email／簡訊，已註冊租客固定收 Email 與站內通知、已綁定 LINE／FB 另收推播；只發給帳單本身的那位承租人）｜target_user=property_manager,prospect｜
jgb/E/bill-invoice-void-limitation｜發票可以線上作廢嗎？（可在帳單詳細頁作廢，但只支援 ezPay；其他金流商的發票作廢不了，已開折讓的發票也不能再作廢）｜target_user=property_manager,prospect｜
jgb/E/bill-notify-remittance-visibility｜「通知已匯款」按鈕什麼時候才會出現？（租客付款資訊視窗只在非線上金流收款的帳單才有；應支出帳單的齒輪選單則沒有這個限制）｜target_user=property_manager,prospect｜
jgb/E/bill-archive-precondition｜帳單要什麼狀態才可以直接封存？（「待發送」跟「已到帳」都可以直接封存，不用先轉成已到帳；可勾選多筆一次封存）｜target_user=property_manager｜
jgb/E/bill-deposit-receipt-no｜押金收據號碼是系統自動產生的嗎？（特定合作團隊的客製功能，號碼透過 Excel 匯出／匯入手動填寫，系統不會自動編流水號）｜target_user=property_manager,prospect｜
jgb/E/bill-scheduled-contract-ended-guard｜合約已結束、但底下還留著未來計費期間的租金帳單，系統排定發送時會怎麼處理？（系統自動排定發送／自動寄出都會跳過不寄，但不會刪除帳單；業者手動排定發送則不受這條規則限制；批次寄出依帳單 id 由小到大處理，沒有可指定的發送順序）｜target_user=property_manager｜
jgb/E/bill-remind-resend-by-support｜業者可以請 JGB 客服代發催繳通知嗎？（此操作需由 JGB 客服協助；業者端沒有自助重發催繳的介面）｜target_user=property_manager,prospect｜
jgb/E/bill-cvs-barcode-overdue-payment｜超商代碼繳費逾期後才繳，帳單還會入帳嗎？（系統不檢查代碼期限，完全依金流商回傳的付款結果；代碼逾期後是否還能繳費屬外部規定，系統不判斷）｜target_user=property_manager,prospect｜
jgb/E/bill-receipt-feature-roadmap｜收據功能還會不會有新的開發？（現行已到帳帳單一律可以看到系統寄送的收據，目前沒有公開的後續開發時程）｜target_user=property_manager,prospect｜
### E-bill-create-edit 建立與編輯帳單（單筆、批次、週期批次） {#E-bill-create-edit}
jgb/E/bill-create-modes｜新增帳單有哪幾種頁面？（新增帳單／新增批次帳單／新增週期帳單／編輯帳單）｜target_user=property_manager,prospect｜
jgb/E/bill-create-target｜新增帳單時「對象」可以選哪些？（租客／大房東／物件／其他）｜target_user=property_manager｜
jgb/E/bill-batch-vs-cycle｜「新增批次帳單」跟「新增週期帳單」有什麼不同？（批次是每個對象各一張，週期是一次產出各期帳單；兩者都可在租客與物件之間切換）｜target_user=property_manager,prospect｜
jgb/E/bill-cycle-schedule-fields｜新增週期帳單的「繳費週期」設定要填哪些欄位？（繳費週期／繳費截止日／截止日設定／帳單週期制度）｜target_user=property_manager｜
jgb/E/bill-cycle-amortization｜「總額（自動分攤）」欄位什麼時候才會出現？（只有新增週期帳單、且團隊開通社區投報率時）｜target_user=property_manager｜
jgb/E/bill-fee-item-rules｜帳單費用細目填寫有什麼規則？（度數欄位最多小數點後 2 位、電水瓦斯金額欄位限制小數點後 2 位、當期度數不可小於上期度數）｜target_user=property_manager｜
jgb/E/bill-title-field｜「帳單標題」最多可以輸入幾個字？（45 個字）｜target_user=property_manager｜
jgb/E/bill-remark-field｜「帳單備註」最多可以輸入幾個字？（150 個字）｜target_user=property_manager｜
jgb/E/bill-internal-note-field｜「內部備註」最多可以輸入幾個字？誰看得到？（100 個字，僅供業者團隊成員查看／編輯，租客看不到）｜target_user=property_manager｜
jgb/E/bill-internal-note-visibility｜「內部備註」在哪些地方會出現？（只給業者團隊成員看：新增帳單單筆與編輯帳單可填，帳單列表欄位與帳單明細可看；批次／週期帳單頁面不顯示）｜target_user=property_manager｜
jgb/E/bill-payment-method-account-pair｜新增帳單時付款方式跟收款帳戶一定要一起填嗎？（兩者要嘛都空、要嘛都填；固定虛擬帳號例外）｜target_user=property_manager｜
jgb/E/bill-tenant-unverified-draft-lock｜租客還沒完成驗證時，發給他的帳單會怎樣？（帳單卡在草稿分頁，發不出去；但可以手動移至應到帳/已到帳）｜target_user=property_manager,prospect｜
jgb/E/bill-submit-button-behavior｜新增帳單頁面下方送出按鈕的文字跟行為會依情境改變（送出／發送簽核／簽核中／預覽帳單）｜target_user=property_manager｜
jgb/E/bill-contract-payment-prefill｜新增帳單選租客當對象時，付款方式會自動帶入合約的收款設定嗎？（會，但帳戶已停用/不可取號等情況不會亂猜）｜target_user=property_manager｜
jgb/E/bill-partial-month-proration｜不足一個月的租金怎麼算？（依天數比例；預設團隊以剩餘天數 ÷ 該月曆天數，逐月產帳以實際天數 ÷ 該期帳單天數，不是固定除以 30）｜target_user=property_manager,prospect｜
jgb/E/bill-power-reading-draft-defaults｜草稿帳單的電費度數要自己填嗎？（草稿階段度數預設留空；物件有綁定智慧電錶時，可在編輯頁按「取得即時電錶度數」先帶入）｜target_user=property_manager｜
### E-bill-stats 帳單統計與報表 {#E-bill-stats}
jgb/E/bill-stat-overview｜「統計報表」的「當前表現」分頁顯示什麼？（收款情況／支出情況卡片）｜target_user=property_manager,prospect｜
jgb/E/bill-stat-monthly-tabs｜統計報表除了「當前表現」，還有「每月報表」「每月對帳單」分頁，但只有特定合作團隊看得到｜target_user=property_manager｜
jgb/E/bill-monthly-report-upload｜「每月報表」跟「每月對帳單」分頁在做什麼？（依社區/物件上傳與下載每月的物件報表、對帳單檔案）｜target_user=property_manager｜
### E-social-housing-report 社宅報表 {#E-social-housing-report}
jgb/E/social-housing-sheet-list｜社宅報表的「清冊列表」在列什麼？（每個媒合編號底下的表單勾選與修繕費、申請期數）｜target_user=property_manager｜
jgb/E/social-housing-sheet-contract-version｜社宅報表上方的合約版本切換列是做什麼用的？（切換不同版本的社宅合約，每次查詢都會帶著這個版本一起送出）｜target_user=property_manager｜
jgb/E/social-housing-sheet-make-form｜社宅報表怎麼製作表單？（填撥款日、勾選表單後按「製作表單」，會記錄成清冊紀錄）｜target_user=property_manager｜
jgb/E/social-housing-sheet-export-history｜社宅報表的「匯出歷史」會記錄幾筆匯出動作？（系統至多記錄近 30 筆）｜target_user=property_manager｜
jgb/E/social-housing-sheet-archive｜社宅報表的「歸檔」是什麼意思？（操作按鈕是「確定歸檔」；綠色「歸檔」標籤只在已歸檔後才出現）｜target_user=property_manager｜
jgb/E/social-housing-sheet-program-scope｜社宅報表的「社會住宅」身份可以對應到哪個地方政府的社宅方案？（系統只定義身份類別，不判斷方案適配）｜target_user=property_manager｜
### E-balance-invoice 差額發票（群組、底租、社區層開關） {#E-balance-invoice}
jgb/E/balance-invoice-community-switch｜差額發票要在哪裡設定？（團隊開通後在「差額發票管理」建立差額群組；社區編輯頁的差額發票開關只對部分特定合作團隊顯示）｜target_user=property_manager,prospect｜
jgb/E/balance-invoice-group-statuses｜差額發票群組總表有哪些狀態？（尚未生效／進行中／歷史／封存）｜target_user=property_manager｜
jgb/E/balance-invoice-list-columns｜差額發票群組總表列表裡看得到哪些欄位？（ID／出租物件數／本月發票狀態／累積成本／累積收入／累積發票金額）｜target_user=property_manager｜
jgb/E/balance-invoice-group-basic-info｜建立差額發票群組要填哪些基本資料？（群組名稱／底租／租期／前期餘額／房屋座落地址／房屋稅籍編號）｜target_user=property_manager｜
jgb/E/balance-invoice-pick-and-individual-rent｜差額發票群組怎麼加入物件？每個物件的底租可以自訂嗎？（群組可開「自訂個別底租」，把群組底租總額分配給各物件）｜target_user=property_manager｜
jgb/E/balance-invoice-group-detail-tabs｜差額發票群組詳細頁面看得到什麼？（招租數量／本月應收金額／本月已收金額，以及三個分頁）｜target_user=property_manager｜
jgb/E/balance-invoice-monthly-invoice-table｜「差額總表」裡每個月的差額怎麼看、怎麼開發票？（累積成本、累積收入、差額、是否開發票、發票金額、發票字軌）｜target_user=property_manager｜
jgb/E/balance-invoice-timing｜差額發票什麼時候自動產生？（一般業者每月 1 日 03:00 開立上月發票；特定團隊另有自己的時程）｜target_user=property_manager｜
jgb/E/balance-invoice-group-action-menu｜差額發票群組的動作選單有哪些選項？什麼時候不能用？（編輯群組／開立發票／封存群組／刪除群組；列表頁不能用時反灰，詳細頁直接不顯示；另有查看歷程圖示）｜target_user=property_manager｜
jgb/E/balance-invoice-refund-report-column｜差額發票收支表的租金退款／減免怎麼呈現？（列在「租金增(減)(B)」欄，以負數表示）｜target_user=property_manager｜
jgb/E/balance-invoice-rent-item-rule｜差額發票收支表怎麼判斷一個帳單品項算不算「租金」收入？（系統預設品項看名稱是不是「租金」「退租金」；自訂品項看品項性質）｜target_user=property_manager｜
jgb/E/balance-invoice-entity-type-change｜身分從法人改成自然人後，差額發票群組要怎麼重新設定？（系統沒有專用的身分切換規則）｜target_user=property_manager｜
jgb/E/balance-invoice-unsigned-contract｜合約還沒簽回時能不能開發票或收據？（發票看合約的開票設定、押金收據看帳單是否到帳，簽署狀態是否連動要看個案）｜target_user=property_manager｜
jgb/E/balance-invoice-anomaly-list｜帳單不在任何差額發票群組內時，JGB 怎麼處理？（列進內部「發票異常盤查」名單，處理需洽客服）｜target_user=property_manager｜
### E-virtual-account 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） {#E-virtual-account}
jgb/E/recharge-account-list-columns｜「固定虛擬帳號管理」列表看得到哪些資訊？（虛擬帳號、餘額、歷程一律都有；租客或物件欄位看團隊的固定虛擬帳號模式；有編輯權限時另有操作欄）｜target_user=property_manager｜
jgb/E/recharge-account-delete｜固定虛擬帳號要怎麼刪除？（列表操作選單選「刪除」，跳出確認視窗後才會真的刪掉）｜target_user=property_manager｜
jgb/E/recharge-account-history-content｜點開「歷程」看得到哪些內容？（每筆金額變動的時間／類型／金額／前後餘額／操作人員，有連結帳單可以點開查看）｜target_user=property_manager｜
jgb/E/recharge-account-bank-support｜固定虛擬帳號可以選哪些銀行？（聯邦、中國信託有專屬的建號流程，其餘從系統銀行清單選）｜target_user=property_manager｜
jgb/E/recharge-account-ubot-flow｜聯邦（803）虛擬帳號怎麼建立？有什麼限制？（金額鎖在帳號裡，租客月租變動要重新建一組）｜target_user=property_manager｜
jgb/E/recharge-account-ctbc-flow｜中國信託（822）虛擬帳號怎麼算出帳號？（填企業識別碼 5 碼與繳款人識別碼 8 碼由系統計算）｜target_user=property_manager｜
jgb/E/recharge-account-immutable｜虛擬帳號建立後，銀行跟帳號可以改嗎？（不行，銀行跟帳號建立後不能改；可以改餘額，以及依團隊模式改租客資料或綁定物件）｜target_user=property_manager｜
jgb/E/recharge-account-estate-binding-validation｜虛擬帳號綁定物件時，輸入物件 ID 有什麼驗證？｜target_user=property_manager｜
jgb/E/recharge-account-export｜「固定虛擬帳號管理」的「報表匯出」匯出什麼？（指定日期區間內租客匯入的入帳明細 Excel）｜target_user=property_manager｜
jgb/E/recharge-account-daily-settlement｜固定虛擬帳號的入帳是怎麼自動比對到帳單的？（入金當下即時銷帳，另有每日凌晨 03:00 排程再比對；限特定合作團隊；餘額不夠不會變成已到帳）｜target_user=property_manager｜
jgb/E/recharge-account-refund-excluded｜退押金這類要付給租客的帳單，也走固定虛擬帳號嗎？（不會，顯示的是租客本人的收款帳戶）｜target_user=property_manager｜
jgb/E/recharge-account-vs-single-use-atm｜「固定虛擬帳號管理」跟租客線上繳費產生的 ATM 虛擬帳號是同一種嗎？（不是，ATM 那組是單筆繳費用、效期 180 天）｜target_user=property_manager｜
jgb/E/recharge-account-mismatch-and-duplicate｜租客重複匯款時系統怎麼處理？（國泰世華單筆帳單 ATM 帳號已付款後重複匯入會略過；固定虛擬帳號多匯的部分留作餘額）｜target_user=property_manager｜
jgb/E/recharge-account-regenerate-expired｜逾期的虛擬帳號能不能重新產生？（此操作需由 JGB 客服協助，業者端沒有自助入口）｜target_user=property_manager｜
### E-payment-onboarding 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」） {#E-payment-onboarding}
jgb/E/payment-gateway-options｜JGB 支援哪些收款金流？身分限制是什麼？（國泰世華／永豐銀行／中國信託／藍新／愛金卡；個人房東不能開通藍新、國泰世華、永豐銀行）｜target_user=property_manager,prospect｜
jgb/E/payment-gateway-fees｜各家收款金流的費率跟入帳帳戶限制是什麼？（國泰世華／永豐銀行首次設定費 5,000 元且限本行帳戶；中國信託／藍新免費且不限本行帳戶）｜target_user=property_manager,prospect｜
jgb/E/newebpay-precondition｜開通藍新智付通前要準備什麼？（申請表要自填 09 開頭的台灣手機號碼）｜target_user=property_manager｜
jgb/E/newebpay-required-fields｜開通藍新智付通前，個人房東跟團隊各自要先填完哪些資料？｜target_user=property_manager｜
jgb/E/newebpay-payment-methods｜藍新開通時可以勾選哪些付款方式？（信用卡／Google Pay／Samsung Pay／ATM／超商代碼；國外卡要另外申請）｜target_user=property_manager,prospect｜
jgb/E/ctbc-apply-flow｜中國信託收款怎麼申請？（中信轉帳 Pay 填資料送審，ACH 驗證約 5 個工作天；中信虛擬帳號填 5 碼企業代碼即可，個人房東不能開通）｜target_user=property_manager｜
jgb/E/ctbc-form-validation｜中國信託申請表單各欄位有什麼格式限制？（聯絡電話 10 碼、銀行代碼 3 碼、銀行帳號 10～16 碼）｜target_user=property_manager｜
jgb/E/payment-gateway-withdrawal｜各家金流的款項要怎麼提領？（藍新要自己登入後台辦理，前 5 次免費之後每次 10 元）｜target_user=property_manager,prospect｜
jgb/E/payment-onboarding-tax-risk｜線上金流收款的資金流向會不會有稅務申報風險？（系統負責收款；稅務風險屬稅捐機關與業者自身規劃，系統不判斷）｜target_user=property_manager,prospect｜
jgb/E/cash-payment-account-management｜「現金收款帳戶」怎麼管理？（可以新增、編輯、移除；需要收款設置編輯權限）｜target_user=property_manager｜

## F 修繕 {#F}
scope: 報修、派工、進度與狀態、修繕通知；⛔ 費用入帳歸 E
### F-repair-list 修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存） {#F-repair-list}
jgb/F/repair-status-tabs｜修繕單總表有哪些狀態分頁？（申請修繕、安排修繕、完成修繕、結單、封存，各代表什麼階段）｜target_user=property_manager,prospect｜
jgb/F/repair-list-search-filter｜修繕單總表可以怎麼搜尋或篩選？（案名／地址／經理人／租客關鍵字，加上單一組「修繕單時間段」下拉：報修時間起訖／最後更新時間起訖／7 日內申請報修三選一，還有分類／項目／是否緊急）｜target_user=property_manager｜
jgb/F/repair-list-columns｜修繕單總表的表格欄位顯示什麼？（物件地址、分類＆項目、報修日期、最後更新、結算金額、房東/管理者、租客）｜target_user=property_manager｜
jgb/F/repair-list-sort-and-pagination｜修繕單總表怎麼排序、一頁看幾筆？（每頁 30／60／90 筆可選；排序選項裡的「結算金額」只有房東方帳號才看得到）｜target_user=property_manager｜
jgb/F/repair-create-button-visibility｜「新增修繕單」按鈕誰看得到？（租客一定有；房東方要有「新增&編輯&刪除所屬」或「新增&編輯&刪除所有」修繕資料其中一項權限）｜target_user=property_manager｜
jgb/F/repair-total-visibility｜「結算總金額」是什麼？（只有房東方帳號登入時才會顯示；這個數字只加總目前這一頁看得到的修繕單，換頁或換每頁筆數就會不一樣）｜target_user=property_manager｜
jgb/F/repair-export-visibility｜誰能匯出修繕單？（要另外有匯出修繕資料的權限；而且這顆按鈕只有在「新增修繕單」按鈕會出現的身分底下才會一起出現，單獨有匯出權限而沒有編輯權限的房東方帳號看不到它）｜target_user=property_manager｜
jgb/F/repair-move-status-from-list｜修繕單總表怎麼切換狀態？（每列右邊的齒輪選單有「移至」各個狀態的選項，封存後仍然可以再移回其他狀態）｜target_user=property_manager｜
jgb/F/repair-view-only-roles｜哪些身分會看到「查看」而不是「編輯＆查看」的齒輪按鈕文字？（大房東角色，以及只有「顯示所屬」沒有「顯示所有」修繕資料權限的經理人帳號；這個文字只反映顯示修繕資料的權限，能不能移動狀態、能不能在細節頁編輯是另一組「編輯修繕」權限決定的，兩者互相獨立）｜target_user=property_manager｜
jgb/F/repair-list-filter-category-item-urgent｜修繕單總表可以用分類、項目、是否緊急篩選嗎？（可以；先選分類才能選項目，換分類會把已選的項目清空；「是否緊急」是一個勾選框，勾了才會加上這個條件）｜target_user=property_manager｜
jgb/F/repair-list-contact-card｜修繕單總表點「房東/管理者」或「租客」欄位會怎樣？（會彈出這個人的聯絡資訊卡）｜target_user=property_manager｜
### F-repair-apply 報修申請流程 {#F-repair-apply}
jgb/F/repair-apply-flow-and-entry｜怎麼申請修繕單？（【修繕管理】>【修繕單總表】右上角「新增修繕單」進入，選物件→選分類項目→填報修細節→送出，按「上一步」「下一步」在步驟間切換）｜target_user=property_manager｜
jgb/F/repair-apply-without-contract｜沒有租約在跑的物件也能申請修繕嗎？（可以，房東方只要建好物件就能申請，不用先有合約）｜target_user=property_manager,prospect｜
jgb/F/repair-apply-category-item-other｜報修分類項目怎麼選？（分類與項目都是系統設定的清單，選好之後在報修細節可以按「編輯」回上一步重選；有一個特定分類會多出讓使用者自己輸入名稱的欄位）｜target_user=property_manager｜
jgb/F/repair-apply-detail-fields｜報修細節要填什麼？（項目分類、問題必填；預約時段依身分決定是否必填；緊急修繕、佐證照片、備註選填；「通知及同步租客」是房東代租客申請時會看到的一個開關，但目前沒有實際作用）｜target_user=property_manager｜
jgb/F/repair-apply-reservation-slots｜預約時段規則是什麼？（畫面上標示為必填，但實際上只有租客身分申請時系統才會擋下沒填的情況；房東申請時就算不填也能送出）｜target_user=property_manager｜
jgb/F/repair-apply-photo-limit｜報修可以附照片或影片嗎？（照片最多 10 張；影片最長 30 秒或 100MB；支援 jpeg／jpg／png 圖片與 mov／mp4／webm 影片）｜target_user=property_manager,prospect｜
jgb/F/repair-apply-notifications｜新增修繕單後誰會收到通知？（租客本人、團隊擁有者會收到 Email，租客如果有綁定 LINE 也會收到 LINE 通知）｜target_user=property_manager,prospect｜
jgb/F/repair-notifications-by-stage｜安排廠商、完成修繕、結單時還會發哪些通知？（依幫助中心教學：填寫廠商資訊後、完成修繕儲存後、移到結單狀態時，租客或團隊都會再收到一次通知）｜target_user=property_manager｜
### F-repair-edit 修繕單編輯 {#F-repair-edit}
jgb/F/repair-edit-progress-timeline｜修繕單細節頁的進度時間軸顯示什麼？（申請修繕、安排修繕、完成修繕、結單、封存五個階段各自的日期，還沒到的階段不顯示日期）｜target_user=property_manager｜
jgb/F/repair-edit-print｜修繕單細節頁怎麼列印？（右上角有「列印」按鈕，會叫出瀏覽器內建的列印視窗，可以印出來或存成 PDF）｜target_user=property_manager｜
jgb/F/repair-edit-switch-status｜修繕單細節頁怎麼切換狀態？（下拉選單直接選要換到哪個階段，按「變更」儲存）｜target_user=property_manager｜
jgb/F/repair-edit-cannot-edit-roles｜誰不能編輯修繕單細節頁？（租客帳號、大房東角色都只能看，不能切換狀態、不能改廠商資訊、不能寫房東備註）｜target_user=property_manager｜
jgb/F/repair-edit-application-detail-readonly｜修繕單細節頁顯示哪些報修時填的資料？（「細節補充」區塊底下：申請日期、是否緊急、照片、聯絡電話或 Email、物件區域與時區、分類項目、問題、備註、預約時段；房東方才看得到「細節補充」這個標題與說明文字）｜target_user=property_manager｜
jgb/F/repair-edit-vendor-assign｜怎麼安排修繕廠商？（填寫修繕時間、廠商名稱、維修人員、聯絡電話，儲存後會留下歷史紀錄可以展開查看）｜target_user=property_manager｜
jgb/F/repair-edit-landlord-complete-memo｜「房東備註」要填什麼？（完成時間、備註文字最多 300 字、可以附照片，最多 10 張、單檔最大 10MB、支援 JPG／PNG／PDF；只有有編輯權限的房東方帳號能編輯）｜target_user=property_manager｜
jgb/F/repair-edit-amount-visibility｜修繕結算金額誰看得到？（「結算金額」欄位只有身分是房東的帳號才會顯示，租客看不到；這筆金額目前只是修繕單自己的紀錄文字，沒有找到跟帳單模組串接的路徑）｜target_user=property_manager｜
jgb/F/repair-edit-tenant-memo｜「房客備註」是什麼？（右邊那一欄，只有這張修繕單有填過預約時段才會出現，沒有的話會顯示「此修繕單為房東發起，無房客備註」）｜target_user=property_manager｜
jgb/F/repair-edit-share-to-vendor｜怎麼把修繕單分享出去給廠商？（在修繕單細節頁點「分享」，可以複製連結，也可以直接用 LINE 分享出去；廠商點開連結不需要登入 JGB 帳號）｜target_user=property_manager｜
### F-repair-share 修繕單分享頁 {#F-repair-share}
jgb/F/repair-share-public-link｜修繕單分享頁需要先登入嗎？（不需要，這個連結是公開的，系統特別把它排除在登入檢查之外，任何拿到網址的人都可以直接打開）｜target_user=property_manager,prospect｜
jgb/F/repair-share-visibility-summary｜分享連結誰看得到？（拿到網址的任何人都能看到這張修繕單房東方的手機／Email、物件所在區域、照片、廠商聯絡電話；金額只有在瀏覽者本人目前登入身分是房東時才會顯示，且不會核對是不是這張修繕單相關的房東或租客）｜target_user=property_manager,prospect｜
jgb/F/repair-share-no-expiry｜分享連結會過期嗎？（目前不會，系統一度寫過 30 天過期的檢查，但已經停用，現在沒有天數限制）｜target_user=property_manager｜
jgb/F/repair-share-content｜修繕單分享頁看得到什麼？（修繕申請單標題與是否緊急、照片、報修細節、安排的廠商資訊、房東備註與房客備註，全部都是唯讀；不會顯示物件廣告連結、縮圖，也沒有房東／承租方資訊側欄）｜target_user=property_manager｜

## G 裝置（IoT） {#G}
scope: IoT 門鎖、密碼、裝置廠商與狀態；⛔ 抄表歸 E
### G-power-meter 電表列表與單一電表 {#G-power-meter}
jgb/G/power-meter-list-category-tabs｜電錶清單怎麼切換分類？（所有電錶、一般型、儲值型三個分類，切換後會換一批列表）｜target_user=property_manager｜
jgb/G/power-meter-list-status-tags｜電錶清單的狀態標籤是什麼意思？（全部／供電中／斷電中／未連線，夾在分類跟清單之間；未連線含未啟用）｜target_user=property_manager｜
jgb/G/power-meter-list-search｜電錶清單怎麼用關鍵字搜尋？（可選描述、序號、設備名稱、所屬物件名稱其中一種）｜target_user=property_manager｜
jgb/G/power-meter-list-sort｜電錶清單怎麼排序？（可依設備描述、目前電度、預計可用電度排序；門鎖、攝影機、小白盒清單沒有排序選單）｜target_user=property_manager｜
jgb/G/power-meter-manufacturer-maintenance｜電錶清單出現「原廠系統維護中」是什麼意思？（維護期間度數不更新、無法儲值）｜target_user=property_manager｜
jgb/G/power-meter-vendor-unreachable｜電錶顯示「目前連不上廠商」怎麼辦？（度數不會更新、儲值送不出去；業者跟租客都看得到）｜target_user=property_manager,tenant｜
jgb/G/power-meter-service-expiry｜電錶顯示「服務到期」或「快到期」怎麼辦？（30 天內到期會提醒續訂；只有業者看得到，只出現在清單頁）｜target_user=property_manager｜
jgb/G/power-meter-list-row-fields｜電錶清單每一列顯示什麼？（型號序號、目前電度、狀態、所屬物件；儲值型才有預計可用電度與低電度警報）｜target_user=property_manager｜
jgb/G/power-meter-usage-chart-export｜電錶清單列展開後能看什麼？（用電量走勢圖可選 1/7/30/90 天；CSV 只能下載前 90 天）｜target_user=property_manager｜
jgb/G/power-meter-single-edit-tabs｜電錶編輯頁能改什麼？（儲值型有基本設定／電錶資料／開立發票三個頁籤，一般型只有基本設定）｜target_user=property_manager｜
jgb/G/power-meter-single-estate-single-bind｜一支電錶只能綁一個物件？（選擇物件的挑選頁是單選，選了一個之後其他物件會被鎖住不能再選）｜target_user=property_manager｜
jgb/G/power-meter-mode-switch｜怎麼切換電錶的供電狀態？（一般型：供電／斷電；儲值型：儲值／強開／斷電，切換中鎖按鈕只有儲值型有）｜target_user=property_manager｜
jgb/G/power-meter-basic-info-fields｜電錶資料頁的餘額、費率、預計可用電度怎麼看？（只有儲值型電錶才有這個頁籤；費率由雲端儲值系統設定，可用電度＝餘額÷費率）｜target_user=property_manager｜
jgb/G/power-meter-topup-flow｜電錶怎麼儲值？（「儲值」按鈕就在清單列上，不用展開；金額固定四個選項，維護中或連不上廠商時按鈕會變灰）｜target_user=property_manager｜
jgb/G/iot-entry-requirements｜電錶／門鎖／攝影機／小白盒頁面需要什麼條件才能進入？（需訂閱方案、且未超過物件數量上限）｜target_user=property_manager,prospect｜
jgb/G/power-meter-invoice-tab-fields｜開立發票頁籤裡面能填什麼？（目前只有帳單是否開立發票一個選項）｜target_user=property_manager｜
jgb/G/power-meter-list-empty-state｜電錶清單沒有資料時畫面顯示什麼？（分類內沒有設備寫「此分類尚無設備」；完全沒綁定寫「目前尚無綁定設備」，租客看不到綁定引導連結）｜target_user=property_manager｜
### G-device-page 裝置頁（門鎖、攝影機、小白盒） {#G-device-page}
jgb/G/device-page-shared-list｜門鎖／攝影機／小白盒清單長什麼樣？（型號序號、描述、狀態、所屬物件四欄，可依關鍵字搜尋，沒有排序選單）｜target_user=property_manager,prospect｜
jgb/G/device-page-lock-open-close｜門鎖清單怎麼直接開門／鎖門？（開門一定有、鎖門只有特定廠商支援；離線時按鈕不會顯示）｜target_user=property_manager｜
jgb/G/device-edit-tabs-by-type｜裝置編輯頁的頁籤，門鎖跟攝影機／小白盒不一樣？（門鎖多出密碼設定、開門記錄兩個頁籤）｜target_user=property_manager｜
jgb/G/device-lock-type-and-binding-limit｜私人門鎖跟共用門鎖差在哪？（私人只能綁一個物件，共用可以綁多個）｜target_user=property_manager,prospect｜
jgb/G/device-lock-passwords-three-types｜門鎖密碼有哪三種？（房東個人密碼、租客個人密碼、租客共用密碼，權限各不同）｜target_user=property_manager｜
jgb/G/device-lock-open-log｜門鎖的開門記錄怎麼看？（可依日期查詢操作時間與動作，沒有記錄時會顯示尚無記錄）｜target_user=property_manager｜
jgb/G/device-gateway-not-counted｜小白盒綁定物件跟門鎖不同在哪？（小白盒不會讓物件被標記為「IoT裝置」，也不會擋刪除）｜target_user=property_manager｜
### G-remote-unlock 遠端解鎖（輸入解鎖密碼開門） {#G-remote-unlock}
jgb/G/remote-unlock-page｜遠端解鎖連結怎麼用？（輸入共用密碼按開門，密碼錯誤或連結失效會提示原因；找不到產生這個連結的入口）｜target_user=property_manager｜
jgb/G/remote-unlock-no-login｜遠端解鎖連結需要登入嗎？（不用登入，只要有連結跟密碼就能開）｜target_user=property_manager,prospect｜

## H 幫助中心 {#H}
scope: 幫助中心入口與使用方式、教學文件位置；⛔ 各功能怎麼用歸該功能所在架（目前空架，存廢另裁）
### H-help-center 幫助中心（分類、文章、搜尋） {#H-help-center}
jgb/H/help-center-home-groups｜幫助中心首頁長什麼樣？（分類卡片顯示圖示、篇數、更新日期）｜target_user=property_manager,prospect｜
jgb/H/help-center-group-structure｜幫助中心分類頁怎麼排文章？（分類底下先分次分類，各次分類再列出文章卡片）｜target_user=property_manager,prospect｜
jgb/H/help-center-post-detail｜幫助中心文章內頁有什麼？（麵包屑、分享到 Facebook／LINE、上下篇導覽、相關文章）｜target_user=property_manager,prospect｜
jgb/H/help-center-search｜幫助中心搜尋怎麼運作？（比對標題與內文、多個關鍵字要同時出現、可加選分類）｜target_user=property_manager,prospect｜
jgb/H/help-center-trial-form｜幫助中心的「立即免費試用」視窗是什麼時候跳出來的？（首頁停留 60 秒自動彈出，四個欄位都要填）｜target_user=property_manager,prospect｜

## I 方案與導入 {#I}
scope: 方案比較與試用、功能矩陣、導入與資料遷移、批次匯入流程、競品（deliberate_no）；⛔ 找真人走 handoff
### I-pricing 方案、價格與免費試用 {#I-pricing}
jgb/I/pricing-plan-tiers-overview｜JGB 有哪些方案？（免費試用、體驗方案、入門／熱門／專業四級距、企業方案）｜target_user=property_manager,prospect｜
jgb/I/pricing-free-trial-eligibility｜免費試用怎麼開始、能用多久？（新建立房東身分自動取得，一個週期後不自動續訂）｜target_user=property_manager,prospect｜
jgb/I/pricing-free-trial-feature-scope｜免費試用不能用哪些功能？（最多 5 個物件，不支援團隊與門鎖電錶等進階功能）｜target_user=property_manager,prospect｜
jgb/I/pricing-individual-vs-corporate-team｜個人房東與企業團隊方案差在哪？（人員管理四項功能、自動對帳與分店管理起始級距不同）｜target_user=property_manager,prospect｜
jgb/I/pricing-free-vs-experience-plan｜免費方案與體驗方案差在哪？（前者系統贈送 5 個物件，後者每月付費可續訂 10 個物件）｜target_user=property_manager,prospect｜
jgb/I/pricing-calc-by-estate-count｜怎麼用物件數量試算方案價格？（50～500 物件拉桿試算，超過 500 個要洽企業方案）｜target_user=property_manager,prospect｜
jgb/I/pricing-quota-near-full-notice｜物件額度快滿了會怎樣？（剩 5 個以下觸發提醒，剛好剩 5 個另寄 Email）｜target_user=property_manager｜
jgb/I/pricing-enterprise-plan-offer｜企業方案提供什麼？（客製化 LOGO 頁與網址頁，需另外聯繫洽談）｜target_user=property_manager,prospect｜
jgb/I/pricing-trial-plan-landing-page｜體驗方案介紹頁講什麼？（每月費用試算、體驗方案資格需求、客戶見證、免費試用／免費諮詢按鈕）｜target_user=property_manager,prospect｜
jgb/I/pricing-plan-price-basis｜方案價格怎麼算、年繳有折扣嗎？（體驗方案月費固定台幣 100 元；一般方案年繳等於 10 個月的月費）｜target_user=property_manager,prospect｜
jgb/I/pricing-quota-full-block｜物件額度用滿了會怎樣？（新增物件、匯入等入口會被擋下並提示升級方案）｜target_user=property_manager｜
### I-subscription-payment 訂閱、付款與訂單 {#I-subscription-payment}
jgb/I/subscription-choose-plan-flow｜訂閱頁怎麼選方案？（體驗方案、依物件數量拉桿的基本方案、企業方案洽談三選一）｜target_user=property_manager｜
jgb/I/subscription-payment-authorization-flow｜訂閱怎麼扣款？（先試刷 TWD 1 驗證信用卡、藍新金流走 SSL／PCI-DSS）｜target_user=property_manager,prospect｜
jgb/I/subscription-invoice-fields｜訂閱時發票資訊要填什麼？（二聯式／三聯式、統一編號僅三聯式必填；地址欄目前沒有掛必填檢查）｜target_user=property_manager｜
jgb/I/subscription-coupon-and-renewal-discount｜訂閱優惠碼怎麼用？（輸入後即時驗證，續訂優惠次數沒有設定上限時顯示「終生」）｜target_user=property_manager｜
jgb/I/subscription-my-plan-page｜我的方案頁看什麼？（方案卡片、付款方式綁定狀態、溢繳費用）｜target_user=property_manager｜
jgb/I/subscription-change-card-flow｜怎麼換綁信用卡？（更新要重新授權並試刷 1 元，變更方案按鈕需要對應權限）｜target_user=property_manager｜
jgb/I/subscription-plan-change-billing｜換方案時舊方案沒用完的錢會退嗎？（按剩餘天數比例換算成溢繳金，直接折抵新方案費用）｜target_user=property_manager｜
jgb/I/subscription-cancel-effect｜取消訂閱會怎樣？（立即停止自動續訂與已授權信用卡，但用到目前效期結束才失效）｜target_user=property_manager｜
jgb/I/subscription-renewal-charge-failure｜自動續訂扣款失敗會怎樣？（方案資料整個清空、限額歸零、所有物件立即下架，沒有寬限期）｜target_user=property_manager｜
jgb/I/orders-payment-history｜付款紀錄頁看什麼？（扣款日、訂單編號、付款內容、金額、收據）｜target_user=property_manager｜
jgb/I/payment-vendor-options-overview｜收款設置支援哪些金流商？（藍新／國泰世華／永豐／中信／icash Pay／現金收款帳戶，各家設定費與手續費不同）｜target_user=property_manager｜
jgb/I/payment-vendor-eligibility-by-role-and-plan｜哪些身分或方案不能開通某些金流商？（個人房東不能開藍新／國泰世華／永豐，免費方案／體驗方案不能開國泰世華／永豐）｜target_user=property_manager｜
jgb/I/payment-newebpay-setup-details｜藍新金流申請要注意什麼？（個人房東無法申請；手機與 Email 送出後不能改，每個金流最多開三組帳號，需審核）｜target_user=property_manager｜
jgb/I/payment-vendor-edit-after-binding｜金流綁定後還能改嗎？（除了國泰世華，其他金流商明細頁都是唯讀不能重送）｜target_user=property_manager｜
jgb/I/payment-icash-ctbc-setup｜icash Pay／中信收款帳戶申請要多久？（智付通約 2-5 個工作天，中信 ACH 驗證約 5 個工作天）｜target_user=property_manager｜
jgb/I/payment-receipt-template-options｜收據範本有哪些？（財政部包租業租金收據範本只有法人／社宅團隊才看得到）｜target_user=property_manager｜
jgb/I/payment-receipt-deposit-team-extras｜押金收據能自訂摘要跟蓋章嗎？（摘要與三顆收款章都只有特定合作團隊才看得到）｜target_user=property_manager｜
jgb/I/payment-bill-e-invoice-setup｜帳單怎麼開電子發票？（要先聯繫 JGB 業務開通加值服務，開通後才會出現稅與發票分頁）｜target_user=property_manager,prospect｜
jgb/I/payment-permission-menu-visibility｜沒有查看權限會怎樣？（收款設置與訂閱方案選單整個不會出現）｜target_user=property_manager｜
jgb/I/payment-bill-autosend-and-recipient｜帳單可以自動排程發送、指定收款人嗎？（提前 0～20 天自動發送，收款人可選原簽約者／主要經理人／自訂）｜target_user=property_manager｜
### I-demo-booking 預約 demo {#I-demo-booking}
jgb/I/demo-form-fields｜預約 demo 表單要填什麼？（公司、職稱、聯絡方式、物件所在地、感興趣功能與諮詢內容）｜target_user=property_manager,prospect｜
jgb/I/demo-form-option-lists｜demo 表單的下拉選項有哪些？（物件數量 7 級距、團隊人數 6 級距、感興趣功能 6 項）｜target_user=property_manager,prospect｜
jgb/I/demo-form-submit-result｜demo 表單送出後多久有人聯繫？（顯示感謝頁，2-3 個工作天內專人聯繫）｜target_user=property_manager,prospect｜
jgb/I/demo-form-actual-validation-scope｜demo 表單哪些欄位真的會被系統擋下？（系統實際只驗公司、姓名、電話、Email 四項）｜target_user=property_manager｜
### I-control-panel 控制台（設定、通知信範本、自動化任務） {#I-control-panel}
jgb/I/control-panel-entry-scope｜控制台首頁目前能用什麼？（目前只有「任務管理器」一個項目可以點擊進入）｜target_user=property_manager｜
jgb/I/control-panel-setting-shell｜進入控制台設定後看到什麼？（本身只是麵包屑與側欄外殼，內容是任務管理器頁面）｜target_user=property_manager｜
jgb/I/task-manager-purpose｜任務管理器是做什麼用的？（設定週期性任務或預定通知，系統會提前自動開單並寄信）｜target_user=property_manager｜
jgb/I/task-manager-type-behavior-scope｜新增任務能選哪些類型？（目前只開放「通知」類型，行為是信件通知或站內通知）｜target_user=property_manager｜
jgb/I/task-manager-cycle-options｜任務週期怎麼設定？（單位分年／月，方式可選僅一次、持續不停、特定日期結束、重複特定次數）｜target_user=property_manager｜
jgb/I/task-manager-form-fields｜新增任務表單有哪些欄位？（任務名稱、任務類型、關聯物件、任務行為、任務時間、重複間隔、結束時間、通知對象、通知內容）｜target_user=property_manager｜
jgb/I/task-manager-edit-delete-copy｜已建立的任務怎麼編輯／刪除？（每筆任務可編輯、複製、刪除，編輯週期任務可選只改這次或連後續一起改）｜target_user=property_manager｜
jgb/I/notification-mail-settings｜通知信副本信箱怎麼設定？（預設收件為團隊擁有者信箱，每個通知信最多再加 3 組副本）｜target_user=property_manager｜
jgb/I/control-panel-access-restriction｜誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定」子路徑才會擋）｜target_user=property_manager｜
### I-marketing-home 官網首頁 {#I-marketing-home}
jgb/I/homepage-sections-overview｜官網首頁有哪些區塊？（橫幅、熱門物件、優質租管業者推薦、特色介紹、企業夥伴、最新消息）｜target_user=prospect｜
jgb/I/homepage-ten-features-actual-count｜首頁「JGB平台十大特色」實際列出幾項？（標題寫十大，目前輪播只設定 3 項：管理儀表板、線上合約管理、即時帳務報表）｜target_user=prospect｜
jgb/I/homepage-city-count-cta｜首頁說 JGB 在東南亞幾個城市使用？（超過 8 個城市，旁邊有免費試用／免費諮詢按鈕）｜target_user=prospect｜
jgb/I/homepage-presales-assistant-visibility｜首頁的線上諮詢小幫手正式站看得到嗎？（目前設定為正式環境不顯示，只在非正式環境出現）｜target_user=property_manager｜
jgb/I/homepage-three-advantages｜首頁「JGB平台擁有三大優勢」是哪三項？（提高出租效率、自動化管房流程、提升租客服務品質）｜target_user=prospect｜
jgb/I/homepage-latest-news-section｜首頁「最新消息」顯示什麼？（沒有消息資料時整區塊不會出現，點擊會開啟幫助中心文章）｜target_user=prospect｜
jgb/I/homepage-enterprise-partners-section｜首頁「企業夥伴」放了什麼？（10 個合作夥伴 logo 排成靜態方格，不是輪播）｜target_user=prospect｜
### I-hicloud-order 中華電信雲市集訂單頁 {#I-hicloud-order}
jgb/I/tcloud-order-info-fields｜雲市集訂單頁顯示什麼？（訂單編號、時間、採購方案、價格、點數折抵、付款狀態）｜target_user=property_manager,prospect｜
jgb/I/tcloud-payment-instructions｜雲市集訂單怎麼付款？（國泰世華一次性虛擬帳號限 WebATM，2 個工作天內付款，付款後 2 天開發票、7 天內開通）｜target_user=property_manager,prospect｜
jgb/I/tcloud-link-invalid-cases｜雲市集訂單連結為什麼會失效？（連結簽章驗證不過，或訂單編號查無資料，都會導回官網首頁）｜target_user=property_manager,prospect｜
