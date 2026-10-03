# Plan 9.21 W2-S1 修正紀錄（D／E／F／I 疑點 21 條，新 D1「修整條」）

> 允許集合 `scratchpad/p921-w2/allowed.json`（21 條，D 10／E 3／F 2／I 6；兩來源＝D／E：repo 審核單 9.20 S5＋`p920-w5/p920-s5-raw-*`，F／I：9.20 S2 審核單＋`p920-w1/p920-s2-raw-*`）。基準＝`scratchpad/p921-w2/backup/drafts/`。句序一律為**備份側**句序（drafts_diff 的 item 句序，0 起算）；doubt 的「句序」為 1 起算（0＝標題），依據節照原文保留。**範圍**寫在「依據」欄：`依據 #n`＝doubt 所指、`整條 #m`＝同條整條檢查新增、`依據 #n＋整條 #m`＝兩者（計畫 §1「新 D1」）。起草＝executor（`scratchpad/p921-w2/brief-executor-fix.md`，逐句筆記 `fix-notes.md`），主 session 審閱並機械驗證後套用；ops 原檔 `scratchpad/p921-w2/ops.json`。verifier 判定：過／不過／待核。
> `jgb/E/bill-actions-received`：起草者判 doubt 理由在現行內容已不成立（所指句不在現行內文、重開／作廢發票與退款對帳單已由現行句說明），該條改動全為整條檢查（`整條 #m`），由核對 verifier 一併確認 doubt 已不成立。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/D/contract-payment-method` | sentences | 0 | 改 | 整條 #1 | 過 |
| `jgb/D/contract-payment-method` | sentences | 2 | 改 | 整條 #1 | 過 |
| `jgb/D/contract-payment-method` | sentences | 3 | 改 | 整條 #1 | 過 |
| `jgb/D/contract-payment-method` | sentences | 4 | 改 | 依據 #1 | 過 |
| `jgb/D/contract-payment-method` | sources |  | 改 | 依據 #1 | 過 |
| `jgb/D/contract-show-panels` | sentences | 0 | 改 | 整條 #2 | 過 |
| `jgb/D/contract-show-panels` | sentences | 1 | 改 | 依據 #2 | 過 |
| `jgb/D/contract-show-panels` | sentences | 2 | 改 | 依據 #2 | 過 |
| `jgb/D/contract-show-panels` | sources |  | 改 | 整條 #2 | 過 |
| `jgb/D/contract-show-panels` | title |  | 改 | 整條 #2 | 過 |
| `jgb/D/contract-tax-invoice` | sentences | 0 | 改 | 整條 #3 | 過 |
| `jgb/D/contract-tax-invoice` | sentences | 1 | 改 | 整條 #3 | 過 |
| `jgb/D/contract-tax-invoice` | sentences | 2 | 改 | 依據 #3 | 過 |
| `jgb/D/contract-tax-invoice` | sentences | 3 | 新增句 | 依據 #3＋整條 #3 | 過 |
| `jgb/D/contract-tax-invoice` | sources |  | 改 | 依據 #3＋整條 #3 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | phrasings |  | 改 | 依據 #4 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | sentences | 0 | 改 | 依據 #4 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | sentences | 2 | 新增句 | 整條 #4 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | sources |  | 改 | 依據 #4 | 過 |
| `jgb/D/contract-thinkcloud-signing-variants` | title |  | 改 | 依據 #4 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 0 | 改 | 整條 #5 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 1 | 改 | 整條 #5 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 2 | 改 | 依據 #5 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 3 | 新增句 | 依據 #5＋整條 #5 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sources |  | 改 | 依據 #5＋整條 #5 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | title |  | 改 | 整條 #5 | 過 |
| `jgb/D/early-termination-form-fields` | phrasings |  | 改 | 依據 #6 | 過 |
| `jgb/D/early-termination-form-fields` | sentences | 1 | 改 | 整條 #6 | 過 |
| `jgb/D/early-termination-form-fields` | sentences | 2 | 新增句 | 整條 #6 | 過 |
| `jgb/D/early-termination-form-fields` | sources |  | 改 | 整條 #6 | 過 |
| `jgb/D/early-termination-reasons` | sentences | 0 | 改 | 整條 #7 | 過 |
| `jgb/D/early-termination-reasons` | sentences | 1 | 改 | 依據 #7 | 過 |
| `jgb/D/early-termination-reasons` | sentences | 2 | 改 | 整條 #7 | 過 |
| `jgb/D/early-termination-reasons` | sources |  | 改 | 整條 #7 | 過 |
| `jgb/D/early-termination-reasons` | title |  | 改 | 整條 #7 | 過 |
| `jgb/D/move-out-bill-generation` | phrasings |  | 改 | 整條 #8 | 過 |
| `jgb/D/move-out-bill-generation` | sentences | 0 | 改 | 整條 #8 | 過 |
| `jgb/D/move-out-bill-generation` | sentences | 1 | 改 | 整條 #8 | 過 |
| `jgb/D/move-out-bill-generation` | sentences | 2 | 改 | 依據 #8 | 過 |
| `jgb/D/move-out-bill-generation` | sentences | 3 | 新增句 | 依據 #8＋整條 #8 | 過 |
| `jgb/D/move-out-bill-generation` | sources |  | 改 | 依據 #8＋整條 #8 | 過 |
| `jgb/D/move-out-bill-generation` | title |  | 改 | 依據 #8 | 過 |
| `jgb/D/move-out-eligibility-conditions` | sentences | 2 | 改 | 依據 #9 | 過 |
| `jgb/D/move-out-eligibility-conditions` | sources |  | 改 | 整條 #9 | 過 |
| `jgb/D/move-out-eligibility-conditions` | title |  | 改 | 依據 #9 | 過 |
| `jgb/D/social-housing-tenant-license` | sentences | 0 | 改 | 依據 #10 | 過 |
| `jgb/D/social-housing-tenant-license` | sentences | 1 | 新增句 | 依據 #10＋整條 #10 | 過 |
| `jgb/D/social-housing-tenant-license` | sources |  | 改 | 整條 #10 | 過 |
| `jgb/D/social-housing-tenant-license` | title |  | 改 | 依據 #10 | 過 |
| `jgb/E/bill-actions-received` | sentences | 0 | 新增句 | 整條 #11 | 過 |
| `jgb/E/bill-actions-received` | sentences | 6 | 改 | 整條 #11 | 過 |
| `jgb/E/bill-actions-received` | sentences | 8 | 新增句 | 整條 #11 | 過 |
| `jgb/E/bill-actions-received` | sources |  | 改 | 整條 #11 | 過 |
| `jgb/E/bill-partial-month-proration` | phrasings |  | 改 | 依據 #12 | 過 |
| `jgb/E/recharge-account-mismatch-and-duplicate` | phrasings |  | 改 | 依據 #13 | 過 |
| `jgb/E/recharge-account-mismatch-and-duplicate` | sentences | 1 | 改 | 整條 #12 | 過 |
| `jgb/E/recharge-account-mismatch-and-duplicate` | sources |  | 改 | 依據 #13 | 過 |
| `jgb/F/repair-apply-flow-and-entry` | sentences | 0 | 改 | 依據 #14 | 過 |
| `jgb/F/repair-apply-flow-and-entry` | sentences | 5 | 改 | 整條 #13 | 過 |
| `jgb/F/repair-apply-flow-and-entry` | sources |  | 改 | 整條 #13 | 過 |
| `jgb/F/repair-apply-flow-and-entry` | title |  | 改 | 依據 #14 | 過 |
| `jgb/F/repair-edit-amount-visibility` | phrasings |  | 改 | 依據 #15 | 過 |
| `jgb/F/repair-edit-amount-visibility` | sentences | 2 | 新增句 | 依據 #15＋整條 #14 | 過 |
| `jgb/F/repair-edit-amount-visibility` | sources |  | 改 | 依據 #15 | 過 |
| `jgb/F/repair-edit-amount-visibility` | title |  | 改 | 依據 #15 | 過 |
| `jgb/I/control-panel-setting-shell` | sentences | 1 | 新增句 | 依據 #16＋整條 #15 | 過 |
| `jgb/I/control-panel-setting-shell` | sources |  | 改 | 依據 #16 | 過 |
| `jgb/I/control-panel-setting-shell` | title |  | 改 | 依據 #16 | 過 |
| `jgb/I/homepage-sections-overview` | sentences | 0 | 改 | 整條 #16 | 過 |
| `jgb/I/homepage-sections-overview` | sentences | 1 | 改 | 依據 #17 | 過 |
| `jgb/I/homepage-sections-overview` | sentences | 2 | 新增句 | 依據 #17 | 過 |
| `jgb/I/homepage-sections-overview` | sources |  | 改 | 依據 #17 | 過 |
| `jgb/I/notification-mail-settings` | phrasings |  | 改 | 依據 #18 | 過 |
| `jgb/I/notification-mail-settings` | sentences | 0 | 改 | 整條 #17 | 過 |
| `jgb/I/notification-mail-settings` | sentences | 2 | 新增句 | 依據 #18＋整條 #17 | 過 |
| `jgb/I/notification-mail-settings` | sources |  | 改 | 依據 #18 | 過 |
| `jgb/I/notification-mail-settings` | title |  | 改 | 依據 #18 | 過 |
| `jgb/I/pricing-free-trial-eligibility` | sentences | 0 | 改 | 整條 #18 | 過 |
| `jgb/I/pricing-free-trial-eligibility` | sentences | 1 | 改 | 整條 #18 | 過 |
| `jgb/I/pricing-free-trial-eligibility` | sentences | 2 | 新增句 | 整條 #18 | 過 |
| `jgb/I/pricing-free-trial-eligibility` | sentences | 3 | 刪句 | 依據 #19 | — |
| `jgb/I/pricing-free-trial-eligibility` | title |  | 改 | 整條 #18 | 過 |
| `jgb/I/pricing-free-vs-experience-plan` | sentences | 0 | 改 | 依據 #20＋整條 #19 | 過 |
| `jgb/I/pricing-free-vs-experience-plan` | sentences | 1 | 改 | 依據 #20 | 過 |
| `jgb/I/pricing-free-vs-experience-plan` | sources |  | 改 | 依據 #20＋整條 #19 | 過 |
| `jgb/I/pricing-quota-full-block` | sentences | 2 | 改 | 依據 #21 | 過 |
| `jgb/I/pricing-quota-full-block` | sentences | 3 | 新增句 | 依據 #21＋整條 #20 | 過 |

## 刪除

（無）

## 已由前案處理

（無）

## 停下交業主

（無）

## 依據

1. `jgb/D/contract-payment-method`（9.20 S5 doubt）：句序 5：「加入常用帳號」實際看的是 edit_role 權限，也就是「編輯團隊」，跟收款設定無關；收款設定是另一個權限 edit_role_payment「編輯收款設置」
2. `jgb/D/contract-show-panels`（9.20 S5 doubt）：句序 2：兩種提示是看檢視者身分決定的（租客看到「請確認點交結果」，房東端看到「等待承租方確認」），不是看「目前哪一方在等待」；第 3 句的點退提示也是同一個判斷
3. `jgb/D/contract-tax-invoice`（9.20 S5 doubt）：句序 3：講法「租金以外可以開發票嗎」只能用「僅提供租金品項開立發票」這句提示回答，但程式會對所有應稅品項開票，押金設算息也有獨立發票，畫面上還有生活費用計稅品項，所以這句提示已過時，照它回答會誤導
4. `jgb/D/contract-thinkcloud-signing-variants`（9.20 S5 doubt）：句序 1：「協商條款」簽名框這個標籤只出現在程式註解；介面、合約 PDF 範本與設定檔都沒有這個字串，等於把註解當成介面標籤
5. `jgb/D/contract-upload-existing-vs-electronic`（9.20 S5 doubt）：句序 3：10MB 上限出自幫助中心，跟程式不一致：建立紙本合約時，在「基本條件」分頁上傳合約檔案的上限是 15MB；10MB 是合約檢視頁上傳用的元件預設值
6. `jgb/D/early-termination-form-fields`（9.20 S5 doubt）：句序 講法：講法「取消提前終止合約」沒辦法用本條內文回答：兩句都只講申請欄位，完全沒提取消（取消寫在 early-termination-tenant-cancel）
7. `jgb/D/early-termination-reasons`（9.20 S5 doubt）：句序 2：引號內的例句「承租方擅自將租賃住宅轉租或轉讓租賃權於他人」在現行選項裡找不到逐字原文；實際字串中間還有「違反第七條第三項規定，」
8. `jgb/D/move-out-bill-generation`（9.20 S5 doubt）：句序 3：程式裡「點退完成」不看有沒有繳款：註冊租客按下同意，點退帳單就成立，合約當下轉為點退完成，跟句子與標題寫的「租客確認並繳款才算完成」不符（幫助中心這樣寫，但與程式衝突）
9. `jgb/D/move-out-eligibility-conditions`（9.20 S5 doubt）：句序 標題：標題寫「合約狀態須為執行中」，內文與程式只允許合約成立（SIGNED）、點交完成、歷史合約；點交中、點退中、提前解約中的合約也在執行中列表，卻不能點退，標題比內容寬
10. `jgb/D/social-housing-tenant-license`（9.20 S5 doubt）：句序 1：「家庭年所得是否低於當地一定百分位所得」這個選項在程式裡已被註解掉，畫面上現在是無自有住宅、所得低於最低生活費 3.5 倍、財稅所得總檢核三項，標題的「家庭年所得百分位」也一樣不成立
11. `jgb/E/bill-actions-received`（9.20 S5 doubt）：句序 4：「此操作需由 JGB 客服協助。」沒有指明是哪個操作；講法裡的重開發票、作廢發票，在現行齒輪選單是業者可以自己做的動作（需 add_bill 權限），與這句矛盾；標題列出的「退款對帳單」內文也完全沒寫
12. `jgb/E/bill-partial-month-proration`（9.20 S5 doubt）：句序 講法：講法「點退帳單租金怎麼算」無法由內文回答：內文只寫週期產帳的不足月比例；點退帳單的費用來自合約的點退費用項目，不走這套比例，照內文回答會誤導
13. `jgb/E/recharge-account-mismatch-and-duplicate`（9.20 S5 doubt）：句序 講法：講法「虛擬帳號匯款金額不符」無法由內文回答：內文只寫重複匯款與餘額；引用的 #p914-atm-amount-mismatch（國泰／中信／永豐轉待對帳、藍新不動帳）一句都沒寫進來
14. `jgb/F/repair-apply-flow-and-entry`（9.20 S2 doubt）：句序 1：第 1 句與標題把入口寫死成【修繕管理】>【修繕單總表】，但第 3、4 句明講租客也走這個流程；程式裡租客側欄的選單名稱是【我的報修】，所以這句漏了租客身分的例外
15. `jgb/F/repair-edit-amount-visibility`（9.20 S2 doubt）：句序 1：講法「修繕結算金額怎麼填」「完成修繕怎麼登記費用」用內文答不出來：兩句只講誰看得到、會不會變成帳單，沒講是在「完成修繕」>「房東備註」的編輯模式裡填金額
16. `jgb/I/control-panel-setting-shell`（9.20 S2 doubt）：句序 1：講法「控制台側邊欄」在內文找不到答案：設定頁在非新增／編輯時會顯示側欄，裡面只有「任務管理設定」一項，內文完全沒提
17. `jgb/I/homepage-sections-overview`（9.20 S2 doubt）：句序 2：「從特定搜尋入口進入首頁時才會顯示」沒有來源：顯示條件只是網址帶 allowSearch 參數，全庫沒有任何入口會帶這個參數
18. `jgb/I/notification-mail-settings`（9.20 S2 doubt）：句序 2：標題與講法（「通知信副本信箱怎麼加」「通知信設定在哪裡」）都在問能不能加副本信箱，內文卻只看控制台這一頁，等於回答「沒有地方可加」；但現行會員側欄的「通知收件信箱」頁就能新增信箱，每個通知信最多 3 組，內文漏了這個例外
19. `jgb/I/pricing-free-trial-eligibility`（9.20 S2 doubt）：句序 4：「取消訂閱也不會退款」描述的是現行程式走不到的情境：免費方案建立時不設自動續約資料，取消訂閱入口一開始就因 plan_extend_ymd 為空而擋下（同組外的 subscription-cancel-effect 第 4 句也這樣寫），這句其實是程式註解，被寫成了使用者會遇到的事實
20. `jgb/I/pricing-free-vs-experience-plan`（9.20 S2 doubt）：句序 1：沒有標明出處就直接說免費方案「擁有智能合約及自動對帳功能」，等於替待裁 #42/#43 選了 FAQ 那一邊；同粗目的 pricing-free-trial-feature-scope 依免費試用彈窗把自動對帳列為不支援，兩條互相矛盾
21. `jgb/I/pricing-quota-full-block`（9.20 S2 doubt）：句序 3：未訂閱版內文的物件數條件寫反了：上限有值時顯示「無上限」，沒有值時顯示空白，畫面上永遠不會出現句中說的「[物件上限]」數字

## 整條依據

1. `jgb/D/contract-payment-method`：分頁範圍（一般合約）、固定虛擬帳號顯示條件與現金收款指定帳戶流程寫法與程式不符：code:src/pages/contracts/edit/payment/Index.vue `<General v-if="editStore.options?.property_purpose_key == 1"`；code:src/pages/contracts/edit/payment/General.vue `{{ t('使用其他帳戶') }}`
2. `jgb/D/contract-show-panels`：面板區塊名稱與出現條件寫錯（出／承租方資訊並非面板、承租方確認前沒有面板）：code:src/pages/contracts/show/_parts/SocialHousingPanel.vue `v-if="scopeStore.state?.nowStep == 3"`；code:src/pages/contracts/show/_parts/PanelInfoStructure.vue `{{ t('業者') }}`
3. `jgb/D/contract-tax-invoice`：分頁出現條件漏例外（社宅、發票設定、車位合約僅特定合作團隊）、應稅品項範圍寫太窄：code:src/use/useEditStore.js `return node.name !== 'contracts.edit.taxAndInvoice'`；code:src/pages/contracts/edit/taxAndInvoice/index.jsx `<div class="mr-5 font-500">{ t('生活費用計稅品項') }</div>`
4. `jgb/D/contract-thinkcloud-signing-variants`：送簽流程漏說明解析失敗於送簽階段同樣擋下：code:app/Http/Controllers/ContractController.php `$signBlockAry = $diyContractService->readToSignBlock($result,$contract,$role);`
5. `jgb/D/contract-upload-existing-vs-electronic`：紙本簽約適用情境與自製合約模板入口和程式不符、帳務說法無程式來源、社宅身分例外漏寫：code:src/components/Lightbox/SelectContractMethod.jsx `description: '請上傳雙方已簽訂完成或是已公證完成的合約',`；code:src/components/Lightbox/SelectContractMethod.jsx `description: '自製合約模板',`
6. `jgb/D/early-termination-form-fields`：違約金設定漏必填條件、佐證資料格式大小與特定合作團隊支付金額例外：code:src/components/Lightbox/ContractEarlyTerminationByLandlord.jsx `{ t('支援JPG、PNG檔，檔案大小最大[s1]MB。', [10]) }`
7. `jgb/D/early-termination-reasons`：原因選擇標籤與介面不符、文字框漏200字上限、標題稱法定理由無源：code:src/components/Lightbox/ContractEarlyTerminationByLandlord.jsx `maxLength={200}`
8. `jgb/D/move-out-bill-generation`：點退第二步不是產生帳單、帳單項目名稱無源、免註冊帳單為草稿不自動發送、漏歷史合約例外：code:app/Services/BillService.php `// 免註冊點退帳單改為「停留草稿，不自動發送」：`；code:app/Http/Controllers/ContractController.php `$contract->status = Contract::CONTRACT_HISTORY_DONE;`
9. `jgb/D/move-out-eligibility-conditions`：合約狀態清單漏明確排除點交中、點退中、提前解約中：code:app/Contract.php `// 條件1: 合約目前狀態不為「合約成立/點交完成/歷史合約/完成歷史合約」，則不可點退`
10. `jgb/D/social-housing-tenant-license`：漏承租資格變動通知與其他申請身分條件、漏包租包管範本無此分頁的例外：code:src/use/useEditStore.js `if (editStore.form.contract_template_selected === 'charter'){`；code:src/pages/contracts/edit/tenantLicense/Index.vue `<div class="font-500 mb-4">{{ t('承租資格變動通知') }}<sup class="text-main-500">*</sup></div>`
11. `jgb/E/bill-actions-received`：各動作漏帳務編輯權限與房東方身分例外、封存寫成一律、漏押金設算息帳單不通知租客：code:src/use/config/useBillTypes.js `const canEditOwnedBill = hasPermission('owner_bill') || hasPermission('add_bill')`；code:app/Notification.php `// 押金設算息帳單已到帳時，不需要通知租客`
12. `jgb/E/recharge-account-mismatch-and-duplicate`：一律先進儲值餘額過於絕對（找不到對應固定虛擬帳號時不入帳）：code:app/RechargeAccount.php `$result = self::_addLog($rechargeAccount, $value, $param);`
13. `jgb/F/repair-apply-flow-and-entry`：LINE 否定結論範圍過寬（網頁介面沒有，但有LINE推播與外部開單API）：code:app/Notification.php `botbonnie_api('push', 'line', $repair->role_id, $repair->user_id, [`；code:routes/api.php `->name('api.external.repairs.store')`
14. `jgb/F/repair-edit-amount-visibility`：漏編輯結算金額的權限與大房東例外：code:src/pages/repair/edit/Index.vue `&& !state.is_big_landlord`
15. `jgb/I/control-panel-setting-shell`：漏手機版與新增編輯頁無側邊欄的例外：code:src/pages/control-panel/_parts/OrderAside.vue `<div class="left-0 z-10 -mx-5 block w-screen bg-grey-50 px-2 lg:hidden">`
16. `jgb/I/homepage-sections-overview`：區塊順序漏三大優勢：code:src/pages/listings/Home.vue `<div v-html="t('JGB平台擁有三大優勢', null, $store.state.listingsI18n)"></div>`
17. `jgb/I/notification-mail-settings`：指涉不明（控制台頁）與漏會員側欄頁的權限與身分條件：code:src/pages/users/notification/Index.vue `hasPermissionToEdit: computed(()=>store.state.userData?.permission?.edit_notification || false),`；code:app/Role.php `'permission' => 'show_notification',`
18. `jgb/I/pricing-free-trial-eligibility`：價格頁連結文字不符、企業團隊與社宅房東一律取得免費方案、效期說明：code:app/User.php `$role->plan_name = '免費方案';`；code:src/pages/listings/pricing/parts/PlanAndDevice.vue `{ t('免費註冊試用', null, store.state.listingsI18n) }`
19. `jgb/I/pricing-free-vs-experience-plan`：每一個新創身份過於絕對（個人房東帶優惠代碼取得優惠方案）、自動對帳說法與彈窗矛盾故不寫：code:app/User.php `if (!empty($promotion = session('promotion')) && !empty($promotion['type']) && $promotion['type']=='registration_plan') {`；code:config/defaultplan.php `"estate_limit" => 5,`
20. `jgb/I/pricing-quota-full-block`：漏訂閱失效時複製、編輯物件與刊登廣告也出現同一彈窗：code:app/Http/Middleware/SubscriptionCheck.php `case 'api2.estates.edit': // 擋編輯物件`

## 整條待裁

- `jgb/I/pricing-free-vs-experience-plan`：免費方案／體驗方案是否有「自動對帳」：涉及待裁 #42／#43（`open-questions-20261003-w1s1-921.md`）——FAQ 與免費試用彈窗互相矛盾；本條刪除該語、不選邊，裁決後再補一句。

## 另見

（同粗目其他細目或程式本身的問題，本片不改，留下一份計畫或另案）

- `jgb/D/contract-payment-method`：未見矛盾。社宅收款方式另有條目「社宅合約『收款方式』怎麼設定」，與本條範圍不同。
- `jgb/D/contract-show-panels`：未見矛盾；「合約檢視頁的『歸檔資料』」等條目另屬流程範圍，未讀。
- `jgb/D/contract-tax-invoice`：「合約編輯分頁會依什麼條件增減」（同粗目）已寫稅務發票資格會影響分頁，與本條新 S0 不矛盾；未發現矛盾。
- `jgb/D/contract-thinkcloud-signing-variants`：「簽約時進入的雲想科技頁面是什麼？」未讀內文；本條不與其矛盾。
- `jgb/D/contract-upload-existing-vs-electronic`：「合約檢視頁的『歸檔資料』…有什麼檔案限制」另一條檔案上限（程式為 10MB：ArchiveFileUploader.jsx `size_limit={10}`），與本條 15MB 是不同入口，兩條不矛盾，但讀者可能混淆。
- `jgb/D/early-termination-reasons`：舊版 blade 燈箱（early-termination-by-landlord.blade.php）仍在原始碼，本次未核對它是否還被走到；本條以現行 Vue 燈箱為準（ContractLightboxes.vue、ContractItem.vue 皆引用 Vue 元件）。
- `jgb/D/move-out-bill-generation`：「什麼合約可以點退」「點退完成的合約為什麼還在『執行中合約』」等未見與本條矛盾；「點退第二步『點退找補費用』頁面要填什麼」說「含提前解約時自動帶入的違約金、傢俱…」，與本條不衝突，但本次沒驗其項目名稱。特定合作團隊的簽核（move_out_approval 旗標）會影響點退帳單何時能送出，本條未寫入，其他條也未見（另見，未改）。
- `jgb/D/move-out-eligibility-conditions`：「點退的時間限制是什麼？（到期前 30 天起，過到期日沒上限）」與程式（`$now < $startTs || $now > INF`）一致；但程式另有「尚未到合約開始日不可點退」一條，該條標題未提，另見（未改）。
- `jgb/D/social-housing-tenant-license`：「社宅合約『授權』分頁要確認什麼？（合法建物條件…）」屬出租方授權分組（不是承租方），標題未區分出租方／承租方的「授權」分頁，易與本條混淆，未改。另「社宅合約選包租包管或轉租範本分頁會不同嗎」與本條新 S3 一致。
- `jgb/E/bill-actions-received`：「封存」狀態那條（齒輪選單是空的）不矛盾；「帳單要什麼狀態才可以直接封存？（待發送與已到帳都可以，不用先轉成已到帳…）」同樣未寫權限，可能有同類漏例外，未讀全文，另見未改。租客側「已到帳」收款帳單（反轉帳單）在程式沒有用權限過濾（只有房東分支呼叫 assembleOptions），與本條新 S0 的「房東方帳號」限定一致，租客側選單內容本條沒有展開。
- `jgb/E/bill-partial-month-proration`：doubt 理由說這則講法同時出現在 canon 的 D.md 與 E.md；我用腳本掃 drafts-A..I.json 全部細目的 phrasings，只有 jgb/E/bill-partial-month-proration 含這則（drafts 內無 D 側細目持有它；canon/jgb/D.md 的出處本次未讀，不確定是舊文本殘留或另有來源），另見（未改）。
- `jgb/E/recharge-account-mismatch-and-duplicate`：未見矛盾。「固定虛擬帳號的入帳是怎麼自動比對到帳單的？（入金當下即時銷帳，另有每日凌晨 03:00 排程再比對…）」與本條 S1「只有白名單團隊自動銷帳」需對齊：程式在 recharge() 即時銷帳受同一白名單 gate 約束；該條若寫成所有團隊都會即時銷帳，會與本條矛盾，未讀其全文，另見（未改）。
- `jgb/F/repair-apply-flow-and-entry`：「報修細節要填什麼？…」「預約時段規則是什麼」等未讀全文；「新增修繕單後誰會收到通知？（租客送出時通知房東方；房東方在網頁上建立時只寄 Email 給房東方，租客…）」與本條 S5（LINE 通知）需對齊：程式 Notification.php 的 repair_create 對房東方同時有 botbonnie LINE／facebook 推播，該條若寫「只寄 Email」要查是否與程式一致，另見（未改）。
- `jgb/F/repair-edit-amount-visibility`：「誰不能編輯修繕單細節頁？（租客帳號、大房東角色不能…）」與本條新 S3 一致；「房東備註要填什麼？（完成時間、備註文字最多 300 字、可以附照片…）」未提及結算金額欄位，與本條可互補，未改。
- `jgb/I/control-panel-setting-shell`：「誰能用控制台的任務管理與通知信設定？（僅限特定合作團隊角色；控制台首頁本身沒有這層檢查，只有進到「設定…」）」與程式一致：controlPanel.setting 路由 beforeEnter 只放行兩個特定合作團隊角色群組，否則導向 /users；本條未重複此條件，也不矛盾。
- `jgb/I/homepage-sections-overview`：「首頁『JGB平台十大特色』實際列出幾項？」「首頁『JGB平台擁有三大優勢』是哪三項？」與本條 S0 不矛盾；「首頁的線上諮詢小幫手正式站看得到嗎？」與 Home.vue 末端 `<PresalesAssistant v-if="window.APP_ENV !== 'production'" />` 一致，本條 S0 未提小幫手，未改。
- `jgb/I/notification-mail-settings`：「控制台首頁目前能用什麼？」「誰能用控制台的任務管理與通知信設定？」皆與本條不矛盾。同書架另有 A 粗目的「通知收件設定有哪些分類？」（jgb/A/notification-settings-categories）講的是同一頁（會員側欄頁），分類列表與本條新 S2 的例子需一致，未讀其全文，另見（未改）。
- `jgb/I/pricing-free-trial-eligibility`：同組外的「subscription-cancel-effect」（doubt 已指出）第 4 句同樣把註解寫成事實，不在本批 21 條，另見（未改）。「免費方案與體驗方案差在哪？」「免費試用不能用哪些功能？」兩條的待裁 #42／#43 與本條無關。
- `jgb/I/pricing-free-vs-experience-plan`：「免費試用不能用哪些功能？（最多 5 個物件，不支援團隊與門鎖電錶等進階功能）」依免費試用彈窗把自動對帳列為不支援，即 #42 的另一邊，本條不再與它矛盾。「免費試用怎麼開始、能用多久？」新 S1 與本條新 S0 對「個人房東帶優惠代碼」的說法一致。
- `jgb/I/pricing-quota-full-block`（整條檢查發現，非 54 則待裁；jgb2 程式缺陷候選）：未訂閱版彈窗內文的數字位置在程式上永遠是「無上限」或空白（與有效訂閱版不同），像是程式判斷式寫反的缺陷；是要保持現況、還是排入修程式，需業主決定。本條已避開，不把該數字寫進內文。
- `jgb/I/pricing-quota-full-block`：「物件額度快滿了會怎樣？（剩 5 個以下觸發提醒…）」「免費試用不能用哪些功能」與本條不衝突，未讀全文。

## 自檢摘要（我實際跑過的檢查）

1. `ops-draft.json` 為合法 JSON，id 集合與 `allowed.json` 的 21 個完全相同、無多無少；沒有任何 `__stop__`。
2. 證據：每筆 `evidence_add` 的 `quote_or_symbol` 都用腳本（check_ev.py）在對應來源檔（jgb2 釘住匯出／幫助中心 HTML／帳本）內做逐字子字串比對：`checked 191 evidence items, bad 0`。`add_sources` 的檔案皆存在。每個改過或新增的句子至少一筆證據（我在撰寫時逐條對照；刪除的句子其舊證據隨句移除）。
3. 套用演練：把 `drafts-D/E/F/I.json` 複製到 scratchpad 的 `sim/`，設 `P919_RUNS`、`ALLOWED` 後對 21 條逐一跑 `edit_fine.py`，全部 exit 0（句數：contract-tax-invoice 4→9、payment-method 5→5、tenant-license 1→4、show-panels 3→3、upload-vs-electronic 3→6、move-out-bill 4→6、eligibility 3→3、early-termination-reasons 3→3、form-fields 2→4、thinkcloud 2→3、bill-actions-received 8→10、proration 1→1、recharge 2→2、repair-apply 6→6、repair-amount 2→4、control-panel-shell 1→3、homepage 3→4、notification-mail 2→4、free-trial 4→4、free-vs-experience 3→3、quota-full 3→6）。repo 的 drafts 未動（`git status` 在該目錄無輸出）。
4. 客戶名：用 `customer-terms.json` 的 18 條 regex 掃 ops 的標題、句子、講法、證據 quote 與本檔全文：0 命中。
5. 加引號標籤：把新／改句子裡全部 92 個「…」引號內容逐字 `grep -F` 匯出的 src／app／resources／config（排除 i18n 字典）：91 個命中；唯一未命中的是 `不綁信用卡的30天的試用方案，歡迎體驗！`，因介面原字串為 `不綁信用卡的[s1]天的試用方案，歡迎體驗！`（[s1]=30），畫面顯示等同，保留。
6. 否定結論的正對照（詳見各條 (b)）：bill-actions-received（前端無「重寄收據」按鈕；正對照 `labelKey: '收據'` 命中 2 處）；repair-edit-amount-visibility（修繕不產帳單；正對照 RepairController 內 `Notification::` 4 處）；homepage-sections-overview（無任何連結帶特定搜尋參數；正對照 `listings.search` 可搜到）；notification-mail-settings（控制台無入口）；repair-apply-flow-and-entry（網頁介面無 LINE 發起報修；正對照 LINE 通知與分享皆命中）；thinkcloud（「協商」只在註解；正對照同一 grep 命中該註解行）。
7. 已知限制：`edit_fine.py` 沒有「刪除單筆舊證據」的操作，只有「刪句連帶移除該句證據」；為避免舊證據掛在改過的句子上自相矛盾，凡舊證據會與新句矛盾的條目（upload-vs-electronic、move-out-bill-generation、pricing-free-trial-eligibility）我用「刪舊句＋新增句」處理；仍有兩處舊證據掛在已改句上但字串仍存在且不矛盾（contract-tax-invoice 舊 EV[2] 引畫面提示字串、social-housing-tenant-license 舊 EV[0] 引財稅所得總檢核字串），已在各條 (a) 註明。
8. 沒有做的事：沒有碰 repo 任何檔、沒有 git 寫入、沒有讀 `.env`、沒有連網／docker、沒有直接讀 `/Users/chenqinghuang/dev/work/jgb2/`、沒有讀 `~/jgb-archive/`、沒有寫 `~/.claude/canon`、沒有派子代理。

## 核對過程

- **D＋E 包**（fresh verifier，`scratchpad/p921-w2/brief-fix-DE.txt`，結論機械取出存 `verdict-DE.txt`）：57 項 **REFUTED 56／57**。不過 1 項：`move-out-bill-generation` 新增句（改後句 3）——寫歷史合約經租客同意後「不是『點退完成』」；程式同意時一樣把點退完成加進狀態旗標，歷史合約列表對這類合約顯示「點退完成」，也與同組 `move-out-remains-in-active-list` 矛盾（P2，本片引入）。
- **F＋I 包**（`brief-fix-FI.txt`，`verdict-FI.txt`）：30 項 **CONFIRMED 30／30**。
- `bill-actions-received`（doubt 理由在現行內容已不成立、改動全為整條）：D＋E 包 4 項全數判過。
- 兩包 verifier 對「整條」列 50 列全數判過；無範圍標錯判定。
- **依 D1 修一次**（ops `scratchpad/p921-w2/ops-recheck.json`，新 evidence 2 筆逐字命中；主 session 先對匯出確認：同意分支 `$contract->bit_status += Contract::CONTRACT_MOVE_OUT_DONE;`、歷史合約列表 `'text' => ___('點退完成'),`）：句 3 改為「如果是歷史合約，租客按下同意後，合約仍留在歷史合約底下，列表上的狀態同樣顯示「點退完成」。」
- **複核**（`brief-recheck.txt`，`verdict-recheck.txt`，該條全部 7 項）：**CONFIRMED 7／7**。
- 附建議（不阻擋，延後）：D＋E 4 則（稅與發票列表也收含租金／自備品項、社宅房東根本不出現選擇方式視窗、特定合作團隊無「帳單設定」分頁、系統點退第一步大標是「設備損壞確認」）、F＋I 1 則（控制台側欄預設收合、手機版通知信設定頁選單名稱空白，P3），明細見各 verdict 檔，留下一份計畫。

## 差異比對輸出（最終位元組）

`P919_DIFF_SHELVES=ABCDEFGHI python3 scratchpad/p921-w2/drafts_diff.py --base scratchpad/p921-w2/backup/drafts --cur runs/outline-20260920 --doubt scratchpad/p921-w2/allowed.json --fix-log <本檔>`

```
[diff] (g) evidence remaps on allowed fines: 20; new out-of-range: 0
[diff] fines in base (shelves ABCDEFGHI): 539; doubt set: 21 (not found in base: 0)
[diff] changed/deleted items: 87 in 21 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 87; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

drafts-A／B／C／G／H 與備份 `cmp` 相同；`scope_check` PASS；`coverage_check` PASS。
