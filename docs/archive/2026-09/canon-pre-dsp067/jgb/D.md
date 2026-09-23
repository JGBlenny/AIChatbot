---
coarse: D
title: 租約（含委託約子題）
scope: 合約建立、簽署、狀態與階段、續約、退租、違約金、租客邀請簽約；委託約（僅法人房東）；⛔ 帳單與押金金流歸 E
version: 2026-09-15.0
reviewers: [owner]
language: zh-TW
---
## 租約（含委託約子題） {#D}
### 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） {#jgb/D/contract-esign-flow}
- phrasings:
  - {text: "簽約邀請是用簡訊還是email", source: "koyu:slug48#4", status: approved}
  - {text: "上傳既有合約", source: "question_summary:3600", status: approved}
  - {text: "建立合約", source: "question_summary:3600", status: approved}
  - {text: "簽約邀請", source: "question_summary:3600", status: approved}
  - {text: "線上電子簽約", source: "question_summary:3600", status: approved}
  - {text: "簽約要另外收費嗎", source: "gapmap:C22", status: approved}
  - {text: "電子簽章收費", source: "gapmap:C22", status: approved}
  - {text: "電子合約的簽約邀請,有時效嗎?", source: "helpcenter:slug73", status: approved}
- sources: [kb:3600, docs:knowledge/jgb-product-facts.md#esign-no-fee, helpcenter:Landlordonboarding09Socialhousing, helpcenter:onboarding10, helpcenter:onboarding7, helpcenter:onboarding9-1, helpcenter:onboarding9-2, draft:batch#15, helpcenter:Landlordonboarding06Finance, kb:3374, kb:3375, kb:3484, kb:3332, helpcenter:onboarding5, helpcenter:landlordonboarding04lease]
- see_also: [jgb/D/contract-modify-after-sign]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
合約多、怕簽錯、紙本來回慢？
金箍棒的租約管理把一般租賃合約從建約到簽署搬到線上，一頁看完重點：
【建約方式】三種：電子合約（公版範本）、電子合約（客製化契約書）、紙本簽約（把既有的紙本合約上傳留存）。
上傳的既存合約與系統制式合約效力相同，後續合約、帳務、修繕一樣可追蹤。
【流程】只有「刊登中」的物件能建約。
系統以表單引導逐項填寫（租金、收款方式、傢俱與修繕責任、公證、附件、補充條款等），全部填完可先「預覽合約」確認合約文本，再寄送給租客；送出簽約邀請後，租客會收到簡訊／Email 等邀請通知，點連結線上電子簽名（不用手寫紙本），管理者回簽即完成。
租客可選擇免註冊（由管理方代填資料），或直接在邀請流程中完成註冊。
【時效】簽約邀請有效 72 小時（同時也是租客的契約審閱期），逾期連結失效、合約退回待發送，需重填租客資料再發。
【身分】建約時可用個人或法人（團隊）身分；團隊建約會把大小章、租賃管理人員、公司聯繫資訊一併帶進合約。
【社會住宅】社會住宅另有專屬流程：因公證為必要程序，須列印紙本完成公證後上傳歸檔，並非線上完成簽署。
【費用】電子簽章在系統內不另外收費；方案包含哪些內容以定價頁為準。
方案與費用請見 [查看方案與費用](https://www.jgbsmart.com/pricing) 或由專人說明。
想看實際建約畫面可預約 demo。
建立合約後狀態為「待發送」。
發送簽約邀請前請確認合約必填欄位已填寫完整，否則系統會提示「欄位未填寫完整」。
發送成功後狀態變為「待租客簽回」，系統會以 Email 或簡訊通知租客前往簽署。
若租客未收到通知，可檢查聯絡資訊是否正確，或重新發送邀請。
合約簽署分兩階段：（1）租客簽名：租客收到通知後進入簽署頁面完成電子簽名，狀態變為「待房東簽名」；（2）房東簽名：房東確認簽署後合約正式生效，狀態變為「已簽署」。
簽署完成後系統自動開始產生帳單。
若租客遲未簽名，可透過系統重新發送通知提醒。
業者發送簽約邀請的操作步驟：1. 在合約列表中找到狀態為「待發送」的合約（或新建合約選擇物件）；2. 進入合約編輯頁面，確認租期、租金、租客聯絡方式（Email 或手機）等必填欄位已填寫完整；3. 點選「發送簽約邀請」，系統會以 Email 或簡訊通知租客前往簽署；4. 邀請發送後合約狀態變為「待租客簽回」，邀請有效期限預設 72 小時；5. 租客完成簽名後狀態變為「待房東確認」，業者再完成簽名即合約生效。
若必填欄位未填完整，系統會提示無法發送。
合約建立到一半離開頁面時，系統有自動儲存：點選「預覽」或「下一步」會觸發儲存。
若操作後很快離開頁面，可能尚未觸發，資料不一定保得住。
若中途離開，可至【合約總表】>【待發送合約】查看是否有先前建立的合約草稿。
建立合約時，系統會依序引導填寫基本條件、租金費用、收款方式、附設傢俱、現況補充、公證、合約附件與補充條款等頁面。
收款方式若選擇線上金流，還需要確認已在「收款設置」完成串接設定。
以團隊身分建立合約時，基本資料會自動帶入先前在團隊資訊填寫的公司登記資料與聯絡資訊，需先確認正確，如需修改可點「團隊資訊」回去編輯。
團隊建約時需在「經理人資訊」選擇這份合約由哪一位經理人管理，經理人為團隊中負責該物件的成員，要新增經理人需到「人員管理」的成員列表操作。
基本資訊最下方可以選擇用電子簽名圖章取代手動簽名，先前已上傳公司大小章或電子簽名圖章的可直接選用，尚未設定的可到「團隊資訊」設置。
補充條款的用途是因為系統電子合約採政府提供的公版定型化契約，若有其他合約條款需要補充可在此描述，系統會自動把條款內容帶入合約。
預覽合約頁右方的邀請簽約欄位若無法填寫、只剩右上方「返回編輯」可按，通常是編輯合約時必填資訊未填，返回編輯後系統會自動跳回填寫不完整的頁面。
租客反映沒收到合約邀請時，電子租約邀請會受網路、Wi-Fi、手機熱點影響，收訊差的環境收到會較慢，可切換穩定網路後再簽；也可能被郵件服務商判為垃圾信，可到垃圾或廣告郵件匣尋找並設為非垃圾郵件。

### 續約能不能批次處理（含快速日期設定、紙本上傳、通知分流） {#jgb/D/contract-batch-renewal}
- phrasings:
  - {text: "多筆合約一起續", source: "question_summary:3530", status: proposed}
  - {text: "快速日期設定", source: "question_summary:3530", status: proposed}
  - {text: "批次續約", source: "question_summary:3530", status: proposed}
- sources: [kb:3600, docs:knowledge/jgb-product-facts.md#esign-no-fee, helpcenter:Landlordonboarding09Socialhousing, helpcenter:onboarding10, helpcenter:onboarding7, helpcenter:onboarding9-1, helpcenter:onboarding9-2, kb:3530, helpcenter:landlordonboarding04lease]
- see_also: [jgb/D/contract-modify-after-sign]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
【其他】建立新約需逐份進行（不支援批次匯入既有合約）；續約則可在執行中合約一次勾選多筆批次處理（正在提前解約申請中、點交中、點退中的合約無法納入）。
續約頁面支援一次勾選多筆合約批次處理。
續約期間不用手動算日期，系統提供 1、2、3、6、12、18 個月的快速選項，點選後自動帶入新的結束日，也可以逐筆個別指定。
如果跟租客已經在線下簽好紙本合約，續約時可以直接上傳既有的合約 PDF 存檔。
送出後系統會依每筆合約的租客類型，分別發出簽約邀請或續約確認通知。
批次續約的入口在「執行中合約」頁面，點右上方「建立合約」旁的小箭頭，選擇「批次續約」。
勾選要續約的合約後設定續約日期，可用上方的快速設定一次套用到所有勾選的合約，也可以在下方逐份個別設定每份合約的續約期日。
批次續約送出後，系統會把續約邀請發送給租客，這些合約會列在「待租客簽回」中。
租客簽回續約邀請後，管理方確認資料無誤，點選「立即簽名」完成簽約程序，該合約的續約即告完成。

### 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程） {#jgb/D/contract-history-retention}
- phrasings:
  - {text: "歷史合約是什麼?", source: "helpcenter:slug15", status: approved}
  - {text: "既存合約是什麼", source: "koyu:qa06#3", status: approved}
  - {text: "制式合約是什麼意思", source: "koyu:qa06#14", status: approved}
  - {text: "歷史合約裡面放什麼", source: "koyu:slug15#16", status: approved}
  - {text: "合約到期後就消失了", source: "koyu:slug15#8", status: approved}
  - {text: "歷史合約的狀態有哪些", source: "koyu:slug15#2", status: approved}
  - {text: "合約上寫線上智能整合收款是什麼", source: "koyu:slug86#9", status: approved}
- sources: [draft:batch#10, helpcenter:slug15, kb:3330, kb:3385, kb:3853, helpcenter:qa15]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「歷史合約」是已到期的合約，會依點退進度顯示「點退完成」「未退押金」「待退押金」「點退中」等狀態；點退可從合約結束前 30 天起隨時執行。
歷史合約與已完成的帳單系統都會保留、不自動刪除、沒有期限，但仍建議把重要合約下載 PDF 自行留存。
JGB 系統保存歷史合約資料 5 年。
依中華民國《民法》規定，合約等憑證建議至少保存 5 年。
建議管理團隊每年固定時間歸檔副本。
合約過期後分兩階段處理：（1）合約結束日到達時：若已完成點退，直接標記為「合約結案」；若尚未點退，先標記為「歷史合約」，此時仍可安排點退；（2）合約結束日 30 天後：自動標記為「合約結案」，生命週期正式結束。
系統每天自動檢查並更新合約狀態，無需手動操作。
點退或提前解約都完成後，合約在到期（或終止）日前仍會顯示「執行中」，這是正常的——系統是在過了到期/終止日之後，由每日排程自動把合約轉為歷史合約，不需要手動操作，通常是隔天就會更新。
若已經過期好幾天仍停在執行中，屬於異常，請聯繫客服盤查。

### 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） {#jgb/D/contract-modify-after-sign}
- phrasings:
  - {text: "修改合約", source: "question_summary:3600", status: approved}
- sources: [kb:3600, helpcenter:Landlordonboarding09Socialhousing, helpcenter:onboarding10, helpcenter:onboarding7, helpcenter:onboarding9-1, helpcenter:onboarding9-2, kb:3838, kb:3839, kb:3842, kb:3873, kb:3874, kb:3875, kb:4562, kb:4646, helpcenter:slug17, helpcenter:qa07]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
【修改】未發送的合約可直接編輯；已送出邀請要先取消再改（管理者主動取消會保留已填的租客資料；逾期或租客不同意退回則會清空）；租客已簽回但管理方尚未回簽時，可取消簽名後修改重發；雙方都簽完後不可直接修改，只能複製該合約重建新約重簽，或走資料異動申請。
合約 PDF 上的簽署參數（租金、電價、租期等）簽後不可更動；資料異動申請調整的是系統資料，不重簽則 PDF 與實際收款會不一致。
想改合約內容時，能怎麼改取決於這份合約走到哪一步：還沒發送簽約邀請的合約可以直接進編輯頁修改；已送出邀請、還在簽署中的，要先取消簽約退回「待發送」再修改重發；雙方都簽署完成的合約因電子簽章效力無法直接修改，出口只有兩條——複製合約重建新約重新簽署，或填寫資料異動申請書由客服在後台調整資料。
不確定自己的合約在哪一步，提供合約編號或物件名稱即可查詢判斷。
合約已送出簽約邀請但還沒完成雙方簽署時（等租客簽、或租客已簽等管理方回簽），不能直接編輯。
處理方式是取消簽約讓合約退回「待發送」，修改後重新發送邀請。
管理方主動取消時，已填寫的租客資料會保留；但若是租客按「不同意」或邀請逾期自動退回，租客資料會被清空、需要重新填寫。
點不了編輯、或系統告知無法編輯合約時，先確認是不是權限問題：團隊擁有者會依職務設定成員的閱覽與編輯權限，沒有合約編輯權限的成員會無法編輯或查看合約。
這種情況請團隊擁有者（或有團隊管理權限的同事）到團隊管理調整您的角色權限。
若權限正常仍不能編輯，才是合約狀態的限制（簽署中或已簽署的合約本來就不可直接編輯）。
已與房客議定修改內容、要更新現有合約時：可用「複製合約」功能，依需要的項目選擇複製再調整，不必整份重填；若合約還在待發送、內容已與房客確認，建議直接創建新合約（房客同意即可，不必再次線上簽名）。
舊合約可提交異動單移至歷史合約、過去帳單手動封存，之後以新合約與新帳單為準。
租客簽回合約時沒有附上身分證，而出租方要求上傳身分證為必要程序時，只要出租方尚未簽回合約，就可以對這份合約進行「取消邀請」。

### 合約範本有哪些可以選（含內文隨內政部新制更新） {#jgb/D/contract-templates}
- phrasings:
  - {text: "合約範本", source: "question_summary:3600", status: approved}
- sources: [kb:3600, draft:batch#9, docs:knowledge/jgb-product-facts.md#charter-vs-management, helpcenter:Landlordonboarding09Socialhousing, helpcenter:onboarding10, helpcenter:onboarding7, helpcenter:onboarding9-1, helpcenter:onboarding9-2, helpcenter:qa06, kb:3845]
- see_also: [jgb/D/contract-modify-after-sign]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
金箍棒的電子合約範本共 12 種：內政部中文版、內政部英文版、公會中文版各有原房東、包租業、代租代管三種身分版本，另有英泰文版（原房東、代租代管）與英越文版（單一版本）。
法人團隊 12 種都能選；個人房東可選內政部中文版、內政部英文版、英泰文版與公會中文版（皆原房東版）。
另有半伴客製化住宅租賃契約書、新北住都中心租賃契約書與汽車停車位契約書三種特殊用途範本，非一般房東可選。
也可以上傳自己既有的紙本合約留存。
因應法規變動（如電費新制），內政部會更改應記載及不得記載事項，租賃公會全聯會也會建議調整租賃契約內文。
金箍棒近期會較高頻率地更新合約內文用詞（個別磋商條款、電費計算方式、租賃標的現況確認等），但原則是「不改變操作流程」——管理者的建約與簽署操作不受影響，新建合約自動採用新版內文。

### 合約到期追問可答範圍與到期提醒（導向續約面向） {#jgb/D/lease-expiry-followup-scope}
- phrasings:
  - {text: "合約預告期是否已到", source: "line-doc:⑤#E", status: approved}
  - {text: "租客續約意願查詢", source: "line-doc:⑤#E", status: approved}
- sources: [draft:batch#17, kb:3799, kb:3824, kb:3388]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
進續約面向（不是退租收尾）：可依合約條款回答預告期是否到了、距到期幾天；租客有無續約意願 JGB 沒有欄位，要業務自己問。
本細目涵蓋的系統機制目錄：合約領域-系統合約(母共用)；合約領域-續約(子面向)
機制正文在知識庫，需要時以 kb.get 取原文；數字一律以 JGB 資料為準
系統提供合約到期倒數提醒功能，預設在到期前 30 天提示。
建議在合約到期前 30-60 天評估是否續約：若要續約，需在到期前完成整個續約簽署流程，以確保新舊合約無縫銜接。
若不續約，合約到期後系統自動轉為歷史合約，建議在到期後 30 天內完成點退手續。

### 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整） {#jgb/D/sublease-vs-management-contract}
- phrasings:
  - {text: "包租跟代管差在哪", source: "gapmap:C03", status: approved}
- sources: [kb:3600, draft:batch#9, docs:knowledge/jgb-product-facts.md#charter-vs-management, helpcenter:Landlordonboarding09Socialhousing, helpcenter:onboarding10, helpcenter:onboarding7, helpcenter:onboarding9-1, helpcenter:onboarding9-2, helpcenter:qa06, kb:3089, kb:3090, kb:3093, kb:3094]
- see_also: [jgb/D/contract-modify-after-sign]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
包租與代管在系統上的差別主要在委託合約的設定：包租填包租租金與其計算制度，代管填服務費的制度、週期與約定日期；範本也依原房東、包租業、代租代管分版。
包租業的租約通常是由業主與租客直接簽訂，租客享有較多的隱私權和自主性。
而代管業則是業主將物件委託給管理公司，租約由管理公司與租客簽訂，租客在享受服務的同時，能夠獲得更穩定的管理與維護保障。
這意味著，代管業的租客在遇到問題時，能更方便地請求協助，且管理公司會負責處理大部分的事務，這對於租客來說是一種權益保障。
包租業通常會將押金存放在專用帳戶，並依照租約約定進行管理。
而代管業則可能會根據管理協議，直接由管理公司處理押金的收取和退還，並在退租後依據實際情況進行扣除或全額退還。
房客在租約中應詳細了解押金的管理方式及退還流程，以確保自身權益。
包租業的租約終止條件通常較為固定，可能包括租期屆滿、雙方協議終止等。
而代管業則可能會根據管理合約的具體條款，如租客失信、違反合約等情形，提前終止租約。
建議您查看您的租約文件以了解具體條件。
租金調整通常依據租約中的條款進行，主要規定包括：
1. 調整頻率：包租業通常在合約期結束時調整，代管業可能每年依市場行情調整
2. 調整方式：可能按市場行情、通貨膨脹率或約定百分比進行
3. 通知義務：調整前應提前通知租客
您有權了解調整的具體理由及幅度。
如需確認具體條款，請查看租約或聯繫管理師。

### 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 {#jgb/D/contract-create-entry-and-prereq}
- phrasings:
  - {text: "一物件多合約", source: "question_summary:3862", status: proposed}
  - {text: "上限10份", source: "question_summary:3862", status: proposed}
  - {text: "怎麼開始建", source: "question_summary:3881", status: proposed}
  - {text: "新增合約入口", source: "question_summary:3861", status: proposed}
  - {text: "物件刊登前提", source: "question_summary:3861", status: proposed}
  - {text: "物件為什麼不能建立合約", source: "question_summary:3507", status: proposed}
  - {text: "缺什麼欄位", source: "question_summary:4153", status: proposed}
  - {text: "要簽新合約", source: "question_summary:3881", status: proposed}
- sources: [kb:3861, kb:3507, kb:4153, kb:3862, kb:3881, helpcenter:slug10, helpcenter:slug12, helpcenter:slug71]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
新增合約有兩個入口：「合約總表」右上角「建立合約」選擇物件，或「物件總表」找到物件右下方齒輪點「新增/編輯合約」。
前提是物件必須處於「刊登中」——未刊登、洽談中與租約中狀態的物件無法建立新合約，所以建約前請先完成物件刊登。
物件無法建立合約，先檢查兩個前提：（1）物件必須是「刊登中」狀態——未刊登的物件無法建約，請先完成刊登；（2）必填欄位齊備（名稱、用途、建築類型、樓層、面積、租金與地址等）——缺任何一欄都會擋建約。
想知道特定物件到底卡在哪，可以直接問「這個物件為什麼不能建約」，系統會查該物件目前還缺哪些欄位。
一個物件最多可以綁定 10 份合約（含制式與上傳的既存合約）。
常見用法：物件租給多位租客各自簽約，或 A 租約快到期時先開放招租、與新租客 B 預先簽約，新舊合約並存銜接。
「未刊登」的物件代表物件還在編輯中，不會顯示在公開廣告頁，也無法新增合約。
物件還沒刊登而無法新增合約時，先把物件刊登：進入「物件管理」的「物件總表」，點物件右方小齒輪選「刊登招租廣告」或「刊登買賣廣告」，再點右上角的「刊登」。
另一種刊登方式是在「物件總表」點進物件，點「招租廣告」，再點右上角的「刊登」。
刊登完成後，物件總表中的該物件會顯示「刊登中」，接著就能進行「建立合約」或「上傳合約」。
要編輯已建立的合約，入口是「合約總表」中的「編輯合約」。

### 合約複製快速建立相似合約 {#jgb/D/contract-copy}
- phrasings:
  - {text: "合約複製", source: "question_summary:3394", status: proposed}
  - {text: "快速建立", source: "question_summary:3394", status: proposed}
  - {text: "合約要怎麼建立", source: "koyu:onboarding5#1", status: proposed}
- sources: [kb:3394]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約複製功能可快速建立與既有合約條件相似的新合約，適合同一物件換租客或多間物件條件相同的情況。
操作方式：在合約列表或詳情頁面選擇「複製合約」，系統會複製原合約的資料（基本條件、租金設定、設備、現況、謄本等），產生一份新的草稿合約。
複製後需修改租客資訊、租期等差異項目，再進行簽約流程。
複製不會影響原合約。

### 上傳既存（紙本）合約：適用情境、效力、入口、檔案上限 {#jgb/D/upload-existing-contract}
- phrasings:
  - {text: "上傳既存合約", source: "question_summary:3860", status: proposed}
  - {text: "既存合約", source: "question_summary:4218", status: proposed}
  - {text: "是什麼", source: "question_summary:4218", status: proposed}
  - {text: "簽署完成上傳備查", source: "question_summary:4218", status: proposed}
  - {text: "適用情境", source: "question_summary:3860", status: proposed}
- sources: [kb:3860, kb:4218, helpcenter:landlordonboarding04lease]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
手上已有簽署完成的紙本合約、或團隊有自己的公版合約時，不必重簽一次——用「上傳合約」把文件存成 PDF 上傳到平台建檔即可。
上傳後的既存合約與 JGB 制式合約具有相同效力，一樣可以追蹤後續的合約、帳務與修繕。
入口在合約列表右上方「上傳合約」，依指定格式填寫上傳；PDF 以 10MB 為限，過大可調低掃描品質再存檔。
是的——既存合約就是已經在線下簽署完成的合約，上傳到系統留存備查並接續管理（後續帳單、點交等功能照常使用）。
入口：合約總表右上「建立合約」選「既存合約」。
如果點進去沒有物件可選，通常是因為還沒有「刊登中」的物件——建立合約（含既存合約）的前提是物件處於刊登中狀態，請先完成物件刊登。
上傳既存合約的入口有兩個：在「合約總表」點「建立合約」後選擇「紙本簽約」進入上傳，或在「物件總表」點需簽約物件旁的小齒輪選「上傳合約」。
版本更新後，上傳合約已改為從「建立合約」進入、選擇紙本合約來上傳。
進入上傳合約介面後，需先選擇「合約類型」，完成後點「上傳合約」選取合約檔案上傳。
上傳合約的其餘資料填寫與發送合約步驟，與建立合約相同。
上傳合約的檔案限制為 10MB 以內，是為了讓管理者與租客都能迅速上傳與下載合約。
上傳的 PDF 大於 10MB 時，可在掃描時於印表機選擇不同的掃描品質；若仍超過，市面上的免費或付費 PDF 軟體也可在輸出時壓縮檔案。

### 合約附件上傳、備註 50 行與補充條款限制 {#jgb/D/contract-attachments-notes-limits}
- phrasings:
  - {text: "上傳管理", source: "question_summary:3393", status: proposed}
  - {text: "合約備註", source: "question_summary:3843", status: proposed}
  - {text: "合約附件", source: "question_summary:3393", status: proposed}
  - {text: "行上限", source: "question_summary:3843", status: proposed}
  - {text: "合約附件、補充條款限制", source: "helpcenter:qa04", status: proposed}
  - {text: "合約附件上限", source: "koyu:qa04#15", status: proposed}
  - {text: "補充條款有沒有頁數限制", source: "koyu:qa04#4", status: proposed}
- sources: [kb:3393, kb:3843, helpcenter:qa04]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約支援上傳附件功能，可附加合約相關的補充文件：例如房屋照片、身分證明文件、公證書、特約條款附件等。
上傳方式：在合約詳情頁面的「附件」區域點選上傳，選擇檔案即可。
支援常見檔案格式（PDF、JPG、PNG 等），單一合約 PDF 上傳上限為 15MB。
已上傳的附件可供合約雙方在詳情頁面查看和下載。
建議將重要的補充文件都上傳至系統以便集中管理。
合約備註因系統版面限制最多寫 50 行。
內容超過時，建議另外整理成一份文件檔，上傳到「合約附件」中的「其他」作為附件，效果相同且不受行數限制。
合約附件目前只能上傳檔案，圖片格式僅支援 JPG、PNG 與 PDF。
合約附件每個項目可上傳的檔案數量各有不同的限制，上傳前需留意。
補充條款目前至多只能放 1 頁 A4 的內容。
補充條款填寫後務必執行「預覽結果」，確認最終呈現的樣子。

### 合約相關 PDF 下載（合約書、摘要、點交／點退清單、提前解約文件） {#jgb/D/contract-pdf-download}
- phrasings:
  - {text: "PDF", source: "question_summary:3390", status: proposed}
  - {text: "各種文件", source: "question_summary:3390", status: proposed}
- sources: [kb:3390]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 合約支援多種 PDF 文件下載：（1）合約書 PDF：包含完整合約條款和雙方電子簽章；（2）合約摘要 PDF：合約重點資訊摘要；（3）點交清單 PDF：記錄搬入時的設施現況和水電度數；（4）點退清單 PDF：退房時的設施檢查和結算明細；（5）提前解約文件 PDF：提前解約的協議書。
下載方式：在合約詳情頁面點選對應的「下載 PDF」按鈕即可。
PDF 需在對應流程完成後才能下載（如合約書需雙方簽署完成）。

### 簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法 {#jgb/D/signer-identity-and-seal}
- phrasings:
  - {text: "Logo", source: "question_summary:3864", status: proposed}
  - {text: "個人法人", source: "question_summary:3440", status: proposed}
  - {text: "兩位承租人填寫方式", source: "question_summary:4645", status: proposed}
  - {text: "公司大小章", source: "question_summary:3864", status: proposed}
  - {text: "合約呈現", source: "question_summary:3864", status: proposed}
  - {text: "大房東自己簽約", source: "question_summary:3866", status: proposed}
  - {text: "業者團隊身分", source: "question_summary:3866", status: proposed}
  - {text: "簽約身份管理", source: "question_summary:3440", status: proposed}
  - {text: "雙人簽約", source: "question_summary:4645", status: proposed}
  - {text: "Logo大小章&合約呈現方式", source: "helpcenter:slug99", status: proposed}
- sources: [kb:3440, kb:3864, kb:3866, kb:4645]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約身份用於合約簽署時的簽名方資訊。
租客可在帳號設定中新增簽約身份，支援個人身份（姓名、身分證字號）和公司法人身份（公司名稱、統一編號）。
房東方的簽署人資訊則在簽署方資訊頁面管理。
簽約時系統會帶入已設定的身份資料，無需每次重新填寫。
建議在簽約前先完成身份資訊設定，以加快簽署流程。
在「團隊資訊」中上傳公司 Logo 與大小章後，系統合約會自動帶入：Logo 呈現在合約右上角、大小章呈現在簽章處。
簽約前先把團隊資訊設定好，合約產出就有完整的公司形象與用印。
除了公司團隊成員，大房東/投資人也可以自己操作物件簽約：登入後選擇「業者」團隊身分，即可對自己的物件走建約與簽約流程，物件、合約、帳務與修繕狀態也都能在同一介面瀏覽管理。
兩人共同簽約時：身分證欄位請把證件種類改選「其他身分證」（此選項不檢核格式），即可一次輸入兩位的證號；姓名欄建議填「姓：第一位全名、名：/第二位全名」（例如 姓：宋維光、名：/宋紹光），兩位簽約人就會完整顯示、不會跑版。
電子簽署由其中一位承租人代表完成即可。

### 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整） {#jgb/D/contract-send-invite}
- phrasings:
  - {text: "Email", source: "question_summary:3867", status: proposed}
  - {text: "合約為什麼不能發送簽約邀請", source: "question_summary:3490", status: proposed}
  - {text: "合約簽約邀請", source: "question_summary:3368", status: proposed}
  - {text: "為什麼不能發送", source: "question_summary:3368", status: proposed}
  - {text: "發送通道", source: "question_summary:3867", status: proposed}
  - {text: "發送邀請", source: "question_summary:3368", status: proposed}
  - {text: "租客會收到什麼形式的邀請", source: "koyu:slug48#1", status: proposed}
- sources: [kb:3867, kb:3368, kb:3490, helpcenter:slug13, helpcenter:slug48]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約邀請可用兩種通道發給租客：Email 或手機號碼（簡訊）。
發送當下租客會收到簡訊、Email 與系統通知的提醒；合約上填了哪個通道，邀請就送到哪裡，所以發送前請確認租客的聯絡方式填寫正確。
租客需在效期內（預設 72 小時）點連結完成簽署。
合約無法發送簽約邀請時，系統會提示「欄位未填寫完整」。
請依序排查以下條件。
寄送合約邀請時，若租客擁有或願意註冊 JGB 帳號，在「租約管理」的「合約總表」點「編輯合約」，填入租客註冊 JGB 用的電子郵件或電話號碼。
合約內容可按照系統內定格式填寫，也可以自行上傳合約，填寫完成後點「邀請租客簽約」即可寄出。
租客不願註冊 JGB 帳號時，可選取「租客免註冊」，由房東填寫租客資料後按「下一步」繼續。

### 簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長 {#jgb/D/esign-invite-expiry}
- phrasings:
  - {text: "資料清空", source: "question_summary:3868", status: proposed}
  - {text: "連結失效", source: "question_summary:3868", status: proposed}
  - {text: "邀請過期", source: "question_summary:3868", status: proposed}
- sources: [kb:3331, kb:3868, helpcenter:slug13]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約簽約邀請自發送起 72 小時內有效，第一封邀請信件會載明期限，房東 Dashboard 與「待租客簽回」列表可看到每份合約的倒數。
若租客超過期限未簽，連結失效、合約會退回管理者端（待發送）並清空已填的租客資料，需重新填寫租客資料後重新發送。
若覺得 72 小時太短，可透過資料異動申請書申請將效期調整為 7 天或 30 天。
簽約邀請自發送起 72 小時內有效，逾期連結失效，系統會把合約退回「待發送」並清空已填的租客資料——這也是「租客資料怎麼不見了」最常見的原因。
此時需要重新填寫租客資料、重新發送邀請。
房東可在 Dashboard 與「待租客簽回」列表看到每份合約的簽約倒數；若 72 小時對你的情境太短，可透過資料異動申請書申請調整為 7 天或 30 天。
簽約邀請逾期後不需要重建合約，系統會自動把合約退回「待發送」狀態，直接重新發送邀請即可。
系統每小時檢查一次逾期的簽約邀請。
每天 0、6、12、18 點，系統會再檢查一次 24 小時內即將到期的簽約邀請，並發送倒數提醒。
逾期自動退回時會被清空的承租人資訊包含姓名、聯絡方式、地址與緊急聯絡人，手動取消邀請則會保留這些資料。

### 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 {#jgb/D/esign-troubleshooting}
- phrasings:
  - {text: "一直簽不成", source: "question_summary:3883", status: proposed}
  - {text: "卡住了", source: "question_summary:3815", status: proposed}
  - {text: "合約卡在哪", source: "question_summary:3815", status: proposed}
  - {text: "合約怎麼還沒生效", source: "question_summary:3814", status: proposed}
  - {text: "查得到與查不到的", source: "question_summary:3872", status: proposed}
  - {text: "生效了沒", source: "question_summary:3814", status: proposed}
  - {text: "簽了沒動靜", source: "question_summary:3815", status: proposed}
  - {text: "簽名載入失敗", source: "question_summary:3870", status: proposed}
  - {text: "簽約瀏覽器建議", source: "question_summary:3870", status: proposed}
  - {text: "簽約連結打不開", source: "question_summary:3392", status: proposed}
  - {text: "簽署進度", source: "question_summary:3872", status: proposed}
  - {text: "電子簽章失敗", source: "question_summary:3392", status: proposed}
- sources: [kb:3392, kb:3870, kb:3872, kb:3883, kb:3884, kb:3814, kb:3815, kb:4644]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約電子簽章失敗的常見原因與處理：1. 簽署連結過期：邀請連結有效期限到期，請房東重新發送簽約邀請；2. 瀏覽器相容性：建議使用 Chrome 或 Safari 最新版本，避免使用 IE；3. 簽名板無法載入：可能是裝置或網路問題，嘗試重新整理頁面或換裝置；4. 租客尚未綁定帳號：需先完成帳號綁定才能簽署；5. 系統錯誤：若反覆失敗，請截圖錯誤訊息聯繫客服查看簽章服務狀態。
JGB 使用雲想電子簽章服務進行合約簽署。
手機簽約時若簽名板載入不了或流程卡住，多半是瀏覽器相容性問題：Android/iOS 都建議改用 Chrome、Safari 或 Firefox 三大主流瀏覽器。
部分手機品牌的內建瀏覽器有特殊設定，會導致 Google 辨識套件與雲想簽約系統無法正常運作；線上簽約涉及法律效力與個資，主流瀏覽器在安全性上也最有保障。
系統可以判斷這份合約的簽署進度到哪一步：邀請發出了沒、還差租客簽名還是差管理者回簽、發送通道與租客綁定狀態。
但「合約裡第幾個簽名格沒簽」這種格子層級的細節，資料在電子簽供應商（雲想）端，系統查不到；若租客反映簽到一半卡在某格，先依標準排查（換瀏覽器、重新進入連結），解決不了請聯繫客服代查簽署紀錄。
系統不會檢查租客簽名的內容——租客只要在簽名頁面有觸碰紀錄（即使只是難以辨識的一點）就會視為已簽、可進行下一步，因此可能發生少簽而系統未擋下的情況（例如送租補因缺簽名被退件）。
把關時機在管理者「回簽」：回簽位置與租客簽名位置相同，回簽時逐頁確認租客都已確實簽立再完成當頁回簽，即可避免缺簽名。

### 租客收到簽約邀請後的簽署步驟（租客視角） {#jgb/D/tenant-sign-steps}
- phrasings:
  - {text: "收到簽約邀請", source: "question_summary:3442", status: proposed}
  - {text: "簽署步驟", source: "question_summary:3442", status: proposed}
  - {text: "租客會收到什麼形式的簽約邀請?是否有時效?", source: "helpcenter:slug48", status: proposed}
  - {text: "租客說沒收到簽約通知", source: "koyu:slug48#7", status: proposed}
  - {text: "簽約邀請怎麼發", source: "koyu:slug13#2", status: proposed}
- sources: [kb:3442, helpcenter:slug84]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客收到簽約邀請後的操作步驟：1. 透過 Email 或簡訊中的連結進入簽署頁面；2. 若尚未註冊 JGB 帳號，系統會引導完成帳號綁定；3. 確認合約內容（租期、租金、押金等條款）；4. 完成電子簽名（手寫簽名）；5. 簽署完成後等待房東簽名，雙方都簽名後合約正式生效。
若連結過期或無法開啟，請聯繫房東重新發送邀請。
租客收到邀請簽約的郵件通知後點開連結，會先看到欲簽訂的物件廣告，點右下方的「查看合約」。
登入後確認合約內容正確，點「立即簽約」進入下一步。
接著填寫「承租方簽約資料」並往下一步。
預覽合約 PDF 確認無誤後，點「前往簽名框」，再點「請點擊簽署框」進行電子簽名，完成後送出簽名結果。
送出簽名後即等待房東確認合約並回簽。
房東回簽合約後，租客會收到系統通知，合約會列入「執行中合約」。

### 電子合約法律效力、簽章認證與 72 小時審閱期 {#jgb/D/esign-legal-validity}
- phrasings:
  - {text: "72小時", source: "question_summary:3328", status: proposed}
  - {text: "合約審閱期", source: "question_summary:3328", status: proposed}
  - {text: "法律效力", source: "question_summary:3865", status: proposed}
  - {text: "簽章認證", source: "question_summary:3865", status: proposed}
  - {text: "電子合約", source: "question_summary:3865", status: proposed}
- sources: [kb:3865, kb:3328]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
平台合約以電子文件與電子簽章完成，依電子簽章法第 4 條、第 9 條具有法律效力，與本人簽名蓋章效力相同。
簽章採用經濟部商業司認可的憑證機構「雲想科技」SelfieSign 影音數位簽章技術，同時通過歐盟 eIDAS 與 ISO27001 認證。
會員經身分驗證後於平台簽署的合約，均視為本人行為。
依法規，審閱期要求是企業經營者不能要求消費者拋棄審閱期的權利，但這不代表消費者在 72 小時（三日）內簽約就無效或可據此解約。
實務做法：管理公司可錄影，由租客表示已了解審閱期權益，並在三日內完成簽約及點交。
系統中合約的每一個歷程都有租客自行操作的紀錄，可作為佐證。
簽約邀請上會載明簽約期限，租客可自行選擇何時完成簽署。

### 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 {#jgb/D/contract-status-overview}
- phrasings:
  - {text: "不太對勁", source: "question_summary:4563", status: proposed}
  - {text: "包含狀態", source: "question_summary:3389", status: proposed}
  - {text: "合約執行中", source: "question_summary:3389", status: proposed}
  - {text: "合約狀態", source: "question_summary:3373", status: proposed}
  - {text: "合約狀態查詢", source: "question_summary:3372", status: proposed}
  - {text: "合約目前是什麼狀態", source: "question_summary:3510", status: proposed}
  - {text: "待房東簽名", source: "question_summary:4254", status: proposed}
  - {text: "待發送", source: "question_summary:4254", status: proposed}
  - {text: "待租客簽回", source: "question_summary:4254", status: proposed}
  - {text: "目前狀態", source: "question_summary:3372", status: proposed}
  - {text: "簽約前狀態", source: "question_summary:4254", status: proposed}
  - {text: "階段總覽", source: "question_summary:3373", status: proposed}
- sources: [kb:3373, kb:3389, kb:4254, kb:3372, kb:3510, kb:3511, kb:4563]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 合約共有 12 種狀態，分為 4 大階段：（1）簽約前：待發送、待租客簽回、待房東簽名；（2）執行中：已簽署、點交中、已點交、點退中、已點退；（3）提前解約：提前解約中、提前解約已確認；（4）歷史合約：合約結束、合約生命週期結束。
每個狀態對應不同的可執行操作，如需查詢特定狀態的說明或可進行的操作，請告知目前的合約狀態。
合約在前台顯示為「執行中」時，實際包含 5 種細分狀態：已簽署、點交中、已點交、點退中、已點退。
這些都屬於合約有效期間內的不同階段。
已簽署表示雙方完成簽名但尚未辦理入住；已點交表示租客已入住；已點退表示退房手續完成。
可在合約詳情頁查看目前的細分狀態。
這三個是合約「簽約前」階段的狀態，依簽署進度遞進：（1）待發送：合約剛建立完成，尚未把簽約邀請發送給租客，此時可自由編輯合約內容；（2）待租客簽回：已送出簽約邀請，等待租客線上簽名；（3）待房東簽名：租客已完成簽名，換房東（或管理方）簽名。
雙方都簽完後合約進入「已簽署」，開始生效並自動產生帳單。
若邀請逾期或想修改內容，可取消邀請退回待發送狀態重新編輯。
需查詢合約的 status 來判斷目前階段。
需查合約狀態欄位，逐一檢查各操作的前置條件。
前端只顯示按鈕可不可按，不顯示原因。

### 查詢合約資訊：以合約編號／物件名稱查、不能用租客姓名反查、租客資料卡 {#jgb/D/contract-lookup}
- phrasings:
  - {text: "合約編號查詢", source: "question_summary:4641", status: proposed}
  - {text: "姓名反查合約編號", source: "question_summary:4639", status: proposed}
  - {text: "找某租客的租約", source: "question_summary:4639", status: proposed}
  - {text: "查詢合約資訊", source: "question_summary:4641", status: proposed}
  - {text: "用租客姓名找合約", source: "question_summary:4639", status: proposed}
- sources: [kb:4639, kb:4641, helpcenter:slug101]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
智能助手目前無法直接用租客姓名反查合約編號，查詢合約資訊時請提供合約編號或物件名稱。
若手邊只有租客姓名，可先到後台合約列表以租客姓名搜尋，找到對應合約後，再以該合約編號向助手查詢狀態或細節。
要查看租客的聯絡方式，可點選角色姓名（身份卡），租客資料卡會完整呈現租客資料。
租客資料卡上點擊電話號碼，會直接導向電話頁面撥號。
租客資料卡上點擊 Email，會導入撰寫郵件的畫面，可直接發送郵件。

### 依合約狀態篩選物件（點交點退、待退押金、本月到期、無合約） {#jgb/D/contract-filter-by-state}
- phrasings:
  - {text: "快到期空房", source: "question_summary:4655", status: proposed}
  - {text: "押金狀態", source: "question_summary:4149", status: proposed}
  - {text: "本月到期", source: "question_summary:4655", status: proposed}
  - {text: "無合約", source: "question_summary:4655", status: proposed}
  - {text: "物件快速篩選", source: "question_summary:4149", status: proposed}
  - {text: "物件總表篩選", source: "question_summary:4655", status: proposed}
  - {text: "管理者如何快速找到點交、點退與押金狀態的物件?", source: "helpcenter:slug20250612", status: proposed}
- sources: [kb:4149, kb:4655, helpcenter:slug20250612]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
想快速找出正在點交、點退中、已完成點交點退、或待退押金的物件：到「租約管理」→「合約總表」→ 點選「點交點退」分頁，依所需狀態篩選即可一次列出目標物件。
各狀態的意義與後續處理（點交流程、押金退還）屬合約管理範疇，可再進一步詢問。
要同時看到本月到期與目前沒有合約的物件，可在物件總表上方欄位篩選：選「本月到期」後，標籤顯示「無合約／洽談中」的就是目前沒有合約的物件，標籤「合約中」的則是本月即將到期的物件。
「合約總表」的「點交點退」篩選可以用來找出點交中、已點交、點退中、點退完成、要退押金與未退押金的物件。

### 資料異動申請書的填寫與提交 {#jgb/D/contract-data-change-form}
- phrasings:
  - {text: "填寫與提交", source: "question_summary:3841", status: proposed}
- sources: [kb:3841]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
已簽署合約要調整系統資料時，走資料異動申請書：下載官方範本 [資料異動申請書（docx）](https://chatai.jgbsmart.com/forms/contract-data-change-form-20250101.docx)，填寫三個部分——申請人會員資訊（會員類別、帳號、姓名；團隊管理者的會員帳號應填「團隊擁有者」）、申請異動內容（異動項目類別、合約 ID、異動前與異動後的具體描述）、申請人簽署與公司用印。
完成後由申請人會員帳戶的電子信箱寄到 客服信箱（官網），或紙本郵寄客服部（114 台北市內湖區瑞光路 335 號 6 樓之 16）。
金箍棒保留是否受理異動與費用收取的權利，辦理完成後會以 email 回覆。

### 合約快照原則：物件資料、租客聯絡方式或姓名事後修改，合約與通知都不連動 {#jgb/D/contract-snapshot-independence}
- phrasings:
  - {text: "合約與通知不同步", source: "question_summary:3896", status: proposed}
  - {text: "合約顯示與PDF一致不變", source: "question_summary:3897", status: proposed}
  - {text: "快照原則", source: "question_summary:3894", status: proposed}
  - {text: "既有合約不受影響", source: "question_summary:3894", status: proposed}
  - {text: "物件資料修改", source: "question_summary:3894", status: proposed}
  - {text: "租客修改信箱電話", source: "question_summary:3896", status: proposed}
  - {text: "租客改名", source: "question_summary:3897", status: proposed}
- sources: [kb:3894, kb:3896, kb:3897]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
簽約當下系統會把物件資料（名稱、租金、押金、設備、現況等）完整快照進合約，之後合約頁與 PDF 讀的都是這份快照。
所以物件在租約中仍然可以自由編輯——系統不會因為有合約就鎖定欄位——改地址、坪數、設備、照片或刊登租金，都不會讓既有合約或其 PDF 變動，兩者互不影響。
若在建約「草稿」階段想帶入物件最新資料，可在合約編輯中主動重新帶入；已簽署的合約則不會自動連動。
點交與租賃標的現況確認紀錄同樣以當時快照保存，不受物件後續修改影響。
租客自己在會員設定改了 Email 或手機，已簽合約上的承租人聯絡資訊不會跟著變——合約存的是簽約當下的快照，而且所有通知（簽約邀請、點交、點退、帳單）都寄到合約或帳單上的快照欄位，不是會員帳號現值。
所以「租客改了信箱之後收不到通知」是系統的預期行為，不是寄送異常。
處理方式：聯繫客服把租客的新聯絡資訊同步到合約（合約同步屬人工選配作業，不會自動發生）；還沒發送簽約邀請的合約，直接編輯更正聯絡方式再發送即可。
承租人姓名在簽約當下快照進合約，之後列表與詳情頁顯示的都是這份快照，和 PDF 上的名字一致。
租客事後修改會員姓名或簽約身份資料，系統畫面與合約文件都不會變——不會出現「畫面是新名字、PDF 是舊名字」的錯亂，兩邊都是簽約當時的名字。
若因改名需要更新合約書面（如公司更名），屬於已簽合約的內容變更，走複製重建新約重簽。

### 更換承租人／退房後換新租客：只能新建合約，舊約收尾與物件重刊登 {#jgb/D/tenant-change-new-contract}
- phrasings:
  - {text: "更換承租人", source: "question_summary:3898", status: proposed}
  - {text: "物件要重開嗎", source: "question_summary:4216", status: proposed}
  - {text: "退房後換新租客", source: "question_summary:4216", status: proposed}
  - {text: "需重簽新約", source: "question_summary:3898", status: proposed}
  - {text: "點退押金", source: "question_summary:4216", status: proposed}
- sources: [kb:3898, kb:4216]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 系統沒有「更換承租人」功能：資料異動申請書能調整的合約欄位不含承租人；續約是同一位承租人延長租期，也換不了人；承租人只在簽署前的邀請階段綁定。
所以合約簽署完成後要換人，做法是重新建立一份新合約給新承租人簽署，原合約再依情況走提前解約或到期收尾。
原合約的細部處理方式（終止時點、押金與帳單銜接）建議洽客服確認。
前一位租客退房、要簽給新租客時的銜接流程：（1）先把舊合約收尾——就算押金已經私下退還給租客，仍建議走「點退押金」讓系統結案（點退清單可如實結算，金額列零也可以），舊合約才會正常結束轉歷史；（2）物件不需要刪除也不需要重開新物件——物件資料與合約互相獨立（簽約時已快照），舊約結束後把物件重新「刊登」即可；（3）對新租客走正常建立合約（建約前提是物件為刊登中）。

### 合約刪除、取消、作廢的條件與取消 vs 歷史合約差異 {#jgb/D/contract-cancel-delete}
- phrasings:
  - {text: "合約刪除", source: "question_summary:3846", status: proposed}
  - {text: "合約取消", source: "question_summary:3386", status: proposed}
  - {text: "為什麼不能取消或作廢合約", source: "question_summary:3513", status: proposed}
  - {text: "與歷史合約差異", source: "question_summary:3386", status: proposed}
- sources: [kb:3846, kb:3513, kb:3386]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
想刪除或作廢合約時，能不能刪取決於狀態：還沒發送簽約邀請（待發送）的合約可以直接刪除；已送出邀請的要先取消簽約退回待發送後刪除；雙方簽署完成的合約無法刪除或取消——不再執行就走提前解約流程，到期後系統會自動轉為歷史合約留存紀錄。
若是特殊情況需要處理已簽合約的資料，走資料異動申請書由客服評估。
合約簽署生效後（status >= 8）無法取消，需改用「提前解約」。
合約取消與歷史合約不同：取消是指合約被作廢或無效化，不會出現在執行中或歷史合約列表中；歷史合約則是正常到期結束，仍可查閱完整記錄。
取消通常發生在簽約前（如租客拒絕簽署），取消後合約記錄保留但標記為無效。
若需查看已取消的合約，請在篩選條件中選擇「已取消」。

### 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 {#jgb/D/handover-checkin}
- phrasings:
  - {text: "修改清單重發", source: "question_summary:3516", status: proposed}
  - {text: "合約為什麼不能點交", source: "question_summary:3491", status: proposed}
  - {text: "合約點交流程", source: "question_summary:3376", status: proposed}
  - {text: "合約點交需要哪些條件", source: "question_summary:3377", status: proposed}
  - {text: "租客不同意點交", source: "question_summary:3516", status: proposed}
  - {text: "設備分類與自訂項目", source: "question_summary:3515", status: proposed}
  - {text: "點交前置條件說明", source: "question_summary:3377", status: proposed}
  - {text: "點交清單內容", source: "question_summary:3515", status: proposed}
- sources: [kb:3376, kb:3377, kb:3491, kb:3515, kb:3516, helpcenter:landlordonboarding04lease]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約點交（搬入）流程：1. 房東建立點交清單並發送給租客，記錄設施現況、水電度數起始值，可附上照片；2. 租客確認內容無誤後同意點交，狀態變為「已點交」。
若租客尚未同意，房東可取消點交重新操作。
點交完成後水電度數即作為後續帳單的計算基準。
合約點交需滿足以下條件：1. 租客已註冊並綁定 JGB 帳號；2. 雙方已完成電子簽章；3. 合約尚未進行過點交或點退；4. 合約不在提前解約狀態。
若無法點交，請依序檢查：租客是否已綁定帳號、雙方是否都已簽名完成、是否正在進行提前解約。
合約點交按鈕灰色時，需查詢合約資料判斷具體原因。
點交清單不用從零建立，系統已內建標準設備清單，分成室外、客餐廳及臥室、廚房及衛浴三大區域，涵蓋門鎖、冷氣、家具、衛浴設備等常見項目。
發送點交時逐項標記狀態（良好、損壞、無此設備），需要的話可以為每項填寫狀況描述（30 字內）、上傳最多 3 張照片，並標記日後的維修責任由房東或租客負責。
清單沒有的東西（例如鋼琴、書櫃）可以用自訂項目加進去，填法跟標準設備一樣。
租客不同意點交時，這次點交會被退回，合約回到「已簽署」狀態，您會收到通知，也能看到租客填寫的不同意原因。
處理方式很單純：依照租客反映的問題修改點交清單，再重新發送一次就好，重發沒有次數限制。
另外，如果租客遲遲沒有回應，您也可以先取消這次點交邀請，內容整理好再重發。
點交是選擇性操作，可依房東習慣與房客的約定自行決定是否進行，未點交的合約也可以發送帳單。
點交的時機是簽約完成後，即可在「執行中合約」選取要點交的物件進行點交。
「執行中合約」列表裡，每份合約是否已點交會以燈號方式顯示在合約上方。
建約時在「附設傢俱」註記的傢俱與責任歸屬，簽約完成後都會帶入點交清單。
點交清單送出前需確認另計費用項目的起始度數，若沒有另計費用項目可直接送出。
點交清單記錄的初始電費度數若有填寫，會直接帶入帳單，由系統自動計算電費。
點交清單送出後，系統會立即通知租客進行點交確認，待租客確認後點交程序即完成。

### 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 {#jgb/D/return-checkout}
- phrasings:
  - {text: "合約為什麼不能點退", source: "question_summary:3492", status: proposed}
  - {text: "合約點退", source: "question_summary:3379", status: proposed}
  - {text: "合約點退流程", source: "question_summary:3378", status: proposed}
  - {text: "操作位置", source: "question_summary:3850", status: proposed}
  - {text: "租客不同意點退", source: "question_summary:3520", status: proposed}
  - {text: "租客拒絕確認", source: "question_summary:3521", status: proposed}
  - {text: "費用與賠償項目", source: "question_summary:3518", status: proposed}
  - {text: "點退找補費用", source: "question_summary:3850", status: proposed}
  - {text: "點退清單填寫", source: "question_summary:3518", status: proposed}
  - {text: "點退金額有異議", source: "question_summary:3521", status: proposed}
- sources: [kb:3378, kb:3379, kb:3492, kb:3518, kb:3520, kb:3521, kb:3850, helpcenter:slug27, helpcenter:slug28, helpcenter:slug66, helpcenter:landlordonboarding04lease]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約點退（搬出）流程：1. 房東建立點退清單，記錄設施檢查結果、損壞賠償明細及水電度數結算，發送給租客；2. 租客確認內容後同意點退。
點退完成後系統自動產生點退帳單，含押金結算、水電費和賠償金額。
合約到期後系統會自動將合約標記為歷史合約。
合約點退需滿足以下條件：1. 租客已綁定 JGB 帳號；2. 合約已簽署完成；3. 已到達合約開始日；4. 尚未完成過點退。
特別注意：合約不需要先完成點交即可進行點退（例如租客尚未入住就退租的情況）；合約過期後仍可進行點退，以處理到期後才辦退房的情況。
合約點退按鈕灰色時，需查詢合約資料判斷原因。
注意：不需先點交也可以點退；合約過期後仍可點退。
發送點退時，您需要在點退清單裡完成幾件事：逐項檢查設備狀態，有損壞的填上賠償金額和原因（可附照片佐證）；結算水電瓦斯費；有其他費用或違約金也一併填入；最後設定繳款期限。
系統會自動儲存草稿，中途離開再回來可以接著填，發送成功後草稿就會清掉。
租客同意點退後系統會直接依清單金額產生點退帳單，所以各項金額在發送前確認好即可。
租客不同意點退時，這次點退會被退回，您會收到通知並能看到租客填寫的原因，通常是對賠償金額或費用結算有意見。
跟租客確認好之後，修改點退清單重新發送即可，沒有次數限制；租客還沒回應前，您也可以先取消點退邀請。
要注意的是，租客一旦同意，點退帳單就自動成立了，之後金額有問題就得從帳單端處理，所以發送前建議先跟租客把金額對好。
對點退清單上的賠償金額或費用結算有疑問時，請先不要按同意，選擇「不同意」並填寫原因，房東會收到通知，跟您確認後修改清單重新發送。
因為您一旦同意，系統就會直接依清單金額產生點退帳單，所以同意前請把每筆賠償和費用都核對清楚，有爭議先透過不同意的方式反映。
點退的押金找補（多退少補）在「編輯點退清單」時一併操作，不在帳務管理裡另外設定。
房東送出點退結果、租客同意後，系統會立即在合約細節產生點退清單，並依清單金額自動產生帳單、分派到付款方（房東或租客）的繳費帳單中。
點退退款目前僅提供線下付款。
點退押金的入口在「合約管理」的「執行中合約」中列於「30 天內到期」的合約，或在「歷史合約」中找到該物件，打開右下方小齒輪選「點退押金」。
點退押金可以選擇不執行，不執行時該合約的狀態會被標註為「未退押金」。
未點退的合約在租約到期後，同樣會進入歷史合約。
進入點退後先進行設備損壞確認，若有損壞可按「編輯」輸入賠償金額及理由，再按「下一步」。
接著輸入繳費期限；若有帳單尚未繳清，可算出餘額從點退押金中扣除，再按「送出帳單」，確認帳單細節後送出。
點退帳單的內容含提前解約金、點退押金與賠償金，並需填入帳單期限後發送。
租客同意點退結果後，管理方在編輯點退押金清單時一併編輯帳單，管理方與租客都可以到繳費帳單查看。
待租客確認點退並完成繳款後，點退程序即完成。

### 取消／收回點交或點退邀請，為什麼不能取消 {#jgb/D/handover-return-cancel-invite}
- phrasings:
  - {text: "取消點交邀請", source: "question_summary:4255", status: proposed}
  - {text: "取消點退邀請", source: "question_summary:4255", status: proposed}
  - {text: "收回邀請", source: "question_summary:4255", status: proposed}
  - {text: "為什麼不能取消點交或點退", source: "question_summary:3512", status: proposed}
- sources: [kb:3512, kb:4255]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
取消點交需 status=16，取消點退需 status=64。
租客已同意則不能撤回。

### 租客要退租了接下來怎麼做：到期收尾步驟總覽（點退→帳單→封存→轉歷史）與退租跑到哪一步 {#jgb/D/lease-end-checkout-overview}
- phrasings:
  - {text: "到期退租收尾", source: "question_summary:3847", status: proposed}
  - {text: "接下來怎麼做", source: "question_summary:3876", status: proposed}
  - {text: "步驟總覽", source: "question_summary:3847", status: proposed}
  - {text: "租客要退租了", source: "question_summary:3876", status: proposed}
  - {text: "退租跑到哪一步了", source: "question_summary:3878", status: proposed}
  - {text: "還缺什麼", source: "question_summary:3878", status: proposed}
- sources: [kb:3847, kb:3876, kb:3878]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約到期退租的收尾順序：一、發送點退清單（到期前 30 天起就能操作，記錄設備檢查、賠償與水電結算）；二、租客同意後系統自動產生點退帳單，押金多退少補；三、到帳單總表以合約編號搜尋，把剩餘未結帳單批次封存（系統不會自動封存）；四、過到期日後系統每日排程自動把合約轉為歷史合約，不用手動操作。
點退不以點交為前提，租客沒點交過也能直接點退。

### 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 {#jgb/D/early-termination-flow}
- phrasings:
  - {text: "反悔處理", source: "question_summary:3525", status: proposed}
  - {text: "取消提前解約申請", source: "question_summary:3525", status: proposed}
  - {text: "可以解約嗎", source: "question_summary:3370", status: proposed}
  - {text: "合約提前解約", source: "question_summary:3370", status: proposed}
  - {text: "合約未到期退租", source: "question_summary:3380", status: proposed}
  - {text: "合約為什麼不能提前解約", source: "question_summary:3493", status: proposed}
  - {text: "房東提前解約理由", source: "question_summary:3523", status: proposed}
  - {text: "房東發起", source: "question_summary:3382", status: proposed}
  - {text: "提前終止", source: "question_summary:3370", status: proposed}
  - {text: "提前解約", source: "question_summary:3380", status: proposed}
  - {text: "租客發起", source: "question_summary:3381", status: proposed}
  - {text: "租客違約欠租", source: "question_summary:3523", status: proposed}
- sources: [kb:3380, kb:3381, kb:3382, kb:3370, kb:3493, kb:3523, kb:3525, kb:3851, helpcenter:landlordonboarding04lease]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
提前解約可由租客或房東任一方發起。
發起條件：1. 合約狀態為「已簽署」或「已點交」；2. 未曾提出過提前解約；3. 合約未在續約流程中。
租客發起時，合約須有允許提前解約的設定；房東發起則無此限制。
提前解約生效後，合約終止日會更新為雙方協議的提前終止日期。
租客發起提前解約流程：1. 租客提出申請（需合約設定允許提前解約，否則無法申請）；2. 房東收到通知後須在 7 天內回應確認；3. 若房東逾期未回應，提前解約自動生效。
生效後合約終止日更新為租客希望的解約日期。
若合約不允許提前解約，租客需先與房東協商調整合約設定。
房東發起提前解約流程：1. 房東提出申請；2. 租客需簽署提前解約同意書（電子簽章）；3. 租客完成簽名後系統生成解約文件，解約正式生效。
與租客發起不同，房東發起不受合約設定限制，但需要租客配合簽名才能完成，租客不簽名則無法強制生效。
提前解約按鈕灰色時，需判斷合約狀態和設定。
房東發起提前解約時，系統會要求選擇解約理由，提供 10 種法定理由，主要分兩類：一是「出租方為重新建築而必要收回」，這類的簽署期限放寬到 90 天，而且可以設定賠償金給租客；二是租客違約類，包含遲付租金或管理費達兩個月、擅自轉租、擅自變更用途、毀損房屋經催告不改善、擅自裝修或影響結構安全、存放危險物品等，這類不需支付違約金，簽署期限是 30 天。
都不符合的話選「其他」自行填寫理由。
申請時也可以上傳佐證資料供租客查看。
提前解約申請在還沒生效前都可以取消：也就是房東還沒確認、7 天等待期也還沒過的期間，到申請頁面取消即可，合約會恢復原狀繼續執行，對方也會收到取消通知。
但只要房東已經確認，或 7 天到了自動生效，合約終止日就已經更新，這時就無法取消了，想繼續承租只能重新簽一份新合約。
所以提出申請前建議先跟對方溝通好。
房東發起提前解約後，需要租客電子簽署提前解約同意書才會生效，回簽效期預設 30 天；「出租方為重新建築而必要收回」這類法定事由的簽署期限放寬到 90 天。
租客逾期未簽，提前解約不會成立，合約維持原狀。
發起前建議先與租客溝通好終止日與違約金，避免卡在回簽。
可以提前終止合約的是執行中合約，不論已完成點交或尚未點交都可以發起。
正在異動中的合約無法提前終止，包括「點交中」、「點退中」與「提前終止合約申請中」的合約。
已結束的合約也無法提前終止，包括「已點退」與「已結束」的合約。
房東發起提前終止時，在「合約管理」的「執行中合約」點該合約旁的小齒輪選「提前終止合約」，先選填終止理由並上傳佐證資料。
接著填寫提前終止合約日期、違約金資訊與責任歸屬，按「下一步」確認內容後「送出」，等待房客簽回。
送出後的終止合約申請可在「待租客簽回」查看；若要取消，點物件旁小齒輪選「取消提前終止合約」。
房客簽回後，到「合約管理」的「待房東簽名」點「前往簽名」，確認內容後點「立即簽約」，完成簽名即完成提前終止合約。

### 提前解約違約金怎麼算（預告期）、由誰付 {#jgb/D/early-termination-penalty}
- phrasings:
  - {text: "房東賠償租客", source: "question_summary:3524", status: proposed}
  - {text: "提前解約違約金付款方", source: "question_summary:3524", status: proposed}
  - {text: "提前解約違約金計算", source: "question_summary:3522", status: proposed}
  - {text: "退租賠償金額", source: "question_summary:3522", status: proposed}
  - {text: "房東要怎麼提前解約", source: "koyu:onboarding9-1#1", status: proposed}
  - {text: "租客要怎麼提前解約", source: "koyu:onboarding9-2#1", status: proposed}
- sources: [kb:3522, kb:3524]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
提前解約的違約金不用自己算，送出申請時系統會自動算好顯示出來。
計算邏輯是看「預告期」夠不夠：系統會比較從提出申請到希望解約日的天數，跟合約設定的預告天數（常見是 60 天）。
天數有滿，違約金用較低的那組設定（例如 1 個月租金）；不夠，就用較高的那組（例如 2 個月租金）。
至於用月租倍數還是固定金額計算，依合約建立時的設定，也有些合約是約定依補充條款處理。
實際金額一律以合約設定為準。
違約金由誰支付，看提前解約是誰發起的。
租客發起的，違約金一律由租客支付，金額依合約設定自動計算。
房東發起的就有彈性：如果是租客違約導致（例如欠租達兩個月），系統不會產生違約金；如果是房東自己的原因（例如要收回重建），可以設定一筆賠償金由房東支付給租客。
這筆錢不會另外開帳單，系統會在點退時自動列入點退帳單，跟押金一起結算。

### 提前解約生效後：何時可點退、違約金與押金一併結算、之後還要處理什麼 {#jgb/D/early-termination-aftermath}
- phrasings:
  - {text: "提前解約之後", source: "question_summary:3877", status: proposed}
  - {text: "提前解約生效後", source: "question_summary:3526", status: proposed}
  - {text: "還要處理什麼", source: "question_summary:3877", status: proposed}
  - {text: "點退與違約金結算", source: "question_summary:3526", status: proposed}
  - {text: "提前解約後何時可以進行點退?", source: "helpcenter:slug29", status: proposed}
- sources: [kb:3526, kb:3877, helpcenter:slug29]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
提前解約生效後，系統會把合約終止日改成雙方談定的解約日，但租約要真正結清，還需要走完點退：房東發送點退清單、租客確認後，系統自動產生點退帳單。
提前解約的違約金不用另外處理，系統會自動把它列進點退帳單，跟押金、水電結算、設備賠償一起算總帳。
如果違約金是約定由房東賠償租客，會以負數列入，直接從應付金額中扣抵。
提前解約後，從新的租期到期日往前算 30 天起，就可以到「執行中合約」進行「點退押金」。
點退帳單的可操作期間，從租期到期前 30 天起一直到合約結束後都可以進行。
提前解約後的點退，系統會依照合約條件自動帶入並判斷是否有違約金。
系統帶入的違約金數字，房東可以依照實際狀況自行調整。

### 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 {#jgb/D/renewal-flow}
- phrasings:
  - {text: "不需電子簽名", source: "question_summary:3529", status: proposed}
  - {text: "免註冊租客續約", source: "question_summary:3529", status: proposed}
  - {text: "前置條件", source: "question_summary:3384", status: proposed}
  - {text: "可以續約嗎", source: "question_summary:3371", status: proposed}
  - {text: "合約為什麼不能續約", source: "question_summary:3494", status: proposed}
  - {text: "合約續約", source: "question_summary:3371", status: proposed}
  - {text: "已達數量上限", source: "question_summary:3854", status: proposed}
  - {text: "延長合約", source: "question_summary:3371", status: proposed}
  - {text: "方案配額", source: "question_summary:3854", status: proposed}
  - {text: "流程步驟", source: "question_summary:3383", status: proposed}
  - {text: "續約資料保留與重置", source: "question_summary:3528", status: proposed}
  - {text: "重新簽署", source: "question_summary:3528", status: proposed}
- sources: [kb:3383, kb:3384, kb:3494, kb:3371, kb:3879, kb:3880, kb:3528, kb:3529, kb:3858, kb:3854]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約續約流程：1. 房東發起續約，系統自動複製原合約建立新合約，新合約起始日為原合約結束日隔天；2. 新合約需重新走完簽約流程（發送邀請→租客簽名→房東簽名）；3. 簽署完成後新合約生效，原合約自動標記為舊版本。
可透過系統查閱完整的續約歷史紀錄。
合約續約須同時滿足以下條件：1. 租客已綁定 JGB 帳號；2. 雙方簽名已完成；3. 未發出或完成點退；4. 點交流程已完成（不能在點交中途）；5. 未在提前解約流程中或已完成提前解約；6. 合約尚未過期。
建議在合約到期前提早發起續約，以確保新舊合約無縫銜接。
續約按鈕灰色時，需逐一排查 7 個條件。
發起續約時，系統會自動複製原合約產生新合約：物件和租客資料、租金押金設定、客製化資訊都會帶過去，租客的固定虛擬帳號也會沿用，繳費帳號不會變。
但簽名不會帶過去——續約等於簽一份新約，需要重新發送邀請走簽署流程（邀請有效期 72 小時）。
新合約的起始日，系統會自動接在原合約結束日的隔天，確保租期無縫銜接。
如果續約要調整條件（例如調漲租金），在發送邀請前修改新合約內容就可以。
續約要不要重新簽名，取決於租客有沒有綁定 JGB 帳號。
已綁定的租客，續約需要重新走一次簽署流程（發送邀請、租客簽名、房東簽名）；免註冊租客因為無法電子簽名，系統會改發續約確認通知，發送後就直接完成續約，不用簽。
如果希望免註冊租客也改用電子簽署，要先邀請他註冊並綁定帳號，再發起續約。
已註冊（綁定帳號）的租客續約需要重新走簽署流程：發送續約邀請、租客簽名、房東簽名，邀請效期與一般簽約相同為 72 小時，逾期需重新發送。
免註冊租客則不用重簽，系統改發續約確認通知，發送後即完成續約。
續約或建約時出現「已達數量上限」，原因是訂閱方案的合約配額用完了——系統計算的是方案合約上限加上加購數，減去團隊目前的合約總數；要注意歷史合約與每一次續約都會計入總數，所以就算執行中合約不多，累積的歷史約也可能吃滿配額。
解法是升級方案、加購合約數，或聯繫客服協助盤點。
這與物件是否下架無關。

### 系統續約 vs 重建新約的取捨（條件變更、租屋補助審核） {#jgb/D/renewal-vs-new-contract}
- phrasings:
  - {text: "付款方式變更", source: "question_summary:3329", status: proposed}
  - {text: "合約延長", source: "question_summary:3329", status: proposed}
  - {text: "租屋補助", source: "question_summary:3333", status: proposed}
  - {text: "租補過審", source: "question_summary:3333", status: proposed}
  - {text: "系統續約", source: "question_summary:3855", status: proposed}
  - {text: "續約條件變更", source: "question_summary:3329", status: proposed}
  - {text: "重建新約", source: "question_summary:3855", status: proposed}
- sources: [kb:3855, kb:3329, kb:3333]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
只是延長租期、其他條件都不變時，用系統續約最省事：系統複製原約產生新約、起始日自動接在原到期日隔天，產出「續約增補」文件。
但有兩種情況建議重建新約：一是租金、電費、補充條款等日期以外的參數要變更——這些屬於簽後不可改的內容，需要重新簽訂才有法律效力；二是租客要申請租屋補助——部分審核單位對續約增補的認定不一，重建一份完整新約較不易被退件。
若合約內除日期以外的參數有變更（如租金、電費、補充條款等），需要重新簽訂一份租約，以確保法律效力並配合實價登錄等作業。
執行中的電子合約無法直接修改內容。
建議做法：
1. 全部重來：建立新合約
2. 將原合約 PDF 下載，用紙本上傳方式重新上傳，發給租客點選同意，再透過異動單將舊合約封存
每個租補承辦專員的審核標準不同。
建議做法：
1. 將原合約本文以及續約附件一併提供給審核單位，因為合約本文依循內政部規範，續約只是延後期限
2. 請租客提供審核專員的聯繫方式，由管理公司直接與承辦電話溝通，一次說明清楚

### 續約後原合約去哪了：續約歷史、增補文件分頁、有沒有下一份約 {#jgb/D/renewal-history-and-addendum}
- phrasings:
  - {text: "下一份約", source: "question_summary:4660", status: proposed}
  - {text: "原合約保留查詢", source: "question_summary:3527", status: proposed}
  - {text: "原合約分頁", source: "question_summary:3856", status: proposed}
  - {text: "合約有沒有續約", source: "question_summary:4660", status: proposed}
  - {text: "續約增補文件", source: "question_summary:3856", status: proposed}
  - {text: "續約歷史紀錄", source: "question_summary:3527", status: proposed}
- sources: [kb:3527, kb:3856, kb:4660]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
續約後原合約不會不見。
系統的做法是另外建立一份新合約，把原合約標成舊版本，所以合約列表平常只顯示最新那份。
在列表找不到原合約時，到合約的續約歷史就能看到完整紀錄——從原始合約到每一次續約，每份的條款、簽名紀錄和 PDF 都完整保留，隨時可以調閱。
系統續約不會重產一份完整合約全文，而是產生「續約增補」PDF，以分頁形式掛在合約鏈上。
所以續約後在原合約看到多出的「其他分頁」，就是歷次續約的增補文件；列表平常只顯示最新一筆合約，開舊約會自動跳轉到最新續約，完整的鏈都可在續約歷史查閱。

### 委託約與租賃約的差別（系統分開管理） {#jgb/D/delegation-vs-lease-contract}
- phrasings:
  - {text: "委託約", source: "question_summary:3334", status: proposed}
  - {text: "租賃約", source: "question_summary:3334", status: proposed}
  - {text: "與出租合約差異", source: "question_summary:3471", status: proposed}
- sources: [kb:3334, kb:3471]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
委託約是房東與管理公司之間的委託管理合約，租賃約是管理公司與租客之間的租賃契約。
系統中分別管理，圖示（icon）不同。
建立合約時請注意選擇正確的合約類型，避免混淆。
委託合約（受託合約）與出租合約是 JGB 系統中兩種不同類型的合約：（1）出租合約：房東與租客之間的租賃關係，管理租金收取、點交點退等；（2）委託合約：房東與物管業者之間的委託管理關係，約定物件代管條件、管理費用、管理期限等。
兩種合約獨立管理，一個物件可同時有委託合約（房東委託物管）和出租合約（物管代為出租給租客）。
委託合約有獨立的簽署和管理流程。

### 委託合約的建立簽署、提前終止與 PDF 下載 {#jgb/D/delegation-contract-flow}
- phrasings:
  - {text: "委託合約", source: "question_summary:3472", status: proposed}
  - {text: "委託合約提前終止", source: "question_summary:3473", status: proposed}
  - {text: "建立簽署流程", source: "question_summary:3472", status: proposed}
  - {text: "文件下載", source: "question_summary:3474", status: proposed}
  - {text: "解除委託", source: "question_summary:3473", status: proposed}
- sources: [kb:3472, kb:3473, kb:3474]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約建立與簽署流程：1. 物管在系統中建立委託合約，填寫房東資訊、基本條件（委託期限、管理範圍）、費用設定（管理費）、付款方式和管理方資訊；2. 確認內容後發送簽約邀請給房東；3. 房東收到通知後進入簽署頁面完成電子簽章；4. 物管方也完成簽名後，委託合約正式生效。
簽署完成後系統會產生委託合約 PDF 文件供雙方留存。
委託合約提前終止流程：物管或房東可在委託合約有效期間內提出提前終止。
操作步驟：1. 在委託合約詳情頁面選擇「提前終止」；2. 填寫終止原因和協議終止日期；3. 發送通知給對方確認；4. 對方同意後委託合約終止。
終止後該物件回歸房東自行管理。
若委託合約下有進行中的出租合約，需先處理出租合約的安排再終止委託。
委託合約簽署完成後，系統會自動產生委託合約 PDF 文件。
下載方式：在委託合約詳情頁面點選「下載 PDF」即可取得包含完整合約條款和雙方電子簽章的 PDF 檔案。
PDF 內容包含：委託期限、管理範圍、費用約定、雙方簽署資訊等。
房東和物管雙方都可在系統中下載此文件。
建議下載後妥善保存以備查閱。

### 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 {#jgb/D/delegation-contract-terms-general}
- phrasings:
  - {text: "委託管理合約", source: "question_summary:3114", status: proposed}
  - {text: "委託管理合約服務", source: "question_summary:3259", status: proposed}
  - {text: "委託管理合約期限", source: "question_summary:3115", status: proposed}
  - {text: "委託管理合約權利", source: "question_summary:3122", status: proposed}
  - {text: "委託管理合約權益", source: "question_summary:3260", status: proposed}
  - {text: "委託管理合約法律", source: "question_summary:3125", status: proposed}
  - {text: "服務費用計算", source: "question_summary:3158", status: proposed}
  - {text: "租約管理服務", source: "question_summary:3147", status: proposed}
  - {text: "管理師責任", source: "question_summary:3121", status: proposed}
  - {text: "管理費用支付方式", source: "question_summary:3123", status: proposed}
  - {text: "管理費用計算", source: "question_summary:3117", status: proposed}
- sources: [kb:3114, kb:3115, kb:3121, kb:3122, kb:3125, kb:3147, kb:3259, kb:3260, kb:3117, kb:3123, kb:3158]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託管理合約是房東與包租代管公司之間的法律協議，授權公司負責租屋管理、維護及租客安置等事宜。
作為租客，您可以享有更專業的服務，並確保您的居住環境得到妥善管理。
委託管理合約的期限通常為一年，但具體的期限可能會依據合約內容而有所不同。
建議您查看您的合約，或聯繫您的管理師以獲取詳細資訊。
管理師的責任包括協助租客處理租約相關事宜、維護房屋設施、定期檢查物件狀況、協調維修服務及確保租客的權益受到保障。
管理師還需要進行租金收取、提供租客資訊及解決租客的疑問與問題。
租客在委託管理合約中享有多項權利，包括對租金、押金的明確說明，維修服務的及時反應，以及租約條款的遵守。
此外，租客有權要求管理公司提供定期的物業維護報告及相關費用的透明度。
您也有權在合約期間提出任何合理的維修請求，管理公司必須在合理的時間內處理。
委託管理合約通常適用於民法及租賃相關法律，具體條文及適用法律可能依合約內容及地區有所不同。
建議您聯繫您的管理師確認相關法律適用情況。
是的，我們業者提供租約管理服務，確保您的租約在有效期內得到妥善管理和維護。
您可以隨時向管理師詢問有關租約的具體內容和權益，保障您的權益。
委託管理合約中通常包含的服務範圍包括租金收取、物業維護、租客管理、報修處理、公共設施管理以及租約更新等。
這些服務旨在確保您作為房客的居住體驗順暢且舒適。
租客在委託管理合約中享有多項權益，包括：獲得安全、舒適的居住環境、及時的維修服務、租金透明以及押金的妥善管理。
此外，若有合約變更或終止，租客需提前獲得通知，並有權了解合約內容及任何費用的明細。
管理費用的計算方式通常依據租金的百分比或固定金額來決定，具體的計算方式會在您的委託管理合約中明確列出。
建議您仔細查看合約內容，若有疑問，可以聯繫您的管理師確認。
管理費用的支付方式通常包括一次性支付或分期支付，具體方式可以根據您的合約條款而定。
如需詳細資訊，請聯繫您的管理師確認。
業者的服務費用一般是根據租金的比例來計算的，具體比例可能因合約而異，包含管理、維護等服務費用。
建議您查閱合約或聯繫管理師以獲取詳細資訊。

### 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 {#jgb/D/delegation-contract-change-termination}
- phrasings:
  - {text: "合約爭議解決", source: "question_summary:3126", status: proposed}
  - {text: "合約變更", source: "question_summary:3118", status: proposed}
  - {text: "委託管理合約終止", source: "question_summary:3116", status: proposed}
  - {text: "委託管理合約責任", source: "question_summary:3316", status: proposed}
  - {text: "委託管理合約轉讓", source: "question_summary:3261", status: proposed}
  - {text: "委託管理合約違約責任", source: "question_summary:3120", status: proposed}
  - {text: "終止合約程序", source: "question_summary:3124", status: proposed}
  - {text: "續約流程", source: "question_summary:3119", status: proposed}
- sources: [kb:3116, kb:3118, kb:3119, kb:3120, kb:3124, kb:3126, kb:3261, kb:3316]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託管理合約可以提前終止的條件通常包括：雙方協議終止、合約約定的提前終止條款、或因不可抗力事件影響等。
建議您聯繫您的管理師以獲取具體條件及流程。
要對委託管理合約進行變更，您需要聯繫您的管理師，提供具體的變更需求，並確認相關條件及程序。
管理師會協助您處理變更事宜，確保您的權益被妥善保護。
委託管理合約到期後，您可以與管理師聯繫進行續約的相關事宜。
一般來說，續約通常會根據原合約條款進行，但也可以根據您的需求進行調整。
建議提前一個月聯繫，以便有足夠時間處理續約事宜。
委託管理合約中，違約責任通常會明確規定違約方需承擔的責任，包括賠償因違約所造成的損失。
具體條款可能因合約而異，建議您仔細閱讀合約內容或聯繫您的管理師確認細節。
終止委託管理合約的程序通常包括書面通知管理公司，並根據合約條款要求終止。
建議您查看合約中有關終止的具體條款，或聯繫您的管理師以獲取詳細指導。
委託管理合約中的爭議解決方式通常包括協商、調解及仲裁。
房客可以要求與管理師進行協商，若無法達成共識，可尋求第三方調解，必要時也可進行仲裁，以保障您的權益。
委託管理合約一般是不可轉讓的，因為這涉及到雙方的合意及責任。
如果您有特殊情況，建議聯繫您的管理師以確認具體的合約條款及可能的解決方案。
委託管理合約中的違約責任通常包括違約方需賠償對方因此而產生的損失。
具體的賠償金額及條件會依合約內容而定，建議您仔細閱讀合約或詢問您的管理師以獲取詳細資訊。

### 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算） {#jgb/D/deposit-setting-and-refund-system}
- phrasings:
  - {text: "什麼時候退", source: "question_summary:4278", status: proposed}
  - {text: "兩種模式", source: "question_summary:3387", status: proposed}
  - {text: "押金多少", source: "question_summary:4263", status: proposed}
  - {text: "押金要付多少", source: "question_summary:4278", status: proposed}
  - {text: "押金計算", source: "question_summary:3387", status: proposed}
  - {text: "押金資訊", source: "question_summary:4263", status: proposed}
  - {text: "押金金額和退還方式查詢", source: "question_summary:1392", status: proposed}
  - {text: "退租押金怎麼退還", source: "question_summary:4279", status: proposed}
  - {text: "退還方式", source: "question_summary:4263", status: proposed}
- sources: [kb:3387, kb:1392, kb:4263, kb:4278, kb:4279]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
JGB 合約押金有兩種計算方式：（1）按月數計算：押金總額 = 押金月數 × 月租金，例如月租 10,000 元、押 2 個月，押金為 20,000 元；（2）固定金額：直接設定押金總額，例如固定 15,000 元。
押金在點退時結算，扣除損壞賠償和未繳費用後退還差額。
建立合約時可選擇適合的計算方式。

### 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 {#jgb/D/deposit-legal-limits}
- phrasings:
  - {text: "押金上限", source: "question_summary:2901", status: proposed}
  - {text: "押金使用規定", source: "question_summary:3215", status: proposed}
  - {text: "押金利息", source: "question_summary:2929", status: proposed}
  - {text: "押金抵扣租金", source: "question_summary:3211", status: proposed}
  - {text: "押金支付方式", source: "question_summary:2935", status: proposed}
  - {text: "押金條款", source: "question_summary:2934", status: proposed}
  - {text: "押金法律規定", source: "question_summary:3021", status: proposed}
  - {text: "押金用途", source: "question_summary:2937", status: proposed}
  - {text: "押金相關法律", source: "question_summary:3284", status: proposed}
  - {text: "押金約定", source: "question_summary:2936", status: proposed}
  - {text: "押金規定", source: "question_summary:2926", status: proposed}
  - {text: "押金轉讓", source: "question_summary:2932", status: proposed}
- sources: [kb:2901, kb:2916, kb:2926, kb:2929, kb:2932, kb:2934, kb:2935, kb:2936, kb:2937, kb:3021, kb:3211, kb:3215, kb:3284]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
根據法律規定，租賃契約中押金的上限通常是兩個月的租金。
這意味著您可以享有這一上限的保障，避免押金過高的情況。
如果有任何不明之處，建議您聯繫您的管理師確認具體情況。
押金是租客在租房時支付的一筆預付款，用於保障房東在租約期間可能發生的損失或費用。
通常在退租後，若房屋狀況良好，押金將在約定時間內全額退還。
若有損壞或未支付費用，押金可用來抵扣相關費用。
根據法律規定，租賃契約中的押金最高不得超過兩個月的租金。
這意味著您所支付的押金應該在此範圍內，若有任何疑問或需要確認的細節，建議聯繫您的管理師。
根據相關法律規定，房東並不需要支付押金的利息給租客，押金通常是用來保障房東的權益。
如果您對押金的具體條款有疑問，建議您聯繫您的管理師確認合約內容。
押金一般不可轉讓給第三方，這是為了保護您的權益及確保合約的有效性。
如果您有特殊情況，建議與您的管理師聯繫以獲取具體建議。
租賃契約中應明確押金的金額、支付方式、退還條件及時間。
建議您要求管理師提供押金的詳細規定，並確認是否有任何扣款的情況及其明細。
租客可以透過現金、銀行轉帳或第三方支付平台支付押金。
具體的支付方式可能因物件而異，建議您聯繫您的管理師確認最適合的支付方式。
租約中對押金的約定一般不能自行修改，變更須經雙方同意並簽署修正協議。
建議您與管理師聯繫確認具體情況。
押金主要是用來作為租約的保證，不能用於其他用途。
退租時，押金會根據房屋狀況進行檢查，若無損壞，會全額退還。
如有扣款，會提前告知明細。
押金通常是租賃契約中約定的金額，用於保障房東的權益，並在租約結束後根據房屋狀況進行退還。
根據法律規定，房東需在退租後的一定期限內退還押金，如有扣款應提前告知具體原因和明細。
押金不能用來抵扣租金。
押金是為了保障房東的權益，租金應按合約正常繳納。
如有其他問題，請隨時聯繫管理師。
押金是用來保障租約期間的物品損壞或租金違約等情況，無法用於其他用途。
若有任何扣款，會在退租時提前告知明細。
根據《民法》第 399 條，押金可作為租賃期間的保證，並應於租約終止後合理時間內退還。
若有扣款，需提供明細說明，保障您的權益。

### 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 {#jgb/D/deposit-deduction-refund}
- phrasings:
  - {text: "押金保管責任", source: "question_summary:2933", status: proposed}
  - {text: "押金扣除", source: "question_summary:2927", status: proposed}
  - {text: "押金扣除爭議", source: "question_summary:2931", status: proposed}
  - {text: "押金爭議解決", source: "question_summary:3212", status: proposed}
  - {text: "押金用途說明", source: "question_summary:2930", status: proposed}
  - {text: "押金管理", source: "question_summary:3154", status: proposed}
  - {text: "押金管理責任", source: "question_summary:3213", status: proposed}
  - {text: "押金與損壞賠償", source: "question_summary:3171", status: proposed}
- sources: [kb:2927, kb:2930, kb:2931, kb:2933, kb:3154, kb:3171, kb:3212, kb:3213]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東可以在以下情況下扣除押金：若房客造成房屋損壞、未支付租金、或未按照合約約定進行清潔。
扣除金額需合理，並應提前告知房客具體扣款明細。
是的，房東在扣除押金時需要提供用途說明，包括扣款的具體項目和金額。
這樣可以保障您的權益，讓您清楚了解押金的使用情況。
如果您對扣款有疑問，可以隨時聯繫您的管理師以獲取更多資訊。
如果您與房東對押金的扣除有爭議，建議首先與房東進行溝通，了解扣除的具體原因。
如果無法達成共識，可以尋求管理師的協助，或透過書面形式提出申訴，並保留相關證據以便後續處理。
房東有責任妥善保管押金，並在租約結束時根據合約約定退還押金，如有任何扣款需提前告知明細。
您可以要求房東提供押金的相關管理資訊，以保障您的權益。
押金將在租約結束後進行管理，退租時會進行檢查，若無損壞或未付費用，押金會在30天內退還至您的指定帳戶。
如有扣款，會提前告知明細。
押金是為了保障房東和租客雙方的權益。
在租約結束時，若房屋內有損壞，管理師會根據損壞程度及修繕費用來決定是否從押金中扣除相應金額。
您有權在退租時要求明細說明，確保扣款合理。
如果您與房東對押金的扣除有爭議，建議首先查看租約中的相關條款以確認雙方的權利與責任。
您可以與管理師聯繫，協助進一步溝通和調解，必要時可以尋求法律諮詢來保障您的權益。
房東有責任將押金妥善保管，並在租約結束後根據合約條款退還押金。
如果有任何扣款，房東應提前通知房客並提供詳細明細。

### 租約中的寵物押金與飼養寵物費用 {#jgb/D/tenant-pet-clauses}
- phrasings:
  - {text: "寵物押金", source: "question_summary:2928", status: proposed}
  - {text: "飼養寵物費用", source: "question_summary:2977", status: proposed}
  - {text: "租約中的物件還能再開一份嗎", source: "koyu:slug71#10", status: proposed}
- sources: [kb:2928, kb:2977]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在租賃契約中，業主可以要求寵物押金作為對可能損害的保障。
不過，具體要求需依租賃契約的條款而定，您可以與管理師確認相關細節及具體金額。
飼養寵物是否需要額外支付費用，取決於您的租約條款。
一般來說，某些租約可能會要求額外的押金或月租費用來涵蓋寵物造成的損害。
建議您查看租約內容或聯繫您的管理師以確認具體要求。

### 租屋相關保險：租屋保險費用、租客設備投保、押金投保 {#jgb/D/tenant-rental-insurance}
- phrasings:
  - {text: "押金投保", source: "question_summary:3214", status: proposed}
  - {text: "租客設備投保", source: "question_summary:3202", status: proposed}
  - {text: "租屋保險費用", source: "question_summary:3006", status: proposed}
- sources: [kb:3006, kb:3202, kb:3214]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租屋保險的費用通常依據保險公司、保險範圍及保額的不同而有所差異，一般來說，年費用可能在數千元左右。
建議您向保險公司詢問具體報價，以獲得最準確的資訊。
租客設備是否需要投保，通常取決於租約的約定。
一般來說，租客有權選擇為其個人物品投保，以避免意外損失。
建議您檢視租約內容，若有疑問可聯繫您的管理師確認具體要求。
押金投保並不是強制要求，但建議您考慮投保，以保障您的權益。
若有損壞或其他問題，投保可以幫助您減少損失。
請聯繫您的管理師了解更多詳細資訊。

### 入住注意事項與傢俱清點 {#jgb/D/move-in-inspection}
- phrasings:
  - {text: "傢俱清點", source: "question_summary:2942", status: proposed}
  - {text: "入住注意事項", source: "question_summary:2938", status: proposed}
- sources: [kb:2938, kb:2942]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
入住時請注意檢查房屋的整體狀況，包括水電設施、家具與家電的運作是否正常。
此外，請確認租約中的條款，特別是押金、租金和管理費的相關規定。
如果發現任何問題，請儘早聯繫您的管理師進行處理。
保持良好的溝通，確保您的權益獲得保障。
入住時，您可以與管理師一起進行傢俱清點。
請確認所有傢俱及設備的狀況，並記錄任何損壞或缺失。
如果有問題，建議您立即通知管理師，以便在退租時避免不必要的爭議。

### 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 {#jgb/D/tenant-move-out-obligations}
- phrasings:
  - {text: "原狀回復義務", source: "question_summary:3216", status: proposed}
  - {text: "原狀回復要求", source: "question_summary:2941", status: proposed}
  - {text: "租客物品處理", source: "question_summary:3218", status: proposed}
  - {text: "租約到期物品處理", source: "question_summary:2950", status: proposed}
  - {text: "設備狀況處理", source: "question_summary:3273", status: proposed}
  - {text: "設備處理", source: "question_summary:3191", status: proposed}
  - {text: "退租注意事項", source: "question_summary:2939", status: proposed}
  - {text: "退租清潔標準", source: "question_summary:2943", status: proposed}
  - {text: "退租清潔要求", source: "question_summary:2944", status: proposed}
  - {text: "退租物品處理", source: "question_summary:2948", status: proposed}
  - {text: "退租義務", source: "question_summary:2940", status: proposed}
  - {text: "遺留物品處理", source: "question_summary:2947", status: proposed}
- sources: [kb:2939, kb:2940, kb:2941, kb:2943, kb:2944, kb:2947, kb:2948, kb:2950, kb:3191, kb:3216, kb:3218, kb:3273]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
退租時需注意的事項包括：確認清潔狀況，保持物件原狀；提前通知管理師退租意圖；檢查所有設備是否正常運作。
此外，請確保所有個人財物已搬走，並完成點交程序，這樣才能順利退還押金。
租客在退租時需將物件恢復至原狀，這包括清潔房屋、修復任何損壞及移除個人財物。
若有損壞或未清理的情況，管理師可能會依合約規定扣除相應的押金。
建議您在退租前與管理師確認具體要求，以保障您的權益。
房東要求租客在退租時將房屋恢復到原狀，這包括保持房屋的清潔、修復任何因使用而造成的損壞，以及根據合約約定的其他要求。
租客有權獲得合理的磨損考量，並不需要負責正常使用造成的輕微損壞。
退租時的清潔標準通常包括：整體房屋清潔、地板掃除及拖洗、廁所及廚房的衛生清理、窗戶及門的清潔，以及所有家具的清理。
若有特殊損壞或污漬，可能需另行處理。
建議您在退租前與管理師確認具體要求。
房東通常會要求租客在退租時將物件清潔至入住時的狀態，包括地板、廚房、衛浴等區域。
具體要求可能會在租約中列明，建議您查看租約或聯繫管理師確認詳細清潔標準。
租客退租後遺留物品的處理方式通常是，管理師會在確認物品遺留後，依合約規定通知您。
一般來說，您有權要求管理師在一定期限內處理這些物品，並有可能需負擔相關費用。
建議您聯繫管理師確認具體流程及相關權益。
房東在租客退租後，會根據合約約定處理遺留物品。
一般來說，房東會通知租客取回遺留物品，如果在指定期限內未取回，房東有權處理這些物品。
建議您在退租時，確認所有物品是否已帶走，並了解合約中對於遺留物品的具體規定。
租約到期後，您應在約定的退租日期之前自行將物品搬出，並確保房屋內不留下任何個人財物。
如果您需要額外的搬遷協助或有特殊情況，請與您的管理師聯繫，以獲取更多資訊。
租期結束時，您需要檢查並確保所有設備的狀況良好。
若有損壞或故障，請及時通知管理師進行維修或更換，以免影響押金的退還。
建議您在退租前拍攝設備的照片作為證據，保留良好記錄。
在退租時，租客有義務將租屋恢復至原狀，這包括清理室內外的垃圾、修補任何損壞的地方，以及保證房屋內部的設施功能正常。
若有任何損壞或清潔不足，房東有權從押金中扣除相應的費用。
建議您提前檢查合約中的具體條款，以確保遵守相關規定，並保護您的權益。
租約到期後，您有責任自行處理在租屋內的物品。
建議您在搬遷前提前安排好物品的搬運及清理，確保不遺留任何私人物品。
如果有任何物品留下，可能會導致額外的清理費用或押金扣款。
租期結束時，您需檢查並整理設備狀況，確保所有設備運作正常。
如有損壞或異常，請及時通知管理師，以便進行維修或處理。
這樣有助於順利退還押金，並避免不必要的費用扣除。

### 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） {#jgb/D/lease-termination-notice-rules}
- phrasings:
  - {text: "提前終止租約", source: "question_summary:2953", status: proposed}
  - {text: "提前解約規定", source: "question_summary:2958", status: proposed}
  - {text: "提前解約通知", source: "question_summary:2955", status: proposed}
  - {text: "提前通知", source: "question_summary:2951", status: proposed}
  - {text: "搬遷要求", source: "question_summary:2952", status: proposed}
  - {text: "租約有效性", source: "question_summary:2957", status: proposed}
  - {text: "租約終止", source: "question_summary:2959", status: proposed}
  - {text: "租約終止通知", source: "question_summary:3217", status: proposed}
  - {text: "租約處理", source: "question_summary:2956", status: proposed}
  - {text: "終止租約", source: "question_summary:3022", status: proposed}
  - {text: "終止租約通知", source: "question_summary:2949", status: proposed}
- sources: [kb:2949, kb:2951, kb:2952, kb:2953, kb:2955, kb:2956, kb:2957, kb:2958, kb:2959, kb:3022, kb:3217]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客需要提前至少 30 天通知房東終止租約。
建議您以書面形式通知，以確保有紀錄可循。
根據租約規定，租客在搬遷前通常需提前通知房東至少一個月。
建議您檢查您的租約，確認具體的通知期限，以確保您的權益受到保障。
房東要求租客搬遷時，通常需要提前通知，並且必須遵循租約中的相關條款。
租客有權獲得合理的通知時間，通常為30天，具體依合約內容而定。
若房東無法合法要求租客搬遷，租客可以維護自己的權益，並尋求管理師的協助。
房東可以在租客未支付租金、違反合約條款、或對房屋造成重大損害等情況下依法提前終止租約。
若發生這些情況，房東需根據合約規定通知您，並且通常需要給予合理的解約通知時間。
建議您與管理師確認具體的合約條款，以保護自己的權益。
租客提前解約通常需要提前通知房東至少30天，具體時間請參考您的租約條款。
如果您有任何疑問或希望確認詳情，建議聯繫您的管理師以獲取正確的資訊。
如果租客失蹤，房東應首先查看租約中有關解約的條款。
一般來說，房東可以依據租約條款提前終止租約，但需要遵循法律規定，例如發出正式通知。
此外，房客在租約內的權益仍然受到保護，如有任何爭議，建議與管理師聯繫以獲取具體指導。
如果租客失蹤，租約仍然有效，除非有明確的提前解約條款或雙方同意終止租約。
建議您與管理師聯繫確認具體情況及後續步驟。
在不定期租約中，租客需提前通知管理師，並按照合約中的約定條件提前解約。
建議查看合約內的相關條款，確保遵循通知期限及解約程序，以避免違約責任。
房東可以根據租約約定的條款合法終止不定期租約，通常需要提前通知租客並符合相關法律規定，具體情況建議您聯繫管理師確認。
您有權要求房東提供合法的終止理由，並確保您的權益不受侵害。
租客可以在以下情況終止租約：房東未能履行租約條款、租屋環境不符合居住標準、或因不可抗力因素如自然災害等。
建議您提前通知管理師，並查看租約中的相關條款以確保您的權益。
房東終止租約需提前通知租客，通常這段時間為合約中規定的天數，建議您查閱您的租約以確認具體要求。
如果有任何疑問，請聯繫您的管理師以獲取詳細資訊。

### 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 {#jgb/D/breach-penalty-rules}
- phrasings:
  - {text: "提前解約後果", source: "question_summary:3285", status: proposed}
  - {text: "提前解約法律後果", source: "question_summary:2962", status: proposed}
  - {text: "提前解約證據", source: "question_summary:2961", status: proposed}
  - {text: "租屋合約違約責任", source: "question_summary:3294", status: proposed}
  - {text: "違約責任", source: "question_summary:2903", status: proposed}
  - {text: "違約金上限", source: "question_summary:2954", status: proposed}
  - {text: "違約金計算", source: "question_summary:2960", status: proposed}
- sources: [kb:2903, kb:2954, kb:2960, kb:2961, kb:2962, kb:3285, kb:3294]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租賃契約中的違約責任通常是指如果租客或房東未能履行契約條款，可能會承擔的責任與後果。
對於房客而言，這可能包括提前終止合約的罰金或損失賠償等。
建議仔細查看契約細則，並在有疑問時諮詢管理師以了解自身權益及義務。
根據台灣租賃法，違約金的上限不得超過租金的兩個月。
如果您需要進一步了解或有其他問題，建議聯繫您的管理師確認具體條款。
違約金的計算通常依據您的租約條款而定，可能是剩餘租期租金的某個百分比或固定金額。
建議您查看租約中的違約金條款，或聯繫您的管理師以獲取具體資訊。
在提前解約的情況下，租客應保留以下證據：租約副本、提前解約的書面通知、與房東或管理師的通訊紀錄（如電子郵件或簡訊），以及任何與解約相關的文件或收據。
這些證據將有助於保護您的權益，避免未來的爭議。
提前解約可能會導致租客需要支付違約金，具體金額依合約而定。
此外，若未提前通知，可能會影響押金的退還。
建議仔細閱讀租約的解約條款，並與管理師聯繫以獲取具體建議。
提前解約可能會導致您需要支付違約金，具體金額依合約而定。
此外，您可能會失去部分或全部押金。
建議您仔細閱讀合約條款，必要時與管理師聯繫以了解詳細情況及您的權益。
租屋合約中違約的責任通常會明確規定，若房客提前解約，可能需支付違約金或承擔相應的損失賠償責任。
具體條款可參考合約內容，並建議與管理師確認以獲取詳細資訊。

### 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助 {#jgb/D/tenant-renewal-and-extension-rights}
- phrasings:
  - {text: "延住規定", source: "question_summary:2946", status: proposed}
  - {text: "租約延住", source: "question_summary:2945", status: proposed}
  - {text: "租約續約", source: "question_summary:3153", status: proposed}
  - {text: "租賃契約續約", source: "question_summary:2898", status: proposed}
  - {text: "續約規定", source: "question_summary:3204", status: proposed}
- sources: [kb:2898, kb:2945, kb:2946, kb:3153, kb:3204]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租賃契約的續約規定通常會在租賃契約中明確說明，您可以選擇在租期終了前通知管理師是否續約。
若未提前通知，契約可能自動續約或終止，具體依合約條款而定。
建議您仔細閱讀契約內容，或直接聯繫管理師確認。
租約到期後的延住需事先與管理師確認，並依合約條款進行申請。
若合約中有延住的選項，您可以在到期前提出申請，並同時確認延住的租金及條件。
房東對於租客延住的看法通常會依據租約的條款而定。
若租約中有延住的相關規定，建議您遵循合約內容，並提前通知管理師，協助您確認是否可以延住及相關的費用問題。
您有權在合約期限內協商延住事宜，並了解可能的租金調整或其他條件。
是的，我們業者會協助處理租約續約事宜。
在續約過程中，您可以獲得相關的資訊和幫助，以確保續約順利進行。
如果您有任何特定的需求或問題，請隨時告訴我們。
租賃契約的續約規定通常會在合約中明確說明。
一般來說，續約需要提前通知，並且續約條件會依據原合約的約定進行。
建議您查看您的租賃契約或聯繫管理師以獲取具體的續約條件和流程。

### 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） {#jgb/D/lease-clauses-interpretation}
- phrasings:
  - {text: "合約條款", source: "question_summary:3159", status: proposed}
  - {text: "合約條款解釋", source: "question_summary:3034", status: proposed}
  - {text: "租屋合約條款解釋", source: "question_summary:3296", status: proposed}
  - {text: "租屋合約變更", source: "question_summary:3028", status: proposed}
  - {text: "租約條款解釋", source: "question_summary:3239", status: proposed}
  - {text: "租金包含服務", source: "question_summary:3209", status: proposed}
  - {text: "租金支付法律依據", source: "question_summary:2924", status: proposed}
  - {text: "租金爭議解決", source: "question_summary:3210", status: proposed}
- sources: [kb:2924, kb:3028, kb:3034, kb:3159, kb:3209, kb:3210, kb:3239, kb:3296]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租金支付的法律依據主要來自於租賃契約，該契約會明確規定租金的金額、支付方式及支付期限等條款。
根據法律，房客有權要求房東或管理公司依約收取租金，並應提供相應的收據或證明。
您也可以向管理師查詢相關條款，確保自己的權益受到保障。
租屋合約的變更需要雙方協商一致，並遵循《民法》相關規定。
變更內容需以書面形式確認，並取得雙方簽名，這樣才能保障您的權益。
若您對合約的具體條款有疑問，建議聯繫您的管理師確認。
租屋合約中的條款通常需要根據具體內容進行解釋。
如果您對某些條款有疑問，建議您可以聯繫您的管理師進行詳細說明，確保您了解自己的權益及義務。
合約條款中重要的內容包括租金金額、付款方式、租約期限、押金金額及退還條件、維修責任、解約條件等。
這些條款保障了您的權益，並明確雙方的責任與義務，建議您仔細閱讀合約內容，若有疑問可與管理師聯繫確認。
租金通常包含以下項目：
1. 房屋租金本身
2. 管理費用
3. 公共區域的清潔、維護及保安服務
部分租約也可能包含水電費、網路費及公共設施使用費，具體內容會依租約條款而定。
建議您查看租約或聯繫管理師確認詳細項目。
租金爭議可以透過協商、調解和法律途徑來解決。
首先，您可以嘗試與管理師直接溝通，尋求問題的解決方案。
如果無法達成共識，可以考慮尋求第三方調解服務，或是向相關政府單位申訴。
若情況仍未改善，最終可以通過法律途徑解決，建議您保留所有相關的證據文件以便使用。
租屋合約中的條款通常會在合約附帶的說明中進行解釋。
若您對某些條款有疑問，建議直接與您的管理師聯繫，管理師可以針對您的個別情況提供詳細的解釋，並確保您的權益受到保障。
租屋合約中的條款通常會詳細說明租客和房東的權利與義務。
若您不清楚某些條款的意義，建議可以向您的管理師詢問，確保您了解自己的權益及責任。

### 租約中的設備與公共設備使用規範 {#jgb/D/equipment-usage-under-lease}
- phrasings:
  - {text: "公共設備使用規範", source: "question_summary:3201", status: proposed}
  - {text: "公共設備使用限制", source: "question_summary:3196", status: proposed}
  - {text: "租屋設備使用規範", source: "question_summary:3290", status: proposed}
  - {text: "設備使用規範", source: "question_summary:2989", status: proposed}
- sources: [kb:2989, kb:3290, kb:3196, kb:3201]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客在使用租屋內的設備時，應遵循合約中列明的使用規範，例如不得隨意改裝設備、妥善維護並報告任何故障。
若設備出現問題，請及時聯繫管理師進行維修，這是您的權利與責任。
租客在使用租屋內設備時，應遵循合約中約定的規範，通常包括妥善使用設備、定期維護以及不得私自改動設備設置等。
此外，若設備出現故障，請及時聯繫管理師報修，確保問題能夠迅速處理，保障您的居住權益。
租客對公共設備的使用通常會有一些基本的限制，例如使用時間、使用人數或遵守社區規範等。
具體的使用規則會在租約中列明，您可以參考租約內容或直接詢問您的管理師以獲取詳細信息。
公共設備的使用規範通常包括不打擾他人、保持設備清潔，以及遵守使用時間等要求。
具體規範可能因物件而異，建議您查看租約或與管理師確認詳細規定。

### 租屋期間戶籍遷移與居住證明 {#jgb/D/household-registration-under-lease}
- phrasings:
  - {text: "居住證明費用", source: "question_summary:3047", status: proposed}
  - {text: "戶籍登記與租約", source: "question_summary:3043", status: proposed}
  - {text: "戶籍遷移", source: "question_summary:3035", status: proposed}
- sources: [kb:3035, kb:3043, kb:3047]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客在租屋期間是可以遷移戶籍的，這不影響租約的有效性。
不過，建議您在遷移戶籍前，先與房東或管理師確認相關規定，確保不會影響您的租住權益。
戶籍登記可以作為您的居住證明，這對於某些行政手續或享有租屋相關的權益是有幫助的。
租約則是您與房東之間的法律文件，確認您的居住權利和租金條件。
通常，您在租屋時，應該依據租約上的地址進行戶籍登記，以確保合法居住。
申請居住證明一般是免費的，您不需要支付任何費用。
建議您確認具體的申請流程和要求，以確保一切順利。

### 轉租與分租的租約條款與押金處理 {#jgb/D/sublease-and-shared-lease-terms}
- phrasings:
  - {text: "分租租約條款", source: "question_summary:3079", status: proposed}
  - {text: "押金處理", source: "question_summary:3077", status: proposed}
  - {text: "轉租租約條款", source: "question_summary:3078", status: proposed}
- sources: [kb:3077, kb:3078, kb:3079]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
轉租時，押金的處理通常由原租客與新租客協商。
如果原租客將押金轉交給新租客，請確保在轉租合約中明確載明，以保障雙方權益。
如果有疑問，建議聯繫您的管理師確認具體流程。
轉租的租約應包含以下條款：轉租方與承租方的基本資訊、租金金額及支付方式、租約期限、轉租物件的使用規範、押金的處理方式、以及雙方的權利義務等。
此外，需明確規定轉租的條件及是否需要原出租方的同意，以保障您的權益。
分租的租約中應包含租金金額、支付方式、租約期限、押金條款、使用權限、維護責任、終止條款及分租者的權利與義務等。
這些條款可以保障您的權益，讓您在租住期間更加安心。

### 社會住宅租約與一般租約的差異、期限與終止 {#jgb/D/social-housing-lease}
- phrasings:
  - {text: "社會住宅租約期限", source: "question_summary:3132", status: proposed}
  - {text: "社會住宅租約終止", source: "question_summary:3134", status: proposed}
  - {text: "社會住宅與租約差異", source: "question_summary:3131", status: proposed}
  - {text: "租約期限", source: "question_summary:3318", status: proposed}
- sources: [kb:3131, kb:3132, kb:3134, kb:3318]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社會住宅通常是由政府提供的較為經濟實惠的租住選擇，租金較一般市場租約低，且有保障的居住權利。
此外，社會住宅會設有申請資格，優先考量低收入家庭或特定族群。
一般租約則較為靈活，但租金和條件多變，租客權益相對較少。
社會住宅的租約期限通常為兩年，租客在租約到期後可以選擇續租，具體條件需依照相關政策和管理機構的規定。
建議您向管理師確認具體的租約期限和續租流程。
社會住宅的租約可以在以下情況下終止：租客主動提出終止、租客違反租約條款、房屋進行重大修繕或重建等。
建議您檢視租約內容，確保了解自己的權益。
如有疑問，請聯繫您的管理師確認。
社會住宅的租約期限通常為兩年，期滿後可依照相關規定申請續約，具體情況建議您諮詢您的管理師以獲得詳細資訊。

### 租約公證：是什麼、去哪辦、費用、對房東房客的保障、與租補關係、公證合約如何上傳 {#jgb/D/lease-notarization}
- phrasings:
  - {text: "租約公證?房東房客都應該關注的保障", source: "helpcenter:rent3", status: proposed}
- sources: [helpcenter:rent3]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
租約公證是指租賃雙方訂立書面契約後，向地方法院公證處或民間公證人事務所領取公證請求書，填妥後交由公證處收件登記，由公證人辦理。
租約經公證後，承租人交還房屋、給付租金及違約金、出租人返還押租金等事項，不須訴訟就可以請求法院強制執行。
辦理公證可持請求書和租賃契約書三份，於法院上班時間前往地方法院公證處申請；不想跑法院也可以找鄰近的民間合法公證人事務所辦理。
公證費用以租金總額或房屋課稅現值二者較高者加上保證金計算，20 萬元以下收 1000 元，20 萬至 50 萬元 2000 元，逾 50 萬至 100 萬元 3000 元，逾 100 萬至 200 萬元 4000 元，逾 200 萬至 500 萬元 5000 元，逾 500 萬至 1000 萬元 6000 元，逾 1000 萬至 5000 萬元的超過部分每 1000 萬元加收 2000 元，逾 5000 萬元的超過部分每 1000 萬元加收 1000 元，不滿 1000 萬元按 1000 萬元計算；若附加強制執行條款，費用加收二分之一。
對房東而言，遇到不付租金、拒付違約金或租期屆滿拒不搬遷的房客，可直接持公證書向法院聲請強制執行，公證書具有與判決相同的執行力。
對租客而言，房東於租期屆滿後拒不返還押租金、或租期內無故要求提前終止租約時，同樣可持公證書聲請強制執行；公證後租金、押金與租賃期限都有法律層面的明確記錄，可防止房東事後片面更改條件。
申請租金補貼需檢附申請書、租賃契約影本、戶口名簿影本或全戶戶籍謄本、特殊家庭成員證明等文件，依內政部法規公告，租賃契約並未以「已公證」為補貼要件。
想在 JGB 平台留存公證合約，可將房東、租客、代書三方簽訂完成的公證合約以上傳既存合約的方式上傳，系統可協助綁定租客帳號並追蹤後續提前解約、續約、帳務管理與修繕報修，功能與系統合約相同。
