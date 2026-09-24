---
coarse: G
title: 裝置（IoT）
scope: IoT 門鎖、密碼、裝置廠商與狀態；⛔ 抄表歸 E
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
---
## 裝置（IoT） {#G}
### 電錶項目追問可答範圍（餘額、可用度數、供電、低電量警報） {#jgb/G/meter-item-followup-scope}
- phrasings:
  - {text: "電表餘額與斷電時間查詢", source: "line-doc:⑤#-", status: approved}
- sources: [draft:batch#19, kb:4021, kb:4091, kb:3460]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
電錶餘額不足走電表排障面向；電錶可依名稱或 id 指定，餘額、可用度數、是否供電來自 JGB；「還能用幾天」是推算，必須標明是推算。
本細目涵蓋的系統機制目錄：IoT領域-智慧設備(母共用)；IoT領域-電表排障(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準
當儲值電表的餘額低於設定的警戒值時，系統會自動發送低電量警報通知給租客和房東，提醒儘速儲值以避免斷電。
系統每日自動檢查所有電表餘額狀態。
房東可在管理後台查看低電量警報的歷史紀錄。
收到警報後建議立即進行儲值操作，儲值成功後警報會自動解除。

### 智慧電錶與門鎖整合（售前） {#jgb/G/smart-meter-lock-iot}
- phrasings:
  - {text: "IoT", source: "question_summary:3603", status: approved}
  - {text: "智慧門鎖", source: "question_summary:3603", status: approved}
  - {text: "智慧電錶", source: "question_summary:3603", status: approved}
  - {text: "智慧電表", source: "koyu:Landlordonboarding08Device#15", status: approved}
  - {text: "IOT設備", source: "koyu:Landlordonboarding08Device#14", status: approved}
  - {text: "私人門鎖和共用門鎖差別", source: "gapmap:C39", status: approved}
- sources: [kb:3603, docs:knowledge/jgb-product-facts.md#doorlock-types]
- reviewed: {by: owner, at: 2026-09-07}
- target_user: [prospect]
- business_types: [system_provider]
- instance_applicability: general
現場抄電表、換門鎖很煩？
金箍棒有整合智慧電錶（抄表可自動帶入帳單）與智慧門鎖，屬硬體設備，實際支援範圍、安裝與費用由專人為您說明。
門鎖分兩型：「私人門鎖」是單一房間的門鎖，只綁一個物件，房東與租客各自設一組密碼；「共用門鎖」是大樓或住家大門，可綁多個物件，由房東設一組共用密碼給租客使用。
可留資由專人與您聯絡。

### 電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理） {#jgb/G/meter-vendor-binding}
- sources: [kb:4049, kb:4058, kb:3508, helpcenter:Landlordonboarding08Device]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
電表安裝好之後要串接進 JGB：到「團隊管理→進階設定→綁定設備廠商」綁定廠商帳號（台科電選「台科電儲值系統」，輸入雲端帳號密碼），驗證通過後系統會自動同步該帳號下的裝置清單，不需逐顆手動新增；之後每日也會自動同步新裝置。
注意：同一個廠商帳號只能綁定一個團隊，若顯示已被綁定，需聯繫客服處理換綁。
剛同步的電表不會自動關聯物件，請到「裝置管理→智慧電錶」逐顆編輯綁定物件，租客端就能看到自己房間的電表。
要讓租客走儲值電費，建立/編輯合約時電費欄選「依儲值電錶設定」，租客儲值的付款管道會沿用該合約的收款方式（線下/線上）。
帳號已被綁定時，需查 DB 確認被哪個 role 綁走。

### 智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數 {#jgb/G/meter-device-management}
- sources: [kb:4049, helpcenter:Landlordonboarding08Device]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
電表安裝好之後要串接進 JGB：到「團隊管理→進階設定→綁定設備廠商」綁定廠商帳號（台科電選「台科電儲值系統」，輸入雲端帳號密碼），驗證通過後系統會自動同步該帳號下的裝置清單，不需逐顆手動新增；之後每日也會自動同步新裝置。
注意：同一個廠商帳號只能綁定一個團隊，若顯示已被綁定，需聯繫客服處理換綁。
剛同步的電表不會自動關聯物件，請到「裝置管理→智慧電錶」逐顆編輯綁定物件，租客端就能看到自己房間的電表。
要讓租客走儲值電費，建立/編輯合約時電費欄選「依儲值電錶設定」，租客儲值的付款管道會沿用該合約的收款方式（線下/線上）。

### 租客端看到即時電表與自行儲值的前提設定 {#jgb/G/tenant-meter-visibility}
- sources: [kb:4051, kb:4049]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客註冊並綁定合約後，就能在租客端前台看到自己房間的電表即時資訊（度數、儲值餘額）並自行儲值。
前提：電表已關聯到該物件、合約已綁定該租客。
若租客反映看不到電表，先確認合約與物件的關聯設定；租客登入身分問題（登錯帳號、身分未切換）屬帳號範疇另行排查。
電表安裝好之後要串接進 JGB：到「團隊管理→進階設定→綁定設備廠商」綁定廠商帳號（台科電選「台科電儲值系統」，輸入雲端帳號密碼），驗證通過後系統會自動同步該帳號下的裝置清單，不需逐顆手動新增；之後每日也會自動同步新裝置。
注意：同一個廠商帳號只能綁定一個團隊，若顯示已被綁定，需聯繫客服處理換綁。
剛同步的電表不會自動關聯物件，請到「裝置管理→智慧電錶」逐顆編輯綁定物件，租客端就能看到自己房間的電表。
要讓租客走儲值電費，建立/編輯合約時電費欄選「依儲值電錶設定」，租客儲值的付款管道會沿用該合約的收款方式（線下/線上）。

### 電錶實體度數與 JGB 顯示不同／長期不更新 {#jgb/G/meter-data-sync-gap}
- sources: [kb:4044]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
電表實體顯示的度數與 JGB 上的數字不同，先看落差多大：系統與廠商的資料同步為每小時一次，一小時內的落差屬正常現象，等下次同步就會追上。
若數字長期不動或落差持續擴大，高機率是台科電雲端帳號的密碼變更或未開通 API 服務，導致該帳號下所有電表停止同步——到「團隊管理→進階設定→綁定設備廠商」重新驗證廠商帳號密碼即可恢復。
JGB 顯示的度數一律以最後同步值為準，不會自行推算。

### IoT 設備（門鎖／電表）無法連線的排查順序 {#jgb/G/iot-offline-troubleshooting}
- sources: [kb:3461]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
IoT 設備（門鎖/電表）無法連線的排查順序：1. 確認設備電源正常（門鎖電池、電表通電）；2. 確認現場網路正常（Wi-Fi/閘道器可嘗試重啟）；3. 台科電電表特別注意：若同一帳號下多顆電表同時顯示離線或數據長期不更新，高機率是台科電雲端帳號的密碼變更或未開通 API 服務——請到「團隊管理→進階設定→綁定設備廠商」重新驗證廠商帳號密碼即可恢復。
系統與廠商的資料同步為每小時一次，剛恢復後請等下一次同步再確認。
以上都排除仍離線，請聯繫對應廠商（台科電/SkyWatch），並提供設備名稱與所在物件。

### 智慧門鎖功能：租客密碼、QR Code、開門紀錄與密碼管理 {#jgb/G/smart-lock-functions}
- sources: [kb:3458]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 智慧門鎖功能：（1）密碼開門：系統為每位租客產生專屬門鎖密碼，在合約有效期間內可使用；（2）QR Code 開門：系統產生 QR Code，掃碼即可開門，適合訪客臨時使用；（3）開門紀錄：可在系統中查看門鎖的開門歷史記錄。
房東可管理門鎖密碼（新增/刪除），也可產生分享密碼供訪客或維修人員臨時使用。
若門鎖無法開啟，請確認密碼是否正確、門鎖電量是否充足、網路連線是否正常。

### 分享門鎖密碼：訪客／維修／清潔人員臨時存取 {#jgb/G/smart-lock-share-password}
- sources: [kb:3462]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東可產生臨時分享密碼提供給訪客、維修人員或清潔人員使用。
操作方式：在門鎖管理頁面選擇「分享密碼」，系統會產生一組一次性或限時密碼，可透過連結或訊息分享給對方。
分享密碼有使用次數或時間限制，過期後自動失效。
此功能僅限房東或有門鎖管理權限的團隊成員操作，租客無法產生分享密碼。

### IoT 設定：門鎖預設密碼規則與連結起始日的生效範圍 {#jgb/G/smart-lock-password-rules}
- sources: [kb:4052]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
IoT 設定中的門鎖預設密碼規則（如手機末四碼）與連結起始日，決定租客門鎖權限的產生方式與生效時點。
調整規則時注意生效範圍：以設定頁說明為準，通常影響新建立的連結，既有合約的門鎖權限是否同步調整請於設定頁確認或逐一檢視。
不確定影響範圍時建議先詢問客服再調整，避免影響在住租客的門鎖使用。

### 門鎖硬體功能（悠遊卡／磁扣／電池／音量）屬廠商範疇 {#jgb/G/smart-lock-hardware-vendor}
- sources: [kb:4054]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
門鎖的硬體功能問題——例如是否支援悠遊卡/磁扣開門、磁扣費用、按鍵音量能否調整、電池與接電供電方式——這些屬於門鎖廠商的硬體規格範疇，支援與否和費用以該型號的廠商文件為準，JGB 系統端無法調整硬體行為。
請聯繫對應的門鎖廠商（如 SkyWatch）詢問，並提供門鎖型號。
JGB 端可管理的是門鎖密碼規則與分享密碼等軟體功能。

### 門鎖 QR Code／密碼失靈開不了門的排查 {#jgb/G/smart-lock-failure}
- sources: [kb:4055, kb:3458]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
門鎖 QRCode 或密碼突然失靈開不了門：先做基本排查——確認門鎖電池電量（低電量常導致感應異常）、密碼是否在有效期內（租客密碼與合約效期連動）、QRCode 是否過期重新產生一組試試。
基本排查後仍失靈，屬設備故障，請聯繫門鎖廠商處理並提供型號與狀況描述；租客被鎖在門外的緊急情況請依社區的備用開門程序處理。
JGB 智慧門鎖功能：（1）密碼開門：系統為每位租客產生專屬門鎖密碼，在合約有效期間內可使用；（2）QR Code 開門：系統產生 QR Code，掃碼即可開門，適合訪客臨時使用；（3）開門紀錄：可在系統中查看門鎖的開門歷史記錄。
房東可管理門鎖密碼（新增/刪除），也可產生分享密碼供訪客或維修人員臨時使用。
若門鎖無法開啟，請確認密碼是否正確、門鎖電量是否充足、網路連線是否正常。
