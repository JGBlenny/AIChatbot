# JGB 產品功能全表（步 0a 分母）— master @ b2ee2ac382ce

來源：jgb2 `master`（`config/character.php`、`routes/web.php`、`routes/api.php`）、幫助中心 `JGB幫助中心_HTML_交付_20260818`、正本 `rag-orchestrator/canon/jgb`。
路由覆蓋：Route:: 出現 908／解析 891／未解析 17。已知不涵蓋面見腳本檔頭。

## 0. 計數

| 單位 | 權限 action | 路由 | controller | 幫助中心頁 | 正本細目 |
|---|---|---|---|---|---|
| 1175 | 45 | 891 | 115 | 92 | 210 |

## 1. 功能單位（0b 只填判定，⛔ 不得增刪合併）

| unit_id | 種類 | 側 | 內部 | 證據 |
|---|---|---|---|---|
| `action:add_bill` | action | 房東側 |  | config/character.php:'add_bill' |
| `action:add_contract` | action | 房東側 |  | config/character.php:'add_contract' |
| `action:add_estate` | action | 房東側 |  | config/character.php:'add_estate' |
| `action:assign_contract` | action | 房東側 |  | config/character.php:'assign_contract' |
| `action:assign_estate` | action | 房東側 |  | config/character.php:'assign_estate' |
| `action:chart_bill` | action | 房東側 |  | config/character.php:'chart_bill' |
| `action:chart_owner_bill` | action | 房東側 |  | config/character.php:'chart_owner_bill' |
| `action:edit_biglandlord` | action | 房東側 |  | config/character.php:'edit_biglandlord' |
| `action:edit_contract` | action | 房東側 |  | config/character.php:'edit_contract' |
| `action:edit_estate` | action | 房東側 |  | config/character.php:'edit_estate' |
| `action:edit_notification` | action | 房東側 |  | config/character.php:'edit_notification' |
| `action:edit_owner_repair` | action | 房東側 |  | config/character.php:'edit_owner_repair' |
| `action:edit_repair` | action | 房東側 |  | config/character.php:'edit_repair' |
| `action:edit_role` | action | 房東側 |  | config/character.php:'edit_role' |
| `action:edit_role_team` | action | 房東側 |  | config/character.php:'edit_role_team' |
| `action:edit_social_housing_sheet` | action | 房東側 |  | config/character.php:'edit_social_housing_sheet' |
| `action:export_bill` | action | 房東側 |  | config/character.php:'export_bill' |
| `action:export_contract` | action | 房東側 |  | config/character.php:'export_contract' |
| `action:export_estate` | action | 房東側 |  | config/character.php:'export_estate' |
| `action:export_repair` | action | 房東側 |  | config/character.php:'export_repair' |
| `action:owner_bill` | action | 房東側 |  | config/character.php:'owner_bill' |
| `action:pay_bill` | action | 房東側 |  | config/character.php:'pay_bill' |
| `action:public_estate` | action | 房東側 |  | config/character.php:'public_estate' |
| `action:receive_bill` | action | 房東側 |  | config/character.php:'receive_bill' |
| `action:send_contract_invitation` | action | 房東側 |  | config/character.php:'send_contract_invitation' |
| `action:show_biglandlord` | action | 房東側 |  | config/character.php:'show_biglandlord' |
| `action:show_biglandlord_report` | action | 房東側 |  | config/character.php:'show_biglandlord_report' |
| `action:show_bill` | action | 房東側 |  | config/character.php:'show_bill' |
| `action:show_contract` | action | 房東側 |  | config/character.php:'show_contract' |
| `action:show_contract_history` | action | 房東側 |  | config/character.php:'show_contract_history' |
| `action:show_contract_signed` | action | 房東側 |  | config/character.php:'show_contract_signed' |
| `action:show_email_log` | action | 房東側 |  | config/character.php:'show_email_log' |
| `action:show_estate` | action | 房東側 |  | config/character.php:'show_estate' |
| `action:show_lessee` | action | 房東側 |  | config/character.php:'show_lessee' |
| `action:show_notification` | action | 房東側 |  | config/character.php:'show_notification' |
| `action:show_owner_bill` | action | 房東側 |  | config/character.php:'show_owner_bill' |
| `action:show_owner_contract` | action | 房東側 |  | config/character.php:'show_owner_contract' |
| `action:show_owner_contract_history` | action | 房東側 |  | config/character.php:'show_owner_contract_history' |
| `action:show_owner_contract_signed` | action | 房東側 |  | config/character.php:'show_owner_contract_signed' |
| `action:show_owner_estate` | action | 房東側 |  | config/character.php:'show_owner_estate' |
| `action:show_owner_repair` | action | 房東側 |  | config/character.php:'show_owner_repair' |
| `action:show_repair` | action | 房東側 |  | config/character.php:'show_repair' |
| `action:show_role` | action | 房東側 |  | config/character.php:'show_role' |
| `action:show_role_team` | action | 房東側 |  | config/character.php:'show_role_team' |
| `action:sign_contract` | action | 房東側 |  | config/character.php:'sign_contract' |
| `help:Landlordonboarding00_zh-Hant.html#加入團隊` | help | 房東側 |  | Landlordonboarding00_zh-Hant.html#加入團隊 |
| `help:Landlordonboarding00_zh-Hant.html#瀏覽物件所屬修繕` | help | 房東側 |  | Landlordonboarding00_zh-Hant.html#瀏覽物件所屬修繕 |
| `help:Landlordonboarding00_zh-Hant.html#瀏覽物件所屬合約` | help | 房東側 |  | Landlordonboarding00_zh-Hant.html#瀏覽物件所屬合約 |
| `help:Landlordonboarding00_zh-Hant.html#瀏覽物件所屬帳務` | help | 房東側 |  | Landlordonboarding00_zh-Hant.html#瀏覽物件所屬帳務 |
| `help:Landlordonboarding00_zh-Hant.html#瀏覽物件資訊` | help | 房東側 |  | Landlordonboarding00_zh-Hant.html#瀏覽物件資訊 |
| `help:Landlordonboarding00_zh-Hant.html#總覽資訊` | help | 房東側 |  | Landlordonboarding00_zh-Hant.html#總覽資訊 |
| `help:Landlordonboarding00phone_zh-Hant.html#加入團隊` | help | 房東側 |  | Landlordonboarding00phone_zh-Hant.html#加入團隊 |
| `help:Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬修繕` | help | 房東側 |  | Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬修繕 |
| `help:Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬合約` | help | 房東側 |  | Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬合約 |
| `help:Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬帳務` | help | 房東側 |  | Landlordonboarding00phone_zh-Hant.html#瀏覽物件所屬帳務 |
| `help:Landlordonboarding00phone_zh-Hant.html#瀏覽物件資訊` | help | 房東側 |  | Landlordonboarding00phone_zh-Hant.html#瀏覽物件資訊 |
| `help:Landlordonboarding00phone_zh-Hant.html#總覽資訊` | help | 房東側 |  | Landlordonboarding00phone_zh-Hant.html#總覽資訊 |
| `help:Landlordonboarding01_zh-Hant.html#創建帳號` | help | 房東側 |  | Landlordonboarding01_zh-Hant.html#創建帳號 |
| `help:Landlordonboarding01_zh-Hant.html#帳號設置` | help | 房東側 |  | Landlordonboarding01_zh-Hant.html#帳號設置 |
| `help:Landlordonboarding01_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding01_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding02_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#⚠️ 版本更新 |
| `help:Landlordonboarding02_zh-Hant.html#創建團隊` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#創建團隊 |
| `help:Landlordonboarding02_zh-Hant.html#功能重點：專業級股東報告，雲端式屋主回報` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#功能重點：專業級股東報告，雲端式屋主回報 |
| `help:Landlordonboarding02_zh-Hant.html#團隊成員管理` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#團隊成員管理 |
| `help:Landlordonboarding02_zh-Hant.html#團隊設置` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#團隊設置 |
| `help:Landlordonboarding02_zh-Hant.html#常見問題` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#常見問題 |
| `help:Landlordonboarding02_zh-Hant.html#新增大房東（所有權人/轉租人）：` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#新增大房東（所有權人/轉租人）： |
| `help:Landlordonboarding02_zh-Hant.html#新增＆管理大房東` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#新增＆管理大房東 |
| `help:Landlordonboarding02_zh-Hant.html#查看＆變更現行的訂閱方案` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#查看＆變更現行的訂閱方案 |
| `help:Landlordonboarding02_zh-Hant.html#設定團隊招租頁面網址＆時區` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#設定團隊招租頁面網址＆時區 |
| `help:Landlordonboarding02_zh-Hant.html#請各位擅用 【Ctrl+F】的搜索功能。` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#請各位擅用 【Ctrl+F】的搜索功能。 |
| `help:Landlordonboarding02_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding02_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding02_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding02_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding02_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding06Finance_zh-Hant.html#批次發送帳單` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#批次發送帳單 |
| `help:Landlordonboarding06Finance_zh-Hant.html#批次編輯帳單` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#批次編輯帳單 |
| `help:Landlordonboarding06Finance_zh-Hant.html#新增帳單` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#新增帳單 |
| `help:Landlordonboarding06Finance_zh-Hant.html#新增帳單-導覽＆介面介紹` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#新增帳單-導覽＆介面介紹 |
| `help:Landlordonboarding06Finance_zh-Hant.html#此篇新手上路，將分別告訴你` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#此篇新手上路，將分別告訴你 |
| `help:Landlordonboarding06Finance_zh-Hant.html#確認帳單` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#確認帳單 |
| `help:Landlordonboarding06Finance_zh-Hant.html#租金帳單` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#租金帳單 |
| `help:Landlordonboarding06Finance_zh-Hant.html#編輯帳單-導覽＆介面介紹` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#編輯帳單-導覽＆介面介紹 |
| `help:Landlordonboarding06Finance_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding06Finance_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding06Finance_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding06Finance_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding06Finance_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding06Finance_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding08Device_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | Landlordonboarding08Device_zh-Hant.html#⚠️ 版本更新 |
| `help:Landlordonboarding08Device_zh-Hant.html#智慧電錶` | help | 房東側 |  | Landlordonboarding08Device_zh-Hant.html#智慧電錶 |
| `help:Landlordonboarding08Device_zh-Hant.html#智慧電錶綁帳單` | help | 房東側 |  | Landlordonboarding08Device_zh-Hant.html#智慧電錶綁帳單 |
| `help:Landlordonboarding08Device_zh-Hant.html#查看用電度數` | help | 房東側 |  | Landlordonboarding08Device_zh-Hant.html#查看用電度數 |
| `help:Landlordonboarding08Device_zh-Hant.html#系統功能＆介面展示` | help | 房東側 |  | Landlordonboarding08Device_zh-Hant.html#系統功能＆介面展示 |
| `help:Landlordonboarding08Device_zh-Hant.html#非台科電電錶的基本設定及綁定物件` | help | 房東側 |  | Landlordonboarding08Device_zh-Hant.html#非台科電電錶的基本設定及綁定物件 |
| `help:Landlordonboarding08Device_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding08Device_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#一般生活費用、修繕費用⋯等單一帳單產生` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#一般生活費用、修繕費用⋯等單一帳單產生 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#創建社宅合約` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#創建社宅合約 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#創建社宅團隊` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#創建社宅團隊 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#創建社宅物件` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#創建社宅物件 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#押租金帳單產生＆發送` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#押租金帳單產生＆發送 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#清冊列表功能` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#清冊列表功能 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#社宅帳務功能` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#社宅帳務功能 |
| `help:Landlordonboarding09Socialhousing_zh-Hant.html#📌 小提醒` | help | 房東側 |  | Landlordonboarding09Socialhousing_zh-Hant.html#📌 小提醒 |
| `help:Landlordonboarding_zh-Hant.html#修繕篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#修繕篇 |
| `help:Landlordonboarding_zh-Hant.html#合約篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#合約篇 |
| `help:Landlordonboarding_zh-Hant.html#帳務篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#帳務篇 |
| `help:Landlordonboarding_zh-Hant.html#收款設置篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#收款設置篇 |
| `help:Landlordonboarding_zh-Hant.html#物件篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#物件篇 |
| `help:Landlordonboarding_zh-Hant.html#社宅篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#社宅篇 |
| `help:Landlordonboarding_zh-Hant.html#設備篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#設備篇 |
| `help:Landlordonboarding_zh-Hant.html#註冊篇（ㄧ）— 個人房東篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#註冊篇（ㄧ）— 個人房東篇 |
| `help:Landlordonboarding_zh-Hant.html#註冊篇（二）— 公司團隊篇` | help | 房東側 |  | Landlordonboarding_zh-Hant.html#註冊篇（二）— 公司團隊篇 |
| `help:advanced12_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | advanced12_zh-Hant.html#⚠️ 版本更新 |
| `help:advanced12_zh-Hant.html#企業會員帳號：統一編號` | help | 房東側 |  | advanced12_zh-Hant.html#企業會員帳號：統一編號 |
| `help:advanced12_zh-Hant.html#個人房東預設密碼：身分證字號` | help | 房東側 |  | advanced12_zh-Hant.html#個人房東預設密碼：身分證字號 |
| `help:advanced12_zh-Hant.html#個人房東：登入藍新後台` | help | 房東側 |  | advanced12_zh-Hant.html#個人房東：登入藍新後台 |
| `help:advanced12_zh-Hant.html#法人（團隊）房東：登入藍新後台` | help | 房東側 |  | advanced12_zh-Hant.html#法人（團隊）房東：登入藍新後台 |
| `help:advanced12_zh-Hant.html#藍新後台提款方法：` | help | 房東側 |  | advanced12_zh-Hant.html#藍新後台提款方法： |
| `help:beike_zh-Hant.html#兩家相似與不同之處` | help | 房東側 |  | beike_zh-Hant.html#兩家相似與不同之處 |
| `help:beike_zh-Hant.html#貝殼迅速攀升原因：` | help | 房東側 |  | beike_zh-Hant.html#貝殼迅速攀升原因： |
| `help:billexpired_zh-Hant.html#儲值前請先確認三個條件` | help | 房東側 |  | billexpired_zh-Hant.html#儲值前請先確認三個條件 |
| `help:contract_review_period_zh-Hant.html#1.契約審閱權` | help | 房東側 |  | contract_review_period_zh-Hant.html#1.契約審閱權 |
| `help:contract_review_period_zh-Hant.html#2.不動產租賃相關契約至少之審閱天數` | help | 房東側 |  | contract_review_period_zh-Hant.html#2.不動產租賃相關契約至少之審閱天數 |
| `help:einvoice_zh-Hant.html#Step 1：確認功能已啟用` | help | 房東側 |  | einvoice_zh-Hant.html#Step 1：確認功能已啟用 |
| `help:einvoice_zh-Hant.html#Step 2：選擇發票開立模式` | help | 房東側 |  | einvoice_zh-Hant.html#Step 2：選擇發票開立模式 |
| `help:einvoice_zh-Hant.html#Step 3：設定合約的「稅與發票」` | help | 房東側 |  | einvoice_zh-Hant.html#Step 3：設定合約的「稅與發票」 |
| `help:einvoice_zh-Hant.html#Step 4：帳單開立與查看發票` | help | 房東側 |  | einvoice_zh-Hant.html#Step 4：帳單開立與查看發票 |
| `help:einvoice_zh-Hant.html#作廢與重開發票` | help | 房東側 |  | einvoice_zh-Hant.html#作廢與重開發票 |
| `help:einvoice_zh-Hant.html#使用前需要先確認三件事` | help | 房東側 |  | einvoice_zh-Hant.html#使用前需要先確認三件事 |
| `help:einvoice_zh-Hant.html#名詞說明` | help | 房東側 |  | einvoice_zh-Hant.html#名詞說明 |
| `help:einvoice_zh-Hant.html#常見問題` | help | 房東側 |  | einvoice_zh-Hant.html#常見問題 |
| `help:einvoice_zh-Hant.html#這個功能可以做什麼` | help | 房東側 |  | einvoice_zh-Hant.html#這個功能可以做什麼 |
| `help:einvoice_zh-Hant.html#需要協助時找誰` | help | 房東側 |  | einvoice_zh-Hant.html#需要協助時找誰 |
| `help:einvoice_zh-Hant.html#📌 小提醒` | help | 房東側 |  | einvoice_zh-Hant.html#📌 小提醒 |
| `help:einvoice_zh-Hant.html#📌 小提醒` | help | 房東側 |  | einvoice_zh-Hant.html#📌 小提醒 |
| `help:einvoice_zh-Hant.html#📌 小提醒` | help | 房東側 |  | einvoice_zh-Hant.html#📌 小提醒 |
| `help:esg_zh-Hant.html#ESG的內涵` | help | 房東側 |  | esg_zh-Hant.html#ESG的內涵 |
| `help:esg_zh-Hant.html#一、什麼是ESG？` | help | 房東側 |  | esg_zh-Hant.html#一、什麼是ESG？ |
| `help:esg_zh-Hant.html#三、企業該如何去實踐ESG？` | help | 房東側 |  | esg_zh-Hant.html#三、企業該如何去實踐ESG？ |
| `help:esg_zh-Hant.html#二、為何要做ESG?` | help | 房東側 |  | esg_zh-Hant.html#二、為何要做ESG? |
| `help:landlordonboarding04lease_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#⚠️ 版本更新 |
| `help:landlordonboarding04lease_zh-Hant.html#上傳（既有）合約` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#上傳（既有）合約 |
| `help:landlordonboarding04lease_zh-Hant.html#合約簽訂` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#合約簽訂 |
| `help:landlordonboarding04lease_zh-Hant.html#常見問題` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#常見問題 |
| `help:landlordonboarding04lease_zh-Hant.html#常見問題` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#常見問題 |
| `help:landlordonboarding04lease_zh-Hant.html#建立合約` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#建立合約 |
| `help:landlordonboarding04lease_zh-Hant.html#批次續約` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#批次續約 |
| `help:landlordonboarding04lease_zh-Hant.html#提前終止合約` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#提前終止合約 |
| `help:landlordonboarding04lease_zh-Hant.html#提前終止合約流程：` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#提前終止合約流程： |
| `help:landlordonboarding04lease_zh-Hant.html#此篇新手上路，將分別告訴你如何` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#此篇新手上路，將分別告訴你如何 |
| `help:landlordonboarding04lease_zh-Hant.html#點交/點退` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#點交/點退 |
| `help:landlordonboarding04lease_zh-Hant.html#點退流程` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#點退流程 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding04lease_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding04lease_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#JGB 支援哪幾家線上金流？` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#JGB 支援哪幾家線上金流？ |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#中國信託（中信）` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#中國信託（中信） |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#單一金流設定多組帳號` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#單一金流設定多組帳號 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#國泰（虛擬ATM）` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#國泰（虛擬ATM） |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#常見問題` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#常見問題 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#永豐（虛擬ATM）` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#永豐（虛擬ATM） |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#現金收款帳戶` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#現金收款帳戶 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#藍新（信用卡、超商代碼、虛擬ATM）` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#藍新（信用卡、超商代碼、虛擬ATM） |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#虛擬 ATM 帳號分成兩種` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#虛擬 ATM 帳號分成兩種 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#請各位擅用 【Ctrl+F】的搜索功能。` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#請各位擅用 【Ctrl+F】的搜索功能。 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#開通線上金流教程` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#開通線上金流教程 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒 |
| `help:landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒` | help | 房東側 |  | landlordonboarding05Paymentsettings_zh-Hant.html#📌 小提醒 |
| `help:law20250520_zh-Hant.html#一、租賃契約書的保存期限（法律雖無明文強制，實務仍建議保留）` | help | 房東側 |  | law20250520_zh-Hant.html#一、租賃契約書的保存期限（法律雖無明文強制，實務仍建議保留） |
| `help:law20250520_zh-Hant.html#二、相關法律追溯期（請求權時效）` | help | 房東側 |  | law20250520_zh-Hant.html#二、相關法律追溯期（請求權時效） |
| `help:law20250520_zh-Hant.html#總結建議` | help | 房東側 |  | law20250520_zh-Hant.html#總結建議 |
| `help:onboarding10_zh-Hant.html` | help | 房東側 |  | onboarding10_zh-Hant.html |
| `help:onboarding11_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding11_zh-Hant.html#📌 小提醒 |
| `help:onboarding12_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding12_zh-Hant.html#📌 小提醒 |
| `help:onboarding13_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | onboarding13_zh-Hant.html#⚠️ 版本更新 |
| `help:onboarding13_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding13_zh-Hant.html#📌 小提醒 |
| `help:onboarding14_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | onboarding14_zh-Hant.html#⚠️ 版本更新 |
| `help:onboarding14_zh-Hant.html#一、收款帳單 - 收據下載` | help | 房東側 |  | onboarding14_zh-Hant.html#一、收款帳單 - 收據下載 |
| `help:onboarding14_zh-Hant.html#二、繳款帳單 - 收據下載` | help | 房東側 |  | onboarding14_zh-Hant.html#二、繳款帳單 - 收據下載 |
| `help:onboarding1_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | onboarding1_zh-Hant.html#⚠️ 版本更新 |
| `help:onboarding1_zh-Hant.html#一、註冊篇` | help | 房東側 |  | onboarding1_zh-Hant.html#一、註冊篇 |
| `help:onboarding1_zh-Hant.html#三、房東登入篇` | help | 房東側 |  | onboarding1_zh-Hant.html#三、房東登入篇 |
| `help:onboarding1_zh-Hant.html#二、租客電子合約邀請註冊` | help | 房東側 |  | onboarding1_zh-Hant.html#二、租客電子合約邀請註冊 |
| `help:onboarding1_zh-Hant.html#四、租客登入篇` | help | 房東側 |  | onboarding1_zh-Hant.html#四、租客登入篇 |
| `help:onboarding1_zh-Hant.html#驗證碼會傳到Email信箱內` | help | 房東側 |  | onboarding1_zh-Hant.html#驗證碼會傳到Email信箱內 |
| `help:onboarding1_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding1_zh-Hant.html#📌 小提醒 |
| `help:onboarding2_zh-Hant.html#一、房東帳號篇：` | help | 房東側 |  | onboarding2_zh-Hant.html#一、房東帳號篇： |
| `help:onboarding2_zh-Hant.html#三、租客帳號篇：` | help | 房東側 |  | onboarding2_zh-Hant.html#三、租客帳號篇： |
| `help:onboarding2_zh-Hant.html#二、團隊帳號篇：` | help | 房東側 |  | onboarding2_zh-Hant.html#二、團隊帳號篇： |
| `help:onboarding3_zh-Hant.html#一、線下（現金）付款` | help | 租客側 |  | onboarding3_zh-Hant.html#一、線下（現金）付款 |
| `help:onboarding3_zh-Hant.html#三、線上付款：信用卡` | help | 租客側 |  | onboarding3_zh-Hant.html#三、線上付款：信用卡 |
| `help:onboarding3_zh-Hant.html#二、線上付款：虛擬ATM（藍新、國泰、永豐）` | help | 租客側 |  | onboarding3_zh-Hant.html#二、線上付款：虛擬ATM（藍新、國泰、永豐） |
| `help:onboarding3_zh-Hant.html#📌 小提醒` | help | 租客側 |  | onboarding3_zh-Hant.html#📌 小提醒 |
| `help:onboarding4_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | onboarding4_zh-Hant.html#⚠️ 版本更新 |
| `help:onboarding4_zh-Hant.html#一、新增物件` | help | 房東側 |  | onboarding4_zh-Hant.html#一、新增物件 |
| `help:onboarding4_zh-Hant.html#三、批次上傳物件` | help | 房東側 |  | onboarding4_zh-Hant.html#三、批次上傳物件 |
| `help:onboarding4_zh-Hant.html#二、複製現有物件` | help | 房東側 |  | onboarding4_zh-Hant.html#二、複製現有物件 |
| `help:onboarding4_zh-Hant.html#另外由於JGB系統已於 2022/05/12 新增社區功能` | help | 房東側 |  | onboarding4_zh-Hant.html#另外由於JGB系統已於 2022/05/12 新增社區功能 |
| `help:onboarding4_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding4_zh-Hant.html#📌 小提醒 |
| `help:onboarding5_zh-Hant.html#一、建立合約` | help | 房東側 |  | onboarding5_zh-Hant.html#一、建立合約 |
| `help:onboarding5_zh-Hant.html#二、編輯合約` | help | 房東側 |  | onboarding5_zh-Hant.html#二、編輯合約 |
| `help:onboarding5_zh-Hant.html#租客視角` | help | 房東側 |  | onboarding5_zh-Hant.html#租客視角 |
| `help:onboarding5_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding5_zh-Hant.html#📌 小提醒 |
| `help:onboarding6_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | onboarding6_zh-Hant.html#⚠️ 版本更新 |
| `help:onboarding6_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding6_zh-Hant.html#📌 小提醒 |
| `help:onboarding7_zh-Hant.html#如果租客不同意點交呢？` | help | 房東側 |  | onboarding7_zh-Hant.html#如果租客不同意點交呢？ |
| `help:onboarding7_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding7_zh-Hant.html#📌 小提醒 |
| `help:onboarding7_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding7_zh-Hant.html#📌 小提醒 |
| `help:onboarding8_zh-Hant.html#一、編輯帳單並送出` | help | 房東側 |  | onboarding8_zh-Hant.html#一、編輯帳單並送出 |
| `help:onboarding8_zh-Hant.html#三、收據確認` | help | 房東側 |  | onboarding8_zh-Hant.html#三、收據確認 |
| `help:onboarding8_zh-Hant.html#二、租客付款` | help | 房東側 |  | onboarding8_zh-Hant.html#二、租客付款 |
| `help:onboarding8_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding8_zh-Hant.html#📌 小提醒 |
| `help:onboarding9-1_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding9-1_zh-Hant.html#📌 小提醒 |
| `help:onboarding9-1_zh-Hant.html#📌 小提醒` | help | 房東側 |  | onboarding9-1_zh-Hant.html#📌 小提醒 |
| `help:onboarding9-2_zh-Hant.html#對方可以拒絕提前解約嗎？` | help | 租客側 |  | onboarding9-2_zh-Hant.html#對方可以拒絕提前解約嗎？ |
| `help:onboarding9-2_zh-Hant.html#租客一定可以提前解約嗎？` | help | 租客側 |  | onboarding9-2_zh-Hant.html#租客一定可以提前解約嗎？ |
| `help:onboarding9-2_zh-Hant.html#📌 小提醒` | help | 租客側 |  | onboarding9-2_zh-Hant.html#📌 小提醒 |
| `help:onboarding9-2_zh-Hant.html#📌 小提醒` | help | 租客側 |  | onboarding9-2_zh-Hant.html#📌 小提醒 |
| `help:paymentapply_zh-Hant.html#先確認您的身分是否符合` | help | 房東側 |  | paymentapply_zh-Hant.html#先確認您的身分是否符合 |
| `help:paymentapply_zh-Hant.html#款項會匯到哪裡？` | help | 房東側 |  | paymentapply_zh-Hant.html#款項會匯到哪裡？ |
| `help:paymentapply_zh-Hant.html#款項要怎麼提領？` | help | 房東側 |  | paymentapply_zh-Hant.html#款項要怎麼提領？ |
| `help:property_zh-Hant.html#創建社區` | help | 房東側 |  | property_zh-Hant.html#創建社區 |
| `help:property_zh-Hant.html#常見問題` | help | 房東側 |  | property_zh-Hant.html#常見問題 |
| `help:property_zh-Hant.html#建立物件` | help | 房東側 |  | property_zh-Hant.html#建立物件 |
| `help:property_zh-Hant.html#批次新增物件` | help | 房東側 |  | property_zh-Hant.html#批次新增物件 |
| `help:property_zh-Hant.html#批次新增社區` | help | 房東側 |  | property_zh-Hant.html#批次新增社區 |
| `help:property_zh-Hant.html#招租` | help | 房東側 |  | property_zh-Hant.html#招租 |
| `help:property_zh-Hant.html#查看/編輯已建立之物件` | help | 房東側 |  | property_zh-Hant.html#查看/編輯已建立之物件 |
| `help:property_zh-Hant.html#查看/編輯已建立社區` | help | 房東側 |  | property_zh-Hant.html#查看/編輯已建立社區 |
| `help:property_zh-Hant.html#買賣` | help | 房東側 |  | property_zh-Hant.html#買賣 |
| `help:propmarket2_zh-Hant.html#1.自建團隊` | help | 房東側 |  | propmarket2_zh-Hant.html#1.自建團隊 |
| `help:propmarket2_zh-Hant.html#2.技術合作：` | help | 房東側 |  | propmarket2_zh-Hant.html#2.技術合作： |
| `help:propmarket2_zh-Hant.html#3.加速器與創投：` | help | 房東側 |  | propmarket2_zh-Hant.html#3.加速器與創投： |
| `help:propmarket2_zh-Hant.html#什麼是PropTech?` | help | 房東側 |  | propmarket2_zh-Hant.html#什麼是PropTech? |
| `help:qa01_zh-Hant.html` | help | 房東側 |  | qa01_zh-Hant.html |
| `help:qa04_zh-Hant.html#📌 小提醒` | help | 房東側 |  | qa04_zh-Hant.html#📌 小提醒 |
| `help:qa05_zh-Hant.html#📌 小提醒` | help | 房東側 |  | qa05_zh-Hant.html#📌 小提醒 |
| `help:qa06_zh-Hant.html#JGB 提供哪些公版合約？` | help | 房東側 |  | qa06_zh-Hant.html#JGB 提供哪些公版合約？ |
| `help:qa06_zh-Hant.html#為什麼我的選單裡沒有這麼多種？` | help | 房東側 |  | qa06_zh-Hant.html#為什麼我的選單裡沒有這麼多種？ |
| `help:qa07_zh-Hant.html#📌 小提醒` | help | 房東側 |  | qa07_zh-Hant.html#📌 小提醒 |
| `help:qa15_zh-Hant.html` | help | 房東側 |  | qa15_zh-Hant.html |
| `help:qa21_zh-Hant.html` | help | 房東側 |  | qa21_zh-Hant.html |
| `help:qa23_zh-Hant.html#有兩組權限沒開，選單會整個看不見` | help | 房東側 |  | qa23_zh-Hant.html#有兩組權限沒開，選單會整個看不見 |
| `help:qa23_zh-Hant.html#為什麼權限勾了卻沒有作用？` | help | 房東側 |  | qa23_zh-Hant.html#為什麼權限勾了卻沒有作用？ |
| `help:qa23_zh-Hant.html#📌 小提醒` | help | 房東側 |  | qa23_zh-Hant.html#📌 小提醒 |
| `help:qa27_zh-Hant.html#ATM付款` | help | 房東側 |  | qa27_zh-Hant.html#ATM付款 |
| `help:qa27_zh-Hant.html#信用卡付款` | help | 房東側 |  | qa27_zh-Hant.html#信用卡付款 |
| `help:qa27_zh-Hant.html#線上金流要收多少費用？` | help | 房東側 |  | qa27_zh-Hant.html#線上金流要收多少費用？ |
| `help:rent3_zh-Hant.html#一、什麼是租約公證？` | help | 房東側 |  | rent3_zh-Hant.html#一、什麼是租約公證？ |
| `help:rent3_zh-Hant.html#三、租約公證費用大約多少？` | help | 房東側 |  | rent3_zh-Hant.html#三、租約公證費用大約多少？ |
| `help:rent3_zh-Hant.html#二、公證單位去哪找？` | help | 房東側 |  | rent3_zh-Hant.html#二、公證單位去哪找？ |
| `help:rent3_zh-Hant.html#五、申請租金補貼一定要將租約公證嗎？` | help | 房東側 |  | rent3_zh-Hant.html#五、申請租金補貼一定要將租約公證嗎？ |
| `help:rent3_zh-Hant.html#四、租約公證對房東和租客的好處及保障？` | help | 房東側 |  | rent3_zh-Hant.html#四、租約公證對房東和租客的好處及保障？ |
| `help:rentallaw.pt1_zh-Hant.html` | help | 房東側 |  | rentallaw.pt1_zh-Hant.html |
| `help:rentallaw.pt2_zh-Hant.html#一、對房東的影響——房東常見的租屋糾紛是否能以租賃專法保障？` | help | 房東側 |  | rentallaw.pt2_zh-Hant.html#一、對房東的影響——房東常見的租屋糾紛是否能以租賃專法保障？ |
| `help:rentallaw.pt2_zh-Hant.html#二、對租客的影響——租客常見的租屋糾紛是否能以租賃專法保障？` | help | 房東側 |  | rentallaw.pt2_zh-Hant.html#二、對租客的影響——租客常見的租屋糾紛是否能以租賃專法保障？ |
| `help:rentallaw.pt3_zh-Hant.html#一、什麼是包租業？又什麼是代管業？` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#一、什麼是包租業？又什麼是代管業？ |
| `help:rentallaw.pt3_zh-Hant.html#三、包租代管業者怎麼賺錢？` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#三、包租代管業者怎麼賺錢？ |
| `help:rentallaw.pt3_zh-Hant.html#二、包租跟代管的優勢分別是什麼？如果我是房東又該選擇哪個？` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#二、包租跟代管的優勢分別是什麼？如果我是房東又該選擇哪個？ |
| `help:rentallaw.pt3_zh-Hant.html#五、要如何成為一名專業包管人員？` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#五、要如何成為一名專業包管人員？ |
| `help:rentallaw.pt3_zh-Hant.html#代管` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#代管 |
| `help:rentallaw.pt3_zh-Hant.html#包租` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#包租 |
| `help:rentallaw.pt3_zh-Hant.html#四、如果想成政府許可的包管業者，該如何申請？` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#四、如果想成政府許可的包管業者，該如何申請？ |
| `help:rentallaw.pt3_zh-Hant.html#報名資格` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#報名資格 |
| `help:rentallaw.pt3_zh-Hant.html#申請流程` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#申請流程 |
| `help:rentallaw.pt3_zh-Hant.html#訓練期程` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#訓練期程 |
| `help:rentallaw.pt3_zh-Hant.html#（一）主要收入來源` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#（一）主要收入來源 |
| `help:rentallaw.pt3_zh-Hant.html#（二）租賃專法補貼` | help | 房東側 |  | rentallaw.pt3_zh-Hant.html#（二）租賃專法補貼 |
| `help:rentallaw.pt5_zh-Hant.html#【公益出租人】` | help | 房東側 |  | rentallaw.pt5_zh-Hant.html#【公益出租人】 |
| `help:rentallaw.pt5_zh-Hant.html#【委託包租代管的一般房東】` | help | 房東側 |  | rentallaw.pt5_zh-Hant.html#【委託包租代管的一般房東】 |
| `help:rentallaw.pt5_zh-Hant.html#【社宅包租代管房東】` | help | 房東側 |  | rentallaw.pt5_zh-Hant.html#【社宅包租代管房東】 |
| `help:repair_zh-Hant.html#安排修繕` | help | 房東側 |  | repair_zh-Hant.html#安排修繕 |
| `help:repair_zh-Hant.html#完成修繕` | help | 房東側 |  | repair_zh-Hant.html#完成修繕 |
| `help:repair_zh-Hant.html#此篇新手上路，將分別告訴你如何` | help | 房東側 |  | repair_zh-Hant.html#此篇新手上路，將分別告訴你如何 |
| `help:repair_zh-Hant.html#結單` | help | 房東側 |  | repair_zh-Hant.html#結單 |
| `help:repair_zh-Hant.html#📌 小提醒` | help | 房東側 |  | repair_zh-Hant.html#📌 小提醒 |
| `help:repair_zh-Hant.html#📌 小提醒` | help | 房東側 |  | repair_zh-Hant.html#📌 小提醒 |
| `help:repair_zh-Hant.html#📌 小提醒` | help | 房東側 |  | repair_zh-Hant.html#📌 小提醒 |
| `help:repair_zh-Hant.html#📌 小提醒` | help | 房東側 |  | repair_zh-Hant.html#📌 小提醒 |
| `help:sea-internet_zh-Hant.html#一、東南亞網際網路市場有多大？` | help | 房東側 |  | sea-internet_zh-Hant.html#一、東南亞網際網路市場有多大？ |
| `help:sea-internet_zh-Hant.html#七、在東南亞網際網路市場該如何獲得客戶的心` | help | 房東側 |  | sea-internet_zh-Hant.html#七、在東南亞網際網路市場該如何獲得客戶的心 |
| `help:sea-internet_zh-Hant.html#三、如何用數位服務留住客戶` | help | 房東側 |  | sea-internet_zh-Hant.html#三、如何用數位服務留住客戶 |
| `help:sea-internet_zh-Hant.html#二、驅動數位服務（Digital Service）消費的三大因素` | help | 房東側 |  | sea-internet_zh-Hant.html#二、驅動數位服務（Digital Service）消費的三大因素 |
| `help:sea-internet_zh-Hant.html#五、客戶想在你的數位服務獲得什麼` | help | 房東側 |  | sea-internet_zh-Hant.html#五、客戶想在你的數位服務獲得什麼 |
| `help:sea-internet_zh-Hant.html#六、電子支付趨勢不可擋` | help | 房東側 |  | sea-internet_zh-Hant.html#六、電子支付趨勢不可擋 |
| `help:sea-internet_zh-Hant.html#四、搭上數位服務的船` | help | 房東側 |  | sea-internet_zh-Hant.html#四、搭上數位服務的船 |
| `help:slug00_zh-Hant.html#收不到E-mail驗證信？` | help | 房東側 |  | slug00_zh-Hant.html#收不到E-mail驗證信？ |
| `help:slug00_zh-Hant.html#收不到手機簡訊驗證碼？` | help | 房東側 |  | slug00_zh-Hant.html#收不到手機簡訊驗證碼？ |
| `help:slug01_zh-Hant.html` | help | 房東側 |  | slug01_zh-Hant.html |
| `help:slug02_zh-Hant.html` | help | 房東側 |  | slug02_zh-Hant.html |
| `help:slug03_zh-Hant.html` | help | 房東側 |  | slug03_zh-Hant.html |
| `help:slug100_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | slug100_zh-Hant.html#⚠️ 版本更新 |
| `help:slug101_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug101_zh-Hant.html#📌 小提醒 |
| `help:slug102_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | slug102_zh-Hant.html#⚠️ 版本更新 |
| `help:slug103_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | slug103_zh-Hant.html#⚠️ 版本更新 |
| `help:slug104_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | slug104_zh-Hant.html#⚠️ 版本更新 |
| `help:slug10_zh-Hant.html` | help | 房東側 |  | slug10_zh-Hant.html |
| `help:slug12_zh-Hant.html` | help | 房東側 |  | slug12_zh-Hant.html |
| `help:slug13_zh-Hant.html#簽約邀請逾期了怎麼辦？` | help | 房東側 |  | slug13_zh-Hant.html#簽約邀請逾期了怎麼辦？ |
| `help:slug13_zh-Hant.html#重新發送前請留意` | help | 房東側 |  | slug13_zh-Hant.html#重新發送前請留意 |
| `help:slug15_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | slug15_zh-Hant.html#⚠️ 版本更新 |
| `help:slug15_zh-Hant.html#歷史合約與帳單會保留多久？` | help | 房東側 |  | slug15_zh-Hant.html#歷史合約與帳單會保留多久？ |
| `help:slug17_zh-Hant.html` | help | 房東側 |  | slug17_zh-Hant.html |
| `help:slug1_zh-Hant.html#⚠️ 版本更新` | help | 房東側 |  | slug1_zh-Hant.html#⚠️ 版本更新 |
| `help:slug1_zh-Hant.html#前往「社區總表」，選擇社區` | help | 房東側 |  | slug1_zh-Hant.html#前往「社區總表」，選擇社區 |
| `help:slug20250612_zh-Hant.html` | help | 房東側 |  | slug20250612_zh-Hant.html |
| `help:slug20_zh-Hant.html#一、線下付款` | help | 房東側 |  | slug20_zh-Hant.html#一、線下付款 |
| `help:slug20_zh-Hant.html#二、線上付款（藍新、國泰、永豐、中信）` | help | 房東側 |  | slug20_zh-Hant.html#二、線上付款（藍新、國泰、永豐、中信） |
| `help:slug21_zh-Hant.html#房東多久會確認收款？系統會自動確認嗎？` | help | 房東側 |  | slug21_zh-Hant.html#房東多久會確認收款？系統會自動確認嗎？ |
| `help:slug22_zh-Hant.html#帳單分為兩種模式：線上 / 線下` | help | 房東側 |  | slug22_zh-Hant.html#帳單分為兩種模式：線上 / 線下 |
| `help:slug24_zh-Hant.html` | help | 房東側 |  | slug24_zh-Hant.html |
| `help:slug27_zh-Hant.html` | help | 房東側 |  | slug27_zh-Hant.html |
| `help:slug28_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug28_zh-Hant.html#📌 小提醒 |
| `help:slug29_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug29_zh-Hant.html#📌 小提醒 |
| `help:slug39_zh-Hant.html#物件狀態是怎麼判斷的？` | help | 房東側 |  | slug39_zh-Hant.html#物件狀態是怎麼判斷的？ |
| `help:slug48_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug48_zh-Hant.html#📌 小提醒 |
| `help:slug66_zh-Hant.html` | help | 房東側 |  | slug66_zh-Hant.html |
| `help:slug71_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug71_zh-Hant.html#📌 小提醒 |
| `help:slug73_zh-Hant.html` | help | 房東側 |  | slug73_zh-Hant.html |
| `help:slug75_zh-Hant.html#線上付款（自動對帳） - 管理方視角：` | help | 房東側 |  | slug75_zh-Hant.html#線上付款（自動對帳） - 管理方視角： |
| `help:slug75_zh-Hant.html#線下付款 - 管理方視角：` | help | 房東側 |  | slug75_zh-Hant.html#線下付款 - 管理方視角： |
| `help:slug75_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug75_zh-Hant.html#📌 小提醒 |
| `help:slug75_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug75_zh-Hant.html#📌 小提醒 |
| `help:slug76_zh-Hant.html#📌 小提醒` | help | 房東側 |  | slug76_zh-Hant.html#📌 小提醒 |
| `help:slug78_zh-Hant.html` | help | 房東側 |  | slug78_zh-Hant.html |
| `help:slug79_zh-Hant.html` | help | 房東側 |  | slug79_zh-Hant.html |
| `help:slug84_zh-Hant.html` | help | 房東側 |  | slug84_zh-Hant.html |
| `help:slug86_zh-Hant.html` | help | 房東側 |  | slug86_zh-Hant.html |
| `help:slug88_zh-Hant.html` | help | 房東側 |  | slug88_zh-Hant.html |
| `help:slug90_zh-Hant.html` | help | 房東側 |  | slug90_zh-Hant.html |
| `help:slug92_zh-Hant.html` | help | 房東側 |  | slug92_zh-Hant.html |
| `help:slug93_zh-Hant.html` | help | 房東側 |  | slug93_zh-Hant.html |
| `help:slug95_zh-Hant.html` | help | 房東側 |  | slug95_zh-Hant.html |
| `help:slug99_zh-Hant.html` | help | 房東側 |  | slug99_zh-Hant.html |
| `help:tenantintro.register_zh-Hant.html#註冊篇` | help | 租客側 |  | tenantintro.register_zh-Hant.html#註冊篇 |
| `help:tenantintro.register_zh-Hant.html#📌 小提醒` | help | 租客側 |  | tenantintro.register_zh-Hant.html#📌 小提醒 |
| `route:Admin\AnnouncementController@admin.announcement` | route | 房東側 | 是 | routes/web.php:admin.announcement |
| `route:Admin\ApiController@admin.apis.address_zip` | route | 房東側 | 是 | routes/web.php:admin.apis.address_zip |
| `route:Admin\ApiController@admin.apis.upload` | route | 房東側 | 是 | routes/web.php:admin.apis.upload |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.batch_publish` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.batch_publish |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.create` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.create |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.delete_media` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.delete_media |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.destroy` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.destroy |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.duplicate` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.duplicate |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.edit` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.edit |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.index` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.index |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.preview` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.preview |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.store` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.store |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.update` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.update |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.upload_media` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.upload_media |
| `route:Admin\AssistantContentController@admin.platform_settings.assistant_content.validate_json` | route | 房東側 | 是 | routes/web.php:admin.platform_settings.assistant_content.validate_json |
| `route:Admin\BannerController@admin.banner` | route | 房東側 | 是 | routes/web.php:admin.banner |
| `route:Admin\BiglandlordController@admin.biglandlord.exportEstates` | route | 房東側 | 是 | routes/web.php:admin.biglandlord.exportEstates |
| `route:Admin\BiglandlordController@admin.biglandlord.exportEstatesPage` | route | 房東側 | 是 | routes/web.php:admin.biglandlord.exportEstatesPage |
| `route:Admin\BillController@admin.bill` | route | 房東側 | 是 | routes/web.php:admin.bill |
| `route:Admin\BillController@admin.bill.generateInvoice` | route | 房東側 | 是 | routes/web.php:admin.bill.generateInvoice |
| `route:Admin\BillController@admin.bills` | route | 房東側 | 是 | routes/web.php:admin.bills |
| `route:Admin\BillController@admin.customer_service.bill_settings` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings |
| `route:Admin\BillController@admin.customer_service.bill_settings.add_detail` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.add_detail |
| `route:Admin\BillController@admin.customer_service.bill_settings.delete_detail` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.delete_detail |
| `route:Admin\BillController@admin.customer_service.bill_settings.force_status` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.force_status |
| `route:Admin\BillController@admin.customer_service.bill_settings.history.destroy` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.history.destroy |
| `route:Admin\BillController@admin.customer_service.bill_settings.history.update` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.history.update |
| `route:Admin\BillController@admin.customer_service.bill_settings.manual_complete.destroy` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.manual_complete.destroy |
| `route:Admin\BillController@admin.customer_service.bill_settings.regenerate_virtual_account` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.regenerate_virtual_account |
| `route:Admin\BillController@admin.customer_service.bill_settings.update` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.update |
| `route:Admin\BillController@admin.customer_service.bill_settings.update_detail` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_settings.update_detail |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings.create` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings.create |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings.destroy` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings.destroy |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings.edit` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings.edit |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings.search_roles` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings.search_roles |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings.store` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings.store |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings.test_push` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings.test_push |
| `route:Admin\BotbonnieSettingAdminController@admin.customer_service.botbonnie_settings.update` | route | 房東側 | 是 | routes/web.php:admin.customer_service.botbonnie_settings.update |
| `route:Admin\ContractAmountAdjustmentController@admin.customer_service.contract_amount_adjustment` | route | 房東側 | 是 | routes/web.php:admin.customer_service.contract_amount_adjustment |
| `route:Admin\ContractAmountAdjustmentController@admin.customer_service.contract_amount_adjustment.execute` | route | 房東側 | 是 | routes/web.php:admin.customer_service.contract_amount_adjustment.execute |
| `route:Admin\ContractAmountAdjustmentController@admin.customer_service.contract_amount_adjustment.preview` | route | 房東側 | 是 | routes/web.php:admin.customer_service.contract_amount_adjustment.preview |
| `route:Admin\ContractAmountAdjustmentController@admin.customer_service.contract_amount_adjustment.preview_status` | route | 房東側 | 是 | routes/web.php:admin.customer_service.contract_amount_adjustment.preview_status |
| `route:Admin\ContractController@admin.contract` | route | 房東側 | 是 | routes/web.php:admin.contract |
| `route:Admin\ContractController@admin.contracts` | route | 房東側 | 是 | routes/web.php:admin.contracts |
| `route:Admin\ContractController@admin.contracts_old` | route | 房東側 | 是 | routes/web.php:admin.contracts_old |
| `route:Admin\CouponController@admin.coupon` | route | 房東側 | 是 | routes/web.php:admin.coupon |
| `route:Admin\CustomerController@admin.customers.data` | route | 房東側 | 是 | routes/web.php:admin.customers.data |
| `route:Admin\CustomerController@admin.customers.information` | route | 房東側 | 是 | routes/web.php:admin.customers.information |
| `route:Admin\CustomerController@admin.customers.report` | route | 房東側 | 是 | routes/web.php:admin.customers.report |
| `route:Admin\CustomerController@admin.customers.tcloud` | route | 房東側 | 是 | routes/web.php:admin.customers.tcloud |
| `route:Admin\CustomerServiceController@/bill_payment_management/batch_update` | route | 房東側 | 是 | routes/web.php:/bill_payment_management/batch_update |
| `route:Admin\CustomerServiceController@/move_out_contracts/details/{id}` | route | 房東側 | 是 | routes/web.php:/move_out_contracts/details/{id} |
| `route:Admin\CustomerServiceController@/move_out_contracts/edit/{id}` | route | 房東側 | 是 | routes/web.php:/move_out_contracts/edit/{id} |
| `route:Admin\CustomerServiceController@/move_out_contracts/update/{id}` | route | 房東側 | 是 | routes/web.php:/move_out_contracts/update/{id} |
| `route:Admin\CustomerServiceController@/payment_management/batch_update_contracts` | route | 房東側 | 是 | routes/web.php:/payment_management/batch_update_contracts |
| `route:Admin\CustomerServiceController@/payment_management/get_contract_bills` | route | 房東側 | 是 | routes/web.php:/payment_management/get_contract_bills |
| `route:Admin\CustomerServiceController@/payment_management/get_payment_actions` | route | 房東側 | 是 | routes/web.php:/payment_management/get_payment_actions |
| `route:Admin\CustomerServiceController@/payment_management/get_role_payment_options` | route | 房東側 | 是 | routes/web.php:/payment_management/get_role_payment_options |
| `route:Admin\CustomerServiceController@/virtual_account_inquiry/get_bill_info` | route | 房東側 | 是 | routes/web.php:/virtual_account_inquiry/get_bill_info |
| `route:Admin\CustomerServiceController@admin.customer_service.add_tenant` | route | 租客側 | 是 | routes/web.php:admin.customer_service.add_tenant |
| `route:Admin\CustomerServiceController@admin.customer_service.add_tenant.add` | route | 租客側 | 是 | routes/web.php:admin.customer_service.add_tenant.add |
| `route:Admin\CustomerServiceController@admin.customer_service.add_tenant.search_contract` | route | 租客側 | 是 | routes/web.php:admin.customer_service.add_tenant.search_contract |
| `route:Admin\CustomerServiceController@admin.customer_service.add_tenant.search_user` | route | 租客側 | 是 | routes/web.php:admin.customer_service.add_tenant.search_user |
| `route:Admin\CustomerServiceController@admin.customer_service.balance_invoice_inquiry` | route | 房東側 | 是 | routes/web.php:admin.customer_service.balance_invoice_inquiry |
| `route:Admin\CustomerServiceController@admin.customer_service.balance_invoice_inquiry.check_anomalies` | route | 房東側 | 是 | routes/web.php:admin.customer_service.balance_invoice_inquiry.check_anomalies |
| `route:Admin\CustomerServiceController@admin.customer_service.balance_invoice_inquiry.community_bills` | route | 房東側 | 是 | routes/web.php:admin.customer_service.balance_invoice_inquiry.community_bills |
| `route:Admin\CustomerServiceController@admin.customer_service.balance_invoice_inquiry.monthly_status` | route | 房東側 | 是 | routes/web.php:admin.customer_service.balance_invoice_inquiry.monthly_status |
| `route:Admin\CustomerServiceController@admin.customer_service.balance_invoice_inquiry.team_data` | route | 房東側 | 是 | routes/web.php:admin.customer_service.balance_invoice_inquiry.team_data |
| `route:Admin\CustomerServiceController@admin.customer_service.balance_invoice_inquiry.team_list` | route | 房東側 | 是 | routes/web.php:admin.customer_service.balance_invoice_inquiry.team_list |
| `route:Admin\CustomerServiceController@admin.customer_service.bill_payment_management` | route | 房東側 | 是 | routes/web.php:admin.customer_service.bill_payment_management |
| `route:Admin\CustomerServiceController@admin.customer_service.contract_status_management` | route | 房東側 | 是 | routes/web.php:admin.customer_service.contract_status_management |
| `route:Admin\CustomerServiceController@admin.customer_service.contract_status_management.batch_update` | route | 房東側 | 是 | routes/web.php:admin.customer_service.contract_status_management.batch_update |
| `route:Admin\CustomerServiceController@admin.customer_service.electricity_meter_inquiry` | route | 房東側 | 是 | routes/web.php:admin.customer_service.electricity_meter_inquiry |
| `route:Admin\CustomerServiceController@admin.customer_service.electricity_meter_inquiry.search` | route | 房東側 | 是 | routes/web.php:admin.customer_service.electricity_meter_inquiry.search |
| `route:Admin\CustomerServiceController@admin.customer_service.iot_meter_history` | route | 房東側 | 是 | routes/web.php:admin.customer_service.iot_meter_history |
| `route:Admin\CustomerServiceController@admin.customer_service.istaging_device_inquiry` | route | 房東側 | 是 | routes/web.php:admin.customer_service.istaging_device_inquiry |
| `route:Admin\CustomerServiceController@admin.customer_service.istaging_device_inquiry.search` | route | 房東側 | 是 | routes/web.php:admin.customer_service.istaging_device_inquiry.search |
| `route:Admin\CustomerServiceController@admin.customer_service.istaging_device_inquiry.sync` | route | 房東側 | 是 | routes/web.php:admin.customer_service.istaging_device_inquiry.sync |
| `route:Admin\CustomerServiceController@admin.customer_service.low_battery_inquiry` | route | 房東側 | 是 | routes/web.php:admin.customer_service.low_battery_inquiry |
| `route:Admin\CustomerServiceController@admin.customer_service.low_battery_inquiry.search` | route | 房東側 | 是 | routes/web.php:admin.customer_service.low_battery_inquiry.search |
| `route:Admin\CustomerServiceController@admin.customer_service.move_out_contracts` | route | 房東側 | 是 | routes/web.php:admin.customer_service.move_out_contracts |
| `route:Admin\CustomerServiceController@admin.customer_service.nthurc_tax_adjustment.batch_update` | route | 房東側 | 是 | routes/web.php:admin.customer_service.nthurc_tax_adjustment.batch_update |
| `route:Admin\CustomerServiceController@admin.customer_service.nthurc_tax_adjustment.get_bills` | route | 房東側 | 是 | routes/web.php:admin.customer_service.nthurc_tax_adjustment.get_bills |
| `route:Admin\CustomerServiceController@admin.customer_service.nthurc_tax_adjustment.index` | route | 房東側 | 是 | routes/web.php:admin.customer_service.nthurc_tax_adjustment.index |
| `route:Admin\CustomerServiceController@admin.customer_service.payment_management` | route | 房東側 | 是 | routes/web.php:admin.customer_service.payment_management |
| `route:Admin\CustomerServiceController@admin.customer_service.sinopac_decryption` | route | 房東側 | 是 | routes/web.php:admin.customer_service.sinopac_decryption |
| `route:Admin\CustomerServiceController@admin.customer_service.virtual_account_inquiry` | route | 房東側 | 是 | routes/web.php:admin.customer_service.virtual_account_inquiry |
| `route:Admin\DataCleanupController@admin.customer_service.data_cleanup.delete` | route | 房東側 | 是 | routes/web.php:admin.customer_service.data_cleanup.delete |
| `route:Admin\DataCleanupController@admin.customer_service.data_cleanup.index` | route | 房東側 | 是 | routes/web.php:admin.customer_service.data_cleanup.index |
| `route:Admin\DataCleanupController@admin.customer_service.data_cleanup.query` | route | 房東側 | 是 | routes/web.php:admin.customer_service.data_cleanup.query |
| `route:Admin\DataCleanupController@admin.customer_service.data_cleanup.restore` | route | 房東側 | 是 | routes/web.php:admin.customer_service.data_cleanup.restore |
| `route:Admin\DemoFormController@/excel` | route | 房東側 | 是 | routes/web.php:/excel |
| `route:Admin\DemoFormController@admin.demo` | route | 房東側 | 是 | routes/web.php:admin.demo |
| `route:Admin\EstateController@admin.estates` | route | 房東側 | 是 | routes/web.php:admin.estates |
| `route:Admin\EstateController@admin.estates.map` | route | 房東側 | 是 | routes/web.php:admin.estates.map |
| `route:Admin\FeatureConfigController@admin.feature_configs` | route | 房東側 | 是 | routes/web.php:admin.feature_configs |
| `route:Admin\FeatureConfigController@admin.feature_configs.cycle_date_type_default_settings` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.cycle_date_type_default_settings |
| `route:Admin\FeatureConfigController@admin.feature_configs.delete_role` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.delete_role |
| `route:Admin\FeatureConfigController@admin.feature_configs.deposit_interest_settings` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.deposit_interest_settings |
| `route:Admin\FeatureConfigController@admin.feature_configs.fixed_virtual_account_settings` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.fixed_virtual_account_settings |
| `route:Admin\FeatureConfigController@admin.feature_configs.roles` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.roles |
| `route:Admin\FeatureConfigController@admin.feature_configs.search_roles` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.search_roles |
| `route:Admin\FeatureConfigController@admin.feature_configs.search_users` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.search_users |
| `route:Admin\FeatureConfigController@admin.feature_configs.update_cycle_date_type_default_settings` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.update_cycle_date_type_default_settings |
| `route:Admin\FeatureConfigController@admin.feature_configs.update_deposit_interest_settings` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.update_deposit_interest_settings |
| `route:Admin\FeatureConfigController@admin.feature_configs.update_fixed_virtual_account_settings` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.update_fixed_virtual_account_settings |
| `route:Admin\FeatureConfigController@admin.feature_configs.user_roles` | route | 房東側 | 是 | routes/web.php:admin.feature_configs.user_roles |
| `route:Admin\FeedbackController@admin.feedback` | route | 房東側 | 是 | routes/web.php:admin.feedback |
| `route:Admin\HelpCenterController@admin.help.centers` | route | 房東側 | 是 | routes/web.php:admin.help.centers |
| `route:Admin\HelpCenterController@admin.help.centers.group` | route | 房東側 | 是 | routes/web.php:admin.help.centers.group |
| `route:Admin\HelpCenterController@admin.help.centers.preview` | route | 房東側 | 是 | routes/web.php:admin.help.centers.preview |
| `route:Admin\HelpCenterController@admin.help.centers.relatedPost` | route | 房東側 | 是 | routes/web.php:admin.help.centers.relatedPost |
| `route:Admin\HelpCenterController@admin.help.centers.subgroup` | route | 房東側 | 是 | routes/web.php:admin.help.centers.subgroup |
| `route:Admin\IndexController@admin.auth.google` | route | 房東側 | 是 | routes/web.php:admin.auth.google |
| `route:Admin\IndexController@admin.auth.google.callback` | route | 房東側 | 是 | routes/web.php:admin.auth.google.callback |
| `route:Admin\IndexController@admin.indexs` | route | 房東側 | 是 | routes/web.php:admin.indexs |
| `route:Admin\IndexController@admin.login` | route | 房東側 | 是 | routes/web.php:admin.login |
| `route:Admin\IndexController@admin.logout` | route | 房東側 | 是 | routes/web.php:admin.logout |
| `route:Admin\InvoiceFailureController@admin.invoice_failure` | route | 房東側 | 是 | routes/web.php:admin.invoice_failure |
| `route:Admin\InvoiceFailureController@admin.invoice_failures` | route | 房東側 | 是 | routes/web.php:admin.invoice_failures |
| `route:Admin\InvoiceFailureController@admin.invoice_failures.notify` | route | 房東側 | 是 | routes/web.php:admin.invoice_failures.notify |
| `route:Admin\InvoiceFailureController@admin.invoice_failures.scan` | route | 房東側 | 是 | routes/web.php:admin.invoice_failures.scan |
| `route:Admin\InvoiceSupplementController@/invoice_supplement/{id}` | route | 房東側 | 是 | routes/web.php:/invoice_supplement/{id} |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.batch_store` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.batch_store |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.create` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.create |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.index` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.index |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.logs` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.logs |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.reset_invoice` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.reset_invoice |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.search` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.search |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.store` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.store |
| `route:Admin\InvoiceSupplementController@admin.customer_service.invoice_supplement.touch_issue` | route | 房東側 | 是 | routes/web.php:admin.customer_service.invoice_supplement.touch_issue |
| `route:Admin\IotManagementController@admin.customer_service.create_miezo_meter` | route | 房東側 | 是 | routes/web.php:admin.customer_service.create_miezo_meter |
| `route:Admin\IotManagementController@admin.customer_service.iot_management` | route | 房東側 | 是 | routes/web.php:admin.customer_service.iot_management |
| `route:Admin\IotManagementController@admin.customer_service.iot_management.api_test` | route | 房東側 | 是 | routes/web.php:admin.customer_service.iot_management.api_test |
| `route:Admin\IotManagementController@admin.customer_service.iot_management.diagnose` | route | 房東側 | 是 | routes/web.php:admin.customer_service.iot_management.diagnose |
| `route:Admin\IotManagementController@admin.customer_service.iot_management.manual_topup` | route | 房東側 | 是 | routes/web.php:admin.customer_service.iot_management.manual_topup |
| `route:Admin\IotManagementController@admin.customer_service.store_miezo_meter` | route | 房東側 | 是 | routes/web.php:admin.customer_service.store_miezo_meter |
| `route:Admin\LocaleController@/import` | route | 房東側 | 是 | routes/web.php:/import |
| `route:Admin\LocaleController@admin.locales` | route | 房東側 | 是 | routes/web.php:admin.locales |
| `route:Admin\LogController@admin.logs.actionLog` | route | 房東側 | 是 | routes/web.php:admin.logs.actionLog |
| `route:Admin\LogController@admin.logs.adminLoginLog` | route | 房東側 | 是 | routes/web.php:admin.logs.adminLoginLog |
| `route:Admin\LogController@admin.logs.admin_log` | route | 房東側 | 是 | routes/web.php:admin.logs.admin_log |
| `route:Admin\LogController@admin.logs.commandLog` | route | 房東側 | 是 | routes/web.php:admin.logs.commandLog |
| `route:Admin\LogController@admin.logs.commandStat` | route | 房東側 | 是 | routes/web.php:admin.logs.commandStat |
| `route:Admin\LogController@admin.logs.email` | route | 房東側 | 是 | routes/web.php:admin.logs.email |
| `route:Admin\LogController@admin.logs.serverLoginLog` | route | 房東側 | 是 | routes/web.php:admin.logs.serverLoginLog |
| `route:Admin\LogController@admin.logs.sms` | route | 房東側 | 是 | routes/web.php:admin.logs.sms |
| `route:Admin\MarketingInviteController@admin.marketingInvite.destroy` | route | 房東側 | 是 | routes/web.php:admin.marketingInvite.destroy |
| `route:Admin\PaymentController@admin.cathaybk_atm_received` | route | 房東側 | 是 | routes/web.php:admin.cathaybk_atm_received |
| `route:Admin\PaymentController@admin.error_payments` | route | 房東側 | 是 | routes/web.php:admin.error_payments |
| `route:Admin\PaymentController@admin.payments` | route | 房東側 | 是 | routes/web.php:admin.payments |
| `route:Admin\PaymentController@admin.payments.subscriptions` | route | 房東側 | 是 | routes/web.php:admin.payments.subscriptions |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.cathaybk.cvs_query` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.cathaybk.cvs_query |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.cathaybk.cvs_query.execute` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.cathaybk.cvs_query.execute |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.function.check` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.function.check |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.get_config` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.get_config |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.index` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.index |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.check` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.check |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.diagnose` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.diagnose |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.test` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.test |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.test.execute` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.test.execute |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.virtual_account` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.virtual_account |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.virtual_account.disable` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.virtual_account.disable |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.virtual_account.query` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.virtual_account.query |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.sinopac.virtual_account.update_expiry` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.sinopac.virtual_account.update_expiry |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.test` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.test |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.test.execute` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.test.execute |
| `route:Admin\PaymentGatewayController@admin.payment_gateway.unmatched_payments` | route | 房東側 | 是 | routes/web.php:admin.payment_gateway.unmatched_payments |
| `route:Admin\PdfController@admin.pdfs.widget` | route | 房東側 | 是 | routes/web.php:admin.pdfs.widget |
| `route:Admin\PermissionController@admin.permissions.admin_group` | route | 房東側 | 是 | routes/web.php:admin.permissions.admin_group |
| `route:Admin\PermissionController@admin.permissions.admin_user` | route | 房東側 | 是 | routes/web.php:admin.permissions.admin_user |
| `route:Admin\PermissionController@admin.permissions.table` | route | 房東側 | 是 | routes/web.php:admin.permissions.table |
| `route:Admin\PromotionController@admin.promotion` | route | 房東側 | 是 | routes/web.php:admin.promotion |
| `route:Admin\RecruitmentPageController@/check-slug` | route | 房東側 | 是 | routes/web.php:/check-slug |
| `route:Admin\RecruitmentPageController@/get-roles-by-owner` | route | 房東側 | 是 | routes/web.php:/get-roles-by-owner |
| `route:Admin\RecruitmentPageController@/search-roles` | route | 房東側 | 是 | routes/web.php:/search-roles |
| `route:Admin\RecruitmentPageController@recruitment-pages.create` | route | 房東側 | 是 | routes/web.php:recruitment-pages.create |
| `route:Admin\RecruitmentPageController@recruitment-pages.destroy` | route | 房東側 | 是 | routes/web.php:recruitment-pages.destroy |
| `route:Admin\RecruitmentPageController@recruitment-pages.edit` | route | 房東側 | 是 | routes/web.php:recruitment-pages.edit |
| `route:Admin\RecruitmentPageController@recruitment-pages.index` | route | 房東側 | 是 | routes/web.php:recruitment-pages.index |
| `route:Admin\RecruitmentPageController@recruitment-pages.store` | route | 房東側 | 是 | routes/web.php:recruitment-pages.store |
| `route:Admin\RecruitmentPageController@recruitment-pages.update` | route | 房東側 | 是 | routes/web.php:recruitment-pages.update |
| `route:Admin\ReportController@admin.reports.esign` | route | 房東側 | 是 | routes/web.php:admin.reports.esign |
| `route:Admin\ReportController@admin.reports.index` | route | 房東側 | 是 | routes/web.php:admin.reports.index |
| `route:Admin\ReportController@admin.reports.notification` | route | 房東側 | 是 | routes/web.php:admin.reports.notification |
| `route:Admin\ReportController@admin.reports.notification_key` | route | 房東側 | 是 | routes/web.php:admin.reports.notification_key |
| `route:Admin\ReportController@admin.reports.tcloud` | route | 房東側 | 是 | routes/web.php:admin.reports.tcloud |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.create` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.create |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.destroy` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.destroy |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.edit` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.edit |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.get_role_companies` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.get_role_companies |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.index` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.index |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.search_role` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.search_role |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.store` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.store |
| `route:Admin\RoleInvoiceController@admin.customer_service.role_invoice_settings.update` | route | 房東側 | 是 | routes/web.php:admin.customer_service.role_invoice_settings.update |
| `route:Admin\TenantInfoUpdateController@admin.customer_service.user_info_modify` | route | 房東側 | 是 | routes/web.php:admin.customer_service.user_info_modify |
| `route:Admin\TenantInfoUpdateController@admin.customer_service.user_info_modify.edit` | route | 房東側 | 是 | routes/web.php:admin.customer_service.user_info_modify.edit |
| `route:Admin\TenantInfoUpdateController@admin.customer_service.user_info_modify.logs` | route | 房東側 | 是 | routes/web.php:admin.customer_service.user_info_modify.logs |
| `route:Admin\TenantInfoUpdateController@admin.customer_service.user_info_modify.search` | route | 房東側 | 是 | routes/web.php:admin.customer_service.user_info_modify.search |
| `route:Admin\TenantInfoUpdateController@admin.customer_service.user_info_modify.update` | route | 房東側 | 是 | routes/web.php:admin.customer_service.user_info_modify.update |
| `route:Admin\TenantInfoUpdateController@admin.customer_service.user_info_modify.validate` | route | 房東側 | 是 | routes/web.php:admin.customer_service.user_info_modify.validate |
| `route:Admin\ToolController@admin.tools.cathaybk_atm` | route | 房東側 | 是 | routes/web.php:admin.tools.cathaybk_atm |
| `route:Admin\ToolController@admin.tools.ctbc_pay` | route | 房東側 | 是 | routes/web.php:admin.tools.ctbc_pay |
| `route:Admin\ToolController@admin.tools.email` | route | 房東側 | 是 | routes/web.php:admin.tools.email |
| `route:Admin\ToolController@admin.tools.istaging` | route | 房東側 | 是 | routes/web.php:admin.tools.istaging |
| `route:Admin\ToolController@admin.tools.pop_role_agents` | route | 房東側 | 是 | routes/web.php:admin.tools.pop_role_agents |
| `route:Admin\ToolController@admin.tools.queueJobs` | route | 房東側 | 是 | routes/web.php:admin.tools.queueJobs |
| `route:Admin\ToolController@admin.tools.rent591` | route | 房東側 | 是 | routes/web.php:admin.tools.rent591 |
| `route:Admin\ToolController@admin.tools.sinopac` | route | 房東側 | 是 | routes/web.php:admin.tools.sinopac |
| `route:Admin\ToolController@admin.tools.transfer_subscription` | route | 房東側 | 是 | routes/web.php:admin.tools.transfer_subscription |
| `route:Admin\TrialFormController@admin.trial` | route | 房東側 | 是 | routes/web.php:admin.trial |
| `route:Admin\UserController@admin.role_payments` | route | 房東側 | 是 | routes/web.php:admin.role_payments |
| `route:Admin\UserController@admin.roles` | route | 房東側 | 是 | routes/web.php:admin.roles |
| `route:Admin\UserController@admin.users` | route | 房東側 | 是 | routes/web.php:admin.users |
| `route:Admin\UserController@admin.users.cacu` | route | 房東側 | 是 | routes/web.php:admin.users.cacu |
| `route:Admin\UserController@admin.users.inheritance` | route | 房東側 | 是 | routes/web.php:admin.users.inheritance |
| `route:Admin\UserController@admin.users.login_log` | route | 房東側 | 是 | routes/web.php:admin.users.login_log |
| `route:Admin\UserController@admin.users.online` | route | 房東側 | 是 | routes/web.php:admin.users.online |
| `route:AdvertisementController@/redirect/{adType}/{adId}` | route | 房東側 |  | routes/web.php:/redirect/{adType}/{adId} |
| `route:ApiController@/` | route | 房東側 |  | routes/web.php:/ |
| `route:ApiController@/api2/getAside` | route | 房東側 |  | routes/web.php:/api2/getAside |
| `route:ApiController@/api2/getCurrentUser` | route | 房東側 |  | routes/web.php:/api2/getCurrentUser |
| `route:ApiController@/api2/getDemoFormData` | route | 房東側 |  | routes/web.php:/api2/getDemoFormData |
| `route:ApiController@/banks` | route | 房東側 |  | routes/web.php:/banks |
| `route:ApiController@/currencyRates` | route | 房東側 |  | routes/web.php:/currencyRates |
| `route:ApiController@/mustDo` | route | 房東側 |  | routes/web.php:/mustDo |
| `route:ApiController@/mustDo/completed` | route | 房東側 |  | routes/api.php:/mustDo/completed |
| `route:ApiController@/mustDo/readLog` | route | 房東側 |  | routes/web.php:/mustDo/readLog |
| `route:ApiController@/timezone` | route | 房東側 |  | routes/web.php:/timezone |
| `route:ApiController@/twIdLocations` | route | 房東側 |  | routes/web.php:/twIdLocations |
| `route:ApiController@/zipData` | route | 房東側 |  | routes/web.php:/zipData |
| `route:ApiController@apis.log` | route | 房東側 |  | routes/web.php:apis.log |
| `route:ApiController@apis.mix-manifest` | route | 房東側 |  | routes/web.php:apis.mix-manifest |
| `route:ApiController@apis.upload` | route | 房東側 |  | routes/web.php:apis.upload |
| `route:ApiController@apis/rent/{roleId?}/{parameter?}` | route | 房東側 |  | routes/web.php:apis/rent/{roleId?}/{parameter?} |
| `route:ApiController@exchangeCurrency` | route | 房東側 |  | routes/web.php:exchangeCurrency |
| `route:ApiController@getListingsI18n` | route | 房東側 |  | routes/web.php:getListingsI18n |
| `route:ApiController@getPlanPricings` | route | 房東側 |  | routes/web.php:getPlanPricings |
| `route:ApiController@getSiteOptions` | route | 房東側 |  | routes/web.php:getSiteOptions |
| `route:ApiController@getZipData` | route | 房東側 |  | routes/web.php:getZipData |
| `route:ApiController@geti18n` | route | 房東側 |  | routes/web.php:geti18n |
| `route:Api\FacilitiesController@/config` | route | 房東側 |  | routes/api.php:/config |
| `route:Api\FeatureConfigApiController@/config` | route | 房東側 |  | routes/api.php:/config |
| `route:ApprovalController@/add` | route | 房東側 |  | routes/web.php:/add |
| `route:ApprovalController@/process` | route | 房東側 |  | routes/web.php:/process |
| `route:ApprovalController@/process/update/{id}` | route | 房東側 |  | routes/web.php:/process/update/{id} |
| `route:ApprovalController@/projects` | route | 房東側 |  | routes/web.php:/projects |
| `route:ApprovalController@/search` | route | 房東側 |  | routes/web.php:/search |
| `route:ApprovalController@/update/{id}` | route | 房東側 |  | routes/web.php:/update/{id} |
| `route:ApprovalController@add` | route | 房東側 |  | routes/api.php:add |
| `route:AuthController@/api2/authEmail/{action?}` | route | 房東側 |  | routes/web.php:/api2/authEmail/{action?} |
| `route:AuthController@/api2/authPhone/{action?}` | route | 房東側 |  | routes/web.php:/api2/authPhone/{action?} |
| `route:AuthController@/api2/login/{action?}/{customerAccount?}` | route | 房東側 |  | routes/web.php:/api2/login/{action?}/{customerAccount?} |
| `route:AuthController@users.sso` | route | 房東側 |  | routes/web.php:users.sso |
| `route:BalanceInvoiceController@/` | route | 房東側 |  | routes/api.php:/ |
| `route:BalanceInvoiceController@activityLogs` | route | 房東側 |  | routes/api.php:activityLogs |
| `route:BalanceInvoiceController@export` | route | 房東側 |  | routes/api.php:export |
| `route:BalanceInvoiceController@groupOptions` | route | 房東側 |  | routes/api.php:groupOptions |
| `route:BalanceInvoiceController@invoice` | route | 房東側 |  | routes/api.php:invoice |
| `route:BalanceInvoiceController@regenerateExcel` | route | 房東側 |  | routes/api.php:regenerateExcel |
| `route:BalanceInvoiceController@regenerateInvoice` | route | 房東側 |  | routes/api.php:regenerateInvoice |
| `route:BalanceInvoiceController@report` | route | 房東側 |  | routes/api.php:report |
| `route:BalanceInvoiceController@voidInvoice` | route | 房東側 |  | routes/api.php:voidInvoice |
| `route:BalanceInvoiceController@{id}` | route | 房東側 |  | routes/api.php:{id} |
| `route:BalanceInvoiceController@{id}/edit` | route | 房東側 |  | routes/api.php:{id}/edit |
| `route:BalanceInvoiceController@{status}` | route | 房東側 |  | routes/api.php:{status} |
| `route:BiglandlordController@/report` | route | 房東側 |  | routes/web.php:/report |
| `route:BiglandlordController@/report/fixItemGroupId` | route | 房東側 |  | routes/web.php:/report/fixItemGroupId |
| `route:BiglandlordController@/report/markDirty` | route | 房東側 |  | routes/web.php:/report/markDirty |
| `route:BiglandlordController@/report/send-result` | route | 房東側 |  | routes/web.php:/report/send-result |
| `route:BiglandlordController@/report/send-targets` | route | 房東側 |  | routes/web.php:/report/send-targets |
| `route:BiglandlordController@/report/sheet/{action}` | route | 房東側 |  | routes/web.php:/report/sheet/{action} |
| `route:BiglandlordController@all` | route | 房東側 |  | routes/api.php:all |
| `route:BiglandlordController@api.biglandlord.notify.invite` | route | 房東側 |  | routes/api.php:api.biglandlord.notify.invite |
| `route:BiglandlordController@api.biglandlord.notify.validate` | route | 房東側 |  | routes/api.php:api.biglandlord.notify.validate |
| `route:BiglandlordController@api.biglandlord.record.excel.confirm` | route | 房東側 |  | routes/api.php:api.biglandlord.record.excel.confirm |
| `route:BiglandlordController@api.biglandlord.record.excel.preview` | route | 房東側 |  | routes/api.php:api.biglandlord.record.excel.preview |
| `route:BiglandlordController@estate` | route | 房東側 |  | routes/api.php:estate |
| `route:BiglandlordController@estate/{id}` | route | 房東側 |  | routes/api.php:estate/{id} |
| `route:BiglandlordController@export` | route | 房東側 |  | routes/api.php:export |
| `route:BiglandlordController@import` | route | 房東側 |  | routes/api.php:import |
| `route:BiglandlordController@sample` | route | 房東側 |  | routes/api.php:sample |
| `route:BillController@/api2/bill/socialHousingSheets/{action?}/{subAction?}` | route | 房東側 |  | routes/web.php:/api2/bill/socialHousingSheets/{action?}/{subAction?} |
| `route:BillController@/bills/cycleBillPaymentOptions` | route | 房東側 |  | routes/api.php:/bills/cycleBillPaymentOptions |
| `route:BillController@/bills/cycleBillRecalcPeriod` | route | 房東側 |  | routes/api.php:/bills/cycleBillRecalcPeriod |
| `route:BillController@/bills/cycleBills` | route | 房東側 |  | routes/api.php:/bills/cycleBills |
| `route:BillController@/bills/searchOptions` | route | 房東側 |  | routes/api.php:/bills/searchOptions |
| `route:BillController@/bills/{id}/invoice-info` | route | 房東側 |  | routes/api.php:/bills/{id}/invoice-info |
| `route:BillController@/common` | route | 房東側 |  | routes/web.php:/common |
| `route:BillController@/createPaymentOptions` | route | 房東側 |  | routes/web.php:/createPaymentOptions |
| `route:BillController@/export/{action?}` | route | 房東側 |  | routes/web.php:/export/{action?} |
| `route:BillController@/items` | route | 房東側 |  | routes/api.php:/items |
| `route:BillController@/lazyFields` | route | 房東側 |  | routes/web.php:/lazyFields |
| `route:BillController@/list2/{type?}/{status?}` | route | 房東側 |  | routes/web.php:/list2/{type?}/{status?} |
| `route:BillController@/merge` | route | 房東側 |  | routes/web.php:/merge |
| `route:BillController@/payInfo` | route | 房東側 |  | routes/web.php:/payInfo |
| `route:BillController@/pick/{action?}` | route | 房東側 |  | routes/web.php:/pick/{action?} |
| `route:BillController@/receipt` | route | 房東側 |  | routes/web.php:/receipt |
| `route:BillController@/single` | route | 房東側 |  | routes/web.php:/single |
| `route:BillController@/singleFeeSubtotal` | route | 房東側 |  | routes/web.php:/singleFeeSubtotal |
| `route:BillController@/stat` | route | 房東側 |  | routes/web.php:/stat |
| `route:BillController@/subtotal` | route | 房東側 |  | routes/web.php:/subtotal |
| `route:BillController@batchCreateBill` | route | 房東側 |  | routes/web.php:batchCreateBill |
| `route:BillController@bill.payURL` | route | 房東側 |  | routes/web.php:bill.payURL |
| `route:BillController@bills.activity_logs` | route | 房東側 |  | routes/web.php:bills.activity_logs |
| `route:BillController@bills.archive` | route | 房東側 |  | routes/web.php:bills.archive |
| `route:BillController@bills.batch` | route | 房東側 |  | routes/web.php:bills.batch |
| `route:BillController@bills.batch-invoice` | route | 房東側 |  | routes/web.php:bills.batch-invoice |
| `route:BillController@bills.batch_edit_ziyu.export` | route | 房東側 |  | routes/web.php:bills.batch_edit_ziyu.export |
| `route:BillController@bills.batch_edit_ziyu.import` | route | 房東側 |  | routes/web.php:bills.batch_edit_ziyu.import |
| `route:BillController@bills.batch_fee_edit.confirm` | route | 房東側 |  | routes/web.php:bills.batch_fee_edit.confirm |
| `route:BillController@bills.batch_fee_edit.load` | route | 房東側 |  | routes/web.php:bills.batch_fee_edit.load |
| `route:BillController@bills.batch_fee_edit.resolve_ids` | route | 房東側 |  | routes/web.php:bills.batch_fee_edit.resolve_ids |
| `route:BillController@bills.cancel` | route | 房東側 |  | routes/web.php:bills.cancel |
| `route:BillController@bills.combination` | route | 房東側 |  | routes/web.php:bills.combination |
| `route:BillController@bills.current_meter` | route | 房東側 |  | routes/web.php:bills.current_meter |
| `route:BillController@bills.deposit_receipt.confirm` | route | 房東側 |  | routes/web.php:bills.deposit_receipt.confirm |
| `route:BillController@bills.deposit_receipt.export` | route | 房東側 |  | routes/web.php:bills.deposit_receipt.export |
| `route:BillController@bills.deposit_receipt.export_pdf` | route | 房東側 |  | routes/web.php:bills.deposit_receipt.export_pdf |
| `route:BillController@bills.deposit_receipt.pdf_list` | route | 房東側 |  | routes/web.php:bills.deposit_receipt.pdf_list |
| `route:BillController@bills.deposit_receipt.preview` | route | 房東側 |  | routes/web.php:bills.deposit_receipt.preview |
| `route:BillController@bills.deposit_receipt_pdf` | route | 房東側 |  | routes/web.php:bills.deposit_receipt_pdf |
| `route:BillController@bills.deposit_receipt_pdf_for_bill` | route | 房東側 |  | routes/web.php:bills.deposit_receipt_pdf_for_bill |
| `route:BillController@bills.excel.batch.import` | route | 房東側 |  | routes/web.php:bills.excel.batch.import |
| `route:BillController@bills.excel.batch.import.confirm` | route | 房東側 |  | routes/web.php:bills.excel.batch.import.confirm |
| `route:BillController@bills.excel.batch.import.preview` | route | 房東側 |  | routes/web.php:bills.excel.batch.import.preview |
| `route:BillController@bills.excel.batch.import.sample` | route | 房東側 |  | routes/web.php:bills.excel.batch.import.sample |
| `route:BillController@bills.invoice.confirm` | route | 房東側 |  | routes/web.php:bills.invoice.confirm |
| `route:BillController@bills.invoice.import` | route | 房東側 |  | routes/web.php:bills.invoice.import |
| `route:BillController@bills.invoice.preview` | route | 房東側 |  | routes/web.php:bills.invoice.preview |
| `route:BillController@bills.item` | route | 房東側 |  | routes/web.php:bills.item |
| `route:BillController@bills.list` | route | 房東側 |  | routes/web.php:bills.list |
| `route:BillController@bills.one` | route | 房東側 |  | routes/web.php:bills.one |
| `route:BillController@bills.pay_complete_remark` | route | 房東側 |  | routes/web.php:bills.pay_complete_remark |
| `route:BillController@bills.pay_method` | route | 房東側 |  | routes/web.php:bills.pay_method |
| `route:BillController@bills.pay_notification` | route | 房東側 |  | routes/web.php:bills.pay_notification |
| `route:BillController@bills.pdf` | route | 房東側 |  | routes/web.php:bills.pdf |
| `route:BillController@bills.pick` | route | 房東側 |  | routes/web.php:bills.pick |
| `route:BillController@bills.pie` | route | 房東側 |  | routes/web.php:bills.pie |
| `route:BillController@bills.prev_meter` | route | 房東側 |  | routes/web.php:bills.prev_meter |
| `route:BillController@bills.prev_meter_by_contract` | route | 房東側 |  | routes/web.php:bills.prev_meter_by_contract |
| `route:BillController@bills.set_complete` | route | 房東側 |  | routes/web.php:bills.set_complete |
| `route:BillController@bills.single-invoice` | route | 房東側 |  | routes/web.php:bills.single-invoice |
| `route:BillController@bills.update_deposit_receipt_no` | route | 房東側 |  | routes/web.php:bills.update_deposit_receipt_no |
| `route:BillController@bills.void_invoice` | route | 房東側 |  | routes/web.php:bills.void_invoice |
| `route:BillController@getbatchCreateOption/{type}` | route | 房東側 |  | routes/web.php:getbatchCreateOption/{type} |
| `route:BillController@upgradeTermsAgree` | route | 房東側 |  | routes/web.php:upgradeTermsAgree |
| `route:BotbonnieSettingController@admin.botbonnie.bind` | route | 房東側 |  | routes/web.php:admin.botbonnie.bind |
| `route:BotbonnieSettingController@admin.botbonnie.callback` | route | 房東側 |  | routes/web.php:admin.botbonnie.callback |
| `route:BotbonnieWebhookController@admin.botbonnie.webhook` | route | 房東側 |  | routes/web.php:admin.botbonnie.webhook |
| `route:CommunityController@/batch/{action?}` | route | 房東側 |  | routes/web.php:/batch/{action?} |
| `route:CommunityController@/community/searchOptions` | route | 房東側 |  | routes/api.php:/community/searchOptions |
| `route:CommunityController@/estates` | route | 房東側 |  | routes/web.php:/estates |
| `route:CommunityController@/files` | route | 房東側 |  | routes/web.php:/files |
| `route:CommunityController@/getAll` | route | 房東側 |  | routes/web.php:/getAll |
| `route:CommunityController@/list` | route | 房東側 |  | routes/web.php:/list |
| `route:CommunityController@/meta` | route | 房東側 |  | routes/web.php:/meta |
| `route:CommunityController@/single` | route | 房東側 |  | routes/web.php:/single |
| `route:CommunityController@communities.batch.confirm` | route | 房東側 |  | routes/web.php:communities.batch.confirm |
| `route:CommunityController@communities.batch.preview` | route | 房東側 |  | routes/web.php:communities.batch.preview |
| `route:CommunityController@downloadS3` | route | 房東側 |  | routes/api.php:downloadS3 |
| `route:CommunityRoiController@/investments` | route | 房東側 |  | routes/web.php:/investments |
| `route:CommunityRoiController@/operationDates` | route | 房東側 |  | routes/web.php:/operationDates |
| `route:CommunityRoiController@/report` | route | 房東側 |  | routes/web.php:/report |
| `route:ContractController@/additionalConvention` | route | 房東側 |  | routes/web.php:/additionalConvention |
| `route:ContractController@/api2/contract/list/{action?}/{status?}` | route | 房東側 |  | routes/web.php:/api2/contract/list/{action?}/{status?} |
| `route:ContractController@/api2/contract/single/{id}/{action?}` | route | 房東側 |  | routes/web.php:/api2/contract/single/{id}/{action?} |
| `route:ContractController@/api2/recharge_logs/{contractId?}` | route | 房東側 |  | routes/web.php:/api2/recharge_logs/{contractId?} |
| `route:ContractController@/archive/{category}` | route | 房東側 |  | routes/api.php:/archive/{category} |
| `route:ContractController@/attachments` | route | 房東側 |  | routes/web.php:/attachments |
| `route:ContractController@/basic` | route | 房東側 |  | routes/web.php:/basic |
| `route:ContractController@/contracts/recharge-accounts/search` | route | 房東側 |  | routes/api.php:/contracts/recharge-accounts/search |
| `route:ContractController@/contracts/searchOptions` | route | 房東側 |  | routes/api.php:/contracts/searchOptions |
| `route:ContractController@/declaration/export` | route | 房東側 |  | routes/api.php:/declaration/export |
| `route:ContractController@/declaration/reporting-agents` | route | 房東側 |  | routes/api.php:/declaration/reporting-agents |
| `route:ContractController@/facilities` | route | 房東側 |  | routes/web.php:/facilities |
| `route:ContractController@/info/{contractId}` | route | 房東側 |  | routes/web.php:/info/{contractId} |
| `route:ContractController@/metadata` | route | 房東側 |  | routes/api.php:/metadata |
| `route:ContractController@/rent` | route | 房東側 |  | routes/web.php:/rent |
| `route:ContractController@/send/{contractId}` | route | 房東側 |  | routes/web.php:/send/{contractId} |
| `route:ContractController@/situation` | route | 房東側 |  | routes/web.php:/situation |
| `route:ContractController@/transcript` | route | 房東側 |  | routes/web.php:/transcript |
| `route:ContractController@/{targetId}/copy/additionalConvention/{sourceId}` | route | 房東側 |  | routes/web.php:/{targetId}/copy/additionalConvention/{sourceId} |
| `route:ContractController@/{targetId}/copy/basic/{sourceId}` | route | 房東側 |  | routes/web.php:/{targetId}/copy/basic/{sourceId} |
| `route:ContractController@/{targetId}/copy/facilities/{sourceId}` | route | 房東側 |  | routes/web.php:/{targetId}/copy/facilities/{sourceId} |
| `route:ContractController@/{targetId}/copy/rent/{sourceId}` | route | 房東側 |  | routes/web.php:/{targetId}/copy/rent/{sourceId} |
| `route:ContractController@/{targetId}/copy/situation/{sourceId}` | route | 房東側 |  | routes/web.php:/{targetId}/copy/situation/{sourceId} |
| `route:ContractController@/{targetId}/copy/transcript/{sourceId}` | route | 房東側 |  | routes/web.php:/{targetId}/copy/transcript/{sourceId} |
| `route:ContractController@/{targetId}/copyFromEstate/facilities/{estateId}` | route | 房東側 |  | routes/web.php:/{targetId}/copyFromEstate/facilities/{estateId} |
| `route:ContractController@/{targetId}/copyFromEstate/rent/{estateId}` | route | 房東側 |  | routes/web.php:/{targetId}/copyFromEstate/rent/{estateId} |
| `route:ContractController@/{targetId}/copyFromEstate/transcript/{estateId}` | route | 房東側 |  | routes/web.php:/{targetId}/copyFromEstate/transcript/{estateId} |
| `route:ContractController@api.contract.cancel.move.in` | route | 房東側 |  | routes/api.php:api.contract.cancel.move.in |
| `route:ContractController@api.contract.cancel.move.out` | route | 房東側 |  | routes/api.php:api.contract.cancel.move.out |
| `route:ContractController@api.contract.confirm` | route | 房東側 |  | routes/api.php:api.contract.confirm |
| `route:ContractController@api.contract.extension` | route | 房東側 |  | routes/api.php:api.contract.extension |
| `route:ContractController@api.contract.invite` | route | 房東側 |  | routes/api.php:api.contract.invite |
| `route:ContractController@api.contract.pdf.preview` | route | 房東側 |  | routes/api.php:api.contract.pdf.preview |
| `route:ContractController@api2.contract.batchDelete` | route | 房東側 |  | routes/web.php:api2.contract.batchDelete |
| `route:ContractController@api2.contract.batchPreValidate` | route | 房東側 |  | routes/web.php:api2.contract.batchPreValidate |
| `route:ContractController@api2.contracts.edit` | route | 房東側 |  | routes/web.php:api2.contracts.edit |
| `route:ContractController@api2.contracts.move-in` | route | 房東側 |  | routes/web.php:api2.contracts.move-in |
| `route:ContractController@api2.contracts.move-out` | route | 房東側 |  | routes/web.php:api2.contracts.move-out |
| `route:ContractController@api2.contracts.pick` | route | 房東側 |  | routes/web.php:api2.contracts.pick |
| `route:ContractController@api2.contracts.show` | route | 房東側 |  | routes/web.php:api2.contracts.show |
| `route:ContractController@api2.contracts.upload` | route | 房東側 |  | routes/web.php:api2.contracts.upload |
| `route:ContractController@api3.contracts.earlyTermination.check` | route | 房東側 |  | routes/web.php:api3.contracts.earlyTermination.check |
| `route:ContractController@contract/{id}/createBillDraft` | route | 房東側 |  | routes/api.php:contract/{id}/createBillDraft |
| `route:ContractController@contracts.cancel` | route | 房東側 |  | routes/web.php:contracts.cancel |
| `route:ContractController@contracts.create` | route | 房東側 |  | routes/web.php:contracts.create |
| `route:ContractController@contracts.credit_card_auto_pay` | route | 房東側 |  | routes/web.php:contracts.credit_card_auto_pay |
| `route:ContractController@contracts.delete` | route | 房東側 |  | routes/web.php:contracts.delete |
| `route:ContractController@contracts.early_termination` | route | 房東側 |  | routes/web.php:contracts.early_termination |
| `route:ContractController@contracts.edit` | route | 房東側 |  | routes/web.php:contracts.edit |
| `route:ContractController@contracts.estate` | route | 房東側 |  | routes/web.php:contracts.estate |
| `route:ContractController@contracts.getContracts` | route | 房東側 |  | routes/web.php:contracts.getContracts |
| `route:ContractController@contracts.invite` | route | 房東側 |  | routes/web.php:contracts.invite |
| `route:ContractController@contracts.move_in` | route | 房東側 |  | routes/web.php:contracts.move_in |
| `route:ContractController@contracts.move_out` | route | 房東側 |  | routes/web.php:contracts.move_out |
| `route:ContractController@contracts.pdf` | route | 房東側 |  | routes/web.php:contracts.pdf |
| `route:ContractController@contracts.pdfImage` | route | 房東側 |  | routes/web.php:contracts.pdfImage |
| `route:ContractController@contracts.pdf_early_termination` | route | 房東側 |  | routes/web.php:contracts.pdf_early_termination |
| `route:ContractController@contracts.pdf_move_in` | route | 房東側 |  | routes/web.php:contracts.pdf_move_in |
| `route:ContractController@contracts.pdf_move_out` | route | 房東側 |  | routes/web.php:contracts.pdf_move_out |
| `route:ContractController@contracts.pdf_summary` | route | 房東側 |  | routes/web.php:contracts.pdf_summary |
| `route:ContractController@contracts.pick` | route | 房東側 |  | routes/web.php:contracts.pick |
| `route:ContractController@contracts.renew` | route | 房東側 |  | routes/web.php:contracts.renew |
| `route:ContractController@contracts.renewBillPreview` | route | 房東側 |  | routes/web.php:contracts.renewBillPreview |
| `route:ContractController@contracts.renewInit` | route | 房東側 |  | routes/web.php:contracts.renewInit |
| `route:ContractController@contracts.sendRenewContracts` | route | 房東側 |  | routes/web.php:contracts.sendRenewContracts |
| `route:ContractController@contracts.show` | route | 房東側 |  | routes/web.php:contracts.show |
| `route:ContractController@contracts.sign` | route | 房東側 |  | routes/web.php:contracts.sign |
| `route:ContractController@contracts.thinkcloud` | route | 房東側 |  | routes/web.php:contracts.thinkcloud |
| `route:CustomerController@customers.demand` | route | 房東側 |  | routes/web.php:customers.demand |
| `route:CustomerController@customers.tcloud` | route | 房東側 |  | routes/web.php:customers.tcloud |
| `route:DepositInterestController@/calculate` | route | 房東側 |  | routes/web.php:/calculate |
| `route:DepositInterestController@/search` | route | 房東側 |  | routes/web.php:/search |
| `route:DownloadController@actual-price-registrations/{filename}` | route | 房東側 |  | routes/api.php:actual-price-registrations/{filename} |
| `route:EntrustedContractController@api.entrustedContract.cancel` | route | 房東側 |  | routes/api.php:api.entrustedContract.cancel |
| `route:EntrustedContractController@api.entrustedContract.confirm` | route | 房東側 |  | routes/api.php:api.entrustedContract.confirm |
| `route:EntrustedContractController@api.entrustedContract.create` | route | 房東側 |  | routes/api.php:api.entrustedContract.create |
| `route:EntrustedContractController@api.entrustedContract.delete` | route | 房東側 |  | routes/api.php:api.entrustedContract.delete |
| `route:EntrustedContractController@api.entrustedContract.earlyTermination.cancel` | route | 房東側 |  | routes/api.php:api.entrustedContract.earlyTermination.cancel |
| `route:EntrustedContractController@api.entrustedContract.earlyTermination.check` | route | 房東側 |  | routes/api.php:api.entrustedContract.earlyTermination.check |
| `route:EntrustedContractController@api.entrustedContract.earlyTermination.send` | route | 房東側 |  | routes/api.php:api.entrustedContract.earlyTermination.send |
| `route:EntrustedContractController@api.entrustedContract.get.edit,info` | route | 房東側 |  | routes/api.php:api.entrustedContract.get.edit,info |
| `route:EntrustedContractController@api.entrustedContract.get.pdf` | route | 房東側 |  | routes/api.php:api.entrustedContract.get.pdf |
| `route:EntrustedContractController@api.entrustedContract.get.sign` | route | 房東側 |  | routes/api.php:api.entrustedContract.get.sign |
| `route:EntrustedContractController@api.entrustedContract.invite` | route | 房東側 |  | routes/api.php:api.entrustedContract.invite |
| `route:EntrustedContractController@api.entrustedContract.list` | route | 房東側 |  | routes/api.php:api.entrustedContract.list |
| `route:EntrustedContractController@api.entrustedContract.list.searchOptions` | route | 房東側 |  | routes/api.php:api.entrustedContract.list.searchOptions |
| `route:EntrustedContractController@api.entrustedContract.show` | route | 房東側 |  | routes/api.php:api.entrustedContract.show |
| `route:EntrustedContractController@api.entrustedContract.sign` | route | 房東側 |  | routes/api.php:api.entrustedContract.sign |
| `route:EntrustedContractController@api.entrustedContract.update` | route | 房東側 |  | routes/api.php:api.entrustedContract.update |
| `route:EntrustedContractController@entrustedContracts.estate` | route | 房東側 |  | routes/web.php:entrustedContracts.estate |
| `route:EntrustedContractController@entrustedContracts.thinkcloud.check` | route | 房東側 |  | routes/web.php:entrustedContracts.thinkcloud.check |
| `route:EscrowUserController@/add` | route | 房東側 |  | routes/web.php:/add |
| `route:EscrowUserController@/delete/{escrowUserId}` | route | 房東側 |  | routes/web.php:/delete/{escrowUserId} |
| `route:EscrowUserController@/list` | route | 房東側 |  | routes/web.php:/list |
| `route:EscrowUserController@/update/{escrowUserId}` | route | 房東側 |  | routes/web.php:/update/{escrowUserId} |
| `route:EscrowUserController@/{escrowUserId}` | route | 房東側 |  | routes/web.php:/{escrowUserId} |
| `route:EstateController@/api2/estate/index/{action}` | route | 房東側 |  | routes/web.php:/api2/estate/index/{action} |
| `route:EstateController@/api2/estate/list/{action?}/{type?}` | route | 房東側 |  | routes/web.php:/api2/estate/list/{action?}/{type?} |
| `route:EstateController@/attachments` | route | 房東側 |  | routes/web.php:/attachments |
| `route:EstateController@/estates/searchOptions` | route | 房東側 |  | routes/api.php:/estates/searchOptions |
| `route:EstateController@/estates/{status?}` | route | 房東側 |  | routes/web.php:/estates/{status?} |
| `route:EstateController@/list/{action?}/{type?}` | route | 房東側 |  | routes/web.php:/list/{action?}/{type?} |
| `route:EstateController@/metadata` | route | 房東側 |  | routes/api.php:/metadata |
| `route:EstateController@/monthlyReport/list` | route | 房東側 |  | routes/web.php:/monthlyReport/list |
| `route:EstateController@/single` | route | 房東側 |  | routes/web.php:/single |
| `route:EstateController@api.get.estate.monthly.report.list` | route | 房東側 |  | routes/api.php:api.get.estate.monthly.report.list |
| `route:EstateController@api2.estate.batchDelete` | route | 房東側 |  | routes/web.php:api2.estate.batchDelete |
| `route:EstateController@api2.estate.batchPreValidate` | route | 房東側 |  | routes/web.php:api2.estate.batchPreValidate |
| `route:EstateController@api2.estate.close` | route | 房東側 |  | routes/web.php:api2.estate.close |
| `route:EstateController@api2.estate.dashboard` | route | 房東側 |  | routes/web.php:api2.estate.dashboard |
| `route:EstateController@api2.estate.delete` | route | 房東側 |  | routes/web.php:api2.estate.delete |
| `route:EstateController@api2.estate.sell-close` | route | 房東側 |  | routes/web.php:api2.estate.sell-close |
| `route:EstateController@api2.estates.community` | route | 房東側 |  | routes/web.php:api2.estates.community |
| `route:EstateController@api2.estates.create` | route | 房東側 |  | routes/web.php:api2.estates.create |
| `route:EstateController@api2.estates.edit` | route | 房東側 |  | routes/web.php:api2.estates.edit |
| `route:EstateController@api2.estates.pick` | route | 房東側 |  | routes/web.php:api2.estates.pick |
| `route:EstateController@estates.bell` | route | 房東側 |  | routes/web.php:estates.bell |
| `route:EstateController@estates.close` | route | 房東側 |  | routes/web.php:estates.close |
| `route:EstateController@estates.community` | route | 房東側 |  | routes/web.php:estates.community |
| `route:EstateController@estates.copy` | route | 房東側 |  | routes/web.php:estates.copy |
| `route:EstateController@estates.custom_fees` | route | 房東側 |  | routes/web.php:estates.custom_fees |
| `route:EstateController@estates.delete` | route | 房東側 |  | routes/web.php:estates.delete |
| `route:EstateController@estates.general.batch` | route | 房東側 |  | routes/web.php:estates.general.batch |
| `route:EstateController@estates.general.batch.agents` | route | 房東側 |  | routes/web.php:estates.general.batch.agents |
| `route:EstateController@estates.general.batch.confirm` | route | 房東側 |  | routes/web.php:estates.general.batch.confirm |
| `route:EstateController@estates.general.batch.preview` | route | 房東側 |  | routes/web.php:estates.general.batch.preview |
| `route:EstateController@estates.general.batch.sample` | route | 房東側 |  | routes/web.php:estates.general.batch.sample |
| `route:EstateController@estates.house` | route | 房東側 |  | routes/web.php:estates.house |
| `route:EstateController@estates.map` | route | 房東側 |  | routes/web.php:estates.map |
| `route:EstateController@estates.open` | route | 房東側 |  | routes/web.php:estates.open |
| `route:EstateController@estates.sell-close` | route | 房東側 |  | routes/web.php:estates.sell-close |
| `route:EstateController@estates.sell-house` | route | 房東側 |  | routes/web.php:estates.sell-house |
| `route:EstateController@estates.sell-open` | route | 房東側 |  | routes/web.php:estates.sell-open |
| `route:EstateController@estates.sell-show` | route | 房東側 |  | routes/web.php:estates.sell-show |
| `route:EstateController@estates.show` | route | 房東側 |  | routes/web.php:estates.show |
| `route:EstateController@estates.social-housing.batch` | route | 房東側 |  | routes/web.php:estates.social-housing.batch |
| `route:EstateController@estates.social-housing.batch.confirm` | route | 房東側 |  | routes/web.php:estates.social-housing.batch.confirm |
| `route:EstateController@estates.social-housing.batch.preview` | route | 房東側 |  | routes/web.php:estates.social-housing.batch.preview |
| `route:EstateController@estates.social-housing.batch.sample` | route | 房東側 |  | routes/web.php:estates.social-housing.batch.sample |
| `route:ExternalController@/external_api/estate` | route | 房東側 |  | routes/web.php:/external_api/estate |
| `route:ExternalController@/external_api/nthurc` | route | 房東側 |  | routes/web.php:/external_api/nthurc |
| `route:ExternalController@/external_api/thinkcloud/{action?}` | route | 房東側 |  | routes/web.php:/external_api/thinkcloud/{action?} |
| `route:ExternalController@/external_api/token` | route | 房東側 |  | routes/web.php:/external_api/token |
| `route:External\BillApiController@api.external.bills.index` | route | 房東側 |  | routes/api.php:api.external.bills.index |
| `route:External\BillApiController@api.external.bills.show` | route | 房東側 |  | routes/api.php:api.external.bills.show |
| `route:External\ContractApiController@api.external.contracts.status-overview` | route | 房東側 |  | routes/api.php:api.external.contracts.status-overview |
| `route:External\ContractCheckinApiController@api.external.contracts.checkin-eligibility` | route | 房東側 |  | routes/api.php:api.external.contracts.checkin-eligibility |
| `route:External\EstateApiController@api.external.estates.index` | route | 房東側 |  | routes/api.php:api.external.estates.index |
| `route:External\EstateApiController@api.external.estates.show` | route | 房東側 |  | routes/api.php:api.external.estates.show |
| `route:External\InvoiceApiController@api.external.invoices.index` | route | 房東側 |  | routes/api.php:api.external.invoices.index |
| `route:External\InvoiceLogApiController@api.external.invoice-logs.index` | route | 房東側 |  | routes/api.php:api.external.invoice-logs.index |
| `route:External\IotManufacturerApiController@api.external.iot-manufacturers.index` | route | 房東側 |  | routes/api.php:api.external.iot-manufacturers.index |
| `route:External\MeterApiController@api.external.meters.index` | route | 房東側 |  | routes/api.php:api.external.meters.index |
| `route:External\MeterApiController@api.external.meters.show` | route | 房東側 |  | routes/api.php:api.external.meters.show |
| `route:External\PaymentApiController@api.external.payments.index` | route | 房東側 |  | routes/api.php:api.external.payments.index |
| `route:External\PaymentLogApiController@api.external.payment-logs.index` | route | 房東側 |  | routes/api.php:api.external.payment-logs.index |
| `route:External\RechargeAccountApiController@api.external.recharge-accounts.index` | route | 房東側 |  | routes/api.php:api.external.recharge-accounts.index |
| `route:External\RechargeAccountApiController@api.external.recharge-accounts.store` | route | 房東側 |  | routes/api.php:api.external.recharge-accounts.store |
| `route:External\RepairApiController@api.external.repairs.categories` | route | 房東側 |  | routes/api.php:api.external.repairs.categories |
| `route:External\RepairApiController@api.external.repairs.index` | route | 房東側 |  | routes/api.php:api.external.repairs.index |
| `route:External\RepairApiController@api.external.repairs.show` | route | 房東側 |  | routes/api.php:api.external.repairs.show |
| `route:External\RepairApiController@api.external.repairs.store` | route | 房東側 |  | routes/api.php:api.external.repairs.store |
| `route:External\SubscriptionApiController@api.external.roles.subscription` | route | 房東側 |  | routes/api.php:api.external.roles.subscription |
| `route:External\TeamMemberApiController@api.external.roles.member-permissions` | route | 房東側 |  | routes/api.php:api.external.roles.member-permissions |
| `route:External\TeamMemberApiController@api.external.roles.members` | route | 房東側 |  | routes/api.php:api.external.roles.members |
| `route:External\TenantApiController@api.external.tenants.registration-status` | route | 租客側 |  | routes/api.php:api.external.tenants.registration-status |
| `route:External\TenantApiController@api.external.tenants.summary` | route | 租客側 |  | routes/api.php:api.external.tenants.summary |
| `route:HelpAssistantController@/api2/assistant/chat` | route | 房東側 |  | routes/web.php:/api2/assistant/chat |
| `route:HelpAssistantController@/api2/assistant/chat-scenarios` | route | 房東側 |  | routes/web.php:/api2/assistant/chat-scenarios |
| `route:HelpAssistantController@/api2/assistant/enabled` | route | 房東側 |  | routes/web.php:/api2/assistant/enabled |
| `route:HelpAssistantController@/api2/assistant/feedback` | route | 房東側 |  | routes/web.php:/api2/assistant/feedback |
| `route:HelpAssistantController@/api2/assistant/guide` | route | 房東側 |  | routes/web.php:/api2/assistant/guide |
| `route:HelpAssistantController@/api2/assistant/report` | route | 房東側 |  | routes/web.php:/api2/assistant/report |
| `route:HelpAssistantController@/api2/assistant/search` | route | 房東側 |  | routes/web.php:/api2/assistant/search |
| `route:HelpAssistantController@/api2/assistant/suggestions` | route | 房東側 |  | routes/web.php:/api2/assistant/suggestions |
| `route:HelpAssistantController@/api2/assistant/track` | route | 房東側 |  | routes/web.php:/api2/assistant/track |
| `route:IndexController@/api2/ajaxRedirectTest` | route | 房東側 |  | routes/web.php:/api2/ajaxRedirectTest |
| `route:IndexController@/api2/demoForm/getOptions` | route | 房東側 |  | routes/web.php:/api2/demoForm/getOptions |
| `route:IndexController@/api2/demo_form` | route | 房東側 |  | routes/web.php:/api2/demo_form |
| `route:IndexController@/api2/helpCenter/{action?}` | route | 房東側 |  | routes/web.php:/api2/helpCenter/{action?} |
| `route:IndexController@/api2/marketingBonus` | route | 房東側 |  | routes/web.php:/api2/marketingBonus |
| `route:IndexController@/api2/trial_form` | route | 房東側 |  | routes/web.php:/api2/trial_form |
| `route:IndexController@/edit/{id}/{any2?}/{any3?}` | route | 房東側 |  | routes/web.php:/edit/{id}/{any2?}/{any3?} |
| `route:IndexController@/estates/dashboard/{any?}` | route | 房東側 |  | routes/web.php:/estates/dashboard/{any?} |
| `route:IndexController@/estates/{any?}/{any2?}` | route | 房東側 |  | routes/web.php:/estates/{any?}/{any2?} |
| `route:IndexController@/list/{status}` | route | 房東側 |  | routes/web.php:/list/{status} |
| `route:IndexController@/power_meter/{params?}` | route | 房東側 |  | routes/web.php:/power_meter/{params?} |
| `route:IndexController@/repair/{any?}/{any2?}` | route | 房東側 |  | routes/web.php:/repair/{any?}/{any2?} |
| `route:IndexController@/show/{id}` | route | 房東側 |  | routes/web.php:/show/{id} |
| `route:IndexController@/users/subscription/chose/{action?}` | route | 房東側 |  | routes/web.php:/users/subscription/chose/{action?} |
| `route:IndexController@/users/subscription/unsubscribe` | route | 房東側 |  | routes/web.php:/users/subscription/unsubscribe |
| `route:IndexController@/users/subscription/{any?}` | route | 房東側 |  | routes/web.php:/users/subscription/{any?} |
| `route:IndexController@/users/verify/{any}` | route | 房東側 |  | routes/web.php:/users/verify/{any} |
| `route:IndexController@/users/{any}/{any2?}/{any3?}` | route | 房東側 |  | routes/web.php:/users/{any}/{any2?}/{any3?} |
| `route:IndexController@/vite` | route | 房東側 |  | routes/web.php:/vite |
| `route:IndexController@/{any}` | route | 房東側 |  | routes/web.php:/{any} |
| `route:IndexController@/{id}/edit/{any2?}/{any3?}` | route | 房東側 |  | routes/web.php:/{id}/edit/{any2?}/{any3?} |
| `route:IndexController@bigLandlords/{any?}` | route | 房東側 |  | routes/web.php:bigLandlords/{any?} |
| `route:IndexController@bills.edit` | route | 房東側 |  | routes/web.php:bills.edit |
| `route:IndexController@bills.index` | route | 房東側 |  | routes/web.php:bills.index |
| `route:IndexController@bills.sheet` | route | 房東側 |  | routes/web.php:bills.sheet |
| `route:IndexController@bills.socialHousingSheets` | route | 房東側 |  | routes/web.php:bills.socialHousingSheets |
| `route:IndexController@bills.stat` | route | 房東側 |  | routes/web.php:bills.stat |
| `route:IndexController@communities.edit` | route | 房東側 |  | routes/web.php:communities.edit |
| `route:IndexController@communities.estates` | route | 房東側 |  | routes/web.php:communities.estates |
| `route:IndexController@communities.forceBinding` | route | 房東側 |  | routes/web.php:communities.forceBinding |
| `route:IndexController@communities.forceBinding.edit` | route | 房東側 |  | routes/web.php:communities.forceBinding.edit |
| `route:IndexController@communities.index` | route | 房東側 |  | routes/web.php:communities.index |
| `route:IndexController@communities.pick` | route | 房東側 |  | routes/web.php:communities.pick |
| `route:IndexController@communities.show` | route | 房東側 |  | routes/web.php:communities.show |
| `route:IndexController@contracts.index` | route | 房東側 |  | routes/web.php:contracts.index |
| `route:IndexController@contracts.move_in.social_housing` | route | 房東側 |  | routes/web.php:contracts.move_in.social_housing |
| `route:IndexController@contracts.move_out` | route | 房東側 |  | routes/web.php:contracts.move_out |
| `route:IndexController@contracts.move_out.social_housing` | route | 房東側 |  | routes/web.php:contracts.move_out.social_housing |
| `route:IndexController@contracts.pick` | route | 房東側 |  | routes/web.php:contracts.pick |
| `route:IndexController@contracts.show.social_housing` | route | 房東側 |  | routes/web.php:contracts.show.social_housing |
| `route:IndexController@controlPanel/{any?}` | route | 房東側 |  | routes/web.php:controlPanel/{any?} |
| `route:IndexController@entrustedContracts.index` | route | 房東側 |  | routes/web.php:entrustedContracts.index |
| `route:IndexController@estates.edit` | route | 房東側 |  | routes/web.php:estates.edit |
| `route:IndexController@estates.pick` | route | 房東側 |  | routes/web.php:estates.pick |
| `route:IndexController@exchange_currency` | route | 房東側 |  | routes/web.php:exchange_currency |
| `route:IndexController@indexs.emailOpen` | route | 房東側 |  | routes/web.php:indexs.emailOpen |
| `route:IndexController@indexs.shortUrl` | route | 房東側 |  | routes/web.php:indexs.shortUrl |
| `route:IndexController@marketing.welcome-bonus` | route | 房東側 |  | routes/web.php:marketing.welcome-bonus |
| `route:IndexController@members.index` | route | 房東側 |  | routes/web.php:members.index |
| `route:IndexController@nthurc.parking.projects` | route | 房東側 |  | routes/web.php:nthurc.parking.projects |
| `route:IndexController@nthurc.projects` | route | 房東側 |  | routes/web.php:nthurc.projects |
| `route:IndexController@result.screen` | route | 房東側 |  | routes/web.php:result.screen |
| `route:IndexController@share` | route | 房東側 |  | routes/web.php:share |
| `route:IndexController@tools.unlock` | route | 房東側 |  | routes/web.php:tools.unlock |
| `route:IndexController@users.advance` | route | 房東側 |  | routes/web.php:users.advance |
| `route:IndexController@users.approval` | route | 房東側 |  | routes/web.php:users.approval |
| `route:IndexController@users.index` | route | 房東側 |  | routes/web.php:users.index |
| `route:IndexController@users.info` | route | 房東側 |  | routes/web.php:users.info |
| `route:IndexController@users.lesseeList` | route | 房東側 |  | routes/web.php:users.lesseeList |
| `route:IndexController@users.notification` | route | 房東側 |  | routes/web.php:users.notification |
| `route:IndexController@users.orders` | route | 房東側 |  | routes/web.php:users.orders |
| `route:IndexController@users.payment` | route | 房東側 |  | routes/web.php:users.payment |
| `route:IndexController@users.rechargeAccountList` | route | 房東側 |  | routes/web.php:users.rechargeAccountList |
| `route:IndexController@users.signer_info` | route | 房東側 |  | routes/web.php:users.signer_info |
| `route:IndexController@users.team.owned.member` | route | 房東側 |  | routes/web.php:users.team.owned.member |
| `route:InternalController@/internal_api/ctbc_received/{payment}` | route | 房東側 |  | routes/web.php:/internal_api/ctbc_received/{payment} |
| `route:Internal\AgentManageController@/agents` | route | 房東側 |  | routes/api.php:/agents |
| `route:Internal\AgentManageController@/agents/{id}/active` | route | 房東側 |  | routes/api.php:/agents/{id}/active |
| `route:Internal\AgentManageController@/agents/{id}/permissions` | route | 房東側 |  | routes/api.php:/agents/{id}/permissions |
| `route:Internal\AgentManageController@/whoami` | route | 房東側 |  | routes/api.php:/whoami |
| `route:Internal\BillQueryController@/bills` | route | 房東側 |  | routes/api.php:/bills |
| `route:Internal\BillQueryController@/bills/{id}` | route | 房東側 |  | routes/api.php:/bills/{id} |
| `route:Internal\CodeQueryController@/code/file` | route | 房東側 |  | routes/api.php:/code/file |
| `route:Internal\CodeQueryController@/code/grep` | route | 房東側 |  | routes/api.php:/code/grep |
| `route:Internal\CodeQueryController@/code/tree` | route | 房東側 |  | routes/api.php:/code/tree |
| `route:Internal\ContractQueryController@/contracts` | route | 房東側 |  | routes/api.php:/contracts |
| `route:Internal\ContractQueryController@/contracts/{id}` | route | 房東側 |  | routes/api.php:/contracts/{id} |
| `route:Internal\ContractWriteController@/bills` | route | 房東側 |  | routes/api.php:/bills |
| `route:Internal\ContractWriteController@/contracts` | route | 房東側 |  | routes/api.php:/contracts |
| `route:Internal\EstateQueryController@/estates` | route | 房東側 |  | routes/api.php:/estates |
| `route:Internal\EstateQueryController@/estates/{id}` | route | 房東側 |  | routes/api.php:/estates/{id} |
| `route:Internal\EstateWriteController@/estates` | route | 房東側 |  | routes/api.php:/estates |
| `route:Internal\OpsController@/env` | route | 房東側 |  | routes/api.php:/env |
| `route:Internal\OpsController@/logs` | route | 房東側 |  | routes/api.php:/logs |
| `route:Internal\OpsController@/logs/{file}` | route | 房東側 |  | routes/api.php:/logs/{file} |
| `route:Internal\TeamQueryController@/teams` | route | 房東側 |  | routes/api.php:/teams |
| `route:InvoiceController@api.invoice.callback` | route | 房東側 |  | routes/api.php:api.invoice.callback |
| `route:IotController@/doorLockPasswords` | route | 房東側 |  | routes/web.php:/doorLockPasswords |
| `route:IotController@/manufacturerFetch` | route | 房東側 |  | routes/web.php:/manufacturerFetch |
| `route:IotController@/{deviceType}/list` | route | 房東側 |  | routes/web.php:/{deviceType}/list |
| `route:IotController@/{deviceType}/mode` | route | 房東側 |  | routes/web.php:/{deviceType}/mode |
| `route:IotController@/{deviceType}/rateLog` | route | 房東側 |  | routes/web.php:/{deviceType}/rateLog |
| `route:IotController@/{deviceType}/single` | route | 房東側 |  | routes/web.php:/{deviceType}/single |
| `route:IotController@/{deviceType}/stats` | route | 房東側 |  | routes/web.php:/{deviceType}/stats |
| `route:IotController@/{deviceType}/topUp` | route | 房東側 |  | routes/web.php:/{deviceType}/topUp |
| `route:IotController@/{deviceType}/topUpLog` | route | 房東側 |  | routes/web.php:/{deviceType}/topUpLog |
| `route:IotController@/{deviceType}/usage` | route | 房東側 |  | routes/web.php:/{deviceType}/usage |
| `route:IotController@/{deviceType}/{params?}` | route | 房東側 |  | routes/web.php:/{deviceType}/{params?} |
| `route:IotController@iot.update-state` | route | 房東側 |  | routes/web.php:iot.update-state |
| `route:IotController@iots.device` | route | 房東側 |  | routes/web.php:iots.device |
| `route:IotController@iots.estate` | route | 房東側 |  | routes/web.php:iots.estate |
| `route:IotController@iots.index` | route | 房東側 |  | routes/web.php:iots.index |
| `route:IotController@iots.lock-log` | route | 房東側 |  | routes/web.php:iots.lock-log |
| `route:IotController@iots.manufacturer` | route | 房東側 |  | routes/web.php:iots.manufacturer |
| `route:IotController@iots.passcode` | route | 房東側 |  | routes/web.php:iots.passcode |
| `route:IotController@iots.qr-code` | route | 房東側 |  | routes/web.php:iots.qr-code |
| `route:IotController@iots.save` | route | 房東側 |  | routes/web.php:iots.save |
| `route:IotController@iots.set-lock` | route | 房東側 |  | routes/web.php:iots.set-lock |
| `route:IotController@iots.set-poweron` | route | 房東側 |  | routes/web.php:iots.set-poweron |
| `route:IotController@iots.share-passcode` | route | 房東側 |  | routes/web.php:iots.share-passcode |
| `route:IotController@iots.stat` | route | 房東側 |  | routes/web.php:iots.stat |
| `route:Jgb3\AuthController@api.jgb3.get.token` | route | 房東側 |  | routes/api.php:api.jgb3.get.token |
| `route:Jgb3\ContractController@contracts.diyContract` | route | 房東側 |  | routes/web.php:contracts.diyContract |
| `route:Jgb3\Controller@/` | route | 房東側 |  | routes/web.php:/ |
| `route:LesseeController@/subscribe` | route | 房東側 |  | routes/api.php:/subscribe |
| `route:LesseeController@api.lessee.archive` | route | 房東側 |  | routes/api.php:api.lessee.archive |
| `route:LesseeController@api.lessee.batch.confirm` | route | 房東側 |  | routes/api.php:api.lessee.batch.confirm |
| `route:LesseeController@api.lessee.batch.import` | route | 房東側 |  | routes/api.php:api.lessee.batch.import |
| `route:LesseeController@api.lessee.batch.preview` | route | 房東側 |  | routes/api.php:api.lessee.batch.preview |
| `route:LesseeController@api.lessee.batch.sample` | route | 房東側 |  | routes/api.php:api.lessee.batch.sample |
| `route:LesseeController@api.lessee.bill.list` | route | 房東側 |  | routes/api.php:api.lessee.bill.list |
| `route:LesseeController@api.lessee.contract.list` | route | 房東側 |  | routes/api.php:api.lessee.contract.list |
| `route:LesseeController@api.lessee.create` | route | 房東側 |  | routes/api.php:api.lessee.create |
| `route:LesseeController@api.lessee.delete` | route | 房東側 |  | routes/api.php:api.lessee.delete |
| `route:LesseeController@api.lessee.list` | route | 房東側 |  | routes/api.php:api.lessee.list |
| `route:LesseeController@api.lessee.notify.invite` | route | 房東側 |  | routes/api.php:api.lessee.notify.invite |
| `route:LesseeController@api.lessee.repair.list` | route | 房東側 |  | routes/api.php:api.lessee.repair.list |
| `route:LesseeController@api.lessee.search` | route | 房東側 |  | routes/api.php:api.lessee.search |
| `route:LesseeController@api.lessee.status` | route | 房東側 |  | routes/api.php:api.lessee.status |
| `route:LesseeController@api.lessee.update` | route | 房東側 |  | routes/api.php:api.lessee.update |
| `route:LineController@lines.bot` | route | 房東側 |  | routes/web.php:lines.bot |
| `route:LineController@lines.liff` | route | 房東側 |  | routes/web.php:lines.liff |
| `route:LineController@lines.log` | route | 房東側 |  | routes/web.php:lines.log |
| `route:ListingController@/api2/listings/search` | route | 房東側 |  | routes/web.php:/api2/listings/search |
| `route:ListingController@/help/{any?}/{slug?}` | route | 房東側 |  | routes/web.php:/help/{any?}/{slug?} |
| `route:ListingController@/{any?}/{any2?}/{any3?}/{any4?}` | route | 房東側 |  | routes/web.php:/{any?}/{any2?}/{any3?}/{any4?} |
| `route:ListingController@getListingsData` | route | 房東側 |  | routes/web.php:getListingsData |
| `route:ListingController@indexs` | route | 房東側 |  | routes/web.php:indexs |
| `route:MarketingInviteController@marketing.invite` | route | 房東側 |  | routes/web.php:marketing.invite |
| `route:MondayStatisticController@/export` | route | 房東側 |  | routes/web.php:/export |
| `route:MondayStatisticController@/import` | route | 房東側 |  | routes/web.php:/import |
| `route:MondayStatisticController@/send-email` | route | 房東側 |  | routes/web.php:/send-email |
| `route:MondayStatisticController@/upload` | route | 房東側 |  | routes/web.php:/upload |
| `route:MondayStatisticController@/user-options` | route | 房東側 |  | routes/web.php:/user-options |
| `route:MondayStatisticController@/view` | route | 房東側 |  | routes/web.php:/view |
| `route:MondayStatisticController@/week-options` | route | 房東側 |  | routes/web.php:/week-options |
| `route:MondayStatisticController@/week-statistics` | route | 房東側 |  | routes/web.php:/week-statistics |
| `route:NotificationController@notifications.index` | route | 房東側 |  | routes/web.php:notifications.index |
| `route:NotificationController@notifications.navbar` | route | 房東側 |  | routes/web.php:notifications.navbar |
| `route:NthurcController@/list` | route | 房東側 |  | routes/web.php:/list |
| `route:NthurcController@/single` | route | 房東側 |  | routes/web.php:/single |
| `route:NthurcController@/tenantList` | route | 租客側 |  | routes/web.php:/tenantList |
| `route:NthurcController@cancelExtension` | route | 房東側 |  | routes/api.php:cancelExtension |
| `route:NthurcController@nthurc.tenantList.confirm` | route | 租客側 |  | routes/web.php:nthurc.tenantList.confirm |
| `route:NthurcController@nthurc.tenantList.preview` | route | 租客側 |  | routes/web.php:nthurc.tenantList.preview |
| `route:NthurcParkingController@/list` | route | 房東側 |  | routes/web.php:/list |
| `route:NthurcParkingController@/single` | route | 房東側 |  | routes/web.php:/single |
| `route:NthurcParkingController@/tenantList` | route | 租客側 |  | routes/web.php:/tenantList |
| `route:PaymentController@/rolePayments` | route | 房東側 |  | routes/api.php:/rolePayments |
| `route:PaymentController@payments.atm.received` | route | 房東側 |  | routes/web.php:payments.atm.received |
| `route:PaymentController@payments.credit_card.active` | route | 房東側 |  | routes/web.php:payments.credit_card.active |
| `route:PaymentController@payments.credit_card.refund` | route | 房東側 |  | routes/web.php:payments.credit_card.refund |
| `route:PaymentController@payments.notify` | route | 房東側 |  | routes/web.php:payments.notify |
| `route:PaymentController@payments.pay` | route | 房東側 |  | routes/web.php:payments.pay |
| `route:PaymentController@payments.query` | route | 房東側 |  | routes/web.php:payments.query |
| `route:PaymentController@payments.return` | route | 房東側 |  | routes/web.php:payments.return |
| `route:PromotionController@promotion.index` | route | 房東側 |  | routes/web.php:promotion.index |
| `route:QueueController@/api2/getBatchCode` | route | 房東側 |  | routes/web.php:/api2/getBatchCode |
| `route:QueueController@/api2/getBatchStatus` | route | 房東側 |  | routes/web.php:/api2/getBatchStatus |
| `route:RechargeAccountListController@api.recharge-accounts.destroy` | route | 房東側 |  | routes/api.php:api.recharge-accounts.destroy |
| `route:RechargeAccountListController@api.recharge-accounts.export` | route | 房東側 |  | routes/api.php:api.recharge-accounts.export |
| `route:RechargeAccountListController@api.recharge-accounts.generate` | route | 房東側 |  | routes/api.php:api.recharge-accounts.generate |
| `route:RechargeAccountListController@api.recharge-accounts.getEstate` | route | 房東側 |  | routes/api.php:api.recharge-accounts.getEstate |
| `route:RechargeAccountListController@api.recharge-accounts.history` | route | 房東側 |  | routes/api.php:api.recharge-accounts.history |
| `route:RechargeAccountListController@api.recharge-accounts.list` | route | 房東側 |  | routes/api.php:api.recharge-accounts.list |
| `route:RechargeAccountListController@api.recharge-accounts.store` | route | 房東側 |  | routes/api.php:api.recharge-accounts.store |
| `route:RechargeAccountListController@api.recharge-accounts.update` | route | 房東側 |  | routes/api.php:api.recharge-accounts.update |
| `route:ReferralController@referral.users.create` | route | 房東側 |  | routes/web.php:referral.users.create |
| `route:RepairController@/api2/getRepairList/{action?}` | route | 房東側 |  | routes/web.php:/api2/getRepairList/{action?} |
| `route:RepairController@/api2/repair/category_items` | route | 房東側 |  | routes/web.php:/api2/repair/category_items |
| `route:RepairController@/api2/repair/pick/{action?}` | route | 房東側 |  | routes/web.php:/api2/repair/pick/{action?} |
| `route:RepairController@/api2/repairItem/share/{id?}` | route | 房東側 |  | routes/web.php:/api2/repairItem/share/{id?} |
| `route:RepairController@/api2/repairItem/{action?}/{id?}` | route | 房東側 |  | routes/web.php:/api2/repairItem/{action?}/{id?} |
| `route:RepairController@/categories` | route | 房東側 |  | routes/web.php:/categories |
| `route:RepairController@/{type?}/{status?}/{role?}/{user?}/{action?}` | route | 房東側 |  | routes/web.php:/{type?}/{status?}/{role?}/{user?}/{action?} |
| `route:RepairController@repairs.pick` | route | 房東側 |  | routes/web.php:repairs.pick |
| `route:RepairController@repairs.show` | route | 房東側 |  | routes/web.php:repairs.show |
| `route:RoleController@/additions` | route | 房東側 |  | routes/api.php:/additions |
| `route:RoleController@/estates` | route | 房東側 |  | routes/api.php:/estates |
| `route:RoleController@/getCurrency` | route | 房東側 |  | routes/web.php:/getCurrency |
| `route:RoleController@/setCurrency` | route | 房東側 |  | routes/web.php:/setCurrency |
| `route:RoleController@api3.users.advance.getCycleDiscount` | route | 房東側 |  | routes/web.php:api3.users.advance.getCycleDiscount |
| `route:RoleController@api3.users.advance.setCycleDiscount` | route | 房東側 |  | routes/web.php:api3.users.advance.setCycleDiscount |
| `route:RoleController@feeCategories` | route | 房東側 |  | routes/api.php:feeCategories |
| `route:RoleController@info` | route | 房東側 |  | routes/web.php:info |
| `route:SinopacVaNotifyController@payments.sinopac.va_received` | route | 房東側 |  | routes/web.php:payments.sinopac.va_received |
| `route:SitemapController@sitemaps.estate_ad` | route | 房東側 |  | routes/web.php:sitemaps.estate_ad |
| `route:SitemapController@sitemaps.help_center` | route | 房東側 |  | routes/web.php:sitemaps.help_center |
| `route:SitemapController@sitemaps.index` | route | 房東側 |  | routes/web.php:sitemaps.index |
| `route:SitemapController@sitemaps.lessor_store` | route | 房東側 |  | routes/web.php:sitemaps.lessor_store |
| `route:SitemapController@sitemaps.matching` | route | 房東側 |  | routes/web.php:sitemaps.matching |
| `route:TaishinVaNotifyController@payments.taishin.va_received` | route | 房東側 |  | routes/web.php:payments.taishin.va_received |
| `route:TaskManagementController@/cycleOptions` | route | 房東側 |  | routes/web.php:/cycleOptions |
| `route:TaskManagementController@/scopeOptions` | route | 房東側 |  | routes/web.php:/scopeOptions |
| `route:TaskManagementController@/search` | route | 房東側 |  | routes/web.php:/search |
| `route:TaskManagementController@/typeOptions` | route | 房東側 |  | routes/web.php:/typeOptions |
| `route:TaskManagementController@/{id}/copy` | route | 房東側 |  | routes/web.php:/{id}/copy |
| `route:TaskManagementController@/{id}/detail` | route | 房東側 |  | routes/web.php:/{id}/detail |
| `route:TenantCreditRatingController@api.lessee.creditRating.overview` | route | 房東側 |  | routes/api.php:api.lessee.creditRating.overview |
| `route:TenantCreditRatingController@api.lessee.creditRating.store` | route | 房東側 |  | routes/api.php:api.lessee.creditRating.store |
| `route:TenantCreditRatingController@api.lessee.creditRating.update` | route | 房東側 |  | routes/api.php:api.lessee.creditRating.update |
| `route:ToolController@/cmd` | route | 房東側 |  | routes/web.php:/cmd |
| `route:ToolController@/recharge/{key}` | route | 房東側 |  | routes/web.php:/recharge/{key} |
| `route:ToolController@/short_url/{key}` | route | 房東側 |  | routes/web.php:/short_url/{key} |
| `route:ToolController@/template` | route | 房東側 |  | routes/web.php:/template |
| `route:ToolController@api.tools.imageProxy` | route | 房東側 |  | routes/web.php:api.tools.imageProxy |
| `route:ToolController@api.tools.unlock` | route | 房東側 |  | routes/web.php:api.tools.unlock |
| `route:ToolController@apis.image.proxy.redirect` | route | 房東側 |  | routes/web.php:apis.image.proxy.redirect |
| `route:ToolController@tools.beta` | route | 房東側 |  | routes/web.php:tools.beta |
| `route:ToolController@tools.checkpass` | route | 房東側 |  | routes/web.php:tools.checkpass |
| `route:ToolController@tools.login` | route | 房東側 |  | routes/web.php:tools.login |
| `route:ToolController@tools.loginRole` | route | 房東側 |  | routes/web.php:tools.loginRole |
| `route:UbotVaNotifyController@payments.ubot.va_received` | route | 房東側 |  | routes/web.php:payments.ubot.va_received |
| `route:UserController@/` | route | 房東側 |  | routes/web.php:/ |
| `route:UserController@/accountStatus` | route | 房東側 |  | routes/web.php:/accountStatus |
| `route:UserController@/add` | route | 房東側 |  | routes/web.php:/add |
| `route:UserController@/api2/setUserInfo/{action?}` | route | 房東側 |  | routes/web.php:/api2/setUserInfo/{action?} |
| `route:UserController@/api2/subscription/{action?}` | route | 房東側 |  | routes/web.php:/api2/subscription/{action?} |
| `route:UserController@/api2/subscriptionChose/{action?}` | route | 房東側 |  | routes/web.php:/api2/subscriptionChose/{action?} |
| `route:UserController@/api2/unsubscribe` | route | 房東側 |  | routes/web.php:/api2/unsubscribe |
| `route:UserController@/api2/user/index/{action?}` | route | 房東側 |  | routes/web.php:/api2/user/index/{action?} |
| `route:UserController@/cashBanks/{target?}` | route | 房東側 |  | routes/web.php:/cashBanks/{target?} |
| `route:UserController@/company/create` | route | 房東側 |  | routes/web.php:/company/create |
| `route:UserController@/company/delete` | route | 房東側 |  | routes/web.php:/company/delete |
| `route:UserController@/customAdditionalTermsTemplate` | route | 房東側 |  | routes/web.php:/customAdditionalTermsTemplate |
| `route:UserController@/customFeeItems/{action?}` | route | 房東側 |  | routes/web.php:/customFeeItems/{action?} |
| `route:UserController@/delete/{signingIdentityId}` | route | 房東側 |  | routes/web.php:/delete/{signingIdentityId} |
| `route:UserController@/info` | route | 房東側 |  | routes/web.php:/info |
| `route:UserController@/info/enable` | route | 房東側 |  | routes/web.php:/info/enable |
| `route:UserController@/info/update` | route | 房東側 |  | routes/web.php:/info/update |
| `route:UserController@/list` | route | 房東側 |  | routes/web.php:/list |
| `route:UserController@/list/{type}` | route | 房東側 |  | routes/web.php:/list/{type} |
| `route:UserController@/mailGroups` | route | 房東側 |  | routes/web.php:/mailGroups |
| `route:UserController@/mailGroups/update` | route | 房東側 |  | routes/web.php:/mailGroups/update |
| `route:UserController@/meta` | route | 房東側 |  | routes/web.php:/meta |
| `route:UserController@/publish` | route | 房東側 |  | routes/web.php:/publish |
| `route:UserController@/publish/save` | route | 房東側 |  | routes/web.php:/publish/save |
| `route:UserController@/recharge_accounts` | route | 房東側 |  | routes/web.php:/recharge_accounts |
| `route:UserController@/sendMultiTeamReport` | route | 房東側 |  | routes/web.php:/sendMultiTeamReport |
| `route:UserController@/sendReport` | route | 房東側 |  | routes/web.php:/sendReport |
| `route:UserController@/supportedVendors` | route | 房東側 |  | routes/web.php:/supportedVendors |
| `route:UserController@/tenants` | route | 租客側 |  | routes/web.php:/tenants |
| `route:UserController@/update` | route | 房東側 |  | routes/web.php:/update |
| `route:UserController@/update/{signingIdentityId}` | route | 房東側 |  | routes/web.php:/update/{signingIdentityId} |
| `route:UserController@/vendor` | route | 房東側 |  | routes/web.php:/vendor |
| `route:UserController@/vendor/{id}` | route | 房東側 |  | routes/web.php:/vendor/{id} |
| `route:UserController@/vendors` | route | 房東側 |  | routes/web.php:/vendors |
| `route:UserController@/wenzhongItemCodes` | route | 房東側 |  | routes/web.php:/wenzhongItemCodes |
| `route:UserController@/{memberType}` | route | 房東側 |  | routes/web.php:/{memberType} |
| `route:UserController@/{signingIdentityId}` | route | 房東側 |  | routes/web.php:/{signingIdentityId} |
| `route:UserController@api3.get.users.estates` | route | 房東側 |  | routes/web.php:api3.get.users.estates |
| `route:UserController@api3.get.users.infos` | route | 房東側 |  | routes/web.php:api3.get.users.infos |
| `route:UserController@api3.post.users.infos` | route | 房東側 |  | routes/web.php:api3.post.users.infos |
| `route:UserController@api3.users.index` | route | 房東側 |  | routes/web.php:api3.users.index |
| `route:UserController@getDashboardEmailLogs` | route | 房東側 |  | routes/web.php:getDashboardEmailLogs |
| `route:UserController@users.account` | route | 房東側 |  | routes/web.php:users.account |
| `route:UserController@users.add_merchant` | route | 房東側 |  | routes/web.php:users.add_merchant |
| `route:UserController@users.change.email` | route | 房東側 |  | routes/web.php:users.change.email |
| `route:UserController@users.coupon` | route | 房東側 |  | routes/web.php:users.coupon |
| `route:UserController@users.device` | route | 房東側 |  | routes/web.php:users.device |
| `route:UserController@users.help` | route | 房東側 |  | routes/web.php:users.help |
| `route:UserController@users.help-content` | route | 房東側 |  | routes/web.php:users.help-content |
| `route:UserController@users.lineChat` | route | 房東側 |  | routes/web.php:users.lineChat |
| `route:UserController@users.logout` | route | 房東側 |  | routes/web.php:users.logout |
| `route:UserController@users.messager` | route | 房東側 |  | routes/web.php:users.messager |
| `route:UserController@users.paymentLogs` | route | 房東側 |  | routes/web.php:users.paymentLogs |
| `route:UserController@users.resetDevicePassword` | route | 房東側 |  | routes/web.php:users.resetDevicePassword |
| `route:UserController@users.role` | route | 房東側 |  | routes/web.php:users.role |
| `route:UserController@users.roleEmail` | route | 房東側 |  | routes/web.php:users.roleEmail |
| `route:UserController@users.roleTenant` | route | 租客側 |  | routes/web.php:users.roleTenant |
| `route:UserController@users.safety` | route | 房東側 |  | routes/web.php:users.safety |
| `route:UserController@users.setLock` | route | 房東側 |  | routes/web.php:users.setLock |
| `route:UserController@users.team` | route | 房東側 |  | routes/web.php:users.team |
| `route:Vendors\ICashPayController@/getMemberRegisterUrl` | route | 房東側 |  | routes/web.php:/getMemberRegisterUrl |
| `route:Vendors\ICashPayController@api.icashpay.receiveICPMemberRegister` | route | 房東側 |  | routes/api.php:api.icashpay.receiveICPMemberRegister |
| `route:Vendors\ICashPayController@api.icashpay.receivePaymentInfo` | route | 房東側 |  | routes/api.php:api.icashpay.receivePaymentInfo |
| `route:Vendors\ICashPayController@api.icashpay.receiveTradeInfo` | route | 房東側 |  | routes/api.php:api.icashpay.receiveTradeInfo |
| `route:Vendors\ICashPayController@api.icashpay.redirectGetPaymentURL` | route | 房東側 |  | routes/api.php:api.icashpay.redirectGetPaymentURL |
| `route:Vendors\ICashPayController@api3.icashpay.redirectGetPaymentURL` | route | 房東側 |  | routes/web.php:api3.icashpay.redirectGetPaymentURL |
| `route:Vendors\ICashPayController@api3.icashpay.redirectTradeInfo` | route | 房東側 |  | routes/web.php:api3.icashpay.redirectTradeInfo |
| `route:\Rap2hpoutre\LaravelLogViewer\LogViewerController@admin.tools.laravel_log` | route | 房東側 |  | routes/web.php:admin.tools.laravel_log |

## 2. 正本細目標題（只列，不判定）

- `jgb/A/account-registration` 怎麼註冊帳號（Email 主路徑、驗證碼、SSO 第三方、租客從合約邀請註冊）
- `jgb/A/login-methods` 怎麼登入（Email／手機號碼／SSO 第三方、選擇房東或租客身分入口）
- `jgb/A/line-login-redirects-to-register` 用 LINE 快速登入卻被帶去註冊頁、登不進去（只認 LINE 註冊帳號、無事後綁定、改用帳密登入）
- `jgb/A/account-profile-settings` 帳號資訊在哪改、能改什麼（頭像、姓名、聯絡方式、偏好設定、簽約資訊與證件附件）
- `jgb/A/registered-vs-unregistered-tenant` 租客一定要註冊嗎？註冊租客與免註冊租客差在哪（登入、通知、帳單寄送、到帳作業）
- `jgb/A/email-case-sensitivity` Email 大小寫算不同帳號嗎（Email 為帳號識別、大小寫視為不同帳號）
- `jgb/A/verification-code-not-received` 收不到驗證碼（Email 驗證信或簡訊）怎麼排查（含改走 Email／SSO、聯繫客服要帶的資訊）
- `jgb/A/verification-code-invalid` 驗證碼一直輸入失敗（重發即換碼、三字母識別碼比對、5 分鐘效期、錯三次失效、120 秒冷卻）
- `jgb/A/forgot-password` 忘記密碼怎麼重設（Email 或簡訊擇一驗證、錯三次失效、密碼規則）
- `jgb/A/forgot-account-email` 忘記當初用哪個信箱註冊怎麼查（忘記帳號功能以手機驗證取得打星號提示、無綁手機找客服）
- `jgb/A/change-email-or-phone` 要換帳號的信箱或手機號碼怎麼辦（Email 唯讀走客服、手機未綁可自助綁定、已綁換號走申請書）
- `jgb/A/change-account-name` 註冊名字與證件不符要怎麼改（合約簽署前自改藍字帶入、簽署後鎖定走申請書同步）
- `jgb/A/data-change-request-form` 資料異動申請書怎麼申請（載明帳號識別、修改前後值、相關合約 ID，公司用印後寄客服信箱）
- `jgb/A/duplicate-accounts-merge` 不小心註冊了兩個帳號能不能合併（無自助合併、走客服後台，載明保留與處理的帳號）
- `jgb/A/already-registered-error` 註冊時顯示此帳號／手機已註冊怎麼辦（本人改登入或重設密碼、被他人占用走解綁申請）
- `jgb/A/tenant-login-cannot-see-data` 租客登入後看不到合約、帳單或電表怎麼排查（身分未切換、登入信箱與邀請信箱不一致、以合約查帳號狀態）
- `jgb/B/owner-report-collection-remit` 大房東報表與代收代付怎麼交代（月報內容、提供方式、排程寄送）
- `jgb/B/role-permission-granularity` 成員權限能不能細分、怎麼設（角色範本、自訂角色、模組層級、物件授權）
- `jgb/B/team-management-overview` 團隊管理模組做什麼
- `jgb/B/what-is-owner-landlord` 大房東是什麼
- `jgb/B/leasing-vs-management-business-model` 包租業與代管業是什麼、差在哪（定義、簽約對象、誰管理、房東該選哪個）
- `jgb/B/leasing-vs-management-liability-and-risk` 包租與代管的法律責任與風險由誰承擔
- `jgb/B/business-type-fee-model` 包租與代管怎麼收費、業者怎麼賺錢（租差、抽成、管理費範疇、政府補貼）
- `jgb/B/business-type-setting-and-system-differences` 團隊業態（包租／代管）在系統裡怎麼設、差在哪（合約模板、發票主體、差額發票）
- `jgb/B/leasing-management-license-and-staff-qualification` 如何成為政府許可的包租代管業者與合格包管人員
- `jgb/B/add-team-member` 怎麼新增團隊成員（需先註冊、加入後要指派角色、加了看不到怎麼辦）
- `jgb/B/who-has-permission-lookup` 怎麼查團隊裡誰有某個操作權限
- `jgb/B/remove-team-member-data-retention` 移除團隊成員後他建的資料會怎樣
- `jgb/B/account-in-multiple-teams` 一個帳號可以加入多個團隊嗎、權限怎麼算
- `jgb/B/change-team-principal-or-phone` 怎麼變更團隊主要負責人或綁定手機（異動單）
- `jgb/B/feature-not-visible-troubleshooting` 找不到某功能或無法操作的可能原因
- `jgb/B/add-owner-landlord-and-access` 怎麼新增大房東並設定他能看的物件範圍
- `jgb/B/owner-landlord-contact-book-import-export` 大房東聯絡簿怎麼批次匯入匯出
- `jgb/C/property-management-overview` 房源管理模組做什麼（含自訂狀態標籤）
- `jgb/C/community-batch-create` 社區建立與批次新增物件
- `jgb/C/property-status-meaning` 物件狀態（未刊登／刊登中／洽談中／合約中）是什麼意思
- `jgb/C/rental-storefront-vr` 招租店舖與 VR 看屋
- `jgb/C/community-setup-and-property-binding` 社區建立、編輯與物件歸戶（含公共區域物件、社宅強制綁定）
- `jgb/C/property-batch-import` 物件批次匯入：範本、表格填寫與上傳失敗
- `jgb/C/property-listing-conditions` 物件要怎麼刊登上架、刊登需要什麼條件
- `jgb/C/property-unlisting` 物件怎麼下架、為什麼突然全部下架
- `jgb/C/property-edit-vs-publish` 編輯物件與刊登物件差在哪、為什麼修改沒存到
- `jgb/C/property-add-blocked` 為什麼不能新增物件
- `jgb/C/public-display-address` 對外顯示地址改了為什麼後台還是完整地址
- `jgb/C/storefront-entry-share` 招租店舖入口在哪、怎麼分享、為什麼物件沒出現
- `jgb/C/community-public-page` 社區公開頁面是什麼、能拿來做什麼
- `jgb/C/property-vr-tour` 物件 VR 虛擬導覽怎麼綁、費用與拍攝找誰
- `jgb/C/property-custom-tags` 物件自訂標籤怎麼建、怎麼用來篩選
- `jgb/C/property-advanced-search` 物件列表進階搜尋怎麼用
- `jgb/C/occupancy-rate-calculation` 首頁即時物件出租率怎麼算、已出租數字從哪來
- `jgb/C/community-facilities-and-hours` 社區有哪些公共設施、開放時間、費用與變更通知
- `jgb/C/community-facility-usage-rules` 公共設施使用規範：權利、義務、安全規範與違規後果
- `jgb/C/community-garbage-disposal` 社區垃圾分類、回收時間、大型廢棄物與洗衣烘衣使用規範
- `jgb/C/community-facility-disputes` 公共設施損壞責任、使用爭議處理與責任保險
- `jgb/C/community-services-and-events` 社區生活服務與活動（社區活動、包裹代收、社宅社區服務）
- `jgb/D/contract-esign-flow` 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用）
- `jgb/D/contract-batch-renewal` 續約能不能批次處理（含快速日期設定、紙本上傳、通知分流）
- `jgb/D/contract-history-retention` 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程）
- `jgb/D/contract-modify-after-sign` 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查）
- `jgb/D/contract-templates` 合約範本有哪些可以選（含內文隨內政部新制更新）
- `jgb/D/lease-expiry-followup-scope` 合約到期追問可答範圍與到期提醒（導向續約面向）
- `jgb/D/sublease-vs-management-contract` 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整）
- `jgb/D/contract-create-entry-and-prereq` 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口
- `jgb/D/contract-copy` 合約複製快速建立相似合約
- `jgb/D/upload-existing-contract` 上傳既存（紙本）合約：適用情境、效力、入口、檔案上限
- `jgb/D/contract-attachments-notes-limits` 合約附件上傳、備註 50 行與補充條款限制
- `jgb/D/contract-pdf-download` 合約相關 PDF 下載（合約書、摘要、點交／點退清單、提前解約文件）
- `jgb/D/signer-identity-and-seal` 簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法
- `jgb/D/contract-send-invite` 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整）
- `jgb/D/esign-invite-expiry` 簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長
- `jgb/D/esign-troubleshooting` 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆
- `jgb/D/tenant-sign-steps` 租客收到簽約邀請後的簽署步驟（租客視角）
- `jgb/D/esign-legal-validity` 電子合約法律效力、簽章認證與 72 小時審閱期
- `jgb/D/contract-status-overview` 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀
- `jgb/D/contract-lookup` 查詢合約資訊：以合約編號／物件名稱查、不能用租客姓名反查、租客資料卡
- `jgb/D/contract-filter-by-state` 依合約狀態篩選物件（點交點退、待退押金、本月到期、無合約）
- `jgb/D/contract-data-change-form` 資料異動申請書的填寫與提交
- `jgb/D/contract-snapshot-independence` 合約快照原則：物件資料、租客聯絡方式或姓名事後修改，合約與通知都不連動
- `jgb/D/tenant-change-new-contract` 更換承租人／退房後換新租客：只能新建合約，舊約收尾與物件重刊登
- `jgb/D/contract-cancel-delete` 合約刪除、取消、作廢的條件與取消 vs 歷史合約差異
- `jgb/D/handover-checkin` 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發
- `jgb/D/return-checkout` 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議
- `jgb/D/handover-return-cancel-invite` 取消／收回點交或點退邀請，為什麼不能取消
- `jgb/D/lease-end-checkout-overview` 租客要退租了接下來怎麼做：到期收尾步驟總覽（點退→帳單→封存→轉歷史）與退租跑到哪一步
- `jgb/D/early-termination-flow` 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約
- `jgb/D/early-termination-penalty` 提前解約違約金怎麼算（預告期）、由誰付
- `jgb/D/early-termination-aftermath` 提前解約生效後：何時可點退、違約金與押金一併結算、之後還要處理什麼
- `jgb/D/renewal-flow` 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限
- `jgb/D/renewal-vs-new-contract` 系統續約 vs 重建新約的取捨（條件變更、租屋補助審核）
- `jgb/D/renewal-history-and-addendum` 續約後原合約去哪了：續約歷史、增補文件分頁、有沒有下一份約
- `jgb/D/delegation-vs-lease-contract` 委託約與租賃約的差別（系統分開管理）
- `jgb/D/delegation-contract-flow` 委託合約的建立簽署、提前終止與 PDF 下載
- `jgb/D/delegation-contract-terms-general` 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律
- `jgb/D/delegation-contract-change-termination` 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決
- `jgb/D/deposit-setting-and-refund-system` 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算）
- `jgb/D/deposit-legal-limits` 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租
- `jgb/D/deposit-deduction-refund` 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理
- `jgb/D/tenant-pet-clauses` 租約中的寵物押金與飼養寵物費用
- `jgb/D/tenant-rental-insurance` 租屋相關保險：租屋保險費用、租客設備投保、押金投保
- `jgb/D/move-in-inspection` 入住注意事項與傢俱清點
- `jgb/D/tenant-move-out-obligations` 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出
- `jgb/D/lease-termination-notice-rules` 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤）
- `jgb/D/breach-penalty-rules` 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留
- `jgb/D/tenant-renewal-and-extension-rights` 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助
- `jgb/D/lease-clauses-interpretation` 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議）
- `jgb/D/equipment-usage-under-lease` 租約中的設備與公共設備使用規範
- `jgb/D/household-registration-under-lease` 租屋期間戶籍遷移與居住證明
- `jgb/D/sublease-and-shared-lease-terms` 轉租與分租的租約條款與押金處理
- `jgb/D/social-housing-lease` 社會住宅租約與一般租約的差異、期限與終止
- `jgb/D/lease-notarization` 租約公證：是什麼、去哪辦、費用、對房東房客的保障、與租補關係、公證合約如何上傳
- `jgb/E/billing-overview` 帳務管理模組做什麼
- `jgb/E/bill-contents-extra-fees` 帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整）
- `jgb/E/bill-format-customize` 帳單版面、收據版式與收訖章能不能自訂
- `jgb/E/credit-card-rent-payment` 租客能不能用信用卡繳房租（限藍新、流程與限制）
- `jgb/E/dunning-draft-not-auto-send` 催繳草稿不可一鍵發送給租客
- `jgb/E/dunning-draft-template-tone-late-fee` 催繳草稿的生成規則（模板、語氣分級與滯納金提及）
- `jgb/E/einvoice-issuing` 電子發票何時開、自動開立設定、載具類型與一物件一發票
- `jgb/E/overdue-bill-followup-scope` 逾期帳單追問可答範圍（依帳單編號查狀態、金額、逾期明細）
- `jgb/E/overdue-reminder-late-fee` 租客逾期未繳怎麼辦（繳費提醒、催繳通知條件、逾期標示與訂閱通知）
- `jgb/E/payment-gateway-options` 金流廠商差別、支援付款方式與申請條件
- `jgb/E/utility-split-calculation` 水電與公共費用怎麼分算（依合約）
- `jgb/E/virtual-account-prepaid` 固定虛擬帳號與儲值金抵扣是什麼、跟一般虛擬帳號差在哪
- `jgb/E/rent-amount-calculation` 租金金額怎麼算（以合約租金快照為準、不足月按比例）
- `jgb/E/utility-meter-billing-and-reading` 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算）
- `jgb/E/management-fee` 管理費是什麼、用途與怎麼算
- `jgb/E/periodic-bill-generation` 週期帳單何時產生、三種建立方式與續約／補簽起算
- `jgb/E/bill-scheduled-auto-send` 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿）
- `jgb/E/bill-send-failure` 帳單為什麼發不出去（狀態、金額、度數未填、租客聯絡方式未驗證）
- `jgb/E/bill-recall-cancel` 帳單發出去想收回、取消或設失效（可用狀態與繳費資訊斷開）
- `jgb/E/bill-archive-after-termination` 提前終止／退租後多產生的帳單要封存、封存後怎麼退回
- `jgb/E/manual-bill-creation` 手動新增帳單、負值退款、Excel 批次匯入與補建紀錄
- `jgb/E/checkout-bill-settlement` 點退帳單怎麼算（未結費用、賠償、押金互抵、多退少補）
- `jgb/E/bill-status-reconciliation` 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳
- `jgb/E/paid-but-status-not-updated` 租客說繳了但錢還沒進來／帳單卡在待對帳
- `jgb/E/cash-bank-account-collection` 現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳
- `jgb/E/payment-gateway-setup` 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試）
- `jgb/E/payment-fees-and-sms` 金流手續費誰負擔、費率多少與帳單簡訊是否收費
- `jgb/E/tenant-payment-methods` 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層）
- `jgb/E/tenant-online-payment-steps` 租客線上繳費操作步驟（信用卡、虛擬 ATM）
- `jgb/E/tenant-view-bills` 租客在哪裡看帳單、繳費狀態與付款入口
- `jgb/E/tenant-cannot-see-bill` 租客說看不到帳單（可見三條件與信箱錯配）
- `jgb/E/bill-reports-export` 帳單報表匯出、統計圖表與儀表板
- `jgb/E/credit-card-auto-debit` 信用卡自動扣款授權設定與扣款失敗處理
- `jgb/E/virtual-account-transfer` 虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易
- `jgb/E/payment-failure-troubleshooting` 租客繳不了費／轉帳或刷卡一直失敗怎麼排查
- `jgb/E/payment-amount-mismatch` 付款金額不符、重複轉帳、多繳少繳怎麼處理
- `jgb/E/convenience-store-payment` 超商代碼／條碼繳費流程與入帳撥付時程
- `jgb/E/fixed-virtual-account-management` 固定虛擬帳號怎麼開通設定、入帳沖銷與餘額歷程查詢
- `jgb/E/prepaid-meter-topup-billing` 儲值電表的儲值帳單、入帳與電費預付收取
- `jgb/E/late-fee-calculation` 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額）
- `jgb/E/invoice-not-issued-troubleshooting` 發票為什麼還沒開、顯示已開卻沒號碼的排查
- `jgb/E/invoice-void-reissue` 發票開錯了怎麼作廢、補開與作廢不了
- `jgb/E/differential-invoice` 差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出）
- `jgb/E/deposit-imputed-interest` 押金設算息怎麼算、利率設定與年度一次限制
- `jgb/E/landlord-owner-bills` 大房東帳單（代收代付）怎麼看與建立
- `jgb/E/bill-receipt-pdf` 帳單收據 PDF 下載與繳費證明
- `jgb/E/rent-collection-agent-vs-direct` 包租代管租金代收與房東直收有什麼差別
- `jgb/E/rent-market-discount-tax` 租金行情、折扣條件與公益出租人減稅（租客視角）
- `jgb/F/repair-progress-followup-scope` 修繕進度追問可答範圍與查詢方式
- `jgb/F/repair-system` 線上報修與進度追蹤
- `jgb/F/repair-ticket-after-submit` 確認送出後的單如何處理
- `jgb/F/repair-ticket-mid-flow-cancel` 報修流程中途取消的規則
- `jgb/F/repair-ticket-no-lease` 代開單時的租約查詢身分與空屋／無租約物件開單規則
- `jgb/F/repair-ticket-open-and-confirm` 開修繕單基本流程與確認機制（拍照進場／文字口述）
- `jgb/F/repair-ticket-photo-count-limit` 修繕辨識與附件的照片張數限制
- `jgb/F/repair-ticket-photo-recognition-uncertain` 照片辨識信心不足或看不出損壞時的處理
- `jgb/F/repair-ticket-reclassify` 確認卡上修改辨識結果的規則
- `jgb/F/repair-ticket-submit-failure` 建單失敗時的處理與重試規則
- `jgb/F/repair-ticket-urgency-judgment` 修繕單急迫程度的判斷來源與值域
- `jgb/F/repair-responsibility-landlord-vs-tenant` 房屋修繕責任劃分（房東與租客各負責什麼、費用誰出）
- `jgb/F/common-equipment-maintenance-responsibility` 公共設備的維護、損壞、更新、費用與檢查紀錄責任
- `jgb/F/tenant-equipment-maintenance-responsibility` 租客設備的使用、維護、損壞賠償、更新與費用責任
- `jgb/F/tenant-repair-notification-duty` 租客發現需修繕時的通知義務與要求合理期限修繕的權利
- `jgb/F/tenant-emergency-self-repair` 緊急情況下租客自行修繕的條件、事後通知與費用報銷
- `jgb/F/emergency-repair-flag-and-handling` 緊急修繕的標記、優先處理與回應時效
- `jgb/F/neighbor-leak-responsibility` 鄰居漏水的修繕責任與處理
- `jgb/F/repair-responsibility-dispute` 修繕責任有爭議時的處理
- `jgb/F/repair-warranty-period` 修繕後的保固期
- `jgb/F/social-housing-repair-responsibility` 社會住宅的維修責任
- `jgb/F/repair-flow-stages` 修繕流程六階段與各狀態意義
- `jgb/F/repair-cost-recording-and-settlement` 修繕費用的記錄、分擔與結單自動產生修繕費帳單
- `jgb/F/repair-request-how-to-submit` 在系統提出修繕申請的步驟與需填資料（租客／房東）
- `jgb/F/repair-dispatch-and-close` 業者受理報修、安排廠商、完工登錄到結單封存的操作
- `jgb/F/repair-multiple-items-one-ticket` 多個品項是否分開報修（合併在一張報修單）
- `jgb/G/meter-item-followup-scope` 電錶項目追問可答範圍（餘額、可用度數、供電、低電量警報）
- `jgb/G/smart-meter-lock-iot` 智慧電錶與門鎖整合（售前）
- `jgb/G/meter-vendor-binding` 電表串接：綁定設備廠商帳號與裝置自動同步（含已被綁定處理）
- `jgb/G/meter-device-management` 智慧電錶裝置管理：命名、供電／斷電、綁定物件、查看用電度數
- `jgb/G/tenant-meter-visibility` 租客端看到即時電表與自行儲值的前提設定
- `jgb/G/meter-data-sync-gap` 電錶實體度數與 JGB 顯示不同／長期不更新
- `jgb/G/iot-offline-troubleshooting` IoT 設備（門鎖／電表）無法連線的排查順序
- `jgb/G/smart-lock-functions` 智慧門鎖功能：租客密碼、QR Code、開門紀錄與密碼管理
- `jgb/G/smart-lock-share-password` 分享門鎖密碼：訪客／維修／清潔人員臨時存取
- `jgb/G/smart-lock-password-rules` IoT 設定：門鎖預設密碼規則與連結起始日的生效範圍
- `jgb/G/smart-lock-hardware-vendor` 門鎖硬體功能（悠遊卡／磁扣／電池／音量）屬廠商範疇
- `jgb/G/smart-lock-failure` 門鎖 QR Code／密碼失靈開不了門的排查
- `jgb/I/competitor-comparison` 跟 Bananas、屋我也差在哪
- `jgb/I/competitor-neutrality` 會評論競爭對手嗎
- `jgb/I/dashboard-overview` 首頁儀表板顯示哪些數據
- `jgb/I/data-migration` 舊系統資料能否匯入（可匯入範圍、不支援項目與批次匯入做法）
- `jgb/I/free-trial` 可以免費試用嗎
- `jgb/I/individual-landlord-scale-fit` 個人房東（約 10～30 戶）適配與建議做法
- `jgb/I/pricing-plans` 怎麼收費與方案分級差異
- `jgb/I/product-overview` 系統總覽、能解決什麼問題與適不適合我
- `jgb/I/property-quota-limit` 方案物件額度上限與用滿怎麼辦
- `jgb/I/subscription-change-renewal` 升級、變更、續約與取消訂閱（含付款紀錄）
- `jgb/I/subscription-payment-failure` 訂閱扣款失敗：方案失效、物件下架與恢復
- `jgb/I/team-company-fit` 公司或包租代管團隊適合嗎
- `jgb/I/why-choose-jgb` 為什麼選金箍棒
- `jgb/I/onboarding-tutorial-index` 房東新手教學總覽（從哪開始、各篇教學有哪些）
