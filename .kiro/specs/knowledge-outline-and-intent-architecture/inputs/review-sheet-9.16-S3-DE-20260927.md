# 審核單：Plan 9.16 S3 D／E 未審細目第二批代理先審（138 條）

> 審閱的正本版本：commit `3642733c`。本單由 `scratchpad/p916_s3_sheet.py sheet` 從 verifier 原始回覆解析結果機械產生，⛔ 手改。
> 合計：pass 98／doubt 40／未先審 0。
> 回覆方式（S4）：每組回「過」＝該組 **pass** 細目標已審；doubt 細目只能「本批不審」或「照原樣過」（逐條）。
> ⚠️＝該組 doubt 超過該組待審條數的 30%，建議整組本批不審。⛔ 標示「有未先審細目」的組不可整組回「過」。

## 合約列表與搜尋 `D-contract-list`（待審 3 條：pass 3／doubt 0／未先審 0）

- [pass] `jgb/D/contract-create-entry` 怎麼建立一份新合約？（合約總表右上角「建立合約」，或物件總表小齒輪選建立合約）
- [pass] `jgb/D/contract-list-columns` 合約總表有哪些欄位？（含團隊自訂的「標籤」欄）
- [pass] `jgb/D/contract-list-export-declaration` 合約總表可以匯出實價登錄資料嗎？（只有在「執行中合約」頁籤、中文站台、團隊開通此功能且帳號有建立合約權限時才會出現按鈕）

回覆：

## 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） `D-contract-edit-general`（待審 23 條：pass 17／doubt 6／未先審 0）

- [pass] `jgb/D/contract-tenant-basic-info` 承租方基本資料怎麼填？（個人／法人租客、租客註冊或免註冊、緊急聯絡人）
- [pass] `jgb/D/contract-rentbasic-billing-cycle` 「基本條件」分頁的繳費週期與帳單週期制度怎麼設定？（繳費週期／繳費截止日、當月分算或跨月計算、分算日）
- [pass] `jgb/D/contract-rentbasic-tenant-language` 「基本條件」分頁的租客慣用語系是什麼？（決定系統產生給租客的合約文件語系）
- [pass] `jgb/D/contract-rentbasic-early-termination` 合約的「可否提前解約」與違約金怎麼設定？（每月租金／固定金額／詳參補充條款／其他四種算法）
- [pass] `jgb/D/contract-rent-fees` 租金費用分頁要設定什麼？（租金、押金、自訂收入／支出費用、租金優惠、繳費週期優惠）
- [pass] `jgb/D/contract-rent-deposit-two-modes` 押金有哪幾種設定方式？（每月租金倍數／固定金額兩種計算基準）
- [pass] `jgb/D/contract-rent-adjustment` 租金調幅設定分頁在做什麼？（依繳費期數設定固定金額或百分比調漲／調降）
- [pass] `jgb/D/contract-bill-setting` 帳單設定分頁在做什麼？（預先編輯未來帳單的標題、金額、週期與自動執行動作）
- [pass] `jgb/D/contract-facilities-tab` 附設傢俱分頁在做什麼？（設定家具責任歸屬，簽約後會帶入點交清單）
- [pass] `jgb/D/contract-situation-tab` 現況補充分頁要寫什麼？（車位、屋況、漏水處等內政部規範現況細節）
- [pass] `jgb/D/contract-building-transcript-optional` 建物謄本分頁是選填的嗎？（選填，僅供合約內容完備使用，不會顯示在廣告頁）
- [pass] `jgb/D/contract-attachments-optional` 合約附件分頁能上傳什麼？（各類文件圖片或 PDF，最大 10MB）
- [pass] `jgb/D/contract-additional-convention` 補充條款有字數限制嗎？（最多 50 行、每行 50 字，可套用範本與複製其他合約）
- [pass] `jgb/D/contract-edit-tabs-conditional-rules` 合約編輯分頁會依什麼條件增減？（紙本／客製化契約書、車位、特定合作團隊範本、稅務發票資格皆會影響）
- [pass] `jgb/D/contract-edit-building-transcript-visibility` 「建物謄本」分頁什麼時候不會顯示？（只有選中／未選合約範本時才顯示，選到英越文或泰文版就會被拿掉）
- [pass] `jgb/D/contract-lease-scope-by-space-type` 合約的租賃範圍怎麼決定？（物件空間型態為整戶時自動為「全部」，其餘一律「部分」，不用使用者勾選）
- [pass] `jgb/D/contract-tenant-code-change` 承租人編碼要異動怎麼辦？（此操作需由 JGB 客服協助）
- [doubt] `jgb/D/contract-edit-tabs-overview` 建立一般合約有哪些分頁？（承租方資訊、租賃契約六項、點交兩項、出租方資訊、選填四項共 14 頁） —— 句序 7：句中說「稅與發票」只有在團隊沒開通自動產生發票時「才會」被拿掉，但車位合約不論有沒有開通，只要沒有特定角色也會拿掉這個分頁，程式有反例
- [doubt] `jgb/D/contract-rentbasic-template-and-dates` 「基本條件」分頁的合約範本與日期要怎麼設定？（合約範本／類型、合約起迄日期、租賃訂約日期） —— 句序 6：句中把「轉租合約」寫成一般合約範本可選的一種，但這個標籤只出現在社宅範本（sublet）；一般住宅的 12 種範本裡沒有「轉租合約」，只有「113年內政部轉租契約(包租轉租)」
- [doubt] `jgb/D/contract-rentbasic-latefee` 「基本條件」分頁的遲繳滯納金怎麼計算？（僅新北住都角色群組可見，兩段比例＋拖欠天數門檻，欄位唯讀） —— 句序 1：標題和句 1 直接寫出客戶名「新北住都」，應改成「特定合作團隊」（內容本身與程式相符）
- [doubt] `jgb/D/contract-tax-invoice` 稅與發票分頁怎麼設定？（是否開立發票、應稅品項、目前只支援租金品項開發票） —— 句序 0（標題）：標題把「目前只支援租金品項開發票」當成事實，但現行畫面上「押金設算息」（功能開關開啟時）和「生活費用計稅品項」都能設為應稅並開發票；內文句 3 只是轉述畫面提示，沒有問題
- [doubt] `jgb/D/contract-payment-method` 合約收款方式有哪幾種？（線上金流、現金收款、固定虛擬帳號三種） —— 句序 2：句中出現客戶名「Meta Capital 系列」，應改成「特定合作團隊的專用範本」
- [doubt] `jgb/D/contract-landlord-dealer-basic` 出租方基本資料分頁要填什麼？（個人／團隊資料自動帶入、指定經理人、電子簽名圖章） —— 句序 4：句中寫成出租方都能選電子簽名圖章，但這個功能只開放給法人房東；個人房東的分頁上不會出現這個區塊

回覆：

## 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） `D-contract-edit-social-housing`（待審 19 條：pass 7／doubt 12／未先審 0） ⚠️

- [pass] `jgb/D/social-housing-building-detail` 社宅合約「建物標的」分組有哪些分頁？（建物細節、現況補充、現況照片、附設傢俱四個分頁）
- [pass] `jgb/D/social-housing-photos-tab` 社宅合約「現況照片」分頁一定要上傳嗎？（部分照片為必填，用來證明社宅內部現況設備存在）
- [pass] `jgb/D/social-housing-subsidy-terms-tab` 社宅合約「補助申請」分頁在做什麼？（配合社宅包租代管 333 補貼政策，出租方三種稅費減免）
- [pass] `jgb/D/social-housing-tenant-household` 社宅合約「家庭＆財產」分頁要登記什麼？（家庭成員、不動產與動產總額、最近年所得）
- [pass] `jgb/D/social-housing-tenant-license` 社宅合約承租方的「授權」分頁要同意什麼？（財稅所得總檢核、家庭年所得百分位等資格條件）
- [pass] `jgb/D/social-housing-dealer-basic` 社宅合約「業者」分頁在做什麼？（確認團隊資料與經理人資訊，有誤要回團隊資訊或帳號資訊修改）
- [pass] `jgb/D/social-housing-move-in-terms` 社宅合約「點交證明文件」分頁在約定什麼？（點交狀態與修繕責任的預先約定，不是簽約後實際執行的點交）
- [doubt] `jgb/D/social-housing-facilities-tab` 社宅合約「附設傢俱」分頁要填什麼？（各格局家具與數量） —— 句序 1：社宅附設傢俱分頁不是按格局分別填家具。實際內容是：勾選「設備」、勾選是否有「隔間」，再填「家電」和「傢俱」各品項的整體數量，家電另外填廠牌/型號。格局只是一行提示文字
- [doubt] `jgb/D/social-housing-rent-basic-conditions` 社宅合約「基本條件」要填什麼？（合約範本、委託期間、住宅現況、物件返還狀態、代收定金、爭議處理） —— 句序 1：範本下拉選單的選項字樣是「代租代管」「包租包管」，句中寫的「包租合約」「轉租合約」畫面上沒有。「轉租」也不能在基本條件分頁直接選：只有從包租包管合約點「新增轉租契約書」建立的合約才會出現這個選項，而且選單會鎖住（第 2、5 句的範本名稱也有同樣問題）
- [doubt] `jgb/D/social-housing-early-termination-difference` 社宅合約的提前解約怎麼設定？跟一般合約一樣嗎？（只設定雙方是否可以提前解約，沒有違約金計算方式） —— 句序 2：這句把一般合約寫成一律要選違約金計算方式並分段設定，漏掉特定合作團隊的專屬範本：meta_capital_condos 範本只填「提前解約預告日」，meta_capital_office 範本整段都沒有，nthurc_social_housing 範本只有單一門檻、不分段
- [doubt] `jgb/D/social-housing-rent-fees-tab` 社宅合約「租金費用」分頁要填什麼？（代租金額或包租金額、租金與押金、生活費用） —— 句序 1：句中寫的範本名稱「包租合約」「轉租合約」畫面上沒有，範本選單的字樣是「包租包管」「轉租」。欄位邏輯（代租金額／包租金額／轉租兩項都沒有）則正確
- [doubt] `jgb/D/social-housing-payment-method-tab` 社宅合約「收款方式」怎麼設定？（轉帳、票據、現金三種；代租代管範本還要選收款人是原房東或業者） —— 句序 2：範本名稱「包租合約」「轉租合約」畫面上沒有，應寫成畫面上的「包租包管」「轉租」。收款人欄位只在代租代管出現，這部分正確
- [doubt] `jgb/D/social-housing-notary` 社宅合約一定要公證嗎？（預設應辦理公證，可填理由不辦但視同放棄公證費補助；辦理公證後需下載文件紙本簽署再上傳歸檔） —— 句序 2：「只有『包租合約』範本可以逐款選擇」引用的範本名稱畫面上沒有，選單字樣是「包租包管」。可逐款選擇的條件本身（charter）正確
- [doubt] `jgb/D/social-housing-attachments-tab` 社宅合約「合約附件」要準備什麼？（合約附件只收其他文件如附註條款、稅籍證明；測量成果圖等在出租方附件分頁，轉租合約除外） —— 句序 1：例外寫成「轉租合約」「包租合約」（標題也寫「轉租合約除外」），但畫面上的範本名稱是「轉租」「包租包管」。哪些分頁被隱藏（sublet 拿掉出租方附件、charter 拿掉承租方附件）則正確
- [doubt] `jgb/D/social-housing-landlord-tabs-overview` 社宅合約「出租方」分組有哪些分頁？（基本資料、授權、附件三個分頁） —— 句序 1：說出租方分組「一律」有三個分頁，但選轉租範本時「授權」「附件」兩個分頁會被拿掉，只剩基本資料
- [doubt] `jgb/D/social-housing-landlord-license-conditions` 社宅合約「授權」分頁要確認什麼？（合法建物條件、同意提供住宅、同意轉租等授權事項） —— 句序 1：「主要用途登記含『住』…字樣／提出合法房屋證明」在畫面上屬於「住宅使用」這一項，不在「合法建物條件」下；合法建物條件的選項其實是「出租人為出租住宅之所有權人」「租賃標的需坐落於當地直轄市」。第 2 句也有問題：「同意提供住宅」是在包租包管和代租代管兩種方式中二選一，不是兩個「是否同意」的問題
- [doubt] `jgb/D/social-housing-tenant-tabs-overview` 社宅合約「承租方」分組有哪些分頁？（基本資料、家庭＆財產、授權、附件） —— 句序 1：說承租方分組「一律」有四個分頁，而且都用來確認租客的社宅資格，但選包租包管範本時會拿掉家庭＆財產、授權、附件，承租方也改填公司資料
- [doubt] `jgb/D/social-housing-tenant-basic-status` 社宅合約「基本資料」怎麼審核租客資格？（承租人資格、住宅政策補貼戶、代理人；包租合約改填公司資料） —— 句序 1：範本名稱「轉租合約」「包租合約」（第 2 句與標題同樣）畫面上沒有，選單字樣是「轉租」「包租包管」。欄位內容（承租人資格、住宅政策補貼戶、代理人最多 3 位、charter 改填公司資料）對碼正確
- [doubt] `jgb/D/social-housing-charter-sublet-tab-hiding` 社宅合約選「包租包管」或「轉租」範本，分頁會不同嗎？（包租包管隱藏承租方戶籍/證照/附件，轉租隱藏出租方證照/附件） —— 句序 標題：標題寫包租包管隱藏「戶籍/證照/附件」、轉租隱藏「證照/附件」，但這些不是畫面上的分頁名稱，是程式代號（Household/License）的中譯。實際名稱是「家庭＆財產」「授權」「附件」，而內文寫的就是實際名稱，標題和內文對不上

回覆：

## 簽約與合約檢視 `D-contract-sign-view`（待審 9 條：pass 6／doubt 3／未先審 0） ⚠️

- [pass] `jgb/D/contract-invite-and-review-period` 合約邀請發出後租客有多久審閱期？（預設 3 天／72 小時，逾期連結失效，天數為團隊可調整設定）
- [pass] `jgb/D/contract-esign-no-extra-fee` 電子簽章簽約要另外收費嗎？（系統內沒有簽章計費機制，簽約流程無付費／加購畫面）
- [pass] `jgb/D/contract-show-paper-upload-archive` 合約檢視頁的「歸檔資料」是什麼？有什麼檔案限制？（租客免註冊的合約簽署後上傳合約、續約、終止合約的歸檔 PDF，最大 10MB）
- [pass] `jgb/D/contract-show-creditcard-auth-prompt` 簽約時會提示信用卡自動扣款授權嗎？（收款設定需要信用卡自動扣款時，租客在簽約頁點「下一步」會提示前往授權；特定合作團隊專屬範本除外）
- [pass] `jgb/D/contract-upload-existing-vs-electronic` 上傳既有合約跟建立電子合約差在哪？（既存合約用於已簽好或有自己公版合約的情境，皆可續用系統帳務／修繕追蹤）
- [pass] `jgb/D/contract-guarantor-add-after-signing` 簽約後可以補加保證人嗎？（租客簽約流程本身就能加連帶保證人；簽約完成後要補加，業者端沒有自助功能，需洽 JGB 客服協助）
- [doubt] `jgb/D/contract-sign-flow-steps` 租客簽約要經過哪些步驟？（填承租方簽約資料與上傳文件、預覽合約、自動扣款先授權信用卡、部分範本另有條款勾選、雲想科技畫面簽名） —— 句序 3：「租客身份要上傳『小章』；法人身份則要上傳『大章』與『小章』」把選填寫成必填。印章欄位在「合約附件(選填)」區塊內，沒有必填標記，送出前的完成度檢查（allDone）也不檢查印章
- [doubt] `jgb/D/contract-locked-after-signing` 合約簽約後可以修改嗎？（送出前可編輯、簽名前可取消簽名重編，簽署完成即無法更改，需重新簽一份新合約） —— 句序 2：現行合約列表齒輪選單的字樣是「取消邀請」，不是「取消簽名」。「取消簽名」只出現在沒有路由的舊 ContractController@index。另外，「取消邀請」在「待房東簽名」（租客已簽）狀態下也能用，不只是「雙方都還沒簽名前」
- [doubt] `jgb/D/contract-show-panels` 合約檢視頁面看得到什麼？（出／承租方資訊、業者、經理人資訊，以及點交點退進行中的提示） —— 句序 1：這個檢視頁（src/pages/contracts/show/Index.vue）只給社宅合約用，路由是 sh-show。一般合約的檢視頁是 show.blade.php，上面沒有「合約點交中／點退中」提示。內文把它寫成所有合約的檢視頁，範圍錯了

回覆：

## 點交 `D-move-in`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/D/move-in-page-general-vs-social-housing` 點交頁面一般合約跟社宅合約用的是同一個嗎？（不是，一般住宅合約用一般合約的點交頁面，社宅合約會被導向社宅合約的點交頁面）

回覆：

## 點退 `D-move-out`（待審 7 條：pass 4／doubt 3／未先審 0） ⚠️

- [pass] `jgb/D/move-out-timing-window` 點退的時間限制是什麼？（合約到期前 30 天起可以點退，過了到期日之後目前沒有再設上限）
- [pass] `jgb/D/move-out-remains-in-active-list` 點退完成的合約為什麼還在「執行中合約」？（只要還沒到合約到期日就會留在執行中，到期後才轉入歷史合約）
- [pass] `jgb/D/move-out-fee-adjustment-step` 點退第二步「點退找補費用」頁面要填什麼？（系統帶入的點退費用項目，含提前解約時自動帶入的違約金、傢俱賠償，另可填備註、期限、附件）
- [pass] `jgb/D/move-out-tenant-no-response-cancel` 租客不確認點退時要怎麼辦？（系統不會逾期自動放行，只能由房東取消點退邀請後重新發送）
- [doubt] `jgb/D/move-out-checklist-and-damage` 點退清單怎麼處理設備損壞？（可編輯填入賠償金額與理由，過程可儲存草稿） —— 句序 1：免註冊租客可以選「上傳點退文件」，這時第一步只顯示上傳的 PDF（標題「點退清單」），不會列出傢俱項目，也沒有「編輯」，句子寫成所有點退都一樣；另外系統點退時畫面上的標題是「設備損壞確認」，不是「點退清單」
- [doubt] `jgb/D/move-out-bill-generation` 點退會產生什麼帳單？（含提前解約金、點退押金、賠償金，設定期限後發送，租客確認並繳款才算完成） —— 句序 3：句子說一定要等租客確認並繳款才算完成，漏了免註冊租客的例外：免註冊租客的點退一送出就直接變成點退完成，系統也同時建立點退帳單，不需要租客確認
- [doubt] `jgb/D/move-out-eligibility-conditions` 什麼合約可以點退？（合約狀態須為執行中／點交完成／歷史合約、須綁定 JGB 租客帳號，免註冊租客除外） —— 句序 3：加了引號的狀態名「完成歷史合約」只出現在程式註解（CONTRACT_HISTORY_DONE），現行畫面上沒有這個標籤；1024 和 2048 兩個狀態在畫面上都歸在「歷史合約」，這是實作詞

回覆：

## 續約 `D-renew`（待審 2 條：pass 2／doubt 0／未先審 0）

- [pass] `jgb/D/renew-date-setting-modes` 續約日期怎麼設定？（多份合約可用快速日期設定一次加 N 個月，或個別指定每份合約的續約日）
- [pass] `jgb/D/renew-upload-paper-signed` 續約可以上傳紙本已簽合約嗎？（只選一份紙本簽約的合約續約時可以，提供雙方已完成簽約的紙本合約掃描檔）

回覆：

## 提前解約 `D-early-termination`（待審 6 條：pass 4／doubt 2／未先審 0） ⚠️

- [pass] `jgb/D/early-termination-reasons` 房東申請提前解約要選什麼理由？（新版中文合約有 10 項法定理由可選，其餘合約只能選「其他」）
- [pass] `jgb/D/early-termination-form-fields` 申請提前解約要填什麼？（預計提前解約日須早於原合約到期日、違約金支付方與金額、佐證資料）
- [pass] `jgb/D/early-termination-eligibility` 什麼合約可以提前解約？（合約狀態須為成立或點交完成、沒有申請過或已完成過提前解約；「可否提前解約」設定只限制租客發起，不影響房東發起）
- [pass] `jgb/D/early-termination-effect-move-out` 提前解約後多久可以點退？（依新合約終止日往前推 30 天內即可執行點退押金）
- [doubt] `jgb/D/early-termination-tenant-cancel` 誰可以取消已送出的提前解約申請？（房東透過小齒輪取消，租客只有在提前解約確認中狀態才能取消） —— 句序 2：加了引號的狀態名「提前解約確認中」只出現在程式註解，現行畫面和幫助中心用的是「提前解約申請中」或「提前終止合約申請中」；而且租客取消只走「由租客發起」的分支
- [doubt] `jgb/D/early-termination-billing-after` 提前解約後還會出新帳單嗎？（解約日之後系統不會再自動產生新租金帳單；已產生、落在解約日後的帳單要業者自行封存） —— 句序 3：「合約預覽帳單」是設定檔註解（IS_OPEN_CONTRACT_BILL_SETTING），畫面上沒有這個設定；關閉的只有寫死在程式裡的特定合作團隊，句子卻寫成像團隊自己開關的設定，也沒寫出「特定合作團隊」

回覆：

## 租約公證（公證分頁與公證服務） `D-notary`（待審 3 條：pass 2／doubt 1／未先審 0） ⚠️

- [pass] `jgb/D/general-contract-notary-tab` 一般合約的「公證」分頁怎麼設定？（是否辦理公證，同意時可複選三項應逕受強制執行事項；英文與英越文版合約不支援）
- [pass] `jgb/D/contract-thinkcloud-esign-service` 簽約時進入的雲想科技頁面是什麼？（系統導向 Thinkcloud 雲想科技的電子簽署網頁，簽完再導回 JGB；一般合約、委託合約皆會用到）
- [doubt] `jgb/D/contract-thinkcloud-signing-variants` 雲想科技簽署畫面依合約類型有什麼差異？（公會版本合約加補充條款多一個協商條款簽名框；DIY 客製化合約解析失敗時會顯示提示訊息，不會直接出現系統錯誤畫面） —— 句序 2：「DIY」是程式用語（isDiyContract），畫面上沒有這個字；解析失敗時 thinkcloud 回傳的是 JSON 陣列，而這條流程是整頁跳轉進來的（contracts/sign 轉到 thinkcloud），所以不是畫面上的提示；標題把送簽前的失敗說成簽署畫面的差異

回覆：

## 委託合約（列表、建立編輯、檢視） `D-entrust-contract`（待審 11 條：pass 8／doubt 3／未先審 0）

- [pass] `jgb/D/entrusted-contract-what-is-it` 委託合約是什麼？（房東委託業者包租代管的合約，跟業者與租客之間的租賃合約是不同份文件）
- [pass] `jgb/D/entrusted-contract-preview-to-show` 委託合約編輯完成後怎麼進入簽署？（點右上角「預覽合約」先儲存資料，再進入檢視頁面）
- [pass] `jgb/D/entrusted-contract-upload-file-size-limit` 委託合約上傳既有檔案限制多大？（畫面寫最大 6MB，上傳元件實際上限是 10MB）
- [pass] `jgb/D/entrusted-contract-landlord-info` 委託合約的房東資訊怎麼填？（房東註冊或房東免註冊；免註冊時要選個人房東或法人房東身份）
- [pass] `jgb/D/entrusted-contract-manager-info` 委託合約的經理人資訊分頁要填什麼？（選簽約公司並帶出公司、經紀人與租賃住宅管理人員資訊、指定經理人、電子簽名圖章）
- [pass] `jgb/D/entrusted-contract-payment` 委託合約收付款資訊怎麼設定？（沒有選擇器，固定顯示「出租方帳戶」與「管理方帳戶」兩個現金收付區塊，後者必填）
- [pass] `jgb/D/entrusted-contract-show-and-upload` 委託合約檢視頁面能做什麼？（查看歸檔資料、上傳既有委託合約檔案、尚未寄出邀請前可返回編輯）
- [pass] `jgb/D/entrusted-contract-create-entry` 委託合約怎麼建立？（委託合約列表頁「建立委託約」按鈕，需有建立合約權限，可選客製化契約書或紙本簽約）
- [doubt] `jgb/D/entrusted-contract-lease-type` 委託合約「包租」跟「代管」有什麼不同？（代管必填服務費計算模式、幣別與金額或比例；計算制度、週期、約定日期兩者都要填） —— 句序 2：漏了特定合作團隊（beyond360）的例外：這個團隊看不到計算模式和計算制度，約定日期也不列入完成檢查，租金標籤顯示「零用金」而不是「包租租金」
- [doubt] `jgb/D/entrusted-contract-tabs-overview` 委託合約編輯畫面有哪些分頁？（房東資訊、委託條件三頁、管理方資訊共 3 組 5 頁） —— 句序 1：漏了特定合作團隊的例外：beyond360 團隊的第二個分頁標籤顯示「零用金與服務費」，不是「租金費用」
- [doubt] `jgb/D/entrusted-contract-fees` 委託合約的收費分頁要設定什麼？（服務費或包租金額的計算模式與週期，押金提示不得超過兩個月租金） —— 句序 1：漏了特定合作團隊的例外：beyond360 團隊看不到計算模式、參考金額、計算制度，押金提示也不顯示（押金提示另外只在 zh-TW 顯示），頁面標題是「零用金與服務費」

回覆：

## 帳單列表與帳單狀態 `E-bill-list`（待審 9 條：pass 7／doubt 2／未先審 0）

- [pass] `jgb/E/bill-actions-draft` 「草稿」狀態的帳單可以做哪些動作？（編輯／發送／移至已到帳／封存）
- [pass] `jgb/E/bill-actions-unreceived` 「應到帳」狀態的收款帳單可以做哪些動作？（匯款資訊／移至已到帳／開立發票／取消帳單）
- [pass] `jgb/E/bill-actions-progress` 「待對帳」狀態的收款帳單可以做哪些動作？（退至應到帳／移至已到帳／開立發票，沒有取消帳單）
- [pass] `jgb/E/bill-list-export-other-tabs` 「草稿帳單」「支出帳單」「總收支」分頁的匯出按鈕，跟帳單總表不是同一套（不需要先勾選，走另一個較舊的匯出流程）
- [pass] `jgb/E/bill-single-notification-deeplink` 帳單通知信裡的連結點進去會看到什麼？（帳單列表只先列出通知裡的那幾張帳單，自己改篩選後回到一般列表）
- [pass] `jgb/E/bill-balance-tab` 「總收支」分頁的用途是什麼？（「全部」混列已到帳與已支出的帳單，另有已到帳、已支出、應到帳、應支出各自的頁籤）
- [pass] `jgb/E/bill-notify-remittance-visibility` 「通知已匯款」按鈕什麼時候才會出現？（租客付款資訊視窗只在非線上金流收款的帳單才有；應支出帳單的齒輪選單則沒有這個限制）
- [doubt] `jgb/E/bill-actions-received` 「已到帳」狀態的收款帳單可以做哪些動作？（收款備註／發票／收據／退款對帳單） —— 句序 8：寫成到帳時「一律」寄附收據 PDF 的信，但特定合作團隊的款項確認信完全不附收據，漏了這個團隊例外（帳本本身也寫了「或不附」）
- [doubt] `jgb/E/bill-receipt-feature-roadmap` 收據功能還會不會有新的開發？（現行已到帳帳單一律可以看到系統寄送的收據，目前沒有公開的後續開發時程） —— 句序 1：「系統也會自動寄送附收據 PDF 的通知信給租客」是絕對句，漏了特定合作團隊的信完全不附收據；標題「一律可以看到系統寄送的收據」也跟著過頭

回覆：

## 建立與編輯帳單（單筆、批次、週期批次） `E-bill-create-edit`（待審 16 條：pass 13／doubt 3／未先審 0）

- [pass] `jgb/E/bill-create-modes` 新增帳單有哪幾種頁面？（新增帳單／新增批次帳單／新增週期帳單／編輯帳單）
- [pass] `jgb/E/bill-create-target` 新增帳單時「對象」可以選哪些？（租客／大房東／物件／其他）
- [pass] `jgb/E/bill-batch-vs-cycle` 「新增批次帳單」跟「新增週期帳單」有什麼不同？（批次是每個對象各一張，週期是一次產出各期帳單；兩者都可在租客與物件之間切換）
- [pass] `jgb/E/bill-cycle-schedule-fields` 新增週期帳單的「繳費週期」設定要填哪些欄位？（繳費週期／繳費截止日／截止日設定／帳單週期制度）
- [pass] `jgb/E/bill-cycle-amortization` 「總額（自動分攤）」欄位什麼時候才會出現？（只有新增週期帳單、且團隊開通社區投報率時）
- [pass] `jgb/E/bill-fee-item-rules` 帳單費用細目填寫有什麼規則？（度數欄位最多小數點後 2 位、電水瓦斯金額欄位限制小數點後 2 位、當期度數不可小於上期度數）
- [pass] `jgb/E/bill-title-field` 「帳單標題」最多可以輸入幾個字？（45 個字）
- [pass] `jgb/E/bill-remark-field` 「帳單備註」最多可以輸入幾個字？（150 個字）
- [pass] `jgb/E/bill-internal-note-field` 「內部備註」最多可以輸入幾個字？誰看得到？（100 個字，僅供業者團隊成員查看／編輯，租客看不到）
- [pass] `jgb/E/bill-payment-method-account-pair` 新增帳單時付款方式跟收款帳戶一定要一起填嗎？（兩者要嘛都空、要嘛都填；固定虛擬帳號例外）
- [pass] `jgb/E/bill-submit-button-behavior` 新增帳單頁面下方送出按鈕的文字跟行為會依情境改變（送出／發送簽核／簽核中／預覽帳單）
- [pass] `jgb/E/bill-contract-payment-prefill` 新增帳單選租客當對象時，付款方式會自動帶入合約的收款設定嗎？（會，但帳戶已停用/不可取號等情況不會亂猜）
- [pass] `jgb/E/bill-power-reading-draft-defaults` 草稿帳單的電費度數要自己填嗎？（草稿階段度數預設留空；物件有綁定智慧電錶時，可在編輯頁按「取得即時電錶度數」先帶入）
- [doubt] `jgb/E/bill-internal-note-visibility` 「內部備註」在哪些地方會出現？（只給業者團隊成員看：新增帳單單筆與編輯帳單可填，帳單列表欄位與帳單明細可看；批次／週期帳單頁面不顯示） —— 句序 1：標題和句 1 把「可填」限在新增帳單（單筆）與編輯帳單，帳單列表欄位只算「可看」；但帳單列表的「內部備註」欄其實可以直接行內編輯後存檔，有程式反例
- [doubt] `jgb/E/bill-tenant-unverified-draft-lock` 租客還沒完成驗證時，發給他的帳單會怎樣？（帳單卡在草稿分頁，發不出去；但可以手動移至應到帳/已到帳） —— 句序 1：「帳單停留在草稿、驗證完成前發不出去」只能在畫面提示文字裡找到；現行單張送出、新增後送出、批次新增送出這幾條路徑都沒有檢查租客驗證狀態，發送用的 ready() 也沒有，程式並沒有做這個攔截
- [doubt] `jgb/E/bill-partial-month-proration` 不足一個月的租金怎麼算？（依天數比例；預設團隊以剩餘天數 ÷ 該月曆天數，逐月產帳以實際天數 ÷ 該期帳單天數，不是固定除以 30） —— 句序 1：把設定檔註解裡的標籤「合約預覽帳單」加引號寫成團隊可以開關的功能名，但前台沒有這個字；實際上是寫死只有兩個特定合作團隊關閉，應改寫成「特定合作團隊」

回覆：

## 社宅報表 `E-social-housing-report`（待審 1 條：pass 1／doubt 0／未先審 0）

- [pass] `jgb/E/social-housing-sheet-program-scope` 社宅報表的「社會住宅」身份可以對應到哪個地方政府的社宅方案？（系統只定義身份類別，不判斷方案適配）

回覆：

## 差額發票（群組、底租、社區層開關） `E-balance-invoice`（待審 4 條：pass 3／doubt 1／未先審 0）

- [pass] `jgb/E/balance-invoice-community-switch` 差額發票要在哪裡設定？（團隊開通後在「差額發票管理」建立差額群組；社區編輯頁的差額發票開關只對部分特定合作團隊顯示）
- [pass] `jgb/E/balance-invoice-pick-and-individual-rent` 差額發票群組怎麼加入物件？每個物件的底租可以自訂嗎？（群組可開「自訂個別底租」，把群組底租總額分配給各物件）
- [pass] `jgb/E/balance-invoice-group-action-menu` 差額發票群組的動作選單有哪些選項？什麼時候不能用？（編輯群組／開立發票／封存群組／刪除群組；列表頁不能用時反灰，詳細頁直接不顯示；另有查看歷程圖示）
- [doubt] `jgb/E/balance-invoice-monthly-invoice-table` 「差額總表」裡每個月的差額怎麼看、怎麼開發票？（累積成本、累積收入、差額、是否開發票、發票金額、發票字軌） —— 句序 4：「要開立差額發票，是在群組列表動作選單點『開立發票』」把手動開立寫成唯一方式，漏了系統每月自動開立這條主路徑，手動和自動兩條流程混成一條

回覆：

## 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） `E-virtual-account`（待審 14 條：pass 13／doubt 1／未先審 0）

- [pass] `jgb/E/recharge-account-list-columns` 「固定虛擬帳號管理」列表看得到哪些資訊？（虛擬帳號、餘額、歷程一律都有；租客或物件欄位看團隊的固定虛擬帳號模式；有編輯權限時另有操作欄）
- [pass] `jgb/E/recharge-account-delete` 固定虛擬帳號要怎麼刪除？（列表操作選單選「刪除」，跳出確認視窗後才會真的刪掉）
- [pass] `jgb/E/recharge-account-history-content` 點開「歷程」看得到哪些內容？（每筆金額變動的時間／類型／金額／前後餘額／操作人員，有連結帳單可以點開查看）
- [pass] `jgb/E/recharge-account-bank-support` 固定虛擬帳號可以選哪些銀行？（聯邦、中國信託有專屬的建號流程，其餘從系統銀行清單選）
- [pass] `jgb/E/recharge-account-ubot-flow` 聯邦（803）虛擬帳號怎麼建立？有什麼限制？（金額鎖在帳號裡，租客月租變動要重新建一組）
- [pass] `jgb/E/recharge-account-ctbc-flow` 中國信託（822）虛擬帳號怎麼算出帳號？（填企業識別碼 5 碼與繳款人識別碼 8 碼由系統計算）
- [pass] `jgb/E/recharge-account-immutable` 虛擬帳號建立後，銀行跟帳號可以改嗎？（不行，銀行跟帳號建立後不能改；可以改餘額，以及依團隊模式改租客資料或綁定物件）
- [pass] `jgb/E/recharge-account-estate-binding-validation` 虛擬帳號綁定物件時，輸入物件 ID 有什麼驗證？
- [pass] `jgb/E/recharge-account-export` 「固定虛擬帳號管理」的「報表匯出」匯出什麼？（指定日期區間內租客匯入的入帳明細 Excel）
- [pass] `jgb/E/recharge-account-daily-settlement` 固定虛擬帳號的入帳是怎麼自動比對到帳單的？（入金當下即時銷帳，另有每日凌晨 03:00 排程再比對；限特定合作團隊；餘額不夠不會變成已到帳）
- [pass] `jgb/E/recharge-account-refund-excluded` 退押金這類要付給租客的帳單，也走固定虛擬帳號嗎？（不會，顯示的是租客本人的收款帳戶）
- [pass] `jgb/E/recharge-account-vs-single-use-atm` 「固定虛擬帳號管理」跟租客線上繳費產生的 ATM 虛擬帳號是同一種嗎？（不是，ATM 那組是單筆繳費用、效期 180 天）
- [pass] `jgb/E/recharge-account-regenerate-expired` 逾期的虛擬帳號能不能重新產生？（此操作需由 JGB 客服協助，業者端沒有自助入口）
- [doubt] `jgb/E/recharge-account-mismatch-and-duplicate` 租客重複匯款時系統怎麼處理？（國泰世華單筆帳單 ATM 帳號已付款後重複匯入會略過；固定虛擬帳號多匯的部分留作餘額） —— 句序 2：「一律……系統自動銷帳、多匯留作餘額抵扣後續帳單」寫成絕對，漏了例外：自動銷帳（入金當下與每日排程都一樣）只對後台自動對帳白名單的特定合作團隊生效，其他團隊的餘額不會自動抵帳單，也和同組 daily-settlement 的「限特定合作團隊」互相矛盾

回覆：

## 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」） `E-payment-onboarding`（待審 10 條：pass 7／doubt 3／未先審 0）

- [pass] `jgb/E/payment-gateway-options` JGB 支援哪些收款金流？身分限制是什麼？（國泰世華／永豐銀行／中國信託／藍新／愛金卡；個人房東不能開通藍新、國泰世華、永豐銀行）
- [pass] `jgb/E/payment-gateway-fees` 各家收款金流的費率跟入帳帳戶限制是什麼？（國泰世華／永豐銀行首次設定費 5,000 元且限本行帳戶；中國信託／藍新免費且不限本行帳戶）
- [pass] `jgb/E/newebpay-precondition` 開通藍新智付通前要準備什麼？（申請表要自填 09 開頭的台灣手機號碼）
- [pass] `jgb/E/ctbc-apply-flow` 中國信託收款怎麼申請？（中信轉帳 Pay 填資料送審，ACH 驗證約 5 個工作天；中信虛擬帳號填 5 碼企業代碼即可，個人房東不能開通）
- [pass] `jgb/E/ctbc-form-validation` 中國信託申請表單各欄位有什麼格式限制？（聯絡電話 10 碼、銀行代碼 3 碼、銀行帳號 10～16 碼）
- [pass] `jgb/E/payment-gateway-withdrawal` 各家金流的款項要怎麼提領？（藍新要自己登入後台辦理，前 5 次免費之後每次 10 元）
- [pass] `jgb/E/cash-payment-account-management` 「現金收款帳戶」怎麼管理？（可以新增、編輯、移除；需要收款設置編輯權限）
- [doubt] `jgb/E/newebpay-required-fields` 開通藍新智付通前，個人房東跟團隊各自要先填完哪些資料？ —— 句序 1：標題和第 1、3 句都寫成個人房東可以走藍新開通、只要先補資料；但在現行收款設定頁，個人房東的藍新選項是停用的，會顯示「您無法開通此收款方式」，進不了這條流程，也和同組 payment-gateway-options 的「個人房東不能開通藍新」矛盾。draft 的證據來自舊的 addMerchant 路徑（`page:web:users.add_merchant`、`return redirect()->route('users.role')`）
- [doubt] `jgb/E/newebpay-payment-methods` 藍新開通時可以勾選哪些付款方式？（信用卡／Google Pay／Samsung Pay／ATM／超商代碼；國外卡要另外申請） —— 句序 1：「可以勾選……預設都是開啟的」跟現行畫面不符：Newebpay.vue 的付款方式 checkbox 是未綁定的 input，沒有 checked 也沒有 onChange，畫面上五個框預設是未勾選的，勾不勾都不會改動送出的 paymentMethods；實際送出時一律用後端預設的 enabled true
- [doubt] `jgb/E/payment-onboarding-tax-risk` 線上金流收款的資金流向會不會有稅務申報風險？（系統負責收款；稅務風險屬稅捐機關與業者自身規劃，系統不判斷） —— 句序 1：「系統負責代為收款」沒有來源：draft 證據只有 `'您已開通過商店'`，撐不起這個說法。它也跟程式的實際資金流向不一致：藍新的款項留在業者自己的藍新帳戶，國泰、永豐直接入業者的本行帳戶。在稅務語境下寫「系統代收」會誤導；裁決 #102 只允許寫已查證的系統側事實

回覆：
