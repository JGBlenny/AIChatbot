# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/D/contract-batch-renewal` | 續約能不能批次處理 | `jgb/D/contract-batch-renewal` | 續約能不能批次處理（含快速日期設定、紙本上傳、通知分流） | merge | D/D/D | |
| 2 | `tmp:canon:jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | `jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | merge | D/D/D | |
| 3 | `tmp:canon:jgb/D/contract-history-retention` | 歷史合約保留多久（含點退狀態） | `jgb/D/contract-history-retention` | 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程） | merge | D/D/D | |
| 4 | `tmp:canon:jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 5 | `tmp:canon:jgb/D/contract-templates` | 合約範本有哪些可以選 | `jgb/D/contract-templates` | 合約範本有哪些可以選（含內文隨內政部新制更新） | merge | D/D/D | |
| 6 | `tmp:canon:jgb/D/lease-expiry-followup-scope` | 合約到期追問可答範圍（導向續約面向） | `jgb/D/lease-expiry-followup-scope` | 合約到期追問可答範圍與到期提醒（導向續約面向） | merge | D/D/D | |
| 7 | `tmp:canon:jgb/D/sublease-vs-management-contract` | 包租與代管在委託合約設定上的差別 | `jgb/D/sublease-vs-management-contract` | 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整） | merge | D/D/D | |
| 8 | `tmp:draft:10` | 如何寄送合約邀請？ | `jgb/D/contract-send-invite` | 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整） | split | D/D/D | |
| 9 | `tmp:draft:10` | 如何寄送合約邀請？ | `jgb/D/esign-invite-expiry` | 簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長 | split | D/D/D | |
| 10 | `tmp:draft:11` | 租客簽約後如何更改？ | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 11 | `tmp:draft:12` | 管理者如何快速找到點交、點退與押金狀態的物件？ | `jgb/D/contract-filter-by-state` | 依合約狀態篩選物件（點交點退、待退押金、本月到期、無合約） | new | D/D/D | |
| 12 | `tmp:draft:13` | 點退押金的找補費用在哪裡操作呢？ | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 13 | `tmp:draft:14` | 點退需要在租約30天內到期時，才能操作 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 14 | `tmp:draft:15` | 提前解約後何時可以進行點退？ | `jgb/D/early-termination-aftermath` | 提前解約生效後：何時可點退、違約金與押金一併結算、之後還要處理什麼 | new | D/D/D | |
| 15 | `tmp:draft:16` | 租客會收到什麼形式的簽約邀請？是否有時效？ | `jgb/D/contract-send-invite` | 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整） | new | D/D/D | |
| 16 | `tmp:draft:17` | 點退押金在做什麼？ | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 17 | `tmp:draft:18` | 如何新增合約？ | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 18 | `tmp:draft:19` | 租客該如何簽約？ | `jgb/D/tenant-sign-steps` | 租客收到簽約邀請後的簽署步驟（租客視角） | new | D/D/D | |
| 19 | `tmp:draft:2` | 房東教學04：合約篇 | `jgb/D/contract-batch-renewal` | 續約能不能批次處理（含快速日期設定、紙本上傳、通知分流） | split | D/D/D | |
| 20 | `tmp:draft:2` | 房東教學04：合約篇 | `jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | split | D/D/D | |
| 21 | `tmp:draft:2` | 房東教學04：合約篇 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | split | D/D/D | |
| 22 | `tmp:draft:2` | 房東教學04：合約篇 | `jgb/D/handover-checkin` | 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 | split | D/D/D | |
| 23 | `tmp:draft:2` | 房東教學04：合約篇 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | split | D/D/D | |
| 24 | `tmp:draft:2` | 房東教學04：合約篇 | `jgb/D/upload-existing-contract` | 上傳既存（紙本）合約：適用情境、效力、入口、檔案上限 | split | D/D/D | |
| 25 | `tmp:draft:20` | 租客沒有上傳身分證，請問該怎麼辦？ | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 26 | `tmp:draft:21` | 租客資料卡：查看聯絡方式與一鍵聯繫 | `jgb/D/contract-lookup` | 查詢合約資訊：以合約編號／物件名稱查、不能用租客姓名反查、租客資料卡 | new | ⚠️ ?/D/D | |
| 27 | `tmp:draft:3` | 一分鐘上手 如何建立＆編輯合約 | `jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | merge | D/D/D | |
| 28 | `tmp:draft:5` | 合約附件、補充條款限制 | `jgb/D/contract-attachments-notes-limits` | 合約附件上傳、備註 50 行與補充條款限制 | new | D/D/D | |
| 29 | `tmp:draft:6` | 已點退的合約還在執行中？ | `jgb/D/contract-history-retention` | 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程） | merge | D/D/D | |
| 30 | `tmp:draft:7` | 租約公證？房東房客都應該關注的保障 | `jgb/D/lease-notarization` | 租約公證：是什麼、去哪辦、費用、對房東房客的保障、與租補關係、公證合約如何上傳 | new | D/D/D | |
| 31 | `tmp:draft:8` | 未刊登的物件也可以新增合約嗎？ | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 32 | `tmp:draft:9` | 編輯合約要從哪邊進入？ | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 33 | `tmp:kb:1392` | 押金金額和退還方式查詢 | `jgb/D/deposit-setting-and-refund-system` | 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算） | new | D/D/D | |
| 34 | `tmp:kb:2898` | 租賃契約續約 | `jgb/D/tenant-renewal-and-extension-rights` | 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助 | new | D/D/D | |
| 35 | `tmp:kb:2901` | 押金上限 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 36 | `tmp:kb:2903` | 違約責任 | `jgb/D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | new | D/D/D | |
| 37 | `tmp:kb:2916` | 押金 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 38 | `tmp:kb:2924` | 租金支付法律依據 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 39 | `tmp:kb:2926` | 押金規定 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 40 | `tmp:kb:2927` | 押金扣除 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 41 | `tmp:kb:2928` | 寵物押金 | `jgb/D/tenant-pet-clauses` | 租約中的寵物押金與飼養寵物費用 | new | D/D/D | |
| 42 | `tmp:kb:2929` | 押金利息 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 43 | `tmp:kb:2930` | 押金用途說明 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 44 | `tmp:kb:2931` | 押金扣除爭議 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 45 | `tmp:kb:2932` | 押金轉讓 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 46 | `tmp:kb:2933` | 押金保管責任 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 47 | `tmp:kb:2934` | 押金條款 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 48 | `tmp:kb:2935` | 押金支付方式 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 49 | `tmp:kb:2936` | 押金約定 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 50 | `tmp:kb:2937` | 押金用途 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 51 | `tmp:kb:2938` | 入住注意事項 | `jgb/D/move-in-inspection` | 入住注意事項與傢俱清點 | new | D/D/D | |
| 52 | `tmp:kb:2939` | 退租注意事項 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 53 | `tmp:kb:2940` | 退租義務 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 54 | `tmp:kb:2941` | 原狀回復要求 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 55 | `tmp:kb:2942` | 傢俱清點 | `jgb/D/move-in-inspection` | 入住注意事項與傢俱清點 | new | D/D/D | |
| 56 | `tmp:kb:2943` | 退租清潔標準 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 57 | `tmp:kb:2944` | 退租清潔要求 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 58 | `tmp:kb:2945` | 租約延住 | `jgb/D/tenant-renewal-and-extension-rights` | 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助 | new | D/D/D | |
| 59 | `tmp:kb:2946` | 延住規定 | `jgb/D/tenant-renewal-and-extension-rights` | 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助 | new | D/D/D | |
| 60 | `tmp:kb:2947` | 遺留物品處理 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 61 | `tmp:kb:2948` | 退租物品處理 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 62 | `tmp:kb:2949` | 終止租約通知 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 63 | `tmp:kb:2950` | 租約到期物品處理 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 64 | `tmp:kb:2951` | 提前通知 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 65 | `tmp:kb:2952` | 搬遷要求 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 66 | `tmp:kb:2953` | 提前終止租約 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 67 | `tmp:kb:2954` | 違約金上限 | `jgb/D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | new | D/D/D | |
| 68 | `tmp:kb:2955` | 提前解約通知 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 69 | `tmp:kb:2956` | 租約處理 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 70 | `tmp:kb:2957` | 租約有效性 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 71 | `tmp:kb:2958` | 提前解約規定 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 72 | `tmp:kb:2959` | 租約終止 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 73 | `tmp:kb:2960` | 違約金計算 | `jgb/D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | new | D/D/D | |
| 74 | `tmp:kb:2961` | 提前解約證據 | `jgb/D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | new | D/D/D | |
| 75 | `tmp:kb:2962` | 提前解約法律後果 | `jgb/D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | new | D/D/D | |
| 76 | `tmp:kb:2977` | 飼養寵物費用 | `jgb/D/tenant-pet-clauses` | 租約中的寵物押金與飼養寵物費用 | new | D/D/D | |
| 77 | `tmp:kb:2989` | 設備使用規範 | `jgb/D/equipment-usage-under-lease` | 租約中的設備與公共設備使用規範 | new | D/D/D | |
| 78 | `tmp:kb:3006` | 租屋保險費用 | `jgb/D/tenant-rental-insurance` | 租屋相關保險：租屋保險費用、租客設備投保、押金投保 | new | D/D/D | |
| 79 | `tmp:kb:3021` | 押金法律規定 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 80 | `tmp:kb:3022` | 終止租約 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 81 | `tmp:kb:3028` | 租屋合約變更 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 82 | `tmp:kb:3034` | 合約條款解釋 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 83 | `tmp:kb:3035` | 戶籍遷移 | `jgb/D/household-registration-under-lease` | 租屋期間戶籍遷移與居住證明 | new | D/D/D | |
| 84 | `tmp:kb:3043` | 戶籍登記與租約 | `jgb/D/household-registration-under-lease` | 租屋期間戶籍遷移與居住證明 | new | D/D/D | |
| 85 | `tmp:kb:3047` | 居住證明費用 | `jgb/D/household-registration-under-lease` | 租屋期間戶籍遷移與居住證明 | new | D/D/D | |
| 86 | `tmp:kb:3077` | 押金處理 | `jgb/D/sublease-and-shared-lease-terms` | 轉租與分租的租約條款與押金處理 | new | D/D/D | |
| 87 | `tmp:kb:3078` | 轉租租約條款 | `jgb/D/sublease-and-shared-lease-terms` | 轉租與分租的租約條款與押金處理 | new | D/D/D | |
| 88 | `tmp:kb:3079` | 分租租約條款 | `jgb/D/sublease-and-shared-lease-terms` | 轉租與分租的租約條款與押金處理 | new | D/D/D | |
| 89 | `tmp:kb:3089` | 租約類型差異 | `jgb/D/sublease-vs-management-contract` | 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整） | merge | D/D/D | |
| 90 | `tmp:kb:3090` | 押金管理差異 | `jgb/D/sublease-vs-management-contract` | 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整） | merge | D/D/D | |
| 91 | `tmp:kb:3093` | 租約終止條件 | `jgb/D/sublease-vs-management-contract` | 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整） | merge | D/D/D | |
| 92 | `tmp:kb:3094` | 租金調整政策 | `jgb/D/sublease-vs-management-contract` | 包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整） | merge | D/D/D | |
| 93 | `tmp:kb:3114` | 委託管理合約 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 94 | `tmp:kb:3115` | 委託管理合約期限 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 95 | `tmp:kb:3116` | 委託管理合約終止 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 96 | `tmp:kb:3117` | 管理費用計算 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 97 | `tmp:kb:3118` | 合約變更 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 98 | `tmp:kb:3119` | 續約流程 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 99 | `tmp:kb:3120` | 委託管理合約違約責任 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 100 | `tmp:kb:3121` | 管理師責任 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 101 | `tmp:kb:3122` | 委託管理合約權利 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 102 | `tmp:kb:3123` | 管理費用支付方式 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 103 | `tmp:kb:3124` | 終止合約程序 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 104 | `tmp:kb:3125` | 委託管理合約法律 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 105 | `tmp:kb:3126` | 合約爭議解決 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 106 | `tmp:kb:3131` | 社會住宅與租約差異 | `jgb/D/social-housing-lease` | 社會住宅租約與一般租約的差異、期限與終止 | new | D/D/D | |
| 107 | `tmp:kb:3132` | 社會住宅租約期限 | `jgb/D/social-housing-lease` | 社會住宅租約與一般租約的差異、期限與終止 | new | D/D/D | |
| 108 | `tmp:kb:3134` | 社會住宅租約終止 | `jgb/D/social-housing-lease` | 社會住宅租約與一般租約的差異、期限與終止 | new | D/D/D | |
| 109 | `tmp:kb:3147` | 租約管理服務 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 110 | `tmp:kb:3153` | 租約續約 | `jgb/D/tenant-renewal-and-extension-rights` | 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助 | new | D/D/D | |
| 111 | `tmp:kb:3154` | 押金管理 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 112 | `tmp:kb:3158` | 服務費用計算 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 113 | `tmp:kb:3159` | 合約條款 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 114 | `tmp:kb:3171` | 押金與損壞賠償 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 115 | `tmp:kb:3191` | 設備處理 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 116 | `tmp:kb:3196` | 公共設備使用限制 | `jgb/D/equipment-usage-under-lease` | 租約中的設備與公共設備使用規範 | new | ⚠️ ?/D/D | |
| 117 | `tmp:kb:3201` | 公共設備使用規範 | `jgb/D/equipment-usage-under-lease` | 租約中的設備與公共設備使用規範 | new | ⚠️ ?/D/D | |
| 118 | `tmp:kb:3202` | 租客設備投保 | `jgb/D/tenant-rental-insurance` | 租屋相關保險：租屋保險費用、租客設備投保、押金投保 | new | D/D/D | |
| 119 | `tmp:kb:3204` | 續約規定 | `jgb/D/tenant-renewal-and-extension-rights` | 租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助 | new | D/D/D | |
| 120 | `tmp:kb:3209` | 租金包含服務 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 121 | `tmp:kb:3210` | 租金爭議解決 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 122 | `tmp:kb:3211` | 押金抵扣租金 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 123 | `tmp:kb:3212` | 押金爭議解決 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 124 | `tmp:kb:3213` | 押金管理責任 | `jgb/D/deposit-deduction-refund` | 押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理 | new | D/D/D | |
| 125 | `tmp:kb:3214` | 押金投保 | `jgb/D/tenant-rental-insurance` | 租屋相關保險：租屋保險費用、租客設備投保、押金投保 | new | D/D/D | |
| 126 | `tmp:kb:3215` | 押金使用規定 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 127 | `tmp:kb:3216` | 原狀回復義務 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 128 | `tmp:kb:3217` | 租約終止通知 | `jgb/D/lease-termination-notice-rules` | 終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤） | new | D/D/D | |
| 129 | `tmp:kb:3218` | 租客物品處理 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 130 | `tmp:kb:3239` | 租約條款解釋 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 131 | `tmp:kb:3259` | 委託管理合約服務 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 132 | `tmp:kb:3260` | 委託管理合約權益 | `jgb/D/delegation-contract-terms-general` | 委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律 | new | D/D/D | |
| 133 | `tmp:kb:3261` | 委託管理合約轉讓 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 134 | `tmp:kb:3273` | 設備狀況處理 | `jgb/D/tenant-move-out-obligations` | 退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出 | new | D/D/D | |
| 135 | `tmp:kb:3284` | 押金相關法律 | `jgb/D/deposit-legal-limits` | 押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租 | new | D/D/D | |
| 136 | `tmp:kb:3285` | 提前解約後果 | `jgb/D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | new | D/D/D | |
| 137 | `tmp:kb:3290` | 租屋設備使用規範 | `jgb/D/equipment-usage-under-lease` | 租約中的設備與公共設備使用規範 | new | D/D/D | |
| 138 | `tmp:kb:3294` | 租屋合約違約責任 | `jgb/D/breach-penalty-rules` | 違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留 | new | D/D/D | |
| 139 | `tmp:kb:3296` | 租屋合約條款解釋 | `jgb/D/lease-clauses-interpretation` | 租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議） | new | D/D/D | |
| 140 | `tmp:kb:3316` | 委託管理合約責任 | `jgb/D/delegation-contract-change-termination` | 委託管理合約的變更、續約、終止、轉讓、違約與爭議解決 | new | D/D/D | |
| 141 | `tmp:kb:3318` | 租約期限 | `jgb/D/social-housing-lease` | 社會住宅租約與一般租約的差異、期限與終止 | new | D/D/D | |
| 142 | `tmp:kb:3328` | 合約審閱期 72小時 | `jgb/D/esign-legal-validity` | 電子合約法律效力、簽章認證與 72 小時審閱期 | new | D/D/D | |
| 143 | `tmp:kb:3329` | 合約延長 付款方式變更 續約條件變更 | `jgb/D/renewal-vs-new-contract` | 系統續約 vs 重建新約的取捨（條件變更、租屋補助審核） | new | D/D/D | |
| 144 | `tmp:kb:3330` | 歷史合約 保存期限 | `jgb/D/contract-history-retention` | 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程） | merge | D/D/D | |
| 145 | `tmp:kb:3331` | 合約簽約邀請 期限 過期 | `jgb/D/esign-invite-expiry` | 簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長 | new | D/D/D | |
| 146 | `tmp:kb:3332` | 合約建立 中途離開 未儲存 | `jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | merge | D/D/D | |
| 147 | `tmp:kb:3333` | 續約 租屋補助 租補過審 | `jgb/D/renewal-vs-new-contract` | 系統續約 vs 重建新約的取捨（條件變更、租屋補助審核） | new | D/D/D | |
| 148 | `tmp:kb:3334` | 委託約 租賃約 差異 | `jgb/D/delegation-vs-lease-contract` | 委託約與租賃約的差別（系統分開管理） | new | D/D/D | |
| 149 | `tmp:kb:3368` | 合約簽約邀請 發送邀請 為什麼不能發送 | `jgb/D/contract-send-invite` | 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整） | new | D/D/D | |
| 150 | `tmp:kb:3370` | 合約提前解約 可以解約嗎 提前終止 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 151 | `tmp:kb:3371` | 合約續約 可以續約嗎 延長合約 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 152 | `tmp:kb:3372` | 合約狀態查詢 目前狀態 | `jgb/D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | new | D/D/D | |
| 153 | `tmp:kb:3373` | 合約狀態 12 階段總覽 | `jgb/D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | new | D/D/D | |
| 154 | `tmp:kb:3374` | 合約建立 發送簽約邀請 | `jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | merge | D/D/D | |
| 155 | `tmp:kb:3375` | 合約簽署流程 雙方簽名 | `jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | merge | D/D/D | |
| 156 | `tmp:kb:3376` | 合約點交流程 搬入 | `jgb/D/handover-checkin` | 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 | new | D/D/D | |
| 157 | `tmp:kb:3377` | 合約點交需要哪些條件 點交前置條件說明 | `jgb/D/handover-checkin` | 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 | new | D/D/D | |
| 158 | `tmp:kb:3378` | 合約點退流程 搬出 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 159 | `tmp:kb:3379` | 合約點退 前置條件 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 160 | `tmp:kb:3380` | 提前解約 合約未到期退租 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 161 | `tmp:kb:3381` | 提前解約 租客發起 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 162 | `tmp:kb:3382` | 提前解約 房東發起 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 163 | `tmp:kb:3383` | 合約續約 流程步驟 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 164 | `tmp:kb:3384` | 合約續約 前置條件 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 165 | `tmp:kb:3385` | 歷史合約 過期與結案 | `jgb/D/contract-history-retention` | 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程） | merge | D/D/D | |
| 166 | `tmp:kb:3386` | 合約取消 與歷史合約差異 | `jgb/D/contract-cancel-delete` | 合約刪除、取消、作廢的條件與取消 vs 歷史合約差異 | new | D/D/D | |
| 167 | `tmp:kb:3387` | 押金計算 兩種模式 | `jgb/D/deposit-setting-and-refund-system` | 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算） | new | D/D/D | |
| 168 | `tmp:kb:3388` | 合約即將到期 到期提醒 | `jgb/D/lease-expiry-followup-scope` | 合約到期追問可答範圍與到期提醒（導向續約面向） | merge | D/D/D | |
| 169 | `tmp:kb:3389` | 合約執行中 包含狀態 | `jgb/D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | new | D/D/D | |
| 170 | `tmp:kb:3390` | 合約 PDF 下載 各種文件 | `jgb/D/contract-pdf-download` | 合約相關 PDF 下載（合約書、摘要、點交／點退清單、提前解約文件） | new | D/D/D | |
| 171 | `tmp:kb:3392` | 簽約連結打不開 電子簽章失敗 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 172 | `tmp:kb:3393` | 合約附件 上傳管理 | `jgb/D/contract-attachments-notes-limits` | 合約附件上傳、備註 50 行與補充條款限制 | new | D/D/D | |
| 173 | `tmp:kb:3394` | 合約複製 快速建立 | `jgb/D/contract-copy` | 合約複製快速建立相似合約 | new | D/D/D | |
| 174 | `tmp:kb:3440` | 簽約身份管理 個人法人 | `jgb/D/signer-identity-and-seal` | 簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法 | new | D/D/D | |
| 175 | `tmp:kb:3442` | 收到簽約邀請 簽署步驟 | `jgb/D/tenant-sign-steps` | 租客收到簽約邀請後的簽署步驟（租客視角） | new | D/D/D | |
| 176 | `tmp:kb:3471` | 委託合約 與出租合約差異 | `jgb/D/delegation-vs-lease-contract` | 委託約與租賃約的差別（系統分開管理） | new | D/D/D | |
| 177 | `tmp:kb:3472` | 委託合約 建立簽署流程 | `jgb/D/delegation-contract-flow` | 委託合約的建立簽署、提前終止與 PDF 下載 | new | D/D/D | |
| 178 | `tmp:kb:3473` | 委託合約提前終止 解除委託 | `jgb/D/delegation-contract-flow` | 委託合約的建立簽署、提前終止與 PDF 下載 | new | D/D/D | |
| 179 | `tmp:kb:3474` | 委託合約 PDF 文件下載 | `jgb/D/delegation-contract-flow` | 委託合約的建立簽署、提前終止與 PDF 下載 | new | D/D/D | |
| 180 | `tmp:kb:3484` | 發送簽約邀請 建立合約步驟 | `jgb/D/contract-esign-flow` | 建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用） | merge | D/D/D | |
| 181 | `tmp:kb:3490` | 合約為什麼不能發送簽約邀請 | `jgb/D/contract-send-invite` | 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整） | new | D/D/D | |
| 182 | `tmp:kb:3491` | 合約為什麼不能點交 | `jgb/D/handover-checkin` | 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 | new | D/D/D | |
| 183 | `tmp:kb:3492` | 合約為什麼不能點退 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 184 | `tmp:kb:3493` | 合約為什麼不能提前解約 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 185 | `tmp:kb:3494` | 合約為什麼不能續約 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 186 | `tmp:kb:3507` | 物件為什麼不能建立合約 | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 187 | `tmp:kb:3510` | 合約目前是什麼狀態 | `jgb/D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | new | D/D/D | |
| 188 | `tmp:kb:3511` | 合約的點交/點退/提前解約/續約按鈕是否可用 | `jgb/D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | new | D/D/D | |
| 189 | `tmp:kb:3512` | 為什麼不能取消點交或點退 | `jgb/D/handover-return-cancel-invite` | 取消／收回點交或點退邀請，為什麼不能取消 | new | D/D/D | |
| 190 | `tmp:kb:3513` | 為什麼不能取消或作廢合約 | `jgb/D/contract-cancel-delete` | 合約刪除、取消、作廢的條件與取消 vs 歷史合約差異 | new | D/D/D | |
| 191 | `tmp:kb:3515` | 點交清單內容 設備分類與自訂項目 | `jgb/D/handover-checkin` | 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 | new | D/D/D | |
| 192 | `tmp:kb:3516` | 租客不同意點交 修改清單重發 | `jgb/D/handover-checkin` | 點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發 | new | D/D/D | |
| 193 | `tmp:kb:3518` | 點退清單填寫 費用與賠償項目 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 194 | `tmp:kb:3520` | 租客不同意點退 修改清單重發 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 195 | `tmp:kb:3521` | 點退金額有異議 租客拒絕確認 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 196 | `tmp:kb:3522` | 提前解約違約金計算 退租賠償金額 | `jgb/D/early-termination-penalty` | 提前解約違約金怎麼算（預告期）、由誰付 | new | D/D/D | |
| 197 | `tmp:kb:3523` | 租客違約欠租 房東提前解約理由 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 198 | `tmp:kb:3524` | 提前解約違約金付款方 房東賠償租客 | `jgb/D/early-termination-penalty` | 提前解約違約金怎麼算（預告期）、由誰付 | new | D/D/D | |
| 199 | `tmp:kb:3525` | 取消提前解約申請 反悔處理 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 200 | `tmp:kb:3526` | 提前解約生效後 點退與違約金結算 | `jgb/D/early-termination-aftermath` | 提前解約生效後：何時可點退、違約金與押金一併結算、之後還要處理什麼 | new | D/D/D | |
| 201 | `tmp:kb:3527` | 續約歷史紀錄 原合約保留查詢 | `jgb/D/renewal-history-and-addendum` | 續約後原合約去哪了：續約歷史、增補文件分頁、有沒有下一份約 | new | D/D/D | |
| 202 | `tmp:kb:3528` | 續約資料保留與重置 重新簽署 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 203 | `tmp:kb:3529` | 免註冊租客續約 不需電子簽名 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 204 | `tmp:kb:3530` | 批次續約 多筆合約一起續 快速日期設定 | `jgb/D/contract-batch-renewal` | 續約能不能批次處理（含快速日期設定、紙本上傳、通知分流） | merge | D/D/D | |
| 205 | `tmp:kb:3814` | 合約怎麼還沒生效 生效了沒 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 206 | `tmp:kb:3815` | 合約卡在哪 卡住了 簽了沒動靜 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 207 | `tmp:kb:3838` | 合約修改 能不能改 三種出口 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 208 | `tmp:kb:3839` | 簽署中合約修改 取消退回再改 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 209 | `tmp:kb:3841` | 資料異動申請書 填寫與提交 | `jgb/D/contract-data-change-form` | 資料異動申請書的填寫與提交 | new | D/D/D | |
| 210 | `tmp:kb:3842` | 編輯不了合約 權限不足 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 211 | `tmp:kb:3843` | 合約備註 50 行上限 | `jgb/D/contract-attachments-notes-limits` | 合約附件上傳、備註 50 行與補充條款限制 | new | D/D/D | |
| 212 | `tmp:kb:3845` | 合約內文用詞更新 內政部新制 | `jgb/D/contract-templates` | 合約範本有哪些可以選（含內文隨內政部新制更新） | merge | D/D/D | |
| 213 | `tmp:kb:3846` | 合約刪除 作廢 條件 | `jgb/D/contract-cancel-delete` | 合約刪除、取消、作廢的條件與取消 vs 歷史合約差異 | new | D/D/D | |
| 214 | `tmp:kb:3847` | 到期退租收尾 步驟總覽 | `jgb/D/lease-end-checkout-overview` | 租客要退租了接下來怎麼做：到期收尾步驟總覽（點退→帳單→封存→轉歷史）與退租跑到哪一步 | new | D/D/D | |
| 215 | `tmp:kb:3850` | 點退找補費用 操作位置 | `jgb/D/return-checkout` | 點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議 | new | D/D/D | |
| 216 | `tmp:kb:3851` | 提前解約回簽 效期30天 | `jgb/D/early-termination-flow` | 提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約 | new | D/D/D | |
| 217 | `tmp:kb:3853` | 收尾完成 何時轉歷史合約 | `jgb/D/contract-history-retention` | 歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程） | merge | D/D/D | |
| 218 | `tmp:kb:3854` | 續約失敗 已達數量上限 方案配額 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | ⚠️ D/?/D | |
| 219 | `tmp:kb:3855` | 系統續約 vs 重建新約 取捨 | `jgb/D/renewal-vs-new-contract` | 系統續約 vs 重建新約的取捨（條件變更、租屋補助審核） | new | D/D/D | |
| 220 | `tmp:kb:3856` | 續約增補文件 原合約分頁 | `jgb/D/renewal-history-and-addendum` | 續約後原合約去哪了：續約歷史、增補文件分頁、有沒有下一份約 | new | D/D/D | |
| 221 | `tmp:kb:3858` | 續約重簽 邀請效期72小時 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 222 | `tmp:kb:3860` | 上傳既存合約 適用情境 效力 | `jgb/D/upload-existing-contract` | 上傳既存（紙本）合約：適用情境、效力、入口、檔案上限 | new | D/D/D | |
| 223 | `tmp:kb:3861` | 新增合約入口 物件刊登前提 | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 224 | `tmp:kb:3862` | 一物件多合約 上限10份 | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 225 | `tmp:kb:3864` | 公司大小章 Logo 合約呈現 | `jgb/D/signer-identity-and-seal` | 簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法 | new | D/D/D | |
| 226 | `tmp:kb:3865` | 電子合約 法律效力 簽章認證 | `jgb/D/esign-legal-validity` | 電子合約法律效力、簽章認證與 72 小時審閱期 | new | D/D/D | |
| 227 | `tmp:kb:3866` | 大房東自己簽約 業者團隊身分 | `jgb/D/signer-identity-and-seal` | 簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法 | new | D/D/D | |
| 228 | `tmp:kb:3867` | 簽約邀請 發送通道 Email 簡訊 | `jgb/D/contract-send-invite` | 發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整） | new | D/D/D | |
| 229 | `tmp:kb:3868` | 邀請過期 連結失效 資料清空 | `jgb/D/esign-invite-expiry` | 簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長 | new | D/D/D | |
| 230 | `tmp:kb:3870` | 簽約瀏覽器建議 簽名載入失敗 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 231 | `tmp:kb:3872` | 簽署進度 查得到與查不到的 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 232 | `tmp:kb:3873` | 我想改合約 內容要修改 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 233 | `tmp:kb:3874` | 合約打錯了 填錯要改 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 234 | `tmp:kb:3875` | 簽出去的合約還能改嗎 改得了嗎 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 235 | `tmp:kb:3876` | 租客要退租了 接下來怎麼做 | `jgb/D/lease-end-checkout-overview` | 租客要退租了接下來怎麼做：到期收尾步驟總覽（點退→帳單→封存→轉歷史）與退租跑到哪一步 | new | D/D/D | |
| 236 | `tmp:kb:3877` | 提前解約之後 還要處理什麼 | `jgb/D/early-termination-aftermath` | 提前解約生效後：何時可點退、違約金與押金一併結算、之後還要處理什麼 | new | D/D/D | |
| 237 | `tmp:kb:3878` | 退租跑到哪一步了 還缺什麼 | `jgb/D/lease-end-checkout-overview` | 租客要退租了接下來怎麼做：到期收尾步驟總覽（點退→帳單→封存→轉歷史）與退租跑到哪一步 | new | D/D/D | |
| 238 | `tmp:kb:3879` | 合約快到期 要續約怎麼辦 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 239 | `tmp:kb:3880` | 租客要續租 合約怎麼延 | `jgb/D/renewal-flow` | 合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限 | new | D/D/D | |
| 240 | `tmp:kb:3881` | 要簽新合約 怎麼開始建 | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 241 | `tmp:kb:3883` | 租客簽不了約 一直簽不成 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 242 | `tmp:kb:3884` | 租客說沒收到合約 找不到約 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 243 | `tmp:kb:3894` | 物件資料修改 既有合約不受影響 快照原則 | `jgb/D/contract-snapshot-independence` | 合約快照原則：物件資料、租客聯絡方式或姓名事後修改，合約與通知都不連動 | new | D/D/D | |
| 244 | `tmp:kb:3896` | 租客修改信箱電話 合約與通知不同步 | `jgb/D/contract-snapshot-independence` | 合約快照原則：物件資料、租客聯絡方式或姓名事後修改，合約與通知都不連動 | new | D/D/D | |
| 245 | `tmp:kb:3897` | 租客改名 合約顯示與PDF一致不變 | `jgb/D/contract-snapshot-independence` | 合約快照原則：物件資料、租客聯絡方式或姓名事後修改，合約與通知都不連動 | new | D/D/D | |
| 246 | `tmp:kb:3898` | 更換承租人 需重簽新約 | `jgb/D/tenant-change-new-contract` | 更換承租人／退房後換新租客：只能新建合約，舊約收尾與物件重刊登 | new | D/D/D | |
| 247 | `tmp:kb:4149` | 點交 點退 押金狀態 物件快速篩選 | `jgb/D/contract-filter-by-state` | 依合約狀態篩選物件（點交點退、待退押金、本月到期、無合約） | new | D/D/D | |
| 248 | `tmp:kb:4153` | 物件為什麼不能建立合約 缺什麼欄位 | `jgb/D/contract-create-entry-and-prereq` | 新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口 | new | D/D/D | |
| 249 | `tmp:kb:4216` | 退房後換新租客 點退押金 物件要重開嗎 | `jgb/D/tenant-change-new-contract` | 更換承租人／退房後換新租客：只能新建合約，舊約收尾與物件重刊登 | new | D/D/D | |
| 250 | `tmp:kb:4218` | 既存合約 是什麼 簽署完成上傳備查 | `jgb/D/upload-existing-contract` | 上傳既存（紙本）合約：適用情境、效力、入口、檔案上限 | new | D/D/D | |
| 251 | `tmp:kb:4254` | 簽約前狀態 待發送 待租客簽回 待房東簽名 差別 | `jgb/D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | new | D/D/D | |
| 252 | `tmp:kb:4255` | 取消點交邀請 取消點退邀請 收回邀請 | `jgb/D/handover-return-cancel-invite` | 取消／收回點交或點退邀請，為什麼不能取消 | new | D/D/D | |
| 253 | `tmp:kb:4263` | 押金資訊 押金多少 退還方式 | `jgb/D/deposit-setting-and-refund-system` | 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算） | new | D/D/D | |
| 254 | `tmp:kb:4278` | 押金要付多少 什麼時候退 | `jgb/D/deposit-setting-and-refund-system` | 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算） | new | D/D/D | |
| 255 | `tmp:kb:4279` | 退租押金怎麼退還 | `jgb/D/deposit-setting-and-refund-system` | 合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算） | new | D/D/D | |
| 256 | `tmp:kb:4562` | 想改合約租期 租金要調整 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 257 | `tmp:kb:4563` | 合約狀態怪怪的 不太對勁 | `jgb/D/contract-status-overview` | 合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀 | new | D/D/D | |
| 258 | `tmp:kb:4639` | 用租客姓名找合約 找某租客的租約 姓名反查合約編號 | `jgb/D/contract-lookup` | 查詢合約資訊：以合約編號／物件名稱查、不能用租客姓名反查、租客資料卡 | new | D/D/D | |
| 259 | `tmp:kb:4641` | 查詢合約資訊 合約編號查詢 | `jgb/D/contract-lookup` | 查詢合約資訊：以合約編號／物件名稱查、不能用租客姓名反查、租客資料卡 | new | D/D/D | |
| 260 | `tmp:kb:4644` | 租客簽名檢查 漏簽提醒 少簽防呆 | `jgb/D/esign-troubleshooting` | 租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆 | new | D/D/D | |
| 261 | `tmp:kb:4645` | 雙人簽約 兩位承租人填寫方式 | `jgb/D/signer-identity-and-seal` | 簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法 | new | D/D/D | |
| 262 | `tmp:kb:4646` | 合約修改後更新 改租金要重填嗎 複製合約 | `jgb/D/contract-modify-after-sign` | 合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查） | merge | D/D/D | |
| 263 | `tmp:kb:4655` | 物件總表篩選 快到期空房 本月到期 無合約 | `jgb/D/contract-filter-by-state` | 依合約狀態篩選物件（點交點退、待退押金、本月到期、無合約） | new | ⚠️ D/?/D | |
| 264 | `tmp:kb:4660` | 合約有沒有續約 下一份約 | `jgb/D/renewal-history-and-addendum` | 續約後原合約去哪了：續約歷史、增補文件分頁、有沒有下一份約 | new | D/D/D | |

## B. 拆分（split）——一個舊細目拆成多個新細目

| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |
|---|---|---|---|
| `tmp:kb:tmp:draft:10` |  | `jgb/D/contract-send-invite`《發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整）》；`jgb/D/esign-invite-expiry`《簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長》 | |
| `tmp:kb:tmp:draft:2` |  | `jgb/D/contract-batch-renewal`《續約能不能批次處理（含快速日期設定、紙本上傳、通知分流）》；`jgb/D/contract-esign-flow`《建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用）》；`jgb/D/early-termination-flow`《提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約》；`jgb/D/handover-checkin`《點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發》；`jgb/D/return-checkout`《點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議》；`jgb/D/upload-existing-contract`《上傳既存（紙本）合約：適用情境、效力、入口、檔案上限》 | |

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/D/breach-penalty-rules`《違約責任與違約金一般規範：上限、計算、提前解約後果、證據保留》 | `tmp:kb:2903`＋`tmp:kb:2954`＋`tmp:kb:2960`＋`tmp:kb:2961`＋`tmp:kb:2962`＋`tmp:kb:3285`＋`tmp:kb:3294` | 違約金額度與後果是契約層一般規範一題，多筆近重複合併；系統自動計算違約金另見 | |
| `jgb/D/contract-attachments-notes-limits`《合約附件上傳、備註 50 行與補充條款限制》 | `tmp:kb:3393`＋`tmp:kb:3843`＋`tmp:kb:tmp:draft:5` | 附件、備註、補充條款都是合約本文以外的補充載體，其格式／容量／行數限制互為替代方案（備註超行改上傳附件） | |
| `jgb/D/contract-batch-renewal`《續約能不能批次處理（含快速日期設定、紙本上傳、通知分流）》 | `tmp:kb:tmp:canon:jgb/D/contract-batch-renewal`＋`tmp:kb:3530`＋`tmp:kb:tmp:draft:2` | 「多筆合約一起續」是獨立提問；3530 的快速日期與依租客類型分流通知、教學文批次續約段拆入補足操作細節 | |
| `jgb/D/contract-cancel-delete`《合約刪除、取消、作廢的條件與取消 vs 歷史合約差異》 | `tmp:kb:3846`＋`tmp:kb:3513`＋`tmp:kb:3386` | 能否取消／刪除由狀態決定、且取消後的記錄與歷史合約不同，三筆互補；已簽後只能提前解約以另見處理 | |
| `jgb/D/contract-create-entry-and-prereq`《新增合約從哪進、物件為什麼不能建約（須刊登中、必填欄位）、一物件多合約上限、編輯入口》 | `tmp:kb:3861`＋`tmp:kb:3507`＋`tmp:kb:4153`＋`tmp:kb:3862`＋`tmp:kb:3881`＋`tmp:kb:tmp:draft:8`＋`tmp:kb:tmp:draft:9`＋`tmp:kb:tmp:draft:18` | 「要簽新約從哪開始／為什麼不能建約」是簽約流程之前獨立成立的入口＋前提題；draft:9 編輯入口同屬入口；空內文 4153/3881 只當入口 | |
| `jgb/D/contract-esign-flow`《建約方式與線上電子簽約流程（含時效、身分、社宅、簽約邀請通知、費用）》 | `tmp:kb:tmp:canon:jgb/D/contract-esign-flow`＋`tmp:kb:3374`＋`tmp:kb:3375`＋`tmp:kb:3484`＋`tmp:kb:3332`＋`tmp:kb:tmp:draft:3`＋`tmp:kb:tmp:draft:2` | 主路徑「怎麼建約、怎麼簽」：建約後發送邀請、租客簽、管理方回簽一條龍；3332 草稿自動儲存屬建約過程；教學文合約篇的建約與簽訂段拆入；發送通道／效期／排錯各自另見獨立細目 | |
| `jgb/D/contract-filter-by-state`《依合約狀態篩選物件（點交點退、待退押金、本月到期、無合約）》 | `tmp:kb:4149`＋`tmp:kb:4655`＋`tmp:kb:tmp:draft:12` | 由合約驅動的物件狀態篩選歸租約，篩選入口與各狀態語義分層；4149 與 draft:12 內容相同合併 | |
| `jgb/D/contract-history-retention`《歷史合約保留多久與何時轉歷史（含點退狀態、過期結案排程）》 | `tmp:kb:tmp:canon:jgb/D/contract-history-retention`＋`tmp:kb:3330`＋`tmp:kb:3385`＋`tmp:kb:3853`＋`tmp:kb:tmp:draft:6` | 「保留多久／到期後去哪了／已點退為何還在執行中」同屬合約結束後生命週期一問；⚠ 材料矛盾：既有細目說無期限不刪除、3330 說保存 5 年，此處只並列不裁真偽 | |
| `jgb/D/contract-lookup`《查詢合約資訊：以合約編號／物件名稱查、不能用租客姓名反查、租客資料卡》 | `tmp:kb:4639`＋`tmp:kb:4641`＋`tmp:kb:tmp:draft:21` | 「怎麼找到那份合約、找到後看租客聯絡方式」是查找路徑一題，與狀態語義分層；空內文 4641 只當入口 | |
| `jgb/D/contract-modify-after-sign`《合約送出或簽完後能不能修改（三種出口，含編輯不了的權限排查）》 | `tmp:kb:tmp:canon:jgb/D/contract-modify-after-sign`＋`tmp:kb:3838`＋`tmp:kb:3839`＋`tmp:kb:3842`＋`tmp:kb:3873`＋`tmp:kb:3874`＋`tmp:kb:3875`＋`tmp:kb:4562`＋`tmp:kb:4646`＋`tmp:kb:tmp:draft:11`＋`tmp:kb:tmp:draft:20` | 「我想改合約」各種問法（打錯、租金要調、簽出去還能改嗎、編輯不了）全落到同一個依合約階段分三出口的答案；3842 權限不足是同一問的另一排查分支；空內文 3873/3874/3875/4562 只當入口 | |
| `jgb/D/contract-send-invite`《發送簽約邀請：通道（Email／簡訊）、租客會收到什麼、為什麼不能發送（欄位未填完整）》 | `tmp:kb:3867`＋`tmp:kb:3368`＋`tmp:kb:3490`＋`tmp:kb:tmp:draft:10`＋`tmp:kb:tmp:draft:16` | 發送邀請的操作、通道與「欄位未填寫完整」排查是同一節點；draft:10 的寄送段拆入；空內文 3368 只當入口；效期與逾期另見 | |
| `jgb/D/contract-snapshot-independence`《合約快照原則：物件資料、租客聯絡方式或姓名事後修改，合約與通知都不連動》 | `tmp:kb:3894`＋`tmp:kb:3896`＋`tmp:kb:3897` | 三筆都是同一機制（簽約當下快照）的不同表現，互為印證才說得清 | |
| `jgb/D/contract-status-overview`《合約狀態總覽：12 狀態 4 階段、簽約前三狀態、執行中五細分、按鈕能不能按的前置判讀》 | `tmp:kb:3373`＋`tmp:kb:3389`＋`tmp:kb:4254`＋`tmp:kb:3372`＋`tmp:kb:3510`＋`tmp:kb:3511`＋`tmp:kb:4563` | 「合約現在是什麼狀態／什麼狀態能做什麼」是狀態語義一題；3511 是按鈕可用性總入口；空內文 3372/3510/4563 只當入口 | |
| `jgb/D/contract-templates`《合約範本有哪些可以選（含內文隨內政部新制更新）》 | `tmp:kb:tmp:canon:jgb/D/contract-templates`＋`tmp:kb:3845` | 範本清單與範本內文隨法規更新屬同一標的（系統提供的合約文本），三角度一致 | |
| `jgb/D/delegation-contract-change-termination`《委託管理合約的變更、續約、終止、轉讓、違約與爭議解決》 | `tmp:kb:3116`＋`tmp:kb:3118`＋`tmp:kb:3119`＋`tmp:kb:3120`＋`tmp:kb:3124`＋`tmp:kb:3126`＋`tmp:kb:3261`＋`tmp:kb:3316` | 合約存續期間的變動事件與違約爭議互相關聯，近重複合併；系統上的提前終止操作另見委託合約流程 | |
| `jgb/D/delegation-contract-flow`《委託合約的建立簽署、提前終止與 PDF 下載》 | `tmp:kb:3472`＋`tmp:kb:3473`＋`tmp:kb:3474` | 委託合約在系統上的生命週期（建立→簽署→終止→文件）三筆互相銜接 | |
| `jgb/D/delegation-contract-terms-general`《委託管理合約一般內容：定義、期限、服務範圍、管理師責任與租客權益、管理費計算與支付、適用法律》 | `tmp:kb:3114`＋`tmp:kb:3115`＋`tmp:kb:3121`＋`tmp:kb:3122`＋`tmp:kb:3125`＋`tmp:kb:3147`＋`tmp:kb:3259`＋`tmp:kb:3260`＋`tmp:kb:3117`＋`tmp:kb:3123`＋`tmp:kb:3158` | 委託管理合約「約了什麼」的租客視角泛問近重複合併；管理費依合約約定故留此不歸帳務；3147 租約管理服務是同一泛問 | |
| `jgb/D/delegation-vs-lease-contract`《委託約與租賃約的差別（系統分開管理）》 | `tmp:kb:3334`＋`tmp:kb:3471` | 兩種合約類型的定義差異獨立成立，售前與業者同答；包租／代管設定差異另見既有細目 | |
| `jgb/D/deposit-deduction-refund`《押金扣除、退還與爭議：扣款條件、明細告知、保管責任、退還期限、爭議處理》 | `tmp:kb:2927`＋`tmp:kb:2930`＋`tmp:kb:2931`＋`tmp:kb:2933`＋`tmp:kb:3154`＋`tmp:kb:3171`＋`tmp:kb:3212`＋`tmp:kb:3213` | 扣除條件、明細義務、保管責任、退還期限與爭議處理彼此依賴才完整；系統點退結算另見 | |
| `jgb/D/deposit-legal-limits`《押金一般規範：上限兩個月、無利息、法源、用途、支付方式、約定修改、轉讓、不得抵租》 | `tmp:kb:2901`＋`tmp:kb:2916`＋`tmp:kb:2926`＋`tmp:kb:2929`＋`tmp:kb:2932`＋`tmp:kb:2934`＋`tmp:kb:2935`＋`tmp:kb:2936`＋`tmp:kb:2937`＋`tmp:kb:3021`＋`tmp:kb:3211`＋`tmp:kb:3215`＋`tmp:kb:3284` | 押金「是什麼、上限多少、法源、怎麼約定、能做什麼用」是押金的一般規範一題，多筆近重複合併；扣除退還爭議另見 | |
| `jgb/D/deposit-setting-and-refund-system`《合約押金設定（月數／固定金額）與押金查詢、退還時點（點退結算）》 | `tmp:kb:3387`＋`tmp:kb:1392`＋`tmp:kb:4263`＋`tmp:kb:4278`＋`tmp:kb:4279` | 系統上押金怎麼設、怎麼查、何時退是合約設定的操作題，與法律常識分層；空內文 1392/4263/4278/4279 只當入口 | |
| `jgb/D/early-termination-aftermath`《提前解約生效後：何時可點退、違約金與押金一併結算、之後還要處理什麼》 | `tmp:kb:3526`＋`tmp:kb:3877`＋`tmp:kb:tmp:draft:15` | 解約生效後的收尾（點退時點、違約金併入點退帳單）是解約流程之後獨立的一題；空內文 3877 只當入口 | |
| `jgb/D/early-termination-flow`《提前解約（JGB 流程）：發起條件、租客發起、房東發起與法定理由、回簽效期、取消申請、為什麼不能提前解約》 | `tmp:kb:3380`＋`tmp:kb:3381`＋`tmp:kb:3382`＋`tmp:kb:3370`＋`tmp:kb:3493`＋`tmp:kb:3523`＋`tmp:kb:3525`＋`tmp:kb:3851`＋`tmp:kb:tmp:draft:2` | 誰能發起、需要什麼條件、對方怎麼回應、逾期或反悔如何處理是一條互相依賴的流程；房東理由清單決定回簽期限與是否有違約金；空內文 3370 只當入口；教學文提前終止段拆入 | |
| `jgb/D/early-termination-penalty`《提前解約違約金怎麼算（預告期）、由誰付》 | `tmp:kb:3522`＋`tmp:kb:3524` | 違約金額度與付款方由合約設定與發起方決定，兩筆互補；法律常識層的違約金另見一般規範細目 | |
| `jgb/D/equipment-usage-under-lease`《租約中的設備與公共設備使用規範》 | `tmp:kb:2989`＋`tmp:kb:3290`＋`tmp:kb:3196`＋`tmp:kb:3201` | 設備使用規範由租約約定，四筆近重複合併；房東維修責任法源出架至修繕 | |
| `jgb/D/esign-invite-expiry`《簽約邀請效期 72 小時、逾期退回與租客資料清空、可申請延長》 | `tmp:kb:3331`＋`tmp:kb:3868`＋`tmp:kb:tmp:draft:10` | 邀請逾期的後果（連結失效、退回待發送、資料清空）與手動取消保留資料的差別、可申請 7／30 天效期是一組互相依賴的內容；draft:10 的逾期段拆入 | |
| `jgb/D/esign-legal-validity`《電子合約法律效力、簽章認證與 72 小時審閱期》 | `tmp:kb:3865`＋`tmp:kb:3328` | 電子簽章效力與審閱期法規是合約法律地位一題，售前與業者同答，與操作流程無依賴 | |
| `jgb/D/esign-troubleshooting`《租客簽不了、沒收到、卡住：連結打不開、簽名板載入失敗、瀏覽器建議、簽署進度查得到什麼、漏簽防呆》 | `tmp:kb:3392`＋`tmp:kb:3870`＋`tmp:kb:3872`＋`tmp:kb:3883`＋`tmp:kb:3884`＋`tmp:kb:3814`＋`tmp:kb:3815`＋`tmp:kb:4644` | 簽署異常的排查（連結、瀏覽器、綁定、雲想端）與「合約怎麼還沒生效／卡在哪」的進度判讀是問題導向的一題；回簽逐頁檢查少簽屬簽署把關；空內文 3883/3884/3814/3815 只當入口 | |
| `jgb/D/handover-checkin`《點交（搬入）：流程、前置條件、為什麼不能點交、清單內容與自訂項目、租客不同意重發》 | `tmp:kb:3376`＋`tmp:kb:3377`＋`tmp:kb:3491`＋`tmp:kb:3515`＋`tmp:kb:3516`＋`tmp:kb:tmp:draft:2` | 點交的流程、前置條件、清單填法與退回重發互相依賴才完整（前置條件解釋為何按鈕灰）；教學文點交段拆入 | |
| `jgb/D/handover-return-cancel-invite`《取消／收回點交或點退邀請，為什麼不能取消》 | `tmp:kb:3512`＋`tmp:kb:4255` | 取消邀請橫跨點交與點退且由狀態值決定（租客已同意即不可撤回），獨立成一問避免歸邊；空內文 4255 只當入口 | |
| `jgb/D/household-registration-under-lease`《租屋期間戶籍遷移與居住證明》 | `tmp:kb:3035`＋`tmp:kb:3043`＋`tmp:kb:3047` | 戶籍與居住證明是租約附帶的行政題，三筆互補獨立成立 | |
| `jgb/D/lease-clauses-interpretation`《租約條款有哪些、怎麼解釋與變更（租金法律依據、租金包含項目、租金爭議）》 | `tmp:kb:2924`＋`tmp:kb:3028`＋`tmp:kb:3034`＋`tmp:kb:3159`＋`tmp:kb:3209`＋`tmp:kb:3210`＋`tmp:kb:3239`＋`tmp:kb:3296` | 「合約寫了什麼、怎麼解讀、怎麼變更」是契約條款總論一題；租金事項由合約條款決定歸租約，帳單計算另見帳務 | |
| `jgb/D/lease-end-checkout-overview`《租客要退租了接下來怎麼做：到期收尾步驟總覽（點退→帳單→封存→轉歷史）與退租跑到哪一步》 | `tmp:kb:3847`＋`tmp:kb:3876`＋`tmp:kb:3878` | 跨點退／帳單／歷史合約的順序總覽是獨立的導覽題，與各步驟細目分層；空內文 3876/3878 只當入口 | |
| `jgb/D/lease-expiry-followup-scope`《合約到期追問可答範圍與到期提醒（導向續約面向）》 | `tmp:kb:tmp:canon:jgb/D/lease-expiry-followup-scope`＋`tmp:kb:3388` | 到期倒數提醒與「到期前多久該做什麼」是到期追問的可答內容；續約與退租各有細目，此處只管到期本身；本月到期篩選另見依狀態篩選細目 | |
| `jgb/D/lease-termination-notice-rules`《終止租約的通知期與合法事由（租客／房東、不定期租約、租客失蹤）》 | `tmp:kb:2949`＋`tmp:kb:2951`＋`tmp:kb:2952`＋`tmp:kb:2953`＋`tmp:kb:2955`＋`tmp:kb:2956`＋`tmp:kb:2957`＋`tmp:kb:2958`＋`tmp:kb:2959`＋`tmp:kb:3022`＋`tmp:kb:3217` | 「要提前多久通知、什麼情況能終止」是法規與契約層的一般規範，多筆近重複合併；系統提前解約操作另見 | |
| `jgb/D/move-in-inspection`《入住注意事項與傢俱清點》 | `tmp:kb:2938`＋`tmp:kb:2942` | 入住時的檢查與清點是租約起點的一般常識，與系統點交流程分層以另見處理 | |
| `jgb/D/renewal-flow`《合約續約（JGB 流程）：步驟、前置條件、為什麼不能續約、資料沿用與重簽、免註冊租客、已達數量上限》 | `tmp:kb:3383`＋`tmp:kb:3384`＋`tmp:kb:3494`＋`tmp:kb:3371`＋`tmp:kb:3879`＋`tmp:kb:3880`＋`tmp:kb:3528`＋`tmp:kb:3529`＋`tmp:kb:3858`＋`tmp:kb:3854` | 「可以續約嗎／怎麼延／為什麼不能續」同一條系統續約路徑；3529 與 3858 內容重疊；3854 方案配額上限是「不能續／不能建」的一種原因；空內文 3371/3879/3880 只當入口 | |
| `jgb/D/renewal-history-and-addendum`《續約後原合約去哪了：續約歷史、增補文件分頁、有沒有下一份約》 | `tmp:kb:3527`＋`tmp:kb:3856`＋`tmp:kb:4660` | 續約產出物（增補 PDF、舊版本、續約歷史）的查閱方式獨立成立；空內文 4660 只當入口 | |
| `jgb/D/renewal-vs-new-contract`《系統續約 vs 重建新約的取捨（條件變更、租屋補助審核）》 | `tmp:kb:3855`＋`tmp:kb:3329`＋`tmp:kb:3333` | 「該續約還是重簽」是決策題，取決於參數是否變更與租補審核，三角度一致 | |
| `jgb/D/return-checkout`《點退（搬出）：流程、前置條件與時機、為什麼不能點退、清單費用賠償、押金找補與點退帳單、租客不同意或有異議》 | `tmp:kb:3378`＋`tmp:kb:3379`＋`tmp:kb:3492`＋`tmp:kb:3518`＋`tmp:kb:3520`＋`tmp:kb:3521`＋`tmp:kb:3850`＋`tmp:kb:tmp:draft:13`＋`tmp:kb:tmp:draft:14`＋`tmp:kb:tmp:draft:17`＋`tmp:kb:tmp:draft:2` | 點退的前置（不需先點交、過期仍可、30 天內到期起）、清單填寫、找補在點退清單操作、帳單自動產生與不同意處理是一條路徑；3521 是租客端同一機制的另一視角；教學文點退段拆入 | |
| `jgb/D/signer-identity-and-seal`《簽約身分與簽署方資訊：個人／法人、公司大小章與 Logo、大房東以業者身分簽約、兩位承租人填法》 | `tmp:kb:3440`＋`tmp:kb:3864`＋`tmp:kb:3866`＋`tmp:kb:4645` | 「合約上簽署方是誰、怎麼呈現」是簽署主體設定一題，三角度一致 | |
| `jgb/D/social-housing-lease`《社會住宅租約與一般租約的差異、期限與終止》 | `tmp:kb:3131`＋`tmp:kb:3132`＋`tmp:kb:3134`＋`tmp:kb:3318` | 社宅租約是獨立子題；系統上的社宅公證流程在電子簽約細目以另見處理 | |
| `jgb/D/sublease-and-shared-lease-terms`《轉租與分租的租約條款與押金處理》 | `tmp:kb:3077`＋`tmp:kb:3078`＋`tmp:kb:3079` | 轉租／分租是租約的特殊型態，條款與押金處理三筆互補 | |
| `jgb/D/sublease-vs-management-contract`《包租與代管的差別（委託合約設定、租約簽訂方、押金管理、終止條件、租金調整）》 | `tmp:kb:tmp:canon:jgb/D/sublease-vs-management-contract`＋`tmp:kb:3089`＋`tmp:kb:3090`＋`tmp:kb:3093`＋`tmp:kb:3094` | 「包租跟代管差在哪」一題一細目：系統設定差異與租客視角的四則比較互為補充，拆成中立版＋租客版會違反講法唯一 | |
| `jgb/D/tenant-change-new-contract`《更換承租人／退房後換新租客：只能新建合約，舊約收尾與物件重刊登》 | `tmp:kb:3898`＋`tmp:kb:4216` | 「換人」沒有功能，答案是舊約收尾＋新約，兩筆分別講為何與怎麼做 | |
| `jgb/D/tenant-move-out-obligations`《退租義務：原狀回復、清潔標準、設備狀況、遺留物品處理、物品搬出》 | `tmp:kb:2939`＋`tmp:kb:2940`＋`tmp:kb:2941`＋`tmp:kb:2943`＋`tmp:kb:2944`＋`tmp:kb:2947`＋`tmp:kb:2948`＋`tmp:kb:2950`＋`tmp:kb:3191`＋`tmp:kb:3216`＋`tmp:kb:3218`＋`tmp:kb:3273` | 「退租要做到什麼程度／東西沒搬走怎麼辦」近重複合併為退租義務一問；押金扣除另見 | |
| `jgb/D/tenant-pet-clauses`《租約中的寵物押金與飼養寵物費用》 | `tmp:kb:2928`＋`tmp:kb:2977` | 寵物條款是獨立提問，答案依租約約定 | |
| `jgb/D/tenant-renewal-and-extension-rights`《租約續約與延住的一般約定：要不要提前通知、依原合約條件、業者會不會協助》 | `tmp:kb:2898`＋`tmp:kb:2945`＋`tmp:kb:2946`＋`tmp:kb:3153`＋`tmp:kb:3204` | 契約層的續約／延住規定與系統續約操作是不同層級，多筆近重複合併 | |
| `jgb/D/tenant-rental-insurance`《租屋相關保險：租屋保險費用、租客設備投保、押金投保》 | `tmp:kb:3006`＋`tmp:kb:3202`＋`tmp:kb:3214` | 保險是否需要、費用多少是租約附帶的獨立主題，三筆同屬保險 | |
| `jgb/D/tenant-sign-steps`《租客收到簽約邀請後的簽署步驟（租客視角）》 | `tmp:kb:3442`＋`tmp:kb:tmp:draft:19` | 業者被租客問「我要怎麼簽」的標準說明，與管理方流程分開才不混淆視角 | |
| `jgb/D/upload-existing-contract`《上傳既存（紙本）合約：適用情境、效力、入口、檔案上限》 | `tmp:kb:3860`＋`tmp:kb:4218`＋`tmp:kb:tmp:draft:2` | 既存合約是與電子簽約平行的另一種建約方式，效力、入口與 10MB 限制自成完整內容；售前也常問；教學文上傳合約段拆入 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| audience_level：contract-esign-flow 改為 prospect 專屬、只吸收 3865，操作段另拆 contract-create-fill-flow／contract-send-invite／contract-signing-flow-and-presign-states | 既有細目本身已是操作流程且兩受眾共用，拆出會形成中立版與受眾版並存；採 user_question_path／content_boundary 的兩受眾合併 | |
| audience_level：3865 電子簽章效力併入 contract-esign-flow、3328 審閱期併入邀請效期 | 兩角度多數把法律效力與審閱期獨立成 esign-legal-validity，售前與業者同答且與操作無依賴 | |
| content_boundary：發送邀請（3867/3368/3490/draft:10/draft:16）併入 contract-esign-flow | user_question_path 與 audience_level 都把「怎麼寄／為什麼不能寄」獨立於主流程；採獨立 contract-send-invite | |
| user_question_path：發送邀請與 72 小時效期合為一條 sign-invite-send-expiry-and-resend | 兩角度多數把效期／逾期清空獨立成 esign-invite-expiry；效期題被續約、審閱期等多處引用，宜單獨一處 | |
| audience_level：3374/3484 歸 contract-send-invite | 兩角度把建約後發送邀請的步驟視為主流程節點，歸 contract-esign-flow | |
| user_question_path：3884「租客說沒收到」歸發送邀請細目 | 兩角度歸簽署排錯；沒收到是異常排查而非正常發送步驟 | |
| user_question_path：3872/3814/3815/4563 另立 contract-progress-lookup；audience_level：3872/3814/3815 併入簽署流程 | 三角度無多數；「怎麼還沒生效／卡在哪／簽署進度查得到什麼」是問題導向，採 content_boundary 歸 esign-troubleshooting；4563「狀態怪怪的」兩角度歸狀態總覽 | |
| audience_level：4254 簽約前三狀態併入簽署流程細目 | 兩角度歸 contract-status-overview，狀態語義集中一處 | |
| user_question_path：4149/draft:12 點交點退篩選併入 contract-status-overview；content_boundary：4655 出架至 C | 兩角度把篩選獨立成操作題；4655 僅一角度出架故留 D，本月到期／無合約與點交點退同屬由合約驅動的物件篩選，採 audience_level 的 contract-filter-by-state | |
| user_question_path：4655 併入 lease-expiry-followup-scope | 4655 是物件總表篩選操作，與到期追問的可答範圍不同層級，歸篩選細目 | |
| audience_level：3842 權限不足另立 contract-edit-permission | 兩角度視為「編輯不了合約」同一問的排查分支，併入 contract-modify-after-sign | |
| user_question_path：draft:9 編輯入口併入 contract-modify-after-sign | 兩角度歸建約入口細目；draft:9 只講從哪進，不講能不能改 | |
| user_question_path：3394 複製合約併入建約入口細目 | 兩角度獨立成 contract-copy；複製是獨立功能且被修改題以另見引用 | |
| user_question_path：3390 PDF 下載與附件／備註限制合為 contract-documents-attachments-and-pdf | 兩角度分成 contract-pdf-download 與 contract-attachments-notes-limits；下載與上傳限制是不同提問 | |
| content_boundary：3332 草稿自動儲存歸建約前提細目；audience_level：歸 contract-create-fill-flow | 中途離開是建約填寫過程的問題，fill-flow 已併入 contract-esign-flow，故 3332 隨之歸主流程 | |
| content_boundary：3854「已達數量上限」出架至 I；audience_level：另立 contract-quota-limit | 僅一角度出架故留 D；為守 45～55 條上限採 user_question_path 併入 renewal-flow（症狀出現在建約／續約，成因方案配額以 reason 標明） | |
| audience_level：點交拆 contract-handover-prereq＋contract-handover-flow；點退拆 contract-moveout-prereq＋contract-moveout-flow | 兩角度把前置條件與流程合為一題，前置條件正是「為什麼不能點交／點退」的答案 | |
| content_boundary：3850/draft:13/draft:17 找補與點退帳單另立 return-deposit-settlement | 兩角度併入點退流程；找補在點退清單內操作，與點退清單填寫不可分 | |
| audience_level：3876/3878/4279 併入點退流程 | 兩角度把「退租接下來怎麼做／跑到哪一步」歸收尾總覽 lease-end-checkout-overview；4279 依 content_boundary 歸押金設定與退還時點 | |
| audience_level：3385/3853/draft:6 轉歷史合約時點併入收尾細目 contract-expiry-closing-to-history | 兩角度併入既有 contract-history-retention；「已點退為何還在執行中」與保留期限同屬合約結束後生命週期 | |
| audience_level：提前解約拆四條（prereq／initiate／cancel／after-effect） | 兩角度以一條流程涵蓋發起條件、雙方發起、取消；生效後結算另立 early-termination-aftermath 為三角度中兩者所採 | |
| user_question_path：違約金計算與生效後結算合為 early-termination-penalty-settlement | 兩角度分成 early-termination-penalty 與 early-termination-aftermath；算法／付款方與生效後收尾是不同提問 | |
| audience_level：續約拆 contract-renewal-prereq＋contract-renewal-flow，且 draft:2 續約段拆入 renewal-flow | 兩角度合為一條 renewal-flow；draft:2 的續約段實為批次續約，兩角度歸 contract-batch-renewal | |
| content_boundary：4660「有沒有續約」歸 renewal-flow | 兩角度歸 renewal-history-and-addendum；查有沒有下一份約是續約後查詢 | |
| user_question_path：3879 併入 lease-expiry-followup-scope | 兩角度歸 renewal-flow；「快到期要續約怎麼辦」是續約入口問法 | |
| audience_level：sublease-vs-management-contract 只 keep，3089/3090/3093 另立 tenant-sublease-vs-management-rights、3094 歸 tenant-rent-clauses | 兩角度全部併入既有細目；同一主題拆中立版與租客版違反「一個主題一個細目」 | |
| audience_level：租金條款（2924/3094/3209/3210）另立 tenant-rent-clauses | 兩角度把租金條款併入 lease-clauses-interpretation（3094 併入包租代管差別） | |
| user_question_path：委託約子題拆 create-sign／terminate（3473+3116+3124）／terms-and-rights／management-fee-terms；3114 歸 entrust-vs-lease-contract | 兩角度把系統操作三筆合為 delegation-contract-flow，法規常識分為一般內容與變更終止兩條；3114 定義題兩角度歸一般內容 | |
| audience_level：管理費三筆（3117/3123/3158）歸委託約變更與費用細目；user_question_path：另立 entrust-management-fee-terms | 三角度無多數；管理費怎麼算是「約了什麼」的內容，採 content_boundary 歸 delegation-contract-terms-general | |
| user_question_path／content_boundary：3147 租約管理服務歸委託約條款／租約條款解釋 | user_question_path 與 audience_level 都歸委託管理合約基本內容（業者提供的租約管理服務即委託服務範圍） | |
| user_question_path：押金分兩條（金額與法定上限含 3387 系統模式／扣除退還） | 兩角度把系統押金設定（3387 與空內文入口）獨立成操作題，與法律常識分層 | |
| content_boundary：2928/2977 寵物押金併入 deposit-legal-limits；3214 押金投保由 user_question_path 併入押金金額 | 兩角度把寵物條款獨立、把三筆保險合為 tenant-rental-insurance | |
| content_boundary：2937/3211/3215 歸押金扣除退還；audience_level：2933/3213 保管責任歸法律規定 | 逐筆取多數：用途／不得抵租／使用規定歸一般規範，保管責任歸扣除退還 | |
| user_question_path：入住注意事項合併設備使用規範與保險（2989/3290/3202/3006） | 兩角度只保留 2938/2942 為入住清點，設備規範獨立、保險獨立 | |
| content_boundary：退租遺留物品另立 move-out-leftover-items | 兩角度把遺留物品併入退租義務一題 | |
| user_question_path：終止租約依租客／房東拆 early-termination-rights-and-penalty 與 landlord-termination-and-eviction | 兩角度依命題拆為「通知期與合法事由」與「違約責任與違約金」，違約金題不因發起方而異 | |
| user_question_path：3196/3201 公共設備使用規範出架至 C | 僅一角度出架故留 D；兩角度視為由租約約定的設備使用規範 | |
| audience_level：3199/3276 設備維護法律依據留 D 併入設備使用規範 | 兩角度出架至修繕（講的是房東修繕責任與報修） | |
| user_question_path：draft:21 租客資料卡出架至 B | 僅一角度出架故留 D；兩角度歸 contract-lookup（找到合約後看承租人聯絡方式） | |
| audience_level：contract-batch-renewal 只 merge 3530、不拆入 draft:2 批次續約段 | 兩角度把教學文批次續約段拆入既有細目 | |
| user_question_path／audience_level：upload-existing-contract 受眾分別為兩者／僅業者 | 既存合約能否上傳是售前常問的能力題，採兩受眾（兩角度） | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 55 | 0 | 0 | 0 | 0 | 0 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/D/breach-penalty-rules` | merge |
| `jgb/D/contract-attachments-notes-limits` | merge |
| `jgb/D/contract-batch-renewal` | merge+split-child |
| `jgb/D/contract-cancel-delete` | merge |
| `jgb/D/contract-create-entry-and-prereq` | merge |
| `jgb/D/contract-esign-flow` | merge+split-child |
| `jgb/D/contract-filter-by-state` | merge |
| `jgb/D/contract-history-retention` | merge |
| `jgb/D/contract-lookup` | merge |
| `jgb/D/contract-modify-after-sign` | merge |
| `jgb/D/contract-send-invite` | merge+split-child |
| `jgb/D/contract-snapshot-independence` | merge |
| `jgb/D/contract-status-overview` | merge |
| `jgb/D/contract-templates` | merge |
| `jgb/D/delegation-contract-change-termination` | merge |
| `jgb/D/delegation-contract-flow` | merge |
| `jgb/D/delegation-contract-terms-general` | merge |
| `jgb/D/delegation-vs-lease-contract` | merge |
| `jgb/D/deposit-deduction-refund` | merge |
| `jgb/D/deposit-legal-limits` | merge |
| `jgb/D/deposit-setting-and-refund-system` | merge |
| `jgb/D/early-termination-aftermath` | merge |
| `jgb/D/early-termination-flow` | merge+split-child |
| `jgb/D/early-termination-penalty` | merge |
| `jgb/D/equipment-usage-under-lease` | merge |
| `jgb/D/esign-invite-expiry` | merge+split-child |
| `jgb/D/esign-legal-validity` | merge |
| `jgb/D/esign-troubleshooting` | merge |
| `jgb/D/handover-checkin` | merge+split-child |
| `jgb/D/handover-return-cancel-invite` | merge |
| `jgb/D/household-registration-under-lease` | merge |
| `jgb/D/lease-clauses-interpretation` | merge |
| `jgb/D/lease-end-checkout-overview` | merge |
| `jgb/D/lease-expiry-followup-scope` | merge |
| `jgb/D/lease-termination-notice-rules` | merge |
| `jgb/D/move-in-inspection` | merge |
| `jgb/D/renewal-flow` | merge |
| `jgb/D/renewal-history-and-addendum` | merge |
| `jgb/D/renewal-vs-new-contract` | merge |
| `jgb/D/return-checkout` | merge+split-child |
| `jgb/D/signer-identity-and-seal` | merge |
| `jgb/D/social-housing-lease` | merge |
| `jgb/D/sublease-and-shared-lease-terms` | merge |
| `jgb/D/sublease-vs-management-contract` | merge |
| `jgb/D/tenant-change-new-contract` | merge |
| `jgb/D/tenant-move-out-obligations` | merge |
| `jgb/D/tenant-pet-clauses` | merge |
| `jgb/D/tenant-renewal-and-extension-rights` | merge |
| `jgb/D/tenant-rental-insurance` | merge |
| `jgb/D/tenant-sign-steps` | merge |
| `jgb/D/upload-existing-contract` | merge+split-child |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

| 舊細目 | 子細目數 |
|---|---|
| `tmp:kb:tmp:draft:10` | 2 |
| `tmp:kb:tmp:draft:2` | 6 |
