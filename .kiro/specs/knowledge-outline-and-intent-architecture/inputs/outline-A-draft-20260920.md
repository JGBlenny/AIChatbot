# A 架草稿（jgb2 master @ b2ee2ac382ce；粗目 8、細目 63、句 166）

讀法：每個粗目底下一條細目答一件事；句子後的〔〕是來源檔（程式或幫助中心頁）；「待查」是文件與程式衝突或程式裡查不到的，未選邊。

## 註冊帳號（Email／SSO、驗證碼、手機綁定）（12 條；頁：users.create、users.verify、users.verify.phone）

### 如何註冊 JGB 帳號？（Email、驗證碼、帳號設定三步驟）
- 講法：怎麼註冊帳號／註冊流程是什麼／第一次用要怎麼開帳號／註冊要填什麼／怎麼申請 JGB 帳號
- 給誰看：property_manager、prospect
- 註冊只需要一組 Email，同一個帳號可以同時擁有房東和租客身分。〔幫助中心:onboarding1_zh-Hant.html〕
- 第一步輸入 Email 並勾選「我不是機器人」驗證後按繼續，系統會寄送驗證碼到該信箱。〔src/pages/users/auth/parts/CreateWelcome.vue〕
- 第二步輸入收到的 Email 驗證碼完成信箱驗證。〔src/pages/users/auth/parts/EmailVerify.vue〕
- 第三步填寫姓氏、名稱、稱謂並設定密碼，按下「完成註冊」即建立帳號。〔src/pages/users/auth/parts/AccountSetting.vue〕
- 註冊時需先閱讀並同意服務條款和隱私權聲明才能繼續下一步。〔src/pages/users/auth/parts/CreateWelcome.vue〕

### 租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「註冊」接續完成）
- 講法：租客電子合約邀請註冊／房東邀請租客簽約怎麼註冊／收到合約邀請信怎麼辦／租客可以不註冊嗎
- 給誰看：property_manager、prospect
- 租客還沒有 JGB 帳號時，房東在建立合約時輸入租客的 Email 或手機號碼發送邀請，房東端會進入「待租客簽回」畫面，顯示尚未註冊會員租客的 Email 帳號。〔幫助中心:onboarding1_zh-Hant.html〕
- 租客會收到簽約邀請郵件，點選信中的「查看合約」按鈕後，會進入該物件的廣告頁供租客參考。〔幫助中心:onboarding1_zh-Hant.html〕
- 租客在廣告頁確認無誤後，點選頁面右下角的「查看合約」，因為還未註冊成為 JGB 會員，會先進入 JGB 登入畫面，此時點選「註冊」按鈕即可完成註冊，並接續完成合約。〔幫助中心:onboarding1_zh-Hant.html〕
- 租客也可以選擇不註冊帳號，改由房東自行填寫租客的身份資料。〔幫助中心:onboarding1_zh-Hant.html〕

### 可以用 Facebook、Google、LINE 註冊嗎？（SSO 仍需完成 Email 綁定）
- 講法：可以用臉書登入註冊嗎／可以用 Google 帳號註冊嗎／LINE 可以註冊嗎／第三方帳號註冊／SSO 註冊
- 給誰看：property_manager、prospect
- 註冊頁除了 Email 之外，也提供 Facebook、Google、LINE 三種第三方帳號快速註冊。〔src/pages/users/auth/parts/SSOBar.vue〕
- 透過 LINE 內建瀏覽器開啟 Google 註冊時，系統會另外開啟外部瀏覽器完成驗證。〔src/pages/users/auth/parts/SSOBar.vue〕
- 用第三方帳號註冊成功後，仍會導向 Email 驗證流程，系統會自動帶入對應的 Email 完成綁定。〔幫助中心:onboarding1_zh-Hant.html〕

### 註冊卡在機器人驗證過期怎麼辦？（會退回第一步重新勾選）
- 講法：機器人驗證過期／我不是機器人卡住／註冊一直失敗／驗證框顯示不出來
- 給誰看：property_manager
- 若「我不是機器人」驗證已經過期，畫面會提示重新輸入 Email 並重新勾選「我不是機器人」，流程退回到第一步的 Email 輸入畫面。〔src/pages/users/auth/parts/CreateWelcome.vue〕
- 退回第一步時，先前輸入的 Email 與驗證通行證會被清空，需要重新輸入 Email 並重新勾選「我不是機器人」才能繼續。〔src/pages/users/auth/parts/EmailVerify.vue〕

### 沒收到 Email 驗證碼怎麼辦？（可重發，發送次數過多會出現等待秒數）
- 講法：沒收到驗證信／驗證碼重發／驗證信在等待／Email 驗證碼過期
- 給誰看：property_manager
- 驗證碼輸入畫面提供「重發驗證信」的連結，可以重新觸發寄送。〔src/pages/users/auth/parts/EmailVerify.vue〕
- 短時間內重複要求重發時，系統會回傳等待秒數，重發連結在倒數期間會停用並顯示剩餘秒數。〔src/pages/users/auth/parts/EmailVerify.vue〕
- 超過發送次數上限時，畫面上會出現對應的錯誤提示。〔src/pages/users/auth/parts/EmailVerify.vue〕
- 如果 Email 打錯，可以點「點此重新輸入」返回第一步修改。〔src/pages/users/auth/parts/EmailVerify.vue〕

### 註冊密碼格式要求是什麼？（至少 6 碼、須同時包含英文與數字）
- 講法：密碼規則／密碼要幾碼／密碼格式／設定密碼限制
- 給誰看：property_manager、prospect
- 密碼長度至少需 6 個字元（含）以上。〔src/pages/users/auth/parts/AccountSetting.vue〕
- 密碼須同時包含至少一個英文字母和一個數字，只有英文或只有數字都無法通過。〔src/pages/users/auth/parts/AccountSetting.vue〕
- 確認密碼欄位必須與密碼欄位輸入一致才能完成註冊。〔src/pages/users/auth/parts/AccountSetting.vue〕

### 註冊時 Email 已被註冊過怎麼辦？（系統會將帳號合併）
- 講法：Email 已經註冊過／帳號合併／重複註冊／曾經用 SSO 註冊過還能再用 Email 註冊嗎
- 給誰看：property_manager
- 驗證信步驟通過後，系統會先檢查該 Email 是否已被註冊（例如先前已用同一 Email 透過第三方帳號註冊過）。〔src/pages/users/auth/parts/AccountSetting.vue〕
- 若已註冊，畫面標題會顯示「帳號已註冊」，並提示該 Email 已註冊過、JGB 將進行帳號合併，使用者按「繼續」即可完成流程進入下一步（綁定手機）。〔src/pages/users/auth/parts/AccountSetting.vue〕
- 此情境按「繼續」時會直接完成帳號設定，不會再檢查姓名、密碼等欄位是否填寫完整。〔src/pages/users/auth/parts/AccountSetting.vue〕

### 註冊要綁定手機號碼嗎？（可選填、簡訊驗證、可「下次再驗證」略過）
- 講法：註冊要綁手機嗎／手機驗證怎麼做／可以跳過手機驗證嗎／手機驗證碼收不到
- 給誰看：property_manager、prospect
- 帳號設定完成後會進入綁定手機的步驟，可選擇國碼並輸入手機號碼，號碼長度上限依所選國家而有上限。〔src/pages/users/auth/parts/PhoneVerify.vue〕
- 送出後系統會發送簡訊驗證碼，輸入正確驗證碼即完成綁定。〔src/pages/users/auth/parts/PhoneVerify.vue〕
- 在註冊流程中，這一步驟可以按「下次再驗證」略過，不會擋住完成註冊。〔src/pages/users/auth/parts/PhoneVerify.vue〕
- 簡訊驗證碼一樣提供「重發簡訊」功能，重複發送過於頻繁時會出現等待秒數限制。〔src/pages/users/auth/parts/PhoneVerify.vue〕
- 綁定手機後，未來登入、忘記密碼、忘記帳號都可以使用該手機號碼進行驗證或作為替代登入方式。〔src/pages/users/auth/parts/PhoneVerify.vue〕

### 註冊時發現手機已綁定過怎麼辦？（直接顯示已綁定、按繼續完成流程）
- 講法：手機已經綁定過／重複綁定手機
- 給誰看：property_manager
- 系統會在進入手機綁定步驟前先檢查目前帳號是否已有綁定手機。〔src/pages/users/auth/parts/PhoneVerify.vue〕
- 若已綁定，畫面會直接顯示「手機已綁定」，說明未來可用手機號碼登入或作為忘記帳號時的替代找回方式，按「繼續」即可完成註冊流程。〔src/pages/users/auth/parts/PhoneVerify.vue〕
- 若是在註冊流程中出現此畫面，按「繼續」會前進到選擇身分步驟；若是註冊完成後在其他情境觸發手機驗證，則會依原本要前往的頁面返回，不會進入選擇身分畫面。〔src/pages/users/auth/parts/PhoneVerify.vue〕

### 註冊完之後要選身分嗎？（房東/管理者、租客二選一，可同時擁有兩種身分）
- 講法：註冊完要選身分嗎／房東身分和租客身分／怎麼切換房東和租客／我是房東還是租客
- 給誰看：property_manager、prospect
- 註冊或登入時都會出現身分選擇畫面，讓使用者選擇「我是房東/管理者」或「我是租客」。〔src/pages/users/auth/parts/RoleSelect.vue〕
- 同一組帳號可同時擁有房東與租客兩種身分，選擇的身分只決定這次要進入哪一種介面。〔幫助中心:onboarding1_zh-Hant.html〕
- 若是從租客端網站導轉來註冊，選擇身分後系統會依照先前記下的導轉網址，把使用者導回原本要前往的頁面，而不是進入一般會員中心首頁。〔src/pages/users/auth/parts/RoleSelect.vue〕

### 驗證碼輸入畫面長什麼樣子？（識別碼加 4 碼數字，輸入錯誤太多次會被鎖住）
- 講法：驗證碼長什麼樣子／驗證碼輸入錯誤被鎖／驗證碼幾碼
- 給誰看：property_manager
- 驗證碼輸入畫面由兩部分組成：左邊顯示一組簡短的識別碼，右邊是使用者要輸入的 4 碼數字驗證碼。〔src/pages/users/auth/parts/VerifyPanel.vue〕
- 如果驗證碼連續輸入錯誤太多次，畫面會顯示對應的錯誤訊息；手機驗證、忘記帳號、忘記密碼這三個流程的輸入框會同時被鎖住、無法再輸入，但註冊時的 Email 驗證流程只會顯示錯誤訊息，輸入框不會被鎖住。〔src/pages/users/auth/parts/VerifyPanel.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -n "isLocked" master -- src/pages/users/auth/parts/', 'result': 'EmailVerify.vue 0 個命中（沒有把 isLocked 傳給 VerifyPanel，畫面不會鎖住輸入框，只會顯示錯誤訊息）', 'control_term': 'PhoneVerify.vue／forget/Account.vue／forget/Password.vue 各 1 個命中（正對照組：這三個檔案都有把 isLocked 綁到 VerifyPanel，輸入框會被鎖住）'}`

### 從驗證信連結折返時會從頭開始註冊嗎？（不會，系統會記住 Email 直接跳到輸入驗證碼畫面）
- 講法：點驗證信連結會不會重來／收信後點回註冊頁／驗證信折返
- 給誰看：property_manager
- 透過信箱 App 開啟的註冊邀請連結，常會用信箱 App 內建的瀏覽器開啟；使用者跳去收驗證信、再重新點開連結時，很容易讓整個註冊流程從頭開始重跑一次。〔src/pages/users/auth/Create.vue〕
- 為了避免這個情況，系統會把使用者輸入過的 Email 記在瀏覽器裡；只要偵測到有記住的 Email，而且上次是停在輸入驗證碼的步驟，就會直接帶使用者跳到輸入驗證碼畫面，不需要重新輸入 Email。〔src/pages/users/auth/parts/CreateWelcome.vue〕

## 登入（11 條；頁：users.login）

### JGB 有哪些登入方式？（Email、手機號碼、Facebook／Google／LINE）
- 講法：怎麼登入／登入方式有哪些／可以用手機登入嗎／SSO 登入
- 給誰看：property_manager、prospect
- 登入表單可在 Email 與手機號碼兩種帳號輸入方式間切換。〔src/pages/users/auth/parts/LoginForm.vue〕
- 登入頁另外提供 Facebook、Google、LINE 第三方帳號登入。〔src/pages/users/auth/parts/SSOBar.vue〕

### 登入前為什麼要先選擇身分？（決定進入房東/管理者或租客的登入表單）
- 講法：登入頁面在哪／為什麼要選身分才能登入
- 給誰看：property_manager、prospect
- 登入前需先選擇身分：房東/管理者或租客。〔src/pages/users/auth/parts/RoleSelect.vue〕

### 用手機號碼登入時，國碼與號碼格式有什麼規則？（號碼長度上限與格式依所選國家而定）
- 講法：手機登入國碼／手機號碼格式限制／手機登入長度限制
- 給誰看：property_manager、prospect
- 選擇手機號碼登入時需先選擇國碼，號碼長度上限依所選國家而定，且手機格式會依所選國家的規則做檢查。〔src/pages/users/auth/parts/LoginForm.vue〕

### 「記住我」是做什麼？（只延長登入效期，跟記住登入方式無關）
- 講法：記住我是什麼
- 給誰看：property_manager、prospect
- 「記住我」勾選只影響下次登入送出時是否要延長登入效期，跟登入方式無關；不論是否勾選「記住我」，上次選擇用 Email 還是手機號碼登入，下次開啟登入頁都會沿用同一種方式。〔src/pages/users/auth/parts/LoginForm.vue〕

### 從 Facebook／Google／LINE 導回登入頁時，第三方登入按鈕會重複出現嗎？（不會）
- 講法：第三方登入導回重複按鈕／上次用什麼方式登入
- 給誰看：property_manager、prospect
- 如果是從 Facebook、Google、LINE 登入導回登入頁的情況，畫面不會重複顯示這些第三方登入按鈕。〔src/pages/users/auth/parts/LoginForm.vue〕

### 登入時身分選錯了怎麼辦？（會依選擇的身分決定進入哪個角色的登入表單）
- 講法：登入身分選錯／怎麼切換登入身分／房東登入還是租客登入
- 給誰看：property_manager
- 登入頁網址可以帶身分參數，直接跳到對應身分（房東/管理者或租客）的登入表單。〔src/pages/users/auth/Login.vue〕
- 若沒有帶身分參數，或參數不是這兩者之一，會停留在身分選擇畫面，需先點選「房東/管理者」或「租客」卡片才會出現帳號密碼欄位。〔src/pages/users/auth/Login.vue〕
- 登入表單元件與身分選擇元件共用同一份角色欄位，只要這個角色欄位被清空，畫面就會自動跳回身分選擇畫面，不會停在空白的帳密表單。〔src/pages/users/auth/parts/LoginForm.vue〕

### 登入帳號或密碼錯誤時會顯示什麼？
- 講法：登入失敗／帳號密碼錯誤／登不進去
- 給誰看：property_manager
- 登入失敗時，畫面會在密碼欄位下方顯示錯誤訊息。〔src/pages/users/auth/parts/LoginForm.vue〕
- 任何一個登入欄位（國碼、手機、Email、密碼）內容變更後，先前的錯誤訊息會被清除，需重新送出才會再次驗證。〔src/pages/users/auth/parts/LoginForm.vue〕
- 切換登入方式（Email／手機號碼）時，原本輸入的帳號欄位與密碼會一併被清空，需要重新輸入。〔src/pages/users/auth/parts/LoginForm.vue〕

### 登入頁的「忘記密碼？」連結在哪裡？（在登入表單下方，點擊前往忘記密碼流程）
- 講法：忘記密碼在哪／忘記密碼連結
- 給誰看：property_manager
- 登入表單下方提供「忘記密碼？」連結，點擊後會前往忘記密碼流程頁面。〔src/pages/users/auth/parts/LoginForm.vue〕

### 登入頁的「忘記帳號？」連結在哪裡？（在登入表單下方，點擊前往忘記帳號流程）
- 講法：忘記帳號在哪／忘記帳號連結
- 給誰看：property_manager
- 登入表單下方提供「忘記帳號？」連結，點擊後會前往忘記帳號流程頁面。〔src/pages/users/auth/parts/LoginForm.vue〕

### 登入頁下面有連到註冊頁的連結嗎？（「還沒有帳號嗎？立即註冊」）
- 講法：登入頁下面有什麼連結／還沒帳號怎麼註冊
- 給誰看：property_manager、prospect
- 尚未註冊的使用者也可從登入頁「還沒有帳號嗎？立即註冊」連結前往註冊頁。〔src/pages/users/auth/parts/LoginForm.vue〕

### 同一帳號同時有房東與租客身分時怎麼切換？（登入時重新選擇身分，或在帳號資訊設定預設身分）
- 講法：房東租客身分切換／怎麼換身分登入／登入預設身分
- 給誰看：property_manager
- 同一組帳號如果同時有房東/管理者與租客兩種身分，登入時可以在身分選擇畫面重新選擇這次要用哪一種身分進入。〔src/pages/users/auth/Login.vue〕
- 如果同時管理多個房東身分／團隊，可以到帳號資訊頁的「偏好設定」設定登入預設要進入的房東身分，之後登入會直接帶入這個預設身分。〔app/Http/Controllers/UserController.php〕
- ⚠️ 待查：本頁程式只證實同組帳號可有房東與租客兩種身分、以及登入時重選身分／偏好設定裡的預設房東身分；是否存在「已登入狀態下不重新登入即可切換身分」的入口，本次盤查未找到來源，待業主或後續盤查補充。

## 忘記帳號、忘記密碼（4 條；頁：users.forget、users.forget.account、users.forget.password）

### 忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示）
- 講法：忘記帳號怎麼辦／忘記 email 帳號／找回帳號
- 給誰看：property_manager
- 忘記帳號功能只能用「當初綁定在帳號上的手機號碼」進行簡訊驗證碼驗證來找回。〔src/pages/users/auth/parts/forget/Account.vue〕
- 如果帳號當初沒有綁定手機號碼，忘記帳號畫面上會提示需改聯繫 JGB 客服協助。〔src/pages/users/auth/parts/forget/Account.vue〕
- 手機驗證成功後，畫面會顯示身份驗證成功並給出帳號提示（Email 提示字串），而不是直接顯示完整帳號。〔src/pages/users/auth/parts/forget/Account.vue〕
- 如果驗證完成後仍無法藉此找回帳戶，需要聯繫所屬的租賃管理業者，由業者協助向 JGB 申請重新找回帳號。〔幫助中心:slug01_zh-Hant.html〕

### 沒綁手機號碼還能用「忘記帳號」找回嗎？（不行，只能靠手機簡訊驗證）
- 講法：沒綁手機忘記帳號／沒有手機號碼怎麼找回帳號
- 給誰看：property_manager
- 忘記帳號功能的驗證方式只有手機簡訊驗證碼一種，沒有 Email 驗證選項。〔src/pages/users/auth/parts/forget/Account.vue〕
- 帳號如果沒有綁定手機號碼，就無法透過此頁面自助找回，畫面上直接提示改為聯繫 JGB 客服。〔src/pages/users/auth/parts/forget/Account.vue〕
- 手機號碼欄位在輸入過程中會即時顯示驗證結果（成功或錯誤提示），並依所選國碼提示號碼長度上限。〔src/pages/users/auth/parts/forget/Account.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 grep -n 'EmailVerify\\|verifyEmail\\|emailLogin' master -- src/pages/users/auth/parts/forget/Account.vue", 'result': "0 matches — 這個元件裡沒有任何 Email 驗證路徑（原本引用 `git grep -c 'email'` 命中 5，但那 5 筆其實是 showEmailHint／email_hint 這個「找回後顯示 Email 提示」的功能，不是「用 Email 驗證身分」的替代路徑，用字面 'email' 計數會誤判）", 'control_term': "git -C jgb2/dev2 grep -c 'phoneValidator' master -- src/pages/users/auth/parts/forget/Account.vue => 14（正對照組：手機驗證的呼叫確實大量存在於同一檔案）"}`

### 忘記密碼怎麼辦？（Email 或手機任一驗證後即可重設新密碼）
- 講法：忘記密碼怎麼辦／重設密碼／密碼忘記了
- 給誰看：property_manager
- 重設密碼前必須先完成帳號驗證，可以選擇用 Email 或手機號碼兩種方式其中之一收驗證碼。〔src/pages/users/auth/parts/forget/Password.vue〕
- 驗證碼確認正確後，畫面會顯示「帳號驗證成功」並切換到重設密碼表單。〔src/pages/users/auth/parts/forget/Password.vue〕
- 新密碼的格式限制與註冊時相同：至少 6 個字元、需同時包含英文與數字，且需與確認密碼欄位一致。〔src/pages/users/auth/parts/forget/Password.vue〕
- 送出並顯示密碼設定成功後，系統會依處理結果自動導向指定頁面或一般登入頁，需使用新密碼重新登入。〔src/pages/users/auth/parts/forget/Password.vue〕
- 如果密碼設定失敗，畫面會用瀏覽器內建的提示視窗顯示「密碼設定失敗」以及失敗原因，不是用頁面上一般的錯誤提示樣式呈現。〔src/pages/users/auth/parts/forget/Password.vue〕

### 「請設定密碼」畫面是什麼情境？（受邀請帳號的初次設定密碼流程）
- 講法：請設定密碼是什麼／被邀請要設密碼／被邀請設定密碼的頁面
- 給誰看：property_manager
- 當使用者是透過特定邀請連結進入忘記密碼頁面時，畫面會直接顯示「請設定密碼」，而不是一般的忘記密碼流程，並跳過帳號驗證直接進入設定密碼表單。〔src/pages/users/auth/parts/forget/Password.vue〕
- 此情境是搭配受邀請設定密碼的帳號（例如被交由他人代管的大房東子帳號），透過瀏覽器暫存的識別碼與委託連結建立密碼，設定成功後那組暫存資料會被清除，並依處理結果導向對應頁面。〔src/pages/users/auth/parts/forget/Password.vue〕
- 此畫面沿用一般忘記密碼頁面同樣的新密碼格式規則，設定成功後會依處理結果導向指定頁面，沒有指定頁面時才導回一般登入頁。〔src/pages/users/auth/parts/forget/Password.vue〕
- ⚠️ 待查：被邀請設定密碼連結的實際發送情境（哪個功能觸發大房東子帳號設密碼）未在本頁程式中找到來源，僅能確認前端行為，待業主補充或於後續盤查（大房東相關粗目）核對

## 會員中心首頁（7 條；頁：users.index、users.dashboard）

### 會員中心首頁有哪些統計區塊？（即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單）
- 講法：首頁看得到什麼／會員中心首頁／會員中心首頁有什麼統計資料／登入後的首頁
- 給誰看：property_manager
- 一般房東/管理者登入後的首頁上方會並排四個統計區塊：即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單。〔src/pages/users/dashboard/Landlord.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -c "空置房源" master -- src', 'result': '0 — 程式裡沒有「空置房源」這個字樣', 'control_term': 'git -C jgb2/dev2 grep -n "即時物件出租率" master -- src => 1（正對照組：Block_Vacancy.vue 裡實際顯示的文字是「即時物件出租率」）'}`

### 首頁的圖表看得到什麼？（招租／買賣廣告刊登率圓環圖、收支情況圖）
- 講法：首頁圖表／刊登率圓環圖／收支情況圖表
- 給誰看：property_manager
- 首頁提供「招租廣告刊登率／買賣廣告刊登率」圓環圖，顯示刊登中、未刊登、總件數。〔src/pages/users/dashboard/parts/RatioDoughnutChart.vue〕
- 首頁另外提供「收支情況」圖，顯示收入、支出、當日結餘、累計結餘。〔src/pages/users/dashboard/parts/BalanceChart.vue〕

### 首頁下方還有哪些列表？（帳單、合約、修繕整合列表，具通知權限者另有 Email 通知紀錄）
- 講法：首頁下方列表／帳單合約修繕整合列表／Email 通知紀錄區塊
- 給誰看：property_manager
- 首頁下方顯示帳單、合約、修繕的整合列表；具備通知檢視權限的使用者，還會另外看到 Email 通知紀錄區塊。〔src/pages/users/dashboard/Landlord.vue〕

### 大房東的首頁畫面和一般房東不一樣嗎？（只顯示物件/社區最新收支詳情與收支圖表，沒有捷徑與四個統計方塊）
- 講法：大房東首頁／大房東看到的畫面／大房東首頁跟一般房東有什麼不同
- 給誰看：property_manager
- 若目前登入身分是大房東，首頁不會顯示即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單四個方塊，也不會有捷徑區塊。〔src/pages/users/dashboard/Landlord.vue〕
- 大房東首頁改為顯示「物件最新收支詳情」（若身分是社區則顯示「社區最新收支詳情」），以及可自訂區間（7天／30天／90天／6個月）的收支圖表。〔src/pages/users/dashboard/Landlord.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/dashboard/Landlord.vue | sed -n '129,163p' | grep -c 'ShortCuts\\|Block_Vacancy'", 'result': '0 — 大房東分支（isBigLandlord 為真時渲染的區塊，第 129-163 行）裡完全沒有 ShortCuts 或 Block_Vacancy', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/dashboard/Landlord.vue | sed -n '163,209p' | grep -c 'ShortCuts\\|Block_Vacancy' => 2（正對照組：一般房東分支，第 163-209 行，兩者都存在）"}`
- ⚠️ 待查：幫助中心文件 Landlordonboarding00 描述大房東首頁有 7 個區塊，但目前程式碼（src/pages/users/dashboard/Landlord.vue 第 129-162 行）在大房東分支只渲染 EstateDetails 與 BalanceChart 兩個元件——文件與程式碼有落差，本細目依程式碼為準記錄事實，何者才是正確版本待業主裁決，不在此代為選邊。

### 怎麼在會員中心首頁切換團隊？（左上角下拉選單選擇被加入的團隊）
- 講法：怎麼切換團隊／被加入多個團隊／團隊下拉選單在哪
- 給誰看：property_manager
- 登入後若已被管理業者加入團隊，可從畫面左上角的下拉選單選擇要檢視的團隊。〔幫助中心:Landlordonboarding00_zh-Hant.html〕
- 選擇團隊後，畫面即顯示該團隊所屬的物件、合約、帳務與修繕資訊。〔幫助中心:Landlordonboarding00_zh-Hant.html〕
- 手機版與電腦版是同一套系統、同一組功能，畫面只依螢幕寬度調整排列方式，功能不會因裝置而減少。〔幫助中心:Landlordonboarding00phone_zh-Hant.html〕

### 首頁的「滿租率(beta)」頁簽是什麼？（限定開放的社區收入統計，非所有團隊都看得到）
- 講法：滿租率 beta／首頁頁簽／社區收入統計
- 給誰看：property_manager
- 首頁除了「主要」頁簽外，只有被列入特定開放名單的團隊，才會多顯示「滿租率(beta)」頁簽。〔src/pages/users/dashboard/Landlord.vue〕
- 切換到滿租率頁簽會改顯示社區收入統計圖表，取代原本的統計方塊與收支圖表區塊。〔src/pages/users/dashboard/Landlord.vue〕
- 切換頁簽時，網址會記錄目前所在的頁簽，之後可以用該網址直接分享或加入書籤停留在該頁簽。〔src/pages/users/dashboard/Landlord.vue〕

### 首頁「捷徑」區塊有哪些功能？（新增物件、新增合約、新增帳單、新增修繕、查看統計報表、查看大房東列表）
- 講法：捷徑區塊有哪些功能／首頁捷徑按鈕
- 給誰看：property_manager
- 「捷徑」區塊列出常用的快速入口，包含新增物件、新增合約、新增帳單、新增修繕、查看統計報表、查看大房東列表。〔src/pages/users/dashboard/parts/ShortCuts.vue〕
- 首頁「捷徑」區塊只有符合特定操作權限（例如新增物件、新增合約、新增帳單、編輯屋主修繕、帳單圖表、屋主帳單圖表、顯示大房東其中之一）的使用者才會看到。〔src/pages/users/dashboard/Landlord.vue〕

## 帳號資訊（10 條；頁：web:users.account）

### 帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂）
- 講法：帳號基本資訊怎麼改／改姓名／改大頭照／帳號資訊頁面
- 給誰看：property_manager
- 帳號資訊頁的「帳號基本資訊」區塊可以上傳／更換大頭照（選填），並編輯姓氏、名稱、稱謂。〔resources/views/users/account.blade.php〕
- 頁面說明這些資料是為了讓刊登廣告時租客有更安心的租屋體驗而蒐集的。〔resources/views/users/account.blade.php〕
- 若帳號的基本資訊被鎖定（例如合約雙方完成簽署後，系統會自動鎖定租客的基本資訊），姓氏、名稱、稱謂三個欄位就不會再被更新，即使表單有送出新值。〔app/Http/Controllers/UserController.php〕

### 帳號資訊頁怎麼看手機的綁定狀態？（已綁定／未綁定，未綁定才有「前往綁定」按鈕）
- 講法：手機有沒有綁定／手機綁定狀態／前往綁定按鈕
- 給誰看：property_manager
- 帳號資訊頁的「帳號資訊」區塊會顯示手機號碼目前是「已綁定」或「未綁定」，未綁定時提供「前往綁定」按鈕導向手機驗證頁。〔resources/views/users/account.blade.php〕

### 帳號資訊頁的 Email 驗證狀態怎麼看？（Email 無法自行更改，需聯繫客服）
- 講法：email 驗證狀態／怎麼換 email／更換綁定信箱
- 給誰看：property_manager
- 同區塊也會顯示 Email 驗證狀態：一般帳號會顯示「已驗證」或「未驗證」；只有特定合作單位的帳號，才會顯示「未完成驗證」或「未設定」。〔resources/views/users/account.blade.php〕
- 一般帳號的 Email 欄位是鎖定唯讀的，頁面提示如需更換 Email 帳號，需要聯繫 JGB 客服處理，不能在此頁直接自行修改。〔resources/views/users/account.blade.php〕

### 手機已經綁定後可以自己更換嗎？（沒有更換入口，只顯示已綁定狀態）
- 講法：換手機號碼／更換綁定手機／手機已綁定還能改嗎
- 給誰看：property_manager
- 帳號資訊頁的手機欄位一旦顯示「已綁定」，就不會再出現「前往綁定」或其他可以修改號碼的按鈕。〔resources/views/users/account.blade.php〕
- 手機驗證流程如果偵測到目前帳號已經綁定過手機，會直接顯示「手機已綁定」畫面，並提示未來可以用這支電話號碼登入，接下來只有「繼續」按鈕，沒有換一支手機重新綁定的選項。〔src/pages/users/auth/parts/PhoneVerify.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -c "換手機\\|更換手機" master -- resources/views/users/account.blade.php src/pages/users/auth/parts/PhoneVerify.vue', 'result': '0 — 這兩個檔案裡都沒有「換手機」或「更換手機」的更換入口文字', 'control_term': 'git -C jgb2/dev2 grep -c "前往綁定" master -- resources/views/users/account.blade.php => 1（正對照組：同檔案裡確實有「前往綁定」這個真實存在、會顯示的按鈕文字，只是只在未綁定時出現）'}`

### 帳號資訊頁怎麼看 SSO 綁定狀態？（Facebook／Google／LINE 各自顯示已綁定或未綁定）
- 講法：sso 綁定狀態／有沒有連 facebook／帳號有沒有連 google
- 給誰看：property_manager
- 帳號資訊頁「SSO 綁定狀態」區塊會分別列出 Facebook、Google、LINE 三個第三方帳號各自的綁定狀態（已綁定或未綁定）。〔resources/views/users/account.blade.php〕
- 頁面本身沒有提供解除 SSO 綁定的按鈕或連結，只顯示 Facebook、Google、LINE 三個平台各自的綁定狀態。〔resources/views/users/account.blade.php〕
- 「修改密碼」區塊只有在該帳號已經設有密碼時才會顯示；如果帳號是純粹用第三方帳號註冊、從未設定過密碼，此區塊會被隱藏。〔app/Http/Controllers/UserController.php〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:resources/views/users/account.blade.php | sed -n '222,251p' | grep -ic '解除\\|unbind\\|unlink'", 'result': '0 — SSO 綁定狀態區塊（第 222-251 行）裡沒有任何解除／unbind／unlink 相關的按鈕或文字', 'control_term': "git -C jgb2/dev2 grep -c '前往綁定' master -- resources/views/users/account.blade.php => 1（正對照組：同一頁面手機欄位確實有「前往綁定」這種操作型連結，證明本頁不是完全沒有可操作連結，只是 SSO 區塊剛好沒有解除功能）"}`

### 登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼，新密碼規則同註冊）
- 講法：登入後怎麼改密碼／帳號資訊改密碼／修改密碼要輸入原密碼嗎
- 給誰看：property_manager
- 帳號資訊頁點選「修改密碼」會展開密碼修改表單。〔resources/views/users/account.blade.php〕
- 修改密碼必須同時填寫目前密碼、新密碼與確認新密碼；若目前密碼輸入錯誤，會回覆「目前密碼驗證錯誤」並擋下整筆表單儲存。〔app/Http/Controllers/UserController.php〕
- 新密碼長度需至少 6 個字元，且需與確認新密碼欄位一致，這與註冊時的密碼規則一致。〔app/Http/Controllers/UserController.php〕
- 同一使用者名下若有以此帳號代管的子帳號（例如受託的大房東子帳號），密碼變更會一併同步更新到這些子帳號。〔app/Http/Controllers/UserController.php〕
- 「密碼」區塊下方會顯示「上次更新：」的日期時間；如果從來沒有改過密碼，則顯示帳號建立的時間。〔app/Http/Controllers/UserController.php〕
- ⚠️ 待查：驗證規則 'password' => 'min:6|...' 允許剛好 6 個字元，但對應的錯誤訊息文案寫「密碼必須超過6個字元」（字面上是要求超過 6 碼、也就是至少 7 碼）；規則與文案不一致，何者為準待業主裁決。

### 帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話）
- 講法：聯絡資訊怎麼填／WhatsApp 要填什麼／line id 要填嗎／第二組電話用途
- 給誰看：property_manager
- 「聯絡資訊」區塊會呈現在刊登的廣告上，讓租客有更多管道聯繫房東。〔resources/views/users/account.blade.php〕
- LINE 欄位可勾選「同手機號碼」，勾選後不需另外輸入 LINE ID；未勾選則需填寫 LINE ID。〔resources/views/users/account.blade.php〕
- Facebook 欄位填寫的是個人首頁連結，欄位長度上限 200 字元。〔resources/views/users/account.blade.php〕
- WhatsApp 欄位旁有提示：請填寫國碼與電話號碼、國碼前面不需打「+」，欄位長度上限 200 字元。〔resources/views/users/account.blade.php〕
- 第二組聯絡號碼欄位限填純數字，長度上限 50 字元；畫面上目前沒有「以此電話作為廣告頁聯絡電話」這個核取方塊可以勾選。〔resources/views/users/account.blade.php〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -n "以此電話作為廣告頁聯絡電話" master -- resources/views/users/account.blade.php', 'result': '1 個命中，該行前後被 {{-- ... --}} 包住（第 328-334 行是同一段 Blade 註解），這個核取方塊不會顯示給使用者', 'control_term': 'git -C jgb2/dev2 grep -n "第二組聯絡號碼" master -- resources/views/users/account.blade.php => 命中在註解區塊外，是真的會渲染的欄位標籤（正對照組：同一個區塊裡確實存在沒被註解掉、會顯示的欄位）'}`

### 帳號資訊頁的偏好設定能設定什麼？（登入預設房東身份、時區、Email 通知語系）
- 講法：登入預設身份怎麼設／時區設定在哪／Email 通知語言
- 給誰看：property_manager
- 「偏好設定」可以指定「登入預設房東身份」，決定同帳號有多個房東身份時預設要進入哪一個。〔resources/views/users/account.blade.php〕
- 可選擇非台灣時區，選擇後系統會將排程通知（例如每日過期帳單通知、合約 30 天內到期提醒）的發送時間改用所選時區計算。〔resources/views/users/account.blade.php〕
- 可設定「Email 通知語系」，決定收到系統通知信時使用哪種語言。〔resources/views/users/account.blade.php〕

### 帳號資訊頁有「資訊完整度」進度條嗎？（目前頁面上不會顯示這個區塊）
- 講法：資訊完整度是什麼／為什麼不能刊登廣告／為什麼不能簽約
- 給誰看：property_manager、prospect
- 帳號資訊頁目前不會顯示「會員狀態」卡片與「資訊完整度」進度條，這個區塊目前對使用者是關閉的。〔resources/views/users/account.blade.php〕
- 「簽約資訊」是一個獨立於帳號資訊頁的頁面，用來填寫簽約所需的身份資料（如身分證字號、戶籍地址等），不是本頁「帳號基本資訊」的欄位。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -n "config_rule_type == \'landlord\'" master -- resources/views/users/account.blade.php', 'result': "1 個命中：`@if (false && $role->config_rule_type == 'landlord')`，條件寫死 false，這個區塊（含會員狀態卡片與資訊完整度進度條）永遠不會渲染", 'control_term': 'git -C jgb2/dev2 grep -n "___(\'帳號基本資訊\')" master -- resources/views/users/account.blade.php => 命中在第 101 行，不在任何條件為 false 的區塊裡，確實會渲染（正對照組：同檔案裡真正會顯示的區塊）'}`
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -c "infoIdentity" master -- resources/views/users/account.blade.php', 'result': '18 個命中；其中第 2 行落在檔案最上方 `{{-- @php dd($infoIdentity); @endphp --}}` 這段 Blade 註解裡，跟第 349–725 行 `<?php /* ... */ ?>` 的死區塊是兩段不同的註解；其餘 17 個命中全部落在第 349–725 行的死區塊內', 'control_term': 'git -C jgb2/dev2 grep -n "___(\'帳號基本資訊\')" master -- resources/views/users/account.blade.php => 命中在第 101 行，在這兩段註解範圍之外，確實會渲染（正對照組）'}`
- ⚠️ 待查：UserController（account 方法）的顯示資料裡定義了『資訊完整度』兩階段：第一階段（1/2 基本資訊）標示解鎖「刊登廣告」，第二階段（2/2 身份資訊）標示解鎖「簽立合約」與「開通線上智能整合收款」；但對應的畫面卡片整段被 `@if (false && ...)` 關閉、不會顯示給使用者，本次盤查也沒有在別處找到真的依這兩個階段擋下刊登廣告／簽約／開通收款的判斷式。這兩階段目前是否仍是實際生效的規則（只是進度條沒顯示），或整個機制已經廢棄，待業主或後續盤查確認。

### 帳號資訊頁儲存失敗會提示什麼？（頁面沒有完整載入時會提醒重新整理再儲存）
- 講法：儲存失敗提示／帳號資訊存不進去
- 給誰看：property_manager
- 如果送出儲存時，系統偵測到頁面沒有完整載入（缺少應該要有的欄位），會擋下這次儲存，並提示「頁面沒有完整載入，這次的資料沒有儲存，請重新整理頁面後再儲存一次」。〔app/Http/Controllers/UserController.php〕

## 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章）（8 條；頁：users.signer_info、web:users.roleTenant）

### 個人房東的簽約資訊要填什麼？（姓氏、名稱、身分證字號、Email、手機、身分證正反面）
- 講法：個人房東簽約資訊／簽約要填身分證嗎／簽約資訊個人欄位
- 給誰看：property_manager、prospect
- 個人身分的簽約資訊必填欄位為姓氏、名稱、身分證字號。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 另需填寫 Email 與手機號碼，同樣列為必填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 身分證正反面照片為附件上傳項目，走證件引導裁切流程。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 另可上傳「工作名片/學生證」「良民證」「小章」三項其他附件，皆非必填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 如果有多筆個人身分資料（例如同時管理多個角色），表單上方會出現一列可以切換的項目；超過 5 筆時，會多一個「所有團隊」的下拉選單方便切換，並不是變成側邊清單或捲動列。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '202,221p' | grep -c isRequired", 'result': '0 — otherAttachmentInfo 這三個附件（工作名片/學生證、良民證、小章）欄位定義裡完全沒有 isRequired', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '115,149p' | grep -c 'isRequired: true' => 3（正對照組：同檔案的必填欄位姓氏/名稱/身分證字號確實都寫了 isRequired: true）"}`

### 公司身分的簽約資訊要填什麼？（公司名稱、統編、負責人、公司電話/Email、登記證資料）
- 講法：公司簽約資訊／統編怎麼填／公司負責人要填嗎
- 給誰看：property_manager、prospect
- 公司/團隊身分的簽約資訊必填項目為公司登記名稱（上限 20 字）與公司統編、公司電話、公司 Email。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 統編欄位可選擇類型：「公司統編(檢核)」會用台灣統編檢查碼規則驗證格式，長度上限 8 碼；選「其他統編(不檢核)」則不驗證，長度上限放寬到 20 碼。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 公司登記證號、登記證日期、公司登記證縣市為選填欄位；若身分是社宅團隊，公司登記證號則改為必填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「公司負責人」是公司團隊都會顯示的欄位；「社宅業者編號」只有社宅團隊才會顯示並填寫，一般公司團隊看不到這個欄位。〔src/pages/users/team/_parts/SignerDetails.vue〕

### 公司身分要上傳哪些印章與證件附件？（公司大章、小章、經紀人章、經紀業章、租賃管理員章）
- 講法：公司大小章上傳／經紀人章要傳嗎／簽約印章附件
- 給誰看：property_manager、prospect
- 公司身分的簽約資訊固定要上傳五種印章附件：公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章；這五個欄位並沒有依身分或資格才顯示的條件，一律都會出現在頁面上。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 除了這五種印章之外，還有一個獨立的「電子簽約圖章」欄位（畫面上顯示為「圖章」），用來啟用「預設使用圖章取代親手簽名」的簽約方式，走另一組上傳流程。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '509,536p' | grep -c isFieldVisible", 'result': '0 — corpAttachmentInfo（五個印章欄位定義，第 509-536 行）裡沒有任何 isFieldVisible 或 isRequired 條件', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '224,300p' | grep -c isFieldVisible => 有命中（正對照組：同檔案公司基本欄位確實有依條件顯示/隱藏的欄位，證明「沒有條件」是印章欄位特有的，不是我漏抓）"}`

### 有不動產經紀人／租賃管理人員資格要多填什麼？（經紀人證號、租賃管理人員證號等）
- 講法：經紀人證號要填嗎／租賃管理人員資訊／經紀業名稱
- 給誰看：property_manager、prospect
- 公司簽約資訊可填寫經紀人名稱（上限 15 字）與經紀人證號、經紀業名稱（上限 15 字）與經紀業證號。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 也可填寫租賃管理人員名稱與租賃管理人員證號；租賃管理人員目前沒有對應的 Email 欄位，只有經紀人才有經紀人 Email 欄位。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 若身分為社宅團隊，經紀人名稱、經紀人證號、租賃管理人員名稱、租賃管理人員證號皆會變為必填欄位，並且會多顯示經紀人的聯絡電話與 Email、以及租賃管理人員的聯絡電話；一般公司團隊這些欄位皆為選填或不顯示。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 grep -c leasing_manager_email master -- src/pages/users/team/_parts/SignerDetails.vue', 'result': '0 — 沒有租賃管理人員 Email 欄位', 'control_term': 'git -C jgb2/dev2 grep -n broker_email master -- src/pages/users/team/_parts/SignerDetails.vue => 2 個命中（正對照組：經紀人確實有對應的 Email 欄位，證明是「租賃管理人員缺這個欄位」而不是整組都沒有）'}`

### 簽約資訊誰能編輯？（沒有編輯權限的欄位會顯示為停用樣式）
- 講法：誰能改簽約資訊／沒有編輯權限會怎樣／簽約資訊唯讀
- 給誰看：property_manager
- 「簽約資訊」頁面本身固定以可編輯模式載入。〔src/pages/users/signerInfo/Index.vue〕
- 公司身分的各欄位元件都能各自被設成不可編輯，此時公司登記名稱、統編、負責人等欄位會顯示為停用樣式。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 個人身分的欄位元件目前沒有這種可設為不可編輯的樣式切換，固定顯示為一般可編輯樣式；只有公司身分的欄位會依此顯示停用樣式。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '115,175p' | grep -c isAllowedToEdit", 'result': '0 — 個人身分欄位定義（firstRowOfIndividualInfo／secondRowOfIndividualInfo，第 115-175 行）完全沒有引用 isAllowedToEdit', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/team/_parts/SignerDetails.vue | sed -n '224,300p' | grep -c isAllowedToEdit => 4（正對照組：同檔案公司欄位確實有引用，證明不是我漏抓關鍵字）"}`
- ⚠️ 待查：「團隊資訊」頁（可能傳入 isAllowedToEdit 為 false 的呼叫端）不在本粗目頁面範圍內，本細目僅描述元件本身支援唯讀模式，實際哪些角色會被設為不可編輯需另外於團隊/人員相關粗目查證

### 簽約資訊的地址欄位怎麼填？（戶籍/通訊地址、公司登記/通訊地址皆為必填，可一鍵「同上」）
- 講法：戶籍地址要填嗎／通訊地址可以跟戶籍一樣嗎／公司登記地址
- 給誰看：property_manager、prospect
- 個人身分需填寫「戶籍地址」與「通訊地址」，兩者皆為必填。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 通訊地址欄位旁提供「同戶籍地址」按鈕，點擊後會直接把戶籍地址的內容複製到通訊地址。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 公司身分則對應填寫「公司登記地址」與「公司通訊地址」，同樣皆為必填，並提供「同公司登記地址」快速複製按鈕。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 只有社宅團隊，才會額外顯示經紀人通訊地址與租賃管理人員通訊地址兩個獨立欄位；非社宅團隊即使有經紀人或租賃管理人員資格，也不會顯示這兩個地址欄位。〔src/pages/users/team/_parts/SignerDetails.vue〕

### 公司名下有多筆簽約對象時要怎麼切換？（表單上方出現切換列，超過 5 筆再加「所有團隊」下拉選單）
- 講法：公司多筆簽約對象切換／多個公司要怎麼切換
- 給誰看：property_manager
- 如果目前團隊底下有多筆公司簽約對象資料，簽約資訊表單上方會出現一列可以切換的項目，點選就能切到不同的對象。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 超過 5 筆公司簽約對象時，會多一個「所有團隊」的下拉選單，方便直接選擇要編輯的對象，而不是逐一點選切換列。〔src/pages/users/team/_parts/SignerDetails.vue〕

### 簽約資訊頁的「管理」「儲存」按鈕做什麼？（管理開啟簽約對象管理視窗，儲存只在個人身分頁面出現）
- 講法：簽約資訊管理按鈕／簽約資訊儲存按鈕
- 給誰看：property_manager
- 「管理」按鈕會開啟一個管理簽約對象的視窗，用來新增、編輯或選擇要簽約的對象。〔src/pages/users/team/_parts/SignerDetails.vue〕
- 「儲存」按鈕只有在個人身分、且位於「簽約資訊」這個獨立頁面時才會出現，用來單獨儲存目前這筆個人簽約資料。〔src/pages/users/team/_parts/SignerDetails.vue〕

## 通知中心（7 條；頁：web:notifications.index）

### 通知中心怎麼依類型篩選通知？（依合約/帳務/修繕/裝置/其他分類）
- 講法：通知中心怎麼篩選／通知中心的通知類型有哪些／怎麼看合約類通知
- 給誰看：property_manager
- 通知中心提供依類型篩選的下拉選單，選項為全部、合約、帳務、修繕、裝置、其他。〔app/Http/Controllers/NotificationController.php〕

### 通知中心的通知怎麼標示未讀？（列表項目左側的紅點，沒有「只顯示未讀」的篩選功能）
- 講法：只看未讀通知／通知未讀紅點
- 給誰看：property_manager
- 通知列表中，尚未讀取的通知，項目左側會有一個小紅點做提示。〔resources/views/notifications/index.blade.php〕
- 頁面目前沒有「只顯示未讀」這種篩選核取方塊，無法只篩選未讀通知。〔resources/views/notifications/index.blade.php〕
- 否定查證：`{'grep': "git -C jgb2/dev2 grep -n 'checkbox-unread' master -- resources/views/notifications/index.blade.php", 'result': '1 個命中，該行（<input type="checkbox" id="checkbox-unread" /> ...）前一行是 <!-- 、後一行是 -->，整段是 HTML 註解，瀏覽器不會渲染', 'control_term': "git -C jgb2/dev2 grep -n 'per_page' master -- resources/views/notifications/index.blade.php => 命中在註解區塊外，是真的會渲染、也真的能操作的每頁筆數選單（正對照組：同檔案裡確實存在沒被註解掉、能正常運作的篩選功能）"}`

### 通知中心每頁顯示筆數可以怎麼調整？（30/60/90 筆，預設 30 筆）
- 講法：通知每頁幾筆／通知中心分頁
- 給誰看：property_manager
- 每頁顯示筆數可切換 30 項、60 項或 90 項，預設為 30 項。〔app/Http/Controllers/NotificationController.php〕

### 為什麼通知中心是空的？（房東側需要查看通知的權限才看得到通知內容）
- 講法：通知中心是空的／為什麼看不到通知／通知權限
- 給誰看：property_manager
- 租客身分一律能看到自己的通知內容。〔app/Http/Controllers/NotificationController.php〕
- 房東側（非租客）使用者，只有具備查看通知的權限，通知中心才會顯示實際通知資料。〔app/Http/Controllers/NotificationController.php〕
- 沒有這項權限時，類型篩選下拉選單仍會顯示，但會變成停用樣式；每頁筆數選單則完全不會出現；畫面主要區塊會顯示「您還沒有收到任何通知，再等等吧 📭」，而不是錯誤訊息。〔resources/views/notifications/index.blade.php〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:app/Http/Controllers/NotificationController.php | sed -n '37,55p' | grep -c 'pageNav = get_paginate'", 'result': '0 — $pageNav 在函式一開始被設為 null（第 37 行），權限判斷之前不會被賦值', 'control_term': "git -C jgb2/dev2 show master:app/Http/Controllers/NotificationController.php | sed -n '56,115p' | grep -c 'pageNav = get_paginate' => 1（正對照組：$pageNav 只有在權限判斷通過、進入該 if 區塊後才會被賦值，沒有權限時就維持 null，畫面的 @if (!empty($pageNav)) 因此不會渲染）"}`

### 點擊通知列表項目會發生什麼？（前往原連結，並帶上標記已讀的依據）
- 講法：點通知會怎樣／通知會標記已讀嗎／通知連結
- 給誰看：property_manager
- 每則通知點擊後，會依原本的連結網址前往對應頁面，並在網址上加一個參數，作為之後判斷這則通知已經處理過的依據。〔app/Http/Controllers/NotificationController.php〕
- 每則通知會顯示所屬物件名稱、通知來源使用者姓名、通知內容文字，以及依通知類型著色的標籤（如合約、帳務、修繕、裝置、其他、訊息）。〔resources/views/notifications/index.blade.php〕

### 篩選後頁碼超出範圍會自動跳回第一頁嗎？（寫了判斷式，但實際上永遠不會被觸發）
- 講法：通知頁碼超出範圍／篩選後跳到空白頁
- 給誰看：property_manager
- 篩選通知後如果頁碼超出範圍，畫面不會自動跳回第一頁，只會顯示空的通知清單。〔app/Http/Controllers/NotificationController.php〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:app/Http/Controllers/NotificationController.php | sed -n '107,116p'", 'result': "$datas 在這裡被賦值成 Laravel 的 LengthAwarePaginator 物件（->paginate() 的回傳值），不是陣列；PHP 的 empty() 對非 null 的物件恆回傳 false，因此 if (empty($datas) && request('page') > 1) 這個條件永遠不會成立，導回邏輯是死碼", 'control_term': '同檔案第 37 行 $datas = []; 才是陣列初始值——empty() 對陣列跟對物件的行為不同，這不是我瞎猜的行為推測，而是同一份程式碼裡本身混用了兩種型別的對照'}`

### 導覽列的通知鈴鐺會顯示什麼？（最近 5 筆通知與未點擊數量，大房東不會顯示）
- 講法：導覽列通知鈴鐺／鈴鐺數字是什麼／紅點跟鈴鐺數字差別
- 給誰看：property_manager
- 導覽列鈴鐺點開後只會列出最近 5 筆通知，跟通知中心的完整列表不同。〔app/Http/Controllers/NotificationController.php〕
- 鈴鐺上顯示的數字，是使用者「還沒點擊過」的通知數量；這跟通知列表項目旁的紅點（未讀）是兩個獨立的狀態，分別依據不同的欄位判斷。〔app/Http/Controllers/NotificationController.php〕
- 跟通知中心一樣，只有租客身分或具備查看通知權限的房東側使用者才會取得通知資料；如果目前是大房東身分，即使有這項權限，鈴鐺也不會顯示通知資料。〔app/Http/Controllers/NotificationController.php〕

## 通知收件設定與發送報表（通知收件信箱最多再加 3 組）（4 條；頁：users.notification）

### 通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱）
- 講法：通知收件信箱最多幾組／怎麼加通知信箱／額外通知信箱
- 給誰看：property_manager
- 「通知收件設定」頁面說明每個通知信分類最多可再新增 3 組電子信箱收取通知信件。〔src/pages/users/notification/Index.vue〕
- 預設信箱欄位固定顯示帳號本身的 Email，此欄位鎖定無法編輯。〔src/pages/users/notification/Index.vue〕
- 每個通知分類卡片內都可各自新增/移除最多 3 組自訂收件信箱，每組都是標準 Email 格式輸入框且為必填，彼此分類互不共用額度。〔src/pages/users/notification/Index.vue〕
- 需要具備通知設定的編輯權限，才能新增信箱、儲存表單；沒有這個權限時，「新增信箱」與「儲存」按鈕會直接消失，但每組信箱旁的移除（×）按鈕仍會顯示，只是變成無法點擊的停用樣式。〔src/pages/users/notification/Index.vue〕
- 否定查證：`{'grep': "git -C jgb2/dev2 show master:src/pages/users/notification/Index.vue | sed -n '243,267p' | grep -c 'v-if.*hasPermissionToEdit'", 'result': '0 — 移除（×）按鈕所在的區塊沒有用 hasPermissionToEdit 包住，一定會渲染', 'control_term': "git -C jgb2/dev2 show master:src/pages/users/notification/Index.vue | sed -n '268,279p' | grep -c 'v-if.*hasPermissionToEdit' => 1（正對照組：「新增信箱」按鈕的區塊確實用 v-if 包住 hasPermissionToEdit，沒有權限時整塊不會渲染，跟移除按鈕的「渲染但停用」是不同做法）"}`

### 通知收件設定有哪些分類？（合約、帳務、修繕、訂閱、房東管理，另有限定開放的加盟分潤報表）
- 講法：通知收件設定的分類有哪些／帳務通知包含什麼／訂閱通知是什麼
- 給誰看：property_manager
- 「合約管理類別」包含租客簽名、合約成立、提前解約等通知信。〔src/use/config/useForwardNotificationEmails.ts〕
- 「帳務管理類別」包含帳單已到帳、租客已匯款、金額不匹配等通知信。〔src/use/config/useForwardNotificationEmails.ts〕
- 「修繕管理類別」包含租客提出修繕、修改修繕備註等通知信。〔src/use/config/useForwardNotificationEmails.ts〕
- 「訂閱管理類別」包含訂閱方案修改、即將扣款、取消訂閱等通知信。〔src/use/config/useForwardNotificationEmails.ts〕
- 「房東管理類別」包含大房東報表排定發送等通知信。〔src/use/config/useForwardNotificationEmails.ts〕
- 「加盟分潤報表」類別只有被列入特定開放名單的團隊才會顯示，若想讓新團隊加入分潤報表需另外聯繫 JGB。〔src/use/config/useForwardNotificationEmails.ts〕

### 「發送報表」「多團隊合併報表」按鈕是做什麼的？（限加盟分潤報表分類，多團隊合併僅限特定團隊）
- 講法：發送報表按鈕／多團隊合併報表／分潤報表怎麼看
- 給誰看：property_manager
- 只有「加盟分潤報表」分類會顯示「發送報表」按鈕，點擊會開啟通知信報表的燈箱視窗。〔src/use/config/useForwardNotificationEmails.ts〕
- 「多團隊合併報表」按鈕只在限定的特定樓宇團隊底下才會顯示，其餘分類與團隊都看不到這個按鈕。〔src/use/config/useForwardNotificationEmails.ts〕
- 點擊「發送報表」或「多團隊合併報表」按鈕時，會依目前所在的通知分類，開啟對應的報表視窗。〔src/pages/users/notification/Index.vue〕
- 否定查證：`{'grep': 'git -C jgb2/dev2 show master:src/use/config/useForwardNotificationEmails.ts | grep -c showMultiTeamReportButton', 'result': '只有 franchiseProfitShare 這一個分類定義了 showMultiTeamReportButton，其餘 5 個分類都沒有這個欄位（等同 false）', 'control_term': 'git -C jgb2/dev2 show master:src/use/config/useForwardNotificationEmails.ts | grep -c showMailReportButton => 10（正對照組：showMailReportButton 這個欄位每個分類都有寫，證明不是我漏抓，而是 showMultiTeamReportButton 真的只有一個分類有）'}`

### 通知收件設定改完怎麼儲存？（至少要有一個分類填了自訂信箱，儲存鍵才會啟用）
- 講法：通知設定怎麼存／儲存按鈕按不下去／沒填信箱能存嗎
- 給誰看：property_manager
- 「儲存」按鈕只有在至少一個分類已經填了自訂收件信箱時才會啟用，否則呈現停用樣式且送出動作不會執行。〔src/pages/users/notification/Index.vue〕
- 儲存成功會顯示「儲存成功」提示；若儲存失敗，畫面會用系統回傳的訊息或預設「儲存失敗，請稍後再試。」顯示錯誤提示；若發生網路錯誤則顯示「網路錯誤，請稍後再試。」〔src/pages/users/notification/Index.vue〕
- 頁面載入時會自動取得目前各分類的自訂信箱與預設信箱，按下「儲存」則會把整包分類資料送出更新。〔src/pages/users/notification/Index.vue〕
