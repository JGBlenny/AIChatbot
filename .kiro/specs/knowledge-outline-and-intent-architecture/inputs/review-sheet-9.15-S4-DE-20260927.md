# 審核單 Plan 9.15 S4：D 租約／E 帳務 業主終審（依粗目整組）

> **終點指標**：已審細目 pm 0／535、prospect 0／121。本單每組你回「過」⇒ 該組 `pass` 細目全數標已審。
> `doubt` 細目逐條選：**本批不審**（預設；列入 Plan 9.16 待修）或 **照原樣過**。⛔ 本片不改內容。
> 代理先審＝fresh verifier 逐句對源＋可答性＋本線已知錯型；理由一句，證據在 session 紀錄。doubt 比例 >30% 的組標 ⚠️（建議整組本批不審）。
> 本單涵蓋 15／17 個粗目：pass 115、doubt 61。尚未先審：E-virtual-account、E-payment-onboarding


## D-contract-list｜合約列表與搜尋（11 條：pass 8／doubt 3）

**pass（回「過」即標已審）**：
- `jgb/D/contract-list-status-tabs`｜合約列表有哪些狀態頁籤？（待發送合約／待租客簽回／待房東簽名／執行中合約／歷史合約）
- `jgb/D/contract-search-keyword-scope`｜合約列表怎麼搜尋合約？（案名／地址／租客／ID／手機／信箱六種關鍵字，另有進階搜尋）
- `jgb/D/contract-create-estate-completeness-requirement`｜物件要先刊登廣告才能建立合約嗎？（現行規則是必填欄位要填齊，不是看刊登狀態）
- `jgb/D/contract-list-row-gear-actions`｜合約總表列的小齒輪可以做什麼操作？（不論狀態都有「查看物件」「查看帳單」；其餘依合約狀態、身分與權限增減）
- `jgb/D/contract-list-row-sort-options`｜合約總表可以怎麼排序？（依名稱、更新時間、合約起始日、終止日、成立日，各分新舊／早晚，共 5 種依據）
- `jgb/D/contract-list-deposit-alert`｜合約總表的待退押金提示燈號是什麼意思？（合約到期前 30 天才能點退）
- `jgb/D/contract-list-bill-currency-column`｜合約總表什麼時候會多出「帳單幣別」欄？（只有在批次建立帳單、挑選合約的頁面才會出現，一般檢視沒有這一欄）
- `jgb/D/contract-list-export-excel`｜合約總表可以匯出 Excel 嗎？（勾選後按「匯出合約」，需要匯出合約權限，內容含租期、每期租金、合約押金等欄位）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/contract-create-entry`｜怎麼建立一份新合約？（合約總表右上角「建立合約」，或物件總表小齒輪選建立合約）
  - 疑點：建立方式的介面標籤寫錯（實為「電子合約 - 住宅租賃契約書／客製化契約書／紙本簽約」），且社宅房東不跳選擇框
- `jgb/D/contract-list-columns`｜合約總表有哪些欄位？（含團隊自訂的「標籤」欄）
  - 疑點：標題問有哪些欄位，內容只講「標籤」一欄
- `jgb/D/contract-list-export-declaration`｜合約總表可以匯出實價登錄資料嗎？（只有在「執行中合約」頁籤、中文站台、且團隊開通此功能時才會出現按鈕）
  - 疑點：漏權限條件：匯出實價登錄按鈕需「新增合約」權限、搜尋結果頁不顯示

## D-contract-edit-general｜建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款）（23 條：pass 16／doubt 7） ⚠️ doubt 比例 30%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/D/contract-edit-tabs-overview`｜建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁）
- `jgb/D/contract-rentbasic-billing-cycle`｜「基本條件」分頁的繳費週期與帳單週期制度怎麼設定？（繳費週期／繳費截止日、當月分算或跨月計算、分算日）
- `jgb/D/contract-rentbasic-latefee`｜「基本條件」分頁的遲繳滯納金怎麼計算？（僅新北住都角色群組可見，兩段比例＋拖欠天數門檻，欄位唯讀）
- `jgb/D/contract-rent-deposit-two-modes`｜押金有哪幾種設定方式？（每月租金倍數／固定金額兩種計算基準）
- `jgb/D/contract-rent-adjustment`｜租金調幅設定分頁在做什麼？（依繳費期數設定固定金額或百分比調漲／調降）
- `jgb/D/contract-tax-invoice`｜稅與發票分頁怎麼設定？（是否開立發票、應稅品項、目前只支援租金品項開發票）
- `jgb/D/contract-payment-method`｜合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種）
- `jgb/D/contract-facilities-tab`｜附設傢俱分頁在做什麼？（設定家具責任歸屬，簽約後會帶入點交清單）
- `jgb/D/contract-situation-tab`｜現況補充分頁要寫什麼？（車位、屋況、漏水處等內政部規範現況細節）
- `jgb/D/contract-landlord-dealer-basic`｜出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、電子簽名圖章）
- `jgb/D/contract-building-transcript-optional`｜建物謄本分頁是選填的嗎？（選填，僅供合約內容完備使用，不會顯示在廣告頁）
- `jgb/D/contract-attachments-optional`｜合約附件分頁能上傳什麼？（各類文件圖片或 PDF，最大 10MB）
- `jgb/D/contract-additional-convention`｜補充條款有字數限制嗎？（最多 50 行、每行 50 字，可套用範本與複製其他合約）
- `jgb/D/contract-edit-building-transcript-visibility`｜「建物謄本」分頁什麼時候不會顯示？（只有選中／未選合約範本時才顯示，選到英越文或泰文版就會被拿掉）
- `jgb/D/contract-lease-scope-by-space-type`｜合約的租賃範圍怎麼決定？（物件空間型態為整戶時自動為「全部」，其餘一律「部分」，不用使用者勾選）
- `jgb/D/contract-tenant-code-change`｜承租人編碼要異動怎麼辦？（此操作需由 JGB 客服協助）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/contract-tenant-basic-info`｜承租方基本資料怎麼填？（個人／法人租客、租客註冊或免註冊、緊急聯絡人）
  - 疑點：把租客註冊／免註冊兩種模式混成一條（身份別、緊急聯絡人只在免註冊；新增租客只在註冊＋既存合約）
- `jgb/D/contract-rentbasic-template-and-dates`｜「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期）
  - 疑點：「合約類型」只在既存合約、「合約範本」只在電子合約，互斥；租賃訂約日期只在紙本／DIY
- `jgb/D/contract-rentbasic-tenant-language`｜「基本條件」分頁的租客慣用語系是什麼？（決定系統產生給租客的合約文件語系）
  - 疑點：租客慣用語系只在既存合約出現
- `jgb/D/contract-rentbasic-early-termination`｜合約的「可否提前解約」與違約金怎麼設定？（每月租金／固定金額／詳參補充條款／其他四種算法）
  - 疑點：漏特定合作團隊範本的例外（違約金設定只有一段、或整段被換掉）
- `jgb/D/contract-rent-fees`｜租金費用分頁要設定什麼？（租金、押金、自訂收入／支出費用、租金優惠、繳費週期優惠）
  - 疑點：句中寫出特定客戶名稱
- `jgb/D/contract-bill-setting`｜帳單設定分頁在做什麼？（預先編輯未來帳單的標題、金額、週期與自動執行動作）
  - 疑點：寫出客戶名稱，且把程式 TODO 註解寫成對外承諾
- `jgb/D/contract-edit-tabs-conditional-rules`｜合約編輯分頁會依什麼條件增減？（紙本／DIY 合約、車位、Meta Capital 範本、稅務發票資格皆會影響）
  - 疑點：無源推論（不支援公證的原因）＋客戶名稱＋把 TODO 寫成對外承諾

## D-contract-edit-social-housing｜建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般）（19 條：pass 11／doubt 8） ⚠️ doubt 比例 42%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/D/social-housing-photos-tab`｜社宅合約「現況照片」分頁一定要上傳嗎？（部分照片為必填，用來證明社宅內部現況設備存在）
- `jgb/D/social-housing-facilities-tab`｜社宅合約「附設傢俱」分頁要填什麼？（各格局家具與數量）
- `jgb/D/social-housing-subsidy-terms-tab`｜社宅合約「補助申請」分頁在做什麼？（配合社宅包租代管 333 補貼政策，出租方三種稅費減免）
- `jgb/D/social-housing-landlord-tabs-overview`｜社宅合約「出租方」分組有哪些分頁？（基本資料、授權、附件三個分頁）
- `jgb/D/social-housing-landlord-license-conditions`｜社宅合約「授權」分頁要確認什麼？（合法建物條件、同意提供住宅、同意轉租等授權事項）
- `jgb/D/social-housing-tenant-tabs-overview`｜社宅合約「承租方」分組有哪些分頁？（基本資料、家庭＆財產、授權、附件）
- `jgb/D/social-housing-tenant-household`｜社宅合約「家庭＆財產」分頁要登記什麼？（家庭成員、不動產與動產總額、最近年所得）
- `jgb/D/social-housing-tenant-license`｜社宅合約承租方的「授權」分頁要同意什麼？（財稅所得總檢核、家庭年所得百分位等資格條件）
- `jgb/D/social-housing-dealer-basic`｜社宅合約「業者」分頁在做什麼？（確認團隊資料與經理人資訊，有誤要回團隊資訊或帳號資訊修改）
- `jgb/D/social-housing-move-in-terms`｜社宅合約「點交證明文件」分頁在約定什麼？（點交狀態與修繕責任的預先約定，不是簽約後實際執行的點交）
- `jgb/D/social-housing-charter-sublet-tab-hiding`｜社宅合約選「包租包管」或「轉租」範本，分頁會不同嗎？（包租包管隱藏承租方戶籍/證照/附件，轉租隱藏出租方證照/附件）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/social-housing-building-detail`｜社宅合約「建物標的」分組有哪些分頁？（建物細節、現況補充、現況照片、附設傢俱四個分頁）
  - 疑點：只說回物件編輯修改；實際要先刪合約、改物件、再重建合約
- `jgb/D/social-housing-rent-basic-conditions`｜社宅合約「基本條件」要填什麼？（合約範本、委託期間、住宅現況、物件返還狀態、代收定金、爭議處理）
  - 疑點：委託期間等多個欄位在包租包管／轉租範本不顯示，寫成每份都要設；「是否帶租約」歸類錯
- `jgb/D/social-housing-early-termination-difference`｜社宅合約的提前解約說明文字跟一般合約不同（只顯示少於預告天數需付違約金的情境，沒有達門檻天數的減免說明）
  - 疑點：講的是特定合作團隊的一般合約範本，不是社宅合約頁；含客戶名稱
- `jgb/D/social-housing-rent-fees-tab`｜社宅合約「租金費用」分頁要填什麼？（代租金額／租金與押金／生活費用）
  - 疑點：「代租金額」只在代租代管範本；包租包管是「包租金額」、轉租兩者皆無
- `jgb/D/social-housing-payment-method-tab`｜社宅合約「收款方式」怎麼設定？（轉帳、票據、現金三種，收款人可選原房東或業者）
  - 疑點：「收款人」欄只在代租代管範本，句子說法與程式相反
- `jgb/D/social-housing-notary`｜社宅合約一定要公證嗎？（預設應辦理公證，可填理由不辦但視同放棄公證費補助；辦理公證後需下載文件紙本簽署再上傳歸檔）
  - 疑點：「保證人效力」是固定文字不是欄位；「強制執行」選項只在包租包管；句 4 照幫助中心寫「公證必要」違反 #28 裁決
- `jgb/D/social-housing-attachments-tab`｜社宅合約「合約附件」要準備什麼？（測量成果圖、稅籍證明等，出租方與承租方各自也有附件上傳分頁）
  - 疑點：合約附件分頁現只有「其他」一項，測量成果圖在出租方附件分頁
- `jgb/D/social-housing-tenant-basic-status`｜社宅合約「基本資料」怎麼審核租客資格？（低收入戶、中低收入戶等身分別選項）
  - 疑點：「新增代理人」包租包管範本不顯示；兩個欄位的選項混成一份

## D-contract-sign-view｜簽約與合約檢視（9 條：pass 5／doubt 4） ⚠️ doubt 比例 44%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/D/contract-esign-no-extra-fee`｜電子簽章簽約要另外收費嗎？（系統內沒有簽章計費機制，簽約流程無付費／加購畫面）
- `jgb/D/contract-locked-after-signing`｜合約簽約後可以修改嗎？（送出前可編輯、簽名前可取消簽名重編，簽署完成即無法更改，需重新簽一份新合約）
- `jgb/D/contract-show-panels`｜合約檢視頁面看得到什麼？（出／承租方資訊、業者、經理人資訊，以及點交點退進行中的提示）
- `jgb/D/contract-upload-existing-vs-electronic`｜上傳既有合約跟建立電子合約差在哪？（既存合約用於已簽好或有自己公版合約的情境，皆可續用系統帳務／修繕追蹤）
- `jgb/D/contract-guarantor-add-after-signing`｜簽約後可以補加保證人嗎？（租客簽約流程本身就能加連帶保證人；簽約完成後要補加，業者端沒有自助功能，需洽 JGB 客服協助）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/contract-invite-and-review-period`｜合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效，天數為團隊可調整設定）
  - 疑點：「換裝置不會自動綁定」依賴程式疑似缺陷（Email 比對以明文對密文、新資料應比不到）；兩位 verifier 見解相反，建議改寫成不下絕對結論
- `jgb/D/contract-sign-flow-steps`｜租客簽約要經過哪些步驟？（承租方簽約資料、上傳身分證明文件與印章、部分合約範本另有條款勾選、雲想科技畫面簽名）
  - 疑點：一般範本「下一步」先進預覽頁、自動扣款先跳授權；身份證明文件只有客製範本必填
- `jgb/D/contract-show-paper-upload-archive`｜上傳既有（紙本）合約檔案有什麼限制？（PDF、最大 10MB，依合約／續約／終止合約分類歸檔）
  - 疑點：歸檔上傳區是給「免註冊租客且已簽」的合約本文歸檔，不是給紙本既有合約
- `jgb/D/contract-show-creditcard-auth-prompt`｜合約檢視頁面會提示信用卡自動扣款授權嗎？（收款設定需要信用卡自動扣款時才會提示前往授權）
  - 疑點：合約檢視頁的授權提示沒有接上觸發；實際出現在租客簽約頁

## D-move-in｜點交（7 條：pass 6／doubt 1）

**pass（回「過」即標已審）**：
- `jgb/D/move-in-checklist-and-responsibility`｜點交清單怎麼確認？（依合約約定的傢俱項目逐一上傳照片、標註出租方或承租方負責）
- `jgb/D/move-in-meter-readings`｜點交要填另計費用起始度數嗎？（依合約設定另計的費用項目要輸入起始度數，會直接帶入日後帳單計算）
- `jgb/D/move-in-blocked-states`｜點交送出後還能再送一次嗎？（已完成點交無法再次送出；已送出、等待租客確認中的清單要先取消邀請才能改）
- `jgb/D/move-in-cancel-invite`｜點交邀請送出後可以取消嗎？（可以，系統會記錄「取消點交邀請」這個動作）
- `jgb/D/move-in-result-pdf`｜點交結果能下載 PDF 嗎？（有專屬頁面可以檢視或下載點交 PDF）
- `jgb/D/move-in-optional-and-timing`｜點交是必要流程嗎？（點交是選擇性操作，未點交也能發帳單；簽約完成後即可在執行中合約選取物件點交）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/move-in-page-general-vs-social-housing`｜點交頁面一般合約跟社宅合約用的是同一個嗎？（不是，一般住宅合約用一般合約的點交頁面，社宅合約會被導向社宅合約的點交頁面）
  - 疑點：流程寫反：點交頁是填寫送出的頁面，送出後導回合約檢視

## D-move-out｜點退（7 條：pass 4／doubt 3） ⚠️ doubt 比例 43%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/D/move-out-checklist-and-damage`｜點退清單怎麼處理設備損壞？（可編輯填入賠償金額與理由，過程可儲存草稿）
- `jgb/D/move-out-eligibility-conditions`｜什麼合約可以點退？（合約狀態須為執行中／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外）
- `jgb/D/move-out-remains-in-active-list`｜點退完成的合約為什麼還在「執行中合約」？（只要還沒到合約到期日就會留在執行中，到期後才轉入歷史合約）
- `jgb/D/move-out-tenant-no-response-cancel`｜租客不確認點退時要怎麼辦？（系統不會逾期自動放行，只能由房東取消點退邀請後重新發送）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/move-out-bill-generation`｜點退會產生什麼帳單？（含提前解約金、點退押金、賠償金，設定期限後發送，租客確認並繳款才算完成）
  - 疑點：第一步介面標題是「點退清單」，句子寫「點交清單」且前後不一
- `jgb/D/move-out-timing-window`｜點退的時間限制是什麼？（合約到期前 30 天起可以點退，過了到期日之後目前沒有再設上限）
  - 疑點：把程式註解裡的內部變更史寫成對外知識（過程筆記）
- `jgb/D/move-out-fee-adjustment-step`｜點退第二步「點退找補費用」頁面要填什麼？（傢俱賠償、應退費用、違約金，另可填備註、期限、附件）
  - 疑點：取自已不再使用的舊元件標題；現行只有「傢俱賠償」

## D-renew｜續約（8 條：pass 6／doubt 2）

**pass（回「過」即標已審）**：
- `jgb/D/renew-batch-entry-and-selection`｜怎麼一次幫多筆合約續約？（合約總表「建立合約」旁選批次續約，異動中的合約不能選）
- `jgb/D/renew-preview-bill-generation`｜續約可以預先編輯帳單嗎？（續約預覽頁可先編輯續約期間帳單，實際帳單於完成續約後才產生）
- `jgb/D/renew-signing-flow`｜續約邀請發出後流程是什麼？（租客簽回後可在「待租客簽回」查找，房東確認無誤後立即簽名完成續約）
- `jgb/D/renew-invite-review-days`｜續約邀請效期是幾天？（預設 3 天，團隊可覆蓋設定）
- `jgb/D/renew-data-carryover-rules`｜續約時資料怎麼沿用？（新合約由舊合約複製，並更新出租方/承租方最新資料；週期設定有調整就用新的、沒調整就沿用）
- `jgb/D/renew-deposit-difference-handling`｜續約押金差額怎麼處理？（一般續約第一張帳單不列押金；只有特定合作團隊的延長續約會用原押金算差額；新合約無法直接沿用舊合約押金，一律列全額押金）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/renew-date-setting-modes`｜續約日期怎麼設定？（快速日期設定一次套用全部，或個別指定每份合約的續約日）
  - 疑點：快速日期設定是各合約自到期日加 N 個月，且只在多選時出現
- `jgb/D/renew-upload-paper-signed`｜續約可以上傳紙本已簽合約嗎？（可以，提供雙方已完成簽約的紙本合約掃描檔即可）
  - 疑點：上傳區只在單選且為既存合約時出現；電子圖章是另一開關、只對法人房東

## D-early-termination｜提前解約（6 條：pass 3／doubt 3） ⚠️ doubt 比例 50%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/D/early-termination-eligibility`｜什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起）
- `jgb/D/early-termination-effect-move-out`｜提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金）
- `jgb/D/early-termination-billing-after`｜提前解約後還會出新帳單嗎？（解約日之後系統不會再自動產生新租金帳單；已產生、落在解約日後的帳單要業者自行封存）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/early-termination-reasons`｜房東申請提前解約要選什麼理由？（新版中文合約有 10 項法定理由可選，其餘合約只能選「其他」）
  - 疑點：文字框固定顯示、未選「其他」時停用，句子說不出現
- `jgb/D/early-termination-form-fields`｜申請提前解約要填什麼？（欲提前解約日須早於原合約到期日、違約金由誰付、佐證資料）
  - 疑點：引號標籤不存在（實為「預計提前解約日」「支付方」）；違約金可不填
- `jgb/D/early-termination-tenant-cancel`｜誰可以取消已送出的提前解約申請？（房東透過小齒輪取消，租客只有在提前解約確認中狀態才能取消）
  - 疑點：齒輪選項實名「取消提前解約」，非「取消提前終止合約」

## D-notary｜租約公證（公證分頁與公證服務）（3 條：pass 1／doubt 2） ⚠️ doubt 比例 67%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/D/contract-thinkcloud-signing-variants`｜雲想科技簽署畫面依合約類型有什麼差異？（公會版本合約加補充條款多一個協商條款簽名框；DIY 客製化合約解析失敗時會顯示提示訊息，不會直接出現系統錯誤畫面）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/general-contract-notary-tab`｜一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項，僅支援中文合約）
  - 疑點：「保證人效力」是自動組出的說明文字、不可設定；標題「僅支援中文」超出來源
- `jgb/D/contract-thinkcloud-esign-service`｜簽約時進入的雲想科技頁面是做什麼的？（承載 Thinkcloud 電子簽署流程的內嵌頁面，一般合約、委託合約皆會用到）
  - 疑點：現行直接導向 Thinkcloud 網址，不是內嵌頁

## D-entrust-contract｜委託合約（列表、建立編輯、檢視）（11 條：pass 5／doubt 6） ⚠️ doubt 比例 55%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/D/entrusted-contract-what-is-it`｜委託合約是什麼？（房東委託業者包租代管的合約，跟業者與租客之間的租賃合約是不同份文件）
- `jgb/D/entrusted-contract-tabs-overview`｜委託合約編輯畫面有哪些分頁？（房東資訊、委託條件三頁、管理方資訊共 3 組 5 頁）
- `jgb/D/entrusted-contract-preview-to-show`｜委託合約編輯完成後怎麼進入簽署？（點右上角「預覽合約」先儲存資料，再進入檢視頁面）
- `jgb/D/entrusted-contract-fees`｜委託合約的收費分頁要設定什麼？（服務費或包租金額的計算模式與週期，押金提示不得超過兩個月租金）
- `jgb/D/entrusted-contract-payment`｜委託合約收付款資訊怎麼設定？（沒有選擇器，固定顯示「出租方帳戶」與「管理方帳戶」兩個現金收付區塊，後者必填）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/D/entrusted-contract-lease-type`｜委託合約「包租」跟「代管」有什麼不同？（代管必填服務費計算模式、幣別與金額或比例；計算制度、週期、約定日期兩者都要填）
  - 疑點：「委託約範本」只在電子 DIY 委託約；紙本換成上傳「委託約檔案」
- `jgb/D/entrusted-contract-upload-file-size-limit`｜委託合約上傳既有檔案限制多大？（6MB，比一般合約的 10MB 小）
  - 疑點：畫面寫 6MB，但上傳元件實際上限 10MB
- `jgb/D/entrusted-contract-landlord-info`｜委託合約的房東資訊怎麼填？（房東註冊或房東免註冊、選擇個人房東或法人房東身份）
  - 疑點：「出租方身份別」與加密提示只在房東免註冊時出現
- `jgb/D/entrusted-contract-manager-info`｜委託合約的經理人資訊分頁要填什麼？（公司基本資料、指定經理人、租賃住宅管理人員名稱與證號、電子簽名圖章）
  - 疑點：管理人員名稱證號是帶出顯示、不能在此填；順序寫反
- `jgb/D/entrusted-contract-show-and-upload`｜委託合約檢視頁面能做什麼？（查看歸檔資料、上傳既有委託合約檔案、未簽署前可返回編輯）
  - 疑點：標題說未簽署前可返回編輯，實際只有尚未寄出邀請時可以
- `jgb/D/entrusted-contract-create-entry`｜委託合約怎麼建立？（委託合約列表頁「建立委託約」按鈕，需有建立合約權限，可選客製化契約書或紙本簽約）
  - 疑點：客製化契約書走 DIY 合約頁，與紙本流程不同；標籤符號不符

## E-bill-list｜帳單列表與帳單狀態（33 條：pass 24／doubt 9）

**pass（回「過」即標已審）**：
- `jgb/E/bill-list-tabs`｜帳單列表分成哪些分頁？（帳單總表／草稿帳單／收款帳單／支出帳單／總收支）
- `jgb/E/bill-status-tabs-landlord`｜「草稿帳單」「收款帳單」「支出帳單」分頁底下各分哪些狀態？
- `jgb/E/bill-status-tabs-tenant`｜租客的帳單列表跟房東的有什麼不同？（只有收款帳單／支出帳單兩個分頁）
- `jgb/E/bill-actions-scheduled`｜「排定發送」狀態的帳單可以做哪些動作？（只有「取消排定發送」）
- `jgb/E/bill-actions-archived`｜「封存」狀態的帳單可以做哪些動作？（沒有任何動作，齒輪選單是空的）
- `jgb/E/bill-actions-expense-unpaid`｜「應支出」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：付款）
- `jgb/E/bill-actions-expense-unconfirmed`｜「待對帳」狀態的支出帳單，房東跟租客各能做什麼？（房東：前往付款／通知已匯款／取消帳單；租客：沒有齒輪動作）
- `jgb/E/bill-actions-expense-paid`｜「已支出」狀態的支出帳單，房東跟租客各能做什麼？（房東一律有編輯收款備註／封存；反轉帳單才多出收據／退款對帳單）
- `jgb/E/bill-expired-status`｜帳單狀態顯示「已失效」是什麼意思？（限電錶儲值帳單，4 天繳費期限）
- `jgb/E/bill-list-keyword-search`｜帳單列表怎麼用關鍵字搜尋？（可指定用案名／地址／租客／ID／手機／信箱／帳單名稱／虛擬帳號／合約帳單共 9 種比對）
- `jgb/E/bill-list-export`｜帳單總表怎麼匯出？（要先勾選帳單才會出現匯出選項；全選走篩選條件、勾選部分筆數走ID清單；其他分頁另有一套匯出流程）
- `jgb/E/bill-list-bulk-action-intersection`｜帳單總表勾選多筆不同狀態的帳單時，批次操作列會出現哪些動作？（只列出每一筆帳單都能做的共同動作）
- `jgb/E/bill-list-income-export-social-housing`｜「收款帳單」分頁固定的匯出按鈕，什麼時候會多出「匯出租客繳費證明」子選項？（只有身分類別為社會住宅的帳號才有）
- `jgb/E/bill-list-special-team-cvs-buttons`｜「應到帳」「已到帳」狀態，特定合作團隊的帳號會多出哪些按鈕？（應到帳：匯入發票；已到帳：匯出收據／匯入收據／批次匯出收據）
- `jgb/E/bill-balance-tab-export-submenu`｜「總收支」分頁的匯出按鈕，特定合作團隊的帳號會多出什麼子選項？（匯出收支明細表）
- `jgb/E/bill-list-batch-shortcuts`｜「草稿帳單」分頁右上角有哪些批次建立帳單的快捷按鈕？（新增週期帳單／新增批次帳單／排定發送帳單／批次編輯帳單，Excel新增帳單僅限特定合作團隊；帳單總表沒有這些按鈕）
- `jgb/E/bill-scheduled-send-rule`｜「排定發送帳單」有什麼限制？（只有度數填完的帳單才能排，每天中午 12 點統一發送）
- `jgb/E/bill-notify-channels`｜帳單通知走哪些管道？通知對象是誰？（免註冊租客可分別開關 Email／簡訊，已註冊租客固定收 Email 與站內通知、已綁定 LINE／FB 另收推播；只發給帳單本身的那位承租人）
- `jgb/E/bill-invoice-void-limitation`｜發票可以線上作廢嗎？（可在帳單詳細頁作廢，但只支援 ezPay；其他金流商的發票作廢不了，已開折讓的發票也不能再作廢）
- `jgb/E/bill-archive-precondition`｜帳單要什麼狀態才可以直接封存？（「待發送」跟「已到帳」都可以直接封存，不用先轉成已到帳；可勾選多筆一次封存）
- `jgb/E/bill-deposit-receipt-no`｜押金收據號碼是系統自動產生的嗎？（特定合作團隊的客製功能，號碼透過 Excel 匯出／匯入手動填寫，系統不會自動編流水號）
- `jgb/E/bill-scheduled-contract-ended-guard`｜合約已結束、但底下還留著未來計費期間的租金帳單，系統排定發送時會怎麼處理？（系統自動排定發送／自動寄出都會跳過不寄，但不會刪除帳單；業者手動排定發送則不受這條規則限制；批次寄出依帳單 id 由小到大處理，沒有可指定的發送順序）
- `jgb/E/bill-remind-resend-by-support`｜業者可以請 JGB 客服代發催繳通知嗎？（此操作需由 JGB 客服協助；業者端沒有自助重發催繳的介面）
- `jgb/E/bill-cvs-barcode-overdue-payment`｜超商代碼繳費逾期後才繳，帳單還會入帳嗎？（系統不檢查代碼期限，完全依金流商回傳的付款結果；代碼逾期後是否還能繳費屬外部規定，系統不判斷）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/E/bill-actions-draft`｜「草稿」狀態的帳單可以做哪些動作？（編輯／發送／移至已到帳／封存）
  - 疑點：「草稿可直接移至已到帳」漏特定合作團隊例外（該選項被拿掉）
- `jgb/E/bill-actions-unreceived`｜「應到帳」狀態的收款帳單可以做哪些動作？（匯款資訊／移至已到帳／開立發票／取消帳單）
  - 疑點：「一律可移至已到帳」漏特定合作團隊例外
- `jgb/E/bill-actions-progress`｜「待對帳」狀態的收款帳單可以做哪些動作？（退至應到帳／移至已到帳／開立發票，沒有取消帳單）
  - 疑點：單筆與批次的「移至已到帳」都漏特定合作團隊例外
- `jgb/E/bill-actions-received`｜「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單）
  - 疑點：「發票」按鈕看合約層設定而非帳單；eCloud 發票開登入頁；收據附件漏特定團隊例外
- `jgb/E/bill-list-export-other-tabs`｜「草稿帳單」「支出帳單」「總收支」分頁的匯出按鈕，跟帳單總表不是同一套（不需要先勾選，走另一個較舊的匯出流程）
  - 疑點：排定發送／封存／已失效三個頁籤沒有匯出按鈕，句子寫一律有
- `jgb/E/bill-single-notification-deeplink`｜帳單通知信裡的連結點進去會看到什麼？（單張帳單以彈窗顯示，不會跳到完整列表）
  - 疑點：「該帳單不存在」提示出自舊路由，現行通知連結走列表＋彈窗
- `jgb/E/bill-balance-tab`｜「總收支」分頁的用途是什麼？（同時看全部已到帳、已支出、應到帳、應支出的帳單）
  - 疑點：標題說可同時看已到帳與應到帳等，實際「全部」只含已完成帳單
- `jgb/E/bill-notify-remittance-visibility`｜「通知已匯款」按鈕什麼時候才會出現？（只在非線上金流收款的帳單才有，改走線上金流收款就不顯示）
  - 疑點：介面路徑是幫助中心舊說法（現行為「帳務管理」→「繳費帳單」）；房東端應支出帳單的「通知已匯款」無線上金流條件
- `jgb/E/bill-receipt-feature-roadmap`｜收據功能還會不會有新的開發？（現行已到帳帳單一律可以看到系統寄送的收據，目前沒有公開的後續開發時程）
  - 疑點：收據附件漏特定合作團隊例外

## E-bill-create-edit｜建立與編輯帳單（單筆、批次、週期批次）（16 條：pass 8／doubt 8） ⚠️ doubt 比例 50%，建議整組本批不審

**pass（回「過」即標已審）**：
- `jgb/E/bill-create-modes`｜新增帳單有哪幾種頁面？（新增帳單／新增批次帳單／新增週期帳單／編輯帳單）
- `jgb/E/bill-cycle-schedule-fields`｜新增週期帳單的「繳費週期」設定要填哪些欄位？（繳費週期／繳費截止日／截止日設定／帳單週期制度）
- `jgb/E/bill-title-field`｜「帳單標題」最多可以輸入幾個字？（45 個字）
- `jgb/E/bill-remark-field`｜「帳單備註」最多可以輸入幾個字？（150 個字）
- `jgb/E/bill-internal-note-field`｜「內部備註」最多可以輸入幾個字？誰看得到？（100 個字，僅供業者團隊成員查看／編輯，租客看不到）
- `jgb/E/bill-payment-method-account-pair`｜新增帳單時付款方式跟收款帳戶一定要一起填嗎？（兩者要嘛都空、要嘛都填；固定虛擬帳號例外）
- `jgb/E/bill-tenant-unverified-draft-lock`｜租客還沒完成驗證時，發給他的帳單會怎樣？（帳單卡在草稿分頁，發不出去；但可以手動移至應到帳/已到帳）
- `jgb/E/bill-partial-month-proration`｜不足一個月的租金怎麼算？（依天數比例；預設團隊以剩餘天數 ÷ 該月曆天數，逐月產帳以實際天數 ÷ 該期帳單天數，不是固定除以 30）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/E/bill-create-target`｜新增帳單時「對象」可以選哪些？（租客／大房東／物件／其他）
  - 疑點：切換對象後只有租客會帶入預設值，其餘維持清空；且只在單筆新增頁
- `jgb/E/bill-batch-vs-cycle`｜「新增批次帳單」跟「新增週期帳單」有什麼不同？（挑租客合約 vs 挑物件）
  - 疑點：兩種頁面都可切租客／物件；週期帳單是一次批次產出各期，不是之後自動反覆產生
- `jgb/E/bill-cycle-amortization`｜「總額（自動分攤）」欄位什麼時候才會出現？（只有新增週期帳單、且團隊開通社區投報率時）
  - 疑點：預設「每期金額」是填同一個數，不是逐期分別填
- `jgb/E/bill-fee-item-rules`｜帳單費用細目填寫有什麼規則？（度數欄位最多小數點後 2 位、電水瓦斯金額欄位限制小數點後 2 位、當期度數不可小於上期度數）
  - 疑點：檢查在離開欄位時觸發，不是一邊輸入即時提示
- `jgb/E/bill-internal-note-visibility`｜「內部備註」欄位在哪些頁面會出現？（只有「新增帳單」單筆跟「編輯帳單」有，批次／週期帳單頁面不顯示）
  - 疑點：帳單列表與詳細彈窗也會顯示內部備註；條件是看的人是否為管理方團隊成員
- `jgb/E/bill-submit-button-behavior`｜新增帳單頁面下方送出按鈕的文字跟行為會依情境改變（送出／發送簽核／簽核中／預覽帳單）
  - 疑點：「發送簽核」只有特定合作團隊會走
- `jgb/E/bill-contract-payment-prefill`｜新增帳單選租客當對象時，付款方式會自動帶入合約的收款設定嗎？（會，但帳戶已停用/不可取號等情況不會亂猜）
  - 疑點：固定虛擬帳號合約綁定有效時會帶入，句子說不會
- `jgb/E/bill-power-reading-draft-defaults`｜草稿帳單的電費度數要自己填嗎？（草稿階段度數預設留空，可在編輯頁按「取得即時電錶度數」先帶入）
  - 疑點：「取得即時電錶度數」只在綁智慧電表時出現，特定合作團隊隱藏

## E-bill-stats｜帳單統計與報表（3 條：pass 3／doubt 0）

**pass（回「過」即標已審）**：
- `jgb/E/bill-stat-overview`｜「統計報表」的「當前表現」分頁顯示什麼？（收款情況／支出情況卡片）
- `jgb/E/bill-stat-monthly-tabs`｜統計報表除了「當前表現」，還有「每月報表」「每月對帳單」分頁，但只有特定合作團隊看得到
- `jgb/E/bill-monthly-report-upload`｜「每月報表」跟「每月對帳單」分頁在做什麼？（依社區/物件上傳與下載每月的物件報表、對帳單檔案）

## E-social-housing-report｜社宅報表（6 條：pass 5／doubt 1）

**pass（回「過」即標已審）**：
- `jgb/E/social-housing-sheet-list`｜社宅報表的「清冊列表」在列什麼？（每個媒合編號底下的表單勾選與修繕費、申請期數）
- `jgb/E/social-housing-sheet-contract-version`｜社宅報表上方的合約版本切換列是做什麼用的？（切換不同版本的社宅合約，每次查詢都會帶著這個版本一起送出）
- `jgb/E/social-housing-sheet-make-form`｜社宅報表怎麼製作表單？（填撥款日、勾選表單後按「製作表單」，會記錄成清冊紀錄）
- `jgb/E/social-housing-sheet-export-history`｜社宅報表的「匯出歷史」會記錄幾筆匯出動作？（系統至多記錄近 30 筆）
- `jgb/E/social-housing-sheet-archive`｜社宅報表的「歸檔」是什麼意思？（操作按鈕是「確定歸檔」；綠色「歸檔」標籤只在已歸檔後才出現）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/E/social-housing-sheet-program-scope`｜社宅報表的「社會住宅」身份可以對應到哪個地方政府的社宅方案？（系統只定義身份類別，不判斷方案適配）
  - 疑點：裁決句無 evidence 對應；程式有社宅合約期別版本與報表版本相關

## E-balance-invoice｜差額發票（群組、底租、社區層開關）（14 條：pass 10／doubt 4）

**pass（回「過」即標已審）**：
- `jgb/E/balance-invoice-group-statuses`｜差額發票群組總表有哪些狀態？（尚未生效／進行中／歷史／封存）
- `jgb/E/balance-invoice-list-columns`｜差額發票群組總表列表裡看得到哪些欄位？（ID／出租物件數／本月發票狀態／累積成本／累積收入／累積發票金額）
- `jgb/E/balance-invoice-group-basic-info`｜建立差額發票群組要填哪些基本資料？（群組名稱／底租／租期／前期餘額／房屋座落地址／房屋稅籍編號）
- `jgb/E/balance-invoice-group-detail-tabs`｜差額發票群組詳細頁面看得到什麼？（招租數量／本月應收金額／本月已收金額，以及三個分頁）
- `jgb/E/balance-invoice-timing`｜差額發票什麼時候自動產生？（一般業者每月 1 日 03:00 開立上月發票；特定團隊另有自己的時程）
- `jgb/E/balance-invoice-refund-report-column`｜差額發票收支表的租金退款／減免怎麼呈現？（列在「租金增(減)(B)」欄，以負數表示）
- `jgb/E/balance-invoice-rent-item-rule`｜差額發票收支表怎麼判斷一個帳單品項算不算「租金」收入？（系統預設品項看名稱是不是「租金」「退租金」；自訂品項看品項性質）
- `jgb/E/balance-invoice-entity-type-change`｜身分從法人改成自然人後，差額發票群組要怎麼重新設定？（系統沒有專用的身分切換規則）
- `jgb/E/balance-invoice-unsigned-contract`｜合約還沒簽回時能不能開發票或收據？（發票看合約的開票設定、押金收據看帳單是否到帳，簽署狀態是否連動要看個案）
- `jgb/E/balance-invoice-anomaly-list`｜帳單不在任何差額發票群組內時，JGB 怎麼處理？（列進內部「發票異常盤查」名單，處理需洽客服）

**doubt（逐條：本批不審／照原樣過；預設本批不審）**：
- `jgb/E/balance-invoice-community-switch`｜社區怎麼開啟差額發票功能？（社區編輯頁的開關，設定底租總額幣別與每月租金）
  - 疑點：社區層開關是已淘汰舊功能且只給名單內團隊；現行是團隊層差額群組
- `jgb/E/balance-invoice-pick-and-individual-rent`｜差額發票群組怎麼加入物件？每個物件的底租可以自訂嗎？（可開「自訂個別底租」分配群組底租）
  - 疑點：「自訂個別底租」是整個群組一個開關，不是每個物件各自開
- `jgb/E/balance-invoice-monthly-invoice-table`｜「差額總表」裡每個月的差額怎麼看、怎麼開發票？（累積成本、累積收入、差額、是否開發票、發票金額、發票字軌）
  - 疑點：差額顯示為絕對值；標題問怎麼開發票未回答
- `jgb/E/balance-invoice-group-action-menu`｜差額發票群組列表的動作選單有哪些選項？各自什麼時候會被停用？（編輯群組／開立發票／封存群組／刪除群組；另有查看歷程圖示）
  - 疑點：停用選項是隱藏不是顯示停用；詳細頁「開立發票」一律隱藏；能否刪除看是否開過發票


## 裁決紀錄

業主 2026-09-27：「安全組過、⚠️組不審」「先寫入已審，B7 之後」。
- 過（pass 細目全數標已審，共 62 條）：D-contract-list 8、D-move-in 6、D-renew 6、E-bill-list 24、E-bill-stats 3、E-social-housing-report 5、E-balance-invoice 10
- 本批不審：8 個 ⚠️ 組（含其 pass 細目 53 條）與全部 61 條 doubt ⇒ 列 Plan 9.16 待修
- 未先審：E-virtual-account、E-payment-onboarding（B7，併入 9.16）
- 寫入：`- reviewed: {by: owner, at: 2026-09-27}`；fresh outcome verifier CONFIRMED
