# 審核單：Plan 9.17 S1 A／B／C 未審細目代理先審（223 條）

> 審閱的正本版本：commit `f03be3b0`。本單由 `scratchpad/p917_s1_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 155／doubt 68／未先審 0。
> 回覆方式（S2）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審。⛔ 標示「有未先審細目」的組不可整組回「過」。

## 註冊帳號（Email／SSO、驗證碼、手機綁定） `A-registration`（待審 12 條：pass 7／doubt 5／未先審 0） ⚠️

- [pass] `jgb/A/register-email-steps` 如何註冊 JGB 帳號？（Email、驗證碼、帳號設定三步驟）
- [pass] `jgb/A/register-tenant-contract-invitation` 租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「註冊」接續完成）
- [pass] `jgb/A/register-captcha-expired` 註冊卡在機器人驗證過期怎麼辦？（會退回第一步重新勾選）
- [pass] `jgb/A/register-email-verify-resend` 沒收到 Email 驗證碼怎麼辦？（可重發，發送次數過多會出現等待秒數）
- [pass] `jgb/A/register-password-rule` 註冊密碼格式要求是什麼？（至少 6 碼、須同時包含英文與數字）
- [pass] `jgb/A/register-phone-bind` 註冊要綁定手機號碼嗎？（可選填、簡訊驗證、可「下次再驗證」略過）
- [pass] `jgb/A/register-phone-already-bound` 註冊時發現手機已綁定過怎麼辦？（直接顯示已綁定、按繼續完成流程）
- [doubt] `jgb/A/register-sso` 可以用 Facebook、Google、LINE 註冊嗎？（SSO 仍需完成 Email 綁定） —— 句序 3：「系統會自動帶入對應的 Email」無源：SSO 回呼只導到 users.create?sso=1&social_type，不帶 Email；Create.vue 的 email 初始為空，沒有預填
- [doubt] `jgb/A/register-email-already-registered` 註冊時 Email 已被註冊過怎麼辦？（系統會將帳號合併） —— 句序 標題/1：同一 Email 已用 Email 註冊完成時，第一步就顯示「此帳號已註冊。」並擋下，不會合併；只有主帳號存在、還沒有 Email 帳號（例如先用 SSO 註冊）才會走合併
- [doubt] `jgb/A/register-role-select` 註冊完之後要選身分嗎？（房東/管理者、租客二選一，可同時擁有兩種身分） —— 句序 1/3：session 有 redirect_after_login 時，綁手機步驟（略過或驗證成功）直接跳轉，跳過選身分；SSO 已註冊帳號也直接進首頁。「都會出現」與「選擇身分後導回」和程式矛盾
- [doubt] `jgb/A/register-verify-code-shape` 驗證碼輸入畫面長什麼樣子？（識別碼加 4 碼數字，輸入錯誤太多次會被鎖住） —— 句序 標題/2：後端 AuthController 各驗證分支都不回傳 is_locked（在同一匯出 grep「is_locked」只有 Iot 相關檔案命中，當正對照），所以沒有任何流程會鎖輸入框；實際是回「驗證次數過多，驗證碼已失效，請稍候重發…」
- [doubt] `jgb/A/register-email-link-resume` 從驗證信連結折返時會從頭開始註冊嗎？（不會，系統會記住 Email 直接跳到輸入驗證碼畫面） —— 句序 標題/2：折返時會重打 sendVerEmail；session 內沒有這個 Email 的機器人驗證紀錄（或超過 1800 秒）就會回 recaptcha_required，前端清空 Email、退回第一步，程式註解明寫這情況「多半是從信件連結折返」

回覆：

## 登入 `A-login`（待審 11 條：pass 8／doubt 3／未先審 0）

- [pass] `jgb/A/login-methods` JGB 有哪些登入方式？（Email、手機號碼、Facebook／Google／LINE）
- [pass] `jgb/A/login-role-select-before` 登入前為什麼要先選擇身分？（決定進入房東/管理者或租客的登入表單）
- [pass] `jgb/A/login-phone-country-code` 用手機號碼登入時，國碼與號碼格式有什麼規則？（號碼長度上限與格式依所選國家而定）
- [pass] `jgb/A/login-remember-me` 「記住我」是做什麼？（只延長登入效期，跟記住登入方式無關）
- [pass] `jgb/A/login-error` 登入帳號或密碼錯誤時會顯示什麼？
- [pass] `jgb/A/login-forget-password-link` 登入頁的「忘記密碼？」連結在哪裡？（在登入表單下方，點擊前往忘記密碼流程）
- [pass] `jgb/A/login-forget-account-link` 登入頁的「忘記帳號？」連結在哪裡？（在登入表單下方，點擊前往忘記帳號流程）
- [pass] `jgb/A/login-identity-switch` 同一帳號同時有房東與租客身分時怎麼切換？（登入時重新選擇身分，或在帳號資訊設定預設身分）
- [doubt] `jgb/A/login-sso-redirect-no-duplicate-buttons` 從 Facebook／Google／LINE 導回登入頁時，第三方登入按鈕會重複出現嗎？（不會） —— 句序 標題/1：authSSO 回呼只導向註冊頁、首頁或 redirect_after_login，不會導回登入頁並帶 sso 參數，所以描述的情境無源
- [doubt] `jgb/A/login-role-redirect` 登入時身分選錯了怎麼辦？（會依選擇的身分決定進入哪個角色的登入表單） —— 句序 3：「元件共用同一份角色欄位」是實作詞；全條也沒回答「選錯怎麼辦」，登入表單沒有返回鈕
- [doubt] `jgb/A/login-no-account-register-link` 登入頁下面有連到註冊頁的連結嗎？（「還沒有帳號嗎？立即註冊」） —— 句序 標題：「立即註冊」在登入表單最上方（歡迎標題之下、帳號欄之前），不在「下面」；頁面最下方是忘記密碼？／忘記帳號？

回覆：

## 忘記帳號、忘記密碼 `A-account-recovery`（待審 4 條：pass 2／doubt 2／未先審 0） ⚠️

- [pass] `jgb/A/forget-account-flow` 忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示）
- [pass] `jgb/A/forget-account-no-phone` 沒綁手機號碼還能用「忘記帳號」找回嗎？（不行，只能靠手機簡訊驗證）
- [doubt] `jgb/A/forget-password-flow` 忘記密碼怎麼辦？（Email 或手機任一驗證後即可重設新密碼） —— 句序 3/5：重設密碼的後端 regex 限制字元範圍，和註冊規則不同，所以不能說「與註冊時相同」；後端回 field_errors 時密碼欄也會顯示「格式錯誤。」，不是只有 alert
- [doubt] `jgb/A/forget-password-setpwd-invite` 「請設定密碼」畫面是什麼情境？（受邀請帳號的初次設定密碼流程） —— 句序 2：「大房東子帳號」無源，程式是 BigLandlord 邀請流程；「暫存識別碼與委託連結」是在描述 cookie，屬實作詞

回覆：

## 會員中心首頁 `A-member-home`（待審 7 條：pass 6／doubt 1／未先審 0）

- [pass] `jgb/A/dashboard-overview-blocks` 會員中心首頁有哪些統計區塊？（即時物件出租率、即將到期合約、即將到來應到帳帳單、7日內修繕單）
- [pass] `jgb/A/dashboard-overview-charts` 首頁的圖表看得到什麼？（招租／買賣廣告刊登率圓環圖、收支情況圖）
- [pass] `jgb/A/dashboard-overview-lists` 首頁下方還有哪些列表？（帳單、合約、修繕整合列表，具通知權限者另有 Email 通知紀錄）
- [pass] `jgb/A/dashboard-team-switch` 怎麼在會員中心首頁切換團隊？（左上角下拉選單選擇被加入的團隊）
- [pass] `jgb/A/dashboard-occupancy-tab` 首頁的「滿租率(beta)」頁簽是什麼？（限定開放的社區收入統計，非所有團隊都看得到）
- [pass] `jgb/A/dashboard-shortcuts-list` 首頁「捷徑」區塊有哪些功能？（新增物件、新增合約、新增帳單、新增修繕、查看統計報表、查看大房東列表）
- [doubt] `jgb/A/dashboard-big-landlord-view` 大房東的首頁畫面和一般房東不一樣嗎？（只顯示物件/社區最新收支詳情與收支圖表，沒有捷徑與四個統計方塊） —— 句序 2：首頁網址不帶 bigLandlord_id，標籤條件任一成立就顯示「社區最新收支詳情」，所以首頁一律是這個標籤，不是「身分是社區才顯示」

回覆：

## 帳號資訊 `A-account-profile`（待審 10 條：pass 7／doubt 3／未先審 0）

- [pass] `jgb/A/account-phone-bind-status` 帳號資訊頁怎麼看手機的綁定狀態？（已綁定／未綁定，未綁定才有「前往綁定」按鈕）
- [pass] `jgb/A/account-email-verify-status` 帳號資訊頁的 Email 驗證狀態怎麼看？（Email 無法自行更改，需聯繫客服）
- [pass] `jgb/A/account-phone-no-change-entry` 手機已經綁定後可以自己更換嗎？（沒有更換入口，只顯示已綁定狀態）
- [pass] `jgb/A/account-sso-status` 帳號資訊頁怎麼看 SSO 綁定狀態？（Facebook／Google／LINE 各自顯示已綁定或未綁定）
- [pass] `jgb/A/account-preference` 帳號資訊頁的偏好設定能設定什麼？（登入預設房東身份、時區、Email 通知語系）
- [pass] `jgb/A/account-progress-unlock` 帳號資訊頁有「資訊完整度」進度條嗎？（目前頁面上不會顯示這個區塊）
- [pass] `jgb/A/account-save-integrity-check` 帳號資訊頁儲存失敗會提示什麼？（頁面沒有完整載入時會提醒重新整理再儲存）
- [doubt] `jgb/A/account-basic-info` 帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂） —— 句序 3：只有列入名單的特定合作團隊，合約簽完後才會鎖定租客資料，而且姓、名、身分證字號三欄都要有值才會鎖；原句寫成凡是雙方完成簽署就一律自動鎖定，漏了這些例外。evidence 引用的程式註解「合約雙方完成簽署後自動鎖定租客基本資訊」在釘住匯出裡也找不到
- [doubt] `jgb/A/account-change-password` 登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼，新密碼規則同註冊） —— 句序 3：註冊時密碼還必須同時含英文與數字（前端擋送出，後端也有 regex）；修改密碼頁雖然顯示「密碼應有至少一位英文和數字」，後端卻只檢查 min:6。所以「這與註冊時的密碼規則一致」不成立，標題「新密碼規則同註冊」也跟著錯。另外句序 4 的例子「受託的大房東子帳號」無源：father_id 子帳號其實是 SSO 綁定帳號
- [doubt] `jgb/A/account-contact-info` 帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話） —— 句序 2：「未勾選則需填寫 LINE ID」會被讀成必填，但 LINE 輸入框沒有 required，後端也直接照存、不做檢查；對「line id 要填嗎」這個問法會答錯

回覆：

## 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章） `A-signer-info`（待審 8 條：pass 2／doubt 6／未先審 0） ⚠️

- [pass] `jgb/A/signer-broker-manager-fields` 有不動產經紀人／租賃管理人員資格要多填什麼？（經紀人證號、租賃管理人員證號等）
- [pass] `jgb/A/signer-multi-entry-switch` 公司名下有多筆簽約對象時要怎麼切換？（表單上方出現切換列，超過 5 筆再加「所有團隊」下拉選單）
- [doubt] `jgb/A/signer-individual-fields` 個人房東的簽約資訊要填什麼？（姓氏、名稱、身分證字號、Email、手機、身分證正反面） —— 句序 5：切換列用的就是 ScrollNav 元件（isShowScrollBar，overflow-x: auto），本身就是橫向捲動列；「並不是變成側邊清單或捲動列」有程式反證，讀起來也像過程更正筆記
- [doubt] `jgb/A/signer-corp-fields` 公司身分的簽約資訊要填什麼？（公司名稱、統編、負責人、公司電話/Email、登記證資料） —— 句序 1：把必填項目寫成完整清單，但社宅團隊的「公司負責人」也是必填；句序 4 只說負責人都會顯示，沒說社宅必填，漏了社會住宅這個例外（問法「公司負責人要填嗎」會答錯）
- [doubt] `jgb/A/signer-corp-seals` 公司身分要上傳哪些印章與證件附件？（公司大章、小章、經紀人章、經紀業章、租賃管理員章） —— 句序 1：「固定要上傳五種印章附件」會被讀成必填；實際上五個印章欄位都沒有 isRequired，後端沒上傳就存 null，是選填
- [doubt] `jgb/A/signer-edit-permission` 簽約資訊誰能編輯？（沒有編輯權限的欄位會顯示為停用樣式） —— 句序 2：標題問「誰能編輯」，括號又說依編輯權限決定，但內文沒有講誰能編輯，也沒提任何權限，只說元件「能被設成不可編輯」，沒有回答標題。實際上是團隊資訊頁用 edit_role_info 權限來決定
- [doubt] `jgb/A/signer-address-fields` 簽約資訊的地址欄位怎麼填？（戶籍/通訊地址、公司登記/通訊地址皆為必填，可一鍵「同上」） —— 標題：標題加了引號的「同上」不是現行介面標籤，實際按鈕文字是「同戶籍地址」「同公司登記地址」（正對照：「同戶籍地址」有命中，「同上」命中 0）
- [doubt] `jgb/A/signer-manage-save-buttons` 簽約資訊頁的「管理」「儲存」按鈕做什麼？（管理開啟簽約對象管理視窗，儲存只在個人身分頁面出現） —— 句序 1：「管理」燈箱（團隊資訊管理）只有「新增」與刪除（×）兩個功能，沒有編輯或選擇簽約對象的功能；「新增、編輯或選擇」有程式反證

回覆：

## 通知中心 `A-notification-center`（待審 7 條：pass 5／doubt 2／未先審 0）

- [pass] `jgb/A/notification-center-type-filter` 通知中心怎麼依類型篩選通知？（依合約/帳務/修繕/裝置/其他分類）
- [pass] `jgb/A/notification-center-unread-dot` 通知中心的通知怎麼標示未讀？（列表項目左側的紅點，沒有「只顯示未讀」的篩選功能）
- [pass] `jgb/A/notification-center-per-page` 通知中心每頁顯示筆數可以怎麼調整？（30/60/90 筆，預設 30 筆）
- [pass] `jgb/A/notification-center-permission` 為什麼通知中心是空的？（房東側需要查看通知的權限才看得到通知內容）
- [pass] `jgb/A/notification-navbar-bell` 導覽列的通知鈴鐺會顯示什麼？（最近 5 筆通知與未點擊數量，大房東不會顯示）
- [doubt] `jgb/A/notification-mark-read-navigate` 點擊通知列表項目會發生什麼？（前往原連結，並帶上標記已讀的依據） —— 句序 1：「每則通知點擊後會依原連結前往」漏了例外：訊息類（type 32）走另一段邏輯，不會導頁，而是要開訊息燈箱（這段還引用了未定義變數 userMessageData）。句序 2 自己也列了「訊息」標籤，同一條細目前後不一致
- [doubt] `jgb/A/notification-mark-read-out-of-range` 篩選後頁碼超出範圍會自動跳回第一頁嗎？（寫了判斷式，但實際上永遠不會被觸發） —— 標題：標題括號「寫了判斷式，但實際上永遠不會被觸發」是實作詞兼過程筆記，不是使用者看得到的行為（內文本身正確）

回覆：

## 通知收件設定與發送報表（通知收件信箱最多再加 3 組） `A-notification-settings`（待審 4 條：pass 2／doubt 2／未先審 0） ⚠️

- [pass] `jgb/A/notification-settings-categories` 通知收件設定有哪些分類？（合約、帳務、修繕、訂閱、房東管理，另有限定開放的加盟分潤報表）
- [pass] `jgb/A/notification-settings-save` 通知收件設定改完怎麼儲存？（至少要有一個分類填了自訂信箱，儲存鍵才會啟用）
- [doubt] `jgb/A/notification-settings-extra-emails` 通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱） —— 句序 2：預設信箱取的是目前身分（團隊）擁有者的 Email，不是登入帳號本身的 Email；法人團隊成員看到的是團隊擁有者的信箱，漏了身分例外
- [doubt] `jgb/A/notification-settings-report-buttons` 「發送報表」「多團隊合併報表」按鈕是做什麼的？（限加盟分潤報表分類，多團隊合併僅限特定團隊） —— 句序 2：「特定樓宇團隊」寫出了客戶名稱（樓宇資產管理顧問有限公司，role 21228），應寫「特定合作團隊」；而且出處是程式註解

回覆：

## 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊） `B-team-profile`（待審 12 條：pass 10／doubt 2／未先審 0）

- [pass] `jgb/B/team-basic-info` 團隊資訊頁面可以設定什麼？（公司 Logo、團隊名稱、團隊介紹）
- [pass] `jgb/B/team-ad-contact` 廣告頁聯絡資訊要填什麼？（Line ID、Facebook、WhatsApp 選填，公司電話與公司 Email 必填）
- [pass] `jgb/B/team-delete` 怎麼刪除團隊？（需先解除訂閱方案、輸入團隊名稱確認、刪除後資料無法恢復）
- [pass] `jgb/B/team-signer-company-info` 簽約資訊卡的「公司資訊」要填什麼？（公司登記名稱上限 20 字、公司統編皆為必填；公司負責人只有社宅團隊必填；社宅團隊還要填必填的社宅業者編號與公司登記證號，公司登記證日期與縣市則不分團隊都是選填）
- [pass] `jgb/B/team-signer-agent-info` 簽約資訊卡的「經紀人資訊」要填什麼？（經紀人／經紀業名稱與證號，名稱上限 15 字；社宅團隊多了經紀人聯絡電話與 Email，且都是必填）
- [pass] `jgb/B/team-signer-manager-info` 簽約資訊卡的「租賃住宅管理人員資訊」要填什麼？（姓名與證號；社宅團隊多了聯絡電話欄位，且姓名／證號／電話都是必填；沒有 Email 欄位）
- [pass] `jgb/B/team-signer-stamps` 簽約資訊卡可以上傳哪幾種圖章？（法人或社宅團隊的簽約資訊卡才看得到「附件」與「電子簽約圖章」兩個區塊；「附件」有公司大章、公司小章、不動產經紀人章、不動產經紀業章、租賃管理員章五種，「電子簽約圖章」另外只有一個「圖章」欄位）
- [pass] `jgb/B/team-multi-company-info` 一個團隊可以管理多組公司資訊嗎？（可以在「團隊資訊管理」視窗新增與刪除，但清單第一筆不能刪除）
- [pass] `jgb/B/team-info-no-view-permission` 沒有查看團隊資訊的權限，打開團隊資訊頁會怎樣？（提示「您目前登入的帳號無法查看團隊資訊功能」）
- [pass] `jgb/B/team-signer-address-groups` 簽約資訊卡上有哪些地址欄位群？（個人的戶籍地址／通訊地址、公司的登記地址／通訊地址，都有「同上」可以直接帶入；社宅團隊另有經紀人與租賃管理人員各自的通訊地址）
- [doubt] `jgb/B/team-signer-personal-info` 簽約資訊卡「個人資訊」區塊只有個人團隊看得到，要填什麼？（姓氏、名稱、身分證字號、Email、手機必填；戶籍地址／通訊地址／身分證正反面／其他附件選填或另有條件） —— 句序 標題：標題把戶籍地址／通訊地址歸進「選填或另有條件」，但第 2 句與程式都寫兩組地址必填，標題和內文互相矛盾
- [doubt] `jgb/B/team-signer-profile-switch` 怎麼在多組簽約資訊之間切換？（頁面上方有分頁式選單，超過 5 組會收進「所有團隊」下拉選單） —— 句序 標題：標題說超過 5 組會「收進」「所有團隊」下拉選單，但實際上分頁列仍然整排顯示，下拉選單是另外多出來的，第 2 句也明寫「多出一個」且列出全部組數

回覆：

## 成員列表（邀請、角色、成員名下資料） `B-member-list`（待審 13 條：pass 10／doubt 3／未先審 0）

- [pass] `jgb/B/member-list-overview` 成員列表可以看到什麼資訊？（成員總人數、加入時間、Email、手機號碼、目前的角色）
- [pass] `jgb/B/member-invite` 怎麼邀請新成員加入團隊？（用 Email 或手機號碼搜尋，對方要先是 JGB 會員）
- [pass] `jgb/B/member-role-concept` 成員的「角色」權限決定什麼？（決定看得到與能編輯的物件、合約、帳務、修繕等範圍）
- [pass] `jgb/B/member-role-manage` 怎麼管理團隊的角色範本？（可新增、編輯、刪除，也能套用 JGB 內建的快速設定範本）
- [pass] `jgb/B/member-remove` 怎麼移除成員？（列表右側的紅色 × 圖示開啟確認視窗，按「移除」才會真的刪除；名下還有物件或合約會被擋下）
- [pass] `jgb/B/member-assign-owned` 怎麼指派物件或合約給成員？（點成員旁的鉛筆圖示選「編輯綁定物件」或「編輯綁定合約」）
- [pass] `jgb/B/member-role-permission-list` 怎麼查看每個角色能做什麼？（點「角色權限說明」的「這裡」開啟角色權限列表，每一列是一項權限、每一欄是一個角色，用勾號／叉號表示有沒有這項權限）
- [pass] `jgb/B/member-role-edit-open-condition` 編輯角色時的「開啟條件」是什麼？（要先勾選列出的其他權限，這個權限選項的勾選框才能點；沒先勾好之前，勾選框會維持鎖住）
- [pass] `jgb/B/member-list-sort` 成員列表可以怎麼排序？（姓名、加入時間、手機號碼、Email、角色名稱各有正反兩種排序）
- [pass] `jgb/B/member-list-role-select-disabled` 為什麼「團隊擁有者」和自己那一列的角色下拉不能改？（這兩列是固定顯示在列表最上面、角色下拉是鎖住的，跟其他成員分開處理）
- [doubt] `jgb/B/member-seat-limit` 邀請成員有名額上限嗎？（依訂閱方案而定，達上限要升級方案才能繼續邀請） —— 句序 2：這句寫成一律「導引前往升級訂閱方案」，漏了尚未訂閱的例外：沒有訂閱時 isFull 直接成立，視窗文字是「請先前往訂閱服務」，按鈕是「我要訂閱」，不是「升級」。本細目的 target_user 含 prospect，正好是這種情況
- [doubt] `jgb/B/member-list-role-inline-change` 成員列表可以直接改成員的角色嗎？（列表每一列都有角色下拉選單可以直接切換；選單裡也有「+ 新增角色」，可以直接開「編輯角色」視窗） —— 句序 1：「每一列都有角色下拉選單、選了就直接送出變更」是絕對句，漏了例外：團隊擁有者列和自己那一列的下拉是鎖住的 select-picker，也沒有「+ 新增角色」；沒有編輯權限時整個下拉也被鎖住。這和同組細目 member-list-role-select-disabled 互相矛盾，標題「每一列都有角色下拉選單可以直接切換」有同樣問題
- [doubt] `jgb/B/member-role-edit-reset` 編輯角色時的「重設條件」按鈕是做什麼的？（把目前正在編輯、還沒儲存的勾選狀態還原） —— 句序 標題：標題說「把還沒儲存的勾選狀態還原」，但內文與程式的行為都是「全部清空」，包括原本已載入的勾選；「回到調整前狀態」那段程式已被註解掉，標題和內文互相矛盾

回覆：

## 大房東列表與授權物件 `B-biglandlord-list`（待審 12 條：pass 9／doubt 3／未先審 0）

- [pass] `jgb/B/biglandlord-list-overview` 大房東列表可以看到哪些欄位？（ID、姓名、會員註冊、身分證字號、生日、主要聯絡方式、帳戶資訊、合作方式、合作起迄、所屬物件）
- [pass] `jgb/B/biglandlord-add` 怎麼新增大房東？（已註冊會員填 Email 即可，未註冊只要填姓氏與名稱，Email 選填）
- [pass] `jgb/B/biglandlord-authorize-estates` 大房東的「授權物件」怎麼設定？（逐筆物件勾選瀏覽廣告／合約／帳務／修繕；合約要先勾廣告，帳務要先勾廣告＋合約，修繕沒有前提）
- [pass] `jgb/B/biglandlord-import-export` 大房東名單可以批次匯入或匯出嗎？（可以，Excel 匯入新增、Excel 匯出下載）
- [pass] `jgb/B/biglandlord-actions-menu` 大房東列表每一列的操作選單有哪些功能？（編輯所屬物件、編輯大房東、刪除大房東）
- [pass] `jgb/B/biglandlord-delete-confirm` 刪除大房東會發生什麼？（先跳出確認視窗，確認後這位大房東就無法再存取這個團隊的任何資訊）
- [pass] `jgb/B/biglandlord-list-empty` 大房東列表沒有資料時會顯示什麼？（一開始沒有任何大房東顯示「尚無大房東」；用關鍵字搜尋卻沒有符合結果則顯示「沒有符合的結果😢」）
- [pass] `jgb/B/biglandlord-batch-template-fields` 批次匯入大房東的 Excel 範本要填哪些欄位？（姓氏、名稱必填，其餘含 Email、手機、身分證字號、地址、帳戶資訊、合作方式與合作起迄都是選填）
- [pass] `jgb/B/biglandlord-list-sort` 大房東列表可以用什麼排序？（姓名、手機號碼、Email、身分證字號，各有正序與反序共 8 種排序方式）
- [doubt] `jgb/B/biglandlord-authorize-apply-step` 授權物件頁取消勾選後，為什麼要按「套用」才會生效？（取消勾選只是待處理狀態，按套用才真的移除，按恢復可以取消這次變更） —— 句序 1：「「套用」後將移除此物件」這個遮罩只在按紅色 X 移除整筆物件（readyToRemove）時出現，取消勾選權限不會出現；標題的「取消勾選」和句意都錯把兩個動作混成一個
- [doubt] `jgb/B/biglandlord-escrow-owner` 大房東列表上方的「所有權人／轉租人」是做什麼用的？（記錄代管物件的所有權人或轉租人資料，加快編輯合約速度） —— 句序 1：現行側邊選單的「大房東列表」連到 SPA /bigLandlords/list，那頁上方沒有「所有權人／轉租人」區塊；這個區塊只存在舊 blade users/team/2，而現行選單沒有連到這頁，屬於舊路徑
- [doubt] `jgb/B/biglandlord-seat-limit` 大房東名額有上限嗎？（大房東列表頁的「新增大房東」目前沒有名額檢查；成員／大房東管理頁（團隊管理底下的大房東列表）的「邀請」按鈕才有，額滿時會提示升級方案） —— 句序 2：「成員／大房東管理」這個頁名在介面上不存在；「團隊管理底下的大房東列表」也和現行選單矛盾：團隊管理底下只有 type=1 的成員列表，大房東列表掛在「大房東管理」底下、連到 SPA；句中寫的「邀請」按鈕與額滿燈箱只在沒有選單入口的舊 blade users/team/2 上

回覆：

## 大房東報表 `B-biglandlord-report`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/B/biglandlord-report-overview` 大房東報表可以看到什麼？（依大房東列出所屬物件、出租中物件與執行中合約租金總額）
- [pass] `jgb/B/biglandlord-report-permission` 誰看得到大房東報表？（需要「查看大房東報表」的角色權限）
- [doubt] `jgb/B/biglandlord-report-community-rate` 大房東報表可以依社區細看嗎？（報表清單有「社區」欄，細節頁還會顯示匯率） —— 句序 2：「匯率」不是固定的欄位，是有條件的 tooltip：只有結算幣別和站台幣別不同、而且有匯率資料時才出現，手機版也不顯示文字；句子寫成一定會顯示，漏了條件

回覆：

## 大房東對帳表 `B-biglandlord-sheet`（待審 7 條：pass 7／doubt 0／未先審 0）

- [pass] `jgb/B/biglandlord-sheet-overview` 大房東對帳表在算什麼？（只有特定合作團隊看得到完整的押金、屋主資金、屋主提領、屋主直收等類別金額，其他團隊只看得到屋主租金收支；單月報表才有「上一月」「下一月」「下載」，整年度報表是「匯出報表」）
- [pass] `jgb/B/biglandlord-sheet-empty` 對帳表顯示「尚未被指派物件」是什麼意思？（這位大房東還沒被授權任何物件）
- [pass] `jgb/B/biglandlord-sheet-multi-currency` 對帳表出現「本月含多幣別帳單」提示是什麼意思？（該月的帳單有不同幣別，已用結算幣別加總）
- [pass] `jgb/B/biglandlord-sheet-hide-empty-rows` 對帳表可以隱藏沒有金額的項目嗎？（可以開關「隱藏空值項目」）
- [pass] `jgb/B/biglandlord-sheet-month-drilldown` 對帳表怎麼從年表切到單一月份的月報？（點表頭的月份會進入該月月報，點「取消」回到年表）
- [pass] `jgb/B/biglandlord-sheet-load-download-fail` 對帳表載入或下載失敗會怎樣？（載入失敗會顯示錯誤並提供「重試」，下載失敗只顯示錯誤訊息）
- [pass] `jgb/B/biglandlord-sheet-aside-and-loading` 大房東對帳表頁面的側邊選單和載入畫面長怎樣？（左側有社區／物件選單，看單一物件報表時會顯示上次匯入時間，報表產生中會顯示載入百分比進度條）

回覆：

## 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」） `B-advanced-settings`（待審 18 條：pass 10／doubt 8／未先審 0） ⚠️

- [pass] `jgb/B/advance-fee-items` 帳單的「自訂費用項目」怎麼設定？（分收入類／支出類，必填性質與自定義名稱，會科品項代號選填）
- [pass] `jgb/B/advance-additional-terms` 「預設補充條款」怎麼設定？（最多可以設 3 組，編輯合約時直接選用）
- [pass] `jgb/B/advance-custom-label` 「標籤設定」是做什麼用的？（幫物件加自訂標籤，單個標籤上限 18 字元）
- [pass] `jgb/B/advance-device-binding` 怎麼綁定智能裝置廠商？（輸入裝置廠商帳號密碼完成綁定，之後可在 JGB 平台管理裝置）
- [pass] `jgb/B/advance-notification-locale` 「Email 通知語系」在哪設定、誰看得到？（只有法人房東或社宅團隊看得到，決定代發通知信的預設語系）
- [pass] `jgb/B/advance-timezone` 「時區設定」會影響哪些通知？（只有法人房東或社宅團隊看得到，改變排程通知的發送時間）
- [pass] `jgb/B/advance-settlement-currency` 「結算幣別」是做什麼用的？（只有法人房東或社宅團隊看得到，把大房東報表的多幣別合約統一結算成一種幣別）
- [pass] `jgb/B/advance-device-binding-visibility` 為什麼進階設定看不到「裝置管理」區塊？（訂閱方案要生效中，且不能是免費方案）
- [pass] `jgb/B/advance-dedicated-account` 「房東專屬帳號」是做什麼用的？（只有法人房東或社宅團隊看得到；顯示在團隊首頁，且第一次儲存後不能自行修改，要洽 JGB 客服）
- [pass] `jgb/B/advance-contract-label` 「合約管理」的標籤設定跟物件的標籤設定是同一個嗎？（不是，這是合約專用的另一組標籤）
- [doubt] `jgb/B/advance-discount-items` 進階設定的「優惠項目」是給誰用的？（只有統上或新北住都的合作團隊才看得到，可設定折扣套用在租金費用上） —— 句序 1：標題與句子直接寫出客戶名「統上」「新北住都」，應改寫成「特定合作團隊」（第 2 句「新北住都合作團隊上限是 30 組」也有同樣問題）
- [doubt] `jgb/B/advance-late-fee` 進階設定的「延遲金設置」怎麼計算？（只有統上合作團隊看得到，公式是租金 × (逾期天數 - 緩衝天數) × 延遲金%） —— 句序 1：標題與句子寫出客戶名「統上」，應改寫成「特定合作團隊」
- [doubt] `jgb/B/advance-fee-items-merge` 自訂費用項目可以合併嗎？（可以選多個已存在的品項合併成新品項，合併後無法回復） —— 句序 1：實際流程不是「合併成一個新品項」：使用者要在「欲合併品項」下拉選單選一個已存在的品項，勾選的品項會併入那個品項，後端也是併入既有品項；另外系統預設品項不能勾選
- [doubt] `jgb/B/advance-payment-cycle-discount` 進階設定的「繳費週期優惠」是給誰用的？（只有統上團隊才看得到，選比月繳更長的繳費週期就有折扣） —— 句序 1：標題與句子寫出客戶名「統上」「新北住都」，應改寫成「特定合作團隊」
- [doubt] `jgb/B/advance-auto-publish-unpublish` 招租廣告可以自動刊登或自動下架嗎？（可以，合約到期日前 N 天自動刊登，簽約後自動下架） —— 句序 1：寫成每個團隊都能用，漏了例外：這兩個設定只在團隊 id 列在設定檔 auto_publish_role_ids 裡的團隊才會顯示，其他團隊看不到；標題「可以」也是同樣的絕對說法
- [doubt] `jgb/B/advance-sales-item-code` 「銷貨單品項代號對應」是做什麼用的？（只有特定團隊才有，設定匯出「M 化銷貨單」時每個品項要帶的產品代號） —— 句序 2：「沒有設定代號的品項，匯出產品代號會是空白」與現行設定燈箱矛盾：留空的品項會沿用系統預設代號，只有系統預設也沒有代號的品項才會是空白
- [doubt] `jgb/B/advance-community-labels` 「社區管理」的城市／區域／位置設定是做什麼？（只有特定合作團隊看得到，用來建立社區篩選用的自訂標籤） —— 句序 2：城市／區域／位置標籤實際上是在社區編輯頁選用，不是「為物件加上」標籤；標題說的「社區篩選用」在句子和程式裡都找不到根據
- [doubt] `jgb/B/advance-short-lease-approval` 進階設定的「短租期核可流程」是做什麼的？（只有統上合作團隊看得到；租期少於設定天數時，合約要先簽核通過才會發出邀請給租客） —— 句序 1：標題與句子寫出客戶名「統上」，應改寫成「特定合作團隊」

回覆：

## 租客列表（當前租客／封存、準時繳租率、信用評價） `B-tenant-list`（待審 14 條：pass 10／doubt 4／未先審 0）

- [pass] `jgb/B/lessee-tabs` 租客列表有哪兩個分頁？（當前租客／封存，封存代表這位租客已被移出列表且目前沒有進行中的合約）
- [pass] `jgb/B/lessee-credit-rating-visibility` 租客列表的「信用評價」欄位為什麼有些人看不到？（需要有查看租客信用評價的權限才會顯示這一欄）
- [pass] `jgb/B/lessee-notification-status-color` 租客列表裡 Email／手機號碼顯示藍色、橘色、灰色代表什麼？（驗證狀態：已驗證／等待驗證／未驗證）
- [pass] `jgb/B/lessee-verification-link-expiry` 租客的 Email／手機驗證連結多久過期？（72 小時）
- [pass] `jgb/B/lessee-on-time-pay-rate` 租客的「準時繳租率」怎麼算？（已到帳未逾期帳單數 ÷ 全部應計入帳單數）
- [pass] `jgb/B/lessee-list-columns` 租客列表可以看到哪些欄位？（ID、姓名、會員註冊、Email - 通知、手機號碼 - 通知、註冊合約、免註冊合約、所屬修繕、準時繳租率、帳戶名稱、帳號資訊、操作）
- [pass] `jgb/B/lessee-pending-verification-bill-draft` 租客的 Email 或手機還在等待驗證時，帳單會怎樣？（帳單會停留在草稿分頁，等驗證完成或連結過期才能發送，也可以手動移動）
- [pass] `jgb/B/lessee-export-entry-by-role` 匯出租客的入口在哪？（一般房東用「新增租客」下拉選單裡的「匯出租客」；社宅團隊只有一顆「匯出」按鈕，沒有新增或匯入）
- [pass] `jgb/B/lessee-list-search-and-pagination` 租客列表可以怎麼搜尋篩選、每頁看幾筆？（可依姓名／Email／手機號碼／租客 ID 搜尋，用會員註冊與通知狀態篩選，每頁可選 30／60／90 筆）
- [pass] `jgb/B/lessee-action-menu` 租客列表每一列的操作選單有哪些功能？（建立電子合約、上傳紙本合約、編輯租客、封存租客；封存分頁裡則改成刪除租客）
- [doubt] `jgb/B/lessee-crud` 租客列表可以新增、匯入、匯出租客嗎？（可以手動新增，也支援 Excel 匯入與匯出） —— 句序 1：寫成每個團隊都能新增、匯入、匯出，漏了身分例外：只有個人房東與法人房東有「新增租客」「匯入租客」，社宅團隊只有「匯出」（同組 lessee-export-entry-by-role 已寫明）
- [doubt] `jgb/B/lessee-notification-toggle-effect` 租客的通知開關關閉後會怎樣？（收不到任何合約或帳單的通知信件或簡訊） —— 句序 1：Email 與手機的通知開關是分開的，關掉其中一個只停那一種管道；已註冊租客的開關不能操作，仍會收到 Email。「收不到任何信件或簡訊」把兩個管道和兩種身分混成一句
- [doubt] `jgb/B/lessee-list-columns-by-role` 社宅團隊與特定合作團隊的租客列表欄位有什麼不一樣？（社宅團隊沒有「會員註冊」「免註冊合約」「操作」，「註冊合約」欄改叫「所屬總合約」；特定合作團隊多了國籍、生日、主要聯絡方式） —— 句序 2：「特定合作團隊多出國籍、生日、主要聯絡方式」在現行畫面不會發生：currentRole 只會回傳社宅或 default，beyond360 那組欄位永遠選不到；第 1 句加引號的「操作」也不是實際存在的表頭標籤
- [doubt] `jgb/B/lessee-bulk-notify` 租客列表勾選多筆租客後可以做什麼？（統上團隊可以批次發送通知，其他團隊沒有這個批次操作） —— 句序 1：標題與句子寫出客戶名「統上」，應改寫成「特定合作團隊」

回覆：

## 社區列表與建立 `C-community-list`（待審 8 條：pass 7／doubt 1／未先審 0）

- [pass] `jgb/C/community-list-overview-stats` 社區總表顯示什麼資訊？（物件總數、招租／買賣廣告數、空置數量、本月應收與已收）
- [pass] `jgb/C/community-add-single-and-limit` 如何新增社區？（訂閱方案有可建立社區數量上限）
- [pass] `jgb/C/community-batch-add-and-copy` 怎麼批次新增社區、或複製現有社區建立新社區？
- [pass] `jgb/C/community-list-filter-sort` 社區總表怎麼搜尋與排序？（案名／地址關鍵字、縣市行政區、建物類型、捷運站）
- [pass] `jgb/C/community-export-list` 社區總表可以匯出嗎？（需要匯出物件權限，會依目前篩選條件匯出）
- [pass] `jgb/C/community-list-pagination` 社區總表每頁筆數可以調整嗎？（30／60／90項）
- [pass] `jgb/C/community-list-add-permission` 誰看得到新增社區的入口？（總表右上角需要編輯物件權限；空狀態的批次新增／新增社區入口需要新增物件權限）
- [doubt] `jgb/C/community-delete-requires-empty` 社區可以刪除嗎？（社區底下不能有任何物件才能刪除，且刪除後無法復原） —— 句序 1：加引號的「刪除」不是現行選單標籤，齒輪選單的選項字樣是「刪除社區」（「刪除」只是確認燈箱裡的按鈕），而且這個選項只有具編輯物件權限的人才看得到

回覆：

## 社區資料編輯（基本資料、照片與描述、介紹與交通） `C-community-edit`（待審 6 條：pass 5／doubt 1／未先審 0）

- [pass] `jgb/C/community-edit-tabs` 社區編輯有哪些分頁？（基本資料、介紹與交通、照片與描述）
- [pass] `jgb/C/community-edit-gallery-photo-limit` 社區照片與描述可以上傳幾張圖片？（限1張，JPG/PNG，檔案大小最大10MB）
- [pass] `jgb/C/community-edit-gallery-save-notice` 社區照片與描述什麼時候會跳出「已更新」提示？（存檔成功後才出現，不是上傳當下）
- [pass] `jgb/C/community-edit-intros-and-transit` 社區介紹與交通怎麼填？（社區簡介、鄰近交通說明、可加多個鄰近捷運站）
- [pass] `jgb/C/community-edit-basic-required-field` 社區基本資料哪個欄位是必填？（只有社區名稱是必填）
- [doubt] `jgb/C/community-edit-basic-fields` 社區基本資料要填什麼？（社區名稱限30字、詳細地址與對外顯示地址、建築類型、總樓層、屋齡） —— 句序 1：夾了過程筆記「查不到對應的長度驗證規則，無法確認超過30字時是否真的會被擋下」；而且程式確實沒有長度驗證（name 只有 required），「限制30個字」只是輸入框的提示文字，標題卻寫成「社區名稱限30字」

回覆：

## 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） `C-community-estates`（待審 5 條：pass 1／doubt 4／未先審 0） ⚠️

- [pass] `jgb/C/community-estates-pagination` 社區物件清單每頁筆數可以調整嗎？（30／60／90項）
- [doubt] `jgb/C/community-estates-overview-card` 社區底下物件頁最上方顯示什麼？（招租廣告、買賣廣告、目前空置數量、類型、屋齡、本月應收與已收金額） —— 句序 3：「管理員身分」是從 is_admin 這個實作欄位來的說法，JGB 沒有叫「管理員」的角色；實際條件是具編輯物件權限（擁有者也包含在內）
- [doubt] `jgb/C/community-estates-category-switch` 社區底下的物件清單怎麼切換總覽／招租／買賣？（欄位標題會跟著切換內容改變） —— 句序 1：加引號的「總覽-1」是 i18n 翻譯 key，沒有核實過畫面上實際顯示的字；草稿自己的 open_questions 也寫了無法確認
- [doubt] `jgb/C/community-estates-add-batch-copy` 怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制） —— 句序 3：加引號的「社區共用空間」出自程式註解，不是介面標籤；介面上這類物件叫「公共區域」
- [doubt] `jgb/C/community-estates-extra-tabs` 社區底下有差額發票、投報率頁籤嗎？（依團隊是否開通該功能才會出現，投入成本與投報率兩個頁籤是同一個開關） —— 句序 2：「開通投報率功能時這兩個頁籤會一起出現」漏了身分與權限的例外：大房東，以及沒有 show_bill 權限的人，即使團隊已開通也看不到這兩個頁籤

回覆：

## 社區公開頁（社區詳情、社區總表） `C-community-public-page`（待審 4 條：pass 1／doubt 3／未先審 0） ⚠️

- [pass] `jgb/C/community-show-content` 社區公開頁（社區廣告）顯示什麼？（基本資訊、鄰近捷運、社區介紹、刊登中物件）
- [doubt] `jgb/C/community-show-price-range` 社區公開頁最上方顯示什麼價格區間？（租賃金額區間、售價金額區間、售價單價區間坪或平方公尺隨語系切換） —— 句序 2：後端的 sell_price_range_per_unit 永遠是空陣列，所以「售價單價區間」根本不會顯示，而且畫面上也沒有「售價單價區間」這個標籤；句序 1 的「只在有2筆資料時」其實是 length===2 的實作寫法，意思是「有刊登中物件的最小／最大值」，不是「兩筆物件」
- [doubt] `jgb/C/community-show-share` 社區公開頁怎麼分享？（分享燈箱、查看所有物件連結） —— 句序 2：「查看所有物件」連到的是團隊的公開店鋪頁（users.public，只帶團隊 encryptId），不是這個社區的物件清單；句序 1 也漏了例外：行動裝置支援 navigator.share 時，會改用系統的分享選單，不會開燈箱
- [doubt] `jgb/C/community-show-editor-nav` 在社區廣告頁可以直接跳到編輯社區、社區詳情或社區總表嗎？（只有管理員看得到這個選單） —— 句序 1：標題和內文寫「只有管理員（身分）」，但實際條件是具編輯物件權限（is_admin 就是 edit_estate），「管理員」是實作詞，不是現行的角色名稱

回覆：

## 物件綁定社區的導引（2022/05 社區功能上線時的強制綁定流程，限團隊擁有者） `C-community-force-binding`（待審 5 條：pass 5／doubt 0／未先審 0）

- [pass] `jgb/C/forcebinding-why-and-who` 為什麼會出現「物件需綁定社區」的導引？（2022/05/12 社區功能上線，只有團隊擁有者能操作）
- [pass] `jgb/C/forcebinding-welcome-progress` 物件綁定社區的導引起始畫面顯示什麼？（已綁定與尚未綁定的物件數量、需同意服務條款）
- [pass] `jgb/C/forcebinding-two-steps` 物件綁定社區導引有哪兩個步驟？（填寫社區資料、選擇欲綁定社區內的物件；未完成系統功能無法正常使用）
- [pass] `jgb/C/forcebinding-select-estates-irreversible` 怎麼挑選要綁定的物件？（可關鍵字搜尋、每頁30/60/90項，確認綁定後無法修改）
- [pass] `jgb/C/forcebinding-completion-states` 綁定完成後會看到什麼？（全部綁完顯示恭喜，還有剩則提示繼續綁定）

回覆：

## 物件列表與篩選 `C-estate-list`（待審 10 條：pass 6／doubt 4／未先審 0） ⚠️

- [pass] `jgb/C/estate-list-add-must-pick-community` 物件總表怎麼新增物件？（新增與複製現有物件都要先經過社區選擇畫面，目前沒有批次新增入口）
- [pass] `jgb/C/estate-list-counter-and-limit` 物件總表標題下方顯示什麼？（目前物件總數、尚可新增數量）
- [pass] `jgb/C/estate-list-keyword-search` 物件總表關鍵字搜尋可以查什麼？（案名、地址、租客、物件ID、手機、信箱）
- [pass] `jgb/C/estate-list-batch-actions` 物件總表可以批次操作嗎？（匯出物件、新增批次帳單、批次刊登／取消刊登招租廣告、刪除；批次取消刊登失敗時不會顯示任何提示）
- [pass] `jgb/C/estate-list-pagination` 物件總表每頁筆數可以調整嗎？（30／60／90項）
- [pass] `jgb/C/estate-list-category-switch` 物件總表怎麼切換總覽／招租／買賣？（三種分類切換）
- [doubt] `jgb/C/estate-list-filters` 物件總表有哪些進階篩選條件？（縣市行政區、經理人、大房東、社區、捷運、用途、格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金與面積(坪)範圍、標籤） —— 句序 標題：標題列出的篩選條件包含「用途」，但句序2寫的是「沒有依用途篩選的選項」，標題和內文互相矛盾；程式也證實物件總表的進階搜尋沒有用途篩選
- [doubt] `jgb/C/estate-status-affects-actions` 物件狀態會影響哪些功能？（未刊登／刊登中／洽談中／合約中，各自能做的操作不同） —— 句序 1：加引號的「合約中」是幫助中心 slug39 的舊用詞；現行物件總表的貼標和即時合約狀態篩選都寫「租約中」（另兩個是「無合約／無租約」「洽談中」），介面上找不到「合約中」這個字；draft 的 open_questions 也已經指出這個落差
- [doubt] `jgb/C/estate-list-filters-space-type-and-others` 物件總表篩選還有哪些條件？（空間類型多選、其他群組：VR、有電梯、可開伙、可養寵物） —— 句序 2：加引號的「其他」群組不是現行介面標籤；VR／有電梯／可開伙／可養寵物這組篩選的按鈕，桌機版和手機版都寫「更多」
- [doubt] `jgb/C/estate-list-sort-remembers-last` 物件總表怎麼排序？（排序選項由系統提供，上次選的排序方式會被記住並自動帶入） —— 句序 2：「排序方式會被記住」這句是絕對句，漏了窄螢幕的例外：寬度小於 576px 時，手機版 ListSearchBar 把排序存在另一把鍵下，進頁時只讀 estatesList，所以手機上不會自動帶入上次的排序

回覆：

## 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） `C-estate-edit`（待審 13 條：pass 10／doubt 3／未先審 0）

- [pass] `jgb/C/estate-edit-basic-address` 物件的詳細地址與對外顯示地址有什麼差別？
- [pass] `jgb/C/estate-edit-basic-floor-room-number` 物件的樓層與房號要怎麼填？（頂加輸入+1、地下室輸入-1）
- [pass] `jgb/C/estate-edit-basic-community-name-hide` 物件廣告頁可以隱藏群組/大樓名稱嗎？
- [pass] `jgb/C/estate-edit-building-transcript-social` 社宅物件建物謄本要填什麼？（申請謄本日期、段小段、謄本面積公式，不會顯示在廣告頁）
- [pass] `jgb/C/estate-edit-gallery-title-photos` 物件標題與照片有什麼限制？（標題最長60字、照片最多15張15MB、平面圖最多5張含PDF）
- [pass] `jgb/C/estate-edit-intro-transit` 物件介紹要填什麼？（房源簡介、鄰近交通，可加多筆鄰近捷運站）
- [pass] `jgb/C/estate-edit-vr-720` 物件的720 VR全景照怎麼拍？（需先安裝 VR Maker App 掃 QR Code 拍攝，可設定是否用於廣告）
- [pass] `jgb/C/estate-edit-cannot-change-community` 物件可以換綁到別的社區嗎？（畫面上目前沒有這個操作入口）
- [pass] `jgb/C/estate-edit-basic-orientation` 物件基本資料可以填朝向嗎？
- [pass] `jgb/C/estate-edit-tabs-overview` 物件編輯有哪些分頁？（「物件資訊」與「廣告資訊」兩個群組；社宅與一般物件的建物謄本分頁互斥）
- [doubt] `jgb/C/estate-edit-basic-space-type` 物件基本資料的空間類型、用途、格局要怎麼填？ —— 句序 1：「底下先選『用途』…必填」是絕對句，漏了社宅例外：社宅物件（property_purpose_key=2）的基本資料根本不顯示用途欄位；另外用途選項會依團隊設定縮減，「兩者都是必填」的「兩者」指的是哪兩個也不清楚
- [doubt] `jgb/C/estate-edit-building-transcript-general` 一般物件建物謄本要填什麼？（土地標的清冊、坐落基地、稅籍編號、專有部分、主建物、附屬建物） —— 句序 1：「要求填寫」讀起來是必填，和社宅那條同樣措辭（那邊確實是必填）放在一起更容易誤解；但一般物件建物謄本的欄位都沒有必填標記，這個分頁也不列入完成勾選；「供實價登錄使用」只出現在程式註解，介面上沒有這句
- [doubt] `jgb/C/estate-edit-facilities` 物件附設傢俱怎麼設定？（第一個區塊標題是格局(<空間類型>)，依空間分區加入家電、傢俱、自訂項目，數量0不顯示在廣告頁） —— 句序 1：「第一個區塊標題是格局(<空間類型>)」是絕對句，但社宅物件載入的是另一個元件，標題是「附設傢俱／設備」；車位和空地則只顯示「格局」加上「不需要設定」的提示；這條的來源只引了一般物件的 General.vue

回覆：

## 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實） `C-rent-listing`（待審 8 條：pass 7／doubt 1／未先審 0）

- [pass] `jgb/C/estate-rent-detail-deposit-cap` 招租押金有法定上限嗎？（一般租賃契約押金最高不得超過兩個月租金）
- [pass] `jgb/C/estate-rent-detail-move-in-lease-terms` 招租詳情的最短租期、最快入住日、最快點交日怎麼填？
- [pass] `jgb/C/estate-rent-detail-tenant-conditions` 招租條件要求可以設定什麼？（身份限制複選、養寵物可否、開伙可否、生活公約）
- [pass] `jgb/C/estate-rent-contact-agency-info` 刊登主資訊的團隊資訊要在哪裡修改？（法人／社宅房東顯示公司資訊、到團隊資訊修改；個人房東顯示經理人資訊、到帳號資訊修改）
- [pass] `jgb/C/estate-rent-contact-manager-and-hide` 招租廣告可以隱藏經理人／房東的名稱、電話、Email嗎？（勾選框在「經理人資訊」或「刊登主資訊」的經理人卡片上，每種身分只有一組）
- [pass] `jgb/C/estate-rent-verify-legal` 招租的核實訊息是什麼？（依租賃住宅市場發展條例核實產權登記與違建面積）
- [pass] `jgb/C/estate-rent-open-permission-and-validation` 為什麼物件刊登不出去？（需要刊登物件或新增物件的權限；必填欄位沒填完會退回編輯頁）
- [doubt] `jgb/C/estate-rent-detail-price-and-tax` 招租詳情要填哪些金額相關欄位？（面積、幣別、每月租金、營業稅：應稅／零稅率／免稅） —— 句序 2：「營業稅可以選擇應稅／零稅率／免稅」是絕對句，但營業稅欄位只對特定合作團隊顯示；句序1的「同建物謄本面積」也只有社宅物件才有，而且介面上是按鈕不是勾選框，一般物件改用面積換算元件

回覆：

## 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） `C-estate-dashboard`（待審 9 條：pass 6／doubt 3／未先審 0） ⚠️

- [pass] `jgb/C/estate-dashboard-rent-performance` 招租表現分頁顯示什麼？（空置天數、廣告瀏覽次數、帳務表現、合約歷程與修繕紀錄摘要）
- [pass] `jgb/C/estate-dashboard-bills-tabs` 物件儀表板的帳務收支有哪些子頁籤？（總收支、統計報表）
- [pass] `jgb/C/estate-dashboard-repair-status-flow` 物件儀表板修繕紀錄怎麼呈現？（申請修繕→安排修繕→完成修繕→結單四狀態）
- [pass] `jgb/C/estate-dashboard-runnings-vs-memos` 「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入/支出金額，記事本只是純文字備註）
- [pass] `jgb/C/estate-dashboard-monthly-report-upload` 每月報表／每月對帳單怎麼上傳？（PDF、10MB上限，可批次指定多個物件，同月重傳會覆蓋舊檔）
- [pass] `jgb/C/estate-dashboard-top-cards` 物件儀表板最上方顯示哪三張卡？（物件資訊、招租廣告、買賣廣告；編輯捷徑需要新增物件權限）
- [doubt] `jgb/C/estate-dashboard-entry-and-groups` 物件儀表板進去預設是哪個分頁？（預設招租表現；大房東看不到「限管理者查看」分頁群組） —— 句序 1：「預設導向招租表現」寫成絕對句，漏了大房東這個例外：大房東從物件總表進入時會直接導到「合約歷程」；如果大房東照預設進到招租表現，API 會把他導回物件總表。這也和第 3 句「大房東只看得到與大房東共享的分頁」互相衝突
- [doubt] `jgb/C/estate-dashboard-contracts-history` 物件儀表板的合約歷程顯示哪些欄位？（一般房東：狀態／簽約類型／物件／承租人／租期／是否通知；社宅房東：合約名稱／承租人／租期） —— 句序 1：括號裡寫「租客身分登入時標題改成出租人、不顯示是否通知」，但物件儀表板整個路由禁止租客進入，租客根本看不到這一頁，這句在現行畫面上到不了
- [doubt] `jgb/C/estate-dashboard-attachments-vs-contract-attachments` 「附件清單」跟「合約附件」差在哪？（附件清單自由上傳、有儲存空間上限，下載不限身分但只有代理人且有新增物件權限才能刪除；合約附件是租賃法定文件的固定清單） —— 句序 1：「附件清單可自由上傳任意檔案」有反證：前端上傳欄位和後端驗證都只收 JPG／PNG／PDF

回覆：

## 單一物件廣告頁（招租） `C-estate-public-page`（待審 8 條：pass 7／doubt 1／未先審 0）

- [pass] `jgb/C/estate-house-preview-unpublished` 物件還沒刊登（未開放）時，廣告頁會怎麼顯示？（屋主看到的是預覽頁提示；其他人造訪會得到404）
- [pass] `jgb/C/estate-house-invite-countdown` 簽約邀請連結會失效嗎？（連結會顯示倒數，過期後失效）
- [pass] `jgb/C/estate-house-content-blocks` 物件廣告頁顯示哪些內容？（照片／VR全景切換、設備與設施、交通與環境設施、溫馨提醒）
- [pass] `jgb/C/estate-house-contact-landlord` 物件廣告頁「聯絡房東」區塊顯示什麼？（房東電話／Email依隱藏設定決定是否顯示；公司廣告電話／Email不受隱藏設定影響）
- [pass] `jgb/C/estate-house-vs-show-url` 物件廣告頁的網址會自動轉換嗎？（刊登中時，內部編號網址會自動轉址到 JGB 編號公開網址）
- [pass] `jgb/C/estate-house-fees-table` 物件廣告頁有費用明細表嗎？（車位物件不顯示，其餘物件顯示生活費用表）
- [pass] `jgb/C/estate-house-appointment-cta` 物件廣告頁有預約入住的按鈕嗎？（一般訪客看到「立即預約入住」，受邀簽約者看到「查看合約」）
- [doubt] `jgb/C/estate-house-info-card` 物件廣告頁的資料卡片顯示什麼？（地址／社區名稱、租金元/月與含哪些費用、建築類型與樓層或格局、商用類的空間類型與座位數、面積、物件平面圖） —— 句序 4：「座位數只在商用、且不是店面也不是整層空間時顯示」與現行執行結果不符：頁面傳進元件的 spaceType 是翻譯後的中文標籤（「店面」「整層空間」），元件卻拿它跟英文 key 比對，所以條件永遠成立，所有商用物件都會顯示座位數

回覆：

## 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） `C-team-storefront`（待審 5 條：pass 3／doubt 2／未先審 0） ⚠️

- [pass] `jgb/C/team-public-page-purpose` 房東對外首頁（招租店舖）是什麼？（公開展示聯絡資訊、簡介與所有刊登中物件，供分享給潛在租客）
- [pass] `jgb/C/team-public-page-edit-and-banner` 招租店舖上可以直接編輯哪些內容？（封面照片、大頭照、姓名、自我介紹，會連動帳號資訊）
- [pass] `jgb/C/team-public-page-filter-and-view` 招租店舖怎麼篩選物件？（鄉鎮區或捷運、類型與格局，可切換小圖示／大圖示／條列式；每頁筆數 30／60／90，預設 30）
- [doubt] `jgb/C/team-public-page-share` 招租店舖怎麼分享？（可分享至FB、Line、LinkedIn，加入團隊且設定客製帳號可有專屬短網址） —— 句序 2：「有客製短網址就分享它，否則用系統產生的固定網址」出自舊路徑：share/public 端點只有舊的 users/public.blade.php 在引用，而這個 blade 已經沒有任何 controller 會渲染。現行招租店舖是 Vue 頁面，分享出去的就是當下頁面的網址
- [doubt] `jgb/C/team-public-page-recruitment` 多團隊招募頁是什麼？（沒有指定住宅或商用時自動轉址到住宅、強制只顯示招租、不顯示社區篩選、每頁預設10筆） —— 句序 標題：標題寫了「每頁預設10筆」，內文卻沒有這一句（這件事只寫在同組的 filter-and-view）。標題問「是什麼」，內文也只列出和一般店舖的差異，沒有說明這個頁面本身是什麼

回覆：
