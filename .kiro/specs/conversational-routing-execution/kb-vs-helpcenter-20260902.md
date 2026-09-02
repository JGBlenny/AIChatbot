# 知識庫 × 官方權威來源 對帳（2026-09-02 首輪，34 筆）

> 射程：`knowledge_base` id **3327–3360**（2026-04-19 loop 生成的平台操作知識，
> 當日剛補上 `business_types = system_provider` 而對業者可見）
> 機械層：`scripts/audit/kb_vs_helpcenter.py`（尺自證通過）
> 語義層：代理逐筆對帳，13 筆（9 筆機械抓不到 ＋ 4 筆數字衝突反證）
>
> ⛔ **本檔不自行選邊**（CANON 事實紀律第 4 條）。衝突並列兩邊證據，交裁決。

## 權威來源

```text
官方幫助中心  ~/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818/*zh-Hant*.html
              93 篇，扣掉部落格／行銷頁（esg/beike/sea-internet/rentallaw/propmarket/law）＝ 84 篇
jgb2 原始碼   ~/jgb/project/jgb/jgb2   master @ 637cb12165
```

⚠️ 兩個來源**會互相矛盾**（見 D-2）。⛔ 不得預設哪一個一定對。

---

## 一、⛔ 知識講錯，且官方明確寫了相反的話

### D-1　`kb3330`「JGB 系統保存歷史合約資料 5 年」——**最嚴重**

```text
官方  slug15_zh-Hant.html
      「系統不會自動刪除您的合約或帳單，歷史合約與已完成的帳單都會保留在系統中，**沒有期限**」
      「**這與法規建議的保存年限是兩件事**，系統不刪除是我們的做法，
        實際要保存多久則屬於您的法律義務，兩者請分開評估」
知識  「JGB 系統保存歷史合約資料 5 年。依中華民國《民法》規定，合約等憑證建議至少保存 5 年」
```

⚠️ 官方**專門寫了一段預防這個誤解**（把「系統保留期限」與「法規保存年限」切開），
而知識恰好把兩者合成官方要防的那句話。
⇒ 客服照講會讓業者以為第 6 年資料會消失。錯誤方向**不可回復**（使用者不會回頭驗證）。
⇒ 改法零風險：照抄 `slug15` 原文。

重跑：`grep -o "沒有期限" $HC/slug15_zh-Hant.html`；`grep -rl "5年\|五年" $HC/*zh-Hant*.html`（空）

### D-3　`kb3345`「永豐撥款日為繳款日 + 2 天」——**斷言了官方自己說還沒確定的事**

```text
官方  paymentapply_zh-Hant.html 逐字：
      「（國泰世華、永豐銀行與中國信託的**提領方式與審核工作天，待業務提供後補寫**。）」
知識  「永豐撥款日為繳款日 + 2 天」
```

⚠️ 程式端唯一近似值 `app/Payment.php` 的 `'AgreedDay' => 'CREDIT:5|VACC:3'`
**屬藍新 NewebPay 開通 payload、與永豐無關，且是 3 不是 2** ⇒ 極可能是誤植來源。
⇒ 斷言未知的**金流時程**，比講錯一個已知值風險更高。
⇒ 建議降級為「請洽永豐商戶後台撥款明細」。

### D-4　`kb3344`「分行代號：021」——與程式的單一真相來源差一碼

```text
程式  app/Payment.php（有「單一真相來源」註解區塊）
      SINOPAC_FVA_BRANCH_CODE = '0210'   ← 4 碼
知識  「分行代號：021」                    ← 3 碼
```

同筆的 `807`／`永豐商業銀行`／`豐收款服務專戶`／`台北分行` **皆與程式一致**。
⚠️ 這是租客會照著鍵入的臨櫃欄位。
⚠️ 同筆「854 + 11 碼流水號」「國泰分行可直存」**兩來源皆查無**（`atm_prefix` 在程式裡
是逐業者存在 `role_payments.info`，非寫死 854）⇒ 一併標未證實。

---

## 二、⚠️ 兩個權威來源互相矛盾 ⇒ ⛔ 不自行選邊，交裁

### D-2　`kb3336` 帳單排定發送——**三方說法都不一樣**

```text
知識    每日 12:00～17:00 自動寄出，放進去就**立即被寄出**
官方    onboarding12：「帳單統一於**當日 12:00** 發送給租客」
        Landlordonboarding06Finance：「將於**每日 12:00** 將選取的帳單統一發送」
程式    app/Console/Kernel.php：`bill:batch-send` 排了**四班**
        dailyAt('12:00') / ('13:00') / ('14:00') / ('15:00')
        （13–15 點的註解逐字寫「因為會斷掉，所以先暴力處理」）
```

逐條判定：

```text
知識的「17:00 上界」        ⛔ 錯（實際末班 15:00）
知識的「放進去就立即寄出」   ⛔ 錯——BillBatchSend::handle() 撈的是
                            `status = BILL_PREPARE_TO_READY`(32) 的整點批次掃描
                            ⇒ 16:20 放入當天不會寄，而知識會讓客服說「會立即寄出」
知識的兩條操作建議          ⚠️ 結論碰巧仍成立，但**理由是錯的**
官方的「統一於當日 12:00」   ⚠️ **也不完整**——漏了 13/14/15 三班
```

⇒ **待裁：以官方頁為準、還是以程式為準？** 並建議把官方頁的不完整回報給文件方。

### D-5　`kb3332`「合約自動儲存的觸發條件為操作後 10 秒」

```text
程式  src/use/useAutoSaveOld.js  setTimeout(..., 5000)  // debounce
      src/use/useAutoSave.js     預設 delay = 3000
      billSetting/Index.jsx 註明「autosave 有 5 秒 debounce、save() 還有 2 秒 throttle」
知識  「操作後 10 秒」
```

⚠️ 同檔註解有 `save(true) // 會delay x秒才顯示 已於 10 秒前儲存`
⇒ **知識很可能把畫面提示字當成觸發條件。** 幫助中心兩來源皆無此主題。
（同筆「點預覽／點下一步觸發」「至待發送合約找草稿」無反證。）

### D-6　`kb3327` 點退草稿帳單的產生時機

```text
官方  landlordonboarding04lease：「點退時機：於租約將於 30 天內到期或是已解約之歷史合約，
      **可進行點退**，並且除了點退之外，**系統也會自動產生帳單進行押金之退回**」
      ⇒ 點退草稿帳單是**房東主動發起點退時**產生
知識  「雙方簽名完成後，**系統會在管理者端產生點退草稿帳單**」
      ⇒ 把觸發者與時點說成「提前終止簽完就自動發生」
```

流程骨架其餘部分（齒輪→提前終止→租客同意→雙方簽名→違約金可調）與官方一致。
同筆「不自動封存退租後帳單」：幫助中心查無；程式 `Bill::archive()` 存在但
點退／退租完成路徑查無自動封存 ⇒ 不反對，但未證實。

### D-7　`kb3343` 國泰超商繳費狀態流程——**知識是對的，官方頁的通則會誤導**

```text
程式  BillReconcileAccount.php：`cathaybk-cvs_barcode` **每日 12:00** 查銷帳 → setPaid → status 8（待對帳）
      `cathaybk-cvs_barcode-settlement` **每日 06:00**，註解逐字
      「每月逢五觸發，遇假日則順延至下一營業日」→ setComplete → status 16（已到帳）
      ⇒ 知識的「5、15、25 日、遇假日順延」與 `substr($dayOfMonth,-1)=='5'` 判斷完全吻合
官方  slug22／onboarding8：「線上付款系統會自動對帳，**因此不會出現在待對帳**」
```

⚠️ 判為**不同命題**（官方那句講即時銷帳的虛擬 ATM；超商條碼是兩階段 T+N 結算，
碼上確實會停在 status=8）⇒ 知識 CONFIRMED，⚠️ **但官方頁的通則措辭會誤導客服**。

### D-8　`kb3344` 永豐虛擬帳號是浮動還是固定

```text
官方  landlordonboarding05Paymentsettings：永豐虛擬 ATM 是「**浮動／變動式，每期換號**」
程式  `SINOPAC_FVA_*`（**F**ixed **V**irtual **A**ccount）常數 ＋ `SwitchFvaBank.php`
      ＋ `bill:recharge-account`「**固定**虛擬帳號之帳單自動到帳排程」
```

---

## 三、✅ 機械誤報，知識是對的

### `kb3339`「最多一次產出 12 個月的帳單」

```text
程式  app/Contract.php  const BILLING_CYCLE_MONTHS = [1..12]
      註解：「繳費週期允許的月數…1~12 個月皆可…存檔白名單驗證與前後台選項皆以此為單一來源」
      CycleBillScheduleValidator.php：「繳費週期僅限 1 至 12 個月」
      前端 constants/contract.js：「1=每月、**12=每年**」
```
⇒ 「單張帳單最多涵蓋 12 個月」成立，「超過 12 個月用年繳拆兩張」的推論算術一致。
⚠️ 機械腳本誤報原因：幫助中心沒寫這個數字 ⇒ **「官方沒寫」被當成「衝突」**。

---

## 四、官方查無、屬客服經驗談（⛔ 不等於錯，但無背書）

```text
kb3333  續約 租屋補助 租補過審    幫助中心 7 種說法全空；程式只有欄位層 to_user_rent_subsidy_*
kb3334  委託約 租賃約 差異        「系統中分別管理」由程式佐證（EntrustedContract 獨立 model／路由／前端區塊），
                                  ⛔ 但「圖示（icon）不同」兩來源皆查不到
kb3328  合約審閱期 72 小時        ✅ CONFIRMED（contract_review_period 逐字「完整72小時」）
kb3329  簽約後不可改需重簽        ✅ CONFIRMED（landlordonboarding04lease 逐字）
kb3331  簽約邀請期限與逾期退回     ✅ CONFIRMED；知識獨有的「可申請 7 天／30 天」由 jgb2
                                  migration `seed_contract_review_renew_period_feature_config` 證實
```

---

## 統計

```text
機械層（34 筆）  CONSISTENT 21｜NUMBER_MISMATCH 4｜NO_MATCHING_PAGE 9
語義層（13 筆）  CONFIRMED 4｜CONFLICT 4｜NOT_IN_SOURCE 3｜機械誤報 1｜部分證實 1
```

⚠️ 機械層的 `CONSISTENT 21` **⛔ 不等於那 21 筆是對的**——只代表「知識裡的數值在
官方比對頁找得到」。沒有數值的敘述性錯誤，這一層抓不到。
