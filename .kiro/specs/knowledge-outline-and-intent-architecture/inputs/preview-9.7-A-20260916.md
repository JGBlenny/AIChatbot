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

### 怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口） {#jgb/A/login-methods}
- sources: [helpcenter:Landlordonboarding01, helpcenter:onboarding1]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general

### 用 LINE 快速登入卻被帶去註冊頁、登不進去（只認 LINE 註冊帳號、無事後綁定、改用帳密登入） {#jgb/A/line-login-redirects-to-register}
- sources: [kb:3967]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客用 LINE 快速登入卻被帶到註冊畫面，原因是：LINE 快速登入只認「當初用 LINE 註冊」的帳號；用帳號密碼註冊的帳號沒有 LINE 綁定，目前也沒有事後補綁的功能，所以系統找不到對應帳號、只能導去註冊。
解法很單純：請租客改用帳號密碼登入即可，不需要重新註冊。
另外在 LINE 內建瀏覽器裡開啟登入頁偶爾會有狀況，可改用手機的一般瀏覽器再試。

### 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件） {#jgb/A/account-profile-settings}
- sources: [helpcenter:onboarding2, helpcenter:slug95, helpcenter:Landlordonboarding01]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general

### 租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業） {#jgb/A/registered-vs-unregistered-tenant}
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

### Email 大小寫算不同帳號嗎（Email 為帳號識別、大小寫視為不同帳號） {#jgb/A/email-case-sensitivity}
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

### 驗證碼一直輸入失敗（重發即換碼、三字母識別碼比對、5 分鐘效期、錯三次失效、120 秒冷卻） {#jgb/A/verification-code-invalid}
- sources: [kb:3964]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租客輸入驗證碼連續失敗，最常見的原因是重複按了「重新取得」：每次重新取得都會產生新的驗證碼、舊碼立即失效，手上那封訊息裡的碼可能已經不是最新的。
排查方式：簡訊或信件開頭有三個英文字母的識別碼，請租客核對畫面上顯示的識別碼，只輸入「識別碼一致的那一封」裡的驗證碼。
驗證碼效期 5 分鐘、輸錯三次會失效；重發有 120 秒冷卻，冷卻中按重發不會發出新訊息。
若三次失效，等冷卻結束重新取得一組再輸入即可。

### 忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則） {#jgb/A/forgot-password}
- sources: [kb:3436, helpcenter:slug02]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
忘記密碼：在登入頁點「忘記密碼」，選擇用 Email 或手機簡訊接收驗證碼（擇一），輸入驗證碼通過後即可直接設定新密碼。
注意驗證碼輸錯三次會失效，需重新取得。
若連當初註冊用的信箱都不確定：登入頁有「忘記帳號」，以手機簡訊驗證後系統會顯示打星號的信箱提示；沒有綁定手機的話請聯繫客服協助查詢。

### 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服） {#jgb/A/forgot-account-email}
- sources: [kb:3436, kb:3969, helpcenter:slug01]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
忘記密碼：在登入頁點「忘記密碼」，選擇用 Email 或手機簡訊接收驗證碼（擇一），輸入驗證碼通過後即可直接設定新密碼。
注意驗證碼輸錯三次會失效，需重新取得。
若連當初註冊用的信箱都不確定：登入頁有「忘記帳號」，以手機簡訊驗證後系統會顯示打星號的信箱提示；沒有綁定手機的話請聯繫客服協助查詢。
使用者忘記當初用哪個信箱註冊時：登入頁有「忘記帳號」功能，以手機簡訊驗證身分後，系統會顯示打星號的信箱提示（例如 s***＠hotmail.com），通常足以想起是哪個信箱。
如果帳號沒有綁定手機、無法用這個功能，請聯繫 JGB 客服協助查詢，並準備合約或物件資訊供身分核對。

### 要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書） {#jgb/A/change-email-or-phone}
- sources: [kb:3437, kb:3980]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號的 Email 無法自行變更：帳號設定頁的 Email 欄位是唯讀的，如需更換請聯繫 JGB 客服，走資料異動申請書流程由後台處理。
手機號碼分兩種情況：帳號還沒綁定手機時，可到帳號設定「前往綁定」自助綁定（簡訊驗證）；已綁定要更換號碼則同樣屬後台作業，請透過資料異動申請書申請。
申請書需載明帳號識別（信箱或手機）、修改前後值與相關合約 ID，經公司用印後寄至 客服信箱（官網）。

### 註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步） {#jgb/A/change-account-name}
- sources: [kb:3971, kb:4561]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客註冊時填的名字與證件不同，不需要重新註冊。
分兩種情況：合約還沒完成簽署——請租客到「帳號設定」的基本資訊自行改名，簽署時合約上的藍字（由帳號資料帶入的欄位）就會是新名字；合約已完成雙方簽署——合約上的資料是定案快照，不會跟著帳號連動，而且簽署完成後帳號姓名會被鎖定無法自改，這種情況要透過資料異動申請書請客服後台同步修改帳號與合約資料。

### 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱） {#jgb/A/data-change-request-form}
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
- sources: [kb:3972]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
同一個人不小心註冊了兩個帳號（例如 hotmail 和 gmail 各一個，或信箱大小寫不同各成一帳），系統沒有自助合併功能，需由客服後台處理。
請填寫資料異動申請書，載明要保留的帳號、要處理的帳號、以及相關合約 ID，經公司用印後寄至 客服信箱（官網）。
日常提醒租客：登入時用當初註冊的確切寫法輸入信箱，可避免誤登或誤建第二個帳號。

### 註冊時顯示此帳號／手機已註冊怎麼辦（本人改登入或重設密碼、被他人占用走解綁申請） {#jgb/A/already-registered-error}
- sources: [kb:3966]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
註冊時出現「此帳號已註冊」或「此手機已註冊」，代表該信箱或手機已經有 JGB 帳號了——不要再嘗試註冊或另開新帳號。
分兩種情況處理：如果是本人之前註冊過，改走登入，忘記密碼可在登入頁自助重設；如果那個號碼或信箱是被別人（例如前租客、同事的舊帳號）占用，需要走解綁申請由客服後台處理，解綁後才能重新綁定。

### 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態） {#jgb/A/tenant-login-cannot-see-data}
- sources: [kb:3968, kb:3869, kb:3978]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客登入成功卻看不到自己的合約、帳單或電表，照順序排查：一、確認左上角身分選單已切到「租客」身分——租客資料只在租客身分下顯示；二、確認登入的信箱是「當初註冊時的確切寫法」——寫法不同可能登進另一個同名帳號，那個帳號名下沒有合約，自然什麼都看不到；三、都確認過仍看不到，提供合約編號或物件名稱，系統可以查這份合約的租客帳號狀態（是否已註冊、邀請信箱與登入帳號是否一致）來判斷是不是登錯帳號。
租客說收到了邀請、也註冊登入了，卻看不到合約——常見原因是「發送信箱」與「登入帳號」不一致：邀請寄到 A 信箱，但租客用 B 信箱（或用其他方式如 SSO）註冊登入，系統無法把合約對到他的帳號。
排查方式：請租客確認實際登入的帳號信箱，與合約上填的發送信箱是否相同；不一致時，把合約退回修改為租客實際登入的信箱後重新發送邀請即可。
