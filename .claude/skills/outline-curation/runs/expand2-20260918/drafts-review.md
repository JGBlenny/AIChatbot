# expand2-20260918 草稿逐項紀錄

⛔ 未觸碰 `rag-orchestrator/canon/`；本檔只列決策與查證，不落正本。

## 1. F｜修繕派廠商與廠商資訊怎麼記

決定：**⛔ 不寫（已覆蓋，非新增非補句）**

既有細目 `jgb/F/repair-dispatch-and-close`（標題「業者受理報修、安排廠商、完工登錄到結單封存的操作」）已完整涵蓋：填入廠商名稱與聯絡電話、安排修繕狀態轉換、完工日期／說明／完工照片／結算金額、結單封存。內容與 jgb2 `RepairController.php` 的 `assign_logs`（`repairer_name`／`vendor_name`／`vendor_phone`）、幫助中心 `repair_zh-Hant.html` §安排修繕 逐項對應，找不到既有細目沒答到的產品事實。

查證：
- `git -C jgb2/dev2 show master:app/Http/Controllers/RepairController.php | sed -n '1420,1450p'` → `assign_logs`（`vendor_name`／`vendor_phone`／`repairer_name`）欄位存在
- `grep -n "安排修繕" 幫助中心/repair_zh-Hant.html` → 「填寫廠商資訊，填入安排的修繕時間、廠商名稱、維修人員和聯絡電話」

## 2. E｜逾期滯納金與自動催繳通知怎麼運作

決定：**append → `jgb/E/overdue-reminder-late-fee`**

既有 `jgb/E/overdue-reminder-late-fee`（到期前五三一日提醒、逾期後每日提醒、訂閱通知）與 `jgb/E/late-fee-calculation`（滯納金三種客製版本：延遲金／階梯式／固定金額）已完整覆蓋計算與自動通知機制本身。唯一真缺口＝「逾期分級」（依逾期嚴重度分級催繳強度或升級處理，例如轉銷售/法務）：程式與帳單模型無此欄位或邏輯，補一句不支援聲明掛在 `overdue-reminder-late-fee`。

查證：
- `git -C jgb2/dev2 grep -n "late_fee_percent\|late_fee_info" master -- app/Bill.php` → 欄位存在（正對照）
- `git -C jgb2/dev2 grep -ic 分級 master -- app/Bill.php app/Console/Commands/BillAmercementNotify.php` → 0

## 3. B｜大房東月報排程自動寄送

決定：**⛔ 不寫（已覆蓋，非新增非補句）**

既有 `jgb/B/owner-report-collection-remit` 標題就含「排程寄送」，內容已列排程可選每月／每季／每半年／每年、確認信、每次寄送前預告通知、設定入口在大房東管理的報表排程功能——與 jgb2 `SendBiglandlordMonthlyReportChunkJob.php`／`BiglandlordReportSendService.php` 的批次寄送設計逐項吻合，無新增空間。

查證：
- `git -C jgb2/dev2 show master:app/Jobs/SendBiglandlordMonthlyReportChunkJob.php | head -30` → 分塊寄送、逐筆記錄進度，與既有細目描述一致

## 4. D｜委託約與租賃約分開管理、狀態自動更新

決定：**append → `jgb/D/delegation-vs-lease-contract`**

既有兩條細目（`delegation-vs-lease-contract` 講差別、`delegation-contract-flow` 講建立簽署與提前終止流程）沒有講「狀態自動更新」這件事本身，也沒有「兩份約到期錯配預警」的不支援聲明。補三句到 `delegation-vs-lease-contract`（狀態排程自動更新到歷史、提前終止緩衝期屆滿自動生效、無錯配預警）。

查證：
- `git -C jgb2/dev2 show master:app/Console/Commands/EntrustedContractStatusUpdater.php | head -25` → `entrusted-contract:update history|early-termination` 兩個排程動作
- `git -C jgb2/dev2 grep -rn "錯配\|mismatch" master -- app/EntrustedContract.php app/Contract.php` → 0（正對照：同指令對 `AuditBillTotalMismatch.php` 等帳務對帳指令有命中，工具正常）
- `docs/knowledge/jgb-product-facts.md#single-vs-dual-contract` → 已記錄委託約／租賃約獨立並存、無關聯欄位

## 5. C｜社區投報率怎麼看

決定：**new → `jgb/C/community-roi-overview`**

程式 `CommunityRoiService.php` docstring 完整說明計算單位（社區）、分子（當月獲利）、分母（累計投入成本）、刻意不做的兩件事（不查重複計算、無投入成本月份留空）。有真實 API 入口 `CommunityRoiController.php` 與路由 `routes/web.php` 的 `roi` prefix。幫助中心查無對應頁，純靠 jgb2 程式佐證，屬合理（此類財務計算細節本就不進教學頁）。

查證：
- `git -C jgb2/dev2 grep -ln CommunityRoiService master -- app/Http/Controllers` → `Api/CommunityRoiController.php`
- `git -C jgb2/dev2 grep -n roi master -- routes/web.php` → `Route::prefix('roi')->namespace('Api')`

## 6. C｜社區依空置數排序與出租狀態看板

決定：**new（僅排序半段）→ `jgb/C/community-list-vacancy-sort`；看板半段⛔不寫**

`sortOptionsMap($withVacancySort)` 確實提供「空置數量(多至少/少至多)」排序，且用在真實路由 `CommunityController::webList`（`routes/web.php` 有 `Route::prefix('communities')->group` 下的 `list` 路由指到 `webList`）。但「出租狀態看板」(`resources/structures/estate/dashboard/rent_status.php`) 全庫 **0 處**被任何 controller/route 引用——同目錄 `structures/common/sortOptions.php` 這種「結構示意」檔在 `BillController`／`ContractController` 有多筆真實 `require resource_path(...)` 引用（正對照，證明「查無引用」不是工具或路徑錯誤）。判定該 dashboard 檔是未串接的死碼／示意稿，⛔ 不寫入正本、也不算產品支援看板功能。

查證：
- `git -C jgb2/dev2 grep -n withVacancySort master -- app/Http/Controllers/CommunityController.php` → 命中，`sortOptionsMap(true)` 用於 `webList()`
- `git -C jgb2/dev2 grep -rn "structures/estate/dashboard\|dashboard/rent_status" master -- app/ resources/ routes/` → 0
- `git -C jgb2/dev2 grep -c "require resource_path" master -- app/Http/Controllers/ContractController.php` → 4（正對照：structures 引用模式本身在別處是活的）

## 7. B or I｜週期任務與通知

決定：**new → `jgb/I/task-manager-cycle-notification`（放 I 架，理由見下）**

找到真實 UI 入口：`routes/web.php` `controlPanel/taskManagement`（「控制台」>「任務管理器」），在全站 `need_login` 中介層群組內（一般登入使用者可用，非後台限定）。`TaskService::getTypeOptions()` 顯示任務類型目前只有 `notification`（`repair` 類型的程式碼被整段註解掉、未啟用），`getCycleOptions()` 顯示週期單位年/月、方式僅一次/持續不停/特定日期結束/重複特定次數。

放架理由：B 架 scope 明訂「團隊建立與成員邀請、角色權限、人員管理、大房東記錄」，任務管理器不屬其中任一項；I 架已收容其他跨系統總覽型細目（dashboard-overview、product-overview），與本細目性質更接近，故放 I。

查證：
- `git -C jgb2/dev2 grep -n taskManagement master -- routes/web.php` → 位於 `need_login` 群組
- `git -C jgb2/dev2 show master:app/Services/TaskService.php | sed -n '420,445p'` → `type.value == 'notification'`，`repair` 選項整段被註解

## 8. A or I｜通知通道能通知什麼

決定：**new → `jgb/I/notification-channels-and-events`（放 I 架，理由同上：A 架 scope 是帳號／身分，通知通道不屬此）**

`app/Notification.php` 明確列出通知渠道註解「簡訊、通知中心、email」，以及七類通知事件常數（物件／合約／帳務／修繕／裝置／訊息／大房東）。幫助中心 `repair_zh-Hant.html` 多處確認租客綁定 LINE 會同步收到通知。

查證：
- `git -C jgb2/dev2 show master:app/Notification.php | sed -n '15,54p'` → `NOTIFICATION_TITLE` 七類常數＋渠道註解
- `grep -o ".\{20\}綁定Line.\{40\}" 幫助中心/repair_zh-Hant.html` → 三處命中

## 9. I｜手機怎麼用

決定：**new → `jgb/I/mobile-web-access`**

幫助中心直接有一頁教學「大房東教學：瀏覽物件、合約、帳務和修繕狀態（手機篇）」，內文逐字：「JGB 沒有另外的 APP，它是純網頁系統，手機請直接開啟瀏覽器登入，網址與電腦版相同」「手機版與電腦版是同一套系統、同一組功能，差別只在畫面會依螢幕寬度調整排列方式」。這是目前查到的最直接第一手來源，優於原先預期的「查 jgb2 responsive class」路徑。另以 `resources/views/layouts/app.blade.php` 的 viewport meta 佐證技術面響應式設計。

查證：
- `grep -o "JGB 沒有另外的 APP.\{0,60\}" 幫助中心/Landlordonboarding00phone_zh-Hant.html` → 命中原句
- `git -C jgb2/dev2 grep -n viewport master -- resources/views/layouts/app.blade.php` → 命中

## 10. I｜AI 客服能做什麼

決定：**new → `jgb/I/ai-assistant-capabilities`**

依 `agent_rules.py` 的四條鐵則、判準、五類敏感轉人（客戶案例／報價／合約SLA／法遵／資安），以及 `mcp_facade.py` 的 `_jgb2_spec` 六域（bills/contracts/accounts/meters/estates/repairs，皆 `property_manager`／`tenant` 才有鍵，`prospect` 缺鍵即永不可見，程式註解逐字「prospect 缺鍵＝永不可見（售前不查 jgb2 個資）」）與 `kb.get`/`kb.search`/`help.read` 三受眾皆 M0（人人可用）。只寫這兩檔與 `docs/api/mcp-facade.md` 明確陳述的事，不外推。

查證：
- `grep -n "prospect 缺鍵＝永不可見" rag-orchestrator/services/agent/mcp_facade.py` → 命中（設計註解逐字）
- `grep -n "_jgb2_spec(" -A2 rag-orchestrator/services/agent/mcp_facade.py` 配合其上方 `domains = (...)` tuple → 六域清單
- `grep -n "五類問題一律轉真人" rag-orchestrator/services/agent/agent_rules.py` → `_SENSITIVE_LINE` 組句

## 11. I｜目前不支援的功能

決定：**new → `jgb/I/unsupported-features`（10 項，見下方對「9」與「10」計數落差的說明）**

⚠️ 任務文字寫「9 items」但逐項列出的清單實際有 10 個（逾期分級／分戶帳餘額查詢／雙合約到期錯配預警／單間利差裝修攤提／提前解約損益一鍵試算／招租漏斗平均空置天數／業務派單佣金／ERP財會／客服案件中心SLA／多據點分區權限），來源表 §4「處置彙總」段落本身也是寫「9 項」但列了 10 個名詞——判定是來源表自身計數的筆誤（⛔ 我不自行選邊改動它，只如實反映：我把 10 項全部逐一查證並各寫一句）。

逐項再驗證（皆帶正對照 `EntrustedContract` 在 `app/` 的 22 個檔案命中，證明 grep 工具與 `master` checkout 正常）：

| 項目 | grep 結果 | 判定 |
|---|---|---|
| 逾期分級 | `分級` 於 `Bill.php`／`BillAmercementNotify.php` 0 命中 | 不支援 |
| 分戶帳餘額查詢 | `分戶帳`／`sub_ledger` 0 命中；僅 `BigLandlordReportViewerScope`（可視範圍過濾，非餘額查詢） | 不支援 |
| 雙合約到期錯配預警 | `錯配`／`mismatch` 於 `EntrustedContract.php`／`Contract.php` 0 命中 | 不支援 |
| 單間利差／裝修攤提 | `CommunityRoiService` 明文只做社區層級 | 不支援（社區層級投報率有） |
| 提前解約損益一鍵試算 | `Contract.php` 有 `CONTRACT_EARLY_TERMINATION` 違約金，無「損益試算」 | 不支援（違約金計算有） |
| 招租漏斗／平均空置天數 | 全庫查無對應欄位 | 不支援（空置數量排序有） |
| 業務派單／佣金 | `commission` 0 命中；`Task` 的 `repair` 類型被註解掉 | 不支援 |
| ERP財會（月結關帳/分錄/稽核留痕） | `journal_entry`／`closing_period` 0 命中 | 不支援 |
| 客服案件中心／SLA | `SupportTicket`／`sla` 0 命中 | 不支援 |
| 多據點分區權限 | `分區權限`／`多據點` 0 命中；`config/character.php` 存在但無 zone/branch 欄位 | 不支援 |

查無（無法進一步確認的邊界，交裁決，⛔ 不猜）：
- 「客服案件中心」查到的唯一相關類別是 `app/Modules/CustomerService/Shared/Traits/AuditLog`，屬本 AI 客服模組自身的操作留痕 trait，非面向租客/房東的工單系統——已排除，不當支援證據。

## DSP-060a 補句（社宅支援不主推／商務中心不在範圍）

決定：**append → `jgb/I/team-company-fit`**

選 `team-company-fit` 而非 `product-overview`：前者主題就是「公司或包租代管團隊適合嗎」，社宅業者與商務中心都是「這個客群適合嗎」的範圍問題，語意貼合；`product-overview` 主題是系統總覽功能介紹，硬塞範圍聲明會偏題。兩句依 DSP-060a 逐字裁決：社宅句陳述「支援」的產品事實（`Role::RULE_KEY_LANDLORD_SOCIAL_HOUSING` 常數存在、既有 D/F 社宅細目可查），商務中心句陳述「範圍」而非「產品做不到」，已在 `not_supported_notes` 註明避免誤讀。

查證：
- `git -C jgb2/dev2 grep -n RULE_KEY_LANDLORD_SOCIAL_HOUSING master -- app/Role.php` → `const RULE_KEY_LANDLORD_SOCIAL_HOUSING = 4` 及多處 `allow_role_key` 引用
- `rag-orchestrator/canon/jgb/D.md` `jgb/D/social-housing-lease`、`rag-orchestrator/canon/jgb/F.md` `jgb/F/social-housing-repair-responsibility` → 既有細目存在

---

## 總表

| # | 主題 | 決定 | 句數 |
|---|---|---|---|
| 1 | 修繕派廠商 | ⛔ 不寫（已覆蓋） | 0 |
| 2 | 逾期滯納金/催繳 | append | 1 |
| 3 | 大房東月報排程 | ⛔ 不寫（已覆蓋） | 0 |
| 4 | 委託約/租賃約 | append | 3 |
| 5 | 社區投報率 | new | 6 |
| 6 | 社區空置排序 | new（看板半段⛔不寫） | 3 |
| 7 | 任務管理器 | new | 4 |
| 8 | 通知通道 | new | 3 |
| 9 | 手機怎麼用 | new | 3 |
| 10 | AI客服能做什麼 | new | 5 |
| 11 | 不支援功能清單 | new | 10 |
| DSP-060a | 社宅/商務中心補句 | append | 2 |

**查無彙總**（三項）：
1. 「出租狀態看板」查無 UI 入口（`rent_status.php` 未被任何 controller/route 引用），僅排序半段成立。
2. 「客服案件中心」查到的 `AuditLog` trait 是本 AI 客服模組自身留痕、非工單系統，不算支援證據。
3. 來源表 §4 標「不支援 9 項」但實列 10 項，計數本身有筆誤，交人裁決是否改表；本次已就全部 10 項逐一查證。
