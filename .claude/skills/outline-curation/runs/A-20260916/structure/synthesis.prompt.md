你是知識大綱結構的合成者。輸入＝同一批項目在三個角度下各自的結構提議。任務：合成一份最終提議。
合成規則：三份提議一致處直接採用；分歧處擇一並把未採用的寫進 rejected_alternatives（alternative 一句描述、reason 一句理由）。
⛔ 不得引入三份提議都沒有的細目 id；⛔ 不得改粗目；⛔ 不讀取任何檔案或工具。

## 粗目（受眾 jgb，固定，⛔ 不得增刪改）
- A：帳號與身分
- B：團隊、人員與大房東
- C：社區與物件
- D：租約（含委託約子題）
- E：帳務（含發票、收款金流、抄表）
- F：修繕
- G：裝置（IoT）
- H：幫助中心
- I：方案與導入

## 輸出定義
fines：細目清單。每一細目＝一個可獨立回答的主題；`id` 為 `jgb/<粗目碼>/<slug>`，slug 只用小寫英數與連字號且與 `slug` 欄相同；`merge_of` 列出構成此細目的輸入項目 id（一個或多個）；`split_from` 列出被拆出的來源項目 id（拆分時填，否則空陣列）；`moved_from` 首跑為空陣列；`reason` 一句話說明切分依據。
id_map：每一個輸入項目 id 必須出現至少一次（op 為 keep／merge／split／move，old＝該項目 id、new＝細目 id）；op=new 的列 old＝該新材料的項目 id（tmp:kb:*／tmp:draft:*），⛔ 不是 null。
target_user：每一細目必填，值域 prospect／property_manager；兩者共用的細目明列兩者，不得空陣列。
coarses：照抄固定粗目表（id 與 title），⛔ 不得增刪改。
同受眾細目互斥：一個主題只能有一個細目；相似者合併，不同層級者以另見處理而非重複。
歸位判準（跨粗目命題只能歸一處，依下列定義判）：錢怎麼算歸帳務、錢怎麼進來歸帳務底下的收款金流子題；由合約條款決定的歸租約、出現在帳單列上的歸帳務；物件本身的屬性歸社區與物件、由合約驅動的物件狀態歸租約；通知是投遞管道，歸它所通知的那個領域，⛔ 不自成細目。
講法唯一：同一句講法只掛一個細目；同一命題若答案因受眾而異，各受眾各一細目（不同 id），⛔ 不得同時存在中立細目與受眾版細目。
⚠️ 本次為擴充模式，**只補一架（A）**：候選項目分兩種——`tmp:canon:*`（A 架既有細目）與 `tmp:kb:*`／`tmp:draft:*`（本次新材料）；其餘八架的既有細目**不在候選之列**（不得引用、不得討論）。
op（本次必填）：既有細目（`tmp:canon:*`）一律 `op=keep` 且 `id` 不變，除非你判定它該與其他項目 `merge` 或被 `split`；新材料成為新細目一律 `op=new`。
fines：本次每一筆 `coarse_id` 必須等於 `A`，`id` 必須為 `jgb/A/<slug>`。
out_of_shelf：材料若明顯不屬於本架 ⇒ 列在此陣列（`{id, suggested_shelf, why}`），⛔ 不要勉強提成細目；此類項目不需出現在 id_map。
回覆格式：只輸出一個 JSON 物件（符合下方 schema），不加任何說明文字、不加 Markdown 圍欄。

## schema
{"type": "object", "properties": {"angle": {"type": "string"}, "coarses": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}}, "required": ["id", "title"], "additionalProperties": false}}, "fines": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "coarse_id": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}, "title": {"type": "string"}, "slug": {"type": "string"}, "merge_of": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/A/account-registration", "tmp:kb:3348", "tmp:kb:3349", "tmp:kb:3350", "tmp:kb:3354", "tmp:kb:3435", "tmp:kb:3436", "tmp:kb:3437", "tmp:kb:3869", "tmp:kb:3871", "tmp:kb:3964", "tmp:kb:3965", "tmp:kb:3966", "tmp:kb:3967", "tmp:kb:3968", "tmp:kb:3969", "tmp:kb:3971", "tmp:kb:3972", "tmp:kb:3975", "tmp:kb:3978", "tmp:kb:3980", "tmp:kb:4561", "tmp:draft:1", "tmp:draft:2", "tmp:draft:3", "tmp:draft:4", "tmp:draft:5", "tmp:draft:6", "tmp:draft:7", "tmp:draft:8", "tmp:draft:9", "tmp:draft:10"]}}, "split_from": {"type": "array", "items": {"type": "string", "enum": ["tmp:canon:jgb/A/account-registration", "tmp:kb:3348", "tmp:kb:3349", "tmp:kb:3350", "tmp:kb:3354", "tmp:kb:3435", "tmp:kb:3436", "tmp:kb:3437", "tmp:kb:3869", "tmp:kb:3871", "tmp:kb:3964", "tmp:kb:3965", "tmp:kb:3966", "tmp:kb:3967", "tmp:kb:3968", "tmp:kb:3969", "tmp:kb:3971", "tmp:kb:3972", "tmp:kb:3975", "tmp:kb:3978", "tmp:kb:3980", "tmp:kb:4561", "tmp:draft:1", "tmp:draft:2", "tmp:draft:3", "tmp:draft:4", "tmp:draft:5", "tmp:draft:6", "tmp:draft:7", "tmp:draft:8", "tmp:draft:9", "tmp:draft:10"]}}, "moved_from": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}, "target_user": {"type": "array", "items": {"type": "string", "enum": ["prospect", "property_manager"]}}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["id", "coarse_id", "title", "slug", "merge_of", "split_from", "moved_from", "reason", "target_user", "op"], "additionalProperties": false}}, "id_map": {"type": "array", "items": {"type": "object", "properties": {"old": {"anyOf": [{"type": "string", "enum": ["tmp:canon:jgb/A/account-registration", "tmp:kb:3348", "tmp:kb:3349", "tmp:kb:3350", "tmp:kb:3354", "tmp:kb:3435", "tmp:kb:3436", "tmp:kb:3437", "tmp:kb:3869", "tmp:kb:3871", "tmp:kb:3964", "tmp:kb:3965", "tmp:kb:3966", "tmp:kb:3967", "tmp:kb:3968", "tmp:kb:3969", "tmp:kb:3971", "tmp:kb:3972", "tmp:kb:3975", "tmp:kb:3978", "tmp:kb:3980", "tmp:kb:4561", "tmp:draft:1", "tmp:draft:2", "tmp:draft:3", "tmp:draft:4", "tmp:draft:5", "tmp:draft:6", "tmp:draft:7", "tmp:draft:8", "tmp:draft:9", "tmp:draft:10"]}, {"type": "null"}]}, "new": {"type": "string"}, "op": {"type": "string", "enum": ["keep", "split", "merge", "move", "new"]}}, "required": ["old", "new", "op"], "additionalProperties": false}}, "out_of_shelf": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string", "enum": ["tmp:canon:jgb/A/account-registration", "tmp:kb:3348", "tmp:kb:3349", "tmp:kb:3350", "tmp:kb:3354", "tmp:kb:3435", "tmp:kb:3436", "tmp:kb:3437", "tmp:kb:3869", "tmp:kb:3871", "tmp:kb:3964", "tmp:kb:3965", "tmp:kb:3966", "tmp:kb:3967", "tmp:kb:3968", "tmp:kb:3969", "tmp:kb:3971", "tmp:kb:3972", "tmp:kb:3975", "tmp:kb:3978", "tmp:kb:3980", "tmp:kb:4561", "tmp:draft:1", "tmp:draft:2", "tmp:draft:3", "tmp:draft:4", "tmp:draft:5", "tmp:draft:6", "tmp:draft:7", "tmp:draft:8", "tmp:draft:9", "tmp:draft:10"]}, "suggested_shelf": {"type": "string"}, "why": {"type": "string"}}, "required": ["id", "suggested_shelf", "why"], "additionalProperties": false}}, "rejected_alternatives": {"type": "array", "items": {"type": "object", "properties": {"alternative": {"type": "string"}, "reason": {"type": "string"}}, "required": ["alternative", "reason"], "additionalProperties": false}}}, "required": ["angle", "coarses", "fines", "id_map", "out_of_shelf", "rejected_alternatives"], "additionalProperties": false}

## 輸入項目（32 筆，原序列舉）
### tmp:canon:jgb/A/account-registration
標題：怎麼註冊帳號（含驗證碼通知）
內容：註冊很快：到 JGB 網站點「註冊」，輸入 Email 收驗證碼，填基本資料就完成；也可以用 Facebook、Gmail、LINE 第三方帳號註冊，系統會一併建立 Email 登入。 一個帳號同時可有房東與租客身分，手機號碼作輔助登入。 租客不一定要自己註冊，房東建立合約時輸入租客 Email 或手機發出簽約邀請，租客也能從電子合約完成註冊。

### tmp:kb:3348
標題：免註冊 註冊 租客 差異
內容：註冊租客與免註冊租客的差異：

【註冊租客】
- 可透過 email 和密碼登入系統
- 可在系統內查看合約、帳單
- 可直接收到系統通知

【免註冊租客】
- 無法登入系統查看資料
- 需透過「人員管理」進行 email 驗證後才能收到通知
- 帳單以附件形式寄送，檔案密碼為公司統一編號
- 管理者需每月手動協助到帳（較麻煩）

建議盡量引導租客使用註冊帳號，以實現自動化管理。

### tmp:kb:3349
標題：email 大小寫 帳號 不同
內容：JGB 系統將 email 作為帳號識別，大小寫不同會被視為不同帳號。

常見問題：
- 邀請大房東時 email 大小寫不正確，導致邀請失敗
- 租客用不同大小寫的 email 註冊，導致看不到合約或帳單
- 合約發送的 email 與租客登入的帳號不一致

請務必確認 email 完全一致（包含大小寫）。

### tmp:kb:3350
標題：簡訊 驗證碼 收不到
內容：收不到簡訊驗證碼的可能原因：
1. 訊號不佳或發生堵塞，請稍後再次重發
2. 手機安裝了來電攔截 APP（如 Whoscall），可能將驗證簡訊攔截
3. 手機同時有多款簡訊 APP（Google Messenger、FB Messenger、品牌內建等），僅有一款能接收簡訊，可能在更新時設定異常
4. 填寫了錯誤的手機號碼或 email

建議先確認手機號碼正確，檢查攔截設定後再次重發驗證碼。

### tmp:kb:3354
標題：身分證 必填 租賃契約 上傳
內容：依「住宅租賃定型化契約應記載及不得記載事項」，合約需記載當事人的統一編號（身分證明文件編號），但並未強制要求上傳身分證影本，僅為備存形式。

房東和房客互相核對身分證是簽約時的必要步驟，但系統上此欄位非強制填寫。影本上可註記「僅限房屋租賃簽約使用」以保護個資。

若發現租客未上傳身分證，管理者可退出簽名、取消合約，重新寄送給租客。

### tmp:kb:3435
標題：註冊帳號 建立流程
內容：JGB 帳號註冊以 Email 為主路徑：1. 進入註冊頁輸入 Email 並通過機器人驗證；2. 收 Email 驗證碼完成信箱驗證（驗證碼效期 5 分鐘，訊息開頭有三個英文字母的識別碼，請輸入與畫面識別碼相符那封信裡的碼）；3. 設定密碼；4. 選擇身分（房東/租客）；5. 綁定手機（簡訊驗證）——這一步可先跳過，之後再到帳號設定補綁。收到合約邀請的租客用邀請信中的連結進入註冊即可。

### tmp:kb:3436
標題：忘記密碼 無法登入
內容：忘記密碼：在登入頁點「忘記密碼」，選擇用 Email 或手機簡訊接收驗證碼（擇一），輸入驗證碼通過後即可直接設定新密碼。注意驗證碼輸錯三次會失效，需重新取得。若連當初註冊用的信箱都不確定：登入頁有「忘記帳號」，以手機簡訊驗證後系統會顯示打星號的信箱提示；沒有綁定手機的話請聯繫客服協助查詢。

### tmp:kb:3437
標題：Email 變更 手機驗證
內容：帳號的 Email 無法自行變更：帳號設定頁的 Email 欄位是唯讀的，如需更換請聯繫 JGB 客服，走資料異動申請書流程由後台處理。手機號碼分兩種情況：帳號還沒綁定手機時，可到帳號設定「前往綁定」自助綁定（簡訊驗證）；已綁定要更換號碼則同樣屬後台作業，請透過資料異動申請書申請。申請書需載明帳號識別（信箱或手機）、修改前後值與相關合約 ID，經公司用印後寄至 客服信箱（官網）。

### tmp:kb:3869
標題：租客看不到合約 登入信箱不符
內容：租客說收到了邀請、也註冊登入了，卻看不到合約——常見原因是「發送信箱」與「登入帳號」不一致：邀請寄到 A 信箱，但租客用 B 信箱（或用其他方式如 SSO）註冊登入，系統無法把合約對到他的帳號。排查方式：請租客確認實際登入的帳號信箱，與合約上填的發送信箱是否相同；不一致時，把合約退回修改為租客實際登入的信箱後重新發送邀請即可。

### tmp:kb:3871
標題：驗證信 驗證碼收不到 排查
內容：租客註冊或簽約時收不到驗證信/驗證碼，依序排查：一、檢查垃圾信件匣與促銷分類；二、確認信箱/手機號碼輸入正確（多一個空格也會失敗）；三、簡訊可能被手機的攔截程式擋下，檢查攔截紀錄；四、稍候一兩分鐘再點重新發送，避免連續觸發限制。都試過仍收不到，記下租客的帳號與時間點聯繫客服查發送紀錄。

### tmp:kb:3964
標題：驗證碼一直失敗 重發 新舊碼
內容：租客輸入驗證碼連續失敗，最常見的原因是重複按了「重新取得」：每次重新取得都會產生新的驗證碼、舊碼立即失效，手上那封訊息裡的碼可能已經不是最新的。排查方式：簡訊或信件開頭有三個英文字母的識別碼，請租客核對畫面上顯示的識別碼，只輸入「識別碼一致的那一封」裡的驗證碼。驗證碼效期 5 分鐘、輸錯三次會失效；重發有 120 秒冷卻，冷卻中按重發不會發出新訊息。若三次失效，等冷卻結束重新取得一組再輸入即可。

### tmp:kb:3965
標題：收不到驗證簡訊 改用信箱註冊
內容：租客收不到註冊或合約的驗證簡訊時，依序排查：一、核對手機號碼是否正確；二、請租客檢查垃圾簡訊匣；三、確認沒有在短時間內重複按重發（120 秒冷卻內不會發出新簡訊、每日有則數上限）。仍收不到就改走 Email：JGB 註冊本來就以 Email 為主路徑，把註冊頁連結提供給租客、請租客用信箱完成註冊即可；手機可之後再補綁。合約邀請也可以改用 Email 重新發送。

### tmp:kb:3966
標題：註冊顯示已註冊 該怎麼辦
內容：註冊時出現「此帳號已註冊」或「此手機已註冊」，代表該信箱或手機已經有 JGB 帳號了——不要再嘗試註冊或另開新帳號。分兩種情況處理：如果是本人之前註冊過，改走登入，忘記密碼可在登入頁自助重設；如果那個號碼或信箱是被別人（例如前租客、同事的舊帳號）占用，需要走解綁申請由客服後台處理，解綁後才能重新綁定。

### tmp:kb:3967
標題：LINE 快速登入 跳到註冊 登不進去
內容：租客用 LINE 快速登入卻被帶到註冊畫面，原因是：LINE 快速登入只認「當初用 LINE 註冊」的帳號；用帳號密碼註冊的帳號沒有 LINE 綁定，目前也沒有事後補綁的功能，所以系統找不到對應帳號、只能導去註冊。解法很單純：請租客改用帳號密碼登入即可，不需要重新註冊。另外在 LINE 內建瀏覽器裡開啟登入頁偶爾會有狀況，可改用手機的一般瀏覽器再試。

### tmp:kb:3968
標題：登入成功 看不到合約帳單電表
內容：租客登入成功卻看不到自己的合約、帳單或電表，照順序排查：一、確認左上角身分選單已切到「租客」身分——租客資料只在租客身分下顯示；二、確認登入的信箱是「當初註冊時的確切寫法」——寫法不同可能登進另一個同名帳號，那個帳號名下沒有合約，自然什麼都看不到；三、都確認過仍看不到，提供合約編號或物件名稱，系統可以查這份合約的租客帳號狀態（是否已註冊、邀請信箱與登入帳號是否一致）來判斷是不是登錯帳號。

### tmp:kb:3969
標題：忘記當初註冊的信箱 查詢帳號
內容：使用者忘記當初用哪個信箱註冊時：登入頁有「忘記帳號」功能，以手機簡訊驗證身分後，系統會顯示打星號的信箱提示（例如 s***＠hotmail.com），通常足以想起是哪個信箱。如果帳號沒有綁定手機、無法用這個功能，請聯繫 JGB 客服協助查詢，並準備合約或物件資訊供身分核對。

### tmp:kb:3971
標題：註冊名字與證件不同 改名 藍字
內容：租客註冊時填的名字與證件不同，不需要重新註冊。分兩種情況：合約還沒完成簽署——請租客到「帳號設定」的基本資訊自行改名，簽署時合約上的藍字（由帳號資料帶入的欄位）就會是新名字；合約已完成雙方簽署——合約上的資料是定案快照，不會跟著帳號連動，而且簽署完成後帳號姓名會被鎖定無法自改，這種情況要透過資料異動申請書請客服後台同步修改帳號與合約資料。

### tmp:kb:3972
標題：兩個帳號 合併 重複帳號
內容：同一個人不小心註冊了兩個帳號（例如 hotmail 和 gmail 各一個，或信箱大小寫不同各成一帳），系統沒有自助合併功能，需由客服後台處理。請填寫資料異動申請書，載明要保留的帳號、要處理的帳號、以及相關合約 ID，經公司用印後寄至 客服信箱（官網）。日常提醒租客：登入時用當初註冊的確切寫法輸入信箱，可避免誤登或誤建第二個帳號。

### tmp:kb:3975
標題：租客一直沒辦法註冊 卡住了
內容：

### tmp:kb:3978
標題：租客登入後什麼都看不到 畫面空空的
內容：

### tmp:kb:3980
標題：會員帳號資料要修改 信箱手機要換
內容：

### tmp:kb:4561
標題：註冊名字跟證件不符 要怎麼改資料
內容：

### tmp:draft:1
標題：房東教學01：註冊篇(一) 個人房東
內容：房東教學01：註冊篇(一) 個人房東 JGB為租房管理的一站式平台，致力於提升房東以及包租代管業者物件的管理效率，讓繁瑣的人工流程交由系統所處理。 此系列教學文將分成【註冊篇】、【物件篇】、【合約篇】、【帳務篇】、【修繕篇】五個部分，此篇文是整個教學文的第一篇【註冊篇】。 圖 1 操作畫面 創建帳號 親愛的管理者您好，不管你是個人房東、包租代管業者，如未來您將用JGB的系統來管理物件，我們都建議您創建一個帳號。 請先進入 JGB官網首頁，點選畫面右上方之【登入】 圖 2 操作畫面 進入頁面之後，點選畫面上方藍色字體之【立即註冊】 圖 3 操作畫面 進入註冊頁面之後，輸入想要註冊的E-mail帳號 圖 4 操作畫面 完成輸入Email後，平台將會自動發送一組驗證碼至註冊之信箱，於您的註冊信箱接收驗證碼後並輸入 （*若信箱填寫有誤可「點此藍字重新輸入」重新寄送驗證信） 常見問題 Ｑ：為什麼我沒有收到註冊的Email信件驗證碼？ Ａ：驗證信的收取，會受到當下網路、Wi-Fi、手機熱點之影響，如在一個網路收訊較差的地方，可能收到的驗證碼速度會比較慢，建議嘗試切換穩定網路或訊號較清楚的手機網路進行驗證。 Ｑ：我網路是穩定的，確認Email後依舊沒有收到驗證碼，怎麼辦？ Ａ：可能是您的電子郵件服務商判斷驗證信為垃圾信，建議您至垃圾、廣告郵件匣中尋找信件，並將它設定為非垃圾郵件。 若上述方式均嘗試後依然沒有收到驗證碼，可點選右下方 「真人客服」 尋求專員協助，我們將迅速回覆您。 驗證碼輸入無誤後，系統會跳至帳號設定的介面，在此需輸入您的帳號姓名&密碼，輸入完成後可點選「完成註冊」 📌 小提醒 設定完密碼請務必記住喔 圖 5 操作畫面 點選後即完成註冊流程 圖 6 操作畫面 帳號設置 恭喜您已完成註冊！若想更近一步針對該帳號的資料進行編輯或是更動，請跟著以下步驟去操作吧！ 先行完善帳號的設置，畢竟創建物件、發送合約時的基本訊息都來自帳號基本資料的設定，沒有填妥完整資訊也無法發出合約，故建議先行完成基本資料的建置。 請先進入 JGB官網首頁，點選畫面右上方之【登入】 圖 7 操作畫面 選擇【以房東身份登入】 圖 8 操作畫面 輸入您的帳號或密碼（於註冊時若有綁定Facebook、Gmail、LINE等SSO第三方帳號註冊，也得點選頁面下方之選項，以SSO第三方帳號之管道登入） 圖 9 操作畫面 進入系統頁面後，請點選右上方帳號【頭像】的部分，點選「帳號資訊」 圖 10 操作畫面 於帳號資訊內可以針對以下內容進行編輯： （1）帳號基本資訊：姓名／綁定手機／修改密碼 （2）聯絡資訊：Line ID／Facebook／第二組聯絡號碼 圖 11 操作畫面 （3）偏好設定：登入預設身份／時區／Email 通知語系 圖 12 操作畫面 （4）『其他設定』裡的『簽約資訊』新增：身分證字號／戶籍地址／通訊地址／身分證正反面照片／其他附件 圖 13 操作畫面 編輯完成後即可點選【儲存】 親愛的管理者您好，恭喜你已完成帳號註冊與個人資料的建置！ 接下來你可以 點此了解創建物件的教學、或前往 收款設置，開通設置帳戶。 如果您是包租代管業者（開立公司、創建團隊）請 點我前往，創建團隊 的新手上路。

### tmp:draft:2
標題：房東教學02：註冊篇(二) 公司團隊篇
內容：房東教學02：註冊篇(二) 公司團隊篇 親愛的管理者您好，歡迎來到創建團隊的教學，此篇新手上路，將分別告訴你如何 ➡創建團隊 ➡團隊設置 ➡團隊成員管理 ➡新增＆管理大房東 ➡查看＆變更現行的訂閱方案 ➡設定團隊招租對外網址＆時區 ➡常見問題 請各位擅用 【Ctrl+F】的搜索功能。 創建團隊 創建團隊可以幫助公司、管理者，藉由公司的名義進行簽約、包租、代管，並且以團隊細分權限，舉凡「大房東、高專、會計師」可以看到什麼區塊資訊的權限都可以在團隊管理中進行設定，此處設定好的團隊資訊，在創建合約時可將團隊資料如：大小章、租賃管理人員名稱、公司聯繫資訊一併帶入合約。 登入頁面後，於左上角的身份下拉式選單選擇【新增團隊】。 圖 1 操作畫面 選擇【團隊型態】，確定之後點選【下一步】。 圖 2 操作畫面 填寫團隊名稱／公司電話／公司E-mail。 圖 3 操作畫面 確認填寫內容後，點選【完成】即可建立團隊。 團隊設置 團隊創建完成後，你可以與左上方確認點選進入團隊。 點選左側選單當中【團隊管理】中之【團隊資訊】進行編輯。 （如想要新增不只一組的甲方團隊訊息，請見 此篇教學 ） 基本資訊：含公司logo／團隊名稱／團隊介紹 圖 4 操作畫面 聯絡資訊：含Line ID／Facebook／公司電話／公司Email 圖 5 操作畫面 簽約資訊：公司資訊／經紀人資訊／租賃住宅管理人員資訊／附件（公司大小章）/電子簽約圖章 圖 6 操作畫面 📌 小提醒 大小章的附件上傳之後，即可在簽約時在合約對應欄位自動上傳您的電子印鑑，下方電子簽約圖章部分，若開啟【預設使用圖章取代親手簽名】即可於簽約時自動顯示該簽章圖樣，免手動簽名 圖 7 操作畫面 於【團隊管理】中之【收款設置】中可以設定線上/線下金流收款帳戶。 （詳細教學請參考 收款設置篇 ） 團隊成員管理 團隊建立完成後，就可以開始設定您團隊中的角色，並且可以針對不同角色設定不同的系統權限，也可以在創建角色完成後開始邀請您團隊的夥伴一同加入，跟著以下步驟一同完成您的團隊組織吧！ 於【人員管理】中點選【成員列表】。 進入介面後點選右上方之【角色管理】。 圖 8 操作畫面 點選【新增角色】。 圖 9 操作畫面 填入角色名稱＆設定相關系統權限。 📌 小提醒 此步驟主要是在新增類似「職位」以及該職位權限的功能，並非為設定團隊成員 新增角色完成後點選【新增】。 圖 10 操作畫面 📌 小提醒 可於儲存後點選【角色管理】查看新增的角色，日後也可透過點擊該角色的【編輯】圖示進行權限＆名稱的編輯 若要新增「人員」加入團隊，可點選右上方之【邀請】。 圖 11 操作畫面 填入該人員的手機或E-mail。 📌 小提醒 該成員必須已註冊JGB帳號才可進行邀請 圖 12 操作畫面 成員受邀進入後，即可透過右方的下拉式選單，選取其【角色】，進行角色選擇＆權限限制。 圖 13 操作畫面 設定完成後即完成「成員」的新增。 如成員已被加入團隊，登錄後即可以於左上角選擇進入團隊。 圖 14 操作畫面 新增＆管理大房東 功能重點：專業級股東報告，雲端式屋主回報 省時回報： 降低溝通的來往時間，大幅提升效率，將時間留給更重要的事情上，如開發房源、行銷招租等。 創造品牌力： 資訊透明且即時，不只增強大房東的信任度與黏著度，也增加品牌識別度。 管理瀏覽權限： 團隊管理者可視覺化管理大房東瀏覽項目的權限，功能簡單好操作。 多國資產管理： 一站式多國語言及多幣別換算，可支援位於不同國家的大房東，有效管理跨國資產。 在【大房東管理】中，您可以把大房東（所有權人/轉租人）加入設置中，加入設置的【大房東】可以迅速在簽約時迅速的帶入資料，也可以在系統中管理大房東的權限，並且讓大房東自行進系統看了解物件狀況，減少彼此之溝通成本。 ⚠️ 版本更新 版本更新後，所有權人/轉租人統一為大房東 新增大房東（所有權人/轉租人）： 在【大房東管理】中點選【大房東列表】。 圖 15 操作畫面 進入介面後可於此新增【大房東】 圖 16 操作畫面 點選【新增】。 圖 17 操作畫面 填入所有權人資料，確認資料後點選【完成】。 圖 18 操作畫面 完成後即可從列表當中看到新增之大房東。 若要刪除大房東或編輯大房東，可點選右方小齒輪 圖 19 操作畫面 如管理者有在【大房東列表】新增【大房東】資訊，就可以在【建立合約】中的【基本資料】自動帶入【大房東】之訊息，無需在重新填寫一次資料。 圖 20 操作畫面 圖 21 操作畫面 圖 22 操作畫面 圖 23 操作畫面 待大房東加入之後，編輯大房東資料以及權限，可點選右方小齒輪，選取「編輯大房東」 （若尚未建立物件者可參考 物件篇 ）。 圖 24 操作畫面 可以在此編輯大房東資訊 圖 25 操作畫面 點選【編輯所屬物件】，「授權更多物件」。 圖 26 操作畫面 選擇物件，完成後點選【下一步】。 圖 27 操作畫面 於物件右方可設定大房東之系統操作＆觀看之權限。 圖 28 操作畫面 設定後即完成大房東之設置，日後若需新增該房東的物件，可再次點選小齒輪，並點選【編輯所屬物件】進行新增。 圖 29 操作畫面 查看＆變更現行的訂閱方案 可於【團隊管理】中之【訂閱方案】查看你的現行方案。 如你需要變更方案，請點選【變更】。 圖 30 操作畫面 選擇您所需要管理的物件數量來評估年/月費的價格 （若您有客製化管理系統需求也可以選擇【企業方案】來預約客製化的DEMO來滿足您的所需） 圖 31 操作畫面 填寫基本資料。 點選【前往授權】。 圖 32 操作畫面 完成後續付款程序後，即可變更您的方案。 可於【團隊管理】中之【付款紀錄】中查看您在訂閱系統的支出。 圖 33 操作畫面 設定團隊招租頁面網址＆時區 設定對外招租頁面之網址，將有助於增加品牌網址辨識度。 如您需要設定請前往：「團隊管理」>「進階設定」>「房東專屬帳號設定」進行編輯。 圖 34 操作畫面 時區設定：不通地域的時區，同樣可以在「團隊管理」>「進階設定」>「房東專屬帳號設定」進行編輯。 圖 35 操作畫面 合約管理：預設補充條款，下次建立合約時就可自動填入條款內容，無需每次輸入 圖 36 操作畫面 圖 37 操作畫面 新增自定義費用：可在此新增支出類/收入類的自定義費用項目，之後新增單帳單時可不必一再輸入 圖 38 操作畫面 圖 39 操作畫面 常見問題 Ｑ：沒有權限的團隊成員，可否進行簽約、點交、點退？ Ａ：若設有角色含有合約查看編輯權限，可以看到全部的合約。 （角色建議：公司業務） 圖 40 操作畫面 若角色未設定任何權限，可透過【編輯】按鍵來發配特定合約，給予其編輯、查看和簽約的權限。 （角色建議：適用職務：外部仲介、高專、非公司正式職員） 圖 41 操作畫面 圖 42 操作畫面 圖 43 操作畫面 Ｑ：可以將同一個人同時加入團隊成員及大房東嗎？ Ａ：不行，團隊成員和大房東無法同時存在同一個帳號。 假設在大房東設定為「可查看A物件」，但在團隊成員設定上顯示「沒有查看物件權限」，會導致系統判斷錯誤。 Ｑ：我是團隊一員，系統為何告知我沒辦法編輯合約？ Ａ：因團隊擁有者會因職務考量設定不同的閱覽、編輯權限，團隊成員若遇到無法編輯/查看物件、合約、帳務、修繕、團隊項目時，需請有團隊管理權限同事們幫忙設立權限。

### tmp:draft:3
標題：註冊一套專屬你的租房管理
內容：註冊一套專屬你的租房管理 以下我們會一步步詳細解說改版後的註冊登入流程，協助您成為走在最前端的國際化科技房東！ 我們將註冊登入教學分為： 註冊篇 租客電子合約邀請註冊篇 房東登入篇 租客登入篇 一、註冊篇 第一步驟進入JGB官網，並點擊右上角的「登入」。 圖 1 操作畫面 進入以下頁面後，點選下方藍字「立即註冊」。 圖 2 操作畫面 輸入欲註冊的Email帳號，點選「繼續」。 圖 3 操作畫面 平台會發送驗證碼到Email信箱內，查看過後輸入您所收到的驗證碼，驗證碼若正確，系統會自動進入下一個註冊步驟。 圖 4 操作畫面 進入信箱查看驗證碼並輸入 圖 5 操作畫面 驗證碼會傳到Email信箱內 填入基本資料完成帳號設定，點選「完成註冊」。 圖 6 操作畫面 點選過後即完成註冊啦 📌 小提醒 若選擇透過Facebook、Gmail、LINE等SSO第三方帳號註冊，系統也會自動連結進入Email帳號註冊流程。 讓用戶除了使用SSO第三方帳號登入外也可以同時使用E-mail帳號來進行註冊，避免未來忘記要用什麼方式來進行登入！ 二、租客電子合約邀請註冊 圖 7 操作畫面 ⚠️ 版本更新 系統優化改版：租客可自行選擇是否要註冊JGB帳號，若租客不想註冊則可由房東自行填寫租客身份資料等。 租客若願意註冊帳號，還未註冊JGB帳號前，房東在建立合約時輸入租客Email或手機號碼發送邀請，此時租客也可透過JGB的電子合約來完成帳號註冊！ 房東邀請還未註冊會員之租客。 圖 8 操作畫面 點選邀請簽約後，會進入「待租客簽回」畫面，可以看到尚未註冊會員租客的Email帳號。 圖 9 操作畫面 此時，該租客會收到簽約邀請郵件。 圖 10 操作畫面 租客點選郵件內之「查看合約」按鈕後，會進入該物件廣告頁供租客參考。 圖 11 操作畫面 租客確認無誤後，點選廣告頁右下角之「查看合約」，因還未註冊成為JGB會員，所以會進入JGB登入畫面，此時點選「註冊」按鈕，則可順利註冊您專屬的JGB帳號啦！接續即可完成合約！ 圖 12 操作畫面 三、房東登入篇 進入JGB登入畫面，點選房東/管理者的「前往登入」按鈕。 圖 13 操作畫面 房東可選擇透過Email登入; 註冊後綁定手機號碼，也可選擇使用手機號碼登入。 圖 14 操作畫面 房東Email登入 圖 15 操作畫面 房東手機號碼登入 四、租客登入篇 進入JGB登入畫面，點選租客的「前往登入」按鈕。 圖 16 操作畫面 租客可選擇透過Email登入; 註冊後綁定手機號碼，也可選擇使用手機號碼登入。 圖 17 操作畫面 租客Email登入 圖 18 操作畫面 租客手機號碼登入

### tmp:draft:4
標題：帳號資訊設定 完成您的個人資料吧！
內容：帳號資訊設定 完成您的個人資料吧！ 設定個人的帳號資訊是在一個雲端平台數一數二重要的步驟，完成您的個人資料，即可方便自動化的帶入及其他功能的操作呦！ 對於資訊安全有疑慮嗎？別擔心！JGB與世界大廠AWS雲端安全合作，為您的個資嚴格把關。 以下分為三篇： 房東帳號篇 團隊帳號篇 租客帳號篇 大家快去看看屬於自己身份的教學囉，Let's go！ 一、房東帳號篇： 登入後，首先確認自己的身份為『個人房東』。 點按右上角的頭像圖示，並選擇『帳號資訊』 圖 1 操作畫面 出現以下畫面便可以開始編輯您的資料囉！ 您可以在此 更換大頭照 選擇email通知租客的語言 社群帳號，以利租客聯繫 以下資料則需要在『其他設定』裡的『簽約資訊』新增 個人資料 上傳相關文件 圖 2 操作畫面 圖 3 操作畫面 輸入完成後，記得按下右上角的『儲存』按鈕。以上恭喜您完成帳號資訊編輯囉！以後若有需要更改，也可再回來進行編輯。 二、團隊帳號篇： 登入後，首先先依以上房東篇的步驟把個人的帳號資訊輸入完成，再進行以下兩個選擇。 新增團隊 選擇自己所屬團隊 若需新增團隊，先在左上方的選單選擇『＋新增團隊』 圖 4 操作畫面 圖 5 操作畫面 完成基本資訊，並按下確認 出現以下畫面便可以開始編輯您的資料囉！ 您可以在此（未來要到此畫面可在左邊的『團隊管理』>『團隊資訊』裡編輯）： 公司相關資料 選擇email通知租客的語言 社群帳號，以利租客聯繫 團隊介紹 上傳相關文件 圖 6 操作畫面 圖 7 操作畫面 圖 8 操作畫面 輸入完成後，記得按下右上角的『儲存』按鈕。以上恭喜您完成帳號資訊編輯囉！ 三、租客帳號篇： 登入後，首先確認自己的身份為『租客』。 點按右上角的頭像圖示，並選擇『帳號資訊』 圖 9 操作畫面 出現以下畫面便可以開始編輯您的資料囉！ 您可以在此 更換大頭照 選擇收到email通知的語言 社群帳號，以利房東聯繫 圖 10 操作畫面 至「其他設定」的「簽約資訊」裡更改個人資訊 圖 11 操作畫面 輸入完成後，記得按下右上角的『儲存』按鈕。以上恭喜您完成帳號資訊編輯囉！以後若有需要更改，也可再回來進行編輯。 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。

### tmp:draft:5
標題：租客沒有上傳身分證，請問該怎麼辦？
內容：租客沒有上傳身分證，請問該怎麼辦？ 如果出租方要求上傳身分證為必要程序，但租客在簽回時未附上、同時出租方尚未簽回合約，可以進行「取消邀請」。 圖 1 操作畫面 📌 小提醒 為保雙方權益，一旦承租方與出租方簽訂完成簽署流程、進入執行中合約，就無法更動合約內容。 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。

### tmp:draft:6
標題：註冊時收不到驗證信
內容：註冊時收不到驗證信 Update Date：2023/08/17 若是您在註冊帳號時遇到以下情形，請您檢查後再嘗試操作。 收不到E-mail驗證信？ 切換使用訊號穩定之網路。 由於網路、Wi-Fi、手機熱點等網路環境速度的影響。若有遇到類似情形，可能現場Wi-Fi訊號比較弱，建議嘗試切換成手機行動網路。 尋找郵件的垃圾郵件閘。 可能是您的電子郵件服務商判斷驗證信為垃圾信，建議您至垃圾郵件匣中搜尋，並將此郵件設定為非垃圾郵件，以此不漏接JGB系統發通知郵件喔。 檢查輸入的Email是否正確。 可能輸入帳號時有不小心輸入錯誤，可以再重複確認一下喔！ 圖 1 操作畫面 如果以上方法嘗試後皆無法改善的話，建議可改用Facebook、Google、Line帳號來進行註冊。 收不到手機簡訊驗證碼？ 請移動到戶外空間或窗邊後，點選驗證碼重新發送 這可能是電信業者現場的訊號影響所致。可嘗試將手機拿至戶外，或是人在室內的話也可將手機帶至窗戶邊，大部分可改善手機信號不好的問題。 補充案例：各家銀行發送簡訊OTP也會遇到此情形，有時候收銀行簡訊也需要移動到收訊好的地方。 檢查號碼是否輸入正確 可能輸入號碼時有不小心輸入錯誤，可以再重複確認一下喔！ 如果以上方法嘗試後皆無法改善的話，可先跳過綁定手機號碼階段，並請聯絡您的租賃管理業者，請他們協助提供給JGB以下資訊，我們會儘速安排客服人員為您處理。 您的手機號碼和E-mail 手機產品型號與軟體版本（Iphone13 - iOS 16.5，Galaxy S22 - Android 12） 使用的瀏覽器（Safari、Google Chrome、Firefox） 現場網路環境（ Wi-Fi 網路測速多少、有時候月底手機的資費方案部分業者會降速到3G等各種狀況) 電子信箱服務供應商 (Gmail, Yahoo, Outlook, iCloud Mail等等) 發送驗證碼的確切時間點 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。

### tmp:draft:7
標題：我忘記帳號怎麼辦？
內容：我忘記帳號怎麼辦？ 如果不小心遺忘了帳號，各位租客可以透過系統進行驗證，獲得自己的帳號提示，以下為操作步驟流程 進入系統登入頁面，滑到頁面最下方找到【忘記帳號？】，並進行點選。 圖 1 操作畫面 點選【忘記帳號？】後，輸入原帳號綁定的電話號碼進行簡訊驗證。 圖 2 操作畫面 圖 3 操作畫面 驗證完成後，即可收到自己的帳號提示。 圖 4 操作畫面 如果完成以上流程後還是不能協助您找回帳戶的話，請聯繫您的租賃管理業者，租賃管理業者會協助您向我們申請重新找回您的帳號。 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。

### tmp:draft:8
標題：我忘記密碼怎麼辦？
內容：我忘記密碼怎麼辦？ 進入系統登入頁面，滑到頁面最下方找到【忘記密碼？】，並進行點選。 圖 1 操作畫面 點選【忘記密碼？】後，輸入帳號 Email 或綁定的電話號碼進行驗證碼驗證。 圖 2 操作畫面 圖 3 操作畫面 圖 4 操作畫面 圖 5 操作畫面 驗證完成後，即可重新設定自己的帳戶密碼。新密碼請設定至少 6 個字元，並且同時包含英文字母與數字，只有英文或只有數字都無法通過。 完成新密碼設定後，按下【送出】，看到系統提示密碼變更成功後，就可以重新登錄了喔！ 圖 6 操作畫面 如果發現也忘記自己的帳號的話，請參考 我忘記帳號了怎麼辦？ 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。

### tmp:draft:9
標題：如何更改帳號資訊？
內容：如何更改帳號資訊？ 右上角點擊頭像，選擇「帳號資訊」。 圖 1 操作畫面 輕鬆更改帳號資訊。 圖 2 操作畫面 如您需要更多操作說明，歡迎透過線上客服與我們聯繫，或參考其他幫助文章。

### tmp:draft:10
標題：租客系統操作教學—註冊篇
內容：租客系統操作教學—註冊篇 圖 1 操作畫面 親愛的租客您好，歡迎使用JGB的租屋管理系統！ 在JGB的租管系統中，您將可以線上簽約、點交、繳交房租、發送修繕單 這次的教學將會分成三個部分 分別是【註冊篇】、【 合約篇 】、【 繳租（帳務）篇 】 三篇互有連貫也彼此獨立 如果你需要與使用JGB系統的租管業者簽約，你務必先註冊帳戶！ 現在話不多說，我們馬上開始～！ 註冊篇 若您尚未使用或註冊過JGB平台者，在收到房東的簽約邀請時，首先第一步就是註冊一個JGB帳號，接下來就依照以下教學帶您一步一步完成帳號的註冊吧！ step1: 在簡訊收到合約邀請後，請在訊息部分點選藍色的連結 / 在Email收到合約邀請後Email，請在郵件當中點選 「查看合約」 圖 2 操作畫面 圖 3 操作畫面 step2:在點選合約連結之後，會進入閱覽物件的頁面，此時您可以再次確認該物件的條件是否符合您的需求，於確認無誤之後即可立即點選右下方之 「查看合約」 圖 4 操作畫面 step3:此時系統將會跳至登入頁面，請點選 「立即註冊」 手機介面 電腦介面 圖 5 操作畫面 圖 6 操作畫面 step4: 進入註冊頁面之後，輸入想要註冊的E-mail帳號 手機介面 電腦介面 圖 7 操作畫面 圖 8 操作畫面 step5: 完成輸入Email後，平台將會自動發送一組驗證碼至註冊之信箱，於您的註冊信箱接收驗證碼後並輸入 （*若信箱填寫有誤可點選藍字重新輸入） （*驗證信件有可能因信箱篩選緣故，發送至垃圾垃圾郵件或垃圾桶，若沒收到信件可至該處進行確認，若確認過後都沒有收到，可在1分鐘後於頁面點選「重新發送驗證碼」再次確認） 手機介面 電腦介面 圖 9 操作畫面 圖 10 操作畫面 step6: 驗證碼輸入無誤後，系統會跳至帳號設定的介面，在此需輸入您的帳號姓名&密碼，輸入完成後可點選 「完成註冊」 (*設定完密碼請務必記住喔！) 圖 11 操作畫面 圖 12 操作畫面 手機介面 電腦介面 點選後即完成註冊流程啦～ 📌 小提醒 若選擇透過Facebook、Gmail、LINE等SSO第三方帳號註冊，系統也會自動連結進入Email帳號註冊流程。 讓用戶除了使用SSO第三方帳號登入外也可以同時使用E-mail帳號來進行註冊，避免未來忘記要用什麼方式來進行登入！ 恭喜您已順利完成註冊！接著就可以透過已經註冊好的帳號來體驗JGB為您帶來的便利以及服務，用科技來打破您對於傳統租房方式的想像。 如果房東已經發送合約，那就事不宜遲，利用您剛註冊完成的帳號簽約去吧～（進行簽約： 簽約篇 ）


## 三份角度提議
[
 {
  "angle": "user_question_path",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "jgb/A/account-registration",
    "coarse_id": "A",
    "title": "怎麼註冊帳號（Email／第三方／租客從合約邀請註冊）",
    "slug": "account-registration",
    "merge_of": [
     "tmp:canon:jgb/A/account-registration",
     "tmp:kb:3435",
     "tmp:draft:1",
     "tmp:draft:3",
     "tmp:draft:10"
    ],
    "split_from": [
     "tmp:draft:1",
     "tmp:draft:3"
    ],
    "moved_from": [],
    "reason": "使用者問「怎麼註冊」是一條問法，房東自註冊與租客從邀請註冊只是答案內的分支；draft:1／draft:3 只取註冊段併入，其餘段拆去帳號資訊設定與登入方式。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/A/login-methods",
    "coarse_id": "A",
    "title": "怎麼登入（Email／手機號碼／第三方帳號、房東與租客入口）",
    "slug": "login-methods",
    "merge_of": [
     "tmp:draft:3"
    ],
    "split_from": [
     "tmp:draft:3"
    ],
    "moved_from": [],
    "reason": "「怎麼登入」與「怎麼註冊」是不同問題，答案是登入管道與身分入口；由 draft:3 的房東登入篇與租客登入篇拆出。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/account-profile-settings",
    "coarse_id": "A",
    "title": "怎麼修改帳號資訊（姓名、頭像、聯絡方式、偏好、簽約資訊）",
    "slug": "account-profile-settings",
    "merge_of": [
     "tmp:draft:4",
     "tmp:draft:9",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "「帳號資訊在哪改、能改什麼」是一個獨立問題；draft:1 的帳號設置段拆入此處；draft:4 團隊資訊段屬團隊資訊，以另見處理不另提細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/registered-vs-unregistered-tenant",
    "coarse_id": "A",
    "title": "租客一定要註冊嗎？註冊租客與免註冊租客差在哪",
    "slug": "registered-vs-unregistered-tenant",
    "merge_of": [
     "tmp:kb:3348"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "使用者會直接問「租客可不可以不註冊／差別是什麼」，可獨立回答，屬帳號身分層而非合約層。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/email-case-sensitivity",
    "coarse_id": "A",
    "title": "Email 大小寫算不同帳號嗎",
    "slug": "email-case-sensitivity",
    "merge_of": [
     "tmp:kb:3349"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「大小寫有沒有差」是可獨立回答的規則問題，且被看不到合約、重複帳號、邀請失敗多條問題共同引用，獨立一細目供另見。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/verification-code-not-received",
    "coarse_id": "A",
    "title": "收不到驗證碼（Email 驗證信或簡訊）怎麼辦",
    "slug": "verification-code-not-received",
    "merge_of": [
     "tmp:kb:3350",
     "tmp:kb:3871",
     "tmp:kb:3965",
     "tmp:draft:6"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "使用者問「收不到驗證碼」通常不先區分管道，一條問法一細目，答案內依 Email／簡訊分支並含改走 Email 註冊的替代路徑。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/verification-code-invalid",
    "coarse_id": "A",
    "title": "驗證碼一直輸入失敗（新舊碼、識別碼、效期與冷卻）",
    "slug": "verification-code-invalid",
    "merge_of": [
     "tmp:kb:3964"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「收到了但一直錯」與「收不到」是不同問題，排查點是識別碼核對與重發冷卻，獨立一細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/tenant-registration-stuck",
    "coarse_id": "A",
    "title": "租客一直沒辦法註冊、卡住了怎麼排查",
    "slug": "tenant-registration-stuck",
    "merge_of": [
     "tmp:kb:3975"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "管理者常以籠統的「租客卡在註冊」發問，需要一個分流入口回答排查順序，再另見驗證碼、已註冊、LINE 登入等具體細目；來源內容為空，僅保留問法。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/already-registered-error",
    "coarse_id": "A",
    "title": "註冊時顯示此帳號／手機已註冊怎麼辦",
    "slug": "already-registered-error",
    "merge_of": [
     "tmp:kb:3966"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「顯示已註冊」是一條明確問法，答案分本人改登入與被他人占用走解綁兩支。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/line-login-redirects-to-register",
    "coarse_id": "A",
    "title": "用 LINE 快速登入卻被帶去註冊、登不進去",
    "slug": "line-login-redirects-to-register",
    "merge_of": [
     "tmp:kb:3967"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法是登入異常而非登入方式說明，原因（LINE 只認 LINE 註冊帳號）與解法（改帳密登入）可獨立回答。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/forgot-password",
    "coarse_id": "A",
    "title": "忘記密碼怎麼辦",
    "slug": "forgot-password",
    "merge_of": [
     "tmp:kb:3436",
     "tmp:draft:8"
    ],
    "split_from": [
     "tmp:kb:3436"
    ],
    "moved_from": [],
    "reason": "「忘記密碼」是獨立問法；3436 同時含忘記帳號段，拆出至忘記帳號細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/forgot-account-email",
    "coarse_id": "A",
    "title": "忘記當初用哪個信箱註冊怎麼查",
    "slug": "forgot-account-email",
    "merge_of": [
     "tmp:kb:3969",
     "tmp:draft:7",
     "tmp:kb:3436"
    ],
    "split_from": [
     "tmp:kb:3436"
    ],
    "moved_from": [],
    "reason": "「忘記帳號」與「忘記密碼」是不同問題，答案是手機驗證取得打星號信箱提示、無綁手機找客服。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/change-email-or-phone",
    "coarse_id": "A",
    "title": "要換帳號的信箱或手機號碼怎麼辦",
    "slug": "change-email-or-phone",
    "merge_of": [
     "tmp:kb:3437",
     "tmp:kb:3980"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「信箱手機要換」是一條問法，答案是 Email 唯讀走資料異動申請書、手機未綁可自助綁定；與一般帳號資訊編輯不同層級。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/change-account-name",
    "coarse_id": "A",
    "title": "註冊名字與證件不符要怎麼改",
    "slug": "change-account-name",
    "merge_of": [
     "tmp:kb:3971",
     "tmp:kb:4561"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "問法固定為「名字跟證件不符」，答案依合約是否已完成簽署分自改與申請書兩支。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/duplicate-accounts-merge",
    "coarse_id": "A",
    "title": "不小心註冊了兩個帳號能不能合併",
    "slug": "duplicate-accounts-merge",
    "merge_of": [
     "tmp:kb:3972"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "「兩個帳號要合併」是獨立問法，無自助功能、走申請書，與已註冊錯誤和大小寫規則以另見連結。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/login-but-nothing-visible",
    "coarse_id": "A",
    "title": "租客登入後看不到合約、帳單或電表",
    "slug": "login-but-nothing-visible",
    "merge_of": [
     "tmp:kb:3968",
     "tmp:kb:3869",
     "tmp:kb:3978"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "三筆是同一條問法「登入了卻什麼都看不到」，排查順序＝身分選單、登入信箱與邀請信箱是否一致、以合約查帳號狀態；歸帳號身分而非租約。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/A/account-registration",
    "new": "jgb/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3435",
    "new": "jgb/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:draft:3",
    "new": "jgb/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:draft:10",
    "new": "jgb/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:draft:3",
    "new": "jgb/A/login-methods",
    "op": "split"
   },
   {
    "old": "tmp:draft:4",
    "new": "jgb/A/account-profile-settings",
    "op": "merge"
   },
   {
    "old": "tmp:draft:9",
    "new": "jgb/A/account-profile-settings",
    "op": "merge"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/account-profile-settings",
    "op": "split"
   },
   {
    "old": "tmp:kb:3348",
    "new": "jgb/A/registered-vs-unregistered-tenant",
    "op": "new"
   },
   {
    "old": "tmp:kb:3349",
    "new": "jgb/A/email-case-sensitivity",
    "op": "new"
   },
   {
    "old": "tmp:kb:3350",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3871",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3965",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:draft:6",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3964",
    "new": "jgb/A/verification-code-invalid",
    "op": "new"
   },
   {
    "old": "tmp:kb:3975",
    "new": "jgb/A/tenant-registration-stuck",
    "op": "new"
   },
   {
    "old": "tmp:kb:3966",
    "new": "jgb/A/already-registered-error",
    "op": "new"
   },
   {
    "old": "tmp:kb:3967",
    "new": "jgb/A/line-login-redirects-to-register",
    "op": "new"
   },
   {
    "old": "tmp:kb:3436",
    "new": "jgb/A/forgot-password",
    "op": "split"
   },
   {
    "old": "tmp:draft:8",
    "new": "jgb/A/forgot-password",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3969",
    "new": "jgb/A/forgot-account-email",
    "op": "merge"
   },
   {
    "old": "tmp:draft:7",
    "new": "jgb/A/forgot-account-email",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3436",
    "new": "jgb/A/forgot-account-email",
    "op": "split"
   },
   {
    "old": "tmp:kb:3437",
    "new": "jgb/A/change-email-or-phone",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3980",
    "new": "jgb/A/change-email-or-phone",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3971",
    "new": "jgb/A/change-account-name",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4561",
    "new": "jgb/A/change-account-name",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3972",
    "new": "jgb/A/duplicate-accounts-merge",
    "op": "new"
   },
   {
    "old": "tmp:kb:3968",
    "new": "jgb/A/login-but-nothing-visible",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3869",
    "new": "jgb/A/login-but-nothing-visible",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3978",
    "new": "jgb/A/login-but-nothing-visible",
    "op": "merge"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:3354",
    "suggested_shelf": "D",
    "why": "問的是租賃契約要不要記載／上傳身分證、租客未上傳時退出簽名取消合約，是合約簽署與契約應記載事項，不是帳號身分。"
   },
   {
    "id": "tmp:draft:5",
    "suggested_shelf": "D",
    "why": "租客簽回未附身分證時取消邀請、執行中合約不可更動，屬合約簽署流程。"
   },
   {
    "id": "tmp:draft:2",
    "suggested_shelf": "B",
    "why": "整篇為創建團隊、團隊設置、成員角色權限、大房東管理、訂閱方案、招租網址，屬團隊人員與大房東（訂閱方案段屬 I）。"
   }
  ]
 },
 {
  "angle": "content_boundary",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "jgb/A/account-registration",
    "coarse_id": "A",
    "title": "怎麼註冊帳號（Email 主路徑、驗證碼、SSO、租客由簽約邀請註冊）",
    "slug": "account-registration",
    "merge_of": [
     "tmp:canon:jgb/A/account-registration",
     "tmp:kb:3435",
     "tmp:draft:1",
     "tmp:draft:3",
     "tmp:draft:10"
    ],
    "split_from": [
     "tmp:draft:1",
     "tmp:draft:3"
    ],
    "moved_from": [],
    "reason": "註冊步驟（Email→驗證碼→密碼→選身分→綁手機可跳過）、SSO 註冊與租客從電子合約邀請註冊互相依賴才是一份完整的『怎麼註冊』，且與既有細目同一主題，故併入既有細目而非另立；draft:1／draft:3 只取註冊段，登入與帳號設定段另拆。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "merge"
   },
   {
    "id": "jgb/A/login-methods",
    "coarse_id": "A",
    "title": "怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分）",
    "slug": "login-methods",
    "merge_of": [
     "tmp:draft:1",
     "tmp:draft:3"
    ],
    "split_from": [
     "tmp:draft:1",
     "tmp:draft:3"
    ],
    "moved_from": [],
    "reason": "登入方式與登入時選身分是註冊完成後獨立成立的操作主題，與『怎麼註冊』各自完整、內容不同，故自成一細目；來源為 draft:1 的登入段與 draft:3 的房東／租客登入篇。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/verification-code-not-received",
    "coarse_id": "A",
    "title": "收不到驗證信／驗證簡訊怎麼排查（含改走 Email 或 SSO）",
    "slug": "verification-code-not-received",
    "merge_of": [
     "tmp:kb:3350",
     "tmp:kb:3871",
     "tmp:kb:3965",
     "tmp:draft:6",
     "tmp:draft:1",
     "tmp:kb:3975"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "『收不到驗證碼』的排查步驟（垃圾信匣、號碼／信箱正確、攔截 APP、訊號、120 秒冷卻、改走 Email／SSO、聯繫客服要帶的資訊）散在五筆來源但缺一不全，屬同一內容單元；kb:3975 標題『租客一直沒辦法註冊卡住了』無內文，依標題歸入最常見的卡點來源；draft:1 只取其常見問題段。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/verification-code-rejected",
    "coarse_id": "A",
    "title": "驗證碼一直輸入失敗（新舊碼、識別碼比對、效期與冷卻）",
    "slug": "verification-code-rejected",
    "merge_of": [
     "tmp:kb:3964"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "『收到了但驗不過』是與『收不到』不同的完整內容：重發即換碼、三字母識別碼比對、5 分鐘效期、錯三次失效、120 秒冷卻，可獨立回答，故不與收不到合併，兩者以另見互指。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/login-email-mismatch",
    "coarse_id": "A",
    "title": "登入成功卻看不到合約／帳單（身分未切換、登入信箱與合約發送信箱不一致、Email 大小寫視為不同帳號）",
    "slug": "login-email-mismatch",
    "merge_of": [
     "tmp:kb:3349",
     "tmp:kb:3869",
     "tmp:kb:3968",
     "tmp:kb:3978"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "kb:3349 的機制（Email 為帳號識別且分大小寫）與 kb:3869／kb:3968 的症狀排查（切身分、核對登入信箱寫法、退回合約改信箱重寄）互相依賴才完整，故合為一細目；kb:3978 為同症狀的無內文標題。kb:3349 提到邀請大房東失敗屬 B 架症狀，由 B 以另見引用此機制。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/forgot-password",
    "coarse_id": "A",
    "title": "忘記密碼怎麼重設（Email 或簡訊驗證、密碼規則）",
    "slug": "forgot-password",
    "merge_of": [
     "tmp:kb:3436",
     "tmp:draft:8"
    ],
    "split_from": [
     "tmp:kb:3436"
    ],
    "moved_from": [],
    "reason": "重設密碼是一個獨立完整的自助流程（擇一驗證、錯三次失效、密碼至少 6 碼英數混合），kb:3436 內含的『忘記帳號』段拆出另立，避免兩主題混在一筆。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/forgot-account",
    "coarse_id": "A",
    "title": "忘記當初註冊的信箱怎麼查（忘記帳號功能、無綁手機找客服）",
    "slug": "forgot-account",
    "merge_of": [
     "tmp:kb:3436",
     "tmp:kb:3969",
     "tmp:draft:7"
    ],
    "split_from": [
     "tmp:kb:3436"
    ],
    "moved_from": [],
    "reason": "『不知道帳號是哪個信箱』與『知道帳號但忘密碼』是兩個各自完整的問題，前者靠手機簡訊驗證取得打星號提示、無綁手機則透過業者向客服申請；kb:3436 的忘記帳號段與 kb:3969、draft:7 合併。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/change-email-phone",
    "coarse_id": "A",
    "title": "帳號的 Email 與手機號碼怎麼變更（Email 唯讀走客服、手機未綁可自助綁定）",
    "slug": "change-email-phone",
    "merge_of": [
     "tmp:kb:3437",
     "tmp:kb:3980"
    ],
    "split_from": [
     "tmp:kb:3437"
    ],
    "moved_from": [],
    "reason": "信箱／手機這兩個登入識別的變更規則（Email 不可自改、手機未綁定可自助、已綁定改號走後台）是一份完整內容；kb:3437 內的申請書填寫細節屬共用流程，拆出至 data-change-request-form 以另見引用；kb:3980 為同主題無內文標題。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/change-name-vs-contract",
    "coarse_id": "A",
    "title": "註冊姓名與證件不符怎麼改（合約簽署前自改、簽署後鎖定走客服）",
    "slug": "change-name-vs-contract",
    "merge_of": [
     "tmp:kb:3971",
     "tmp:kb:4561"
    ],
    "split_from": [
     "tmp:kb:3971"
    ],
    "moved_from": [],
    "reason": "姓名修改的可否取決於合約是否已完成簽署（藍字帶入 vs 定案快照與帳號姓名鎖定），這組條件與做法互相依賴才完整，且與信箱／手機變更的規則不同，故獨立成細目；申請書流程拆出另見；kb:4561 為同主題無內文標題。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/data-change-request-form",
    "coarse_id": "A",
    "title": "資料異動申請書怎麼申請（帳號資料的後台異動流程與應載明事項）",
    "slug": "data-change-request-form",
    "merge_of": [
     "tmp:kb:3437",
     "tmp:kb:3971",
     "tmp:kb:3972"
    ],
    "split_from": [
     "tmp:kb:3437",
     "tmp:kb:3971",
     "tmp:kb:3972"
    ],
    "moved_from": [],
    "reason": "換信箱、換已綁手機、簽署後改名、合併重複帳號四個主題都引用同一套『申請書載明帳號識別／修改前後值／合約 ID、公司用印、寄客服信箱』流程；此流程本身可獨立成立，依『不同層級以另見處理而非重複』抽成一細目供各主題引用。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/profile-settings",
    "coarse_id": "A",
    "title": "帳號資訊可以設定哪些內容（頭像、通知語系、聯絡社群、簽約資訊與證件附件）",
    "slug": "profile-settings",
    "merge_of": [
     "tmp:draft:4",
     "tmp:draft:9",
     "tmp:draft:1"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "註冊後的帳號資訊頁（基本資訊、聯絡資訊、偏好設定、其他設定的簽約資訊）是獨立於註冊與登入的完整主題；draft:1 只取其帳號設置段；draft:4 的團隊帳號篇屬團隊資訊（B 架），本細目僅取房東／租客帳號篇，團隊段由 B 以另見處理。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/registered-vs-unregistered-tenant",
    "coarse_id": "A",
    "title": "註冊租客與免註冊租客的差異（登入、通知、帳單寄送、到帳作業）",
    "slug": "registered-vs-unregistered-tenant",
    "merge_of": [
     "tmp:kb:3348"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "租客帳號『有無註冊』對登入、通知投遞、帳單寄送與手動到帳的影響是一份自足內容，主題是帳號存在與否的後果而非帳務規則，歸 A；帳單附件密碼與手動到帳僅為後果描述，不另立於 E。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/already-registered-error",
    "coarse_id": "A",
    "title": "註冊時顯示此帳號／手機已註冊怎麼辦（本人改登入、被占用走解綁申請）",
    "slug": "already-registered-error",
    "merge_of": [
     "tmp:kb:3966"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "註冊撞號的兩個分支（本人舊帳號→改登入或重設密碼；被他人占用→解綁申請）是註冊當下的獨立問題，與事後『兩個帳號要合併』內容不同，故各自一細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/duplicate-accounts-merge",
    "coarse_id": "A",
    "title": "同一人有兩個帳號怎麼合併（無自助合併、走客服後台）",
    "slug": "duplicate-accounts-merge",
    "merge_of": [
     "tmp:kb:3972"
    ],
    "split_from": [
     "tmp:kb:3972"
    ],
    "moved_from": [],
    "reason": "重複帳號合併是已成事實後的處理主題，內容（保留哪個、處理哪個、合約 ID）獨立完整；申請書流程拆出至 data-change-request-form 另見；與 already-registered-error 為不同時點的問題不合併。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/line-login-redirects-to-signup",
    "coarse_id": "A",
    "title": "LINE 快速登入被帶到註冊頁（只認 LINE 註冊帳號、無事後綁定、改用帳密登入）",
    "slug": "line-login-redirects-to-signup",
    "merge_of": [
     "tmp:kb:3967"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "SSO 帳號對應規則（LINE 快速登入只匹配以 LINE 註冊的帳號、無補綁功能）與其處置（改用帳密登入、換一般瀏覽器）是一組自足的內容，與一般登入方式說明分屬不同層級，以另見連到 login-methods。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/A/account-registration",
    "new": "jgb/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3348",
    "new": "jgb/A/registered-vs-unregistered-tenant",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3349",
    "new": "jgb/A/login-email-mismatch",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3350",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3435",
    "new": "jgb/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3436",
    "new": "jgb/A/forgot-password",
    "op": "split"
   },
   {
    "old": "tmp:kb:3436",
    "new": "jgb/A/forgot-account",
    "op": "split"
   },
   {
    "old": "tmp:kb:3437",
    "new": "jgb/A/change-email-phone",
    "op": "split"
   },
   {
    "old": "tmp:kb:3437",
    "new": "jgb/A/data-change-request-form",
    "op": "split"
   },
   {
    "old": "tmp:kb:3869",
    "new": "jgb/A/login-email-mismatch",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3871",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3964",
    "new": "jgb/A/verification-code-rejected",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3965",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3966",
    "new": "jgb/A/already-registered-error",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3967",
    "new": "jgb/A/line-login-redirects-to-signup",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3968",
    "new": "jgb/A/login-email-mismatch",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3969",
    "new": "jgb/A/forgot-account",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3971",
    "new": "jgb/A/change-name-vs-contract",
    "op": "split"
   },
   {
    "old": "tmp:kb:3971",
    "new": "jgb/A/data-change-request-form",
    "op": "split"
   },
   {
    "old": "tmp:kb:3972",
    "new": "jgb/A/duplicate-accounts-merge",
    "op": "split"
   },
   {
    "old": "tmp:kb:3972",
    "new": "jgb/A/data-change-request-form",
    "op": "split"
   },
   {
    "old": "tmp:kb:3975",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3978",
    "new": "jgb/A/login-email-mismatch",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3980",
    "new": "jgb/A/change-email-phone",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4561",
    "new": "jgb/A/change-name-vs-contract",
    "op": "merge"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/verification-code-not-received",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/login-methods",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/profile-settings",
    "op": "split"
   },
   {
    "old": "tmp:draft:3",
    "new": "jgb/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:draft:3",
    "new": "jgb/A/login-methods",
    "op": "split"
   },
   {
    "old": "tmp:draft:4",
    "new": "jgb/A/profile-settings",
    "op": "merge"
   },
   {
    "old": "tmp:draft:6",
    "new": "jgb/A/verification-code-not-received",
    "op": "merge"
   },
   {
    "old": "tmp:draft:7",
    "new": "jgb/A/forgot-account",
    "op": "merge"
   },
   {
    "old": "tmp:draft:8",
    "new": "jgb/A/forgot-password",
    "op": "merge"
   },
   {
    "old": "tmp:draft:9",
    "new": "jgb/A/profile-settings",
    "op": "merge"
   },
   {
    "old": "tmp:draft:10",
    "new": "jgb/A/account-registration",
    "op": "merge"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:kb:3354",
    "suggested_shelf": "D",
    "why": "內容是租賃契約應記載事項、身分證影本是否必上傳、租客未上傳時退出簽名／取消合約重寄——整段以合約簽署為主體，身分證在此是合約文件而非帳號身分。"
   },
   {
    "id": "tmp:draft:5",
    "suggested_shelf": "D",
    "why": "『租客沒上傳身分證』的處置是在待租客簽回階段取消邀請、執行中合約不可更動，屬合約簽署流程，與帳號無關。"
   },
   {
    "id": "tmp:draft:2",
    "suggested_shelf": "B",
    "why": "整篇為創建團隊、團隊資訊、角色與成員權限、大房東新增與授權、訂閱方案、招租網址與時區；主體是團隊／人員／大房東（B），訂閱方案段屬 I，皆非帳號與身分。"
   }
  ]
 },
 {
  "angle": "audience_level",
  "coarses": [
   {
    "id": "A",
    "title": "帳號與身分"
   },
   {
    "id": "B",
    "title": "團隊、人員與大房東"
   },
   {
    "id": "C",
    "title": "社區與物件"
   },
   {
    "id": "D",
    "title": "租約（含委託約子題）"
   },
   {
    "id": "E",
    "title": "帳務（含發票、收款金流、抄表）"
   },
   {
    "id": "F",
    "title": "修繕"
   },
   {
    "id": "G",
    "title": "裝置（IoT）"
   },
   {
    "id": "H",
    "title": "幫助中心"
   },
   {
    "id": "I",
    "title": "方案與導入"
   }
  ],
  "fines": [
   {
    "id": "jgb/A/account-registration",
    "coarse_id": "A",
    "title": "怎麼註冊帳號（含驗證碼通知）",
    "slug": "account-registration",
    "merge_of": [
     "tmp:canon:jgb/A/account-registration",
     "tmp:kb:3435",
     "tmp:draft:1",
     "tmp:draft:3",
     "tmp:draft:10"
    ],
    "split_from": [
     "tmp:draft:1",
     "tmp:draft:3"
    ],
    "moved_from": [],
    "reason": "操作層級：註冊步驟（Email 主路徑、驗證碼、設密碼、選身分、綁手機、SSO）對房東與租客相同，租客從合約邀請進入後的註冊步驟亦同，故 kb:3435、draft:1 註冊段、draft:3 註冊段與 draft:10 併入既有細目；租客要不要註冊（權益層級）另見 tenant-registration-choice，收不到驗證碼另見 verification-code-issues。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "keep"
   },
   {
    "id": "jgb/A/tenant-registration-choice",
    "coarse_id": "A",
    "title": "租客要不要註冊：註冊租客與免註冊租客的差異",
    "slug": "tenant-registration-choice",
    "merge_of": [
     "tmp:kb:3348",
     "tmp:draft:3"
    ],
    "split_from": [
     "tmp:draft:3"
    ],
    "moved_from": [],
    "reason": "權益／能力層級：管理者需要知道租客可自選是否註冊、註冊後能做什麼、免註冊會少什麼（無法登入、需人員管理驗證 email、帳單附件寄送、手動到帳），與註冊步驟（操作層級）是不同層級，故獨立成細目、步驟另見 account-registration。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/login-methods-and-identity",
    "coarse_id": "A",
    "title": "怎麼登入：Email／手機／第三方登入與房東租客身分",
    "slug": "login-methods-and-identity",
    "merge_of": [
     "tmp:draft:3",
     "tmp:kb:3967"
    ],
    "split_from": [
     "tmp:draft:3"
    ],
    "moved_from": [],
    "reason": "能力層級：登入管道有哪些（Email、綁定手機、SSO）、登入時要選房東或租客身分、以及 LINE 快速登入只認 LINE 註冊帳號且無法事後補綁的限制，這些是受眾要知道「能不能」的層級，與註冊步驟分開。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/verification-code-issues",
    "coarse_id": "A",
    "title": "驗證碼收不到或一直失敗（Email／簡訊）",
    "slug": "verification-code-issues",
    "merge_of": [
     "tmp:kb:3350",
     "tmp:kb:3871",
     "tmp:kb:3964",
     "tmp:kb:3965",
     "tmp:kb:3975",
     "tmp:draft:6"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層級排查：收不到驗證信／簡訊與驗證碼輸入失敗（新舊碼、識別碼、5 分鐘效期、三次失效、120 秒冷卻、改走 Email）是同一受眾同一主題的排查流程，kb:3975「租客一直沒辦法註冊卡住了」為此主題的入口講法，故合併為一細目。",
    "target_user": [
     "prospect",
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/account-recovery",
    "coarse_id": "A",
    "title": "忘記密碼或忘記帳號怎麼找回",
    "slug": "account-recovery",
    "merge_of": [
     "tmp:kb:3436",
     "tmp:kb:3969",
     "tmp:draft:7",
     "tmp:draft:8"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層級：忘記密碼（Email／簡訊擇一驗證後重設，密碼規則）與忘記帳號（手機簡訊驗證後顯示打星號信箱，無綁手機找客服）互相引用、同一受眾同一主題，故合併為一個找回帳號的細目。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/account-profile-settings",
    "coarse_id": "A",
    "title": "帳號資訊設定：可自助編輯的欄位與位置",
    "slug": "account-profile-settings",
    "merge_of": [
     "tmp:draft:1",
     "tmp:draft:4",
     "tmp:draft:9"
    ],
    "split_from": [
     "tmp:draft:1"
    ],
    "moved_from": [],
    "reason": "操作層級：登入後到頭像「帳號資訊」可自行編輯的內容（基本資訊、聯絡資訊、偏好設定、簽約資訊）與儲存方式，draft:1 帳號設置段拆入此處；draft:4 團隊帳號篇屬 B 架團隊資訊，此處只取房東與租客帳號段；不能自改的識別欄位另見 account-data-change。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/account-data-change",
    "coarse_id": "A",
    "title": "換信箱、換手機、改姓名：哪些能自改、哪些要走資料異動申請書",
    "slug": "account-data-change",
    "merge_of": [
     "tmp:kb:3437",
     "tmp:kb:3980",
     "tmp:kb:3971",
     "tmp:kb:4561"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "權益／能力層級：Email 唯讀不可自改、手機未綁可自助綁定但換號需申請書、姓名在合約簽署完成後鎖定需申請書同步，這些是「帳號識別資料能否自改」的邊界與客服申請流程，與可自助編輯的一般帳號資訊（操作層級）不同層級，kb:3980 與 kb:4561 為此主題的入口講法。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/account-identity-uniqueness",
    "coarse_id": "A",
    "title": "帳號識別規則：Email 大小寫、已註冊提示與重複帳號合併",
    "slug": "account-identity-uniqueness",
    "merge_of": [
     "tmp:kb:3349",
     "tmp:kb:3966",
     "tmp:kb:3972"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "能力層級：Email 為帳號識別且大小寫視為不同帳號、註冊顯示已註冊代表帳號已存在（本人改登入或他人占用走解綁）、誤建兩個帳號無自助合併需申請書，三者都是「帳號唯一性」的系統規則，故合為一細目；由此造成的租客看不到合約症狀另見 tenant-login-cannot-see-data。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   },
   {
    "id": "jgb/A/tenant-login-cannot-see-data",
    "coarse_id": "A",
    "title": "租客登入後看不到合約、帳單或電表的排查",
    "slug": "tenant-login-cannot-see-data",
    "merge_of": [
     "tmp:kb:3869",
     "tmp:kb:3968",
     "tmp:kb:3978"
    ],
    "split_from": [],
    "moved_from": [],
    "reason": "操作層級排查：租客登入成功卻看不到資料，依序檢查身分選單是否切到租客、登入信箱是否與邀請信箱完全一致、必要時以合約查租客帳號狀態並退回修改信箱重發邀請；根因在帳號對不上而非合約本身，故歸帳號架，kb:3978 為此主題的入口講法。",
    "target_user": [
     "property_manager"
    ],
    "op": "new"
   }
  ],
  "id_map": [
   {
    "old": "tmp:canon:jgb/A/account-registration",
    "new": "jgb/A/account-registration",
    "op": "keep"
   },
   {
    "old": "tmp:kb:3435",
    "new": "jgb/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:draft:1",
    "new": "jgb/A/account-profile-settings",
    "op": "split"
   },
   {
    "old": "tmp:draft:3",
    "new": "jgb/A/account-registration",
    "op": "split"
   },
   {
    "old": "tmp:draft:3",
    "new": "jgb/A/tenant-registration-choice",
    "op": "split"
   },
   {
    "old": "tmp:draft:3",
    "new": "jgb/A/login-methods-and-identity",
    "op": "split"
   },
   {
    "old": "tmp:draft:10",
    "new": "jgb/A/account-registration",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3348",
    "new": "jgb/A/tenant-registration-choice",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3967",
    "new": "jgb/A/login-methods-and-identity",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3350",
    "new": "jgb/A/verification-code-issues",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3871",
    "new": "jgb/A/verification-code-issues",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3964",
    "new": "jgb/A/verification-code-issues",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3965",
    "new": "jgb/A/verification-code-issues",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3975",
    "new": "jgb/A/verification-code-issues",
    "op": "merge"
   },
   {
    "old": "tmp:draft:6",
    "new": "jgb/A/verification-code-issues",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3436",
    "new": "jgb/A/account-recovery",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3969",
    "new": "jgb/A/account-recovery",
    "op": "merge"
   },
   {
    "old": "tmp:draft:7",
    "new": "jgb/A/account-recovery",
    "op": "merge"
   },
   {
    "old": "tmp:draft:8",
    "new": "jgb/A/account-recovery",
    "op": "merge"
   },
   {
    "old": "tmp:draft:4",
    "new": "jgb/A/account-profile-settings",
    "op": "merge"
   },
   {
    "old": "tmp:draft:9",
    "new": "jgb/A/account-profile-settings",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3437",
    "new": "jgb/A/account-data-change",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3980",
    "new": "jgb/A/account-data-change",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3971",
    "new": "jgb/A/account-data-change",
    "op": "merge"
   },
   {
    "old": "tmp:kb:4561",
    "new": "jgb/A/account-data-change",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3349",
    "new": "jgb/A/account-identity-uniqueness",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3966",
    "new": "jgb/A/account-identity-uniqueness",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3972",
    "new": "jgb/A/account-identity-uniqueness",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3869",
    "new": "jgb/A/tenant-login-cannot-see-data",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3968",
    "new": "jgb/A/tenant-login-cannot-see-data",
    "op": "merge"
   },
   {
    "old": "tmp:kb:3978",
    "new": "jgb/A/tenant-login-cannot-see-data",
    "op": "merge"
   }
  ],
  "out_of_shelf": [
   {
    "id": "tmp:draft:2",
    "suggested_shelf": "B",
    "why": "整篇為創建團隊、團隊設置、成員角色權限、大房東管理（另含訂閱方案段屬 I、收款設置段屬 E），主體是團隊與人員，不是個人帳號與身分。"
   },
   {
    "id": "tmp:kb:3354",
    "suggested_shelf": "D",
    "why": "命題是租賃契約應記載事項與身分證影本是否必上傳、未上傳時退出簽名取消合約重寄，由合約簽署流程與法規決定，依歸位判準歸租約。"
   },
   {
    "id": "tmp:draft:5",
    "suggested_shelf": "D",
    "why": "租客簽回未附身分證時出租方可取消邀請、簽署完成後不可更動，是合約簽署階段的處置，不是帳號資料設定。"
   }
  ]
 }
]

請輸出合成提議（angle 欄填 synthesis）。