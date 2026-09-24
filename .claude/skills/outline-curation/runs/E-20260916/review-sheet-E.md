# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/E/bill-contents-extra-fees` | 帳單內容與臨時加收費用 | `jgb/E/bill-contents-extra-fees` | 帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整） | merge | E/E/E | |
| 2 | `tmp:canon:jgb/E/bill-format-customize` | 帳單版面能不能自訂 | `jgb/E/bill-format-customize` | 帳單版面、收據版式與收訖章能不能自訂 | merge | E/E/E | |
| 3 | `tmp:canon:jgb/E/billing-overview` | 帳務管理模組做什麼 | `jgb/E/billing-overview` | 帳務管理模組做什麼 | keep | E/E/E | |
| 4 | `tmp:canon:jgb/E/credit-card-rent-payment` | 租客能不能用信用卡繳房租 | `jgb/E/credit-card-rent-payment` | 租客能不能用信用卡繳房租（限藍新、流程與限制） | merge | E/E/E | |
| 5 | `tmp:canon:jgb/E/dunning-draft-not-auto-send` | 催繳草稿不可一鍵發送給租客 | `jgb/E/dunning-draft-not-auto-send` | 催繳草稿不可一鍵發送給租客 | keep | E/E/E | |
| 6 | `tmp:canon:jgb/E/dunning-draft-template-tone-late-fee` | 催繳草稿的生成規則（模板、語氣分級與滯納金提及） | `jgb/E/dunning-draft-template-tone-late-fee` | 催繳草稿的生成規則（模板、語氣分級與滯納金提及） | keep | E/E/E | |
| 7 | `tmp:canon:jgb/E/einvoice-issuing` | 電子發票能不能自動開、載具怎麼用 | `jgb/E/einvoice-issuing` | 電子發票何時開、自動開立設定、載具類型與一物件一發票 | merge | E/E/E | |
| 8 | `tmp:canon:jgb/E/overdue-bill-followup-scope` | 逾期帳單追問可答範圍 | `jgb/E/overdue-bill-followup-scope` | 逾期帳單追問可答範圍（依帳單編號查狀態、金額、逾期明細） | merge | E/E/E | |
| 9 | `tmp:canon:jgb/E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（含繳費提醒通知） | `jgb/E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（繳費提醒、催繳通知條件、逾期標示與訂閱通知） | merge | E/E/E | |
| 10 | `tmp:canon:jgb/E/payment-gateway-options` | 金流廠商差別與申請條件 | `jgb/E/payment-gateway-options` | 金流廠商差別、支援付款方式與申請條件 | merge | E/E/E | |
| 11 | `tmp:canon:jgb/E/utility-split-calculation` | 水電費怎麼分算 | `jgb/E/utility-split-calculation` | 水電與公共費用怎麼分算（依合約） | merge | E/E/E | |
| 12 | `tmp:canon:jgb/E/virtual-account-prepaid` | 固定虛擬帳號與儲值金抵扣 | `jgb/E/virtual-account-prepaid` | 固定虛擬帳號與儲值金抵扣是什麼、跟一般虛擬帳號差在哪 | merge | E/E/E | |
| 13 | `tmp:draft:1` | 房東教學05：收款設置篇 | `jgb/E/bill-format-customize` | 帳單版面、收據版式與收訖章能不能自訂 | split | E/E/E | |
| 14 | `tmp:draft:1` | 房東教學05：收款設置篇 | `jgb/E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | split | E/E/E | |
| 15 | `tmp:draft:1` | 房東教學05：收款設置篇 | `jgb/E/cash-bank-account-collection` | 現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳 | split | E/E/E | |
| 16 | `tmp:draft:1` | 房東教學05：收款設置篇 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | split | E/E/E | |
| 17 | `tmp:draft:10` | 當租客完成匯款時，要如何通知並請房東確認到帳？ | `jgb/E/cash-bank-account-collection` | 現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳 | new | E/E/E | |
| 18 | `tmp:draft:11` | 房東如何確認向租客收租的帳單及款項細節？ | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 19 | `tmp:draft:12` | 房東及租客要如何辨認「逾期帳單」? | `jgb/E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（繳費提醒、催繳通知條件、逾期標示與訂閱通知） | merge | E/E/E | |
| 20 | `tmp:draft:13` | 「線上金流」&「現金/轉帳匯款」收款的最大差異是什麼？ | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 21 | `tmp:draft:14` | 租客該如何追蹤現金/轉帳匯款完成的帳單後續？ | `jgb/E/cash-bank-account-collection` | 現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳 | new | E/E/E | |
| 22 | `tmp:draft:2` | 帳務篇：新增單一帳單 | `jgb/E/manual-bill-creation` | 手動新增帳單、負值退款、Excel 批次匯入與補建紀錄 | new | E/E/E | |
| 23 | `tmp:draft:3` | 帳務篇：批次發送帳單 | `jgb/E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | new | E/E/E | |
| 24 | `tmp:draft:4` | 既存合約的歷史帳單如何移至已到帳 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 25 | `tmp:draft:5` | 租客線上與現金之繳費方式 | `jgb/E/tenant-online-payment-steps` | 租客線上繳費操作步驟（信用卡、虛擬 ATM） | new | E/E/E | |
| 26 | `tmp:draft:6` | 租客繳費方式（藍新ATM） | `jgb/E/tenant-online-payment-steps` | 租客線上繳費操作步驟（信用卡、虛擬 ATM） | new | E/E/E | |
| 27 | `tmp:draft:7` | 租客繳費方式（國泰ATM） | `jgb/E/tenant-online-payment-steps` | 租客線上繳費操作步驟（信用卡、虛擬 ATM） | new | E/E/E | |
| 28 | `tmp:draft:8` | 租客繳費方式（線下付款） | `jgb/E/cash-bank-account-collection` | 現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳 | new | E/E/E | |
| 29 | `tmp:draft:9` | 租客如何即時確認繳費帳單狀況？ | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 30 | `tmp:kb:2909` | 租金行情參考 | `jgb/E/rent-market-discount-tax` | 租金行情、折扣條件與公益出租人減稅（租客視角） | new | ⚠️ E/E/? | |
| 31 | `tmp:kb:2910` | 管理費 | `jgb/E/management-fee` | 管理費是什麼、用途與怎麼算 | new | E/E/E | |
| 32 | `tmp:kb:2911` | 公共費用分攤 | `jgb/E/utility-split-calculation` | 水電與公共費用怎麼分算（依合約） | merge | E/E/E | |
| 33 | `tmp:kb:2913` | 租金多繳溢繳退還處理 | `jgb/E/payment-amount-mismatch` | 付款金額不符、重複轉帳、多繳少繳怎麼處理 | new | E/E/E | |
| 34 | `tmp:kb:2918` | 租金支付期限 | `jgb/E/tenant-payment-methods` | 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層） | new | E/E/E | |
| 35 | `tmp:kb:2920` | 租金折扣條件 | `jgb/E/rent-market-discount-tax` | 租金行情、折扣條件與公益出租人減稅（租客視角） | new | ⚠️ E/E/? | |
| 36 | `tmp:kb:2921` | 租金支付證明 | `jgb/E/bill-receipt-pdf` | 帳單收據 PDF 下載與繳費證明 | new | E/E/E | |
| 37 | `tmp:kb:2925` | 租金市場變化 | `jgb/E/rent-market-discount-tax` | 租金行情、折扣條件與公益出租人減稅（租客視角） | new | ⚠️ E/E/? | |
| 38 | `tmp:kb:3011` | 公益出租人減稅 | `jgb/E/rent-market-discount-tax` | 租金行情、折扣條件與公益出租人減稅（租客視角） | new | ⚠️ E/E/? | |
| 39 | `tmp:kb:3105` | 管理費用途 | `jgb/E/management-fee` | 管理費是什麼、用途與怎麼算 | new | E/E/E | |
| 40 | `tmp:kb:3207` | 租金少繳不足補繳 | `jgb/E/payment-amount-mismatch` | 付款金額不符、重複轉帳、多繳少繳怎麼處理 | new | E/E/E | |
| 41 | `tmp:kb:3208` | 租金遲繳罰款 | `jgb/E/late-fee-calculation` | 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額） | new | E/E/E | |
| 42 | `tmp:kb:3326` | 包租代管租金代收與房東直收差異 | `jgb/E/rent-collection-agent-vs-direct` | 包租代管租金代收與房東直收有什麼差別 | new | ⚠️ E/E/? | |
| 43 | `tmp:kb:3327` | 提前終止 帳單封存 退租 | `jgb/E/bill-archive-after-termination` | 提前終止／退租後多產生的帳單要封存、封存後怎麼退回 | new | E/E/E | |
| 44 | `tmp:kb:3335` | 對帳流程 帳單狀態 應到帳 待對帳 已到帳 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 45 | `tmp:kb:3336` | 帳單排定發送 自動發送 草稿帳單 | `jgb/E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | new | E/E/E | |
| 46 | `tmp:kb:3337` | 帳單簡訊 費用 收費 | `jgb/E/payment-fees-and-sms` | 金流手續費誰負擔、費率多少與帳單簡訊是否收費 | new | ⚠️ E/E/? | |
| 47 | `tmp:kb:3338` | 物件 帳單 發票 對應關係 | `jgb/E/einvoice-issuing` | 電子發票何時開、自動開立設定、載具類型與一物件一發票 | merge | E/E/E | |
| 48 | `tmp:kb:3340` | 催繳 逾期 通知 | `jgb/E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（繳費提醒、催繳通知條件、逾期標示與訂閱通知） | merge | E/E/E | |
| 49 | `tmp:kb:3342` | 帳單繳費期限 發送日 設定 | `jgb/E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | new | E/E/E | |
| 50 | `tmp:kb:3343` | 國泰 超商繳費 狀態流程 | `jgb/E/convenience-store-payment` | 超商代碼／條碼繳費流程與入帳撥付時程 | new | E/E/E | |
| 51 | `tmp:kb:3344` | 永豐 臨櫃匯款 虛擬帳號格式 | `jgb/E/virtual-account-transfer` | 虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易 | new | E/E/E | |
| 52 | `tmp:kb:3346` | 金流 手續費 誰支付 | `jgb/E/payment-fees-and-sms` | 金流手續費誰負擔、費率多少與帳單簡訊是否收費 | new | E/E/E | |
| 53 | `tmp:kb:3347` | 信用卡 繳費 定期扣款 刷卡 | `jgb/E/credit-card-rent-payment` | 租客能不能用信用卡繳房租（限藍新、流程與限制） | merge | E/E/E | |
| 54 | `tmp:kb:3352` | 電費 計算 夏季 非夏季 電價 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 55 | `tmp:kb:3353` | 電表 儲值 雲端電表 | `jgb/E/prepaid-meter-topup-billing` | 儲值電表的儲值帳單、入帳與電費預付收取 | new | E/E/E | |
| 56 | `tmp:kb:3360` | 匯出 報表 收支明細 | `jgb/E/bill-reports-export` | 帳單報表匯出、統計圖表與儀表板 | new | E/E/E | |
| 57 | `tmp:kb:3361` | 帳單沒到帳 帳單狀態 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 58 | `tmp:kb:3362` | 發票沒開 發票狀態 | `jgb/E/invoice-not-issued-troubleshooting` | 發票為什麼還沒開、顯示已開卻沒號碼的排查 | new | E/E/E | |
| 59 | `tmp:kb:3366` | 繳費成功 繳費紀錄 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 60 | `tmp:kb:3391` | 信用卡自動扣款 授權設定 | `jgb/E/credit-card-auto-debit` | 信用卡自動扣款授權設定與扣款失敗處理 | new | E/E/E | |
| 61 | `tmp:kb:3395` | 帳單狀態流程 對帳機制 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 62 | `tmp:kb:3396` | 帳單收費項目 六種費用 | `jgb/E/bill-contents-extra-fees` | 帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整） | merge | E/E/E | |
| 63 | `tmp:kb:3397` | 租金計費方式 週期比例 | `jgb/E/rent-amount-calculation` | 租金金額怎麼算（以合約租金快照為準、不足月按比例） | new | E/E/E | |
| 64 | `tmp:kb:3398` | 電費計費方式 度數計算 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 65 | `tmp:kb:3399` | 週期帳單 自動產生規則 | `jgb/E/periodic-bill-generation` | 週期帳單何時產生、三種建立方式與續約／補簽起算 | new | E/E/E | |
| 66 | `tmp:kb:3400` | 逾期費計算 催繳通知 | `jgb/E/late-fee-calculation` | 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額） | new | E/E/E | |
| 67 | `tmp:kb:3401` | 帳單建立方式 手動自動 | `jgb/E/periodic-bill-generation` | 週期帳單何時產生、三種建立方式與續約／補簽起算 | new | E/E/E | |
| 68 | `tmp:kb:3402` | 點退帳單 自動產生 費用結算 | `jgb/E/checkout-bill-settlement` | 點退帳單怎麼算（未結費用、賠償、押金互抵、多退少補） | new | E/E/E | |
| 69 | `tmp:kb:3403` | 帳單排定發送 預約機制 | `jgb/E/bill-recall-cancel` | 帳單發出去想收回、取消或設失效（可用狀態與繳費資訊斷開） | split | E/E/E | |
| 70 | `tmp:kb:3403` | 帳單排定發送 預約機制 | `jgb/E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | split | E/E/E | |
| 71 | `tmp:kb:3404` | 大量建立帳單 Excel 批次匯入 | `jgb/E/manual-bill-creation` | 手動新增帳單、負值退款、Excel 批次匯入與補建紀錄 | new | E/E/E | |
| 72 | `tmp:kb:3405` | 自訂費用品項 管理設定 | `jgb/E/bill-contents-extra-fees` | 帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整） | merge | E/E/E | |
| 73 | `tmp:kb:3406` | 帳單收據 繳費證明 PDF 下載 | `jgb/E/bill-receipt-pdf` | 帳單收據 PDF 下載與繳費證明 | new | E/E/E | |
| 74 | `tmp:kb:3407` | 帳單統計報表 收支分析 | `jgb/E/bill-reports-export` | 帳單報表匯出、統計圖表與儀表板 | new | E/E/E | |
| 75 | `tmp:kb:3408` | 繳租金方式 信用卡超商轉帳 | `jgb/E/tenant-payment-methods` | 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層） | new | E/E/E | |
| 76 | `tmp:kb:3409` | 信用卡繳費 流程說明 | `jgb/E/credit-card-rent-payment` | 租客能不能用信用卡繳房租（限藍新、流程與限制） | merge | E/E/E | |
| 77 | `tmp:kb:3410` | 虛擬帳號轉帳 繳費方式 | `jgb/E/virtual-account-transfer` | 虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易 | new | E/E/E | |
| 78 | `tmp:kb:3411` | 超商代碼繳費 流程說明 | `jgb/E/convenience-store-payment` | 超商代碼／條碼繳費流程與入帳撥付時程 | new | E/E/E | |
| 79 | `tmp:kb:3412` | 付款狀態 流轉說明 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 80 | `tmp:kb:3413` | 金流商 各家特性 | `jgb/E/payment-gateway-options` | 金流廠商差別、支援付款方式與申請條件 | merge | E/E/E | |
| 81 | `tmp:kb:3414` | 付款成功 自動開發票 | `jgb/E/einvoice-issuing` | 電子發票何時開、自動開立設定、載具類型與一物件一發票 | merge | E/E/E | |
| 82 | `tmp:kb:3415` | 信用卡自動扣款 失敗處理 | `jgb/E/credit-card-auto-debit` | 信用卡自動扣款授權設定與扣款失敗處理 | new | E/E/E | |
| 83 | `tmp:kb:3416` | 付款金額錯誤 重複轉帳 | `jgb/E/payment-amount-mismatch` | 付款金額不符、重複轉帳、多繳少繳怎麼處理 | new | E/E/E | |
| 84 | `tmp:kb:3417` | 儲值金 回充帳戶功能 | `jgb/E/fixed-virtual-account-management` | 固定虛擬帳號怎麼開通設定、入帳沖銷與餘額歷程查詢 | new | E/E/E | |
| 85 | `tmp:kb:3418` | 發票開立時機 觸發條件 | `jgb/E/einvoice-issuing` | 電子發票何時開、自動開立設定、載具類型與一物件一發票 | merge | E/E/E | |
| 86 | `tmp:kb:3419` | 電子發票 類型格式 | `jgb/E/einvoice-issuing` | 電子發票何時開、自動開立設定、載具類型與一物件一發票 | merge | E/E/E | |
| 87 | `tmp:kb:3420` | 發票未收到 排查步驟 | `jgb/E/invoice-not-issued-troubleshooting` | 發票為什麼還沒開、顯示已開卻沒號碼的排查 | new | E/E/E | |
| 88 | `tmp:kb:3421` | 發票作廢 流程說明 | `jgb/E/invoice-void-reissue` | 發票開錯了怎麼作廢、補開與作廢不了 | new | E/E/E | |
| 89 | `tmp:kb:3422` | 差額發票 功能說明 | `jgb/E/differential-invoice` | 差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出） | new | E/E/E | |
| 90 | `tmp:kb:3423` | 發票補開 特殊處理 | `jgb/E/invoice-void-reissue` | 發票開錯了怎麼作廢、補開與作廢不了 | new | E/E/E | |
| 91 | `tmp:kb:3443` | 線上繳費 付款步驟 | `jgb/E/tenant-online-payment-steps` | 租客線上繳費操作步驟（信用卡、虛擬 ATM） | new | E/E/E | |
| 92 | `tmp:kb:3447` | 查看合約帳單 資訊查詢 | `jgb/E/tenant-view-bills` | 租客在哪裡看帳單、繳費狀態與付款入口 | new | E/E/E | |
| 93 | `tmp:kb:3459` | 儲值電表 使用儲值 | `jgb/E/prepaid-meter-topup-billing` | 儲值電表的儲值帳單、入帳與電費預付收取 | new | E/E/E | |
| 94 | `tmp:kb:3466` | 大房東帳單 代收代付 | `jgb/E/landlord-owner-bills` | 大房東帳單（代收代付）怎麼看與建立 | new | E/E/E | |
| 95 | `tmp:kb:3478` | 邀請租客 訂閱通知 | `jgb/E/overdue-reminder-late-fee` | 租客逾期未繳怎麼辦（繳費提醒、催繳通知條件、逾期標示與訂閱通知） | merge | E/E/E | |
| 96 | `tmp:kb:3485` | 帳單發送收款 催繳管理 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 97 | `tmp:kb:3489` | 合約帳單管理 查詢統計 | `jgb/E/bill-reports-export` | 帳單報表匯出、統計圖表與儀表板 | new | E/E/E | |
| 98 | `tmp:kb:3495` | 帳單為什麼發不出去 | `jgb/E/bill-send-failure` | 帳單為什麼發不出去（狀態、金額、度數未填、租客聯絡方式未驗證） | new | E/E/E | |
| 99 | `tmp:kb:3496` | 帳單為什麼取消不了 | `jgb/E/bill-recall-cancel` | 帳單發出去想收回、取消或設失效（可用狀態與繳費資訊斷開） | new | E/E/E | |
| 100 | `tmp:kb:3497` | 已付款但帳單狀態沒有更新 | `jgb/E/paid-but-status-not-updated` | 租客說繳了但錢還沒進來／帳單卡在待對帳 | new | E/E/E | |
| 101 | `tmp:kb:3499` | 帳單手動到帳或標記已收款失敗 | `jgb/E/bill-status-reconciliation` | 帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳 | new | E/E/E | |
| 102 | `tmp:kb:3500` | 信用卡付款失敗 | `jgb/E/payment-failure-troubleshooting` | 租客繳不了費／轉帳或刷卡一直失敗怎麼排查 | new | E/E/E | |
| 103 | `tmp:kb:3501` | 信用卡自動扣款失敗 | `jgb/E/credit-card-auto-debit` | 信用卡自動扣款授權設定與扣款失敗處理 | new | E/E/E | |
| 104 | `tmp:kb:3502` | 虛擬帳號過期或轉帳失敗 | `jgb/E/payment-failure-troubleshooting` | 租客繳不了費／轉帳或刷卡一直失敗怎麼排查 | new | E/E/E | |
| 105 | `tmp:kb:3503` | 發票為什麼沒有開出來 | `jgb/E/invoice-not-issued-troubleshooting` | 發票為什麼還沒開、顯示已開卻沒號碼的排查 | new | E/E/E | |
| 106 | `tmp:kb:3504` | 發票為什麼作廢不了 | `jgb/E/invoice-void-reissue` | 發票開錯了怎麼作廢、補開與作廢不了 | new | E/E/E | |
| 107 | `tmp:kb:3519` | 點退帳單金額計算 押金結算 | `jgb/E/checkout-bill-settlement` | 點退帳單怎麼算（未結費用、賠償、押金互抵、多退少補） | new | E/E/E | |
| 108 | `tmp:kb:3531` | 滯納金帳單產生 付款後結算規則 | `jgb/E/late-fee-calculation` | 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額） | new | E/E/E | |
| 109 | `tmp:kb:3532` | 滯納金客製版本 固定金額階梯式 | `jgb/E/late-fee-calculation` | 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額） | new | E/E/E | |
| 110 | `tmp:kb:3533` | 押金設算息 利率計算與帳單 | `jgb/E/deposit-imputed-interest` | 押金設算息怎麼算、利率設定與年度一次限制 | new | E/E/E | |
| 111 | `tmp:kb:3534` | 押金設算息利率設定 年度一次限制 | `jgb/E/deposit-imputed-interest` | 押金設算息怎麼算、利率設定與年度一次限制 | new | E/E/E | |
| 112 | `tmp:kb:3535` | 差額發票金額計算 租金品項底租 | `jgb/E/differential-invoice` | 差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出） | new | E/E/E | |
| 113 | `tmp:kb:3536` | 差額發票金額變少 前期虧損結轉 | `jgb/E/differential-invoice` | 差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出） | new | E/E/E | |
| 114 | `tmp:kb:3537` | 差額發票群組 物件綁定底租設定 | `jgb/E/differential-invoice` | 差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出） | new | E/E/E | |
| 115 | `tmp:kb:3538` | 差額發票開立匯出 自動排程收支明細 | `jgb/E/differential-invoice` | 差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出） | new | E/E/E | |
| 116 | `tmp:kb:3539` | 固定虛擬帳號不會過期 與一般帳號差別 | `jgb/E/virtual-account-prepaid` | 固定虛擬帳號與儲值金抵扣是什麼、跟一般虛擬帳號差在哪 | merge | E/E/E | |
| 117 | `tmp:kb:3540` | 固定虛擬帳號設定 銀行模式權限 | `jgb/E/fixed-virtual-account-management` | 固定虛擬帳號怎麼開通設定、入帳沖銷與餘額歷程查詢 | new | E/E/E | |
| 118 | `tmp:kb:3541` | 固定虛擬帳號入帳 自動扣款對帳 | `jgb/E/fixed-virtual-account-management` | 固定虛擬帳號怎麼開通設定、入帳沖銷與餘額歷程查詢 | new | E/E/E | |
| 119 | `tmp:kb:3542` | 固定虛擬帳號查詢 餘額變動歷程 | `jgb/E/fixed-virtual-account-management` | 固定虛擬帳號怎麼開通設定、入帳沖銷與餘額歷程查詢 | new | E/E/E | |
| 120 | `tmp:kb:3548` | 申請線上金流 先確認金流商 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 121 | `tmp:kb:3549` | 藍新金流申請 資料與審核時間 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 122 | `tmp:kb:3550` | 永豐金流設定 店舖編號加密因子 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 123 | `tmp:kb:3551` | 信用卡ATM收款手續費 房東負擔 | `jgb/E/payment-fees-and-sms` | 金流手續費誰負擔、費率多少與帳單簡訊是否收費 | new | E/E/E | |
| 124 | `tmp:kb:3552` | 現金銀行帳戶收款設定 手動確認入帳 | `jgb/E/cash-bank-account-collection` | 現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳 | new | E/E/E | |
| 125 | `tmp:kb:3553` | 收款設置 收訖章與帳單自動發送 | `jgb/E/bill-format-customize` | 帳單版面、收據版式與收訖章能不能自訂 | split | E/E/E | |
| 126 | `tmp:kb:3553` | 收款設置 收訖章與帳單自動發送 | `jgb/E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | split | E/E/E | |
| 127 | `tmp:kb:3554` | 線上金流只能綁一家 更換與未設定 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 128 | `tmp:kb:3555` | 國泰世華金流設定 ATM前綴加密因子 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 129 | `tmp:kb:3852` | 提前終止後帳單仍產生 需封存 | `jgb/E/bill-archive-after-termination` | 提前終止／退租後多產生的帳單要封存、封存後怎麼退回 | new | E/E/E | |
| 130 | `tmp:kb:3857` | 續約帳單 起算時點 | `jgb/E/periodic-bill-generation` | 週期帳單何時產生、三種建立方式與續約／補簽起算 | new | E/E/E | |
| 131 | `tmp:kb:3895` | 物件刊登租金調整 帳單金額不變 | `jgb/E/rent-amount-calculation` | 租金金額怎麼算（以合約租金快照為準、不足月按比例） | new | E/E/E | |
| 132 | `tmp:kb:3923` | 超商繳費 狀態沒跳 撥付時程 | `jgb/E/convenience-store-payment` | 超商代碼／條碼繳費流程與入帳撥付時程 | new | E/E/E | |
| 133 | `tmp:kb:3924` | 租客轉帳失敗 匯款上限 資訊核對 | `jgb/E/payment-failure-troubleshooting` | 租客繳不了費／轉帳或刷卡一直失敗怎麼排查 | new | E/E/E | |
| 134 | `tmp:kb:3925` | 臨櫃匯款 虛擬帳號 可行方式 | `jgb/E/virtual-account-transfer` | 虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易 | new | E/E/E | |
| 135 | `tmp:kb:3926` | 帳單收回重發 發出去想收回 影響與時機 | `jgb/E/bill-recall-cancel` | 帳單發出去想收回、取消或設失效（可用狀態與繳費資訊斷開） | new | E/E/E | |
| 136 | `tmp:kb:3927` | 租客看不到帳單 三條件與信箱情境 | `jgb/E/tenant-cannot-see-bill` | 租客說看不到帳單（可見三條件與信箱錯配） | new | E/E/E | |
| 137 | `tmp:kb:3928` | 帳單還沒出現 產生時點規則 | `jgb/E/periodic-bill-generation` | 週期帳單何時產生、三種建立方式與續約／補簽起算 | new | E/E/E | |
| 138 | `tmp:kb:3929` | 發票顯示已開 卻沒有號碼 | `jgb/E/invoice-not-issued-troubleshooting` | 發票為什麼還沒開、顯示已開卻沒號碼的排查 | new | E/E/E | |
| 139 | `tmp:kb:3930` | 新收款帳戶驗證 一元帳單測試 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 140 | `tmp:kb:3931` | 租客說繳了 錢還沒進來 | `jgb/E/paid-but-status-not-updated` | 租客說繳了但錢還沒進來／帳單卡在待對帳 | new | E/E/E | |
| 141 | `tmp:kb:3932` | 帳單卡在待對帳 狀態一直沒跳 | `jgb/E/paid-but-status-not-updated` | 租客說繳了但錢還沒進來／帳單卡在待對帳 | new | E/E/E | |
| 142 | `tmp:kb:3933` | 租客繳不了費 一直失敗 | `jgb/E/payment-failure-troubleshooting` | 租客繳不了費／轉帳或刷卡一直失敗怎麼排查 | new | E/E/E | |
| 143 | `tmp:kb:3934` | 帳單金額怪怪的 跟預期不一樣 | `jgb/E/rent-amount-calculation` | 租金金額怎麼算（以合約租金快照為準、不足月按比例） | new | E/E/E | |
| 144 | `tmp:kb:3935` | 這期帳單怎麼還沒出來 | `jgb/E/periodic-bill-generation` | 週期帳單何時產生、三種建立方式與續約／補簽起算 | new | E/E/E | |
| 145 | `tmp:kb:3936` | 租客說看不到帳單 找不到 | `jgb/E/tenant-cannot-see-bill` | 租客說看不到帳單（可見三條件與信箱錯配） | new | E/E/E | |
| 146 | `tmp:kb:3937` | 發票怎麼還沒開 沒收到發票 | `jgb/E/invoice-not-issued-troubleshooting` | 發票為什麼還沒開、顯示已開卻沒號碼的排查 | new | E/E/E | |
| 147 | `tmp:kb:3938` | 發票開錯了 要作廢重開 | `jgb/E/invoice-void-reissue` | 發票開錯了怎麼作廢、補開與作廢不了 | new | E/E/E | |
| 148 | `tmp:kb:3939` | 滯納金怎麼收這麼多 | `jgb/E/late-fee-calculation` | 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額） | new | E/E/E | |
| 149 | `tmp:kb:3940` | 這筆延遲金是怎麼算的 | `jgb/E/late-fee-calculation` | 滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額） | new | E/E/E | |
| 150 | `tmp:kb:3941` | 要開始收租 帳單要怎麼設定 | `jgb/E/periodic-bill-generation` | 週期帳單何時產生、三種建立方式與續約／補簽起算 | new | E/E/E | |
| 151 | `tmp:kb:3942` | 收款帳戶怎麼綁 金流怎麼申請 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 152 | `tmp:kb:4053` | 租客儲值教學 操作步驟 | `jgb/E/prepaid-meter-topup-billing` | 儲值電表的儲值帳單、入帳與電費預付收取 | new | E/E/E | |
| 153 | `tmp:kb:4086` | 儲值電表 電費收取 租客預付 | `jgb/E/prepaid-meter-topup-billing` | 儲值電表的儲值帳單、入帳與電費預付收取 | new | E/E/E | |
| 154 | `tmp:kb:4150` | 報表匯出 帳單報表 大量資料 | `jgb/E/bill-reports-export` | 帳單報表匯出、統計圖表與儀表板 | new | E/E/E | |
| 155 | `tmp:kb:4217` | 電費 收費方式 設定 包租金 另外收 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 156 | `tmp:kb:4220` | 草稿帳單 會自動發送嗎 封存哪裡看 | `jgb/E/bill-scheduled-auto-send` | 帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿） | new | E/E/E | |
| 157 | `tmp:kb:4221` | 收款帳戶 銀行有限制嗎 台新 | `jgb/E/payment-gateway-setup` | 線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試） | new | E/E/E | |
| 158 | `tmp:kb:4222` | 電表度數登記錯誤 修改 重算 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 159 | `tmp:kb:4223` | 帳單在哪裡看 繳費 | `jgb/E/tenant-view-bills` | 租客在哪裡看帳單、繳費狀態與付款入口 | new | E/E/E | |
| 160 | `tmp:kb:4256` | 調整收款方式 線上付款方式設定 租客繳費通道 | `jgb/E/tenant-payment-methods` | 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層） | new | E/E/E | |
| 161 | `tmp:kb:4257` | 發票自動開立時點 何時開發票 開立時間 | `jgb/E/einvoice-issuing` | 電子發票何時開、自動開立設定、載具類型與一物件一發票 | merge | E/E/E | |
| 162 | `tmp:kb:4265` | 電費 計費方式 每度電價 電錶 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 163 | `tmp:kb:4268` | 繳費方式 怎麼繳費 轉帳帳戶 超商繳費 | `jgb/E/tenant-payment-methods` | 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層） | new | E/E/E | |
| 164 | `tmp:kb:4271` | 為什麼要收管理費 費用怎麼算 | `jgb/E/management-fee` | 管理費是什麼、用途與怎麼算 | new | E/E/E | |
| 165 | `tmp:kb:4282` | 電費怎麼算 一度多少錢 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 166 | `tmp:kb:4283` | 電費帳單計費方式 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 167 | `tmp:kb:4285` | 水費帳單計費方式 | `jgb/E/utility-meter-billing-and-reading` | 水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算） | new | E/E/E | |
| 168 | `tmp:kb:4288` | 可以用什麼方式繳費 有哪些繳費管道 | `jgb/E/tenant-payment-methods` | 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層） | new | E/E/E | |
| 169 | `tmp:kb:4289` | 可以超商繳費或轉帳嗎 | `jgb/E/tenant-payment-methods` | 租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層） | new | E/E/E | |
| 170 | `tmp:kb:4637` | 帳單總表 虛擬帳號查交易 銀行抽查入帳 | `jgb/E/virtual-account-transfer` | 虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易 | new | E/E/E | |
| 171 | `tmp:kb:4638` | 帳單批次匯入 整批電費帳單 批次建立 | `jgb/E/manual-bill-creation` | 手動新增帳單、負值退款、Excel 批次匯入與補建紀錄 | new | E/E/E | |
| 172 | `tmp:kb:4642` | 帳單品名修改 租金改停車位費 | `jgb/E/bill-contents-extra-fees` | 帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整） | merge | E/E/E | |
| 173 | `tmp:kb:4643` | 帳單無法寄送 租客聯絡方式未驗證 | `jgb/E/bill-send-failure` | 帳單為什麼發不出去（狀態、金額、度數未填、租客聯絡方式未驗證） | new | E/E/E | |
| 174 | `tmp:kb:4647` | 未發送帳單一次編輯 批次調整範圍 | `jgb/E/bill-contents-extra-fees` | 帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整） | merge | E/E/E | |
| 175 | `tmp:kb:4649` | 租客直接匯款 補建帳單紀錄 | `jgb/E/manual-bill-creation` | 手動新增帳單、負值退款、Excel 批次匯入與補建紀錄 | new | E/E/E | |
| 176 | `tmp:kb:4650` | 新增帳單 手動開帳單給租客 操作入口 | `jgb/E/manual-bill-creation` | 手動新增帳單、負值退款、Excel 批次匯入與補建紀錄 | new | E/E/E | |
| 177 | `tmp:kb:4651` | 逾期帳單虛擬帳號 可否繳款 年繳拆分 | `jgb/E/virtual-account-transfer` | 虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易 | new | E/E/E | |
| 178 | `tmp:kb:4653` | 帳單封存後退回 重開帳單 | `jgb/E/bill-archive-after-termination` | 提前終止／退租後多產生的帳單要封存、封存後怎麼退回 | new | E/E/E | |
| 179 | `tmp:kb:4656` | 查帳單 帳單編號查詢 | `jgb/E/overdue-bill-followup-scope` | 逾期帳單追問可答範圍（依帳單編號查狀態、金額、逾期明細） | merge | E/E/E | |
| 180 | `tmp:kb:4657` | 合約的點退帳單金額 查點退金額 | `jgb/E/checkout-bill-settlement` | 點退帳單怎麼算（未結費用、賠償、押金互抵、多退少補） | new | E/E/E | |

## B. 拆分（split）——一個舊細目拆成多個新細目

| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |
|---|---|---|---|
| `tmp:kb:3403` | 帳單排定發送 預約機制 | `jgb/E/bill-recall-cancel`《帳單發出去想收回、取消或設失效（可用狀態與繳費資訊斷開）》；`jgb/E/bill-scheduled-auto-send`《帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿）》 | |
| `tmp:kb:3553` | 收款設置 收訖章與帳單自動發送 | `jgb/E/bill-format-customize`《帳單版面、收據版式與收訖章能不能自訂》；`jgb/E/bill-scheduled-auto-send`《帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿）》 | |
| `tmp:kb:tmp:draft:1` |  | `jgb/E/bill-format-customize`《帳單版面、收據版式與收訖章能不能自訂》；`jgb/E/bill-scheduled-auto-send`《帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿）》；`jgb/E/cash-bank-account-collection`《現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳》；`jgb/E/payment-gateway-setup`《線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試）》 | |

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/E/bill-archive-after-termination`《提前終止／退租後多產生的帳單要封存、封存後怎麼退回》 | `tmp:kb:3327`＋`tmp:kb:3852`＋`tmp:kb:4653` | 「解約後帳單還在產生怎麼辦」答案是批次封存與異動單退回，是帳單退場動作、獨立於終止流程本身。 | |
| `jgb/E/bill-contents-extra-fees`《帳單內容、費用品項與臨時加收（六種費用、自訂品項、品名、未發送批次調整）》 | `tmp:kb:tmp:canon:jgb/E/bill-contents-extra-fees`＋`tmp:kb:3396`＋`tmp:kb:3405`＋`tmp:kb:4642`＋`tmp:kb:4647` | 「帳單列上有哪些費用、品項名稱怎麼來、臨時加收怎麼補」是同一命題；4647 一次編輯未發送帳單只支援水電、加收項目要另開週期帳單，正是臨時加收的操作邊界，併入。 | |
| `jgb/E/bill-format-customize`《帳單版面、收據版式與收訖章能不能自訂》 | `tmp:kb:tmp:canon:jgb/E/bill-format-customize`＋`tmp:kb:3553`＋`tmp:kb:tmp:draft:1` | 版面可調什麼的答案就是收款設置頁的收據版式與收訖章；3553 與 draft:1 只取收據類型與收款章段落，其餘段落拆給發送與金流細目。 | |
| `jgb/E/bill-recall-cancel`《帳單發出去想收回、取消或設失效（可用狀態與繳費資訊斷開）》 | `tmp:kb:3926`＋`tmp:kb:3496`＋`tmp:kb:3403` | 「能不能收回／為什麼取消不了」同一提問，答案是狀態限制與收回會刷新繳費資訊；3403 只取收回段。 | |
| `jgb/E/bill-receipt-pdf`《帳單收據 PDF 下載與繳費證明》 | `tmp:kb:3406`＋`tmp:kb:2921` | 「要繳費證明／收據哪裡下載」同題，含租客視角；收據版式設定屬版面細目、查收據金額是 face 資料查詢。 | |
| `jgb/E/bill-reports-export`《帳單報表匯出、統計圖表與儀表板》 | `tmp:kb:3360`＋`tmp:kb:3407`＋`tmp:kb:4150`＋`tmp:kb:3489` | 報表種類、收款品項篩選限制、大量匯出等待與儀表板／統計圖是「彙總輸出」的同一組功能。 | |
| `jgb/E/bill-scheduled-auto-send`《帳單什麼時候發、排定發送與自動發送設定（提前天數、整點批次、草稿）》 | `tmp:kb:3336`＋`tmp:kb:3342`＋`tmp:kb:4220`＋`tmp:kb:tmp:draft:3`＋`tmp:kb:3403`＋`tmp:kb:3553`＋`tmp:kb:tmp:draft:1` | 「草稿會自動發嗎、幾點寄出、提前幾天」互相依賴才完整；批次排定發送教學併入；3403／3553／draft:1 只取排定發送段落。 | |
| `jgb/E/bill-send-failure`《帳單為什麼發不出去（狀態、金額、度數未填、租客聯絡方式未驗證）》 | `tmp:kb:3495`＋`tmp:kb:4643` | 發送被擋的原因自成一張排查清單，不依賴排程規則。 | |
| `jgb/E/bill-status-reconciliation`《帳單與付款狀態流程、線上自動對帳 vs 線下手動到帳》 | `tmp:kb:3335`＋`tmp:kb:3395`＋`tmp:kb:3412`＋`tmp:kb:3485`＋`tmp:kb:3499`＋`tmp:kb:3361`＋`tmp:kb:3366`＋`tmp:kb:tmp:draft:9`＋`tmp:kb:tmp:draft:11`＋`tmp:kb:tmp:draft:13`＋`tmp:kb:tmp:draft:4` | 六種帳單狀態、付款狀態、線上／線下對帳差異、手動到帳失敗與既存合約歷史帳單移至已到帳，都靠同一條狀態機解釋；3361、3366 空內文只當入口。 | |
| `jgb/E/cash-bank-account-collection`《現金／銀行帳戶收款：帳戶設定、租客通知已匯款與業者手動確認入帳》 | `tmp:kb:3552`＋`tmp:kb:tmp:draft:8`＋`tmp:kb:tmp:draft:10`＋`tmp:kb:tmp:draft:14`＋`tmp:kb:tmp:draft:1` | 線下收款帳戶的建立、租客回報後五碼、房東手動確認是一條完整的線下流程；draft:1 只取現金收款帳戶段落。 | |
| `jgb/E/checkout-bill-settlement`《點退帳單怎麼算（未結費用、賠償、押金互抵、多退少補）》 | `tmp:kb:3402`＋`tmp:kb:3519`＋`tmp:kb:4657` | 「點退金額怎麼來、是退錢還是補繳」同題，出現在帳單列上歸帳務；4657 空內文只當入口。 | |
| `jgb/E/convenience-store-payment`《超商代碼／條碼繳費流程與入帳撥付時程》 | `tmp:kb:3411`＋`tmp:kb:3343`＋`tmp:kb:3923` | 「超商繳了狀態沒跳」答案就是超商通道分段與撥付日，3343 與 3923 近重複併為一題。 | |
| `jgb/E/credit-card-auto-debit`《信用卡自動扣款授權設定與扣款失敗處理》 | `tmp:kb:3391`＋`tmp:kb:3415`＋`tmp:kb:3501` | 授權設定、續扣、失敗通知與改付方式是一套機制，與單次刷卡分開；⚠ 與 3347「房租不可定期扣款」矛盾，本細目只標不裁。 | |
| `jgb/E/credit-card-rent-payment`《租客能不能用信用卡繳房租（限藍新、流程與限制）》 | `tmp:kb:tmp:canon:jgb/E/credit-card-rent-payment`＋`tmp:kb:3347`＋`tmp:kb:3409` | 能不能刷、走哪家、流程怎麼走同屬一次性刷卡命題；⚠ 材料矛盾：3347 說房租不可設定定期扣款，3391／3408 說有信用卡自動扣款，本細目不裁真偽，自動扣款另立細目。 | |
| `jgb/E/deposit-imputed-interest`《押金設算息怎麼算、利率設定與年度一次限制》 | `tmp:kb:3533`＋`tmp:kb:3534` | 客製功能的計算與年度一次設定限制彼此依賴，自成一題。 | |
| `jgb/E/differential-invoice`《差額發票（群組綁定、底租、金額計算與虧損結轉、開立匯出）》 | `tmp:kb:3422`＋`tmp:kb:3535`＋`tmp:kb:3536`＋`tmp:kb:3537`＋`tmp:kb:3538` | 群組綁定、底租、虧損結轉與開立匯出是同一功能的連續段落，拆開會失去計算脈絡。 | |
| `jgb/E/einvoice-issuing`《電子發票何時開、自動開立設定、載具類型與一物件一發票》 | `tmp:kb:tmp:canon:jgb/E/einvoice-issuing`＋`tmp:kb:3418`＋`tmp:kb:4257`＋`tmp:kb:3414`＋`tmp:kb:3419`＋`tmp:kb:3338` | 開立模式、觸發時點、載具格式與「一物件一帳單一發票」前提互相依賴才答得完整；未開出的排查與作廢補開各自成排查清單，另立。 | |
| `jgb/E/fixed-virtual-account-management`《固定虛擬帳號怎麼開通設定、入帳沖銷與餘額歷程查詢》 | `tmp:kb:3417`＋`tmp:kb:3540`＋`tmp:kb:3541`＋`tmp:kb:3542` | 業者操作面（開通銀行、模式權限、手動對帳／自動沖銷、歷程與匯出）與售前概念題分開成受眾版細目。 | |
| `jgb/E/invoice-not-issued-troubleshooting`《發票為什麼還沒開、顯示已開卻沒號碼的排查》 | `tmp:kb:3420`＋`tmp:kb:3503`＋`tmp:kb:3929`＋`tmp:kb:3937`＋`tmp:kb:3362` | 發票未開立排查自成清單，可獨立於開立模式說明回答；3937、3362 空內文只當入口。 | |
| `jgb/E/invoice-void-reissue`《發票開錯了怎麼作廢、補開與作廢不了》 | `tmp:kb:3421`＋`tmp:kb:3423`＋`tmp:kb:3504`＋`tmp:kb:3938` | 作廢與補開是成對的修正動作，與開立時機、未開排查分開；3938 空內文只當入口。 | |
| `jgb/E/late-fee-calculation`《滯納金／延遲金怎麼算、何時產生與客製版本（延遲金、階梯式、固定金額）》 | `tmp:kb:3400`＋`tmp:kb:3531`＋`tmp:kb:3532`＋`tmp:kb:3939`＋`tmp:kb:3940`＋`tmp:kb:3208` | 公式、三版差異與獨立滯納金帳單互相依賴；3208 租客視角遲繳罰款併入；3939、3940 空內文只當入口。 | |
| `jgb/E/management-fee`《管理費是什麼、用途與怎麼算》 | `tmp:kb:2910`＋`tmp:kb:3105`＋`tmp:kb:4271` | 租客視角問管理費用途與計算，屬帳單列上費用留 E；4271 空內文只當入口；查自己的管理費金額是 face 資料查詢，不併入。 | |
| `jgb/E/manual-bill-creation`《手動新增帳單、負值退款、Excel 批次匯入與補建紀錄》 | `tmp:kb:tmp:draft:2`＋`tmp:kb:4650`＋`tmp:kb:3404`＋`tmp:kb:4638`＋`tmp:kb:4649` | 單筆新增、負值退款、批次匯入與租客直接匯款後補建紀錄都是「不靠週期、人工開帳單」的操作路徑。 | |
| `jgb/E/overdue-bill-followup-scope`《逾期帳單追問可答範圍（依帳單編號查狀態、金額、逾期明細）》 | `tmp:kb:tmp:canon:jgb/E/overdue-bill-followup-scope`＋`tmp:kb:4656` | 「查某張帳單編號」是既有可答範圍的入口講法，4656 空內文只當入口；查點退金額歸點退帳單細目。 | |
| `jgb/E/overdue-reminder-late-fee`《租客逾期未繳怎麼辦（繳費提醒、催繳通知條件、逾期標示與訂閱通知）》 | `tmp:kb:tmp:canon:jgb/E/overdue-reminder-late-fee`＋`tmp:kb:3340`＋`tmp:kb:tmp:draft:12`＋`tmp:kb:3478` | 催繳通知時機與待對帳不催的條件、逾期紅字標示、邀請租客訂閱通知都是「租客沒繳系統會怎麼提醒」；通知是投遞管道，歸它所通知的逾期領域，不自成細目。 | |
| `jgb/E/paid-but-status-not-updated`《租客說繳了但錢還沒進來／帳單卡在待對帳》 | `tmp:kb:3497`＋`tmp:kb:3931`＋`tmp:kb:3932` | 已付款未更新是最常見的客服故障提問，與狀態流程說明分開成排查入口；3931、3932 空內文只當入口。 | |
| `jgb/E/payment-amount-mismatch`《付款金額不符、重複轉帳、多繳少繳怎麼處理》 | `tmp:kb:3416`＋`tmp:kb:2913`＋`tmp:kb:3207` | 金額不一致被退回、多繳退還、少繳補繳都是「錢數對不上」的處理，主題與轉帳失敗不同。 | |
| `jgb/E/payment-failure-troubleshooting`《租客繳不了費／轉帳或刷卡一直失敗怎麼排查》 | `tmp:kb:3502`＋`tmp:kb:3924`＋`tmp:kb:3933`＋`tmp:kb:3500` | 收回重發、一元測試、額度上限、信用卡失敗查後端的排查順序自成一體，與帳號用法說明分開；3933 空內文只當入口。 | |
| `jgb/E/payment-fees-and-sms`《金流手續費誰負擔、費率多少與帳單簡訊是否收費》 | `tmp:kb:3346`＋`tmp:kb:3551`＋`tmp:kb:3337` | 「這些要不要錢、誰付」的成本歸屬提問合為一處；3337 簡訊不另收費僅一角度出架，依契約留 E。 | |
| `jgb/E/payment-gateway-options`《金流廠商差別、支援付款方式與申請條件》 | `tmp:kb:tmp:canon:jgb/E/payment-gateway-options`＋`tmp:kb:3413` | 「哪家金流差在哪、誰能申請、各家支援什麼付款方式」同題，3413 各家特性併入；實際申請與參數綁定是操作路徑，另立細目。 | |
| `jgb/E/payment-gateway-setup`《線上金流怎麼申請與綁定（藍新／永豐／國泰／中信、只能一家、收款帳戶銀行、一元測試）》 | `tmp:kb:3548`＋`tmp:kb:3549`＋`tmp:kb:3550`＋`tmp:kb:3555`＋`tmp:kb:3942`＋`tmp:kb:3930`＋`tmp:kb:3554`＋`tmp:kb:4221`＋`tmp:kb:tmp:draft:1` | 「收款帳戶怎麼綁、金流怎麼申請、只能綁一家、撥付帳戶有無銀行限制、新帳戶怎麼測」是同一操作路徑；3942 空內文只當入口；draft:1 只取金流開通段落。 | |
| `jgb/E/periodic-bill-generation`《週期帳單何時產生、三種建立方式與續約／補簽起算》 | `tmp:kb:3399`＋`tmp:kb:3401`＋`tmp:kb:3928`＋`tmp:kb:3935`＋`tmp:kb:3857`＋`tmp:kb:3941` | 「這期帳單怎麼還沒出來／要開始收租怎麼設定」答案都是週期選項、提前一個月產生、續約與補簽補產的產生規則；3935、3941 空內文只當入口。 | |
| `jgb/E/prepaid-meter-topup-billing`《儲值電表的儲值帳單、入帳與電費預付收取》 | `tmp:kb:3353`＋`tmp:kb:3459`＋`tmp:kb:4053`＋`tmp:kb:4086` | 儲值產生帳單並付款入帳屬「錢怎麼進來」，租客儲值教學與預付制併入；未復電與單價設定屬裝置端，出架至 G。 | |
| `jgb/E/rent-amount-calculation`《租金金額怎麼算（以合約租金快照為準、不足月按比例）》 | `tmp:kb:3397`＋`tmp:kb:3895`＋`tmp:kb:3934` | 「帳單金額跟預期不一樣／改了刊登價為何帳單沒變」答案都是租金來源與比例規則，與水電算法主題不同；3934 空內文只當入口。 | |
| `jgb/E/rent-market-discount-tax`《租金行情、折扣條件與公益出租人減稅（租客視角）》 | `tmp:kb:2909`＋`tmp:kb:2925`＋`tmp:kb:2920`＋`tmp:kb:3011` | 四則都在回答「租金水準為何如此」，各自不成獨立主題、合為一段；僅一角度出架至 D，依契約留 E。 | |
| `jgb/E/tenant-cannot-see-bill`《租客說看不到帳單（可見三條件與信箱錯配）》 | `tmp:kb:3927`＋`tmp:kb:3936` | 業者視角的排查題，答案是可見三條件與合約信箱錯配；3936 空內文只當入口。 | |
| `jgb/E/tenant-online-payment-steps`《租客線上繳費操作步驟（信用卡、虛擬 ATM）》 | `tmp:kb:3443`＋`tmp:kb:tmp:draft:5`＋`tmp:kb:tmp:draft:6`＋`tmp:kb:tmp:draft:7` | 各金流別的租客付款教學都是「怎麼付」的操作步驟，近重複合併；線下匯款通知歸現金收款細目。 | |
| `jgb/E/tenant-payment-methods`《租客有哪些繳費方式、繳費日與通道怎麼調整（團隊層／合約層）》 | `tmp:kb:3408`＋`tmp:kb:4256`＋`tmp:kb:4268`＋`tmp:kb:4288`＋`tmp:kb:4289`＋`tmp:kb:2918` | 可用通道清單、兩層設定與繳費日依合約是「租客能怎麼繳」的同一答案；三筆模板講法近重複合併。 | |
| `jgb/E/tenant-view-bills`《租客在哪裡看帳單、繳費狀態與付款入口》 | `tmp:kb:3447`＋`tmp:kb:4223` | 租客視角「帳單在哪裡看」獨立可答，與業者排查「租客看不到」分開。 | |
| `jgb/E/utility-meter-billing-and-reading`《水電計費方式與度數（六種電費模式、度數×單價、夏季電價、度數登記錯誤重算）》 | `tmp:kb:4217`＋`tmp:kb:3352`＋`tmp:kb:3398`＋`tmp:kb:4222`＋`tmp:kb:4265`＋`tmp:kb:4282`＋`tmp:kb:4283`＋`tmp:kb:4285` | 合約層水電收費模式與抄表度數怎麼算出帳單列，是業者操作層一題；四筆空內文只當入口。 | |
| `jgb/E/utility-split-calculation`《水電與公共費用怎麼分算（依合約）》 | `tmp:kb:tmp:canon:jgb/E/utility-split-calculation`＋`tmp:kb:2911` | 售前與租客視角同答「依合約分算」，2911 公共費用分攤併入；計費模式設定、度數與電價的操作層另見 utility-meter-billing-and-reading。 | |
| `jgb/E/virtual-account-prepaid`《固定虛擬帳號與儲值金抵扣是什麼、跟一般虛擬帳號差在哪》 | `tmp:kb:tmp:canon:jgb/E/virtual-account-prepaid`＋`tmp:kb:3539` | 「固定帳號會不會過期、和一般帳號差別」是概念題併入既有細目；開通、模式權限、入帳沖銷與歷程查詢是業者操作，另立細目。 | |
| `jgb/E/virtual-account-transfer`《虛擬帳號轉帳怎麼繳、效期、臨櫃匯款、逾期後可否繳與用帳號查交易》 | `tmp:kb:3410`＋`tmp:kb:3344`＋`tmp:kb:3925`＋`tmp:kb:4651`＋`tmp:kb:4637` | 各家效期、永豐帳號格式、臨櫃可行方式、逾期後仍可繳、帳單總表以虛擬帳號回查是同一種一次性帳號的用法；⚠ 效期材料矛盾（3410 藍新 180 天／永豐約 7 天／國泰無時限，3539 一般 3–7 天，4651 可沿用很長）只標不裁。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| audience_level：既有 bill-contents-extra-fees 只 keep（售前），另立 PM 版 bill-fee-items-and-edit | 品項清單與自訂品項的答案不因受眾而異，依「不得同時存在中立細目與受眾版細目」併入既有細目（兩角度採 merge）。 | |
| audience_level：既有 einvoice-issuing 只 keep，另立 invoice-issuing-timing-and-types | 開立時機、載具與一物件一發票是同一命題、答案不因受眾而異，併入既有細目（兩角度採 merge）。 | |
| audience_level：既有 overdue-reminder-late-fee 只 keep，另立 overdue-bill-marking-and-auto-notice | 逾期標示與催繳通知條件就是「逾期怎麼被提醒」的同一答案，併入既有細目（兩角度採 merge）。 | |
| content_boundary：把金流申請與參數綁定（3548/3549/3550/3555/3554/4221/3930/3942）全併入既有 payment-gateway-options | 「選哪家」是售前比較、「怎麼綁參數」是業者操作路徑，兩角度分立，故另立 payment-gateway-setup。 | |
| content_boundary：把水電計費模式、度數與電價全併入既有 utility-split-calculation | 「依合約分算」是能力層、六種模式與抄表更正是操作層，兩角度分立，另立 utility-meter-billing-and-reading。 | |
| content_boundary：把固定虛擬帳號開通／模式／沖銷／歷程（3417/3540/3541/3542）全併入既有 virtual-account-prepaid | 概念題與業者管理操作分屬不同層級，兩角度分立，另立 fixed-virtual-account-management。 | |
| audience_level：3539（固定帳號不過期、與一般帳號差別）歸 fixed-virtual-account-management | 是概念比較而非操作，兩角度歸既有 virtual-account-prepaid。 | |
| content_boundary：把「已付款但狀態沒更新」（3497/3931/3932）併入 bill-status-reconciliation | 故障排查入口與狀態流程說明是不同提問路徑，兩角度分立為 paid-but-status-not-updated。 | |
| audience_level：把線下匯款雙端流程（draft:8/10/11/13/14、draft:4、3499、3361）獨立為 offline-payment-notify-and-manual-reconcile | 線上／線下差異與手動到帳歸狀態流程，租客通知已匯款歸現金收款帳戶細目，分別由兩角度多數支持，不另設第三個細目。 | |
| content_boundary：draft:10、draft:14 歸 bill-status-reconciliation；user_question_path 亦同 | 兩則是線下匯款後租客通知與追蹤，與 3552 現金帳戶收款流程同一條線，採 content_boundary／audience_level 多數歸 cash-bank-account-collection。 | |
| content_boundary：draft:4 歸 recurring-bill-generation；audience_level 歸 offline | draft:4 核心是既存合約歷史帳單手動移至已到帳，採 user_question_path 歸 bill-status-reconciliation。 | |
| audience_level：3485 歸 bill-creation-methods、3401/3941 歸 bill-creation-methods | 3485 是發送→應到帳→待對帳→已到帳流程（兩角度歸狀態流程）；3401 三種建立方式與 3941 入口兩角度歸週期產生規則。 | |
| audience_level：把批次匯入（3404/4638）獨立為 bill-batch-import-excel | 批次匯入與單筆手動新增同屬人工開帳單操作，兩角度合為一題 manual-bill-creation。 | |
| audience_level：4649（租客直接匯款補建帳單紀錄）歸 prepaid-meter-topup-billing | 答案是到待發送帳單手動新增一筆，屬手動建單操作（兩角度）。 | |
| content_boundary：把收回／取消與封存合為 bill-recall-cancel-archive | 收回是發送中的帳單退回待發送，封存是退租後多餘帳單退場，兩角度分立為 bill-recall-cancel 與 bill-archive-after-termination。 | |
| audience_level：3403 整筆歸 bill-recall-and-cancel；user_question_path 整筆歸 bill-scheduled-auto-send | 3403 前半講排定發送、後半講收回，採 content_boundary 拆分到兩細目。 | |
| user_question_path：3553 整筆歸 bill-format-customize；audience_level 整筆歸 bill-auto-send-schedule | 3553 同時含收訖章／收據類型與自動排程發送，採 content_boundary 拆分到兩細目。 | |
| user_question_path／audience_level：draft:1 整筆歸金流申請細目 | draft:1 為收款設置全篇教學，含金流開通、現金帳戶、排定發送、收據與收款章四段，採 content_boundary 四向拆分。 | |
| audience_level：3478（邀請租客訂閱通知）歸 bill-send-failure | 訂閱通知是讓租客收到繳費提醒的投遞管道，兩角度歸 overdue-reminder-late-fee。 | |
| content_boundary：3337（帳單簡訊不收費）歸 overdue-reminder-late-fee；audience_level 出架至 I | 「要不要另外付錢」是成本歸屬問題，隨手續費歸 payment-fees-and-sms；僅一角度出架，依契約留 E。 | |
| audience_level：2909/2925/2920/3011 出架至 D、3326 出架至 I | 僅一角度出架，依契約留 E，採兩角度的租客視角細目。 | |
| audience_level：3554／4221 歸 receiving-account-and-payment-method-config；content_boundary 歸 payment-gateway-options | 只能綁一家與收款帳戶銀行限制是綁定操作的規則，採 user_question_path 歸 payment-gateway-setup，不另設設定總表細目。 | |
| audience_level：4256（調整收款方式兩層設定）歸 receiving-account-and-payment-method-config | 兩角度歸 tenant-payment-methods：通道開關就是「租客能怎麼繳」的答案。 | |
| content_boundary：3443、draft:5 歸 tenant-payment-methods；audience_level：draft:5 歸 tenant-payment-channels、3409 歸 steps | 3443 與 draft:5 是逐步付款教學，歸 tenant-online-payment-steps；3409 是刷卡流程說明，兩角度歸既有 credit-card-rent-payment。 | |
| content_boundary：draft:6／draft:7 歸 virtual-account-atm-transfer | 兩則是租客付款操作教學，兩角度歸 tenant-online-payment-steps。 | |
| user_question_path：1391/4281/2918 併入 rent-payment-info-tenant 細目；content_boundary 併入 tenant-payment-methods | 1391/4281 是個別金額查詢，依契約列 out_of_shelf（face 資料查詢）；2918 依租約繳費期限的通用答案歸 tenant-payment-methods。 | |
| user_question_path：另立 parking-fee-inquiry（1394/4261/4275）；content_boundary 把 4261/4275 併入 bill-contents 當品項入口 | 停車費三筆皆為個別金額查詢（1394 內文即要車位編號查詢），依契約列 out_of_shelf（face 資料查詢）。 | |
| user_question_path／content_boundary：1388、1393、4640 併入水電／管理費／收據細目當入口 | 三筆為查自己的電費、管理費、收據金額，屬個別金額查詢，依契約列 out_of_shelf（face 資料查詢）。 | |
| content_boundary：4047／4564（儲值後未復電）併入 prepaid-meter-topup-billing | 兩角度出架至 G，取多數：復電是裝置端入值問題。 | |
| content_boundary：3500（信用卡付款失敗）併入既有 credit-card-rent-payment | 付款失敗屬排查題，兩角度歸 payment-failure-troubleshooting。 | |
| content_boundary：4651 拆分（年繳拆分段歸 recurring-bill-generation） | 4651 兩段都短且以逾期帳號可否繳為主，兩角度整筆歸 virtual-account-transfer，不拆。 | |
| user_question_path：4637（帳單總表以虛擬帳號查交易）歸 bill-query-reports-export | 查交易是虛擬帳號用法的一環，兩角度歸 virtual-account-transfer。 | |
| audience_level：4657（查點退金額）併入 overdue-bill-followup-scope | 點退金額的答案是點退帳單算法，兩角度歸 checkout-bill-settlement。 | |
| audience_level：3423（發票補開）歸 invoice-not-issued-troubleshooting | 補開與作廢是成對修正動作，兩角度歸 invoice-void-reissue。 | |
| user_question_path：差額發票拆為 differential-invoice-setup 與 differential-invoice-amount | 群組底租設定與金額結轉互相依賴，兩角度合為一題 differential-invoice。 | |
| audience_level：3366（繳費成功 繳費紀錄）歸 tenant-view-bills-and-pay-entry | 空內文入口，題意是繳費成功後的狀態，兩角度歸 bill-status-reconciliation。 | |
| content_boundary：3447/4223 與 3927/3936 合為 tenant-bill-visibility | 租客「在哪看」與業者排查「為什麼看不到」是不同提問路徑，兩角度分立。 | |
| content_boundary：bill-status-reconciliation、periodic-bill-generation、bill-scheduled-send、tenant-payment-methods 等操作細目 target_user 含 prospect | 多數角度判為業者操作層，只有 bill-status-reconciliation 因含「線上 vs 線下最大差異」售前命題保留雙受眾。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 48 | 0 | 0 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/E/bill-archive-after-termination` | merge |
| `jgb/E/bill-contents-extra-fees` | merge |
| `jgb/E/bill-format-customize` | merge+split-child |
| `jgb/E/bill-recall-cancel` | merge+split-child |
| `jgb/E/bill-receipt-pdf` | merge |
| `jgb/E/bill-reports-export` | merge |
| `jgb/E/bill-scheduled-auto-send` | merge+split-child |
| `jgb/E/bill-send-failure` | merge |
| `jgb/E/bill-status-reconciliation` | merge |
| `jgb/E/cash-bank-account-collection` | merge+split-child |
| `jgb/E/checkout-bill-settlement` | merge |
| `jgb/E/convenience-store-payment` | merge |
| `jgb/E/credit-card-auto-debit` | merge |
| `jgb/E/credit-card-rent-payment` | merge |
| `jgb/E/deposit-imputed-interest` | merge |
| `jgb/E/differential-invoice` | merge |
| `jgb/E/einvoice-issuing` | merge |
| `jgb/E/fixed-virtual-account-management` | merge |
| `jgb/E/invoice-not-issued-troubleshooting` | merge |
| `jgb/E/invoice-void-reissue` | merge |
| `jgb/E/late-fee-calculation` | merge |
| `jgb/E/management-fee` | merge |
| `jgb/E/manual-bill-creation` | merge |
| `jgb/E/overdue-bill-followup-scope` | merge |
| `jgb/E/overdue-reminder-late-fee` | merge |
| `jgb/E/paid-but-status-not-updated` | merge |
| `jgb/E/payment-amount-mismatch` | merge |
| `jgb/E/payment-failure-troubleshooting` | merge |
| `jgb/E/payment-fees-and-sms` | merge |
| `jgb/E/payment-gateway-options` | merge |
| `jgb/E/payment-gateway-setup` | merge+split-child |
| `jgb/E/periodic-bill-generation` | merge |
| `jgb/E/prepaid-meter-topup-billing` | merge |
| `jgb/E/rent-amount-calculation` | merge |
| `jgb/E/rent-market-discount-tax` | merge |
| `jgb/E/tenant-cannot-see-bill` | merge |
| `jgb/E/tenant-online-payment-steps` | merge |
| `jgb/E/tenant-payment-methods` | merge |
| `jgb/E/tenant-view-bills` | merge |
| `jgb/E/utility-meter-billing-and-reading` | merge |
| `jgb/E/utility-split-calculation` | merge |
| `jgb/E/virtual-account-prepaid` | merge |
| `jgb/E/virtual-account-transfer` | merge |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

| 舊細目 | 子細目數 |
|---|---|
| `tmp:kb:3403` | 2 |
| `tmp:kb:3553` | 2 |
| `tmp:kb:tmp:draft:1` | 4 |
