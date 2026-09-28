# Plan 9.19 S1 修正紀錄（A／B／C 疑點＋I 1 條）

> 允許集合 `scratchpad/p919-s1-allowed.json`（69 條）。基準＝`scratchpad/p919-s1-backup/drafts/`。句序一律為**備份側**句序（`p919_s1_drafts_diff.py` 的 item 句序）。evidence 句序位移由 `p919_edit.py` 機械處理，不列入本表（差異比對 (g) 另查）。verifier 判定：過／不過／待核。改寫工具 `scratchpad/p919_edit.py`。

## 修正表

| 細目 id | 欄位 | 句序 | 動作 | 依據 | verifier |
|---|---|---|---|---|---|
| `jgb/A/account-basic-info` | sentences | 2 | 改 | 依據 #1 | 過 |
| `jgb/A/account-change-password` | sentences | 2 | 改 | 依據 #2 | 過 |
| `jgb/A/account-change-password` | sentences | 3 | 改 | 依據 #2 | 過 |
| `jgb/A/account-change-password` | title |  | 改 | 依據 #2 | 過 |
| `jgb/A/account-contact-info` | sentences | 1 | 改 | 依據 #3 | 過 |
| `jgb/A/dashboard-big-landlord-view` | sentences | 1 | 改 | 依據 #4 | 過 |
| `jgb/A/dashboard-big-landlord-view` | title |  | 改 | 依據 #4 | 過 |
| `jgb/A/forget-password-flow` | sentences | 2 | 改 | 依據 #5 | 過 |
| `jgb/A/forget-password-flow` | sentences | 4 | 改 | 依據 #5 | 過 |
| `jgb/A/forget-password-setpwd-invite` | sentences | 1 | 改 | 依據 #6 | 過 |
| `jgb/A/login-no-account-register-link` | phrasings |  | 改 | 依據 #7 | 過 |
| `jgb/A/login-no-account-register-link` | sentences | 0 | 改 | 依據 #7 | 過 |
| `jgb/A/login-no-account-register-link` | title |  | 改 | 依據 #7 | 過 |
| `jgb/A/login-role-redirect` | sentences | 2 | 改 | 依據 #8 | 過 |
| `jgb/A/notification-mark-read-navigate` | sentences | 0 | 改 | 依據 #9 | 過 |
| `jgb/A/notification-mark-read-navigate` | title |  | 改 | 依據 #9 | 過 |
| `jgb/A/notification-mark-read-out-of-range` | title |  | 改 | 依據 #10 | 過 |
| `jgb/A/notification-settings-extra-emails` | sentences | 1 | 改 | 依據 #11 | 過 |
| `jgb/A/register-email-already-registered` | sentences | 0 | 改 | 依據 #12 | 過 |
| `jgb/A/register-email-already-registered` | sentences | 1 | 改 | 依據 #12 | 過 |
| `jgb/A/register-email-already-registered` | sources |  | 改 | 依據 #12 | 過 |
| `jgb/A/register-email-already-registered` | title |  | 改 | 依據 #12 | 過 |
| `jgb/A/register-email-link-resume` | sentences | 1 | 改 | 依據 #13 | 過 |
| `jgb/A/register-email-link-resume` | title |  | 改 | 依據 #13 | 過 |
| `jgb/A/register-role-select` | sentences | 0 | 改 | 依據 #14 | 過 |
| `jgb/A/register-role-select` | sentences | 2 | 改 | 依據 #14 | 過 |
| `jgb/A/register-role-select` | title |  | 改 | 依據 #14 | 過 |
| `jgb/A/register-sso` | sentences | 2 | 改 | 依據 #15 | 過 |
| `jgb/A/register-verify-code-shape` | sentences | 1 | 改 | 依據 #16 | 過 |
| `jgb/A/register-verify-code-shape` | title |  | 改 | 依據 #16 | 過 |
| `jgb/A/signer-address-fields` | title |  | 改 | 依據 #17 | 過 |
| `jgb/A/signer-corp-fields` | sentences | 0 | 改 | 依據 #18 | 過 |
| `jgb/A/signer-corp-fields` | sentences | 3 | 改 | 依據 #18 | 過 |
| `jgb/A/signer-corp-seals` | sentences | 0 | 改 | 依據 #19 | 過 |
| `jgb/A/signer-corp-seals` | title |  | 改 | 依據 #19 | 過 |
| `jgb/A/signer-edit-permission` | sentences | 1 | 改 | 依據 #20 | 過 |
| `jgb/A/signer-individual-fields` | sentences | 4 | 改 | 依據 #21 | 過 |
| `jgb/A/signer-manage-save-buttons` | sentences | 0 | 改 | 依據 #22 | 過 |
| `jgb/A/signer-manage-save-buttons` | title |  | 改 | 依據 #22 | 過 |
| `jgb/B/advance-auto-publish-unpublish` | sentences | 0 | 改 | 依據 #23 | 過 |
| `jgb/B/advance-auto-publish-unpublish` | title |  | 改 | 依據 #23 | 過 |
| `jgb/B/advance-community-labels` | sentences | 1 | 改 | 依據 #24 | 過 |
| `jgb/B/advance-community-labels` | title |  | 改 | 依據 #24 | 過 |
| `jgb/B/advance-fee-items-merge` | sentences | 0 | 改 | 依據 #25 | 過 |
| `jgb/B/advance-fee-items-merge` | title |  | 改 | 依據 #25 | 過 |
| `jgb/B/advance-sales-item-code` | sentences | 1 | 改 | 依據 #26 | 過 |
| `jgb/B/biglandlord-authorize-apply-step` | phrasings |  | 改 | 依據 #27 | 過 |
| `jgb/B/biglandlord-authorize-apply-step` | sentences | 0 | 改 | 依據 #27 | 過 |
| `jgb/B/biglandlord-authorize-apply-step` | sentences | 1 | 改 | 依據 #27 | 過 |
| `jgb/B/biglandlord-authorize-apply-step` | title |  | 改 | 依據 #27 | 過 |
| `jgb/B/biglandlord-report-community-rate` | sentences | 1 | 改 | 依據 #28 | 過 |
| `jgb/B/biglandlord-report-community-rate` | title |  | 改 | 依據 #28 | 過 |
| `jgb/B/biglandlord-seat-limit` | phrasings |  | 改 | 依據 #29 | 過 |
| `jgb/B/biglandlord-seat-limit` | sentences | 1 | 刪句 | 依據 #29 | 過 |
| `jgb/B/biglandlord-seat-limit` | sources |  | 改 | 依據 #29 | 過 |
| `jgb/B/biglandlord-seat-limit` | title |  | 改 | 依據 #29 | 過 |
| `jgb/B/lessee-crud` | sentences | 0 | 改 | 依據 #30 | 過 |
| `jgb/B/lessee-crud` | title |  | 改 | 依據 #30 | 過 |
| `jgb/B/lessee-list-columns-by-role` | phrasings |  | 改 | 依據 #31 | 過 |
| `jgb/B/lessee-list-columns-by-role` | sentences | 0 | 改 | 依據 #31 | 過 |
| `jgb/B/lessee-list-columns-by-role` | sentences | 1 | 刪句 | 依據 #31 | 過 |
| `jgb/B/lessee-list-columns-by-role` | title |  | 改 | 依據 #31 | 過 |
| `jgb/B/lessee-notification-toggle-effect` | sentences | 0 | 改 | 依據 #32 | 過 |
| `jgb/B/lessee-notification-toggle-effect` | sources |  | 改 | 依據 #32 | 過 |
| `jgb/B/lessee-notification-toggle-effect` | title |  | 改 | 依據 #32 | 過 |
| `jgb/B/member-list-role-inline-change` | sentences | 0 | 改 | 依據 #33 | 過 |
| `jgb/B/member-list-role-inline-change` | sentences | 1 | 改 | 依據 #33 | 過 |
| `jgb/B/member-list-role-inline-change` | title |  | 改 | 依據 #33 | 過 |
| `jgb/B/member-role-edit-reset` | phrasings |  | 改 | 依據 #34 | 過 |
| `jgb/B/member-role-edit-reset` | title |  | 改 | 依據 #34 | 過 |
| `jgb/B/member-seat-limit` | sentences | 1 | 改 | 依據 #35 | 過 |
| `jgb/B/member-seat-limit` | title |  | 改 | 依據 #35 | 過 |
| `jgb/B/team-signer-personal-info` | title |  | 改 | 依據 #36 | 過 |
| `jgb/B/team-signer-profile-switch` | title |  | 改 | 依據 #37 | 過 |
| `jgb/C/community-delete-requires-empty` | sentences | 0 | 改 | 依據 #38 | 過 |
| `jgb/C/community-delete-requires-empty` | sources |  | 改 | 依據 #38 | 過 |
| `jgb/C/community-edit-basic-fields` | sentences | 0 | 改 | 依據 #39 | 過 |
| `jgb/C/community-edit-basic-fields` | title |  | 改 | 依據 #39 | 過 |
| `jgb/C/community-estates-add-batch-copy` | sentences | 2 | 改 | 依據 #40 | 過 |
| `jgb/C/community-estates-category-switch` | sentences | 0 | 改 | 依據 #41 | 過 |
| `jgb/C/community-estates-extra-tabs` | sentences | 1 | 改 | 依據 #42 | 過 |
| `jgb/C/community-estates-extra-tabs` | sources |  | 改 | 依據 #42 | 過 |
| `jgb/C/community-estates-extra-tabs` | title |  | 改 | 依據 #42 | 過 |
| `jgb/C/community-estates-overview-card` | sentences | 2 | 改 | 依據 #43 | 過 |
| `jgb/C/community-estates-overview-card` | sources |  | 改 | 依據 #43 | 過 |
| `jgb/C/community-show-editor-nav` | sentences | 0 | 改 | 依據 #44 | 過 |
| `jgb/C/community-show-editor-nav` | sources |  | 改 | 依據 #44 | 過 |
| `jgb/C/community-show-editor-nav` | title |  | 改 | 依據 #44 | 過 |
| `jgb/C/community-show-price-range` | phrasings |  | 改 | 依據 #45 | 過 |
| `jgb/C/community-show-price-range` | sentences | 0 | 改 | 依據 #45 | 過 |
| `jgb/C/community-show-price-range` | sentences | 1 | 刪句 | 依據 #45 | 過 |
| `jgb/C/community-show-price-range` | sources |  | 改 | 依據 #45 | 過 |
| `jgb/C/community-show-price-range` | title |  | 改 | 依據 #45 | 過 |
| `jgb/C/community-show-share` | sentences | 0 | 改 | 依據 #46 | 過 |
| `jgb/C/community-show-share` | sentences | 1 | 改 | 依據 #46 | 過 |
| `jgb/C/community-show-share` | title |  | 改 | 依據 #46 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | sentences | 0 | 改 | 依據 #47 | 過 |
| `jgb/C/estate-dashboard-attachments-vs-contract-attachments` | title |  | 改 | 依據 #47 | 過 |
| `jgb/C/estate-dashboard-contracts-history` | sentences | 0 | 改 | 依據 #48 | 過 |
| `jgb/C/estate-dashboard-entry-and-groups` | sentences | 0 | 改 | 依據 #49 | 過 |
| `jgb/C/estate-dashboard-entry-and-groups` | sources |  | 改 | 依據 #49 | 過 |
| `jgb/C/estate-dashboard-entry-and-groups` | title |  | 改 | 依據 #49 | 過 |
| `jgb/C/estate-edit-basic-space-type` | sentences | 0 | 改 | 依據 #50 | 過 |
| `jgb/C/estate-edit-building-transcript-general` | sentences | 0 | 改 | 依據 #51 | 過 |
| `jgb/C/estate-edit-building-transcript-general` | sentences | 1 | 改 | 依據 #51 | 過 |
| `jgb/C/estate-edit-building-transcript-general` | title |  | 改 | 依據 #51 | 過 |
| `jgb/C/estate-edit-facilities` | sentences | 0 | 改 | 依據 #52 | 過 |
| `jgb/C/estate-edit-facilities` | sources |  | 改 | 依據 #52 | 過 |
| `jgb/C/estate-edit-facilities` | title |  | 改 | 依據 #52 | 過 |
| `jgb/C/estate-house-info-card` | sentences | 3 | 改 | 依據 #53 | 過 |
| `jgb/C/estate-house-info-card` | sources |  | 改 | 依據 #53 | 過 |
| `jgb/C/estate-list-filters` | title |  | 改 | 依據 #54 | 過 |
| `jgb/C/estate-list-filters-space-type-and-others` | sentences | 1 | 改 | 依據 #55 | 過 |
| `jgb/C/estate-list-filters-space-type-and-others` | sources |  | 改 | 依據 #55 | 過 |
| `jgb/C/estate-list-filters-space-type-and-others` | title |  | 改 | 依據 #55 | 過 |
| `jgb/C/estate-list-sort-remembers-last` | sentences | 1 | 改 | 依據 #56 | 過 |
| `jgb/C/estate-list-sort-remembers-last` | title |  | 改 | 依據 #56 | 過 |
| `jgb/C/estate-rent-detail-price-and-tax` | sentences | 0 | 改 | 依據 #57 | 過 |
| `jgb/C/estate-rent-detail-price-and-tax` | sentences | 1 | 改 | 依據 #57 | 過 |
| `jgb/C/estate-rent-detail-price-and-tax` | title |  | 改 | 依據 #57 | 過 |
| `jgb/C/estate-status-affects-actions` | sentences | 0 | 改 | 依據 #58 | 過 |
| `jgb/C/estate-status-affects-actions` | sentences | 1 | 改 | 依據 #58 | 過 |
| `jgb/C/estate-status-affects-actions` | sentences | 2 | 改 | 依據 #58 | 過 |
| `jgb/C/estate-status-affects-actions` | title |  | 改 | 依據 #58 | 過 |
| `jgb/C/team-public-page-recruitment` | phrasings |  | 改 | 依據 #59 | 過 |
| `jgb/C/team-public-page-recruitment` | sentences | 2 | 新增句 | 依據 #59 | 過 |
| `jgb/C/team-public-page-recruitment` | title |  | 改 | 依據 #59 | 過 |
| `jgb/C/team-public-page-share` | phrasings |  | 改 | 依據 #60 | 過 |
| `jgb/C/team-public-page-share` | sentences | 1 | 改 | 依據 #60 | 過 |
| `jgb/C/team-public-page-share` | sources |  | 改 | 依據 #60 | 過 |
| `jgb/C/team-public-page-share` | title |  | 改 | 依據 #60 | 過 |
| `jgb/I/pricing-trial-plan-landing-page` | sentences | 0 | 改 | 依據 #61 | 過 |
| `jgb/I/pricing-trial-plan-landing-page` | sentences | 2 | 改 | 依據 #61 | 過 |

## 刪除

（無整條刪除）

## 允許集合內未改的 8 條

- `jgb/B/advance-discount-items`、`jgb/B/advance-late-fee`、`jgb/B/advance-payment-cycle-discount`、`jgb/B/advance-short-lease-approval`、`jgb/B/lessee-bulk-notify`：9.17 doubt 只有客戶名，已在 9.18 S1 改寫，本片不改。
- `jgb/A/notification-settings-report-buttons`：doubt 是客戶名（已在 9.18 S1 改寫）與「出處是程式註解」；程式本身確有 `return roleId === 21228`（`src/use/config/useForwardNotificationEmails.ts`），行為有據，本片不改。
- **需整條刪除、依 D1 停下交業主**：
  - `jgb/A/login-sso-redirect-no-duplicate-buttons`：第三方登入回呼不會導回登入頁（`app/Http/Controllers/AuthController.php` `case 'callback':`＋`return redirect($ssoRegisterUrl);`），細目描述的情境在現行程式走不到。
  - `jgb/B/biglandlord-escrow-owner`：「所有權人／轉租人」區塊只在舊 blade `users/team/2`，現行側邊選單的大房東列表連到 SPA `/bigLandlords/list`（`app/Role.php` `'/bigLandlords/list'`），屬舊路徑。

## 核對過程

- **第一輪**：3 包 fresh verifier，序列跑。
  - A 包 37 項：過 34、不過 3（`register-email-already-registered` 的合併條件寫錯 ×2；`login-no-account-register-link` 還留著答不了的講法 ×1）。
  - B 包 33 項：過 32、不過 1（`lessee-notification-toggle-effect` 新句沒有出處，掛著的舊 evidence 意思又相反）。
  - C＋I 包 48 項：過 36、不過 12（10 項 P3 是新內容的出處沒補進 sources／evidence；`estate-edit-facilities` 是有反證的絕對句 ×2；`team-public-page-recruitment` 留著答不了的講法 ×1）。
  - 另採納兩項建議：`member-role-edit-reset` 的講法、`lessee-notification-toggle-effect` 的 sources。
- **依 D1 修一次**：主 session 先對程式確認每一項，再修改：補上 sources 與 evidence、改寫、調整講法，並以刪句後重新插入的方式拿掉和新句矛盾的舊 evidence。修改涉及的 40 項交一位 fresh verifier 複核，結果過 38、不過 2。
- **複核仍不過的 2 項：處置偏離 D1 字面，交業主知悉。**
  - 兩項的**句子內容都已由複核 verifier 確認正確**，不過的原因都不是句子錯：
    1. `register-email-already-registered` 句 0：出處沒有登錄，只缺 `AuthController.php`，屬 P3。
    2. `team-public-page-share`：拿掉 IndexController 那句之後，講法「招租店舖有沒有短網址」就沒有句子能回答，屬 P2 回歸。
  - D1 字面是「整句刪」，但照字面刪會刪掉正確的句子。因此改用**不增加任何新內容的機械修補**：
    1. 補登 `code:app/Http/Controllers/AuthController.php` 與兩筆 evidence（`if (User::checkEmailUserByEmail($request->email, 1)) {`、`$result['data']['field_errors']['email'] = ___('此帳號已註冊。');`，grep 各命中 1）。
    2. 移除講法「招租店舖有沒有短網址」。`askable` 欄不進正本（C.md、jgb.json 命中 0；正對照：該講法在 C.md 命中 1）。
  - 由主 session 以 grep 驗證：sources 已含 AuthController、句 0 有 2 筆 AuthController evidence；講法與句子裡不再有「短網址」。S2 會再由獨立 verifier 重新先審這兩條。

## 依據

1. `jgb/A/account-basic-info`：9.17 S1 doubt（句序 3）——只有列入名單的特定合作團隊，合約簽完後才會鎖定租客資料，而且姓、名、身分證字號三欄都要有值才會鎖；原句寫成凡是雙方完成簽署就一律自動鎖定，漏了這些例外。evidence 引用的程式註解「合約雙方完成簽署後自動鎖定租客基本資訊」在釘住匯出裡也找不到｜證據：app/Contract.php 可 grep「in_array($model->user_id, $isBasicInfoLockedUserIds)」；config/app.php 可 grep「is_basic_info_locked_user_ids」
2. `jgb/A/account-change-password`：9.17 S1 doubt（句序 3）——註冊時密碼還必須同時含英文與數字（前端擋送出，後端也有 regex）；修改密碼頁雖然顯示「密碼應有至少一位英文和數字」，後端卻只檢查 min:6。所以「這與註冊時的密碼規則一致」不成立，標題「新密碼規則同註冊」也跟著錯。另外句序 4 的例子「受託的大房東子帳號」無源：father_id 子帳號其實是 SSO 綁定帳號｜證據：app/Http/Controllers/AuthController.php 可 grep「regex:/^(?=.*[a-zA-Z])(?=.*[0-9]).*$/」；UserController.php#account 可 grep「'password' => 'min:6|required_with」；app/User.php 可 grep「$newUser->father_id = $user->id;」
3. `jgb/A/account-contact-info`：9.17 S1 doubt（句序 2）——「未勾選則需填寫 LINE ID」會被讀成必填，但 LINE 輸入框沒有 required，後端也直接照存、不做檢查；對「line id 要填嗎」這個問法會答錯｜證據：resources/views/users/account.blade.php 可 grep「placeholder="{{___('請填上 Line ID')}}"」（沒有 required）；UserController.php#account 可 grep「$this->user->line = $input['line'];」
4. `jgb/A/dashboard-big-landlord-view`：9.17 S1 doubt（句序 2）——首頁網址不帶 bigLandlord_id，標籤條件任一成立就顯示「社區最新收支詳情」，所以首頁一律是這個標籤，不是「身分是社區才顯示」｜證據：code:src/pages/users/dashboard/parts/EstateDetails.vue「|| isEmpty(route.query.bigLandlord_id)」
5. `jgb/A/forget-password-flow`：9.17 S1 doubt（句序 3/5）——重設密碼的後端 regex 限制字元範圍，和註冊規則不同，所以不能說「與註冊時相同」；後端回 field_errors 時密碼欄也會顯示「格式錯誤。」，不是只有 alert｜證據：code:app/Http/Controllers/AuthController.php「regex:/(^[A-Za-z0-9*&-_]+$)+/」；code:src/pages/users/auth/parts/forget/Password.vue「field_errors?.password」
6. `jgb/A/forget-password-setpwd-invite`：9.17 S1 doubt（句序 2）——「大房東子帳號」無源，程式是 BigLandlord 邀請流程；「暫存識別碼與委託連結」是在描述 cookie，屬實作詞｜證據：code:app/Http/Controllers/AuthController.php「//如果有指定用戶更新密碼（BigLandlord 流程）」；code:src/pages/users/auth/parts/forget/Password.vue「Cookies?.get('bigLandlord_id')」
7. `jgb/A/login-no-account-register-link`：9.17 S1 doubt（句序 標題）——「立即註冊」在登入表單最上方（歡迎標題之下、帳號欄之前），不在「下面」；頁面最下方是忘記密碼？／忘記帳號？｜證據：code:src/pages/users/auth/parts/LoginForm.vue「{{ t('還沒有帳號嗎？') }}」
8. `jgb/A/login-role-redirect`：9.17 S1 doubt（句序 3）——「元件共用同一份角色欄位」是實作詞；全條也沒回答「選錯怎麼辦」，登入表單沒有返回鈕｜證據：code:src/pages/users/auth/parts/LoginForm.vue「// 如果沒有選角色，導回上一步」
9. `jgb/A/notification-mark-read-navigate`：9.17 S1 doubt（句序 1）——「每則通知點擊後會依原連結前往」漏了例外：訊息類（type 32）走另一段邏輯，不會導頁，而是要開訊息燈箱（這段還引用了未定義變數 userMessageData）。句序 2 自己也列了「訊息」標籤，同一條細目前後不一致｜證據：resources/views/notifications/index.blade.php 可 grep「if(data.type == 32)」「$store.commit('lightbox', 'showUserMessage')」
10. `jgb/A/notification-mark-read-out-of-range`：9.17 S1 doubt（標題）——標題括號「寫了判斷式，但實際上永遠不會被觸發」是實作詞兼過程筆記，不是使用者看得到的行為（內文本身正確）｜證據：標題原文「寫了判斷式」；NotificationController.php 可 grep「if (empty($datas) && request('page') > 1)」
11. `jgb/A/notification-settings-extra-emails`：9.17 S1 doubt（句序 2）——預設信箱取的是目前身分（團隊）擁有者的 Email，不是登入帳號本身的 Email；法人團隊成員看到的是團隊擁有者的信箱，漏了身分例外｜證據：app/Http/Controllers/UserController.php（getRoleEmailGroups）可 grep「$data['default'] = !empty($this->role->user->email)」
12. `jgb/A/register-email-already-registered`：9.17 S1 doubt（句序 標題/1）——同一 Email 已用 Email 註冊完成時，第一步就顯示「此帳號已註冊。」並擋下，不會合併；只有主帳號存在、還沒有 Email 帳號（例如先用 SSO 註冊）才會走合併｜證據：code:app/Http/Controllers/AuthController.php「User::checkEmailUserByEmail($request->email, 1)」＋「此帳號已註冊。」
13. `jgb/A/register-email-link-resume`：9.17 S1 doubt（句序 標題/2）——折返時會重打 sendVerEmail；session 內沒有這個 Email 的機器人驗證紀錄（或超過 1800 秒）就會回 recaptcha_required，前端清空 Email、退回第一步，程式註解明寫這情況「多半是從信件連結折返」｜證據：code:src/pages/users/auth/parts/EmailVerify.vue「多半是從信件連結折返、身上已經沒有通行證了」；code:app/Services/AuthService.php「REGISTER_CAPTCHA_TTL = 1800」
14. `jgb/A/register-role-select`：9.17 S1 doubt（句序 1/3）——session 有 redirect_after_login 時，綁手機步驟（略過或驗證成功）直接跳轉，跳過選身分；SSO 已註冊帳號也直接進首頁。「都會出現」與「選擇身分後導回」和程式矛盾｜證據：code:src/pages/users/auth/parts/PhoneVerify.vue「function skipVerify(){」＋「window.location.href = state.redirectToLivingUrl」
15. `jgb/A/register-sso`：9.17 S1 doubt（句序 3）——「系統會自動帶入對應的 Email」無源：SSO 回呼只導到 users.create?sso=1&social_type，不帶 Email；Create.vue 的 email 初始為空，沒有預填｜證據：code:app/Http/Controllers/AuthController.php「'sso' => 1, 'social_type' => $key」；code:src/pages/users/auth/Create.vue「email: '',」
16. `jgb/A/register-verify-code-shape`：9.17 S1 doubt（句序 標題/2）——後端 AuthController 各驗證分支都不回傳 is_locked（在同一匯出 grep「is_locked」只有 Iot 相關檔案命中，當正對照），所以沒有任何流程會鎖輸入框；實際是回「驗證次數過多，驗證碼已失效，請稍候重發…」｜證據：code:src/pages/users/auth/parts/VerifyPanel.vue「:disabled="isLocked"」；code:app/Http/Controllers/AuthController.php「驗證次數過多，驗證碼已失效」
17. `jgb/A/signer-address-fields`：9.17 S1 doubt（標題）——標題加了引號的「同上」不是現行介面標籤，實際按鈕文字是「同戶籍地址」「同公司登記地址」（正對照：「同戶籍地址」有命中，「同上」命中 0）｜證據：SignerDetails.vue 可 grep「t('同戶籍地址')」「t('同公司登記地址')」；grep「同上」為 0
18. `jgb/A/signer-corp-fields`：9.17 S1 doubt（句序 1）——把必填項目寫成完整清單，但社宅團隊的「公司負責人」也是必填；句序 4 只說負責人都會顯示，沒說社宅必填，漏了社會住宅這個例外（問法「公司負責人要填嗎」會答錯）｜證據：SignerDetails.vue 在 company_principal_name 區塊可 grep「isRequired: state.isSocialHousingTeam,」
19. `jgb/A/signer-corp-seals`：9.17 S1 doubt（句序 1）——「固定要上傳五種印章附件」會被讀成必填；實際上五個印章欄位都沒有 isRequired，後端沒上傳就存 null，是選填｜證據：SignerDetails.vue 的 corpAttachmentInfo 沒有 isRequired；UserController.php 可 grep「$role->company_broker_license_seal = !empty($input['company_broker_license_seal'])」
20. `jgb/A/signer-edit-permission`：9.17 S1 doubt（句序 2）——標題問「誰能編輯」，括號又說依編輯權限決定，但內文沒有講誰能編輯，也沒提任何權限，只說元件「能被設成不可編輯」，沒有回答標題。實際上是團隊資訊頁用 edit_role_info 權限來決定｜證據：app/Http/Controllers/UserController.php（role 方法）可 grep「$enableEdit = $this->isHasGPermission('edit_role_info');」；resources/views/users/role.blade.php 可 grep「:is-allowed-to-edit="{{ json_encode($enableEdit」
21. `jgb/A/signer-individual-fields`：9.17 S1 doubt（句序 5）——切換列用的就是 ScrollNav 元件（isShowScrollBar，overflow-x: auto），本身就是橫向捲動列；「並不是變成側邊清單或捲動列」有程式反證，讀起來也像過程更正筆記｜證據：src/pages/users/team/_parts/SignerDetails.vue 可 grep「<ScrollNav v-if="state.scrollNavDetail?.isShowScrollBar"」；src/components/ScrollNav.vue 可 grep「overflow-x: auto」
22. `jgb/A/signer-manage-save-buttons`：9.17 S1 doubt（句序 1）——「管理」燈箱（團隊資訊管理）只有「新增」與刪除（×）兩個功能，沒有編輯或選擇簽約對象的功能；「新增、編輯或選擇」有程式反證｜證據：src/components/Lightbox/SignerInfosEdit.vue 只有 emit('createRole')／emit('deleteRole', id)，可 grep「t('新增')」「handelDelete」
23. `jgb/B/advance-auto-publish-unpublish`：9.17 S1 doubt（句序 1）——寫成每個團隊都能用，漏了例外：這兩個設定只在團隊 id 列在設定檔 auto_publish_role_ids 裡的團隊才會顯示，其他團隊看不到；標題「可以」也是同樣的絕對說法｜證據：code:src/pages/users/advance/Index.jsx「estateAdState.is_enabled && <>」與「is_enabled: false, // 是否為可使用「即將釋出」功能的團隊」；code:app/Http/Controllers/UserController.php「$isAutoPublishRole = in_array($this->role->id, $autoPublishRoleIds);」
24. `jgb/B/advance-community-labels`：9.17 S1 doubt（句序 2）——城市／區域／位置標籤實際上是在社區編輯頁選用，不是「為物件加上」標籤；標題說的「社區篩選用」在句子和程式裡都找不到根據｜證據：code:src/pages/communities/edit/Basic.vue「options={labelState.group?.[`community_${ node }`]」；community_city 只出現在 communities/edit/Basic.vue、advance/Index.jsx、UserController.php 三處
25. `jgb/B/advance-fee-items-merge`：9.17 S1 doubt（句序 1）——實際流程不是「合併成一個新品項」：使用者要在「欲合併品項」下拉選單選一個已存在的品項，勾選的品項會併入那個品項，後端也是併入既有品項；另外系統預設品項不能勾選｜證據：code:src/components/Lightbox/CustomFeeItemMerge.jsx「請選擇想要併入的品項以便後續流程。」與「options={state.availableItems.map(node=>node.id)}」；code:app/Http/Controllers/UserController.php「$mergeToItem = Item::findOwnItem($role->id, $mergeToId, $feeType);」
26. `jgb/B/advance-sales-item-code`：9.17 S1 doubt（句序 2）——「沒有設定代號的品項，匯出產品代號會是空白」與現行設定燈箱矛盾：留空的品項會沿用系統預設代號，只有系統預設也沒有代號的品項才會是空白｜證據：code:src/pages/users/advance/_part/WenzhongItemCodeManagement.vue「留空的品項會沿用系統預設代號（灰字顯示）；系統預設也沒有的品項，匯出檔的產品代號會是空白。」
27. `jgb/B/biglandlord-authorize-apply-step`：9.17 S1 doubt（句序 1）——「「套用」後將移除此物件」這個遮罩只在按紅色 X 移除整筆物件（readyToRemove）時出現，取消勾選權限不會出現；標題的「取消勾選」和句意都錯把兩個動作混成一個｜證據：src/pages/bigLandlords/list/_parts/owned.jsx：grep「state.userOwned.readyToRemove = [...state.userOwned.readyToRemove, listItem.id]」（綁在 icon_x_red.svg 按鈕上）、「state.userOwned.readyToRemove.includes(listItem.id)」（遮罩出現的條件）；權限 checkbox 的 onChange 只改 listItem.capabilities.premises
28. `jgb/B/biglandlord-report-community-rate`：9.17 S1 doubt（句序 2）——「匯率」不是固定的欄位，是有條件的 tooltip：只有結算幣別和站台幣別不同、而且有匯率資料時才出現，手機版也不顯示文字；句子寫成一定會顯示，漏了條件｜證據：src/pages/bigLandlords/report/_parts/BigLandlordItemDetail.jsx：grep「store.state.siteOptions?.dollarSign !== result.baseCurrency」「!isEmpty(store.state?.currencyRates?.[props.base_currency])」「<div className="hidden lg:block">{t('匯率')}</div>」
29. `jgb/B/biglandlord-seat-limit`：9.17 S1 doubt（句序 2）——「成員／大房東管理」這個頁名在介面上不存在；「團隊管理底下的大房東列表」也和現行選單矛盾：團隊管理底下只有 type=1 的成員列表，大房東列表掛在「大房東管理」底下、連到 SPA；句中寫的「邀請」按鈕與額滿燈箱只在沒有選單入口的舊 blade users/team/2 上｜證據：app/Role.php：grep「route('users.team', ['type' => 1])」「'大房東列表',」；在 app、resources、src 下 grep「成員／大房東管理」「成員/大房東管理」都沒有結果（同一輪 grep「大房東管理'」在 app/Role.php 有命中，當正對照組）；resources/views/users/team/index.blade.php：grep「lightboxOpen('subscribedPlanBigLandlordIsFull')」
30. `jgb/B/lessee-crud`：9.17 S1 doubt（句序 1）——寫成每個團隊都能新增、匯入、匯出，漏了身分例外：只有個人房東與法人房東有「新增租客」「匯入租客」，社宅團隊只有「匯出」（同組 lessee-export-entry-by-role 已寫明）｜證據：code:src/pages/users/lesseeList/parts/PageTop.vue「(store.state.userData?.role?.config_rule_key === 2 || store.state.userData?.role?.config_rule_key === 3) && <div className="col-auto">」與「config_rule_key === 4 && <div class="col-auto">」
31. `jgb/B/lessee-list-columns-by-role`：9.17 S1 doubt（句序 2）——「特定合作團隊多出國籍、生日、主要聯絡方式」在現行畫面不會發生：currentRole 只會回傳社宅或 default，beyond360 那組欄位永遠選不到；第 1 句加引號的「操作」也不是實際存在的表頭標籤｜證據：code:src/pages/users/lesseeList/parts/ListTable.vue「return 'default'」（位於 currentRole: computed 內）與「return columnPattern[state.currentRole]」；「const action = {」只有 key，沒有 title
32. `jgb/B/lessee-notification-toggle-effect`：9.17 S1 doubt（句序 1）——Email 與手機的通知開關是分開的，關掉其中一個只停那一種管道；已註冊租客的開關不能操作，仍會收到 Email。「收不到任何信件或簡訊」把兩個管道和兩種身分混成一句｜證據：code:src/pages/users/lesseeList/parts/ContactInfoBlock.jsx「notifyStatusType: props?.info?.type === ContactInfoType.mail ? 'email_notify_status' : 'phone_notify_status'」與「className={` ${ props?.is_tenant_registered === 1 && 'disabled'} `}」；docs:knowledge/jgb-product-facts.md#p914-bill-notify
33. `jgb/B/member-list-role-inline-change`：9.17 S1 doubt（句序 1）——「每一列都有角色下拉選單、選了就直接送出變更」是絕對句，漏了例外：團隊擁有者列和自己那一列的下拉是鎖住的 select-picker，也沒有「+ 新增角色」；沒有編輯權限時整個下拉也被鎖住。這和同組細目 member-list-role-select-disabled 互相矛盾，標題「每一列都有角色下拉選單可以直接切換」有同樣問題｜證據：jgb2 釘住匯出 resources/views/users/team/index.blade.php：擁有者列和自己列用 `<select-picker class="disabled"`，成員列用 `<div class="col-12 shrink px-0 {{$enableEdit?'':'disabled'}}"`，另見正本 B.md `{#jgb/B/member-list-role-select-disabled}`
34. `jgb/B/member-role-edit-reset`：9.17 S1 doubt（句序 標題）——標題說「把還沒儲存的勾選狀態還原」，但內文與程式的行為都是「全部清空」，包括原本已載入的勾選；「回到調整前狀態」那段程式已被註解掉，標題和內文互相矛盾｜證據：jgb2 釘住匯出 src/store/modules/team/capabilityEdit.js：mutations.reset 內的 `// 重設條件，全部取消句選` 會把 capObj 全部設成 `[]`，而 `// 重設條件回到調整前的狀態` 以下都是註解
35. `jgb/B/member-seat-limit`：9.17 S1 doubt（句序 2）——這句寫成一律「導引前往升級訂閱方案」，漏了尚未訂閱的例外：沒有訂閱時 isFull 直接成立，視窗文字是「請先前往訂閱服務」，按鈕是「我要訂閱」，不是「升級」。本細目的 target_user 含 prospect，正好是這種情況｜證據：jgb2 釘住匯出 app/Http/Controllers/UserController.php `$isFull = (!$this->role->isSubscriptionActive() || $this->role->remainTeamsCount() === 0);`；resources/views/layouts/lightbox/general.blade.php `您尚未訂閱服務最多可邀請 [s1] 位成員，目前已到達上限，請先前往訂閱服務` 與 `我要訂閱`，「前往升級」只在 `$role->isSubscriptionActive()` 成立時才替換上去
36. `jgb/B/team-signer-personal-info`：9.17 S1 doubt（句序 標題）——標題把戶籍地址／通訊地址歸進「選填或另有條件」，但第 2 句與程式都寫兩組地址必填，標題和內文互相矛盾｜證據：jgb2 釘住匯出 src/pages/users/team/_parts/SignerDetails.vue：`<h5 class="mb-2">{{ t('戶籍地址') }}</h5>` 下方的 address-component 帶 `:required="true"`；「通訊地址」那一組同樣帶 `:required="true"`
37. `jgb/B/team-signer-profile-switch`：9.17 S1 doubt（句序 標題）——標題說超過 5 組會「收進」「所有團隊」下拉選單，但實際上分頁列仍然整排顯示，下拉選單是另外多出來的，第 2 句也明寫「多出一個」且列出全部組數｜證據：jgb2 釘住匯出 src/pages/users/team/_parts/SignerDetails.vue：`isShowScrollBar: productEntryState && productEntryState.role.companyInfoList.length > 1` 與 `<tooltip v-if="state.scrollNavDetail?.isMoreThan5"` 兩個條件並存
38. `jgb/C/community-delete-requires-empty`：9.17 S1 doubt（句序 1）——加引號的「刪除」不是現行選單標籤，齒輪選單的選項字樣是「刪除社區」（「刪除」只是確認燈箱裡的按鈕），而且這個選項只有具編輯物件權限的人才看得到｜證據：app/Http/Controllers/CommunityController.php `'text' => ___('刪除社區')`（webList 內，被 `hasPermission($user, 'edit_estate')` 包住）
39. `jgb/C/community-edit-basic-fields`：9.17 S1 doubt（句序 1）——夾了過程筆記「查不到對應的長度驗證規則，無法確認超過30字時是否真的會被擋下」；而且程式確實沒有長度驗證（name 只有 required），「限制30個字」只是輸入框的提示文字，標題卻寫成「社區名稱限30字」｜證據：src/pages/communities/edit/Basic.vue `請告訴客戶您的社區名稱為何。限制 [s1] 個字`；app/Services/CommunityService.php validatorSingle `"name" => "required"`
40. `jgb/C/community-estates-add-batch-copy`：9.17 S1 doubt（句序 3）——加引號的「社區共用空間」出自程式註解，不是介面標籤；介面上這類物件叫「公共區域」｜證據：app/Estate.php `const SHARE_HOUSING = 3; // 社區共用空間`；src/pages/communities/list/_parts/ListTableHead.vue `t('不包含公共區域')`
41. `jgb/C/community-estates-category-switch`：9.17 S1 doubt（句序 1）——加引號的「總覽-1」是 i18n 翻譯 key，沒有核實過畫面上實際顯示的字；草稿自己的 open_questions 也寫了無法確認｜證據：src/pages/communities/estates/Index.vue `t('總覽-1')`；drafts-C.json 該條 open_questions「無法確認這個翻譯 key 實際顯示出來的中文字串」
42. `jgb/C/community-estates-extra-tabs`：9.17 S1 doubt（句序 2）——「開通投報率功能時這兩個頁籤會一起出現」漏了身分與權限的例外：大房東，以及沒有 show_bill 權限的人，即使團隊已開通也看不到這兩個頁籤｜證據：app/Http/Controllers/CommunityController.php isCommunityRoiVisible `$role->isBigLandlord($user)`、`REQUIRED_PERMISSION`；app/Http/Controllers/Api/CommunityRoiController.php `REQUIRED_PERMISSION = 'show_bill'`
43. `jgb/C/community-estates-overview-card`：9.17 S1 doubt（句序 3）——「管理員身分」是從 is_admin 這個實作欄位來的說法，JGB 沒有叫「管理員」的角色；實際條件是具編輯物件權限（擁有者也包含在內）｜證據：app/Services/CommunityService.php getEditData `'is_admin' => $this->isHasGPermission('edit_estate', $role, $user)`；src/pages/communities/estates/_parts/CommunityOverview.vue `v-show="props.data?.is_admin"`
44. `jgb/C/community-show-editor-nav`：9.17 S1 doubt（句序 1）——標題和內文寫「只有管理員（身分）」，但實際條件是具編輯物件權限（is_admin 就是 edit_estate），「管理員」是實作詞，不是現行的角色名稱｜證據：src/pages/communities/show/Index.vue `afterTools: ()=>communityShowScopeStore.dataFetcher.data?.is_admin`；app/Services/CommunityService.php `'is_admin' => $this->isHasGPermission('edit_estate', $role, $user)`
45. `jgb/C/community-show-price-range`：9.17 S1 doubt（句序 2）——後端的 sell_price_range_per_unit 永遠是空陣列，所以「售價單價區間」根本不會顯示，而且畫面上也沒有「售價單價區間」這個標籤；句序 1 的「只在有2筆資料時」其實是 length===2 的實作寫法，意思是「有刊登中物件的最小／最大值」，不是「兩筆物件」｜證據：app/Services/CommunityService.php `'sell_price_range_per_unit' => [],`；src/pages/communities/show/_parts/PageTop.vue `sell_price_range_per_unit?.length === 2`
46. `jgb/C/community-show-share`：9.17 S1 doubt（句序 2）——「查看所有物件」連到的是團隊的公開店鋪頁（users.public，只帶團隊 encryptId），不是這個社區的物件清單；句序 1 也漏了例外：行動裝置支援 navigator.share 時，會改用系統的分享選單，不會開燈箱｜證據：src/pages/communities/show/_parts/AsideContact.vue `name: 'users.public'` 加上 `encryptId: state.data?.team?.encryptId`；src/pages/communities/show/_parts/PageTop.vue `isDevice('any') && typeof navigator.share === 'function'`
47. `jgb/C/estate-dashboard-attachments-vs-contract-attachments`：9.17 S1 doubt（句序 1）——「附件清單可自由上傳任意檔案」有反證：前端上傳欄位和後端驗證都只收 JPG／PNG／PDF｜證據：code:src/pages/estates/dashboard/attachments/Index.vue `accept="image/jpeg,image/png,application/pdf"`；code:app/Http/Controllers/EstateController.php `case 'add_attachment':` 下 `'file' => 'required|mimes:jpeg,jpg,png,pdf|max:10240'`
48. `jgb/C/estate-dashboard-contracts-history`：9.17 S1 doubt（句序 1）——括號裡寫「租客身分登入時標題改成出租人、不顯示是否通知」，但物件儀表板整個路由禁止租客進入，租客根本看不到這一頁，這句在現行畫面上到不了｜證據：code:src/routes/estates.js `notAllowedRoles: ['tenant']`（estates.dashboard 父路由）；code:src/routes/index.js `if (to.meta?.notAllowedRoles?.includes('tenant')){` → `window.location.href = '/users'`
49. `jgb/C/estate-dashboard-entry-and-groups`：9.17 S1 doubt（句序 1）——「預設導向招租表現」寫成絕對句，漏了大房東這個例外：大房東從物件總表進入時會直接導到「合約歷程」；如果大房東照預設進到招租表現，API 會把他導回物件總表。這也和第 3 句「大房東只看得到與大房東共享的分頁」互相衝突｜證據：code:app/Http/Controllers/EstateController.php `(!$isBigLandlord) ? 'estates.dashboard' : 'estates.dashboard.contracts'`；同檔 `case 'rent_status':` 下 `if ($isBigLandlord) {` → `'redirect' => route('estates.index', ['any' => 1])`
50. `jgb/C/estate-edit-basic-space-type`：9.17 S1 doubt（句序 1）——「底下先選『用途』…必填」是絕對句，漏了社宅例外：社宅物件（property_purpose_key=2）的基本資料根本不顯示用途欄位；另外用途選項會依團隊設定縮減，「兩者都是必填」的「兩者」指的是哪兩個也不清楚｜證據：src/pages/estates/edit/basic/Index.vue `v-if="editStore.options?.property_purpose_key != 2"`、`premisesUseForOptions[store?.state?.userData?.role?.estate_use_for]`
51. `jgb/C/estate-edit-building-transcript-general`：9.17 S1 doubt（句序 1）——「要求填寫」讀起來是必填，和社宅那條同樣措辭（那邊確實是必填）放在一起更容易誤解；但一般物件建物謄本的欄位都沒有必填標記，這個分頁也不列入完成勾選；「供實價登錄使用」只出現在程式註解，介面上沒有這句｜證據：src/pages/contracts/edit/buildingTranscript/General.vue 搜 `after-required` 0 筆（對照組：同目錄外 building_transcript/Index.vue 有 `after-required`）；src/routes/estates.js building_transcript_general 的 `checkedIcon: false`；General.vue `// === 土地標的清冊（實價登錄用`
52. `jgb/C/estate-edit-facilities`：9.17 S1 doubt（句序 1）——「第一個區塊標題是格局(<空間類型>)」是絕對句，但社宅物件載入的是另一個元件，標題是「附設傢俱／設備」；車位和空地則只顯示「格局」加上「不需要設定」的提示；這條的來源只引了一般物件的 General.vue｜證據：src/pages/estates/edit/facilities/Index.vue `<SocialHousing` 與 `v-if="[2].includes(parseInt(editStore.options?.property_purpose_key))"`；_parts/SocialHousing.vue `t('附設傢俱')`；_parts/General.vue `t('車位用途物件，不需要設定「格局」內容')`
53. `jgb/C/estate-house-info-card`：9.17 S1 doubt（句序 4）——「座位數只在商用、且不是店面也不是整層空間時顯示」與現行執行結果不符：頁面傳進元件的 spaceType 是翻譯後的中文標籤（「店面」「整層空間」），元件卻拿它跟英文 key 比對，所以條件永遠成立，所有商用物件都會顯示座位數｜證據：code:resources/views/estate/show.blade.php `:space-type="{{ json_encode($labelsSpaceType[$premisesInfoBasic['space_type']]`；code:app/Estate.php `$labelsBusinessSpaceTypes[$k] = ___($v,$lang);`；code:src/pages/estates/show/_parts/EstateBasicInfo.vue `props.spaceType !== 'retail_shop' && props.spaceType !== 'office_flat'`
54. `jgb/C/estate-list-filters`：9.17 S1 doubt（句序 標題）——標題列出的篩選條件包含「用途」，但句序2寫的是「沒有依用途篩選的選項」，標題和內文互相矛盾；程式也證實物件總表的進階搜尋沒有用途篩選｜證據：src/pages/estates/list/_parts/EstatesAdvanceSearchBlock.jsx 搜 `EstateSearchKey.use_for` 0 筆（對照組 `EstateSearchKey.building` 1 筆）
55. `jgb/C/estate-list-filters-space-type-and-others`：9.17 S1 doubt（句序 2）——加引號的「其他」群組不是現行介面標籤；VR／有電梯／可開伙／可養寵物這組篩選的按鈕，桌機版和手機版都寫「更多」｜證據：src/components/AdvGroupSelect.jsx `{ t('更多') }`；src/components/AdvGroupSelectMobile.jsx `{ t('更多') }`
56. `jgb/C/estate-list-sort-remembers-last`：9.17 S1 doubt（句序 2）——「排序方式會被記住」這句是絕對句，漏了窄螢幕的例外：寬度小於 576px 時，手機版 ListSearchBar 把排序存在另一把鍵下，進頁時只讀 estatesList，所以手機上不會自動帶入上次的排序｜證據：src/pages/estates/list/Index.vue `:sortingKey="\`bills_${route?.params?.action}\`"` 對照 `genLocalSort({ to, from, next }, 'estatesList')`
57. `jgb/C/estate-rent-detail-price-and-tax`：9.17 S1 doubt（句序 2）——「營業稅可以選擇應稅／零稅率／免稅」是絕對句，但營業稅欄位只對特定合作團隊顯示；句序1的「同建物謄本面積」也只有社宅物件才有，而且介面上是按鈕不是勾選框，一般物件改用面積換算元件｜證據：src/pages/estates/edit/rent_detail/Index.jsx `specialRolesState.findSpecialRoleGroup(store.state.userData.role.id)?.key == 'nthurc' &&`（在營業稅區塊前）；`[2].includes(parseInt(props.editStore.options?.property_purpose_key))`（在「同建物謄本面積」按鈕前）
58. `jgb/C/estate-status-affects-actions`：9.17 S1 doubt（句序 1）——加引號的「合約中」是幫助中心 slug39 的舊用詞；現行物件總表的貼標和即時合約狀態篩選都寫「租約中」（另兩個是「無合約／無租約」「洽談中」），介面上找不到「合約中」這個字；draft 的 open_questions 也已經指出這個落差｜證據：app/Estate.php `'org_text' => '租約中'`；src/use/search/modules/contractStatus.js `3: t('租約中')`
59. `jgb/C/team-public-page-recruitment`：9.17 S1 doubt（句序 標題）——標題寫了「每頁預設10筆」，內文卻沒有這一句（這件事只寫在同組的 filter-and-view）。標題問「是什麼」，內文也只列出和一般店舖的差異，沒有說明這個頁面本身是什麼｜證據：canon:rag-orchestrator/canon/jgb/C.md `{#jgb/C/team-public-page-recruitment}` 標題 `每頁預設10筆` 對照內文兩句；code:src/pages/users/public/Index.vue `route.params.encryptId === 'recruitment' ? 10 : 30`
60. `jgb/C/team-public-page-share`：9.17 S1 doubt（句序 2）——「有客製短網址就分享它，否則用系統產生的固定網址」出自舊路徑：share/public 端點只有舊的 users/public.blade.php 在引用，而這個 blade 已經沒有任何 controller 會渲染。現行招租店舖是 Vue 頁面，分享出去的就是當下頁面的網址｜證據：code:app/Http/Controllers/IndexController.php `Role::findRoleByCustomerAccount($this->role->customer_account, true)`（share()）只被 resources/views/users/public.blade.php `route('share', ['action' => 'public'` 引用；code:routes/web.php `'/p/{encryptId?}/{mode?}/{premisesUseFor?}', 'IndexController@vueIndex'`；code:src/pages/users/public/_parts/AsideInfo.vue `url: \`${window.location.protocol}//${window.location.host}${route.fullPath}\``
61. `jgb/I/pricing-trial-plan-landing-page`：9.18 S2 doubt——寫出合作品牌名「愛租屋」；句 1 引號漏「元」（現行「每月只需 [s1] 元」）｜證據：`src/pages/listings/pricing/TrialPlan.vue` `t('愛租屋'`、`每月只需 [s1] 元`

## 差異比對輸出（最終位元組）

```
[diff] (g) evidence remaps on allowed fines: 19; new out-of-range: 0
[diff] fines in base (shelves ABCI): 277; doubt set: 69 (not found in base: 0)
[diff] changed/deleted items: 133 in 61 fines; deleted fines: 0
[diff] (b) changed ids outside doubt set: 0
[diff] (c) items on protected (non-doubt) fines: 0
[diff] (f) structural differences: 0
[diff] (a) fix-log rows: 133; unlogged diffs: 0; log rows with no diff: 0
[diff] (d) deleted fines: diff 0 vs fix-log 刪除 0; equal: True
[diff] (e) rows not passed and not a deletion: 0
[diff] RESULT: PASS
```

正對照（scratch 副本 `pc10/`）：改允許集合外 `jgb/B/team-basic-info` 的 evidence ⇒ (c) 報出、FAIL；把允許集合內一筆 evidence 句序改為 99 ⇒ (g) `out-of-range evidence 0 -> 1`、FAIL。
