# -*- coding: utf-8 -*-
"""Plan 9.28 誘餌（正對照）：取已全數核對過的 18 條（9.23～9.25 write 證據）之一，恰改一句的關鍵事實。
每項：(來源細目 id, 句序 n, 原片段, 改後片段, 誘餌 slug, 誘餌標題)；第 k 項配給批 B{k}。
原片段必須在該句中恰出現一次；誘餌 id（jgb/<來源架>/<slug>）與標題不得與正本既有細目相同（gen_briefs 斷言）。
排序讓誘餌的架儘量與該批相同（A→B01～B05、C→B06～B09、D→B10～B14、其餘批無同架誘餌）。"""
DECOYS = [
    # B01～B05：A 架
    ("jgb/A/account-contact-info", 3, "欄位長度上限 200 字元", "欄位長度上限 100 字元",
     "contact-info-social-fields", "聯絡資訊的 LINE、Facebook、WhatsApp 欄位怎麼填？"),
    ("jgb/A/account-change-password", 3, "「目前密碼驗證錯誤」", "「目前密碼輸入錯誤」",
     "password-form-validation", "帳號資訊頁修改密碼時要填哪些欄位？填錯會怎樣？"),
    ("jgb/A/account-change-password-rules", 1, "新密碼長度需至少 6 個字元", "新密碼長度需至少 8 個字元",
     "new-password-length", "帳號資訊頁設定新密碼有長度限制嗎？"),
    ("jgb/A/account-contact-info", 5, "第二組聯絡號碼欄位長度上限 50 字元", "第二組聯絡號碼欄位長度上限 30 字元",
     "contact-info-second-phone", "聯絡資訊可以填第二組聯絡電話嗎？"),
    ("jgb/A/account-change-password", 4, "則顯示帳號建立的時間", "則顯示「尚未更新」",
     "password-last-updated", "密碼區塊的「上次更新」顯示什麼時間？"),
    # B06～B09：C 架
    ("jgb/C/estate-dashboard-attachments-vs-contract-attachments", 1, "每個物件最多存放 5 個檔案", "每個物件最多存放 8 個檔案",
     "estate-attachment-storage", "物件的附件清單可以放幾個檔案？"),
    ("jgb/C/estate-dashboard-runnings-vs-memos", 2, "最多 3 個附件", "最多 5 個附件",
     "landlord-ledger-entry", "房東流水帳新增一筆要填什麼？可以附檔嗎？"),
    ("jgb/C/team-public-page-recruitment", 5, "多團隊招募頁每頁預設顯示 10 筆", "多團隊招募頁每頁預設顯示 20 筆",
     "recruitment-page-size", "招募頁與招租店舖每頁顯示幾筆物件？"),
    ("jgb/C/community-pick-next-step", 2, "系統會直接建立一份副本並進入新社區的編輯頁", "會先跳出確認視窗，按「確定」後建立副本並回到社區列表",
     "community-copy-flow", "複製社區、在社區新增物件，選好社區之後會發生什麼？"),
    # B10～B14：D 架
    ("jgb/D/contract-show-panels", 2, "租客看到「合約點交中，請確認點交結果」，其他身分（例如房東方）看到「合約點交中，等待承租方確認」",
     "租客看到「合約點交中，等待承租方確認」，其他身分（例如房東方）看到「合約點交中，請確認點交結果」",
     "social-housing-handover-notice", "社宅合約點交、點退進行中時，檢視頁會顯示什麼提示？"),
    ("jgb/D/contract-upload-existing-vs-electronic", 6, "畫面上的單檔大小上限是 15 MB，超過會提示重新上傳小於 15 MB 的檔案",
     "畫面上的單檔大小上限是 20 MB，超過會提示重新上傳小於 20 MB 的檔案",
     "paper-contract-upload-limits", "紙本簽約和電子合約在建立時有什麼不同？"),
    ("jgb/D/general-contract-notary-tab", 4, "三個強制執行事項會預設全部勾選", "三個強制執行事項會預設全部不勾選",
     "notary-enforcement-items", "一般合約的公證分頁要怎麼設定強制執行事項？"),
    ("jgb/D/contract-upload-existing-vs-electronic", 2, "的說明是「自製合約模板」", "的說明是「上傳自己的合約」",
     "contract-create-method-menu", "按「建立合約」後可以選哪幾種建立方式？"),
    ("jgb/D/general-contract-notary-tab", 1, "要先選擇這份租賃合約是否「同意辦理」公證", "預設就已經「同意辦理」公證，不需要另外選擇",
     "notary-agree-option", "哪些合約範本可以在公證分頁選擇辦理公證？"),
    # B15～B20：其餘
    ("jgb/A/account-change-password-rules", 2, "但按「儲存」時不會檢查這一條", "按「儲存」時沒有英文和數字的密碼會被擋下",
     "password-alnum-hint", "改密碼時「至少一位英文和數字」是強制的嗎？"),
    ("jgb/C/estate-dashboard-attachments-vs-contract-attachments", 8, "授權代理人簽約同意書最多 2 份", "授權代理人簽約同意書最多 4 份",
     "contract-attachment-quota", "合約附件每個項目可以上傳幾份？"),
    ("jgb/C/estate-dashboard-runnings-vs-memos", 4, "沒有收入支出的金額欄位", "也要填收入或支出的金額",
     "estate-notebook-entry", "物件記事本新增一筆要填什麼？"),
    ("jgb/C/team-public-page-recruitment", 2, "補上「住宅」用途", "補上「商用」用途",
     "public-page-purpose-redirect", "招募頁網址沒帶物件用途時會怎樣？"),
    ("jgb/C/community-pick-next-step", 4, "會接著進入挑選要複製哪一個物件的畫面", "會直接複製該社區的第一筆物件並進入編輯頁",
     "community-pick-copy-estate", "從社區選擇畫面複製物件，下一步是什麼？"),
    ("jgb/C/estate-dashboard-runnings-vs-memos", 1, "說明與對象可以留空", "說明與對象都是必填",
     "ledger-required-fields", "房東流水帳哪些欄位必填？"),
    # B21～B24：I 架
    ("jgb/I/pricing-quota-full-block", 4, "按鈕文字是「前往升級」", "按鈕文字是「立即升級」",
     "quota-full-upgrade-dialog", "物件數量到上限時會跳出什麼視窗？"),
    ("jgb/I/pricing-quota-full-block", 5, "按鈕文字是「我要訂閱」", "按鈕文字是「前往訂閱」",
     "quota-full-no-subscription", "沒有訂閱時新增物件達上限會看到什麼？"),
    ("jgb/I/pricing-free-trial-eligibility", 1, "不綁信用卡的30天的試用方案", "不綁信用卡的14天的試用方案",
     "free-trial-length", "免費試用方案可以用多久？要綁信用卡嗎？"),
    ("jgb/I/pricing-free-vs-experience-plan", 1, "可以創建 10 個物件", "可以創建 20 個物件",
     "experience-plan-quota", "體驗方案可以建幾個物件？"),
]
