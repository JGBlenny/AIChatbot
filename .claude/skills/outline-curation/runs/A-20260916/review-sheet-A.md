# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/A/account-registration` | 怎麼註冊帳號（含驗證碼通知） | `jgb/A/account-registration` | 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） | keep | A/A/A | |
| 2 | `tmp:draft:1` | 房東教學01：註冊篇(一) 個人房東 | `jgb/A/account-profile-settings` | 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件） | split | A/A/A | |
| 3 | `tmp:draft:1` | 房東教學01：註冊篇(一) 個人房東 | `jgb/A/account-registration` | 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） | split | A/A/A | |
| 4 | `tmp:draft:1` | 房東教學01：註冊篇(一) 個人房東 | `jgb/A/login-methods` | 怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口） | split | A/A/A | |
| 5 | `tmp:draft:10` | 租客系統操作教學—註冊篇 | `jgb/A/account-registration` | 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） | merge | A/A/A | |
| 6 | `tmp:draft:3` | 註冊一套專屬你的租房管理 | `jgb/A/account-registration` | 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） | split | A/A/A | |
| 7 | `tmp:draft:3` | 註冊一套專屬你的租房管理 | `jgb/A/login-methods` | 怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口） | split | A/A/A | |
| 8 | `tmp:draft:3` | 註冊一套專屬你的租房管理 | `jgb/A/registered-vs-unregistered-tenant` | 租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業） | split | A/A/A | |
| 9 | `tmp:draft:4` | 帳號資訊設定 完成您的個人資料吧！ | `jgb/A/account-profile-settings` | 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件） | new | A/A/A | |
| 10 | `tmp:draft:6` | 註冊時收不到驗證信 | `jgb/A/verification-code-not-received` | 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） | new | A/A/A | |
| 11 | `tmp:draft:7` | 我忘記帳號怎麼辦？ | `jgb/A/forgot-account-email` | 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服） | new | A/A/A | |
| 12 | `tmp:draft:8` | 我忘記密碼怎麼辦？ | `jgb/A/forgot-password` | 忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則） | new | A/A/A | |
| 13 | `tmp:draft:9` | 如何更改帳號資訊？ | `jgb/A/account-profile-settings` | 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件） | new | A/A/A | |
| 14 | `tmp:kb:3348` | 免註冊 註冊 租客 差異 | `jgb/A/registered-vs-unregistered-tenant` | 租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業） | new | A/A/A | |
| 15 | `tmp:kb:3349` | email 大小寫 帳號 不同 | `jgb/A/email-case-sensitivity` | Email 大小寫算不同帳號嗎（Email 為帳號識別、大小寫視為不同帳號） | new | A/A/A | |
| 16 | `tmp:kb:3350` | 簡訊 驗證碼 收不到 | `jgb/A/verification-code-not-received` | 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） | new | A/A/A | |
| 17 | `tmp:kb:3435` | 註冊帳號 建立流程 | `jgb/A/account-registration` | 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） | merge | A/A/A | |
| 18 | `tmp:kb:3436` | 忘記密碼 無法登入 | `jgb/A/forgot-account-email` | 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服） | split | A/A/A | |
| 19 | `tmp:kb:3436` | 忘記密碼 無法登入 | `jgb/A/forgot-password` | 忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則） | split | A/A/A | |
| 20 | `tmp:kb:3437` | Email 變更 手機驗證 | `jgb/A/change-email-or-phone` | 要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書） | split | A/A/A | |
| 21 | `tmp:kb:3437` | Email 變更 手機驗證 | `jgb/A/data-change-request-form` | 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱） | split | A/A/A | |
| 22 | `tmp:kb:3869` | 租客看不到合約 登入信箱不符 | `jgb/A/tenant-login-cannot-see-data` | 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態） | new | A/A/A | |
| 23 | `tmp:kb:3871` | 驗證信 驗證碼收不到 排查 | `jgb/A/verification-code-not-received` | 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） | new | A/A/A | |
| 24 | `tmp:kb:3964` | 驗證碼一直失敗 重發 新舊碼 | `jgb/A/verification-code-invalid` | 驗證碼一直輸入失敗（重發即換碼、三字母識別碼比對、5 分鐘效期、錯三次失效、120 秒冷卻） | new | A/A/A | |
| 25 | `tmp:kb:3965` | 收不到驗證簡訊 改用信箱註冊 | `jgb/A/verification-code-not-received` | 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） | new | A/A/A | |
| 26 | `tmp:kb:3966` | 註冊顯示已註冊 該怎麼辦 | `jgb/A/already-registered-error` | 註冊時顯示此帳號／手機已註冊怎麼辦（本人改登入或重設密碼、被他人占用走解綁申請） | new | A/A/A | |
| 27 | `tmp:kb:3967` | LINE 快速登入 跳到註冊 登不進去 | `jgb/A/line-login-redirects-to-register` | 用 LINE 快速登入卻被帶去註冊頁、登不進去（只認 LINE 註冊帳號、無事後綁定、改用帳密登入） | new | A/A/A | |
| 28 | `tmp:kb:3968` | 登入成功 看不到合約帳單電表 | `jgb/A/tenant-login-cannot-see-data` | 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態） | new | A/A/A | |
| 29 | `tmp:kb:3969` | 忘記當初註冊的信箱 查詢帳號 | `jgb/A/forgot-account-email` | 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服） | new | A/A/A | |
| 30 | `tmp:kb:3971` | 註冊名字與證件不同 改名 藍字 | `jgb/A/change-account-name` | 註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步） | split | A/A/A | |
| 31 | `tmp:kb:3971` | 註冊名字與證件不同 改名 藍字 | `jgb/A/data-change-request-form` | 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱） | split | A/A/A | |
| 32 | `tmp:kb:3972` | 兩個帳號 合併 重複帳號 | `jgb/A/data-change-request-form` | 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱） | split | A/A/A | |
| 33 | `tmp:kb:3972` | 兩個帳號 合併 重複帳號 | `jgb/A/duplicate-accounts-merge` | 不小心註冊了兩個帳號能不能合併（無自助合併、走客服後台，載明保留與處理的帳號） | split | A/A/A | |
| 34 | `tmp:kb:3975` | 租客一直沒辦法註冊 卡住了 | `jgb/A/verification-code-not-received` | 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） | new | A/A/A | |
| 35 | `tmp:kb:3978` | 租客登入後什麼都看不到 畫面空空的 | `jgb/A/tenant-login-cannot-see-data` | 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態） | new | A/A/A | |
| 36 | `tmp:kb:3980` | 會員帳號資料要修改 信箱手機要換 | `jgb/A/change-email-or-phone` | 要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書） | new | A/A/A | |
| 37 | `tmp:kb:4561` | 註冊名字跟證件不符 要怎麼改資料 | `jgb/A/change-account-name` | 註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步） | new | A/A/A | |

## B. 拆分（split）——一個舊細目拆成多個新細目

| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |
|---|---|---|---|
| `tmp:kb:3436` | 忘記密碼 無法登入 | `jgb/A/forgot-account-email`《忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服）》；`jgb/A/forgot-password`《忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則）》 | |
| `tmp:kb:3437` | Email 變更 手機驗證 | `jgb/A/change-email-or-phone`《要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書）》；`jgb/A/data-change-request-form`《資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱）》 | |
| `tmp:kb:3971` | 註冊名字與證件不同 改名 藍字 | `jgb/A/change-account-name`《註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步）》；`jgb/A/data-change-request-form`《資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱）》 | |
| `tmp:kb:3972` | 兩個帳號 合併 重複帳號 | `jgb/A/data-change-request-form`《資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱）》；`jgb/A/duplicate-accounts-merge`《不小心註冊了兩個帳號能不能合併（無自助合併、走客服後台，載明保留與處理的帳號）》 | |
| `tmp:kb:tmp:draft:1` |  | `jgb/A/account-profile-settings`《帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件）》；`jgb/A/account-registration`《怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊）》；`jgb/A/login-methods`《怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口）》 | |
| `tmp:kb:tmp:draft:3` |  | `jgb/A/account-registration`《怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊）》；`jgb/A/login-methods`《怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口）》；`jgb/A/registered-vs-unregistered-tenant`《租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業）》 | |

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/A/account-profile-settings`《帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件）》 | `tmp:kb:tmp:draft:4`＋`tmp:kb:tmp:draft:9`＋`tmp:kb:tmp:draft:1` | 三角度一致：登入後到頭像「帳號資訊」可自助編輯的欄位與位置是獨立於註冊與登入的主題；draft:1 只取帳號設置段；draft:4 的團隊帳號篇屬 B 架團隊資訊，本細目只取房東／租客帳號篇，團隊段由 B 以另見處理。不能自改的識別欄位另見 change-email-or-phone／change-account-name。 | |
| `jgb/A/account-registration`《怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊）》 | `tmp:kb:tmp:canon:jgb/A/account-registration`＋`tmp:kb:3435`＋`tmp:kb:tmp:draft:1`＋`tmp:kb:tmp:draft:3`＋`tmp:kb:tmp:draft:10` | 三角度一致：註冊步驟（Email→驗證碼→密碼→選身分→綁手機可跳過）、SSO 註冊與租客由電子合約邀請進入註冊是同一份「怎麼註冊」，與既有細目同主題故吸收而非另立；draft:1／draft:3 只取註冊段，登入段、帳號設置段與「租客可自選是否註冊」段各拆去對應細目。 | |
| `jgb/A/change-account-name`《註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步）》 | `tmp:kb:3971`＋`tmp:kb:4561` | 姓名可否自改取決於合約是否已完成簽署，這組條件與信箱／手機變更的規則不同，故獨立成細目；申請書流程拆出至 data-change-request-form 另見；kb:4561 無內文，只當入口併入。 | |
| `jgb/A/change-email-or-phone`《要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書）》 | `tmp:kb:3437`＋`tmp:kb:3980` | 信箱／手機這兩個登入識別的變更規則（Email 不可自改、手機未綁可自助、已綁改號走後台）是一份完整內容，與一般帳號資訊編輯及改姓名的判斷條件不同；kb:3437 內的申請書填寫細節屬共用流程，拆出至 data-change-request-form 另見；kb:3980 無內文，只當入口併入。 | |
| `jgb/A/data-change-request-form`《資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱）》 | `tmp:kb:3437`＋`tmp:kb:3971`＋`tmp:kb:3972` | 換信箱、換已綁手機、簽署後改名、合併重複帳號四個主題引用同一套申請書流程；依「不同層級以另見處理而非重複」與講法唯一原則抽成一細目供各主題引用，避免四處重複同一段流程。 | |
| `jgb/A/forgot-account-email`《忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服）》 | `tmp:kb:3436`＋`tmp:kb:3969`＋`tmp:kb:tmp:draft:7` | 「不知道帳號是哪個信箱」與「知道帳號但忘密碼」是兩個各自完整的問題，答案路徑不同（手機簡訊驗證取得提示 vs 重設密碼）；kb:3436 的忘記帳號段與 kb:3969、draft:7 合併。 | |
| `jgb/A/forgot-password`《忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則）》 | `tmp:kb:3436`＋`tmp:kb:tmp:draft:8` | 重設密碼是獨立完整的自助流程；kb:3436 同時含「忘記帳號」段，拆出至 forgot-account-email，避免兩主題混在一筆；兩角度分開、一角度合併，採分開。 | |
| `jgb/A/login-methods`《怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口）》 | `tmp:kb:tmp:draft:1`＋`tmp:kb:tmp:draft:3` | 「怎麼登入」與「怎麼註冊」是不同問題且註冊後獨立成立，三角度皆獨立成細目；來源為 draft:3 的房東／租客登入篇與 draft:1 的登入段。LINE 快速登入異常屬排障題，另見 line-login-redirects-to-register。 | |
| `jgb/A/registered-vs-unregistered-tenant`《租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業）》 | `tmp:kb:3348`＋`tmp:kb:tmp:draft:3` | 三角度皆獨立成細目：租客可自選是否註冊、註冊後能做什麼、免註冊會少什麼，是帳號存在與否的後果而非帳務規則，歸 A；draft:3 的「租客可自行選擇是否註冊」改版說明是此命題的來源故拆入，註冊步驟另見 account-registration。 | |
| `jgb/A/tenant-login-cannot-see-data`《租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態）》 | `tmp:kb:3968`＋`tmp:kb:3869`＋`tmp:kb:3978` | 三角度一致為一細目：同一條問法「登入了卻什麼都看不到」，排查順序＝身分選單、登入信箱與邀請信箱是否一致、以合約查租客帳號狀態並退回改信箱重寄；根因在帳號對不上而非合約本身，歸 A；kb:3978 無內文，只當入口併入；Email 大小寫規則以另見引用不重複。 | |
| `jgb/A/verification-code-not-received`《收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊）》 | `tmp:kb:3350`＋`tmp:kb:3871`＋`tmp:kb:3965`＋`tmp:kb:3975`＋`tmp:kb:tmp:draft:6` | 三角度一致：「收不到驗證碼」的排查步驟（垃圾信匣、號碼／信箱正確、攔截 APP、訊號、120 秒冷卻與每日上限、改走 Email／SSO、聯繫客服要帶的資訊）散在多筆來源但缺一不全，屬同一主題；kb:3975「租客一直沒辦法註冊卡住了」無內文，依契約只當入口併入最常見的卡點細目，不獨立成空細目。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| audience_level：把 kb:3964「驗證碼一直失敗」併入 verification-code-issues，與「收不到驗證碼」同一細目。 | 「收到了但驗不過」與「收不到」是不同命題（識別碼／新舊碼 vs 投遞管道），排障題可分開；user_question_path 與 content_boundary 皆分開，採分開並以另見互指。 | |
| user_question_path：kb:3975「租客一直沒辦法註冊卡住了」獨立成 tenant-registration-stuck 分流入口細目。 | 來源無內文，契約明定空內文 kb 列只當入口併入最近細目、不獨立成空細目；最常見的卡點是驗證碼，故併入 verification-code-not-received（content_boundary 與 audience_level 亦如此）。 | |
| audience_level：忘記密碼與忘記帳號合為一個 account-recovery 細目。 | 兩者答案路徑不同（重設密碼 vs 手機驗證取得打星號信箱提示），是兩個可獨立回答的問題；另兩角度皆分開，採分開。 | |
| content_boundary：kb:3349 Email 大小寫規則併入 login-email-mismatch；audience_level：併入 account-identity-uniqueness。 | 該規則被邀請大房東失敗（B 架）、租客看不到合約、誤建第二帳號多條症狀共同引用，併入任一症狀細目會讓其他症狀無處引用；獨立成 email-case-sensitivity 供各處另見（user_question_path）。 | |
| audience_level：kb:3967 LINE 快速登入異常併入 login-methods-and-identity。 | 排障題與操作題分開；LINE 登入被導去註冊的原因與處置可獨立回答，另兩角度皆獨立成細目。 | |
| audience_level：account-data-change 把換信箱／換手機與改姓名合為一細目。 | 改姓名的可否取決於合約是否已簽署，換信箱／手機的規則取決於是否已綁定，判斷條件不同，是兩個命題；另兩角度皆分開。 | |
| audience_level：account-identity-uniqueness 把 kb:3349／3966／3972 三者合為「帳號唯一性規則」一細目。 | 三者是不同問法（大小寫有沒有差、顯示已註冊怎麼辦、兩個帳號能不能合併），答案各自完整；另兩角度皆分開，採分開。 | |
| user_question_path 與 audience_level：資料異動申請書流程留在換信箱、改姓名、合併帳號各細目內文，不另立 data-change-request-form。 | 同一段申請書流程會在四個細目重複，違反講法唯一與「不同層級以另見處理而非重複」；採 content_boundary 抽成共用細目，各主題以另見引用。 | |
| content_boundary：draft:1 的常見問題段（收不到驗證信）額外拆入 verification-code-not-received，使 draft:1 拆成四處。 | 該段內容已被 draft:6 完整涵蓋且文字幾乎相同，拆入不增加命題；draft:1 維持註冊、登入、帳號設置三處拆分。 | |
| user_question_path 與 content_boundary：draft:3 只拆入 account-registration 與 login-methods，「租客可自行選擇是否註冊」段留在註冊細目。 | 該段正是 registered-vs-unregistered-tenant 的命題來源，依 audience_level 拆入該細目，避免同一命題同時落在兩個細目。 | |
| audience_level：既有細目 account-registration 列 op=keep。 | 擴充契約明定既有細目吸收新來源時 fine 層 op=merge（既有來源自身在 id_map 列 keep）。 | |
| audience_level：forgot／profile-settings／change-email-or-phone 等細目 target_user 只列 property_manager；content_boundary：change-email-phone 列兩者。 | 註冊、登入、忘記密碼／帳號、帳號資訊設定是售前試用者也會問的操作題，依多數角度列兩者；換信箱／手機、改姓名、合併帳號、申請書、大小寫規則、租客登入看不到資料是業者管理情境，依多數角度只列 property_manager。 | |
| 同主題不同 id 命名：verification-code-rejected、forgot-account、change-email-phone、change-name-vs-contract、profile-settings、line-login-redirects-to-signup（content_boundary）；login-but-nothing-visible（user_question_path）；login-email-mismatch（content_boundary）；login-methods-and-identity、verification-code-issues、tenant-registration-choice（audience_level）。 | 同一主題只保留一個 id，優先採兩角度以上相同或最能描述命題的既有提議 id（verification-code-invalid、forgot-account-email、change-email-or-phone、change-account-name、account-profile-settings、line-login-redirects-to-register、tenant-login-cannot-see-data、login-methods、registered-vs-unregistered-tenant），未引入三份提議都沒有的 id。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/A/account-profile-settings` | merge+split-child |
| `jgb/A/account-registration` | merge+split-child |
| `jgb/A/change-account-name` | merge+split-child |
| `jgb/A/change-email-or-phone` | merge+split-child |
| `jgb/A/data-change-request-form` | merge+split-child |
| `jgb/A/duplicate-accounts-merge` | split-child |
| `jgb/A/forgot-account-email` | merge+split-child |
| `jgb/A/forgot-password` | merge+split-child |
| `jgb/A/login-methods` | merge+split-child |
| `jgb/A/registered-vs-unregistered-tenant` | merge+split-child |
| `jgb/A/tenant-login-cannot-see-data` | merge |
| `jgb/A/verification-code-not-received` | merge |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

| 舊細目 | 子細目數 |
|---|---|
| `tmp:kb:3436` | 2 |
| `tmp:kb:3437` | 2 |
| `tmp:kb:3971` | 2 |
| `tmp:kb:3972` | 2 |
| `tmp:kb:tmp:draft:1` | 3 |
| `tmp:kb:tmp:draft:3` | 3 |
