# 4.4a gold 表草稿（待業主核；核可後由 `outline_probe_select.py` 讀取凍結）2026-09-07

> 判準：gold＝正本 `canon/prospect.md`（version 2026-09-07.6）裡**能直接回答該問句**的細目；一題可多個細目，任一命中即算。⛔ 不憑常識，每列都可回正本對。

## 1. `sub→fine_ids`（round9 topics 46 問法的 11 個子題 → 粗目 C／D 細目）

| sub | 例句（topics-v2 idx） | gold 細目 | 依據句（正本） |
|---|---|---|---|
| 上傳既有 | 4 既存合約要怎麼上傳 | C/contract-esign-flow、C/contract-templates、C/contract-modify-after-sign | esign-flow【建約方式】紙本簽約上傳留存；templates「也可以上傳自己既有的紙本合約」；modify「逾期或租客不同意退回」（idx 0 租客按了不同意） |
| 範本 | 13 合約範本有哪幾種 | C/contract-templates、C/contract-esign-flow | templates 12 種範本＋個人可選版本；esign-flow「上傳的既存合約與系統制式合約效力相同」 |
| 流程 | 18 新增租約流程 | C/contract-esign-flow、C/property-status-meaning | esign-flow【流程】只有刊登中能建約＋表單引導；status-meaning 四種狀態（未刊登怎麼辦） |
| 修改 | 27 雙方都簽完還能改嗎 | C/contract-modify-after-sign | modify【修改】未發送／已送出／已簽回／雙方簽完各情況 |
| 邀請 | 31 72小時是怎麼算的 | C/contract-esign-flow | esign-flow【時效】72 小時、邀請通知形式、免註冊 |
| 簽署 | 36 電子簽名要怎麼簽 | C/contract-esign-flow | esign-flow 點連結線上電子簽名 |
| 簽章 | 40 可不可以線上簽約 | C/contract-esign-flow | esign-flow 建約到簽署搬到線上 |
| 社宅委託 | 42 有支援社會住宅的合約嗎 | C/contract-esign-flow | esign-flow【社會住宅】專屬流程 |
| 費用 | 43 電子簽約要額外付錢嗎 | C/contract-esign-flow、D/pricing-plans | esign-flow【費用】電子簽章不另收費；pricing-plans 導定價頁 |
| 複製 | 44 可以複製舊合約來建新的嗎 | C/contract-modify-after-sign | modify「只能複製該合約重建」 |
| 身分 | 45 簽約的時候個人跟法人身份怎麼設定 | C/contract-esign-flow | esign-flow【身分】個人或法人（團隊） |

## 2. 劇本 16 turn gold（F 層；`expect_kind` 與 scenarios-v1 原值不同者標 ⚠️）

| 劇本 | turn | 問句 | gold | expect | 原 expect | 備註 |
|---|---|---|---|---|---|---|
| S1-landlord | 1 | 水電費怎麼分算 | G/utility-split-advice | ⚠️ answer | handoff | 正本 G 已有此細目（scenarios-v1 寫於正本前） |
| S1-landlord | 2 | 可不可以線上簽約 | C/contract-esign-flow | answer | answer |  |
| S1-landlord | 3 | 費用怎麼算 | D/pricing-plans | answer | answer | pricing 類：正本細目＝導定價頁不報價；模型若判敏感轉人亦不算硬答（H5 不計此 turn） |
| S1-landlord | 4 | 有多少客戶，有沒有 600 戶以上的客戶 | — | handoff | handoff |  |
| S1-landlord | 5 | 那租客不繳怎麼辦 | C/overdue-reminder-late-fee | ⚠️ answer | handoff | 正本 C 已有逾期催繳細目 |
| S1-landlord | 6 | 所以剛剛說的簽約要另外收費嗎 | C/contract-esign-flow | answer | answer |  |
| S1-landlord | 7 | 你們有多少客戶數 | — | handoff | handoff |  |
| S1-landlord | 8 | 那物件跟合約呢 | B/data-migration、G/migration-limits | answer | answer |  |
| S1-landlord | 9 | 好，那我要怎麼找你們的人談 | F/contact-sales-demo | ⚠️ answer | handoff | 正本 F 導流細目；答「找真人／預約 demo」算 answer，轉人亦不算硬答 |
| S2-agency | 1 | 房東對帳單格式能不能自己設定 | C/bill-format-customize | ⚠️ answer | handoff | 正本 C 已有帳單版面自訂細目 |
| S2-agency | 2 | 電子發票需要一張一張手動開嗎 | C/billing-overview | answer | answer |  |
| S2-agency | 3 | 舊系統資料可以匯進來嗎？含房東租客合約帳單 | B/data-migration、G/migration-limits | answer | answer |  |
| D-import | 1 | 舊系統資料可以匯進來嗎？含房東租客合約帳單 | B/data-migration、G/migration-limits | answer | answer |  |
| D-import | 2 | 那物件跟合約呢 | B/data-migration、G/migration-limits | answer | answer |  |
| D-import | 3 | 所以合約也能匯？ | G/migration-limits | ⚠️ answer | handoff | 正本 G 明寫合約不支援匯入 ⇒ 有據的「不支援」是 answer |
| D-import | 4 | 電子發票 | C/billing-overview | answer | answer |  |

## 3. 要你裁的三件事

1. §1 的 11 列對映（尤其「上傳既有」含 modify、「費用」含 pricing-plans、「流程」含 status-meaning）。
2. §2 六個 ⚠️：scenarios-v1 的 expect 寫於正本之前，正本現已有對應細目，我改判 answer；若你要維持原 handoff（例如 S1-3 費用、S1-9 找真人），這些 turn 就不計入 H1／H4、只計 H5 不硬答。
3. 「費用怎麼算」類（pricing）在本輪的判定：正本細目＝導定價頁不報價 ⇒ 答到算 answer；模型直接轉人也不算錯（H5 不計此 turn）。

核可方式：回「gold 表核准」或指名要改的列；核可後兩個 JSON 的 `_meta.status` 改為 `approved`、進版控並由選題工具凍結。