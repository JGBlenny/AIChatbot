# Plan 9.20 S2 先審結果整理：8 條 doubt 與 11 條附帶建議（2026-10-01 先審，2026-10-03 整理）

> 來源：S2 兩批 fresh verifier 的 raw（`extract_verdict.py` 從 transcript 機械取出），本檔以程式從 raw 逐字轉出，⛔ 未改寫判定內容。審核單正本是 `review-sheet-9.20-S2-FGHI-20261001.md`；本檔不取代審核單，也不影響「安全組過」的判定。
>
> 處置規則：doubt 依 D1 在下一份修正計畫處理（本批不審）；建議附在 **pass** 細目上，依 §12-2「只修 doubt 所指」**不自動處理**，交業主參考。⚠️ 建議若改到句子、sources 等指紋欄位，該細目的已審會被生成器丟掉、需重審；只改講法則不會（HANDOFF §12-2）。

## 1. doubt 8 條（下一份修正計畫的允許集合候選）

| # | 批 | 細目 | S1 修過？ | 句序 | 理由 | 證據 |
|---|---|---|---|---|---|---|
| 1 | S2B1 | `jgb/F/repair-apply-flow-and-entry` | 是 | 1 | 第 1 句與標題把入口寫死成【修繕管理】>【修繕單總表】，但第 3、4 句明講租客也走這個流程；程式裡租客側欄的選單名稱是【我的報修】，所以這句漏了租客身分的例外 | app/Role.php `'label' => $this->config_rule_type === 'landlord' ? ___('修繕管理') : ___('我的報修')` |
| 2 | S2B1 | `jgb/F/repair-edit-amount-visibility` | 是 | 1 | 講法「修繕結算金額怎麼填」「完成修繕怎麼登記費用」用內文答不出來：兩句只講誰看得到、會不會變成帳單，沒講是在「完成修繕」>「房東備註」的編輯模式裡填金額 | src/pages/repair/_parts/MemoArea.vue `{{ t('結算金額') }}`（在 isEditing 分支的 PrefixInput）；src/pages/repair/edit/Index.vue `:showAmount="store.state.userData?.role?.config_rule_type === 'landlord'"` |
| 3 | S2B2 | `jgb/I/pricing-free-trial-eligibility` | 是 | 4 | 「取消訂閱也不會退款」描述的是現行程式走不到的情境：免費方案建立時不設自動續約資料，取消訂閱入口一開始就因 plan_extend_ymd 為空而擋下（同組外的 subscription-cancel-effect 第 4 句也這樣寫），這句其實是程式註解，被寫成了使用者會遇到的事實 | app/User.php「不設定 plan_first_ymd 與 plan_cycle 使方案不會續訂」、「贈送的方案價格一定要 0 以免使用者取消訂閱拿到退款」；app/Http/Controllers/UserController.php unsubscribe()「if (empty($this->role->plan_extend_ymd))」 |
| 4 | S2B2 | `jgb/I/pricing-free-vs-experience-plan` | 否 | 1 | 沒有標明出處就直接說免費方案「擁有智能合約及自動對帳功能」，等於替待裁 #42/#43 選了 FAQ 那一邊；同粗目的 pricing-free-trial-feature-scope 依免費試用彈窗把自動對帳列為不支援，兩條互相矛盾 | src/pages/listings/pricing/parts/FAQ.vue「並擁有智能合約及自動對帳功能」 vs src/pages/listings/template-parts/LightboxFreePlan.vue unsupportedList「自動對帳」 |
| 5 | S2B2 | `jgb/I/pricing-quota-full-block` | 否 | 3 | 未訂閱版內文的物件數條件寫反了：上限有值時顯示「無上限」，沒有值時顯示空白，畫面上永遠不會出現句中說的「[物件上限]」數字 | resources/views/layouts/lightbox/general.blade.php「!empty($role)&&!isset($role->plan_estate_limit) ? $role->plan_estate_limit : '無上限'」 |
| 6 | S2B2 | `jgb/I/control-panel-setting-shell` | 是 | 1 | 講法「控制台側邊欄」在內文找不到答案：設定頁在非新增／編輯時會顯示側欄，裡面只有「任務管理設定」一項，內文完全沒提 | src/pages/control-panel/setting/Index.jsx「{!state.isHightLightShow && <OrderAside />}」；src/pages/control-panel/_parts/OrderAside.vue「label: t('任務管理設定')」 |
| 7 | S2B2 | `jgb/I/notification-mail-settings` | 是 | 2 | 標題與講法（「通知信副本信箱怎麼加」「通知信設定在哪裡」）都在問能不能加副本信箱，內文卻只看控制台這一頁，等於回答「沒有地方可加」；但現行會員側欄的「通知收件信箱」頁就能新增信箱，每個通知信最多 3 組，內文漏了這個例外 | src/pages/users/notification/Index.vue「每個通知信最多可再新增 3 組電子信箱收取通知信件。」「新增信箱」；app/Role.php「'label' => ___('通知收件信箱')」 |
| 8 | S2B2 | `jgb/I/homepage-sections-overview` | 是 | 2 | 「從特定搜尋入口進入首頁時才會顯示」沒有來源：顯示條件只是網址帶 allowSearch 參數，全庫沒有任何入口會帶這個參數 | src/pages/listings/Home.vue「v-if="$route.query?.allowSearch"」；全庫 grep「allowSearch」只命中 Home.vue 與 src/pages/listings/template-parts/HomeTop.vue 的判斷式 |

「S1 修過？」以 `fix-log-9.20-S1-FGHI-20261001.md` 是否出現該 id 判定。

## 2. pass 細目的附帶建議 11 條（交業主參考，不自動處理）

| # | 批 | 細目 | 建議 |
|---|---|---|---|
| 1 | S2B1 | `jgb/F/repair-status-tabs` | 第 4 句的「另見『看修繕單分享頁需要先登入嗎』」改成現行標題「修繕單分享頁需要先登入嗎？」 |
| 2 | S2B1 | `jgb/F/repair-apply-without-contract` | 第 1 句「申請修繕不需要這個物件正在跑合約」限定為房東方；租客只能從已簽約、執行中合約的物件報修，見 EstateController.php `$isTenantRepairCreate` |
| 3 | S2B1 | `jgb/F/repair-edit-application-detail-readonly` | 第 4 句的「另見『報修細節要填哪些欄位，哪些是必填的』」改成現行標題「報修細節要填什麼？」 |
| 4 | S2B1 | `jgb/F/repair-edit-landlord-complete-memo` | 「支援 JPG／PNG／PDF、單檔 10MB」照抄畫面文字；但上傳元件的 accept 也收 video/mp4、quicktime、webm，影片走 AjaxUploader 的 size_limit_video 100MB 上限，見 MemoArea.vue `accept="image/jpeg,image/png,application/pdf,video/mp4` |
| 5 | S2B1 | `jgb/F/repair-edit-share-to-vendor` | 「另見『看修繕單分享頁需要先登入嗎』」改成現行標題 |
| 6 | S2B1 | `jgb/G/device-edit-tabs-by-type` | 第 1、3 句「都可以修改描述／選擇或移除物件」只對業者成立；租客也打得開編輯頁，但描述欄位是 disabled、沒有「儲存」也沒有「選擇物件」，見 resources/views/iot/index.blade.php `:class="{'disabled' :isTenant}"`、doorlock/basic.blade.php `v-if="!isTenant"` |
| 7 | S2B1 | `jgb/G/remote-unlock-page` | 講法「遠端解鎖連結怎麼產生」內文只答得到「畫面上沒有產生入口、連結固定不變」，取得管道仍待業主裁決〔待裁 #40〕，可考慮拿掉這條講法 |
| 8 | S2B2 | `jgb/I/pricing-plan-price-basis` | get_plan_price 的「月費×10／×12」只適用 price_type='basic'；price_type='unit' 的年繳是單價×12×plan_durations 折扣。可註明「目前」或依價格類型而定，grep「目前年繳的費用計算方式為 月繳費用*10」 |
| 9 | S2B2 | `jgb/I/subscription-cancel-effect` | 「怎麼取消訂閱」這個講法只答到選原因與送出，可補上取消訂閱頁的入口 |
| 10 | S2B2 | `jgb/I/payment-bill-e-invoice-setup` | 「稅與發票」分頁只出現在 property_purpose_key=1 的一般物件合約，src/routes/contracts.js「contracts.edit.taxAndInvoice」 |
| 11 | S2B2 | `jgb/I/task-manager-form-fields` | 「編輯範圍」只要是編輯既有任務就會顯示，條件是 route.params.id 有值，不限週期性任務，grep「{ !isEmpty(route.params.id) &&」 |

分類：「另見」引用的標題已過時 3 條（`repair-status-tabs`、`repair-edit-application-detail-readonly`、`repair-edit-share-to-vendor`）；身分例外（租客）2 條；講法答不全 2 條；條件限定 3 條；影片上傳 1 條。

## 3. S1 核對附帶的 P3／P4 建議 8 條（計畫 §S2 約定 S2 後另列）

原文在 `fix-log-9.20-S1-FGHI-20261001.md`「核對過程」的「附建議」，共 8 項，這裡不重抄。和第 2 節的重疊有兩處：`repair-edit-share-to-vendor`（S1 建議改標題、S2 建議改「另見」引用，兩件不同事）；「另見」引用標題過時（S1 點名 `pricing-free-trial-feature-scope`，S2 再點名 3 條）。其中 `pricing-free-trial-eligibility` 已列入第 1 節的 doubt，下次修正時一併處理。

## 4. S2 scratch 產物（repo 外，S3 推導要用）

位置：`/private/tmp/claude-501/-Users-chenqinghuang-dev-work-AIChatbot/10bbe889-b004-4507-9860-313734c25333/scratchpad/p920-w1/`。`/private/tmp` 可能被清；S3 前以下列 sha256 前 16 碼核對，不符或不在就依計畫 §S2「已預跑」重建，raw 從代理 transcript 以 `extract_verdict.py` 重取。

| 檔 | sha256 前 16 碼 |
|---|---|
| `p920-s2-targets.json` | `51cf233d8d1491fc` |
| `p920-s2-batches.json` | `805203d8d4498382` |
| `p920-s2-hold.json` | `4f53cda18c2baa0c` |
| `p920-s2-raw-S2B1.txt` | `88248fafdb5e435f` |
| `p920-s2-raw-S2B2.txt` | `ad9e97154982c7c4` |
| `p920-s2-results.json` | `c4ed3bdec657ded8` |
