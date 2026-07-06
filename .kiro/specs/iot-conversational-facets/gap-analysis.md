# 落差分析：iot-conversational-facets

> 分析日期：2026-07-04　基準：requirements.md（R1–R9）＋現行 codebase（contract＋billing＋account 三域全收案後）
> 定位：提供資訊與選項，不做最終決定；〔研究〕標記者入設計階段研究清單。

## 一、現況元件盤點

| 元件 | 現況 | 對本 spec 的意義 |
|---|---|---|
| 面向化底座全套 | 母子分類、三層脈絡、config_for_category、face 貫穿、secondary_calls（清單）、deterministic_id、suppress_head_id、候選辨識、收斂/身分保底——三域實戰 ×3 | 純資料複製，引擎連前三域補的通用擴充都現成 |
| **`/meters` 端點白名單（重大發現）** | jgb2 已上線（MeterApiController.php:100-114）：`is_poweron`（供電）／`balance`+`available_meter`（餘額/可用度數）／`is_online`（連線）／`is_low_battery`／`synced_at`（最後同步）／`current_reading`（度數現值）／`is_topup`+`enable_topup`（預付型判別）／`estate_id`+`estate_name`（識別）／`manufacturer`＋`meter_type`（cloud/manual） | **未給電三路判因（R2.2）要的欄位全部現成**——is_poweron × balance × is_online 直接可判；設備狀況查詢（R2.5）齊；識別鏈用 estate_name keyword。**G 缺口趨近於零** |
| `/recharge-accounts` 端點 | 已上線（index＋store，含分頁） | 儲值帳戶 grounding（R3）；20151 無資料，欄位形狀〔研究：真碼白名單〕 |
| `iot.py`＋`jgb_iot_manufacturers` | diagnose_iot（廠商綁定失敗）＋綁定狀態格式化；實測 20151 回 DAE×2＋SkyWatch | R2.3 廠商串接分支的現成骨架；face=None 零回歸慣例同前三域 |
| 既有知識 | IoT 智慧設備 5 筆 | R7.2 補標對象 |
| 驗證 harness | 路由回歸（59+15 案）、面向整合/e2e 模式、匯入工具、runbook | R9 直接擴案例 |

## 二、逐需求落差與實作選項

### R1 底座 — 落差＝純資料
母 `智慧設備`＋2 子分類、脈絡 3 列、config 2 筆——照四件套 migration 模式。無程式落差。

### R2 電表排障 — **主落差 1：識別鏈粒度**
一戶可能多顆電表（總表/分表）。選項：
- **A. 單槽 meter_ref＋estate_name keyword 裁判（傾向）**：物件名/房號 → meters keyword 過濾 → 多顆列候選（label 帶 name/estate_name/度數）——沿 bill_ref/member_ref 模式，機制零改。〔研究：meters 端點支援哪些查詢參數——estate_id？keyword？〕
- B. 先鎖合約再查電表：兩跳，複雜且合約≠電表歸屬。

### R2 — **主落差 2：未給電判因優先序與復電機制**〔研究核心〕
欄位全齊（is_poweron/balance/is_online），缺的是**決策樹語義**：
- balance≤0 且 is_poweron=false ⇒ 餘額耗盡斷電？還是有獨立斷電原因欄？
- is_online=false 時 is_poweron 值可信嗎（離線設備的欄位新鮮度——synced_at 判讀）？
- 復電路徑：儲值後自動復電？需手動？（涉 R5.5 不代操作紅線的指路內容）
- **「台科電」對應哪個 manufacturer**：對外枚舉只有 SkyWatch/Miezo/DAE——台科電疑為 DAE 中文名或另有整合〔研究：jgb2 內部代號對照〕；廠商差異（斷電/復電/同步機制）逐廠盤。

### R2 — 落差 3：`get_meters` client 包裝
registry 無 wrapper——照 get_team_members 模式新增（含 mock、keyword 參數、分頁處理），小工作量。

### R3 IoT 設定引導 — 落差＝純資料
select='category'（**記得明填 grounding target_user——account spec 逮到的坑**）；儲值 vs 帳務分界寫進 persona＋脈絡。

### R4 門鎖單發包 — 落差＝知識產製
無程式落差；R4.3 誤吸由路由測試把關（門鎖問句不得吸進電表排障）。

### R5 決定性 — 落差＝builder 擴充（iot.py 平行加）
`build_meter_facts`（未給電三路/離線/度數/狀況解碼）＋既有 diagnose_iot 零回歸（face=None 恆等測試同前三域）。度數/金額引存值——meters 欄位皆數值型直引。

### R6 路由 — **主落差：三組誤吸邊界**
①「儲值」語彙：帳務域已有「收款帳戶怎麼綁 金流怎麼申請」錨點與儲值金知識——IoT 錨點避「金流/入帳」、帳務避「電表」；②「看不到電表」：帳號域登入排障實案 9 的語彙——IoT 錨點用「沒電/未給電/離線」不用「看不到」；③門鎖硬體單發 vs 電表排障。三組入路由測試點名（沿 account 模式）。

### R7 知識 — 落差＝執行工作＋**過濾工序（本域特有）**
20 舊案先過 jgb2 現碼過濾（2021-2023 案大半可能已解決/改版）——research 產出「逐案存廢表」再轉製；現行痛點（台科電/未給電/設備狀況）知識以 research 盤出的真機制產製；help 素材 fetch 改 IoT 關鍵字重跑。

### R8 G 清單 — 落差可能為零
meters 欄位已足 R2 主場景；盤查後若缺（如斷電原因碼、復電操作端點），才出 G 契約——**可能是四域第一個「無 G 清單」的 spec**。

### R9 回歸 — 落差＝執行工作
照模式擴；跨域 e2e 選「儲值錢進來了沒」（IoT→帳務）＋「租客說他看不到電表」（IoT→帳號）。

## 三、實作策略選項

| 策略 | 內容 | 權衡 |
|---|---|---|
| **A. 兩面向一次做（傾向）** | 電表排障（grounded）＋設定引導（category），門鎖單發包隨知識批次 | 是四域最小的一次（2 面向、1 builder、1 wrapper）；gate 在 research 的未給電決策樹語義 |
| B. 只做電表排障 | 最小可行 | 設定引導本來就薄（純資料），拆開無收益 |
| C. 等有電表資料的 role 再做 | 20151 無電表資料，e2e 真資料驗證受限 | **真實限制**：e2e 需找有電表的 preview role 或請 JGB 造測試資料——但這是驗證問題不是開發問題，不應阻塞 |

**建議 A**；e2e 真資料前置（找有電表的 role）列 research 待辦，找不到就 e2e 驗降級態＋整合層 stub 驗分支（誠實標注覆蓋差異）。

## 四、設計階段研究清單（jgb2 真碼，file:line 證據）

1. **未給電決策樹語義**：is_poweron/balance/is_online 的判定優先序、餘額耗盡自動斷電條件、復電機制（自動/手動/操作路徑）——R2.2 分支集定案前提。
2. **「台科電」廠商對照**：對外枚舉（SkyWatch/Miezo/DAE）與使用者口中「台科電」的對應；逐廠商斷電/復電/同步機制差異。
3. **meters 查詢參數面**：estate_id/keyword/分頁——識別鏈選項 A 可行性。
4. **recharge-accounts 欄位白名單**＋儲值扣款鏈（單價設定、扣款時點、餘額不足處置）。
5. **離線判定**：is_online 的更新機制與 synced_at 閾值；離線時其他欄位的可信度（facts 措辭要不要帶「截至最後同步」）。
6. **20 舊案逐案存廢表**：對現碼過濾（R7.1 的前置工序）。
7. **e2e 真資料前置**：preview 哪個 role 有電表（掃 roles 或請 JGB 指路）。
