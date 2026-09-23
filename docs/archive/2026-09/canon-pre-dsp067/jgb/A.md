---
coarse: A
title: 帳號與身分
scope: 註冊、登入、找回帳號、身分（房東／租客／法人／社宅）與個人資料、聯絡方式變更；⛔ 團隊成員權限歸 B
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
---
## 帳號與身分 {#A}
### 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） {#jgb/A/account-registration}
- phrasings:
  - {text: "怎麼開帳號", source: "koyu:onboarding1#14", status: approved}
  - {text: "屋主帳號怎麼用", source: "koyu:Landlordonboarding00#15", status: approved}
  - {text: "租客怎麼開帳號", source: "koyu:tenantintro.register#13", status: approved}
  - {text: "帳號忘記了怎麼救", source: "koyu:slug01#6", status: approved}
  - {text: "帳號資訊怎麼變更", source: "koyu:slug95#13", status: approved}
  - {text: "我忘記帳號怎麼辦?", source: "helpcenter:slug01", status: approved}
  - {text: "登入帳號怎麼找回", source: "koyu:slug01#13", status: approved}
  - {text: "註冊要用email還是手機", source: "koyu:onboarding1#5", status: approved}
  - {text: "我要改我的email", source: "koyu:slug95#4", status: approved}
  - {text: "email打錯了怎麼辦", source: "koyu:slug00#10", status: approved}
- sources: [draft:batch#16, helpcenter:Landlordonboarding01, helpcenter:onboarding1, draft:batch#15, helpcenter:Landlordonboarding06Finance, kb:3435, helpcenter:tenantintro.register]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
註冊很快：到 JGB 網站點「註冊」，輸入 Email 收驗證碼，填基本資料就完成；也可以用 Facebook、Gmail、LINE 第三方帳號註冊，系統會一併建立 Email 登入。
一個帳號同時可有房東與租客身分，手機號碼作輔助登入。
租客不一定要自己註冊，房東建立合約時輸入租客 Email 或手機發出簽約邀請，租客也能從電子合約完成註冊。
JGB 帳號註冊以 Email 為主路徑：1. 進入註冊頁輸入 Email 並通過機器人驗證；2. 收 Email 驗證碼完成信箱驗證（驗證碼效期 5 分鐘，訊息開頭有三個英文字母的識別碼，請輸入與畫面識別碼相符那封信裡的碼）；3. 設定密碼；4. 選擇身分（房東/租客）；5. 綁定手機（簡訊驗證）——這一步可先跳過，之後再到帳號設定補綁。
收到合約邀請的租客用邀請信中的連結進入註冊即可。
註冊入口在 JGB 官網首頁：先點畫面右上方的「登入」，進入頁面後再點上方藍字「立即註冊」，就會進入註冊頁面讓你輸入想註冊的 Email。
輸入 Email 並點「繼續」後，平台會自動寄一組驗證碼到該信箱，回到頁面輸入收到的驗證碼，驗證碼正確系統就會自動進入下一個註冊步驟。
註冊途中發現信箱填錯，可在驗證碼頁面點藍字重新輸入信箱，系統會重新寄送驗證信，不必從頭再來。
驗證碼通過後會跳到帳號設定介面，在此輸入帳號姓名與密碼，再點「完成註冊」即完成整個註冊流程；設定完的密碼請務必記住。
用 SSO 第三方帳號註冊時系統仍會連結進 Email 帳號註冊流程，用意是讓使用者除了 SSO 登入外同時保有 Email 登入方式，避免未來忘記當初是用哪種方式登入。
租客從合約邀請註冊的路徑：簡訊收到邀請就點訊息裡的藍色連結，Email 收到邀請就點郵件中的「查看合約」，會先進入該物件的閱覽頁面，確認物件條件無誤後點右下方的「查看合約」，系統會跳到登入頁，此時點「立即註冊」即可用一般的 Email 驗證碼流程完成註冊，接著就能繼續完成合約。
房東在建立合約時對尚未註冊的租客送出邀請簽約後，畫面會進入「待租客簽回」，在那裡可以看到這位尚未註冊會員租客的 Email 帳號，同時租客會收到簽約邀請郵件。
不論是個人房東或包租代管業者，只要之後要用 JGB 系統管理物件都建議先創建一個帳號；包租代管業者若要開立公司、創建團隊，另有創建團隊的新手上路教學。

### 怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口） {#jgb/A/login-methods}
- phrasings:
  - {text: "怎麼登入", source: "owner:20260916", status: approved}
  - {text: "登入方式", source: "owner:20260916", status: approved}
  - {text: "手機號碼登入", source: "owner:20260916", status: approved}
  - {text: "房東身分登入", source: "owner:20260916", status: approved}
  - {text: "租客登入入口", source: "owner:20260916", status: approved}
- sources: [helpcenter:Landlordonboarding01, helpcenter:onboarding1]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
登入入口在 JGB 官網首頁右上方的「登入」，進入 JGB 登入畫面後，房東或管理者點房東/管理者那一側的「前往登入」，租客則點租客那一側的「前往登入」，兩種身分的登入入口是分開的。
房東與租客都可以用 Email 登入；若註冊後已綁定手機號碼，也可以改用手機號碼登入。
在登入頁輸入帳號與密碼即可登入；若註冊時是綁定 Facebook、Gmail、LINE 等 SSO 第三方帳號，要點頁面下方的第三方登入選項，以同一個 SSO 管道登入。
登入畫面會先要求選擇身分，例如選「以房東身份登入」後再輸入帳號密碼進入系統。
登入後若想調整預設進入的身分，可點右上方頭像進入「帳號資訊」，在偏好設定裡設定「登入預設身份」。

### 用 LINE 快速登入卻被帶去註冊頁、登不進去（只認 LINE 註冊帳號、無事後綁定、改用帳密登入） {#jgb/A/line-login-redirects-to-register}
- phrasings:
  - {text: "快速登入", source: "question_summary:3967", status: approved}
  - {text: "登不進去", source: "question_summary:3967", status: approved}
  - {text: "跳到註冊", source: "question_summary:3967", status: approved}
- sources: [kb:3967]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客用 LINE 快速登入卻被帶到註冊畫面，原因是：LINE 快速登入只認「當初用 LINE 註冊」的帳號；用帳號密碼註冊的帳號沒有 LINE 綁定，目前也沒有事後補綁的功能，所以系統找不到對應帳號、只能導去註冊。
解法很單純：請租客改用帳號密碼登入即可，不需要重新註冊。
另外在 LINE 內建瀏覽器裡開啟登入頁偶爾會有狀況，可改用手機的一般瀏覽器再試。

### 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件） {#jgb/A/account-profile-settings}
- phrasings:
  - {text: "帳號資訊設定", source: "owner:20260916", status: approved}
  - {text: "個人資料在哪改", source: "owner:20260916", status: approved}
  - {text: "改頭像", source: "owner:20260916", status: approved}
  - {text: "通知語言設定", source: "owner:20260916", status: approved}
  - {text: "簽約資訊填寫", source: "owner:20260916", status: approved}
- sources: [helpcenter:onboarding2, helpcenter:slug95, helpcenter:Landlordonboarding01]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
要修改帳號資料，登入後點右上角的頭像圖示，選擇「帳號資訊」就能進入編輯畫面；編輯完成記得按右上角的「儲存」，之後若要再改也可以隨時回來編輯。
帳號資訊要在對應的身分下編輯：房東先確認目前身分為「個人房東」、租客先確認身分為「租客」，再點頭像進入「帳號資訊」。
帳號資訊裡能編輯的項目分成四塊：帳號基本資訊（姓名、綁定手機、修改密碼）、聯絡資訊（Line ID、Facebook、第二組聯絡號碼）、偏好設定（登入預設身份、時區、Email 通知語系），以及「其他設定」裡的「簽約資訊」。
簽約用的個人資料不在帳號資訊首頁，要到「其他設定」的「簽約資訊」新增，包括身分證字號、戶籍地址、通訊地址、身分證正反面照片與其他附件。
大頭照、Email 通知使用的語言、以及方便對方聯繫的社群帳號，都在帳號資訊頁直接更換；房東填的是通知租客的語言與供租客聯繫的社群帳號，租客填的則是自己收通知的語言與供房東聯繫的社群帳號。
建議註冊後先把帳號基本資料填完整，因為創建物件、發送合約時的基本訊息都來自帳號基本資料，沒有填妥完整資訊就無法發出合約。
團隊（公司）的資料不在個人的帳號資訊裡：先完成個人帳號資訊後，從左上方選單「＋新增團隊」建立或選擇所屬團隊，之後在「團隊管理」>「團隊資訊」編輯公司相關資料、通知租客的 email 語言、社群帳號、團隊介紹與相關文件。

### 租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業） {#jgb/A/registered-vs-unregistered-tenant}
- phrasings:
  - {text: "免註冊", source: "question_summary:3348", status: approved}
  - {text: "租客一定要註冊嗎", source: "owner:20260916", status: approved}
- sources: [kb:3348, helpcenter:onboarding1]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
註冊租客與免註冊租客的差異：
【註冊租客】
可透過 email 和密碼登入系統
可在系統內查看合約、帳單
可直接收到系統通知
【免註冊租客】
無法登入系統查看資料
需透過「人員管理」進行 email 驗證後才能收到通知
帳單以附件形式寄送，檔案密碼為公司統一編號
管理者需每月手動協助到帳（較麻煩）
建議盡量引導租客使用註冊帳號，以實現自動化管理。
租客要不要註冊 JGB 帳號由租客自行選擇，這是系統優化改版後的規則；租客不想註冊時，房東可以自行填寫租客的身份資料等內容來建立合約。
房東對尚未註冊會員的租客送出邀請簽約後，合約會進入「待租客簽回」畫面，在那裡可以看到這位尚未註冊租客的 Email 帳號。
尚未註冊的租客從邀請郵件的「查看合約」進入合約時，會因為還不是 JGB 會員而被帶到登入畫面，在那裡點「註冊」完成註冊後就能接續完成合約。

### Email 大小寫算不同帳號嗎（Email 為帳號識別、大小寫視為不同帳號） {#jgb/A/email-case-sensitivity}
- phrasings:
  - {text: "email大小寫", source: "owner:20260916", status: approved}
- sources: [kb:3349]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 系統將 email 作為帳號識別，大小寫不同會被視為不同帳號。
常見問題：
邀請大房東時 email 大小寫不正確，導致邀請失敗
租客用不同大小寫的 email 註冊，導致看不到合約或帳單
合約發送的 email 與租客登入的帳號不一致
請務必確認 email 完全一致（包含大小寫）。

### 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） {#jgb/A/verification-code-not-received}
- phrasings:
  - {text: "收不到驗證簡訊", source: "question_summary:3965", status: approved}
  - {text: "改用信箱註冊", source: "question_summary:3965", status: approved}
  - {text: "租客一直沒辦法註冊", source: "question_summary:3975", status: approved}
  - {text: "驗證碼收不到", source: "question_summary:3871", status: approved}
- sources: [kb:3350, kb:3871, kb:3965, kb:3975, helpcenter:slug00]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
收不到簡訊驗證碼的可能原因：
1. 訊號不佳或發生堵塞，請稍後再次重發
2. 手機安裝了來電攔截 APP（如 Whoscall），可能將驗證簡訊攔截
3. 手機同時有多款簡訊 APP（Google Messenger、FB Messenger、品牌內建等），僅有一款能接收簡訊，可能在更新時設定異常
4. 填寫了錯誤的手機號碼或 email
建議先確認手機號碼正確，檢查攔截設定後再次重發驗證碼。
租客註冊或簽約時收不到驗證信/驗證碼，依序排查：一、檢查垃圾信件匣與促銷分類；二、確認信箱/手機號碼輸入正確（多一個空格也會失敗）；三、簡訊可能被手機的攔截程式擋下，檢查攔截紀錄；四、稍候一兩分鐘再點重新發送，避免連續觸發限制。
都試過仍收不到，記下租客的帳號與時間點聯繫客服查發送紀錄。
租客收不到註冊或合約的驗證簡訊時，依序排查：一、核對手機號碼是否正確；二、請租客檢查垃圾簡訊匣；三、確認沒有在短時間內重複按重發（120 秒冷卻內不會發出新簡訊、每日有則數上限）。
仍收不到就改走 Email：JGB 註冊本來就以 Email 為主路徑，把註冊頁連結提供給租客、請租客用信箱完成註冊即可；手機可之後再補綁。
合約邀請也可以改用 Email 重新發送。
收不到 Email 驗證信時，第一個檢查點是網路環境：驗證信的收取會受 Wi-Fi、手機熱點等網路速度影響，現場 Wi-Fi 訊號弱時建議切換成手機行動網路再試。
在垃圾郵件匣找到 JGB 的驗證信後，建議順手把它設定為非垃圾郵件，之後 JGB 系統發的通知郵件才不會再被擋掉。
Email 驗證信在切換網路、翻找垃圾郵件匣、確認信箱拼寫都試過仍收不到時，可以改用 Facebook、Google、Line 帳號來註冊。
收不到手機簡訊驗證碼時可能是現場電信訊號不佳，把手機拿到戶外或室內的窗邊後再點「驗證碼重新發送」大多能改善；這和收銀行簡訊 OTP 有時要移到收訊好的地方是同一種情形。
簡訊驗證碼各種方法都試過仍收不到，可以先跳過綁定手機號碼的階段完成註冊，再請租賃管理業者協助向 JGB 提供排查資訊，交由客服人員處理。
請客服排查簡訊驗證碼問題時要準備的資訊有：手機號碼與 Email、手機型號與軟體版本、使用的瀏覽器、現場網路環境（Wi-Fi 測速、月底資費是否被降速等）、電子信箱服務供應商，以及發送驗證碼的確切時間點。

### 驗證碼一直輸入失敗（重發即換碼、三字母識別碼比對、5 分鐘效期、錯三次失效、120 秒冷卻） {#jgb/A/verification-code-invalid}
- phrasings:
  - {text: "新舊碼", source: "question_summary:3964", status: approved}
  - {text: "驗證碼一直失敗", source: "question_summary:3964", status: approved}
- sources: [kb:3964]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客輸入驗證碼連續失敗，最常見的原因是重複按了「重新取得」：每次重新取得都會產生新的驗證碼、舊碼立即失效，手上那封訊息裡的碼可能已經不是最新的。
排查方式：簡訊或信件開頭有三個英文字母的識別碼，請租客核對畫面上顯示的識別碼，只輸入「識別碼一致的那一封」裡的驗證碼。
驗證碼效期 5 分鐘、輸錯三次會失效；重發有 120 秒冷卻，冷卻中按重發不會發出新訊息。
若三次失效，等冷卻結束重新取得一組再輸入即可。

### 忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則） {#jgb/A/forgot-password}
- phrasings:
  - {text: "我忘記密碼怎麼辦?", source: "helpcenter:slug02", status: approved}
  - {text: "忘記密碼", source: "question_summary:3436", status: approved}
  - {text: "無法登入", source: "question_summary:3436", status: approved}
- sources: [kb:3436, helpcenter:slug02]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
忘記密碼：在登入頁點「忘記密碼」，選擇用 Email 或手機簡訊接收驗證碼（擇一），輸入驗證碼通過後即可直接設定新密碼。
注意驗證碼輸錯三次會失效，需重新取得。
若連當初註冊用的信箱都不確定：登入頁有「忘記帳號」，以手機簡訊驗證後系統會顯示打星號的信箱提示；沒有綁定手機的話請聯繫客服協助查詢。
「忘記密碼？
」的位置在系統登入頁面的最下方，要往下滑才會看到，點選後輸入帳號 Email 或綁定的電話號碼進行驗證碼驗證。
重設密碼時新密碼有格式要求：至少 6 個字元，而且要同時包含英文字母與數字，只有英文或只有數字都無法通過。
設定好新密碼後按「送出」，畫面出現密碼變更成功的提示就代表完成，接著用新密碼重新登入即可。

### 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服） {#jgb/A/forgot-account-email}
- phrasings:
  - {text: "忘記當初註冊的信箱", source: "question_summary:3969", status: approved}
  - {text: "查詢帳號", source: "question_summary:3969", status: approved}
  - {text: "不記得當初用哪個信箱註冊", source: "koyu:slug01#4", status: approved}
- sources: [kb:3436, kb:3969, helpcenter:slug01]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
忘記密碼：在登入頁點「忘記密碼」，選擇用 Email 或手機簡訊接收驗證碼（擇一），輸入驗證碼通過後即可直接設定新密碼。
注意驗證碼輸錯三次會失效，需重新取得。
若連當初註冊用的信箱都不確定：登入頁有「忘記帳號」，以手機簡訊驗證後系統會顯示打星號的信箱提示；沒有綁定手機的話請聯繫客服協助查詢。
使用者忘記當初用哪個信箱註冊時：登入頁有「忘記帳號」功能，以手機簡訊驗證身分後，系統會顯示打星號的信箱提示（例如 s***＠hotmail.com），通常足以想起是哪個信箱。
如果帳號沒有綁定手機、無法用這個功能，請聯繫 JGB 客服協助查詢，並準備合約或物件資訊供身分核對。
「忘記帳號？
」的位置在系統登入頁面的最下方，要往下滑才會看到，點選後輸入原帳號綁定的電話號碼進行簡訊驗證，驗證完成就會收到帳號提示。
忘記帳號功能靠的是原帳號綁定的電話號碼，因此驗證時輸入的手機號碼必須是當初在帳號裡綁定的那一個。
走完忘記帳號的簡訊驗證流程後仍然找不回帳戶，可以聯繫自己的租賃管理業者，由業者協助向 JGB 申請重新找回帳號。

### 要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書） {#jgb/A/change-email-or-phone}
- phrasings:
  - {text: "信箱手機要換", source: "question_summary:3980", status: approved}
  - {text: "會員帳號資料要修改", source: "question_summary:3980", status: approved}
- sources: [kb:3437, kb:3980]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號的 Email 無法自行變更：帳號設定頁的 Email 欄位是唯讀的，如需更換請聯繫 JGB 客服，走資料異動申請書流程由後台處理。
手機號碼分兩種情況：帳號還沒綁定手機時，可到帳號設定「前往綁定」自助綁定（簡訊驗證）；已綁定要更換號碼則同樣屬後台作業，請透過資料異動申請書申請。
申請書需載明帳號識別（信箱或手機）、修改前後值與相關合約 ID，經公司用印後寄至 客服信箱（官網）。

### 註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步） {#jgb/A/change-account-name}
- phrasings:
  - {text: "要怎麼改資料", source: "question_summary:4561", status: approved}
  - {text: "註冊名字與證件不同", source: "question_summary:3971", status: approved}
  - {text: "註冊名字跟證件不符", source: "question_summary:4561", status: approved}
- sources: [kb:3971, kb:4561]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客註冊時填的名字與證件不同，不需要重新註冊。
分兩種情況：合約還沒完成簽署——請租客到「帳號設定」的基本資訊自行改名，簽署時合約上的藍字（由帳號資料帶入的欄位）就會是新名字；合約已完成雙方簽署——合約上的資料是定案快照，不會跟著帳號連動，而且簽署完成後帳號姓名會被鎖定無法自改，這種情況要透過資料異動申請書請客服後台同步修改帳號與合約資料。

### 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱） {#jgb/A/data-change-request-form}
- phrasings:
  - {text: "資料異動申請書", source: "owner:20260916", status: approved}
  - {text: "申請書怎麼填", source: "owner:20260916", status: approved}
- sources: [kb:3437, kb:3971, kb:3972]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號的 Email 無法自行變更：帳號設定頁的 Email 欄位是唯讀的，如需更換請聯繫 JGB 客服，走資料異動申請書流程由後台處理。
手機號碼分兩種情況：帳號還沒綁定手機時，可到帳號設定「前往綁定」自助綁定（簡訊驗證）；已綁定要更換號碼則同樣屬後台作業，請透過資料異動申請書申請。
申請書需載明帳號識別（信箱或手機）、修改前後值與相關合約 ID，經公司用印後寄至 客服信箱（官網）。
租客註冊時填的名字與證件不同，不需要重新註冊。
分兩種情況：合約還沒完成簽署——請租客到「帳號設定」的基本資訊自行改名，簽署時合約上的藍字（由帳號資料帶入的欄位）就會是新名字；合約已完成雙方簽署——合約上的資料是定案快照，不會跟著帳號連動，而且簽署完成後帳號姓名會被鎖定無法自改，這種情況要透過資料異動申請書請客服後台同步修改帳號與合約資料。
同一個人不小心註冊了兩個帳號（例如 hotmail 和 gmail 各一個，或信箱大小寫不同各成一帳），系統沒有自助合併功能，需由客服後台處理。
請填寫資料異動申請書，載明要保留的帳號、要處理的帳號、以及相關合約 ID，經公司用印後寄至 客服信箱（官網）。
日常提醒租客：登入時用當初註冊的確切寫法輸入信箱，可避免誤登或誤建第二個帳號。

### 不小心註冊了兩個帳號能不能合併（無自助合併、走客服後台，載明保留與處理的帳號） {#jgb/A/duplicate-accounts-merge}
- phrasings:
  - {text: "兩個帳號", source: "question_summary:3972", status: approved}
  - {text: "重複帳號", source: "question_summary:3972", status: approved}
  - {text: "帳號重複註冊了", source: "owner:20260916", status: approved}
- sources: [kb:3972]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
同一個人不小心註冊了兩個帳號（例如 hotmail 和 gmail 各一個，或信箱大小寫不同各成一帳），系統沒有自助合併功能，需由客服後台處理。
請填寫資料異動申請書，載明要保留的帳號、要處理的帳號、以及相關合約 ID，經公司用印後寄至 客服信箱（官網）。
日常提醒租客：登入時用當初註冊的確切寫法輸入信箱，可避免誤登或誤建第二個帳號。

### 註冊時顯示此帳號／手機已註冊怎麼辦（本人改登入或重設密碼、被他人占用走解綁申請） {#jgb/A/already-registered-error}
- phrasings:
  - {text: "註冊顯示已註冊", source: "question_summary:3966", status: approved}
- sources: [kb:3966]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
註冊時出現「此帳號已註冊」或「此手機已註冊」，代表該信箱或手機已經有 JGB 帳號了——不要再嘗試註冊或另開新帳號。
分兩種情況處理：如果是本人之前註冊過，改走登入，忘記密碼可在登入頁自助重設；如果那個號碼或信箱是被別人（例如前租客、同事的舊帳號）占用，需要走解綁申請由客服後台處理，解綁後才能重新綁定。

### 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態） {#jgb/A/tenant-login-cannot-see-data}
- phrasings:
  - {text: "畫面空空的", source: "question_summary:3978", status: approved}
  - {text: "登入信箱不符", source: "question_summary:3869", status: approved}
  - {text: "看不到合約帳單電表", source: "question_summary:3968", status: approved}
  - {text: "租客登入後什麼都看不到", source: "question_summary:3978", status: approved}
  - {text: "租客看不到合約", source: "question_summary:3869", status: approved}
- sources: [kb:3968, kb:3869, kb:3978]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客登入成功卻看不到自己的合約、帳單或電表，照順序排查：一、確認左上角身分選單已切到「租客」身分——租客資料只在租客身分下顯示；二、確認登入的信箱是「當初註冊時的確切寫法」——寫法不同可能登進另一個同名帳號，那個帳號名下沒有合約，自然什麼都看不到；三、都確認過仍看不到，提供合約編號或物件名稱，系統可以查這份合約的租客帳號狀態（是否已註冊、邀請信箱與登入帳號是否一致）來判斷是不是登錯帳號。
租客說收到了邀請、也註冊登入了，卻看不到合約——常見原因是「發送信箱」與「登入帳號」不一致：邀請寄到 A 信箱，但租客用 B 信箱（或用其他方式如 SSO）註冊登入，系統無法把合約對到他的帳號。
排查方式：請租客確認實際登入的帳號信箱，與合約上填的發送信箱是否相同；不一致時，把合約退回修改為租客實際登入的信箱後重新發送邀請即可。
