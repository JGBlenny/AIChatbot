# D 架草稿（jgb2 master @ b2ee2ac382ce；粗目 10、細目 97、句 246）

讀法：每個粗目底下一條細目答一件事；句子後的〔〕是來源檔（程式或幫助中心頁）；「待查」是文件與程式衝突或程式裡查不到的，未選邊。

## 合約列表與搜尋（10 條；頁：contracts.index、contracts.list、contracts.search）

### 合約列表有哪些狀態頁籤？（待發送合約／待租客簽回／待房東簽名／執行中合約／歷史合約）
- 講法：合約列表有哪些狀態／待租客簽回是什麼意思／合約總表分頁／合約狀態頁籤
- 給誰看：property_manager
- 合約管理的合約總表依進度分成五個頁籤：待發送合約、待租客簽回、待房東簽名、執行中合約、歷史合約。〔src/pages/contracts/list/_parts/PageTop.vue〕
- 網址列的合約狀態代碼只接受 1 到 5，如果代碼不在這個範圍，系統會自動導回沒有篩選狀態的合約總表。〔src/routes/contracts.js〕
- 如果目前登入身分是租客，直接進入代碼 1（待發送合約）頁籤時，系統會把畫面導回登入後的首頁。〔src/routes/contracts.js〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「const allows = ['1', '2', '3', '4', '5']...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'const allows = [\'"\'"\'1\'"\'"\', \'"\'"\'2\'"\'"\', \'"\'"\'3\'"\'"\', \'"\'"\'4\'"\'"\', \'"\'"\'5\'"\'"\']\' master -- src/routes/contracts.js', 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:src/routes/contracts.js）「window.location.href = '/users...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`
- ⚠️ 待查：「登入後的首頁」對應的路由是 users.dashboard；這個路由依角色渲染不同元件（租客走 Tenant.vue，房東／社宅走 Landlord.vue），本細目描述的是租客被導轉後的畫面，但「首頁」這個標籤字串（t('首頁')）只在 Landlord.vue 的麵包屑找到證據，Tenant.vue 本身沒有對應的標題文字，交回裁決是否需要另外查證租客視角的頁面標題。

### 合約列表怎麼搜尋合約？（案名／地址／租客／ID／手機／信箱六種關鍵字，另有進階搜尋）
- 講法：合約怎麼搜尋／合約列表關鍵字搜尋範圍／進階搜尋合約／合約搜尋結果頁面
- 給誰看：property_manager
- 合約列表的關鍵字搜尋可以選擇搜尋範圍，包含案名、地址、租客、ID、手機、信箱六種。〔src/pages/contracts/list/Index.vue〕
- 合約列表也支援進階搜尋，可以用社區、合約類型、是否註冊 JGB 帳號、通知狀態、租期範圍查詢方式、空間類型、租金、面積(坪)等條件篩選。〔src/components/Lightbox/ContractsAdvSearch.vue〕
- 用進階搜尋條件查詢後，畫面標題會顯示成「合約搜尋結果」，這是另一個頁面，跟前面五個狀態頁籤是分開的。〔src/pages/contracts/list/_parts/PageTop.vue〕

### 怎麼建立一份新合約？（合約總表右上角「建立合約」，或物件總表小齒輪選建立合約）
- 講法：怎麼建立合約／合約要去哪裡建立／一個物件可以簽幾份合約／新增合約入口
- 給誰看：property_manager
- 在合約管理的合約總表頁面，點選右上角的「建立合約」按鈕，選取想建立合約的物件並按下一步，即可開始建立合約。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 也可以在物件管理的物件總表中，對想建立合約的物件點選小齒輪，選擇「建立合約」直接進入。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 建立合約時可以選擇「電子合約（公版）」「電子合約（客製化契約書）」或「紙本簽約」三種建立方式。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 一個物件最多可以綁定 10 份合約，例如同一物件的舊租約仍在執行中，也可以先跟新租客預先簽下一份合約，等舊約到期銜接。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

### 物件要先刊登廣告才能建立合約嗎？（現行規則是必填欄位要填齊，不是看刊登狀態）
- 講法：物件要刊登才能建約嗎／沒有上架的物件可以簽約嗎／建立合約的物件條件
- 給誰看：property_manager
- 建立合約前，系統會先檢查該物件的必填欄位是否已經填寫齊全，沒填齊會擋下並提示「請先完善物件所有必填欄位」。〔app/Http/Controllers/ContractController.php〕
- 建立合約的檢查條件曾經改過：早期是看物件「是否已刊登」來決定能不能建立合約，2024/11/13 已經改成看「物件必填資料是否填齊」，以前用刊登狀態當條件的做法目前已經不再套用。〔app/Http/Controllers/ContractController.php〕
- ⚠️ 待查：幫助中心 landlordonboarding04lease_zh-Hant.html FAQ 寫「未刊登的物件代表物件還在編輯中，並不會顯示在公開廣告也無法新增合約」，但 app/Http/Controllers/ContractController.php 顯示 2024/11/13 已將建約條件由『物件已刊登（is_open）』改成『物件必填欄位齊全（isCurrentDataCanCreateContract）』，舊的判斷條件已經停用不再生效。兩者是否等價（欄位填齊是否等同已刊登）未經查證，交回裁決。

### 合約總表列的小齒輪可以做什麼操作？（依合約目前狀態與權限顯示「編輯合約」「刪除合約」「取消簽名」等動作）
- 講法：合約列表小齒輪可以做什麼／合約列表的齒輪按鈕能做什麼
- 給誰看：property_manager
- 合約總表每一列可以點選小齒輪，依合約目前狀態顯示「編輯合約」「刪除合約」「取消簽名」等動作，實際顯示哪些動作要看目前狀態與權限。〔app/Http/Controllers/ContractController.php〕
- ⚠️ 待查：小齒輪動作（編輯合約／刪除合約／取消簽名／取消續約／取消提前解約／點交物件等）在 ContractController.php index() 內依合約狀態組成陣列，本細目只列出最常見的幾種，完整清單依合約狀態、身分、權限而異，未逐一列舉。

### 合約總表可以怎麼排序？（依名稱、更新時間、合約起始日、終止日、成立日，各分新舊／早晚，共 5 種依據）
- 講法：合約列表怎麼排序／合約排序選單
- 給誰看：property_manager
- 合約總表可以用排序選單依名稱、更新時間（新／舊）、合約起始日（早／晚）、合約終止日（早／晚）、合約成立日（早／晚）排序。〔app/Http/Controllers/ContractController.php〕

### 合約總表有哪些欄位？（含團隊自訂的「標籤」欄）
- 講法：合約列表標籤欄／合約總表欄位
- 給誰看：property_manager
- 合約總表有一欄「標籤」，顯示團隊在合約上設定的自訂標籤。〔src/pages/contracts/list/_parts/ListTable.vue〕

### 合約總表的待退押金提示燈號是什麼意思？（合約到期前 30 天才能點退）
- 講法：待退押金提示是什麼／合約列表押金提示燈號
- 給誰看：property_manager
- 如果合約帶有「待退押金」提示燈號，滑鼠移過去會顯示提示文字「合約到期前30天始可點退」。〔src/pages/contracts/list/_parts/stickerLabelBlock.jsx〕

### 合約總表什麼時候會多出「帳單幣別」欄？（只有在批次建立帳單、挑選合約的頁面才會出現，一般檢視沒有這一欄）
- 講法：合約列表帳單幣別欄／帳單幣別什麼時候出現
- 給誰看：property_manager
- 「帳單幣別」不是合約總表固定顯示的欄位；只有在挑選合約進行批次建立帳單的頁面，而且動作確實是批次建立帳單時，才會多出這一欄。〔src/pages/contracts/list/_parts/ListTable.vue〕
- 否定查證：`{'claim': '合約總表一般檢視（非挑選合約頁面）的欄位清單裡不含 CURRENCY／帳單幣別欄', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n 'ContractColumnKey.CURRENCY' master -- src/pages/contracts/list/_parts/ListTable.vue", 'result': '命中 4 筆：欄位定義本體（124-125行）、渲染樣板（571行）、以及 isInPickContractPage 分支下唯一會把它塞進欄位清單的一行 `...(isBillCreateAction ? [ContractColumnKey.CURRENCY] : [])`（219行）；一般總表（非揀選頁、isInPickContractPage 為 false）走的是另一個陣列，四筆命中裡沒有任何一筆出現在那個陣列中', 'positive_control': "同檔 grep -n 'ContractColumnKey.TAGS' 命中 5 筆，其中兩筆分別出現在一般總表陣列（247行）與挑選頁陣列（233行），證明同一種 grep 條件、同一個檔案，確實能在兩個陣列裡都命中，對照之下 CURRENCY 只在挑選頁陣列出現、一般總表陣列完全沒有，不是查詢方式的問題"}`

### 合約總表可以匯出實價登錄資料嗎？（只有在「執行中合約」頁籤、中文站台、且團隊開通此功能時才會出現按鈕）
- 講法：匯出實價登錄資料／合約列表怎麼匯出實價登錄
- 給誰看：property_manager
- 合約總表右上角有「匯出實價登錄資料」按鈕，點下去會開啟一個彈窗，可以匯出符合條件的合約資料，供之後申報實價登錄使用。〔src/pages/contracts/list/_parts/PageTop.vue〕
- 這個按鈕只有在「執行中合約」頁籤、網站語言是中文、而且團隊有開通這個功能時才會顯示；如果篩選結果目前是 0 筆，按鈕會呈現不能點的狀態。〔src/pages/contracts/list/_parts/PageTop.vue〕

## 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款）（21 條；頁：contracts.edit、contracts.edit.tenantInfo、contracts.edit.rentBasic、contracts.edit.rent、contracts.edit.rentAdjustment、contracts.edit.taxAndInvoice、contracts.edit.billSetting、contracts.edit.payment、contracts.edit.facilities、contracts.edit.situation、contracts.edit.dealerBasic、contracts.edit.buildingTranscript、contracts.edit.landlordAttachment、contracts.edit.additionalConvention）

### 建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁）
- 講法：建約有哪些步驟／合約編輯分幾頁／建立合約流程／合約分頁順序
- 給誰看：property_manager
- 建立一般住宅合約的編輯畫面依序分成「承租方資訊」「租賃契約」「點交」「出租方資訊」與「選填」五個分組，合計 14 個分頁。〔src/routes/contracts.js〕
- 「租賃契約」分組底下依序是基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式六個分頁。〔src/routes/contracts.js〕
- 「點交」分組底下是附設傢俱與現況補充兩個分頁；「選填」分組底下是建物謄本、公證、合約附件、補充條款四個分頁。〔src/routes/contracts.js〕
- 分頁旁邊打勾圖示代表必填分頁；租金調幅設定、稅與發票、附設傢俱、現況補充、建物謄本、公證、合約附件、補充條款這 8 頁沒有打勾圖示，屬於選填分頁。〔src/routes/contracts.js〕
- 實際會顯示哪些分頁不是固定的，會依合約範本、物件用途（例如車位）、是否為既存（紙本／DIY）合約等條件動態增減。〔src/use/useEditStore.js〕
- 「租金調幅設定」分頁只有具備特定角色權限的團隊才會顯示；一般團隊看不到這個分頁，實際編輯合約時只會看到 13 個分頁，不是 14 個。〔src/use/useEditStore.js〕
- 否定查證：`{'claim': 'contractRoutes__edit（一般合約 14 個分頁區塊，src/routes/contracts.js 第 218~378 行）裡 checkedIcon: false 有 8 筆、checkedIcon: true 有 6 筆', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 show master:src/routes/contracts.js | sed -n '218,378p' | grep -c 'checkedIcon: false'", 'result': '8 筆', 'positive_control': "同一段範圍 grep -c 'checkedIcon: true' 命中 6 筆，8+6=14 剛好等於分頁總數，可交叉驗證兩者加總沒有漏記"}`
- ⚠️ 待查：「稅與發票」「帳單設定」等其他選填分頁是否也有類似的一般團隊預設不顯示的隱藏規則，本細目未逐一查證每個選填分頁，只確認了租金調幅設定這一項，交回裁決是否需要逐項查證。

### 承租方基本資料怎麼填？（個人／法人租客、租客註冊或免註冊、緊急聯絡人）
- 講法：承租方基本資料怎麼填／租客要註冊帳號才能簽約嗎／法人租客怎麼填／緊急聯絡人
- 給誰看：property_manager
- 「基本資料」分頁用來填寫承租方的簽約資料，可以選擇租客身份是「個人租客」或「法人租客」。〔src/pages/contracts/edit/tenantInfo/Index.jsx〕
- 系統提供「租客註冊」與「租客免註冊」兩種模式：租客註冊代表租客會自己註冊 JGB 會員並填妥承租方資訊；租客免註冊代表租客不需要註冊會員，改由管理者代為填寫承租方資訊。〔src/pages/contracts/edit/tenantInfo/Index.jsx〕
- 這個分頁也可以新增租客的緊急聯絡人，填寫姓名、關係與聯絡號碼。〔src/pages/contracts/edit/tenantInfo/Index.jsx〕
- 分頁上會提示，這裡填寫的租客資料會謄寫進合約內容，過程經過加密處理。〔src/pages/contracts/edit/tenantInfo/Index.jsx〕

### 「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期）
- 講法：合約範本怎麼選／合約起迄日期怎麼設定／租賃訂約日期是什麼／合約範本有哪幾種
- 給誰看：property_manager
- 「基本條件」分頁要先選擇「合約類型」與「合約範本」，決定這份合約要用哪一種定型化契約內容。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 分頁上要設定「合約起迄日期」，也就是這份合約的租期起訖。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 另外還有「租賃訂約日期」欄位，用來記錄雙方實際簽訂這份合約的日期，跟合約起迄日期是不同的欄位。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 一般團隊建立一般住宅合約時，可選的合約範本共有 12 種：「114年內政部住宅租賃契約(原房東)」「113年內政部轉租契約(包租轉租)」「代租代管契約(參考114年租賃契約)」「內政部英文版 租賃契約書 原房東」「內政部英文版 租賃契約書 包租業」「內政部英文版 租賃契約書 代租代管」「英越文版 租賃契約書」「英泰文版 租賃契約書 原房東」「英泰文版 租賃契約書 代租代管」「公會中文版 租賃契約書 原房東」「公會中文版 租賃契約書 包租業」「公會中文版 租賃契約書 代租代管」。〔app/Http/Controllers/ContractController.php〕
- 如果登入身分是個人房東角色，可選範本會縮減成 4 種：「114年內政部住宅租賃契約(原房東)」「內政部英文版 租賃契約書 原房東」「英泰文版 租賃契約書 原房東」「公會中文版 租賃契約書 原房東」。〔app/Http/Controllers/ContractController.php〕
- ⚠️ 待查：幫助中心 landlordonboarding04lease_zh-Hant.html 說「內政部所規範的五種合約範本」（且列舉的是原房東中文版／包租業中文版／代租代管中文版／英文版／英越文版共 5 個名目），但程式（app/Http/Controllers/ContractController.php 的範本組裝邏輯＋config/contract.php 的範本標籤）顯示一般團隊實際可選 12 種、個人房東身分可選 4 種，兩者皆非 5 種；文件與程式衝突，交回裁決以何者為準。

### 「基本條件」分頁的繳費週期與帳單週期制度怎麼設定？（繳費週期／繳費截止日、當月分算或跨月計算、分算日）
- 講法：繳費週期怎麼設定／繳費截止日是什麼／跨月計算跟當月分算差在哪／帳單週期分算日
- 給誰看：property_manager
- 「基本條件」分頁要設定「繳費週期」，決定多久要繳一次款項。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 同時要設定「繳費截止日」，也就是每期帳單的繳款期限。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 帳單週期制度分成「當月分算」與「跨月計算」兩種計費方式，會影響租期不足一個完整週期時金額怎麼分攤。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 選擇跨月計算時，還要設定「帳單週期分算日」。〔src/pages/contracts/edit/rentBasic/General.vue〕

### 「基本條件」分頁的遲繳滯納金怎麼計算？（僅新北住都角色群組可見，兩段比例＋拖欠天數門檻，欄位唯讀）
- 講法：滯納金怎麼設定／遲繳滯納金計算方式／滯納金比例跟拖欠天數
- 給誰看：property_manager
- 「遲繳滯納金」設定只出現在新北住都角色群組的合約上；租客超過繳費期限還沒繳款，會先產生第一筆比例的滯納金，如果拖欠超過設定的天數門檻，還會再產生第二筆同比例的滯納金。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 滯納金的比例（X）跟拖欠天數門檻（Y）兩個欄位在合約編輯畫面上是唯讀的，不能在合約上直接修改；這兩個數值是這份合約自己的一筆設定紀錄，第一次需要用到時會用系統預設值（2%、30 天）自動建立，之後就固定在這份合約上，不會因為系統預設值以後改變而跟著變動。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 否定查證：`{'claim': '滯納金設定不是用一支「取得團隊層級設定」的方法讀出來的（app/ 底下找不到任何 amercement 相關的 getSettings 呼叫）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -in amercement master -- app/ | grep -i getSettings', 'result': '0 筆', 'positive_control': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c "getSettings(" master -- app/Http/Controllers/ContractController.php 命中 4 筆，證明 getSettings( 這個查詢字串本身有效、grep 條件沒問題，只是滯納金真的不是走這支方法'}`

### 「基本條件」分頁的租客慣用語系是什麼？（決定系統產生給租客的合約文件語系）
- 講法：租客慣用語系是什麼／合約文件語系怎麼選
- 給誰看：property_manager
- 「租客慣用語系」欄位要選租客習慣使用的語系，之後透過 JGB 系統產生給租客的相關合約文件，都會以這個語系為主。〔src/pages/contracts/edit/rentBasic/General.vue〕

### 合約的「可否提前解約」與違約金怎麼設定？（每月租金／固定金額／詳參補充條款／其他四種算法）
- 講法：提前解約違約金怎麼算／合約可否提前解約設定／違約金計算方式／解約通知天數
- 給誰看：property_manager
- 「基本條件」分頁要設定租客是否可以提前解約，選項是「可以」或「不可以」。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 選擇可以提前解約時，要再選違約金計算方式：「每月租金」「固定金額」「詳參後文補充條款」，既存（上傳）合約另外多一個「其他」選項可以自訂文字說明（最多 30 個字元）。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 選「每月租金」或「固定金額」時，畫面上會提示依內政部函釋：一方未先期通知逕行終止租約，賠償他方的違約金最高不得超過一個月租金額。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 選「每月租金」時，系統會依租客通知房東的天數門檻分兩段計算，達到門檻天數（含）以上通知的違約金月數，跟少於門檻天數通知的違約金月數，可以分別設定不同月數。〔src/pages/contracts/edit/rentBasic/General.vue〕

### 租金費用分頁要設定什麼？（租金、押金、自訂收入／支出費用、租金優惠、繳費週期優惠）
- 講法：租金費用怎麼設定／押金上限／自訂費用收入支出／繳費週期優惠／租金優惠跟繳費週期優惠差在哪
- 給誰看：property_manager
- 「租金費用」分頁用來設定租金、押金、生活費用以及自訂費用等收費項目。〔src/pages/contracts/edit/rent/Index.jsx〕
- 押金欄位下方會顯示提示文字：根據內政部租賃住宅市場發展及管理條例規定，一般租賃契約押金額度最高不得超過兩個月租金。〔src/pages/contracts/edit/rent/Index.jsx〕
- 自訂費用分成「收入」與「支出」兩種性質：收入類是向對方收取的款項，支出類是向對方付款的款項，折抵、折扣也算在支出類。〔src/pages/contracts/edit/billSetting/Index.jsx〕
- 這個分頁還可以設定「租金優惠」，但這個欄位只對統上、新北住都、新北住都停車場這幾個特殊角色群組顯示，一般團隊看不到這個設定。〔src/pages/contracts/edit/rent/Index.jsx〕
- 「租金優惠」底下還有一個「繳費週期優惠」子選項（例如年繳、半年繳、季繳），只有統上這一個角色群組才會顯示；新北住都、新北住都停車場即使能看到租金優惠，也看不到繳費週期優惠。選擇繳費週期優惠後會連動變更「基本條件」分頁的繳費週期設定。〔src/pages/contracts/edit/rent/Index.jsx〕
- 否定查證：`{'claim': '「租金優惠」欄位一般團隊看不到，只對統上／新北住都／新北住都停車場顯示', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "\'租金優惠\'" master -- src/pages/contracts/edit/rent/Index.jsx', 'result': '命中 1 筆，緊接的判斷式為 (state.isTongSang || state.isNthurc || state.isNthurcParking) && <div ...>，一般團隊（三者皆非）不會進入這個分支', 'positive_control': '同檔「租金」「押金」等一般欄位無此角色判斷式包裹，一般團隊可見，兩者對照可證明此區塊是額外的角色限制而非全域顯示'}`
- 否定查證：`{'claim': '「繳費週期優惠」子選項只對統上顯示，比「租金優惠」的角色條件更窄（不含新北住都／新北住都停車場）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "\'繳費週期優惠\'" master -- src/pages/contracts/edit/rent/Index.jsx', 'result': '命中 2 筆（欄位標籤與已選優惠後顯示的折扣文字各一筆），標籤那筆往上兩行是 state.isTongSang && <div>，只用 isTongSang 單一角色判斷，不含 isNthurc / isNthurcParking', 'positive_control': '同檔上一層「租金優惠」判斷式為 (state.isTongSang || state.isNthurc || state.isNthurcParking)，跟「繳費週期優惠」的單一 isTongSang 判斷式對照，可證明後者角色條件確實更窄，不是筆誤漏抄'}`

### 押金有哪幾種設定方式？（每月租金倍數／固定金額兩種計算基準）
- 講法：押金怎麼算／押金計算基準
- 給誰看：property_manager
- 押金的計算基準有兩種：「每月租金」（依月租金倍數計算）或「固定金額」（直接輸入金額），可以在「租金費用」分頁切換。〔src/pages/contracts/edit/rent/Index.jsx〕

### 租金調幅設定分頁在做什麼？（依繳費期數設定固定金額或百分比調漲／調降）
- 講法：租金調幅怎麼設定／租金逐年調漲／分期調整租金／租金調幅方式
- 給誰看：property_manager
- 「租金調幅設定」分頁可以針對合約每一期繳費週期，分別設定主租金或自訂租金項目的調幅。〔src/pages/contracts/edit/rentAdjustment/Index.vue〕
- 調幅方式有五種：無調幅、固定租金調幅(+)、固定金額優惠(-)、百分比調幅(+)、百分比優惠(-)。〔src/pages/contracts/edit/rentAdjustment/Index.vue〕
- 可以用「批次設定調幅」一次套用到全部或指定的租金項目，也可以在下方表格對每一期單獨設定。〔src/pages/contracts/edit/rentAdjustment/Index.vue〕
- 這個分頁要先在「基本條件」設定好合約起迄日期、繳費週期及帳單週期制度，才能列出各期的調幅設定列。〔src/pages/contracts/edit/rentAdjustment/Index.vue〕
- 這個分頁只有具備特定角色權限的團隊才會顯示；一般團隊的合約編輯畫面裡沒有「租金調幅設定」這個分頁可以填。〔src/use/useEditStore.js〕
- 否定查證：`{'claim': '一般團隊（不具備特定角色權限）的合約編輯畫面裡看不到「租金調幅設定」這個分頁', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c "specialRoles.currentSpecialRole.includes(\'rentAdjustment\')" master -- src/use/useEditStore.js', 'result': "命中 1 筆，緊接的判斷式是 if (!specialRoles.currentSpecialRole.includes('rentAdjustment')){ myRoutes = myRoutes.filter((node)=>node.name !== 'contracts.edit.rentAdjustment') }，不具備該角色的團隊會被過濾掉這個分頁", 'positive_control': '同檔 grep -c "label: \'租金調幅設定\'" 在 src/routes/contracts.js 命中 1 筆，證明這個分頁本身確實存在於路由設定裡、不是查詢範圍錯誤，只是會被上述判斷式動態過濾掉'}`

### 稅與發票分頁怎麼設定？（是否開立發票、應稅品項、目前只支援租金品項開發票）
- 講法：合約發票怎麼設定／租金以外可以開發票嗎／應稅品項設定／統一編號要不要打
- 給誰看：property_manager
- 「稅與發票」分頁要先設定這份合約的帳單是否要開立發票。〔src/pages/contracts/edit/taxAndInvoice/index.jsx〕
- 選擇開立發票後，要設定出租方統一編號，以及發票是否要打承租方的統一編號。〔src/pages/contracts/edit/taxAndInvoice/index.jsx〕
- 這個分頁可以逐項設定「應稅品項」是否應稅，但畫面上會提示 JGB 目前僅提供租金品項開立發票服務，其他品項的發票支援持續增加中。〔src/pages/contracts/edit/taxAndInvoice/index.jsx〕
- 如果目前沒有任何品項會開立發票，畫面會提示應該把「帳單是否開立發票」改為「否」，不然帳單不會有發票金額。〔src/pages/contracts/edit/taxAndInvoice/index.jsx〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「t('目前這份合約沒有任何品項會開立發票，帳單不會有發票金額。若確定不需要發票，...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'t(\'"\'"\'目前這份合約沒有任何品項會開立發票，帳單不會有發票金額。若確定不需要發票，建議把上方「帳單是否開立發票」改為「否」。\'"\'"\')\' master -- src/pages/contracts/edit/taxAndInvoice/index.jsx', 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（code:src/pages/contracts/edit/taxAndInvoice/index.jsx）「<h5 class="mb-2">{ t(\'帳單是否開立發票...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`

### 帳單設定分頁在做什麼？（預先編輯未來帳單的標題、金額、週期與自動執行動作）
- 講法：帳單設定分頁怎麼用／可以先編輯未來帳單嗎／帳單期間跟租期不一樣／帳單自動執行動作
- 給誰看：property_manager
- 「帳單設定」分頁可以預先編輯這份合約未來衍生的每一張帳單，包括標題、繳費期限、帳單週期、金額、細項、備註，以及成立後的自動執行動作。〔src/pages/contracts/edit/billSetting/Index.jsx〕
- 如果某張帳單的自動執行動作選擇「已到帳」，代表合約成立時這張帳單會直接被視為已到帳。〔src/pages/contracts/edit/billSetting/Index.jsx〕
- 如果帳單設定的期間跟合約租期對不起來，畫面會出現警示，寄送合約邀請時會被系統擋下，需要重新產生帳單表或逐期調整日期，直到跟合約租期一致才能正常送出邀請。〔src/pages/contracts/edit/billSetting/Index.jsx〕
- 帳單狀態分成草稿、應到帳／應支出、已到帳／已支出、封存四種。〔src/pages/contracts/edit/billSetting/Index.jsx〕
- 「帳單設定」分頁在新北住都、新北住都停車場、統上這幾個角色群組會被拿掉、暫不開放使用；這是新北住都個案的暫時處理，等新北住都確認需求後才會恢復顯示。〔src/use/useEditStore.js〕

### 合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種）
- 講法：收款方式有哪些／怎麼設定收租金方式／固定虛擬帳號收租／現金收款帳戶
- 給誰看：property_manager
- 「收款方式」分頁讓房東指定租客要用哪種方式支付款項，選項有「線上金流」「現金收款」「固定虛擬帳號」三種，但不是每個團隊都看得到全部三種。〔src/pages/contracts/edit/payment/General.vue〕
- 「線上金流」只有在使用者國別是台灣、且合約範本不是 Meta Capital 系列時才會顯示這個選項。〔src/pages/contracts/edit/payment/General.vue〕
- 「固定虛擬帳號」只有具備特定特殊角色權限的團隊才會顯示這個選項。〔src/pages/contracts/edit/payment/General.vue〕
- 選擇「現金收款」可以指定收款銀行帳戶，填寫銀行代碼、銀行名稱、帳戶名稱、銀行帳號等資料，也可以把常用帳號加入清單方便下次選用。〔src/pages/contracts/edit/payment/General.vue〕
- 「加入常用帳號」按鈕只有具備編輯角色（收款設定相關）權限的成員才會顯示，權限不足的成員在這個分頁看不到這個按鈕。〔src/pages/contracts/edit/payment/General.vue〕
- 否定查證：`{'claim': '沒有編輯角色（收款設定相關）權限的成員，在「收款方式」分頁看不到「加入常用帳號」按鈕', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "v-if=\\"store.state.userData.permission?.edit_role\\"" master -- src/pages/contracts/edit/payment/General.vue', 'result': '命中 1 筆，緊接著是「加入常用帳號」按鈕本體，沒有 edit_role 權限時整個按鈕不會渲染', 'positive_control': '同檔 grep -n "t(\'加入常用帳號\')" 命中 1 筆，證明按鈕文字本身確實存在於檔案裡，只是外層包了權限判斷式'}`

### 附設傢俱分頁在做什麼？（設定家具責任歸屬，簽約後會帶入點交清單）
- 講法：附設傢俱怎麼填／家具修繕責任歸屬／點交清單怎麼來的
- 給誰看：property_manager
- 「附設傢俱」分頁用來勾選租屋處提供的家具、家電，並可以設定每一項的修繕責任歸屬方；也可以從物件資料或其他合約複製資料進來。〔src/pages/contracts/edit/facilities/General.vue〕
- 分頁上提示：依照合約設定，所有品項預設由出租方負責修繕，也可以勾選特定項目改由承租方負責，但如果是承租方刻意損壞，仍要由承租方自行負擔責任。〔src/pages/contracts/edit/facilities/General.vue〕
- 簽約完成後，這個分頁勾選、標註的家具傢俱項目，都會自動帶入之後的點交清單。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

### 現況補充分頁要寫什麼？（車位、屋況、漏水處等內政部規範現況細節）
- 講法：現況補充要寫什麼／非自然死亡揭露
- 給誰看：property_manager
- 「現況補充」分頁可以紀錄車位、屋況、漏水處等現況細節，包括建物出租型態、是否曾發生非自然死亡等內政部規範的項目。〔src/pages/contracts/edit/situation/General.vue〕

### 出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、電子簽名圖章）
- 講法：出租方基本資料怎麼填／經理人資訊怎麼設定／電子簽名圖章／團隊資料自動帶入
- 給誰看：property_manager
- 「出租方基本資料」分頁如果是個人房東，需要填妥電話、Email、身分證字號、戶籍地址、通訊地址。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 如果是用團隊方式建立合約，出租方資料（公司登記名稱、統一編號、電話、Email、公司登記地址、公司通訊地址）會自動帶入先前團隊資訊填寫的內容，需要修改的話要回到「團隊資訊」編輯。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 填妥出租方資料後，要在「經理人資訊」選擇這份合約由團隊中哪一位經理人負責管理。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 分頁最下方可以選擇新增電子簽名圖章取代手動簽名；如果先前沒有上傳過電子圖章，需要先到「團隊資訊」設定才能使用這個功能。〔src/pages/contracts/edit/dealerBasic/Index.vue〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「t('使用電子簽名圖章取代親手簽名')...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'t(\'"\'"\'使用電子簽名圖章取代親手簽名\'"\'"\')\' master -- src/pages/contracts/edit/dealerBasic/Index.vue', 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（help:landlordonboarding04lease_zh-Hant.html）「此處如果您是個人房東，你需要填妥電話、Email、身分證字號...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`

### 建物謄本分頁是選填的嗎？（選填，僅供合約內容完備使用，不會顯示在廣告頁）
- 講法：建物謄本要填嗎／謄本資訊會公開嗎／建物謄本是選填的嗎
- 給誰看：property_manager
- 「建物謄本」分頁是選填分頁，用來補充建物的謄本資訊，讓合約內容更完備。〔src/routes/contracts.js〕
- 這個分頁的資訊只是為了合約內容完備，並不會刊登在物件的網頁廣告上，可以放心填寫。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕
- 否定查證：`{'claim': '建物謄本分頁登記的段/小段/地號等欄位不會顯示在物件的公開廣告頁（estate/show 頁面）', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -in '地號\\|土地標的清冊\\|建物謄本' master -- 'src/pages/estates/show/**'", 'result': '0 筆', 'positive_control': '同範圍 grep -c 租金 master -- src/pages/estates/show/_parts/FeesTable.vue 命中 2 筆，證明該公開頁面元件讀得到內容、grep 條件有效'}`
- ⚠️ 待查：「不會刊登在網頁廣告上」的原句出自社宅合約教學頁對物件建立步驟中的建物謄本欄位，用在一般合約「建立與編輯」分頁的建物謄本（buildingTranscript/General.vue）上屬同名同性質欄位的合理外推，未直接對到一般合約分頁的說明文字，列此供覆核。

### 合約附件分頁能上傳什麼？（各類文件圖片或 PDF，最大 10MB）
- 講法：合約附件可以放什麼／附件檔案大小限制／合約附件格式
- 給誰看：property_manager
- 「合約附件」分頁（一般團隊）可以上傳授權代理人簽約同意書、建物所有權/有權出租之證明文件、使用執照影本、出租方同意轉租確認書、房屋位置格局示意圖、社區管理規約/住戶生活規約等文件，也有「其他」項目可以上傳附註條款、稅籍證明等。〔src/pages/contracts/edit/landlordAttachment/Index.vue〕
- 分頁提示圖片僅支援 JPG、PNG、PDF 檔，檔案大小最大 10MB，每個項目限制的上傳檔案數量不同。〔src/pages/contracts/edit/landlordAttachment/Index.vue〕
- 上傳這些附件的目的是為了避免日後爭議，屬於選填分頁。〔src/pages/contracts/edit/landlordAttachment/Index.vue〕
- 「估價師租金簽註意見書」這個勾選項目只出現在社宅合約的分頁裡，一般合約的合約附件清單並不包含這一項。〔src/pages/contracts/edit/landlordAttachment/Index.vue〕
- 否定查證：`{'claim': '一般合約（attachmentRowOptionsGeneral）的合約附件清單裡沒有「估價師租金簽註意見書」這一項', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "估價師租金簽註意見書" master -- src/pages/contracts/edit/landlordAttachment/Index.vue', 'result': '命中 1 筆（第 620 行），位於 <template v-if="editStore.options.property_purpose_key === 2"> 區塊內（社宅專用），不在 attachmentRowOptionsGeneral 定義範圍', 'positive_control': '同檔 attachmentRowOptionsGeneral 物件裡的 attachment_user_agent_signing_consent／attachment_user_others 等 7 個 key 皆可 grep 到且不受此 v-if 限制，可與此項目對照出「有出現在程式裡」但「不在一般清單」的差異'}`

### 補充條款有字數限制嗎？（最多 50 行、每行 50 字，可套用範本與複製其他合約）
- 講法：補充條款字數限制／補充條款最多幾行／合約條款寫不下怎麼辦／補充條款範本
- 給誰看：property_manager
- 「補充條款」分頁最多可以寫 50 行，每行限制 50 個字。〔src/utils/constants/contract.js〕
- 補充條款是因為系統的電子合約使用政府提供的公版定型化契約，如果需要補充其他合約條款，可以在這裡描述，系統會自動把條款內容帶入合約當中。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 如果內容超過 50 行限制，建議另外寫成文字檔或圖片檔，改放在「合約附件」的「其他」項目上傳。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 這個分頁也提供「預設補充條款」範本可以套用，或是選擇「複製現有合約資料」把其他合約已填寫的補充條款複製過來。〔src/pages/contracts/edit/additionalConvention/Index.vue〕
- 否定查證：`{'claim': 'additionConventionLimit.textPerLine 是每行 50 字，不是幫助中心說的其他數字', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n 'textPerLine' master -- src/utils/constants/contract.js", 'result': 'textPerLine: 50 // 每行最多幾個字 —— 命中 1 筆，數值為 50，與句子一致', 'positive_control': '同檔 termLines 命中 1 筆，數值為 50，兩個限制數字皆可在同一檔案 grep 到，非誤植'}`
- ⚠️ 待查：src/pages/contracts/edit/additionalConvention/Index.vue 另外還有一句提示「補充條款至多僅限 1 頁 A4 內容，請務必執行「預覽結果」以確認最終呈現。」，跟本細目已收錄的「最多 50 行、每行 50 字」是不同的限制描述（前者是排版後的頁數提示，後者是輸入框的字元數上限），兩者可能同時成立（字數在上限內仍可能因排版超過 1 頁），交回裁決是否要在正本中一併說明兩種限制描述的關係。

### 合約編輯分頁會依什麼條件增減？（紙本／DIY 合約、車位、Meta Capital 範本、稅務發票資格皆會影響）
- 講法：合約分頁為什麼變少／紙本合約有哪些分頁／車位合約分頁
- 給誰看：property_manager
- 如果這份合約是「上傳既有（紙本）」合約，可用分頁不會被縮減，跟一般團隊建立一般住宅合約時看到的整組分頁完全一樣（基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、公證、合約附件、補充條款）。〔src/use/useEditStore.js〕
- 如果合約範本選擇 Meta Capital 系列，「公證」分頁會被拿掉，因為 Meta Capital 不支援公證。〔src/use/useEditStore.js〕
- 如果物件用途是車位，可用分頁會被限縮成更小的子集；只有具備特定角色權限的團隊，車位合約才會額外顯示「稅與發票」分頁。〔src/use/useEditStore.js〕
- 「稅與發票」分頁只有在團隊具備自動開立發票資格時才會顯示。〔src/use/useEditStore.js〕
- 如果這份合約是「上傳既有（DIY）」自訂範本合約，可用分頁比一般團隊的整組少一項：不會出現「租金調幅設定」分頁，其餘分頁不變。〔src/use/useEditStore.js〕
- 另外還有兩條不需要任何前置條件、對所有合約都生效的過濾規則：「租金調幅設定」分頁只有具備特定角色權限的團隊才顯示；「帳單設定」分頁則是統上、新北住都、新北住都停車場這幾個角色群組看不到（這是新北住都個案的暫時處理，等新北住都確認需求後才會恢復顯示）。〔src/use/useEditStore.js〕
- 否定查證：`{'claim': '紙本（paper）過濾白名單與一般團隊（general）完整分頁清單，兩份清單所含的分頁名稱集合完全相同（沒有任何一個分頁被紙本過濾拿掉）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "is_existed === ContractIsExisted.paper" master -- src/use/useEditStore.js', 'result': '命中 1 筆，緊接的白名單陣列列出 14 個分頁名稱，逐一比對 src/routes/contracts.js 的 contractRoutes__edit 陣列（14 筆），兩邊的 name 集合完全一致', 'positive_control': '同檔 grep -n "is_existed === ContractIsExisted.diy" 命中 1 筆，緊接的白名單陣列只有 13 個分頁名稱、缺少 contracts.edit.rentAdjustment，證明兩個白名單陣列讀取方式一致、只是內容確實不同，不是查詢路徑錯誤'}`

### 「建物謄本」分頁什麼時候不會顯示？（只有選中／未選合約範本時才顯示，選到英越文或泰文版就會被拿掉）
- 講法：建物謄本分頁不見了／什麼時候沒有建物謄本
- 給誰看：property_manager
- 一般住宅合約的「建物謄本」分頁只有在還沒選合約範本，或是選到「114年內政部住宅租賃契約(原房東)」「113年內政部轉租契約(包租轉租)」「代租代管契約(參考114年租賃契約)」這三種公版、或對應的公會中文版這三種時才會顯示；選到英文版、英越文版、英泰文版等其他範本時，這個分頁不會出現。〔src/use/useEditStore.js〕
- 否定查證：`{'claim': '英泰文版範本（th_th_individual／th_th_management）不在讓「建物謄本」分頁顯示的白名單裡', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c 'th_th_individual' master -- src/use/useEditStore.js", 'result': '0 筆', 'positive_control': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c 'tw_zh_individual_union' master -- src/use/useEditStore.js 命中 1 筆，證明同一支檔案、同樣的查詢方式讀得到內容，只是 th_th_individual 真的不在這份白名單裡"}`

## 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般）（19 條；頁：contracts.edit.socialHousing.attachments、contracts.edit.socialHousing.buildingTranscript、contracts.edit.socialHousing.dealerBasic、contracts.edit.socialHousing.facilities、contracts.edit.socialHousing.landlordAttachment、contracts.edit.socialHousing.landlordBasic、contracts.edit.socialHousing.landlordLicense、contracts.edit.socialHousing.moveIn、contracts.edit.socialHousing.payment、contracts.edit.socialHousing.photos、contracts.edit.socialHousing.publicNotary、contracts.edit.socialHousing.rent、contracts.edit.socialHousing.rentBasic、contracts.edit.socialHousing.situation、contracts.edit.socialHousing.subsidyTerms、contracts.edit.socialHousing.tenantAttachment、contracts.edit.socialHousing.tenantBasic、contracts.edit.socialHousing.tenantHousehold、contracts.edit.socialHousing.tenantLicense）

### 社宅合約「建物標的」分組有哪些分頁？（建物細節、現況補充、現況照片、附設傢俱四個分頁）
- 講法：社宅合約建物標的怎麼填／建物細節填錯怎麼改
- 給誰看：property_manager
- 社宅合約的「建物標的」分組包含建物細節（建物資訊／建物謄本）、現況補充、現況照片、附設傢俱四個分頁。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕
- 建物細節分頁主要呈現物件建立時填寫的資料，如果資料有誤，需要回到物件編輯修改，不能直接在合約分頁改。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕
- ⚠️ 待查：幫助中心只列出「現況補充」為建物標的分組下的一個分頁名稱，沒有針對這個分頁本身的欄位/規則另外撰寫說明文字，本細目暫未補上該分頁的細節內容，交回裁決是否需要另外查證。

### 社宅合約「現況照片」分頁一定要上傳嗎？（部分照片為必填，用來證明社宅內部現況設備存在）
- 講法：現況照片一定要上傳嗎／社宅照片認證
- 給誰看：property_manager
- 現況照片分頁提醒部分現況照片為必填，因為要證明社宅內部現況確實有該項設備，未來需要提供給公會進行認證。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「附設傢俱」分頁要填什麼？（各格局家具與數量）
- 講法：社宅附設傢俱／社宅傢俱數量怎麼填
- 給誰看：property_manager
- 附設傢俱分頁要填入物件內部各格局的家具與數量。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「基本條件」要填什麼？（合約範本、委託期間、住宅現況、物件返還狀態、代收定金、爭議處理）
- 講法：社宅合約基本條件／委託租賃期間是什麼／物件返還狀態怎麼設定／代收定金幾日內轉交
- 給誰看：property_manager
- 社宅合約的「基本條件」分頁除了合約範本、合約起迄日，還要設定「委託租賃期間」或「委託管理期間」，也就是業者受託管理這個物件的期間。〔src/pages/contracts/edit/rentBasic/SocialHousing.vue〕
- 這個分頁要設定「住宅現況」，例如是否為既存租賃契約住宅（帶租約住宅）、住宅所有權人自行使用或現為空屋無人使用等狀態。〔src/pages/contracts/edit/rentBasic/SocialHousing.vue〕
- 「物件返還狀態」要設定租客返還物件時室內裝潢應回復的狀況，選項包含現況返還、回復原狀等。〔src/pages/contracts/edit/rentBasic/SocialHousing.vue〕
- 如果業者會代收定金，這個分頁要設定業者收到定金後應於幾日內將租金轉交給原房東；另外還要設定張貼租賃廣告、修繕聯絡方式、爭議處理（如是否依仲裁法規定進行仲裁）等項目。〔src/pages/contracts/edit/rentBasic/SocialHousing.vue〕

### 社宅合約的提前解約說明文字跟一般合約不同（只顯示少於預告天數需付違約金的情境，沒有達門檻天數的減免說明）
- 講法：社宅合約提前解約說明／社宅違約金跟一般合約一樣嗎
- 給誰看：property_manager
- 一般住宅合約在違約金計算方式選「每月租金」時，畫面會分別列出「達到預告天數（含）以上通知」與「少於預告天數通知」兩種情境各自的違約金月數。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 但如果合約範本選擇新北住都社宅專用範本，畫面只會顯示「少於預告天數通知，需支付違約金」的情境，不會出現達到天數即可減免的那一句。〔src/pages/contracts/edit/rentBasic/General.vue〕
- 否定查證：`{'claim': '句子引用的畫面/程式文字「v-if="editStore.form.contract_template_s...」確實逐字存在於來源檔案（句子本身即引用該字串）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'v-if="editStore.form.contract_template_selected !== \'"\'"\'nthurc_social_housing\'"\'"\'"\' master -- src/pages/contracts/edit/rentBasic/General.vue', 'result': '3 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:src/pages/contracts/edit/rentBasic/General.vue）「t('租客若於 [s1] 天(含)以上通知房東，需支付 [s...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`

### 社宅合約「租金費用」分頁要填什麼？（代租金額／租金與押金／生活費用）
- 講法：社宅租金費用怎麼填／社宅代租金額怎麼設定
- 給誰看：property_manager
- 社宅合約的「租金費用」分頁要設定代租金額、租金與押金、生活費用等項目。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「收款方式」怎麼設定？（轉帳、票據、現金三種，收款人可選原房東或業者）
- 講法：社宅收款方式／收款人是誰
- 給誰看：property_manager
- 社宅合約的「收款方式」跟一般合約不同，選項是「轉帳」「票據」「現金」三種。〔src/pages/contracts/edit/payment/SocialHousing.vue〕
- 收款方式分頁還要設定「收款人」是「原房東」還是「業者」本身，反映包租、代管兩種委託型態下實際收款對象不同。〔src/pages/contracts/edit/payment/SocialHousing.vue〕

### 社宅合約一定要公證嗎？（預設應辦理公證，可填理由不辦但視同放棄公證費補助；辦理公證後需下載文件紙本簽署再上傳歸檔）
- 講法：社宅合約一定要公證嗎／公證費由誰負擔／社宅簽約流程／公證後怎麼上傳
- 給誰看：property_manager
- 社宅合約的「公證」分頁預設文字是：本租賃契約應辦理公證，但租賃雙方如果因特定事由同意不辦理公證，視同自願放棄公證費申請的權益。〔src/pages/contracts/edit/publicNotary/SocialHousing.vue〕
- 這個分頁可以設定公證是否強制執行特定事項、保證人效力，以及公證產生的額外稅費由誰負擔（例如平均分擔）。〔src/pages/contracts/edit/publicNotary/SocialHousing.vue〕
- 填完所有分頁內容後，可以點選「預覽合約」，再點「下載合約文件」，依文件進行紙本簽約與公證。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕
- 完成公證後，需要把掃描好的合約 PDF 檔上傳，並選擇是否要綁定租客後送出，才能完成歸檔；因為公證目前是必要程序，社宅合約無法只在線上就完成簽約。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕
- 如果選擇不辦理公證，需要在「不辦理公證理由」欄位填寫理由，這個欄位最多只能輸入 100 個字元。〔src/pages/contracts/edit/publicNotary/SocialHousing.vue〕
- 否定查證：`{'claim': '句子引用的幫助中心文字「目前社會住宅因「公證」是必要的程序，故無法於線上即完成簽約...」確實逐字存在於該頁面', 'grep': "grep -cF '目前社會住宅因「公證」是必要的程序，故無法於線上即完成簽約' /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/Landlordonboarding09Socialhousing_zh-Hant.html", 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（code:src/pages/contracts/edit/publicNotary/SocialHousing.vue）grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`
- ⚠️ 待查：幫助中心 Landlordonboarding09Socialhousing_zh-Hant.html 說「公證是必要的程序，故無法於線上即完成簽約」，但 src/pages/contracts/edit/publicNotary/SocialHousing.vue 有 t('不辦理公證理由') 欄位，文案也寫「租賃雙方因以下事由同意不辦理公證者，視同自願放棄公證費申請之權益」，顯示程式上其實存在『同意不辦理公證』的路徑（代價是放棄公證費補助），跟幫助中心『必要程序、無法線上完成』的說法不完全一致，交回裁決是否已過期或屬於例外選項。

### 社宅合約「合約附件」要準備什麼？（測量成果圖、稅籍證明等，出租方與承租方各自也有附件上傳分頁）
- 講法：社宅合約附件要準備什麼／出租方承租方附件上傳
- 給誰看：property_manager
- 社宅合約的「合約附件」分頁要上傳測量成果圖、稅籍證明等文件；出租方與承租方各自也有獨立的「附件」分頁。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「補助申請」分頁在做什麼？（配合社宅包租代管 333 補貼政策，出租方三種稅費減免）
- 講法：社宅333補貼政策／社宅補助申請怎麼填
- 給誰看：property_manager
- 「補助申請」分組主要配合政府的社會住宅包租代管 333 補貼政策：出租方有房屋稅、地價稅、租金所得稅三種稅費減免，承租方有公證費、修繕費、居家安全相關保險費三項費用補助，業者則有仲介費、代管費由政府全額補助的三年免費專業服務。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕
- 補助申請分頁要填寫補助費用申請日期、住宅出租修繕費、公證費、承租人租金補助等條件。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「出租方」分組有哪些分頁？（基本資料、授權、附件三個分頁）
- 講法：社宅出租方分頁有哪些／社宅出租方基本資料授權附件
- 給誰看：property_manager
- 社宅合約「出租方」分組包含基本資料、授權、附件三個分頁。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「授權」分頁要確認什麼？（合法建物條件、同意提供住宅、同意轉租等授權事項）
- 講法：合法建物條件／出租方授權項目
- 給誰看：property_manager
- 「授權」分頁要確認合法建物條件，例如主要用途登記含有「住」「住宅」「農舍」「套房」「公寓」或「住宿」字樣，或提出合法房屋證明等文件。〔src/pages/contracts/edit/landlordLicense/Index.vue〕
- 「授權」分頁也要設定出租人是否同意提供住宅、是否同意出租予租屋服務事業再轉租（包租包管）等授權事項。〔src/pages/contracts/edit/landlordLicense/Index.vue〕

### 社宅合約「承租方」分組有哪些分頁？（基本資料、家庭＆財產、授權、附件）
- 講法：社宅承租方分頁有哪些／社宅承租方基本資料家庭授權附件
- 給誰看：property_manager
- 社宅合約「承租方」分組包含基本資料、家庭＆財產、授權、附件，用來確認租客的申請身分是否符合社會住宅資格。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「基本資料」怎麼審核租客資格？（低收入戶、中低收入戶等身分別選項）
- 講法：低收入戶申請社宅／社宅租客資格怎麼審核
- 給誰看：property_manager
- 基本資料分頁要勾選承租方身分別，選項包含一般戶、低收入戶、中低收入戶、六十五歲以上之老人（限申請人本人）、住宅政策補貼戶等，或勾選「以上均無」。〔src/pages/contracts/edit/tenantBasic/Index.vue〕

### 社宅合約「家庭＆財產」分頁要登記什麼？（家庭成員、不動產與動產總額、最近年所得）
- 講法：社宅家庭財產申報／社宅不動產動產總額申報
- 給誰看：property_manager
- 「家庭＆財產」分頁要登記家庭成員、所在地址、持分比例、不動產總額、動產總額與最近年所得。〔src/pages/contracts/edit/tenantHousehold/Index.vue〕

### 社宅合約承租方的「授權」分頁要同意什麼？（財稅所得總檢核、家庭年所得百分位等資格條件）
- 講法：承租方授權項目／財稅所得總檢核授權
- 給誰看：property_manager
- 授權分頁要勾選同意授權的項目，包含申請人及家庭成員是否符合財稅所得總檢核、家庭年所得是否低於當地一定百分位所得等資格條件。〔src/pages/contracts/edit/tenantLicense/Index.vue〕

### 社宅合約「業者」分頁在做什麼？（確認團隊資料與經理人資訊，有誤要回團隊資訊或帳號資訊修改）
- 講法：社宅業者分頁／業者資料錯誤要去哪改
- 給誰看：property_manager
- 社宅合約的「業者」分頁用來確認團隊資料與經理人資訊是否正確。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕
- 如果資料有誤，需要點選藍字的「團隊資訊」或「帳號資訊」連結回去修改，不能直接在這個分頁修改。〔幫助中心:Landlordonboarding09Socialhousing_zh-Hant.html〕

### 社宅合約「點交證明文件」分頁在約定什麼？（點交狀態與修繕責任的預先約定，不是簽約後實際執行的點交）
- 講法：社宅點交證明文件是什麼／合約裡的點交跟實際點交一樣嗎
- 給誰看：property_manager
- 社宅合約編輯畫面裡的「點交證明文件」分頁，是在合約條款中先約定點交狀態與修繕責任，例如選擇「現狀」或「修繕後點交」。〔src/pages/contracts/edit/moveIn/Index.vue〕
- 分頁提示：依照合約，所有品項預設以現狀且由出租方負責修繕，如果承租方刻意損壞，則由承租方自行負擔責任。〔src/pages/contracts/edit/moveIn/Index.vue〕
- 這個分頁只是合約條款裡的預先約定，跟簽約完成之後、實際執行點交作業的流程是不同的頁面。〔src/routes/contracts.js〕

### 社宅合約選「包租包管」或「轉租」範本，分頁會不同嗎？（包租包管隱藏承租方戶籍/證照/附件，轉租隱藏出租方證照/附件）
- 講法：社宅包租包管範本分頁／社宅轉租範本分頁差異
- 給誰看：property_manager
- 如果合約範本選擇「包租包管」範本，承租方分組下的「家庭＆財產」「授權」「附件」三個分頁不會顯示。〔src/use/useEditStore.js〕
- 如果合約範本選擇「轉租」範本，出租方分組下的「授權」「附件」兩個分頁不會顯示。〔src/use/useEditStore.js〕
- 否定查證：`{'claim': '句子引用的畫面/程式文字「if (editStore.form.contract_template_sel...」確實逐字存在於來源檔案（句子本身即引用該字串）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'if (editStore.form.contract_template_selected === \'"\'"\'charter\'"\'"\'){\' master -- src/use/useEditStore.js', 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（code:src/use/useEditStore.js）「if (editStore.form.contract_te...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`
- 否定查證：`{'claim': '句子引用的畫面/程式文字「if (editStore.form.contract_template_sel...」確實逐字存在於來源檔案（句子本身即引用該字串）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'if (editStore.form.contract_template_selected === \'"\'"\'sublet\'"\'"\'){\' master -- src/use/useEditStore.js', 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（code:src/use/useEditStore.js）「if (editStore.form.contract_te...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`
- ⚠️ 待查：社宅合約範本其實有三個值：management（代租代管）、charter（包租包管）、sublet（轉租）；useEditStore.js 只對 charter／sublet 有額外拿掉分頁的規則，grep 不到 'management' 這個字串，研判選「代租代管」範本時看到的是完整分頁，未逐一查證交回裁決是否需要補一條說明。

## 簽約與合約檢視（8 條；頁：web:contracts.sign、contracts.show、web:contracts.show）

### 合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效，天數為團隊可調整設定）
- 講法：合約審閱期多久／合約邀請多久會過期／租客沒簽約連結失效／審閱期天數
- 給誰看：property_manager、prospect
- 房東送出合約邀請後，系統會給租客一段審閱期才能簽約；天數其實是讀團隊設定，沒有設定才用預設的 3 天（72 小時）。〔app/Http/Controllers/ContractController.php〕
- 這個審閱天數設定屬於團隊層級，不同團隊可以各自覆蓋預設值。〔app/Http/Controllers/ContractController.php〕
- 從發送邀請時開始計算，租客如果沒有在期限內完成簽約，這個合約邀請連結就會失效。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 否定查證：`{'claim': '審閱天數沒有設定時，程式用 ?? 3 這個 PHP null-coalescing 語法回退到 3 天，這是句子引用的原始程式片段', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c -F -e \'->getSettings(\'"\'"\'contract_review_renew_period\'"\'"\', (int) optional($this->role)->id)[\'"\'"\'review_days\'"\'"\'] ?? 3);\' master -- app/Http/Controllers/ContractController.php', 'result': '2 筆命中', 'positive_control': '同一 fine 另一筆證據（contract_inviting_expire_at 那行）用相同方式 grep 命中 2 筆，證明 grep 條件與檔案存取本身有效'}`
- 否定查證：`{'claim': '句子引用的幫助中心文字「從您發送邀請時開始計算，租客需要在72小時內進行簽約，否則該連結就會失效。...」確實逐字存在於該頁面', 'grep': "grep -cF '從您發送邀請時開始計算，租客需要在72小時內進行簽約，否則該連結就會失效。' /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/landlordonboarding04lease_zh-Hant.html", 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:app/Http/Controllers/ContractController.php）「->getSettings('contract_review_renew_period', (int) optional($this->role)->id)['review_days'] ?? 3);」grep -cF 命中 2 筆，證明 grep 條件與檔案存取本身有效"}`
- ⚠️ 待查：app/Http/Controllers/Internal/ContractWriteController.php 另有一條寫死 72 小時（+72 HOUR）的路徑，數值恰好與預設值相同，但走的是內部/API 寫入流程而非本細目描述的主要送出邀請流程，本細目未收錄此路徑，交回裁決是否兩條路徑需要分開說明。

### 租客簽約要經過哪些步驟？（承租方簽約資料、上傳身分證明文件與印章、部分合約範本另有條款勾選、雲想科技畫面簽名）
- 講法：租客怎麼簽約／簽約要填什麼／簽約要傳哪些印章／簽名過程有紀錄嗎
- 給誰看：property_manager
- 租客簽約頁面第一步要填寫「承租方簽約資料」，並選擇「簽約身份」。〔resources/views/contract/sign.blade.php〕
- 頁面會要求上傳承租方身份證明文件影本；另外還有「工作名片/學生證」（同一個上傳欄位）與「良民證」等其他證明文件的上傳欄位，各自獨立、不能互相替代。〔resources/views/contract/sign.blade.php〕
- 印章上傳依簽約身份不同而異：租客身份要上傳「小章」；法人身份（非租客）則要上傳「大章」與「小章」兩個欄位。〔resources/views/contract/sign.blade.php〕
- 如果這份合約是 GTB 契約範本，簽約前會多一個步驟：畫面下方會出現 5 個條款確認選項（詳閱契約條款、無法更改內容、續約通知天數、履約保證金退還天數、吸菸罰緩等規定），要全部勾選才能繼續；一般合約範本沒有這個額外勾選步驟。〔src/entry/contract-sign.js〕
- 確認資料無誤後，如果是 GTB 契約，要先點「下一步，同意合約條款」進到條款頁勾完 5 個確認選項，再點「下一步，前往簽名」才會進入雲想科技（Thinkcloud）的簽約畫面；一般合約範本只有一個「下一步」按鈕，點選後直接進入雲想科技簽約畫面。整個瀏覽、簽名過程都有時間戳記與 IP 紀錄。〔resources/views/contract/sign.blade.php〕
- 否定查證：`{'claim': '簽約流程裡沒有「免簽」這個說法（幫助中心與程式皆無此詞）', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c '免簽' master -- 'src/**' 'resources/**'", 'result': '0 筆', 'positive_control': "同範圍 grep -c '電子簽' 命中 19 個檔案，證明 grep 與範圍本身是有效的、不是查詢條件本身有問題"}`
- ⚠️ 待查：isGTBContract（src/entry/contract-sign.js computed）在 resources/views/contract/sign.blade.php 裡有 11 處消費端，會控制「下一步，前往簽名」按鈕、承租方身份證明文件影本必填星號、實際入住人／履約保證金退款整個區塊、電子簽約圖章區塊，不是未接線的死碼。GTB 這個範本代號本身，程式裡除了一則註解「// GTB 大翰」（src/pages/contracts/edit/_methods/getFormDataForStepDone.js）外，找不到把它翻譯成正式產品用語的地方，交回裁決 GTB 契約在商業上該怎麼向使用者稱呼或介紹。

### 電子簽章簽約要另外收費嗎？（系統內沒有簽章計費機制，簽約流程無付費／加購畫面）
- 講法：電子簽章要收費嗎／簽約要加購嗎／電子簽章計費
- 給誰看：property_manager、prospect
- JGB 的電子簽章走 Thinkcloud 這家第三方服務，相關的簽約紀錄裡沒有任何費用或點數欄位。〔database/migrations/2026_06_17_000002_create_contract_esign_table.php〕
- 租客的簽約頁流程沒有付費或加購的畫面元素。〔resources/views/contract/sign.blade.php〕
- 否定查證：`{'claim': 'contract_esign 資料表沒有費用／點數／金額相關欄位', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -in 'fee\\|point\\|price\\|amount' master -- database/migrations/2026_06_17_000002_create_contract_esign_table.php", 'result': '0 筆', 'positive_control': '同檔 grep -c thinkcloud 命中 17 筆，證明檔案本身讀得到、grep 條件有效，只是費用類欄位確實不存在'}`
- 否定查證：`{'claim': '租客簽約頁（resources/views/contract/sign.blade.php）畫面文字裡沒有付費／加購／購買／收費字樣', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -in '付費\\|加購\\|購買\\|收費' master -- resources/views/contract/sign.blade.php", 'result': '0 筆', 'positive_control': '同檔 grep -c 簽約 命中 7 筆，證明檔案讀得到內容、不是空檔案或路徑寫錯'}`
- ⚠️ 待查：這只證明系統內沒有簽章計費機制，不證明 JGB 方案價目表沒有把電子簽章列為方案內容——方案內容以 /pricing 頁為準，售前不應直接報價。

### 合約簽約後可以修改嗎？（送出前可編輯、簽名前可取消簽名重編，簽署完成即無法更改，需重新簽一份新合約）
- 講法：合約簽名後可以改嗎／合約內容填錯怎麼辦／取消簽名重新編輯／簽約後修改合約
- 給誰看：property_manager、prospect
- 合約如果還沒發送出去，都可以點選小齒輪選擇「編輯合約」進行編輯與修改。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 合約已經發送但雙方都還沒完成簽名前，可以點選小齒輪選擇「取消簽名」，取消之後可以重新編輯這份合約。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 如果合約已經簽名完成，就無法再修改內容，需要重新創建一份合約才能修改。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 合約簽署完成即會生成 PDF 檔案，且電子簽章具有法律效力，無法更改該合約或物件的內容，內容有誤時需要先解約才能再簽署一份新合約。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 否定查證：`{'claim': '句子引用的幫助中心文字「如合約已經簽名，想要更改，請重新創建一份合約進行修改。...」確實逐字存在於該頁面', 'grep': "grep -cF '如合約已經簽名，想要更改，請重新創建一份合約進行修改。' /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/landlordonboarding04lease_zh-Hant.html", 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（help:landlordonboarding04lease_zh-Hant.html）grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`
- 否定查證：`{'claim': '句子引用的幫助中心文字「*合約簽署完成即生成pdf檔之合約，且電子簽章具有法律效力，無法更改該合約或物件...」確實逐字存在於該頁面', 'grep': "grep -cF '*合約簽署完成即生成pdf檔之合約，且電子簽章具有法律效力，無法更改該合約或物件之內容，需謹慎閱覽合約再行簽約。若內容有誤，需將其解約才能再簽署一份合約。' /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/landlordonboarding04lease_zh-Hant.html", 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（help:landlordonboarding04lease_zh-Hant.html）grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`

### 合約檢視頁面看得到什麼？（出／承租方資訊、業者、經理人資訊，以及點交點退進行中的提示）
- 講法：合約檢視頁面看得到什麼／合約詳細資料在哪看／合約點交中提示
- 給誰看：property_manager
- 合約檢視頁面會顯示「出／承租方資訊」「業者」「經理人資訊」等區塊面板。〔src/pages/contracts/show/_parts/PanelInfoStructure.vue〕
- 如果合約正在點交流程中，頁面會顯示提示：合約點交中，等待承租方確認，或合約點交中，請確認點交結果，依目前是哪一方在等待而不同。〔src/pages/contracts/show/Index.vue〕
- 點退流程中的合約也會有類似的提示：合約點退中，等待承租方確認，或合約點退中，請確認點退結果。〔src/pages/contracts/show/Index.vue〕

### 上傳既有（紙本）合約檔案有什麼限制？（PDF、最大 10MB，依合約／續約／終止合約分類歸檔）
- 講法：上傳紙本合約檔案限制／既存合約歸檔類別
- 給誰看：property_manager
- 合約檢視頁用來上傳既有（紙本）合約的歸檔檔案，支援 PDF 檔，檔案大小最大 10MB。〔resources/views/contract/show.blade.php〕
- 歸檔資料依照來源分成三種類別：合約、續約、終止合約，畫面上方會顯示對應的類別標籤。〔resources/views/contract/show.blade.php〕

### 合約檢視頁面會提示信用卡自動扣款授權嗎？（收款設定需要信用卡自動扣款時才會提示前往授權）
- 講法：信用卡自動扣款授權／前往授權是什麼
- 給誰看：property_manager
- 如果合約的收款設定需要信用卡自動扣款，合約檢視頁面會提示「即將前往授權」，說明需要授權信用卡才能在約定繳費日自動扣款，確認後點選「前往授權」繼續流程。〔resources/views/contract/show.blade.php〕

### 上傳既有合約跟建立電子合約差在哪？（既存合約用於已簽好或有自己公版合約的情境，皆可續用系統帳務／修繕追蹤）
- 講法：上傳既有合約適用情境／上傳合約檔案太大怎麼辦／既存合約跟電子合約差別
- 給誰看：property_manager、prospect
- 「上傳合約」適用於已經跟租客簽署完的合約，或是業者本身特有的公版合約，讓已有合約的房東也能無縫接軌使用系統。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 不論是上傳既有合約或使用 JGB 內政部公版合約，之後都可以透過系統做後續合約、帳務、修繕追蹤。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 如果掃描的合約 PDF 檔案大於 10MB，建議先在印表機端調整掃描品質，或使用線上壓縮工具縮小檔案再上傳。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

## 點交（7 條；頁：contracts.moveIn、web:contracts.move_in）

### 點交清單怎麼確認？（依合約約定的傢俱項目逐一上傳照片、標註出租方或承租方負責）
- 講法：點交清單怎麼確認／點交要上傳照片嗎／點交責任歸屬／點交備註字數限制
- 給誰看：property_manager
- 點交清單會列出合約成立時約定的交接項目，點選「編輯」可以上傳照片或加上備註說明現況。〔resources/views/contract/move-in.blade.php〕
- 每個項目可以標註責任歸屬是「出租方」還是「承租方」負責，這個標註是從合約的附設傢俱分頁帶過來的。〔resources/views/contract/move-in.blade.php〕
- 點交備註（補充條款）欄位限制填寫 20 行，每行限制 50 個字，超過部分系統會自動裁切。〔resources/views/contract/move-in.blade.php〕
- 如果這個空間目前沒有任何品項，畫面會提示「此空間尚未提供任何品項」。〔resources/views/contract/move-in.blade.php〕
- 否定查證：`{'claim': '句子引用的畫面/程式文字「<div v-show="size($store.state.handover....」確實逐字存在於來源檔案（句子本身即引用該字串）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'<div v-show="size($store.state.handover.handover_list_origin[pattern_key].facilities_list) <= 0" class="mb-4">{{ ___(\'"\'"\'此空間尚未提供任何品項。\'"\'"\') }}</div>\' master -- resources/views/contract/move-in.blade.php', 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:resources/views/contract/move-in.blade.php）「<div>{{ ___('以下是合約立定時的約定交接項目，點...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`

### 點交要填另計費用起始度數嗎？（依合約設定另計的費用項目要輸入起始度數，會直接帶入日後帳單計算）
- 講法：點交要填電表度數嗎／點交起始度數／點交後帳單怎麼算電費
- 給誰看：property_manager
- 點交流程裡有「另計費用起始度數」項目，根據合約上的設定，某些費用是額外計算的，需要輸入每筆費用的起始度數。〔resources/views/contract/move-in.blade.php〕
- 點交清單如果有填寫初始電費度數，這個度數會直接帶入日後帳單，系統會自動計算電費。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

### 點交頁面一般合約跟社宅合約用的是同一個嗎？（不是，一般住宅合約用一般合約的點交頁面，社宅合約會被導向社宅合約的點交頁面）
- 講法：社宅點交頁面跟一般合約一樣嗎／點交頁面差異
- 給誰看：property_manager
- 一般住宅合約點交送出後，會進入一般合約專用的點交頁面。〔routes/web.php〕
- 如果合約的物件用途是社會住宅，系統會強制把畫面導轉到另一個社宅專用的點交頁面。〔app/Http/Controllers/ContractController.php〕

### 點交送出後還能再送一次嗎？（已完成點交無法再次送出；已送出、等待租客確認中的清單要先取消邀請才能改）
- 講法：點交已送出可以改嗎／點交完成能重新點交嗎／取消點交邀請
- 給誰看：property_manager
- 如果這份合約已經完成點交，系統會擋下再次送出點交的動作，並提示「此合約已完成點交，無法再次送出點交」。〔app/Contract.php〕
- 如果點交清單已經送出、正在等待租客確認，系統也會擋下重複送出，並提示要先取消點交邀請，才能重新送出點交清單。〔app/Contract.php〕
- 否定查證：`{'claim': '「已完成點交後系統擋下再次送出」是目前程式行為，不是舊邏輯殘留', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n 'moveInSubmitBlockedReason' master -- app/Http/Controllers/ContractController.php app/Contract.php", 'result': '命中 3 筆：app/Contract.php 定義該方法，app/Http/Controllers/ContractController.php 兩處呼叫（moveIn、moveIn2）並用其回傳值導頁——定義與呼叫互相呼應，非死碼', 'positive_control': '同一 grep 對已知早已移除的方法名（如 moveInSubmitBlockedReasonLegacy）搜尋應為 0 筆，實際查無此名稱可供對照，改以「呼叫端存在」作為判死活的依據'}`

### 點交邀請送出後可以取消嗎？（可以，系統會記錄「取消點交邀請」這個動作）
- 講法：點交邀請可以取消嗎／已送出的點交怎麼收回
- 給誰看：property_manager
- 已經送出、等待租客確認的點交邀請可以取消，系統會記錄這個「取消點交邀請」動作。〔app/Contract.php〕

### 點交結果能下載 PDF 嗎？（有專屬頁面可以檢視或下載點交 PDF）
- 講法：點交結果PDF／點交可以下載嗎
- 給誰看：property_manager
- 點交結果有專屬的頁面，可以用來檢視或下載點交內容的 PDF 檔。〔routes/web.php〕

### 點交是必要流程嗎？（點交是選擇性操作，未點交也能發帳單；簽約完成後即可在執行中合約選取物件點交）
- 講法：點交一定要做嗎／什麼時候可以點交／不點交可以發帳單嗎
- 給誰看：property_manager、prospect
- 點交基本上是選擇性操作，可以依房東的習慣和房客約定自行決定是否進行，沒有點交也可以發送帳單。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 點交的時機是簽約完成後，就可以在「執行中合約」選取想點交的物件進行點交。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 執行中合約列表會用燈號的方式顯示這份合約有沒有進行點交。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 否定查證：`{'claim': '句子引用的幫助中心文字「基本上點交點退是「選擇性操作」，可依照房東習慣和房客約定自行決定是否進行，未點交...」確實逐字存在於該頁面', 'grep': "grep -cF '基本上點交點退是「選擇性操作」，可依照房東習慣和房客約定自行決定是否進行，未點交也可以發送帳單' /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/landlordonboarding04lease_zh-Hant.html", 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（help:landlordonboarding04lease_zh-Hant.html）grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`
- 否定查證：`{'claim': '句子引用的幫助中心文字「執行中合約中，合約是否有點交的會以燈號的方式顯現在合約上方。...」確實逐字存在於該頁面', 'grep': "grep -cF '執行中合約中，合約是否有點交的會以燈號的方式顯現在合約上方。' /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/landlordonboarding04lease_zh-Hant.html", 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（help:landlordonboarding04lease_zh-Hant.html）grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`

## 點退（6 條；頁：contracts.moveOut）

### 點退清單怎麼處理設備損壞？（可編輯填入賠償金額與理由，過程可儲存草稿）
- 講法：點退設備損壞怎麼處理／點退可以先存草稿嗎／點退賠償金額
- 給誰看：property_manager
- 點退清單會列出點交時約定的傢俱項目，如果物件沒有提供傢俱品項，畫面會提示不需要清點。〔src/pages/contracts/move-out/Index.jsx〕
- 點退時如果發現設備有損壞，需要由房客負賠償責任，可以點選「編輯」並填入賠償金額與理由；沒有標註就代表狀況正常。〔src/pages/contracts/move-out/Index.jsx〕
- 點退過程可以先按「儲存點退草稿」，不用一次填完，儲存失敗時畫面會提示「草稿儲存失敗，請稍後再試」。〔src/pages/contracts/move-out/Index.jsx〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「t('根據合約，此物件您沒有提供傢俱品項，無需清點。')...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'t(\'"\'"\'根據合約，此物件您沒有提供傢俱品項，無需清點。\'"\'"\')\' master -- src/pages/contracts/move-out/Index.jsx', 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:src/pages/contracts/move-out/Index.jsx）「t('請確認物件點退都沒有問題，若有損壞請輸入賠償金額與理由...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`
- 否定查證：`{'claim': "句子引用的畫面/程式文字「t('請確認物件點退都沒有問題，若有損壞請輸入賠償金額與理由，無標註表示狀況正常...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'t(\'"\'"\'請確認物件點退都沒有問題，若有損壞請輸入賠償金額與理由，無標註表示狀況正常。\'"\'"\')\' master -- src/pages/contracts/move-out/Index.jsx', 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:src/pages/contracts/move-out/Index.jsx）「t('根據合約，此物件您沒有提供傢俱品項，無需清點。')...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`

### 點退會產生什麼帳單？（含提前解約金、點退押金、賠償金，設定期限後發送，租客確認並繳款才算完成）
- 講法：點退帳單包含什麼／點退押金怎麼退／點退完成的條件
- 給誰看：property_manager
- 點退流程分兩步：第一步確認點交清單、填寫損壞賠償金額，第二步才會進入「點退找補費用」頁面產生帳單。〔src/pages/contracts/move-out/Index.jsx〕
- 點退確認清單、填完損壞賠償金額之後，系統會製作點退帳單，內容包含提前解約金、點退押金、賠償金，並要填入帳單期限。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 帳單設定完成後要發送給租客，等租客確認點退內容並完成繳款，才算完成點退程序。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

### 什麼合約可以點退？（合約狀態須為執行中／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外）
- 講法：什麼合約可以點退／沒有註冊的租客可以點退嗎／點退合約狀態限制
- 給誰看：property_manager
- 點退有一個限制：如果合約沒有綁定 JGB 註冊租客帳號，一般情況下不可以點退。〔app/Contract.php〕
- 但如果是「免註冊租客」（建檔時就標註不綁定 JGB 帳號），因為點退一送出就立即成立、不需要租客登入同意，所以這種情況仍然允許點退。〔app/Contract.php〕
- 合約狀態必須是「合約成立」「點交完成」「歷史合約」或「完成歷史合約」其中之一才能點退；已經點退完成過的合約不能再次點退。〔app/Contract.php〕
- 否定查證：`{'claim': '「合約沒有綁定 JGB 租客帳號則不可點退」在程式中確實存在（非註解掉的舊邏輯）', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n 'function canMoveOut' master -- app/Contract.php", 'result': '命中 1 筆：app/Contract.php 定義 canMoveOut()，緊接的 if (!$this->to_user_connect && !$isExemptRegisterTenant) { return false; } 為現行有效程式碼（未被註解）', 'positive_control': '同檔 canEarlyTermination() 亦可用同樣方式 grep 到且緊接生效條件式，兩者皆非死碼，可互相對照'}`

### 點退的時間限制是什麼？（合約到期前 30 天起可以點退，過了到期日之後目前沒有再設上限）
- 講法：點退時間限制／點退要在到期前幾天辦理／合約到期後還能點退嗎
- 給誰看：property_manager
- 點退最早可以在合約到期日的前 30 天開始執行。〔app/Contract.php〕
- 點退原本也有到期日後 30 天內的上限，但這個上限已經在 2022/08/04 因法律顧問需求改為「無限制」，所以合約到期之後能不能點退目前沒有再受這個上限卡住。〔app/Contract.php〕
- 否定查證：`{'claim': '點退到期日後的 30 天上限（$endTs）目前沒有任何條件式在用它卡住點退，即「無限制」是現行行為', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n '\\$endTs' master -- app/Contract.php", 'result': '命中 1 筆，僅有 $endTs = $dateEndTs + 86400 * 30; 這一行定義，沒有任何 if / return 用到這個變數', 'positive_control': "同檔 grep -n '\\$startTs' 命中 2 筆——定義那行，以及 if ($now < $startTs || $now > INF) 的判斷式裡確實被使用，可對照證明 $endTs 是「定義但未使用」而非 grep 語法本身有問題"}`
- ⚠️ 待查：幫助中心 landlordonboarding04lease_zh-Hant.html 只說「租約將於30天內到期或是已解約之歷史合約，可進行點退」，沒有明確講到期日之後是否有上限；程式 app/Contract.php canMoveOut() 的上界判斷式 `$now > INF` 恆為 false（即無上限），下界仍是到期日前 30 天，兩者不衝突，但幫助中心未提及『無上限』這件事，列此供覆核是否需要在對外說法補充。

### 點退完成的合約為什麼還在「執行中合約」？（只要還沒到合約到期日就會留在執行中，到期後才轉入歷史合約）
- 講法：已點退為什麼還在執行中合約／歷史合約是什麼／點退狀態分類
- 給誰看：property_manager、prospect
- 已經點退或已經辦理提前解約的合約，如果還沒到合約到期日，都還是會停留在「執行中合約」列表。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 歷史合約是指已經到期的合約；因為點退可以在合約到期前 30 天就開始執行，所以歷史合約列表底下的狀態還會再細分成「點退完成」「未退押金」「待退押金」「點退中」。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

### 點退第二步「點退找補費用」頁面要填什麼？（傢俱賠償、應退費用、違約金，另可填備註、期限、附件）
- 講法：點退找補費用要填什麼／點退第二步流程／傢俱賠償跟應退費用差在哪
- 給誰看：property_manager
- 點退流程的第二步會進入「點退找補費用」頁面，這裡才是真正產生帳單的畫面，跟第一步的點交確認清單是分開的兩個步驟。〔src/pages/contracts/move-out/Index.jsx〕
- 這個頁面要填的收費／退費項目包含「傢俱賠償」、「應退費用」、「違約金」，另外還可以填寫備註、繳費期限、附件。〔src/pages/contracts/move-out/_parts/__Compensation.vue〕

## 續約（7 條；頁：contracts.renew、contracts.renew.preview、contracts.pick）

### 怎麼一次幫多筆合約續約？（合約總表「建立合約」旁選批次續約，異動中的合約不能選）
- 講法：批次續約怎麼操作／續約可以選哪些合約／哪些合約不能續約
- 給誰看：property_manager
- 在「執行中合約」點選右上方建立合約旁的小箭頭，選擇「批次續約」，就會進入合約挑選頁面。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 挑選合約時可以用案名、地址、經理人、大房東、租客、ID 六種範圍搜尋。〔src/pages/contracts/pick/Index.jsx〕
- 續約功能無法選擇正在異動中的合約，包括「提前解約申請中」「點交中」及「點退中」的合約。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 否定查證：`{'claim': '句子引用的幫助中心文字「*續約功能，無法選擇正在異動中的合約，包括「提前解約申請中」、「點交中」及「點退...」確實逐字存在於該頁面', 'grep': "grep -cF '*續約功能，無法選擇正在異動中的合約，包括「提前解約申請中」、「點交中」及「點退中」的合約。' /Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/landlordonboarding04lease_zh-Hant.html", 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（help:landlordonboarding04lease_zh-Hant.html）grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`

### 續約日期怎麼設定？（快速日期設定一次套用全部，或個別指定每份合約的續約日）
- 講法：續約日期怎麼設定／續約可以一次設定嗎／租客收不到續約通知
- 給誰看：property_manager
- 選好要續約的合約之後，可以用「快速日期設定」一次套用同一個續約日期到所有合約。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 也可以在下方個別調整，用「個別指定續約日」分別設定每一份合約各自的續約日期。〔src/pages/contracts/renew/Index.vue〕
- 如果租客的聯繫方式尚未驗證，或是通知功能沒有開啟，畫面會提示這位租客無法收到續約通知。〔src/pages/contracts/renew/Index.vue〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「t('租客聯繫方式尚未驗證 / 未開啟通知，無法收到續約的通知。')...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'t(\'"\'"\'租客聯繫方式尚未驗證 / 未開啟通知，無法收到續約的通知。\'"\'"\')\' master -- src/pages/contracts/renew/Index.vue', 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:src/pages/contracts/renew/Index.vue）「t('個別指定續約日')...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`

### 續約可以上傳紙本已簽合約嗎？（可以，提供雙方已完成簽約的紙本合約掃描檔即可）
- 講法：續約可以上傳紙本合約嗎／續約用電子簽名圖章
- 給誰看：property_manager
- 續約頁面提供「合約檔案」上傳功能，可以直接提供雙方已經完成簽約的紙本合約掃描檔。〔src/pages/contracts/renew/Index.vue〕
- 這個功能也支援用電子簽名圖章取代親手簽名，但如果團隊還沒上傳電子簽名圖章，這個選項會無法啟用。〔src/pages/contracts/renew/Index.vue〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「t('團隊尚未上傳電子簽名圖章，無法啟用。')...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'t(\'"\'"\'團隊尚未上傳電子簽名圖章，無法啟用。\'"\'"\')\' master -- src/pages/contracts/renew/Index.vue', 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:src/pages/contracts/renew/Index.vue）「t('請提供雙方已完成簽約的紙本合約掃描檔。')...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`

### 續約可以預先編輯帳單嗎？（續約預覽頁可先編輯續約期間帳單，實際帳單於完成續約後才產生）
- 講法：續約可以先看帳單嗎／續約帳單什麼時候產生／確認續約帳單頁面
- 給誰看：property_manager
- 續約流程有一個「確認續約帳單」的預覽頁面，會依續約日期與週期設定，預先產生一系列帳單。〔src/pages/contracts/renew/Preview.vue〕
- 這些帳單可以預先編輯標題、繳費期限、帳單週期、金額、細項與自動執行動作，但畫面會提示：實際帳單要等合約完成續約後才會真正產生。〔src/pages/contracts/renew/Preview.vue〕
- 如果這份合約沒有可以預先產生的帳單，畫面會顯示「此合約無可預產的帳單」。〔src/pages/contracts/renew/Preview.vue〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「t('此合約無可預產的帳單')...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'t(\'"\'"\'此合約無可預產的帳單\'"\'"\')\' master -- src/pages/contracts/renew/Preview.vue', 'result': '1 筆命中', 'positive_control': "同一 fine 的另一筆證據（code:src/pages/contracts/renew/Preview.vue）「t('以下為依續約日期與週期設定預先產生的帳單，可預先編輯標...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效"}`

### 續約邀請發出後流程是什麼？（租客簽回後可在「待租客簽回」查找，房東確認無誤後立即簽名完成續約）
- 講法：續約簽約流程／租客簽回續約後要做什麼／續約怎麼完成
- 給誰看：property_manager
- 設定完續約日期後，系統會將續約邀請發送給租客，可以在「待租客簽回」欄位中查找這份合約。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 租客簽回後，房東方確認資料無誤，就可以點選「立即簽名」並完成簽約程序，最後即完成該合約的續約。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

### 續約邀請效期是幾天？（預設 3 天，團隊可覆蓋設定）
- 講法：續約邀請幾天內要簽／續約審閱天數
- 給誰看：property_manager
- 續約邀請發出後的審閱天數，預設是 3 天，團隊可以另外設定天數覆蓋這個預設值。〔app/Services/ContractService.php〕

### 續約時資料怎麼沿用？（新合約由舊合約複製，並更新出租方/承租方最新資料；週期設定有調整就用新的、沒調整就沿用）
- 講法：續約會沿用舊合約資料嗎／續約聯絡資料會更新嗎
- 給誰看：property_manager
- 續約時系統會複製原合約產生新合約，並用出租方、承租方目前最新的角色或會員資料，更新聯絡電話、Email 等欄位，不是直接照抄舊合約當時填寫的資料。〔app/Services/ContractService.php〕
- 繳費週期、帳單週期制度等設定，如果續約頁面有調整就用新的值，沒調整則沿用原合約設定。〔app/Services/ContractService.php〕
- ⚠️ 待查：本細目未查證續約流程是否允許直接修改租金金額（rent），只確認到繳費週期/帳單週期設定與出租承租方聯絡資料的更新規則，交回裁決是否需要另外查證「續約可否改租金」。

## 提前解約（5 條；頁：web:contracts.early_termination）

### 房東申請提前解約要選什麼理由？（新版中文合約有 10 項法定理由可選，其餘合約只能選「其他」）
- 講法：提前解約理由有哪些／解約要選什麼原因／非中文合約解約理由
- 給誰看：property_manager
- 房東發起提前終止合約時，一定要選擇「原因」，選項一律包含「其他」。〔app/Http/Controllers/ContractController.php〕
- 只有合約檔案是新版中文合約時，才會顯示其他 10 項法定理由，例如「出租方為重新建築而必要收回」「承租方遲付租金之總額達兩個月之金額」「承租方擅自將租賃住宅轉租或轉讓租賃權於他人」等。〔app/Http/Controllers/ContractController.php〕
- 選擇「其他」以外的理由時，畫面不會出現理由說明文字欄位；但若選「其他」，會出現一個文字框讓房東輸入解約理由文字。〔resources/views/layouts/lightbox/early-termination-by-landlord.blade.php〕
- 否定查證：`{'claim': "選「其他」以外的理由不會出現理由說明文字欄位——原本 drafts 版本引用的 'other' => ___('其他') 與 reason_2 兩處字串在 ContractController.php 裡各出現 3 筆／1 筆，其中 1949 行那組屬於 index() 內的『取消訂閱理由』(我不再需要使用相關服務／無法解決我遇上的問題／費用昂貴)，跟提前解約完全無關；真正的提前解約區塊在 earlyTermination() function（22684 行起），本細目證據已改指向該函式內文字", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "public function earlyTermination\\|public function index(" master -- app/Http/Controllers/ContractController.php', 'result': 'index() 在 142 行、earlyTermination() 在 22684 行；原引用行號 1949 落在 index() 函式體內（142~22207 之間），不在 earlyTermination() 範圍', 'positive_control': "同一個 grep 對 'reason_1' 字串搜尋只在 earlyTermination() 附近（22738 行起）出現，可與被誤用的 index() 區塊互相對照確認範圍正確"}`
- 否定查證：`{'claim': '理由說明文字欄位（textarea）只在勾選『其他』時才會渲染，其餘理由不會出現這個欄位', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "v-if=.reasonKey == \'other\'." master -- resources/views/layouts/lightbox/early-termination-by-landlord.blade.php', 'result': '命中 1 筆，且該 v-if 只包住這一個 <div class="textarea-box">，同一個 v-for 迴圈裡沒有其他理由分支帶文字框', 'positive_control': '同檔 grep -n \'type="radio" name="reason_options"\' 命中 1 筆，證明每個理由都走同一個 radio 迴圈渲染，只有 reasonKey == \'other\' 那個條件式額外多渲染文字框'}`

### 申請提前解約要填什麼？（欲提前解約日須早於原合約到期日、違約金由誰付、佐證資料）
- 講法：提前解約要填什麼／解約違約金由誰付／提前解約日期限制／取消提前終止合約
- 給誰看：property_manager
- 房東申請提前解約時要填寫「欲提前解約日」，這個日期必須早於原合約的到期日，否則系統會擋下申請。〔app/Http/Controllers/ContractController.php〕
- 表單也要選擇「違約金由誰付」以及填寫違約金金額，並可以上傳佐證資料。〔app/Http/Controllers/ContractController.php〕

### 誰可以取消已送出的提前解約申請？（房東透過小齒輪取消，租客只有在提前解約確認中狀態才能取消）
- 講法：房東怎麼取消提前終止合約／租客可以取消提前解約嗎／取消提前解約條件
- 給誰看：property_manager
- 房東如果想取消已經送出的提前解約申請，可以點選合約旁的小齒輪，選取「取消提前終止合約」。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 租客也可以取消提前解約申請，但只有在合約狀態是「提前解約確認中」時才能取消。〔app/Http/Controllers/ContractController.php〕
- 如果合約不是這個狀態，系統會擋下取消動作並提示「您無法取消這份提前解約」。〔app/Http/Controllers/ContractController.php〕
- 否定查證：`{'claim': "句子引用的畫面/程式文字「'status-error' => ___('您無法取消這份提前解約')...」確實逐字存在於來源檔案（句子本身即引用該字串）", 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -cF \'\'"\'"\'status-error\'"\'"\' => ___(\'"\'"\'您無法取消這份提前解約\'"\'"\')\' master -- app/Http/Controllers/ContractController.php', 'result': '1 筆命中', 'positive_control': '同一 fine 的另一筆證據（code:app/Http/Controllers/ContractController.php）「if ($contract->status != Contr...」grep 命中 1 筆，證明 grep 條件與檔案存取本身有效'}`

### 什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起）
- 講法：什麼合約可以提前解約／可否提前解約設定對房東有效嗎／續約中可以提前解約嗎
- 給誰看：property_manager
- 可以申請提前解約的合約，狀態必須是「合約成立」或「點交完成」；已經在提前解約流程中、或已經完成過提前解約的合約不能再次申請。〔app/Contract.php〕
- 合約裡「租客是否可以提前解約」這個設定，只會限制租客身分發起提前解約；如果是房東身分要發起，不受這個設定限制。〔app/Contract.php〕
- 如果合約正在續約流程中、還沒完成簽名，也不能發起提前解約。〔app/Contract.php〕

### 提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金）
- 講法：提前解約後多久可以點退／提前解約影響
- 給誰看：property_manager、prospect
- 成功提前終止合約後，合約終止日會依新的日期更新，在租期到期前 30 天，就可以執行「點退押金」。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕
- 點退時系統會依照合約條件，自動帶入並判斷是否有違約金，房東可以依照實際狀況調整數字。〔幫助中心:landlordonboarding04lease_zh-Hant.html〕

## 租約公證（公證分頁與公證服務）（3 條；頁：contracts.edit.publicNotary、web:contracts.thinkcloud）

### 一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項，僅支援中文合約）
- 講法：一般合約公證怎麼設定／公證強制執行事項／英文合約可以公證嗎
- 給誰看：property_manager
- 一般合約的「公證」分頁要先選擇這份租賃合約是否同意辦理公證。〔src/pages/contracts/edit/publicNotary/General.vue〕
- 選擇同意辦理公證後，可以複選「公證書載明下列事項應逕受強制執行」的項目，包含：承租方如於租期屆滿後不返還租賃住宅；承租方未依約給付之欠繳租金、費用及代繳之管理費或違約應付金額；出租方於租期屆滿或契約終止時應返還承租方之全部或一部分押金。〔src/pages/contracts/edit/publicNotary/General.vue〕
- 這個分頁也可以設定保證人效力。〔src/pages/contracts/edit/publicNotary/General.vue〕
- 畫面提示：目前英文與英越文版合約不支援公證這個項目。〔src/pages/contracts/edit/publicNotary/General.vue〕

### 簽約時進入的雲想科技頁面是做什麼的？（承載 Thinkcloud 電子簽署流程的內嵌頁面，一般合約、委託合約皆會用到）
- 講法：簽約跳出的雲想科技頁面是什麼／雲想科技畫面是誰在用
- 給誰看：property_manager
- 這個頁面是用來承載 Thinkcloud（雲想科技）電子簽署畫面的內嵌頁面，簽約流程走到需要簽名的步驟時會導向這裡。〔resources/views/contract/thinkcloud.blade.php〕
- 這個頁面不只租賃合約會用到，委託合約簽署也共用同一個頁面。〔app/Http/Controllers/ContractController.php〕
- ⚠️ 待查：此頁面（雲想科技簽署頁面）在骨架中被歸類於「租約公證」粗目，但依程式內容，它實際承載的是 Thinkcloud 電子簽署 iframe，功能上更接近『簽約與合約檢視』的簽署機制本身，跟公證（notary）是否辦理是兩件事；本細目依骨架既定分類撰寫內容真實描述其功能，未強行改寫成公證服務，是否要調整粗目歸屬交回裁決。

### 雲想科技簽署畫面依合約類型有什麼差異？（公會版本合約加補充條款多一個協商條款簽名框；DIY 客製化合約解析失敗時會顯示提示訊息，不會直接出現系統錯誤畫面）
- 講法：DIY合約怎麼簽名／協商條款簽名框是什麼
- 給誰看：property_manager
- 如果合約是公會版本合約且有補充條款，簽署畫面會多一個「協商條款」簽名框。〔app/Http/Controllers/ContractController.php〕
- 如果是 DIY 客製化合約（自行上傳範本），系統會嘗試用兩種方式解析上傳的 PDF 底稿；如果兩種都解析失敗，畫面會顯示提示訊息（例如請用瀏覽器「列印→另存為 PDF」重新輸出後再上傳），而不是直接跳出系統錯誤畫面，但簽約流程仍需要使用者依提示重新上傳才能繼續。〔app/Http/Controllers/ContractController.php〕

## 委託合約（列表、建立編輯、檢視）（11 條；頁：entrustContracts.index、entrustedContracts.edit、entrustedContracts.edit.basic、entrustedContracts.edit.fee、entrustedContracts.edit.landlord_info、entrustedContracts.edit.manager_info、entrustedContracts.edit.payment、entrustedContracts.list、entrustedContracts.show）

### 委託合約是什麼？（房東委託業者包租代管的合約，跟業者與租客之間的租賃合約是不同份文件）
- 講法：委託合約是什麼／委託合約跟租賃合約差在哪／委託合約狀態頁籤
- 給誰看：property_manager、prospect
- 委託合約是房東與業者之間的合約，用來約定房東把物件委託給包租代管業者管理；它跟業者與租客之間的租賃合約是各自獨立的兩份合約。〔docs:knowledge/jgb-product-facts.md〕
- 委託合約總表跟一般合約總表一樣分成五個狀態頁籤：待發送委託約、待房東簽回、待管理者簽名、執行中委託約、歷史委託約。〔src/pages/entrustedContracts/list/_parts/PageTop.jsx〕
- 這裡的簽署角色跟一般合約相反：委託合約是等房東簽回，最後由管理者（業者）簽名完成。〔src/pages/entrustedContracts/list/_parts/PageTop.jsx〕

### 委託合約「包租」跟「代管」有什麼不同？（代管必填服務費制度／週期／約定日期，包租用包租租金及其計算制度）
- 講法：包租跟代管差在哪／委託合約類型／代管合約要填什麼
- 給誰看：property_manager、prospect
- 委託合約用「委託約類型」區分「包租合約」與「代管合約」兩種，也要設定委託約範本、委託約起迄日期。〔src/pages/entrustedContracts/edit/requirement/Basic.jsx〕
- 選擇代管合約時，必須填寫服務費制度、服務費幣別、服務費金額（收取頻率與約定日期）。〔docs:knowledge/jgb-product-facts.md〕
- 選擇包租合約時，則是用「包租租金」及其計算制度、收取頻率、約定日期。〔src/pages/entrustedContracts/edit/requirement/Fees.jsx〕

### 委託合約編輯畫面有哪些分頁？（房東資訊、委託條件三頁、管理方資訊共 3 組 5 頁）
- 講法：委託合約分頁有哪些／委託合約編輯步驟
- 給誰看：property_manager
- 委託合約編輯畫面分成「房東資訊」「委託條件」「管理方資訊」三個分組，「委託條件」底下又分基本資料、租金費用、收款方式三個分頁，合計 5 個分頁。〔src/routes/entrustedContracts.js〕

### 委託合約編輯完成後怎麼進入簽署？（點右上角「預覽合約」先儲存資料，再進入檢視頁面）
- 講法：委託合約怎麼進入簽署／委託合約預覽合約按鈕
- 給誰看：property_manager
- 委託合約編輯完成後，點選右上角「預覽合約」會先儲存資料，再進入委託合約檢視頁面，後續的簽署與歸檔都在檢視頁面進行。〔src/pages/entrustedContracts/edit/Index.jsx〕

### 委託合約上傳既有檔案限制多大？（6MB，比一般合約的 10MB 小）
- 講法：委託合約上傳檔案大小限制／委託合約檔案6MB
- 給誰看：property_manager
- 委託合約檢視頁面上傳既有委託合約檔案的大小上限是 6MB，比一般租賃合約檢視頁面的 10MB 上限更小。〔src/pages/entrustedContracts/show/_parts/signerInfo/ArchiveFileUploader.jsx〕

### 委託合約的收費分頁要設定什麼？（服務費或包租金額的計算模式與週期，押金提示不得超過兩個月租金）
- 講法：委託合約收費怎麼算／委託合約押金上限／跨月計算與當月分算
- 給誰看：property_manager
- 委託合約的收費分頁要設定計算模式、週期、單價、幣別等資訊。〔src/pages/entrustedContracts/edit/requirement/Fees.jsx〕
- 分頁上會提示：依內政部租賃住宅市場發展及管理條例規定，一般租賃契約押金額度最高不得超過兩個月租金。〔src/pages/entrustedContracts/edit/requirement/Fees.jsx〕
- 分頁也可以參考支付金額與參考服務費金額，並支援跨月計算或當月分算兩種計費方式。〔src/pages/entrustedContracts/edit/requirement/Fees.jsx〕

### 委託合約的房東資訊怎麼填？（房東註冊或房東免註冊、選擇個人房東或法人房東身份）
- 講法：委託合約房東資訊怎麼填／房東一定要註冊帳號嗎／房東免註冊是什麼
- 給誰看：property_manager
- 委託合約的房東資訊分頁要選擇「出租方身份別」，是「個人房東」還是「法人房東」。〔src/pages/entrustedContracts/edit/landlordInfo/LandlordInfo.jsx〕
- 跟一般租賃合約類似，這裡也有「房東註冊」與「房東免註冊」兩種模式：房東註冊代表房東會自己註冊 JGB 會員並自行填妥出租方資訊；房東免註冊代表房東不需要註冊會員，改由管理者協助填寫房東資訊。〔src/pages/entrustedContracts/edit/landlordInfo/LandlordInfo.jsx〕
- 分頁提示：系統會將這裡填寫的房東資料謄寫到合約內，過程經過加密處理，不讓資料外流。〔src/pages/entrustedContracts/edit/landlordInfo/LandlordInfo.jsx〕

### 委託合約的經理人資訊分頁要填什麼？（公司基本資料、指定經理人、租賃住宅管理人員名稱與證號、電子簽名圖章）
- 講法：委託合約經理人資訊怎麼填／租賃住宅管理人員證號／委託合約電子簽名圖章
- 給誰看：property_manager
- 委託合約的經理人資訊分頁要確認公司資訊（公司登記名稱、統一編號、登記地址、通訊地址、電話、Email）是否正確，並在「經理人」欄位指定這份合約由誰管理。〔src/pages/entrustedContracts/edit/managerInfo/ManagerInfo.jsx〕
- 這個分頁另外有「租賃住宅管理人員資訊」欄位，要填寫租賃住宅管理人員名稱與證號，這跟前面的經理人資訊是不同的欄位。〔src/pages/entrustedContracts/edit/managerInfo/ManagerInfo.jsx〕
- 分頁最下方也可以設定「使用電子簽名圖章取代親手簽名」。〔src/pages/entrustedContracts/edit/managerInfo/ManagerInfo.jsx〕

### 委託合約收付款資訊怎麼設定？（沒有選擇器，固定顯示「出租方帳戶」與「管理方帳戶」兩個現金收付區塊，後者必填）
- 講法：委託合約收付款怎麼設定／收款是給房東還是業者／委託合約可以選一種收款方式嗎
- 給誰看：property_manager
- 委託合約的「收付款資訊」分頁沒有讓你先選一種收款方式的選擇器，畫面固定顯示「現金收付－出租方帳戶」與「現金收付－管理方帳戶」兩個區塊，兩個都會顯示，不是挑一個顯示。〔src/pages/entrustedContracts/edit/requirement/Payment.jsx〕
- 「現金收付－管理方帳戶」是必填區塊；「現金收付－出租方帳戶」則沒有標示必填。〔src/pages/entrustedContracts/edit/requirement/Payment.jsx〕
- 兩個區塊都要填寫銀行代碼、銀行名稱、帳戶名稱、銀行帳號，管理方帳戶還可以把常用帳號加入清單方便下次選用。〔src/pages/entrustedContracts/edit/requirement/Payment.jsx〕
- 否定查證：`{'claim': '委託合約收付款資訊分頁裡沒有付款方式選擇器（沒有 payment_method 欄位、沒有 radio 選項）', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c \'payment_method\\|type="radio"\' master -- src/pages/entrustedContracts/edit/requirement/Payment.jsx', 'result': '0 筆', 'positive_control': '同檔 grep -c "t(\'現金收付\')" 命中 2 筆，證明檔案讀得到內容、grep 條件有效，只是選擇器本身確實不存在'}`

### 委託合約檢視頁面能做什麼？（查看歸檔資料、上傳既有委託合約檔案、未簽署前可返回編輯）
- 講法：委託合約檢視頁面看得到什麼／委託合約上傳檔案／委託合約還沒簽名可以改嗎
- 給誰看：property_manager
- 委託合約檢視頁面會顯示這份合約的「歸檔資料」，如果還沒上傳合約檔案，會提示「您尚未上傳合約檔案」；上傳後會顯示「檔案已上傳」。〔src/pages/entrustedContracts/show/Index.jsx〕
- 「返回編輯」按鈕只有在合約狀態是「待發送委託約」（尚未寄出邀請）時才會顯示；一旦狀態變成「待房東簽回」或之後，這個按鈕就會消失，不能再回到編輯畫面。〔src/pages/entrustedContracts/show/Index.jsx〕
- 頁面上方也有「合約總表」連結，可以快速回到委託合約列表。〔src/pages/entrustedContracts/show/Index.jsx〕
- 否定查證：`{'claim': '委託合約狀態不是「待發送委託約」（STATUS_READY=1）時，檢視頁面上不會顯示「返回編輯」按鈕', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "contract_info?.status === 1" master -- src/pages/entrustedContracts/show/Index.jsx', 'result': '命中 2 筆，皆為同一個 v-if 條件（外層 tools 區塊、內層按鈕本體），都以 === 1 做嚴格比對，狀態不是 1 時整個按鈕區塊不會渲染', 'positive_control': '同檔 grep -n "t(\'返回編輯\')" 命中 1 筆，證明按鈕文字本身確實存在於檔案裡，不是查詢路徑寫錯，只是外層有狀態條件包住'}`

### 委託合約怎麼建立？（委託合約列表頁「建立委託約」按鈕，需有建立合約權限，可選客製化契約書或紙本簽約）
- 講法：委託合約怎麼建立／委託合約建立入口
- 給誰看：property_manager
- 在委託合約列表頁，如果目前登入身分有建立合約的權限，右上角會出現「建立委託約」按鈕（搜尋結果畫面不會顯示這個按鈕）。〔src/pages/entrustedContracts/list/_parts/PageTop.jsx〕
- 點選「建立委託約」會彈出視窗，可以選擇「電子合約－客製化契約書」或「紙本簽約」兩種方式（委託合約沒有內政部公版電子合約選項）；選好之後會先進入物件挑選頁，選定物件後才進入委託合約編輯畫面繼續填寫。〔src/pages/entrustedContracts/list/_parts/PageTop.jsx〕
- 否定查證：`{'claim': '搜尋結果畫面（entrustedContracts.search）不會顯示「建立委託約」按鈕', 'grep': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n 'isSearchScreen' master -- src/pages/entrustedContracts/list/_parts/PageTop.jsx", 'result': '命中 2 筆：isSearchScreen 的定義（判斷目前路由是否為 entrustedContracts.search），以及「建立委託約」按鈕外層 && !state.isSearchScreen 的顯示條件，搜尋畫面時這個條件為否、按鈕不會渲染', 'positive_control': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c 'add_contract' master -- src/pages/entrustedContracts/list/_parts/PageTop.jsx 命中 1 筆，證明檔案內容讀得到、grep 條件有效，只是另外還有一層搜尋畫面的排除條件"}`
- 否定查證：`{'claim': '委託合約的建立合約彈窗沒有「內政部公版電子合約（contractCreate）」這個選項', 'grep': 'git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -n "isHiddenItem={\\[\'contractCreate\'\\]}" master -- src/pages/entrustedContracts/list/_parts/PageTop.jsx', 'result': '命中 1 筆，委託合約列表頁把 contractCreate 這個選項傳進 isHiddenItem，彈窗元件會把它從可選清單濾掉', 'positive_control': "git -C /Users/chenqinghuang/dev/work/jgb2/dev2 grep -c 'contractCreate:' master -- src/components/Lightbox/SelectContractMethod.jsx 命中 1 筆，證明 contractCreate 這個選項本來確實存在於元件的選項清單裡，只是被委託合約頁面指定隱藏"}`
