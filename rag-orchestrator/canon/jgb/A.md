---
coarse: A
title: 帳號與身分
scope: 註冊、登入、找回帳號、身分（房東／租客／法人／社宅）與個人資料、聯絡方式變更；⛔ 團隊成員權限歸 B
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 註冊帳號（Email／SSO、驗證碼、手機綁定） {#A-registration}
### 如何註冊 JGB 帳號？（Email、驗證碼、帳號設定三步驟） {#jgb/A/register-email-steps}
- phrasings:
  - {text: "怎麼註冊帳號", source: "draft:outline-20260920", status: proposed}
  - {text: "註冊流程是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "第一次用要怎麼開帳號", source: "draft:outline-20260920", status: proposed}
  - {text: "註冊要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼申請 JGB 帳號", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/Create.vue, code:src/pages/users/auth/parts/CreateWelcome.vue, code:src/pages/users/auth/parts/EmailVerify.vue, code:src/pages/users/auth/parts/AccountSetting.vue, help:onboarding1_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
註冊只需要一組 Email，同一個帳號可以同時擁有房東和租客身分。
第一步輸入 Email 並勾選「我不是機器人」驗證後按繼續，系統會寄送驗證碼到該信箱。
第二步輸入收到的 Email 驗證碼完成信箱驗證。
第三步填寫姓氏、名稱、稱謂並設定密碼，按下「完成註冊」即建立帳號。
註冊時需先閱讀並同意服務條款和隱私權聲明才能繼續下一步。
### 租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「立即註冊」接續完成） {#jgb/A/register-tenant-contract-invitation}
- phrasings:
  - {text: "租客電子合約邀請註冊", source: "draft:outline-20260920", status: proposed}
  - {text: "房東邀請租客簽約怎麼註冊", source: "draft:outline-20260920", status: proposed}
  - {text: "收到合約邀請信怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "租客可以不註冊嗎", source: "draft:outline-20260920", status: proposed}
- sources: [help:onboarding1_zh-Hant.html, code:app/Http/Controllers/AuthController.php, code:src/pages/contracts/edit/tenantInfo/Index.jsx, code:app/Notification.php, code:resources/views/emails/zh-TW/contracts/invite.blade.php, code:resources/views/estate/show.blade.php, code:src/pages/users/auth/parts/LoginForm.vue, code:src/components/SurelyVue/Contract/CategoryCell.jsx, code:app/Http/Controllers/EstateController.php, code:app/Http/Middleware/LoginCheck.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
房東建立合約時，若選「租客註冊」，會在「合約邀請聯繫方式」選 Email 或手機號碼並填入租客的聯絡方式來發送邀請；邀請送出後，合約會進入「待租客簽回」。
房東用 Email 邀請時，租客會收到簽約邀請郵件；點選信中的「查看合約」按鈕後，會進入該物件的廣告頁供租客參考。
房東用手機號碼邀請時，租客收到的是帶有同一個連結的簡訊。
租客在廣告頁點選「查看合約」後，如果還沒有登入，會先進入 JGB 登入畫面。
登入畫面上有「立即註冊」可以點選。
註冊完成後，系統會把這份合約邀請綁定到新帳號，租客就能接續處理這份合約。
房東建立合約時若選「租客免註冊」，租客不需要註冊 JGB 會員，改由房東／管理者協助填寫租客資訊。
### 可以用 Facebook、Google、LINE 註冊嗎？（SSO 仍需完成 Email 綁定） {#jgb/A/register-sso}
- phrasings:
  - {text: "可以用臉書登入註冊嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "可以用 Google 帳號註冊嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "LINE 可以註冊嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "第三方帳號註冊", source: "draft:outline-20260920", status: proposed}
  - {text: "SSO 註冊", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/SSOBar.vue, code:src/pages/users/auth/parts/CreateWelcome.vue, help:onboarding1_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
註冊頁除了 Email 之外，也提供 Facebook、Google、LINE 三種第三方帳號快速註冊。
透過 LINE 內建瀏覽器開啟 Google 註冊時，系統會另外開啟外部瀏覽器完成驗證。
用第三方帳號註冊後，仍會進入 Email 驗證流程，需要自行輸入要綁定的 Email 並完成驗證。
### 註冊卡在機器人驗證過期怎麼辦？（重新勾選「我不是機器人」；寄驗證信時沒通過會退回第一步） {#jgb/A/register-captcha-expired}
- phrasings:
  - {text: "機器人驗證過期", source: "draft:outline-20260920", status: proposed}
  - {text: "我不是機器人卡住", source: "draft:outline-20260920", status: proposed}
  - {text: "註冊一直失敗", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/EmailVerify.vue, code:src/pages/users/auth/parts/CreateWelcome.vue, code:app/Http/Controllers/AuthController.php, code:app/Services/AuthService.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在第一步 Email 輸入畫面，「我不是機器人」的勾選失效時，「繼續」按鈕會收起來，需要重新勾選才會再出現。
如果是在寄驗證信時，系統判定機器人驗證沒有通過，畫面會退回第一步的 Email 輸入畫面，並提示「機器人驗證已經過期，請重新輸入 Email 並勾選「我不是機器人」」
退回第一步時，先前輸入的 Email 與機器人驗證結果都會被清空，需要重新輸入 Email 並重新勾選「我不是機器人」才能繼續。
機器人驗證通過後，系統只在 30 分鐘內承認同一個 Email 的驗證紀錄；超過之後再寄驗證信，就會要求重新驗證。
### 沒收到 Email 驗證碼怎麼辦？（可重發，發送次數過多會出現等待秒數） {#jgb/A/register-email-verify-resend}
- phrasings:
  - {text: "沒收到驗證信", source: "draft:outline-20260920", status: proposed}
  - {text: "驗證碼重發", source: "draft:outline-20260920", status: proposed}
  - {text: "驗證信在等待", source: "draft:outline-20260920", status: proposed}
  - {text: "Email 驗證碼過期", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/EmailVerify.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
驗證碼輸入畫面提供「重發驗證信」的連結，可以重新觸發寄送。
短時間內重複要求重發時，系統會回傳等待秒數，重發連結在倒數期間會停用並顯示剩餘秒數。
超過發送次數上限時，畫面上會出現對應的錯誤提示。
如果 Email 打錯，可以點「點此重新輸入」返回第一步修改。
### 註冊密碼格式要求是什麼？（至少 6 碼、須同時包含英文與數字） {#jgb/A/register-password-rule}
- phrasings:
  - {text: "密碼規則", source: "draft:outline-20260920", status: proposed}
  - {text: "密碼要幾碼", source: "draft:outline-20260920", status: proposed}
  - {text: "密碼格式", source: "draft:outline-20260920", status: proposed}
  - {text: "設定密碼限制", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/AccountSetting.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
密碼長度至少需 6 個字元（含）以上。
密碼須同時包含至少一個英文字母和一個數字，只有英文或只有數字都無法通過。
確認密碼欄位必須與密碼欄位輸入一致才能完成註冊。
### 註冊時 Email 已被註冊過怎麼辦？（已完成註冊的 Email 會直接被擋下；只有還沒完成 Email 註冊的舊帳號才會進行帳號合併） {#jgb/A/register-email-already-registered}
- phrasings:
  - {text: "Email 已經註冊過", source: "draft:outline-20260920", status: proposed}
  - {text: "帳號合併", source: "draft:outline-20260920", status: proposed}
  - {text: "重複註冊", source: "draft:outline-20260920", status: proposed}
  - {text: "曾經用 SSO 註冊過還能再用 Email 註冊嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/AccountSetting.vue, code:app/Http/Controllers/AuthController.php]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果這個 Email 已經有完成註冊的帳號（Email 已驗證、也設過密碼），在第一步輸入 Email 時就會顯示「此帳號已註冊」並擋下，不會進入後續步驟；現在用第三方帳號註冊時，也會一併建立這樣的帳號。
只有這個 Email 已經有帳號、但還沒完成 Email 註冊（例如較早期用第三方帳號註冊的帳號）時，驗證信步驟通過後，畫面標題才會顯示「帳號已註冊」並提示 JGB 將進行帳號合併，使用者按「繼續」即可完成流程進入下一步（綁定手機）。
此情境按「繼續」時會直接完成帳號設定，不會再檢查姓名、密碼等欄位是否填寫完整。
### 註冊要綁定手機號碼嗎？（可選填、簡訊驗證、可「下次再驗證」略過） {#jgb/A/register-phone-bind}
- phrasings:
  - {text: "註冊要綁手機嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "手機驗證怎麼做", source: "draft:outline-20260920", status: proposed}
  - {text: "可以跳過手機驗證嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "手機驗證碼收不到", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/PhoneVerify.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
帳號設定完成後會進入綁定手機的步驟，可選擇國碼並輸入手機號碼，號碼長度上限依所選國家而有上限。
送出後系統會發送簡訊驗證碼，輸入正確驗證碼即完成綁定。
在註冊流程中，這一步驟可以按「下次再驗證」略過，不會擋住完成註冊。
簡訊驗證碼一樣提供「重發簡訊」功能，重複發送過於頻繁時會出現等待秒數限制。
綁定手機後，未來登入、忘記密碼、忘記帳號都可以使用該手機號碼進行驗證或作為替代登入方式。
### 註冊時發現手機已綁定過怎麼辦？（直接顯示已綁定、按繼續完成流程） {#jgb/A/register-phone-already-bound}
- phrasings:
  - {text: "手機已經綁定過", source: "draft:outline-20260920", status: proposed}
  - {text: "重複綁定手機", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/PhoneVerify.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
系統會在進入手機綁定步驟前先檢查目前帳號是否已有綁定手機。
若已綁定，畫面會直接顯示「手機已綁定」，說明未來可用手機號碼登入或作為忘記帳號時的替代找回方式，按「繼續」即可完成註冊流程。
若是在註冊流程中出現此畫面，按「繼續」會前進到選擇身分步驟；若是註冊完成後在其他情境觸發手機驗證，則會依原本要前往的頁面返回，不會進入選擇身分畫面。
### 註冊完之後要選身分嗎？（一般會在房東/管理者、租客中二選一，可同時擁有兩種身分；從租客端網站導轉來的會直接導回原頁） {#jgb/A/register-role-select}
- phrasings:
  - {text: "註冊完要選身分嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "房東身分和租客身分", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼切換房東和租客", source: "draft:outline-20260920", status: proposed}
  - {text: "我是房東還是租客", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/RoleSelect.vue, help:onboarding1_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
一般的註冊或登入流程會出現身分選擇畫面，讓使用者選擇「我是房東/管理者」或「我是租客」；已註冊過的第三方帳號登入時，則會直接進入首頁。
同一組帳號可同時擁有房東與租客兩種身分，選擇的身分只決定這次要進入哪一種介面。
若是從租客端網站導轉來註冊，綁定手機這一步完成或略過後，系統會直接把使用者導回原本要前往的頁面，不會再出現身分選擇畫面。
### 驗證碼輸入畫面長什麼樣子？（識別碼加 4 碼數字；輸入錯誤太多次驗證碼會失效，需重新發送） {#jgb/A/register-verify-code-shape}
- phrasings:
  - {text: "驗證碼長什麼樣子", source: "draft:outline-20260920", status: proposed}
  - {text: "驗證碼輸入錯誤被鎖", source: "draft:outline-20260920", status: proposed}
  - {text: "驗證碼幾碼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/VerifyPanel.vue, code:src/pages/users/auth/parts/EmailVerify.vue, code:src/pages/users/auth/parts/PhoneVerify.vue, code:src/pages/users/auth/parts/forget/Account.vue, code:src/pages/users/auth/parts/forget/Password.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
驗證碼輸入畫面由兩部分組成：左邊顯示一組簡短的識別碼，右邊是使用者要輸入的 4 碼數字驗證碼。
如果驗證碼輸入錯誤太多次，畫面會提示驗證次數過多、驗證碼已失效，需要稍候重新發送驗證碼；輸入框本身不會被鎖住。
### 從信箱 App 點註冊連結、去收驗證碼再回來，會從頭開始註冊嗎？（同一瀏覽器會記住 Email 回到驗證碼步驟；機器人驗證失效時退回第一步） {#jgb/A/register-email-link-resume}
- phrasings:
  - {text: "註冊到一半去收信再回來會重來嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "收信後點回註冊頁", source: "draft:outline-20260920", status: proposed}
  - {text: "從信箱 App 開註冊連結會重來嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/Create.vue, code:src/pages/users/auth/parts/CreateWelcome.vue, code:src/pages/users/auth/parts/EmailVerify.vue, code:app/Services/AuthService.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
輸入 Email 進入驗證碼步驟後，系統會把這個 Email 和目前停在驗證碼步驟這件事記在瀏覽器裡。
之後在同一個瀏覽器重新開啟註冊頁時，會直接帶回這個 Email 並跳到驗證碼步驟，不會從第一步重來。
回到驗證碼步驟時，系統會再嘗試寄一次驗證信。
但如果寄驗證信時，這個瀏覽器已經沒有這個 Email 還有效的機器人驗證紀錄（例如已超過 30 分鐘），會清空 Email 並退回第一步，需要重新勾選「我不是機器人」。
## 登入 {#A-login}
### JGB 有哪些登入方式？（Email、手機號碼、Facebook／Google／LINE） {#jgb/A/login-methods}
- phrasings:
  - {text: "怎麼登入", source: "draft:outline-20260920", status: proposed}
  - {text: "登入方式有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "可以用手機登入嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "SSO 登入", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/LoginForm.vue, code:src/pages/users/auth/parts/SSOBar.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
登入表單可在 Email 與手機號碼兩種帳號輸入方式間切換。
登入頁另外提供 Facebook、Google、LINE 第三方帳號登入。
### 登入前為什麼要先選擇身分？（決定進入房東/管理者或租客的登入表單） {#jgb/A/login-role-select-before}
- phrasings:
  - {text: "登入頁面在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼要選身分才能登入", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/RoleSelect.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
登入前需先選擇身分：房東/管理者或租客。
### 用手機號碼登入時，國碼與號碼格式有什麼規則？（號碼長度上限與格式依所選國家而定） {#jgb/A/login-phone-country-code}
- phrasings:
  - {text: "手機登入國碼", source: "draft:outline-20260920", status: proposed}
  - {text: "手機號碼格式限制", source: "draft:outline-20260920", status: proposed}
  - {text: "手機登入長度限制", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/LoginForm.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
選擇手機號碼登入時需先選擇國碼，號碼長度上限依所選國家而定，且手機格式會依所選國家的規則做檢查。
### 「記住我」是做什麼？（只延長登入效期，跟記住登入方式無關） {#jgb/A/login-remember-me}
- phrasings:
  - {text: "記住我是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/LoginForm.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「記住我」勾選只影響下次登入送出時是否要延長登入效期，跟登入方式無關；不論是否勾選「記住我」，上次選擇用 Email 還是手機號碼登入，下次開啟登入頁都會沿用同一種方式。
### 登入時身分選錯了怎麼辦？（會依選擇的身分決定進入哪個角色的登入表單） {#jgb/A/login-role-redirect}
- phrasings:
  - {text: "登入身分選錯", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼切換登入身分", source: "draft:outline-20260920", status: proposed}
  - {text: "房東登入還是租客登入", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/Login.vue, code:src/pages/users/auth/parts/LoginForm.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
登入頁網址可以帶身分參數，直接跳到對應身分（房東/管理者或租客）的登入表單。
若沒有帶身分參數，或參數不是這兩者之一，會停留在身分選擇畫面，需先點選「房東/管理者」或「租客」卡片才會出現帳號密碼欄位。
登入表單上沒有返回身分選擇的按鈕；選錯身分時，重新開啟不帶身分參數的登入頁，就會回到身分選擇畫面重新選擇。
### 登入帳號或密碼錯誤時會顯示什麼？ {#jgb/A/login-error}
- phrasings:
  - {text: "登入失敗", source: "draft:outline-20260920", status: proposed}
  - {text: "帳號密碼錯誤", source: "draft:outline-20260920", status: proposed}
  - {text: "登不進去", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/LoginForm.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
登入失敗時，畫面會在密碼欄位下方顯示錯誤訊息。
任何一個登入欄位（國碼、手機、Email、密碼）內容變更後，先前的錯誤訊息會被清除，需重新送出才會再次驗證。
切換登入方式（Email／手機號碼）時，原本輸入的帳號欄位與密碼會一併被清空，需要重新輸入。
### 登入頁的「忘記密碼？」連結在哪裡？（在登入表單下方，點擊前往忘記密碼流程） {#jgb/A/login-forget-password-link}
- phrasings:
  - {text: "忘記密碼在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "忘記密碼連結", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/LoginForm.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
登入表單下方提供「忘記密碼」連結，點擊後會前往忘記密碼流程頁面。
### 登入頁的「忘記帳號？」連結在哪裡？（在登入表單下方，點擊前往忘記帳號流程） {#jgb/A/login-forget-account-link}
- phrasings:
  - {text: "忘記帳號在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "忘記帳號連結", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/LoginForm.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
登入表單下方提供「忘記帳號」連結，點擊後會前往忘記帳號流程頁面。
### 登入頁有連到註冊頁的連結嗎？（登入表單上方的「還沒有帳號嗎？立即註冊」） {#jgb/A/login-no-account-register-link}
- phrasings:
  - {text: "登入頁怎麼去註冊", source: "draft:outline-20260920", status: proposed}
  - {text: "還沒帳號怎麼註冊", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/LoginForm.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
尚未註冊的使用者可以從登入表單上方「還沒有帳號嗎」旁的「立即註冊」連結前往註冊頁。
### 同一帳號同時有房東與租客身分時怎麼切換？（登入時重新選擇身分，或在帳號資訊設定預設身分） {#jgb/A/login-identity-switch}
- phrasings:
  - {text: "房東租客身分切換", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼換身分登入", source: "draft:outline-20260920", status: proposed}
  - {text: "登入預設身分", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/Login.vue, code:app/Http/Controllers/UserController.php#account]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
同一組帳號如果同時有房東/管理者與租客兩種身分，登入時可以在身分選擇畫面重新選擇這次要用哪一種身分進入。
如果同時管理多個房東身分／團隊，可以到帳號資訊頁的「偏好設定」設定登入預設要進入的房東身分，之後登入會直接帶入這個預設身分。
## 忘記帳號、忘記密碼 {#A-account-recovery}
### 忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示） {#jgb/A/forget-account-flow}
- phrasings:
  - {text: "忘記帳號怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "忘記 email 帳號", source: "draft:outline-20260920", status: proposed}
  - {text: "找回帳號", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/forget/Account.vue, code:app/Http/Controllers/AuthController.php, code:app/User.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
忘記帳號功能只能用「當初綁定在帳號上的手機號碼」進行簡訊驗證碼驗證來找回。
忘記帳號畫面的說明文字寫明：如果未綁定手機號碼，請聯繫 JGB 客服。
輸入的手機號碼若沒有對應的帳號，手機欄位下方會提示「手機號碼格式錯誤或無此號碼對應的帳號」
手機驗證成功後，畫面會顯示「身份驗證成功」「以下為您的帳號提示：」，下面是只露出 Email 開頭第一個字、其餘以 * 遮蔽的帳號提示，@ 後面的網域照常顯示，而不是完整帳號。
驗證成功畫面的最下方寫著「如有其他問題，請聯繫 JGB 客服」
### 沒綁手機號碼還能用「忘記帳號」找回嗎？（不行，只能靠手機簡訊驗證） {#jgb/A/forget-account-no-phone}
- phrasings:
  - {text: "沒綁手機忘記帳號", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有手機號碼怎麼找回帳號", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/forget/Account.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
忘記帳號功能的驗證方式只有手機簡訊驗證碼一種，沒有 Email 驗證選項。
帳號如果沒有綁定手機號碼，就無法透過此頁面自助找回，畫面上直接提示改為聯繫 JGB 客服。
手機號碼欄位在輸入過程中會即時顯示驗證結果（成功或錯誤提示），並依所選國碼提示號碼長度上限。
### 忘記密碼怎麼辦？（Email 或手機任一驗證後即可重設新密碼） {#jgb/A/forget-password-flow}
- phrasings:
  - {text: "忘記密碼怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "重設密碼", source: "draft:outline-20260920", status: proposed}
  - {text: "密碼忘記了", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/forget/Password.vue, help:slug02_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
重設密碼前必須先完成帳號驗證，可以選擇用 Email 或手機號碼兩種方式其中之一收驗證碼。
驗證碼確認正確後，畫面會顯示「帳號驗證成功」並切換到重設密碼表單。
新密碼需至少 6 個字元、同時包含英文與數字，且需與確認密碼欄位一致。
送出並顯示密碼設定成功後，系統會依處理結果自動導向指定頁面或一般登入頁，需使用新密碼重新登入。
如果密碼設定失敗，畫面會跳出提示視窗顯示「密碼設定失敗」與失敗原因；若是密碼格式不符，密碼欄位下方也會顯示錯誤提示。
### 「請設定密碼」畫面是什麼情境？（受邀請帳號的初次設定密碼流程） {#jgb/A/forget-password-setpwd-invite}
- phrasings:
  - {text: "請設定密碼是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "被邀請要設密碼", source: "draft:outline-20260920", status: proposed}
  - {text: "被邀請設定密碼的頁面", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/auth/parts/forget/Password.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
當使用者是透過特定邀請連結進入忘記密碼頁面時，畫面會直接顯示「請設定密碼」，而不是一般的忘記密碼流程，並跳過帳號驗證直接進入設定密碼表單。
這個情境用在大房東的邀請流程：受邀的帳號透過邀請連結進入後，直接設定自己的密碼，設定成功後會依處理結果導向對應頁面。
此畫面沿用一般忘記密碼頁面同樣的新密碼格式規則，設定成功後會依處理結果導向指定頁面，沒有指定頁面時才導回一般登入頁。
## 會員中心首頁 {#A-member-home}
### 會員中心首頁有哪些統計區塊？（即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單） {#jgb/A/dashboard-overview-blocks}
- phrasings:
  - {text: "首頁看得到什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "會員中心首頁", source: "draft:outline-20260920", status: proposed}
  - {text: "會員中心首頁有什麼統計資料", source: "draft:outline-20260920", status: proposed}
  - {text: "登入後的首頁", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/dashboard/Landlord.vue, code:src/pages/users/dashboard/parts/Block_Vacancy.vue, code:src/pages/users/dashboard/parts/Block_ExpiringContract.vue, code:src/pages/users/dashboard/parts/Block_AccountsReceivable.vue, code:src/pages/users/dashboard/parts/Block_Repair.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般房東/管理者登入後的首頁上方會並排四個統計區塊：即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單。
### 首頁的圖表看得到什麼？（招租／買賣廣告刊登率圓環圖、收支情況圖） {#jgb/A/dashboard-overview-charts}
- phrasings:
  - {text: "首頁圖表", source: "draft:outline-20260920", status: proposed}
  - {text: "刊登率圓環圖", source: "draft:outline-20260920", status: proposed}
  - {text: "收支情況圖表", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/dashboard/parts/RatioDoughnutChart.vue, code:src/pages/users/dashboard/parts/BalanceChart.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
首頁提供「招租廣告刊登率／買賣廣告刊登率」圓環圖，顯示刊登中、未刊登、總件數。
首頁另外提供「收支情況」圖，顯示收入、支出、當日結餘、累計結餘。
### 首頁下方還有哪些列表？（帳單、合約、修繕整合列表，具通知權限者另有 Email 通知紀錄） {#jgb/A/dashboard-overview-lists}
- phrasings:
  - {text: "首頁下方列表", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單合約修繕整合列表", source: "draft:outline-20260920", status: proposed}
  - {text: "Email 通知紀錄區塊", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/dashboard/Landlord.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
首頁下方顯示帳單、合約、修繕的整合列表；具備通知檢視權限的使用者，還會另外看到 Email 通知紀錄區塊。
### 大房東的首頁畫面和一般房東不一樣嗎？（只顯示社區最新收支詳情與收支圖表，沒有捷徑與四個統計方塊） {#jgb/A/dashboard-big-landlord-view}
- phrasings:
  - {text: "大房東首頁", source: "draft:outline-20260920", status: proposed}
  - {text: "大房東看到的畫面", source: "draft:outline-20260920", status: proposed}
  - {text: "大房東首頁跟一般房東有什麼不同", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/dashboard/Landlord.vue, help:Landlordonboarding00_zh-Hant.html, code:src/pages/users/dashboard/parts/EstateDetails.vue, code:src/pages/users/dashboard/parts/Block_Vacancy.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
若目前登入身分是大房東，首頁不會顯示即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單四個方塊，也不會有捷徑區塊。
大房東首頁改為顯示「社區最新收支詳情」，以及可自訂區間（7天／30天／90天／6個月）的收支圖表。
### 怎麼在會員中心首頁切換團隊？（左上角下拉選單選擇被加入的團隊） {#jgb/A/dashboard-team-switch}
- phrasings:
  - {text: "怎麼切換團隊", source: "draft:outline-20260920", status: proposed}
  - {text: "被加入多個團隊", source: "draft:outline-20260920", status: proposed}
  - {text: "團隊下拉選單在哪", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding00_zh-Hant.html, help:Landlordonboarding00phone_zh-Hant.html]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
登入後若已被管理業者加入團隊，可從畫面左上角的下拉選單選擇要檢視的團隊。
選擇團隊後，畫面即顯示該團隊所屬的物件、合約、帳務與修繕資訊。
手機版與電腦版是同一套系統、同一組功能，畫面只依螢幕寬度調整排列方式，功能不會因裝置而減少。
### 首頁的「滿租率(beta)」頁簽是什麼？（限定開放的社區收入統計，非所有團隊都看得到） {#jgb/A/dashboard-occupancy-tab}
- phrasings:
  - {text: "滿租率 beta", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁頁簽", source: "draft:outline-20260920", status: proposed}
  - {text: "社區收入統計", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/dashboard/Landlord.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
首頁除了「主要」頁簽外，只有被列入特定開放名單的團隊，才會多顯示「滿租率(beta)」頁簽。
切換到滿租率頁簽會改顯示社區收入統計圖表，取代原本的統計方塊與收支圖表區塊。
切換頁簽時，網址會記錄目前所在的頁簽，之後可以用該網址直接分享或加入書籤停留在該頁簽。
### 首頁「捷徑」區塊有哪些功能？（新增物件、新增合約、新增帳單、新增修繕、查看統計報表、查看大房東列表） {#jgb/A/dashboard-shortcuts-list}
- phrasings:
  - {text: "捷徑區塊有哪些功能", source: "draft:outline-20260920", status: proposed}
  - {text: "首頁捷徑按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/dashboard/parts/ShortCuts.vue, code:src/pages/users/dashboard/Landlord.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「捷徑」區塊列出常用的快速入口，包含新增物件、新增合約、新增帳單、新增修繕、查看統計報表、查看大房東列表。
首頁「捷徑」區塊只有符合特定操作權限（例如新增物件、新增合約、新增帳單、編輯屋主修繕、帳單圖表、屋主帳單圖表、顯示大房東其中之一）的使用者才會看到。
## 帳號資訊 {#A-account-profile}
### 帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂） {#jgb/A/account-basic-info}
- phrasings:
  - {text: "帳號基本資訊怎麼改", source: "draft:outline-20260920", status: proposed}
  - {text: "改姓名", source: "draft:outline-20260920", status: proposed}
  - {text: "改大頭照", source: "draft:outline-20260920", status: proposed}
  - {text: "帳號資訊頁面", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php, code:app/Http/Controllers/UserController.php#account, code:app/Contract.php, code:app/Http/Controllers/ContractController.php]
- reviewed: {by: owner, at: 2026-10-04}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號資訊頁的「帳號基本資訊」區塊可以上傳／更換大頭照（選填），並編輯姓氏、名稱、稱謂。
頁面說明這些資料是為了讓刊登廣告時租客有更安心的租屋體驗而蒐集的。
部分特定合作團隊的合約完成簽署後，系統會依簽署方式鎖定租客的基本資訊，兩種方式都要求已有租客的身分證字號，沒有身分證字號就不會鎖定；鎖定後，姓氏、名稱、稱謂三個欄位在畫面上不能再編輯，即使表單有送出新值也不會被更新。
### 帳號資訊頁怎麼看手機的綁定狀態？（已綁定／未綁定，未綁定才有「前往綁定」按鈕） {#jgb/A/account-phone-bind-status}
- phrasings:
  - {text: "手機有沒有綁定", source: "draft:outline-20260920", status: proposed}
  - {text: "手機綁定狀態", source: "draft:outline-20260920", status: proposed}
  - {text: "前往綁定按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號資訊頁的「帳號資訊」區塊會顯示手機號碼目前是「已綁定」或「未綁定」，未綁定時提供「前往綁定」按鈕導向手機驗證頁。
### 帳號資訊頁的 Email 驗證狀態怎麼看？（Email 無法自行更改，需聯繫客服） {#jgb/A/account-email-verify-status}
- phrasings:
  - {text: "email 驗證狀態", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼換 email", source: "draft:outline-20260920", status: proposed}
  - {text: "更換綁定信箱", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
同區塊也會顯示 Email 驗證狀態：一般帳號會顯示「已驗證」或「未驗證」；只有特定合作單位的帳號，才會顯示「未完成驗證」或「未設定」。
一般帳號的 Email 欄位是鎖定唯讀的，頁面提示如需更換 Email 帳號，需要聯繫 JGB 客服處理，不能在此頁直接自行修改。
### 手機已經綁定後可以自己更換嗎？（沒有更換入口，只顯示已綁定狀態） {#jgb/A/account-phone-no-change-entry}
- phrasings:
  - {text: "換手機號碼", source: "draft:outline-20260920", status: proposed}
  - {text: "更換綁定手機", source: "draft:outline-20260920", status: proposed}
  - {text: "手機已綁定還能改嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php, code:src/pages/users/auth/parts/PhoneVerify.vue]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號資訊頁的手機欄位一旦顯示「已綁定」，就不會再出現「前往綁定」或其他可以修改號碼的按鈕。
手機驗證流程如果偵測到目前帳號已經綁定過手機，會直接顯示「手機已綁定」畫面，並提示未來可以用這支電話號碼登入，接下來只有「繼續」按鈕，沒有換一支手機重新綁定的選項。
### 帳號資訊頁怎麼看 SSO 綁定狀態？（Facebook／Google／LINE 各自顯示已綁定或未綁定） {#jgb/A/account-sso-status}
- phrasings:
  - {text: "sso 綁定狀態", source: "draft:outline-20260920", status: proposed}
  - {text: "有沒有連 facebook", source: "draft:outline-20260920", status: proposed}
  - {text: "帳號有沒有連 google", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php, code:app/Http/Controllers/UserController.php#account]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號資訊頁「SSO 綁定狀態」區塊會分別列出 Facebook、Google、LINE 三個第三方帳號各自的綁定狀態（已綁定或未綁定）。
頁面本身沒有提供解除 SSO 綁定的按鈕或連結，只顯示 Facebook、Google、LINE 三個平台各自的綁定狀態。
「修改密碼」區塊只有在該帳號已經設有密碼時才會顯示；如果帳號是純粹用第三方帳號註冊、從未設定過密碼，此區塊會被隱藏。
### 登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼、新密碼與確認新密碼） {#jgb/A/account-change-password}
- phrasings:
  - {text: "登入後怎麼改密碼", source: "draft:outline-20260920", status: proposed}
  - {text: "帳號資訊改密碼", source: "draft:outline-20260920", status: proposed}
  - {text: "修改密碼要輸入原密碼嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php, code:app/Http/Controllers/UserController.php#account, code:src/components/PasswordForm.vue]
- reviewed: {by: owner, at: 2026-10-04}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
帳號資訊頁只有在帳號本身有設定密碼時，才會顯示「密碼」區塊。
帳號資訊頁點選「修改密碼」會展開密碼修改表單。
修改密碼必須同時填寫目前密碼、新密碼與確認新密碼；若目前密碼輸入錯誤，會回覆「目前密碼驗證錯誤」並擋下整筆表單儲存。
「密碼」區塊下方會顯示「上次更新：」的日期時間；如果從來沒有改過密碼，則顯示帳號建立的時間。
### 帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話） {#jgb/A/account-contact-info}
- phrasings:
  - {text: "聯絡資訊怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "WhatsApp 要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "line id 要填嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "第二組電話欄位有什麼限制", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php]
- reviewed: {by: owner, at: 2026-10-04}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「聯絡資訊」區塊會呈現在刊登的廣告上，讓租客有更多管道聯繫房東。
LINE 欄位可勾選「同手機號碼」，勾選後不需另外輸入 LINE ID；未勾選時可以自行填寫 LINE ID，這個欄位不是必填。
Facebook 欄位填寫的是個人首頁連結，欄位長度上限 200 字元。
WhatsApp 欄位旁有提示：請填寫國碼與電話號碼、國碼前面不需打「+」，欄位長度上限 200 字元。
第二組聯絡號碼欄位長度上限 50 字元。
畫面上目前沒有「以此電話作為廣告頁聯絡電話」這個核取方塊可以勾選。
### 帳號資訊頁的偏好設定能設定什麼？（登入預設房東身份、時區、Email 通知語系） {#jgb/A/account-preference}
- phrasings:
  - {text: "登入預設身份怎麼設", source: "draft:outline-20260920", status: proposed}
  - {text: "時區設定在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "Email 通知語言", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/users/account.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「偏好設定」可以指定「登入預設房東身份」，決定同帳號有多個房東身份時預設要進入哪一個。
可選擇非台灣時區，選擇後系統會將排程通知（例如每日過期帳單通知、合約 30 天內到期提醒）的發送時間改用所選時區計算。
可設定「Email 通知語系」，決定收到系統通知信時使用哪種語言。
### 帳號資訊頁有「資訊完整度」進度條嗎？（目前頁面上不會顯示這個區塊） {#jgb/A/account-progress-unlock}
- phrasings:
  - {text: "資訊完整度是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼不能刊登廣告", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼不能簽約", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php#account, code:resources/views/users/account.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
帳號資訊頁目前不會顯示「會員狀態」卡片與「資訊完整度」進度條，這個區塊目前對使用者是關閉的。
「簽約資訊」是一個獨立於帳號資訊頁的頁面，用來填寫簽約所需的身份資料（如身分證字號、戶籍地址等），不是本頁「帳號基本資訊」的欄位。
### 帳號資訊頁儲存失敗會提示什麼？（頁面沒有完整載入時會提醒重新整理再儲存） {#jgb/A/account-save-integrity-check}
- phrasings:
  - {text: "儲存失敗提示", source: "draft:outline-20260920", status: proposed}
  - {text: "帳號資訊存不進去", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php#account]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果送出儲存時，系統偵測到頁面沒有完整載入（缺少應該要有的欄位），會擋下這次儲存，並提示「頁面沒有完整載入，這次的資料沒有儲存，請重新整理頁面後再儲存一次」。
### 在帳號資訊頁改密碼，新密碼有什麼規則？（至少 6 個字元、需與確認新密碼一致；英數混合在這裡只是提示） {#jgb/A/account-change-password-rules}
- phrasings:
  - {text: "改密碼有什麼限制", source: "draft:outline-20260920", status: proposed}
  - {text: "改密碼一定要英文加數字嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "帳號資訊頁新密碼規則", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/UserController.php, code:src/components/PasswordForm.vue, code:resources/views/users/account.blade.php, code:app/Http/Controllers/AuthController.php]
- reviewed: {by: owner, at: 2026-10-04}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在帳號資訊頁修改密碼時，新密碼長度需至少 6 個字元，且需與確認新密碼欄位一致。
帳號資訊頁的密碼表單會提示「密碼應有至少一位英文和數字」，但按「儲存」時不會檢查這一條。
註冊帳號時設定的密碼則必須同時包含英文與數字。
## 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章） {#A-signer-info}
### 個人房東的簽約資訊要填什麼？（姓氏、名稱、身分證字號、Email、手機、身分證正反面） {#jgb/A/signer-individual-fields}
- phrasings:
  - {text: "個人房東簽約資訊", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約要填身分證嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約資訊個人欄位", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
個人身分的簽約資訊必填欄位為姓氏、名稱、身分證字號。
另需填寫 Email 與手機號碼，同樣列為必填。
身分證正反面照片為附件上傳項目，走證件引導裁切流程。
另可上傳「工作名片/學生證」「良民證」「小章」三項其他附件，皆非必填。
如果有多筆個人身分資料（例如同時管理多個角色），表單上方會出現一列可以橫向捲動切換的項目；超過 5 筆時，會多一個「所有團隊」的下拉選單方便切換。
### 公司身分的簽約資訊要填什麼？（公司名稱、統編、負責人、公司電話/Email、登記證資料） {#jgb/A/signer-corp-fields}
- phrasings:
  - {text: "公司簽約資訊", source: "draft:outline-20260920", status: proposed}
  - {text: "統編怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "公司負責人要填嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
公司/團隊身分的簽約資訊必填項目為公司登記名稱（上限 20 字）、公司統編、公司電話、公司 Email；社宅團隊另外必須填寫公司負責人。
統編欄位可選擇類型：「公司統編(檢核)」會用台灣統編檢查碼規則驗證格式，長度上限 8 碼；選「其他統編(不檢核)」則不驗證，長度上限放寬到 20 碼。
公司登記證號、登記證日期、公司登記證縣市為選填欄位；若身分是社宅團隊，公司登記證號則改為必填。
「公司負責人」是公司團隊都會顯示的欄位，社宅團隊為必填、其他公司團隊為選填；「社宅業者編號」只有社宅團隊才會顯示並填寫，一般公司團隊看不到這個欄位。
### 公司身分可以上傳哪些印章與證件附件？（公司大章、小章、經紀人章、經紀業章、租賃管理員章，皆為選填） {#jgb/A/signer-corp-seals}
- phrasings:
  - {text: "公司大小章上傳", source: "draft:outline-20260920", status: proposed}
  - {text: "經紀人章要傳嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約印章附件", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
公司身分的簽約資訊可以上傳五種印章附件：公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章；這五個欄位一律都會出現在頁面上，皆為選填。
除了這五種印章之外，還有一個獨立的「電子簽約圖章」欄位（畫面上顯示為「圖章」），用來啟用「預設使用圖章取代親手簽名」的簽約方式，走另一組上傳流程。
### 有不動產經紀人／租賃管理人員資格要多填什麼？（經紀人證號、租賃管理人員證號等） {#jgb/A/signer-broker-manager-fields}
- phrasings:
  - {text: "經紀人證號要填嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "租賃管理人員資訊", source: "draft:outline-20260920", status: proposed}
  - {text: "經紀業名稱", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
公司簽約資訊可填寫經紀人名稱（上限 15 字）與經紀人證號、經紀業名稱（上限 15 字）與經紀業證號。
也可填寫租賃管理人員名稱與租賃管理人員證號；租賃管理人員目前沒有對應的 Email 欄位，只有經紀人才有經紀人 Email 欄位。
若身分為社宅團隊，經紀人名稱、經紀人證號、租賃管理人員名稱、租賃管理人員證號皆會變為必填欄位，並且會多顯示經紀人的聯絡電話與 Email、以及租賃管理人員的聯絡電話；一般公司團隊這些欄位皆為選填或不顯示。
### 簽約資訊誰能編輯？（沒有編輯權限的欄位會顯示為停用樣式） {#jgb/A/signer-edit-permission}
- phrasings:
  - {text: "誰能改簽約資訊", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有編輯權限會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約資訊唯讀", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/signerInfo/Index.vue, code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「簽約資訊」頁面本身固定以可編輯模式載入。
團隊的簽約資訊只有團隊擁有者，或具備編輯團隊資訊權限的成員可以編輯；沒有權限時，公司登記名稱、統編、負責人等公司欄位會顯示為停用樣式。
個人身分的欄位元件目前沒有這種可設為不可編輯的樣式切換，固定顯示為一般可編輯樣式；只有公司身分的欄位會依此顯示停用樣式。
### 簽約資訊的地址欄位怎麼填？（戶籍/通訊地址、公司登記/通訊地址皆為必填，可一鍵「同戶籍地址」「同公司登記地址」） {#jgb/A/signer-address-fields}
- phrasings:
  - {text: "戶籍地址要填嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "通訊地址可以跟戶籍一樣嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "公司登記地址", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
個人身分需填寫「戶籍地址」與「通訊地址」，兩者皆為必填。
通訊地址欄位旁提供「同戶籍地址」按鈕，點擊後會直接把戶籍地址的內容複製到通訊地址。
公司身分則對應填寫「公司登記地址」與「公司通訊地址」，同樣皆為必填，並提供「同公司登記地址」快速複製按鈕。
只有社宅團隊，才會額外顯示經紀人通訊地址與租賃管理人員通訊地址兩個獨立欄位；非社宅團隊即使有經紀人或租賃管理人員資格，也不會顯示這兩個地址欄位。
### 公司名下有多筆簽約對象時要怎麼切換？（表單上方出現切換列，超過 5 筆再加「所有團隊」下拉選單） {#jgb/A/signer-multi-entry-switch}
- phrasings:
  - {text: "公司多筆簽約對象切換", source: "draft:outline-20260920", status: proposed}
  - {text: "多個公司要怎麼切換", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果目前團隊底下有多筆公司簽約對象資料，簽約資訊表單上方會出現一列可以切換的項目，點選就能切到不同的對象。
超過 5 筆公司簽約對象時，會多一個「所有團隊」的下拉選單，方便直接選擇要編輯的對象，而不是逐一點選切換列。
### 簽約資訊頁的「管理」「儲存」按鈕做什麼？（管理開啟簽約對象視窗可新增或刪除，儲存只在個人身分頁面出現） {#jgb/A/signer-manage-save-buttons}
- phrasings:
  - {text: "簽約資訊管理按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約資訊儲存按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/team/_parts/SignerDetails.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「管理」按鈕會開啟管理簽約對象的視窗，可以新增簽約對象，或刪除既有的簽約對象。
「儲存」按鈕只有在個人身分、且位於「簽約資訊」這個獨立頁面時才會出現，用來單獨儲存目前這筆個人簽約資料。
## 通知中心 {#A-notification-center}
### 通知中心怎麼依類型篩選通知？（依合約/帳務/修繕/裝置/其他分類） {#jgb/A/notification-center-type-filter}
- phrasings:
  - {text: "通知中心怎麼篩選", source: "draft:outline-20260920", status: proposed}
  - {text: "通知中心的通知類型有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼看合約類通知", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/NotificationController.php#index]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
通知中心提供依類型篩選的下拉選單，選項為全部、合約、帳務、修繕、裝置、其他。
### 通知中心的通知怎麼標示未讀？（列表項目左側的紅點，沒有「只顯示未讀」的篩選功能） {#jgb/A/notification-center-unread-dot}
- phrasings:
  - {text: "只看未讀通知", source: "draft:outline-20260920", status: proposed}
  - {text: "通知未讀紅點", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/notifications/index.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
通知列表中，尚未讀取的通知，項目左側會有一個小紅點做提示。
頁面目前沒有「只顯示未讀」這種篩選核取方塊，無法只篩選未讀通知。
### 通知中心每頁顯示筆數可以怎麼調整？（30/60/90 筆，預設 30 筆） {#jgb/A/notification-center-per-page}
- phrasings:
  - {text: "通知每頁幾筆", source: "draft:outline-20260920", status: proposed}
  - {text: "通知中心分頁", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/NotificationController.php#index]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
每頁顯示筆數可切換 30 項、60 項或 90 項，預設為 30 項。
### 為什麼通知中心是空的？（房東側需要查看通知的權限才看得到通知內容） {#jgb/A/notification-center-permission}
- phrasings:
  - {text: "通知中心是空的", source: "draft:outline-20260920", status: proposed}
  - {text: "為什麼看不到通知", source: "draft:outline-20260920", status: proposed}
  - {text: "通知權限", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/NotificationController.php#index, code:resources/views/notifications/index.blade.php]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客身分一律能看到自己的通知內容。
房東側（非租客）使用者，只有具備查看通知的權限，通知中心才會顯示實際通知資料。
沒有這項權限時，類型篩選下拉選單仍會顯示，但會變成停用樣式；每頁筆數選單則完全不會出現；畫面主要區塊會顯示「您還沒有收到任何通知，再等等吧 📭」，而不是錯誤訊息。
### 點擊通知列表項目會發生什麼？（前往原連結並把該則通知標為已讀；訊息類通知不換頁） {#jgb/A/notification-mark-read-navigate}
- phrasings:
  - {text: "點通知會怎樣", source: "draft:outline-20260920", status: proposed}
  - {text: "通知會標記已讀嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "通知連結", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/NotificationController.php#index, code:resources/views/notifications/index.blade.php, code:app/Http/Controllers/Controller.php, code:app/Notification.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
除了訊息類通知之外，每則通知點擊後都會依原本的連結網址前往對應頁面，並在網址上多帶一個通知編號參數。
前往的頁面載入時，系統會依這個參數把這則通知標為已讀，並把網址上的這個參數拿掉。
訊息類通知則是在原頁面開啟訊息視窗，不會換頁。
### 篩選後頁碼超出範圍會自動跳回第一頁嗎？（不會，只會顯示空的通知清單） {#jgb/A/notification-mark-read-out-of-range}
- phrasings:
  - {text: "通知頁碼超出範圍", source: "draft:outline-20260920", status: proposed}
  - {text: "篩選後跳到空白頁", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/NotificationController.php#index]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
篩選通知後如果頁碼超出範圍，畫面不會自動跳回第一頁，只會顯示空的通知清單。
### 導覽列的通知鈴鐺會顯示什麼？（最近 5 筆通知與未點擊數量，大房東不會顯示） {#jgb/A/notification-navbar-bell}
- phrasings:
  - {text: "導覽列通知鈴鐺", source: "draft:outline-20260920", status: proposed}
  - {text: "鈴鐺數字是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "紅點跟鈴鐺數字差別", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/NotificationController.php#navbar]
- reviewed: {by: owner, at: 2026-09-28}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
導覽列鈴鐺點開後只會列出最近 5 筆通知，跟通知中心的完整列表不同。
鈴鐺上顯示的數字，是使用者「還沒點擊過」的通知數量；這跟通知列表項目旁的紅點（未讀）是兩個獨立的狀態，分別依據不同的欄位判斷。
跟通知中心一樣，只有租客身分或具備查看通知權限的房東側使用者才會取得通知資料；如果目前是大房東身分，即使有這項權限，鈴鐺也不會顯示通知資料。
## 通知收件設定與發送報表（通知收件信箱最多再加 3 組） {#A-notification-settings}
### 通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱） {#jgb/A/notification-settings-extra-emails}
- phrasings:
  - {text: "通知收件信箱最多幾組", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼加通知信箱", source: "draft:outline-20260920", status: proposed}
  - {text: "額外通知信箱", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/notification/Index.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「通知收件設定」頁面說明每個通知信分類最多可再新增 3 組電子信箱收取通知信件。
預設信箱欄位固定顯示目前身分（團隊）擁有者的 Email，此欄位鎖定無法編輯；團隊成員看到的也是團隊擁有者的信箱。
每個通知分類卡片內都可各自新增/移除最多 3 組自訂收件信箱，每組都是標準 Email 格式輸入框且為必填，彼此分類互不共用額度。
需要具備通知設定的編輯權限，才能新增信箱、儲存表單；沒有這個權限時，「新增信箱」與「儲存」按鈕會直接消失，但每組信箱旁的移除（×）按鈕仍會顯示，只是變成無法點擊的停用樣式。
### 通知收件設定有哪些分類？（合約、帳務、修繕、訂閱、房東管理，另有限定開放的加盟分潤報表） {#jgb/A/notification-settings-categories}
- phrasings:
  - {text: "通知收件設定的分類有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "帳務通知包含什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "訂閱通知是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useForwardNotificationEmails.ts]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「合約管理類別」包含租客簽名、合約成立、提前解約等通知信。
「帳務管理類別」包含帳單已到帳、租客已匯款、金額不匹配等通知信。
「修繕管理類別」包含租客提出修繕、修改修繕備註等通知信。
「訂閱管理類別」包含訂閱方案修改、即將扣款、取消訂閱等通知信。
「房東管理類別」包含大房東報表排定發送等通知信。
「加盟分潤報表」類別只有被列入特定開放名單的團隊才會顯示，若想讓新團隊加入分潤報表需另外聯繫 JGB。
### 「發送報表」「多團隊合併報表」按鈕是做什麼的？（選起始日與終止日，把加盟分潤報表寄到自訂通知信箱；僅限加盟分潤報表分類，多團隊合併僅限特定團隊） {#jgb/A/notification-settings-report-buttons}
- phrasings:
  - {text: "發送報表按鈕", source: "draft:outline-20260920", status: proposed}
  - {text: "多團隊合併報表", source: "draft:outline-20260920", status: proposed}
  - {text: "分潤報表怎麼看", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/config/useForwardNotificationEmails.ts, code:src/pages/users/notification/Index.vue, code:src/components/Lightbox/NotificationMailReport.vue, code:app/Services/FranchiseProfitShareService.php]
- reviewed: {by: owner, at: 2026-10-03}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只有「加盟分潤報表」分類（限定開放的特定合作團隊才看得到）會顯示「發送報表」按鈕，點擊會開啟選擇時間區間的視窗。
在視窗裡選好「起始日」與「終止日」後按「發送」，系統會把這段期間的加盟分潤報表寄到這個分類設定的自訂通知信箱，成功時會顯示「報表已發送至指定信箱」。
如果這段期間沒有分潤資料，或這個分類還沒有設定自訂通知信箱，報表不會寄出，畫面會跳出失敗提示，說明是查無分潤資料或未設定收件人。
「多團隊合併報表」按鈕只在特定合作團隊底下才會顯示，其餘分類與團隊都看不到這個按鈕。
「多團隊合併報表」視窗同樣選起始日與終止日，系統會把幾個合作團隊在這段期間的加盟分潤資料合併成一份報表，寄到這個分類設定的自訂通知信箱。
點擊「發送報表」或「多團隊合併報表」按鈕時，會依目前所在的通知分類，開啟對應的報表視窗。
### 通知收件設定改完怎麼儲存？（至少要有一個分類填了自訂信箱，儲存鍵才會啟用） {#jgb/A/notification-settings-save}
- phrasings:
  - {text: "通知設定怎麼存", source: "draft:outline-20260920", status: proposed}
  - {text: "儲存按鈕按不下去", source: "draft:outline-20260920", status: proposed}
  - {text: "沒填信箱能存嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/users/notification/Index.vue]
- reviewed: {by: owner, at: 2026-09-29}
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「儲存」按鈕只有在至少一個分類已經填了自訂收件信箱時才會啟用，否則呈現停用樣式且送出動作不會執行。
儲存成功會顯示「儲存成功」提示；若儲存失敗，畫面會用系統回傳的訊息或預設「儲存失敗，請稍後再試」顯示錯誤提示；若發生網路錯誤則顯示「網路錯誤，請稍後再試」
頁面載入時會自動取得目前各分類的自訂信箱與預設信箱，按下「儲存」則會把整包分類資料送出更新。
