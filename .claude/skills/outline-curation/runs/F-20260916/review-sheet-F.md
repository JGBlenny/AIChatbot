# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/F/repair-progress-followup-scope` | 修繕進度追問可答範圍 | `jgb/F/repair-progress-followup-scope` | 修繕進度追問可答範圍與查詢方式 | keep | F/F/F | |
| 2 | `tmp:canon:jgb/F/repair-system` | 線上報修與進度追蹤 | `jgb/F/repair-system` | 線上報修與進度追蹤 | keep | F/F/F | |
| 3 | `tmp:canon:jgb/F/repair-ticket-after-submit` | 確認送出後的單如何處理 | `jgb/F/repair-ticket-after-submit` | 確認送出後的單如何處理 | keep | F/F/F | |
| 4 | `tmp:canon:jgb/F/repair-ticket-mid-flow-cancel` | 報修流程中途取消的規則 | `jgb/F/repair-ticket-mid-flow-cancel` | 報修流程中途取消的規則 | keep | F/F/F | |
| 5 | `tmp:canon:jgb/F/repair-ticket-no-lease` | 代開單時的租約查詢身分與空屋／無租約物件開單規則 | `jgb/F/repair-ticket-no-lease` | 代開單時的租約查詢身分與空屋／無租約物件開單規則 | keep | F/F/F | |
| 6 | `tmp:canon:jgb/F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | `jgb/F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | keep | F/F/F | |
| 7 | `tmp:canon:jgb/F/repair-ticket-photo-count-limit` | 修繕辨識與附件的照片張數限制 | `jgb/F/repair-ticket-photo-count-limit` | 修繕辨識與附件的照片張數限制 | keep | F/F/F | |
| 8 | `tmp:canon:jgb/F/repair-ticket-photo-recognition-uncertain` | 照片辨識信心不足或看不出損壞時的處理 | `jgb/F/repair-ticket-photo-recognition-uncertain` | 照片辨識信心不足或看不出損壞時的處理 | keep | F/F/F | |
| 9 | `tmp:canon:jgb/F/repair-ticket-reclassify` | 確認卡上修改辨識結果的規則 | `jgb/F/repair-ticket-reclassify` | 確認卡上修改辨識結果的規則 | keep | F/F/F | |
| 10 | `tmp:canon:jgb/F/repair-ticket-submit-failure` | 建單失敗時的處理與重試規則 | `jgb/F/repair-ticket-submit-failure` | 建單失敗時的處理與重試規則 | keep | F/F/F | |
| 11 | `tmp:canon:jgb/F/repair-ticket-urgency-judgment` | 修繕單急迫程度的判斷來源與值域 | `jgb/F/repair-ticket-urgency-judgment` | 修繕單急迫程度的判斷來源與值域 | keep | F/F/F | |
| 12 | `tmp:kb:1558` | 維修進度查詢 | `jgb/F/repair-progress-followup-scope` | 修繕進度追問可答範圍與查詢方式 | merge | F/F/F | |
| 13 | `tmp:kb:2963` | 房屋修繕責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 14 | `tmp:kb:2964` | 修繕責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 15 | `tmp:kb:2965` | 緊急修繕 | `jgb/F/tenant-emergency-self-repair` | 緊急情況下租客自行修繕的條件、事後通知與費用報銷 | new | F/F/F | |
| 16 | `tmp:kb:2966` | 修繕通知 | `jgb/F/tenant-repair-notification-duty` | 租客發現需修繕時的通知義務與要求合理期限修繕的權利 | new | F/F/F | |
| 17 | `tmp:kb:2967` | 漏水修繕責任 | `jgb/F/neighbor-leak-responsibility` | 鄰居漏水的修繕責任與處理 | new | F/F/F | |
| 18 | `tmp:kb:2968` | 修繕費用負擔 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 19 | `tmp:kb:2969` | 修繕條款 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 20 | `tmp:kb:2970` | 公共設施維護 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 21 | `tmp:kb:2971` | 維護責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 22 | `tmp:kb:2972` | 修繕請求 | `jgb/F/repair-request-how-to-submit` | 在系統提出修繕申請的步驟與需填資料（租客／房東） | new | F/F/F | |
| 23 | `tmp:kb:2973` | 修繕義務 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 24 | `tmp:kb:2974` | 修繕責任爭議 | `jgb/F/repair-responsibility-dispute` | 修繕責任有爭議時的處理 | new | F/F/F | |
| 25 | `tmp:kb:2975` | 修繕保固期 | `jgb/F/repair-warranty-period` | 修繕後的保固期 | new | F/F/F | |
| 26 | `tmp:kb:3029` | 維修責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 27 | `tmp:kb:3030` | 房屋維修責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 28 | `tmp:kb:3145` | 緊急維修服務 | `jgb/F/emergency-repair-flag-and-handling` | 緊急修繕的標記、優先處理與回應時效 | new | F/F/F | |
| 29 | `tmp:kb:3186` | 公共設備維護 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 30 | `tmp:kb:3187` | 租客設備維護 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 31 | `tmp:kb:3188` | 公共設備損壞責任 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 32 | `tmp:kb:3189` | 設備損壞責任 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 33 | `tmp:kb:3190` | 公共設備檢查 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 34 | `tmp:kb:3192` | 公共設備維護費 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 35 | `tmp:kb:3193` | 設備維護費用 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 36 | `tmp:kb:3194` | 公共設備更新責任 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 37 | `tmp:kb:3195` | 設備更新責任 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 38 | `tmp:kb:3197` | 設備維護記錄 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 39 | `tmp:kb:3198` | 設備使用責任 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 40 | `tmp:kb:3200` | 設備損壞賠償 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 41 | `tmp:kb:3203` | 維護責任範圍 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 42 | `tmp:kb:3219` | 修繕通知義務 | `jgb/F/tenant-repair-notification-duty` | 租客發現需修繕時的通知義務與要求合理期限修繕的權利 | new | F/F/F | |
| 43 | `tmp:kb:3220` | 自行修繕 | `jgb/F/tenant-emergency-self-repair` | 緊急情況下租客自行修繕的條件、事後通知與費用報銷 | new | F/F/F | |
| 44 | `tmp:kb:3221` | 修繕維護責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 45 | `tmp:kb:3222` | 租屋設施維護責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 46 | `tmp:kb:3272` | 設備維護責任 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 47 | `tmp:kb:3274` | 公共設備維護費用 | `jgb/F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | new | F/F/F | |
| 48 | `tmp:kb:3275` | 租客設備責任 | `jgb/F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | new | F/F/F | |
| 49 | `tmp:kb:3277` | 房東維護責任 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 50 | `tmp:kb:3286` | 修繕通知責任 | `jgb/F/tenant-repair-notification-duty` | 租客發現需修繕時的通知義務與要求合理期限修繕的權利 | new | F/F/F | |
| 51 | `tmp:kb:3287` | 修繕費用分擔 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 52 | `tmp:kb:3288` | 修繕權限 | `jgb/F/tenant-emergency-self-repair` | 緊急情況下租客自行修繕的條件、事後通知與費用報銷 | new | F/F/F | |
| 53 | `tmp:kb:3289` | 修繕責任約定 | `jgb/F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | new | F/F/F | |
| 54 | `tmp:kb:3320` | 社會住宅維修責任 | `jgb/F/social-housing-repair-responsibility` | 社會住宅的維修責任 | new | F/F/F | |
| 55 | `tmp:kb:3365` | 修繕進度 修繕查詢 | `jgb/F/repair-progress-followup-scope` | 修繕進度追問可答範圍與查詢方式 | merge | F/F/F | |
| 56 | `tmp:kb:3424` | 修繕流程 狀態說明 | `jgb/F/repair-flow-stages` | 修繕流程六階段與各狀態意義 | new | F/F/F | |
| 57 | `tmp:kb:3425` | 修繕費用 結算方式 | `jgb/F/repair-cost-recording-and-settlement` | 修繕費用的記錄、分擔與結單自動產生修繕費帳單 | new | F/F/F | |
| 58 | `tmp:kb:3426` | 緊急修繕 判定處理 | `jgb/F/emergency-repair-flag-and-handling` | 緊急修繕的標記、優先處理與回應時效 | new | F/F/F | |
| 59 | `tmp:kb:3427` | 修繕申請 報修方式 | `jgb/F/repair-request-how-to-submit` | 在系統提出修繕申請的步驟與需填資料（租客／房東） | new | F/F/F | |
| 60 | `tmp:kb:3446` | 提出修繕 報修步驟 | `jgb/F/repair-request-how-to-submit` | 在系統提出修繕申請的步驟與需填資料（租客／房東） | new | F/F/F | |
| 61 | `tmp:kb:3488` | 修繕受理派工 安排廠商 | `jgb/F/repair-dispatch-and-close` | 業者受理報修、安排廠商、完工登錄到結單封存的操作 | new | F/F/F | |
| 62 | `tmp:kb:4249` | 收到租客修繕申請 怎麼受理處理 | `jgb/F/repair-dispatch-and-close` | 業者受理報修、安排廠商、完工登錄到結單封存的操作 | new | F/F/F | |
| 63 | `tmp:kb:4416` | 報修 修繕 東西壞了 想報修 | `jgb/F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | merge | F/F/F | |
| 64 | `tmp:kb:4418` | 馬桶不通 排水堵塞 水管堵住 | `jgb/F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | merge | F/F/F | |
| 65 | `tmp:kb:4420` | 修繕進度 報修單 修得怎樣了 處理到哪 | `jgb/F/repair-progress-followup-scope` | 修繕進度追問可答範圍與查詢方式 | merge | F/F/F | |
| 66 | `tmp:kb:4421` | 漏水 滲水 天花板漏水 水管漏水 | `jgb/F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | merge | F/F/F | |
| 67 | `tmp:kb:4422` | 冷氣壞了 電器壞了 家電故障 | `jgb/F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | merge | F/F/F | |
| 68 | `tmp:kb:4654` | 報修多個品項 都壞了分開報嗎 一張報修單 | `jgb/F/repair-multiple-items-one-ticket` | 多個品項是否分開報修（合併在一張報修單） | new | F/F/F | |

## B. 拆分（split）——一個舊細目拆成多個新細目

（本次無拆分）

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/F/common-equipment-maintenance-responsibility`《公共設備的維護、損壞、更新、費用與檢查紀錄責任》 | `tmp:kb:2970`＋`tmp:kb:3186`＋`tmp:kb:3188`＋`tmp:kb:3190`＋`tmp:kb:3192`＋`tmp:kb:3194`＋`tmp:kb:3197`＋`tmp:kb:3274` | 三角度來源集合一致：以「公共設備」為主體的責任問題（維護／損壞／更新／費用由房東或管理方、檢查頻率依管理規定、需留維護紀錄）合為一題，主體與房屋本體、租客設備不同故分立；slug 採 user_question_path。 | |
| `jgb/F/emergency-repair-flag-and-handling`《緊急修繕的標記、優先處理與回應時效》 | `tmp:kb:3145`＋`tmp:kb:3426` | 三角度一致（來源 3145＋3426、兩受眾共用）：業者提供緊急維修服務與系統緊急標記的意義／排序互相依賴才完整，對潛在客戶與業者答案相同；對話建單急迫值域另見 repair-ticket-urgency-judgment，租客自行修繕另見 tenant-emergency-self-repair。 | |
| `jgb/F/repair-dispatch-and-close`《業者受理報修、安排廠商、完工登錄到結單封存的操作》 | `tmp:kb:3488`＋`tmp:kb:4249` | 三角度一致合併：兩筆都是業者端受理→派工→完工→結單→封存的操作步驟，互補合一；階段定義另見 repair-flow-stages；slug 採 audience_level。 | |
| `jgb/F/repair-progress-followup-scope`《修繕進度追問可答範圍與查詢方式》 | `tmp:kb:tmp:canon:jgb/F/repair-progress-followup-scope`＋`tmp:kb:1558`＋`tmp:kb:3365`＋`tmp:kb:4420` | 三角度一致：查修繕進度是同一主題同一受眾同一層級，既有細目定可答欄位，1558／4420 補查詢入口與無單時導向報修的講法，3365 空內文只當入口；id 不變。 | |
| `jgb/F/repair-request-how-to-submit`《在系統提出修繕申請的步驟與需填資料（租客／房東）》 | `tmp:kb:2972`＋`tmp:kb:3427`＋`tmp:kb:3446` | 採 user_question_path 與 content_boundary 多數：三筆都是系統頁面報修要填什麼、步驟與提交後的通知追蹤，與對話開單細目是不同介面層；售前會問租客怎麼報修故兩受眾共用。 | |
| `jgb/F/repair-responsibility-landlord-vs-tenant`《房屋修繕責任劃分（房東與租客各負責什麼、費用誰出）》 | `tmp:kb:2963`＋`tmp:kb:2964`＋`tmp:kb:2968`＋`tmp:kb:2969`＋`tmp:kb:2971`＋`tmp:kb:2973`＋`tmp:kb:3029`＋`tmp:kb:3030`＋`tmp:kb:3203`＋`tmp:kb:3221`＋`tmp:kb:3222`＋`tmp:kb:3277`＋`tmp:kb:3287`＋`tmp:kb:3289` | 三角度同 id：14 筆講同一命題（結構與固定設施歸房東、日常小修與使用不當歸租客、以租約為準）各自只講一方，合為一題；租客責任題留 F 標 property_manager；3221 修繕後維持狀態責任併入；社宅變體另立細目（採 A／B 多數）。 | |
| `jgb/F/repair-ticket-open-and-confirm`《開修繕單基本流程與確認機制（拍照進場／文字口述）》 | `tmp:kb:tmp:canon:jgb/F/repair-ticket-open-and-confirm`＋`tmp:kb:4416`＋`tmp:kb:4418`＋`tmp:kb:4421`＋`tmp:kb:4422` | 採 user_question_path 與 content_boundary 多數：四筆空內文症狀列（想報修／馬桶不通／漏水／冷氣壞）是使用者在對話裡開口即進入對話開單流程的入口講法，只當本細目入口不獨立成細目；id 不變。 | |
| `jgb/F/tenant-emergency-self-repair`《緊急情況下租客自行修繕的條件、事後通知與費用報銷》 | `tmp:kb:2965`＋`tmp:kb:3220`＋`tmp:kb:3288` | 採 content_boundary 與 audience_level 多數：2965（租客可於影響安全健康時緊急修繕並保留證據）與 3220／3288 同屬租客權益層，三筆合一；與系統緊急標記分屬不同層，以另見處理。 | |
| `jgb/F/tenant-equipment-maintenance-responsibility`《租客設備的使用、維護、損壞賠償、更新與費用責任》 | `tmp:kb:3187`＋`tmp:kb:3189`＋`tmp:kb:3193`＋`tmp:kb:3195`＋`tmp:kb:3198`＋`tmp:kb:3200`＋`tmp:kb:3272`＋`tmp:kb:3275` | 三角度來源集合一致：以「租客設備」為主體（日常保養、正常磨損由房東、不當使用由租客賠償、賠償標準由管理師評估、更新與維護費由房東）合為一題；賠償金額屬責任歸屬不屬計費故留 F；slug 採 user_question_path。 | |
| `jgb/F/tenant-repair-notification-duty`《租客發現需修繕時的通知義務與要求合理期限修繕的權利》 | `tmp:kb:2966`＋`tmp:kb:3219`＋`tmp:kb:3286` | 三角度來源集合一致：租客的通知義務與要求合理期限修繕的權利是法定義務／權利命題，非系統通知投遞管道，故獨立成細目；slug 採 user_question_path。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| audience_level：把空內文症狀列 4416／4418／4421／4422 掛到系統報修步驟細目（repair-request-submit-steps）而非對話開單細目。 | 這四筆是使用者在對話裡開口的入口講法，開口即進入對話代開單流程；user_question_path 與 content_boundary 多數皆掛 repair-ticket-open-and-confirm，且空內文列只當入口。 | |
| user_question_path：把 kb 2965（緊急修繕）併入緊急標記細目 emergency-repair-handling（三受眾共用）。 | 2965 講的是租客可於影響安全健康時自行緊急修繕並保留證據，屬租客權益層而非系統標記層；content_boundary 與 audience_level 多數併入租客自行修繕細目。 | |
| audience_level：把 kb 3320（社會住宅維修責任）併入 repair-responsibility-landlord-vs-tenant。 | 社宅答案主體是管理單位，與房東／租客通則不同，併入會混淆對象；user_question_path 與 content_boundary 多數獨立成細目。 | |
| content_boundary：kb 3425 修繕費用記錄細目 target_user 標 prospect＋property_manager。 | 費用欄位記錄與結單開帳單是業者操作步驟，售前能力層已由 repair-system 承接；user_question_path 與 audience_level 多數標 property_manager。 | |
| audience_level：系統報修步驟細目 target_user 只標 property_manager，且吸收 7 筆來源。 | 售前會問「租客怎麼報修」且答案相同，user_question_path 與 content_boundary 多數標兩受眾；來源以 2972／3427／3446 三筆為準（症狀列另歸對話開單）。 | |
| content_boundary 與 audience_level 為既有 repair-progress-followup-scope 的標題分歧：A／B 沿用「修繕進度追問可答範圍」。 | 新材料補入查詢入口講法，採 audience_level 的標題「…與查詢方式」以反映吸收後範圍；id 不變。 | |
| slug 分歧（緊急標記）：user_question_path emergency-repair-handling、audience_level repair-emergency-flag-and-priority。 | 採 content_boundary 的 emergency-repair-flag-and-handling，因其來源集合（3145＋3426）與多數裁決一致且名稱明示「標記」以與 urgency-judgment 區隔。 | |
| slug 分歧（租客自行修繕）：user_question_path tenant-self-repair-in-emergency、audience_level repair-tenant-emergency-self-repair。 | 採 content_boundary 的 tenant-emergency-self-repair，來源集合與多數裁決一致；三者語義相同，擇一即可。 | |
| slug 分歧（公共設備／租客設備）：content_boundary common-facility-maintenance／tenant-equipment-responsibility、audience_level repair-common-facility-responsibility／repair-tenant-equipment-responsibility。 | 採 user_question_path 的 common-equipment-maintenance-responsibility／tenant-equipment-maintenance-responsibility，兩者對稱命名且與材料標題「公共設備／租客設備」用字一致。 | |
| slug 分歧（通知義務）：content_boundary tenant-repair-notice-obligation、audience_level repair-notify-duty-and-timely-repair-right。 | 採 user_question_path 的 tenant-repair-notification-duty；標題補「要求合理期限修繕的權利」以涵蓋 3219／2969 的權利面。 | |
| slug 分歧（費用記錄）：user_question_path repair-fee-recording-and-billing、audience_level repair-cost-record-and-bill。 | 採 content_boundary 的 repair-cost-recording-and-settlement，與材料標題「結算方式」對應。 | |
| slug 分歧（系統報修步驟）：content_boundary repair-request-submission-in-system、audience_level repair-request-submit-steps。 | 採 user_question_path 的 repair-request-how-to-submit，貼近使用者問法。 | |
| slug 分歧（業者派工）：user_question_path repair-dispatch-and-close-by-manager、content_boundary repair-intake-and-dispatch。 | 採 audience_level 的 repair-dispatch-and-close，最短且涵蓋受理到結單封存全程。 | |
| slug 分歧（多品項、鄰損）：audience_level repair-request-multiple-items、repair-neighbor-leak-responsibility。 | 採 user_question_path 與 content_boundary 共同使用的 repair-multiple-items-one-ticket、neighbor-leak-responsibility（兩角度一致）。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 26 | 0 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/F/common-equipment-maintenance-responsibility` | merge |
| `jgb/F/emergency-repair-flag-and-handling` | merge |
| `jgb/F/repair-dispatch-and-close` | merge |
| `jgb/F/repair-progress-followup-scope` | merge |
| `jgb/F/repair-request-how-to-submit` | merge |
| `jgb/F/repair-responsibility-landlord-vs-tenant` | merge |
| `jgb/F/repair-ticket-open-and-confirm` | merge |
| `jgb/F/tenant-emergency-self-repair` | merge |
| `jgb/F/tenant-equipment-maintenance-responsibility` | merge |
| `jgb/F/tenant-repair-notification-duty` | merge |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

（無）
