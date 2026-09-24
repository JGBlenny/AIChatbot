# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/G/meter-item-followup-scope` | 電錶項目追問可答範圍（導向電表排障面向） | `jgb/G/meter-item-followup-scope` | 電錶項目追問可答範圍（餘額、可用度數、供電、低電量警報） | keep | G/G/G | |
| 2 | `tmp:canon:jgb/G/smart-meter-lock-iot` | 智慧電錶與門鎖整合 | `jgb/G/smart-meter-lock-iot` | 智慧電錶與門鎖整合（售前） | keep | G/G/G | |
| 3 | `tmp:draft:1` | 房東教學08：IOT設備篇 | `jgb/G/meter-device-management` | 智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數 | split | G/G/G | |
| 4 | `tmp:draft:1` | 房東教學08：IOT設備篇 | `jgb/G/meter-vendor-binding` | 電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理） | split | G/G/G | |
| 5 | `tmp:kb:3458` | 智慧門鎖 使用說明 | `jgb/G/smart-lock-failure` | 門鎖 QR Code／密碼失靈開不了門的排查 | split | G/G/G | |
| 6 | `tmp:kb:3458` | 智慧門鎖 使用說明 | `jgb/G/smart-lock-functions` | 智慧門鎖功能：租客密碼、QR Code、開門紀錄與密碼管理 | split | G/G/G | |
| 7 | `tmp:kb:3460` | 電表低電量警報 通知 | `jgb/G/meter-item-followup-scope` | 電錶項目追問可答範圍（餘額、可用度數、供電、低電量警報） | merge | G/G/G | |
| 8 | `tmp:kb:3461` | IoT 設備無法連線 排查 | `jgb/G/iot-offline-troubleshooting` | IoT 設備（門鎖／電表）無法連線的排查順序 | new | G/G/G | |
| 9 | `tmp:kb:3462` | 分享門鎖密碼 臨時存取 | `jgb/G/smart-lock-share-password` | 分享門鎖密碼：訪客／維修／清潔人員臨時存取 | new | G/G/G | |
| 10 | `tmp:kb:3508` | IoT 廠商帳號綁定失敗 | `jgb/G/meter-vendor-binding` | 電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理） | new | G/G/G | |
| 11 | `tmp:kb:4044` | 電錶數據與 JGB 不同 度數落差 | `jgb/G/meter-data-sync-gap` | 電錶實體度數與 JGB 顯示不同／長期不更新 | new | G/G/G | |
| 12 | `tmp:kb:4049` | 電表串接 綁定 啟用 | `jgb/G/meter-device-management` | 智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數 | split | G/G/G | |
| 13 | `tmp:kb:4049` | 電表串接 綁定 啟用 | `jgb/G/meter-vendor-binding` | 電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理） | split | G/G/G | |
| 14 | `tmp:kb:4049` | 電表串接 綁定 啟用 | `jgb/G/tenant-meter-visibility` | 租客端看到即時電表與自行儲值的前提設定 | split | G/G/G | |
| 15 | `tmp:kb:4051` | 租客看即時電表 可見設定 | `jgb/G/tenant-meter-visibility` | 租客端看到即時電表與自行儲值的前提設定 | new | G/G/G | |
| 16 | `tmp:kb:4052` | IoT 連結起始日 密碼規則 生效 | `jgb/G/smart-lock-password-rules` | IoT 設定：門鎖預設密碼規則與連結起始日的生效範圍 | new | G/G/G | |
| 17 | `tmp:kb:4054` | 門鎖硬體功能 悠遊卡 磁扣 電池 | `jgb/G/smart-lock-hardware-vendor` | 門鎖硬體功能（悠遊卡／磁扣／電池／音量）屬廠商範疇 | new | G/G/G | |
| 18 | `tmp:kb:4055` | 門鎖失靈 QRCode 密碼開不了 | `jgb/G/smart-lock-failure` | 門鎖 QR Code／密碼失靈開不了門的排查 | new | G/G/G | |
| 19 | `tmp:kb:4058` | 電表要怎麼串接進系統 | `jgb/G/meter-vendor-binding` | 電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理） | new | G/G/G | |

## B. 拆分（split）——一個舊細目拆成多個新細目

| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |
|---|---|---|---|
| `tmp:kb:3458` | 智慧門鎖 使用說明 | `jgb/G/smart-lock-failure`《門鎖 QR Code／密碼失靈開不了門的排查》；`jgb/G/smart-lock-functions`《智慧門鎖功能：租客密碼、QR Code、開門紀錄與密碼管理》 | |
| `tmp:kb:4049` | 電表串接 綁定 啟用 | `jgb/G/meter-device-management`《智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數》；`jgb/G/meter-vendor-binding`《電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理）》；`jgb/G/tenant-meter-visibility`《租客端看到即時電表與自行儲值的前提設定》 | |
| `tmp:kb:tmp:draft:1` |  | `jgb/G/meter-device-management`《智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數》；`jgb/G/meter-vendor-binding`《電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理）》 | |

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/G/meter-device-management`《智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數》 | `tmp:kb:4049`＋`tmp:kb:tmp:draft:1` | 裝置管理→智慧電錶頁的操作（逐顆編輯命名、供電／斷電、綁定物件，下箭頭看每日／每週度數折線圖）是與廠商帳號綁定不同步驟的獨立操作題，同一頁的查詢一併收於此不另拆；取 kb:4049 的「剛同步的電表不會自動關聯物件，須逐顆編輯綁定」段與 draft:1 的非台科電基本設定＋查看度數段，draft:1 版本警語「僅可操作智慧電表」屬本頁範圍；draft:1 的「智慧電錶綁帳單」段出現在帳單列上、屬 E 抄表／帳務，本架不收、另見。 | |
| `jgb/G/meter-item-followup-scope`《電錶項目追問可答範圍（餘額、可用度數、供電、低電量警報）》 | `tmp:kb:tmp:canon:jgb/G/meter-item-followup-scope`＋`tmp:kb:3460` | 既有細目 id 不變、吸收 kb:3460：低電量警報是「電錶餘額低於警戒值」這個命題的投遞管道（通知歸它所通知的領域、⛔ 不自成細目），與餘額／可用度數／供電同屬一個可獨立回答的主題；「還能用幾天」仍標明為推算，數字一律以 JGB 資料為準。 | |
| `jgb/G/meter-vendor-binding`《電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理）》 | `tmp:kb:4049`＋`tmp:kb:4058`＋`tmp:kb:3508`＋`tmp:kb:tmp:draft:1` | 「電表怎麼串接進 JGB／怎麼綁台科電帳號／顯示已被綁定怎麼辦」為一個命題：取 kb:4049 的「團隊管理→進階設定→綁定設備廠商、驗證後自動同步裝置清單、一個廠商帳號只能綁一個團隊」段，kb:3508 的已被綁定內部處置（查 DB 看被哪個 role 綁走）併入同一命題，draft:1 的「綁定與串接需由 JGB 業務協助、台科電有專屬教學」段拆入；kb:4058 內文為空，只作入口併入、不獨立成細目。 | |
| `jgb/G/smart-lock-failure`《門鎖 QR Code／密碼失靈開不了門的排查》 | `tmp:kb:4055`＋`tmp:kb:3458` | 「門鎖突然開不了」是獨立排障題：電池電量→密碼效期（與合約連動）→重新產生 QR Code→排除後屬設備故障轉廠商→被鎖門外走社區備用開門程序；kb:3458 的排障尾句拆入此處；純連線問題另見 iot-offline-troubleshooting。 | |
| `jgb/G/tenant-meter-visibility`《租客端看到即時電表與自行儲值的前提設定》 | `tmp:kb:4051`＋`tmp:kb:4049` | 「租客說看不到電表／租客怎麼走儲值電費」是獨立的前提排查題，與後台裝置操作分開：kb:4051 的可見前提（電表已關聯物件、合約已綁定租客）加上 kb:4049 的「建立／編輯合約時電費欄選依儲值電錶設定」這一啟用前提；租客儲值款怎麼收（線下／線上沿用合約收款方式）屬 E 收款金流另見，租客登入身分問題屬 A 另見。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| user_question_path：kb:3460 低電量警報獨立成細目 jgb/G/meter-low-balance-alert | 通知是投遞管道、歸它所通知的領域且 ⛔ 不自成細目；警報通知的命題就是「電錶餘額不足」，content_boundary 與 audience_level 兩角度皆併入既有細目 meter-item-followup-scope，採多數並保留既有 id | |
| audience_level：draft:1 的產品功能與諮詢段併入既有售前細目 jgb/G/smart-meter-lock-iot（op=merge） | draft:1 是房東教學、受眾為 property_manager，售前細目受眾為 prospect；同一命題答案因受眾而異須各受眾各一細目，既有 prospect 細目維持 keep；「綁定需業務協助」段對 PM 是串接問題的一部分，拆入 meter-vendor-binding（user_question_path 與 content_boundary 兩角度一致） | |
| user_question_path：「查看每日／每週用電度數」獨立成 jgb/G/meter-usage-readings-view | 與命名／供電／綁定物件同在裝置管理→智慧電錶同一頁、同一操作叢集，答案即同一路徑導覽；content_boundary 與 audience_level 皆收於 meter-device-management，採多數 | |
| user_question_path：電表綁定拆為 meter-vendor-account-binding／meter-device-property-binding 兩個 slug | 切分方向（廠商帳號綁定 vs 裝置頁操作）與 content_boundary 一致，予以採用；slug 取 content_boundary 與 audience_level 兩角度共同使用的 meter-vendor-binding／meter-device-management | |
| audience_level：kb:4051 租客可見前提併入 meter-device-management | 「租客說看不到電表」是前提排查題、與後台裝置操作題可分（排障題與操作題可分）；user_question_path 與 content_boundary 皆獨立成細目，採多數，slug 取 content_boundary 的 tenant-meter-visibility | |
| content_boundary：kb:4049 的「合約電費欄選依儲值電錶設定」段本架不收、歸 D／E | 該設定是租客能走儲值電費的啟用前提，缺了它「租客怎麼儲值」答不完整，故留在 tenant-meter-visibility；錢怎麼收（線下／線上沿用合約收款方式）仍歸 E 收款金流另見，與 user_question_path 一致 | |
| audience_level：kb:4044 度數落差與 kb:3461 離線合為 jgb/G/iot-offline-sync-troubleshooting | 兩者症狀入口不同（數字不對 vs 顯示離線），排障題依症狀分；共用的補救動作以另見處理，user_question_path 與 content_boundary 皆分列，採多數 | |
| audience_level：kb:3458＋3462＋4052 合為 jgb/G/smart-lock-management | 功能總覽、分享密碼操作、密碼規則生效範圍是三個可獨立回答且層級不同的問題（總覽 vs 操作 vs 設定），合併會讓一句講法對應多個命題；user_question_path 與 content_boundary 皆分列為三細目，採多數 | |
| slug 分歧：user_question_path 的 iot-device-offline-troubleshoot／meter-reading-mismatch-sync／smart-lock-features-usage／smart-lock-password-rule-start-date／smart-lock-hardware-vendor-scope／tenant-meter-visibility-prepaid，audience_level 的 smart-lock-hardware-boundary | 同一命題只取一個 id：有多數者取多數（smart-lock-share-password、smart-lock-failure），無多數者取 content_boundary 較短且與其他角度字根相近的 slug（iot-offline-troubleshooting、meter-data-sync-gap、smart-lock-functions、smart-lock-password-rules、smart-lock-hardware-vendor、tenant-meter-visibility） | |
| audience_level：kb:3190／3196／3201 建議去向 C 社區與物件 | 三筆內文皆明示「依租約／管理規定」或「查看租約」；另兩角度分別判 F／D／D，去向取多數 | |
| content_boundary 與 audience_level：既有細目 tmp:canon 列在 id_map 標 op=merge | 契約規定既有來源自身列 op=keep、被吸收的新來源列 op=merge、fine 本身 op=merge；依契約寫法，語義相同 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/G/meter-device-management` | merge+split-child |
| `jgb/G/meter-item-followup-scope` | merge |
| `jgb/G/meter-vendor-binding` | merge+split-child |
| `jgb/G/smart-lock-failure` | merge+split-child |
| `jgb/G/smart-lock-functions` | split-child |
| `jgb/G/tenant-meter-visibility` | merge+split-child |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

| 舊細目 | 子細目數 |
|---|---|
| `tmp:kb:3458` | 2 |
| `tmp:kb:4049` | 3 |
| `tmp:kb:tmp:draft:1` | 2 |
