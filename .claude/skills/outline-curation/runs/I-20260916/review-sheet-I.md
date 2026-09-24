# 步 2 歸屬審核單（jgb，自動產出）

> 「一致」＝三角度對該舊細目的**歸屬粗目**相同；標 ⚠️ 的是三角度分歧、或合成結果與三角度皆不同。

## A. 舊細目 → 新細目（合成結果）

| # | 舊細目 | 舊標題 | 新 id（粗目） | 新標題 | op | 三角度粗目（user_question_path/content_boundary/audience_level） | 業主 |
|---|---|---|---|---|---|---|---|
| 1 | `tmp:canon:jgb/I/competitor-comparison` | 跟 Bananas、屋我也差在哪 | `jgb/I/competitor-comparison` | 跟 Bananas、屋我也差在哪 | keep | I/I/I | |
| 2 | `tmp:canon:jgb/I/competitor-neutrality` | 會評論競爭對手嗎 | `jgb/I/competitor-neutrality` | 會評論競爭對手嗎 | merge | I/I/I | |
| 3 | `tmp:canon:jgb/I/dashboard-overview` | 首頁儀表板顯示哪些數據 | `jgb/I/dashboard-overview` | 首頁儀表板顯示哪些數據 | keep | I/I/I | |
| 4 | `tmp:canon:jgb/I/data-migration` | 舊系統資料能否匯入（可匯入範圍與不支援項目） | `jgb/I/data-migration` | 舊系統資料能否匯入（可匯入範圍、不支援項目與批次匯入做法） | merge | I/I/I | |
| 5 | `tmp:canon:jgb/I/free-trial` | 可以免費試用嗎 | `jgb/I/free-trial` | 可以免費試用嗎 | keep | I/I/I | |
| 6 | `tmp:canon:jgb/I/individual-landlord-scale-fit` | 個人房東（約 10～30 戶）適配與建議做法 | `jgb/I/individual-landlord-scale-fit` | 個人房東（約 10～30 戶）適配與建議做法 | keep | I/I/I | |
| 7 | `tmp:canon:jgb/I/pricing-plans` | 怎麼收費 | `jgb/I/pricing-plans` | 怎麼收費與方案分級差異 | merge | I/I/I | |
| 8 | `tmp:canon:jgb/I/product-overview` | 系統總覽、能解決什麼問題與適不適合我 | `jgb/I/product-overview` | 系統總覽、能解決什麼問題與適不適合我 | merge | I/I/I | |
| 9 | `tmp:canon:jgb/I/property-quota-limit` | 方案物件額度上限與用滿怎麼辦 | `jgb/I/property-quota-limit` | 方案物件額度上限與用滿怎麼辦 | keep | I/I/I | |
| 10 | `tmp:canon:jgb/I/subscription-change-renewal` | 升級、續約與取消訂閱 | `jgb/I/subscription-change-renewal` | 升級、變更、續約與取消訂閱（含付款紀錄） | merge | I/I/I | |
| 11 | `tmp:canon:jgb/I/team-company-fit` | 公司或包租代管團隊適合嗎 | `jgb/I/team-company-fit` | 公司或包租代管團隊適合嗎 | keep | I/I/I | |
| 12 | `tmp:canon:jgb/I/why-choose-jgb` | 為什麼選金箍棒 | `jgb/I/why-choose-jgb` | 為什麼選金箍棒 | keep | I/I/I | |
| 13 | `tmp:draft:1` | 房東教學：總論篇 | `jgb/I/onboarding-tutorial-index` | 房東新手教學總覽（從哪開始、各篇教學有哪些） | new | I/I/I | |
| 14 | `tmp:kb:3356` | 訂閱 取消 方案 | `jgb/I/subscription-change-renewal` | 升級、變更、續約與取消訂閱（含付款紀錄） | merge | I/I/I | |
| 15 | `tmp:kb:3453` | 訂閱方案 種類差異 | `jgb/I/pricing-plans` | 怎麼收費與方案分級差異 | merge | I/I/I | |
| 16 | `tmp:kb:3454` | 訂閱方案 升級更換 | `jgb/I/subscription-change-renewal` | 升級、變更、續約與取消訂閱（含付款紀錄） | merge | I/I/I | |
| 17 | `tmp:kb:3455` | 取消訂閱 退訂流程 | `jgb/I/subscription-change-renewal` | 升級、變更、續約與取消訂閱（含付款紀錄） | merge | I/I/I | |
| 18 | `tmp:kb:3457` | 訂閱付款紀錄 自動續訂 | `jgb/I/subscription-change-renewal` | 升級、變更、續約與取消訂閱（含付款紀錄） | split | I/I/I | |
| 19 | `tmp:kb:3457` | 訂閱付款紀錄 自動續訂 | `jgb/I/subscription-payment-failure` | 訂閱扣款失敗：方案失效、物件下架與恢復 | split | I/I/I | |
| 20 | `tmp:kb:3476` | 租客批次匯入 Excel | `jgb/I/data-migration` | 舊系統資料能否匯入（可匯入範圍、不支援項目與批次匯入做法） | merge | I/I/I | |
| 21 | `tmp:kb:3509` | 訂閱扣款失敗導致功能異常 | `jgb/I/subscription-payment-failure` | 訂閱扣款失敗：方案失效、物件下架與恢復 | new | I/I/I | |
| 22 | `tmp:kb:3798` | 售前系統脈絡 append（競品協定/CTA/功能索引） | `jgb/I/competitor-neutrality` | 會評論競爭對手嗎 | split | I/I/I | |
| 23 | `tmp:kb:3798` | 售前系統脈絡 append（競品協定/CTA/功能索引） | `jgb/I/product-overview` | 系統總覽、能解決什麼問題與適不適合我 | split | I/I/I | |
| 24 | `tmp:kb:5376` | 費用怎麼算 一年多少錢 收費方式 月費 年費 要花多少 | `jgb/I/pricing-plans` | 怎麼收費與方案分級差異 | merge | I/I/I | |

## B. 拆分（split）——一個舊細目拆成多個新細目

| 舊細目 | 舊標題 | 子細目（新 id《標題》） | 業主 |
|---|---|---|---|
| `tmp:kb:3457` | 訂閱付款紀錄 自動續訂 | `jgb/I/subscription-change-renewal`《升級、變更、續約與取消訂閱（含付款紀錄）》；`jgb/I/subscription-payment-failure`《訂閱扣款失敗：方案失效、物件下架與恢復》 | |
| `tmp:kb:3798` | 售前系統脈絡 append（競品協定/CTA/功能索引） | `jgb/I/competitor-neutrality`《會評論競爭對手嗎》；`jgb/I/product-overview`《系統總覽、能解決什麼問題與適不適合我》 | |

## C. 合併（merge）——多個舊細目併成一個新細目

| 新細目 | 併自 | 理由 | 業主 |
|---|---|---|---|
| `jgb/I/competitor-neutrality`《會評論競爭對手嗎》 | `tmp:kb:tmp:canon:jgb/I/competitor-neutrality`＋`tmp:kb:3798` | 「你們會不會講同業壞話／能不能幫我比」的落點；依兩角度多數，自 tmp:kb:3798 拆出 §5b 競品處理協定併入作為本題的回答邊界（護欄，非新比較內容），其餘段落拆給 product-overview。 | |
| `jgb/I/data-migration`《舊系統資料能否匯入（可匯入範圍、不支援項目與批次匯入做法）》 | `tmp:kb:tmp:canon:jgb/I/data-migration`＋`tmp:kb:3476` | 兩角度多數：tmp:kb:3476 的租客 Excel 批次匯入步驟是既有細目所列「租客可批次匯入」這一項的操作面，離開匯入範圍脈絡即失去導入語義，併入不另立細目。 | |
| `jgb/I/pricing-plans`《怎麼收費與方案分級差異》 | `tmp:kb:tmp:canon:jgb/I/pricing-plans`＋`tmp:kb:5376`＋`tmp:kb:3453` | 三角度一致 merge：tmp:kb:5376 內文與既有細目逐字相同（純講法入口）；tmp:kb:3453 的方案等級差異（物件數、大房東數、進階功能）與「依規模與功能分級收費」是同一命題的兩面；額度用滿另見 property-quota-limit、升級操作另見 subscription-change-renewal。 | |
| `jgb/I/product-overview`《系統總覽、能解決什麼問題與適不適合我》 | `tmp:kb:tmp:canon:jgb/I/product-overview`＋`tmp:kb:3798` | 三角度一致併入 tmp:kb:3798：既有細目以「先選一個您最想改善的」收尾，3798 §7 情境→功能對照索引正是其接續（痛點分流依據）；§6 CTA 出口慣例隨拆分餘段歸此細目作為出口規則、非可回答命題；§5b 拆給 competitor-neutrality。 | |
| `jgb/I/subscription-change-renewal`《升級、變更、續約與取消訂閱（含付款紀錄）》 | `tmp:kb:tmp:canon:jgb/I/subscription-change-renewal`＋`tmp:kb:3454`＋`tmp:kb:3356`＋`tmp:kb:3455`＋`tmp:kb:3457` | 既有細目原內容不動（⛔ 不拆既有）：升級／變更（3454）、取消操作與影響（3356、3455）、自動續訂與付款紀錄（3457 拆出此段）都是訂閱方案頁的正常操作，且既有標題已含「取消訂閱」，同受眾同主題只留一細目；扣款失敗的排障題另見 subscription-payment-failure；3455 與既有內容對取消後果的描述不一致，留待內容審核，本步不判真偽。 | |
| `jgb/I/subscription-payment-failure`《訂閱扣款失敗：方案失效、物件下架與恢復》 | `tmp:kb:3509`＋`tmp:kb:3457` | 兩角度多數判為獨立題：「扣款失敗／功能突然不能用／物件全被下架」是系統事件觸發的排障提問，與使用者主動變更方案的提問路徑不同；依契約以 op=new 只掛新材料（3509 整筆＋3457 扣款失敗段），既有 subscription-change-renewal 的一句扣款失敗摘要不動、以另見銜接；3509 與 3457 對失效時點（立即清除 vs 補繳期限後降免費版）描述不一致，留待內容審核。 | |

## D. 合成否決的替代方案（⚠️ 你可以翻案）

| 被否決 | 理由 | 業主 |
|---|---|---|
| user_question_path／content_boundary：把既有 subscription-change-renewal 以 op=split 拆成兩題（變更＋扣款失敗）或三題（變更／取消／扣款失敗） | 契約規定既有細目只准 keep 或 merge、⛔ 不拆既有；扣款失敗改以 op=new 只掛新材料（3509＋3457 段）另立細目，既有內容原封不動、以另見銜接。 | |
| content_boundary：另立 jgb/I/subscription-cancel（取消訂閱的操作與影響），掛 3356、3455 並自既有細目拆出取消句 | 1:2 少數；既有標題已含「取消訂閱」，再立取消細目會造成同受眾同主題兩細目、違反互斥；且取消與變更同在訂閱方案頁、同屬正常操作，3356／3455 併入既有細目即可。 | |
| audience_level：把 3509 與 3457 的扣款失敗段一併併入 subscription-change-renewal，訂閱管理只留一細目 | 1:2 少數；扣款失敗是系統事件觸發的排障提問，與使用者主動變更方案的提問路徑不同，3509 整筆可獨立回答，另立細目不重複既有內容。 | |
| audience_level：以 3476 另立 jgb/I/bulk-import-operations（批次匯入操作步驟，操作層） | 1:2 少數；3476 只有租客一種匯入步驟，單一來源不足以撐「批次匯入操作」整題，且它正是既有 data-migration 所列「租客可批次匯入」的操作面，併入不另立。 | |
| audience_level：3798 整筆併入 product-overview、competitor-neutrality 純 keep 不吸收 §5b | 1:2 少數；§5b 競品處理協定是「會不會評論同業」這一題的回答邊界（護欄、非比較內容），留在 product-overview 與該題無關；拆段各歸其題。 | |
| content_boundary：product-overview 標題改為「…（含情境→功能索引與出口）」並把 §6 CTA 視為細目內容 | 兩角度多數認 §6 是出口慣例／路由規則、非可回答命題；3798 餘段仍映射到 product-overview 作為來源，但標題維持原題不擴。 | |
| user_question_path：draft:1 的導入教學總覽 target_user 同列 prospect 與 property_manager | 1:2 少數；正文以「歡迎您加入」對已註冊管理者說話，屬導入後的操作入口；潛在客戶的「導入要做什麼」由 data-migration／free-trial 路徑承接。 | |
| draft:1 新細目 slug 取 onboarding-steps-overview（角度一）或 landlord-onboarding-guide（角度三） | 三角度各提一個 id，擇一：取 onboarding-tutorial-index，因兩角度皆定性為「只保留各篇索引不展開」，index 最貼近細目實質。 | |
| subscription-change-renewal 標題採角度三「升級、續約、取消訂閱與扣款失敗處理」 | 扣款失敗已另立細目，標題含它會造成兩細目同題；改為「升級、變更、續約與取消訂閱（含付款紀錄）」反映併入的 3454／3356／3455／3457 段。 | |
| content_boundary：2909、2925 租金行情／市場變化歸 D（租金由租約決定） | 1:2 少數；租金行情與市場變化是錢怎麼算的參考，非合約條款所定，依多數歸 E。 | |
| audience_level：2918 支付期限、2920 折扣條件歸 D（由合約條款決定） | 1:2 少數；支付期限即帳單繳款期、折扣是租金計算，依「出現在帳單列上／錢怎麼算歸帳務」歸 E。 | |
| user_question_path：3158 業者服務費、3209 租金包含項目歸 E | 1:2 少數；服務費比例與租金包含項目皆由合約（委託約／租約）條款決定，依「由合約條款決定的歸租約」歸 D。 | |
| content_boundary：3478 邀請租客訂閱通知歸 B（人員管理操作）；audience_level：歸 A（租客帳號綁定） | 三角度各異、無多數；依歸位判準「通知歸它所通知的領域」裁決：通知內容為帳單與繳費提醒，歸 E。 | |

## E. 粗目分佈（合成後）

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 |

## F. 待審清單

⚠️ 本表只列結構上可預測的部分——本腳本輸入不含既有正本（`--canon`），讀不到舊細目的實際講法／`see_also`／`reviewed`，故不假裝算得出 `pending-*.json` 的實際筆數；確切筆數要 `apply_proposal.py --canon` 實際套用後看 `pending-splits.json`／`pending-phrasings.json`／`pending-see_also.json`。

### F1. 套用後會失去既有 `reviewed`（內容因 merge／split 改變）的新細目

| 新細目 | 原因 |
|---|---|
| `jgb/I/competitor-neutrality` | merge+split-child |
| `jgb/I/data-migration` | merge |
| `jgb/I/pricing-plans` | merge |
| `jgb/I/product-overview` | merge+split-child |
| `jgb/I/subscription-change-renewal` | merge+split-child |
| `jgb/I/subscription-payment-failure` | merge+split-child |

### F2. 會產生 `pending-splits.json`／`pending-phrasings.json` 的拆分來源

| 舊細目 | 子細目數 |
|---|---|
| `tmp:kb:3457` | 2 |
| `tmp:kb:3798` | 2 |
