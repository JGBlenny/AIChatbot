---
coarse: D
title: 租約（含委託約子題）
scope: 合約建立、簽署、狀態與階段、續約、退租、違約金、租客邀請簽約；委託約（僅法人房東）；⛔ 帳單與押金金流歸 E
version: 2026-09-21.0
reviewers: [owner]
language: zh-TW
---
## 合約列表與搜尋 {#D-contract-list}
### 合約列表有哪些狀態頁籤？（待發送合約／待租客簽回／待房東簽名／執行中合約／歷史合約） {#jgb/D/contract-list-status-tabs}
- phrasings:
  - {text: "合約列表有哪些狀態", source: "draft:outline-20260920", status: proposed}
  - {text: "待租客簽回是什麼意思", source: "draft:outline-20260920", status: proposed}
  - {text: "合約總表分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "合約狀態頁籤", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/list/_parts/PageTop.vue, code:src/routes/contracts.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約管理的合約總表依進度分成五個頁籤：待發送合約、待租客簽回、待房東簽名、執行中合約、歷史合約。
網址列的合約狀態代碼只接受 1 到 5，如果代碼不在這個範圍，系統會自動導回沒有篩選狀態的合約總表。
如果目前登入身分是租客，直接進入代碼 1（待發送合約）頁籤時，系統會把畫面導回登入後的首頁。
### 合約列表怎麼搜尋合約？（案名／地址／租客／ID／手機／信箱六種關鍵字，另有進階搜尋） {#jgb/D/contract-search-keyword-scope}
- phrasings:
  - {text: "合約怎麼搜尋", source: "draft:outline-20260920", status: proposed}
  - {text: "合約列表關鍵字搜尋範圍", source: "draft:outline-20260920", status: proposed}
  - {text: "進階搜尋合約", source: "draft:outline-20260920", status: proposed}
  - {text: "合約搜尋結果頁面", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/list/Index.vue, code:src/pages/contracts/list/_parts/PageTop.vue, code:src/components/Lightbox/ContractsAdvSearch.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約列表的關鍵字搜尋可以選擇搜尋範圍，包含案名、地址、租客、ID、手機、信箱六種。
合約列表也支援進階搜尋，可以用社區、合約類型、是否註冊 JGB 帳號、通知狀態、租期範圍查詢方式、空間類型、租金、面積(坪)等條件篩選。
用進階搜尋條件查詢後，畫面標題會顯示成「合約搜尋結果」，這是另一個頁面，跟前面五個狀態頁籤是分開的。
### 怎麼建立一份新合約？（合約總表右上角「建立合約」，或物件總表小齒輪選建立合約） {#jgb/D/contract-create-entry}
- phrasings:
  - {text: "怎麼建立合約", source: "draft:outline-20260920", status: proposed}
  - {text: "合約要去哪裡建立", source: "draft:outline-20260920", status: proposed}
  - {text: "一個物件可以簽幾份合約", source: "draft:outline-20260920", status: proposed}
  - {text: "新增合約入口", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在合約管理的合約總表頁面，點選右上角的「建立合約」按鈕，選取想建立合約的物件並按下一步，即可開始建立合約。
也可以在物件管理的物件總表中，對想建立合約的物件點選小齒輪，選擇「建立合約」直接進入。
建立合約時可以選擇「電子合約（公版）」「電子合約（客製化契約書）」或「紙本簽約」三種建立方式。
一個物件最多可以綁定 10 份合約，例如同一物件的舊租約仍在執行中，也可以先跟新租客預先簽下一份合約，等舊約到期銜接。
### 物件要先刊登廣告才能建立合約嗎？（現行規則是必填欄位要填齊，不是看刊登狀態） {#jgb/D/contract-create-estate-completeness-requirement}
- phrasings:
  - {text: "物件要刊登才能建約嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有上架的物件可以簽約嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "建立合約的物件條件", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
建立合約前，系統會先檢查該物件的必填欄位是否已經填寫齊全，沒填齊會擋下並提示「請先完善物件所有必填欄位」。
建立合約的檢查條件曾經改過：早期是看物件「是否已刊登」來決定能不能建立合約，2024/11/13 已經改成看「物件必填資料是否填齊」，以前用刊登狀態當條件的做法目前已經不再套用。
### 合約總表列的小齒輪可以做什麼操作？（依合約目前狀態與權限顯示「編輯合約」「刪除合約」「取消簽名」等動作） {#jgb/D/contract-list-row-gear-actions}
- phrasings:
  - {text: "合約列表小齒輪可以做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "合約列表的齒輪按鈕能做什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約總表每一列可以點選小齒輪，依合約目前狀態顯示「編輯合約」「刪除合約」「取消簽名」等動作，實際顯示哪些動作要看目前狀態與權限。
### 合約總表可以怎麼排序？（依名稱、更新時間、合約起始日、終止日、成立日，各分新舊／早晚，共 5 種依據） {#jgb/D/contract-list-row-sort-options}
- phrasings:
  - {text: "合約列表怎麼排序", source: "draft:outline-20260920", status: proposed}
  - {text: "合約排序選單", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約總表可以用排序選單依名稱、更新時間（新／舊）、合約起始日（早／晚）、合約終止日（早／晚）、合約成立日（早／晚）排序。
### 合約總表有哪些欄位？（含團隊自訂的「標籤」欄） {#jgb/D/contract-list-columns}
- phrasings:
  - {text: "合約列表標籤欄", source: "draft:outline-20260920", status: proposed}
  - {text: "合約總表欄位", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/list/_parts/ListTable.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約總表有一欄「標籤」，顯示團隊在合約上設定的自訂標籤。
### 合約總表的待退押金提示燈號是什麼意思？（合約到期前 30 天才能點退） {#jgb/D/contract-list-deposit-alert}
- phrasings:
  - {text: "待退押金提示是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "合約列表押金提示燈號", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/list/_parts/stickerLabelBlock.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果合約帶有「待退押金」提示燈號，滑鼠移過去會顯示提示文字「合約到期前30天始可點退」。
### 合約總表什麼時候會多出「帳單幣別」欄？（只有在批次建立帳單、挑選合約的頁面才會出現，一般檢視沒有這一欄） {#jgb/D/contract-list-bill-currency-column}
- phrasings:
  - {text: "合約列表帳單幣別欄", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單幣別什麼時候出現", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/list/_parts/ListTable.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「帳單幣別」不是合約總表固定顯示的欄位；只有在挑選合約進行批次建立帳單的頁面，而且動作確實是批次建立帳單時，才會多出這一欄。
### 合約總表可以匯出實價登錄資料嗎？（只有在「執行中合約」頁籤、中文站台、且團隊開通此功能時才會出現按鈕） {#jgb/D/contract-list-export-declaration}
- phrasings:
  - {text: "匯出實價登錄資料", source: "draft:outline-20260920", status: proposed}
  - {text: "合約列表怎麼匯出實價登錄", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/list/_parts/PageTop.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約總表右上角有「匯出實價登錄資料」按鈕，點下去會開啟一個彈窗，可以匯出符合條件的合約資料，供之後申報實價登錄使用。
這個按鈕只有在「執行中合約」頁籤、網站語言是中文、而且團隊有開通這個功能時才會顯示；如果篩選結果目前是 0 筆，按鈕會呈現不能點的狀態。
## 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） {#D-contract-edit-general}
### 建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁） {#jgb/D/contract-edit-tabs-overview}
- phrasings:
  - {text: "建約有哪些步驟", source: "draft:outline-20260920", status: proposed}
  - {text: "合約編輯分幾頁", source: "draft:outline-20260920", status: proposed}
  - {text: "建立合約流程", source: "draft:outline-20260920", status: proposed}
  - {text: "合約分頁順序", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/contracts.js, code:src/use/useEditStore.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
建立一般住宅合約的編輯畫面依序分成「承租方資訊」「租賃契約」「點交」「出租方資訊」與「選填」五個分組，合計 14 個分頁。
「租賃契約」分組底下依序是基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式六個分頁。
「點交」分組底下是附設傢俱與現況補充兩個分頁；「選填」分組底下是建物謄本、公證、合約附件、補充條款四個分頁。
分頁旁邊打勾圖示代表必填分頁；租金調幅設定、稅與發票、附設傢俱、現況補充、建物謄本、公證、合約附件、補充條款這 8 頁沒有打勾圖示，屬於選填分頁。
實際會顯示哪些分頁不是固定的，會依合約範本、物件用途（例如車位）、是否為既存（紙本／DIY）合約等條件動態增減。
「租金調幅設定」分頁只有具備特定角色權限的團隊才會顯示；一般團隊看不到這個分頁，實際編輯合約時只會看到 13 個分頁，不是 14 個。
### 承租方基本資料怎麼填？（個人／法人租客、租客註冊或免註冊、緊急聯絡人） {#jgb/D/contract-tenant-basic-info}
- phrasings:
  - {text: "承租方基本資料怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "租客要註冊帳號才能簽約嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "法人租客怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "緊急聯絡人", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/tenantInfo/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「基本資料」分頁用來填寫承租方的簽約資料，可以選擇租客身份是「個人租客」或「法人租客」。
系統提供「租客註冊」與「租客免註冊」兩種模式：租客註冊代表租客會自己註冊 JGB 會員並填妥承租方資訊；租客免註冊代表租客不需要註冊會員，改由管理者代為填寫承租方資訊。
這個分頁也可以新增租客的緊急聯絡人，填寫姓名、關係與聯絡號碼。
分頁上會提示，這裡填寫的租客資料會謄寫進合約內容，過程經過加密處理。
### 「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期） {#jgb/D/contract-rentbasic-template-and-dates}
- phrasings:
  - {text: "合約範本怎麼選", source: "draft:outline-20260920", status: proposed}
  - {text: "合約起迄日期怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "租賃訂約日期是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "合約範本有哪幾種", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentBasic/General.vue, code:app/Http/Controllers/ContractController.php, code:config/contract.php, code:app/Role.php, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「基本條件」分頁要先選擇「合約類型」與「合約範本」，決定這份合約要用哪一種定型化契約內容。
分頁上要設定「合約起迄日期」，也就是這份合約的租期起訖。
另外還有「租賃訂約日期」欄位，用來記錄雙方實際簽訂這份合約的日期，跟合約起迄日期是不同的欄位。
一般團隊建立一般住宅合約時，可選的合約範本共有 12 種：「114年內政部住宅租賃契約(原房東)」「113年內政部轉租契約(包租轉租)」「代租代管契約(參考114年租賃契約)」「內政部英文版 租賃契約書 原房東」「內政部英文版 租賃契約書 包租業」「內政部英文版 租賃契約書 代租代管」「英越文版 租賃契約書」「英泰文版 租賃契約書 原房東」「英泰文版 租賃契約書 代租代管」「公會中文版 租賃契約書 原房東」「公會中文版 租賃契約書 包租業」「公會中文版 租賃契約書 代租代管」。
如果登入身分是個人房東角色，可選範本會縮減成 4 種：「114年內政部住宅租賃契約(原房東)」「內政部英文版 租賃契約書 原房東」「英泰文版 租賃契約書 原房東」「公會中文版 租賃契約書 原房東」。
### 「基本條件」分頁的繳費週期與帳單週期制度怎麼設定？（繳費週期／繳費截止日、當月分算或跨月計算、分算日） {#jgb/D/contract-rentbasic-billing-cycle}
- phrasings:
  - {text: "繳費週期怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "繳費截止日是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "跨月計算跟當月分算差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單週期分算日", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentBasic/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「基本條件」分頁要設定「繳費週期」，決定多久要繳一次款項。
同時要設定「繳費截止日」，也就是每期帳單的繳款期限。
帳單週期制度分成「當月分算」與「跨月計算」兩種計費方式，會影響租期不足一個完整週期時金額怎麼分攤。
選擇跨月計算時，還要設定「帳單週期分算日」。
### 「基本條件」分頁的遲繳滯納金怎麼計算？（僅新北住都角色群組可見，兩段比例＋拖欠天數門檻，欄位唯讀） {#jgb/D/contract-rentbasic-latefee}
- phrasings:
  - {text: "滯納金怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "遲繳滯納金計算方式", source: "draft:outline-20260920", status: proposed}
  - {text: "滯納金比例跟拖欠天數", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentBasic/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「遲繳滯納金」設定只出現在新北住都角色群組的合約上；租客超過繳費期限還沒繳款，會先產生第一筆比例的滯納金，如果拖欠超過設定的天數門檻，還會再產生第二筆同比例的滯納金。
滯納金的比例（X）跟拖欠天數門檻（Y）兩個欄位在合約編輯畫面上是唯讀的，不能在合約上直接修改；這兩個數值是這份合約自己的一筆設定紀錄，第一次需要用到時會用系統預設值（2%、30 天）自動建立，之後就固定在這份合約上，不會因為系統預設值以後改變而跟著變動。
### 「基本條件」分頁的租客慣用語系是什麼？（決定系統產生給租客的合約文件語系） {#jgb/D/contract-rentbasic-tenant-language}
- phrasings:
  - {text: "租客慣用語系是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "合約文件語系怎麼選", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentBasic/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「租客慣用語系」欄位要選租客習慣使用的語系，之後透過 JGB 系統產生給租客的相關合約文件，都會以這個語系為主。
### 合約的「可否提前解約」與違約金怎麼設定？（每月租金／固定金額／詳參補充條款／其他四種算法） {#jgb/D/contract-rentbasic-early-termination}
- phrasings:
  - {text: "提前解約違約金怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "合約可否提前解約設定", source: "draft:outline-20260920", status: proposed}
  - {text: "違約金計算方式", source: "draft:outline-20260920", status: proposed}
  - {text: "解約通知天數", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentBasic/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「基本條件」分頁要設定租客是否可以提前解約，選項是「可以」或「不可以」。
選擇可以提前解約時，要再選違約金計算方式：「每月租金」「固定金額」「詳參後文補充條款」，既存（上傳）合約另外多一個「其他」選項可以自訂文字說明（最多 30 個字元）。
選「每月租金」或「固定金額」時，畫面上會提示依內政部函釋：一方未先期通知逕行終止租約，賠償他方的違約金最高不得超過一個月租金額。
選「每月租金」時，系統會依租客通知房東的天數門檻分兩段計算，達到門檻天數（含）以上通知的違約金月數，跟少於門檻天數通知的違約金月數，可以分別設定不同月數。
### 租金費用分頁要設定什麼？（租金、押金、自訂收入／支出費用、租金優惠、繳費週期優惠） {#jgb/D/contract-rent-fees}
- phrasings:
  - {text: "租金費用怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "押金上限", source: "draft:outline-20260920", status: proposed}
  - {text: "自訂費用收入支出", source: "draft:outline-20260920", status: proposed}
  - {text: "繳費週期優惠", source: "draft:outline-20260920", status: proposed}
  - {text: "租金優惠跟繳費週期優惠差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/billSetting/Index.jsx, code:src/pages/contracts/edit/rent/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「租金費用」分頁用來設定租金、押金、生活費用以及自訂費用等收費項目。
押金欄位下方會顯示提示文字：根據內政部租賃住宅市場發展及管理條例規定，一般租賃契約押金額度最高不得超過兩個月租金。
自訂費用分成「收入」與「支出」兩種性質：收入類是向對方收取的款項，支出類是向對方付款的款項，折抵、折扣也算在支出類。
這個分頁還可以設定「租金優惠」，但這個欄位只對統上、新北住都、新北住都停車場這幾個特殊角色群組顯示，一般團隊看不到這個設定。
「租金優惠」底下還有一個「繳費週期優惠」子選項（例如年繳、半年繳、季繳），只有統上這一個角色群組才會顯示；新北住都、新北住都停車場即使能看到租金優惠，也看不到繳費週期優惠。
選擇繳費週期優惠後會連動變更「基本條件」分頁的繳費週期設定。
### 押金有哪幾種設定方式？（每月租金倍數／固定金額兩種計算基準） {#jgb/D/contract-rent-deposit-two-modes}
- phrasings:
  - {text: "押金怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "押金計算基準", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rent/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
押金的計算基準有兩種：「每月租金」（依月租金倍數計算）或「固定金額」（直接輸入金額），可以在「租金費用」分頁切換。
### 租金調幅設定分頁在做什麼？（依繳費期數設定固定金額或百分比調漲／調降） {#jgb/D/contract-rent-adjustment}
- phrasings:
  - {text: "租金調幅怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "租金逐年調漲", source: "draft:outline-20260920", status: proposed}
  - {text: "分期調整租金", source: "draft:outline-20260920", status: proposed}
  - {text: "租金調幅方式", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentAdjustment/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「租金調幅設定」分頁可以針對合約每一期繳費週期，分別設定主租金或自訂租金項目的調幅。
調幅方式有五種：無調幅、固定租金調幅(+)、固定金額優惠(-)、百分比調幅(+)、百分比優惠(-)。
可以用「批次設定調幅」一次套用到全部或指定的租金項目，也可以在下方表格對每一期單獨設定。
這個分頁要先在「基本條件」設定好合約起迄日期、繳費週期及帳單週期制度，才能列出各期的調幅設定列。
這個分頁只有具備特定角色權限的團隊才會顯示；一般團隊的合約編輯畫面裡沒有「租金調幅設定」這個分頁可以填。
### 稅與發票分頁怎麼設定？（是否開立發票、應稅品項、目前只支援租金品項開發票） {#jgb/D/contract-tax-invoice}
- phrasings:
  - {text: "合約發票怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "租金以外可以開發票嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "應稅品項設定", source: "draft:outline-20260920", status: proposed}
  - {text: "統一編號要不要打", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/taxAndInvoice/index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「稅與發票」分頁要先設定這份合約的帳單是否要開立發票。
選擇開立發票後，要設定出租方統一編號，以及發票是否要打承租方的統一編號。
這個分頁可以逐項設定「應稅品項」是否應稅，但畫面上會提示 JGB 目前僅提供租金品項開立發票服務，其他品項的發票支援持續增加中。
如果目前沒有任何品項會開立發票，畫面會提示應該把「帳單是否開立發票」改為「否」，不然帳單不會有發票金額。
### 帳單設定分頁在做什麼？（預先編輯未來帳單的標題、金額、週期與自動執行動作） {#jgb/D/contract-bill-setting}
- phrasings:
  - {text: "帳單設定分頁怎麼用", source: "draft:outline-20260920", status: proposed}
  - {text: "可以先編輯未來帳單嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單期間跟租期不一樣", source: "draft:outline-20260920", status: proposed}
  - {text: "帳單自動執行動作", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/billSetting/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「帳單設定」分頁可以預先編輯這份合約未來衍生的每一張帳單，包括標題、繳費期限、帳單週期、金額、細項、備註，以及成立後的自動執行動作。
如果某張帳單的自動執行動作選擇「已到帳」，代表合約成立時這張帳單會直接被視為已到帳。
如果帳單設定的期間跟合約租期對不起來，畫面會出現警示，寄送合約邀請時會被系統擋下，需要重新產生帳單表或逐期調整日期，直到跟合約租期一致才能正常送出邀請。
帳單狀態分成草稿、應到帳／應支出、已到帳／已支出、封存四種。
「帳單設定」分頁在新北住都、新北住都停車場、統上這幾個角色群組會被拿掉、暫不開放使用；這是新北住都個案的暫時處理，等新北住都確認需求後才會恢復顯示。
### 合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種） {#jgb/D/contract-payment-method}
- phrasings:
  - {text: "收款方式有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "怎麼設定收租金方式", source: "draft:outline-20260920", status: proposed}
  - {text: "固定虛擬帳號收租", source: "draft:outline-20260920", status: proposed}
  - {text: "現金收款帳戶", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/payment/General.vue, code:app/Contract.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「收款方式」分頁讓房東指定租客要用哪種方式支付款項，選項有「線上金流」「現金收款」「固定虛擬帳號」三種，但不是每個團隊都看得到全部三種。
「線上金流」只有在使用者國別是台灣、且合約範本不是 Meta Capital 系列時才會顯示這個選項。
「固定虛擬帳號」只有具備特定特殊角色權限的團隊才會顯示這個選項。
選擇「現金收款」可以指定收款銀行帳戶，填寫銀行代碼、銀行名稱、帳戶名稱、銀行帳號等資料，也可以把常用帳號加入清單方便下次選用。
「加入常用帳號」按鈕只有具備編輯角色（收款設定相關）權限的成員才會顯示，權限不足的成員在這個分頁看不到這個按鈕。
### 附設傢俱分頁在做什麼？（設定家具責任歸屬，簽約後會帶入點交清單） {#jgb/D/contract-facilities-tab}
- phrasings:
  - {text: "家具修繕責任歸屬", source: "draft:outline-20260920", status: proposed}
  - {text: "點交清單怎麼來的", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/facilities/General.vue, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「附設傢俱」分頁用來勾選租屋處提供的家具、家電，並可以設定每一項的修繕責任歸屬方；也可以從物件資料或其他合約複製資料進來。
分頁上提示：依照合約設定，所有品項預設由出租方負責修繕，也可以勾選特定項目改由承租方負責，但如果是承租方刻意損壞，仍要由承租方自行負擔責任。
簽約完成後，這個分頁勾選、標註的家具傢俱項目，都會自動帶入之後的點交清單。
### 現況補充分頁要寫什麼？（車位、屋況、漏水處等內政部規範現況細節） {#jgb/D/contract-situation-tab}
- phrasings:
  - {text: "現況補充要寫什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "非自然死亡揭露", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/situation/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「現況補充」分頁可以紀錄車位、屋況、漏水處等現況細節，包括建物出租型態、是否曾發生非自然死亡等內政部規範的項目。
### 出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、電子簽名圖章） {#jgb/D/contract-landlord-dealer-basic}
- phrasings:
  - {text: "出租方基本資料怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "經理人資訊怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "電子簽名圖章", source: "draft:outline-20260920", status: proposed}
  - {text: "團隊資料自動帶入", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/dealerBasic/Index.vue, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「出租方基本資料」分頁如果是個人房東，需要填妥電話、Email、身分證字號、戶籍地址、通訊地址。
如果是用團隊方式建立合約，出租方資料（公司登記名稱、統一編號、電話、Email、公司登記地址、公司通訊地址）會自動帶入先前團隊資訊填寫的內容，需要修改的話要回到「團隊資訊」編輯。
填妥出租方資料後，要在「經理人資訊」選擇這份合約由團隊中哪一位經理人負責管理。
分頁最下方可以選擇新增電子簽名圖章取代手動簽名；如果先前沒有上傳過電子圖章，需要先到「團隊資訊」設定才能使用這個功能。
### 建物謄本分頁是選填的嗎？（選填，僅供合約內容完備使用，不會顯示在廣告頁） {#jgb/D/contract-building-transcript-optional}
- phrasings:
  - {text: "建物謄本要填嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "謄本資訊會公開嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "建物謄本是選填的嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/contracts.js, help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「建物謄本」分頁是選填分頁，用來補充建物的謄本資訊，讓合約內容更完備。
這個分頁的資訊只是為了合約內容完備，並不會刊登在物件的網頁廣告上，可以放心填寫。
### 合約附件分頁能上傳什麼？（各類文件圖片或 PDF，最大 10MB） {#jgb/D/contract-attachments-optional}
- phrasings:
  - {text: "合約附件可以放什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "附件檔案大小限制", source: "draft:outline-20260920", status: proposed}
  - {text: "合約附件格式", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/landlordAttachment/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「合約附件」分頁（一般團隊）可以上傳授權代理人簽約同意書、建物所有權/有權出租之證明文件、使用執照影本、出租方同意轉租確認書、房屋位置格局示意圖、社區管理規約/住戶生活規約等文件，也有「其他」項目可以上傳附註條款、稅籍證明等。
分頁提示圖片僅支援 JPG、PNG、PDF 檔，檔案大小最大 10MB，每個項目限制的上傳檔案數量不同。
上傳這些附件的目的是為了避免日後爭議，屬於選填分頁。
「估價師租金簽註意見書」這個勾選項目只出現在社宅合約的分頁裡，一般合約的合約附件清單並不包含這一項。
### 補充條款有字數限制嗎？（最多 50 行、每行 50 字，可套用範本與複製其他合約） {#jgb/D/contract-additional-convention}
- phrasings:
  - {text: "補充條款字數限制", source: "draft:outline-20260920", status: proposed}
  - {text: "補充條款最多幾行", source: "draft:outline-20260920", status: proposed}
  - {text: "合約條款寫不下怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "補充條款範本", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/additionalConvention/Index.vue, code:src/utils/constants/contract.js, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「補充條款」分頁最多可以寫 50 行，每行限制 50 個字。
補充條款是因為系統的電子合約使用政府提供的公版定型化契約，如果需要補充其他合約條款，可以在這裡描述，系統會自動把條款內容帶入合約當中。
如果內容超過 50 行限制，建議另外寫成文字檔或圖片檔，改放在「合約附件」的「其他」項目上傳。
這個分頁也提供「預設補充條款」範本可以套用，或是選擇「複製現有合約資料」把其他合約已填寫的補充條款複製過來。
### 合約編輯分頁會依什麼條件增減？（紙本／DIY 合約、車位、Meta Capital 範本、稅務發票資格皆會影響） {#jgb/D/contract-edit-tabs-conditional-rules}
- phrasings:
  - {text: "合約分頁為什麼變少", source: "draft:outline-20260920", status: proposed}
  - {text: "紙本合約有哪些分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "車位合約分頁", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/useEditStore.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果這份合約是「上傳既有（紙本）」合約，可用分頁不會被縮減，跟一般團隊建立一般住宅合約時看到的整組分頁完全一樣（基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、公證、合約附件、補充條款）。
如果合約範本選擇 Meta Capital 系列，「公證」分頁會被拿掉，因為 Meta Capital 不支援公證。
如果物件用途是車位，可用分頁會被限縮成更小的子集；只有具備特定角色權限的團隊，車位合約才會額外顯示「稅與發票」分頁。
「稅與發票」分頁只有在團隊具備自動開立發票資格時才會顯示。
如果這份合約是「上傳既有（DIY）」自訂範本合約，可用分頁比一般團隊的整組少一項：不會出現「租金調幅設定」分頁，其餘分頁不變。
另外還有兩條不需要任何前置條件、對所有合約都生效的過濾規則：「租金調幅設定」分頁只有具備特定角色權限的團隊才顯示；「帳單設定」分頁則是統上、新北住都、新北住都停車場這幾個角色群組看不到（這是新北住都個案的暫時處理，等新北住都確認需求後才會恢復顯示）。
### 「建物謄本」分頁什麼時候不會顯示？（只有選中／未選合約範本時才顯示，選到英越文或泰文版就會被拿掉） {#jgb/D/contract-edit-building-transcript-visibility}
- phrasings:
  - {text: "建物謄本分頁不見了", source: "draft:outline-20260920", status: proposed}
  - {text: "什麼時候沒有建物謄本", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/useEditStore.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般住宅合約的「建物謄本」分頁只有在還沒選合約範本，或是選到「114年內政部住宅租賃契約(原房東)」「113年內政部轉租契約(包租轉租)」「代租代管契約(參考114年租賃契約)」這三種公版、或對應的公會中文版這三種時才會顯示；選到英文版、英越文版、英泰文版等其他範本時，這個分頁不會出現。
## 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） {#D-contract-edit-social-housing}
### 社宅合約「建物標的」分組有哪些分頁？（建物細節、現況補充、現況照片、附設傢俱四個分頁） {#jgb/D/social-housing-building-detail}
- phrasings:
  - {text: "社宅合約建物標的怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "建物細節填錯怎麼改", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約的「建物標的」分組包含建物細節（建物資訊／建物謄本）、現況補充、現況照片、附設傢俱四個分頁。
建物細節分頁主要呈現物件建立時填寫的資料，如果資料有誤，需要回到物件編輯修改，不能直接在合約分頁改。
### 社宅合約「現況照片」分頁一定要上傳嗎？（部分照片為必填，用來證明社宅內部現況設備存在） {#jgb/D/social-housing-photos-tab}
- phrasings:
  - {text: "現況照片一定要上傳嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅照片認證", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
現況照片分頁提醒部分現況照片為必填，因為要證明社宅內部現況確實有該項設備，未來需要提供給公會進行認證。
### 社宅合約「附設傢俱」分頁要填什麼？（各格局家具與數量） {#jgb/D/social-housing-facilities-tab}
- phrasings:
  - {text: "社宅附設傢俱", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅傢俱數量怎麼填", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
附設傢俱分頁要填入物件內部各格局的家具與數量。
### 社宅合約「基本條件」要填什麼？（合約範本、委託期間、住宅現況、物件返還狀態、代收定金、爭議處理） {#jgb/D/social-housing-rent-basic-conditions}
- phrasings:
  - {text: "社宅合約基本條件", source: "draft:outline-20260920", status: proposed}
  - {text: "委託租賃期間是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "物件返還狀態怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "代收定金幾日內轉交", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentBasic/SocialHousing.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約的「基本條件」分頁除了合約範本、合約起迄日，還要設定「委託租賃期間」或「委託管理期間」，也就是業者受託管理這個物件的期間。
這個分頁要設定「住宅現況」，例如是否為既存租賃契約住宅（帶租約住宅）、住宅所有權人自行使用或現為空屋無人使用等狀態。
「物件返還狀態」要設定租客返還物件時室內裝潢應回復的狀況，選項包含現況返還、回復原狀等。
如果業者會代收定金，這個分頁要設定業者收到定金後應於幾日內將租金轉交給原房東；另外還要設定張貼租賃廣告、修繕聯絡方式、爭議處理（如是否依仲裁法規定進行仲裁）等項目。
### 社宅合約的提前解約說明文字跟一般合約不同（只顯示少於預告天數需付違約金的情境，沒有達門檻天數的減免說明） {#jgb/D/social-housing-early-termination-difference}
- phrasings:
  - {text: "社宅合約提前解約說明", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅違約金跟一般合約一樣嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/rentBasic/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般住宅合約在違約金計算方式選「每月租金」時，畫面會分別列出「達到預告天數（含）以上通知」與「少於預告天數通知」兩種情境各自的違約金月數。
但如果合約範本選擇新北住都社宅專用範本，畫面只會顯示「少於預告天數通知，需支付違約金」的情境，不會出現達到天數即可減免的那一句。
### 社宅合約「租金費用」分頁要填什麼？（代租金額／租金與押金／生活費用） {#jgb/D/social-housing-rent-fees-tab}
- phrasings:
  - {text: "社宅租金費用怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅代租金額怎麼設定", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約的「租金費用」分頁要設定代租金額、租金與押金、生活費用等項目。
### 社宅合約「收款方式」怎麼設定？（轉帳、票據、現金三種，收款人可選原房東或業者） {#jgb/D/social-housing-payment-method-tab}
- phrasings:
  - {text: "社宅收款方式", source: "draft:outline-20260920", status: proposed}
  - {text: "收款人是誰", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/payment/SocialHousing.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約的「收款方式」跟一般合約不同，選項是「轉帳」「票據」「現金」三種。
收款方式分頁還要設定「收款人」是「原房東」還是「業者」本身，反映包租、代管兩種委託型態下實際收款對象不同。
### 社宅合約一定要公證嗎？（預設應辦理公證，可填理由不辦但視同放棄公證費補助；辦理公證後需下載文件紙本簽署再上傳歸檔） {#jgb/D/social-housing-notary}
- phrasings:
  - {text: "社宅合約一定要公證嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "公證費由誰負擔", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅簽約流程", source: "draft:outline-20260920", status: proposed}
  - {text: "公證後怎麼上傳", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/publicNotary/SocialHousing.vue, help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約的「公證」分頁預設文字是：本租賃契約應辦理公證，但租賃雙方如果因特定事由同意不辦理公證，視同自願放棄公證費申請的權益。
這個分頁可以設定公證是否強制執行特定事項、保證人效力，以及公證產生的額外稅費由誰負擔（例如平均分擔）。
填完所有分頁內容後，可以點選「預覽合約」，再點「下載合約文件」，依文件進行紙本簽約與公證。
完成公證後，需要把掃描好的合約 PDF 檔上傳，並選擇是否要綁定租客後送出，才能完成歸檔；因為公證目前是必要程序，社宅合約無法只在線上就完成簽約。
如果選擇不辦理公證，需要在「不辦理公證理由」欄位填寫理由，這個欄位最多只能輸入 100 個字元。
### 社宅合約「合約附件」要準備什麼？（測量成果圖、稅籍證明等，出租方與承租方各自也有附件上傳分頁） {#jgb/D/social-housing-attachments-tab}
- phrasings:
  - {text: "社宅合約附件要準備什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "出租方承租方附件上傳", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約的「合約附件」分頁要上傳測量成果圖、稅籍證明等文件；出租方與承租方各自也有獨立的「附件」分頁。
### 社宅合約「補助申請」分頁在做什麼？（配合社宅包租代管 333 補貼政策，出租方三種稅費減免） {#jgb/D/social-housing-subsidy-terms-tab}
- phrasings:
  - {text: "社宅333補貼政策", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅補助申請怎麼填", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「補助申請」分組主要配合政府的社會住宅包租代管 333 補貼政策：出租方有房屋稅、地價稅、租金所得稅三種稅費減免，承租方有公證費、修繕費、居家安全相關保險費三項費用補助，業者則有仲介費、代管費由政府全額補助的三年免費專業服務。
補助申請分頁要填寫補助費用申請日期、住宅出租修繕費、公證費、承租人租金補助等條件。
### 社宅合約「出租方」分組有哪些分頁？（基本資料、授權、附件三個分頁） {#jgb/D/social-housing-landlord-tabs-overview}
- phrasings:
  - {text: "社宅出租方分頁有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅出租方基本資料授權附件", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約「出租方」分組包含基本資料、授權、附件三個分頁。
### 社宅合約「授權」分頁要確認什麼？（合法建物條件、同意提供住宅、同意轉租等授權事項） {#jgb/D/social-housing-landlord-license-conditions}
- phrasings:
  - {text: "合法建物條件", source: "draft:outline-20260920", status: proposed}
  - {text: "出租方授權項目", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/landlordLicense/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「授權」分頁要確認合法建物條件，例如主要用途登記含有「住」「住宅」「農舍」「套房」「公寓」或「住宿」字樣，或提出合法房屋證明等文件。
「授權」分頁也要設定出租人是否同意提供住宅、是否同意出租予租屋服務事業再轉租（包租包管）等授權事項。
### 社宅合約「承租方」分組有哪些分頁？（基本資料、家庭＆財產、授權、附件） {#jgb/D/social-housing-tenant-tabs-overview}
- phrasings:
  - {text: "社宅承租方分頁有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅承租方基本資料家庭授權附件", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約「承租方」分組包含基本資料、家庭＆財產、授權、附件，用來確認租客的申請身分是否符合社會住宅資格。
### 社宅合約「基本資料」怎麼審核租客資格？（低收入戶、中低收入戶等身分別選項） {#jgb/D/social-housing-tenant-basic-status}
- phrasings:
  - {text: "低收入戶申請社宅", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅租客資格怎麼審核", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/tenantBasic/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
基本資料分頁要勾選承租方身分別，選項包含一般戶、低收入戶、中低收入戶、六十五歲以上之老人（限申請人本人）、住宅政策補貼戶等，或勾選「以上均無」。
### 社宅合約「家庭＆財產」分頁要登記什麼？（家庭成員、不動產與動產總額、最近年所得） {#jgb/D/social-housing-tenant-household}
- phrasings:
  - {text: "社宅家庭財產申報", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅不動產動產總額申報", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/tenantHousehold/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
「家庭＆財產」分頁要登記家庭成員、所在地址、持分比例、不動產總額、動產總額與最近年所得。
### 社宅合約承租方的「授權」分頁要同意什麼？（財稅所得總檢核、家庭年所得百分位等資格條件） {#jgb/D/social-housing-tenant-license}
- phrasings:
  - {text: "承租方授權項目", source: "draft:outline-20260920", status: proposed}
  - {text: "財稅所得總檢核授權", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/tenantLicense/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
授權分頁要勾選同意授權的項目，包含申請人及家庭成員是否符合財稅所得總檢核、家庭年所得是否低於當地一定百分位所得等資格條件。
### 社宅合約「業者」分頁在做什麼？（確認團隊資料與經理人資訊，有誤要回團隊資訊或帳號資訊修改） {#jgb/D/social-housing-dealer-basic}
- phrasings:
  - {text: "社宅業者分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "業者資料錯誤要去哪改", source: "draft:outline-20260920", status: proposed}
- sources: [help:Landlordonboarding09Socialhousing_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約的「業者」分頁用來確認團隊資料與經理人資訊是否正確。
如果資料有誤，需要點選藍字的「團隊資訊」或「帳號資訊」連結回去修改，不能直接在這個分頁修改。
### 社宅合約「點交證明文件」分頁在約定什麼？（點交狀態與修繕責任的預先約定，不是簽約後實際執行的點交） {#jgb/D/social-housing-move-in-terms}
- phrasings:
  - {text: "社宅點交證明文件是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "合約裡的點交跟實際點交一樣嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/moveIn/Index.vue, code:src/routes/contracts.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
社宅合約編輯畫面裡的「點交證明文件」分頁，是在合約條款中先約定點交狀態與修繕責任，例如選擇「現狀」或「修繕後點交」。
分頁提示：依照合約，所有品項預設以現狀且由出租方負責修繕，如果承租方刻意損壞，則由承租方自行負擔責任。
這個分頁只是合約條款裡的預先約定，跟簽約完成之後、實際執行點交作業的流程是不同的頁面。
### 社宅合約選「包租包管」或「轉租」範本，分頁會不同嗎？（包租包管隱藏承租方戶籍/證照/附件，轉租隱藏出租方證照/附件） {#jgb/D/social-housing-charter-sublet-tab-hiding}
- phrasings:
  - {text: "社宅包租包管範本分頁", source: "draft:outline-20260920", status: proposed}
  - {text: "社宅轉租範本分頁差異", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/use/useEditStore.js, code:app/Http/Controllers/ContractController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果合約範本選擇「包租包管」範本，承租方分組下的「家庭＆財產」「授權」「附件」三個分頁不會顯示。
如果合約範本選擇「轉租」範本，出租方分組下的「授權」「附件」兩個分頁不會顯示。
## 簽約與合約檢視 {#D-contract-sign-view}
### 合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效，天數為團隊可調整設定） {#jgb/D/contract-invite-and-review-period}
- phrasings:
  - {text: "合約審閱期多久", source: "draft:outline-20260920", status: proposed}
  - {text: "合約邀請多久會過期", source: "draft:outline-20260920", status: proposed}
  - {text: "租客沒簽約連結失效", source: "draft:outline-20260920", status: proposed}
  - {text: "審閱期天數", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php, code:app/Http/Controllers/Internal/ContractWriteController.php, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
房東送出合約邀請後，系統會給租客一段審閱期才能簽約；天數其實是讀團隊設定，沒有設定才用預設的 3 天（72 小時）。
這個審閱天數設定屬於團隊層級，不同團隊可以各自覆蓋預設值。
從發送邀請時開始計算，租客如果沒有在期限內完成簽約，這個合約邀請連結就會失效。
### 租客簽約要經過哪些步驟？（承租方簽約資料、上傳身分證明文件與印章、部分合約範本另有條款勾選、雲想科技畫面簽名） {#jgb/D/contract-sign-flow-steps}
- phrasings:
  - {text: "租客怎麼簽約", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約要傳哪些印章", source: "draft:outline-20260920", status: proposed}
  - {text: "簽名過程有紀錄嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/contract/sign.blade.php, code:src/entry/contract-sign.js, code:src/pages/contracts/edit/_methods/getFormDataForStepDone.js, help:contract_review_period_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
租客簽約頁面第一步要填寫「承租方簽約資料」，並選擇「簽約身份」。
頁面會要求上傳承租方身份證明文件影本；另外還有「工作名片/學生證」（同一個上傳欄位）與「良民證」等其他證明文件的上傳欄位，各自獨立、不能互相替代。
印章上傳依簽約身份不同而異：租客身份要上傳「小章」；法人身份（非租客）則要上傳「大章」與「小章」兩個欄位。
如果這份合約是 GTB 契約範本，簽約前會多一個步驟：畫面下方會出現 5 個條款確認選項（詳閱契約條款、無法更改內容、續約通知天數、履約保證金退還天數、吸菸罰緩等規定），要全部勾選才能繼續；一般合約範本沒有這個額外勾選步驟。
確認資料無誤後，如果是 GTB 契約，要先點「下一步，同意合約條款」進到條款頁勾完 5 個確認選項，再點「下一步，前往簽名」才會進入雲想科技（Thinkcloud）的簽約畫面；一般合約範本只有一個「下一步」按鈕，點選後直接進入雲想科技簽約畫面。
整個瀏覽、簽名過程都有時間戳記與 IP 紀錄。
### 電子簽章簽約要另外收費嗎？（系統內沒有簽章計費機制，簽約流程無付費／加購畫面） {#jgb/D/contract-esign-no-extra-fee}
- phrasings:
  - {text: "電子簽章要收費嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約要加購嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "電子簽章計費", source: "draft:outline-20260920", status: proposed}
- sources: [code:database/migrations/2026_06_17_000002_create_contract_esign_table.php, code:resources/views/contract/sign.blade.php]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
JGB 的電子簽章走 Thinkcloud 這家第三方服務，相關的簽約紀錄裡沒有任何費用或點數欄位。
租客的簽約頁流程沒有付費或加購的畫面元素。
### 合約簽約後可以修改嗎？（送出前可編輯、簽名前可取消簽名重編，簽署完成即無法更改，需重新簽一份新合約） {#jgb/D/contract-locked-after-signing}
- phrasings:
  - {text: "合約簽名後可以改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "合約內容填錯怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "取消簽名重新編輯", source: "draft:outline-20260920", status: proposed}
  - {text: "簽約後修改合約", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
合約如果還沒發送出去，都可以點選小齒輪選擇「編輯合約」進行編輯與修改。
合約已經發送但雙方都還沒完成簽名前，可以點選小齒輪選擇「取消簽名」，取消之後可以重新編輯這份合約。
如果合約已經簽名完成，就無法再修改內容，需要重新創建一份合約才能修改。
合約簽署完成即會生成 PDF 檔案，且電子簽章具有法律效力，無法更改該合約或物件的內容，內容有誤時需要先解約才能再簽署一份新合約。
### 合約檢視頁面看得到什麼？（出／承租方資訊、業者、經理人資訊，以及點交點退進行中的提示） {#jgb/D/contract-show-panels}
- phrasings:
  - {text: "合約檢視頁面看得到什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "合約詳細資料在哪看", source: "draft:outline-20260920", status: proposed}
  - {text: "合約點交中提示", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/show/Index.vue, code:src/pages/contracts/show/_parts/PanelInfoStructure.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約檢視頁面會顯示「出／承租方資訊」「業者」「經理人資訊」等區塊面板。
如果合約正在點交流程中，頁面會顯示提示：合約點交中，等待承租方確認，或合約點交中，請確認點交結果，依目前是哪一方在等待而不同。
點退流程中的合約也會有類似的提示：合約點退中，等待承租方確認，或合約點退中，請確認點退結果。
### 上傳既有（紙本）合約檔案有什麼限制？（PDF、最大 10MB，依合約／續約／終止合約分類歸檔） {#jgb/D/contract-show-paper-upload-archive}
- phrasings:
  - {text: "上傳紙本合約檔案限制", source: "draft:outline-20260920", status: proposed}
  - {text: "既存合約歸檔類別", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/contract/show.blade.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
合約檢視頁用來上傳既有（紙本）合約的歸檔檔案，支援 PDF 檔，檔案大小最大 10MB。
歸檔資料依照來源分成三種類別：合約、續約、終止合約，畫面上方會顯示對應的類別標籤。
### 合約檢視頁面會提示信用卡自動扣款授權嗎？（收款設定需要信用卡自動扣款時才會提示前往授權） {#jgb/D/contract-show-creditcard-auth-prompt}
- phrasings:
  - {text: "信用卡自動扣款授權", source: "draft:outline-20260920", status: proposed}
  - {text: "前往授權是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/contract/show.blade.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果合約的收款設定需要信用卡自動扣款，合約檢視頁面會提示「即將前往授權」，說明需要授權信用卡才能在約定繳費日自動扣款，確認後點選「前往授權」繼續流程。
### 上傳既有合約跟建立電子合約差在哪？（既存合約用於已簽好或有自己公版合約的情境，皆可續用系統帳務／修繕追蹤） {#jgb/D/contract-upload-existing-vs-electronic}
- phrasings:
  - {text: "上傳既有合約適用情境", source: "draft:outline-20260920", status: proposed}
  - {text: "上傳合約檔案太大怎麼辦", source: "draft:outline-20260920", status: proposed}
  - {text: "既存合約跟電子合約差別", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
「上傳合約」適用於已經跟租客簽署完的合約，或是業者本身特有的公版合約，讓已有合約的房東也能無縫接軌使用系統。
不論是上傳既有合約或使用 JGB 內政部公版合約，之後都可以透過系統做後續合約、帳務、修繕追蹤。
如果掃描的合約 PDF 檔案大於 10MB，建議先在印表機端調整掃描品質，或使用線上壓縮工具縮小檔案再上傳。
## 點交 {#D-move-in}
### 點交清單怎麼確認？（依合約約定的傢俱項目逐一上傳照片、標註出租方或承租方負責） {#jgb/D/move-in-checklist-and-responsibility}
- phrasings:
  - {text: "點交清單怎麼確認", source: "draft:outline-20260920", status: proposed}
  - {text: "點交要上傳照片嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "點交責任歸屬", source: "draft:outline-20260920", status: proposed}
  - {text: "點交備註字數限制", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/contract/move-in.blade.php, code:src/pages/contracts/move-in/Index.vue, code:src/pages/contracts/edit/facilities/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點交清單會列出合約成立時約定的交接項目，點選「編輯」可以上傳照片或加上備註說明現況。
每個項目可以標註責任歸屬是「出租方」還是「承租方」負責，這個標註是從合約的附設傢俱分頁帶過來的。
點交備註（補充條款）欄位限制填寫 20 行，每行限制 50 個字，超過部分系統會自動裁切。
如果這個空間目前沒有任何品項，畫面會提示「此空間尚未提供任何品項」。
### 點交要填另計費用起始度數嗎？（依合約設定另計的費用項目要輸入起始度數，會直接帶入日後帳單計算） {#jgb/D/move-in-meter-readings}
- phrasings:
  - {text: "點交要填電表度數嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "點交起始度數", source: "draft:outline-20260920", status: proposed}
  - {text: "點交後帳單怎麼算電費", source: "draft:outline-20260920", status: proposed}
- sources: [code:resources/views/contract/move-in.blade.php, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點交流程裡有「另計費用起始度數」項目，根據合約上的設定，某些費用是額外計算的，需要輸入每筆費用的起始度數。
點交清單如果有填寫初始電費度數，這個度數會直接帶入日後帳單，系統會自動計算電費。
### 點交頁面一般合約跟社宅合約用的是同一個嗎？（不是，一般住宅合約用一般合約的點交頁面，社宅合約會被導向社宅合約的點交頁面） {#jgb/D/move-in-page-general-vs-social-housing}
- phrasings:
  - {text: "社宅點交頁面跟一般合約一樣嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "點交頁面差異", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php, code:routes/web.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般住宅合約點交送出後，會進入一般合約專用的點交頁面。
如果合約的物件用途是社會住宅，系統會強制把畫面導轉到另一個社宅專用的點交頁面。
### 點交送出後還能再送一次嗎？（已完成點交無法再次送出；已送出、等待租客確認中的清單要先取消邀請才能改） {#jgb/D/move-in-blocked-states}
- phrasings:
  - {text: "點交已送出可以改嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "點交完成能重新點交嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "取消點交邀請", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Contract.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果這份合約已經完成點交，系統會擋下再次送出點交的動作，並提示「此合約已完成點交，無法再次送出點交」。
如果點交清單已經送出、正在等待租客確認，系統也會擋下重複送出，並提示要先取消點交邀請，才能重新送出點交清單。
### 點交邀請送出後可以取消嗎？（可以，系統會記錄「取消點交邀請」這個動作） {#jgb/D/move-in-cancel-invite}
- phrasings:
  - {text: "點交邀請可以取消嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "已送出的點交怎麼收回", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Contract.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
已經送出、等待租客確認的點交邀請可以取消，系統會記錄這個「取消點交邀請」動作。
### 點交結果能下載 PDF 嗎？（有專屬頁面可以檢視或下載點交 PDF） {#jgb/D/move-in-result-pdf}
- phrasings:
  - {text: "點交結果PDF", source: "draft:outline-20260920", status: proposed}
  - {text: "點交可以下載嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:routes/web.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點交結果有專屬的頁面，可以用來檢視或下載點交內容的 PDF 檔。
### 點交是必要流程嗎？（點交是選擇性操作，未點交也能發帳單；簽約完成後即可在執行中合約選取物件點交） {#jgb/D/move-in-optional-and-timing}
- phrasings:
  - {text: "點交一定要做嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "什麼時候可以點交", source: "draft:outline-20260920", status: proposed}
  - {text: "不點交可以發帳單嗎", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
點交基本上是選擇性操作，可以依房東的習慣和房客約定自行決定是否進行，沒有點交也可以發送帳單。
點交的時機是簽約完成後，就可以在「執行中合約」選取想點交的物件進行點交。
執行中合約列表會用燈號的方式顯示這份合約有沒有進行點交。
## 點退 {#D-move-out}
### 點退清單怎麼處理設備損壞？（可編輯填入賠償金額與理由，過程可儲存草稿） {#jgb/D/move-out-checklist-and-damage}
- phrasings:
  - {text: "點退設備損壞怎麼處理", source: "draft:outline-20260920", status: proposed}
  - {text: "點退可以先存草稿嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "點退賠償金額", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/move-out/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點退清單會列出點交時約定的傢俱項目，如果物件沒有提供傢俱品項，畫面會提示不需要清點。
點退時如果發現設備有損壞，需要由房客負賠償責任，可以點選「編輯」並填入賠償金額與理由；沒有標註就代表狀況正常。
點退過程可以先按「儲存點退草稿」，不用一次填完，儲存失敗時畫面會提示「草稿儲存失敗，請稍後再試」。
### 點退會產生什麼帳單？（含提前解約金、點退押金、賠償金，設定期限後發送，租客確認並繳款才算完成） {#jgb/D/move-out-bill-generation}
- phrasings:
  - {text: "點退帳單包含什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "點退押金怎麼退", source: "draft:outline-20260920", status: proposed}
  - {text: "點退完成的條件", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html, code:src/pages/contracts/move-out/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點退流程分兩步：第一步確認點交清單、填寫損壞賠償金額，第二步才會進入「點退找補費用」頁面產生帳單。
點退確認清單、填完損壞賠償金額之後，系統會製作點退帳單，內容包含提前解約金、點退押金、賠償金，並要填入帳單期限。
帳單設定完成後要發送給租客，等租客確認點退內容並完成繳款，才算完成點退程序。
### 什麼合約可以點退？（合約狀態須為執行中／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外） {#jgb/D/move-out-eligibility-conditions}
- phrasings:
  - {text: "什麼合約可以點退", source: "draft:outline-20260920", status: proposed}
  - {text: "沒有註冊的租客可以點退嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "點退合約狀態限制", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Contract.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點退有一個限制：如果合約沒有綁定 JGB 註冊租客帳號，一般情況下不可以點退。
但如果是「免註冊租客」（建檔時就標註不綁定 JGB 帳號），因為點退一送出就立即成立、不需要租客登入同意，所以這種情況仍然允許點退。
合約狀態必須是「合約成立」「點交完成」「歷史合約」或「完成歷史合約」其中之一才能點退；已經點退完成過的合約不能再次點退。
### 點退的時間限制是什麼？（合約到期前 30 天起可以點退，過了到期日之後目前沒有再設上限） {#jgb/D/move-out-timing-window}
- phrasings:
  - {text: "點退時間限制", source: "draft:outline-20260920", status: proposed}
  - {text: "點退要在到期前幾天辦理", source: "draft:outline-20260920", status: proposed}
  - {text: "合約到期後還能點退嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Contract.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點退最早可以在合約到期日的前 30 天開始執行。
點退原本也有到期日後 30 天內的上限，但這個上限已經在 2022/08/04 因法律顧問需求改為「無限制」，所以合約到期之後能不能點退目前沒有再受這個上限卡住。
### 點退完成的合約為什麼還在「執行中合約」？（只要還沒到合約到期日就會留在執行中，到期後才轉入歷史合約） {#jgb/D/move-out-remains-in-active-list}
- phrasings:
  - {text: "已點退為什麼還在執行中合約", source: "draft:outline-20260920", status: proposed}
  - {text: "歷史合約是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "點退狀態分類", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
已經點退或已經辦理提前解約的合約，如果還沒到合約到期日，都還是會停留在「執行中合約」列表。
歷史合約是指已經到期的合約；因為點退可以在合約到期前 30 天就開始執行，所以歷史合約列表底下的狀態還會再細分成「點退完成」「未退押金」「待退押金」「點退中」。
### 點退第二步「點退找補費用」頁面要填什麼？（傢俱賠償、應退費用、違約金，另可填備註、期限、附件） {#jgb/D/move-out-fee-adjustment-step}
- phrasings:
  - {text: "點退找補費用要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "點退第二步流程", source: "draft:outline-20260920", status: proposed}
  - {text: "傢俱賠償跟應退費用差在哪", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/move-out/Index.jsx, code:src/pages/contracts/move-out/_parts/__Compensation.vue, code:src/pages/contracts/move-out/_parts/__Refund.vue, code:src/pages/contracts/move-out/_parts/__LiquidatedDamages.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
點退流程的第二步會進入「點退找補費用」頁面，這裡才是真正產生帳單的畫面，跟第一步的點交確認清單是分開的兩個步驟。
這個頁面要填的收費／退費項目包含「傢俱賠償」、「應退費用」、「違約金」，另外還可以填寫備註、繳費期限、附件。
## 續約 {#D-renew}
### 怎麼一次幫多筆合約續約？（合約總表「建立合約」旁選批次續約，異動中的合約不能選） {#jgb/D/renew-batch-entry-and-selection}
- phrasings:
  - {text: "批次續約怎麼操作", source: "draft:outline-20260920", status: proposed}
  - {text: "續約可以選哪些合約", source: "draft:outline-20260920", status: proposed}
  - {text: "哪些合約不能續約", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/pick/Index.jsx, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在「執行中合約」點選右上方建立合約旁的小箭頭，選擇「批次續約」，就會進入合約挑選頁面。
挑選合約時可以用案名、地址、經理人、大房東、租客、ID 六種範圍搜尋。
續約功能無法選擇正在異動中的合約，包括「提前解約申請中」「點交中」及「點退中」的合約。
### 續約日期怎麼設定？（快速日期設定一次套用全部，或個別指定每份合約的續約日） {#jgb/D/renew-date-setting-modes}
- phrasings:
  - {text: "續約日期怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "續約可以一次設定嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "租客收不到續約通知", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/renew/Index.vue, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
選好要續約的合約之後，可以用「快速日期設定」一次套用同一個續約日期到所有合約。
也可以在下方個別調整，用「個別指定續約日」分別設定每一份合約各自的續約日期。
如果租客的聯繫方式尚未驗證，或是通知功能沒有開啟，畫面會提示這位租客無法收到續約通知。
### 續約可以上傳紙本已簽合約嗎？（可以，提供雙方已完成簽約的紙本合約掃描檔即可） {#jgb/D/renew-upload-paper-signed}
- phrasings:
  - {text: "續約可以上傳紙本合約嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "續約用電子簽名圖章", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/renew/Index.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
續約頁面提供「合約檔案」上傳功能，可以直接提供雙方已經完成簽約的紙本合約掃描檔。
這個功能也支援用電子簽名圖章取代親手簽名，但如果團隊還沒上傳電子簽名圖章，這個選項會無法啟用。
### 續約可以預先編輯帳單嗎？（續約預覽頁可先編輯續約期間帳單，實際帳單於完成續約後才產生） {#jgb/D/renew-preview-bill-generation}
- phrasings:
  - {text: "續約可以先看帳單嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "續約帳單什麼時候產生", source: "draft:outline-20260920", status: proposed}
  - {text: "確認續約帳單頁面", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/renew/Preview.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
續約流程有一個「確認續約帳單」的預覽頁面，會依續約日期與週期設定，預先產生一系列帳單。
這些帳單可以預先編輯標題、繳費期限、帳單週期、金額、細項與自動執行動作，但畫面會提示：實際帳單要等合約完成續約後才會真正產生。
如果這份合約沒有可以預先產生的帳單，畫面會顯示「此合約無可預產的帳單」。
### 續約邀請發出後流程是什麼？（租客簽回後可在「待租客簽回」查找，房東確認無誤後立即簽名完成續約） {#jgb/D/renew-signing-flow}
- phrasings:
  - {text: "續約簽約流程", source: "draft:outline-20260920", status: proposed}
  - {text: "租客簽回續約後要做什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "續約怎麼完成", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
設定完續約日期後，系統會將續約邀請發送給租客，可以在「待租客簽回」欄位中查找這份合約。
租客簽回後，房東方確認資料無誤，就可以點選「立即簽名」並完成簽約程序，最後即完成該合約的續約。
### 續約邀請效期是幾天？（預設 3 天，團隊可覆蓋設定） {#jgb/D/renew-invite-review-days}
- phrasings:
  - {text: "續約邀請幾天內要簽", source: "draft:outline-20260920", status: proposed}
  - {text: "續約審閱天數", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Services/ContractService.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
續約邀請發出後的審閱天數，預設是 3 天，團隊可以另外設定天數覆蓋這個預設值。
### 續約時資料怎麼沿用？（新合約由舊合約複製，並更新出租方/承租方最新資料；週期設定有調整就用新的、沒調整就沿用） {#jgb/D/renew-data-carryover-rules}
- phrasings:
  - {text: "續約會沿用舊合約資料嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "續約聯絡資料會更新嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Services/ContractService.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
續約時系統會複製原合約產生新合約，並用出租方、承租方目前最新的角色或會員資料，更新聯絡電話、Email 等欄位，不是直接照抄舊合約當時填寫的資料。
繳費週期、帳單週期制度等設定，如果續約頁面有調整就用新的值，沒調整則沿用原合約設定。
## 提前解約 {#D-early-termination}
### 房東申請提前解約要選什麼理由？（新版中文合約有 10 項法定理由可選，其餘合約只能選「其他」） {#jgb/D/early-termination-reasons}
- phrasings:
  - {text: "提前解約理由有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "解約要選什麼原因", source: "draft:outline-20260920", status: proposed}
  - {text: "非中文合約解約理由", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php, code:resources/views/layouts/lightbox/early-termination-by-landlord.blade.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東發起提前終止合約時，一定要選擇「原因」，選項一律包含「其他」。
只有合約檔案是新版中文合約時，才會顯示其他 10 項法定理由，例如「出租方為重新建築而必要收回」「承租方遲付租金之總額達兩個月之金額」「承租方擅自將租賃住宅轉租或轉讓租賃權於他人」等。
選擇「其他」以外的理由時，畫面不會出現理由說明文字欄位；但若選「其他」，會出現一個文字框讓房東輸入解約理由文字。
### 申請提前解約要填什麼？（欲提前解約日須早於原合約到期日、違約金由誰付、佐證資料） {#jgb/D/early-termination-form-fields}
- phrasings:
  - {text: "提前解約要填什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "解約違約金由誰付", source: "draft:outline-20260920", status: proposed}
  - {text: "提前解約日期限制", source: "draft:outline-20260920", status: proposed}
  - {text: "取消提前終止合約", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東申請提前解約時要填寫「欲提前解約日」，這個日期必須早於原合約的到期日，否則系統會擋下申請。
表單也要選擇「違約金由誰付」以及填寫違約金金額，並可以上傳佐證資料。
### 誰可以取消已送出的提前解約申請？（房東透過小齒輪取消，租客只有在提前解約確認中狀態才能取消） {#jgb/D/early-termination-tenant-cancel}
- phrasings:
  - {text: "房東怎麼取消提前終止合約", source: "draft:outline-20260920", status: proposed}
  - {text: "租客可以取消提前解約嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "取消提前解約條件", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php, help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
房東如果想取消已經送出的提前解約申請，可以點選合約旁的小齒輪，選取「取消提前終止合約」。
租客也可以取消提前解約申請，但只有在合約狀態是「提前解約確認中」時才能取消。
如果合約不是這個狀態，系統會擋下取消動作並提示「您無法取消這份提前解約」。
### 什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起） {#jgb/D/early-termination-eligibility}
- phrasings:
  - {text: "什麼合約可以提前解約", source: "draft:outline-20260920", status: proposed}
  - {text: "可否提前解約設定對房東有效嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "續約中可以提前解約嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Contract.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
可以申請提前解約的合約，狀態必須是「合約成立」或「點交完成」；已經在提前解約流程中、或已經完成過提前解約的合約不能再次申請。
合約裡「租客是否可以提前解約」這個設定，只會限制租客身分發起提前解約；如果是房東身分要發起，不受這個設定限制。
如果合約正在續約流程中、還沒完成簽名，也不能發起提前解約。
### 提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金） {#jgb/D/early-termination-effect-move-out}
- phrasings:
  - {text: "提前解約後多久可以點退", source: "draft:outline-20260920", status: proposed}
  - {text: "提前解約影響", source: "draft:outline-20260920", status: proposed}
- sources: [help:landlordonboarding04lease_zh-Hant.html]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
成功提前終止合約後，合約終止日會依新的日期更新，在租期到期前 30 天，就可以執行「點退押金」。
點退時系統會依照合約條件，自動帶入並判斷是否有違約金，房東可以依照實際狀況調整數字。
## 租約公證（公證分頁與公證服務） {#D-notary}
### 一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項，僅支援中文合約） {#jgb/D/general-contract-notary-tab}
- phrasings:
  - {text: "一般合約公證怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "公證強制執行事項", source: "draft:outline-20260920", status: proposed}
  - {text: "英文合約可以公證嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/contracts/edit/publicNotary/General.vue]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
一般合約的「公證」分頁要先選擇這份租賃合約是否同意辦理公證。
選擇同意辦理公證後，可以複選「公證書載明下列事項應逕受強制執行」的項目，包含：承租方如於租期屆滿後不返還租賃住宅；承租方未依約給付之欠繳租金、費用及代繳之管理費或違約應付金額；出租方於租期屆滿或契約終止時應返還承租方之全部或一部分押金。
這個分頁也可以設定保證人效力。
畫面提示：目前英文與英越文版合約不支援公證這個項目。
### 簽約時進入的雲想科技頁面是做什麼的？（承載 Thinkcloud 電子簽署流程的內嵌頁面，一般合約、委託合約皆會用到） {#jgb/D/contract-thinkcloud-esign-service}
- phrasings:
  - {text: "簽約跳出的雲想科技頁面是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "雲想科技畫面是誰在用", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php, code:resources/views/contract/thinkcloud.blade.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
這個頁面是用來承載 Thinkcloud（雲想科技）電子簽署畫面的內嵌頁面，簽約流程走到需要簽名的步驟時會導向這裡。
這個頁面不只租賃合約會用到，委託合約簽署也共用同一個頁面。
### 雲想科技簽署畫面依合約類型有什麼差異？（公會版本合約加補充條款多一個協商條款簽名框；DIY 客製化合約解析失敗時會顯示提示訊息，不會直接出現系統錯誤畫面） {#jgb/D/contract-thinkcloud-signing-variants}
- phrasings:
  - {text: "DIY合約怎麼簽名", source: "draft:outline-20260920", status: proposed}
  - {text: "協商條款簽名框是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:app/Http/Controllers/ContractController.php]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
如果合約是公會版本合約且有補充條款，簽署畫面會多一個「協商條款」簽名框。
如果是 DIY 客製化合約（自行上傳範本），系統會嘗試用兩種方式解析上傳的 PDF 底稿；如果兩種都解析失敗，畫面會顯示提示訊息（例如請用瀏覽器「列印→另存為 PDF」重新輸出後再上傳），而不是直接跳出系統錯誤畫面，但簽約流程仍需要使用者依提示重新上傳才能繼續。
## 委託合約（列表、建立編輯、檢視） {#D-entrust-contract}
### 委託合約是什麼？（房東委託業者包租代管的合約，跟業者與租客之間的租賃合約是不同份文件） {#jgb/D/entrusted-contract-what-is-it}
- phrasings:
  - {text: "委託合約是什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約跟租賃合約差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約狀態頁籤", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/list/_parts/PageTop.jsx, docs:knowledge/jgb-product-facts.md#single-vs-dual-contract]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
委託合約是房東與業者之間的合約，用來約定房東把物件委託給包租代管業者管理；它跟業者與租客之間的租賃合約是各自獨立的兩份合約。
委託合約總表跟一般合約總表一樣分成五個狀態頁籤：待發送委託約、待房東簽回、待管理者簽名、執行中委託約、歷史委託約。
這裡的簽署角色跟一般合約相反：委託合約是等房東簽回，最後由管理者（業者）簽名完成。
### 委託合約「包租」跟「代管」有什麼不同？（代管必填服務費制度／週期／約定日期，包租用包租租金及其計算制度） {#jgb/D/entrusted-contract-lease-type}
- phrasings:
  - {text: "包租跟代管差在哪", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約類型", source: "draft:outline-20260920", status: proposed}
  - {text: "代管合約要填什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/edit/requirement/Basic.jsx, code:src/pages/entrustedContracts/edit/requirement/Fees.jsx, docs:knowledge/jgb-product-facts.md#charter-vs-management]
- target_user: [property_manager, prospect]
- business_types: [system_provider]
- instance_applicability: general
委託合約用「委託約類型」區分「包租合約」與「代管合約」兩種，也要設定委託約範本、委託約起迄日期。
選擇代管合約時，必須填寫服務費制度、服務費幣別、服務費金額（收取頻率與約定日期）。
選擇包租合約時，則是用「包租租金」及其計算制度、收取頻率、約定日期。
### 委託合約編輯畫面有哪些分頁？（房東資訊、委託條件三頁、管理方資訊共 3 組 5 頁） {#jgb/D/entrusted-contract-tabs-overview}
- phrasings:
  - {text: "委託合約分頁有哪些", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約編輯步驟", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/routes/entrustedContracts.js]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約編輯畫面分成「房東資訊」「委託條件」「管理方資訊」三個分組，「委託條件」底下又分基本資料、租金費用、收款方式三個分頁，合計 5 個分頁。
### 委託合約編輯完成後怎麼進入簽署？（點右上角「預覽合約」先儲存資料，再進入檢視頁面） {#jgb/D/entrusted-contract-preview-to-show}
- phrasings:
  - {text: "委託合約怎麼進入簽署", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約預覽合約按鈕", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/edit/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約編輯完成後，點選右上角「預覽合約」會先儲存資料，再進入委託合約檢視頁面，後續的簽署與歸檔都在檢視頁面進行。
### 委託合約上傳既有檔案限制多大？（6MB，比一般合約的 10MB 小） {#jgb/D/entrusted-contract-upload-file-size-limit}
- phrasings:
  - {text: "委託合約上傳檔案大小限制", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約檔案6MB", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/show/_parts/signerInfo/ArchiveFileUploader.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約檢視頁面上傳既有委託合約檔案的大小上限是 6MB，比一般租賃合約檢視頁面的 10MB 上限更小。
### 委託合約的收費分頁要設定什麼？（服務費或包租金額的計算模式與週期，押金提示不得超過兩個月租金） {#jgb/D/entrusted-contract-fees}
- phrasings:
  - {text: "委託合約收費怎麼算", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約押金上限", source: "draft:outline-20260920", status: proposed}
  - {text: "跨月計算與當月分算", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/edit/requirement/Fees.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約的收費分頁要設定計算模式、週期、單價、幣別等資訊。
分頁上會提示：依內政部租賃住宅市場發展及管理條例規定，一般租賃契約押金額度最高不得超過兩個月租金。
分頁也可以參考支付金額與參考服務費金額，並支援跨月計算或當月分算兩種計費方式。
### 委託合約的房東資訊怎麼填？（房東註冊或房東免註冊、選擇個人房東或法人房東身份） {#jgb/D/entrusted-contract-landlord-info}
- phrasings:
  - {text: "委託合約房東資訊怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "房東一定要註冊帳號嗎", source: "draft:outline-20260920", status: proposed}
  - {text: "房東免註冊是什麼", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/edit/landlordInfo/LandlordInfo.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約的房東資訊分頁要選擇「出租方身份別」，是「個人房東」還是「法人房東」。
跟一般租賃合約類似，這裡也有「房東註冊」與「房東免註冊」兩種模式：房東註冊代表房東會自己註冊 JGB 會員並自行填妥出租方資訊；房東免註冊代表房東不需要註冊會員，改由管理者協助填寫房東資訊。
分頁提示：系統會將這裡填寫的房東資料謄寫到合約內，過程經過加密處理，不讓資料外流。
### 委託合約的經理人資訊分頁要填什麼？（公司基本資料、指定經理人、租賃住宅管理人員名稱與證號、電子簽名圖章） {#jgb/D/entrusted-contract-manager-info}
- phrasings:
  - {text: "委託合約經理人資訊怎麼填", source: "draft:outline-20260920", status: proposed}
  - {text: "租賃住宅管理人員證號", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約電子簽名圖章", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/edit/managerInfo/ManagerInfo.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約的經理人資訊分頁要確認公司資訊（公司登記名稱、統一編號、登記地址、通訊地址、電話、Email）是否正確，並在「經理人」欄位指定這份合約由誰管理。
這個分頁另外有「租賃住宅管理人員資訊」欄位，要填寫租賃住宅管理人員名稱與證號，這跟前面的經理人資訊是不同的欄位。
分頁最下方也可以設定「使用電子簽名圖章取代親手簽名」。
### 委託合約收付款資訊怎麼設定？（沒有選擇器，固定顯示「出租方帳戶」與「管理方帳戶」兩個現金收付區塊，後者必填） {#jgb/D/entrusted-contract-payment}
- phrasings:
  - {text: "委託合約收付款怎麼設定", source: "draft:outline-20260920", status: proposed}
  - {text: "收款是給房東還是業者", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約可以選一種收款方式嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/edit/requirement/Payment.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約的「收付款資訊」分頁沒有讓你先選一種收款方式的選擇器，畫面固定顯示「現金收付－出租方帳戶」與「現金收付－管理方帳戶」兩個區塊，兩個都會顯示，不是挑一個顯示。
「現金收付－管理方帳戶」是必填區塊；「現金收付－出租方帳戶」則沒有標示必填。
兩個區塊都要填寫銀行代碼、銀行名稱、帳戶名稱、銀行帳號，管理方帳戶還可以把常用帳號加入清單方便下次選用。
### 委託合約檢視頁面能做什麼？（查看歸檔資料、上傳既有委託合約檔案、未簽署前可返回編輯） {#jgb/D/entrusted-contract-show-and-upload}
- phrasings:
  - {text: "委託合約檢視頁面看得到什麼", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約上傳檔案", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約還沒簽名可以改嗎", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/show/Index.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
委託合約檢視頁面會顯示這份合約的「歸檔資料」，如果還沒上傳合約檔案，會提示「您尚未上傳合約檔案」；上傳後會顯示「檔案已上傳」。
「返回編輯」按鈕只有在合約狀態是「待發送委託約」（尚未寄出邀請）時才會顯示；一旦狀態變成「待房東簽回」或之後，這個按鈕就會消失，不能再回到編輯畫面。
頁面上方也有「合約總表」連結，可以快速回到委託合約列表。
### 委託合約怎麼建立？（委託合約列表頁「建立委託約」按鈕，需有建立合約權限，可選客製化契約書或紙本簽約） {#jgb/D/entrusted-contract-create-entry}
- phrasings:
  - {text: "委託合約怎麼建立", source: "draft:outline-20260920", status: proposed}
  - {text: "委託合約建立入口", source: "draft:outline-20260920", status: proposed}
- sources: [code:src/pages/entrustedContracts/list/_parts/PageTop.jsx, code:src/components/Lightbox/SelectContractMethod.jsx, code:src/pages/estates/pick/_parts/pick.jsx]
- target_user: [property_manager]
- business_types: [system_provider]
- instance_applicability: general
在委託合約列表頁，如果目前登入身分有建立合約的權限，右上角會出現「建立委託約」按鈕（搜尋結果畫面不會顯示這個按鈕）。
點選「建立委託約」會彈出視窗，可以選擇「電子合約－客製化契約書」或「紙本簽約」兩種方式（委託合約沒有內政部公版電子合約選項）；選好之後會先進入物件挑選頁，選定物件後才進入委託合約編輯畫面繼續填寫。
