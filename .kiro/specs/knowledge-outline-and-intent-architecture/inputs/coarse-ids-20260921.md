# 粗目 id 凍結表（57 個）— 2026-09-21

> 為什麼有這份：粗目 id 是正本的永久錨點（`## <標題> {#<架字母>-<slug>}`），正則只允許 ASCII `[a-z0-9-]+`，而粗目標題是中文長句 ⇒ **⛔ 無法機械轉寫**。本表是 id 的**唯一來源**，`drafts_to_canon.py` 依標題逐字查表，查不到就大聲失敗、⛔ 不自行造 slug。
> 對應規則：一個標題一個 id；id 全域唯一；首字母＝所在架。標題以 `runs/outline-20260920/drafts-<架>.json` 的 `coarse` 欄為準（含 `⇄ 由 X 移入` 字樣者，查表時**先去掉** `⇄ …` 後綴再比對）。
> ⛔ id 一經生成正本即不可改（改 id ＝ 換一條細目的家）；要改請在生成前改本表。

| # | 架 | 粗目標題 | 粗目 id | 細目數 |
|---|---|---|---|---|
| 1 | A | 註冊帳號（Email／SSO、驗證碼、手機綁定） | `A-registration` | 12 |
| 2 | A | 登入 | `A-login` | 11 |
| 3 | A | 忘記帳號、忘記密碼 | `A-account-recovery` | 4 |
| 4 | A | 會員中心首頁 | `A-member-home` | 7 |
| 5 | A | 帳號資訊 | `A-account-profile` | 10 |
| 6 | A | 簽約資訊（證件、身分證號、戶籍地址；公司統編與大小章） | `A-signer-info` | 8 |
| 7 | A | 通知中心 | `A-notification-center` | 7 |
| 8 | A | 通知收件設定與發送報表（通知收件信箱最多再加 3 組） | `A-notification-settings` | 4 |
| 9 | B | 團隊資訊（團隊名稱、介紹、首頁、廣告頁聯絡資訊、刪除團隊） | `B-team-profile` | 12 |
| 10 | B | 成員列表（邀請、角色、成員名下資料） | `B-member-list` | 13 |
| 11 | B | 大房東列表與授權物件 | `B-biglandlord-list` | 12 |
| 12 | B | 大房東報表 | `B-biglandlord-report` | 3 |
| 13 | B | 大房東對帳表 | `B-biglandlord-sheet` | 7 |
| 14 | B | 進階設定（費用項目、租金折扣、滯納金、補充條款範本、自訂標籤、時區語系；介面路徑「團隊管理 > 進階設定」） | `B-advanced-settings` | 18 |
| 15 | B | 租客列表（當前租客／封存、準時繳租率、信用評價） | `B-tenant-list` | 14 |
| 16 | C | 社區列表與建立 | `C-community-list` | 8 |
| 17 | C | 社區資料編輯（基本資料、照片與描述、介紹與交通） | `C-community-edit` | 6 |
| 18 | C | 社區底下的物件（管理端清單：總覽／招租／買賣切換、編輯社區、預覽廣告頁） | `C-community-estates` | 5 |
| 19 | C | 社區公開頁（社區詳情、社區總表） | `C-community-public-page` | 4 |
| 20 | C | 物件綁定社區的導引（2022/05 社區功能上線時的強制綁定流程，限團隊擁有者） | `C-community-force-binding` | 5 |
| 21 | C | 物件列表與篩選 | `C-estate-list` | 10 |
| 22 | C | 物件資料編輯（基本資料、建物謄本、附設傢俱、標題與照片、物件介紹、720 VR） | `C-estate-edit` | 13 |
| 23 | C | 招租刊登（招租詳情、刊登主資訊、核實訊息＝租賃住宅條例的產權與違建核實） | `C-rent-listing` | 8 |
| 24 | C | 物件儀表板（招租表現、合約歷程、帳務收支、修繕紀錄、附件清單、房東流水帳、合約附件、物件記事本、每月報表、每月對帳單；入口直接轉到招租表現） | `C-estate-dashboard` | 9 |
| 25 | C | 單一物件廣告頁（招租） | `C-estate-public-page` | 8 |
| 26 | C | 團隊招租店鋪（對外首頁、多團隊招募頁、banner 與篩選） | `C-team-storefront` | 5 |
| 27 | D | 合約列表與搜尋 | `D-contract-list` | 10 |
| 28 | D | 建立與編輯一般合約（13 個分頁：基本資料、基本條件、租金費用、租金調幅設定、稅與發票、帳單設定、收款方式、附設傢俱、現況補充、出租方基本資料、建物謄本、合約附件、補充條款） | `D-contract-edit-general` | 21 |
| 29 | D | 建立與編輯社宅合約（房東基本資料與授權書、租客資格與證明文件、家庭與所得檢核、補貼修繕項目、照片檢核、點交，其餘分頁同一般） | `D-contract-edit-social-housing` | 19 |
| 30 | D | 簽約與合約檢視 | `D-contract-sign-view` | 8 |
| 31 | D | 點交 | `D-move-in` | 7 |
| 32 | D | 點退 | `D-move-out` | 6 |
| 33 | D | 續約 | `D-renew` | 7 |
| 34 | D | 提前解約 | `D-early-termination` | 5 |
| 35 | D | 租約公證（公證分頁與公證服務） | `D-notary` | 3 |
| 36 | D | 委託合約（列表、建立編輯、檢視） | `D-entrust-contract` | 11 |
| 37 | E | 帳單列表與帳單狀態 | `E-bill-list` | 24 |
| 38 | E | 建立與編輯帳單（單筆、批次、週期批次） | `E-bill-create-edit` | 14 |
| 39 | E | 帳單統計與報表 | `E-bill-stats` | 7 |
| 40 | E | 社宅報表 | `E-social-housing-report` | 5 |
| 41 | E | 差額發票（群組、底租、社區層開關） | `E-balance-invoice` | 9 |
| 42 | E | 固定虛擬帳號管理（租客虛擬帳號、餘額、歷程） | `E-virtual-account` | 10 |
| 43 | E | 線上金流收款帳號開通（藍新、中信；入口在「線上智能整合收款」頁的「開通帳號」） | `E-payment-onboarding` | 8 |
| 44 | F | 修繕單列表與狀態（申請修繕、安排修繕、完成修繕、結單、封存） | `F-repair-list` | 11 |
| 45 | F | 報修申請流程 | `F-repair-apply` | 8 |
| 46 | F | 修繕單編輯 | `F-repair-edit` | 10 |
| 47 | F | 修繕單分享頁 | `F-repair-share` | 4 |
| 48 | G | 電表列表與單一電表 | `G-power-meter` | 17 |
| 49 | G | 裝置頁（門鎖、攝影機、小白盒） | `G-device-page` | 7 |
| 50 | G | 遠端解鎖（輸入解鎖密碼開門） | `G-remote-unlock` | 2 |
| 51 | H | 幫助中心（分類、文章、搜尋） | `H-help-center` | 5 |
| 52 | I | 方案、價格與免費試用 | `I-pricing` | 11 |
| 53 | I | 訂閱、付款與訂單 | `I-subscription-payment` | 20 |
| 54 | I | 預約 demo | `I-demo-booking` | 4 |
| 55 | I | 控制台（設定、通知信範本、自動化任務） | `I-control-panel` | 9 |
| 56 | I | 官網首頁 | `I-marketing-home` | 7 |
| 57 | I | 中華電信雲市集訂單頁 | `I-hicloud-order` | 3 |

合計 57 個粗目、515 條細目（A 63／B 79／C 81／D 97／E 77／F 33／G 26／H 5／I 54）。
