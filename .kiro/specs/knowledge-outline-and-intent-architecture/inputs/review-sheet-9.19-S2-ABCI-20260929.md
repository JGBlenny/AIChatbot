# 審核單：Plan 9.19 S2 A／B／C＋I 修正後重新先審（111 條）

> 審閱的正本版本：commit `bdb2327b`。本單由 `scratchpad/p919_s2_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 83／doubt 26／未先審 0。
> 回覆方式（S3）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審（[hold] 不計入分母）。⛔ 標示「有未先審細目」的組不可整組回「過」。
> [hold]＝業主已裁列下個計畫刪除，⛔ 標已審；整組回「過」也不涵蓋它們。

## 註冊帳號（Email／SSO、驗證碼、手機綁定） `A-registration`（待審 12 條：pass 9／doubt 3／未先審 0）

- [pass] `jgb/A/register-email-steps` 如何註冊 JGB 帳號？（Email、驗證碼、帳號設定三步驟）
- [pass] `jgb/A/register-sso` 可以用 Facebook、Google、LINE 註冊嗎？（SSO 仍需完成 Email 綁定）
- [pass] `jgb/A/register-email-verify-resend` 沒收到 Email 驗證碼怎麼辦？（可重發，發送次數過多會出現等待秒數）
- [pass] `jgb/A/register-password-rule` 註冊密碼格式要求是什麼？（至少 6 碼、須同時包含英文與數字）
- [pass] `jgb/A/register-email-already-registered` 註冊時 Email 已被註冊過怎麼辦？（已完成註冊的 Email 會直接被擋下；只有還沒完成 Email 註冊的舊帳號才會進行帳號合併）
- [pass] `jgb/A/register-phone-bind` 註冊要綁定手機號碼嗎？（可選填、簡訊驗證、可「下次再驗證」略過）
- [pass] `jgb/A/register-phone-already-bound` 註冊時發現手機已綁定過怎麼辦？（直接顯示已綁定、按繼續完成流程）
- [pass] `jgb/A/register-role-select` 註冊完之後要選身分嗎？（一般會在房東/管理者、租客中二選一，可同時擁有兩種身分；從租客端網站導轉來的會直接導回原頁）
- [pass] `jgb/A/register-verify-code-shape` 驗證碼輸入畫面長什麼樣子？（識別碼加 4 碼數字；輸入錯誤太多次驗證碼會失效，需重新發送）
- [doubt] `jgb/A/register-tenant-contract-invitation` 租客從電子合約邀請怎麼註冊？（房東建約發邀請，租客點「查看合約」再點「註冊」接續完成） —— 句序 3：「點選「註冊」按鈕」這個引號標籤是照幫助中心文件寫的，現行登入頁上沒有叫「註冊」的按鈕，只有「立即註冊」；標題也有同樣問題
- [doubt] `jgb/A/register-captcha-expired` 註冊卡在機器人驗證過期怎麼辦？（會退回第一步重新勾選） —— 句序 1：提示加退回第一步，只發生在寄驗證信時後端回 recaptcha_required；如果停在第一步時勾選過期，只會把「繼續」按鈕收起來，不會提示也沒有退回。另外講法「驗證框顯示不出來」內文完全沒有回答
- [doubt] `jgb/A/register-email-link-resume` 從驗證信連結折返時會從頭開始註冊嗎？（系統會記住 Email，但機器人驗證失效時會退回第一步） —— 句序 1：標題和講法寫的是「驗證信連結」，但驗證信裡只有驗證碼，沒有註冊連結；程式處理的其實是從信箱 App 重新點開「註冊邀請連結」的情境。句 1 也是照程式註解改寫的開發背景說明

回覆：

## 登入 `A-login`（待審 3 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/A/login-role-redirect` 登入時身分選錯了怎麼辦？（會依選擇的身分決定進入哪個角色的登入表單）
- [pass] `jgb/A/login-no-account-register-link` 登入頁有連到註冊頁的連結嗎？（登入表單上方的「還沒有帳號嗎？立即註冊」）
- [hold] `jgb/A/login-sso-redirect-no-duplicate-buttons` 從 Facebook／Google／LINE 導回登入頁時，第三方登入按鈕會重複出現嗎？（不會） —— 業主已裁列下個計畫刪除，⛔ 標已審（先審判定：doubt）

回覆：

## 忘記帳號、忘記密碼 `A-account-recovery`（待審 4 條：pass 3／doubt 1／未先審 0）

- [pass] `jgb/A/forget-account-no-phone` 沒綁手機號碼還能用「忘記帳號」找回嗎？（不行，只能靠手機簡訊驗證）
- [pass] `jgb/A/forget-password-flow` 忘記密碼怎麼辦？（Email 或手機任一驗證後即可重設新密碼）
- [pass] `jgb/A/forget-password-setpwd-invite` 「請設定密碼」畫面是什麼情境？（受邀請帳號的初次設定密碼流程）
- [doubt] `jgb/A/forget-account-flow` 忘記帳號怎麼辦？（用已綁定的手機號碼簡訊驗證找回 Email 提示） —— 句序 4：「聯繫所屬的租賃管理業者」出自幫助中心寫給租客的文章，但本細目的對象是房東/管理者，這句沒有限定身分；現行畫面寫的則是「如有其他問題，請聯繫 JGB 客服」

回覆：

## 會員中心首頁 `A-member-home`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/A/dashboard-big-landlord-view` 大房東的首頁畫面和一般房東不一樣嗎？（只顯示社區最新收支詳情與收支圖表，沒有捷徑與四個統計方塊）

回覆：

## 帳號資訊 `A-account-profile`（待審 3 條：pass 1／doubt 2／未先審 0） ⚠️

- [pass] `jgb/A/account-contact-info` 帳號資訊頁的聯絡資訊要填什麼？（LINE ID、Facebook 個人首頁、WhatsApp、第二組電話）
- [doubt] `jgb/A/account-basic-info` 帳號資訊頁能改哪些基本資料？（大頭照、姓氏、名稱、稱謂） —— 句序 3：「姓氏、名稱、身分證字號都已填寫才鎖定」只是其中一條路徑；房東在租客簽完後簽署的那條路徑，只要合約上有租客身分證字號，而且團隊在名單內，就會直接上鎖，不看姓名有沒有填
- [doubt] `jgb/A/account-change-password` 登入後怎麼在帳號資訊頁修改密碼？（需輸入目前密碼、新密碼與確認新密碼） —— 句序 4：程式是把新密碼寫進 father_id 底下所有子帳號，其中也包含 Email 登入帳號，跟「有沒有綁 Facebook/Google/LINE」無關。這是內部資料結構的細節，寫成「同步到綁定的登入帳號」會讓人誤以為第三方帳號的密碼也改了

回覆：

## 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章） `A-signer-info`（待審 8 條：pass 8／doubt 0／未先審 0）

- [pass] `jgb/A/signer-individual-fields` 個人房東的簽約資訊要填什麼？（姓氏、名稱、身分證字號、Email、手機、身分證正反面）
- [pass] `jgb/A/signer-corp-fields` 公司身分的簽約資訊要填什麼？（公司名稱、統編、負責人、公司電話/Email、登記證資料）
- [pass] `jgb/A/signer-corp-seals` 公司身分可以上傳哪些印章與證件附件？（公司大章、小章、經紀人章、經紀業章、租賃管理員章，皆為選填）
- [pass] `jgb/A/signer-broker-manager-fields` 有不動產經紀人／租賃管理人員資格要多填什麼？（經紀人證號、租賃管理人員證號等）
- [pass] `jgb/A/signer-edit-permission` 簽約資訊誰能編輯？（沒有編輯權限的欄位會顯示為停用樣式）
- [pass] `jgb/A/signer-address-fields` 簽約資訊的地址欄位怎麼填？（戶籍/通訊地址、公司登記/通訊地址皆為必填，可一鍵「同戶籍地址」「同公司登記地址」）
- [pass] `jgb/A/signer-multi-entry-switch` 公司名下有多筆簽約對象時要怎麼切換？（表單上方出現切換列，超過 5 筆再加「所有團隊」下拉選單）
- [pass] `jgb/A/signer-manage-save-buttons` 簽約資訊頁的「管理」「儲存」按鈕做什麼？（管理開啟簽約對象視窗可新增或刪除，儲存只在個人身分頁面出現）

回覆：

## 通知中心 `A-notification-center`（待審 2 條：pass 1／doubt 1／未先審 0） ⚠️

- [pass] `jgb/A/notification-mark-read-out-of-range` 篩選後頁碼超出範圍會自動跳回第一頁嗎？（不會，只會顯示空的通知清單）
- [doubt] `jgb/A/notification-mark-read-navigate` 點擊通知列表項目會發生什麼？（前往原連結，並帶上標記已讀的依據；訊息類通知不換頁） —— 句序 2：「每則通知會顯示所屬物件名稱、通知來源使用者姓名」這個絕對句漏了例外：物件名稱和來源姓名都包在 estate_title 非空的條件裡，沒有物件的通知兩者都不顯示。另外這句是在講列表長什麼樣，沒有回答「點擊會發生什麼」

回覆：

## 通知收件設定與發送報表（通知收件信箱最多再加 3 組） `A-notification-settings`（待審 4 條：pass 3／doubt 1／未先審 0）

- [pass] `jgb/A/notification-settings-extra-emails` 通知收件信箱最多能加幾組？（每個通知分類最多再加 3 組電子信箱）
- [pass] `jgb/A/notification-settings-categories` 通知收件設定有哪些分類？（合約、帳務、修繕、訂閱、房東管理，另有限定開放的加盟分潤報表）
- [pass] `jgb/A/notification-settings-save` 通知收件設定改完怎麼儲存？（至少要有一個分類填了自訂信箱，儲存鍵才會啟用）
- [doubt] `jgb/A/notification-settings-report-buttons` 「發送報表」「多團隊合併報表」按鈕是做什麼的？（限加盟分潤報表分類，多團隊合併僅限特定團隊） —— 句序 1：標題問按鈕「是做什麼的」，講法也有「分潤報表怎麼看」，但內文只說按了會開啟燈箱；沒寫出這個視窗實際的用途：選起始日和終止日，再把該區間的報表寄到信箱。所以標題和講法都答不到

回覆：

## 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊） `B-team-profile`（待審 2 條：pass 1／doubt 1／未先審 0） ⚠️

- [pass] `jgb/B/team-signer-profile-switch` 怎麼在多組簽約資訊之間切換？（頁面上方有可切換的分頁列，超過 5 組時另外多出「所有團隊」下拉選單）
- [doubt] `jgb/B/team-signer-personal-info` 簽約資訊卡「個人資訊」區塊只有個人團隊看得到，要填什麼？（姓氏、名稱、身分證字號、Email、手機、戶籍地址、通訊地址必填；身分證正反面與其他附件選填） —— 句序 4：標題講的是只有個人團隊看得到的「個人資訊」區塊，但第 4、5 句寫的是公司資訊的地址欄位和社宅團隊的經紀人／管理人員地址。這兩塊只有法人或社宅團隊看得到，和標題不符，等於把另一條細目 team-signer-address-groups 的內容混了進來

回覆：

## 成員列表（邀請、角色、成員名下資料） `B-member-list`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/B/member-seat-limit` 邀請成員有名額上限嗎？（依訂閱方案而定；已訂閱達上限要升級方案，未訂閱要先訂閱）
- [pass] `jgb/B/member-list-role-inline-change` 成員列表可以直接改成員的角色嗎？（一般成員那一列可以用角色下拉選單直接切換；擁有者與自己那一列、或沒有編輯權限時選單會鎖住）
- [pass] `jgb/B/member-role-edit-reset` 編輯角色時的「重設條件」按鈕是做什麼的？（把所有權限勾選全部清空）

回覆：

## 大房東列表與授權物件 `B-biglandlord-list`（待審 3 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/B/biglandlord-authorize-apply-step` 授權物件頁移除物件後，為什麼要按「套用」才會生效？（按紅色 X 移除只是待處理狀態，按套用才真的移除，按恢復可以取消這次變更）
- [pass] `jgb/B/biglandlord-seat-limit` 大房東名額有上限嗎？（目前大房東列表頁的「新增大房東」沒有名額檢查）
- [hold] `jgb/B/biglandlord-escrow-owner` 大房東列表上方的「所有權人／轉租人」是做什麼用的？（記錄代管物件的所有權人或轉租人資料，加快編輯合約速度） —— 業主已裁列下個計畫刪除，⛔ 標已審（先審判定：doubt）

回覆：

## 大房東報表 `B-biglandlord-report`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/B/biglandlord-report-overview` 大房東報表可以看到什麼？（依大房東列出所屬物件、出租中物件與執行中合約租金總額）
- [pass] `jgb/B/biglandlord-report-community-rate` 大房東報表可以依社區細看嗎？（報表清單有「社區」欄，幣別不同時細節頁會顯示匯率）
- [doubt] `jgb/B/biglandlord-report-permission` 誰看得到大房東報表？（需要「查看大房東報表」的角色權限） —— 句序 1：「才不會在選單整理時被拿掉」是在描述程式的 unset 動作，屬於實作用語；而且列出的來源 UserController.php 只有權限名稱，選單的顯示規則其實在 app/Role.php，另外選單項目只給法人和社宅團隊（allow_role_key）這個身分條件也沒寫

回覆：

## 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」） `B-advanced-settings`（待審 18 條：pass 16／doubt 2／未先審 0）

- [pass] `jgb/B/advance-discount-items` 進階設定的「優惠項目」是給誰用的？（只有部分特定合作團隊才看得到，可設定折扣套用在租金費用上）
- [pass] `jgb/B/advance-late-fee` 進階設定的「延遲金設置」怎麼計算？（只有特定合作團隊看得到，公式是租金 × (逾期天數 - 緩衝天數) × 延遲金%）
- [pass] `jgb/B/advance-additional-terms` 「預設補充條款」怎麼設定？（最多可以設 3 組，編輯合約時直接選用）
- [pass] `jgb/B/advance-device-binding` 怎麼綁定智能裝置廠商？（輸入裝置廠商帳號密碼完成綁定，之後可在 JGB 平台管理裝置）
- [pass] `jgb/B/advance-fee-items-merge` 自訂費用項目可以合併嗎？（可以把多個品項併入其中一個既有品項，合併後無法回復）
- [pass] `jgb/B/advance-payment-cycle-discount` 進階設定的「繳費週期優惠」是給誰用的？（只有特定合作團隊才看得到，選比月繳更長的繳費週期就有折扣）
- [pass] `jgb/B/advance-notification-locale` 「Email 通知語系」在哪設定、誰看得到？（只有法人房東或社宅團隊看得到，決定代發通知信的預設語系）
- [pass] `jgb/B/advance-timezone` 「時區設定」會影響哪些通知？（只有法人房東或社宅團隊看得到，改變排程通知的發送時間）
- [pass] `jgb/B/advance-settlement-currency` 「結算幣別」是做什麼用的？（只有法人房東或社宅團隊看得到，把大房東報表的多幣別合約統一結算成一種幣別）
- [pass] `jgb/B/advance-device-binding-visibility` 為什麼進階設定看不到「裝置管理」區塊？（訂閱方案要生效中，且不能是免費方案）
- [pass] `jgb/B/advance-dedicated-account` 「房東專屬帳號」是做什麼用的？（只有法人房東或社宅團隊看得到；顯示在團隊首頁，且第一次儲存後不能自行修改，要洽 JGB 客服）
- [pass] `jgb/B/advance-auto-publish-unpublish` 招租廣告可以自動刊登或自動下架嗎？（部分特定合作團隊可以：合約到期日前 N 天自動刊登，簽約後自動下架）
- [pass] `jgb/B/advance-contract-label` 「合約管理」的標籤設定跟物件的標籤設定是同一個嗎？（不是，這是合約專用的另一組標籤）
- [pass] `jgb/B/advance-sales-item-code` 「銷貨單品項代號對應」是做什麼用的？（只有特定團隊才有，設定匯出「M 化銷貨單」時每個品項要帶的產品代號）
- [pass] `jgb/B/advance-community-labels` 「社區管理」的城市／區域／位置設定是做什麼？（只有特定合作團隊看得到，用來建立社區可選用的城市、區域、位置標籤）
- [pass] `jgb/B/advance-short-lease-approval` 進階設定的「短租期核可流程」是做什麼的？（只有特定合作團隊看得到；租期少於設定天數時，合約要先簽核通過才會發出邀請給租客）
- [doubt] `jgb/B/advance-fee-items` 帳單的「自訂費用項目」怎麼設定？（分收入類／支出類，必填性質與自定義名稱，會科品項代號選填） —— 句序 1：講法「費用項目可以合併嗎」在本條三句裡都答不到（合併寫在另一條 advance-fee-items-merge）
- [doubt] `jgb/B/advance-custom-label` 「標籤設定」是做什麼用的？（幫物件加自訂標籤，單個標籤上限 18 字元） —— 句序 3：說明文字寫 18 字元（9 個字），但程式實際不分中英文，一律只收 9 個字元，打英文也收不到 18 個；標題和第 3 句寫的「18 字元」跟程式行為不符

回覆：

## 租客列表（當前租客／封存、準時繳租率、信用評價） `B-tenant-list`（待審 4 條：pass 3／doubt 1／未先審 0）

- [pass] `jgb/B/lessee-crud` 租客列表可以新增、匯入、匯出租客嗎？（個人房東與法人房東可以手動新增、Excel 匯入與匯出；社宅團隊只能匯出）
- [pass] `jgb/B/lessee-notification-toggle-effect` 租客的通知開關關閉後會怎樣？（Email 與手機的開關分開，關掉哪一個就停哪一種通知）
- [pass] `jgb/B/lessee-list-columns-by-role` 社宅團隊的租客列表欄位有什麼不一樣？（沒有「會員註冊」「免註冊合約」與操作選單，「註冊合約」欄改叫「所屬總合約」）
- [doubt] `jgb/B/lessee-bulk-notify` 租客列表勾選多筆租客後可以做什麼？（特定合作團隊可以批次發送通知，其他團隊沒有這個批次操作） —— 句序 1：批次操作列固定黏在列表上方，不在「畫面下方」。另外，非特定合作團隊的列表根本沒有勾選框，並不是「勾選後沒有批次列」

回覆：

## 社區列表與建立 `C-community-list`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/C/community-delete-requires-empty` 社區可以刪除嗎？（社區底下不能有任何物件才能刪除，且刪除後無法復原）

回覆：

## 社區資料編輯（基本資料、照片與描述、介紹與交通） `C-community-edit`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/C/community-edit-basic-fields` 社區基本資料要填什麼？（社區名稱、詳細地址與對外顯示地址、建築類型、總樓層、屋齡）

回覆：

## 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） `C-community-estates`（待審 5 條：pass 3／doubt 2／未先審 0） ⚠️

- [pass] `jgb/C/community-estates-category-switch` 社區底下的物件清單怎麼切換總覽／招租／買賣？（欄位標題會跟著切換內容改變）
- [pass] `jgb/C/community-estates-add-batch-copy` 怎麼在社區底下新增物件？（新增／批次新增／複製現有物件，受物件數量上限限制）
- [pass] `jgb/C/community-estates-pagination` 社區物件清單每頁筆數可以調整嗎？（30／60／90項）
- [doubt] `jgb/C/community-estates-overview-card` 社區底下物件頁最上方顯示什麼？（招租廣告、買賣廣告、目前空置數量、類型、屋齡、本月應收與已收金額） —— 句序 3：卡片右上角的選單只在電腦版出現。手機版沒有這個選單，改成在卡片下方顯示「編輯社區」「預覽廣告頁」「刪除社區」，標籤也不同。絕對句漏了手機版例外
- [doubt] `jgb/C/community-estates-extra-tabs` 社區底下有差額發票、投報率頁籤嗎？（依團隊是否開通該功能才會出現；投入成本與投報率是同一個開關，大房東與沒有帳單查看權限的成員看不到） —— 句序 標題：標題寫兩種頁籤都「依團隊是否開通」，但差額發票頁籤看的是單一社區自己的開關，內文也寫「該社區開通」，標題和內文互相矛盾

回覆：

## 社區公開頁（社區詳情、社區總表） `C-community-public-page`（待審 4 條：pass 4／doubt 0／未先審 0）

- [pass] `jgb/C/community-show-content` 社區公開頁（社區廣告）顯示什麼？（基本資訊、鄰近捷運、社區介紹、刊登中物件）
- [pass] `jgb/C/community-show-price-range` 社區公開頁最上方顯示什麼價格區間？（租賃金額區間、售價金額區間）
- [pass] `jgb/C/community-show-share` 社區公開頁怎麼分享？（分享燈箱或手機分享選單、查看所有物件連結）
- [pass] `jgb/C/community-show-editor-nav` 在社區廣告頁可以直接跳到編輯社區、社區詳情或社區總表嗎？（只有具備編輯物件權限的使用者看得到這個選單）

回覆：

## 物件列表與篩選 `C-estate-list`（待審 10 條：pass 6／doubt 4／未先審 0） ⚠️

- [pass] `jgb/C/estate-list-add-must-pick-community` 物件總表怎麼新增物件？（新增與複製現有物件都要先經過社區選擇畫面，目前沒有批次新增入口）
- [pass] `jgb/C/estate-list-counter-and-limit` 物件總表標題下方顯示什麼？（目前物件總數、尚可新增數量）
- [pass] `jgb/C/estate-list-keyword-search` 物件總表關鍵字搜尋可以查什麼？（案名、地址、租客、物件ID、手機、信箱）
- [pass] `jgb/C/estate-list-pagination` 物件總表每頁筆數可以調整嗎？（30／60／90項）
- [pass] `jgb/C/estate-list-filters-space-type-and-others` 物件總表篩選還有哪些條件？（空間類型多選、「更多」：VR、有電梯、可開伙、可養寵物）
- [pass] `jgb/C/estate-list-category-switch` 物件總表怎麼切換總覽／招租／買賣？（三種分類切換）
- [doubt] `jgb/C/estate-list-filters` 物件總表有哪些進階篩選條件？（縣市行政區、經理人、大房東、社區、捷運、格局、建築類型、即時合約狀態、合約到期日、招租廣告狀態、租金與面積(坪)範圍、標籤） —— 句序 3：「篩選結果：目前範圍／總筆數」只在寬螢幕（lg）顯示；窄螢幕看不到，手機版篩選區塊也沒有這一行。絕對句漏了手機版例外
- [doubt] `jgb/C/estate-list-batch-actions` 物件總表可以批次操作嗎？（匯出物件、新增批次帳單、批次刊登／取消刊登招租廣告、刪除；批次取消刊登失敗時不會顯示任何提示） —— 句序 1：個人房東、大房東、租客在物件總表沒有勾選框，完全不能批次操作。句子只寫「依權限」，漏了身分例外
- [doubt] `jgb/C/estate-status-affects-actions` 物件狀態會影響哪些功能？（未刊登／刊登中／洽談中／租約中，各自能做的操作不同） —— 句序 1：這條把幫助中心的舊四態分類（文件寫「合約中」）和程式標籤「租約中」拼在一起。現行程式的合約狀態貼紙只有 無合約／洽談中／租約中，刊登狀態（未刊登／刊登中）是另一個獨立維度；四態互斥的狀態表在後端是被註解掉的舊碼。各狀態可做的操作也只有文件來源，找不到現行程式對應
- [doubt] `jgb/C/estate-list-sort-remembers-last` 物件總表怎麼排序？（排序選項由系統提供，電腦版會記住上次選的排序方式） —— 句序 3：「窄螢幕不會自動帶入上次的排序」與程式不符。進入頁面時一律用 estatesList 這個鍵讀回排序，不看螢幕寬度，所以窄螢幕也會帶入在寬螢幕選過的排序；窄螢幕只是不會把自己的選擇存成 estatesList。分界是 576px，也不是「電腦版」

回覆：

## 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） `C-estate-edit`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/C/estate-edit-basic-space-type` 物件基本資料的空間類型、用途、格局要怎麼填？
- [pass] `jgb/C/estate-edit-building-transcript-general` 一般物件建物謄本可以填什麼？（土地標的清冊、坐落基地、稅籍編號、專有部分、主建物、附屬建物，皆非必填）
- [doubt] `jgb/C/estate-edit-facilities` 物件附設傢俱怎麼設定？（依用途與格局分區加入家電、傢俱、自訂項目，數量0不顯示在廣告頁） —— 句序 1：「商用」和「有建物」這兩個標題底下只有必填的「座位數」，不是設定家電、傢俱的地方。商用物件的傢俱在「辦公空間」區塊，店面在「店面空間」區塊。「每個區塊都能設定家電、傢俱」不成立

回覆：

## 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實） `C-rent-listing`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/C/estate-rent-detail-price-and-tax` 招租詳情要填哪些金額相關欄位？（面積、幣別、每月租金；特定合作團隊另有營業稅：應稅／零稅率／免稅）

回覆：

## 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） `C-estate-dashboard`（待審 9 條：pass 7／doubt 2／未先審 0）

- [pass] `jgb/C/estate-dashboard-entry-and-groups` 物件儀表板進去預設是哪個分頁？（一般預設招租表現，大房東直接進合約歷程；大房東看不到「限管理者查看」分頁群組）
- [pass] `jgb/C/estate-dashboard-rent-performance` 招租表現分頁顯示什麼？（空置天數、廣告瀏覽次數、帳務表現、合約歷程與修繕紀錄摘要）
- [pass] `jgb/C/estate-dashboard-contracts-history` 物件儀表板的合約歷程顯示哪些欄位？（一般房東：狀態／簽約類型／物件／承租人／租期／是否通知；社宅房東：合約名稱／承租人／租期）
- [pass] `jgb/C/estate-dashboard-bills-tabs` 物件儀表板的帳務收支有哪些子頁籤？（總收支、統計報表）
- [pass] `jgb/C/estate-dashboard-repair-status-flow` 物件儀表板修繕紀錄怎麼呈現？（申請修繕→安排修繕→完成修繕→結單四狀態）
- [pass] `jgb/C/estate-dashboard-monthly-report-upload` 每月報表／每月對帳單怎麼上傳？（PDF、10MB上限，可批次指定多個物件，同月重傳會覆蓋舊檔）
- [pass] `jgb/C/estate-dashboard-top-cards` 物件儀表板最上方顯示哪三張卡？（物件資訊、招租廣告、買賣廣告；編輯捷徑需要新增物件權限）
- [doubt] `jgb/C/estate-dashboard-attachments-vs-contract-attachments` 「附件清單」跟「合約附件」差在哪？（附件清單可上傳 JPG／PNG／PDF、有儲存空間上限，下載不限身分但只有代理人且有新增物件權限才能刪除；合約附件是租賃法定文件的固定清單） —— 句序 1：「加價購」按鈕在現行程式裡已被註解掉，畫面上不存在；講法「附件清單空間不夠怎麼辦」會因此被答成一條走不到的路（另外，「租賃法定文件」在畫面上沒有來源，畫面原文是「如有以下附件，可上傳圖片做補充，以避免日後爭議」）
- [doubt] `jgb/C/estate-dashboard-runnings-vs-memos` 「房東流水帳」跟「物件記事本」差在哪？（流水帳要記收入/支出金額，記事本只是純文字備註） —— 句序 0（標題）：標題說記事本「只是純文字備註」，但第 2 句與程式都顯示記事本可以附加附件，標題跟內文互相矛盾

回覆：

## 單一物件廣告頁（招租） `C-estate-public-page`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/C/estate-house-info-card` 物件廣告頁的資料卡片顯示什麼？（地址／社區名稱、租金元/月與含哪些費用、建築類型與樓層或格局、商用類的空間類型與座位數、面積、物件平面圖）

回覆：

## 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） `C-team-storefront`（待審 5 條：pass 2／doubt 3／未先審 0） ⚠️

- [pass] `jgb/C/team-public-page-purpose` 房東對外首頁（招租店舖）是什麼？（公開展示聯絡資訊、簡介與所有刊登中物件，供分享給潛在租客）
- [pass] `jgb/C/team-public-page-recruitment` 多團隊招募頁和一般招租店舖有什麼不同？（沒有指定住宅或商用時自動轉址到住宅、只顯示招租、不顯示社區篩選、每頁預設 10 筆）
- [doubt] `jgb/C/team-public-page-edit-and-banner` 招租店舖上可以直接編輯哪些內容？（封面照片、大頭照、姓名、自我介紹，會連動帳號資訊） —— 句序 1：程式裡能編輯的欄位跟句子不符。個人房東的「姓名」沒有 editable，只有自我介紹可以改；團隊身分能編輯的是「團隊名稱」「經理人證號」「租賃管理員證號」「公司電話」「公司Email」「團隊介紹」，沒有「姓名／自我介紹」這兩個標籤。句子也漏了權限條件：必須同時符合 is_admin 和 edit_role 權限才能編輯。這句只照幫助中心寫，跟現行程式衝突
- [doubt] `jgb/C/team-public-page-filter-and-view` 招租店舖怎麼篩選物件？（鄉鎮區或捷運、類型與格局，可切換小圖示／大圖示／條列式；每頁筆數 30／60／90，預設 30） —— 句序 1：「鄉鎮/區或捷運」「類型與格局」這兩個群組標題只出現在 id="asideFilter" 的 Lightbox2 裡，而整個 src 都沒有任何地方打開這個燈箱，是走不到的畫面。現行實際的篩選列是 PublicSearchBlock／PublicSearchBlockM，內容有縣市、區域、社區、捷運、類型、房數、建築類型、租金、面積、其他，並不是「兩組」
- [doubt] `jgb/C/team-public-page-share` 招租店舖怎麼分享？（可分享至FB、Line、LinkedIn或複製連結，分享的是目前頁面的網址） —— 句序 1：絕對句漏了手機裝置的例外：在 Android／iOS 裝置上，如果瀏覽器支援 navigator.share，會直接叫出系統原生的分享選單，不會出現 FB／Line／LinkedIn／複製連結的燈箱

回覆：

## 方案、價格與免費試用 `I-pricing`（待審 1 條：pass 0／doubt 1／未先審 0） ⚠️

- [doubt] `jgb/I/pricing-trial-plan-landing-page` 體驗方案介紹頁講什麼？（每月費用試算、體驗方案資格需求、客戶見證、免費試用／免費諮詢按鈕） —— 講法：講法「深入了解企業方案後看到什麼」對應不到這條細目：「深入了解企業方案」連到的是預約 demo 表單，不是體驗方案介紹頁，進到介紹頁的入口是「查看體驗方案」。這句講法也跟同粗目的 pricing-enterprise-plan-offer 矛盾

回覆：
