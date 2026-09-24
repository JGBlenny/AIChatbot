# 9.7 逐架擴充總審核單 ③補審 — 2026-09-16（等業主 ✅ 才可見）

未審 190 條（含 9.5 遺留 15 條）。補審＝加 `reviewed: {by: owner, at: 2026-09-16}` ⇒ 兩受眾視圖可引用。審法：整架 ✅、或列出要 ✗ 的 id（其餘 ✅）。內容全文見各架檔；矛盾清單見 ④。

### A 帳號與身分（未審 16）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `A/account-registration` | 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） | pm, prospect | 13 | |
| `A/login-methods` | 怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口） | pm, prospect | 5 | |
| `A/line-login-redirects-to-register` | 用 LINE 快速登入卻被帶去註冊頁、登不進去（只認 LINE 註冊帳號、無事後綁定、改用帳密登入） | pm, prospect | 3 | |
| `A/account-profile-settings` | 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件） | pm, prospect | 7 | |
| `A/registered-vs-unregistered-tenant` | 租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業） | pm, prospect | 14 | |
| `A/email-case-sensitivity` | Email 大小寫算不同帳號嗎（Email 為帳號識別、大小寫視為不同帳號） | pm | 6 | |
| `A/verification-code-not-received` | 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） | pm, prospect | 17 | |
| `A/verification-code-invalid` | 驗證碼一直輸入失敗（重發即換碼、三字母識別碼比對、5 分鐘效期、錯三次失效、120 秒冷卻） | pm, prospect | 4 | |
| `A/forgot-password` | 忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則） | pm, prospect | 7 | |
| `A/forgot-account-email` | 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服） | pm, prospect | 9 | |
| `A/change-email-or-phone` | 要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書） | pm | 3 | |
| `A/change-account-name` | 註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步） | pm | 2 | |
| `A/data-change-request-form` | 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱） | pm | 8 | |
| `A/duplicate-accounts-merge` | 不小心註冊了兩個帳號能不能合併（無自助合併、走客服後台，載明保留與處理的帳號） | pm | 3 | |
| `A/already-registered-error` | 註冊時顯示此帳號／手機已註冊怎麼辦（本人改登入或重設密碼、被他人占用走解綁申請） | pm, prospect | 2 | |
| `A/tenant-login-cannot-see-data` | 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態） | pm | 3 | |

### B 團隊、人員與大房東（未審 16）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `B/owner-report-collection-remit` | 大房東報表與代收代付怎麼交代（月報內容、提供方式、排程寄送） | pm, prospect | 10 | |
| `B/role-permission-granularity` | 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權） | pm, prospect | 13 | |
| `B/what-is-owner-landlord` | 大房東是什麼 | pm, prospect | 8 | |
| `B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | prospect | 34 | |
| `B/leasing-vs-management-liability-and-risk` | 包租與代管的法律責任與風險由誰承擔 | prospect | 17 | |
| `B/business-type-fee-model` | 包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼） | prospect | 13 | |
| `B/business-type-setting-and-system-differences` | 團隊業態（包租／代管）在系統裡怎麼設、差在哪（合約模板、發票主體、差額發票） | pm, prospect | 4 | |
| `B/leasing-management-license-and-staff-qualification` | 如何成為政府許可的包租代管業者與合格包管人員 | prospect | 7 | |
| `B/add-team-member` | 怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦） | pm | 9 | |
| `B/who-has-permission-lookup` | 怎麼查團隊裡誰有某個操作權限 | pm | 3 | |
| `B/remove-team-member-data-retention` | 移除團隊成員後他建的資料會怎樣 | pm | 3 | |
| `B/account-in-multiple-teams` | 一個帳號可以加入多個團隊嗎、權限怎麼算 | pm | 2 | |
| `B/change-team-principal-or-phone` | 怎麼變更團隊主要負責人或綁定手機（異動單） | pm | 4 | |
| `B/feature-not-visible-troubleshooting` | 找不到某功能或無法操作的可能原因 | pm | 2 | |
| `B/add-owner-landlord-and-access` | 怎麼新增大房東並設定他能看的物件範圍 | pm | 4 | |
| `B/owner-landlord-contact-book-import-export` | 大房東聯絡簿怎麼批次匯入匯出 | pm | 3 | |

### C 社區與物件（未審 19）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `C/property-status-meaning` | 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思 | pm, prospect | 7 | |
| `C/community-setup-and-property-binding` | 社區建立、編輯與物件歸戶（含公共區域物件、社宅強制綁定） | pm | 9 | |
| `C/property-batch-import` | 物件批次匯入：範本、表格填寫與上傳失敗 | pm | 14 | |
| `C/property-listing-conditions` | 物件要怎麼刊登上架、刊登需要什麼條件 | pm | 3 | |
| `C/property-unlisting` | 物件怎麼下架、為什麼突然全部下架 | pm | 6 | |
| `C/property-edit-vs-publish` | 編輯物件與刊登物件差在哪、為什麼修改沒存到 | pm | 3 | |
| `C/property-add-blocked` | 為什麼不能新增物件 | pm | 2 | |
| `C/public-display-address` | 對外顯示地址改了為什麼後台還是完整地址 | pm | 2 | |
| `C/storefront-entry-share` | 招租店舖入口在哪、怎麼分享、為什麼物件沒出現 | pm | 4 | |
| `C/community-public-page` | 社區公開頁面是什麼、能拿來做什麼 | pm | 5 | |
| `C/property-vr-tour` | 物件 VR 虛擬導覽怎麼綁、費用與拍攝找誰 | pm | 2 | |
| `C/property-custom-tags` | 物件自訂標籤怎麼建、怎麼用來篩選 | pm | 5 | |
| `C/property-advanced-search` | 物件列表進階搜尋怎麼用 | pm | 3 | |
| `C/occupancy-rate-calculation` | 首頁即時物件出租率怎麼算、已出租數字從哪來 | pm | 1 | |
| `C/community-facilities-and-hours` | 社區有哪些公共設施、開放時間、費用與變更通知 | pm | 12 | |
| `C/community-facility-usage-rules` | 公共設施使用規範：權利、義務、安全規範與違規後果 | pm | 19 | |
| `C/community-garbage-disposal` | 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範 | pm | 14 | |
| `C/community-facility-disputes` | 公共設施損壞責任、使用爭議處理與責任保險 | pm | 13 | |
| `C/community-services-and-events` | 社區生活服務與活動（社區活動、包裹代收、社宅社區服務） | pm | 4 | |

### D 租約（含委託約子題）（未審 55）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | pm, prospect | 33 | |
| `D/contract-batch-renewal` | 續約能不能批次處理（含快速日期設定、紙本上傳、通知分流） | pm, prospect | 9 | |
| `D/contract-history-retention` | 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程） | pm, prospect | 9 | |
| `D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | pm | 13 | |
| `D/contract-templates` | 合約範本有哪些可以選（含內文隨內政部新制更新） | pm, prospect | 6 | |
| `D/lease-expiry-followup-scope` | 合約到期追問可答範圍與到期提醒（導向續約面向） | pm | 6 | |
| `D/sublease-vs-management-contract` | 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整） | pm, prospect | 16 | |
| `D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | pm | 11 | |
| `D/contract-copy` | 合約複製快速建立相似合約 | pm | 4 | |
| `D/upload-existing-contract` | 上傳既存（紙本）合約：適用情境、效力、入口、檔案上限 | pm, prospect | 12 | |
| `D/contract-attachments-notes-limits` | 合約附件上傳、備註 50 行與補充條款限制 | pm | 11 | |
| `D/contract-pdf-download` | 合約相關 PDF 下載（合約書、摘要、點交／點退清單、提前解約文件） | pm | 3 | |
| `D/signer-identity-and-seal` | 簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法 | pm | 10 | |
| `D/contract-send-invite` | 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整） | pm | 8 | |
| `D/esign-invite-expiry` | 簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長 | pm | 10 | |
| `D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | pm | 8 | |
| `D/tenant-sign-steps` | 租客收到簽約邀請後的簽署步驟（租客視角） | pm | 8 | |
| `D/esign-legal-validity` | 電子合約法律效力、簽章認證與 72 小時審閱期 | pm, prospect | 7 | |
| `D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | pm | 12 | |
| `D/contract-lookup` | 查詢合約資訊：以合約編號／物件名稱查、不能用租客姓名反查、租客資料卡 | pm | 5 | |
| `D/contract-filter-by-state` | 依合約狀態篩選物件（點交點退、待退押金、本月到期、無合約） | pm | 4 | |
| `D/contract-data-change-form` | 資料異動申請書的填寫與提交 | pm | 3 | |
| `D/contract-snapshot-independence` | 合約快照原則：物件資料、租客聯絡方式或姓名事後修改，合約與通知都不連動 | pm | 10 | |
| `D/tenant-change-new-contract` | 更換承租人／退房後換新租客：只能新建合約，舊約收尾與物件重刊登 | pm | 4 | |
| `D/contract-cancel-delete` | 合約刪除、取消、作廢的條件與取消 vs 歷史合約差異 | pm | 6 | |
| `D/handover-checkin` | 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 | pm | 19 | |
| `D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | pm | 26 | |
| `D/handover-return-cancel-invite` | 取消／收回點交或點退邀請，為什麼不能取消 | pm | 2 | |
| `D/lease-end-checkout-overview` | 租客要退租了接下來怎麼做：到期收尾步驟總覽（點退→帳單→封存→轉歷史）與退租跑到哪一步 | pm | 2 | |
| `D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | pm | 26 | |
| `D/early-termination-penalty` | 提前解約違約金怎麼算（預告期）、由誰付 | pm | 9 | |
| `D/early-termination-aftermath` | 提前解約生效後：何時可點退、違約金與押金一併結算、之後還要處理什麼 | pm | 7 | |
| `D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | pm | 17 | |
| `D/renewal-vs-new-contract` | 系統續約 vs 重建新約的取捨（條件變更、租屋補助審核） | pm | 11 | |
| `D/renewal-history-and-addendum` | 續約後原合約去哪了：續約歷史、增補文件分頁、有沒有下一份約 | pm | 5 | |
| `D/delegation-vs-lease-contract` | 委託約與租賃約的差別（系統分開管理） | pm, prospect | 6 | |
| `D/delegation-contract-flow` | 委託合約的建立簽署、提前終止與 PDF 下載 | pm | 11 | |
| `D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | pm | 23 | |
| `D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | pm | 17 | |
| `D/deposit-setting-and-refund-system` | 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算） | pm | 3 | |
| `D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | pm | 30 | |
| `D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | pm | 18 | |
| `D/tenant-pet-clauses` | 租約中的寵物押金與飼養寵物費用 | pm | 5 | |
| `D/tenant-rental-insurance` | 租屋相關保險：租屋保險費用、租客設備投保、押金投保 | pm | 8 | |
| `D/move-in-inspection` | 入住注意事項與傢俱清點 | pm | 7 | |
| `D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | pm | 32 | |
| `D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | pm | 25 | |
| `D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | pm | 17 | |
| `D/tenant-renewal-and-extension-rights` | 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助 | pm | 14 | |
| `D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | pm | 24 | |
| `D/equipment-usage-under-lease` | 租約中的設備與公共設備使用規範 | pm | 8 | |
| `D/household-registration-under-lease` | 租屋期間戶籍遷移與居住證明 | pm | 7 | |
| `D/sublease-and-shared-lease-terms` | 轉租與分租的租約條款與押金處理 | pm | 7 | |
| `D/social-housing-lease` | 社會住宅租約與一般租約的差異、期限與終止 | pm | 9 | |
| `D/lease-notarization` | 租約公證：是什麼、去哪辦、費用、對房東房客的保障、與租補關係、公證合約如何上傳 | pm, prospect | 8 | |

### E 帳務（含發票、收款金流、抄表）（未審 47）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `E/billing-overview` | 帳務管理模組做什麼 | prospect | 3 | |
| `E/bill-contents-extra-fees` | 帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整） | pm, prospect | 13 | |
| `E/bill-format-customize` | 帳單版面、收據版式與收訖章能不能自訂 | pm, prospect | 9 | |
| `E/credit-card-rent-payment` | 租客能不能用信用卡繳房租（限藍新、流程與限制） | pm, prospect | 8 | |
| `E/dunning-draft-template-tone-late-fee` | 催繳草稿的生成規則（模板、語氣分級與滯納金提及） | pm | 2 | |
| `E/einvoice-issuing` | 電子發票何時開、自動開立設定、載具類型與一物件一發票 | pm, prospect | 21 | |
| `E/overdue-bill-followup-scope` | 逾期帳單追問可答範圍（依帳單編號查狀態、金額、逾期明細） | pm | 3 | |
| `E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（繳費提醒、催繳通知條件、逾期標示與訂閱通知） | pm, prospect | 16 | |
| `E/payment-gateway-options` | 金流廠商差別、支援付款方式與申請條件 | pm, prospect | 8 | |
| `E/utility-split-calculation` | 水電與公共費用怎麼分算（依合約） | pm, prospect | 3 | |
| `E/virtual-account-prepaid` | 固定虛擬帳號與儲值金抵扣是什麼、跟一般虛擬帳號差在哪 | pm, prospect | 3 | |
| `E/rent-amount-calculation` | 租金金額怎麼算（以合約租金快照為準、不足月按比例） | pm | 6 | |
| `E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | pm | 14 | |
| `E/management-fee` | 管理費是什麼、用途與怎麼算 | pm | 4 | |
| `E/periodic-bill-generation` | 週期帳單何時產生、三種建立方式與續約／補簽起算 | pm | 11 | |
| `E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | pm | 25 | |
| `E/bill-send-failure` | 帳單為什麼發不出去（狀態、金額、度數未填、租客聯絡方式未驗證） | pm | 4 | |
| `E/bill-recall-cancel` | 帳單發出去想收回、取消或設失效（可用狀態與繳費資訊斷開） | pm | 10 | |
| `E/bill-archive-after-termination` | 提前終止／退租後多產生的帳單要封存、封存後怎麼退回 | pm | 13 | |
| `E/manual-bill-creation` | 手動新增帳單、負值退款、Excel 批次匯入與補建紀錄 | pm | 14 | |
| `E/checkout-bill-settlement` | 點退帳單怎麼算（未結費用、賠償、押金互抵、多退少補） | pm | 7 | |
| `E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | pm, prospect | 21 | |
| `E/paid-but-status-not-updated` | 租客說繳了但錢還沒進來／帳單卡在待對帳 | pm | 2 | |
| `E/cash-bank-account-collection` | 現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳 | pm | 9 | |
| `E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | pm | 26 | |
| `E/payment-fees-and-sms` | 金流手續費誰負擔、費率多少與帳單簡訊是否收費 | pm, prospect | 6 | |
| `E/tenant-payment-methods` | 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層） | pm | 13 | |
| `E/tenant-online-payment-steps` | 租客線上繳費操作步驟（信用卡、虛擬 ATM） | pm | 11 | |
| `E/tenant-view-bills` | 租客在哪裡看帳單、繳費狀態與付款入口 | pm | 6 | |
| `E/tenant-cannot-see-bill` | 租客說看不到帳單（可見三條件與信箱錯配） | pm | 2 | |
| `E/bill-reports-export` | 帳單報表匯出、統計圖表與儀表板 | pm | 12 | |
| `E/credit-card-auto-debit` | 信用卡自動扣款授權設定與扣款失敗處理 | pm | 11 | |
| `E/virtual-account-transfer` | 虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易 | pm | 20 | |
| `E/payment-failure-troubleshooting` | 租客繳不了費／轉帳或刷卡一直失敗怎麼排查 | pm | 5 | |
| `E/payment-amount-mismatch` | 付款金額不符、重複轉帳、多繳少繳怎麼處理 | pm | 6 | |
| `E/convenience-store-payment` | 超商代碼／條碼繳費流程與入帳撥付時程 | pm | 9 | |
| `E/fixed-virtual-account-management` | 固定虛擬帳號怎麼開通設定、入帳沖銷與餘額歷程查詢 | pm | 11 | |
| `E/prepaid-meter-topup-billing` | 儲值電表的儲值帳單、入帳與電費預付收取 | pm | 14 | |
| `E/late-fee-calculation` | 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額） | pm | 13 | |
| `E/invoice-not-issued-troubleshooting` | 發票為什麼還沒開、顯示已開卻沒號碼的排查 | pm | 5 | |
| `E/invoice-void-reissue` | 發票開錯了怎麼作廢、補開與作廢不了 | pm | 9 | |
| `E/differential-invoice` | 差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出） | pm | 13 | |
| `E/deposit-imputed-interest` | 押金設算息怎麼算、利率設定與年度一次限制 | pm | 6 | |
| `E/landlord-owner-bills` | 大房東帳單（代收代付）怎麼看與建立 | pm | 5 | |
| `E/bill-receipt-pdf` | 帳單收據 PDF 下載與繳費證明 | pm | 7 | |
| `E/rent-collection-agent-vs-direct` | 包租代管租金代收與房東直收有什麼差別 | pm | 3 | |
| `E/rent-market-discount-tax` | 租金行情、折扣條件與公益出租人減稅（租客視角） | pm | 10 | |

### F 修繕（未審 19）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `F/repair-progress-followup-scope` | 修繕進度追問可答範圍與查詢方式 | pm | 3 | |
| `F/repair-ticket-no-lease` | 代開單時的租約查詢身分與空屋／無租約物件開單規則 | pm | 2 | |
| `F/repair-ticket-open-and-confirm` | 開修繕單基本流程與確認機制（拍照進場／文字口述） | pm | 1 | |
| `F/repair-ticket-photo-recognition-uncertain` | 照片辨識信心不足或看不出損壞時的處理 | pm | 2 | |
| `F/repair-responsibility-landlord-vs-tenant` | 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出） | pm | 38 | |
| `F/common-equipment-maintenance-responsibility` | 公共設備的維護、損壞、更新、費用與檢查紀錄責任 | pm | 17 | |
| `F/tenant-equipment-maintenance-responsibility` | 租客設備的使用、維護、損壞賠償、更新與費用責任 | pm | 20 | |
| `F/tenant-repair-notification-duty` | 租客發現需修繕時的通知義務與要求合理期限修繕的權利 | pm | 9 | |
| `F/tenant-emergency-self-repair` | 緊急情況下租客自行修繕的條件、事後通知與費用報銷 | pm | 7 | |
| `F/emergency-repair-flag-and-handling` | 緊急修繕的標記、優先處理與回應時效 | pm, prospect | 6 | |
| `F/neighbor-leak-responsibility` | 鄰居漏水的修繕責任與處理 | pm | 2 | |
| `F/repair-responsibility-dispute` | 修繕責任有爭議時的處理 | pm | 3 | |
| `F/repair-warranty-period` | 修繕後的保固期 | pm | 2 | |
| `F/social-housing-repair-responsibility` | 社會住宅的維修責任 | pm | 2 | |
| `F/repair-flow-stages` | 修繕流程六階段與各狀態意義 | pm, prospect | 2 | |
| `F/repair-cost-recording-and-settlement` | 修繕費用的記錄、分擔與結單自動產生修繕費帳單 | pm | 4 | |
| `F/repair-request-how-to-submit` | 在系統提出修繕申請的步驟與需填資料（租客／房東） | pm, prospect | 9 | |
| `F/repair-dispatch-and-close` | 業者受理報修、安排廠商、完工登錄到結單封存的操作 | pm | 5 | |
| `F/repair-multiple-items-one-ticket` | 多個品項是否分開報修（合併在一張報修單） | pm | 1 | |

### G 裝置（未審 11）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `G/meter-item-followup-scope` | 電錶項目追問可答範圍（餘額、可用度數、供電、低電量警報） | pm | 7 | |
| `G/meter-vendor-binding` | 電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理） | pm | 10 | |
| `G/meter-device-management` | 智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數 | pm | 9 | |
| `G/tenant-meter-visibility` | 租客端看到即時電表與自行儲值的前提設定 | pm | 7 | |
| `G/meter-data-sync-gap` | 電錶實體度數與 JGB 顯示不同／長期不更新 | pm | 3 | |
| `G/iot-offline-troubleshooting` | IoT 設備（門鎖／電表）無法連線的排查順序 | pm | 3 | |
| `G/smart-lock-functions` | 智慧門鎖功能：租客密碼、QR Code、開門紀錄與密碼管理 | pm | 3 | |
| `G/smart-lock-share-password` | 分享門鎖密碼：訪客／維修／清潔人員臨時存取 | pm | 4 | |
| `G/smart-lock-password-rules` | IoT 設定：門鎖預設密碼規則與連結起始日的生效範圍 | pm | 3 | |
| `G/smart-lock-hardware-vendor` | 門鎖硬體功能（悠遊卡／磁扣／電池／音量）屬廠商範疇 | pm | 3 | |
| `G/smart-lock-failure` | 門鎖 QR Code／密碼失靈開不了門的排查 | pm | 5 | |

### I 方案與導入（未審 7）

| id | 標題 | 受眾 | 句 | 業主 |
|---|---|---|---|---|
| `I/competitor-neutrality` | 會評論競爭對手嗎 | prospect | 33 | |
| `I/data-migration` | 舊系統資料能否匯入（可匯入範圍、不支援項目與批次匯入做法） | pm, prospect | 7 | |
| `I/pricing-plans` | 怎麼收費與方案分級差異 | pm, prospect | 10 | |
| `I/product-overview` | 系統總覽、能解決什麼問題與適不適合我 | prospect | 35 | |
| `I/subscription-change-renewal` | 升級、變更、續約與取消訂閱（含付款紀錄） | pm | 20 | |
| `I/subscription-payment-failure` | 訂閱扣款失敗：方案失效、物件下架與恢復 | pm | 7 | |
| `I/onboarding-tutorial-index` | 房東新手教學總覽（從哪開始、各篇教學有哪些） | pm | 7 | |
