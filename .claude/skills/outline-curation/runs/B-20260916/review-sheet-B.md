# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/B/owner-report-collection-remit` | 大房東報表與代收代付怎麼交代 | `jgb/B/owner-report-collection-remit` | 大房東報表與代收代付怎麼交代（月報內容、提供方式、排程寄送） | keep | B/B/B | |
| 2 | `tmp:canon:jgb/B/role-permission-granularity` | 成員權限能不能細分（只看不改、看不到財務） | `jgb/B/role-permission-granularity` | 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權） | keep | B/B/B | |
| 3 | `tmp:canon:jgb/B/team-management-overview` | 團隊管理模組做什麼 | `jgb/B/team-management-overview` | 團隊管理模組做什麼 | keep | B/B/B | |
| 4 | `tmp:canon:jgb/B/what-is-owner-landlord` | 大房東是什麼 | `jgb/B/what-is-owner-landlord` | 大房東是什麼 | keep | B/B/B | |
| 5 | `tmp:draft:1` | 租賃專法下的包租代管業 | `jgb/B/business-type-fee-model` | 包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼） | split | B/B/B | |
| 6 | `tmp:draft:1` | 租賃專法下的包租代管業 | `jgb/B/leasing-management-license-and-staff-qualification` | 如何成為政府許可的包租代管業者與合格包管人員 | split | B/B/B | |
| 7 | `tmp:draft:1` | 租賃專法下的包租代管業 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | split | B/B/B | |
| 8 | `tmp:kb:3084` | 包租業定義 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 9 | `tmp:kb:3085` | 代管業介紹 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 10 | `tmp:kb:3086` | 包租代管差異 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 11 | `tmp:kb:3087` | 包租與代管差異 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 12 | `tmp:kb:3088` | 收費結構差異 | `jgb/B/business-type-fee-model` | 包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼） | new | B/B/B | |
| 13 | `tmp:kb:3091` | 包租業與代管業差異 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 14 | `tmp:kb:3092` | 管理費用差異 | `jgb/B/business-type-fee-model` | 包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼） | new | B/B/B | |
| 15 | `tmp:kb:3095` | 包租業與代管業 | `jgb/B/leasing-vs-management-liability-and-risk` | 包租與代管的法律責任與風險由誰承擔 | new | B/B/B | |
| 16 | `tmp:kb:3096` | 風險管理策略 | `jgb/B/leasing-vs-management-liability-and-risk` | 包租與代管的法律責任與風險由誰承擔 | new | B/B/B | |
| 17 | `tmp:kb:3254` | 法律責任差異 | `jgb/B/leasing-vs-management-liability-and-risk` | 包租與代管的法律責任與風險由誰承擔 | new | B/B/B | |
| 18 | `tmp:kb:3255` | 風險管理差異 | `jgb/B/leasing-vs-management-liability-and-risk` | 包租與代管的法律責任與風險由誰承擔 | new | B/B/B | |
| 19 | `tmp:kb:3303` | 包租業介紹 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 20 | `tmp:kb:3304` | 代管業定義 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 21 | `tmp:kb:3305` | 包租代管服務差異 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 22 | `tmp:kb:3306` | 包租業與代管業比較 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 23 | `tmp:kb:3307` | 包租代管法律責任 | `jgb/B/leasing-vs-management-liability-and-risk` | 包租與代管的法律責任與風險由誰承擔 | new | B/B/B | |
| 24 | `tmp:kb:3308` | 包租代管業務差異 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 25 | `tmp:kb:3309` | 包租代管關係 | `jgb/B/leasing-vs-management-business-model` | 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個） | new | B/B/B | |
| 26 | `tmp:kb:3310` | 包租與代管風險管理 | `jgb/B/leasing-vs-management-liability-and-risk` | 包租與代管的法律責任與風險由誰承擔 | new | B/B/B | |
| 27 | `tmp:kb:3312` | 代管服務費 | `jgb/B/business-type-fee-model` | 包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼） | new | B/B/B | |
| 28 | `tmp:kb:3359` | 團隊 權限 成員 管理 | `jgb/B/change-team-principal-or-phone` | 怎麼變更團隊主要負責人或綁定手機（異動單） | split | B/B/B | |
| 29 | `tmp:kb:3359` | 團隊 權限 成員 管理 | `jgb/B/role-permission-granularity` | 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權） | split | B/B/B | |
| 30 | `tmp:kb:3439` | 團隊成員 新增管理 | `jgb/B/add-team-member` | 怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦） | new | B/B/B | |
| 31 | `tmp:kb:3463` | 大房東 概念說明 | `jgb/B/what-is-owner-landlord` | 大房東是什麼 | merge | B/B/B | |
| 32 | `tmp:kb:3464` | 大房東新增 權限設定 | `jgb/B/add-owner-landlord-and-access` | 怎麼新增大房東並設定他能看的物件範圍 | new | B/B/B | |
| 33 | `tmp:kb:3465` | 大房東月報表 報表功能 | `jgb/B/owner-report-collection-remit` | 大房東報表與代收代付怎麼交代（月報內容、提供方式、排程寄送） | merge | B/B/B | |
| 34 | `tmp:kb:3467` | 大房東聯絡簿 批次匯入匯出 | `jgb/B/owner-landlord-contact-book-import-export` | 大房東聯絡簿怎麼批次匯入匯出 | new | B/B/B | |
| 35 | `tmp:kb:3482` | 看不到功能 權限不足 | `jgb/B/feature-not-visible-troubleshooting` | 找不到某功能或無法操作的可能原因 | new | ⚠️ B/?/B | |
| 36 | `tmp:kb:3543` | 大房東報表排程 自動寄送設定 | `jgb/B/owner-report-collection-remit` | 大房東報表與代收代付怎麼交代（月報內容、提供方式、排程寄送） | merge | B/B/B | |
| 37 | `tmp:kb:3544` | 新增團隊成員 需先註冊帳號 | `jgb/B/add-team-member` | 怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦） | new | B/B/B | |
| 38 | `tmp:kb:3545` | 團隊成員權限 只能查看不能編輯 | `jgb/B/role-permission-granularity` | 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權） | merge | B/B/B | |
| 39 | `tmp:kb:3546` | 移除團隊成員 資料保留處理 | `jgb/B/remove-team-member-data-retention` | 移除團隊成員後他建的資料會怎樣 | new | B/B/B | |
| 40 | `tmp:kb:3547` | 一個帳號加入多個團隊 身分切換 | `jgb/B/account-in-multiple-teams` | 一個帳號可以加入多個團隊嗎、權限怎麼算 | new | B/B/B | |
| 41 | `tmp:kb:3974` | 誰有權限 操作權限 盤查 | `jgb/B/who-has-permission-lookup` | 怎麼查團隊裡誰有某個操作權限 | new | B/B/B | |
| 42 | `tmp:kb:3981` | 加了團隊成員 他什麼都看不到 | `jgb/B/add-team-member` | 怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦） | new | B/B/B | |
| 43 | `tmp:kb:3982` | 成員權限怎麼開 只能看不能改 | `jgb/B/role-permission-granularity` | 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權） | merge | B/B/B | |
| 44 | `tmp:kb:4224` | 包租 代管 差別 系統功能 | `jgb/B/business-type-setting-and-system-differences` | 團隊業態（包租／代管）在系統裡怎麼設、差在哪（合約模板、發票主體、差額發票） | new | B/B/B | |
| 45 | `tmp:kb:4250` | 團隊成員 角色權限 有哪些選擇 | `jgb/B/role-permission-granularity` | 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權） | merge | B/B/B | |
| 46 | `tmp:kb:4251` | 新增團隊成員 邀請流程 | `jgb/B/add-team-member` | 怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦） | new | B/B/B | |

## B. 拆分（split）——一個舊細目拆成多個新細目

| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |
|---|---|---|---|
| `tmp:kb:3359` | 團隊 權限 成員 管理 | `jgb/B/change-team-principal-or-phone`《怎麼變更團隊主要負責人或綁定手機（異動單）》；`jgb/B/role-permission-granularity`《成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權）》 | |
| `tmp:kb:tmp:draft:1` |  | `jgb/B/business-type-fee-model`《包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼）》；`jgb/B/leasing-management-license-and-staff-qualification`《如何成為政府許可的包租代管業者與合格包管人員》；`jgb/B/leasing-vs-management-business-model`《包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個）》 | |

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/B/add-team-member`《怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦）》 | `tmp:kb:3439`＋`tmp:kb:3544`＋`tmp:kb:4251`＋`tmp:kb:3981` | 「怎麼加成員／為什麼加不進去／加了他什麼都看不到」是同一條操作路徑，答案都是先註冊、加入後指派角色；三筆同流程各補一段，3981 空內文只當入口掛此（兩角度如此）。 | |
| `jgb/B/business-type-fee-model`《包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼）》 | `tmp:kb:3088`＋`tmp:kb:3092`＋`tmp:kb:3312`＋`tmp:kb:tmp:draft:1` | 業者向房東怎麼收費與收入來源是業態商業模式而非系統帳單計算，三角度皆留 B；draft 第三節（含補貼）拆入；租金代收 vs 直收屬「錢怎麼進來」歸 E，只列 out_of_shelf 另見。 | |
| `jgb/B/leasing-vs-management-business-model`《包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個）》 | `tmp:kb:3084`＋`tmp:kb:3085`＋`tmp:kb:3086`＋`tmp:kb:3087`＋`tmp:kb:3091`＋`tmp:kb:3303`＋`tmp:kb:3304`＋`tmp:kb:3305`＋`tmp:kb:3306`＋`tmp:kb:3308`＋`tmp:kb:3309`＋`tmp:kb:tmp:draft:1` | 11 筆重複改寫的定義與差異文與 draft 第一、二節皆在回答「包租／代管各是什麼、跟誰簽約、誰管理、適合誰」，同受眾同層級收成一題；業態定義群三角度皆留 B。 | |
| `jgb/B/leasing-vs-management-liability-and-risk`《包租與代管的法律責任與風險由誰承擔》 | `tmp:kb:3095`＋`tmp:kb:3096`＋`tmp:kb:3254`＋`tmp:kb:3255`＋`tmp:kb:3307`＋`tmp:kb:3310` | 「出問題誰負責／空置與損壞風險誰扛」是與定義題不同的可獨立回答主題，六筆互為改寫合為一題（3095 內文講法律責任歸此而非定義）；兩角度主張獨立、一角度併入定義，採獨立。 | |
| `jgb/B/owner-report-collection-remit`《大房東報表與代收代付怎麼交代（月報內容、提供方式、排程寄送）》 | `tmp:kb:tmp:canon:jgb/B/owner-report-collection-remit`＋`tmp:kb:3465`＋`tmp:kb:3543` | 「大房東報表能做什麼／怎麼產／怎麼自動寄」是同一主題，3465 月報表內容與三種提供方式、3543 排程週期與預告通知是同題的操作答案，併入既有細目、id 不變；三角度中兩份主張合併。 | |
| `jgb/B/role-permission-granularity`《成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權）》 | `tmp:kb:tmp:canon:jgb/B/role-permission-granularity`＋`tmp:kb:3359`＋`tmp:kb:3545`＋`tmp:kb:3982`＋`tmp:kb:4250` | 「能不能只給看不給改／有哪些角色／怎麼開權限」是同一主題的能力面與操作面，3545 層級相依、4250 自訂角色與設定入口、3359 權限與物件授權段併入，3982 空內文只當入口；既有 id 不變，3359 的異動單段另拆出。 | |
| `jgb/B/what-is-owner-landlord`《大房東是什麼》 | `tmp:kb:tmp:canon:jgb/B/what-is-owner-landlord`＋`tmp:kb:3463` | 3463 與既有細目同為大房東的概念定義（委託代管的業主、可看授權物件的合約帳單報表、方案數量上限），三角度一致吸收、id 不變；新增與授權操作另見 add-owner-landlord-and-access。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| audience_level：既有 owner-report-collection-remit 只保留售前能力層（keep），另立 owner-landlord-report-schedule 收 3465／3543 的操作層。 | 「大房東報表怎麼產／怎麼寄」是同一主題，拆成能力層與操作層會讓同一問題有兩個細目；兩角度主張吸收，採 merge、id 不變、target_user 列兩者。 | |
| audience_level：既有 role-permission-granularity 只留 prospect 的能力層（keep），另立 member-role-permission-setup 收 3545／4250／3982／3359。 | 同一主題不得同時存在能力版與操作版兩細目；兩角度主張吸收進既有細目，採 merge 並把 target_user 擴為兩者。 | |
| audience_level：3974（誰有某操作權限）併入權限設定細目。 | 盤查型提問與設定型提問路徑不同；兩角度主張獨立 who-has-permission-lookup，採獨立。 | |
| content_boundary：法律責任與風險（3096／3254／3255／3307／3310）併入業態定義細目成一大題。 | 「誰負責／風險誰扛」是可獨立回答的主題，18 筆合一會讓細目過寬；兩角度主張獨立，採獨立。 | |
| user_question_path：3095 歸入定義細目。 | 3095 標題泛稱但內文講的是法律責任由誰承擔，依內文歸 liability-and-risk。 | |
| audience_level：3326（租金代收 vs 房東直收）併入收費細目。 | 歸位判準「錢怎麼進來歸帳務底下的收款金流」，兩角度與合成契約皆判 E；只列 out_of_shelf 另見，不進 B。 | |
| user_question_path：draft 第四、五節拆成兩題（業者許可申請／包管人員證照）。 | 兩節皆為「如何合法從業」的人員資格題且各自篇幅短；兩角度主張合一，採單一細目。 | |
| content_boundary：draft 第三（二）節政府補貼歸入許可／法規細目。 | 補貼在原文屬「業者怎麼賺錢」的收入來源，兩角度歸收費細目，採收費。 | |
| user_question_path：3480 在 B 架另立 role-function-scope（各角色功能範圍）。 | 該列主體是四種身分的功能總表而非團隊；兩角度判 A 架，跨架命題只能歸一處，採 out_of_shelf A。 | |
| content_boundary：3482（看不到功能）歸 H 幫助中心。 | 四個原因中角色限制與團隊權限是主因、且與 3981 症狀相鄰；兩角度留 B，採留 B。 | |
| audience_level：3981（加了成員他什麼都看不到）掛在 3482 的排查細目。 | 該症狀的答案（加入後須指派角色）就在 add-team-member；兩角度掛 add-team-member，採之。 | |
| content_boundary：team-management-overview 的 target_user 列 prospect＋property_manager。 | 既有內文是模組總覽與 demo 導引，屬售前層級；兩角度判 prospect，採 prospect。 | |
| audience_level：what-is-owner-landlord 只列 prospect。 | 吸收 3463 後含物管設定大房東帳號與方案上限，物管也會問；兩角度列兩者，採兩者。 | |
| audience_level：business-type-setting-and-system-differences 只列 property_manager。 | 售前會問「系統支援包租嗎／差在哪」；兩角度列兩者，採兩者。 | |
| content_boundary：收費細目與許可細目 target_user 列兩者。 | 三筆 kb 與 draft 皆為產業說明而非系統操作，物管不需靠系統答；兩角度判 prospect，採 prospect。 | |
| slug 取捨：rent-vs-manage-*（user_question_path）、business-type-lease-vs-manage／business-type-system-differences／rental-service-act-licensing／one-account-multiple-teams／add-owner-landlord-and-scope／change-team-owner（content_boundary）、leasing-vs-management-fee-and-rent-collection／member-cannot-see-function-troubleshooting（audience_level）。 | 同一主題只能一個 id，取多數或語意最準者：業態群採 leasing-vs-management-* 與 business-type-*，收費題不採含 rent-collection 的 slug（該子題已歸 E），排查題採不限成員的 feature-not-visible-troubleshooting。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/B/add-team-member` | merge |
| `jgb/B/business-type-fee-model` | merge+split-child |
| `jgb/B/change-team-principal-or-phone` | split-child |
| `jgb/B/leasing-management-license-and-staff-qualification` | split-child |
| `jgb/B/leasing-vs-management-business-model` | merge+split-child |
| `jgb/B/leasing-vs-management-liability-and-risk` | merge |
| `jgb/B/owner-report-collection-remit` | merge |
| `jgb/B/role-permission-granularity` | merge+split-child |
| `jgb/B/what-is-owner-landlord` | merge |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

| 舊細目 | 子細目數 |
|---|---|
| `tmp:kb:3359` | 2 |
| `tmp:kb:tmp:draft:1` | 3 |
