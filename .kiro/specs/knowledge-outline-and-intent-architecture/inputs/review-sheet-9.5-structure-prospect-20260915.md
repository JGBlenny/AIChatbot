# 步 2 歸屬審核單（prospect，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:kb:prospect/A/dashboard-overview` | 首頁儀表板顯示哪些數據 | `prospect/I/dashboard-overview` | 首頁儀表板顯示哪些數據 | move | ⚠️ I/H/I | |
| 2 | `tmp:kb:prospect/A/pain-points` | 你們能解決什麼問題（痛點對應模組） | `prospect/I/product-overview` | 系統總覽、能解決什麼問題與適不適合我 | merge | I/I/I | |
| 3 | `tmp:kb:prospect/A/product-overview` | 系統總覽與適不適合我 | `prospect/I/product-overview` | 系統總覽、能解決什麼問題與適不適合我 | merge | I/I/I | |
| 4 | `tmp:kb:prospect/A/why-choose-jgb` | 為什麼選金箍棒 | `prospect/I/why-choose-jgb` | 為什麼選金箍棒 | move | I/I/I | |
| 5 | `tmp:kb:prospect/B/data-migration` | 舊系統資料能否匯入（可匯入範圍） | `prospect/I/data-migration` | 舊系統資料能否匯入（可匯入範圍與不支援項目） | merge | I/I/I | |
| 6 | `tmp:kb:prospect/B/individual-landlord-scale-fit` | 個人房東（約 10～30 戶）適配與建議做法 | `prospect/I/individual-landlord-scale-fit` | 個人房東（約 10～30 戶）適配與建議做法 | move | I/I/I | |
| 7 | `tmp:kb:prospect/B/team-company-fit` | 公司或包租代管團隊適合嗎 | `prospect/I/team-company-fit` | 公司或包租代管團隊適合嗎 | move | I/I/I | |
| 8 | `tmp:kb:prospect/C/bill-contents-extra-fees` | 帳單內容與臨時加收費用 | `prospect/E/bill-contents-extra-fees` | 帳單內容與臨時加收費用 | move | E/E/E | |
| 9 | `tmp:kb:prospect/C/bill-format-customize` | 帳單版面能不能自訂 | `prospect/E/bill-format-customize` | 帳單版面能不能自訂 | move | E/E/E | |
| 10 | `tmp:kb:prospect/C/billing-overview` | 帳務管理模組做什麼 | `prospect/E/billing-overview` | 帳務管理模組做什麼 | split | E/E/E | |
| 11 | `tmp:kb:prospect/C/billing-overview` | 帳務管理模組做什麼 | `prospect/E/einvoice-issuing` | 電子發票能不能自動開、載具怎麼用 | split | E/E/E | |
| 12 | `tmp:kb:prospect/C/community-batch-create` | 社區建立與批次新增物件 | `prospect/C/community-batch-create` | 社區建立與批次新增物件 | keep | C/C/C | |
| 13 | `tmp:kb:prospect/C/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、批次續約） | `prospect/D/contract-batch-renewal` | 續約能不能批次處理 | split | D/D/D | |
| 14 | `tmp:kb:prospect/C/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、批次續約） | `prospect/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | split | D/D/D | |
| 15 | `tmp:kb:prospect/C/contract-history-retention` | 歷史合約保留多久 | `prospect/D/contract-history-retention` | 歷史合約保留多久（含點退狀態） | move | D/D/D | |
| 16 | `tmp:kb:prospect/C/contract-modify-after-sign` | 合約送出或簽完後能不能修改 | `prospect/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改 | move | D/D/D | |
| 17 | `tmp:kb:prospect/C/contract-templates` | 合約範本有哪些可以選 | `prospect/D/contract-templates` | 合約範本有哪些可以選 | split | D/D/D | |
| 18 | `tmp:kb:prospect/C/contract-templates` | 合約範本有哪些可以選 | `prospect/D/sublease-vs-management-contract` | 包租與代管在委託合約設定上的差別 | split | D/D/D | |
| 19 | `tmp:kb:prospect/C/credit-card-rent-payment` | 租客能不能用信用卡繳房租 | `prospect/E/credit-card-rent-payment` | 租客能不能用信用卡繳房租 | move | E/E/E | |
| 20 | `tmp:kb:prospect/C/notification-channels` | 系統通知管道與時機 | `prospect/A/account-registration` | 怎麼註冊帳號（含驗證碼通知） | split | ⚠️ A/A/E | |
| 21 | `tmp:kb:prospect/C/notification-channels` | 系統通知管道與時機 | `prospect/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | split | ⚠️ A/A/E | |
| 22 | `tmp:kb:prospect/C/notification-channels` | 系統通知管道與時機 | `prospect/E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（含繳費提醒通知） | split | ⚠️ A/A/E | |
| 23 | `tmp:kb:prospect/C/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦 | `prospect/E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（含繳費提醒通知） | merge | E/E/E | |
| 24 | `tmp:kb:prospect/C/owner-report-collection-remit` | 大房東報表與代收代付 | `prospect/B/owner-report-collection-remit` | 大房東報表與代收代付怎麼交代 | move | B/B/B | |
| 25 | `tmp:kb:prospect/C/payment-gateway-options` | 金流廠商差別與申請條件 | `prospect/E/payment-gateway-options` | 金流廠商差別與申請條件 | split | E/E/E | |
| 26 | `tmp:kb:prospect/C/payment-gateway-options` | 金流廠商差別與申請條件 | `prospect/E/virtual-account-prepaid` | 固定虛擬帳號與儲值金抵扣 | split | E/E/E | |
| 27 | `tmp:kb:prospect/C/property-management-overview` | 房源管理模組做什麼 | `prospect/C/property-management-overview` | 房源管理模組做什麼（含自訂狀態標籤） | keep | C/C/C | |
| 28 | `tmp:kb:prospect/C/property-status-meaning` | 物件狀態是什麼意思 | `prospect/C/property-status-meaning` | 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思 | keep | C/C/C | |
| 29 | `tmp:kb:prospect/C/rental-storefront-vr` | 招租店舖與 VR 看屋 | `prospect/C/rental-storefront-vr` | 招租店舖與 VR 看屋 | keep | C/C/C | |
| 30 | `tmp:kb:prospect/C/repair-system` | 線上報修與進度追蹤 | `prospect/F/repair-system` | 線上報修與進度追蹤 | move | F/F/F | |
| 31 | `tmp:kb:prospect/C/role-permission-granularity` | 成員權限能不能細分（只看不改、看不到財務） | `prospect/B/role-permission-granularity` | 成員權限能不能細分（只看不改、看不到財務） | move | B/B/B | |
| 32 | `tmp:kb:prospect/C/smart-meter-lock-iot` | 智慧電錶與門鎖整合 | `prospect/G/smart-meter-lock-iot` | 智慧電錶與門鎖整合 | move | G/G/G | |
| 33 | `tmp:kb:prospect/C/team-management-overview` | 團隊管理模組做什麼 | `prospect/B/team-management-overview` | 團隊管理模組做什麼 | move | B/B/B | |
| 34 | `tmp:kb:prospect/C/what-is-owner-landlord` | 大房東是什麼 | `prospect/B/what-is-owner-landlord` | 大房東是什麼 | move | B/B/B | |
| 35 | `tmp:kb:prospect/D/account-registration` | 怎麼註冊帳號 | `prospect/A/account-registration` | 怎麼註冊帳號（含驗證碼通知） | merge | A/A/A | |
| 36 | `tmp:kb:prospect/D/free-trial` | 可以免費試用嗎 | `prospect/I/free-trial` | 可以免費試用嗎 | move | I/I/I | |
| 37 | `tmp:kb:prospect/D/pricing-plans` | 怎麼收費 | `prospect/I/pricing-plans` | 怎麼收費 | move | I/I/I | |
| 38 | `tmp:kb:prospect/D/property-quota-limit` | 方案物件額度上限 | `prospect/I/property-quota-limit` | 方案物件額度上限與用滿怎麼辦 | move | I/I/I | |
| 39 | `tmp:kb:prospect/D/subscription-change-renewal` | 升級、續約與取消訂閱 | `prospect/I/subscription-change-renewal` | 升級、續約與取消訂閱 | move | I/I/I | |
| 40 | `tmp:kb:prospect/E/competitor-comparison` | 跟 Bananas、屋我也差在哪 | `prospect/I/competitor-comparison` | 跟 Bananas、屋我也差在哪 | move | I/I/I | |
| 41 | `tmp:kb:prospect/E/competitor-neutrality` | 會評論競爭對手嗎 | `prospect/I/competitor-neutrality` | 會評論競爭對手嗎 | move | I/I/I | |
| 42 | `tmp:kb:prospect/G/migration-limits` | 資料搬遷目前不支援的項目（合約與歷史帳單） | `prospect/I/data-migration` | 舊系統資料能否匯入（可匯入範圍與不支援項目） | merge | I/I/I | |
| 43 | `tmp:kb:prospect/G/utility-split-advice` | 水電費怎麼分算與大概多少錢 | `prospect/E/utility-split-calculation` | 水電費怎麼分算 | move | E/E/E | |

## B. 拆分（split）——一個舊細目拆成多個新細目

| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |
|---|---|---|---|
| `tmp:kb:prospect/C/billing-overview` | 帳務管理模組做什麼 | `prospect/E/billing-overview`《帳務管理模組做什麼》；`prospect/E/einvoice-issuing`《電子發票能不能自動開、載具怎麼用》 | |
| `tmp:kb:prospect/C/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、批次續約） | `prospect/D/contract-batch-renewal`《續約能不能批次處理》；`prospect/D/contract-esign-flow`《建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用）》 | |
| `tmp:kb:prospect/C/contract-templates` | 合約範本有哪些可以選 | `prospect/D/contract-templates`《合約範本有哪些可以選》；`prospect/D/sublease-vs-management-contract`《包租與代管在委託合約設定上的差別》 | |
| `tmp:kb:prospect/C/notification-channels` | 系統通知管道與時機 | `prospect/A/account-registration`《怎麼註冊帳號（含驗證碼通知）》；`prospect/D/contract-esign-flow`《建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用）》；`prospect/E/overdue-reminder-late-fee`《租客逾期未繳怎麼辦（含繳費提醒通知）》 | |
| `tmp:kb:prospect/C/payment-gateway-options` | 金流廠商差別與申請條件 | `prospect/E/payment-gateway-options`《金流廠商差別與申請條件》；`prospect/E/virtual-account-prepaid`《固定虛擬帳號與儲值金抵扣》 | |

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `prospect/A/account-registration`《怎麼註冊帳號（含驗證碼通知）》 | `tmp:kb:prospect/D/account-registration`＋`tmp:kb:prospect/C/notification-channels` | 三份一致歸帳號；註冊驗證碼走 Email 是通知投遞細節，兩份提議依「通知歸它所通知的領域」併入註冊。 | |
| `prospect/D/contract-esign-flow`《建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用）》 | `tmp:kb:prospect/C/contract-esign-flow`＋`tmp:kb:prospect/C/notification-channels` | 建約方式、流程、72 小時時效、身分、社宅公證與費用依附流程才完整（兩份併入），簽約邀請通知歸它所通知的租約領域；批次續約依多數拆出。 | |
| `prospect/E/overdue-reminder-late-fee`《租客逾期未繳怎麼辦（含繳費提醒通知）》 | `tmp:kb:prospect/C/overdue-reminder-late-fee`＋`tmp:kb:prospect/C/notification-channels` | 三份一致：繳費提醒的管道與時機是逾期處理的一部分，通知不自成細目，歸它所通知的帳務領域。 | |
| `prospect/I/data-migration`《舊系統資料能否匯入（可匯入範圍與不支援項目）》 | `tmp:kb:prospect/B/data-migration`＋`tmp:kb:prospect/G/migration-limits` | 三份一致：可匯入與不支援項目是同一導入問題的正反兩面且講法重複，合併為單一細目。 | |
| `prospect/I/product-overview`《系統總覽、能解決什麼問題與適不適合我》 | `tmp:kb:prospect/A/product-overview`＋`tmp:kb:prospect/A/pain-points` | 三份提議一致：總覽與痛點對應同為導入評估的開場問題，答案都是模組總覽加追問狀況，合併為一細目歸方案與導入。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| content_boundary 把首頁儀表板歸 H 幫助中心（prospect/H/dashboard-overview）。 | 另外兩份提議皆歸 I，且潛在客戶問的是導入前的產品畫面而非使用導覽，採多數歸方案與導入。 | |
| audience_level 把競品比較併入為什麼選金箍棒（prospect/I/why-choose-jgb 含 competitor-comparison）。 | 另外兩份皆保持分開；「為什麼選你們」與「跟某某比差在哪」是不同問法，比較內容含對手名稱與中立限制，講法並不重複。 | |
| user_question_path 把中立原則併入競品比較（prospect/I/competitor-comparison 含 competitor-neutrality）。 | 另外兩份皆獨立；「會不會評論對手」是立場說明，可獨立回答並被比較細目另見，合併會讓一句講法掛兩題。 | |
| audience_level 把團隊管理總覽與成員權限細分合併為 prospect/B/team-management-and-permissions。 | 另外兩份皆分開；總覽與「能不能只看不改」是不同問法，權限顆粒度自身完整。 | |
| audience_level 把大房東定義與大房東報表合併為 prospect/B/owner-landlord-and-report。 | 另外兩份皆分開；名詞定義與報表功能是不同層級的問題，以另見處理而非合併。 | |
| content_boundary 把代管月結差額發票從大房東報表拆為 prospect/E/owner-settlement-difference-invoice。 | 僅一份提議拆出；該段只有一句，是報表產出的一環，單獨不足以成為可獨立回答的主題。 | |
| user_question_path 再拆出 prospect/D/esign-invitation-validity（邀請 72 小時時效）與 prospect/D/social-housing-contract（社宅公證）。 | 另外兩份皆併入建約流程；時效與社宅例外依附流程才完整，拆出會產生與流程細目重複的講法。 | |
| audience_level 把批次續約留在建約流程細目內不拆。 | 另外兩份皆拆出；「續約可以一次多筆嗎」與建新約流程主題不同，可獨立回答。 | |
| audience_level 把包租／代管委託約差別留在合約範本細目內不拆。 | 另外兩份皆拆出；粗目 D 明列委託約子題，包租租金制度與代管服務費設定是獨立問法。 | |
| audience_level 把電子發票自動開立與載具留在帳務總覽內不拆。 | 另外兩份皆拆出；「發票可以自動開嗎」是獨立可答的問題，與模組總覽主題不同。 | |
| content_boundary 把水電分算併入帳單內容細目（prospect/E/bill-contents-extra-fees 含 utility-split-advice）。 | 另外兩份皆保持獨立；「水電怎麼分算」是獨立問法，併入會讓帳單內容細目承載不同主題。 | |
| audience_level 把信用卡繳租併入金流廠商細目（prospect/E/payment-gateway-options 含 credit-card-rent-payment）。 | 另外兩份皆分開；「能不能刷卡」是最常見的獨立問法，前提與設定自身完整，以另見處理。 | |
| audience_level 把固定虛擬帳號與儲值金留在金流廠商細目內不拆。 | 另外兩份皆拆出；儲值抵扣是另一收款機制，與廠商申請條件主題不同。 | |
| audience_level 不把註冊驗證碼通知併入帳號註冊細目。 | 另外兩份皆併入；依「通知歸它所通知的領域」判準，驗證碼通知歸註冊，否則該句講法無處可掛。 | |
| slug 分歧：individual-landlord-fit（user_question_path）、contract-creation-esign-flow（content_boundary）、contract-renewal-batch（user_question_path）、entrust-contract-sublease-vs-management（content_boundary）、einvoice-auto-issue-carrier（content_boundary）、virtual-account-prepaid-balance（content_boundary）、utility-split-advice（audience_level）。 | 主題歸屬一致僅命名不同，依多數或較短且對應主題內容（分算而非建議）者擇一，不影響細目互斥。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 1 | 4 | 4 | 6 | 9 | 1 | 1 | 0 | 12 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `prospect/A/account-registration` | merge+split-child |
| `prospect/D/contract-batch-renewal` | split-child |
| `prospect/D/contract-esign-flow` | merge+split-child |
| `prospect/D/contract-templates` | split-child |
| `prospect/D/sublease-vs-management-contract` | split-child |
| `prospect/E/billing-overview` | split-child |
| `prospect/E/einvoice-issuing` | split-child |
| `prospect/E/overdue-reminder-late-fee` | merge+split-child |
| `prospect/E/payment-gateway-options` | split-child |
| `prospect/E/virtual-account-prepaid` | split-child |
| `prospect/I/data-migration` | merge |
| `prospect/I/product-overview` | merge |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

| 舊細目 | 子細目數 |
|---|---|
| `tmp:kb:prospect/C/billing-overview` | 2 |
| `tmp:kb:prospect/C/contract-esign-flow` | 2 |
| `tmp:kb:prospect/C/contract-templates` | 2 |
| `tmp:kb:prospect/C/notification-channels` | 3 |
| `tmp:kb:prospect/C/payment-gateway-options` | 2 |
