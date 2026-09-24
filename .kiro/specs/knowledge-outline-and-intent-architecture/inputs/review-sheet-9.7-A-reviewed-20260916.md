# 9.7 A 架補審單 — 2026-09-16（等業主 ✅ 才可見）

A 架 16 條全部未審（`reviewed` 缺）⇒ 目前兩受眾視圖只出標題、不可引用。你逐條 ✅（或「全部 ✅」／指名 ✗ 要改的）後，我加 `reviewed: {by: owner, at: 2026-09-16}`、重導出、跑測試。內容全文見 `rag-orchestrator/canon/jgb/A.md`。

| # | id | 標題 | 受眾 | 講法 | 內容句 | 來源 | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `jgb/A/account-registration` | 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊） | pm, prospect | 10 | 13 | 7 | |
| 2 | `jgb/A/login-methods` | 怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口） | pm, prospect | 5 | 5 | 2 | |
| 3 | `jgb/A/line-login-redirects-to-register` | 用 LINE 快速登入卻被帶去註冊頁、登不進去（只認 LINE 註冊帳號、無事後綁定、改用帳密登入） | pm, prospect | 3 | 3 | 1 | |
| 4 | `jgb/A/account-profile-settings` | 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件） | pm, prospect | 5 | 7 | 3 | |
| 5 | `jgb/A/registered-vs-unregistered-tenant` | 租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業） | pm, prospect | 2 | 14 | 2 | |
| 6 | `jgb/A/email-case-sensitivity` | Email 大小寫算不同帳號嗎（Email 為帳號識別、大小寫視為不同帳號） | pm | 1 | 6 | 1 | |
| 7 | `jgb/A/verification-code-not-received` | 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊） | pm, prospect | 4 | 17 | 5 | |
| 8 | `jgb/A/verification-code-invalid` | 驗證碼一直輸入失敗（重發即換碼、三字母識別碼比對、5 分鐘效期、錯三次失效、120 秒冷卻） | pm, prospect | 2 | 4 | 1 | |
| 9 | `jgb/A/forgot-password` | 忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則） | pm, prospect | 3 | 7 | 2 | |
| 10 | `jgb/A/forgot-account-email` | 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服） | pm, prospect | 3 | 9 | 3 | |
| 11 | `jgb/A/change-email-or-phone` | 要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書） | pm | 2 | 3 | 2 | |
| 12 | `jgb/A/change-account-name` | 註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步） | pm | 3 | 2 | 2 | |
| 13 | `jgb/A/data-change-request-form` | 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱） | pm | 2 | 8 | 3 | |
| 14 | `jgb/A/duplicate-accounts-merge` | 不小心註冊了兩個帳號能不能合併（無自助合併、走客服後台，載明保留與處理的帳號） | pm | 3 | 3 | 1 | |
| 15 | `jgb/A/already-registered-error` | 註冊時顯示此帳號／手機已註冊怎麼辦（本人改登入或重設密碼、被他人占用走解綁申請） | pm, prospect | 1 | 2 | 1 | |
| 16 | `jgb/A/tenant-login-cannot-see-data` | 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態） | pm | 5 | 3 | 3 | |

補審後：兩受眾視圖細目可引用；`test_canon_assembler_req._UNREVIEWED_IDS` 同步刪 16 條。
