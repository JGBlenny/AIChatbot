# 包租／代管 18 客群 × 九架正本覆蓋表 — 2026-09-17

> 來源：`~/Downloads/JGB租房管理系統 - 20大客群營運維度與PM拆解 by Joan - Brian update3.xlsx`（單一工作表 35 客群；業主 2026-09-17 縮限「目前只需要包租／代管」⇒ 類型欄含「包租」或「代管」的 18 個）。
> 對照物：工作樹九架正本 `rag-orchestrator/canon/jgb/A–I.md`（210 細目，sha 前綴 `b94acd638e35`）。
> 業態對應：文件「代管」＝`business_types: property_management`、「包租」＝`full_service`（`docs/architecture/DATABASE_SCHEMA.md` 業態值定義）；正本 210 條目前全標 `[system_provider]`，尚未依業態分流。
> ⚠️ 「缺」只代表正本沒有這條細目；產品有沒有這個功能要走 skill 步 5b（對 jgb2 程式／幫助中心）查證，⛔ 不得在正本補造功能。

## 1. 18 客群

⚠️ DSP-060（2026-09-17）排除商務中心／共享空間客群：下表 34、35、20、36 四列雖在來源表標「包租、商用」，⛔ 不在售前範圍，列出只為標明排除；實際範圍＝其餘 14 個客群。

| 編號 | 類型 | 客群 | 規模 | 代收 |
|---|---|---|---|---|
| 1 | 代管 仲介 | 想投入代管的仲介個人 | 微 | 無 |
| 2 | 代管 | 管理 10 間以內的代管個人 | 微 | 無 |
| 5 | 代管 仲介 | 想投入代管的仲介店老闆 | 小 | 無 |
| 6 | 代管 仲介 | 仲介店老闆（收金流） | 小 | 有 |
| 21 | 代管 | 20 間以內微型代管公司（剛立案） | 微 | 有 |
| 7 | 代管 | 50 間以內代管公司 | 小 | 有 |
| 9 | 代管 仲介 | 跨國仲介 50 戶 | 小 | 有 |
| 10 | 代管 仲介 | 跨國仲介 200 戶 | 中 | 有 |
| 22 | 代管 | 500 間以上大型代管公司 | 大 | 有 |
| 4 | 包租 | 個人包租（斜槓合股） | 微 | 有 |
| 23 | 包租 | 20 間以內包租工作室 | 微 | 有 |
| 14 | 包租 | 室內設計轉職創業者 | 小 | 有 |
| 15 | 包租 | 100–200 間包租公司 | 中 | 有 |
| 16 | 包租 | 500 間包租公司 | 大 | 有 |
| 34 | 包租、商用 | 微型共享空間／工作室 | 微 | 有 |
| 35 | 包租、商用 | 商務中心小型單店 | 小 | 有 |
| 20 | 包租、商用 | 商務中心 | 中 | 有 |
| 36 | 包租、商用 | 連鎖商務中心／共享辦公 | 大 | 有 |

## 2. 痛點主題 × 正本覆蓋（依出現客群數排序）

狀態：✅ 有細目直接答；🟡 有相近細目但沒答到痛點本身；❌ 正本無此細目（產品有無待 5b 查證）。

| 痛點主題 | 客群 | 狀態 | 對應細目（id） | 缺口說明 |
|---|---|---|---|---|
| 收租自動對帳／銀行匯入沖帳 | 2,6,21,7,22,15,16,34,35,20,36 | ✅ | E/bill-status-reconciliation、E/cash-bank-account-collection、E/payment-gateway-setup、E/virtual-account-transfer、E/fixed-virtual-account-management | 已審的只有 0 條（皆未審） |
| 逾期催繳（批次、分級、LINE） | 1,2,5,6,21,7,15,23 | 🟡 | E/overdue-reminder-late-fee、E/dunning-draft-template-tone-late-fee、E/dunning-draft-not-auto-send、E/late-fee-calculation | 「批次催繳／逾期分級」沒有細目；且系統催繳草稿不可一鍵發送（E/dunning-draft-not-auto-send），售前要誠實講 |
| 屋主月報／代收代付分戶帳 | 1,2,5,6,21,7,22,9,10 | ✅ | B/owner-report-collection-remit、E/landlord-owner-bills、E/rent-collection-agent-vs-direct、B/add-owner-landlord-and-access | 「排程自動寄送」「分戶帳餘額查詢」是否存在待查 |
| 電子簽約／續約提醒／版本管理 | 1,2,5,6,21,7,15 | ✅ | D/contract-esign-flow、D/contract-templates、D/contract-batch-renewal、D/renewal-flow、D/esign-legal-validity、D/lease-expiry-followup-scope | — |
| 修繕工單：派工、外包廠商、費用歸屬 | 1,2,5,6,21,7,15,22 | 🟡 | F/repair-dispatch-and-close、F/repair-cost-recording-and-settlement、F/repair-flow-stages、F/repair-system | 「外包廠商名冊」「工單 SLA／廠商評核」無細目 |
| 權限分層（店長／業務／行政／財務） | 5,6,7,22,15,16,10,36 | ✅ | B/role-permission-granularity、B/who-has-permission-lookup、B/add-team-member | 「多據點分區權限」「操作留痕／稽核紀錄」無細目 |
| Excel／紙本無痛匯入 | 2,21,7 | ✅ | I/data-migration、C/property-batch-import、E/manual-bill-creation（Excel 批次） | — |
| 低月費／依戶數計價／免費入門 | 1,2,21,23,34 | ✅ | I/pricing-plans、I/free-trial、I/property-quota-limit、I/individual-landlord-scale-fit | 「Freemium 單一物件免費」與現行方案是否相符待查 |
| 押金管理與退租結算 | 21,7,23,15 | ✅ | D/deposit-setting-and-refund-system、D/return-checkout、E/checkout-bill-settlement、D/lease-end-checkout-overview | — |
| 租賃法規／公版契約／合規 | 1,21 | ✅ | D/contract-templates（內政部新制）、B/leasing-management-license-and-staff-qualification、D/deposit-legal-limits | — |
| 發票／統編／差額發票 | 6,34,35,20,36 | ✅ | E/einvoice-issuing、E/differential-invoice、E/invoice-void-reissue | 「企業客戶月結帳單」無細目 |
| 儀表板／營運數字（收租率、空置率） | 7,22,16,36 | 🟡 | I/dashboard-overview、C/occupancy-rate-calculation、E/bill-reports-export | 「戰情室 BI、分區比較、催收率」無；大型客群核心痛點 |
| **雙合約關聯（原屋主約 vs 轉租約）到期錯配預警** | 4,23,14,15 | 🟡 | D/sublease-vs-management-contract、D/delegation-vs-lease-contract、D/delegation-contract-flow | 包租四個客群的第一痛點；正本只講「差別」，沒有「兩份約關聯與到期預警」 |
| **利差精算／單間損益／裝修攤提／回本試算** | 4,23,14,15,16 | ❌ | — | 包租核心；產品是否有任何損益工具待查 |
| **提前解約損益試算** | 23,14,15 | 🟡 | D/early-termination-penalty、D/early-termination-flow | 有違約金算法，無「損益一鍵試算」 |
| **空置看板／招租漏斗／平均空置天數** | 4,23,15,16 | 🟡 | C/occupancy-rate-calculation、C/property-status-meaning、C/rental-storefront-vr | 只有出租率；無看板／漏斗 |
| **合夥分帳／股東報表** | 4,14 | ❌ | — | 產品極可能無；售前應誠實 |
| **任務指派／待辦清單／業務派單／佣金** | 1,2,4,5,6 | ❌ | — | 仲介轉代管客群的第一痛點；產品有無待查 |
| **物件現況報告書／電子名片頁（開發屋主信任工具）** | 1,2,21,5 | 🟡 | C/community-public-page、C/storefront-entry-share | 「現況報告書」無 |
| **租客 Chatbot 自動客服** | 4,23,14 | ❌ | — | 這是本 AI 客服自己；正本無「AI 客服能做什麼」細目，I 架應補 |
| LINE 通知（收租、到期、修繕進度） | 1,2,5,21,7,15,34,35 | 🟡 | E/overdue-reminder-late-fee（訂閱通知）、F/repair-flow-stages | DSP-049 通知＝細目屬性，但沒有一條專講「通知通道與能通知什麼」 |
| 手機版完整操作 | 1,2,4,21,23,34 | ❌ | — | 產品事實：JGB 無 APP、Web 內嵌（記憶）；需一條細目說清楚 |
| ERP 財會／月結關帳／分錄／稽核留痕 | 22,16 | ❌ | — | 大型客群；產品有無待查 |
| 客服案件中心／SLA | 22,16,36 | ❌ | — | 同上 |
| 多語系／多幣別／多時區／跨境簽章 | 9,10 | ❌ | — | 跨國仲介兩客群整組無；產品有無待查 |
| 座位／會議室預訂、彈性計費、點數、會員、門禁連動 | 34,35,20,36 | ❌ | G/smart-lock-*（門鎖僅住宅情境） | 商務中心四客群幾乎整組無；屬產品範疇問題，不是知識缺口 |
| IoT 電表／門鎖 | 20,36（門禁）、（住宅客群隱含） | ✅ | G/* 11 條 | 商用門禁情境無 |

## 3. 結論

1. **代管十客群**：核心痛點（對帳、催繳、屋主月報、電子簽約、修繕工單、權限、匯入、方案）正本大多有細目，但 E 架（帳務）48 條全未審、催繳有「不可一鍵發送」的產品限制要誠實講；缺的是外包廠商名冊、批次催繳分級、操作留痕、戰情 BI。
2. **包租八客群**：第一痛點「雙合約關聯與到期錯配」「利差／損益／攤提試算」正本整組沒有；商用四客群（共享空間、商務中心）的需求與 JGB 租房產品幾乎不交集，應先裁「售前對這四客群怎麼回」再談知識。
3. **共通缺口**：「AI 客服能做什麼」（賣的就是這個）、「手機怎麼用」、「通知通道」三條售前必答的細目不存在。
4. **下一步（不需裁決即可做）**：對表中 ❌／🟡 且標「待查」的 12 項跑 skill 步 5b（jgb2 程式＋幫助中心）查產品事實 → 有的補細目、沒有的寫進 I 架「不支援項目」讓售前誠實答。需裁決：商務中心四客群是否納入售前範圍；業態軸是否依 `property_management`／`full_service` 分流細目。

## 4. 產品有無：唯讀 scout 對 jgb2 `master`＋幫助中心的查證（2026-09-17）與處置

裁決 DSP-060 後對 §2 的 12 項「待查」跑唯讀 scout，主會話再以 `git grep -c <pat> master -- app/ database/migrations/ routes/` 補正對照（`EntrustedContract` 445、`late_fee_percent` 18、`SendBiglandlordMonthlyReportChunkJob` 4 命中）；scout 四項「無」中兩項被推翻（空置、任務），兩項成立（ERP 稽核、客服案件）。

| 項目 | 產品 | 證據 | 處置 |
|---|---|---|---|
| 修繕外包廠商（派單、廠商名稱電話） | 有 | `app/Http/Controllers/RepairController.php`；幫助中心 `repair_zh-Hant.html` §安排修繕 | **補細目**（F 架：業者派廠商與廠商資訊怎麼記） |
| 批次催繳／逾期分級 | 部分 | `app/Bill.php:late_fee_percent`／`late_fee_info`、`BillAmercementNotify.php` | 補細目講「逾期滯納金＋自動催繳通知」；「分級」寫不支援（待 5b 核） |
| 屋主月報排程寄送 | 有 | `app/Jobs/SendBiglandlordMonthlyReportChunkJob.php`、`app/Services/BiglandlordReportSendService.php` | 既有 B/owner-report-collection-remit 補「排程寄送」內容 |
| 分戶帳餘額查詢 | 查無 | 只見 `BigLandlordReportViewerScope` | 待 5b 核後寫「不支援」 |
| 雙合約關聯與到期預警 | 部分 | `app/EntrustedContract.php`；`LEASE_TYPE_CHARTER`／`LEASE_TYPE_MANAGEMENT` | 補細目：委託約與租賃約分開管理、狀態自動更新；「到期錯配預警」寫不支援 |
| 利差／單間損益／裝修攤提 | 部分 | `app/Services/Communities/CommunityRoiService.php`；`BillServiceTotalAmountAmortizationTest.php` | 補細目：社區層級投報率怎麼看；「單間利差、裝修攤提」寫不支援 |
| 提前解約違約金 | 有 | `app/Contract.php:CONTRACT_EARLY_TERMINATION`；`EarlyTerminationPenaltyValidationTest.php` | 既有 D/early-termination-penalty 已覆蓋；「損益一鍵試算」寫不支援 |
| 空置看板／招租漏斗／平均空置天數 | 部分 | `app/Http/Controllers/CommunityController.php::sortOptionsMap($withVacancySort)`（社區清單可依空置數排序）；`resources/structures/estate/dashboard/rent_status.php`（出租狀態看板） | 補細目：社區空置數排序與出租狀態看板；「招租漏斗、平均空置天數」寫不支援 |
| 任務指派／派單／佣金 | 部分 | `app/Task.php`（`tasks`：週期任務、`notification_recipient`／`notification_content`、`is_complete`）；`Commission` 0 命中 | 補細目前先查 `tasks` 在 UI 的入口與用途（待辦／週期提醒）；「業務派單、佣金」寫不支援 |
| 物件現況報告書／電子名片頁 | 部分 | 幫助中心 `Landlordonboarding09Socialhousing_zh-Hant.html` §現況補充 | 只有社宅簽約流程的現況照片；「現況報告書／名片頁」寫不支援 |
| ERP 財會（月結、分錄、稽核留痕） | 無 | `journal_entry`／`closing_period` 0 命中；`AuditLog` 31 命中皆為 `app/Modules/CustomerService/Shared/Traits/AuditLog`（AI 客服 API 模組的留痕，非產品財會功能） | 寫進 I 架「不支援項目」；E/bill-reports-export 補「清冊匯出」邊界 |
| 客服案件中心／SLA | 無 | `SupportTicket`／`class Ticket`／`sla` 0 命中（正對照同語料 445 命中） | 寫進 I 架「不支援項目」 |
| 通知通道與事件 | 有 | `app/Notification.php`「通知渠道：簡訊、通知中心、email」；`SmsJob.php`；幫助中心 repair 頁「綁定 Line 也會收到通知」 | **補細目**（跨架屬性 DSP-049 之外，另立一條「通知通道能通知什麼」） |
| 手機 APP | 無原生 APP，Web 內嵌 | scout；記憶 `project_jgb_product_context` | **補細目**（I 架：手機怎麼用） |
| AI 客服能做什麼 | — | 本系統自身 | **補細目**（I 架；內容來自 `agent_rules`／工具清單，非 jgb2） |

**兩個範圍事實**：
- 幫助中心明確寫到**社會住宅**與包租代管；未提商務中心、共享辦公、學校宿舍。⚠️ DSP-060 把「政府社宅」客群排除在售前範圍外，但產品支援社宅、正本已有社宅細目（D/social-housing-lease、F/social-housing-repair-responsibility、C 社宅綁定）——**交業主**：社宅是「不主動經營的客群」還是「不支援」，兩者售前答法不同。
- 權限模型（`config/character.php`、`Role`）無分區／據點欄位 ⇒ 大型客群「多據點分區權限」寫不支援。

**處置彙總**：補細目：草稿代理（`.claude/skills/outline-curation/runs/expand2-20260918/drafts.json`）判定新細目 7 條（社區投報率、社區空置排序、任務管理器週期任務、通知通道、手機、AI 客服、不支援項目）＋補句 3 條（催繳、委託約與租賃約、團隊適配含社宅／商務中心）；廠商派單與月報排程既有細目已完整覆蓋、不另寫；出租狀態看板 `rent_status.php` 全庫零引用判死碼不寫；「不支援」10 項（逾期分級、分戶帳餘額、到期錯配預警、單間利差／裝修攤提、損益一鍵試算、招租漏斗、業務派單／佣金、ERP 財會、客服案件中心、多據點分區權限）寫進 I 架一條「目前不支援的功能」細目（售前誠實答、不導引）。
