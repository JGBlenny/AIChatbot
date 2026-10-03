# Plan 9.22 S1 修正紀錄（A／C／D／I 疑點 6 條，新 D1「修整條」）

> 允許集合 `scratchpad/p922-s1/allowed.json`（6 條，A 1／C 2／D 2／I 1；兩來源＝A／C：repo 審核單 9.21 W1-S2＋`p921-s2/p921-s2-raw-W1S2B*`，D／I：9.21 W2-S2 審核單＋`p921-w2s2/p921-w2s2-raw-W2S2B*`）。基準＝`scratchpad/p922-s1/backup/drafts/`。句序一律為**備份側**句序（drafts_diff 的 item 句序，0 起算）；doubt 的「句序」為 1 起算（0＝標題），依據節照原文保留。**範圍**寫在「依據」欄：`依據 #n`＝doubt 所指、`整條 #m`＝同條整條檢查新增、`依據 #n＋整條 #m`＝兩者（計畫 9.21 §1「新 D1」）。起草＝executor（`scratchpad/p922-s1/brief-executor-fix.md`，逐句筆記 `fix-notes.md`），主 session 審閱並機械驗證後套用；ops 原檔 `scratchpad/p922-s1/ops.json`。verifier 判定：過／不過／待核。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/A/account-contact-info` | phrasings |  | 改 | 整條 #5 | 過 |
| `jgb/A/account-contact-info` | sentences | 4 | 改 | 依據 #1 | 過 |
| `jgb/A/account-contact-info` | sentences | 5 | 新增句 | 依據 #1 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 1 | 改 | 整條 #1 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 2 | 改 | 依據 #2 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 3 | 改 | 整條 #1 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 4 | 改 | 整條 #1 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 5 | 改 | 整條 #1 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 6 | 新增句 | 整條 #1 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 7 | 新增句 | 整條 #1 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sources |  | 改 | 依據 #2 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | title |  | 改 | 依據 #2 | 過 |
| `jgb/C/team-public-page-recruitment` | sentences | 0 | 改 | 依據 #3 | 過 |
| `jgb/C/team-public-page-recruitment` | sentences | 1 | 改 | 整條 #2 | 過 |
| `jgb/C/team-public-page-recruitment` | sentences | 2 | 改 | 整條 #2 | 過 |
| `jgb/C/team-public-page-recruitment` | sentences | 3 | 新增句 | 整條 #2 | 過 |
| `jgb/C/team-public-page-recruitment` | sources |  | 改 | 整條 #2 | 過 |
| `jgb/C/team-public-page-recruitment` | title |  | 改 | 依據 #3 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 0 | 改 | 整條 #3 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 1 | 改 | 依據 #4 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 2 | 改 | 整條 #3 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 3 | 改 | 整條 #3 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sentences | 4 | 新增句 | 整條 #3 | 過 |
| `jgb/D/contract-upload-existing-vs-electronic` | sources |  | 改 | 整條 #3 | 過 |
| `jgb/D/general-contract-notary-tab` | sentences | 0 | 改 | 整條 #4 | 過 |
| `jgb/D/general-contract-notary-tab` | sentences | 1 | 改 | 依據 #5 | 過 |
| `jgb/D/general-contract-notary-tab` | sentences | 2 | 改 | 整條 #4 | 過 |
| `jgb/D/general-contract-notary-tab` | sentences | 3 | 改 | 依據 #5 | 過 |
| `jgb/D/general-contract-notary-tab` | sentences | 4 | 新增句 | 整條 #4 | 過 |
| `jgb/D/general-contract-notary-tab` | sources |  | 改 | 依據 #5 | 過 |
| `jgb/D/general-contract-notary-tab` | title |  | 改 | 依據 #5 | 過 |
| `jgb/I/pricing-free-vs-experience-plan` | sentences | 2 | 改 | 依據 #6 | 過 |
| `jgb/I/pricing-free-vs-experience-plan` | sentences | 3 | 新增句 | 整條 #6 | 過 |
| `jgb/I/pricing-free-vs-experience-plan` | sources |  | 改 | 依據 #6 | 過 |
| `jgb/I/pricing-free-vs-experience-plan` | title |  | 改 | 依據 #6 | 過 |

## 刪除

（無）

## 已由前案處理

（無）

## 停下交業主

（無）

## 依據

1. `jgb/A/account-contact-info`（9.21 W1-S2 doubt）：句序 5：「第二組聯絡號碼欄位限填純數字」在程式裡沒有被強制：「限純數字」提示判斷的是另一個 store 值 premises_edit.contact.phone2（預設 ''，這頁的輸入框沒綁到它），提示永遠不會出現；後端存檔時也是原值照存，沒有任何數字驗證
2. `jgb/C/estate-dashboard-attachments-vs-contract-attachments`（9.21 W1-S2 doubt）：句序 3：下載附件後端要求物件編輯權限（edit_estate，或代理人且有 add_estate），沒有權限的使用者（包括能看到「附件清單」分頁的大房東）下載時會收到「權限不足！」，所以句子和標題的「下載不限身分」與程式相反
3. `jgb/C/team-public-page-recruitment`（9.21 W1-S2 doubt）：句序 1：標題把「沒有指定用途時自動轉址到住宅」列為與一般店舖的差異，但一般招租店舖缺 mode 或 premisesUseFor 時同樣會轉址補上 rent／residential，所以這一點不是差異；另外講法「招募頁跟一般店舖的網址不一樣嗎」在內文找不到答案（內文沒寫 /p/recruitment/{slug} 和 /p/{encryptId}/{mode}/{premisesUseFor} 的網址差別）
4. `jgb/D/contract-upload-existing-vs-electronic`（9.21 W2-S2 doubt）：句序 2：把畫面上已過時的說明「使用最新 109 年內政部公版合約」當成事實照寫，但現行可選範本是 114 年住宅租賃契約、113 年轉租契約等，「最新 109 年」與程式不符
5. `jgb/D/general-contract-notary-tab`（9.21 W2-S2 doubt）：句序 4：第 4 句與標題寫成「英文與英越文版合約不支援公證」，漏了例外：程式裡「內政部英文版 包租業」範本（en_us_corporation）其實有公證選項；反過來，英文版代租代管範本（en_us_management）與紙本／客製化（DIY）合約也沒有公證選項，卻同樣只顯示那句提示，所以「英文合約可以公證嗎」這個講法會被答錯
6. `jgb/I/pricing-free-vs-experience-plan`（9.21 W2-S2 doubt）：句序 標題：標題寫體驗方案「每月付費」，但內文第 3 句寫體驗方案可切換「月費／年費」，同粗目 pricing-plan-price-basis 也寫體驗方案年繳＝月費×12，程式確實可以年繳訂體驗方案，標題斷言只能按月付與內容不符

## 整條依據

1. `jgb/C/estate-dashboard-attachments-vs-contract-attachments`：上傳與刪除的後端權限檢查、合約附件「社區管理規約、住戶生活規約」為同一項目、選檔實際可選 PDF 與各項份數上限未寫入：code:app/Http/Controllers/EstateController.php `case 'upload_contract_attachment': // 新增合約附件`；code:src/pages/estates/dashboard/contractAttachments/index.vue `title: `${t('社區管理規約')}、${t('住戶生活規約')}`,`；code:src/pages/estates/dashboard/contractAttachments/index.vue `accept="image/jpeg,image/png,application/pdf"`
2. `jgb/C/team-public-page-recruitment`：招募頁篩選沒有社區選項（一般店舖有社區才有）、只有招租物件、每頁可選筆數與網址格式未寫清楚：code:src/pages/users/public/_parts/TopFilter.vue `// 招租頁面不需要 community 和 agentId 篩選器`；code:src/pages/users/public/Index.vue `options={route.params.encryptId === 'recruitment' ? [10, 30, 60, 90] : [30, 60, 90]}`
3. `jgb/D/contract-upload-existing-vs-electronic`：建立合約入口、社宅不出現選單而是直接進流程、紙本簽約分頁列舉含推論、客製化契約書「編輯底稿」未寫，並刪除無源的行銷語與「不是上傳合約」句：code:src/pages/contracts/list/_parts/PageTop.vue `v-if="store.state.userData?.role?.config_rule_key !== 4"`；code:src/pages/contracts/edit/rentBasic/General.vue `{{ t('編輯底稿') }}`
4. `jgb/D/general-contract-notary-tab`：「辦理公證」選項只存在於部分合約範本（原句為絕對句）、強制執行事項文字與標題錯置、保證人效力內容只有款號會變動：code:src/use/config/useContractRequiredField.js `[ContractTemplate.en_us_corporation]: [`；code:src/pages/contracts/edit/publicNotary/General.vue `{{ t('2：承租方未依約給付之欠繳租金、費用及出租方或租賃住宅所有權人代繳之管理費，或違約時應支付之金額。') }}`
5. `jgb/A/account-contact-info`：講法「第二組電話用途」內文答不到，改為欄位限制：code:resources/views/users/account.blade.php `name="phone2" maxlength="50"`
6. `jgb/I/pricing-free-vs-experience-plan`：免費方案價格固定為 0 與不自動續訂未寫，使講法「免費方案可以續訂嗎」內文答不到：code:app/User.php `// 不設定 plan_first_ymd 與 plan_cycle 使方案不會續訂`

## 整條待裁

- `jgb/I/pricing-free-vs-experience-plan`：免費方案與體驗方案是否有「自動對帳」：涉及待裁 #42／#43（`open-questions-20261003-w2s1-921.md`）——`FAQ.vue` 與 `LightboxFreePlan.vue` 說法不同；本條內文只寫「智能合約」，不選邊。

## 另見

（同粗目其他細目或程式本身的問題，本片不改，留下一份計畫或另案）

- `jgb/C/team-public-page-recruitment`（起草觀察，jgb2 缺陷候選）：招募頁標題旁的「招租中物件／買賣中物件」下拉仍會顯示，選「買賣中物件」會把網址的招募頁代稱位置換成 `sell`（`src/pages/users/public/_parts/TopFilter.vue` 的 RouterLink 帶 `encryptId: route.params.encryptId`、`mode: node.value`）；本條未寫入「招募頁不能切換買賣」。
- `jgb/C/estate-dashboard-attachments-vs-contract-attachments`：同粗目其他細目若也寫「下載不限身分」或大房東權限之類絕對句，建議以 `EstateController.php` `dashboard(` 內 `$hasEditPermission`、`isBigLandlord` 的定義複查（未逐條核對）。
- `jgb/C/estate-dashboard-attachments-vs-contract-attachments`：「合約附件」頁面說明寫「圖片僅支援JPG、PNG檔」，程式 `accept` 另含 PDF（走 `PdfToImg`）——畫面文字落後程式，本條依程式寫並保留說明原句。
- `jgb/D/contract-upload-existing-vs-electronic`：幫助中心對「業者自有公版合約」該走上傳還是客製化契約書的說法與程式無對應，本條刪句不背書；幫助中心同段的檔案上限數字與程式（`rentBasic/General.vue` `:size_limit="15"`）不符，其他細目若引用需對碼。
- `jgb/D/general-contract-notary-tab`：畫面提示「*目前英文與英越文版合約不支援此項目。」在紙本、客製化契約書與英文版代租代管上也會出現，文字不精確（畫面文案待修候選）。

## 核對過程

- **派工前檢查**：`doubt_source_check.py worklist`／`fixlog` 皆 PASS（6 條理由與 9.21 重審 raw 逐字相同、舊來源字串 0）；核對 brief 殘留 9 字串 0、修正紀錄路徑恰 1、件數一致（35 項／6 條）、判準段與底稿逐字相同。
- **A＋C＋D＋I 包**（fresh verifier，`scratchpad/p922-s1/brief-fix-ACDI.txt`，結論機械取出存 `verdict-ACDI.txt`）：35 項 **REFUTED 34／35**。不過 1 項：`general-contract-notary-tab` 改後句 6——寫「沒有『辦理公證』選項的合約，公證分頁只會顯示提示」是絕對句，漏了部分特定合作團隊專用範本與車位合約整個沒有公證分頁的例外（P2，本片引入）。
- 「整條」列 20 列全數判過；無範圍標錯判定。
- **依 D1 修一次**（ops `scratchpad/p922-s1/ops-recheck.json`，新 evidence 4 筆逐字命中；主 session 先對匯出確認 `src/use/useEditStore.js` 的公證分頁過濾）：句 6 限定「有『公證』分頁、但範本沒有『辦理公證』選項的合約」；新增句 7「車位合約，以及部分特定合作團隊的專用範本，合約編輯畫面不會出現『公證』分頁；車位合約即使用的是有『辦理公證』選項的範本，也一樣沒有這個分頁。」
- **複核**（`brief-recheck.txt`，派工前同一組檢查 PASS；`verdict-recheck.txt`，該條全部 7 項）：**CONFIRMED 7／7**。
- 附建議（不阻擋，延後）：`contract-upload-existing-vs-electronic` 社宅句以社宅房東看不到的選單標籤「電子合約 - 住宅租賃契約書」稱呼該流程，可改不加引號的說法（P4）。

## 差異比對輸出（最終位元組）

`P919_DIFF_SHELVES=ABCDEFGHI python3 scratchpad/p922-s1/drafts_diff.py --base scratchpad/p922-s1/backup/drafts --cur runs/outline-20260920 --doubt scratchpad/p922-s1/allowed.json --fix-log <本檔>`

```
[diff] (g) evidence remaps on allowed fines: 6; new out-of-range: 0
[diff] fines in base (shelves ABCDEFGHI): 539; doubt set: 6 (not found in base: 0)
[diff] changed/deleted items: 35 in 6 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 35; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

drafts-B／E／F／G／H 與備份 `cmp` 相同；`scope_check` PASS；`coverage_check` PASS；`doubt_source_check fixlog` PASS。
